"""LAS-b revision A targets on the reduced harness: P5r4 / P5r6 (beta 4.5 + end ramp N_r 4 / 6).

Rules: ``06_analysis/02_control/verif_matrix/las_revA_targeted_rules.md`` (control-expert,
sealed; LF sha256 ``las_revA_judge.RULES_REVA_SHA256``) on top of ``las_rev_targeted_rules.md``
and its rev1 (all three checked, H-1). The rules text wins where this code differs. The run
machinery (candidate wrapper, DONE record, pool, pair jobs) is ``las_rev_targeted``'s.

Candidates (rules 1.2, ``las`` = ``C2Config.with_10hz_d1().liftoff_approach_slow``, b0):
  P0    the preset as it is (no override at all)
  P5    ``replace(las, light_leg_fraction_of_F_min=4.5, min_active_periods=0,
        end_ramp_periods=0)`` (N_r 0 given explicitly, rules 7.2)
  P5r4  the same with ``end_ramp_periods=4``;  P5r6  with ``end_ramp_periods=6``
Applied in the worker by ``las_rev_targeted.install_candidate`` (``dataclasses.replace`` on a
b0 config only; ``las_targeted.install`` is never installed); every line records the settings
the run's controller used (K-A8). The preset itself is not touched.

Bundles (rules 3), output ``06_analysis/03_hydraulic/coupled/v5/las/revA/revA_R<bundle>
[_<candidates>].jsonl`` (opened with ``"x"``, no resume):
  R-0    6 P0 bit tests (``las_rev_judge.R0_EXPECTED``, rules 7.1).
  R-0P5  P5 on the 30 R-G points; hash and ``F_RL_kN`` = the reference P5 line (rules 7.2).
  R-G    (ga) 30 points x P5r4, P5r6 = 60; label ``<candidate>-LT-c<centre>-j<j>``.
  R-H    (ga) half-step points j 0.5 .. 3.5 (24) x P5, P5r4, P5r6 = 72; label
         ``<candidate>-LH-c<centre>-j<j with p>`` (``touch_budget.j`` a float).
  R-T    (na) T-1 8 + T-2 184 keys x the candidates given (those that passed (ga)).
  R-S    (da) F-3 16 + F-4 14 jobs x the candidates given.
  R-P0   P0 on the union of the keys whose hash changed in the revA R-T / R-S files.
  R-X    P0 with the DONE record on the keys of the C-4 exception claims, or --keys.
Gates before a run (exit 2): H-1 seals; H-10 the reference ``rev_RG.jsonl`` (``--ref-rg``,
raw sha256 7e8c3b41..) for R-0P5, R-G, R-T, R-S; H-2 R-0 passed before R-0P5, and R-0 and R-0P5
passed with the current tool sha256 before R-G and later; R-T / R-S / R-P0 / R-X need every
earlier revA R-G / R-H / R-T / R-S / R-P0 line from the current commit and tool sha256, and
R-T / R-S need each given candidate's 30 R-G + 24 R-H lines with the (ga) status ``pass``
(audit item (ga)); R-T / R-S job dicts must equal the stored L lines' (H-4).

During a batch (``las_revA_judge`` checks on each finished line): H-2 an R-0 / R-0P5 mismatch
-> stop everything; H-3 a K-A mismatch -> no more jobs of that candidate (R-H lines are checked
when their P5 pair line is in); H-4 a missing field -> stop; H-5 an R-P0 / R-X hash that is not
L's -> stop; H-7 an error line -> the job once more (R-0P5 / R-G / R-H: stop, re-run the bundle
as a whole); H-8 five pairs with a C-2 type violation -> no more of that candidate's jobs; a run
identity change or a ``controller_tag`` that is not the setting's -> stop.
Line = the ``run_v5`` line + ``las`` (``las_rev_targeted.las_block`` + ``params.n_r`` + ``ramp``
{n_r, start_factor, periods_applied, scaled_periods, end_t_s, end_reason}) + ``rev`` {bundle,
candidate, label, key, grid_point, identity, rules_sha256, rules_rev1_sha256,
rules_revA_sha256, settings, expected_settings, settings_match, controller_tag, record flags}
(+ ``diag`` for grid lines, ``periods[].las`` with ramp_m / ramp_factor / ramp_scaled, + the
DONE record ``done_trace`` / ``done_clock``).

Usage (dynamics-dev python.exe, project root, PowerShell):
  python -I -B 04_scripts/04_hydraulic/coupled/las_revA_targeted.py list [--bundle R-0 ..]
      [--candidates P5r4,P5r6] [--ref-rg <rev_RG.jsonl>]
  python -I -B 04_scripts/04_hydraulic/coupled/las_revA_targeted.py run --bundle R-0P5
      [--ref-rg <rev_RG.jsonl>] [--candidates ..] [--workers 4] [--affinity HEX] [--out <jsonl>]
      [--keys K1,K2] [--from <jsonl> ..] [--limit N] [--no-done-record]
Exit codes: 0 done, 1 a stop condition or run errors (run) / a count or reference mismatch
(list), 2 input error (seals, reference, gates, dirty code, existing --out, job dicts).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import traceback
from dataclasses import asdict, dataclass, replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import las_rev_targeted as rev  # noqa: E402  (imports fb_targeted: thread variables first)
import las_revA_judge as judge  # noqa: E402

rj = judge.rj
fb = rev.fb
ROOT = fb.ROOT
REVA_DIR = judge.REVA_DIR
IDENTITY_FILES = {**rev.IDENTITY_FILES,
                  "las_revA_targeted.py": HERE / "las_revA_targeted.py",
                  "las_revA_judge.py": HERE / "las_revA_judge.py"}
"""Rules 4: c2.py, the revA tool and judge, the rev tool and judge, las_phase_diag,
fb_targeted, las_targeted."""

BUNDLES = judge.BUNDLES
BUNDLE_CANDIDATES = {"R-0": ("P0",), "R-0P5": ("P5",), "R-G": judge.JUDGED_CANDIDATES,
                     "R-H": judge.HALF_CANDIDATES, "R-T": None, "R-S": None, "R-P0": ("P0",),
                     "R-X": ("P0",)}
"""None: the candidates must be given (those that passed (ga), rules 3 order)."""
BUNDLE_COUNTS = {"R-0": 6, "R-0P5": judge.GRID_LINES, "R-G": 2 * judge.GRID_LINES,
                 "R-H": 3 * judge.HALF_LINES}
REFERENCE_BUNDLES = ("R-0P5", "R-G", "R-T", "R-S")
"""H-10: the bundles that read the reference P5 lines (R-T / R-S through the (ga) gate)."""
WHOLE_BUNDLE_RERUN = judge.GRID_BUNDLES
EARLIER_BUNDLE_FILES = ("revA_RG*.jsonl", "revA_RH*.jsonl", "revA_RT*.jsonl", "revA_RS*.jsonl",
                        "revA_RP0*.jsonl")


# ------------------------------------------------------------------------------- candidates
@dataclass(frozen=True)
class RevACandidate:
    """One candidate of rules 1.2 (``beta``, ``n_min``, ``N_r`` over the b0 preset)."""

    name: str
    beta: float
    n_min: int
    n_r: int

    def settings_from(self, preset_settings):
        """The candidate's ``LiftoffApproachSlowSettings`` (P0: the preset unchanged)."""
        if self.name == "P0":
            return preset_settings
        return replace(preset_settings, light_leg_fraction_of_F_min=self.beta,
                       min_active_periods=self.n_min, end_ramp_periods=self.n_r)


