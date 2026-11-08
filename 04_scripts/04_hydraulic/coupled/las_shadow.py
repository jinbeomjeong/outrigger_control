"""T4h shadow judge of the adopted LAS-b variant (sealed ``las_targeted_rules.md`` 4).

Per stored record: did the variant's start gate (S1 .. S8 of rules 1.2) hold in any LEVEL step?
``fires`` = rerun needed, ``silent`` = the rule never starts, the commands are bit for bit the
stored ones (the rule acts only after its start), ``undecidable`` = rerun (a field is missing).

Inputs: T4h npz (``t_s``, ``phase``, ``lower_estimate_N``, ``meta_json`` with ``events`` and
``F_min_N``). Most v5 T4h records were written without ``lower_estimate_N`` (only the r79 Dg-3
records and the ``las_targeted.py --gate-npz-dir`` records carry it): those are
``undecidable`` (rules 4: a missing field -> rerun). W_ref is ``meta.W_ref_N`` or, without it,
the YAML superstructure mass x g (``C2Controller._reference_weight_N``); S1 is
``meta.soil_enable`` or, without it, true (assumption, listed per record).

Gate evaluation per period k (``t_s[k]``; ``phase`` is the phase after the update):
  LEVEL step  the update ran ``_level_step``: phase entering it (``phase[k-1]``) LEVEL, or DONE /
              PROBE / READY with ``phase[k]`` LEVEL or FAULT* (the re-level of
              ``_hold_probe_or_relevel``: ``_start_relevel`` sets LEVEL first, and a DONE cannot
              follow in that period because ``complete_since_s`` was cleared). A head-sensor FAULT
              raised in ``_read`` of a LEVEL period is still counted (over-count, safe side).
  S2          a LEVEL step without ``WARN_CRAWLER_LIFTOFF_UNCONFIRMED`` at t_k (that S-4 FAULT is
              set in ``_update_crawler_zone``, before the wrapper point).
  S3          no ``crawler_liftoff_confirmed`` (or ``INFO_SOIL_STATE_RESTORED``) at or before t_k:
              the LOC is confirmed in ``_update_liftoff_window`` at the start of ``_level_step``,
              before the wrapper point, so an event at t_k already closes S3 in period k.
  S4          no ``soil_mode_start`` at or before t_k: it is raised in
              ``_hold_crawler_zone_until_liftoff`` inside ``_update_crawler_zone``, before the
              wrapper point.
  S5          true (proof below).
  S6          no active re-approach after the events at or before t_k: ``_update_lifted_reapproach``
              runs before ``_phase_command`` in ``update``; ``leg_reapproach_start`` adds the leg,
              ``leg_reapproach_contact`` / ``WARN_LEG_REAPPROACH_NO_CONTACT`` remove it, and a
              period entered in a phase outside ``REAPPROACH_PHASES`` ends all (no event).
  S7          sum L >= alpha W_ref and min L < beta F_min on ``lower_estimate_N[k]``.
  S8          true (rules 4: the stored command is not the P30fz-stage value; safe side).
Silent records list the blocked conditions: per condition the LEVEL steps where it was false,
and the step with the fewest false conditions.

Confirmation 1 (rules 4): ``lower_estimate_N`` is L-hat of rules 1.1.
  ``verdict_runs.LoggedController._logged_lower_estimate_N`` logs
  ``self._load_estimate_N(self._state.last_forces.lower)`` after ``update``. In ``c2.py``
  ``_read`` sets ``state.last_forces = forces`` and builds the reading with
  ``cylinder_force_lower_N = forces.lower`` (the same array), so the logged input is
  ``reading.cylinder_force_lower_N``. ``_load_estimate_N`` subtracts ``_leg_seal_bands_N()`` =
  ``TwoPressureMonitor.leg_seal_bands_N(state.seal_band_N)``: ``state.seal_band_N`` is assigned
  only after a probe round (``c2.py`` ``_update_seal_band`` path, PROBE phase), and the
  fallback legs change only in ``TwoPressureMonitor.read`` (``_diagnose_sensors``,
  ``_check_moving``, ``_check_physical_lower_bound``) or ``probe_round_finished`` (PROBE). In a
  LEVEL update neither runs after ``_read``, so the value logged after the update equals the one
  the wrapper reads inside ``_level_step``. (``ContactJudge.PRESSURE`` returns the reading
  unchanged in both.) The ``--gate-npz-dir`` records use the same logger; V-1 checks it on runs.
Confirmation 2 (rules 4): in a soil-response run before the LOC every LEVEL step has
  ``in_crawler_zone`` true at the wrapper point. ``_level_step`` calls
  ``_update_crawler_zone`` (before ``_apply_pre_loc_lift_pause``); with ``config.soil.enable`` it
  ends with ``_hold_crawler_zone_until_liftoff``, which returns early only when
  ``soil.is_liftoff_confirmed``; otherwise a released latch is set back
  (``state.in_crawler_zone = True``, starting the soil mode). S3 (no LOC in the run) implies no
  LOC confirmed now, so S1 and S2 and S3 give S5. The instrumented runs count the steps where
  this failed (``las.gates.zone_false_with_s1_s3``, V-1 requires 0).
Same-time order: every event above is raised at ``reading.t_s`` = ``t_s[k]`` and, except the
  LOC revocation (after the command, not read here), before the wrapper point of that update.

Usage (dynamics-dev python, project root):
  python -I -B .../las_shadow.py judge (--t4h DIR_OR_NPZ ... | --jsonl X --t4h-dir D)
      [--candidate b0 | custom --alpha ...] --out <jsonl>
  python -I -B .../las_shadow.py v1 --instrumented <las_V1.jsonl> --npz-dir DIR
  python -I -B .../las_shadow.py v2 --shadow <judge out jsonl> [--count 3] [--candidate b0]
      [--workers 3] [--affinity HEX] --out <jsonl>
The last stdout line is JSON. Exit codes: 0 done / check passed, 1 check failed (V-1, V-2) or
run errors, 2 input error.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import las_targeted as lt  # noqa: E402  (first: sets the one-thread variables numpy reads)
import numpy as np  # noqa: E402

FIRES = "fires"
SILENT = "silent"
UNDECIDABLE = "undecidable"
LOC_EVENTS = ("crawler_liftoff_confirmed", "INFO_SOIL_STATE_RESTORED")
SOIL_MODE_EVENT = "soil_mode_start"
S4_FAULT_EVENT = "WARN_CRAWLER_LIFTOFF_UNCONFIRMED"
REAPPROACH_START = "leg_reapproach_start"
REAPPROACH_ENDS = ("leg_reapproach_contact", "WARN_LEG_REAPPROACH_NO_CONTACT")
REAPPROACH_PHASES = ("level", "done", "probe", "ready")
RELEVEL_FROM = ("done", "probe", "ready")
RELEVEL_TO = ("level", "fault", "fault_reground")
REQUIRED_ARRAYS = ("t_s", "phase", "lower_estimate_N", "meta_json")
TIME_TOLERANCE_S = 1e-9
V1_MIN_RECORDS = 10
V1_MIN_EACH = 3
V2_COUNT = 3


# ------------------------------------------------------------------------------- record
@dataclass(frozen=True)
class ShadowRecord:
    """The fields of one T4h record the gate needs."""

    name: str
    t_s: np.ndarray
    phase: np.ndarray
    lower_estimate_N: np.ndarray
    events: list[tuple[float, str]]
    F_min_N: float
    weight_ref_N: float | None
    soil_enable: bool | None
    job: dict | None
    commands_sha256: str | None


def read_record(path: Path) -> tuple[ShadowRecord | None, str | None]:
    """(record, None) or (None, why it cannot be judged)."""
    with np.load(path, allow_pickle=False) as data:
        missing = [name for name in REQUIRED_ARRAYS if name not in data.files]
        if missing:
            return None, f"missing {missing}"
        meta = json.loads(str(data["meta_json"]))
        record = ShadowRecord(
            name=path.name, t_s=np.asarray(data["t_s"], float),
            phase=np.asarray(data["phase"]).astype(str),
            lower_estimate_N=np.asarray(data["lower_estimate_N"], float).reshape(-1, 4),
            events=[(float(t), str(name)) for t, name in meta.get("events") or []],
            F_min_N=meta.get("F_min_N"), weight_ref_N=meta.get("W_ref_N"),
            soil_enable=meta.get("soil_enable"), job=meta.get("job"),
            commands_sha256=meta.get("commands_sha256"))
    if "events" not in meta:
        return None, "missing meta events"
    if record.F_min_N is None:
        return None, "missing meta F_min_N"
    return record, None


_YAML_WEIGHT: dict = {}


def yaml_weight_ref_N() -> float:
    """``C2Controller._reference_weight_N`` from the YAML (superstructure mass x g)."""
    if "W" not in _YAML_WEIGHT:
        from outrigger_sim.params import load_params
        from outrigger_sim.sensors.imu import STANDARD_GRAVITY_M_S2

        mass_kg = load_params().superstructure.mass_properties.mass_kg
        _YAML_WEIGHT["W"] = float(mass_kg) * STANDARD_GRAVITY_M_S2
    return _YAML_WEIGHT["W"]


# ------------------------------------------------------------------------------- gates
def _events_up_to(events: list[tuple[float, str]], t_s: float) -> list[str]:
    return [name for t, name in events if t <= t_s + TIME_TOLERANCE_S]


def _events_at(events: list[tuple[float, str]], t_s: float) -> list[str]:
    return [name for t, name in events if abs(t - t_s) <= TIME_TOLERANCE_S]


def level_step_flags(phase: np.ndarray) -> np.ndarray:
    """Whether update k ran ``_level_step`` (module docstring)."""
    flags = np.zeros(len(phase), bool)
    for k in range(1, len(phase)):
        entering, after = phase[k - 1], phase[k]
        flags[k] = entering == "level" or (entering in RELEVEL_FROM and after in RELEVEL_TO)
    return flags


def reapproach_active(record: ShadowRecord) -> np.ndarray:
    """Whether a re-approach is active at the wrapper point of update k (S6 false)."""
    active: set[str] = set()
    out = np.zeros(len(record.t_s), bool)
    by_time: dict[int, list[str]] = {}
    for t, name in record.events:
        k = int(np.searchsorted(record.t_s, t - TIME_TOLERANCE_S))
        if k < len(record.t_s) and abs(record.t_s[k] - t) <= TIME_TOLERANCE_S:
            by_time.setdefault(k, []).append(name)
    for k in range(len(record.t_s)):
        entering = record.phase[k - 1] if k else ""
        if entering not in REAPPROACH_PHASES:
            active.clear()
        for name in by_time.get(k, []):
            head, _, leg = name.partition(":")
            if head == REAPPROACH_START:
                active.add(leg)
            elif head in REAPPROACH_ENDS:
                active.discard(leg)
        out[k] = bool(active)
    return out


def _first_time(events: list[tuple[float, str]], heads: tuple[str, ...]) -> float | None:
    times = [t for t, name in events if name.split(":")[0] in heads]
    return min(times) if times else None


def gate_matrix(record: ShadowRecord, params: lt.LasParams) -> dict[str, np.ndarray]:
    """S1 .. S8 per update (booleans) and the LEVEL-step flag."""
    t_s = record.t_s
    count = len(t_s)
    weight_N = record.weight_ref_N if record.weight_ref_N is not None else yaml_weight_ref_N()
    soil = True if record.soil_enable is None else bool(record.soil_enable)
    level = level_step_flags(record.phase)
    s4_fault = np.array([S4_FAULT_EVENT in [n.split(":")[0] for n in _events_at(record.events, t)]
                         for t in t_s], bool)
    t_loc = _first_time(record.events, LOC_EVENTS)
    t_soil = _first_time(record.events, (SOIL_MODE_EVENT,))
    loads = record.lower_estimate_N
    with np.errstate(invalid="ignore"):
        s7 = (loads.sum(axis=1) >= params.alpha * weight_N) & (
            loads.min(axis=1) < params.beta * record.F_min_N)
    return {
        "level": level,
        "S1": np.full(count, soil),
        "S2": level & ~s4_fault,
        "S3": np.array([t_loc is None or t < t_loc - TIME_TOLERANCE_S for t in t_s], bool),
        "S4": np.array([t_soil is None or t < t_soil - TIME_TOLERANCE_S for t in t_s], bool),
        "S5": np.ones(count, bool),
        "S6": ~reapproach_active(record),
        "S7": s7 & np.isfinite(loads).all(axis=1),
        "S8": np.ones(count, bool),
    }


def shadow_judge(record: ShadowRecord, params: lt.LasParams) -> dict:
    """``fires`` / ``silent`` / ``undecidable`` of one record and why."""
    gates = gate_matrix(record, params)
    names = lt.GATE_NAMES
    stacked = np.stack([gates[name] for name in names], axis=1)
    before_s7 = stacked[:, :6].all(axis=1)
    has_nan_where_needed = bool((before_s7 & ~np.isfinite(record.lower_estimate_N).all(axis=1))
                                .any())
    fired = np.flatnonzero(stacked.all(axis=1))
    assumptions = []
    if record.weight_ref_N is None:
        assumptions.append("W_ref from YAML")
    if record.soil_enable is None:
        assumptions.append("S1 assumed true")
    out = {"file": record.name, "job": record.job, "commands_sha256": record.commands_sha256,
           "assumptions": assumptions}
    if fired.size:
        k = int(fired[0])
        return {**out, "status": FIRES, "first_fire_t_s": float(record.t_s[k])}
    if has_nan_where_needed:
        return {**out, "status": UNDECIDABLE, "reason": "lower_estimate_N NaN where S1 .. S6 hold"}
    level_rows = np.flatnonzero(gates["S2"])
    false_counts = {name: int((~gates[name][level_rows]).sum()) for name in names}
    closest = None
    if level_rows.size:
        misses = (~stacked[level_rows]).sum(axis=1)
        best = int(level_rows[int(np.argmin(misses))])
        closest = {"t_s": float(record.t_s[best]),
                   "false": [name for name in names if not gates[name][best]]}
    return {**out, "status": SILENT, "first_fire_t_s": None,
            "blocked": {"level_steps": int(level_rows.size), "false_counts": false_counts,
                        "closest": closest}}


def judge_file(path: Path, params: lt.LasParams) -> dict:
    record, why = read_record(path)
    if record is None:
        return {"file": path.name, "status": UNDECIDABLE, "reason": why}
    return shadow_judge(record, params)


# ------------------------------------------------------------------------------- inputs
def npz_files(paths: list[Path]) -> list[Path]:
    out = []
    for path in paths:
        out += sorted(path.rglob("*.npz")) if path.is_dir() else [path]
    return out


def files_of_jsonl(jsonl: Path, t4h_dir: Path) -> list[tuple[dict, Path | None]]:
    """(line, npz or None) per line: ``t4h_file`` (run_v5) or ``las.gate_npz``."""
    out = []
    for text in jsonl.read_text(encoding="utf-8").splitlines():
        line = json.loads(text)
        name = line.get("t4h_file") or (line.get("las") or {}).get("gate_npz")
        out.append((line, None if name is None else t4h_dir / name))
    return out


def params_from_args(args) -> lt.LasParams:
    (_, params), = lt.resolve_candidates([args.candidate], args)
    if params.kind != lt.KIND_LASB:
        raise ValueError("the shadow judge is defined for LAS-b variants only")
    return params


def run_judge(args) -> int:
    params = params_from_args(args)
    results = []
    if args.jsonl is not None:
        for line, path in files_of_jsonl(args.jsonl, args.t4h_dir):
            if path is None or not path.exists():
                results.append({"file": None if path is None else path.name, "job": line["job"],
                                "status": UNDECIDABLE, "reason": "no T4h record"})
            else:
                results.append(judge_file(path, params))
    else:
        results = [judge_file(path, params) for path in npz_files(args.t4h)]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, default=str) + "\n")
    counts = {status: sum(r["status"] == status for r in results)
              for status in (FIRES, SILENT, UNDECIDABLE)}
    reasons: dict[str, int] = {}
    for result in results:
        if result["status"] == UNDECIDABLE:
            reasons[result["reason"]] = reasons.get(result["reason"], 0) + 1
    print(f"{len(results)} records: {counts}; undecidable reasons {reasons}")
    print(json.dumps({"command": "judge", "params": params.to_dict(), "records": len(results),
                      **counts, "undecidable_reasons": reasons, "out": str(args.out)}))
    return 0


# ------------------------------------------------------------------------------- V-1
def v1_compare(line: dict, npz_dir: Path) -> dict:
    """In-run first S1 .. S7 time against the offline judge of the run's own record."""
    las = line.get("las") or {}
    params = lt.LasParams.from_dict(las["params"])
    gates = las.get("gates") or {}
    online = gates.get("first_s1_s7_t_s")
    offline = judge_file(npz_dir / las["gate_npz"], params)
    off_t = offline.get("first_fire_t_s")
    is_same = (online is None and off_t is None) or (
        online is not None and off_t is not None and abs(online - off_t) <= TIME_TOLERANCE_S)
    return {"key": las.get("key"), "setting": line["job"].get("setting"),
            "online_first_s": online, "offline_first_s": off_t,
            "offline_status": offline["status"],
            "zone_false_with_s1_s3": gates.get("zone_false_with_s1_s3"),
            "match": bool(is_same and offline["status"] != UNDECIDABLE
                          and gates.get("zone_false_with_s1_s3") == 0)}


