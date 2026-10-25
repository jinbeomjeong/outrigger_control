"""Train and score the ground-contact ML candidates against the replayed J_C (P-S8-2).

Spec ``00_docs/04_control/s6_control_spec.md`` rev. 39 205, rev. 51 223.2 (tags, P-S8-18).
Runs in the ML environment only:

    C:\\ProgramData\\miniforge3\\envs\\pytorch_214_cuda_python_313\\python.exe -I \\
        04_scripts/05_ml/train_contact_ml.py --episodes <folder of episode npz> --out <folder> \\
        [--ml-masks <verify_S8ML.json> --tags-dir <folder of s8_ml_rev51_*.json>] \\
        [--release-scan <h_s8_4_release_scan.json>] \\
        [--judged-episodes <folder of judged-case npz>] [--lgbm-preset regularized|legacy]
    ... --synthetic 12x4 --out <folder>      # pipeline smoke on synthetic episodes only

Episode npz files come from ``build_contact_episodes.py`` (Chrono environment); this process
never imports pychrono (205.4: no shared process). Outputs in ``--out``: ``report.json``
(dataset summary with the episode count per crawler contact model, tags, split, seeds, set
scores, E1-E7 and tag rows, latency, ONNX exporter and ONNX-vs-model check), ``lgbm_*.txt``,
``lgbm_*.onnx``, ``contact_gru.onnx``. E5 uses the ONNX latency of both models; the native
LightGBM latency is kept as a reference.

Tags: ``--ml-masks`` is also the judge record whose ``ml_metrics`` may carry the rev. 51 tags
(C-S8-34 ④); without them the tags come from ``--tags-dir`` (rev. 51 control results).
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

os.environ.setdefault("MKL_THREADING_LAYER", "TBB")  # torch + MKL numpy (CLAUDE.md)
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")  # deterministic cuBLAS (GRU seed)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "03_src"))

import numpy as np  # noqa: E402

from outrigger_sim.contact_episode import (  # noqa: E402
    Episode,
    count_by_crawler_contact,
    load_episode,
)
from outrigger_sim.control.contact_replay import ReplaySettings  # noqa: E402
from outrigger_sim.ml.dataset import (  # noqa: E402
    INDIVIDUAL_PRESSURE_CHANNELS,
    EpisodeTags,
    Examples,
    branch_history,
    build_examples,
    load_episode_tags,
    load_ml_masks,
    release_step_rows,
    uses_individual_pressures,
)
from outrigger_sim.ml.evaluate import score_set, verdict_rows  # noqa: E402
from outrigger_sim.ml.models import (  # noqa: E402
    GruOnnxModel,
    GruSettings,
    LightGbmOnnxModel,
    LightGbmSettings,
    OnnxExport,
    Prediction,
    export_gru_onnx,
    export_lightgbm_onnx,
    lightgbm_latency,
    lightgbm_onnx_latency,
    onnx_latency,
    train_gru,
    train_lightgbm,
)
from outrigger_sim.ml.split import SPLIT_SEED, Split, split_by_base  # noqa: E402
from outrigger_sim.ml.synthetic import synthetic_cases, synthetic_episode  # noqa: E402
from outrigger_sim.verify.contact_metrics import ContactClass  # noqa: E402

SYNTHETIC_SEED = 20261024
OOD_SETS = (("OOD-1 middle auger", "ood_level"), ("OOD-2 roll > 4.4 deg", "ood_roll"))
JUDGED_SET = "judged cases"


def _load_episodes(args: argparse.Namespace) -> list[Episode]:
    if args.synthetic:
        bases, per_base = (int(part) for part in args.synthetic.lower().split("x"))
        return [synthetic_episode(case)
                for case in synthetic_cases(bases, per_base, SYNTHETIC_SEED)]
    return _load_folder(Path(args.episodes))


def _load_folder(folder: Path) -> list[Episode]:
    paths = sorted(folder.glob("*.npz"))
    if not paths:
        raise SystemExit(f"no episode npz in {folder}")
    return [load_episode(path) for path in paths]


def _load_tags(args: argparse.Namespace) -> dict[str, EpisodeTags] | None:
    if not args.ml_masks or args.synthetic:
        return None
    tags_dir = Path(args.tags_dir) if args.tags_dir else None
    release_scan = Path(args.release_scan) if args.release_scan else None
    return load_episode_tags(Path(args.ml_masks), tags_dir, release_scan)


def _settings_for(episode: Episode) -> ReplaySettings:
    return ReplaySettings.from_controller_meta(episode.meta["controller"], episode.F_min_N)


def _pick(episodes: list[Episode], indices) -> list[Episode]:
    return [episodes[i] for i in indices]


def _export_lightgbm(model, out: Path) -> OnnxExport | None:
    try:
        return export_lightgbm_onnx(model, out)
    except ImportError as error:
        print(f"LightGBM ONNX unavailable ({error}); E5 uses the native LightGBM latency")
        return None


def _export_meta(export: OnnxExport | None) -> dict | None:
    if export is None:
        return None
    return {"files": [path.name for path in export.paths], "exporter": export.exporter,
            "fallback_reason": export.fallback_reason, "bytes": export.model_bytes}


def _onnx_difference(original: Prediction, onnx: Prediction) -> dict[str, float]:
    """Largest |ONNX - original model| on the same examples (record, not judged)."""
    return {
        "probabilities_max_abs": float(np.max(
            np.abs(original.probabilities - onnx.probabilities), initial=0.0)),
        "min_force_kN_max_abs": float(np.max(
            np.abs(original.min_force_kN - onnx.min_force_kN), initial=0.0)),
    }


def _onnx_checks(test: Examples, lightgbm_model, lightgbm_export, gru_model, gru_export) -> dict:
    checks = {"gru": _onnx_difference(gru_model.predict(test),
                                      GruOnnxModel(gru_export.paths[0]).predict(test))}
    if lightgbm_export is not None:
        checks["lightgbm"] = _onnx_difference(lightgbm_model.predict(test),
                                              LightGbmOnnxModel(lightgbm_export).predict(test))
    return checks


def _examples_summary(examples: Examples) -> dict:
    """Example, class and weight counts of one share (training inputs, not scores)."""
    classes = Counter(ContactClass(int(code)).name for code in examples.labels)
    weights = Counter(f"{float(weight):g}" for weight in examples.weights)
    return {"examples": examples.count, "classes": dict(sorted(classes.items())),
            "weights": dict(sorted(weights.items()))}


def _share_summary(episodes: list[Episode], split: Split) -> dict:
    """Bases, episodes and base runs per share."""
    summary = {}
    for name in ("train", "validation", "test", "ood_level", "ood_roll"):
        metas = [episodes[i].meta for i in getattr(split, name)]
        base_runs = [m for m in metas if m.get("episode_id") == m.get("base_id")]
        summary[name] = {"bases": sorted({str(m.get("base_id")) for m in metas}),
                         "episodes": len(metas) - len(base_runs), "base_runs": len(base_runs)}
    return summary


def _tag_summary(episodes: list[Episode], split: Split,
                 tags: dict[str, EpisodeTags] | None) -> dict | None:
    """Tagged runs and the share each falls in."""
    if tags is None:
        return None
    share_of = {}
    for name in ("train", "validation", "test", "ood_level", "ood_roll"):
        for index in getattr(split, name):
            share_of[str(episodes[index].meta.get("episode_id"))] = name
    runs = {run: {"plant_rod_collapse_windows_s": [list(w) for w in tag.rod_collapse_windows_s],
                  "reapproach_pingpong": tag.is_reapproach_pingpong,
                  "plant_release_rod_steps": len(tag.release_steps),
                  "share": share_of.get(run)}
            for run, tag in sorted(tags.items())}
    per_share = Counter()
    for entry in runs.values():
        per_share[(entry["share"], "release_steps")] += entry["plant_release_rod_steps"]
        per_share[(entry["share"], "rod_collapse")] += len(entry["plant_rod_collapse_windows_s"])
        per_share[(entry["share"], "pingpong")] += int(entry["reapproach_pingpong"])
    return {"runs": runs,
            "per_share": {f"{share}:{kind}": count for (share, kind), count in
                          sorted(per_share.items(), key=str)}}


def _release_step_effect(examples: Examples, episodes: list[Episode],
                         tags: dict[str, EpisodeTags] | None) -> dict | None:
    """H-S8-4 (3): examples inside a ``plant_release_rod_step`` window, and whether their
    weight changed (only when a channel uses one pressure sensor alone)."""
    if tags is None:
        return None
    inside = np.zeros(examples.count, dtype=bool)
    for index, episode in enumerate(episodes):
        rows = release_step_rows(episode, tags).any(axis=1)
        in_record = examples.record_index == index
        inside[in_record] = rows[examples.row[in_record]]
    return {"individual_pressure_channels": list(INDIVIDUAL_PRESSURE_CHANNELS),
            "uses_individual_pressures": uses_individual_pressures(),
            "train_examples_in_windows": int(inside.sum()),
            "train_weights_set_to_0_by_tag": int(inside.sum()) if uses_individual_pressures()
            else 0}


def _history_count(episodes: list[Episode]) -> dict[str, int]:
    """Branched episodes with and without a base-run window history (:func:`branch_history`)."""
    bases = [e for e in episodes if e.meta.get("episode_id") == e.meta.get("base_id")]
    branched = [e for e in episodes if e.meta.get("episode_id") != e.meta.get("base_id")]
    with_history = sum(branch_history(e, bases) is not None for e in branched)
    return {"base_runs": len(bases), "branched": len(branched),
            "branched_with_base_history": with_history}


def _evaluation_sets(episodes, split, judged) -> dict[str, list[Episode]]:
    sets = {"test": _pick(episodes, split.test)}
    for label, field_name in OOD_SETS:
        indices = getattr(split, field_name)
        if indices:
            sets[label] = _pick(episodes, indices)
    if judged:
        sets[JUDGED_SET] = judged
    return sets


def _score_model(model, sets, masks, tags, latency, latency_note) -> dict:
    scores = {label: score_set(set_episodes, model.predict, _settings_for, masks, tags)
              for label, set_episodes in sets.items()}
    ood = {label: scores[label] for label, _ in OOD_SETS if label in scores}
    test = scores["test"]
    result = {
        "test": test.to_dict(),
        "out_of_distribution": {k: v.to_dict() for k, v in ood.items()},
        "latency": latency.__dict__,
        "latency_note": latency_note,
        "verdict_rows": verdict_rows(test, latency.p99_ms, latency.model_bytes, ood),
    }
    if JUDGED_SET in scores:
        judged = scores[JUDGED_SET]
        result["judged_cases"] = judged.to_dict()
        result["judged_rows"] = verdict_rows(judged, None, None)
    return result


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--episodes", help="folder of episode npz files")
    source.add_argument("--synthetic", help="BASESxEPISODES synthetic smoke set, e.g. 12x4")
    parser.add_argument("--out", required=True, help="output folder")
    parser.add_argument("--epochs", type=int, default=GruSettings().epochs)
    parser.add_argument("--rounds", type=int, default=None,
                        help="LightGBM rounds (default: the preset's)")
    parser.add_argument("--seed", type=int, default=SPLIT_SEED, help="split seed")
    parser.add_argument("--ml-masks", help="verify_S8ML.json whose ml_masks (FAULT entry .. "
                        "run end) are left out of training and scoring; also the tag record")
    parser.add_argument("--tags-dir", help="folder of the rev. 51 control results "
                        "(s8_ml_rev51_liftoff_rod.json, s8_ml_rev51_reapp_scan.json), used "
                        "when the judge record has no tags")
    parser.add_argument("--release-scan", help="hydraulics h_s8_4_release_scan.json "
                        "(releases_big -> plant_release_rod_step tag)")
    parser.add_argument("--judged-episodes", help="folder of judged-case episode npz files, "
                        "scored as an extra set (never trained on)")
    parser.add_argument("--lgbm-preset", choices=("regularized", "legacy"),
                        default="regularized", help="LightGBM leaf regularisation: "
                        "'legacy' = LightGBM defaults (before the fix)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    episodes = _load_episodes(args)
    judged = _load_folder(Path(args.judged_episodes)) if args.judged_episodes else []
    masks = load_ml_masks(Path(args.ml_masks)) if args.ml_masks else None
    tags = _load_tags(args)
    split = split_by_base([e.meta for e in episodes], seed=args.seed)
    train = build_examples(_pick(episodes, split.train), masks=masks, tags=tags)
    validation = build_examples(_pick(episodes, split.validation), masks=masks, tags=tags)
    crawler_counts = count_by_crawler_contact(e.meta for e in episodes)
    print(f"episodes {len(episodes)}, examples train {train.count} valid {validation.count}")
    print(f"episodes per crawler contact model: {crawler_counts}")

    gru_settings = GruSettings(epochs=args.epochs)
    base_lightgbm = LightGbmSettings.legacy() if args.lgbm_preset == "legacy" else (
        LightGbmSettings())
    rounds = base_lightgbm.rounds if args.rounds is None else args.rounds
    lightgbm_settings = dataclasses.replace(base_lightgbm, rounds=rounds)
    release_effect = _release_step_effect(train, _pick(episodes, split.train), tags)
    lightgbm_model = train_lightgbm(train, validation, lightgbm_settings)
    lightgbm_model.save(out)
    lightgbm_export = _export_lightgbm(lightgbm_model, out)
    print(f"LightGBM trees: classifier {lightgbm_model.classifier.num_trees()}, "
          f"regressor {lightgbm_model.regressor.num_trees()} "
          f"({time.perf_counter() - started:.0f} s)")
    gru_model = train_gru(train, validation, gru_settings)
    gru_export = export_gru_onnx(gru_model, train, out / "contact_gru.onnx")
    print(f"GRU ONNX exporter: {gru_export.exporter}"
          + (f" (fallback: {gru_export.fallback_reason})" if gru_export.fallback_reason else "")
          + f" ({time.perf_counter() - started:.0f} s)")

    sets = _evaluation_sets(episodes, split, judged)
    test_examples = build_examples(sets["test"], masks=masks, tags=tags)
    report: dict = {
        "spec": "s6_control_spec.md rev. 39 205, rev. 51 223.2; P-S8-2, P-S8-18",
        "source": "synthetic smoke (not training data)" if args.synthetic else args.episodes,
        "command": " ".join(sys.argv),
        "ml_masks": {"file": args.ml_masks, "runs": len(masks or {})},
        "tags": _tag_summary(episodes, split, tags),
        "release_step_effect": release_effect,
        "lightgbm_preset": args.lgbm_preset,
        "dataset": {"episodes": len(episodes),
                    "episodes_per_crawler_contact": crawler_counts,
                    "window_history": _history_count(episodes),
                    "judged_episodes": [str(e.meta.get("episode_id")) for e in judged],
                    "train": _examples_summary(train),
                    "validation": _examples_summary(validation),
                    "test": _examples_summary(test_examples)},
        "split": split.to_dict(),
        "shares": _share_summary(episodes, split),
        "seeds": {"split": split.seed, "gru": gru_settings.seed,
                  "lightgbm": lightgbm_settings.seed,
                  "synthetic": SYNTHETIC_SEED if args.synthetic else None},
        "settings": {"gru": gru_settings.__dict__, "lightgbm": lightgbm_settings.__dict__},
        "training": {"lightgbm_trees": {"classifier": lightgbm_model.classifier.num_trees(),
                                        "regressor": lightgbm_model.regressor.num_trees()}},
        "gru_device": gru_model.device,
        "onnx": {
            "gru": _export_meta(gru_export),
            "lightgbm": _export_meta(lightgbm_export),
            "difference_on_test": _onnx_checks(test_examples, lightgbm_model, lightgbm_export,
                                               gru_model, gru_export),
        },
        "models": {},
    }
    lightgbm_native = lightgbm_latency(lightgbm_model, test_examples)
    latencies = {
        "lightgbm": (lightgbm_native if lightgbm_export is None
                     else lightgbm_onnx_latency(lightgbm_export, test_examples)),
        "gru": onnx_latency(gru_export.paths[0], test_examples),
    }
    latency_notes = {
        "lightgbm": ("native LightGBM (onnxmltools unavailable)" if lightgbm_export is None
                     else "onnxruntime CPU, 1 thread, 4 legs per call, features included"),
        "gru": "onnxruntime CPU, 1 thread, 4 legs per call",
    }
    del train, validation, test_examples
    for name, model in (("lightgbm", lightgbm_model), ("gru", gru_model)):
        report["models"][name] = _score_model(model, sets, masks, tags, latencies[name],
                                              latency_notes[name])
        print(f"{name} scored ({time.perf_counter() - started:.0f} s)")
    report["models"]["lightgbm"]["latency_native"] = lightgbm_native.__dict__
    report["wall_s"] = time.perf_counter() - started
    (out / "report.json").write_text(json.dumps(report, indent=1, default=str),
                                     encoding="utf-8")
    print(f"report: {out / 'report.json'} ({report['wall_s']:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
