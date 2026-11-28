"""R2 (ed9_design/control_d1_rule/report.md 4.2): detection power of C-m against injected
persistent head-reading jumps on the Chrono ML pilot records (open-loop record replay, the
method of spec 218.15 (c) / 219.2 (d) and ``04_scripts/03_control/s8/s8ml2_jump_inject.py``).

For every 10 Hz period ``j`` of an episode after its event and before its first FAULT phase, and
every leg and jump ``J`` (bar), the period's head step is ``dp = dh_j + J``; it is a D1 candidate
when ``|dp| > 100 bar`` (the strict ``max_step_Pa`` gate). With ``theta = 0.5 |dp| A_p`` and
``jf = J A_p`` it is flagged (unexplained) by

* D1'  (sum rule):   ``|ds_j + jf| >= theta``
* C0   (D1''):       ``|dr_j + jf| >= theta`` with ``r = sum F - M_eff f_z`` when D1'' applies
  (crawler lifted at ``j``, ``f_z`` of ``j`` and ``j-1`` finite), else D1'
* C-m:               C0 and ``|r_j + jf - med(r_{j-1}, r_{j-2}, r_{j-3})| >= theta`` when D1''
  applies and the three references are valid consecutive periods, else C0

``f_z`` is the last 10 ms IMU partial mean of the period minus the gyro lever term ``(alpha x
r)_z`` where the record has gyro samples (lever correction on, the controller default; without
gyro samples uncorrected, as the monitor does with ``WARN_D1_IMU_GYRO_MISSING``). ``M_eff`` is
the median ``sum F / f_z`` of the READY periods before the event. A period counts as lifted when
the phase of the period before it is one of ``c2.CRAWLER_LIFTED_PHASES`` (the monitor reads the
controller's phase of the period before). Periods are quiet when every ``|dh_j| <= 30 bar``,
else transient. The uninjected real steps above 100 bar give the false-fault counts.

No pickle is loaded (``allow_pickle=False``); only the npz arrays and ``result.json`` are read.

Usage (python-dev ``python.exe -I -B``)::

    python ml_inject_cm.py <ml batch dir> --params <02_params/rexome33.yaml>
        --out <ml_inject_cm.csv> [--provenance <json>]

Exit codes: 0 written; 2 input error (no batch, an existing output); 3 tool error. The stdout's
last line is JSON with ``status`` and the output paths.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

EXIT_OK, EXIT_INPUT, EXIT_ERROR = 0, 2, 3
BAR_PA = 1e5
MAX_STEP_BAR = 100.0
STEP_RATIO = 0.5
QUIET_STEP_BAR = 30.0
MEDIAN_REFERENCES = 3
JUMPS_BAR = (-150.0, -100.0, 100.0, 150.0)
GYRO_PERIOD_S = 0.01
LIFTED_PHASES = frozenset({"level", "done", "reanchor", "probe", "ready"})
"""``c2.CRAWLER_LIFTED_PHASES`` as recorded in ``r8_series`` ``phase`` (the test module
``test_two_pressure_d1_imu.py`` uses the same set)."""
FAULT_PHASE = "fault"
IMU_MOUNT_C1_BODY_M = (0.31, 0.88, 0.040)
"""IMU mount C1, body axes (``CLAUDE.md`` IMU 위치, ``sensors/imu.py``): the lever arm is this
minus the centre of mass of the episode's auger level (YAML
``superstructure.auger_levels.<level>.com_m``), as ``run_S8C.refresh_restored_controller``
gives a restored branch (``test_two_pressure_d1_imu.py``)."""
RULES = ("d1p", "c0", "cm")


class InputError(ValueError):
    """No batch folder or an existing output."""


@dataclass
class Tally:
    candidates: int = 0
    detected: dict[str, int] = field(default_factory=lambda: dict.fromkeys(RULES, 0))


@dataclass(frozen=True)
class Episode:
    """The 10 Hz arrays one replay needs (N for forces, bar for head steps)."""

    name: str
    t_s: np.ndarray
    head_bar: np.ndarray
    sum_N: np.ndarray
    f_z: np.ndarray
    lifted: np.ndarray
    judged: np.ndarray
    m_eff_kg: float
    has_gyro: bool
    lever_source: str


def level_lever_arms(params_path: Path) -> dict[str, tuple[float, float, float]]:
    """Auger level -> IMU mount minus that level's centre of mass (body axes, m)."""
    import yaml

    params = yaml.safe_load(params_path.read_text(encoding="utf-8"))
    levels = params["superstructure"]["auger_levels"]
    return {name: tuple(mount - float(com) for mount, com
                        in zip(IMU_MOUNT_C1_BODY_M, level["com_m"], strict=True))
            for name, level in levels.items()}


def _lever_arm(case: Path, arms: dict) -> tuple[tuple[float, float, float], str]:
    settings = json.loads((case / "case.json").read_text(encoding="utf-8")).get("settings") or {}
    level = str((settings.get("base") or {}).get("level"))
    if level not in arms:
        raise InputError(f"{case.name}: auger level {level!r} not in the params")
    return arms[level], f"yaml_{level}"


