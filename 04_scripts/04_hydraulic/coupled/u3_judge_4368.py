"""436.8 path 1 judge of U-3 / U-6 (H-3 / H-4), new version (rules rev5 R5-A1 / R5-A2).

``u3_judge_k1.py`` stays the record-only revision (rev5 R5-A2); the H-3 / H-4 grades come from
this file. It reuses the reading, quantity, gate and U-6 code of ``u3_judge_k1`` unchanged and
replaces only the definitions listed below (rev5 R5-A3):

  D-01  settle v2 is recomputed from the run's own ``settle_v2`` record (spec 398.3, rev3 R3-B6,
        rev4 R4-C2 units: Delta phi / theta in rad, pad x / y in mm), not from a stored v4
        re-judgement baseline.
  D-02  h9 and study D get settle v2 too (D: ``results[]`` entries, top-level ``settle_v2``).
  D-03  study D start-gap pads use their start-gap target; the table-target outcome is a record.
  D-04  ``status``: ``checked`` recompute, ``no_table_check`` settle item not applicable (count),
        ``error`` / no block = ``판정 불가``; ``gate``: ``judged`` (ok false = settle_check_fail),
        ``settle_check_fail`` (recomputed ok must be false), ``record_only`` (not graded).
        Recomputed values differing from ``result`` (1e-9) = ``판정 불가`` (S-13); recorded
        ``tolerances`` other than 1 mm / 0.005 deg / 0.002 deg stop the bundle (S-11);
        ``table_sha256`` other than the table file's, or a table-sourced ``gap_target_mm``
        other than ``table_gap_target_mm`` = ``판정 불가``.
  D-05  study B reads ``rev85/finB2_x426b.json`` and does not filter by ``suite`` (rev3 R3-B2);
        whether its key set equals ``finB2_x426b_rejudged.json``'s is recorded.
  D-06  reuse: ``reuse == "d1"`` count = ``meta.v5.reuse_d1.<suite>.reused`` count, and every
        ``d1_key`` names exactly one ``d1.key`` line of the H-1 output (rev3 R3-B3).
A ``판정 불가`` line makes its bundle ``판정 불가`` (rules 8.1); it is not a VB-only failure.

Usage (python-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/u3_judge_4368.py --out <report.json>
      --u3-dir <resume_k1 U-3 folder> --v4-dir 06_analysis/02_control/s9 --h1-d1 <h1_d1.jsonl>
      [--g3 <g3.json>] [--bundles slope,h6,...] [--no-u6] [--k1-report <u3_judge_k1 report>]
      [--rules-dir <verif_matrix>]
  The settle table is the file each ``settle_v2.inputs.table`` names (its sha256 is checked).
Exit codes: 0 judged, 1 a gate / stop / 판정 불가 finding, 2 input error, 3 internal error.
"""

from __future__ import annotations

import argparse
import dataclasses
import math
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "04_scripts" / "03_control" / "s9", ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.append(str(_path))

import judge4368_common as common  # noqa: E402
import u3_judge_k1 as base  # noqa: E402

GRADES = (*base.GRADES, "not_judgeable")
NOT_JUDGEABLE = "not_judgeable"
SETTLE_CHECK_FAIL = "settle_check_fail"
GAP_TOL_MM = 1.0
ATTITUDE_TOL_MIN_DEG = 0.005
ATTITUDE_RESIDUAL_MARGIN_DEG = 0.002
"""Spec 398.3 settle v2 thresholds (rev3 R3-B6)."""
RECORDED_TOLERANCES = {
    "gap_mm": GAP_TOL_MM,
    "attitude_min_deg": ATTITUDE_TOL_MIN_DEG,
    "attitude_residual_margin_deg": ATTITUDE_RESIDUAL_MARGIN_DEG,
}
GAP_SOURCE_TABLE = "table"
STUDY_B_INPUT = "rev85/finB2_x426b.json"
STUDY_B_OLD_INPUT = "rev85/finB2_x426b_rejudged.json"
DEFINITION_CHANGES = ("D-01", "D-02", "D-03", "D-04", "D-05", "D-06")


@dataclasses.dataclass(frozen=True)
class Bundle4368:
    """One U-3 bundle with the 436.8 settle v2 switch (``settle_v2``) and suite filter."""

    name: str
    v4_file: str
    kind: str
    expected: int
    suite: str | None = None
    settle_v2: bool = False


