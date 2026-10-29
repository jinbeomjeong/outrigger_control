"""Paper table: item 4 "max moving pressure" [bar] per independent variable (read-only).

No simulation is run. Sources:

* S8 rigid floor (Chrono L2b, 86 cases): the judged rows of ``verify_S8C.json`` (p1r + rest
  batches), case settings from ``07_results/S8/<batch>/<case>/result.json``. The 10 Hz Record is
  re-read to locate the peak leg / time and to check that the stored value is reproduced.
* S9 P3b soft ground (Chrono SCM, 24 cases): no pressure key in ``s9_P3b_summary.json``, so the
  item 4 value is computed from each case Record with the S8 judge definition.
* Supplementary Chrono cases with a Record but no item 4 row: G6 single soft pad (SCM) and the G8
  non-planar start acceptance (L1-R pad block). The reduced-model judgements (rev70 / rev74)
  carry only minimum forces, which is reported as "no pressure key".

Item 4 definition (``outrigger_sim.verify.s6_control._pressure_and_rocking_metrics``, spec
rev. 50 220.6 (2)): p = F_cyl / A_p per leg (net cylinder force over the head area of that leg,
10 Hz Record), maximum over the samples with |u_applied| > 1e-6 m/s. Floor-event cases judge the
extension samples outside the event transient and report the transient peak (head F / A_p, any
state, 1 ms pads).

The stored S8 rows are judge rev. 46 (before spec rev. 50) and were computed with
``u_applied != 0``; the locked valve leaves u_applied decaying to ~1e-37 m/s, so locked samples
entered those values. The paper value ``max_moving_pressure_bar`` uses the current mask; the
stored value is kept next to it and is checked against a legacy-mask recomputation.

Because the extension force limit of a leg is 210 bar x A_p of that leg, p / 210 bar is also the
ratio of the peak force to the leg's extension force limit (front 278.7 kN, rear 199.6 kN).

Usage: python -I paper_max_pressure_table.py [out.json]
"""

import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
S8_VERIFY = {
    "p1r_20261024_222013": ROOT / "06_analysis/01_chrono/18_S8/p1r_20261024_222013/verify_S8C.json",
    "rest_20261024_233615": ROOT
    / "06_analysis/01_chrono/18_S8/rest_20261024_233615/verify_S8C.json",
}
S8_RESULTS = ROOT / "07_results/S8"
S9_SUMMARY = ROOT / "06_analysis/01_chrono/19_S9/s9_P3b_summary.json"
S9_P3B_BATCH = ROOT / "07_results/S9/batch_P3b_20261026_122444"
SUPPLEMENTARY_BATCHES = {
    "G6 single soft pad (Chrono SCM, L2b)": ROOT / "07_results/S9/batch_G6_20261028_075108",
    "G8 non-planar start acceptance (Chrono L1-R pad block)": ROOT
    / "07_results/S6/bundleC_g8c76_p28acc_p28_L1R_20261027_222426",
}
REDUCED_JUDGEMENT_DIRS = [
    ROOT / "06_analysis/02_control/s8/rev70",
    ROOT / "06_analysis/02_control/s8/rev74",
]
DEFAULT_OUT = ROOT / "06_analysis/02_control/s8/paper/max_pressure_by_variable.json"

LEGS = ("FL", "FR", "RL", "RR")
MOVING_EPS_M_S = 1.0e-6  # s6_control.MOVING_EPS_M_S
PA_PER_BAR = 1.0e5
RELIEF_BAR = 210.0
JUDGE_LIMIT_BAR = 180.0  # s6_control.MOVING_PRESSURE_TOL_BAR
EXTENSION_FORCE_LIMIT_KN = {"FL": 278.7, "FR": 278.7, "RL": 199.6, "RR": 199.6}  # 210 bar x A_p
ITEM_MOVING = "4 max moving pressure"
ITEM_OUTSIDE_EVENT = "4 max moving pressure outside the event transient"
ITEM_IN_EVENT = "4 max pressure in the event transient"
REPRODUCE_TOL_BAR = 1e-6
PRESSURE_KEY = re.compile(r"press|_bar|F_max|max_F|peak", re.IGNORECASE)


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _find_head_areas(meta) -> list[float]:
    """Every ``head_area_m2`` list of four in the Record meta; they must agree."""
    found: list[list[float]] = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "head_area_m2" and isinstance(value, list) and len(value) == 4:
                    found.append([float(x) for x in value])
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(meta)
    if not found or any(not np.allclose(areas, found[0], rtol=1e-12) for areas in found):
        raise ValueError(f"no unique head_area_m2 in the Record meta: {found}")
    return found[0]


