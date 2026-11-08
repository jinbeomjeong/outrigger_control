"""Judge of the LAS-b revision targets (P5 / P3 / P53 against L, sealed rules 5 .. 9).

Rules: ``06_analysis/02_control/verif_matrix/las_rev_targeted_rules.md`` (control-expert,
sealed; LF sha256 :data:`RULES_SHA256`). The rules text wins where this code differs. This
module reads only JSON lines (no simulation import), so ``las_rev_targeted.py`` can use its
checks during a batch (K-1 .. K-4, the C-2 type count of H-8) and a re-count script can read the
same files on its own.

Inputs: the ``rev_R*.jsonl`` files of ``las_rev_targeted.py`` (``rev`` block per line) and the
stored L lines: ``v5/las/las_T1.jsonl`` (``las.candidate`` ``b0``) and ``las_T2.jsonl`` for R-T,
``v5/fb/fb_F3.jsonl`` / ``fb_F4.jsonl`` (``fb.candidate`` ``L``) for R-S.

What it checks (rules section in brackets):
  K-1 .. K-4 [2]  pre-registered hashes / start times / the P3 identical set / settings + n_min.
  R-0 [7.1]       six P0 hashes against the stored 64-character values (H-2).
  (ga) R-G [5.1]  G-1 F_RL and F_judged >= 10.400 kN, G-2 R_c <= 0.500 kN per cell (j 0..3),
                  G-3 exclusion check (30 lines, no error, level budget 0, gates consistent),
                  G-4 = K-1, K-2, K-4.
  (na) R-T [5.2]  C-2 type (a) .. (c) per pair, C-1 T-1 F_judged >= 10,414.589 N, C-F margin
                  line, C-S stroke +1 mm, A-3 the 48 H-R-0 hashes, R-1 / R-2 READY median /
                  maximum over the changed-hash population with the empty-set rule and the
                  C-4 exception [6].
  (da) R-S [5.3]  C-2 type ((b), (c) only for the verdict cases), C-S on the D-1 pairs, READY
                  change recorded with the exception flag.
  R-P0 [7.3]      every changed key reproduced by P0 with the stored hash (else H-5).
  Ranking [9]     min F_judged of (ga), changed pairs of (na)+(da), R-1 median, P5 > P3 > P53.
None / missing [5.0]: a field the criteria need that is missing makes the pair undecidable
(H-4); None values count as failures as the rules say.
Audit items of 2026-11-09: an expected candidate without R-G lines is ``incomplete`` /
``not_run`` and the exit is 1 (ga); a missing field in the R-T / R-S K checks is H-4
(undecidable), not an H-3 stop (na); a line's ``controller_tag`` must be the one of its setting
(V0 ``final_C4G2_LAS``, VB ``final_C4G2_P3_LAS``) (da).

Usage (python-dev, project root, PowerShell):
  python -I -B 04_scripts/04_hydraulic/coupled/las_rev_judge.py [files ...] [--out <md>]
      (no files: every ``rev_R*.jsonl`` in ``v5/las/rev/``)
Exit codes: 0 judged, 1 a stop condition (H-2 .. H-5, H-9 or undecidable), 2 input error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
V5_DIR = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5"
REV_DIR = V5_DIR / "las" / "rev"
RULES_PATH = ROOT / "06_analysis" / "02_control" / "verif_matrix" / "las_rev_targeted_rules.md"
RULES_SHA_PATH = RULES_PATH.with_suffix(".sha256")
RULES_SHA256 = "bb235f27567240b205a544ed7cfd10237827e4627088e0eab1f62b318416ff60"
"""``las_rev_targeted_rules.sha256`` (LF digest, sealed 2026-11-08 21:44:50 +09:00)."""
RULES_REV1_PATH = RULES_PATH.with_name("las_rev_targeted_rules_rev1.md")
RULES_REV1_SHA_PATH = RULES_REV1_PATH.with_suffix(".sha256")
RULES_REV1_SHA256 = "672bc8f81ba75419e5a201e05a94e2f9aead2de3c205f80c2661e7474cd9fd51"
"""rev1 (LF digest, before any candidate line): ``d1.items`` over the key union (R1-1, R1-2),
H-4 only without ``d1`` / items or with equal hash and other items (R1-3)."""
SEALED_RULES = ((RULES_PATH, RULES_SHA_PATH, RULES_SHA256),
                (RULES_REV1_PATH, RULES_REV1_SHA_PATH, RULES_REV1_SHA256))
STORED_PATHS = {"T-1": V5_DIR / "las" / "las_T1.jsonl", "T-2": V5_DIR / "las" / "las_T2.jsonl",
                "F-3": V5_DIR / "fb" / "fb_F3.jsonl", "F-4": V5_DIR / "fb" / "fb_F4.jsonl"}
STORED_COUNTS = {"T-1": 8, "T-2": 184, "F-3": 16, "F-4": 14}

# Rules 1.2 candidates: (beta, n_min).
CANDIDATE_VALUES = {"P0": (3.5, 0), "P5": (4.5, 0), "P3": (3.5, 8), "P53": (4.5, 8)}
GRID_CANDIDATES = ("P5", "P3", "P53")
CANDIDATE_ORDER = ("P5", "P3", "P53")
"""Rules 9.4 last tie-break."""
BUNDLES = ("R-0", "R-G", "R-T", "R-S", "R-P0", "R-X")

# Rules 5 thresholds.
F_MIN_N = 9414.589
GRID_FORCE_FLOOR_KN = 10.400
GRID_RANGE_LIMIT_KN = 0.500
C1_FORCE_FLOOR_N = F_MIN_N + 1000.0
"""LAS-b original C1: F_min + 1,000 N = 10,414.589 N."""
STROKE_INCREASE_LIMIT_M = 0.001
READY_MEDIAN_LIMIT_S = 1.0
READY_MAX_LIMIT_S = 5.0
EXCEPTION_DT_FLOOR_S = 1.0
EXCEPTION_SHARE = 0.8
EXCEPTION_COUNT_LIMIT = 5
EXCEPTION_DT_LIMIT_S = 15.0
C2_STOP_PAIRS = 5
"""H-8: pairs with at least one C-2 type violation in one candidate's R-T or R-S."""
START_TOLERANCE_S = 0.05
"""Rules 2.2: T_s / 2."""
RANK_FORCE_TIE_KN = 0.3
TIME_TOLERANCE_S = 1e-9
EVENT_PREFIXES = ("FAULT", "WARN")
H_R_0_MARK = "|H-R-0|"
H_R_0_COUNT = 48
GRID_SETTINGS = ("VB", "V0")
GRID_CENTRES = ("1", "0.94", "nom")
GRID_STEPS = (0, 1, 2, 3, 4)
RANGE_STEPS = (0, 1, 2, 3)
G3_KEY_PREFIX = "D1|H-R-A|rigid+J1@FR|T|diag-op|K3"
T1_ROW_PREFIXES = ("D1|H-R-A|rigid+J1@FR|T|diag-op|K1|", "D1|H-R-A|rigid+J1@FR|T|diag-op|K3|")

