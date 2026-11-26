"""436.9 edition 8 key files and the layer rule (``jp3_remedy_spec_v8_rules.md`` 5.1, 6.3, 7.1,
7.2; 16 Y8-6).

Two key files, made deterministically from their sources (no time, path or commit in them):

* ``census_keys_ed8.json`` (spec 5.1, P8-10): 1043 lines in stage order C-J (388, the ``job``
  of each line of the edition 7 ``j9_main.jsonl``, VBM -> VBN, LSM<n> -> LSN<n>), C-S (460,
  ``sens_keys_ed7.json``, VBM<key> -> VBN<key>), C-D (24, the 12 jobs of the git blob
  ``d_grid_keys12.json`` x {VBN, VBNslow}, V0 pair from the matching ``confirm_b_grid192.json``
  line) and C-G (171, ``confirm_g1_grid171.json``, VBM -> VBN). Each line: ``stage``, ``job``
  (with its edition 8 ``setting``), ``source_setting``, ``role``, ``v0_pair``.
* ``heldout_g_ed8.json`` (spec 7.1, 7.2): 339 slots of the held-out source G' - (가) the 171
  clean clusters x one new phase of O', (나) the 48 clean RE1bF clusters x one (shape, phase)
  of {25 mm / 0.05 s, 30 mm / 0.04 s} x (O' and the four stored phases), (다) the 40 clean
  families (level, timing, leg, event) x {1, 3, 6} kN x one phase of the eight. Slots in
  (source label, slot key) string order; ``numpy.random.default_rng(20261127)`` draws, per
  slot, the condition (``integers``) and then the A/A order of the slot's other candidates
  (``permutation``). A cluster or family is clean when every stored V0 grid run of it (the four
  stored phases) passes. Each slot: the VBN job, the V0 job of its condition and the A/A
  candidate V0 jobs in order; twin fields are checked against ``verdict_cases.EventTwin``.

The layer rule (spec 6.3) and the 0c' event-name record are functions here
(:func:`stratum_of`, :func:`event_of_job`, :func:`event_resolution_counts`); the judgement tool
(T8, a later commit) reads its V0 inputs and calls them. Nothing here reads a result of the
edition 8 controller.

======  ==============================================================================
exit    meaning
======  ==============================================================================
0       the key file(s) written (and the input sha256 digests as the spec quotes them)
2       input error: a missing or unreadable source, another sha256, another line count,
        an existing output file
3       tool error (any unexpected failure)
======  ==============================================================================

Usage (checkout root or any folder; ``--root`` = the main checkout with the sources):
  python -I -B ed8_key_lists.py census  --root <repo> --out <census_keys_ed8.json>
  python -I -B ed8_key_lists.py heldout --root <repo> --out <heldout_g_ed8.json>
The stdout's last line is JSON with ``status``, the line count, the sha256 and the output path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import traceback
from collections import Counter
from dataclasses import dataclass, fields
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

EXIT_OK, EXIT_INPUT, EXIT_TOOL = 0, 2, 3
JP3 = "06_analysis/02_control/j_p3_cause"
J9_MAIN = (f"{JP3}/j9_runs/8a2a52ce/j9main_a1/j9_main.jsonl",
           "c89ec827ce541a53127a0115b8e1185b35e50df9cea2612d4a74b40cc618c122")
SENS_KEYS = (f"{JP3}/ed7_design/keys_seal_b46bdf8f/sens_keys_ed7.json",
             "be930b75a375877d07fc84fa98a9f8b0ee463f5b592319cfd6869fcc62a05b1b")
D_KEYS_BLOB = (f"3ecf61f1:{JP3}/prelaunch_j9/run_records_ed6/d_grid_keys12.json",
               "a995abff9d73816f58a0e3d67a59f18b3e60fb006fe48d824012b79b57d87981")
G1_KEYS = (f"{JP3}/ed7_design/keys_seal_b46bdf8f/confirm_g1_grid171.json",
           "684054abb1ad05d8f82141f58eafdfa3c096edae1c05c9a4b9e8ae9ffe5b5dec")
GRID192_KEYS = (f"{JP3}/ed6_design/keys/confirm_b_grid192.json",
                "4e80e69bd2233b994853ae3f60ed0749f2c39c7dbb6390bc012b016efa5cf85b")
"""Spec v8 5.1 sources: (repo-relative path or git blob, sha256)."""
CENSUS_STAGE_LINES = {"C-J": 388, "C-S": 460, "C-D": 24, "C-G": 171}
CENSUS_LINES = 1043
CJ_SETTING_MAP = {"VBM": "VBN", **{f"LSM{n}": f"LSN{n}" for n in "1234"}}
"""Spec v8 5.1: VBM -> VBN, LSM<n> -> LSN<n> (C-J); C-S maps VBM<key> -> VBN<key>."""
CD_SETTINGS = (("VBN", "jp3a_fault_and_v0_in_C-G"), ("VBNslow", "jp3a_fault_v0_record"))
"""Spec v8 5.2 C-D: VBN failures against V0 count in the C-G cell; VBNslow is a record."""
IGNORED_JOB_FIELDS = ("setting", "mask", "t4h_dir")
V0_MAIN_SOURCE = "v5/main.jsonl V0"

HELDOUT_SEED = 20261127
"""Spec v8 7.2 (seed rule: the seal date with +1 past every seed of editions 5 .. 8)."""
NEW_PHASES_S = (0.0125, 0.0375, 0.0625, 0.0875)
"""O' (spec v8 7.1)."""
STORED_PHASES_S = (0.0, 0.025, 0.05, 0.075)
ALL_PHASES_S = tuple(sorted(NEW_PHASES_S + STORED_PHASES_S))
SHAPES = ((0.025, 0.05), (0.030, 0.04))
"""Spec v8 7.1 (나): RE1bF (depth m, ramp s) variants."""
NEW_FS_KN = (1.0, 3.0, 6.0)
HELDOUT_SIZES = {"a_phase": 171, "b_shape": 48, "c_fs": 120}
HELDOUT_SLOTS = 339
HELDOUT_SETTING = "VBN"

