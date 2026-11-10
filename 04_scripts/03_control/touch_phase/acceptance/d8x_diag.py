"""D8x J3 diagnosis (not a judgement): R-a runs again with 1 ms series, and boundary baselines.

The runs go through ``acc_d8.run_one`` itself (D8x mode, the same case builder
``acc_d8.d8x_cases``, the same K1 install ``d8x_record.install_k1_order_gate``), so a
rerun must give the stored ``commands_sha256``. Two read-only recorders are added in this
process: one after every plant chunk (``FlexPlant.step``) and one after every controller
update (``HarnessAdapter.update``). They copy state and change nothing.

Nothing written here is a D8x record: the outputs carry ``"diagnostic": true`` and do not go
to ``06_analysis/02_control/d8x/ra``.

Usage (project root, dynamics-dev, ``MKL_THREADING_LAYER=TBB``, ``*_NUM_THREADS=1``)::

    python -I -B d8x_diag.py rerun --k1 off --ids "<id>,<id>" --out-dir <dir>
        [--stored <ra_off.json>[,<ra_on.json>]] [--workers N]
    python -I -B d8x_diag.py boundary --k1 off --half-spans 5.5,3.5 --out <file.json>
        [--levels top] [--stages main,robust,kt] [--series fail|all|none] [--workers N]

``rerun`` writes ``<dir>/<slug>.npz`` per id and ``<dir>/rerun_summary.json``. ``boundary``
builds the 16 R-a point tags on the symmetric diamond with the given half spans
(:func:`diamond_points`), resumes from ``<file>.partial.jsonl`` and writes ``<file>`` and the
series of the selected runs to ``<file stem>_series/``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from multiprocessing import Pool
from pathlib import Path

os.environ["ACC_D8X"] = "1"  # before acc_d8 is imported: the D8x path (preset, this checkout)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import acc_d8  # noqa: E402
import numpy as np  # noqa: E402

D8X_K1_ENV = acc_d8.D8X_K1_ENV
LEG_NAMES = ("FL", "FR", "RL", "RR")
EVENT_LOOKBACK_S = 2.0
"""Events listed before each pad-lift interval."""
SERIES_CHOICES = ("fail", "all", "none")

# Columns of ``FlexPlant.hist`` (record mode, a[11:45], ``run_mast_flex_c2_check``).
HIST_PAD_LAST = slice(0, 4)
HIST_CRAWLER_NORMAL = 4
HIST_PRESSURE_MAX = slice(5, 9)
HIST_PRESSURE_MIN = slice(9, 13)
HIST_PAD_MIN = slice(13, 17)
"""Minimum pad axial force over the chunk: the J3 value (``acc_d8._d8x_fields``)."""
HIST_PAD_TANGENTIAL_X = slice(17, 21)
HIST_PAD_TANGENTIAL_Y = slice(21, 25)
HIST_CRAWLER_TANGENTIAL = 25

_CHUNKS: list[dict] = []
_UPDATES: list[dict] = []
_INSTALLED: dict = {}


# ------------------------------------------------------------------------------- points
def diamond_points(roll_half_deg: float, pitch_half_deg: float) -> dict[str, tuple[float, float]]:
    """The 16 R-a tags of ``d8x_points.json`` on a symmetric diamond.

    Axis vertices, ``r<sr>p<sp><f>`` at roll = f * roll_half, pitch = (1 - f) * pitch_half
    (``run_target_envelope._slope_of_tag``), and ``d45<sr><sp>`` on the diamond at
    |roll| = |pitch| = roll_half * pitch_half / (roll_half + pitch_half), rounded to 4
    decimals as the point file. (The D8x file keeps the nose-down d45 at the literal
    2.2627 deg, R_v 1.0085; here every point has R_v = 1 to rounding.)
    """
    points = {"pitch+": (0.0, pitch_half_deg), "pitch-": (0.0, -pitch_half_deg),
              "roll+": (roll_half_deg, 0.0), "roll-": (-roll_half_deg, 0.0)}
    for tag, fraction, roll_sign, pitch_sign in (
            ("r+p+0.25", 0.25, 1, 1), ("r+p+0.5", 0.5, 1, 1), ("r+p+0.75", 0.75, 1, 1),
            ("r+p-0.25", 0.25, 1, -1), ("r+p-0.5", 0.5, 1, -1), ("r+p-0.75", 0.75, 1, -1),
            ("r-p+0.5", 0.5, -1, 1), ("r-p-0.5", 0.5, -1, -1)):
        points[tag] = (round(roll_sign * fraction * roll_half_deg, 4),
                       round(pitch_sign * (1.0 - fraction) * pitch_half_deg, 4))
    diagonal = round(roll_half_deg * pitch_half_deg / (roll_half_deg + pitch_half_deg), 4)
    for tag, roll_sign, pitch_sign in (("d45++", 1, 1), ("d45-+", -1, 1), ("d45+-", 1, -1),
                                       ("d45--", -1, -1)):
        points[tag] = (roll_sign * diagonal, pitch_sign * diagonal)
    return points


def id_slug(run_id: str) -> str:
    """File name of a run id (``|`` -> ``__``, ``+`` -> ``P``; other signs kept)."""
    text = run_id.replace("|", "__").replace("+", "P")
    return re.sub(r"[^A-Za-z0-9._-]", "_", text)


# ---------------------------------------------------------------------------- recorders
def _c2py():
    import c2py_r8d1_closed_loop as c2py

    return c2py


def install_recorders() -> None:
    """Wrap ``FlexPlant.step`` and ``HarnessAdapter.update`` with read-only recorders (once)."""
    if _INSTALLED:
        return
    c2py = _c2py()
    plant_class = c2py.rmf.FlexPlant
    adapter_class = c2py.HarnessAdapter
    previous_step = plant_class.step
    previous_update = adapter_class.update

    def step(self, u, nsteps):
        command = np.array(u, float)
        out = previous_step(self, u, nsteps)
        if nsteps > 1000:  # the crawler settle before the run: the plant drops its history too
            _CHUNKS.clear()
            return out
        _CHUNKS.append(_chunk_record(self, command))
        return out

    def update(self, m, t):
        speeds = previous_update(self, m, t)
        _UPDATES.append({"t": float(t), "phase": str(self.controller.phase),
                         "speed": np.array(speeds, float), "load": np.array(m["P"], float),
                         "stroke": np.array(m["x"], float),
                         "att_f": np.array(self.controller.filtered_attitude_rad, float)})
        return speeds

    plant_class.step = step
    adapter_class.update = update
    _INSTALLED.update(step=previous_step, update=previous_update)


def _chunk_record(plant, command: np.ndarray) -> dict:
    phi, theta = plant.attitude()
    valve = getattr(plant, "_uf", None)
    return {"t": float(plant.t), "x": np.array(plant.x, float), "sref": np.array(plant.sref, float),
            "u_cmd": command, "u_valve": None if valve is None else np.array(valve, float),
            "pflag": np.array(plant.pflag, np.int8), "cflag": np.array(plant.cflag, np.int8),
            "clearance": float(plant.crawler_clearance()), "att": (float(phi), float(theta)),
            "w": np.array(plant.w, float)}


def _reset_recorders() -> None:
    _CHUNKS.clear()
    _UPDATES.clear()


# ------------------------------------------------------------------------------- series
def collect_series(row: dict) -> dict[str, np.ndarray]:
    """1 ms and controller-period arrays of the run just finished in this process."""
    c2py = _c2py()
    plant = c2py.rmf.LAST["plant"]
    hist = np.asarray(plant.hist, float)
    t_hist = np.asarray(plant.hist_t, float)
    if len(_CHUNKS) != len(t_hist):
        raise RuntimeError(f"chunk recorder {len(_CHUNKS)} rows, plant history {len(t_hist)}")
    t_chunks = np.array([c["t"] for c in _CHUNKS])
    if not np.array_equal(t_chunks, t_hist):
        raise RuntimeError("chunk recorder times differ from the plant history times")
    crawler_xy = np.asarray(plant.cr_rel, float)[:, :2] + np.asarray(plant.body.com, float)[:2]
    return {
        "t_s": t_hist,
        "pad_normal_min_N": hist[:, HIST_PAD_MIN],
        "pad_normal_last_N": hist[:, HIST_PAD_LAST],
        "rod_weight_N": np.asarray(plant.Wr, float),
        "crawler_normal_N": hist[:, HIST_CRAWLER_NORMAL],
        "crawler_tangential_x_N": hist[:, HIST_CRAWLER_TANGENTIAL],
        "pad_tangential_x_N": hist[:, HIST_PAD_TANGENTIAL_X],
        "pad_tangential_y_N": hist[:, HIST_PAD_TANGENTIAL_Y],
        "pressure_force_max_N": hist[:, HIST_PRESSURE_MAX],
        "pressure_force_min_N": hist[:, HIST_PRESSURE_MIN],
        "stroke_m": np.array([c["x"] for c in _CHUNKS]),
        "motor_stroke_m": np.array([c["sref"] for c in _CHUNKS]),
        "command_m_s": np.array([c["u_cmd"] for c in _CHUNKS]),
        "valve_m_s": np.array([c["u_valve"] if c["u_valve"] is not None else np.full(4, np.nan)
                               for c in _CHUNKS]),
        "pad_contact": np.array([c["pflag"] for c in _CHUNKS]),
        "crawler_contact": np.array([c["cflag"] for c in _CHUNKS]),
        "crawler_point_xy_m": crawler_xy,
        "crawler_clearance_m": np.array([c["clearance"] for c in _CHUNKS]),
        "att_rad": np.array([c["att"] for c in _CHUNKS]),
        "body_rate_rad_s": np.array([c["w"] for c in _CHUNKS]),
        "ctrl_t_s": np.array([u["t"] for u in _UPDATES]),
        "ctrl_phase": np.array([u["phase"] for u in _UPDATES]),
        "ctrl_speed_m_s": np.array([u["speed"] for u in _UPDATES]),
        "ctrl_load_N": np.array([u["load"] for u in _UPDATES]),
        "ctrl_stroke_m": np.array([u["stroke"] for u in _UPDATES]),
        "ctrl_att_filtered_rad": np.array([u["att_f"] for u in _UPDATES]),
        "event_t_s": np.array([float(t) for t, _ in row["d8x"]["events"]]),
        "event_name": np.array([str(name) for _, name in row["d8x"]["events"]]),
        "t_touch_s": np.float64(np.nan if row["d8x"]["t_touch_s"] is None
                                else row["d8x"]["t_touch_s"]),
        "t_lift_s": np.float64(np.nan if row["d8x"]["t_lift_s"] is None
                               else row["d8x"]["t_lift_s"]),
    }


def _intervals(mask: np.ndarray, t_s: np.ndarray) -> list[list[float]]:
    """Runs of True as [t_first, t_last] (chunk end times)."""
    edges = np.flatnonzero(np.diff(np.concatenate([[0], mask.astype(np.int8), [0]])))
    starts, stops = edges[::2], edges[1::2]
    return [[float(t_s[start]), float(t_s[stop - 1])]
            for start, stop in zip(starts, stops, strict=True)]


def _snapshot(series: dict, index: int) -> dict:
    ctrl_index = int(np.searchsorted(series["ctrl_t_s"], series["t_s"][index], side="right")) - 1
    contact = series["crawler_contact"][index]
    crawler_x = series["crawler_point_xy_m"][:, 0]
    return {
        "t_s": float(series["t_s"][index]),
        "phase": str(series["ctrl_phase"][ctrl_index]) if ctrl_index >= 0 else None,
        "pad_normal_kN": np.round(series["pad_normal_min_N"][index] / 1e3, 3).tolist(),
        "stroke_mm": np.round(series["stroke_m"][index] * 1e3, 2).tolist(),
        "oil_compression_mm": np.round((series["motor_stroke_m"][index]
                                        - series["stroke_m"][index]) * 1e3, 3).tolist(),
        "command_mm_s": np.round(series["command_m_s"][index] * 1e3, 3).tolist(),
        "valve_mm_s": np.round(series["valve_m_s"][index] * 1e3, 3).tolist(),
        "crawler_normal_kN": round(float(series["crawler_normal_N"][index]) / 1e3, 2),
        "crawler_contact_front_rear": [int(contact[crawler_x > 0].sum()),
                                       int(contact[crawler_x <= 0].sum())],
        "crawler_clearance_mm": round(float(series["crawler_clearance_m"][index]) * 1e3, 3),
        "att_deg": np.round(np.degrees(series["att_rad"][index]), 4).tolist(),
        "body_rate_deg_s": np.round(np.degrees(series["body_rate_rad_s"][index]), 4).tolist(),
    }


def pad_lift_summary(series: dict) -> dict:
    """Which pads lose contact after the TOUCH end (pad normal <= 0, the J3 test), when, and the
    state at the start of each interval."""
    t_s = series["t_s"]
    t_touch = float(series["t_touch_s"])
    after_touch = (t_s >= t_touch - 1e-9) if np.isfinite(t_touch) else np.zeros_like(t_s, bool)
    rod_weight = series["rod_weight_N"][None, :]
    pad = (series["pad_normal_min_N"] - rod_weight) + rod_weight  # the J3 arithmetic, bit for bit
    lifted = (pad <= 0.0) & after_touch[:, None]
    legs = {}
    for leg, name in enumerate(LEG_NAMES):
        mask = lifted[:, leg]
        entry = {"chunks": int(mask.sum()),
                 "min_after_touch_kN": (round(float(pad[after_touch, leg].min()) / 1e3, 3)
                                        if after_touch.any() else None)}
        if mask.any():
            entry["intervals_s"] = _intervals(mask, t_s)
            entry["start_states"] = [_snapshot(series, int(np.searchsorted(t_s, start)))
                                     for start, _ in entry["intervals_s"][:3]]
            entry["events_before_first"] = _events_between(
                series, entry["intervals_s"][0][0] - EVENT_LOOKBACK_S, entry["intervals_s"][0][1])
        legs[name] = entry
    return {"t_touch_s": t_touch, "t_lift_s": float(series["t_lift_s"]),
            "J3_recount": int(lifted.any(axis=1).sum()), "legs": legs}


def _events_between(series: dict, t_from: float, t_to: float) -> list[list]:
    times, names = series["event_t_s"], series["event_name"]
    keep = (times >= t_from - 1e-9) & (times <= t_to + 1e-9)
    return [[round(float(t), 3), str(n)] for t, n in zip(times[keep], names[keep], strict=True)]


# ---------------------------------------------------------------------------------- runs
def diag_run(task: dict) -> dict:
    """``acc_d8.run_one`` with the recorders; adds the ``diag`` block and saves the series."""
    install_recorders()
    _reset_recorders()
    row = acc_d8.run_one(task["case"])
    if "error" in row:
        return row
    series = collect_series(row)
    summary = pad_lift_summary(series)
    row["diag"] = summary
    failed = summary["J3_recount"] > 0
    series_dir = task.get("series_dir")
    if series_dir and (task["save"] == "all" or (task["save"] == "fail" and failed)):
        path = Path(series_dir) / f"{id_slug(row['id'])}.npz"
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **series)
        row["diag"]["series_file"] = path.name
    return row


def _all_cases(points: dict, stages: tuple[str, ...], levels: tuple[str, ...]) -> list[dict]:
    cases = acc_d8.d8x_cases(points, stages)
    return [case for case in cases if case["d8x"]["level"] in levels]


def _run_pool(tasks: list[dict], workers: int, sink_path: Path | None = None) -> list[dict]:
    rows = []
    t0 = time.perf_counter()
    sink = sink_path.open("a", encoding="utf-8") if sink_path else None
    try:
        with Pool(max(1, min(workers, len(tasks)))) as pool:
            for n, row in enumerate(pool.imap_unordered(diag_run, tasks, chunksize=1), 1):
                rows.append(row)
                if sink:
                    sink.write(json.dumps(row, default=float) + "\n")
                    sink.flush()
                j3 = (row.get("diag") or {}).get("J3_recount")
                print(f"[{n}/{len(tasks)} {time.perf_counter() - t0:.0f} s] {row['id']} "
                      f"J3 {j3} {row.get('error', '')[:200]}", flush=True)
    finally:
        if sink:
            sink.close()
    return rows


def _check_main_tree() -> None:
    bad = acc_d8.acc_common.main_tree_modules()
    if bad:
        raise SystemExit(f"main-tree modules imported: {bad[:5]}")


def _meta(args: argparse.Namespace, identity_start: dict, extra: dict) -> dict:
    record = acc_d8._record_module()
    return {"diagnostic": True, "not_a_d8x_record": "D8x J3 diagnosis; no judgement reads this",
            "command": args.command, "k1": args.k1, **extra,
            "provenance": acc_d8.acc_common.provenance(),
            "identity_start": identity_start, "identity_end": record.run_identity(acc_d8.REPO_ROOT)}


# --------------------------------------------------------------------------------- rerun
def _stored_rows(paths: list[Path]) -> dict[str, dict]:
    rows = {}
    for path in paths:
        doc = json.loads(path.read_text(encoding="utf-8"))
        arm = doc["meta"]["d8x"]["k1"]
        for row in doc["runs"]:
            rows[f"{arm}:{row['id']}"] = row
    return rows


def _compare_stored(row: dict, stored: dict | None) -> dict:
    if stored is None:
        return {"stored": False}
    keys = ("J3_pad_lift_samples", "J3_pad_normal_min_N", "t_touch_s", "t_lift_s", "t_ready_s")
    return {"stored": True,
            "commands_sha256_equal": stored["commands_sha256"] == row["commands_sha256"],
            "d8x_equal": {key: stored["d8x"][key] == row["d8x"][key] for key in keys},
            "events_equal": stored["d8x"]["events"] == row["d8x"]["events"]}


def command_rerun(args: argparse.Namespace) -> None:
    record = acc_d8._record_module()
    identity_start = record.run_identity(acc_d8.REPO_ROOT)
    points = record.ra_point_angles(record.load_points(args.points))
    by_id = {case["id"]: case for case in acc_d8.d8x_cases(points, acc_d8.D8X_STAGES)}
    missing = [run_id for run_id in args.ids if run_id not in by_id]
    if missing:
        raise SystemExit(f"ids not in the D8x R-a cases: {missing}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    tasks = [{"case": by_id[run_id], "series_dir": str(args.out_dir), "save": "all"}
             for run_id in args.ids]
    rows = _run_pool(tasks, args.workers)
    _check_main_tree()
    stored = _stored_rows(args.stored)
    for row in rows:
        row["stored_compare"] = _compare_stored(row, stored.get(f"{args.k1}:{row['id']}"))
    module_lists = acc_d8._pop_module_lists(rows)
    order = {run_id: n for n, run_id in enumerate(args.ids)}
    rows.sort(key=lambda row: order[row["id"]])
    meta = _meta(args, identity_start, {"points_file": str(args.points),
                                        "stored": [str(p) for p in args.stored],
                                        "module_files_by_sha256": module_lists})
    out = args.out_dir / "rerun_summary.json"
    out.write_text(json.dumps({"meta": meta, "runs": rows}, indent=1, default=float),
                   encoding="utf-8")
    print("done", out, flush=True)


# ------------------------------------------------------------------------------ boundary
def command_boundary(args: argparse.Namespace) -> None:
    record = acc_d8._record_module()
    identity_start = record.run_identity(acc_d8.REPO_ROOT)
    roll_half, pitch_half = args.half_spans
    points = diamond_points(roll_half, pitch_half)
    cases = _all_cases(points, args.stages, args.levels)
    partial = args.out.with_name(args.out.name + ".partial.jsonl")
    series_dir = args.out.with_name(args.out.stem + "_series")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    done = {}
    if partial.exists():
        for line in partial.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            done[row["id"]] = row
    tasks = [{"case": case, "series_dir": str(series_dir), "save": args.series}
             for case in cases if case["id"] not in done]
    print(f"cases {len(cases)}, done {len(done)}, to run {len(tasks)}", flush=True)
    if tasks:
        for row in _run_pool(tasks, args.workers, partial):
            done[row["id"]] = row
    _check_main_tree()
    rows = [done[case["id"]] for case in cases]
    module_lists = acc_d8._pop_module_lists(rows)
    meta = _meta(args, identity_start, {
        "half_spans_deg": {"roll": roll_half, "pitch": pitch_half}, "points": points,
        "levels": list(args.levels), "stages": list(args.stages), "n": len(rows),
        "module_files_by_sha256": module_lists})
    args.out.write_text(json.dumps({"meta": meta, "runs": rows}, indent=1, default=float),
                        encoding="utf-8")
    print("done", args.out, "errors", sum("error" in row for row in rows), flush=True)


# ---------------------------------------------------------------------------------- main
def _comma_list(text: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in text.split(",") if part.strip())


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="D8x J3 diagnosis (not a judgement)")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("rerun", "boundary"):
        command = sub.add_parser(name)
        command.add_argument("--k1", required=True, choices=("off", "on"))
        command.add_argument("--workers", type=int, default=8)
    rerun = sub.choices["rerun"]
    rerun.add_argument("--ids", required=True, type=lambda s: list(_comma_list(s)),
                       help="comma list of stored R-a ids (with the cfg, e.g. main|C2_tv0.1|...)")
    rerun.add_argument("--out-dir", required=True, type=Path)
    rerun.add_argument("--points", type=Path, default=None, help="D8x point file (default)")
    rerun.add_argument("--stored", type=lambda s: [Path(p) for p in _comma_list(s)], default=[],
                       help="stored R-a files (ra_off.json, ra_on.json) to compare with")
    boundary = sub.choices["boundary"]
    boundary.add_argument("--half-spans", required=True,
                          type=lambda s: tuple(float(v) for v in _comma_list(s)),
                          help="roll,pitch half spans of the symmetric diamond, deg")
    boundary.add_argument("--out", required=True, type=Path)
    boundary.add_argument("--levels", type=_comma_list, default=("top",))
    boundary.add_argument("--stages", type=_comma_list, default=acc_d8.D8X_STAGES)
    boundary.add_argument("--series", choices=SERIES_CHOICES, default="fail")
    args = parser.parse_args()
    if args.command == "boundary" and len(args.half_spans) != 2:
        parser.error("--half-spans: two values roll,pitch")
    return args


def main() -> None:
    args = _parse_args()
    os.environ[D8X_K1_ENV] = args.k1  # inherited by the spawned workers (acc_d8.run_one reads it)
    if args.command == "rerun":
        command_rerun(args)
    else:
        command_boundary(args)


if __name__ == "__main__":
    main()
