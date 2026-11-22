"""436.9 edition 5 P5-2 / P5-4 (``jp3_remedy_spec_v5.md`` 5): the fixed values computed after
the implementation and before the run (records for the seal; this script prepares them, the
main session runs it).

``p52``  Case replay rows A .. F (``run_v5`` JSON lines of ``j9_cases`` / ``j9_case_f`` /
         ``jp3_case_replay.py``, or an r79 run file) to the P5-2 record: per row its setting,
         job, ``rule_revision``, the J-P3 judged key sums (``jp3a_breach_reads``,
         ``jp3b_breach_over_tol_reads``, ``jp3c_breach_reads``) and the rev 6 counts
         ``jp3_r58_witness_carries``, ``jp3_r59_substeps``, ``jp3_r510_candidates`` (per leg and
         summed). A row without its ``extend_bound_check`` or without a judged key is listed in
         ``problems`` (never read as 0). X11 rows (``*_X11``, ③ rev 5 under test constants) are
         not P5-2 rows (edition 5 erratum 1 1): listed in ``excluded_rows``, not counted. Each
         row keeps its ``identity`` (the job without ``mask`` / ``t4h_dir``), its ``source``
         (the rows file name), ``is_rev6`` and ``p4_on`` (``hydraulic_options``
         ``rod_reading_truth``); ``judged_key_total`` sums the P4-on rev 6 rows only (erratum 1
         1A, prelaunch audit B-2: E's VBJ / LSJ1 .. 4 and F's E branch); ``judged_key_record``
         keeps the sums of the rev 4 rows (A, C) and the P4-off rev 6 rows (B, D, F-B) as
         records; ``inputs`` names every rows file with its sha256 and ``disclosure`` the
         erratum 4 4-1 sentence. ``p54`` lists every replayed T4h file with its sha256.
``p52-compare``  Prelaunch audit B-2 (P5-2 stops "고정 수와 차 > 0", "판정 키 > 0") at steps (4a) /
         (4b): ``--rows <source>=<file>`` against the fixed ``--fixed`` record (its sha256 from
         the fixed list): exit 0 pass, 1 a rev 6 row's per-leg rev 6 counts differ or a P4-on
         rev 6 row has a judged key > 0, 2 not judgeable (another sha256, a source or row set
         other than the record's, a missing key), 3 a tool error.
``p54``  Open-loop replay (commands fixed) of stored T4h records (P5-4: the stored VBH T4h) with
         the run's own monitor setting at ③ revision 5 and at revision 6
         (``t4h_replay.checked_run_config``), the rod fallbacks forced at the run's own
         ``WARN_ROD_PRESSURE_FALLBACK`` events (``contact_replay.fallback_rows_from_events``).
         Per revision: ``retract_tracker_dominated_reads`` (lock / hold reads of a fallback leg
         whose ④ comes from an R5-7 ``retract_tracker`` candidate) and the ``max_over_kN``
         distribution of their stretches; the reduction of rev 6 against rev 5 (P5-4 record,
         expected about 23 %, F8). The plant rod pressure is not in a T4h record, so
         ``max_over_kN`` uses ``p_tr ~ (p_h,read A_h - F_true) / A_ann`` (T4h ``true_force_N``):
         the head reading error enters both revisions alike, A_h / A_ann times (front 3.521,
         rear 3.025; 1.327 / 0.950 kN per head-reading bar; erratum 2 2-2, the output's
         ``plant_rod_pressure``); a record, not a judged value.

Usage (dynamics-dev or Chrono-dev, project root; read only, one output file each):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_p5_fixed_values.py p52 --rows <file> [...]
      --out <p52.json>
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_p5_fixed_values.py p54 --t4h <folder>
      --out <p54.json>
  python -I -B ... p52-compare --fixed <p52.json> --fixed-sha256 <sha> --rows
      j9_cases.jsonl=<file> cd.jsonl=<file> --out <report.json>
p52 / p54: exit 0 written, 2 an existing ``--out`` or no input, 3 a tool error. The stdout's
last line is JSON with ``status``, the counts and the output path. The fixed records are made
by ``step_p5fixed.ps1`` (prelaunch, before the c dry check; spec v5 8 1).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src", ROOT / "04_scripts" / "03_control" / "s9"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

JUDGED_KEYS = ("jp3a_breach_reads", "jp3b_breach_over_tol_reads", "jp3c_breach_reads")
COVERAGE_KEYS = ("jp3_r58_witness_carries", "jp3_r59_substeps", "jp3_r510_candidates")
REVISIONS = (5, 6)
EXIT_WRITTEN, EXIT_NOT_USABLE, EXIT_ERROR = 0, 2, 3


# ------------------------------------------------------------------------------- P5-2
RUNTIME_JOB_FIELDS = ("mask", "t4h_dir")
"""Run-time job fields (placement, output folder): not part of a row's identity."""
P4_OPTION = "rod_reading_truth"
"""``hydraulic_options`` flag of a P4-on run (addendum 4a-2 B2)."""
REV6 = 6
P52_COMPARED_KEYS = COVERAGE_KEYS
"""Prelaunch audit B-2: the rev 6 counts each row of the fixed record must keep (per leg)."""


