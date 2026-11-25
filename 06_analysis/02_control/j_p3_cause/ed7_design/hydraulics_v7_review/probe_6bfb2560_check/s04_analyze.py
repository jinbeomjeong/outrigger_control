"""Edition 7 probe (run 6bfb2560, ed7_probe_a1): record checks of the P1 supplement.

Read only. Streams ed7_probe.jsonl and opens the T4h npz of the rows it needs.

1. VBM family (gate mode ``gate_only_p1_patch``): ``rod_check_clear_count`` per row and the
   cleared ``Delta p_fill`` values.
2. Each rod check clear (t_c, leg): the next release of that leg. Expected: no
   ``p1_fill_release_log`` row and no ``p1_retract_seed_log`` row at that release (the lag starts
   at the locked truth), an extend opening at the release, no retract fill in between.
   Also every ``p1_fill_release_log`` row of every VBM row is classified by the direction of its
   release (retract expected; an extend one would be a trapped rise in an extend M2 start).
3. Void share trap: neutral holds of a locked retract line (x held with drain > 0) in lock
   intervals without any fill rise evidence (the floor can only be ``min(void_fill_m, void)``);
   record caps (``*_truncated`` keys, lists at their caps).
4. Old plant L: ``stale_seed_release`` counts against the lock log seed count.

Usage: python -I -B s04_analyze.py <jsonl> <t4h dir> <out json>
"""
from __future__ import annotations

import collections
import json
import math
import sys
from pathlib import Path

import numpy as np

JSONL = Path(sys.argv[1])
T4H_DIR = Path(sys.argv[2])
OUT = Path(sys.argv[3])

M_FAMILY = ("M", "Mslow", "Mfast", "Mc005", "Mc04")
MAX_LOGGED_FILLS = 600          # check_open_delay.MAX_LOGGED_FILLS
MAX_LOGGED_LOCK_EVENTS = 2000   # harness_hydraulics.MAX_LOGGED_LOCK_EVENTS
OPEN_WINDOW_S = 0.003           # fill open time (3 decimals, chunk start) before the release
TIME_TOL_S = 1e-6
EPS_M_S = 1e-6
LEGS = ("FL", "FR", "RL", "RR")


def releases_of(lock_events, leg):
    return sorted(t for t, i, locked in lock_events if int(i) == leg and not locked)


def locks_of(lock_events, leg):
    return sorted(t for t, i, locked in lock_events if int(i) == leg and locked)


def fills_near(fills, leg, direction, t_rel):
    return [row for row in fills
            if int(row[2]) == leg and int(row[3]) == direction
            and t_rel - OPEN_WINDOW_S <= float(row[1]) <= t_rel + TIME_TOL_S]


def fills_between(fills, leg, direction, t0, t1):
    return [row for row in fills
            if int(row[2]) == leg and int(row[3]) == direction and t0 < float(row[1]) <= t1]


def has_row_at(rows, t_col, leg_col, t, leg):
    return [row for row in rows
            if int(row[leg_col]) == leg and abs(float(row[t_col]) - t) <= TIME_TOL_S]


class T4h:
    """Lazy T4h arrays of one row."""

    def __init__(self, path: Path):
        with np.load(path, allow_pickle=False) as data:
            self.t = data["t_s"]
            self.rod = data["rod_pressure_Pa"]
            self.locked = data["locked"]
            self.cmd = data["command_m_s"]
            self.x = data["p1_x_m"]
            self.need = data["p1_need_m"]
            self.drain = data["p1_drain_m_s"]
            self.valve = data["p1_valve_speed_m_s"]
            self.line_dir = data["p1_line_dir"]
            self.found = data["p1_read_found"]

    def first_read_after(self, t):
        idx = np.flatnonzero(self.t >= t - TIME_TOL_S)
        return None if len(idx) == 0 else int(idx[0])

    def last_read_before(self, t):
        idx = np.flatnonzero(self.t < t - TIME_TOL_S)
        return None if len(idx) == 0 else int(idx[-1])


