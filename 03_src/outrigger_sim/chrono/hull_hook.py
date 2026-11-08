"""SCM convex-hull hook (``native/chrono_hull``, cpp-expert; contract in that folder's README).

``chrono_hull_hook.dll`` swaps the four ``ChConvexHull2D`` import slots of ``Chrono_vehicle.dll`` for a
bit-identical fast path (G-A: 0 bit mismatches; G-C: representative SCM npz bit-identical; G-D: median wall
1203.2 s off / 929.0 s fast = 1.30x).

Mode selection (adopted 2026-11-09, user pre-approval "G-D median speed ratio >= 1.2 -> fast by default"):

* ``OUTRIGGER_HULL_HOOK`` absent or empty -> **default** :data:`DEFAULT_MODE` (``fast``). If the DLL is missing
  or refuses to install (e.g. ``hash_mismatch`` after a pychrono update), the run falls back to ``off``
  (original Chrono code; results are the same bits, only slower), prints a warning and records
  ``fallback_reason`` in ``result.json`` ``hull_hook``.
* ``OUTRIGGER_HULL_HOOK=off`` -> nothing is loaded or changed (the former default; use it to undo the switch).
* ``OUTRIGGER_HULL_HOOK=fast|shadow|dump`` (explicit) -> strict: a missing DLL or a non-zero install status
  prints the reason and stops the process (exit 2); a run that asked for the hook must not silently run
  without it.

Call order (README "호출 시점과 스레드"): ``import pychrono.vehicle`` first, then :func:`install_from_env`
before the first SCM step; :func:`stats_record` at the end of the run (``result.json`` ``hull_hook``: the
resolved mode, its source and, when the DLL is installed, the counters).
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
DEFAULT_MODE = "fast"
"""Mode when ``OUTRIGGER_HULL_HOOK`` is unset (2026-11-09; ``off`` before)."""
API_VERSION = 1
MODE_NAMES = {0: "off", 1: "fast", 2: "shadow", 3: "dump"}
MODE_CODES = {v: k for k, v in MODE_NAMES.items()}
FALLBACK_REASONS = ("none", "too_few_points", "not_lattice", "duplicate_points", "collinear_input",
                    "ambiguous_step", "loop_guard", "reserved7")
_COUNTERS = ("calls", "fast_computed", "fallback", "shadow_compared", "shadow_mismatch", "dumped_records",
             "non_jarvis_calls")
_ENV_KEYS = (ENV_MODE, "OUTRIGGER_HULL_HOOK_DUMP", "OUTRIGGER_HULL_HOOK_DUMP_EVERY", "OUTRIGGER_HULL_HOOK_DUMP_MAX",
             ENV_DLL)


class HookStats(ctypes.Structure):
    _fields_ = [(n, ctypes.c_uint64) for n in _COUNTERS] + [("fallback_by_reason", ctypes.c_uint64 * 8)]


_state: dict = {"lib": None, "meta": None}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def requested_mode(environ=None) -> tuple[str, str]:
    """``(mode, source)`` asked for by the environment: ``source`` ``"env"`` (explicit value, lower-cased; not
    validated here) or ``"default"`` (unset / empty -> :data:`DEFAULT_MODE`). No DLL is touched."""
    env = os.environ if environ is None else environ
    value = (env.get(ENV_MODE) or "").strip().lower()
    return (value, "env") if value else (DEFAULT_MODE, "default")


def _fail(msg: str, source: str, meta: dict) -> dict:
    """Explicit request -> exit 2; default request -> fall back to off (process unchanged) and record why."""
    if source == "env":
        print(f"hull hook: {msg}", flush=True)
        raise SystemExit(2)
    print(f"hull hook: WARNING default {DEFAULT_MODE} not installed ({msg}); running with the original Chrono "
          f"code (off). Set {ENV_MODE}=off to silence, or build native/chrono_hull (build.ps1).", flush=True)
    meta.update(mode="off", fallback_reason=msg)
    _state.update(lib=None, meta=meta)
    return meta


def install_from_env(environ=None) -> dict:
    """Install the hook as :func:`requested_mode` says and return the meta (``mode`` = effective mode,
    ``requested``, ``source``, ``fallback_reason``, env values, DLL path / SHA-256 when loaded). Idempotent
    within a process (the first call decides)."""
    if _state["meta"] is not None:
        return _state["meta"]
    env = os.environ if environ is None else environ
    req, source = requested_mode(env)
    meta: dict = {"mode": None, "requested": req, "source": source, "default_mode": DEFAULT_MODE,
                  "fallback_reason": None, "env": {k: env.get(k) for k in _ENV_KEYS},
                  "api_version": None, "dll": None, "dll_sha256": None}
    if req not in MODE_CODES:
        print(f"hull hook: {ENV_MODE}={env.get(ENV_MODE)!r} is not one of {sorted(MODE_CODES)}", flush=True)
        raise SystemExit(2)
    if req == "off":  # nothing loaded, nothing changed (the pre-2026-11-09 default run)
        meta["mode"] = "off"
        _state.update(lib=None, meta=meta)
        return meta
    if "pychrono.vehicle" not in sys.modules:
        raise RuntimeError("hull hook: import pychrono.vehicle before install_from_env (Chrono_vehicle.dll)")
    dll = Path(env.get(ENV_DLL) or DLL_PATH).resolve()
    meta["dll"] = str(dll)
    if not dll.is_file():
        return _fail(f"DLL missing: {dll} (build.ps1)", source, meta)
    meta["dll_sha256"] = _sha256(dll)
    lib = ctypes.CDLL(str(dll))
    lib.chrono_hull_hook_status_string.restype = ctypes.c_char_p
    lib.chrono_hull_hook_status_string.argtypes = [ctypes.c_int]
    lib.chrono_hull_hook_install.restype = ctypes.c_int
    lib.chrono_hull_hook_install.argtypes = [ctypes.c_int]
    lib.chrono_hull_hook_install_from_env.restype = ctypes.c_int
    lib.chrono_hull_hook_mode.restype = ctypes.c_int
    lib.chrono_hull_hook_version.restype = ctypes.c_int
    lib.chrono_hull_hook_get_stats.restype = ctypes.c_int
    lib.chrono_hull_hook_get_stats.argtypes = [ctypes.POINTER(HookStats), ctypes.c_uint32]
    version = int(lib.chrono_hull_hook_version())
    meta["api_version"] = version
    if version != API_VERSION:
        return _fail(f"API version {version} != {API_VERSION} ({dll})", source, meta)
    # explicit: the DLL reads the process env itself (dump path / every / max); default: install(fast) directly
    status = int(lib.chrono_hull_hook_install_from_env()) if source == "env" \
        else int(lib.chrono_hull_hook_install(MODE_CODES[DEFAULT_MODE]))
    if status != 0:
        return _fail(f"install failed status {status} {lib.chrono_hull_hook_status_string(status).decode()} "
                     f"(requested {req}, {source})", source, meta)
    mode = int(lib.chrono_hull_hook_mode())
    meta["mode"] = MODE_NAMES.get(mode, str(mode))
    _state.update(lib=lib, meta=meta)
    print(f"hull hook: installed mode {meta['mode']} ({source}; {dll.name} {meta['dll_sha256'][:12]})", flush=True)
    return meta


def active() -> bool:
    """True when the DLL is installed (any mode it reports, incl. shadow / dump)."""
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
    """``result.json`` block ``hull_hook`` (resolved mode + install meta + counters; ``stats`` is ``None`` when
    the DLL is not installed) or ``None`` when :func:`install_from_env` never ran in this process (no SCM
    model imported)."""
    if _state["meta"] is None:
        return None
    return {**_state["meta"], "stats": stats()}
