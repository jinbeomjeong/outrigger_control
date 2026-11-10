"""K-2 V-5 flattener: the V-5 step outputs of one arm as flat rows plus the raw fields of the rev2 absolute items.

``k2_touch_creep_rules_rev2.md`` 1 judges V-5 with the absolute items of ``touch_phase/acceptance/criteria.md`` on
the K-2 arm and pass -> fail against the off arm. Path 1 (``k2_judge.py judge-v5``) reads this tool's output; path 2
(``k2_recount.py``) reads the raw outputs itself (rules 8 independence). This tool decides nothing: it moves the
existing per-row verdicts into rows (``key``, ``pass``; g8 also ``ready`` and ``faults``) and copies, without
judging them, the raw values the absolute items need:

==============  ============================================  ==================================================
bundle          source files (one arm folder)                 row verdict taken from / raw fields copied
==============  ============================================  ==================================================
grid            grid_r67_main, grid_r67_top, grid_r69_top,    ``results[].runs[].pass`` (``acc_judge.event_runs``;
                grid_r69_bottom (.json)                       an errored result is a row with ``pass`` false);
                                                              ``error``, ``fault_periods``
soil            soil_A.json                                   the same, ``|two`` keys only (acc_judge soil)
regression      clip_harness, clip_p0, clip_x426_C,           ``acc_judge.flat_verdicts`` + ``is_good``; clip_A by
                clip_x426_D, clip_A, clip_r79_L1L2_judgement  ``event_runs``; the r79 L1/L2 judgement ``runs[].pass``
                (+ raw clip_r79_L1L2, clip_r79_L3L4)          (clip_r79_L3L4 is record only: not a row; its events
                                                              and step identity are read); meta: r79 judgement
                                                              ``unmatched`` / ``errors``, the rev2 2 key lists
d8              d8_both.json                                  ``acc_judge.judge_d8`` row conditions; ``error``,
                                                              ``fails``, ``fault``, ``min_true_cyl_force_kN``,
                                                              ``ss_true_att_deg_maxabs``, ``t_ready_s``
noise_L2        r79_L1L2_judgement.json (+ raw r79_L1L2.json) ``runs[].pass`` of the L2 rows without S1@FL / S1@FR
                                                              (``acc_judge.noise_verdict``); meta: judgement
                                                              ``unmatched`` / ``errors``, ``reference`` group
                                                              ``all`` ``false_loc``, ``controller_settings`` vs
                                                              ``meta.preset_settings`` of the raw run (SGS keys
                                                              judged, rev4 1 (b); all keys recorded)
ps7             ps7.json or ps7_E.json (run_ps7 --out)        ``[].pass`` (``r68.run_job``); ``error``,
                                                              ``controller_tag``, ``touch_creep_latch``
g8_safe_stop    g8_jobs1, g8_jobs3, g8_jobs5 (.jsonl)         ``pass``; ``ready`` = ``final == "ready"``; ``faults``
                                                              = ``warn_fault`` names starting with FAULT; ``error``
==============  ============================================  ==================================================

Every bundle meta also holds, per V-5 step of the bundle (``k2_commands.json`` step names), the identity sidecar
(``<arm>/<step>.launch.json``: ``rc``, ``ACC_COMBO`` / ``ACC_K2``, git heads), the provenance record
(``<arm>/provenance/<step>.json``; d8: ``d8_both.json`` ``meta``) and, for the outputs with event lists (noise raw
run, PS-7, ``clip_r79_*``), the rows with ``INFO_TOUCH_CREEP_LATCH`` / any ``INFO_TOUCH_CREEP_*``. A missing file is
recorded as missing (``exists`` false), not filled in: the judge counts it (E-9).

The r79 judgement files are the outputs of ``04_scripts/03_control/s8/r79_sensor_judge.py judge <out> <run>``
(as ``acc_judge.r79_judge``); without them the tool stops with that command, unless ``--run-r79-judge`` lets it
run the judge itself with this interpreter.

Usage (python-dev or dynamics-dev; scipy for acc_judge)::

    python -I -B k2_v5_flatten.py --arm-dir runs/v5/off --out-dir runs/v5/off/flat
        [--checkout <run checkout>] [--source <bundle>:<part>=<file> ...] [--run-r79-judge]

Writes ``<out-dir>/<bundle>.json`` (``{"meta", "runs"}``) per bundle and ``<out-dir>/flatten_summary.json``.
Exit 0 written, 2 input error (missing or unreadable source, existing output), 3 internal error. The last stdout
line is JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ACCEPTANCE_DIR = ROOT / "04_scripts" / "03_control" / "touch_phase" / "acceptance"
GUARD_KN = 14.41
"""acc_judge ``GUARD_KN`` (F_min + 5 kN)."""
D8_ATTITUDE_LIMIT_DEG = 0.2
D8_READY_LIMIT_S = 100.0
S1_FRONT = ("S1@FL", "S1@FR")
LATCH_EVENT = "INFO_TOUCH_CREEP_LATCH"
CREEP_EVENT_PREFIX = "INFO_TOUCH_CREEP_"
SETTINGS_LEVEL_KEYS = ("target.gyro_noise_std_rad_s",)
"""``controller_settings`` keys the r79 sensor level sets per row (L2: the gyro noise of the sensor model), so they
differ from ``meta.preset_settings`` by design; recorded only (rev4 1 (b) judges the SGS keys)."""
SGS_SETTINGS_PREFIX = "lift_stroke_guard."
SOURCES: dict[str, dict[str, tuple[str, ...]]] = {
    "grid": {"grid_r67_main": ("grid_r67_main.json",), "grid_r67_top": ("grid_r67_top.json",),
             "grid_r69_top": ("grid_r69_top.json",), "grid_r69_bottom": ("grid_r69_bottom.json",)},
    "soil": {"soil_A": ("soil_A.json",)},
    "regression": {"clip_harness": ("clip_harness.json",), "clip_p0": ("clip_p0.json",),
                   "clip_x426_C": ("clip_x426_C.json",), "clip_x426_D": ("clip_x426_D.json",),
                   "clip_A": ("clip_A.json",), "clip_r79_L1L2": ("clip_r79_L1L2_judgement.json",)},
    "d8": {"d8": ("d8_both.json",)},
    "noise_L2": {"r79_L1L2": ("r79_L1L2_judgement.json",)},
    "ps7": {"ps7": ("ps7.json", "ps7_E.json")},
    "g8_safe_stop": {"g8_jobs1": ("g8_jobs1.jsonl",), "g8_jobs3": ("g8_jobs3.jsonl",),
                     "g8_jobs5": ("g8_jobs5.jsonl",)},
}
"""bundle -> part -> accepted file names, looked up in the arm folder and its sub-folder named after the
bundle family (``grid/``, ``regression/``, ``soil/``, ``d8/``, ``noise/``) as in the acceptance layout."""
RAW_SOURCES: dict[str, dict[str, tuple[str, ...]]] = {
    "regression": {"clip_r79_L1L2_run": ("clip_r79_L1L2.json",), "clip_r79_L3L4_run": ("clip_r79_L3L4.json",)},
    "noise_L2": {"r79_L1L2_run": ("r79_L1L2.json",)},
}
"""Raw step outputs read for the absolute items and the K-2 evidence only (no rows of their own)."""
SUBFOLDERS = {"grid": "grid", "soil": "soil", "regression": "regression", "d8": "d8", "noise_L2": "noise"}
R79_RUN_OF_JUDGEMENT = {"clip_r79_L1L2_judgement.json": "clip_r79_L1L2.json",
                        "r79_L1L2_judgement.json": "r79_L1L2.json"}
EXIT_WRITTEN, EXIT_INPUT, EXIT_INTERNAL = 0, 2, 3


@dataclass(frozen=True)
class Step:
    """One V-5 step of ``k2_commands.json``: its sidecar / provenance name and the part holding its events."""

    name: str
    provenance: str | None = "file"
    """``file`` (``provenance/<name>.json``), ``output:<part>`` (that output's ``meta``) or None (no record)."""
    events_part: str | None = None


STEPS: dict[str, tuple[Step, ...]] = {
    "grid": tuple(Step(part) for part in SOURCES["grid"]),
    "soil": (Step("soil_A"),),
    "regression": (Step("reg1"), Step("reg2"), Step("reg3"), Step("reg4", events_part="clip_r79_L1L2_run"),
                   Step("reg5", events_part="clip_r79_L3L4_run"), Step("reg6"), Step("reg7"),
                   Step("clip_r79_L1L2_judgement", provenance=None)),
    "d8": (Step("d8", provenance="output:d8"),),
    "noise_L2": (Step("noise_L1L2", events_part="r79_L1L2_run"), Step("r79_L1L2_judgement", provenance=None)),
    "ps7": (Step("ps7", events_part="ps7"),),
    "g8_safe_stop": tuple(Step(part, provenance=None) for part in SOURCES["g8_safe_stop"]),
}
"""bundle -> its V-5 steps (``k2_commands.json`` ``v5_<step>_<arm>``; sidecar ``<arm>/<step>.launch.json``)."""
PROVENANCE_KEYS = ("combo", "k2", "touch_creep_latch", "controller_tag", "c2_sha256", "git_head")
SIDECAR_ENV_KEYS = ("ACC_COMBO", "ACC_K2")


class InputError(Exception):
    """A source is missing or unreadable (exit 2)."""


def _acc_judge():
    if str(ACCEPTANCE_DIR) not in sys.path:
        sys.path.insert(0, str(ACCEPTANCE_DIR))
    import acc_judge

    return acc_judge


# ------------------------------------------------------------------------------- reading
def _load(path: Path):
    try:
        if path.suffix == ".jsonl":
            return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"{path}: {exc}") from exc


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def locate(arm_dir: Path, bundle: str, part: str, overrides: dict[str, Path],
           table: dict[str, dict[str, tuple[str, ...]]] = SOURCES) -> Path | None:
    """The source file of one part: an override, the arm folder, or its bundle sub-folder."""
    override = overrides.get(f"{bundle}:{part}")
    if override is not None:
        return override
    folders = [arm_dir]
    if bundle in SUBFOLDERS:
        folders.append(arm_dir / SUBFOLDERS[bundle])
    for name in table[bundle][part]:
        for folder in folders:
            if (folder / name).is_file():
                return folder / name
    return None


