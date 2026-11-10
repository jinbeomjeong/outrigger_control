"""Synthetic tests for recount_rem.py (path 2). Designed from rules 9.1 #1-#11 situations,
not from the path-1 tests. Run: conda run -n dynamics-dev python -I test_recount_rem.py
"""
import ast
import copy
import importlib.util
import json
import math
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "recount_rem.py")
RULES = r"C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\las_k1_rules_adopt2.md"

spec = importlib.util.spec_from_file_location("recount_rem", TOOL)
rr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rr)

HEAD = "a" * 40
C2SHA = "c" * 64
ZCSHA = "d" * 64
FMOD = "f" * 64
VB_OPTS = ["--flow-eta-v", "0.85", "--flow-dp-comp-bar", "10", "--flow-dp-unload-bar", "20",
           "--flow-width-bar", "1", "--flow-law", "priority", "--valve-tau-s", "0.1", "--rod-release-force",
           "--lock-overlap-ratio", "0.02", "--lock-closing-delay-s", "0.05", "--lock-window-follows-plant",
           "--extend-start-tracked"]


def T(n):
    """Chrono-like float time of period n (small drift, like 45.10000000037363)."""
    return n / 10.0 + 3.7e-10


# ----------------------------------------------------------------------------- scenario
def default_scenario(key):
    """Uniform soft soil: soil start 332, L1 at 451 with dP 103, revoke 454, restart 455, re-LOC 465."""
    spec_ = rr.RULE_ROWS[key]
    forced = spec_["forced"] == "first"
    locs = [dict(n=451, nP=435, nS=332, r4=True, force_block=forced)]
    sc = dict(starts=[(332, "release")], locs=locs, revokes=[454], faults=[], phases_end="ready")
    sc["starts"].append((455, "release"))
    # re-LOC after revoke: struct zero (t_P = t_S = restart)
    if forced:
        sc["locs"].append(dict(n=465, nP=455, nS=455, r4=True))   # re-evaluated (no target)
    else:
        sc["locs"].append(dict(n=465, nP=455, nS=455, r4=False))  # target kept -> not R4
    return sc


