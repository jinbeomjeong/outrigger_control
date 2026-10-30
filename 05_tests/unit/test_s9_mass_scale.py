"""Q-D (2026-10-29): ``run_S9.py level --mass-scale`` and the MS1 batch row (no Chrono run beyond one ChBody)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

import run_S9  # noqa: E402

MS1_NAME = "P3b_J1_B_top_Fs4_m1p1"
BATCH_DEF_SHA256 = {
    "E_dual": "2b3232627472913c35c245d903ca24996a9d2bf27f14389727cc86c958ed7bee",
    "G6": "3e60f3f2a05aba3e5dcfda9c35950ccd6feba77dad407375031a1a0023594f67",
    "G6P": "81e1abb2e7093c0e9e40f4c665e875cbb5eb2c2e952115d2a4b4686568e6fc73",
    "G6_opt": "1a77342aac4ee9add68e003a159a221c6d94225787caa396f06bd78a25636376",
    "P1_L": "96c926917d6f7d5de2abdc52daa917d9e953308d03e5c87a10f2f0b71875ef1c",
    "P1_V0p": "04436ab9f4b7789728899d51e72501cad2e514588ab7a74e0b6dd6df2fefc68d",
    "P1_V16": "59c0601d4e60543533e293a32d3ee9fd598a0931f3cc2e7ce04533b9be21f7f7",
    "P2": "428f4fc993e7050457998aaaf1fc8ab868035d175fa5295ef26391a21af09070",
    "P2prime": "b5d704faeefdfb9bb6972361b0754eef53a2aee33065a906918855d7abaf035a",
    "P3-10": "0d9c3fe04d294403612d1a22e06f4046e912d6d87f0c495dacc952fcd417b483",
    "P3a": "dfde9d2097a55c9bff472536ed613fa32d2c1e435d541c2e692fc1153c7b611b",
    "P3b": "6793b3bd29eda4861b244535f43a786a2bfb01ef2fff06d0c97f7544bbc7687b",
    "S9SL": "1e80cba9a0bd75abeb0307a949511afba093fe7b7b8a910096cbde88ec335837",
    "p3b_aug": "98f48ac2eccc2bbf3849d6d18f79e755433468271772f23d91d91c788be4cd79",
    "MS1": "5dc833dd79c1564f20d175c4c648d1fdae2f3060b58bfd6c0f5e5835a496215d",  # run 2026-10-29 18:33
    "D424": "c8c74d0efa95790a74c623177098f7641f7cb5fd45c29da6d3ee166163a6a84f",  # run 2026-10-30 01:49
    "D424R": "0bce854f7f764b80712ca06dc70923b6729c55350ca520610e99230e75c516b2",  # run 2026-10-30 07:36
}
"""Normalised batch definitions (interpreter / script paths dropped) before the Q-D change (2026-10-29)."""


def _norm(s9_batch, argv):
    out = []
    for a in argv:
        s = str(a)
        if s == s9_batch.PY:
            s = "<PY>"
        elif s.startswith(str(s9_batch.HERE)):
            s = "<HERE>/" + Path(s).name
        out.append(s)
    return out


def test_existing_batch_definitions_unchanged() -> None:
    import s9_batch

    b = s9_batch.batches()
    # RV1 .. RV5: test_s9_rv{1..5}.py; RV6 / FINAL* (incl. FINAL-REP / FINAL-R-REP): test_s9_final.py
    assert set(b) == set(BATCH_DEF_SHA256) | {"RV1", "RV2", "RV3", "RV4", "RV5", "RV6", "FINAL1", "FINAL2", "FINAL3",
                                              "FINAL4", "FINAL5", "FINAL6", "FINAL-R", "FINAL-REP", "FINAL-R-REP",
                                              "FINAL-REP-X"}
    for name, want in BATCH_DEF_SHA256.items():
        rows = [{**r, "argv": _norm(s9_batch, r["argv"])} for r in b[name]]
        assert hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest() == want, name


def test_ms1_row_is_p3b_j1_b_top_plus_mass_scale() -> None:
    import s9_batch

    rows = s9_batch.batches()["MS1"]
    assert [r["case"] for r in rows] == [MS1_NAME]
    row = rows[0]
    assert row["est_s"] == run_S9.MS1_EST_S and row["note"].startswith("pair P3b_J1_B_top_Fs4")
    p3b = {r["case"]: r for r in s9_batch.batches()["P3b"]}
    base = p3b["P3b_J1_B_top_Fs4"]["argv"]
    argv = row["argv"]
    i = argv.index("--note")
    assert argv[:i] + argv[-1:] == base  # P3b settings unchanged, extra options only before --approved
    assert argv[i:-1] == ["--note", row["note"], "--mass-scale", "1.1"]
    ap = run_S9.build_parser()
    a = ap.parse_args(argv[len(s9_batch.RUN):] + ["--case", MS1_NAME, "--out-root", "x"])
    assert (a.soil, a.pad_variant, a.level, a.fs_kN, a.grid, a.crawler_grid) == (
        "J1", "dwg_rear250", "top", 4.0, 0.01, 0.04)
    assert (a.duration, a.pressure_grade, a.imu_grade, a.seed, a.threads) == (120.0, "normal", "ideal", 20261026, 4)
    assert a.mass_scale == 1.1 and a.start_limit == "preset" and a.twist_relax == "preset"
    q = s9_batch.schedule_cases(rows, e_cases=[MS1_NAME], parallel_e=1)
    assert q["pcore"] == [] and [c["case"] for c in q["ecore"]] == [MS1_NAME]
    # case_plan stays as it was (test_s9_rev420_records CASE_DIGEST): MS1 is listed by s9_batch only
    assert MS1_NAME not in {r["case"] for r in run_S9.case_plan()}


def test_d424_rows() -> None:
    """Spec 424.6 A-8: the MS1 re-run has the MS1 case name and argv (batch folder = tag); x1.2 differs only in the
    case name, the note and the scale."""
    import s9_batch

    b = s9_batch.batches()
    ms1, d424 = b["MS1"][0], b["D424"]
    assert [r["case"] for r in d424] == [MS1_NAME, "P3b_J1_B_top_Fs4_m1p2"]
    assert d424[0]["argv"] == ms1["argv"] and d424[0]["est_s"] == run_S9.D424_EST_S["m1p1"]
    a12 = d424[1]["argv"]
    i = a12.index("--note")
    assert a12[:i] == ms1["argv"][:i] and a12[-1] == "--approved"
    assert a12[i:-1] == ["--note", d424[1]["note"], "--mass-scale", "1.2"]
    assert d424[1]["est_s"] == run_S9.D424_EST_S["m1p2"]
    assert [c["case"] for c in run_S9.d424_cases(include_optional=False)] == [MS1_NAME]
    assert run_S9.build_parser().parse_args(a12[len(s9_batch.RUN):]).mass_scale == 1.2


D424R_NAMES = [MS1_NAME, "P3b_J2_B_middle_Fs4", "P3b_J2_B_bottom_Fs4"]


def test_d424r_rows_same_argv_as_former_runs() -> None:
    """Spec 424.11.2 'Chrono 3건' (2026-10-30): ① = the D424 / MS1 row (argv bit for bit), ② / ③ = the study ③ J2 B
    middle / bottom rows (argv bit for bit, no --note); notes and the planned pool are batch.json-only keys."""
    import s9_batch

    b = s9_batch.batches()
    rows = b["D424R"]
    assert [r["case"] for r in rows] == D424R_NAMES
    assert rows[0]["argv"] == b["D424"][0]["argv"] == b["MS1"][0]["argv"]
    aug = {r["case"]: r for r in b["p3b_aug"]}
    for r in rows[1:]:
        assert r["argv"] == aug[r["case"]]["argv"] and "--note" not in r["argv"]
        assert r["note"].startswith("424.11.2 Chrono 3건")
    assert [r["planned_pool"] for r in rows] == ["pcore", "ecore", "ecore"]
    assert tuple(r["case"] for r in rows if r["planned_pool"] == "ecore") == run_S9.D424R_E_CASES
    # est_s: measured former walls; E rows x 1.67 rounded to 100 s
    assert [r["est_s"] for r in rows] == [5919.0, 10700.0, 10600.0]
    assert all(r["est_s"] == run_S9.d424r_est_s(r["case"]) for r in rows)
    for c in run_S9.d424r_cases():
        assert c["group"] == "D424R"
    # former run folders named in the table exist when results are on disk
    for case, (folder, pool, wall) in run_S9.D424R_MEASURED_WALL_S.items():
        bj = ROOT / "07_results" / "S9" / folder / "batch.json"
        if bj.exists():
            ent = {e["case"]: e for e in json.loads(bj.read_text("utf-8"))["cases"]}[case]
            assert ent["pool"] == pool and ent["rc"] == 0 and round(ent["wall_s"], 1) == wall


@pytest.mark.parametrize("e_tokens", [["P3b_J2_B_middle_Fs4,P3b_J2_B_bottom_Fs4"],
                                      ["P3b_J2_B_middle_Fs4", "P3b_J2_B_bottom_Fs4"]])
def test_d424r_schedule_command(e_tokens) -> None:
    """The documented command splits the pools: ① alone on P, ② / ③ on E (comma or space separated names)."""
    import s9_batch

    argv = ["run", "D424R", "--parallel", "1", "--parallel-e", "2", "--e-cases", *e_tokens]
    kw = s9_batch.schedule_args(s9_batch.build_parser().parse_args(argv), argv)
    assert kw["e_cases"] == D424R_NAMES[1:] and (kw["parallel"], kw["parallel_e"]) == (1, 2)
    q = s9_batch.schedule_cases(s9_batch.batches()["D424R"], e_cases=kw["e_cases"], parallel_e=kw["parallel_e"])
    assert [c["case"] for c in q["pcore"]] == [MS1_NAME]
    assert [c["case"] for c in q["ecore"]] == D424R_NAMES[1:]
    assert s9_batch.split_names(None) is None and s9_batch.split_names(["a,,b", "c"]) == ["a", "b", "c"]


def test_d424r_batch_folder_is_rejudge_target(tmp_path) -> None:
    """``run_S9.py rejudge <batch folder>`` picks every D424R case folder (all names start with P3b_)."""
    for n in D424R_NAMES:
        (tmp_path / n).mkdir()
        (tmp_path / n / "result.json").write_text("{}", "utf-8")
    assert [p.name for p in run_S9.rejudge_targets([str(tmp_path)])] == sorted(D424R_NAMES)


def test_level_default_mass_scale_and_p3b_argv_without_it() -> None:
    ap = run_S9.build_parser()
    for c in run_S9.p3b_cases() + run_S9.g6p_cases() + run_S9.s9sl_cases():
        argv = run_S9.p3b_level_argv(c)
        assert "--mass-scale" not in argv
        assert ap.parse_args(argv).mass_scale == 1.0


def _params():
    from outrigger_sim.params import load_params

    return load_params(level="top", model="L2b_NSC")


def _body(params):
    from outrigger_sim.chrono.bodies import BodyPose, make_superstructure

    return make_superstructure(params, BodyPose((0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)))


def _state(body):
    xx, xy, p = body.GetInertiaXX(), body.GetInertiaXY(), body.GetPos()
    return (body.GetMass(), xx.x, xx.y, xx.z, xy.x, xy.y, xy.z, p.x, p.y, p.z)


def test_apply_mass_scale_one_is_untouched_and_weight_exact() -> None:
    params = _params()
    body = _body(params)
    before = _state(body)
    rec = run_S9.apply_mass_scale(SimpleNamespace(superstructure=body), params, 1.0)
    assert _state(body) == before
    assert rec["plant_weight_N"] == run_S9.model_weight_N(params) == rec["yaml_weight_N"]
    assert run_S9.model_weight_N(params, 1.0) == (params.superstructure.mass_properties.mass_kg
                                                  + sum(leg.moving_part.mass_kg for leg in params.legs)) * run_S9.G


def test_apply_mass_scale_scales_mass_inertia_keeps_cog() -> None:
    params = _params()
    body = _body(params)
    m0, *rest = _state(body)
    pos0 = rest[6:]
    rec = run_S9.apply_mass_scale(SimpleNamespace(superstructure=body), params, 1.1)
    props = params.superstructure.mass_properties
    assert body.GetMass() == pytest.approx(1.1 * props.mass_kg, rel=1e-15)
    np.testing.assert_allclose(rec["plant_superstructure_inertia_cog_body_kg_m2"],
                               1.1 * np.asarray(props.inertia_kg_m2), rtol=1e-14)
    p = body.GetPos()
    assert (p.x, p.y, p.z) == tuple(pos0)
    assert rec["plant_weight_N"] == pytest.approx(run_S9.model_weight_N(params) + 0.1 * props.mass_kg * run_S9.G,
                                                  rel=1e-14)
    assert rec["mass_scale"] == 1.1 and rec["yaml_superstructure_mass_kg"] == props.mass_kg
    for bad in (0.0, -1.0, float("nan")):
        with pytest.raises(ValueError):
            run_S9.apply_mass_scale(SimpleNamespace(superstructure=_body(params)), params, bad)


W_REF = 376_583.56424339
P37_ADDED = {"mass_scale", "W_plant_N", "loaded_threshold_basis"}


def test_p37_threshold_w_plant() -> None:
    """Spec 422.6: loaded-window threshold 0.01 W_plant (= 0.01 W_ref bit for bit at scale 1); W_ref kept."""
    blk1 = run_S9.p37_plateau_block(np.zeros(1), np.zeros(1), [], None, None, {"W_ref_N": W_REF}, None)
    assert blk1["loaded_threshold_N"] == run_S9.P37_LOADED_FRACTION * W_REF  # former expression
    assert blk1["W_plant_N"] == W_REF and blk1["W_ref_N"] == W_REF and blk1["mass_scale"] == 1.0
    blk = run_S9.p37_plateau_block(np.zeros(1), np.zeros(1), [], None, None, {"W_ref_N": W_REF}, None,
                                   mass_scale=1.1)
    assert blk["loaded_threshold_N"] == pytest.approx(0.01 * 1.1 * W_REF, rel=1e-15)
    assert blk["W_ref_N"] == W_REF and blk["W_plant_N"] == pytest.approx(1.1 * W_REF, rel=1e-15)


def test_judgement_weights_and_rejudge_scale() -> None:
    w = run_S9.judgement_weights(1.1, 417_771.27, W_REF, 9415.0)
    assert w["W_plant_N"] == pytest.approx(1.1 * W_REF) and w["W_ref_N"] == W_REF
    assert w["P3-7_loaded_threshold_N"] == pytest.approx(0.011 * W_REF)
    assert w["F_min_N"] == 9415.0 and w["F_min_x_mass_scale_record_N"] == pytest.approx(10_356.5)
    assert run_S9.rejudge_mass_scale({"args": {}}) == 1.0
    assert run_S9.rejudge_mass_scale({"args": {"mass_scale": 1.0}, "mass_scale": {"mass_scale": 1.1}}) == 1.1
    assert run_S9.rejudge_mass_scale({"args": {"mass_scale": 1.2}}) == 1.2


STORED = ["batch_p3b_aug_20261029_002839/P3b_J2_B_bottom_Fs4",
          "batch_G6P_20261028_154030/G6_G1_B_top_Fs4_spJ1FL",
          "batch_S9SL_20261028_194403/S9SL_C2_J1_A_top_Fs4_r4p4_p0",
          "batch_P3b_20261027_174330/P3b_J1_B_top_Fs4"]


@pytest.mark.parametrize("rel", STORED)
def test_stored_rejudge_p37_unchanged_at_scale_one(rel) -> None:
    d = ROOT / "07_results" / "S9" / rel
    if not (d / "result.json").exists():
        pytest.skip(f"{rel} not on disk")
    stored = json.loads((d / "result.json").read_text("utf-8"))["p3b"]
    res = run_S9.rejudge_case(d, write=False)
    assert res["unchanged_blocks_equal"], res["unchanged_block_diffs"]
    assert res["judgement_weights"]["mass_scale"] == 1.0
    old_b = stored["P3-7_plateau"]
    new_b = json.loads(json.dumps(run_S9._plain(res["p3b"]["P3-7_plateau"])))
    added = set(new_b) - set(old_b)
    assert added <= P37_ADDED
    # the criterion text names W_plant since the 422.6 wording fix (values unchanged)
    assert {k: new_b[k] for k in old_b if k != "criterion"} == {k: v for k, v in old_b.items() if k != "criterion"}
    for k in ("P3-7_within", "P3-7_rise_min_loaded_N", "P3-7_reconstruct_ok"):
        assert res["p3b"]["checks"][k] == stored["checks"][k], k


def test_mass_scale_record_keeps_controller_w_ref() -> None:
    ev = [SimpleNamespace(t_s=30.0, name="WARN_WEIGHT_MISMATCH:1.103"), SimpleNamespace(t_s=31.0, name="x")]
    blk = {"plant_superstructure_weight_N": 1.1 * 376_580.0, "mass_scale": 1.1}
    out = run_S9.mass_scale_record(blk, SimpleNamespace(events=ev), {"soil": {"W_ref_N": 376_580.0}})
    assert out["controller_weight_ref_N"] == 376_580.0
    assert out["plant_over_W_ref"] == pytest.approx(1.1)
    assert out["weight_mismatch_events"] == [[30.0, "WARN_WEIGHT_MISMATCH:1.103"]]