def has_error(entry: dict) -> bool:
    """Rev4 1 (a): an ``error`` value that is not empty (None, ``""``, ``[]``, ``{}`` are no error; g8trace writes
    ``"error": null`` on every row)."""
    value = entry.get("error")
    return value is not None and value is not False and value not in ("", [], {})


def error_rows(doc) -> int:
    """Entries with an error in ``results[]``, ``results[].runs[]``, ``runs[]``, ``records[]`` (a list doc: its
    entries)."""
    if isinstance(doc, list):
        return sum(has_error(entry) for entry in doc if isinstance(entry, dict))
    count = 0
    for name in ("results", "runs", "records"):
        for entry in doc.get(name) or []:
            if not isinstance(entry, dict):
                continue
            count += has_error(entry)
            count += sum(has_error(run) for run in entry.get("runs") or [] if isinstance(run, dict))
    return count


def _event_names(events) -> list[str]:
    names = []
    for event in events or []:
        names.append(str(event[1]) if isinstance(event, (list, tuple)) and len(event) >= 2 else str(event))
    return names


def event_record(doc, source: str) -> dict:
    """Rows of an output with an event list and how many carry a latch / any creep event (rev2 1 evidence)."""
    rows = doc if isinstance(doc, list) else doc.get("results") or []
    latch = creep = with_events = 0
    for row in rows:
        names = _event_names(row.get("events"))
        with_events += "events" in row
        latch += any(name.startswith(LATCH_EVENT) for name in names)
        creep += any(name.startswith(CREEP_EVENT_PREFIX) for name in names)
    return {"source": source, "rows": len(rows), "rows_with_event_list": with_events, "latch_rows": latch,
            "creep_rows": creep}


