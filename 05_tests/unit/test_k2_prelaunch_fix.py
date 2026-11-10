"""K-2 pre-launch fixes: the V-5 flattener, the identity sidecar wrapper, run_ps7 ``--out`` / row record and the
V-6 D-hat record of ``k2_judge``.

The flattener tests read the stored acceptance outputs (``06_analysis/02_control/touch_phase/acceptance``,
tracked) and check the flat rows against the counts of the stored ``judgement.json``; they need scipy
(``acc_judge``) and skip without it. Nothing is simulated.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
K2_SCRIPTS = ROOT / "04_scripts" / "03_control" / "k2"
for _folder in (K2_SCRIPTS, ROOT / "04_scripts" / "03_control" / "d8x"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

import k2_judge  # noqa: E402
import k2_v5_flatten  # noqa: E402
import run_with_identity  # noqa: E402

ACCEPTANCE = ROOT / "06_analysis" / "02_control" / "touch_phase" / "acceptance"
PS7_E = ROOT / "06_analysis" / "02_control" / "touch_phase" / "ps7_E.json"
G8_DIR = ACCEPTANCE / "g8_safe_stop"


def _g8_overrides() -> list[str]:
    return [f"g8_safe_stop:g8_jobs{n}={G8_DIR / f'out{n}.jsonl'}" for n in (1, 3, 5)]


@pytest.fixture(scope="module")
def flat(tmp_path_factory) -> Path:
    pytest.importorskip("scipy")
    out_dir = tmp_path_factory.mktemp("flat")
    argv = ["--arm-dir", str(ACCEPTANCE), "--out-dir", str(out_dir), "--source", f"ps7:ps7={PS7_E}",
            *[item for override in _g8_overrides() for item in ("--source", override)]]
    assert k2_v5_flatten.main(argv) == k2_v5_flatten.EXIT_WRITTEN
    return out_dir


def _bundle(flat: Path, name: str) -> dict:
    return json.loads((flat / f"{name}.json").read_text(encoding="utf-8"))


def _judgement() -> dict:
    return json.loads((ACCEPTANCE / "judgement.json").read_text(encoding="utf-8"))


# --- V-5 flattener on the stored acceptance outputs --------------------------------------------------------
def test_grid_parts_match_the_stored_judgement(flat) -> None:
    sources = _bundle(flat, "grid")["meta"]["sources"]
    rows = _bundle(flat, "grid")["runs"]
    for part in _judgement()["grid"]["parts"]:
        part_rows = [row for row in rows if row["part"] == part["name"]]
        assert sources[part["name"]]["rows"] == part["n"]
        assert sum(not row["pass"] for row in part_rows) == part["failed"], part["name"]


def test_soil_d8_noise_match_the_stored_judgement(flat) -> None:
    judgement = _judgement()
    soil = _bundle(flat, "soil")["meta"]
    assert (soil["rows"], soil["failed"]) == (judgement["soil"]["n"], judgement["soil"]["failed"])
    d8 = _bundle(flat, "d8")["meta"]
    assert d8["rows"] == judgement["d8"]["n"]
    assert d8["failed"] == sum(judgement["d8"]["bad_counts"].values()) == 0
    noise = _bundle(flat, "noise_L2")["meta"]
    assert (noise["rows"], noise["failed"]) == (judgement["noise_L2"]["runs"], judgement["noise_L2"]["failures"])


def test_regression_parts_match_the_stored_judgement(flat) -> None:
    judgement = _judgement()
    sources = _bundle(flat, "regression")["meta"]["sources"]
    for part in judgement["regression_flat"]:
        assert sources[part["name"]]["rows"] == part["n"]
    assert sources["clip_A"]["rows"] == judgement["regression_A"]["n"]
    assert sources["clip_r79_L1L2"]["rows"] == judgement["regression_r79_L1L2"]["n"]
    assert _bundle(flat, "regression")["meta"]["rows"] == 93


def test_ps7_and_g8_rows(flat) -> None:
    ps7 = _bundle(flat, "ps7")
    stored = json.loads(PS7_E.read_text(encoding="utf-8"))
    assert ps7["meta"]["rows"] == len(stored) == 20
    assert ps7["meta"]["failed"] == sum(not row["pass"] for row in stored)
    g8 = _bundle(flat, "g8_safe_stop")["runs"]
    lines = [json.loads(line) for n in (1, 3, 5)
             for line in (G8_DIR / f"out{n}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(g8) == len(lines) == 83
    assert sum(row["ready"] for row in g8) == sum(line["final"] == "ready" for line in lines)
    assert all(all(name.startswith("FAULT") for name in row["faults"]) for row in g8)


def test_v5_bundle_reads_the_flat_rows(flat) -> None:
    """The stored outputs have no sidecar / provenance: only the common rc / c2_sha256 items fail, and the K-2
    evidence makes the bundle not judgeable (rev2 1)."""
    for name, kind in (("grid", "pass_to_fail"), ("noise_L2", "noise_cp")):
        path = str(flat / f"{name}.json")
        result = k2_judge.v5_bundle({"kind": kind, "off": [path], "tcl": [path], "key": "key", "status": "pass"})
        failing = {item for item, value in result["absolute"]["tcl"]["items"].items() if not value["ok"]}
        assert result["unpaired"] == [] and result["relative_passed"] is True
        assert failing == {"rc", "c2_sha256"} and "K-2 evidence" in result["not_judgeable"]
        assert result["result_kind"] == "not_judgeable"  # rev6 1: common items are not judgeable
    path = str(flat / "g8_safe_stop.json")
    result = k2_judge.v5_bundle({"kind": "g8", "off": [path], "tcl": [path], "key": "key", "status": "pass",
                                 "ready": "ready", "faults": "faults"})
    assert result["relative_passed"] is True and result["failures"] == []


def test_existing_output_is_refused(flat) -> None:
    argv = ["--arm-dir", str(ACCEPTANCE), "--out-dir", str(flat), "--bundles", "soil"]
    assert k2_v5_flatten.main(argv) == k2_v5_flatten.EXIT_INPUT


def test_missing_r79_judgement_names_the_judge_command(tmp_path, capsys) -> None:
    argv = ["--arm-dir", str(tmp_path), "--out-dir", str(tmp_path / "flat"), "--bundles", "noise_L2"]
    assert k2_v5_flatten.main(argv) == k2_v5_flatten.EXIT_INPUT
    assert "r79_sensor_judge.py judge" in capsys.readouterr().out


def test_d8_row_conditions() -> None:
    good = {"id": "x", "min_true_cyl_force_kN": 20.0, "ss_true_att_deg_maxabs": 0.05, "t_ready_s": 40.0}
    assert k2_v5_flatten.d8_row_pass(good)
    for change in ({"error": "boom"}, {"fails": ["S-1"]}, {"fault": True}, {"min_true_cyl_force_kN": 14.0},
                   {"ss_true_att_deg_maxabs": 0.21}, {"t_ready_s": None}, {"t_ready_s": 100.1}):
        assert not k2_v5_flatten.d8_row_pass({**good, **change}), change


# --- identity sidecar wrapper -----------------------------------------------------------------------------
def _wrapper(sidecar: Path, *command: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-B", str(K2_SCRIPTS / "run_with_identity.py"), str(sidecar),
                           "--git-dir", str(ROOT), "--", *command], capture_output=True, text=True,
                          env=env, cwd=ROOT, timeout=300, check=False)


def test_wrapper_passes_rc_and_records_identity(tmp_path) -> None:
    sidecar = tmp_path / "id.json"
    env = {**os.environ, "ACC_K2": "on", "MKL_NUM_THREADS": "1", "UNRELATED_X": "1"}
    done = _wrapper(sidecar, sys.executable, "-I", "-c", "import sys; sys.exit(7)", env=env)
    assert done.returncode == 7
    record = json.loads(sidecar.read_text(encoding="utf-8"))
    assert record["rc"] == 7 and record["argv"][-1] == "import sys; sys.exit(7)"
    assert record["env"]["ACC_K2"] == "on" and record["env"]["MKL_NUM_THREADS"] == "1"
    assert "UNRELATED_X" not in record["env"]
    assert record["affinity_mask"] == run_with_identity.affinity_mask()
    assert record["child_affinity_mask"] in (None, record["affinity_mask"])
    assert record["git_start"]["head"] == record["git_end"]["head"]
    assert record["start"] <= record["end"]


def test_wrapper_refuses_an_existing_sidecar(tmp_path) -> None:
    sidecar = tmp_path / "id.json"
    sidecar.write_text("{}", encoding="utf-8")
    assert _wrapper(sidecar, sys.executable, "-c", "pass").returncode == run_with_identity.EXIT_WRAPPER_ERROR
    assert sidecar.read_text(encoding="utf-8") == "{}"


def test_env_subset_names() -> None:
    environ = {"OMP_WAIT_POLICY": "PASSIVE", "OUTRIGGER_HULL_HOOK": "off", "ACC_COMBO": "off",
               "NUMBA_NUM_THREADS": "1", "MKL_THREADING_LAYER": "TBB", "PATH": "x"}
    assert set(run_with_identity.env_subset(environ)) == set(environ) - {"PATH"}


# --- run_ps7 --------------------------------------------------------------------------------------------
def test_ps7_existing_out_is_not_overwritten(tmp_path) -> None:
    out = tmp_path / "ps7.json"
    out.write_text("[]", encoding="utf-8")
    done = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "04_scripts" / "03_control" / "touch_phase"
                                                          / "run_ps7.py"), "E", "--out", str(out)],
                          capture_output=True, text=True, timeout=120, check=False)
    assert done.returncode == 0 and "already done" in done.stdout
    assert out.read_text(encoding="utf-8") == "[]"


def test_ps7_preset_record() -> None:
    sys.path.insert(0, str(ROOT / "03_src"))
    sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "touch_phase"))
    import run_ps7

    from outrigger_sim.control import c2
    record = run_ps7._preset_record(c2)
    assert record == {"controller_tag": "final_C4G2_LAS_K1", "touch_creep_latch": False}


# --- V-6 D-hat from the k2 block ------------------------------------------------------------------------------
def test_v6_reads_dhat_from_the_k2_block(tmp_path) -> None:
    row = {key: None for key in k2_judge.CHRONO_ROW_KEYS}
    row.update(case_id="K2_L1_top_fdown3.5_Fs0_off", controller_tag=k2_judge.expected_tag(False, False),
               k1_order_gate=False, touch_creep_latch=False, engine="L1", floor_true_deg=[0.0, 3.5],
               t_touch_s=1.0, t_lift_s=2.0, t_ready_s=40.0, J1_min_cyl_after_lift_N=30e3, J1_window_s=1.0,
               reanchor_intervals_s=[], J2_min_cyl_reanchor_N=None, J4_att_max_after_ready_deg=0.01,
               J6_max_moving_bar=150.0, J6_max_locked_bar=200.0, crawler_recontact_after_loc=0, events=[],
               k2={"dhat_N": 1234.5, "dhat_window_open_legs": ["FL"], "dhat_window_stroke_mm": 3.0})
    (tmp_path / "row.json").write_text(json.dumps(row), encoding="utf-8")
    np.savez(tmp_path / "pads.npz", t=np.linspace(0.0, 50.0, 501), N=np.full((501, 4), 50e3))
    spec = {"row_json": str(tmp_path / "row.json"), "pads_npz": str(tmp_path / "pads.npz"), "arm": "off",
            "engine": "L1"}
    result = k2_judge.judge_chrono_k2_row("K2_L1_top_fdown3.5_Fs0_off", spec, k2_judge.f_d8_N())
    assert result["dhat_N"] == 1234.5
    assert result["dhat_window_open_legs"] == ["FL"] and result["dhat_window_stroke_mm"] == 3.0
