"""K-2 TOUCH creep latch Chrono rows: V-6 (L1-R + L2b-NSC, 8) and V-7 (SCM, 4, record only).

Rules ``06_analysis/02_control/k2/k2_touch_creep_rules.md`` (sealed, raw sha256 a3658197...) 3.5 / 3.6 / 9.3 and
the dynamics specification ``k2_dyn_spec.md`` (502b0bb7...) 3. cad-expert definitions, 2026-11-10.

V-6 (``run_S6C.py`` / ``run_S8C.py`` ``--set k2_v6``; each runner runs its engine's 4 rows): top, rigid mast, rigid
floor, K1 order gate off, tag ``final_C4G2_LAS`` (off arm) / ``final_C4G2_LAS_TCL`` (K-2 arm), floors ``fdown3.5``
(0, 3.5) deg and the new ``k2pp025`` (1.375, 2.625) deg (rules 3.2 ``r+p+0.25``); L1-R F_s 0 with the moving-leg pad
damping on (zeta 0.10, ``chrono/moving_pad_damping``), L2b F_s 4 kN front (rear x 0.8333 in the plant), no moving
damping. Scenario / length / sensors of the families (rules 3.5): L1-R ``C1_*`` (bundle C, ideal leg sensors, beta 1.0,
fixed length scenario + 8 s), L2b ``K24_*`` (pilot check, end rule D8 READY + 10 s); the nose-down floor ``fdown3.5``
takes the H4V scenario (``run_S8C._d8_scenario``, the ``C1_H4V_top_fdown3.5`` / ``K24_top_fdown3.5_Fs4`` definition),
``k2pp025`` the D8 scenario.

A batch runs ONE arm: the runner needs ``--k2 off|on``, ``--k1-order-gate off`` and ``--expect-controller <the arm's
tag>`` (L1-R also ``--pad-zeta-moving 0.1``), all explicit; ``--only`` naming a row of the other arm, another value or
a row outside the set is refused before any Chrono step (:func:`select_rows`). Records: ``result.json``
``touch_creep_requested`` / ``touch_creep_effective`` / ``k2`` (row block), ``k2_row.json`` (the flat row of
``k2_recount.DEFAULT_FIELDS["chrono_row"]`` / ``k2_judge.CHRONO_ROW_KEYS``), ``k2_pads.npz`` (``t``, ``N``: 1 ms pad
normal force, t relative to the start state, the time base of the row), ``k2_rate.npz`` (``t``, ``body_omega``: deck
angular velocity in body axes, record rate); ``batch_meta.json`` ``k2``.

V-7 (``s9_batch.py run k2_v7``): FINAL-REP ``P3b_J1_B_top_Fs4`` / ``P3b_J2_B_top_Fs4`` rows x {off, K-2}, K1 off (the
"Chrono K1 off" decision of rules 0 line 6; ASSUMPTION for V-7, the rules name it for V-6), ``--threads`` /
``OMP_WAIT_POLICY`` / hull hook from the rows' start env (I-6).
"""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

RULES = "06_analysis/02_control/k2/k2_touch_creep_rules.md"
RULES_SHA256 = "a3658197bdab02870a0b362144606f404021ebac90662a35efacfa8dbe477263"
DYN_SPEC = "06_analysis/02_control/k2/k2_dyn_spec.md"
DYN_SPEC_SHA256 = "502b0bb78558d40586cbcddb718b6c5d53529de4e78369f454762c9fe73727ff"

