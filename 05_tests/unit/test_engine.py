"""Unit tests for the SimEngine protocol and Snapshot rules (plan 3.1-3.3, R16).

A pure-Python fake engine (four integrating legs and a one-degree-of-freedom body on a
spring) exercises the contract: zero-order hold, per-step saturation, snapshot round trip,
fingerprint checks and the lifecycle. The engine boundary test checks that ``engine`` does
not pull in pychrono.
"""

from __future__ import annotations

import ast
import contextlib
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from outrigger_sim.engine import (
    AnalyticStart,
    EngineClosedError,
    EngineInfo,
    EngineNotReadyError,
    SimEngine,
    Snapshot,
    SnapshotMismatchError,
    ensure_snapshot_compatible,
)
from outrigger_sim.signals import LEG_COUNT, Command, Measurements, TruthState

GRAVITY_M_S2 = 9.80665
FAKE_DT_S = 1.0e-3
FAKE_STROKE_MAX_M = 0.68
FAKE_BODY_MASS_KG = 1000.0
FAKE_LEG_STIFFNESS_N_M = 1.0e5
FAKE_LEG_DAMPING_N_S_M = 2.0e3
FAKE_HEAD_AREA_M2 = 0.0104
FAKE_PADS_STROKE_M = 0.1
FAKE_INFO = EngineInfo(name="fake", version="1.0", model="heave")
PARAMS_SHA256 = hashlib.sha256(b"params A").hexdigest()
OTHER_PARAMS_SHA256 = hashlib.sha256(b"params B").hexdigest()


def _command(leg_speed_m_s: list[float], t_s: float = 0.0) -> Command:
    return Command(t_s=t_s, leg_speed_m_s=np.array(leg_speed_m_s))


def _zero_command(t_s: float = 0.0) -> Command:
    return _command([0.0] * LEG_COUNT, t_s)


