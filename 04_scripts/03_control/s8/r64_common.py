"""Rev. 64 shared readers for the record-replay analyses (read only, no engine).

Every helper reads the files one Chrono case folder leaves (``record/record.npz``,
``r8_series.npz``, ``pads.npz``, ``controller_events.json``, ``result.json``).
Units: SI (N, Pa, s, m/s); force sums are cylinder net forces from the readings.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterator

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")
A_P = np.array([1.3273e-2, 1.3273e-2, 9.503e-3, 9.503e-3])  # head area [m2], spec 64.1
A_ANN = np.array([3.770e-3, 3.770e-3, 3.142e-3, 3.142e-3])  # annulus area [m2]
F_MIN_N = 9414.6
G = 9.80665
YAML_MASS_KG = 38400.8
LEVER_XY = (-0.150, 0.881)  # r_C1 x, y [m] (spec 219.2: (alpha x r)_z = 0.881 a_x + 0.150 a_y)
PERIOD_S = 0.1
_EVENT_RE = re.compile(r"t_s=([-0-9.eE+]+), name='([^']*)'")


def case_dirs(roots: list[str]) -> Iterator[Path]:
    """Folders under ``roots`` that hold ``record/record.npz`` (sorted, de-duplicated)."""
    seen = set()
    for root in roots:
        for rec in sorted(Path(root).rglob("record.npz")):
            if rec.parent.name != "record":
                continue
            case = rec.parent.parent
            key = str(case.resolve())
            if key not in seen:
                seen.add(key)
                yield case


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _walk(obj: Any) -> Iterator[Any]:
    yield obj
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def events(case: Path, result: Any | None = None) -> list[tuple[float, str]]:
    """Controller events as (t_s, name): ``controller_events.json`` strings, else every
    ``{"t_s", "name"}`` dict found in ``result.json``."""
    raw = load_json(case / "controller_events.json")
    out = []
    if raw:
        for e in raw:
            m = _EVENT_RE.search(str(e))
            if m:
                out.append((float(m.group(1)), m.group(2)))
        return out
    result = result if result is not None else load_json(case / "result.json")
    if result is None:
        return out
    for o in _walk(result):
        if isinstance(o, dict) and "t_s" in o and "name" in o and isinstance(o["name"], str):
            try:
                out.append((float(o["t_s"]), o["name"]))
            except (TypeError, ValueError):
                pass
    return sorted(set(out))


def find_key(result: Any, key: str) -> Any:
    for o in _walk(result):
        if isinstance(o, dict) and key in o:
            return o[key]
    return None


def phase_names(r8: Any) -> np.ndarray | None:
    if r8 is None or "phase" not in r8.files:
        return None
    return np.array([str(p).split(".")[-1].upper() for p in r8["phase"]])


def net_sum_N(head_Pa: np.ndarray, rod_Pa: np.ndarray) -> np.ndarray:
    return (head_Pa * A_P - rod_Pa * A_ANN).sum(axis=-1)


def imu_fz(r8: Any, rec: Any, lever: bool = True) -> np.ndarray:
    """Body-z specific force per controller sample: the last 10 ms partial mean (D1''),
    minus the C1 lever term from the last two gyro partial means; the record's period value
    when the partial means are missing."""
    if r8 is not None and "imu_samples" in r8.files:
        fz = np.array(r8["imu_samples"][:, -1, 2], dtype=float)
        if lever and "imu_gyro_samples" in r8.files:
            g = np.asarray(r8["imu_gyro_samples"], dtype=float)
            alpha = (g[:, -1, :2] - g[:, -2, :2]) / 0.01
            fz = fz - (alpha[:, 0] * LEVER_XY[1] - alpha[:, 1] * LEVER_XY[0])
        return fz
    return np.array(rec["meas.specific_force"][:, 2], dtype=float)
