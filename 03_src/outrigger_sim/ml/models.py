"""Ground-contact models: LightGBM baseline and a GRU network, ONNX export (spec 205.6).

Needs the ML environment ``pytorch_214_cuda_python_313`` (torch, lightgbm, onnx, onnxruntime).
Both models give, per leg and sample, class probabilities of {G, U, L} and the window minimum
of the rod force [kN] (the load estimate scored by M4).

Lower-quantile load estimate (spec rev. 52 233, U-S8-52, P-S8-19): with
``lower_quantile`` set (0.05 = lower 5 %), the GRU gets a second regression output trained with
the pinball loss and LightGBM a third booster with the ``quantile`` objective. The quantile then
is the load estimate (:attr:`Prediction.load_estimate_kN`, E2 and the P5 confirmation); the
point estimate stays as a record. No constant margin is subtracted anywhere.

ONNX (E5):

* GRU network: the torch default dynamo exporter (needs ``onnxscript``, opset 18); when it
  fails, the TorchScript exporter (``dynamo=False``, opset 17). :attr:`OnnxExport.exporter`
  says which one wrote the file.
* LightGBM: ``onnxmltools`` (opset 15, the converter's maximum), one file per booster. The
  features (:func:`tabular_features`) stay in numpy. ONNX trees compare in float32, so the
  thresholds are first rounded down to float32 (:func:`_booster_with_float32_thresholds`);
  for float32 features this keeps every split decision of the original booster.
"""

from __future__ import annotations

import logging
import time
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import lightgbm
import numpy as np
import torch
from numpy.typing import NDArray
from torch import nn

from outrigger_sim.ml.dataset import CLASS_COUNT, Examples, tabular_features

TRAIN_SEED = 20261024
DYNAMO_OPSET = 18
TORCHSCRIPT_OPSET = 17
LIGHTGBM_OPSET = 15
"""Highest opset the onnxmltools 1.16 LightGBM converter supports."""
MIN_BATCH_WEIGHT = 1e-12
"""Floor of a batch's weight sum in the GRU loss (a batch may hold only weight-0 rows)."""
ONNX_LEG_COUNT = 4
"""Rows per latency call: one control period's inference of the four legs (E5)."""
GRU_INPUT_NAMES = ("sequences", "context")
GRU_OUTPUT_NAME = "output"
LIGHTGBM_INPUT_NAME = "features"
LIGHTGBM_ONNX_FILES = ("lgbm_classifier.onnx", "lgbm_regressor.onnx")
LIGHTGBM_QUANTILE_ONNX_FILE = "lgbm_quantile.onnx"
THRESHOLD_PREFIX = "threshold="
"""Line of a LightGBM model string with a tree's split thresholds."""
TREE_SIZES_PREFIX = "tree_sizes="
DYNAMO_NOISE_WARNINGS = (
    r"The tensor attributes self\.gru\._flat_weights",
    r"# The axis name: batch will not be used",
    r"_check_is_size will be removed",
)
"""Regexes of torch-internal warnings the dynamo GRU export always raises (torch 2.14)."""

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Prediction:
    """Model output for a set of examples."""

    probabilities: NDArray[np.float64]
    """(N, 3) class probabilities."""
    min_force_kN: NDArray[np.float64]
    """(N,) predicted window minimum of the rod force (point estimate)."""
    lower_quantile_kN: NDArray[np.float64] | None = None
    """(N,) lower quantile of the window minimum; ``None`` = model without a quantile output."""

    @property
    def load_estimate_kN(self) -> NDArray[np.float64]:
        """The load estimate the judge uses: the lower quantile when present, else the point."""
        return self.min_force_kN if self.lower_quantile_kN is None else self.lower_quantile_kN


# --- LightGBM ------------------------------------------------------------------------------


