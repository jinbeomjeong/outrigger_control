"""Offline screen of the spec 110.1 load-sum diagnostics (D5 / E-5) on recorded S6 runs.

Independent re-implementation (numpy only, no controller import) used for control spec
revision 29 (117). For every case of the given batches:

* nominal net force ``F_i = p_h A_p - p_r A_ann`` from ``record.npz`` (20 ms controller
  samples); constant zero offsets cancel in the differences used here;
* controller phase and the GE1'-c standstill gate from ``ge1_series.json``;
* command-free time from ``u_cmd`` (the output of period k-1 acts before sample k);
* a load reference at the first READY sample with commands zero for 0.5 s and the gate
  open (110.1 (2)), re-taken at every READY entry; ``--mean-window N`` averages the last N
  samples instead of one (N = 1 reproduces the 110.1 code);
* over READY samples with commands zero >= 0.5 s: max ``|sum F - sum F_ref|``, the longest
  run above the E-5 limit 4 kN, and per reference the mean / max / std of the deviation
  from 2 s after the reference on (the reference bias).

Run (dynamics-dev):
    conda run -n dynamics-dev python -I s6_diag_load_reference_screen.py \
        --out <json> [--mean-window 25] <batch> [<batch> ...]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "07_results" / "S6"
SETTLE_S = 0.5
DRIFT_N = 4000.0


def _phase_series(res: dict, ge1: list, t_rel: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    phase_at = np.empty(len(t_rel), dtype=object)
    for k, tr in enumerate(t_rel):
        name = None
        for t_phase, phase in res["phases"]:
            if tr + 1e-9 >= t_phase:
                name = phase
        phase_at[k] = name
    ge1_map = {round(e[0], 2): (e[1], bool(e[2] and e[2].get("is_geometry_valid"))) for e in ge1}
    valid = np.zeros(len(t_rel), dtype=bool)
    for k, tr in enumerate(t_rel):
        hit = ge1_map.get(round(float(tr), 2))
        if hit is not None:
            phase_at[k] = hit[0]
            valid[k] = hit[1]
    return phase_at, valid


def screen(case_dir: Path, mean_window: int) -> dict | None:
    rec_path = case_dir / "record" / "record.npz"
    res_path = case_dir / "result.json"
    ge1_path = case_dir / "ge1_series.json"
    if not (rec_path.exists() and res_path.exists() and ge1_path.exists()):
        return None
    rec = np.load(rec_path)
    res = json.loads(res_path.read_text(encoding="utf-8"))
    settings = res["settings"]
    two_pressure = res["controller_meta"].get("two_pressure", {})
    head_area = np.array(two_pressure["head_area_m2"])
    annulus_area = np.array(two_pressure["annulus_area_m2"])
    t = rec["t"]
    t_rel = t - float(settings.get("start_t_s") or 0.0)
    head = rec["meas.head_pressure"]
    rod = np.nan_to_num(rec["meas.rod_pressure"]) if "meas.rod_pressure" in rec.files else 0.0 * head
    total = (head * head_area - rod * annulus_area).sum(axis=1)
    u_cmd = rec["u_cmd"]
    period = float(np.median(np.diff(t)))
    free = np.zeros(len(t))
    count = 0
    for k in range(1, len(t)):
        count = 0 if np.any(u_cmd[k - 1] != 0.0) else count + 1
        free[k] = count * period
    phase_at, valid = _phase_series(res, json.loads(ge1_path.read_text(encoding="utf-8")), t_rel)

    ref = None
    refs: list[tuple[float, float]] = []
    samples: list[tuple[float, float, int]] = []
    max_dev, t_max, run, longest = 0.0, None, 0.0, 0.0
    for k in range(len(t)):
        is_ready = phase_at[k] == "ready"
        if is_ready and (k == 0 or phase_at[k - 1] != "ready"):
            ref = None
        if not is_ready:
            run = 0.0
            continue
        settled = free[k] >= SETTLE_S - 1e-9
        if ref is None:
            if settled and valid[k]:
                ref = float(np.mean(total[max(0, k - mean_window + 1):k + 1]))
                refs.append((round(float(t_rel[k]), 2), round(ref / 1e3, 3)))
            continue
        if not settled:
            run = 0.0
            continue
        dev = float(total[k] - ref)
        samples.append((float(t_rel[k]), dev, len(refs)))
        if abs(dev) > max_dev:
            max_dev, t_max = abs(dev), float(t_rel[k])
        run = run + period if abs(dev) > DRIFT_N else 0.0
        longest = max(longest, run)

    table = np.array(samples) if samples else np.zeros((0, 3))
    bias = []
    for index in range(1, len(refs) + 1):
        seg = table[table[:, 2] == index]
        if len(seg) <= 50:
            continue
        late = seg[seg[:, 0] >= seg[0, 0] + 2.0, 1]
        bias.append({
            "mean_kN": round(float(np.mean(late)) / 1e3, 3),
            "max_abs_kN": round(float(np.max(np.abs(late))) / 1e3, 3),
            "std_kN": round(float(np.std(late)) / 1e3, 3),
        })
    judged = (phase_at == "ready") & (free >= SETTLE_S - 1e-9)
    return {
        "case": case_dir.name,
        "batch": case_dir.parent.name,
        "pressure_grade": settings.get("pressure_grade"),
        "zero_calibration": settings.get("zero_calibration"),
        "head_offset_bar": settings.get("head_offset_bar"),
        "head_drift_bar": settings.get("head_drift_bar"),
        "references_t_s_sum_kN": refs,
        "max_abs_dev_kN": round(max_dev / 1e3, 3),
        "t_max_abs_dev_s": None if t_max is None else round(t_max, 2),
        "longest_run_over_4kN_s": round(longest, 2),
        "judged_s": round(float(np.sum(judged)) * period, 1),
        "reference_bias_from_2s": bias,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("batches", nargs="+")
    parser.add_argument("--mean-window", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for batch in args.batches:
        for case_dir in sorted((ROOT / batch).iterdir()):
            if case_dir.is_dir():
                row = screen(case_dir, args.mean_window)
                if row is not None:
                    rows.append(row)
    payload = {
        "generated_by": "04_scripts/03_control/s6_diag_load_reference_screen.py (control-expert)",
        "spec": "s6_control_spec.md revision 29, section 117",
        "settings": {"settle_s": SETTLE_S, "e5_limit_N": DRIFT_N, "mean_window_samples": args.mean_window},
        "batches": args.batches,
        "cases": rows,
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(rows)} cases -> {args.out}")


if __name__ == "__main__":
    main()
