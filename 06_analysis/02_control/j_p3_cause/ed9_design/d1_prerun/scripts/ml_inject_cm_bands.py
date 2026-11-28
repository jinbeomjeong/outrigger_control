"""R2 by band and by run (user decision 2026-11-28; stats ``ed9_design/stats_impl_check/
report.md`` Q-2 (다), 5.1): the injection of ``ml_inject_cm.py`` with every candidate tagged by
its band against the crawler lift-off and written per run.

Reference time (user decision: "ML 기준 시각 = 크롤러 이탈"): the first period at which the crawler
force ``|F_crawler|`` of the record falls from above :data:`CRAWLER_CONTACT_N` to below it.

* ``episodes`` (192, the ``ml_inject_cm.py`` population): an episode starts from its base's
  READY branch with the crawler already off, so its lift-off is the base's (28-55 s before the
  event, every judged period lies in ``tail``). Judged periods, ``M_eff`` and validity exactly
  as ``ml_inject_cm.py`` (event onward, READY median before the event).
* ``bases_phase`` / ``bases_liftoff`` (24 each): the crawler lift-off transient itself. Judged
  from the lift-off to the first FAULT phase; ``M_eff`` is the YAML superstructure mass of the
  base's auger level (the R8 preset's ``imu_mass_before_ready = "yaml"`` before a READY median
  exists). ``bases_phase`` counts a period as lifted by the phase rule of ``ml_inject_cm.py``
  (LEVEL onward, the crawler possibly still in contact); ``bases_liftoff`` only from the true
  lift-off on (a proxy of the R8 preset's LOC rule, :func:`load_base`).

Bands of ``t - t_lift`` (s): ``k0`` [0, 0.1), ``k1`` [0.1, 0.2), ``k2`` [0.2, 0.3), ``late``
[0.3, 2.5), ``tail`` >= 2.5 (control ``control_d1_rule/report.md`` 2.3 bands; ``tail`` beyond
its transient window), ``before`` < 0.

``event_band`` (stats ``stats_r3_check/report.md`` 위임 python 1): the same bands of ``t -
t_event`` for an episode (``result.json`` ``event_t_s``, the time ``ml_inject_cm.py`` judges
from), :data:`NO_EVENT_BAND` for a base. ``row_role`` (:data:`ROW_ROLES`): episodes = the judged
P9-D1-5 rows; ``bases_liftoff`` k0 .. k2 = identity cells (C-m = C0 by its fallback), late /
tail = evidence; ``bases_phase`` = outside the edition 9 run conditions (kept as a public row).

Outputs (new paths, never overwritten): ``--out`` one row per (population, jump, period class,
band, event band) with the counts and rates of ``ml_inject_cm.py``; ``--runs-out`` the same per
run (an episode or a base), for cluster resampling (stats 5.1); ``--provenance``.

Usage (python-dev ``python.exe -I -B``, ``MKL_THREADING_LAYER=TBB``)::

    python ml_inject_cm_bands.py <ml batch> --params <02_params/rexome33.yaml>
        --out <ml_inject_cm_bands.csv> --runs-out <ml_inject_cm_runs.csv> --provenance <json>

Exit codes: 0 written; 2 input error; 3 tool error. The stdout's last line is JSON with
``status`` and the output paths.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import traceback
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ml_inject_cm as base_tool  # noqa: E402

EXIT_OK, EXIT_INPUT, EXIT_ERROR = 0, 2, 3
CRAWLER_CONTACT_N = 1000.0
"""Crawler contact threshold of the lift-off reference (an assumption: well above the record
noise, far below the crawler's share of the weight)."""
BANDS = (("k0", 0.0, 0.1), ("k1", 0.1, 0.2), ("k2", 0.2, 0.3), ("late", 0.3, 2.5),
         ("tail", 2.5, float("inf")))
BAND_TOLERANCE_S = 1e-6
BASE_POPULATIONS = {"bases_phase": False, "bases_liftoff": True}
"""The two validity readings of a base (:func:`load_base`): the phase rule and the lift-off
proxy of the LOC rule."""
NO_EVENT_BAND = "no_event"
"""``event_band`` of a base (a base run has no injected event)."""
IDENTITY_BANDS = ("k0", "k1", "k2")
"""``bases_liftoff`` bands where C-m = C0 by construction: fewer than three valid references
after the lift-off, so C-m falls back to C0 (control ``control_r3_check/report.md`` 2)."""
ROW_ROLES = {
    "judged": "P9-D1-5 judged row (episodes)",
    "identity_cell": "C-m = C0 by construction (fallback, valid references < 3), not evidence",
    "evidence": "C-m evidence cell (bases_liftoff late / tail)",
    "outside_run_conditions": "outside the edition 9 run conditions (soil response off, phase "
                              "rule); a public record row, kept"}
"""``row_role`` (stats ``stats_r3_check/report.md`` 1, control ``control_r3_check/report.md``
1.4, 2; user decision 2026-11-28 "stats 권고 4건 채택")."""


def row_role(population: str, band: str) -> str:
    """The ``row_role`` of a (population, band) row (:data:`ROW_ROLES`)."""
    if population == "episodes":
        return "judged"
    if population == "bases_phase":
        return "outside_run_conditions"
    return "identity_cell" if band in IDENTITY_BANDS else "evidence"


class InputError(ValueError):
    """No batch, an existing output or a run without a lift-off."""


def band_of(offset_s: float) -> str:
    if offset_s < -BAND_TOLERANCE_S:
        return "before"
    for name, low, high in BANDS:
        if low - BAND_TOLERANCE_S <= offset_s < high - BAND_TOLERANCE_S:
            return name
    return "tail"


def crawler_lift_off_s(record_path: Path) -> float | None:
    """The first above -> below crossing of ``|F_crawler|`` (None: no crossing)."""
    with np.load(record_path, allow_pickle=False) as record:
        t_s = np.asarray(record["t"], dtype=float)
        force = np.linalg.norm(np.asarray(record["F_crawler"], dtype=float), axis=1)
    touching = force > CRAWLER_CONTACT_N
    for k in range(1, t_s.size):
        if touching[k - 1] and not touching[k]:
            return float(t_s[k])
    return None


def level_masses(params_path: Path) -> dict[str, float]:
    import yaml

    params = yaml.safe_load(params_path.read_text(encoding="utf-8"))
    return {name: float(level["mass_kg"])
            for name, level in params["superstructure"]["auger_levels"].items()}


def _level_of(case: Path) -> str:
    settings = json.loads((case / "case.json").read_text(encoding="utf-8")).get("settings") or {}
    return str((settings.get("base") or {}).get("level"))


def load_base(case: Path, head_area_m2, annulus_m2, arms, masses, *,
              is_lift_off_validity: bool) -> tuple | None:
    """(the run's arrays as a ``ml_inject_cm.Episode``, lift-off time) of a base.

    ``is_lift_off_validity``: a period counts as lifted (D1'' applies, a C-m reference is
    valid) only from the true crawler lift-off on, a proxy of the R8 preset's LOC rule
    (``c2._is_crawler_lifted_for_d1`` with the soil response on); False = the phase rule of
    ``ml_inject_cm.py`` (LEVEL onward, crawler possibly still in contact)."""
    t_lift = crawler_lift_off_s(case / "record" / "record.npz")
    if t_lift is None:
        return None
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
    level = _level_of(case)
    if level not in masses:
        raise InputError(f"{case.name}: auger level {level!r} not in the params")
    if gyro is not None:
        f_z = base_tool._corrected_f_z(f_z, gyro, arms[level])
    sum_N = (head_Pa * head_area_m2 - rod_Pa * annulus_m2).sum(axis=1)
    phase_before = np.concatenate([[""], phase[:-1]])
    lifted = np.isin(phase_before, list(base_tool.LIFTED_PHASES))
    if is_lift_off_validity:
        lifted &= t_s >= t_lift - BAND_TOLERANCE_S
    no_fault_yet = np.cumsum(phase == base_tool.FAULT_PHASE) == 0
    judged = (t_s >= t_lift - BAND_TOLERANCE_S) & no_fault_yet
    run = base_tool.Episode(case.name, t_s, head_Pa / base_tool.BAR_PA, sum_N, f_z, lifted,
                            judged, masses[level], gyro is not None, f"yaml_mass_{level}")
    return run, t_lift


def episode_event_s(case: Path) -> float:
    """The episode's event time (``result.json`` ``event_t_s``, the one ``ml_inject_cm``
    judges from; :func:`base_tool.load_episode` returned None without it)."""
    result = json.loads((case / "result.json").read_text(encoding="utf-8"))
    return float(result["event_t_s"])


def _base_lift_offs(batch: Path) -> dict[str, float | None]:
    return {base.name: crawler_lift_off_s(base / "record" / "record.npz")
            for base in sorted((batch / "bases").glob("ML*")) if base.is_dir()}


def tally_run(run, t_lift: float, population: str, tallies: dict, head_area_m2,
              t_event: float | None = None) -> None:
    """Every candidate of the run into ``tallies[(population, run, jump, class, band,
    event_band)]``: ``band`` against the lift-off, ``event_band`` against the episode's event
    (stats ``stats_r3_check/report.md`` 위임 python 1; :data:`NO_EVENT_BAND` for a base)."""
    residual = run.sum_N - run.m_eff_kg * run.f_z
    for j in range(1, run.t_s.size):
        if not run.judged[j]:
            continue
        period_class = base_tool._period_class(run, j)
        band = band_of(float(run.t_s[j] - t_lift))
        event_band = NO_EVENT_BAND if t_event is None else band_of(float(run.t_s[j] - t_event))
        for leg in range(4):
            real = base_tool.flags_of(run, residual, j, leg, 0.0, head_area_m2)
            if real is not None:
                _count(tallies, (population, run.name, "real_steps", period_class, band,
                                 event_band), real)
            for jump_bar in base_tool.JUMPS_BAR:
                flags = base_tool.flags_of(run, residual, j, leg, jump_bar, head_area_m2)
                if flags is not None:
                    _count(tallies, (population, run.name, f"{jump_bar:+.0f}", period_class,
                                     band, event_band), flags)


def _count(tallies: dict, key: tuple, flags: dict[str, bool]) -> None:
    cell = tallies.setdefault(key, {"candidates": 0, **dict.fromkeys(base_tool.RULES, 0)})
    cell["candidates"] += 1
    for rule in base_tool.RULES:
        cell[rule] += bool(flags[rule])


def _row(key_fields: dict, cell: dict) -> dict:
    row = {**key_fields, "candidates": cell["candidates"]}
    for rule in base_tool.RULES:
        row[f"{rule}_flagged"] = cell[rule]
        row[f"{rule}_rate"] = (f"{cell[rule] / cell['candidates']:.6f}"
                               if cell["candidates"] else "")
    row["c0_minus_cm"] = cell["c0"] - cell["cm"]
    row["cm_minus_d1p"] = cell["cm"] - cell["d1p"]
    return row


def _key_fields(population: str, jump: str, period_class: str, band: str,
                event_band: str) -> dict:
    return {"population": population, "injected_jump_bar": jump, "period_class": period_class,
            "band": band, "event_band": event_band, "row_role": row_role(population, band)}


def aggregate_rows(tallies: dict) -> list[dict]:
    totals: dict[tuple, dict] = defaultdict(
        lambda: {"candidates": 0, **dict.fromkeys(base_tool.RULES, 0)})
    for (population, _, *rest), cell in tallies.items():
        total = totals[(population, *rest)]
        for name, value in cell.items():
            total[name] += value
    return [_row(_key_fields(*key), cell) for key, cell in sorted(totals.items())]


def run_rows(tallies: dict) -> list[dict]:
    rows = []
    for (population, run, *rest), cell in sorted(tallies.items()):
        fields = _key_fields(population, *rest)
        rows.append(_row({"population": population, "run": run, **fields}, cell))
    return rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: argparse.Namespace) -> dict:
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    if not (args.batch / "episodes").is_dir() or not (args.batch / "bases").is_dir():
        raise InputError(f"no episodes / bases under {args.batch}")
    for path in (args.out, args.runs_out, args.provenance):
        if path.exists():
            raise InputError(f"{path} exists")
    head_area_m2 = np.array([1.3273229e-2, 1.3273229e-2, 9.50331778e-3, 9.50331778e-3])
    annulus_m2 = np.array([3.76991118e-3, 3.76991118e-3, 3.14159265e-3, 3.14159265e-3])
    arms = base_tool.level_lever_arms(args.params)
    masses = level_masses(args.params)
    lift_offs = _base_lift_offs(args.batch)
    tallies: dict = {}
    used = {"episodes": 0, "bases": 0}
    skipped: dict[str, list[str]] = {"episodes": [], "bases": []}
    for case in sorted(p for p in (args.batch / "episodes").glob("ML*") if p.is_dir()):
        episode = base_tool.load_episode(case, head_area_m2, annulus_m2, arms)
        base_name = json.loads((case / "result.json").read_text(encoding="utf-8")).get("base")
        t_lift = lift_offs.get(base_name)
        if episode is None or t_lift is None:
            skipped["episodes"].append(case.name)
            continue
        used["episodes"] += 1
        tally_run(episode, t_lift, "episodes", tallies, head_area_m2,
                  t_event=episode_event_s(case))
    for case in sorted(p for p in (args.batch / "bases").glob("ML*") if p.is_dir()):
        for population, is_lift_off_validity in BASE_POPULATIONS.items():
            loaded = load_base(case, head_area_m2, annulus_m2, arms, masses,
                               is_lift_off_validity=is_lift_off_validity)
            if loaded is None:
                skipped["bases"].append(case.name)
                break
            tally_run(*loaded, population, tallies, head_area_m2)
        else:
            used["bases"] += 1
    if not tallies:
        raise InputError("no candidate in any run")
    _write_csv(args.out, aggregate_rows(tallies))
    _write_csv(args.runs_out, run_rows(tallies))
    provenance = {
        "rule": "R2 by band and run (module docstring); ml_inject_cm.py rules imported",
        "started_at": started,
        "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "batch": str(args.batch), "params": str(args.params),
        "params_sha256": _sha256(args.params), "runs_used": used, "runs_skipped": skipped,
        "reference": "crawler lift-off: first |F_crawler| crossing above -> below "
                     f"{CRAWLER_CONTACT_N} N (an episode takes its base's)",
        "bands_s": {name: [low, high] for name, low, high in BANDS},
        "script_sha256": _sha256(Path(__file__)),
        "rules_script_sha256": _sha256(Path(base_tool.__file__)),
        "outputs": {str(path): _sha256(path) for path in (args.out, args.runs_out)},
        "event_reference": "episodes: result.json event_t_s; bases: " + NO_EVENT_BAND,
        "row_roles": ROW_ROLES,
        "columns": {"band": "band of t - t_lift (crawler lift-off)",
                    "event_band": "band of t - t_event (episodes), no_event (bases)",
                    "row_role": "the row's use (row_roles)",
                    "c0_minus_cm": "C0 flagged minus C-m flagged (the loss count, >= 0)",
                    "cm_minus_d1p": "C-m flagged minus D1' flagged (P-S8-14 (c) margin)"}}
    with args.provenance.open("x", encoding="utf-8") as handle:
        json.dump(provenance, handle, indent=1)
    return provenance


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("batch", type=Path)
    parser.add_argument("--params", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--runs-out", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        provenance = run(args)
        print(json.dumps({"status": "ok", "runs_used": provenance["runs_used"],
                          "out": str(args.out), "runs_out": str(args.runs_out)}))
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
