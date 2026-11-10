"""K-2 judge, path 1 (``06_analysis/02_control/k2/k2_touch_creep_rules.md`` 8, 9.1-5). Reads the raw results;
never runs a simulation.

Sub-commands:
  points      write ``k2_points_5p5_3p5.json`` (rules 3.2, ``d8x_diag.diamond_points(5.5, 3.5)``), or ``--check`` it
              (rev1 2: file == diamond_points <= 1e-12 deg; vs the rules table d45 <= 2e-5 deg, others exact)
  prelaunch   run-start record ``k2_prelaunch_<bundle>.json`` (I-2, I-3, I-7; V-3 key list, ``--write-keys``)
  judge-v2    V-2 D8x R-a, off + K-2 arms x K1 off / on (G-A, I-4, E-1 .. E-9, SH-1 .. SH-6)
  judge-v3    V-3 dissipation arms x {off, K-2} on the 273 keys (G-B, E-5, I-9)
  judge-v4    V-4 5.5 / 3.5 boundary, top, K1 off (G-C)
  judge-v5    V-5 acceptance regression (rev2 1 / rev4): criteria.md absolute items on the K-2 arm, K-2
              evidence, pass -> fail vs the off arm of the same commit (G-D); input k2_v5_flatten.py files
  judge-v6    V-6 Chrono 8 rows (G-E: K-2 rows; off rows recorded; 5.4 prediction table; SH-1 .. SH-6 rev2 3)
  record-v7   V-7 SCM 4 rows (record only)
  selftest-v5-stored  the V-5 reader on the stored acceptance outputs as both arms (rev4 2 format check)
  report      gates G-S .. G-F and the grade (10) from the outputs above

Common contract: ``--out <file>`` (the report JSON), ``--format json|md``; exit 0 pass, 1 fail, 2 not judgeable /
input error (a missing result key is 2), 3 internal error; the last stdout line is JSON. The rules file and its
addenda rev1 .. rev5 must match their sealed sha256 (``k2_touch_creep_rules[_revN].sha256``, the values this judge
implements) and the dynamics spec its rules 3.3 sha256 (exit 2 otherwise).
Every judging command prints its field map (rules item <-> raw result key).
Interpreter: python-dev or dynamics-dev (numpy, PyYAML; no simulation imports).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import subprocess
import sys
import traceback
from collections.abc import Iterable
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D8X_DIR = HERE.parent / "d8x"
ACCEPTANCE_DIR = HERE.parent / "touch_phase" / "acceptance"
for _folder in (HERE, D8X_DIR, ACCEPTANCE_DIR, ROOT / "03_src"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

import d8x_judge  # noqa: E402  (row J items, loaders, NotJudgeable)
import k2_record  # noqa: E402  (SH-1 / SH-2 definitions of the harness record, reused for the V-6 rows)

from outrigger_sim.hydraulics import v5_options  # noqa: E402

K2_DIR = ROOT / "06_analysis" / "02_control" / "k2"
RULES_PATH = K2_DIR / "k2_touch_creep_rules.md"
RULES_SEAL_PATH = K2_DIR / "k2_touch_creep_rules.sha256"
RULES_REV1_SHA256 = "5ba081c62f8aef0edc5bb99119d7586b0d2914761582f2323c289f472f244776"
RULES_SHA256 = "a3658197bdab02870a0b362144606f404021ebac90662a35efacfa8dbe477263"
RULES_REV1_SHA256 = "5ba081c62f8aef0edc5bb99119d7586b0d2914761582f2323c289f472f244776"
RULES_REV2_SHA256 = "b3f1b41f27030c75aec726d2a3feb5abc36697864e0d83766a8fe0c4460394ea"
RULES_REV3_SHA256 = "8bcdb0ed1fdf6d730ac781929e93b233972d1e80566e1ae14ffb7ddf049d6e61"
RULES_REV4_SHA256 = "82160ff54874e3d43bf7c5a1ae96d6e8612b1e7635aaccea39a4299352ce00c5"
RULES_REV5_SHA256 = "73b877580ec5dc94a46a38d2ed620372cddd17dd38eef06126d84843b485eccc"
SEALED_RULES = (
    (RULES_PATH, RULES_SEAL_PATH, RULES_SHA256),
    *(
        (K2_DIR / f"k2_touch_creep_rules_rev{n}.md", K2_DIR / f"k2_touch_creep_rules_rev{n}.sha256", sha)
        for n, sha in ((1, RULES_REV1_SHA256), (2, RULES_REV2_SHA256), (3, RULES_REV3_SHA256),
                       (4, RULES_REV4_SHA256), (5, RULES_REV5_SHA256))
    ),
)
"""Rules file, seal file, sha256 this judge implements (rev2 8: path 1 checks the original and rev1 .. rev5
seals; later revisions win: rev5 > rev4 > rev3 > rev2 > rev1 > original)."""
DYN_SPEC_PATH = K2_DIR / "k2_dyn_spec.md"
DYN_SPEC_SHA256 = "502b0bb78558d40586cbcddb718b6c5d53529de4e78369f454762c9fe73727ff"
"""Rules 3.3: raw sha256 of the dynamics spec."""
POINTS_PATH = K2_DIR / "k2_points_5p5_3p5.json"
POINTS_SCHEMA = "k2_points/1"
HALF_SPANS_DEG = (5.5, 3.5)
D45_TABLE_DEG = 19.25 / 9.0
"""Rules 3.2 table: ``d45 = 5.5 * 3.5 / 9``."""
POINT_TOLERANCE_DEG = 1e-12
"""Rules 3.2 / rev1 2: point file == ``diamond_points(5.5, 3.5)`` per component."""
D45_TABLE_TOLERANCE_DEG = 2e-5
"""Rules rev1 2: the four d45 points may differ from the rules 3.2 table (19.25 / 9 deg) by this much
(``diamond_points`` rounds them to 2.1389 deg, the run key); the other twelve points must equal it."""
V3_KEYS_SHA256 = "d4a030d71e4a365e328fbbf7caa212c378a8671fed8ba206d25b50666255cf95"
V3_EXPECTED_KEYS = 273
V3_NOSE_DOWN_TAGS = ("pitch+", "r+p+0.25", "r+p+0.5", "r+p+0.75", "d45++", "d45-+", "r-p+0.5")
"""Rules 3.3 selection rule 2: top rows on these points (floor pitch > 0)."""
STORED_RA_OFF_SHA256_PREFIX = "100985bf"
EXPECTED_ROWS = {"v2": {"off": 910, "on": 192}, "v4": 596, "v6": 8, "v7": 4}
V3_ARMS = ("H0", "L1eq", "L1eq_fs", "L1eq_zm", "AUG", "AUG_crc2", "AUG_eps")
V3_JUDGED_ARMS = ("H0", "L1eq", "L1eq_fs", "L1eq_zm", "AUG", "AUG_eps")
V3_DISS_PRESETS = {
    "H0": "none",
    "L1eq": "l1eq",
    "L1eq_fs": "l1eq_fs",
    "L1eq_zm": "l1eq_zm",
    "AUG": "aug",
    "AUG_crc2": "aug_crc2",
    "AUG_eps": "aug_eps",
}
LEG_NAMES = ("FL", "FR", "RL", "RR")
LATCH_EVENT = "INFO_TOUCH_CREEP_LATCH"
CAP_EVENT = "INFO_TOUCH_CREEP_CAP"
DIP_EVENT = "INFO_TOUCH_DIP_HELD"
LATCH_WINDOW_SAMPLES = 5
CONTROL_PERIOD_S = 0.1
NOISE_CP_LIMIT = 0.03
"""V-5 noise L2: one-sided CP 95 % upper bound <= 3 % (rules 3.4)."""
SH3_READY_DELAY_S = 3.0
SH4_J1_EROSION_N = -3.0e3
SH6_MARGIN_N = 2.0e3
CHRONO_ROWS = (
    "K2_L1_top_fdown3.5_Fs0_off",
    "K2_L1_top_fdown3.5_Fs0_tcl",
    "K2_L1_top_k2pp025_Fs0_off",
    "K2_L1_top_k2pp025_Fs0_tcl",
    "K2_L2b_top_fdown3.5_Fs4_off",
    "K2_L2b_top_fdown3.5_Fs4_tcl",
    "K2_L2b_top_k2pp025_Fs4_off",
    "K2_L2b_top_k2pp025_Fs4_tcl",
)
CHRONO_FLOORS_DEG = {"fdown3.5": (0.0, 3.5), "k2pp025": (1.375, 2.625)}
EXIT_PASS, EXIT_FAIL, EXIT_NOT_JUDGEABLE, EXIT_INTERNAL = 0, 1, 2, 3
NotJudgeable = d8x_judge.NotJudgeable

FIELD_MAP_K2 = {
    **d8x_judge.FIELD_MAP_HARNESS,
    "E-4": "d8x.events: K-2 rows INFO_TOUCH_CREEP_LATCH:<leg> for all 4 legs and INFO_TOUCH_DIP_HELD 0; off rows "
    "no INFO_TOUCH_CREEP_*",
    "E-6": "controller_tag (acc_d8 row) and touch_creep_latch == the arm's expected tag / switch",
    "E-7": "angles_deg == point file (<= 1e-9 deg)",
    "E-8": "d8x.J3_pad_lift_samples (from the 1 ms pad series) is an int and series_file is named",
    "I-4": "commands_sha256 of the off arm == stored D8x ra_off.json / ra_on.json rows",
    "I-9": "aug_arm, is_kplant (row) and k2.aug.{arm, is_kplant, preset, case_id, valve_open_fraction_touch_to_lift "
    "(4 values in [0, 1])}",
    "E-5 (rev3 1)": "k2.aug.plant_aug.{preset, options key set per arm, resolved values (relative 1e-9)}; V-2 / V-4 "
    "aug_arm and k2.aug None",
    "SH-1": "k2.SH1_lift_chunks_after_latch (per leg) > 0 on a K-2 row",
    "SH-2": "median k2.SH2_rate_amp_deg_s of the K-2 rows > median of the off rows (per bundle)",
    "SH-3": "t_ready_s(K-2) - t_ready_s(off) > 3.0 s (per pair)",
    "SH-4": "min J1(K-2 rows) - min J1(off rows) < -3 kN (per bundle)",
    "SH-5": "k2.event_counts.INFO_TOUCH_CREEP_CAP > 0 on a K-2 row",
    "SH-6": "J1 or J2 < F_D8 + 2 kN on a K-2 row",
    "D_hat (rev1 4, record)": "k2.dhat_N, k2.dhat_window_open_legs, k2.dhat_window_stroke_mm; pairs by key, "
    "quantiles 0 / 5 / 50 / 95 / 100 % of K-2 - off [kN], |difference| >= 5 kN listed",
}


# ----------------------------------------------------------------------------------- helpers
def raw_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _seal_problem(rules_path: Path, seal_path: Path, expected_sha256: str | None) -> str | None:
    """One sealed rules file: raw sha256 == the first token of its ``.sha256`` (== the value this tool was built
    for, when given)."""
    try:
        sealed = seal_path.read_text(encoding="utf-8").split()[0]
        actual = raw_sha256(rules_path)
    except (FileNotFoundError, IndexError):
        return f"I-7 no seal or rules file {seal_path.name} / {rules_path.name}"
    if actual != sealed:
        return f"I-7 {rules_path.name} sha256 {actual} != sealed {sealed}"
    if expected_sha256 is not None and sealed != expected_sha256:
        return f"I-7 {seal_path.name} seal {sealed} != {expected_sha256} (this judge implements that revision)"
    return None


def seal_problems() -> list[str]:
    """I-7: the original rules, rev1 and rev2 raw sha256 == their seals (rev1 / rev2: == the revisions this judge
    implements), the dynamics spec == rules 3.3."""
    problems = []
    for rules_path, seal_path, expected in SEALED_RULES:
        problem = _seal_problem(rules_path, seal_path, expected)
        if problem:
            problems.append(problem)
    if raw_sha256(DYN_SPEC_PATH) != DYN_SPEC_SHA256:
        problems.append(
            f"3.3 {DYN_SPEC_PATH.name} sha256 {raw_sha256(DYN_SPEC_PATH)} != {DYN_SPEC_SHA256}"
        )
    return problems


def _runs_of(path: Path) -> list[dict]:
    """Rows of an acc_d8 output (``{"runs": [...]}``) or of a ``.jsonl``."""
    path = Path(path)
    if path.suffix == ".jsonl":
        return d8x_judge._load_jsonl(path)
    return d8x_judge._load_json(path).get("runs", [])


def _event_names(row: dict) -> list[str]:
    return d8x_judge._event_names((row.get("d8x") or {}).get("events"))


def expected_tag(k1_on: bool, k2_on: bool) -> str:
    """V0 tag of a harness arm (rules 1.2): ``final_C4G2_LAS`` [+ ``_K1``] [+ ``_TCL``]."""
    tag = v5_options.LAS_K1_CONTROLLER_TAG if k1_on else v5_options.LAS_CONTROLLER_TAG
    return tag + v5_options.TOUCH_CREEP_TAG_SUFFIX if k2_on else tag


def f_d8_N() -> float:
    return d8x_judge.f_d8_N()


def _median(values: Iterable[float | None]) -> float | None:
    numbers = [v for v in values if d8x_judge._is_number(v)]
    return statistics.median(numbers) if numbers else None


# ---------------------------------------------------------------------------------- points
def diamond_points(roll_half_deg: float, pitch_half_deg: float) -> dict:
    """``d8x_diag.diamond_points`` itself, compiled from its source alone (importing ``d8x_diag`` would install the
    harness through ``acc_d8``)."""
    import ast

    source_path = ACCEPTANCE_DIR / "d8x_diag.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "diamond_points"
    )
    namespace: dict = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source_path), "exec"), namespace)  # noqa: S102
    return namespace["diamond_points"](roll_half_deg, pitch_half_deg)


def build_points() -> dict:
    """Rules 3.2 points (``d8x_diag.diamond_points(5.5, 3.5)``) and their check against the rules table."""
    points = diamond_points(*HALF_SPANS_DEG)
    roll_half, pitch_half = HALF_SPANS_DEG
    table = {}
    for tag in points:
        if tag.startswith("d45"):
            table[tag] = (
                math.copysign(D45_TABLE_DEG, 1 if tag[3] == "+" else -1),
                math.copysign(D45_TABLE_DEG, 1 if tag[4] == "+" else -1),
            )
        elif tag in ("pitch+", "pitch-", "roll+", "roll-"):
            table[tag] = points[tag]
        else:
            fraction = float(tag[4:])
            table[tag] = (
                (1 if tag[1] == "+" else -1) * fraction * roll_half,
                (1 if tag[3] == "+" else -1) * (1 - fraction) * pitch_half,
            )
    differences = {
        tag: max(abs(points[tag][0] - table[tag][0]), abs(points[tag][1] - table[tag][1]))
        for tag in points
    }
    return {
        "schema": POINTS_SCHEMA,
        "rules": {
            "path": str(RULES_PATH.relative_to(ROOT)).replace("\\", "/"),
            "sha256": raw_sha256(RULES_PATH),
        },
        "source": "d8x_diag.diamond_points(5.5, 3.5) (commit 6f2f7cb)",
        "half_spans_deg": list(HALF_SPANS_DEG),
        "ra_points": [
            {
                "tag": tag,
                "roll_deg": float(r),
                "pitch_deg": float(p),
                "R_v": abs(r) / roll_half + abs(p) / pitch_half,
            }
            for tag, (r, p) in points.items()
        ],
        "table_check": table_check(differences),
    }


def table_check(differences: dict[str, float]) -> dict:
    """Rules rev1 2: d45 points within :data:`D45_TABLE_TOLERANCE_DEG` of the table, the others equal."""
    d45 = {tag: d for tag, d in differences.items() if tag.startswith("d45")}
    others = {tag: d for tag, d in differences.items() if not tag.startswith("d45")}
    failing = {tag: d for tag, d in d45.items() if d > D45_TABLE_TOLERANCE_DEG}
    failing.update({tag: d for tag, d in others.items() if d != 0.0})
    return {
        "rule": "rev1 2: d45 |file - table| <= 2e-5 deg, the other 12 points == table",
        "d45_max_difference_deg": max(d45.values()),
        "other_max_difference_deg": max(others.values()),
        "failing": failing,
        "ok": not failing and len(d45) == 4 and len(others) == 12,
    }


def point_file_problems(path: Path) -> list[str]:
    """Rules 3.2 / rev1 2: the stored file's angles equal ``diamond_points(5.5, 3.5)`` within 1e-12 deg."""
    stored = d8x_judge._load_json(path)
    if stored.get("schema") != POINTS_SCHEMA:
        return [f"{path}: schema {stored.get('schema')!r}, expected {POINTS_SCHEMA!r}"]
    want = diamond_points(*HALF_SPANS_DEG)
    got = {p["tag"]: (float(p["roll_deg"]), float(p["pitch_deg"])) for p in stored["ra_points"]}
    if set(got) != set(want):
        return [f"{path}: tags {sorted(got)} != diamond_points {sorted(want)}"]
    differing = {
        tag: got[tag]
        for tag in want
        if max(abs(got[tag][0] - want[tag][0]), abs(got[tag][1] - want[tag][1]))
        > POINT_TOLERANCE_DEG
    }
    return [f"{path}: angles differ from diamond_points(5.5, 3.5): {differing}"] if differing else []


