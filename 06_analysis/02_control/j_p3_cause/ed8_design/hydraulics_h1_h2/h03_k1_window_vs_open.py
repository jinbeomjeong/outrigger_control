"""h03: K1 window of every extend-first probe leg against the plant's extend head-check opening
(edition 7 run 8a2a52ce, sensitivity and j9main; read only).

Per probe phase and leg (first block of >= 5 positive commands = trapezoid first move, as a02):
  i0 first command read, imid = i0 + n_pos // 2 (K1 mid read, ``_step_trapezoid``), iext last read
  before the first negative command (``_end_stage`` FIRST_MOVE).
  The plant's extend head-check opening is the first ``line_fill_gate.fills`` row with dir +1 of
  the leg whose open time lies in [t(i0) - 0.05, t(iext) + 0.05] (sub-step time, x at opening).
  Also: the leg's last nonzero command sign before i0 (seal friction state), head / rod reads,
  motor (oil) stroke moves, read force moves (p_h A_h - p_r A_ann), true force moves.
  The (i-b) record of the round (``probe_d6_record.rounds``) of the leg: target reached, extra.
  The stiffness warning of the round: the WARN event of the line in [round start, round end + 1 s].

Output: h03_rows.csv (one row per leg window), h03_summary.json (per setting).
Usage: python -I -B h03_k1_window_vs_open.py
"""
import csv
import json
import math
import os
from collections import defaultdict

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
J9 = r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\8a2a52ce"
PROBE = (r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\6bfb2560"
         r"\ed7_probe_a1")
SOURCES = {
    "sens": (os.path.join(J9, r"sens_a1\sens.jsonl"), os.path.join(J9, r"sens_a1\sens_t4h")),
    "j9main": (os.path.join(J9, r"j9main_a1\j9_main.jsonl"),
               os.path.join(J9, r"j9main_a1\j9_main_t4h")),
    "probe": (os.path.join(PROBE, "ed7_probe.jsonl"), os.path.join(PROBE, "ed7_probe_t4h")),
}
A_H = np.array([math.pi / 4 * 0.13 ** 2] * 2 + [math.pi / 4 * 0.11 ** 2] * 2)
A_ROD = np.array([math.pi / 4 * 0.11 ** 2] * 2 + [math.pi / 4 * 0.09 ** 2] * 2)
A_ANN = A_H - A_ROD
LEGS = ("FL", "FR", "RL", "RR")
STIFF = "WARN_PROBE_STIFFNESS_OUT_OF_RANGE"
MIN_BLOCK = 5


def job_key(job):
    tw = job.get("twin") or {}
    parts = [str(job.get("case")), f"e{job.get('eps', 0.0)}", f"o{job.get('offset_s', 0.0)}"]
    if tw:
        parts += [str(tw.get("level")), str(tw.get("leg")), f"Fs{tw.get('fs_kN')}"]
    return "|".join(parts)


def leg_windows(z):
    t = z["t_s"]
    ph = np.char.lower(z["phase"].astype(str))
    cmd = z["command_m_s"]
    out = []
    n = len(t)
    i = 0
    rnd = 0
    while i < n:
        if ph[i] != "probe":
            i += 1
            continue
        j = i
        while j < n and ph[j] == "probe":
            j += 1
        rnd += 1
        for leg in range(4):
            idx = [k for k in range(i, j) if abs(cmd[k, leg]) > 1e-9]
            if not idx:
                continue
            blocks = []
            for k in idx:
                sgn = 1 if cmd[k, leg] > 0 else -1
                if blocks and k == blocks[-1][1][-1] + 1 and blocks[-1][0] == sgn:
                    blocks[-1][1].append(k)
                else:
                    blocks.append((sgn, [k]))
            long_blocks = [b for b in blocks if len(b[1]) >= MIN_BLOCK]
            if not long_blocks:
                continue
            sgn, blk = long_blocks[0]
            if sgn < 0:
                out.append({"round": rnd, "leg": leg, "reversed": True, "i0": blk[0],
                            "phase_start": i, "phase_end": j - 1})
                continue
            i0 = blk[0]
            npos = len(blk)
            neg = [k for k in range(blk[-1], j) if cmd[k, leg] < -1e-9]
            iext = (neg[0] - 1) if neg else blk[-1] + 1
            iret_end = neg[-1] if neg else iext
            out.append({"round": rnd, "leg": leg, "reversed": False, "i0": i0, "npos": npos,
                        "imid": i0 + npos // 2, "iext": iext, "iret_end": iret_end,
                        "phase_start": i, "phase_end": j - 1})
        i = j
    return out