V6_SET = "k2_v6"
V7_BATCH = "k2_v7"
K2_FLOOR = "k2pp025"
K2_FLOORS: dict[str, tuple[float, float]] = {K2_FLOOR: (1.375, 2.625)}
"""Rules 3.2 ``r+p+0.25`` = (0.25 x 5.5, 0.75 x 3.5) deg (roll, pitch; pitch > 0 = nose down)."""
V6_FLOORS = ("fdown3.5", K2_FLOOR)
PAD_ZETA_MOVING = 0.10
"""Rules 3.3 / dyn spec 1: axial zeta of an open leg (normal dashpot only)."""
FS_L2B_KN = 4.0
ARMS = ("off", "on")
"""``--k2`` values of the two arms; the row names use ``off`` / ``tcl``."""
ARM_NAME = {"off": "off", "on": "tcl"}
K1_ORDER_GATE = False
"""V-6 runs with the LAS-b K1 order gate off (rules I-10, user decision Q-4)."""
EXPECTED_TAG = {"off": "final_C4G2_LAS", "on": "final_C4G2_LAS_TCL"}
"""Rules 1.2 / I-10 (K1 off)."""
LATCH_EVENT = "INFO_TOUCH_CREEP_LATCH"
CAP_EVENT = "INFO_TOUCH_CREEP_CAP"
LATCH_WINDOW_SAMPLES = 5
CONTROL_PERIOD_S = 0.1
ROW_FILE = "k2_row.json"
PADS_FILE = "k2_pads.npz"
RATE_FILE = "k2_rate.npz"
TIME_TOL_S = 1e-9


@dataclass(frozen=True)
class K2Row:
    """One V-6 row of rules 3.5."""

    number: int
    engine: str  # "L1R" | "L2b"
    floor: str
    fs_kN: float
    arm: str  # "off" | "on"
    moving_damping: bool

    @property
    def name(self) -> str:
        eng = "L1" if self.engine == "L1R" else "L2b"
        return f"K2_{eng}_top_{self.floor}_Fs{self.fs_kN:g}_{ARM_NAME[self.arm]}"

    @property
    def expected_tag(self) -> str:
        return EXPECTED_TAG[self.arm]

    @property
    def pad_zeta_moving(self) -> float | None:
        return PAD_ZETA_MOVING if self.moving_damping else None

    def to_meta(self) -> dict[str, Any]:
        return {"row": self.number, "name": self.name, "engine": self.engine, "floor": self.floor,
                "floor_true_deg": list(floor_deg(self.floor)), "fs_kN": self.fs_kN,
                "fs_rear_note": "rear = front x actuator.L2b_NSC rear_scale 0.8333 in the plant" if self.fs_kN else None,
                "arm": self.arm, "touch_creep_latch": self.arm == "on", "k1_order_gate": K1_ORDER_GATE,
                "moving_damping": self.moving_damping, "pad_zeta_moving": self.pad_zeta_moving,
                "expected_tag": self.expected_tag, "rules": RULES, "rules_sha256": RULES_SHA256}


V6_ROWS: tuple[K2Row, ...] = tuple(
    K2Row(n, eng, floor, fs, arm, eng == "L1R")
    for n, (eng, floor, fs, arm) in enumerate(
        [(e, f, fs, a) for e, fs in (("L1R", 0.0), ("L2b", FS_L2B_KN)) for f in V6_FLOORS for a in ARMS], start=1))
"""Rules 3.5 #1-8, in the table order (L1 fdown off / tcl, L1 k2pp025 off / tcl, L2b ...)."""


def floor_deg(floor: str) -> tuple[float, float]:
    if floor in K2_FLOORS:
        return K2_FLOORS[floor]
    if floor == "fdown3.5":
        return (0.0, 3.5)
    raise KeyError(floor)


def rows(engine: str | None = None, arm: str | None = None) -> list[K2Row]:
    return [r for r in V6_ROWS if (engine is None or r.engine == engine) and (arm is None or r.arm == arm)]


def row_by_name(name: str) -> K2Row:
    for r in V6_ROWS:
        if r.name == name:
            return r
    raise KeyError(name)


def register_floors(floors: dict[str, tuple[float, float]]) -> None:
    """Add :data:`K2_FLOORS` to a runner's floor table (``s6_stage2.FLOORS``); a different value raises."""
    for k, v in K2_FLOORS.items():
        if k in floors and tuple(floors[k]) != v:
            raise RuntimeError(f"floor {k} already defined as {floors[k]}")
        floors[k] = v


