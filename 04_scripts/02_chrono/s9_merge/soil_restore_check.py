"""(나) check of the soil-state merge rule (다) (user decision 2026-10-26) on Chrono S8 ML runs.

For ML bases of the 768 plan the base is run from the start in this tree with the soil response
on (the R8 preset), and its ``branch.pkl`` episodes are compared with the same episodes started
from a base pickled by the controller before the soil response (``_RunState.soil`` None, e.g.
the R3 bases of the main tree, copied here), which get rule (다) on restore.

Usage (Chrono-dev python, any cwd)::

    python -I -X utf8 -u soil_restore_check.py base <base_id> <out_root>
    python -I -X utf8 -u soil_restore_check.py episode <episode_id> <base_dir> <out_dir> [<s>]
    python -I -X utf8 -u soil_restore_check.py drive <out_root> <old_bases_dir> \
        <base_id>:<ep>,<ep> ...
    python -I -X utf8 -u soil_restore_check.py compare <out_root> <old_bases_dir> <out.json>

Outputs ``<out_root>/bases_on/<base_id>/``, ``<out_root>/episodes_native/<episode_id>/``
(from ``bases_on``) and ``<out_root>/episodes_restored/<episode_id>/`` (from the old base).
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import pickle
import subprocess
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHRONO = HERE.parent
ROOT = CHRONO.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(CHRONO))

PLAN = ROOT / "07_results" / "S8" / "ml_main_20261025_090131" / "ml_plan.json"
"""The 768 plan of the S8 ML main run (read only)."""
CONCURRENT_RUNS = 2
SOIL_EVENTS = ("INFO_SOIL_STATE_RESTORED", "crawler_liftoff_confirmed", "soil_mode_start",
               "INFO_CLEARANCE_BIAS", "WARN_CRAWLER_LIFTOFF_UNCONFIRMED", "WARN_WEIGHT_MISMATCH")


def _plan() -> dict:
    return json.loads(PLAN.read_text(encoding="utf-8"))


def _base(base_id: str):
    import run_S8C as s8c

    doc = next(b for b in _plan()["bases"] if b["base_id"] == base_id)
    return s8c.MLBase(**s8c._tuples(doc))


def _episode(episode_id: str) -> dict:
    base_id = episode_id.split("_")[0]
    return next(e for e in _plan()["episodes"][base_id] if e["episode_id"] == episode_id)


def _prepare_process() -> dict:
    from outrigger_sim import hostcpu

    placement = hostcpu.place_process("pcore")
    import outrigger_sim

    src = Path(outrigger_sim.__file__).resolve()
    if not src.is_relative_to(ROOT.resolve()):
        raise RuntimeError(f"outrigger_sim imported from {src}, not from {ROOT}")
    return {"placement": placement, "outrigger_sim_file": str(src)}


def _foreign_modules() -> list[str]:
    files = {str(Path(m.__file__).resolve()) for m in list(sys.modules.values())
             if getattr(m, "__file__", None) and "outrigger" in str(m.__file__)}
    return sorted(f for f in files if not Path(f).is_relative_to(ROOT.resolve()))


def _write_result(case_dir: Path, summary: dict, info: dict, wall_s: float) -> None:
    import run_S8C as s8c

    summary["soil_restore_check"] = {**info, "wall_s": wall_s,
                                     "foreign_project_modules": _foreign_modules()}
    (case_dir / "result.json").write_text(
        json.dumps(s8c.s6c._plain(summary), indent=1, ensure_ascii=False), encoding="utf-8")


def run_base(base_id: str, out_root: Path) -> None:
    info = _prepare_process()
    import run_S8C as s8c

    case_dir = out_root / "bases_on" / base_id
    case_dir.mkdir(parents=True, exist_ok=False)
    wall0 = time.perf_counter()
    summary = s8c.job_ml_base(_base(base_id), case_dir)
    _write_result(case_dir, summary, info, time.perf_counter() - wall0)


def run_episode(episode_id: str, base_dir: Path, out_dir: Path,
                episode_s: float | None = None) -> None:
    """``episode_s``: shorter episode (smoke test only)."""
    info = _prepare_process()
    import run_S8C as s8c

    case_dir = out_dir / episode_id
    case_dir.mkdir(parents=True, exist_ok=False)
    wall0 = time.perf_counter()
    summary = s8c.job_ml_episode(_base(episode_id.split("_")[0]), _episode(episode_id),
                                 base_dir, case_dir, episode_s=episode_s)
    _write_result(case_dir, summary, info, time.perf_counter() - wall0)


# --- driver -------------------------------------------------------------------------------------


def _run(args: list[str], log: Path) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "w", encoding="utf-8") as handle:
        return subprocess.call([sys.executable, "-I", "-X", "utf8", "-u", __file__, *args],
                               stdout=handle, stderr=subprocess.STDOUT)


def drive(out_root: Path, old_bases: Path, specs: list[str]) -> None:
    """Bases first (two at a time), episodes from the old bases while they run, native
    episodes once their base exists."""
    plan: dict[str, list[str]] = {}
    for spec in specs:
        base_id, episodes = spec.split(":")
        plan[base_id] = episodes.split(",")
    logs = out_root / "logs"
    with concurrent.futures.ThreadPoolExecutor(CONCURRENT_RUNS) as pool:
        bases = {b: pool.submit(_run, ["base", b, str(out_root)], logs / f"base_{b}.log")
                 for b in plan}
        jobs = {}
        for b, episodes in plan.items():
            for ep in episodes:
                jobs[f"restored_{ep}"] = pool.submit(
                    _run, ["episode", ep, str(old_bases / b), str(out_root / "episodes_restored")],
                    logs / f"restored_{ep}.log")

        def native(base_id: str, episode_id: str) -> int:
            if bases[base_id].result() != 0:
                return -1
            return _run(["episode", episode_id, str(out_root / "bases_on" / base_id),
                         str(out_root / "episodes_native")], logs / f"native_{episode_id}.log")

        for b, episodes in plan.items():
            for ep in episodes:
                jobs[f"native_{ep}"] = pool.submit(native, b, ep)
        status = {f"base_{b}": f.result() for b, f in bases.items()}
        status.update({k: f.result() for k, f in jobs.items()})
    (out_root / "drive_status.json").write_text(json.dumps(status, indent=1), encoding="utf-8")
    print(json.dumps(status, indent=1), flush=True)


# --- compare ------------------------------------------------------------------------------------


def _sha(array) -> str:
    import numpy as np

    data = np.ascontiguousarray(np.asarray(array, dtype=np.float64))
    return hashlib.sha256(data.tobytes()).hexdigest()


def _series(run: Path) -> dict:
    import numpy as np

    with np.load(run / "r8_series.npz", allow_pickle=False) as r8:
        return {k: r8[k] for k in r8.files}


def _record(run: Path) -> dict:
    import numpy as np

    with np.load(run / "record" / "record.npz", allow_pickle=False) as rec:
        return {k: rec[k] for k in rec.files if rec[k].dtype.kind in "fiub"}


def _events(run: Path) -> list[str]:
    return json.loads((run / "controller_events.json").read_text(encoding="utf-8"))


def _without_soil(events: list[str]) -> list[str]:
    return [e for e in events if not any(name in e for name in SOIL_EVENTS)]


def _differing_keys(native: dict, restored: dict) -> dict:
    keys = sorted(set(native) | set(restored))
    return {k: {"native": native.get(k), "restored": restored.get(k)} for k in keys
            if native.get(k) != restored.get(k)}


def _pickled_soil(base_dir: Path) -> dict | None:
    with open(base_dir / "branch.pkl", "rb") as handle:
        blob = pickle.load(handle)  # noqa: S301 - own run of this check
    controller = blob["controller"]
    if getattr(controller._state, "soil", None) is None:
        return None
    return controller.meta()["soil"]


def compare_base(base_id: str, out_root: Path, old_bases: Path) -> dict:
    import numpy as np

    on_dir, old_dir = out_root / "bases_on" / base_id, old_bases / base_id
    on_r8, old_r8 = _series(on_dir), _series(old_dir)
    on_rec, old_rec = _record(on_dir), _record(old_dir)
    differing = [k for k in on_rec if k in old_rec and not np.array_equal(
        on_rec[k], old_rec[k], equal_nan=True)]
    on_result = json.loads((on_dir / "result.json").read_text(encoding="utf-8"))
    return {"base": base_id,
            "issued_u_sha_on": _sha(on_r8["issued_u"]),
            "issued_u_sha_old": _sha(old_r8["issued_u"]),
            "issued_u_equal": bool(np.array_equal(on_r8["issued_u"], old_r8["issued_u"])),
            "record_arrays_differing": differing,
            "events_equal_without_soil": _without_soil(_events(on_dir)) == _events(old_dir),
            "old_pickle_soil": _pickled_soil(old_dir),
            "on_pickle_soil": _pickled_soil(on_dir),
            "wall_s": on_result["soil_restore_check"]["wall_s"],
            "foreign_modules": on_result["soil_restore_check"]["foreign_project_modules"]}


def compare_episode(episode_id: str, out_root: Path, base_row: dict) -> dict:
    import numpy as np

    native_dir = out_root / "episodes_native" / episode_id
    restored_dir = out_root / "episodes_restored" / episode_id
    native_r8, restored_r8 = _series(native_dir), _series(restored_dir)
    native_res = json.loads((native_dir / "result.json").read_text(encoding="utf-8"))
    restored_res = json.loads((restored_dir / "result.json").read_text(encoding="utf-8"))
    native_rec, restored_rec = _record(native_dir), _record(restored_dir)
    differing = [k for k in native_rec if k in restored_rec and not np.array_equal(
        native_rec[k], restored_rec[k], equal_nan=True)]
    refreshed = restored_res["settings"]["settings_refreshed"]
    restored_loc = refreshed["soil_state"].get("offline_judge", {}).get("loc") or {}
    native_soil = base_row["on_pickle_soil"] or {}
    state_rows = {}
    for key, judge_key in (("t_P_s", "t_P_s"), ("t_loc_s", "t_loc_s"), ("W_hat_N", "W_hat_N"),
                           ("clearance_at_P_m", "clearance_at_P_m"),
                           ("clearance_at_loc_m", "clearance_at_loc_m")):
        state_rows[key] = {"native_pickle": native_soil.get(key),
                           "restored": restored_loc.get(judge_key)}
    restored_events = _events(restored_dir)
    return {
        "episode": episode_id, "kind": _episode(episode_id)["kind"],
        "issued_u_sha_native": _sha(native_r8["issued_u"]),
        "issued_u_sha_restored": _sha(restored_r8["issued_u"]),
        "issued_u_equal": bool(np.array_equal(native_r8["issued_u"], restored_r8["issued_u"])),
        "computed_u_equal": bool(np.array_equal(native_r8["computed_u"],
                                                restored_r8["computed_u"])),
        "n_periods": int(len(native_r8["t"])),
        "record_arrays_differing": differing,
        "events_equal_without_soil": _without_soil(_events(native_dir))
        == _without_soil(restored_events),
        "restore_events": [e for e in restored_events if "INFO_SOIL_STATE_RESTORED" in e],
        "soil_state_rule": refreshed["soil_state"].get("rule"),
        "soil_state_restored_vs_native_pickle": state_rows,
        "reapproach_max_duration_s": refreshed.get("reapproach_max_duration_s"),
        "native_soil_rule": native_res["settings"]["settings_refreshed"]["soil_state"]["rule"],
        "end_soil_meta_differing": _differing_keys(native_res["controller_meta"]["soil"],
                                                   restored_res["controller_meta"]["soil"]),
        "wall_s": {"native": native_res["wall_s"], "restored": restored_res["wall_s"]},
    }


def compare(out_root: Path, old_bases: Path, out: Path) -> None:
    rows = {"bases": [], "episodes": []}
    for base_dir in sorted((out_root / "bases_on").iterdir()):
        row = compare_base(base_dir.name, out_root, old_bases)
        rows["bases"].append(row)
        for ep_dir in sorted((out_root / "episodes_native").glob(f"{base_dir.name}_ep*")):
            rows["episodes"].append(compare_episode(ep_dir.name, out_root, row))
    out.write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")


def main(argv: list[str]) -> int:
    action = argv[0]
    if action == "base":
        run_base(argv[1], Path(argv[2]))
    elif action == "episode":
        run_episode(argv[1], Path(argv[2]), Path(argv[3]),
                    float(argv[4]) if len(argv) > 4 else None)
    elif action == "drive":
        drive(Path(argv[1]), Path(argv[2]), argv[3:])
    elif action == "compare":
        compare(Path(argv[1]), Path(argv[2]), Path(argv[3]))
    else:
        raise SystemExit(f"unknown action {action!r}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception:  # noqa: BLE001 - report the traceback in the job log, exit 1
        traceback.print_exc()
        sys.exit(1)