def last_sign_before(cmd, i0, leg):
    for k in range(i0 - 1, -1, -1):
        if abs(cmd[k, leg]) > 1e-9:
            return (1 if cmd[k, leg] > 0 else -1), k
    return 0, None


def main():
    rows = []
    for src, (jsonl, t4h_dir) in SOURCES.items():
        with open(jsonl, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                d = json.loads(ln)
                job = d.get("job", {})
                setting = job.get("setting")
                if not str(setting).startswith(("VBM", "LSM", "P7-")):
                    continue
                t4h = d.get("t4h_file")
                path = os.path.join(t4h_dir, os.path.basename(str(t4h))) if t4h else None
                if not path or not os.path.exists(path):
                    continue
                z = np.load(path, allow_pickle=False)
                t = z["t_s"]
                cmd = z["command_m_s"]
                head, rod = z["head_pressure_Pa"], z["rod_pressure_Pa"]
                force = head * A_H - rod * A_ANN
                stroke = z["motor_stroke_m"]
                tf = z["true_force_N"]
                locked = z["locked"]
                gate = z["jp3_gate_open"] if "jp3_gate_open" in z.files else np.zeros_like(locked)
                lfg = (d.get("hydraulics_record") or {}).get("line_fill_gate") or {}
                fills = lfg.get("fills") or []
                ext_fills = [r for r in fills if int(r[3]) == 1]
                ret_fills = [r for r in fills if int(r[3]) == -1]
                warns = [(float(tt), float(str(nm).split(":")[1])) for tt, nm in
                         (d.get("events") or []) if str(nm).startswith(STIFF)]
                d6 = (d.get("probe_d6_record") or {}).get("rounds") or []
                patch = (d.get("hydraulic_options") or {}).get("p1_patch") or {}
                d6s = (d.get("hydraulic_options") or {}).get("probe_d6_settings") or {}
                for w in leg_windows(z):
                    leg = w["leg"]
                    t_ph0, t_ph1 = float(t[w["phase_start"]]), float(t[w["phase_end"]])
                    wr = [r for tt, r in warns if t_ph0 - 0.05 <= tt <= t_ph1 + 1.0]
                    base = {"src": src, "setting": setting, "key": job_key(job),
                            "line_scale": patch.get("line_scale"),
                            "dead_scale": patch.get("dead_scale"),
                            "beta_GPa": (patch.get("bulk_modulus_Pa") or 0) / 1e9,
                            "ib": d6s.get("retract_position_target"),
                            "round": w["round"], "leg": LEGS[leg],
                            "round_warn_ratio": wr[0] if wr else None,
                            "reversed": w["reversed"]}
                    if w["reversed"]:
                        rows.append(base)
                        continue
                    i0, imid, iext = w["i0"], w["imid"], w["iext"]
                    if iext >= len(t) or w["iret_end"] >= len(t):
                        continue  # the line ends inside the probe (no full window)
                    t0, tm, te = float(t[i0]), float(t[imid]), float(t[iext])
                    fo = [r for r in ext_fills if int(r[2]) == leg
                          and t0 - 0.05 <= float(r[1]) <= te + 0.05]
                    t_open = float(fo[0][1]) if fo else None
                    x_open = float(fo[0][4]) if fo else None
                    p_a_open = float(fo[0][7]) if fo else None
                    p_b_open = float(fo[0][8]) if fo else None
                    unlock = next((k for k in range(i0, iext + 1) if not locked[k, leg]), None)
                    gopen = next((k for k in range(i0, iext + 1) if gate[k, leg]), None)
                    lsign, lk = last_sign_before(cmd, i0, leg)
                    # retract of this window: plant retract opening (fills dir -1) in the
                    # second move, and the (i-b) record of the leg near the retract
                    tr0 = te
                    tr1 = float(t[w["iret_end"]]) + 2.0
                    ro = [r for r in ret_fills if int(r[2]) == leg and tr0 - 0.05 <= float(r[1]) <= tr1]
                    d6r = [r for r in d6 if r.get("leg") == LEGS[leg]
                           and tr0 - 0.5 <= float(r.get("t_s", -1)) <= tr1 + 3.0]
                    d6r = d6r[0] if d6r else {}
                    s0 = float(stroke[i0 - 1, leg])
                    ds_mid = float(stroke[imid, leg]) - s0
                    ds_half = float(stroke[iext, leg] - stroke[imid, leg])
                    dF_half = float(force[iext, leg] - force[imid, leg])
                    dF_first = float(force[imid, leg] - force[i0 - 1, leg])
                    cmd_mid = float(np.sum(cmd[i0:imid, leg]) * 0.1)
                    k_mot = dF_half / ds_half if abs(ds_half) > 1e-6 else None

                    def slope(k, leg=leg):
                        ds_k = float(stroke[k, leg] - stroke[k - 1, leg])
                        if abs(ds_k) < 1e-6:
                            return None
                        return round(float(force[k, leg] - force[k - 1, leg]) / ds_k / 1e6, 2)

                    slope_mid = slope(imid)
                    slope_win1 = slope(imid + 1)
                    # oil delivered by the plant before the K1 mid read while the slope was
                    # still the stuck-seal oil column (> 20 MN/m) after the mid read
                    stick_after = 0.0
                    for k in range(imid + 1, iext + 1):
                        sk = slope(k)
                        if sk is None or sk <= 20.0:
                            break
                        stick_after += float(stroke[k, leg] - stroke[k - 1, leg])
                    # piston proxy: oil column stiffness k_h = beta A_h / (L0h + s), beta 1 GPa,
                    # L0h 0.05 m (harness kernel values ASSUMED for the proxy only)
                    k_h = 1.0e9 * A_H[leg] / (0.05 + s0)
                    ds_pist = ds_half - dF_half / k_h
                    k_pist = dF_half / ds_pist if abs(ds_pist) > 1e-6 else None
                    # end of the probe of this leg: net oil stroke change (start -> after retract)
                    iend = min(w["iret_end"] + 6, len(t) - 1)
                    rows.append({
                        **base,
                        "t_start_s": round(t0, 2), "t_mid_s": round(tm, 2), "t_ext_s": round(te, 2),
                        "cmd_to_mid_mm": round(cmd_mid * 1e3, 3),
                        "t_open_ext_s": None if t_open is None else round(t_open, 3),
                        "open_minus_mid_s": None if t_open is None else round(t_open - tm, 3),
                        "open_after_mid": None if t_open is None else bool(t_open > tm),
                        "x_open_mm": x_open, "p_a_open_bar": p_a_open, "p_b_open_bar": p_b_open,
                        "unlock_read_minus_mid": None if unlock is None else unlock - imid,
                        "gate_read_minus_mid": None if gopen is None else gopen - imid,
                        "last_sign": lsign,
                        "last_move_age_s": None if lk is None else round(t0 - float(t[lk]), 2),
                        "p_h_start_bar": round(float(head[i0 - 1, leg]) / 1e5, 2),
                        "p_r_start_bar": round(float(rod[i0 - 1, leg]) / 1e5, 2),
                        "s_start_mm": round(s0 * 1e3, 2),
                        "ds_mid_mm": round(ds_mid * 1e3, 3), "ds_half_mm": round(ds_half * 1e3, 3),
                        "dF_first_kN": round(dF_first / 1e3, 3), "dF_half_kN": round(dF_half / 1e3, 3),
                        "dFtrue_half_kN": round(float(tf[iext, leg] - tf[imid, leg]) / 1e3, 3),
                        "slope_mid_MN_m": slope_mid, "slope_win1_MN_m": slope_win1,
                        "stick_after_mid_mm": round(stick_after * 1e3, 3),
                        "Kmot_half_MN_m": None if k_mot is None else round(k_mot / 1e6, 3),
                        "Kpist_proxy_MN_m": None if k_pist is None else round(k_pist / 1e6, 3),
                        "ret_open": bool(ro), "ret_need_mm": float(ro[0][4]) if ro else None,
                        "net_stroke_after_mm": round(float(stroke[iend, leg] - s0) * 1e3, 3),
                        "ib_target_reached": d6r.get("retract_target_reached"),
                        "ib_extra_mm": None if d6r.get("retract_extra_m") is None
                        else round(float(d6r["retract_extra_m"]) * 1e3, 3),
                        "d6_witness_mm": None if d6r.get("retract_witness_m") is None
                        else round(float(d6r["retract_witness_m"]) * 1e3, 3),
                    })
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(os.path.join(OUT, "h03_rows.csv"), "w", newline="", encoding="utf-8") as f:
        wcsv = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        wcsv.writeheader()
        wcsv.writerows(rows)
    summ = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r["reversed"]:
            summ[(r["src"], r["setting"])]["reversed"] += 1
            continue
        s = summ[(r["src"], r["setting"])]
        s["windows"] += 1
        oam = r["open_after_mid"]
        s["open_after_mid" if oam else ("open_before_mid" if oam is False else "open_none")] += 1
        if r["round_warn_ratio"] is not None:
            s["windows_in_warn_round"] += 1
            if oam:
                s["warn_round_and_open_after_mid"] += 1
    js = {f"{a}:{b}": dict(v) for (a, b), v in sorted(summ.items())}
    with open(os.path.join(OUT, "h03_summary.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(js, f, indent=1)
    print(json.dumps(js, indent=1))


if __name__ == "__main__":
    main()
