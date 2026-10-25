"""Summarise a ``train_contact_ml_v2.py`` report (P-S8-19) into the S8 record and one figure.

    C:\\ProgramData\\miniforge3\\envs\\pytorch_214_cuda_python_313\\python.exe -I \\
        04_scripts/05_ml/report_contact_ml_v2.py <train report.json> <summary .json> \\
        <figure .png> [--reproduce <text file of the reproduction commands>]

The summary keeps per model: the E1-E7 table per seed (default reading basis), the worst-seed
E1 verdict with the E / N condition, mean / min / max of the other rows, the decision levels
picked on the validation share, the quantile coverage (E2), the reading-basis rows (record raw,
ML raw features, upper bound, level 0.5, corrected-features dependence) and the E / N group
misses with the missed truth episodes of the worst E / N seed. The figure shows the per-seed
values of E1 (test and E / N misses), E2 and the quantile coverage against their limits.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SERIES_COLORS = {"J_C": "#2a78d6", "lightgbm": "#eb6834", "gru": "#1baf7a"}
"""Categorical slots 1-3 of the validated palette used by ``report_contact_ml.py``."""
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
MODEL_LABELS = {"gru": "GRU", "lightgbm": "LightGBM"}
GATE_GROUPS = ("E", "N", "CB")
"""Control-3 gate groups of the E1 second condition (p1r / rest / CB records)."""
COVERAGE_TARGET = 0.95
NONINFERIORITY_KN = 0.5


def _verdict(rows: list[dict], item: str) -> dict | None:
    return next((row for row in rows if row["item"] == item), None)


def _seed_table_row(run: dict) -> dict[str, Any]:
    """One seed's E1-E7 values on the default basis."""
    rows = run["verdict_rows"]
    e1, e2, e3 = _verdict(rows, "E1"), _verdict(rows, "E2"), _verdict(rows, "E3")
    e4, e5, e7 = _verdict(rows, "E4"), _verdict(rows, "E5"), _verdict(rows, "E7")
    test = run["test"]
    coverage = run["quantile_coverage"]
    en = run.get("en_groups", {}).get("default_corrected")
    groups = run.get("en_groups", {}).get("detail", {}).get("groups", {})
    gate = [groups[name] for name in GATE_GROUPS if name in groups]
    return {
        "seed": run["seed"],
        "threshold": run["threshold"],
        "E1": {"ML_missed": e1["value"]["ML_missed"], "episodes": e1["value"]["episodes"],
               "J_C_missed": test["J_C"]["M1_missed"],
               "ML_upper_95": e1["value"]["ML_upper"], "J_C_upper_95": e1["value"]["J_C_upper"],
               "passed": e1["passed"],
               "EN_ML_missed": None if en is None else en["ML_missed"],
               "EN_J_C_missed": None if en is None else en["J_C_missed"],
               "EN_episodes": None if en is None else en["episodes"],
               "gate_ML_missed": sum(g["ML_missed"] for g in gate) if gate else None,
               "gate_J_C_missed": sum(g["J_C_missed"] for g in gate) if gate else None,
               "gate_episodes": sum(g["episodes"] for g in gate) if gate else None},
        "E2": {**e2["value"], "passed": e2["passed"],
               "coverage_validation": coverage["validation"],
               "coverage_test": coverage["test"]},
        "E3": {"ML_median_delay_s": test["ML"]["M3_median_delay_s"],
               "J_C_median_delay_s": test["J_C"]["M3_median_delay_s"],
               "ML_false_action_flags": test["ML"]["M2_false_action_flags"],
               "J_C_false_action_flags": test["J_C"]["M2_false_action_flags"],
               "passed": e3["passed"]},
        "E4": {"ECE": e4["value"], "passed": e4["passed"]},
        "E5": {**e5["value"], "passed": e5["passed"]},
        "E6": {label: {"ML_missed": scores["ML"]["M1_missed"],
                       "J_C_missed": scores["J_C"]["M1_missed"],
                       "episodes": scores["ML"]["episodes"],
                       "passed": scores["ML"]["M1_missed_upper_95"]
                       <= scores["J_C"]["M1_missed_upper_95"] + 1e-12}
               for label, scores in run["out_of_distribution"].items()},
        "E7": None if e7 is None else e7["value"],
        "judged_cases": run.get("judged_cases"),
    }


