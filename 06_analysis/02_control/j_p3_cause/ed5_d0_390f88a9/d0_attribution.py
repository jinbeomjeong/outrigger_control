"""D0 plant split (run 390f88a9): attribution tables against V0, stored VB and j9_main VBJ (read only).

Inputs
- D0 summary: j9_runs/390f88a9/d0_plant_split_a1/d0_summary.json (python-expert, branch d0-split 390f88a9)
- V0 / stored VB rows: 06_analysis/03_hydraulic/coupled/v5/main.jsonl
- j9_main VBJ rows: j9_runs/606f8713/j9main_a1/j9_main.jsonl (reproduction check of D0-1)

Conventions: negative feedback, T_s 0.1 s, d = 1; forces kN (E-3 = min_F_after_W), READY s.
F_min 9.415 kN; READY limit 100 s (soil rows S1, S5); event rows judged by J1..J5 against V0.
Outputs (this folder): d0_attribution.csv, d0_attribution.json, d0_fig_r12_min_force.png,
d0_fig_level_stall.png. control-expert, 2026-11-23 (analysis after the result, design input).
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

J = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause")
D0 = J / "j9_runs/390f88a9/d0_plant_split_a1/d0_summary.json"
V5 = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\main.jsonl")
J9 = J / "j9_runs/606f8713/j9main_a1/j9_main.jsonl"
OUT = Path(__file__).resolve().parent
F_MIN = 9.41458911
VARIANTS = {
    "D0-1": "VBJ (P1..P4, rev 6)",
    "D0-2": "VBJ - P1 (P2..P4)",
    "D0-3": "VB + P1 (rev 4)",
    "D0-8": "VBH + P1 (rev 6)",
    "D0-4": "VBJ, P1 volume 0.5",
    "D0-5": "VBJ, c_v 0.002",
    "D0-6": "VBJ, c_v 0.04",
    "D0-7": "VBJ, c_v 0.002 + volume 0.5",
}
KEYS = ["R12_o0.0", "R12_top-FL-Fs8-o0.0", "R12_bottom-FL-Fs4-o0.0", "R12_top-FR-Fs4-o0.0",
        "R15_o0.0", "R15_o0.05", "S5_e0.0", "S1_e0.003"]


def stem(job: dict) -> str:
    c = job["case"]
    tw = job.get("twin")
    if c.startswith(("R1", "R2", "R7")) and "offset_s" in job and job.get("offset_s") is not None:
        if tw:
            return f"{c}_{tw['level']}-{tw['leg']}-Fs{tw['fs_kN']:g}-o{job['offset_s']}"
        return f"{c}_o{job['offset_s']}"
    return f"{c}_e{job['eps']}"


def ref_rows(path: Path, setting: str) -> dict:
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            j = d["job"]
            if j.get("setting") != setting or j.get("decision"):
                continue
            k = stem(j)
            if k not in KEYS:
                continue
            eo = d.get("event_output") or {}
            mfw = eo.get("min_F_after_W_kN") or {}
            out[k] = {"final_phase": d.get("final_phase"),
                      "t_ready": (d.get("values") or {}).get("times", {}).get("t_first_ready_s"),
                      "minF": min(mfw.values()) if mfw else None, "event_pass": eo.get("pass"),
                      "t_back": eo.get("t_ready_back_s"), "sha": d.get("commands_sha256")}
    return out


def verdict(row: dict, v0: dict) -> str:
    """Item failures against V0 (v5 criteria 3: J2, J3, J4, J5 shown; J1 gates follow J2/J4)."""
    k = row["key"]
    fails = []
    if k.startswith(("R12", "R15")):
        if v0["minF"] is not None and v0["minF"] >= F_MIN and (row["min_force_kN"] < F_MIN):
            fails.append("J2")
        if v0["final_phase"] == "ready" and row["final_phase"] != "ready":
            fails.append("J4")
        if v0["t_back"] is not None and row["J5"] == "fail":
            fails.append("J5")
    else:
        if row["t_first_ready_s"] is None or row["t_first_ready_s"] > 100.0:
            fails.append("J3")
    return ";".join(fails) if fails else "pass"


def main() -> None:
    d0 = json.loads(D0.read_text(encoding="utf-8"))["rows"]
    v0 = ref_rows(V5, "V0")
    vb = ref_rows(V5, "VB")
    vbj = ref_rows(J9, "VBJ")
    rows = []
    for r in d0:
        k = r["key"]
        rows.append({
            "variant": r["variant"], "desc": VARIANTS[r["variant"]], "key": k,
            "final_phase": r["final_phase"], "t_first_ready_s": r["t_first_ready_s"],
            "min_force_kN": r["min_force_kN"], "V0_minF_kN": v0[k]["minF"], "VB_minF_kN": vb[k]["minF"],
            "V0_t_ready_s": v0[k]["t_ready"], "VB_t_ready_s": vb[k]["t_ready"],
            "vs_V0": verdict(r, v0[k]), "held_fraction": r["held_fraction"],
            "held_filling": r.get("held_filling"), "held_balanced": r.get("held_balanced"),
            "other_leg_retract_delay_max_s": r.get("other_leg_retract_delay_max_s"),
            "locked_at_extend": r.get("locked_at_extend"), "unlock_delay_s": r.get("unlock_delay_s"),
            "sha10": r["commands_sha256"][:10],
            "D0-1_equals_j9main_VBJ": (r["commands_sha256"] == vbj[k]["sha"]) if r["variant"] == "D0-1" else None,
        })
    rows.sort(key=lambda x: (list(VARIANTS).index(x["variant"]), KEYS.index(x["key"])))
    with open(OUT / "d0_attribution.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    by = defaultdict(dict)
    for r in rows:
        by[r["variant"]][r["key"]] = r
    summ = {"reference": {k: {"V0": v0[k], "VB": vb[k]} for k in KEYS}, "variants": {}}
    for v in VARIANTS:
        rr = by[v]
        r12 = [rr[k] for k in KEYS if k.startswith("R12")]
        summ["variants"][v] = {
            "desc": VARIANTS[v],
            "R12_minF_kN": {r["key"]: r["min_force_kN"] for r in r12},
            "R12_fail_J2": sum(1 for r in r12 if "J2" in r["vs_V0"]),
            "R12_other_leg_retract_delay_s": [r["other_leg_retract_delay_max_s"] for r in r12],
            "level_stall_rows(J4)": [r["key"] for r in rr.values() if "J4" in r["vs_V0"]],
            "J3_fail_rows": [r["key"] for r in rr.values() if "J3" in r["vs_V0"]],
            "S5_t_ready": rr["S5_e0.0"]["t_first_ready_s"], "S1_t_ready": rr["S1_e0.003"]["t_first_ready_s"],
            "held_fraction_max": max(r["held_fraction"] for r in rr.values()),
            "fails_vs_V0": sum(1 for r in rr.values() if r["vs_V0"] != "pass"),
        }
    summ["D0-3_equals_D0-8_sha"] = all(by["D0-3"][k]["sha10"] == by["D0-8"][k]["sha10"] for k in KEYS)
    summ["D0-1_equals_j9main_VBJ"] = all(by["D0-1"][k]["D0-1_equals_j9main_VBJ"] for k in KEYS)
    (OUT / "d0_attribution.json").write_text(json.dumps(summ, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summ["variants"], indent=1))
    print("D0-3 == D0-8:", summ["D0-3_equals_D0-8_sha"], " D0-1 == j9main VBJ:", summ["D0-1_equals_j9main_VBJ"])

    # Figure 1: R12 event-row minimum force per variant and key
    r12k = [k for k in KEYS if k.startswith("R12")]
    order = list(VARIANTS)
    fig, ax = plt.subplots(figsize=(9.0, 4.5))
    x = np.arange(len(order))
    wdt = 0.2
    for i, k in enumerate(r12k):
        ax.bar(x + (i - 1.5) * wdt, [by[v][k]["min_force_kN"] for v in order], wdt, label=k)
        ax.plot([x[0] - 0.5, x[-1] + 0.5], [v0[k]["minF"]] * 2, lw=0.5, color=f"C{i}", ls="--")
    ax.axhline(F_MIN, color="k", lw=1.0, ls=":")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{v}\n{VARIANTS[v]}" for v in order], fontsize=7)
    ax.set_ylabel("E-3 minimum leg force after the event window [kN]")
    ax.set_title("D0 (390f88a9): R12/G4 rows; dotted F_min 9.415 kN, dashed V0 per key", fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "d0_fig_r12_min_force.png", dpi=130)
    plt.close(fig)

    # Figure 2: LEVEL gate-hold fraction and first READY of the stall-prone rows
    fig, ax = plt.subplots(figsize=(9.0, 4.0))
    for i, k in enumerate(["R15_o0.0", "R15_o0.05", "S5_e0.0", "S1_e0.003",
                           "R12_bottom-FL-Fs4-o0.0", "R12_top-FR-Fs4-o0.0"]):
        ax.plot(x, [by[v][k]["held_fraction"] for v in order], marker="o", label=k)
    ax.axhline(0.10, color="grey", lw=0.6, ls=":")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{v}\n{VARIANTS[v]}" for v in order], fontsize=7)
    ax.set_ylabel("LEVEL gate-hold fraction [-]")
    ax.set_title("plant locked while |u| > 1 um/s in LEVEL; old VB plant max 0.012", fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "d0_fig_level_stall.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()
