"""436.9 edition 6 path 1 judges (``jp3_remedy_spec_v6.md`` 4 step 4a, 6.1 .. 6.3, 6.6; 8 Y-5 /
Y-6): j9_main with the edition 5 judgement readings (1) .. (3), the sensitivity rows, the
confirmation stage (가) and the grid (나).

Sub-commands (every one writes ``--out``, never overwritten):

``j9main``  ``--edition 6`` (VBL / LSL1 .. LSL4 against V0; VBL -> VB, LSL<n> -> LS<n> of the
            436.8 tables) or ``--edition 5`` (VBJ / LSJ: the edition 5 j9_main with the readings,
            the reproduction of the edition 5 judgement 5 2). The ``jp3_j9main_judge.judge``
            definitions with the readings of 6.2:
            * (1) J1 baseline per item: on a pair whose reference fails J1, a new gate is judged
              by its item (``Fmin_after_*`` -> J2, ``fault0`` -> J7, ``end_att`` -> J4 / J6; the
              gate entry becomes a record); a new gate without an item (``no_lift``,
              ``recurrence``, ``U832_*``, ``U57_*``) stays a J1 failure. Counted per (row,
              phase, item): ``vb_fail_pair_items`` (J1 once per pair); ``vb_fail_items`` keeps
              the gate-level count.
            * (2) L-b judged on the relative reading (the item fails where VB passes it);
              ``L-b_absolute`` (an LS row failing J3 / J5 on its own) is a record.
            * (3) the S8 F-5 clause and the criteria 6 stop values with no post-stop sample
              (``soil_stop_crawler.after_stop_chunks`` 0, stop values None) and the same on the
              V0 line of the pair are ``not_applicable_harness`` (a record).
            * ``baseline_failures``: ``counted`` computed (reference failures that are counted
              failures; 0 by the readings), fail / undetermined entries apart from FLAG / record.
            * Edition 6 identity (6.1): tag ``final_C4G2_P3W_LAS_K1_LSB``, the ③ revision 6
              items, ``lsb_components`` = {A_i, A_ii, B3} as a set, ``lsb_settings`` = the sealed
              defaults; J-P3 judged rows must be 200 (``setting_defect`` else, 0 not judgeable).
            * A missing line, an error line, a line of another setting: not judgeable.
``sens``    ``--keys`` a sealed key file (``sens_keys_v2.json`` 6.2 or ``confirm_a_keys_v2.json``
            6.3 (가); its sha256 is checked), ``--rows`` the run of its jobs (``run_v5`` batch
            ``ed6_keys``), ``--v0`` the stored V0 rows. Every key line must have one result line
            and a V0 pair (not judgeable else). A unit (setting, row, phase) fails on a counted
            J1 .. J11 item (readings (1) and (3)), an S8 SA-4 failure or a stop; the J7
            stiffness exception of the four sensitivity settings (6.2, single condition: the
            new J7 names, first ``:`` token, are exactly ``WARN_PROBE_STIFFNESS_OUT_OF_RANGE``)
            turns that J7 into a record (``j7_stiffness_exempt``). Probe-seen units
            (``probe_seen``) only stop; the others take the cluster rule (k = 2): a (setting,
            row) with 2+ failing phases, or more than 2 single-phase failures, fails. J-P3:
            expected judged rows (104 / 56).
``grid``    ``--keys confirm_b_grid192.json``, ``--rows`` the VBL grid run: the 174 opportunity
            lines (key file ``v0_pass``) fail by ``event_output.pass`` false (allowed 1), every
            line has FAULT 0 (``fault_periods``, ``fault_events``, gate ``fault0``, a ``FAULT``
            event), J-P3 judged rows 192; WARN names are recorded against the stored V0 grid line
            and never judged (6.3 revision 8 reading); the 18 V0-failing lines: FAULT and J-P3
            only.

Edition 6 erratum 2 2-1 (step 5, implementation checks; Y-14):

``hash-match``  ``--reference`` rows (a stored output) against ``--rows`` (the rerun) by job:
            every reference job (``--setting`` keeps only that setting's lines) has exactly
            one rerun line without an error and the same ``commands_sha256``; the rerun has
            no other job. Used for P5-1-type invariance (606f8713 cases / case F / C·D / X11)
            and the probe reproduction (cbdb4d28, P6-3).
``d0-1``        ``hash-match`` of D0 variant 1 (``--setting D0-1``, 8 lines) against the stored
            D0 run (390f88a9, P6-0).
``t8``          P6-1: the ``ed6_t8`` rows (22 jobs x VBL, VBL0; ``--main-jsonl`` gives the jobs):
            a pair without ``WARN_ROD_PRESSURE_FALLBACK`` on both lines has the same
            ``commands_sha256`` (else failed); a pair with it is a record; no pair without it
            is not judgeable; a missing or extra line, an error line, a line without
            ``event_names`` / ``events`` or a 64-character hash: not judgeable.
``cases``       P6-2: the ``ed6_cases`` rows (cases E and F x VBL, LSL1 .. LSL4): the 6.1
            identity, every row a judged J-P3 row (10; else setting defect, 0 not judgeable),
            J-P3 without a breach (H-7 failed); the ``lsb_record`` activations are a record.

======  ==================  ====================================================================
exit    status              meaning
======  ==================  ====================================================================
0       ``pass``            no failure, no setting defect, no not-judgeable reason
1       ``failed``          a counted failure (or a probe-unit stop) - the other reasons kept
2       ``setting_defect``  no failure; an identity defect or another J-P3 judged row count
2       ``not_judgeable``   no failure, no defect; a missing line / V0 pair / key, 0 judged rows,
                            another key file sha256, an existing ``--out``
3       ``error``           a tool error (every unexpected exception)
======  ==================  ====================================================================

Usage (dynamics-dev, the code checkout root):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_ed6_judge.py j9main --edition 6
      --rows <ed6_j9_main.jsonl> --v0 <v5/main.jsonl> --v0-sha256 <sha> --out <report.json>
  python -I -B ... sens --keys <sens_keys_v2.json> --rows <run.jsonl> --v0 ... --out ...
  python -I -B ... grid --keys <confirm_b_grid192.json> --rows <run.jsonl> --grid-root <repo>
      --out ...
  python -I -B ... hash-match --reference <stored.jsonl> --rows <rerun.jsonl> --out ...
  python -I -B ... d0-1 --reference <d0_plant_split.jsonl> --rows <d0_1.jsonl> --out ...
  python -I -B ... t8 --rows <ed6_t8.jsonl> --main-jsonl <v5/main.jsonl> --out ...
  python -I -B ... cases --rows <ed6_cases.jsonl> --out ...
The stdout's last line is JSON with ``status`` and the report path (no judged values).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import jp3_j9main_judge as base  # noqa: E402

EXIT_PASS, EXIT_FAILED, EXIT_STOP, EXIT_ERROR = 0, 1, 2, 3
EXIT_OF_STATUS = {"pass": EXIT_PASS, "failed": EXIT_FAILED, "setting_defect": EXIT_STOP,
                  "not_judgeable": EXIT_STOP}
SETTING_MAPS = {
    5: {"VBJ": "VB", "LSJ1": "LS1", "LSJ2": "LS2", "LSJ3": "LS3", "LSJ4": "LS4"},
    6: {"VBL": "VB", "LSL1": "LS1", "LSL2": "LS2", "LSL3": "LS3", "LSL4": "LS4"},
}
ED6_TAG = "final_C4G2_P3W_LAS_K1_LSB"
ED6_P3_OFF_TAG = "final_C4G2_LAS_K1_LSB"
SEALED_COMPONENTS = frozenset({"A_i", "A_ii", "B3"})
J9_MAIN_JUDGED_ROWS = 200
GATE_ITEMS = {"Fmin_after_W": ("J2",), "Fmin_after_event": ("J2",), "fault0": ("J7",),
              "end_att": ("J4", "J6")}
"""Reading (1): the item a new gate is judged by when the reference fails J1."""
SENSITIVITY_SETTINGS = ("VBLc005", "VBLc04", "VBLv05", "VBLv15")
STIFFNESS_WARNING = "WARN_PROBE_STIFFNESS_OUT_OF_RANGE"
CLUSTER_K = 2
SEALED_KEY_FILES = {
    "sens_keys_v2.json": ("70f4bb6d7afaa3f8b7ac3437db3ce5d2e4d9cca05e74b9a5c38f3b0269b77f74",
                          184, 104),
    "confirm_a_keys_v2.json": ("75413549fa9a9127744df1bc4cc92f0e99ee5881e1542726bd5d4f7b09869721",
                               216, 56),
    "confirm_b_grid192.json": ("4e80e69bd2233b994853ae3f60ed0749f2c39c7dbb6390bc012b016efa5cf85b",
                               192, 192),
}
"""Spec v6 6.2 / 6.3 (revision 14): (sha256, lines, J-P3 judged rows) of the sealed key files."""
GRID_ALLOWED_FAILURES = 1
FAULT_PREFIX = "FAULT"
KEY_PRESENCE = {
    "rows": ("job", "controller_tag", "lsb_components", "lsb_settings",
             "hydraulics_record.extend_bound_check.rule_revision",
             "hydraulics_record.extend_bound_check.spec_edition",
             "hydraulic_options.extend_start_tracked", "hydraulic_options.extend_start_hold",
             "hydraulic_options.extend_start_witness", "head_only_declared", "commands_sha256",
             "t4h_file", "events", "event_output", "soil_stop_crawler"),
    "grid_rows": ("event_output.pass", "event_output.gates", "event_output.fault_periods",
                  "event_output.fault_events", "event_output.warnings"),
    "t4h_meta": ("head_only_declared", "events"),
    "t4h_arrays_j_p3_rows": ("rod_pressure_Pa",),
    "t4h_arrays_j7_exempt_record": ("t_s", "phase"),
    "t4h_arrays_12b": ("t_s", "phase", "command_m_s", "motor_stroke_m", "rod_fault_applied",
                       "jp3_t_s", "jp3_r58_witness", "jp3_r59_substeps",
                       "jp3_r510_candidates"),
}
"""Spec v6 6.6 (revision 13, M-10): the names these judges read (rows, T4h meta, T4h arrays;
``jp3_12b_judge_ed6`` reads the 12b arrays through ``jp3_12b_judge``). A missing
``head_only_declared`` falls back to the case table's path; a missing T4h ``phase`` leaves the
J7 exemption record's phase None (a record, never a judgement)."""


