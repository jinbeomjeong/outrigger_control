// chrono_hull_hook.dll: routes Chrono_vehicle.dll's ChConvexHull2D calls through
// the bit-exact fast hull (see exact_fast_hull.h and README.md).
//
// Mechanism: Chrono_vehicle.dll calls the ChConvexHull2D constructor, destructor,
// GetArea and GetPerimeter through its import address table (IAT). Install
// rewrites those four slots to the functions below; uninstall restores them.
// Objects keep the exact memory layout of chrono::utils::ChConvexHull2D, so an
// object may be built by either implementation and destroyed by either one
// (both are /MD builds of the same MSVC STL and share the UCRT heap).

#include "chrono_hull_hook.h"

#include <windows.h>

#include <atomic>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <cwctype>
#include <filesystem>
#include <memory>
#include <mutex>
#include <new>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "chrono/core/ChVector2.h"
#include "chrono/utils/ChConvexHull.h"
#include "exact_fast_hull.h"
#include "import_slots.h"
#include "patch_dump.h"

namespace {

using chrono::ChVector2d;
namespace hull = outrigger::hull;

// ---------------------------------------------------------------------------
// Constants

constexpr char kCoreDllName[] = "Chrono_core.dll";
constexpr wchar_t kCoreDllNameW[] = L"Chrono_core.dll";
constexpr wchar_t kVehicleDllNameW[] = L"Chrono_vehicle.dll";

// Decorated names as exported by Chrono_core.dll (dumpbin /exports).
constexpr char kConstructorName[] =
    "??0ChConvexHull2D@utils@chrono@@QEAA@AEAV?$vector@V?$ChVector2@N@chrono@@"
    "V?$allocator@V?$ChVector2@N@chrono@@@std@@@std@@W4Method@012@@Z";
constexpr char kDestructorName[] = "??1ChConvexHull2D@utils@chrono@@QEAA@XZ";
constexpr char kGetAreaName[] = "?GetArea@ChConvexHull2D@utils@chrono@@QEBANXZ";
constexpr char kGetPerimeterName[] = "?GetPerimeter@ChConvexHull2D@utils@chrono@@QEBANXZ";

// SHA-256 of the conda pychrono 10.0.0 py312h418371c_1198 DLLs the hook was
// verified against. Another build may have a different object layout or code;
// the hook refuses to install there.
constexpr std::string_view kExpectedCoreSha256 =
    "889b0d9d20c93f4933faa94ea8757b25287780c20039cc406db7dae47fadd502";
constexpr std::string_view kExpectedVehicleSha256 =
    "8f4a843ecc9bd2e4d9e4ffb3e1d2da6e8704c4f66c4627568da6687b58b69f62";

constexpr int kJarvisMethod = chrono::utils::ChConvexHull2D::JARVIS;

// ---------------------------------------------------------------------------
// Object layout and function types

/// Same data members, in the same order, as chrono::utils::ChConvexHull2D.
struct ConvexHull2DLayout {
  std::vector<ChVector2d> hull;
  double perimeter = 0;
  double area = 0;
};
static_assert(sizeof(ConvexHull2DLayout) == sizeof(chrono::utils::ChConvexHull2D),
              "ChConvexHull2D layout changed; the hook would corrupt objects");

// On x64 a member function receives `this` as its first argument, and MSVC
// constructors return `this`; these free-function types match that ABI.
using ConstructorFn = ConvexHull2DLayout* (*)(ConvexHull2DLayout* self,
                                              std::vector<ChVector2d>& points, int method);
using DestructorFn = void (*)(ConvexHull2DLayout* self);
using GetterFn = double (*)(const ConvexHull2DLayout* self);

struct OriginalFunctions {
  ConstructorFn construct = nullptr;
  DestructorFn destroy = nullptr;
  GetterFn get_area = nullptr;
  GetterFn get_perimeter = nullptr;
};

struct ImportSlots {
  void** construct = nullptr;
  void** destroy = nullptr;
  void** get_area = nullptr;
  void** get_perimeter = nullptr;
};

// ---------------------------------------------------------------------------
// Process-wide state

struct Counters {
  std::atomic<std::uint64_t> calls{0};
  std::atomic<std::uint64_t> fast_computed{0};
  std::atomic<std::uint64_t> fallback{0};
  std::atomic<std::uint64_t> shadow_compared{0};
  std::atomic<std::uint64_t> shadow_mismatch{0};
  std::atomic<std::uint64_t> dumped_records{0};
  std::atomic<std::uint64_t> non_jarvis_calls{0};
  std::atomic<std::uint64_t> fallback_by_reason[CHRONO_HULL_HOOK_REASON_COUNT]{};
  std::atomic<std::uint64_t> dump_sample_counter{0};
};

struct DumpTarget {
  std::mutex mutex;
  std::unique_ptr<hull::PatchDumpWriter> writer;  // null = no dump file; guarded by mutex
  std::atomic<std::uint64_t> every_nth{1};        // read without the mutex by ConstructDump
  std::uint64_t max_records = 0;                  // 0 = unlimited; guarded by mutex
};

struct HookState {
  std::mutex install_mutex;
  bool installed = false;  // guarded by install_mutex
  ImportSlots slots;       // guarded by install_mutex
  // Written before the slots are patched and only cleared after they are
  // restored, so the hooked functions may read it without locking.
  OriginalFunctions original;
  std::atomic<int> mode{CHRONO_HULL_HOOK_MODE_OFF};
  Counters counters;
  DumpTarget dump;
};

HookState& State() {
  static HookState state;
  return state;
}

void Increment(std::atomic<std::uint64_t>& counter) {
  counter.fetch_add(1, std::memory_order_relaxed);
}

// ---------------------------------------------------------------------------
// Dumping and comparison

void WriteDumpRecord(const std::vector<ChVector2d>& points, std::uint32_t flags) {
  DumpTarget& dump = State().dump;
  const std::scoped_lock lock(dump.mutex);
  if (!dump.writer) return;
  Counters& counters = State().counters;
  if (dump.max_records != 0 &&
      counters.dumped_records.load(std::memory_order_relaxed) >= dump.max_records) {
    return;
  }
  dump.writer->Write(points, flags);
  Increment(counters.dumped_records);
}

bool SameBits(double a, double b) {
  return std::bit_cast<std::uint64_t>(a) == std::bit_cast<std::uint64_t>(b);
}

bool IsBitIdentical(const ConvexHull2DLayout& original, const hull::HullResult& fast) {
  if (!SameBits(original.perimeter, fast.perimeter) || !SameBits(original.area, fast.area) ||
      original.hull.size() != fast.hull.size()) {
    return false;
  }
  for (std::size_t i = 0; i < fast.hull.size(); ++i) {
    if (!SameBits(original.hull[i].x(), fast.hull[i].x()) ||
        !SameBits(original.hull[i].y(), fast.hull[i].y())) {
      return false;
    }
  }
  return true;
}

void CountFallback(hull::FastHullOutcome outcome) {
  Counters& counters = State().counters;
  Increment(counters.fallback);
  const auto reason = static_cast<std::size_t>(outcome);
  if (reason < CHRONO_HULL_HOOK_REASON_COUNT) Increment(counters.fallback_by_reason[reason]);
}

// ---------------------------------------------------------------------------
// Replacement entry points

ConvexHull2DLayout* ConstructFast(ConvexHull2DLayout* self, std::vector<ChVector2d>& points,
                                  int method) {
  hull::FastHullAttempt attempt = hull::TryComputeHullExact(points);
  if (attempt.outcome != hull::FastHullOutcome::kComputed) {
    CountFallback(attempt.outcome);
    return State().original.construct(self, points, method);
  }
  Increment(State().counters.fast_computed);
  return new (self) ConvexHull2DLayout{std::move(attempt.result.hull), attempt.result.perimeter,
                                       attempt.result.area};
}

ConvexHull2DLayout* ConstructShadow(ConvexHull2DLayout* self, std::vector<ChVector2d>& points,
                                    int method) {
  State().original.construct(self, points, method);
  const hull::FastHullAttempt attempt = hull::TryComputeHullExact(points);
  if (attempt.outcome != hull::FastHullOutcome::kComputed) {
    CountFallback(attempt.outcome);
    return self;
  }
  Counters& counters = State().counters;
  Increment(counters.fast_computed);
  Increment(counters.shadow_compared);
  if (!IsBitIdentical(*self, attempt.result)) {
    Increment(counters.shadow_mismatch);
    WriteDumpRecord(points, hull::kDumpMismatch);
  }
  return self;
}

ConvexHull2DLayout* ConstructDump(ConvexHull2DLayout* self, std::vector<ChVector2d>& points,
                                  int method) {
  State().original.construct(self, points, method);
  const std::uint64_t call_number =
      State().counters.dump_sample_counter.fetch_add(1, std::memory_order_relaxed);
  if (call_number % State().dump.every_nth.load(std::memory_order_relaxed) == 0) {
    WriteDumpRecord(points, hull::kDumpSampled);
  }
  return self;
}

ConvexHull2DLayout* HookedConstruct(ConvexHull2DLayout* self, std::vector<ChVector2d>& points,
                                    int method) {
  HookState& state = State();
  Increment(state.counters.calls);
  if (method != kJarvisMethod) {
    Increment(state.counters.non_jarvis_calls);
    return state.original.construct(self, points, method);
  }
  switch (state.mode.load(std::memory_order_relaxed)) {
    case CHRONO_HULL_HOOK_MODE_FAST:
      return ConstructFast(self, points, method);
    case CHRONO_HULL_HOOK_MODE_SHADOW:
      return ConstructShadow(self, points, method);
    case CHRONO_HULL_HOOK_MODE_DUMP:
      return ConstructDump(self, points, method);
    default:
      return state.original.construct(self, points, method);
  }
}

void HookedDestroy(ConvexHull2DLayout* self) { self->~ConvexHull2DLayout(); }

double HookedGetArea(const ConvexHull2DLayout* self) { return self->area; }

double HookedGetPerimeter(const ConvexHull2DLayout* self) { return self->perimeter; }

// ---------------------------------------------------------------------------
// Install / uninstall (callers hold install_mutex)

bool HasExpectedHash(HMODULE module, std::string_view expected) {
  const std::optional<std::filesystem::path> path = hull::ModulePath(module);
  if (!path) return false;
  const std::optional<std::string> actual = hull::FileSha256Hex(*path);
  return actual && *actual == expected;
}

struct SlotPlan {
  void** slot;
  void* original;
  void* replacement;
};

int RestoreSlotsLocked() {
  HookState& state = State();
  if (!state.installed) return CHRONO_HULL_HOOK_OK;
  const SlotPlan plans[] = {
      {state.slots.construct, reinterpret_cast<void*>(state.original.construct), nullptr},
      {state.slots.destroy, reinterpret_cast<void*>(state.original.destroy), nullptr},
      {state.slots.get_area, reinterpret_cast<void*>(state.original.get_area), nullptr},
      {state.slots.get_perimeter, reinterpret_cast<void*>(state.original.get_perimeter), nullptr},
  };
  int status = CHRONO_HULL_HOOK_OK;
  for (const SlotPlan& plan : plans) {
    if (!hull::WriteImportSlot(plan.slot, plan.original)) status = CHRONO_HULL_HOOK_ERR_PROTECT;
  }
  state.installed = false;
  state.mode.store(CHRONO_HULL_HOOK_MODE_OFF);
  // `original` stays valid: Chrono_core.dll is still loaded, and a call that
  // entered a hooked function just before the restore may still use it.
  return status;
}

int PatchSlotsLocked(int mode) {
  HookState& state = State();
  const HMODULE vehicle = GetModuleHandleW(kVehicleDllNameW);
  const HMODULE core = GetModuleHandleW(kCoreDllNameW);
  if (vehicle == nullptr || core == nullptr) return CHRONO_HULL_HOOK_ERR_MODULE_NOT_LOADED;
  if (!HasExpectedHash(core, kExpectedCoreSha256) ||
      !HasExpectedHash(vehicle, kExpectedVehicleSha256)) {
    return CHRONO_HULL_HOOK_ERR_HASH_MISMATCH;
  }

  const char* const names[] = {kConstructorName, kDestructorName, kGetAreaName, kGetPerimeterName};
  void* const replacements[] = {
      reinterpret_cast<void*>(&HookedConstruct), reinterpret_cast<void*>(&HookedDestroy),
      reinterpret_cast<void*>(&HookedGetArea), reinterpret_cast<void*>(&HookedGetPerimeter)};
  SlotPlan plans[4]{};
  for (int i = 0; i < 4; ++i) {
    void** slot = hull::FindImportSlot(vehicle, kCoreDllName, names[i]);
    if (slot == nullptr) return CHRONO_HULL_HOOK_ERR_IMPORT_NOT_FOUND;
    void* exported = reinterpret_cast<void*>(GetProcAddress(core, names[i]));
    if (exported == nullptr || *slot != exported) return CHRONO_HULL_HOOK_ERR_IMPORT_NOT_ORIGINAL;
    plans[i] = {slot, exported, replacements[i]};
  }

  state.original = {reinterpret_cast<ConstructorFn>(plans[0].original),
                    reinterpret_cast<DestructorFn>(plans[1].original),
                    reinterpret_cast<GetterFn>(plans[2].original),
                    reinterpret_cast<GetterFn>(plans[3].original)};
  state.slots = {plans[0].slot, plans[1].slot, plans[2].slot, plans[3].slot};
  state.mode.store(mode);

  for (int i = 0; i < 4; ++i) {
    if (!hull::WriteImportSlot(plans[i].slot, plans[i].replacement)) {
      for (int j = 0; j < i; ++j) {
        // Best effort: put back what was already patched.
        static_cast<void>(hull::WriteImportSlot(plans[j].slot, plans[j].original));
      }
      state.mode.store(CHRONO_HULL_HOOK_MODE_OFF);
      return CHRONO_HULL_HOOK_ERR_PROTECT;
    }
  }
  state.installed = true;
  return CHRONO_HULL_HOOK_OK;
}

bool IsValidMode(int mode) {
  return mode >= CHRONO_HULL_HOOK_MODE_OFF && mode <= CHRONO_HULL_HOOK_MODE_DUMP;
}

bool HasDumpWriter() {
  DumpTarget& dump = State().dump;
  const std::scoped_lock lock(dump.mutex);
  return dump.writer != nullptr;
}

// ---------------------------------------------------------------------------
// Environment variables

std::optional<std::wstring> ReadEnvironment(const wchar_t* name) {
  const DWORD length = GetEnvironmentVariableW(name, nullptr, 0);
  if (length == 0) return std::nullopt;
  std::wstring value(length, L'\0');
  const DWORD written = GetEnvironmentVariableW(name, value.data(), length);
  value.resize(written);
  return value;
}

std::optional<int> ParseMode(std::wstring value) {
  for (wchar_t& c : value) c = static_cast<wchar_t>(std::towlower(c));
  if (value.empty() || value == L"off" || value == L"0") return CHRONO_HULL_HOOK_MODE_OFF;
  if (value == L"fast") return CHRONO_HULL_HOOK_MODE_FAST;
  if (value == L"shadow") return CHRONO_HULL_HOOK_MODE_SHADOW;
  if (value == L"dump") return CHRONO_HULL_HOOK_MODE_DUMP;
  return std::nullopt;
}

std::optional<std::uint64_t> ReadUnsignedEnvironment(const wchar_t* name,
                                                     std::uint64_t default_value) {
  const std::optional<std::wstring> text = ReadEnvironment(name);
  if (!text || text->empty()) return default_value;
  std::uint64_t value = 0;
  for (const wchar_t c : *text) {
    if (c < L'0' || c > L'9') return std::nullopt;
    value = value * 10 + static_cast<std::uint64_t>(c - L'0');
  }
  return value;
}

}  // namespace

