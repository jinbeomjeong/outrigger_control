"""Tables of the clipped reduced-model runs (bundle ``CL``, criteria 9.1): values only, no verdict.

Reads ``run_verdict.py --bundles CL`` results and the stored unclipped runs, and writes in the clip
folder:
  clip_pairs.json / .csv   flow on against flow off, both clipped (the verdict_pairs layout: the
                           R, E and T inputs of ``aggregate_verdict.pair_row``)
  clip_summary.csv         one row per on run: main values on, off and their delta, next to the
                           delta of the stored unclipped pair
  command_excess.csv       each stored flow-off run: how far its commands pass v_max

Usage:
  <python> -I -B aggregate_clip.py [--clip-dir DIR] [--stored-dir DIR]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
from aggregate_verdict import (  # noqa: E402
    DEFAULT_DIR,
    OFF_BUNDLE,
    _delta,
    _dig,
    _load_runs,
    _write_long_csv,
    pair_row,
)
from params import load_params  # noqa: E402
from verdict_cases import ALL_CASE_IDS, CLIP_BUNDLE  # noqa: E402

CLIP_DIR = DEFAULT_DIR / "clip"
EXCESS_TOLERANCE_M_S = 1e-9
"""Commands at v_max carry rounding (up to 1 ulp); only a larger excess is an excess."""
ETA_TAGS = {"eta0.85": "A", "eta0.90": "B"}
"""Tag of a clipped on run -> bundle of its stored unclipped twin."""
ALIASES = {"S6": "S5"}
"""Criteria 8.1: the reduced model has one row for both (``--decide S6=alias_s5``)."""
SUMMARY_METRICS = {
    "t_ready_s": "run.t_ready_s",
    "t_done_s": "run.t_done_s",
    "min_true_force_after_off_kN": "run.min_true_Fcyl_after_off_kN",
    "max_motor_stroke_mm": "run.max_motor_stroke_mm",
    "clearance_true_ready_mm": "run.clear_true_ready_mm",
    "rut_ready_mm": "rut_ready_mm",
    "probe_rounds": "probe_rounds.n_probe_rounds",
    "n_reapproach": "run.n_reapproach",
    "n_crawler_recontact": "run.n_crawler_recontact",
}
"""Summary columns -> dotted path in a run result."""


@dataclass(frozen=True)
class CommandExcess:
    """How the commands of one stored run stand to v_max."""

    case_id: str
    periods: int
    peak_mm_s: float
    excess_over_v_max_mm_s: float
    periods_over: int
    periods_over_per_leg: list[int]
    phases_over: list[str]


def command_excess(path: Path, case_id: str, v_max_m_s: float) -> CommandExcess:
    """Reads the 10 Hz commands of one stored run."""
    with np.load(path, allow_pickle=False) as stored:
        magnitude = np.abs(stored["command"])
        phase = stored["phase"]
    is_over = magnitude > v_max_m_s + EXCESS_TOLERANCE_M_S
    is_period_over = is_over.any(axis=1)
    peak_m_s = float(magnitude.max())
    return CommandExcess(
        case_id=case_id, periods=len(magnitude), peak_mm_s=peak_m_s * 1e3,
        excess_over_v_max_mm_s=(peak_m_s - v_max_m_s) * 1e3,
        periods_over=int(is_period_over.sum()),
        periods_over_per_leg=is_over.sum(axis=0).tolist(),
        phases_over=sorted(set(phase[is_period_over].tolist())))


def excess_table(stored_dir: Path, v_max_m_s: float) -> list[CommandExcess]:
    """Every case with a stored flow-off run; an alias case has no file of its own."""
    table = []
    for case_id in ALL_CASE_IDS:
        path = stored_dir / f"{OFF_BUNDLE}_{case_id}.npz"
        if path.is_file():
            table.append(command_excess(path, case_id, v_max_m_s))
    return table


def _write_excess_csv(path: Path, table: list[CommandExcess], v_max_m_s: float) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["case_id", "v_max_mm_s", "periods", "peak_mm_s",
                         "excess_over_v_max_mm_s", "periods_over", "periods_over_FL_FR_RL_RR",
                         "phases_over"])
        for row in table:
            writer.writerow([row.case_id, v_max_m_s * 1e3, row.periods, row.peak_mm_s,
                             row.excess_over_v_max_mm_s, row.periods_over,
                             " ".join(map(str, row.periods_over_per_leg)),
                             " ".join(row.phases_over)])


def _unclipped_twin_id(record: dict) -> str:
    """``CL_S1_eta0.85`` -> ``A_S1_eta0.85``."""
    tag = record["run_id"].rsplit("_", 1)[-1]
    return f"{ETA_TAGS[tag]}_{record['case_id']}_{tag}"


def summary_row(record: dict, off: dict, stored: dict[str, dict]) -> dict:
    """Main values of one clipped on run, its clipped off run and the unclipped pair's delta."""
    unclipped_on = stored.get(_unclipped_twin_id(record))
    unclipped_off = stored.get(f"{OFF_BUNDLE}_{record['case_id']}")
    row = {"run_id": record["run_id"], "case_id": record["case_id"],
           "eta_v": record["setting"]["eta_v"], "class_on": record.get("harness_class"),
           "class_off": off.get("harness_class"), "final_phase_on": record.get("final_phase"),
           "final_phase_off": off.get("final_phase"),
           "command_peak_on_mm_s": _dig(record, "command_clip.peak_command_m_s") * 1e3,
           "command_peak_off_mm_s": _dig(off, "command_clip.peak_command_m_s") * 1e3,
           "valve_peak_on_mm_s": _dig(record, "command_clip.peak_valve_m_s") * 1e3,
           "off_hash_same_as_unclipped_off": None if unclipped_off is None else
           off.get("commands_sha256") == unclipped_off.get("commands_sha256")}
    for name, path in SUMMARY_METRICS.items():
        on_value, off_value = _dig(record, path), _dig(off, path)
        row[f"{name}_on"] = on_value
        row[f"{name}_off"] = off_value
        row[f"{name}_delta"] = _delta(on_value, off_value)
        row[f"{name}_delta_unclipped"] = None if unclipped_on is None or unclipped_off is None \
            else _delta(_dig(unclipped_on, path), _dig(unclipped_off, path))
    return row


def _write_summary_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--clip-dir", type=Path, default=CLIP_DIR)
    parser.add_argument("--stored-dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()
    v_max_m_s = load_params().v_max
    excess = excess_table(args.stored_dir, v_max_m_s)
    _write_excess_csv(args.clip_dir / "command_excess.csv", excess, v_max_m_s)

    runs = _load_runs(args.clip_dir)
    stored = _load_runs(args.stored_dir)
    pairs, summaries = [], []
    for record in runs.values():
        off = runs.get(f"{CLIP_BUNDLE}_OFF_{record['case_id']}")
        if record["bundle"] != CLIP_BUNDLE or record is off or off is None:
            continue
        pairs.append(pair_row(record, off, args.clip_dir))
        summaries.append(summary_row(record, off, stored))
    payload = {"note": "values only; verdicts by control-expert (criteria 9.1, 13)",
               "v_max_m_s": v_max_m_s, "aliases": ALIASES, "pairs": pairs}
    json_path = args.clip_dir / "clip_pairs.json"
    json_path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    _write_long_csv(args.clip_dir / "clip_pairs.csv", pairs)
    _write_summary_csv(args.clip_dir / "clip_summary.csv", summaries)
    print(f"{len(pairs)} pairs -> {json_path}")


if __name__ == "__main__":
    main()
