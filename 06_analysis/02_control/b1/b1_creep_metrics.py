"""B1 creep basis (``V5-B1-CREEP``) path 1: metrics M-1 .. M-12, harness constants and grades.

Rules: ``b1_creep_basis_rules_seal_candidate_draft.md`` (seal candidate, :data:`RULES_SHA256`;
after the seal S-0 only the file name and the SHA-256 constant change). Path 2 is written
separately by control-expert from the rule text only (rules 9); this file is path 1.

Subcommands::

    constants --harness <b1_H.jsonl> --out <b1_harness_constants.json>
        rules 7.3: kappa_z and C_type per pad type (per-leg windows t_e,i, C-2), the kappa
        ratio per type (record, > 1.5 = "kappa nonlinear"), delta_allow, from the 20 H-P runs.
    judge --chrono-batch <batch folder> --harness <b1_H.jsonl> --identity <identity.json>
          --out <b1_metrics_path1.json> [--constants <b1_harness_constants.json>]
          [--p7-ref <s2d_SC.jsonl>]
        rules 3.1 row states, 3.2 bundle state, 3.3 grades D-a .. D-h, 5 metrics M-1 .. M-12,
        7.2 m_L and the predictor candidates P-A / P-B / P-D / P-C, 4.4 threshold forms T-1 ..
        T-14, 4.5 integer periods, 6 grid record (full 10 Hz or the fallback windows).

Inputs (``b1-run-record/1``, the same arrays for both engines, periods aligned by
``n = round(t / 0.1)``):

* Harness: ``b1_harness.py`` lines and ``npz/<run id>.npz`` (``stroke_read_m``, ``sink_m``,
  ``load_read_N``, ``att_filt_rad``, ``c_hat_m``, ``c_target_m``). Grid factor ``f = 1``.
* Chrono row folder ``<batch>/<case>/``: ``result.json``, ``record/record.npz`` (``t``,
  ``meas.stroke``: the reading stroke), ``step_series.npz`` (``t_s``,
  ``pad_sinkage_geometric_m``, ``scm_pad_normal_N``, ``scm_crawler_normal_N``; 1 ms, looked up
  by ``searchsorted(t, n 0.1 - 1e-9)``) and :data:`CHRONO_B1_RECORD` (the controller arrays
  above plus the grid record R-G1 .. R-G4, key names :data:`CHRONO_GRID_KEYS`; set by the
  Chrono runner, cad-expert). A missing field gives NA for what needs it, never INVALID.
* Identity record (``--identity``): per row ``{"ok": bool, "reasons": [...]}`` of rules I-1 ..
  I-17 from prelaunch / postrun / audit, ``rc`` per row, and ``runner_log`` ``{errors_total,
  errors_left}`` (E-5). The tool adds the I-3 / I-4 / I-7 / I-11 checks it can read itself.

Units SI (m, N, s, rad). Exit: 0 bundle COMPLETE / PARTIAL with grades, 1 bundle UNDETERMINED
or blocked (E-5), 2 input error, 3 internal error (E-6 self check). The last stdout line is a
one-line JSON summary. numpy + json + stdlib only; no project import.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# ===================================================================================== constants
RULES_FILE = "b1_creep_basis_rules_seal_candidate_draft.md"
RULES_SHA256 = "fa142d525c9c8d318212c245b552cea47b0394ed97680900653bcda737ab5cf9"
"""Seal candidate (not sealed). After S-0: the sealed file name and its SHA-256."""
SCHEMA_METRICS = "b1-creep-metrics/1"
SCHEMA_CONSTANTS = "b1-harness-constants/1"
RECORD_SCHEMA = "b1-run-record/1"
PATH_NAME = "path 1"

PERIOD_S = 0.1
SERIES_LOOKUP_TOL_S = 1e-9
"""Rules 4.5: 1 ms lookup ``searchsorted(t, tau - 1e-9)``, ``tau = n 0.1``."""
EPS_TH_M = 1e-9
"""Rules 4.4 threshold tolerance (not the two-path value tolerance of rules 9)."""
LEGS = ("FL", "FR", "RL", "RR")
FRONT, REAR = "front330", "rear250"
PAD_TYPE = (FRONT, FRONT, REAR, REAR)
S_GUARD_M = 0.6828
C_STAR_M = 0.05
"""``thresholds.clearance_target_m`` (rules 0.1)."""
N_A = 0.2
"""P-D assumed exponent (rules 7.2, J2 set n)."""
KAPPA_W_FLOOR_N = 1.0
"""Rules 7.3: ``kappa`` divides by ``max(W_hat, 1 N)``."""
KAPPA_RATIO_FLAG = 1.5

ZA_M = 0.003       # T-1
OS_M = 0.005       # T-2
HC_M = 0.003       # T-3
PRED_M = 0.010     # T-4
NEED_M = 0.020     # T-5
WG_M = 0.005       # T-6
M12_M = 0.005      # T-13
T14_M = 5e-4       # T-14
GRID_N_BAND = (0.95, 1.05)
GRID_N_TOL = 1e-9
GRID_LAW_MAX = 0.005
GRID_LAW_TOL = 1e-12
GRID_COST_LIMIT = 1.05    # T-10
T8_SAMPLES = 100
T9_FRACTION = 0.01
T9_TOL_N = 1e-6
F_PHASE_BAND = {REAR: (1.0 - 0.013, 1.0 + 0.042), FRONT: (1.0 - 0.028, 1.0 + 0.050)}
"""Rules 0.4 table, grid 0.01 m: (f_min, f_max) per pad type (C-3, D-c fallback)."""
Z_SOIL_CANDIDATES = {"Z0": 0.0, "Z1": 0.002}
"""TR-8 (record only); Z2 = 0.1 z_b*(t_R) per row; Zf = field test (absent)."""

BATCH_NAME = "V5-B1-CREEP"
CTRL_TAG_VB = "final_C4G2_P3_LAS_K1"
CTRL_TAG_V0 = "final_C4G2_LAS_K1"
HULL_DLL_SHA = "cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15"
P7_REF_SHA256 = "70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa"
P7_CANDIDATE = "P0"
SOIL = "J2"
PAD_VARIANT = "dwg_rear250"


@dataclass(frozen=True)
class ChronoRow:
    """One Chrono row of rules 2.1."""

    case: str
    level: str
    budget_leg: str
    duration_s: float
    role: str


CHRONO_ROWS = {
    "C1": ChronoRow("B1_J2_B_bottom_Fs4_VB_fdown", "bottom", "FL", 160.0, "core"),
    "C2": ChronoRow("B1_J2_B_middle_Fs4_VB_fdown", "middle", "FL", 160.0, "core"),
    "C3": ChronoRow("B1_J2_B_top_Fs4_VB_fdown", "top", "FL", 160.0, "aux"),
    "C4": ChronoRow("B1_J2_B_bottom_Fs4_VB_diag", "bottom", "FR", 160.0, "core"),
    "C5": ChronoRow("B1_J2_B_top_Fs4_VB_fup", "top", "RL", 160.0, "core"),
    "C6": ChronoRow("B1_J2_B_bottom_Fs4_m1p1_VB_fdown", "bottom", "FL", 180.0, "sensitivity"),
}
CORE_ROWS = ("C1", "C2", "C4", "C5")
R_ROWS = ("C1", "C2", "C3", "C4", "C5")
"""The x1.0 set before validity (rules 3.3: core four + C3 when VALID)."""
NEED_ROWS = ("C1", "C2", "C4")
C6_MASS_SCALE = 1.1
HARNESS_PAIR_ROW = {"C1": "C1", "C2": "C2", "C3": "C3", "C4": "C4", "C5": "C5", "C6": "C6"}

CHRONO_B1_RECORD = "b1_record.npz"
CHRONO_RECORD_KEYS = ("n", "load_read_N", "att_filt_rad", "c_hat_m", "c_target_m")
CHRONO_GRID_KEYS = {
    "n": "grid_n", "n_inside": "grid_n_inside", "n_contact": "grid_n_contact",
    "hull_area": "grid_hull_area_m2", "hull_perimeter": "grid_hull_perimeter_m",
    "z_geo": "grid_sinkage_geometric_m", "sigma_sum": "grid_sigma_sum_area_N",
}
"""R-G1 key names in :data:`CHRONO_B1_RECORD` (proposal; cad-expert fixes them before the sha
of this tool is fixed)."""
CHRONO_PAD_XY_KEYS = ("pad_xy_n", "pad_xy_m", "pad_yaw_rad")
CHRONO_SHADOW_KEY = "loc_shadow"
"""Optional M-12 entries of a Chrono row (same form as the harness shadow) in result.json."""

EV_LOC = "crawler_liftoff_confirmed"
EV_REVOKE = "INFO_LOC_REVOKED"
EV_E3C10 = "INFO_LOC_CLEARANCE_MARGIN"
EV_R4C30 = "INFO_LOC_FLAT_SOIL_MARGIN"
EV_R4_SKIP = "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order"
EV_SGS = "FAULT_LIFT_STROKE_LIMIT:soil"
EV_WARN_LIFT = "WARN_LIFT_STROKE_LIMITED"
EV_STROKE_END = "FAULT_STROKE_END"
EV_DSB_HOLD = "INFO_DIFF_SINK_HOLD"
EV_DSB_RELEASE = "INFO_DIFF_SINK_RELEASE"
EV_LIFT_PAUSED = "INFO_LIFT_PAUSED"
EV_WINDOW_RESTART = "INFO_LOC_WINDOW_RESTART"
START_REFUSAL_PREFIX = "REJ_"
FAULT_PHASES = ("fault", "fault_reground", "C2Phase.FAULT", "C2Phase.FAULT_REGROUND")

EXIT_OK, EXIT_FOUND, EXIT_INPUT, EXIT_INTERNAL = 0, 1, 2, 3
NA = "NA"


class InputError(Exception):
    """An input file is missing, unreadable or not what the rules name."""


# ===================================================================================== records
@dataclass
class GridRecord:
    """R-G1 per recorded period: arrays (K,) / (K, 4); ``grid_m`` is the pad grid Delta."""

    n: np.ndarray
    n_contact: np.ndarray
    hull_area: np.ndarray
    hull_perimeter: np.ndarray
    z_geo: np.ndarray
    sigma_sum: np.ndarray
    grid_m: float


@dataclass
class RunRecord:
    """``b1-run-record/1`` of one run (module docstring); optional arrays are None."""

    run_id: str
    source: str
    level: str
    n: np.ndarray
    stroke: np.ndarray
    sink: np.ndarray | None
    events: list[tuple[float, str]]
    t_ready_s: float | None
    load: np.ndarray | None = None
    att: np.ndarray | None = None
    c_hat: np.ndarray | None = None
    c_target: np.ndarray | None = None
    c_target_final_m: float | None = None
    t_departure_s: float | None = None
    t_creep_s: float | None = None
    final_phase: str | None = None
    grid: GridRecord | None = None
    pad_xy: dict | None = None
    loc_shadow: dict | None = None
    crawler_clear: np.ndarray | None = None
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Geometry:
    """YAML / soil-set quantities (read from the files, rules 9)."""

    pad_xy_m: np.ndarray
    static_loads_N: dict[str, np.ndarray]
    pad_area_m2: np.ndarray
    pad_b_poly_m: np.ndarray
    kc: float
    kphi: float
    n_soil: float
    superstructure_mass_kg: dict[str, float]


# ===================================================================================== helpers
def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def period_index(t_s: float) -> int:
    """Rules 4.5: ``n = round(t / 0.1)``."""
    return int(round(float(t_s) / PERIOD_S))


def _finite(value) -> bool:
    return value is not None and isinstance(value, int | float) and math.isfinite(value)


def _num(value) -> float | None:
    """JSON-safe float (None for NaN / inf / None)."""
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _legs(values) -> list[float | None] | None:
    return None if values is None else [_num(v) for v in values]


def event_base(name: str) -> str:
    return name.split(":")[0]


def is_sgs_event(name: str) -> bool:
    return name == EV_SGS or (event_base(name) == "FAULT_LIFT_STROKE_LIMIT"
                              and "soil" in name.split(":")[1:])


def margin_event_mm(name: str) -> int | None:
    """Target [mm] of an E3c10 / R4c30 event (``<NAME>:<integer mm>``), else None."""
    match = re.fullmatch(rf"({EV_E3C10}|{EV_R4C30}):(-?\d+)", name)
    return None if match is None else int(match.group(2))


class Rows:
    """Lookup of a record's period index -> row (rules 4.5: "same sample" = same ``n``)."""

    def __init__(self, n: np.ndarray) -> None:
        self.index = {int(value): i for i, value in enumerate(np.asarray(n, dtype=np.int64))}

    def at(self, array: np.ndarray | None, n: int | None):
        if array is None or n is None or int(n) not in self.index:
            return None
        return array[self.index[int(n)]]


