// Random convex-hull inputs for the equivalence test and the benchmark.
//
// Lattice families imitate SCMTerrain contact patches: points are
// `delta * integer node index` (computed the way SCM does) and ordered by a
// 4-neighbour flood fill from a random seed node, like the SCM patch builder.

#pragma once

#include <cstdint>
#include <random>
#include <string>
#include <vector>

#include "chrono/core/ChVector2.h"

namespace outrigger::hull::testing {

struct HullCase {
  std::string family;
  std::vector<chrono::ChVector2d> points;
};

/// Shape of a pad-like footprint (regular octagon from a chamfered square).
struct PadShape {
  double side_m = 0.33;
  double chamfer_m = 0.03;
  double yaw_rad = 0;
};

class CaseGenerator {
 public:
  explicit CaseGenerator(std::uint64_t seed) : engine_(seed) {}

  /// Next case from a weighted mix of all families.
  HullCase Next();

  /// Rasterized pad footprint at `delta_m`, flood-fill ordered. Deterministic
  /// for a given generator state; used by the benchmark.
  HullCase Pad(const PadShape& shape, double delta_m);

  /// Rasterized rotated rectangle (crawler track segment), flood-fill ordered.
  HullCase Box(double length_m, double width_m, double yaw_rad, double delta_m);

 private:
  HullCase RandomPad();
  HullCase RandomBox();
  HullCase PartialPad();
  HullCase Blob();
  HullCase SmallLattice();
  HullCase LatticeLine();
  HullCase SeedIsFirst();
  HullCase DuplicatedNodes();
  HullCase GenericDoubles();
  HullCase NearCollinear();
  HullCase Shuffled();

  double Uniform(double low, double high);
  int UniformInt(int low, int high);
  double RandomDelta();

  std::mt19937_64 engine_;
};

}  // namespace outrigger::hull::testing