CANDIDATES = {name: RevACandidate(name, *values)
              for name, values in judge.CANDIDATE_VALUES.items()}


# ------------------------------------------------------------------------------- jobs
def half_step_text(j: int | float) -> str:
    """``1.5`` -> ``1p5`` (rules 3.2 label)."""
    return str(j).replace(".", "p")


def grid_label(candidate: str, centre: str, j: int | float, is_half: bool) -> str:
    kind = "LH" if is_half else "LT"
    return f"{candidate}-{kind}-c{centre}-j{half_step_text(j)}"


def grid_jobs(bundle: str, candidates) -> tuple[list[dict], list[dict]]:
    """R-0P5 / R-G (j 0..4) and R-H (j 0.5 .. 3.5): the two grid keys (VB first) x
    candidates x centre x j."""
    import las_targeted

    is_half = bundle == "R-H"
    steps = judge.HALF_STEPS if is_half else judge.GRID_STEPS
    base = sorted(las_targeted.jobs_for_keys(list(rev.GRID_KEYS)),
                  key=lambda job: job["setting"] != "VB")
    jobs, entries = [], []
    for job in base:
        for centre in judge.GRID_CENTRES:
            for j in steps:
                for candidate in candidates:
                    jobs.append(job)
                    entries.append(rev._entry(bundle, candidate,
                                              grid_label(candidate, centre, j, is_half),
                                              (centre, j), record_diag=True))
    return jobs, entries


