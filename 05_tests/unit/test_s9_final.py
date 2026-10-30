"""RV6 / FINAL1 .. FINAL6 / FINAL-R (spec 430.5 / 431.3, user decision 2026-10-30): the ``s9_batch.py`` rows of the
final-controller re-runs (``run_S9.rv6_cases`` / ``run_S9.final_cases`` / ``s9_batch.final_r_rows``). Definitions only:
no Chrono run."""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))
sys.path.insert(0, str(ROOT / "03_src"))

import run_S9  # noqa: E402
import s9_batch  # noqa: E402

SOIL = ("RV6", "FINAL1", "FINAL2", "FINAL3", "FINAL4", "FINAL5", "FINAL6")
COUNTS = {"RV6": 5,"FINAL1": 8, "FINAL2": 8, "FINAL3": 6, "FINAL4": 6, "FINAL5": 18, "FINAL6": 6}
S9_RESULTS = ROOT / "07_results" / "S9"


@pytest.fixture(scope="module")
def b() -> dict[str, list[dict]]:
    return s9_batch.batches()


def _by_case(rows: list[dict]) -> dict[str, dict]:
    return {r["case"]: r for r in rows}


def test_counts_and_unique_ids(b) -> None:
    for name, n in COUNTS.items():
        names = [r["case"] for r in b[name]]
        assert len(names) == n, name
        assert len(set(names)) == n, name
    soil = [r["case"] for n in SOIL for r in b[n]]
    assert len(soil) == len(set(soil)) == sum(COUNTS.values())
    fr = [r["case"] for r in b["FINAL-R"]]
    assert len(fr) == len(set(fr)) == 116


def test_final_rows_carry_the_controller_check_and_meta(b) -> None:
    for name in SOIL:
        for r in b[name]:
            argv = r["argv"]
            assert argv.count("--expect-controller") == 1, r["case"]
            assert argv[argv.index("--expect-controller") + 1] == run_S9.FINAL_CONTROLLER
            assert r["controller"] == run_S9.FINAL_CONTROLLER and r["group"] == name
            assert r["priority"] == run_S9.FINAL_PRIORITY[name]
            assert r["planned_pool"] == "pcore" and r["est_s"] == r["est_pool_s"]["pcore"]
            assert r["est_pool_s"]["ecore"] >= r["est_pool_s"]["pcore"] > 0
            a = run_S9.build_parser().parse_args(argv[len(s9_batch.RUN):] + ["--case", r["case"], "--out-root", "x"])
            assert a.expect_controller == run_S9.FINAL_CONTROLLER and a.action == "level"


def test_expected_case_names(b) -> None:
    assert [r["case"] for r in b["FINAL1"]] == [f"P3b_{s}_{p}_top_Fs4" for s in ("G1", "J1", "J2", "S1")
                                                for p in ("A", "B")]
    assert [r["case"] for r in b["FINAL2"]] == [
        "P3b_J1_B_top_Fs4_m1p1", "P3b_J2_B_top_Fs4_m1p1", "P3b_J1_B_middle_Fs4", "P3b_J1_B_bottom_Fs4",
        "P3b_J2_B_middle_Fs4", "P3b_J2_B_bottom_Fs4", "P3b_J1_A_middle_Fs4", "P3b_J1_A_bottom_Fs4"]
    assert [r["case"] for r in b["FINAL3"]] == [
        "S9SL_C1_G1_B_top_Fs4_r0_p3p2", "S9SL_C2_J1_A_top_Fs4_r4p4_p0", "S9SL_C3_J1_B_top_Fs4_r3p3_p0",
        "S9SL_C4_J1_A_top_Fs4_r0_p3p2", "S9SL_X4nd_J1_B_top_Fs4_r0_p2p8", "S9SL_X4ed_J1_B_top_Fs4_r1p925_p1p4"]
    assert [r["case"] for r in b["FINAL4"]] == [f"G6_G1_B_top_Fs4_sp{k}" for k in
                                                ("G1RR", "J1FL", "J1RR", "J2FL", "J2RR", "S1FL")]
    f5 = [r["case"] for r in b["FINAL5"]]
    assert len(f5) == 18 and f5[:8] == [f"P3b_{s}_{p}_top_Fs{fs}" for s in ("G1", "J1") for p in ("A", "B")
                                        for fs in (0, 8)]
    assert set(f5[8:]) == {f"P3b_G1_{p}_{lv}_Fs4" for p in ("A", "B") for lv in ("middle", "bottom")} | {
        f"P3b_{s}_{p}_{lv}_Fs4" for s, p in (("J2", "A"), ("S1", "A"), ("S1", "B")) for lv in ("middle", "bottom")}
    assert [r["case"] for r in b["RV6"]] == ["S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0", "S9SL_X6sa75_J2_B_top_Fs4_r3p3_p0",
                                             "S9SL_X6sa875_J2_B_top_Fs4_r3p85_p0", "S9SL_X6rb_J1_B_top_Fs4_rm2p86_p0",
                                             "S9SL_X6rbp_J1_B_top_Fs4_r2p86_p0"]
    # no FINAL bundle repeats a row of another (X4-rp only as RV6 X6-rp-sa)
    assert "S9SL_X4rp_J1_B_top_Fs4_r3p85_p0" not in {r["case"] for n in SOIL for r in b[n]}


