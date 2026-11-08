// G-A equivalence test: the fast hull must be bit-identical to the conda
// pychrono binary's chrono::utils::ChConvexHull2D (Chrono_core.dll export).
//
// Usage:
//   hull_equivalence_test --cases N [--seed S] [--threads T] [--out summary.json]
//   hull_equivalence_test --dump patches.ohull [--out summary.json]
// Exit code: 0 = no mismatch, 1 = mismatch found, 2 = bad arguments or input.

#include <algorithm>
#include <atomic>
#include <bit>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <format>
#include <fstream>
#include <iostream>
#include <map>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <thread>
#include <utility>
#include <vector>

#include "chrono/core/ChVector2.h"
#include "chrono/utils/ChConvexHull.h"
#include "exact_fast_hull.h"
#include "hull_cases.h"
#include "patch_dump.h"
#include "reference_jarvis.h"

namespace {

using chrono::ChVector2d;
namespace hull = outrigger::hull;

struct Options {
  std::uint64_t case_count = 0;
  std::uint64_t seed = 20261108;
  int thread_count = 1;
  std::filesystem::path dump_path;
  std::filesystem::path summary_path;
};

/// Counters for one input family.
struct FamilyTally {
  std::uint64_t cases = 0;
  std::uint64_t points = 0;
  std::uint64_t reference_mismatch = 0;  // local verbatim copy vs binary
  std::uint64_t fast_mismatch = 0;       // fast path vs binary
  std::uint64_t layout_mismatch = 0;     // object layout probe vs getters
  std::uint64_t outcome[hull::kFastHullOutcomeCount] = {};