class NotJudgeable(Exception):
    """An input defect (exit 2, ``not_judgeable``)."""


# ------------------------------------------------------------------------------- shared
def sealed_lsb_settings() -> dict:
    """``lsb_settings`` of a run with the sealed components and default parameters (6.1)."""
    import verdict_runs

    from outrigger_sim.control.c2 import C2Config

    config = C2Config().with_10hz_d1(lock_start_b_components=tuple(sorted(SEALED_COMPONENTS)))
    meta = verdict_runs.meta_for_json(config.lock_start_b.to_meta())
    return json.loads(json.dumps(meta))


def lsb_identity_problems(row: dict, expected_settings: dict) -> list[str]:
    """6.1 items 5 and the path 1 ``lsb_settings`` identity (revision 13, M-6)."""
    components = row.get("lsb_components")
    problems = []
    if not isinstance(components, list) or len(set(components)) != len(components) or (
            set(components) != SEALED_COMPONENTS):
        problems.append(f"lsb_components {components!r}")
    settings = row.get("lsb_settings")
    if settings is None or json.loads(json.dumps(settings)) != expected_settings:
        problems.append("lsb_settings differ from the sealed defaults")
    return problems


def ed6_identity_problems(row: dict, expected_settings: dict, *, p3_on: bool = True
                          ) -> list[str]:
    """6.1 identity of one edition 6 line: ③ on (items 1 .. 5, the exact tag) or ③ off
    (item 5 only, with the ③-off tag)."""
    if not p3_on:
        problems = lsb_identity_problems(row, expected_settings)
        if row.get("controller_tag") != ED6_P3_OFF_TAG:
            problems.append(f"controller_tag {row.get('controller_tag')!r}")
        return problems
    problems = base.line_identity_problems(row)
    if row.get("controller_tag") != ED6_TAG:
        problems.append(f"controller_tag {row.get('controller_tag')!r} is not {ED6_TAG}")
    return problems + lsb_identity_problems(row, expected_settings)


def metric_rows(rows: list[dict], folders: tuple[Path, ...], setting_map: dict[str, str]
                ) -> list[dict]:
    """436.8 metric rows (settings relabelled by ``setting_map``) with the raw
    ``soil_stop_crawler`` block (reading 3)."""
    import judge_stage1_4368 as path1

    out = []
    for row in rows:
        metric = path1.metrics(row, folders)
        metric["setting"] = setting_map.get(metric["setting"], metric["setting"])
        metric["soil_stop_crawler"] = row.get("soil_stop_crawler")
        out.append(metric)
    return out


