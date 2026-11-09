"""LAS-b K1 judge: R4c30 order gate bundles Y-0, Y-P, Y-S, Y-T on the reduced harness.

Rules: ``06_analysis/02_control/verif_matrix/las_k1_rules.md`` (control-expert, sealed; LF
sha256 :data:`RULES_K1_SHA256`) and the six A-plan rules files it inherits (all checked before
anything is judged). The rules text wins where this code differs.

What this module owns (``k1_targeted`` imports it):
  - the stored base files (raw sha256, rules 0.2 / appendices) and the key lists recomputed
    from them, each checked against the appendix list sha256 (rules 7);
  - the sub-bundles of rules 3 (who runs which keys with which LAS-b / K1 candidate and
    against which stored hash);
  - the judgement of rules 4: K-0 .. K-4, H-1 .. H-4 (with SK-3 the shadow ``would_block``
    set of Q-0b), C-2 type, P3, C-S, C-F, the READY record and the rules 5 prediction table.

Pairs are made on the full key (``row_key|setting|eps``); times are compared as control
periods ``round(t / 0.1)`` (rules 5.0.2). Grades (rules 4.4 / 4.5): ``fail`` (a C-2 type,
P3, C-S or C-F violation) wins over ``stop`` (a K or H problem, an unpaired, out-of-list or
duplicate line), then ``incomplete`` (missing keys, error lines left after one re-run),
``not_run`` (an earlier bundle did not pass), ``pass``.

Usage (python-dev or dynamics-dev, project root, PowerShell):
  python -I -B 04_scripts/04_hydraulic/coupled/k1_judge.py [--k1-dir <v5/las/k1>]
      [--v5-dir <v5>] [--json-out <json>]
Exit codes: 0 pass, 1 fail, 2 stop or input error, 3 incomplete. The last stdout line is JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import las_revA_judge as ajudge  # noqa: E402  (stdlib only, like las_rev_judge)

rj = ajudge.rj
ROOT = rj.ROOT
V5_DIR = rj.V5_DIR
K1_DIR_RELATIVE = Path("las") / "k1"

RULES_K1_PATH = rj.RULES_PATH.with_name("las_k1_rules.md")
RULES_K1_SHA_PATH = RULES_K1_PATH.with_suffix(".sha256")
RULES_K1_SHA256 = "2742c9760ad55a87eccbf73e84025aafe0171a3555e1f54ab19fab24d888e4a0"
"""``las_k1_rules.sha256`` (LF digest, sealed 2026-11-09 16:24:49 +09:00)."""
RULES_REVA_REV3_PATH = ajudge.RULES_REVA_PATH.with_name("las_revA_targeted_rules_rev3.md")
RULES_REVA_REV3_SHA256 = "98082a368da626f90ce3b0a41f5c74145b4095c155f14b2b2f63eb319352d709"
"""= ``las_revA_diag.RULES_REVA_REV3_SHA256`` (kept here so the judge needs no numpy)."""
SEALED_RULES = (
    *ajudge.SEALED_RULES,
    (RULES_REVA_REV3_PATH, RULES_REVA_REV3_PATH.with_suffix(".sha256"), RULES_REVA_REV3_SHA256),
    (RULES_K1_PATH, RULES_K1_SHA_PATH, RULES_K1_SHA256),
)
"""The six A-plan rules files and the K1 original (later K1 revisions are added here)."""
RULES_FIELDS = (*ajudge.RULES_FIELDS, "rules_revA_rev3_sha256", "rules_k1_sha256")
RULES_VALUES = (*ajudge.RULES_VALUES, RULES_REVA_REV3_SHA256, RULES_K1_SHA256)
"""Rules 2: every line records all seven digests."""

PERIOD_S = 0.1
STROKE_LIMIT_M = rj.STROKE_INCREASE_LIMIT_M
"""C-S: 0.001 m, compared as it is (rules 4.3, no tolerance)."""
F_FLOOR_N = rj.C1_FORCE_FLOOR_N
"""C-F: 10,414.589 N."""
PASSING_VERDICTS = ("pass", "allowed_stop")
P3_ITEM_PREFIXES = ("P3-1", "P3-5")
THREAD_LAYER = "TBB"
FLAT_SOIL_MARGIN_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN"
SKIP_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED"
"""Base name of ``INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order`` in ``event_names``."""

# Stored base files (rules 0.2 / appendices): v5-relative path and raw sha256.
BASE_FILES = {
    "SC": (Path("soil_defer") / "s2d_SC.jsonl",
           "70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa"),
    "RS": (Path("las") / "revA2" / "revA_RS.jsonl",
           "7c407b6ee07b001f5504186fa013193ba6a2992516021f263b2bb537de43875d"),
    "RP0": (Path("las") / "revA2" / "revA_RP0.jsonl",
            "9be02cafce97fa4e4a5f4892d55f5d3d8dcd652de85da0f5bdfbe0a34d127300"),
    "RT": (Path("las") / "revA2" / "revA_RT.jsonl",
           "c72f7e0882c50d86e565366866526ed55073d8bfef5c9f959b82c0e2885afd54"),
}
STORED_L_FILES = {name: path.relative_to(V5_DIR) for name, path in rj.STORED_PATHS.items()}
"""The A-plan pair baselines (las_T1, las_T2, fb_F3, fb_F4) of the Y-0c reference."""

# Appendix list sha256 (rules "부록 목록 규약": sorted keys, LF after each, UTF-8).
LIST_SHA256 = {
    "A": "dc1e65d49bc0ea34fd04fdb7ba4eeceb7fc576ee15de9658dbe26927598b753b",
    "A5": "4cdc9bfe100a4b7d7504df8621eff2fd32660604ab423a61a070ca7a634c5da6",
    "B": "ef6c010dcbc48db71cc79a87d7558f46a65f5f9f544cca2d00fc623b287de684",
    "C": "19c78b49197ac53da5ae50808555c5879aabc90765589ea220830d5588a23950",
    "C_SB2": "56177ba0a566a28b3fb8422872118b8392f4b1bcb06e7b01065ac6bce061c8a5",
    "C_SA1": "7a7caafd5e2b1aba0acbe88e5f85a54c15d2fd699b36d52fe931106a98022d76",
    "D": "4160bddfff318f8c13b36652c3203e89a02159b5fd5a624499aa6ef0940fe933",
}
LIST_COUNTS = {"A": 165, "A5": 5, "B": 40, "C": 30, "C_SB2": 2, "C_SA1": 1, "D": 192}
B_SAMPLE = 40
J2_PATCH_KEY = "D1|H-S-A-J2|G1+J2@FL|T|flat|K1|VB|e0"
BOUNDARY_KEY = "D1|H-S-A|G1+J1@FL|T|flat|K1|VB|e0"
Y_SA_CHANGED = (J2_PATCH_KEY,)
"""Appendix C ``Y-Sa 예측`` = 바뀜 (list sha256 ``C_SA1``)."""
Y_SB_CHANGED = (J2_PATCH_KEY, BOUNDARY_KEY)
"""Appendix C ``Y-Sb 예측`` = 바뀜 (list sha256 ``C_SB2``)."""

BUNDLES = ("Y-0", "Y-P", "Y-S", "Y-T")
K1_OFF, K1_ON = "K1off", "K1on"


@dataclass(frozen=True)
class SubBundle:
    """One row of the rules 3 tables."""

    name: str
    bundle: str
    key_list: str
    las_candidate: str
    k1_candidate: str
    reference: str
    """Where the expected hash comes from: ``SC``, ``RS``, ``L`` (stored L, else RP0), ``RT``
    or the sub-bundle the hash prediction compares with (``Y-0c`` / ``Y-0b``)."""
    record_done: bool


SUB_BUNDLES = {
    sub.name: sub for sub in (
        SubBundle("Y-0a", "Y-0", "A5", "P0", K1_OFF, "SC", False),
        SubBundle("Y-0b", "Y-0", "C", "P5r4", K1_OFF, "RS", True),
        SubBundle("Y-0c", "Y-0", "C", "P0", K1_OFF, "L", True),
        SubBundle("Y-0d", "Y-0", "B", "P0", K1_OFF, "SC", False),
        SubBundle("Y-Pa", "Y-P", "A", "P0", K1_ON, "SC", False),
        SubBundle("Y-Pb", "Y-P", "B", "P0", K1_ON, "SC", False),
        SubBundle("Y-Sa", "Y-S", "C", "P0", K1_ON, "Y-0c", True),
        SubBundle("Y-Sb", "Y-S", "C", "P5r4", K1_ON, "Y-0b", True),
        SubBundle("Y-T", "Y-T", "D", "P5r4", K1_ON, "RT", True),
    )
}
"""``record_done`` follows the line that made the stored hash (S-C lines without, revA2 with)."""
BUNDLE_COUNTS = {"Y-0": 105, "Y-P": 205, "Y-S": 60, "Y-T": 192}
PREDICTED_CHANGES = {"Y-Pa": "A5", "Y-Pb": None, "Y-Sa": "C_SA1", "Y-Sb": "C_SB2", "Y-T": None}
"""H-2 / H-3 / H-4: the key list whose hashes may change (None: none may)."""
SHADOW_BLOCKS = {"Y-0a": "A5", "Y-0b": "C_SB2", "Y-0c": "C_SA1", "Y-0d": None}
"""Q-0b / SK-3: the keys whose shadow ``would_block`` is true."""

STATUS_PASS, STATUS_FAIL, STATUS_STOP = "pass", "fail", "stop"
STATUS_INCOMPLETE, STATUS_NOT_RUN = "incomplete", "not_run"
STATUS_ORDER = (STATUS_FAIL, STATUS_STOP, STATUS_INCOMPLETE, STATUS_NOT_RUN, STATUS_PASS)
EXIT_CODES = {STATUS_PASS: 0, STATUS_FAIL: 1, STATUS_STOP: 2, STATUS_INCOMPLETE: 3,
              STATUS_NOT_RUN: 3}


# ------------------------------------------------------------------------------- small facts
def period_of(t_s: float | None) -> int | None:
    """Rules 5.0.2: whole control periods (29.999999999975 s -> 300)."""
    return None if t_s is None else round(t_s / PERIOD_S)


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key_list_sha256(keys) -> str:
    """Appendix rule: sorted keys, LF after each, UTF-8."""
    return hashlib.sha256("".join(f"{key}\n" for key in sorted(keys)).encode("utf-8")).hexdigest()


def key_sha256(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def stored_key_of(line: dict) -> str:
    """Appendix rule: ``d1.key`` (an R-S verdict case: ``rev.key``)."""
    d1 = line.get("d1")
    return d1["key"] if d1 else rj.rev_of(line)["key"]


def k1_of(line: dict) -> dict:
    """The ``k1`` block; an error line from the pool keeps the entry inside ``rev``."""
    return line.get("k1") or rj.rev_of(line).get("k1") or {}


def key_of(line: dict) -> str | None:
    return rj.rev_of(line).get("key")


def has_event(line: dict, name: str) -> bool:
    return bool((line.get("event_names") or {}).get(name))


def seal_problems() -> list[str]:
    return rj.sealed_rules_problems(SEALED_RULES)


# ------------------------------------------------------------------------------- base files
@dataclass
class Bases:
    """The stored base lines by key and the key lists recomputed from them."""

    by_file: dict[str, dict[str, dict]] = field(default_factory=dict)
    stored_l: dict = field(default_factory=dict)
    lists: dict[str, list[str]] = field(default_factory=dict)
    paths: dict[str, Path] = field(default_factory=dict)
    sha256: dict[str, str] = field(default_factory=dict)


def _sc_period_difference(line: dict) -> int | None:
    soil = (line.get("s2d") or {}).get("soil") or {}
    n_P, n_S = period_of(soil.get("t_P_s")), period_of(soil.get("t_S_s"))
    return None if n_P is None or n_S is None else n_P - n_S


def recompute_lists(sc_lines: list[dict], rs_lines: list[dict], rt_lines: list[dict]
                    ) -> dict[str, list[str]]:
    """Appendices A .. D from the stored files (rules 7: recomputed, never typed in).

    A = S-C keys with ``INFO_LOC_FLAT_SOIL_MARGIN``; A5 = those with ``n_P - n_S <= 0`` (the
    keys the gate blocks); B = the first 40 of the other S-C keys by sha256(key) hex; C = the
    R-S keys; D = the R-T keys. C_SA1 / C_SB2 are the appendix C prediction columns."""
    r4 = sorted(stored_key_of(line) for line in sc_lines
                if has_event(line, FLAT_SOIL_MARGIN_EVENT))
    blocked = sorted(stored_key_of(line) for line in sc_lines
                     if has_event(line, FLAT_SOIL_MARGIN_EVENT)
                     and (_sc_period_difference(line) is None
                          or _sc_period_difference(line) <= 0))
    others = [stored_key_of(line) for line in sc_lines
              if not has_event(line, FLAT_SOIL_MARGIN_EVENT)]
    sample = sorted(others, key=key_sha256)[:B_SAMPLE]
    return {"A": r4, "A5": blocked, "B": sample,
            "C": sorted(stored_key_of(line) for line in rs_lines),
            "C_SB2": sorted(Y_SB_CHANGED), "C_SA1": sorted(Y_SA_CHANGED),
            "D": sorted(stored_key_of(line) for line in rt_lines)}


def list_problems(lists: dict[str, list[str]]) -> list[str]:
    """Rules 7: each recomputed list is its appendix list (count and sha256)."""
    problems = []
    for name, expected in LIST_SHA256.items():
        keys = lists.get(name, [])
        digest = key_list_sha256(keys)
        if len(keys) != LIST_COUNTS[name] or len(set(keys)) != len(keys) or digest != expected:
            problems.append(f"list {name}: {len(keys)} keys, sha256 {digest} != appendix "
                            f"{expected}")
    return problems


def _by_key(lines: list[dict], name: str) -> tuple[dict[str, dict], list[str]]:
    out, problems = {}, []
    for line in lines:
        if rj.is_error(line):
            problems.append(f"{name}: an error line")
            continue
        key = stored_key_of(line)
        if key in out:
            problems.append(f"{name}: key {key} twice")
        out[key] = line
    return out, problems


def load_bases(v5_dir: Path = V5_DIR) -> tuple[Bases, list[str]]:
    """The stored files (raw sha256 checked), the stored L lines and the recomputed lists.

    Returns:
        (bases, problems); any problem means the lists or references cannot be trusted.
    """
    bases, problems = Bases(), []
    lines_by_file = {}
    for name, (relative, expected) in BASE_FILES.items():
        path = v5_dir / relative
        bases.paths[name] = path
        if not path.exists():
            problems.append(f"missing {path}")
            continue
        bases.sha256[name] = raw_sha256(path)
        if bases.sha256[name] != expected:
            problems.append(f"{path.name} sha256 {bases.sha256[name]} != {expected}")
        lines_by_file[name] = rj.read_lines(path)
        bases.by_file[name], found = _by_key(lines_by_file[name], name)
        problems += found
    try:
        bases.stored_l = rj.load_stored({name: v5_dir / relative
                                         for name, relative in STORED_L_FILES.items()})
    except (OSError, ValueError) as exc:
        problems.append(f"stored L lines: {exc}")
    for name, relative in STORED_L_FILES.items():
        path = v5_dir / relative
        bases.paths[name] = path
        if path.exists():
            bases.sha256[name] = raw_sha256(path)
    if len(lines_by_file) == len(BASE_FILES):
        bases.lists = recompute_lists(lines_by_file["SC"], lines_by_file["RS"],
                                      lines_by_file["RT"])
        problems += list_problems(bases.lists)
    return bases, problems


def sub_keys(sub: SubBundle, bases: Bases) -> list[str]:
    return list(bases.lists.get(sub.key_list, []))


def reference_line(sub: SubBundle, key: str, bases: Bases) -> tuple[dict | None, str | None]:
    """(stored line, file name) whose hash a line of ``sub`` is checked against; the Y-S
    sub-bundles compare with run lines (:func:`expected_hash`)."""
    if sub.reference in ("SC", "RS", "RT"):
        return bases.by_file.get(sub.reference, {}).get(key), sub.reference
    if sub.reference == "L":
        line = rj.stored_line(bases.stored_l, key) if bases.stored_l else None
        if line is not None:
            return line, rj.source_of(bases.stored_l, key)
        return bases.by_file.get("RP0", {}).get(key), "RP0"
    return None, None


def reference_file_of(sub: SubBundle, key: str, bases: Bases) -> tuple[str | None, str | None]:
    """(path, raw sha256) of the line's base file (rules 2: recorded on every line)."""
    reference = sub.reference
    if reference in ("Y-0c", "Y-0b"):
        reference = SUB_BUNDLES[reference].reference
        sub = SUB_BUNDLES[sub.reference]
    _, name = reference_line(sub, key, bases)
    if name is None:
        return None, None
    path = bases.paths.get(name)
    return (None if path is None else str(path)), bases.sha256.get(name)


