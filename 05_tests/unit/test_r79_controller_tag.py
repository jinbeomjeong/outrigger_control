"""Top-level ``controller_tag`` of the r79 / r67 screen results = the T4h meta tag.

G-S b1ddeae (436.8): the r79 seedext (H-8) and ``las_t3_dg3`` H-6 results carried
``final_C4G2_P3`` and the H-7 (③ off) result no tag, while the T4h meta of the same runs had
``final_C4G2_P3_LAS_K1`` / ``final_C4G2_LAS_K1``. Cause: the screens do not go through
``verdict_runs._finish``, so ``plant_options_record`` read an empty ``_LAST_FINISHED_CONFIG``
and tagged the options only. The screens now pass the run's own config. The record is written
after the run; the commands and their hash do not read it.

The screens import the numba harness (dynamics-dev); the checks run in a subprocess so the
patched helpers do not leak into other tests.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
S8 = ROOT / "04_scripts" / "03_control" / "s8"
COUPLED = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
SRC = ROOT / "03_src"
TIMEOUT_S = 600

CHECK_SCRIPT = """
import json
import os
import sys
from types import SimpleNamespace

sys.path[:0] = [{s8!r}, {coupled!r}, {src!r}]
os.environ["R79_V5_SETTING"] = "VB"
os.environ["R67_V5_SETTING"] = "VB"
import harness_hydraulics
import r67_g1_screen as r67
import r79_sensor_screen as r79
import run_v5
import verdict_runs
from outrigger_sim.control.c2 import C2Config
from outrigger_sim.hydraulics.v5_options import HydraulicOptions, controller_tag

# the preset checks need a built plant; this test only reads the tag wiring
harness_hydraulics.check_last_lock_window = lambda *args, **kwargs: None
harness_hydraulics.check_last_extend_start = lambda *args, **kwargs: None
harness_hydraulics.last_armed_record = lambda *args, **kwargs: {{}}
r67.first_lift_time_s = lambda plant, period: None
r67._lift_and_lock_window = lambda plant, ctrl: (None, {{}})
r67.resume_k1_block = lambda ctrl: {{}}
verdict_runs.review_record_of = lambda ctrl: None
r79.j_p3_run_record = lambda record, periods: {{}}
verdict_runs._LAST_FINISHED_CONFIG[0] = None  # the screens never call _finish

preset = C2Config().with_10hz_d1()
vb_plant = run_v5.SETTINGS["VB"][1]
arms = {{"p3_on": HydraulicOptions.from_dict(vb_plant),
        "p3_off": HydraulicOptions.from_dict(
            {{k: v for k, v in vb_plant.items() if k != "extend_start_tracked"}})}}
out = {{}}
for name, options in arms.items():
    ctrl = SimpleNamespace(config=preset, events=[])
    run = SimpleNamespace(ctrl=ctrl, adapter=None, controller_period_arrays=lambda: {{}})
    r67.V5_JOB_RUN.update(plant=SimpleNamespace(), ctrl=ctrl)
    out[name] = {{
        "t4h_meta": controller_tag(options, preset),  # r79.write_t4h / run_v5 _finish rule
        "r79_top": r79._v5_record(options, run, SimpleNamespace()).get("controller_tag"),
        "r67_grid_top": r67.v5_job_record(options, "R67_V5_SETTING").get("controller_tag"),
        "without_config": verdict_runs.plant_options_record(options).get("controller_tag"),
    }}
print(json.dumps(out))
"""


def run_check(tmp_path: Path) -> dict:
    script = tmp_path / "tag_check.py"
    script.write_text(CHECK_SCRIPT.format(s8=str(S8), coupled=str(COUPLED), src=str(SRC)),
                      encoding="utf-8")
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "MKL_THREADING_LAYER": "TBB"}
    # the screens read the project root from argv[1] at import
    done = subprocess.run([sys.executable, "-I", "-B", str(script), str(ROOT)], cwd=ROOT,
                          env=environment, capture_output=True, text=True, timeout=TIMEOUT_S)
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_screen_top_level_tag_is_the_t4h_meta_tag(tmp_path: Path) -> None:
    pytest.importorskip("numba", reason="r67 / r79 import the harness (dynamics-dev)")
    tags = run_check(tmp_path)
    assert tags["p3_on"]["t4h_meta"] == "final_C4G2_P3_LAS_K1"  # H-6 / H-8 T4h meta
    assert tags["p3_off"]["t4h_meta"] == "final_C4G2_LAS_K1"  # H-7 T4h meta
    for name, arm in tags.items():
        assert arm["r79_top"] == arm["t4h_meta"], name
        assert arm["r67_grid_top"] == arm["t4h_meta"], name
    # the G-S b1ddeae symptom when the run's config is not passed
    assert tags["p3_on"]["without_config"] == "final_C4G2_P3"
    assert tags["p3_off"]["without_config"] is None