def build_result(key, sc):
    spec_ = rr.RULE_ROWS[key]
    gate_on = spec_["gate"] == "on"
    tag = rr.TAG_V0 if spec_["v5"] == "V0" else rr.TAG_VB
    starts = [dict(t_s=T(n), push_base_stroke_m=0.37, source=src) for (n, src) in sc["starts"]]
    events = []
    for s in starts:
        events.append(dict(t_s=s["t_s"], name="soil_mode_start"))
    decisions = []
    target = False
    for L in sc["locs"]:
        t_loc = T(L["n"])
        events.append(dict(t_s=t_loc, name="crawler_liftoff_confirmed"))
        if L.get("e3c10"):
            events.append(dict(t_s=t_loc, name="INFO_LOC_CLEARANCE_MARGIN:30"))
            continue
        if L.get("no_decision"):
            continue
        t_P = None if L.get("nP") is None else T(L["nP"])
        if "t_P" in L:
            t_P = L["t_P"]
        if L.get("t_S", "auto") == "auto":
            prior = [s for s in starts if round(s["t_s"] / 0.1) < L["n"]]
            t_S = prior[-1]["t_s"] if prior else None
        else:
            t_S = L["t_S"]
        nP = None if t_P is None else round(t_P / 0.1)
        nS = None if t_S is None else round(t_S / 0.1)
        dP = None if (nP is None or nS is None) else nP - nS
        r4 = L["r4"]
        natural = r4 and (dP is None or dP <= 0)
        wb = r4 and (True if L.get("force_block") else natural)
        if "would_block" in L:
            wb = L["would_block"]
        applied = r4 and not (gate_on and wb)
        if "applied" in L:
            applied = L["applied"]
        decisions.append(dict(t_loc_s=t_loc, t_P_s=t_P, t_S_s=t_S, n_P=nP, n_S=nS, dP=dP,
                              r4_due_without_gate=r4, would_block=wb, applied=applied))
        ev_app = L.get("ev_applied", applied)
        ev_skip = L.get("ev_skipped", wb and not applied)
        if ev_app:
            events.append(dict(t_s=t_loc, name="INFO_LOC_FLAT_SOIL_MARGIN:80"))
        if ev_skip:
            events.append(dict(t_s=t_loc, name="INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order"))
    for n in sc["revokes"]:
        events.append(dict(t_s=T(n), name="INFO_LOC_REVOKED:2.5"))
    for (n, nm) in sc["faults"]:
        events.append(dict(t_s=T(n), name=nm))
    events.sort(key=lambda e: e["t_s"])
    phases = [dict(t_s=T(81), phase="check"), dict(t_s=T(128), phase="touch"), dict(t_s=T(315), phase="level")]
    if sc.get("phases_end") == "ready":
        phases += [dict(t_s=T(540), phase="done"), dict(t_s=T(541), phase="probe"), dict(t_s=T(897), phase="ready")]
    res = dict(
        action="level",
        args=dict(action="level", soil=spec_["soil"], level=spec_["level"], mass_scale=spec_["mass"],
                  k1_order_gate=spec_["gate"], k1_forced_block=spec_["forced"], expect_controller=tag,
                  case=spec_["case"], threads=4, **rr.FIXED_ARGS),
        placement=dict(mode="pcore", affinity_ok=True, power_throttling_off_ok=True, omp_wait_policy="PASSIVE"),
        meta=dict(num_threads_chrono=4), num_threads_chrono=4,
        hull_hook=dict(mode="fast", requested="fast", fallback_reason=None, dll_sha256=rr.DLL_SHA_EXPECTED),
        code_state=dict(git_at_start=dict(head=HEAD, dirty=[], clean=True),
                        files_at_start={
                            "outrigger_sim.control.c2": dict(path="03_src/outrigger_sim/control/c2.py", sha256=C2SHA),
                            "outrigger_sim.control.zero_calibration": dict(path="03_src/outrigger_sim/control/zero_calibration.py", sha256=ZCSHA)}),
        c2_setup=dict(k1_order_gate=spec_["gate"], expect_controller=dict(name=tag, ok=True, checks=[]),
                      k1_forced_block={"requested": spec_["forced"],
                                       "class": ("k1_forced_block.K1ForcedBlockC2Controller" if spec_["forced"] == "first"
                                                 else "outrigger_sim.control.c2.C2Controller"),
                                       "module_sha256": (FMOD if spec_["forced"] == "first" else None)}),
        controller_meta=dict(
            period_s=0.1,
            soil=dict(t_loc_s=T(sc["locs"][-1]["n"]) if sc["locs"] else None, mode_starts=starts,
                      restored_from=None, soil_mode_t_s=starts[-1]["t_s"] if starts else None),
            slope_clearance_margin=dict(order_gate=dict(enabled=gate_on, decisions=decisions)),
            loc_revoke=dict(settings=dict(keep_slope_margin_on_revoke=True, max_revokes=2),
                            revokes=len(sc["revokes"]), t_revoke_s=[T(n) for n in sc["revokes"]])),
        events=events, phases=phases,
        p3b={"P3-5_clearance_stroke": dict(s_motor_max_m=[0.47, 0.41, 0.40, 0.40])},
        p3b_ext=dict(crawler_gap=dict(grid_end_m=0.058, end_m=0.057)),
    )
    if spec_["forced"] == "first":
        L1 = next((d for d in decisions if d["r4_due_without_gate"]), None)
        calls = [dict(t_s=d["t_loc_s"], forced=(d is L1), result=d["would_block"], n_P=d["n_P"], n_S=d["n_S"])
                 for d in decisions if d["r4_due_without_gate"]]
        res["controller_meta"]["k1_forced_block"] = dict(
            mode="first", **{"class": "k1_forced_block.K1ForcedBlockC2Controller"}, module_sha256=FMOD,
            forced_t_loc_s=None if L1 is None else L1["t_loc_s"],
            forced_n_loc=None if L1 is None else round(L1["t_loc_s"] / 0.1),
            natural_blocked=None if L1 is None else (L1["dP"] is None or L1["dP"] <= 0),
            n_P=None if L1 is None else L1["n_P"], n_S=None if L1 is None else L1["n_S"],
            dP=None if L1 is None else L1["dP"], calls=calls)
    return res