def read_rows(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(document, dict):
        return document["results"] if "results" in document else [document]
    return document


def _check_of(row: dict) -> dict | None:
    record = row.get("hydraulics_record") or {}
    return record.get("extend_bound_check") or row.get("extend_bound_check")


def row_identity(row: dict) -> str:
    """The row's job without its run-time fields (an r79 row: its key without the candidate
    prefix), with the setting - the same row of another run has the same identity."""
    if row.get("key"):
        key = str(row["key"])
        return json.dumps({"key": key.split("#", 1)[1] if "#" in key else key,
                           "setting": _setting_of(row)}, sort_keys=True)
    job = {name: value for name, value in (row.get("job") or {}).items()
           if name not in RUNTIME_JOB_FIELDS}
    return json.dumps(job, sort_keys=True)


def is_p4_on(row: dict) -> bool:
    return (row.get("hydraulic_options") or {}).get(P4_OPTION) is True


REV4_JUDGED_KEY = "breach_reads"
"""The revision 4 J-P3 judged key (``extend_start_bound.J_P3_NAME``: ``ext_moving.breach_reads``,
kept flat in the record)."""
JUDGED_KEYS_OF_REVISION = {4: (REV4_JUDGED_KEY,), 5: JUDGED_KEYS, 6: JUDGED_KEYS}
JUDGED_KEY_READING = ("정오 4 4-1의 '판정 키'는 줄의 ③ 판에 따른 J-P3 판정 키다"
                      "(판 4a 6.1·4a-2 R6). rev 4 = `ext_moving.breach_reads`, "
                      "rev 5·6 = jp3a/b/c.")
"""control's reading of erratum 4 4-1 (2026-11-22), written into the record and the step
record as it is."""
LEG_COUNT = 4


def row_revision(row: dict, check: dict) -> tuple[int | None, str, str | None]:
    """(revision, source, problem) of a row's ③ record: ``rule_revision`` when the record has
    it, else the controller tag's (``v5_options.extend_start_revision_of_tag``); neither, or
    both but differing, is a problem."""
    from outrigger_sim.hydraulics.v5_options import extend_start_revision_of_tag

    recorded = check.get("rule_revision")
    tagged = extend_start_revision_of_tag(row.get("controller_tag"))
    if recorded is None and tagged is None:
        return None, "none", "no rule_revision and no ③ revision of the tag"
    if recorded is not None and tagged is not None and recorded != tagged:
        return None, "both", f"rule_revision {recorded!r} but the tag's revision {tagged!r}"
    if recorded is not None:
        return recorded, "record", None
    return tagged, "tag", None


def _is_count_list(values) -> bool:
    """Four integer counts >= 0 (436.8 RD-8: a judged key of another shape is never read)."""
    return (isinstance(values, list) and len(values) == LEG_COUNT
            and all(isinstance(value, int) and not isinstance(value, bool) and value >= 0
                    for value in values))


def p52_row(row: dict, problems: list[str], source: str = "") -> dict:
    """The P5-2 values of one case replay row: its ③ revision (:func:`row_revision`), the
    J-P3 judged keys of that revision (rev 4 ``breach_reads``, rev 5 / 6 jp3a / b / c;
    :data:`JUDGED_KEY_READING`), the rev 6 counts of a rev 6 row."""
    label = row.get("key") or json.dumps(row.get("job"), sort_keys=True)
    check = _check_of(row)
    out = {"row": label, "identity": row_identity(row), "source": source,
           "setting": _setting_of(row), "rule_revision": None, "revision_source": None,
           "is_rev6": False, "p4_on": is_p4_on(row)}
    if check is None:
        problems.append(f"{label}: no extend_bound_check")
        return out
    revision, revision_source, problem = row_revision(row, check)
    out.update(rule_revision=revision, revision_source=revision_source,
               is_rev6=revision == REV6)
    if problem is not None:
        problems.append(f"{label}: {problem}")
        return out
    judged_keys = JUDGED_KEYS_OF_REVISION.get(revision)
    if judged_keys is None:
        problems.append(f"{label}: no J-P3 judged keys of revision {revision!r}")
        return out
    for key in judged_keys:
        values = check.get(key)
        if not _is_count_list(values):
            problems.append(f"{label}: {key} missing or not 4 integer counts >= 0")
            continue
        out[key] = values
        out[f"{key}_sum"] = int(sum(values))
    if revision == REV6:
        for key in COVERAGE_KEYS:
            values = check.get(key)
            if not (isinstance(values, list) and len(values) == LEG_COUNT):
                problems.append(f"{label}: {key} missing")
                continue
            out[key] = values
            out[f"{key}_sum"] = int(sum(values))
    return out


X11_SETTING_SUFFIX = "_X11"
"""Erratum 1 1: P5-2 is read on the case replays A .. F; the X11 arm is a sensitivity check."""


def _setting_of(row: dict) -> str | None:
    return row.get("v5_setting") or (row.get("job") or {}).get("setting")


def p52(paths: list[Path]) -> dict:
    """The P5-2 record (erratum 1 1A): every row with its rev 6 counts; ``judged_key_total``
    sums the judged keys of the P4-on rev 6 rows only (E: VBJ, LSJ1 .. 4; F: the E branch);
    the other rows' judged keys stay per row (prelaunch audit B-2)."""
    problems: list[str] = []
    rows, excluded = [], []
    for path in paths:
        for row in read_rows(path):
            setting = _setting_of(row)
            if setting is not None and setting.endswith(X11_SETTING_SUFFIX):
                excluded.append({"setting": setting, "job": row.get("job")})
                continue
            rows.append(p52_row(row, problems, source=path.name))
    judged = [row for row in rows if row["is_rev6"] and row["p4_on"]]
    return {"rule": "jp3_remedy_spec_v5.md P5-2 (fixed after implementation, before the run; "
                    "erratum 1 1: cases A .. F, 1A: the rev 6 counts on the rev 6 rows, the judged "
                    "key total on the P4-on rev 6 rows; erratum 4 4-1)",
            "inputs": [{"path": str(path), "sha256": file_sha256(path)} for path in paths],
            "rows": rows, "problems": problems, "excluded_rows": excluded,
            "rev6_rows": sum(row["is_rev6"] for row in rows), "p4_on_rev6_rows": len(judged),
            "judged_key_total": _judged_sum(judged),
            # erratum 4 4-1: records only (A / C rev 4: breach_reads; the P4-off rev 6 rows
            # B, D, F-B are judged at step (4) by the edition 4a 5.3 case conditions)
            "judged_key_record": {
                "rev4_rows": _judged_sum([row for row in rows if row["rule_revision"] == 4]),
                "p4_off_rev6_rows": _judged_sum([row for row in rows
                                                 if row["is_rev6"] and not row["p4_on"]])},
            "judged_key_reading": JUDGED_KEY_READING,
            "disclosure": P52_DISCLOSURE}


P52_DISCLOSURE = ("P5-2 고정 계산에서 사례 재생 줄의 판정 키와 사례별 합격 값을 실행 전에 보았다"
                  "(원판 5절 설계). 단계 (4)는 같은 코드로 다시 돌려 고정값과 같아야 한다.")
"""Erratum 4 4-1 (sealed 4bc4ecdd): the disclosure sentence of the P5-2 fixed computation, as
written."""


def _judged_sum(rows: list[dict]) -> int:
    """The judged key sum of ``rows``, each by its own revision's keys."""
    return sum(row.get(f"{key}_sum", 0) for row in rows
               for key in JUDGED_KEYS_OF_REVISION.get(row["rule_revision"], ()))


def file_sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _rows_of_sources(values: list[str]) -> dict[str, Path]:
    """``<source name>=<path>`` arguments (the fixed record's ``source`` names)."""
    out = {}
    for value in values:
        name, separator, path = value.partition("=")
        if not separator or name in out:
            raise ValueError(f"--rows {value!r}: one <source name>=<path> per source")
        out[name] = Path(path)
    return out


def p52_compare(fixed_path: Path, fixed_sha256: str, rows: dict[str, Path]) -> dict:
    """Prelaunch audit B-2 (P5-2 stop "고정 수와 차 > 0", "판정 키 > 0"): the rows of the given
    sources against the fixed record. Failed: a rev 6 row whose per-leg rev 6 counts differ
    from the fixed ones, or a P4-on rev 6 row with a judged key > 0. Not judgeable: another
    fixed sha256, a source the record does not name, other row identities than the record's
    (per source), a problem of the record or of the new rows (a missing key)."""
    import hashlib

    report: dict = {"rule": "jp3_remedy_spec_v5.md P5-2 / erratum 1 1A (prelaunch audit B-2)",
                    "fixed": {"path": str(fixed_path), "sha256": fixed_sha256},
                    "failures": [], "not_judgeable": []}
    if hashlib.sha256(fixed_path.read_bytes()).hexdigest() != fixed_sha256:
        report["not_judgeable"].append("--fixed is not of the given sha256")
        return report
    fixed = json.loads(fixed_path.read_text(encoding="utf-8"))
    if fixed.get("problems"):
        report["not_judgeable"].append(f"the fixed record has {len(fixed['problems'])} problems")
    new = p52(list(rows.values()))
    source_of = {path.name: name for name, path in rows.items()}
    if new["problems"]:
        report["not_judgeable"] += new["problems"]
    for name in rows:
        if not any(row["source"] == name for row in fixed["rows"]):
            report["not_judgeable"].append(f"source {name}: not in the fixed record")
    compared = 0
    for name in rows:
        fixed_rows = {row["identity"]: row for row in fixed["rows"] if row["source"] == name}
        new_rows = {row["identity"]: row for row in new["rows"]
                    if source_of.get(row["source"]) == name}
        if set(fixed_rows) != set(new_rows):
            report["not_judgeable"].append(
                f"source {name}: {len(set(fixed_rows) ^ set(new_rows))} rows on one side only")
            continue
        for identity, row in new_rows.items():
            before = fixed_rows[identity]
            if before["is_rev6"] != row["is_rev6"] or before["p4_on"] != row["p4_on"]:
                report["not_judgeable"].append(f"{row['row']}: another revision / P4 state")
                continue
            if not row["is_rev6"]:
                continue
            # erratum 4 4-1 (audit N-1): a difference is judged only with both values present;
            # a missing value on either side is not judgeable, never "no difference"
            absent = [key for key in P52_COMPARED_KEYS
                      if before.get(key) is None or row.get(key) is None]
            if absent:
                report["not_judgeable"].append(f"{row['row']}: {absent} missing on a side")
                continue
            compared += 1
            differing = [key for key in P52_COMPARED_KEYS if before.get(key) != row.get(key)]
            if differing:
                report["failures"].append(f"{row['row']}: {differing} differ from the fixed")
            if row["p4_on"] and any(row.get(f"{key}_sum", 0) for key in JUDGED_KEYS):
                report["failures"].append(f"{row['row']}: a J-P3 judged key > 0")
    if compared == 0 and not report["not_judgeable"]:
        report["not_judgeable"].append("no rev 6 row compared")
    report["rev6_rows_compared"] = compared
    report["status"] = ("failed" if report["failures"] else
                        "not_judgeable" if report["not_judgeable"] else "pass")
    return report


# ------------------------------------------------------------------------------- P5-4
def p54_record(path: Path, revision: int) -> dict:
    """Dominated reads of one stored T4h record replayed at ``revision`` (module docstring)."""
    import t4h_replay

    from outrigger_sim.control import contact_replay as replay
    from outrigger_sim.control.c2 import C2Geometry, C2Phase
    from outrigger_sim.control.extend_start_bound import _DominatedReads
    from outrigger_sim.control.two_pressure import RodSensorState

    arrays, meta = t4h_replay.load_record(path)
    closed_loop, config, _ = t4h_replay.checked_run_config(path.name, meta, "tracked_bound",
                                                          revision)
    geometry = C2Geometry.from_params(closed_loop.PARAMS)
    allowance = t4h_replay.offset_allowance_of(meta, config)
    events = [(float(t), str(name)) for t, name in meta.get("events") or []]
    t_s = np.asarray(arrays["t_s"], float)
    head = np.asarray(arrays["head_pressure_Pa"], float)
    rod = np.asarray(arrays["rod_pressure_Pa"], float)
    stroke = np.asarray(arrays["motor_stroke_m"], float)
    acting = replay._previous(np.asarray(arrays["command_m_s"], float), fill=0.0)
    is_ready = replay._previous(np.asarray(arrays["phase"]), fill="") == C2Phase.READY.value
    seal_band = replay._previous(np.asarray(arrays["seal_band_N"], float))
    true_force = np.asarray(arrays["true_force_N"], float)
    head_area = np.asarray(geometry.head_area_m2, float)
    annulus = np.asarray(geometry.annulus_area_m2, float)
    monitor = replay._offline_monitor(geometry, config)
    fallback_rows = replay.fallback_rows_from_events(events, t_s, config.period_s)
    calibration_rows = replay._calibration_rows(events, t_s, config.period_s)
    offsets = np.asarray(meta.get("zero_offset_N") or np.zeros(4), float)
    dominated = _DominatedReads(600.0 / annulus)
    for row in range(t_s.size):
        is_calibrated = calibration_rows <= row
        monitor.set_zero_offsets_N(np.where(is_calibrated, offsets, 0.0))
        has_allowance = (is_calibrated if allowance.from_s is None
                         else np.full(4, t_s[row] > allowance.from_s + 1e-9))
        monitor.set_offset_allowance_N(np.where(has_allowance, allowance.deduction_N, 0.0))
        for leg, first_row in enumerate(fallback_rows):
            if first_row == row:
                monitor.rod_state[leg] = RodSensorState.FALLBACK
        monitor.read(float(t_s[row]), head[row], rod[row], acting[row], bool(is_ready[row]),
                     seal_band[row], stroke_m=stroke[row])
        trace = monitor.extend_bound_trace_row()
        if trace is None:
            continue
        plant_Pa = (head[row] * head_area - true_force[row]) / annulus  # p_tr proxy
        classes = [_class(value) for value in trace["class"]]
        dominated.add(classes, np.asarray(trace["used_bound_Pa"], float), plant_Pa, trace,
                      true_force[row])
    record = dominated.record()
    over = [row["max_over_kN"] for row in record["retract_tracker_stretch_log"]
            if row["max_over_kN"] is not None]
    return {"file": path.name, "revision": revision,
            "dominated_reads": int(sum(record["retract_tracker_dominated_reads"])),
            "stretches": len(record["retract_tracker_stretch_log"]), "max_over_kN": over}


def _class(value):
    from outrigger_sim.control.extend_start_bound import PeriodClass

    return None if value is None else PeriodClass(value)


def p54(folder: Path) -> dict:
    files = sorted(folder.glob("*.npz"))
    per_revision = {}
    for revision in REVISIONS:
        rows = [p54_record(path, revision) for path in files]
        over = [value for row in rows for value in row["max_over_kN"]]
        per_revision[str(revision)] = {
            "dominated_reads": sum(row["dominated_reads"] for row in rows),
            "stretches": sum(row["stretches"] for row in rows),
            "max_over_kN_p50": float(np.percentile(over, 50)) if over else None,
            "max_over_kN_p90": float(np.percentile(over, 90)) if over else None,
            "max_over_kN_max": max(over) if over else None, "files": rows}
    before, after = (per_revision[str(revision)]["dominated_reads"] for revision in REVISIONS)
    return {"rule": "jp3_remedy_spec_v5.md P5-4 (record; expected reduction about 23 %, F8; "
                    "erratum 4 4-1: the edition 4a VBH run's T4h)",
            "t4h_folder": str(folder), "files": len(files),
            "inputs": [{"file": path.name, "sha256": file_sha256(path)} for path in files],
            "by_revision": per_revision,
            "dominated_reduction": None if before == 0 else 1.0 - after / before,
            "plant_rod_pressure": proxy_disclosure()}


def proxy_disclosure() -> dict:
    """Erratum 1 8 (control review of 8a3c48c7 W-7): the ``max_over_kN`` plant rod pressure is
    the proxy ``(p_h,read A_h - F_true) / A_ann``; a head reading error enters it A_h / A_ann
    times (front 3.521, rear 3.025), as a force 1 bar of head reading is A_h x 1 bar (front
    1.327 kN, rear 0.950 kN; erratum 2 2-2). ``retract_tracker_dominated_reads`` does not use
    it. A record."""
    from outrigger_sim.control.c2 import C2Geometry
    from outrigger_sim.params import load_params

    geometry = C2Geometry.from_params(load_params())
    gains, force_per_bar = {}, {}
    for side, leg in (("front", 0), ("rear", 2)):
        head = float(geometry.head_area_m2[leg])
        annulus = float(geometry.annulus_area_m2[leg])
        # 3 decimals (erratum 2 2-2: front 3.521 / rear 3.025, 1.327 / 0.950 kN)
        gains[side] = round(head / annulus, 3)
        force_per_bar[side] = round(head * 1e5 / 1e3, 3)
    return {"definition": "(head reading x A_h - true_force_N) / A_ann (T4h proxy; the plant "
                          "rod pressure is not in a T4h record)",
            "head_error_gain": gains, "max_over_kN_per_head_bar": force_per_bar,
            "text": (f"a head reading error enters A_h / A_ann times (front "
                     f"{gains['front']:.3f}, rear {gains['rear']:.3f}); as a force, per bar of "
                     f"head reading front {force_per_bar['front']:.3f} kN, rear "
                     f"{force_per_bar['rear']:.3f} kN (erratum 2 2-2)"),
            "dominated_reads_use_it": False, "judged": False}


EXIT_OF_COMPARE = {"pass": 0, "failed": 1, "not_judgeable": 2}


def _main_compare(args) -> int:
    """``p52-compare`` (module docstring): exit 0 pass, 1 failed, 2 not judgeable, 3 error."""
    try:
        report = p52_compare(args.fixed, args.fixed_sha256, _rows_of_sources(args.rows))
    except ValueError as exc:
        print(f"input error: {exc}", file=sys.stderr)
        print(json.dumps({"status": "not_judgeable"}))
        return EXIT_NOT_USABLE
    except Exception as exc:  # noqa: BLE001 (every other failure is a tool error)
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(json.dumps({"status": "error"}))
        return EXIT_ERROR
    report["status"] = ("failed" if report["failures"] else
                        "not_judgeable" if report["not_judgeable"] else "pass")
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1)
    print(json.dumps({"status": report["status"], "failures": len(report["failures"]),
                      "not_judgeable": len(report["not_judgeable"]), "out": str(args.out)}))
    return EXIT_OF_COMPARE[report["status"]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    rows = sub.add_parser("p52")
    rows.add_argument("--rows", type=Path, nargs="+", required=True)
    rows.add_argument("--out", type=Path, required=True)
    replay_parser = sub.add_parser("p54")
    replay_parser.add_argument("--t4h", type=Path, required=True)
    replay_parser.add_argument("--out", type=Path, required=True)
    compare_parser = sub.add_parser("p52-compare")
    compare_parser.add_argument("--fixed", type=Path, required=True)
    compare_parser.add_argument("--fixed-sha256", required=True)
    compare_parser.add_argument("--rows", nargs="+", required=True,
                                help="<source name>=<rows file> (the fixed record's names)")
    compare_parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        print(json.dumps({"status": "not_usable", "reason": "--out exists"}))
        return EXIT_NOT_USABLE
    if args.command == "p52-compare":
        return _main_compare(args)
    try:
        document = p52(args.rows) if args.command == "p52" else p54(args.t4h)
    except Exception as exc:  # a tool error
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(json.dumps({"status": "error"}))
        return EXIT_ERROR
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(document, handle, indent=1)
    count = len(document.get("rows", [])) or document.get("files", 0)
    if not count:
        print(json.dumps({"status": "not_usable", "reason": "no input row", "out": str(args.out)}))
        return EXIT_NOT_USABLE
    print(json.dumps({"status": "written", "count": count,
                      "problems": len(document.get("problems", [])), "out": str(args.out)}))
    return EXIT_WRITTEN


if __name__ == "__main__":
    sys.exit(main())