def v1_verdict(rows: list[dict]) -> dict:
    fires = sum(row["online_first_s"] is not None for row in rows)
    silent = sum(row["online_first_s"] is None for row in rows)
    settings = sorted({row["setting"] for row in rows})
    problems = []
    if len(rows) < V1_MIN_RECORDS:
        problems.append(f"{len(rows)} records < {V1_MIN_RECORDS}")
    if fires < V1_MIN_EACH or silent < V1_MIN_EACH:
        problems.append(f"fires {fires}, silent {silent} (>= {V1_MIN_EACH} each)")
    if not {"V0", "VB"} <= set(settings):
        problems.append(f"settings {settings} (VB and V0 needed)")
    mismatched = [row["key"] for row in rows if not row["match"]]
    if mismatched:
        problems.append(f"mismatch {mismatched}")
    return {"command": "v1", "records": len(rows), "fires": fires, "silent": silent,
            "settings": settings, "passed": not problems, "problems": problems}


def run_v1(args) -> int:
    lines = [json.loads(t) for t in args.instrumented.read_text(encoding="utf-8").splitlines()]
    good = [line for line in lines if "error" not in line and (line.get("las") or {})
            .get("mode") == lt.MODE_GATE and (line.get("las") or {}).get("gate_npz")]
    rows = [v1_compare(line, args.npz_dir) for line in good]
    for row in rows:
        print(f"{row['key']:<52} online {row['online_first_s']} offline {row['offline_first_s']} "
              f"({row['offline_status']}) zone_false {row['zone_false_with_s1_s3']} "
              f"{'ok' if row['match'] else 'MISMATCH'}")
    verdict = v1_verdict(rows)
    verdict["error_lines"] = len(lines) - len(good)
    print(json.dumps(verdict))
    return 0 if verdict["passed"] else 1