def build_argv(key):
    s = rr.RULE_ROWS[key]
    tag = rr.TAG_V0 if s["v5"] == "V0" else rr.TAG_VB
    av = ["python.exe", "-I", "-X", "utf8", "-u", "run_S9.py", "level", "--soil", s["soil"], "--pad-variant", "dwg_rear250",
          "--level", s["level"], "--fs-kN", "4", "--threads", "4", "--duration", "120", "--pressure-grade", "normal",
          "--imu-grade", "ideal", "--seed", "20261026", "--expect-controller", tag, "--approved"]
    if s["v5"] == "VB":
        av += VB_OPTS
    if s["mass"] != 1.0:
        av += ["--mass-scale", str(s["mass"])]
    av += ["--k1-order-gate", s["gate"]]
    if s["forced"] == "first":
        av += ["--k1-forced-block", "first"]
    return av


def write_cmd_npz(folder, u_offset_at=None):
    import numpy as np
    t = np.array([8.1 + 0.1 * i for i in range(1120)])
    u = np.zeros((1120, 4))
    if u_offset_at is not None:
        u[u_offset_at:, 0] = 1e-4
    np.savez(os.path.join(folder, "controller_commands.npz"), t_s=t, issued_u_m_s=u)


class Batch:
    def __init__(self, root):
        self.root = root
        self.sc = {k: default_scenario(k) for k in rr.RULE_ROWS}
        self.missing = set()
        self.rc = {}
        self.result_patch = {}
        self.npz_offset = {}

    def write(self):
        cases = []
        for key, s in rr.RULE_ROWS.items():
            entry = dict(case=s["case"], rem_key=key, role=s["role"], argv=build_argv(key), rc=self.rc.get(key, 0),
                         pool="pcore", planned_pool="pcore", omp_wait_policy="PASSIVE",
                         hull_hook_effective=dict(mode="fast", fallback_reason=None),
                         code_at_launch=dict(files={"03_src/outrigger_sim/control/c2.py": C2SHA,
                                                    "03_src/outrigger_sim/control/zero_calibration.py": ZCSHA},
                                             git=dict(head=HEAD, dirty=[])))
            cases.append(entry)
            folder = os.path.join(self.root, s["case"])
            if key in self.missing:
                continue
            os.makedirs(folder, exist_ok=True)
            res = build_result(key, self.sc[key])
            if key in self.result_patch:
                self.result_patch[key](res)
            with open(os.path.join(folder, "result.json"), "w", encoding="utf-8") as f:
                json.dump(res, f)
            write_cmd_npz(folder, self.npz_offset.get(key))
        with open(os.path.join(self.root, "batch.json"), "w", encoding="utf-8") as f:
            json.dump(dict(batch="V5-LAS-K1-REM", mixed_hull_mode=False, cases=cases), f)
        return self.root


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rem_t_", dir=HERE)
        self.b = Batch(os.path.join(self.tmp, "batch"))
        os.makedirs(self.b.root)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, rules=RULES):
        self.b.write()
        out = os.path.join(self.tmp, "out.json")
        code = rr.main(["--batch", self.b.root, "--rules", rules, "--out", out])
        with open(out, encoding="utf-8") as f:
            return code, json.load(f)

    def set_pair(self, key, sc):
        """Apply the same scenario to a gateoff row and its gate-on pair (L1 identical)."""
        self.b.sc[key] = sc
        pair = {"R1": "R7", "R4": "R8"}.get(key)
        if pair:
            self.b.sc[pair] = copy.deepcopy(sc)