# Rules 2.1 / 2.2: the 30 D-b lines (diag_Db.jsonl, b0 + TOUCH budget) as recorded: full
# commands hash and the b0 LAS-b start time. Group A (a >= 8) is K-1, group B is K-2.
D_B_LINES = {
    ("V0", "0.94", 0): ("ed5764c9b759e69743b5cf545c692832786495f3b5942d611c2feafe3e06e3ef", 22.0),
    ("V0", "0.94", 1): ("fdef826b7254fa7ebe1d01a700ad86fb62cad6e04cc8804037c99d9feaffec99", 21.7),
    ("V0", "0.94", 2): ("7d1b34ecdf58d755a628ed1c78f6d927d060ddca7a54e3a3441dc30b1d1fd160", 22.0),
    ("V0", "0.94", 3): ("7a6ef9e2c7f2d6c092a49195bb89ce7603c2aa9107a06fd6040550ca1826951d", 21.7),
    ("V0", "0.94", 4): ("5110db6f37caf6356120cd4b698990896b05dd48c1c160089986491c379c5431", 22.1),
    ("V0", "1", 0): ("52547a6e145e8783e07b310435ef5c2b11fd0012780755cb7b40cb61e8b12507", 20.7),
    ("V0", "1", 1): ("d7153125c1f581665ce79a36cd361f289059213ab87c1f07137e184d2878e4c2", 21.1),
    ("V0", "1", 2): ("9270a8bb9d20688a951f46aa328e20567a0e32df88489937bbbd37fe43d68833", 20.7),
    ("V0", "1", 3): ("58140da4b5481f334818fd562ceb81b5e5c0a46d8fc259f2e64a1d21660308ca", 21.1),
    ("V0", "1", 4): ("876fed85522c12e6663fcdfa55dcb28f1d5e7e393b9c47d4bcd11b6514572db4", 20.8),
    ("V0", "nom", 0): ("c190903359aa8dc18316f2cbaf152da914cefc2ca42a150fe25b8d65510dfff0", 23.1),
    ("V0", "nom", 1): ("42683a203bf1bf06b037632ad226d4367ec5a92d3fcd864d7d513ed8567963e9", 23.1),
    ("V0", "nom", 2): ("1394c19e7bf3389642a144d61abd3f2ead0c53b00238d9acba70cb112e0441db", 23.1),
    ("V0", "nom", 3): ("acfe58346d299ee2e7974cacf8812ebec4f449f191dea99ed157de018fb46ada", 22.8),
    ("V0", "nom", 4): ("eca649708d8526b6d03f6cf482f3e09f3b73e074c320e1bea782443cd353f1f3", 23.2),
    ("VB", "0.94", 0): ("2d459242518a74a104a6d56e88bc762a2d38e0a0b9cfd0068c3d581e9c1bc84e", 22.4),
    ("VB", "0.94", 1): ("38618bda6038bf7f0f56448ee22635804959dbdf3251d539346cedf2fd8dc111", 22.4),
    ("VB", "0.94", 2): ("108c4357f171d0dec77f2fdab16c2c9173d29de80811338dbac70abb18fcab4a", 22.4),
    ("VB", "0.94", 3): ("2933e25f8ceb6a4583a844c03687c1de431185360c5e7c13da244a16c62feac8", 22.4),
    ("VB", "0.94", 4): ("b7df1774cd7e515d4b5d2d973ba38180b135921fe41f9916fdc0391cc506dab5", 22.4),
    ("VB", "1", 0): ("eec974b66af2b06063eaf146fc7098eaf968bb017d5567d14fbfe4fa72b5ab15", 22.4),
    ("VB", "1", 1): ("12b8dc95a4dd41db985017a738fb6314d4e1bad48a3ab1e25622f68c504a688f", 22.4),
    ("VB", "1", 2): ("e702e1c0f231113c9311793a5338a88d92797431aaf39abb971d1135111dd2bb", 22.4),
    ("VB", "1", 3): ("a40b31bdc696e37cf553539969e55fe20bc0b47eccff0ff3cb9afbfd676ee2b2", 22.4),
    ("VB", "1", 4): ("4fa9360b3debb351abded6151f0017b12f4e63f1f3205ba0cc888f3fd1cce7d2", 22.4),
    ("VB", "nom", 0): ("c72e663e16cf5aec24199f3fe12ff7ed272f18ebde30fc109e710f084947a862", 23.1),
    ("VB", "nom", 1): ("030c8bc6bf2a94723ebdd50e8fd4918ca3b8a0f6cd2babe47b5a487a52aebb78", 23.1),
    ("VB", "nom", 2): ("e2e750fa446aee5abea82e6d70095a06c2909ed93616b7a006ca622d1205e85f", 22.9),
    ("VB", "nom", 3): ("49f71495509f5ea3bfaeea2bcb91aac4f78f57eac69686c742eb7fd4a4c339bc", 22.8),
    ("VB", "nom", 4): ("237b1f2196b916ba239e26d83e7f54d5c1573bdc819056643ff010b10d4b0b91", 23.2),
}
K2_PREDICTED_START_S = {
    ("V0", "0.94", 0): 21.8, ("V0", "0.94", 2): 21.8, ("V0", "0.94", 4): 21.9,
    ("V0", "1", 1): 20.9, ("V0", "1", 3): 20.9,
    ("V0", "nom", 0): 23.0, ("V0", "nom", 1): 23.0, ("V0", "nom", 2): 23.0,
    ("V0", "nom", 4): 23.1,
    ("VB", "nom", 0): 23.0, ("VB", "nom", 1): 23.0, ("VB", "nom", 4): 23.1,
}
"""Rules 2.2: the predicted P5 / P53 start of the 12 group-B lines (the other 18 are K-1)."""
K3_EXPECTED_COUNTS = {"T-1": 4, "T-2": 145, "F-3": 13, "F-4": 14}
"""Rules 2.3: stored L lines P3 may not change."""
R0_EXPECTED = {
    ("D1|H-R-A|rigid+J1@FR|T|diag-op|K1|VB|e0", "P0"):
        "aff9b0f10ac54cf8d65e1e220cd832334e29fdfd6b3d54a8a772141a84e4cc5b",
    ("D1|H-R-A|rigid+J1@FR|T|diag-op|K3|V0|e0", "P0"):
        "fc2ca22f285097be8ddb151389cebb9f7af26b0b52c6b4d3898c479712d61cc2",
    ("D1|H-R-A|rigid+J1@FR|T|diag-op|K3|VB|e0.002", "P0-LT-c1-j0"):
        "eec974b66af2b06063eaf146fc7098eaf968bb017d5567d14fbfe4fa72b5ab15",
    ("D1|H-R-A|rigid+J1@FR|T|diag-op|K3|V0|e0.002", "P0-LT-c1-j0"):
        "52547a6e145e8783e07b310435ef5c2b11fd0012780755cb7b40cb61e8b12507",
    ("D1|H-S-A|G1+J1@FR|T|diag-psa-soil|K1|VB|e0", "P0"):
        "9d35ecc64f769d6615f662728345425036289a788fcc77effc50a53a0442944d",
    ("R12|VB|etadef|e0|o0", "P0"):
        "017b1959826bda43cb43e64b6de2a162e800f5ef26125dc7c8e21f23d8183646",
}
"""Rules 7.1: (pair key, label) -> stored hash (las_T1 b0, diag_Db A-1, fb_F3 / fb_F4 L)."""


class MissingField(KeyError):
    """A field the criteria need is not in the line (rules 5.0: undecidable, H-4)."""


