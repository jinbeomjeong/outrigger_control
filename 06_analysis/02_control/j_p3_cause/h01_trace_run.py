"""Re-run R12 bottom-FL-Fs4 o0.0 (VB, LS3) with a read-only trace of the RR plant internals.

The trace wraps ``harness_hydraulics.make_hydraulics_plant_class``: after every ``_rod_force``
call of an armed plant it copies RR state (t, locked, last_dir, p_r0, Gr, Gr_lock, c, c_lock, r0,
t_rel, M2 lag pressure and target, net oil force) for 48.3 s <= t <= 49.4 s. It does not write
to the plant. The command hash is compared with the stored h10 line to prove the same run.

Usage (dynamics-dev, any cwd):
  python -I -B b01_trace_run.py <out_dir> [settings comma list]
Writes <out_dir>/trace_<setting>.npz and <out_dir>/trace_summary.json.
"""
from __future__ import annotations

import json
import os
import sys
from multiprocessing import get_context
from pathlib import Path

for _name in ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_name, "1")
os.environ.setdefault("MKL_THREADING_LAYER", "TBB")

ROOT = Path(r"C:\workspace\outrigger_control")
COUPLED = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
H10 = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "resume_k1" / "h10_reuse_rerun.jsonl"
STORED_LINE = {"VB": 28, "LS2": 172, "LS3": 245}
LEG = 3
T0, T1 = 48.3, 49.4


def _job(setting: str) -> dict:
    return {"case": "R12", "eps": 0.0, "offset_s": 0.0,
            "twin": {"level": "bottom", "leg": "FL", "fs_kN": 4.0}, "setting": setting}


def worker(setting: str, out_dir: str) -> dict:
    sys.path.insert(0, str(COUPLED))
    os.chdir(ROOT)
    import numpy as np

    import harness_hydraulics as hh
    import run_v5

    rows: list[tuple] = []
    original = hh.make_hydraulics_plant_class

    def traced(base, options, damping_N_s_m=None):
        cls = original(base, options, damping_N_s_m)

        class Traced(cls):
            def _rod_force(self, u):
                out = super()._rod_force(u)
                t = float(self.t)
                if T0 <= t <= T1 and getattr(self, "armed", False):
                    i = LEG
                    lag = getattr(self, "rod_pressure_lag", None)
                    net = float(np.asarray(self.pressure(), float)[i])
                    if lag is not None:
                        mode_dir = float(self.last_dir[i])
                        from outrigger_sim.hydraulics.rod_chamber import RodChamberMode
                        mode = RodChamberMode.EXT if mode_dir > 0 else RodChamberMode.RET
                        target = float(lag._legs[i].moving_target_rod_pressure_Pa(mode, net))
                        p_lag = float(lag.pressure_Pa[i])
                    else:
                        target = p_lag = float("nan")
                    rows.append((id(self), t, float(np.asarray(u, float)[i]),
                                 float(bool(self.locked[i])), float(self.last_dir[i]),
                                 float(self.p_r0[i]), float(self.Gr[i]), float(self.Gr_lock[i]),
                                 float(self.sref[i] - self.x[i]), float(self.c_lock[i]),
                                 float(self.r0[i]), float(self.t_rel[i]), p_lag, target, net,
                                 float(self.sref[i]), float(self.x[i])))
                return out

        Traced.__name__ = cls.__name__
        Traced.__qualname__ = cls.__qualname__
        return Traced

    hh.make_hydraulics_plant_class = traced
    record = run_v5.run_one(_job(setting))
    cols = ("plant_id", "t", "u_kernel", "locked", "last_dir", "p_r0", "Gr", "Gr_lock", "c",
            "c_lock", "r0", "t_rel", "p_lag", "p_target", "net_N", "sref", "x")
    arr = np.array(rows, float) if rows else np.zeros((0, len(cols)))
    # one plant object per array row group; keep constants of the leg as well
    np.savez(Path(out_dir) / f"trace_{setting}.npz", data=arr, cols=np.array(cols))
    stored = None
    if setting in STORED_LINE:
        line = H10.read_text(encoding="utf-8").splitlines()[STORED_LINE[setting] - 1]
        stored = json.loads(line).get("commands_sha256")
    hrec = record.get("hydraulics_record") or {}
    ebc = hrec.get("extend_bound_check") or {}
    return {"setting": setting, "error": record.get("error"), "tb": record.get("tb"),
            "wall_s": record.get("wall_s"),
            "commands_sha256": record.get("commands_sha256"), "stored_sha256": stored,
            "same_run": stored is not None and stored == record.get("commands_sha256"),
            "rows": int(arr.shape[0]),
            "plants": sorted({int(r[0]) for r in rows}),
            "bound_check_RR": {k: (v[LEG] if isinstance(v, list) and len(v) == 4 else None)
                               for k, v in ebc.items()
                               if k in ("breach_reads", "min_gap_bar", "min_gap_t_s")}}


def main() -> None:
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    settings = sys.argv[2].split(",") if len(sys.argv) > 2 else ["VB", "LS3"]
    with get_context("spawn").Pool(len(settings), maxtasksperchild=1) as pool:
        results = pool.starmap(worker, [(s, str(out_dir)) for s in settings])
    (out_dir / "trace_summary.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    for r in results:
        print(json.dumps({k: r[k] for k in r if k != "tb"}))
        if r.get("tb"):
            print(r["tb"])


if __name__ == "__main__":
    main()
