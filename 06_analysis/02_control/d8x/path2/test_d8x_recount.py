"""Synthetic tests of d8x_recount.py (path 2). No real D8x result exists yet.

Run: python -I -B -m unittest discover -s <this folder> -p test_d8x_recount.py
(or python -I -B test_d8x_recount.py). Fixtures follow the record keys of the producers
(acc_d8.py --points, run_v5.py d1 --group H-R-X, run_S6C/run_S8C judge, d8x_g0_rev1.json).
"""

from __future__ import annotations

import copy
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("d8x_recount", HERE / "d8x_recount.py")
R = importlib.util.module_from_spec(_spec)
sys.modules["d8x_recount"] = R
_spec.loader.exec_module(R)

KT = 0.25
KT_SCALES = {"x0.3": 0.3 * KT, "x1": KT, "x3": 3.0 * KT}
TAG_V0 = "final_C4G2_LAS"
TAG_VB = "final_C4G2_P3_LAS"
IDENT = {"python": "py", "python_version": "3.12", "affinity_mask": "0xfff0000",
         "threads": {"MKL_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "NUMBA_NUM_THREADS": "1",
                     "OPENBLAS_NUM_THREADS": "1", "MKL_THREADING_LAYER": "TBB"},
         "git": {"head": "abc", "status_porcelain": "", "is_clean": True}}


def d8x_block(j1=50000.0, events=None, **over):
    block = {"t_touch_s": 20.0, "t_crawler_off_s": 22.0, "t_loc_s": 22.5, "t_lift_s": 22.0,
             "t_ready_s": 45.0, "t_end_s": 60.0, "J1_min_cyl_after_lift_N": j1, "J1_leg": 3,
             "J1_t_s": 30.0, "J1_window_s": 38.0, "reanchor_intervals_s": [],
             "J2_min_cyl_reanchor_N": None, "J3_pad_lift_samples": 0,
             "J3_pad_normal_min_N": 1000.0, "J4_att_max_after_ready_deg": 0.03,
             "J6_max_moving_bar": 120.0, "stroke_max_m": 0.60,
             "events": events if events is not None else [[22.5, "crawler_liftoff_confirmed"],
                                                          [45.0, "ready_heave_tail"]]}
    block.update(over)
    return block


def sha(*parts):
    return "h" + "|".join(str(p) for p in parts)


# ----------------------------------------------------------------------------------- R-a
def ra_cases(k1):
    cases = []

    def add(stage, kind, variant, level, mast, tag, param=None):
        rid = f"{kind}|C2_tv0.1|{level}|{mast}|{tag}" + (f"|{param}" if param is not None else "")
        cases.append(dict(stage=stage, variant=variant, level=level, mast=mast, point=tag, id=rid))

    for level in R.LEVELS:
        for tag in R.RA_POINTS:
            for mast in R.MASTS:
                add("main", "main", "main", level, mast, tag)
            if k1 == "on":
                continue
            if level == "top":
                for mast in R.MASTS:
                    for s in (1, 2):
                        add("robust", "seed", f"seed{s}", level, mast, tag, s)
                    for s in range(3):
                        add("robust", "d0", f"d0s{s}", level, mast, tag, s)
                    for beta in (0.69e9, 1.6e9):
                        add("robust", "beta", f"beta{beta:g}", level, mast, tag, f"{beta:g}")
            elif tag in R.RA_ROBUST_LOWER:
                for mast in R.MASTS:
                    for beta in (0.69e9, 1.6e9):
                        add("robust", "beta", f"beta{beta:g}", level, mast, tag, f"{beta:g}")
                    add("robust", "d0", "d0s0", level, mast, tag, 0)
            if tag in R.RA_KT:
                masts = ("rigid", "stiff") if level == "top" else ("rigid",)
                for mast in masts:
                    for scale in KT_SCALES.values():
                        add("kt", "kt", f"kt{scale:.4f}", level, mast, tag, f"{scale:.4f}")
                        if level == "top":
                            add("kt", "ktd0", f"ktd0{scale:.4f}", level, mast, tag, f"{scale:.4f}")
    return cases


def ra_doc(k1="off", j1_of=None):
    runs = []
    for c in ra_cases(k1):
        j1 = 50000.0 if j1_of is None else j1_of(c)
        run = {"id": c["id"], "cfg": "C2_tv0.1", "min_true_cyl_force_kN": j1 / 1e3,
               "t_ready_s": 45.0, "t_touch_s": 20.0, "fails": [], "phase": "ready", "fault": False,
               "warnings": [], "commands_sha256": sha(c["stage"], c["level"], c["mast"], c["point"],
                                                      c["variant"]),
               "stage": c["stage"], "variant": c["variant"], "point": c["point"],
               "level": c["level"], "mast": c["mast"],
               "angles_deg": list(R.RA_POINTS[c["point"]]), "k1_order_gate": k1 == "on",
               "liftoff_slow_enabled": True, "controller_tag": TAG_V0,
               "module_files_sha256": "m", "d8x": d8x_block(j1)}
        runs.append(run)
    meta = {"n": len(runs), "d8x": {"k1": k1, "points_sha256": "p", "identity_start": IDENT,
                                    "identity_end": IDENT}}
    return {"meta": meta, "runs": runs}