# ------------------------------------------------------------------------------- per bundle rows
def _event_rows(doc: dict, prefix: str, keep=lambda key: True) -> list[dict]:
    """``acc_judge.event_runs``: one row per run (errored results: one row, ``pass`` false)."""
    rows = []
    for key, run in _acc_judge().event_runs(doc).items():
        if not keep(key):
            continue
        if len(key) == 2:
            rows.append({"key": f"{prefix}|{key[0]}|error", "pass": False, "error": True,
                         "fault_periods": None})
            continue
        rows.append({"key": f"{prefix}|" + "|".join(str(item) for item in key), "pass": bool(run.get("pass")),
                     "error": has_error(run), "fault_periods": run.get("fault_periods"),
                     "commands_sha256": run.get("commands_sha256")})
    return rows


def _flat_rows(doc: dict, prefix: str) -> list[dict]:
    """``acc_judge.flat_verdicts`` + ``is_good`` (wrapper, H8 and x426 formats)."""
    acc_judge = _acc_judge()
    return [{"key": f"{prefix}|{key}", "pass": bool(acc_judge.is_good(verdict)), "verdict": verdict}
            for key, verdict in acc_judge.flat_verdicts(doc).items()]


def _r79_rows(doc: dict, prefix: str, *, l2_without_s1_front: bool) -> list[dict]:
    """``runs[]`` of an r79 judgement (``acc_judge.noise_verdict`` filter for the noise bundle)."""
    rows = []
    for run in doc["runs"]:
        if l2_without_s1_front and (run["level"] != "L2" or any(m in run["inner"] for m in S1_FRONT)):
            continue
        rows.append({"key": f"{prefix}|{run['key']}", "pass": bool(run["pass"]), "level": run.get("level")})
    return rows


