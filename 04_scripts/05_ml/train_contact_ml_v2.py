"""P-S8-19: multi-seed ground-contact ML evaluation with the rev. 52 rules (spec 232 / 233).

Rules (``00_docs/04_control/s6_control_spec.md`` rev. 52, U-S8-51 / U-S8-52):

* Reading basis (232, :mod:`outrigger_sim.ml.reading_basis`): the default verdict uses the
  corrected reading (+0.5 kN where the pad contact force is below 1.5 kN) for J_C and the
  same correction on the ML force features; the recorded reading is a record row, the upper
  bound ``F_s - m g`` a sensitivity row. "Corrected features" row: ML misses raw -> corrected
  against J_C raw -> corrected ("Chrono bias dependence" when ML grows more).
* E2 conservative regression (233): lower 5 % quantile (GRU pinball loss, LightGBM
  ``quantile`` objective); the quantile is the ML load estimate. No constant margin.
* Decision level (233): picked on the validation share before the test share is scored
  (validation ML misses <= validation J_C misses, fewest false action flags).
* Seeds (233): split fixed, five model seeds; E1 is judged on the worst seed, the other rows
  give mean / min / max.
* E / N groups (233): the control-3 gate records (p1r, rest, CB, MLJ) replayed open loop; E1's
  second condition is "ML misses 0" there, on every seed.

Training data and tags are unchanged (``ml_main_20261025_090131/ml_dataset``). Runs in the ML
environment (torch on CUDA):

    C:\\ProgramData\\miniforge3\\envs\\pytorch_214_cuda_python_313\\python.exe -I \\
        04_scripts/05_ml/train_contact_ml_v2.py --episodes <ml_dataset> \\
        --judged-episodes <ml_dataset_mlj> --en-episodes <E / N episode folder> \\
        --ml-masks <verify_S8ML.json> --tags-dir 06_analysis/02_control/s8 \\
        --release-scan 06_analysis/03_hydraulic/s8/h_s8_4_release_scan.json \\
        --out <folder> [--src <source tree>] [--seeds 5] [--quick]

``--src`` imports ``outrigger_sim`` from another tree (a copy whose ``control/`` is pinned to the
committed judge path). ``--quick`` trains one seed for two epochs on a few episodes (pipeline
check only). Output: ``<out>/report.json`` and per seed ``<out>/seed_<k>/`` model files.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("MKL_THREADING_LAYER", "TBB")  # torch + MKL numpy (CLAUDE.md)
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")  # deterministic cuBLAS (GRU seed)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_OPTION = "--src"


def _source_root(argv: list[str]) -> Path:
    """The ``--src`` tree (default ``03_src``); read before ``outrigger_sim`` is imported."""
    if SOURCE_OPTION in argv:
        position = argv.index(SOURCE_OPTION)
        return Path(argv[position + 1]).resolve()
    return PROJECT_ROOT / "03_src"


SOURCE_ROOT = _source_root(sys.argv[1:])
sys.path.insert(0, str(SOURCE_ROOT))

import argparse  # noqa: E402
import dataclasses  # noqa: E402
import gc  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402
from collections.abc import Sequence  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402
from typing import Any  # noqa: E402

import numpy as np  # noqa: E402

from outrigger_sim.contact_episode import Episode, load_episode  # noqa: E402
from outrigger_sim.control.contact_replay import ReplaySettings  # noqa: E402
from outrigger_sim.ml.dataset import (  # noqa: E402
    EpisodeTags,
    Examples,
    MlMask,
    build_examples,
    load_episode_tags,
    load_ml_masks,
)
from outrigger_sim.ml.evaluate import (  # noqa: E402
    ExampleKeys,
    ScoringContext,
    SetScores,
    ThresholdChoice,
    episode_detections,
    ml_judgements,
    prepare_scoring,
    quantile_coverage,
    score_prediction,
    select_threshold,
    verdict_rows,
)
from outrigger_sim.ml.models import (  # noqa: E402
    GruSettings,
    LightGbmSettings,
    Prediction,
    export_gru_onnx,
    export_lightgbm_onnx,
    lightgbm_onnx_latency,
    onnx_latency,
    train_gru,
    train_lightgbm,
)
from outrigger_sim.ml.reading_basis import (  # noqa: E402
    RATCHET_CONTACT_LIMIT_N,
    RATCHET_CORRECTION_N,
    ReadingBasis,
    corrected_sample_count,
    pad_record_at_samples,
    pads_path,
    with_reading_basis,
)
from outrigger_sim.ml.split import SPLIT_SEED, split_by_base  # noqa: E402

LOWER_QUANTILE = 0.05
"""E2 conservative regression: lower 5 % quantile (spec rev. 52 233, 236)."""
FIRST_MODEL_SEED = 20261024
"""Seed of model 0 (the rev. 51 seed); model ``k`` uses ``FIRST_MODEL_SEED + k``."""
DEFAULT_SEED_COUNT = 5
RECORD_THRESHOLD = 0.5
"""The old fixed level, kept as a record row only."""
MODEL_NAMES = ("gru", "lightgbm")
OOD_SETS = (("OOD-1 middle auger", "ood_level"), ("OOD-2 roll > 4.4 deg", "ood_roll"))
JUDGED_SET = "judged cases"
EN_SET = "E/N groups"
QUICK_BASES = 40
"""``--quick``: bases kept (with their branches) so that every share stays non-empty."""
EN_GROUP_PREFIXES = (("E", "E_"), ("N", "N_"), ("CB", "CB_"), ("MLJ", "MLJ_"))


# --- data ------------------------------------------------------------------------------------


@dataclass
class EpisodeSet:
    """One evaluation set on the three reading bases (same runs, same truth)."""

    name: str
    by_basis: dict[ReadingBasis, list[Episode]]
    corrected_samples: int
    """(sample, leg) readings the default correction changed."""


def _load_folder(folder: Path) -> list[Episode]:
    paths = sorted(folder.glob("*.npz"))
    if not paths:
        raise SystemExit(f"no episode npz in {folder}")
    return [load_episode(path) for path in paths]


def _episode_bases(episodes: Sequence[Episode]) -> tuple[dict[ReadingBasis, list[Episode]], int]:
    """Every episode on the three reading bases, from its case folder's 1 ms pad record."""
    by_basis: dict[ReadingBasis, list[Episode]] = {basis: [] for basis in ReadingBasis}
    corrected = 0
    for episode in episodes:
        contact_N, seal_limit_N = pad_record_at_samples(pads_path(episode, PROJECT_ROOT),
                                                        episode["t_s"])
        corrected += corrected_sample_count(contact_N)
        for basis in ReadingBasis:
            by_basis[basis].append(with_reading_basis(episode, basis, contact_N, seal_limit_N))
    return by_basis, corrected


