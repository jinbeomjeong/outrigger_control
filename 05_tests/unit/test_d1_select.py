"""D-1 selection script (``d1_select.py``) against the sealed test values of
``d1_selection_rules.md`` 12.1 (eight cases), plus the D-1 row table (``d1_rows.py``: G-1
counts, slopes, keys) and the section 3 / 4.1 plumbing. Synthetic inputs, no harness run."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import d1_rows  # noqa: E402
import d1_select as sel  # noqa: E402


def _run(group, level, slope, *, m, k=1, eps=0.0, setting="VB", grade="pass", f_first=60e3,
         stroke=0.5, base="rigid", sink=None, holds=0, f_judged=20e3, att=0.05) -> dict:
    row_key = f"{group}|{base}|{level}|{slope}|K{k}" + (f"|{sink['name']}@{sink['leg']}"
                                                        if sink else "")
    return {"row_key": row_key, "group": group, "level": level, "slope": slope, "base": base,
            "K": k, "sink": sink, "tags": [], "setting": setting, "eps": eps, "grade": grade,
            "fail_items": [] if grade == "pass" else ["x"], "F_first_level_min_N": f_first,
            "stroke_max_m": stroke, "F_judged_min_N": f_judged, "att_judged_deg": att,
            "dsb75_events": [{"name": "INFO_DIFF_SINK_HOLD"}] * holds, "j_p3": "pass",
            "m": m, "terms": {}, "missing_terms": []}


def _roll_runs(level, plus_m, minus_m, **kwargs) -> list[dict]:
    """Four VB runs per sign: (K1, K3) x (eps 0, 2e-3) in that order."""
    runs = []
    for slope, values in (("roll+op", plus_m), ("roll-op", minus_m)):
        for value, (k, eps) in zip(values, ((1, 0.0), (1, 2e-3), (3, 0.0), (3, 2e-3)),
                                   strict=True):
            extra = kwargs.get(slope, {}).get((k, eps), {})
            runs.append(_run("H-R-0", level, slope, m=value, k=k, eps=eps, **extra))
    return runs


def _s1(entries: list[dict]) -> dict:
    return sel.s1_selection(entries, sel._by_key(entries))


# ------------------------------------------------------------------------- 12.1 cases 1 .. 3
def test_case_1_smaller_margin_wins() -> None:
    entries = _roll_runs("middle", (0.120, 0.118, 0.110, 0.111), (0.105, 0.109, 0.1095, 0.108))
    cell = _s1(entries)["C2-03"]
    assert cell["selected"] == ["D1C2_middle_rollm4.4_Fs4"]
    assert not cell["baseline_failure"]


def test_case_2_tie_goes_to_the_smaller_first_level_force() -> None:
    entries = _roll_runs("middle", (0.120, 0.118, 0.1100, 0.111),
                         (0.1105, 0.112, 0.113, 0.114),
                         **{"roll+op": {(3, 0.0): {"f_first": 57_100.0}},
                            "roll-op": {(1, 0.0): {"f_first": 55_000.0}}})
    cell = _s1(entries)["C2-03"]
    assert cell["selected"] == ["D1C2_middle_rollm4.4_Fs4"]
    tie_values = {c["name"]: c["F_first_level_min_N"] for c in cell["candidates"]}
    assert tie_values == {"D1C2_middle_roll4.4_Fs4": 57_100.0,
                          "D1C2_middle_rollm4.4_Fs4": 55_000.0}


def test_case_3_allowed_stop_ranks_before_pass() -> None:
    entries = _roll_runs("middle", (0.30, 0.31, 0.32, 0.33), (0.05, 0.06, 0.07, 0.08),
                         **{"roll+op": {(1, 0.0): {"grade": "allowed_stop"}}})
    assert _s1(entries)["C2-03"]["selected"] == ["D1C2_middle_roll4.4_Fs4"]


# ---------------------------------------------------------------------------- 12.1 case 4
def test_case_4_failed_fup_rec_is_excluded_without_a_g3_stop() -> None:
    entries = []
    for slope, values in (("diag-rec", (0.08, 0.09)), ("roll-rec", (0.06, 0.07)),
                          ("fup-rec", (0.02, 0.03))):
        for value, eps in zip(values, (0.0, 2e-3), strict=True):
            grade = "fail" if slope == "fup-rec" and eps == 0.0 else "pass"
            entries.append(_run("H-S-0", "middle", slope, m=value, eps=eps, grade=grade,
                                base="J1"))
            entries.append(_run("H-S-0", "middle", slope, m=value, eps=eps, base="J1",
                                setting="V0"))
    index = sel._by_key(entries)
    cell = sel.s2_selection(entries, index, d1_rows.slope_deg)["S-01"]
    assert cell["selected"] == ["D1S_J1_B_middle_Fs4_rm2p64_p0"]
    assert cell["fup_rec_excluded"] and "가정 경계 미성립" in cell["fup_rec_note"]
    assert sel.gate_g3(entries, index)["pass"]


# ------------------------------------------------------------------------- 12.1 cases 5, 6
def test_case_5_rule_1_transfers_the_additive_correction() -> None:
    means = {("V0", 1): 0.20, ("V0", 3): 0.17, ("VB", 1): 0.19, ("VB", 3): 0.15}
    result = sel.crawler_rule(means, 0.005)
    assert result["rule"] == 1
    assert result["transfer_correction"] == pytest.approx(-0.02)


def test_case_6_opposite_small_effects_are_rule_2() -> None:
    means = {("V0", 1): 0.200, ("V0", 3): 0.203, ("VB", 1): 0.200, ("VB", 3): 0.198}
    assert sel.crawler_rule(means, 0.004)["rule"] == 2


# ------------------------------------------------------------------------- 12.1 cases 7, 8
def _psc_entries(stroke_override: dict | None = None) -> list[dict]:
    entries = []
    holds = {"c-slow": 0, "c-mid": 1, "c-edge": 0, "c-fast": 1}
    for name, leg in sel.PSC_POINTS:
        sink = {"name": name, "leg": leg}
        for eps in (0.0, 2e-3):
            stroke = (stroke_override or {}).get((name, leg, eps), 0.55)
            entries.append(_run("H-S-C", "top", "flat", m=0.2, eps=eps, base="J1", sink=sink,
                                holds=holds[name], f_judged=12_000.0, att=0.06,
                                stroke=stroke))
    return entries


def test_case_7_quiet_profiles_skip_d1_psc() -> None:
    result = sel.s3_selection(_psc_entries())
    assert result["rows"] == [] and result["decision"] == "하네스 근거로 생략"


def test_case_8_near_stroke_brings_its_profile_and_base() -> None:
    result = sel.s3_selection(_psc_entries({("c-fast", "FL", 2e-3): 0.650}))
    assert result["rows"] == ["D1PSC_J1_B_top_Fs4_FL_cfast", "D1PSC_J1_B_top_Fs4_spFLJ1_base"]
    assert result["profiles"]["c-fast@FL"]["T3_near_limit"]


# --------------------------------------------------------------------------- plumbing
def test_run_margin_terms() -> None:
    d1 = {"F_judged_min_N": 2 * sel.F_MIN_N, "t_ready_s": 60.0, "t_ready_limit_s": 120.0,
          "att_judged_deg": 0.1, "stroke_max_m": 0.5136, "group": "H-R-0", "path": "steady"}
    margin = sel.run_margin(d1)
    assert margin["terms"]["m_F"] == pytest.approx(1.0)
    assert margin["terms"]["m_T"] == pytest.approx(0.5)
    assert margin["m"] == pytest.approx(0.25)  # stroke term (0.6848 - 0.5136) / 0.6848
    no_ready = sel.run_margin({**d1, "t_ready_s": None})
    assert no_ready["terms"]["m_T"] is None
    psc = sel.run_margin({**d1, "group": "H-S-C", "path": "event"})
    assert psc["terms"]["m_T"] is None


def test_missing_field_stops_with_exit_code_2() -> None:
    line = {"job": {"d1": {"key": "x"}, "eps": 0.0, "setting": "VB"},
            "d1": {name: None for name in sel.REQUIRED_FIELDS if name != "j_p3"}}
    report, code = sel.select([line], set(), d1_rows.slope_deg)
    assert code == 2 and report["gates"]["G-2"]["runs"][0]["missing"] == ["j_p3"]


def test_baseline_failure_adds_the_next_candidate() -> None:
    entries = _roll_runs("bottom", (0.30, 0.31, 0.32, 0.33), (0.05, 0.06, 0.07, 0.08),
                         **{"roll+op": {(1, 0.0): {"grade": "fail"}}})
    twin = dict(entries[0], setting="V0")
    cell = _s1([*entries, twin])["C2-07"]
    assert cell["baseline_failure"]
    assert cell["selected"] == ["D1C2_bottom_roll4.4_Fs4", "D1C2_bottom_rollm4.4_Fs4"]


def test_crawler_table_cell_from_runs() -> None:
    """Section 8 on run entries: the case 5 means with a phase spread, m and every term."""
    means = {("V0", 1): 0.20, ("V0", 3): 0.17, ("VB", 1): 0.19, ("VB", 3): 0.15}
    entries = []
    for (setting, k), mean in means.items():
        for eps, shift in ((0.0, 0.001), (2e-3, -0.001)):
            run = _run("H-R-0", "top", "flat", m=mean + shift, k=k, eps=eps, setting=setting)
            run["terms"] = {name: mean + shift for name in sel.TERMS}
            entries.append(run)
    cell = sel.crawler_table(entries, sel._by_key(entries))["T|flat"]
    assert cell["m"]["rule"] == 1 and cell["m"]["sigma"] == pytest.approx(0.002)
    assert cell["m"]["transfer_correction"] == pytest.approx(-0.02)
    assert not cell["terms_differ_from_m"]


# ------------------------------------------------------------------------------ D-1 rows
def test_row_table_matches_the_g1_counts() -> None:
    rows = d1_rows.all_rows()
    families = {}
    for row in rows:
        family = "H-S-C-g" if row.group == "H-S-C-g" else row.group[:3]
        families[family] = families.get(family, 0) + 1
    assert families == sel.EXPECTED_COMBINATIONS
    assert len(d1_rows.jobs()) == 868


@pytest.mark.parametrize(("name", "expected"), [
    ("diag-op", (2.3351, 1.5017)), ("fdown-val", (0.0, 3.5)), ("roll-val", (-5.5, 0.0)),
    ("fup-rec", (0.0, -2.8)), ("roll-rec", (-2.64, 0.0)), ("roll+rec", (2.2, 0.0)),
    ("diag-rec", (1.925, 1.4)), ("fdown-psa", (0.0, 2.4)), ("diag-psa-soil", (2.2, 1.6)),
    ("diag-val", (2.7355, 1.7592))])
def test_slope_values_of_the_row_definition(name, expected) -> None:
    assert d1_rows.slope_deg(name) == expected


def test_row_round_trip_and_paths() -> None:
    for row in d1_rows.all_rows():
        assert d1_rows.D1Row.from_job(row.to_job()) == row
    by_key = {row.key: row for row in d1_rows.all_rows()}
    assert by_key["D1|H-R-A|rigid+J1@FR|M|diag-op|K3"].path == "g6"
    assert by_key["D1|H-S-C|J2|B|flat|K1|c-slow@FL"].sink.timing == "ready"
    sloped = by_key["D1|H-S-C-g|J1|T|diag-rec|K1|c-mid@FR|dsb_gated_off"]
    assert sloped.role == "record" and sloped.path == "event"
    assert "ASSUMED_BOUNDARY" in by_key["D1|H-S-0|J1|M|fup-rec|K1"].tags