# ------------------------------------------------------------------------------- V-2
def pick_silent(shadow_lines: list[dict], count: int) -> list[dict]:
    """The first ``count`` silent records with a stored job and command hash."""
    picked = [line for line in shadow_lines if line["status"] == SILENT and line.get("job")
              and line.get("commands_sha256")]
    return picked[:count]


def run_v2(args) -> int:
    params = params_from_args(args)
    shadow_lines = [json.loads(t) for t in args.shadow.read_text(encoding="utf-8").splitlines()]
    picked = pick_silent(shadow_lines, args.count)
    if len(picked) < args.count:
        print(json.dumps({"command": "v2", "error": f"{len(picked)} silent records with a job"}))
        return 2
    mask = None if args.affinity is None else int(args.affinity, 16)
    jobs = lt.with_las([dict(line["job"]) for line in picked], args.candidate, params,
                       lt.MODE_ACT, mask)
    import run_v5  # noqa: F401  (sys.path of the harness, as las_targeted.run_batch)
    import verdict_runs

    verdict_runs.warm_numba_cache()
    with get_context("spawn").Pool(args.workers, maxtasksperchild=1) as pool:
        reruns = pool.map(lt.run_las_job, jobs)
    rows = []
    for line, rerun in zip(picked, reruns, strict=True):
        new_hash = rerun.get("commands_sha256")
        rows.append({"file": line["file"], "stored": line["commands_sha256"], "rerun": new_hash,
                     "error": rerun.get("error"), "started": (rerun.get("las") or {})
                     .get("start_t_s"), "equal": new_hash == line["commands_sha256"]})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for rerun in reruns:
            rerun["job"].pop("mask", None)
            handle.write(json.dumps(rerun, default=str) + "\n")
    for row in rows:
        print(f"{row['file']}: stored {row['stored'][:12]} rerun {str(row['rerun'])[:12]} "
              f"{'equal' if row['equal'] else 'DIFFERENT'}")
    passed = all(row["equal"] for row in rows)
    print(json.dumps({"command": "v2", "passed": passed, "rows": rows}))
    return 0 if passed else 1