def cmd_points(args) -> tuple[int, dict]:
    doc = build_points()
    path = Path(args.points_file)
    problems = []
    check = doc["table_check"]
    if not check["ok"]:
        problems.append(f"rev1 2 rules table check failed: {check['failing']}")
    if args.check:
        problems += point_file_problems(path)
    else:
        path.write_bytes(
            (json.dumps(doc, indent=1) + "\n").encode("utf-8")
        )  # LF: the k2 folder is -text
    status = EXIT_NOT_JUDGEABLE if problems else EXIT_PASS
    return status, {
        "points_file": str(path),
        "ra_points": len(doc["ra_points"]),
        "table_check": doc["table_check"],
        "problems": problems,
    }


# ------------------------------------------------------------------------------- prelaunch
def v3_keys(ra_off_rows: list[dict]) -> list[str]:
    """Rules 3.3 selection: J3 > 0 rows, union top rows on the nose-down points; sorted."""
    keys = set()
    for row in ra_off_rows:
        d8x = row.get("d8x") or {}
        if (d8x.get("J3_pad_lift_samples") or 0) > 0:
            keys.add(row["id"])
        if row.get("level") == "top" and row.get("point") in V3_NOSE_DOWN_TAGS:
            keys.add(row["id"])
    return sorted(keys)


def keys_sha256(keys: Iterable[str]) -> str:
    return hashlib.sha256("\n".join(sorted(keys)).encode("utf-8")).hexdigest()