def apply_reading_1(table: dict, rows_by: dict, reference: str) -> list[dict]:
    """Reading (1) on a ``_full_items`` table, in place; returns the gate entries it made
    records (each with the item that judges it)."""
    base_rows = {(r["row"], r["phase"]): r for r in rows_by.get(reference, [])}
    moved = []
    for setting, part in table.items():
        for item in part["items"]:
            if item["item"] != "J1" or item["kind"] != "fail" or not item["detail"].startswith(
                    "gate "):
                continue
            ref = base_rows.get((item["row"], item["phase"]))
            gate = item["detail"][len("gate "):]
            if ref is None or not ref.get("gates") or gate not in GATE_ITEMS:
                continue
            item["kind"] = "record"
            item["reading_1"] = list(GATE_ITEMS[gate])
            moved.append({"setting": setting, "row": item["row"], "phase": item["phase"],
                          "gate": gate, "judged_by": list(GATE_ITEMS[gate])})
    return moved


def fail_items(items: list[dict]) -> list[dict]:
    return [item for item in items if item["kind"] == "fail"]


def pair_items(items: list[dict]) -> list[tuple]:
    """Counted failures per (row, phase, item): J1 once per pair (6.2 reading (1))."""
    return sorted({(item["row"], str(item["phase"]), item["item"]) for item in fail_items(items)})


def s8_items(rows_by: dict, settings: tuple[str, ...]) -> dict:
    """``jp3_j9main_judge.s8_items`` reading the raw ``soil_stop_crawler`` with reading (3)."""
    import judge_stage1_4368 as path1

    v0 = {r["phase"]: r for r in rows_by.get(base.V0_SETTING, []) if r["row"] == path1.S8_ROW}
    out = {"f5_records": [], "failures": [], "stops": [], "not_judgeable": [],
           "not_applicable_harness": []}
    for setting in settings:
        for row in rows_by.get(setting, []):
            if row["row"] != path1.S8_ROW:
                continue
            where = {"setting": setting, "row": row["row"], "phase": row["phase"]}
            sa4 = path1.sa4_items(row)
            if sa4["state"] == "fail":
                out["failures"].append({**where, "item": "SA-4", "kind": "fail",
                                        "detail": [k for k, v in sa4["items"].items() if not v]})
            elif sa4["state"] != "pass":
                out["not_judgeable"].append({**where, "item": "SA-4", "kind": "not_judgeable",
                                             "detail": "a SA-4 item without a record"})
            crawler = row.get("soil_stop_crawler") or {}
            margin, after = crawler.get("margin_at_stop_kN"), crawler.get("max_after_stop_kN")
            if margin is None or after is None:
                reference = (v0.get(row["phase"]) or {}).get("soil_stop_crawler") or {}
                if (crawler.get("after_stop_chunks") == 0
                        and reference.get("after_stop_chunks") == 0
                        and reference.get("margin_at_stop_kN") is None):
                    out["not_applicable_harness"].append(
                        {**where, "item": "F-5", "kind": "record",
                         "detail": "no post-stop sample here and in V0 (reading 3)"})
                else:
                    out["not_judgeable"].append({**where, "item": "F-5",
                                                 "kind": "not_judgeable",
                                                 "detail": "criteria 6 stop values None"})
                continue
            if margin < 0:
                out["f5_records"].append({**where, "margin_at_stop_kN": margin})
            if margin < base.F5_STOP_MARGIN_KN or after > base.F5_STOP_MAX_AFTER_KN:
                out["stops"].append({**where, "item": "F-5", "kind": "stop",
                                     "detail": "criteria 6 stop value"})
    return out


def baseline_record(rows_by: dict, counted: set[tuple]) -> dict:
    """``baseline_failures`` with ``counted`` computed and FLAG / record entries apart."""
    listed = base.baseline_failures(rows_by)
    out = {"rule": listed["rule"], "failures": [], "records": []}
    hits = 0
    for table in base.BASELINE_TABLES:
        for entry in listed[table]:
            key = (entry["setting"], entry["row"], str(entry["phase"]), entry["item"])
            entry = {**entry, "table": table, "is_counted": key in counted}
            hits += entry["is_counted"]
            group = "records" if entry["reference_state"] in (base.STATE_FLAG,
                                                               base.STATE_RECORD) else "failures"
            out[group].append(entry)
    out["counted"] = hits
    out["failure_count"] = len(out["failures"])
    out["record_count"] = len(out["records"])
    out["failure_item_units"] = len({(e["row"], str(e["phase"]), e["item"])
                                     for e in out["failures"] if e["table"] == "J_vs_V0"})
    return out


def status_of(basis: dict) -> str:
    if basis["failures"]:
        return "failed"
    if basis["setting_defects"]:
        return "setting_defect"
    if basis["not_judgeable"]:
        return "not_judgeable"
    return "pass"


def jp3_judged_rows(jp3: dict) -> int:
    """Judged rows of the hold revision judgements (``j_p3_judgement_rev5`` ``runs``)."""
    total = 0
    for revision in (5, 6):
        judgement = jp3.get(f"rev{revision}") or {}
        if judgement.get("status") in (None, "no_judged_runs"):
            continue
        total += int(judgement.get("runs_judged") or 0)
    return total


def jp3_basis(jp3: dict, expected_rows: int | None) -> tuple[list[str], list[str], list[str]]:
    """(failures, setting defects, not judgeable) of one J-P3 judgement (``base`` rules plus
    the expected judged row count)."""
    from j_p3_inputs import HOLD_REVISIONS, has_judged_breach

    hold = [jp3.get(f"rev{revision}") or {} for revision in HOLD_REVISIONS]
    revision_statuses = set((jp3.get("status_by_revision") or {}).values())
    own_statuses = {j.get("status") for j in hold}
    failures = ["J-P3 H-7"] if (jp3["status"] == "H-7" or "H-7" in revision_statuses
                                or any(has_judged_breach(j) for j in hold)) else []
    defects, unjudged = [], []
    if jp3["status"] == "setting_defect" or "setting_defect" in (
            own_statuses | revision_statuses) or sum(
            jp3.get(key) or 0 for key in base.JP3_ROW_DEFECT_COUNTS):
        defects.append("J-P3 setting_defect")
    judged = jp3_judged_rows(jp3)
    if judged == 0:
        unjudged.append("J-P3 0 judged rows")
    elif expected_rows is not None and judged != expected_rows:
        defects.append(f"J-P3 judged rows {judged} != {expected_rows}")
    # an empty revision 4 side alone is no reason (``jp3_j9main_judge.status_basis``)
    unjudged += [f"J-P3 {s}" for s in sorted({jp3["status"], *own_statuses} - {None})
                 if s in base.JP3_NOT_JUDGEABLE]
    return failures, defects, unjudged


