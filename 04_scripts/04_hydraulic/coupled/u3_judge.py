"""Judgement of the paper v5 U-3 / U-6 reruns (``u3_u6_rerun_rules.md`` 4, 5 and 7, sealed).

Grades per key (rules 4, the judge functions of v4):
  slope, h6, x426b  fix-candidates record, settle check v2 (``s9_settle_rejudge.rejudge_record``
                    with the baseline the v4 re-judgement used), then the verdict class
  h9                fix-candidates record verdict (v4 kept it without the settle re-judgement)
  D                 ``s9_soil_slope`` result verdict (P3 rows with the spec 421.1 READY limit)
  g6, C             r72 gates with the G6-7 demotion (``b5_official.demote_preloc_gate``,
                    spec 377 / U-S9-G6c); a soil-guard stop is the safe stop
  g8                fix-candidates g8 record (P-S8-28 family gates of ``r70_p28_screen``)
  p3b               fix-candidates p3b record (``p3_lite_gates``, as v4; rules rev1 1 #3)
Rules rev1 (``u3_u6_rerun_rules_rev1.md``, its SHA-256 read from the file into the report):
G-4 asks a rod reading and J-P3 ``pass`` of the g8 VB runs (``ROD_READING_SUITES``) and
``no_rod_reading`` of the others; G-6 stops on a ``WARN_ROD_PRESSURE_FALLBACK`` event in a g8
VB run; the previous-edition g6 grade is the stored verdict (``previous_g6_demotion``).
Grade classes: ``pass``, ``flag`` (passed with a FLAG), ``safe_stop``
(``stroke_limited_stop``) and ``fail``.

Report (rules 5.1): per bundle the VB counts and phrase, the V0 -> VB 4 x 4 table, the five
VB - V0 differences (first READY s, min F after lift-off kN, max stroke mm, READY rut mm, end
attitude deg; ``NA`` when one side lacks the value), the classes of rules 5.1 and the previous
edition (V0 - v4 ``final_SGS_R4``, record only). U-6 (5.2): per controller lite pass, C2 safe
stops, crawler-load failures and the official verdicts, with the v4 values of the same keys.
Gates G-1 .. G-6 (rules 7, rev1) first; any failed gate stops the judgement (no phrases).

Exit code: 0 judged, 1 a gate stopped it, 2 an input missing.

Usage (python-dev or dynamics-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/u3_judge.py judge <out_json>
      [--u3-dir 06_analysis/02_control/v5_rerun] [--v4-dir 06_analysis/02_control/s9]
      [--g3 <g3_json>] [--bundles slope,h6,...]
  python -I -B 04_scripts/04_hydraulic/coupled/u3_judge.py g3 <out_json> <before> <after> ...
      (G-3: pairs of output files of the same keys without options; equal command hashes)
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
S9_DIR = ROOT / "04_scripts" / "03_control" / "s9"
for _path in (HERE, S9_DIR, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.append(str(_path))

import v5_rerun  # noqa: E402

GRADES = ("pass", "flag", "safe_stop", "fail")
SAFE_STOP_VERDICT = "stroke_limited_stop"
PASSED_VERDICTS = ("pass", "stroke_limited_pass")
QUANTITIES = ("t_ready_s", "min_force_kN", "max_stroke_mm", "rut_ready_mm", "att_end_deg")
EXTEND_START_RULE = "tracked_bound"
EXTEND_START_REVISION = 4
J_P3_HEAD_ONLY = "no_rod_reading"
DEFAULT_U3_DIR = v5_rerun.OUT_DIR
DEFAULT_V4_DIR = ROOT / "06_analysis" / "02_control" / "s9"
U6_CONTROLLERS = ("C2", "ABL", "IND")
U6_TAGS = {"C2": v5_rerun.TAG_VB, "ABL": v5_rerun.TAG_ABL, "IND": v5_rerun.TAG_IND}
RULES_REVISIONS = (v5_rerun.RULES_PATH.with_name("u3_u6_rerun_rules_rev1.md"),)
"""Sealed addenda (rev1 2026-11-08: g8 reads rod pressures, P3b = p3_lite_gates, G-6, the
previous-edition g6 without the G6-7 demotion)."""


def revision_record(path: Path) -> dict:
    """Name, SHA-256 read from the file, the sealed SHA-256 (``<stem>.sha256``) and their match."""
    seal = path.with_suffix(".sha256")
    sealed = seal.read_text(encoding="utf-8").split()[0] if seal.is_file() else None
    sha = v5_rerun.text_sha256(path)
    return {"rules": path.name, "sha256": sha, "sealed_sha256": sealed,
            "match_seal": sha is not None and sha == sealed}


@dataclasses.dataclass(frozen=True)
class Bundle:
    """One U-3 bundle of rules 2: v4 file (under ``--v4-dir``), suite, grade kind, key count."""

    name: str
    v4_file: str
    kind: str
    expected: int
    suite: str | None = None
    settle_v2: bool = False


BUNDLES = (
    Bundle("slope", "rev85/finB2_harness_rejudged.json", "record", 110, "slope", True),
    Bundle("h6", "rev85/finB2_harness_rejudged.json", "record", 26, "h6", True),
    Bundle("h9", "rev85/finB2_h9.json", "record", 24, "h9"),
    Bundle("g6", "rev85/finB2_p0.json", "g6", 116, "g6"),
    Bundle("g8", "rev85/finB2_p0.json", "g8", 516, "g8"),
    Bundle("p3b", "rev85/finB2_p0.json", "record", 171, "p3b"),
    Bundle("x426b", "rev85/finB2_x426b_rejudged.json", "record", 84, "x426b", True),
    Bundle("C", "rev85/fin_x426_C.json", "r72", 34),
    Bundle("D", "rev85/fin_x426_D.json", "slope_result", 33),
)
U6_BUNDLES = (("b5_wide", "rev84/fin2_b5_wide_official.json", 226, "B"),
              ("b5_main", "rev84/fin_b5_main.json", 16, None))
"""(name, v4 file, cases, pad filter): 226 x 3 = 678 and 16 x 3 = 48 runs (rules 3)."""


# -------------------------------------------------------------------------------- reading
def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def entries_of(payload: dict, suite: str | None = None) -> list[dict]:
    items = payload.get("records") or payload.get("results") or []
    return [e for e in items if suite is None or e.get("suite") in (None, suite)]


def _max_abs(values) -> float | None:
    if values is None:
        return None
    if isinstance(values, (int, float)):
        return abs(float(values))
    finite = [abs(float(v)) for v in values if v is not None and math.isfinite(float(v))]
    return max(finite) if finite else None


def quantities(entry: dict, kind: str) -> dict:
    """The five rules 5.1 quantities of one record (None when absent)."""
    if kind == "slope_result":
        run = entry.get("run") or {}
        return {"t_ready_s": run.get("t_ready_s"),
                "min_force_kN": run.get("min_true_Fcyl_after_off_kN"),
                "max_stroke_mm": run.get("max_motor_stroke_mm"),
                "rut_ready_mm": entry.get("rut_ready_mm", run.get("clear_true_ready_mm")),
                "att_end_deg": _max_abs(run.get("att_end_deg"))}
    if kind == "r72":
        return {"t_ready_s": entry.get("t_ready_s"),
                "min_force_kN": entry.get("min_true_Fcyl_after_off_kN"),
                "max_stroke_mm": entry.get("max_motor_stroke_mm"),
                "rut_ready_mm": entry.get("rut_clear_ready_mm"),
                "att_end_deg": _max_abs(entry.get("att_end_deg"))}
    att = entry.get("att_end_deg")
    return {"t_ready_s": entry.get("t_ready_s"), "min_force_kN": entry.get("min_force_kN"),
            "max_stroke_mm": entry.get("max_stroke_mm"), "rut_ready_mm": entry.get("rut_ready_mm"),
            "att_end_deg": _max_abs(att if att is not None
                                    else entry.get("att_end_absmax_deg"))}


# --------------------------------------------------------------------------------- grading
def _verdict_grade(verdict: str | None, has_flag: bool) -> str:
    if verdict == SAFE_STOP_VERDICT:
        return "safe_stop"
    if verdict in PASSED_VERDICTS:
        return "flag" if has_flag else "pass"
    return "fail"


def _g6_grade(gate_record: dict, verdict: str | None, flags: list[str]) -> tuple[str, list]:
    """r72 gates with the G6-7 demotion; a soil-guard stop record is the safe stop."""
    import b5_official

    if verdict == SAFE_STOP_VERDICT:
        return "safe_stop", flags
    gates, demotion = b5_official.demote_preloc_gate(gate_record)
    all_flags = list(flags) + demotion
    if not all(gates.values()):
        return "fail", all_flags
    return ("flag" if all_flags else "pass"), all_flags


def _rows_flags(rows: dict) -> list[str]:
    """FLAGs of a ``s9_soil_slope`` result as the slope-suite record has them (P3-1, P3-2)."""
    flags = list((rows.get("P3-1") or {}).get("flag_names") or [])
    p32 = rows.get("P3-2") or {}
    if p32.get("flag"):
        flags += list(p32.get("flag_names") or [p32.get("flag_name")])
    return flags


def grade(entry: dict, bundle: Bundle, baseline: dict | None) -> dict:
    """Grade, the verdict it came from and the FLAGs of one record (rules 4)."""
    if "error" in entry:
        return {"grade": "fail", "verdict": "error", "flags": []}
    kind = bundle.kind
    if kind == "slope_result":
        flags = _rows_flags(entry.get("rows") or {})
        return {"grade": _verdict_grade(entry.get("verdict"), bool(flags)),
                "verdict": entry.get("verdict"), "flags": flags}
    if kind == "r72":
        result, flags = _g6_grade(entry, entry.get("verdict"), list(entry.get("flags") or []))
        return {"grade": result, "verdict": entry.get("verdict") or entry.get("pass"),
                "flags": flags}
    if kind == "g6":
        gate_record = ((entry.get("v5") or {}).get("r72")
                       or {"gates": {name: False for name in entry.get("failed_rows") or []}})
        flags = list(entry.get("flags") or [])
        result, flags = _g6_grade({**gate_record, "final_phase": entry.get("final_phase")},
                                  entry.get("verdict"), flags)
        return {"grade": result, "verdict": entry.get("verdict"), "flags": flags,
                "gates_source": "v5.r72" if (entry.get("v5") or {}).get("r72") else
                "failed_rows (no r72 gates: G6-7 demotion not applied)"}
    if kind == "g8":
        flagged = bool(entry.get("failed_rows")) and bool(entry.get("passed"))
        return {"grade": "fail" if not entry.get("passed") else ("flag" if flagged else "pass"),
                "verdict": entry.get("verdict"), "flags": entry.get("failed_rows") if flagged
                else []}
    record = entry
    if bundle.settle_v2 and baseline is not None:
        import s9_settle_rejudge

        record = s9_settle_rejudge.rejudge_record(entry, baseline)
    flags = list(record.get("flags") or [])
    return {"grade": _verdict_grade(record.get("verdict"), bool(flags)),
            "verdict": record.get("verdict"), "flags": flags,
            "settle_v2_source": record.get("settle_v2_source")}


# ------------------------------------------------------------------------------ comparison
def transition_table(pairs: list[tuple[str, str]]) -> dict:
    """4 x 4 counts ``{from: {to: n}}``."""
    table = {a: dict.fromkeys(GRADES, 0) for a in GRADES}
    for before, after in pairs:
        table[before][after] += 1
    return table


def differences(before: dict[str, dict], after: dict[str, dict]) -> dict:
    """``after - before`` per quantity over the common keys (NA = one side without it)."""
    out = {}
    for name in QUANTITIES:
        values, na = [], 0
        for key in after:
            a, b = after[key].get(name), (before.get(key) or {}).get(name)
            if a is None or b is None:
                na += 1
                continue
            values.append(float(a) - float(b))
        out[name] = {"n": len(values), "NA": na,
                     "mean": sum(values) / len(values) if values else None,
                     "min": min(values, default=None), "max": max(values, default=None)}
    return out


def classify_pairs(v0: dict[str, dict], vb: dict[str, dict]) -> dict:
    """Rules 5.1 classes: VB-only failure, baseline failure, VB improvement, safe-stop move."""
    classes = {"vb_only_failure": [], "baseline_failure": [], "vb_improvement": [],
               "safe_stop_move": []}
    for key, after in vb.items():
        before = v0.get(key)
        if before is None:
            continue
        a, b = after["grade"], before["grade"]
        if a == "fail" and b != "fail":
            classes["vb_only_failure"].append({"key": key, "v0": b, "vb_verdict": after["verdict"],
                                               "vb_flags": after["flags"]})
        elif a == "fail" and b == "fail":
            classes["baseline_failure"].append(key)
        elif b == "fail":
            classes["vb_improvement"].append({"key": key, "vb": a})
        if {a, b} == {"pass", "safe_stop"}:
            classes["safe_stop_move"].append({"key": key, "v0": b, "vb": a})
    return classes


def phrase(counts: dict[str, int], vb_only: int) -> str | None:
    """Rules 5.1 bundle phrase (None while a VB-only failure waits for the user)."""
    if vb_only:
        return None
    return (f"VB 통과 {counts['pass']} / FLAG {counts['flag']} / 안전 종료 "
            f"{counts['safe_stop']} / 실패 {counts['fail']}(그중 VB 고유 0)")


# ------------------------------------------------------------------------------------ gates
def run_v5_problems(entry: dict, setting: str, expected_tag: str, *, needs_bound: bool) -> list:
    """Rules 7 G-2 fields of one record's ``v5`` block (empty = complete)."""
    v5 = entry.get("v5") or {}
    problems = []
    if v5.get("v5_setting") != setting:
        problems.append(f"v5_setting {v5.get('v5_setting')!r}")
    if v5.get("controller_tag") != expected_tag:
        problems.append(f"controller_tag {v5.get('controller_tag')!r} != {expected_tag!r}")
    extend = v5.get("extend_start") or {}
    is_bound = (extend.get("rule") == EXTEND_START_RULE
                and extend.get("revision") == EXTEND_START_REVISION)
    if needs_bound and not is_bound:
        problems.append(f"③ {extend}")
    if not needs_bound and extend.get("rule") == EXTEND_START_RULE:
        problems.append("③ on where it must be off")
    for name in ("definition_sha256", "head_only_declared", "has_rod_reading"):
        if v5.get(name) is None:
            problems.append(f"{name} missing")
    return problems