@dataclass(frozen=True)
class LightGbmSettings:
    """Booster settings; the leaf regularisation keeps the rare U / L classes stable.

    With the LightGBM defaults (``min_sum_hessian_in_leaf`` 1e-3, no L2) the multiclass leaf
    values of a few U / L rows blew up after the second round on the main S8 batch (0.25 %
    U / L): the validation loss doubled and early stopping kept one round only.
    """

    num_leaves: int = 31
    learning_rate: float = 0.05
    rounds: int = 1000
    early_stopping_rounds: int = 30
    seed: int = TRAIN_SEED
    min_sum_hessian_in_leaf: float = 5.0
    lambda_l2: float = 10.0
    min_data_in_leaf: int = 100
    lower_quantile: float | None = None
    """Quantile level of the third booster (``objective="quantile"``); ``None`` = none."""

    @classmethod
    def legacy(cls) -> LightGbmSettings:
        """The settings before the regularisation (LightGBM defaults, 400 rounds)."""
        return cls(rounds=400, min_sum_hessian_in_leaf=1e-3, lambda_l2=0.0, min_data_in_leaf=20)


@dataclass
class LightGbmModel:
    classifier: lightgbm.Booster
    regressor: lightgbm.Booster
    quantile_regressor: lightgbm.Booster | None = None

    def predict(self, examples: Examples) -> Prediction:
        features = tabular_features(examples)
        quantile = None
        if self.quantile_regressor is not None:
            quantile = np.asarray(self.quantile_regressor.predict(features), dtype=float)
        return Prediction(
            np.asarray(self.classifier.predict(features), dtype=float).reshape(-1, CLASS_COUNT),
            np.asarray(self.regressor.predict(features), dtype=float),
            quantile,
        )

    def boosters(self) -> list[lightgbm.Booster]:
        """Classifier, regressor and (when trained) the quantile regressor."""
        boosters = [self.classifier, self.regressor]
        if self.quantile_regressor is not None:
            boosters.append(self.quantile_regressor)
        return boosters

    def save(self, folder: Path) -> list[Path]:
        folder.mkdir(parents=True, exist_ok=True)
        names = ["lgbm_classifier.txt", "lgbm_regressor.txt", "lgbm_quantile.txt"]
        paths = []
        for name, booster in zip(names, self.boosters(), strict=False):
            path = folder / name
            booster.save_model(str(path))
            paths.append(path)
        return paths


def train_lightgbm(
    train: Examples, validation: Examples, settings: LightGbmSettings | None = None
) -> LightGbmModel:
    """Multiclass classifier and min-force regressor on :func:`tabular_features`."""
    settings = settings or LightGbmSettings()
    common = {
        "num_leaves": settings.num_leaves,
        "learning_rate": settings.learning_rate,
        "seed": settings.seed,
        "min_sum_hessian_in_leaf": settings.min_sum_hessian_in_leaf,
        "lambda_l2": settings.lambda_l2,
        "min_data_in_leaf": settings.min_data_in_leaf,
        "deterministic": True,
        "num_threads": 4,
        "verbose": -1,
    }
    x_train, x_valid = tabular_features(train), tabular_features(validation)
    stop = [lightgbm.early_stopping(settings.early_stopping_rounds, verbose=False)]
    classifier = lightgbm.train(
        {**common, "objective": "multiclass", "num_class": CLASS_COUNT},
        lightgbm.Dataset(x_train, train.labels, weight=train.weights),
        settings.rounds,
        valid_sets=[lightgbm.Dataset(x_valid, validation.labels, weight=validation.weights)],
        callbacks=stop,
    )
    regressor = lightgbm.train(
        {**common, "objective": "regression"},
        lightgbm.Dataset(x_train, train.target_min_kN, weight=train.weights),
        settings.rounds,
        # Weighted like the classifier so that weight-0 rows (lift-off transient) do not steer
        # early stopping.
        valid_sets=[lightgbm.Dataset(x_valid, validation.target_min_kN,
                                     weight=validation.weights)],
        callbacks=stop,
    )
    quantile_regressor = None
    if settings.lower_quantile is not None:
        quantile_regressor = lightgbm.train(
            {**common, "objective": "quantile", "alpha": settings.lower_quantile},
            lightgbm.Dataset(x_train, train.target_min_kN, weight=train.weights),
            settings.rounds,
            valid_sets=[lightgbm.Dataset(x_valid, validation.target_min_kN,
                                         weight=validation.weights)],
            callbacks=stop,
        )
    return LightGbmModel(classifier, regressor, quantile_regressor)


# --- GRU network ---------------------------------------------------------------------------