def test_argv_is_the_original_row_plus_the_controller_check(b) -> None:
    """Each FINAL / RV6 row = an existing batch row of the same case (argv byte for byte) + --expect-controller."""
    orig: dict[str, list[str]] = {}
    for name in ("P3b", "p3b_aug", "S9SL", "MS1", "RV1", "G6", "G6P", "RV4", "RV5"):
        for r in b[name]:
            orig.setdefault(r["case"], r["argv"])
    x4rp = _by_case(b["RV1"])["S9SL_X4rp_J1_B_top_Fs4_r3p85_p0"]["argv"]
    for name in SOIL:
        for r in b[name]:
            plain = s9_batch.strip_controller_check(r["argv"])
            if r["case"] == "S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0":
                assert plain == x4rp and r["pair_case"] == "S9SL_X4rp_J1_B_top_Fs4_r3p85_p0"
                assert r["source_run"] == r["pair_run"] == run_S9.RV6_X4RP_RUN
            elif r["case"].startswith("S9SL_X6"):
                assert r["case"] not in orig
            else:
                assert plain == orig[r["case"]], r["case"]


def test_rv6_rows_follow_spec_430(b) -> None:
    rows = _by_case(b["RV6"])
    ap = run_S9.build_parser()
    floors = {"S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0": ("J1", 3.85), "S9SL_X6sa75_J2_B_top_Fs4_r3p3_p0": ("J2", 3.3),
              "S9SL_X6sa875_J2_B_top_Fs4_r3p85_p0": ("J2", 3.85), "S9SL_X6rb_J1_B_top_Fs4_rm2p86_p0": ("J1", -2.86),
              "S9SL_X6rbp_J1_B_top_Fs4_r2p86_p0": ("J1", 2.86)}
    for name, (soil, roll) in floors.items():
        a = ap.parse_args(rows[name]["argv"][len(s9_batch.RUN):] + ["--case", name, "--out-root", "x"])
        assert (a.soil, a.pad_variant, a.level, a.fs_kN, a.duration, a.start_limit) == (
            soil, "dwg_rear250", "top", 4.0, 160.0, "record_only")
        assert (a.floor_roll, a.floor_pitch, a.seed, a.mass_scale) == (roll, 0.0, 20261026, 1.0)
    assert [bool(rows[n].get("optional")) for n in floors] == [False, True, True, False, True]
    rb, rbp = rows["S9SL_X6rb_J1_B_top_Fs4_rm2p86_p0"], rows["S9SL_X6rbp_J1_B_top_Fs4_r2p86_p0"]
    assert (rb["direction"], rb["k"], rbp["direction"], rbp["k"]) == ("roll_neg", 0.65, "roll_pos", 0.65)
    assert rb["harness_case"] == "H9|J1|B|top|roll_neg@k0.65" and rbp["harness_case"] == "H9|J1|B|top|roll_pos@k0.65"
    assert rb["h9_result"] == run_S9.RV6_H9_RESULT == "06_analysis/02_control/s9/rev85/h9_roll_fine.json"
    assert "met" in rb["requires"]
    # the x-direction is X6-rbp / X6-rbn by --rv6-dir
    alt = _by_case(s9_batch.batches(rv6_dir="roll_pos")["RV6"])
    assert "S9SL_X6rb_J1_B_top_Fs4_r2p86_p0" in alt and "S9SL_X6rbn_J1_B_top_Fs4_rm2p86_p0" in alt
    with pytest.raises(ValueError):
        run_S9.rv6_cases(0.65, "pitch")
    assert rows["S9SL_X6sa75_J2_B_top_Fs4_r3p3_p0"]["harness_case"] == "H3|J2|B|top|roll_pos@k0.75"
    assert rows["S9SL_X6sa875_J2_B_top_Fs4_r3p85_p0"]["harness_case"] == "H3|J2|B|top|roll_pos@k0.875"


