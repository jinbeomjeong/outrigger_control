"""Process placement on the hybrid CPU of the simulation PC (engine independent).

``00_docs/03_chrono/chrono_build_plan.md`` section 4 and risk #24: on this PC (Intel
i7-14700, 8 P-cores + 12 E-cores) Windows runs a window-less child ``python.exe`` on the
E-cores and the Chrono step is about 2.5x slower. Long runs therefore pin themselves to the
fastest cores and switch the execution-speed power throttling (EcoQoS) off for their own
process. Nothing else (no system setting) is changed. Ported from
``04_scripts/02_chrono/solver_benchmark/step_cost_S0.py`` (``cpu_sets``, ``place_process``)
so that run scripts and the later runner (S6) share one implementation.

Off Windows every function is a no-op that reports what it did not do.
"""

from __future__ import annotations

import os
import sys
from typing import Any


def cpu_sets() -> list[dict[str, int]]:
    """Logical processors with their EfficiencyClass (``GetSystemCpuSetInformation``).

    Higher class = faster core (i7-14700: P-cores 1, E-cores 0). Empty off Windows.
    """
    if sys.platform != "win32":
        return []
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    fn = k32.GetSystemCpuSetInformation
    fn.argtypes = [
        ctypes.c_void_p,
        wintypes.ULONG,
        ctypes.POINTER(wintypes.ULONG),
        wintypes.HANDLE,
        wintypes.ULONG,
    ]
    fn.restype = wintypes.BOOL
    need = wintypes.ULONG(0)
    fn(None, 0, ctypes.byref(need), None, 0)
    buf = (ctypes.c_ubyte * need.value)()
    if not fn(buf, need.value, ctypes.byref(need), None, 0):
        return []
    raw = bytes(buf)
    out, off = [], 0
    while off < need.value:
        size = int.from_bytes(raw[off : off + 4], "little")
        kind = int.from_bytes(raw[off + 4 : off + 8], "little")
        if kind == 0:  # CpuSetInformation
            out.append(
                {
                    "id": int.from_bytes(raw[off + 8 : off + 12], "little"),
                    "group": int.from_bytes(raw[off + 12 : off + 14], "little"),
                    "logical": raw[off + 14],
                    "core": raw[off + 15],
                    "efficiency_class": raw[off + 18],
                }
            )
        off += size
    return out


MASK_ENV = {"pcore": "OUTRIGGER_PCORE_MASK", "ecore": "OUTRIGGER_ECORE_MASK"}
"""Optional affinity mask of a pool (``s9_batch run --p-mask / --e-mask``, 2026-11-13): an
integer (``0x00FF0000``) whose bits must lie inside that pool's logical processors. Unset or
empty = the whole pool (former behaviour)."""


def mask_hex(mask: int) -> str:
    """``0x%08X`` text of an affinity mask (the form batch.json and result.json record)."""
    return f"0x{int(mask):08X}"


def parse_mask(text: str) -> int:
    """Affinity mask from text (``0x..``, decimal or ``0b..``); must be > 0.

    Raises:
        ValueError: Not an integer or not positive.
    """
    try:
        mask = int(str(text).strip(), 0)
    except ValueError as e:
        raise ValueError(f"affinity mask {text!r} is not an integer (e.g. 0x00FF0000)") from e
    if mask <= 0:
        raise ValueError(f"affinity mask {text!r} must be > 0")
    return mask


def pool_logical(mode: str, sets: list[dict[str, int]] | None = None) -> list[int]:
    """Group-0 logical processors of the ``pcore`` (highest efficiency class) or ``ecore``
    (lowest) pool."""
    sets = cpu_sets() if sets is None else sets
    classes = sorted({s["efficiency_class"] for s in sets})
    if not classes:
        return []
    wanted = classes[-1] if mode == "pcore" else classes[0]
    return [s["logical"] for s in sets if s["efficiency_class"] == wanted and s["group"] == 0]


