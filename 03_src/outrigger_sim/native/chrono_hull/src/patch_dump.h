// Binary dump of convex-hull inputs (SCM contact patch points).
//
// File layout (little endian):
//   header : char magic[8] = "OHULLDMP", uint32 version = 1, uint32 reserved = 0
//   record : uint32 point_count, uint32 flags, then point_count * (double x, double y)
// `flags` is a PatchDumpFlag bit set. Records are appended; a file may be
// written by several runs one after another.

#pragma once

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <optional>
#include <vector>

#include "chrono/core/ChVector2.h"

namespace outrigger::hull {

enum PatchDumpFlag : std::uint32_t {
  kDumpSampled = 1u << 0,   ///< Written by the sampling dump mode.
  kDumpMismatch = 1u << 1,  ///< Shadow mode found a bit difference.
};

struct PatchRecord {
  std::uint32_t flags = 0;
  std::vector<chrono::ChVector2d> points;
};

/// Appends records to a dump file. Not thread-safe; the caller serializes.
class PatchDumpWriter {
 public:
  /// Opens `path` for appending and writes the header if the file is empty.
  /// Check is_open() afterwards.
  explicit PatchDumpWriter(const std::filesystem::path& path);

  [[nodiscard]] bool is_open() const { return stream_.is_open() && stream_.good(); }

  void Write(const std::vector<chrono::ChVector2d>& points, std::uint32_t flags);

 private:
  std::ofstream stream_;
};

/// Reads a whole dump file. Returns nullopt if the file is missing or malformed.
[[nodiscard]] std::optional<std::vector<PatchRecord>> ReadPatchDump(
    const std::filesystem::path& path);

}  // namespace outrigger::hull