E_CANDIDATE_EVENTS = ("RE1bF",)
"""Spec v8 6.3: the E candidate event (with its depth / ramp variants, the same name)."""
E_WINDOW_S = 0.450
DIAGONAL_LEG = {"FL": "RR", "RR": "FL", "FR": "RL", "RL": "FR"}


class KeyInputError(ValueError):
    """A source the key files cannot be made from (exit 2)."""


class LayerInputError(ValueError):
    """Spec v8 6.3: a layer input defect of an E-candidate event row (``setting_defect``)."""


# ------------------------------------------------------------------------- sources
def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _checked(data: bytes, expected: str, what: str) -> bytes:
    digest = sha256_of(data)
    if digest != expected:
        raise KeyInputError(f"{what}: sha256 {digest} is not {expected}")
    return data


def read_source(root: Path, source: tuple[str, str]) -> bytes:
    """The bytes of a spec source (a file under ``root`` or a ``<rev>:<path>`` git blob),
    its sha256 checked.

    Raises:
        KeyInputError: Unreadable, or another sha256.
    """
    name, expected = source
    try:
        if ":" in name.split("/", 1)[0]:
            completed = subprocess.run(["git", "-C", str(root), "show", name],
                                       capture_output=True, check=True, timeout=120,
                                       stdin=subprocess.DEVNULL)
            data = completed.stdout
        else:
            data = (root / name).read_bytes()
    except (OSError, subprocess.SubprocessError) as exc:
        raise KeyInputError(f"{name}: {exc}") from exc
    return _checked(data, expected, name)


def plain_job(job: dict) -> dict:
    """A job without its setting and the runtime-only entries."""
    return {key: value for key, value in job.items() if key not in IGNORED_JOB_FIELDS}


def plain_job_key(job: dict) -> str:
    return json.dumps(plain_job(job), sort_keys=True)


@dataclass(frozen=True)
class CensusSources:
    """The parsed spec v8 5.1 sources."""

    j9_main_jobs: tuple[dict, ...]
    sens_lines: tuple[dict, ...]
    d_jobs: tuple[dict, ...]
    g1_lines: tuple[dict, ...]
    grid192_lines: tuple[dict, ...]