def rod_reading_suites() -> tuple[str, ...]:
    """``s9_slope_fix_candidates.ROD_READING_SUITES`` (g8): the bundles with rod readings."""
    import s9_slope_fix_candidates

    return tuple(s9_slope_fix_candidates.ROD_READING_SUITES)


def _j_p3_stop(entry: dict, reason: str) -> dict:
    v5 = entry.get("v5") or {}
    return {"key": v5_rerun.entry_key(entry), "suite": entry.get("suite"),
            "j_p3": v5.get("j_p3"), "has_rod_reading": v5.get("has_rod_reading"),
            "head_only_declared": v5.get("head_only_declared"), "reason": reason}


def _rod_suite_stops(entries: list[dict]) -> list[dict]:
    """Rules rev1 4: a g8 VB run has a rod reading and J-P3 ``pass``; the runs together pass
    ``extend_start_bound.j_p3_judgement`` with their rod-reading flags."""
    from outrigger_sim.control.extend_start_bound import j_p3_judgement

    stops = [_j_p3_stop(e, "rod-reading suite without a rod reading or J-P3 not pass")
             for e in entries
             if not e["v5"].get("has_rod_reading") or e["v5"].get("j_p3") != "pass"]
    if entries:
        judged = j_p3_judgement([e["v5"].get("extend_bound_check") for e in entries],
                                [bool(e["v5"].get("has_rod_reading")) for e in entries],
                                [bool(e["v5"].get("head_only_declared")) for e in entries])
        if judged["status"] != "pass" and not stops:
            stops.append({"suite": entries[0].get("suite"), "j_p3": judged["status"],
                          "reason": "j_p3_judgement over the rod-reading runs",
                          "runs_by_case": judged["runs_by_case"]})
    return stops


