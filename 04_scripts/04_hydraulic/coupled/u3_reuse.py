"""D-1 run reuse for the U-3 rerun (``u3_u6_rerun_rules.md`` 6, sealed 2026-11-08).

At most 19 U-3 keys of the slope / h9 suites have a D-1 H-S twin (rules 6 table). A key reuses
its D-1 run only if all of:
  Q-1  the D-1 line has the same setting (V0 / VB), phase eps 0 and no error;
  Q-2  the same case: soil, pad B, auger level, floor (roll, pitch) floats, F_s 4 kN, mass x1.0,
       settle hook ``harness`` with a table row, crawler x1.0, the default run length
       (``S9_RUN_LIMIT_S`` unset);
  Q-3  the same code: the D-1 lines carry no commit, so the Q-4 sample is always required;
  Q-4  per family (one table line) the first key runs on the U-3 path and its logged command
       hash equals the D-1 line's ``commands_sha256``; otherwise the whole family runs;
  Q-5  the reused record is the slope-suite record of the D-1 run (``d1.u3``, written by
       ``d1_runs.u3_record``) and is judged by the U-3 judge like any other record; a D-1
       line without that block is not reused.
  Q-6  (rules rev2 1 #6, LAS-b switch) the D-1 line carries the LAS tag of the setting
       (V0 ``final_C4G2_LAS``, VB ``final_C4G2_P3_LAS``): only ``v5/d1_las.jsonl`` lines are
       reused; a line without a tag or with another tag is not. The reused record keeps the
       line's tag.
A reused record carries ``reuse: "d1"`` and ``d1_key``.
"""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path

REUSE_SUITES = ("slope", "h9")
SOILS_FLAT = ("G1", "J1", "J2")
SOILS_SOFT_SLOPE = ("J1", "J2")
FS_KN = 4.0
SETTLE_HOOK = "harness"
RUN_LIMIT_ENV = "S9_RUN_LIMIT_S"


def _table() -> dict[str, tuple[str, str]]:
    """Rules 6 table: v4 key -> (family, D-1 row key)."""
    table: dict[str, tuple[str, str]] = {}
    for soil in SOILS_FLAT:
        table[f"H1|{soil}|B|top|flat"] = ("H-S-0 flat", f"D1|H-S-0|{soil}|T|flat|K1")
        table[f"H2|{soil}|B|bottom|flat"] = ("H-S-0 flat", f"D1|H-S-0|{soil}|B|flat|K1")
    table["H1|S1|B|top|flat"] = ("H-S-1", "D1|H-S-1|S1|T|flat|K1")
    table["H2|S1|B|bottom|flat"] = ("H-S-1", "D1|H-S-1|S1|B|flat|K1")
    for soil in SOILS_SOFT_SLOPE:
        fdown = ("H-S-0 fdown-rec", f"D1|H-S-0|{soil}|T|fdown-rec|K1")
        table[f"H3|{soil}|B|top|nose_down@k0.875"] = fdown
        table[f"H3|{soil}|B|top|edge_nd@k0.875"] = ("H-S-0 diag-rec",
                                                     f"D1|H-S-0|{soil}|T|diag-rec|K1")
        table[f"H3|{soil}|B|top|roll_pos@k0.5"] = ("H-S-0 roll+rec",
                                                   f"D1|H-S-0|{soil}|T|roll+rec|K1")
        table[f"H9|{soil}|B|top|roll_neg@k0.6"] = ("H-S-0 roll-rec",
                                                   f"D1|H-S-0|{soil}|T|roll-rec|K1")
    for soil in SOILS_FLAT:
        table[f"H4|{soil}|B|top|nose_down_2p8"] = ("H-S-0 fdown-rec",
                                                   f"D1|H-S-0|{soil}|T|fdown-rec|K1")
    return table


REUSE_TABLE = _table()
"""19 keys (rules 6: 6 + 2 + 5 + 2 + 2 + 2)."""


@dataclasses.dataclass
class Plan:
    """Reuse candidates of one suite run: key -> D-1 line, the rejected keys and the samples."""

    setting: str
    lines: dict[str, dict]
    family_of: dict[str, str]
    samples: dict[str, str]
    rejected: dict[str, str]

    @property
    def reusable_ids(self) -> set[str]:
        """Candidate keys that are not a family sample (those run on the U-3 path first)."""
        return {key for key in self.lines if key not in self.samples.values()}