def _episode_set(name: str, episodes: Sequence[Episode]) -> EpisodeSet:
    by_basis, corrected = _episode_bases(episodes)
    return EpisodeSet(name, by_basis, corrected)


def _settings_for(episode: Episode) -> ReplaySettings:
    return ReplaySettings.from_controller_meta(episode.meta["controller"], episode.F_min_N)


def _en_group(run: str) -> str:
    for group, prefix in EN_GROUP_PREFIXES:
        if run.startswith(prefix):
            return group
    return "other"


# --- models ----------------------------------------------------------------------------------


@dataclass
class TrainedModel:
    """One model of one seed and what was measured on it."""

    name: str
    seed: int
    model: Any
    export: Any
    latency: Any
    info: dict[str, Any] = field(default_factory=dict)


def _text_digest(text: str) -> str:
    """Short SHA-256 of a model string (shows whether two seeds gave the same booster)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _gru_settings(seed: int, epochs: int) -> GruSettings:
    return GruSettings(epochs=epochs, seed=seed, lower_quantile=LOWER_QUANTILE)


def _lightgbm_settings(seed: int, rounds: int | None) -> LightGbmSettings:
    settings = LightGbmSettings(seed=seed, lower_quantile=LOWER_QUANTILE)
    return settings if rounds is None else dataclasses.replace(settings, rounds=rounds)


def train_models(
    train: Examples, validation: Examples, seeds: Sequence[int], out: Path, epochs: int,
    rounds: int | None,
) -> list[TrainedModel]:
    """GRU and LightGBM per seed, each exported to ONNX with its CPU latency (E5)."""
    models = []
    latency_rows = validation.subset(np.arange(validation.count) < 4)
    for seed in seeds:
        folder = out / f"seed_{seed}"
        started = time.perf_counter()
        gru = train_gru(train, validation, _gru_settings(seed, epochs))
        gru_export = export_gru_onnx(gru, train, folder / "contact_gru.onnx")
        models.append(TrainedModel(
            "gru", seed, gru, gru_export, onnx_latency(gru_export.paths[0], latency_rows),
            {"device": gru.device, "exporter": gru_export.exporter,
             "train_s": time.perf_counter() - started}))
        started = time.perf_counter()
        lightgbm = train_lightgbm(train, validation, _lightgbm_settings(seed, rounds))
        lightgbm.save(folder)
        lightgbm_export = export_lightgbm_onnx(lightgbm, folder)
        models.append(TrainedModel(
            "lightgbm", seed, lightgbm, lightgbm_export,
            lightgbm_onnx_latency(lightgbm_export, latency_rows),
            {"trees": [booster.num_trees() for booster in lightgbm.boosters()],
             "model_sha256": [_text_digest(b.model_to_string()) for b in lightgbm.boosters()],
             "train_s": time.perf_counter() - started}))
        print(f"seed {seed}: trained ({time.perf_counter() - started:.0f} s for LightGBM)",
              flush=True)
    return models


# --- scoring ---------------------------------------------------------------------------------


@dataclass
class ScoredSet:
    """Predictions per ML basis and contexts per J_C basis of one evaluation set."""

    name: str
    predictions: dict[ReadingBasis, list[Prediction]]
    """Per ML-feature basis, one prediction per trained model (same order)."""
    contexts: dict[ReadingBasis, ScoringContext]
    """Per J_C reading basis."""
    keys: ExampleKeys
    episode_count: int


def _keys_equal(left: ExampleKeys, right: ExampleKeys) -> bool:
    return all(np.array_equal(getattr(left, name), getattr(right, name))
               for name in ("labels", "record_index", "row", "leg"))


def score_inputs(
    episode_set: EpisodeSet,
    models: Sequence[TrainedModel],
    ml_bases: Sequence[ReadingBasis],
    jc_bases: Sequence[ReadingBasis],
    masks: dict[str, MlMask] | None,
    tags: dict[str, EpisodeTags] | None,
) -> ScoredSet:
    """Predict every model on the ML bases and replay J_C on the J_C bases (examples are
    built one basis at a time and dropped after prediction)."""
    predictions: dict[ReadingBasis, list[Prediction]] = {}
    contexts: dict[ReadingBasis, ScoringContext] = {}
    keys = None
    for basis in dict.fromkeys([*ml_bases, *jc_bases]):
        episodes = episode_set.by_basis[basis]
        examples = build_examples(episodes, masks=masks, tags=tags)
        basis_keys = ExampleKeys.of(examples)
        if keys is None:
            keys = basis_keys
        elif not _keys_equal(keys, basis_keys):
            raise RuntimeError(f"{episode_set.name}: examples differ between reading bases")
        if basis in ml_bases:
            predictions[basis] = [trained.model.predict(examples) for trained in models]
        if basis in jc_bases:
            contexts[basis] = prepare_scoring(episodes, examples, _settings_for, masks, tags)
        del examples
        gc.collect()
    episode_count = len(episode_set.by_basis[ReadingBasis.RAW])
    return ScoredSet(episode_set.name, predictions, contexts, keys, episode_count)


def _score(scored: ScoredSet, model_index: int, ml_basis: ReadingBasis,
           jc_basis: ReadingBasis, threshold: float) -> SetScores:
    prediction = scored.predictions[ml_basis][model_index]
    return score_prediction(scored.contexts[jc_basis], prediction, threshold)


def _miss_row(scores: SetScores) -> dict[str, Any]:
    ml, jc = scores.ml, scores.combined
    return {"episodes": ml.episode_count, "ML_missed": ml.missed,
            "ML_upper_95": ml.missed_upper_95, "J_C_missed": jc.missed,
            "J_C_upper_95": jc.missed_upper_95, "ML_late": ml.late, "J_C_late": jc.late,
            "ML_false_action_flags": ml.false_action_flags,
            "J_C_false_action_flags": jc.false_action_flags,
            "passed": ml.missed_upper_95 <= jc.missed_upper_95 + 1e-12}


def _bias_dependence_row(raw: SetScores, corrected: SetScores) -> dict[str, Any]:
    """Spec 232 "corrected features": ML misses raw -> corrected against J_C's change."""
    ml_change = corrected.ml.missed - raw.ml.missed
    jc_change = corrected.combined.missed - raw.combined.missed
    return {"ML_missed_raw": raw.ml.missed, "ML_missed_corrected": corrected.ml.missed,
            "J_C_missed_raw": raw.combined.missed,
            "J_C_missed_corrected": corrected.combined.missed,
            "ML_change": ml_change, "J_C_change": jc_change,
            "chrono_bias_dependent": ml_change > jc_change}