def bundle_jobs(bundle: str, candidates, mask: int | None = None, keys=None,
                record_done: bool = True) -> list[dict]:
    """The jobs of a bundle with their ``rev`` entries (``keys`` filters R-T / R-S and is
    required for R-P0 / R-X)."""
    if bundle == "R-0":
        base, entries = rev.r0_jobs()
    elif bundle in judge.GRID_BUNDLES:
        base, entries = grid_jobs(bundle, candidates)
    elif bundle in ("R-T", "R-S"):
        all_base = rev.t_base_jobs() if bundle == "R-T" else rev.s_base_jobs()
        if keys is not None:
            all_base = [job for job in all_base if fb.fb_key(job) in set(keys)]
        base, entries = rev.pair_jobs(bundle, all_base, candidates)
    elif bundle in ("R-P0", "R-X"):
        if keys is None:
            raise ValueError(f"{bundle} needs keys (--keys or --from)")
        by_key = rev._jobs_by_key(rev.t_base_jobs() + rev.s_base_jobs())
        missing = [key for key in keys if key not in by_key]
        if missing:
            raise KeyError(f"{bundle}: keys outside R-T / R-S: {missing[:5]}")
        base, entries = rev.pair_jobs(bundle, [by_key[key] for key in keys], ("P0",))
    else:
        raise ValueError(f"unknown bundle {bundle!r}")
    jobs = []
    for index, (job, entry) in enumerate(zip(base, entries, strict=True)):
        entry = {**entry, "id": index, "record_done": record_done}
        jobs.append(rev._with_entry(job, entry, mask))
    return jobs


# ------------------------------------------------------------------------------- worker
def run_identity() -> dict:
    """``fb_targeted.run_identity`` with this tool's files and the three rules sha256."""
    return {**fb.run_identity(files=IDENTITY_FILES), "rules_sha256": rj.RULES_SHA256,
            "rules_rev1_sha256": rj.RULES_REV1_SHA256,
            "rules_revA_sha256": judge.RULES_REVA_SHA256}


_RUN: dict = {}
"""The worker's run values (one run per worker)."""


def _install_all(entry: dict) -> None:
    import las_phase_diag

    fb._install_candidate(fb.CANDIDATES["L"])  # threads, preset LAS-b b0, run capture
    # Read before the run: the harness later patches with_10hz_d1 (and keeps its last result).
    _RUN["preset_settings"] = rev.preset_las_settings()
    grid_point = None if entry["grid_point"] is None else tuple(entry["grid_point"])
    if entry["record_diag"] or grid_point is not None:
        las_phase_diag.install(entry["record_diag"], grid_point)
    candidate = CANDIDATES[entry["candidate"]]
    if candidate.name != "P0":
        rev.install_candidate(candidate, preset_settings=_RUN["preset_settings"])
    if entry["record_done"]:
        rev.install_done_recorder()


def no_ramp(n_r: int) -> dict:
    """``las.ramp`` of a run whose LAS-b never started (the meta has no ``ramp``)."""
    return {"n_r": n_r, "start_factor": None, "periods_applied": 0, "scaled_periods": 0,
            "end_t_s": None, "end_reason": None}


