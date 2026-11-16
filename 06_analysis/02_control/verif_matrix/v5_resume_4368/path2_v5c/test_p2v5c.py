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
         "lock_window_alignment": {"fallback_legs": {}, "n_late_fallback_by_leg": {}}}   # RD-10: no fallback leg
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
    """Four grid files <folder>/<setting>/<stem>.json. results[0] / [1] = family F keys FR / FL; in grid_r67_top
    their FS24 runs have four phases (0, 0.025, 0.05, 0.075), in grid_r67_main two (0, 0.05): 12 family F rows."""
    paths = {}
    (Path(folder) / setting).mkdir(parents=True, exist_ok=True)
    for stem in gr.STEMS:
        results = []
        for i in range(n // 6):
            key = ("screen|top|0.0|ready|FR", "screen|top|0.0|ready|FL")[i] if i < 2 else f"screen|bottom|0.0|level|K{i}"
            if stem == "grid_r67_top" and i < 2:
                plan = (("FS24", 0.0), ("FS24", 0.025), ("FS24", 0.05), ("FS24", 0.075), ("G4", 0.0), ("G4", 0.05))
            else:
                plan = (("FS24", 0.0), ("FS24", 0.05), ("RE1bF", 0.0), ("RE1bF", 0.05), ("G4", 0.0), ("G4", 0.05))
            runs = []
            for ev, off in plan:
                run = fast_run(offset_s=off, event=ev)
                if ev == "G4":
                    run.update(lifts={}, min_F_after_event_kN={"FL": 30.0, "FR": 30.0, "RL": 30.0, "RR": 30.0})
                runs.append(run)
            results.append({"key": key, "v5_setting": setting, "runs": runs})   # supplement 3-6: results[i] setting
        if mutate:
            mutate(stem, results)
        p = Path(folder) / setting / f"{stem}.json"
        p.write_text(json.dumps({"meta": {"spec": gr.FAMILY_F_EVENT and "rev. 67 (G1 / G2 / G7 reduced screen)",
                                          "v5_setting": setting}, "results": results}), "utf-8")
        paths[stem] = str(p)
    return paths


def ff_lines(vb_bad=0, v0_bad=0):
    """Synthetic h9_family_F.jsonl (supplement 4-5 fields): 2 keys x 16 phases x V0 / VB, the first ``*_bad``
    phases with Fmin_after_W false."""
    gates = {k: True for k in gr.gates_p2(fast_run(), CORE)}
    out = []
    for key in sorted(gr.FAMILY_F_KEYS):
        for s, nbad in (("VB", vb_bad), ("V0", v0_bad)):
            for i in range(16):
                g = dict(gates, Fmin_after_W=i >= nbad)
                out.append({"key": key, "setting": s, "offset_s": i * 0.00625, "event": "FS24", "gates": g,
                            "fault_events": [], "final_phase": "ready",
                            "controller_tag": "final_C4G2_P3_LAS_K1" if s == "VB" else "final_C4G2_LAS_K1"})
    return out


def write_ff(folder, lines, name="h9_family_F.jsonl"):
    p = Path(folder) / "ff" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n", "utf-8")
    return str(p)


class Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


REPO = cm.REPO_DEFAULT


class TestGridCmd(unittest.TestCase):
    def run_grid(self, mut_vb=None, mut_v0=None, n=192, family_f=None, ff_name="h9_family_F.jsonl", stored=True):
        with tempfile.TemporaryDirectory() as td:
            vb = write_grid(td, "VB", mut_vb, n)
            v0 = write_grid(td, "V0", mut_v0, n)
            st = write_grid(td, "stored", None, n) if stored else {}
            ff = write_ff(td, ff_lines() if family_f is None else family_f, ff_name)
            a = Args(vb=[f"{k}={v}" for k, v in vb.items()], v0_new=[f"{k}={v}" for k, v in v0.items()],
                     v0_stored=[f"{k}={v}" for k, v in st.items()], v0_sample=None, family_f=ff)
            return gr.cmd_grid(a, REPO, V5J, CORE)

    def test_v0_sample(self):
        with tempfile.TemporaryDirectory() as td:
            st = write_grid(td, "V0", None)
            sm = write_grid(td, "S", None)
            vb = write_grid(td, "VB", None)
            ff = write_ff(td, ff_lines())
            for stem, p in sm.items():   # give every run a hash; same as stored
                for q in (st[stem], p):
                    d = json.loads(Path(q).read_text("utf-8"))
                    for r in d["results"]:
                        for i, run in enumerate(r["runs"]):
                            run["commands_sha256"] = f"{r['key']}{i}"
                    Path(q).write_text(json.dumps(d), "utf-8")
            a = Args(vb=[f"{k}={v}" for k, v in vb.items()], v0_stored=[f"{k}={v}" for k, v in st.items()],
                     v0_sample=[f"{k}={v}" for k, v in sm.items()], v0_new=None, family_f=ff)
            body, s = gr.cmd_grid(a, REPO, V5J, CORE)
            self.assertEqual(body["v0_pair"]["sample"]["same"], 8)
            self.assertTrue(body["v0_pair"]["pair"].startswith("stored"))
            d = json.loads(Path(sm["grid_r69_top"]).read_text("utf-8"))
            d["results"][0]["runs"][0]["commands_sha256"] = "changed"
            Path(sm["grid_r69_top"]).write_text(json.dumps(d), "utf-8")
            body, s = gr.cmd_grid(a, REPO, V5J, CORE)
            self.assertEqual(body["v0_pair"]["sample"]["same"], 7)
            self.assertEqual(s, "undecidable")

    def test_family_F_rule(self):
        """Supplement 4-5: R-1..R-4 always computed from h9_family_F.jsonl; applied (pass = excluded, fail /
        undecidable = v5 H-10) only with a two-gate-only transition in the 12 family F rows; else a record."""
        def m(stem, res):
            if stem == "grid_r67_top":
                res[0]["runs"][0]["min_F_after_W_kN"] = {"FL": 5.0, "FR": 20.0, "RL": 20.0, "RR": 20.0}
        body, st = self.run_grid(mut_vb=m, family_f=ff_lines(4, 1))   # 4 <= 1 + 4, sum 8 <= 2 + 6
        fr = body["grid"]["family_F_rule"]
        self.assertEqual((fr["result"], fr["k"]["screen|top|0.0|ready|FL|VB"], body["grid"]["family_F_rows"]),
                         ("pass", 4, 12))
        self.assertEqual(st, "pass")
        body, st = self.run_grid(mut_vb=m, family_f=ff_lines(6, 1))   # 6 > 5
        self.assertEqual(body["grid"]["family_F_rule"]["result"], "fail")
        self.assertFalse(body["grid"]["family_F_rule"]["R1"]["screen|top|0.0|ready|FR"])
        self.assertIn("H-10", body["stop_codes"])
        bad = ff_lines(0, 0)
        del bad[3]["gates"]["U57_outside"]                              # a VB line field missing -> undecidable
        body, st = self.run_grid(mut_vb=m, family_f=bad)
        self.assertEqual(body["grid"]["family_F_rule"]["result"], "undecidable")
        self.assertIn("H-10", body["stop_codes"])                      # applicable + undecidable = v5 H-10
        body, st = self.run_grid(family_f=ff_lines(6, 1))              # not applicable: R fail is a record
        self.assertEqual((body["grid"]["family_F_rule"]["result"], st), ("fail", "pass"))
        r4 = ff_lines(0, 0)
        r4[0]["gates"]["U57_sum"] = False                              # VB FL phase 0: R-4 violation
        r4[1]["fault_events"] = ["FAULT_X"]                            # VB FL phase 1: R-3 violation
        fr = self.run_grid(family_f=r4)[0]["grid"]["family_F_rule"]
        self.assertEqual((fr["R3"]["ok"], fr["R4"]["ok"], fr["R4"]["violations"][0][2]), (False, False, ["U57_sum"]))

    def test_family_F_form_and_plate(self):
        """Supplement 4-5 form (64 cells) = S-15; supplement 4-3: setting missing = S-11, tag of another plate = S-2."""
        body, st = self.run_grid(family_f=ff_lines()[:-1])
        self.assertIn("S-15", body["stop_codes"])
        self.assertEqual(body["grid"]["family_F_rule"]["result"], "undecidable")
        x = ff_lines()
        x[0]["controller_tag"] = "final_C4G2_LAS_K1"                   # VB line with the 3-none tag
        body, st = self.run_grid(family_f=x)
        self.assertEqual(body["stop_codes"], ["S-2"])
        x = ff_lines()
        x[5]["setting"] = None
        body, st = self.run_grid(family_f=x)
        self.assertIn("S-11", body["stop_codes"])

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
        """Supplement 4-4: the family file and the four stored V0 grids must exist with their names (S-15)."""
        def m(stem, res):
            if stem == "grid_r67_top":
                res[0]["runs"][0]["min_F_after_W_kN"] = {"FL": 5.0, "FR": 20.0, "RL": 20.0, "RR": 20.0}
        body, st = self.run_grid(mut_vb=m)
        self.assertEqual(st, "pass")                                   # default family file passes R-1..R-4
        self.assertEqual(len(body["grid"]["family_F"]), 1)
        body, st = self.run_grid(ff_name="h9_family_F_copy.jsonl")
        self.assertEqual(body["stop_codes"], ["S-15"])
        body, st = self.run_grid(stored=False)
        self.assertEqual(body["stop_codes"], ["S-15"])
        self.assertFalse(body["inputs"]["supplement_4-4"]["ok"])
        with self.assertRaises(SystemExit), __import__("contextlib").redirect_stderr(__import__("io").StringIO()):
            gr.build_parser().parse_args(["--expect-head", "x", "grid", "--vb", "a=b"])   # --family-f required

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

    def test_r81_grid_tag_from_job(self):
        """rev8 R8-1 (user decision 19): a grid run without a tag reads the tag of its job record results[i];
        the run tag wins; neither -> J-P3 not applicable + S-2 (R8-2)."""
        def m(stem, res):
            for r in res:
                r["controller_tag"] = "final_C4G2_P3_LAS_K1"
                for run in r["runs"]:
                    run.pop("resume_k1", None)
        body, st = self.run_grid(mut_vb=m)
        self.assertNotIn("S-2", body["stop_codes"])
        self.assertEqual(body["inputs"]["vb"]["grid_r67_main"]["tags"], {"final_C4G2_P3_LAS_K1": 192})

        def m2(stem, res):
            m(stem, res)
            if stem == "grid_r67_main":
                res[0]["runs"][0]["controller_tag"] = "final_C4G2_LAS_K1"   # run tag wins (not 3)
                res[1]["runs"][0]["controller_tag"] = "final_C4G2_P3_LAS_K1"
                res[1].pop("controller_tag")
                res[2].pop("controller_tag")                                # neither for res[2] runs
        body, st = self.run_grid(mut_vb=m2)
        s2 = [s for s in body["grid"]["stops"] if s["code"] == "S-2"]
        self.assertEqual(len(s2), 1 + 5 + 6)   # res[0] run 0; res[1] runs 1..5; res[2] all six

    def test_r121_grid_t4h(self):
        """rev12 R12-1: a VB grid run that recorded t4h_file with no T4h folder -> S-2 (J-P3 not judged)."""
        def m(stem, res):
            if stem == "grid_r67_main":
                res[0]["runs"][0]["t4h_file"] = "x.npz"
        body, st = self.run_grid(mut_vb=m)
        self.assertEqual(st, "stop")
        self.assertIn("S-2", body["stop_codes"])
        self.assertEqual(body["R11-2_t4h"]["lookup"].get("not_found"), 1)


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

    def test_r112_t4h_lookup(self):
        """rev11 R11-2: convention folders of --h10 only; another folder only without them, at most one
        (else S-11, not judged); recorded t4h_file found 0 or 2+ times = S-2; found once = no R11-2 stop."""
        import argparse  # noqa: PLC0415
        import numpy as np  # noqa: PLC0415
        with tempfile.TemporaryDirectory() as td:
            h10 = Path(td) / "h10_reuse_rerun.jsonl"
            other = Path(td) / "other"
            other.mkdir()
            ns = argparse.Namespace(h9=str(Path(td) / "h9.jsonl"), h10=str(h10), overlap_ta=None)
            ns.t4h_root = [str(other), str(other) + "2"]               # two folders given
            body, st = s1.cmd_stage1(ns, REPO, V5J, CORE)
            self.assertEqual((st, body["stop_codes"]), ("stop", ["S-11"]))
            conv = Path(td) / "h10_reuse_rerun_t4h"
            conv.mkdir()
            ns.t4h_root = [str(other)]                                 # given while a convention folder exists
            body, st = s1.cmd_stage1(ns, REPO, V5J, CORE)
            self.assertEqual((st, body["stop_codes"]), ("stop", ["S-11"]))
            self.assertIn("input_error", body["R11-2_t4h_places"])
            places, perr = V5J.t4h_places([str(h10)], None)
            self.assertIsNone(perr)
            dirs = places[str(h10)]
            self.assertEqual(dirs, [conv])
            ln = line("R1", "VB", t4h_file="R1_VB.npz")
            v0 = line("R1", "V0")
            pk = V5J.pair_key(v0["job"])

            def r112(d):
                log = {}
                out = s1.judge_all(V5J, CORE, [ln], {pk: v0}, {}, None, d, "h10", log)
                f = out[("VB", pk)][1]
                return [s for s in f.stops if "R11-2" in s["why"]], log
            st2, log = r112(dirs)                                       # not found
            self.assertEqual(([s["code"] for s in st2], log), (["S-2"], {"not_found": 1}))
            np.savez(conv / "R1_VB.npz", rod_pressure_Pa=np.array([1.0e5]))
            st2, log = r112(dirs)                                       # found once
            self.assertEqual((st2, log), ([], {"ok": 1}))
            (Path(td) / "t4h").mkdir()
            np.savez(Path(td) / "t4h" / "R1_VB.npz", rod_pressure_Pa=np.array([1.0e5]))
            places, _ = V5J.t4h_places([str(h10)], None)
            st2, log = r112(places[str(h10)])                           # found in both convention folders
            self.assertEqual(([s["code"] for s in st2], log), (["S-2"], {"several": 1}))
            ln.pop("t4h_file")
            st2, log = r112(places[str(h10)])                           # no t4h_file: configuration (R3-C8)
            self.assertEqual((st2, log), ([], {"no_t4h_file": 1}))

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
                         [f"rev{n}.md" for n in range(3, 26)])            # R4 RD-2: rev3 ~ rev25 here
        r = {"items": r["items"][:10]}                                     # rev3 ~ rev12 checks below
        rev7 = r["items"][-6]
        self.assertEqual(rev7["want"], "e81f7d31779b0d69a140c9d90aa4684f3c9299e84aec6af06b13d48d58631502")
        self.assertEqual(rev7["seal_file_sha"], rev7["want"])
        rev8 = r["items"][-5]
        self.assertEqual(rev8["want"], "3ecafaaf33d84bb6f34a8cef5401771832a4999e4930f3644caff56eed640e56")
        self.assertEqual(rev8["seal_file_sha"], rev8["want"])
        self.assertEqual(rev8["sha256"], rev8["want"])
        rev9 = r["items"][-4]   # rev9 R9-8: file sha = code seal = .sha256 record
        self.assertEqual(rev9["want"], "4cf7843ce469df511d7b99c7236f0b245afae9fb4ba5ad903e1c2da823a59a6d")
        self.assertEqual(rev9["seal_file_sha"], rev9["want"])
        self.assertEqual(rev9["sha256"], rev9["want"])
        rev10 = r["items"][-3]   # rev10 R10-3: file sha = code seal = .sha256 record
        self.assertEqual(rev10["want"], "62a0bd8dd6644f78bf37d052e884061d8c14e1cc96e2babc72a6ac0618f12c29")
        self.assertEqual(rev10["seal_file_sha"], rev10["want"])
        self.assertEqual(rev10["sha256"], rev10["want"])
        rev11 = r["items"][-2]   # rev11 R11-7: file sha = code seal = .sha256 record
        self.assertEqual(rev11["want"], "9bac452470faf74f921aa7474b3dabad781dac1ba6c3493aff998e69e430617f")
        self.assertEqual(rev11["seal_file_sha"], rev11["want"])
        self.assertEqual(rev11["sha256"], rev11["want"])
        rev12 = r["items"][-1]   # rev12 R12-6: file sha = code seal = .sha256 record
        self.assertEqual(rev12["want"], "78f1f99b1bb27473d6e3317c58af195cc3b477829ca1439f390aeeaf32565140")
        self.assertEqual(rev12["seal_file_sha"], rev12["want"])
        self.assertEqual(rev12["sha256"], rev12["want"])

    def test_rev7_seal_mismatch_stops(self):
        """The last sealed file (rev12) differing from its seal is not ok (S-1 through run_main)."""
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

    def test_r97_k1_only_tags(self):
        """rev9 R9-7: LAS-b off + K1 on tags. final_C4G2_K1 (3 off) is not 3 on -> on a VB line J-P3 not
        applicable + S-2; final_C4G2_P3_K1 (3 on) is 3 on (tag decided by the base-tag function only)."""
        is_p3, _ = CORE.load_is_extend_start(REPO)
        self.assertFalse(is_p3("final_C4G2_K1"))
        self.assertTrue(is_p3("final_C4G2_P3_K1"))
        f = CORE.Findings()
        r = {"resume_k1": {"controller_tag": "final_C4G2_K1"},
             "hydraulics_record": {"m2_clipped_steps_post_lift": [0, 0, 0, 0]},
             "hydraulic_options": {"m2_law": "flow_limited_r5"}}
        jp = nz.run_checks("H-6", {"k": r}, CORE, V5J, is_p3, True, f)
        self.assertEqual(jp.get("not_applicable_tag"), 1)
        self.assertIn("S-2", [s["code"] for s in f.stops])

    def test_r121_jp3_rod_input(self):
        """rev12 R12-1 (Q-R12-1 = A): no t4h_file key = configuration; recorded and found once = T4h reading;
        recorded and found 0 / 2+ times or not a name = S-2 and J-P3 not judged (no configuration stand-in)."""
        import numpy as np  # noqa: PLC0415
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td) / "a", Path(td) / "b"
            a.mkdir()
            b.mkdir()
            f, log = CORE.Findings(), {}
            self.assertEqual(cm.jp3_rod_input(f, "w", {}, [a], V5J, True, log), (True, True))
            r = {"t4h_file": "k.npz"}
            self.assertEqual(cm.jp3_rod_input(f, "w", r, [a], V5J, True, log), (None, False))   # 0 files
            np.savez(a / "k.npz", rod_pressure_Pa=np.array([np.nan]))
            self.assertEqual(cm.jp3_rod_input(f, "w", r, [a], V5J, True, log), (False, True))   # T4h: no rod
            np.savez(b / "k.npz", rod_pressure_Pa=np.array([1.0]))
            self.assertEqual(cm.jp3_rod_input(f, "w", r, [a, b], V5J, True, log), (None, False))   # 2 files
            for bad in (None, 3, ""):   # user decision 24: key present, value None / not a string / empty
                self.assertEqual(cm.jp3_rod_input(f, "w", {"t4h_file": bad}, [a], V5J, True, log), (None, False))
            self.assertEqual([s["code"] for s in f.stops], ["S-2"] * 5)
            self.assertEqual(log, {"no_t4h_file": 1, "not_found": 1, "ok": 1, "several": 1, "bad_t4h_file": 3})
            # noise run_checks: an H-6 run that recorded a T4h file not found -> S-2, J-P3 not judged
            f = CORE.Findings()
            rr = {"t4h_file": "missing.npz", "resume_k1": {"controller_tag": "final_C4G2_P3_LAS_K1"},
                  "hydraulics_record": {"m2_clipped_steps_post_lift": [0, 0, 0, 0]},
                  "hydraulic_options": {"m2_law": "flow_limited_r5"}}
            is_p3, _ = CORE.load_is_extend_start(REPO)
            jp = nz.run_checks("H-6", {"k": rr}, CORE, V5J, is_p3, True, f, [a], {})
            self.assertEqual(jp, {"t4h_unresolved": 1})
            self.assertEqual([s["code"] for s in f.stops], ["S-2"])
            # stage1 strip: a judge_pair J-P3 result and its findings are dropped
            f = CORE.Findings()
            f.stop("J-P3-defect", "w", "x")
            f.stop("H-7", "w", "J-P3 ext_moving breach_reads [1, 0, 0, 0]")
            f.stop("H-7", "w", "n_late_fallback 1")
            f.undec("w", "J-P3: no T4h record")
            items = {"J-P3": {"result": "H-7"}}
            cm.strip_jp3(items, f)
            self.assertEqual(items["J-P3"]["result"], "t4h_unresolved")
            self.assertEqual([s["why"] for s in f.stops], ["n_late_fallback 1"])
            self.assertEqual(f.undecidable, [])

    def test_r123_git_at_start_required(self):
        """rev12 R12-3: noise needs --git-at-start (argparse error, exit 2)."""
        with self.assertRaises(SystemExit) as cx:
            nz.build_parser().parse_args(["noise", "--noise-vb", "a", "--noise-v0", "b", "--h6", "c",
                                          "--judge-dir", "d"])
        self.assertEqual(cx.exception.code, 2)

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


