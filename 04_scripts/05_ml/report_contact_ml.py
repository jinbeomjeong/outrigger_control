"""Summarise a ``train_contact_ml.py`` report into the S8 analysis record and one figure.

    C:\\ProgramData\\miniforge3\\envs\\pytorch_214_cuda_python_313\\python.exe -I \\
        04_scripts/05_ml/report_contact_ml.py <train report.json> <summary .json> <figure .png> \\
        [LABEL=<earlier train report.json> ...]

Earlier reports are kept as ``compared_runs`` (test-share rows only), e.g. the run before a tag
or a setting changed.

The summary keeps, per model: the E1-E7 and tag rows of the test share, M1-M4 of ML and J_C on
every scored set (test, OOD-1, OOD-2, judged cases), ONNX size and latency; plus the dataset,
split and tag summary and the reproduction command. The figure compares ML and J_C on the
E1 / E2 / M2 / M3 values per set (small multiples, one scale per panel).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SERIES_COLORS = {"J_C": "#2a78d6", "LightGBM": "#eb6834", "GRU": "#1baf7a"}
"""Categorical slots 1-3 of the validated dataviz reference palette (light surface)."""
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
MODEL_LABELS = {"lightgbm": "LightGBM", "gru": "GRU"}
PANELS = (
    ("M1_missed_upper_95", "E1: missed-episode 95 % upper bound", 100.0, "%"),
    ("M4_max_N", "E2: M4 risk-side max error", 1e-3, "kN"),
    ("M2_false_action_flags", "M2: false action flags", 1.0, "count"),
    ("M3_median_delay_s", "M3: median action delay", 1.0, "s"),
)


def _judge_metrics(score: dict) -> dict:
    keys = ("episodes", "M1_missed", "M1_missed_upper_95", "M1p_late", "M2_false_action_flags",
            "M3_median_delay_s", "M4_max_N", "M4_p5_p50_p95_N")
    return {key: score.get(key) for key in keys}


def _set_summary(scores: dict) -> dict:
    return {"ML": _judge_metrics(scores["ML"]), "J_C": _judge_metrics(scores["J_C"]),
            "ECE_ML": scores["ECE"], "examples": scores["examples"]}


def _model_summary(model: dict, onnx_meta: dict | None) -> dict:
    sets = {"test": _set_summary(model["test"])}
    for name, scores in model["out_of_distribution"].items():
        sets[name] = _set_summary(scores)
    if "judged_cases" in model:
        sets["judged cases"] = _set_summary(model["judged_cases"])
    return {"verdict_rows": model["verdict_rows"], "judged_rows": model.get("judged_rows"),
            "sets": sets, "latency": model["latency"], "latency_note": model["latency_note"],
            "onnx": onnx_meta}


def summarise(report: dict) -> dict:
    """The analysis record of one training report."""
    models = {name: _model_summary(model, report["onnx"].get(name))
              for name, model in report["models"].items()}
    return {
        "spec": report["spec"],
        "source": report["source"],
        "reproduce": report.get("command"),
        "seeds": report["seeds"],
        "settings": report.get("settings"),
        "dataset": report["dataset"],
        "shares": report.get("shares"),
        "ml_masks": report["ml_masks"],
        "tags": report.get("tags"),
        "release_step_effect": report.get("release_step_effect"),
        "lightgbm_preset": report.get("lightgbm_preset"),
        "gru_device": report.get("gru_device"),
        "onnx_difference_on_test": report["onnx"]["difference_on_test"],
        "models": models,
        "wall_s": report.get("wall_s"),
    }


def _panel_values(summary: dict, key: str, scale: float) -> tuple[list[str], dict[str, list]]:
    first = next(iter(summary["models"].values()))
    set_names = list(first["sets"])
    values: dict[str, list] = {"J_C": []}
    for set_name in set_names:
        value = first["sets"][set_name]["J_C"][key]
        values["J_C"].append(None if value is None else value * scale)
    for name, model in summary["models"].items():
        label = MODEL_LABELS.get(name, name)
        values[label] = []
        for set_name in set_names:
            value = model["sets"][set_name]["ML"][key]
            values[label].append(None if value is None else value * scale)
    return set_names, values


def _draw_panel(axis, set_names, values, title, unit) -> None:
    width = 0.8 / len(values)
    for index, (series, series_values) in enumerate(values.items()):
        for position, value in enumerate(series_values):
            x = position + (index - (len(values) - 1) / 2) * width
            if value is None:
                axis.text(x, 0, "n/a", ha="center", va="bottom", fontsize=7,
                          color=TEXT_SECONDARY)
                continue
            axis.bar(x, value, width * 0.92, color=SERIES_COLORS[series],
                     label=series if position == 0 else None)
            text = f"{value:.0f}" if unit == "count" else f"{value:.2f}"
            axis.text(x, value, text, ha="center", va="bottom" if value >= 0 else "top",
                      fontsize=7, color=TEXT_PRIMARY)
    tick_labels = [name.replace(" ", "\n", 1) for name in set_names]
    axis.set_xticks(range(len(set_names)), tick_labels, fontsize=8, color=TEXT_SECONDARY)
    low, high = axis.get_ylim()
    span = high - low
    axis.set_ylim(min(low, 0.0) - 0.08 * span, max(high, 0.0) + 0.12 * span)
    axis.set_title(f"{title} [{unit}]", fontsize=9, color=TEXT_PRIMARY, loc="left")
    axis.axhline(0.0, color=TEXT_SECONDARY, linewidth=0.6)
    axis.grid(axis="y", color="#e4e3df", linewidth=0.6)
    axis.set_axisbelow(True)
    axis.tick_params(axis="y", labelsize=8, colors=TEXT_SECONDARY)
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)


def draw_figure(summary: dict, path: Path) -> None:
    """ML against J_C on the E1 / E2 / M2 / M3 values of every scored set."""
    figure, axes = plt.subplots(2, 2, figsize=(11, 7), facecolor=SURFACE)
    for axis, (key, title, scale, unit) in zip(axes.flat, PANELS, strict=True):
        axis.set_facecolor(SURFACE)
        set_names, values = _panel_values(summary, key, scale)
        _draw_panel(axis, set_names, values, title, unit)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="upper right", frameon=False, fontsize=9, ncols=3)
    figure.suptitle("S8 ground-contact ML vs replayed J_C (same samples per set)",
                    fontsize=11, color=TEXT_PRIMARY, x=0.01, ha="left")
    figure.tight_layout(rect=(0, 0, 1, 0.95))
    figure.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(figure)


def comparison(label: str, report: dict, path: Path) -> dict:
    """Test-share rows of an earlier run, for the before / after table."""
    return {"label": label, "train_report": str(path),
            "lightgbm_preset": report.get("lightgbm_preset"),
            "release_step_effect": report.get("release_step_effect"),
            "models": {name: {"verdict_rows": model["verdict_rows"],
                              "test": _set_summary(model["test"])}
                       for name, model in report["models"].items()}}


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    report_path, summary_path, figure_path = (Path(arg) for arg in argv[:3])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = summarise(report)
    summary["train_report"] = str(report_path)
    summary["figure"] = str(figure_path)
    summary["compared_runs"] = []
    for item in argv[3:]:
        label, _, path_text = item.partition("=")
        other = json.loads(Path(path_text).read_text(encoding="utf-8"))
        summary["compared_runs"].append(comparison(label, other, Path(path_text)))
    summary_path.write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=str),
                            encoding="utf-8")
    draw_figure(summary, figure_path)
    print(f"summary: {summary_path}\nfigure: {figure_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
