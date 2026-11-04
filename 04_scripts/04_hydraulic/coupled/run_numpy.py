"""Run the numpy model for the scenarios, one process per scenario pool.

usage: run_numpy.py [--names A B ...] [--dt 5e-5] [--tag _dt5e-5] [--jobs 6]
Writes 06_analysis/03_hydraulic/coupled/numpy/<scenario><tag>.csv (GAUGE pressures).
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

from model import simulate, write_csv  # noqa: E402
from params import LEGS, OUT_DIR, load_params  # noqa: E402
from scenarios import BY_NAME, SCENARIOS  # noqa: E402


def one(job: tuple[str, float, str, dict]) -> dict:
    sys.path.insert(0, str(HERE))
    name, dt, tag, kw = job
    p = load_params().with_(**kw)
    res = simulate(p, BY_NAME[name], dt=dt)
    out = OUT_DIR / "numpy"
    out.mkdir(parents=True, exist_ok=True)
    write_csv(res, out / f"{name}{tag}.csv")
    idx = {n: j for j, n in enumerate(res["names"])}
    last = res["data"][-1]
    return {"name": name, "wall_s": round(res["wall_s"], 1), "dt": dt,
            "v_mm_s": [round(last[idx[f"v_{leg}"]] * 1e3, 3) for leg in LEGS],
            "p_h_bar": [round(last[idx[f"p_h_{leg}"]] / 1e5, 2) for leg in LEGS],
            "p_P_bar": round(last[idx["p_P"]] / 1e5, 2), "Q_byp_L_min": round(last[idx["Q_byp"]] * 6e4, 3),
            "finite": bool(np.isfinite(res["data"]).all())}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", nargs="*")
    ap.add_argument("--dt", type=float, default=5e-5)
    ap.add_argument("--tag", default="")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--flow-off", action="store_true", help="flow limit off (ample supply)")
    ap.add_argument("--law", default=None, help="priority or proportional")
    ap.add_argument("--dp-c", type=float, help="section compensator dp [bar]")
    ap.add_argument("--dp-ls", type=float, help="standby dp [bar]")
    ap.add_argument("--width", type=float, help="smoothing width [bar]")
    args = ap.parse_args()
    names = args.names or [s.name for s in SCENARIOS]
    kw: dict = {}
    if args.flow_off:
        kw["flow_limit"] = False
    if args.law:
        kw["law"] = args.law
    if args.dp_c:
        kw["dp_comp"] = args.dp_c * 1e5
    if args.dp_ls:
        kw["dp_unl"] = args.dp_ls * 1e5
    if args.width:
        kw["width"] = args.width * 1e5
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        rows = list(ex.map(one, [(n, args.dt, args.tag, kw) for n in names]))
    for r in rows:
        print(json.dumps(r))
    path = OUT_DIR / "numpy" / f"run_log{args.tag}.json"
    old = json.loads(path.read_text()) if path.exists() else {}
    old.update({r["name"]: r for r in rows})
    path.write_text(json.dumps(old, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