# ------------------------------------------------------------------------------- reading
def lf_sha256(path: Path) -> str:
    """sha256 with CRLF read as LF (the seal is an LF digest)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def seal_problems(rules_path: Path = RULES_PATH, sha_path: Path = RULES_SHA_PATH,
                  expected: str = RULES_SHA256) -> list[str]:
    """H-1: the rules and their ``.sha256`` are there and both give the sealed digest."""
    problems = [f"missing {path}" for path in (rules_path, sha_path) if not path.exists()]
    if problems:
        return problems
    tokens = sha_path.read_text(encoding="utf-8").split()
    if not tokens or tokens[0].lower() != expected:
        problems.append(f"{sha_path.name} does not hold {expected}")
    digest = lf_sha256(rules_path)
    if digest != expected:
        problems.append(f"{rules_path.name} LF sha256 {digest} != sealed {expected}")
    return problems


def sealed_rules_problems(sealed=SEALED_RULES) -> list[str]:
    """H-1 over the original rules and every sealed addendum (rev1)."""
    problems = []
    for rules_path, sha_path, expected in sealed:
        problems += seal_problems(rules_path, sha_path, expected)
    return problems


def read_lines(path: Path) -> list[dict]:
    """JSON lines of a file (blank lines skipped).

    Raises:
        ValueError: A line that is not JSON.
    """
    out = []
    for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not text.strip():
            continue
        try:
            out.append(json.loads(text))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: {exc}") from exc
    return out


def need(mapping: dict | None, *path: str):
    """``mapping[path[0]][path[1]]...``; a missing key raises :class:`MissingField`."""
    value = mapping
    for name in path:
        if not isinstance(value, dict) or name not in value:
            raise MissingField(".".join(path))
        value = value[name]
    return value


def stored_key(line: dict) -> str:
    """Pair key of a stored line (``fb.key``, else ``las.key``)."""
    if "fb" in line:
        return line["fb"]["key"]
    return line["las"]["key"]


def is_stored_l(source: str, line: dict) -> bool:
    if source.startswith("T-"):
        return (line.get("las") or {}).get("candidate") == "b0"
    return (line.get("fb") or {}).get("candidate") == "L"


def load_stored(paths: dict[str, Path] = STORED_PATHS) -> dict[str, dict[str, dict]]:
    """``{source: {key: L line}}`` of the stored baselines (rules 3.2 / 3.3).

    Raises:
        OSError, ValueError: A file is missing, unreadable or has the wrong L count.
    """
    stored = {}
    for source, path in paths.items():
        lines = [line for line in read_lines(path) if is_stored_l(source, line)]
        by_key = {stored_key(line): line for line in lines}
        if len(by_key) != STORED_COUNTS[source] or len(lines) != len(by_key):
            raise ValueError(f"{path.name}: {len(lines)} L lines ({len(by_key)} keys), "
                             f"expected {STORED_COUNTS[source]}")
        stored[source] = by_key
    return stored


def stored_line(stored: dict, key: str) -> dict | None:
    for by_key in stored.values():
        if key in by_key:
            return by_key[key]
    return None


def source_of(stored: dict, key: str) -> str | None:
    for source, by_key in stored.items():
        if key in by_key:
            return source
    return None


# ------------------------------------------------------------------------------- line facts
def rev_of(line: dict) -> dict:
    return line.get("rev") or {}


def is_error(line: dict) -> bool:
    return "error" in line


def is_verdict_case(line: dict) -> bool:
    return "case" in (line.get("job") or {})


def ready_time(line: dict) -> float | None:
    """READY time of a line: ``d1.t_ready_s`` (D-1), ``values.times.t_first_ready_s`` (cases)."""
    if is_verdict_case(line):
        return need(line, "values", "times", "t_first_ready_s")
    return need(line, "d1", "t_ready_s")


def event_name_set(line: dict) -> set[str]:
    """``FAULT*`` / ``WARN*`` names of ``event_names`` (the part before ``:``)."""
    names = need(line, "event_names")
    out = set()
    for name in names:
        base = str(name).split(":", 1)[0]
        if base.startswith(EVENT_PREFIXES):
            out.add(base)
    return out


def grid_point_of(line: dict) -> tuple[str, str, int] | None:
    """(setting, centre, j) of an R-G / R-0 grid line."""
    point = rev_of(line).get("grid_point")
    if point is None:
        return None
    setting = need(line, "job", "setting")
    return setting, str(point[0]), int(point[1])


# ------------------------------------------------------------------------------- K checks
def p3_identical_keys(stored: dict) -> dict[str, set[str]]:
    """Rules 2.3: per source, the stored L keys that P3 may not change (not started, an end
    other than ``sum``, or ``sum`` with a >= 8)."""
    n_min = CANDIDATE_VALUES["P3"][1]
    out = {}
    for source, by_key in stored.items():
        keys = set()
        for key, line in by_key.items():
            las = line.get("las") or {}
            if (las.get("start_t_s") is None or las.get("end_reason") != "sum"
                    or int(las.get("active_periods") or 0) >= n_min):
                keys.add(key)
        out[source] = keys
    return out


def settings_problems(line: dict) -> list[str]:
    """K-4: the controller's own settings are the candidate's, and a ``sum`` end has
    ``a >= n_min``."""
    rev = rev_of(line)
    candidate = need(rev, "candidate")
    beta, n_min = CANDIDATE_VALUES[candidate]
    problems = []
    if need(rev, "settings_match") is not True:
        problems.append("K-4 controller settings differ from the candidate's (other fields)")
    settings = need(rev, "settings")
    if settings.get("light_leg_fraction_of_F_min") != beta:
        problems.append(f"K-4 beta {settings.get('light_leg_fraction_of_F_min')} != {beta}")
    if settings.get("min_active_periods") != n_min:
        problems.append(f"K-4 n_min {settings.get('min_active_periods')} != {n_min}")
    params = need(line, "las", "params")
    if params.get("beta") != beta or params.get("n_min") != n_min:
        problems.append(f"K-4 las.params beta {params.get('beta')} n_min {params.get('n_min')}")
    las = need(line, "las")
    if las.get("end_reason") == "sum" and int(las.get("active_periods") or 0) < n_min:
        problems.append(f"K-4 sum end with a {las.get('active_periods')} < n_min {n_min}")
    return problems


def grid_problems(line: dict) -> list[str]:
    """K-1 (group A: hash = D-b) and K-2 (group B: start time) of an R-G line."""
    point = grid_point_of(line)
    if point is None or point not in D_B_LINES:
        return [f"K grid point {point} unknown"]
    candidate = rev_of(line)["candidate"]
    stored_sha, b0_start_s = D_B_LINES[point]
    if point not in K2_PREDICTED_START_S:
        if line["commands_sha256"] != stored_sha:
            return [f"K-1 {point} hash {line['commands_sha256'][:12]} != D-b {stored_sha[:12]}"]
        return []
    expected_s = b0_start_s if candidate == "P3" else K2_PREDICTED_START_S[point]
    start_s = need(line, "las", "start_t_s")
    if start_s is None or abs(start_s - expected_s) > START_TOLERANCE_S + TIME_TOLERANCE_S:
        return [f"K-2 {point} {candidate} start {start_s} != predicted {expected_s}"]
    return []


def k_problems(line: dict, stored: dict | None, k3_keys: dict | None = None) -> list[str]:
    """K-1 .. K-4 and the R-0 hash of one finished line (empty = as predicted).

    Raises:
        MissingField: A field the check reads is not in the line.
    """
    rev = rev_of(line)
    bundle, candidate = need(rev, "bundle"), need(rev, "candidate")
    problems = list(settings_problems(line))
    key = need(rev, "key")
    if bundle == "R-0":
        expected = R0_EXPECTED.get((key, need(rev, "label")))
        if expected is None:
            problems.append(f"R-0 job {key} {rev.get('label')} is not in the R-0 table")
        elif line["commands_sha256"] != expected:
            problems.append(f"H-2 R-0 {key} hash {line['commands_sha256']} != {expected}")
    if bundle == "R-G":
        problems += grid_problems(line)
    if bundle in ("R-T", "R-S") and candidate == "P3" and stored is not None:
        k3_keys = k3_keys or p3_identical_keys(stored)
        source = source_of(stored, key)
        if source is not None and key in k3_keys[source]:
            stored_sha = stored[source][key]["commands_sha256"]
            if line["commands_sha256"] != stored_sha:
                problems.append(f"K-3 {key} hash {line['commands_sha256'][:12]} != stored "
                                f"{stored_sha[:12]}")
    return problems


# ------------------------------------------------------------------------------- C-2 type
def _item_violations(cand_items: dict, l_items: dict) -> list[str]:
    """Rules 5.0 over the key union (rev1 R1-1 / R1-2): a key on one side only reads None on
    the other. Violations: L true and candidate not true; L None and candidate false."""
    out = []
    for name in sorted(set(cand_items) | set(l_items)):
        l_value, value = l_items.get(name), cand_items.get(name)
        if (l_value is True and value is not True) or (l_value is None and value is False):
            out.append(f"item {name} {l_value} -> {value}")
    return out


def items_only(cand: dict, l_line: dict) -> dict[str, list[str]]:
    """rev1 R1-2: the ``d1.items`` keys on one side only (reported per pair)."""
    cand_keys = set(need(cand, "d1", "items"))
    l_keys = set(need(l_line, "d1", "items"))
    return {"items_only_L": sorted(l_keys - cand_keys),
            "items_only_cand": sorted(cand_keys - l_keys)}


def same_trajectory_drift(cand: dict, l_line: dict) -> None:
    """rev1 R1-3: equal commands hash but other ``d1.items`` (keys or values) is judge drift.

    Raises:
        MissingField: Same hash, different items (undecidable, H-4).
    """
    cand_items, l_items = need(cand, "d1", "items"), need(l_line, "d1", "items")
    if cand["commands_sha256"] == l_line["commands_sha256"] and cand_items != l_items:
        raise MissingField("d1.items differ with an equal commands hash (rev1 R1-3)")


def _verdict_violations(cand: dict, l_line: dict) -> list[str]:
    """(a): verdict, fail items, items."""
    cand_d1, l_d1 = need(cand, "d1"), need(l_line, "d1")
    verdict, l_verdict = need(cand_d1, "verdict"), need(l_d1, "verdict")
    out = []
    if verdict is None:
        out.append("verdict None")
    elif l_verdict in ("pass", "allowed_stop") and verdict == "fail":
        out.append(f"verdict {l_verdict} -> fail")
    extra = set(need(cand_d1, "fail_items") or ()) - set(need(l_d1, "fail_items") or ())
    if extra:
        out.append(f"new fail items {sorted(extra)}")
    same_trajectory_drift(cand, l_line)
    return out + _item_violations(need(cand_d1, "items"), need(l_d1, "items"))


def _phase_violations(cand: dict, l_line: dict) -> list[str]:
    """(b): READY phase and READY time."""
    out = []
    if need(l_line, "final_phase") == "ready" and need(cand, "final_phase") != "ready":
        out.append(f"final_phase ready -> {cand['final_phase']}")
    if ready_time(l_line) is not None and ready_time(cand) is None:
        out.append("READY time -> None")
    return out


def _event_violations(cand: dict, l_line: dict) -> list[str]:
    """(c): candidate FAULT / WARN names within L's."""
    extra = event_name_set(cand) - event_name_set(l_line)
    return [f"new events {sorted(extra)}"] if extra else []