def las_block(controller, harness: dict | None, candidate: str) -> dict:
    """``las_rev_targeted.las_block`` + ``params.n_r`` + ``ramp`` (rules 4)."""
    block = rev.las_block(controller, harness, candidate)
    meta = controller.meta()["liftoff_approach_slow"]
    n_r = meta["settings"]["end_ramp_periods"]
    return {**block, "params": {**block["params"], "n_r": n_r},
            "ramp": meta.get("ramp") or no_ramp(n_r)}


def rev_block(entry: dict, job: dict, controller, line: dict, identity: dict) -> dict:
    settings = asdict(controller.config.liftoff_approach_slow)
    preset = _RUN.get("preset_settings") or rev.preset_las_settings()
    expected = asdict(CANDIDATES[entry["candidate"]].settings_from(preset))
    return {**{name: entry[name] for name in ("bundle", "candidate", "label", "grid_point",
                                              "record_diag", "record_done")},
            "key": fb.fb_key(job), "identity": identity, "rules_sha256": rj.RULES_SHA256,
            "rules_rev1_sha256": rj.RULES_REV1_SHA256,
            "rules_revA_sha256": judge.RULES_REVA_SHA256,
            "settings": settings, "expected_settings": expected,
            "settings_match": settings == expected,
            "controller_tag": line.get("controller_tag")}


def _add_blocks(line: dict, entry: dict, job: dict, identity: dict) -> None:
    import las_phase_diag

    plant, controller = fb._run_objects(job)
    if plant is None or controller is None:
        raise RuntimeError(f"run objects not captured (plant {plant is not None}, "
                           f"controller {controller is not None})")
    line["las"] = las_block(controller, fb._CAPTURE.get("harness"), entry["candidate"])
    line["rev"] = rev_block(entry, job, controller, line, identity)
    if entry["record_diag"]:
        diag_entry = {"bundle": entry["bundle"], "label": entry["label"], "record": True}
        line["diag"] = {"key": fb.fb_key(job),
                        **las_phase_diag.diag_block(diag_entry, line, line["las"], controller,
                                                    plant, identity)}
    if entry["record_done"]:
        line["done_trace"], line["done_clock"] = rev.done_blocks(controller)


def run_revA_job(job: dict) -> dict:
    """Worker: install the candidate (+ TOUCH budget / recorders), run, add the blocks."""
    t_start = time.perf_counter()
    entry = job.pop("rev")
    head = {"job": job, "rev": {**entry, "key": fb.fb_key(job)}}
    try:
        import run_v5  # sys.path and thread variables first

        identity = run_identity()
        _install_all(entry)
    except Exception as exc:  # recorded as an error line; the batch decides (H-7)
        return {**head, "error": f"install: {exc!r}", "tb": traceback.format_exc()[-3000:],
                "wall_s": round(time.perf_counter() - t_start, 1)}
    line = run_v5.run_one(job)
    if "error" in line:
        return {**line, "rev": head["rev"]}
    try:
        _add_blocks(line, entry, job, identity)
    except Exception as exc:
        return {**head, "error": f"metrics: {exc!r}", "tb": traceback.format_exc()[-3000:],
                "wall_s": round(time.perf_counter() - t_start, 1)}
    line["rev"]["id"] = entry["id"]
    return line


# ------------------------------------------------------------------------------- batch checks
def r0p5_problems(record: dict, reference: dict) -> list[str]:
    """Rules 7.2 on one R-0P5 line (H-2)."""
    point = judge.grid_point_of(record)
    ref = reference.get(point)
    if ref is None:
        return [f"H-2 R-0P5 {point} has no reference line"]
    problems = []
    if record["commands_sha256"] != ref["commands_sha256"]:
        problems.append(f"H-2 R-0P5 {point} hash {record['commands_sha256']} != "
                        f"{ref['commands_sha256']}")
    f_rl = ((record.get("diag") or {}).get("summary") or {}).get("F_RL_kN")
    if f_rl != ref["diag"]["summary"]["F_RL_kN"]:
        problems.append(f"H-2 R-0P5 {point} F_RL {f_rl!r} != {ref['diag']['summary']['F_RL_kN']!r}")
    return problems