# ----------------------------------------------------------------------------- tests
class TestDefaults(Base):
    def test_all_pass(self):
        code, o = self.run_tool()
        self.assertEqual(o["stop_keys"], [], o["k_checks"])
        self.assertEqual(o["grade_provisional"], "통과")
        self.assertEqual(code, 0)
        for x in rr.GATEOFF_KEYS:
            self.assertEqual(o["rows"][x]["status"], "POS")
            self.assertEqual(o["rows"][x]["L1"]["dP"], 103)
        self.assertEqual(o["flag_counts"]["SHADOW_RELOC"], 6)
        self.assertEqual(o["flag_counts"]["SHADOW_RELOC_struct_zero"], 6)
        self.assertEqual(o["flag_counts"]["THIN_MARGIN"], 0)
        self.assertEqual(o["flag_counts"]["PAIR_DIVERGE"], 0)
        self.assertEqual(o["pairs"]["R7"]["k7"], True)
        self.assertEqual(o["pairs"]["R7"]["gateon_path"], "APPLIED_AT_L1")
        self.assertEqual(o["diag"]["F1"]["path_class"], "FORCED_R4_NEVER")
        self.assertTrue(o["diag"]["F1"]["FORCED_AT_L1"])
        self.assertTrue(o["diag"]["F1"]["FORCED_PAIR_L1"])
        self.assertTrue(o["diag"]["F1"]["valid"], o["diag"]["F1"]["invalid_reasons"])
        self.assertTrue(o["diag"]["F1"]["reeval"][0]["struct_zero"])
        self.assertIsNone(o["k10"])
        self.assertTrue(o["provisional"])

    def test_tool_imports_stdlib_only(self):
        with open(TOOL, encoding="utf-8") as fh:
            txt = fh.read()
        tree = ast.parse(txt)
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                mods.add((node.module or "").split(".")[0])
        allowed = {"__future__", "argparse", "datetime", "hashlib", "json", "math", "os", "sys", "traceback", "numpy"}
        self.assertTrue(mods <= allowed, mods - allowed)
        self.assertNotIn("import las_k1", txt)
        self.assertNotIn("outrigger_sim import", txt)


class Test01Statuses(Base):  # 9.1 #1
    def test_pos_nonpos_nor4_missing(self):
        self.b.sc["R2"] = dict(starts=[(332, "release")], locs=[dict(n=451, nP=327, nS=332, r4=True)],
                               revokes=[], faults=[], phases_end="ready")
        self.b.sc["R3"] = dict(starts=[(332, "release")], locs=[dict(n=451, nP=435, r4=False)],
                               revokes=[], faults=[], phases_end="ready")
        self.b.missing.add("R6")
        self.b.rc["R6"] = 1
        code, o = self.run_tool()
        st = {x: o["rows"][x]["status"] for x in rr.GATEOFF_KEYS}
        self.assertEqual(st, dict(R1="POS", R2="NONPOS", R3="NO_R4", R4="POS", R5="POS", R6="MISSING"))
        self.assertEqual(o["rows"]["R2"]["L1"]["dP"], -5)
        self.assertEqual(o["grade_provisional"], "미달")  # 미달 before 판정 불가
        self.assertIn("MEASURED_NONPOS", o["grade_reasons"])
        self.assertEqual(code, 1)


class Test02StructZero(Base):  # 9.1 #2
    def test_struct_zero_true_and_broken_window(self):
        sc = default_scenario("R2")
        sc["locs"][1] = dict(n=468, nP=458, nS=455, r4=False)  # window restarted later -> dP 3
        self.b.sc["R2"] = sc
        code, o = self.run_tool()
        d1 = o["rows"]["R1"]["decisions"][1]
        self.assertTrue(d1["post_revoke"])
        self.assertEqual(d1["restart_n"], 455)
        self.assertTrue(d1["struct_zero"])
        d2 = o["rows"]["R2"]["decisions"][1]
        self.assertEqual(d2["dP"], 3)
        self.assertFalse(d2["struct_zero"])
        self.assertEqual(o["flag_counts"]["SHADOW_RELOC"], 6)
        self.assertEqual(o["flag_counts"]["SHADOW_RELOC_struct_zero"], 5)


class Test03LateStruct(Base):  # 9.1 #3
    def test_late_struct_fails(self):
        self.b.sc["R3"] = dict(starts=[(332, "release"), (455, "release")],
                               locs=[dict(n=451, nP=435, r4=False), dict(n=465, nP=455, nS=455, r4=True)],
                               revokes=[454], faults=[], phases_end="ready")
        code, o = self.run_tool()
        r = o["rows"]["R3"]
        self.assertEqual(r["status"], "LATE_STRUCT")
        self.assertEqual(r["L1"]["n_loc"], 465)
        self.assertEqual(o["grade_provisional"], "미달")
        self.assertIn("STRUCT_ZERO", o["grade_reasons"])


