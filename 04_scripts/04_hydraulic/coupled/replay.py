"""Replay a Chrono run record through the shared-pump circuit (numpy model, prescribed loads).

Inputs from <case>/record/record.npz: t, u_applied (plant speed after the +-v_max clip,
actuation.py:226; sampled 10 Hz, linear interpolation here), F_cyl, stroke_true.
Output: leg speeds under the shared pump and the speed/stroke difference to the record.
Loads stay as recorded (no feedback of the speed difference on the mechanics); closing
that loop is the Chrono integration, outside this stage.

usage: replay.py <case dir> [--eta 0.90] [--t0 8.1] [--t1 30] [--dt 1e-4] [--out path.csv]
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

from model import simulate, write_csv  # noqa: E402
from params import LEGS, OUT_DIR, Params, load_params  # noqa: E402


@dataclass
class Replay:
    case: Path
    eta_v: float
    t_start: float
    t_end: float
    t: np.ndarray
    v_cmd: np.ndarray
    F: np.ndarray
    s: np.ndarray
    coupled: bool = False

    def s_start(self, p: Params) -> np.ndarray:
        return np.array([np.interp(self.t_start, self.t, self.s[:, i]) for i in range(4)])

    def load_fn(self, p: Params):
        return lambda t: np.array([np.interp(t, self.t, self.F[:, i]) for i in range(4)])

    def command_fn(self, p: Params):
        return lambda t: np.array([np.interp(t, self.t, self.v_cmd[:, i]) for i in range(4)]) / p.v_max


def load_replay(case: Path, eta_v: float, t0: float | None = None, t1: float | None = None) -> Replay:
    with np.load(case / "record" / "record.npz", allow_pickle=True) as d:
        t = np.asarray(d["t"], float)
        return Replay(case, eta_v, float(t[0] if t0 is None else t0), float(t[-1] if t1 is None else t1), t,
                      np.asarray(d["u_applied"], float), np.asarray(d["F_cyl"], float),
                      np.asarray(d["stroke_true"], float))


def compare(res: dict, rep: Replay) -> dict:
    idx = {n: j for j, n in enumerate(res["names"])}
    t = res["time"]
    out = {"wall_s": round(res["wall_s"], 1), "dt": res["dt"], "t": [rep.t_start, rep.t_end], "eta_v": rep.eta_v,
           "legs": {}, "Q_pump_L_min": float(res["data"][0, idx["Q_pump"]] * 6e4)}
    for i, leg in enumerate(LEGS):
        rec_v = np.interp(t, rep.t, rep.v_cmd[:, i])
        sim_v = res["data"][:, idx[f"v_{leg}"]]
        rec_s = np.interp(t, rep.t, rep.s[:, i])
        sim_s = res["data"][:, idx[f"s_{leg}"]]
        out["legs"][leg] = {"max_abs_speed_diff_mm_s": float(np.abs(sim_v - rec_v).max() * 1e3),
                            "stroke_diff_end_mm": float((sim_s[-1] - rec_s[-1]) * 1e3),
                            "stroke_diff_max_abs_mm": float(np.abs(sim_s - rec_s).max() * 1e3)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("case", type=Path)
    ap.add_argument("--eta", type=float, default=0.90)
    ap.add_argument("--t0", type=float)
    ap.add_argument("--t1", type=float)
    ap.add_argument("--dt", type=float, default=1e-4)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    p = load_params()
    rep = load_replay(args.case, args.eta, args.t0, args.t1)
    res = simulate(p, rep, dt=args.dt)
    out_csv = args.out or OUT_DIR / "replay" / f"{args.case.name}_eta{args.eta:.2f}.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    write_csv(res, out_csv)
    summary = compare(res, rep)
    summary["csv"] = str(out_csv)
    print(json.dumps(summary))
    out_csv.with_suffix(".json").write_text(json.dumps(summary, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