def _masked_peak(p_bar, mask, t_s, applied) -> dict:
    if not mask.any():
        return {"max_bar": None, "samples": 0}
    masked = np.where(mask, p_bar, -np.inf)
    sample, leg = np.unravel_index(int(np.argmax(masked)), masked.shape)
    return {
        "max_bar": float(p_bar[sample, leg]),
        "leg": LEGS[leg],
        "t_s": float(t_s[sample]),
        "u_applied_m_s": float(applied[sample, leg]),
        "samples": int(mask.sum()),
    }


def record_moving_peak(case_dir: Path, event_window_s=None, t0_s: float = 0.0) -> dict:
    """Item 4 recomputed from a case Record (F_cyl / A_p per leg, 10 Hz).

    ``current`` = spec rev. 50 220.6 (2) mask |u_applied| > 1e-6 m/s. ``legacy`` = the mask the
    stored rev. 46 rows were judged with (u_applied != 0; the locked valve leaves an exponentially
    decaying u_applied of ~1e-37 m/s, so locked samples were counted). With ``event_window_s``
    (relative to ``t0_s``) only the extension samples outside the window count, as in the
    floor-event rows.
    """
    record = np.load(case_dir / "record" / "record.npz", allow_pickle=False)
    areas_m2 = np.asarray(_find_head_areas(_read_json(case_dir / "record" / "meta.json")))
    applied = np.asarray(record["u_applied"], float)
    t_s = np.asarray(record["t"], float)
    p_bar = np.asarray(record["F_cyl"], float) / areas_m2 / PA_PER_BAR
    if event_window_s is None:
        current = np.abs(applied) > MOVING_EPS_M_S
        legacy = applied != 0.0
    else:
        t_rel = t_s - t0_s
        outside = ~((t_rel >= event_window_s[0]) & (t_rel <= event_window_s[1]))[:, None]
        current = outside & (applied > MOVING_EPS_M_S)
        legacy = outside & (applied > 0.0)
    # sensor-model head reading (offset / noise included): p_h >= F / A_p by the rod-side term
    head_bar = np.asarray(record["meas.head_pressure"], float) / PA_PER_BAR
    measured_head_max_bar = float(head_bar[current].max()) if current.any() else None
    return {
        "head_area_m2": areas_m2.tolist(),
        "current": _masked_peak(p_bar, current, t_s, applied),
        "legacy": _masked_peak(p_bar, legacy, t_s, applied),
        "max_any_state_bar": float(p_bar.max()),
        "measured_head_pressure_current_mask_max_bar": measured_head_max_bar,
    }


def _ratios(value_bar: float | None, leg: str | None) -> dict:
    if value_bar is None:
        return {}
    ratios = {
        "ratio_to_relief_210": value_bar / RELIEF_BAR,
        "ratio_to_judge_180": value_bar / JUDGE_LIMIT_BAR,
    }
    if leg is not None:
        # p / 210 bar = F / (210 bar A_p) of the same leg
        ratios["peak_force_kN"] = value_bar / RELIEF_BAR * EXTENSION_FORCE_LIMIT_KN[leg]
        ratios["ratio_to_leg_extension_force_limit"] = value_bar / RELIEF_BAR
    return ratios


def _fs_from_name(case: str) -> float | None:
    match = re.search(r"Fs(\d+)", case)
    return None if match is None else float(match.group(1))