def gate_j_p3(entries: list[dict]) -> list[dict]:
    """Rules 7 G-4 with rev1 4: VB C2 runs of a head-only suite are ``no_rod_reading``
    (declared, no rod reading); those of a rod-reading suite (g8) have a rod reading and pass
    J-P3. Anything else (setting defect, H-7, the wrong reading kind) stops."""
    rod_suites = rod_reading_suites()
    vb_runs = [e for e in entries
               if (e.get("v5") or {}).get("controller_tag") == v5_rerun.TAG_VB]
    rod_runs = [e for e in vb_runs if e.get("suite") in rod_suites]
    stops = _rod_suite_stops(rod_runs)
    for entry in vb_runs:
        if entry.get("suite") in rod_suites:
            continue
        v5 = entry["v5"]
        if (v5.get("j_p3") != J_P3_HEAD_ONLY or v5.get("has_rod_reading")
                or not v5.get("head_only_declared")):
            stops.append(_j_p3_stop(entry, "head-only suite with a rod reading or J-P3 not "
                                           "no_rod_reading"))
    return stops


def gate_fallback(entries: list[dict]) -> list[dict]:
    """Rules rev1 G-6: no ``WARN_ROD_PRESSURE_FALLBACK`` event in a g8 VB run (else the ③
    bound reached the command on that key: stop and ask)."""
    rod_suites = rod_reading_suites()
    stops = []
    for entry in entries:
        v5 = entry.get("v5") or {}
        if v5.get("controller_tag") != v5_rerun.TAG_VB or entry.get("suite") not in rod_suites:
            continue
        count = v5.get("rod_pressure_fallback_events")
        if count is None:  # a record before the count: the warnings name set
            count = sum(1 for name in entry.get("warnings") or []
                        if name.startswith(v5_rerun.FALLBACK_EVENT_PREFIX))
        if count >= 1:
            stops.append({"key": v5_rerun.entry_key(entry), "suite": entry.get("suite"),
                          "fallback_events": count})
    return stops