class Test04GateoffTwoR4(Base):  # 9.1 #4
    def test_two_r4_in_gateoff_is_stop(self):
        sc = default_scenario("R2")
        sc["locs"][1] = dict(n=465, nP=460, nS=455, r4=True)
        self.b.sc["R2"] = sc
        code, o = self.run_tool()
        self.assertIn("K-6", o["stop_keys"])
        self.assertEqual(o["grade_provisional"], "stop")
        self.assertEqual(code, 2)


class Test05PairUlp(Base):  # 9.1 #5
    def test_one_ulp_pair_is_stop(self):
        def patch(res):
            d = res["controller_meta"]["slope_clearance_margin"]["order_gate"]["decisions"][0]
            d["t_P_s"] = math.nextafter(d["t_P_s"], math.inf)
        self.b.result_patch["R7"] = patch
        code, o = self.run_tool()
        self.assertFalse(o["pairs"]["R7"]["k7"])
        self.assertIn("K-7", o["stop_keys"])
        self.assertEqual(code, 2)


class Test06GateonNever(Base):  # 9.1 #6
    def test_gateon_r4_never_path(self):
        sc = default_scenario("R1")
        sc["locs"][0] = dict(n=451, nP=329, nS=332, r4=True)  # dP -3
        self.set_pair("R1", sc)
        on = copy.deepcopy(sc)
        on["locs"][1] = dict(n=465, nP=455, nS=455, r4=True)  # re-evaluated, struct zero -> blocked again
        self.b.sc["R7"] = on
        code, o = self.run_tool()
        self.assertEqual(o["rows"]["R1"]["status"], "NONPOS")
        self.assertTrue(o["pairs"]["R7"]["k7"])
        self.assertEqual(o["pairs"]["R7"]["gateon_path"], "R4_NEVER")
        seq = o["pairs"]["R7"]["gateon_r4_sequence"]
        self.assertEqual(len(seq), 2)
        self.assertTrue(seq[1]["struct_zero"])
        self.assertEqual(o["flag_counts"]["GATEON_PATH"], 1)
        self.assertEqual(o["grade_provisional"], "미달")
        self.assertEqual(o["stop_keys"], [])


class Test07SkippedNotApplied(Base):  # 9.1 #7
    def test_exact_names(self):
        self.assertNotEqual(rr.base_name("INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order"), rr.EV_FLAT)
        self.assertEqual(rr.base_name("INFO_LOC_FLAT_SOIL_MARGIN:80"), rr.EV_FLAT)

    def test_skip_event_is_not_application(self):
        # gate-on L1 says applied but only a SKIPPED:order event exists -> K-8 (e) false -> stop
        sc = copy.deepcopy(self.b.sc["R7"])
        sc["locs"][0]["ev_applied"] = False
        sc["locs"][0]["ev_skipped"] = True
        self.b.sc["R7"] = sc
        code, o = self.run_tool()
        d = o["rows"]["R7"]["decisions"][0]
        self.assertEqual(d["ev_applied"], 0)
        self.assertEqual(d["ev_skipped_order"], 1)
        self.assertIn("K-8", o["stop_keys"])
        self.assertFalse(o["pairs"]["R7"]["cond3"])


class Test08SamePeriodStart(Base):  # 9.1 #8
    def test_same_period_start_not_used(self):
        for key in ("R2",):
            sc = default_scenario(key)
            sc["starts"].insert(1, (451, "release"))  # a start in the LOC period
            self.b.sc[key] = sc
        code, o = self.run_tool()
        d = o["rows"]["R2"]["decisions"][0]
        self.assertEqual(d["n_S"], 332)
        self.assertEqual(o["stop_keys"], [], o["k_checks"]["K-8"]["failures_judge_scope"])

    def test_same_period_start_in_tS_is_stop(self):
        sc = default_scenario("R2")
        sc["starts"].insert(1, (451, "release"))
        sc["locs"][0]["t_S"] = T(451)
        self.b.sc["R2"] = sc
        code, o = self.run_tool()
        self.assertIn("K-8", o["stop_keys"])