def _worst_en_detail(runs: list[dict]) -> dict | None:
    with_en = [run for run in runs if "en_groups" in run]
    if not with_en:
        return None
    worst = max(with_en, key=lambda run: run["en_groups"]["default_corrected"]["ML_missed"])
    detail = worst["en_groups"]["detail"]
    return {"seed": worst["seed"], "groups": detail["groups"],
            "missed_episodes": detail["missed_episodes"]}


def _en_condition(runs: list[dict]) -> dict[str, Any] | None:
    """E1 second condition on the control-3 gate groups only (spec 233: MLJ is a judge-check
    set and does not stand in for the E / N groups); MLJ is shown as a record."""
    with_en = [run for run in runs if "en_groups" in run]
    if not with_en:
        return None
    per_seed = []
    for run in with_en:
        groups = run["en_groups"]["detail"]["groups"]
        gate = {name: groups[name] for name in GATE_GROUPS if name in groups}
        per_seed.append({
            "seed": run["seed"],
            "gate_episodes": sum(g["episodes"] for g in gate.values()),
            "gate_ML_missed": sum(g["ML_missed"] for g in gate.values()),
            "gate_J_C_missed": sum(g["J_C_missed"] for g in gate.values()),
            "MLJ_record": groups.get("MLJ"),
        })
    return {"groups": list(GATE_GROUPS),
            "per_seed": per_seed,
            "passed": all(row["gate_ML_missed"] == 0 for row in per_seed),
            "worst_gate_ML_missed": max(row["gate_ML_missed"] for row in per_seed)}


def _model_summary(runs: list[dict], aggregate: dict) -> dict[str, Any]:
    first_condition = aggregate["E1"]["first_condition_passed"]
    gate = _en_condition(runs)
    return {
        "E1_verdict": {
            "first_condition_worst_seed": first_condition,
            "second_condition_gate_groups": None if gate is None else gate["passed"],
            "passed": bool(first_condition and gate is not None and gate["passed"]),
        },
        "E1_second_condition": gate,
        "aggregate": aggregate,
        "per_seed": [_seed_table_row(run) for run in runs],
        "threshold_choice": [{"seed": run["seed"],
                              **{k: v for k, v in run["threshold_choice"].items()
                                 if k != "candidates"}} for run in runs],
        "reading_basis_rows": [{"seed": run["seed"], **run["E1_rows"],
                                "corrected_features_row": run["corrected_features_row"]}
                               for run in runs],
        "en_groups_per_seed": [{"seed": run["seed"],
                                **{k: v for k, v in run["en_groups"].items() if k != "detail"},
                                "groups": run["en_groups"]["detail"]["groups"]}
                               for run in runs if "en_groups" in run],
        "en_worst_seed_detail": _worst_en_detail(runs),
        "info": [{"seed": run["seed"], **run["info"]} for run in runs],
    }


def summarise(report: dict) -> dict[str, Any]:
    """The analysis record of one v2 report."""
    return {
        "spec": report["spec"],
        "reproduce_command": report["command"],
        "source_tree": report["source_tree"],
        "episodes": report["episodes"],
        "judged_episodes": report["judged_episodes"],
        "en_episodes": report["en_episodes"],
        "en_runs": report["en_runs"],
        "seeds": report["seeds"],
        "split_episode_counts": report["split"],
        "settings": report["settings"],
        "reading_basis": report["reading_basis"],
        "models": {name: _model_summary(runs, report["summary"][name])
                   for name, runs in report["per_model"].items()},
        "wall_s": report["wall_s"],
    }


# --- figure ----------------------------------------------------------------------------------


def _style(axis, title: str, unit: str) -> None:
    axis.set_facecolor(SURFACE)
    axis.set_title(f"{title} [{unit}]", fontsize=9, color=TEXT_PRIMARY, loc="left")
    axis.grid(axis="y", color=GRID, linewidth=0.6)
    axis.set_axisbelow(True)
    axis.tick_params(labelsize=8, colors=TEXT_SECONDARY)
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)


def _seed_points(axis, summary: dict, value_of, label_suffix: str = "", marker: str = "o",
                 offset: float = 0.0) -> None:
    """One mark per seed per model, models side by side."""
    for position, (name, model) in enumerate(summary["models"].items()):
        values = [value_of(row) for row in model["per_seed"]]
        xs = [position + offset + 0.06 * (k - (len(values) - 1) / 2)
              for k in range(len(values))]
        points = [(x, v) for x, v in zip(xs, values, strict=True) if v is not None]
        if points:
            axis.scatter(*zip(*points, strict=True), s=24, color=SERIES_COLORS[name],
                         marker=marker, label=f"{MODEL_LABELS[name]}{label_suffix}", zorder=3)
    axis.set_xticks(range(len(summary["models"])),
                    [MODEL_LABELS[name] for name in summary["models"]])
    axis.set_xlim(-0.6, len(summary["models"]) - 0.4)


