"""436.9 edition 6 key lists fixed before the seal (``jp3_remedy_spec_v6.md`` 6.2 / 6.3,
revision 9 G-6, spec 8 Y-8).

Three files in ``--out-dir`` (``06_analysis/02_control/j_p3_cause/ed6_design/keys/``; an
existing file is never overwritten):

* ``sens_keys.json`` (6.2 sensitivity rows): ``VBLc005``, ``VBLc04``, ``VBLv05``, ``VBLv15`` x
  the subset R12 4 phases + G4 :data:`SENS_G4_TWINS` (7 twins x the 2 G4 offsets) + R14 + R15
  + R16 + S1 + S4 + S5 + S7 + R2ra (the ``run_v5`` phases of each row); a line the probe
  1bd405c8 covers (``d0_plant_split.D0_KEYS``) is marked ``probe_seen`` (32 units: a stop
  condition only, never judged evidence).
* ``confirm_a_keys.json`` (6.3 (가)): the same four settings x the j9_main required rows
  outside the subset (the other G4 twins, S8, R2, R7); no probe key is among them.
* ``confirm_b_grid192.json`` (6.3 (나)): setting ``VBL`` x the 192 grid rows of stats
  ``ed6_design/stats_v6/s50_grid_sample.csv`` (seed 20261123, one offset per cluster; its
  sha256 is checked), each an R12 event job with the stored row's twin (level, leg, F_s,
  event, timing, offset), and the stored V0 grid row as its pair.

Every line: the ``run_v5`` job, the V0 pair (sensitivity / (가): the V0 job of the ``main``
batch; (나): the stored grid file, key, run index and V0 command hash), ``head_only_declared``
(the case table's path: steady = head only, event = not), and per file the generation command,
the expected line count and the expected J-P3 judged rows (lines not declared head only; every
setting here is ③ revision 6).

Exit 0 = written, 2 = input error (an output exists, the s50 file is not the fixed one, a V0
pair is missing), 3 = tool error. The stdout's last line is JSON with ``status`` and the counts.

Usage (dynamics-dev or Chrono-dev, the code checkout root):
  python -I -B 04_scripts/04_hydraulic/coupled/ed6_key_lists.py --out-dir <keys folder>
      --grid-sample <s50_grid_sample.csv> --grid-sample-sha256 <sha>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import d0_plant_split as d0  # noqa: E402  (imports run_v5)
import run_v5  # noqa: E402

EXIT_WRITTEN, EXIT_INPUT, EXIT_TOOL = 0, 2, 3
SENS_ROWS = ("R12", "R14", "R15", "R16", "S1", "S4", "S5", "S7", "R2ra")
SENS_G4_TWINS = (("top", "FL", 8.0), ("bottom", "FL", 4.0), ("top", "FR", 4.0),
                 ("top", "RL", 4.0), ("top", "RR", 4.0), ("bottom", "RR", 4.0),
                 ("top", "FL", 0.0))
"""The 7 G4 width-grid twins of the subset (stats s40 frame: 7 keys x 2 offsets). The first
three are the probe keys; the other four (PROVISIONAL, a python-expert proposal for the
stats / control decision): the two rear legs at the top with F_s 4, the rear bottom twin, and
the FL top twin with F_s 0, so every leg, both levels and F_s 0 / 4 / 8 are in."""
GRID_SAMPLE_COLUMNS = ("level", "fs_kN", "timing", "leg", "event", "offset_s", "file", "key",
                       "run_id", "v0_commands_sha256", "v0_pass")
GRID_SETTING = "VBL"
GRID_FILE_ROOT = "06_analysis/02_control/touch_phase/acceptance/c4g2_only/grid"
OUTPUTS = ("sens_keys.json", "confirm_a_keys.json", "confirm_b_grid192.json")
EXPECTED = {"sens_keys.json": (184, 104), "confirm_a_keys.json": (104, 56),
            "confirm_b_grid192.json": (192, 192)}
"""(lines, J-P3 judged rows) the spec counts give; the tool stops when its lists differ."""


class InputError(Exception):
    """No output is written (exit 2)."""


def code_identity() -> dict:
    """HEAD and cleanliness of the checkout this script runs from (a git failure stops)."""
    repo = HERE.parents[2]

    def git(*args: str) -> str:
        done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                              timeout=120, check=False)
        if done.returncode != 0:
            raise InputError(f"git {args[0]} failed: {done.stderr.strip()}")
        return done.stdout.strip()

    head = git("rev-parse", "HEAD")
    if not head:
        raise InputError("git rev-parse gave no HEAD")
    return {"checkout": str(repo), "head": head, "is_clean": git("status", "--porcelain") == ""}


def _row_name(job: dict) -> str:
    return "R2ra" if job.get("decision") == "reanchor_on" else job["case"]


def _twin_key(job: dict) -> tuple | None:
    twin = job.get("twin")
    return None if twin is None else (twin["level"], twin["leg"], float(twin["fs_kN"]))


def is_sens_row(job: dict) -> bool:
    """A required row of the 6.2 subset (module docstring)."""
    if job.get("twin"):
        return _twin_key(job) in SENS_G4_TWINS
    return _row_name(job) in SENS_ROWS


def is_head_only(job: dict) -> bool:
    """The case table's path: a steady row is declared head only (``verdict_runs.execute``)."""
    case, _ = run_v5._case_of(job)
    return case.path != "event"