# ------------------------------------------------------------------------------- j9main
def check_rows(rows: list[dict], expected_jobs: list[dict], settings: tuple[str, ...]) -> None:
    import run_v5

    expected = Counter(run_v5.job_key(job) for job in expected_jobs)
    found = Counter(run_v5.job_key(row["job"]) for row in rows)
    problems = []
    if found != expected:
        problems.append(f"rows are not the expected jobs ({sum((expected - found).values())} "
                        f"missing, {sum((found - expected).values())} extra or repeated)")
    if any("error" in row for row in rows):
        problems.append(f"{sum('error' in row for row in rows)} error lines")
    other = sorted({str(row["job"].get("setting")) for row in rows} - set(settings))
    if other:
        problems.append(f"rows of settings {other}")
    if problems:
        raise NotJudgeable("; ".join(problems))


def judge_j9main(rows_path: Path, v0_path: Path, v0_sha256: str, edition: int) -> dict:
    """``j9main`` (module docstring)."""
    import judge4368_common as common
    import judge_stage1_4368 as path1
    import run_v5
    from j_p3_inputs import j_p3_over_rows

    setting_map = SETTING_MAPS[edition]
    rows = base.read_rows(rows_path)
    jobs = run_v5.ed6_j9_main_jobs() if edition == 6 else run_v5.j9_main_jobs()
    check_rows(rows, jobs, tuple(setting_map))
    v0 = base.stored_v0_rows(v0_path, v0_sha256)
    folders = tuple(common.t4h_folders(rows_path, rows))
    metrics = (metric_rows(rows, folders, setting_map)
               + metric_rows(v0, tuple(common.t4h_folders(v0_path, v0)), {}))
    rows_by = path1._by_setting(metrics)
    vb, ls = path1.JUDGED_SETTING, path1.LS_SETTINGS
    j_vs_v0 = base._full_items(rows_by, (vb,), base.V0_SETTING)
    ls_vs_vb = base._full_items(rows_by, ls, vb)
    moved = apply_reading_1(j_vs_v0, rows_by, base.V0_SETTING)
    moved += apply_reading_1(ls_vs_vb, rows_by, vb)
    vb_items = j_vs_v0[vb]["items"]
    vb_failed_rows = {(i["row"], i["phase"]) for i in fail_items(vb_items)}
    l_a = [dict(i, setting=s) for s, part in ls_vs_vb.items() for i in fail_items(part["items"])
           if i["item"] in base.L_A_ITEMS and (i["row"], i["phase"]) not in vb_failed_rows]
    l_b = [dict(i, setting=s) for s, part in ls_vs_vb.items() for i in fail_items(part["items"])
           if i["item"] in base.L_B_ITEMS]
    l_b_absolute = [{"setting": s, "row": r["row"], "phase": r["phase"], **entry}
                    for s in ls for r in rows_by.get(s, [])
                    for entry in base.own_item_failures(r)
                    if entry["item"] in base.L_B_ITEMS and entry["state"] == base.STATE_FAIL]
    l_c = base.limit_cycle_suspects(rows_by)
    stops = [dict(i, setting=s) for table in (j_vs_v0, ls_vs_vb) for s, part in table.items()
             for i in part["items"] if i["kind"] == "stop"]
    l_e = [i for i in stops if i["setting"] in ls and i["item"] == "J11"]
    s8 = s8_items(rows_by, (vb, *ls))
    stops += s8["stops"]
    r15 = base.r15_worsening(rows_by)
    unjudgeable = [dict(i, setting=s) for table in (j_vs_v0, ls_vs_vb)
                   for s, part in table.items() for i in part["items"]
                   if i["kind"] == "not_judgeable"]
    unjudgeable += s8["not_judgeable"] + l_c["not_judgeable"] + base.r15_not_judgeable(r15)
    no_reference = {f"{name} {s}": part["no_reference"]
                    for name, table in (("J_vs_V0", j_vs_v0), ("LS_vs_VB", ls_vs_vb))
                    for s, part in table.items() if part["no_reference"]}
    jp3 = j_p3_over_rows(base.j_p3_rows(rows, folders), edition5_order=True)
    if edition == 6:
        expected = sealed_lsb_settings()
        identity = [{"job": row["job"], "problems": problems} for row in rows
                    if (problems := ed6_identity_problems(row, expected))]
    else:
        identity = base.identity_defects(rows)
    # the failures the status counts: VB against V0, and LS only through L-a / L-b
    counted = {(vb, i["row"], str(i["phase"]), i["item"]) for i in fail_items(vb_items)}
    counted |= {(i["setting"], i["row"], str(i["phase"]), i["item"]) for i in l_a + l_b}
    report = {"rule": "jp3_remedy_spec_v6.md 6.1 / 6.2 (readings (1) .. (3)), path 1",
              "edition": edition, "setting_map": setting_map, "rows": len(rows),
              "v0_rows": len(v0),
              "inputs": {"rows": {"path": str(rows_path), "sha256": base.file_sha256(rows_path)},
                         "v0": {"path": str(v0_path), "sha256": v0_sha256}},
              "J_vs_V0": j_vs_v0, "LS_vs_VB": ls_vs_vb, "reading_1_moved": moved,
              "vb_fail_items": len(fail_items(vb_items)),
              "vb_fail_pair_items": len(pair_items(vb_items)),
              "vb_fail_by_item": dict(Counter(i["item"] for i in fail_items(vb_items))),
              "identity_defects": identity,
              "baseline_failures": baseline_record(rows_by, counted),
              "r15_worsening": r15, "S8": s8, "L-a": l_a, "L-b": l_b,
              "L-b_absolute": l_b_absolute, "L-c": l_c["suspects"], "L-e": l_e,
              "stops": stops, "not_judgeable_items": unjudgeable, "no_reference": no_reference,
              "J-P3": jp3, "J-P3_judged_rows": jp3_judged_rows(jp3)}
    report["status_basis"] = j9main_basis(report, edition)
    report["status"] = status_of(report["status_basis"])
    return report


