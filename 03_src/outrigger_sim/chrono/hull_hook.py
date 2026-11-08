"""Opt-in SCM convex-hull hook (``native/chrono_hull``, cpp-expert; contract in that folder's README).

``chrono_hull_hook.dll`` swaps the four ``ChConvexHull2D`` import slots of ``Chrono_vehicle.dll`` for a
bit-identical fast path. It is **off by default**: without the environment variable ``OUTRIGGER_HULL_HOOK``
(or with an empty value) :func:`install_from_env` does nothing at all (the DLL is not even loaded), so every
run without the variable is the former run.

Call order (README "호출 시점과 스레드"): ``import pychrono.vehicle`` first, then :func:`install_from_env`
before the first SCM step; :func:`stats_record` at the end of the run (the counters go into ``result.json``
``hull_hook`` only when the hook is active). A non-zero install status is printed and stops the process
(exit 2): a run that asked for the hook must not silently run without it.
"""

from __future__ import annotations

import ctypes
import hashlib
import os
import sys
from pathlib import Path

ENV_MODE = "OUTRIGGER_HULL_HOOK"
ENV_DLL = "OUTRIGGER_HULL_HOOK_DLL"
"""Optional DLL path override (default :data:`DLL_PATH`)."""
DLL_PATH = Path(__file__).resolve().parents[1] / "native" / "chrono_hull" / "bin" / "chrono_hull_hook.dll"
API_VERSION = 1
MODE_NAMES = {0: "off", 1: "fast", 2: "shadow", 3: "dump"}
FALLBACK_REASONS = ("none", "too_few_points", "not_lattice", "duplicate_points", "collinear_input",
                    "ambiguous_step", "loop_guard", "reserved7")
_COUNTERS = ("calls", "fast_computed", "fallback", "shadow_compared", "shadow_mismatch", "dumped_records",
             "non_jarvis_calls")


class HookStats(ctypes.Structure):
    _fields_ = [(n, ctypes.c_uint64) for n in _COUNTERS] + [("fallback_by_reason", ctypes.c_uint64 * 8)]


_state: dict = {"lib": None, "meta": None}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install_from_env(environ=None) -> dict | None:
    """Install the hook from ``OUTRIGGER_HULL_HOOK`` (README contract). Returns ``None`` when the variable is
    absent or empty (nothing loaded, nothing changed), else the install meta (mode, DLL path / SHA-256, env
    values). Idempotent within a process. Exits 2 on a non-zero install status."""
    env = os.environ if environ is None else environ
    value = (env.get(ENV_MODE) or "").strip()
    if not value:
        return None
    if _state["meta"] is not None:
        return _state["meta"]
    if "pychrono.vehicle" not in sys.modules:
        raise RuntimeError("hull hook: import pychrono.vehicle before install_from_env (Chrono_vehicle.dll)")
    dll = Path(env.get(ENV_DLL) or DLL_PATH).resolve()
    if not dll.is_file():
        print(f"hull hook: {ENV_MODE}={value!r} but the DLL is missing: {dll} (build.ps1)", flush=True)
        raise SystemExit(2)
    lib = ctypes.CDLL(str(dll))
    lib.chrono_hull_hook_status_string.restype = ctypes.c_char_p
    lib.chrono_hull_hook_status_string.argtypes = [ctypes.c_int]
    lib.chrono_hull_hook_install_from_env.restype = ctypes.c_int
    lib.chrono_hull_hook_mode.restype = ctypes.c_int
    lib.chrono_hull_hook_version.restype = ctypes.c_int
    lib.chrono_hull_hook_get_stats.restype = ctypes.c_int
    lib.chrono_hull_hook_get_stats.argtypes = [ctypes.POINTER(HookStats), ctypes.c_uint32]
    version = int(lib.chrono_hull_hook_version())
    if version != API_VERSION:
        print(f"hull hook: API version {version} != {API_VERSION} ({dll})", flush=True)
        raise SystemExit(2)
    status = int(lib.chrono_hull_hook_install_from_env())
    if status != 0:
        print(f"hull hook: install failed status {status} "
              f"{lib.chrono_hull_hook_status_string(status).decode()} ({ENV_MODE}={value!r})", flush=True)
        raise SystemExit(2)
    mode = int(lib.chrono_hull_hook_mode())
    meta = {"env": {k: env.get(k) for k in (ENV_MODE, "OUTRIGGER_HULL_HOOK_DUMP", "OUTRIGGER_HULL_HOOK_DUMP_EVERY",
                                           "OUTRIGGER_HULL_HOOK_DUMP_MAX", ENV_DLL)},
            "mode": MODE_NAMES.get(mode, str(mode)), "api_version": version, "dll": str(dll),
            "dll_sha256": _sha256(dll)}
    _state.update(lib=lib, meta=meta)
    print(f"hull hook: installed mode {meta['mode']} ({dll.name} {meta['dll_sha256'][:12]})", flush=True)
    return meta


def active() -> bool:
    return _state["lib"] is not None


def stats() -> dict | None:
    """Counters of the installed hook (``None`` when not installed)."""
    lib = _state["lib"]
    if lib is None:
        return None
    s = HookStats()
    status = int(lib.chrono_hull_hook_get_stats(ctypes.byref(s), ctypes.sizeof(HookStats)))
    if status != 0:
        return {"error": f"get_stats status {status} {lib.chrono_hull_hook_status_string(status).decode()}"}
    out = {n: int(getattr(s, n)) for n in _COUNTERS}
    out["fallback_by_reason"] = {FALLBACK_REASONS[i]: int(s.fallback_by_reason[i]) for i in range(8)
                                 if int(s.fallback_by_reason[i])}
    out["fallback_fraction"] = out["fallback"] / out["calls"] if out["calls"] else None
    return out


def stats_record() -> dict | None:
    """``result.json`` block ``hull_hook`` (install meta + counters) or ``None`` when the hook is off."""
    if _state["meta"] is None:
        return None
    return {**_state["meta"], "stats": stats()}