def _prediction_shift(scored: ScoredSet, model_index: int) -> dict[str, float]:
    """Largest change of the ML outputs when the features move from raw to corrected."""
    raw = scored.predictions[ReadingBasis.RAW][model_index]
    corrected = scored.predictions[ReadingBasis.CORRECTED][model_index]
    low_raw = raw.probabilities[:, 1] + raw.probabilities[:, 2]
    low_corrected = corrected.probabilities[:, 1] + corrected.probabilities[:, 2]
    return {
        "low_probability_max_abs": float(np.max(np.abs(low_corrected - low_raw), initial=0.0)),
        "load_estimate_kN_max_abs": float(np.max(
            np.abs(corrected.load_estimate_kN - raw.load_estimate_kN), initial=0.0)),
        "examples_changed": int(np.count_nonzero(
            np.abs(corrected.load_estimate_kN - raw.load_estimate_kN) > 1e-9)),
    }


def _jc_basis_effect(scored: ScoredSet) -> dict[str, dict[str, int]]:
    """Per non-raw J_C basis: decision and action flags that differ from the raw replay."""
    raw_records = scored.contexts[ReadingBasis.RAW].jc_records
    effect = {}
    for basis, context in scored.contexts.items():
        if basis is ReadingBasis.RAW:
            continue
        decision = action = 0
        for raw, other in zip(raw_records, context.jc_records, strict=True):
            decision += int(np.count_nonzero(raw.decision_flags != other.decision_flags))
            action += int(np.count_nonzero(raw.action_flags != other.action_flags))
        effect[str(basis)] = {"decision_flags_changed": decision,
                              "action_flags_changed": action}
    return effect