def d8_row_pass(run: dict) -> bool:
    """The row conditions of ``acc_judge.judge_d8`` (its ``bad`` lists): a row passes when it is in none."""
    if "error" in run:
        return False
    return not (run.get("fails") or run.get("fault") or run["min_true_cyl_force_kN"] < GUARD_KN
                or run["ss_true_att_deg_maxabs"] > D8_ATTITUDE_LIMIT_DEG
                or not run.get("t_ready_s") or run["t_ready_s"] > D8_READY_LIMIT_S)


D8_RAW_FIELDS = ("fails", "fault", "min_true_cyl_force_kN", "ss_true_att_deg_maxabs", "t_ready_s")


def _d8_rows(doc: dict) -> list[dict]:
    rows = []
    for run in doc["runs"]:
        try:
            passed = d8_row_pass(run)
        except (KeyError, TypeError):  # a missing or None value: the absolute items count it (E-9)
            passed = False
        rows.append({"key": f"d8|{run['id']}", "pass": passed, "error": has_error(run),
                     **{name: run.get(name) for name in D8_RAW_FIELDS}})
    return rows


def _ps7_rows(doc: list) -> list[dict]:
    return [{"key": f"ps7|{row['key']}" if not str(row["key"]).startswith("ps7|") else row["key"],
             "pass": bool(row.get("pass")) and "error" not in row, "error": has_error(row),
             "controller_tag": row.get("controller_tag"), "touch_creep_latch": row.get("touch_creep_latch")}
            for row in doc]


def _g8_rows(lines: list[dict]) -> list[dict]:
    rows = []
    for line in lines:
        faults = [str(name) for name in line.get("warn_fault") or [] if str(name).startswith("FAULT")]
        rows.append({"key": f"{line['tag']}|{line['key']}", "pass": bool(line.get("pass")) and not line.get("error"),
                     "ready": str(line.get("final")).lower() == "ready", "faults": faults,
                     "error": has_error(line), "controller_tag": line.get("controller_tag"),
                     "touch_creep_latch": line.get("touch_creep_latch")})
    return rows


def rows_of(bundle: str, part: str, doc) -> list[dict]:
    """Flat rows of one source (module docstring table)."""
    if bundle == "grid":
        return _event_rows(doc, part)
    if bundle == "soil":
        return _event_rows(doc, part, keep=lambda key: key[0].endswith("|two"))
    if bundle == "regression":
        if part == "clip_A":
            return _event_rows(doc, part)
        if part == "clip_r79_L1L2":
            return _r79_rows(doc, part, l2_without_s1_front=False)
        return _flat_rows(doc, part)
    if bundle == "d8":
        return _d8_rows(doc)
    if bundle == "noise_L2":
        return _r79_rows(doc, part, l2_without_s1_front=True)
    if bundle == "ps7":
        return _ps7_rows(doc)
    if bundle == "g8_safe_stop":
        return _g8_rows(doc)
    raise InputError(f"unknown bundle {bundle!r}")


# ------------------------------------------------------------------------------- bundle meta
def r79_judgement_record(doc: dict) -> dict:
    """``unmatched`` / ``errors`` counts and the ``reference`` group ``all`` ``false_loc`` (None when absent)."""
    reference_all = [row for row in doc.get("reference") or [] if row.get("group") == "all"]
    return {"unmatched": len(doc["unmatched"]) if isinstance(doc.get("unmatched"), list) else None,
            "errors": len(doc["errors"]) if isinstance(doc.get("errors"), list) else None,
            "reference_all_false_loc": reference_all[0].get("false_loc") if len(reference_all) == 1 else None,
            "unmatched_keys": list(doc.get("unmatched") or [])[:20]}