def make_checker(reference: dict | None):
    """``check(record, bundle, state, stored, k3_keys, identity)`` of ``rev.run_batch``; it
    keeps the R-H lines until their P5 pair line is in."""
    half_lines: dict[str, dict[tuple, dict]] = {}

    def k_found(record: dict, bundle: str, stored: dict) -> list[str] | None:
        """K problems of a finished line; None when an R-H pair is not in yet."""
        rev_entry = record["rev"]
        if bundle == "R-0":
            sha = rj.R0_EXPECTED.get((rev_entry["key"], rev_entry["label"]))
            found = judge.settings_problems(record)
            if record["commands_sha256"] != sha:
                found.append(f"H-2 R-0 {rev_entry['key']} hash {record['commands_sha256']}")
            return found
        if bundle == "R-0P5":
            return judge.settings_problems(record) + r0p5_problems(record, reference or {})
        if bundle == "R-G":
            pair = (reference or {}).get(judge.grid_point_of(record))
            if pair is None:
                raise judge.MissingField("reference P5 pair line")
            return judge.grid_k_problems(record, pair, bundle)
        if bundle == "R-H":
            return None
        return judge.pair_k_problems_of_line(record, rj.stored_line(stored, rev_entry["key"]))

    def half_found(record: dict) -> list[tuple[dict, list[str]]]:
        """K-A of the R-H lines whose P5 pair is in once ``record`` is added."""
        point = judge.grid_point_of(record)
        by_candidate = half_lines.setdefault(point, {})
        by_candidate[record["rev"]["candidate"]] = record
        pair = by_candidate.get(judge.REFERENCE_CANDIDATE)
        if pair is None:
            return []
        out = []
        for name, line in list(by_candidate.items()):
            if name == judge.REFERENCE_CANDIDATE:
                problems = judge.settings_problems(line)
            else:
                problems = judge.grid_k_problems(line, pair, "R-H")
            out.append((line, problems))
            if name != judge.REFERENCE_CANDIDATE:
                del by_candidate[name]
        return out

    def check(record, bundle, state, stored, k3_keys, current_identity) -> None:
        rev_entry = record["rev"]
        problems = fb.identity_mismatch(rev_entry.get("identity"), current_identity)
        if problems:
            state.stop = f"run identity changed during the batch: {problems[:3]}"
            return
        tags = judge.tag_problems(record)
        if tags:
            state.stop = f"{rev_entry['key']} {rev_entry['label']}: {tags}"
            return
        try:
            found = k_found(record, bundle, stored)
            pending = [(record, found)] if found is not None else half_found(record)
        except judge.MissingField as exc:
            state.stop = f"H-4 {rev_entry['key']} {rev_entry['label']}: missing {exc}"
            return
        for line, line_problems in pending:
            _note_k(line, line_problems, bundle, state)
        _note_pair(record, bundle, state, stored)

    return check


def _note_k(line: dict, problems: list[str], bundle: str, state) -> None:
    if not problems:
        return
    rev_entry = line["rev"]
    print(f"K MISMATCH {rev_entry['candidate']} {rev_entry['label']}: {problems}", flush=True)
    if bundle in ("R-0", "R-0P5") or any(text.startswith("H-2") for text in problems):
        state.stop = f"H-2 {bundle} mismatch: {problems}"
    else:
        state.stopped_candidates.setdefault(rev_entry["candidate"],
                                            f"H-3 {rev_entry['label']}: {problems}")


def _note_pair(record: dict, bundle: str, state, stored: dict) -> None:
    """H-5 (R-P0 / R-X) and the H-8 C-2 count (R-T / R-S)."""
    rev_entry = record["rev"]
    l_line = rj.stored_line(stored, rev_entry["key"])
    if bundle in ("R-P0", "R-X") and (
            l_line is None or record["commands_sha256"] != l_line["commands_sha256"]):
        state.stop = f"H-5 {bundle} {rev_entry['key']} does not reproduce the stored L hash"
        return
    if bundle not in ("R-T", "R-S") or l_line is None:
        return
    try:
        violations = rj.pair_violations(record, l_line)
    except rj.MissingField as exc:
        violations = [f"undecidable: missing {exc}"]
    if violations:
        pairs = state.c2_pairs.setdefault(rev_entry["candidate"], set())
        pairs.add(rev_entry["key"])
        if len(pairs) >= rj.C2_STOP_PAIRS:
            state.stopped_candidates.setdefault(rev_entry["candidate"],
                                                f"H-8 {len(pairs)} C-2 pairs")


