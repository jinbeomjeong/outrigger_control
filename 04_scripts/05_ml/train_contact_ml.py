"""Train and score the ground-contact ML candidates against the replayed J_C (P-S8-2).

Spec ``00_docs/04_control/s6_control_spec.md`` rev. 39 205. Runs in the ML environment only:

    C:\\ProgramData\\miniforge3\\envs\\pytorch_214_cuda_python_313\\python.exe -I \\
        04_scripts/05_ml/train_contact_ml.py --episodes <folder of episode npz> --out <folder>
    ... --synthetic 12x4 --out <folder>      # pipeline smoke on synthetic episodes only

Episode npz files come from ``build_contact_episodes.py`` (Chrono environment); this process
never imports pychrono (205.4: no shared process). Outputs in ``--out``: ``report.json``
(dataset summary with the episode count per crawler contact model, split, seeds, set scores,
E1-E6 rows, latency, ONNX exporter and ONNX-vs-model check), ``lgbm_*.txt``, ``lgbm_*.onnx``,
``contact_gru.onnx``. E5 uses the ONNX latency of both models; the native LightGBM latency is
kept as a reference.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("MKL_THREADING_LAYER", "TBB")  # torch + MKL numpy (CLAUDE.md)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "03_src"))

import numpy as np  # noqa: E402

from outrigger_sim.contact_episode import (  # noqa: E402
    Episode,
    count_by_crawler_contact,
    load_episode,
)
from outrigger_sim.control.contact_replay import ReplaySettings  # noqa: E402
from outrigger_sim.ml.dataset import Examples, build_examples, load_ml_masks  # noqa: E402
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
from outrigger_sim.ml.split import SPLIT_SEED, split_by_base  # noqa: E402
from outrigger_sim.ml.synthetic import synthetic_cases, synthetic_episode  # noqa: E402

SYNTHETIC_SEED = 20261024


def _load_episodes(args: argparse.Namespace) -> list[Episode]:
    if args.synthetic:
        bases, per_base = (int(part) for part in args.synthetic.lower().split("x"))
        return [synthetic_episode(case)
                for case in synthetic_cases(bases, per_base, SYNTHETIC_SEED)]
    paths = sorted(Path(args.episodes).glob("*.npz"))
    if not paths:
        raise SystemExit(f"no episode npz in {args.episodes}")
    return [load_episode(path) for path in paths]


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--episodes", help="folder of episode npz files")
    source.add_argument("--synthetic", help="BASESxEPISODES synthetic smoke set, e.g. 12x4")
    parser.add_argument("--out", required=True, help="output folder")
    parser.add_argument("--epochs", type=int, default=GruSettings().epochs)
    parser.add_argument("--rounds", type=int, default=LightGbmSettings().rounds)
    parser.add_argument("--seed", type=int, default=SPLIT_SEED, help="split seed")
    parser.add_argument("--ml-masks", help="verify_S8ML.json whose ml_masks (FAULT entry .. "
                        "run end) are left out of training and scoring")
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    episodes = _load_episodes(args)
    masks = load_ml_masks(Path(args.ml_masks)) if args.ml_masks else None
    split = split_by_base([e.meta for e in episodes], seed=args.seed)
    train = build_examples(_pick(episodes, split.train), masks=masks)
    validation = build_examples(_pick(episodes, split.validation), masks=masks)
    crawler_counts = count_by_crawler_contact(e.meta for e in episodes)
    print(f"episodes {len(episodes)}, examples train {train.count} valid {validation.count}")
    print(f"episodes per crawler contact model: {crawler_counts}")

    lightgbm_model = train_lightgbm(train, validation, LightGbmSettings(rounds=args.rounds))
    lightgbm_model.save(out)
    lightgbm_export = _export_lightgbm(lightgbm_model, out)
    gru_model = train_gru(train, validation, GruSettings(epochs=args.epochs))
    gru_export = export_gru_onnx(gru_model, train, out / "contact_gru.onnx")
    print(f"GRU ONNX exporter: {gru_export.exporter}"
          + (f" (fallback: {gru_export.fallback_reason})" if gru_export.fallback_reason else ""))

    test_episodes = _pick(episodes, split.test)
    test_examples = build_examples(test_episodes, masks=masks)
    report: dict = {
        "spec": "s6_control_spec.md rev. 39 205; P-S8-2",
        "source": "synthetic smoke (not training data)" if args.synthetic else args.episodes,
        "ml_masks": {"file": args.ml_masks, "runs": len(masks or {})},
        "dataset": {"episodes": len(episodes),
                    "episodes_per_crawler_contact": crawler_counts},
        "split": split.to_dict(),
        "seeds": {"split": split.seed, "train": GruSettings().seed,
                  "synthetic": SYNTHETIC_SEED if args.synthetic else None},
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
    for name, model in (("lightgbm", lightgbm_model), ("gru", gru_model)):
        test_scores = score_set(test_episodes, model.predict, _settings_for, masks)
        ood = {
            label: score_set(_pick(episodes, indices), model.predict, _settings_for, masks)
            for label, indices in (("OOD-1 middle auger", split.ood_level),
                                   ("OOD-2 roll > 4.4 deg", split.ood_roll))
            if indices
        }
        latency = latencies[name]
        report["models"][name] = {
            "test": test_scores.to_dict(),
            "out_of_distribution": {k: v.to_dict() for k, v in ood.items()},
            "latency": latency.__dict__,
            "latency_note": latency_notes[name],
            "verdict_rows": verdict_rows(test_scores, latency.p99_ms, latency.model_bytes, ood),
        }
    report["models"]["lightgbm"]["latency_native"] = lightgbm_native.__dict__
    report["wall_s"] = time.perf_counter() - started
    (out / "report.json").write_text(json.dumps(report, indent=1, default=str),
                                     encoding="utf-8")
    print(f"report: {out / 'report.json'} ({report['wall_s']:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