def _s8_case_rows(batch: str, verify_path: Path) -> list[dict]:
    verify = _read_json(verify_path)
    metrics = {m["case"]: m for m in verify["metrics"]}
    s8_meta = verify["s8_metrics"]
    by_case: dict[str, dict] = {}
    for row in verify["rows"]:
        if row["item"] not in (ITEM_MOVING, ITEM_OUTSIDE_EVENT, ITEM_IN_EVENT):
            continue
        entry = by_case.setdefault(row["case"], {"items": {}})
        entry["items"][row["item"]] = {
            "value": row["value"],
            "limit": row["limit"],
            "passed": row["passed"],
        }
    cases = []
    for case, entry in by_case.items():
        cases.append(
            _s8_case(batch, verify_path, case, entry["items"], metrics[case], s8_meta[case]["s8"])
        )
    return cases


def _s8_case(batch, verify_path, case, items, metric, s8) -> dict:
    case_dir = S8_RESULTS / batch / case
    settings = _read_json(case_dir / "result.json")["settings"]
    judged_item = ITEM_MOVING if ITEM_MOVING in items else ITEM_OUTSIDE_EVENT
    stored = items[judged_item]["value"]
    window_s = metric.get("event_pressure_window_s") if judged_item == ITEM_OUTSIDE_EVENT else None
    recomputed = record_moving_peak(case_dir, window_s, metric["times_s"]["t0"])
    current = recomputed["current"]
    legacy_error_bar = abs(recomputed["legacy"]["max_bar"] - stored)
    in_event = items.get(ITEM_IN_EVENT)
    record_path = (case_dir / "record" / "record.npz").relative_to(ROOT).as_posix()
    verify_rel = verify_path.relative_to(ROOT).as_posix()
    return {
        "case": case,
        "batch": batch,
        "source": f"{record_path} (current mask); stored: {verify_rel} rows['{judged_item}']",
        "max_moving_pressure_bar": current["max_bar"],
        "peak_leg": current.get("leg"),
        "stored_rev46_bar": stored,
        "stored_reproduced_by_legacy_mask": legacy_error_bar <= REPRODUCE_TOL_BAR,
        "stored_minus_current_bar": stored - current["max_bar"],
        "judged_item": judged_item,
        "judge_limit_bar": items[judged_item]["limit"],
        "stored_passed": items[judged_item]["passed"],
        "event_transient_peak_bar": None if in_event is None else in_event["value"],
        "event_transient_limit_bar": None if in_event is None else in_event["limit"],
        "max_pressure_any_step_bar": metric.get("max_pressure_any_step_bar"),
        "floor": settings["floor"],
        "level": settings["level"],
        "contact": settings["contact"],
        "group": settings["group"],
        "pressure_grade": settings.get("pressure_grade"),
        "event": settings.get("event"),
        "engine": s8.get("engine"),
        "condition": s8.get("condition"),
        "fs_kN": _fs_from_name(case),
        "fs_kN_verify": s8.get("fs_kN"),
        "settings_match_verify": settings["floor"] == metric["floor"]
        and settings["level"] == metric["level"],
        "event_window_s": window_s,
        "record_recomputed": recomputed,
    } | _ratios(current["max_bar"], current.get("leg"))


def _max_by(
    cases: list[dict],
    key: str,
    value_key: str = "max_moving_pressure_bar",
    leg_key: str | None = "peak_leg",
) -> dict:
    """Largest value per level of ``key`` with the case that produced it."""
    table: dict[str, dict] = {}
    for case in cases:
        level = str(case[key])
        value = case[value_key]
        if value is None:
            continue
        best = table.get(level)
        if best is None or value > best["max_bar"]:
            leg = None if leg_key is None else case.get(leg_key)
            table[level] = {
                "max_bar": value,
                "case": case["case"],
                "peak_leg": leg,
                "source": case["source"],
            }
    for level, best in table.items():
        best["n_cases"] = sum(1 for c in cases if str(c[key]) == level and c[value_key] is not None)
        best |= _ratios(best["max_bar"], best["peak_leg"])
    return dict(sorted(table.items()))