BUNDLES = (
    Bundle4368("slope", "rev85/finB2_harness_rejudged.json", "record", 110, "slope", True),
    Bundle4368("h6", "rev85/finB2_harness_rejudged.json", "record", 26, "h6", True),
    Bundle4368("h9", "rev85/finB2_h9.json", "record", 24, "h9", True),  # D-02
    Bundle4368("g6", "rev85/finB2_p0.json", "g6", 116, "g6"),
    Bundle4368("g8", "rev85/finB2_p0.json", "g8", 516, "g8"),
    Bundle4368("p3b", "rev85/finB2_p0.json", "record", 171, "p3b"),
    Bundle4368("x426b", STUDY_B_INPUT, "record", 84, None, True),  # D-05: no suite filter
    Bundle4368("C", "rev85/fin_x426_C.json", "r72", 34),
    Bundle4368("D", "rev85/fin_x426_D.json", "slope_result", 33, None, True),  # D-02
)


# ---------------------------------------------------------------------------- settle v2 (D-01)
def _close(a: Any, b: Any) -> bool:
    """Rules 9.2 K-10 form: booleans equal, numbers within 1e-9, lists element-wise."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b or a == b
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return (
            math.isfinite(a) and math.isfinite(b) and abs(float(a) - float(b)) <= common.COMPARE_EPS
        )
    return a == b


def recompute_settle_v2(inputs: dict, gap_target_mm: list[float] | None = None) -> dict:
    """Spec 398.3 settle v2 from the recorded inputs (rev4 R4-C2 units).

    pen_mean_i [mm] = pen_inst_i [mm] + (y_i [mm] d_phi [rad] - x_i [mm] d_theta [rad]);
    gap ok when every |pen_mean_i + gap_target_i| <= 1 mm; attitude ok when every
    |attitude error| <= max(0.005 deg, |residual| + 0.002 deg).
    """
    targets = inputs["gap_target_mm"] if gap_target_mm is None else gap_target_mm
    d_phi_rad, d_theta_rad = (math.radians(float(v)) for v in inputs["d_attitude_deg"])
    pen_mean = [
        float(pen) + (float(y) * 1e3 * d_phi_rad - float(x) * 1e3 * d_theta_rad)
        for pen, (x, y) in zip(inputs["pen_inst_mm"], inputs["pad_xy_m"], strict=True)
    ]
    pen_plus_gap = [p + float(g) for p, g in zip(pen_mean, targets, strict=True)]
    tolerances = [
        max(ATTITUDE_TOL_MIN_DEG, abs(float(r)) + ATTITUDE_RESIDUAL_MARGIN_DEG)
        for r in inputs["residual_deg"]
    ]
    is_gap_ok = all(abs(e) <= GAP_TOL_MM + common.COMPARE_EPS for e in pen_plus_gap)
    is_attitude_ok = all(
        abs(float(e)) <= tol + common.COMPARE_EPS
        for e, tol in zip(inputs["attitude_error_deg"], tolerances, strict=True)
    )
    return {
        "pen_mean_mm": pen_mean,
        "pen_plus_gap_mm": pen_plus_gap,
        "gap_ok": is_gap_ok,
        "attitude_tol_deg": tolerances,
        "attitude_ok": is_attitude_ok,
        "ok": is_gap_ok and is_attitude_ok,
    }


def tolerance_problems(block: dict) -> list[str]:
    """Rev4 R4-C2: recorded tolerances equal spec 398.3 within 1e-9 (else S-11)."""
    recorded = block.get("tolerances") or {}
    return [
        f"tolerances.{name} {recorded.get(name)!r} != {value}"
        for name, value in RECORDED_TOLERANCES.items()
        if not isinstance(recorded.get(name), (int, float))
        or abs(float(recorded[name]) - value) > common.COMPARE_EPS
    ]


def source_problems(inputs: dict, table_sha256: dict[str, str | None]) -> list[str]:
    """Rev3 R3-B6 / rev4 R4-C2: table file sha256 and a table-sourced target."""
    problems = []
    table = inputs.get("table")
    if table not in table_sha256:
        path = Path(table) if table else None
        table_sha256[table] = common.file_sha256(path) if path and path.is_file() else None
    if table_sha256[table] is None:
        problems.append(f"table file {table!r} not readable")
    elif inputs.get("table_sha256") != table_sha256[table]:
        problems.append("table_sha256 differs from the table file")
    table_target = inputs.get("table_gap_target_mm")
    if table_target is None:
        problems.append("table_gap_target_mm missing (F-5)")
    elif inputs.get("gap_target_source") == GAP_SOURCE_TABLE and not _close(
        [float(v) for v in inputs["gap_target_mm"]], [float(v) for v in table_target]
    ):
        problems.append("table-sourced gap_target_mm != table_gap_target_mm")
    return problems


def assess_settle_v2(block: dict | None, table_sha256: dict[str, str | None]) -> dict:
    """Rev3 R3-B6 settle item of one line: ``state`` ``fail`` / ``ok`` / ``not_applicable`` /
    ``record_only`` / ``not_judgeable``, with the reasons and the S-11 tolerance problems."""
    if block is None:
        return {"state": NOT_JUDGEABLE, "reasons": ["settle_v2 block missing"]}
    status = block.get("status")
    if status == "no_table_check":
        return {"state": "not_applicable", "reasons": ["no_table_check (가정: v1 대상 아님)"]}
    if status != "checked":
        return {"state": NOT_JUDGEABLE, "reasons": [f"status {status!r}"]}
    inputs, recorded = block.get("inputs") or {}, block.get("result") or {}
    out: dict[str, Any] = {"tolerance_problems": tolerance_problems(block)}
    try:
        again = recompute_settle_v2(inputs)
    except (KeyError, TypeError, ValueError) as exc:
        return {**out, "state": NOT_JUDGEABLE, "reasons": [f"inputs unreadable: {exc!r}"]}
    reasons = [
        f"result.{name} differs from the recomputation"
        for name in (
            "pen_mean_mm",
            "pen_plus_gap_mm",
            "gap_ok",
            "attitude_tol_deg",
            "attitude_ok",
            "ok",
        )
        if not _close(recorded.get(name), again[name])
    ]
    reasons += source_problems(inputs, table_sha256)
    out["recomputed_ok"] = again["ok"]
    out["start_gap_table_ok"] = _table_target_outcome(inputs)
    gate = recorded.get("gate")
    if gate == SETTLE_CHECK_FAIL and again["ok"]:
        reasons.append("gate settle_check_fail but the recomputed ok is true")
    if reasons:
        return {**out, "state": NOT_JUDGEABLE, "reasons": reasons}
    if gate == "record_only":
        return {**out, "state": "record_only", "reasons": []}
    if gate not in ("judged", SETTLE_CHECK_FAIL):
        return {**out, "state": NOT_JUDGEABLE, "reasons": [f"gate {gate!r}"]}
    return {**out, "state": "ok" if again["ok"] else "fail", "reasons": []}


def _table_target_outcome(inputs: dict) -> bool | None:
    """Rev3 R3-B7 record: the ok of a start-gap line computed with the table targets."""
    if inputs.get("gap_target_source") == GAP_SOURCE_TABLE or not inputs.get("table_gap_target_mm"):
        return None
    return recompute_settle_v2(inputs, [float(v) for v in inputs["table_gap_target_mm"]])["ok"]


def row_verdict(entry: dict, kind: str) -> str | None:
    """The verdict before the settle item: study D ``verdict_rows``; a record's stored verdict,
    rebuilt from its rows when the stored one is the v1 settle failure."""
    if kind == "slope_result":
        return entry.get("verdict_rows", entry.get("verdict"))
    if entry.get("verdict") != SETTLE_CHECK_FAIL:
        return entry.get("verdict")
    import s9_settle_rejudge

    return s9_settle_rejudge.rebuild_row_verdict(entry)


def grade(entry: dict, bundle: Bundle4368, table_sha256: dict[str, str | None]) -> dict:
    """Grade of one record (D-01 .. D-04 for the settle-v2 bundles, else ``u3_judge_k1``)."""
    if not bundle.settle_v2 or "error" in entry:
        return base.grade(
            entry,
            base.Bundle(bundle.name, bundle.v4_file, bundle.kind, bundle.expected, bundle.suite),
            None,
        )
    settle = assess_settle_v2(entry.get("settle_v2"), table_sha256)
    if bundle.kind == "slope_result":
        flags = base._rows_flags(entry.get("rows") or {})  # noqa: SLF001
    else:
        flags = list(entry.get("flags") or [])
    if settle["state"] == NOT_JUDGEABLE:
        return {"grade": NOT_JUDGEABLE, "verdict": None, "flags": flags, "settle_v2": settle}
    verdict = SETTLE_CHECK_FAIL if settle["state"] == "fail" else row_verdict(entry, bundle.kind)
    return {
        "grade": base._verdict_grade(verdict, bool(flags)),  # noqa: SLF001
        "verdict": verdict,
        "flags": flags,
        "settle_v2": settle,
    }


# ------------------------------------------------------------------------------- reuse (D-06)
def read_d1_keys(path: Path | None) -> dict[str, int] | None:
    """``d1.key`` -> number of H-1 lines with it (None when no file is given)."""
    if path is None:
        return None
    counts: dict[str, int] = {}
    for line in common.read_jsonl(path):
        key = (line.get("d1") or {}).get("key")
        if key is not None:
            counts[key] = counts.get(key, 0) + 1
    return counts


def reuse_check(
    payload: dict, items: list[dict], suite: str, d1_keys: dict[str, int] | None
) -> dict:
    """Rev3 R3-B3: reuse count vs the meta list, ``d1_key`` unique in the H-1 output."""
    reused = [e for e in items if e.get("reuse") == "d1"]
    meta = (((payload.get("meta") or {}).get("v5") or {}).get("reuse_d1") or {}).get(suite)
    meta_count = None if meta is None else len(meta.get("reused") or [])
    bad_keys = []
    if reused and d1_keys is None:
        raise common.InputError("reused lines need --h1-d1 (rev3 R3-B3 d1_key check)")
    for entry in reused:
        if (d1_keys or {}).get(entry.get("d1_key"), 0) != 1:
            bad_keys.append(
                {
                    "id": entry.get("id"),
                    "d1_key": entry.get("d1_key"),
                    "matches": (d1_keys or {}).get(entry.get("d1_key"), 0),
                }
            )
    is_count_ok = (meta_count or 0) == len(reused)
    return {
        "reused": len(reused),
        "meta_reused": meta_count,
        "count_equal": is_count_ok,
        "id_field": "d1.key",
        "d1_key_not_unique": bad_keys,
        "pass": is_count_ok and not bad_keys,
    }


# ----------------------------------------------------------------------------------- bundles
def transition_table(pairs: list[tuple[str, str]]) -> dict:
    table = {a: dict.fromkeys(GRADES, 0) for a in GRADES}
    for before, after in pairs:
        table[before][after] += 1
    return table


def judge_bundle(bundle: Bundle4368, u3_dir: Path, v4_dir: Path, d1_keys, table_sha256) -> dict:
    """Grades, tables and gates of one U-3 bundle with the 436.8 definitions."""
    v4_path = v4_dir / bundle.v4_file
    v4_keys = base.v5_rerun.ids_from(
        v4_path, "B", suites=None if bundle.suite is None else (bundle.suite,)
    )
    graded, values, keysets, errors, gate2, commits = {}, {}, {}, {}, [], {}
    j_p3_stops, fallback_stops, reuse = [], [], None
    for setting in base.v5_rerun.SETTINGS:
        payload = common.read_json(u3_dir / f"u3_{bundle.name}_{setting}.json")
        commits[setting] = base._file_commit(payload)  # noqa: SLF001
        items = base.entries_of(payload, bundle.suite)
        keys = [base.v5_rerun.entry_key(e) for e in items]
        keysets[setting], errors[setting] = (
            keys,
            [k for k, e in zip(keys, items, strict=True) if "error" in e],
        )
        graded[setting] = {
            k: grade(e, bundle, table_sha256) for k, e in zip(keys, items, strict=True)
        }
        values[setting] = {
            k: base.quantities(e, bundle.kind) for k, e in zip(keys, items, strict=True)
        }
        tag = base.EXPECTED_TAGS[setting]
        gate2 += [
            {"setting": setting, "key": k, "problems": p}
            for k, e in zip(keys, items, strict=True)
            if (p := base.run_v5_problems(e, setting, tag, needs_bound=setting == "VB"))
        ]
        if setting == "VB":
            j_p3_stops = base.gate_j_p3(items, bundle.expected)
            fallback_stops = base.gate_fallback(items, bundle.expected)
        if bundle.settle_v2 and bundle.kind == "record":
            reuse = (reuse or {}) | {
                setting: reuse_check(payload, items, bundle.suite or bundle.name, d1_keys)
            }
    return _bundle_report(
        bundle,
        graded,
        values,
        keysets,
        v4_keys,
        errors,
        gate2,
        commits,
        j_p3_stops,
        fallback_stops,
        reuse,
    )


def _settle_counts(graded: dict) -> dict:
    counts: dict[str, int] = {}
    tolerance = []
    for key, record in graded.items():
        settle = record.get("settle_v2")
        if settle is None:
            continue
        counts[settle["state"]] = counts.get(settle["state"], 0) + 1
        if settle.get("tolerance_problems"):
            tolerance.append({"key": key, "problems": settle["tolerance_problems"]})
        if settle.get("start_gap_table_ok") is not None:
            counts["start_gap_lines"] = counts.get("start_gap_lines", 0) + 1
            if settle["start_gap_table_ok"] != settle.get("recomputed_ok"):
                counts["start_gap_ok_differs_with_table_target"] = (
                    counts.get("start_gap_ok_differs_with_table_target", 0) + 1
                )
    return {"states": counts, "tolerance_S11": tolerance}


def _bundle_report(
    bundle,
    graded,
    values,
    keysets,
    v4_keys,
    errors,
    gate2,
    commits,
    j_p3_stops,
    fallback_stops,
    reuse,
) -> dict:
    v0, vb = graded["V0"], graded["VB"]
    undecided = sorted(
        {k for setting in graded for k, r in graded[setting].items() if r["grade"] == NOT_JUDGEABLE}
    )
    judged_v0 = {k: r for k, r in v0.items() if k not in undecided}
    judged_vb = {k: r for k, r in vb.items() if k not in undecided}
    classes = base.classify_pairs(judged_v0, judged_vb)
    counts = {g: sum(1 for r in vb.values() if r["grade"] == g) for g in GRADES}
    settle = {s: _settle_counts(graded[s]) for s in graded}
    g1 = {
        "pass": (
            not errors["V0"]
            and not errors["VB"]
            and all(len(keysets[s]) == bundle.expected for s in keysets)
            and all(set(keysets[s]) == set(v4_keys) for s in keysets)
            and len(v4_keys) == bundle.expected
        ),
        "expected": bundle.expected,
        "counts": {s: len(k) for s, k in keysets.items()},
        "v4_keys": len(v4_keys),
        "errors": errors,
    }
    gates = {
        "G-1": g1,
        "G-2": {
            "pass": not gate2 and all(commits.values()),
            "problems": gate2[:20],
            "code_commit": commits,
        },
        "G-4": {"pass": not j_p3_stops, "stops": j_p3_stops[:20]},
        "G-5": {
            "pass": not classes["vb_only_failure"],
            "vb_only_failures": classes["vb_only_failure"],
        },
        "G-6": {"pass": not fallback_stops, "stops": fallback_stops[:20]},
        "S-11 settle tolerances": {"pass": not any(settle[s]["tolerance_S11"] for s in settle)},
    }
    if reuse is not None:
        gates["R3-B3 reuse"] = {"pass": all(r["pass"] for r in reuse.values()), **reuse}
    status = (
        "판정 불가"
        if undecided
        else ("judged" if all(g["pass"] for g in gates.values()) else "stopped")
    )
    return {
        "bundle": bundle.name,
        "kind": bundle.kind,
        "v4_file": bundle.v4_file,
        "settle_v2": bundle.settle_v2,
        "status": status,
        "not_judgeable_keys": undecided,
        "vb_counts": counts,
        "phrase": None
        if status != "judged"
        else base.phrase({g: counts[g] for g in base.GRADES}, len(classes["vb_only_failure"])),
        "transition_V0_VB": transition_table(
            [(v0[k]["grade"], vb[k]["grade"]) for k in vb if k in v0]
        ),
        "differences_VB_minus_V0": base.differences(values["V0"], values["VB"]),
        "classes": classes,
        "settle_v2_counts": settle,
        "gates": gates,
        "grades": {s: {k: r["grade"] for k, r in graded[s].items()} for s in graded},
    }


def study_b_keyset_record(v4_dir: Path) -> dict:
    """D-05 record: whether the two study B files have the same pad-B key set."""
    new = set(base.v5_rerun.ids_from(v4_dir / STUDY_B_INPUT, "B", suites=None))
    old_path = v4_dir / STUDY_B_OLD_INPUT
    if not old_path.is_file():
        return {"input": STUDY_B_INPUT, "keys": len(new), "old_file": "없음"}
    old = set(base.v5_rerun.ids_from(old_path, "B", suites=None))
    return {
        "input": STUDY_B_INPUT,
        "keys": len(new),
        "old_file": STUDY_B_OLD_INPUT,
        "old_keys": len(old),
        "same_key_set": new == old,
        "only_new": sorted(new - old)[:10],
        "only_old": sorted(old - new)[:10],
    }


def compare_with_k1(report: dict, k1_report_path: Path | None) -> dict | None:
    """Rev5 R5-A2: lines whose grade differs from the record-only ``u3_judge_k1`` report."""
    if k1_report_path is None:
        return None
    k1 = common.read_json(k1_report_path)
    out = {}
    for name, part in report["u3"].items():
        old = ((k1.get("u3") or {}).get(name) or {}).get("grades") or {}
        differing = [
            {"setting": s, "key": k, "k1": old.get(s, {}).get(k), "4368": g}
            for s, grades in part["grades"].items()
            for k, g in grades.items()
            if old.get(s, {}).get(k) != g
        ]
        out[name] = {
            "n_differ": len(differing),
            "lines": differing[:40],
            "explained_by": list(DEFINITION_CHANGES),
        }
    return out


# --------------------------------------------------------------------------------------- main
def judge(args: argparse.Namespace) -> dict:
    names = [n for n in (args.bundles or "").split(",") if n]
    bundles = [b for b in BUNDLES if not names or b.name in names]
    u3_dir, v4_dir = Path(args.u3_dir), Path(args.v4_dir)
    missing = [
        str(p)
        for p in [
            *(v4_dir / b.v4_file for b in bundles),
            *(u3_dir / f"u3_{b.name}_{s}.json" for b in bundles for s in base.v5_rerun.SETTINGS),
        ]
        if not p.is_file()
    ]
    if missing:
        raise common.InputError(f"missing inputs: {missing[:10]}")
    d1_keys = read_d1_keys(args.h1_d1)
    table_sha256: dict[str, str | None] = {}
    report: dict[str, Any] = {
        "u3": {b.name: judge_bundle(b, u3_dir, v4_dir, d1_keys, table_sha256) for b in bundles}
    }
    if any(b.name == "x426b" for b in bundles):
        report["study_B_keyset"] = study_b_keyset_record(v4_dir)
    if not args.no_u6:
        report["u6"] = base.judge_u6(u3_dir, v4_dir)  # rev3 R3-B4: same official_verdict count
    g3 = common.read_json(Path(args.g3)) if args.g3 else {"pass": False, "note": "no G-3 record"}
    report["G-3"] = g3
    report["vs_u3_judge_k1"] = compare_with_k1(report, args.k1_report)
    findings = [] if g3.get("pass") is True else ["G-3 not passed"]
    for name, part in report["u3"].items():
        findings += [
            f"{name}: {gate} not passed"
            for gate, value in part["gates"].items()
            if not value["pass"]
        ]
        if part["status"] == "판정 불가":
            findings.append(f"{name}: 판정 불가 ({len(part['not_judgeable_keys'])} keys)")
    for name, part in (report.get("u6") or {}).items():
        findings += [
            f"u6 {name}: {gate} not passed"
            for gate, value in part["gates"].items()
            if not value["pass"]
        ]
    report["findings"] = findings
    return report


def parser() -> argparse.ArgumentParser:
    out = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    common.add_common_arguments(out)
    out.add_argument("--u3-dir", type=Path, required=True, help="436.8 U-3 / U-6 output folder")
    out.add_argument("--v4-dir", type=Path, required=True, help="stored s9 folder (key files)")
    out.add_argument("--h1-d1", type=Path, default=None, help="H-1 output (resume_k1/h1_d1.jsonl)")
    out.add_argument("--g3", default=None, help="G-3 record (u3_judge_k1.py g3)")
    out.add_argument("--bundles", default="", help="comma list (default all U-3 bundles)")
    out.add_argument("--no-u6", action="store_true", help="U-3 only")
    out.add_argument(
        "--k1-report",
        type=Path,
        default=None,
        help="u3_judge_k1 report of the same outputs (rev5 R5-A2 differing lines)",
    )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return common.run_judge(
        judge,
        args,
        script=Path(__file__).resolve(),
        old_tools=(HERE / "u3_judge_k1.py",),
        changes=DEFINITION_CHANGES,
    )


if __name__ == "__main__":
    sys.exit(main())