def _git_text(*args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    return done.stdout.strip() if done.returncode == 0 else ""


def _blob(path: Path) -> str | None:
    relative = str(Path(path).resolve().relative_to(ROOT)).replace("\\", "/")
    return _git_text("rev-parse", f"HEAD:{relative}") or None


def cmd_prelaunch(args) -> tuple[int, dict]:
    problems = seal_problems()
    status = _git_text("status", "--porcelain", "--untracked-files=no")
    if status:
        problems.append("I-2 git status not empty")
    record = {
        "bundle": args.bundle,
        "head": _git_text("rev-parse", "HEAD"),
        "git_status": status,
        "rules_sha256": raw_sha256(RULES_PATH),
        "dyn_spec_sha256": raw_sha256(DYN_SPEC_PATH),
        "plan_id": args.plan_id,
        "recount_script": None,
    }
    recount = HERE / "k2_recount.py"
    if recount.is_file():
        record["recount_script"] = {
            "path": "04_scripts/03_control/k2/k2_recount.py",
            "blob": _blob(recount),
        }
    else:
        problems.append("8 path-2 script k2_recount.py not committed")
    if args.bundle in ("v2", "v3"):
        record["tags"] = {
            "k1_off": [expected_tag(False, False), expected_tag(False, True)],
            "k1_on": [expected_tag(True, False), expected_tag(True, True)],
        }
    if args.bundle == "v4":
        if not POINTS_PATH.is_file():
            problems.append(f"3.2 no point file {POINTS_PATH}")
        else:
            record["points_sha256"] = raw_sha256(POINTS_PATH)
        record["tags"] = {"k1_off": [expected_tag(False, False), expected_tag(False, True)]}
    if args.bundle == "v3":
        _prelaunch_v3(args, record, problems)
    if args.python:
        record["python"] = d8x_judge._interpreter(args.python)
    record["problems"] = problems
    return (EXIT_NOT_JUDGEABLE if problems else EXIT_PASS), record


def _prelaunch_v3(args, record: dict, problems: list[str]) -> None:
    if not args.stored_off:
        problems.append("3.3 --stored-off ra_off.json needed for the V-3 key list")
        return
    sha = raw_sha256(Path(args.stored_off))
    if not sha.startswith(STORED_RA_OFF_SHA256_PREFIX):
        problems.append(
            f"3.3 stored ra_off.json sha256 {sha} does not start with {STORED_RA_OFF_SHA256_PREFIX}"
        )
    keys = v3_keys(_runs_of(Path(args.stored_off)))
    record["v3_keys"] = {"n": len(keys), "sha256": keys_sha256(keys), "stored_off_sha256": sha}
    if len(keys) != V3_EXPECTED_KEYS or keys_sha256(keys) != V3_KEYS_SHA256:
        problems.append(
            f"3.3 V-3 keys {len(keys)} / {keys_sha256(keys)} != {V3_EXPECTED_KEYS} / {V3_KEYS_SHA256}"
        )
    if args.write_keys:
        Path(args.write_keys).write_text("\n".join(keys) + "\n", encoding="utf-8")
        record["v3_keys"]["written"] = str(args.write_keys)


# ------------------------------------------------------------------------------- row judging
def k2_evidence_problems(names: list[str], k2_on: bool) -> list[str]:
    """E-4: latch events on all four legs and no dip hold (K-2), no creep event (off)."""
    latched = {name.split(":", 1)[1] for name in names if name.startswith(LATCH_EVENT + ":")}
    creep = [name for name in names if name.startswith("INFO_TOUCH_CREEP_")]
    dips = [name for name in names if name.startswith(DIP_EVENT)]
    if k2_on:
        problems = [] if latched == set(LEG_NAMES) else [f"E-4 latch events on {sorted(latched)}"]
        return problems + ([f"E-4 {len(dips)} {DIP_EVENT}"] if dips else [])
    return [f"E-4 off row with {len(creep)} INFO_TOUCH_CREEP_*"] if creep else []


def judge_harness_row(row: dict, *, k2_on: bool, angles_by_point: dict | None, f_d8: float) -> dict:
    """J1 .. J11 (``d8x_judge.judge_metrics``) and the K-2 identity items of one harness row; the K1 arm is the
    row's own ``k1_order_gate``."""
    if "error" in row:
        return {
            "id": row.get("id"),
            "k1_on": None,
            "k2_on": k2_on,
            "verdict": "not_judgeable",
            "not_judgeable": [f"run error {row['error']}"],
            "fail_items": [],
            "values": {},
        }
    k1_on = bool(row.get("k1_order_gate"))
    judged = d8x_judge.judge_metrics(row.get("d8x") or {}, row.get("fails"), f_d8)
    problems = list(judged["not_judgeable"])
    want_tag = expected_tag(k1_on, k2_on)
    if row.get("controller_tag") != want_tag:
        problems.append(f"E-6 tag {row.get('controller_tag')} != {want_tag}")
    if row.get("touch_creep_latch") is not k2_on:
        problems.append(f"E-6 touch_creep_latch {row.get('touch_creep_latch')!r} != {k2_on}")
    if angles_by_point is not None:
        angles = angles_by_point.get(row.get("point"))
        if angles is None or not d8x_judge._angles_match(
            row.get("angles_deg"), angles, d8x_judge.ANGLE_TOLERANCE_HARNESS_DEG
        ):
            problems.append(f"E-7 angles {row.get('angles_deg')} != point {row.get('point')}")
    if not isinstance((row.get("d8x") or {}).get("J3_pad_lift_samples"), int) or not row.get(
        "series_file"
    ):
        problems.append("E-8 no 1 ms pad series (series_file)")
    problems += k2_evidence_problems(_event_names(row), k2_on)
    k2 = row.get("k2") or {}
    return {
        "id": row["id"],
        "k1_on": k1_on,
        "k2_on": k2_on,
        "verdict": "not_judgeable" if problems else ("fail" if judged["fail_items"] else "pass"),
        "fail_items": judged["fail_items"],
        "not_judgeable": problems,
        "values": judged["values"],
        "t_ready_s": (row.get("d8x") or {}).get("t_ready_s"),
        "has_h4": bool((row.get("d8x") or {}).get("reanchor_intervals_s")),
        "commands_sha256": row.get("commands_sha256"),
        "sh1": k2.get("SH1_lift_chunks_after_latch"),
        "sh2": k2.get("SH2_rate_amp_deg_s"),
        "cap": (k2.get("event_counts") or {}).get(CAP_EVENT),
        "J3_margin_N": (row.get("d8x") or {}).get("J3_pad_normal_min_N"),
        "dhat_N": k2.get("dhat_N"),
        "dhat_window_open_legs": k2.get("dhat_window_open_legs"),
        "dhat_window_stroke_mm": k2.get("dhat_window_stroke_mm"),
    }


def judge_files(
    files: list[str], *, k2_on: bool, angles_by_point: dict | None, f_d8: float
) -> list[dict]:
    rows = []
    for path in files:
        for run in _runs_of(Path(path)):
            rows.append(
                judge_harness_row(run, k2_on=k2_on, angles_by_point=angles_by_point, f_d8=f_d8)
            )
    return rows


def summarise(rows: list[dict], expected: int | None, label: str) -> dict:
    counts = {"pass": 0, "fail": 0, "not_judgeable": 0}
    for row in rows:
        counts[row["verdict"]] += 1
    return {"bundle": label, "expected": expected, "actual": len(rows), **counts}


def count_problems(rows: list[dict], expected_by_k1: dict, label: str) -> list[str]:
    """E-1 per K1 arm, E-6 tag histogram, duplicate keys."""
    problems = []
    for k1_on, expected in expected_by_k1.items():
        actual = sum(1 for row in rows if row["k1_on"] is k1_on)
        if actual != expected:
            problems.append(
                f"E-1 {label} K1 {'on' if k1_on else 'off'}: {actual} rows, expected {expected}"
            )
    keys = [(row["id"], row["k1_on"]) for row in rows]
    if len(set(keys)) != len(keys):
        problems.append(f"E-1 {label}: duplicate keys")
    return problems


def _row_j(row: dict, item: str):
    return (row.get("values") or {}).get(item)


def _sh_row_flags(k2_rows: list[dict], f_d8: float, label: str, missing: dict) -> list[dict]:
    """SH-1, SH-5, SH-6 per K-2 row; a missing value is counted (E-9), J2 only on rows with an H4 interval."""
    flags = []
    for row in k2_rows:
        sh1 = row.get("sh1")
        if not isinstance(sh1, list) or len(sh1) != len(LEG_NAMES) or any(c is None for c in sh1):
            missing["SH-1"] += 1
        if any((count or 0) > 0 for count in sh1 or []):
            flags.append({"flag": "SH-1", "bundle": label, "id": row["id"], "value": sh1})
        if row.get("cap") is None:
            missing["SH-5"] += 1
        elif row["cap"] > 0:
            flags.append({"flag": "SH-5", "bundle": label, "id": row["id"], "value": row["cap"]})
        items = ("J1_N", "J2_N") if row.get("has_h4") else ("J1_N",)
        for item in items:
            value = _row_j(row, item)
            if not d8x_judge._is_number(value):
                missing["SH-6"] += 1
            elif value < f_d8 + SH6_MARGIN_N:
                flags.append({"flag": "SH-6", "bundle": label, "id": row["id"], item: value})
    return flags


def _sh_missing_flags(missing: dict, label: str) -> list[dict]:
    """E-9 (rev2 1 / 3): a missing indicator value is a FLAG, with its count."""
    return [{"flag": name, "bundle": label, "missing": count} for name, count in missing.items() if count]


def sh_flags(k2_rows: list[dict], off_rows: list[dict], f_d8: float, label: str) -> dict:
    """SH-1 .. SH-6 of one bundle (rules 5.2; E-11 pairs by (id, K1 arm)); missing values are counted and
    flagged (E-9), never skipped."""
    off_by_key = {(row["id"], row["k1_on"]): row for row in off_rows}
    k2_by_key = {(row["id"], row["k1_on"]): row for row in k2_rows}
    unpaired = sorted(str(key) for key in set(off_by_key) ^ set(k2_by_key))
    missing = dict.fromkeys(("SH-1", "SH-2", "SH-3", "SH-4", "SH-5", "SH-6"), 0)
    flags = _sh_row_flags(k2_rows, f_d8, label, missing)
    if unpaired:
        return {
            "bundle": label,
            "not_judgeable": f"E-11 {len(unpaired)} unpaired keys",
            "unpaired": unpaired[:20],
            "flags": flags + _sh_missing_flags(missing, label),
            "missing": missing,
        }
    missing["SH-2"] = sum(not d8x_judge._is_number(row.get("sh2")) for row in k2_rows + off_rows)
    k2_median = _median(row.get("sh2") for row in k2_rows)
    off_median = _median(row.get("sh2") for row in off_rows)
    if k2_median is not None and off_median is not None and k2_median > off_median:
        flags.append(
            {"flag": "SH-2", "bundle": label, "k2_median": k2_median, "off_median": off_median}
        )
    delays = []
    for key, row in k2_by_key.items():
        a, b = row.get("t_ready_s"), off_by_key[key].get("t_ready_s")
        if not (d8x_judge._is_number(a) and d8x_judge._is_number(b)):
            missing["SH-3"] += 1
            continue
        delays.append((a - b, key[0]))
        if a - b > SH3_READY_DELAY_S:
            flags.append({"flag": "SH-3", "bundle": label, "id": key[0], "delay_s": a - b})
    j1_k2 = [_row_j(r, "J1_N") for r in k2_rows]
    j1_off = [_row_j(r, "J1_N") for r in off_rows]
    missing["SH-4"] = sum(not d8x_judge._is_number(v) for v in j1_k2 + j1_off)
    numbers_k2 = [v for v in j1_k2 if d8x_judge._is_number(v)]
    numbers_off = [v for v in j1_off if d8x_judge._is_number(v)]
    erosion = (min(numbers_k2) - min(numbers_off)) if numbers_k2 and numbers_off else None
    if erosion is not None and erosion < SH4_J1_EROSION_N:
        flags.append({"flag": "SH-4", "bundle": label, "min_J1_difference_N": erosion})
    return {
        "bundle": label,
        "flags": flags + _sh_missing_flags(missing, label),
        "missing": missing,
        "sh2_medians": [k2_median, off_median],
        "sh4_min_J1_difference_N": erosion,
        "ready_delay_s_top5": sorted(delays)[-5:],
    }


def invariance_i4(off_rows: list[dict], stored_paths: list[str]) -> dict:
    """I-4: off-arm commands_sha256 == the stored D8x rows, row by row (keys (id, K1 arm))."""
    stored = {}
    for path in stored_paths:
        for run in _runs_of(Path(path)):
            stored[(run["id"], bool(run.get("k1_order_gate")))] = run.get("commands_sha256")
    differing = [
        row["id"]
        for row in off_rows
        if stored.get((row["id"], row["k1_on"])) != row.get("commands_sha256")
    ]
    return {
        "n": len(off_rows),
        "stored": len(stored),
        "differing": differing[:40],
        "n_differing": len(differing),
        "ok": not differing and len(off_rows) == len(stored),
    }


def _points_of(path) -> dict | None:
    if not path:
        return None
    doc = d8x_judge._load_json(Path(path))
    return {p["tag"]: (float(p["roll_deg"]), float(p["pitch_deg"])) for p in doc["ra_points"]}


def _manifest_part(args, bundle: str) -> dict:
    manifest = d8x_judge._load_json(Path(args.manifest))
    if bundle not in manifest:
        raise NotJudgeable(f"manifest has no {bundle}")
    return manifest[bundle]


def _gate_value(status: int, k2_summaries: list[dict]) -> str:
    if status == EXIT_NOT_JUDGEABLE:
        return "not_judgeable"
    return "fail" if any(summary["fail"] for summary in k2_summaries) else "pass"


def _status(problems: list[str], summaries: list[dict]) -> int:
    if problems or any(s["not_judgeable"] for s in summaries):
        return EXIT_NOT_JUDGEABLE
    return EXIT_FAIL if any(s["fail"] for s in summaries) else EXIT_PASS


def _failed(rows_by_label: dict) -> list[dict]:
    return [
        {
            "bundle": label,
            "id": row["id"],
            "k1_on": row["k1_on"],
            "fail_items": row["fail_items"],
            "not_judgeable": row["not_judgeable"],
        }
        for label, rows in rows_by_label.items()
        for row in rows
        if row["verdict"] != "pass"
    ][:300]


def _off_tcl_bundle(
    part: dict, *, label: str, expected_by_k1: dict, angles: dict | None, f_d8: float
) -> tuple[dict, list[dict], list[dict], list[str]]:
    off = judge_files(part["off"], k2_on=False, angles_by_point=angles, f_d8=f_d8)
    tcl = judge_files(part["tcl"], k2_on=True, angles_by_point=angles, f_d8=f_d8)
    problems = count_problems(off, expected_by_k1, f"{label}.off") + count_problems(
        tcl, expected_by_k1, f"{label}.tcl"
    )
    sh = [
        sh_flags(
            [r for r in tcl if r["k1_on"] is k1],
            [r for r in off if r["k1_on"] is k1],
            f_d8,
            f"{label} K1 {'on' if k1 else 'off'}",
        )
        for k1 in expected_by_k1
    ]
    problems += [block["not_judgeable"] for block in sh if block.get("not_judgeable")]
    summaries = {
        "off": summarise(off, sum(expected_by_k1.values()), f"{label}.off"),
        "tcl": summarise(tcl, sum(expected_by_k1.values()), f"{label}.tcl"),
    }
    dhat = dhat_record(
        {(r["id"], r["k1_on"]): r.get("dhat_N") for r in tcl},
        {(r["id"], r["k1_on"]): r.get("dhat_N") for r in off},
        label,
    )
    return {"summaries": summaries, "sh": sh, "dhat": dhat}, off, tcl, problems


DHAT_QUANTILES_PERCENT = (0, 5, 50, 95, 100)
DHAT_LIST_ABOVE_N = 5.0e3
"""Rules rev1 4 (b): rows with |D_hat(K-2) - D_hat(off)| >= 5 kN are listed."""


def dhat_record(k2_by_key: dict, off_by_key: dict, label: str) -> dict:
    """Rules rev1 4 (b), record only: quantiles 0 / 5 / 50 / 95 / 100 % of D_hat(K-2) - D_hat(off) of
    the pairs with both values [kN] (``numpy.percentile``, linear), the pairs with |difference| >= 5 kN,
    and the keys without a pair or a value."""
    import numpy as np

    differences, large, missing = [], [], []
    for key in sorted(set(k2_by_key) | set(off_by_key), key=str):
        a, b = k2_by_key.get(key), off_by_key.get(key)
        if not (d8x_judge._is_number(a) and d8x_judge._is_number(b)):
            missing.append(str(key))
            continue
        difference = a - b
        differences.append(difference)
        if abs(difference) >= DHAT_LIST_ABOVE_N:
            large.append({"key": list(key) if isinstance(key, tuple) else key,
                          "dhat_k2_kN": a / 1e3, "dhat_off_kN": b / 1e3,
                          "difference_kN": difference / 1e3})
    quantiles = None
    if differences:
        values = np.percentile(np.asarray(differences, float) / 1e3, DHAT_QUANTILES_PERCENT)
        quantiles = {f"p{p}": float(v) for p, v in zip(DHAT_QUANTILES_PERCENT, values, strict=True)}
    return {"bundle": label, "pairs": len(differences), "quantiles_kN": quantiles,
            "abs_ge_5kN": large, "missing": missing[:50], "n_missing": len(missing)}


def cmd_judge_v2(args) -> tuple[int, dict]:
    problems = seal_problems()
    part = _manifest_part(args, "v2")
    f_d8 = f_d8_N()
    result, off, tcl, more = _off_tcl_bundle(
        part,
        label="V-2",
        f_d8=f_d8,
        expected_by_k1={False: EXPECTED_ROWS["v2"]["off"], True: EXPECTED_ROWS["v2"]["on"]},
        angles=_points_of(part.get("points")),
    )
    problems += more + options_off_problems(part["off"] + part["tcl"], "V-2")
    stored = part.get("stored_off") or []
    i4 = invariance_i4(off, stored) if stored else {"ok": None}
    if i4["ok"] is not True:
        problems.append(
            "I-4 off rows vs stored D8x: "
            + ("stored_off not given" if i4["ok"] is None else f"{i4['n_differing']} differ")
        )
    status = _status(problems, list(result["summaries"].values()))
    return status, {
        "bundle": "V-2",
        "gate": {"G-A": _gate_value(status, [result["summaries"]["tcl"]])},
        **result,
        "I-4": i4,
        "problems": problems,
        "failed_rows": _failed({"off": off, "tcl": tcl}),
        "field_map": FIELD_MAP_K2,
    }


def cmd_judge_v4(args) -> tuple[int, dict]:
    problems = seal_problems()
    part = _manifest_part(args, "v4")
    points_path = part.get("points") or str(POINTS_PATH)
    status_points, check = cmd_points(argparse.Namespace(points_file=points_path, check=True))
    if status_points != EXIT_PASS:
        problems += check["problems"]
    result, off, tcl, more = _off_tcl_bundle(
        part,
        label="V-4",
        f_d8=f_d8_N(),
        expected_by_k1={False: EXPECTED_ROWS["v4"]},
        angles=_points_of(points_path),
    )
    problems += more + options_off_problems(part["off"] + part["tcl"], "V-4")
    levels = {
        row["id"].split("|")[2] for row in off + tcl if row.get("id") and row["id"].count("|") >= 2
    }
    if levels - {"top"}:
        problems.append(f"V-4 levels {sorted(levels)} (top only)")
    status = _status(problems, list(result["summaries"].values()))
    return status, {
        "bundle": "V-4",
        "gate": {"G-C": _gate_value(status, [result["summaries"]["tcl"]])},
        **result,
        "problems": problems,
        "failed_rows": _failed({"off": off, "tcl": tcl}),
        "field_map": FIELD_MAP_K2,
    }


def options_off_problems(files: list[str], label: str) -> list[str]:
    """Rev2 4 V-2 / V-4: no dissipation option on any row (``aug_arm`` and ``k2.aug`` absent or None)."""
    problems = []
    for path in files:
        for run in _runs_of(Path(path)):
            if run.get("aug_arm") is not None or (run.get("k2") or {}).get("aug") is not None:
                problems.append(f"E-5 {label} {run.get('id')}: options on (aug_arm {run.get('aug_arm')!r})")
                if len(problems) > 20:
                    return problems
    return problems


# --- rev2 4 / rev3 1: V-3 arm values ------------------------------------------------------------------------
AUG_OPTION_KEYS_BY_ARM = {
    "H0": frozenset(),
    "L1eq": frozenset({"crawler_kt_rel"}),
    "L1eq_fs": frozenset({"crawler_kt_rel", "seal_fs_front_N"}),
    "L1eq_zm": frozenset({"crawler_kt_rel", "pad_zeta_moving"}),
    "AUG": frozenset({"crawler_kt_rel", "seal_fs_front_N", "pad_zeta_moving"}),
    "AUG_crc2": frozenset({"crawler_kt_rel", "seal_fs_front_N", "pad_zeta_moving", "crawler_c_scale"}),
    "AUG_eps": frozenset({"crawler_kt_rel", "seal_fs_front_N", "pad_zeta_moving", "valve_open_eps_m_s"}),
}
"""Rev3 1: ``k2.aug.plant_aug.options`` key set of each arm (equal sets; H0 ``options == {}``)."""
AUG_RESOLVED_VALUES = {
    "crawler_kt_rel": 0.23309250561413625,
    "seal_fs_front_N": 4000.0,
    "seal_fs_rear_scale": 0.8333,
    "pad_zeta_moving": 0.10,
    "crawler_c_scale": 2.0,
}
"""Rev3 1: ``resolved`` reference values (the run YAML computed values; rev2 4 printed them rounded)."""
VALVE_OPEN_EPS_AUG_EPS_M_S = 0.00209243016
VALVE_OPEN_EPS_LOCK_M_S = 1e-6
"""Rev3 1: ``resolved.valve_open_eps_m_s`` (every arm): 0.1 v_max for AUG_eps, the YAML lock eps otherwise."""
AUG_RELATIVE_TOLERANCE = 1e-9
AUG_ZERO_TOLERANCE = 1e-12
"""Rev3 1: relative difference <= 1e-9; for a zero reference the absolute difference <= 1e-12."""
PAD_ZETA_MOVING = 0.10
PAD_ZETA_LOCKED = 0.03


def _close(value, expected: float) -> bool:
    if not d8x_judge._is_number(value):
        return False
    if expected == 0.0:
        return abs(value) <= AUG_ZERO_TOLERANCE
    return abs(value - expected) <= AUG_RELATIVE_TOLERANCE * abs(expected)


def _resolved_problems(arm: str, options: dict, resolved: dict) -> list[str]:
    """Rev3 1: the ``resolved`` value of every quantity in ``options`` (and the valve-open threshold of every arm)."""
    problems = []
    names = set(options)
    if "seal_fs_front_N" in names:
        names.add("seal_fs_rear_scale")
    names.discard("valve_open_eps_m_s")
    for name in sorted(names):
        if not _close(resolved.get(name), AUG_RESOLVED_VALUES[name]):
            problems.append(f"resolved {name} {resolved.get(name)!r} != {AUG_RESOLVED_VALUES[name]}")
    if "pad_zeta_moving" in options and not _cn_moving_ok(resolved):
        problems.append("resolved cn_moving_N_s_m != cn_lock_N_s_m x 0.10 / 0.03")
    eps = VALVE_OPEN_EPS_AUG_EPS_M_S if arm == "AUG_eps" else VALVE_OPEN_EPS_LOCK_M_S
    if not _close(resolved.get("valve_open_eps_m_s"), eps):
        problems.append(f"resolved valve_open_eps_m_s {resolved.get('valve_open_eps_m_s')!r} != {eps}")
    return problems


def aug_value_problems(arm: str, plant_aug: dict | None) -> list[str]:
    """Rev3 1 E-5 of one V-3 row: ``k2.aug.plant_aug`` preset, option key set and resolved values."""
    plant_aug = plant_aug or {}
    options, resolved = plant_aug.get("options"), plant_aug.get("resolved")
    if not isinstance(options, dict) or not isinstance(resolved, dict):
        return ["plant_aug options / resolved missing"]
    problems = []
    if plant_aug.get("preset") != V3_DISS_PRESETS[arm]:
        problems.append(f"plant_aug preset {plant_aug.get('preset')!r} != {V3_DISS_PRESETS[arm]}")
    if set(options) != AUG_OPTION_KEYS_BY_ARM[arm]:
        problems.append(f"options keys {sorted(options)} != {sorted(AUG_OPTION_KEYS_BY_ARM[arm])}")
        return problems
    return problems + _resolved_problems(arm, options, resolved)


def _cn_moving_ok(resolved: dict) -> bool:
    lock, moving = resolved.get("cn_lock_N_s_m"), resolved.get("cn_moving_N_s_m")
    if not isinstance(lock, list) or not isinstance(moving, list) or len(lock) != len(moving) or not lock:
        return False
    return all(_close(b, a * PAD_ZETA_MOVING / PAD_ZETA_LOCKED) for a, b in zip(lock, moving, strict=True))


def open_share_problem(shares) -> str | None:
    """Rev2 4 I-9: four per-leg valve-open shares, each finite in [0, 1] (a dict by leg or a list)."""
    values = list(shares.values()) if isinstance(shares, dict) else shares
    if not isinstance(values, list) or len(values) != len(LEG_NAMES):
        return f"valve-open shares {shares!r}"
    if not all(d8x_judge._is_number(v) and math.isfinite(v) and 0.0 <= v <= 1.0 for v in values):
        return f"valve-open shares {values!r} not finite in [0, 1]"
    return None


def _aug_problems(files: list[str], arm: str) -> list[str]:
    """E-5 / I-9 of the V-3 rows of one arm (top-level ``aug_arm`` / ``is_kplant``, the ``k2.aug`` block with the
    rev3 1 values, the open shares)."""
    problems = []
    for path in files:
        for run in _runs_of(Path(path)):
            problems += _aug_row_problems(run, arm)
            if len(problems) > 20:
                return problems
    return problems


def _aug_row_problems(run: dict, arm: str) -> list[str]:
    aug = (run.get("k2") or {}).get("aug") or {}
    run_id = run.get("id")
    if run.get("aug_arm") != arm or run.get("is_kplant") is not True:
        return [f"E-5 {run_id}: aug_arm {run.get('aug_arm')} / is_kplant {run.get('is_kplant')}"]
    if aug.get("arm") != arm or aug.get("is_kplant") is not True:
        return [f"E-5 {run_id}: k2.aug.arm {aug.get('arm')!r} / is_kplant {aug.get('is_kplant')!r}"]
    if aug.get("preset") != V3_DISS_PRESETS[arm] or aug.get("case_id") != run_id:
        return [f"I-9 {run_id}: preset {aug.get('preset')!r} / case_id {aug.get('case_id')!r}"]
    problems = [f"E-5 {run_id}: {p}" for p in aug_value_problems(arm, aug.get("plant_aug"))]
    share = open_share_problem(aug.get("valve_open_fraction_touch_to_lift"))
    if share:
        problems.append(f"I-9 {run_id}: {share}")
    return problems


def cmd_judge_v3(args) -> tuple[int, dict]:
    problems = seal_problems()
    part = _manifest_part(args, "v3")
    f_d8 = f_d8_N()
    angles = _points_of(part.get("points"))
    arms, rows_by_label, judged_summaries = {}, {}, []
    for arm in V3_ARMS:
        if arm not in part.get("arms", {}):
            problems.append(f"E-1 V-3 arm {arm} missing")
            continue
        cell = part["arms"][arm]
        result, off, tcl, more = _off_tcl_bundle(
            cell,
            label=f"V-3 {arm}",
            f_d8=f_d8,
            expected_by_k1={False: V3_EXPECTED_KEYS},
            angles=angles,
        )
        for side, rows in (("off", off), ("tcl", tcl)):
            if keys_sha256({row["id"] for row in rows}) != V3_KEYS_SHA256:
                problems.append(f"E-5 V-3 {arm}.{side}: key list sha differs")
            problems += _aug_problems(cell[side], arm)
        if arm in V3_JUDGED_ARMS:
            problems += more
            judged_summaries.append(result["summaries"]["tcl"])
        result["off_J3_rows"] = sum(1 for row in off if "J3" in row["fail_items"])
        arms[arm] = result
        rows_by_label[f"{arm}.off"], rows_by_label[f"{arm}.tcl"] = off, tcl
    status = _status(problems, judged_summaries)
    b3 = all(
        arms.get(arm, {}).get("off_J3_rows") == 0 for arm in ("L1eq", "L1eq_fs", "L1eq_zm", "AUG")
    )
    return status, {
        "bundle": "V-3",
        "gate": {"G-B": _gate_value(status, judged_summaries)},
        "arms": arms,
        "sh": [
            block
            for result in (arms.get(a) for a in V3_JUDGED_ARMS)
            if result
            for block in result["sh"]
        ],
        "dhat": [arms[a]["dhat"] for a in V3_JUDGED_ARMS if a in arms],
        "B-3": b3,
        "problems": problems,
        "failed_rows": _failed(rows_by_label),
        "field_map": FIELD_MAP_K2,
    }


# ------------------------------------------------------------------------------------ V-5
def _dotted(row: dict, dotted: str):
    value = row
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            raise NotJudgeable(f"V-5 key {dotted!r} missing")
        value = value[part]
    return value


def _passed(row: dict, dotted: str) -> bool:
    value = _dotted(row, dotted)
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in ("pass", "fail", "ok", "stroke_limited_pass"):
        return value.lower() in ("pass", "ok", "stroke_limited_pass")
    raise NotJudgeable(f"V-5 status {value!r}")


def cp_upper_95(failures: int, n: int) -> float:
    """One-sided Clopper-Pearson 95 % upper bound of a failure rate (beta quantile)."""
    from scipy.stats import beta

    return 1.0 if failures >= n else float(beta.ppf(0.95, failures + 1, n - failures))


def _binomial_cdf(k: int, n: int, p: float) -> float:
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 0.0 if k < n else 1.0
    log_p, log_q = math.log(p), math.log1p(-p)
    return sum(
        math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * log_p + (n - i) * log_q)
        for i in range(k + 1)
    )


