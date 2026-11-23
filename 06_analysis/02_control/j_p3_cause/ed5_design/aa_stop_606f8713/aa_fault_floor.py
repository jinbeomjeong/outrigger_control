"""Erratum 8 inputs from the VBK0 A/A of run 606f8713 (read-only; no VBK line is opened).

1. 6.3.7 (1) floor: per case, the (name, leg) FAULT pair sets of VBK0 b1 (seed 40) and b2
   (seed 41), from the T4h ``meta_json`` ``events`` (6.3.7 (1) parse) plus the PHASE_FAULT
   entry of the T4h ``phase`` (erratum 1 7). Counted both ways (b2 pairs not in b1 = "b2 new",
   b1 pairs not in b2 = "b1 new"). Two parses: this file's own, and ``fault_pairs`` /
   ``phase_fault_pairs`` of the run commit's ``jp3_12b_judge.py`` (worktree ed5-run5); they
   must agree.
2. The (2)+(3) A/A analogue n23 in each direction (base = one seed, other = the other seed;
   base READY reached and other READY missing, or other - base rounded to 1e-6 s > 30 s).
3. The stall signature of erratum 8 applied to every VBK0 line of b1 / b2 and of the c dry
   VBK0 lines (seeds 90 / 91): READY missing, no fault-phase entry, last T4h ``phase`` row
   level or probe, and over the reads with ``t_s`` >= last ``t_s`` - 20 s (1e-6 s tolerance)
   the span (max - min) of ``motor_stroke_m`` below 1 mm on all four legs.
4. The T4h arrays the signature needs, present in every VBK0 T4h file used.
Writes ``aa_fault_floor.json``.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
J9 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\606f8713")
JUDGE_DIR = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed5-run5\04_scripts"
                 r"\04_hydraulic\coupled")
LEGS = ("FL", "FR", "RL", "RR")
NO_LEG = "–"
FAULT_PHASES = ("fault", "fault_reground")
STALL_WINDOW_S = 20.0
STALL_SPAN_M = 1.0e-3
TOL_S = 1e-6
SIGNATURE_ARRAYS = ("t_s", "phase", "motor_stroke_m")


def plain(key: str) -> str:
    return key.split("#", 1)[1] if "#" in key else key


def case_of(key: str) -> str:
    t = plain(key).split("|")
    return "|".join([t[0], *t[2:]])


def ready(row: dict):
    b = row["base"]
    return b.get("t_ready_s", b.get("t_ready"))


def rows_of(path: Path) -> list:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return doc["results"] if isinstance(doc, dict) else doc


def own_fault_pairs(events: list, phase) -> set:
    pairs = set()
    for event in events:
        name = event[1] if isinstance(event, (list, tuple)) else event
        tokens = str(name).split(":")
        if not tokens[0].startswith("FAULT"):
            continue
        legs = {p for tok in tokens[1:] for p in tok.split(",") if p in LEGS}
        for leg in legs or {NO_LEG}:
            pairs.add((tokens[0], leg))
    ph = [str(v).lower() for v in phase]
    if any(v in FAULT_PHASES and (i == 0 or ph[i - 1] not in FAULT_PHASES)
           for i, v in enumerate(ph)):
        pairs.add(("PHASE_FAULT", NO_LEG))
    return pairs


def load_t4h(folder: Path, row: dict) -> tuple[dict, dict]:
    with np.load(folder / row["t4h_file"], allow_pickle=False) as d:
        arrays = {k: np.asarray(d[k]) for k in d.files if k != "meta_json"}
        meta = json.loads(str(d["meta_json"]))
    return arrays, meta


def signature(row: dict, arrays: dict, fault_pairs: set) -> dict:
    t = np.asarray(arrays["t_s"], float)
    phase = np.asarray(arrays["phase"]).astype(str)
    s = np.asarray(arrays["motor_stroke_m"], float)
    window = t >= t[-1] - STALL_WINDOW_S - TOL_S
    span = s[window].max(axis=0) - s[window].min(axis=0)
    has_phase_fault = ("PHASE_FAULT", NO_LEG) in fault_pairs
    parts = {"ready_missing": ready(row) is None,
             "no_fault_phase_entry": not has_phase_fault,
             "last_phase_level_or_probe": phase[-1].lower() in ("level", "probe"),
             "stroke_span_below_1mm": bool((span < STALL_SPAN_M).all())}
    return {"is_signature": all(parts.values()), "parts": parts,
            "last_t_s": round(float(t[-1]), 3), "last_phase": phase[-1],
            "span_mm": np.round(span * 1e3, 3).tolist(), "n_window_reads": int(window.sum())}


def main() -> None:
    sys.path.insert(0, str(JUDGE_DIR))
    import jp3_12b_judge as judge  # run-commit judge parse (second path)

    out: dict = {"judge_module": str(Path(judge.__file__).resolve())}
    blocks = {}
    missing_arrays: list = []
    for blk in ("b1", "b2"):
        folder = J9 / "12b_vbk0_base_a1" / f"VBK0_{blk}_t4h"
        lines = {}
        for row in rows_of(J9 / "12b_vbk0_base_a1" / f"VBK0_{blk}.json"):
            arrays, meta = load_t4h(folder, row)
            missing_arrays += [f"{blk}:{row['key']}:{a}" for a in SIGNATURE_ARRAYS
                               if a not in arrays]
            own = own_fault_pairs(meta["events"], arrays["phase"])
            ref = judge.fault_pairs(meta["events"]) | judge.phase_fault_pairs(arrays["phase"])
            lines[case_of(row["key"])] = {"row": row, "own": own, "ref": ref,
                                          "sig": signature(row, arrays, own)}
        blocks[blk] = lines
    cases = list(blocks["b1"])
    parse_mismatch = [f"{b}:{c}" for b in blocks for c in cases
                      if blocks[b][c]["own"] != blocks[b][c]["ref"]]
    b2_new = {c: sorted(blocks["b2"][c]["own"] - blocks["b1"][c]["own"]) for c in cases}
    b1_new = {c: sorted(blocks["b1"][c]["own"] - blocks["b2"][c]["own"]) for c in cases}
    pair_names = Counter(f"{n}|{leg}" for b in blocks for c in cases
                         for n, leg in blocks[b][c]["own"])
    out["fault_floor"] = {
        "pairs": len(cases),
        "parse_mismatch_own_vs_judge": parse_mismatch,
        "lines_with_any_fault_pair": {b: sum(bool(blocks[b][c]["own"]) for c in cases)
                                      for b in blocks},
        "fault_pair_counts_all_lines": dict(pair_names),
        "b2_new_pairs": sum(bool(v) for v in b2_new.values()),
        "b1_new_pairs": sum(bool(v) for v in b1_new.values()),
        "either_direction_pairs": sum(bool(b2_new[c] or b1_new[c]) for c in cases),
        "b2_new": {c: v for c, v in b2_new.items() if v},
        "b1_new": {c: v for c, v in b1_new.items() if v},
    }
    n23 = {}
    for base, other in (("b1", "b2"), ("b2", "b1")):
        loss, late, worse_keys, both_missing = 0, 0, [], 0
        for c in cases:
            r0, r1 = ready(blocks[base][c]["row"]), ready(blocks[other][c]["row"])
            if r0 is None and r1 is None:
                both_missing += 1
                continue
            if r0 is None:
                continue
            if r1 is None:
                loss += 1
                worse_keys.append(c)
            elif round(r1 - r0, 6) > 30.0:
                late += 1
                worse_keys.append(c)
        n23[f"base_{base}_other_{other}"] = {"n_ready_loss": loss, "n_ready_plus30": late,
                                             "n23": loss + late, "keys": worse_keys,
                                             "both_missing_excluded": both_missing}
    out["n23_aa_analogue"] = n23
    sig = {}
    for b in blocks:
        for c in cases:
            line = blocks[b][c]
            if line["row"]["base"].get("t_ready_s", line["row"]["base"].get("t_ready")) is None:
                sig[f"{b}:{c}"] = line["sig"]
    out["signature_12b_vbk0_no_ready"] = sig
    out["signature_12b_vbk0_counts"] = {
        b: sum(blocks[b][c]["sig"]["is_signature"] for c in cases) for b in blocks}
    out["signature_false_on_ready_lines"] = sum(
        blocks[b][c]["sig"]["is_signature"] for b in blocks for c in cases
        if ready(blocks[b][c]["row"]) is not None)
    dry = {}
    dry_fault_lines, dry_lines = 0, 0
    for name in ("c92", "c93"):
        folder = J9 / "cdry_a1" / f"VBK0_{name}_t4h"
        for row in rows_of(J9 / "cdry_a1" / f"VBK0_{name}.json"):
            arrays, meta = load_t4h(folder, row)
            pairs = own_fault_pairs(meta["events"], arrays["phase"])
            dry_lines += 1
            dry_fault_lines += bool(pairs)
            if ready(row) is not None:
                continue
            missing_arrays += [f"{name}:{row['key']}:{a}" for a in SIGNATURE_ARRAYS
                               if a not in arrays]
            dry[f"{name}:{case_of(row['key'])}"] = signature(row, arrays, pairs)
    out["signature_cdry_vbk0_no_ready"] = dry
    out["cdry_vbk0_fault_lines"] = {"lines": dry_lines, "with_fault_pair": dry_fault_lines}
    # 5. a loose bound on the (1) false failure (record): per-line FAULT rate of rod-fault VBK0
    #    lines, one-sided 95 % upper (0 observed), times the judged pairs and the changed share.
    n_lines = 2 * len(cases) + dry_lines
    k_lines = sum(bool(blocks[b][c]["own"]) for b in blocks for c in cases) + dry_fault_lines
    p_up = 1.0 - 0.05 ** (1.0 / n_lines) if k_lines == 0 else None
    bounds = {}
    if p_up is not None:
        for label, c_val in (("c_point_0.127", 20 / 158), ("c_cp95_0.189", 0.18870750758740512),
                             ("c_1", 1.0)):
            lam = c_val * 334 * p_up
            bounds[label] = {"lambda_upper": lam, "P1_upper": 1.0 - float(np.exp(-lam))}
    out["fault_false_fail_bound"] = {"vbk0_rod_fault_lines": n_lines,
                                     "lines_with_fault_pair": k_lines,
                                     "p_line_upper95_one_sided": p_up,
                                     "judged_pairs_b1_b2": 334, "bounds": bounds,
                                     "note": "record only; point estimate 0"}
    out["signature_arrays_missing"] = missing_arrays
    (HERE / "aa_fault_floor.json").write_text(json.dumps(out, indent=1, ensure_ascii=False,
                                                         default=list), encoding="utf-8")
    print(json.dumps({"fault_floor": {k: v for k, v in out["fault_floor"].items()
                                      if k not in ("b2_new", "b1_new")},
                      "n23": {k: {kk: vv for kk, vv in v.items() if kk != "keys"}
                              for k, v in n23.items()},
                      "sig_counts": out["signature_12b_vbk0_counts"],
                      "sig_on_ready": out["signature_false_on_ready_lines"],
                      "arrays_missing": len(missing_arrays)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