def _corrected_f_z(f_z: np.ndarray, gyro: np.ndarray | None, arm) -> np.ndarray:
    """``f_z - (alpha x r)_z`` per period from the last two gyro partial means."""
    if gyro is None:
        return f_z
    alpha = (gyro[:, -1, :2] - gyro[:, -2, :2]) / GYRO_PERIOD_S
    lever_z = alpha[:, 0] * arm[1] - alpha[:, 1] * arm[0]
    finite = np.all(np.isfinite(gyro[:, -2:, :2]), axis=(1, 2))
    return np.where(finite, f_z - lever_z, f_z)


def load_episode(case: Path, head_area_m2: np.ndarray, annulus_m2: np.ndarray,
                 arms: dict) -> Episode | None:
    """None when the episode has no event time or fewer than three READY periods before it."""
    result = json.loads((case / "result.json").read_text(encoding="utf-8"))
    if result.get("event_t_s") is None:
        return None
    event_s = float(result["event_t_s"])
    with np.load(case / "r8_series.npz", allow_pickle=False) as r8:
        t_s = np.asarray(r8["t"], dtype=float)
        phase = np.char.lower(r8["phase"].astype(str))
        f_z = np.asarray(r8["imu_samples"][:, -1, 2], dtype=float)
        gyro = np.asarray(r8["imu_gyro_samples"], dtype=float) if (
            "imu_gyro_samples" in r8.files) else None
    with np.load(case / "record" / "record.npz", allow_pickle=False) as record:
        index = np.clip(np.searchsorted(record["t"], t_s - 1e-9), 0, record["t"].size - 1)
        head_Pa = np.asarray(record["meas.head_pressure"][index], dtype=float)
        rod_Pa = np.asarray(record["meas.rod_pressure"][index], dtype=float)
    arm, lever_source = _lever_arm(case, arms) if gyro is not None else (None, "no_gyro")
    f_z = _corrected_f_z(f_z, gyro, arm)
    sum_N = (head_Pa * head_area_m2 - rod_Pa * annulus_m2).sum(axis=1)
    ready = (phase == "ready") & (t_s < event_s - 0.05) & np.isfinite(f_z) & (f_z > 0)
    if ready.sum() < 3:
        return None
    phase_before = np.concatenate([[""], phase[:-1]])
    lifted = np.isin(phase_before, list(LIFTED_PHASES))
    no_fault_yet = np.cumsum(phase == FAULT_PHASE) == 0
    judged = (t_s >= event_s) & no_fault_yet
    return Episode(case.name, t_s, head_Pa / BAR_PA, sum_N, f_z, lifted, judged,
                   float(np.median(sum_N[ready] / f_z[ready])), gyro is not None, lever_source)


def _uses_d1_imu(episode: Episode, j: int) -> bool:
    return bool(episode.lifted[j] and np.isfinite(episode.f_z[j])
                and np.isfinite(episode.f_z[j - 1]))


def _median_reference(episode: Episode, residual: np.ndarray, j: int) -> float | None:
    """``med(r_{j-1..j-3})`` when the three periods are valid (lifted, finite), else None."""
    if j - MEDIAN_REFERENCES < 0:
        return None
    window = range(j - MEDIAN_REFERENCES, j)
    if not all(episode.lifted[k] and np.isfinite(residual[k]) for k in window):
        return None
    return float(np.median([residual[k] for k in window]))


def flags_of(episode: Episode, residual: np.ndarray, j: int, leg: int, jump_bar: float,
             head_area_m2: np.ndarray) -> dict[str, bool] | None:
    """The three rules on period ``j``, leg ``leg``, jump ``jump_bar`` (None: no candidate)."""
    step_bar = episode.head_bar[j, leg] - episode.head_bar[j - 1, leg] + jump_bar
    if not abs(step_bar) > MAX_STEP_BAR:
        return None
    jump_N = jump_bar * BAR_PA * head_area_m2[leg]
    threshold_N = STEP_RATIO * abs(step_bar) * BAR_PA * head_area_m2[leg]
    d1p = abs(episode.sum_N[j] - episode.sum_N[j - 1] + jump_N) >= threshold_N
    if not _uses_d1_imu(episode, j):
        return {"d1p": d1p, "c0": d1p, "cm": d1p}
    c0 = abs(residual[j] - residual[j - 1] + jump_N) >= threshold_N
    cm = c0
    reference = _median_reference(episode, residual, j)
    if reference is not None:
        cm = c0 and abs(residual[j] + jump_N - reference) >= threshold_N
    return {"d1p": d1p, "c0": c0, "cm": cm}


def _period_class(episode: Episode, j: int) -> str:
    largest_step_bar = np.max(np.abs(episode.head_bar[j] - episode.head_bar[j - 1]))
    return "transient" if largest_step_bar > QUIET_STEP_BAR else "quiet"