def read_census_sources(root: Path) -> CensusSources:
    """The five sources (sha256 checked).

    Raises:
        KeyInputError: As :func:`read_source`, or a malformed source.
    """
    try:
        j9 = read_source(root, J9_MAIN).decode("utf-8")
        j9_jobs = tuple(json.loads(line)["job"] for line in j9.splitlines() if line.strip())
        sens = json.loads(read_source(root, SENS_KEYS))["lines"]
        d_jobs = json.loads(read_source(root, D_KEYS_BLOB))["jobs"]
        g1 = json.loads(read_source(root, G1_KEYS))["lines"]
        grid192 = json.loads(read_source(root, GRID192_KEYS))["lines"]
    except (KeyError, ValueError) as exc:
        if isinstance(exc, KeyInputError):
            raise
        raise KeyInputError(f"a malformed source: {exc!r}") from exc
    return CensusSources(j9_jobs, tuple(sens), tuple(entry["job"] for entry in d_jobs),
                         tuple(g1), tuple(grid192))


# ------------------------------------------------------------------------- census
def _census_line(stage: str, row: dict, setting: str, source_setting: str | None, role: str,
                 v0_pair: dict) -> dict:
    return {"stage": stage, "job": {**row, "setting": setting},
            "source_setting": source_setting, "role": role, "v0_pair": v0_pair}


def _cj_lines(jobs: tuple[dict, ...]) -> list[dict]:
    lines = []
    for job in jobs:
        setting = CJ_SETTING_MAP.get(job.get("setting"))
        if setting is None:
            raise KeyInputError(f"C-J: setting {job.get('setting')!r} has no edition 8 name")
        row = plain_job(job)
        role = "judged_vs_V0" if setting == "VBN" else "judged_vs_VBN"
        v0_pair = {"job": {**row, "setting": "V0"}, "source": V0_MAIN_SOURCE}
        lines.append(_census_line("C-J", row, setting, job["setting"], role, v0_pair))
    return lines


def _cs_lines(sens_lines: tuple[dict, ...]) -> list[dict]:
    lines = []
    for entry in sens_lines:
        source_setting = entry["job"]["setting"]
        if not source_setting.startswith("VBM") or source_setting == "VBM":
            raise KeyInputError(f"C-S: setting {source_setting!r} is not a VBM<key>")
        setting = "VBN" + source_setting[len("VBM"):]
        role = "judged_vs_V0" if entry.get("judged") else "record"
        lines.append(_census_line("C-S", plain_job(entry["job"]), setting, source_setting,
                                  role, dict(entry["v0_pair"])))
    return lines


def _cd_lines(d_jobs: tuple[dict, ...], grid192_lines: tuple[dict, ...]) -> list[dict]:
    by_key: dict[str, list[dict]] = {}
    for line in grid192_lines:
        by_key.setdefault(plain_job_key(line["job"]), []).append(line)
    pairs = []
    for job in d_jobs:
        found = by_key.get(plain_job_key(job), [])
        if len(found) != 1:
            raise KeyInputError(f"C-D: {len(found)} confirm_b_grid192 lines match {job}")
        pairs.append((plain_job(job), dict(found[0]["v0_pair"])))
    return [_census_line("C-D", row, setting, None, role, v0_pair)
            for setting, role in CD_SETTINGS for row, v0_pair in pairs]


def _cg_lines(g1_lines: tuple[dict, ...]) -> list[dict]:
    lines = []
    for entry in g1_lines:
        source_setting = entry["job"]["setting"]
        if source_setting != "VBM":
            raise KeyInputError(f"C-G: setting {source_setting!r} is not VBM")
        lines.append(_census_line("C-G", plain_job(entry["job"]), "VBN", source_setting,
                                  "judged_vs_V0", dict(entry["v0_pair"])))
    return lines


def census_lines(sources: CensusSources) -> list[dict]:
    """The 1043 census lines in stage order (spec v8 5.1).

    Raises:
        KeyInputError: A stage with another line count, an unknown setting, a C-D job without
            exactly one ``confirm_b_grid192`` line.
    """
    stages = {"C-J": _cj_lines(sources.j9_main_jobs), "C-S": _cs_lines(sources.sens_lines),
              "C-D": _cd_lines(sources.d_jobs, sources.grid192_lines),
              "C-G": _cg_lines(sources.g1_lines)}
    counts = {stage: len(lines) for stage, lines in stages.items()}
    if counts != CENSUS_STAGE_LINES:
        raise KeyInputError(f"census stage lines {counts}, expected {CENSUS_STAGE_LINES}")
    return [line for lines in stages.values() for line in lines]