def settings_record(run_doc: dict) -> dict:
    """``results[].controller_settings`` vs ``meta.preset_settings`` (rev4 1 (b) judges the SGS keys
    ``lift_stroke_guard.*`` only): mismatching rows over the SGS keys, and as a record over all keys and without
    the level keys (:data:`SETTINGS_LEVEL_KEYS`); rows without settings or without SGS keys are missing."""
    preset = (run_doc.get("meta") or {}).get("preset_settings")
    record = {"results": len(run_doc.get("results") or []), "preset_settings": preset is not None,
              "preset_sgs_keys": sorted(k for k in preset or {} if k.startswith(SGS_SETTINGS_PREFIX)),
              "missing": 0, "rows_without_sgs_keys": 0, "mismatch_sgs": 0, "mismatch_all": 0,
              "mismatch_excluding_level_keys": 0, "differing_keys": {}}
    if preset is None:
        return record
    for result in run_doc.get("results") or []:
        settings = result.get("controller_settings")
        if not isinstance(settings, dict):
            record["missing"] += 1
            continue
        record["rows_without_sgs_keys"] += not any(k.startswith(SGS_SETTINGS_PREFIX) for k in settings)
        differing = sorted(key for key in set(settings) | set(preset) if settings.get(key) != preset.get(key))
        record["mismatch_all"] += bool(differing)
        record["mismatch_excluding_level_keys"] += any(key not in SETTINGS_LEVEL_KEYS for key in differing)
        record["mismatch_sgs"] += any(key.startswith(SGS_SETTINGS_PREFIX) for key in differing)
        for key in differing:
            record["differing_keys"][key] = record["differing_keys"].get(key, 0) + 1
    return record


def regression_keys(docs: dict[str, object]) -> dict:
    """Rev2 2 judged / record key lists (``prelaunch/regression_keys.keys``, the same key function) of the
    regression outputs: ``<file>:<row key>``, sorted, sha256 over the LF-joined list."""
    judged = []
    for name in ("clip_harness.json", "clip_p0.json"):
        judged += [f"{name}:{r['id']}" for r in docs[name]["records"]]
    for name in ("clip_x426_C.json", "clip_x426_D.json"):
        judged += [f"{name}:{r.get('key', r.get('id', r.get('case_id')))}" for r in docs[name]["results"]]
    for result in docs["clip_A.json"]["results"]:
        judged += [f"clip_A.json:{result['key']}#{i}" for i in range(len(result["runs"]))]
    judged_r79 = {r["key"] for r in docs["clip_r79_L1L2_judgement.json"]["runs"]}
    judged += [f"clip_r79_L1L2_judgement.json:{key}" for key in judged_r79]
    record = [f"clip_r79_L1L2.json:{r['key']}|{r.get('level')}" for r in docs["clip_r79_L1L2.json"]["results"]
              if r["key"] not in judged_r79]
    record += [f"clip_r79_L3L4.json:{r['key']}|{r.get('level')}" for r in docs["clip_r79_L3L4.json"]["results"]]
    judged, record = sorted(set(judged)), sorted(set(record))

    def digest(items: list[str]) -> str:
        return hashlib.sha256("\n".join(items).encode("utf-8")).hexdigest()

    return {"judged_n": len(judged), "judged_sha256": digest(judged), "record_n": len(record),
            "record_sha256": digest(record)}


def _sidecar_record(path: Path) -> dict:
    if not path.is_file():
        return {"path": str(path), "exists": False, "rc": None}
    doc = _load(path)
    env = doc.get("env") or {}
    return {"path": str(path), "exists": True, "rc": doc.get("rc"),
            **{name: env.get(name) for name in SIDECAR_ENV_KEYS},
            "git_start_head": (doc.get("git_start") or {}).get("head"),
            "git_end_head": (doc.get("git_end") or {}).get("head")}


