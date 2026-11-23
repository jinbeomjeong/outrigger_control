"""Per-case detail of the 12b VBK0 A/A stop (run 606f8713), read-only.

For the counted A/A pairs, the both-sides-no-READY pairs and the five largest READY gaps:
selected ``base`` fields of the b1/b2 VBK0 lines, the T4h phase run summary after the fault
(phase sequence with durations), and the fault-free stored rows of the same case in the
12b case source ``h8_noise_VB.json`` (sha 2219ab97, VB rev 4 noise seeds, no rod fault).

Also checks that the b1 and b2 plans differ only by block / seed tokens (setting check).
Writes ``aa_detail.json`` next to this script.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
           r"\606f8713\12b_vbk0_base_a1")
X11 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\prelaunch_j9"
           r"\ed5_inputs\x11")
H8 = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\resume_k1"
          r"\h8_noise_VB.json")
H8_SHA = "2219ab9782b22fbe07e6c1f90e8b49c6b3703b0575b5d7cfb7d72b4f067bec43"
FIELDS = ("final_phase", "pass", "t_ready_s", "t_done_s", "t_P_s", "t_loc_s", "t_off_s",
          "phase_path", "n_relevel", "n_reapproach", "n_probe_rounds", "n_warn", "warnings",
          "flags", "att_end_deg", "loc_revokes", "late_loc_revoked", "weak_leg",
          "min_true_Fcyl_after_off_kN", "max_motor_stroke_mm", "info_counts", "gates")


def plain(key: str) -> str:
    return key.split("#", 1)[1] if "#" in key else key


def case_of(key: str) -> str:
    t = plain(key).split("|")
    return "|".join([t[0], *t[2:]])


def ready(row: dict):
    b = row["base"]
    return b.get("t_ready_s", b.get("t_ready"))


def load(block: str) -> dict:
    doc = json.loads((RUN / f"VBK0_{block}.json").read_text(encoding="utf-8"))
    rows = doc["results"] if isinstance(doc, dict) else doc
    return {case_of(r["key"]): r for r in rows}


def phase_runs(block: str, row: dict, t_from: float) -> list:
    path = RUN / f"VBK0_{block}_t4h" / row["t4h_file"]
    with np.load(path, allow_pickle=False) as d:
        phase = np.asarray(d["phase"]).astype(str)
        t = np.asarray(d["jp3_t_s"]) if "jp3_t_s" in d.files else None
    period = 0.1
    runs = []
    for i, p in enumerate(phase):
        if not runs or runs[-1][1] != p:
            runs.append([i, p, 1])
        else:
            runs[-1][2] += 1
    return [(round(a * period, 1), b, round(c * period, 1)) for a, b, c in runs
            if (a + c) * period >= t_from - 1.0]


def plan_check() -> dict:
    out = {}
    plans = {b: json.loads((X11 / f"{b}_plan.json").read_text(encoding="utf-8"))
             for b in ("b1", "b2")}
    seeds = {"b1": "40", "b2": "41"}
    norm = {}
    for b, plan in plans.items():
        rows = {}
        for key, f in plan["faults"].items():
            k2 = key.replace(f"|s{seeds[b]}|", "|s<seed>|")
            f2 = dict(f)
            f2["fault_id"] = re.sub(rf"12b-{b}-s{seeds[b]}-", "12b-<b>-s<seed>-", f["fault_id"])
            rows[k2] = f2
        norm[b] = rows
        out[f"{b}_top_keys"] = sorted(k for k in plan if k != "faults")
    out["same_after_normalising"] = norm["b1"] == norm["b2"]
    out["n_faults"] = {b: len(r) for b, r in norm.items()}
    keys = {b: [ln.strip() for ln in (X11 / f"{b}_keys.txt").read_text().splitlines()
                if ln.strip()] for b in ("b1", "b2")}
    out["keys_same_after_normalising"] = (
        [k.replace("|s40|", "|s<seed>|") for k in keys["b1"]]
        == [k.replace("|s41|", "|s<seed>|") for k in keys["b2"]])
    other = {b: {k: v for k, v in plans[b].items() if k != "faults"} for b in plans}
    out["non_fault_fields_b1"] = other["b1"]
    out["non_fault_fields_b2"] = other["b2"]
    return out


def h8_rows() -> dict:
    data = H8.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    rows = json.loads(data.decode("utf-8"))["results"]
    by_case: dict[str, list] = {}
    for r in rows:
        if r.get("level") != "L2":
            continue
        k = plain(r["key"])
        seed = k.split("|")[1]
        by_case.setdefault(case_of(r["key"]), []).append(
            (seed, ready(r), (r.get("base") or {}).get("final_phase"),
             (r.get("base") or {}).get("pass")))
    return {"sha256": sha, "sha_ok": sha == H8_SHA, "by_case": by_case}


def main() -> None:
    b1, b2 = load("b1"), load("b2")
    cases = list(b1)
    diffs = []
    for c in cases:
        r1, r2 = ready(b1[c]), ready(b2[c])
        if r1 is not None and r2 is not None:
            diffs.append((abs(r1 - r2), c))
    diffs.sort(reverse=True)
    focus = [c for c in cases if ready(b1[c]) is None or ready(b2[c]) is None]
    focus += [c for _, c in diffs[:5] if c not in focus]
    h8 = h8_rows()
    out = {"plan_check": plan_check(), "h8_sha_ok": h8["sha_ok"], "cases": {}}
    for c in focus:
        entry = {}
        for blk, rows in (("b1", b1), ("b2", b2)):
            row = rows[c]
            base = row["base"]
            entry[blk] = {f: base.get(f) for f in FIELDS if f in base}
            entry[blk]["rod_fault_brief"] = {
                k: row["rod_fault"].get(k) for k in ("fault_id", "leg", "anchor", "trigger_read",
                                                    "first_applied_t_s", "applied_periods",
                                                    "reads", "pre_trigger_fallback")}
            entry[blk]["rod_fault_brief"]["latched"] = row["rod_fault"].get("latched")
            t0 = row["rod_fault"].get("first_applied_t_s") or 0.0
            entry[blk]["phase_runs_from_fault"] = phase_runs(blk, row, t0)
            entry[blk]["events_head"] = [e for e in (base.get("events_head") or [])][:60]
        entry["h8_fault_free_L2_rows"] = h8["by_case"].get(c)
        out["cases"][c] = entry
    # fault-free cross-seed READY spread of the focus cases
    (HERE / "aa_detail.json").write_text(json.dumps(out, indent=1, default=str,
                                                    ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"focus": focus, "plan_same": out["plan_check"]["same_after_normalising"],
                      "keys_same": out["plan_check"]["keys_same_after_normalising"],
                      "h8_sha_ok": h8["sha_ok"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