def _en_detail(scored: ScoredSet, model_index: int, threshold: float) -> dict[str, Any]:
    """Per E / N group misses and the missed truth episodes (default basis)."""
    context = scored.contexts[ReadingBasis.CORRECTED]
    prediction = scored.predictions[ReadingBasis.CORRECTED][model_index]
    ml_rows = episode_detections(context, ml_judgements(context, prediction, threshold))
    jc_rows = episode_detections(context, context.jc_records)
    groups: dict[str, dict[str, int]] = {}
    missed = []
    for ml_row, jc_row in zip(ml_rows, jc_rows, strict=True):
        group = groups.setdefault(_en_group(ml_row["run"]),
                                  {"episodes": 0, "ML_missed": 0, "J_C_missed": 0})
        group["episodes"] += 1
        is_ml_missed = ml_row["first_decision_s"] is None
        is_jc_missed = jc_row["first_decision_s"] is None
        group["ML_missed"] += int(is_ml_missed)
        group["J_C_missed"] += int(is_jc_missed)
        if is_ml_missed or is_jc_missed:
            missed.append({**{k: ml_row[k] for k in ("run", "leg", "t_on_s", "t_off_s",
                                                      "is_lift")},
                           "ML_first_decision_s": ml_row["first_decision_s"],
                           "J_C_first_decision_s": jc_row["first_decision_s"]})
    return {"groups": groups, "missed_episodes": missed}