def _provenance_record(arm_dir: Path, step: Step, outputs: dict[str, object]) -> dict | None:
    if step.provenance is None:
        return None
    if step.provenance.startswith("output:"):
        part = step.provenance.split(":", 1)[1]
        meta = (outputs.get(part) or {}).get("meta") if isinstance(outputs.get(part), dict) else None
        source, doc = f"output {part} meta", meta
    else:
        path = arm_dir / "provenance" / f"{step.name}.json"
        source, doc = str(path), (_load(path) if path.is_file() else None)
    if not isinstance(doc, dict):
        return {"source": source, "exists": False}
    return {"source": source, "exists": True, **{key: doc.get(key) for key in PROVENANCE_KEYS},
            "missing_keys": [key for key in PROVENANCE_KEYS if key not in doc]}


def step_records(arm_dir: Path, bundle: str, outputs: dict[str, object]) -> list[dict]:
    """Sidecar, provenance and event evidence of every step of a bundle (missing files recorded as missing)."""
    records = []
    for step in STEPS[bundle]:
        events = None
        if step.events_part is not None and step.events_part in outputs:
            events = event_record(outputs[step.events_part], step.events_part)
        records.append({"step": step.name,
                        "sidecar": _sidecar_record(arm_dir / f"{step.name}.launch.json"),
                        "provenance": _provenance_record(arm_dir, step, outputs),
                        "events": events})
    return records


def _canonical_name(bundle: str, part: str) -> str:
    table = SOURCES[bundle] if part in SOURCES[bundle] else RAW_SOURCES[bundle]
    return table[part][0]


def bundle_meta_extra(bundle: str, outputs: dict[str, object]) -> dict:
    """Bundle-level raw fields of the rev2 1 absolute items (regression / noise)."""
    if bundle == "regression":
        by_file_name = {_canonical_name(bundle, part): doc for part, doc in outputs.items()}
        return {"r79_judgement": r79_judgement_record(outputs["clip_r79_L1L2"]),
                "regression_keys": regression_keys(by_file_name)}
    if bundle == "noise_L2":
        return {"r79_judgement": r79_judgement_record(outputs["r79_L1L2"]),
                "settings": settings_record(outputs["r79_L1L2_run"]),
                "raw_run_errors": error_rows(outputs["r79_L1L2_run"])}
    return {}


# ------------------------------------------------------------------------------- r79 judge
def run_r79_judge(judgement: Path, checkout: Path) -> None:
    """``acc_judge.r79_judge``: the checkout's ``r79_sensor_judge.py judge <out> <run>`` with this interpreter."""
    run_file = judgement.with_name(R79_RUN_OF_JUDGEMENT[judgement.name])
    if not run_file.is_file():
        raise InputError(f"no r79 run file {run_file} for {judgement.name}")
    script = checkout / "04_scripts" / "03_control" / "s8" / "r79_sensor_judge.py"
    done = subprocess.run([sys.executable, "-I", "-B", str(script), "judge", str(judgement), str(run_file)],
                          capture_output=True, text=True, timeout=1800, check=False)
    if done.returncode:
        raise InputError(f"r79 judge failed for {run_file}: {done.stderr[-800:]}")


def _r79_judge_command(arm_dir: Path, bundle: str, checkout: Path) -> str:
    name = SOURCES[bundle]["clip_r79_L1L2" if bundle == "regression" else "r79_L1L2"][0]
    run_name = R79_RUN_OF_JUDGEMENT[name]
    return (f"<python> -I -B {checkout / '04_scripts/03_control/s8/r79_sensor_judge.py'} judge "
            f"{arm_dir / name} {arm_dir / run_name}")


# ------------------------------------------------------------------------------- CLI
def _read_bundle(arm_dir: Path, bundle: str, overrides: dict[str, Path], *, checkout: Path,
                 run_judge: bool) -> tuple[dict[str, object], dict[str, Path]]:
    outputs, paths = {}, {}
    for part in SOURCES[bundle]:
        path = locate(arm_dir, bundle, part, overrides)
        if path is None and run_judge and part in ("clip_r79_L1L2", "r79_L1L2"):
            path = arm_dir / SOURCES[bundle][part][0]
            run_r79_judge(path, checkout)
        if path is None:
            hint = (f" (run {_r79_judge_command(arm_dir, bundle, checkout)})"
                    if part in ("clip_r79_L1L2", "r79_L1L2") else "")
            raise InputError(f"{bundle}:{part}: no {SOURCES[bundle][part]} in {arm_dir}{hint}")
        outputs[part], paths[part] = _load(path), path
    for part in RAW_SOURCES.get(bundle, {}):
        path = locate(arm_dir, bundle, part, overrides, RAW_SOURCES)
        if path is None:
            raise InputError(f"{bundle}:{part}: no {RAW_SOURCES[bundle][part]} in {arm_dir}")
        outputs[part], paths[part] = _load(path), path
    return outputs, paths