# ----------------------------------------------------------------------------------- R-c
RC_ANGLES = {**R.AXIS_VERTICES, **R.RPX_POINTS}


def rc_lines(k1="off", j1_of=None):
    out = []
    for setting in ("VB", "V0"):
        for level in R.LEVELS:
            for floor in R.RC_FLOORS:
                for scale in (1.0, 3.0):
                    for eps in R.RC_EPS[k1]:
                        roll, pitch = RC_ANGLES[floor]
                        j1 = 50000.0 if j1_of is None else j1_of(setting, level, floor, scale, eps)
                        block = d8x_block(j1)
                        block.update({"k1_order_gate": k1 == "on", "liftoff_slow_enabled": True,
                                      "angles_deg": [roll, pitch], "level": level, "floor": floor,
                                      "crawler_k_scale": scale, "module_files_sha256": "m"})
                        out.append({
                            "job": {"d1": {"group": "H-R-X", "base": "rigid", "level": level,
                                           "slope_name": floor, "roll_deg": roll,
                                           "pitch_deg": pitch, "crawler_k_scale": scale},
                                    "eps": eps, "setting": setting, "k1": k1},
                            "commands_sha256": sha(setting, level, floor, scale, eps),
                            "final_phase": "ready",
                            "controller_tag": TAG_VB if setting == "VB" else TAG_V0,
                            "d1": {"verdict": "pass", "fail_items": [], "d8x": block}})
    return out


# -------------------------------------------------------------------------------- Chrono
def chrono_rows(w_floor="dxmm050", v_floor="roll5.7", j1_kn_of=None):
    rows = []
    for no, family, engine, beta, fs, level, floor, order, settle, group in R.CHRONO_TABLE:
        floor = {"<W>": w_floor, "<V>": v_floor}.get(floor, floor)
        if family == "C1_D8":
            name = f"D8X_{family}_{level}_{floor}_b1.6"
        elif family == "C1_H4V":
            name = f"D8X_{family}_{level}_{floor}"
        else:
            name = f"D8X_{family}_{level}_{floor}_Fs{fs:g}"
        j1 = 40.0 if j1_kn_of is None else j1_kn_of(no, floor)
        h4 = floor == "fdown3.7"
        events = ["C2Event(t_s=7.2, name='INFO_PRESSURE_ZERO_CALIBRATED:FL')",
                  "C2Event(t_s=28.4, name='crawler_liftoff_confirmed')"]
        if h4:
            events += ["C2Event(t_s=61.3, name='reanchor_started')",
                       "C2Event(t_s=79.3, name='reanchor_completed')"]
        block = {"row": name, "slope_limit_mode": "verification_ext",
                 "floor_true_deg": list(R.CHRONO_FLOORS[floor]),
                 "half_spans_deg": {"roll": 5.7, "pitch_nose_down": 3.7, "pitch_nose_up": 3.6},
                 "level": level, "beta_GPa": beta, "controller_tag": TAG_V0, "fs_kN": fs,
                 "liftoff_slow_enabled": True,
                 "settle_map": ({"kind": "level", "level": level} if settle == "level"
                                else {"kind": "identity"}),
                 "scenario_group": group or "D8", "scenario_id": f"S_{no}"}
        metrics = {"case": name[4:], "group": group or "D8", "level": level, "floor": floor,
                   "times_s": {"t0": 3.0, "touch": 23.9, "ready": 77.5, "liftoff": 24.3,
                               "end": 87.5},
                   "final_phase": "ready", "F_min_N": 9414.58911, "min_cyl_after_liftoff_kN": j1,
                   "min_cyl_reanchor_kN": 30.0 if h4 else None,
                   "pad_N_min_after_liftoff_kN": 31.0, "max_moving_pressure_bar": 117.0,
                   "max_pressure_any_step_bar": 117.1, "target_code": "ACCEPTED",
                   "floor_true_deg": list(R.CHRONO_FLOORS[floor]),
                   "att_err_after_ready_maxabs_deg": 0.02, "crawler_recontact_after_loc_count": 0,
                   "stroke": {"max_m": [0.65, 0.65, 0.35, 0.35]}, "events": events}
        rows.append({"name": name, "block": block, "metrics": metrics, "no": no})
    return rows


def write_chrono(root: Path, rows) -> None:
    for r in rows:
        case = r["metrics"]["case"]
        folder = root / f"final_{case}" / case
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "result.json").write_text(json.dumps({"case": case, "d8x": r["block"],
                                                        "acceptance": {"target_code": "ACCEPTED"}}))
        vdir = root / f"final_{case}" / "_verify"
        vdir.mkdir(parents=True, exist_ok=True)
        (vdir / f"verify_{case}.json").write_text(json.dumps({"meta": {}, "metrics": [r["metrics"]]}))
        t = np.arange(3.1, r["metrics"]["times_s"]["end"] + 1e-9, 0.1)
        phase = np.where(t < 23.9, "touch", np.where(t < 77.5 - 1e-9, "level", "ready"))
        np.savez(folder / "r8_series.npz", t=t, phase=phase.astype("<U16"))