# ------------------------------------------------------------------------------- gates
def _lines_of(directory: Path, pattern: str) -> list[dict]:
    return [line for path in sorted(directory.glob(pattern)) for line in rj.read_lines(path)]


def bit_test_problems(bundle: str, current: dict, reference: dict | None,
                      directory: Path = REVA_DIR) -> list[str]:
    """H-2 before a run: R-0 passed before R-0P5; R-0 and R-0P5 passed before R-G and later,
    all their lines with the current tool sha256 (the same code)."""
    if bundle == "R-0":
        return []
    needed = ("R-0",) if bundle == "R-0P5" else ("R-0", "R-0P5")
    problems = []
    for name in needed:
        pattern = f"revA_{name.replace('-', '')}.jsonl"
        lines = _lines_of(directory, pattern)
        result = (judge.judge_r0(lines) if name == "R-0"
                  else judge.judge_r0p5(lines, reference))
        if not result["pass"]:
            problems.append(f"{name} ({pattern}) not passed: ran {result['ran']}, errors "
                            f"{result['errors']}, problems {result['problems'][:3]}")
        stale = [line for line in lines
                 if ((line.get("rev") or {}).get("identity") or {}).get("sha256")
                 != current.get("sha256")]
        if stale:
            problems.append(f"{name}: {len(stale)} lines from other tool / code sha256")
    return problems


def earlier_identity_problems(bundle: str, current: dict, directory: Path = REVA_DIR
                              ) -> list[str]:
    """Rules 4 before R-T / R-S / R-P0 / R-X: revA R-G and R-H files exist and every earlier
    bundle line has the current commit and tool sha256."""
    if bundle in ("R-0", "R-0P5", "R-G", "R-H"):
        return []
    paths = sorted({path for pattern in EARLIER_BUNDLE_FILES
                    for path in directory.glob(pattern)})
    problems = [f"no {prefix}*.jsonl in {directory}" for prefix in ("revA_RG", "revA_RH")
                if not any(path.name.startswith(prefix) for path in paths)]
    for path in paths:
        for line in rj.read_lines(path):
            if "error" in line:
                continue
            recorded = (line.get("rev") or {}).get("identity") or {}
            for name in ("git_head", "sha256"):
                if recorded.get(name) != current.get(name):
                    problems.append(f"{path.name} {(line.get('rev') or {}).get('label')}: "
                                    f"{name}")
    return problems


def grid_gate_problems(candidates, reference: dict | None, directory: Path = REVA_DIR
                       ) -> list[str]:
    """Audit item (ga) before R-T / R-S: 30 R-G + 24 R-H lines per candidate and its (ga)
    status ``pass``."""
    lines = _lines_of(directory, "revA_RG*.jsonl") + _lines_of(directory, "revA_RH*.jsonl")
    problems = []
    for name in candidates:
        result = judge.judge_grid(name, lines, reference)
        counts = (result["R-G_lines"], result["R-H_lines"])
        if counts != (judge.GRID_LINES, judge.HALF_LINES):
            problems.append(f"{name}: R-G / R-H lines {counts}, expected "
                            f"{(judge.GRID_LINES, judge.HALF_LINES)}")
        elif result["status"] != judge.STATUS_PASS:
            problems.append(f"{name}: (ga) status {result['status']}, not pass")
    return problems


# ------------------------------------------------------------------------------- CLI
def default_out(bundle: str, candidates, default_candidates) -> Path:
    name = f"revA_{bundle.replace('-', '')}"
    if default_candidates is None or tuple(candidates) != tuple(default_candidates):
        name += "_" + "_".join(candidates)
    return REVA_DIR / f"{name}.jsonl"