def cp_upper_95_bisection(failures: int, n: int) -> float:
    """The same bound by bisection on the binomial sum ``P(X <= k; n, p) = 0.05`` (rev2 1: two paths)."""
    if failures >= n:
        return 1.0
    low, high = 0.0, 1.0
    for _ in range(200):
        middle = 0.5 * (low + high)
        if _binomial_cdf(failures, n, middle) > 0.05:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


# --- rev2 1: absolute items of criteria.md on the K-2 arm, K-2 evidence from the provenance -------------
C2_SHA256_RUN = "f58ee42b0f10ea42ceac5768e6ed373a38ee5e14440d9fc831536700b45ba6b1"
"""Rev2 1 common item: provenance ``c2_sha256`` = the k2-run working copy of ``c2.py`` (blob ``18c71876``)."""
V5_EXPECTED_ROWS = {"soil": 60, "d8": 576, "noise_L2": 855, "regression": 93, "ps7": 20, "g8_safe_stop": 83}
"""Rev2 1 row counts of the K-2 arm (grid: none in the table; E-1 takes the manifest count)."""
REGRESSION_JUDGED_SHA256 = "2900db889efc73070c3a8fbe557b1a4ad9ee3392afc099ba00be1d0549174ec9"
REGRESSION_RECORD_SHA256 = "d4f58334c6ca7c393c35072a798c09f4995d7fde274e0af6b21b99f977d503eb"
"""Rev2 2: sha256 of the judged (93) and record (49) key lists (``prelaunch/regression_keys.py keys``)."""
V5_RELATIVE_GATES = {"grid": True, "soil": True, "regression": True, "ps7": True, "g8_safe_stop": True,
                     "d8": False, "noise_L2": False}