def pool_mask_override(
    mode: str, logical: list[int], environ=None
) -> tuple[int | None, str | None]:
    """(mask, raw env text) of :data:`MASK_ENV` for ``mode``; (None, None) when unset / empty
    or ``mode`` has none.

    Raises:
        ValueError: The mask is invalid or has bits outside ``logical`` (the pool).
    """
    env = os.environ if environ is None else environ
    key = MASK_ENV.get(mode)
    raw = env.get(key) if key else None
    if raw is None or not str(raw).strip():
        return None, None
    mask = parse_mask(raw)
    pool = 0
    for lp in logical:
        pool |= 1 << lp
    if mask & ~pool:
        raise ValueError(
            f"{key}={raw}: bits {mask_hex(mask & ~pool)} outside the {mode} pool {mask_hex(pool)}"
        )
    return mask, str(raw)


def process_affinity_mask() -> int | None:
    """Affinity mask of this process read back from the OS (``GetProcessAffinityMask``); None
    off Windows / on error."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.GetProcessAffinityMask.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_size_t),
        ctypes.POINTER(ctypes.c_size_t),
    ]
    k32.GetProcessAffinityMask.restype = wintypes.BOOL
    proc_mask, sys_mask = ctypes.c_size_t(0), ctypes.c_size_t(0)
    process = k32.GetCurrentProcess()
    if not k32.GetProcessAffinityMask(process, ctypes.byref(proc_mask), ctypes.byref(sys_mask)):
        return None
    return int(proc_mask.value)


def place_process(mode: str = "pcore") -> dict[str, Any]:
    """Pin this process: ``"pcore"`` (highest efficiency class), ``"ecore"``, ``"os"`` (none).

    For ``pcore`` / ``ecore`` the EcoQoS execution-speed throttling of this process is
    switched off as well (``SetProcessInformation`` ProcessPowerThrottling, state 0).

    With :data:`MASK_ENV` of the mode set, only the masked processors of the pool are used;
    the record then also has ``affinity_mask_env`` / ``affinity_mask_requested`` and the mask
    read back from the OS (``affinity_mask_process``, ``affinity_mask_ok``), and
    ``affinity_logical_processors`` lists the masked set. Without it the record and the
    placement are as before.

    Returns:
        What was done (JSON-ready), for the run metadata.

    Raises:
        ValueError: Unknown mode, or an invalid / out-of-pool mask (before any affinity
            change).
    """
    if mode not in ("pcore", "ecore", "os"):
        raise ValueError(f"unknown placement mode {mode!r}")
    info: dict[str, Any] = {"mode": mode}
    sets = cpu_sets()
    info["efficiency_classes"] = sorted({s["efficiency_class"] for s in sets})
    if mode == "os" or not sets:
        return info
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    process = k32.GetCurrentProcess()
    classes = info["efficiency_classes"]
    wanted = classes[-1] if mode == "pcore" else classes[0]
    logical = [s["logical"] for s in sets if s["efficiency_class"] == wanted and s["group"] == 0]
    override, raw = pool_mask_override(mode, logical)
    if override is not None:
        logical = [lp for lp in logical if override >> lp & 1]
    mask = 0
    for lp in logical:
        mask |= 1 << lp
    k32.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    k32.SetProcessAffinityMask.restype = wintypes.BOOL
    info["affinity_ok"] = bool(k32.SetProcessAffinityMask(process, mask))
    info["affinity_logical_processors"] = logical
    if override is not None:
        got = process_affinity_mask()
        info.update(
            affinity_mask_env=raw,
            affinity_mask_requested=mask_hex(override),
            affinity_mask_process=None if got is None else mask_hex(got),
            affinity_mask_ok=got == override,
        )

    class PowerThrottlingState(ctypes.Structure):
        _fields_ = [  # noqa: RUF012 - ctypes layout
            ("Version", wintypes.ULONG),
            ("ControlMask", wintypes.ULONG),
            ("StateMask", wintypes.ULONG),
        ]

    state = PowerThrottlingState(1, 0x1, 0x0)  # EXECUTION_SPEED controlled, throttling off
    k32.SetProcessInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    k32.SetProcessInformation.restype = wintypes.BOOL
    info["power_throttling_off_ok"] = bool(
        k32.SetProcessInformation(process, 4, ctypes.byref(state), ctypes.sizeof(state))
    )
    return info
