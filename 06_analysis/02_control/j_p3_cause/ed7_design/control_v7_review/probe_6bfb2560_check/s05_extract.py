"""Edition 7 probe (6bfb2560, ed7_probe_a1) analysis 1: prediction check P7-7 / P7-8, record checks.

Streams ed7_probe.jsonl (only the needed keys), reads the T4h npz per line, writes CSV / JSON to
the output folder given as argv[1]. Read only on the probe folder.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
           r"\6bfb2560\ed7_probe_a1")
ROWS = RUN / "ed7_probe.jsonl"
T4H = RUN / "ed7_probe_t4h"
COND = RUN / "condition_ad7a716e.json"
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
LEGS = ("FL", "FR", "RL", "RR")
PERIOD_S = 0.1
BAR = 1e5


def key_name(job: dict) -> str:
    twin = job.get("twin")
    if twin:
        parts = [twin["level"], twin["leg"], f"Fs{twin['fs_kN']:g}", f"o{job.get('offset_s', 0.0)}"]
        if "event" in twin:
            parts += [twin["event"], twin.get("timing", "")]
        return f"{job['case']}_" + "-".join(parts)
    if "offset_s" in job:
        return f"{job['case']}_o{job['offset_s']}"
    return f"{job['case']}_e{job['eps']}"


def e3_max_drop(stroke: np.ndarray, k0: int, k1: int) -> float:
    """Max over k in [k0, k1] of mean(s[k0-3..k0-1]) - mean(s[k-2..k]) (retract sign)."""
    if k0 < 3:
        return math.nan
    ref = float(np.mean(stroke[k0 - 3:k0]))
    best = -math.inf
    for k in range(k0 + 2, min(k1, len(stroke) - 1) + 1):
        best = max(best, ref - float(np.mean(stroke[k - 2:k + 1])))
    return best


def probe_retract_segments(arr: dict) -> list[dict]:
    """Per leg, contiguous negative-command runs inside PROBE reads (gaps <= 2 zero reads merged)."""
    phase = np.array([str(p).lower() for p in arr["phase"]])
    cmd = arr["command_m_s"]
    t = arr["t_s"]
    stroke = arr["motor_stroke_m"]
    head = arr["head_pressure_Pa"]
    rod = arr["rod_pressure_Pa"]
    p_tr = arr.get("jp3_p_tr_Pa")
    x = arr.get("p1_x_m")
    need = arr.get("p1_need_m")
    is_open = arr.get("p1_is_open")
    rod_rel = arr.get("p1_rod_released")
    segs = []
    n = len(t)
    for leg in range(4):
        neg = (cmd[:, leg] < 0) & (phase == "probe")
        k = 0
        while k < n:
            if not neg[k]:
                k += 1
                continue
            k0 = k
            kend = k
            j = k + 1
            while j < n:
                if neg[j]:
                    kend = j
                    j += 1
                elif j + 2 < n and (neg[j + 1] or neg[j + 2]) and phase[j] == "probe":
                    j += 1
                else:
                    break
            k = kend + 1
            win_end = min(kend + 8, n - 1)
            seg = {"leg": LEGS[leg], "t_start_s": round(float(t[k0]), 3),
                   "t_end_s": round(float(t[kend]), 3), "reads": kend - k0 + 1,
                   "oil_cmd_mm": float(-np.sum(cmd[k0:kend + 1, leg]) * PERIOD_S * 1e3),
                   "e3_drop_mm": e3_max_drop(stroke[:, leg], k0, win_end) * 1e3,
                   "p_h_read_bar": float(head[k0 - 1, leg] / BAR) if k0 > 0 else math.nan,
                   "p_r_read_before_bar": float(rod[k0 - 1, leg] / BAR) if k0 > 0 else math.nan,
                   "p_r_read_after_bar": float(rod[win_end, leg] / BAR),
                   "stroke_before_mm": float(stroke[k0 - 1, leg] * 1e3) if k0 > 0 else math.nan}
            if p_tr is not None and k0 > 0:
                seg["p_tr_rise_bar"] = float((np.nanmax(p_tr[k0:win_end + 1, leg])
                                              - p_tr[k0 - 1, leg]) / BAR)
            if x is not None and need is not None:
                ratio = x[k0:win_end + 1, leg] / np.where(need[k0:win_end + 1, leg] > 0,
                                                          need[k0:win_end + 1, leg], np.nan)
                seg["p1_max_x_over_need"] = float(np.nanmax(ratio)) if np.any(np.isfinite(ratio)) else math.nan
                seg["p1_need_mm"] = float(np.nanmax(need[k0:win_end + 1, leg]) * 1e3)
                seg["p1_max_x_mm"] = float(np.nanmax(x[k0:win_end + 1, leg]) * 1e3)
            if is_open is not None:
                seg["p1_open_any"] = bool(np.any(is_open[k0:win_end + 1, leg]))
                ldir = arr.get("p1_line_dir")
                if ldir is not None and x is not None:
                    ret = ldir[k0:win_end + 1, leg] == -1
                    seg["p1_open_ret"] = bool(np.any(is_open[k0:win_end + 1, leg] & ret))
                    # fill / need on the retract line before the first open read
                    xs, ns_, os_ = (x[k0:win_end + 1, leg], need[k0:win_end + 1, leg],
                                    is_open[k0:win_end + 1, leg])
                    first_open = np.flatnonzero(os_ & ret)
                    stop = int(first_open[0]) if first_open.size else len(xs)
                    pre = ret[:stop] & np.isfinite(ns_[:stop]) & (ns_[:stop] > 0)
                    seg["p1_ret_x_max_mm"] = float(np.max(xs[:stop][pre]) * 1e3) if pre.any() else math.nan
                    seg["p1_ret_need_at_xmax_mm"] = (float(ns_[:stop][pre][np.argmax(xs[:stop][pre])] * 1e3)
                                                     if pre.any() else math.nan)
                    seg["p1_ret_need_first_mm"] = float(ns_[:stop][pre][0] * 1e3) if pre.any() else math.nan
            if rod_rel is not None:
                seg["p1_rod_released_any"] = bool(np.any(rod_rel[k0:win_end + 1, leg]))
            segs.append(seg)
    return segs


NEEDED = ("t_s", "phase", "command_m_s", "motor_stroke_m", "head_pressure_Pa", "rod_pressure_Pa",
          "true_force_N", "jp3_t_s", "jp3_class", "jp3_plant_state", "jp3_p_tr_Pa",
          "jp3_used_bound_Pa", "p1_x_m", "p1_need_m", "p1_is_open", "p1_rod_released", "p1_line_dir",
          "lsb_ib_on", "lsb_protected")


def load_t4h(name: str) -> tuple[dict, dict | None]:
    path = T4H / name
    with np.load(path, allow_pickle=False) as data:
        arr = {k: np.array(data[k]) for k in NEEDED if k in data.files}
        meta = json.loads(str(data["meta_json"])) if "meta_json" in data.files else None
        if "jp3_class_names" in data.files:
            arr["jp3_class_names"] = [str(s) for s in data["jp3_class_names"]]
            arr["jp3_plant_state_names"] = [str(s) for s in data["jp3_plant_state_names"]]
    return arr, meta


def d_condition_gaps(arr: dict, t_event: float) -> dict:
    """Independent ③ rev 7 condition reads: first PROBE stretch after the event, legs with a
    locked_ext -> moving_ext transition, carry_ext reads; gap = used - p_tr at the read, and
    used - p_tr at the last locked_ext read before the transition (the pre-release truth)."""
    names_c = arr["jp3_class_names"]
    names_s = arr["jp3_plant_state_names"]
    carry = names_c.index("carry_ext")
    locked_ext = names_s.index("locked_ext")
    moving_ext = names_s.index("moving_ext")
    phase = np.array([str(p).lower() for p in arr["phase"]])
    t = arr["t_s"]
    idx = np.flatnonzero((phase == "probe") & (t >= t_event))
    if not idx.size:
        return {"window": None, "reads": []}
    a = int(idx[0])
    b = a
    while b + 1 < len(phase) and phase[b + 1] == "probe":
        b += 1
    jt = arr["jp3_t_s"]
    inside = np.flatnonzero((jt >= t[a] - 1e-9) & (jt <= t[b] + 1e-9))
    st = arr["jp3_plant_state"][inside]
    cl = arr["jp3_class"][inside]
    used = arr["jp3_used_bound_Pa"][inside]
    ptr = arr["jp3_p_tr_Pa"][inside]
    reads = []
    for leg in range(4):
        trans = [k for k in range(1, len(inside)) if st[k - 1, leg] == locked_ext
                 and st[k, leg] == moving_ext]
        if not trans:
            continue
        kt = trans[0]
        pre_truth = float(ptr[kt - 1, leg])
        for k in np.flatnonzero(cl[:, leg] == carry):
            reads.append({"leg": LEGS[leg], "t_s": round(float(jt[inside[k]]), 3),
                          "t_transition_s": round(float(jt[inside[kt]]), 3),
                          "gap_read_bar": float((used[k, leg] - ptr[k, leg]) / BAR),
                          "gap_pre_release_bar": float((used[k, leg] - pre_truth) / BAR),
                          "p_tr_read_bar": float(ptr[k, leg] / BAR),
                          "p_tr_pre_release_bar": pre_truth / BAR,
                          "used_bar": float(used[k, leg] / BAR)})
    return {"window": [float(t[a]), float(t[b])], "reads": reads}


def ib_rising_edges(arr: dict) -> list[int]:
    on = arr.get("lsb_ib_on")
    if on is None:
        return [None] * 4
    out = []
    for leg in range(4):
        col = on[:, leg].astype(int)
        out.append(int(np.sum(np.diff(np.concatenate([[0], col])) == 1)))
    return out


def main() -> None:
    cond = json.loads(COND.read_text(encoding="utf-8"))
    cond_by_file = {e["t4h_file"]: e for e in cond["lines"]}
    line_rows, round_rows, seg_rows, shot_rows, d_rows = [], [], [], [], []
    anomalies = []
    event_key_counts = Counter()
    ebc_keys = None
    with ROWS.open(encoding="utf-8") as fh:
        for text in fh:
            rec = json.loads(text)
            if "error" in rec:
                anomalies.append({"line_error": rec.get("job"), "error": rec["error"][:300]})
                continue
            p = rec["ed7_probe"]
            plant, arm, part = p["plant"], p["arm"], p["part"]
            key = key_name(rec["job"])
            tag = f"{key}|{plant}|{arm}"
            names = rec.get("event_names") or {}
            for k_, v_ in names.items():
                event_key_counts[k_.split(":")[0]] += v_
            ve = rec["values"]["events"]
            eo = rec.get("event_output") or {}
            faults = sorted(set(ve.get("fault_events") or []) | set(eo.get("fault_events") or [])
                            | {k_ for k_ in names if k_.startswith("FAULT")})
            warns = sorted({k_ for k_ in names if k_.startswith("WARN")}
                           | set(ve.get("warn_events") or []))
            d6 = rec.get("probe_d6_record")
            blind = (rec.get("lsb_record") or {}).get("blind")
            ebc = (rec.get("hydraulics_record") or {}).get("extend_bound_check")
            if ebc is not None and ebc_keys is None:
                ebc_keys = sorted(ebc.keys())
            row = {"key": key, "plant": plant, "arm": arm, "part": part,
                   "head_only": rec.get("head_only_declared"), "t_event_s": rec.get("t_event_s"),
                   "final_phase": rec.get("final_phase"), "faults": ";".join(faults),
                   "warns": ";".join(warns), "commands_sha256": rec.get("commands_sha256"),
                   "min_F_after_liftoff_kN": rec["values"]["forces"]["after_liftoff"]["min_kN"],
                   "min_F_after_event_kN": (min(eo["min_F_after_event_kN"].values())
                                            if eo.get("min_F_after_event_kN") else None),
                   "event_pass": eo.get("pass"),
                   "rod_fallback": ";".join(k_ for k_ in names
                                            if k_.startswith("INFO_ROD_PRESSURE_FAULT_REASON")),
                   "n_info_d6": sum(v_ for k_, v_ in names.items()
                                    if k_.startswith("INFO_D6_NOT_OPENED")),
                   "n_warn_retract": sum(v_ for k_, v_ in names.items()
                                         if k_.startswith("WARN_PROBE_RETRACT_NOT_OPENED")),
                   "n_latch_ev": sum(v_ for k_, v_ in names.items()
                                     if k_.startswith("INFO_LSB_BLIND_LATCH")),
                   "n_protect_ev": sum(v_ for k_, v_ in names.items()
                                       if k_.startswith("INFO_LSB_BLIND_PROTECT")),
                   "n_cap_ev": sum(v_ for k_, v_ in names.items() if k_.startswith("INFO_LSB_CAP")),
                   "has_d6_record": d6 is not None, "has_blind": blind is not None}
            if ebc is not None:
                row["ebc_breach_reads"] = sum(ebc.get("breach_reads") or [0])
                row["ebc_locked_over_tol"] = sum(ebc.get("locked_breach_over_tol_reads") or [0])
                for kk in ("jp3a_breach_reads", "jp3b_breach_reads", "jp3c_breach_reads"):
                    if kk in ebc:
                        v = ebc[kk]
                        row[f"ebc_{kk}"] = sum(v) if isinstance(v, list) else v
            # --- D6 witness record checks ---
            if d6 is not None:
                rounds = d6.get("rounds") or []
                nj = d6.get("not_judgeable_rounds")
                rr = d6.get("reversed_rounds") or {}
                cnt_not_opened = [0] * 4
                cnt_rev = [0] * 4
                for r in rounds:
                    li = LEGS.index(r["leg"])
                    rr_row = {"key": key, "plant": plant, "arm": arm, "part": part, **r,
                              "rise_bar": r["rise_Pa"] / BAR, "required_bar": r["required_Pa"] / BAR,
                              "retract_witness_mm": (None if r["retract_witness_m"] is None
                                                     else r["retract_witness_m"] * 1e3)}
                    round_rows.append(rr_row)
                    if not r["is_opened"]:
                        cnt_not_opened[li] += 1
                    if r["is_reversed"]:
                        cnt_rev[li] += 1
                        if not isinstance(r.get("k1_mid_opened"), bool):
                            anomalies.append({"line": tag, "issue": "reversed round k1_mid_opened not bool", "row": r})
                    elif r.get("k1_mid_opened") is not None:
                        anomalies.append({"line": tag, "issue": "non-reversed round has k1_mid_opened", "row": r})
                    for fld in ("is_reversed", "k1_mid_opened", "retract_witness_m", "is_opened",
                                "retract_target_reached", "retract_extra_m"):
                        if fld not in r:
                            anomalies.append({"line": tag, "issue": f"round missing {fld}"})
                    wit = r["retract_witness_m"]
                    if wit is not None and (wit >= 3e-4) != r["is_opened"]:
                        anomalies.append({"line": tag, "issue": "is_opened vs witness >= 0.3 mm", "row": r})
                if nj != cnt_not_opened:
                    anomalies.append({"line": tag, "issue": "not_judgeable_rounds != rows not opened",
                                      "nj": nj, "rows": cnt_not_opened})
                if sum(cnt_not_opened) != row["n_info_d6"]:
                    anomalies.append({"line": tag, "issue": "INFO_D6 count != not-opened rows",
                                      "events": row["n_info_d6"], "rows": sum(cnt_not_opened)})
                ns = rr.get("not_substituted") or [0] * 4
                if ns != cnt_rev:
                    anomalies.append({"line": tag, "issue": "reversed_rounds.not_substituted != reversed rows",
                                      "record": ns, "rows": cnt_rev})
                row["d6_rounds"] = len(rounds)
                row["d6_not_judgeable"] = sum(cnt_not_opened)
                row["rev_not_sub"] = sum(ns)
                row["rev_sub"] = sum(rr.get("substituted") or [0] * 4)
            elif p["probe_d6"] and not rec.get("head_only_declared"):
                row["d6_missing_note"] = "probe_d6 on, event path, no record"
            # --- A_ib record ---
            if blind is not None:
                legs = blind["legs"]
                shots = blind.get("shots") or []
                for s_ in shots:
                    shot_rows.append({"key": key, "plant": plant, "arm": arm, **{
                        k_: v_ for k_, v_ in s_.items() if k_ != "delta_F_N"},
                        "dF_max_abs_kN": (None if s_.get("delta_F_N") is None
                                          else max(abs(v) for v in s_["delta_F_N"]) / 1e3)})
                tot = Counter()
                for leg in LEGS:
                    c = legs[leg]
                    ls = [s_ for s_ in shots if s_["leg"] == leg]
                    if c["triggers"] != len(c["trigger_periods"]) or c["triggers"] != len(ls):
                        anomalies.append({"line": tag, "issue": "blind triggers/periods/shots mismatch",
                                          "leg": leg, "c": c, "shots": len(ls)})
                    unk = sum(1 for s_ in ls if not s_["completion_known"])
                    if unk != c["triggers_completion_unknown"]:
                        anomalies.append({"line": tag, "issue": "completion_unknown mismatch", "leg": leg})
                    n_end = sum(c["end"].values())
                    n_open_end = sum(1 for s_ in ls if s_["end"] is None)
                    if n_end + n_open_end != c["triggers"]:
                        anomalies.append({"line": tag, "issue": "end counts mismatch", "leg": leg,
                                          "end": c["end"], "triggers": c["triggers"]})
                    sign_changes = sum(1 for a_, b_ in zip(ls, ls[1:]) if a_["sign"] != b_["sign"])
                    if c["latches"] and c["n_rev"] < 3 * c["latches"]:
                        anomalies.append({"line": tag, "issue": "latch with n_rev < 3", "leg": leg, "c": c})
                    if c["n_rev"] - c["latches"] > sign_changes:
                        anomalies.append({"line": tag, "issue": "n_rev - latches > fired sign changes",
                                          "leg": leg, "c": c, "sign_changes": sign_changes})
                    if c["n_rev"] > 0 and c["latches"] == 0 and c["n_rev"] > 2 * 1 and False:
                        pass
                    if (c["protect_blocked_periods"] > 0) != (sum(
                            v_ for k_, v_ in names.items()
                            if k_ == f"INFO_LSB_BLIND_PROTECT:{leg}") > 0):
                        anomalies.append({"line": tag, "issue": "protect periods vs event", "leg": leg})
                    if names.get(f"INFO_LSB_BLIND_LATCH:{leg}", 0) != c["latches"]:
                        anomalies.append({"line": tag, "issue": "latch event count != latches", "leg": leg,
                                          "ev": names.get(f"INFO_LSB_BLIND_LATCH:{leg}", 0), "c": c["latches"]})
                    for fld in ("triggers", "trigger_periods", "triggers_completion_unknown", "end",
                                "latches", "n_rev", "protect_blocked_periods"):
                        tot[fld] += (len(c[fld]) if isinstance(c[fld], (list, dict)) and fld != "end"
                                     else (sum(c[fld].values()) if fld == "end" else c[fld]))
                if "A_ib" not in p["components"] and sum(legs[l_]["triggers"] for l_ in LEGS):
                    anomalies.append({"line": tag, "issue": "A_ib off but blind triggers"})
                row.update({"ib_triggers": tot["triggers"], "ib_unknown": tot["triggers_completion_unknown"],
                            "ib_latches": tot["latches"], "ib_n_rev": tot["n_rev"],
                            "ib_protect_periods": tot["protect_blocked_periods"],
                            "ib_shots_grew": blind.get("shots_twist_grew"),
                            "ib_four_leg": blind.get("four_leg_twist_triggers"),
                            "ib_dD_med_kN": (float(np.median([abs(s_["delta_D_N"]) for s_ in shots
                                                              if s_["delta_D_N"] is not None])) / 1e3
                                             if any(s_["delta_D_N"] is not None for s_ in shots) else None),
                            "ib_dD_max_kN": (max(abs(s_["delta_D_N"]) for s_ in shots
                                                 if s_["delta_D_N"] is not None) / 1e3
                                             if any(s_["delta_D_N"] is not None for s_ in shots) else None),
                            "ib_trig_periods_med": (float(np.median([tp for l_ in LEGS
                                                                    for tp in legs[l_]["trigger_periods"]]))
                                                    if tot["triggers"] else None)})
            elif "A_ib" in p["components"]:
                anomalies.append({"line": tag, "issue": "A_ib on but no blind record"})
            # --- T4h ---
            name = rec.get("t4h_file")
            if name and (T4H / name).is_file():
                arr, meta = load_t4h(name)
                edges = ib_rising_edges(arr)
                if blind is not None and edges[0] is not None:
                    trig = [blind["legs"][l_]["triggers"] for l_ in LEGS]
                    if edges != trig:
                        row["ib_on_edges_vs_triggers"] = f"{edges} vs {trig}"
                if meta is not None and meta.get("probe_d6_record") is not None and d6 is not None:
                    if len(meta["probe_d6_record"]["rounds"]) != len(d6["rounds"]):
                        anomalies.append({"line": tag, "issue": "T4h meta d6 rounds != line"})
                for s_ in probe_retract_segments(arr):
                    seg_rows.append({"key": key, "plant": plant, "arm": arm, "part": part, **s_})
                # post-event LEVEL length
                if rec.get("t_event_s") is not None:
                    ph = np.array([str(x_).lower() for x_ in arr["phase"]])
                    t = arr["t_s"]
                    after = t >= rec["t_event_s"]
                    row["level_after_event_s"] = round(float(np.sum((ph == "level") & after)) * PERIOD_S, 1)
                if part == "d" or (rec.get("t_event_s") is not None and "jp3_t_s" in arr
                                   and not rec.get("head_only_declared")):
                    dc = d_condition_gaps(arr, float(rec["t_event_s"])) if rec.get("t_event_s") is not None else {"reads": []}
                    ce = cond_by_file.get(name, {})
                    reads = dc["reads"]
                    row["cond_reads_indep"] = len(reads)
                    row["cond_reads_tool"] = ce.get("condition_reads")
                    row["cond_breach_tool"] = ce.get("condition_breach_reads")
                    row["cond_state_tool"] = ce.get("state")
                    row["cond_breach_indep"] = sum(r["gap_read_bar"] * BAR < -1.0 for r in reads)
                    row["cond_min_gap_read_bar"] = min((r["gap_read_bar"] for r in reads), default=None)
                    row["cond_min_gap_pre_release_bar"] = min((r["gap_pre_release_bar"] for r in reads), default=None)
                    tool_gaps = sorted(round(r_["gap_Pa"] / BAR, 9) for r_ in ce.get("reads", []))
                    mine = sorted(round(r["gap_read_bar"], 9) for r in reads)
                    if ce and tool_gaps != mine:
                        anomalies.append({"line": tag, "issue": "condition gaps tool != independent",
                                          "tool": tool_gaps[:10], "mine": mine[:10]})
                    if part == "d":
                        for r in reads:
                            d_rows.append({"key": key, "plant": plant, "arm": arm, **r})
            line_rows.append(row)

    def write_csv(name, rows):
        if not rows:
            return
        cols = []
        for r in rows:
            for k_ in r:
                if k_ not in cols:
                    cols.append(k_)
        with (OUT / name).open("w", newline="", encoding="utf-8") as fh_:
            w = csv.DictWriter(fh_, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow({k_: (json.dumps(v_) if isinstance(v_, (dict, list)) else v_)
                            for k_, v_ in r.items()})

    write_csv("lines.csv", line_rows)
    write_csv("d6_rounds.csv", round_rows)
    write_csv("probe_retract_segments.csv", seg_rows)
    write_csv("ib_shots.csv", shot_rows)
    write_csv("d_condition_reads.csv", d_rows)
    (OUT / "anomalies.json").write_text(json.dumps(anomalies, indent=1, default=str), encoding="utf-8")
    (OUT / "event_key_counts.json").write_text(json.dumps(dict(event_key_counts.most_common()), indent=1),
                                               encoding="utf-8")
    print(json.dumps({"lines": len(line_rows), "rounds": len(round_rows), "segments": len(seg_rows),
                      "shots": len(shot_rows), "d_reads": len(d_rows), "anomalies": len(anomalies),
                      "ebc_keys": ebc_keys, "status": "ok"}))


if __name__ == "__main__":
    main()