@pytest.mark.parametrize("k, tag, roll", [(0.65, "rm2p86", -2.86), (0.6, "rm2p64", -2.64), (0.7, "rm3p08", -3.08)])
def test_rv6_k_argument(k, tag, roll) -> None:
    assert (run_S9.RV6_K_DEFAULT, run_S9.RV6_DIR_DEFAULT) == (0.65, "roll_neg")
    rows = s9_batch.batches(rv6_k=k)["RV6"]
    rb = rows[3]
    assert rb["case"] == f"S9SL_X6rb_J1_B_top_Fs4_{tag}_p0" and rb["k"] == k
    assert float(rb["argv"][rb["argv"].index("--floor-roll") + 1]) == roll
    assert float(rows[4]["argv"][rows[4]["argv"].index("--floor-roll") + 1]) == -roll
    assert [r["case"] for r in rows[:3]] == [r["case"] for r in s9_batch.batches()["RV6"][:3]]
    with pytest.raises(ValueError):
        run_S9.rv6_cases(0.3)
    argv = ["run", "RV6", "--rv6-k", str(k), "--rv6-dir", "roll_pos"]
    a = s9_batch.build_parser().parse_args(argv)
    assert (a.rv6_k, a.rv6_dir) == (k, "roll_pos")
    assert s9_batch.build_parser().parse_args(["list", "RV6"]).rv6_dir is None


def test_final6_event_rows_wait_for_their_base(b) -> None:
    rows = b["FINAL6"]
    names = {r["case"] for r in rows}
    deps = [r for r in rows if r.get("depends_on")]
    assert len(deps) == 2 and all(r["depends_on"] in names for r in deps)
    q = s9_batch.schedule_cases(rows)
    assert len(q["pcore"]) == 6


def test_source_args_check_on_the_former_runs(b) -> None:
    """Rows with a former run reproduce its result.json args (only the rows whose former run exists here)."""
    checked = 0
    for name in SOIL:
        doc = s9_batch.check_sources(name, b[name])
        assert doc["ok"], [r for r in doc["rows"] if r["status"] == "differs"]
        checked += sum(1 for r in doc["rows"] if r["status"] == "ok")
    if checked == 0:
        pytest.skip("no former run folders under 07_results/S9")


def test_source_args_check_detects_a_difference(tmp_path, b) -> None:
    row = _by_case(b["FINAL1"])["P3b_J1_B_top_Fs4"]
    tail = row["argv"][len(s9_batch.RUN):]
    a = vars(run_S9.build_parser().parse_args(tail + ["--case", "P3b_J1_B_top_Fs4", "--out-root", "x"]))
    a.pop("expect_controller")
    (tmp_path / "result.json").write_text(json.dumps({"args": a}), "utf-8")
    assert run_S9.source_args_check(tail, tmp_path)["status"] == "ok"
    a["fs_kN"] = 8.0
    (tmp_path / "result.json").write_text(json.dumps({"args": a}), "utf-8")
    chk = run_S9.source_args_check(tail, tmp_path)
    assert chk["status"] == "differs" and [d["key"] for d in chk["diffs"]] == ["fs_kN"]
    # an option the former run did not have must keep its default
    a["fs_kN"] = 4.0
    a.pop("mass_scale")
    (tmp_path / "result.json").write_text(json.dumps({"args": a}), "utf-8")
    assert run_S9.source_args_check(tail, tmp_path)["status"] == "ok"
    x5 = _by_case(b["FINAL2"])["P3b_J2_B_top_Fs4_m1p1"]["argv"][len(s9_batch.RUN):]
    assert run_S9.source_args_check(x5, tmp_path)["status"] == "differs"
    shutil.rmtree(tmp_path / "missing", ignore_errors=True)
    assert run_S9.source_args_check(tail, tmp_path / "missing")["status"] == "no_source"