def pair_violations(cand: dict, l_line: dict) -> list[str]:
    """C-2 type (a) .. (c) of one pair; verdict cases only (b) and (c) (rules 5.3).

    Raises:
        MissingField: A criteria field missing in either line (undecidable, H-4).
    """
    out = [] if is_verdict_case(l_line) else _verdict_violations(cand, l_line)
    return out + _phase_violations(cand, l_line) + _event_violations(cand, l_line)


def stroke_increase_m(cand: dict, l_line: dict) -> float | None:
    """C-S: ``d1.stroke_max_m`` increase (None when either is None)."""
    value, l_value = need(cand, "d1", "stroke_max_m"), need(l_line, "d1", "stroke_max_m")
    if value is None or l_value is None:
        return None
    return float(value) - float(l_value)


# ------------------------------------------------------------------------------- done clock
def las_end_s(line: dict) -> float | None:
    """The LAS-b end restarts must follow (rules 6): ``las.end_t_s``."""
    return (line.get("las") or {}).get("end_t_s")


def exception_record(cand: dict, l_line: dict, rx_line: dict | None,
                     las_end_of=las_end_s) -> dict:
    """Rules 6 for one pair with a READY delay above +1.0 s.

    Args:
        las_end_of: The time every counted restart must follow (``las_revA_judge`` passes
            the end of the end ramp).

    Returns:
        ``is_exception`` and the values behind it (``reason`` when it is not one).
    """
    delta_s = ready_time(cand) - ready_time(l_line)
    out = {"dt_s": delta_s, "is_exception": False}
    clock = cand.get("done_clock")
    if rx_line is None or "done_clock" not in rx_line or clock is None:
        return {**out, "reason": "no done_clock on both sides (R-X line missing)"}
    if rx_line["commands_sha256"] != l_line["commands_sha256"]:
        return {**out, "reason": "H-5 R-X hash differs from the stored L", "h5": True}
    loss_s, l_loss_s = clock.get("loss_s"), rx_line["done_clock"].get("loss_s")
    out.update(loss_cand_s=loss_s, loss_L_s=l_loss_s,
               resets=clock.get("resets"), t_las_start_s=(cand.get("las") or {}).get("start_t_s"),
               t_las_end_s=las_end_of(cand),
               t_loc_last_s=clock.get("t_loc_last_before_done_s"))
    if loss_s is None or l_loss_s is None:
        return {**out, "reason": "loss_s None"}
    excess_s = loss_s - l_loss_s
    out["E_over_dt"] = excess_s / delta_s if delta_s else None
    if excess_s < EXCEPTION_SHARE * delta_s - TIME_TOLERANCE_S:
        return {**out, "reason": "E < 0.8 dt"}
    t_end_s = out["t_las_end_s"]
    starts = clock.get("clock_starts_s") or []
    counted = [reset for reset in clock.get("resets") or []
               if starts and starts[0] - TIME_TOLERANCE_S <= reset["t_s"]
               <= starts[-1] + TIME_TOLERANCE_S]
    if t_end_s is None or any(reset["t_s"] < t_end_s - TIME_TOLERANCE_S for reset in counted):
        return {**out, "reason": "a restart before the LAS-b end"}
    return {**out, "is_exception": True, "reason": "gate timing branch"}


# ------------------------------------------------------------------------------- (ga) R-G
@dataclass
class GridResult:
    candidate: str
    lines: dict[tuple[str, str, int], dict] = field(default_factory=dict)
    errors: int = 0
    duplicates: list = field(default_factory=list)


def _grid_lines(lines: list[dict]) -> dict[str, GridResult]:
    results = {name: GridResult(name) for name in GRID_CANDIDATES}
    for line in lines:
        rev = rev_of(line)
        if rev.get("bundle") != "R-G" or rev.get("candidate") not in results:
            continue
        result = results[rev["candidate"]]
        if is_error(line):
            result.errors += 1
            continue
        point = grid_point_of(line)
        if point in result.lines:
            result.duplicates.append(point)
        result.lines[point] = line
    return results


def _summary_value(line: dict, name: str):
    return need(line, "diag", "summary", name)