def _file_commit(payload: dict) -> str | None:
    return (((payload.get("meta") or {}).get("v5") or {}).get("code") or {}).get("commit")


# ---------------------------------------------------------------------------------- bundles
def _settle_baseline(v4_payload: dict) -> dict | None:
    """The settle v2 baseline the v4 re-judgement used (its meta), else the default one."""
    import s9_settle_rejudge

    stored = ((v4_payload.get("meta") or {}).get("settle_rejudge") or {}).get("baseline")
    path = Path(stored) if stored and Path(stored).is_file() else s9_settle_rejudge.DEFAULT_BASELINE
    return s9_settle_rejudge.load_baseline(path)


def judge_bundle(bundle: Bundle, u3_dir: Path, v4_dir: Path) -> dict:
    """Grades, tables and gate inputs of one U-3 bundle."""
    v4_payload = read_json(v4_dir / bundle.v4_file)
    v4_keys = v5_rerun.ids_from(v4_dir / bundle.v4_file, "B",
                                suites=None if bundle.suite is None else (bundle.suite,))
    baseline = _settle_baseline(v4_payload) if bundle.settle_v2 else None
    graded, values, gate2, commits, errors, keysets = {}, {}, [], {}, {}, {}
    j_p3_stops, fallback_stops, reused = [], [], 0
    for setting in v5_rerun.SETTINGS:
        payload = read_json(u3_dir / f"u3_{bundle.name}_{setting}.json")
        commits[setting] = _file_commit(payload)
        items = entries_of(payload, bundle.suite)
        keysets[setting] = [v5_rerun.entry_key(e) for e in items]
        errors[setting] = [k for k, e in zip(keysets[setting], items, strict=True) if "error" in e]
        tag = v5_rerun.TAG_VB if setting == "VB" else v5_rerun.TAG_V0
        graded[setting] = {k: grade(e, bundle, baseline)
                           for k, e in zip(keysets[setting], items, strict=True)}
        values[setting] = {k: quantities(e, bundle.kind)
                           for k, e in zip(keysets[setting], items, strict=True)}
        gate2 += [{"setting": setting, "key": k, "problems": p}
                  for k, e in zip(keysets[setting], items, strict=True)
                  if (p := run_v5_problems(e, setting, tag, needs_bound=setting == "VB"))]
        if setting == "VB":
            j_p3_stops = gate_j_p3(items)
            fallback_stops = gate_fallback(items)
            reused = sum(1 for e in items if e.get("reuse") == "d1")
    v4_items = {v5_rerun.entry_key(e): e for e in entries_of(v4_payload, bundle.suite)}
    v4_graded = {k: previous_grade(v4_items[k], bundle, baseline) for k in v4_keys}
    v4_values = {k: quantities(v4_items[k], bundle.kind) for k in v4_keys}
    return _bundle_report(bundle, graded, values, v4_graded, v4_values, {
        "keys": keysets, "v4_keys": v4_keys, "errors": errors, "gate2": gate2,
        "commits": commits, "j_p3_stops": j_p3_stops, "fallback_stops": fallback_stops,
        "reused": reused})