def _choose_thresholds(validation: ScoredSet, models: Sequence[TrainedModel]
                       ) -> list[ThresholdChoice]:
    """Decision level per model from the validation share, default basis (233)."""
    context = validation.contexts[ReadingBasis.CORRECTED]
    choices = []
    for index, trained in enumerate(models):
        prediction = validation.predictions[ReadingBasis.CORRECTED][index]
        choice = select_threshold(context, prediction)
        print(f"{trained.name} seed {trained.seed}: threshold {choice.threshold} "
              f"(validation ML missed {choice.ml_missed} / J_C {choice.jc_missed}, "
              f"false flags {choice.false_action_flags})", flush=True)
        choices.append(choice)
    return choices


def score_model(
    index: int, trained: TrainedModel, threshold: float, sets: dict[str, ScoredSet],
) -> dict[str, Any]:
    """Every row of one model and seed (the threshold is already fixed)."""
    default = ReadingBasis.CORRECTED
    test = sets["test"]
    test_default = _score(test, index, default, default, threshold)
    test_raw = _score(test, index, ReadingBasis.RAW, ReadingBasis.RAW, threshold)
    ood = {label: _score(sets[label], index, default, default, threshold)
           for label, _ in OOD_SETS if label in sets}
    latency_ms = trained.latency.p99_ms
    result: dict[str, Any] = {
        "seed": trained.seed,
        "threshold": threshold,
        "test": test_default.to_dict(),
        "verdict_rows": verdict_rows(test_default, latency_ms, trained.latency.model_bytes, ood),
        "out_of_distribution": {label: scores.to_dict() for label, scores in ood.items()},
        "E1_rows": {
            "default_corrected": _miss_row(test_default),
            "record_raw": _miss_row(test_raw),
            "ML_raw_features_vs_J_C_corrected": _miss_row(
                _score(test, index, ReadingBasis.RAW, default, threshold)),
            "sensitivity_upper_bound": _miss_row(
                _score(test, index, ReadingBasis.UPPER_BOUND, ReadingBasis.UPPER_BOUND,
                       threshold)),
            "record_threshold_0.5": _miss_row(
                _score(test, index, default, default, RECORD_THRESHOLD)),
        },
        "corrected_features_row": {**_bias_dependence_row(test_raw, test_default),
                                   "prediction_shift": _prediction_shift(test, index)},
        "quantile_coverage": {
            "validation": quantile_coverage(sets["validation"].keys,
                                            sets["validation"].predictions[default][index],
                                            sets["validation"].contexts[default].F_min_N),
            "test": quantile_coverage(test.keys, test.predictions[default][index],
                                      test.contexts[default].F_min_N),
        },
        "latency": trained.latency.__dict__,
        "info": trained.info,
    }
    if JUDGED_SET in sets:
        judged = _score(sets[JUDGED_SET], index, default, default, threshold)
        result["judged_cases"] = _miss_row(judged)
    if EN_SET in sets:
        en = sets[EN_SET]
        en_default = _score(en, index, default, default, threshold)
        en_raw = _score(en, index, ReadingBasis.RAW, ReadingBasis.RAW, threshold)
        en_upper = _score(en, index, ReadingBasis.UPPER_BOUND, ReadingBasis.UPPER_BOUND,
                          threshold)
        result["en_groups"] = {
            "default_corrected": _miss_row(en_default),
            "record_raw": _miss_row(en_raw),
            "sensitivity_upper_bound": _miss_row(en_upper),
            "corrected_features_row": {**_bias_dependence_row(en_raw, en_default),
                                       "prediction_shift": _prediction_shift(en, index)},
            "M4_max_N": {"ML": en_default.ml.near_fmin_error_max_N,
                         "J_C": en_default.combined.near_fmin_error_max_N},
            "detail": _en_detail(en, index, threshold),
            "ML_missed_zero": en_default.ml.missed == 0,
        }
    return result


