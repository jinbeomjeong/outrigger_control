"""436.9 edition 4a J4a-9: the re-implementation's case replays against the clean ``221456d``
baseline (``jp3_remedy_spec.md`` 5.7 P4-1 .. P4-4, P4-9, 13.1; addendum 4a-1 section 1).

Checks, in order (any failure stops with "not judgeable" or the failed prediction):

1. Baseline: the sha256 of ``SHA256SUMS`` is :data:`BASELINE_SUMS_SHA256`; every listed file
   has its hash; the script opens no baseline file outside the list (CRLF lines: ``\\r`` cut).
2. Pairs: every baseline row (``j9_cases.jsonl``, ``cd.jsonl``) has exactly one new row of the
   same job; the new revision 5 rows carry the sealed identity (13.6), test-only settings are
   refused.
3. P4-1: ``commands_sha256`` equal per pair (T8).
4. Per read (T4h npz): ``jp3_t_s`` of equal length and value; P4-2 used bound new >= baseline
   (1 Pa); a raised read must be an R5-7 read (source ``retract_tracker``) or follow one on its
   leg (seed / carry); a class change only CARRY instead of EXT / RET of the same direction.
5. Judged rows (``jp3_judged_row``) > 0; per class reads > 0 (lock, hold, carry_ext,
   carry_ret, ext) over the revision 5 rows (the A rows and VBG4 have no ``class_reads``).
6. P4-3a: J-P3a / b / c judged keys 0 and ``relock_step_over_1bar_count`` 0 on VBJ, LSJ1 .. 4.
7. P4-4: ``p1_retract_seed_count`` and the largest seed step equal to the baseline; one
   ``p1_retract_seed_log`` row per seed, each read net force step <= 1 N.
8. P4-9: ``retract_tracker_dominated_reads`` 0 and an empty stretch log (no fallback leg);
   ``jp3_model_bound_source`` present on every revision 5 T4h.

Usage (python-dev or dynamics-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_baseline_compare.py <baseline folder>
      --new <jsonl> [<jsonl> ...] --out <report.json>

Exit 0 all checks pass, 1 a prediction failed, 2 not judgeable (baseline or pairing), 3 error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

BASELINE_SUMS_SHA256 = "197ac14e96822130ba4eee98486be6ba9646c207ed1a27936c275077b3a60361"
"""Edition 4a 13.1 / addendum 4a-1: the sealed baseline list."""
SPEC_EDITION = "8be9de22"
BASELINE_ROW_FILES = ("j9_cases.jsonl", "cd.jsonl")
JUDGED_SETTINGS = ("VBJ", "LSJ1", "LSJ2", "LSJ3", "LSJ4")
JUDGED_KEYS = ("jp3a_breach_reads", "jp3b_breach_over_tol_reads", "jp3c_breach_reads")
CLASS_NAMES = ("lock", "hold", "carry_ext", "carry_ret", "ext", "ret")
REQUIRED_CLASSES = ("lock", "hold", "carry_ext", "carry_ret", "ext")
RETRACT_TRACKER_CODE = 4
"""``jp3_source_names`` index of ``retract_tracker`` (appended last, J4a-4)."""
BOUND_TOLERANCE_PA = 1.0
NET_FORCE_TOLERANCE_N = 1.0
TEST_ONLY_SETTINGS = ("VBG4", "VBG5")
EXIT_PASS, EXIT_FAILED, EXIT_NOT_JUDGEABLE, EXIT_ERROR = 0, 1, 2, 3


class NotJudgeable(Exception):
    """Baseline or pairing broken (13.1: stop)."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Baseline:
    """The sealed folder: only files of ``SHA256SUMS`` are opened, each hash checked."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        sums = folder / "SHA256SUMS"
        if _sha256(sums) != BASELINE_SUMS_SHA256:
            raise NotJudgeable(f"{sums}: sha256 is not {BASELINE_SUMS_SHA256[:12]}")
        self.hashes: dict[str, str] = {}
        for line in sums.read_bytes().decode("utf-8").split("\n"):
            line = line.rstrip("\r")  # committed -text: CRLF lines (addendum 4a-1)
            if not line:
                continue
            digest, name = line.split(maxsplit=1)
            self.hashes[name.lstrip("*")] = digest
        for name, digest in self.hashes.items():
            if _sha256(folder / name) != digest:
                raise NotJudgeable(f"baseline {name}: hash differs from SHA256SUMS")

    def path(self, name: str) -> Path:
        """A listed file; anything else is refused (addendum 4a-1)."""
        name = name.replace("\\", "/")
        if name not in self.hashes:
            raise NotJudgeable(f"baseline file {name} is not in SHA256SUMS")
        return self.folder / name

    def rows(self, name: str) -> list[dict]:
        return _read_rows(self.path(name))

    def t4h(self, row_file: str, record: dict) -> Path:
        stem = Path(row_file).stem
        return self.path(f"{stem}_t4h/{Path(record['t4h_file']).name}")


def _read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _job_key(record: dict) -> str:
    return json.dumps(record["job"], sort_keys=True)


def _check(record: dict) -> dict:
    return (record.get("hydraulics_record") or {}).get("extend_bound_check") or {}


def _is_revision_5(record: dict) -> bool:
    return _check(record).get("rule_revision") == 5


def pair_rows(baseline: Baseline, new_rows: list[dict]) -> list[tuple[str, dict, dict]]:
    """(baseline row file, baseline record, new record) per baseline row."""
    new_by_key: dict[str, list[dict]] = {}
    for record in new_rows:
        setting = record["job"]["setting"]
        if setting.endswith("_X11"):
            raise NotJudgeable(f"test-only setting {setting} in the compared set (13.6)")
        new_by_key.setdefault(_job_key(record), []).append(record)
    pairs = []
    for row_file in BASELINE_ROW_FILES:
        for old in baseline.rows(row_file):
            matches = new_by_key.get(_job_key(old), [])
            if len(matches) != 1:
                raise NotJudgeable(f"{old['job']['setting']}: {len(matches)} new rows")
            pairs.append((row_file, old, matches[0]))
    return pairs


def check_identity(record: dict) -> list[str]:
    """13.6: a new revision 5 row of the sealed edition with the default rules."""
    if record["job"]["setting"] in TEST_ONLY_SETTINGS or not _is_revision_5(record):
        return []
    check = _check(record)
    wanted = {"spec_edition": SPEC_EDITION, "carry_end_rule": "inherit_when_gate_shut",
              "retract_start_rule": "with_tracker"}
    return [f"{record['job']['setting']}: {key} {check.get(key)!r}"
            for key, value in wanted.items() if check.get(key) != value]


def compare_reads(old_npz: Path, new_npz: Path) -> dict:
    """Step 4 for one pair; raises :class:`NotJudgeable` on a different read time base."""
    with np.load(old_npz, allow_pickle=False) as old, np.load(new_npz, allow_pickle=False) as new:
        if "jp3_t_s" not in old:
            return {"has_trace": False}
        if "jp3_model_bound_source" not in new:
            raise NotJudgeable(f"{new_npz.name}: no jp3_model_bound_source (P4-9)")
        t_old, t_new = old["jp3_t_s"], new["jp3_t_s"]
        if t_old.shape != t_new.shape or not np.array_equal(t_old, t_new):
            raise NotJudgeable(f"{new_npz.name}: jp3_t_s differs from the baseline")
        used_old, used_new = old["jp3_used_bound_Pa"], new["jp3_used_bound_Pa"]
        class_old, class_new = old["jp3_class"], new["jp3_class"]
        source = new["jp3_model_bound_source"]
        u_new = new["jp3_u_m_s"]
    with np.errstate(invalid="ignore"):
        lowered = used_new < used_old - BOUND_TOLERANCE_PA
        raised = used_new > used_old + BOUND_TOLERANCE_PA
    nan_changed = np.isnan(used_old) != np.isnan(used_new)
    unexplained = _unexplained_raises(raised, class_new, source)
    bad_class = _bad_class_changes(class_old, class_new, u_new)
    return {"has_trace": True, "reads": int(t_new.size),
            "lowered_reads": int(lowered.sum()), "nan_changed_reads": int(nan_changed.sum()),
            "raised_reads": int(raised.sum()),
            "raised_retract_tracker_reads": int((raised & (source == RETRACT_TRACKER_CODE)).sum()),
            "unexplained_raised_reads": unexplained, "bad_class_changes": bad_class,
            "class_changes": int((class_old != class_new).sum())}


def _unexplained_raises(raised: np.ndarray, classes: np.ndarray, source: np.ndarray) -> int:
    """P4-2: a raised read is an R5-7 read, or a later read of the same leg reached from one
    (seed / carry / moving) without an unrelated lock or hold read in between."""
    lock_codes = {CLASS_NAMES.index("lock"), CLASS_NAMES.index("hold")}
    count = 0
    for leg in range(raised.shape[1]):
        follows_tracker = False
        for read in range(raised.shape[0]):
            is_tracker = source[read, leg] == RETRACT_TRACKER_CODE
            is_lock = int(classes[read, leg]) in lock_codes
            if is_lock:
                follows_tracker = is_tracker
            if raised[read, leg] and not (is_tracker or follows_tracker):
                count += 1
    return count


def _bad_class_changes(old: np.ndarray, new: np.ndarray, u_new: np.ndarray) -> int:
    """P4-2: allowed changes are EXT -> CARRY_ext and RET -> CARRY_ret (a later gate)."""
    allowed = {(CLASS_NAMES.index("ext"), CLASS_NAMES.index("carry_ext")),
               (CLASS_NAMES.index("ret"), CLASS_NAMES.index("carry_ret"))}
    changed = np.argwhere(old != new)
    return sum((int(old[r, c]), int(new[r, c])) not in allowed for r, c in changed)


def seed_checks(old: dict, new: dict) -> list[str]:
    """P4-4 on one judged pair."""
    old_h, new_h = old["hydraulics_record"], new["hydraulics_record"]
    problems = []
    for key in ("p1_retract_seed_count", "p1_retract_seed_step_max_bar"):
        if old_h.get(key) != new_h.get(key):
            problems.append(f"{key} {new_h.get(key)} != baseline {old_h.get(key)}")
    rows = new_h.get("p1_retract_seed_log") or []
    columns = new_h.get("p1_retract_seed_log_columns") or []
    if len(rows) != new_h.get("p1_retract_seed_count"):
        problems.append(f"p1_retract_seed_log rows {len(rows)} != count")
    if rows:
        index = columns.index("net_force_step_N")
        worst = max(abs(row[index]) for row in rows)
        if worst > NET_FORCE_TOLERANCE_N:
            problems.append(f"seed net force step {worst:.3f} N > 1 N")
    return problems


def compare(baseline: Baseline, new_rows: list[dict]) -> dict:
    pairs = pair_rows(baseline, new_rows)
    report: dict = {"pairs": [], "failures": []}
    class_totals = dict.fromkeys(CLASS_NAMES, 0)
    judged_rows = 0
    for row_file, old, new in pairs:
        setting = new["job"]["setting"]
        failures = check_identity(new)
        if old["commands_sha256"] != new["commands_sha256"]:
            failures.append("P4-1 commands_sha256 differs")
        reads = compare_reads(baseline.t4h(row_file, old), Path(new["t4h_file"]))
        if reads.get("lowered_reads") or reads.get("nan_changed_reads"):
            failures.append("P4-2 a read's used bound below the baseline")
        if reads.get("unexplained_raised_reads") or reads.get("bad_class_changes"):
            failures.append("P4-2 an unexplained raise or class change")
        check = _check(new)
        if _is_revision_5(new):
            judged_rows += int(bool(check.get("jp3_judged_row")))
            for name in CLASS_NAMES:
                class_totals[name] += int(sum((check.get("class_reads") or {}).get(name, [])))
            if sum(check.get("retract_tracker_dominated_reads") or [0]) or check.get(
                    "retract_tracker_stretch_log"):
                failures.append("P4-9 retract_tracker records on a run without fallback legs")
        if setting in JUDGED_SETTINGS:
            failures += [f"P4-3a {key} {check.get(key)}" for key in JUDGED_KEYS
                         if sum(check.get(key) or [0])]
            if new["hydraulics_record"].get("relock_step_over_1bar_count"):
                failures.append("P4-3a relock step over 1 bar")
            failures += [f"P4-4 {problem}" for problem in seed_checks(old, new)]
        report["pairs"].append({"setting": setting, "row_file": row_file,
                                "commands_sha256": new["commands_sha256"][:12],
                                "reads": reads, "failures": failures})
        report["failures"] += [f"{setting}: {failure}" for failure in failures]
    if judged_rows == 0:
        raise NotJudgeable("no judged row (13.1)")
    missing = [name for name in REQUIRED_CLASSES if class_totals[name] == 0]
    if missing:
        raise NotJudgeable(f"no reads of class {missing} over the revision 5 rows (13.1)")
    report.update(judged_rows=judged_rows, class_reads=class_totals)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("baseline", type=Path)
    parser.add_argument("--new", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        baseline = Baseline(args.baseline)
        new_rows = [row for path in args.new for row in _read_rows(path)]
        report = compare(baseline, new_rows)
        status = "pass" if not report["failures"] else "failed"
        code = EXIT_PASS if status == "pass" else EXIT_FAILED
    except NotJudgeable as exc:
        report, status, code = {"reason": str(exc)}, "not_judgeable", EXIT_NOT_JUDGEABLE
    except (OSError, KeyError, ValueError) as exc:
        report, status, code = {"reason": f"{type(exc).__name__}: {exc}"}, "error", EXIT_ERROR
    report["status"] = status
    report["baseline_sums_sha256"] = BASELINE_SUMS_SHA256
    args.out.write_text(json.dumps(report, indent=1, default=float), encoding="utf-8")
    print(json.dumps({"status": status, "failures": len(report.get("failures", [])),
                      "reason": report.get("reason")}))
    return code


if __name__ == "__main__":
    sys.exit(main())
