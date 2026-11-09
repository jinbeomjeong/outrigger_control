"""LAS-b revision A addendum rev2 on the reduced harness: P5r4 (beta 4.5 + end ramp N_r 4).

Rules: ``06_analysis/02_control/verif_matrix/las_revA_targeted_rules_rev2.md`` (control-expert,
sealed; LF sha256 ``las_revA_judge.RULES_REVA_REV2_SHA256``) on top of its rev1, the revA
rules and the two files they inherit (all five checked, H-1). The rules text wins where this
code differs. The run machinery (candidate wrapper, DONE record, pool, pair jobs) is
``las_rev_targeted``'s.

Candidates (rules 1.2, rev2 R2-2, ``las`` = ``C2Config.with_10hz_d1().liftoff_approach_slow``,
b0):
  P0    the preset as it is (no override at all)
  P5    ``replace(las, light_leg_fraction_of_F_min=4.5, min_active_periods=0,
        end_ramp_periods=0)`` (N_r 0 given explicitly, rules 7.2)
  P5r4  the same with ``end_ramp_periods=4`` (P5r6 is dropped, rev2 R2-2)
Applied in the worker by ``las_rev_targeted.install_candidate`` (``dataclasses.replace`` on a
b0 config only; ``las_targeted.install`` is never installed); every line records the settings
the run's controller used (K-A8). The preset itself is not touched.

Bundles (rev2 R2-5), output ``06_analysis/03_hydraulic/coupled/v5/las/revA2/revA_R<bundle>
[_<candidates>].jsonl`` (opened with ``"x"``, no resume):
  R-0    6 P0 bit tests (``las_rev_judge.R0_EXPECTED``, rules 7.1).
  R-0P5  P5 on the 30 R-G points; hash and ``F_RL_kN`` = the reference P5 line (rules 7.2).
  R-0A   P5r4 on the 30 R-G points (j 0..4, label ``P5r4-LT-c<centre>-j<j>``) and the 24 R-H
         points (j 0.5 .. 3.5, ``P5r4-LH-c<centre>-j<j with p>``) = 54; hash = the stored
         P5r4 line of the point (``revA_RG.jsonl`` / ``revA_RH.jsonl``, 64 characters).
  R-Q    P5r4 on the 48 quarter-step points j 0.25 .. 3.75, label
         ``P5r4-LQ-c<centre>-j<j with p>`` (``touch_budget.j`` a float).
  R-T    (na) T-1 8 + T-2 184 keys x P5r4.
  R-S    (da) F-3 16 + F-4 14 jobs x P5r4.
  R-P0   P0 on the keys whose hash changed in the revA2 R-T / R-S files.
  R-X    P0 with the DONE record on the keys of the C-4 exception claims, or --keys.
Gates before a run (exit 2): H-1 seals; H-10 the reference ``rev_RG.jsonl`` (``--ref-rg``,
raw sha256 7e8c3b41..) for every bundle but R-0 and the stored ``revA_RG.jsonl`` /
``revA_RH.jsonl`` (``--ref-reva-rg`` / ``--ref-reva-rh``, ac389809.. / f934cbd9..) for R-0A
and later; H-2 R-0 passed before R-0P5, R-0 and R-0P5 before R-0A, and R-0 / R-0P5 / R-0A
(hashes, K-A, H-11') before R-Q, every line from the current commit and tool sha256 (rev2
R2-5: one commit, one tool sha256); R-T / R-S / R-P0 / R-X need every earlier revA2 line
(R-0 .. R-P0) from the current commit and tool sha256 and no line rev2 does not run, and
R-T / R-S need (ga)' ``pass`` without an H-2 / H-4 / H-6' / H-11' / H-13 stop or an H-12
ask (``las_revA_judge.na_da_gate_problems``); R-T / R-S job dicts must equal the stored L
lines' (H-4).

During a batch (``las_revA_judge`` checks on each finished line): H-2 an R-0 / R-0P5 / R-0A
hash mismatch -> stop everything; a K-A mismatch on R-0A / R-Q (H-3 / H-13) -> stop
everything (one candidate); H-3 on R-T / R-S -> no more P5r4 jobs; H-4 a missing field ->
stop; H-5 an R-P0 / R-X hash that is not L's -> stop; H-7 an error line -> the job once more
(R-0P5 / R-0A / R-Q: stop, re-run the bundle as a whole); H-8 five pairs with a C-2 type
violation -> no more P5r4 jobs; a run identity change or a ``controller_tag`` that is not the
setting's -> stop.
Line = the ``run_v5`` line + ``las`` (``las_rev_targeted.las_block`` + ``params.n_r`` + ``ramp``
{n_r, start_factor, periods_applied, scaled_periods, end_t_s, end_reason}) + ``rev`` {bundle,
candidate, label, key, grid_point, identity, the five rules sha256 (``rules_sha256``,
``rules_rev1_sha256``, ``rules_revA_sha256``, ``rules_revA_rev1_sha256``,
``rules_revA_rev2_sha256``), settings, expected_settings, settings_match, controller_tag,
record flags} (+ ``diag`` for grid lines, ``periods[].las`` with ramp_m / ramp_factor /
ramp_scaled, + the DONE record ``done_trace`` / ``done_clock``).

Usage (dynamics-dev python.exe, project root, PowerShell):
  python -I -B 04_scripts/04_hydraulic/coupled/las_revA_targeted.py list [--bundle R-0 ..]
      [--ref-rg <rev_RG.jsonl>] [--ref-reva-rg <revA_RG.jsonl>] [--ref-reva-rh <revA_RH.jsonl>]
  python -I -B 04_scripts/04_hydraulic/coupled/las_revA_targeted.py run --bundle R-0A
      [--ref-rg ..] [--ref-reva-rg ..] [--ref-reva-rh ..] [--workers 4] [--affinity HEX]
      [--out <jsonl>] [--keys K1,K2] [--from <jsonl> ..] [--limit N] [--no-done-record]
Exit codes: 0 done, 1 a stop condition or run errors (run) / a count or reference mismatch
(list), 2 input error (seals, references, gates, dirty code, existing --out, job dicts).
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
REVA_DIR = judge.REVA2_DIR
IDENTITY_FILES = {**rev.IDENTITY_FILES,
                  "las_revA_targeted.py": HERE / "las_revA_targeted.py",
                  "las_revA_judge.py": HERE / "las_revA_judge.py"}
"""Rules 4: c2.py, the revA tool and judge, the rev tool and judge, las_phase_diag,
fb_targeted, las_targeted."""

BUNDLES = judge.BUNDLES
P5R4_ONLY = judge.JUDGED_CANDIDATES
BUNDLE_CANDIDATES = {"R-0": ("P0",), "R-0P5": (judge.REFERENCE_CANDIDATE,), "R-0A": P5R4_ONLY,
                     "R-Q": P5R4_ONLY, "R-T": P5R4_ONLY, "R-S": P5R4_ONLY, "R-P0": ("P0",),
                     "R-X": ("P0",)}
BUNDLE_COUNTS = {"R-0": 6, "R-0P5": judge.GRID_LINES, "R-0A": judge.R0A_LINES,
                 "R-Q": judge.QUARTER_LINES}
REFERENCE_BUNDLES = tuple(name for name in BUNDLES if name != "R-0")
"""H-10: R-0P5 / R-0A read the reference P5 lines; every later bundle judges with them."""
STORED_REVA_BUNDLES = tuple(name for name in BUNDLES if name not in ("R-0", "R-0P5"))
"""H-10 (rev2 R2-6): R-0A is paired with the stored revA lines; later bundles gate on R-0A."""
WHOLE_BUNDLE_RERUN = judge.GRID_BUNDLES
BIT_TEST_ORDER = ("R-0", "R-0P5", "R-0A")
GRID_KIND_STEPS = {"R-0P5": (("LT", judge.GRID_STEPS),),
                   "R-0A": (("LT", judge.GRID_STEPS), ("LH", judge.HALF_STEPS)),
                   "R-Q": (("LQ", judge.QUARTER_STEPS),)}
"""Label kind and steps of the grid bundles (R-G integer, R-H half and R-Q quarter steps)."""


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
def step_text(j: int | float) -> str:
    """``1.5`` -> ``1p5``, ``0.25`` -> ``0p25`` (rules 3.2 / rev2 R2-3 label)."""
    return str(j).replace(".", "p")


def grid_label(candidate: str, centre: str, j: int | float, kind: str) -> str:
    """``<candidate>-<kind>-c<centre>-j<j>``; kind LT (integer), LH (half) or LQ (quarter)."""
    return f"{candidate}-{kind}-c{centre}-j{step_text(j)}"


def grid_jobs(bundle: str, candidates) -> tuple[list[dict], list[dict]]:
    """R-0P5 / R-0A / R-Q: the two grid keys (VB first) x centre x steps x candidates."""
    import las_targeted

    base = sorted(las_targeted.jobs_for_keys(list(rev.GRID_KEYS)),
                  key=lambda job: job["setting"] != "VB")
    jobs, entries = [], []
    for kind, steps in GRID_KIND_STEPS[bundle]:
        for job in base:
            for centre in judge.GRID_CENTRES:
                for j in steps:
                    for candidate in candidates:
                        jobs.append(job)
                        entries.append(rev._entry(bundle, candidate,
                                                  grid_label(candidate, centre, j, kind),
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
def rules_block() -> dict:
    """The five rules sha256 every line records (rev2 B.1)."""
    return dict(zip(judge.RULES_FIELDS, judge.RULES_VALUES, strict=True))


def run_identity() -> dict:
    """``fb_targeted.run_identity`` with this tool's files and the five rules sha256."""
    return {**fb.run_identity(files=IDENTITY_FILES), **rules_block()}


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
            "key": fb.fb_key(job), "identity": identity, **rules_block(),
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