# ------------------------------------------------------------------------------------ G0
def g0_doc(err=(0.005, 0.005)):
    rows = []
    for level in R.LEVELS:
        for tag, (roll, pitch) in R.G0_POINTS.items():
            allowance = 0.002 + (0.0029 if pitch > 0 else 0.0)
            rows.append({"level": level, "tag": tag, "floor_deg": [roll, pitch],
                         "G0": {"G0-1": {"s_max_m": 0.66, "allowance_m": allowance},
                                "G0-2": {"F_static_min_N": 60000.0},
                                "G0-3": {"swivel_deg": 4.0},
                                "G0-4": {"floor_hat_deg": [roll + err[0], pitch + err[1]]}},
                         "verdict": "pass", "source": "synthetic"})
    return {"meta": {}, "rows": rows}


def points_doc():
    return {"schema": "d8x_points/1", "rules_rev": "rev1",
            "rules": {"original": {"sha256": R.RULES_SHA256["d8x_rules.md"]},
                      "rev1": {"sha256": R.RULES_SHA256["d8x_rules_rev1.md"]},
                      "rev2": {"sha256": R.RULES_SHA256["d8x_rules_rev2.md"]}},
            "ra_points": [{"tag": k, "roll_deg": v[0], "pitch_deg": v[1]} for k, v in R.RA_POINTS.items()],
            "rpx_points": [{"name": k, "roll_deg": v[0], "pitch_deg": v[1]} for k, v in R.RPX_POINTS.items()],
            "axis_vertices": [{"name": k, "roll_deg": v[0], "pitch_deg": v[1]}
                              for k, v in R.AXIS_VERTICES.items()],
            "rc_floors": list(R.RC_FLOORS)}


def w_j1(case):
    """R-a J1: r-p-0.5 top rigid 30 kN, d45+- 26 kN, others 50 kN (W via the R-c mirror)."""
    if case["level"] == "top" and case["mast"] == "rigid":
        if case["point"] == "r-p-0.5":
            return 30000.0
        if case["point"] == "d45+-":
            return 26000.0
    return 50000.0


def w_rc(setting, level, floor, scale, eps):
    if level == "top" and floor == "rpX--":
        return 25000.0
    return 50000.0


def v_chrono(no, floor):
    return 20.0 if no == 3 else 40.0


class Fixture:
    def __init__(self):
        self.ra_off = ra_doc("off", w_j1)
        self.ra_on = ra_doc("on", w_j1)
        self.rc_off = rc_lines("off", w_rc)
        self.rc_on = rc_lines("on", w_rc)
        self.chrono = chrono_rows("dxmm050", "roll5.7", v_chrono)
        self.g0 = g0_doc()
        self.points = points_doc()

    def write(self, root: Path) -> dict:
        root.mkdir(parents=True, exist_ok=True)
        paths = {k: root / f"{k}.json" for k in ("ra_off", "ra_on", "g0", "points")}
        for k, p in paths.items():
            p.write_text(json.dumps(getattr(self, k)))
        for k in ("rc_off", "rc_on"):
            p = root / f"hrx_{k}.jsonl"
            p.write_text("\n".join(json.dumps(x) for x in getattr(self, k)) + "\n")
            (root / f"hrx_{k}.identity.json").write_text(json.dumps({"start": [IDENT], "end": [IDENT]}))
            paths[k] = p
        croot = root / "chrono"
        if croot.exists():
            shutil.rmtree(croot)
        write_chrono(croot, self.chrono)
        paths["chrono"] = croot
        return paths


def run_tool(paths: dict, extra=(), drop=()) -> tuple[int, dict, dict]:
    argv = ["recount"]
    for flag, key in (("--points", "points"), ("--g0", "g0"), ("--ra", "ra_off"),
                      ("--ra-k1", "ra_on"), ("--rc", "rc_off"), ("--rc-k1", "rc_on")):
        if key not in drop:
            argv += [flag, str(paths[key])]
    if "chrono" not in drop:
        argv += ["--chrono", str(paths["chrono"])]
    out = paths["chrono"].parent / "report.json"
    argv += ["--out", str(out), *extra]
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = R.main(argv)
    summary = json.loads(buf.getvalue().strip().splitlines()[-1])
    return code, json.loads(out.read_text(encoding="utf-8")), summary


def rows_of(report, bundle, k1="off"):
    if bundle == "R-a":
        return report["ra"][k1]["rows"]
    if bundle == "R-c":
        return report["rc"][k1]["rows"]
    return report["chrono"]["rows"]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="d8x_rc_"))
        self.fx = Fixture()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_fx(self, **kw):
        return run_tool(self.fx.write(self.tmp), **kw)


