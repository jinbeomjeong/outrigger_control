#include "patch_dump.h"

#include <array>
#include <cstddef>
#include <system_error>
#include <utility>

namespace outrigger::hull {
namespace {

constexpr std::array<char, 8> kMagic = {'O', 'H', 'U', 'L', 'L', 'D', 'M', 'P'};
constexpr std::uint32_t kVersion = 1;

// Defensive upper bound for one record when reading (SCM patches are far smaller).
constexpr std::uint32_t kMaxPointsPerRecord = 50'000'000;

template <typename T>
void WriteValue(std::ofstream& stream, const T& value) {
  stream.write(reinterpret_cast<const char*>(&value), sizeof value);
}

template <typename T>
bool ReadValue(std::ifstream& stream, T& value) {
  stream.read(reinterpret_cast<char*>(&value), sizeof value);
  return static_cast<std::size_t>(stream.gcount()) == sizeof value;
}

}  // namespace

PatchDumpWriter::PatchDumpWriter(const std::filesystem::path& path) {
  std::error_code error;
  const bool is_empty =
      !std::filesystem::exists(path, error) || std::filesystem::file_size(path, error) == 0;
  stream_.open(path, std::ios::binary | std::ios::app);
  if (!stream_.is_open() || !is_empty) return;
  stream_.write(kMagic.data(), kMagic.size());
  WriteValue(stream_, kVersion);
  WriteValue(stream_, std::uint32_t{0});
  stream_.flush();
}

void PatchDumpWriter::Write(const std::vector<chrono::ChVector2d>& points, std::uint32_t flags) {
  WriteValue(stream_, static_cast<std::uint32_t>(points.size()));
  WriteValue(stream_, flags);
  for (const chrono::ChVector2d& point : points) {
    WriteValue(stream_, point.x());
    WriteValue(stream_, point.y());
  }
  stream_.flush();
}

std::optional<std::vector<PatchRecord>> ReadPatchDump(const std::filesystem::path& path) {
  std::ifstream stream(path, std::ios::binary);
  if (!stream.is_open()) return std::nullopt;

  std::array<char, 8> magic{};
  stream.read(magic.data(), magic.size());
  std::uint32_t version = 0;
  std::uint32_t reserved = 0;
  if (stream.gcount() != static_cast<std::streamsize>(magic.size()) || magic != kMagic ||
      !ReadValue(stream, version) || version != kVersion || !ReadValue(stream, reserved)) {
    return std::nullopt;
  }

  std::vector<PatchRecord> records;
  std::uint32_t point_count = 0;
  while (ReadValue(stream, point_count)) {
    PatchRecord record;
    if (point_count > kMaxPointsPerRecord || !ReadValue(stream, record.flags)) {
      return std::nullopt;
    }
    record.points.resize(point_count);
    for (chrono::ChVector2d& point : record.points) {
      double x = 0;
      double y = 0;
      if (!ReadValue(stream, x) || !ReadValue(stream, y)) return std::nullopt;
      point = chrono::ChVector2d(x, y);
    }
    records.push_back(std::move(record));
  }
  return records;
}

}  // namespace outrigger::hull