"""Rev2 1 "off arm" column: pass -> fail against the off arm gates the bundle, or is only recorded (D8: READY
mean and worst minimum force differences; noise: the pass -> fail list)."""
SOIL_ABSOLUTE_MARKERS = ("|G1|", "|J2|")
"""Rev2 1 soil: these rows must pass on the K-2 arm; the other (rigid) rows are compared with the off arm."""
ARM_K2 = {"off": "off", "tcl": "on"}
"""``ACC_K2`` / provenance ``k2`` of an arm."""
V5_COMBO = {"g8_safe_stop": "off"}
"""Rev2 1 evidence: ``combo`` of the G8 steps; every other bundle runs the preset."""
V5_PRESET_COMBO = "preset"
ROW_EVIDENCE_BUNDLES = ("g8_safe_stop",)
"""Rev5 2: bundles whose K-2 evidence is the rows' ``touch_creep_latch`` / ``controller_tag`` (a row without them
is missing, E-9); other rows carrying them are checked too. G8 events are not evidence (its steps have no events
part)."""
GUARD_KN_V5 = 14.41
D8_ATTITUDE_LIMIT_DEG_V5 = 0.2
D8_READY_LIMIT_S_V5 = 100.0
"""Rev2 1 D8 row limits (criteria.md: F_min + 5 kN, 0.2 deg, READY <= 100 s)."""


def _flat_docs(paths: list[str]) -> list[dict]:
    docs = []
    for path in paths:
        doc = d8x_judge._load_json(Path(path))
        if not isinstance(doc, dict) or "runs" not in doc:
            raise NotJudgeable(f"V-5 {path}: not a flattener output")
        docs.append(doc)
    return docs


def _flat_bundle(docs: list[dict]) -> str | None:
    """The bundle named in the flattener meta of all docs (None when a doc has no meta or they differ)."""
    names = {(doc.get("meta") or {}).get("bundle") for doc in docs}
    return names.pop() if len(names) == 1 and None not in names else None


class _Items:
    """Absolute items of one arm: violations and missing values (E-9: a missing value is a failure)."""

    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def add(self, name: str, ok: bool | None, detail=None) -> None:
        item = self.items.setdefault(name, {"ok": True, "violations": 0, "missing": 0, "detail": []})
        if ok is None:
            item["missing"] += 1
        elif not ok:
            item["violations"] += 1
        item["ok"] = item["violations"] == 0 and item["missing"] == 0
        if detail is not None and not ok and len(item["detail"]) < 20:
            item["detail"].append(detail)

    def require(self, name: str) -> None:
        """An item that must appear even when nothing was counted (an empty input is not a pass)."""
        self.items.setdefault(name, {"ok": True, "violations": 0, "missing": 0, "detail": []})

    def result(self) -> dict:
        return {"passed": all(item["ok"] for item in self.items.values()), "items": self.items,
                "missing": {name: item["missing"] for name, item in self.items.items() if item["missing"]}}


def _equal_or_missing(value, expected) -> bool | None:
    return None if value is None else value == expected


RUN_HEAD = "6a44ff81d25aea1fa162daf9b14c23b99beb9db0"
"""Rev2 7 / rev5 2: the commit every V-5 step runs at."""


def g8_c2_ok(sidecar: dict, checkout_c2: dict | None) -> bool | None:
    """Rev5 2: a G8 step used the run commit's ``c2.py`` when its sidecar has start and end HEAD = RUN_HEAD, both
    clean, rc 0, and the fixed checkout's working copy sha256 = :data:`C2_SHA256_RUN`; a missing value is None."""
    values = (sidecar.get("git_start_head"), sidecar.get("git_end_head"), sidecar.get("git_start_clean"),
              sidecar.get("git_end_clean"), sidecar.get("rc"), (checkout_c2 or {}).get("sha256"))
    if not sidecar.get("exists") or any(value is None for value in values):
        return None
    start, end, start_clean, end_clean, rc, c2_sha = values
    return (start == end == RUN_HEAD and start_clean is True and end_clean is True and rc == 0
            and c2_sha == C2_SHA256_RUN)


def _absolute_common(items: _Items, metas: list[dict]) -> None:
    """Rev2 1 common: step sidecar rc 0, no error rows, provenance c2_sha256."""
    items.require("rc")
    items.require("error_rows")
    items.require("c2_sha256")
    for meta in metas:
        for step in meta.get("steps") or []:
            sidecar = step.get("sidecar") or {}
            items.add("rc", _equal_or_missing(sidecar.get("rc"), 0), step["step"])
            provenance = step.get("provenance")
            if provenance is None:  # judge steps: no c2 item; G8: rev5 2 (sidecar HEAD + clean + checkout c2)
                if not str(step["step"]).endswith("_judgement"):
                    items.add("c2_sha256", g8_c2_ok(sidecar, meta.get("checkout_c2")), step["step"])
                continue
            items.add("c2_sha256", _equal_or_missing(provenance.get("c2_sha256"), C2_SHA256_RUN), step["step"])
        for part, source in (meta.get("sources") or {}).items():
            count = source.get("error_rows")
            items.add("error_rows", None if count is None else count == 0, f"{part}: {count}")


def _absolute_rows(items: _Items, bundle: str, rows: list[dict]) -> None:
    expected = V5_EXPECTED_ROWS.get(bundle)
    if expected is not None:
        items.add("rows", len(rows) == expected, f"{len(rows)} != {expected}")
    if bundle in ("grid", "soil"):
        items.require("fault_periods")
        for row in rows:
            value = row.get("fault_periods")
            items.add("fault_periods", None if value is None else not value, row["key"])
    if bundle == "soil":
        items.require("soil_G1_J2_pass")
        for row in rows:
            if any(marker in row["key"] for marker in SOIL_ABSOLUTE_MARKERS):
                items.add("soil_G1_J2_pass", bool(row.get("pass")), row["key"])
    if bundle == "d8":
        _absolute_d8(items, rows)


def _absolute_d8(items: _Items, rows: list[dict]) -> None:
    """Rev2 1 D8 row conditions with the raw values (missing = failure)."""
    def at_most(value, limit):
        return None if not d8x_judge._is_number(value) else value <= limit

    for name in ("error", "fails", "fault", "min_force", "attitude", "ready"):
        items.require(f"d8_{name}")
    for row in rows:
        key = row["key"]
        items.add("d8_error", not row.get("error"), key)
        fails = row.get("fails")
        items.add("d8_fails", None if fails is None else not fails, key)
        items.add("d8_fault", None if row.get("fault") is None else not row["fault"], key)
        force = row.get("min_true_cyl_force_kN")
        items.add("d8_min_force", None if not d8x_judge._is_number(force) else force >= GUARD_KN_V5, key)
        items.add("d8_attitude", at_most(row.get("ss_true_att_deg_maxabs"), D8_ATTITUDE_LIMIT_DEG_V5), key)
        items.add("d8_ready", at_most(row.get("t_ready_s"), D8_READY_LIMIT_S_V5), key)