class TestBaseline(Base):
    def test_all_pass(self):
        code, rep, summ = self.run_fx()
        self.assertEqual(rep["grade"]["label"], "통과", rep["grade"])
        self.assertEqual(code, 0)
        b = rep["bundles"]
        self.assertEqual((b["R-a"]["expected"], b["R-a"]["actual"], b["R-a"]["pass"]), (1102, 1102, 1102))
        self.assertEqual(b["R-a"]["parts"]["off"]["actual"], 910)
        self.assertEqual(b["R-a"]["parts"]["on"]["actual"], 192)
        self.assertEqual((b["R-c"]["actual"], b["R-c"]["pass"]), (288, 288))
        self.assertEqual((b["C"]["actual"], b["C"]["pass"]), (19, 19))
        self.assertEqual((b["G0"]["actual"], b["G0"]["pass"]), (60, 60))
        for gate in ("G0", "G1", "G2a", "G2b"):
            self.assertEqual(rep["gates"][gate], "pass")
        self.assertEqual(rep["gates"]["G-S"]["I-3"], "pass")
        self.assertEqual(rep["invariance"]["V-1"]["class"], "K1_INVARIANT")
        self.assertEqual(rep["invariance"]["V-2"]["class"], "LAS_INACTIVE")
        self.assertEqual(summ["grade"], "통과")

    def test_w_uses_mirror_and_v(self):
        _, rep, _ = self.run_fx()
        w = rep["selection"]["W"]
        self.assertEqual((w["status"], w["point"], w["floor"]), ("selected", "r-p-0.5", "dxmm050"))
        self.assertEqual(w["m_N"], 25000.0)
        self.assertEqual(rep["selection"]["V"]["floor"], "roll5.7")

    def test_expected_set_sizes(self):
        self.assertEqual(len(R.ra_expected("off")), 910)
        self.assertEqual(len(R.ra_expected("on")), 192)
        self.assertEqual(len(R.rc_expected("off")), 192)
        self.assertEqual(len(R.rc_expected("on")), 96)
        names = R.chrono_expected_rows("dxpp025", "rpX")
        self.assertEqual(len(names), 19)
        self.assertIn("D8X_K24_top_fup3.6_Fs4", names)
        self.assertIn("D8X_C1_D8_top_fup3.6_b1.6", names)
        self.assertIn("D8X_K0V_top_fup3.6_Fs0", names)
        self.assertIn("D8X_C1_H4V_top_fdown3.7", names)

    def test_rv_table(self):
        self.assertAlmostEqual(R.r_v(0.0, -3.6), 1.0, places=12)
        self.assertAlmostEqual(R.r_v(2.2627, 2.2627), 1.008505, places=6)
        self.assertAlmostEqual(R.r_v(2.8242, -1.8162), 0.999974, places=6)
        self.assertAlmostEqual(R.r_v(0.0, -3.7), 1.027778, places=6)
        self.assertLessEqual(max(R.r_v(*v) for v in R.RA_POINTS.values()), 1.01)