def series_at(t_s: np.ndarray, values: np.ndarray, n: int) -> np.ndarray | None:
    """1 ms series value at ``tau = n 0.1`` (rules 4.5)."""
    index = int(np.searchsorted(t_s, n * PERIOD_S - SERIES_LOOKUP_TOL_S))
    return None if index >= len(t_s) else np.asarray(values[index], dtype=float)


# ===================================================================================== inputs
def read_geometry(yaml_path: Path, soil_sets_path: Path) -> Geometry:
    """Pad xy, static leg loads per level, pad B area / b_poly (YAML) and the J2 set.

    Raises:
        InputError: A block is missing or incomplete.
    """
    lines = yaml_path.read_text(encoding="utf-8").splitlines()
    sets = json.loads(soil_sets_path.read_text(encoding="utf-8"))["sets"]
    chrono = sets[SOIL]["chrono"]
    area, b_poly = _yaml_pad_shapes(lines)
    loads, masses = _yaml_static_loads(lines)
    return Geometry(pad_xy_m=_yaml_pad_xy(lines), static_loads_N=loads, pad_area_m2=area,
                    pad_b_poly_m=b_poly, kc=float(chrono["Kc"]), kphi=float(chrono["Kphi"]),
                    n_soil=float(chrono["n"]), superstructure_mass_kg=masses)


def _block_start(lines: list[str], header: str, start: int = 0) -> int:
    for index in range(start, len(lines)):
        if lines[index].rstrip() == header:
            return index
    raise InputError(f"YAML block {header.strip()!r} not found")


def _yaml_pad_xy(lines: list[str]) -> np.ndarray:
    """``legs.<leg>.pad_bottom_center_retracted_m`` (x, y)."""
    start = _block_start(lines, "legs:")
    out: dict[str, tuple[float, float]] = {}
    leg = None
    for text in lines[start + 1:]:
        if text and not text.startswith(" "):
            break
        match = re.match(r"^  (FL|FR|RL|RR):\s*$", text)
        if match:
            leg = match.group(1)
            continue
        match = re.match(r"^    pad_bottom_center_retracted_m:\s*\[([^\]]+)\]", text)
        if match and leg:
            x_m, y_m = (float(v) for v in match.group(1).split(",")[:2])
            out[leg] = (x_m, y_m)
    if set(out) != set(LEGS):
        raise InputError(f"legs.*.pad_bottom_center_retracted_m incomplete: {sorted(out)}")
    return np.array([out[leg] for leg in LEGS], dtype=float)


def _yaml_static_loads(lines: list[str]) -> tuple[dict[str, np.ndarray], dict[str, float]]:
    """``superstructure.auger_levels.<level>.static_leg_loads_N`` and ``mass_kg``."""
    start = _block_start(lines, "  auger_levels:", _block_start(lines, "superstructure:"))
    loads: dict[str, dict[str, float]] = {}
    masses: dict[str, float] = {}
    level, in_loads = None, False
    for text in lines[start + 1:]:
        if text and not text.startswith("    "):
            break
        match = re.match(r"^    (top|middle|bottom):\s*$", text)
        if match:
            level, in_loads = match.group(1), False
            continue
        match = re.match(r"^      mass_kg:\s*([0-9.eE+-]+)", text)
        if match and level:
            masses[level] = float(match.group(1))
        if re.match(r"^      static_leg_loads_N:\s*$", text):
            in_loads = True
            continue
        match = re.match(r"^        (FL|FR|RL|RR):\s*([0-9.eE+-]+)", text)
        if match and level and in_loads:
            loads.setdefault(level, {})[match.group(1)] = float(match.group(2))
        elif re.match(r"^      \S", text):
            in_loads = False
    if set(loads) != {"top", "middle", "bottom"} or any(set(v) != set(LEGS)
                                                         for v in loads.values()):
        raise InputError("superstructure.auger_levels.*.static_leg_loads_N incomplete")
    return {k: np.array([v[leg] for leg in LEGS], dtype=float) for k, v in loads.items()}, masses


