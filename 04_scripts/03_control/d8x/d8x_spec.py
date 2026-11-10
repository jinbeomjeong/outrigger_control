"""D8x rules as data: seals, the point tables read from the rules text, thresholds, expected keys.

Sources (both sealed; the judge refuses to run when either sha256 differs):
  ``06_analysis/02_control/d8x/d8x_rules.md``       original, sha256 a377b9bb...
  ``06_analysis/02_control/d8x/d8x_rules_rev1.md``  rev1 (nose-up 3.6 deg, d45 W threshold 1.01),
                                                    sha256 ad16f452...
The points are not typed in here: :func:`rules_point_tables` reads the (A) / (B) / (C) tables of
section 1.2 and the W name table of section 5.1 from the rules files, a later file replacing a
whole table it repeats (rev1 replaces 1.2 (A) (B) (C); 5.1 names stay the original's). The floor
half-spans come from ``outrigger_sim.control.target.VERIFICATION_EXT_HALF_SPANS_DEG`` (rev1 1.1);
:func:`verification_usage` is the asymmetric R_v of rev1 1.1.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(ROOT / "03_src") not in sys.path:
    sys.path.insert(0, str(ROOT / "03_src"))

from outrigger_sim.control.target import VERIFICATION_EXT_HALF_SPANS_DEG  # noqa: E402
from outrigger_sim.hydraulics.v5_options import (  # noqa: E402
    EXTEND_START_LAS_K1_CONTROLLER_TAG,
    LAS_K1_CONTROLLER_TAG,
    LIFTOFF_SLOW_TAG_SUFFIX,
    ORDER_GATE_TAG_SUFFIX,
    is_liftoff_slow_tag,  # noqa: F401  (re-exported: d8x_judge E-6 LAS-b tag test)
)

D8X_DIR = ROOT / "06_analysis" / "02_control" / "d8x"
RULES_FILES = (
    ("original", D8X_DIR / "d8x_rules.md",
     "a377b9bb028385bb7d7d97312a71816ba0ca758e2cb193e25b2d092fff064da8"),
    ("rev1", D8X_DIR / "d8x_rules_rev1.md",
     "ad16f452fb4dce7395a059c73d7caf213f1a9a69f18af8d230bf03f4518e80d4"),
    ("rev2", D8X_DIR / "d8x_rules_rev2.md",
     "5f3fa620fe704834a9b6c0a65824b29b75e2a527ea8e97a17abb5e07987a8c27"),
)
"""(revision, path, sealed sha256 of the raw bytes; the files are ``-text`` in git). rev2 is an
interpretation supplement without point tables."""
CURRENT_RULES_REV = "rev1"
"""Revision of the point tables in force (rev1 1.2; rev2 has no tables); the point file's
``rules_rev``."""
POINTS_PATH = D8X_DIR / "d8x_points.json"
POINTS_SCHEMA = "d8x_points/1"
PARAMS_PATH = ROOT / "02_params" / "rexome33.yaml"

LEVELS = ("top", "middle", "bottom")
LEVEL_LETTER = {"top": "T", "middle": "M", "bottom": "B"}
MASTS = ("rigid", "stiff", "upper", "lower")
GUARD_EXTRA_N = 5000.0
"""Rules header: F_D8 = F_min + 5,000 N."""
FLAG_EXTRA_N = 2000.0
"""Rules 10 FLAG (i): J1 or J2 below F_D8 + 2 kN."""
ATTITUDE_LIMIT_DEG = 0.2
READY_LIMIT_S = 120.0
MOVING_LIMIT_BAR = 210.0
LOCKED_LIMIT_BAR = 350.0
STROKE_GUARD_M = 0.6828
STROKE_FLAG_MARGIN_MM = 5.0
G0_4_ERROR_FLAG_DEG = 0.02
LIFT_WINDOW_MIN_S = 1.0
"""Rules 6 E-8."""
STROKE_EVENTS = ("FAULT_STROKE_END", "WARN_LIFT_STROKE_LIMITED", "FAULT_LIFT_STROKE_LIMIT")
"""Rules 4.1 J7 (``FAULT_LIFT_STROKE_LIMIT*`` by prefix)."""
WARN_ALLOWED = ("WARN_PROBE_STIFFNESS_OUT_OF_RANGE",)
"""Rules 4.1 J9 allow list."""
LIFTOFF_SLOW_EVENT = "INFO_LIFTOFF_SLOW"
SOIL_EVENTS = ("soil_mode_start", "INFO_LOC_FLAT_SOIL_MARGIN", "INFO_LOC_CLEARANCE_MARGIN",
               "INFO_LOC_REVOKED")
"""Rules 7 V-1: Chrono rows inherit the K1 result only without these."""

G0_4_RV_HAT_MAX = 1.005
G0_4_RV_HAT_MAX_D45 = 1.01
"""Rev1 4.3 (record only since rev2 3): for_level R_v hat of the W candidates, d45** 1.01,
the others 1.005."""
G0_4_ERROR_MAX_DEG = 0.037
G0_REUSE_REF = "3da8daa:06_analysis/00_dynamics/d8x_g0.json"
G0_REUSE_BLOB = "26e90fd07ea0c29b8b77d589139b5ef89369a92b"
G0_REUSE_COMMIT = "3da8daa"
G0_PATH_FILES = ("04_scripts/01_dynamics/run_target_envelope.py",
                 "04_scripts/01_dynamics/run_s6_slope_boundary_check.py",
                 "04_scripts/01_dynamics/dyn_model.py", "02_params/rexome33.yaml")
"""Rev1 3: G0 path files whose blob ids must equal 3da8daa for the 33 reused evaluations
(plus the import targets the G0 records list)."""
G0_REUSED_POINTS = ("pitch+", "roll+", "roll-", "r+p+0.25", "r+p+0.5", "r+p+0.75", "r-p+0.5",
                    "d45++", "d45-+", "rpX", "rpX-+")
G0_RERUN_POINTS = ("pitch-", "r+p-0.25", "r+p-0.5", "r+p-0.75", "r-p-0.5", "d45+-", "d45--",
                   "rpX+-", "rpX--")
G0_4_JUDGED = {"top": ("pitch+", "pitch-", "roll+", "rpX"), "middle": (), "bottom": ()}
"""Rev2 3 gate scope: the L1-R rows #7 .. #11 floors at the top, fdown3.7 / fup3.6 / roll5.7 /
rpX (= the (A) tags pitch+ / pitch- / roll+ and rpX); #12 / #13 (middle / bottom rpX) and
rollm5.7 are recorded only."""
W_TRUE_RV_MAX = 1.01
"""Rev2 3: W eligibility = true R_v (rev1 1.2) <= 1 + eps_u; the for_level R_v hat is a record."""
SETTLE_MAP_BY_ENGINE = {"L2b": "identity", "L1-R": "level"}
"""Rev2 1 / E-4b: Chrono settle map per engine (``run_S7C.SETTLE_MAP_BY_ENGINE``, C-R17)."""
SCENARIO_GROUPS = {1: "G2-R", 7: "D8", 11: "G2-R", 14: "G2-R"}
"""Rev2 6: rows whose scenario group the rules name (L2b fdown3.7 = H4V ``G2-R``); the other
rows must record a group (E-5) that is reported."""
LAS_TAG_SUFFIX = LIFTOFF_SLOW_TAG_SUFFIX
"""Rev2 4: a D8x row runs with LAS-b on; its tag carries this suffix (``final_C4G2`` = off),
possibly followed by the K1 suffix (``final_C4G2_LAS_K1``): test it with
``v5_options.is_liftoff_slow_tag``, not ``str.endswith``."""
W_MIRRORS = {"r+p-0.5": "rpX+-", "r-p+0.5": "rpX-+", "r-p-0.5": "rpX--"}
"""Rules 5.1: mirrored diagonals whose R-c top J1 joins m(p)."""

KT_REL_CHRONO = 0.4021968558889507
"""``run_s6_slope_boundary_check.KT_REL_CHRONO`` (td_kt variants)."""
RA_CONFIG_NAME = "C2_tv0.1"
RA_ROBUST_LOWER_TAGS = ("pitch+", "pitch-", "roll+", "roll-", "r+p+0.5", "d45++")
RA_KT_TAGS = ("pitch+", "pitch-", "roll+", "roll-", "r+p+0.5", "r+p+0.25", "d45++")
RA_BETAS_PA = (0.69e9, 1.6e9)
CHRONO_NOSE_UP_FLOOR = "fup3.6"
"""Rev1 4.4: ``fup3.7`` of the original 4.4 table reads ``fup3.6``."""
RC_SETTINGS = ("VB", "V0")
RC_EPS = {"off": (0.0, 2e-3), "on": (0.0,)}
RC_CRAWLER_SCALES = (1.0, 3.0)
EXPECTED_COUNTS = {"G0": 60, "ra_off": 910, "ra_on": 192, "rc_off": 192, "rc_on": 96, "C": 19}
"""Rules 3 / E-1: R-a 1,102 = 910 + 192 K1 pairs, R-c 288 = 192 + 96, Chrono 18 + 1."""
DEFAULT_TAGS = {"ra": LAS_K1_CONTROLLER_TAG, "VB": EXTEND_START_LAS_K1_CONTROLLER_TAG,
                "V0": LAS_K1_CONTROLLER_TAG}
"""Preset tags since the K1 switch (``final_C4G2_LAS_K1`` for V0 / the harness preset,
``final_C4G2_P3_LAS_K1`` for VB with the ③ bound; rules 2.1 had the ``_LAS`` tags at sealing).
These are the K1-on arm's tags; the off arm's are :func:`arm_tag`."""


def arm_tag(preset_tag: str, k1: str) -> str:
    """Expected controller tag of a harness K1 arm (R-a / R-c) for ``preset_tag``.

    The recorded tag names the effective switches (``v5_options.controller_tag``): the on arm
    records the preset tag with ``_K1``, the off arm (gate installed off) the same tag without
    it (``final_C4G2_LAS_K1`` -> ``final_C4G2_LAS``).

    Raises:
        ValueError: ``k1`` is not ``off`` / ``on``.
    """
    if k1 not in ("off", "on"):
        raise ValueError(f"K1 arm {k1!r}: expected off / on")
    base = preset_tag.removesuffix(ORDER_GATE_TAG_SUFFIX)
    return base + ORDER_GATE_TAG_SUFFIX if k1 == "on" else base


# ------------------------------------------------------------------------------------ seals
def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seal_report() -> dict:
    """Raw sha256 of each rules file against the sealed value and its ``.sha256`` file."""
    report = {}
    for rev, path, sealed in RULES_FILES:
        actual = file_sha256(path) if path.is_file() else None
        sidecar = path.with_suffix(".sha256")
        recorded = sidecar.read_text(encoding="utf-8").split()[0] if sidecar.is_file() else None
        report[rev] = {"path": path.relative_to(ROOT).as_posix(), "sha256": actual,
                       "sealed": sealed, "sidecar": recorded,
                       "ok": actual == sealed == recorded}
    return report


def seals_ok(report: dict | None = None) -> bool:
    return all(entry["ok"] for entry in (report or seal_report()).values())


# ------------------------------------------------------------------------------------ usage
def verification_usage(roll_deg: float, pitch_deg: float) -> float:
    """Rev1 1.1: ``|phi| / 5.7 + |theta| / Theta(theta)`` (nose up = theta < 0)."""
    spans = VERIFICATION_EXT_HALF_SPANS_DEG
    pitch_span = spans["pitch_nose_down"] if pitch_deg >= 0.0 else spans["pitch_nose_up"]
    return abs(roll_deg) / spans["roll"] + abs(pitch_deg) / pitch_span


# ------------------------------------------------------------------------------ rules tables
_NUMBER = r"[−\-]?\d+(?:\.\d+)?"
_ROW = re.compile(rf"^\|\s*`([^`]+)`\s*\|\s*({_NUMBER})\s*\|\s*({_NUMBER})\s*\|"
                  rf"(?:\s*({_NUMBER})\s*\|)?")
_NAME_PAIR = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|")
_BLOCK_MARKERS = (("**(A)", "A"), ("**(B)", "B"), ("**(C)", "C"), ("### 5.1", "W"),
                  ("## 5.1", "W"))


def _plain(cell: str) -> str:
    return cell.replace("*", "").replace("−", "-").strip()


def _block_of(line: str) -> str | None | bool:
    """The table block a line opens, None for a line that closes one, False for neither."""
    for marker, block in _BLOCK_MARKERS:
        if line.startswith(marker):
            return block
    if line.startswith(("#", "**")):
        return None
    return False


def parse_rules_tables(text: str) -> dict[str, list]:
    """Tables (A) / (B) / (C) of 1.2 (name, roll, pitch, R_v text) and the W name table of 5.1."""
    tables: dict[str, list] = {}
    block = None
    for raw in text.splitlines():
        line = raw.strip()
        opened = _block_of(line)
        if opened is not False:
            block = opened
            if block is not None:
                tables[block] = []
            continue
        if block is None or not line.startswith("|"):
            continue
        cleaned = "|".join(_plain(cell) if "`" not in cell else cell.replace("*", "")
                           for cell in line.split("|"))
        if block == "W":
            match = _NAME_PAIR.match(cleaned)
            if match:
                tables[block].append((match.group(1), match.group(2)))
            continue
        match = _ROW.match(cleaned)
        if match:
            name, roll, pitch, usage = match.groups()
            tables[block].append((name, float(_plain(roll)), float(_plain(pitch)),
                                  None if usage is None else _plain(usage)))
    return {key: rows for key, rows in tables.items() if rows}


def rules_point_tables() -> dict[str, list]:
    """The tables in force: each rules file in order, a later table replacing an earlier one."""
    merged: dict[str, list] = {}
    sources: dict[str, str] = {}
    for rev, path, _ in RULES_FILES:
        for block, rows in parse_rules_tables(path.read_text(encoding="utf-8")).items():
            merged[block] = rows
            sources[block] = rev
    return {"tables": merged, "sources": sources}


def _point_entries(rows: list, key: str) -> list[dict]:
    entries = []
    for name, roll, pitch, usage_text in rows:
        usage = verification_usage(roll, pitch)
        entry = {key: name, "roll_deg": roll, "pitch_deg": pitch, "R_v": usage}
        if usage_text is not None:
            decimals = len(usage_text.split(".")[1]) if "." in usage_text else 0
            entry["R_v_table"] = usage_text
            entry["R_v_table_ok"] = round(usage, decimals) == float(usage_text)
        entries.append(entry)
    return entries


def build_points() -> dict:
    """The point file content (rules 1.2 of the revision in force, I-3).

    Raises:
        ValueError: A table is missing.
    """
    read = rules_point_tables()
    tables = read["tables"]
    missing = [block for block in ("A", "B", "C", "W") if block not in tables]
    if missing:
        raise ValueError(f"rules tables not found: {missing}")
    ra = _point_entries(tables["A"], "tag")
    rpx = _point_entries(tables["B"], "name")
    axis = _point_entries(tables["C"], "name")
    seals = seal_report()
    return {
        "schema": POINTS_SCHEMA, "rules_rev": CURRENT_RULES_REV,
        "rules": {rev: {"path": entry["path"], "sha256": entry["sha256"]}
                  for rev, entry in seals.items()},
        "table_sources": read["sources"], "half_spans_deg": dict(VERIFICATION_EXT_HALF_SPANS_DEG),
        "levels": list(LEVELS), "ra_points": ra, "rpx_points": rpx, "axis_vertices": axis,
        "g0_points": [entry["tag"] for entry in ra] + [entry["name"] for entry in rpx],
        "rc_floors": [entry["name"] for entry in axis] + [entry["name"] for entry in rpx],
        "w_candidates": [{"ra_point": point, "floor": floor} for point, floor in tables["W"]],
        "w_mirrors": dict(W_MIRRORS),
    }


def point_table_problems(doc: dict) -> list[str]:
    """R_v column mismatches and name problems of a point document."""
    problems = [f"{entry.get('tag') or entry.get('name')}: R_v {entry['R_v']:.9f} vs table "
                f"{entry['R_v_table']}"
                for entry in [*doc["ra_points"], *doc["rpx_points"], *doc["axis_vertices"]]
                if entry.get("R_v_table_ok") is False]
    tags = {entry["tag"] for entry in doc["ra_points"]}
    problems += [f"W candidate {c['ra_point']} not an (A) tag" for c in doc["w_candidates"]
                 if c["ra_point"] not in tags]
    problems += [f"mirror {a} -> {b} unknown" for a, b in W_MIRRORS.items()
                 if a not in tags or b not in doc["rc_floors"]]
    if len(doc["ra_points"]) != 16 or len(doc["rpx_points"]) != 4 or len(doc["axis_vertices"]) != 4:
        problems.append("point counts are not 16 / 4 / 4")
    return problems


def points_by_name(doc: dict) -> dict[str, tuple[float, float]]:
    out = {e["tag"]: (e["roll_deg"], e["pitch_deg"]) for e in doc["ra_points"]}
    out.update({e["name"]: (e["roll_deg"], e["pitch_deg"])
                for e in [*doc["rpx_points"], *doc["axis_vertices"]]})
    return out


# ----------------------------------------------------------------------------- expected keys
def expected_ra_ids(doc: dict, stages: tuple[str, ...]) -> list[str]:
    """Run ids of R-a (``acc_d8.d8x_cases`` after ``r8.apply``), in case order."""
    ids = []
    config = RA_CONFIG_NAME
    kt_scales = (KT_REL_CHRONO, 0.3 * KT_REL_CHRONO, 3.0 * KT_REL_CHRONO)
    for level in LEVELS:
        for entry in doc["ra_points"]:
            tag = entry["tag"]
            if "main" in stages:
                ids += [f"main|{config}|{level}|{mast}|{tag}" for mast in MASTS]
            if "robust" in stages:
                ids += _robust_ids(config, level, tag)
            if "kt" in stages and tag in RA_KT_TAGS:
                masts = ("rigid", "stiff") if level == "top" else ("rigid",)
                for mast in masts:
                    for scale in kt_scales:
                        ids.append(f"kt|{config}|{level}|{mast}|{tag}|{scale:.4f}")
                        if level == "top":
                            ids.append(f"ktd0|{config}|{level}|{mast}|{tag}|{scale:.4f}")
    return ids


def _robust_ids(config: str, level: str, tag: str) -> list[str]:
    ids = []
    if level == "top":
        for mast in MASTS:
            ids += [f"seed|{config}|{level}|{mast}|{tag}|{s}" for s in (1, 2)]
            ids += [f"d0|{config}|{level}|{mast}|{tag}|{s}" for s in range(3)]
            ids += [f"beta|{config}|{level}|{mast}|{tag}|{b:g}" for b in RA_BETAS_PA]
        return ids
    if tag in RA_ROBUST_LOWER_TAGS:
        for mast in MASTS:
            ids += [f"beta|{config}|{level}|{mast}|{tag}|{b:g}" for b in RA_BETAS_PA]
            ids.append(f"d0|{config}|{level}|{mast}|{tag}|0")
    return ids


def rc_row_key(level: str, floor: str, scale: float) -> str:
    """``D1Row.key`` of an H-R-X row."""
    return f"D1|H-R-X|rigid|{LEVEL_LETTER[level]}|{floor}|K{scale:g}"


def expected_rc_keys(doc: dict, k1: str) -> list[str]:
    """``<row key>|<setting>|e<eps>`` of R-c (``d1_rows.d8x_jobs``)."""
    keys = []
    for setting in RC_SETTINGS:
        for level in LEVELS:
            for floor in doc["rc_floors"]:
                for scale in RC_CRAWLER_SCALES:
                    keys += [f"{rc_row_key(level, floor, scale)}|{setting}|e{eps:g}"
                             for eps in RC_EPS[k1]]
    return keys


def chrono_rows(w_floor: str | None, v_floor: str | None) -> list[dict]:
    """Rules 4.4 (floor names of rev1 4.4): 18 first-order rows and the second-order row."""
    fup = CHRONO_NOSE_UP_FLOOR
    w = w_floor or "<W>"
    v = v_floor or "<V>"
    table = [
        ("K24", "L2b", 1.0, 4.0, "top", "fdown3.7"), ("K24", "L2b", 1.0, 4.0, "top", fup),
        ("K24", "L2b", 1.0, 4.0, "top", "roll5.7"), ("K24", "L2b", 1.0, 4.0, "top", "rollm5.7"),
        ("K24", "L2b", 1.0, 4.0, "top", "rpX"), ("K24", "L2b", 1.0, 4.0, "top", w),
        ("C1_D8", "L1-R", 1.6, None, "top", "fdown3.7"), ("C1_D8", "L1-R", 1.6, None, "top", fup),
        ("C1_D8", "L1-R", 1.6, None, "top", "roll5.7"), ("C1_D8", "L1-R", 1.6, None, "top", "rpX"),
        ("C1_H4V", "L1-R", 1.0, None, "top", "fdown3.7"),
        ("A", "L2b", 1.0, 0.0, "middle", "rpX"), ("A", "L2b", 1.0, 0.0, "bottom", "rpX"),
        ("K0V", "L2b", 1.0, 0.0, "top", "fdown3.7"), ("K0V", "L2b", 1.0, 0.0, "top", fup),
        ("K0V", "L2b", 1.0, 0.0, "top", "roll5.7"), ("K0V", "L2b", 1.0, 0.0, "top", "rollm5.7"),
        ("K0V", "L2b", 1.0, 0.0, "top", "rpX"), ("K8", "L2b", 1.0, 8.0, "top", v),
    ]
    rows = []
    for number, (family, engine, beta, fs, level, floor) in enumerate(table, 1):
        if family in ("K24", "K0V", "K8", "A"):
            suffix = f"_Fs{fs:g}"
        elif family == "C1_D8":
            suffix = f"_b{beta:g}"
        else:
            suffix = ""
        rows.append({"number": number, "name": f"D8X_{family}_{level}_{floor}{suffix}",
                     "family": family, "engine": engine, "beta_GPa": beta, "fs_kN": fs,
                     "level": level, "floor": floor, "order": 2 if number == 19 else 1})
    return rows