class TestRows(Base):
    def test_j1_below_line_fails(self):
        self.fx.ra_off["runs"][5]["d8x"]["J1_min_cyl_after_lift_N"] = R.F_D8_N - 1.0
        code, rep, _ = self.run_fx()
        self.assertEqual(rep["grade"]["label"], "미달")
        self.assertEqual(code, 1)
        self.assertEqual(rep["gates"]["G1"], "fail")
        row = rows_of(rep, "R-a")[5]
        self.assertEqual(row["verdict"], "fail")
        self.assertIn("J1", row["failed_items"])

    def test_j1_exactly_on_line_passes_with_flag(self):
        self.fx.ra_off["runs"][0]["d8x"]["J1_min_cyl_after_lift_N"] = R.F_D8_N
        code, rep, _ = self.run_fx()
        self.assertEqual(rep["grade"]["label"], "조건부 통과")
        self.assertTrue(any(f["flag"] == "i" for f in rep["flags"]))

    def test_k1_row_fail_does_not_gate(self):
        self.fx.ra_on["runs"][0]["d8x"]["J4_att_max_after_ready_deg"] = 0.3
        _, rep, _ = self.run_fx()
        self.assertEqual(rep["gates"]["G1"], "pass")
        self.assertEqual(rep["bundles"]["R-a"]["k1_rows_fail"], 1)

    def test_nan_field_fails(self):
        self.fx.rc_off[3]["d1"]["d8x"]["J4_att_max_after_ready_deg"] = float("nan")
        _, rep, _ = self.run_fx()
        row = rows_of(rep, "R-c")[3]
        self.assertEqual(row["verdict"], "fail")
        self.assertIn("J4", row["failed_items"])

    def test_missing_ready_fails_e2(self):
        self.fx.rc_off[0]["d1"]["d8x"]["t_ready_s"] = None
        _, rep, _ = self.run_fx()
        row = rows_of(rep, "R-c")[0]
        self.assertEqual(row["verdict"], "fail")
        self.assertTrue(any("E-2" in f for f in row["fail"]))

    def test_rej_event_fails_e3(self):
        self.fx.ra_off["runs"][7]["d8x"]["events"].append([1.0, "REJ_SLOPE_D8"])
        _, rep, _ = self.run_fx()
        self.assertEqual(rows_of(rep, "R-a")[7]["verdict"], "fail")

    def test_event_classes(self):
        ev = R.classify_events(["FAULT_STROKE_END:FL", "FAULT_LIFT_STROKE_LIMIT:soil",
                                "WARN_LIFT_STROKE_LIMITED", "FAULT_HEAD_PRESSURE:RL",
                                "WARN_PROBE_STIFFNESS_OUT_OF_RANGE:FR", "WARN_LEG_REAPPROACH_NO_CONTACT",
                                "INFO_LIFTOFF_SLOW:FL", "INFO_LOC_REVOKED"])
        self.assertEqual(len(ev["J7"]), 3)
        self.assertEqual(ev["J8"], ["FAULT_HEAD_PRESSURE:RL"])
        self.assertEqual(ev["J9"], ["WARN_LEG_REAPPROACH_NO_CONTACT"])
        self.assertEqual(len(ev["LAS"]), 1)
        self.assertEqual(ev["V1_block"], ["INFO_LOC_REVOKED"])

    def test_allowed_warn_passes(self):
        self.fx.ra_off["runs"][2]["d8x"]["events"].append([30.0, "WARN_PROBE_STIFFNESS_OUT_OF_RANGE:FL"])
        _, rep, _ = self.run_fx()
        self.assertEqual(rows_of(rep, "R-a")[2]["verdict"], "pass")

    def test_j2_only_when_h4(self):
        run = self.fx.ra_off["runs"][4]
        run["d8x"]["reanchor_intervals_s"] = [[40.0, 50.0]]
        run["d8x"]["J2_min_cyl_reanchor_N"] = R.F_D8_N - 10.0
        _, rep, _ = self.run_fx()
        row = rows_of(rep, "R-a")[4]
        self.assertIn("J2", row["failed_items"])
        self.assertEqual(rows_of(rep, "R-a")[3]["items"]["J2"]["result"], "n/a")

    def test_e8_short_window_unjudgeable(self):
        self.fx.rc_off[1]["d1"]["d8x"]["J1_window_s"] = 0.5
        code, rep, _ = self.run_fx()
        self.assertEqual(rows_of(rep, "R-c")[1]["verdict"], "unjudgeable")
        self.assertEqual(rep["grade"]["label"], "판정 불가")
        self.assertEqual(code, 2)

    def test_driver_error_record_fails(self):
        run = self.fx.ra_off["runs"][9]
        self.fx.ra_off["runs"][9] = {"id": run["id"], "error": "boom", "tb": "x"}
        _, rep, _ = self.run_fx()
        row = rows_of(rep, "R-a")[9]
        self.assertEqual(row["verdict"], "fail")
        self.assertEqual(run["variant"], "beta6.9e+08")
        self.assertEqual(row["key"], "|".join((run["stage"], run["level"], run["mast"],
                                               run["point"], "beta0.69")))

    def test_j11_harness_fails(self):
        self.fx.ra_off["runs"][1]["fails"] = ["D8 min force"]
        self.fx.rc_off[2]["d1"]["fail_items"] = ["READY"]
        _, rep, _ = self.run_fx()
        self.assertIn("J11", rows_of(rep, "R-a")[1]["failed_items"])
        self.assertIn("J11", rows_of(rep, "R-c")[2]["failed_items"])


