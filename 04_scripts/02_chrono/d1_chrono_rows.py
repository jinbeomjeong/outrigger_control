"""D-1 controller verification matrix: the Chrono rows (definitions only; cad 2026-11-08).

Source: ``d1_rows_final.md`` 4 (dynamics-expert, user decisions U1-U8 of 2026-11-08, ``00_docs/decision_log.md`` 4).
The rows are ``s9_batch`` rows (``s9_batch list D1-CHRONO`` / ``check-sources`` / ``run``); this module only builds
them and is called by ``s9_batch.batches`` with the ``s9_batch`` module itself, so the VB arguments always come from
the live ``s9_batch.v5_rigid_argv("VB")`` / ``s9_batch.v5_vb_argv()`` (never copied here).

Batches:

* ``D1-CHRONO`` (candidates of the 16 required rows, ``d1_id`` per row):

  - C2-01 ... 08: ``run_S8C`` set ``d1c2`` (L2b-NSC, rigid floor, rigid NSC crawler), auger middle / bottom x
    fdown-op (0, 3.2), fup-op (0, -3.2), roll+op (4.4, 0) / roll-op (-4.4, 0) (sign chosen by the D-1 selection:
    both defined, ``d1_select`` ``roll_sign``), diag-op = rpBop (2.3351, 1.5017); F_s 4 kN; VB = ``V5_VB_ARGS`` without
    ``valve_tau_s`` (the S8 case has tau_v 0.1 s); tag "rigid crawler upper bound for 8 s after lift-off".
  - C1-09 ... 12: ``run_S6C`` set ``d1c1`` (L1-R V0, VB not available on L1), top / bottom x flat / diag-op, crawler
    x3 (U6) from the x3 settled start snapshots (``run_S6C.py snaps-crx`` first).
  - S-01 / S-02: ``run_S9 level`` J1 pad B, auger middle / bottom, slope candidates diag-rec (1.925, 1.4) / roll-rec
    (-2.64, 0) and fup-rec (0, -2.8) (``ASSUMED_BOUNDARY``, optional), S9SL form (record_only start limit, 160 s
    closed loop), VB = ``v5_vb_argv()`` (valve 0.1 s on the soil rows), ``--expect-controller``.
  - S-03 / S-04: ``run_S9 level`` G1 base + J1 patch under FL (G6P triple layout), auger middle / bottom, flat, 200 s
    closed loop (the J1FL G6 length), VB.

* ``D1-PSC`` (optional, after the C-3 probe passed; selection by control-expert / main session): PS-c on Chrono = the A1
  ``--soil-event`` mechanism (``run_S9.SoilEventDriver``: the patch terrain's reference frame lowered by
  ``-d P345``), J1 pad B top flat, base rows (FL / RL patch of the same soil) + c-slow / c-mid / c-edge / c-fast @FL and
  c-mid @RL; event rows ``depends_on`` their base (``mid@<base>`` reads t_LOC / t_DONE of the base folder). Closed loop
  200 s (c-slow at READY + 5 s with a 20 s ramp).

Estimates (``est_s``, P pool, ASSUMPTION): C2 = the s9_batch v5 rigid rule (V0 estimate + 180 s) x 1.08 on the run_S8C
P-pool estimate of the case; C1 = ``BundleCCase.wall_estimate_s`` (stage-2 7-worker fit); soil rows =
``run_S9.final_est_pool_s`` x ``s9_batch.V5_SOIL_VB_FACTOR`` (1.2).
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent

D1_BATCH = "D1-CHRONO"
D1_PSC_BATCH = "D1-PSC"
D1_SOURCE = "dyn_d1/d1_rows_final.md 4 (2026-11-08, U1-U8)"
D1_C2_TAG = "rigid crawler upper bound for 8 s after lift-off (S8-L1 / S8-L5)"
D1_C2_ROWS: tuple[tuple[str, str, str, str | None], ...] = (
    ("C2-01", "middle", "fdown3.2", None), ("C2-02", "middle", "fup3.2", None),
    ("C2-03", "middle", "roll4.4", "roll_sign"), ("C2-03", "middle", "rollm4.4", "roll_sign"),
    ("C2-04", "middle", "rpBop", None),
    ("C2-05", "bottom", "fdown3.2", None), ("C2-06", "bottom", "fup3.2", None),
    ("C2-07", "bottom", "roll4.4", "roll_sign"), ("C2-07", "bottom", "rollm4.4", "roll_sign"),
    ("C2-08", "bottom", "rpBop", None),
)
"""(D-1 id, auger level, run_S8C floor, selection group). Two candidates share the roll id (one is kept)."""
D1_S_SLOPES: tuple[tuple[str, tuple[float, float], bool], ...] = (
    ("diag-rec", (1.925, 1.4), False),
    ("roll-rec", (-2.64, 0.0), False),
    ("fup-rec", (0.0, -2.8), True),
)
"""S-01 / S-02 slope candidates (d1_rows_final.md 1: name, floor (roll, pitch) [deg], optional). fup-rec is the U3
assumed boundary (``ASSUMED_BOUNDARY``), its inclusion is open (d1_rows_final.md 8 item 2)."""
D1_S_LEVELS = (("S-01", "middle"), ("S-02", "bottom"))
D1_S_PATCH_LEVELS = (("S-03", "middle"), ("S-04", "bottom"))
D1_S_PATCH_DURATION_S = 200.0
"""G6 J1@FL closed-loop length (run_S9.G6_DURATION_S["J1FL"])."""
D1_PSC_PROFILES: tuple[tuple[str, str, float, float, str], ...] = (
    ("c-slow", "FL", 11.5, 20.0, "ready+5"),
    ("c-mid", "FL", 20.0, 6.0, "mid"),
    ("c-edge", "FL", 15.0, 8.0, "mid"),
    ("c-fast", "FL", 30.0, 4.0, "mid"),
    ("c-mid", "RL", 20.0, 6.0, "mid"),
)
"""PS-c profiles (d1_rows_final.md 3: name, pad, d [mm], T [s], timing); ``mid`` = mid(LOC, first DONE) of the base."""
D1_PSC_DURATION_S = 200.0
D1_PSC_PROBE = "06_analysis/01_chrono/19_S9/psc_frame_probe"
"""C-3 probe results (s9_psc_frame_probe.py, 2026-11-08)."""


def _r9() -> ModuleType:
    sys.path.insert(0, str(HERE))
    try:
        import run_S9 as r9  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    return r9


def _tag(v: float) -> str:
    return f"{v:g}".replace("-", "m").replace(".", "p")


def c2_rows(sb: ModuleType) -> list[dict[str, Any]]:
    """C2-01 ... 08 candidates (10): ``sb.v5_rigid_row`` (VB arguments of ``sb.v5_rigid_argv("VB")``)."""
    sys.path.insert(0, str(HERE))
    try:
        import run_S8C as s8  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    cases = {c.case_id: c for c in s8.case_set("d1c2")}
    rows = []
    for rid, level, floor, select in D1_C2_ROWS:
        cid = f"D1C2_{level}_{floor}_Fs4"
        v0 = float(cases[cid].wall_estimate_s("p"))
        r = sb.v5_rigid_row(cid, "d1c2", "VB", criteria_id=rid, group=D1_BATCH, v0_wall_s=v0, source_run=None,
                            pair_case=None,
                            note=f"{D1_BATCH} {rid}: run_S8C {cid} L2b VB, judged (D8 / P + v5 record); tag "
                                 f"'{D1_C2_TAG}'; IMU R_c and READY-window sum F_c / load centre recorded")
        r.update(d1_id=rid, d1_role="judge", d1_tag=D1_C2_TAG, engine="L2b_NSC", d1_source=D1_SOURCE)
        if select:
            r["d1_select"] = select
        rows.append(r)
    return rows


def c1_rows(sb: ModuleType) -> list[dict[str, Any]]:
    """C1-09 ... 12 (4): ``run_S6C run --set d1c1 --only <id> --approved --jobs 1`` (L1-R V0, crawler x3)."""
    sys.path.insert(0, str(HERE))
    try:
        import run_S6C as s6  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    cases = {c.case_id: c for c in s6.d1c1_cases()}
    rows = []
    for rid, cid in s6.D1C1_IDS.items():
        c = cases[cid]
        rows.append({"case": cid, "est_s": round(c.wall_estimate_s()), "s6c": True, "fixed_pcore": True,
                     "argv": sb.S6C + ["run", "--set", "d1c1", "--only", cid, "--approved", "--jobs", "1",
                                       "--tag", f"d1_{cid}"],
                     "family": "d1c1", "engine": "L1R", "group": D1_BATCH, "criteria_id": rid, "d1_id": rid,
                     "d1_role": "record", "v5_setting": None, "d1_source": D1_SOURCE,
                     "requires": f"start snapshot {c.snapshot} (run_S6C.py snaps-crx)",
                     "note": f"{D1_BATCH} {rid}: run_S6C {cid} L1-R V0, crawler x{s6.D1C1_FACTOR:g} (U6), record; "
                             "VB transfer by the 2x2 rule (d1_rows_final.md 5)"})
    return rows


def _soil_vb(sb: ModuleType, r9: ModuleType, c: dict[str, Any], rid: str, *, role: str, note: str,
             p3b_form: bool = False) -> dict[str, Any]:
    """A ``run_S9 level`` row of ``c`` on the run-time preset (``--expect-controller``) + ``sb.v5_vb_argv()``.
    ``p3b_form``: estimate on the P3b form (a same-soil triple layout costs as the plain J1 run, not the G1-base G6
    form)."""
    r = dict(c)
    r["controller"] = r9.FINAL_CONTROLLER
    est = r9.final_est_pool_s({k: v for k, v in r.items() if k != "soil_patch"} if p3b_form else r)
    pools = {k: round(v * sb.V5_SOIL_VB_FACTOR, -2) for k, v in est.items()}
    return {"case": r["case"], "est_s": pools["pcore"], "est_pool_s": pools,
            "argv": sb.RUN + r9.p3b_level_argv(r) + sb.v5_vb_argv(), "controller": r9.FINAL_CONTROLLER,
            "group": D1_BATCH, "criteria_id": rid, "d1_id": rid, "d1_role": role, "v5_setting": "VB",
            "d1_source": D1_SOURCE, "planned_pool": "pcore", "note": note}


def soil_rows(sb: ModuleType) -> list[dict[str, Any]]:
    """S-01 / S-02 candidates (J1 B middle / bottom x :data:`D1_S_SLOPES`) and S-03 / S-04 (G1 + J1@FL)."""
    r9 = _r9()
    rows = []
    for rid, level in D1_S_LEVELS:
        for name, (roll, pitch), optional in D1_S_SLOPES:
            c = r9.p3b_case("D1-S", "J1", "B", level, 4.0)
            sim_s = r9.CRAWLER_SETTLE_S + r9.S9SL_DURATION_S
            c.update(case=f"D1S_J1_B_{level}_Fs4_r{_tag(roll)}_p{_tag(pitch)}", floor_deg=(roll, pitch),
                     start_limit=r9.S9SL_START_LIMIT, duration_s=r9.S9SL_DURATION_S, sim_s=sim_s)
            r = _soil_vb(sb, r9, c, rid, role="judge",
                         note=f"{D1_BATCH} {rid} candidate {name} ({roll:g}, {pitch:g}) deg: J1 B {level} SCM VB, "
                              "P3 judged, READY 120 s, stroke_limited_stop allowed"
                              + ("; ASSUMED_BOUNDARY (U3)" if name == "fup-rec" else ""))
            r.update(d1_select="s_slope", d1_slope=name)
            if optional:
                r.update(optional=True, d1_flag="ASSUMED_BOUNDARY")
            rows.append(r)
    for rid, level in D1_S_PATCH_LEVELS:
        c = r9.g6_case("G1", "J1", "FL", level=level, group="D1-S", duration_s=D1_S_PATCH_DURATION_S)
        c["case"] = c["case"].replace("G6_", "D1S_", 1)
        rows.append(_soil_vb(sb, r9, c, rid, role="judge",
                             note=f"{D1_BATCH} {rid}: G1 base + J1 patch @FL (G6P triple layout), pad B {level}, flat, "
                                  f"{D1_S_PATCH_DURATION_S:g} s, SCM VB; P3 + G6 judged"))
    return rows


def psc_rows(sb: ModuleType) -> list[dict[str, Any]]:
    """D1-PSC (optional): J1 B top flat, base + event rows (``--soil-event LEG:d:T:trigger``), VB."""
    r9 = _r9()
    rows = []
    bases: dict[str, str] = {}
    for leg in sorted({p[1] for p in D1_PSC_PROFILES}):
        c = r9.p3b_case("D1-PSC", "J1", "B", "top", 4.0)
        c["soil_patch"] = {"leg": leg, "set": "J1", "grid_m": r9.P3B_PAD_GRID_M["J1"]}
        c.update(case=f"D1PSC_J1_B_top_Fs4_sp{leg}J1_base", duration_s=D1_PSC_DURATION_S,
                 sim_s=r9.CRAWLER_SETTLE_S + D1_PSC_DURATION_S)
        bases[leg] = c["case"]
        r = _soil_vb(sb, r9, c, f"PSC-base-{leg}", role="timing base",
                     note=f"{D1_PSC_BATCH} base {leg}: triple layout J1@{leg}, no event (timing source, "
                          "bit-identical to the event rows until t_ev)", p3b_form=True)
        r.update(group=D1_PSC_BATCH, optional=True, d1_select="psc")
        rows.append(r)
        base_c = c
        for name, pleg, d_mm, t_s, timing in D1_PSC_PROFILES:
            if pleg != leg:
                continue
            ev = dict(base_c)
            trig = "ready+5" if timing == "ready+5" else f"mid@{bases[leg]}"
            ev.update(case=f"D1PSC_J1_B_top_Fs4_{leg}_{name.replace('-', '')}",
                      soil_event=f"{leg}:{d_mm:g}:{t_s:g}:{trig}")
            r = _soil_vb(sb, r9, ev, f"PSC-{name}-{leg}", role="judge (426.3 E-1 .. E-7 + DSb75 record)",
                         note=f"{D1_PSC_BATCH} {name} @{leg}: d {d_mm:g} mm / T {t_s:g} s P345, {timing}; frame "
                              f"lowering of the patch terrain (C-3 probe {D1_PSC_PROBE} passed)", p3b_form=True)
            r.update(group=D1_PSC_BATCH, optional=True, d1_select="psc", depends_on=bases[leg])
            rows.append(r)
    return rows


def d1_batches(sb: ModuleType) -> dict[str, list[dict[str, Any]]]:
    """The two D-1 batches for ``s9_batch.batches`` (names unique inside each batch)."""
    out = {D1_BATCH: [*c2_rows(sb), *c1_rows(sb), *soil_rows(sb)], D1_PSC_BATCH: psc_rows(sb)}
    for name, rows in out.items():
        names = [r["case"] for r in rows]
        dup = sorted({n for n in names if names.count(n) > 1})
        if dup:
            raise RuntimeError(f"{name}: duplicate row names {dup}")
    return out


def required_count(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Distinct D-1 ids per kind (C2 8, C1 4, S 4 = 16 required)."""
    ids = {r["d1_id"] for r in rows if not r.get("optional") or r.get("d1_select") == "s_slope"}
    return {"C2": sum(i.startswith("C2-") for i in ids), "C1": sum(i.startswith("C1-") for i in ids),
            "S": sum(i.startswith("S-") for i in ids)}
