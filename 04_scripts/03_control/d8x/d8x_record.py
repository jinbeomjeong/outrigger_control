"""D8x run-side records: the point file, the K1 switch and the per-run ``d8x`` block.

Rules ``06_analysis/02_control/d8x/d8x_rules.md`` (sealed, sha256 in ``d8x_rules.sha256``):
1.2 (point file), 2.1 (K1 arms, both set the gate explicitly since the K1 switch), 2.2 I-1
(run identity), 4.1 (the items
the judge reads), 6 E-2 / E-8 (times). The R-a driver (``acc_d8.py --points``) and the R-c rows
(``d1_runs.py``, group ``H-R-X``) import this module; the judge (``d8x_judge.py``) only reads
what they wrote. Nothing here judges.

The ``d8x`` block of a run (raw floats, no rounding, so the two-path recount can compare them
to 1e-9):

    t_touch_s, t_crawler_off_s, t_loc_s, t_lift_s (= the earlier of the two), t_ready_s, t_end_s
    J1_min_cyl_after_lift_N / _leg / _t_s, J1_window_s (t_end - t_lift, rule E-8)
    reanchor_intervals_s, J2_min_cyl_reanchor_N (None without an H4 interval)
    J3_pad_lift_samples (pad normal <= 0 after the TOUCH end), J3_pad_normal_min_N
    J4_att_max_after_ready_deg, J6_max_moving_bar, stroke_max_m
    events [[t_s, name], ...] (every controller event), k1_order_gate, controller_tag

Usage (closure of the imports of a bundle, for ``d8x_judge.py manifest``)::

    <python> -I -B 04_scripts/03_control/d8x/d8x_record.py import-closure --bundle ra|rc|C
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import platform
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D8X_DIR = ROOT / "06_analysis" / "02_control" / "d8x"
RULES_PATH = D8X_DIR / "d8x_rules.md"
DEFAULT_POINTS_PATH = D8X_DIR / "d8x_points.json"
POINTS_SCHEMA = "d8x_points/1"
POINTS_RULES_REV = "rev1"
"""Rev1 1.2: runs read only a point file built from the rev1 tables (``d8x_spec`` checks the
same value against the sealed files when it writes the file)."""
LEVELS = ("top", "middle", "bottom")
K1_CHOICES = ("off", "on")
LOC_EVENT = "crawler_liftoff_confirmed"
REANCHOR_START_EVENT = "reanchor_started"
REANCHOR_END_PREFIXES = ("reanchor_completed", "reanchor_aborted", "reanchor_band_exceeded")
THREAD_VARIABLES = ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "NUMBA_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS", "MKL_THREADING_LAYER")
TIME_TOLERANCE_S = 1e-9


# ------------------------------------------------------------------------------- point file
def text_sha256(path: Path) -> str:
    """SHA-256 of a text file with LF line ends (the same on a CRLF checkout)."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_points(path: Path | str | None = None) -> dict:
    """The point file written by ``d8x_judge.py points``.

    Raises:
        FileNotFoundError: No point file (run ``d8x_judge.py points`` first).
        ValueError: Another schema.
    """
    path = Path(path or DEFAULT_POINTS_PATH)
    if not path.is_file():
        raise FileNotFoundError(f"no D8x point file {path} (d8x_judge.py points writes it)")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != POINTS_SCHEMA:
        raise ValueError(f"{path}: schema {doc.get('schema')!r}, expected {POINTS_SCHEMA!r}")
    if doc.get("rules_rev") != POINTS_RULES_REV:
        raise ValueError(f"{path}: rules_rev {doc.get('rules_rev')!r}, expected "
                         f"{POINTS_RULES_REV!r} (rev1 1.2: the original point file is not used)")
    return doc


def _angles(entries: Iterable[dict], key: str) -> dict[str, tuple[float, float]]:
    return {entry[key]: (float(entry["roll_deg"]), float(entry["pitch_deg"])) for entry in entries}


def ra_point_angles(doc: dict) -> dict[str, tuple[float, float]]:
    """(A) boundary points, tag -> (roll, pitch) deg, in table order."""
    return _angles(doc["ra_points"], "tag")