# ------------------------------------------------------------------------------- CLI
def _add_candidate_args(parser) -> None:
    parser.add_argument("--candidate", default="b0")
    for name in ("--alpha", "--beta", "--gamma", "--alpha-end", "--t-max"):
        parser.add_argument(name, type=float)
    parser.add_argument("--n-end", type=int)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    judge = sub.add_parser("judge", help="fires / silent / undecidable per record")
    judge.add_argument("--t4h", type=Path, nargs="*", default=[])
    judge.add_argument("--jsonl", type=Path, default=None)
    judge.add_argument("--t4h-dir", type=Path, default=None)
    judge.add_argument("--out", type=Path, required=True)
    _add_candidate_args(judge)
    v1 = sub.add_parser("v1", help="instrumented runs against the offline judge")
    v1.add_argument("--instrumented", type=Path, required=True)
    v1.add_argument("--npz-dir", type=Path, required=True)
    v2 = sub.add_parser("v2", help="rerun silent records with the variant, compare hashes")
    v2.add_argument("--shadow", type=Path, required=True)
    v2.add_argument("--count", type=int, default=V2_COUNT)
    v2.add_argument("--workers", type=int, default=V2_COUNT)
    v2.add_argument("--affinity", default=None)
    v2.add_argument("--out", type=Path, required=True)
    _add_candidate_args(v2)
    args = parser.parse_args(argv)
    try:
        if args.command == "judge":
            if (args.jsonl is None) == (not args.t4h):
                raise ValueError("give --t4h or --jsonl with --t4h-dir")
            if args.jsonl is not None and args.t4h_dir is None:
                raise ValueError("--jsonl needs --t4h-dir")
            return run_judge(args)
        if args.command == "v1":
            return run_v1(args)
        return run_v2(args)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"command": args.command, "error": repr(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
