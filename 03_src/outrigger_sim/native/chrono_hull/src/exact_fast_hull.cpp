// Bit-exact fast replacement for the Jarvis path of chrono::utils::ChConvexHull2D.
//
// Why it is exact (summary; see README.md for the full argument):
//  1. Lattice certificate. If every point is `origin + (k, l) * spacing` up to a
//     small residual, every SignedArea value equals spacing_x*spacing_y*(integer)
//     up to an error E. With E < 1e-11 and spacing_x*spacing_y >= 1e-8, Chrono's
//     tolerance predicate (|value| < 1e-10 means collinear) is the exact integer
//     orientation predicate.
//  2. With an exact predicate, each Jarvis step picks the lowest-index point among
//     the remaining collinear points ahead on the current hull edge. Points that
//     are not on the hull boundary never influence a step, except through the
//     choice of the initial candidate (the lowest-index point that is neither the
//     current point nor already added), and except when the start point is
//     the initial candidate while the walk is on the first hull edge. There the
//     result depends only on the index of the lowest-index point off the edge
//     line, which we look up in the full input (ResolveStepBehindFirst); if the
//     original would step inside the hull we decline.
//  3. So we keep: per lattice row the min-x and max-x points, every point of the
//     bottom and top rows (a superset of the boundary), plus the lowest-index
//     point not kept (so the initial candidate is unchanged). We run the original
//     Jarvis loop verbatim on these points in their original index order. Every
//     floating-point operation that feeds the perimeter and area is then the same
//     operation on the same operands in the same order.

#include "exact_fast_hull.h"

#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdint>
#include <limits>
#include <optional>
#include <span>

