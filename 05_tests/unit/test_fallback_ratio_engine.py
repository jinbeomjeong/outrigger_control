"""U-S8-61 (control spec 302.4 / 304 (1)): R-5 fallback ratio source per engine (no Chrono run).

``outrigger_sim.chrono.fallback_ratio``: L1 / L1-R runs ``plant_meta`` with the plant ratio
``k_r A_p / (k_h A_ann)`` per leg; L2b-NSC and SCM keep the preset ``column_nominal``; a config
without R-5 or with the ``level`` slope is returned unchanged. ``run_S6C.l1_fallback_ratio`` is
the L1 runner hook (``job_bundle_c``).
"""

from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from outrigger_sim.chrono import fallback_ratio as fr
from outrigger_sim.control.c2 import C2Config, C2Controller, FallbackSlope
from outrigger_sim.params import load_params

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "04_scripts" / "02_chrono"

EXPECTED_RATIO = (1.2929, 1.2929, 1.2278, 1.2278)
"""Task C-1 (U-S8-61): FL / FR 1.2929, RL / RR 1.2278 (YAML 2026-10-26)."""


@pytest.fixture(scope="module")
def params():
    return load_params(level="top")


@pytest.fixture(scope="module")
def preset():
    return C2Config().with_10hz_d1()


def _fallback_meta(params, config) -> dict:
    meta = C2Controller.from_params(params, config).meta()
    return {k: v for k, v in meta["r8"]["fast_relevel"].items() if k.startswith("fallback")}


def test_plant_ratio_values(params) -> None:
    ratio = fr.plant_fallback_ratio(params)
    assert len(ratio) == 4
    assert ratio == pytest.approx(EXPECTED_RATIO, abs=5e-5)
    assert ratio[0] == ratio[1] and ratio[2] == ratio[3]  # left / right symmetric


@pytest.mark.parametrize("level", ["middle", "bottom"])
def test_plant_ratio_independent_of_auger_level(params, level) -> None:
    assert fr.plant_fallback_ratio(load_params(level=level)) == fr.plant_fallback_ratio(params)


def test_ratio_formula() -> None:
    leg = SimpleNamespace(rod_stiffness_N_m=3.0e8, head_area_m2=0.0133,
                          head_stiffness_N_m=4.0e8, annulus_area_m2=0.0038)
    (ratio,) = fr.ratio_from_leg_params([leg])
    assert ratio == pytest.approx(3.0e8 * 0.0133 / (4.0e8 * 0.0038), rel=1e-15)


@pytest.mark.parametrize("engine", ["L1", "L1R", "L1-R"])
def test_l1_engines_take_plant_meta(params, preset, engine) -> None:
    cfg, meta = fr.with_engine_fallback_ratio(preset, engine, params)
    got = cfg.r8.fast_relevel
    assert str(got.fallback_ratio_source) == "plant_meta"
    assert got.fallback_plant_ratio == fr.plant_fallback_ratio(params)
    assert meta["applied"] is True and meta["fallback_plant_ratio"] == list(got.fallback_plant_ratio)
    # only the ratio keys of r8.fast_relevel change
    assert replace(cfg, r8=preset.r8) == preset
    assert replace(got, fallback_ratio_source=preset.r8.fast_relevel.fallback_ratio_source,
                   fallback_plant_ratio=None) == preset.r8.fast_relevel
    # the controller meta records the setting
    m = _fallback_meta(params, cfg)
    assert m["fallback_slope"] == "nominal_gap" and m["fallback_ratio_source"] == "plant_meta"
    assert m["fallback_plant_ratio"] == pytest.approx(EXPECTED_RATIO, abs=5e-5)


@pytest.mark.parametrize("engine", ["L2b_NSC", "L2b", "SCM", "S9"])
def test_l2b_and_scm_keep_the_preset(params, preset, engine) -> None:
    cfg, meta = fr.with_engine_fallback_ratio(preset, engine, params)
    assert cfg is preset
    assert meta["applied"] is False and meta["fallback_ratio_source"] == "column_nominal"
    m = _fallback_meta(params, cfg)
    assert m["fallback_ratio_source"] == "column_nominal" and m["fallback_plant_ratio"] is None


def test_given_ratio_is_used(preset) -> None:
    cfg, meta = fr.with_engine_fallback_ratio(preset, "L1R", plant_ratio=(1.1, 1.2, 1.3, 1.4))
    assert cfg.r8.fast_relevel.fallback_plant_ratio == (1.1, 1.2, 1.3, 1.4)
    assert meta["ratio_origin"] == "given"