# --- aggregation -----------------------------------------------------------------------------


def _spread(values: Sequence[float | int | None]) -> dict[str, float | None]:
    finite = [float(v) for v in values if v is not None]
    if not finite:
        return {"mean": None, "min": None, "max": None}
    return {"mean": float(np.mean(finite)), "min": min(finite), "max": max(finite)}


def _row_value(rows: list[dict], item: str) -> dict | float | None:
    for row in rows:
        if row["item"] == item:
            return row
    return None


def aggregate(per_seed: list[dict[str, Any]]) -> dict[str, Any]:
    """E1 on the worst seed (largest ML 95 % upper bound, then most misses); other rows as
    mean / min / max over the seeds."""
    e1 = [run["E1_rows"]["default_corrected"] for run in per_seed]
    worst_index = max(range(len(e1)), key=lambda i: (e1[i]["ML_upper_95"], e1[i]["ML_missed"]))
    worst = per_seed[worst_index]
    en_zero = [run["en_groups"]["ML_missed_zero"] for run in per_seed if "en_groups" in run]
    en_missed = [run["en_groups"]["default_corrected"]["ML_missed"] for run in per_seed
                 if "en_groups" in run]
    e1_first = e1[worst_index]["passed"]
    e1_second = all(en_zero) if en_zero else None
    summary: dict[str, Any] = {
        "E1": {
            "worst_seed": worst["seed"],
            "worst_seed_row": e1[worst_index],
            "first_condition_passed": e1_first,
            "second_condition_EN_ML_missed_zero_all_seeds": e1_second,
            "EN_ML_missed_per_seed": en_missed,
            "passed": bool(e1_first and e1_second) if e1_second is not None else None,
            "ML_missed_per_seed": [row["ML_missed"] for row in e1],
            "ML_upper_95_per_seed": [row["ML_upper_95"] for row in e1],
            "median_ML_missed": float(np.median([row["ML_missed"] for row in e1])),
            "J_C_missed": e1[0]["J_C_missed"],
            "J_C_upper_95": e1[0]["J_C_upper_95"],
        },
        "thresholds": [run["threshold"] for run in per_seed],
    }
    rows = {}
    for item in ("E2", "E3", "E4", "E5"):
        values = [_row_value(run["verdict_rows"], item) for run in per_seed]
        rows[item] = {"passed_per_seed": [row["passed"] if row else None for row in values],
                      "values_per_seed": [row["value"] if row else None for row in values]}
    rows["E2"]["ML_M4_max_N"] = _spread(
        [v["ML_M4_max_N"] for v in rows["E2"]["values_per_seed"] if v])
    rows["E2"]["J_C_M4_max_N"] = rows["E2"]["values_per_seed"][0]["J_C_M4_max_N"]
    rows["E4"]["ECE"] = _spread(rows["E4"]["values_per_seed"])
    rows["E5"]["p99_ms"] = _spread([v["p99_ms"] for v in rows["E5"]["values_per_seed"]])
    test_scores = [run["test"]["ML"] for run in per_seed]
    rows["E3"]["ML_median_delay_s"] = _spread([s["M3_median_delay_s"] for s in test_scores])
    rows["E3"]["ML_false_action_flags"] = _spread([s["M2_false_action_flags"]
                                                   for s in test_scores])
    rows["E3"]["J_C"] = {"median_delay_s": per_seed[0]["test"]["J_C"]["M3_median_delay_s"],
                         "false_action_flags": per_seed[0]["test"]["J_C"][
                             "M2_false_action_flags"]}
    coverage = [run["quantile_coverage"] for run in per_seed]
    rows["E2"]["quantile_coverage"] = {
        share: {key: _spread([c[share][key] for c in coverage])
                for key in ("all_weighted", "near_F_min_band")}
        for share in ("validation", "test")}
    summary["rows"] = rows
    summary["E6"] = {
        label: _spread([run["out_of_distribution"][label]["ML"]["M1_missed"]
                        for run in per_seed if label in run["out_of_distribution"]])
        for label, _ in OOD_SETS}
    summary["corrected_features_dependent_seeds"] = sum(
        run["corrected_features_row"]["chrono_bias_dependent"] for run in per_seed)
    return summary