class ContactGru(nn.Module):
    """GRU over the window + probe context -> 3 class logits, the min force [kN] and, with
    ``has_quantile``, its lower quantile [kN]."""

    def __init__(self, channel_count: int, context_count: int, hidden: int = 48,
                 has_quantile: bool = False) -> None:
        super().__init__()
        output_count = CLASS_COUNT + 1 + int(has_quantile)
        self.gru = nn.GRU(channel_count, hidden, batch_first=True)
        self.head = nn.Sequential(
            nn.Linear(hidden + context_count, hidden), nn.ReLU(), nn.Linear(hidden, output_count)
        )

    def forward(self, sequences: torch.Tensor, context: torch.Tensor) -> torch.Tensor:
        _, last_hidden = self.gru(sequences)
        return self.head(torch.cat([last_hidden[-1], context], dim=1))


@dataclass(frozen=True)
class GruSettings:
    hidden: int = 48
    epochs: int = 30
    batch_size: int = 512
    learning_rate: float = 2e-3
    regression_weight: float = 0.1
    """Loss weight of the min-force head (kN^2) against the class cross-entropy."""
    patience: int = 5
    seed: int = TRAIN_SEED
    device: str | None = None
    """``None`` = CUDA when available."""
    lower_quantile: float | None = None
    """Quantile level of the extra output (pinball loss); ``None`` = no quantile output."""
    quantile_weight: float = 1.0
    """Loss weight of the pinball term (kN) against the class cross-entropy (ASSUMPTION)."""


@dataclass
class GruModel:
    network: ContactGru
    device: str

    def predict(self, examples: Examples, batch_size: int = 4096) -> Prediction:
        self.network.eval()
        outputs = []
        with torch.no_grad():
            for start in range(0, examples.count, batch_size):
                part = slice(start, start + batch_size)
                out = self.network(
                    torch.from_numpy(examples.sequences[part]).to(self.device),
                    torch.from_numpy(examples.context[part]).to(self.device),
                )
                outputs.append(out.cpu().numpy())
        output_count = self.network.head[-1].out_features
        raw = np.concatenate(outputs) if outputs else np.zeros((0, output_count))
        return _prediction_from_raw(raw)


def _prediction_from_raw(raw: NDArray[np.floating]) -> Prediction:
    """Network output (logits of the 3 classes, min force [kN], optional lower quantile [kN])
    -> :class:`Prediction`."""
    logits = raw[:, :CLASS_COUNT]
    probabilities = np.exp(logits - logits.max(axis=1, keepdims=True))
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    quantile = None
    if raw.shape[1] > CLASS_COUNT + 1:
        quantile = raw[:, CLASS_COUNT + 1].astype(float)
    return Prediction(probabilities.astype(float), raw[:, CLASS_COUNT].astype(float), quantile)


def pinball_loss(predicted: torch.Tensor, targets: torch.Tensor, quantile: float
                 ) -> torch.Tensor:
    """Per-row quantile (pinball) loss: ``max(q (y - p), (q - 1)(y - p))``."""
    residual = targets - predicted
    return torch.maximum(quantile * residual, (quantile - 1.0) * residual)


def _gru_loss(output, labels, targets, weights, settings: GruSettings):
    class_loss = nn.functional.cross_entropy(output[:, :CLASS_COUNT], labels, reduction="none")
    regression_loss = (output[:, CLASS_COUNT] - targets) ** 2
    row_loss = class_loss + settings.regression_weight * regression_loss
    if settings.lower_quantile is not None:
        quantile_loss = pinball_loss(output[:, CLASS_COUNT + 1], targets, settings.lower_quantile)
        row_loss = row_loss + settings.quantile_weight * quantile_loss
    # A batch of only weight-0 rows (lift-off transient) would divide 0 by 0.
    total_weight = torch.sum(weights).clamp_min(MIN_BATCH_WEIGHT)
    return torch.sum(weights * row_loss) / total_weight


def _tensors(examples: Examples, device: str) -> list[torch.Tensor]:
    return [
        torch.from_numpy(array).to(device)
        for array in (examples.sequences, examples.context, examples.labels,
                      examples.target_min_kN, examples.weights)
    ]