def named_floor_angles(doc: dict) -> dict[str, tuple[float, float]]:
    """(B) rpX points and (C) axis vertices, name -> (roll, pitch) deg."""
    return {**_angles(doc["rpx_points"], "name"), **_angles(doc["axis_vertices"], "name")}


def rc_floor_angles(doc: dict) -> dict[str, tuple[float, float]]:
    """The eight R-c floors (rules 3, R-c table) in the point-file order."""
    named = named_floor_angles(doc)
    return {name: named[name] for name in doc["rc_floors"]}


# ---------------------------------------------------------------------------------------- K1
_K1_INSTALLED: dict = {}


def install_k1_order_gate(is_on: bool, controller_class=None) -> None:
    """Every controller of this process gets the K1 order gate set to ``is_on``.

    K1 is ``slope_clearance_margin.flat_soil_margin_order_gate`` (rules 2.1, the R4c30 order
    gate); nothing else changes (the ``k1_targeted.install_order_gate`` way). Both arms install
    explicitly: since the K1 switch (``las_k1_rules_adopt.md`` 9.1) the R8 preset has the gate
    on, so an off arm that installed nothing would silently run with the gate on. A second call
    with the same value in one process is a no-op.

    Raises:
        RuntimeError: Already installed in this process with the other value.
    """
    is_on = bool(is_on)
    if _K1_INSTALLED:
        if _K1_INSTALLED["is_on"] is not is_on:
            raise RuntimeError(f"d8x_record.install_k1_order_gate: installed with "
                               f"{_K1_INSTALLED['is_on']}, asked for {is_on}")
        return
    if controller_class is None:
        from outrigger_sim.control import c2

        controller_class = c2.C2Controller
    original_init = controller_class.__init__

    def __init__(self, geometry, config=None, *args, **kwargs):
        if config is not None:
            margin = replace(config.slope_clearance_margin, flat_soil_margin_order_gate=is_on)
            config = replace(config, slope_clearance_margin=margin)
        original_init(self, geometry, config, *args, **kwargs)

    controller_class.__init__ = __init__
    _K1_INSTALLED.update({"class": controller_class, "is_on": is_on})


def k1_arm_is_on(k1: str | None) -> bool:
    """``on`` / ``off`` of a D8x K1 arm as the gate value.

    Raises:
        ValueError: Anything else (a D8x run always names its arm; no silent preset fallback).
    """
    if k1 not in K1_CHOICES:
        raise ValueError(f"D8x K1 arm {k1!r}: expected one of {K1_CHOICES}")
    return k1 == "on"


def effective_k1(controller) -> bool:
    """The K1 order gate of a controller's configuration."""
    return bool(controller.config.slope_clearance_margin.flat_soil_margin_order_gate)


def liftoff_slow_enabled(controller) -> bool:
    """LAS-b (``liftoff_approach_slow.enable``) of a controller's configuration (rev2 4)."""
    settings = getattr(controller.config, "liftoff_approach_slow", None)
    return bool(getattr(settings, "enable", False))


def preset_controller_tag(controller) -> str | None:
    """The v5 tag of a controller without hydraulic options (``final_C4G2_LAS_K1`` with LAS-b
    and the K1 gate, ``final_C4G2_LAS`` with the gate off)."""
    from outrigger_sim.hydraulics.v5_options import controller_tag

    return controller_tag(None, controller.config)


def controller_events(controller) -> list[list]:
    """Every event of a controller as ``[t_s, name]``."""
    return [[float(event.t_s), str(event.name)] for event in controller.events]


# ------------------------------------------------------------------------------ run metrics
def _first_event_time(events: Sequence[Sequence], name: str) -> float | None:
    times = [float(t) for t, event_name in events if event_name == name]
    return min(times) if times else None


def reanchor_intervals(events: Sequence[Sequence], t_end_s: float) -> list[list[float]]:
    """H4 intervals: ``reanchor_started`` to its end event (the run end without one)."""
    intervals = []
    start = None
    for t, name in sorted(((float(t), str(n)) for t, n in events), key=lambda item: item[0]):
        if name == REANCHOR_START_EVENT and start is None:
            start = t
        elif start is not None and name.startswith(REANCHOR_END_PREFIXES):
            intervals.append([start, t])
            start = None
    if start is not None:
        intervals.append([start, float(t_end_s)])
    return intervals