class Test09Undecidable(Base):  # 9.1 #9
    def _nor4(self, key):
        sc = dict(starts=[(332, "release")], locs=[dict(n=451, nP=435, r4=False)], revokes=[], faults=[], phases_end="ready")
        self.set_pair(key, sc) if key in ("R1", "R4") else self.b.sc.__setitem__(key, sc)

    def test_three_pos(self):
        for x in ("R4", "R5", "R6"):
            self._nor4(x)
        code, o = self.run_tool()
        self.assertEqual(o["grade_provisional"], "판정 불가")
        self.assertTrue(any("POS 3" in r for r in o["grade_reasons"]))
        self.assertTrue(o["pairs"]["R8"]["k7"])  # both NO_R4, same first LOC

    def test_r4_r5_nor4(self):
        for x in ("R4", "R5"):
            self._nor4(x)
        code, o = self.run_tool()
        self.assertEqual(o["conditions"]["1_pos_count"], 4)
        self.assertEqual(o["grade_provisional"], "판정 불가")
        self.assertIn("R4 and R5 both NO_R4", o["grade_reasons"])


class Test10Rounding(Base):  # 9.1 #10
    def test_round(self):
        self.assertEqual(rr.per(34.95), 350)
        self.assertEqual(rr.per(34.85), 348)
        self.assertEqual(rr.per(None), None)


class Test11Forced(Base):  # 9.1 #11 + user decision (fourth class)
    def test_classes(self):
        # F1 default: FORCED_R4_NEVER. F2: no revoke.
        self.b.sc["F2"] = dict(starts=[(333, "release")], locs=[dict(n=553, nP=537, nS=333, r4=True, force_block=True)],
                               revokes=[], faults=[], phases_end="ready")
        # R4/R8 match F2 L1 so FORCED_PAIR_L1 holds
        sc4 = dict(starts=[(333, "release")], locs=[dict(n=553, nP=537, nS=333, r4=True)], revokes=[], faults=[], phases_end="ready")
        self.set_pair("R4", sc4)
        code, o = self.run_tool()
        self.assertEqual(o["diag"]["F1"]["path_class"], "FORCED_R4_NEVER")
        self.assertEqual(o["diag"]["F2"]["path_class"], "FORCED_NO_REVOKE")
        self.assertTrue(o["diag"]["F2"]["FORCED_PAIR_L1"])
        self.assertEqual(o["grade_provisional"], "통과")
        self.assertEqual(code, 0)

    def test_late_and_revoked_no_reeval(self):
        f1 = default_scenario("F1")
        f1["locs"][1] = dict(n=470, nP=462, nS=455, r4=True)  # dP 7 -> applied late
        self.b.sc["F1"] = f1
        f2 = default_scenario("F2")
        f2["locs"] = f2["locs"][:1]  # revoke, then no further LOC
        self.b.sc["F2"] = f2
        code, o = self.run_tool()
        self.assertEqual(o["diag"]["F1"]["path_class"], "FORCED_R4_LATE")
        self.assertEqual(o["diag"]["F1"]["late_applied"], dict(n_loc=470, dP=7))
        self.assertEqual(o["diag"]["F2"]["path_class"], "FORCED_REVOKED_NO_REEVAL")
        self.assertEqual(o["grade_provisional"], "통과")

    def test_missing_diag_does_not_change_grade(self):
        self.b.missing |= {"F1", "F2"}
        self.b.rc.update(F1=1, F2=1)
        code, o = self.run_tool()
        self.assertEqual(o["grade_provisional"], "통과")
        self.assertEqual(code, 0)
        self.assertIsNone(o["diag"]["F1"]["path_class"])

    def test_invalid_diag_identity_does_not_stop(self):
        def patch(res):
            res["controller_meta"]["k1_forced_block"]["calls"].append(dict(t_s=99.0, forced=True, result=True))
            res["hull_hook"]["mode"] = "off"
        self.b.result_patch["F1"] = patch
        code, o = self.run_tool()
        self.assertFalse(o["diag"]["F1"]["valid"])
        self.assertEqual(o["stop_keys"], [])
        self.assertEqual(o["grade_provisional"], "통과")

    def test_forced_meta_in_judge_row_is_stop(self):
        def patch(res):
            res["controller_meta"]["k1_forced_block"] = dict(mode="first")
        self.b.result_patch["R2"] = patch
        code, o = self.run_tool()
        self.assertIn("K-6", o["stop_keys"])
        self.assertEqual(code, 2)