def test_controller_expectation_on_the_preset() -> None:
    from outrigger_sim.control.c2 import C2Config

    assert run_S9.FINAL_CONTROLLER == "final_SGS_R4"  # spec 429.11 (was final_P36sa)
    want = dict(run_S9.CONTROLLER_EXPECTATIONS[run_S9.FINAL_CONTROLLER])
    assert want["lift_stroke_guard.soil_stop"] is True and want["lift_stroke_guard.soil_stop_scope"] == "any_loc"
    assert want["slope_clearance_margin.flat_soil_margin_m"] == 0.03
    assert {"soil.enable", "loc_revoke.enable", "loc_revoke.soil_gate", "loc_revoke.stroke_guard",
            "diff_sink.enable"} <= set(want)  # L1gs / DSb75 checks kept
    assert run_S9.CONTROLLER_ABSENT_OR_OFF[run_S9.FINAL_CONTROLLER] == ("floor_twist_ledger", "attitude_integral_clamp")
    assert run_S9.CONTROLLER_PENDING_CHECKS == {}
    paths_all = list(want) + ["floor_twist_ledger.enable", "attitude_integral_clamp.enable"]

    # the current R8 preset (soil_stop False / flat_soil_margin_m 0.0 until the switch after B1) is refused
    cfg = C2Config().with_10hz_d1()
    rec = run_S9.controller_expectation(cfg, run_S9.FINAL_CONTROLLER)
    assert [c["path"] for c in rec["checks"]] == paths_all and rec["pending_record"] == {}
    if not (cfg.lift_stroke_guard.soil_stop and cfg.slope_clearance_margin.flat_soil_margin_m == 0.03):
        assert not rec["ok"]
        bad = {c["path"] for c in rec["checks"] if not c["ok"]}
        assert bad <= {"lift_stroke_guard.soil_stop", "slope_clearance_margin.flat_soil_margin_m"} and bad
    # the final configuration (both switches on) passes; P37t / ZIC blocks absent in C2Config = ok
    on = C2Config().with_10hz_d1(soil_stop=True, flat_soil_margin_m=0.03)
    rec = run_S9.controller_expectation(on, run_S9.FINAL_CONTROLLER)
    assert rec["ok"], [c for c in rec["checks"] if not c["ok"]]
    assert on.slope_clearance_margin.flat_soil_margin_m == 0.03 and on.lift_stroke_guard.soil_stop_scope == "any_loc"
    # one rule off at a time -> refused at that path only
    no_r4 = C2Config().with_10hz_d1(soil_stop=True, flat_soil_margin_m=0.0)
    rec = run_S9.controller_expectation(no_r4, run_S9.FINAL_CONTROLLER)
    assert [c["path"] for c in rec["checks"] if not c["ok"]] == ["slope_clearance_margin.flat_soil_margin_m"]
    off = replace(on, lift_stroke_guard=replace(on.lift_stroke_guard, soil_stop=False))
    rec = run_S9.controller_expectation(off, run_S9.FINAL_CONTROLLER)
    assert not rec["ok"] and [c["path"] for c in rec["checks"] if not c["ok"]] == ["lift_stroke_guard.soil_stop"]
    no_ds = replace(on, diff_sink=replace(on.diff_sink, enable=False))
    assert not run_S9.controller_expectation(no_ds, run_S9.FINAL_CONTROLLER)["ok"]
    no_l1 = replace(on, loc_revoke=replace(on.loc_revoke, enable=False))
    assert not run_S9.controller_expectation(no_l1, run_S9.FINAL_CONTROLLER)["ok"]

    # P37t / ZIC blocks: absent or enable False passes, enable True / no enable attribute refuses
    class Block:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    class Wrapped:
        def __init__(self, base, **blocks):
            self._base = base
            self.__dict__.update(blocks)

        def __getattr__(self, name):
            return getattr(self._base, name)

    for blocks, ok in (({"floor_twist_ledger": Block(enable=False)}, True),
                       ({"attitude_integral_clamp": Block(enable=False, cap_fraction=0.5)}, True),
                       ({"floor_twist_ledger": Block(enable=True)}, False),
                       ({"attitude_integral_clamp": Block(enable=True)}, False),
                       ({"attitude_integral_clamp": Block(cap_fraction=0.5)}, False)):
        rec = run_S9.controller_expectation(Wrapped(on, **blocks), run_S9.FINAL_CONTROLLER)
        assert rec["ok"] is ok, blocks
        if not ok:
            assert [c["path"] for c in rec["checks"] if not c["ok"]] == [f"{next(iter(blocks))}.enable"]

    class Bare:
        pass

    rec = run_S9.controller_expectation(Bare(), run_S9.FINAL_CONTROLLER)
    assert not rec["ok"]
    assert all(c["got"] == ("<absent>" if c["path"].split(".")[0] in run_S9.CONTROLLER_ABSENT_OR_OFF[
        run_S9.FINAL_CONTROLLER] else "<missing>") for c in rec["checks"])


