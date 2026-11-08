#include "hull_cases.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <numbers>
#include <queue>
#include <unordered_map>
#include <unordered_set>
#include <utility>

namespace outrigger::hull::testing {
namespace {

using chrono::ChVector2d;

struct Node {
  int i;
  int j;
  bool operator==(const Node&) const = default;
};

std::int64_t Key(Node node) {
  return (static_cast<std::int64_t>(node.i) << 32) ^ static_cast<std::uint32_t>(node.j);
}

// Grid index of the shape centre is drawn from this range, so world
// coordinates reach about +-50 m at 1 cm spacing (rounding stress).
constexpr int kMaxOriginIndex = 5000;

// Same neighbour order as SCMTerrain's flood fill.
constexpr std::array<Node, 4> kNeighbors4 = {Node{-1, 0}, Node{1, 0}, Node{0, -1}, Node{0, 1}};

/// Point exactly as SCMTerrain builds it: ChVector2d(m_delta * ij.x(), m_delta * ij.y()).
ChVector2d ScmPoint(Node node, double delta) { return ChVector2d(delta * node.i, delta * node.j); }

/// 4-neighbour flood fill from `nodes[seed]` over `nodes`; returns the points of
/// the seed's connected component in visiting order (the SCM patch order).
std::vector<ChVector2d> FloodFillOrder(const std::vector<Node>& nodes, std::size_t seed,
                                       double delta) {
  std::unordered_map<std::int64_t, bool> visited;
  for (const Node node : nodes) visited.emplace(Key(node), false);

  std::vector<ChVector2d> points;
  std::queue<Node> todo;
  visited[Key(nodes[seed])] = true;
  points.push_back(ScmPoint(nodes[seed], delta));
  todo.push(nodes[seed]);
  while (!todo.empty()) {
    const Node current = todo.front();
    todo.pop();
    for (const Node step : kNeighbors4) {
      const Node neighbor{current.i + step.i, current.j + step.j};
      auto found = visited.find(Key(neighbor));
      if (found == visited.end() || found->second) continue;
      found->second = true;
      points.push_back(ScmPoint(neighbor, delta));
      todo.push(neighbor);
    }
  }
  return points;
}

/// Grid nodes whose position relative to the shape centre satisfies `inside`.
template <typename InsidePredicate>
std::vector<Node> Rasterize(double half_extent_m, double delta, Node origin, double sub_x,
                            double sub_y, InsidePredicate inside) {
  const int reach = static_cast<int>(std::ceil(half_extent_m / delta)) + 2;
  std::vector<Node> nodes;
  for (int di = -reach; di <= reach; ++di) {
    for (int dj = -reach; dj <= reach; ++dj) {
      const double x = di * delta - sub_x;
      const double y = dj * delta - sub_y;
      if (inside(x, y)) nodes.push_back(Node{origin.i + di, origin.j + dj});
    }
  }
  return nodes;
}

bool InsideOctagon(double x, double y, const PadShape& shape) {
  const double c = std::cos(-shape.yaw_rad);
  const double s = std::sin(-shape.yaw_rad);
  const double xr = std::abs(c * x - s * y);
  const double yr = std::abs(s * x + c * y);
  const double half = 0.5 * shape.side_m;
  return xr <= half && yr <= half && xr + yr <= shape.side_m - shape.chamfer_m;
}

bool InsideBox(double x, double y, double length, double width, double yaw) {
  const double c = std::cos(-yaw);
  const double s = std::sin(-yaw);
  return std::abs(c * x - s * y) <= 0.5 * length && std::abs(s * x + c * y) <= 0.5 * width;
}

}  // namespace

double CaseGenerator::Uniform(double low, double high) {
  return std::uniform_real_distribution<double>(low, high)(engine_);
}

int CaseGenerator::UniformInt(int low, int high) {
  return std::uniform_int_distribution<int>(low, high)(engine_);
}

double CaseGenerator::RandomDelta() {
  constexpr std::array<double, 3> kDeltas = {0.01, 0.02, 0.04};  // SCM grids used in S9
  const int pick = UniformInt(0, 3);
  // One draw in four uses an arbitrary spacing (not a short decimal).
  return pick < 3 ? kDeltas[static_cast<std::size_t>(pick)] : Uniform(0.005, 0.05);
}

HullCase CaseGenerator::Pad(const PadShape& shape, double delta_m) {
  const Node origin{UniformInt(-kMaxOriginIndex, kMaxOriginIndex),
                    UniformInt(-kMaxOriginIndex, kMaxOriginIndex)};
  const double sub_x = Uniform(0, delta_m);
  const double sub_y = Uniform(0, delta_m);
  std::vector<Node> nodes =
      Rasterize(shape.side_m, delta_m, origin, sub_x, sub_y,
                [&](double x, double y) { return InsideOctagon(x, y, shape); });
  if (nodes.empty()) nodes.push_back(origin);
  const auto seed = static_cast<std::size_t>(UniformInt(0, static_cast<int>(nodes.size()) - 1));
  return {"pad", FloodFillOrder(nodes, seed, delta_m)};
}

HullCase CaseGenerator::Box(double length_m, double width_m, double yaw_rad, double delta_m) {
  const Node origin{UniformInt(-kMaxOriginIndex, kMaxOriginIndex),
                    UniformInt(-kMaxOriginIndex, kMaxOriginIndex)};
  const double sub_x = Uniform(0, delta_m);
  const double sub_y = Uniform(0, delta_m);
  std::vector<Node> nodes =
      Rasterize(0.5 * std::hypot(length_m, width_m), delta_m, origin, sub_x, sub_y,
                [&](double x, double y) { return InsideBox(x, y, length_m, width_m, yaw_rad); });
  if (nodes.empty()) nodes.push_back(origin);
  const auto seed = static_cast<std::size_t>(UniformInt(0, static_cast<int>(nodes.size()) - 1));
  return {"box", FloodFillOrder(nodes, seed, delta_m)};
}

HullCase CaseGenerator::RandomPad() {
  PadShape shape;
  shape.side_m = Uniform(0.15, 0.5);
  shape.chamfer_m = Uniform(0, 0.25 * shape.side_m);
  shape.yaw_rad = Uniform(0, 0.5 * std::numbers::pi);
  return Pad(shape, RandomDelta());
}

HullCase CaseGenerator::RandomBox() {
  const double delta = UniformInt(0, 1) == 0 ? 0.02 : 0.04;
  HullCase c = Box(Uniform(0.2, 3.5), Uniform(0.1, 0.6), Uniform(0, std::numbers::pi), delta);
  return c;
}

HullCase CaseGenerator::PartialPad() {
  PadShape shape{Uniform(0.15, 0.5), 0, Uniform(0, 0.5 * std::numbers::pi)};
  shape.chamfer_m = Uniform(0, 0.25 * shape.side_m);
  const double delta = RandomDelta();
  const double direction = Uniform(0, 2 * std::numbers::pi);
  const double cut = Uniform(-0.3, 0.4) * shape.side_m;
  const Node origin{UniformInt(-kMaxOriginIndex, kMaxOriginIndex),
                    UniformInt(-kMaxOriginIndex, kMaxOriginIndex)};
  std::vector<Node> nodes = Rasterize(
      shape.side_m, delta, origin, Uniform(0, delta), Uniform(0, delta), [&](double x, double y) {
        return InsideOctagon(x, y, shape) &&
               std::cos(direction) * x + std::sin(direction) * y <= cut;
      });
  if (nodes.empty()) nodes.push_back(origin);
  const auto seed = static_cast<std::size_t>(UniformInt(0, static_cast<int>(nodes.size()) - 1));
  return {"partial_pad", FloodFillOrder(nodes, seed, delta)};
}

HullCase CaseGenerator::Blob() {
  const int target = UniformInt(32, 3000);
  const Node origin{UniformInt(-kMaxOriginIndex, kMaxOriginIndex),
                    UniformInt(-kMaxOriginIndex, kMaxOriginIndex)};
  std::vector<Node> nodes = {origin};
  std::unordered_set<std::int64_t> occupied = {Key(origin)};
  while (static_cast<int>(nodes.size()) < target) {
    const Node base =
        nodes[static_cast<std::size_t>(UniformInt(0, static_cast<int>(nodes.size()) - 1))];
    const Node step = kNeighbors4[static_cast<std::size_t>(UniformInt(0, 3))];
    const Node grown{base.i + step.i, base.j + step.j};
    if (occupied.insert(Key(grown)).second) nodes.push_back(grown);
  }
  const auto seed = static_cast<std::size_t>(UniformInt(0, static_cast<int>(nodes.size()) - 1));
  return {"blob", FloodFillOrder(nodes, seed, RandomDelta())};
}

HullCase CaseGenerator::SmallLattice() {
  const int count = UniformInt(1, 40);
  const int box = UniformInt(1, 8);
  const double delta = RandomDelta();
  const Node origin{UniformInt(-kMaxOriginIndex, kMaxOriginIndex),
                    UniformInt(-kMaxOriginIndex, kMaxOriginIndex)};
  HullCase c{"small_lattice", {}};
  for (int k = 0; k < count; ++k) {
    c.points.push_back(
        ScmPoint(Node{origin.i + UniformInt(0, box), origin.j + UniformInt(0, box)}, delta));
  }
  return c;
}

HullCase CaseGenerator::LatticeLine() {
  const int count = UniformInt(2, 80);
  const Node step =
      std::array<Node, 4>{Node{1, 0}, Node{0, 1}, Node{1, 1}, Node{2, -1}}[UniformInt(0, 3)];
  const double delta = RandomDelta();
  const Node origin{UniformInt(-kMaxOriginIndex, kMaxOriginIndex),
                    UniformInt(-kMaxOriginIndex, kMaxOriginIndex)};
  HullCase c{"lattice_line", {}};
  for (int k = 0; k < count; ++k) {
    c.points.push_back(ScmPoint(Node{origin.i + k * step.i, origin.j + k * step.j}, delta));
  }
  if (UniformInt(0, 1) == 1) {
    c.points.push_back(ScmPoint(Node{origin.i + 1, origin.j + 3}, delta));
  }
  std::shuffle(c.points.begin(), c.points.end(), engine_);
  return c;
}

HullCase CaseGenerator::SeedIsFirst() {
  HullCase c = RandomPad();
  // Put the Jarvis start point (lowest x, then lowest y) at index 0: this is
  // the case where the fast path must decline.
  auto first = std::min_element(c.points.begin(), c.points.end(),
                                [](const ChVector2d& a, const ChVector2d& b) {
                                  return a.x() < b.x() || (a.x() == b.x() && a.y() < b.y());
                                });
  std::iter_swap(c.points.begin(), first);
  c.family = "seed_is_first";
  return c;
}

HullCase CaseGenerator::DuplicatedNodes() {
  HullCase c = RandomPad();
  const int copies = UniformInt(1, 3);
  for (int k = 0; k < copies; ++k) {
    const ChVector2d copy =
        c.points[static_cast<std::size_t>(UniformInt(0, static_cast<int>(c.points.size()) - 1))];
    c.points.insert(c.points.begin() + UniformInt(0, static_cast<int>(c.points.size())), copy);
  }
  c.family = "duplicated_nodes";
  return c;
}

HullCase CaseGenerator::GenericDoubles() {
  const int count = UniformInt(4, 300);
  const double scale = std::pow(10.0, Uniform(-2, 2));
  const bool gaussian = UniformInt(0, 1) == 1;
  std::normal_distribution<double> normal(0, scale);
  HullCase c{"generic_doubles", {}};
  for (int k = 0; k < count; ++k) {
    c.points.emplace_back(gaussian ? normal(engine_) : Uniform(-scale, scale),
                          gaussian ? normal(engine_) : Uniform(-scale, scale));
  }
  return c;
}

HullCase CaseGenerator::NearCollinear() {
  const int count = UniformInt(4, 200);
  const double angle = Uniform(0, std::numbers::pi);
  const double noise = std::pow(10.0, Uniform(-13, -8));
  HullCase c{"near_collinear", {}};
  for (int k = 0; k < count; ++k) {
    const double t = Uniform(-1, 1);
    c.points.emplace_back(t * std::cos(angle) + Uniform(-noise, noise),
                          t * std::sin(angle) + Uniform(-noise, noise));
  }
  return c;
}

HullCase CaseGenerator::Shuffled() {
  HullCase c = UniformInt(0, 1) == 0 ? RandomPad() : Blob();
  std::shuffle(c.points.begin(), c.points.end(), engine_);
  c.family = "shuffled_lattice";
  return c;
}

HullCase CaseGenerator::Next() {
  // Weights favour SCM-like patches; the rest exercise fallbacks and edge cases.
  const int pick = UniformInt(0, 99);
  if (pick < 25) return RandomPad();
  if (pick < 35) return RandomBox();
  if (pick < 50) return PartialPad();
  if (pick < 63) return Blob();
  if (pick < 66) return SeedIsFirst();
  if (pick < 68) return DuplicatedNodes();
  if (pick < 78) return SmallLattice();
  if (pick < 83) return LatticeLine();
  if (pick < 90) return GenericDoubles();
  if (pick < 93) return NearCollinear();
  return Shuffled();
}

}  // namespace outrigger::hull::testing