def _reference_line(axis, value: float, text: str, color: str) -> None:
    axis.axhline(value, color=color, linewidth=1.0, linestyle="--", zorder=2)
    axis.text(axis.get_xlim()[1], value, f" {text}", fontsize=7, color=color, va="center",
              ha="left")


def draw_figure(summary: dict, path: Path) -> None:
    """Per-seed E1 (test, E / N), E2 and near-F_min quantile coverage against their limits."""
    figure, axes = plt.subplots(2, 2, figsize=(11, 7), facecolor=SURFACE)
    first = next(iter(summary["models"].values()))["per_seed"][0]

    axis = axes[0, 0]
    _seed_points(axis, summary, lambda row: row["E1"]["ML_missed"])
    _style(axis, f"E1 test: ML missed episodes per seed (of {first['E1']['episodes']})",
           "count")
    # Same episode count for both judges, so "ML upper <= J_C upper" is "ML missed <= J_C".
    j_c_missed = first["E1"]["J_C_missed"]
    _reference_line(axis, j_c_missed, f"J_C missed ({j_c_missed}) = pass limit",
                    SERIES_COLORS["J_C"])

    axis = axes[0, 1]
    _seed_points(axis, summary, lambda row: row["E1"]["gate_ML_missed"])
    _style(axis, "E1 gate groups E + N + CB: ML missed episodes "
           f"(of {first['E1']['gate_episodes']})", "count")
    gate_j_c_missed = first["E1"]["gate_J_C_missed"]
    if gate_j_c_missed == 0:
        _reference_line(axis, 0.0, "required 0 (J_C missed 0)", SERIES_COLORS["J_C"])
    else:
        _reference_line(axis, 0.0, "required: 0", TEXT_SECONDARY)
        _reference_line(axis, gate_j_c_missed, f"J_C missed ({gate_j_c_missed})",
                        SERIES_COLORS["J_C"])
    axis.yaxis.get_major_locator().set_params(integer=True)

    axis = axes[1, 0]
    _seed_points(axis, summary, lambda row: row["E2"]["ML_M4_max_N"] / 1e3)
    _style(axis, "E2: M4 risk-side max error, lower-5 % quantile estimate", "kN")
    limit = first["E2"]["J_C_M4_max_N"] / 1e3 + NONINFERIORITY_KN
    _reference_line(axis, limit, f"J_C + 0.5 kN ({limit:.1f})", SERIES_COLORS["J_C"])

    axis = axes[1, 1]
    _seed_points(axis, summary,
                 lambda row: row["E2"]["coverage_validation"]["near_F_min_band"],
                 " validation (o)", "o", -0.15)
    _seed_points(axis, summary, lambda row: row["E2"]["coverage_test"]["near_F_min_band"],
                 " test (^)", "^", 0.15)
    _style(axis, "Quantile coverage near F_min (truth >= estimate), o validation, ^ test",
           "share")
    _reference_line(axis, COVERAGE_TARGET, "target 0.95", TEXT_SECONDARY)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="upper right", frameon=False, fontsize=9, ncols=2)
    figure.suptitle("S8 ground-contact ML, P-S8-19: five model seeds, corrected reading "
                    "(spec rev. 52 232 / 233)", fontsize=11, color=TEXT_PRIMARY, x=0.01,
                    ha="left")
    figure.tight_layout(rect=(0, 0, 0.93, 0.95))
    figure.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(figure)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    report_path, summary_path, figure_path = (Path(arg) for arg in argv[:3])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = summarise(report)
    summary["train_report"] = str(report_path)
    summary["figure"] = str(figure_path)
    if "--reproduce" in argv:
        reproduce_path = Path(argv[argv.index("--reproduce") + 1])
        summary["reproduce"] = reproduce_path.read_text(encoding="utf-8").splitlines()
    summary_path.write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=str),
                            encoding="utf-8")
    draw_figure(summary, figure_path)
    print(f"summary: {summary_path}\nfigure: {figure_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
