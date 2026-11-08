// G-A speed check: time per hull call, conda binary vs fast path, on SCM-like
// patches. Writes one CSV row per timing sample:
//   shape,implementation,points,us_per_call
// Usage: hull_bench --out samples.csv [--samples 300] [--seed S]

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <format>
#include <fstream>
#include <iostream>
#include <numbers>
#include <ratio>
#include <string>
#include <string_view>
#include <vector>

#include "chrono/core/ChVector2.h"
#include "chrono/utils/ChConvexHull.h"
#include "exact_fast_hull.h"
#include "hull_cases.h"

namespace {

using chrono::ChVector2d;
using Clock = std::chrono::steady_clock;
namespace hull = outrigger::hull;

// Each timing sample repeats the call until at least this much time has passed,
// so timer resolution does not matter.
constexpr std::chrono::microseconds kMinBatchTime{2000};

struct BenchShape {
  std::string name;
  std::vector<ChVector2d> points;
};

/// Shapes matching the S9 setup: FL soil patch at 1 cm, other pads at 2 cm,
/// crawler track segments at 4 cm (project YAML pad types A/B).
std::vector<BenchShape> MakeShapes(std::uint64_t seed) {
  hull::testing::CaseGenerator generator(seed);
  std::vector<BenchShape> shapes;
  shapes.push_back({"pad330_1cm", generator.Pad({0.33, 0.03, 0.0}, 0.01).points});
  shapes.push_back({"pad330_1cm_yaw10",
                    generator.Pad({0.33, 0.03, 10.0 * std::numbers::pi / 180}, 0.01).points});
  shapes.push_back({"pad250_1cm", generator.Pad({0.25, 0.03, 0.0}, 0.01).points});
  shapes.push_back({"pad330_2cm", generator.Pad({0.33, 0.03, 0.0}, 0.02).points});
  shapes.push_back({"pad250_2cm", generator.Pad({0.25, 0.03, 0.0}, 0.02).points});
  shapes.push_back({"track_3m_4cm", generator.Box(3.0, 0.5, 0.0, 0.04).points});
  shapes.push_back({"track_1m_4cm", generator.Box(1.0, 0.5, 0.0, 0.04).points});
  return shapes;
}

template <typename Call>
double MicrosecondsPerCall(Call&& call) {
  std::uint64_t repetitions = 0;
  const Clock::time_point start = Clock::now();
  Clock::duration elapsed{};
  do {
    call();
    ++repetitions;
    elapsed = Clock::now() - start;
  } while (elapsed < kMinBatchTime);
  return std::chrono::duration<double, std::micro>(elapsed).count() /
         static_cast<double>(repetitions);
}

double Percentile(std::vector<double> values, double fraction) {
  std::sort(values.begin(), values.end());
  const double position = fraction * static_cast<double>(values.size() - 1);
  const auto low = static_cast<std::size_t>(position);
  const std::size_t high = std::min(low + 1, values.size() - 1);
  return values[low] + (position - static_cast<double>(low)) * (values[high] - values[low]);
}

}  // namespace

int main(int argc, char** argv) {
  std::filesystem::path out_path;
  int sample_count = 300;
  std::uint64_t seed = 20261108;
  for (int i = 1; i + 1 < argc; i += 2) {
    const std::string_view arg = argv[i];
    if (arg == "--out")
      out_path = argv[i + 1];
    else if (arg == "--samples")
      sample_count = std::max(10, std::atoi(argv[i + 1]));
    else if (arg == "--seed")
      seed = std::strtoull(argv[i + 1], nullptr, 10);
  }
  if (out_path.empty()) {
    std::cerr << "usage: hull_bench --out samples.csv [--samples N] [--seed S]\n";
    return 2;
  }

  std::ofstream csv(out_path);
  csv << "shape,implementation,points,us_per_call\n";
  double sink = 0;  // keeps the optimizer from dropping the calls
  for (BenchShape& shape : MakeShapes(seed)) {
    if (hull::TryComputeHullExact(shape.points).outcome != hull::FastHullOutcome::kComputed) {
      std::cout << std::format("{}: fast path declined, skipped\n", shape.name);
      continue;
    }
    std::vector<double> binary_us;
    std::vector<double> fast_us;
    // Alternate the two implementations so drift affects both equally.
    for (int s = 0; s < sample_count; ++s) {
      binary_us.push_back(MicrosecondsPerCall([&] {
        const chrono::utils::ChConvexHull2D binary(shape.points);
        sink += binary.GetPerimeter();
      }));
      fast_us.push_back(MicrosecondsPerCall(
          [&] { sink += hull::TryComputeHullExact(shape.points).result.perimeter; }));
    }
    for (int s = 0; s < sample_count; ++s) {
      csv << std::format("{},binary,{},{:.4f}\n", shape.name, shape.points.size(), binary_us[s]);
      csv << std::format("{},fast,{},{:.4f}\n", shape.name, shape.points.size(), fast_us[s]);
    }
    const double binary_median = Percentile(binary_us, 0.5);
    const double fast_median = Percentile(fast_us, 0.5);
    std::cout << std::format(
        "{:18} n={:5}  binary median {:9.2f} us (p5 {:9.2f}, p95 {:9.2f})  fast median {:8.2f} us "
        "(p5 {:8.2f}, p95 {:8.2f})  ratio fast/binary {:.4f}\n",
        shape.name, shape.points.size(), binary_median, Percentile(binary_us, 0.05),
        Percentile(binary_us, 0.95), fast_median, Percentile(fast_us, 0.05),
        Percentile(fast_us, 0.95), fast_median / binary_median);
  }
  std::cout << std::format("(checksum {:.6g})\n", sink);
  return 0;
}