class TestEmptySetAndIdentity(Base):
    def test_missing_row_unjudgeable(self):
        del self.fx.ra_off["runs"][10]
        code, rep, _ = self.run_fx()
        self.assertEqual(rep["bundles"]["R-a"]["status"], "unjudgeable")
        self.assertEqual(rep["grade"]["label"], "판정 불가")
        self.assertEqual(code, 2)

    def test_duplicate_key_unjudgeable(self):
        self.fx.rc_off.append(copy.deepcopy(self.fx.rc_off[0]))
        _, rep, _ = self.run_fx()
        self.assertEqual(rep["bundles"]["R-c"]["status"], "unjudgeable")

    def test_tag_mismatch_unjudgeable(self):
        self.fx.rc_off[5]["controller_tag"] = "final_C4G2_P3"
        _, rep, _ = self.run_fx()
        self.assertEqual(rows_of(rep, "R-c")[5]["verdict"], "unjudgeable")

    def test_expect_override(self):
        expect = self.tmp / "expect.json"
        self.tmp.mkdir(parents=True, exist_ok=True)
        expect.write_text(json.dumps({"chrono": "final_C4G2_LAS_K1"}))
        _, rep, _ = self.run_fx(extra=("--expect", str(expect)))
        self.assertEqual(rep["bundles"]["C"]["status"], "unjudgeable")
        self.assertEqual(rep["bundles"]["R-a"]["status"], "pass")
        self.assertEqual(rep["expect"]["source"], str(expect))

    def test_las_off_unjudgeable(self):
        self.fx.ra_off["runs"][11]["liftoff_slow_enabled"] = False
        _, rep, _ = self.run_fx()
        self.assertEqual(rows_of(rep, "R-a")[11]["verdict"], "unjudgeable")

    def test_k1_flag_mismatch_unjudgeable(self):
        self.fx.ra_on["runs"][0]["k1_order_gate"] = False
        _, rep, _ = self.run_fx()
        self.assertEqual(rows_of(rep, "R-a", "on")[0]["verdict"], "unjudgeable")

    def test_angle_mismatch_unjudgeable(self):
        self.fx.ra_off["runs"][0]["angles_deg"] = [0.0, 3.7000001]
        _, rep, _ = self.run_fx()
        self.assertEqual(rows_of(rep, "R-a")[0]["verdict"], "unjudgeable")

    def test_unclean_identity_unjudgeable(self):
        ident = copy.deepcopy(IDENT)
        ident["git"]["is_clean"] = False
        self.fx.ra_off["meta"]["d8x"]["identity_end"] = ident
        _, rep, _ = self.run_fx()
        self.assertEqual(rep["bundles"]["R-a"]["status"], "unjudgeable")

    def test_point_file_mismatch(self):
        self.fx.points["ra_points"][1]["pitch_deg"] = -3.7
        _, rep, _ = self.run_fx()
        self.assertEqual(rep["gates"]["G-S"]["I-3"], "unjudgeable")
        self.assertEqual(rep["grade"]["label"], "판정 불가")

    def test_kt_variant_outside_set(self):
        for run in self.fx.ra_off["runs"]:
            if run["variant"].startswith("kt") and run["variant"].endswith(f"{0.3 * KT:.4f}"):
                run["variant"] = run["variant"].replace(f"{0.3 * KT:.4f}", f"{0.5 * KT:.4f}")
                run["id"] = run["id"].replace(f"{0.3 * KT:.4f}", f"{0.5 * KT:.4f}")
        _, rep, _ = self.run_fx()
        self.assertEqual(rep["bundles"]["R-a"]["status"], "unjudgeable")


class TestInvariance(Base):
    def test_k1_dependent(self):
        self.fx.ra_on["runs"][0]["commands_sha256"] = "different"
        code, rep, _ = self.run_fx()
        v1 = rep["invariance"]["V-1"]
        self.assertEqual(v1["class"], "K1_DEPENDENT")
        self.assertEqual(v1["K1_DEPENDENT"], [["R-a", "pitch+", "top"]])
        self.assertIn("D8X_K24_top_fdown3.7_Fs4", v1["chrono_rows_on_dependent_points"])
        self.assertEqual(rep["grade"]["label"], "조건부 통과")
        self.assertEqual(code, 0)

    def test_las_dependent(self):
        self.fx.rc_off[0]["d1"]["d8x"]["events"].append([23.0, "INFO_LIFTOFF_SLOW:FL"])
        _, rep, _ = self.run_fx()
        v2 = rep["invariance"]["V-2"]
        self.assertEqual(v2["class"], "LAS_DEPENDENT")
        self.assertEqual(v2["LAS_DEPENDENT"], [["R-c", "fdown3.7", "top", 1]])
        self.assertTrue(any(f.get("class") == "LAS_DEPENDENT" for f in rep["flags"]))

    def test_k1_pair_las_not_counted(self):
        self.fx.ra_on["runs"][0]["d8x"]["events"].append([23.0, "INFO_LIFTOFF_SLOW:FL"])
        _, rep, _ = self.run_fx()
        self.assertEqual(rep["invariance"]["V-2"]["class"], "LAS_INACTIVE")

    def test_v3_difference(self):
        _, rep, _ = self.run_fx()
        v3 = rep["invariance"]["V-3"]
        self.assertEqual(len(v3), 96)
        self.assertTrue(all(e["VB_minus_V0_N"] == 0.0 for e in v3))

    def test_chrono_succession_blocked(self):
        self.fx.chrono[0]["metrics"]["events"].append("C2Event(t_s=30.0, name='INFO_LOC_REVOKED')")
        _, rep, _ = self.run_fx()
        succ = {e["row"]: e for e in rep["invariance"]["V-1"]["chrono_succession"]}
        self.assertFalse(succ["D8X_K24_top_fdown3.7_Fs4"]["succession_ok"])