PREVIOUS_G6_DEMOTION = "not_applied"
"""Rules rev1 1 #6: the v4 g6 records keep no r72 gates, so the previous-edition g6 grade is
the stored verdict without the G6-7 demotion (record only)."""


def previous_grade(entry: dict, bundle: Bundle, baseline: dict | None) -> dict:
    """Grade of a v4 stored record: the stored verdict for g6 (rules rev1), else :func:`grade`."""
    if bundle.kind != "g6":
        return grade(entry, bundle, baseline)
    flags = list(entry.get("flags") or [])
    return {"grade": _verdict_grade(entry.get("verdict"), bool(flags)),
            "verdict": entry.get("verdict"), "flags": flags,
            "previous_g6_demotion": PREVIOUS_G6_DEMOTION}


def _bundle_report(bundle: Bundle, graded, values, v4_graded, v4_values, inputs) -> dict:
    v0, vb = graded["V0"], graded["VB"]
    counts = {g: sum(1 for r in vb.values() if r["grade"] == g) for g in GRADES}
    classes = classify_pairs(v0, vb)
    keys, v4_keys = inputs["keys"], inputs["v4_keys"]
    g1 = {"pass": (not inputs["errors"]["V0"] and not inputs["errors"]["VB"]
                   and all(len(keys[s]) == bundle.expected for s in keys)
                   and all(set(keys[s]) == set(v4_keys) for s in keys)
                   and len(v4_keys) == bundle.expected),
          "expected": bundle.expected, "counts": {s: len(k) for s, k in keys.items()},
          "v4_keys": len(v4_keys), "errors": inputs["errors"],
          "not_in_v4": {s: sorted(set(k) - set(v4_keys))[:10] for s, k in keys.items()}}
    g2 = {"pass": not inputs["gate2"] and all(inputs["commits"].values()),
          "problems": inputs["gate2"][:20], "n_problems": len(inputs["gate2"]),
          "code_commit": inputs["commits"]}
    return {"bundle": bundle.name, "kind": bundle.kind, "v4_file": bundle.v4_file,
            "settle_v2": bundle.settle_v2, "runs": {s: len(k) for s, k in keys.items()},
            "reused_d1": inputs["reused"], "vb_counts": counts,
            "phrase": phrase(counts, len(classes["vb_only_failure"])),
            "transition_V0_VB": transition_table([(v0[k]["grade"], vb[k]["grade"])
                                                   for k in vb if k in v0]),
            "differences_VB_minus_V0": differences(values["V0"], values["VB"]),
            "classes": classes,
            "previous_edition": {
                "note": "V0 - v4 (final_SGS_R4): record only (rules 5.1)",
                **({"previous_g6_demotion": PREVIOUS_G6_DEMOTION} if bundle.kind == "g6"
                   else {}),
                "transition_v4_V0": transition_table([(v4_graded[k]["grade"], v0[k]["grade"])
                                                       for k in v0 if k in v4_graded]),
                "differences_V0_minus_v4": differences(v4_values, values["V0"])},
            "gates": {"G-1": g1, "G-2": g2,
                      "G-4": {"pass": not inputs["j_p3_stops"],
                              "stops": inputs["j_p3_stops"][:20]},
                      "G-5": {"pass": not classes["vb_only_failure"],
                              "vb_only_failures": classes["vb_only_failure"]},
                      "G-6": {"pass": not inputs["fallback_stops"],
                              "stops": inputs["fallback_stops"][:20]}},
            "grades": {s: {k: r["grade"] for k, r in graded[s].items()} for s in graded}}


