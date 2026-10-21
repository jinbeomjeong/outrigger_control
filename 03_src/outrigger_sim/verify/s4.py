"""S4 checks, branch A: six-mode identification (V7), beta sensitivity, leg damping sensitivity.

``00_docs/03_chrono/chrono_build_plan.md`` S4 (V7 row, beta row, risk #14); ``dynamics_model.md``
5 V7 (rev. 5 initial velocities, rev. 13 ball-centre bushing). Engine independent: inputs are
the identification results of ``verify/metrics`` and the static / stroke numbers the run script
extracts. Automatic pass / fail is a pre-check; the physical judgement is the
dynamics-expert's. (Branch B, V8(b) energy balance, lives elsewhere.)

Excitations (:data:`EXCITATIONS`, plan "초기 속도 가진 6종"): a rigid initial velocity of
the settled machine about / of the mode-shape reference point (CoM of superstructure + rods),
rotations about world x / y / z (roll, pitch, yaw) and translations along x / y / z (surge,
sway, heave). The speed is ``amplitude * 2 pi f`` with ``f`` the reference frequency of the
nominal target mode. ASSUMPTION (plan: no bushing yield): 0.02 deg (roll, pitch), 0.01 deg
(yaw) as in S2a, 0.5 mm (surge, heave), 0.25 mm (sway: its speed is set at the 8.0 Hz mode 6
and would otherwise put the largest amplitude of all runs into mode 1); every run checks that
no step yields (bushing yield deformation mu N / k_t is about 4 mm at the lightest pad).

Judged run per mode (:func:`assign_modes`): every run is projected on all six modes; mode
``i`` is judged in the run with the largest predicted start amplitude ``|(Phi^T M qdot_0)_i| /
omega_i`` among the runs whose window is long enough (modes 1-2 need >= 20 s, plan). The
other runs give the spread of the identification (recorded).

V7 (plan S4 table): natural frequency ``f_d / sqrt(1 - zeta^2)`` of the damped-cosine fit of
``eta_i`` within +-3 % of ``V7_ball_centre_bushing_rev13 / f_damped_Hz`` (``|lambda| / 2 pi``,
the S2a rule ``verify.s2a.v7_frequency_checks``), zeta minus ``r omega dt / 2`` within
+-30 %. Cross-check by the 6-channel ERA (:data:`ERA_FREQ_REL_TOL`, :data:`ERA_ZETA_REL_TOL`,
ASSUMPTION: identification uncertainty) and the projection leakage is recorded.

Beta sensitivity (plan S4 beta row, rev. 5 rule): only the L1 pad ``k_n`` changes. Judged:
penetration (V2 +-5 %), static pitch (V3 +-0.002 deg), FL +1 mm contact-force change (V5,
5 % of the largest component), FL+ F_min / lift-off travel (V6 +-5 %), undamped frequency
(V7 +-3 %, ERA, ``f_Hz_top_ball_centre_rev13``). zeta is not judged.

Leg damping sensitivity (CLAUDE.md, ``damping_survey.md``: leg zeta 0.01 / 0.10 instead of
0.03): every pad dashpot (``c_n`` through ``g_n`` and the bushing ``c_t``) scaled by
``zeta / 0.03``. Judged (dyn ruling, ``dynamics_model.md`` rev. 19, 5.8; independent check
``06_analysis/00_dynamics/s4_check.json``): reference zeta = nominal zeta x scale (+-30 %),
f_n = nominal f_n (+-3 %, natural frequencies on both sides).

Judged value (:func:`judged_value`): the projection fit, replaced by the ERA value when the fit
residual exceeds 0.05 or the ERA cross-check (f 0.5 %, zeta 10 %, ASSUMPTION accepted by dyn)
fails; fit residual and cross-check rows are information (id ``info``).

Beta mode shapes (:func:`beta_mac_checks`): the frequency-ordered Chrono poles must carry the
nominal labels and MAC values (vs the nominal Phi) of ``s4_check.json /
E_beta_mode_shape_MAC`` within +-0.05 (0.69 GPa modes 4 / 5 at 0.800 / 0.802, the 1.6 GPa
5 <-> 6 crossing with pair MAC 0.992 / 0.971).

Recorded only: bushing yield before lift-off in V6, the rod-side chamber +10 % k_v run (model
uncertainty).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.verify.checks import CheckResult, check_abs, check_max, check_rel
from outrigger_sim.verify.reference import RefKey, ReferenceFile, ValueKind
from outrigger_sim.verify.s1 import V2_REL_TOL, V3_ABS_TOL_DEG
from outrigger_sim.verify.s2a import FIT_RESIDUAL_REL_MAX, V7_FREQ_REL_TOL, V7_ZETA_REL_TOL
from outrigger_sim.verify.s3 import V5_REL_TOL, V6_REL_TOL

N_MODES = 6
LONG_WINDOW_S = 20.0
"""Plan: modes 1-2 windows >= 20 s."""
SHORT_WINDOW_S = 2.0
"""Plan: modes 3-6 windows 1-2 s (tau about 0.3-0.4 s); also the fit window of modes 3-6 in
the 20 s runs."""
LONG_WINDOW_MODES = (0, 1)
ERA_FREQ_REL_TOL = 0.005
"""ASSUMPTION: ERA vs projection natural frequency (identification cross-check)."""
ERA_ZETA_REL_TOL = 0.10
"""ASSUMPTION: ERA vs projection zeta (as ``verify.s2a.LOG_DECREMENT_REL_TOL``)."""
NOMINAL_LEG_ZETA = 0.03
"""YAML ``contact.rigid_floor.L1.derivation.damping_ratio`` (the dashpots were set with it)."""
BETA_V5_DELTA_MM = 1.0
ROD_SIDE_KV_RATIO = RefKey(
    ReferenceFile.REFERENCE, ("hydraulic_circuit", "kv_with_rod_side_over_kv"),
    ValueKind.NUMBER_ARRAY,
)
"""Optional item (plan S4): k_v with the locked rod-side chamber / k_v, per leg. Applied as a
linear k_n scale (both load directions; the chamber really only stiffens on unloading,
``dynamics_model.md`` 2.3), so the run is an upper bound and is recorded only."""


@dataclass(frozen=True)
class S4Excitation:
    """One initial-velocity case (rigid velocity about / of the reference point)."""

    name: str
    kind: str
    """``"rotation"`` (angular velocity about the point) or ``"translation"`` (of the point)."""
    axis_world: tuple[float, float, float]
    amplitude: float
    """deg for rotations, m for translations (ASSUMPTION, module docstring)."""
    target_mode: int
    """0-based nominal mode whose frequency sets the speed."""
    window_s: float

    def velocity(self, f_target_Hz: float) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """``(v_point_world [m/s], omega_world [rad/s])``."""
        axis = np.asarray(self.axis_world, dtype=float)
        w = 2.0 * math.pi * f_target_Hz
        if self.kind == "rotation":
            return np.zeros(3), axis * math.radians(self.amplitude) * w
        if self.kind == "translation":
            return axis * self.amplitude * w, np.zeros(3)
        raise ValueError(f"unknown excitation kind {self.kind!r}")

    def qdot0(self, f_target_Hz: float) -> NDArray[np.float64]:
        """Initial ``dq/dt`` in the mode-shape coordinates (surge, sway, heave, roll, pitch,
        yaw; the level body axes are the world axes)."""
        v, w = self.velocity(f_target_Hz)
        return np.concatenate([v, w])


EXCITATIONS: dict[str, S4Excitation] = {
    "roll": S4Excitation("roll", "rotation", (1.0, 0.0, 0.0), 0.02, 0, LONG_WINDOW_S),
    "pitch": S4Excitation("pitch", "rotation", (0.0, 1.0, 0.0), 0.02, 1, LONG_WINDOW_S),
    "yaw": S4Excitation("yaw", "rotation", (0.0, 0.0, 1.0), 0.01, 2, SHORT_WINDOW_S),
    "surge": S4Excitation("surge", "translation", (1.0, 0.0, 0.0), 0.5e-3, 3, SHORT_WINDOW_S),
    "heave": S4Excitation("heave", "translation", (0.0, 0.0, 1.0), 0.5e-3, 4, SHORT_WINDOW_S),
    "sway": S4Excitation("sway", "translation", (0.0, 1.0, 0.0), 0.25e-3, 5, SHORT_WINDOW_S),
}


def predicted_modal_amplitudes(
    phi: ArrayLike, mass_matrix: ArrayLike, f_Hz: Sequence[float]
) -> dict[str, NDArray[np.float64]]:
    """Per excitation: ``|(Phi^T M qdot_0)_i| / omega_i`` (start amplitude of ``eta_i`` if the
    damping were zero), sqrt(kg) m."""
    pm = np.asarray(phi, dtype=float).T @ np.asarray(mass_matrix, dtype=float)
    w = 2.0 * math.pi * np.asarray(f_Hz, dtype=float)
    return {
        name: np.abs(pm @ exc.qdot0(float(f_Hz[exc.target_mode]))) / w
        for name, exc in EXCITATIONS.items()
    }


def assign_modes(
    phi: ArrayLike, mass_matrix: ArrayLike, f_Hz: Sequence[float]
) -> list[str]:
    """Judged run per mode (module docstring): largest predicted amplitude, window rule."""
    amps = predicted_modal_amplitudes(phi, mass_matrix, f_Hz)
    out = []
    for i in range(N_MODES):
        names = [
            n
            for n, exc in EXCITATIONS.items()
            if i not in LONG_WINDOW_MODES or exc.window_s >= LONG_WINDOW_S
        ]
        out.append(max(names, key=lambda n: amps[n][i]))
    return out


def fit_window_s(mode_index: int, run_window_s: float) -> float:
    """Fit window of a mode in a run: the whole run for modes 1-2, at most 2 s for 3-6."""
    if mode_index in LONG_WINDOW_MODES:
        return run_window_s
    return min(run_window_s, SHORT_WINDOW_S)


@dataclass(frozen=True)
class ModeRow:
    """Identification of one mode in its judged run."""

    mode: int
    """1-based."""
    run: str
    f_proj_Hz: float
    """Natural frequency of the projection fit, ``f_d / sqrt(1 - zeta_fit^2)``."""
    zeta_proj: float
    """Projection-fit zeta minus ``zeta_num``."""
    fit_residual_rms_rel: float
    f_era_Hz: float | None
    zeta_era: float | None
    """ERA zeta minus ``zeta_num``."""
    leakage: float | None
    """:func:`outrigger_sim.verify.metrics.projection_leakage` of ``eta_i``."""
    zeta_num: float
    f_ref_Hz: float
    zeta_ref: float


@dataclass(frozen=True)
class JudgedValue:
    """Judged natural frequency / zeta of one mode and where they come from."""

    f_Hz: float
    zeta: float
    source: str
    """``"projection"`` or ``"ERA"``."""
    reason: str


def judged_value(r: ModeRow) -> JudgedValue:
    """dyn ruling (``dynamics_model.md`` rev. 19, 5.8): the projection fit is the judged value;
    the ERA value replaces it when the fit residual exceeds :data:`FIT_RESIDUAL_REL_MAX` or the
    ERA cross-check (f 0.5 %, zeta 10 %, ASSUMPTION accepted by dyn) fails."""
    era_ok = r.f_era_Hz is not None and r.zeta_era is not None
    proj_ok = r.f_proj_Hz is not None and math.isfinite(r.f_proj_Hz)
    if not proj_ok:
        if era_ok:
            return JudgedValue(r.f_era_Hz, r.zeta_era, "ERA", "no projection fit")
        return JudgedValue(math.nan, math.nan, "none", "no identification")
    if not era_ok:
        return JudgedValue(r.f_proj_Hz, r.zeta_proj, "projection", "no ERA mode")
    if r.fit_residual_rms_rel > FIT_RESIDUAL_REL_MAX:
        return JudgedValue(r.f_era_Hz, r.zeta_era, "ERA",
                           f"fit residual {r.fit_residual_rms_rel:.3g} > {FIT_RESIDUAL_REL_MAX}")
    f_dev = abs(r.f_era_Hz / r.f_proj_Hz - 1.0)
    z_dev = abs(r.zeta_era / r.zeta_proj - 1.0) if r.zeta_proj else math.inf
    if f_dev > ERA_FREQ_REL_TOL or z_dev > ERA_ZETA_REL_TOL:
        return JudgedValue(r.f_era_Hz, r.zeta_era, "ERA",
                           f"ERA cross-check failed (f {f_dev:.3g}, zeta {z_dev:.3g})")
    return JudgedValue(r.f_proj_Hz, r.zeta_proj, "projection", "fit and ERA cross-check ok")


def mode_info_checks(rows: Sequence[ModeRow], label: str = "") -> list[CheckResult]:
    """Fit quality and ERA cross-check rows (information: a failure only switches the judged
    value to ERA, :func:`judged_value`)."""
    out: list[CheckResult] = []
    pre = f"{label}: " if label else ""
    for r in rows:
        tag = f"{pre}mode {r.mode} ({r.run})"
        f_proj = math.nan if r.f_proj_Hz is None else r.f_proj_Hz
        z_proj = math.nan if r.zeta_proj is None else r.zeta_proj
        out.append(check_max("info", f"{tag} damped-cosine fit residual (RMS rel.)",
                             math.nan if r.fit_residual_rms_rel is None
                             else r.fit_residual_rms_rel, FIT_RESIDUAL_REL_MAX, "-"))
        out.append(check_rel("info", f"{tag} ERA vs projection natural frequency",
                             math.nan if r.f_era_Hz is None else r.f_era_Hz, f_proj,
                             ERA_FREQ_REL_TOL, "Hz", note="ASSUMPTION tolerance (dyn accepted)"))
        out.append(check_rel("info", f"{tag} ERA vs projection zeta",
                             math.nan if r.zeta_era is None else r.zeta_era, z_proj,
                             ERA_ZETA_REL_TOL, "-", note="ASSUMPTION tolerance (dyn accepted)"))
    return out


def mode_checks(rows: Sequence[ModeRow], *, check_id: str, ref_key_f: str, ref_key_zeta: str,
                label: str = "") -> list[CheckResult]:
    """Natural frequency +-3 % (f_n vs f_n) and zeta +-30 % of the judged values."""
    out: list[CheckResult] = []
    pre = f"{label}: " if label else ""
    for r in rows:
        j = judged_value(r)
        tag = f"{pre}mode {r.mode} ({r.run}, {j.source})"
        out.append(check_rel(check_id, f"{tag} natural frequency", j.f_Hz, r.f_ref_Hz,
                             V7_FREQ_REL_TOL, "Hz", ref_key=ref_key_f,
                             note=f"f_n = |lambda| / 2 pi vs f_n; {j.reason}"))
        out.append(check_rel(check_id, f"{tag} zeta (- r omega dt/2)", j.zeta, r.zeta_ref,
                             V7_ZETA_REL_TOL, "-", ref_key=ref_key_zeta,
                             note=f"zeta_num {r.zeta_num:.3g} subtracted; {j.reason}"))
    return out


def v7_six_mode_checks(rows: Sequence[ModeRow], *, ref_key_f: str, ref_key_zeta: str,
                       label: str = "") -> list[CheckResult]:
    """V7 frequency / zeta of every mode (judged value, :func:`judged_value`)."""
    return mode_checks(rows, check_id="V7", ref_key_f=ref_key_f, ref_key_zeta=ref_key_zeta,
                       label=label)


def damping_mode_checks(rows: Sequence[ModeRow], leg_zeta: float, *,
                        ref_key_f: str) -> list[CheckResult]:
    """Leg damping sensitivity (dyn ruling rev. 19, 5.8): reference zeta = nominal zeta x
    (leg_zeta / 0.03) in ``rows[*].zeta_ref``, reference f_n = nominal; +-30 % / +-3 %."""
    return mode_checks(rows, check_id="damping", ref_key_f=ref_key_f,
                       ref_key_zeta=f"nominal zeta x {damping_scale(leg_zeta):.4g}",
                       label=f"leg zeta {leg_zeta:g}")


BETA_MAC_ABS_TOL = 0.05
"""dyn ruling rev. 19: Chrono MAC vs the expected MAC (``s4_check.json``) within +-0.05."""


def beta_mac_checks(beta: str, *, mac_by_label: Sequence[float | None],
                    label_of_sorted: Sequence[int], expected_index: Sequence[int],
                    expected_mac: Sequence[float], key: str) -> list[CheckResult]:
    """Per frequency-ordered mode: the nominal label of the Chrono pole equals the expected
    best nominal index, and its MAC against the nominal Phi is within +-0.05 of the expected.

    Args:
        mac_by_label: MAC of the ERA pole picked for nominal label i (0-based list).
        label_of_sorted: 1-based nominal label of each frequency-ordered pole.
        expected_index: 0-based best nominal index per frequency-ordered mode (dyn).
        expected_mac: Best MAC per frequency-ordered mode (dyn).
    """
    out: list[CheckResult] = []
    for j, (lab, ei, em) in enumerate(zip(label_of_sorted, expected_index, expected_mac,
                                          strict=True)):
        mac = mac_by_label[lab - 1]
        out.append(check_abs("beta MAC", f"{beta}: mode {j + 1} (frequency order) nominal label",
                             lab - 1, ei, 0.0, "-", ref_key=key + " / best_nominal_index"))
        out.append(check_abs("beta MAC", f"{beta}: mode {j + 1} MAC vs nominal Phi",
                             math.nan if mac is None else mac, em, BETA_MAC_ABS_TOL, "-",
                             ref_key=key + " / best_MAC"))
    return out


# --- beta sensitivity ---------------------------------------------------------------------------


def beta_static_checks(
    beta: str,
    *,
    penetration_mm: Sequence[float],
    pitch_deg: float,
    ref_penetration_mm: Sequence[float],
    ref_pitch_deg: float,
    keys: Mapping[str, str],
) -> list[CheckResult]:
    """V2 penetration +-5 %, V3 static pitch +-0.002 deg (still window means)."""
    return [
        check_rel("beta V2", f"{beta}: pad penetration", penetration_mm, ref_penetration_mm,
                  V2_REL_TOL, "mm", ref_key=keys["penetration"]),
        check_abs("beta V3", f"{beta}: static pitch", pitch_deg, ref_pitch_deg,
                  V3_ABS_TOL_DEG, "deg", ref_key=keys["pitch"]),
    ]


def beta_v5_checks(beta: str, *, dF_N: Sequence[float], ref_dF_per_mm_N: Sequence[float],
                   key: str, delta_mm: float = BETA_V5_DELTA_MM) -> list[CheckResult]:
    """V5 FL +1 mm contact-force change; tol 5 % of the largest reference component."""
    ref = np.asarray(ref_dF_per_mm_N, dtype=float) * delta_mm
    return [check_abs("beta V5", f"{beta}: FL +{delta_mm:g} mm contact force change",
                      dF_N, ref, V5_REL_TOL * float(np.max(np.abs(ref))), "N", ref_key=key,
                      note="tol = 5 % of the largest component")]


def beta_v6_checks(beta: str, *, f_min_mm: float | None, liftoff_mm: float | None,
                   ref_f_min_mm: float, ref_liftoff_mm: float,
                   keys: Mapping[str, str]) -> list[CheckResult]:
    """V6 FL+ travel at the first F_min crossing and at the first lift-off, +-5 %."""
    return [
        check_rel("beta V6", f"{beta}: FL+ travel at F_min",
                  math.nan if f_min_mm is None else f_min_mm, ref_f_min_mm, V6_REL_TOL, "mm",
                  ref_key=keys["f_min"]),
        check_rel("beta V6", f"{beta}: FL+ travel at lift-off",
                  math.nan if liftoff_mm is None else liftoff_mm, ref_liftoff_mm, V6_REL_TOL,
                  "mm", ref_key=keys["liftoff"]),
    ]


def beta_frequency_checks(beta: str, f_era_Hz: Sequence[float | None],
                          f_ref_Hz: Sequence[float], key: str) -> list[CheckResult]:
    """Undamped (natural) frequency of every mode by ERA, +-3 % (zeta not judged)."""
    return [
        check_rel("beta V7", f"{beta}: mode {i + 1} natural frequency (ERA)",
                  math.nan if f is None else f, float(f_ref_Hz[i]), V7_FREQ_REL_TOL, "Hz",
                  ref_key=key, note="ERA |lambda| / 2 pi; Phi not used (stiffness changed)")
        for i, f in enumerate(f_era_Hz)
    ]


# --- leg damping sensitivity ----------------------------------------------------------------------


def damping_scale(leg_zeta: float) -> float:
    """Dashpot scale of a leg zeta case (``c`` is linear in the design zeta)."""
    return leg_zeta / NOMINAL_LEG_ZETA


def first_order_zeta(zeta_nominal: Sequence[float], scale: float) -> NDArray[np.float64]:
    """First-order expectation of the modal zeta with every pad dashpot scaled (information:
    modal zeta is linear in c to first order; not a reference value)."""
    return np.asarray(zeta_nominal, dtype=float) * scale


def zeta_num_share(zeta_num: Sequence[float], zeta_physical: Sequence[float]) -> list[float]:
    """``zeta_num / zeta_physical`` per mode (the CLAUDE.md dt rule wants <= 0.1)."""
    return [float(a / b) if b > 0 else math.inf for a, b in zip(zeta_num, zeta_physical,
                                                               strict=True)]


def summarize_check_ids(checks: Sequence[Mapping[str, Any]]) -> dict[str, bool]:
    """``{id: all passed}`` of JSON check rows."""
    out: dict[str, bool] = {}
    for c in checks:
        out[c["id"]] = out.get(c["id"], True) and bool(c["passed"])
    return out