class TestSelection(Base):
    def test_w_tie_breaks_by_list_order(self):
        def j1(case):
            if case["level"] == "top" and case["mast"] == "rigid" and case["point"] in ("d45--", "r+p+0.75"):
                return 20000.0
            return 50000.0
        self.fx.ra_off = ra_doc("off", j1)
        self.fx.rc_off = rc_lines("off")
        self.fx.chrono = chrono_rows("dxpp075", "roll5.7", v_chrono)
        _, rep, _ = self.run_fx()
        self.assertEqual(rep["selection"]["W"]["point"], "r+p+0.75")
        self.assertEqual(rep["grade"]["label"], "통과")

    def test_w_ignores_non_rigid_and_k1(self):
        def j1(case):
            if case["level"] == "top" and case["mast"] == "stiff" and case["point"] == "d45-+":
                return 15000.0
            return 50000.0
        self.fx.ra_off = ra_doc("off", j1)
        self.fx.ra_on = ra_doc("on", lambda c: 15000.0 if c["point"] == "r+p+0.25" else 50000.0)
        self.fx.rc_off = rc_lines("off")
        self.fx.chrono = chrono_rows("dxpp025", "roll5.7", v_chrono)
        _, rep, _ = self.run_fx()
        self.assertEqual(rep["selection"]["W"]["point"], "r+p+0.25")  # all equal -> first in order

    def test_chrono_w_row_mismatch_unjudgeable(self):
        self.fx.chrono = chrono_rows("d45pp", "roll5.7", v_chrono)
        _, rep, _ = self.run_fx()
        self.assertEqual(rep["bundles"]["C"]["status"], "unjudgeable")

    def test_v_tie_by_table_order(self):
        self.fx.chrono = chrono_rows("dxmm050", "fup3.6", lambda no, f: 20.0 if no in (2, 5) else 40.0)
        _, rep, _ = self.run_fx()
        self.assertEqual(rep["selection"]["V"]["floor"], "fup3.6")
        self.assertEqual(rep["gates"]["G2b"], "pass")

    def test_w_pending_without_rc(self):
        _, rep, _ = self.run_fx(drop=("rc_off", "rc_on"))
        self.assertEqual(rep["selection"]["W"]["status"], "pending")
        self.assertEqual(rep["gates"]["G1"], "pending")


class TestChrono(Base):
    def _row(self, rep, name):
        return next(r for r in rows_of(rep, "C") if r["row"] == name)

    def test_settle_map_wrong_unjudgeable(self):
        self.fx.chrono[0]["block"]["settle_map"] = {"kind": "level", "level": "top"}
        self.fx.chrono[6]["block"]["settle_map"] = {"kind": "level", "level": "middle"}
        _, rep, _ = self.run_fx()
        self.assertEqual(self._row(rep, "D8X_K24_top_fdown3.7_Fs4")["verdict"], "unjudgeable")
        self.assertEqual(self._row(rep, "D8X_C1_D8_top_fdown3.7_b1.6")["verdict"], "unjudgeable")

    def test_settle_map_string_forms(self):
        self.assertEqual(R._settle_kind("identity"), ("identity", None))
        self.assertEqual(R._settle_kind("level:top"), ("level", "top"))
        self.assertEqual(R._settle_kind({"kind": "level", "level": "bottom"}), ("level", "bottom"))
        self.assertEqual(R._settle_kind("level"), ("level", None))

    def test_no_ready_short_run_unjudgeable(self):
        m = self.fx.chrono[2]["metrics"]
        m["times_s"]["ready"] = None
        m["times_s"]["end"] = 90.0
        _, rep, _ = self.run_fx()
        self.assertEqual(self._row(rep, "D8X_K24_top_roll5.7_Fs4")["verdict"], "unjudgeable")

    def test_no_ready_long_run_fails(self):
        m = self.fx.chrono[3]["metrics"]
        m["times_s"]["ready"] = None
        m["times_s"]["end"] = 125.0
        _, rep, _ = self.run_fx()
        self.assertEqual(self._row(rep, "D8X_K24_top_rollm5.7_Fs4")["verdict"], "fail")
        self.assertEqual(rep["gates"]["G2a"], "fail")

    def test_mode_and_floor_identity(self):
        self.fx.chrono[4]["block"]["slope_limit_mode"] = "verification"
        self.fx.chrono[1]["block"]["floor_true_deg"] = [0.0, -3.7]
        _, rep, _ = self.run_fx()
        self.assertEqual(self._row(rep, "D8X_K24_top_rpX_Fs4")["verdict"], "unjudgeable")
        self.assertEqual(self._row(rep, "D8X_K24_top_fup3.6_Fs4")["verdict"], "unjudgeable")

    def test_recontact_and_pressure(self):
        self.fx.chrono[10]["metrics"]["crawler_recontact_after_loc_count"] = 1
        self.fx.chrono[11]["metrics"]["max_pressure_any_step_bar"] = 360.0
        _, rep, _ = self.run_fx()
        self.assertIn("J10", self._row(rep, "D8X_C1_H4V_top_fdown3.7")["failed_items"])
        self.assertIn("J6_locked", self._row(rep, "D8X_A_middle_rpX_Fs0")["failed_items"])

    def test_target_rejected_fails(self):
        self.fx.chrono[5]["metrics"]["target_code"] = "REJ_SLOPE_D8"
        _, rep, _ = self.run_fx()
        self.assertEqual(self._row(rep, "D8X_K24_top_dxmm050_Fs4")["verdict"], "fail")

    def test_reanchor_j2(self):
        self.fx.chrono[13]["metrics"]["min_cyl_reanchor_kN"] = 14.0
        _, rep, _ = self.run_fx()
        self.assertIn("J2", self._row(rep, "D8X_K0V_top_fdown3.7_Fs0")["failed_items"])

    def test_scenario_group_rev2_6(self):
        self.fx.chrono[0]["block"]["scenario_group"] = "D8"
        _, rep, _ = self.run_fx()
        self.assertEqual(self._row(rep, "D8X_K24_top_fdown3.7_Fs4")["verdict"], "unjudgeable")

    def test_first_order_only_pending(self):
        self.fx.chrono = [r for r in self.fx.chrono if r["no"] != 19]
        code, rep, _ = self.run_fx()
        self.assertEqual(rep["gates"]["G2a"], "pass")
        self.assertEqual(rep["gates"]["G2b"], "pending")
        self.assertEqual(rep["grade"]["label"], "보류(입력 미완)")
        self.assertEqual(code, 0)

    def test_duplicate_chrono_row(self):
        extra = copy.deepcopy(self.fx.chrono[0])
        extra["metrics"]["case"] = extra["metrics"]["case"] + "_rerun"
        self.fx.chrono.append(extra)
        _, rep, _ = self.run_fx()
        self.assertEqual(rep["bundles"]["C"]["status"], "unjudgeable")

    def test_stroke_flag(self):
        self.fx.chrono[0]["metrics"]["stroke"]["max_m"] = [0.679, 0.6, 0.3, 0.3]
        _, rep, _ = self.run_fx()
        self.assertTrue(any(f["flag"] == "ii" for f in rep["flags"]))
        self.assertEqual(rep["grade"]["label"], "조건부 통과")