def test_old_controller_name_is_refused() -> None:
    with pytest.raises(SystemExit):
        run_S9.build_parser().parse_args(["level", "--soil", "J1", "--expect-controller", "final_P36sa"])
    a = run_S9.build_parser().parse_args(["level", "--soil", "J1", "--expect-controller", "final_SGS_R4"])
    assert a.expect_controller == "final_SGS_R4"


def test_expect_controller_absent_by_default() -> None:
    a = run_S9.build_parser().parse_args(["level", "--soil", "J1", "--case", "x", "--out-root", "x"])
    assert not hasattr(a, "expect_controller")
    assert s9_batch.strip_controller_check(["a", "--expect-controller", "final_SGS_R4", "b"]) == ["a", "b"]


def test_final_r_candidates(b) -> None:
    rows = b["FINAL-R"]
    fam: dict[str, int] = {}
    for r in rows:
        fam[r["family"]] = fam.get(r["family"], 0) + 1
        assert r["group"] == "FINAL-R" and r["priority"] == 2 and r["est_s"] > 0
        argv = r["argv"]
        assert argv[argv.index("--only") + 1] == r["case"] and "--approved" in argv
        assert argv[argv.index("--set") + 1] == r["family"]
        assert bool(r.get("s8c")) != bool(r.get("s6c"))
    assert fam == {"p1r": 37, "rest": 48, "g1": 11, "c74": 16, "g8c76_p28acc": 4}
    s6 = [r for r in rows if r.get("s6c")]
    assert [r["case"] for r in s6] == ["G8C1_top_edge_FL_g170", "G8C3_top_edge_FL_g20", "G8C3_top_edge_RL_g230",
                                       "G8C4_top_edge_RR_g230"]
    assert all("--allow-p28-cases" in r["argv"] and r["source_run"].startswith(
        "07_results/S6/bundleC_g8c76_p28acc_p28_L1R_20261027_222426/") for r in s6)
    assert not any("c76_L1R_20261027_211309" in str(r.get("source_run")) for r in rows)
    dup = [r for r in rows if r.get("also_in")]
    assert [(r["case"], r["family"], r["also_in"]) for r in dup] == [("N_D8_top_rpB_Fs8_pressure", "p1r", ["rest"])]
    with pytest.raises(ValueError):
        s9_batch.schedule_cases(rows, e_cases=[rows[0]["case"]], parallel_e=1)
    with pytest.raises(ValueError):
        s9_batch.schedule_cases(rows, e_cases=[rows[-1]["case"]], parallel_e=1)


def test_final_r_s6_rows_match_their_former_batch(tmp_path, b) -> None:
    s6 = [r for r in b["FINAL-R"] if r.get("s6c")]
    src = ROOT / s9_batch.FINAL_R_S6_SOURCE / "batch_meta.json"
    if not src.is_file():
        pytest.skip("former S6 batch not here")
    doc = s9_batch.check_sources("FINAL-R", s6)
    assert doc["ok"] and [r["status"] for r in doc["rows"]] == ["ok"] * 4
    # a changed definition / set is caught
    meta = json.loads(src.read_text("utf-8"))
    meta["plan"]["cases"][0]["duration_s"] = 1.0
    meta["case_set"] = "g8c76"
    d = tmp_path / "S6" / "bx"
    d.mkdir(parents=True)
    (d / "batch_meta.json").write_text(json.dumps(meta), "utf-8")
    row = dict(s6[0], source_run=f"S6/bx/{s6[0]['case']}")
    chk = s9_batch.s6c_source_check(row, root=tmp_path)
    assert chk["status"] == "differs" and {x["key"] for x in chk["diffs"]} >= {"case_set"}