def j9main_basis(report: dict, edition: int) -> dict:
    counted = {"VB J1 .. J11 (pair items)": report["vb_fail_pair_items"],
               "R15 worsening (J2)": len(report["r15_worsening"]["failures"]),
               "S8 SA-4": len(report["S8"]["failures"]), "L-a": len(report["L-a"]),
               "L-b (relative)": len(report["L-b"]), "L-c": len(report["L-c"]),
               "stops (J11 H-7 / L-e, criteria 6 F-5)": len(report["stops"])}
    failures = [f"{name}: {count}" for name, count in counted.items() if count]
    jp3_failures, defects, unjudged = jp3_basis(
        report["J-P3"], J9_MAIN_JUDGED_ROWS if edition == 6 else None)
    failures += jp3_failures
    if report["identity_defects"]:
        defects.insert(0, f"identity: {len(report['identity_defects'])} lines")
    not_judgeable = []
    if report["no_reference"]:
        not_judgeable.append(f"no_reference: {sum(map(len, report['no_reference'].values()))}")
    if report["not_judgeable_items"]:
        not_judgeable.append(f"not-judgeable items: {len(report['not_judgeable_items'])}")
    if not report["J_vs_V0"].get("VB", {}).get("runs"):
        not_judgeable.append("0 judged VB rows")
    return {"failures": failures, "setting_defects": defects,
            "not_judgeable": not_judgeable + unjudged}


# ------------------------------------------------------------------------------- keys
def load_key_file(path: Path) -> tuple[dict, tuple[str, int, int]]:
    """A sealed key file and its (sha256, lines, J-P3 rows) (6.2 / 6.3).

    Raises:
        NotJudgeable: Not a sealed name, another sha256, or another line count.
    """
    sealed = SEALED_KEY_FILES.get(Path(path).name)
    data = Path(path).read_bytes()
    if sealed is None or hashlib.sha256(data).hexdigest() != sealed[0]:
        raise NotJudgeable(f"--keys {path} is not a sealed key file")
    document = json.loads(data)
    if len(document["lines"]) != document["expected_lines"] or (
            document["expected_lines"] != sealed[1]
            or document["expected_j_p3_judged_rows"] != sealed[2]):
        raise NotJudgeable(f"--keys {path}: line counts differ from the seal")
    return document, sealed


def matched_lines(document: dict, rows: list[dict]) -> list[tuple[dict, dict]]:
    """(key line, result line) per key line (6.2 / 6.3 line rule).

    Raises:
        NotJudgeable: A key line without exactly one result line, an extra line, an error.
    """
    import run_v5

    by_key: dict[str, list[dict]] = {}
    for row in rows:
        by_key.setdefault(run_v5.job_key(row["job"]), []).append(row)
    pairs, problems = [], []
    wanted = set()
    for line in document["lines"]:
        key = run_v5.job_key(line["job"])
        wanted.add(key)
        found = by_key.get(key) or []
        if len(found) != 1 or "error" in found[0]:
            problems.append(f"{key}: {len(found)} result lines")
            continue
        pairs.append((line, found[0]))
    extra = sum(len(v) for k, v in by_key.items() if k not in wanted)
    if extra:
        problems.append(f"{extra} result lines outside the key file")
    if problems:
        raise NotJudgeable(f"{len(problems)} line problems: {problems[:3]}")
    return pairs


def _first_token(name: str) -> str:
    return name.split(":", 1)[0].split(" at period ", 1)[0]


def apply_j7_exception(table: dict, rows_by: dict, folders: tuple[Path, ...]) -> list[dict]:
    """6.2 J7 stiffness exception (sensitivity settings only, single condition), in place;
    returns the ``j7_stiffness_exempt`` records."""
    records = []
    for setting, part in table.items():
        if setting not in SENSITIVITY_SETTINGS:
            continue
        by_unit: dict[tuple, list[dict]] = {}
        for item in part["items"]:
            if item["item"] == "J7" and item["kind"] == "fail":
                by_unit.setdefault((item["row"], item["phase"]), []).append(item)
        rows = {(r["row"], r["phase"]): r for r in rows_by.get(setting, [])}
        for unit, items in by_unit.items():
            if {_first_token(item["detail"]) for item in items} != {STIFFNESS_WARNING}:
                continue
            for item in items:
                item["kind"] = "record"
                item["j7_exempt"] = True
            records.append(_exempt_record(setting, unit, rows.get(unit) or {}, folders))
    return records


def _exempt_record(setting: str, unit: tuple, row: dict, folders: tuple[Path, ...]) -> dict:
    events = [(t, n) for t, n in row.get("events_full") or []
              if _first_token(n) == STIFFNESS_WARNING]
    phases = _phases_at(row, [t for t, _ in events], folders)
    entries = []
    for (t, name), phase in zip(events, phases, strict=True):
        tail = name.split(":", 1)[1] if ":" in name else None
        try:
            ratio = None if tail is None else float(tail)
        except ValueError:
            ratio = None
        entries.append({"t_s": t, "phase": phase, "raw_ratio": ratio})
    return {"setting": setting, "row": unit[0], "phase": unit[1], "exempt_applied": True,
            "events": entries, "count": len(entries)}


def _phases_at(row: dict, times: list[float], folders: tuple[Path, ...]) -> list[str | None]:
    """The controller phase at each time from the line's T4h (None when not readable)."""
    import judge4368_common as common
    import numpy as np

    located = common.locate_t4h(row, folders) if row else {"status": None}
    if located.get("status") != common.T4H_FOUND or not times:
        return [None] * len(times)
    with np.load(located["path"], allow_pickle=False) as data:
        if "t_s" not in data.files or "phase" not in data.files:
            return [None] * len(times)
        t_s, phase = np.asarray(data["t_s"]), np.asarray(data["phase"]).astype(str)
    out = []
    for t in times:
        index = int(np.searchsorted(t_s, t, side="right")) - 1
        out.append(str(phase[index]) if 0 <= index < phase.size else None)
    return out


def unit_failures(table: dict, s8: dict) -> dict[tuple, list[str]]:
    """Counted failure reasons per (setting, row, phase)."""
    out: dict[tuple, list[str]] = {}
    for setting, part in table.items():
        for item in part["items"]:
            if item["kind"] in ("fail", "stop"):
                out.setdefault((setting, item["row"], str(item["phase"])), []).append(
                    f"{item['item']} {item['kind']}: {item['detail']}")
    for entry in s8["failures"] + s8["stops"]:
        out.setdefault((entry["setting"], entry["row"], str(entry["phase"])), []).append(
            f"{entry['item']} {entry['kind']}")
    return out