# ------------------------------------------------------------------------------- the run lines
@dataclass
class SubLines:
    """Finished and error lines of one sub-bundle, keyed by the full key."""

    finished: dict[str, dict] = field(default_factory=dict)
    error_keys: dict[str, int] = field(default_factory=dict)
    resumed: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    out_of_list: list[str] = field(default_factory=list)
    wrong_candidate: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    errors_left: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.finished) + sum(self.error_keys.values())


def read_run_lines(k1_dir: Path) -> list[dict]:
    """Every line of ``k1_*.jsonl`` in ``k1_dir`` (resume files included)."""
    lines = []
    for path in sorted(k1_dir.glob("k1_*.jsonl")):
        lines += rj.read_lines(path)
    return lines


def split_lines(lines: list[dict], bases: Bases) -> dict[str, SubLines]:
    """Rules 7: duplicates, out-of-list keys, other candidates, missing keys, errors left."""
    out = {name: SubLines() for name in SUB_BUNDLES}
    for line in lines:
        block = k1_of(line)
        sub = SUB_BUNDLES.get(block.get("sub_bundle"))
        key = key_of(line)
        if sub is None:
            out.setdefault("unknown", SubLines()).out_of_list.append(str(key))
            continue
        part = out[sub.name]
        if key not in set(sub_keys(sub, bases)):
            part.out_of_list.append(str(key))
            continue
        if (block.get("las_candidate"), block.get("k1_candidate")) != (sub.las_candidate,
                                                                       sub.k1_candidate):
            part.wrong_candidate.append(str(key))
            continue
        if rj.is_error(line):
            part.error_keys[key] = part.error_keys.get(key, 0) + 1
            continue
        if key in part.finished:
            part.duplicates.append(key)
        part.finished[key] = line
        if block.get("resume"):
            part.resumed.append(key)
    for name, sub in SUB_BUNDLES.items():
        part = out[name]
        for key in sub_keys(sub, bases):
            if key in part.finished:
                continue
            (part.errors_left if key in part.error_keys else part.missing).append(key)
    return out