class FakeEngine:
    """Four integrating legs with stroke ends; body heave on the mean leg via a spring."""

    def __init__(self, params_sha256: str = PARAMS_SHA256, info: EngineInfo = FAKE_INFO):
        self._params_sha256 = params_sha256
        self._info = info
        self._is_closed = False
        self._is_ready = False
        self._time_s = 0.0
        self._held_command = _zero_command()
        self._stroke_m = np.zeros(LEG_COUNT)
        self._applied_speed_m_s = np.zeros(LEG_COUNT)
        self._body_z_m = 0.0
        self._body_vz_m_s = 0.0

    # identity properties: readable in every lifecycle state
    @property
    def time_s(self) -> float:
        return self._time_s

    @property
    def dt_s(self) -> float:
        return FAKE_DT_S

    @property
    def params_sha256(self) -> str:
        return self._params_sha256

    @property
    def info(self) -> EngineInfo:
        return self._info

    @property
    def is_closed(self) -> bool:
        return self._is_closed

    def meta(self) -> dict[str, Any]:
        self._require_open()
        return {
            "engine": self._info.name,
            "engine_version": self._info.version,
            "model": self._info.model,
            "dt_s": FAKE_DT_S,
            "params_sha256": self._params_sha256,
        }

    def reset(self, start: AnalyticStart | Snapshot = AnalyticStart.ON_PADS) -> TruthState:
        self._require_open()
        if isinstance(start, Snapshot):
            self._load_snapshot(start)
        elif start is AnalyticStart.ON_PADS:
            self._set_static_state(FAKE_PADS_STROKE_M)
        else:
            self._set_static_state(0.0)
        self._time_s = 0.0
        self._held_command = _zero_command()
        self._applied_speed_m_s = np.zeros(LEG_COUNT)
        self._is_ready = True
        return self.truth()

    def step(self) -> float:
        self._require_ready()
        self._applied_speed_m_s = self._saturated_speed(self._held_command.leg_speed_m_s)
        self._stroke_m = self._stroke_m + self._applied_speed_m_s * FAKE_DT_S
        accel_m_s2 = self._spring_force_N() / FAKE_BODY_MASS_KG - GRAVITY_M_S2
        self._body_vz_m_s += accel_m_s2 * FAKE_DT_S
        self._body_z_m += self._body_vz_m_s * FAKE_DT_S
        self._time_s += FAKE_DT_S
        return self._time_s

    def apply_command(self, command: Command) -> None:
        self._require_ready()
        self._held_command = command

    def measure(self) -> Measurements:
        self._require_ready()
        return Measurements(
            t_s=self._time_s,
            specific_force_m_s2=[0.0, 0.0, GRAVITY_M_S2],
            angular_rate_rad_s=[0.0, 0.0, 0.0],
            head_pressure_Pa=self._leg_force_N() / FAKE_HEAD_AREA_M2,
            stroke_m=self._stroke_m,
        )

    def truth(self) -> TruthState:
        self._require_ready()
        leg_force_N = self._leg_force_N()
        return TruthState(
            t_s=self._time_s,
            body_pos_m=[0.0, 0.0, self._body_z_m],
            body_quat_wxyz=[1.0, 0.0, 0.0, 0.0],
            body_vel_m_s=[0.0, 0.0, self._body_vz_m_s],
            body_omega_rad_s=np.zeros(3),
            s_motor_m=self._stroke_m,
            s_ref_m=self._stroke_m,
            u_applied_m_s=self._applied_speed_m_s,
            F_cyl_N=leg_force_N,
            F_contact_n_N=leg_force_N,
            F_contact_t_N=np.zeros((LEG_COUNT, 2)),
            is_pad_in_contact=leg_force_N > 0.0,
            F_crawler_N=np.zeros(3),
            bushing_anchor_m=np.full((LEG_COUNT, 3), np.nan),
        )

    def snapshot(self) -> Snapshot:
        self._require_ready()
        return Snapshot(
            engine=self._info,
            params_sha256=self._params_sha256,
            time_s=self._time_s,
            held_command=self._held_command,
            payload={
                "stroke_m": self._stroke_m,
                "applied_speed_m_s": self._applied_speed_m_s,
                "body_z_m": self._body_z_m,
                "body_vz_m_s": self._body_vz_m_s,
            },
        )

    def restore(self, snapshot: Snapshot) -> None:
        self._require_open()
        self._load_snapshot(snapshot)
        self._time_s = snapshot.time_s
        self._held_command = snapshot.held_command
        self._is_ready = True

    def close(self) -> None:
        self._is_closed = True

    # --- helpers ---
    def _require_open(self) -> None:
        if self._is_closed:
            raise EngineClosedError("engine is closed")

    def _require_ready(self) -> None:
        self._require_open()
        if not self._is_ready:
            raise EngineNotReadyError("call reset() or restore() first")

    def _load_snapshot(self, snapshot: Snapshot) -> None:
        ensure_snapshot_compatible(snapshot, engine=self._info, params_sha256=self._params_sha256)
        self._stroke_m = np.array(snapshot.payload["stroke_m"])
        self._applied_speed_m_s = np.array(snapshot.payload["applied_speed_m_s"])
        self._body_z_m = float(snapshot.payload["body_z_m"])
        self._body_vz_m_s = float(snapshot.payload["body_vz_m_s"])

    def _set_static_state(self, stroke_m: float) -> None:
        self._stroke_m = np.full(LEG_COUNT, stroke_m)
        sag_m = FAKE_BODY_MASS_KG * GRAVITY_M_S2 / FAKE_LEG_STIFFNESS_N_M
        self._body_z_m = stroke_m - sag_m
        self._body_vz_m_s = 0.0

    def _saturated_speed(self, commanded_m_s: np.ndarray) -> np.ndarray:
        """Stop legs at the stroke ends; checked on every physics step."""
        is_blocked = ((self._stroke_m >= FAKE_STROKE_MAX_M) & (commanded_m_s > 0.0)) | (
            (self._stroke_m <= 0.0) & (commanded_m_s < 0.0)
        )
        allowed_m_s = np.where(is_blocked, 0.0, commanded_m_s)
        headroom_m_s = (FAKE_STROKE_MAX_M - self._stroke_m) / FAKE_DT_S
        return np.clip(allowed_m_s, -self._stroke_m / FAKE_DT_S, headroom_m_s)

    def _spring_force_N(self) -> float:
        compression_m = float(np.mean(self._stroke_m)) - self._body_z_m
        return FAKE_LEG_STIFFNESS_N_M * compression_m - FAKE_LEG_DAMPING_N_S_M * self._body_vz_m_s

    def _leg_force_N(self) -> np.ndarray:
        return np.full(LEG_COUNT, self._spring_force_N() / LEG_COUNT)


def _run_steps(engine: SimEngine, step_count: int) -> None:
    for _ in range(step_count):
        engine.step()


