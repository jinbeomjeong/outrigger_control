"""Edition 8 records and probe on the reduced harness (dynamics-dev subprocesses;
``ed7_j9fail_8a2a52ce/cause_analysis.md`` 8 P-1 .. P-3).

Command invariance: the P-1 / P-2 records and the probe driver leave the commands of the
edition 7 run commit C (8a2a52ce). Every expected hash below is the ``commands_sha256`` of the
stored line of the same job (read on 2026-11-26):

* V0 / VB: ``06_analysis/03_hydraulic/coupled/v5/main.jsonl`` (sha256 9ad74990...);
* VBM / LSM4 / VBMslow / VBM0 / P7-M-a2: the C outputs ``j_p3_cause/j9_runs/8a2a52ce/``
  (``j9main_a1/j9_main.jsonl``, ``sens_a1/sens.jsonl``, ``impl_t8_a1/ed7_t8.jsonl``,
  ``impl_probe_a1/ed7_probe_a2.jsonl``).

With the record switch off (``run_v5`` lines) a line has no edition 8 key; the probe lines
(switch on) of arm a2 on M / LSM4 / Mslow command exactly as the stored VBM / LSM4 / VBMslow
lines, and carry the records on every line kind the probe writes: event rows (R12, R16 with an
offset), the steady row (head-only declared: S8), the LS plant, a jobs-file row and the new arm
a2w. An error line carries no record (``run_v5.run_one`` returns before the copy).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled"
for _path in (COUPLED_DIR, PROJECT_ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
CHECK_RUNNER = Path(__file__).resolve().with_name("ed7_check_runner.py")
ED7_PROBE = COUPLED_DIR / "ed7_probe.py"
ED8_PROBE = COUPLED_DIR / "ed8_probe.py"
TIMEOUT_S = 2400

R12_FL_FS8 = {"case": "R12", "eps": 0.0, "offset_s": 0.0,
              "twin": {"level": "top", "leg": "FL", "fs_kN": 8.0}}
R12_FR_FS0_O005 = {"case": "R12", "eps": 0.0, "offset_s": 0.05,
                   "twin": {"level": "top", "leg": "FR", "fs_kN": 0.0}}
S8 = {"case": "S8", "eps": 0.0}
R16_O0075 = {"case": "R16", "eps": 0.0, "offset_s": 0.075}
STORED = {
    "V0_S8": ({**S8, "setting": "V0"},
              "67c4494db8cb060c399dc4ae06a733392f2f3863f3077f8508e66978cfe08363"),
    "VB_R10": ({"case": "R10", "eps": 0.002, "setting": "VB"},
               "3c0a2db2be99f4251367a60acca3e3bc7bae5a3d54d5d2efab51821b69e70efc"),
    "VBM_S8": ({**S8, "setting": "VBM"},
               "09d2c9884f85243769c7816516108784430423c7972193540acacb99b9073ff3"),
    "VBM_R12_FLFs8": ({**R12_FL_FS8, "setting": "VBM"},
                      "906bcf42b4fdd781260150c4af936dc13d237e16bccaacdea0aae87a6b2e8886"),
    "VBM0_S2": ({"case": "S2", "eps": 0.002, "setting": "VBM0"},
                "4bfb268428bc824e0884b3d607328b409975aede155d979ac91af0de04ad0c25"),
    "LSM4_R12_FRFs0": ({**R12_FR_FS0_O005, "setting": "LSM4"},
                       "e5aec722503bb3653021257c3363456d2d817c4c8347f911be0673c43d2293b9"),
    "VBMslow_R16": ({**R16_O0075, "setting": "VBMslow"},
                    "d87037c6bed576b0c2850edbad8ef213e6a9fa3c8a4c30155e4b3ac8d2e7c327"),
}
"""(job, the stored ``commands_sha256``) of the switch-off runs."""
P7_M_A2_R2 = "f329c5ef1cae6120b46d775ac3fa415be0b91803e8f388239bc5b513cb23300e"
"""``impl_probe_a1/ed7_probe_a2.jsonl`` P7-M-a2 R2 eps 0.003 (``ed7_probe.py`` unchanged)."""
PROBE_EXPECTED = {
    ("P8-M-a2", "R12_top-FL-Fs8-o0.0"): STORED["VBM_R12_FLFs8"][1],
    ("P8-M-a2", "S8_e0.0"): STORED["VBM_S8"][1],
    ("P8-LSM4-a2", "R12_top-FR-Fs0-o0.05"): STORED["LSM4_R12_FRFs0"][1],
    ("P8-Mslow-a2", "R16_o0.075"): STORED["VBMslow_R16"][1],
}
"""Probe lines of arm a2 and the stored line of the same row and plant."""
PROBE_RUNS = {
    "m": ("--part", "j9main", "--plants", "M", "--arms", "a2,a2w",
          "--keys", "R12_top-FL-Fs8-o0.0,S8_e0.0", "--workers", "4"),
    "lsm4": ("--part", "j9main", "--plants", "LSM4", "--arms", "a2",
             "--keys", "R12_top-FR-Fs0-o0.05", "--workers", "1"),
    "file": ("--part", "file", "--arms", "a2", "--workers", "1"),
}
ED8_LINE_KEYS = {"probe_stiffness_record", "ib_block_record"}
STIFFNESS_WARNING = "WARN_PROBE_STIFFNESS_OUT_OF_RANGE"


def _environment() -> dict:
    return {**os.environ, "MKL_THREADING_LAYER": "TBB", "PYTHONDONTWRITEBYTECODE": "1"}


def _needs_harness() -> None:
    if not HARNESS_PYTHON.exists():
        pytest.skip("dynamics-dev missing")


def _start(command: list[str], folder: Path) -> subprocess.Popen:
    folder.mkdir(parents=True, exist_ok=True)
    log = (folder / "log.txt").open("w", encoding="utf-8")
    return subprocess.Popen([str(HARNESS_PYTHON), "-I", "-B", *command], cwd=folder,
                            env=_environment(), stdout=log, stderr=subprocess.STDOUT)


def _lines(path: Path) -> list[dict]:
    return [json.loads(text) for text in path.read_text(encoding="utf-8").splitlines()]


def _key(job: dict) -> str:
    """``d0_plant_split.key_name`` of a job (the T4h stem without the setting)."""
    import d0_plant_split

    return d0_plant_split.key_name(job)


@pytest.fixture(scope="module")
def harness(tmp_path_factory) -> dict:
    """Every harness run at once, each from its own working folder (not the checkout)."""
    _needs_harness()
    root = tmp_path_factory.mktemp("ed8")
    rows_file = root / "rows.json"
    rows_file.write_text(json.dumps([{**R16_O0075, "setting": "VBMslow"}]), encoding="utf-8")
    processes = {name: _start([str(CHECK_RUNNER), json.dumps(job), str(root / name / "t4h"),
                               str(root / name / "report.json")], root / name)
                 for name, (job, _) in STORED.items()}
    processes["ed7_probe"] = _start(
        [str(ED7_PROBE), "--out", str(root / "ed7" / "probe.jsonl"), "--plants", "M",
         "--arms", "a2", "--keys", "R2_e0.003", "--part", "main", "--workers", "1"],
        root / "ed7_work")
    for name, arguments in PROBE_RUNS.items():
        extra = ("--jobs-file", str(rows_file)) if name == "file" else ()
        processes[f"probe_{name}"] = _start(
            [str(ED8_PROBE), "--out", str(root / "probe" / f"{name}.jsonl"), *arguments,
             *extra], root / f"probe_{name}_work")
    for process in processes.values():
        process.wait(timeout=TIMEOUT_S)
    exits = {name: process.returncode for name, process in processes.items()}
    reports = {name: json.loads((root / name / "report.json").read_text(encoding="utf-8"))
               for name in STORED if exits[name] == 0}
    probe_lines = []
    for name in PROBE_RUNS:
        path = root / "probe" / f"{name}.jsonl"
        probe_lines += _lines(path) if path.exists() else []
    return {"root": root, "exits": exits, "reports": reports, "probe_lines": probe_lines}


@pytest.mark.slow
def test_every_run_ended_without_error(harness) -> None:
    assert harness["exits"] == dict.fromkeys(harness["exits"], 0), harness["exits"]


@pytest.mark.slow
def test_switch_off_runs_keep_the_stored_hashes_and_keys(harness) -> None:
    for name, (_, stored) in STORED.items():
        report = harness["reports"][name]
        assert report["hash"] == stored, name
        assert not ED8_LINE_KEYS & set(report["line_keys"]), name
        assert report["foreign_modules"] == [], name
        if report["t4h"]["arrays"] is None:  # V0 writes no T4h record
            assert name == "V0_S8"
            continue
        assert not ED8_LINE_KEYS & set(report["t4h"]["meta_keys"]), name
        assert "lsb_ib_block" not in report["t4h"]["arrays"], name


@pytest.mark.slow
def test_ed7_probe_keeps_its_stored_hash(harness) -> None:
    (line,) = _lines(harness["root"] / "ed7" / "probe.jsonl")
    assert line["commands_sha256"] == P7_M_A2_R2
    assert not ED8_LINE_KEYS & set(line)


@pytest.mark.slow
def test_probe_a2_lines_command_as_the_stored_lines(harness) -> None:
    by_key = {(line["job"]["setting"], _key(line["job"])): line
              for line in harness["probe_lines"]}
    assert set(PROBE_EXPECTED) <= set(by_key), sorted(by_key)
    for key, stored in PROBE_EXPECTED.items():
        assert by_key[key]["commands_sha256"] == stored, key
    a2w = by_key[("P8-M-a2w", "R12_top-FL-Fs8-o0.0")]
    assert a2w["probe_d6_settings"]["witness"] is True
    assert a2w["probe_d6_settings"]["retract_position_target"] is False
    assert a2w["commands_sha256"] != STORED["VBM_R12_FLFs8"][1]  # (i-b) off acts


@pytest.mark.slow
def test_probe_lines_of_every_kind_carry_the_records(harness) -> None:
    lines = harness["probe_lines"]
    assert len(lines) == 6 and not any("error" in line for line in lines)
    kinds = {(line["head_only_declared"], line["ed8_probe"]["plant"], line["ed8_probe"]["arm"])
             for line in lines}
    assert {(False, "M", "a2"), (True, "M", "a2"), (False, "LSM4", "a2"), (False, "Mslow", "a2"),
            (False, "M", "a2w"), (True, "M", "a2w")} == kinds  # S8 = the steady (head-only) row
    for line in lines:
        name = (line["job"]["setting"], _key(line["job"]))
        block = line["ed8_probe"]
        assert block["ed8_record"] is True and block["p1_read_record"] is True, name
        assert block["foreign_modules"] == [], name
        assert block["part"] == ("file" if block["plant"] == "Mslow" else "j9main"), name
        rounds = line["probe_stiffness_record"]  # a list on every line, empty without a round
        assert isinstance(rounds, list), name
        assert bool(rounds) == (not line["head_only_declared"]), name  # S8 has no probe round
        assert [entry["round"] for entry in rounds] == sorted(
            entry["round"] for entry in rounds), name
        for entry in rounds:
            assert set(entry["legs"]) == {"FL", "FR", "RL", "RR"}, name
        _check_warnings(line, name)
        _check_block_record(line, name)


def _check_warnings(line: dict, name) -> None:
    """Every warned round is the WARN event of its time and ratio, and the other way round."""
    warned = sorted((round(entry["t_s"], 3), f"{STIFFNESS_WARNING}:{entry['raw_ratio']:.3f}")
                    for entry in line["probe_stiffness_record"] if entry["is_warned"])
    events = sorted((round(t, 3), event) for t, event in line["events"]
                    if event.startswith(STIFFNESS_WARNING))
    assert warned == events, name


def _check_block_record(line: dict, name) -> None:
    """The per-leg counts are the sum of the stretches and of the T4h codes."""
    record = line["ib_block_record"]
    assert set(record["codes"]) == {"floor_on", "latched", "condition_1_none",
                                    "condition_1_short", "priority", "condition_2",
                                    "condition_3", "protect", "latch", "trigger"}, name
    for leg, counts in record["legs"].items():
        assert sum(counts.values()) == record["level_periods"], (name, leg)
        from_stretches = Counter()
        for stretch in record["stretches"]:
            from_stretches.update(stretch["legs"][leg])
        assert dict(+from_stretches) == {k: v for k, v in counts.items() if v}, (name, leg)


@pytest.mark.slow
def test_probe_t4h_codes_match_the_line_counts(harness) -> None:
    folder = harness["root"] / "probe"
    for line in harness["probe_lines"]:
        stem = {"Mslow": "file", "LSM4": "lsm4"}.get(line["ed8_probe"]["plant"], "m")
        path = folder / f"{stem}_t4h" / line["t4h_file"]
        with np.load(path, allow_pickle=False) as data:
            meta = json.loads(str(data["meta_json"]))
            codes = data["lsb_ib_block"]
        record = line["ib_block_record"]
        assert meta["ib_block_record"] == record and meta["probe_stiffness_record"] == line[
            "probe_stiffness_record"]
        names = {code: reason for reason, code in record["codes"].items()}
        for leg_index, leg in enumerate(("FL", "FR", "RL", "RR")):
            read = Counter(names[int(code)] for code in codes[:, leg_index] if code >= 0)
            counts = {k: v for k, v in record["legs"][leg].items() if v}
            assert dict(read) == counts, (line["t4h_file"], leg)