def train_gru(
    train: Examples, validation: Examples, settings: GruSettings | None = None
) -> GruModel:
    """Weighted cross-entropy + weighted squared error; best validation epoch kept."""
    settings = settings or GruSettings()
    device = settings.device or ("cuda" if torch.cuda.is_available() else "cpu")
    # cuDNN picks GRU kernels by timing unless told otherwise; fixed kernels keep a rerun with
    # the same seed on the same GPU reproducible.
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.manual_seed(settings.seed)
    generator = torch.Generator().manual_seed(settings.seed)
    network = ContactGru(train.sequences.shape[2], train.context.shape[1], settings.hidden,
                         has_quantile=settings.lower_quantile is not None)
    network.to(device)
    optimizer = torch.optim.Adam(network.parameters(), lr=settings.learning_rate)
    train_tensors = _tensors(train, device)
    valid_tensors = _tensors(validation, device)
    best_loss, best_state, stale_epochs = np.inf, None, 0
    for _ in range(settings.epochs):
        network.train()
        order = torch.randperm(train.count, generator=generator).to(device)
        for start in range(0, train.count, settings.batch_size):
            batch = order[start:start + settings.batch_size]
            sequences, context, labels, targets, weights = (t[batch] for t in train_tensors)
            optimizer.zero_grad()
            loss = _gru_loss(network(sequences, context), labels, targets, weights, settings)
            loss.backward()
            optimizer.step()
        network.eval()
        with torch.no_grad():
            sequences, context, labels, targets, weights = valid_tensors
            valid_loss = float(_gru_loss(network(sequences, context), labels, targets, weights,
                                         settings))
        if valid_loss < best_loss - 1e-6:
            best_loss, stale_epochs = valid_loss, 0
            best_state = {k: v.detach().clone() for k, v in network.state_dict().items()}
        else:
            stale_epochs += 1
            if stale_epochs >= settings.patience:
                break
    if best_state is not None:
        network.load_state_dict(best_state)
    return GruModel(network, device)


# --- ONNX export ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OnnxExport:
    """ONNX files of one model and the exporter that wrote them."""

    paths: tuple[Path, ...]
    exporter: str
    """``"dynamo"`` or ``"torchscript"`` (GRU), ``"onnxmltools"`` (LightGBM)."""
    fallback_reason: str | None = None
    """Why the dynamo exporter was not used (``None`` = no fallback)."""

    @property
    def model_bytes(self) -> int:
        return sum(path.stat().st_size for path in self.paths)


def _export_gru_dynamo(network: ContactGru, sample: tuple[torch.Tensor, ...], path: Path) -> None:
    batch = torch.export.Dim("batch", min=1)
    with warnings.catch_warnings():
        # torch-internal notes on the GRU flat weights, the batch axis name and _check_is_size;
        # the result is checked against torch in test_ml_pipeline (batch 1 to 300).
        for message in DYNAMO_NOISE_WARNINGS:
            warnings.filterwarnings("ignore", message=message)
        program = torch.onnx.export(
            network, sample, dynamo=True, opset_version=DYNAMO_OPSET,
            # verbose=False: the progress lines carry emoji that a cp949 console cannot encode.
            verbose=False,
            input_names=list(GRU_INPUT_NAMES), output_names=[GRU_OUTPUT_NAME],
            dynamic_shapes={name: {0: batch} for name in GRU_INPUT_NAMES},
        )
        program.save(str(path), external_data=False)


def _export_gru_torchscript(
    network: ContactGru, sample: tuple[torch.Tensor, ...], path: Path
) -> None:
    with warnings.catch_warnings():
        # The exporter warns that a GRU traced at batch 4 may fail at other batch sizes; the
        # initial state is zero inside the graph and test_ml_pipeline compares ONNX with torch
        # at several batch sizes.
        warnings.filterwarnings("ignore", message="Exporting a model to ONNX with a batch_size")
        torch.onnx.export(
            network, sample, str(path), dynamo=False, opset_version=TORCHSCRIPT_OPSET,
            input_names=list(GRU_INPUT_NAMES), output_names=[GRU_OUTPUT_NAME],
            dynamic_axes={name: {0: "batch"} for name in (*GRU_INPUT_NAMES, GRU_OUTPUT_NAME)},
        )


