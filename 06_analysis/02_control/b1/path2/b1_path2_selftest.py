"""Synthetic self-test of b1_path2.py (control-expert, path 2). No real B1 result is read.

Usage (dynamics-dev): python -I -B b1_path2_selftest.py --repo <checkout> --work <empty scratch folder>
Exit 0 = all checks pass, 1 = a check failed. The last stdout line is a JSON summary.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b1_path2 as p2  # noqa: E402

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, cond: bool, info: str = "") -> None:
    CHECKS.append((name, bool(cond), info))


def close(a, b, tol=1e-12) -> bool:
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


# ----------------------------------------------------------------------------- synthetic data

BASE = {
    "s_peak": 0.47, "n_peak": 700, "n_loc": 400, "n_ready": 800, "z_rate": 0.0002, "phi": 0.0, "theta": 0.01,
    "c_hat": 0.07, "margin_mm": 80, "c_target": 0.08, "loads": {"FL": 108099.1, "FR": 106106.0, "RL": 62096.68,
                                                                "RR": 60281.81},
    "duration": 160.0, "events_extra": [], "tag": p2.CTRL_TAG_VB, "nh_scale": 1.0, "rc": 0, "sgs": False,
}


def stroke_series(n: np.ndarray, peak: float, n_peak: int) -> np.ndarray:
    s = np.full((len(n), 4), 0.3)
    up = 0.40 + 1e-4 * n
    s[:, 0] = np.where(n <= n_peak, up, (0.40 + 1e-4 * n_peak) - 1e-5 * (n - n_peak))
    s[:, 0] += peak - (0.40 + 1e-4 * n_peak)
    return s


def sink_curve(t: np.ndarray, rate: float, t_loc: float) -> np.ndarray:
    z = np.where(t < t_loc, 0.09 * t / t_loc, 0.09 + rate * (np.minimum(t, 100.0) - t_loc))
    return np.repeat(z[:, None], 4, axis=1)


def events_for(cfg: dict) -> list[dict]:
    t_loc = cfg["n_loc"] * 0.1
    ev = [{"t": t_loc, "name": "crawler_liftoff_confirmed"},
          {"t": t_loc, "name": f"INFO_LOC_CLEARANCE_MARGIN:{cfg['margin_mm']}"}]
    if cfg["sgs"]:
        ev.append({"t": 90.0, "name": "FAULT_LIFT_STROKE_LIMIT:soil:FL"})
    ev += cfg["events_extra"]
    return ev


def make_chrono_row(root: Path, case: str, cfg: dict, prm: dict) -> None:
    d = root / case
    (d / "record").mkdir(parents=True, exist_ok=True)
    n = np.arange(0, int(round(cfg["duration"] / 0.1)) + 1)
    t10 = n * 0.1
    stroke = stroke_series(n, cfg["s_peak"], cfg["n_peak"])
    np.savez(d / "record" / "record.npz", **{"t": t10, "meas.stroke": stroke})
    t1 = np.round(np.arange(0, int(round(cfg["duration"] * 1000)) + 1) * 1e-3, 6)
    z1 = sink_curve(t1, cfg["z_rate"], cfg["n_loc"] * 0.1)
    np.savez(d / "step_series.npz", t=t1, pad_sinkage_geometric_m=z1,
             pad_contact_force_N=np.full((len(t1), 4), 5e4), crawler_load_N=np.zeros(len(t1)))
    z10 = sink_curve(t10, cfg["z_rate"], cfg["n_loc"] * 0.1)
    loads = np.tile([cfg["loads"][leg] for leg in p2.LEGS], (len(n), 1))
    grid = 0.01
    nh = np.array([round(prm["pad"][leg]["A"] / grid ** 2 * cfg["nh_scale"]) for leg in p2.LEGS], dtype=float)
    # hull with b_hull = b_poly: area A, perimeter 2A/b
    area = np.array([prm["pad"][leg]["A"] for leg in p2.LEGS])
    perim = np.array([2 * prm["pad"][leg]["A"] / prm["pad"][leg]["b_poly"] for leg in p2.LEGS])
    k_term = np.array([prm["kc"] / prm["pad"][leg]["b_poly"] + prm["kphi"] for leg in p2.LEGS])
    sigma = nh * grid ** 2 * k_term * z10 ** prm["n"]
    imu_t = np.round(np.arange(0, len(n) * 10) * 0.01, 6)
    np.savez(d / "record" / "b1_grid_record.npz",
             n=n, load_read_N=loads, att_raw_rad=np.tile([cfg["phi"], cfg["theta"]], (len(n), 1)),
             c_hat_m=np.full(len(n), cfg["c_hat"]),
             c_hat_corner_m=np.tile([cfg["c_hat"]] * 4, (len(n), 1)),
             c_target_m=np.full(len(n), cfg["c_target"]),
             n_contact=np.tile(nh, (len(n), 1)), contact_hull_area_m2=np.tile(area, (len(n), 1)),
             contact_hull_perimeter_m=np.tile(perim, (len(n), 1)), sinkage_geometric_m=z10,
             sigma_sum_area_N=sigma, meta_grid_m=np.array([grid]),
             imu_t=imu_t, imu_roll_rad=np.zeros(len(imu_t)), imu_pitch_rad=np.full(len(imu_t), cfg["theta"]))
    res = {"events": events_for(cfg), "p3b": {"t_first_ready_s": (None if cfg["sgs"] else cfg["n_ready"] * 0.1),
                                              "creep_stop": {"t_final_s": 100.0}, "t_departure_s": 30.0,
                                              "weight_N": 376600.0},
           "t_end_s": cfg["duration"], "controller_meta": {"controller_tag": cfg["tag"]},
           "c2_setup": {"expect_controller": {"ok": True}}, "num_threads_chrono": 4,
           "hull_hook": {"requested": "fast", "effective": "fast", "dll_sha256": p2.HULL_DLL_SHA}}
    (d / "result.json").write_text(json.dumps(res), encoding="utf-8")


def make_harness(root: Path, lines: list[dict], name: str, row: str, group: str, variant: str, e: float,
                 shadow: bool, cfg: dict) -> None:
    n = np.arange(0, 1601)
    t10 = n * 0.1
    path = root / f"{name}.npz"
    np.savez(path, t=t10, stroke=stroke_series(n, cfg["s_peak"], cfg["n_peak"]),
             pad_sinkage_m=sink_curve(t10, cfg["z_rate"], cfg["n_loc"] * 0.1),
             load_read_N=np.tile([cfg["loads"][leg] for leg in p2.LEGS], (len(n), 1)),
             att_raw_rad=np.tile([cfg["phi"], cfg["theta"]], (len(n), 1)), c_hat_m=np.full(len(n), cfg["c_hat"]),
             c_hat_corner_m=np.tile([cfg["c_hat"]] * 4, (len(n), 1)), c_target_m=np.full(len(n), cfg["c_target"]))
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    tag = p2.CTRL_TAG_VB if variant == "VB" else p2.CTRL_TAG_V0
    lines.append({"b1": {"group": group, "row": row, "variant": variant, "e": e, "shadow": shadow},
                  "meta": {"controller_tag": tag}, "npz": path.name, "npz_sha256": sha,
                  "commands_sha256": cfg.get("cmd", f"cmd-{row}-{variant}-{e}"), "d1": {"key": f"K|{row}|{variant}|{e}"},
                  "events": events_for(cfg), "t_first_ready_s": (None if cfg["sgs"] else cfg["n_ready"] * 0.1)})


HARNESS = {"s_peak": 0.468, "z_rate": 0.00015}


def build(work: Path, prm: dict, row_over: dict | None = None, h_over: dict | None = None,
          skip_rows: tuple = (), drop_lines=None) -> tuple[Path, Path]:
    if work.exists():
        shutil.rmtree(work)
    batch = work / "batch"
    batch.mkdir(parents=True)
    cases = []
    for rid, (case, *_r) in p2.CHRONO_ROWS.items():
        if rid in skip_rows:
            continue
        cfg = copy.deepcopy(BASE)
        cfg["duration"] = p2.CHRONO_ROWS[rid][3]
        cfg.update((row_over or {}).get(rid, {}))
        make_chrono_row(batch, case, cfg, prm)
        cases.append({"case": case, "rc": cfg["rc"]})
    (batch / "batch.json").write_text(json.dumps({"cases": cases}), encoding="utf-8")
    hdir = work / "harness"
    hdir.mkdir()
    lines: list[dict] = []
    for rid in p2.R_SET:
        for variant in ("VB", "V0"):
            for e in (0.0, 0.002):
                cfg = copy.deepcopy(BASE)
                cfg.update(HARNESS)
                cfg.update((h_over or {}).get(("H-P", rid), {}))
                make_harness(hdir, lines, f"hp_{rid}_{variant}_{e}", rid, "H-P", variant, e, True, cfg)
    for variant in ("VB", "V0"):
        for e in (0.0, 0.002):
            cfg = copy.deepcopy(BASE)
            cfg.update(HARNESS)
            make_harness(hdir, lines, f"hw_{variant}_{e}", "C6", "H-W", variant, e, True, cfg)
    for rid in ("C1", "C5"):
        for variant in ("VB", "V0"):
            cfg = copy.deepcopy(BASE)
            cfg.update(HARNESS)
            cfg.update((h_over or {}).get(("H-M0", rid, variant), {}))
            make_harness(hdir, lines, f"hm0_{rid}_{variant}", rid, "H-M0", variant, 0.0, True, cfg)
    for rid in p2.CORE:
        cfg = copy.deepcopy(BASE)
        cfg.update(HARNESS)
        cfg.update((h_over or {}).get(("H-SH0", rid), {}))
        make_harness(hdir, lines, f"hsh0_{rid}", rid, "H-SH0", "VB", 0.0, False, cfg)
    if drop_lines:
        lines = [ln for ln in lines if not drop_lines(ln)]
    hj = hdir / "b1_H.jsonl"
    hj.write_text("".join(json.dumps(ln) + "\n" for ln in lines), encoding="utf-8")
    return batch, hj


def run_tool(repo: Path, work: Path, batch: Path, hj: Path, p7: Path | None = None) -> tuple[int, dict]:
    out = work / "out.json"
    argv = ["--repo", str(repo), "--batch", str(batch), "--harness-jsonl", str(hj), "--out", str(out)]
    if p7:
        argv += ["--p7-ref", str(p7)]
    code = p2.main(argv)
    return code, (json.loads(out.read_text(encoding="utf-8")) if out.exists() and code in (0, 1) else {})


# ----------------------------------------------------------------------------- checks

def unit_checks(prm: dict) -> None:
    check("cyc rounding", p2.cyc(39.99999999) == 400 and p2.cyc(0.30000000000000004) == 3)
    check("le at threshold", p2.le(0.003 + 0.5e-9, 0.003) and not p2.le(0.003 + 2e-9, 0.003))
    check("gt beyond threshold", p2.gt(0.005 + 2e-9, 0.005) and not p2.gt(0.005 + 0.5e-9, 0.005))
    check("ge within tol", p2.ge(0.020 - 0.5e-9, 0.020) and not p2.ge(0.020 - 2e-9, 0.020))
    check("dc class 0 at 3 mm", p2.classify_dc(0.003, 0.003) == "0")
    check("dc class + beyond", p2.classify_dc(0.003 + 2e-9, 0.004) == "+")
    check("dc class - beyond", p2.classify_dc(-0.004, -0.003 - 2e-9) == "-")
    check("dc class straddle", p2.classify_dc(-0.004, 0.001) == "?" and p2.classify_dc(0.002, 0.004) == "?")
    pad = prm["pad"]["RL"]
    a, b = pad["A"], pad["b_poly"]
    check("f = 1 at full contact", close(p2.grid_factor(a / 1e-4, 0.01, a, 2 * a / b, pad, prm), 1.0, 1e-12))
    f = p2.grid_factor(0.9 * a / 1e-4, 0.01, a, 2 * a / b, pad, prm)
    check("f = ratio^(-1/n)", close(f, 0.9 ** -5, 1e-9), f"{f}")
    k = prm["kc"] / b + prm["kphi"]
    z = 0.12
    ok, ratio, r = p2.grid_validity(0.95 * a / 1e-4, 0.01, a, 2 * a / b, 0.95 * a * k * z ** 0.2, z, pad, prm)
    check("validity band edge 0.95 inclusive", ok and close(ratio, 0.95, 1e-12) and close(r, 0.0, 1e-12))
    ok2, _, _ = p2.grid_validity(0.9499 * a / 1e-4, 0.01, a, 2 * a / b, 0.9499 * a * k * z ** 0.2, z, pad, prm)
    check("validity below band fails", not ok2)
    sig = a * k * z ** 0.2
    ok3, _, r3 = p2.grid_validity(a / 1e-4, 0.01, a, 2 * a / b, sig / (1 - 0.005 / 0.2), z, pad, prm)
    check("validity r_sigma 0.005 inclusive", ok3 and close(r3, 0.005, 1e-12), f"{r3}")
    ok4, _, _ = p2.grid_validity(a / 1e-4, 0.01, a, 2 * a / b, sig / (1 - 0.0051 / 0.2), z, pad, prm)
    check("validity r_sigma above fails", not ok4)
    pts = [(2.0, 1.0), (2.0, -1.0), (-2.5, 1.2), (-2.5, -1.2)]
    vals = [0.01 + 0.002 * y - 0.003 * x for x, y in pts]
    got = p2.plane_fit_at(pts, vals, [(1.8, 1.3), (-1.8, -1.3)])
    check("plane fit exact", close(got[0], 0.01 + 0.002 * 1.3 - 0.003 * 1.8, 1e-12)
          and close(got[1], 0.01 - 0.002 * 1.3 + 0.003 * 1.8, 1e-12))
    check("P-D increment", close(p2.pd_increment(2e-27, 1e5, 1e4), 2e-27 * (1.1e5 ** 5 - 1e5 ** 5), 1e-15))
    check("P-D negative W uses 0", close(p2.pd_increment(2e-27, 1e5, -5e3), 0.0, 1e-18))
    rs = p2.RunSeries()
    rs.events = [(39.0, "INFO_LOC_FLAT_SOIL_MARGIN:80"), (40.0, "INFO_LOC_CLEARANCE_MARGIN:50"),
                 (41.0, "INFO_LOC_CLEARANCE_MARGIN:90")]
    m, src = p2.margin_at(rs, p2.DEFAULT_KEYMAP, 400)
    check("m_L last event up to n_L", close(m, 0.0, 1e-15) and src == "E3c10", f"{m} {src}")
    m2, src2 = p2.margin_at(rs, p2.DEFAULT_KEYMAP, 395)
    check("m_L R4c30 before", close(m2, 0.03, 1e-15) and src2 == "R4c30")
    rs.events = []
    check("m_L none -> 0", p2.margin_at(rs, p2.DEFAULT_KEYMAP, 400) == (0.0, "none"))
    y = p2.parse_block_yaml(["a:", "  b: 1  # c", "  c: [1, 2]", "  d:", "    - [1, 2]", "    - [3, 4]",
                             "  e: \"x # y\"", "f: 2"])
    check("yaml reader", y == {"a": {"b": 1, "c": [1, 2], "d": [[1, 2], [3, 4]], "e": "x # y"}, "f": 2}, str(y))


def m12_and_safety_checks(prm: dict) -> None:
    km = p2.DEFAULT_KEYMAP
    rs = p2.RunSeries()
    rs.n = np.arange(0, 601)
    rs.index = p2._index(rs.n)
    rs.rc_index = rs.index
    rs.rc["rc_chat"] = np.full(len(rs.n), 0.025)
    cp = np.array([0.03, 0.04, 0.05, 0.06])
    plane = np.tile(cp, (len(rs.n), 1))
    plane[400:] += 0.02
    t_imu = np.round(np.arange(0, 6001) * 0.01, 6)
    rs.imu = (t_imu, np.zeros(len(t_imu)), np.full(len(t_imu), 0.01))
    rs.events = [(40.0, "crawler_liftoff_confirmed"), (50.0, "crawler_liftoff_confirmed")]
    rs.m12 = {"m12_corner_plane": plane, "m12_settle_att": np.array([0.0, 0.01]),
              "m12_loc_tP": np.array([39.0, 49.0]), "m12_loc_path": np.array(["1", "3"])}
    rec = p2.m12_records(rs, {}, prm, km)
    check("M-12 path 1 plan A", rec is not None and close(rec[0]["c_hat_A"], 0.02, 1e-12)
          and close(rec[0]["d"], 0.005, 1e-12), json.dumps(rec, default=str))
    check("M-12 path 3 b = 0", rec is not None and close(rec[1]["c_hat_A"], 0.05, 1e-12))
    # tilt step inside the window changes plan A through rho_rel (front corners rise)
    pitch = np.full(len(t_imu), 0.01)
    pitch[(t_imu >= 38.5) & (t_imu <= 39.5)] = 0.012
    rs.imu = (t_imu, np.zeros(len(t_imu)), pitch)
    rec2 = p2.m12_records(rs, {}, prm, km)
    order = km["corner_order"]
    xy = [prm["corners"][c] for c in order]
    rho = [-x * 0.002 for x, _ in xy]
    rel = [r - min(rho) for r in rho]
    b = [max(cp[k] - rel[k], 0.0) for k in range(4)]
    want = min(cp[k] + 0.02 - b[k] for k in range(4))
    check("M-12 centred window tilt", rec2 is not None and close(rec2[0]["c_hat_A"], want, 1e-12),
          f"{rec2[0]['c_hat_A'] if rec2 else None} vs {want}")
    # T-8: 100 consecutive zero-force samples after t_L1 flag the leg, 99 do not
    rs8 = p2.RunSeries()
    rs8.t_sink = np.round(np.arange(0, 2001) * 1e-3, 6)
    force = np.full((len(rs8.t_sink), 4), 1e4)
    force[1200:1300, 0] = 0.0
    force[1200:1299, 1] = 0.0
    rs8.leg_contact = force
    out = p2.safety(rs8, {"fault_stroke_end": False, "n_L1": 10}, km)
    check("T-8 100 samples", out["leg_liftoff"] == ["FL"], str(out))
    rs8.crawler_N = np.zeros(len(rs8.t_sink))
    rs8.crawler_N[1500] = 0.01 * 1e5
    rs8.t_dep, rs8.weight = 1.0, 1e5
    out = p2.safety(rs8, {"fault_stroke_end": False, "n_L1": 10}, km)
    check("T-9 crawler re-touch at 0.01 W", out["crawler_retouch"] is True)


def yaml_text_checks(repo: Path, prm: dict) -> None:
    text = (repo / "02_params" / "rexome33.yaml").read_text(encoding="utf-8")
    check("YAML FL pad xy (text)", "pad_bottom_center_retracted_m: [2.2938, 1.3238," in text
          and prm["pad"]["FL"]["xy"] == [2.2938, 1.3238])
    check("YAML RR pad xy (text)", "pad_bottom_center_retracted_m: [-2.556, -1.2429," in text
          and prm["pad"]["RR"]["xy"] == [-2.556, -1.2429])
    check("YAML rear pad area", close(prm["pad"]["RL"]["A"], 0.0607, 1e-12) and close(prm["pad"]["RL"]["b_poly"],
                                                                                         0.130578967, 1e-12))
    check("YAML top static FL", close(prm["static"]["top"]["FL"], 118099.1, 1e-9))
    check("soil J2", prm["kc"] == 16430.0 and prm["kphi"] == 1724690.0 and prm["n"] == 0.2)
    check("crawler corners", prm["corners"]["RR"] == (-1.84, -1.366) and prm["corners"]["FL"] == (1.844, 1.366))


def e2e_checks(repo: Path, work: Path, prm: dict) -> None:
    batch, hj = build(work / "base", prm)
    p7 = work / "p7.jsonl"
    p7.write_text(json.dumps({"s2d": {"candidate": "P0"}, "d1": {"key": "K|C1|VB|0.0"},
                              "commands_sha256": "cmd-C1-VB-0.0"}) + "\n" +
                  json.dumps({"s2d": {"candidate": "P1"}, "d1": {"key": "K|C2|VB|0.0"},
                              "commands_sha256": "zzz"}) + "\n", encoding="utf-8")
    code, out = run_tool(repo, work / "base", batch, hj, p7)
    check("e2e exit 0", code == 0, str(code))
    check("e2e bundle COMPLETE", out.get("bundle") == "COMPLETE")
    r1 = out["rows"]["C1"]
    m = r1["m"]
    check("t_L / t_R / t_max / t_e periods", (m["n_L"], m["n_R"], m["n_max"], m["n_e"]) == (400, 800, 700, 800))
    check("b* = FL, g", m["b_star"] == "FL" and close(m["g"], 0.6828 - 0.47, 1e-12))
    check("dz_post on t_e window", close(m["dz_post"]["FL"], 0.0002 * 40, 1e-9))
    check("dz t_max record", close(m["dz_L_max"]["FL"], 0.0002 * 30, 1e-9))
    check("dos", close(m["dos"]["FL"], 1e-3, 1e-12))
    gm = r1["gm"]
    check("grid f = 1 valid", gm["max"]["FL"]["valid"] and close(gm["max"]["FL"]["f"], 1.0, 1e-9))
    g = out["grades"]
    check("D-a ZA-1 raw and corr", g["D-a"]["grade"] == "ZA-1" and g["D-a"]["raw"] == "ZA-1"
          and g["D-a"]["corr"] == "ZA-1")
    check("D-a Z values", close(g["D-a"]["Z_ch"], 0.008, 1e-9) and close(g["D-a"]["Z_hn"], 0.006, 1e-9))
    check("D-b OS-FINAL", g["D-b"]["grade"] == "OS-FINAL" and close(g["D-b"]["O"], 1e-3, 1e-12))
    check("D-c H-OK, delta 2 mm", g["D-c"]["grade"] == "H-OK"
          and close(g["D-c"]["detail"]["C1"]["delta_raw"], 0.002, 1e-12))
    ea = 0.47 - (0.44 + 2.2938 * 0.01 + 0.01)
    e = r1["pred"]["e"]
    check("P-A error", close(e["P-A"], ea, 1e-9), f"{e['P-A']} vs {ea}")
    c = out["constants"]
    check("kappa front/rear", close(c["kappa"]["front"], 0.006 / 1e4, 1e-12) and close(c["kappa"]["rear"],
                                                                                     0.006 / 1e4, 1e-12))
    check("delta_allow", close(c["delta_allow"], 1e-3, 1e-12))
    check("kappa ratio 1", close(c["kappa_ratio"]["front"], 1.0, 1e-12))
    check("P-B error", close(e["P-B"], ea - 0.006, 1e-9))
    check("P-C error", close(e["P-C"], ea - 0.006 - 1e-3, 1e-9))
    loads, static = BASE["loads"], prm["static"]["bottom"]
    den = {leg: static[leg] ** 5 - loads[leg] ** 5 for leg in p2.LEGS}
    c_t = {"front": 0.006 / min(den["FL"], den["FR"]), "rear": 0.006 / min(den["RL"], den["RR"])}
    dzh = {leg: c_t[prm["pad"][leg]["type"]] * den[leg] for leg in p2.LEGS}
    check("C_type max per pad type", close(c["C_type"]["front"], c_t["front"], 1e-30)
          and close(c["C_type"]["rear"], c_t["rear"], 1e-30))
    check("P-D error", close(e["P-D"], ea - dzh["FL"], 1e-9), f"{e['P-D']} vs {ea - dzh['FL']}")
    xy = [tuple(prm["pad"][leg]["xy"]) for leg in p2.LEGS]
    amat = np.array([[1.0, yy, -xx] for xx, yy in xy])
    coef = np.linalg.lstsq(amat, np.array([dzh[leg] for leg in p2.LEGS]), rcond=None)[0]
    zc = {cn: coef[0] + coef[1] * yy - coef[2] * xx for cn, (xx, yy) in prm["corners"].items()}
    terms = {cn: 0.07 + prm["corners"][cn][0] * 0.01 + zc[cn] for cn in prm["corners"]}
    kmin = min(terms, key=lambda cn: (terms[cn], ["RR", "RL", "FR", "FL"].index(cn)))
    eg = 0.47 - (0.44 + 2.2938 * 0.01 + max(0.08 - terms[kmin], 0.0) + dzh["FL"])
    check("P-G k* (rear corner)", r1["pred"]["rec"]["k_star"] == kmin and kmin in ("RR", "RL"), str(kmin))
    check("P-G error", close(e["P-G"], eg, 1e-9), f"{e['P-G']} vs {eg}")
    check("D-d PRED-P-A", g["D-d"]["grade"] == "PRED-P-A" and close(g["D-d"]["E"]["P-A"], abs(ea), 1e-9))
    gtil = (0.6828 - 0.47) - 0.096 * (1 - 1 / 1.05)
    check("D-e NEED-RECHECK g~", g["D-e"]["grade"] == "NEED-RECHECK"
          and close(g["D-e"]["rows"]["C1"]["g_tilde"], gtil, 1e-9))
    check("D-f FUP-NA (no SGS)", g["D-f"]["grade"] == "FUP-NA")
    check("D-g W-OK", g["D-g"]["grade"] == "W-OK")
    check("D-h K-SAME with NA keys", g["D-h"]["grade"] == "K-SAME" and g["D-h"]["same"] == ["K|C1|VB|0.0"])
    check("shadow hash ok", out["shadow_hash_ok"] is True)
    h = r1["h_rec"]
    check("eps = c_hat(t_R) - (c*+m_L)", close(h["eps"], 0.07 - 0.08, 1e-12))
    check("m12 NA without inputs", r1["m12"] is None)
    check("no safety note", out["safety_notes"] == {})


def variant_checks(repo: Path, work: Path, prm: dict) -> None:
    # PARTIAL (C3 missing)
    batch, hj = build(work / "partial", prm, skip_rows=("C3",))
    code, out = run_tool(repo, work / "partial", batch, hj)
    check("PARTIAL bundle", code == 0 and out["bundle"] == "PARTIAL" and out["rows"]["C3"]["status"] == "MISSING")
    check("PARTIAL flag on D-a/D-b/D-c/D-d", all("PARTIAL" in out["grades"][k]["flags"]
                                                for k in ("D-a", "D-b", "D-c", "D-d")))
    # UNDETERMINED (core C2 rc 1)
    batch, hj = build(work / "und", prm, row_over={"C2": {"rc": 1}})
    code, out = run_tool(repo, work / "und", batch, hj)
    check("UNDETERMINED exit 1", code == 1 and out["bundle"] == "UNDETERMINED" and out["grades"] == {})
    # MISSING_START and INVALID
    batch, hj = build(work / "rej", prm, row_over={"C3": {"events_extra": [{"t": 5.0, "name": "REJ_TARGET"}]},
                                                   "C6": {"tag": "final_C4G2_P3"}})
    code, out = run_tool(repo, work / "rej", batch, hj)
    check("MISSING_START on REJ_", out["rows"]["C3"]["status"] == "MISSING_START")
    check("INVALID on tag", out["rows"]["C6"]["status"] == "INVALID")
    check("D-g W-NA when C6 invalid", out["grades"]["D-g"]["grade"] == "W-NA")
    # harness VB e0 missing for C1 -> UNDETERMINED; npz sha mismatch -> invalid line
    batch, hj = build(work / "hmiss", prm, drop_lines=lambda ln: ln["b1"]["group"] == "H-P"
                      and ln["b1"]["row"] == "C1" and ln["b1"]["variant"] == "VB" and ln["b1"]["e"] == 0.0)
    code, out = run_tool(repo, work / "hmiss", batch, hj)
    check("UNDETERMINED without H-P VB e0", code == 1 and out["bundle"] == "UNDETERMINED")
    batch, hj = build(work / "hsha", prm)
    lines = [json.loads(x) for x in hj.read_text(encoding="utf-8").splitlines()]
    lines[0]["npz_sha256"] = "0" * 64
    hj.write_text("".join(json.dumps(ln) + "\n" for ln in lines), encoding="utf-8")
    code, out = run_tool(repo, work / "hsha", batch, hj)
    check("harness sha mismatch -> invalid line", out["harness_invalid"].get("0") == "npz sha mismatch")
    # shadow hash mismatch
    batch, hj = build(work / "shad", prm, h_over={("H-SH0", "C2"): {"cmd": "other"}})
    code, out = run_tool(repo, work / "shad", batch, hj)
    check("shadow hash mismatch flagged", out["shadow_hash_ok"] is False)
    # D-f with C5 SGS: one H-M0 pair has R4c30 -> dropped -> one pair SGS -> FUP-OUT one pair
    r4 = [{"t": 40.0, "name": "INFO_LOC_FLAT_SOIL_MARGIN:80"}]
    batch, hj = build(work / "df", prm, row_over={"C5": {"sgs": True}},
                      h_over={("H-M0", "C5", "VB"): {"sgs": True}, ("H-M0", "C5", "V0"): {"events_extra": r4}})
    code, out = run_tool(repo, work / "df", batch, hj)
    check("D-f FUP-OUT one pair", out["grades"]["D-f"]["grade"] == "FUP-OUT"
          and out["grades"]["D-f"]["flags"] == ["one pair"], json.dumps(out["grades"]["D-f"]))
    check("SGS row dos NA and D-b counts", out["rows"]["C5"]["m"]["dos"] is None
          and "C5" in out["grades"]["D-b"]["na_rows"])
    batch, hj = build(work / "df2", prm, row_over={"C5": {"sgs": True}})
    code, out = run_tool(repo, work / "df2", batch, hj)
    check("D-f FUP-IN when a pair READY", out["grades"]["D-f"]["grade"] == "FUP-IN")
    # D-a raw ZA-2 by 3 mm + 2e-9 vs ZA-1 at exactly 3 mm (T-1)
    batch, hj = build(work / "da", prm, row_over={r: {"z_rate": 0.000225} for r in p2.R_SET})
    code, out = run_tool(repo, work / "da", batch, hj)
    check("D-a at 3 mm is ZA-1", out["grades"]["D-a"]["grade"] == "ZA-1",
          f"{out['grades']['D-a'].get('Z_ch')} {out['grades']['D-a'].get('Z_hn')}")
    batch, hj = build(work / "da2", prm, row_over={r: {"z_rate": 0.000226} for r in p2.R_SET})
    code, out = run_tool(repo, work / "da2", batch, hj)
    check("D-a beyond 3 mm is ZA-2 with correction", out["grades"]["D-a"]["grade"] == "ZA-2"
          and close(out["grades"]["D-a"]["correction_m"], 0.00904 - 0.006, 1e-9))
    # grid invalid (N_h 0.9 of full) -> corr NA rows, D-c substitute range
    batch, hj = build(work / "gi", prm, row_over={r: {"nh_scale": 0.9} for r in p2.R_SET})
    code, out = run_tool(repo, work / "gi", batch, hj)
    da, dc = out["grades"]["D-a"], out["grades"]["D-c"]
    check("D-a corr NA when records invalid", da["corr"] is None and "no grid record" in da["flags"])
    check("D-c substitute range used", dc["detail"]["C1"]["substitute"] is True)
    # T-14 mismatch on C2 -> excluded from D-d
    batch, hj = build(work / "t14", prm, row_over={"C2": {"c_target": 0.09}})
    code, out = run_tool(repo, work / "t14", batch, hj)
    check("T-14 mismatch row excluded", out["grades"]["D-d"]["excluded_t14"] == ["C2"]
          and "C2" not in out["grades"]["D-d"]["rows"])
    # D-d PRED-FAIL when error > 10 mm
    batch, hj = build(work / "pf", prm, row_over={r: {"c_hat": 0.03} for r in p2.R_SET})
    code, out = run_tool(repo, work / "pf", batch, hj)
    check("D-d PRED-FAIL beyond 10 mm", out["grades"]["D-d"]["grade"] == "PRED-FAIL",
          json.dumps(out["grades"]["D-d"]["E"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--work", required=True)
    args = ap.parse_args()
    repo, work = Path(args.repo), Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    prm = p2.load_params(repo)
    unit_checks(prm)
    yaml_text_checks(repo, prm)
    m12_and_safety_checks(prm)
    e2e_checks(repo, work, prm)
    variant_checks(repo, work, prm)
    failed = [(n, i) for n, ok, i in CHECKS if not ok]
    for n, ok, i in CHECKS:
        print(("PASS " if ok else "FAIL ") + n + (f"  [{i}]" if (i and not ok) else ""))
    print(json.dumps({"status": "ok" if not failed else "fail", "checks": len(CHECKS), "failed": len(failed)}))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