def test_row_filter_and_only_file(tmp_path, b) -> None:
    rows = b["FINAL-R"]
    flt = s9_batch.parse_row_filter(["family=g1,c74"])
    sel = s9_batch.select_rows(rows, None, flt)
    assert len(sel) == 27 and {r["family"] for r in sel} == {"g1", "c74"}
    sel = s9_batch.select_rows(rows, None, s9_batch.parse_row_filter(["family=rest", "also_in=p1r"]))
    assert sel == []
    sel = s9_batch.select_rows(rows, None, s9_batch.parse_row_filter(["family=p1r", "also_in=rest"]))
    assert [r["case"] for r in sel] == ["N_D8_top_rpB_Fs8_pressure"]
    names = [rows[0]["case"], rows[-1]["case"]]
    for text in (json.dumps(names), json.dumps({"cases": names}), f"# acting\n{names[0]}\n{names[1]}  # g8\n"):
        p = tmp_path / "only.txt"
        p.write_text(text, "utf-8")
        assert s9_batch.read_only_file(str(p)) == names
        assert [r["case"] for r in s9_batch.select_rows(rows, names)] == names
    with pytest.raises(ValueError):
        s9_batch.select_rows(rows, ["no_such_case"])
    a = s9_batch.build_parser().parse_args(["run", "FINAL-R", "--only-file", "x.json", "--row-filter", "family=p1r",
                                            "--no-controller-check"])
    assert (a.only_file, a.row_filter, a.no_controller_check) == ("x.json", ["family=p1r"], True)


def test_list_output(b, capsys) -> None:
    s9_batch.main(["list", "FINAL1"])
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "FINAL1 8 rows" and len(out) == 10 and "ctrl=final_SGS_R4" in out[1]
    s9_batch.main(["list"])
    names = [ln.split()[0] for ln in capsys.readouterr().out.splitlines()]
    assert {"RV6", "FINAL1", "FINAL5", "FINAL6", "FINAL-R"} <= set(names)


FINAL_REP = [  # (case, source bundle, rep_variable, r4_x11_check); user list 2026-10-30 ~18 h, spec 432 / 429.11
    ("S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0", "RV6", "A2", False),
    ("S9SL_X6rb_J1_B_top_Fs4_rm2p86_p0", "RV6", "A2", False),
    ("P3b_J1_B_top_Fs4_m1p1", "FINAL2", "B4", True),
    ("P3b_J2_B_top_Fs4_m1p1", "FINAL2", "B4", True),
    ("P3b_J2_B_middle_Fs4", "FINAL2", "B1", False),
    ("P3b_J1_B_top_Fs4", "FINAL1", "기준", False),
    ("P3b_J2_B_top_Fs4", "FINAL1", "기준", False),
]
FINAL_R_REP = {
    "A1": ["K24_top_flat_Fs4"],
    "A2": ["K24_top_fdown3.5_Fs4", "K24_top_fup3.5_Fs4", "K24_top_roll5.5_Fs4", "K24_top_rpB_Fs4"],
    "A3": ["G8C1_top_edge_FL_g170", "G8C3_top_edge_RL_g230", "G8C3_top_edge_FL_g20", "G8C4_top_edge_RR_g230"],
    "A4": ["E_G4_Fs4", "E_SS_Fs4", "E_RE1bF_Fs8", "G1L_RE1bF_FL_top_Fs0", "G1L_RE1bF_FL_top_o050_Fs4"],
    "B1": ["K0V_top_rpB_Fs0", "A_middle_rpB_Fs0", "A_bottom_rpB_Fs0"],
    "B2": ["K8_top_rpB_Fs8"],
}
FINAL_R_REP_OPTIONAL = {"G8C3_top_edge_FL_g20", "G8C4_top_edge_RR_g230"}