def release_direction_from_t4h(t4h: T4h, leg: int, t_rel: float):
    """Sign of the valve speed in front of the gate on the first read after the release and
    of the command of the read before it (record evidence only)."""
    k_after = t4h.first_read_after(t_rel)
    k_before = t4h.last_read_before(t_rel)
    valve_after = None if k_after is None else float(t4h.valve[k_after, leg])
    cmd_before = None if k_before is None else float(t4h.cmd[k_before, leg])
    return {"valve_after_mm_s": None if valve_after is None else round(valve_after * 1e3, 4),
            "cmd_before_mm_s": None if cmd_before is None else round(cmd_before * 1e3, 4)}


def classify_release(fills, fills_capped, leg, t_rel, t4h):
    ret = fills_near(fills, leg, -1, t_rel)
    ext = fills_near(fills, leg, 1, t_rel)
    evidence = release_direction_from_t4h(t4h, leg, t_rel)
    if ret and not ext:
        kind = "retract"
    elif ext and not ret:
        kind = "extend"
    elif ret and ext:
        kind = "both"
    else:
        valve = evidence["valve_after_mm_s"]
        if fills_capped and fills and t_rel > float(fills[-1][1]):
            kind = "unknown_fills_capped"
        elif valve is not None and valve < -EPS_M_S * 1e3:
            kind = "retract_by_valve"
        elif valve is not None and valve > EPS_M_S * 1e3:
            kind = "extend_by_valve"
        else:
            kind = "unmatched"
    return kind, evidence


def void_hold_episodes(t4h: T4h, lock_events, fill_release_log, clear_log):
    """Neutral holds of a locked retract line whose lock interval has no fill-rise evidence."""
    out = []
    n = len(t4h.t)
    for leg in range(4):
        rels = releases_of(lock_events, leg)
        locks = locks_of(lock_events, leg)
        for k in range(n - 1):
            if not (t4h.found[k] and t4h.found[k + 1]):
                continue
            ok = True
            for j in (k, k + 1):
                if not (t4h.locked[j, leg] and int(t4h.line_dir[j, leg]) == -1
                        and abs(float(t4h.valve[j, leg])) <= EPS_M_S):
                    ok = False
            if not ok:
                continue
            x0, x1 = float(t4h.x[k, leg]), float(t4h.x[k + 1, leg])
            drain = float(t4h.drain[k + 1, leg])
            dt = float(t4h.t[k + 1] - t4h.t[k])
            if not (x0 > 1e-9 and math.isfinite(drain) and drain > 0.0):
                continue
            free_loss = drain * dt
            if not (free_loss > 0.2 * x0 and x1 >= 0.98 * x0):
                continue
            t_read = float(t4h.t[k + 1])
            t_lock = max([t for t in locks if t <= t_read], default=None)
            t_next_rel = min([t for t in rels if t > t_read], default=None)
            lo = -1.0 if t_lock is None else t_lock
            hi = math.inf if t_next_rel is None else t_next_rel
            rise_rel = (t_next_rel is not None
                        and bool(has_row_at(fill_release_log, 0, 1, t_next_rel, leg)))
            rise_clear = any(int(r[1]) == leg and lo < float(r[0]) <= hi for r in clear_log)
            out.append({"leg": LEGS[leg], "t_read": round(t_read, 3),
                        "x_mm": round(x1 * 1e3, 4), "need_mm": round(float(t4h.need[k + 1, leg]) * 1e3, 4),
                        "drain_mm_s": round(drain * 1e3, 4),
                        "rod_read_bar": round(float(t4h.rod[k + 1, leg]) / 1e5, 3),
                        "t_lock": t_lock, "t_next_release": t_next_rel,
                        "rise_evidence": bool(rise_rel or rise_clear),
                        "rise_by_release_row": rise_rel, "rise_by_clear": rise_clear})
    return out


