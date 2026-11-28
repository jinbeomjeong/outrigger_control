"""Edition-9 D1'' rule candidates on the stage-5 diagnosis traces (record replay, no judgement).

Usage (dynamics-dev):
  python.exe -I -B d1_rule_eval.py <stage5_aa_diag folder> <output folder>

Reads the D1 traces of diagnosis 1 (``trace_<label>.json`` + ``runs_trace_on.jsonl``) and of
diagnosis 2 (B, C, D, E). For every trace it takes the controller monitor's rows (the monitor
with the most rows) and recomputes the D1'' residual ``r_j = sum F_j - M f_z,j`` of every
period with one mass ``M`` (the mass of the judged period, as the code does for the pair).

Rules (head step candidate: one-period ``|dp_h| > max_step``; threshold ``0.5 |dp_h| A_p``):
  C0   current D1'':  unexplained iff |r_j - r_{j-1}| >= thr
  Cd   two references: unexplained iff |r_j - r_{j-1}| >= thr and |r_j - r_{j-2}| >= thr
       (``r_{j-2}`` missing -> C0)
  Ce   suspect then confirm: C0 unexplained at j -> FAULT at j+1 iff |r_{j+1} - r_{j-2}| >= thr_j
  Cf   support-loss exemption: no D1'' fault at j when some leg's net-force reading fell by
       >= 50 % from j-2 to j-1 with at least 20 kN at j-2 (else C0)
  Cm   median reference: unexplained iff |r_j - r_{j-1}| >= thr and
       |r_j - median(r_{j-1}, r_{j-2}, r_{j-3})| >= thr (fewer than three references -> C0)
  Cmo  median only: unexplained iff |r_j - median(r_{j-1}, r_{j-2}, r_{j-3})| >= thr (not a
       subset of C0; fewer than three references -> C0)
  D1p  reference: D1' sum rule, unexplained iff |sum F_j - sum F_{j-1}| >= thr (spec 217.5;
       P-S8-14 (c) asks D1'' detection >= D1')

Persistent jump injection (open-loop replay, as spec 219.2 (d)): for every D1''-ready period j
before the first head fault of the trace and every leg, a head offset J (+-100, +-150 bar) from
j on. The jump adds ``J A_p`` to ``sum F`` of j and later; ``dp_h`` of j becomes ``dp_h + J``.
Detection is judged at j (C0, Cd, Cf) or j+1 (Ce). A jump missed at j has no later candidate
(the later one-period changes do not contain it), so it is missed by the step rule.

Writes (refuses existing files): candidate_periods.csv, injection_detail.csv,
injection_summary.csv, rule_eval_summary.json. Exit codes: 0 written, 2 output exists.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

LEGS = ("FL", "FR", "RL", "RR")
BAR = 1e5
RATIO = 0.5
JUMPS_BAR = (100.0, -100.0, 150.0, -150.0)
QUIET_DP_BAR = 30.0  # spec 219.2 (b): transient = max |dp_h| > 30 bar
EXEMPT_DROP = 0.5
EXEMPT_MIN_N = 20e3
RULE_NAMES = ("C0", "Cd", "Ce", "Cf", "Cm", "Cmo", "D1p")
SETS = (
    ("diag1", ".", "runs_trace_on.jsonl", "."),
    ("B", "diag2", "B_gyro_all_trace_on.jsonl", "traces_B"),
    ("C", "diag2", "C_gyro_d1only_trace_on.jsonl", "traces_C"),
    ("D", "diag2", "D_sweep_gyro_off_trace_on.jsonl", "traces_D"),
    ("E", "diag2", "E_sweep_ext_gyro_off_trace_on.jsonl", "traces_E"),
)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def primary(trace: dict) -> tuple[dict, list[dict]]:
    counts: dict[str, int] = {}
    for row in trace["rows"]:
        counts[row["monitor"]] = counts.get(row["monitor"], 0) + 1
    name = max(counts, key=counts.get)
    rows = sorted((r for r in trace["rows"] if r["monitor"] == name), key=lambda r: r["t_s"])
    return trace["monitors"][name], rows


def lift_time(record: dict) -> float | None:
    leg = record["job"]["twin"]["leg"]
    lift = (record.get("event_output") or {}).get("lifts", {}).get(leg)
    if lift is None or record.get("t_event_s") is None or lift.get("first_s") is None:
        return None
    return record["t_event_s"] + lift["first_s"]


def has_fz(row: dict) -> bool:
    return row.get("f_z_used_m_s2") is not None and row.get("net_sum_N") is not None


def residual(row: dict, mass: float) -> float:
    return row["net_sum_N"] - mass * row["f_z_used_m_s2"]


def leg_forces(row: dict, area: list[float], annulus: list[float]) -> list[float]:
    head, rod = row.get("head_Pa"), row.get("rod_Pa")
    if head is None or rod is None:
        return [math.nan] * 4
    return [head[i] * area[i] - rod[i] * annulus[i] for i in range(4)]


def exempt(rows: list[dict], j: int, area, annulus) -> bool:
    if j < 2:
        return False
    before, last = leg_forces(rows[j - 2], area, annulus), leg_forces(rows[j - 1], area, annulus)
    return any(b >= EXEMPT_MIN_N and (b - a) >= EXEMPT_DROP * b for b, a in zip(before, last))


def ready(row: dict) -> bool:
    return bool(row.get("d1pp_inputs_ready")) and has_fz(row)


def valid_ref(row: dict) -> bool:
    """A residual of an earlier period can be rebuilt (crawler off, f_z there)."""
    return bool(row.get("is_crawler_lifted")) and has_fz(row)


def median_ref(rows: list[dict], j: int, mass: float) -> float | None:
    if j < 3 or not all(valid_ref(rows[j - n]) for n in (1, 2, 3)):
        return None
    values = sorted(residual(rows[j - n], mass) for n in (1, 2, 3))
    return values[1]


def analyse(set_name: str, record: dict, trace: dict, cand_rows: list, inj_rows: list) -> dict:
    meta, rows = primary(trace)
    area, annulus = meta["head_area_m2"], meta["annulus_area_m2"]
    max_step = meta["settings"]["max_step_Pa"]
    label = record["label"]
    lift_s = lift_time(record)
    t_event = record.get("t_event_s")
    first_fault = next((i for i, r in enumerate(rows) if r.get("head_fault_reasons")), None)
    info = {"set": set_name, "label": label, "final_phase": record.get("final_phase"),
            "t_event_s": t_event, "lift_s": lift_s, "first_fault_t_s":
                None if first_fault is None else rows[first_fault]["t_s"], "max_step_Pa": max_step}
    # actual candidate periods (D1'' branch)
    for j, row in enumerate(rows):
        cands = row.get("candidates") or {}
        if not cands or row.get("step_rule_branch") != "imu_residual" or j < 1:
            continue
        mass = row["mass_kg"]
        r_j, r_1 = residual(row, mass), residual(rows[j - 1], mass)
        r_2 = residual(rows[j - 2], mass) if j >= 2 and valid_ref(rows[j - 2]) else None
        r_n = residual(rows[j + 1], mass) if j + 1 < len(rows) and valid_ref(rows[j + 1]) else None
        r_med = median_ref(rows, j, mass)
        for leg, c in cands.items():
            thr = c["threshold_N"]
            d1, d2 = abs(r_j - r_1), None if r_2 is None else abs(r_j - r_2)
            c0 = d1 >= thr
            cd = c0 and (d2 is None or d2 >= thr)
            ce = c0 and (r_2 is None or r_n is None or abs(r_n - r_2) >= thr)
            cf = c0 and not exempt(rows, j, area, annulus)
            cm = c0 and (r_med is None or abs(r_j - r_med) >= thr)
            cmo = c0 if r_med is None else abs(r_j - r_med) >= thr
            d1p = abs(row["net_sum_N"] - rows[j - 1]["net_sum_N"]) >= thr
            cand_rows.append({
                "set": set_name, "label": label, "final_phase": record.get("final_phase"),
                "t_s": row["t_s"], "t_minus_event_s": None if t_event is None else round(
                    row["t_s"] - t_event, 4),
                "prev_sample_minus_lift_ms": None if lift_s is None else round(
                    (row["t_s"] - 0.1 - lift_s) * 1e3, 1),
                "leg": leg, "dp_head_bar": round(c["dp_head_Pa"] / BAR, 2),
                "threshold_kN": round(thr / 1e3, 3), "r_jm2_kN": None if r_2 is None else round(
                    r_2 / 1e3, 3), "r_jm1_kN": round(r_1 / 1e3, 3), "r_j_kN": round(r_j / 1e3, 3),
                "r_jp1_kN": None if r_n is None else round(r_n / 1e3, 3),
                "d1_kN": round(d1 / 1e3, 3), "d2_kN": None if d2 is None else round(d2 / 1e3, 3),
                "d1_over_thr": round(d1 / thr, 4), "d2_over_thr": None if d2 is None else round(
                    d2 / thr, 4),
                "r_med_kN": None if r_med is None else round(r_med / 1e3, 3),
                "dmed_over_thr": None if r_med is None else round(abs(r_j - r_med) / thr, 4),
                "code_unexplained": c["is_unexplained"], "C0": c0, "Cd": cd,
                "Ce": ce, "Cf": cf, "Cm": cm, "Cmo": cmo, "D1p": d1p,
                "is_lever_missing": row.get("is_lever_missing")})
    # injection
    end = len(rows) if first_fault is None else first_fault
    for j in range(2, end):
        row = rows[j]
        if not ready(row) or not valid_ref(rows[j - 1]):
            continue
        mass = row["mass_kg"]
        dp = row.get("dp_head_Pa")
        if dp is None:
            continue
        r_j, r_1 = residual(row, mass), residual(rows[j - 1], mass)
        r_2 = residual(rows[j - 2], mass) if valid_ref(rows[j - 2]) else None
        r_n = residual(rows[j + 1], mass) if j + 1 < end and valid_ref(rows[j + 1]) else None
        r_med = median_ref(rows, j, mass)
        max_dp_bar = max(abs(v) for v in dp) / BAR
        kind = "quiet" if max_dp_bar <= QUIET_DP_BAR else "transient"
        near = (t_event is not None and 0.0 <= row["t_s"] - t_event <= 0.5)
        is_exempt = exempt(rows, j, area, annulus)
        for i in range(4):
            for jump_bar in JUMPS_BAR:
                jump = jump_bar * BAR
                step = dp[i] + jump
                if abs(step) <= max_step:
                    c0 = cd = ce = cf = cm = cmo = d1p = False
                    thr = math.nan
                else:
                    thr = RATIO * abs(step) * area[i]
                    add = jump * area[i]
                    d1 = abs(r_j + add - r_1)
                    c0 = d1 >= thr
                    cd = c0 and (r_2 is None or abs(r_j + add - r_2) >= thr)
                    ce = c0 and (r_2 is None or r_n is None or abs(r_n + add - r_2) >= thr)
                    cf = c0 and not is_exempt
                    dmed = None if r_med is None else abs(r_j + add - r_med)
                    cm = c0 and (dmed is None or dmed >= thr)
                    cmo = c0 if dmed is None else dmed >= thr
                    d1p = abs(row["net_sum_N"] + add - rows[j - 1]["net_sum_N"]) >= thr
                inj_rows.append({"set": set_name, "label": label, "t_s": row["t_s"],
                                 "t_minus_event_s": None if t_event is None else round(
                                     row["t_s"] - t_event, 4),
                                 "leg": LEGS[i], "jump_bar": jump_bar, "kind": kind,
                                 "event_0_0p5s": near, "exempt": is_exempt,
                                 "threshold_kN": None if math.isnan(thr) else round(thr / 1e3, 3),
                                 "C0": c0, "Cd": cd, "Ce": ce, "Cf": cf, "Cm": cm, "Cmo": cmo,
                                 "D1p": d1p})
    return info


def summarise(inj_rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for row in inj_rows:
        for scope in ("all", row["kind"], "event_0_0p5s" if row["event_0_0p5s"] else None):
            if scope is None:
                continue
            groups.setdefault((scope, row["jump_bar"]), []).append(row)
    out = []
    for (scope, jump), rows in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        n = len(rows)
        line = {"scope": scope, "jump_bar": jump, "n": n}
        for rule in RULE_NAMES:
            hit = sum(r[rule] for r in rows)
            line[f"{rule}_detected"] = hit
            line[f"{rule}_rate"] = round(hit / n, 6) if n else None
        line["Cd_lost_vs_C0"] = sum(r["C0"] and not r["Cd"] for r in rows)
        line["Ce_lost_vs_C0"] = sum(r["C0"] and not r["Ce"] for r in rows)
        line["Cf_lost_vs_C0"] = sum(r["C0"] and not r["Cf"] for r in rows)
        line["Cm_lost_vs_C0"] = sum(r["C0"] and not r["Cm"] for r in rows)
        line["Cmo_gained_vs_C0"] = sum(r["Cmo"] and not r["C0"] for r in rows)
        line["Cmo_lost_vs_C0"] = sum(r["C0"] and not r["Cmo"] for r in rows)
        out.append(line)
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    columns = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    diag, out = Path(sys.argv[1]), Path(sys.argv[2])
    names = ["candidate_periods.csv", "injection_detail.csv", "injection_summary.csv",
             "rule_eval_summary.json"]
    if any((out / n).exists() for n in names):
        print("refusing to overwrite")
        return 2
    out.mkdir(parents=True, exist_ok=True)
    cand_rows: list[dict] = []
    inj_rows: list[dict] = []
    infos = []
    for set_name, sub, jsonl, trace_dir in SETS:
        base = diag / sub
        for record in read_jsonl(base / jsonl):
            path = base / trace_dir / f"trace_{record['label']}.json"
            trace = json.loads(path.read_text(encoding="utf-8"))
            infos.append(analyse(set_name, record, trace, cand_rows, inj_rows))
    write_csv(out / "candidate_periods.csv", cand_rows)
    write_csv(out / "injection_detail.csv", inj_rows)
    summary = summarise(inj_rows)
    write_csv(out / "injection_summary.csv", summary)
    faults = {rule: sum(1 for r in cand_rows if r[rule]) for rule in RULE_NAMES}
    jobs_fault = {rule: len({(r["set"], r["label"]) for r in cand_rows if r[rule]})
                  for rule in RULE_NAMES}
    mismatch = [r for r in cand_rows if r["C0"] != r["code_unexplained"]]
    d2_ratios = [r["d2_over_thr"] for r in cand_rows if r["d2_over_thr"] is not None]
    result = {"traces": len(infos), "candidate_leg_periods": len(cand_rows),
              "unexplained_leg_periods": faults, "jobs_with_unexplained": jobs_fault,
              "C0_vs_code_mismatch": len(mismatch),
              "max_d2_over_thr_all_candidates": max(d2_ratios) if d2_ratios else None,
              "injection_rows": len(inj_rows), "jobs": infos,
              "rules": {"ratio": RATIO, "quiet_dp_bar": QUIET_DP_BAR,
                        "exempt_drop": EXEMPT_DROP, "exempt_min_N": EXEMPT_MIN_N}}
    (out / "rule_eval_summary.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "jobs"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