class TestUserDecisions(Base):
    def test_k7_gateon_fault_before_L1_is_partial(self):
        self.b.sc["R7"] = dict(starts=[(332, "release")], locs=[], revokes=[], faults=[(440, "FAULT_LIFT_STROKE_LIMIT:soil")],
                               phases_end=None)
        code, o = self.run_tool()
        self.assertIsNone(o["pairs"]["R7"]["k7"])
        self.assertFalse(o["pairs"]["R7"]["cond3"])
        self.assertEqual(o["stop_keys"], [])
        self.assertEqual(o["grade_provisional"], "부분 통과")
        self.assertEqual(code, 1)

    def test_k7_gateon_no_r4_without_fault_is_stop(self):
        self.b.sc["R7"] = dict(starts=[(332, "release")], locs=[dict(n=451, nP=435, r4=False)], revokes=[], faults=[],
                               phases_end="ready")
        code, o = self.run_tool()
        self.assertIn("K-7", o["stop_keys"])

    def test_pre_soil_loc_is_stop(self):
        sc = default_scenario("R2")
        sc["locs"].insert(0, dict(n=300, nP=290, r4=False))  # LOC before soil-mode start, t_S None
        self.b.sc["R2"] = sc
        code, o = self.run_tool()
        self.assertIn("K-8", o["stop_keys"])

    def test_gateoff_missing_gateon_partial_vs_undecidable(self):
        self.b.missing.add("R8")
        self.b.rc["R8"] = 1
        code, o = self.run_tool()
        self.assertEqual(o["grade_provisional"], "부분 통과")


class TestFlags(Base):
    def test_thin_margin_and_pair_diverge(self):
        sc = default_scenario("R1")
        sc["locs"][0] = dict(n=451, nP=342, nS=332, r4=True)  # dP 10
        self.set_pair("R1", sc)
        self.b.npz_offset["R7"] = 300
        code, o = self.run_tool()
        self.assertEqual(o["flags"]["THIN_MARGIN"], ["R1"])
        self.assertEqual(o["flag_counts"]["PAIR_DIVERGE"], 1)
        self.assertEqual(o["flags"]["PAIR_DIVERGE"][0]["first_diff_n"], round((8.1 + 0.1 * 300) / 0.1))
        self.assertEqual(o["grade_provisional"], "통과")

    def test_late_r4_pos(self):
        sc = dict(starts=[(332, "release"), (455, "release")],
                  locs=[dict(n=451, nP=435, r4=False), dict(n=480, nP=470, nS=455, r4=True)],
                  revokes=[454], faults=[], phases_end="ready")
        self.b.sc["R2"] = sc
        code, o = self.run_tool()
        self.assertEqual(o["rows"]["R2"]["status"], "POS")
        self.assertEqual(o["flags"]["LATE_R4"], ["R2"])


class TestIdentity(Base):
    def test_rules_sha_mismatch_is_stop(self):
        d = os.path.join(self.tmp, "rules")
        os.makedirs(d)
        p = os.path.join(d, "las_k1_rules_adopt2.md")
        shutil.copyfile(RULES, p)
        shutil.copyfile(os.path.splitext(RULES)[0] + ".sha256", os.path.splitext(p)[0] + ".sha256")
        with open(p, "ab") as f:
            f.write(b"\n")
        code, o = self.run_tool(rules=p)
        self.assertIn("K-0", o["stop_keys"])

    def test_argv_pair_diff(self):
        orig = build_argv

        def patched(key):
            av = orig(key)
            if key == "R7":
                av = [("130" if t == "120" else t) for t in av]
            return av
        globals()["build_argv"] = patched
        try:
            code, o = self.run_tool()
        finally:
            globals()["build_argv"] = orig
        self.assertIn("K-5", o["stop_keys"])

    def test_v0_row_with_v5_option_is_stop(self):
        orig = build_argv

        def patched(key):
            av = orig(key)
            if key == "R5":
                av = av + ["--valve-tau-s", "0.1"]
            return av
        globals()["build_argv"] = patched
        try:
            code, o = self.run_tool()
        finally:
            globals()["build_argv"] = orig
        self.assertIn("K-5", o["stop_keys"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
