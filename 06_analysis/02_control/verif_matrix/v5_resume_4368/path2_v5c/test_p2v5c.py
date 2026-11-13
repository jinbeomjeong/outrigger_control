"""Synthetic self tests for the path2_v5c tools (no project results are read).

Run: conda run -n dynamics-dev python -I -B -m pytest -q -p no:cacheprovider <this file>
  or conda run -n dynamics-dev python -I -B <this file>   (unittest)
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p2v5c_common as cm  # noqa: E402
import p2v5c_grid as gr  # noqa: E402
import p2v5c_noise as nz  # noqa: E402
import p2v5c_stage1 as s1  # noqa: E402

P2 = cm.find_p2_dir()
V5J = cm.load_v5j(P2)
CORE = V5J.core


def fast_run(**kw):
    r = {"event": "FS24", "offset_s": 0.0, "pair_union_s": 0.5, "pair_last_touch_s": 1.0,
         "adj_lift_sum_W_s": 0.0, "adj_max_gap_W_mm": 0.0, "adj_lift_outside_W_s": 0.0,
         "min_F_after_W_kN": {"FL": 20.0, "FR": 20.0, "RL": 20.0, "RR": 20.0}, "fault_periods": 0,
         "fault_events": [], "final_phase": "ready", "att_end_deg": [0.01, -0.02], "twist": {"n_bundles": 0},
         "pass": True, "resume_k1": {"controller_tag": "final_C4G2_P3_LAS_K1"},
         "hydraulics_record": {"m2_clipped_steps_post_lift": [0, 0, 0, 0],
                               "extend_bound_check": {"breach_reads": [0, 0, 0, 0]}},
         "hydraulic_options": {"m2_law": "flow_limited_r5"},
         "lock_window_alignment": {"n_late_fallback": 0}}
    r.update(kw)
    r["gates"] = {k: v for k, v in gr.gates_p2(r, CORE).items()}
    return r


class TestCP(unittest.TestCase):
    def test_table(self):
        self.assertEqual(cm.cp_max_fail(835), 16)    # rev3 table
        self.assertEqual(cm.cp_max_fail(855), 17)
        self.assertEqual(cm.cp_max_fail(501), 8)
        for k, n in ((16, 835), (8, 501), (0, 25), (3, 25)):
            self.assertAlmostEqual(cm.cp_upper_beta(k, n), cm.cp_upper_root(k, n), places=9)
        self.assertAlmostEqual(cm.cp_upper_beta(16, 835), 0.02896, places=5)


class TestImports(unittest.TestCase):
    def test_pinned_sha(self):
        rec = cm.import_record(P2)
        self.assertTrue(rec["ok"], rec)


class TestGridGates(unittest.TestCase):
    def test_pass_and_thresholds(self):
        self.assertTrue(gr.run_pass(gr.gates_p2(fast_run(), CORE)))
        self.assertFalse(gr.gates_p2(fast_run(pair_union_s=1.8000001), CORE)["U832_pair_union"])
        self.assertTrue(gr.gates_p2(fast_run(pair_union_s=1.8 + 5e-10), CORE)["U832_pair_union"])  # 7.6 tol
        lo = {"FL": 9.4145, "FR": 20.0, "RL": 20.0, "RR": 20.0}
        self.assertFalse(gr.gates_p2(fast_run(min_F_after_W_kN=lo), CORE)["Fmin_after_W"])
        hi = dict(lo, FL=9.4146)
        self.assertTrue(gr.gates_p2(fast_run(min_F_after_W_kN=hi), CORE)["Fmin_after_W"])
        self.assertFalse(gr.gates_p2(fast_run(adj_lift_outside_W_s=0.001), CORE)["U57_outside"])
        self.assertFalse(gr.gates_p2(fast_run(twist={"n_bundles": 2}), CORE)["recurrence"])
        self.assertFalse(gr.gates_p2(fast_run(final_phase="fault"), CORE)["end_att"])

    def test_slow_and_missing(self):
        g4 = fast_run(event="G4", lifts={}, min_F_after_event_kN={"FL": 30.0, "FR": 30.0, "RL": 30.0, "RR": 30.0})
        g = gr.gates_p2(g4, CORE)
        self.assertTrue(gr.run_pass(g))
        g4["lifts"] = {"RR": {"sum_s": 0.1}}
        self.assertFalse(gr.gates_p2(g4, CORE)["no_lift"])
        r = fast_run()
        del r["pair_union_s"]
        self.assertIsNone(gr.run_pass(gr.gates_p2(r, CORE)))


def write_grid(folder, setting, mutate=None, n=192):
    paths = {}
    for stem in gr.STEMS:
        results = []
        for i in range(n // 6):
            key = "screen|top|0.0|ready|FR" if i == 0 else f"screen|bottom|0.0|level|K{i}"
            runs = [fast_run(offset_s=o) for o in (0.0, 0.05)] * 3
            for j, ev in enumerate(("FS24", "FS24", "RE1bF", "RE1bF", "G4", "G4")):
                runs[j] = copy.deepcopy(runs[j])
                runs[j]["event"] = ev
                if ev == "G4":
                    runs[j].update(lifts={}, min_F_after_event_kN={"FL": 30.0, "FR": 30.0, "RL": 30.0, "RR": 30.0})
            results.append({"key": key, "runs": runs})
        if mutate:
            mutate(stem, results)
        p = Path(folder) / f"{setting}_{stem}.json"
        p.write_text(json.dumps({"meta": {"spec": gr.FAMILY_F_EVENT and "rev. 67 (G1 / G2 / G7 reduced screen)",
                                          "v5_setting": setting}, "results": results}), "utf-8")
        paths[stem] = str(p)
    return paths


class Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


REPO = cm.REPO_DEFAULT


class TestGridCmd(unittest.TestCase):
    def run_grid(self, mut_vb=None, mut_v0=None, n=192, family_f=None):
        with tempfile.TemporaryDirectory() as td:
            vb = write_grid(td, "VB", mut_vb, n)
            v0 = write_grid(td, "V0", mut_v0, n)
            ff = None
            if family_f is not None:
                ff = str(Path(td) / "ff.jsonl")
                Path(ff).write_text("\n".join(json.dumps(x) for x in family_f) + "\n", "utf-8")
            a = Args(vb=[f"{k}={v}" for k, v in vb.items()], v0_new=[f"{k}={v}" for k, v in v0.items()],
                     v0_stored=None, v0_sample=None, family_f=ff)
            return gr.cmd_grid(a, REPO, V5J, CORE)

    def test_v0_sample(self):
        with tempfile.TemporaryDirectory() as td:
            st = write_grid(td, "V0", None)
            sm = write_grid(td, "S", None)
            vb = write_grid(td, "VB", None)
            for stem, p in sm.items():   # give every run a hash; same as stored
                for q in (st[stem], p):
                    d = json.loads(Path(q).read_text("utf-8"))
                    for r in d["results"]:
                        for i, run in enumerate(r["runs"]):
                            run["commands_sha256"] = f"{r['key']}{i}"
                    Path(q).write_text(json.dumps(d), "utf-8")
            a = Args(vb=[f"{k}={v}" for k, v in vb.items()], v0_stored=[f"{k}={v}" for k, v in st.items()],
                     v0_sample=[f"{k}={v}" for k, v in sm.items()], v0_new=None, family_f=None)
            body, s = gr.cmd_grid(a, REPO, V5J, CORE)
            self.assertEqual(body["v0_pair"]["sample"]["same"], 8)
            self.assertTrue(body["v0_pair"]["pair"].startswith("stored"))
            d = json.loads(Path(sm["grid_r69_top"]).read_text("utf-8"))
            d["results"][0]["runs"][0]["commands_sha256"] = "changed"
            Path(sm["grid_r69_top"]).write_text(json.dumps(d), "utf-8")
            body, s = gr.cmd_grid(a, REPO, V5J, CORE)
            self.assertEqual(body["v0_pair"]["sample"]["same"], 7)
            self.assertEqual(s, "undecidable")

    def _ff(self, vb_bad, v0_bad):
        lines = []
        for key in sorted(gr.FAMILY_F_KEYS):
            for s, nbad in (("VB", vb_bad), ("V0", v0_bad)):
                for i in range(16):
                    run = fast_run(offset_s=i * 0.00625)
                    if i < nbad:
                        run["min_F_after_W_kN"] = {"FL": 5.0, "FR": 20.0, "RL": 20.0, "RR": 20.0}
                    lines.append({"key": key, "setting": s, "run": run})
        return lines

    def test_family_F_rule(self):
        def m(stem, res):
            if stem == "grid_r67_top":
                res[0]["runs"][0]["min_F_after_W_kN"] = {"FL": 5.0, "FR": 20.0, "RL": 20.0, "RR": 20.0}
        body, st = self.run_grid(mut_vb=m, family_f=self._ff(4, 1))   # 4 <= 1 + 4, sum 8 <= 2 + 6
        self.assertEqual(body["grid"]["family_F_rule"]["result"], "pass")
        self.assertEqual(st, "pass")
        body, st = self.run_grid(mut_vb=m, family_f=self._ff(6, 1))   # 6 > 5
        self.assertEqual(body["grid"]["family_F_rule"]["result"], "fail")
        self.assertIn("H-10", body["stop_codes"])

    def test_all_pass(self):
        body, st = self.run_grid()
        self.assertEqual(st, "pass", body["grid"]["stops"] + body["grid"]["undecidable"])

    def test_transition_outside_family(self):
        def m(stem, res):
            if stem == "grid_r67_main":
                res[1]["runs"][0]["pair_union_s"] = 2.5
        body, st = self.run_grid(mut_vb=m)
        self.assertEqual(st, "stop")
        self.assertIn("H-10", body["stop_codes"])
        self.assertEqual(len(body["grid"]["pass_to_fail_outside_F"]), 1)

    def test_family_F_only(self):
        def m(stem, res):
            if stem == "grid_r67_top":
                res[0]["runs"][0]["min_F_after_W_kN"] = {"FL": 5.0, "FR": 20.0, "RL": 20.0, "RR": 20.0}
        body, st = self.run_grid(mut_vb=m)
        self.assertEqual(st, "undecidable")
        self.assertEqual(len(body["grid"]["family_F"]), 1)

    def test_fault_and_count(self):
        def m(stem, res):
            res[2]["runs"][2]["fault_periods"] = 3
        body, st = self.run_grid(mut_vb=m, mut_v0=m)
        self.assertEqual(st, "fail")
        body, st = self.run_grid(n=186)
        self.assertIn("S-15", body["stop_codes"])

    def test_jp3_breach(self):
        def m(stem, res):
            res[3]["runs"][1]["hydraulics_record"]["extend_bound_check"]["breach_reads"] = [0, 1, 0, 0]
        body, st = self.run_grid(mut_vb=m)
        self.assertIn("H-7", body["stop_codes"])

    def test_r82_non_p3_tag(self):
        """rev8 R8-2: a VB grid run with a non-3 tag -> S-2, J-P3 not counted as undecidable."""
        def m(stem, res):
            if stem == "grid_r67_main":
                res[0]["runs"][0]["resume_k1"] = {"controller_tag": "final_C4G2_LAS_K1"}
        body, st = self.run_grid(mut_vb=m)
        self.assertEqual(st, "stop")
        self.assertIn("S-2", body["stop_codes"])
        self.assertFalse(any("J-P3" in u["why"] for u in body["grid"]["undecidable"]))


def line(case, setting, eps=0.0, **kw):
    ln = {"job": {"case": case, "eps": eps, "setting": setting}, "harness_class": "pass", "final_phase": "ready",
          "t_event_s": None, "commands_sha256": f"{case}{setting}{eps}",
          "values": {"forces": {"after_liftoff": {"min_kN": 50.0}}, "times": {"t_first_ready_s": 60.0},
                     "attitude": {"max_abs_last_5s_deg": 0.01}, "pressure": {"max_moving_bar": 100.0}},
          "command_stats": {"n_rev": 4}, "events": []}
    ln.update(kw)
    return ln


class TestStage1Parts(unittest.TestCase):
    def test_kind(self):
        self.assertEqual(s1.kind_of(line("R6", "VB", 0.001)), "item8")
        self.assertEqual(s1.kind_of(line("R6", "VB", 0.002)), "main")
        self.assertEqual(s1.kind_of({"job": {"case": "R12", "setting": "VB", "timing": "x"}}), "overlap")
        self.assertEqual(s1.kind_of({"job": {"case": "R12", "setting": "V0", "contact": "p"}}), "pressure_only")
        self.assertEqual(s1.kind_of({"job": {"case": "S2", "setting": "VB", "u9_metrics": True}}), "u9")

    def test_counts_stop(self):
        f = CORE.Findings()
        s1.split_lines([line("R1", "V0")], [line("R1", "VB")], f)
        self.assertIn("S-15", f.as_dict()["stop_codes"])

    def _item8(self, vb_vals):
        main, it8 = [], []
        base = {"R6": 20.0, "R8": 30.0, "R9": 40.0}
        for s, vals in (("V0", base), ("VB", vb_vals)):
            for c, v in vals.items():
                for e in (0.0, 0.001, 0.002, 0.003):
                    ln = line(c, s, e)
                    ln["values"]["forces"]["after_liftoff"]["min_kN"] = v + e * 100
                    (it8 if e in (0.001, 0.003) else main).append(ln)
        f = CORE.Findings()
        return s1.item8_order(main, it8, CORE, f), f

    def test_item8(self):
        out, f = self._item8({"R6": 20.0, "R8": 30.0, "R9": 40.0})
        self.assertEqual(out["VB"]["result"], "order_kept")
        self.assertEqual(out["grade"], "pass")
        out, f = self._item8({"R6": 40.0, "R8": 30.0, "R9": 20.0})
        self.assertEqual(out["grade"], "fail")
        self.assertIn("H-11", f.as_dict()["stop_codes"])
        out, f = self._item8({"R6": 30.0, "R8": 30.1, "R9": 40.0})
        self.assertEqual(out["grade"], "flag")

    def test_f5(self):
        ln = line("S8", "VB", soil_stop_crawler={"at_stop_kN": 0.0, "threshold_kN": 3.801, "max_after_stop_kN": 3.9})
        self.assertEqual(s1.f5_clause(ln, CORE)["status"], "clause_fail")
        ln["soil_stop_crawler"]["max_after_stop_kN"] = None
        self.assertEqual(s1.f5_clause(ln, CORE)["status"], "ok")

    def test_p6_p7(self):
        main = [line("R1", "V0", commands_sha256="a"), line("R1", "L1", commands_sha256="a")]
        main += [line(f"C{i}", "L2", commands_sha256=f"h{i}") for i in range(8)]
        main += [line(f"C{i}", "L1", commands_sha256=f"h{i}") for i in range(8)]
        f = CORE.Findings()
        out = s1.check_p6_p7(main, V5J, f)
        self.assertEqual(out["P-6"]["differ"], 0)
        self.assertNotIn("P-6", f.as_dict()["stop_codes"])
        self.assertEqual(out["P-7"]["L1_equal_V0"], 1)
        main[-1]["commands_sha256"] = "zz"
        f = CORE.Findings()
        s1.check_p6_p7(main, V5J, f)
        self.assertIn("P-6", f.as_dict()["stop_codes"])

    def test_m2_law(self):
        f = CORE.Findings()
        a = line("R1", "VB", hydraulic_options={"m2_law": "flow_limited_r4"})
        b = line("R1", "V0", hydraulic_options={"m2_law": None})
        out = s1.m2_law_check([a, b], CORE, f, "t")
        self.assertEqual(out["bad"], 1)


class TestNoise(unittest.TestCase):
    def test_seedext(self):
        se, noise = {}, {}
        for inner in ("A", "B"):
            for s in range(25):
                k = f"L2|s{s}|{inner}"
                se[k] = {"inner": inner, "seed_index": s, "commands_sha256": f"{k}h"}
                if s < 5:
                    noise[k] = {"commands_sha256": f"{k}h"}
        f = CORE.Findings()
        out = nz.seedext("x", se, noise, f)
        self.assertEqual(out["seed0_4_same"], 10)
        self.assertEqual(f.status(), "pass")
        noise["L2|s3|A"]["commands_sha256"] = "other"
        f = CORE.Findings()
        nz.seedext("x", se, noise, f)
        self.assertIn("H-15", f.as_dict()["stop_codes"])
        del noise["L2|s3|A"]["commands_sha256"]
        f = CORE.Findings()
        out = nz.seedext("x", se, noise, f)
        self.assertEqual(f.status(), "pass")              # R3-E4: missing hash = record incomplete
        self.assertEqual(out["record_status"], "기록 불완전")

    def _rec(self, restart=True, w=0.005, mf=20.0, done=50.0, contact=44.0, base=True, final="ready",
             shape="t_done_s"):
        ev = [[40.0, "leg_reapproach_start:RL"], [contact, "leg_reapproach_contact:RL"], [46.0, "crawler_liftoff_confirmed"]]
        if restart:
            ev.append([40.5, "INFO_LOC_WINDOW_RESTART:RL"])
        rec = {"key": "k", "events": ev, "r79": {"t_off_s": 42.0, "t_loc_s": 46.0, "crawler_at_loc_over_W": w,
                                                 "min_true_F_after_off_kN": mf}}
        if base:   # rev7 R7-2: (a) t_done_s + phase_path, (b) timeline (g8)
            pp = [[10.0, "touch"], [30.0, "level"]] + ([[done, "done"]] if done is not None else [])
            if shape == "t_done_s":
                rec["base"] = {"t_done_s": done, "phase_path": pp, "t_loc_final_s": 46.0, "final_phase": final}
            else:
                rec["base"] = {"timeline": pp, "t_loc_final_s": 46.0, "final_phase": final}
        return rec

    @staticmethod
    def _row(**s4):
        rows = {g: {"ok": True} for g in nz.GATES}
        rows["S-4"] = {"ok": True, "fail_misfire_new": False, "miss": False, "recontact_new": False,
                       "loc_minus_off_s": 1.0, **s4}
        return {"key": "k", "rows": rows, "pass": rows["S-4"]["ok"]}

    def test_line_grade(self):
        self.assertEqual(nz.line_grade(self._rec(), self._row(), CORE)[0], "pass")
        late = dict(ok=False, gate_fail=True, loc_minus_off_s=4.0)
        self.assertEqual(nz.line_grade(self._rec(), self._row(**late), CORE)[0], "flag")       # 419.8 all true
        self.assertEqual(nz.line_grade(self._rec(done=45.0), self._row(**late), CORE)[0], "fail")  # c5 false
        self.assertEqual(nz.line_grade(self._rec(done=None, final="fault"), self._row(**late), CORE)[0],
                         "flag")                                    # no DONE + fault end = None (R7-2)
        self.assertEqual(nz.line_grade(self._rec(done=None), self._row(**late), CORE)[0],
                         "undecidable")                             # no DONE, not fault -> S-11 (R7-2)
        self.assertEqual(nz.line_grade(self._rec(shape="timeline"), self._row(**late), CORE)[0], "flag")
        self.assertEqual(nz.line_grade(self._rec(shape="timeline", done=45.0), self._row(**late), CORE)[0],
                         "fail")                                    # timeline shape, c5 false
        self.assertEqual(nz.line_grade(self._rec(restart=False), self._row(**late), CORE)[0], "fail")
        self.assertEqual(nz.line_grade(self._rec(mf=9.0), self._row(**late), CORE)[0], "fail")
        self.assertEqual(nz.line_grade(self._rec(base=False), self._row(**late), CORE)[0], "undecidable")
        self.assertEqual(nz.line_grade(self._rec(), self._row(ok=False, recontact_new=True), CORE)[0], "fail")
        self.assertEqual(nz.line_grade(self._rec(), self._row(ok=False, fail_misfire_new=True), CORE)[0], "fail")
        self.assertEqual(nz.line_grade(self._rec(), self._row(ok=False), CORE)[0], "fail")    # unexplained (R5-C2)
        g = nz.line_grade(self._rec(), self._row(ok=False, flags=["S4_baseline"]), CORE)
        self.assertEqual((g[0], g[1]), ("flag", ["S4_baseline"]))                            # existing FLAG tag
        r = self._row()
        r["rows"]["S-5"]["ok"] = False
        self.assertEqual(nz.line_grade(self._rec(), r, CORE)[0], "fail")
        self.assertEqual(nz.line_grade(self._rec(), None, CORE)[0], "undecidable")

    def test_phase_path_check(self):
        rec = self._rec()
        rec["base"]["t_done_s"] = 60.0           # not the first done of phase_path (50.0)
        f = CORE.Findings()
        nz.late_loc_conditions(rec, CORE, f)
        self.assertIn("S-11", f.as_dict()["stop_codes"])

    def test_first_done_rev7(self):
        """rev7 R7-2: first DONE by base shape; 5 ms match; DONE-less fault = None; strict '<' (Q-12)."""
        fd = nz.first_done
        pp = [[10.0, "touch"], [50.0, "done"], [60.0, "done"]]
        r = fd({"t_done_s": 50.004, "phase_path": pp, "final_phase": "ready"})
        self.assertTrue(r["ok"] and r["phase_path_ok"] and r["shape"] == "t_done_s")
        self.assertAlmostEqual(r["t_done_s"], 50.004)
        self.assertTrue(fd({"t_done_s": 50.005, "phase_path": pp})["ok"])           # 5 ms inclusive
        self.assertFalse(fd({"t_done_s": 50.006, "phase_path": pp})["ok"])          # > 5 ms -> S-11
        self.assertFalse(fd({"t_done_s": 50.1, "phase_path": pp})["ok"])            # one 0.1 s cycle apart
        self.assertFalse(fd({"t_done_s": None, "phase_path": pp, "final_phase": "fault"})["ok"])  # None + done
        self.assertFalse(fd({"t_done_s": 50.0, "final_phase": "ready"})["ok"])      # phase_path missing
        for ph in ("fault", "fault_reground"):
            r = fd({"t_done_s": None, "phase_path": [[10.0, "touch"]], "final_phase": ph})
            self.assertTrue(r["ok"])
            self.assertIsNone(r["t_done_s"])
            r = fd({"timeline": [[10.0, "touch"], [12.0, ph]], "final_phase": ph})
            self.assertTrue(r["ok"] and r["shape"] == "timeline")
            self.assertIsNone(r["t_done_s"])
        self.assertFalse(fd({"t_done_s": None, "phase_path": [], "final_phase": "ready"})["ok"])
        self.assertFalse(fd({"timeline": [[10.0, "touch"]], "final_phase": "ready"})["ok"])
        r = fd({"timeline": [[10.0, "touch"], [47.123, "done"], [70.0, "done"]], "final_phase": "ready"})
        self.assertEqual((r["ok"], r["shape"], r["t_done_s"]), (True, "timeline", 47.123))
        self.assertFalse(fd({"timeline": [], "final_phase": "ready"})["ok"])         # empty -> S-11
        self.assertFalse(fd({"final_phase": "ready"})["ok"])                         # no timeline -> S-11
        self.assertFalse(fd(None)["ok"])
        # S-11 is raised through late_loc_conditions; condition 5 strict: final LOC == first DONE -> False
        rec = self._rec(shape="timeline")
        del rec["base"]["timeline"]
        f = CORE.Findings()
        self.assertIsNone(nz.late_loc_conditions(rec, CORE, f)["c5"])
        self.assertIn("S-11", f.as_dict()["stop_codes"])
        rec = self._rec(done=46.0)                                                   # t_loc_final 46.0
        f = CORE.Findings()
        self.assertFalse(nz.late_loc_conditions(rec, CORE, f)["c5"])
        self.assertEqual(f.status(), "pass")

    def test_l1_gate(self):
        recs = {"a": {"level": "L1", "harness": "g6", "case_index": 1, "inner": "x", "v5_setting": "VB",
                      "r79": {"crawler_at_loc_over_W": 0.02}},
                "b": {"level": "L2", "harness": "g6", "case_index": 2, "inner": "y", "v5_setting": "V0"}}
        g = nz.l1_gate({"n_errors": 1}, recs, "VB", CORE)
        self.assertEqual((g["false_loc"], g["unmatched"], g["errors"], g["setting_mismatch"]), (1, 1, 1, 1))


class TestRev3(unittest.TestCase):
    def test_rev3_seal(self):
        r = cm.check_rev3(REPO)
        self.assertTrue(r["ok"], r)
        self.assertEqual([i["path"].rsplit("_", 1)[1] for i in r["items"]],
                         ["rev3.md", "rev4.md", "rev5.md", "rev6.md", "rev7.md", "rev8.md"])
        rev7 = r["items"][-2]
        self.assertEqual(rev7["want"], "e81f7d31779b0d69a140c9d90aa4684f3c9299e84aec6af06b13d48d58631502")
        self.assertEqual(rev7["seal_file_sha"], rev7["want"])
        rev8 = r["items"][-1]
        self.assertEqual(rev8["want"], "3ecafaaf33d84bb6f34a8cef5401771832a4999e4930f3644caff56eed640e56")
        self.assertEqual(rev8["seal_file_sha"], rev8["want"])
        self.assertEqual(rev8["sha256"], rev8["want"])

    def test_rev7_seal_mismatch_stops(self):
        """A rev8 (last) file differing from its seal is not ok (S-1 through run_main)."""
        with tempfile.TemporaryDirectory() as td:
            for rel, _w, srel in cm.LATER_RULES:
                for x in (rel, srel):
                    p = Path(td) / x
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes((REPO / x).read_bytes())
            p7 = Path(td) / cm.LATER_RULES[-1][0]
            p7.write_bytes(p7.read_bytes() + b"x")
            r = cm.check_rev3(td)
            self.assertFalse(r["ok"])
            self.assertEqual([i["ok"] for i in r["items"]], [True] * (len(cm.LATER_RULES) - 1) + [False])
            (Path(td) / cm.LATER_RULES[-1][2]).unlink()
            p7.write_bytes((REPO / cm.LATER_RULES[-1][0]).read_bytes())
            self.assertFalse(cm.check_rev3(td)["items"][-1]["ok"])     # .sha256 record missing
            sp = Path(td) / cm.LATER_RULES[-1][2]                     # .sha256 record with another value
            sp.write_text("0" * 64 + "  x.md\n", "utf-8")
            self.assertFalse(cm.check_rev3(td)["items"][-1]["ok"])
            sp.write_bytes((REPO / cm.LATER_RULES[-1][2]).read_bytes())
            self.assertTrue(cm.check_rev3(td)["ok"])

    def test_r82_jp3_tag_scope(self):
        """rev8 R8-2: a VB / LS line whose tag is not 3 on -> J-P3 not applicable (not undecidable) + S-2."""
        f = CORE.Findings()
        self.assertFalse(cm.jp3_tag_scope(f, "w", "pass", "VB"))
        self.assertFalse(cm.jp3_tag_scope(f, "w", "H-7", "VB"))
        self.assertEqual(f.status(), "pass")
        self.assertTrue(cm.jp3_tag_scope(f, "w", "not_applicable_tag", "VB"))
        self.assertEqual(f.status(), "stop")
        self.assertEqual([s["code"] for s in f.stops], ["S-2"])
        self.assertEqual(f.undecidable, [])
        # noise path: H-6 / noise_VB line with a non-3 tag
        f = CORE.Findings()
        r = {"resume_k1": {"controller_tag": "final_C4G2_LAS_K1"},
             "hydraulics_record": {"m2_clipped_steps_post_lift": [0, 0, 0, 0]},
             "hydraulic_options": {"m2_law": "flow_limited_r5"}}
        is_p3, _ = CORE.load_is_extend_start(REPO)
        jp = nz.run_checks("H-6", {"k": r}, CORE, V5J, is_p3, True, f)
        self.assertEqual(jp.get("not_applicable_tag"), 1)
        self.assertIn("S-2", [s["code"] for s in f.stops])
        self.assertFalse(any("J-P3" in u["why"] for u in f.undecidable))
        # V0 lines are not checked for J-P3
        f = CORE.Findings()
        nz.run_checks("noise_V0", {"k": r}, CORE, V5J, is_p3, False, f)
        self.assertNotIn("S-2", [s["code"] for s in f.stops])

    def test_sa4_and_guard(self):
        ln = line("S8", "VB", events=[[39.9, "WARN_LIFT_STROKE_LIMITED:FR"], [39.9, "FAULT_LIFT_STROKE_LIMIT:soil:FR"]],
                  soil_stop_crawler={"stop_t_s": 39.9})
        ln["values"]["times"]["t_first_ready_s"] = None
        ln["values"]["pressure"]["saturation_leg_chunks"] = 0
        r = s1.sa4_rest(ln, CORE)
        self.assertTrue(r["same_cycle_warn_fault_soil"])
        self.assertTrue(r["ready_0"] and r["fault_stroke_end_0"] and r["after_stop_Fmin"])
        self.assertIsNone(r["lift_after_stop_0"])         # R4-B1 field absent -> undecidable
        ln["values"]["sa4"] = {"lift_after_stop_ms": [0, 0, 0, 0]}
        self.assertTrue(s1.sa4_rest(ln, CORE)["lift_after_stop_0"])
        ln["values"]["sa4"] = {"lift_after_stop_ms": [0, 3, 0, 0]}
        self.assertFalse(s1.sa4_rest(ln, CORE)["lift_after_stop_0"])
        ln["values"]["sa4"]["F_min_after_stop_N"] = [20000.0, 9414.0, 30000.0, 30000.0]   # rev6 F-9
        r = s1.sa4_rest(ln, CORE)
        self.assertFalse(r["after_stop_Fmin"])
        self.assertEqual(r["after_stop_Fmin_source"], "F-9")
        del ln["values"]["sa4"]["F_min_after_stop_N"]
        ln["values"]["forces"]["after_liftoff"]["min_kN"] = 9.0      # below F_min, no F-9 -> undecidable
        self.assertIsNone(s1.sa4_rest(ln, CORE)["after_stop_Fmin"])
        g = line("S7", "VB", events=[[30.04, "WARN_LIFT_STROKE_LIMITED:FL,RR"]])
        self.assertEqual(s1.fl_guard_cycle(g), 300)
        self.assertIsNone(s1.fl_guard_cycle(line("S7", "VB", events=[])))
        self.assertEqual(s1.fl_guard_cycle({"job": {}}), "no_events")


if __name__ == "__main__":
    unittest.main()