@dataclasses.dataclass
class Decision:
    """Q-4 outcome per family and the keys that reuse their D-1 run."""

    plan: Plan
    families: dict[str, dict]
    reused_ids: set[str]

    def report(self) -> dict:
        return {"setting": self.plan.setting, "families": self.families,
                "reused": sorted(self.reused_ids), "rejected": self.plan.rejected,
                "candidates": sorted(self.plan.lines)}


def read_d1_lines(path: Path) -> list[dict]:
    return [json.loads(text) for text in Path(path).read_text(encoding="utf-8").splitlines()
            if text.strip()]


def _d1_line_for(lines: list[dict], row_key: str, setting: str) -> tuple[dict | None, str]:
    """(line, reason): the Q-1 line of the row, or None with the reason."""
    found = [line for line in lines if (line.get("job") or {}).get("d1", {}).get("key") == row_key
             and line["job"].get("setting") == setting]
    if not found:
        return None, f"Q-1: no D-1 {setting} line for {row_key}"
    eps0 = [line for line in found if float(line["job"].get("eps", 0.0)) == 0.0]
    if not eps0:
        return None, f"Q-1: no eps 0 line for {row_key}"
    line = eps0[0]
    if "error" in line:
        return None, f"Q-1: the D-1 line has an error ({line['error'][:80]})"
    if "u3" not in (line.get("d1") or {}):
        return None, "Q-5: the D-1 line has no u3 block (D-1 run before d1_runs.u3_record)"
    return line, _tag_problem(line, setting)


def _tag_problem(line: dict, setting: str) -> str:
    """Rules rev2 1 #6: only a D-1 line with the LAS tag of the setting is reused
    (``v5/d1_las.jsonl``; the pre-switch ``v5/d1.jsonl`` lines carry another tag or none)."""
    import v5_rerun

    tag = line.get("controller_tag")
    expected = v5_rerun.SETTING_TAGS_LAS[setting]
    if tag is None:
        return "Q-6: the D-1 line has no controller_tag (a run before the LAS-b switch)"
    if tag != expected:
        return f"Q-6: D-1 controller_tag {tag!r} != {expected!r} (rules rev2 1 #6)"
    return ""


def q2_problems(payload: dict, row: dict, settle_hook: str) -> list[str]:
    """Rules 6 Q-2 differences of a U-3 case payload from its D-1 row (empty = same case)."""
    problems = []
    checks = (("soil", payload.get("soil"), row.get("base")), ("pad", payload.get("pad"), "B"),
              ("level", payload.get("level"), row.get("level")),
              ("roll_deg", float(payload.get("roll_deg", 0.0)), float(row.get("roll_deg"))),
              ("pitch_deg", float(payload.get("pitch_deg", 0.0)), float(row.get("pitch_deg"))),
              ("fs_kN", float(payload.get("fs_kN", FS_KN)), FS_KN),
              ("mass_scale", float(payload.get("mass_scale", 1.0)), 1.0),
              ("crawler_k_scale", 1.0, float(row.get("crawler_k_scale", 1.0))),
              ("settle_hook", settle_hook, SETTLE_HOOK))
    for name, ours, theirs in checks:
        if ours != theirs:
            problems.append(f"{name} {ours!r} != {theirs!r}")
    if row.get("patch_soil") is not None or row.get("sink") is not None:
        problems.append("D-1 row is not a uniform steady row")
    if payload.get("settle_table_status") in (None, "no_table_row"):
        problems.append(f"settle table status {payload.get('settle_table_status')!r}")
    if os.environ.get(RUN_LIMIT_ENV):
        problems.append(f"{RUN_LIMIT_ENV} set ({os.environ[RUN_LIMIT_ENV]})")
    return problems


def _options_dict(setting: str) -> dict | None:
    import v5_rerun

    _, options = v5_rerun.options_of(setting)
    return None if options is None else options.to_dict()