def resolve_candidates(bundle: str, text: str | None) -> tuple[str, ...]:
    """Bundle candidates (R-T / R-S need them: P5r4 / P5r6 only).

    Raises:
        ValueError: Missing, unknown or not allowed candidates.
    """
    default = BUNDLE_CANDIDATES[bundle]
    names = tuple(text.split(",")) if text else default
    if not names:
        raise ValueError(f"{bundle} needs --candidates (those that passed (ga))")
    allowed = default or judge.JUDGED_CANDIDATES
    unknown = [name for name in names if name not in allowed]
    if unknown:
        raise ValueError(f"{bundle}: candidates {unknown} not in {allowed}")
    return names


def load_reference_for(bundle: str, path: Path) -> dict | None:
    """The reference P5 lines (H-10 for the bundles that read them).

    Raises:
        ValueError: The reference is needed and missing or not the stored one.
    """
    problems = judge.reference_problems(path)
    if problems:
        if bundle in REFERENCE_BUNDLES:
            raise ValueError(f"{problems} (rules 8 H-10: R-0P5 / R-G are not run)")
        return None
    return judge.load_reference(path)


def list_bundles(bundles, candidates_text: str | None, reference_path: Path
                 ) -> tuple[list[str], list[str]]:
    """(report lines, problems): run counts, the reference and the R-0 table."""
    stored = rj.load_stored()
    lines, problems = [], []
    reference_issues = judge.reference_problems(reference_path)
    problems += reference_issues
    if not reference_issues:
        reference = judge.load_reference(reference_path)
        lines.append(f"reference {reference_path}: {len(reference)} P5 points")
    for bundle in bundles:
        if bundle in ("R-P0", "R-X"):
            lines.append(f"{bundle}: keys from the revA R-T / R-S files (run --from / --keys)")
            continue
        if bundle in ("R-T", "R-S"):
            names = resolve_candidates(
                bundle, candidates_text or ",".join(judge.JUDGED_CANDIDATES))
        else:
            names = BUNDLE_CANDIDATES[bundle]
        jobs = bundle_jobs(bundle, names)
        lines.append(f"{bundle}: {len(jobs)} runs, candidates {names}")
        expected = BUNDLE_COUNTS.get(bundle)
        if expected is not None and len(jobs) != expected:
            problems.append(f"{bundle}: {len(jobs)} runs, expected {expected}")
        problems += rev.job_dict_problems(jobs, stored) if bundle in ("R-T", "R-S") else []
    for (key, label), sha in rj.R0_EXPECTED.items():
        line = rj.stored_line(stored, key)
        if line is not None and label == "P0" and line["commands_sha256"] != sha:
            problems.append(f"R-0 reference {key} differs from the stored line")
    return lines, problems


def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="runs of the bundles and the reference checks")
    listing.add_argument("--bundle", nargs="+", choices=BUNDLES, default=list(BUNDLES))
    listing.add_argument("--candidates", default=None)
    listing.add_argument("--ref-rg", type=Path, default=judge.DEFAULT_REFERENCE_RG)
    run = sub.add_parser("run", help="run a bundle into a new file")
    run.add_argument("--bundle", required=True, choices=BUNDLES)
    run.add_argument("--ref-rg", type=Path, default=judge.DEFAULT_REFERENCE_RG,
                     help="stored rev_RG.jsonl (H-10; the main checkout's, not in git)")
    run.add_argument("--candidates", default=None, help="comma-separated, e.g. P5r4,P5r6")
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--affinity", default=None, help="hex mask, set in every worker")
    run.add_argument("--out", type=Path, default=None)
    run.add_argument("--keys", default=None, help="comma-separated pair keys (subset)")
    run.add_argument("--from", dest="from_files", type=Path, nargs="+", default=None,
                     help="R-P0 / R-X: the revA R-T / R-S files the keys come from")
    run.add_argument("--limit", type=int, default=None, help="first N runs only")
    run.add_argument("--no-done-record", action="store_true")
    return parser.parse_args(argv)