def test_final_rep_rows_reuse_the_source_rows(b) -> None:
    rows = b["FINAL-REP"]
    assert [r["case"] for r in rows] == [c for c, *_ in FINAL_REP]
    assert len({r["case"] for r in rows}) == 7
    for r, (case, src, var, x11) in zip(rows, FINAL_REP):
        old = _by_case(b[src])[case]
        # unchanged: id, argv (incl. --expect-controller), source run, pool estimates, controller
        for k in ("case", "argv", "source_run", "est_s", "est_pool_s", "controller", "group", "cid"):
            assert r.get(k) == old.get(k), (case, k)
        assert r["argv"].count("--expect-controller") == 1
        assert r["argv"][r["argv"].index("--expect-controller") + 1] == run_S9.FINAL_CONTROLLER
        assert (r["rep_bundle"], r["rep_source"], r["rep_variable"]) == ("FINAL-REP", src, var)
        assert "zic_gate" not in r  # ZIC rejected (spec 429.11)
        assert bool(r.get("r4_x11_check")) is x11
        assert (r.get("expected_note") == run_S9.FINAL_REP_X11_EXPECTED) is x11
        assert r["rep_variable"] in run_S9.FINAL_REP_VARIABLES
        assert r["priority"] == run_S9.FINAL_REP_PRIORITY == 1
        assert not r.get("optional") and r["note"].startswith(f"FINAL-REP {var}")
    assert [r["case"] for r in rows if r.get("r4_x11_check")] == ["P3b_J1_B_top_Fs4_m1p1", "P3b_J2_B_top_Fs4_m1p1"]
    assert "P3-6" in run_S9.FINAL_REP_X11_EXPECTED and "크롤러 재접촉 0" in run_S9.FINAL_REP_X11_EXPECTED
    # the extension bundles stay as they were
    assert len(b["FINAL1"]) == 8 and len(b["FINAL2"]) == 8 and len(b["RV6"]) == 5


def test_final_r_rep_rows_reuse_the_final_r_rows(b) -> None:
    rows = b["FINAL-R-REP"]
    want = [(v, n) for v, names in FINAL_R_REP.items() for n in names]
    assert [(r["rep_variable"], r["case"]) for r in rows] == want
    assert len(rows) == len({r["case"] for r in rows}) == 18
    fr = _by_case(b["FINAL-R"])
    for r in rows:
        old = fr[r["case"]]
        for k in ("argv", "est_s", "source_run", "group", "family", "engine", "s8c", "s6c", "fixed_pcore"):
            assert r.get(k) == old.get(k), (r["case"], k)
        assert r["argv"] is not old["argv"]  # a copy: the FINAL-R row is not shared
        assert r["rep_bundle"] == "FINAL-R-REP" and r["priority"] == 2
        assert bool(r.get("optional")) is (r["case"] in FINAL_R_REP_OPTIONAL)
    required = s9_batch.select_rows(rows, None, s9_batch.parse_row_filter(["optional=None"]))
    assert len(required) == 16 and not {r["case"] for r in required} & FINAL_R_REP_OPTIONAL
    sel = s9_batch.select_rows(rows, None, s9_batch.parse_row_filter(["rep_variable=A3"]))
    assert len(sel) == 4
    sel = s9_batch.select_rows(rows, ["K24_top_flat_Fs4", "E_SS_Fs4"])
    assert [r["case"] for r in sel] == ["K24_top_flat_Fs4", "E_SS_Fs4"]
    with pytest.raises(KeyError):
        s9_batch.final_r_rep_rows([r for r in b["FINAL-R"] if r["case"] != "E_SS_Fs4"])


def test_rep_meta_keys_reach_batch_json() -> None:
    for k in ("rep_bundle", "rep_source", "rep_variable", "r4_x11_check", "expected_note", "rep_role"):
        assert k in s9_batch.FINAL_ROW_KEYS and k in s9_batch.ENTRY_META_KEYS
    assert "zic_gate" not in s9_batch.FINAL_ROW_KEYS and "zic_gate" not in s9_batch.ENTRY_META_KEYS


def test_rep_list_and_check_sources(b, capsys) -> None:
    s9_batch.main(["list", "FINAL-REP"])
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "FINAL-REP 7 rows" and len(out) == 9
    assert sum(" r4_x11 " in ln for ln in out) == 2 and all("prio=1" in ln for ln in out[1:8])
    assert all("ctrl=final_SGS_R4" in ln for ln in out[1:8])
    s9_batch.main(["list", "FINAL-R-REP"])
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "FINAL-R-REP 18 rows" and sum(" optional " in ln for ln in out) == 2
    doc = s9_batch.check_sources("FINAL-REP", b["FINAL-REP"])
    assert not any(r["status"] == "differs" for r in doc["rows"])


def test_launch_code_state_and_git_state() -> None:
    st = s9_batch.launch_code_state()
    assert set(st["files"]) == set(s9_batch.CODE_HASH_FILES)
    assert all(v is None or len(v) == 64 for v in st["files"].values())
    if shutil.which("git") is None:
        pytest.skip("git not on PATH")
    g = st["git"]
    assert "error" in g or (len(g["head"]) == 40 and isinstance(g["dirty"], list))