def test_r5_off_and_level_slope_unchanged(params, preset) -> None:
    r7 = C2Config()
    assert r7.r8.fast_relevel is None
    cfg, meta = fr.with_engine_fallback_ratio(r7, "L1", params)
    assert cfg is r7 and meta["applied"] is False
    level = replace(preset, r8=replace(preset.r8, fast_relevel=replace(
        preset.r8.fast_relevel, fallback_slope=FallbackSlope.LEVEL)))
    cfg, meta = fr.with_engine_fallback_ratio(level, "L1R")  # no params needed: ratio unused
    assert cfg is level and meta["applied"] is False


def test_errors(preset) -> None:
    with pytest.raises(ValueError, match="unknown engine"):
        fr.with_engine_fallback_ratio(preset, "MuJoCo")
    with pytest.raises(ValueError, match="plant_params"):
        fr.with_engine_fallback_ratio(preset, "L1R")


def test_ratio_of_model(params) -> None:
    from outrigger_sim.chrono.rod_chamber_link import leg_params_from_params

    legs, _ = leg_params_from_params(params)
    built = SimpleNamespace(rod_chamber=SimpleNamespace(leg_params=legs), params=None)
    assert fr.plant_fallback_ratio_of_model(built) == fr.plant_fallback_ratio(params)
    no_machine = SimpleNamespace(rod_chamber=SimpleNamespace(leg_params=[]), params=params)
    assert fr.plant_fallback_ratio_of_model(no_machine) == fr.plant_fallback_ratio(params)