def replay_episode(episode: Episode, tallies: dict, head_area_m2: np.ndarray) -> None:
    residual = episode.sum_N - episode.m_eff_kg * episode.f_z
    for j in range(1, episode.t_s.size):
        if not episode.judged[j]:
            continue
        period_class = _period_class(episode, j)
        for leg in range(4):
            real = flags_of(episode, residual, j, leg, 0.0, head_area_m2)
            if real is not None:
                _count(tallies, ("real_steps", period_class), real)
            for jump_bar in JUMPS_BAR:
                flags = flags_of(episode, residual, j, leg, jump_bar, head_area_m2)
                if flags is not None:
                    _count(tallies, (f"{jump_bar:+.0f}", period_class), flags)


def _count(tallies: dict, key: tuple[str, str], flags: dict[str, bool]) -> None:
    tally = tallies.setdefault(key, Tally())
    tally.candidates += 1
    for rule in RULES:
        tally.detected[rule] += bool(flags[rule])


def _rate(count: int, total: int) -> float | None:
    return None if total == 0 else count / total


def table_rows(tallies: dict) -> list[dict]:
    """One row per (jump or real steps, period class) with counts, rates and the P-S8-14 (c)
    checks (C-m >= D1' on a jump row, 100 % on a quiet jump row)."""
    rows = []
    order = [*(f"{jump:+.0f}" for jump in JUMPS_BAR), "real_steps"]
    for name in order:
        for period_class in ("transient", "quiet"):
            tally = tallies.get((name, period_class), Tally())
            row = {"injected_jump_bar": name, "period_class": period_class,
                   "candidates": tally.candidates}
            for rule in RULES:
                row[f"{rule}_flagged"] = tally.detected[rule]
                rate = _rate(tally.detected[rule], tally.candidates)
                row[f"{rule}_rate"] = "" if rate is None else f"{rate:.6f}"
            is_jump = name != "real_steps"
            row["cm_ge_d1p"] = (str(tally.detected["cm"] >= tally.detected["d1p"])
                                if is_jump and tally.candidates else "")
            row["cm_full_quiet"] = (str(tally.detected["cm"] == tally.candidates)
                                    if is_jump and period_class == "quiet" and tally.candidates
                                    else "")
            rows.append(row)
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: argparse.Namespace) -> dict:
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    batch = args.batch
    if not (batch / "episodes").is_dir():
        raise InputError(f"no episodes folder under {batch}")
    for path in (args.out, args.provenance):
        if path is not None and path.exists():
            raise InputError(f"{path} exists")
    head_area_m2 = np.array([1.3273229e-2, 1.3273229e-2, 9.50331778e-3, 9.50331778e-3])
    annulus_m2 = np.array([3.76991118e-3, 3.76991118e-3, 3.14159265e-3, 3.14159265e-3])
    arms = level_lever_arms(args.params)
    tallies: dict = {}
    used, skipped, gyro_sources = [], [], {}
    for case in sorted(path for path in (batch / "episodes").glob("ML*") if path.is_dir()):
        episode = load_episode(case, head_area_m2, annulus_m2, arms)
        if episode is None:
            skipped.append(case.name)
            continue
        used.append(case.name)
        gyro_sources[episode.lever_source] = gyro_sources.get(episode.lever_source, 0) + 1
        replay_episode(episode, tallies, head_area_m2)
    if not used:
        raise InputError("no episode could be replayed")
    rows = table_rows(tallies)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    provenance = {
        "rule": "ed9_design/control_d1_rule/report.md 4.2 R2, P-S8-14 (c); module docstring",
        "started_at": started,
        "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "batch": str(batch), "episodes_used": len(used), "episodes_skipped": skipped,
        "lever_sources": gyro_sources, "jumps_bar": list(JUMPS_BAR),
        "params": str(args.params), "params_sha256": _sha256(args.params),
        "script_sha256": _sha256(Path(__file__)), "out": str(args.out),
        "out_sha256": _sha256(args.out),
        "columns": {"candidates": "D1 candidates (|dp| > 100 bar) of the rows' periods",
                    "<rule>_flagged": "candidates the rule leaves unexplained (a FAULT)",
                    "<rule>_rate": "flagged / candidates",
                    "cm_ge_d1p": "jump rows: C-m flagged >= D1' flagged (P-S8-14 (c))",
                    "cm_full_quiet": "quiet jump rows: C-m flags every candidate",
                    "real_steps": "no injection: the flagged counts are false FAULTs"}}
    if args.provenance is not None:
        with args.provenance.open("x", encoding="utf-8") as handle:
            json.dump(provenance, handle, indent=1)
    return provenance


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("batch", type=Path)
    parser.add_argument("--params", type=Path, required=True,
                        help="02_params/rexome33.yaml (the auger-level centres of mass)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        provenance = run(args)
        print(json.dumps({"status": "ok", "episodes_used": provenance["episodes_used"],
                          "out": str(args.out),
                          "provenance": None if args.provenance is None
                          else str(args.provenance)}))
        return EXIT_OK
    except SystemExit as exc:
        return EXIT_INPUT if exc.code else EXIT_OK
    except InputError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}))
        return EXIT_INPUT
    except Exception:  # noqa: BLE001 - every unexpected exception is a tool error
        traceback.print_exc()
        print(json.dumps({"status": "error"}))
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
