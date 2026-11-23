"""436.9 edition 6 erratum 3 (``jp3_remedy_spec_v6_erratum3.md``): the R15 worsening of the
sensitivity judge (3-1, ``jp3_ed6_judge.sens_r15_worsening``) and the 12b array list of the key
presence table (3-3). The grid key presence (3-2) is tested beside the grid judge in
``test_ed6_judges.py``. Synthetic metric rows only.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
for _path in (COUPLED_DIR, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import jp3_12b_judge as judge12b  # noqa: E402
import jp3_ed6_judge as ed6  # noqa: E402

PHASES = ("R15_o0.0", "R15_o0.05")
V0_KN = (-0.22, -0.72)
"""The stored V0 R15 J2 values of erratum 3 3-1 (kN; S = 0.5 kN)."""


def _metric(setting: str, phase: str, value_kN: float | None) -> dict:
    return {"setting": setting, "row": "R15", "phase": phase, "is_event": True, "group": "R",
            "F_after_W_min_kN": value_kN, "F_after_event": None, "F_after": None}


def _rows_by(values: dict[str, tuple]) -> dict[str, list[dict]]:
    """setting -> its R15 values per phase (None in a tuple slot = no line for that phase)."""
    rows_by = {"V0": [_metric("V0", p, v) for p, v in zip(PHASES, V0_KN, strict=True)]}
    for setting, pair in values.items():
        rows_by[setting] = [_metric(setting, p, v) for p, v in zip(PHASES, pair, strict=True)
                            if v != "missing"]
    return rows_by


@pytest.mark.parametrize(("pair", "state", "worse"), [
    ((-3.0, -4.0), "구분됨", True),      # worse in both phases beyond S
    ((8.73, 2.05), "구분됨", False),      # the predicted improvement (E +5.86 kN)
    ((-0.30, -0.60), "위상 산포 안", False),  # within the V0 phase scatter
])
def test_r15_states(pair, state, worse) -> None:
    result = ed6.sens_r15_worsening(_rows_by({"VBLc005": pair}), ("VBLc005",))["VBLc005"]
    assert (result["state"], result["worse"]) == (state, worse)
    assert result["weak_basis"] is True
    assert result["S_N"] == pytest.approx(500.0)
    assert set(result["values"]) == set(PHASES)


@pytest.mark.parametrize("pair", [(-3.0, "missing"), (None, -4.0)])
def test_r15_missing_phase_or_none_is_not_judgeable(pair) -> None:
    result = ed6.sens_r15_worsening(_rows_by({"VBLv05": pair}), ("VBLv05",))["VBLv05"]
    assert result["state"] == "판정 불가" and result["worse"] is False and result["reason"]


def test_r15_setting_without_lines_is_not_judgeable() -> None:
    result = ed6.sens_r15_worsening(_rows_by({}), ("VBLv15",))
    assert result["VBLv15"]["state"] == "판정 불가"


def test_r15_only_the_worse_setting_is_worse() -> None:
    values = {"VBLc005": (8.73, 2.05), "VBLc04": (-3.0, -4.0), "VBLv05": (8.73, 2.06),
              "VBLv15": (8.73, 2.05)}
    result = ed6.sens_r15_worsening(_rows_by(values), ed6.SENSITIVITY_SETTINGS)
    assert [s for s, entry in result.items() if entry["worse"]] == ["VBLc04"]


def test_key_presence_12b_arrays_are_the_judge_arrays() -> None:
    """Erratum 3 3-3: one source - every array jp3_12b_judge reads is listed."""
    listed = set(ed6.KEY_PRESENCE["t4h_arrays_12b"])
    assert listed >= set(judge12b.T4H_REV6_ARRAYS) | set(judge12b.T4H_ARRAYS)
    assert "jp3_r59_end_guard_substeps" in listed
    assert set(ed6.KEY_PRESENCE["grid_rows"]) >= set(ed6.GRID_REQUIRED_KEYS)