// ---------------------------------------------------------------------------
// C API

extern "C" {

int chrono_hull_hook_version(void) { return CHRONO_HULL_HOOK_VERSION; }

int chrono_hull_hook_install(int mode) {
  if (!IsValidMode(mode)) return CHRONO_HULL_HOOK_ERR_BAD_MODE;
  HookState& state = State();
  const std::scoped_lock lock(state.install_mutex);
  if (mode == CHRONO_HULL_HOOK_MODE_OFF) return RestoreSlotsLocked();
  if (mode == CHRONO_HULL_HOOK_MODE_DUMP && !HasDumpWriter()) {
    return CHRONO_HULL_HOOK_ERR_DUMP_FILE;
  }
  if (state.installed) {
    state.mode.store(mode);
    return CHRONO_HULL_HOOK_OK;
  }
  return PatchSlotsLocked(mode);
}

int chrono_hull_hook_install_from_env(void) {
  const std::optional<std::wstring> mode_text = ReadEnvironment(L"OUTRIGGER_HULL_HOOK");
  const std::optional<int> mode = ParseMode(mode_text.value_or(L""));
  if (!mode) return CHRONO_HULL_HOOK_ERR_ENV_VALUE;

  const std::optional<std::wstring> dump_path = ReadEnvironment(L"OUTRIGGER_HULL_HOOK_DUMP");
  if (dump_path && !dump_path->empty()) {
    const std::optional<std::uint64_t> every =
        ReadUnsignedEnvironment(L"OUTRIGGER_HULL_HOOK_DUMP_EVERY", 1);
    const std::optional<std::uint64_t> max_records =
        ReadUnsignedEnvironment(L"OUTRIGGER_HULL_HOOK_DUMP_MAX", 0);
    if (!every || !max_records) return CHRONO_HULL_HOOK_ERR_ENV_VALUE;
    const int status = chrono_hull_hook_set_dump(dump_path->c_str(), *every, *max_records);
    if (status != CHRONO_HULL_HOOK_OK) return status;
  }
  return chrono_hull_hook_install(*mode);
}

int chrono_hull_hook_uninstall(void) {
  HookState& state = State();
  const std::scoped_lock lock(state.install_mutex);
  return RestoreSlotsLocked();
}

int chrono_hull_hook_mode(void) { return State().mode.load(); }

int chrono_hull_hook_set_dump(const wchar_t* path, uint64_t every_nth, uint64_t max_records) {
  DumpTarget& dump = State().dump;
  const std::scoped_lock lock(dump.mutex);
  if (path == nullptr) {
    dump.writer.reset();
    return CHRONO_HULL_HOOK_OK;
  }
  auto writer = std::make_unique<hull::PatchDumpWriter>(std::filesystem::path(path));
  if (!writer->is_open()) return CHRONO_HULL_HOOK_ERR_DUMP_FILE;
  dump.writer = std::move(writer);
  dump.every_nth.store(every_nth == 0 ? 1 : every_nth);
  dump.max_records = max_records;
  return CHRONO_HULL_HOOK_OK;
}

int chrono_hull_hook_get_stats(ChronoHullHookStats* out, uint32_t struct_size) {
  if (out == nullptr || struct_size != sizeof(ChronoHullHookStats)) {
    return CHRONO_HULL_HOOK_ERR_STATS_SIZE;
  }
  const Counters& counters = State().counters;
  out->calls = counters.calls.load();
  out->fast_computed = counters.fast_computed.load();
  out->fallback = counters.fallback.load();
  out->shadow_compared = counters.shadow_compared.load();
  out->shadow_mismatch = counters.shadow_mismatch.load();
  out->dumped_records = counters.dumped_records.load();
  out->non_jarvis_calls = counters.non_jarvis_calls.load();
  for (int i = 0; i < CHRONO_HULL_HOOK_REASON_COUNT; ++i) {
    out->fallback_by_reason[i] = counters.fallback_by_reason[i].load();
  }
  return CHRONO_HULL_HOOK_OK;
}

void chrono_hull_hook_reset_stats(void) {
  Counters& counters = State().counters;
  counters.calls = 0;
  counters.fast_computed = 0;
  counters.fallback = 0;
  counters.shadow_compared = 0;
  counters.shadow_mismatch = 0;
  counters.dumped_records = 0;
  counters.non_jarvis_calls = 0;
  for (auto& reason : counters.fallback_by_reason) reason = 0;
  counters.dump_sample_counter = 0;
}

const char* chrono_hull_hook_status_string(int status) {
  switch (status) {
    case CHRONO_HULL_HOOK_OK:
      return "ok";
    case CHRONO_HULL_HOOK_ERR_BAD_MODE:
      return "bad_mode";
    case CHRONO_HULL_HOOK_ERR_MODULE_NOT_LOADED:
      return "module_not_loaded";
    case CHRONO_HULL_HOOK_ERR_HASH_MISMATCH:
      return "hash_mismatch";
    case CHRONO_HULL_HOOK_ERR_IMPORT_NOT_FOUND:
      return "import_not_found";
    case CHRONO_HULL_HOOK_ERR_IMPORT_NOT_ORIGINAL:
      return "import_not_original";
    case CHRONO_HULL_HOOK_ERR_PROTECT:
      return "protect_failed";
    case CHRONO_HULL_HOOK_ERR_DUMP_FILE:
      return "dump_file";
    case CHRONO_HULL_HOOK_ERR_ENV_VALUE:
      return "env_value";
    case CHRONO_HULL_HOOK_ERR_STATS_SIZE:
      return "stats_size";
    default:
      return "unknown";
  }
}

}  // extern "C"

// Restore the import slots if the DLL is unloaded with FreeLibrary while
// Chrono_vehicle.dll stays loaded; otherwise its slots would point at unmapped
// code. At process exit (reserved != nullptr) nothing is called any more.
BOOL WINAPI DllMain(HINSTANCE /*instance*/, DWORD reason, LPVOID reserved) {
  if (reason == DLL_PROCESS_DETACH && reserved == nullptr) {
    static_cast<void>(chrono_hull_hook_uninstall());
  }
  return TRUE;
}