def merge_episodes(reads):
    """Consecutive held reads of one leg in one lock interval -> one episode."""
    episodes = []
    for row in sorted(reads, key=lambda r: (r["leg"], r["t_read"])):
        last = episodes[-1] if episodes else None
        if (last and last["leg"] == row["leg"] and last["t_lock"] == row["t_lock"]
                and abs(row["t_read"] - last["t_end"] - 0.1) < 0.011):
            last["t_end"] = row["t_read"]
            last["reads"] += 1
            last["x_mm_min"] = min(last["x_mm_min"], row["x_mm"])
            last["x_mm_max"] = max(last["x_mm_max"], row["x_mm"])
            last["rod_read_bar_max"] = max(last["rod_read_bar_max"], row["rod_read_bar"])
            continue
        episodes.append({"leg": row["leg"], "t_start": row["t_read"], "t_end": row["t_read"],
                         "reads": 1, "x_mm_min": row["x_mm"], "x_mm_max": row["x_mm"],
                         "need_mm": row["need_mm"], "drain_mm_s": row["drain_mm_s"],
                         "rod_read_bar_max": row["rod_read_bar"], "t_lock": row["t_lock"],
                         "t_next_release": row["t_next_release"],
                         "rise_evidence": row["rise_evidence"]})
    return episodes