def cluster_rule(failing: dict[tuple, list[str]], units: list[tuple]) -> dict:
    """6.2 cluster rule (k = 2) on the units judged (probe-seen units left out)."""
    per_row = Counter((setting, row) for setting, row, _ in units if (setting, row, _) in failing)
    clusters = sorted(f"{s} {r}" for (s, r), n in per_row.items() if n >= 2)
    singles = sum(1 for n in per_row.values() if n == 1)
    return {"cluster_failures": clusters, "single_failures": singles,
            "is_failed": bool(clusters) or singles > CLUSTER_K, "k": CLUSTER_K}


def judge_sens(keys_path: Path, rows_path: Path, v0_path: Path, v0_sha256: str) -> dict:
    """``sens`` (module docstring)."""
    import judge4368_common as common
    import judge_stage1_4368 as path1
    from j_p3_inputs import j_p3_over_rows

    document, sealed = load_key_file(keys_path)
    if Path(keys_path).name == "confirm_b_grid192.json":
        raise NotJudgeable("the grid key file is judged by the grid sub-command")
    rows = base.read_rows(rows_path)
    pairs = matched_lines(document, rows)
    v0 = base.stored_v0_rows(v0_path, v0_sha256)
    folders = tuple(common.t4h_folders(rows_path, rows))
    import run_v5

    own = metric_rows([row for _, row in pairs], folders, {})
    metrics = own + metric_rows(v0, tuple(common.t4h_folders(v0_path, v0)), {})
    rows_by = path1._by_setting(metrics)
    settings = tuple(document["settings"])
    table = base._full_items(rows_by, settings, base.V0_SETTING)
    if any(part["no_reference"] for part in table.values()):
        raise NotJudgeable("a key line without its V0 pair")
    moved = apply_reading_1(table, rows_by, base.V0_SETTING)
    exempt = apply_j7_exception(table, rows_by, folders)
    s8 = s8_items(rows_by, settings)
    failing = unit_failures(table, s8)
    units = {(metric["setting"], metric["row"], str(metric["phase"])): line
             for (line, _), metric in zip(pairs, own, strict=True)}
    if len(units) != len(pairs) or any(run_v5.job_key(line["job"]) != run_v5.job_key(row["job"])
                                       for line, row in pairs):
        raise NotJudgeable("key lines do not map one to one onto (setting, row, phase) units")
    probe_units = [unit for unit, line in units.items() if line.get("probe_seen")]
    judged_units = [unit for unit, line in units.items() if not line.get("probe_seen")]
    failing = {(s, r, p): v for (s, r, p), v in failing.items()}
    probe_stops = sorted(f"{s} {r} {p}" for s, r, p in probe_units if (s, r, p) in failing)
    cluster = cluster_rule(failing, judged_units)
    jp3 = j_p3_over_rows(base.j_p3_rows([row for _, row in pairs], folders),
                         edition5_order=True)
    expected = sealed_lsb_settings()
    identity = [{"job": row["job"], "problems": problems} for _, row in pairs
                if (problems := ed6_identity_problems(row, expected))]
    unjudgeable = [dict(i, setting=s) for s, part in table.items() for i in part["items"]
                   if i["kind"] == "not_judgeable"] + s8["not_judgeable"]
    failures = []
    if probe_stops:
        failures.append(f"probe-seen unit stop: {len(probe_stops)}")
    if cluster["is_failed"]:
        failures.append("cluster rule (k = 2)")
    jp3_failures, defects, unjudged = jp3_basis(jp3, sealed[2])
    failures += jp3_failures
    if identity:
        defects.insert(0, f"identity: {len(identity)} lines")
    not_judgeable = ([f"not-judgeable items: {len(unjudgeable)}"] if unjudgeable else [])
    if not judged_units:
        not_judgeable.append("0 judged units")
    basis = {"failures": failures, "setting_defects": defects,
             "not_judgeable": not_judgeable + unjudged}
    return {"rule": "jp3_remedy_spec_v6.md 6.2 / 6.3 (가), path 1",
            "keys": {"path": str(keys_path), "sha256": sealed[0], "lines": sealed[1]},
            "inputs": {"rows": {"path": str(rows_path), "sha256": base.file_sha256(rows_path)},
                       "v0": {"path": str(v0_path), "sha256": v0_sha256}},
            "units": len(units), "probe_units": len(probe_units),
            "judged_units": len(judged_units), "table": table, "reading_1_moved": moved,
            "j7_stiffness_exempt": exempt, "S8": s8,
            "failing_units": {" ".join(map(str, k)): v for k, v in sorted(failing.items())},
            "probe_unit_stops": probe_stops, "cluster": cluster,
            "identity_defects": identity, "not_judgeable_items": unjudgeable,
            "J-P3": jp3, "J-P3_judged_rows": jp3_judged_rows(jp3),
            "status_basis": basis, "status": status_of(basis)}


# ------------------------------------------------------------------------------- grid
def grid_v0_run(root: Path, pair: dict) -> dict:
    """The stored V0 grid run of a key line (file, key, run index; its command hash checked).

    Raises:
        NotJudgeable: The run is missing or its command hash differs.
    """
    stored = json.loads((root / pair["file"]).read_text(encoding="utf-8"))
    result = next((r for r in stored["results"] if r["key"] == pair["key"]), None)
    if result is None or pair["run_id"] >= len(result["runs"]):
        raise NotJudgeable(f"no stored V0 grid run {pair['key']} #{pair['run_id']}")
    run = result["runs"][pair["run_id"]]
    if run.get("commands_sha256") != pair["v0_commands_sha256"]:
        raise NotJudgeable(f"stored V0 grid run {pair['key']} #{pair['run_id']}: hash differs")
    return run


def fault_reasons(row: dict) -> list[str]:
    """6.3 (나) FAULT 0: fault periods, fault events, the ``fault0`` gate, a FAULT event."""
    event = row.get("event_output") or {}
    reasons = []
    if (event.get("fault_periods") or 0) > 0:
        reasons.append(f"fault_periods {event['fault_periods']}")
    if event.get("fault_events"):
        reasons.append(f"fault_events {len(event['fault_events'])}")
    if (event.get("gates") or {}).get("fault0") is False:
        reasons.append("gate fault0")
    names = sorted({_first_token(n) for _, n in row.get("events") or []
                    if str(n).startswith(FAULT_PREFIX)})
    reasons += [f"event {name}" for name in names]
    return reasons


