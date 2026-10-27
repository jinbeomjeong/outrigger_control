"""Rev. 64 (b)-6: 10 Hz instantaneous sampling of the event transient, re-sampled at other
phases, against a period-mean sampler.

For every case with pads.npz + r8_series.npz and an ``event_t_s`` (settle / drop episodes):
window [t_ev, t_ev + 5 s]. ``F_pressure`` (1 ms, the net force the two sensors see, true
values) is sampled at the controller instants shifted by phi = 0, 10, .., 90 ms. Per leg the
lower estimate is the sample minus the recorded per-leg band (``leg_band_N``).
  * inst  = F_pressure(t_k + phi) - band          (instantaneous sampler, what R8 does)
  * mean  = mean F_pressure over (t_k + phi - 0.1, t_k + phi] - band (period-mean sampler)
  * alias-only crossings: inst < L and mean >= L, for L = 1.4 F_min (re-approach start) and
    F_min + 5 kN (guard); mean-only crossings the other way;
  * triggers (first sample below the level after one above) of both samplers per leg; an
    instantaneous trigger is spurious when no period-mean sample is below the level within
    [-0.2, +0.3] s;
  * error inst - mean: rms and max per case;
  * heave: the 4..15 Hz FFT peak of the 1 ms sum of F_pressure over [t_ev + 0.05, t_ev + 2.05] s
    (linear trend removed, Hann), its 10 Hz alias f_a = |f - 10 round(f / 10)|.
Open loop on the recorded trajectory: a changed decision would change the trajectory; the
counts measure how often the sampler alone moves a sample across a controller level.
Usage: python -I r64_alias.py <out_json> <workers> <root> [<root> ...]
Read only; no random numbers.
"""
from __future__ import annotations

import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r64_common import F_MIN_N, LEGS, case_dirs, find_key, load_json  # noqa: E402

LEVELS = {"reapproach_1p4Fmin": 1.4 * F_MIN_N, "guard_Fmin_5kN": F_MIN_N + 5000.0}
PHASES_MS = list(range(0, 100, 10))
SPAN_S = 5.0


def heave_peak(t: np.ndarray, s: np.ndarray, t0: float) -> tuple[float | None, float | None]:
    m = (t >= t0 + 0.05) & (t < t0 + 2.05)
    if m.sum() < 500:
        return None, None
    x = s[m]
    tt = t[m] - t[m][0]
    x = x - np.polyval(np.polyfit(tt, x, 1), tt)
    x = x * np.hanning(len(x))
    dt = float(np.median(np.diff(t[m])))
    spec = np.abs(np.fft.rfft(x))
    f = np.fft.rfftfreq(len(x), dt)
    band = (f >= 4.0) & (f <= 15.0)
    if not band.any():
        return None, None
    i = np.flatnonzero(band)[np.argmax(spec[band])]
    amp = 2.0 * spec[i] / np.hanning(len(x)).sum()
    return float(f[i]), float(amp)


def analyse(case: Path) -> dict | None:
    result = load_json(case / "result.json")
    if result is None or not (case / "pads.npz").exists() or not (case / "r8_series.npz").exists():
        return None
    t_ev = result.get("event_t_s") if isinstance(result, dict) else None
    if not isinstance(t_ev, (int, float)):
        return None
    pads = np.load(case / "pads.npz", allow_pickle=True)
    r8 = np.load(case / "r8_series.npz", allow_pickle=True)
    tp = np.asarray(pads["t"], float)
    Fp = np.asarray(pads["F_pressure"], float)
    tk = np.asarray(r8["t"], float)
    band = np.asarray(r8["leg_band_N"], float)
    sel = (tk >= t_ev) & (tk <= t_ev + SPAN_S - 0.1)
    if sel.sum() < 10:
        return None
    dtp = float(np.median(np.diff(tp)))
    nper = int(round(0.1 / dtp))
    csum = np.vstack([np.zeros((1, 4)), np.cumsum(Fp, axis=0)])
    beta = find_key(result, "beta_GPa")
    ep = result.get("episode") or {}
    out = {"case": str(case), "beta_GPa": beta, "kind": ep.get("kind"), "leg": ep.get("leg"),
           "depth_m": ep.get("depth_m"), "ramp_s": ep.get("ramp_s"), "per_phase": {}}
    f_h, a_h = heave_peak(tp, Fp.sum(axis=1), float(t_ev))
    out["heave_hz"] = f_h
    out["heave_amp_kN"] = None if a_h is None else a_h / 1e3
    out["alias_hz"] = None if f_h is None else abs(f_h - 10.0 * round(f_h / 10.0))
    for phi in PHASES_MS:
        ts = tk[sel] + phi / 1000.0
        idx = np.clip(np.searchsorted(tp, ts - 1e-9), nper, len(tp) - 1)
        inst = Fp[idx] - band[sel]
        mean = (csum[idx + 1] - csum[idx + 1 - nper]) / nper - band[sel]
        err = inst - mean
        row = {"err_rms_kN": float(np.sqrt(np.mean(err**2)) / 1e3),
               "err_max_kN": float(np.abs(err).max() / 1e3)}
        for name, level in LEVELS.items():
            a_only = (inst < level) & (mean >= level)
            m_only = (mean < level) & (inst >= level)
            row[f"{name}_alias_only"] = int(a_only.sum())
            row[f"{name}_mean_only"] = int(m_only.sum())
            row[f"{name}_inst_below"] = int((inst < level).sum())
            row[f"{name}_mean_below"] = int((mean < level).sum())
            # triggers: first sample below the level after a sample above (per leg); a spurious
            # instantaneous trigger has no period-mean sample below the level within
            # [-0.2, +0.3] s (2 samples before, 3 after)
            ib, mb = inst < level, mean < level
            trig_i = ib[1:] & ~ib[:-1]
            trig_m = mb[1:] & ~mb[:-1]
            spurious = 0
            for k, leg in zip(*np.nonzero(trig_i)):
                lo, hi = max(0, k + 1 - 2), min(len(mb), k + 1 + 4)
                if not mb[lo:hi, leg].any():
                    spurious += 1
            row[f"{name}_trig_inst"] = int(trig_i.sum())
            row[f"{name}_trig_mean"] = int(trig_m.sum())
            row[f"{name}_trig_inst_spurious"] = int(spurious)
        out["per_phase"][str(phi)] = row
    out["n_samples"] = int(sel.sum())
    return out