def main():
    result = {"m_rows": 0, "l_rows": 0, "clear_rows": [], "clear_events": [],
              "fill_release_kinds": collections.Counter(), "fill_release_extend": [],
              "fill_release_odd": [], "seed_count_mismatch": [], "caps": collections.Counter(),
              "cap_rows": [], "void_episodes": [], "void_reads_total": collections.Counter(),
              "l_stale": [], "l_anomalies": [], "clear_counts_by": {},
              "rows_by_plant": collections.Counter()}
    clear_by = collections.defaultdict(lambda: [0, 0, 0])  # rows, rows with clears, clears
    with JSONL.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            probe = row.get("ed7_probe") or {}
            plant, arm, part = probe.get("plant"), probe.get("arm"), probe.get("part")
            setting = row["job"]["setting"]
            stem = row["t4h_file"][:-4]
            key = stem[: -len(setting) - 1]
            hr = row.get("hydraulics_record") or {}
            result["rows_by_plant"][plant] += 1
            ident = {"plant": plant, "arm": arm, "part": part, "key": key,
                     "t4h": row["t4h_file"], "final_phase": row.get("final_phase"),
                     "harness_class": row.get("harness_class")}
            lock_events = hr.get("lock_events", [])
            if len(lock_events) >= MAX_LOGGED_LOCK_EVENTS:
                result["caps"]["lock_events_at_cap"] += 1
            if plant == "L":
                result["l_rows"] += 1
                stale = hr.get("stale_seed_release")
                seed_count = hr.get("p1_retract_seed_count")
                entry = {**ident, "stale": None if stale is None else
                         {k: stale[k] for k in ("releases_with_seed", "stale_releases",
                                                "log_rows", "log_truncated")},
                         "p1_retract_seed_count": seed_count,
                         "lock_releases": sum(1 for e in lock_events if not e[2])}
                problems = []
                if stale is None:
                    problems.append("no stale_seed_release key")
                else:
                    if stale["log_rows"] != min(stale["releases_with_seed"], MAX_LOGGED_LOCK_EVENTS):
                        problems.append("log_rows != min(releases, cap)")
                    if stale["log_truncated"] != (stale["releases_with_seed"] > stale["log_rows"]):
                        problems.append("log_truncated inconsistent")
                    if stale["log_truncated"]:
                        problems.append("log_truncated true")
                    if not 0 <= stale["stale_releases"] <= stale["releases_with_seed"]:
                        problems.append("stale outside [0, releases]")
                    if seed_count is not None and seed_count != stale["releases_with_seed"]:
                        problems.append(f"releases_with_seed {stale['releases_with_seed']} != "
                                        f"lock_log seed count {seed_count}")
                    n_stale_log = sum(1 for r in stale["log"] if r[2])
                    if not stale["log_truncated"] and n_stale_log != stale["stale_releases"]:
                        problems.append("stale_releases != stale rows of log")
                    if stale["releases_with_seed"] > entry["lock_releases"]:
                        problems.append("more seeded releases than releases")
                    # seed rows of the old plant: seed vs locked pressure (bar)
                    entry["stale_log_seed_minus_locked_bar"] = [
                        round((float(r[3]) - float(r[4])) / 1e5, 3) for r in stale["log"] if r[2]]
                entry["problems"] = problems
                result["l_stale"].append(entry)
                if problems:
                    result["l_anomalies"].append(entry)
                continue
            if plant not in M_FAMILY:
                continue
            result["m_rows"] += 1
            gate = hr["line_fill_gate"]
            fills = gate.get("fills", [])
            fills_capped = len(fills) >= MAX_LOGGED_FILLS
            ext_capped = len(gate.get("ext_starts", [])) >= MAX_LOGGED_FILLS
            clear_log = gate.get("rod_check_clear_log", [])
            clear_count = gate.get("rod_check_clear_count", 0)
            truncated = gate.get("rod_check_clear_log_truncated")
            fill_release_log = hr.get("p1_fill_release_log", [])
            seed_log = hr.get("p1_retract_seed_log", [])
            seed_count = hr.get("p1_retract_seed_count")
            cap_flags = {"fills_at_cap": fills_capped, "ext_starts_at_cap": ext_capped,
                         "rod_check_clear_log_truncated": bool(truncated),
                         "fill_release_log_at_cap": len(fill_release_log) >= MAX_LOGGED_LOCK_EVENTS,
                         "seed_log_at_cap": len(seed_log) >= MAX_LOGGED_LOCK_EVENTS,
                         "lock_log_at_cap": len(hr.get("lock_log", [])) >= MAX_LOGGED_LOCK_EVENTS}
            for name, flag in cap_flags.items():
                result["caps"][name] += int(flag)
            if any(cap_flags.values()):
                result["cap_rows"].append({**ident, **cap_flags, "fills": len(fills),
                                           "ext_starts": len(gate.get("ext_starts", []))})
            if seed_count != len(fill_release_log) or len(seed_log) != len(fill_release_log):
                result["seed_count_mismatch"].append(
                    {**ident, "seed_count": seed_count, "seed_log": len(seed_log),
                     "fill_release_log": len(fill_release_log)})
            by = clear_by[(plant, arm, part)]
            by[0] += 1
            by[1] += int(clear_count > 0)
            by[2] += clear_count
            t4h = T4h(T4H_DIR / row["t4h_file"])
            # 2b. every fill release row: direction of its release
            for r in fill_release_log:
                t_rel, leg = float(r[0]), int(r[1])
                kind, evidence = classify_release(fills, fills_capped, leg, t_rel, t4h)
                result["fill_release_kinds"][kind] += 1
                seed_rows = has_row_at(seed_log, 0, 1, t_rel, leg)
                seed_ok = (len(seed_rows) == 1
                           and abs(float(seed_rows[0][5]) - float(r[3])) <= 1e-6 * max(1.0, abs(float(r[3]))))
                item = {**ident, "t_release": t_rel, "leg": LEGS[leg],
                        "rise_bar": round(float(r[3]) / 1e5, 3), "kind": kind, **evidence,
                        "seed_row_matches": seed_ok}
                if kind in ("extend", "extend_by_valve", "both"):
                    result["fill_release_extend"].append(item)
                elif kind != "retract" or not seed_ok:
                    result["fill_release_odd"].append(item)
            # 1/2. clear events
            if clear_count > 0:
                result["clear_rows"].append({**ident, "count": clear_count,
                                             "log_rows": len(clear_log),
                                             "truncated": bool(truncated)})
            for c in clear_log:
                t_c, leg, cleared = float(c[0]), int(c[1]), float(c[2])
                rels = [t for t in releases_of(lock_events, leg) if t > t_c - TIME_TOL_S]
                t_rel = rels[0] if rels else None
                event = {**ident, "t_clear": t_c, "leg": LEGS[leg],
                         "cleared_bar": round(cleared / 1e5, 3), "t_release": t_rel}
                k_before = t4h.last_read_before(t_c + TIME_TOL_S)
                k_after = t4h.first_read_after(t_c + TIME_TOL_S)
                if k_before is not None and k_after is not None:
                    event["rod_read_before_bar"] = round(float(t4h.rod[k_before, leg]) / 1e5, 3)
                    event["rod_read_after_bar"] = round(float(t4h.rod[k_after, leg]) / 1e5, 3)
                    event["read_after_t"] = round(float(t4h.t[k_after]), 3)
                    event["read_after_locked"] = bool(t4h.locked[k_after, leg])
                if t_rel is None:
                    event["status"] = "no release after clear (run end locked)"
                else:
                    event["window_s"] = round(t_rel - t_c, 4)
                    event["fill_release_row_at_release"] = bool(
                        has_row_at(fill_release_log, 0, 1, t_rel, leg))
                    event["seed_row_at_release"] = bool(has_row_at(seed_log, 0, 1, t_rel, leg))
                    event["extend_open_at_release"] = bool(fills_near(fills, leg, 1, t_rel))
                    event["retract_fill_between"] = bool(fills_between(fills, leg, -1, t_c, t_rel))
                    kind, evidence = classify_release(fills, fills_capped, leg, t_rel, t4h)
                    event["release_kind"] = kind
                    event.update(evidence)
                    lock_rows = [lr for lr in hr.get("lock_log", [])
                                 if int(lr[1]) == leg and lr[9] is not None
                                 and abs(float(lr[9]) - t_rel) <= TIME_TOL_S]
                    if lock_rows:
                        lr = lock_rows[0]
                        event["lock_log"] = {"t_lock": lr[0], "direction_at_lock": lr[2],
                                             "release_cause": lr[10],
                                             "gate_wait_s": round(float(lr[11]), 4),
                                             "dp_tr_lock_bar": round(float(lr[13]) / 1e5, 3)}
                    ok = (not event["fill_release_row_at_release"]
                          and not event["seed_row_at_release"]
                          and not event["retract_fill_between"])
                    event["status"] = "lag start = locked truth" if ok else "CHECK"
                result["clear_events"].append(event)
            # 3. void share holds
            reads = void_hold_episodes(t4h, lock_events, fill_release_log, clear_log)
            for r in reads:
                result["void_reads_total"]["rise_evidence" if r["rise_evidence"]
                                           else "no_rise_evidence"] += 1
            for ep in merge_episodes(reads):
                result["void_episodes"].append({**ident, **ep})
    result["clear_counts_by"] = {f"{p}|{a}|{q}": v for (p, a, q), v in sorted(clear_by.items())}
    result["fill_release_kinds"] = dict(result["fill_release_kinds"])
    result["caps"] = dict(result["caps"])
    result["void_reads_total"] = dict(result["void_reads_total"])
    result["rows_by_plant"] = dict(result["rows_by_plant"])
    OUT.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8", newline="\n")
    # short console summary
    print("rows", result["rows_by_plant"], "M family", result["m_rows"], "L", result["l_rows"])
    print("rows with clear > 0:", len(result["clear_rows"]),
          "clear events:", len(result["clear_events"]))
    print("fill release kinds:", result["fill_release_kinds"])
    print("fill release on extend:", len(result["fill_release_extend"]),
          "odd:", len(result["fill_release_odd"]))
    print("seed count mismatches:", len(result["seed_count_mismatch"]))
    print("caps:", result["caps"])
    print("void hold reads:", result["void_reads_total"],
          "episodes:", len(result["void_episodes"]),
          "no-rise episodes:", sum(1 for e in result["void_episodes"] if not e["rise_evidence"]))
    print("L anomalies:", len(result["l_anomalies"]))


if __name__ == "__main__":
    main()