def judge_grid(keys_path: Path, rows_path: Path, grid_root: Path) -> dict:
    """``grid`` (module docstring)."""
    import judge4368_common as common
    from j_p3_inputs import j_p3_over_rows

    document, sealed = load_key_file(keys_path)
    if Path(keys_path).name != "confirm_b_grid192.json":
        raise NotJudgeable("the grid sub-command takes confirm_b_grid192.json")
    rows = base.read_rows(rows_path)
    pairs = matched_lines(document, rows)
    folders = tuple(common.t4h_folders(rows_path, rows))
    opportunity_failures, faults, warn_records, lines = [], [], [], []
    for line, row in pairs:
        v0_run = grid_v0_run(grid_root, line["v0_pair"])
        event = row.get("event_output")
        if not isinstance(event, dict) or "pass" not in event:
            raise NotJudgeable(f"{line['t4h_file']}: no event_output.pass")
        is_opportunity = bool(line["v0_pair"]["v0_pass"])
        failed = is_opportunity and event["pass"] is not True
        reasons = fault_reasons(row)
        if failed:
            opportunity_failures.append(line["t4h_file"])
        if reasons:
            faults.append({"line": line["t4h_file"], "reasons": reasons})
        warn_new = sorted({_first_token(str(w)) for w in event.get("warnings") or []}
                          - {_first_token(str(w)) for w in v0_run.get("warnings") or []})
        if warn_new:
            warn_records.append({"line": line["t4h_file"], "new_warn_names": warn_new})
        lines.append({"line": line["t4h_file"], "opportunity": is_opportunity,
                      "pass": event["pass"], "v0_pass": v0_run.get("pass")})
    jp3 = j_p3_over_rows(base.j_p3_rows([row for _, row in pairs], folders),
                         edition5_order=True)
    expected = sealed_lsb_settings()
    identity = [{"job": row["job"], "problems": problems} for _, row in pairs
                if (problems := ed6_identity_problems(row, expected))]
    failures = []
    opportunities = sum(line["opportunity"] for line in lines)
    if len(opportunity_failures) > GRID_ALLOWED_FAILURES:
        failures.append(f"opportunity failures {len(opportunity_failures)} > "
                        f"{GRID_ALLOWED_FAILURES}")
    if faults:
        failures.append(f"FAULT lines: {len(faults)}")
    jp3_failures, defects, unjudged = jp3_basis(jp3, sealed[2])
    failures += jp3_failures
    if identity:
        defects.insert(0, f"identity: {len(identity)} lines")
    not_judgeable = [] if opportunities else ["0 opportunity lines"]
    basis = {"failures": failures, "setting_defects": defects,
             "not_judgeable": not_judgeable + unjudged}
    return {"rule": "jp3_remedy_spec_v6.md 6.3 (나), path 1",
            "keys": {"path": str(keys_path), "sha256": sealed[0], "lines": sealed[1]},
            "inputs": {"rows": {"path": str(rows_path), "sha256": base.file_sha256(rows_path)},
                       "grid_root": str(grid_root)},
            "lines": len(lines), "opportunities": opportunities,
            "opportunity_failures": opportunity_failures, "allowed": GRID_ALLOWED_FAILURES,
            "fault_lines": faults, "warn_records": warn_records, "identity_defects": identity,
            "J-P3": jp3, "J-P3_judged_rows": jp3_judged_rows(jp3),
            "status_basis": basis, "status": status_of(basis)}


# ------------------------------------------------------------------------------- step 5
HASH_LENGTH = 64
D0_1_SETTING = "D0-1"
D0_1_LINES = 8
CASE_ROWS = 10


def _require_files(*paths: Path) -> None:
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise NotJudgeable(f"input files missing: {missing}")


def _rows_by_job(rows: list[dict], label: str, problems: list[str]) -> dict[str, dict]:
    import run_v5

    out: dict[str, dict] = {}
    for row in rows:
        key = run_v5.job_key(row["job"])
        if key in out:
            problems.append(f"{label}: job {key} twice")
        if "error" in row:
            problems.append(f"{label}: an error line ({key})")
        out[key] = row
    return out


def judge_hash_match(reference_paths: list[Path], rows_paths: list[Path],
                     setting: str | None = None, expected_lines: int | None = None) -> dict:
    """``hash-match`` (module docstring)."""
    _require_files(*reference_paths, *rows_paths)
    problems: list[str] = []
    reference = [row for path in reference_paths for row in base.read_rows(path)
                 if setting is None or row["job"].get("setting") == setting]
    rows = [row for path in rows_paths for row in base.read_rows(path)]
    reference_by = _rows_by_job(reference, "reference", problems)
    rows_by = _rows_by_job(rows, "rows", problems)
    missing = sorted(set(reference_by) - set(rows_by))
    extra = sorted(set(rows_by) - set(reference_by))
    if missing:
        problems.append(f"{len(missing)} reference jobs without a rerun line")
    if extra:
        problems.append(f"{len(extra)} rerun lines outside the reference")
    if not reference_by:
        problems.append("no reference line")
    if expected_lines is not None and len(reference_by) != expected_lines:
        problems.append(f"{len(reference_by)} reference lines, {expected_lines} expected")
    shared = set(reference_by) & set(rows_by)
    broken = sorted(key for key in shared for row in (reference_by[key], rows_by[key])
                    if not _is_hash(row.get("commands_sha256")))
    if broken:
        problems.append(f"{len(set(broken))} jobs without a 64-character commands_sha256")
    differing = sorted(key for key in shared if key not in broken
                       and rows_by[key]["commands_sha256"]
                       != reference_by[key]["commands_sha256"])
    basis = {"failures": [f"commands_sha256 differs: {len(differing)} jobs"] if differing else [],
             "setting_defects": [], "not_judgeable": problems}
    return {"rule": "jp3_remedy_spec_v6_erratum2.md 2-1 (hash match)",
            "inputs": {"reference": [{"path": str(p), "sha256": base.file_sha256(p)}
                                     for p in reference_paths],
                       "rows": [{"path": str(p), "sha256": base.file_sha256(p)}
                                for p in rows_paths]},
            "setting": setting, "compared": len(set(reference_by) & set(rows_by)),
            "differing_jobs": differing, "status_basis": basis, "status": status_of(basis)}


def _is_hash(value: object) -> bool:
    return isinstance(value, str) and len(value) == HASH_LENGTH