@pytest.fixture(scope="module")
def run_s6c():
    """Load ``run_S6C.py`` as a module; import-time env settings are undone afterwards."""
    env = dict(os.environ)
    path = list(sys.path)
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("run_S6C_test_fallback", SCRIPTS / "run_S6C.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        os.environ.clear()
        os.environ.update(env)
    yield mod
    sys.modules.pop(spec.name, None)
    sys.path[:] = path


def test_run_s6c_l1_hook(run_s6c, params) -> None:
    """``job_bundle_c`` hook on a bundle-C case config: plant_meta with the model's ratio."""
    case = run_s6c.case_table()["C1_D8_top_roll5.5_b1.6"]
    base = run_s6c.controller_config(params, case)
    assert str(base.r8.fast_relevel.fallback_ratio_source) == "column_nominal"
    from outrigger_sim.chrono.rod_chamber_link import leg_params_from_params

    legs, _ = leg_params_from_params(params)
    model = SimpleNamespace(rod_chamber=SimpleNamespace(leg_params=legs), params=params)
    cfg, meta = run_s6c.l1_fallback_ratio(base, model)
    assert meta["applied"] is True and meta["ratio_origin"].startswith("model.rod_chamber")
    assert str(cfg.r8.fast_relevel.fallback_ratio_source) == "plant_meta"
    assert cfg.r8.fast_relevel.fallback_plant_ratio == pytest.approx(EXPECTED_RATIO, abs=5e-5)
    # R7 config (stage 2 style): unchanged, the model is not read
    r7 = C2Config()
    cfg7, meta7 = run_s6c.l1_fallback_ratio(r7, SimpleNamespace())
    assert cfg7 is r7 and meta7["applied"] is False


def _legs_model(params):
    from outrigger_sim.chrono.rod_chamber_link import leg_params_from_params

    legs, _ = leg_params_from_params(params)
    return SimpleNamespace(rod_chamber=SimpleNamespace(leg_params=legs), params=params)


def test_run_s6c_l1_override_env_and_cli(run_s6c, params, monkeypatch, capsys) -> None:
    """B(iii): env -> meta ``env`` + stdout warning; CLI wins over env; bad values raise."""
    assert run_s6c.L1_FALLBACK_SOURCE_ENV == fr.L1_FALLBACK_SOURCE_ENV
    base = C2Config().with_10hz_d1()
    monkeypatch.setenv(fr.L1_FALLBACK_SOURCE_ENV, "column_nominal")
    cfg, meta = run_s6c.l1_fallback_ratio(base, SimpleNamespace())
    assert cfg is base and meta["applied"] is False
    assert meta["fallback_ratio_source_override"] == "env"
    assert meta["override_value"] == "column_nominal"
    assert "WARNING" in capsys.readouterr().out
    # the CLI value wins over the environment variable (no warning then)
    cfg, meta = run_s6c.l1_fallback_ratio(base, _legs_model(params), "plant_meta")
    assert meta["applied"] is True and meta["fallback_ratio_source_override"] == "cli"
    assert "WARNING" not in capsys.readouterr().out
    monkeypatch.setenv(fr.L1_FALLBACK_SOURCE_ENV, "online")
    with pytest.raises(ValueError):
        run_s6c.l1_fallback_ratio(base, SimpleNamespace())
    monkeypatch.delenv(fr.L1_FALLBACK_SOURCE_ENV)
    with pytest.raises(ValueError):
        run_s6c.l1_fallback_ratio(base, SimpleNamespace(), "online")
    cfg, meta = run_s6c.l1_fallback_ratio(base, _legs_model(params))
    assert meta["applied"] is True and meta["fallback_ratio_source_override"] is None
    cfg, meta = run_s6c.l1_fallback_ratio(base, SimpleNamespace(), "column_nominal")
    assert cfg is base and meta["fallback_ratio_source_override"] == "cli"


# --- B(i): ratio provenance --------------------------------------------------------------------


def test_source_meta_yaml_plant(run_s6c, params) -> None:
    cfg, meta = run_s6c.l1_fallback_ratio(C2Config().with_10hz_d1(), _legs_model(params))
    src = meta["fallback_plant_ratio_source"]
    assert src == {"kind": "plant_params", "ratio_override_keys": [],
                   "dead_length_override_keys": [], "known_plant_ratio_upper": False}
    assert meta["fallback_plant_ratio"] == list(cfg.r8.fast_relevel.fallback_plant_ratio)


def test_source_meta_l0r_override_marks_upper(run_s6c) -> None:
    case = run_s6c.case_table()["C5_L0r0.1_top_fdown3.2"]
    over = run_s6c.param_overrides(case)
    plant = load_params(level="top", overrides=over)
    cfg, meta = run_s6c.l1_fallback_ratio(C2Config().with_10hz_d1(), _legs_model(plant))
    src = meta["fallback_plant_ratio_source"]
    assert src["known_plant_ratio_upper"] is True
    assert src["dead_length_override_keys"]
    assert all(k.startswith("actuator.rod_side.column_length_m") for k in src["dead_length_override_keys"])
    assert set(src["dead_length_override_keys"]) <= set(src["ratio_override_keys"])
    # the L_0r change moves the ratio away from the YAML plant
    assert cfg.r8.fast_relevel.fallback_plant_ratio != pytest.approx(EXPECTED_RATIO, abs=5e-5)


def test_source_meta_beta_override_not_upper(run_s6c) -> None:
    case = run_s6c.case_table()["C1_D8_top_roll5.5_b1.6"]
    plant = load_params(level="top", overrides=run_s6c.param_overrides(case))
    src = fr.plant_ratio_source_meta(plant)
    assert "actuator.oil_bulk_modulus_eff_Pa" in src["ratio_override_keys"]
    assert src["known_plant_ratio_upper"] is False


def test_ratio_override_keys_filter() -> None:
    fake = SimpleNamespace(overrides={
        "actuator.oil_dead_length_m": 0.08, "actuator.rod_side.column_length_m.RR": 0.1,
        "legs.FL.cylinder.bore_diameter_m": 0.13, "legs.FL.moving_part.mass_kg": 1.0,
        "contact.rigid_floor.L1.kn_per_pad_N_m": 1e8, "actuator.frame_stiffness_N_m": 1e9})
    assert fr.ratio_override_keys(fake) == [
        "actuator.oil_dead_length_m", "actuator.rod_side.column_length_m.RR",
        "legs.FL.cylinder.bore_diameter_m"]
    src = fr.plant_ratio_source_meta(fake)
    assert src["dead_length_override_keys"] == ["actuator.oil_dead_length_m",
                                                "actuator.rod_side.column_length_m.RR"]
    assert src["known_plant_ratio_upper"] is True


def test_add_to_controller_meta(params) -> None:
    cfg, meta = fr.with_engine_fallback_ratio(C2Config().with_10hz_d1(), "L1R", params)
    meta["fallback_ratio_source_override"] = None
    cm = C2Controller.from_params(params, cfg).meta()
    fr.add_to_controller_meta(cm, meta)
    fast = cm["r8"]["fast_relevel"]
    assert fast["fallback_ratio_source"] == "plant_meta"
    assert fast["fallback_plant_ratio"] == pytest.approx(EXPECTED_RATIO, abs=5e-5)
    assert fast["fallback_plant_ratio_source"]["kind"] == "plant_params"
    assert "fallback_ratio_source_override" in fast
    r7 = C2Controller.from_params(params, C2Config()).meta()
    before = repr(r7)
    fr.add_to_controller_meta(r7, meta)  # R-5 off: nothing to add to
    assert repr(r7) == before


# --- B(iii): batch runners refuse the env override -----------------------------------------------


def test_refuse_env_override(monkeypatch, capsys) -> None:
    monkeypatch.delenv(fr.L1_FALLBACK_SOURCE_ENV, raising=False)
    assert fr.refuse_env_override(False, "x") is None
    monkeypatch.setenv(fr.L1_FALLBACK_SOURCE_ENV, "column_nominal")
    with pytest.raises(SystemExit, match="allow-env-override"):
        fr.refuse_env_override(False, "x")
    assert fr.refuse_env_override(True, "x") == "column_nominal"
    assert "WARNING" in capsys.readouterr().out


def _load_script(name: str, path: Path):
    env = dict(os.environ)
    sys.path.insert(0, str(path.parent))
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        os.environ.clear()
        os.environ.update(env)
    return mod


@pytest.mark.parametrize(("script", "argv"), [
    ("run_S6C.py", ["run", "--approved"]),
    ("run_S6C.py", ["check"]),
    ("run_S7C.py", ["run", "--approved"]),
    ("run_S8C.py", ["run", "--approved"]),
    ("s9_batch.py", ["run", "P3-10"]),
])
def test_batch_runners_refuse_env_override(script, argv, monkeypatch) -> None:
    path = list(sys.path)
    try:
        mod = _load_script(f"{script[:-3]}_env_guard_test", SCRIPTS / script)
        monkeypatch.setenv(fr.L1_FALLBACK_SOURCE_ENV, "column_nominal")
        with pytest.raises(SystemExit, match="allow-env-override"):
            mod.main(argv)
    finally:
        sys.modules.pop(f"{script[:-3]}_env_guard_test", None)
        sys.path[:] = path


def test_run_s8c_controller_returns_fallback_meta() -> None:
    """run_S8C ``_controller`` hands the L2b-NSC fallback meta on (written as ``fallback_ratio``
    in bundle_c / the ML base settings, like run_S7C / run_S9); the preset stays column_nominal."""
    path = list(sys.path)
    try:
        mod = _load_script("run_S8C_fallback_meta_test", SCRIPTS / "run_S8C.py")
        case = mod.case_table()["E_RE1bF_Fs0"]
        assert case.lock_valve != "counterbalance"  # the plant params are then not read
        plant = load_params(level=case.base.scenario.level)
        c2, cfg, _settle, meta = mod._controller(case, plant, None)
        assert meta["applied"] is False and meta["fallback_ratio_source"] == "column_nominal"
        assert str(cfg.r8.fast_relevel.fallback_ratio_source) == "column_nominal"
        assert c2.config is cfg
    finally:
        sys.modules.pop("run_S8C_fallback_meta_test", None)
        sys.path[:] = path


def test_m3_run_cli(monkeypatch) -> None:
    path = list(sys.path)
    try:
        mod = _load_script("m3_run_cli_test", SCRIPTS / "s9_merge" / "m3_run.py")
        a = mod.parse_args(["rpB", "on", "out", "--fallback-ratio-source", "column_nominal"])
        assert (a.key, a.variant, a.duration, a.fallback_ratio_source) == (
            "rpB", "on", None, "column_nominal")
        a = mod.parse_args(["flat", "off", "out", "3.0"])
        assert a.duration == 3.0 and a.fallback_ratio_source is None
        with pytest.raises(SystemExit):
            mod.parse_args(["rpB", "on", "out", "--fallback-ratio-source", "online"])
        with pytest.raises(SystemExit, match="L1 keys only"):
            mod.main(["s8_re1bf", "on", "out", "--fallback-ratio-source", "plant_meta"])
    finally:
        sys.modules.pop("m3_run_cli_test", None)
        sys.path[:] = path


def test_module_has_no_top_level_pychrono_import() -> None:
    text = Path(fr.__file__).read_text(encoding="utf-8")
    top = [line for line in text.splitlines() if line.startswith(("import ", "from "))]
    assert not any("pychrono" in line or "rod_chamber_link" in line for line in top)
