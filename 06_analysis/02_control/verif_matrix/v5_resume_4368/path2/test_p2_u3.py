"""Self-tests of p2_u3.py on synthetic records only."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("p2_u3", HERE / "p2_u3.py")
u3 = importlib.util.module_from_spec(spec)
sys.modules["p2_u3"] = u3
spec.loader.exec_module(u3)
IS_P3 = lambda t: t is not None and "_P3" in t   # noqa: E731 - stand-in for v5_options in unit tests


def rec(i, suite="slope", verdict="pass", setting="V0", tag=None, flags=(), rod=False, j_p3=None, fb=None, **kw):
    v5 = {"v5_setting": setting, "controller_tag": tag or u3.TAG[setting], "definition_sha256": "x", "code": {},
          "head_only_declared": suite != "g8", "has_rod_reading": rod,
          "j_p3": j_p3 or ("no_rod_reading" if setting == "VB" else "not_applicable"),
          "commands_sha256": f"{i:064x}"}
    if fb is not None:
        v5["rod_pressure_fallback_events"] = fb
    r = {"suite": suite, "id": f"H1|J1|B|top|k{i}", "verdict": verdict, "flags": list(flags), "t_ready_s": 50.0,
         "min_force_kN": 40.0, "max_stroke_mm": 500.0, "rut_ready_mm": 40.0, "att_end_deg": [0.01, -0.02], "v5": v5}
    r.update(kw)
    return r


def write(tmp_path, name, recs):
    p = tmp_path / name
    p.write_text(json.dumps({"meta": {}, "records": recs}), "utf-8")
    return str(p)


def test_grades():
    assert u3.grade_u3({"verdict": "pass", "flags": []}) == ("pass", None)
    assert u3.grade_u3({"verdict": "pass", "flags": ["P3-2_late_loc_reapproach"]})[0] == "flag"
    assert u3.grade_u3({"verdict": "stroke_limited_stop", "soil_stop": {"pass": True}})[0] == "safe_stop"
    assert u3.grade_u3({"verdict": "stroke_limited_stop", "soil_stop": {"pass": False}})[0] == "fail"
    assert u3.grade_u3({"verdict": "settle_check_fail"})[0] is None


def test_vb_unique_fail_and_table(tmp_path):
    v0 = write(tmp_path, "u3_slope_V0.json", [rec(1), rec(2, verdict="fail"), rec(3, verdict="fail")])
    vb = write(tmp_path, "u3_slope_VB.json", [rec(1, setting="VB", verdict="fail"), rec(2, setting="VB", verdict="fail"),
                                               rec(3, setting="VB")])
    out, f = u3.recount_u3([{"setting": "V0", "path": v0}, {"setting": "VB", "path": vb}], None, IS_P3)
    assert out["vb_unique_fail"] == ["slope|H1|J1|B|top|k1"]
    assert out["baseline_fail"] == ["slope|H1|J1|B|top|k2"] and out["vb_improve"] == ["slope|H1|J1|B|top|k3"]
    assert out["transition"]["pass"]["fail"] == 1 and out["sentence_VB"]["fail"] == 2
    codes = {s["code"] for s in f.stops}
    assert "G-5" in codes and "G-1" in codes          # counts are not the 1,114 of the rules
    assert "G-4" not in codes and "G-2" not in codes


def test_g8_rod_and_fallback(tmp_path):
    v0 = write(tmp_path, "a_V0.json", [rec(1, suite="g8")])
    vb = write(tmp_path, "a_VB.json", [rec(1, suite="g8", setting="VB", rod=True, j_p3="pass", fb=[{"t": 1}])])
    _, f = u3.recount_u3([{"setting": "V0", "path": v0}, {"setting": "VB", "path": vb}], None, IS_P3)
    assert "G-6" in {s["code"] for s in f.stops} and "G-4" not in {s["code"] for s in f.stops}
    vb = write(tmp_path, "b_VB.json", [rec(1, suite="g8", setting="VB", rod=False, j_p3="no_rod_reading", fb=0)])
    _, f = u3.recount_u3([{"setting": "V0", "path": v0}, {"setting": "VB", "path": vb}], None, IS_P3)
    assert "G-4" in {s["code"] for s in f.stops}


def test_tag_mix(tmp_path):
    v0 = write(tmp_path, "c_V0.json", [rec(1), rec(2, tag="final_C4G2_LAS")])
    _, f = u3.recount_u3([{"setting": "V0", "path": v0}], None, IS_P3)
    assert any(s["code"] == "G-2" and "tags in one file" in s["why"] for s in f.stops)


def test_d1_reuse(tmp_path):
    h1 = tmp_path / "h1.jsonl"
    line = {"job": {"d1": {"key": "D1|H-S-0|J1|T|flat|K1"}, "setting": "VB", "eps": 0.0},
            "controller_tag": u3.TAG["VB"], "commands_sha256": f"{7:064x}"}
    h1.write_text(json.dumps(line) + "\n", "utf-8")
    vb = write(tmp_path, "d_VB.json", [rec(7, setting="VB", reuse="d1", reuse_key="D1|H-S-0|J1|T|flat|K1")])
    out, f = u3.recount_u3([{"setting": "VB", "path": vb}], str(h1), IS_P3)
    assert out["d1_reuse"]["checked"] == 1 and not out["d1_reuse"]["problems"]


def b5(case, ctrl, h="a", lite=True, ov="pass"):
    tag = {"C2": u3.TAG["C2"], "ABL": u3.TAG["ABL"], "IND": "IND", "IND_LAS": "IND_LAS"}[ctrl]
    return {"case": case, "controller": ctrl, "lite_pass": lite, "official_verdict": ov, "crawler_liftoff_fail": False,
            "commands_sha256": h, "v5": {"controller_tag": tag}}


def test_u6(tmp_path):
    recs = [b5(f"c{i}", c, h=f"h{i}{c}") for i in range(3) for c in ("C2", "ABL", "IND")]
    recs[0]["official_verdict"] = "stroke_limited_stop"
    main = tmp_path / "u6_b5_main_VB.json"
    main.write_text(json.dumps({"records": recs}), "utf-8")
    il = [b5(f"c{i}", "IND_LAS", h=(f"h{i}IND" if i < 2 else "zz")) for i in range(3)]
    ilp = tmp_path / "u6_b5_main_VB_IND_LAS.json"
    ilp.write_text(json.dumps({"records": il}), "utf-8")
    out, f = u3.recount_u6([{"controller": None, "path": str(main)}, {"controller": "IND_LAS", "path": str(ilp)}], IS_P3)
    assert out["table"]["C2"]["safe_stop"] == 1 and out["IND_LAS_hash_equal_to_IND"] == 2
    assert out["judged_runs"] == 9
    codes = {s["code"] for s in f.stops}
    assert codes == {"G-1"}                            # 3 cases, rules say 242