def safe(case: Path):
    try:
        return analyse(case)
    except Exception as exc:  # report, continue
        return {"case": str(case), "error": repr(exc)}


def main() -> None:
    out_path, workers, roots = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
    cases = list(case_dirs(roots))
    with Pool(workers) as pool:
        rows = [r for r in pool.map(safe, cases, chunksize=4) if r]
    good = [r for r in rows if "error" not in r]
    summary = {"cases": len(good), "errors": [r for r in rows if "error" in r][:10]}
    for name in LEVELS:
        per = {}
        for phi in PHASES_MS:
            k = str(phi)
            per[k] = {
                "alias_only": sum(r["per_phase"][k][f"{name}_alias_only"] for r in good),
                "trig_inst": sum(r["per_phase"][k][f"{name}_trig_inst"] for r in good),
                "trig_mean": sum(r["per_phase"][k][f"{name}_trig_mean"] for r in good),
                "trig_inst_spurious": sum(r["per_phase"][k][f"{name}_trig_inst_spurious"] for r in good),
                "mean_only": sum(r["per_phase"][k][f"{name}_mean_only"] for r in good),
                "inst_below": sum(r["per_phase"][k][f"{name}_inst_below"] for r in good),
                "mean_below": sum(r["per_phase"][k][f"{name}_mean_below"] for r in good),
                "cases_with_spurious_trigger": sum(
                    r["per_phase"][k][f"{name}_trig_inst_spurious"] > 0 for r in good)}
        summary[name] = per
    summary["samples_per_phase"] = sum(r["n_samples"] for r in good) * 4
    errs = np.array([[r["per_phase"][str(p)]["err_max_kN"] for p in PHASES_MS] for r in good])
    rms = np.array([[r["per_phase"][str(p)]["err_rms_kN"] for p in PHASES_MS] for r in good])
    if len(good):
        summary["err_max_kN_p50_p99_max"] = [float(np.percentile(errs, 50)),
                                            float(np.percentile(errs, 99)), float(errs.max())]
        summary["err_rms_kN_p50_p99"] = [float(np.percentile(rms, 50)), float(np.percentile(rms, 99))]
    fh = [(r["heave_hz"], r["alias_hz"], r["beta_GPa"], r["heave_amp_kN"]) for r in good
          if r["heave_hz"] is not None]
    if fh:
        arr = np.array([(a, b, c if isinstance(c, (int, float)) else np.nan, d) for a, b, c, d in fh])
        summary["heave_hz_min_p50_max"] = [float(np.nanmin(arr[:, 0])), float(np.nanmedian(arr[:, 0])),
                                          float(np.nanmax(arr[:, 0]))]
        summary["alias_hz_min_p50_max"] = [float(np.nanmin(arr[:, 1])), float(np.nanmedian(arr[:, 1])),
                                          float(np.nanmax(arr[:, 1]))]
        ok = ~np.isnan(arr[:, 2])
        if ok.sum() > 3:
            summary["corr_heave_hz_vs_beta"] = float(np.corrcoef(arr[ok, 0], arr[ok, 2])[0, 1])
            bins = [(0.6, 0.9), (0.9, 1.2), (1.2, 1.4), (1.4, 1.7)]
            summary["heave_by_beta"] = {
                f"{lo}-{hi}": [int(((arr[:, 2] >= lo) & (arr[:, 2] < hi)).sum()),
                               float(np.nanmedian(arr[(arr[:, 2] >= lo) & (arr[:, 2] < hi), 0]))
                               if ((arr[:, 2] >= lo) & (arr[:, 2] < hi)).any() else None,
                               float(np.nanmedian(arr[(arr[:, 2] >= lo) & (arr[:, 2] < hi), 1]))
                               if ((arr[:, 2] >= lo) & (arr[:, 2] < hi)).any() else None]
                for lo, hi in bins}
    worst = sorted(good, key=lambda r: -max(r["per_phase"][str(p)]["reapproach_1p4Fmin_trig_inst_spurious"]
                                            for p in PHASES_MS))[:15]
    summary["worst_cases"] = [{"case": Path(r["case"]).name, "beta": r["beta_GPa"],
                               "heave_hz": r["heave_hz"], "alias_hz": r["alias_hz"],
                               "max_spurious_reapproach": max(
                                   r["per_phase"][str(p)]["reapproach_1p4Fmin_trig_inst_spurious"]
                                   for p in PHASES_MS),
                               "spurious_at_phi0": r["per_phase"]["0"]["reapproach_1p4Fmin_trig_inst_spurious"]}
                              for r in worst]
    Path(out_path).write_text(json.dumps({"summary": summary, "cases": good}, indent=1,
                                         ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=1, ensure_ascii=False)[:8000])


if __name__ == "__main__":
    main()