# ----------------------------------------------------------------------------------- U-6
def _u6_counts(items: list[dict]) -> dict:
    out = {}
    for name in U6_CONTROLLERS:
        rows = [e for e in items if e.get("controller") == name]
        official = {}
        for e in rows:
            if e.get("official_verdict") is not None:
                official[e["official_verdict"]] = official.get(e["official_verdict"], 0) + 1
        out[name] = {"runs": len(rows), "lite_pass": sum(bool(e.get("lite_pass")) for e in rows),
                     "safe_stop": sum(e.get("official_verdict") == SAFE_STOP_VERDICT
                                      for e in rows),
                     "crawler_liftoff_fail": sum(bool(e.get("crawler_liftoff_fail"))
                                                 for e in rows),
                     "official": official, "errors": sum("error" in e for e in rows)}
    return out


def judge_u6(u3_dir: Path, v4_dir: Path) -> dict:
    """Rules 5.2 tables and the U-6 gates (G-1, G-2, G-4)."""
    report = {}
    for name, v4_file, cases, pad in U6_BUNDLES:
        payload = read_json(u3_dir / f"u6_{name}_VB.json")
        items = entries_of(payload)
        keys = sorted({e["case"] for e in items})
        v4_keys = v5_rerun.ids_from(v4_dir / v4_file, pad)
        v4_items = [e for e in entries_of(read_json(v4_dir / v4_file)) if e["case"] in set(keys)]
        problems = [{"key": e["case"], "controller": e["controller"], "problems": p}
                    for e in items
                    if (p := run_v5_problems(e, "VB", U6_TAGS.get(e["controller"], "?"),
                                             needs_bound=e["controller"] == "C2"))]
        report[name] = {
            "VB": _u6_counts(items), "v4_same_keys_record": _u6_counts(v4_items),
            "gates": {
                "G-1": {"pass": (len(items) == 3 * cases and len(keys) == cases
                                 and set(keys) <= set(v4_keys)
                                 and not any("error" in e for e in items)),
                        "runs": len(items), "cases": len(keys), "expected_cases": cases},
                "G-2": {"pass": not problems and bool(_file_commit(payload)),
                        "problems": problems[:20], "code_commit": _file_commit(payload)},
                "G-4": {"pass": not gate_j_p3(items), "stops": gate_j_p3(items)[:20]}}}
    return report