def _masked_minimum(t_s: np.ndarray, force: np.ndarray, mask: np.ndarray) -> dict:
    if not mask.any():
        return {"value": None, "leg": None, "t_s": None}
    masked = np.where(mask[:, None], force, np.inf)
    index, leg = np.unravel_index(int(np.argmin(masked)), masked.shape)
    return {"value": float(force[index, leg]), "leg": int(leg), "t_s": float(t_s[index])}


def _earliest(*times: float | None) -> float | None:
    known = [float(t) for t in times if t is not None]
    return min(known) if known else None


def run_metrics(*, t_s, cyl_force_N, rod_weight_N, t_att_s, att_deg, t_touch_s, t_crawler_off_s,
                t_ready_s, events, max_moving_bar, stroke_max_m) -> dict:
    """The ``d8x`` block of one run (module docstring).

    Args:
        t_s: Times of the force samples (1 ms chunks or sub-steps), shape (N,).
        cyl_force_N: True cylinder force F_cyl per leg, shape (N, 4).
        rod_weight_N: Rod weight per leg; pad normal force = F_cyl + rod weight.
        t_att_s: Times of the attitude samples, shape (M,).
        att_deg: True deck (roll, pitch) in degrees, shape (M, 2).
        t_touch_s: End of TOUCH (all four pads grounded); None if never.
        t_crawler_off_s: First crawler load zero; None if never.
        t_ready_s: First READY; None if never.
        events: Controller events ``[t_s, name]``.
        max_moving_bar: Largest pressure while moving (the driver's own value).
        stroke_max_m: Largest stroke of the run (the driver's own value).
    """
    t_s = np.asarray(t_s, float)
    cyl = np.asarray(cyl_force_N, float).reshape(-1, 4)
    pad_normal = cyl + np.asarray(rod_weight_N, float).reshape(1, 4)
    t_att = np.asarray(t_att_s, float)
    att = np.asarray(att_deg, float).reshape(-1, 2)
    t_end = float(max(t_s[-1], t_att[-1]))
    t_loc = _first_event_time(events, LOC_EVENT)
    t_lift = _earliest(t_crawler_off_s, t_loc)
    after_lift = (t_s >= t_lift - TIME_TOLERANCE_S) if t_lift is not None else np.zeros_like(t_s,
                                                                                            bool)
    j1 = _masked_minimum(t_s, cyl, after_lift)
    intervals = reanchor_intervals(events, t_end)
    in_reanchor = np.zeros_like(t_s, bool)
    for start, end in intervals:
        in_reanchor |= (t_s >= start - TIME_TOLERANCE_S) & (t_s <= end + TIME_TOLERANCE_S)
    j2 = _masked_minimum(t_s, cyl, in_reanchor)
    after_touch = (t_s >= t_touch_s - TIME_TOLERANCE_S) if t_touch_s is not None else (
        np.zeros_like(t_s, bool))
    lifted = (pad_normal <= 0.0).any(axis=1) & after_touch
    after_ready = (t_att >= t_ready_s - TIME_TOLERANCE_S) if t_ready_s is not None else (
        np.zeros_like(t_att, bool))
    return {
        "t_touch_s": None if t_touch_s is None else float(t_touch_s),
        "t_crawler_off_s": None if t_crawler_off_s is None else float(t_crawler_off_s),
        "t_loc_s": t_loc, "t_lift_s": t_lift,
        "t_ready_s": None if t_ready_s is None else float(t_ready_s), "t_end_s": t_end,
        "J1_min_cyl_after_lift_N": j1["value"], "J1_leg": j1["leg"], "J1_t_s": j1["t_s"],
        "J1_window_s": None if t_lift is None else t_end - t_lift,
        "reanchor_intervals_s": intervals,
        "J2_min_cyl_reanchor_N": j2["value"],
        "J3_pad_lift_samples": int(lifted.sum()),
        "J3_pad_normal_min_N": (float(pad_normal[after_touch].min())
                                if after_touch.any() else None),
        "J4_att_max_after_ready_deg": (float(np.abs(att[after_ready]).max())
                                       if after_ready.any() else None),
        "J6_max_moving_bar": None if max_moving_bar is None else float(max_moving_bar),
        "stroke_max_m": None if stroke_max_m is None else float(stroke_max_m),
        "events": [[float(t), str(name)] for t, name in events],
    }