def _yaml_pad_shapes(lines: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """``pad_shapes.types.dwg_rear250.legs.<leg>`` area and Bekker b (``gridconv_judge``)."""
    start = _block_start(lines, f"    {PAD_VARIANT}:", _block_start(lines, "pad_shapes:"))
    out: dict[str, tuple[float, float]] = {}
    leg, area = None, None
    for text in lines[start + 1:]:
        if re.match(r"^    \S", text) or (text and not text.startswith(" ")):
            break
        match = re.match(r"^        (FL|FR|RL|RR):\s*$", text)
        if match:
            leg, area = match.group(1), None
            continue
        match = re.match(r"^\s+bottom_area_m2:\s*([0-9.eE+-]+)", text)
        if match and leg:
            area = float(match.group(1))
        match = re.match(r"^\s+bekker_b_m:\s*([0-9.eE+-]+)", text)
        if match and leg and area is not None:
            out[leg] = (area, float(match.group(1)))
    if set(out) != set(LEGS):
        raise InputError(f"pad_shapes.{PAD_VARIANT} legs incomplete: {sorted(out)}")
    return (np.array([out[leg][0] for leg in LEGS]), np.array([out[leg][1] for leg in LEGS]))


# ----------------------------------------------------------------------------------- harness
@dataclass
class HarnessRun:
    """One accepted harness line (E-1) and its run record."""

    line: dict
    record: RunRecord


def _expected_tag(setting: str) -> str | None:
    return {"VB": CTRL_TAG_VB, "V0": CTRL_TAG_V0}.get(setting)


def load_harness(jsonl: Path) -> tuple[dict[str, HarnessRun], list[dict]]:
    """Accepted runs by run id and the refused lines (E-1: error, no meta, other tag, npz).

    The last line of a run id wins (a rerun after an error appends).
    """
    if not jsonl.is_file():
        raise InputError(f"harness jsonl {jsonl} absent")
    lines: dict[str, dict] = {}
    for text in jsonl.read_text(encoding="utf-8").splitlines():
        if text.strip():
            line = json.loads(text)
            lines[line["run_id"]] = line
    runs, refused = {}, []
    for run_id, line in lines.items():
        reason = _harness_refusal(line, jsonl.parent)
        if reason:
            refused.append({"run_id": run_id, "reason": reason})
            continue
        runs[run_id] = HarnessRun(line, _harness_record(line, jsonl.parent))
    return runs, refused


def _harness_refusal(line: dict, folder: Path) -> str | None:
    if line.get("error"):
        return f"error line: {str(line['error'])[:120]}"
    if not isinstance(line.get("controller"), dict):
        return "E-1: no controller meta"
    expected = _expected_tag(line.get("setting", ""))
    if line.get("controller_tag") != expected:
        return f"E-1: tag {line.get('controller_tag')!r} != {expected!r}"
    path = folder / str(line.get("npz"))
    if not path.is_file():
        return f"run record {line.get('npz')} absent"
    if sha256_file(path) != line.get("npz_sha256"):
        return "run record sha256 differs from the line"
    return None


def _harness_record(line: dict, folder: Path) -> RunRecord:
    with np.load(folder / line["npz"], allow_pickle=False) as data:
        arrays = {key: np.asarray(data[key]) for key in data.files}
    events = [(float(t), str(name)) for t, name in line.get("events") or []]
    controller = line.get("controller") or {}
    return RunRecord(
        run_id=line["run_id"], source="harness", level=line["level"],
        n=arrays["n"].astype(np.int64), stroke=arrays["stroke_read_m"], sink=arrays["sink_m"],
        events=events, t_ready_s=line.get("t_first_ready_s"), load=arrays.get("load_read_N"),
        att=arrays.get("att_filt_rad"), c_hat=arrays.get("c_hat_m"),
        c_target=arrays.get("c_target_m"),
        c_target_final_m=controller.get("clearance_target_final_m"),
        t_departure_s=line.get("t_departure_s"), final_phase=line.get("final_phase"),
        loc_shadow=line.get("loc_shadow"), crawler_clear=arrays.get("crawler_clear_true_m"),
        extra={"harness_class": line.get("harness_class"),
               "order_gate_decisions": _order_gate_count(line.get("controller_meta")),
               "commands_sha256": line.get("commands_sha256"), "group": line.get("group"),
               "margin_zero": line.get("margin_zero"), "mass_scale": line.get("mass_scale")})


def _order_gate_count(meta: dict | None) -> int | None:
    gate = ((meta or {}).get("slope_clearance_margin") or {}).get("order_gate") or {}
    decisions = gate.get("decisions")
    return None if decisions is None else len(decisions)


def harness_run_id(group: str, row_id: str, setting: str, eps: float) -> str:
    return f"{group}|{row_id}|{setting}|e{eps:g}"


# ----------------------------------------------------------------------------------- chrono
def _load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        return {key: np.asarray(data[key]) for key in data.files}


def load_chrono_row(batch: Path, row_id: str) -> tuple[RunRecord | None, dict]:
    """Run record and the raw facts of a Chrono row (None record when a V-1 file is absent)."""
    row = CHRONO_ROWS[row_id]
    folder = batch / row.case
    files = {"result": folder / "result.json", "record": folder / "record" / "record.npz",
             "step_series": folder / "step_series.npz"}
    facts: dict = {"case": row.case, "files_present": {k: p.is_file() for k, p in files.items()}}
    if not all(facts["files_present"].values()):
        return None, facts
    result = json.loads(files["result"].read_text(encoding="utf-8"))
    record = _load_npz(files["record"])
    series = _load_npz(files["step_series"])
    b1_path = folder / CHRONO_B1_RECORD
    b1 = _load_npz(b1_path) if b1_path.is_file() else {}
    facts.update(result=result, series=series, b1_record_present=bool(b1),
                 sha256={k: sha256_file(p) for k, p in files.items()})
    return _chrono_record(row_id, result, record, series, b1), facts


def _chrono_record(row_id: str, result: dict, record: dict, series: dict,
                   b1: dict) -> RunRecord:
    n = np.rint(np.asarray(record["t"], dtype=float) / PERIOD_S).astype(np.int64)
    t_1ms = np.asarray(series["t_s"], dtype=float)
    z_1ms = np.asarray(series["pad_sinkage_geometric_m"], dtype=float)
    sink = np.full((len(n), 4), np.nan)
    for index, value in enumerate(n):
        z = series_at(t_1ms, z_1ms, int(value))
        if z is not None:
            sink[index] = z
    p3b = result.get("p3b") or {}
    margin_meta = (result.get("controller_meta") or {}).get("slope_clearance_margin") or {}
    rec = RunRecord(
        run_id=row_id, source="chrono", level=CHRONO_ROWS[row_id].level, n=n,
        stroke=np.asarray(record["meas.stroke"], dtype=float), sink=sink,
        events=[(float(e["t_s"]), str(e["name"])) for e in result.get("events") or []],
        t_ready_s=(p3b.get("P3-5_clearance_stroke") or {}).get("t_first_ready_s"),
        c_target_final_m=margin_meta.get("clearance_target_m"),
        t_departure_s=(p3b.get("P3-2_loc") or {}).get("t_departure_s"),
        t_creep_s=(p3b.get("creep_stop") or {}).get("t_final_s"),
        final_phase=str(result.get("final_phase")) if result.get("final_phase") else None,
        loc_shadow=result.get(CHRONO_SHADOW_KEY),
        extra={"order_gate_decisions": len((margin_meta.get("order_gate") or {})
                                            .get("decisions") or [])})
    _attach_chrono_b1(rec, b1, result)
    return rec


def _aligned(rec_n: np.ndarray, source_n: np.ndarray, values: np.ndarray) -> np.ndarray:
    """``values`` (by ``source_n``) on the periods ``rec_n`` (NaN where absent)."""
    shape = (len(rec_n),) + values.shape[1:]
    out = np.full(shape, np.nan)
    lookup = {int(v): i for i, v in enumerate(source_n)}
    for index, value in enumerate(rec_n):
        if int(value) in lookup:
            out[index] = values[lookup[int(value)]]
    return out


def _attach_chrono_b1(rec: RunRecord, b1: dict, result: dict) -> None:
    if all(key in b1 for key in CHRONO_RECORD_KEYS):
        source_n = b1["n"].astype(np.int64)
        rec.load = _aligned(rec.n, source_n, b1["load_read_N"].astype(float))
        rec.att = _aligned(rec.n, source_n, b1["att_filt_rad"].astype(float))
        rec.c_hat = _aligned(rec.n, source_n, b1["c_hat_m"].astype(float))
        rec.c_target = _aligned(rec.n, source_n, b1["c_target_m"].astype(float))
    if all(key in b1 for key in CHRONO_GRID_KEYS.values()):
        grid_m = ((result.get("meta") or {}).get("scm") or {}).get("grid_m")
        keys = CHRONO_GRID_KEYS
        rec.grid = GridRecord(
            n=b1[keys["n"]].astype(np.int64), n_contact=b1[keys["n_contact"]].astype(float),
            hull_area=b1[keys["hull_area"]].astype(float),
            hull_perimeter=b1[keys["hull_perimeter"]].astype(float),
            z_geo=b1[keys["z_geo"]].astype(float), sigma_sum=b1[keys["sigma_sum"]].astype(float),
            grid_m=float(grid_m) if grid_m is not None else math.nan)
    if all(key in b1 for key in CHRONO_PAD_XY_KEYS):
        rec.pad_xy = {"n": b1["pad_xy_n"].astype(np.int64), "xy": b1["pad_xy_m"].astype(float)}


# ===================================================================================== timing
@dataclass
class Timing:
    """Integer periods of rules 4.5 / 5 (None when absent)."""

    n_L1: int | None
    n_L: int | None
    revokes: int
    n_R: int | None
    n_max: int
    n_max_leg: list[int]
    n_e: int
    n_e_leg: list[int]
    n_end: int
    n_dep: int | None
    n_creep: int | None
    n_sgs: int | None
    n_warn_lift: int | None
    s_max: np.ndarray
    b_star: int


def run_timing(rec: RunRecord) -> Timing:
    """Rules 4.5 / M-1 / M-2 / M-4 periods of a run."""
    locs = [period_index(t) for t, name in rec.events if name == EV_LOC]
    revokes = sum(1 for _, name in rec.events if event_base(name) == EV_REVOKE)
    sgs = [period_index(t) for t, name in rec.events if is_sgs_event(name)]
    warn = [period_index(t) for t, name in rec.events if event_base(name) == EV_WARN_LIFT]
    s_max = np.nanmax(rec.stroke, axis=0)
    overall = float(np.max(s_max))
    b_star = next(i for i in range(4) if s_max[i] >= overall - EPS_TH_M)
    row_max = np.nanmax(rec.stroke, axis=1)
    n_max = int(rec.n[int(np.flatnonzero(row_max >= overall - EPS_TH_M)[0])])
    n_max_leg = [int(rec.n[int(np.flatnonzero(rec.stroke[:, i] >= s_max[i] - EPS_TH_M)[0])])
                 for i in range(4)]
    n_R = None if not _finite(rec.t_ready_s) else period_index(rec.t_ready_s)
    return Timing(
        n_L1=locs[0] if locs else None, n_L=locs[-1] if locs else None, revokes=revokes,
        n_R=n_R, n_max=n_max, n_max_leg=n_max_leg,
        n_e=n_max if n_R is None else max(n_max, n_R),
        n_e_leg=[v if n_R is None else max(v, n_R) for v in n_max_leg],
        n_end=int(rec.n[-1]),
        n_dep=None if not _finite(rec.t_departure_s) else period_index(rec.t_departure_s),
        n_creep=None if not _finite(rec.t_creep_s) else period_index(rec.t_creep_s),
        n_sgs=sgs[0] if sgs else None, n_warn_lift=warn[0] if warn else None,
        s_max=s_max, b_star=b_star)


def margin_at_loc(rec: RunRecord, n_L: int | None) -> dict:
    """Rules 7.2: ``m_L`` from the last E3c10 / R4c30 event up to the last LOC period."""
    if n_L is None:
        return {"m_L_m": None, "source": None, "c_star_run_m": None}
    found = [(period_index(t), name) for t, name in rec.events
             if margin_event_mm(name) is not None and period_index(t) <= n_L]
    if not found:
        return {"m_L_m": 0.0, "source": None, "c_star_run_m": C_STAR_M}
    _, name = found[-1]
    c_star_run = margin_event_mm(name) / 1e3
    return {"m_L_m": c_star_run - C_STAR_M, "source": event_base(name), "event": name,
            "c_star_run_m": c_star_run}


def t14_check(rec: RunRecord, rows: Rows, n_L: int | None, c_star_run_m: float | None) -> dict:
    """Rules T-14: event target against the controller state ``clearance_target_m``."""
    state = rows.at(rec.c_target, n_L)
    source = "period record at n_L"
    if state is None or not _finite(float(state)):
        state, source = rec.c_target_final_m, "final controller meta"
    if c_star_run_m is None or state is None:
        return {"checked": False, "ok": True, "state_m": _num(state), "source": source}
    difference = abs(c_star_run_m - float(state))
    return {"checked": True, "ok": difference - T14_M <= 0.0, "state_m": float(state),
            "difference_m": difference, "source": source}


# ===================================================================================== metrics
def _z(rows: Rows, rec: RunRecord, n: int | None) -> np.ndarray | None:
    value = rows.at(rec.sink, n)
    return None if value is None else np.asarray(value, dtype=float)


def _diff(a, b) -> list[float | None] | None:
    if a is None or b is None:
        return None
    return _legs(np.asarray(a, dtype=float) - np.asarray(b, dtype=float))


def sink_metrics(rec: RunRecord, rows: Rows, tm: Timing) -> dict:
    """M-4 (C-1): window ``t_L -> t_e`` and the per-leg windows ``t_L -> t_e,i``."""
    z_L, z_e, z_max = _z(rows, rec, tm.n_L), _z(rows, rec, tm.n_e), _z(rows, rec, tm.n_max)
    z_R, z_end = _z(rows, rec, tm.n_R), _z(rows, rec, tm.n_end)
    per_leg = []
    for i in range(4):
        z_ei = _z(rows, rec, tm.n_e_leg[i])
        per_leg.append(None if z_ei is None or z_L is None else _num(z_ei[i] - z_L[i]))
    return {"z_L": _legs(z_L), "z_R": _legs(z_R), "z_max": _legs(z_max), "z_e": _legs(z_e),
            "z_end": _legs(z_end), "dz_post": _diff(z_e, z_L), "dz_post_leg_window": per_leg,
            "dz_L_to_max": _diff(z_max, z_L), "dz_max_to_R": _diff(z_R, z_max),
            "dz_L_to_R": _diff(z_R, z_L), "dz_R_to_end": _diff(z_end, z_R),
            "max_rate_after_L_m_s": _max_sink_rate(rec, rows, tm.n_L),
            "secant_L_to_R_m_per_N": _secant(rec, rows, tm)}


def _max_sink_rate(rec: RunRecord, rows: Rows, n_L: int | None) -> list[float | None] | None:
    """Largest 1.0 s backward difference of the sinkage after the last LOC [m/s]."""
    if n_L is None or rec.sink is None:
        return None
    window = int(round(1.0 / PERIOD_S))
    best = [None] * 4
    for n in rec.n:
        if int(n) <= n_L:
            continue
        now, before = _z(rows, rec, int(n)), _z(rows, rec, int(n) - window)
        if now is None or before is None:
            continue
        for i in range(4):
            rate = (now[i] - before[i]) / 1.0
            if math.isfinite(rate) and (best[i] is None or rate > best[i]):
                best[i] = rate
    return best


def _secant(rec: RunRecord, rows: Rows, tm: Timing) -> list[float | None] | None:
    z_L, z_R = _z(rows, rec, tm.n_L), _z(rows, rec, tm.n_R)
    f_L, f_R = rows.at(rec.load, tm.n_L), rows.at(rec.load, tm.n_R)
    if any(v is None for v in (z_L, z_R, f_L, f_R)):
        return None
    out = []
    for i in range(4):
        load_change = float(f_R[i] - f_L[i])
        out.append(None if abs(load_change) <= 0.0 else _num((z_R[i] - z_L[i]) / load_change))
    return out


def predictor_inputs(rec: RunRecord, rows: Rows, tm: Timing, geo: Geometry) -> dict:
    """Rules 7.1 / 7.2 inputs at ``n_L``: s, ds_geo, c_hat, m_L, W_hat, F_pk (None = NA)."""
    margin = margin_at_loc(rec, tm.n_L)
    out = {"m_L": margin, "t14": t14_check(rec, rows, tm.n_L, margin["c_star_run_m"])}
    s_L = rows.at(rec.stroke, tm.n_L)
    att = rows.at(rec.att, tm.n_L)
    c_hat = rows.at(rec.c_hat, tm.n_L)
    load = rows.at(rec.load, tm.n_L)
    out["s_L"] = _legs(s_L)
    out["c_hat_L_m"] = None if c_hat is None else _num(c_hat)
    if att is not None and np.all(np.isfinite(att)):
        roll, pitch = float(att[0]), float(att[1])
        ds = geo.pad_xy_m[:, 0] * pitch - geo.pad_xy_m[:, 1] * roll
        out.update(att_L_rad=[roll, pitch], ds_geo=_legs(ds))
    else:
        out.update(att_L_rad=None, ds_geo=None)
    if load is not None and np.all(np.isfinite(load)) and tm.n_L is not None:
        static = geo.static_loads_N[rec.level]
        before = np.asarray(rec.n) <= tm.n_L
        f_pk = np.nanmax(np.asarray(rec.load)[before], axis=0)
        out.update(W_hat=_legs(static - load), F_pk=_legs(f_pk), static_N=_legs(static))
    else:
        out.update(W_hat=None, F_pk=None, static_N=_legs(geo.static_loads_N[rec.level]))
    return out


def power_term(f_pk: float | None, w_hat: float | None) -> float | None:
    """``(F_pk + max(W, 0))^(1/n_a) - F_pk^(1/n_a)`` (None when F_pk <= 0 or NA)."""
    if not _finite(f_pk) or not _finite(w_hat) or f_pk <= 0.0:
        return None
    exponent = 1.0 / N_A
    return (f_pk + max(w_hat, 0.0)) ** exponent - f_pk ** exponent


def predictions(inputs: dict, constants: dict | None) -> dict[str, list[float | None]]:
    """Rules 7.2: P-A, P-B, P-D, P-C per leg (None where an input or constant is NA)."""
    s_L, ds = inputs.get("s_L"), inputs.get("ds_geo")
    c_hat, m_L = inputs.get("c_hat_L_m"), inputs["m_L"]["m_L_m"]
    if s_L is None or ds is None or c_hat is None or m_L is None:
        return {q: [None] * 4 for q in ("P-A", "P-B", "P-D", "P-C")}
    lift = max(C_STAR_M + m_L - c_hat, 0.0)
    p_a = [None if s_L[i] is None or ds[i] is None else s_L[i] + ds[i] + lift for i in range(4)]
    out = {"P-A": p_a}
    kappa = (constants or {}).get("kappa_z_m_per_N") or {}
    c_type = (constants or {}).get("C_type") or {}
    delta_allow = (constants or {}).get("delta_allow_m")
    w_hat, f_pk = inputs.get("W_hat"), inputs.get("F_pk")
    p_b, p_d, p_c = [], [], []
    for i in range(4):
        k_i, c_i = kappa.get(PAD_TYPE[i]), c_type.get(PAD_TYPE[i])
        w_i = None if w_hat is None else w_hat[i]
        pb = (None if p_a[i] is None or not _finite(k_i) or not _finite(w_i)
              else p_a[i] + k_i * max(w_i, 0.0))
        term = power_term(None if f_pk is None else f_pk[i], w_i)
        pd = None if p_a[i] is None or not _finite(c_i) or term is None else p_a[i] + c_i * term
        p_b.append(pb)
        p_d.append(pd)
        p_c.append(None if pb is None or not _finite(delta_allow) else pb + delta_allow)
    out.update({"P-B": p_b, "P-D": p_d, "P-C": p_c})
    return out


def prediction_errors(s_max: np.ndarray, preds: dict) -> dict[str, list[float | None]]:
    """M-6: ``e_i(q) = s_i,max - s_hat_i(q)`` (+ = prediction short)."""
    return {q: [None if v is None else float(s_max[i]) - v for i, v in enumerate(values)]
            for q, values in preds.items()}


def run_metrics(rec: RunRecord, geo: Geometry, constants: dict | None,
                budget_leg: str | None = None) -> dict:
    """M-1 .. M-8 of one run (grid M-11 is added by :func:`grid_metrics`)."""
    rows = Rows(rec.n)
    tm = run_timing(rec)
    sinks = sink_metrics(rec, rows, tm)
    inputs = predictor_inputs(rec, rows, tm, geo)
    preds = predictions(inputs, constants)
    errors = prediction_errors(tm.s_max, preds)
    s_R = rows.at(rec.stroke, tm.n_R)
    b_star = tm.b_star
    out = {
        "run_id": rec.run_id, "source": rec.source, "level": rec.level,
        "M-1": {"n_dep": tm.n_dep, "n_L1": tm.n_L1, "n_L": tm.n_L, "loc_revokes": tm.revokes,
                "n_R": tm.n_R, "n_creep": tm.n_creep, "n_max": tm.n_max, "n_end": tm.n_end,
                "t_L1_s": _t(tm.n_L1), "t_L_s": _t(tm.n_L), "t_R_s": _t(tm.n_R),
                "t_max_s": _t(tm.n_max), "t_creep_s": _t(tm.n_creep)},
        "M-2": {"s_L": inputs["s_L"], "s_R": _legs(s_R), "s_max": _legs(tm.s_max),
                "b_star": LEGS[b_star], "g_m": S_GUARD_M - float(np.max(tm.s_max)),
                "n_sgs": tm.n_sgs, "n_warn_lift": tm.n_warn_lift},
        "M-4": {"n_e": tm.n_e, "n_e_leg": tm.n_e_leg, "n_max_leg": tm.n_max_leg, **sinks},
        "M-5": {"delta_os": None if s_R is None else _legs(tm.s_max - np.asarray(s_R)),
                "t_max_minus_t_L_s": None if tm.n_L is None else (tm.n_max - tm.n_L) * PERIOD_S},
        "M-6": {"predictions": preds, "errors": errors,
                "lower_bound": tm.n_sgs is not None},  # rules 7.4: SGS s_max is a lower bound
        "predictor_inputs": inputs,
        "M-7": crawler_metrics(rec, rows, tm),
        "M-8": rule_activity(rec),
        "is_sgs": tm.n_sgs is not None, "has_ready": tm.n_R is not None,
        "has_loc": tm.n_L is not None,
    }
    if budget_leg is not None:
        out["budget_leg_b"] = budget_leg
    return out


def _t(n: int | None) -> float | None:
    return None if n is None else n * PERIOD_S


def crawler_metrics(rec: RunRecord, rows: Rows, tm: Timing) -> dict:
    """M-7 from the run record (the Chrono P3-5 / 1 ms values are added by the row)."""
    return {
        "c_hat_m": {name: None if rows.at(rec.c_hat, n) is None else _num(rows.at(rec.c_hat, n))
                    for name, n in (("L", tm.n_L), ("R", tm.n_R), ("end", tm.n_end))},
        "clear_true_m": {name: None if rows.at(rec.crawler_clear, n) is None
                         else _num(rows.at(rec.crawler_clear, n))
                         for name, n in (("L", tm.n_L), ("R", tm.n_R), ("end", tm.n_end))},
    }


def rule_activity(rec: RunRecord) -> dict:
    """M-8: E3c10 / R4c30 events, R4 order skips, revokes, DSb75, SGS, P30fz, LWa."""
    names = [name for _, name in rec.events]
    return {
        "E3c10": [n for n in names if event_base(n) == EV_E3C10],
        "R4c30": [n for n in names if event_base(n) == EV_R4C30],
        "R4_skipped_order": sum(1 for n in names if n == EV_R4_SKIP),
        "loc_revoked": sum(1 for n in names if event_base(n) == EV_REVOKE),
        "order_gate_decisions": rec.extra.get("order_gate_decisions"),
        "dsb75_hold": sum(1 for n in names if event_base(n) == EV_DSB_HOLD),
        "dsb75_release_reasons": [n.split(":", 1)[1] if ":" in n else None
                                  for n in names if event_base(n) == EV_DSB_RELEASE],
        "sgs": sum(1 for n in names if is_sgs_event(n)),
        "P30fz_pauses": sum(1 for n in names if event_base(n) == EV_LIFT_PAUSED),
        "LWa_restarts": sum(1 for n in names if event_base(n) == EV_WINDOW_RESTART),
    }


# ===================================================================================== grid
def k_eq(b_m: float, geo: Geometry) -> float:
    return geo.kc / b_m + geo.kphi


def grid_point(rec: RunRecord, geo: Geometry, leg: int, n: int | None) -> dict:
    """M-11 / T-7 at period ``n`` for one leg: f, z/f, delta_grid, dz_1n and the validity."""
    grid = rec.grid
    if grid is None or n is None:
        return {"state": "no_record"}
    hits = np.flatnonzero(np.asarray(grid.n) == int(n))
    if hits.size == 0:
        return {"state": "no_record"}
    k = int(hits[0])
    n_h = float(grid.n_contact[k, leg])
    area, delta = float(geo.pad_area_m2[leg]), float(grid.grid_m)
    hull_a, hull_p = float(grid.hull_area[k, leg]), float(grid.hull_perimeter[k, leg])
    z_geo, sigma = float(grid.z_geo[k, leg]), float(grid.sigma_sum[k, leg])
    out = {"n": int(n), "N_h": n_h, "N_h_d2_over_A": n_h * delta * delta / area}
    if not (hull_a > 0.0 and hull_p > 0.0 and n_h > 0.0 and math.isfinite(delta)):
        return {**out, "state": "invalid", "reason": "empty contact hull"}
    b_hull = 2.0 * hull_a / hull_p
    law_force = n_h * delta * delta * k_eq(b_hull, geo) * max(z_geo, 0.0) ** geo.n_soil
    residual = (geo.n_soil * abs(sigma - law_force) / sigma) if sigma > 0.0 else math.inf
    nominal = area / (delta * delta)
    is_n_ok = (GRID_N_BAND[0] * nominal - GRID_N_TOL <= n_h
               <= GRID_N_BAND[1] * nominal + GRID_N_TOL)
    is_law_ok = residual - GRID_LAW_MAX <= GRID_LAW_TOL
    f_value = (n_h * delta * delta * k_eq(b_hull, geo)
               / (area * k_eq(float(geo.pad_b_poly_m[leg]), geo))) ** (-1.0 / geo.n_soil)
    out.update(b_hull_m=b_hull, r_sigma=residual, check_i=is_n_ok, check_ii=is_law_ok,
               f=f_value, state="valid" if is_n_ok and is_law_ok else "invalid")
    return out


def grid_metrics(rec: RunRecord, metrics: dict, geo: Geometry) -> dict:
    """M-11 for every leg at t_L, t_R, t_max, t_e, t_end plus the derived corrections."""
    tm_n = {"L": metrics["M-1"]["n_L"], "R": metrics["M-1"]["n_R"],
            "max": metrics["M-1"]["n_max"], "e": metrics["M-4"]["n_e"],
            "end": metrics["M-1"]["n_end"]}
    rows = Rows(rec.n)
    delta = rec.grid.grid_m if rec.grid is not None else math.nan
    points: dict = {}
    for name, n in tm_n.items():
        z = _z(rows, rec, n)
        leg_points = []
        for i in range(4):
            point = grid_point(rec, geo, i, n)
            if z is not None and point.get("state") == "valid":
                point["z_over_f"] = float(z[i]) / point["f"]
                point["delta_grid"] = float(z[i]) * (1.0 - 1.0 / point["f"])
            if z is not None and math.isfinite(delta):
                point["dz_1n"] = float(z[i]) * delta * delta / (geo.n_soil * geo.pad_area_m2[i])
            leg_points.append(point)
        points[name] = leg_points
    return {"grid_m": _num(delta), "points": points,
            "dz_post_corr": [_corr_increment(rows, rec, points, i, tm_n) for i in range(4)],
            "z_e_df_eL": [_df_record(rows, rec, points, i, tm_n["e"], "e") for i in range(4)],
            "z_max_df_maxL": [_df_record(rows, rec, points, i, tm_n["max"], "max")
                              for i in range(4)]}


def _corr_increment(rows, rec, points, leg, tm_n) -> float | None:
    """C-5 (a): ``z(t_e)/f(t_e) - z(t_L)/f(t_L)`` only with both records valid."""
    p_e, p_L = points["e"][leg], points["L"][leg]
    if p_e.get("state") != "valid" or p_L.get("state") != "valid":
        return None
    z_e, z_L = _z(rows, rec, tm_n["e"]), _z(rows, rec, tm_n["L"])
    if z_e is None or z_L is None:
        return None
    return float(z_e[leg]) / p_e["f"] - float(z_L[leg]) / p_L["f"]


def _df_record(rows, rec, points, leg, n_tau, name) -> float | None:
    """C-5 (c) record ``z(tau) (f(tau) - f(t_L))`` (both records valid)."""
    p_tau, p_L = points[name][leg], points["L"][leg]
    z = _z(rows, rec, n_tau)
    if p_tau.get("state") != "valid" or p_L.get("state") != "valid" or z is None:
        return None
    return float(z[leg]) * (p_tau["f"] - p_L["f"])


# ===================================================================================== rows
def chrono_identity_checks(row_id: str, facts: dict, geo: Geometry) -> list[str]:
    """I-3, I-4, I-7, I-11 read from result.json (the rest comes from the identity record)."""
    result = facts["result"]
    problems = []
    expect = (result.get("c2_setup") or {}).get("expect_controller") or {}
    if expect.get("name") != CTRL_TAG_VB or expect.get("ok") is not True:
        problems.append(f"I-3 expect_controller {expect.get('name')!r} ok {expect.get('ok')!r}")
    if (result.get("args") or {}).get("expect_controller") != CTRL_TAG_VB:
        problems.append("I-3 --expect-controller is not the rules tag")
    threads = result.get("num_threads_chrono", (result.get("meta") or {}).get("num_threads_chrono"))
    if threads != 4:
        problems.append(f"I-4 num_threads_chrono {threads!r}")
    hook = result.get("hull_hook") or {}
    requested = hook.get("requested") or (hook.get("default_mode")
                                          if hook.get("source") == "default" else None)
    if hook.get("mode") != "fast" or requested != "fast" or hook.get("dll_sha256") != HULL_DLL_SHA:
        problems.append(f"I-7 hull_hook mode {hook.get('mode')!r} requested {requested!r}")
    mass_scale = (result.get("args") or {}).get("mass_scale", 1.0)
    expected_scale = C6_MASS_SCALE if row_id == "C6" else 1.0
    if not _finite(mass_scale) or abs(float(mass_scale) - expected_scale) > 1e-12:
        problems.append(f"I-11 plant mass_scale {mass_scale!r} != {expected_scale}")
    w_ref = ((result.get("c2_soil") or {}).get("W_ref_N"))
    nominal = geo.superstructure_mass_kg.get(CHRONO_ROWS[row_id].level)
    if w_ref is not None and nominal is not None:
        g_ref = float(w_ref) / nominal
        if abs(g_ref - 9.80665) > 1e-6:
            problems.append(f"I-11 controller W_ref {w_ref} is not the YAML mass x g")
    return problems


def _rc_of(row_id: str, batch: Path, identity: dict) -> int | None:
    rc = ((identity.get("rows") or {}).get(row_id) or {}).get("rc")
    if isinstance(rc, int):
        return rc
    path = batch / "batch.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    for case in data.get("cases", []) if isinstance(data, dict) else []:
        if isinstance(case, dict) and CHRONO_ROWS[row_id].case in (case.get("case"),
                                                                   case.get("name")):
            for key in ("rc", "returncode", "exit_code"):
                if isinstance(case.get(key), int):
                    return case[key]
    return None


def chrono_row_state(row_id: str, rec: RunRecord | None, facts: dict, metrics: dict | None,
                     identity: dict, harness: dict[str, HarnessRun], batch: Path,
                     geo: Geometry) -> dict:
    """Rules 3.1 V-1 .. V-4: VALID / MISSING / MISSING_START / NO_LOC / INVALID."""
    reasons: list[str] = []
    rc = _rc_of(row_id, batch, identity)
    state = {"row_id": row_id, "case": CHRONO_ROWS[row_id].case, "rc": rc}
    if rec is None or rc != 0:
        reasons.append(f"V-1 rc {rc!r}, files {facts.get('files_present')}")
        return {**state, "status": "MISSING", "reasons": reasons}
    n_dur = int(round(CHRONO_ROWS[row_id].duration_s / PERIOD_S))
    is_stop_end = metrics["is_sgs"] or str(rec.final_phase or "").lower() in FAULT_PHASES
    if not (metrics["M-1"]["n_end"] >= n_dur - 1 or is_stop_end):  # T-11
        reasons.append(f"V-1 n_end {metrics['M-1']['n_end']} < {n_dur - 1} without SGS / FAULT")
        return {**state, "status": "MISSING", "reasons": reasons}
    entry = (identity.get("rows") or {}).get(row_id)
    own = chrono_identity_checks(row_id, facts, geo)
    if entry is None or entry.get("ok") is not True or own:
        reasons += own + list((entry or {}).get("reasons") or [])
        if entry is None:
            reasons.append("V-2 identity record absent for this row")
        return {**state, "status": "INVALID", "reasons": reasons}
    if any(name.startswith(START_REFUSAL_PREFIX) for _, name in rec.events):
        return {**state, "status": "MISSING_START", "reasons": ["V-3 start refused"]}
    if not metrics["has_loc"]:
        return {**state, "status": "NO_LOC", "reasons": ["V-3 no LOC"]}
    pair = harness.get(harness_run_id(_pair_group(row_id), row_id, "VB", 0.0))
    state["harness_pair"] = None if pair is None else pair.record.run_id
    if pair is None:
        state["notes"] = ["V-4 harness VB e0 pair absent: D-c NA for this row"]
    return {**state, "status": "VALID", "reasons": []}


def _pair_group(row_id: str) -> str:
    return "H-W" if row_id == "C6" else "H-P"


def safety_notes(rec: RunRecord, facts: dict) -> list[str]:
    """SAFETY_NOTE: FAULT_STROKE_END, leg lift (T-8) after the first LOC, crawler re-landing
    (T-9) after the departure."""
    notes = [f"FAULT_STROKE_END at {t:.1f} s" for t, name in rec.events
             if event_base(name) == EV_STROKE_END]
    series = facts.get("series") or {}
    t_1ms = np.asarray(series.get("t_s", []), dtype=float)
    first_loc = next((t for t, name in rec.events if name == EV_LOC), None)
    pads = series.get("scm_pad_normal_N")
    if pads is not None and first_loc is not None:
        after = t_1ms >= first_loc - SERIES_LOOKUP_TOL_S
        for i in range(4):
            run = _longest_run(np.asarray(pads, dtype=float)[after, i] <= 0.0)
            if run >= T8_SAMPLES:
                notes.append(f"T-8 leg {LEGS[i]} contact 0 for {run} samples after the LOC")
    crawler = series.get("scm_crawler_normal_N")
    weight = ((facts.get("result") or {}).get("p3b") or {}).get("weight_N")
    if crawler is not None and _finite(rec.t_departure_s) and _finite(weight):
        after = t_1ms >= rec.t_departure_s - SERIES_LOOKUP_TOL_S
        values = np.asarray(crawler, dtype=float)[after]
        if values.size and np.any(values - T9_FRACTION * weight >= -T9_TOL_N):
            notes.append("T-9 crawler normal force >= 0.01 W after the departure")
    return notes


def _longest_run(mask: np.ndarray) -> int:
    best = current = 0
    for value in mask:
        current = current + 1 if value else 0
        best = max(best, current)
    return best


# ===================================================================================== constants
def harness_constants(runs: dict[str, HarnessRun], geo: Geometry) -> dict:
    """Rules 7.3 from the 20 H-P runs (E-2: a constant with no leg is NA)."""
    hp = sorted(run_id for run_id in runs if run_id.startswith("H-P|"))
    kappa: dict[str, list] = {FRONT: [], REAR: []}
    c_values: dict[str, list] = {FRONT: [], REAR: []}
    per_run_kappa: dict[str, dict[str, float]] = {FRONT: {}, REAR: {}}
    excluded = {"no_loc_runs": [], "c_type_nonpositive_denominator": 0, "na_legs": 0}
    delta_os = []
    for run_id in hp:
        metrics = run_metrics(runs[run_id].record, geo, None)
        if not metrics["has_loc"]:
            excluded["no_loc_runs"].append(run_id)
            continue
        _collect_leg_constants(run_id, metrics, kappa, c_values, per_run_kappa, excluded)
        os_values = metrics["M-5"]["delta_os"]
        b_star = LEGS.index(metrics["M-2"]["b_star"])
        if os_values is not None and os_values[b_star] is not None:
            delta_os.append((run_id, os_values[b_star]))
    return {
        "schema": SCHEMA_CONSTANTS, "rules_file": RULES_FILE, "rules_sha256": RULES_SHA256,
        "path": PATH_NAME, "runs_used": hp, "excluded": excluded,
        "kappa_z_m_per_N": {t: _max_or_na(v) for t, v in kappa.items()},
        "C_type": {t: _max_or_na(v) for t, v in c_values.items()},
        "n_a": N_A,
        "kappa_ratio": {t: _ratio_record(per_run_kappa[t]) for t in (FRONT, REAR)},
        "delta_allow_m": _max_or_na([v for _, v in delta_os]),
        "delta_allow_runs": [run_id for run_id, _ in delta_os],
    }


def _collect_leg_constants(run_id, metrics, kappa, c_values, per_run_kappa, excluded) -> None:
    dz = metrics["M-4"]["dz_post_leg_window"]
    inputs = metrics["predictor_inputs"]
    w_hat, f_pk = inputs.get("W_hat"), inputs.get("F_pk")
    for i in range(4):
        pad = PAD_TYPE[i]
        if dz[i] is None or w_hat is None or w_hat[i] is None:
            excluded["na_legs"] += 1
            continue
        k_value = dz[i] / max(w_hat[i], KAPPA_W_FLOOR_N)
        kappa[pad].append((run_id, LEGS[i], k_value))
        current = per_run_kappa[pad].get(run_id)
        per_run_kappa[pad][run_id] = k_value if current is None else max(current, k_value)
        term = power_term(None if f_pk is None else f_pk[i], w_hat[i])
        if term is None or term <= 0.0:
            excluded["c_type_nonpositive_denominator"] += 1
            continue
        c_values[pad].append((run_id, LEGS[i], dz[i] / term))


def _max_or_na(values: list) -> float | str:
    numbers = [v[-1] if isinstance(v, tuple) else v for v in values]
    numbers = [v for v in numbers if v is not None and math.isfinite(v)]
    return max(numbers) if numbers else NA


def _ratio_record(per_run: dict[str, float]) -> dict:
    values = [v for v in per_run.values() if math.isfinite(v)]
    if not values or min(values) <= 0.0:
        return {"per_run": per_run, "ratio": NA, "kappa_nonlinear": None}
    ratio = max(values) / min(values)
    return {"per_run": per_run, "ratio": ratio, "kappa_nonlinear": ratio > KAPPA_RATIO_FLAG}


def constants_for_prediction(constants: dict) -> dict:
    """Constants with NA as None (rules E-2)."""
    def clean(value):
        return None if value == NA else value

    return {"kappa_z_m_per_N": {k: clean(v) for k, v in constants["kappa_z_m_per_N"].items()},
            "C_type": {k: clean(v) for k, v in constants["C_type"].items()},
            "delta_allow_m": clean(constants["delta_allow_m"])}


# ===================================================================================== grades
def _grade(name: str, rows: list[str], **fields) -> dict:
    """A grade block; ``NA`` when it was computed on no row (rules 3.2, E-6)."""
    grade = fields.pop("grade", NA)
    flags = fields.pop("flags", [])
    return {"code": name, "grade": grade if rows else NA, "rows": list(rows),
            "row_count": len(rows), "flags": list(flags), **fields}


def classify_band(low: float, high: float, threshold: float) -> str:
    """Rules T-3 on an interval (a point is ``low == high``): "+", "-", "0" or "undetermined"."""
    if low - threshold > EPS_TH_M:
        return "+"
    if -high - threshold > EPS_TH_M:
        return "-"
    if abs(low) - threshold <= EPS_TH_M and abs(high) - threshold <= EPS_TH_M:
        return "0"
    return "undetermined"


def grade_D_a(chrono: dict[str, dict], harness_metrics: dict[str, dict], r_rows: list[str]) -> dict:
    """D-a with the C-5 conditions (a) (b) (c)."""
    raw = {r: chrono[r]["metrics"]["M-4"]["dz_post"][chrono[r]["b_star"]] for r in r_rows}
    corr = {r: chrono[r]["grid"]["dz_post_corr"][chrono[r]["b_star"]] if chrono[r]["grid"]
            else None for r in r_rows}
    hn_values = []
    for r in r_rows:
        for setting in ("VB", "V0"):
            m = harness_metrics.get(harness_run_id("H-P", r, setting, 0.0))
            if m is not None and m["M-4"]["dz_post"] is not None:
                value = m["M-4"]["dz_post"][chrono[r]["b_star"]]
                if value is not None:
                    hn_values.append(value)
    flags = [f"침하 기록 없음: {r}" for r, v in raw.items() if v is None]
    rows = [r for r in r_rows if raw[r] is not None]
    if not rows or not hn_values:
        return _grade("D-a", [], flags=[*flags, "raw or harness value NA"], raw_by_row=raw)
    z_ch, z_hn = max(raw[r] for r in rows), max(hn_values)
    raw_grade = "ZA-1" if z_ch - z_hn - ZA_M <= EPS_TH_M else "ZA-2"
    corr_known = [v for v in corr.values() if v is not None]
    z_corr = max(corr_known) if corr_known else None
    corr_grade = (NA if z_corr is None else
                  "ZA-1" if z_corr - z_hn - ZA_M <= EPS_TH_M else "ZA-2")
    flags += [f"격자 기록 없음: {r}" for r, v in corr.items() if v is None]
    final = raw_grade if corr_grade == NA else (
        "ZA-2" if "ZA-2" in (raw_grade, corr_grade) else "ZA-1")
    if corr_grade != NA and corr_grade != raw_grade:
        flags.append("격자 위상 의존")
    correction = None
    if raw_grade == "ZA-2" and corr_grade == "ZA-1":
        correction = z_ch - z_hn
        flags.append("격자 몫 포함 보정")
    base = max(v for v in (z_ch, z_corr, z_hn) if v is not None)
    z2 = [0.1 * chrono[r]["metrics"]["M-4"]["z_R"][chrono[r]["b_star"]] for r in rows
          if chrono[r]["metrics"]["M-4"]["z_R"] is not None]
    return _grade("D-a", rows, grade=final, flags=flags, raw_grade=raw_grade,
                  corr_grade=corr_grade, Z_ch=z_ch, Z_corr=z_corr, Z_hn=z_hn,
                  raw_by_row=raw, corr_by_row=corr, harness_correction_m=correction,
                  Z_B1_before_soil_m=base,
                  Z_soil_candidates={**Z_SOIL_CANDIDATES,
                                     "Z2": max(z2) if z2 else NA, "Zf": NA})


def grade_D_b(chrono: dict, harness_metrics: dict, r_rows: list[str]) -> dict:
    """D-b: a row without its own READY (SGS) has delta_os NA and leaves the row count."""
    values, used, dropped = [], [], []
    for r in r_rows:
        b = chrono[r]["b_star"]
        own = chrono[r]["metrics"]["M-5"]["delta_os"]
        if own is None or own[b] is None:
            dropped.append(r)
            continue
        pair = harness_metrics.get(harness_run_id("H-P", r, "VB", 0.0))
        pair_os = None if pair is None else pair["M-5"]["delta_os"]
        candidates = [v[b] for v in (own, pair_os) if v is not None and v[b] is not None]
        values.append(max(candidates))
        used.append(r)
    if not values:
        return _grade("D-b", [], dropped_no_ready=dropped)
    top = max(values)
    return _grade("D-b", used, grade="OS-MAX" if top - OS_M > EPS_TH_M else "OS-FINAL",
                  O_m=top, dropped_no_ready=dropped)


def d_c_row(chrono_row: dict, pair_metrics: dict | None, geo: Geometry) -> dict | None:
    """D-c of one row: raw, corrected (or fallback band) and the classes (T-3)."""
    if pair_metrics is None:
        return None
    b = chrono_row["b_star"]
    raw = chrono_row["metrics"]["M-2"]["s_max"][b] - pair_metrics["M-2"]["s_max"][b]
    z_max = chrono_row["metrics"]["M-4"]["z_max"]
    z = None if z_max is None else z_max[b]
    point = (chrono_row["grid"] or {}).get("points", {}).get("max", [{}] * 4)[b]
    out = {"raw_m": raw, "raw_class": classify_band(raw, raw, HC_M), "flags": []}
    if point.get("state") == "valid" and z is not None:
        corrected = raw - point["delta_grid"]
        out.update(corr_m=corrected, corr_low_m=corrected, corr_high_m=corrected,
                   corr_class=classify_band(corrected, corrected, HC_M),
                   delta_grid_m=point["delta_grid"])
        if abs(corrected) <= point.get("dz_1n", -1.0):
            out["flags"].append("절점 계단 수준")
    elif z is not None:
        f_min, f_max = F_PHASE_BAND[PAD_TYPE[b]]
        low, high = raw - z * (1.0 - 1.0 / f_max), raw - z * (1.0 - 1.0 / f_min)
        out.update(corr_m=None, corr_low_m=low, corr_high_m=high,
                   corr_class=classify_band(low, high, HC_M))
        out["flags"].append("대체 범위")
    else:
        out.update(corr_m=None, corr_class="undetermined")
        out["flags"].append("침하 기록 없음")
    if out["corr_class"] == "undetermined":
        out["flags"].append("격자 위상 의존(부호 미확정)")
    return out


def _class_grade(classes: list[str]) -> str:
    known = [c for c in classes if c != "undetermined"]
    if not known:
        return NA
    if "+" in known:
        return "H-OPT"
    return "H-CONS" if "-" in known else "H-OK"


def grade_D_c(chrono: dict, harness_metrics: dict, r_rows: list[str], geo: Geometry) -> dict:
    per_row = {}
    for r in r_rows:
        result = d_c_row(chrono[r], harness_metrics.get(harness_run_id("H-P", r, "VB", 0.0)), geo)
        if result is not None:
            per_row[r] = result
    rows = sorted(per_row)
    corr_grade = _class_grade([per_row[r]["corr_class"] for r in rows])
    raw_grade = _class_grade([per_row[r]["raw_class"] for r in rows])
    flags = []
    undetermined = [r for r in rows if per_row[r]["corr_class"] == "undetermined"]
    if undetermined:
        flags.append(f"격자 위상 의존(부호 미확정): {', '.join(undetermined)}")
    if raw_grade != corr_grade:
        flags.append("격자 위상 의존")
    if any("대체 범위" in per_row[r]["flags"] for r in rows):
        flags.append("대체 범위")
    na_pair = [r for r in r_rows if r not in per_row]
    return _grade("D-c", rows, grade=corr_grade, flags=flags, raw_grade=raw_grade,
                  per_row=per_row, no_pair_rows=na_pair)


PRED_ORDER = ("P-A", "P-B", "P-D", "P-C")


def grade_D_d(chrono: dict, r_rows: list[str]) -> dict:
    """D-d: ``E_q`` over the rows with D-d inputs; ties to the simpler candidate."""
    rows = [r for r in r_rows if chrono[r]["metrics"]["predictor_inputs"]["t14"]["ok"]]
    excluded = {r: "T-14 mismatch" for r in r_rows if r not in rows}
    e_q: dict[str, float | str] = {}
    for q in PRED_ORDER:
        values = [chrono[r]["metrics"]["M-6"]["errors"][q][chrono[r]["b_star"]] for r in rows]
        e_q[q] = NA if (not values or any(v is None for v in values)) else max(
            abs(v) for v in values)
    known = [q for q in PRED_ORDER if e_q[q] != NA]
    flags = [f"행 제외 {r}: {why}" for r, why in excluded.items()]
    if any(chrono[r]["metrics"]["is_sgs"] for r in rows):
        flags.append("하한 포함")
    if not known:
        return _grade("D-d", [], E_q=e_q, flags=flags)
    best_value = min(e_q[q] for q in known)
    best = next(q for q in known if abs(e_q[q] - best_value) <= EPS_TH_M)
    grade = "PRED-FAIL" if best_value - PRED_M > EPS_TH_M else f"PRED-{best}"
    lower_bound = {r: chrono[r]["metrics"]["is_sgs"] for r in rows}
    return _grade("D-d", rows, grade=grade, flags=flags, E_q=e_q, q_star=best,
                  lower_bound_rows=lower_bound)


def grade_D_e(chrono: dict, statuses: dict, geo: Geometry) -> dict:
    rows = [r for r in NEED_ROWS if statuses[r] == "VALID"]
    per_row, all_ok = {}, True
    for r in rows:
        row = chrono[r]
        b = row["b_star"]
        g = row["metrics"]["M-2"]["g_m"]
        z_max = row["metrics"]["M-4"]["z_max"]
        z = None if z_max is None else z_max[b]
        f_min, f_max = F_PHASE_BAND[PAD_TYPE[b]]
        point = (row["grid"] or {}).get("points", {}).get("max", [{}] * 4)[b]
        entry = {"g_m": g, "sgs": row["metrics"]["is_sgs"]}
        if point.get("state") == "valid" and z is not None:
            g_corr = g + point["delta_grid"]
            g_tilde = min(g, g_corr - z * (1.0 - 1.0 / f_max))
            entry.update(g_corr_m=g_corr, g_tilde_m=g_tilde, source="grid record")
        elif z is not None:
            g_tilde = g - z * (f_max - f_min)
            entry.update(g_corr_m=None, g_tilde_m=g_tilde, source="no valid record")
        else:
            g_tilde = None
            entry.update(g_tilde_m=None, source="sinkage NA")
        if z is not None:
            entry["g_corr_band_m"] = [g + z * (1.0 - 1.0 / f_min), g + z * (1.0 - 1.0 / f_max)]
        is_ok = g_tilde is not None and g_tilde - NEED_M >= -EPS_TH_M and not entry["sgs"]
        entry["meets"] = is_ok
        all_ok = all_ok and is_ok
        per_row[r] = entry
    grade = "NEED-RECHECK" if rows == list(NEED_ROWS) and all_ok else "B1-OPEN"
    return _grade("D-e", rows, grade=grade, per_row=per_row,
                  note="SCM 명목 세트 안의 여유이고 실토양 여유가 아니다")


def grade_D_f(chrono: dict, statuses: dict, harness: dict[str, HarnessRun],
              harness_metrics: dict) -> dict:
    if statuses.get("C5") != "VALID":
        return _grade("D-f", [], reason="C5 not VALID")
    if not chrono["C5"]["metrics"]["is_sgs"]:
        return _grade("D-f", ["C5"], grade="FUP-NA")
    pairs, excluded = {}, []
    for setting in ("VB", "V0"):
        run_id = harness_run_id("H-M0", "C5", setting, 0.0)
        metrics = harness_metrics.get(run_id)
        if metrics is None:
            excluded.append(f"{run_id}: absent")
        elif metrics["M-8"]["R4c30"]:
            excluded.append(f"{run_id}: R4c30 event (E-3)")
        else:
            pairs[run_id] = {"sgs": metrics["is_sgs"], "ready": metrics["has_ready"]}
    if not pairs:
        return _grade("D-f", [], reason="E-3: no H-M0 C5 pair (계산 불가)", excluded=excluded)
    if any(p["ready"] for p in pairs.values()):
        grade = "FUP-IN"
    elif all(p["sgs"] for p in pairs.values()):
        grade = "FUP-OUT"
    else:
        grade = NA
    flags = ["짝 1개"] if len(pairs) == 1 else []
    return _grade("D-f", ["C5", *pairs], grade=grade, pairs=pairs, excluded=excluded,
                  flags=flags)


def grade_D_g(chrono: dict, statuses: dict, d_d: dict) -> dict:
    if statuses.get("C6") != "VALID" or d_d["grade"] in (NA, "PRED-FAIL"):
        return _grade("D-g", ["C6"] if statuses.get("C6") == "VALID" else [], grade="W-NA")
    q_star = d_d["q_star"]
    row = chrono["C6"]
    e = row["metrics"]["M-6"]["errors"][q_star][row["b_star"]]
    e_best = d_d["E_q"][q_star]
    if e is None:
        return _grade("D-g", ["C6"], grade="W-NA", reason=f"C6 {q_star} NA")
    grade = "W-OK" if abs(e) - e_best - WG_M <= EPS_TH_M else "W-EXT"
    ratio = abs(e) / e_best if e_best > 0.0 else None
    return _grade("D-g", ["C6"], grade=grade, e_C6_m=e, E_q_star_m=e_best, q_star=q_star,
                  ratio=ratio, lower_bound=row["metrics"]["is_sgs"])


def grade_D_h(harness: dict[str, HarnessRun], p7_path: Path | None) -> dict:
    hp = sorted(run_id for run_id in harness if run_id.startswith("H-P|"))
    if p7_path is None:
        return _grade("D-h", [], reason="P7_REF not given")
    if sha256_file(p7_path) != P7_REF_SHA256:
        return _grade("D-h", [], reason="P7_REF sha256 is not the rules value")
    reference = {}
    for text in p7_path.read_text(encoding="utf-8").splitlines():
        if not text.strip():
            continue
        line = json.loads(text)
        if (line.get("s2d") or {}).get("candidate") == P7_CANDIDATE:
            reference[(line.get("d1") or {}).get("key")] = line.get("commands_sha256")
    per_run = {}
    for run_id in hp:
        line = harness[run_id].line
        key = f"{line['d1_key']}|{line['setting']}|e{float(line['eps']):g}"
        expected = reference.get(key)
        per_run[run_id] = ("K-NA" if expected is None else
                           "K-SAME" if expected == line["commands_sha256"] else "K-DIFF")
    states = set(per_run.values())
    grade = "K-DIFF" if "K-DIFF" in states else "K-NA" if "K-NA" in states else "K-SAME"
    return _grade("D-h", hp, grade=grade, per_run=per_run,
                  diff_keys=[r for r, s in per_run.items() if s == "K-DIFF"])


# ===================================================================================== M-12
def m12_records(runs: dict[str, HarnessRun], harness_metrics: dict, shadow_ok: bool,
                chrono: dict, r_rows: list[str]) -> dict:
    """Rules 7.5 (record only). Harness: the shadow is kept only when the H-SH0 pairs have
    equal command hashes. Chrono: entries of the same form in the row's result
    (:data:`CHRONO_SHADOW_KEY`); without them the row's M-12 is NA (E-4)."""
    harness: dict | str = NA
    if shadow_ok:
        harness = {run_id: _m12_run(run.line.get("loc_shadow"), harness_metrics[run_id])
                   for run_id, run in runs.items()}
    rows = {r: _m12_run(chrono[r]["shadow"], chrono[r]["metrics"]) for r in chrono}
    e_star = [rows[r]["e_P_A_star_m"] if isinstance(rows.get(r), dict) else None
              for r in r_rows]
    e_pa = [chrono[r]["metrics"]["M-6"]["errors"]["P-A"][chrono[r]["b_star"]] for r in r_rows]
    out = {"harness": harness, "chrono": rows,
           "harness_reason": None if shadow_ok else "H-SH0 command hashes differ or missing"}
    if r_rows and all(v is not None for v in e_star + e_pa):
        big_e_star, big_e = max(abs(v) for v in e_star), max(abs(v) for v in e_pa)
        out.update(E_P_A_m=big_e, E_P_A_star_m=big_e_star,
                   anchor_single_sample=abs(big_e - big_e_star) - M12_M > EPS_TH_M)  # T-13
    else:
        out.update(E_P_A_star_m=NA)
    if all(v == NA for v in rows.values()) and harness == NA:
        out["note"] = "M-12 기록 없음"  # E-4
    return out


def _m12_run(shadow: dict | None, metrics: dict) -> dict | str:
    """M-12 of one run: LOC entries, ``e`` of P-A* at b* and ``max |d|`` (NA without shadow)."""
    if not shadow or not shadow.get("locs"):
        return NA
    n_L = metrics["M-1"]["n_L"]
    locs = []
    for loc in shadow["locs"]:
        locs.append({"path": loc.get("path"), "c_min_tP_m": _mm(loc.get("c_min_tP_mm")),
                     "n_P": period_index(loc["t_P_s"]), "n_L": period_index(loc["t_L_s"]),
                     "c_hat_m": _mm(loc.get("c_hat_tL_current_mm")),
                     "c_hat_A_m": _mm(loc.get("c_hat_tL_shadow_mm")),
                     "d_m": _mm(loc.get("diff_tL_mm"))})
    last = next((loc for loc in reversed(locs) if loc["n_L"] == n_L), None)
    e_star = None
    inputs = metrics["predictor_inputs"]
    if last is not None and last["c_hat_A_m"] is not None and inputs["s_L"] is not None \
            and inputs["ds_geo"] is not None and inputs["m_L"]["m_L_m"] is not None:
        b = LEGS.index(metrics["M-2"]["b_star"])
        lift = max(C_STAR_M + inputs["m_L"]["m_L_m"] - last["c_hat_A_m"], 0.0)
        predicted = inputs["s_L"][b] + inputs["ds_geo"][b] + lift
        e_star = metrics["M-2"]["s_max"][b] - predicted
    d_values = [abs(loc["d_m"]) for loc in locs if loc["d_m"] is not None]
    return {"locs": locs, "e_P_A_star_m": e_star, "max_abs_d_m": max(d_values, default=None)}


def _mm(value) -> float | None:
    return None if value is None else float(value) / 1e3


# ===================================================================================== judge
def bundle_state(statuses: dict[str, str], harness: dict[str, HarnessRun]) -> str:
    """Rules 3.2: COMPLETE / PARTIAL / UNDETERMINED."""
    pairs_present = all(harness_run_id("H-P", r, "VB", 0.0) in harness for r in R_ROWS)
    if not pairs_present or any(statuses[r] != "VALID" for r in CORE_ROWS):
        return "UNDETERMINED"
    return "COMPLETE" if all(s == "VALID" for s in statuses.values()) else "PARTIAL"


def shadow_pairs(harness: dict[str, HarnessRun]) -> dict:
    out = {}
    for r in ("C1", "C2", "C4", "C5"):
        on = harness.get(harness_run_id("H-P", r, "VB", 0.0))
        off = harness.get(harness_run_id("H-SH0", r, "VB", 0.0))
        out[r] = ("missing" if on is None or off is None else
                  "same" if on.line["commands_sha256"] == off.line["commands_sha256"] else "DIFF")
    return {"pairs": out, "all_same": all(v == "same" for v in out.values())}


def judge(batch: Path, harness_jsonl: Path, identity: dict, geo: Geometry,
          constants_file: dict | None, p7_path: Path | None) -> dict:
    """Everything of the ``judge`` subcommand (module docstring)."""
    harness, refused = load_harness(harness_jsonl)
    constants = harness_constants(harness, geo)
    if constants_file is not None and _constants_core(constants_file) != _constants_core(constants):
        raise InputError("constants file differs from the constants of this harness jsonl")
    pred_constants = constants_for_prediction(constants)
    harness_metrics = {run_id: run_metrics(run.record, geo, pred_constants)
                       for run_id, run in harness.items()}
    chrono, statuses, row_states, safety = {}, {}, {}, {}
    for row_id in CHRONO_ROWS:
        rec, facts = load_chrono_row(batch, row_id)
        metrics = None if rec is None else run_metrics(rec, geo, pred_constants,
                                                       CHRONO_ROWS[row_id].budget_leg)
        state = chrono_row_state(row_id, rec, facts, metrics, identity, harness, batch, geo)
        statuses[row_id], row_states[row_id] = state["status"], state
        if rec is not None and metrics is not None:
            chrono[row_id] = _chrono_entry(rec, facts, metrics, geo)
            safety[row_id] = safety_notes(rec, facts)
    runner = identity.get("runner_log") or {}
    blocked = ["E-5"] if (runner.get("errors_total") or 0) > 0 and (
        runner.get("errors_left") or 0) > 0 else []
    bundle = bundle_state(statuses, harness)
    pairs = shadow_pairs(harness)
    out = {"schema": SCHEMA_METRICS, "path": PATH_NAME, "rules_file": RULES_FILE,
           "rules_sha256": RULES_SHA256, "tool_sha256": sha256_file(Path(__file__)),
           "batch_name": BATCH_NAME, "bundle": bundle, "blocked": blocked,
           "row_states": row_states, "harness_refused": refused, "shadow_pairs": pairs,
           "constants": constants, "safety_notes": {r: v for r, v in safety.items() if v},
           "rows": {r: _json_row(v) for r, v in chrono.items()},
           "harness": {r: _json_metrics(m) for r, m in harness_metrics.items()}}
    r_rows = [r for r in R_ROWS if statuses[r] == "VALID"]
    out["m12"] = _json_metrics(m12_records(harness, harness_metrics, pairs["all_same"],
                                           chrono, r_rows))
    out["pair_differences"] = pair_differences(chrono, harness_metrics)
    if bundle == "UNDETERMINED" or blocked:
        out["grades"] = {code: _grade(code, [], reason=f"bundle {bundle} {blocked}")
                         for code in ("D-a", "D-b", "D-c", "D-d", "D-e", "D-f", "D-g", "D-h")}
    else:
        out["grades"] = all_grades(chrono, statuses, harness, harness_metrics, geo, p7_path,
                                   bundle)
    self_check(out["grades"])
    return out


def _constants_core(constants: dict) -> str:
    keys = ("kappa_z_m_per_N", "C_type", "delta_allow_m", "runs_used", "n_a")
    return json.dumps({k: constants.get(k) for k in keys}, sort_keys=True)


def _chrono_entry(rec: RunRecord, facts: dict, metrics: dict, geo: Geometry) -> dict:
    grid = grid_metrics(rec, metrics, geo) if rec.grid is not None else None
    b_star = LEGS.index(metrics["M-2"]["b_star"])
    p3b = (facts.get("result") or {}).get("p3b") or {}
    metrics["M-7"]["p3_5"] = {k: (p3b.get("P3-5_clearance_stroke") or {}).get(k) for k in (
        "rut_clearance_at_loc_m", "rut_clearance_min_after_first_ready_m",
        "rut_clearance_end_m")}
    metrics["M-7"]["crawler_max_after_departure_N"] = _crawler_max_after(rec, facts)
    metrics["M-9"] = {name: (block or {}).get("within") for name, block in p3b.items()
                      if name.startswith("P3-") and isinstance(block, dict)}
    metrics["M-4h"] = _pad_shift(rec, metrics)
    return {"metrics": metrics, "grid": grid, "b_star": b_star,
            "b": LEGS.index(CHRONO_ROWS[rec.run_id].budget_leg), "shadow": rec.loc_shadow,
            "files_sha256": facts.get("sha256"), "b1_record_present": facts["b1_record_present"]}


def _crawler_max_after(rec: RunRecord, facts: dict) -> float | None:
    """M-7: largest 1 ms crawler normal force after the crawler departure [N]."""
    series = facts.get("series") or {}
    crawler = series.get("scm_crawler_normal_N")
    if crawler is None or not _finite(rec.t_departure_s):
        return None
    after = np.asarray(series["t_s"], dtype=float) >= rec.t_departure_s - SERIES_LOOKUP_TOL_S
    values = np.asarray(crawler, dtype=float)[after]
    return _num(values.max()) if values.size else None


def _pad_shift(rec: RunRecord, metrics: dict) -> list[float | None] | str:
    """M-4h: |pad xy (t_max) - pad xy (t_L)| per leg (record only)."""
    if rec.pad_xy is None:
        return NA
    rows = Rows(rec.pad_xy["n"])
    xy_L = rows.at(rec.pad_xy["xy"], metrics["M-1"]["n_L"])
    xy_max = rows.at(rec.pad_xy["xy"], metrics["M-1"]["n_max"])
    if xy_L is None or xy_max is None:
        return NA
    return [float(np.hypot(*(np.asarray(xy_max[i]) - np.asarray(xy_L[i])))) for i in range(4)]


def all_grades(chrono, statuses, harness, harness_metrics, geo, p7_path, bundle) -> dict:
    r_rows = [r for r in R_ROWS if statuses[r] == "VALID"]
    d_d = grade_D_d(chrono, r_rows)
    grades = {"D-a": grade_D_a(chrono, harness_metrics, r_rows),
              "D-b": grade_D_b(chrono, harness_metrics, r_rows),
              "D-c": grade_D_c(chrono, harness_metrics, r_rows, geo),
              "D-d": d_d, "D-e": grade_D_e(chrono, statuses, geo),
              "D-f": grade_D_f(chrono, statuses, harness, harness_metrics),
              "D-g": grade_D_g(chrono, statuses, d_d), "D-h": grade_D_h(harness, p7_path)}
    if bundle == "PARTIAL":
        if statuses["C3"] != "VALID":
            grades["D-d"]["flags"].append("PARTIAL (C3)")
        if statuses["C6"] != "VALID":
            grades["D-g"]["flags"].append("PARTIAL (C6)")
    return grades


def self_check(grades: dict) -> None:
    """E-6: a grade computed on no row must be NA (otherwise a tool defect)."""
    for code, block in grades.items():
        if block["row_count"] == 0 and block["grade"] != NA:
            raise AssertionError(f"E-6: {code} graded {block['grade']} on 0 rows")


def pair_differences(chrono: dict, harness_metrics: dict) -> dict:
    """M-10: Chrono - harness VB e0 at the row's b* (the V0 / e0.002 runs as spread)."""
    out = {}
    for r, row in chrono.items():
        b = row["b_star"]
        group = _pair_group(r)
        pair = harness_metrics.get(harness_run_id(group, r, "VB", 0.0))
        if pair is None:
            out[r] = NA
            continue
        quantities = {"s_max": ("M-2", "s_max"), "s_L": ("M-2", "s_L"), "s_R": ("M-2", "s_R"),
                      "dz_post": ("M-4", "dz_post"), "delta_os": ("M-5", "delta_os")}
        entry = {}
        for name, (block, key) in quantities.items():
            own, other = row["metrics"][block][key], pair[block][key]
            entry[name] = (None if own is None or other is None or own[b] is None
                           or other[b] is None else own[b] - other[b])
        entry["g"] = row["metrics"]["M-2"]["g_m"] - pair["M-2"]["g_m"]
        spread = [harness_metrics[k]["M-2"]["s_max"][b] for k in (
            harness_run_id(group, r, s, e) for s in ("VB", "V0") for e in (0.0, 2e-3))
            if k in harness_metrics]
        entry["harness_s_max_spread"] = [min(spread), max(spread)] if spread else None
        out[r] = entry
    return out


# ===================================================================================== JSON out
def _clean(value):
    """JSON-safe copy: non-finite floats -> None, numpy values -> Python values."""
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_clean(v) for v in value]
    if isinstance(value, np.ndarray):
        return _clean(value.tolist())
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, float | np.floating):
        return _num(float(value))
    return value


