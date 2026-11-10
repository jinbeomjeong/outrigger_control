"""K-2 path 1 (``k2_judge.py``) after rules rev2 .. rev4: V-5 absolute items and K-2 evidence, V-6 SH-1 .. SH-6,
E-5 / I-9 option values, the seal check and the stored-output self test. Synthetic inputs; the self test reads
the stored acceptance outputs (scipy for acc_judge). Nothing is simulated."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
K2_SCRIPTS = ROOT / "04_scripts" / "03_control" / "k2"
for _folder in (K2_SCRIPTS, ROOT / "04_scripts" / "03_control" / "d8x"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

import k2_judge  # noqa: E402
import k2_v5_flatten  # noqa: E402

F_D8 = 14414.589
TCL_TAG = "final_C4G2_LAS_K1_TCL"
OFF_TAG = "final_C4G2_LAS_K1"


# --- V-5 synthetic flat docs ---------------------------------------------------------------------------------
def _provenance(arm: str, **changes) -> dict:
    record = {"source": "p.json", "exists": True, "combo": "preset", "k2": k2_judge.ARM_K2[arm],
              "touch_creep_latch": arm == "tcl", "controller_tag": TCL_TAG if arm == "tcl" else OFF_TAG,
              "c2_sha256": k2_judge.C2_SHA256_RUN, "git_head": "6a44ff8"}
    record.update(changes)
    return record


def _step(arm: str, name: str = "d8", *, rc=0, events=None, provenance=None) -> dict:
    return {"step": name, "sidecar": {"exists": True, "rc": rc, "ACC_COMBO": "preset", "ACC_K2": k2_judge.ARM_K2[arm]},
            "provenance": provenance if provenance is not None else _provenance(arm), "events": events}


def _d8_row(index: int, **changes) -> dict:
    row = {"key": f"d8|{index}", "pass": True, "error": False, "fails": [], "fault": False,
           "min_true_cyl_force_kN": 40.0, "ss_true_att_deg_maxabs": 0.05, "t_ready_s": 45.0}
    row.update(changes)
    return row


def _doc(bundle: str, rows: list[dict], steps: list[dict], **meta) -> dict:
    return {"meta": {"tool": "k2_v5_flatten", "bundle": bundle, "sources": {"x": {"rows": len(rows), "error_rows": 0}},
                     "steps": steps, **meta}, "runs": rows}


def _write(tmp_path: Path, name: str, doc: dict) -> str:
    path = tmp_path / name
    path.write_text(json.dumps(doc), encoding="utf-8")
    return str(path)


def _d8_spec(tmp_path: Path, tcl_rows: list[dict], tcl_steps: list[dict] | None = None) -> dict:
    off = _doc("d8", [_d8_row(i) for i in range(576)], [_step("off")])
    tcl = _doc("d8", tcl_rows, tcl_steps or [_step("tcl")])
    return {"kind": "pass_to_fail", "off": [_write(tmp_path, "off.json", off)],
            "tcl": [_write(tmp_path, "tcl.json", tcl)], "key": "key", "status": "pass"}


def test_d8_absolute_items_pass_and_count_missing(tmp_path) -> None:
    good = [_d8_row(i) for i in range(576)]
    assert k2_judge.v5_bundle(_d8_spec(tmp_path, good))["passed"] is True
    rows = [*good[:574], _d8_row(574, t_ready_s=None), _d8_row(575, min_true_cyl_force_kN=14.0)]
    result = k2_judge.v5_bundle(_d8_spec(tmp_path, rows))
    items = result["absolute"]["tcl"]["items"]
    assert result["passed"] is False and result["missing"]["tcl"] == {"d8_ready": 1}
    assert items["d8_min_force"]["violations"] == 1 and result["relative_gates"] is False
    assert result["result_kind"] == "fail"  # rev6 1: a bundle item (missing included) is a failure


def test_common_items_and_counts_are_not_judgeable(tmp_path) -> None:
    """Rev6 1: common items (both arms) and counts make the bundle not judgeable, not failed."""
    rows = [_d8_row(i) for i in range(576)]
    bad_rc = k2_judge.v5_bundle(_d8_spec(tmp_path, rows, [_step("tcl", rc=1)]))
    assert bad_rc["absolute"]["tcl"]["items"]["rc"]["violations"] == 1
    assert bad_rc["result_kind"] == "not_judgeable" and bad_rc["passed"] is False
    other_c2 = _step("tcl", provenance=_provenance("tcl", c2_sha256="0" * 64))
    assert k2_judge.v5_bundle(_d8_spec(tmp_path, rows, [other_c2]))["result_kind"] == "not_judgeable"
    assert k2_judge.v5_bundle(_d8_spec(tmp_path, rows[:575]))["result_kind"] == "not_judgeable"
    off = _doc("d8", rows, [_step("off", rc=2)])
    spec = {"kind": "pass_to_fail", "off": [_write(tmp_path, "off_rc.json", off)],
            "tcl": [_write(tmp_path, "tcl_ok.json", _doc("d8", rows, [_step("tcl")]))], "key": "key",
            "status": "pass"}
    result = k2_judge.v5_bundle(spec)
    assert result["result_kind"] == "not_judgeable" and "off rc" in result["not_judgeable"]


def test_regression_missing_verdict_is_a_counted_failure() -> None:
    keys = {"judged_sha256": k2_judge.REGRESSION_JUDGED_SHA256, "record_sha256": k2_judge.REGRESSION_RECORD_SHA256}
    meta = {"r79_judgement": {"unmatched": 0, "errors": 0}, "regression_keys": keys}
    rows = [{"key": f"r|{i}", "pass": True, "verdict_missing": i < 2} for i in range(93)]
    result = k2_judge.v5_absolute("regression", [_doc("regression", rows, [], **meta)])
    assert result["missing"] == {"regression_verdict": 2} and result["passed"] is False
    flat = k2_v5_flatten._r79_rows({"runs": [{"key": "a", "pass": None, "level": "L2", "inner": "x"}]}, "p",
                                   l2_without_s1_front=False)
    assert flat[0]["verdict_missing"] is True


def test_k2_evidence_makes_the_bundle_not_judgeable(tmp_path) -> None:
    rows = [_d8_row(i) for i in range(576)]
    wrong_k2 = _step("tcl", provenance=_provenance("tcl", k2="off"))
    result = k2_judge.v5_bundle(_d8_spec(tmp_path, rows, [wrong_k2]))
    assert "K-2 evidence" in result["not_judgeable"]
    no_latch = _step("tcl", events={"source": "ps7", "rows": 20, "latch_rows": 0, "creep_rows": 0})
    assert "no row with" in str(k2_judge.v5_evidence("ps7", "tcl", [_doc("ps7", [], [no_latch])]))
    creep_off = _step("off", events={"source": "ps7", "rows": 20, "latch_rows": 1, "creep_rows": 1})
    assert k2_judge.v5_evidence("ps7", "off", [_doc("ps7", [], [creep_off])])
    g8 = {"step": "g8_jobs1", "sidecar": {"exists": True, "rc": 0, "ACC_COMBO": "preset", "ACC_K2": "on"},
          "provenance": None, "events": None}
    assert "ACC_COMBO" in str(k2_judge.v5_evidence("g8_safe_stop", "tcl", [_doc("g8_safe_stop", [], [g8])]))
    row = {"key": "g", "pass": True, "touch_creep_latch": True, "controller_tag": OFF_TAG}
    assert k2_judge.v5_evidence("g8_safe_stop", "tcl", [_doc("g8_safe_stop", [row], [])])


def _g8_sidecar(**changes) -> dict:
    sidecar = {"exists": True, "rc": 0, "ACC_COMBO": "off", "ACC_K2": "on", "git_start_head": k2_judge.RUN_HEAD,
               "git_end_head": k2_judge.RUN_HEAD, "git_start_clean": True, "git_end_clean": True}
    sidecar.update(changes)
    return sidecar


def test_g8_c2_from_the_sidecar_and_checkout() -> None:
    """Rev5 2: G8 c2.py = sidecar HEAD 6a44ff8 at start and end, clean, rc 0, checkout c2.py sha f58ee42b."""
    checkout = {"sha256": k2_judge.C2_SHA256_RUN}

    def c2_item(sidecar: dict, checkout_c2=checkout) -> dict:
        steps = [{"step": "g8_jobs1", "sidecar": sidecar, "provenance": None, "events": None}]
        doc = _doc("g8_safe_stop", [], steps, checkout_c2=checkout_c2)
        return k2_judge.v5_absolute("g8_safe_stop", [doc])["items"]["c2_sha256"]

    assert c2_item(_g8_sidecar())["ok"] is True
    assert c2_item(_g8_sidecar(git_end_head="0" * 40))["violations"] == 1
    assert c2_item(_g8_sidecar(git_start_clean=False))["violations"] == 1
    assert c2_item(_g8_sidecar(rc=1))["violations"] == 1
    assert c2_item(_g8_sidecar(), {"sha256": "0" * 64})["violations"] == 1
    assert c2_item(_g8_sidecar(git_end_clean=None))["missing"] == 1
    assert c2_item(_g8_sidecar(), None)["missing"] == 1


def test_g8_rows_without_switch_fields_are_missing() -> None:
    steps = [{"step": "g8_jobs1", "sidecar": _g8_sidecar(), "provenance": None, "events": None}]
    good = {"key": "g", "pass": True, "touch_creep_latch": True, "controller_tag": TCL_TAG}
    assert k2_judge.v5_evidence("g8_safe_stop", "tcl", [_doc("g8_safe_stop", [good], steps)]) == []
    bare = {"key": "h", "pass": True}
    assert k2_judge.v5_evidence("g8_safe_stop", "tcl", [_doc("g8_safe_stop", [good, bare], steps)])
    assert k2_judge.v5_evidence("grid", "tcl", [_doc("grid", [bare], [])]) == []
    assert all(step.events_part is None for step in k2_v5_flatten.STEPS["g8_safe_stop"])


def test_soil_markers_and_rigid_relative(tmp_path) -> None:
    def rows(g1_pass: bool, rigid_pass: bool) -> list[dict]:
        out = [{"key": f"soil_A|A|G1|FL|Fs0|two|{i}", "pass": g1_pass, "error": False, "fault_periods": 0}
               for i in range(30)]
        return out + [{"key": f"soil_A|A|rigid|FL|Fs0|two|{i}", "pass": rigid_pass, "error": False,
                       "fault_periods": 0} for i in range(30)]

    def spec(off_rows, tcl_rows):
        return {"kind": "pass_to_fail", "key": "key", "status": "pass",
                "off": [_write(tmp_path, "s_off.json", _doc("soil", off_rows, [_step("off", "soil_A")]))],
                "tcl": [_write(tmp_path, "s_tcl.json", _doc("soil", tcl_rows, [_step("tcl", "soil_A")]))]}

    assert k2_judge.v5_bundle(spec(rows(True, True), rows(True, True)))["passed"] is True
    g1_fail = k2_judge.v5_bundle(spec(rows(False, True), rows(False, True)))
    assert g1_fail["absolute"]["tcl"]["items"]["soil_G1_J2_pass"]["violations"] == 30
    assert g1_fail["pass_to_fail"] == []  # G1 / J2 rows are absolute, not compared
    assert k2_judge.v5_bundle(spec(rows(True, True), rows(True, False)))["passed"] is False


def _noise_meta(**changes) -> dict:
    meta = {"r79_judgement": {"unmatched": 0, "errors": 0, "reference_all_false_loc": 0, "unmatched_keys": []},
            "settings": {"preset_settings": True, "preset_sgs_keys": ["lift_stroke_guard.enable"], "missing": 0,
                         "rows_without_sgs_keys": 0, "mismatch_sgs": 0, "mismatch_all": 855,
                         "differing_keys": {"target.gyro_noise_std_rad_s": 855}}}
    meta.update(changes)
    return meta


def test_noise_items() -> None:
    rows = [{"key": f"n|{i}", "pass": i >= 10} for i in range(855)]
    result = k2_judge.v5_absolute("noise_L2", [_doc("noise_L2", rows, [], **_noise_meta())])
    assert result["passed"] is True  # gyro-noise key differs by design (rev4 1 (b))
    record = result["record"]
    assert record["cp95_upper_beta"] == pytest.approx(0.019758084627699315, rel=1e-12)
    assert abs(record["cp95_upper_bisection"] - record["cp95_upper_beta"]) < 1e-12
    sgs = _noise_meta(settings={**_noise_meta()["settings"], "mismatch_sgs": 1})
    assert k2_judge.v5_absolute("noise_L2", [_doc("noise_L2", rows, [], **sgs)])["passed"] is False
    no_sgs = _noise_meta(settings={**_noise_meta()["settings"], "preset_sgs_keys": []})
    assert k2_judge.v5_absolute("noise_L2", [_doc("noise_L2", rows, [], **no_sgs)])["missing"]
    loc = _noise_meta(r79_judgement={**_noise_meta()["r79_judgement"], "reference_all_false_loc": 1})
    assert k2_judge.v5_absolute("noise_L2", [_doc("noise_L2", rows, [], **loc)])["passed"] is False
    many = [{"key": f"n|{i}", "pass": i >= 20} for i in range(855)]
    assert k2_judge.v5_absolute("noise_L2", [_doc("noise_L2", many, [], **_noise_meta())])["passed"] is False


def test_regression_unmatched_is_a_record() -> None:
    keys = {"judged_sha256": k2_judge.REGRESSION_JUDGED_SHA256, "judged_n": 93,
            "record_sha256": k2_judge.REGRESSION_RECORD_SHA256, "record_n": 49}
    meta = {"r79_judgement": {"unmatched": 1, "errors": 0, "unmatched_keys": ["x"]}, "regression_keys": keys}
    rows = [{"key": f"r|{i}", "pass": True} for i in range(93)]
    assert k2_judge.v5_absolute("regression", [_doc("regression", rows, [], **meta)])["passed"] is True
    wrong = {**meta, "regression_keys": {**keys, "judged_sha256": "0" * 64}}
    assert k2_judge.v5_absolute("regression", [_doc("regression", rows, [], **wrong)])["passed"] is False


def test_error_value_rule() -> None:
    assert not k2_v5_flatten.has_error({"error": None})
    assert not k2_v5_flatten.has_error({"error": ""}) and not k2_v5_flatten.has_error({"error": []})
    assert k2_v5_flatten.has_error({"error": "boom"})
    assert k2_v5_flatten.error_rows({"results": [{"error": None, "runs": [{"error": "x"}]}]}) == 1


# --- E-5 / I-9 -------------------------------------------------------------------------------------------------
def _plant_aug(arm: str) -> dict:
    keys = k2_judge.AUG_OPTION_KEYS_BY_ARM[arm]
    values = k2_judge.AUG_RESOLVED_VALUES
    resolved = {"valve_open_eps_m_s": 0.00209243016 if arm == "AUG_eps" else 1e-6}
    for name in keys - {"valve_open_eps_m_s"}:
        resolved[name] = values[name]
    if "seal_fs_front_N" in keys:
        resolved["seal_fs_rear_scale"] = 0.8333
    if "pad_zeta_moving" in keys:
        resolved.update(cn_lock_N_s_m=[3.0e4] * 4, cn_moving_N_s_m=[1.0e5] * 4)
    options = {name: resolved.get(name, "chrono_l1") for name in keys}
    return {"preset": k2_judge.V3_DISS_PRESETS[arm], "options": options, "resolved": resolved}


@pytest.mark.parametrize("arm", k2_judge.V3_ARMS)
def test_rev3_values_per_arm(arm) -> None:
    assert k2_judge.aug_value_problems(arm, _plant_aug(arm)) == []


def test_rev3_value_mismatches() -> None:
    extra = _plant_aug("H0")
    extra["options"] = {"crawler_kt_rel": "chrono_l1"}
    assert k2_judge.aug_value_problems("H0", extra)
    rounded = _plant_aug("L1eq")
    rounded["resolved"]["crawler_kt_rel"] = 0.233093
    assert k2_judge.aug_value_problems("L1eq", rounded)
    eps = _plant_aug("AUG")
    eps["resolved"]["valve_open_eps_m_s"] = 0.00209243016
    assert k2_judge.aug_value_problems("AUG", eps)
    cn = _plant_aug("AUG")
    cn["resolved"]["cn_moving_N_s_m"] = [3.0e4] * 4
    assert k2_judge.aug_value_problems("AUG", cn)


def test_aug_row_identity() -> None:
    run = {"id": "c", "aug_arm": "AUG", "is_kplant": True,
           "k2": {"aug": {"arm": "AUG", "is_kplant": True, "preset": "aug", "case_id": "c",
                          "plant_aug": _plant_aug("AUG"), "valve_open_fraction_touch_to_lift": [0.1, 0.2, 0.0, 1.0]}}}
    assert k2_judge._aug_row_problems(run, "AUG") == []
    run["k2"]["aug"]["valve_open_fraction_touch_to_lift"] = [0.1, 0.2, float("nan"), 1.0]
    assert any("I-9" in p for p in k2_judge._aug_row_problems(run, "AUG"))


def test_aug_crc2_violations_stay_in_its_record(monkeypatch) -> None:
    """Rev6 3: E-5 / I-9 of the record arm AUG_crc2 do not reach the V-3 problems (G-B, grade)."""
    summary = {"bundle": "x", "expected": 273, "actual": 273, "pass": 273, "fail": 0, "not_judgeable": 0}
    monkeypatch.setattr(k2_judge, "seal_problems", lambda: [])
    monkeypatch.setattr(k2_judge, "f_d8_N", lambda: F_D8)
    monkeypatch.setattr(k2_judge, "_manifest_part",
                        lambda args, bundle: {"arms": {arm: {"off": [], "tcl": []} for arm in k2_judge.V3_ARMS}})
    monkeypatch.setattr(k2_judge, "_off_tcl_bundle", lambda cell, **kw: (
        {"summaries": {"off": dict(summary), "tcl": dict(summary)}, "sh": [], "dhat": {}}, [], [], []))
    monkeypatch.setattr(k2_judge, "keys_sha256", lambda keys: k2_judge.V3_KEYS_SHA256)
    monkeypatch.setattr(k2_judge, "_aug_problems", lambda files, arm: ["E-5 bad"] if arm == "AUG_crc2" else [])
    status, result = k2_judge.cmd_judge_v3(None)
    assert result["problems"] == [] and result["gate"]["G-B"] == "pass"
    assert result["arms"]["AUG_crc2"]["record_not_judgeable"] == ["E-5 bad", "E-5 bad"]
    monkeypatch.setattr(k2_judge, "_aug_problems", lambda files, arm: ["E-5 bad"] if arm == "AUG" else [])
    assert k2_judge.cmd_judge_v3(None)[1]["gate"]["G-B"] == "not_judgeable"


def test_options_off_and_chrono_options(tmp_path) -> None:
    path = _write(tmp_path, "v2.json", {"runs": [{"id": "a"}, {"id": "b", "aug_arm": "AUG"}]})
    assert len(k2_judge.options_off_problems([path], "V-2")) == 1
    shares = {"FL": 0.2, "FR": 0.1, "RL": 0.0, "RR": 0.3}
    l1 = {"moving_damping": True, "pad_zeta_moving": 0.1, "valve_open_fraction_touch_to_lift": shares}
    assert k2_judge.chrono_option_problems(l1, "L1") == []
    assert k2_judge.chrono_option_problems({**l1, "valve_open_fraction_touch_to_lift": None}, "L1")
    l2b = {"moving_damping": False, "pad_zeta_moving": None}
    assert k2_judge.chrono_option_problems(l2b, "L2b") == []
    assert k2_judge.chrono_option_problems(l1, "L2b")


# --- SH -------------------------------------------------------------------------------------------------------
def _chrono_row(name: str, k2_on: bool, **changes) -> dict:
    row = {"id": name, "engine": "L1" if "_L1_" in name else "L2b", "k2_on": k2_on, "false_latch": [],
           "cap": 0, "t_ready_s": 50.0, "has_h4": False, "sh1": [0, 0, 0, 0], "sh2": 1.0,
           "values": {"J1_N": 40e3, "J2_N": None}}
    row.update(changes)
    return row


def _chrono_rows(**tcl_changes) -> list[dict]:
    rows = []
    for name in k2_judge.CHRONO_ROWS:
        k2_on = name.endswith("_tcl")
        rows.append(_chrono_row(name, k2_on, **(tcl_changes if k2_on else {})))
    return rows


def test_v6_sh_clean_and_flags() -> None:
    assert k2_judge.chrono_sh(_chrono_rows(), F_D8)["flags"] == []
    flags = {f["flag"] for f in k2_judge.chrono_sh(_chrono_rows(sh2=2.0, t_ready_s=54.0, cap=1), F_D8)["flags"]}
    assert flags == {"SH-2", "SH-3", "SH-5"}
    rows = _chrono_rows()
    rows[1]["false_latch"] = ["FL@1.000"]  # an L1 K-2 row
    assert any(f.get("l1_false_latches") for f in k2_judge.chrono_sh(rows, F_D8)["flags"])
    low = {f["flag"] for f in k2_judge.chrono_sh(_chrono_rows(values={"J1_N": 16e3, "J2_N": None}), F_D8)["flags"]}
    assert {"SH-4", "SH-6"} <= low


def test_v6_sh_missing_is_flagged() -> None:
    rows = _chrono_rows()
    rows[1]["sh2"] = None
    rows[3]["t_ready_s"] = None
    result = k2_judge.chrono_sh(rows, F_D8)
    assert result["missing"]["SH-2"] == 1 and result["missing"]["SH-3"] == 1
    assert {"fewer_than_4_values"} <= {key for f in result["flags"] for key in f}


def test_harness_sh_missing_counts() -> None:
    k2_rows = [{"id": "a", "k1_on": False, "sh1": None, "cap": 0, "sh2": 0.1, "t_ready_s": None,
                "values": {"J1_N": 30e3}}]
    off_rows = [{"id": "a", "k1_on": False, "sh2": 0.3, "t_ready_s": 45.0, "values": {"J1_N": 30e3}}]
    block = k2_judge.sh_flags(k2_rows, off_rows, F_D8, "t")
    assert block["missing"]["SH-1"] == 1 and block["missing"]["SH-3"] == 1
    assert {f["flag"] for f in block["flags"] if "missing" in f} == {"SH-1", "SH-3"}


def test_harness_sh2_pairs_and_sh5_never_missing() -> None:
    """Rev6 2: SH-2 missing per pair, medians from complete pairs only; SH-5 has no missing."""
    k2_rows = [{"id": i, "k1_on": False, "sh1": [0] * 4, "cap": None, "sh2": value, "t_ready_s": 50.0,
                "values": {"J1_N": 30e3}} for i, value in enumerate((0.1, None, 5.0))]
    off_rows = [{"id": i, "k1_on": False, "sh2": value, "t_ready_s": 50.0, "values": {"J1_N": 30e3}}
                for i, value in enumerate((0.2, 0.3, None))]
    block = k2_judge.sh_flags(k2_rows, off_rows, F_D8, "t")
    assert block["missing"]["SH-2"] == 2 and block["missing"]["SH-5"] == 0
    assert block["sh2_medians"] == [0.1, 0.2]


# --- seals and self test --------------------------------------------------------------------------------------
def test_seal_check(tmp_path, monkeypatch) -> None:
    rules = tmp_path / "r.md"
    rules.write_bytes(b"rules\n")
    sha = hashlib.sha256(b"rules\n").hexdigest()
    seal = tmp_path / "r.sha256"
    seal.write_text(f"{sha}  r.md  sealed\n", encoding="utf-8")
    assert k2_judge._seal_problem(rules, seal, sha) is None
    assert k2_judge._seal_problem(rules, seal, "0" * 64)
    rules.write_bytes(b"changed\n")
    assert k2_judge._seal_problem(rules, seal, sha)
    assert k2_judge._seal_problem(tmp_path / "missing.md", seal, sha)
    assert len(k2_judge.SEALED_RULES) == 7 and k2_judge.SEALED_RULES[-1][2] == k2_judge.RULES_REV6_SHA256


def test_selftest_v5_stored(tmp_path) -> None:
    pytest.importorskip("scipy")
    result = k2_judge.selftest_v5_stored(k2_judge.STORED_ACCEPTANCE_DIR, k2_judge.STORED_PS7, tmp_path)
    assert result["ok"] is True, result["bundles"]