def _absolute_bundle_meta(items: _Items, bundle: str, metas: list[dict], rows: list[dict]) -> dict:
    """Noise and regression items from the flattener's bundle meta; returns the recorded values."""
    record: dict = {}
    if bundle == "noise_L2":
        failures = sum(not row.get("pass") for row in rows)
        upper = cp_upper_95(failures, len(rows)) if rows else None
        upper_b = cp_upper_95_bisection(failures, len(rows)) if rows else None
        record.update(failures=failures, n=len(rows), cp95_upper_beta=upper, cp95_upper_bisection=upper_b)
        items.add("noise_cp_beta", None if upper is None else upper <= NOISE_CP_LIMIT, upper)
        items.add("noise_cp_bisection", None if upper_b is None else upper_b <= NOISE_CP_LIMIT, upper_b)
    for meta in metas:
        judgement = meta.get("r79_judgement")
        if bundle in ("noise_L2", "regression"):
            judgement = judgement or {}
            items.add("r79_errors", _equal_or_missing(judgement.get("errors"), 0))
            record["r79_judgement"] = judgement
        if bundle == "noise_L2":  # rev4 1 (c): unmatched judged for the noise bundle only (a record for regression)
            items.add("r79_unmatched", _equal_or_missing(judgement.get("unmatched"), 0),
                      judgement.get("unmatched_keys"))
            items.add("reference_all_false_loc", _equal_or_missing(judgement.get("reference_all_false_loc"), 0))
            settings = meta.get("settings") or {}
            present = (settings.get("preset_settings") is True and bool(settings.get("preset_sgs_keys"))
                       and not settings.get("missing") and not settings.get("rows_without_sgs_keys"))
            items.add("sgs_settings", None if not present else settings.get("mismatch_sgs") == 0,
                      settings.get("differing_keys"))
            record["settings"] = settings
        if bundle == "regression":
            keys = meta.get("regression_keys") or {}
            items.add("regression_judged_keys", _equal_or_missing(keys.get("judged_sha256"),
                                                                  REGRESSION_JUDGED_SHA256), keys.get("judged_n"))
            items.add("regression_record_keys", _equal_or_missing(keys.get("record_sha256"),
                                                                  REGRESSION_RECORD_SHA256), keys.get("record_n"))
            record["regression_keys"] = keys
    return record


def v5_absolute(bundle: str, docs: list[dict]) -> dict:
    """Rev2 1 absolute items of one arm (judged on the K-2 arm, recorded on the off arm)."""
    metas = [doc.get("meta") or {} for doc in docs]
    rows = [row for doc in docs for row in doc["runs"]]
    items = _Items()
    _absolute_common(items, metas)
    _absolute_rows(items, bundle, rows)
    record = _absolute_bundle_meta(items, bundle, metas, rows)
    return {**items.result(), "record": record}


def _tag_has_tcl(tag) -> bool | None:
    return None if not isinstance(tag, str) else tag.endswith(v5_options.TOUCH_CREEP_TAG_SUFFIX)


def v5_evidence(bundle: str, arm: str, docs: list[dict]) -> list[str]:
    """Rev2 1 K-2 evidence of one arm (every provenance record, the G8 sidecar env, row tags and event rows);
    any problem makes the bundle not judgeable."""
    k2_on = arm == "tcl"
    combo = V5_COMBO.get(bundle, V5_PRESET_COMBO)
    problems = []
    for meta in (doc.get("meta") or {} for doc in docs):
        for step in meta.get("steps") or []:
            problems += _step_evidence(step, bundle, arm, combo)
    rows_must_carry = bundle in ROW_EVIDENCE_BUNDLES
    for row in (row for doc in docs for row in doc["runs"]):
        carries = "touch_creep_latch" in row or "controller_tag" in row
        if not carries and not rows_must_carry:
            continue  # bundles whose rows carry no switch record (their evidence is the provenance)
        if row.get("touch_creep_latch") is not k2_on or _tag_has_tcl(row.get("controller_tag")) is not k2_on:
            problems.append(f"{arm} row {row['key']}: touch_creep_latch {row.get('touch_creep_latch')!r} / "
                            f"tag {row.get('controller_tag')!r}")
            if len(problems) > 40:
                break
    return problems


def _step_evidence(step: dict, bundle: str, arm: str, combo: str) -> list[str]:
    k2_on = arm == "tcl"
    name = f"{arm} {step['step']}"
    problems = []
    provenance = step.get("provenance")
    if bundle == "g8_safe_stop":
        sidecar = step.get("sidecar") or {}
        if sidecar.get("ACC_COMBO") != combo or sidecar.get("ACC_K2") != ARM_K2[arm]:
            problems.append(f"{name}: sidecar ACC_COMBO {sidecar.get('ACC_COMBO')!r} / ACC_K2 "
                            f"{sidecar.get('ACC_K2')!r} != {combo} / {ARM_K2[arm]}")
    elif provenance is not None:
        if not provenance.get("exists"):
            problems.append(f"{name}: no provenance {provenance.get('source')}")
        else:
            if provenance.get("combo") != combo:
                problems.append(f"{name}: combo {provenance.get('combo')!r} != {combo}")
            if provenance.get("k2") != ARM_K2[arm]:
                problems.append(f"{name}: k2 {provenance.get('k2')!r} != {ARM_K2[arm]}")
            if provenance.get("touch_creep_latch") is not k2_on:
                problems.append(f"{name}: touch_creep_latch {provenance.get('touch_creep_latch')!r}")
            if _tag_has_tcl(provenance.get("controller_tag")) is not k2_on:
                problems.append(f"{name}: controller_tag {provenance.get('controller_tag')!r}")
    events = step.get("events")
    if events is not None:
        if k2_on and not events.get("latch_rows"):
            problems.append(f"{name}: no row with {LATCH_EVENT} in {events.get('source')}")
        if not k2_on and events.get("creep_rows"):
            problems.append(f"{name}: {events['creep_rows']} rows with INFO_TOUCH_CREEP_* in {events.get('source')}")
    return problems


def _relative_keys(bundle: str, keys: list[str]) -> list[str]:
    if bundle == "soil":
        return [key for key in keys if not any(marker in key for marker in SOIL_ABSOLUTE_MARKERS)]
    return keys


def _g8_failures(spec: dict, common: list[str], off_by_key: dict, tcl_by_key: dict) -> list:
    failures = []
    for key in common:
        a, b = off_by_key[key], tcl_by_key[key]
        if bool(_dotted(a, spec["ready"])) and not bool(_dotted(b, spec["ready"])):
            failures.append([key, "ready lost"])
        old = {str(n).split(":")[0] for n in _dotted(a, spec["faults"]) or [] if str(n).startswith("FAULT_")}
        new = {str(n).split(":")[0] for n in _dotted(b, spec["faults"]) or [] if str(n).startswith("FAULT_")}
        if new - old:
            failures.append([key, f"new FAULT {sorted(new - old)}"])
        if spec.get("status") and _passed(a, spec["status"]) and not _passed(b, spec["status"]):
            failures.append([key, "status pass->fail"])
    return failures


def _d8_record(common: list[str], off_by_key: dict, tcl_by_key: dict) -> dict:
    """Rev2 1 D8 off-arm column (record): READY mean difference and the worst minimum-force difference."""
    ready, force = [], []
    for key in common:
        a, b = off_by_key[key], tcl_by_key[key]
        if d8x_judge._is_number(a.get("t_ready_s")) and d8x_judge._is_number(b.get("t_ready_s")):
            ready.append(b["t_ready_s"] - a["t_ready_s"])
        if d8x_judge._is_number(a.get("min_true_cyl_force_kN")) and d8x_judge._is_number(
            b.get("min_true_cyl_force_kN")
        ):
            force.append(b["min_true_cyl_force_kN"] - a["min_true_cyl_force_kN"])
    return {"ready_mean_delta_s": statistics.fmean(ready) if ready else None,
            "min_force_worst_delta_kN": min(force) if force else None,
            "pairs_ready": len(ready), "pairs_force": len(force)}


def _relative(spec: dict, bundle: str | None, off_by_key: dict, tcl_by_key: dict) -> dict:
    """Pass -> fail against the off arm (rev2 1 "off arm" column)."""
    common = _relative_keys(bundle or "", sorted(set(off_by_key) & set(tcl_by_key)))
    out: dict = {}
    if spec["kind"] == "g8":
        out["failures"] = _g8_failures(spec, common, off_by_key, tcl_by_key)
        out["relative_passed"] = not out["failures"]
        return out
    out["pass_to_fail"] = [
        k for k in common
        if _passed(off_by_key[k], spec["status"]) and not _passed(tcl_by_key[k], spec["status"])
    ]
    out["relative_passed"] = not out["pass_to_fail"]
    if bundle == "d8":
        out["record"] = _d8_record(common, off_by_key, tcl_by_key)
    return out


V5_KINDS = ("pass_to_fail", "noise_cp", "g8", "absolute")


def v5_bundle(spec: dict) -> dict:
    """One V-5 bundle of the manifest (rev2 1): the absolute items on the K-2 arm (recorded on the off arm), the
    K-2 evidence of both arms and pass -> fail against the off arm (gating per :data:`V5_RELATIVE_GATES`).

    ``kind``: ``pass_to_fail`` | ``noise_cp`` | ``g8`` (the comparison form) or ``absolute`` (absolute items
    only); ``off`` / ``tcl`` flattener files; ``key`` / ``status`` dotted paths; g8 ``ready`` / ``faults``.
    """
    if spec["kind"] not in V5_KINDS:
        raise NotJudgeable(f"V-5 kind {spec['kind']!r}")
    off_docs, tcl_docs = _flat_docs(spec["off"]), _flat_docs(spec["tcl"])
    off = [row for doc in off_docs for row in doc["runs"]]
    tcl = [row for doc in tcl_docs for row in doc["runs"]]
    bundle = _flat_bundle(off_docs + tcl_docs)
    off_by_key = {str(_dotted(row, spec["key"])): row for row in off}
    tcl_by_key = {str(_dotted(row, spec["key"])): row for row in tcl}
    result: dict = {"kind": spec["kind"], "bundle": bundle, "n_off": len(off), "n_tcl": len(tcl),
                    "unpaired": sorted(set(off_by_key) ^ set(tcl_by_key))}
    if len(off_by_key) != len(off) or len(tcl_by_key) != len(tcl):
        result.update(passed=False, not_judgeable="duplicate keys")
        return result
    if bundle is None:
        result.update(passed=False, not_judgeable="no k2_v5_flatten meta (rev2 1 absolute items)")
        return result
    relative_gates = V5_RELATIVE_GATES[bundle] and spec["kind"] != "absolute"
    if spec["kind"] != "absolute":
        result.update(_relative(spec, bundle, off_by_key, tcl_by_key))
    result["relative_gates"] = relative_gates
    result["absolute"] = {"tcl": v5_absolute(bundle, tcl_docs), "off_record": v5_absolute(bundle, off_docs)}
    result["evidence"] = {"off": v5_evidence(bundle, "off", off_docs), "tcl": v5_evidence(bundle, "tcl", tcl_docs)}
    result["missing"] = result["absolute"]["tcl"]["missing"]
    result["passed"] = result["absolute"]["tcl"]["passed"] and (
        not relative_gates or result.get("relative_passed", True)
    )
    evidence = result["evidence"]["off"] + result["evidence"]["tcl"]
    if evidence:
        result.update(passed=False, not_judgeable=f"K-2 evidence: {evidence[:5]}")
    if result["unpaired"] and spec["kind"] != "absolute":
        result.update(passed=False, not_judgeable=f"unpaired keys {len(result['unpaired'])}")
    return result


STORED_ACCEPTANCE_DIR = ROOT / "06_analysis" / "02_control" / "touch_phase" / "acceptance"
STORED_PS7 = ROOT / "06_analysis" / "02_control" / "touch_phase" / "ps7_E.json"
SELFTEST_KINDS = {"grid": "pass_to_fail", "soil": "pass_to_fail", "regression": "pass_to_fail",
                  "d8": "pass_to_fail", "noise_L2": "noise_cp", "ps7": "pass_to_fail", "g8_safe_stop": "g8"}
SELFTEST_ROWS = {"grid": 768, **V5_EXPECTED_ROWS}
SELFTEST_SKIPPED_ITEMS = ("rc", "c2_sha256")
"""Common items the stored acceptance outputs have no record for (sidecars, provenance): not checked here."""