def _keys_of(args, stored: dict) -> list[str] | None:
    if args.keys:
        return args.keys.split(",")
    if args.bundle in ("R-P0", "R-X"):
        files = args.from_files or sorted(REVA_DIR.glob("revA_RT*.jsonl")) + sorted(
            REVA_DIR.glob("revA_RS*.jsonl"))
        return rev.keys_from_files(files, args.bundle, stored)
    return None


def _check_gates(args, candidates, identity: dict, reference: dict | None) -> None:
    """Rules 4 / 8 gates before the jobs (raises ValueError)."""
    problems = rev.identity_problems(identity)
    if problems:
        raise ValueError(f"run identity (rules 4): {problems}")
    problems = bit_test_problems(args.bundle, identity, reference)
    if problems:
        raise ValueError(f"H-2 bit tests before {args.bundle}: {problems}")
    problems = earlier_identity_problems(args.bundle, identity)
    if problems:
        raise ValueError(f"earlier bundle lines of another run identity: {problems[:5]}")
    if args.bundle in ("R-T", "R-S"):
        problems = grid_gate_problems(candidates, reference)
        if problems:
            raise ValueError(f"(ga) gate before {args.bundle}: {problems}")


def _prepare(args) -> tuple[list[dict], Path, dict, dict, dict | None]:
    """Jobs, output path, stored lines, identity and reference of a run (raises on input
    errors)."""
    candidates = resolve_candidates(args.bundle, args.candidates)
    path = args.out or default_out(args.bundle, candidates, BUNDLE_CANDIDATES[args.bundle])
    problem = rev.out_path_problem(path, REVA_DIR)
    if problem is not None:
        raise ValueError(problem)
    reference = load_reference_for(args.bundle, args.ref_rg)
    identity = run_identity()
    _check_gates(args, candidates, identity, reference)
    stored = rj.load_stored()
    mask = None if args.affinity is None else int(args.affinity, 16)
    keys = _keys_of(args, stored)
    if keys is not None and not keys:
        raise ValueError("no keys selected")
    jobs = bundle_jobs(args.bundle, candidates, mask, keys, not args.no_done_record)
    problems = rev.job_dict_problems(jobs, stored)
    if problems:
        raise ValueError(f"H-4 job dicts: {problems[:5]}")
    jobs = jobs if args.limit is None else jobs[: args.limit]
    if not jobs:
        raise ValueError("no runs selected")
    return jobs, path, stored, identity, reference


def _run_command(args) -> int:
    try:
        jobs, path, stored, identity, reference = _prepare(args)
    except (KeyError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"input error: {exc!r}")
        print(json.dumps({"bundle": args.bundle, "stop": "input", "reason": str(exc)}))
        return 2
    print(f"run identity: {identity['git_head']} dirty {identity['git_dirty']} "
          f"code_diff {identity['code_diff_sha256'][:12]}", flush=True)
    print(f"{args.bundle}: {len(jobs)} runs -> {path}", flush=True)
    state = rev.run_batch(jobs, path, args.workers, args.bundle, stored, identity,
                          worker=run_revA_job, check=make_checker(reference),
                          whole_bundle_rerun=WHOLE_BUNDLE_RERUN)
    summary = {"bundle": args.bundle, "out": str(path), "runs": state.runs,
               "errors": state.errors, "skipped": state.skipped, "stop": state.stop,
               "stopped_candidates": state.stopped_candidates,
               "c2_pairs": {name: len(keys) for name, keys in state.c2_pairs.items()}}
    print(json.dumps(summary))
    is_bad = state.stop or state.stopped_candidates or state.skipped
    return 1 if is_bad else 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    problems = judge.sealed_rules_problems()
    if problems:
        print(f"input error (H-1): {problems}")
        print(json.dumps({"stop": "H-1", "reasons": problems}))
        return 2
    if args.command == "run":
        return _run_command(args)
    try:
        lines, problems = list_bundles(args.bundle, args.candidates, args.ref_rg)
    except (KeyError, OSError, ValueError) as exc:
        print(f"input error: {exc!r}")
        return 2
    print("\n".join(lines))
    for problem in problems:
        print(f"MISMATCH {problem}")
    print(json.dumps({"bundles": args.bundle, "problems": len(problems)}))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
