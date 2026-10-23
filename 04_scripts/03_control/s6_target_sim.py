"""S6 control spec, time-domain part: C2 R2 (H4) with a non-zero attitude target on the reduced 6-DoF plant.

Re-uses (imports only, nothing modified):
  04_scripts/03_control/run_c2_reanchor.py  C2RN (= C2 R1 'R:BS_hold' + REANCHOR), VARIANTS['H4'], ra_metrics
  04_scripts/01_dynamics/run_pad_tangential_check.py TPlant (pad tangential bushing record), via run_c2_reanchor
  04_scripts/03_control/run_c2_timedomain.run_case (1 step delay + 0.1 s ramp loop)
Added here (controller wrapper C2RT, scratch only):
  * attitude target (phi_t, theta_t): the controller sees phi_meas - phi_t, theta_meas - theta_t, so the PI error,
    the completion check (0.03 deg), the re-level monitor (0.07 deg) and the REANCHOR attitude abort all become
    relative to the target (proposed implementation),
  * REANCHOR trigger mode: 'rel' = |theta_c - theta_t| >= 2.5 deg (falls out of the offset), 'abs' = |theta_c| >= 2.5 deg
    (current R2 rule), 'off',
  * optional target change after the first READY (t_ready_first + delay),
  * motor-stroke maximum tracking (from the measured motor stroke, noise 0.1 mm).
Conventions: body x fwd, y left, z up; roll > 0 left up, pitch > 0 nose down; floor slope = attitude on the
crawler; leg speed > 0 = extension; negative feedback in all C2 channels; T = 20 ms ZOH; plant dt 5e-4 s.
Seed 12345 (sensor noise; motor-stroke noise seed + 1000).

Run: conda run -n dynamics-dev python -I s6_target_sim.py <project_root> <out_json> [workers]
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control"))
import run_c2_reanchor as rca  # noqa: E402
import run_pad_tangential_check as ptc  # noqa: E402
import run_mast_flex_c2_check as rmf  # noqa: E402
import run_control_comparison as rcc  # noqa: E402
import run_c2_timedomain as c2t  # noqa: E402
import run_c2_revision as rcr  # noqa: E402

DEG = math.pi / 180.0
TGT: dict = {}        # per-run target settings (set in run_tgt, read by C2RT)


class C2RT(rca.C2RN):
    name = "C2RT"

    def __init__(self, ctx, contact="pressure"):
        super().__init__(ctx, contact=contact)
        self.tgt = tuple(TGT.get("target_deg", (0.0, 0.0)))
        self.change = TGT.get("change")            # (delay after first READY [s], (roll, pitch) deg) or None
        self.changed_at = None
        self.s_max_seen = np.full(4, -1.0)
        self.s_max_after_change = np.full(4, -1.0)
        self.att_ground_abs = None
        self.ready_times = []

    def _offset(self, m):
        m2 = dict(m)
        m2["phi"] = m["phi"] - self.tgt[0] * DEG
        m2["theta"] = m["theta"] - self.tgt[1] * DEG
        return m2

    def on_touch(self, m):
        super().on_touch(m)                         # att_ground = filtered attitude minus target (relative)
        self.att_ground_abs = (self.att_ground[0] + self.tgt[0] * DEG, self.att_ground[1] + self.tgt[1] * DEG)

    def _eligible(self, m):
        mode = TGT.get("ra_mode", "rel")
        if mode == "off":
            return "disabled"
        if mode == "abs" and self.att_ground_abs is not None:
            keep = self.att_ground
            self.att_ground = self.att_ground_abs
            try:
                return super()._eligible(m)
            finally:
                self.att_ground = keep
        return super()._eligible(m)

    def update(self, m, t):
        if "s" in m:
            self.s_max_seen = np.maximum(self.s_max_seen, m["s"])
            if self.changed_at is not None:
                self.s_max_after_change = np.maximum(self.s_max_after_change, m["s"])
        if (self.change is not None and self.changed_at is None and self.t_ready_first is not None
                and t >= self.t_ready_first + self.change[0] - 1e-9):
            self.changed_at = t
            self.tgt_cmd = tuple(self.change[1])
            if TGT.get("rerun_reanchor") and self.ra is not None and self.ra.get("st") == "finished":
                # anchor reference = relative pitch at which the pads were last anchored
                old = self.tgt
                done_ra = str(self.ra.get("outcome", "")).startswith("completed")
                anchor_abs_pitch = old[1] if done_ra else self.att_ground_abs[1]
                self.att_ground = (self.att_ground[0], anchor_abs_pitch * DEG - self.tgt_cmd[1] * DEG)
                self.att_ground_abs = (self.att_ground_abs[0], anchor_abs_pitch * DEG)
                self.ra = None
                self.ra_reruns = getattr(self, "ra_reruns", 0) + 1
            if not TGT.get("ramp_deg_s"):
                self.tgt = tuple(self.tgt_cmd)
        if self.changed_at is not None and TGT.get("ramp_deg_s"):
            rr, rp = TGT["ramp_deg_s"]
            d_r = self.tgt_cmd[0] - self.tgt[0]; d_p = self.tgt_cmd[1] - self.tgt[1]
            if TGT.get("ramp_norm") == "diamond":      # |phi_dot|/r_phi + |theta_dot|/r_theta <= 1
                need = abs(d_r) / rr + abs(d_p) / rp
            else:                                      # per-axis rate limits, straight line
                need = max(abs(d_r) / rr, abs(d_p) / rp)
            lam = 1.0 if need <= rcc.T_CTRL else rcc.T_CTRL / need
            self.tgt = (self.tgt[0] + lam * d_r, self.tgt[1] + lam * d_p)
        was_ready = self.ready
        u = super().update(self._offset(m), t)
        if self.ready and not was_ready:
            self.ready_times.append(round(float(t), 2))
        return u


def run_tgt(case):
    case = dict(case)
    TGT.clear(); TGT.update(case.get("tgt", {}))
    rmf.CONFIG.clear(); rmf.CONFIG.update({"record": True})
    ptc.RCFG.clear(); ptc.RCFG["case_id"] = case["id"]
    roll, pitch = case["floor_deg"]
    rca.RA.clear(); rca.RA.update(rca.VARIANTS["H4"])
    rcc.Plant = ptc.TPlant; rcc.Sensors = rcr.SensorsS
    c2t.C2D = C2RT
    rcc.CA.update(c2t.OPTION_DEFAULTS); rcc.CA.update(c2t.GAINSETS[rca.R1])
    rcc.CA["Fs_band_N"] = float(case.get("F_band", rca.F_BAND_D5))
    rcc.T_HOLD = float(case.get("t_hold", 10.0))
    t0 = time.perf_counter()
    try:
        r = c2t.run_case(level=case.get("level", "top"), roll=roll, pitch=pitch, beta=case.get("beta", 1.0e9),
                         Fs=case.get("Fs", 0.0), contact=case.get("contact", "pressure"), seed=case.get("seed", 12345),
                         keep_series=True)
        pl = rmf.LAST["plant"]; ctrl = rmf.LAST["ctrl"]
        if not isinstance(pl, ptc.TPlant) or pl.case_id != case["id"] or type(ctrl) is not C2RT:
            raise RuntimeError("identity check failed")
        S = r.pop("_series")
        ra = rca.ra_metrics(S, r, pl, ctrl)
        t = np.asarray(S["t"])
        att = np.degrees(np.column_stack([S["phi"], S["theta"]]))
        tl = r.get("t_crawler_liftoff_s")
        post = t >= (tl if tl is not None else 0.0)
        tgt_final = np.array(getattr(ctrl, "tgt_cmd", ctrl.tgt))
        fin = t >= t[-1] - 5.0
        out = {"id": case["id"], "group": case.get("group"), "level": case.get("level", "top"),
               "floor_deg": [roll, pitch], "target_deg": list(case.get("tgt", {}).get("target_deg", (0, 0))),
               "change": case.get("tgt", {}).get("change"), "ra_mode": case.get("tgt", {}).get("ra_mode", "rel"),
               "contact": case.get("contact", "pressure")}
        out["fails_raw"] = r.get("fails")
        out["fails"] = [f for f in (r.get("fails") or []) if not f.startswith("ss")]
        for k in ("t_touch_s", "t_crawler_liftoff_s", "t_done_s", "t_ready_s", "min_true_cyl_force_kN", "min_true_leg",
                  "max_pressure_bar", "stroke_limit_steps", "force_sat_210bar_steps", "levelled_loads_true_kN",
                  "final_clearance_mm", "events"):
            out[k] = r.get(k)
        out["ready_times_s"] = ctrl.ready_times
        out["changed_at_s"] = None if ctrl.changed_at is None else round(float(ctrl.changed_at), 2)
        out["ra_reruns"] = getattr(ctrl, "ra_reruns", 0)
        out["ra_events"] = ctrl.ra_events[-4:]
        out["s_max_seen_mm"] = (ctrl.s_max_seen * 1e3).round(2).tolist()
        sfin = np.asarray(pl.sref)
        out["s_final_mm"] = (sfin * 1e3).round(2).tolist()
        j = int(np.argmax(ctrl.s_max_seen))
        out["s_overshoot_mm"] = round(float(ctrl.s_max_seen[j] - sfin[j]) * 1e3, 2)      # max-stroke leg
        out["s_overshoot_any_leg_mm"] = round(float(np.max(ctrl.s_max_seen - sfin)) * 1e3, 2)
        if ctrl.changed_at is not None:
            out["s_max_after_change_mm"] = (ctrl.s_max_after_change * 1e3).round(2).tolist()
            ws = t >= ctrl.changed_at
            out["min_true_crawler_clearance_after_change_mm"] = round(float(np.min(S["clr"][ws])) * 1e3, 1)
            Ft = S["Ftrue"][ws]
            out["min_true_cyl_after_change_kN"] = round(float(Ft.min()) / 1e3, 2)
            if len(ctrl.ready_times) >= 2:
                out["t_change_to_ready_s"] = round(ctrl.ready_times[-1] - ctrl.changed_at, 2)
            dev = att[ws] - tgt_final[None, :]
            a0 = np.array(case["tgt"]["target_deg"]); d_t = tgt_final - a0
            osh = []
            for k in range(2):
                if abs(d_t[k]) > 0.05:
                    osh.append(round(float(max(0.0, np.max(np.sign(d_t[k]) * dev[:, k]))), 4))
                else:
                    osh.append(0.0)
            out["att_overshoot_after_change_deg"] = osh
        out["min_true_crawler_clearance_post_lift_mm"] = round(float(np.min(S["clr"][post])) * 1e3, 1) if post.any() else None
        out["ss_err_vs_target_deg"] = round(float(np.abs(att[fin] - tgt_final[None, :]).max()), 4)
        out["ss_att_mean_deg"] = att[fin].mean(axis=0).round(4).tolist()
        out["ra"] = {k: ra.get(k) for k in ("outcome", "theta_ground_deg", "Ft_final_kN", "Ft_at_done_kN",
                                             "min_true_cyl_post_liftoff_substep_kN", "min_true_cyl_during_kN",
                                             "max_att_dev_deg", "duration_s", "Ft_maxleg_start_kN",
                                             "Ft_maxleg_final_kN", "Ft_maxleg_reduction", "t_start_s", "t_end_s")}
        out["ra"]["theta_crawler_abs_deg"] = None if ctrl.att_ground_abs is None else round(ctrl.att_ground_abs[1] / DEG, 3)
        out["ra"]["stop_readings_kN"] = [round(e["P_kN"], 2) for e in ctrl.ra_log if e["what"] == "hold"]
        if r.get("t_ready_s") is not None and r.get("t_touch_s") is not None:
            out["t_level_after_touch_s"] = round(r["t_ready_s"] - r["t_touch_s"], 2)
    except Exception as e:  # noqa: BLE001
        import traceback
        out = {"id": case["id"], "error": repr(e), "tb": traceback.format_exc()[-2000:]}
    finally:
        rcc.T_HOLD = 10.0
    out["wall_s"] = round(time.perf_counter() - t0, 1)
    return out


def cases(stage="all"):
    C = []

    def add(cid, group, floor, target=(0.0, 0.0), ra_mode="rel", change=None, t_hold=10.0, tgx=None, **kw):
        tg = {"target_deg": tuple(target), "ra_mode": ra_mode}
        if change is not None:
            tg["change"] = change
        if tgx:
            tg.update(tgx)
        C.append(dict(id=cid, group=group, floor_deg=floor, tgt=tg, t_hold=t_hold, **kw))

    if stage == "change3":
        for fl, a, b, nm in [((0.0, 0.0), (0.0, 0.0), (2.2, 1.6), "flat|0->r2.2p1.6"),
                             ((0.0, 0.0), (0.0, 0.0), (0.0, 3.0), "flat|0->p+3"),
                             ((0.0, 0.0), (-2.2, -1.6), (2.2, 1.6), "flat|r-2.2p-1.6->r2.2p1.6"),
                             ((2.2, 1.6), (0.0, 0.0), (2.2, 1.6), "P:diag++|0->r2.2p1.6")]:
            add(f"C3|{nm}|diamond.4/.25", "change_ramp_diamond", fl, a, change=(5.0, b), t_hold=80.0,
                tgx={"ramp_deg_s": (0.4, 0.25), "ramp_norm": "diamond"})
            add(f"C3|{nm}|step", "change_step", fl, a, change=(5.0, b), t_hold=80.0)
        return C
    if stage == "change2":
        chg = [((0.0, 0.0), (0.0, 0.0), (0.0, 3.0), "flat|0->p+3"),
               ((0.0, 0.0), (0.0, 3.0), (0.0, -3.0), "flat|p+3->p-3"),
               ((0.0, 0.0), (4.0, 0.0), (-4.0, 0.0), "flat|r+4->r-4"),
               ((0.0, 0.0), (0.0, 0.0), (2.2, 1.6), "flat|0->r2.2p1.6"),
               ((0.0, -3.2), (0.0, -1.6), (0.0, 0.0), "P:pitch-3.2|p-1.6->0")]
        for fl, a, b, nm in chg:
            for rname, ramp in (("ramp.4/.25", (0.4, 0.25)), ("ramp.25/.15", (0.25, 0.15))):
                add(f"C2|{nm}|{rname}", "change_ramp", fl, a, change=(5.0, b), t_hold=80.0, tgx={"ramp_deg_s": ramp})
        for fl, a, b, nm in chg[:2]:
            add(f"C2|{nm}|ramp.4/.25|rerun", "change_rerun", fl, a, change=(5.0, b), t_hold=100.0,
                tgx={"ramp_deg_s": (0.4, 0.25), "rerun_reanchor": True})
        add("C2|flat|0->p-3|ramp.4/.25|rerun", "change_rerun", (0.0, 0.0), (0.0, 0.0), change=(5.0, (0.0, -3.0)),
            t_hold=100.0, tgx={"ramp_deg_s": (0.4, 0.25), "rerun_reanchor": True})
        add("C2|flat|0->p-3|ramp.4/.25", "change_ramp", (0.0, 0.0), (0.0, 0.0), change=(5.0, (0.0, -3.0)),
            t_hold=100.0, tgx={"ramp_deg_s": (0.4, 0.25)})
        return C

    # (0) regression: zero target must reproduce c2_design.md 17.7 Q11 (top, nose-down 3.5, H4, pressure)
    add("reg|V:pitch+3.5|t0|abs", "regression", (0.0, 3.5), ra_mode="abs")
    add("reg|V:pitch+3.5|t0|rel", "regression", (0.0, 3.5), ra_mode="rel")
    # (A) stroke overshoot at the worst accepted static points (rule A, envelope map) and verification vertices
    for fl, tg, nm in [((0.0, -3.2), (0.0, 0.0), "P:pitch-3.2|t0"), ((0.0, 3.2), (0.0, 0.0), "P:pitch+3.2|t0"),
                       ((0.0, -3.5), (0.0, 0.0), "V:pitch-3.5|t0"),
                       ((0.0, 0.0), (0.0, 3.0), "flat|p+3"), ((0.0, 0.0), (0.0, -3.0), "flat|p-3"),
                       ((0.0, 0.0), (-0.25, 3.0), "flat|r-0.25p+3"), ((0.0, 0.0), (4.0, 0.0), "flat|r+4"),
                       ((0.0, 0.0), (-4.0, 0.0), "flat|r-4"), ((0.0, 0.0), (2.2, 1.6), "flat|r+2.2p+1.6"),
                       ((2.2, 1.6), (1.75, -1.25), "P:diag++|r1.75p-1.25"), ((0.0, 3.2), (0.0, 1.6), "P:pitch+3.2|p+1.6"),
                       ((4.4, 0.0), (1.75, -1.25), "P:roll+4.4|r1.75p-1.25")]:
        add(f"A|{nm}", "overshoot", fl, tg)
    for lvl in ("middle", "bottom"):
        add(f"A|{lvl}|P:pitch-3.2|t0", "overshoot", (0.0, -3.2), level=lvl)
        add(f"A|{lvl}|flat|p+3", "overshoot", (0.0, 0.0), (0.0, 3.0), level=lvl)
    # (C) target change after the first READY (+5 s), run on 60 s after READY
    for fl, a, b, nm in [((0.0, 0.0), (0.0, 0.0), (0.0, 3.0), "flat|0->p+3"),
                         ((0.0, 0.0), (0.0, 3.0), (0.0, -3.0), "flat|p+3->p-3"),
                         ((0.0, 0.0), (4.0, 0.0), (-4.0, 0.0), "flat|r+4->r-4"),
                         ((0.0, 0.0), (0.0, 0.0), (2.2, 1.6), "flat|0->r2.2p1.6"),
                         ((0.0, -3.2), (0.0, -1.6), (0.0, 0.0), "P:pitch-3.2|p-1.6->0")]:
        add(f"C|{nm}", "change", fl, a, change=(5.0, b), t_hold=70.0)
    # (B) H4 trigger: relative vs absolute pitch
    for fl, tg, nm in [((0.0, 0.0), (0.0, 3.0), "flat|p+3"), ((0.0, 0.0), (0.0, -3.0), "flat|p-3"),
                       ((0.0, 3.2), (0.0, 3.0), "P:pitch+3.2|p+3"), ((0.0, 3.5), (0.0, 1.0), "V:pitch+3.5|p+1"),
                       ((0.0, -3.5), (0.0, 0.0), "V:pitch-3.5|t0")]:
        for mode in ("off", "abs", "rel"):
            add(f"B|{nm}|{mode}", "trigger", fl, tg, ra_mode=mode)
    # combined contact judge (default of c2.py) on two key cases
    add("A|flat|p+3|combined", "overshoot", (0.0, 0.0), (0.0, 3.0), contact="combined")
    add("A|P:pitch-3.2|t0|combined", "overshoot", (0.0, -3.2), (0.0, 0.0), contact="combined")
    # remove duplicates of B with A (same settings) is not needed: ids differ
    return C


def main():
    out_json = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    cores = c2t.set_affinity()
    C = cases(sys.argv[4] if len(sys.argv) > 4 else "all")
    import multiprocessing as mp
    t0 = time.time()
    res = []
    with mp.get_context("spawn").Pool(min(workers, len(C))) as pool:
        for r in pool.imap_unordered(run_tgt, C):
            res.append(r)
            print(f"{time.time() - t0:7.1f} s  {r['id']}  wall {r.get('wall_s')}  {r.get('error', '')}", flush=True)
    order = {c["id"]: i for i, c in enumerate(C)}
    res.sort(key=lambda r: order[r["id"]])
    out_json.write_text(json.dumps({"meta": {"script": __file__, "affinity": str(cores), "runtime_s": time.time() - t0,
                                             "n_runs": len(C)}, "runs": res}, indent=1, default=float))
    print("written", out_json)


if __name__ == "__main__":
    main()