def resume_keys(lines: list[dict], sub_name: str) -> list[str]:
    """SK-2: keys of a sub-bundle with exactly one error line and no finished line (the
    batch re-ran nothing for them); a key with two error lines was re-run already."""
    finished, errors = set(), {}
    for line in lines:
        if k1_of(line).get("sub_bundle") != sub_name:
            continue
        key = key_of(line)
        if rj.is_error(line):
            errors[key] = errors.get(key, 0) + 1
        else:
            finished.add(key)
    return sorted(key for key, count in errors.items() if count == 1 and key not in finished)


# ------------------------------------------------------------------------------- K checks
def identity_signature(line: dict) -> tuple:
    """Rules 2 values that must be equal over every line (K-0)."""
    block = k1_of(line)
    identity = block.get("identity") or {}
    rules = tuple(block.get(name) for name in RULES_FIELDS)
    return (identity.get("git_head"), identity.get("code_diff_sha256"),
            json.dumps(identity.get("sha256"), sort_keys=True), rules,
            json.dumps(identity.get("threads"), sort_keys=True))


def k0_cross_problems(lines: list[dict]) -> list[str]:
    """K-0 between lines: one identity over all finished lines of all bundles (each line's
    own values: :func:`identity_value_problems`)."""
    signatures: dict[tuple, int] = {}
    for line in lines:
        signature = identity_signature(line)
        signatures[signature] = signatures.get(signature, 0) + 1
    if len(signatures) > 1:
        return [f"K-0: {len(signatures)} run identities over the lines "
                f"(line counts {sorted(signatures.values())})"]
    return []


EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
THREAD_VARIABLES = ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                    "NUMBA_NUM_THREADS")
ALLOWED_DIRTY = (".gitattributes", "00_docs/decision_log.md",
                 "04_scripts/04_hydraulic/coupled/test_k1.py", "05_tests/unit/test_c2_k1.py")
"""Rules 2: documents and this bundle's tests (never imported by a run); the code diff must
be empty all the same, so a dirty test file under ``04_scripts`` still fails K-0."""


def identity_value_problems(block: dict) -> list[str]:
    identity = block.get("identity") or {}
    problems = []
    if identity.get("code_diff_sha256") != EMPTY_SHA256:
        problems.append("code_diff_sha256 not empty")
    dirty = [name for name in identity.get("dirty_files") or () if name not in ALLOWED_DIRTY]
    if dirty:
        problems.append(f"dirty {dirty}")
    threads = identity.get("threads") or {}
    wrong = [name for name in THREAD_VARIABLES if threads.get(name) != "1"]
    if wrong or threads.get("MKL_THREADING_LAYER") != THREAD_LAYER:
        problems.append(f"threads {threads}")
    rules = {name: block.get(name) for name in RULES_FIELDS}
    if rules != dict(zip(RULES_FIELDS, RULES_VALUES, strict=True)):
        problems.append("rules sha256 are not the sealed seven")
    return problems


def _decision_problems(key: str, decision: dict) -> list[str]:
    """K-1 / rules 7: a decision holds t_P and t_S and its period numbers agree."""
    t_P_s, t_S_s = decision.get("t_P_s"), decision.get("t_S_s")
    if t_P_s is None or t_S_s is None:
        return [f"K-1 {key}: decision at {decision.get('t_loc_s')} without t_P / t_S"]
    n_P, n_S = period_of(t_P_s), period_of(t_S_s)
    if (decision.get("n_P"), decision.get("n_S"), decision.get("dP")) != (n_P, n_S, n_P - n_S):
        return [f"K-1 {key}: n_P / n_S / dP {decision.get('n_P')} / {decision.get('n_S')} / "
                f"{decision.get('dP')} != {n_P} / {n_S} / {n_P - n_S}"]
    expected_block = bool(decision.get("r4_due_without_gate")) and n_P <= n_S
    if bool(decision.get("would_block")) != expected_block:
        return [f"K-1 {key}: would_block {decision.get('would_block')} != {expected_block}"]
    return []


def evaluated_loc_periods(block: dict) -> list[int]:
    """LOCs at which R4 was evaluated, from the harness witness of
    ``_apply_slope_clearance_margin`` (rules 7: not the slope margin, R4 on, a soil mode)."""
    return [period_of(call["t_s"]) for call in block.get("loc_calls") or ()
            if not call["slope_margin_fired"] and call["r4_on"]
            and call["t_S_s"] is not None]


