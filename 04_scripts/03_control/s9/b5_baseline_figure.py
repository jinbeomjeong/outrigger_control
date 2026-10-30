"""B5 figure (paper section 4.10): crawler clearance at READY and the F_min margin per case.

Two panels sharing the case axis, one marker per controller (C2 / ABL / IND):
  (a) true crawler floor clearance at READY, all crawler nodes [mm] (``rut_all_ready_mm``),
      reference line at the 25 mm gate;
  (b) minimum true cylinder force after the crawler lift-off minus F_min [kN]
      (``min_Fcyl_after_off_kN - F_min_kN``), reference line at 0.
A run without the value (no READY, harness error) gets an "x" on the lower panel edge.

Several result files of ``b5_baseline_compare.py`` are merged (the wide set comes as
``b5_wide_A.json``, ``b5_wide_B1.json``, ``b5_wide_B2.json``; later files win). Written as a
vector PDF at the paper column width (81.5 mm) plus a 300 dpi PNG preview. Usage (an env with
matplotlib, e.g. dynamics-dev or python-dev):
  python -I b5_baseline_figure.py RESULT.json [RESULT.json ...] [--cases table|wide|all]
      [--out 06_analysis/02_control/s9/rev84/b5_figure.pdf]
Table cases are labelled by their id on the x axis; the wide set (293 cases) by index only.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT_PATH = ROOT / "06_analysis" / "02_control" / "s9" / "rev84" / "b5_figure.pdf"

CONTROLLER_ORDER = ("C2", "ABL", "IND")
# Categorical slots 1-3 of the paper palette (validated: CVD dE >= 9, normal dE >= 27); the
# marker shape carries the identity in grey-scale print.
CONTROLLER_COLORS = {"C2": "#2a78d6", "ABL": "#eb6834", "IND": "#1baf7a"}
CONTROLLER_MARKERS = {"C2": "o", "ABL": "s", "IND": "^"}
CONTROLLER_DODGE = {"C2": -0.22, "ABL": 0.0, "IND": 0.22}
"""x offset per controller (in case units) so the three markers of a case do not overlap."""
WIDE_PREFIXES = ("S|", "G|")
RUT_GATE_MM = 25.0
MISSING_STRIP_FRACTION = 0.12
"""Extra room below the data (fraction of the data range) for the "no value" marks."""
MISSING_MARK_Y = 0.04
"""Height of the "no value" marks in axes units (inside the free strip)."""

# Print sizes of the paper figures (09_paper/figures/scripts/paper_style.py, 2026-10-30)
MM_PER_INCH = 25.4
SINGLE_COLUMN_MM = 81.5
FIGURE_HEIGHT_MM = 92.0
FONT_FAMILY = "Malgun Gothic"
BASE_FONT_PT = 8.0
SMALL_FONT_PT = 7.0
REF_LINE_PT = 0.8
FRAME_PT = 0.6
GRID_PT = 0.5
EDGE_PT = 0.5
MARKER_PT = 3.5
PNG_DPI = 300
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e1e0d9"


def load_records(paths: list[Path]) -> dict[str, dict[str, dict]]:
    """Merge result files into ``case -> controller -> record`` (later files win)."""
    by_case: dict[str, dict] = defaultdict(dict)
    for path in paths:
        for record in json.loads(Path(path).read_text(encoding="utf-8"))["records"]:
            by_case[record["case"]][record["controller"]] = record
    return by_case


def select_cases(by_case: dict, case_set: str) -> list[str]:
    """Table cases (sorted ids), wide cases (sorted) or both, table first."""
    table = sorted(c for c in by_case if not c.startswith(WIDE_PREFIXES))
    wide = sorted(c for c in by_case if c.startswith(WIDE_PREFIXES))
    return {"table": table, "wide": wide, "all": table + wide}[case_set]


def clearance_mm(record: dict | None) -> float | None:
    if record is None or "error" in record:
        return None
    return record.get("rut_all_ready_mm")


def force_margin_kN(record: dict | None) -> float | None:
    if record is None or "error" in record:
        return None
    min_force_kN = record.get("min_Fcyl_after_off_kN")
    if min_force_kN is None:
        return None
    return min_force_kN - record["F_min_kN"]


def _apply_style() -> None:
    plt.rcParams.update({
        "font.family": FONT_FAMILY, "font.size": BASE_FONT_PT,
        "axes.labelsize": BASE_FONT_PT, "xtick.labelsize": SMALL_FONT_PT,
        "ytick.labelsize": SMALL_FONT_PT, "legend.fontsize": BASE_FONT_PT,
        "axes.unicode_minus": False, "mathtext.fontset": "dejavusans",
        "axes.linewidth": FRAME_PT, "axes.edgecolor": INK_SECONDARY, "axes.labelcolor": INK,
        "xtick.color": INK_SECONDARY, "ytick.color": INK_SECONDARY,
        "xtick.major.width": FRAME_PT, "ytick.major.width": FRAME_PT,
        "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "lines.markeredgewidth": EDGE_PT, "legend.frameon": False,
        "pdf.fonttype": 42, "savefig.dpi": PNG_DPI,
    })


def _plot_panel(axes, case_ids: list[str], by_case: dict, value_of, reference: float) -> None:
    """One marker per (case, controller); missing values as "x" on the lower edge."""
    axes.axhline(reference, color=INK_SECONDARY, linewidth=REF_LINE_PT, linestyle=(0, (4, 2)),
                 zorder=1)
    for name in CONTROLLER_ORDER:
        xs, ys, missing_xs = [], [], []
        for index, case_id in enumerate(case_ids):
            x = index + CONTROLLER_DODGE[name]
            if name not in by_case[case_id]:
                continue
            value = value_of(by_case[case_id][name])
            if value is None or not math.isfinite(value):
                missing_xs.append(x)
            else:
                xs.append(x)
                ys.append(value)
        axes.plot(xs, ys, linestyle="none", marker=CONTROLLER_MARKERS[name],
                  markersize=MARKER_PT, color=CONTROLLER_COLORS[name],
                  markeredgecolor="white", zorder=3)
        axes.plot(missing_xs, [MISSING_MARK_Y] * len(missing_xs), linestyle="none", marker="x",
                  markersize=MARKER_PT, color=CONTROLLER_COLORS[name],
                  transform=axes.get_xaxis_transform(), clip_on=False, zorder=3)
    # free strip at the bottom so the "x" marks never sit on a data value
    y_low, y_high = axes.get_ylim()
    axes.set_ylim(y_low - MISSING_STRIP_FRACTION * (y_high - y_low), y_high)
    axes.grid(True, axis="y", color=GRID, linewidth=GRID_PT)
    axes.set_axisbelow(True)
    axes.set_xlim(-0.6, len(case_ids) - 0.4)


def _label_cases(axes, case_ids: list[str]) -> None:
    if any(c.startswith(WIDE_PREFIXES) for c in case_ids):
        axes.set_xlabel("사례 번호")
        return
    axes.set_xticks(range(len(case_ids)))
    axes.set_xticklabels(case_ids, rotation=90)
    axes.set_xlabel("사례")


def _add_legend(figure) -> None:
    handles = [Line2D([], [], linestyle="none", marker=CONTROLLER_MARKERS[name],
                      markersize=MARKER_PT + 1, color=CONTROLLER_COLORS[name],
                      markeredgecolor="white", label=name) for name in CONTROLLER_ORDER]
    handles.append(Line2D([], [], linestyle="none", marker="x", markersize=MARKER_PT + 1,
                          color=INK_SECONDARY, label="값 없음"))
    figure.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.55, 1.0), ncol=4,
                  handletextpad=0.2, columnspacing=1.0)


def draw_figure(by_case: dict, case_ids: list[str]):
    """Two-panel figure: (a) clearance at READY, (b) F_cyl - F_min after the lift-off."""
    _apply_style()
    figure, (top, bottom) = plt.subplots(
        2, 1, sharex=True, figsize=(SINGLE_COLUMN_MM / MM_PER_INCH,
                                    FIGURE_HEIGHT_MM / MM_PER_INCH))
    is_labelled = not any(c.startswith(WIDE_PREFIXES) for c in case_ids)
    # fixed margins: the rotated case ids need about 25 mm below the lower panel
    figure.subplots_adjust(left=0.15, right=0.98, top=0.88, hspace=0.32,
                           bottom=0.30 if is_labelled else 0.11)
    _add_legend(figure)
    _plot_panel(top, case_ids, by_case, clearance_mm, RUT_GATE_MM)
    top.set_ylabel("크롤러 틈 [mm]")
    top.set_title("(a) READY 때 실제 크롤러 틈", loc="left", fontsize=BASE_FONT_PT)
    _plot_panel(bottom, case_ids, by_case, force_margin_kN, 0.0)
    bottom.set_ylabel(r"$F_{cyl}-F_{min}$ [kN]")
    bottom.set_title("(b) 이탈 뒤 최소 실린더 힘 여유", loc="left", fontsize=BASE_FONT_PT)
    _label_cases(bottom, case_ids)
    return figure


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results", nargs="+", type=Path, help="b5_baseline_compare.py JSONs")
    parser.add_argument("--cases", choices=("table", "wide", "all"), default="table")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH, help="PDF path")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    by_case = load_records(args.results)
    case_ids = select_cases(by_case, args.cases)
    if not case_ids:
        raise SystemExit(f"no {args.cases} cases in {[str(p) for p in args.results]}")
    figure = draw_figure(by_case, case_ids)
    pdf_path = args.out.with_suffix(".pdf")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(pdf_path)
    figure.savefig(pdf_path.with_suffix(".png"), dpi=PNG_DPI, facecolor="white")
    print(pdf_path, pdf_path.with_suffix(".png"), f"{len(case_ids)} cases")


if __name__ == "__main__":
    main()