def judge_grid(result: GridResult) -> dict:
    """G-1 .. G-4 of one candidate (rules 5.1)."""
    expected = {(s, c, j) for s in GRID_SETTINGS for c in GRID_CENTRES for j in GRID_STEPS}
    g3 = []
    if result.errors or result.duplicates or set(result.lines) != expected:
        g3.append(f"lines {len(result.lines)}/30, errors {result.errors}, "
                  f"duplicates {result.duplicates}, missing {sorted(expected - set(result.lines))}")
    rows, g1_fail, k_fail, between = [], [], [], []
    for point in sorted(result.lines):
        line = result.lines[point]
        try:
            f_rl = _summary_value(line, "F_RL_kN")
            f_judged = _summary_value(line, "F_judged_min_kN")
            budget = need(line, "diag", "touch_budget", "level_budget_periods")
            consistent = _summary_value(line, "gate_consistent")
            k_fail += [f"{point}: {p}" for p in k_problems(line, None)]
        except MissingField as exc:
            g3.append(f"{point}: missing {exc}")
            continue
        if budget != 0 or consistent is not True:
            g3.append(f"{point}: level_budget_periods {budget}, gate_consistent {consistent}")
        if f_rl is None or f_judged is None or min(f_rl, f_judged) < GRID_FORCE_FLOOR_KN:
            g1_fail.append(f"{point}: F_RL {f_rl} F_judged {f_judged}")
        for value in (f_rl, f_judged):
            if value is not None and GRID_FORCE_FLOOR_KN <= value < C1_FORCE_FLOOR_N / 1e3:
                between.append(f"{point}: {value:.4f} kN")
        las = line.get("las") or {}
        rows.append({"point": list(point), "F_RL_kN": f_rl, "F_judged_min_kN": f_judged,
                     "start_t_s": las.get("start_t_s"),
                     "start_period": _summary_value(line, "las_start_period"),
                     "active_periods": las.get("active_periods"),
                     "end_reason": las.get("end_reason"),
                     "t_lift_s": _summary_value(line, "t_lift_s"),
                     "min_leg_after_lift": _summary_value(line, "min_leg_after_lift"),
                     "commands_sha256": line["commands_sha256"][:12]})
    cells = _grid_cells(result)
    g2_fail = [cell for cell in cells if not cell["ok"]]
    forces = [row["F_judged_min_kN"] for row in rows if row["F_judged_min_kN"] is not None]
    status = grid_status(bool(g1_fail or g2_fail), bool(g3), bool(k_fail))
    return {"candidate": result.candidate, "G-1": not g1_fail, "G-1_fail": g1_fail,
            "G-2": not g2_fail and not g3, "cells": cells, "G-3": not g3, "G-3_problems": g3,
            "G-4": not k_fail, "G-4_problems": k_fail, "between_thresholds": between,
            "min_F_judged_kN": min(forces) if forces else None, "rows": rows,
            "status": status, "pass": status == GRID_PASS}


GRID_PASS = "pass"
GRID_FAIL = "fail"
GRID_UNDECIDABLE = "undecidable"
GRID_STOP = "stop"


def grid_status(has_measure_failure: bool, has_g3_problem: bool, has_k_problem: bool) -> str:
    """(ga) outcome: a K mismatch (G-4 / H-3, which also leaves lines unrun) is a stop
    (implementation defect candidate), a G-3 problem undecidable; only then do G-1 / G-2
    shortfalls make a ``fail``."""
    if has_k_problem:
        return GRID_STOP
    if has_g3_problem:
        return GRID_UNDECIDABLE
    return GRID_FAIL if has_measure_failure else GRID_PASS


def _grid_cells(result: GridResult) -> list[dict]:
    """R_c (j 0..3), M_c (mean j 0..3), P_c = |F(4) - F(0)| per (setting, centre)."""
    cells = []
    for setting in GRID_SETTINGS:
        for centre in GRID_CENTRES:
            values = {}
            for j in GRID_STEPS:
                line = result.lines.get((setting, centre, j))
                if line is not None:
                    values[j] = ((line.get("diag") or {}).get("summary") or {}).get("F_RL_kN")
            phase = [values.get(j) for j in RANGE_STEPS]
            cell = {"setting": setting, "centre": centre, "values": values}
            if any(value is None for value in phase):
                cells.append({**cell, "R_c": None, "M_c": None, "P_c": None, "ok": False})
                continue
            p_c = None if values.get(4) is None or values.get(0) is None else abs(
                values[4] - values[0])
            r_c = max(phase) - min(phase)
            cells.append({**cell, "R_c": r_c, "M_c": sum(phase) / len(phase), "P_c": p_c,
                          "ok": r_c <= GRID_RANGE_LIMIT_KN + TIME_TOLERANCE_S})
    return cells


# ------------------------------------------------------------------------------- (na) / (da)
def _pair_lines(lines: list[dict], bundle: str, candidate: str) -> tuple[dict, int]:
    by_key, errors = {}, 0
    for line in lines:
        rev = rev_of(line)
        if rev.get("bundle") != bundle or rev.get("candidate") != candidate:
            continue
        if is_error(line):
            errors += 1
            continue
        by_key[rev["key"]] = line
    return by_key, errors


def _rx_lines(lines: list[dict]) -> dict[str, dict]:
    return {rev_of(line)["key"]: line for line in lines
            if rev_of(line).get("bundle") == "R-X" and not is_error(line)}


def _pair_records(cand_by_key: dict, stored: dict, sources: tuple[str, ...], rx: dict,
                  las_end_of=las_end_s) -> dict:
    """Per pair: C-2 type, F, stroke, hash, READY delta and the exception record."""
    expected = {key for source in sources for key in stored[source]}
    out = {"missing": sorted(expected - set(cand_by_key)), "pairs": {}, "undecidable": []}
    for key in sorted(expected & set(cand_by_key)):
        cand, l_line = cand_by_key[key], stored_line(stored, key)
        try:
            out["pairs"][key] = _pair_record(key, cand, l_line, rx, las_end_of)
        except MissingField as exc:
            out["undecidable"].append(f"{key}: missing {exc}")
    return out


def _pair_record(key: str, cand: dict, l_line: dict, rx: dict, las_end_of=las_end_s) -> dict:
    is_case = is_verdict_case(l_line)
    record = {"violations": pair_violations(cand, l_line),
              "changed": cand["commands_sha256"] != l_line["commands_sha256"],
              "is_case": is_case, "ready_cand_s": ready_time(cand),
              "ready_L_s": ready_time(l_line)}
    if not is_case:
        record.update(items_only(cand, l_line))
        record.update(F_cand_N=need(cand, "d1", "F_judged_min_N"),
                      F_L_N=need(l_line, "d1", "F_judged_min_N"),
                      stroke_increase_m=stroke_increase_m(cand, l_line))
    both_ready = record["ready_cand_s"] is not None and record["ready_L_s"] is not None
    record["dt_s"] = record["ready_cand_s"] - record["ready_L_s"] if both_ready else None
    if record["changed"] and both_ready and record["dt_s"] > EXCEPTION_DT_FLOOR_S:
        record["exception"] = exception_record(cand, l_line, rx.get(key), las_end_of)
    return record