def judge_t8(rows_path: Path, main_jsonl: Path) -> dict:
    """``t8`` (module docstring)."""
    import jp3_t8_rules as t8_rules
    import run_v5

    _require_files(rows_path, main_jsonl)
    rows = base.read_rows(rows_path)
    expected = run_v5.ed6_t8_jobs(main_jsonl)
    problems: list[str] = []
    rows_by = _rows_by_job(rows, "rows", problems)
    wanted = {run_v5.job_key(job) for job in expected}
    if set(rows_by) != wanted:
        problems.append(f"rows are not the ed6_t8 jobs ({len(wanted - set(rows_by))} missing, "
                        f"{len(set(rows_by) - wanted)} extra)")
    pairs, differing, records = 0, [], []
    for job in expected:
        if job["setting"] != "VBL":
            continue
        new = rows_by.get(run_v5.job_key(job))
        old = rows_by.get(run_v5.job_key({**job, "setting": "VBL0"}))
        if new is None or old is None:
            continue
        name = job["case"]
        fallback = [t8_rules.has_fallback_event(line) for line in (new, old)]
        if None in fallback:
            problems.append(f"{name}: a line without event_names / events")
            continue
        if any(fallback):
            records.append(name)
            continue
        if not (_is_hash(new.get("commands_sha256")) and _is_hash(old.get("commands_sha256"))):
            problems.append(f"{name}: a line without a 64-character commands_sha256")
            continue
        pairs += 1
        if new["commands_sha256"] != old["commands_sha256"]:
            differing.append(name)
    if pairs == 0:
        problems.append("no pair without a fallback (not judgeable)")
    basis = {"failures": [f"VBL != VBL0 commands: {len(differing)} pairs"] if differing else [],
             "setting_defects": [], "not_judgeable": problems}
    return {"rule": "jp3_remedy_spec_v6_erratum2.md 2-1 (ii), spec 5 P6-1",
            "inputs": {"rows": {"path": str(rows_path), "sha256": base.file_sha256(rows_path)},
                       "main_jsonl": {"path": str(main_jsonl),
                                      "sha256": base.file_sha256(main_jsonl)}},
            "judged_pairs": pairs, "differing_pairs": differing,
            "fallback_pairs_record": records, "status_basis": basis,
            "status": status_of(basis)}


def judge_cases(rows_path: Path) -> dict:
    """``cases`` (module docstring)."""
    import judge4368_common as common
    import run_v5
    from j_p3_inputs import j_p3_over_rows

    _require_files(rows_path)
    rows = base.read_rows(rows_path)
    problems: list[str] = []
    rows_by = _rows_by_job(rows, "rows", problems)
    wanted = {run_v5.job_key(job) for job in run_v5.ed6_case_jobs()}
    if set(rows_by) != wanted:
        problems.append(f"rows are not the ed6_cases jobs ({len(wanted - set(rows_by))} missing, "
                        f"{len(set(rows_by) - wanted)} extra)")
    folders = tuple(common.t4h_folders(rows_path, rows))
    jp3 = j_p3_over_rows(base.j_p3_rows(rows, folders), edition5_order=True)
    expected = sealed_lsb_settings()
    identity = [{"job": row["job"], "problems": found} for row in rows
                if (found := ed6_identity_problems(row, expected))]
    head_only = [row["job"] for row in rows if row.get("head_only_declared")]
    failures, defects, unjudged = jp3_basis(jp3, CASE_ROWS)
    if identity:
        defects.insert(0, f"identity: {len(identity)} lines")
    if head_only:
        defects.append(f"{len(head_only)} head-only lines (every case row is a judged row)")
    basis = {"failures": failures, "setting_defects": defects,
             "not_judgeable": problems + unjudged}
    return {"rule": "jp3_remedy_spec_v6_erratum2.md 2-1 (iii), spec 5 P6-2",
            "inputs": {"rows": {"path": str(rows_path), "sha256": base.file_sha256(rows_path)}},
            "rows": len(rows), "identity_defects": identity, "J-P3": jp3,
            "J-P3_judged_rows": jp3_judged_rows(jp3),
            "lsb_record": [{"job": row["job"], "lsb_record": row.get("lsb_record")}
                           for row in rows],
            "status_basis": basis, "status": status_of(basis)}


# ------------------------------------------------------------------------------- CLI
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    j9 = sub.add_parser("j9main")
    j9.add_argument("--edition", type=int, choices=(5, 6), required=True)
    sens = sub.add_parser("sens")
    grid = sub.add_parser("grid")
    for command in (j9, sens, grid):
        command.add_argument("--rows", type=Path, required=True)
        command.add_argument("--out", type=Path, required=True)
    for command in (j9, sens):
        command.add_argument("--v0", type=Path, required=True)
        command.add_argument("--v0-sha256", required=True)
    for command in (sens, grid):
        command.add_argument("--keys", type=Path, required=True)
    grid.add_argument("--grid-root", type=Path, required=True,
                      help="the folder the key file's V0 grid paths are relative to (repo root)")
    hashes = sub.add_parser("hash-match")
    d0 = sub.add_parser("d0-1")
    for command in (hashes, d0):
        command.add_argument("--reference", type=Path, action="append", required=True)
        command.add_argument("--rows", type=Path, action="append", required=True)
        command.add_argument("--out", type=Path, required=True)
    hashes.add_argument("--setting", default=None)
    t8 = sub.add_parser("t8")
    t8.add_argument("--rows", type=Path, required=True)
    t8.add_argument("--main-jsonl", type=Path, required=True)
    t8.add_argument("--out", type=Path, required=True)
    cases = sub.add_parser("cases")
    cases.add_argument("--rows", type=Path, required=True)
    cases.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.out.exists():
        print(json.dumps({"status": "not_judgeable", "reason": "--out exists"}))
        return EXIT_STOP
    try:
        if args.command == "j9main":
            report = judge_j9main(args.rows, args.v0, args.v0_sha256, args.edition)
        elif args.command == "hash-match":
            report = judge_hash_match(args.reference, args.rows, args.setting)
        elif args.command == "d0-1":
            report = judge_hash_match(args.reference, args.rows, D0_1_SETTING, D0_1_LINES)
        elif args.command == "t8":
            report = judge_t8(args.rows, args.main_jsonl)
        elif args.command == "cases":
            report = judge_cases(args.rows)
        elif args.command == "sens":
            report = judge_sens(args.keys, args.rows, args.v0, args.v0_sha256)
        else:
            report = judge_grid(args.keys, args.rows, args.grid_root)
    except NotJudgeable as exc:
        report = {"status": "not_judgeable", "reason": str(exc)}
    except Exception as exc:  # noqa: BLE001 (every other failure is a tool error)
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(json.dumps({"status": "error"}))
        return EXIT_ERROR
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, default=str)
    print(json.dumps({"status": report["status"], "out": str(args.out)}))
    return EXIT_OF_STATUS[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