def _probe_keys() -> set[str]:
    return set(d0.D0_KEYS)


def _v0_keys() -> set[str]:
    return {run_v5.job_key(job) for job in run_v5.batch_jobs("main") if job["setting"] == "V0"}


def required_lines(selector, settings: tuple[str, ...]) -> list[dict]:
    """Every (setting, required row) the selector keeps, with its V0 pair and declarations."""
    v0_keys, probe = _v0_keys(), _probe_keys()
    lines = []
    for setting in settings:
        for row in run_v5.required_rows():
            if not selector(row):
                continue
            job = {**row, "setting": setting}
            v0_job = {**row, "setting": "V0"}
            if run_v5.job_key(v0_job) not in v0_keys:
                raise InputError(f"no V0 job of the main batch for {row}")
            key = d0.key_name(job)
            lines.append({"job": job, "key": key, "v0_pair": {"job": v0_job,
                                                              "source": "v5/main.jsonl V0"},
                          "head_only_declared": is_head_only(job),
                          "probe_seen": key in probe})
    return lines


def grid_lines(path: Path) -> list[dict]:
    """The 192 grid rows of the stats sample as ``VBL`` event jobs."""
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    missing = [name for name in GRID_SAMPLE_COLUMNS if rows and name not in rows[0]]
    if missing:
        raise InputError(f"grid sample columns {missing} missing")
    lines = []
    for row in rows:
        twin = {"level": row["level"], "leg": row["leg"], "fs_kN": float(row["fs_kN"]),
                "event": row["event"], "timing": row["timing"]}
        job = {"case": "R12", "eps": 0.0, "offset_s": float(row["offset_s"]), "twin": twin,
               "setting": GRID_SETTING}
        lines.append({"job": job, "t4h_file": run_v5.t4h_file_name(job),
                      "v0_pair": {"file": f"{GRID_FILE_ROOT}/{row['file']}", "key": row["key"],
                                  "run_id": int(row["run_id"]),
                                  "v0_commands_sha256": row["v0_commands_sha256"],
                                  "v0_pass": row["v0_pass"] == "True"},
                          "head_only_declared": is_head_only(job)})
    names = [line["t4h_file"] for line in lines]
    if len(set(names)) != len(names):
        raise InputError("two grid lines share a T4h file name")
    return lines