def start_states() -> list[dict[str, Any]]:
    """Rules 9.3: start state of every V-6 row (declared in the pre-launch record)."""
    out = []
    for f in V6_FLOORS:
        out.append({"engine": "L1R", "level": "top", "floor": f, "kind": "snapshot",
                    "snapshot": f"S6_crawler_top_{f}", "dir": "07_results/states_L1R",
                    "rows": [r.number for r in rows("L1R") if r.floor == f],
                    "build": "existing (stage 2 / bundle C)" if f == "fdown3.5" else "run_S6C.py snaps-k2"})
    for f in V6_FLOORS:
        out.append({"engine": "L2b", "level": "top", "floor": f, "kind": "in_run_settle", "snapshot": None,
                    "settle": "run_S7C.settle_l2b (CRAWLER_SETTLE_S, rigid NSC crawler), as the K24 family",
                    "rows": [r.number for r in rows("L2b") if r.floor == f]})
    return out


# ------------------------------------------------------------------------------ CLI options
K1_ORDER_GATE_OPTION = "--k1-order-gate"
K1_ORDER_GATE_CHOICES = ("preset", "off", "on")
PAD_ZETA_OPTION = "--pad-zeta-moving"


def add_arguments(ap: Any, *, pad_zeta: bool) -> None:
    """``--k2`` (``touch_creep_option``), ``--k1-order-gate`` (the ``run_S9.K1_ORDER_GATE_OPTION`` form: preset / off /
    on, absent = no attribute) and (L1-R) ``--pad-zeta-moving <value|off>`` (default off)."""
    import argparse

    from outrigger_sim.control.touch_creep_option import add_touch_creep_argument

    add_touch_creep_argument(ap)
    ap.add_argument(K1_ORDER_GATE_OPTION, dest="k1_order_gate", choices=K1_ORDER_GATE_CHOICES,
                    default=argparse.SUPPRESS,
                    help="--set k2_v6: the LAS-b K1 order gate (slope_clearance_margin.flat_soil_margin_order_gate), "
                         "must be given explicitly (off for V-6, rules I-10); refused with other sets. Absent = no "
                         "attribute")
    if pad_zeta:
        ap.add_argument(PAD_ZETA_OPTION, dest="pad_zeta_moving", default="off",
                        help="--set k2_v6 L1-R rows: axial zeta of a moving leg (valve |u| > lock_eps) on the pad "
                             "SMC dashpot g_n (cn only, chrono/moving_pad_damping), e.g. 0.1; 'off' (default) = "
                             "the pad material is not touched (bit-identical)")


def pad_zeta_of_args(args: Any) -> float | None:
    v = getattr(args, "pad_zeta_moving", "off")
    if v is None or str(v).lower() == "off":
        return None
    try:
        z = float(v)
    except ValueError as error:
        raise SystemExit(f"{PAD_ZETA_OPTION} must be a number or off, got {v!r}") from error
    if not (z > 0.0 and math.isfinite(z)):
        raise SystemExit(f"{PAD_ZETA_OPTION} must be > 0, got {v!r}")
    return z


def explicit_options(args: Any) -> dict[str, Any]:
    """The K-2 options given explicitly (non-default) on the command line."""
    from outrigger_sim.control.touch_creep_option import TOUCH_CREEP_PRESET, touch_creep_request

    out: dict[str, Any] = {}
    k2 = touch_creep_request(args)
    if k2 != TOUCH_CREEP_PRESET:
        out["k2"] = k2
    k1 = getattr(args, "k1_order_gate", None)
    if k1 not in (None, "preset"):
        out["k1_order_gate"] = k1
    z = pad_zeta_of_args(args)
    if z is not None:
        out["pad_zeta_moving"] = z
    if getattr(args, "expect_controller", None) is not None:
        out["expect_controller"] = args.expect_controller
    return out