namespace outrigger::hull {
namespace {

using chrono::ChVector2d;

// ---------------------------------------------------------------------------
// Constants

// Chrono's collinearity tolerance on twice the signed triangle area.
constexpr double kCollinearEps = 1e-10;

// Certified bound on |computed SignedArea - lattice SignedArea|. Kept 10x below
// kCollinearEps so collinear lattice triples always test as collinear.
constexpr double kMaxCertifiedError = 1e-11;

// Smallest admissible lattice cell area. A non-collinear lattice triple has
// |SignedArea| >= cell area, so it must stay far above kCollinearEps.
constexpr double kMinCellArea = 1e-8;

// Generous unit roundoff (the true one is 2^-53).
constexpr double kRoundoff = 0x1p-52;

// Lattice index ranges larger than this (relative to the point count) are
// declined to keep the per-index tables small.
constexpr std::int64_t kMaxIndexRangePerPoint = 4;
constexpr std::int64_t kMaxIndexRangeSlack = 16;

// ---------------------------------------------------------------------------
// Verbatim copies of the predicates in Chrono src/chrono/utils/ChConvexHull.cpp.
// Do not rewrite these: the bit pattern of the results depends on the exact
// operation order.

double SignedArea(const ChVector2d& p1, const ChVector2d& p2, const ChVector2d& p3) {
  return (p2.y() - p1.y()) * (p3.x() - p2.x()) - (p2.x() - p1.x()) * (p3.y() - p2.y());
}

int Orientation(const ChVector2d& p1, const ChVector2d& p2, const ChVector2d& p3) {
  const double val = SignedArea(p1, p2, p3);
  if (std::abs(val) < kCollinearEps) return 0;
  return (val > 0) ? 1 : -1;
}

bool InBetween(const ChVector2d& p1, const ChVector2d& p2, const ChVector2d& p3) {
  const bool a = (p2.x() >= p1.x() && p2.x() <= p3.x()) || (p2.x() <= p1.x() && p2.x() >= p3.x());
  const bool b = (p2.y() >= p1.y() && p2.y() <= p3.y()) || (p2.y() <= p1.y() && p2.y() >= p3.y());
  return a && b;
}

// ---------------------------------------------------------------------------
// Lattice certificate

double Coordinate(const ChVector2d& point, int axis) { return axis == 0 ? point.x() : point.y(); }

/// Integer lattice indices of all points along one axis.
struct AxisLattice {
  std::vector<std::int32_t> index;  ///< Per point, 0-based from the minimum.
  std::int32_t index_count = 0;     ///< max index + 1
  double spacing = 0;
  double max_residual = 0;
  double extent = 0;   ///< max - min coordinate
  double max_abs = 0;  ///< max |coordinate|
};

struct AxisCertificate {
  FastHullOutcome failure = FastHullOutcome::kComputed;
  AxisLattice lattice;
};

/// Round every coordinate to a lattice index using `spacing`; return the
/// largest residual, or nullopt if an index is out of the allowed range.
std::optional<double> AssignIndices(const std::vector<ChVector2d>& points, int axis, double origin,
                                    double spacing, std::int64_t max_index,
                                    std::vector<std::int32_t>& index) {
  double max_residual = 0;
  for (std::size_t i = 0; i < points.size(); ++i) {
    const double offset = Coordinate(points[i], axis) - origin;
    const std::int64_t k = std::llround(offset / spacing);
    if (k < 0 || k > max_index) return std::nullopt;
    index[i] = static_cast<std::int32_t>(k);
    max_residual = std::max(max_residual, std::abs(offset - static_cast<double>(k) * spacing));
  }
  return max_residual;
}

/// Points sharing a lattice index must have bit-identical coordinates, and the
/// coordinate must increase strictly with the index. This makes Chrono's
/// InBetween box test agree with the integer one.
bool HasConsistentIndexCoordinates(const std::vector<ChVector2d>& points, int axis,
                                   const AxisLattice& lattice) {
  constexpr std::uint64_t kUnset = ~std::uint64_t{0};
  std::vector<std::uint64_t> bits_of_index(lattice.index_count, kUnset);
  for (std::size_t i = 0; i < points.size(); ++i) {
    const std::uint64_t bits = std::bit_cast<std::uint64_t>(Coordinate(points[i], axis));
    std::uint64_t& slot = bits_of_index[lattice.index[i]];
    if (slot == kUnset) {
      slot = bits;
    } else if (slot != bits) {
      return false;
    }
  }
  double previous = -std::numeric_limits<double>::infinity();
  for (const std::uint64_t bits : bits_of_index) {
    if (bits == kUnset) continue;
    const double value = std::bit_cast<double>(bits);
    if (!(value > previous)) return false;
    previous = value;
  }
  return true;
}

AxisCertificate CertifyAxis(const std::vector<ChVector2d>& points, int axis) {
  AxisCertificate certificate;
  AxisLattice& lattice = certificate.lattice;

  double minimum = std::numeric_limits<double>::infinity();
  double maximum = -std::numeric_limits<double>::infinity();
  for (const ChVector2d& point : points) {
    const double value = Coordinate(point, axis);
    if (!std::isfinite(value)) {
      certificate.failure = FastHullOutcome::kNotLattice;
      return certificate;
    }
    minimum = std::min(minimum, value);
    maximum = std::max(maximum, value);
    lattice.max_abs = std::max(lattice.max_abs, std::abs(value));
  }
  lattice.extent = maximum - minimum;

  double coarse_spacing = std::numeric_limits<double>::infinity();
  for (const ChVector2d& point : points) {
    const double offset = Coordinate(point, axis) - minimum;
    if (offset > 0) coarse_spacing = std::min(coarse_spacing, offset);
  }
  if (!std::isfinite(coarse_spacing)) {
    certificate.failure = FastHullOutcome::kCollinearInput;  // single column/row
    return certificate;
  }

  const std::int64_t max_index =
      kMaxIndexRangePerPoint * static_cast<std::int64_t>(points.size()) + kMaxIndexRangeSlack;
  lattice.index.resize(points.size());
  if (!AssignIndices(points, axis, minimum, coarse_spacing, max_index, lattice.index)) {
    certificate.failure = FastHullOutcome::kNotLattice;
    return certificate;
  }

  // Refine the spacing over the whole extent so the residual does not grow
  // with the index (the coarse spacing carries the rounding of one difference).
  const std::int32_t top_index = *std::max_element(lattice.index.begin(), lattice.index.end());
  lattice.spacing = lattice.extent / static_cast<double>(top_index);
  const std::optional<double> residual =
      AssignIndices(points, axis, minimum, lattice.spacing, max_index, lattice.index);
  if (!residual) {
    certificate.failure = FastHullOutcome::kNotLattice;
    return certificate;
  }
  lattice.max_residual = *residual;
  lattice.index_count = top_index + 1;

  if (!HasConsistentIndexCoordinates(points, axis, lattice)) {
    certificate.failure = FastHullOutcome::kNotLattice;
  }
  return certificate;
}

/// Upper bound on |computed SignedArea - exact lattice SignedArea| for any
/// triple of the input points (see README.md, "error bound").
double SignedAreaErrorBound(const AxisLattice& x, const AxisLattice& y) {
  const double extent = std::max(x.extent, y.extent);
  const double magnitude = std::max(x.max_abs, y.max_abs);
  const double residual =
      std::max(x.max_residual, y.max_residual) + 4 * kRoundoff * (magnitude + extent);
  const double difference_error = 2 * residual + kRoundoff * extent;
  return 4 * extent * difference_error + 2 * difference_error * difference_error +
         4 * kRoundoff * extent * extent;
}

// ---------------------------------------------------------------------------
// Integer geometry checks

std::int64_t LatticeCross(std::int64_t ax, std::int64_t ay, std::int64_t bx, std::int64_t by,
                          std::int64_t cx, std::int64_t cy) {
  return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
}

bool HasDuplicateNodes(const AxisLattice& x, const AxisLattice& y) {
  std::vector<std::uint64_t> keys(x.index.size());
  for (std::size_t i = 0; i < keys.size(); ++i) {
    keys[i] =
        (static_cast<std::uint64_t>(x.index[i]) << 32) | static_cast<std::uint32_t>(y.index[i]);
  }
  std::sort(keys.begin(), keys.end());
  return std::adjacent_find(keys.begin(), keys.end()) != keys.end();
}

/// Requires at least two distinct nodes (guaranteed by both axes having spacing).
bool AreAllNodesCollinear(const AxisLattice& x, const AxisLattice& y) {
  const std::size_t n = x.index.size();
  std::size_t second = 1;
  while (second < n && x.index[second] == x.index[0] && y.index[second] == y.index[0]) {
    ++second;
  }
  for (std::size_t i = 0; i < n; ++i) {
    if (LatticeCross(x.index[0], y.index[0], x.index[second], y.index[second], x.index[i],
                     y.index[i]) != 0) {
      return false;
    }
  }
  return true;
}

// ---------------------------------------------------------------------------
// Candidate reduction

/// Indices (ascending) of the points kept for the reduced Jarvis run: per-row
/// extremes, the full bottom and top rows, and the lowest-index other point.
std::vector<std::size_t> SelectCandidates(const AxisLattice& x, const AxisLattice& y) {
  const std::size_t n = x.index.size();
  constexpr std::size_t kNone = std::numeric_limits<std::size_t>::max();
  std::vector<std::size_t> row_min(y.index_count, kNone);
  std::vector<std::size_t> row_max(y.index_count, kNone);
  for (std::size_t i = 0; i < n; ++i) {
    const std::int32_t row = y.index[i];
    if (row_min[row] == kNone || x.index[i] < x.index[row_min[row]]) row_min[row] = i;
    if (row_max[row] == kNone || x.index[i] > x.index[row_max[row]]) row_max[row] = i;
  }

  std::vector<bool> keep(n, false);
  const std::int32_t top_row = y.index_count - 1;
  for (std::size_t i = 0; i < n; ++i) {
    const std::int32_t row = y.index[i];
    keep[i] = row == 0 || row == top_row || row_min[row] == i || row_max[row] == i;
  }
  // The lowest-index dropped point keeps the Jarvis initial candidate unchanged.
  for (std::size_t i = 0; i < n; ++i) {
    if (!keep[i]) {
      keep[i] = true;
      break;
    }
  }

  std::vector<std::size_t> kept;
  for (std::size_t i = 0; i < n; ++i) {
    if (keep[i]) kept.push_back(i);
  }
  return kept;
}

// ---------------------------------------------------------------------------
// Reduced Jarvis run

/// Candidate points in original index order, with their original indices.
struct CandidateSet {
  std::span<const ChVector2d> all;     ///< full input
  std::span<const std::size_t> index;  ///< original index of each candidate, ascending
  std::vector<ChVector2d> points;      ///< all[index[i]]
};

constexpr std::size_t kUseRegularScan = std::numeric_limits<std::size_t>::max();
constexpr std::size_t kLeavesBoundary = kUseRegularScan - 1;

/// Next point for a step whose initial candidate is the start point `first`
/// while `crt` lies on the first hull edge (first is directly behind crt).
///
/// The original scan keeps `first` until it meets the lowest-index point j* off
/// the line, which replaces it; the first point ahead on the line with index
/// greater than j* then wins and stays. Returns that candidate, or
/// kUseRegularScan when nothing lies ahead (crt is the far end of the edge,
/// where the regular scan is exact), or kLeavesBoundary when no point ahead
/// comes after j* (the original would step inside the hull; we decline).
std::size_t ResolveStepBehindFirst(const CandidateSet& set, const std::vector<bool>& added,
                                   std::size_t crt, std::size_t first) {
  const std::vector<ChVector2d>& points = set.points;
  bool has_point_ahead = false;
  for (std::size_t i = 0; i < points.size(); ++i) {
    if (i != crt && i != first && !added[i] &&
        Orientation(points[crt], points[i], points[first]) == 0) {
      has_point_ahead = true;
      break;
    }
  }
  if (!has_point_ahead) return kUseRegularScan;

  std::size_t lowest_off_line = 0;
  while (lowest_off_line < set.all.size() &&
         Orientation(points[crt], set.all[lowest_off_line], points[first]) == 0) {
    ++lowest_off_line;
  }
  for (std::size_t i = 0; i < points.size(); ++i) {
    if (set.index[i] > lowest_off_line && i != crt && i != first && !added[i] &&
        Orientation(points[crt], points[i], points[first]) == 0) {
      return i;
    }
  }
  return kLeavesBoundary;
}

/// The loop of ChConvexHull2D::ComputeJarvis on the candidates, verbatim except
/// for the parts marked "fast path".
FastHullOutcome RunJarvis(const CandidateSet& set, HullResult& result) {
  const std::vector<ChVector2d>& points = set.points;
  const std::size_t n = points.size();
  std::vector<bool> added(n, false);

  std::size_t first = 0;
  for (std::size_t i = 1; i < n; i++) {
    const double dx = points[i].x() - points[first].x();
    if (dx < 0)
      first = i;
    else if (dx == 0 && points[i].y() < points[first].y())
      first = i;
  }
  result.hull.push_back(points[first]);

  // Fast path: track whether the walk is still on the first hull edge (the only
  // place where `first` lies directly behind crt).
  bool on_first_edge = true;
  std::size_t first_edge_point = first;  // second point of the walk

  std::size_t crt = first;
  do {
    std::size_t next = 0;
    while (next == crt || added[next]) next = (next + 1) % n;

    // Fast path: with `first` behind crt, the original result depends on the
    // index of the lowest-index point off the edge line, which may be a dropped
    // interior point.
    // Elsewhere (hull vertices, the closing edge) `first` is an ordinary
    // candidate and the regular scan is exact.
    std::size_t resolved = kUseRegularScan;
    if (next == first && crt != first && on_first_edge) {
      resolved = ResolveStepBehindFirst(set, added, crt, first);
      if (resolved == kLeavesBoundary) return FastHullOutcome::kAmbiguousStep;
    }

    if (resolved != kUseRegularScan) {
      next = resolved;
    } else {
      for (std::size_t i = 0; i < n; i++) {
        if (Orientation(points[crt], points[i], points[next]) == -1) next = i;
      }
    }

    for (std::size_t i = 0; i < n; i++) {
      if (i != crt && i != next && !added[i] &&
          Orientation(points[crt], points[i], points[next]) == 0 &&
          InBetween(points[crt], points[i], points[next])) {
        result.hull.push_back(points[i]);
        added[i] = true;
      }
    }

    result.hull.push_back(points[next]);
    added[next] = true;
    result.perimeter += (points[next] - points[crt]).Length();
    result.area += SignedArea(points[next], points[crt], ChVector2d(0, 0));

    // Fast path: a correct walk pushes at most n + 1 points.
    if (result.hull.size() > n + 1) return FastHullOutcome::kLoopGuard;

    if (crt == first) {
      first_edge_point = next;
    } else if (on_first_edge) {
      on_first_edge = Orientation(points[first], points[first_edge_point], points[next]) == 0;
    }
    crt = next;
  } while (crt != first);

  return FastHullOutcome::kComputed;
}

}  // namespace

FastHullAttempt TryComputeHullExact(const std::vector<ChVector2d>& points) {
  FastHullAttempt attempt;
  if (points.size() < kMinPointsForFastPath) {
    attempt.outcome = FastHullOutcome::kTooFewPoints;
    return attempt;
  }

  const AxisCertificate x = CertifyAxis(points, 0);
  if (x.failure != FastHullOutcome::kComputed) {
    attempt.outcome = x.failure;
    return attempt;
  }
  const AxisCertificate y = CertifyAxis(points, 1);
  if (y.failure != FastHullOutcome::kComputed) {
    attempt.outcome = y.failure;
    return attempt;
  }
  if (SignedAreaErrorBound(x.lattice, y.lattice) > kMaxCertifiedError ||
      x.lattice.spacing * y.lattice.spacing < kMinCellArea) {
    attempt.outcome = FastHullOutcome::kNotLattice;
    return attempt;
  }
  if (HasDuplicateNodes(x.lattice, y.lattice)) {
    attempt.outcome = FastHullOutcome::kDuplicatePoints;
    return attempt;
  }
  if (AreAllNodesCollinear(x.lattice, y.lattice)) {
    attempt.outcome = FastHullOutcome::kCollinearInput;
    return attempt;
  }

  const std::vector<std::size_t> kept = SelectCandidates(x.lattice, y.lattice);
  CandidateSet candidates{points, kept, {}};
  candidates.points.reserve(kept.size());
  for (const std::size_t i : kept) candidates.points.push_back(points[i]);

  attempt.outcome = RunJarvis(candidates, attempt.result);
  if (attempt.outcome != FastHullOutcome::kComputed) {
    attempt.result = HullResult{};
    return attempt;
  }
  // ChConvexHull2D applies the factor after ComputeJarvis returns.
  attempt.result.area *= 0.5;
  return attempt;
}

const char* ToString(FastHullOutcome outcome) {
  switch (outcome) {
    case FastHullOutcome::kComputed:
      return "computed";
    case FastHullOutcome::kTooFewPoints:
      return "too_few_points";
    case FastHullOutcome::kNotLattice:
      return "not_lattice";
    case FastHullOutcome::kDuplicatePoints:
      return "duplicate_points";
    case FastHullOutcome::kCollinearInput:
      return "collinear_input";
    case FastHullOutcome::kAmbiguousStep:
      return "ambiguous_step";
    case FastHullOutcome::kLoopGuard:
      return "loop_guard";
  }
  return "unknown";
}

}  // namespace outrigger::hull