  void Add(const FamilyTally& other) {
    cases += other.cases;
    points += other.points;
    reference_mismatch += other.reference_mismatch;
    fast_mismatch += other.fast_mismatch;
    layout_mismatch += other.layout_mismatch;
    for (int i = 0; i < hull::kFastHullOutcomeCount; ++i) outcome[i] += other.outcome[i];
  }
};

using Tally = std::map<std::string, FamilyTally>;

bool SameBits(double a, double b) {
  return std::bit_cast<std::uint64_t>(a) == std::bit_cast<std::uint64_t>(b);
}

bool SameHull(const std::vector<ChVector2d>& a, const std::vector<ChVector2d>& b) {
  if (a.size() != b.size()) return false;
  for (std::size_t i = 0; i < a.size(); ++i) {
    if (!SameBits(a[i].x(), b[i].x()) || !SameBits(a[i].y(), b[i].y())) return false;
  }
  return true;
}

bool SameResult(const chrono::utils::ChConvexHull2D& binary, const hull::HullResult& other) {
  return SameBits(binary.GetPerimeter(), other.perimeter) &&
         SameBits(binary.GetArea(), other.area) && SameHull(binary.GetHull(), other.hull);
}

/// Mirrors the hook's assumption about ChConvexHull2D's private layout.
struct ConvexHull2DLayout {
  std::vector<ChVector2d> hull;
  double perimeter = 0;
  double area = 0;
};
static_assert(sizeof(ConvexHull2DLayout) == sizeof(chrono::utils::ChConvexHull2D));

bool LayoutMatches(const chrono::utils::ChConvexHull2D& binary) {
  // Deliberate ABI probe: read the object through the layout the hook uses.
  const auto& mirror = reinterpret_cast<const ConvexHull2DLayout&>(binary);
  return SameBits(mirror.perimeter, binary.GetPerimeter()) &&
         SameBits(mirror.area, binary.GetArea()) && mirror.hull.data() == binary.GetHull().data() &&
         mirror.hull.size() == binary.GetHull().size();
}

void SaveMismatch(const std::vector<ChVector2d>& points, std::string_view kind) {
  static std::mutex mutex;
  const std::scoped_lock lock(mutex);
  static int saved = 0;
  if (saved >= 20) return;  // a few examples are enough to debug
  hull::PatchDumpWriter writer(std::format("mismatch_{}_{}.ohull", kind, saved++));
  if (writer.is_open()) writer.Write(points, hull::kDumpMismatch);
}

void CheckCase(const std::string& family, std::vector<ChVector2d> points, Tally& tally) {
  FamilyTally& entry = tally[family];
  ++entry.cases;
  entry.points += points.size();

  // The binary constructor takes a non-const reference but does not modify
  // the points for the JARVIS method.
  const chrono::utils::ChConvexHull2D binary(points);
  if (!LayoutMatches(binary)) ++entry.layout_mismatch;

  if (!SameResult(binary, hull::reference::ComputeOriginalJarvis(points))) {
    ++entry.reference_mismatch;
    SaveMismatch(points, "reference");
  }

  const hull::FastHullAttempt attempt = hull::TryComputeHullExact(points);
  ++entry.outcome[static_cast<int>(attempt.outcome)];
  if (attempt.outcome == hull::FastHullOutcome::kComputed && !SameResult(binary, attempt.result)) {
    ++entry.fast_mismatch;
    SaveMismatch(points, "fast");
  }
}

Tally RunGenerated(const Options& options) {
  Tally total;
  std::mutex total_mutex;
  std::atomic<std::uint64_t> next_case{0};
  {
    std::vector<std::jthread> workers;
    for (int w = 0; w < options.thread_count; ++w) {
      workers.emplace_back([&, w] {
        hull::testing::CaseGenerator generator(options.seed +
                                               7919ULL * static_cast<std::uint64_t>(w));
        Tally local;
        while (next_case.fetch_add(1) < options.case_count) {
          hull::testing::HullCase c = generator.Next();
          CheckCase(c.family, std::move(c.points), local);
        }
        const std::scoped_lock lock(total_mutex);
        for (const auto& [family, entry] : local) total[family].Add(entry);
      });
    }
  }
  return total;
}

std::optional<Tally> RunDump(const std::filesystem::path& path) {
  const std::optional<std::vector<hull::PatchRecord>> records = hull::ReadPatchDump(path);
  if (!records) return std::nullopt;
  Tally tally;
  for (const hull::PatchRecord& record : *records) {
    if (record.points.empty()) continue;  // Chrono itself would read out of bounds
    CheckCase("scm_dump", record.points, tally);
  }
  return tally;
}

std::string ToJson(const Tally& tally, const FamilyTally& sum) {
  std::string json = "{\n  \"families\": {\n";
  bool first_family = true;
  auto append_entry = [&json](const FamilyTally& e) {
    json += std::format(
        "{{\"cases\": {}, \"points\": {}, \"reference_mismatch\": {}, \"fast_mismatch\": {}, "
        "\"layout_mismatch\": {}, \"outcomes\": {{",
        e.cases, e.points, e.reference_mismatch, e.fast_mismatch, e.layout_mismatch);
    for (int i = 0; i < hull::kFastHullOutcomeCount; ++i) {
      json += std::format("{}\"{}\": {}", i == 0 ? "" : ", ",
                          hull::ToString(static_cast<hull::FastHullOutcome>(i)), e.outcome[i]);
    }
    json += "}}";
  };
  for (const auto& [family, entry] : tally) {
    json += std::format("{}    \"{}\": ", first_family ? "" : ",\n", family);
    append_entry(entry);
    first_family = false;
  }
  json += "\n  },\n  \"total\": ";
  append_entry(sum);
  json += "\n}\n";
  return json;
}

std::optional<Options> ParseOptions(int argc, char** argv) {
  Options options;
  for (int i = 1; i < argc; ++i) {
    const std::string_view arg = argv[i];
    const bool has_value = i + 1 < argc;
    if (arg == "--cases" && has_value) {
      options.case_count = std::strtoull(argv[++i], nullptr, 10);
    } else if (arg == "--seed" && has_value) {
      options.seed = std::strtoull(argv[++i], nullptr, 10);
    } else if (arg == "--threads" && has_value) {
      options.thread_count = std::max(1, std::atoi(argv[++i]));
    } else if (arg == "--dump" && has_value) {
      options.dump_path = argv[++i];
    } else if (arg == "--out" && has_value) {
      options.summary_path = argv[++i];
    } else {
      return std::nullopt;
    }
  }
  if (options.case_count == 0 && options.dump_path.empty()) return std::nullopt;
  return options;
}

}  // namespace

int main(int argc, char** argv) {
  const std::optional<Options> options = ParseOptions(argc, argv);
  if (!options) {
    std::cerr << "usage: hull_equivalence_test (--cases N [--seed S] [--threads T] | --dump FILE) "
                 "[--out summary.json]\n";
    return 2;
  }

  Tally tally;
  if (!options->dump_path.empty()) {
    const std::optional<Tally> dumped = RunDump(options->dump_path);
    if (!dumped) {
      std::cerr << "cannot read dump file " << options->dump_path.string() << "\n";
      return 2;
    }
    tally = *dumped;
  } else {
    tally = RunGenerated(*options);
  }

  FamilyTally sum;
  for (const auto& [family, entry] : tally) sum.Add(entry);
  const std::string json = ToJson(tally, sum);
  if (!options->summary_path.empty()) std::ofstream(options->summary_path) << json;
  std::cout << json;

  const bool any_mismatch = sum.reference_mismatch + sum.fast_mismatch + sum.layout_mismatch > 0;
  std::cout << std::format(
      "{{\"ok\": {}, \"cases\": {}, \"fast_computed\": {}, \"fast_mismatch\": {}, "
      "\"reference_mismatch\": {}, \"layout_mismatch\": {}}}\n",
      any_mismatch ? "false" : "true", sum.cases, sum.outcome[0], sum.fast_mismatch,
      sum.reference_mismatch, sum.layout_mismatch);
  return any_mismatch ? 1 : 0;
}