class TestG0(Base):
    def test_g0_scope_and_allowance(self):
        doc = self.fx.g0
        for row in doc["rows"]:
            if row["tag"] == "roll-" and row["level"] == "top":   # outside the rev2 gate scope
                row["G0"]["G0-4"]["floor_hat_deg"] = [-5.7 - 0.1, 0.0]
            if row["tag"] == "pitch+" and row["level"] == "middle":  # H4 allowance 4.9 mm
                row["G0"]["G0-1"]["s_max_m"] = 0.6828 - 0.0049 - 1e-6
        _, rep, _ = self.run_fx()
        self.assertEqual(rep["gates"]["G0"], "pass")
        for row in doc["rows"]:
            if row["tag"] == "pitch+" and row["level"] == "middle":
                row["G0"]["G0-1"]["s_max_m"] = 0.6828 - 0.0049 + 1e-6
        _, rep, _ = self.run_fx()
        self.assertEqual(rep["gates"]["G0"], "fail")
        self.assertEqual(rep["grade"]["label"], "미달")

    def test_g0_4_gate_point_fails(self):
        for row in self.fx.g0["rows"]:
            if row["tag"] == "rpX" and row["level"] == "top":
                row["G0"]["G0-4"]["floor_hat_deg"] = [2.8632, 1.8413 + 0.04]
        _, rep, _ = self.run_fx()
        self.assertEqual(rep["gates"]["G0"], "fail")

    def test_g0_4_flag_iv(self):
        self.fx.g0 = g0_doc(err=(0.0, 0.021))
        _, rep, _ = self.run_fx()
        self.assertTrue(any(f["flag"] == "iv" for f in rep["flags"]))

    def test_g0_missing_eval(self):
        del self.fx.g0["rows"][0]
        _, rep, _ = self.run_fx()
        self.assertEqual(rep["gates"]["G0"], "unjudgeable")


class TestHashCompare(Base):
    def test_same_and_different(self):
        paths = self.fx.write(self.tmp)
        other = self.tmp / "ra_off_2.json"
        doc = copy.deepcopy(self.fx.ra_off)
        other.write_text(json.dumps(doc))
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = R.main(["hash-compare", "--bundle", "ra", str(paths["ra_off"]), str(other),
                           "--out", str(self.tmp / "hc.json")])
        self.assertEqual(code, 0)
        doc["runs"][3]["commands_sha256"] = "x"
        other.write_text(json.dumps(doc))
        with redirect_stdout(buf):
            code = R.main(["hash-compare", "--bundle", "ra", str(paths["ra_off"]), str(other),
                           "--out", str(self.tmp / "hc.json")])
        self.assertEqual(code, 1)
        res = json.loads((self.tmp / "hc.json").read_text())
        self.assertEqual(len(res["differ"]), 1)


class TestCli(Base):
    def test_input_error_exit2(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = R.main(["recount", "--ra", str(self.tmp / "nope.json")])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(buf.getvalue().strip().splitlines()[-1])["status"], "input_error")

    def test_markdown_output(self):
        paths = self.fx.write(self.tmp)
        out = self.tmp / "r.md"
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = R.main(["recount", "--ra", str(paths["ra_off"]), "--format", "md", "--out", str(out)])
        text = out.read_text(encoding="utf-8")
        self.assertIn("등급(잠정)", text)
        self.assertEqual(code, 0)  # partial input without failure -> pending


if __name__ == "__main__":
    unittest.main()