def _force_checks(pairs: dict, t1_keys: set[str]) -> dict:
    c1, cf, cs = [], [], []
    for key, pair in pairs.items():
        if pair["is_case"]:
            continue
        f_cand, f_l = pair["F_cand_N"], pair["F_L_N"]
        if key in t1_keys and (f_cand is None or f_cand < C1_FORCE_FLOOR_N):
            c1.append(f"{key}: {f_cand}")
        if f_l is not None and f_l >= C1_FORCE_FLOOR_N and (
                f_cand is None or f_cand < C1_FORCE_FLOOR_N):
            cf.append(f"{key}: L {f_l} -> {f_cand}")
        increase = pair["stroke_increase_m"]
        if increase is None or increase > STROKE_INCREASE_LIMIT_M + TIME_TOLERANCE_S:
            cs.append(f"{key}: {increase}")
    return {"C-1_fail": c1, "C-F_fail": cf, "C-S_fail": cs}


def ready_population(pairs: dict) -> dict:
    """Rules 5.2 R-1 / R-2 with the empty-set rule and the C-4 exceptions (rules 6)."""
    changed = [key for key, pair in pairs.items() if pair["changed"]]
    exceptions, population, h5 = [], {}, []
    for key in changed:
        pair = pairs[key]
        if pair["dt_s"] is None:
            continue
        record = pair.get("exception")
        if record is not None and record.get("h5"):
            h5.append(key)
        if record is not None and record["is_exception"]:
            exceptions.append(key)
            continue
        population[key] = pair["dt_s"]
    out = {"changed": len(changed), "population": len(population), "exceptions": exceptions,
           "h5": h5, "median_s": None, "max_s": None}
    if not changed:
        return {**out, "R-1": True, "R-2": True, "basis": f"{len(pairs)}/{len(pairs)} hash equal"}
    if not population:
        return {**out, "R-1": None, "R-2": None, "basis": "changed pairs but empty population"}
    values = list(population.values())
    out.update(median_s=statistics.median(values), max_s=max(values))
    out["R-1"] = out["median_s"] <= READY_MEDIAN_LIMIT_S + TIME_TOLERANCE_S
    out["R-2"] = out["max_s"] <= READY_MAX_LIMIT_S + TIME_TOLERANCE_S
    out["basis"] = "population"
    return out


def exception_excess(pairs: dict, exceptions: list[str]) -> bool:
    """H-9: more than 5 exception pairs, or one with dt > +15 s."""
    return len(exceptions) > EXCEPTION_COUNT_LIMIT or any(
        pairs[key]["dt_s"] > EXCEPTION_DT_LIMIT_S for key in exceptions)


def judge_t(lines: list[dict], stored: dict, candidate: str, las_end_of=las_end_s) -> dict:
    """(na) R-T of one candidate (rules 5.2)."""
    cand_by_key, errors = _pair_lines(lines, "R-T", candidate)
    records = _pair_records(cand_by_key, stored, ("T-1", "T-2"), _rx_lines(lines), las_end_of)
    pairs = records["pairs"]
    c2 = {key: pair["violations"] for key, pair in pairs.items() if pair["violations"]}
    forces = _force_checks(pairs, set(stored["T-1"]))
    h_r_0 = [key for key in stored["T-2"] if H_R_0_MARK in key]
    a3 = [key for key in h_r_0 if key in pairs and pairs[key]["changed"]]
    ready = ready_population(pairs)
    is_complete = not (records["missing"] or records["undecidable"] or errors)
    checks = {"C-2": not c2, "C-1": not forces["C-1_fail"], "C-F": not forces["C-F_fail"],
              "C-S": not forces["C-S_fail"], "A-3": not a3 and len(h_r_0) == H_R_0_COUNT,
              "R-1": ready["R-1"], "R-2": ready["R-2"]}
    return {"candidate": candidate, "complete": is_complete, "errors": errors, **records,
            "C-2_violations": c2, **forces, "A-3_changed": a3, "ready": ready, "checks": checks,
            "exception_excess": exception_excess(pairs, ready["exceptions"]),
            "pass": is_complete and all(value is True for value in checks.values())}


def judge_s(lines: list[dict], stored: dict, candidate: str, las_end_of=las_end_s) -> dict:
    """(da) R-S of one candidate (rules 5.3): C-2 type, C-S; READY recorded only."""
    cand_by_key, errors = _pair_lines(lines, "R-S", candidate)
    records = _pair_records(cand_by_key, stored, ("F-3", "F-4"), _rx_lines(lines), las_end_of)
    pairs = records["pairs"]
    c2 = {key: pair["violations"] for key, pair in pairs.items() if pair["violations"]}
    forces = _force_checks(pairs, set())
    ready = [{"key": key, "dt_s": pair["dt_s"],
              "exception": (pair.get("exception") or {}).get("is_exception")}
             for key, pair in pairs.items() if pair["changed"]]
    is_complete = not (records["missing"] or records["undecidable"] or errors)
    checks = {"C-2": not c2, "C-S": not forces["C-S_fail"]}
    return {"candidate": candidate, "complete": is_complete, "errors": errors, **records,
            "C-2_violations": c2, "C-S_fail": forces["C-S_fail"], "ready_record": ready,
            "checks": checks, "pass": is_complete and all(checks.values())}


# ------------------------------------------------------------------------------- R-0 / R-P0
def judge_r0(lines: list[dict]) -> dict:
    found, tags = {}, []
    errors = 0
    for line in lines:
        rev = rev_of(line)
        if rev.get("bundle") != "R-0":
            continue
        if is_error(line):
            errors += 1
            continue
        found[(rev["key"], rev["label"])] = line["commands_sha256"]
        tags += [f"{rev['key']}: {text}" for text in tag_problems(line)]
    rows = [{"key": key, "label": label, "expected": sha, "got": found.get((key, label)),
             "equal": found.get((key, label)) == sha} for (key, label), sha in R0_EXPECTED.items()]
    return {"rows": rows, "errors": errors, "ran": len(found), "tag_problems": tags,
            "pass": errors == 0 and not tags and all(row["equal"] for row in rows)}


def changed_keys(lines: list[dict], stored: dict) -> set[str]:
    """Keys of R-T / R-S candidate lines whose hash is not the stored L hash (rules 7.3)."""
    out = set()
    for line in lines:
        rev = rev_of(line)
        if rev.get("bundle") not in ("R-T", "R-S") or is_error(line):
            continue
        l_line = stored_line(stored, rev.get("key"))
        if l_line is not None and line["commands_sha256"] != l_line["commands_sha256"]:
            out.add(rev["key"])
    return out


def exception_claim_keys(lines: list[dict], stored: dict) -> set[str]:
    """R-X keys: changed pairs with a READY delay above +1.0 s (rules 6 target)."""
    out = set()
    for line in lines:
        rev = rev_of(line)
        if rev.get("bundle") not in ("R-T", "R-S") or is_error(line):
            continue
        l_line = stored_line(stored, rev.get("key"))
        if l_line is None or line["commands_sha256"] == l_line["commands_sha256"]:
            continue
        try:
            cand_s, l_s = ready_time(line), ready_time(l_line)
        except MissingField:
            continue
        if cand_s is not None and l_s is not None and cand_s - l_s > EXCEPTION_DT_FLOOR_S:
            out.add(rev["key"])
    return out


def judge_rp0(lines: list[dict], stored: dict) -> dict:
    """R-P0: every changed key reproduced by P0 with the stored hash (H-5 otherwise); R-X
    lines must reproduce it too."""
    needed = changed_keys(lines, stored)
    reproduced, mismatches = set(), []
    for line in lines:
        rev = rev_of(line)
        if rev.get("bundle") not in ("R-P0", "R-X") or is_error(line):
            continue
        l_line = stored_line(stored, rev.get("key"))
        if l_line is None:
            mismatches.append(f"{rev.get('bundle')} {rev.get('key')}: no stored L")
        elif line["commands_sha256"] != l_line["commands_sha256"]:
            mismatches.append(f"{rev['bundle']} {rev['key']}: {line['commands_sha256'][:12]} != "
                              f"{l_line['commands_sha256'][:12]}")
        elif rev["bundle"] == "R-P0":
            reproduced.add(rev["key"])
    return {"needed": len(needed), "reproduced": len(needed & reproduced),
            "missing": sorted(needed - reproduced), "H-5": mismatches,
            "pass": not mismatches and needed <= reproduced}


