"""Edition 8 implementation on the reduced harness (dynamics-dev subprocesses;
``jp3_remedy_spec_v8_rules.md`` 12 P8-6, 16 Y8-1 .. Y8-10).

* P8-6: the first-round ``K1_sc`` of direction A with the PSW (``ed8_probe`` arm ``a2w_psw``) on
  R12 top-FR-Fs8 o0.0 x {M, Mslow, Mh15, L} and R7 e0.0 x M equals ``a0.05_k1`` of
  ``ed8_design/control_k1_window/k02_legs.csv`` (the offline replay) within 1e-9 relative.
* Producer forms of the edition 8 settings (``run_v5`` lines): an event row (VBN R12
  bottom-FR-Fs0-RE1bF-ready, where H3' acts), a steady head-only row (VBN S8) and a ③-off
  event row (VBN0 R16): the ``_ED8`` tag, the settings and record keys, the R2 witness record
  without its events, the event-output records and the T4h arrays.
"""

from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled"
for _path in (COUPLED_DIR, PROJECT_ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
CHECK_RUNNER = Path(__file__).resolve().with_name("ed8_check_runner.py")
ED8_PROBE = COUPLED_DIR / "ed8_probe.py"
RECORDS_ROOT = Path(os.environ.get("OUTRIGGER_RECORDS_ROOT", str(PROJECT_ROOT)))
K02_LEGS = (RECORDS_ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "ed8_design"
            / "control_k1_window" / "k02_legs.csv")
TIMEOUT_S = 2400
RELATIVE_TOLERANCE = 1e-9

R12_FR_FS8 = {"case": "R12", "eps": 0.0, "offset_s": 0.0,
              "twin": {"level": "top", "leg": "FR", "fs_kN": 8.0}}
P86_ROWS = [{**R12_FR_FS8, "setting": setting} for setting in ("VBM", "VBMslow", "VBMh15", "VBL")]
P86_ROWS.append({"case": "R7", "eps": 0.0, "setting": "VBM"})
"""P8-6 rows by source setting (``ed8_probe`` part ``file``: VBM -> M, VBMslow -> Mslow,
VBMh15 -> Mh15, VBL -> L)."""
PRODUCER_JOBS = {
    "vbn_event": {"case": "R12", "eps": 0.0, "offset_s": 0.0, "setting": "VBN",
                  "twin": {"level": "bottom", "leg": "FR", "fs_kN": 0.0, "event": "RE1bF",
                           "timing": "ready"}},
    "vbn_steady": {"case": "S8", "eps": 0.0, "setting": "VBN"},
    "vbn0_event": {"case": "R16", "eps": 0.0, "offset_s": 0.0, "setting": "VBN0"},
}
ED8_LINE_KEYS = {"probe_stiffness_record", "ib_block_record", "ed8_settings", "ed8_record",
                 "probe_d6_settings", "probe_d6_record", "lsb_record"}


def _environment() -> dict:
    return {**os.environ, "MKL_THREADING_LAYER": "TBB", "PYTHONDONTWRITEBYTECODE": "1"}


def _start(command: list[str], folder: Path) -> subprocess.Popen:
    folder.mkdir(parents=True, exist_ok=True)
    log = (folder / "log.txt").open("w", encoding="utf-8")
    return subprocess.Popen([str(HARNESS_PYTHON), "-I", "-B", *command], cwd=folder,
                            env=_environment(), stdout=log, stderr=subprocess.STDOUT)


@pytest.fixture(scope="module")
def harness(tmp_path_factory) -> dict:
    """Every harness run at once, each from its own working folder (not the checkout)."""
    if not HARNESS_PYTHON.exists():
        pytest.skip("dynamics-dev missing")
    if not K02_LEGS.exists():
        pytest.skip(f"{K02_LEGS} absent (OUTRIGGER_RECORDS_ROOT)")
    root = tmp_path_factory.mktemp("ed8impl")
    rows_file = root / "p86_rows.json"
    rows_file.write_text(json.dumps(P86_ROWS), encoding="utf-8")
    processes = {name: _start([str(CHECK_RUNNER), json.dumps(job), str(root / name / "t4h"),
                               str(root / name / "report.json")], root / name)
                 for name, job in PRODUCER_JOBS.items()}
    processes["p86"] = _start([str(ED8_PROBE), "--out", str(root / "p86" / "p86.jsonl"),
                               "--part", "file", "--jobs-file", str(rows_file),
                               "--arms", "a2w_psw", "--workers", "5"], root / "p86")
    codes = {name: process.wait(timeout=TIMEOUT_S) for name, process in processes.items()}
    reports = {name: json.loads((root / name / "report.json").read_text(encoding="utf-8"))
               for name in PRODUCER_JOBS if codes[name] == 0}
    p86_path = root / "p86" / "p86.jsonl"
    p86 = ([json.loads(text) for text in p86_path.read_text(encoding="utf-8").splitlines()]
           if p86_path.exists() else [])
    logs = {name: (root / name / "log.txt").read_text(encoding="utf-8")[-3000:]
            for name in processes}
    return {"codes": codes, "reports": reports, "p86": p86, "logs": logs}


def test_every_run_ended_without_error(harness) -> None:
    assert harness["codes"] == dict.fromkeys(harness["codes"], 0), harness["logs"]
    assert len(harness["p86"]) == len(P86_ROWS)
    assert not [line for line in harness["p86"] if "error" in line]


def _k02_first_round() -> dict[tuple[str, str], float]:
    """``(run, leg) -> a0.05_k1`` of round 1, direction A rows (NaN for an empty cell)."""
    table = {}
    with K02_LEGS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["run"].endswith("-A") and row["round"] == "1":
                value = row["a0.05_k1"]
                table[(row["run"], row["leg"])] = float(value) if value else math.nan
    return table


def test_p86_first_round_scale_stiffness_equals_the_replay(harness) -> None:
    import d0_plant_split

    expected = _k02_first_round()
    compared = 0
    for line in harness["p86"]:
        plant = line["ed8_probe"]["plant"]
        run = f"{d0_plant_split.key_name(line['job'])}_D8-{plant}-A"
        first = line["probe_stiffness_record"][0]
        assert first["round"] == 1
        for leg, values in first["legs"].items():
            reference = expected[(run, leg)]
            ours = values.get("scale_k_N_m")
            if math.isnan(reference):
                assert ours is None, (run, leg)
                continue
            assert ours is not None, (run, leg)
            assert abs(ours - reference) <= RELATIVE_TOLERANCE * abs(reference), (run, leg)
            compared += 1
    assert compared >= 16


def test_producer_lines_carry_the_edition_8_keys(harness) -> None:
    for name, report in harness["reports"].items():
        line = report["line"]
        assert ED8_LINE_KEYS <= set(line), name
        assert line["controller_tag"].endswith("_ED8"), name
        settings = line["ed8_settings"]
        assert settings["probe_k1_scale_settings"]["scale_mid_min_piston_travel_m"] == 5e-5
        assert settings["r8"]["stiffness_warning_range"] == [0.8, 3.6]
        assert settings["r8"]["lifted_reapproach"]["short_run_s"] == 0.5
        assert settings["twist_completion_relax"]["locked_drift_waiver"] is True
        assert line["probe_d6_settings"]["witness_mode"] == "record"
        names = line.get("event_names") or {}
        assert not [n for n in names if n.startswith(("INFO_D6_NOT_OPENED",
                                                       "WARN_PROBE_RETRACT_NOT_OPENED"))]
        record = line["ed8_record"]
        assert "twist_waiver" in record and "reapproach_runs" in record
        assert "a1_episodes" in line["lsb_record"]
        assert not report["foreign_modules"], name
        arrays = set(report["t4h"]["arrays"])
        assert {"ed8_done_flags", "ed8_held_legs", "lsb_ib_block"} <= arrays, name
        assert report["t4h"]["controller_tag"] == line["controller_tag"]


def test_event_lines_carry_the_handover_records(harness) -> None:
    for name in ("vbn_event", "vbn0_event"):
        line = harness["reports"][name]["line"]
        output = line["event_output"]
        assert {"reapproach_starts", "reapproach_ends", "lift_intervals"} <= set(output), name
        assert set(output["lift_intervals"]) == {"FL", "FR", "RL", "RR"}
        runs = line["ed8_record"]["reapproach_runs"]
        assert all("exit_required_samples" in run for run in runs), name
    steady = harness["reports"]["vbn_steady"]["line"]
    assert steady["head_only_declared"] is True and not steady["event_output"]


def test_probe_rounds_carry_the_psw_fields(harness) -> None:
    rounds = [entry for name in ("vbn_event", "vbn0_event")
              for entry in harness["reports"][name]["line"]["probe_stiffness_record"]]
    assert rounds, "the event rows probe (the steady row S8 has no probe round)"
    for entry in rounds:
        assert entry["warning_range"] == [0.8, 3.6]
        for values in entry["legs"].values():
            assert {"scale_k_N_m", "scale_ratio", "scale_mid_shift_periods", "moved_by_mid_m",
                    "is_psw_scale_leg"} <= set(values)