def _json_metrics(metrics: dict) -> dict:
    return _clean(metrics)


def _json_row(row: dict) -> dict:
    return _clean({**row, "b_star": LEGS[row["b_star"]], "b": LEGS[row["b"]]})


def _write_json(path: Path, data: dict) -> str:
    text = json.dumps(_clean(data), indent=1, ensure_ascii=False, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ===================================================================================== CLI
def _default_paths(args) -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[3]
    yaml_path = args.yaml or root / "02_params" / "rexome33.yaml"
    soil_path = args.soil_sets or root / "02_params" / "scm_soil_sets.json"
    return yaml_path, soil_path


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("constants", "judge"):
        p = sub.add_parser(name)
        p.add_argument("--harness", type=Path, required=True)
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--yaml", type=Path, default=None)
        p.add_argument("--soil-sets", type=Path, default=None)
        if name == "judge":
            p.add_argument("--chrono-batch", type=Path, required=True)
            p.add_argument("--identity", type=Path, required=True)
            p.add_argument("--constants", type=Path, default=None)
            p.add_argument("--p7-ref", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        geo = read_geometry(*_default_paths(args))
        if args.command == "constants":
            harness, refused = load_harness(args.harness)
            data = {**harness_constants(harness, geo), "harness_refused": refused,
                    "tool_sha256": sha256_file(Path(__file__)),
                    "harness_jsonl_sha256": sha256_file(args.harness)}
            summary = {"kappa_z_m_per_N": data["kappa_z_m_per_N"], "C_type": data["C_type"]}
            code = EXIT_OK
        else:
            if not args.chrono_batch.is_dir():
                raise InputError(f"chrono batch folder {args.chrono_batch} absent")
            identity = json.loads(args.identity.read_text(encoding="utf-8"))
            constants = (None if args.constants is None
                         else json.loads(args.constants.read_text(encoding="utf-8")))
            data = judge(args.chrono_batch, args.harness, identity, geo, constants, args.p7_ref)
            summary = {"bundle": data["bundle"], "blocked": data["blocked"],
                       "grades": {k: v["grade"] for k, v in data["grades"].items()}}
            code = EXIT_FOUND if data["bundle"] == "UNDETERMINED" or data["blocked"] else EXIT_OK
    except (InputError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "input_error", "error": f"{type(exc).__name__}: {exc}"[:500]}))
        return EXIT_INPUT
    except AssertionError as exc:
        print(json.dumps({"status": "internal_error", "error": str(exc)[:500]}))
        return EXIT_INTERNAL
    out_sha = _write_json(args.out, data)
    print(json.dumps({"status": "ok", "command": args.command, "out": str(args.out),
                      "out_sha256": out_sha, **summary}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