def r0a_line_problems(record: dict, reference: dict | None,
                      stored_reva: judge.StoredRevA | None) -> list[str]:
    """H-2 (hash) and K-A1 .. K-A8 of one R-0A line against its P5 pair.

    Raises:
        judge.MissingField: The pair line or a field the K-A checks read is missing.
    """
    problems = judge.settings_problems(record)
    hash_problem = judge.r0a_hash_problem(record, stored_reva)
    if hash_problem is not None:
        problems.append(hash_problem)
    part = judge.part_of(record)
    pairs = reference if part == judge.PART_RG else (
        None if stored_reva is None else stored_reva.half_p5)
    pair = (pairs or {}).get(judge.grid_point_of(record))
    if pair is None:
        raise judge.MissingField(f"P5 pair line of the {part} part")
    return problems + judge.grid_k_problems(record, pair, part)


def make_checker(reference: dict | None, stored_reva: judge.StoredRevA | None = None):
    """``check(record, bundle, state, stored, k3_keys, identity)`` of ``rev.run_batch``."""

    def k_found(record: dict, bundle: str, stored: dict) -> list[str]:
        rev_entry = record["rev"]
        if bundle == "R-0":
            sha = rj.R0_EXPECTED.get((rev_entry["key"], rev_entry["label"]))
            found = judge.settings_problems(record)
            if record["commands_sha256"] != sha:
                found.append(f"H-2 R-0 {rev_entry['key']} hash {record['commands_sha256']}")
            return found
        if bundle == "R-0P5":
            return judge.settings_problems(record) + r0p5_problems(record, reference or {})
        if bundle == "R-0A":
            return r0a_line_problems(record, reference, stored_reva)
        if bundle == "R-Q":
            return judge.quarter_k_problems(record)
        return judge.pair_k_problems_of_line(record, rj.stored_line(stored, rev_entry["key"]))

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
        except judge.MissingField as exc:
            state.stop = f"H-4 {rev_entry['key']} {rev_entry['label']}: missing {exc}"
            return
        _note_k(record, found, bundle, state)
        _note_pair(record, bundle, state, stored)

    return check


