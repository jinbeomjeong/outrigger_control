// Verbatim local copy of ChConvexHull2D(points, JARVIS) from Chrono
// src/chrono/utils/ChConvexHull.cpp, compiled with this project's flags.
// The equivalence test checks it against the conda binary first: if the copy
// matches, this build's floating-point code generation matches Chrono's.

#pragma once

#include <cmath>
#include <cstddef>
#include <vector>

#include "chrono/core/ChVector2.h"
#include "exact_fast_hull.h"

namespace outrigger::hull::reference {

inline double SignedArea(const chrono::ChVector2d& p1, const chrono::ChVector2d& p2,
                         const chrono::ChVector2d& p3) {
  return (p2.y() - p1.y()) * (p3.x() - p2.x()) - (p2.x() - p1.x()) * (p3.y() - p2.y());
}

inline int Orientation(const chrono::ChVector2d& p1, const chrono::ChVector2d& p2,
                       const chrono::ChVector2d& p3) {
  static double eps = 1e-10;
  const double val = SignedArea(p1, p2, p3);
  if (std::abs(val) < eps) return 0;
  return (val > 0) ? 1 : -1;
}

inline bool InBetween(const chrono::ChVector2d& p1, const chrono::ChVector2d& p2,
                      const chrono::ChVector2d& p3) {
  const bool a = (p2.x() >= p1.x() && p2.x() <= p3.x()) || (p2.x() <= p1.x() && p2.x() >= p3.x());
  const bool b = (p2.y() >= p1.y() && p2.y() <= p3.y()) || (p2.y() <= p1.y() && p2.y() >= p3.y());
  return a && b;
}

/// ChConvexHull2D(points, JARVIS), including the n <= 3 special cases and the
/// infinite-loop guard (without its console message).
inline HullResult ComputeOriginalJarvis(const std::vector<chrono::ChVector2d>& points) {
  using chrono::ChVector2d;
  HullResult r;
  const std::size_t n = points.size();
  if (n == 1) {
    r.hull.push_back(points[0]);
    return r;
  }
  if (n == 2) {
    r.perimeter = (points[1] - points[0]).Length();
    r.hull = {points[0], points[1]};
    return r;
  }
  if (n == 3) {
    r.area = 0.5 * std::abs(SignedArea(points[0], points[1], points[2]));
    r.perimeter = (points[1] - points[0]).Length() + (points[2] - points[1]).Length() +
                  (points[0] - points[2]).Length();
    r.hull = {points[0], points[1], points[2]};
    return r;
  }

  std::vector<bool> added(points.size(), false);
  std::size_t first = 0;
  for (std::size_t i = 1; i < points.size(); i++) {
    const double dx = points[i].x() - points[first].x();
    if (dx < 0)
      first = i;
    else if (dx == 0 && points[i].y() < points[first].y())
      first = i;
  }
  r.hull.push_back(points[first]);
  std::size_t crt = first;
  do {
    std::size_t next = 0;
    while (next == crt || added[next]) next = (next + 1) % n;
    for (std::size_t i = 0; i < n; i++) {
      if (Orientation(points[crt], points[i], points[next]) == -1) next = i;
    }
    for (std::size_t i = 0; i < n; i++) {
      if (i != crt && i != next && !added[i] &&
          Orientation(points[crt], points[i], points[next]) == 0 &&
          InBetween(points[crt], points[i], points[next])) {
        r.hull.push_back(points[i]);
        added[i] = true;
      }
    }
    r.hull.push_back(points[next]);
    added[next] = true;
    r.perimeter += (points[next] - points[crt]).Length();
    r.area += SignedArea(points[next], points[crt], ChVector2d(0, 0));
    if (r.hull.size() > n + 1) break;
    crt = next;
  } while (crt != first);
  r.area *= 0.5;
  return r;
}

}  // namespace outrigger::hull::reference