# --- main ------------------------------------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--episodes", required=True, help="training episode folder")
    parser.add_argument("--judged-episodes", help="MLJ judged-case episode folder")
    parser.add_argument("--en-episodes", help="control-3 E / N group episode folder")
    parser.add_argument("--ml-masks", required=True, help="verify_S8ML.json (masks, tags)")
    parser.add_argument("--tags-dir", required=True, help="rev. 51 control result folder")
    parser.add_argument("--release-scan", help="h_s8_4_release_scan.json")
    parser.add_argument("--out", required=True)
    parser.add_argument(SOURCE_OPTION, help="source tree to import outrigger_sim from")
    parser.add_argument("--seeds", type=int, default=DEFAULT_SEED_COUNT)
    parser.add_argument("--epochs", type=int, default=GruSettings().epochs)
    parser.add_argument("--rounds", type=int, default=None, help="LightGBM rounds")
    parser.add_argument("--quick", action="store_true", help="pipeline check only")
    return parser.parse_args(argv)


def _shares(episodes: list[Episode], split) -> dict[str, list[Episode]]:
    shares = {name: [episodes[i] for i in getattr(split, name)]
              for name in ("train", "validation", "test")}
    for label, field_name in OOD_SETS:
        shares[label] = [episodes[i] for i in getattr(split, field_name)]
    return shares