# ---------------------------------------------------------------------------------- identity
def repo_module_files(root: Path = ROOT) -> list[str]:
    """Repository files of the modules loaded in this process (posix, relative to ``root``)."""
    root = Path(root).resolve()
    files = set()
    for module in list(sys.modules.values()):
        path = getattr(module, "__file__", None)
        if not path:
            continue
        try:
            resolved = Path(path).resolve()
        except OSError:
            continue
        if root in resolved.parents and resolved.suffix == ".py":
            files.add(resolved.relative_to(root).as_posix())
    return sorted(files)


def files_digest(files: Sequence[str]) -> str:
    """SHA-256 of a sorted file list (one name per line)."""
    return hashlib.sha256("\n".join(sorted(files)).encode("utf-8")).hexdigest()


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                               encoding="utf-8", timeout=60, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def git_state(root: Path = ROOT) -> dict:
    """HEAD and ``git status --porcelain --untracked-files=no`` (rules I-1)."""
    status = _git(root, "status", "--porcelain", "--untracked-files=no")
    return {"head": _git(root, "rev-parse", "HEAD"), "status_porcelain": status,
            "is_clean": status == ""}


def _affinity_mask() -> str | None:
    try:
        import psutil
    except ImportError:
        return None
    cpus = psutil.Process().cpu_affinity()
    return hex(sum(1 << cpu for cpu in cpus))


def run_identity(root: Path = ROOT) -> dict:
    """Interpreter, thread variables, affinity and git state of this process (rules I-1)."""
    return {"python": sys.executable, "python_version": platform.python_version(),
            "threads": {name: os.environ.get(name) for name in THREAD_VARIABLES},
            "affinity_mask": _affinity_mask(), "git": git_state(root)}


# ---------------------------------------------------------------------------- import closure
CLOSURE_PATHS = ("03_src", "04_scripts/03_control/touch_phase/acceptance",
                 "04_scripts/03_control/r8d1", "04_scripts/03_control", "04_scripts/01_dynamics",
                 "04_scripts/04_hydraulic/coupled", "04_scripts/03_control/s9",
                 "04_scripts/03_control/m1_check", "04_scripts/02_chrono")
CLOSURE_MODULES = {
    "ra": ("acc_d8", "c2py_r8d1_closed_loop", "run_s6_slope_boundary_check", "d8x_record"),
    "rc": ("run_v5", "d1_rows", "d1_runs", "verdict_runs", "run_m1", "s9_soil_slope",
           "s9_soil_closed_loop", "run_control_comparison", "d8x_record"),
    "C": ("run_S6C", "run_S8C", "s6_stage2", "s9_batch"),
}
"""Entry modules imported by ``import-closure`` per bundle (rules 2.2 table)."""


def import_closure(bundle: str) -> dict:
    """Import the entry modules of a bundle and list the repository files loaded."""
    os.environ.setdefault("ACC_WT", str(ROOT))
    os.environ["ACC_D8X"] = "1"
    for sub in reversed(CLOSURE_PATHS):
        text = str(ROOT / sub)
        if text not in sys.path:
            sys.path.insert(0, text)
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    errors = {}
    for name in CLOSURE_MODULES[bundle]:
        try:
            module = importlib.import_module(name)
            if name == "s9_soil_closed_loop":
                module._imports()
        except Exception as exc:  # recorded: the manifest reports what could not be imported
            errors[name] = repr(exc)
    return {"bundle": bundle, "python": sys.executable, "files": repo_module_files(ROOT),
            "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser(description="D8x run-side helpers")
    sub = parser.add_subparsers(dest="command", required=True)
    closure = sub.add_parser("import-closure", help="repository files a bundle imports")
    closure.add_argument("--bundle", required=True, choices=sorted(CLOSURE_MODULES))
    args = parser.parse_args()
    print(json.dumps(import_closure(args.bundle)))


if __name__ == "__main__":
    main()