def _assert_same_truth(first: TruthState, second: TruthState) -> None:
    assert first.t_s == second.t_s
    np.testing.assert_array_equal(first.body_pos_m, second.body_pos_m)
    np.testing.assert_array_equal(first.body_vel_m_s, second.body_vel_m_s)
    np.testing.assert_array_equal(first.s_motor_m, second.s_motor_m)
    np.testing.assert_array_equal(first.u_applied_m_s, second.u_applied_m_s)


@pytest.fixture
def engine() -> FakeEngine:
    fake = FakeEngine()
    fake.reset()
    return fake


# --- protocol ----------------------------------------------------------------------------


def test_fake_engine_satisfies_protocol() -> None:
    assert isinstance(FakeEngine(), SimEngine)


def test_object_without_engine_members_is_not_engine() -> None:
    class StepOnly:
        def step(self) -> float:
            return 0.0

    assert not isinstance(StepOnly(), SimEngine)


def test_reset_returns_truth_at_time_zero_with_analytic_start() -> None:
    fake = FakeEngine()
    on_pads = fake.reset(AnalyticStart.ON_PADS)
    assert on_pads.t_s == 0.0
    np.testing.assert_array_equal(on_pads.s_motor_m, np.full(LEG_COUNT, FAKE_PADS_STROKE_M))
    on_crawler = fake.reset(AnalyticStart.ON_CRAWLER)
    np.testing.assert_array_equal(on_crawler.s_motor_m, np.zeros(LEG_COUNT))


def test_step_returns_time_advanced_by_dt(engine: FakeEngine) -> None:
    assert engine.step() == pytest.approx(FAKE_DT_S)
    assert engine.time_s == pytest.approx(FAKE_DT_S)


def test_meta_contains_required_keys(engine: FakeEngine) -> None:
    meta = engine.meta()
    assert {"engine", "engine_version", "model", "dt_s", "params_sha256"} <= set(meta)
    meta["dt_s"] = -1.0
    assert engine.meta()["dt_s"] == FAKE_DT_S


# --- zero-order hold and saturation ------------------------------------------------------


def test_command_is_held_until_the_next_command(engine: FakeEngine) -> None:
    speed_m_s = 0.02
    engine.apply_command(_command([speed_m_s, 0.0, 0.0, 0.0]))
    _run_steps(engine, 20)
    _run_steps(engine, 20)  # no new command: the first one still holds
    expected_m = FAKE_PADS_STROKE_M + 40 * FAKE_DT_S * speed_m_s
    assert engine.truth().s_motor_m[0] == pytest.approx(expected_m, abs=1e-12)

    engine.apply_command(_zero_command(engine.time_s))
    _run_steps(engine, 20)
    assert engine.truth().s_motor_m[0] == pytest.approx(expected_m, abs=1e-12)


def test_reset_clears_held_command(engine: FakeEngine) -> None:
    engine.apply_command(_command([0.02] * LEG_COUNT))
    engine.reset()
    _run_steps(engine, 10)
    np.testing.assert_array_equal(engine.truth().s_motor_m, np.full(LEG_COUNT, FAKE_PADS_STROKE_M))


def test_any_finite_command_is_saturated_on_every_step(engine: FakeEngine) -> None:
    engine.apply_command(_command([1.0e3, -1.0e3, 0.0, 0.0]))
    engine.step()
    stroke_m = engine.truth().s_motor_m
    assert stroke_m[0] == FAKE_STROKE_MAX_M
    assert stroke_m[1] == 0.0


# --- snapshot ----------------------------------------------------------------------------


def test_snapshot_restore_reproduces_uninterrupted_run(engine: FakeEngine) -> None:
    engine.apply_command(_command([0.02, 0.01, -0.01, 0.0]))
    _run_steps(engine, 100)
    saved = engine.snapshot()
    _run_steps(engine, 100)
    uninterrupted = engine.truth()

    resumed = FakeEngine()
    resumed.restore(saved)  # also holds the saved command again
    assert resumed.time_s == saved.time_s
    _run_steps(resumed, 100)
    _assert_same_truth(resumed.truth(), uninterrupted)


def test_reset_from_snapshot_starts_new_run(engine: FakeEngine) -> None:
    engine.apply_command(_command([0.02] * LEG_COUNT))
    _run_steps(engine, 50)
    settled = engine.snapshot()

    fresh = FakeEngine()
    initial = fresh.reset(settled)
    assert initial.t_s == 0.0
    np.testing.assert_array_equal(initial.s_motor_m, settled.payload["stroke_m"])
    fresh.step()
    np.testing.assert_array_equal(fresh.truth().s_motor_m, settled.payload["stroke_m"])


