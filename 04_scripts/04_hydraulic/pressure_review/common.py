"""Shared helpers of the pressure-dynamics review (read-only use of the project code)."""
from __future__ import annotations

import ctypes
import json
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
# intermediate Hopsan and numpy series: not results to keep in git
SCRATCH = ROOT / "07_results" / "03_hydraulic" / "pressure_review"
OUT = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review"
sys.path.insert(0, str(ROOT / "04_scripts" / "04_hydraulic" / "coupled"))
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, r"C:\Users\jinbeom\.claude\tools\hydraulics")

P_ATM = 1.0e5
AFFINITY_MASK = 0x0C000000  # two logical E cores (26, 27); children inherit


def pin_two_cores() -> None:
    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), AFFINITY_MASK)


class Hmf:
    """Minimal hand-written .hmf (agent memory hopsan-handmade-hmf)."""

    def __init__(self, name: str, t_end: float, ts: float):
        self.name, self.t_end, self.ts = name, t_end, ts
        self.objs: list[str] = []
        self.conns: list[tuple[str, str, str, str]] = []

    def comp(self, typename: str, name: str, params: dict | None = None) -> None:
        lines = [f'      <component typename="{typename}" name="{name}">', "        <parameters>"]
        for k, v in (params or {}).items():
            if isinstance(v, bool):
                val, typ = ("true" if v else "false"), "bool"
            elif isinstance(v, (int, np.integer)):
                val, typ = str(int(v)), "integer"
            elif isinstance(v, str):
                val, typ = v, "string"
            else:
                val, typ = repr(float(v)), "double"
            lines.append(f"          <parameter name={quoteattr(k)} value={quoteattr(val)} type=\"{typ}\"/>")
        lines += ["        </parameters>", "      </component>"]
        self.objs.append("\n".join(lines))

    def connect(self, c1: str, p1: str, c2: str, p2: str) -> None:
        self.conns.append((c1, p1, c2, p2))

    def lookup(self, folder: Path, name: str, t: np.ndarray, y: np.ndarray, target: str, port: str) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        rows = "\n".join(f"{a:.9g},{b:.12g}" for a, b in zip(t, y))
        (folder / f"{name}.csv").write_text(rows + "\n", encoding="ascii")
        self.comp("Signal1DLookupTable", name, {"in#Value": 0.0, "filename": f"{name}.csv", "csvsep": ",",
                                                "inid": 0, "outid": 1, "reload": True})
        self.connect("Clock", "out", name, "in")
        self.connect(name, "out", target, port)

    def write(self, path: Path, n_log: int) -> Path:
        con = "\n".join(f'      <connect startcomponent="{a}" startport="{b}" endcomponent="{c}" endport="{d}"/>'
                        for a, b, c, d in self.conns)
        text = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<hopsanmodelfile hmfversion="0.4" hopsanguiversion="0.7.x" hopsancoreversion="2.24.4">\n'
            "  <requirements>\n    <componentlibrary>HopsanDefaultComponentLibrary</componentlibrary>\n"
            "  </requirements>\n"
            f'  <system typename="Subsystem" name="{self.name}">\n'
            f'    <simulationtime stop="{self.t_end}" timestep="{self.ts}" start="0" inherit_timestep="true"/>\n'
            f'    <simulationlogsettings numsamples="{n_log}" starttime="0"/>\n'
            "    <parameters/>\n    <aliases/>\n    <objects>\n"
            + "\n".join(self.objs)
            + "\n    </objects>\n    <connections>\n" + con + "\n    </connections>\n  </system>\n"
            "</hopsanmodelfile>\n"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


def lag_series(t: np.ndarray, cmd: np.ndarray, tau: float) -> np.ndarray:
    """First-order spool lag of a sampled command (exact per grid step)."""
    out = np.zeros_like(cmd)
    for k in range(1, len(t)):
        keep = np.exp(-(t[k] - t[k - 1]) / tau) if tau > 0 else 0.0
        out[k] = cmd[k - 1] + (out[k - 1] - cmd[k - 1]) * keep
    return out


def dump(name: str, obj: dict) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(obj, indent=1, default=float), encoding="utf-8")
    return path
