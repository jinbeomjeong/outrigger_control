"""Reference trajectory of a short sliding L1 case for the GroundBushingCoulomb adhesion regression.

Written 2026-10-26 with the ground-bushing code of commit 8616be9 (before the per-leg adhesion
argument of ``dynamics_model.md`` 5.33.7 #4). ``05_tests/chrono/test_ground_bushing_adhesion.py``
re-runs the same case with the current code (adhesion 0 = default, and adhesion passed
explicitly as 0) and compares every array with ``np.array_equal`` (bit identity).

Case (test assumption, not a project scenario): L1 four-leg model, top auger level, no crawler,
pads on the level floor at the operating extensions, gravity tilted so that the in-plane
component is 0.6 g (> mu 0.5): the pads slide (yield steps at the end FL 1013 / FR 1014 / RL 85 /
RR 84 of 1500), so the Coulomb limit path of the return mapping is exercised. 0.3 s at the YAML L1 dt (2e-4 s, 1500 steps).

Run (Chrono-dev, project root):
    C:\\ProgramData\\miniforge3\\envs\\Chrono-dev\\python.exe -I 05_tests/data/make_ground_bushing_l1_ref.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "03_src"))

import numpy as np  # noqa: E402

OUT = Path(__file__).resolve().parent / "ground_bushing_l1_slide_ref.npy"
"""float64 (steps, columns) array; column layout in the sibling ``.json`` (``*.npz`` is git-ignored)."""
OUT_LAYOUT = OUT.with_suffix(".json")
T_END_S = 0.3


def pack(data: dict[str, np.ndarray]) -> tuple[np.ndarray, dict]:
    """Flatten the per-step arrays into one float64 matrix (ints are exact in float64)."""
    n = len(next(iter(data.values())))
    cols, layout, start = [], {}, 0
    for key, arr in data.items():
        a = np.asarray(arr, dtype=float).reshape(n, -1)
        layout[key] = {"start": start, "stop": start + a.shape[1], "shape": list(np.asarray(arr).shape[1:]),
                       "dtype": str(np.asarray(arr).dtype)}
        start += a.shape[1]
        cols.append(a)
    return np.hstack(cols), layout


def unpack(matrix: np.ndarray, layout: dict) -> dict[str, np.ndarray]:
    out = {}
    for key, spec in layout.items():
        a = matrix[:, spec["start"]:spec["stop"]].reshape((len(matrix), *spec["shape"]))
        out[key] = a.astype(spec["dtype"])
    return out


def load_reference() -> dict[str, np.ndarray]:
    import json

    return unpack(np.load(OUT), json.loads(OUT_LAYOUT.read_text(encoding="utf-8"))["layout"])
LATERAL_G_FRACTION = 0.6


def run_case(adhesion: object = None) -> dict[str, np.ndarray]:
    """Run the case; ``adhesion`` None = constructor default, else passed to the pad specs."""
    import dataclasses

    from outrigger_sim.chrono.model import L1Model
    from outrigger_sim.chrono.system import set_gravity
    from outrigger_sim.params import load_params

    params = load_params(level="top")
    model = L1Model(params, crawler=False)
    if adhesion is not None:
        bushing = model.bushing
        bushing._pads = tuple(  # noqa: SLF001 - regression of the explicit-zero path
            dataclasses.replace(p, adhesion_N=float(a)) for p, a in zip(bushing._pads, adhesion)  # noqa: SLF001
        )
    g = params.meta.gravity_m_s2
    set_gravity(model.system, (LATERAL_G_FRACTION * g, 0.0, -g))
    rows: dict[str, list] = {"pos": [], "quat": [], "slip": [], "normal": [], "yield": [], "anchor": []}
    for _ in range(round(T_END_S / model.dt_s)):
        model.step()
        p = model.superstructure.GetPos()
        q = model.superstructure.GetRot()
        rows["pos"].append([p.x, p.y, p.z])
        rows["quat"].append([q.e0, q.e1, q.e2, q.e3])
        rows["slip"].append(model.bushing.slip_total_m)
        rows["normal"].append(model.bushing.normal_force_raw_N)
        rows["yield"].append(model.bushing.yield_steps)
        rows["anchor"].append(model.bushing.anchors_world_m())
    return {k: np.asarray(v) for k, v in rows.items()}


if __name__ == "__main__":
    import json

    data = run_case()
    matrix, layout = pack(data)
    np.save(OUT, matrix)
    OUT_LAYOUT.write_text(json.dumps({"generator": "05_tests/data/make_ground_bushing_l1_ref.py",
                                      "code": "ground_bushing.py of commit 8616be9 (before adhesion_N)",
                                      "layout": layout}, indent=1), encoding="utf-8")
    print(OUT, {k: v.shape for k, v in data.items()}, "yield steps end", data["yield"][-1])
