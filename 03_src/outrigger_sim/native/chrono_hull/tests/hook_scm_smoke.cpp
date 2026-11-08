// End-to-end smoke test of chrono_hull_hook.dll inside a real SCMTerrain run
// (conda Chrono_core/Chrono_vehicle DLLs, no Python).
//
// Four pad-like boxes settle onto a flat SCM patch. The program prints the hook
// counters and a hash of every body state bit after the run, so runs in modes
// "off" and "fast" can be compared for bit identity.
//
// Usage: hook_scm_smoke MODE STEPS [DUMP_FILE]
//   MODE = off | fast | shadow | dump   (dump needs DUMP_FILE)

#include <bit>
#include <cstdint>
#include <cstdlib>
#include <format>
#include <iostream>
#include <memory>
#include <numbers>
#include <string>
#include <string_view>
#include <vector>

#include "chrono/core/ChRotation.h"
#include "chrono/physics/ChBodyEasy.h"
#include "chrono/physics/ChContactMaterialSMC.h"
#include "chrono/physics/ChSystemSMC.h"
#include "chrono_hull_hook.h"
#include "chrono_vehicle/terrain/SCMTerrain.h"

namespace {

constexpr double kStepSize_s = 1e-4;  // same as the project's L2b/S9 runs
constexpr double kGridSpacing_m = 0.01;
constexpr double kPadThickness_m = 0.1;
constexpr double kPadDensity_kg_m3 = 2.0e5;  // ~2 t per pad: visible sinkage

struct PadSpec {
  double side_m;
  double x_m;
  double y_m;
  double yaw_deg;
};

constexpr PadSpec kPads[] = {{0.33, -0.8, -0.8, 0.0},
                             {0.33, 0.8, -0.8, 10.0},
                             {0.25, -0.8, 0.8, 30.0},
                             {0.25, 0.8, 0.8, 45.0}};

int ParseMode(std::string_view text) {
  if (text == "off") return CHRONO_HULL_HOOK_MODE_OFF;
  if (text == "fast") return CHRONO_HULL_HOOK_MODE_FAST;
  if (text == "shadow") return CHRONO_HULL_HOOK_MODE_SHADOW;
  if (text == "dump") return CHRONO_HULL_HOOK_MODE_DUMP;
  return -1;
}

/// FNV-1a over raw double bits.
class StateHash {
 public:
  void Add(double number) {
    const auto bits = std::bit_cast<std::uint64_t>(number);
    for (int byte = 0; byte < 8; ++byte) {
      hash_ ^= (bits >> (8 * byte)) & 0xFF;
      hash_ *= 0x100000001B3ULL;
    }
  }
  void Add(const chrono::ChVector3d& v) {
    Add(v.x());
    Add(v.y());
    Add(v.z());
  }
  [[nodiscard]] std::uint64_t value() const { return hash_; }

 private:
  std::uint64_t hash_ = 0xCBF29CE484222325ULL;
};

}  // namespace

int main(int argc, char** argv) {
  if (argc < 3 || ParseMode(argv[1]) < 0) {
    std::cerr << "usage: hook_scm_smoke off|fast|shadow|dump STEPS [DUMP_FILE]\n";
    return 2;
  }
  const int mode = ParseMode(argv[1]);
  const int steps = std::atoi(argv[2]);

  if (argc > 3) {
    const std::wstring dump_path(argv[3], argv[3] + std::char_traits<char>::length(argv[3]));
    const int status = chrono_hull_hook_set_dump(dump_path.c_str(), 1, 0);
    if (status != CHRONO_HULL_HOOK_OK) {
      std::cerr << "set_dump: " << chrono_hull_hook_status_string(status) << "\n";
      return 2;
    }
  }
  const int install_status = chrono_hull_hook_install(mode);
  std::cout << std::format("install({}) = {}\n", argv[1],
                           chrono_hull_hook_status_string(install_status));
  if (install_status != CHRONO_HULL_HOOK_OK) return 2;

  chrono::ChSystemSMC system;
  system.SetCollisionSystemType(chrono::ChCollisionSystem::Type::BULLET);
  system.SetGravitationalAcceleration(chrono::ChVector3d(0, 0, -9.81));

  chrono::vehicle::SCMTerrain terrain(&system, false);
  terrain.SetSoilParameters(2e6, 0, 1.1, 0, 30, 0.01, 4e7, 3e4);
  terrain.Initialize(4.0, 4.0, kGridSpacing_m);

  auto material = chrono_types::make_shared<chrono::ChContactMaterialSMC>();
  std::vector<std::shared_ptr<chrono::ChBodyEasyBox>> pads;
  for (const PadSpec& spec : kPads) {
    auto pad = chrono_types::make_shared<chrono::ChBodyEasyBox>(
        spec.side_m, spec.side_m, kPadThickness_m, kPadDensity_kg_m3, false, true, material);
    pad->SetPos(chrono::ChVector3d(spec.x_m, spec.y_m, 0.5 * kPadThickness_m + 0.002));
    pad->SetRot(chrono::QuatFromAngleZ(spec.yaw_deg * std::numbers::pi / 180));
    system.AddBody(pad);
    terrain.AddActiveDomain(pad, chrono::VNULL,
                            chrono::ChVector3d(spec.side_m * 1.5, spec.side_m * 1.5, 0.5));
    pads.push_back(pad);
  }

  for (int k = 0; k < steps; ++k) {
    terrain.Synchronize(system.GetChTime());
    system.DoStepDynamics(kStepSize_s);
    terrain.Advance(kStepSize_s);
  }

  StateHash hash;
  for (const auto& pad : pads) {
    hash.Add(pad->GetPos());
    hash.Add(pad->GetPosDt());
    hash.Add(pad->GetRot().GetCardanAnglesXYZ());
  }
  ChronoHullHookStats stats{};
  chrono_hull_hook_get_stats(&stats, sizeof stats);
  std::cout << std::format(
      "{{\"mode\": \"{}\", \"steps\": {}, \"state_hash\": \"{:016x}\", \"patches_last_step\": {}, "
      "\"z_pad0\": {:.17g}, \"calls\": {}, \"fast_computed\": {}, \"fallback\": {}, "
      "\"shadow_compared\": {}, \"shadow_mismatch\": {}, \"dumped\": {}, \"fallback_by_reason\": "
      "[{}, {}, {}, {}, {}, {}, {}]}}\n",
      argv[1], steps, hash.value(), terrain.GetNumContactPatches(), pads[0]->GetPos().z(),
      stats.calls, stats.fast_computed, stats.fallback, stats.shadow_compared,
      stats.shadow_mismatch, stats.dumped_records, stats.fallback_by_reason[0],
      stats.fallback_by_reason[1], stats.fallback_by_reason[2], stats.fallback_by_reason[3],
      stats.fallback_by_reason[4], stats.fallback_by_reason[5], stats.fallback_by_reason[6]);
  chrono_hull_hook_uninstall();
  return stats.shadow_mismatch == 0 ? 0 : 1;
}