def census_document(sources: CensusSources) -> dict:
    """``census_keys_ed8.json``: the lines, ``expected_lines`` (``run_v5.sealed_key_jobs``),
    the stage counts, the sources and the 0c' event-name record (counts only)."""
    lines = census_lines(sources)
    return {"rule": "jp3_remedy_spec_v8_rules.md 5.1 (C-J, C-S, C-D, C-G; VBM -> VBN, "
                    "LSM<n> -> LSN<n>, VBM<key> -> VBN<key>)",
            "expected_lines": CENSUS_LINES,
            "stage_lines": dict(CENSUS_STAGE_LINES),
            "sources": {"C-J": {"path": J9_MAIN[0], "sha256": J9_MAIN[1]},
                        "C-S": {"path": SENS_KEYS[0], "sha256": SENS_KEYS[1]},
                        "C-D": {"blob": D_KEYS_BLOB[0], "sha256": D_KEYS_BLOB[1],
                                "v0_pairs": {"path": GRID192_KEYS[0],
                                             "sha256": GRID192_KEYS[1]}},
                        "C-G": {"path": G1_KEYS[0], "sha256": G1_KEYS[1]}},
            "event_resolution": event_resolution_counts(lines),
            "lines": lines}


def document_bytes(document: dict) -> bytes:
    """The key-file bytes (indent 1, LF, UTF-8, trailing newline): one form for the writer and
    the regeneration test."""
    return (json.dumps(document, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


# ------------------------------------------------------------------------- layer rule
@dataclass(frozen=True)
class EventOfJob:
    """The input event of a job (spec v8 6.3): ``kind`` ``steady`` / ``event`` / ``unresolved``;
    the event name and leg, and where each came from (``twin`` / ``default``)."""

    kind: str
    event: str | None = None
    leg: str | None = None
    event_source: str | None = None
    leg_source: str | None = None


def event_of_job(job: dict) -> EventOfJob:
    """The event name and leg of a job: the job twin ``event`` / ``leg``, else the case default
    of ``verdict_cases`` (R12 G4 RR, R14 RE1bF RR, R15 / R16 RE1bF FL); ``steady`` for a
    ``SteadyTwin`` case; ``unresolved`` for an unknown case or one without a default twin."""
    import verdict_cases

    case = verdict_cases.CASES.get(job.get("case"))
    if case is None or case.twin is None:
        return EventOfJob("unresolved")
    if isinstance(case.twin, verdict_cases.SteadyTwin):
        return EventOfJob("steady")
    twin = job.get("twin") or {}
    event_source = "twin" if "event" in twin else "default"
    leg_source = "twin" if "leg" in twin else "default"
    return EventOfJob("event", twin.get("event", case.twin.event),
                      twin.get("leg", case.twin.leg), event_source, leg_source)


def is_e_candidate(job: dict) -> bool:
    """Spec v8 6.3: the job's input event is RE1bF (a depth / ramp variant included)."""
    found = event_of_job(job)
    return found.kind == "event" and found.event in E_CANDIDATE_EVENTS


def stratum_of(job: dict, v0_reapproach_starts: list | None) -> str:
    """The layer of a unit (spec v8 6.3) from its job (the input event) and the
    ``reapproach_starts`` of its V0 pair; the output field ``fast`` is never read.

    ``E``: an E-candidate event row whose V0 pair has a start of the event leg's diagonal leg
    at ``0 <= t`` and ``round(t, 3) <= 0.450`` s after the event; ``N`` otherwise (a steady
    row, an FS24 / G4 row, an empty start list).

    Raises:
        LayerInputError: An event row whose event cannot be named, or an E-candidate row
            without the starts (None) - spec v8 6.3 ``setting_defect``.
    """
    found = event_of_job(job)
    if found.kind == "unresolved":
        raise LayerInputError(f"no event name for {job}")
    if found.kind == "steady" or found.event not in E_CANDIDATE_EVENTS:
        return "N"
    if v0_reapproach_starts is None:
        raise LayerInputError(f"the V0 pair of {job} has no reapproach_starts")
    diagonal = DIAGONAL_LEG[found.leg]
    for start_s, leg in v0_reapproach_starts:
        if leg == diagonal and float(start_s) >= 0.0 and round(float(start_s), 3) <= E_WINDOW_S:
            return "E"
    return "N"


def main_line_starts(line: dict) -> list | None:
    """``event_output.reapproach_starts`` of a main.jsonl V0 line (None = absent)."""
    output = line.get("event_output")
    if not isinstance(output, dict):
        return None
    return output.get("reapproach_starts")


def grid_run_starts(stored_grid: dict, pair: dict) -> list | None:
    """``runs[int(run_id)].reapproach_starts`` (run top level) of a stored grid V0 pair; the
    ``run_id`` of the G1 key file is text, so it is read as an integer.

    Raises:
        LayerInputError: No result of the pair key, a run index out of range or another
            command hash.
    """
    results = [result for result in stored_grid.get("results", [])
               if result.get("key") == pair.get("key")]
    if len(results) != 1:
        raise LayerInputError(f"{len(results)} stored grid results of {pair.get('key')!r}")
    runs = results[0].get("runs", [])
    index = int(pair["run_id"])
    if not 0 <= index < len(runs):
        raise LayerInputError(f"run_id {pair['run_id']!r} out of range")
    run = runs[index]
    if run.get("commands_sha256") != pair.get("v0_commands_sha256"):
        raise LayerInputError(f"stored grid run {pair.get('key')!r} #{index}: hash differs")
    return run.get("reapproach_starts")


def event_resolution_counts(lines: list[dict]) -> dict:
    """0c' (spec v8 4, 6.3): per stage, how the event name and leg of the event rows were set
    (twin / default / unresolved); counts only, no name, leg or layer."""
    record: dict[str, Counter] = {}
    for line in lines:
        counts = record.setdefault(line["stage"], Counter())
        found = event_of_job(line["job"])
        counts["rows"] += 1
        counts[f"kind:{found.kind}"] += 1
        if found.kind == "event":
            counts[f"event_from:{found.event_source}"] += 1
            counts[f"leg_from:{found.leg_source}"] += 1
    return {stage: dict(sorted(counts.items())) for stage, counts in record.items()}


# ------------------------------------------------------------------------- held-out G'
@dataclass(frozen=True)
class Cluster:
    level: str
    leg: str
    fs_kN: float
    event: str
    timing: str

    @property
    def family(self) -> tuple[str, str, str, str]:
        return (self.level, self.timing, self.leg, self.event)

    @property
    def key(self) -> str:
        return f"{self.level}|{self.leg}|Fs{self.fs_kN:g}|{self.event}|{self.timing}"


def _cluster_of(job: dict) -> Cluster:
    twin = job["twin"]
    return Cluster(twin["level"], twin["leg"], float(twin["fs_kN"]), twin["event"],
                   twin["timing"])


def stored_v0_grid_passes(root: Path, file_names: list[str]
                          ) -> dict[tuple[Cluster, float], bool]:
    """The pass flag of every stored V0 grid run, by (cluster, phase), over the grid files
    (a run of the same cluster and phase in two files must agree).

    Raises:
        KeyInputError: A grid file that cannot be read, or two runs that disagree.
    """
    passes: dict[tuple[Cluster, float], bool] = {}
    for name in sorted(set(file_names)):
        try:
            stored = json.loads((root / name).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise KeyInputError(f"stored grid {name}: {exc}") from exc
        for result in stored["results"]:
            runs = result.get("runs") or []
            for run in runs.values() if isinstance(runs, dict) else runs:
                cluster = Cluster(str(result["level"]), str(result["leg"]),
                                  float(result["fs_kN"]), str(run.get("event")),
                                  str(result["timing"]))
                key = (cluster, round(float(run["offset_s"]), 4))
                is_pass = bool(run.get("pass"))
                if passes.setdefault(key, is_pass) != is_pass:
                    raise KeyInputError(f"stored V0 runs of {cluster.key} o{key[1]} disagree")
    return passes


def stored_cluster_passes(root: Path, grid192_lines: tuple[dict, ...]) -> dict[Cluster, bool]:
    """Clean flag of each ``confirm_b_grid192`` cluster: every stored V0 grid run of it passes
    (spec v8 7.1 "모든 오프셋이 V0 통과"; the grid files of the V0 pairs; a cluster has its runs
    at two or four of the stored phases).

    Raises:
        KeyInputError: As :func:`stored_v0_grid_passes`, or a cluster without a stored run.
    """
    runs = stored_v0_grid_passes(root, [line["v0_pair"]["file"] for line in grid192_lines])
    flags_of: dict[Cluster, list[bool]] = {}
    for (cluster, _), is_pass in runs.items():
        flags_of.setdefault(cluster, []).append(is_pass)
    passes: dict[Cluster, bool] = {}
    for line in grid192_lines:
        cluster = _cluster_of(line["job"])
        flags = flags_of.get(cluster)
        if not flags:
            raise KeyInputError(f"cluster {cluster.key}: no stored V0 grid run")
        passes[cluster] = all(flags)
    return passes


def _slot_job(cluster_or_family: Cluster, offset_s: float, *, fs_kN: float | None = None,
              shape: tuple[float, float] | None = None, setting: str) -> dict:
    twin = {"level": cluster_or_family.level, "leg": cluster_or_family.leg,
            "fs_kN": cluster_or_family.fs_kN if fs_kN is None else fs_kN,
            "event": cluster_or_family.event, "timing": cluster_or_family.timing}
    if shape is not None:
        twin.update(depth_m=shape[0], ramp_s=shape[1])
    return {"case": "R12", "eps": 0.0, "offset_s": offset_s, "twin": twin, "setting": setting}


@dataclass(frozen=True)
class SlotFrame:
    """One held-out slot before the draw: the source label, the slot key and its candidate
    conditions (``(offset_s, fs_kN or None, shape or None)``) on a base cluster."""

    source: str
    key: str
    base: Cluster
    candidates: tuple[tuple[float, float | None, tuple[float, float] | None], ...]


def heldout_frames(passes: dict[Cluster, bool]) -> list[SlotFrame]:
    """The 339 slot frames (spec v8 7.1), sorted by (source label, slot key).

    Raises:
        KeyInputError: Other source sizes than 171 / 48 / 120.
    """
    clean = sorted((cluster for cluster, is_clean in passes.items() if is_clean),
                   key=lambda cluster: cluster.key)
    families: dict[tuple[str, str, str, str], list[bool]] = {}
    for cluster, is_clean in passes.items():
        families.setdefault(cluster.family, []).append(is_clean)
    clean_families = sorted(family for family, flags in families.items() if all(flags))
    frames = [SlotFrame("a_phase", cluster.key, cluster,
                        tuple((phase, None, None) for phase in NEW_PHASES_S))
              for cluster in clean]
    frames += [SlotFrame("b_shape", cluster.key, cluster,
                         tuple((phase, None, shape) for shape in SHAPES
                               for phase in ALL_PHASES_S))
               for cluster in clean if cluster.event in E_CANDIDATE_EVENTS]
    for level, timing, leg, event in clean_families:
        base = Cluster(level, leg, 0.0, event, timing)
        for fs_kN in NEW_FS_KN:
            key = f"{level}|{timing}|{leg}|{event}|Fs{fs_kN:g}"
            frames.append(SlotFrame("c_fs", key, base,
                                    tuple((phase, fs_kN, None) for phase in ALL_PHASES_S)))
    sizes = dict(Counter(frame.source for frame in frames))
    if sizes != HELDOUT_SIZES:
        raise KeyInputError(f"held-out source sizes {sizes}, expected {HELDOUT_SIZES}")
    return sorted(frames, key=lambda frame: (frame.source, frame.key))


def _condition_jobs(frame: SlotFrame, condition: tuple, setting: str) -> dict:
    offset_s, fs_kN, shape = condition
    return _slot_job(frame.base, offset_s, fs_kN=fs_kN, shape=shape, setting=setting)


def _check_twin_fields(job: dict) -> None:
    import verdict_cases

    known = {field.name for field in fields(verdict_cases.EventTwin)}
    unknown = sorted(set(job["twin"]) - known)
    if unknown:
        raise KeyInputError(f"twin fields {unknown} are not EventTwin fields")


def heldout_slots(frames: list[SlotFrame], seed: int = HELDOUT_SEED) -> list[dict]:
    """The drawn slots (spec v8 7.2): per slot in order, the condition (``integers``) and the
    A/A order of the other candidates (``permutation``) from one ``default_rng(seed)``."""
    import numpy as np

    rng = np.random.default_rng(seed)
    slots = []
    for frame in frames:
        index = int(rng.integers(len(frame.candidates)))
        condition = frame.candidates[index]
        others = [c for i, c in enumerate(frame.candidates) if i != index]
        order = [others[int(i)] for i in rng.permutation(len(others))]
        job = _condition_jobs(frame, condition, HELDOUT_SETTING)
        _check_twin_fields(job)
        slots.append({"source": frame.source, "slot": frame.key, "condition_index": index,
                      "job": job, "v0_pair": {"job": _condition_jobs(frame, condition, "V0")},
                      "aa_order": [_condition_jobs(frame, other, "V0") for other in order]})
    return slots


def heldout_document(root: Path, sources: CensusSources | None = None) -> dict:
    """``heldout_g_ed8.json`` (spec v8 7.1, 7.2).

    Raises:
        KeyInputError: As :func:`stored_cluster_passes` and :func:`heldout_frames`, or the
            clean clusters are not the 171 G1 clusters.
    """
    sources = sources or read_census_sources(root)
    passes = stored_cluster_passes(root, sources.grid192_lines)
    clean = {cluster for cluster, is_clean in passes.items() if is_clean}
    g1_clusters = {_cluster_of(line["job"]) for line in sources.g1_lines}
    if clean != g1_clusters:
        raise KeyInputError("the clean stored clusters are not the 171 G1 clusters")
    slots = heldout_slots(heldout_frames(passes))
    return {"rule": "jp3_remedy_spec_v8_rules.md 7.1, 7.2 (339 slots; (source, slot) order; "
                    "per slot integers(n) then permutation(n - 1))",
            "seed": HELDOUT_SEED, "rng": "numpy.random.default_rng",
            "setting": HELDOUT_SETTING, "expected_lines": HELDOUT_SLOTS,
            "sizes": dict(HELDOUT_SIZES),
            "candidates": {"a_phase": list(NEW_PHASES_S),
                           "b_shape": {"shapes_m_s": [list(shape) for shape in SHAPES],
                                       "phases_s": list(ALL_PHASES_S)},
                           "c_fs": {"fs_kN": list(NEW_FS_KN), "phases_s": list(ALL_PHASES_S)}},
            "sources": {"clusters": {"path": GRID192_KEYS[0], "sha256": GRID192_KEYS[1]},
                        "clean_check": {"path": G1_KEYS[0], "sha256": G1_KEYS[1]}},
            "lines": slots}


# ------------------------------------------------------------------------- CLI
def write_new(path: Path, data: bytes) -> None:
    """Write a new file (an existing one is refused).

    Raises:
        KeyInputError: The file exists.
    """
    if path.exists():
        raise KeyInputError(f"{path} exists: use a new path")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("census", "heldout"))
    parser.add_argument("--root", type=Path, required=True, help="the checkout with the sources")
    parser.add_argument("--out", type=Path, required=True, help="the key file (a new path)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        sources = read_census_sources(args.root)
        if args.command == "census":
            document = census_document(sources)
        else:
            document = heldout_document(args.root, sources)
        data = document_bytes(document)
        write_new(args.out, data)
    except KeyInputError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}), flush=True)
        return EXIT_INPUT
    except Exception:  # every unexpected failure is a tool error (exit 3), never a result
        traceback.print_exc()
        print(json.dumps({"status": "tool_error", "out": str(args.out)}), flush=True)
        return EXIT_TOOL
    print(json.dumps({"status": "ok", "command": args.command,
                      "lines": len(document["lines"]), "sha256": sha256_of(data),
                      "out": str(args.out)}), flush=True)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