@pytest.mark.parametrize(
    ("target", "field_name"),
    [
        (FakeEngine(params_sha256=OTHER_PARAMS_SHA256), "params_sha256"),
        (FakeEngine(info=EngineInfo("fake", "1.0", "other")), "engine model"),
        (FakeEngine(info=EngineInfo("mujoco", "1.0", "heave")), "engine name"),
    ],
)
def test_restore_rejects_mismatch_and_keeps_state(
    engine: FakeEngine, target: FakeEngine, field_name: str
) -> None:
    saved = engine.snapshot()
    target.reset(AnalyticStart.ON_CRAWLER)
    target.step()
    before = target.truth()

    with pytest.raises(SnapshotMismatchError) as caught:
        target.restore(saved)
    assert caught.value.field_name == field_name
    _assert_same_truth(target.truth(), before)
    with pytest.raises(SnapshotMismatchError):
        target.reset(saved)


def test_engine_version_difference_does_not_block_restore(engine: FakeEngine) -> None:
    saved = engine.snapshot()
    newer = FakeEngine(info=EngineInfo("fake", "2.0", "heave"))
    newer.restore(saved)
    assert newer.time_s == saved.time_s


def test_snapshot_payload_is_read_only_copy() -> None:
    stroke_m = np.array([0.1, 0.2, 0.3, 0.4])
    saved = Snapshot(FAKE_INFO, PARAMS_SHA256, 1.0, _zero_command(), {"stroke_m": stroke_m})
    stroke_m[0] = 9.0
    assert saved.payload["stroke_m"][0] == 0.1
    with pytest.raises(ValueError):
        saved.payload["stroke_m"][0] = 9.0
    with pytest.raises(TypeError):
        saved.payload["extra"] = np.zeros(1)  # type: ignore[index]


@pytest.mark.parametrize(
    "bad_fields",
    [
        {"payload": {"state": np.array([object()])}},
        {"payload": {"": np.zeros(1)}},
        {"params_sha256": "not-a-digest"},
        {"time_s": float("nan")},
        {"time_s": True},
    ],
)
def test_snapshot_rejects_invalid_fields(bad_fields: dict[str, Any]) -> None:
    fields: dict[str, Any] = {
        "engine": FAKE_INFO,
        "params_sha256": PARAMS_SHA256,
        "time_s": 1.0,
        "held_command": _zero_command(),
        "payload": {"stroke_m": np.zeros(LEG_COUNT)},
    }
    fields.update(bad_fields)
    with pytest.raises(ValueError):
        Snapshot(**fields)


# --- lifecycle ---------------------------------------------------------------------------


def test_state_methods_before_reset_raise_not_ready() -> None:
    fake = FakeEngine()
    with pytest.raises(EngineNotReadyError):
        fake.step()
    with pytest.raises(EngineNotReadyError):
        fake.truth()


def test_methods_after_close_raise_and_identity_stays_readable(engine: FakeEngine) -> None:
    engine.close()
    engine.close()  # idempotent
    for call in (engine.step, engine.measure, engine.truth, engine.snapshot, engine.reset):
        with pytest.raises(EngineClosedError):
            call()
    assert engine.is_closed
    assert engine.params_sha256 == PARAMS_SHA256
    assert engine.dt_s == FAKE_DT_S


def test_contextlib_closing_closes_engine() -> None:
    with contextlib.closing(FakeEngine()) as fake:
        fake.reset()
        fake.step()
    assert fake.is_closed


# --- engine boundary ---------------------------------------------------------------------


def _imported_top_level_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def test_engine_module_does_not_import_pychrono(project_root: Path) -> None:
    engine_path = project_root / "03_src" / "outrigger_sim" / "engine.py"
    assert "pychrono" not in _imported_top_level_modules(engine_path)


def test_importing_engine_loads_no_pychrono(project_root: Path) -> None:
    probe = (
        "import sys; sys.path.insert(0, sys.argv[1]); import outrigger_sim.engine; "
        "print(sorted(m for m in sys.modules if m.split('.')[0] == 'pychrono'))"
    )
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    completed = subprocess.run(
        [sys.executable, "-c", probe, str(project_root / "03_src")],
        capture_output=True,
        text=True,
        check=True,
        env=environment,
        timeout=60,
    )
    assert completed.stdout.strip() == "[]"