def plan(d1_path: Path, setting: str, jobs: list[dict], *, settle_hook: str) -> Plan:
    """Q-1 / Q-2 per table key among ``jobs``; the first candidate key of each family is its
    Q-4 sample (it runs on the U-3 path)."""
    lines = read_d1_lines(d1_path)
    found: dict[str, dict] = {}
    family_of: dict[str, str] = {}
    rejected: dict[str, str] = {}
    for job in jobs:
        key = job["id"]
        if job["suite"] not in REUSE_SUITES or key not in REUSE_TABLE:
            continue
        family, row_key = REUSE_TABLE[key]
        line, reason = _d1_line_for(lines, row_key, setting)
        if line is None or reason:
            rejected[key] = reason
            continue
        problems = q2_problems(job["payload"], line["job"]["d1"], settle_hook)
        if line.get("hydraulic_options") != _options_dict(setting):
            problems.append(f"plant options {line.get('hydraulic_options')} differ from the "
                            f"{setting} definition")
        if problems:
            rejected[key] = "Q-2: " + "; ".join(problems)
            continue
        found[key] = line
        family_of[key] = family
    samples: dict[str, str] = {}
    for key, family in family_of.items():
        samples.setdefault(family, key)
    return Plan(setting=setting, lines=found, family_of=family_of, samples=samples,
                rejected=rejected)


def decide(plan_: Plan, sample_records: dict[str, dict]) -> Decision:
    """Q-4: a family reuses its other keys when the sample's logged command hash equals its D-1
    line's ``commands_sha256``."""
    families: dict[str, dict] = {}
    reused: set[str] = set()
    for family, sample in plan_.samples.items():
        record = sample_records.get(sample) or {}
        ours = (record.get("v5") or {}).get("logged_commands_sha256")
        theirs = plan_.lines[sample].get("commands_sha256")
        is_same = "error" not in record and ours is not None and ours == theirs
        members = sorted(key for key, name in plan_.family_of.items() if name == family)
        families[family] = {"sample": sample, "sample_sha256": ours, "d1_sha256": theirs,
                            "same": is_same, "members": members}
        if is_same:
            reused.update(key for key in members if key != sample)
    return Decision(plan=plan_, families=families, reused_ids=reused)


def reused_record(plan_: Plan, job: dict, decision: Decision) -> dict:
    """The U-3 record of a key that reuses its D-1 run (the D-1 ``u3`` block and its v5 keys)."""
    import v5_rerun

    from outrigger_sim.hydraulics.v5_options import is_extend_start_tag

    line = plan_.lines[job["id"]]
    d1 = line["d1"]
    setting = line["job"]["setting"]
    problem = _tag_problem(line, setting)
    if problem:  # plan() rejects such a line; a hand-made plan must not slip one through
        raise ValueError(f"{job['id']}: {problem}")
    v5 = {"v5_setting": setting,
          "controller_tag": line["controller_tag"],
          "definition_sha256": v5_rerun.definition_sha256(setting),
          "code": "D-1 line (no commit recorded; rules 6 Q-3 -> Q-4 sample hash)",
          "head_only_declared": d1.get("head_only_declared"),
          "has_rod_reading": d1.get("has_rod_reading"), "j_p3": d1.get("j_p3"),
          "hydraulic_options": line.get("hydraulic_options"),
          "logged_commands_sha256": line.get("commands_sha256"),
          "commands_sha256": d1["u3"].get("hash"),
          "family_sample": decision.families[plan_.family_of[job["id"]]]["sample"]}
    bound = (line.get("hydraulics_record") or {}).get("extend_bound_check")
    if bound is not None:
        v5["extend_bound_check"] = bound
    if is_extend_start_tag(v5["controller_tag"]):
        # the D-1 worker refused a VB run whose preset rule was not the bound
        # (harness_hydraulics.check_last_extend_start); this code runs revision 4 only
        from outrigger_sim.control.extend_start_bound import EXTEND_START_REVISION

        v5["extend_start"] = {"rule": "tracked_bound", "revision": EXTEND_START_REVISION,
                              "source": "D-1 run check (check_last_extend_start)"}
    return {"suite": job["suite"], "id": job["id"], "candidate": job["candidate"],
            **d1["u3"], "reuse": "d1", "d1_key": d1["key"], "v5": v5, "wall_s": 0.0}