def _auger_pairs(cases: list[dict]) -> list[dict]:
    """Cases that differ only in the auger level (same floor, F_s, contact, sensors, engine)."""
    groups: dict[tuple, dict[str, dict]] = {}
    for case in cases:
        key = (
            case["floor"],
            case["fs_kN"],
            case["contact"],
            case["pressure_grade"],
            case["engine"],
            case["condition"],
            case["event"],
        )
        groups.setdefault(key, {}).setdefault(case["level"], case)
    pairs = []
    for key, by_level in groups.items():
        if len(by_level) < 2:
            continue
        pairs.append(
            {
                "floor": key[0],
                "fs_kN": key[1],
                "contact": key[2],
                "pressure_grade": key[3],
                "levels": {
                    level: {
                        "max_bar": c["max_moving_pressure_bar"],
                        "stored_rev46_bar": c["stored_rev46_bar"],
                        "case": c["case"],
                    }
                    for level, c in sorted(by_level.items())
                },
            }
        )
    return pairs


def s8_section() -> dict:
    cases: list[dict] = []
    for batch, path in S8_VERIFY.items():
        cases.extend(_s8_case_rows(batch, path))
    main = [c for c in cases if c["event"] is None and c["engine"] == "L2b_NSC"]
    events = [c for c in cases if c["event"] is not None]
    return {
        "n_cases": len(cases),
        "n_by_engine": {
            e: sum(c["engine"] == e for c in cases) for e in sorted({c["engine"] for c in cases})
        },
        "n_event_cases": len(events),
        "n_no_event_L2b": len(main),
        "n_stored_reproduced_by_legacy_mask": sum(
            c["stored_reproduced_by_legacy_mask"] for c in cases
        ),
        "n_stored_differs_from_current": sum(
            c["stored_minus_current_bar"] > REPRODUCE_TOL_BAR for c in cases
        ),
        "overall_max": _overall(cases),
        "overall_max_no_event_L2b": _overall(main),
        "no_event_L2b": _variable_tables(
            main, ("floor", "level", "fs_kN", "pressure_grade", "contact")
        )
        | {
            "scope": "event None, engine L2b_NSC (judged + beta sensitivity); floor-slope cases",
            "auger_matched": _auger_pairs(main),
        },
        "all_cases": _variable_tables(cases, ("floor", "level", "fs_kN", "event", "engine"))
        | {
            "event_transient_peak_by_event": _max_by(
                events, "event", "event_transient_peak_bar", None
            )
        },
        "cases": sorted(cases, key=lambda c: (c["case"], c["batch"])),
    }


def _overall(cases: list[dict]) -> dict:
    current = max(cases, key=lambda c: c["max_moving_pressure_bar"])
    stored = max(cases, key=lambda c: c["stored_rev46_bar"])
    return {
        "current": {
            "max_bar": current["max_moving_pressure_bar"],
            "case": current["case"],
            "peak_leg": current["peak_leg"],
        },
        "stored_rev46": {"max_bar": stored["stored_rev46_bar"], "case": stored["case"]},
    }


def _variable_tables(cases: list[dict], keys: tuple[str, ...]) -> dict:
    return {
        f"by_{key}": {
            "current": _max_by(cases, key),
            "stored_rev46": _max_by(cases, key, "stored_rev46_bar", None),
        }
        for key in keys
    }


def _s9_case(case: str, row: dict) -> dict:
    peak = record_moving_peak(S9_P3B_BATCH / case)
    current = peak["current"]
    return {
        "case": case,
        "source": f"{(S9_P3B_BATCH / case).relative_to(ROOT).as_posix()}/record/record.npz "
        "(F_cyl / A_p, |u_applied| > 1e-6 m/s)",
        "max_moving_pressure_bar": current["max_bar"],
        "peak_leg": current.get("leg"),
        "legacy_mask_bar": peak["legacy"]["max_bar"],
        "soil": row["soil"],
        "pad_variant": row["pad_variant"],
        "level": row["level"],
        "fs_kN": row["fs_kN"],
        "record_recomputed": peak,
    } | _ratios(current["max_bar"], current.get("leg"))