ALLOWED_DIRTY = (".gitattributes", "00_docs/decision_log.md")
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
IDENTITY_GROUPS = {"P5": ("R-G", "R-T", "R-S"), "P3": ("R-G", "R-T", "R-S"),
                   "P53": ("R-G", "R-T", "R-S"), "P0": ("R-P0", "R-X")}
"""Rules 4.1: the lines of one candidate come from one commit (R-0 is its own test)."""


CONTROLLER_TAGS = ("final_C4G2_LAS", "final_C4G2_P3_LAS")
"""The LAS-b preset tags a run may carry (V0 / VB); any other tag is another controller."""
CONTROLLER_TAG_BY_SETTING = {"V0": "final_C4G2_LAS", "VB": "final_C4G2_P3_LAS"}
"""The tag each setting must carry (audit item (da), 2026-11-09)."""


def tag_problems(line: dict) -> list[str]:
    """The line's ``controller_tag`` (and the ``rev`` copy) is the one of its ``job.setting``
    (:data:`CONTROLLER_TAG_BY_SETTING`: V0 -> ``final_C4G2_LAS``, VB -> ``final_C4G2_P3_LAS``)."""
    tags = {line.get("controller_tag"), rev_of(line).get("controller_tag")}
    bad = sorted(str(tag) for tag in tags if tag not in CONTROLLER_TAGS)
    if bad:
        return [f"controller_tag {bad} not in {list(CONTROLLER_TAGS)}"]
    setting = (line.get("job") or {}).get("setting")
    expected = CONTROLLER_TAG_BY_SETTING.get(setting)
    if expected is None:
        return [f"setting {setting!r} has no expected controller_tag"]
    wrong = sorted(str(tag) for tag in tags if tag != expected)
    return [f"controller_tag {wrong} != {expected} for setting {setting}"] if wrong else []


def identity_problems(lines: list[dict]) -> dict[str, list[str]]:
    """H-4 (rules 4.1) per candidate: one commit, no code diff, allowed dirty files only,
    the sealed rules sha256."""
    out = {}
    for candidate, bundles in IDENTITY_GROUPS.items():
        heads, problems = set(), []
        for line in lines:
            rev = rev_of(line)
            if rev.get("candidate") != candidate or rev.get("bundle") not in bundles or is_error(
                    line):
                continue
            identity = rev.get("identity") or {}
            heads.add(identity.get("git_head"))
            if identity.get("code_diff_sha256") != EMPTY_SHA256:
                problems.append(f"{rev.get('key')}: code diff")
            extra = set(identity.get("dirty_files") or ()) - set(ALLOWED_DIRTY)
            if extra:
                problems.append(f"{rev.get('key')}: dirty {sorted(extra)}")
            if rev.get("rules_sha256") != RULES_SHA256:
                problems.append(f"{rev.get('key')}: rules sha256 {rev.get('rules_sha256')}")
            if identity.get("rules_rev1_sha256") != RULES_REV1_SHA256:
                problems.append(f"{rev.get('key')}: rules rev1 sha256 "
                                f"{identity.get('rules_rev1_sha256')}")
            problems += [f"{rev.get('key')}: {text}" for text in tag_problems(line)]
        if len(heads) > 1:
            problems.append(f"{len(heads)} commits: {sorted(map(str, heads))}")
        if problems:
            out[candidate] = problems
    return out


MISSING_FIELD_MARK = "H-4"
"""Prefix of a missing-field problem: undecidable (rules 8 H-4), not an H-3 stop."""


def pair_k_problems(lines: list[dict], stored: dict, candidate: str) -> list[str]:
    """K-3 / K-4 (H-3) of one candidate's R-T / R-S lines (an H-3 stop also leaves pairs
    unrun, which must not read as a criteria failure); a missing field is an ``H-4`` entry
    (audit item (na), 2026-11-09)."""
    k3_keys = p3_identical_keys(stored) if stored else None
    out = []
    for bundle in ("R-T", "R-S"):
        for key, line in _pair_lines(lines, bundle, candidate)[0].items():
            try:
                out += [f"{key}: {text}" for text in k_problems(line, stored or None, k3_keys)]
            except MissingField as exc:
                out.append(f"{MISSING_FIELD_MARK} {key}: missing {exc}")
    return out


def split_k_problems(problems: list[str]) -> tuple[list[str], list[str]]:
    """(H-3 stop problems, H-4 missing-field problems) of :func:`pair_k_problems`."""
    missing = [text for text in problems if text.startswith(MISSING_FIELD_MARK)]
    return [text for text in problems if text not in missing], missing


# ------------------------------------------------------------------------------- verdict
def rank(passing: list[str], grid: dict, t_results: dict, s_results: dict) -> list[str]:
    """Rules 9: min F_judged (0.3 kN tie), fewer changed pairs, smaller R-1 median, order."""
    def changed(name):
        return (t_results[name]["ready"]["changed"]
                + sum(pair["changed"] for pair in s_results[name]["pairs"].values()))

    def median(name):
        value = t_results[name]["ready"]["median_s"]
        return float("inf") if value is None else value

    remaining = sorted(passing, key=CANDIDATE_ORDER.index)
    ordered = []
    while remaining:
        best_force = max(grid[name]["min_F_judged_kN"] for name in remaining)
        tied = [name for name in remaining
                if best_force - grid[name]["min_F_judged_kN"] <= RANK_FORCE_TIE_KN]
        tied.sort(key=lambda name: (changed(name), median(name), CANDIDATE_ORDER.index(name)))
        ordered.append(tied[0])
        remaining.remove(tied[0])
    return ordered


def judge(lines: list[dict], stored: dict) -> dict:
    """Every criterion of rules 5 .. 9 over the given lines."""
    out = {"R-0": judge_r0(lines), "grid": {}, "R-T": {}, "R-S": {}, "stops": []}
    grids = _grid_lines(lines)
    for name in GRID_CANDIDATES:
        if grids[name].lines or grids[name].errors:
            out["grid"][name] = judge_grid(grids[name])
    grid_failures = [name for name, result in out["grid"].items()
                     if result["status"] == GRID_FAIL]
    if len(grid_failures) == len(GRID_CANDIDATES):  # G-1 / G-2 shortfalls only (rules 8 H-6)
        out["stops"].append("H-6 every candidate failed (ga)")
    out["pair_k_problems"] = {}
    for name in GRID_CANDIDATES:
        if _pair_lines(lines, "R-T", name)[0]:
            out["R-T"][name] = judge_t(lines, stored, name)
        if _pair_lines(lines, "R-S", name)[0]:
            out["R-S"][name] = judge_s(lines, stored, name)
        problems = pair_k_problems(lines, stored, name)
        if problems:
            out["pair_k_problems"][name] = problems
    out["R-P0"] = judge_rp0(lines, stored)
    out["identity"] = identity_problems(lines)
    for candidate, problems in out["identity"].items():
        out["stops"].append(f"H-4 identity {candidate}: {problems[:3]}")
    if out["R-P0"]["H-5"]:
        out["stops"].append(f"H-5 reproduction failed: {out['R-P0']['H-5'][:3]}")
    if not out["R-0"]["pass"] and out["R-0"]["ran"]:
        out["stops"].append("H-2 R-0 bit test mismatch")
    out["candidates"] = _candidate_verdicts(out)
    passing = [name for name, verdict in out["candidates"].items() if verdict["verdict"] ==
               "adopt_recommended"]
    out["ranking"] = rank(passing, out["grid"], out["R-T"], out["R-S"]) if passing else []
    return out