def k1_problems(line: dict) -> list[str]:
    """K-1: ``enabled`` is the candidate's, every evaluated LOC has its decision (witness
    periods = decision periods), decisions complete, events agree."""
    block, key = k1_of(line), key_of(line)
    for name in ("enabled", "decisions", "r4_applied", "would_block_any", "loc_calls"):
        if name not in block:
            return [f"K-1 {key}: k1.{name} missing"]
    problems = []
    is_on = block["k1_candidate"] == K1_ON
    if block["enabled"] is not is_on or block.get("setting") is not is_on:
        problems.append(f"K-1 {key}: enabled {block['enabled']} / setting "
                        f"{block.get('setting')} for {block['k1_candidate']}")
    decisions = block["decisions"]
    witness = evaluated_loc_periods(block)
    if [period_of(d.get("t_loc_s")) for d in decisions] != witness:
        problems.append(f"K-1 {key}: decisions at {[d.get('t_loc_s') for d in decisions]}, "
                        f"evaluated LOC periods {witness}")
    for decision in decisions:
        problems += _decision_problems(key, decision)
    applied = sum(1 for d in decisions if d.get("applied"))
    events = (line.get("event_names") or {})
    if applied != int(events.get(FLAT_SOIL_MARGIN_EVENT) or 0):
        problems.append(f"K-1 {key}: {applied} applied decisions, "
                        f"{events.get(FLAT_SOIL_MARGIN_EVENT)} {FLAT_SOIL_MARGIN_EVENT} events")
    if block["r4_applied"] is not (applied > 0):
        problems.append(f"K-1 {key}: r4_applied {block['r4_applied']}, {applied} applied")
    if block["would_block_any"] is not any(d.get("would_block") for d in decisions):
        problems.append(f"K-1 {key}: would_block_any {block['would_block_any']}")
    return problems


def k23_problems(line: dict) -> list[str]:
    """K-2 (K1off: applied = due, no skip event) and K-3 (K1on: applied = due and not
    blocked, one skip event per blocked decision)."""
    block, key = k1_of(line), key_of(line)
    is_on = block.get("k1_candidate") == K1_ON
    problems = []
    for decision in block.get("decisions") or ():
        due = bool(decision.get("r4_due_without_gate"))
        expected = due and not (is_on and bool(decision.get("would_block")))
        if bool(decision.get("applied")) != expected:
            label = "K-3" if is_on else "K-2"
            problems.append(f"{label} {key}: applied {decision.get('applied')} at "
                            f"{decision.get('t_loc_s')}, expected {expected}")
    skips = int((line.get("event_names") or {}).get(SKIP_EVENT) or 0)
    blocked = sum(1 for d in block.get("decisions") or ()
                  if d.get("r4_due_without_gate") and d.get("would_block"))
    expected_skips = blocked if is_on else 0
    if skips != expected_skips:
        label = "K-3" if is_on else "K-2"
        problems.append(f"{label} {key}: {skips} {SKIP_EVENT} events, expected {expected_skips}")
    return problems


def k1_off_reference_hash(sub: SubBundle, key: str, parts: dict[str, SubLines],
                          bases: Bases) -> str | None:
    """K-4: the K1off hash of the same key and LAS-b candidate: a K1off run line when there is
    one (Y-0a / Y-0d / Y-0c / Y-0b), else the stored line of that candidate (S-C P0, revA2
    R-T P5r4) the Y-0 bit tests tie to K1off."""
    for name, other in SUB_BUNDLES.items():
        if (other.k1_candidate == K1_OFF and other.las_candidate == sub.las_candidate
                and key in parts[name].finished):
            return parts[name].finished[key]["commands_sha256"]
    if sub.las_candidate == "P0" and key in bases.by_file.get("SC", {}):
        return bases.by_file["SC"][key]["commands_sha256"]
    if sub.las_candidate == "P5r4" and key in bases.by_file.get("RT", {}):
        return bases.by_file["RT"][key]["commands_sha256"]
    return None


def k4_problems(sub: SubBundle, line: dict, parts, bases: Bases) -> list[str]:
    block, key = k1_of(line), key_of(line)
    if sub.k1_candidate != K1_ON or block.get("would_block_any"):
        return []
    reference = k1_off_reference_hash(sub, key, parts, bases)
    if reference is None:
        return [f"K-4 {key}: no K1off line of {sub.las_candidate}"]
    if line["commands_sha256"] != reference:
        return [f"K-4 {key}: hash {line['commands_sha256'][:12]} != K1off {reference[:12]}"]
    return []


# ------------------------------------------------------------------------------- H checks
def expected_hash(sub: SubBundle, key: str, parts: dict[str, SubLines], bases: Bases
                  ) -> str | None:
    """The hash the line's prediction compares with (rules 3 tables)."""
    if sub.reference in SUB_BUNDLES:
        line = parts[sub.reference].finished.get(key)
        return None if line is None else line["commands_sha256"]
    line, _ = reference_line(sub, key, bases)
    return None if line is None else line["commands_sha256"]


def changed_keys(sub: SubBundle, parts, bases: Bases) -> tuple[list[str], list[str]]:
    """(changed, unpaired) keys of a sub-bundle against :func:`expected_hash`."""
    changed, unpaired = [], []
    for key, line in sorted(parts[sub.name].finished.items()):
        reference = expected_hash(sub, key, parts, bases)
        if reference is None:
            unpaired.append(key)
        elif line["commands_sha256"] != reference:
            changed.append(key)
    return changed, unpaired


def predicted_changed(sub: SubBundle, bases: Bases) -> list[str]:
    name = PREDICTED_CHANGES.get(sub.name)
    return [] if name is None else sorted(bases.lists.get(name, []))


def shadow_blocks(sub: SubBundle, parts) -> list[str]:
    return sorted(key for key, line in parts[sub.name].finished.items()
                  if k1_of(line).get("would_block_any"))


def expected_shadow(sub: SubBundle, bases: Bases) -> list[str]:
    name = SHADOW_BLOCKS.get(sub.name)
    return [] if name is None else sorted(bases.lists.get(name, []))


# ------------------------------------------------------------------------------- C checks
def _verdict_extra(cand: dict, base: dict) -> list[str]:
    """C-2 type (a) as the K1 rules word it: a verdict leaving ``pass`` / ``allowed_stop``."""
    if rj.is_verdict_case(base):
        return []
    base_verdict = rj.need(base, "d1", "verdict")
    verdict = rj.need(cand, "d1", "verdict")
    if base_verdict in PASSING_VERDICTS and verdict not in PASSING_VERDICTS:
        return [f"verdict {base_verdict} -> {verdict}"]
    return []


def c2_violations(cand: dict, base: dict) -> list[str]:
    """C-2 type (a) .. (c) (``las_rev_judge.pair_violations``) + the wider (a) verdict rule."""
    found = rj.pair_violations(cand, base)
    for text in _verdict_extra(cand, base):
        if text not in found:
            found.append(text)
    return found