def s9_section() -> dict:
    summary = _read_json(S9_SUMMARY)
    summary_pressure_keys = sorted(_keys_matching(summary["rows"], PRESSURE_KEY))
    cases = [_s9_case(case, row) for case, row in summary["rows"].items()]
    for case in cases:
        case["soil_pad"] = f"{case['soil']}/{case['pad_variant']}"
    overall = max(cases, key=lambda c: c["max_moving_pressure_bar"])
    return {
        "n_cases": len(cases),
        "summary_pressure_keys": summary_pressure_keys,
        "definition_note": "same formula as the S8 item 4 (no event window in P3b); "
        "computed here, not a stored judge value",
        "overall_max": {
            "max_bar": overall["max_moving_pressure_bar"],
            "case": overall["case"],
            "peak_leg": overall["peak_leg"],
        },
        "by_soil": _max_by(cases, "soil"),
        "by_pad_variant": _max_by(cases, "pad_variant"),
        "by_soil_pad": _max_by(cases, "soil_pad"),
        "by_level": _max_by(cases, "level"),
        "by_fs_kN": _max_by(cases, "fs_kN"),
        "cases": cases,
    }


def _keys_matching(node, pattern: re.Pattern) -> set[str]:
    keys: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if pattern.search(key):
                keys.add(key)
            keys |= _keys_matching(value, pattern)
    elif isinstance(node, list):
        for value in node:
            keys |= _keys_matching(value, pattern)
    return keys


def supplementary_section() -> dict:
    out = {}
    for label, batch_dir in SUPPLEMENTARY_BATCHES.items():
        cases = []
        for case_dir in sorted(
            p for p in batch_dir.iterdir() if (p / "record" / "record.npz").is_file()
        ):
            peak = record_moving_peak(case_dir)
            current = peak["current"]
            cases.append(
                {
                    "case": case_dir.name,
                    "max_moving_pressure_bar": current["max_bar"],
                    "peak_leg": current.get("leg"),
                    "legacy_mask_bar": peak["legacy"]["max_bar"],
                    "record_recomputed": peak,
                }
                | _ratios(current["max_bar"], current.get("leg"))
            )
        out[label] = {"batch": batch_dir.relative_to(ROOT).as_posix(), "cases": cases}
    return out


def reduced_section() -> dict:
    found = {}
    for folder in REDUCED_JUDGEMENT_DIRS:
        for path in sorted(folder.glob("*.json")):
            keys = sorted(_keys_matching(_read_json(path), PRESSURE_KEY))
            found[path.relative_to(ROOT).as_posix()] = keys
    return {
        "pattern": PRESSURE_KEY.pattern,
        "pressure_or_peak_keys": found,
        "files_with_keys": [p for p, keys in found.items() if keys],
    }


def main() -> None:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    result = {
        "generator": Path(__file__).relative_to(ROOT).as_posix(),
        "definition": "item 4 = max over |u_applied| > 1e-6 m/s (spec rev. 50 220.6 (2)) of "
        "F_cyl / A_p per leg (10 Hz Record); floor-event cases: extension samples outside the "
        "event transient + transient head F / A_p peak (any state, 1 ms pads, stored value). "
        "stored_rev46_bar = verify_S8C row value (mask u_applied != 0)",
        "references_bar": {"relief": RELIEF_BAR, "judge_limit": JUDGE_LIMIT_BAR},
        "extension_force_limit_kN": EXTENSION_FORCE_LIMIT_KN,
        "S8_rigid": s8_section(),
        "S9_P3b_soft": s9_section(),
        "supplementary_chrono": supplementary_section(),
        "reduced_model_judgements": reduced_section(),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=1), encoding="utf-8")
    s8 = result["S8_rigid"]
    s9 = result["S9_P3b_soft"]
    print(
        f"S8 {s8['n_cases']} cases, legacy mask reproduces the stored value "
        f"{s8['n_stored_reproduced_by_legacy_mask']}, stored > current "
        f"{s8['n_stored_differs_from_current']}"
    )
    print(f"  max {s8['overall_max']}\n  no-event L2b max {s8['overall_max_no_event_L2b']}")
    print(f"S9 P3b {s9['n_cases']} cases, max {s9['overall_max']}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
