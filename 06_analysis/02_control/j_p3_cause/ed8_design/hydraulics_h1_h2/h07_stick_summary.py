"""h07: stuck-seal oil after the K1 mid read, head-check fill and mid-read travel by setting,
probe round and leg; paired probe arms a2 ((i-b) on) against c2 ((i-b) and witness off), same
plant / key / round / leg (read only, from h03_rows.csv).

Output: h07_out.txt, h07_table.csv
"""
import csv
import os
from collections import defaultdict

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
rows = [r for r in csv.DictReader(open(os.path.join(OUT, "h03_rows.csv"), encoding="utf-8"))
        if r["reversed"] == "False"]


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


COLS = ("x_open_mm", "ds_mid_mm", "slope_mid_MN_m", "slope_win1_MN_m", "stick_after_mid_mm",
        "Kpist_proxy_MN_m", "net_stroke_after_mm")
lines, table = [], []


def stats(sub, label):
    out = {"group": label, "n": len(sub)}
    for c in COLS:
        v = np.array([f(r[c]) for r in sub])
        v = v[np.isfinite(v)]
        out[c + "_med"] = round(float(np.median(v)), 3) if len(v) else None
        out[c + "_p90"] = round(float(np.percentile(v, 90)), 3) if len(v) else None
    v = np.array([f(r["stick_after_mid_mm"]) for r in sub])
    out["share_stick_after_mid>0"] = round(float(np.mean(v > 0)), 3) if len(v) else None
    out["warn_round_share"] = round(float(np.mean([r["round_warn_ratio"] != "" for r in sub])), 3)
    return out


order = defaultdict(dict)
for r in rows:
    k = (r["src"], r["setting"], r["key"], r["round"])
    order[k].setdefault(r["leg"], f(r["t_start_s"]))
for r in rows:
    k = (r["src"], r["setting"], r["key"], r["round"])
    legs = sorted(order[k], key=lambda x: order[k][x])
    r["probe_pos"] = str(legs.index(r["leg"]) + 1)

groups = defaultdict(list)
for r in rows:
    groups[(r["src"], r["setting"])].append(r)
    groups[(r["src"], r["setting"], "round" + r["round"])].append(r)
    groups[(r["src"], r["setting"], "pos" + r["probe_pos"])].append(r)
    groups[(r["src"], r["setting"], "last" + r["last_sign"])].append(r)
for key in sorted(groups):
    st = stats(groups[key], "|".join(key))
    table.append(st)
with open(os.path.join(OUT, "h07_table.csv"), "w", newline="", encoding="utf-8") as fo:
    w = csv.DictWriter(fo, fieldnames=list(table[0].keys()), lineterminator="\n")
    w.writeheader()
    w.writerows(table)
SHOW = ("sens|VBMh05", "sens|VBMfast", "sens|VBMb069", "sens|VBMd15", "sens|VBMc005", "sens|VBMc04",
        "sens|VBMh15", "sens|VBMslow", "j9main|VBM", "probe|P7-M-a2", "probe|P7-M-c2",
        "probe|P7-Mslow-a2", "probe|P7-Mslow-c2", "probe|P7-Mfast-a2", "probe|P7-Mfast-c2",
        "probe|P7-L-a2", "probe|P7-L-c2")
lines.append("group | n | x_open med | ds_mid med | slope_win1 med/p90 | stick_after med/p90 |"
             " share stick>0 | Kpist med | warn share")
for st in table:
    g = st["group"]
    if not any(g == s or g.startswith(s + "|") for s in SHOW):
        continue
    lines.append(f"{g} | {st['n']} | {st['x_open_mm_med']} | {st['ds_mid_mm_med']} | "
                 f"{st['slope_win1_MN_m_med']}/{st['slope_win1_MN_m_p90']} | "
                 f"{st['stick_after_mid_mm_med']}/{st['stick_after_mid_mm_p90']} | "
                 f"{st['share_stick_after_mid>0']} | {st['Kpist_proxy_MN_m_med']} | "
                 f"{st['warn_round_share']}")
# paired a2 - c2
lines.append("== paired probe arms (a2 - c2), same plant, key, round, leg")
idx = {(r["src"], r["setting"], r["key"], r["round"], r["leg"]): r for r in rows}
for plant in ("M", "Mslow", "Mfast", "Mc005", "Mc04", "L"):
    for c in ("x_open_mm", "ds_mid_mm", "slope_win1_MN_m", "p_h_start_bar", "p_r_start_bar",
              "dF_first_kN", "dF_half_kN", "net_stroke_after_mm"):
        for rd in ("1", "2"):
            dv = []
            for (src, s, key, rnd, leg), r in idx.items():
                if src != "probe" or s != f"P7-{plant}-a2" or rnd != rd:
                    continue
                o = idx.get((src, f"P7-{plant}-c2", key, rnd, leg))
                if o is None:
                    continue
                a, b = f(r[c]), f(o[c])
                if np.isfinite(a) and np.isfinite(b):
                    dv.append(a - b)
            if dv:
                dv = np.array(dv)
                lines.append(f"  {plant} round {rd} d {c}: n {len(dv)} med {np.median(dv):.3f}"
                             f" p10 {np.percentile(dv, 10):.3f} p90 {np.percentile(dv, 90):.3f}")
# F_s class of the key (round 1 is before the event; the case F_s holds for all legs there)
lines.append("== slope of the first K1-window interval by setting and key F_s tag (windows of legs"
             " 2-4 of a round, extend line filled from empty)")
for s in ("sens|VBMh05", "sens|VBMfast", "j9main|VBM", "sens|VBMd15", "sens|VBMh15",
          "sens|VBMslow", "probe|P7-M-a2", "probe|P7-M-c2", "probe|P7-Mslow-a2",
          "probe|P7-Mslow-c2"):
    src, setting = s.split("|")
    for tag in ("Fs0.0", "Fs4.0", "Fs8.0", "noTwin"):
        sub = [r for r in rows if r["src"] == src and r["setting"] == setting
               and (tag in r["key"] if tag != "noTwin" else "Fs" not in r["key"])
               and r["x_open_mm"] not in ("", None)]
        if not sub:
            continue
        sw = np.array([f(r["slope_win1_MN_m"]) for r in sub])
        sw = sw[np.isfinite(sw)]
        xo = np.array([f(r["x_open_mm"]) for r in sub])
        dm = np.array([f(r["ds_mid_mm"]) for r in sub])
        wr = np.mean([r["round_warn_ratio"] != "" for r in sub])
        lines.append(f"  {s} {tag}: n {len(sub)} x_open med {np.median(xo):.3f} ds_mid med "
                     f"{np.median(dm):.3f} slope_win1 med {np.median(sw):.2f} p75 "
                     f"{np.percentile(sw, 75):.2f} warn-round share {wr:.2f}")
with open(os.path.join(OUT, "h07_out.txt"), "w", encoding="utf-8", newline="\n") as fo:
    fo.write("\n".join(lines) + "\n")
print(len(lines))