# -------------------------------------------------------------------------------------- G-3
def g3_report(pairs: list[tuple[Path, Path]]) -> dict:
    """Rules 7 G-3: per pair of files the command hash of every common key is equal."""
    out = []
    for before, after in pairs:
        hashes = [{_run_key(e): _hash_of(e) for e in entries_of(read_json(p))}
                  for p in (before, after)]
        common = sorted(set(hashes[0]) & set(hashes[1]))
        unequal = [k for k in common if hashes[0][k] != hashes[1][k] or hashes[0][k] is None]
        out.append({"before": str(before), "after": str(after), "keys": common,
                    "unequal": unequal, "pass": bool(common) and not unequal})
    return {"pass": bool(out) and all(item["pass"] for item in out), "pairs": out}


def _run_key(entry: dict) -> str:
    """Key of one run: the stored key, with the controller of a b5 record."""
    key = v5_rerun.entry_key(entry)
    return key if entry.get("controller") is None else f"{key}|{entry['controller']}"


def _hash_of(entry: dict) -> str | None:
    if entry.get("hash") is not None:
        return entry["hash"]
    if entry.get("commands_sha256") is not None:
        return entry["commands_sha256"]
    return (entry.get("run") or {}).get("commands_sha256")


# -------------------------------------------------------------------------------------- main
def _missing_inputs(bundles, u3_dir: Path, v4_dir: Path, with_u6: bool) -> list[str]:
    paths = [*RULES_REVISIONS, *(v4_dir / b.v4_file for b in bundles)]
    paths += [u3_dir / f"u3_{b.name}_{s}.json" for b in bundles for s in v5_rerun.SETTINGS]
    if with_u6:
        paths += [u3_dir / f"u6_{name}_VB.json" for name, *_ in U6_BUNDLES]
        paths += [v4_dir / v4_file for _, v4_file, *_ in U6_BUNDLES]
    return [str(p) for p in paths if not p.is_file()]