NOT_RUN = "not_run: no R-G lines"
"""``at`` of an expected candidate without any R-G line (audit item (ga), 2026-11-09)."""


def _candidate_verdicts(out: dict) -> dict:
    verdicts = {}
    for name in GRID_CANDIDATES:
        grid = out["grid"].get(name)
        if grid is None:
            verdicts[name] = {"verdict": "incomplete", "at": NOT_RUN, "not_run": True}
            continue
        t_result, s_result = out["R-T"].get(name), out["R-S"].get(name)
        if name in out["identity"]:
            verdicts[name] = {"verdict": "undecidable", "at": "H-4 run identity"}
            continue
        stop_problems, missing = split_k_problems(out["pair_k_problems"].get(name, []))
        if grid["status"] == GRID_STOP or stop_problems:
            verdicts[name] = {"verdict": "stop",
                              "at": "G-4 / H-3 K mismatch (implementation defect candidate)"}
            continue
        if missing:
            verdicts[name] = {"verdict": "undecidable", "at": "H-4 missing field"}
            continue
        if grid["status"] == GRID_UNDECIDABLE:
            verdicts[name] = {"verdict": "undecidable", "at": "G-3 exclusion check"}
            continue
        if grid["status"] == GRID_FAIL:
            verdicts[name] = {"verdict": "fail", "at": "(ga) G-1 / G-2"}
            continue
        if t_result is None or s_result is None:
            verdicts[name] = {"verdict": "incomplete", "at": "(na)/(da) not run"}
            continue
        failed = [f"{label} {check}" for label, result in (("(na)", t_result), ("(da)", s_result))
                  for check, value in result["checks"].items() if value is False]
        if failed:  # a definite failure stands even when a stop (H-8) left pairs unrun
            verdicts[name] = {"verdict": "fail", "at": failed}
        elif not (t_result["complete"] and s_result["complete"]) or None in (
                t_result["checks"]["R-1"], t_result["checks"]["R-2"]):
            verdicts[name] = {"verdict": "undecidable", "at": "missing / empty population"}
        elif t_result["exception_excess"]:
            verdicts[name] = {"verdict": "ask", "at": "H-9 exception excess"}
        elif not out["R-P0"]["pass"]:
            verdicts[name] = {"verdict": "incomplete", "at": "R-P0"}
        else:
            verdicts[name] = {"verdict": "adopt_recommended", "at": None}
    return verdicts


# ------------------------------------------------------------------------------- report
def _fmt(value, digits: int = 3) -> str:
    if value is None:
        return "None"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def report_markdown(result: dict, sources: list[Path]) -> str:
    lines = ["# LAS-b revision targets: judgement (las_rev_judge.py)", "",
             f"- rules sha256 {RULES_SHA256}",
             f"- inputs: {', '.join(str(path) for path in sources)}", ""]
    r0 = result["R-0"]
    lines += ["## R-0", "", "| key | label | expected | got | equal |", "|---|---|---|---|---|"]
    lines += [f"| {row['key']} | {row['label']} | {row['expected'][:12]} | "
              f"{(row['got'] or 'None')[:12]} | {row['equal']} |" for row in r0["rows"]]
    for name, grid in result["grid"].items():
        lines += ["", f"## (ga) {name}", "",
                  f"- status {grid['status']}, G-1 {grid['G-1']}, G-2 {grid['G-2']}, "
                  f"G-3 {grid['G-3']}, "
                  f"G-4 {grid['G-4']}, min F_judged {_fmt(grid['min_F_judged_kN'])} kN",
                  f"- G-1 failures {grid['G-1_fail']}", f"- G-3 {grid['G-3_problems']}",
                  f"- G-4 {grid['G-4_problems']}",
                  f"- between 10.400 and 10.414589 kN: {grid['between_thresholds']}", "",
                  "| setting | centre | R_c | M_c | P_c | ok |", "|---|---|---|---|---|---|"]
        lines += [f"| {c['setting']} | {c['centre']} | {_fmt(c['R_c'])} | {_fmt(c['M_c'])} | "
                  f"{_fmt(c['P_c'])} | {c['ok']} |" for c in grid["cells"]]
    for label, block in (("(na) R-T", result["R-T"]), ("(da) R-S", result["R-S"])):
        for name, item in block.items():
            lines += ["", f"## {label} {name}", "", f"- checks {item['checks']}",
                      f"- complete {item['complete']}, missing {len(item['missing'])}, "
                      f"undecidable {item['undecidable'][:5]}, errors {item['errors']}",
                      f"- C-2 violating pairs {len(item['C-2_violations'])}: "
                      f"{dict(list(item['C-2_violations'].items())[:5])}"]
            lines += [f"- items only (rev1 R1-2) {key}: L {pair['items_only_L']}, "
                      f"cand {pair['items_only_cand']}"
                      for key, pair in item["pairs"].items()
                      if pair.get("items_only_L") or pair.get("items_only_cand")]
            if "ready" in item:
                ready = item["ready"]
                lines.append(f"- READY: changed {ready['changed']}, population "
                             f"{ready['population']}, exceptions {ready['exceptions']}, median "
                             f"{_fmt(ready['median_s'])} s, max {_fmt(ready['max_s'])} s "
                             f"({ready['basis']})")
    rp0 = result["R-P0"]
    lines += ["", "## R-P0", "", f"- needed {rp0['needed']}, reproduced {rp0['reproduced']}, "
              f"missing {rp0['missing'][:10]}, H-5 {rp0['H-5'][:5]}", "", "## Verdict", "",
              f"- candidates {result['candidates']}", f"- ranking {result['ranking']}",
              f"- stops {result['stops']}", ""]
    return "\n".join(lines)


def default_inputs(directory: Path = REV_DIR) -> list[Path]:
    return sorted(directory.glob("rev_R*.jsonl"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--out", type=Path, default=None, help="new Markdown file")
    args = parser.parse_args(argv)
    problems = sealed_rules_problems()
    if problems:
        print(f"input error (H-1): {problems}")
        print(json.dumps({"stop": "H-1", "reasons": problems}))
        return 2
    if args.out is not None and args.out.exists():
        print(f"input error: --out {args.out} exists (new files only)")
        return 2
    sources = args.files or default_inputs()
    try:
        lines = [line for path in sources for line in read_lines(path)]
        stored = load_stored()
    except (OSError, ValueError) as exc:
        print(f"input error: {exc!r}")
        return 2
    result = judge(lines, stored)
    report = report_markdown(result, sources)
    print(report)
    if args.out is not None:
        with args.out.open("x", encoding="utf-8") as handle:
            handle.write(report)
    print(json.dumps({"candidates": result["candidates"], "ranking": result["ranking"],
                      "R-0": result["R-0"]["pass"], "stops": result["stops"]}))
    return 1 if is_stop_result(result) else 0


def is_stop_result(result: dict) -> bool:
    """Exit 1: a stop condition, an undecidable / ask / stop candidate, or an expected
    candidate without R-G lines (audit item (ga))."""
    return bool(result["stops"]) or any(
        verdict["verdict"] in ("undecidable", "ask", "stop") or verdict.get("not_run")
        for verdict in result["candidates"].values())


if __name__ == "__main__":
    sys.exit(main())
