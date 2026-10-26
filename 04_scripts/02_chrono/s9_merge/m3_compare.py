"""M-3 table: soil response on vs off per case (``m3_run.py`` outputs) + the offline M-4 judge
of the *off* record against the *on* soil meta (cross-check of ``m4_offline.py``).

Usage: ``python -I -X utf8 04_scripts/02_chrono/s9_merge/m3_compare.py <m3 batch dir> <out.json>``
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import m4_offline  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")


def euler_deg(q: np.ndarray) -> np.ndarray:
    """Roll / pitch (deg) of body quaternions w, x, y, z (body x forward, y left, z up)."""
    w, x, y, z = q.T
    roll = np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))
    return np.degrees(np.stack([roll, pitch], axis=1))


def run_metrics(d: Path) -> dict:
    m3 = json.loads((d / "m3.json").read_text("utf-8"))
    res = json.loads((d / "result.json").read_text("utf-8"))
    rec = np.load(d / "record" / "record.npz", allow_pickle=False)
    r8 = np.load(d / "r8_series.npz", allow_pickle=False)
    t = rec["t"]
    phases = res["phases"]
    t0 = res["settings"]["start_t_s"]
    first = {}
    for ts, ph in phases:
        first.setdefault(ph, ts + t0)
    att = euler_deg(rec["body_quat_wxyz"])
    f = rec["F_cyl"]
    out = {"sha_issued": m3["sha256_issued_u"], "sha_events": m3["sha256_events"],
           "n": m3["n_periods"], "ready_t_s": res.get("ready_t_s"),
           "wall_s": m3["wall_s"], "config_seen": m3["config_seen"],
           "soil": m3["soil"], "events_soil": m3["events_soil"],
           "events_reapproach": m3["events_reapproach"],
           "foreign_modules": m3["foreign_project_modules"]}
    if "level" in first:
        sel = t >= first["level"]
        out["Fcyl_min_after_level_kN"] = float(f[sel].min() / 1e3)
    if "ready" in first:
        sel = t >= first["ready"]
        out["Fcyl_min_after_ready_kN"] = float(f[sel].min() / 1e3)
        out["att_max_after_ready_deg"] = float(np.abs(att[sel]).max())
    out["att_end_deg"] = [float(v) for v in att[-1]]
    out["stroke_max_mm"] = float(rec["s_motor"].max() * 1e3)
    out["record_keys"] = sorted(rec.files)
    out["_arrays"] = {k: rec[k] for k in rec.files if rec[k].dtype.kind in "fiub"}
    out["_r8"] = {k: r8[k] for k in r8.files if r8[k].dtype.kind in "fiub"}
    return out


def main(argv: list[str]) -> int:
    batch, out = Path(argv[0]), Path(argv[1])
    keys = sorted({p.name.split("__")[0] for p in batch.glob("*__on")})
    rows = []
    for key in keys:
        on_d, off_d = batch / f"{key}__on", batch / f"{key}__off"
        if not (on_d / "m3.json").exists() or not (off_d / "m3.json").exists():
            rows.append({"key": key, "status": "missing"})
            continue
        on, off = run_metrics(on_d), run_metrics(off_d)
        rec_diff = [k for k in on["_arrays"] if k in off["_arrays"] and not np.array_equal(
            on["_arrays"][k], off["_arrays"][k], equal_nan=True)]
        r8_diff = [k for k in on["_r8"] if k in off["_r8"] and not np.array_equal(
            on["_r8"][k], off["_r8"][k], equal_nan=True)]
        first_diff = None
        if on["sha_issued"] != off["sha_issued"]:
            a, b = on["_r8"]["issued_u"], off["_r8"]["issued_u"]
            n = min(len(a), len(b))
            idx = np.where(np.any(a[:n] != b[:n], axis=1))[0]
            first_diff = None if not len(idx) else float(on["_r8"]["t"][idx[0]])
        offline = m4_offline.analyse(off_d)
        soil = on["soil"] or {}
        cross = None
        if offline.get("loc") and soil.get("loc"):
            lo = offline["loc"]
            cross = {k: {"offline": lo[k2], "on_meta": soil[k]} for k, k2 in (
                ("t_P_s", "t_P_s"), ("t_loc_s", "t_loc_s"), ("clearance_at_P_m",
                                                              "clearance_at_P_m"),
                ("clearance_at_loc_m", "clearance_at_loc_m"), ("W_hat_N", "W_hat_N"))}
        soil_names = ("soil_mode_start", "crawler_liftoff_confirmed", "INFO_CLEARANCE_BIAS",
                      "WARN_CRAWLER_LIFTOFF_UNCONFIRMED", "WARN_WEIGHT_MISMATCH")
        ev_on = json.loads((on_d / "controller_events.json").read_text("utf-8"))
        ev_off = json.loads((off_d / "controller_events.json").read_text("utf-8"))
        ev_on_wo = [e for e in ev_on if not any(n in e for n in soil_names)]
        t0 = json.loads((on_d / "result.json").read_text("utf-8"))["settings"]["start_t_s"]
        row = {"key": key, "status": "ok", "start_t_s": t0,
               "events_equal_without_soil": ev_on_wo == ev_off,
               "events_only_on": [e for e in ev_on if e not in ev_off],
               "events_only_off": [e for e in ev_off if e not in ev_on],
               "sha_issued_equal": on["sha_issued"] == off["sha_issued"],
               "sha_events_equal": on["sha_events"] == off["sha_events"],
               "first_command_diff_t_s": first_diff,
               "record_arrays_differing": rec_diff, "r8_arrays_differing": r8_diff,
               "on": {k: v for k, v in on.items() if not k.startswith("_")},
               "off": {k: v for k, v in off.items() if not k.startswith("_")},
               "offline_m4_on_off_record": {k: offline.get(k) for k in (
                   "loc", "release_t_s", "first_done_t_s", "loc_before_release",
                   "loc_before_done", "bias_applied", "unchanged", "reason")},
               "offline_vs_on_meta": cross}
        rows.append(row)
        s = soil
        print(f"{key}: sha_equal={row['sha_issued_equal']} events_equal={row['sha_events_equal']} "
              f"rec_diff={len(rec_diff)} LOC={s.get('loc')} t_loc={s.get('t_loc_s')} "
              f"cP_mm={s.get('clearance_at_P_m') and round(1e3 * s['clearance_at_P_m'], 3)} "
              f"soil_mode_t={s.get('soil_mode_t_s')} ready on/off={on['ready_t_s']}/{off['ready_t_s']}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=1, default=lambda o: o.tolist()
                              if hasattr(o, "tolist") else str(o)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
