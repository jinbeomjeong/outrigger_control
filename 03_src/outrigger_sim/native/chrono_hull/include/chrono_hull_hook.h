/* C API of chrono_hull_hook.dll.
 *
 * Replaces, inside the current process, the four chrono::utils::ChConvexHull2D
 * entry points that Chrono_vehicle.dll imports from Chrono_core.dll (constructor,
 * destructor, GetArea, GetPerimeter) with a bit-exact fast implementation.
 * Nothing changes until chrono_hull_hook_install() is called with a mode other
 * than OFF. See README.md for the full contract.
 *
 * Threading: call install/uninstall while no SCM step is running (for example
 * right after importing pychrono.vehicle, before creating SCMTerrain). Statistics
 * calls are safe at any time.
 */

#ifndef OUTRIGGER_CHRONO_HULL_HOOK_H_
#define OUTRIGGER_CHRONO_HULL_HOOK_H_

#include <stdint.h>
#include <wchar.h>

#ifdef CHRONO_HULL_HOOK_BUILD
#define CHRONO_HULL_HOOK_API __declspec(dllexport)
#else
#define CHRONO_HULL_HOOK_API __declspec(dllimport)
#endif

#ifdef __cplusplus
extern "C" {
#endif

/* Value of chrono_hull_hook_version(); bump on any contract change. */
#define CHRONO_HULL_HOOK_VERSION 1

typedef enum ChronoHullHookMode {
  CHRONO_HULL_HOOK_MODE_OFF = 0,    /* original Chrono code (hook removed) */
  CHRONO_HULL_HOOK_MODE_FAST = 1,   /* fast path, original as fallback */
  CHRONO_HULL_HOOK_MODE_SHADOW = 2, /* original result returned; fast path compared bit by bit */
  CHRONO_HULL_HOOK_MODE_DUMP = 3    /* original result returned; inputs sampled to the dump file */
} ChronoHullHookMode;

typedef enum ChronoHullHookStatus {
  CHRONO_HULL_HOOK_OK = 0,
  CHRONO_HULL_HOOK_ERR_BAD_MODE = -1,
  CHRONO_HULL_HOOK_ERR_MODULE_NOT_LOADED = -2,   /* Chrono_vehicle.dll or Chrono_core.dll */
  CHRONO_HULL_HOOK_ERR_HASH_MISMATCH = -3,       /* DLL files differ from the verified build */
  CHRONO_HULL_HOOK_ERR_IMPORT_NOT_FOUND = -4,    /* an expected import slot is missing */
  CHRONO_HULL_HOOK_ERR_IMPORT_NOT_ORIGINAL = -5, /* slot does not point at Chrono_core's export */
  CHRONO_HULL_HOOK_ERR_PROTECT = -6,             /* VirtualProtect failed */
  CHRONO_HULL_HOOK_ERR_DUMP_FILE = -7,           /* dump path missing or not writable (DUMP mode) */
  CHRONO_HULL_HOOK_ERR_ENV_VALUE = -8,           /* unrecognized OUTRIGGER_HULL_HOOK value */
  CHRONO_HULL_HOOK_ERR_STATS_SIZE = -9           /* struct size mismatch in get_stats */
} ChronoHullHookStatus;

/* Number of fallback reasons (FastHullOutcome values 1..6 are counted at their index). */
#define CHRONO_HULL_HOOK_REASON_COUNT 8

typedef struct ChronoHullHookStats {
  uint64_t calls;            /* constructor calls routed through the hook */
  uint64_t fast_computed;    /* fast path produced the result (FAST) or a comparison (SHADOW) */
  uint64_t fallback;         /* fast path declined; original used */
  uint64_t shadow_compared;  /* SHADOW comparisons made */
  uint64_t shadow_mismatch;  /* SHADOW comparisons with any bit difference */
  uint64_t dumped_records;   /* records written to the dump file */
  uint64_t non_jarvis_calls; /* method != JARVIS, always delegated to the original */
  uint64_t fallback_by_reason[CHRONO_HULL_HOOK_REASON_COUNT];
} ChronoHullHookStats;

CHRONO_HULL_HOOK_API int chrono_hull_hook_version(void);

/* Install (or change the mode of) the hook. MODE_OFF removes it. Returns a
 * ChronoHullHookStatus. On error the process is left unchanged. */
CHRONO_HULL_HOOK_API int chrono_hull_hook_install(int mode);

/* Read OUTRIGGER_HULL_HOOK (off|fast|shadow|dump; unset or empty = off) and the
 * related variables (README.md), then call chrono_hull_hook_install(). */
CHRONO_HULL_HOOK_API int chrono_hull_hook_install_from_env(void);

/* Restore the original import slots. Safe to call when not installed. */
CHRONO_HULL_HOOK_API int chrono_hull_hook_uninstall(void);

/* Current mode (OFF when not installed). */
CHRONO_HULL_HOOK_API int chrono_hull_hook_mode(void);

/* Dump file for SHADOW mismatches and DUMP sampling (UTF-16 path; NULL closes
 * the file). `every_nth` >= 1 samples every n-th call in DUMP mode;
 * `max_records` = 0 means unlimited. */
CHRONO_HULL_HOOK_API int chrono_hull_hook_set_dump(const wchar_t* path, uint64_t every_nth,
                                                   uint64_t max_records);

/* Copy the counters; `struct_size` must be sizeof(ChronoHullHookStats). */
CHRONO_HULL_HOOK_API int chrono_hull_hook_get_stats(ChronoHullHookStats* out, uint32_t struct_size);

CHRONO_HULL_HOOK_API void chrono_hull_hook_reset_stats(void);

/* Static ASCII text for a status code. */
CHRONO_HULL_HOOK_API const char* chrono_hull_hook_status_string(int status);

#ifdef __cplusplus
}
#endif

#endif /* OUTRIGGER_CHRONO_HULL_HOOK_H_ */
