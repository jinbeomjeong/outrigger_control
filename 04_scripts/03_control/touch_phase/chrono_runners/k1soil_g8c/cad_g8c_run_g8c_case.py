"""One row of the G8C3 batch (non-planar start, RL g_start 230 mm), pinned checkout 74032be, flow limit off. No source change.

Engines:
  L1R  run_S6C.job_bundle_c, the existing G8C runner (rigid block ``chrono/pad_block``, plant F_s 0 by construction).
  L2b  run_S8C.job_l2b_s8 with F_s 4 kN. No block exists on L2bModel and ``pad_gap_offsets_m`` is limited to the 60 mm sphere
       radius, so the raised floor is the S8 event patch (``chrono/l2b_ground_patch``, never scheduled) with its top face moved h
       along the floor normal, h = g0 - g_start with g0 measured on a probe model after the crawler settle.

Usage: python -I -B -X utf8 -u run_g8c_case.py --row E1|R2|R3|R2L1|R3L1|E0L2|E1L2 [--k1] [--check-short]
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = HERE.parent / "cad_c4g2" / "wt"
MAIN = Path(r"C:\workspace\outrigger_control")
COMMIT = "74032beae72c7e44858e41384bc54c263e724fd3"
C2_SHA = "28482b8d5678c3e1079c9dd89046013bd60cac718e0e8efa195101a36236df67"
BATCH = MAIN / "07_results/S9/batch_g8c3_20261105"
LEG, G_START_M = "RL", 0.230
ECORES = list(range(16, 24))
ROWS = {"E1": ("L1R", "edge", "on", "G8C3_top_edge_RL_g230_C4G2"),
        "R2": ("L2b", "rpB", "off", "G8CL2b_top_rpB_RL_g230_Fs4_off"),
        "R3": ("L2b", "rpB", "on", "G8CL2b_top_rpB_RL_g230_Fs4_C4G2"),
        "R2L1": ("L1R", "rpB", "off", "G8C3_top_rpB_RL_g230_off"),
        "R3L1": ("L1R", "rpB", "on", "G8C3_top_rpB_RL_g230_C4G2"),
        "E0L2": ("L2b", "edge", "off", "G8CL2b_top_edge_RL_g230_Fs4_off"),
        "E1L2": ("L2b", "edge", "on", "G8CL2b_top_edge_RL_g230_Fs4_C4G2")}
ALLOWED_ENV = {"OUTRIGGER_ROD_SIDE_MECHANICS", "OUTRIGGER_PLACEMENT", "OUTRIGGER_RUN_PLACEMENT"}
REDIRECTED: list[str] = []


class MainTreeRedirect:
    """Meta path finder: a module the path finder resolves under the main tree loads from the same relative file of the checkout."""

    @staticmethod
    def find_spec(name, path=None, target=None):
        spec = importlib.machinery.PathFinder.find_spec(name, path, target)
        origin = getattr(spec, "origin", None) if spec is not None else None
        if origin is None or not Path(origin).exists() or not Path(origin).resolve().is_relative_to(MAIN.resolve()):
            return spec
        twin = WT / Path(origin).resolve().relative_to(MAIN.resolve())
        if not twin.exists():
            raise ImportError(f"{name}: main-tree module {origin} has no twin in the checkout")
        REDIRECTED.append(f"{name}: {origin} -> {twin}")
        locations = [str(twin.parent)] if spec.submodule_search_locations is not None else None
        return importlib.util.spec_from_file_location(name, str(twin), submodule_search_locations=locations)


sys.meta_path.insert(0, MainTreeRedirect)
sys.path.insert(0, str(WT / "03_src"))
sys.path.insert(0, str(WT / "04_scripts" / "02_chrono"))


def main_tree_modules() -> list[str]:
    root = MAIN.resolve()
    return [f"{n}: {m.__file__}" for n, m in list(sys.modules.items()) if getattr(m, "__file__", None) and Path(m.__file__).resolve().is_relative_to(root)]


def code_state() -> dict:
    import outrigger_sim
    from outrigger_sim.control import c2

    import run_S6C
    import run_S8C

    sha = hashlib.sha256(Path(c2.__file__).read_bytes()).hexdigest()
    out = {"outrigger_sim": outrigger_sim.__file__, "run_S6C": run_S6C.__file__, "run_S8C": run_S8C.__file__, "c2": c2.__file__, "c2_sha256": sha, "commit": COMMIT, "git_link": (WT / ".git").read_text(encoding="utf-8").strip()}
    inside = all(Path(out[k]).resolve().is_relative_to(WT.resolve()) for k in ("outrigger_sim", "run_S6C", "run_S8C"))
    if sha != C2_SHA or not inside or main_tree_modules():
        raise SystemExit(f"code mix, stopped: {out} {main_tree_modules()}")
    return out


def install_preset(flags: dict) -> dict:
    """The runners call ``C2Config().with_10hz_d1()`` without a config argument, so the keywords go through the preset default."""
    from outrigger_sim.control import c2

    real = c2.C2Config.with_10hz_d1

    def preset(self, **kw):
        for k, v in flags.items():
            kw.setdefault(k, v)
        return real(self, **kw)

    c2.C2Config.with_10hz_d1 = preset
    cfg = c2.C2Config().with_10hz_d1()
    return {"flags": flags, "hold": str(cfg.touch_twist_hold), "retrigger_samples": cfg.r8.lifted_reapproach.retrigger_samples, "clip": cfg.clip_returned_command}


def l1r_case(s6c, cid: str, floor: str):
    """The ``g8c76_cases`` definition with the block and the id of this row (the table has no rpB row)."""
    note = f"G8C3 batch: {floor} top, block under {LEG}, zero-stroke gap g_start {G_START_M * 1e3:g} mm; L1-R plant F_s 0"
    sc = s6c._d8("top", floor)
    sc = dataclasses.replace(sc, case_id=cid, group="G8", items=("G8",), duration_s=sc.duration_s + s6c.G8_EXTRA_S, notes=(note,))
    return s6c.BundleCCase(cid, "G8-C3", sc, notes=(note,), end_after_ready_s=s6c.G8_END_AFTER_READY_S, pad_block=(LEG, G_START_M))


def run_l1r(cid: str, floor: str, d: Path, duration: float | None) -> dict:
    import run_S6C as s6c

    s6c.STATES = MAIN / "07_results" / "states_L1R"  # the checkout has no 07_results; snapshots are read only
    case = l1r_case(s6c, cid, floor)
    summary, _ = s6c.job_bundle_c(case, d, duration_s=duration)
    (d / "result.json").write_text(json.dumps(s6c._plain(summary), indent=1, ensure_ascii=False), encoding="utf-8")
    return {"states": str(s6c.STATES), "fs_kN_plant": 0.0}


class L2bGapRecorder:
    """True crawler clearance of the L2b model: ``n . (c_k - p0) - r`` over the crawler spheres, every 100 steps (10 ms), as ``run_S6C.CrawlerGapRecorder``."""

    def __init__(self, model):
        import numpy as np
        import pychrono as ch

        from outrigger_sim.chrono.probes import chvec

        self.model, self.sup, self.every, self._k = model, model.superstructure, 100, 0
        self.locals = tuple(chvec(c) for c in model.crawler_centres_local_m)
        self.radius = float(model.crawler_layout.sphere_radius_m)
        v = model.floor.TransformDirectionLocalToParent(ch.ChVector3d(0.0, 0.0, 1.0))
        self.n = np.array([v.x, v.y, v.z])
        self.d0 = float(self.n @ np.asarray(model.floor_point_world_m, float))
        self.t, self.rows = [], []

    def gaps_m(self):
        import numpy as np

        out = np.empty(len(self.locals))
        for i, c in enumerate(self.locals):
            p = self.sup.TransformPointLocalToParent(c)
            out[i] = p.x * self.n[0] + p.y * self.n[1] + p.z * self.n[2] - self.d0 - self.radius
        return out

    def __call__(self, engine) -> None:
        del engine
        self._k += 1
        if self._k % self.every == 0:
            self.t.append(float(self.model.system.GetChTime()))
            self.rows.append(self.gaps_m())

    def save(self, path: Path) -> dict:
        import numpy as np

        g = np.asarray(self.rows, float).reshape(-1, len(self.locals))
        np.savez_compressed(path, t=np.asarray(self.t, float), gaps_m=g, min_gap_m=g.min(axis=1) if g.size else np.zeros(0), argmin=g.argmin(axis=1) if g.size else np.zeros(0, int))
        return {"file": path.name, "samples": len(self.t), "every_steps": self.every, "spheres": len(self.locals), "sphere_radius_m": self.radius, "rule": "n . (c_k - p0) - r over every crawler sphere, base floor plane"}


def install_l2b_block(s8, info: dict) -> None:
    """Raised floor under the leg through the unscheduled event patch; build, settle and step-hook wrappers. No source change."""
    import numpy as np

    import outrigger_sim.chrono.l2b_ground_patch as gp

    s7c, st = s8.s7c, s8.st
    j = s8.LEG_NAMES.index(LEG)
    real_build, real_attach, real_settle, real_chain = s8.build_l2b, gp.attach_ground_patches, s7c.settle_l2b, st._chain_hooks

    def build(case, *, patch_legs=()):
        if patch_legs:
            raise SystemExit(f"{case.case_id}: this batch has no floor event, got {patch_legs}")
        probe = real_build(case)[0]
        real_settle(probe, s7c.CRAWLER_SETTLE_S)
        g0 = np.asarray(st.pad_gaps_m(probe), float).copy()
        del probe
        h = float(g0[j]) - G_START_M
        if not h > 0.0:
            raise SystemExit(f"g_start {G_START_M} m not below g0 {g0[j]} m")
        info.update(g0_m=g0.tolist(), h_m=h)

        def attach(model, legs):
            z = model.floor_z_m
            model.floor_z_m = z + h  # read once, for the patch box centre in the floor frame (l2b_ground_patch)
            try:
                return real_attach(model, legs)
            finally:
                model.floor_z_m = z

        gp.attach_ground_patches = attach
        try:
            return real_build(case, patch_legs=(LEG,))
        finally:
            gp.attach_ground_patches = real_attach

    def settle(model, seconds):
        start = real_settle(model, seconds)
        gaps = np.asarray(st.pad_gaps_m(model), float).copy()
        measured = float(gaps[j]) - info["h_m"]
        info.update(g_start_measured_m=measured, gaps_above_base_floor_m=gaps.tolist(), box_top_floor_frame_m=model.ground_patches.patch_centres_floor_m[LEG][2] + gp.PATCH_HALF_SIZE_M[2], floor_z_m=model.floor_z_m)
        if abs(measured - G_START_M) > 1.0e-3:
            raise SystemExit(f"block geometry check failed: gap {measured} m, target {G_START_M} m")
        if abs(info["box_top_floor_frame_m"] - model.floor_z_m - info["h_m"]) > 1.0e-12:
            raise SystemExit(f"patch box top check failed: {info}")
        info["recorder"] = L2bGapRecorder(model)
        return start

    def chain(*hooks):
        return real_chain(*hooks, info["recorder"])

    s8.build_l2b, s7c.settle_l2b, st._chain_hooks = build, settle, chain


def run_l2b(cid: str, floor: str, d: Path, duration: float | None) -> dict:
    from outrigger_sim.control.c2 import C2Config

    import run_S6C as s6c
    import run_S8C as s8

    template =s8.case_table()["K24_top_rpB_Fs4"]
    note = f"G8C3 batch: {floor} top, raised floor under {LEG}, g_start {G_START_M * 1e3:g} mm, F_s {template.fs_kN:g} kN, unscheduled event patch"
    base = dataclasses.replace(s8._bc(cid, s8._d8_scenario("top", floor)), config="G8-L2b", notes=(note,))
    case = dataclasses.replace(template, case_id=cid, base=base, pair_fs0=None, pair_judge=None, notes=(note,))
    info: dict = {}
    install_l2b_block(s8, info)
    summary, _ = s8.job_l2b_s8(case, d, duration_s=duration)
    rec = info.pop("recorder")
    gaps = rec.rows[-1] if rec.rows else rec.gaps_m()
    events = json.loads((d / "controller_events.json").read_text(encoding="utf-8"))
    summary["g8"] = {"leg": LEG, "g_start_target_m": G_START_M, **info, "fs_kN_plant": case.fs_kN, "crawler_gap": rec.save(d / s6c.G8_GAP_NAME),
                     "crawler_gap_end_m": {"min": float(gaps.min()), "argmin": int(gaps.argmin()), "all": [float(v) for v in gaps]},
                     "clearance_target_m": float(C2Config().with_10hz_d1().thresholds.clearance_target_m),
                     "fault_event_names": [e for e in events if "FAULT" in e],
                     "rule": "L2b raised floor: h = g0 - g_start, g0 on a probe model after the crawler settle; unscheduled event patch, box top + h along the floor normal"}
    (d / "result.json").write_text(json.dumps(s6c._plain(summary), indent=1, ensure_ascii=False), encoding="utf-8")
    return {"block": {k: summary["g8"].get(k) for k in ("g0_m", "h_m", "g_start_measured_m")}, "fs_kN_plant": case.fs_kN, "flow_limit": summary["settings"]["s8"].get("flow_limit")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--row", required=True, choices=tuple(ROWS))
    ap.add_argument("--k1", action="store_true", help="also reapproach_retrigger_two_samples (not part of the default rows; the case folder gets _K1)")
    ap.add_argument("--check-short", action="store_true", help="2 s loop on the E-cores 16..23, scratch folder")
    me = ap.parse_args()
    engine, floor, cfg_name, cid = ROWS[me.row]
    if me.k1 and cfg_name != "on":
        raise SystemExit("--k1 is for a C4G2 row")
    cid += "_K1" if me.k1 else ""
    bad = {k: v for k, v in os.environ.items() if k.startswith("OUTRIGGER_") and k not in ALLOWED_ENV}
    if bad:
        raise SystemExit(f"OUTRIGGER_* set, refusing: {bad}")
    os.chdir(WT)
    if me.check_short:
        import psutil

        os.environ["OUTRIGGER_RUN_PLACEMENT"] = "ecore"
        psutil.Process().cpu_affinity(ECORES)
    state = code_state()
    flags = {"touch_twist_hold": True} if cfg_name == "on" else {}
    flags = {**flags, "reapproach_retrigger_two_samples": True} if me.k1 else flags
    config = install_preset(flags)
    root = (HERE / "check_short") if me.check_short else BATCH
    d = root / cid
    if d.exists():
        raise SystemExit(f"case folder exists: {d}")
    d.mkdir(parents=True)
    print("row", me.row, engine, floor, cfg_name, cid, config, flush=True)
    duration = 2.0 if me.check_short else None
    extra = run_l1r(cid, floor, d, duration) if engine == "L1R" else run_l2b(cid, floor, d, duration)
    side = dict(state, row=me.row, engine=engine, floor=floor, config_name=cfg_name, config=config, **extra, main_tree_modules_at_end=main_tree_modules(), redirected=REDIRECTED,
                env={k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OUTRIGGER_PLACEMENT", "OUTRIGGER_RUN_PLACEMENT", "OUTRIGGER_ROD_SIDE_MECHANICS")})
    (d / "g8c_job_side.json").write_text(json.dumps(side, indent=1, default=str), encoding="utf-8")
    print("side", json.dumps({k: side[k] for k in ("c2_sha256", "config", "main_tree_modules_at_end")}, default=str), "extra", extra, "redirected", len(REDIRECTED), flush=True)
    if side["main_tree_modules_at_end"]:
        raise SystemExit(f"main-tree modules at the end: {side['main_tree_modules_at_end']}")


if __name__ == "__main__":
    main()
