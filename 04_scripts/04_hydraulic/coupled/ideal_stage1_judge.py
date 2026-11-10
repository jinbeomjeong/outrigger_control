"""Path-1 aggregation of the ideal-sensor diagnosis stage 1 (plan 8.8; no verdict grades).

Reads the run lines ``ideal_<bundle>_<variant>[_resume].jsonl`` of ``ideal_sensor_targeted.py``
and, when present, ``ideal_HF.json`` / ``ideal_HF_g4_old.json`` of ``r64_g4_ideal_s4.py`` in
one folder (read only). Pairs are (bundle arm, row id): SHD against each variant. Writes the
metrics M-1 .. M-12 per pair, their set totals, the gates G-1 .. G-4 and per direction
prediction P-* ``holds`` (true / false / null = not decidable from the lines).

Usage (python-dev or dynamics-dev, ``-I -B``):
  python -I -B 04_scripts/04_hydraulic/coupled/ideal_stage1_judge.py [<ideal folder>]
      [--out <json>]
Exit codes: 0 written, 2 input error (no lines, unreadable file, existing output). The last
stdout line is JSON.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
IDEAL_DIR = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "las" / "ideal"
PLAN_SHA256_LIST = ("06c9c6b0e90db290b84a96523cbe0570ddcb1bb82d0d5277bb6037f06f260455",
                    "0d3bb1b80a357eeb2bf0a90382ca92f6674322517d721a149ca43f667598a189")
VARIANTS = ("SHD", "IGA", "IGB", "IZ", "S4")
STROKE_GUARD_M = 0.6828
F_MIN_KN = 9.415
FALSE_SOIL_MODE_DELAY_S = 0.05
"""Plan 1.1 / M-8: a soil mode later than the true lift-off by more than this is false."""
SGS_EVENT = "FAULT_LIFT_STROKE_LIMIT"
READY_DELTA_LIMIT_S = 2.0
PRESSURE_EVENTS = ("FAULT_HEAD_PRESSURE", "WARN_ROD_PRESSURE_FALLBACK",
                   "WARN_CRAWLER_RECONTACT_SUSPECTED")


# ------------------------------------------------------------------------------- reading
def read_lines(folder: Path) -> list[dict]:
    lines = []
    for path in sorted(folder.glob("ideal_*_*.jsonl")):
        for text in path.read_text(encoding="utf-8").splitlines():
            if text.strip():
                lines.append(json.loads(text))
    return lines


def ideal_of(line: dict) -> dict:
    return line.get("ideal") or (line.get("rev") or {}).get("ideal") or {}


def latest_finished(lines: list[dict]) -> dict[tuple, dict]:
    """(bundle, variant, arm, key) -> the finished line (a re-run replaces the first)."""
    out = {}
    for line in lines:
        if "error" in line:
            continue
        ideal = ideal_of(line)
        out[(ideal["bundle"], ideal["variant"], ideal["k1_arm"], ideal["key"])] = line
    return out


# ------------------------------------------------------------------------------- metrics
def _get(mapping: dict | None, *names):
    value = mapping
    for name in names:
        if not isinstance(value, dict):
            return None
        value = value.get(name)
    return value


def verdict(line: dict) -> str:
    """M-1: ``d1.verdict`` as it is (plan 7.1). The final phase is not used: a run ending in a
    fault phase keeps its ``d1`` grade (an SGS safe stop is ``allowed_stop``)."""
    return _get(line, "d1", "verdict")


def end_attitude_deg(line: dict) -> list[float | None]:
    """M-12: end |roll|, |pitch| [deg] from the result line ``values.attitude.end_abs_deg``.

    Plan 7.1 gives no rounding; plan 8 computes the metrics from the result line fields
    (``values``, ``d1``). This is the field the runner writes (rounded there to 1e-5 deg) and the
    one path 2 reads; the unrounded ``ideal.final_attitude_deg`` used before differed from it by
    up to 5e-6 deg (M-12 mismatch of the path comparison, 2026-11-10)."""
    end = _get(line, "values", "attitude", "end_abs_deg") or {}
    return [end.get("roll"), end.get("pitch")]


def fault_names(line: dict) -> dict[str, int]:
    """M-3: FAULT events by name (``FAULT_LIFT_STROKE_LIMIT:soil`` kept apart)."""
    out: dict[str, int] = {}
    for name, count in (line.get("event_names") or {}).items():
        if not str(name).startswith("FAULT"):
            continue
        parts = str(name).split(":")
        key = ":".join(parts[:2]) if parts[0] == SGS_EVENT and len(parts) > 1 and \
            parts[1] == "soil" else parts[0]
        out[key] = out.get(key, 0) + int(count or 0)
    return out


def is_sgs_stop(line: dict) -> bool:
    return verdict(line) == "allowed_stop" or any(
        name.startswith(SGS_EVENT) for name in fault_names(line))


def _nearest_index(times: list[float], t_s: float | None) -> int | None:
    if t_s is None or not times:
        return None
    return min(range(len(times)), key=lambda index: abs(times[index] - t_s))


def clearance_errors_mm(ideal: dict, t_s: float | None) -> dict | None:
    """M-10 at ``t_s``: ``c_min - g_box_min`` and ``c_corr_min - g_box_min`` [mm]."""
    periods = ideal.get("periods") or {}
    index = _nearest_index(periods.get("t_s") or [], t_s)
    if index is None:
        return None
    g_min = periods["g_min"][index]
    return {"c_minus_g_mm": (periods["c_min"][index] - g_min) * 1e3,
            "c_corr_minus_g_mm": (periods["c_corr_min"][index] - g_min) * 1e3}


def first_soil_start_s(ideal: dict) -> float | None:
    starts = ideal.get("soil_mode_starts") or []
    return starts[0]["t_s"] if starts else None


def is_f2_path(ideal: dict) -> bool:
    """M-9: the first R4 decision blocked and no R4 margin to the end (K1 limit F2)."""
    decisions = ideal.get("order_gate_decisions") or []
    if not decisions:
        return False
    first = decisions[0]
    return bool(first.get("would_block") and not first.get("applied")
                and not ideal.get("flat_soil_margin_applied"))


def metrics(line: dict) -> dict:
    """M-1 .. M-12 of one line."""
    ideal = ideal_of(line)
    t_lift = _get(line, "values", "forces", "t_lift_s")
    t_loc = ideal.get("t_loc_first_s")
    t_soil = first_soil_start_s(ideal)
    after = _get(line, "values", "forces", "after_liftoff", "min_kN")
    stroke = _get(line, "d1", "stroke_max_m")
    items = _get(line, "d1", "items") or {}
    counts = dict(ideal.get("pressure_event_counts") or {})
    return {
        "M-1": verdict(line), "M-2": _get(line, "d1", "t_ready_s"), "M-3": fault_names(line),
        "M-4_mm": None if stroke is None else (STROKE_GUARD_M - stroke) * 1e3,
        "s_max_mm": None if stroke is None else stroke * 1e3,
        "M-5_kN": None if after is None else after - F_MIN_KN,
        "M-6": {"P3-1": items.get("P3-1"), "P3-5": items.get("P3-5")},
        "M-7_s": None if t_loc is None or t_lift is None else t_loc - t_lift,
        "M-8": {"false_loc": bool(ideal.get("false_loc")),
                "false_soil_mode": (t_soil is not None and t_lift is not None
                                    and t_soil > t_lift + FALSE_SOIL_MODE_DELAY_S),
                "false_soil_mode_ideal": bool(ideal.get("false_soil_mode")),
                "soil_mode_started": t_soil is not None},
        "M-9": {"revokes": len(ideal.get("loc_revokes") or []), "f2": is_f2_path(ideal)},
        "M-10": {"loc": clearance_errors_mm(ideal, t_loc),
                 "ready": clearance_errors_mm(ideal, _get(line, "d1", "t_ready_s"))},
        "M-11": counts,
        "M-12_deg": end_attitude_deg(line),
        "r4_decisions": len(ideal.get("order_gate_decisions") or []),
        "sgs_stop": is_sgs_stop(line), "commands_sha256": line.get("commands_sha256"),
        "matches_stored": ideal.get("matches_stored"), "set": ideal.get("set")}


def pair_record(base: dict, other: dict) -> dict:
    """SHD ``base`` against ``other`` (same bundle, arm and key)."""
    a, b = metrics(base), metrics(other)

    def delta(name):
        return None if a[name] is None or b[name] is None else b[name] - a[name]

    return {"set": a["set"], "shd": a, "variant": b,
            "verdict_transition": f"{a['M-1']}->{b['M-1']}",
            "hash_equal": a["commands_sha256"] == b["commands_sha256"],
            "dt_ready_s": delta("M-2"), "ds_max_mm": delta("s_max_mm"),
            "dF_kN": delta("M-5_kN")}


# ------------------------------------------------------------------------------- aggregation
def _median(values) -> float | None:
    values = [value for value in values if value is not None]
    return statistics.median(values) if values else None


def build_pairs(finished: dict[tuple, dict]) -> dict[tuple, dict]:
    """(bundle, variant, arm, key) -> pair record for every non-SHD line with an SHD line."""
    pairs = {}
    for (bundle, variant, arm, key), line in finished.items():
        if variant == "SHD":
            continue
        base = finished.get((bundle, "SHD", arm, key))
        if base is not None:
            pairs[(bundle, variant, arm, key)] = pair_record(base, line)
    return pairs


def set_totals(pairs: dict[tuple, dict]) -> dict:
    """Per (bundle, variant, arm, set): counts and medians of the pairs."""
    groups: dict[str, list[dict]] = {}
    for (bundle, variant, arm, _), pair in pairs.items():
        groups.setdefault(f"{bundle}|{variant}|{arm}|{pair['set']}", []).append(pair)
    out = {}
    for name, items in sorted(groups.items()):
        transitions: dict[str, int] = {}
        for item in items:
            transitions[item["verdict_transition"]] = transitions.get(
                item["verdict_transition"], 0) + 1
        out[name] = {
            "pairs": len(items), "hash_equal": sum(item["hash_equal"] for item in items),
            "verdict_transitions": transitions,
            "median_dt_ready_s": _median(item["dt_ready_s"] for item in items),
            "median_ds_max_mm": _median(item["ds_max_mm"] for item in items),
            "sgs_stops": {"shd": sum(item["shd"]["sgs_stop"] for item in items),
                          "variant": sum(item["variant"]["sgs_stop"] for item in items)},
            "false_loc": {"shd": sum(item["shd"]["M-8"]["false_loc"] for item in items),
                          "variant": sum(item["variant"]["M-8"]["false_loc"] for item in items)},
            "false_soil_mode": {
                "shd": sum(item["shd"]["M-8"]["false_soil_mode"] for item in items),
                "variant": sum(item["variant"]["M-8"]["false_soil_mode"] for item in items)},
            "median_M7_s": {"shd": _median(item["shd"]["M-7_s"] for item in items),
                            "variant": _median(item["variant"]["M-7_s"] for item in items)},
            "revokes": {"shd": sum(item["shd"]["M-9"]["revokes"] for item in items),
                        "variant": sum(item["variant"]["M-9"]["revokes"] for item in items)},
            "f2": {"shd": sum(item["shd"]["M-9"]["f2"] for item in items),
                   "variant": sum(item["variant"]["M-9"]["f2"] for item in items)}}
    return out


def _select(pairs, bundle: str, variants, sets, arm: str = "on") -> list[dict]:
    return [pair for (b, variant, a, _), pair in pairs.items()
            if b == bundle and variant in variants and pair["set"] in sets and a == arm]


# ------------------------------------------------------------------------------- gates
def gates(finished: dict[tuple, dict], pairs: dict[tuple, dict], hf: dict | None,
          hf_old: dict | None) -> dict:
    shd = [line for (_, variant, _, _), line in finished.items() if variant == "SHD"]
    g1 = {"shd_lines": len(shd), "match_stored": sum(bool(ideal_of(line).get("matches_stored"))
                                                       for line in shd)}
    iz_f = _select(pairs, "I-1", ("IZ",), ("F",))
    g2 = {"pairs": len(iz_f), "hash_equal": sum(pair["hash_equal"] for pair in iz_f)}
    g3_items = []
    for (bundle, variant, arm, key), line in finished.items():
        if variant != "IGA" or ideal_of(line).get("set") not in ("A_P0", "A_boundary_P0"):
            continue
        other = finished.get((bundle, "IGB", arm, key))
        if other is not None:
            g3_items.append(line["commands_sha256"] == other["commands_sha256"])
    g3 = {"pairs": len(g3_items), "hash_equal": sum(g3_items)}
    g4 = {"ii": None if hf is None else hf.get("g4_ii"),
          "i": None if hf_old is None else {"rows": hf_old["meta"]["rows"],
                                            "same": hf_old["meta"]["same"]}}
    return {"G-1": g1, "G-2": g2, "G-3": g3, "G-4": g4}


# ------------------------------------------------------------------------------- predictions
def _holds(condition, decidable: bool) -> bool | None:
    return bool(condition) if decidable else None


def _in(value, low, high) -> bool:
    return value is not None and low <= value <= high


def predictions(pairs: dict[tuple, dict], hf: dict | None) -> list[dict]:
    """Plan 7.2 predictions (rev1 R1-5 premises): observed values and ``holds``."""
    out = []

    def add(name, prediction, observed, holds):
        out.append({"id": name, "prediction": prediction, "observed": observed,
                    "holds": holds})

    a_ig = _select(pairs, "I-1", ("IGA", "IGB"), ("A_P0",))
    no_soil = sum(not p["variant"]["M-8"]["soil_mode_started"] and
                  p["variant"]["r4_decisions"] == 0 for p in a_ig)
    add("P-A1 IGA/IGB", "no soil mode and no R4 decision on 5/5 each",
        f"{no_soil}/{len(a_ig)}", _holds(no_soil == len(a_ig), len(a_ig) == 10))
    a_iz = _select(pairs, "I-1", ("IZ",), ("A_P0",))
    gone = sum(p["shd"]["M-8"]["false_soil_mode"] and not p["variant"]["M-8"]["false_soil_mode"]
               for p in a_iz)
    add("P-A1 IZ", "false soil mode gone on >= 3/5", f"{gone}/{len(a_iz)}",
        _holds(gone >= 3, len(a_iz) == 5))
    iga = {key: p for (b, v, a, key), p in pairs.items() if b == "I-1" and v == "IGA"
           and p["set"] == "A_P0"}
    igb = {key: p for (b, v, a, key), p in pairs.items() if b == "I-1" and v == "IGB"
           and p["set"] == "A_P0"}
    same = sum(iga[key]["variant"]["commands_sha256"] == igb[key]["variant"]["commands_sha256"]
               for key in iga if key in igb)
    add("P-A2", "IGA and IGB hashes equal on A_P0", f"{same}/{len(iga)}",
        _holds(same == len(iga), len(iga) == 5 and len(igb) == 5))
    ds = [p["ds_max_mm"] for p in _select(pairs, "I-1", ("IGA",), ("A_P0",))]
    add("P-A3", "IGA - SHD s_max in [0, +15] mm, median about +9",
        {"values": ds, "median": _median(ds)},
        _holds(all(_in(v, 0.0, 15.0) for v in ds), len(ds) == 5))
    out.append(_p_a4(pairs))
    b_ig = _select(pairs, "I-1", ("IGA", "IGB"), ("B",))
    false_loc = sum(p["variant"]["M-8"]["false_loc"] for p in b_ig)
    delays = [p["variant"]["M-7_s"] for p in b_ig]
    add("P-B1", "B IGA/IGB: false LOC 0/8 and t_LOC - t_lift in [+0.1, +0.3] s",
        {"false_loc": false_loc, "delays_s": delays},
        _holds(false_loc == 0 and all(_in(v, 0.1, 0.3) for v in delays), len(b_ig) == 16))
    out.append(_p_b2(pairs))
    b_iz = _select(pairs, "I-1", ("IZ",), ("B",))
    kept = sum(p["variant"]["M-8"]["false_loc"] for p in b_iz)
    add("P-B3", "B IZ: false LOC stays 8/8", f"{kept}/{len(b_iz)}",
        _holds(kept == len(b_iz), len(b_iz) == 8))
    for variant in ("IGA", "IZ"):
        items = _select(pairs, "I-1", (variant,), ("C",))
        median = _median(p["ds_max_mm"] for p in items)
        stops = (sum(p["shd"]["sgs_stop"] for p in items),
                 sum(p["variant"]["sgs_stop"] for p in items))
        add(f"P-C1 {variant}", "C: s_max up (median +3 .. +12 mm), SGS stops equal or more",
            {"median_ds_max_mm": median, "sgs_stops_shd_variant": stops},
            _holds(_in(median, 3.0, 12.0) and stops[1] >= stops[0], len(items) == 67))
    out.append(_p_c2(pairs))
    for variant in ("IGA", "IGB"):
        items = [p for (b, v, _, _), p in pairs.items() if b == "I-1" and v == variant]
        median = _median(p["variant"]["M-7_s"] for p in items)
        add(f"P-L1 {variant}", "M-7 median <= +0.3 s", median,
            _holds(median is not None and median <= 0.3, len(items) == 161))
        revokes = (sum(p["shd"]["M-9"]["revokes"] for p in items),
                   sum(p["variant"]["M-9"]["revokes"] for p in items))
        f2 = (sum(p["shd"]["M-9"]["f2"] for p in items),
              sum(p["variant"]["M-9"]["f2"] for p in items))
        add(f"P-L2 {variant}", "revocations and F2 paths equal or fewer",
            {"revokes_shd_variant": revokes, "f2_shd_variant": f2},
            _holds(revokes[1] <= revokes[0] and f2[1] <= f2[0], len(items) == 161))
    for variant in ("IGA", "IGB", "IZ"):
        items = _select(pairs, "I-1", (variant,), ("E", "F"))
        new_fail = sum(p["shd"]["M-1"] != "fail" and p["variant"]["M-1"] == "fail"
                       for p in items)
        close = sum(p["dt_ready_s"] is not None and abs(p["dt_ready_s"]) <= READY_DELTA_LIMIT_S
                    for p in items)
        add(f"P-E1 {variant}", "E+F: new fail <= 1/80, |dREADY| <= 2 s on >= 90 %",
            {"new_fail": new_fail, "ready_close": close, "pairs": len(items)},
            _holds(new_fail <= 1 and close >= 0.9 * len(items), len(items) == 80))
    f_iz = _select(pairs, "I-1", ("IZ",), ("F",))
    equal = sum(p["hash_equal"] for p in f_iz)
    add("P-F1", "F IZ: 40/40 hashes equal SHD", f"{equal}/{len(f_iz)}",
        _holds(equal == len(f_iz), len(f_iz) == 40))
    out += _p_s(pairs)
    out += _p_h(hf)
    return out


def _p_a4(pairs) -> dict:
    """IGA / IGB / IZ: K1-off (I-1k) hash = K1-on (I-1) hash on A_P0 + boundary."""
    on = {(v, key): p for (b, v, a, key), p in pairs.items() if b == "I-1" and a == "on"
          and p["set"] in ("A_P0", "A_boundary_P0")}
    off = {(v, key): p for (b, v, a, key), p in pairs.items() if b == "I-1k"}
    shared = [item for item in off if item in on]
    equal = sum(on[item]["variant"]["commands_sha256"] == off[item]["variant"]["commands_sha256"]
                for item in shared)
    shd_off = [p["shd"]["matches_stored"] for p in off.values()]
    return {"id": "P-A4", "prediction": "K1 off = K1 on hashes (IGA, IGB, IZ); SHD K1 off = S-C",
            "observed": {"equal": equal, "pairs": len(shared),
                         "shd_off_match_stored": sum(bool(v) for v in shd_off)},
            "holds": _holds(equal == len(shared) and all(shd_off), len(shared) == 18)}


def _p_b2(pairs) -> dict:
    items = _select(pairs, "I-1", ("IGA", "IGB"), ("B",))
    roll = [p for (b, v, _, key), p in pairs.items() if p in items and "J2" in key
            and "roll+rec" in key]
    diag = [p for (b, v, _, key), p in pairs.items() if p in items and "diag-rec" in key]
    recovered = sum(p["shd"]["M-6"]["P3-1"] is False and p["variant"]["M-6"]["P3-1"] is True
                    for p in roll)
    stops_left = sum(p["variant"]["sgs_stop"] for p in diag)
    return {"id": "P-B2", "prediction": "J2 roll+rec P3-1 recovered >= 2; diag-rec SGS stop >= 1",
            "observed": {"recovered": recovered, "roll_pairs": len(roll),
                         "diag_stops_left": stops_left, "diag_pairs": len(diag)},
            "holds": _holds(recovered >= 2 and stops_left >= 1, bool(roll) and bool(diag))}


def _p_c2(pairs) -> dict:
    items = [(key, p) for (b, v, _, key), p in pairs.items() if b == "I-1" and v == "IGB"
             and p["set"] == "C"]
    median = _median(p["ds_max_mm"] for _, p in items)
    stops = (sum(p["shd"]["sgs_stop"] for _, p in items),
             sum(p["variant"]["sgs_stop"] for _, p in items))
    fdown = sum(p["shd"]["sgs_stop"] and not p["variant"]["sgs_stop"] for key, p in items
                if "J2" in key and "fdown" in key)
    return {"id": "P-C2", "prediction": "C IGB: median ds_max -25 .. -10 mm, SGS stops equal or "
            "fewer, J2 fdown keys losing the SGS stop >= 3",
            "observed": {"median_ds_max_mm": median, "sgs_stops_shd_variant": stops,
                         "j2_fdown_stops_gone": fdown},
            "holds": _holds(_in(median, -25.0, -10.0) and stops[1] <= stops[0] and fdown >= 3,
                            len(items) == 67)}


def _event_total(pair_side: dict, prefix: str) -> int:
    return sum(count for name, count in pair_side["M-11"].items() if name.startswith(prefix))


def _p_s(pairs) -> list[dict]:
    items = [p for (b, v, _, _), p in pairs.items() if b == "I-1" and v == "S4"]
    changed = sum(not p["hash_equal"] for p in items)
    transitions = sum(p["shd"]["M-1"] != p["variant"]["M-1"] for p in items)
    steps = (sum(_event_total(p["shd"], "INFO_PRESSURE_STEP") for p in items),
             sum(_event_total(p["variant"], "INFO_PRESSURE_STEP") for p in items))
    fallback = (sum(_event_total(p["shd"], "WARN_ROD_PRESSURE_FALLBACK") for p in items),
                sum(_event_total(p["variant"], "WARN_ROD_PRESSURE_FALLBACK") for p in items))
    head = sum(_event_total(p["variant"], "FAULT_HEAD_PRESSURE") > 0 for p in items)
    decidable = len(items) == 161
    return [
        {"id": "P-S1", "prediction": "hash changed >= 150/161, verdict transitions <= 3 (the "
         "lower-bound spread part is not decided from the lines)",
         "observed": {"changed": changed, "transitions": transitions},
         "holds": _holds(changed >= 150 and transitions <= 3, decidable)},
        {"id": "P-S2", "prediction": "INFO_PRESSURE_STEP fewer; WARN_ROD_PRESSURE_FALLBACK "
         "equal or more", "observed": {"steps_shd_s4": steps, "fallback_shd_s4": fallback},
         "holds": _holds(steps[1] < steps[0] and fallback[1] >= fallback[0], decidable)},
        {"id": "P-S3", "prediction": "a false FAULT_HEAD_PRESSURE may appear (record)",
         "observed": {"rows_with_head_fault": head}, "holds": None}]


def _hf_rows(hf, arm, jump_bar):
    return [row for row in (hf or {}).get("rows", []) if row["arm"] == arm
            and row["jump_bar"] == jump_bar]


def _p_h(hf: dict | None) -> list[dict]:
    if hf is None:
        return [{"id": name, "prediction": "H-F", "observed": None, "holds": None}
                for name in ("P-H1", "P-H2", "P-H3")]
    j150 = _hf_rows(hf, "S4", 150.0)
    missed_50 = [row for row in j150 if row["phase_ms"] == 50]
    early = [row for row in j150 if row["phase_ms"] <= 20]
    late = [row for row in j150 if row["phase_ms"] == 90]
    h1 = (all(row["missed"] for row in missed_50)
          and all(row["delay_periods"] == 0 for row in early)
          and all(row["delay_periods"] == 1 for row in late))
    j250 = _hf_rows(hf, "S4", 250.0)
    h2 = (all(not row["missed"] for row in j250)
          and all(row["delay_periods"] == 1 for row in j250 if row["phase_ms"] >= 67))
    missed = [row for row in hf.get("rows", []) if row["arm"] == "S4" and row["missed"]]
    return [
        {"id": "P-H1", "prediction": "J 150: missed at 50 ms (6/6), same period <= 20 ms, one "
         "period late at 90 ms", "observed": {
             "missed_at_50": sum(row["missed"] for row in missed_50),
             "rows_at_50": len(missed_50),
             "delays": {row["phase_ms"]: row["delay_periods"] for row in j150}},
         "holds": _holds(h1, len(missed_50) == 6)},
        {"id": "P-H2", "prediction": "J 250: caught at every phase, one period late >= 67 ms",
         "observed": {"missed": sum(row["missed"] for row in j250), "rows": len(j250)},
         "holds": _holds(h2, len(j250) == 36)},
        {"id": "P-H3", "prediction": "missed rows: FAULT later by another check or none (record)",
         "observed": {"missed_rows": len(missed),
                      "fault_entry_later": sum("error" not in (row.get("judge") or {})
                                               for row in missed)},
         "holds": None}]


# ------------------------------------------------------------------------------- CLI
def judge(folder: Path) -> dict:
    lines = read_lines(folder)
    if not lines:
        raise ValueError(f"no ideal run lines in {folder}")
    finished = latest_finished(lines)
    errors = sum("error" in line for line in lines)
    pairs = build_pairs(finished)
    hf = _optional_json(folder / "ideal_HF.json")
    hf_old = _optional_json(folder / "ideal_HF_g4_old.json")
    plan_sha = sorted({tuple(ideal_of(line).get("plan_sha256") or ()) for line in lines})
    return {"plan_sha256": list(PLAN_SHA256_LIST), "lines": len(lines), "error_lines": errors,
            "finished": len(finished), "line_plan_sha256": [list(item) for item in plan_sha],
            "gates": gates(finished, pairs, hf, hf_old), "set_totals": set_totals(pairs),
            "predictions": predictions(pairs, hf),
            "pairs": {"|".join(key): pair for key, pair in sorted(pairs.items())}}


def _optional_json(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", nargs="?", type=Path, default=IDEAL_DIR)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    out = args.out or args.folder / "ideal_stage1_judge.json"
    try:
        if out.exists():
            raise ValueError(f"{out} exists (new files only)")
        result = judge(args.folder)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"input error: {exc!r}")
        print(json.dumps({"stop": "input", "reason": str(exc)}))
        return 2
    out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    holds = [item["holds"] for item in result["predictions"]]
    print(json.dumps({"out": str(out), "lines": result["lines"], "finished": result["finished"],
                      "gates": result["gates"], "predictions_true": holds.count(True),
                      "predictions_false": holds.count(False),
                      "predictions_undecided": holds.count(None)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