def p3_record(cand: dict) -> bool | None:
    """P3: every ``d1.items`` entry named ``P3-1*`` / ``P3-5*`` is true; None = no such item."""
    if rj.is_verdict_case(cand):
        return None
    items = rj.need(cand, "d1", "items")
    values = [value for name, value in items.items() if name.startswith(P3_ITEM_PREFIXES)]
    if not values:
        return None
    return all(value is True for value in values)


def ready_s(line: dict) -> float | None:
    return ((line.get("values") or {}).get("times") or {}).get("t_first_ready_s")


def pair_record(cand: dict, base: dict) -> dict:
    """C-2 type, P3, C-S, C-F and the READY record of one pair (rules 4.3).

    Raises:
        rj.MissingField: A criteria field is missing (undecidable: a stop).
    """
    record = {"key": key_of(cand), "changed": cand["commands_sha256"] != base["commands_sha256"],
              "c2": c2_violations(cand, base), "P3": p3_record(cand)}
    if rj.is_verdict_case(base):
        record.update(stroke_increase_m=None, cs_fail=False, cf_fail=False, F_base_N=None,
                      F_cand_N=None)
    else:
        increase = rj.stroke_increase_m(cand, base)
        if increase is None:
            raise rj.MissingField("d1.stroke_max_m None on a D-1 pair")
        f_base = rj.need(base, "d1", "F_judged_min_N")
        f_cand = rj.need(cand, "d1", "F_judged_min_N")
        record.update(stroke_increase_m=increase, cs_fail=increase > STROKE_LIMIT_M,
                      F_base_N=f_base, F_cand_N=f_cand,
                      cf_fail=(f_base is not None and f_base >= F_FLOOR_N
                               and (f_cand is None or f_cand < F_FLOOR_N)))
    ready_cand, ready_base = ready_s(cand), ready_s(base)
    both = ready_cand is not None and ready_base is not None
    record["ready_dt_s"] = ready_cand - ready_base if both else None
    record["ready_dt_periods"] = (period_of(ready_cand) - period_of(ready_base)) if both else None
    record["fail"] = bool(record["c2"] or record["P3"] is False or record["cs_fail"]
                          or record["cf_fail"])
    return record


def pair_base(sub: SubBundle, key: str, parts, bases: Bases) -> dict | None:
    """Rules 4.3 pairs: Y-P against the stored S-C P0 line, Y-Sb against Y-Sa."""
    if sub.bundle == "Y-P":
        return bases.by_file.get("SC", {}).get(key)
    if sub.name == "Y-Sb":
        return parts["Y-Sa"].finished.get(key)
    return None


def judged_pairs(sub: SubBundle, parts, bases: Bases) -> tuple[list[dict], list[str], list[str]]:
    """(pair records, unpaired keys, stop problems) of Y-P changed lines and every Y-S pair."""
    if sub.bundle not in ("Y-P",) and sub.name != "Y-Sb":
        return [], [], []
    records, unpaired, problems = [], [], []
    for key, cand in sorted(parts[sub.name].finished.items()):
        base = pair_base(sub, key, parts, bases)
        if base is None:
            unpaired.append(key)
            continue
        if sub.bundle == "Y-P" and cand["commands_sha256"] == base["commands_sha256"]:
            continue  # rules 4.3: Y-P judges the lines whose hash changed
        try:
            records.append(pair_record(cand, base))
        except rj.MissingField as exc:
            problems.append(f"{sub.name} {key}: missing {exc}")
    return records, unpaired, problems


# ------------------------------------------------------------------------------- judgement
@dataclass
class SubResult:
    name: str
    lines: int = 0
    stops: list[str] = field(default_factory=list)
    fails: list[str] = field(default_factory=list)
    incomplete: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    shadow: list[str] = field(default_factory=list)
    pairs: list[dict] = field(default_factory=list)
    unpaired: list[str] = field(default_factory=list)
    resumed: list[str] = field(default_factory=list)
    p3_not_applicable: int = 0

    def to_dict(self) -> dict:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


def _structure_problems(name: str, part: SubLines) -> list[str]:
    problems = []
    if part.duplicates:
        problems.append(f"{name}: duplicate lines {part.duplicates[:5]}")
    if part.out_of_list:
        problems.append(f"{name}: keys outside the list {part.out_of_list[:5]}")
    if part.wrong_candidate:
        problems.append(f"{name}: lines of another candidate {part.wrong_candidate[:5]}")
    return problems


def _line_problems(sub: SubBundle, line: dict, parts, bases: Bases) -> list[str]:
    block, key = k1_of(line), key_of(line)
    problems = identity_value_problems(block)
    problems = [f"K-0 {key}: {problems}"] if problems else []
    problems += k1_problems(line)
    problems += k23_problems(line)
    problems += k4_problems(sub, line, parts, bases)
    problems += [f"tag {key}: {text}" for text in rj.tag_problems(line)]
    _, sha = reference_file_of(sub, key, bases)
    if sha is not None and block.get("base_file_sha256") != sha:
        problems.append(f"K-0 {key}: base file sha256 {block.get('base_file_sha256')} != {sha}")
    s2d = block.get("s2d_settings") or {}
    if s2d.get("mode_defer_periods") != 0 or s2d.get("mode_defer_shadow") is not False:
        problems.append(f"K-1 {key}: S2D not off (rules 3): {s2d}")
    return problems


def judge_sub(sub: SubBundle, parts: dict[str, SubLines], bases: Bases) -> SubResult:
    part = parts[sub.name]
    result = SubResult(sub.name, lines=part.count, resumed=list(part.resumed))
    result.stops += _structure_problems(sub.name, part)
    for line in part.finished.values():
        result.stops += _line_problems(sub, line, parts, bases)
    if part.missing:
        result.incomplete.append(f"{len(part.missing)} keys not run: {part.missing[:5]}")
    if part.errors_left:
        result.incomplete.append(f"{len(part.errors_left)} keys with error lines only: "
                                 f"{part.errors_left[:5]}")
    result.changed, result.unpaired = changed_keys(sub, parts, bases)
    _hash_predictions(sub, parts, bases, result)
    records, unpaired, problems = judged_pairs(sub, parts, bases)
    result.pairs, result.stops = records, result.stops + problems
    result.unpaired += unpaired
    if result.unpaired:
        result.stops.append(f"{sub.name}: unpaired keys {sorted(set(result.unpaired))[:5]}")
    for record in records:
        if record["P3"] is None:
            result.p3_not_applicable += 1
        if record["fail"]:
            result.fails.append(_fail_text(record))
    return result


