"""436.9 edition 6 J-P3 judgement of harness batch bundles, path 2 (independent of path 1).

Written by dynamics-expert from the definition sentences of the path-2 handoffs only:
handoff 7 ``jp3_rev6_p2_handoff_ed6.md`` (sha256 ``55c8e92e...``), which takes precedence over
handoff 6 ``jp3_rev6_p2_handoff_ed5.md`` with its errata 1 and 8, and the earlier handoffs that
handoff 7 section 6 carries over (4a-7 with errata 1-3, 4a-8 8, 4a-8 erratum 1 8). No path-1
code, output, judgement file, spec original or design folder is used; the recorded verdict keys
of the run lines are echoed only (``recorded_comparison``).

The per-leg J-P3a / b / c counting (classes, comparison columns, tolerances, NaN rules, code
tables) is the path-2 module ``jp3_rev5_judge_p2`` (own path-2 code, edition 5, unchanged rules
per handoff 7 2.1). What this module adds for edition 6:

* settings (handoff 7 1.1): ③ on = ``VBL``, ``LSL1``..``LSL4``, ``VBLc005``, ``VBLc04``,
  ``VBLv05``, ``VBLv15``, ``VBKL``; ③ off = ``VBL0``, ``VBKL0`` (never J-P3 rows, identity item 5
  only). All of them are P4 on (handoff 7 1.1: plant as VBJ / VBK, P1..P4).
* identity (handoff 7 1.3) on every ③-on line: tag ``final_C4G2_P3W_LAS_K1_LSB`` (base map
  ``final_C4G2_P3W`` -> 6 after removing ``_LSB``, ``_K1``, ``_LAS`` in this order),
  ``rule_revision`` 6, ``spec_edition`` ``fe6f5844``, ``run_extend_start_revision`` (present ->
  6, absent -> ``hydraulic_options`` ``extend_start_tracked`` / ``extend_start_hold`` /
  ``extend_start_witness`` all true, both present and disagreeing -> defect), ``lsb_components``
  as a set equal to {A_i, A_ii, B3} without duplicates. Head-only declared lines without a ③
  record skip items 2 and 3.
* judged rows: ③-on lines that are not head-only declared (T4h meta ``head_only_declared``
  first, 4a-7 erratum 1 3) with grade normal or better; harness lines have no ``level`` and are
  ideal (4a-7 4.3 3). Handoff 6 1.5 (command invariance) is not applied (handoff 7 2.1).
* expected judged-row counts (handoff 7 2.2 - 2.4): j9_main 200, sensitivity rows 104,
  confirmation (a) 56, grid (b) 192; a key list line without a result line = not judgeable.
* bundle status (handoff 7 2.1): fail > setting_defect > other not judgeable > pass; zero
  judged rows is not judgeable.

Breaching reads are reported with their form: judgement (a / b / c), recorded class, plant
state, acting controller phase (T4h ``phase`` row n-1 acts on read n, handoff 6 2.3), the plant
rod pressure ``jp3_p_tr_Pa`` against the judged bound, and the rod reading ``rod_pressure_Pa`` of
the same read against that bound.

Exit codes: 0 pass, 1 fail, 2 not judgeable (incl. setting_defect), 3 tool error.

Usage (dynamics-dev, ``conda run -n dynamics-dev python -I -B``)::

    jp3_ed6_judge_p2.py judge --bundle <name> --records <file.jsonl> [--key-list <json>
        --key-list-sha256 <hex>] --expect-judged-rows N [--expect-settings S ...]
        --out <report.json>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import jp3_rev5_judge_p2 as r5  # noqa: E402  (own path-2 module, same folder)

TOOL_NAME = "jp3_ed6_judge_p2"
TOOL_VERSION = "1"
LEGS = r5.LEGS

ON_SETTINGS = ("VBL", "LSL1", "LSL2", "LSL3", "LSL4", "VBLc005", "VBLc04", "VBLv05", "VBLv15",
               "VBKL")
OFF_SETTINGS = ("VBL0", "VBKL0")
ED6_TAG = "final_C4G2_P3W_LAS_K1_LSB"
TAG_SUFFIXES_STRIP_ORDER = ("_LSB", "_K1", "_LAS")
TAG_BASE_REVISION = {"final_C4G2_P3W": 6}
RULE_REVISION = 6
SPEC_EDITION = "fe6f5844"
LSB_COMPONENTS = frozenset({"A_i", "A_ii", "B3"})
EXTEND_START_OPTIONS = ("extend_start_tracked", "extend_start_hold", "extend_start_witness")
U_HOLD_M_S = 2.09243016e-4
"""Handoff 7 1.4 (0.01 v_max, v_max = 0.0209243016 m/s)."""

NOT_JUDGEABLE_ORDER = ("run_error", "record_defect", "judged_key_missing",
                       "key_list_result_missing", "no_judged_runs")


class ToolError(Exception):
    """Unexpected input (exit 3)."""


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def tag_base(tag: Any) -> str | None:
    """Handoff 7 1.2: remove ``_LSB``, ``_K1``, ``_LAS`` from the end in this order (if
    present); the rest is the tag base."""
    if not isinstance(tag, str):
        return None
    base = tag
    for suffix in TAG_SUFFIXES_STRIP_ORDER:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    return base


def canonical_job(job: Any) -> str:
    return json.dumps(job, sort_keys=True, separators=(",", ":"))


# --------------------------------------------------------------------------------------------
# per line


@dataclass
class LineOutcome:
    index: int
    job: dict
    setting: Any
    role: str  # judged | record | no_rod_reading | reference_off | excluded | stretch_mismatch
    issues: list[tuple[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    declaration: dict | None = None
    evidence: dict | None = None
    identity: dict | None = None
    grade: str | None = None
    t4h: dict | None = None
    legs: dict | None = None
    leg_defects: dict | None = None
    recorded_comparison: dict | None = None
    recorded_judged_row: Any = None
    breach: dict | None = None

    def add(self, kind: str, reason: str) -> None:
        self.issues.append((kind, reason))

    @property
    def kinds(self) -> set[str]:
        return {k for k, _ in self.issues}

    @property
    def label(self) -> str:
        return f"#{self.index} {self.setting} {canonical_job(self.job)}"


def _declaration(raw: dict, trace: r5.Trace | None) -> dict:
    """4a-7 1.1 / erratum 1 3 (handoff 7 2.2: T4h meta ``head_only_declared``)."""
    if raw.get("level") is not None:
        return {"declared": False, "source": "level_line_event_path"}
    if trace is not None and isinstance(trace.meta.get("head_only_declared"), bool):
        d = {"declared": trace.meta["head_only_declared"], "source": "t4h_meta"}
        if isinstance(raw.get("head_only_declared"), bool) \
                and raw["head_only_declared"] != d["declared"]:
            d["line_disagrees"] = raw["head_only_declared"]
        return d
    if isinstance(raw.get("head_only_declared"), bool):
        return {"declared": raw["head_only_declared"], "source": "line"}
    case = (raw.get("job") or {}).get("case")
    if case in r5.STEADY_CASES:
        return {"declared": True, "source": "case_steady"}
    if case in r5.EVENT_CASES:
        return {"declared": False, "source": "case_event"}
    return {"declared": False, "source": "no_declaration_case_not_listed"}


def _identity(raw: dict, ebc: dict | None, trace: r5.Trace | None, out: LineOutcome,
              items: tuple[int, ...]) -> None:
    """Handoff 7 1.3 identity items ``items`` (1..5)."""
    ident: dict[str, Any] = {}
    meta = trace.meta if trace is not None else {}
    if 1 in items:
        tag = raw.get("controller_tag")
        meta_tag = meta.get("controller_tag")
        if tag is None:
            tag = meta_tag
        elif meta_tag is not None and meta_tag != tag:
            out.add("setting_defect", f"line tag {tag!r} != T4h meta tag {meta_tag!r}")
        base = tag_base(tag)
        ident.update(controller_tag=tag, tag_base=base,
                     tag_base_revision=TAG_BASE_REVISION.get(base))
        if tag != ED6_TAG:
            out.add("setting_defect", f"identity 1: tag {tag!r} != {ED6_TAG!r}")
        if TAG_BASE_REVISION.get(base) != RULE_REVISION:
            out.add("setting_defect", f"identity 1: tag base {base!r} is not revision 6")
    if 2 in items:
        value = None if ebc is None else ebc.get("rule_revision")
        ident["rule_revision"] = value
        if value != RULE_REVISION or isinstance(value, bool):
            out.add("setting_defect", f"identity 2: rule_revision {value!r} != 6")
    if 3 in items:
        value = None if ebc is None else ebc.get("spec_edition")
        ident["spec_edition"] = value
        if value != SPEC_EDITION:
            out.add("setting_defect", f"identity 3: spec_edition {value!r} != {SPEC_EDITION!r}")
    if 4 in items:
        present = "run_extend_start_revision" in raw
        value = raw.get("run_extend_start_revision")
        opts = raw.get("hydraulic_options") if isinstance(raw.get("hydraulic_options"),
                                                          dict) else None
        flags = None if opts is None else {k: opts.get(k) for k in EXTEND_START_OPTIONS}
        flags_all_true = flags is not None and all(v is True for v in flags.values())
        ident.update(run_extend_start_revision_present=present,
                     run_extend_start_revision=value, extend_start_options=flags)
        if present and value is not None:
            if value != RULE_REVISION or isinstance(value, bool):
                out.add("setting_defect",
                        f"identity 4: run_extend_start_revision {value!r} != 6")
            elif flags is not None and not flags_all_true:
                out.add("setting_defect", "identity 4: run_extend_start_revision 6 but "
                        f"hydraulic_options {flags} not all true")
        else:
            if present:  # key present with null value: read as absent (recorded)
                out.notes.append("run_extend_start_revision present with null value: read "
                                 "as absent (hydraulic_options decide)")
            if not flags_all_true:
                out.add("setting_defect", "identity 4: run_extend_start_revision absent and "
                        f"hydraulic_options {flags} not all true")
    if 5 in items:
        comps = raw.get("lsb_components")
        meta_comps = meta.get("lsb_components")
        ident["lsb_components"] = comps
        if comps is None and meta_comps is not None:
            comps = meta_comps
        elif meta_comps is not None and comps is not None \
                and sorted(map(str, meta_comps)) != sorted(map(str, comps)):
            out.add("setting_defect", f"lsb_components line {comps!r} != T4h meta {meta_comps!r}")
        ok = isinstance(comps, list) and all(isinstance(c, str) for c in comps) \
            and len(comps) == len(set(comps)) and set(comps) == LSB_COMPONENTS
        if not ok:
            out.add("setting_defect", f"identity 5: lsb_components {comps!r} != set "
                    f"{sorted(LSB_COMPONENTS)}")
    for key in ("carry_end_rule", "retract_start_rule"):  # record only (handoff 7 1.3)
        if ebc is not None:
            ident[key] = ebc.get(key)
    out.identity = ident


def _grade(raw: dict, ebc: dict | None, out: LineOutcome) -> str | None:
    """4a-7 4.3: ``sensor_grade`` -> ``level`` -> harness line without level = ideal."""
    grade = ebc.get("sensor_grade") if ebc else None
    level = raw.get("level")
    level_grade = r5.R79_LEVEL_GRADE.get(str(level)) if level is not None else None
    if grade is not None and grade not in r5.JUDGED_GRADES + r5.RECORD_GRADES:
        out.add("setting_defect", f"unknown sensor_grade {grade!r}")
        return None
    if level is not None and level_grade is None:
        out.add("setting_defect", f"unknown level {level!r}")
        return None
    if grade is not None and level_grade is not None and grade != level_grade:
        out.add("setting_defect", f"sensor_grade {grade!r} != level {level!r}")
        return None
    if grade is not None:
        return grade
    if level_grade is not None:
        return level_grade
    if isinstance(raw.get("job"), dict):
        return "ideal"
    out.add("setting_defect", "no sensor_grade, no level and not a job line")
    return None


def judge_line(index: int, raw: dict, t4h_dir: Path) -> LineOutcome:
    job = raw.get("job") if isinstance(raw.get("job"), dict) else None
    if job is None:
        raise ToolError(f"line {index}: not a harness batch line (no job object)")
    setting = job.get("setting")
    if setting in ON_SETTINGS:
        out = LineOutcome(index, job, setting, "judged")
    elif setting in OFF_SETTINGS:
        out = LineOutcome(index, job, setting, "reference_off")
    else:
        out = LineOutcome(index, job, setting, "excluded")
        out.add("setting_defect", f"setting {setting!r} outside the edition-6 settings")
        return out
    if raw.get("error") is not None:
        if r5.is_stretch_mismatch(raw["error"]):
            out.role = "stretch_mismatch"
            out.notes.append(f"stretch_mismatch error line: {str(raw['error'])[:200]}")
        else:
            out.add("run_error", f"error line: {str(raw['error'])[:200]}")
        return out

    hyd = raw.get("hydraulics_record") if isinstance(raw.get("hydraulics_record"), dict) else {}
    ebc_raw = hyd.get("extend_bound_check")
    if "extend_bound_check" in raw and raw.get("extend_bound_check") != ebc_raw:
        out.add("record_defect", "top-level extend_bound_check != hydraulics_record one")
    ebc = ebc_raw if isinstance(ebc_raw, dict) else None

    trace: r5.Trace | None = None
    name = raw.get("t4h_file")
    path = None if name is None else t4h_dir / Path(str(name)).name
    if path is not None and path.is_file():
        trace = r5.load_trace(path)
        out.t4h = {"file": path.name, "sha256": trace.sha256,
                   "reads": None if trace.t_s is None else int(trace.t_s.size)}
        meta_job = trace.meta.get("job")
        if meta_job is not None and canonical_job(meta_job) != canonical_job(job):
            out.add("setting_defect", f"T4h meta job {meta_job!r} != line job")
    elif path is not None:
        out.t4h = {"file": path.name, "missing": True}

    out.declaration = _declaration(raw, trace)
    if "line_disagrees" in out.declaration:
        out.add("setting_defect", "line head_only_declared disagrees with T4h meta")
    declared = out.declaration["declared"]

    # P4 evidence (4a-8 8.1 / erratum 1 8; harness lines have no r79 key: k = 1)
    calls, reads = hyd.get(r5.TRUTH_CALLS_KEY), hyd.get(r5.ROD_READS_KEY)
    out.evidence = {r5.TRUTH_CALLS_KEY: calls, r5.ROD_READS_KEY: reads, "k": 1}
    if not (r5._is_count(calls) and r5._is_count(reads)):
        out.add("setting_defect", f"P4 evidence keys missing or not integers ({calls!r}, "
                f"{reads!r})")
    elif declared:
        if calls != 0 or reads != 0:
            out.add("setting_defect", f"head-only declared line needs (1) = (2) = 0 "
                    f"({calls}, {reads})")
    elif not (calls == reads and reads > 0):
        out.add("setting_defect", f"event-path P4 line needs (1) = 1 x (2) > 0 "
                f"({calls}, {reads})")

    if setting in OFF_SETTINGS:
        _identity(raw, ebc, trace, out, (5,))
        if ebc is not None:
            out.add("setting_defect", "③-off line with a ③ record")
        return out

    if declared:
        out.role = "no_rod_reading"
        if ebc is not None:
            out.add("setting_defect", "head-only declared line with a ③ record")
            _identity(raw, ebc, trace, out, (1, 2, 3, 4, 5))
        else:
            _identity(raw, ebc, trace, out, (1, 4, 5))
        return out

    _identity(raw, ebc, trace, out, (1, 2, 3, 4, 5))
    if ebc is None:
        out.add("setting_defect", "event-path ③-on line without a ③ record")
        return out
    out.grade = _grade(raw, ebc, out)
    out.recorded_judged_row = ebc.get("jp3_judged_row")
    if out.grade in r5.RECORD_GRADES:
        out.role = "record"
        out.notes.append(f"grade {out.grade}: J-P3 recorded only")
    if "setting_defect" in out.kinds:
        return out

    missing = [f"extend_bound_check.{jk}" for jk in r5.JUDGED_KEYS
               if not (isinstance(ebc.get(jk), list) and len(ebc[jk]) == len(LEGS))]
    if name is None:
        missing.append("t4h_file")
    if out.t4h is not None and out.t4h.get("missing"):
        out.add("record_defect", f"T4h file not found: {out.t4h['file']}")
        return out
    if trace is None:
        out.add("judged_key_missing", ", ".join(missing) or "no T4h")
        return out
    missing += [f"npz:{m}" for m in trace.missing]
    if missing:
        out.add("judged_key_missing", ", ".join(missing))
        return out
    problems = trace.shape_problems + r5.table_problems(trace.tables)
    for problem in problems:
        out.add("record_defect", problem)
    if problems:
        return out
    rec = r5._decode(trace.columns["jp3_class"], r5.CLASS_NAMES)
    state = r5._decode(trace.columns["jp3_plant_state"], r5.PLANT_STATE_NAMES)
    out.legs, out.leg_defects = {}, {}
    for i, leg in enumerate(LEGS):
        res = r5.judge_leg(i, trace.t_s, rec[:, i], state[:, i], trace.columns)
        out.legs[leg] = {k: v for k, v in res.counts.items() if k != "jp3a_by_plant_state"}
        out.leg_defects[leg] = res.defects
        for defect, n in res.defects.items():
            if n:
                out.add("record_defect", f"{leg} {defect} = {n}")
    out.recorded_comparison = r5.recorded_comparison(ebc, out.legs)
    if sum(out.legs[leg][jk] for leg in LEGS for jk in r5.JUDGED_KEYS) > 0:
        out.breach = breach_form(path, rec, state, out.legs)
    return out


# --------------------------------------------------------------------------------------------
# breach form


def breach_form(path: Path, rec: np.ndarray, state: np.ndarray, legs: dict) -> dict:
    """Per breaching read: judgement, class, plant state, acting phase, plant rod pressure vs
    bound, rod reading vs bound (bar). Masks re-derived with the same rules as ``judge_leg``
    and checked against its counts."""
    with np.load(path, allow_pickle=False) as z:
        jt = np.asarray(z["jp3_t_s"], dtype=float)
        t = np.asarray(z["t_s"], dtype=float) if "t_s" in z.files else None
        phase = np.asarray(z["phase"]).astype(str) if "phase" in z.files else None
        rod = np.asarray(z["rod_pressure_Pa"], dtype=float) if "rod_pressure_Pa" in z.files \
            else None
        head = np.asarray(z["head_pressure_Pa"], dtype=float) if "head_pressure_Pa" in z.files \
            else None
        cols = {k: np.asarray(z[k]) for k in z.files if k.startswith("jp3_")}
        lsb = {k: np.asarray(z[k]) for k in ("lsb_a1_on", "lsb_a2_on", "lsb_protected",
                                             "lsb_b1_blocked") if k in z.files}
    src_names = tuple(str(v) for v in np.asarray(cols.get("jp3_source_names", [])).ravel())
    # index of each jp3 read in the T4h read grid
    idx = None
    if t is not None:
        k = np.searchsorted(t, jt)
        k = np.clip(k, 0, t.size - 1)
        k0 = np.clip(k - 1, 0, t.size - 1)
        k = np.where(np.abs(t[k0] - jt) < np.abs(t[k] - jt), k0, k)
        if np.all(np.abs(t[k] - jt) <= 1e-9):
            idx = k
    reads, by_form = [], {}
    count_check = {}
    for i, leg in enumerate(LEGS):
        p_tr = cols["jp3_p_tr_Pa"][:, i].astype(float)
        ext = cols["jp3_ext_bound_Pa"][:, i].astype(float)
        model = cols["jp3_model_bound_Pa"][:, i].astype(float)
        used = cols["jp3_used_bound_Pa"][:, i].astype(float)
        star = cols["jp3_p_star_ret_Pa"][:, i].astype(float)
        c, s = rec[:, i], state[:, i]
        with np.errstate(invalid="ignore"):
            in_a = np.isin(c.astype(str), ("ext", "carry_ext")) & np.isfinite(p_tr) \
                & np.isfinite(ext)
            m_a = in_a & (p_tr - ext > r5.BREACH_TOL_PA)
            in_b = (c.astype(str) == "hold") & np.isfinite(p_tr) & np.isfinite(model)
            m_b = in_b & (p_tr - model > r5.hold_tolerance_Pa(i))
            locked = np.isin(s.astype(str), r5.LOCKED_STATES)
            moving = np.isin(s.astype(str), r5.MOVING_STATES)
            c_ok = (c.astype(str) == "carry_ret") & np.isfinite(p_tr) & np.isfinite(used) \
                & np.isfinite(ext) & (locked | moving)
            trapped = c_ok & (locked | (p_tr > star) | ~np.isfinite(star))
            m_c = trapped & (p_tr - used > r5.BREACH_TOL_PA)
        count_check[leg] = {"a": [int(m_a.sum()), legs[leg]["jp3a_breach_reads"]],
                            "b": [int(m_b.sum()), legs[leg]["jp3b_breach_over_tol_reads"]],
                            "c": [int(m_c.sum()), legs[leg]["jp3c_breach_reads"]]}
        for judgement, mask, bound in (("J-P3a", m_a, ext), ("J-P3b", m_b, model),
                                       ("J-P3c", m_c, used)):
            for n in np.flatnonzero(mask):
                j = None if idx is None else int(idx[n])
                acting = None if (phase is None or j is None or j < 1) else str(phase[j - 1])
                row_phase = None if (phase is None or j is None) else str(phase[j])
                rod_read = None if (rod is None or j is None) else float(rod[j, i])
                src = cols.get("jp3_model_bound_source")
                src_name = None
                if src is not None:
                    code = int(src[n, i])
                    src_name = src_names[code] if 0 <= code < len(src_names) else code
                same_dir = ("carry_ext", "ext") if judgement == "J-P3a" else \
                    ("carry_ret", "ret") if judgement == "J-P3c" else ("hold",)
                k = n
                while k > 0 and str(c[k - 1]) in same_dir:
                    k -= 1
                item = {
                    "leg": leg, "judgement": judgement, "t_s": float(jt[n]), "jp3_read": int(n),
                    "class": str(c[n]), "plant_state": str(s[n]),
                    "plant_state_prev_read": None if n == 0 else str(s[n - 1]),
                    "read_index_in_class_run": int(n - k),
                    "class_before_run": None if k == 0 else str(c[k - 1]),
                    "plant_state_before_run": None if k == 0 else str(s[k - 1]),
                    "acting_phase": acting, "phase_row_n": row_phase,
                    "p_tr_bar": float(p_tr[n]) / 1e5, "bound_bar": float(bound[n]) / 1e5,
                    "excess_bar": float(p_tr[n] - bound[n]) / 1e5,
                    "allowance_bar": (r5.hold_tolerance_Pa(i) if judgement == "J-P3b"
                                      else r5.BREACH_TOL_PA) / 1e5,
                    "rod_reading_bar": None if rod_read is None else rod_read / 1e5,
                    "rod_reading_minus_bound_bar": (None if rod_read is None
                                                    else (rod_read - float(bound[n])) / 1e5),
                    "head_reading_bar": (None if (head is None or j is None)
                                         else float(head[j, i]) / 1e5),
                    "used_bound_bar": float(used[n]) / 1e5,
                    "ext_bound_bar": float(ext[n]) / 1e5,
                    "model_bound_bar": float(model[n]) / 1e5,
                    "p_star_ret_bar": float(star[n]) / 1e5,
                    "u_m_s": float(cols["jp3_u_m_s"][n, i]),
                    "gate_open": (bool(cols["jp3_gate_open"][n, i])
                                  if "jp3_gate_open" in cols else None),
                    "model_bound_source": src_name,
                    "r58_witness": (bool(cols["jp3_r58_witness"][n, i])
                                    if "jp3_r58_witness" in cols else None),
                    "r59_substeps": (int(cols["jp3_r59_substeps"][n, i])
                                     if "jp3_r59_substeps" in cols else None),
                    "r510_candidates": (int(cols["jp3_r510_candidates"][n, i])
                                        if "jp3_r510_candidates" in cols else None),
                    "lsb": {k: (bool(v[j, i]) if j is not None else None)
                            for k, v in lsb.items()},
                }
                reads.append(item)
                rod_above = None if rod_read is None else (rod_read > float(bound[n]))
                fk = (f"{judgement}|{item['class']}|{item['plant_state']}"
                      f"(prev {item['plant_state_prev_read']})|phase {acting}|"
                      f"run after {item['class_before_run']}/{item['plant_state_before_run']}|"
                      f"rod_reading_above_bound={rod_above}")
                by_form[fk] = by_form.get(fk, 0) + 1
    reads.sort(key=lambda r: (r["t_s"], r["leg"]))
    return {"reads": reads, "by_form": by_form, "count_check": count_check,
            "t4h_index_aligned": idx is not None}


# --------------------------------------------------------------------------------------------
# bundle


def read_lines(path: Path) -> list[dict]:
    if not path.is_file():
        raise ToolError(f"records file not found: {path}")
    out = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ToolError(f"{path}:{number}: broken JSON ({exc})") from exc
        if not isinstance(raw, dict):
            raise ToolError(f"{path}:{number}: not an object")
        out.append(raw)
    return out


def judge_bundle(bundle: str, records: Path, key_list: Path | None, key_list_sha: str | None,
                 expect_judged: int, expect_settings: list[str] | None) -> dict:
    t4h_dir = records.parent / f"{records.stem}_t4h"
    raws = read_lines(records)
    bundle_issues: list[tuple[str, str]] = []
    outcomes = [judge_line(i, raw, t4h_dir) for i, raw in enumerate(raws, start=1)]

    test_rows = [o.label for o in outcomes if r5.is_test_setting(o.setting)]
    if test_rows:
        bundle_issues.append(("setting_defect", f"test settings in the input: {test_rows[:10]}"))
    settings_seen: dict[str, int] = {}
    for o in outcomes:
        settings_seen[str(o.setting)] = settings_seen.get(str(o.setting), 0) + 1
    if expect_settings is not None:
        extra = sorted(set(settings_seen) - set(expect_settings))
        if extra:
            bundle_issues.append(("setting_defect", f"settings outside the bundle: {extra}"))

    # key list (handoff 7 2.3 / 2.4)
    key_info = None
    by_job: dict[str, list[LineOutcome]] = {}
    for o in outcomes:
        by_job.setdefault(canonical_job(o.job), []).append(o)
    duplicates = [j for j, v in by_job.items() if len(v) > 1]
    if duplicates:
        bundle_issues.append(("setting_defect", f"duplicate job lines: {duplicates[:5]}"))
    if key_list is not None:
        doc = json.loads(key_list.read_text(encoding="utf-8"))
        sha = sha256_of(key_list)
        lines = doc.get("lines")
        if not isinstance(lines, list):
            raise ToolError(f"{key_list}: no lines")
        missing, decl_mismatch, t4h_mismatch, matched = [], [], [], set()
        for kl in lines:
            cj = canonical_job(kl.get("job"))
            found = by_job.get(cj, [])
            if not found:
                missing.append(cj)
                continue
            matched.add(cj)
            o = found[0]
            if o.declaration is not None and isinstance(kl.get("head_only_declared"), bool) \
                    and kl["head_only_declared"] != o.declaration["declared"]:
                decl_mismatch.append(cj)
            if "t4h_file" in kl and (o.t4h or {}).get("file") != kl["t4h_file"]:
                t4h_mismatch.append(cj)
        not_in_list = sorted(set(by_job) - matched)
        kl_judged = sum(1 for kl in lines if kl.get("head_only_declared") is False)
        key_info = {
            "path": key_list.name, "sha256": sha, "sha256_expected": key_list_sha,
            "lines": len(lines), "expected_lines": doc.get("expected_lines"),
            "expected_j_p3_judged_rows": doc.get("expected_j_p3_judged_rows"),
            "head_only_declared_lines": doc.get("head_only_declared_lines"),
            "lines_not_declared_in_list": kl_judged,
            "settings": doc.get("settings"),
            "missing_results": missing, "result_lines_not_in_list": not_in_list,
            "declaration_mismatch": decl_mismatch, "t4h_file_mismatch": t4h_mismatch}
        if key_list_sha is not None and sha != key_list_sha:
            bundle_issues.append(("setting_defect", f"key list sha256 {sha} != {key_list_sha}"))
        if doc.get("expected_j_p3_judged_rows") != expect_judged:
            bundle_issues.append(("setting_defect", "key list expected_j_p3_judged_rows "
                                  f"{doc.get('expected_j_p3_judged_rows')} != handoff "
                                  f"{expect_judged}"))
        if missing:
            bundle_issues.append(("key_list_result_missing",
                                  f"{len(missing)} key list lines without a result"))
        if not_in_list:
            bundle_issues.append(("setting_defect",
                                  f"{len(not_in_list)} result lines not in the key list"))
        if decl_mismatch:
            bundle_issues.append(("setting_defect",
                                  f"{len(decl_mismatch)} lines: declaration != key list"))
        if t4h_mismatch:
            bundle_issues.append(("setting_defect",
                                  f"{len(t4h_mismatch)} lines: t4h_file != key list"))

    judged = [o for o in outcomes if o.role == "judged"]
    clean = [o for o in judged if not o.issues]
    if len(judged) != expect_judged:
        if judged:
            bundle_issues.append(("setting_defect", f"judged rows {len(judged)} != expected "
                                  f"{expect_judged}"))
    if not judged:
        bundle_issues.append(("no_judged_runs", "no judged row"))

    line_issues = []
    for o in outcomes:
        for kind, reason in o.issues:
            if kind == "setting_defect" or o.role == "judged":
                line_issues.append((kind, f"{o.label}: {reason}"))
            # issues on non-judged lines other than setting_defect are notes only
    all_issues = bundle_issues + line_issues
    kinds = {k for k, _ in all_issues}

    totals = {jk: sum(o.legs[leg][jk] for o in clean for leg in LEGS) for jk in r5.JUDGED_KEYS}
    breach_rows = [o for o in clean if sum(o.legs[leg][jk] for leg in LEGS
                                           for jk in r5.JUDGED_KEYS) > 0]
    unclean_breach = [o.label for o in judged if o.issues and o.legs and sum(
        o.legs[leg][jk] for leg in LEGS for jk in r5.JUDGED_KEYS) > 0]
    stretch = [o.label for o in outcomes if o.role == "stretch_mismatch"]
    breach = sum(totals.values())
    if stretch:
        status = "stretch_mismatch"
    elif breach > 0:
        status = "fail"
    elif "setting_defect" in kinds:
        status = "setting_defect"
    elif kinds:
        status = next(k for k in NOT_JUDGEABLE_ORDER if k in kinds)
    else:
        status = "pass"
    exit_code = {"pass": 0, "fail": 1, "stretch_mismatch": 1}.get(status, 2)
    status_class = ("fail" if status in ("fail", "stretch_mismatch") else
                    "pass" if status == "pass" else
                    "defect" if status == "setting_defect" else "not_judgeable")

    # breakdowns
    def bucket(key_fn):
        d: dict[str, dict] = {}
        for o in outcomes:
            k = key_fn(o)
            e = d.setdefault(k, {"lines": 0, "judged": 0, "clean": 0, "no_rod_reading": 0,
                                 "breach_rows": 0,
                                 "breach_reads": {jk: 0 for jk in r5.JUDGED_KEYS}})
            e["lines"] += 1
            e["judged"] += o.role == "judged"
            e["no_rod_reading"] += o.role == "no_rod_reading"
            if o.role == "judged" and not o.issues:
                e["clean"] += 1
                n = 0
                for jk in r5.JUDGED_KEYS:
                    v = sum(o.legs[leg][jk] for leg in LEGS)
                    e["breach_reads"][jk] += v
                    n += v
                e["breach_rows"] += n > 0
        return d

    by_setting = bucket(lambda o: str(o.setting))
    by_case = bucket(lambda o: str(o.job.get("case")))
    flags = {fk: sum(o.legs[leg][fk] for o in clean for leg in LEGS)
             for fk in ("jp3a_reads", "jp3b_reads", "jp3c_reads", "jp3b_breach_reads",
                        "jp3b_tol_near_reads", "jp3a_margin_used_reads", "jp3c_fill_reads",
                        "jp3c_fill_breach_reads", "jp3a_used_ne_ext_reads",
                        "jp3b_used_ne_model_reads", "class_boundary_reads",
                        "lock_ext_breach_over_tol_reads", "lock_ret_breach_reads",
                        "ret_breach_reads")}
    form_totals: dict[str, int] = {}
    for o in breach_rows:
        for fk, n in o.breach["by_form"].items():
            form_totals[fk] = form_totals.get(fk, 0) + n
    recorded_diff = []
    for o in clean:
        for key, cmp_ in (o.recorded_comparison or {}).items():
            if not cmp_["equal"]:
                recorded_diff.append({"line": o.label, "key": key, "recorded": cmp_["recorded"],
                                      "path2": cmp_["path2"]})
    judged_row_diff = [{"line": o.label, "recorded_jp3_judged_row": o.recorded_judged_row,
                        "path2_role": o.role} for o in outcomes
                       if o.recorded_judged_row is not None
                       and bool(o.recorded_judged_row) != (o.role == "judged")]
    identity_values: dict[str, int] = {}
    for o in outcomes:
        if o.identity:
            k = json.dumps({kk: vv for kk, vv in o.identity.items()}, sort_keys=True)
            identity_values[k] = identity_values.get(k, 0) + 1
    declaration_sources: dict[str, int] = {}
    for o in outcomes:
        s = str((o.declaration or {}).get("source"))
        declaration_sources[s] = declaration_sources.get(s, 0) + 1
    grades: dict[str, int] = {}
    for o in judged:
        grades[str(o.grade)] = grades.get(str(o.grade), 0) + 1

    return {
        "tool": TOOL_NAME, "tool_version": TOOL_VERSION, "path": 2, "bundle": bundle,
        "rules": ["jp3_rev6_p2_handoff_ed6.md (handoff 7, sha256 55c8e92e...) 1.1-1.4, 2.1-2.4",
                  "jp3_rev6_p2_handoff_ed5.md 3 + errata 1, 8 (carried over)",
                  "4a-7 1 / 4 + errata 1-3, 4a-8 8, 4a-8 erratum 1 8 (carried over)"],
        "constants": {"u_hold_m_s": U_HOLD_M_S, "u_hold_used_by_class_table_m_s": r5.U_HOLD_M_S,
                      "breach_tol_Pa": r5.BREACH_TOL_PA,
                      "hold_tol_bar": [r5.hold_tolerance_Pa(i) / 1e5 for i in range(4)],
                      "tag": ED6_TAG, "rule_revision": RULE_REVISION,
                      "spec_edition": SPEC_EDITION, "lsb_components": sorted(LSB_COMPONENTS)},
        "input": {"records": records.name, "sha256": sha256_of(records), "lines": len(raws),
                  "t4h_dir": t4h_dir.name,
                  "t4h_files": len(list(t4h_dir.glob("*.npz"))) if t4h_dir.is_dir() else 0},
        "key_list": key_info,
        "status": status, "status_class": status_class, "exit_code": exit_code,
        "expect_judged_rows": expect_judged, "judged_rows": len(judged),
        "clean_judged_rows": len(clean),
        "no_rod_reading_lines": sum(o.role == "no_rod_reading" for o in outcomes),
        "record_lines": sum(o.role == "record" for o in outcomes),
        "reference_off_lines": sum(o.role == "reference_off" for o in outcomes),
        "settings_seen": settings_seen, "grades_of_judged": grades,
        "issues": [{"kind": k, "where": w} for k, w in all_issues],
        "issue_counts": {k: sum(1 for kk, _ in all_issues if kk == k) for k in sorted(kinds)},
        "identity_defect_lines": sum(any(r.startswith("identity") for _, r in o.issues)
                                     for o in outcomes),
        "totals": totals, "breach_sum": breach,
        "breach_rows": [{"line": o.label, "per_leg": {jk: [o.legs[leg][jk] for leg in LEGS]
                                                      for jk in r5.JUDGED_KEYS},
                         "count_check": o.breach["count_check"],
                         "t4h_index_aligned": o.breach["t4h_index_aligned"],
                         "by_form": o.breach["by_form"], "reads": o.breach["reads"]}
                        for o in breach_rows],
        "breach_form_totals": form_totals,
        "breach_on_rows_with_issues": unclean_breach,
        "stretch_mismatch_rows": stretch,
        "flags": flags, "by_setting": by_setting, "by_case": by_case,
        "declaration_sources": declaration_sources,
        "identity_values": identity_values,
        "recorded_vs_path2_differences": recorded_diff,
        "judged_row_differences": judged_row_diff,
        "lines": [{"line": o.label, "role": o.role, "issues": o.issues, "notes": o.notes,
                   "declaration": o.declaration, "evidence": o.evidence, "grade": o.grade,
                   "t4h": o.t4h,
                   "breach": None if not o.legs else {jk: [o.legs[leg][jk] for leg in LEGS]
                                                      for jk in r5.JUDGED_KEYS}}
                  for o in outcomes],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("judge")
    p.add_argument("--bundle", required=True)
    p.add_argument("--records", type=Path, required=True)
    p.add_argument("--key-list", type=Path)
    p.add_argument("--key-list-sha256")
    p.add_argument("--expect-judged-rows", type=int, required=True)
    p.add_argument("--expect-settings", nargs="*")
    p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.out.exists():
            raise ToolError(f"report exists, not overwritten: {args.out}")
        report = judge_bundle(args.bundle, args.records.resolve(),
                              None if args.key_list is None else args.key_list.resolve(),
                              args.key_list_sha256, args.expect_judged_rows,
                              args.expect_settings)
    except (ToolError, r5.ToolError) as exc:
        print(f"[{TOOL_NAME}] tool error: {exc}", file=sys.stderr)
        print("status=tool_error exit=3")
        return 3
    except Exception:
        import traceback

        traceback.print_exc()
        print("status=tool_error exit=3")
        return 3
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, default=_json_default), encoding="utf-8")
    t = report["totals"]
    print(f"bundle={args.bundle} status={report['status']} exit={report['exit_code']} "
          f"judged={report['judged_rows']}/{report['expect_judged_rows']} "
          f"clean={report['clean_judged_rows']} breach_rows={len(report['breach_rows'])} "
          f"jp3a={t['jp3a_breach_reads']} jp3b={t['jp3b_breach_over_tol_reads']} "
          f"jp3c={t['jp3c_breach_reads']} issues={report['issue_counts']}")
    return report["exit_code"]


def _json_default(o: Any) -> Any:
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not math.isfinite(float(o)) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


if __name__ == "__main__":
    sys.exit(main())