def judge(args) -> int:
    names = [n for n in (args.bundles or "").split(",") if n]
    bundles = [b for b in BUNDLES if not names or b.name in names]
    u3_dir, v4_dir = Path(args.u3_dir), Path(args.v4_dir)
    missing = _missing_inputs(bundles, u3_dir, v4_dir, not args.no_u6)
    if missing:
        print(json.dumps({"exit_code": 2, "missing": missing[:20]}))
        return 2
    report = {"rules": v5_rerun.RULES_PATH.name,
              "rules_sha256": v5_rerun.text_sha256(v5_rerun.RULES_PATH),
              "rules_revisions": [revision_record(path) for path in RULES_REVISIONS],
              "script_sha256": v5_rerun.text_sha256(Path(__file__)),
              "u3": {b.name: judge_bundle(b, u3_dir, v4_dir) for b in bundles}}
    if not args.no_u6:
        report["u6"] = judge_u6(u3_dir, v4_dir)
    g3 = read_json(Path(args.g3)) if args.g3 else {"pass": False, "note": "no G-3 record"}
    report["G-3"] = g3
    gates_ok = g3.get("pass") is True and all(
        gate["pass"] for part in report["u3"].values() for gate in part["gates"].values())
    if not args.no_u6:
        gates_ok = gates_ok and all(gate["pass"] for part in report["u6"].values()
                                    for gate in part["gates"].values())
    code = 0 if gates_ok else 1
    if code:  # rules 7: stop before the judgement; the gate records stay for the question
        for part in report["u3"].values():
            part["phrase"] = None
    report["exit_code"] = code
    Path(args.out_json).write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"exit_code": code, "G-3": g3.get("pass"),
                      "bundles": {n: {g: p["gates"][g]["pass"] for g in p["gates"]}
                                  for n, p in report["u3"].items()}}))
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("judge")
    run.add_argument("out_json")
    run.add_argument("--u3-dir", default=str(DEFAULT_U3_DIR))
    run.add_argument("--v4-dir", default=str(DEFAULT_V4_DIR))
    run.add_argument("--g3", default=None, help="G-3 record (the g3 command)")
    run.add_argument("--bundles", default="", help="comma list (default all U-3 bundles)")
    run.add_argument("--no-u6", action="store_true", help="U-3 only")
    g3 = sub.add_parser("g3")
    g3.add_argument("out_json")
    g3.add_argument("files", nargs="+", help="before after [before after ...]")
    args = parser.parse_args()
    if args.command == "judge":
        return judge(args)
    files = [Path(p) for p in args.files]
    if len(files) % 2 or not all(p.is_file() for p in files):
        print(json.dumps({"exit_code": 2, "error": "pairs of existing files needed"}))
        return 2
    report = g3_report(list(zip(files[::2], files[1::2], strict=True)))
    Path(args.out_json).write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"pass": report["pass"]}))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