def selftest_v5_stored(acceptance_dir: Path, ps7_path: Path, work_dir: Path) -> dict:
    """The V-5 reader on the stored final-controller acceptance outputs, the same files as both arms (as path 2
    ``selftest-v5-stored``, rev4 2): every bundle must give its row count, no pass -> fail and every absolute
    item except :data:`SELFTEST_SKIPPED_ITEMS` passed. K-2 evidence is not checked (no provenance there)."""
    import k2_v5_flatten

    g8 = acceptance_dir / "g8_safe_stop"
    overrides = {"ps7:ps7": ps7_path,
                 **{f"g8_safe_stop:g8_jobs{n}": g8 / f"out{n}.jsonl" for n in (1, 3, 5)}}
    k2_v5_flatten.flatten(acceptance_dir, work_dir, overrides, checkout=ROOT, bundles=list(SELFTEST_KINDS),
                          run_judge=False)
    bundles = {}
    for bundle, kind in SELFTEST_KINDS.items():
        path = str(work_dir / f"{bundle}.json")
        spec = {"kind": kind, "off": [path], "tcl": [path], "key": "key", "status": "pass"}
        if kind == "g8":
            spec.update(ready="ready", faults="faults")
        result = v5_bundle(spec)
        items = result["absolute"]["tcl"]["items"]
        failing = sorted(name for name, item in items.items()
                         if not item["ok"] and name not in SELFTEST_SKIPPED_ITEMS)
        bundles[bundle] = {"rows": result["n_tcl"], "expected_rows": SELFTEST_ROWS[bundle],
                           "relative_passed": result.get("relative_passed"), "failing_items": failing,
                           "ok": result["n_tcl"] == SELFTEST_ROWS[bundle] and not failing
                           and result.get("relative_passed") is True and not result["unpaired"]}
    return {"bundles": bundles, "ok": all(block["ok"] for block in bundles.values()),
            "skipped_items": list(SELFTEST_SKIPPED_ITEMS)}


def cmd_selftest_v5_stored(args) -> tuple[int, dict]:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="k2_selftest_v5_") as work:
        result = selftest_v5_stored(Path(args.acceptance), Path(args.ps7), Path(work))
    return (EXIT_PASS if result["ok"] else EXIT_FAIL), result


def cmd_judge_v5(args) -> tuple[int, dict]:
    problems = seal_problems()
    part = _manifest_part(args, "v5")
    bundles = {name: v5_bundle(spec) for name, spec in sorted(part.items())}
    for name, result in bundles.items():
        expected = (part[name] or {}).get("count")
        if expected is not None and (result["n_off"] != expected or result["n_tcl"] != expected):
            problems.append(f"E-1 V-5 {name}: {result['n_off']} / {result['n_tcl']} != {expected}")
        if result.get("not_judgeable"):
            problems.append(f"V-5 {name}: {result['not_judgeable']}")
    failed = [name for name, result in bundles.items() if not result["passed"]]
    status = EXIT_NOT_JUDGEABLE if problems else (EXIT_FAIL if failed else EXIT_PASS)
    gate = "not_judgeable" if problems else ("fail" if failed else "pass")
    return status, {
        "bundle": "V-5",
        "gate": {"G-D": gate},
        "bundles": bundles,
        "failed": failed,
        "missing": {name: result.get("missing", {}) for name, result in bundles.items()},
        "problems": problems,
        "field_map": {
            "V-5": "manifest v5.<bundle>: kind, off / tcl k2_v5_flatten files, key / status (/ ready, faults) "
            "dotted paths of the flat rows (rules 3.4, rev2 1)",
            "absolute (rev2 1)": "K-2 arm: meta.steps[].sidecar.rc == 0, meta.sources[].error_rows == 0, "
            "steps[].provenance.c2_sha256 == C2_SHA256_RUN; grid / soil rows fault_periods; soil |G1| / |J2| "
            "pass; d8 rows error / fails / fault / min_true_cyl_force_kN / ss_true_att_deg_maxabs / t_ready_s; "
            "noise CP (beta, bisection), meta.r79_judgement unmatched / errors / reference_all_false_loc, "
            "meta.settings.mismatch_sgs (lift_stroke_guard.* keys, rev4 1 (b)); regression "
            "meta.regression_keys sha256, meta.r79_judgement errors (unmatched recorded, rev4 1 (c)); error = "
            "a non-empty error value (rev4 1 (a)); row counts V5_EXPECTED_ROWS",
            "evidence (rev2 1)": "steps[].provenance combo / k2 / touch_creep_latch / controller_tag, G8 "
            "steps[].sidecar ACC_COMBO / ACC_K2, rows touch_creep_latch / controller_tag, steps[].events "
            "latch_rows (K-2 >= 1) / creep_rows (off 0)",
        },
    }


# ------------------------------------------------------------------------------------ V-6 / V-7
CHRONO_ROW_KEYS = (
    "case_id",
    "controller_tag",
    "k1_order_gate",
    "touch_creep_latch",
    "engine",
    "floor_true_deg",
    "t_touch_s",
    "t_lift_s",
    "t_ready_s",
    "J1_min_cyl_after_lift_N",
    "J1_window_s",
    "reanchor_intervals_s",
    "J2_min_cyl_reanchor_N",
    "J4_att_max_after_ready_deg",
    "J6_max_moving_bar",
    "J6_max_locked_bar",
    "crawler_recontact_after_loc",
    "events",
)
"""V-6 row keys (``k2_recount.DEFAULT_FIELDS["chrono_row"]``), read from the runner's row JSON (cad-expert 9.3)."""
CHRONO_PADS_KEYS = ("t", "N")
LOCKED_LIMIT_BAR = 350.0


def _latch_times(names_times: list[tuple[float, str]]) -> dict[int, float]:
    times: dict[int, float] = {}
    for t, name in names_times:
        if name.startswith(LATCH_EVENT + ":"):
            leg = name.split(":", 1)[1]
            if leg in LEG_NAMES:
                times.setdefault(LEG_NAMES.index(leg), float(t))
    return times


def false_latches(t_s, pad_N, latch_times: dict[int, float]) -> list[str]:
    """V-6 L2b (rules 3.5): true pad normal <= 0 at the latch or at one of the 5 window sample times."""
    import numpy as np

    t_s = np.asarray(t_s, float)
    pad_N = np.asarray(pad_N, float)
    bad = []
    for leg, t_latch in latch_times.items():
        for k in range(LATCH_WINDOW_SAMPLES):
            t_sample = t_latch - k * CONTROL_PERIOD_S
            index = int(np.searchsorted(t_s, t_sample + 1e-9)) - 1
            if index < 0 or pad_N[index, leg] <= 0.0:
                bad.append(f"{LEG_NAMES[leg]}@{t_sample:.3f}")
                break
    return bad


def chrono_option_problems(row: dict, engine: str) -> list[str]:
    """Rev2 4 V-6: L1 rows with the moving-leg pad damping on (zeta 0.10) and four valve-open shares (I-9), L2b
    rows with it off."""
    moving_on = engine == "L1"
    problems = []
    if row.get("moving_damping") is not moving_on:
        problems.append(f"E-5 moving_damping {row.get('moving_damping')!r} (expected {moving_on})")
    zeta = row.get("pad_zeta_moving")
    if (moving_on and not _close(zeta, PAD_ZETA_MOVING)) or (not moving_on and zeta is not None):
        problems.append(f"E-5 pad_zeta_moving {zeta!r}")
    if moving_on:
        share = open_share_problem(row.get("valve_open_fraction_touch_to_lift"))
        if share:
            problems.append(f"I-9 {share}")
    return problems


def _chrono_sh2(spec: dict, t_touch_s) -> float | None:
    """SH-2 of a Chrono row (rev2 3): ``k2_rate.npz`` body roll / pitch rate over [t_touch - 0.3 s, t_touch)."""
    import numpy as np

    path = spec.get("rate_npz")
    if not path or not Path(path).is_file():
        return None
    with np.load(path, allow_pickle=False) as rate:
        t_s, omega = np.asarray(rate["t"], float), np.asarray(rate["body_omega"], float).reshape(-1, 3)
    return k2_record.sh2_rate_amplitude_deg_s(t_s, omega, t_touch_s)


def chrono_sh(rows: list[dict], f_d8: float) -> dict:
    """Rev2 3: SH-1 .. SH-6 of the eight V-6 rows as one bundle (pairs ``<base>_off`` / ``<base>_tcl``);
    missing values are FLAGs with their counts, SH-2 needs four values per arm."""
    label = "V-6"
    k2_rows = [row for row in rows if row["k2_on"]]
    off_rows = [row for row in rows if not row["k2_on"]]
    missing = dict.fromkeys(("SH-1", "SH-2", "SH-3", "SH-4", "SH-5", "SH-6"), 0)
    flags = _sh_row_flags(k2_rows, f_d8, label, missing)
    l1_false = sum(len(row["false_latch"]) for row in k2_rows if row["engine"] == "L1")
    if l1_false:
        flags.append({"flag": "SH-5", "bundle": label, "l1_false_latches": l1_false})
    sh2_k2 = [row.get("sh2") for row in k2_rows]
    sh2_off = [row.get("sh2") for row in off_rows]
    missing["SH-2"] = sum(not d8x_judge._is_number(v) for v in sh2_k2 + sh2_off)
    k2_median, off_median = _median(sh2_k2), _median(sh2_off)
    enough = all(sum(d8x_judge._is_number(v) for v in values) >= 4 for values in (sh2_k2, sh2_off))
    if not enough:
        flags.append({"flag": "SH-2", "bundle": label, "fewer_than_4_values": True})
    elif k2_median > off_median:
        flags.append({"flag": "SH-2", "bundle": label, "k2_median": k2_median, "off_median": off_median})
    off_by_base = {row["id"].removesuffix("_off"): row for row in off_rows}
    delays = {}
    for row in k2_rows:
        base = row["id"].removesuffix("_tcl")
        a, b = row.get("t_ready_s"), (off_by_base.get(base) or {}).get("t_ready_s")
        if not (d8x_judge._is_number(a) and d8x_judge._is_number(b)):
            missing["SH-3"] += 1
            continue
        delays[base] = a - b
        if a - b > SH3_READY_DELAY_S:
            flags.append({"flag": "SH-3", "bundle": label, "id": base, "delay_s": a - b})
    j1_k2, j1_off = [_row_j(r, "J1_N") for r in k2_rows], [_row_j(r, "J1_N") for r in off_rows]
    missing["SH-4"] = sum(not d8x_judge._is_number(v) for v in j1_k2 + j1_off)
    erosion = None
    if not missing["SH-4"] and j1_k2 and j1_off:
        erosion = min(j1_k2) - min(j1_off)
        if erosion < SH4_J1_EROSION_N:
            flags.append({"flag": "SH-4", "bundle": label, "min_J1_difference_N": erosion})
    return {"bundle": label, "flags": flags + _sh_missing_flags(missing, label), "missing": missing,
            "sh2_medians": [k2_median, off_median], "sh4_min_J1_difference_N": erosion,
            "ready_delay_s": delays, "l1_false_latches": l1_false}


