"""V-7 SCM record rows for K-2 path 1 ``record-v7`` (rules ``k2_touch_creep_rules.md`` 3.6, record only).

RECORD ONLY, WRITTEN AFTER THE RESULTS (2026-11-11). The V-7 rows ran through ``s9_batch.py run k2_v7``, which
does not call ``k2_chrono_rows.finish_case``; the case folders hold ``result.json``, ``step_series.npz`` and
``record/`` but no ``k2_row.json`` / ``k2_pads.npz``. ``k2_chrono_rows.k2_row`` reads the L1 / L2b record format
(``pads.npz`` with ``F_cyl_min_interval``, ``settings.start_t_s``) and does not apply. This adapter reads the
SCM case files read-only and writes, OUTSIDE the result folder, one ``k2_row.json`` (the V-6 key set) and one
``k2_pads.npz`` (``t``, ``N``) per case. It writes nothing into the batch folder and runs no simulation. Every row
carries ``record_only``, the note :data:`RECORD_NOTE`, the SHA-256 of each input file and of this script, and the
definition differences :data:`DEFINITION_DIFFERENCES` against the V-6 rows.

Rules 3.6 record items (``v7_record`` block of each row): J3, TOUCH end time, ``INFO_TOUCH_CREEP_CAP`` count,
the K-2 latch time and, per leg, the sinkage stroke at the latch, first READY, LOC time, the minimum force after
the crawler lift-off. The other keys repeat the V-6 row (``k2_chrono_rows.k2_row``) with the SCM sources listed
in :data:`DEFINITION_DIFFERENCES`.

Sub-commands::

    rows           --batch <batch folder> --out-dir <folder> [--overwrite]
    fill-manifest  --manifest <k2_manifest.json> --batch-v7 <rows folder> --out <filled copy>

Common contract: ``--out-report <file>`` (the summary JSON), ``--format json|md``; exit 0 done, 1 a case is
incomplete (missing file, non-zero rc), 2 input error (bad folder, output inside the batch, existing output
without ``--overwrite``, a placeholder left), 3 internal error; the last stdout line is JSON.
Interpreter: dynamics-dev or python-dev (numpy only; ``03_src`` / ``d8x_record`` / ``k2_chrono_rows`` helpers).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _folder in (ROOT / "03_src", ROOT / "04_scripts" / "02_chrono", ROOT / "04_scripts" / "03_control" / "d8x"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

import d8x_record  # noqa: E402  (LOC event name, H4 intervals, earliest time)
import k2_chrono_rows as rows_v6  # noqa: E402  (V-6 helpers: latch window, off edge, masked minimum, JSON plain)

EXIT_DONE = 0
EXIT_INCOMPLETE = 1
EXIT_INPUT = 2
EXIT_INTERNAL = 3

TOOL = "k2_v7_scm_rows"
RECORD_NOTE = "record only, written after the results (2026-11-11)"
"""User decision D-6 (2026-11-11): new code after the V-7 results; rules 3.6 rows are records, not judgements."""
LEG_NAMES = ("FL", "FR", "RL", "RR")
EXPECTED_CASES = (
    "K2V7_P3b_J1_B_top_Fs4_off",
    "K2V7_P3b_J1_B_top_Fs4_tcl",
    "K2V7_P3b_J2_B_top_Fs4_off",
    "K2V7_P3b_J2_B_top_Fs4_tcl",
)
INPUT_FILES = ("result.json", "step_series.npz", "record/record.npz", "record/meta.json")
ROW_FILE = rows_v6.ROW_FILE
PADS_FILE = rows_v6.PADS_FILE
TIME_TOL_S = rows_v6.TIME_TOL_S
MOVING_EPS_M_S = 1.0e-6
"""``s6_control.MOVING_EPS_M_S`` (J6 moving sample: ``|u_applied|`` above it), copied to keep the import light."""
READY_DELAY_REPORT_S = 10.0
"""Rules 3.6: a READY delay over +10 s against the off pair is reported to the user."""
PLACEHOLDER = "{BATCH_V7}"
PLACEHOLDER_PATTERN = re.compile(r"\{[A-Z][A-Z0-9_]*\}")

DEFINITION_DIFFERENCES = (
    "time base: seconds from result.json t_loop_start_s (closed-loop start after the 8 s gravity settle); V-6 uses "
    "settings.start_t_s. Events, phases and the 1 ms series are shifted by the same t0 (t0_s in the row); "
    "touch_creep_meta is copied as the controller wrote it (absolute times, as in V-6).",
    "J1 / J2: minimum of the 1 ms step_series.npz F_cyl_N samples (acting force, one sample per 1 ms = 10 physics "
    "steps of dt 1e-4 s); V-6 uses the per-physics-step interval minimum pads.npz F_cyl_min_interval. A minimum "
    "between two 1 ms samples is not seen (the V-7 value can be higher than the step minimum).",
    "J3 and the latch window: SCM terrain normal force on each pad, step_series.npz scm_pad_normal_N (1 ms); V-6 "
    "uses the Chrono contact pad normal of pads.npz (1 ms). Same window (from t_touch_s), threshold (<= 0 N) and "
    "latch-window rule (k2_chrono_rows.latch_window_normals).",
    "t_crawler_off_s / t_liftoff_final_s: record/record.npz F_crawler z > 0 at the 10 Hz control instants (first "
    "on -> off edge / last on sample + 1, the s6_control._times rule). On soil the SCM crawler normal can stay small "
    "and positive after the departure; the P3a-2 departure (normal < 0.01 W for 0.1 s) is given as "
    "p3b_departure_s for comparison.",
    "J4: 1 ms step_series.npz roll_pitch_deg minus the controller target (controller_meta.target.target_rad) from "
    "the first READY; V-6 uses the record-rate body quaternion.",
    "J6: record/record.npz F_cyl / head area (result meta.actuator.head_area_m2), moving = |u_applied| > 1e-6 m/s, "
    "at the 10 Hz record instants (the V-6 rule on the SCM record).",
    "J10 crawler_recontact_after_loc: p3b P3-1_crawler.recontact_count (SCM rule: crawler normal >= 0.01 W after the "
    "first departure); V-6 uses s6_control.d8x_metrics after the LOC event.",
    "controller_tag: c2_setup.expect_controller.name, used only when every check of that block is ok (the run "
    "refuses to start otherwise); the SCM result.json has no k2.controller_tag. k1_order_gate = "
    "c2_setup.k1_order_gate_effective, touch_creep_latch = c2_setup.touch_creep_effective, touch_creep_requested = "
    "c2_setup.touch_creep.",
    "floor_true_deg: result.json args floor_roll / floor_pitch; fs_kN: args fs_kN. moving_damping False and "
    "pad_zeta_moving None (no moving pad damping on SCM), valve_open_fraction_touch_to_lift None (no pad_damping.npz).",
    "k2 (D_hat): dhat_N = controller_meta.touch_twist_hold.twist_load_estimate_N; no 1 ms valve / stroke recorder on "
    "SCM, so the window fields are None (V-6 reads k2_valve.npz).",
    "new V-7 keys (rules 3.6 'sinkage stroke at the latch' per leg): v7_record.latch_legs.<leg> gives the "
    "controller creep_travel_m at the latch (stroke travel after touch_seen, controller_meta.touch_creep_latch."
    "latches) and the 1 ms s_motor_m and pad_sinkage_geometric_m at the last sample at or before the latch time; "
    "pad_sinkage_geometric_m sign as step_series (positive = pad bottom below the undisturbed soil surface, "
    "negative = above it).",
)


class InputError(ValueError):
    """Bad arguments or folders (exit 2)."""


# ------------------------------------------------------------------------------------------ helpers
def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _now() -> str:
    return dt.datetime.now(dt.UTC).astimezone().isoformat(timespec="seconds")


def _is_within(path: Path, folder: Path) -> bool:
    path, folder = path.resolve(), folder.resolve()
    return path == folder or folder in path.parents


def _first_phase(phases: list[tuple[float, str]], name: str) -> float | None:
    return next((t for t, phase in phases if phase == name), None)


def touch_end_s(phases: list[tuple[float, str]]) -> float | None:
    """First phase change out of ``touch`` (the ``s6_control._times`` TOUCH end)."""
    for (_, phase), (t_next, phase_next) in zip(phases[:-1], phases[1:], strict=True):
        if phase == "touch" and phase_next != "touch":
            return t_next
    return None


def last_off_edge_s(t_s: np.ndarray, is_on: np.ndarray) -> float | None:
    """Sample after the last ``True`` (the ``s6_control._times`` lift-off), None when it is the last sample."""
    on = np.flatnonzero(is_on)
    if not on.size or on[-1] + 1 >= len(t_s):
        return None
    return float(t_s[on[-1] + 1])


def sample_at(t_s: np.ndarray, values: np.ndarray, t_query: float) -> np.ndarray | None:
    """Last sample at or before ``t_query`` (None before the first sample)."""
    index = int(np.searchsorted(t_s, t_query + TIME_TOL_S)) - 1
    return None if index < 0 else values[index]


def _all_checks_ok(expect: dict) -> bool:
    checks = expect.get("checks") or []
    return bool(checks) and all(check.get("ok") is True for check in checks) and expect.get("ok", True) is True


# ------------------------------------------------------------------------------------------ case data
class ScmCase:
    """Read-only view of one V-7 case folder (result.json, step_series.npz, record/record.npz)."""

    def __init__(self, folder: Path) -> None:
        self.folder = Path(folder)
        self.result = json.loads((self.folder / "result.json").read_text(encoding="utf-8"))
        self.t0_s = float(self.result["t_loop_start_s"])
        with np.load(self.folder / "step_series.npz", allow_pickle=False) as series:
            self.series = {key: np.asarray(series[key]) for key in series.files}
        with np.load(self.folder / "record" / "record.npz", allow_pickle=False) as record:
            self.record = {key: np.asarray(record[key]) for key in record.files}
        self.t_series_s = self.series["t_s"].astype(float) - self.t0_s
        self.t_record_s = self.record["t"].astype(float) - self.t0_s

    @property
    def phases(self) -> list[tuple[float, str]]:
        return [(float(p["t_s"]) - self.t0_s, str(p["phase"])) for p in self.result["phases"]]

    @property
    def events(self) -> list[list]:
        return [[float(e["t_s"]) - self.t0_s, str(e["name"])] for e in self.result["events"]]

    @property
    def controller_meta(self) -> dict:
        return self.result.get("controller_meta") or {}

    @property
    def c2_setup(self) -> dict:
        return self.result.get("c2_setup") or {}

    @property
    def pad_normal_N(self) -> np.ndarray:
        return self.series["scm_pad_normal_N"].astype(float).reshape(-1, 4)

    @property
    def cyl_force_N(self) -> np.ndarray:
        return self.series["F_cyl_N"].astype(float).reshape(-1, 4)

    @property
    def t_end_s(self) -> float:
        return float(max(self.t_series_s[-1], self.t_record_s[-1]))


# ------------------------------------------------------------------------------------------ row items
def _times(case: ScmCase) -> dict[str, float | None]:
    phases = case.phases
    crawler_on = case.record["F_crawler"].astype(float)[:, 2] > 0.0
    t_off = rows_v6._first_off_edge(case.t_record_s, crawler_on)
    t_loc = next((t for t, name in case.events if name == d8x_record.LOC_EVENT), None)
    departure = ((case.result.get("p3b") or {}).get("departure") or {}).get("t_departure_s")
    return {
        "touch_start": _first_phase(phases, "touch"),
        "touch": touch_end_s(phases),
        "ready": _first_phase(phases, "ready"),
        "crawler_off": t_off,
        "liftoff_final": last_off_edge_s(case.t_record_s, crawler_on),
        "loc": t_loc,
        "lift": d8x_record._earliest(t_off, t_loc),
        "departure": None if departure is None else float(departure) - case.t0_s,
    }


def _force_minima(case: ScmCase, times: dict, events: list[list]) -> dict[str, Any]:
    t_s, force = case.t_series_s, case.cyl_force_N
    t_lift = times["lift"]
    after_lift = t_s >= t_lift - TIME_TOL_S if t_lift is not None else np.zeros_like(t_s, bool)
    j1 = rows_v6._masked_min(t_s, force, after_lift)
    intervals = d8x_record.reanchor_intervals(events, case.t_end_s)
    in_h4 = np.zeros_like(t_s, bool)
    for start, end in intervals:
        in_h4 |= (t_s >= start - TIME_TOL_S) & (t_s <= end + TIME_TOL_S)
    j2 = rows_v6._masked_min(t_s, force, in_h4)
    return {
        "J1_min_cyl_after_lift_N": j1["value"], "J1_leg": j1["leg"], "J1_t_s": j1["t_s"],
        "J1_window_s": None if t_lift is None else case.t_end_s - t_lift,
        "reanchor_intervals_s": intervals, "J2_min_cyl_reanchor_N": j2["value"],
    }


def _pad_items(case: ScmCase, t_touch: float | None) -> dict[str, Any]:
    t_s, normal = case.t_series_s, case.pad_normal_N
    after_touch = t_s >= t_touch - TIME_TOL_S if t_touch is not None else np.zeros_like(t_s, bool)
    return {
        "J3_pad_lift_samples": int(((normal <= 0.0).any(axis=1) & after_touch).sum()),
        "J3_pad_normal_min_N": float(normal[after_touch].min()) if after_touch.any() else None,
    }


def _attitude_and_pressure(case: ScmCase, t_ready: float | None) -> dict[str, Any]:
    target_deg = np.degrees(np.asarray((case.controller_meta.get("target") or {}).get("target_rad", (0.0, 0.0)),
                                       float))
    error_deg = case.series["roll_pitch_deg"].astype(float).reshape(-1, 2) - target_deg
    t_s = case.t_series_s
    after_ready = t_s >= t_ready - TIME_TOL_S if t_ready is not None else np.zeros_like(t_s, bool)
    head_area_m2 = np.asarray(case.result["meta"]["actuator"]["head_area_m2"], float)
    pressure_bar = case.record["F_cyl"].astype(float) / head_area_m2 / 1e5
    moving = np.abs(case.record["u_applied"].astype(float)) > MOVING_EPS_M_S
    return {
        "J4_att_max_after_ready_deg": float(np.abs(error_deg[after_ready]).max()) if after_ready.any() else None,
        "J6_max_moving_bar": float(pressure_bar[moving].max()) if moving.any() else None,
        "J6_max_locked_bar": float(pressure_bar[~moving].max()) if (~moving).any() else None,
    }


def _latch_legs(case: ScmCase) -> dict[str, Any]:
    """Rules 3.6: per latched leg the latch time and the sinkage stroke at the latch (last definition item)."""
    latches = (case.controller_meta.get("touch_creep_latch") or {}).get("latches") or []
    sinkage = case.series["pad_sinkage_geometric_m"].astype(float).reshape(-1, 4)
    stroke = case.series["s_motor_m"].astype(float).reshape(-1, 4)
    legs = {}
    for latch in latches:
        leg = str(latch["leg"])
        index = LEG_NAMES.index(leg)
        t_latch = float(latch["t_s"]) - case.t0_s
        sink = sample_at(case.t_series_s, sinkage, t_latch)
        motor = sample_at(case.t_series_s, stroke, t_latch)
        legs[leg] = {
            "latch_t_s": t_latch, "reason": latch.get("reason"),
            "creep_travel_m": latch.get("creep_travel_m"),
            "s_motor_m": None if motor is None else float(motor[index]),
            "pad_sinkage_geometric_m": None if sink is None else float(sink[index]),
        }
    return legs


def _identity(case: ScmCase) -> dict[str, Any]:
    setup = case.c2_setup
    expect = setup.get("expect_controller") or {}
    args = case.result.get("args") or {}
    return {
        "case_id": args.get("case") or case.folder.name, "engine": "SCM",
        "controller_tag": expect.get("name") if _all_checks_ok(expect) else None,
        "k1_order_gate": bool(setup.get("k1_order_gate_effective")),
        "touch_creep_latch": bool(setup.get("touch_creep_effective")),
        "touch_creep_requested": setup.get("touch_creep"),
        "floor_true_deg": [float(args.get("floor_roll", 0.0)), float(args.get("floor_pitch", 0.0))],
        "fs_kN": args.get("fs_kN"), "moving_damping": False, "pad_zeta_moving": None,
    }


def _dhat(case: ScmCase) -> dict[str, Any]:
    hold = case.controller_meta.get("touch_twist_hold") or {}
    return {"dhat_N": hold.get("twist_load_estimate_N"), "dhat_window_open_legs": None,
            "dhat_window_stroke_mm": None, "dhat_window_s": None, "valve_open_eps_m_s": None,
            "dhat_source": "controller_meta.touch_twist_hold.twist_load_estimate_N",
            "window_source": None, "window_note": "no 1 ms valve / stroke recorder on SCM"}


def v7_record(row: dict, latch_legs: dict) -> dict[str, Any]:
    """The rules 3.6 record items of one row."""
    latch_times = [leg["latch_t_s"] for leg in latch_legs.values()]
    return {
        "J3_pad_lift_samples": row["J3_pad_lift_samples"], "J3_pad_normal_min_N": row["J3_pad_normal_min_N"],
        "t_touch_s": row["t_touch_s"], "cap_events": row["cap_events"],
        "latch_events": sum(1 for _, name in row["events"] if name.startswith(rows_v6.LATCH_EVENT)),
        "latch_last_t_s": max(latch_times) if latch_times else None,
        "latch_legs": latch_legs, "t_ready_s": row["t_ready_s"], "t_loc_s": row["t_loc_s"],
        "J1_min_cyl_after_lift_N": row["J1_min_cyl_after_lift_N"],
    }


def scm_row(case: ScmCase) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    """The V-7 row of one case (V-6 key set + ``v7_record``) and its 1 ms pad series ``(t, N)``."""
    times = _times(case)
    events = case.events
    latches = rows_v6.latch_window_normals(case.t_series_s, case.pad_normal_N, events)
    p3_recontact = ((case.result.get("p3b") or {}).get("P3-1_crawler") or {}).get("recontact_count")
    row = {
        **_identity(case),
        "t_touch_start_s": times["touch_start"], "t_touch_s": times["touch"],
        "t_crawler_off_s": times["crawler_off"], "t_loc_s": times["loc"], "t_lift_s": times["lift"],
        "t_liftoff_final_s": times["liftoff_final"], "t_ready_s": times["ready"], "t_end_s": case.t_end_s,
        **_force_minima(case, times, events),
        **_pad_items(case, times["touch"]),
        **_attitude_and_pressure(case, times["ready"]),
        "crawler_recontact_after_loc": p3_recontact,
        "crawler_recontact_anchor": "p3b.P3-1_crawler.recontact_count (after the first departure, 0.01 W)",
        "latch_window_true_N": latches,
        "false_latch_legs": sorted(leg for leg, value in latches.items() if value["false_latch"]),
        "cap_events": sum(1 for _, name in events if name.startswith(rows_v6.CAP_EVENT)),
        "touch_creep_meta": case.controller_meta.get("touch_creep_latch"),
        "valve_open_fraction_touch_to_lift": None, "valve_open_window_s": None,
        "k2": _dhat(case), "events": events,
        "p3b_departure_s": times["departure"], "t0_s": case.t0_s,
    }
    row["v7_record"] = v7_record(row, _latch_legs(case))
    return row, case.t_series_s, case.pad_normal_N


# ------------------------------------------------------------------------------------------ rows command
def _case_inputs(folder: Path) -> dict[str, str]:
    missing = [name for name in INPUT_FILES if not (folder / name).is_file()]
    if missing:
        raise FileNotFoundError(f"{folder.name}: missing {missing}")
    return {name: file_sha256(folder / name) for name in INPUT_FILES}


def _batch_cases(batch: Path) -> dict[str, dict]:
    doc = json.loads((batch / "batch.json").read_text(encoding="utf-8"))
    return {str(case["case"]): case for case in doc.get("cases", [])}


def _row_meta(case_name: str, inputs: dict, batch_case: dict | None) -> dict[str, Any]:
    return {
        "record_only": True, "note": RECORD_NOTE, "tool": TOOL, "tool_sha256": file_sha256(Path(__file__)),
        "written": _now(), "rules": "06_analysis/02_control/k2/k2_touch_creep_rules.md 3.6",
        "input_sha256": inputs, "batch_rc": None if batch_case is None else batch_case.get("rc"),
        "definition_differences": list(DEFINITION_DIFFERENCES),
        "definitions": "k2_v7_scm_rows module docstring + definition_differences (V-6: k2_chrono_rows.k2_row)",
        "time_base": "seconds from result.json t_loop_start_s (t0_s)",
        "files": {"pads": PADS_FILE},
        "row": {"name": case_name, "engine": "SCM", "source_case": case_name.removeprefix("K2V7_").rsplit("_", 1)[0],
                "arm": case_name.rsplit("_", 1)[1]},
    }


def _check_out_dir(batch: Path, out_dir: Path, overwrite: bool) -> None:
    if not (batch / "batch.json").is_file():
        raise InputError(f"no batch.json in {batch}")
    if _is_within(out_dir, batch) or _is_within(batch, out_dir):
        raise InputError(f"--out-dir {out_dir} overlaps the result folder {batch} (nothing is written there)")
    if overwrite:
        return
    existing = [name for name in EXPECTED_CASES for file in (ROW_FILE, PADS_FILE) if (out_dir / name / file).exists()]
    if existing:
        raise InputError(f"outputs exist for {sorted(set(existing))} (use --overwrite)")


def _write_case(out_dir: Path, name: str, row: dict, t_s: np.ndarray, pad_N: np.ndarray) -> dict[str, str]:
    folder = out_dir / name
    folder.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(folder / PADS_FILE, t=t_s, N=pad_N)
    text = json.dumps(rows_v6._plain(row), indent=1, ensure_ascii=False)
    (folder / ROW_FILE).write_text(text, encoding="utf-8")
    return {ROW_FILE: file_sha256(folder / ROW_FILE), PADS_FILE: file_sha256(folder / PADS_FILE)}


def pair_summary(rows: dict[str, dict]) -> list[dict[str, Any]]:
    """Rules 3.6 report triggers per source case: CAP latch on the K-2 row, READY delay > +10 s against off."""
    pairs = []
    for name, row in sorted(rows.items()):
        if not name.endswith("_tcl"):
            continue
        off = rows.get(name.removesuffix("_tcl") + "_off")
        ready_tcl, ready_off = row.get("t_ready_s"), (off or {}).get("t_ready_s")
        delay = None if ready_tcl is None or ready_off is None else ready_tcl - ready_off
        pairs.append({"tcl": name, "off": None if off is None else off["case_id"], "cap_events": row["cap_events"],
                      "ready_delay_s": delay,
                      "report_to_user": bool(row["cap_events"]) or (delay is not None and delay > READY_DELAY_REPORT_S)})
    return pairs


def cmd_rows(args: argparse.Namespace) -> tuple[int, dict]:
    batch, out_dir = Path(args.batch), Path(args.out_dir)
    _check_out_dir(batch, out_dir, args.overwrite)
    batch_cases = _batch_cases(batch)
    rows, written, problems = {}, {}, []
    for name in EXPECTED_CASES:
        folder = batch / name
        try:
            inputs = _case_inputs(folder)
        except FileNotFoundError as exc:
            problems.append(str(exc))
            continue
        if (batch_cases.get(name) or {}).get("rc") != 0:
            problems.append(f"{name}: batch rc {(batch_cases.get(name) or {}).get('rc')!r}")
        row, t_s, pad_N = scm_row(ScmCase(folder))
        row = {**row, **_row_meta(name, inputs, batch_cases.get(name))}
        rows[name] = row
        written[name] = _write_case(out_dir, name, row, t_s, pad_N)
    status = EXIT_INCOMPLETE if problems or len(rows) != len(EXPECTED_CASES) else EXIT_DONE
    return status, {"record_only": True, "note": RECORD_NOTE, "batch": str(batch), "out_dir": str(out_dir),
                    "tool_sha256": file_sha256(Path(__file__)), "written": written, "problems": problems,
                    "pairs": pair_summary(rows),
                    "v7_record": {name: row["v7_record"] for name, row in rows.items()}}


# ------------------------------------------------------------------------------------------ fill-manifest
def _replace_placeholder(value: Any, replacement: str) -> Any:
    if isinstance(value, dict):
        return {key: _replace_placeholder(item, replacement) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_placeholder(item, replacement) for item in value]
    if isinstance(value, str):
        return value.replace(PLACEHOLDER, replacement)
    return value


def cmd_fill_manifest(args: argparse.Namespace) -> tuple[int, dict]:
    source, out = Path(args.manifest), Path(args.out)
    if out.resolve() == source.resolve():
        raise InputError("--out must be a new file (the manifest stays as it is)")
    if out.exists() and not args.overwrite:
        raise InputError(f"{out} exists (use --overwrite)")
    text = source.read_text(encoding="utf-8")
    count = text.count(PLACEHOLDER)
    filled = _replace_placeholder(json.loads(text), str(Path(args.batch_v7)))
    # The name without braces: the record of the fill must not look like an unfilled slot itself.
    filled["_v7_filled"] = {"note": RECORD_NOTE, "placeholder_name": PLACEHOLDER.strip("{}"),
                            "replaced_by": str(Path(args.batch_v7)),
                            "replaced": count, "source": str(source), "source_sha256": file_sha256(source),
                            "tool": TOOL, "tool_sha256": file_sha256(Path(__file__)), "written": _now()}
    out_text = json.dumps(filled, indent=1, ensure_ascii=False)
    left = sorted(set(PLACEHOLDER_PATTERN.findall(out_text)))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(out_text, encoding="utf-8")
    status = EXIT_INPUT if left else EXIT_DONE
    return status, {"out": str(out), "out_sha256": file_sha256(out), "replaced": count,
                    "placeholders_left": left, "source_sha256": file_sha256(source)}


# ------------------------------------------------------------------------------------------ CLI
COMMANDS = {"rows": cmd_rows, "fill-manifest": cmd_fill_manifest}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-report", type=Path, default=None, help="summary file (JSON or md)")
    parser.add_argument("--format", choices=("json", "md"), default="json")
    sub = parser.add_subparsers(dest="command", required=True)
    rows = sub.add_parser("rows", help="write k2_row.json + k2_pads.npz per V-7 case")
    rows.add_argument("--batch", required=True, type=Path, help="s9_batch k2_v7 folder (read only)")
    rows.add_argument("--out-dir", required=True, type=Path, help="output folder (outside the batch)")
    rows.add_argument("--overwrite", action="store_true")
    fill = sub.add_parser("fill-manifest", help=f"copy the manifest with {PLACEHOLDER} filled")
    fill.add_argument("--manifest", required=True, type=Path)
    fill.add_argument("--batch-v7", required=True, type=Path, help="folder of the rows command")
    fill.add_argument("--out", required=True, type=Path)
    fill.add_argument("--overwrite", action="store_true")
    return parser


def _markdown(command: str, status: int, result: dict) -> str:
    lines = [f"# {TOOL} {command}", "", f"exit {status}", "", f"- note: {RECORD_NOTE}"]
    for key in ("problems", "pairs", "placeholders_left", "out", "out_sha256"):
        if key in result:
            lines.append(f"- {key}: {json.dumps(result[key], default=float)}")
    return "\n".join(lines) + "\n"


def run(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        status, result = COMMANDS[args.command](args)
    except (InputError, FileNotFoundError, json.JSONDecodeError) as exc:
        status, result = EXIT_INPUT, {"problems": [str(exc)]}
    except Exception as exc:  # contract: internal error = exit 3 with the traceback in the record
        status, result = EXIT_INTERNAL, {"error": repr(exc), "traceback": traceback.format_exc()[-3000:]}
    result = {"command": args.command, "exit": status, **result}
    text = _markdown(args.command, status, result) if args.format == "md" else json.dumps(
        rows_v6._plain(result), indent=1, ensure_ascii=False)
    if args.out_report is not None:
        args.out_report.write_text(text, encoding="utf-8")
    print(json.dumps({"command": args.command, "exit": status, "problems": len(result.get("problems", []))}))
    return status


if __name__ == "__main__":
    sys.exit(run())