def _note_k(line: dict, problems: list[str], bundle: str, state) -> None:
    """H-2 / H-3 / H-13: any problem in a bit test or grid bundle stops everything (one
    candidate); on R-T / R-S it stops the candidate."""
    if not problems:
        return
    rev_entry = line["rev"]
    print(f"K MISMATCH {rev_entry['candidate']} {rev_entry['label']}: {problems}", flush=True)
    if bundle in BIT_TEST_ORDER or bundle == "R-Q" or any(
            text.startswith("H-2") for text in problems):
        kind = "H-13" if any(judge.is_h13(text) for text in problems) else "H-2 / H-3"
        state.stop = f"{kind} {bundle} {rev_entry['label']}: {problems}"
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


def bundle_file_name(bundle: str) -> str:
    return f"revA_{bundle.replace('-', '')}.jsonl"


def stale_problems(name: str, lines: list[dict], current: dict) -> list[str]:
    """Lines (errors included) whose commit or tool sha256 is not the current run's (rev2
    R2-5: every bundle of this addendum from one commit and one tool sha256), and finished
    lines that do not record the five sealed rules digests (rev2 B.1)."""
    stale = [line for line in lines
             if any(((line.get("rev") or {}).get("identity") or {}).get(field)
                    != current.get(field) for field in ("git_head", "sha256"))]
    other_rules = [line for line in lines
                   if not rj.is_error(line) and judge.rules_problems(rj.rev_of(line))]
    problems = []
    if stale:
        problems.append(f"{name}: {len(stale)} lines from another commit or tool / code "
                        f"sha256")
    if other_rules:
        problems.append(f"{name}: {len(other_rules)} lines with other rules sha256")
    return problems