def judge_chrono_k2_row(name: str, spec: dict, f_d8: float) -> dict:
    import numpy as np

    row = d8x_judge._load_json(Path(spec["row_json"]))
    if spec.get("path"):
        row = _dotted(row, spec["path"])
    missing = [key for key in CHRONO_ROW_KEYS if key not in row]
    if missing:
        raise NotJudgeable(f"V-6 {name}: row keys missing {missing}")
    pads = np.load(spec["pads_npz"], allow_pickle=False)
    t_s, pad_N = (
        np.asarray(pads[CHRONO_PADS_KEYS[0]], float),
        np.asarray(pads[CHRONO_PADS_KEYS[1]], float),
    )
    after_touch = t_s >= row["t_touch_s"] - 1e-9
    d8x = {
        **{key: row[key] for key in d8x_judge.REQUIRED_D8X_KEYS if key in row},
        "J3_pad_lift_samples": int(np.sum(np.any(pad_N <= 0.0, axis=1) & after_touch)),
    }
    judged = d8x_judge.judge_metrics(d8x, [], f_d8)
    items = dict(judged["items"])
    items.pop("J11", None)  # harness driver item; Chrono rows have no driver fails list
    items["J6_locked"] = (
        d8x_judge._is_number(row["J6_max_locked_bar"])
        and row["J6_max_locked_bar"] <= LOCKED_LIMIT_BAR
    )
    items["J10"] = row["crawler_recontact_after_loc"] in (0, False)
    k2_on = spec["arm"] == "tcl"
    names_times = [(float(t), str(n)) for t, n in row["events"]]
    names = [n for _, n in names_times]
    problems = list(judged["not_judgeable"]) + k2_evidence_problems(names, k2_on)
    want_tag = expected_tag(False, k2_on)
    if row["controller_tag"] != want_tag:
        problems.append(f"I-10 tag {row['controller_tag']} != {want_tag}")
    if row["k1_order_gate"] is not False:
        problems.append("I-10 K1 order gate not off")
    floor = "k2pp025" if "k2pp025" in name else "fdown3.5"
    if not d8x_judge._angles_match(
        row["floor_true_deg"], CHRONO_FLOORS_DEG[floor], d8x_judge.ANGLE_TOLERANCE_CHRONO_DEG
    ):
        problems.append(f"E-7 floor {row['floor_true_deg']}")
    latch_times = _latch_times(names_times)
    false = false_latches(t_s, pad_N, latch_times)
    cap = sum(n.startswith(CAP_EVENT) for n in names)
    if k2_on and spec["engine"] == "L2b":
        items["V6_false_latch"] = not false
        items["V6_cap_latch"] = cap == 0
    problems += chrono_option_problems(row, spec["engine"])
    fail_items = sorted(k for k, ok in items.items() if not ok)
    return {
        "id": name,
        "engine": spec["engine"],
        "arm": spec["arm"],
        "k2_on": k2_on,
        "verdict": "not_judgeable" if problems else ("fail" if fail_items else "pass"),
        "fail_items": fail_items,
        "not_judgeable": problems,
        "J3": d8x["J3_pad_lift_samples"],
        "J3_margin_N": float(np.min(pad_N[after_touch])) if after_touch.any() else None,
        "false_latch": false,
        "cap": cap,
        "t_ready_s": row["t_ready_s"],
        "has_h4": bool(row["reanchor_intervals_s"]),
        "sh1": k2_record.sh1_lift_chunks_after_latch(t_s, pad_N, row["events"], row["t_touch_s"]),
        "sh2": _chrono_sh2(spec, row["t_touch_s"]),
        "values": judged["values"],
        # rules rev1 4, record only: the cad runner writes k2_row.json k2.dhat_* (path 2 reads the same)
        "dhat_N": (row.get("k2") or {}).get("dhat_N"),
        "dhat_window_open_legs": (row.get("k2") or {}).get("dhat_window_open_legs"),
        "dhat_window_stroke_mm": (row.get("k2") or {}).get("dhat_window_stroke_mm"),
    }


def cmd_judge_v6(args) -> tuple[int, dict]:
    problems = seal_problems()
    part = _manifest_part(args, "v6")
    f_d8 = f_d8_N()
    specs = part.get("rows", {})
    if sorted(specs) != sorted(CHRONO_ROWS):
        problems.append(f"E-1 V-6 rows {sorted(specs)} != rules 3.5")
    rows = [judge_chrono_k2_row(name, spec, f_d8) for name, spec in sorted(specs.items())]
    k2_rows = [row for row in rows if row["k2_on"]]
    summary = summarise(k2_rows, 4, "V-6 K-2 rows")
    problems += [p for row in rows for p in row["not_judgeable"]]
    status = _status(problems, [summary])
    stem = {"off": "_off", "tcl": "_tcl"}
    dhat = dhat_record(
        {row["id"].removesuffix(stem["tcl"]): row["dhat_N"] for row in rows if row["k2_on"]},
        {row["id"].removesuffix(stem["off"]): row["dhat_N"] for row in rows if not row["k2_on"]},
        "V-6",
    )
    sh = chrono_sh(rows, f_d8)
    return status, {
        "bundle": "V-6",
        "gate": {"G-E": _gate_value(status, [summary])},
        "summary": summary,
        "sh": [sh],
        "dhat": dhat,
        "rows": rows,
        "problems": problems,
        "field_map": {
            "row": list(CHRONO_ROW_KEYS),
            "pads_npz": list(CHRONO_PADS_KEYS),
            "J3": "pads N <= 0 after t_touch_s",
            "false latch": "rules 3.5 L2b",
            "D_hat (rev1 4, record)": "k2.dhat_N, k2.dhat_window_open_legs, k2.dhat_window_stroke_mm",
            "SH (rev2 3)": "SH-1 pads_npz N <= 0 after each leg's latch and before t_touch_s; SH-2 rate_npz "
            "body_omega[:, :2] over [t_touch_s - 0.3, t_touch_s), medians of 4 + 4 rows; SH-3 t_ready_s "
            "pairs; SH-4 min J1_min_cyl_after_lift_N per arm; SH-5 events INFO_TOUCH_CREEP_CAP + L1 false "
            "latches; SH-6 J1 / J2 (rows with reanchor_intervals_s) < F_D8 + 2 kN",
            "E-5 / I-9 (rev2 4)": "moving_damping, pad_zeta_moving (L1 0.10, L2b None), "
            "valve_open_fraction_touch_to_lift (L1: 4 legs in [0, 1])",
        },
    }


def cmd_record_v7(args) -> tuple[int, dict]:
    part = _manifest_part(args, "v7")
    records = {}
    for name, spec in sorted(part.get("rows", {}).items()):
        row = d8x_judge._load_json(Path(spec["row_json"]))
        if spec.get("path"):
            row = _dotted(row, spec["path"])
        names = [str(n) for _, n in row.get("events", [])]
        records[name] = {
            key: row.get(key)
            for key in ("controller_tag", "t_touch_s", "t_ready_s", "J1_min_cyl_after_lift_N")
        }
        records[name].update(
            cap=sum(n.startswith(CAP_EVENT) for n in names),
            latches=sum(n.startswith(LATCH_EVENT) for n in names),
        )
    status = EXIT_NOT_JUDGEABLE if len(records) != EXPECTED_ROWS["v7"] else EXIT_PASS
    return status, {"bundle": "V-7", "record_only": True, "rows": records}


# --------------------------------------------------------------------------------------- report
GATE_FILES = ("v2", "v3", "v4", "v5", "v6")


def cmd_report(args) -> tuple[int, dict]:
    problems = seal_problems()
    gates, flags, dhat = {}, [], []
    for bundle in GATE_FILES:
        path = getattr(args, bundle)
        if path is None:
            problems.append(f"report: no {bundle} judgement")
            continue
        doc = d8x_judge._load_json(Path(path))
        gates.update(doc.get("gate", {}))
        blocks = doc.get("dhat")  # rules rev1 4: V-2, V-3 judged arms, V-4, V-6 (record only)
        dhat += blocks if isinstance(blocks, list) else ([blocks] if blocks else [])
        for block in doc.get("sh", []):
            flags += block.get("flags", [])
            if block.get("not_judgeable"):
                problems.append(f"{block['bundle']}: {block['not_judgeable']}")
    gates["G-F"] = "pass" if args.recount_match else "not_judgeable"
    if not args.recount_match:
        problems.append("G-F two-path recount match not confirmed (--recount-match)")
    grade = _grade(gates, flags, problems)
    status = {"not_judgeable": EXIT_NOT_JUDGEABLE, "fail": EXIT_FAIL}.get(grade, EXIT_PASS)
    return status, {"gates": gates, "flags": flags, "grade": grade, "problems": problems,
                    "dhat_record": dhat}


def _grade(gates: dict, flags: list, problems: list) -> str:
    """Rules 10: not judgeable > fail > conditional (range, B-2) > conditional > pass."""
    if problems or any(value == "not_judgeable" for value in gates.values()):
        return "not_judgeable"
    if any(gates.get(gate) == "fail" for gate in ("G-B", "G-C", "G-D", "G-E")):
        return "fail"
    if gates.get("G-A") == "fail":
        return "conditional_range"
    return "conditional" if flags else "pass"


# ---------------------------------------------------------------------------------------- CLI
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="K-2 judge, path 1 (k2_touch_creep_rules.md 8)")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--format", choices=("json", "md"), default="json")
    sub = parser.add_subparsers(dest="command", required=True)
    points = sub.add_parser("points")
    points.add_argument("--points-file", default=str(POINTS_PATH))
    points.add_argument("--check", action="store_true")
    prelaunch = sub.add_parser("prelaunch")
    prelaunch.add_argument("--bundle", required=True, choices=("v2", "v3", "v4", "v5", "v6", "v7"))
    prelaunch.add_argument(
        "--stored-off", default=None, help="v3: stored D8x ra_off.json (key selection)"
    )
    prelaunch.add_argument("--write-keys", default=None, help="v3: write the 273 keys to this file")
    prelaunch.add_argument("--plan-id", default=None, help="compute-scheduler-expert plan id (I-3)")
    prelaunch.add_argument("--python", default=None, help="run interpreter to record (I-2)")
    for name in ("judge-v2", "judge-v3", "judge-v4", "judge-v5", "judge-v6", "record-v7"):
        command = sub.add_parser(name)
        command.add_argument(
            "--manifest",
            required=True,
            help="inputs JSON in the k2_recount.py manifest layout (v2 / v4: off, tcl, "
            "series_root, points, stored_off; v3: arms.<arm>.off / tcl; v5: bundles; "
            "v6 / v7: rows)",
        )
    selftest = sub.add_parser("selftest-v5-stored")
    selftest.add_argument("--acceptance", default=str(STORED_ACCEPTANCE_DIR))
    selftest.add_argument("--ps7", default=str(STORED_PS7))
    report = sub.add_parser("report")
    for bundle in GATE_FILES:
        report.add_argument(f"--{bundle}", default=None, help=f"judge-{bundle} output JSON")
    report.add_argument(
        "--recount-match", action="store_true", help="the two-path recount matched (8)"
    )
    return parser


COMMANDS = {
    "points": cmd_points,
    "prelaunch": cmd_prelaunch,
    "judge-v2": cmd_judge_v2,
    "judge-v3": cmd_judge_v3,
    "judge-v4": cmd_judge_v4,
    "judge-v5": cmd_judge_v5,
    "judge-v6": cmd_judge_v6,
    "record-v7": cmd_record_v7,
    "selftest-v5-stored": cmd_selftest_v5_stored,
    "report": cmd_report,
}


def _markdown(command: str, status: int, result: dict) -> str:
    lines = [f"# k2_judge {command}", "", f"exit {status}", ""]
    for key in ("gate", "grade", "summaries", "summary", "problems"):
        if key in result:
            lines.append(f"- {key}: {json.dumps(result[key], default=float)[:2000]}")
    return "\n".join(lines) + "\n"


def run(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        status, result = COMMANDS[args.command](args)
    except NotJudgeable as exc:
        status, result = EXIT_NOT_JUDGEABLE, {"problems": [str(exc)]}
    except Exception as exc:  # contract: internal error = exit 3 with the traceback in the record
        status, result = (
            EXIT_INTERNAL,
            {"error": repr(exc), "traceback": traceback.format_exc()[-3000:]},
        )
    result = {"command": args.command, "exit": status, **result}
    if args.format == "md":
        text = _markdown(args.command, status, result)
    else:
        text = json.dumps(result, indent=1, default=float)
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8")
    summary = {
        "command": args.command,
        "exit": status,
        **{key: result[key] for key in ("gate", "grade") if key in result},
        "problems": len(result.get("problems", [])),
    }
    print(json.dumps(summary, default=float))
    return status


if __name__ == "__main__":
    sys.exit(run())
