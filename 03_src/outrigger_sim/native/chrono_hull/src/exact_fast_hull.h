// Bit-exact fast replacement for the Jarvis path of chrono::utils::ChConvexHull2D.
//
// SCMTerrain only uses the hull perimeter and area, but both are floating-point sums
// accumulated along the Jarvis edge sequence, so a different (if "better") hull
// algorithm changes their bits. This module reproduces the original edge sequence
// exactly on a reduced candidate set and declines (returns a non-kComputed outcome)
// whenever that equivalence cannot be proven. The caller must then run the original.

#pragma once

#include <cstddef>
#include <vector>

#include "chrono/core/ChVector2.h"

namespace outrigger::hull {

/// Hull data in the same form as chrono::utils::ChConvexHull2D keeps it.
struct HullResult {
  std::vector<chrono::ChVector2d> hull;  ///< Same points, same order as the original.
  double perimeter = 0;
  double area = 0;
};

/// Result of a fast-path attempt. Anything other than kComputed means
/// "use the original implementation"; the value tells why (for statistics).
enum class FastHullOutcome {
  kComputed = 0,
  kTooFewPoints,  ///< Below kMinPointsForFastPath; the original is cheap there.
  kNotLattice,    ///< Not an axis-aligned lattice within the certified error bound.
  kDuplicatePoints,
  kCollinearInput,  ///< One row, one column, or all points on one line.
  kAmbiguousStep,   ///< A Jarvis step whose result depends on interior points.
  kLoopGuard,       ///< The reduced run exceeded its size guard.
};
inline constexpr int kFastHullOutcomeCount = 7;

/// Below this many points the fast path is not attempted (n <= 3 is also
/// special-cased by Chrono itself).
inline constexpr std::size_t kMinPointsForFastPath = 32;

struct FastHullAttempt {
  FastHullOutcome outcome = FastHullOutcome::kTooFewPoints;
  HullResult result;  ///< Valid only when outcome == kComputed.
};

/// Compute the Jarvis hull of `points` bit-identically to
/// ChConvexHull2D(points, JARVIS), or decline.
///
/// Requires the points to be an axis-aligned lattice (such as SCM grid nodes,
/// `delta * integer`). Thread-safe (no shared state).
[[nodiscard]] FastHullAttempt TryComputeHullExact(const std::vector<chrono::ChVector2d>& points);

/// Short ASCII name of an outcome, for logs.
[[nodiscard]] const char* ToString(FastHullOutcome outcome);

}  // namespace outrigger::hull
