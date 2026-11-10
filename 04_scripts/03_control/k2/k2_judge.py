"""K-2 judge, path 1 (``06_analysis/02_control/k2/k2_touch_creep_rules.md`` 8, 9.1-5). Reads the raw results;
never runs a simulation.

Sub-commands:
  points      write ``k2_points_5p5_3p5.json`` (rules 3.2, ``d8x_diag.diamond_points(5.5, 3.5)``), or ``--check`` it
  prelaunch   run-start record ``k2_prelaunch_<bundle>.json`` (I-2, I-3, I-7; V-3 key list, ``--write-keys``)
  judge-v2    V-2 D8x R-a, off + K-2 arms x K1 off / on (G-A, I-4, E-1 .. E-9, SH-1 .. SH-6)
  judge-v3    V-3 dissipation arms x {off, K-2} on the 273 keys (G-B, E-5, I-9)
  judge-v4    V-4 5.5 / 3.5 boundary, top, K1 off (G-C)
  judge-v5    V-5 acceptance regression, K-2 arm vs the off arm of the same commit (G-D)
  judge-v6    V-6 Chrono 8 rows (G-E: K-2 rows; off rows recorded; 5.4 prediction table)
  record-v7   V-7 SCM 4 rows (record only)
  report      gates G-S .. G-F and the grade (10) from the outputs above

Common contract: ``--out <file>`` (the report JSON), ``--format json|md``; exit 0 pass, 1 fail, 2 not judgeable /
input error (a missing result key is 2), 3 internal error; the last stdout line is JSON. The rules file must match
its sealed sha256 (``k2_touch_creep_rules.sha256``) and the dynamics spec its rules 3.3 sha256 (exit 2 otherwise).
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
for _folder in (D8X_DIR, ACCEPTANCE_DIR, ROOT / "03_src"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

import d8x_judge  # noqa: E402  (row J items, loaders, NotJudgeable)

from outrigger_sim.hydraulics import v5_options  # noqa: E402

K2_DIR = ROOT / "06_analysis" / "02_control" / "k2"
RULES_PATH = K2_DIR / "k2_touch_creep_rules.md"
RULES_SEAL_PATH = K2_DIR / "k2_touch_creep_rules.sha256"
DYN_SPEC_PATH = K2_DIR / "k2_dyn_spec.md"
DYN_SPEC_SHA256 = "502b0bb78558d40586cbcddb718b6c5d53529de4e78369f454762c9fe73727ff"
"""Rules 3.3: raw sha256 of the dynamics spec."""
POINTS_PATH = K2_DIR / "k2_points_5p5_3p5.json"
POINTS_SCHEMA = "k2_points/1"
HALF_SPANS_DEG = (5.5, 3.5)
D45_TABLE_DEG = 19.25 / 9.0
"""Rules 3.2 table: ``d45 = 5.5 * 3.5 / 9``."""
POINT_TOLERANCE_DEG = 1e-12
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
    "I-9": "aug_arm, is_kplant (row) and k2.aug.{preset, case_id, plant_aug.options, valve_open_fraction_touch_to_lift}",
    "SH-1": "k2.SH1_lift_chunks_after_latch (per leg) > 0 on a K-2 row",
    "SH-2": "median k2.SH2_rate_amp_deg_s of the K-2 rows > median of the off rows (per bundle)",
    "SH-3": "t_ready_s(K-2) - t_ready_s(off) > 3.0 s (per pair)",
    "SH-4": "min J1(K-2 rows) - min J1(off rows) < -3 kN (per bundle)",
    "SH-5": "k2.event_counts.INFO_TOUCH_CREEP_CAP > 0 on a K-2 row",
    "SH-6": "J1 or J2 < F_D8 + 2 kN on a K-2 row",
}


# ----------------------------------------------------------------------------------- helpers
def raw_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seal_problems() -> list[str]:
    """I-7: the rules file raw sha256 == its seal, the dynamics spec == rules 3.3."""
    problems = []
    try:
        sealed = RULES_SEAL_PATH.read_text(encoding="utf-8").split()[0]
    except (FileNotFoundError, IndexError):
        return [f"I-7 no seal {RULES_SEAL_PATH}"]
    if raw_sha256(RULES_PATH) != sealed:
        problems.append(f"I-7 {RULES_PATH.name} sha256 {raw_sha256(RULES_PATH)} != sealed {sealed}")
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
        "table_check": {
            "max_difference_deg": max(differences.values()),
            "differences_above_tolerance": {
                t: d for t, d in differences.items() if d > POINT_TOLERANCE_DEG
            },
        },
    }


def cmd_points(args) -> tuple[int, dict]:
    doc = build_points()
    path = Path(args.points_file)
    problems = []
    above = doc["table_check"]["differences_above_tolerance"]
    if above:  # rules 3.2: the file must equal diamond_points and the table; d45 cannot be both
        problems.append(
            f"3.2 rules table vs diamond_points differ above {POINT_TOLERANCE_DEG:g} deg: {above}"
        )
    if args.check:
        stored = d8x_judge._load_json(path)
        if json.dumps(stored, sort_keys=True) != json.dumps(doc, sort_keys=True):
            problems.append(f"{path} differs from diamond_points(5.5, 3.5) (3.2)")
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
        "commands_sha256": row.get("commands_sha256"),
        "sh1": k2.get("SH1_lift_chunks_after_latch"),
        "sh2": k2.get("SH2_rate_amp_deg_s"),
        "cap": (k2.get("event_counts") or {}).get(CAP_EVENT),
        "J3_margin_N": (row.get("d8x") or {}).get("J3_pad_normal_min_N"),
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


def sh_flags(k2_rows: list[dict], off_rows: list[dict], f_d8: float, label: str) -> dict:
    """SH-1 .. SH-6 of one bundle (rules 5.2; E-11 pairs by (id, K1 arm))."""
    off_by_key = {(row["id"], row["k1_on"]): row for row in off_rows}
    k2_by_key = {(row["id"], row["k1_on"]): row for row in k2_rows}
    unpaired = sorted(str(key) for key in set(off_by_key) ^ set(k2_by_key))
    flags = []
    for row in k2_rows:
        sh1 = row.get("sh1") or []
        if any((count or 0) > 0 for count in sh1):
            flags.append({"flag": "SH-1", "bundle": label, "id": row["id"], "value": sh1})
        if (row.get("cap") or 0) > 0:
            flags.append({"flag": "SH-5", "bundle": label, "id": row["id"], "value": row["cap"]})
        values = row.get("values") or {}
        for item in ("J1_N", "J2_N"):
            if d8x_judge._is_number(values.get(item)) and values[item] < f_d8 + SH6_MARGIN_N:
                flags.append({"flag": "SH-6", "bundle": label, "id": row["id"], item: values[item]})
    if unpaired:
        return {
            "bundle": label,
            "not_judgeable": f"E-11 {len(unpaired)} unpaired keys",
            "unpaired": unpaired[:20],
            "flags": flags,
        }
    k2_median = _median(row.get("sh2") for row in k2_rows)
    off_median = _median(row.get("sh2") for row in off_rows)
    if k2_median is not None and off_median is not None and k2_median > off_median:
        flags.append(
            {"flag": "SH-2", "bundle": label, "k2_median": k2_median, "off_median": off_median}
        )
    delays = []
    for key, row in k2_by_key.items():
        a, b = row.get("t_ready_s"), off_by_key[key].get("t_ready_s")
        if d8x_judge._is_number(a) and d8x_judge._is_number(b):
            delays.append((a - b, key[0]))
            if a - b > SH3_READY_DELAY_S:
                flags.append({"flag": "SH-3", "bundle": label, "id": key[0], "delay_s": a - b})
    j1_k2 = [
        r["values"]["J1_N"]
        for r in k2_rows
        if d8x_judge._is_number((r.get("values") or {}).get("J1_N"))
    ]
    j1_off = [
        r["values"]["J1_N"]
        for r in off_rows
        if d8x_judge._is_number((r.get("values") or {}).get("J1_N"))
    ]
    erosion = (min(j1_k2) - min(j1_off)) if j1_k2 and j1_off else None
    if erosion is not None and erosion < SH4_J1_EROSION_N:
        flags.append({"flag": "SH-4", "bundle": label, "min_J1_difference_N": erosion})
    return {
        "bundle": label,
        "flags": flags,
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
    return {"summaries": summaries, "sh": sh}, off, tcl, problems


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
    problems += more
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
    problems += more
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


def _aug_problems(files: list[str], arm: str) -> list[str]:
    """E-5 / I-9 of the V-3 rows of one arm (top-level ``aug_arm`` / ``is_kplant``, the ``k2.aug`` block)."""
    problems = []
    for path in files:
        for run in _runs_of(Path(path)):
            aug = (run.get("k2") or {}).get("aug") or {}
            if run.get("aug_arm") != arm or run.get("is_kplant") is not True:
                problems.append(
                    f"E-5 {run.get('id')}: aug_arm {run.get('aug_arm')} / is_kplant "
                    f"{run.get('is_kplant')}"
                )
            elif (
                aug.get("preset") != V3_DISS_PRESETS[arm]
                or aug.get("case_id") != run.get("id")
                or aug.get("valve_open_fraction_touch_to_lift") is None
                or not (aug.get("plant_aug") or {}).get("options")
                and arm != "H0"
            ):
                problems.append(
                    f"I-9 {run.get('id')}: preset / case_id / valve-open share / options"
                )
            if len(problems) > 20:
                return problems
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
    """One-sided Clopper-Pearson 95 % upper bound of a failure rate."""
    from scipy.stats import beta

    return 1.0 if failures >= n else float(beta.ppf(0.95, failures + 1, n - failures))


def v5_bundle(spec: dict) -> dict:
    """One V-5 bundle of the manifest (``kind`` pass_to_fail | noise_cp | g8; ``off`` / ``tcl`` file lists;
    ``key`` / ``status`` dotted paths; g8 ``ready`` / ``faults``)."""
    off = [row for path in spec["off"] for row in _runs_of(Path(path))]
    tcl = [row for path in spec["tcl"] for row in _runs_of(Path(path))]
    off_by_key = {str(_dotted(row, spec["key"])): row for row in off}
    tcl_by_key = {str(_dotted(row, spec["key"])): row for row in tcl}
    result = {
        "kind": spec["kind"],
        "n_off": len(off),
        "n_tcl": len(tcl),
        "unpaired": sorted(set(off_by_key) ^ set(tcl_by_key)),
    }
    if len(off_by_key) != len(off) or len(tcl_by_key) != len(tcl):
        result.update(passed=False, not_judgeable="duplicate keys")
        return result
    common = sorted(set(off_by_key) & set(tcl_by_key))
    if spec["kind"] in ("pass_to_fail", "noise_cp"):
        result["pass_to_fail"] = [
            k
            for k in common
            if _passed(off_by_key[k], spec["status"]) and not _passed(tcl_by_key[k], spec["status"])
        ]
    if spec["kind"] == "pass_to_fail":
        result["passed"] = not result["pass_to_fail"]
    elif spec["kind"] == "noise_cp":
        failures = sum(not _passed(row, spec["status"]) for row in tcl)
        result.update(failures=failures, cp95_upper=cp_upper_95(failures, len(tcl)))
        result["passed"] = result["cp95_upper"] <= NOISE_CP_LIMIT
    elif spec["kind"] == "g8":
        failures = []
        for key in common:
            a, b = off_by_key[key], tcl_by_key[key]
            if bool(_dotted(a, spec["ready"])) and not bool(_dotted(b, spec["ready"])):
                failures.append([key, "ready lost"])
            old = {
                str(n).split(":")[0]
                for n in _dotted(a, spec["faults"]) or []
                if str(n).startswith("FAULT_")
            }
            new = {
                str(n).split(":")[0]
                for n in _dotted(b, spec["faults"]) or []
                if str(n).startswith("FAULT_")
            }
            if new - old:
                failures.append([key, f"new FAULT {sorted(new - old)}"])
            if spec.get("status") and _passed(a, spec["status"]) and not _passed(b, spec["status"]):
                failures.append([key, "status pass->fail"])
        result.update(failures=failures, passed=not failures)
    else:
        raise NotJudgeable(f"V-5 kind {spec['kind']!r}")
    if result["unpaired"]:
        result.update(passed=False, not_judgeable=f"unpaired keys {len(result['unpaired'])}")
    return result


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
        "problems": problems,
        "field_map": {
            "V-5": "manifest v5.<bundle>: kind, off / tcl files, key / status (/ ready, "
            "faults) dotted paths of the driver rows (rules 3.4)"
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
        "values": judged["values"],
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
    return status, {
        "bundle": "V-6",
        "gate": {"G-E": _gate_value(status, [summary])},
        "summary": summary,
        "rows": rows,
        "problems": problems,
        "field_map": {
            "row": list(CHRONO_ROW_KEYS),
            "pads_npz": list(CHRONO_PADS_KEYS),
            "J3": "pads N <= 0 after t_touch_s",
            "false latch": "rules 3.5 L2b",
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
    gates, flags = {}, []
    for bundle in GATE_FILES:
        path = getattr(args, bundle)
        if path is None:
            problems.append(f"report: no {bundle} judgement")
            continue
        doc = d8x_judge._load_json(Path(path))
        gates.update(doc.get("gate", {}))
        for block in doc.get("sh", []):
            flags += block.get("flags", [])
            if block.get("not_judgeable"):
                problems.append(f"{block['bundle']}: {block['not_judgeable']}")
    gates["G-F"] = "pass" if args.recount_match else "not_judgeable"
    if not args.recount_match:
        problems.append("G-F two-path recount match not confirmed (--recount-match)")
    grade = _grade(gates, flags, problems)
    status = {"not_judgeable": EXIT_NOT_JUDGEABLE, "fail": EXIT_FAIL}.get(grade, EXIT_PASS)
    return status, {"gates": gates, "flags": flags, "grade": grade, "problems": problems}


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