def _bit_result(name: str, lines: list[dict], reference: dict | None,
                stored_reva: judge.StoredRevA | None) -> list[str]:
    if name == "R-0":
        result = judge.judge_r0(lines)
    elif name == "R-0P5":
        result = judge.judge_r0p5(lines, reference)
    else:
        return judge.r0a_gate_problems(lines, reference, stored_reva)
    if result["pass"]:
        return []
    return [f"{name} not passed: ran {result['ran']}, errors {result['errors']}, problems "
            f"{result['problems'][:3]}"]


def bit_test_problems(bundle: str, current: dict, reference: dict | None,
                      stored_reva: judge.StoredRevA | None = None,
                      directory: Path = REVA_DIR) -> list[str]:
    """H-2 before a run: the bit tests before ``bundle`` (R-0 < R-0P5 < R-0A < the rest)
    passed, all their lines from the current commit and tool sha256."""
    position = BIT_TEST_ORDER.index(bundle) if bundle in BIT_TEST_ORDER else len(BIT_TEST_ORDER)
    problems = []
    for name in BIT_TEST_ORDER[:position]:
        file_name = bundle_file_name(name)
        lines = _lines_of(directory, file_name)
        problems += [f"{text} ({file_name})"
                     for text in _bit_result(name, lines, reference, stored_reva)]
        problems += stale_problems(name, lines, current)
    return problems


def earlier_identity_problems(bundle: str, current: dict, directory: Path = REVA_DIR
                              ) -> list[str]:
    """Rev2 B.2 before R-T / R-S / R-P0 / R-X: the R-0A and R-Q files exist, every earlier
    revA2 line (R-0, R-0P5, R-0A, R-Q, R-T, R-S, R-P0) has the current commit and tool sha256
    and no line is one rev2 does not run (P5r6, old bundles)."""
    if bundle in ("R-0", "R-0P5", "R-0A", "R-Q"):
        return []
    paths = sorted(directory.glob("revA_R*.jsonl"))
    problems = [f"no {bundle_file_name(name)} in {directory}" for name in ("R-0A", "R-Q")
                if not any(path.name == bundle_file_name(name) for path in paths)]
    for path in paths:
        lines = rj.read_lines(path)
        problems += stale_problems(path.name, lines, current)
        problems += [f"{path.name}: {text}" for text in judge.foreign_line_problems(lines)]
    return problems