def select_rows(args: Any, engine: str, set_ids: Sequence[str]) -> tuple[list[str], dict[str, Any]]:
    """Rows of ``--set k2_v6`` for one batch of ``engine`` and the ``batch_meta.json`` ``k2`` record.

    One arm per batch (the ``--k2`` value), every option explicit and equal to the rows' definition.

    Raises:
        SystemExit: ``--k2`` not off / on, ``--k1-order-gate`` not off, ``--expect-controller`` not the arm's tag, the
            L1-R ``--pad-zeta-moving`` not 0.1 (or given on L2b), or ``--only`` rows outside the set / of the other arm.
    """
    from outrigger_sim.control.touch_creep_option import touch_creep_request

    k2 = touch_creep_request(args)
    if k2 not in ARMS:
        raise SystemExit(f"--set {V6_SET} needs --k2 off or --k2 on (explicit; got {k2!r}); one arm per batch")
    k1 = getattr(args, "k1_order_gate", None)
    if k1 != "off":
        raise SystemExit(f"--set {V6_SET} needs {K1_ORDER_GATE_OPTION} off (explicit; rules I-10), got {k1!r}")
    want_tag = EXPECTED_TAG[k2]
    if getattr(args, "expect_controller", None) != want_tag:
        raise SystemExit(f"--set {V6_SET} --k2 {k2} needs --expect-controller {want_tag} (rules I-10), got "
                         f"{getattr(args, 'expect_controller', None)!r}")
    z = pad_zeta_of_args(args) if engine == "L1R" else None
    if engine == "L1R" and z != PAD_ZETA_MOVING:
        raise SystemExit(f"--set {V6_SET} L1-R rows need {PAD_ZETA_OPTION} {PAD_ZETA_MOVING:g} (rules 3.5: moving "
                         f"damping on in all 4 L1 rows), got {getattr(args, 'pad_zeta_moving', 'off')!r}")
    arm_ids = [r.name for r in rows(engine, k2)]
    if sorted(set(arm_ids) - set(set_ids)):
        raise RuntimeError(f"{V6_SET}: rows {arm_ids} not in the runner set {list(set_ids)}")
    only = list(getattr(args, "only", None) or [])
    if only:
        outside = sorted(set(only) - set(set_ids))
        if outside:
            raise SystemExit(f"--set {V6_SET} --only: not rows of this set / engine: {outside}")
        other = sorted(set(only) - set(arm_ids))
        if other:
            raise SystemExit(f"--set {V6_SET} --k2 {k2} --only: rows of the other arm {other} (arms are not mixed "
                             "in one batch)")
        ids = [n for n in arm_ids if n in only]
    else:
        ids = arm_ids
    record = {"set": V6_SET, "engine": engine, "k2": k2, "touch_creep_latch": k2 == "on",
              "k1_order_gate": K1_ORDER_GATE, "k1_order_gate_request": k1, "expect_controller": want_tag,
              "pad_zeta_moving": z, "rows": {n: row_by_name(n).to_meta() for n in ids},
              "start_states": [s for s in start_states() if s["engine"] == engine],
              "rules": RULES, "rules_sha256": RULES_SHA256, "dyn_spec": DYN_SPEC, "dyn_spec_sha256": DYN_SPEC_SHA256}
    return ids, record


def refuse_outside(args: Any, case_set: str) -> None:
    """Explicit K-2 options with a set other than ``k2_v6``: refused (the other sets run their own definition)."""
    given = {k: v for k, v in explicit_options(args).items() if k != "expect_controller"}
    if case_set != V6_SET and given:
        raise SystemExit(f"{sorted(given)} only with --set {V6_SET} (got --set {case_set})")


def apply_to_config(config: Any, *, k2_arm: str | None, k1_order_gate: bool | None) -> Any:
    """The row's K1 gate and K-2 arm on a built C2 config (unchanged for None)."""
    from dataclasses import replace

    from outrigger_sim.control.touch_creep_option import with_touch_creep

    if k1_order_gate is not None:
        config = replace(config, slope_clearance_margin=replace(
            config.slope_clearance_margin, flat_soil_margin_order_gate=bool(k1_order_gate)))
    if k2_arm is not None:
        config = with_touch_creep(config, k2_arm)
    return config