def export_gru_onnx(
    model: GruModel, examples: Examples, path: Path, *, use_dynamo: bool = True
) -> OnnxExport:
    """ONNX file of the network on CPU (batch axis dynamic).

    Args:
        model: Trained network.
        examples: Source of the sample input (its first four rows).
        path: Output file.
        use_dynamo: Try the dynamo exporter first; ``False`` = TorchScript only.

    Returns:
        The written file and the exporter used; a dynamo failure is logged and falls back to
        the TorchScript exporter.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    network = model.network.to("cpu").eval()
    sample = (torch.from_numpy(examples.sequences[:ONNX_LEG_COUNT]),
              torch.from_numpy(examples.context[:ONNX_LEG_COUNT]))
    try:
        if use_dynamo:
            try:
                _export_gru_dynamo(network, sample, path)
                return OnnxExport((path,), "dynamo")
            except Exception as error:  # noqa: BLE001 - any exporter failure falls back
                reason = f"{type(error).__name__}: {str(error).splitlines()[0][:300]}"
                logger.warning("dynamo ONNX export failed (%s); using TorchScript", reason)
        else:
            reason = "dynamo disabled by the caller"
        _export_gru_torchscript(network, sample, path)
        return OnnxExport((path,), "torchscript", reason)
    finally:
        model.network.to(model.device)


def _float32_floor(values: NDArray[np.float64]) -> NDArray[np.float64]:
    """Largest float32 not above each value (as float64)."""
    rounded = values.astype(np.float32)
    is_above = rounded.astype(np.float64) > values
    rounded[is_above] = np.nextafter(rounded[is_above], np.float32(-np.inf))
    return rounded.astype(np.float64)


def _booster_with_float32_thresholds(booster: lightgbm.Booster) -> lightgbm.Booster:
    """Copy of ``booster`` with every split threshold rounded down to float32.

    For a float32 feature ``x``, ``x <= t`` holds exactly when ``x <= floor32(t)``, so the copy
    splits float32 features like the original, and the float32 thresholds of ONNX trees are
    exact. Without this an ONNX regressor differed on 5 of 2808 synthetic rows by up to
    0.26 kN (a split flipped by rounding to nearest).

    Raises:
        ValueError: The booster has categorical splits (thresholds are category sets).
    """
    lines = []
    for line in booster.model_to_string().splitlines():
        if line.startswith("num_cat=") and int(line.removeprefix("num_cat=")) != 0:
            raise ValueError("categorical splits are not supported by the threshold rounding")
        if line.startswith(TREE_SIZES_PREFIX):
            # Byte sizes of the tree blocks, which the new threshold text changes; without
            # them LightGBM parses the trees sequentially (with stale sizes it aborts).
            continue
        if line.startswith(THRESHOLD_PREFIX):
            values = np.array(line.removeprefix(THRESHOLD_PREFIX).split(), dtype=np.float64)
            floored = " ".join(repr(value) for value in _float32_floor(values).tolist())
            lines.append(THRESHOLD_PREFIX + floored)
        else:
            lines.append(line)
    return lightgbm.Booster(model_str="\n".join(lines) + "\n")


def export_lightgbm_onnx(model: LightGbmModel, folder: Path) -> OnnxExport:
    """ONNX files of the classifier (probabilities, no ZipMap) and the regressor.

    Raises:
        ImportError: ``onnxmltools`` is not installed.
    """
    import onnxmltools
    from onnxmltools.convert.common.data_types import FloatTensorType

    folder.mkdir(parents=True, exist_ok=True)
    input_types = [
        (LIGHTGBM_INPUT_NAME, FloatTensorType([None, model.classifier.num_feature()]))
    ]
    classifier = onnxmltools.convert_lightgbm(
        _booster_with_float32_thresholds(model.classifier), initial_types=input_types,
        zipmap=False, target_opset=LIGHTGBM_OPSET,
    )
    onnx_models = [classifier]
    paths = [folder / LIGHTGBM_ONNX_FILES[0], folder / LIGHTGBM_ONNX_FILES[1]]
    regressors = [model.regressor]
    if model.quantile_regressor is not None:
        regressors.append(model.quantile_regressor)
        paths.append(folder / LIGHTGBM_QUANTILE_ONNX_FILE)
    for regressor in regressors:
        onnx_models.append(onnxmltools.convert_lightgbm(
            _booster_with_float32_thresholds(regressor), initial_types=input_types,
            target_opset=LIGHTGBM_OPSET,
        ))
    for onnx_model, path in zip(onnx_models, paths, strict=True):
        path.write_bytes(onnx_model.SerializeToString())
    return OnnxExport(tuple(paths), "onnxmltools")


# --- ONNX inference and latency --------------------------------------------------------------


def _cpu_session(path: Path, threads: int = 1):
    import onnxruntime

    options = onnxruntime.SessionOptions()
    options.intra_op_num_threads = threads
    return onnxruntime.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])


class GruOnnxModel:
    """The exported GRU run by onnxruntime on CPU (same :class:`Prediction` as torch)."""

    def __init__(self, path: Path, threads: int = 1) -> None:
        self._session = _cpu_session(path, threads)

    def predict(self, examples: Examples) -> Prediction:
        feeds = {"sequences": examples.sequences, "context": examples.context}
        (raw,) = self._session.run([GRU_OUTPUT_NAME], feeds)
        return _prediction_from_raw(np.asarray(raw, dtype=float))


class LightGbmOnnxModel:
    """The exported LightGBM pair run by onnxruntime on CPU (features computed in numpy)."""

    def __init__(self, export: OnnxExport, threads: int = 1) -> None:
        classifier_path, regressor_path, *quantile_paths = export.paths
        self._classifier = _cpu_session(classifier_path, threads)
        self._regressor = _cpu_session(regressor_path, threads)
        self._quantile = (_cpu_session(quantile_paths[0], threads) if quantile_paths
                          else None)

    def predict(self, examples: Examples) -> Prediction:
        feeds = {LIGHTGBM_INPUT_NAME: tabular_features(examples)}
        (probabilities,) = self._classifier.run(["probabilities"], feeds)
        (min_force_kN,) = self._regressor.run(None, feeds)
        quantile = None
        if self._quantile is not None:
            (quantile_kN,) = self._quantile.run(None, feeds)
            quantile = np.asarray(quantile_kN, dtype=float).ravel()
        return Prediction(np.asarray(probabilities, dtype=float),
                          np.asarray(min_force_kN, dtype=float).ravel(), quantile)


@dataclass(frozen=True)
class LatencyResult:
    """Per-call wall time of one control period's inference (4 legs), CPU."""

    p50_ms: float
    p99_ms: float
    calls: int
    model_bytes: int