def _quick_subset(episodes: list[Episode]) -> list[Episode]:
    """The episodes of the first :data:`QUICK_BASES` bases (base runs with their branches)."""
    bases = sorted({str(e.meta.get("base_id")) for e in episodes})[:QUICK_BASES]
    return [e for e in episodes if str(e.meta.get("base_id")) in bases]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    episodes = _load_folder(Path(args.episodes))
    if args.quick:
        episodes = _quick_subset(episodes)
    masks = load_ml_masks(Path(args.ml_masks))
    tags = load_episode_tags(Path(args.ml_masks), Path(args.tags_dir),
                             Path(args.release_scan) if args.release_scan else None)
    split = split_by_base([e.meta for e in episodes], seed=SPLIT_SEED)
    shares = _shares(episodes, split)
    seed_count = 1 if args.quick else args.seeds
    seeds = [FIRST_MODEL_SEED + k for k in range(seed_count)]
    epochs = 2 if args.quick else args.epochs

    train = build_examples(shares["train"], masks=masks, tags=tags)
    validation_raw = build_examples(shares["validation"], masks=masks, tags=tags)
    print(f"episodes {len(episodes)}, train {train.count}, validation {validation_raw.count}",
          flush=True)
    models = train_models(train, validation_raw, seeds, out, epochs, args.rounds)
    del train, validation_raw
    gc.collect()
    print(f"trained {len(models)} models ({time.perf_counter() - started:.0f} s)", flush=True)

    default, raw, upper = ReadingBasis.CORRECTED, ReadingBasis.RAW, ReadingBasis.UPPER_BOUND
    plans: list[tuple[str, list[Episode], list, list]] = [
        ("validation", shares["validation"], [default], [default]),
        ("test", shares["test"], [default, raw, upper], [default, raw, upper]),
    ]
    for label, _ in OOD_SETS:
        if shares[label]:
            plans.append((label, shares[label], [default], [default]))
    if args.judged_episodes:
        plans.append((JUDGED_SET, _load_folder(Path(args.judged_episodes)), [default],
                      [default]))
    if args.en_episodes:
        plans.append((EN_SET, _load_folder(Path(args.en_episodes)), [default, raw, upper],
                      [default, raw, upper]))
    sets: dict[str, ScoredSet] = {}
    corrected_counts = {}
    for name, set_episodes, ml_bases, jc_bases in plans:
        episode_set = _episode_set(name, set_episodes)
        corrected_counts[name] = episode_set.corrected_samples
        sets[name] = score_inputs(episode_set, models, ml_bases, jc_bases, masks, tags)
        print(f"{name}: {sets[name].episode_count} episodes, {sets[name].keys.count} examples "
              f"({time.perf_counter() - started:.0f} s)", flush=True)

    # The decision level is fixed on the validation share before any test score is computed.
    choices = _choose_thresholds(sets["validation"], models)
    per_model: dict[str, list[dict[str, Any]]] = {name: [] for name in MODEL_NAMES}
    for index, (trained, choice) in enumerate(zip(models, choices, strict=True)):
        result = score_model(index, trained, choice.threshold, sets)
        result["threshold_choice"] = choice.to_dict()
        per_model[trained.name].append(result)
        print(f"{trained.name} seed {trained.seed} scored "
              f"({time.perf_counter() - started:.0f} s)", flush=True)

    report = {
        "spec": "s6_control_spec.md rev. 52 232 / 233; U-S8-51, U-S8-52; P-S8-19",
        "command": " ".join(sys.argv),
        "source_tree": str(SOURCE_ROOT),
        "quick": args.quick,
        "episodes": args.episodes,
        "judged_episodes": args.judged_episodes,
        "en_episodes": args.en_episodes,
        "en_runs": ([str(e.meta.get("episode_id")) for e in
                     sets[EN_SET].contexts[default].episodes] if EN_SET in sets else []),
        "seeds": {"split": SPLIT_SEED, "models": seeds},
        "reading_basis": {
            "default": str(default), "correction_N": RATCHET_CORRECTION_N,
            "contact_limit_N": RATCHET_CONTACT_LIMIT_N,
            "corrected_samples_per_set": corrected_counts,
            "J_C_flag_changes_against_raw": {
                name: _jc_basis_effect(scored) for name, scored in sets.items()
                if ReadingBasis.RAW in scored.contexts},
            "rows": {"default_corrected": "J_C corrected reading, ML corrected features",
                     "record_raw": "both on the recorded reading",
                     "ML_raw_features_vs_J_C_corrected": "ML recorded features, J_C "
                                                         "corrected reading",
                     "sensitivity_upper_bound": "lifted legs (N <= 0) read F_s - m g, both",
                     "record_threshold_0.5": "default basis, decision level 0.5"},
        },
        "settings": {"gru": dataclasses.asdict(_gru_settings(seeds[0], epochs)),
                     "lightgbm": dataclasses.asdict(_lightgbm_settings(seeds[0], args.rounds)),
                     "lower_quantile": LOWER_QUANTILE},
        "split": {name: len(items) for name, items in shares.items()},
        "per_model": per_model,
        "summary": {name: aggregate(results) for name, results in per_model.items()},
        "wall_s": time.perf_counter() - started,
    }
    (out / "report.json").write_text(json.dumps(report, indent=1, default=str),
                                     encoding="utf-8")
    print(f"report: {out / 'report.json'} ({report['wall_s']:.0f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
