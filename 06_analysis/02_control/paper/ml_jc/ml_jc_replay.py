"""Replay J_C / J_P on the stored ML evaluation episodes and list every truth episode (read only).

Usage: python -I ml_jc_replay.py <src_dir> <out_json>
Runs on four workers on the E-core mask 0x00FF0000. No simulation.
"""
import ctypes
import json
import multiprocessing as mp
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control")
ML = ROOT / r"07_results\S8\ml_main_20261025_090131"
AFFINITY = 0x00FF0000
WORKERS = 4


def pin() -> None:
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.SetProcessAffinityMask.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
    k32.SetProcessAffinityMask.restype = ctypes.c_int
    if not k32.SetProcessAffinityMask(k32.GetCurrentProcess(), AFFINITY):
        raise OSError(ctypes.get_last_error())


def init(src: str) -> None:
    pin()
    sys.path.insert(0, src)


def one(args: tuple[str, str]) -> dict:
    import numpy as np

    from outrigger_sim.contact_episode import LEG_NAMES, load_episode
    from outrigger_sim.control.contact_replay import Judge, ReplaySettings, record_judgement, replay_both
    from outrigger_sim.ml.dataset import load_ml_masks
    from outrigger_sim.ml.evaluate import liftoff_transient_samples, ml_scored_samples
    from outrigger_sim.ml.reading_basis import ReadingBasis, pad_record_at_samples, pads_path, with_reading_basis
    from outrigger_sim.verify.contact_metrics import scored_detections

    path, masks_path = args
    masks = load_ml_masks(Path(masks_path))
    episode = load_episode(Path(path))
    contact, limit = pad_record_at_samples(pads_path(episode, ROOT), episode["t_s"])
    corrected = with_reading_basis(episode, ReadingBasis.CORRECTED, contact, limit)
    settings = ReplaySettings.from_controller_meta(episode.meta["controller"], episode.F_min_N)
    replays = replay_both(corrected, settings)
    rec_c = record_judgement(corrected, replays[Judge.COMBINED])
    rec_p = record_judgement(corrected, replays[Judge.PRESSURE])
    m = episode.meta
    t = np.asarray(episode["t_s"], dtype=float)
    fmin = episode.F_min_N
    phase = np.asarray(episode["phase"])
    band = np.asarray(episode["seal_band_N"], dtype=float)
    age = np.asarray(episode["probe_age_s"], dtype=float)
    round_end = np.asarray(episode["probe_round_end"], dtype=bool)
    true_min = np.asarray(episode["true_force_min_N"], dtype=float)
    true_now = np.asarray(episode["true_force_N"], dtype=float)
    est = replays[Judge.COMBINED].load_estimate_N
    reading = np.asarray(corrected["lower_reading_N"], dtype=float)
    rows = []
    for scope, mask in (("scored", ml_scored_samples(episode, masks)), ("transient", liftoff_transient_samples(episode, masks))):
        det_c = scored_detections(replace(rec_c, scored=mask))
        det_p = scored_detections(replace(rec_p, scored=mask))
        for dc, dp in zip(det_c, det_p, strict=True):
            e = dc.episode
            r = slice(e.on_row, e.off_row + 1)
            leg = e.leg
            est_seg = est[r, leg]
            rows.append({
                "scope": scope, "run": str(m.get("episode_id")), "leg": LEG_NAMES[leg], "t_on_s": float(t[e.on_row]),
                "duration_s": float(t[e.off_row] - t[e.on_row]) + float(m.get("period_s") or 0.1), "samples": e.off_row - e.on_row + 1,
                "is_lift": bool(e.is_lift), "true_min_kN": float(np.nanmin(true_min[r, leg])) / 1e3,
                "true_at_samples_min_kN": float(np.nanmin(true_now[r, leg])) / 1e3,
                "est_min_kN": float(np.nanmin(est_seg)) / 1e3 if np.isfinite(est_seg).any() else None,
                "est_minus_Fmin_min_kN": float(np.nanmin(est_seg) - fmin) / 1e3 if np.isfinite(est_seg).any() else None,
                "reading_min_kN": float(np.nanmin(reading[r, leg])) / 1e3,
                "band_on_kN": float(band[e.on_row, leg]) / 1e3, "phase_on": str(phase[e.on_row]),
                "phases": sorted({str(x) for x in phase[r]}),
                "probe_age_on_s": float(age[e.on_row, leg]) if np.isfinite(age[e.on_row, leg]) else None,
                "probe_rounds_before": int(round_end[: e.on_row + 1].sum()),
                "t_since_event_s": None if m.get("event_t_s") is None else float(t[e.on_row]) - float(m["event_t_s"]),
                "JC_first_decision_s": dc.first_decision_s, "JC_action_delay_s": dc.action_delay_s,
                "JP_first_decision_s": dp.first_decision_s, "JP_action_delay_s": dp.action_delay_s,
            })
    fs = m.get("seal_friction_N")
    return {"path": path, "meta": {
        "episode_id": m.get("episode_id"), "base_id": m.get("base_id"), "level": m.get("level"), "seal_friction_N": fs,
        "floor": m.get("floor"), "floor_roll_deg": m.get("floor_roll_deg"), "floor_pitch_deg": m.get("floor_pitch_deg"), "sensor_grade": m.get("sensor_grade"),
        "zero_calibration": m.get("zero_calibration"), "sensor_condition": m.get("sensor_condition"), "event": m.get("event"), "event_t_s": m.get("event_t_s"),
        "beta_Pa": m.get("beta_Pa"), "crawler_contact": m.get("crawler_contact"), "source": m.get("source"), "F_min_N": fmin,
    }, "rows": rows}


def main() -> None:
    src, out = sys.argv[1], sys.argv[2]
    pin()
    sys.path.insert(0, src)
    import outrigger_sim
    from outrigger_sim.ml.split import SPLIT_SEED, split_by_base

    print("module", outrigger_sim.__file__, flush=True)
    masks = str(ML / "verify_S8ML.json")
    folders = {"main": ML / "ml_dataset", "MLJ": ML / "ml_dataset_mlj", "EN": ML / "ml_dataset_en"}
    jobs = {name: sorted(str(p) for p in folder.glob("*.npz")) for name, folder in folders.items()}
    with mp.get_context("spawn").Pool(WORKERS, initializer=init, initargs=(src,)) as pool:
        results = {name: pool.map(one, [(p, masks) for p in paths], chunksize=4) for name, paths in jobs.items()}
    metas = [r["meta"] for r in results["main"]]
    split = split_by_base(metas, seed=SPLIT_SEED)
    labels = {"train": split.train, "validation": split.validation, "test": split.test, "OOD-1": split.ood_level, "OOD-2": split.ood_roll}
    sets = {}
    for name, idx in labels.items():
        sets[name] = [results["main"][i] for i in idx]
    sets["MLJ"] = results["MLJ"]
    sets["EN"] = results["EN"]
    for name, items in sets.items():
        scored = [row for item in items for row in item["rows"] if row["scope"] == "scored"]
        miss = [row for row in scored if row["JC_first_decision_s"] is None]
        missp = [row for row in scored if row["JP_first_decision_s"] is None]
        print(f"{name}: runs {len(items)} episodes {len(scored)} J_C missed {len(miss)} J_P missed {len(missp)}", flush=True)
    Path(out).write_text(json.dumps(sets, indent=0, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
