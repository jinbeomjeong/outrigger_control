"""Q7-D3: twist-coordinate analysis of the A_ib (blind-band fill) shots in the
ed7 probe arm a2 (condition 3 (da)), using the b46bdf8f repro (114 lines) that
carries the new record keys level_done / twist_over_limit and T4h D trace.

Conventions
-----------
- Leg order FL, FR, RL, RR. Twist vector n = (0.4761, -0.4761, -0.5228, 0.5228),
  D = n^T F, compression positive (spec 3 conventions, dynamics d7 sec. 1).
- true_force_N: harness true cylinder/leg force [N], compression +.
- lsb_ib_twist_load_N: controller D used by condition (da) (10 Hz update).
- Times in s, forces reported in kN.

Outputs (CSV/JSON/TXT) go to --out folder.
"""
import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\b46bdf8f\repro_a2")
N_TW = np.array([0.4761, -0.4761, -0.5228, 0.5228])
LEGS = ("FL", "FR", "RL", "RR")
LIMIT_N = 15000.0
F_MIN_N = 9415.0


def job_name(job):
    eps = job.get("eps")
    case = job.get("case")
    return f"{case}_e{eps}" if eps is not None else str(case)


def nearest_idx(t, x):
    return int(np.argmin(np.abs(t - x)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)

    shot_rows = []
    episode_rows = []
    done_rows = []
    line_rows = []
    with open(RUN / "ed7_probe_a2.jsonl", encoding="utf-8") as fh:
        for raw in fh:
            rec = json.loads(raw)
            job = rec["job"]
            setting = job["setting"]
            plant = setting.split("-")[1]
            # unique line key: T4h file stem without the setting suffix
            key = Path(rec["t4h_file"]).stem.rsplit("_P7-", 1)[0]
            part = rec.get("ed7_probe", {}).get("part") if isinstance(rec.get("ed7_probe"), dict) else None
            blind = (rec.get("lsb_record") or {}).get("blind") or {}
            npz_path = RUN / "ed7_probe_a2_t4h" / Path(rec["t4h_file"]).name
            z = np.load(npz_path, allow_pickle=False)
            t = z["t_s"]
            phase = z["phase"]
            Ft = z["true_force_N"]
            Dtrue = Ft @ N_TW
            Dctl = z["lsb_ib_twist_load_N"] if "lsb_ib_twist_load_N" in z.files else np.full(t.shape, np.nan)
            Fmin_leg = z["true_force_min_N"] if "true_force_min_N" in z.files else Ft
            t_ev = rec.get("t_event_s")
            lvl = phase == "level"
            # max |D| during LEVEL (controller and true)
            maxD_ctl_level = float(np.nanmax(np.abs(Dctl[lvl]))) if lvl.any() and np.isfinite(Dctl[lvl]).any() else float("nan")
            maxD_true_level = float(np.max(np.abs(Dtrue[lvl]))) if lvl.any() else float("nan")
            # D at end of each LEVEL segment
            seg_end_D = []
            idx = np.flatnonzero(lvl)
            if idx.size:
                breaks = np.flatnonzero(np.diff(idx) > 1)
                ends = np.r_[idx[breaks], idx[-1]]
                for e in ends:
                    nxt = phase[e + 1] if e + 1 < len(phase) else "END"
                    seg_end_D.append((float(t[e]), float(Dctl[e]) if np.isfinite(Dctl[e]) else float("nan"), float(Dtrue[e]), str(nxt)))
            tol = blind.get("twist_over_limit") or {}
            line_rows.append({
                "key": key, "plant": plant, "part": part, "final_phase": rec.get("final_phase"),
                "t_event_s": t_ev,
                "shots": len(blind.get("shots", [])),
                "four_leg": blind.get("four_leg_twist_triggers"),
                "tol_entries": tol.get("entries"), "tol_periods": tol.get("periods"),
                "level_done_n": len(blind.get("level_done", [])),
                "level_done_paths": ";".join(d["path"] for d in blind.get("level_done", [])),
                "maxD_ctl_level_kN": maxD_ctl_level / 1e3, "maxD_true_level_kN": maxD_true_level / 1e3,
                "level_seg_ends": json.dumps([(round(a, 2), round(b / 1e3, 2), round(c / 1e3, 2), d) for a, b, c, d in seg_end_D]),
                "minF_level_kN": float(Fmin_leg[lvl].min()) / 1e3 if lvl.any() else float("nan"),
            })
            for d in blind.get("level_done", []):
                done_rows.append({"key": key, "plant": plant, "t_s": d["t_s"], "path": d["path"],
                                  "twist_load_kN": d["twist_load_N"] / 1e3})
            shots = blind.get("shots", [])
            for ep in tol.get("episodes", []):
                st, en = ep["start_t_s"], ep["end_t_s"]
                i0 = nearest_idx(t, st)
                prev_phase = str(phase[i0 - 1]) if i0 > 0 else ""
                # shots that ended within 3 s before the start, or active at start
                near = [s for s in shots if s["start_t_s"] <= st + 1e-9 and (s.get("end_t_s") or st) >= st - 3.0]
                episode_rows.append({
                    "key": key, "plant": plant, "start_t_s": st, "end_t_s": en, "periods": ep["periods"],
                    "max_abs_twist_kN": ep["max_abs_twist_N"] / 1e3,
                    "t_since_event_s": (st - t_ev) if t_ev is not None else None,
                    "prev_phase": prev_phase,
                    "end_phase": str(phase[nearest_idx(t, en)]) if en is not None else "open",
                    "near_shots": ";".join(f"{s['leg']}{s['sign']:+d}@{s['start_t_s']:.1f}" for s in near),
                    "D_true_at_start_kN": float(Dtrue[i0]) / 1e3,
                })
            for s in shots:
                st = s["start_t_s"]
                en = s.get("end_t_s")
                i0 = nearest_idx(t, st)
                ib = i0 - 1 if i0 > 0 else 0
                iend = nearest_idx(t, (en if en is not None else st) + 1.0)
                win = slice(ib, iend + 1)
                li = LEGS.index(s["leg"])
                pred_sign = math.copysign(1.0, N_TW[li] * s["sign"])
                Dc0 = float(Dctl[ib]) if np.isfinite(Dctl[ib]) else float("nan")
                # stroke change of the shooting leg over the shot
                sm = z["motor_stroke_m"][:, li]
                ds = float(sm[iend] - sm[ib])
                # rank-1 prediction with k1 (beta 1.0): front 27.5, rear 26.3 MN/m (d7 2.4)
                k1 = 27.5e6 if li < 2 else 26.3e6
                dD_pred = k1 * N_TW[li] * ds * float(np.sum(N_TW ** 2))  # n^T S e_i ds, S = k1 n n^T / |n|^2 approx
                shot_rows.append({
                    "key": key, "plant": plant, "leg": s["leg"], "sign": s["sign"], "start_t_s": st,
                    "end_t_s": en, "end": s.get("end"), "completion_known": s.get("completion_known"),
                    "t_since_event_s": (st - t_ev) if t_ev is not None else None,
                    "D_before_rec_kN": s["twist_before_N"] / 1e3, "D_after_rec_kN": s["twist_after_N"] / 1e3,
                    "dD_rec_kN": s["delta_D_N"] / 1e3, "twist_grew": s.get("twist_grew"),
                    "D_ctl_before_kN": Dc0 / 1e3,
                    "branch": "twist_gt_15_possible" if abs(Dc0) > LIMIT_N else "attitude_or_clearance",
                    "shot_sign_twist_dir": int(pred_sign),
                    "shot_reduces_D_by_sign": bool(pred_sign != math.copysign(1.0, s["twist_before_N"])),
                    "stroke_change_mm": ds * 1e3,
                    "dD_pred_rank1_kN": dD_pred / 1e3,
                    "maxabsD_ctl_win_kN": float(np.nanmax(np.abs(Dctl[win]))) / 1e3,
                    "crossed_15_in_window": bool(abs(Dc0) <= LIMIT_N and np.nanmax(np.abs(Dctl[win])) > LIMIT_N),
                    "minF_before_kN": float(Fmin_leg[ib].min()) / 1e3,
                    "minF_win_kN": float(Fmin_leg[win].min()) / 1e3,
                    "dF_max_abs_kN": max(abs(x) for x in s["delta_F_N"]) / 1e3,
                })

    def wcsv(name, rows):
        if not rows:
            (out / name).write_text("", encoding="utf-8")
            return
        with open(out / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    wcsv("a2_shots.csv", shot_rows)
    wcsv("a2_twist_over_limit_episodes.csv", episode_rows)
    wcsv("a2_level_done.csv", done_rows)
    wcsv("a2_lines.csv", line_rows)

    # summary
    S = {}
    S["lines"] = len(line_rows)
    S["shots"] = len(shot_rows)
    S["shots_grew"] = sum(1 for r in shot_rows if r["twist_grew"])
    S["shots_by_branch"] = {b: sum(1 for r in shot_rows if r["branch"] == b) for b in ("twist_gt_15_possible", "attitude_or_clearance")}
    S["shots_crossed_15"] = sum(1 for r in shot_rows if r["crossed_15_in_window"])
    S["shots_absD_after_gt15"] = sum(1 for r in shot_rows if abs(r["D_after_rec_kN"]) > 15)
    S["dD_abs_kN"] = {"median": float(np.median([abs(r["dD_rec_kN"]) for r in shot_rows])) if shot_rows else None,
                      "max": max((abs(r["dD_rec_kN"]) for r in shot_rows), default=None)}
    S["absD_before_kN"] = {"median": float(np.median([abs(r["D_before_rec_kN"]) for r in shot_rows])) if shot_rows else None,
                           "max": max((abs(r["D_before_rec_kN"]) for r in shot_rows), default=None)}
    S["absD_after_kN_max"] = max((abs(r["D_after_rec_kN"]) for r in shot_rows), default=None)
    S["minF_win_kN_min"] = min((r["minF_win_kN"] for r in shot_rows), default=None)
    S["minF_drop_kN_max"] = max((r["minF_before_kN"] - r["minF_win_kN"] for r in shot_rows), default=None)
    S["four_leg_total"] = sum((r["four_leg"] or 0) for r in line_rows)
    S["tol_entries_total"] = sum((r["tol_entries"] or 0) for r in line_rows)
    S["tol_lines"] = sum(1 for r in line_rows if (r["tol_entries"] or 0) > 0)
    S["tol_periods_total"] = sum((r["tol_periods"] or 0) for r in line_rows)
    S["level_done"] = {p: sum(1 for d in done_rows if d["path"] == p) for p in ("strict", "relax")}
    S["level_done_relax_absD_kN_max"] = max((abs(d["twist_load_kN"]) for d in done_rows if d["path"] == "relax"), default=None)
    S["level_done_absD_kN_max"] = max((abs(d["twist_load_kN"]) for d in done_rows), default=None)
    S["final_phase_counts"] = {}
    for r in line_rows:
        S["final_phase_counts"][r["final_phase"]] = S["final_phase_counts"].get(r["final_phase"], 0) + 1
    S["episodes"] = len(episode_rows)
    S["episodes_with_near_shot"] = sum(1 for e in episode_rows if e["near_shots"])
    (out / "a2_summary.json").write_text(json.dumps(S, indent=2), encoding="utf-8")
    print(json.dumps(S, indent=2))


if __name__ == "__main__":
    main()