def prime_gate_problems(stored: dict, reference: dict | None,
                        stored_reva: judge.StoredRevA | None, directory: Path = REVA_DIR
                        ) -> list[str]:
    """(ga)' gate before R-T / R-S (rev2 R2-4, H-6', H-11', H-12, H-13)."""
    lines = _lines_of(directory, "revA_R*.jsonl")
    result = judge.judge(lines, stored, reference, stored_reva)
    return judge.na_da_gate_problems(result)


# ------------------------------------------------------------------------------- CLI
def default_out(bundle: str, candidates, default_candidates) -> Path:
    name = f"revA_{bundle.replace('-', '')}"
    if default_candidates is None or tuple(candidates) != tuple(default_candidates):
        name += "_" + "_".join(candidates)
    return REVA_DIR / f"{name}.jsonl"


def resolve_candidates(bundle: str, text: str | None) -> tuple[str, ...]:
    """Bundle candidates: rev2 runs one candidate per bundle (P5r4 for R-0A .. R-S).

    Raises:
        ValueError: A candidate the bundle does not run.
    """
    default = BUNDLE_CANDIDATES[bundle]
    names = tuple(text.split(",")) if text else default
    unknown = [name for name in names if name not in default]
    if unknown or not names:
        raise ValueError(f"{bundle}: candidates {list(names)} not in {default} (rev2 R2-2)")
    return names


@dataclass
class ReferencePaths:
    """The three stored reference files (H-10)."""

    rg: Path
    reva_rg: Path
    reva_rh: Path


def load_references_for(bundle: str, paths: ReferencePaths
                        ) -> tuple[dict | None, judge.StoredRevA | None]:
    """The reference P5 lines and the stored revA lines a bundle needs (H-10).

    Raises:
        ValueError: A needed reference is missing or not the stored one.
    """
    reference, stored_reva = None, None
    issues = judge.reference_problems(paths.rg)
    if bundle in REFERENCE_BUNDLES:
        if issues:
            raise ValueError(f"{issues} (rules 8 H-10; give --ref-rg, the main checkout's "
                             f"file)")
        reference = judge.load_reference(paths.rg)
    if bundle in STORED_REVA_BUNDLES:
        issues = judge.stored_reva_problems(paths.reva_rg, paths.reva_rh)
        if issues:
            raise ValueError(f"{issues} (rev2 H-10; give --ref-reva-rg / --ref-reva-rh, the "
                             f"main checkout's files)")
        stored_reva = judge.load_stored_reva(paths.reva_rg, paths.reva_rh)
    return reference, stored_reva


def list_bundles(bundles, paths: ReferencePaths) -> tuple[list[str], list[str]]:
    """(report lines, problems): run counts, the references and the R-0 table."""
    stored = rj.load_stored()
    lines, problems = [], []
    reference_issues = judge.reference_problems(paths.rg)
    reva_issues = judge.stored_reva_problems(paths.reva_rg, paths.reva_rh)
    problems += reference_issues + reva_issues
    if not reference_issues:
        lines.append(f"reference {paths.rg}: {len(judge.load_reference(paths.rg))} P5 points")
    if not reva_issues:
        stored_reva = judge.load_stored_reva(paths.reva_rg, paths.reva_rh)
        lines.append(f"stored revA: {len(stored_reva.p5r4)} P5r4 points, "
                     f"{len(stored_reva.half_p5)} R-H P5 points")
    for bundle in bundles:
        if bundle in ("R-P0", "R-X"):
            lines.append(f"{bundle}: keys from the revA2 R-T / R-S files (run --from / --keys)")
            continue
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


def _add_reference_args(parser) -> None:
    parser.add_argument("--ref-rg", type=Path, default=judge.DEFAULT_REFERENCE_RG,
                        help="stored rev_RG.jsonl (H-10; the main checkout's, not in git)")
    parser.add_argument("--ref-reva-rg", type=Path, default=judge.DEFAULT_STORED_REVA_RG,
                        help="stored revA_RG.jsonl (rev2 H-10; main checkout, not in git)")
    parser.add_argument("--ref-reva-rh", type=Path, default=judge.DEFAULT_STORED_REVA_RH,
                        help="stored revA_RH.jsonl (rev2 H-10; main checkout, not in git)")