def preflight_record(name: str, config: Any, tag: str) -> dict[str, Any]:
    """Config-only check of one row: tag = expected, K1 gate off, ``touch_creep_latch.enable`` = the arm, LAS-b on.

    Raises:
        SystemExit: Any mismatch (nothing has run).
    """
    from outrigger_sim.control.touch_creep_option import is_touch_creep_enabled

    r = row_by_name(name)
    gate = bool(config.slope_clearance_margin.flat_soil_margin_order_gate)
    tcl = is_touch_creep_enabled(config)
    las = bool(getattr(getattr(config, "liftoff_approach_slow", None), "enable", False))
    problems = []
    if tag != r.expected_tag:
        problems.append(f"controller tag {tag} != {r.expected_tag}")
    if gate is not K1_ORDER_GATE:
        problems.append(f"K1 order gate {gate}")
    if tcl is not (r.arm == "on"):
        problems.append(f"touch_creep_latch.enable {tcl} for arm {r.arm}")
    if not las:
        problems.append("LAS-b off")
    if problems:
        raise SystemExit(f"{name}: K-2 preflight refused: " + "; ".join(problems))
    return {"controller_tag": tag, "expected_tag": r.expected_tag, "k1_order_gate": gate,
            "touch_creep_latch": tcl, "las_b_enabled": las}


# ------------------------------------------------------------------------------ row record
def _rel_events(case: Mapping[str, Any], t0: float) -> list[list]:
    from outrigger_sim.verify import s6_control as s6

    return [[float(t) - t0, str(n)] for t, n in s6._events(case)]


def _first_off_edge(t, on) -> float | None:
    import numpy as np

    on = np.asarray(on, bool)
    idx = np.flatnonzero(on[:-1] & ~on[1:])
    return float(t[idx[0] + 1]) if idx.size else None


def _masked_min(t, f, mask) -> dict[str, Any]:
    import numpy as np

    if not mask.any():
        return {"value": None, "leg": None, "t_s": None}
    m = np.where(mask[:, None], f, np.inf)
    i, leg = np.unravel_index(int(np.argmin(m)), m.shape)
    return {"value": float(f[i, leg]), "leg": int(leg), "t_s": float(t[i])}


def latch_window_normals(t, n, events_rel: Sequence[Sequence]) -> dict[str, Any]:
    """Per latched leg: the true pad normal force [N] at the latch time and at the 5 window sample times
    ``t_latch - k T_s`` (k = 0..4), each read at the last 1 ms sample at or before that time (rules 3.5 air false
    latch; the ``k2_recount.false_latch`` rule)."""
    import numpy as np

    from outrigger_sim.params import LEG_ORDER

    t = np.asarray(t, float)
    n = np.asarray(n, float)
    out: dict[str, Any] = {}
    for te, name in events_rel:
        if not str(name).startswith(LATCH_EVENT + ":"):
            continue
        leg = str(name).split(":", 1)[1]
        if leg not in LEG_ORDER or leg in out:
            continue
        j = LEG_ORDER.index(leg)
        samples = []
        for k in range(LATCH_WINDOW_SAMPLES):
            ts = float(te) - k * CONTROL_PERIOD_S
            i = int(np.searchsorted(t, ts + TIME_TOL_S)) - 1
            samples.append({"t_s": ts, "sample_t_s": None if i < 0 else float(t[i]),
                            "N": None if i < 0 else float(n[i, j])})
        out[leg] = {"latch_t_s": float(te), "window": samples,
                    "false_latch": any(s["N"] is None or s["N"] <= 0.0 for s in samples)}
    return out