def _hash_predictions(sub: SubBundle, parts, bases: Bases, result: SubResult) -> None:
    """H-1 (with SK-3 the shadow set of Q-0b), H-2, H-3, H-4 on the finished keys."""
    finished = set(parts[sub.name].finished)
    if sub.bundle == "Y-0":
        if result.changed:
            result.stops.append(f"H-1 {sub.name}: hash changed {result.changed[:5]}")
        result.shadow = shadow_blocks(sub, parts)
        expected = [key for key in expected_shadow(sub, bases) if key in finished]
        if result.shadow != expected:
            result.stops.append(f"SK-3 {sub.name}: shadow would_block {result.shadow} != Q-0b "
                                f"{expected}")
        return
    expected = [key for key in predicted_changed(sub, bases) if key in finished]
    if result.changed != expected:
        rule = {"Y-P": "H-2", "Y-S": "H-3", "Y-T": "H-4"}[sub.bundle]
        result.stops.append(f"{rule} {sub.name}: changed {result.changed} != predicted "
                            f"{expected}")


def _fail_text(record: dict) -> str:
    parts = []
    if record["c2"]:
        parts.append(f"C-2 {record['c2']}")
    if record["P3"] is False:
        parts.append("P3")
    if record["cs_fail"]:
        parts.append(f"C-S +{record['stroke_increase_m'] * 1e3:.3f} mm")
    if record["cf_fail"]:
        parts.append(f"C-F {record['F_cand_N']}")
    return f"{record['key']}: {'; '.join(parts)}"


def bundle_status(results: list[SubResult]) -> str:
    if any(result.fails for result in results):
        return STATUS_FAIL
    if any(result.stops for result in results):
        return STATUS_STOP
    if any(result.incomplete for result in results):
        return STATUS_INCOMPLETE
    return STATUS_PASS


def worst_status(statuses) -> str:
    statuses = list(statuses)
    for status in STATUS_ORDER:
        if status in statuses:
            return status
    return STATUS_PASS


def judge(lines: list[dict], bases: Bases, base_problems: list[str] | None = None,
          seal: list[str] | None = None) -> dict:
    """Rules 4 over the run lines of every bundle; ``status`` per bundle and overall."""
    if base_problems or seal:
        return {"status": STATUS_STOP, "bundles": {}, "input_problems":
                list(seal or []) + list(base_problems or [])}
    parts = split_lines(lines, bases)
    finished = [line for part in parts.values() for line in part.finished.values()]
    cross = k0_cross_problems(finished)
    out = {"bundles": {}, "subs": {}, "k0_cross": cross,
           "unknown_lines": (parts.get("unknown") or SubLines()).out_of_list}
    earlier_passed = True
    for bundle in BUNDLES:
        subs = [sub for sub in SUB_BUNDLES.values() if sub.bundle == bundle]
        results = [judge_sub(sub, parts, bases) for sub in subs]
        lines_seen = sum(result.lines for result in results)
        if lines_seen == 0 and not earlier_passed:
            status = STATUS_NOT_RUN
        else:
            status = bundle_status(results)
            if status == STATUS_PASS and cross:
                status = STATUS_STOP
        out["bundles"][bundle] = {"status": status, "lines": lines_seen,
                                  "expected_lines": BUNDLE_COUNTS[bundle]}
        out["subs"].update({result.name: result.to_dict() for result in results})
        earlier_passed = earlier_passed and status == STATUS_PASS
    statuses = [entry["status"] for entry in out["bundles"].values()]
    if out["unknown_lines"]:
        statuses.append(STATUS_STOP)
    out["status"] = worst_status(statuses)
    out["predictions"] = prediction_table(parts, bases, out)
    return out


# ------------------------------------------------------------------------------- predictions
SOFT_GROUPS = ("H-S-1", "H-S-C", "H-R-A-S1")


def is_genuine_soft(key: str) -> bool:
    """Q-0c rows: H-S-0 J1 / J2 flat, H-S-1, H-S-C, H-R-A-S1."""
    fields = key.split("|")
    if len(fields) < 5 or fields[0] != "D1":
        return False
    group, floor, path = fields[1], fields[2], fields[4]
    if group in SOFT_GROUPS:
        return True
    return group == "H-S-0" and floor in ("J1", "J2") and path == "flat"


def _stroke_m(line: dict | None) -> float | None:
    return None if line is None else ((line.get("d1") or {}).get("stroke_max_m"))


def _difference_mm(cand: dict | None, base: dict | None) -> float | None:
    value, base_value = _stroke_m(cand), _stroke_m(base)
    if value is None or base_value is None:
        return None
    return (value - base_value) * 1e3


def _row(name: str, prediction: str, observed, holds: bool | None) -> dict:
    return {"id": name, "prediction": prediction, "observed": observed, "holds": holds}


def prediction_table(parts: dict[str, SubLines], bases: Bases, result: dict) -> list[dict]:
    """Rules 5 predictions against the lines (information; H is judged above)."""
    subs = result["subs"]
    rows = []
    y0 = [subs[name] for name in ("Y-0a", "Y-0b", "Y-0c", "Y-0d")]
    y0_lines = sum(len(parts[name].finished) for name in ("Y-0a", "Y-0b", "Y-0c", "Y-0d"))
    y0_equal = y0_lines - sum(len(sub["changed"]) for sub in y0)
    rows.append(_row("Q-0a", "105/105 hashes equal", f"{y0_equal}/{y0_lines}",
                     y0_lines == BUNDLE_COUNTS["Y-0"] and y0_equal == y0_lines))
    shadow = {sub["name"]: sub["shadow"] for sub in y0}
    expected = {name: expected_shadow(SUB_BUNDLES[name], bases) for name in shadow}
    rows.append(_row("Q-0b", expected, shadow, shadow == expected))
    rows.append(_q0c(parts))
    rows += _yp_rows(parts, bases, subs)
    rows += _ys_rows(parts, subs)
    yt = parts["Y-T"]
    empty = sum(1 for line in yt.finished.values() if not k1_of(line).get("decisions"))
    rows.append(_row("Q-T1", "192/192 equal, decisions empty 192",
                     {"equal": len(yt.finished) - len(subs["Y-T"]["changed"]),
                      "empty_decisions": empty},
                     len(yt.finished) == 192 and not subs["Y-T"]["changed"] and empty == 192))
    rows.append(_row("Q-C1..Q-C4", "S-Ch (separate sealed plan)", "not judged here", None))
    return rows