def flatten(arm_dir: Path, out_dir: Path, overrides: dict[str, Path], *, checkout: Path,
            bundles: list[str], run_judge: bool) -> dict:
    summary = {"arm_dir": str(arm_dir), "bundles": {}}
    for bundle in bundles:
        outputs, paths = _read_bundle(arm_dir, bundle, overrides, checkout=checkout, run_judge=run_judge)
        rows, sources = [], {}
        for part in SOURCES[bundle]:
            part_rows = rows_of(bundle, part, outputs[part])
            sources[part] = {"path": str(paths[part]), "sha256": _sha256(paths[part]), "rows": len(part_rows),
                             "error_rows": error_rows(outputs[part])}
            rows += [{**row, "part": part} for row in part_rows]
        for part in RAW_SOURCES.get(bundle, {}):
            sources[part] = {"path": str(paths[part]), "sha256": _sha256(paths[part]), "rows": 0,
                             "error_rows": error_rows(outputs[part]), "raw_only": True}
        keys = [row["key"] for row in rows]
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        if duplicates:
            raise InputError(f"{bundle}: duplicate keys {duplicates[:5]}")
        target = out_dir / f"{bundle}.json"
        meta = {"tool": "k2_v5_flatten", "bundle": bundle, "arm_dir": str(arm_dir), "sources": sources,
                "rows": len(rows), "failed": sum(not row["pass"] for row in rows),
                "steps": step_records(arm_dir, bundle, outputs), **bundle_meta_extra(bundle, outputs)}
        target.write_text(json.dumps({"meta": meta, "runs": rows}, indent=1), encoding="utf-8")
        summary["bundles"][bundle] = {"file": str(target), "rows": len(rows), "failed": meta["failed"]}
    (out_dir / "flatten_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def _overrides(items: list[str]) -> dict[str, Path]:
    out = {}
    for item in items:
        name, _, path = item.partition("=")
        bundle, _, part = name.partition(":")
        known = part in SOURCES.get(bundle, {}) or part in RAW_SOURCES.get(bundle, {})
        if not path or not known:
            raise InputError(f"--source {item!r}: expected <bundle>:<part>=<file>")
        out[name] = Path(path)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--arm-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--checkout", type=Path, default=ROOT, help="checkout of r79_sensor_judge.py")
    parser.add_argument("--source", action="append", default=[], help="<bundle>:<part>=<file> override")
    parser.add_argument("--bundles", default=",".join(SOURCES), help="comma list (default all)")
    parser.add_argument("--run-r79-judge", action="store_true",
                        help="run r79_sensor_judge for a missing r79 judgement (acc_judge.r79_judge)")
    args = parser.parse_args(argv)
    try:
        bundles = [name for name in args.bundles.split(",") if name]
        unknown = sorted(set(bundles) - set(SOURCES))
        if unknown:
            raise InputError(f"--bundles: unknown {unknown}")
        targets = [args.out_dir / f"{bundle}.json" for bundle in bundles]
        existing = [str(path) for path in targets if path.exists()]
        if existing:
            raise InputError(f"outputs exist (new files only): {existing}")
        args.out_dir.mkdir(parents=True, exist_ok=True)
        summary = flatten(args.arm_dir, args.out_dir, _overrides(args.source), checkout=args.checkout,
                          bundles=bundles, run_judge=args.run_r79_judge)
    except InputError as exc:
        print(json.dumps({"exit": EXIT_INPUT, "error": str(exc)}))
        return EXIT_INPUT
    except Exception as exc:  # contract: internal error = exit 3 with the traceback
        print(traceback.format_exc()[-3000:], file=sys.stderr)
        print(json.dumps({"exit": EXIT_INTERNAL, "error": repr(exc)}))
        return EXIT_INTERNAL
    print(json.dumps({"exit": EXIT_WRITTEN, "bundles": {k: v["rows"] for k, v in summary["bundles"].items()}}))
    return EXIT_WRITTEN


if __name__ == "__main__":
    sys.exit(main())