P3_TAG, V0_TAG = "final_C4G2_P3_LAS_K1", "final_C4G2_LAS_K1"


def ebc(br, **kw):
    return {"breach_reads": br, **kw}


def r79(tag, setting, br=None, lwa="ok", **kw):
    """Synthetic r79 record (H-6 / H-8 form) with an RD-10 J11 block."""
    r = {"key": kw.pop("key", "k"), "v5_setting": setting, "resume_k1": {"controller_tag": tag},
         "hydraulics_record": {"m2_clipped_steps_post_lift": [0, 0, 0, 0]},
         "hydraulic_options": {"m2_law": "flow_limited_r5"} if setting == "VB" else {}}
    if br is not None:
        r["hydraulics_record"]["extend_bound_check"] = ebc(br, **kw.pop("ebc_kw", {}))
    if lwa == "ok":
        r["lock_window_alignment"] = {"fallback_legs": {}, "n_late_fallback_by_leg": {}}
    elif isinstance(lwa, dict):
        r["lock_window_alignment"] = lwa
    r.update(kw)
    return r


class TestR4(unittest.TestCase):
    """R4 common block (e451f067...) and supplements 2-1 / 2-2 on synthetic inputs only."""

    def test_rd2_union(self):
        seals = CORE.check_seals(REPO)
        u = cm.rd2_union(seals)
        self.assertTrue(u["ok"], u)
        self.assertEqual((u["sheets"], u["want_sheets"]), (26, 26))
        self.assertEqual(len(cm.RD2_SEALS), 26)
        self.assertEqual(cm.RD2_SEALS[0][0], "06_analysis/02_control/verif_matrix/v5_resume_4368_rules.md")
        self.assertEqual(cm.RD2_SEALS[25][1], "c0b778fd3f53996a2caed37e373975afea591b3c798784843cb9e7eeaac6f233")
        # the imported list and this folder's list agree with RD-2 sheet by sheet
        for rel, sha, _s in cm.RD2_SEALS:
            if rel in seals["rules"]:
                self.assertEqual(seals["rules"][rel]["want"], sha)
        bad = copy.deepcopy(seals)
        first = next(iter(bad["rules"]))
        del bad["rules"][first]                                  # the original sheet not checked anywhere
        self.assertEqual(cm.rd2_union(bad)["missing"], [first])
        bad = copy.deepcopy(seals)
        bad["rules"][cm.RD2_SEALS[20][0]]["want"] = "0" * 64      # a sheet checked with another value
        self.assertFalse(cm.rd2_union(bad)["ok"])

    def test_head_check_s12(self):
        """RD-1 5: --expect-head is required; another commit = S-12, exit 2, nothing judged."""
        import contextlib  # noqa: PLC0415
        import io  # noqa: PLC0415
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            s1.build_parser().parse_args(["merge", "--part", "x.json"])
        for bad in ("0" * 40, "HEAD"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = s1.main(["--expect-head", bad, "merge", "--part", "nofile.json"])
            summary = json.loads(buf.getvalue().strip().splitlines()[-1])
            self.assertEqual((code, summary["status"], summary["stop_codes"]), (2, "stop", ["S-12"]))
        head = cm.git_head(REPO)
        self.assertTrue(CORE.head_check(REPO, head)["ok"])

    def test_rd7_rows_and_order(self):
        rec = {"hydraulics_record": {"extend_bound_check": ebc(
            [0, 2, 0, 1], min_gap_bar=[0.5, -0.75, 0.1, -0.01], first_breach_t_s=[None, 12.3, None, 20.0])}}
        rows = cm.jp3_rows("H-8", "f.json", "results[3]", rec, "key|a", "VB", CORE)
        self.assertEqual([(r["leg"], r["breach_reads"], r["min_gap_bar"], r["first_breach_t_s"]) for r in rows],
                         [("FR", 2, -0.75, 12.3), ("RR", 1, -0.01, 20.0)])
        e = rec["hydraulics_record"]["extend_bound_check"]
        e["min_gap_Pa"] = [0.0, -150000.0, 0.0, -1000.0]                       # supplement 3-3: not read
        e["min_gap_bar"][1], e["first_breach_t_s"][3] = float("inf"), float("nan")   # not finite -> null
        rows = cm.jp3_rows("H-8", "f.json", "results[3]", rec, "key|a", "VB", CORE)
        self.assertEqual([(r["min_gap_bar"], r["first_breach_t_s"]) for r in rows], [(None, 12.3), (-0.01, None)])
        del e["min_gap_bar"]
        self.assertEqual([r["min_gap_bar"] for r in cm.jp3_rows("H-8", "f", "p", rec, "k", "VB", CORE)], [None, None])
        mixed = [{"bundle": "H-10", "file": "a/h10_reuse_rerun.jsonl", "position": "line 1", "leg": "FL"},
                 {"bundle": "H-9", "file": "x/h9_stage1.jsonl", "position": "line 10", "leg": "FL"},
                 {"bundle": "H-9", "file": "x/h9_grid/grid_r67_main.json", "position": "results[10].runs[2]",
                  "leg": "RR"},
                 {"bundle": "H-9", "file": "x/h9_grid/grid_r67_main.json", "position": "results[9].runs[5]",
                  "leg": "FL"},
                 {"bundle": "H-6", "file": "z.json", "position": "results[2]", "leg": "RL"},
                 {"bundle": "H-9", "file": "x/h9_stage1.jsonl", "position": "line 9", "leg": "RL"},
                 {"bundle": "H-9", "file": "x/h9_stage1.jsonl", "position": "line 9", "leg": "FR"}]
        self.assertEqual([(r["bundle"], r["position"], r["leg"]) for r in cm.rd7_sort(mixed, CORE.bundle_key)],
                         [("H-6", "results[2]", "RL"), ("H-9", "results[9].runs[5]", "FL"),
                          ("H-9", "results[10].runs[2]", "RR"), ("H-9", "line 9", "FR"), ("H-9", "line 9", "RL"),
                          ("H-9", "line 10", "FL"), ("H-10", "line 1", "FL")])          # supplement 3-5: H-9 < H-10
        self.assertEqual(cm.rd7_markers([], [{"marker": "L-e"}]), ["L-e"])
        self.assertEqual(cm.rd7_markers([{"x": 1}], [{"marker": "H-7"}]), ["멈춤 H-7"])

    def test_rd13_lists(self):
        lists = cm.rd13_lists()
        self.assertEqual(sorted(lists), sorted(cm.RD7_BUNDLES))
        for b, v in lists.items():
            self.assertEqual(v["sha256"], cm.canon_sha(v["items"]))
            kinds = {x["구분"] for x in v["items"]}
            self.assertTrue(kinds <= {"등급 항목", "기록", "관문"}, kinds)
            names = [x["항목"] for x in v["items"]]
            self.assertEqual(len(names), len(set(names)), b)
            self.assertTrue(any(n.startswith("J-P3 ext_moving") for n in names))
            self.assertTrue(any(n.startswith("J11 실제 대체 다리") for n in names))

    # ---------------------------------------------------------------- grid (H-9, supplement 2-2)
    def run_grid(self, mut):
        return TestGridCmd.run_grid(self, mut_vb=mut)

    def test_grid_rd8_undecidable_never_pass(self):
        for br, kind in (([0, 0, 0], "format"), ([0, True, 0, 0], "format"), ([0, -1, 0, 0], "format")):
            def m(stem, res, br=br):
                if stem == "grid_r67_main":
                    res[3]["runs"][1]["hydraulics_record"]["extend_bound_check"]["breach_reads"] = br
            body, st = self.run_grid(m)
            self.assertEqual(st, "undecidable", br)
            self.assertEqual(body["R4"]["RD-8"]["H-9"][kind], 1)
            self.assertEqual(body["R4"]["RD-7"]["J-P3"]["H-9"], [])
            self.assertNotIn("H-7", body["stop_codes"])

        def m2(stem, res):
            if stem == "grid_r67_main":
                res[3]["runs"][1]["extend_bound_check"] = {"breach_reads": [0, 0, 0, 1]}   # top level differs
        body, st = self.run_grid(m2)
        self.assertEqual(st, "undecidable")
        self.assertEqual(body["R4"]["RD-8"]["H-9"]["top_level_mismatch"], 1)

    def test_grid_jp3_and_j11_rows(self):
        def m(stem, res):
            if stem == "grid_r69_top":
                res[3]["v5_setting"] = "VB"
                run = res[3]["runs"][1]
                run["hydraulics_record"]["extend_bound_check"] = ebc([0, 0, 4, 0], min_gap_bar=[1.0, 1.0, -0.5, 1.0],
                                                                     first_breach_t_s=[None, None, 33.3, None])
                res[1]["runs"][2]["lock_window_alignment"] = {"fallback_legs": {"RL": {"x": 1}},
                                                              "n_late_fallback_by_leg": {"RL": 2}}
        body, st = self.run_grid(m)
        self.assertEqual(st, "stop")
        jp, j11 = body["R4"]["RD-7"]["J-P3"]["H-9"], body["R4"]["RD-7"]["J11"]["H-9"]
        self.assertEqual([(r["position"], r["leg"], r["key"], r["setting"], r["breach_reads"], r["min_gap_bar"],
                           r["first_breach_t_s"]) for r in jp],
                         [("results[3].runs[1]", "RL", "screen|bottom|0.0|level|K3", "VB", 4, -0.5, 33.3)])
        self.assertEqual([(r["position"], r["leg"], r["n_late_fallback_by_leg"], r["marker"], r["setting"])
                          for r in j11], [("results[1].runs[2]", "RL", 2, "H-7", "VB")])
        self.assertEqual(body["R4"]["markers"]["H-9"], ["멈춤 H-7"])
        self.assertEqual(body["R4"]["RD-9"]["H-9"], {"p3_on": 768, "scanned": 768})

    def test_grid_j11_block_and_old_key(self):
        def m(stem, res):
            if stem == "grid_r67_top":
                del res[0]["runs"][0]["lock_window_alignment"]             # RD-10: undecidable on VB
                res[0]["runs"][1]["lock_window_alignment"]["n_late_fallback"] = 3   # old key: no stop any more
        body, st = self.run_grid(m)
        self.assertEqual(st, "undecidable")
        self.assertEqual(body["R4"]["RD-10"]["H-9"]["undecidable"], 1)
        self.assertNotIn("H-7", body["stop_codes"])

        def m3(stem, res):   # supplement 3-6: no results[i].v5_setting -> J11 undecidable (file meta VB not used)
            if stem == "grid_r67_top":
                del res[1]["v5_setting"]
                res[1]["runs"][0]["lock_window_alignment"] = {"fallback_legs": {"RL": {}},
                                                              "n_late_fallback_by_leg": {"RL": 2}}
        body, st = self.run_grid(m3)
        self.assertEqual(st, "undecidable")
        self.assertEqual(body["R4"]["RD-10"]["H-9"]["undecidable"], 6)
        self.assertEqual(body["R4"]["RD-7"]["J11"]["H-9"], [])
        self.assertNotIn("H-7", body["stop_codes"])

    # ---------------------------------------------------------------- noise (H-6 / H-8, supplement 2-1)
    def test_noise_lists_and_dg3_skip(self):
        is_p3, _ = CORE.load_is_extend_start(REPO)
        rd, f = cm.RdCounter(CORE.bundle_key), CORE.Findings()
        vb = {"k1": r79(P3_TAG, "VB", [0, 0, 0, 2], key="k1", ebc_kw={"min_gap_bar": [1, 1, 1, -0.2],
                                                                     "first_breach_t_s": [None, None, None, 7.0]}),
              "k2": r79(P3_TAG, "VB", [1, 0, 0, 0], key="k2"),                      # dg3 key: H-6 line
              "k3": r79(P3_TAG, "VB", [0, 0, 0, 0], key="k3",
                        lwa={"fallback_legs": ["RR"], "n_late_fallback_by_leg": {"RR": 1}})}
        nz.run_checks("noise_VB", vb, CORE, V5J, is_p3, True, f, [], {}, rd=rd, bundle="H-8",
                      rfile="r/h8_noise_VB.json", pos={"k1": 0, "k2": 1, "k3": 2}, skip={"k2"})
        jp, j11 = rd.as_dict(["H-8"])["RD-7"]["J-P3"]["H-8"], rd.as_dict(["H-8"])["RD-7"]["J11"]["H-8"]
        self.assertEqual([(r["position"], r["leg"], r["breach_reads"], r["min_gap_bar"]) for r in jp],
                         [("results[0]", "RR", 2, -0.2)])
        self.assertEqual([(r["position"], r["leg"], r["n_late_fallback_by_leg"]) for r in j11], [("results[2]", "RR", 1)])
        self.assertEqual(rd.p3["H-8"], 3)                                  # RD-9 counts k2 (file line) ...
        self.assertEqual(rd.as_dict(["H-8"])["RD-10"]["H-8"]["results"], {"pass": 1, "stop": 1})   # ... not judged
        self.assertFalse(any("k2" in s["where"] for s in f.stops))
        self.assertEqual(sorted(s["code"] for s in f.stops), ["H-7", "H-7"])
        # V0 file: J11 is a record (no stop), block missing = input missing, a 3-on tag on a V0 line = S-2
        rd, f = cm.RdCounter(CORE.bundle_key), CORE.Findings()
        v0 = {"a": r79(V0_TAG, "V0", key="a", lwa={"fallback_legs": {"FL": {}}, "n_late_fallback_by_leg": {"FL": 4}}),
              "b": r79(V0_TAG, "V0", key="b", lwa=None),
              "c": r79(P3_TAG, "V0", key="c")}
        nz.run_checks("noise_V0", v0, CORE, V5J, is_p3, False, f, rd=rd, bundle="H-8", rfile="r/v0.json",
                      pos={"a": 0, "b": 1, "c": 2})
        d = rd.as_dict(["H-8"])
        self.assertEqual(d["RD-7"]["J11"]["H-8"], [])
        self.assertEqual(d["RD-10"]["H-8"]["input_missing"], 1)
        self.assertEqual([s["code"] for s in f.stops], ["S-2"])
        # RD-8 format defect on an H-6 line: undecidable, counted, not a pass
        rd, f = cm.RdCounter(CORE.bundle_key), CORE.Findings()
        nz.run_checks("H-6", {"x": r79(P3_TAG, "VB", [0, 0, 1.0, 0], key="x")}, CORE, V5J, is_p3, True, f, [], {},
                      rd=rd, bundle="H-6", rfile="r/h6.json", pos={"x": 0})
        self.assertEqual(f.status(), "undecidable")
        self.assertEqual(rd.as_dict(["H-6"])["RD-8"]["H-6"]["format"], 1)

    def test_dg3_key_source(self):
        keys, rec = nz.dg3_keys(REPO, None, CORE)
        if (REPO / nz.DG3_KEY_SOURCE).is_file():
            self.assertTrue(rec["ok"], rec)
            self.assertEqual(len(keys), 135)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "dg3.json"
            p.write_text(json.dumps({"results": [{"key": "a"}]}), "utf-8")
            keys, rec = nz.dg3_keys(REPO, str(p), CORE)
            self.assertIsNone(keys)
            self.assertFalse(rec["ok"])

    # ---------------------------------------------------------------- stage1 (H-9 main / pressure_only, H-10)
    def test_stage1_rd_scan(self):
        def ev(case, st, **kw):   # event line: rod reading by configuration (R3-C8)
            return line(case, st, t_event_s=10.0, controller_tag=P3_TAG if st in ("VB", "LS1") else V0_TAG, **kw)
        ok_lwa = {"fallback_legs": {}, "n_late_fallback_by_leg": {}}
        h9 = [ev("R12", "V0", lock_window_alignment={"fallback_legs": {"RL": {}}, "n_late_fallback_by_leg": {"RL": 5}}),
              ev("R14", "V0"),
              {"job": {"case": "R12", "setting": "V0", "contact": "p"}, "controller_tag": V0_TAG}]
        h10 = [ev("R12", "VB", lock_window_alignment=ok_lwa,
                  hydraulics_record={"extend_bound_check": ebc([0, 0, 3, 0], min_gap_bar=[1, 1, -1.25, 1],
                                                               first_breach_t_s=[None, None, 12.3, None])}),
               None,
               ev("R14", "LS1", lock_window_alignment={"fallback_legs": {"FR": {}}, "n_late_fallback_by_leg": {"FR": 2}},
                  hydraulics_record={"extend_bound_check": ebc([0, 0, 0, 0])}),
               ev("S2", "VB", hydraulics_record={"extend_bound_check": ebc([1, 0, 0, 0], min_gap_Pa=[-2.0e5, 0, 0, 0],
                                                                          first_breach_t_s=[5.5, None, None, None])})]
        h10[3]["job"]["u9_metrics"] = True
        with tempfile.TemporaryDirectory() as td:
            p9, p10 = Path(td) / "h9_stage1.jsonl", Path(td) / "h10_reuse_rerun.jsonl"
            p9.write_text("\n".join(json.dumps(x) for x in h9) + "\n", "utf-8")
            p10.write_text("\n".join("" if x is None else json.dumps(x) for x in h10) + "\n", "utf-8")
            lines, nums = cm.read_jsonl_numbered(p10)
            self.assertEqual(nums, [1, 3, 4])                              # blank line counted (RD-7 3)
            import argparse  # noqa: PLC0415
            ns = argparse.Namespace(h9=str(p9), h10=str(p10), overlap_ta=None, t4h_root=None)
            body, st = s1.cmd_stage1(ns, REPO, V5J, CORE)
        r4 = body["R4"]
        jp = r4["RD-7"]["J-P3"]["H-10"]
        self.assertEqual([(r["position"], r["leg"], r["key"], r["setting"], r["breach_reads"], r["min_gap_bar"],
                           r["first_breach_t_s"]) for r in jp],
                         [("line 1", "RL", "R12", "VB", 3, -1.25, 12.3),
                          ("line 4", "FL", "S2", "VB", 1, None, 5.5)])          # no min_gap_bar -> null (3-3)
        self.assertEqual([(r["position"], r["leg"], r["n_late_fallback_by_leg"], r["marker"])
                          for r in r4["RD-7"]["J11"]["H-10"]], [("line 3", "FR", 2, "L-e")])
        self.assertEqual(r4["RD-7"]["J11"]["H-9"], [])                     # V0 J11 = record (rev16:103)
        self.assertEqual(r4["RD-10"]["H-9"]["input_missing"], 2)
        self.assertEqual(r4["RD-10"]["H-10"]["undecidable"], 1)            # U-9 VB line without the block
        self.assertEqual((r4["RD-9"]["H-9"]["p3_on"], r4["RD-9"]["H-10"]["p3_on"]), (0, 3))
        self.assertEqual(r4["markers"]["H-10"], ["L-e", "멈춤 H-7"])
        self.assertFalse(any("V0" in str(s["where"]) and s["code"] == "H-7" for s in body["H-9_stage1"]["stops"]))
        self.assertIn("L-e", body["H-10"]["stop_codes"])
        self.assertEqual(sorted(body["RD-13"]), ["H-10", "H-9"])
        # supplement 4-3: plate by job.setting (h10) / one plate (h9_stage1), tag compared
        self.assertEqual(r4["supplement_4-3_plates"], {"h10": {"VB": 2, "LS": 1}, "h9_stage1": {"none": 3}})
        self.assertNotIn("S-11", body["stop_codes"])
        f = CORE.Findings()
        self.assertIsNone(cm.plate_check(f, "w", None, P3_TAG))                     # field missing = S-11
        self.assertEqual(cm.plate_check(f, "w", "LS2", None), "LS")                  # tag missing = S-11
        self.assertEqual(cm.plate_check(f, "w", "V3", P3_TAG), "none")               # 3-none plate, 3-on tag = S-2
        self.assertEqual(cm.plate_check(f, "w", "VB", P3_TAG), "VB")                 # match
        self.assertEqual([s["code"] for s in f.stops], ["S-11", "S-11", "S-2"])

    def test_stage1_rd8_never_pass(self):
        """RD-8 through judge_pair (judged VB line) and through rd_scan (U-9 VB line): undecidable, counted."""
        is_p3, _ = CORE.load_is_extend_start(REPO)
        ok_lwa = {"fallback_legs": {}, "n_late_fallback_by_leg": {}}
        vb = line("R12", "VB", t_event_s=10.0, controller_tag=P3_TAG, lock_window_alignment=ok_lwa,
                  hydraulics_record={"extend_bound_check": ebc([0, 0, 0])})
        v0 = line("R12", "V0", t_event_s=10.0, controller_tag=V0_TAG)
        u9 = line("S2", "VB", t_event_s=10.0, controller_tag=P3_TAG, lock_window_alignment=ok_lwa,
                  hydraulics_record={"extend_bound_check": ebc([0, 0, "1", 0])})
        u9["job"]["u9_metrics"] = True
        by_id = {}
        out = s1.judge_all(V5J, CORE, [vb], {V5J.pair_key(v0["job"]): v0}, {}, is_p3, [], "h10", {}, by_id)
        items, f = out[("VB", V5J.pair_key(vb["job"]))]
        self.assertEqual(items["J-P3"]["result"], "undecidable")
        self.assertTrue(any(u["why"].startswith("J-P3: RD-8") for u in f.undecidable))
        rd, f10 = cm.RdCounter(CORE.bundle_key), CORE.Findings()
        s1.rd_scan(V5J, CORE, is_p3, rd, "H-10", "r/h10.jsonl", [vb, u9], [1, 2], by_id, [], f10, {})
        self.assertEqual(rd.as_dict(["H-10"])["RD-8"]["H-10"]["format"], 2)
        self.assertEqual(rd.as_dict(["H-10"])["RD-7"]["J-P3"]["H-10"], [])
        self.assertEqual(f10.status(), "undecidable")                      # the U-9 line, never a pass

    # ---------------------------------------------------------------- merge
    def test_merge(self):
        here = Path(s1.__file__).resolve().parent
        head = "a" * 40

        def part(tool, bundles, rows=(), p3=None):
            rd = cm.RdCounter(CORE.bundle_key)
            for b in bundles:
                for _ in range((p3 or {}).get(b, 1)):
                    rd.line(b, True)
            rd.jp3 += list(rows)
            return {"tool": tool, "tool_sha256": cm.sha256_file(here / tool),
                    "common_sha256": cm.sha256_file(here / "p2v5c_common.py"), "head_check": {"head": head},
                    "status": "pass", "R4": rd.as_dict(list(bundles)),
                    "RD-13": {b: cm.rd13_lists()[b] for b in bundles}}
        row = {"leg": "FL", "key": "k", "setting": "VB", "breach_reads": 1, "min_gap_bar": -0.1, "first_breach_t_s": 1.0}
        parts = [part("p2v5c_noise.py", ("H-6", "H-8")),
                 part("p2v5c_stage1.py", ("H-9", "H-10"),
                      [dict(row, bundle="H-9", file="r/h9_stage1.jsonl", position="line 5")], {"H-9": 0}),
                 part("p2v5c_grid.py", ("H-9",),
                      [dict(row, bundle="H-9", file="r/h9_grid/grid_r67_main.json", position="results[2].runs[1]")])]
        with tempfile.TemporaryDirectory() as td:
            paths = []
            for i, p in enumerate(parts):
                q = Path(td) / f"p{i}.json"
                q.write_text(json.dumps(p, ensure_ascii=False), "utf-8")
                paths.append(str(q))
            body, st = s1.cmd_merge(Args(part=paths, expect_head=head), REPO, V5J, CORE)
            self.assertEqual([r["position"] for r in body["RD-7"]["J-P3"]["H-9"]], ["results[2].runs[1]", "line 5"])
            self.assertEqual(body["RD-9"]["H-9"]["p3_on"], 1)               # stage1 0 + grid 1
            self.assertEqual(body["markers"]["H-9"], ["멈춤 H-7"])
            self.assertEqual(st, "stop")
            self.assertNotIn("S-8", body["stop_codes"])
            self.assertEqual(body["RD-7_sha256"]["J-P3"]["H-9"], cm.canon_sha(body["RD-7"]["J-P3"]["H-9"]))
            body, st = s1.cmd_merge(Args(part=paths[:2], expect_head=head), REPO, V5J, CORE)   # grid missing
            self.assertEqual((st, body["stop_codes"]), ("stop", ["S-11"]))
            body, st = s1.cmd_merge(Args(part=paths, expect_head="b" * 40), REPO, V5J, CORE)  # other HEAD
            self.assertIn("S-12", body["stop_codes"])
            parts[2]["R4"]["RD-9"]["H-9"]["p3_on"] = 0                      # H-9 sum 0 -> S-8
            Path(paths[2]).write_text(json.dumps(parts[2], ensure_ascii=False), "utf-8")
            body, st = s1.cmd_merge(Args(part=paths, expect_head=head), REPO, V5J, CORE)
            self.assertIn("S-8", body["stop_codes"])


if __name__ == "__main__":
    unittest.main()