def _document(lines: list[dict], name: str, command: str, extra: dict) -> dict:
    judged = sum(not line["head_only_declared"] for line in lines)
    expected_lines, expected_judged = EXPECTED[name]
    if (len(lines), judged) != (expected_lines, expected_judged):
        raise InputError(f"{name}: {len(lines)} lines / {judged} judged rows, expected "
                         f"{expected_lines} / {expected_judged}")
    return {"rule": "jp3_remedy_spec_v6.md 6.2 / 6.3 (revision 9 G-6, spec 8 Y-8)",
            "generation_command": command, **extra,
            "expected_lines": len(lines), "expected_j_p3_judged_rows": judged,
            "head_only_declared_lines": len(lines) - judged, "lines": lines}


def build(grid_sample: Path, grid_sha256: str, command: str) -> dict[str, dict]:
    identity = {"code_identity": code_identity()}
    if hashlib.sha256(grid_sample.read_bytes()).hexdigest() != grid_sha256:
        raise InputError(f"--grid-sample {grid_sample} is not of the given sha256")
    sens_settings = run_v5.ED6_SENSITIVITY_SETTINGS
    sens = required_lines(is_sens_row, sens_settings)
    confirm_a = required_lines(lambda job: not is_sens_row(job), sens_settings)
    if any(line["probe_seen"] for line in confirm_a):
        raise InputError("a probe key is outside the sensitivity subset")
    grid = grid_lines(grid_sample)
    common = {**identity, "settings": list(sens_settings)}
    return {
        "sens_keys.json": _document(sens, "sens_keys.json", command, {
            **common, "subset": {"rows": list(SENS_ROWS),
                                 "g4_twins": [list(twin) for twin in SENS_G4_TWINS],
                                 "g4_twin_choice": "provisional (module docstring)"},
            "probe_seen_units": sum(line["probe_seen"] for line in sens),
            "probe_source": "j9_runs/1bd405c8/ed6_probe_a1/ed6_probe.jsonl (D0 8 keys)"}),
        "confirm_a_keys.json": _document(confirm_a, "confirm_a_keys.json", command, {
            **common, "rows": "run_v5.required_rows() outside the sens_keys subset"}),
        "confirm_b_grid192.json": _document(grid, "confirm_b_grid192.json", command, {
            **identity, "settings": [GRID_SETTING], "grid_sample": {"path": str(grid_sample),
                                                        "sha256": grid_sha256},
            "extraction": "stats s50: one offset per (level, F_s, timing, leg, event) cluster, "
                          "numpy default_rng(20261123), among the V0-passing offsets",
            "seed": 20261123,
            "v0_pass_lines": sum(line["v0_pair"]["v0_pass"] for line in grid)}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--grid-sample", type=Path, required=True)
    parser.add_argument("--grid-sample-sha256", required=True)
    args = parser.parse_args(argv)
    command = ("python -I -B 04_scripts/04_hydraulic/coupled/ed6_key_lists.py --out-dir "
               f"{args.out_dir} --grid-sample {args.grid_sample} --grid-sample-sha256 "
               f"{args.grid_sample_sha256}")
    try:
        if any((args.out_dir / name).exists() for name in OUTPUTS):
            raise InputError("an output exists (never overwritten)")
        documents = build(args.grid_sample, args.grid_sample_sha256, command)
    except InputError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}))
        return EXIT_INPUT
    except Exception:  # every unexpected failure is a tool error (exit 3)
        traceback.print_exc()
        print(json.dumps({"status": "tool_error"}))
        return EXIT_TOOL
    args.out_dir.mkdir(parents=True, exist_ok=True)
    shas = {}
    for name, document in documents.items():
        data = (json.dumps(document, indent=1) + "\n").encode("utf-8")
        with (args.out_dir / name).open("xb") as handle:
            handle.write(data)
        shas[name] = hashlib.sha256(data).hexdigest()
    print(json.dumps({"status": "written", "sha256": shas,
                      "lines": {name: doc["expected_lines"] for name, doc in documents.items()}}))
    return EXIT_WRITTEN


if __name__ == "__main__":
    sys.exit(main())