def _q0c(parts) -> dict:
    values = {}
    for name in ("Y-0b", "Y-0c"):
        for key, line in parts[name].finished.items():
            if is_genuine_soft(key):
                for decision in k1_of(line).get("decisions") or ():
                    values[f"{name} {key}"] = decision.get("dP")
    low = {label: dp for label, dp in values.items() if dp is None or dp < 20}
    return _row("Q-0c", "genuine soft rows dP >= +20", {"rows": len(values), "below": low},
                bool(values) and not low)


def _yp_rows(parts, bases: Bases, subs: dict) -> list[dict]:
    pairs = {pair["key"]: pair for pair in subs["Y-Pa"]["pairs"]}
    changed = subs["Y-Pa"]["changed"]
    expected = sorted(bases.lists.get("A5", []))
    rows = [_row("Q-P1", "changed = appendix A 5 keys", changed, changed == expected)]
    drops = {key: (None if pairs.get(key) is None or pairs[key]["stroke_increase_m"] is None
                   else round(-pairs[key]["stroke_increase_m"] * 1e3, 3)) for key in changed}
    rows.append(_row("Q-P2", "5 keys stroke 25..35 mm lower, C-S 0", drops,
                     bool(drops) and all(value is not None and 25.0 <= value <= 35.0
                                         for value in drops.values())))
    clean = [key for key in changed if pairs.get(key) and not pairs[key]["c2"]
             and pairs[key]["P3"] is not False]
    rows.append(_row("Q-P3", "5 keys no C-2 / P3 / new FAULT-WARN", f"{len(clean)}/{len(changed)}",
                     bool(changed) and len(clean) == len(changed)))
    ready = {key: (pairs.get(key) or {}).get("ready_dt_s") for key in changed}
    rows.append(_row("Q-P4", "READY dt <= 0 and >= -5 s", ready,
                     bool(ready) and all(v is not None and -5.0 <= v <= 0.0
                                         for v in ready.values())))
    return rows


def _ys_rows(parts, subs: dict) -> list[dict]:
    sa, sb = parts["Y-Sa"].finished, parts["Y-Sb"].finished
    boundary = _difference_mm(sb.get(BOUNDARY_KEY), sa.get(BOUNDARY_KEY))
    rows = [_row("Q-S1", "boundary key stroke delta in [-1, +1] mm (median +0.1)", boundary,
                 None if boundary is None else -1.0 <= boundary <= 1.0)]
    patch = _difference_mm(sb.get(J2_PATCH_KEY), sa.get(J2_PATCH_KEY))
    blocked = [all(d.get("would_block") and not d.get("applied")
                   for d in k1_of(line).get("decisions") or [{}])
               for line in (sa.get(J2_PATCH_KEY), sb.get(J2_PATCH_KEY)) if line is not None]
    rows.append(_row("Q-S2", "J2 patch key: R4 blocked on both, delta in [-1, +1] mm",
                     {"delta_mm": patch, "blocked": blocked},
                     None if patch is None else (len(blocked) == 2 and all(blocked)
                                                 and -1.0 <= patch <= 1.0)))
    others = [pair for pair in subs["Y-Sb"]["pairs"]
              if pair["key"] not in (BOUNDARY_KEY, J2_PATCH_KEY)]
    rows.append(_row("Q-S3", "the other 28 pairs pass C-2 / C-F / C-S",
                     f"{sum(1 for pair in others if not pair['fail'])}/{len(others)}",
                     len(others) == 28 and not any(pair["fail"] for pair in others)))
    rows.append(_row("Q-S4", "Y-S pass", None, None))
    return rows


# ------------------------------------------------------------------------------- CLI
def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--v5-dir", type=Path, default=V5_DIR,
                        help="v5 folder with the stored base files (the main checkout's)")
    parser.add_argument("--k1-dir", type=Path, default=None,
                        help="folder of the k1_*.jsonl files (default <v5-dir>/las/k1)")
    parser.add_argument("--json-out", type=Path, default=None)
    return parser.parse_args(argv)


def _json_value(value):
    return value.item() if hasattr(value, "item") else str(value)


def summary_of(result: dict) -> dict:
    return {"status": result["status"],
            "bundles": {name: entry["status"] for name, entry in result.get("bundles", {}).items()},
            "input_problems": len(result.get("input_problems") or ())}


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    k1_dir = args.k1_dir or args.v5_dir / K1_DIR_RELATIVE
    try:
        bases, base_problems = load_bases(args.v5_dir)
        lines = read_run_lines(k1_dir) if k1_dir.exists() else []
    except (OSError, ValueError) as exc:
        print(f"input error: {exc!r}")
        print(json.dumps({"status": STATUS_STOP, "input_error": str(exc)}))
        return EXIT_CODES[STATUS_STOP]
    result = judge(lines, bases, base_problems, seal_problems())
    for problem in result.get("input_problems") or ():
        print(f"INPUT {problem}")
    for name, entry in result.get("bundles", {}).items():
        print(f"{name}: {entry['status']} ({entry['lines']}/{entry['expected_lines']} lines)")
    for name, sub in result.get("subs", {}).items():
        for kind in ("fails", "stops", "incomplete"):
            for text in sub[kind]:
                print(f"  {name} {kind[:-1] if kind != 'incomplete' else kind}: {text}")
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(result, indent=1, default=_json_value) + "\n",
                                 encoding="utf-8")
    print(json.dumps(summary_of(result)))
    return EXIT_CODES[result["status"]]


if __name__ == "__main__":
    sys.exit(main())