def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="runs of the bundles and the reference checks")
    listing.add_argument("--bundle", nargs="+", choices=BUNDLES, default=list(BUNDLES))
    _add_reference_args(listing)
    run = sub.add_parser("run", help="run a bundle into a new file")
    run.add_argument("--bundle", required=True, choices=BUNDLES)
    _add_reference_args(run)
    run.add_argument("--candidates", default=None, help="only the bundle's own candidate")
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--affinity", default=None, help="hex mask, set in every worker")
    run.add_argument("--out", type=Path, default=None)
    run.add_argument("--keys", default=None, help="comma-separated pair keys (subset)")
    run.add_argument("--from", dest="from_files", type=Path, nargs="+", default=None,
                     help="R-P0 / R-X: the revA2 R-T / R-S files the keys come from")
    run.add_argument("--limit", type=int, default=None, help="first N runs only")
    run.add_argument("--no-done-record", action="store_true")
    return parser.parse_args(argv)


def _paths_of(args) -> ReferencePaths:
    return ReferencePaths(args.ref_rg, args.ref_reva_rg, args.ref_reva_rh)


def _keys_of(args, stored: dict) -> list[str] | None:
    if args.keys:
        return args.keys.split(",")
    if args.bundle in ("R-P0", "R-X"):
        files = args.from_files or sorted(REVA_DIR.glob("revA_RT*.jsonl")) + sorted(
            REVA_DIR.glob("revA_RS*.jsonl"))
        return rev.keys_from_files(files, args.bundle, stored)
    return None


def _check_gates(bundle: str, identity: dict, stored: dict, reference: dict | None,
                 stored_reva: judge.StoredRevA | None) -> None:
    """Rules 4 / 8 and rev2 R2-5 / R2-6 gates before the jobs (raises ValueError)."""
    problems = rev.identity_problems(identity)
    if problems:
        raise ValueError(f"run identity (rules 4): {problems}")
    problems = bit_test_problems(bundle, identity, reference, stored_reva)
    if problems:
        raise ValueError(f"H-2 bit tests before {bundle}: {problems}")
    problems = earlier_identity_problems(bundle, identity)
    if problems:
        raise ValueError(f"earlier bundle lines of another run identity: {problems[:5]}")
    if bundle in ("R-T", "R-S"):
        problems = prime_gate_problems(stored, reference, stored_reva)
        if problems:
            raise ValueError(f"(ga)' gate before {bundle}: {problems}")


def _prepare(args) -> tuple[list[dict], Path, dict, dict, dict | None, judge.StoredRevA | None]:
    """Jobs, output path, stored lines, identity and references of a run (raises on input
    errors)."""
    candidates = resolve_candidates(args.bundle, args.candidates)
    path = args.out or default_out(args.bundle, candidates, BUNDLE_CANDIDATES[args.bundle])
    problem = rev.out_path_problem(path, REVA_DIR)
    if problem is not None:
        raise ValueError(problem)
    reference, stored_reva = load_references_for(args.bundle, _paths_of(args))
    identity = run_identity()
    stored = rj.load_stored()
    _check_gates(args.bundle, identity, stored, reference, stored_reva)
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
    return jobs, path, stored, identity, reference, stored_reva


def _run_command(args) -> int:
    try:
        jobs, path, stored, identity, reference, stored_reva = _prepare(args)
    except (KeyError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"input error: {exc!r}")
        print(json.dumps({"bundle": args.bundle, "stop": "input", "reason": str(exc)}))
        return 2
    print(f"run identity: {identity['git_head']} dirty {identity['git_dirty']} "
          f"code_diff {identity['code_diff_sha256'][:12]}", flush=True)
    print(f"{args.bundle}: {len(jobs)} runs -> {path}", flush=True)
    state = rev.run_batch(jobs, path, args.workers, args.bundle, stored, identity,
                          worker=run_revA_job, check=make_checker(reference, stored_reva),
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
        lines, problems = list_bundles(args.bundle, _paths_of(args))
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