def _first_legs(examples: Examples) -> Examples:
    return examples.subset(np.arange(examples.count) < ONNX_LEG_COUNT)


def onnx_latency(path: Path, examples: Examples, calls: int = 2000) -> LatencyResult:
    """GRU ONNX: onnxruntime CPU, one thread, 4 legs per call (spec 205.6 E5), after 50
    warm-up calls."""
    session = _cpu_session(path)
    feeds = {"sequences": examples.sequences[:ONNX_LEG_COUNT],
             "context": examples.context[:ONNX_LEG_COUNT]}
    return _time_calls(lambda: session.run(None, feeds), calls, path.stat().st_size)


def lightgbm_onnx_latency(
    export: OnnxExport, examples: Examples, calls: int = 2000
) -> LatencyResult:
    """LightGBM ONNX (E5): features + both boosters for 4 legs per call, onnxruntime CPU,
    one thread."""
    runner = LightGbmOnnxModel(export)
    four = _first_legs(examples)
    return _time_calls(lambda: runner.predict(four), calls, export.model_bytes)


def lightgbm_latency(model: LightGbmModel, examples: Examples, calls: int = 500) -> LatencyResult:
    """Native LightGBM CPU predict of 4 legs (features included); reference to the ONNX path."""
    four = _first_legs(examples)
    size = sum(len(booster.model_to_string()) for booster in model.boosters())
    return _time_calls(lambda: model.predict(four), calls, size)


def _time_calls(call: Callable[[], object], calls: int, model_bytes: int) -> LatencyResult:
    for _ in range(50):
        call()
    times = np.empty(calls)
    for index in range(calls):
        start = time.perf_counter()
        call()
        times[index] = time.perf_counter() - start
    p50, p99 = np.percentile(times * 1e3, [50, 99])
    return LatencyResult(float(p50), float(p99), calls, int(model_bytes))