def k2_row(case_dir: Path, *, row: K2Row, params: Any) -> dict[str, Any]:
    """The flat V-6 row of ``case_dir`` (``k2_recount.DEFAULT_FIELDS["chrono_row"]``) from its saved files; also
    writes :data:`PADS_FILE` / :data:`RATE_FILE` / :data:`ROW_FILE`. Times relative to the start state
    (``settings.start_t_s``); events ``[t, name]`` in the same base.

    Definitions (D8x 4.1, the harness ``d8x_record.run_metrics`` names): ``t_touch_s`` = first instant after TOUCH
    (``s6_control._times``, the sample where the four legs are latched); ``t_crawler_off_s`` = first crawler
    on -> off edge of the record (``F_crawler`` z > 0); ``t_lift_s`` = earlier of that and the LOC event; J1 = minimum
    ``F_cyl_min_interval`` (every physics step) from ``t_lift``; J1 window = run end - ``t_lift``; J2 in the H4
    intervals (``reanchor_started`` to its end event); J4 = max |true deck attitude - target| from the first READY;
    J6 = ``F_cyl / A_p`` over the record samples with ``|u_applied| > 1e-6`` (moving) / the others (locked), the
    ``s6_control`` definition; J10 = ``s6_control.d8x_metrics`` crawler re-contacts after LOC.
    """
    import numpy as np

    from outrigger_sim.verify import s6_control as s6

    sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "d8x"))
    try:
        import d8x_record  # noqa: PLC0415
    finally:
        sys.path.remove(str(ROOT / "04_scripts" / "03_control" / "d8x"))
    case_dir = Path(case_dir)
    c = s6.load_case(case_dir)
    res = c["result"]
    s = res["settings"]
    t0 = float(s["start_t_s"])
    tm = s6._times(c)
    rec = c["rec"]
    tr = np.asarray(rec["t"], float) - t0
    pads = c["pads"]
    tp = np.asarray(pads["t"], float) - t0
    npad = np.asarray(pads["N"], float).reshape(-1, 4)
    fmin = np.asarray(pads["F_cyl_min_interval"], float).reshape(-1, 4)
    events = _rel_events(c, t0)
    t_end = float(max(tp[-1], tr[-1]))
    on = np.asarray(rec["F_crawler"], float)[:, 2] > 0.0
    t_off = _first_off_edge(tr, on)
    t_loc = next((t for t, n in events if n == d8x_record.LOC_EVENT), None)
    t_lift = d8x_record._earliest(t_off, t_loc)
    after_lift = tp >= t_lift - TIME_TOL_S if t_lift is not None else np.zeros_like(tp, bool)
    j1 = _masked_min(tp, fmin, after_lift)
    intervals = d8x_record.reanchor_intervals(events, t_end)
    in_h4 = np.zeros_like(tp, bool)
    for a, b in intervals:
        in_h4 |= (tp >= a - TIME_TOL_S) & (tp <= b + TIME_TOL_S)
    j2 = _masked_min(tp, fmin, in_h4)
    rp = np.degrees(np.array([s6.roll_pitch_from_quat(q) for q in rec["body_quat_wxyz"]]))
    err = rp - np.asarray(s["target_deg"], float)
    t_ready = tm["ready"]
    after_ready = tr >= t_ready - TIME_TOL_S if t_ready is not None else np.zeros_like(tr, bool)
    area = s6._head_areas_m2(params)
    moving = np.abs(np.asarray(rec["u_applied"], float)) > s6.MOVING_EPS_M_S
    p_bar = np.asarray(rec["F_cyl"], float) / area / 1e5
    dm = s6.d8x_metrics(c, tr, err, tm)
    after_touch = tp >= tm["touch"] - TIME_TOL_S if tm["touch"] is not None else np.zeros_like(tp, bool)
    # deck angular velocity in body axes (R^T w_world) at the record rate
    q = np.asarray(rec["body_quat_wxyz"], float)
    w = np.asarray(rec["body_omega"], float)
    w_body = np.array([_rot_t(qq, ww) for qq, ww in zip(q, w, strict=True)])
    np.savez_compressed(case_dir / PADS_FILE, t=tp, N=npad)
    np.savez_compressed(case_dir / RATE_FILE, t=tr, body_omega=w_body)
    latches = latch_window_normals(tp, npad, events)
    phases = [(float(a), p) for a, p in res["phases"]]
    t_touch_start = next((a for a, p in phases if p == "touch"), None)
    ctl = res.get("controller_meta") or {}
    k2_meta = ctl.get("touch_creep_latch")
    window = None
    damp_file = case_dir / "pad_damping.npz"
    if damp_file.exists() and tm["touch"] is not None and t_lift is not None:
        from outrigger_sim.chrono.moving_pad_damping import load_switches, open_fraction

        window = open_fraction(load_switches(damp_file), tm["touch"] + t0, t_lift + t0)
    out = {
        "case_id": res["case"], "engine": "L1" if row.engine == "L1R" else "L2b",
        "controller_tag": (res.get("k2") or {}).get("controller_tag"),
        "k1_order_gate": bool((ctl.get("slope_clearance_margin") or {}).get("settings", {}).get(
            "flat_soil_margin_order_gate")),
        "touch_creep_latch": bool(res.get("touch_creep_effective")),
        "touch_creep_requested": res.get("touch_creep_requested"),
        "floor_true_deg": [float(v) for v in (res.get("acceptance") or {}).get("floor_true_deg")],
        "fs_kN": row.fs_kN, "moving_damping": row.moving_damping, "pad_zeta_moving": row.pad_zeta_moving,
        "t_touch_start_s": t_touch_start, "t_touch_s": tm["touch"], "t_crawler_off_s": t_off, "t_loc_s": t_loc,
        "t_lift_s": t_lift, "t_liftoff_final_s": tm["liftoff"], "t_ready_s": t_ready, "t_end_s": t_end,
        "J1_min_cyl_after_lift_N": j1["value"], "J1_leg": j1["leg"], "J1_t_s": j1["t_s"],
        "J1_window_s": None if t_lift is None else t_end - t_lift,
        "reanchor_intervals_s": intervals, "J2_min_cyl_reanchor_N": j2["value"],
        "J3_pad_lift_samples": int(((npad <= 0.0).any(axis=1) & after_touch).sum()),
        "J3_pad_normal_min_N": float(npad[after_touch].min()) if after_touch.any() else None,
        "J4_att_max_after_ready_deg": float(np.abs(err[after_ready]).max()) if after_ready.any() else None,
        "J6_max_moving_bar": float(p_bar[moving].max()) if moving.any() else None,
        "J6_max_locked_bar": float(p_bar[~moving].max()) if (~moving).any() else None,
        "crawler_recontact_after_loc": dm.get("crawler_recontact_after_loc_count"),
        "crawler_recontact_anchor": dm.get("crawler_recontact_anchor"),
        "latch_window_true_N": latches,
        "false_latch_legs": sorted(k for k, v in latches.items() if v["false_latch"]),
        "cap_events": sum(1 for _, n in events if str(n).startswith(CAP_EVENT)),
        "touch_creep_meta": k2_meta,
        "valve_open_fraction_touch_to_lift": None if window is None else dict(zip(
            ("FL", "FR", "RL", "RR"), window, strict=True)),
        "valve_open_window_s": None if window is None else [tm["touch"], t_lift],
        "events": events,
        "files": {"pads": PADS_FILE, "rate": RATE_FILE},
        "time_base": "relative to settings.start_t_s (pads.npz / record / controller events minus t0)",
        "definitions": "k2_chrono_rows.k2_row docstring (D8x 4.1 names)",
        "row": row.to_meta(),
    }
    (case_dir / ROW_FILE).write_text(json.dumps(_plain(out), indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def _rot_t(q, w):
    """``R(q)^T w`` (q = w, x, y, z)."""
    import numpy as np

    a, b, c, d = (float(v) for v in q)
    r = np.array([[a * a + b * b - c * c - d * d, 2 * (b * c - a * d), 2 * (b * d + a * c)],
                  [2 * (b * c + a * d), a * a - b * b + c * c - d * d, 2 * (c * d - a * b)],
                  [2 * (b * d - a * c), 2 * (c * d + a * b), a * a - b * b - c * c + d * d]])
    return r.T @ np.asarray(w, float)


def _plain(value):
    import numpy as np

    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return _plain(value.tolist())
    if isinstance(value, np.generic):
        return _plain(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def finish_case(case_dir: Path, summary: dict[str, Any], *, row: K2Row, params: Any) -> dict[str, Any]:
    """After ``result.json`` is written: the row record, ``result.json`` ``k2`` block (re-written)."""
    rec = k2_row(case_dir, row=row, params=params)
    summary["k2_row"] = {k: rec[k] for k in ("t_touch_s", "t_lift_s", "t_ready_s", "J1_min_cyl_after_lift_N",
                                             "J3_pad_lift_samples", "J3_pad_normal_min_N", "cap_events",
                                             "false_latch_legs", "valve_open_fraction_touch_to_lift")}
    summary["k2_row"]["file"] = ROW_FILE
    (Path(case_dir) / "result.json").write_text(json.dumps(_plain(summary), indent=1, ensure_ascii=False),
                                                encoding="utf-8")
    return rec


# ------------------------------------------------------------------------------ V-7 (s9_batch)
V7_SOURCE_CASES = ("P3b_J1_B_top_Fs4", "P3b_J2_B_top_Fs4")
V7_TAG = {"off": "final_C4G2_LAS", "on": "final_C4G2_LAS_TCL"}
V7_START_ENV = {"OMP_WAIT_POLICY": "PASSIVE", "OUTRIGGER_HULL_HOOK": "fast"}


def _with_controller(argv: list[str], tag: str) -> list[str]:
    out = list(argv)
    i = out.index("--expect-controller")
    out[i + 1] = tag
    return out


def v7_rows(sb: ModuleType) -> list[dict[str, Any]]:
    """4 rows: the FINAL-REP rows of :data:`V7_SOURCE_CASES` with ``--expect-controller`` = the arm tag and
    ``--k1-order-gate off --k2 off|on`` appended (argv otherwise unchanged)."""
    src = {r["case"]: r for r in sb.level_rows("final_rep_cases")}
    out = []
    for case in V7_SOURCE_CASES:
        base = src[case]
        for arm in ARMS:
            name = f"K2V7_{case}_{ARM_NAME[arm]}"
            argv = _with_controller(base["argv"], V7_TAG[arm]) + [K1_ORDER_GATE_OPTION, "off", "--k2", arm]
            out.append({"case": name, "est_s": base["est_s"], "argv": argv, "controller": V7_TAG[arm],
                        "group": V7_BATCH, "planned_pool": "pcore", "start_env": dict(V7_START_ENV),
                        "k2_arm": arm, "touch_creep_latch": arm == "on", "k1_order_gate": "off",
                        "source_case": case, "pair_case": f"K2V7_{case}_{ARM_NAME['on' if arm == 'off' else 'off']}",
                        "note": f"{V7_BATCH} (rules 3.6, record only): FINAL-REP {case}, K-2 {arm}, K1 off, "
                                f"{V7_TAG[arm]}"})
    return out


def k2_batches(sb: ModuleType) -> dict[str, list[dict[str, Any]]]:
    r = v7_rows(sb)
    if len({x["case"] for x in r}) != len(r):
        raise RuntimeError(f"{V7_BATCH}: duplicate rows")
    return {V7_BATCH: r}


def v7_argv_check(row: dict[str, Any]) -> dict[str, Any]:
    """Build check without Chrono: the level argv parses, ``--threads`` = the fixed count, the run-time config
    (K1 gate, K-2) passes ``--expect-controller``."""
    sys.path.insert(0, str(HERE))
    try:
        import las_k1_chrono_rows as lk  # noqa: PLC0415
        import run_S9 as r9  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    level = row["argv"][row["argv"].index("level"):]
    a = r9.build_parser().parse_args(level)
    config = lk.run_level_config(r9, a)
    chk = r9.controller_expectation(config, row["controller"])
    diffs = [] if chk["ok"] else [c for c in chk["checks"] if not c["ok"]]
    if getattr(a, "threads", None) != r9.SCM_THREADS_FIXED:
        diffs.append({"key": "threads", "row": getattr(a, "threads", None), "want": r9.SCM_THREADS_FIXED})
    return {"case": row["case"], "status": "differs" if diffs else "ok", "diffs": diffs,
            "touch_creep_latch": bool(config.touch_creep_latch.enable),
            "k1_order_gate": bool(config.slope_clearance_margin.flat_soil_margin_order_gate)}
