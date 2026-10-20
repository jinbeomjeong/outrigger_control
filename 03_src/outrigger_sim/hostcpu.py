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


def place_process(mode: str = "pcore") -> dict[str, Any]:
    """Pin this process: ``"pcore"`` (highest efficiency class), ``"ecore"``, ``"os"`` (none).

    For ``pcore`` / ``ecore`` the EcoQoS execution-speed throttling of this process is
    switched off as well (``SetProcessInformation`` ProcessPowerThrottling, state 0).

    Returns:
        What was done (JSON-ready), for the run metadata.
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
    mask = 0
    for lp in logical:
        mask |= 1 << lp
    k32.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    k32.SetProcessAffinityMask.restype = wintypes.BOOL
    info["affinity_ok"] = bool(k32.SetProcessAffinityMask(process, mask))
    info["affinity_logical_processors"] = logical

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
