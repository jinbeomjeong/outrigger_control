"""B1 creep basis, path 2 recount (control-expert), independent of path 1.

Implements the sealed rules ``06_analysis/02_control/b1/b1_creep_rules.md`` (sha256
``6b99702ce26d6da28fbfe6473b622c7e51419241916cbc101f795828f498774e``) from their text only:
row status (3.1), bundle status and empty-set rules (3.2), grades D-a .. D-h (3.3, 3.3.1 C-1 .. C-5,
15 Q-1 .. Q-8), threshold comparison forms (4.4), integer control periods (4.5), metrics M-1 .. M-12
(5, 7.5), predictors P-A / P-B / P-C / P-D / P-G (7.1, 7.2) and the harness constants (7.3).

Only numpy and the standard library (json, re, math, argparse, hashlib) are used. The YAML values the
rules name (pad shapes, pad positions, static leg loads) are read with a small block-YAML reader for
the three top-level sections that hold them; the soil set comes from ``02_params/scm_soil_sets.json``
and the crawler corners from the ``CRAWLER_XY_BOX_M`` line of ``c2.py`` (text, not imported).

Input key names: the rules (section 6) fix the R-C1 names and leave the other file keys to the
implementation and the prelaunch key list. Every file key this script reads is in ``DEFAULT_KEYMAP``;
``--keymap <json>`` overrides entries (data only, the code does not change). A key that is missing
in the data gives ``NA`` where the rules allow it, otherwise the row is ``MISSING``.

Exit codes: 0 = bundle COMPLETE or PARTIAL (grades written), 1 = bundle UNDETERMINED, 2 = input or
usage error, 3 = internal error. The last stdout line is a JSON summary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

RULES_SHA256 = "6b99702ce26d6da28fbfe6473b622c7e51419241916cbc101f795828f498774e"
TOOL_VERSION = "1.1"

LEGS = ("FL", "FR", "RL", "RR")
FRONT = ("FL", "FR")
T_S = 0.1                     # control period [s] (rules, conventions)
EPS_TH = 1e-9                 # threshold comparison tolerance [m] (4.4)
EPS_F = 1e-6                  # T-9 force tolerance [N]
EPS_R = 1e-12                 # T-7 (ii) dimensionless residual tolerance
S_GUARD = 0.6828              # stroke guard [m]
C_STAR = 0.05                 # clearance_target_m [m]
N_A = 0.2                     # P-D assumed exponent (7.2)
M_L_TOL = 5e-4                # T-14 [m]
# 0.4 table, 0.01 m row: f - 1 range per pad type
F_RANGE = {"rear": (1.0 - 0.013, 1.0 + 0.042), "front": (1.0 - 0.028, 1.0 + 0.050)}
VALID_NH_BAND = (0.95, 1.05)  # C-4 (i)
VALID_RSIGMA = 0.005          # C-4 (ii)
KAPPA_RATIO_FLAG = 1.5        # 7.3

# 2.1 table: id -> case, auger level, mass scale, duration [s], planned budget leg, role
CHRONO_ROWS = {
    "C1": ("B1_J2_B_bottom_Fs4_VB_fdown", "bottom", 1.0, 160.0, "FL", "core"),
    "C2": ("B1_J2_B_middle_Fs4_VB_fdown", "middle", 1.0, 160.0, "FL", "core"),
    "C3": ("B1_J2_B_top_Fs4_VB_fdown", "top", 1.0, 160.0, "FL", "aux"),
    "C4": ("B1_J2_B_bottom_Fs4_VB_diag", "bottom", 1.0, 160.0, "FR", "core"),
    "C5": ("B1_J2_B_top_Fs4_VB_fup", "top", 1.0, 160.0, "RL", "core"),
    "C6": ("B1_J2_B_bottom_Fs4_m1p1_VB_fdown", "bottom", 1.1, 180.0, "FL", "sens"),
}
CORE = ("C1", "C2", "C4", "C5")
R_SET = ("C1", "C2", "C3", "C4", "C5")
CTRL_TAG_VB = "final_C4G2_P3_LAS_K1"
CTRL_TAG_V0 = "final_C4G2_LAS_K1"
HULL_DLL_SHA = "cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15"
CANDIDATE_ORDER = ("P-A", "P-B", "P-D", "P-G", "P-C")

DEFAULT_KEYMAP: dict[str, Any] = {
    # batch layout
    "batch_json": "batch.json",
    "batch_cases": "cases",
    "batch_case_name": "case",
    "batch_case_rc": "rc",
    "row_dir": "{case}",
    "result_json": "result.json",
    "record_npz": "record/record.npz",
    "step_npz": "step_series.npz",
    "grid_npz": "record/b1_grid_record.npz",
    # result.json paths (dotted)
    "res_events": "events",
    "event_time": "t",
    "event_name": "name",
    "res_t_first_ready": "p3b.t_first_ready_s",
    "res_t_creep": "p3b.creep_stop.t_final_s",
    "res_t_departure": "p3b.t_departure_s",
    "res_weight": "p3b.weight_N",
    "res_t_end": "t_end_s",
    "res_tag": "controller_meta.controller_tag",
    "res_expect_ok": "c2_setup.expect_controller.ok",
    "res_threads": "num_threads_chrono",
    "res_hull_req": "hull_hook.requested",
    "res_hull_eff": "hull_hook.effective",
    "res_hull_sha": "hull_hook.dll_sha256",
    # record.npz (10 Hz)
    "rec_t": "t",
    "rec_stroke": "meas.stroke",
    # step_series.npz (1 ms)
    "step_t": "t",
    "step_sink": "pad_sinkage_geometric_m",
    "step_leg_contact_N": "pad_contact_force_N",
    "step_crawler_N": "crawler_load_N",
    # b1_grid_record.npz: R-C1 (names fixed by the rules) and R-G1 / R-G3 / R-G4
    "rc_n": "n",
    "g_n": "n_cycle",
    "g_computed": "computed",
    "rc_load": "load_read_N",
    "rc_att": "att_raw_rad",
    "rc_chat": "c_hat_m",
    "rc_chat_corner": "c_hat_corner_m",
    "rc_ctarget": "c_target_m",
    "g_n_contact": "n_contact",
    "g_hull_area": "contact_hull_area_m2",
    "g_hull_perim": "contact_hull_perimeter_m",
    "g_sink": "sinkage_geometric_m",
    "g_sigma": "sigma_sum_area_N",
    "res_grid_m": "b1_grid_record.static.grid_m",
    "res_grid_pads": "b1_grid_record.static.pads",
    "res_grid_pad_leg": "leg",
    "res_grid_pad_m": "grid_m",
    "imu_t": "imu_t_s",
    "imu_roll": "imu_raw_roll_rad",
    "imu_pitch": "imu_raw_pitch_rad",
    # optional M-12 inputs (rules 7.5); absent -> NA
    "m12_corner_plane": "c_corner_plane_m",
    "m12_settle_att": "settle_att_rad",
    "m12_loc_tP": "loc_t_P_s",
    "m12_loc_path": "loc_path",
    # corner order of c_hat_corner_m / CRAWLER corners (c2.py CRAWLER_CORNER_NAMES order)
    "corner_order": ["RR", "RL", "FR", "FL"],
    # event names
    "ev_loc": "crawler_liftoff_confirmed",
    "ev_revoke": "INFO_LOC_REVOKED",
    "ev_sgs": "FAULT_LIFT_STROKE_LIMIT:soil",
    "ev_warn_lift": "WARN_LIFT_STROKE_LIMITED",
    "ev_reject_prefix": "REJ_",
    "ev_fault_prefix": "FAULT_",
    "ev_stroke_end": "FAULT_STROKE_END",
    "ev_e3": "INFO_LOC_CLEARANCE_MARGIN:",
    "ev_r4": "INFO_LOC_FLAT_SOIL_MARGIN:",
    # harness jsonl line fields (dotted) and its npz keys (10 Hz)
    "h_group": "b1.group",
    "h_row": "b1.row",
    "h_variant": "b1.variant",
    "h_e": "b1.e",
    "h_shadow": "b1.shadow",
    "h_tag": "meta.controller_tag",
    "h_error": "error",
    "h_npz": "npz",
    "h_npz_sha": "npz_sha256",
    "h_commands_sha": "commands_sha256",
    "h_key": "d1.key",
    "h_events": "events",
    "h_t_first_ready": "t_first_ready_s",
    "h_level": "b1.level",
    "h_shadow_locs": "loc_shadow.locs",
    "hs_path": "path",
    "hs_t_P": "t_P_s",
    "hs_t_L": "t_L_s",
    "hs_c_min_tP_mm": "c_min_tP_mm",
    "hs_now_mm": "c_hat_tL_current_mm",
    "hs_shadow_mm": "c_hat_tL_shadow_mm",
    "hs_short": "short_window",
    "hn_t": "t",
    "hn_stroke": "stroke",
    "hn_sink": "pad_sinkage_m",
    "hn_load": "load_read_N",
    "hn_att": "att_raw_rad",
    "hn_chat": "c_hat_m",
    "hn_chat_corner": "c_hat_corner_m",
    "hn_ctarget": "c_target_m",
    # P7_REF lines
    "p7_candidate": "s2d.candidate",
    "p7_key": "d1.key",
    "p7_hash": "commands_sha256",
}


class InputError(Exception):
    """Usage or input error (exit 2)."""


# ----------------------------------------------------------------------------- small helpers

def jget(obj: Any, dotted: str, default: Any = None) -> Any:
    """``obj`` at the dotted path (list items by integer), ``default`` when absent."""
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.lstrip("-").isdigit() and -len(cur) <= int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return default
    return cur


def cyc(t: float) -> int:
    """Integer control period n = round(t / 0.1) (4.5)."""
    return int(round(float(t) / T_S))


def le(a: float, b: float, eps: float = EPS_TH) -> bool:
    """a <= b within the threshold tolerance (a - b <= eps)."""
    return a - b <= eps


def gt(a: float, b: float, eps: float = EPS_TH) -> bool:
    """a > b beyond the threshold tolerance (a - b > eps)."""
    return a - b > eps


def ge(a: float, b: float, eps: float = EPS_TH) -> bool:
    """a >= b within the tolerance (a - b >= -eps)."""
    return a - b >= -eps


def fnum(x: Any) -> float | None:
    """Finite float or None."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def nmax(values: list[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return max(vals) if vals else None


# ----------------------------------------------------------------------------- parameters

def _yaml_scalar(text: str) -> Any:
    text = text.strip()
    if not text:
        return None
    if text[0] in "\"'":
        return text[1:text.index(text[0], 1)]
    if text.startswith("["):
        inner = text[1:text.rindex("]")]
        return [_yaml_scalar(p) for p in _split_flow(inner)] if inner.strip() else []
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _split_flow(inner: str) -> list[str]:
    parts, depth, cur, quote = [], 0, "", ""
    for ch in inner:
        if quote:
            cur += ch
            if ch == quote:
                quote = ""
            continue
        if ch in "\"'":
            quote = ch
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
            continue
        cur += ch
    parts.append(cur)
    return [p for p in parts if p.strip()]


def _strip_comment(line: str) -> str:
    quote, out = "", []
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def parse_block_yaml(lines: list[str]) -> Any:
    """Minimal block YAML (mappings, '- ' sequences, flow lists, scalars) for the sections read here."""
    items = []
    for raw in lines:
        s = _strip_comment(raw)
        if s.strip():
            items.append((len(s) - len(s.lstrip(" ")), s.strip()))

    def parse(i: int, indent: int) -> tuple[Any, int]:
        if i < len(items) and items[i][1].startswith("- "):
            seq = []
            while i < len(items) and items[i][0] == indent and items[i][1].startswith("- "):
                seq.append(_yaml_scalar(items[i][1][2:]))
                i += 1
            return seq, i
        out: dict[str, Any] = {}
        while i < len(items) and items[i][0] == indent:
            key, _, rest = items[i][1].partition(":")
            key = key.strip().strip("\"'")
            i += 1
            if rest.strip():
                out[key] = _yaml_scalar(rest)
            elif i < len(items) and items[i][0] > indent:
                out[key], i = parse(i, items[i][0])
            elif i < len(items) and items[i][0] == indent and items[i][1].startswith("- "):
                out[key], i = parse(i, indent)
            else:
                out[key] = None
        return out, i

    value, _ = parse(0, items[0][0]) if items else ({}, 0)
    return value


def read_yaml_sections(path: Path, names: tuple[str, ...]) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    out: dict[str, Any] = {}
    for name in names:
        start = next((k for k, ln in enumerate(lines) if ln.startswith(name + ":")), None)
        if start is None:
            raise InputError(f"YAML section {name!r} missing in {path}")
        end = next((k for k in range(start + 1, len(lines))
                    if lines[k] and not lines[k][0].isspace() and not lines[k].startswith("#")), len(lines))
        out[name] = parse_block_yaml(lines[start + 1:end])
    return out


def load_params(repo: Path) -> dict[str, Any]:
    """Pad geometry, static loads, soil J2 and crawler corners from their sources (rules 0.4, 7.1, 7.2)."""
    y = read_yaml_sections(repo / "02_params" / "rexome33.yaml", ("superstructure", "legs", "pad_shapes"))
    pads = y["pad_shapes"]
    ptype = pads.get("default_type", "dwg_rear250")
    if ptype != "dwg_rear250":
        raise InputError(f"pad_shapes.default_type is {ptype!r}, the rules use dwg_rear250")
    shape = pads["types"]["dwg_rear250"]["legs"]
    pad = {}
    for leg in LEGS:
        area = float(shape[leg]["bottom_area_m2"])
        pad[leg] = {"A": area, "b_poly": float(shape[leg]["bekker_b_m"]),
                    "xy": [float(v) for v in y["legs"][leg]["pad_bottom_center_retracted_m"][0:2]],
                    "type": "front" if leg in FRONT else "rear"}
    static = {lvl: {leg: float(v[leg]) for leg in LEGS}
              for lvl, v in ((k, y["superstructure"]["auger_levels"][k]["static_leg_loads_N"])
                             for k in ("top", "middle", "bottom"))}
    soil = json.loads((repo / "02_params" / "scm_soil_sets.json").read_text(encoding="utf-8"))
    j2 = soil["sets"]["J2"]["chrono"]
    c2_text = (repo / "03_src" / "outrigger_sim" / "control" / "c2.py").read_text(encoding="utf-8")
    m = re.search(r"^CRAWLER_XY_BOX_M\s*=\s*\(\(([-\d.]+),\s*([-\d.]+)\),\s*\(([-\d.]+),\s*([-\d.]+)\)\)",
                  c2_text, re.M)
    if not m:
        raise InputError("CRAWLER_XY_BOX_M not found in c2.py")
    x0, x1, y0, y1 = (float(g) for g in m.groups())
    corners = {"RR": (x0, y0), "RL": (x0, y1), "FR": (x1, y0), "FL": (x1, y1)}
    return {"pad": pad, "static": static, "kc": float(j2["Kc"]), "kphi": float(j2["Kphi"]),
            "n": float(j2["n"]), "corners": corners}


# ----------------------------------------------------------------------------- formulas

def grid_factor(n_h: float, grid: float, hull_area: float, hull_perim: float, pad: dict, prm: dict) -> float | None:
    """f of rules 0.4: [N_h D^2 (kc/b_hull + kphi) / (A (kc/b_poly + kphi))]^(-1/n)."""
    if not n_h or not hull_perim or hull_area <= 0:
        return None
    b_hull = 2.0 * hull_area / hull_perim
    num = n_h * grid ** 2 * (prm["kc"] / b_hull + prm["kphi"])
    den = pad["A"] * (prm["kc"] / pad["b_poly"] + prm["kphi"])
    if num <= 0 or den <= 0:
        return None
    return (num / den) ** (-1.0 / prm["n"])


def grid_validity(n_h: float, grid: float, hull_area: float, hull_perim: float, sigma_sum: float, z: float,
                  pad: dict, prm: dict) -> tuple[bool, float | None, float | None]:
    """C-4 (i) N_h in [0.95, 1.05] A / D^2, (ii) r_sigma <= 0.005; returns (valid, N_h D^2/A, r_sigma)."""
    ratio = n_h * grid ** 2 / pad["A"]
    ok_i = ge(n_h, VALID_NH_BAND[0] * pad["A"] / grid ** 2) and le(n_h, VALID_NH_BAND[1] * pad["A"] / grid ** 2)
    r_sig = None
    ok_ii = False
    if sigma_sum and sigma_sum > 0 and hull_perim and hull_perim > 0 and hull_area > 0 and z is not None and z >= 0:
        b_hull = 2.0 * hull_area / hull_perim
        law = n_h * grid ** 2 * (prm["kc"] / b_hull + prm["kphi"]) * z ** prm["n"]
        r_sig = prm["n"] * abs(sigma_sum - law) / sigma_sum
        ok_ii = r_sig - VALID_RSIGMA <= EPS_R
    return ok_i and ok_ii, ratio, r_sig


def plane_fit_at(points_xy: list[tuple[float, float]], values: list[float],
                 query: list[tuple[float, float]]) -> list[float]:
    """Least-squares plane dz = a + b y - c x (support matrix form [1, y, -x]) evaluated at ``query``."""
    a = np.array([[1.0, y, -x] for x, y in points_xy])
    coef, *_ = np.linalg.lstsq(a, np.asarray(values, dtype=float), rcond=None)
    return [float(coef[0] + coef[1] * y - coef[2] * x) for x, y in query]


def pd_increment(c_type: float, f_pk: float, w_hat: float) -> float | None:
    """P-D sinkage increment C [(F_pk + max(W,0))^(1/n_a) - F_pk^(1/n_a)]."""
    if c_type is None or f_pk is None or w_hat is None or f_pk < 0:
        return None
    return c_type * ((f_pk + max(w_hat, 0.0)) ** (1.0 / N_A) - f_pk ** (1.0 / N_A))


# ----------------------------------------------------------------------------- run data (Chrono / harness)

class RunSeries:
    """10 Hz series of one run indexed by integer period, plus events and scalar times."""

    def __init__(self) -> None:
        self.n: np.ndarray = np.zeros(0, dtype=int)
        self.stroke: np.ndarray | None = None      # (k, 4) [m]
        self.sink10: np.ndarray | None = None      # (k, 4) harness sinkage [m]
        self.t_sink: np.ndarray | None = None      # 1 ms time [s] (Chrono)
        self.sink: np.ndarray | None = None        # (m, 4) 1 ms sinkage [m]
        self.leg_contact: np.ndarray | None = None
        self.crawler_N: np.ndarray | None = None
        self.rc: dict[str, np.ndarray] = {}        # R-C1 arrays indexed like rc_n
        self.rc_index: dict[int, int] = {}
        self.grid: dict[str, np.ndarray] = {}
        self.grid_index: dict[int, int] = {}
        self.grid_m: dict[str, float] | None = None   # per leg, from result.json static (no fallback)
        self.imu: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None
        self.m12: dict[str, Any] = {}
        self.events: list[tuple[float, str]] = []
        self.t_ready: float | None = None
        self.t_creep: float | None = None
        self.t_dep: float | None = None
        self.weight: float | None = None
        self.t_end: float | None = None
        self.index: dict[int, int] = {}

    def at(self, arr: np.ndarray | None, n: int | None) -> np.ndarray | None:
        if arr is None or n is None or n not in self.index:
            return None
        return arr[self.index[n]]

    def rc_at(self, key: str, n: int | None) -> np.ndarray | None:
        if key not in self.rc or n is None or n not in self.rc_index:
            return None
        return self.rc[key][self.rc_index[n]]

    def sink_at(self, n: int | None) -> np.ndarray | None:
        """z(tau) for tau = n * 0.1: 1 ms series with searchsorted(t, tau - 1e-9) (rules M-4), else 10 Hz."""
        if n is None:
            return None
        if self.sink is not None and self.t_sink is not None and len(self.t_sink):
            i = int(np.searchsorted(self.t_sink, n * T_S - 1e-9))
            i = min(i, len(self.t_sink) - 1)
            return self.sink[i]
        return self.at(self.sink10, n)


def _events(raw: Any, km: dict) -> list[tuple[float, str]]:
    out = []
    for e in raw or []:
        if isinstance(e, dict):
            t, name = e.get(km["event_time"]), e.get(km["event_name"])
        elif isinstance(e, (list, tuple)) and len(e) >= 2:
            t, name = e[0], e[1]
        else:
            continue
        if fnum(t) is not None and name is not None:
            out.append((float(t), str(name)))
    return sorted(out, key=lambda x: x[0])


def _npz(path: Path) -> dict[str, np.ndarray] | None:
    if not path.is_file():
        return None
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def _index(n_arr: np.ndarray) -> dict[int, int]:
    return {int(v): k for k, v in enumerate(np.asarray(n_arr).astype(int))}


def load_chrono_row(row_dir: Path, km: dict) -> tuple[RunSeries | None, dict, list[str]]:
    """Read one Chrono row; returns (series or None, result.json dict, missing file list)."""
    missing = [name for name in (km["result_json"], km["record_npz"], km["step_npz"])
               if not (row_dir / name).is_file()]
    if missing:
        return None, {}, missing
    res = json.loads((row_dir / km["result_json"]).read_text(encoding="utf-8"))
    rs = RunSeries()
    rec = _npz(row_dir / km["record_npz"]) or {}
    step = _npz(row_dir / km["step_npz"]) or {}
    if km["rec_t"] not in rec or km["rec_stroke"] not in rec:
        return None, res, [f"{km['record_npz']}:{km['rec_t']}/{km['rec_stroke']}"]
    rs.n = np.rint(np.asarray(rec[km["rec_t"]], dtype=float) / T_S).astype(int)
    rs.index = _index(rs.n)
    rs.stroke = np.asarray(rec[km["rec_stroke"]], dtype=float)
    if km["step_t"] in step and km["step_sink"] in step:
        rs.t_sink = np.asarray(step[km["step_t"]], dtype=float)
        rs.sink = np.asarray(step[km["step_sink"]], dtype=float)
    else:
        return None, res, [f"{km['step_npz']}:{km['step_sink']}"]
    rs.leg_contact = step.get(km["step_leg_contact_N"])
    rs.crawler_N = step.get(km["step_crawler_N"])
    grid = _npz(row_dir / km["grid_npz"])
    if grid is not None:
        _attach_grid(rs, grid, km)
    if grid is not None:
        rs.grid_m = grid_spacing(res, km)
    rs.events = _events(jget(res, km["res_events"]), km)
    rs.t_ready = fnum(jget(res, km["res_t_first_ready"]))
    rs.t_creep = fnum(jget(res, km["res_t_creep"]))
    rs.t_dep = fnum(jget(res, km["res_t_departure"]))
    rs.weight = fnum(jget(res, km["res_weight"]))
    rs.t_end = fnum(jget(res, km["res_t_end"]))
    if rs.t_end is None and len(rs.n):
        rs.t_end = float(rs.n.max()) * T_S
    return rs, res, []


def grid_spacing(res: dict, km: dict) -> dict[str, float]:
    """Pad SCM grid per leg: result.json static scalar, else static pads[i] per leg; none -> input error."""
    scalar = fnum(jget(res, km["res_grid_m"]))
    if scalar is not None:
        return {leg: scalar for leg in LEGS}
    pads = jget(res, km["res_grid_pads"])
    out: dict[str, float] = {}
    if isinstance(pads, list):
        for i, pad in enumerate(pads):
            if not isinstance(pad, dict):
                continue
            leg = pad.get(km["res_grid_pad_leg"]) or (LEGS[i] if i < len(LEGS) else None)
            val = fnum(pad.get(km["res_grid_pad_m"]))
            if leg in LEGS and val is not None:
                out[leg] = val
    if set(out) != set(LEGS):
        raise InputError(f"grid spacing missing in result.json ({km['res_grid_m']} null and "
                         f"{km['res_grid_pads']} incomplete: {sorted(out)})")
    return out


def _attach_grid(rs: RunSeries, grid: dict[str, np.ndarray], km: dict) -> None:
    if km["rc_n"] in grid:
        rs.rc_index = _index(grid[km["rc_n"]])              # R-C1: every control period, no filter
    if km["g_n"] in grid:
        g_arr = np.asarray(grid[km["g_n"]]).astype(int)
        keep = np.ones(len(g_arr), dtype=bool)
        if km.get("g_computed") and km["g_computed"] in grid:
            keep = np.asarray(grid[km["g_computed"]]).astype(bool)
        rs.grid_index = {int(v): k for k, v in enumerate(g_arr) if keep[k]}
        for k in ("rc_load", "rc_att", "rc_chat", "rc_chat_corner", "rc_ctarget"):
            if km[k] in grid:
                rs.rc[k] = np.asarray(grid[km[k]], dtype=float)
        for k in ("g_n_contact", "g_hull_area", "g_hull_perim", "g_sink", "g_sigma"):
            if km[k] in grid:
                rs.grid[k] = np.asarray(grid[km[k]], dtype=float)
    if all(km[k] in grid for k in ("imu_t", "imu_roll", "imu_pitch")):
        rs.imu = (np.asarray(grid[km["imu_t"]], dtype=float), np.asarray(grid[km["imu_roll"]], dtype=float),
                  np.asarray(grid[km["imu_pitch"]], dtype=float))
    for k in ("m12_corner_plane", "m12_settle_att", "m12_loc_tP", "m12_loc_path"):
        if km[k] in grid:
            rs.m12[k] = grid[km[k]]


def load_harness_line(line: dict, base: Path, km: dict) -> tuple[RunSeries | None, str | None]:
    """Harness run series from its jsonl line and npz; returns (series, invalid reason)."""
    rel = jget(line, km["h_npz"])
    if not rel:
        return None, "no npz"
    path = (base / rel) if not Path(rel).is_absolute() else Path(rel)
    if not path.is_file():
        return None, "npz missing"
    want = jget(line, km["h_npz_sha"])
    if want is None or sha256_file(path) != want:
        return None, "npz sha mismatch"
    z = _npz(path) or {}
    rs = RunSeries()
    if km["hn_t"] not in z or km["hn_stroke"] not in z:
        return None, "npz keys"
    rs.n = np.rint(np.asarray(z[km["hn_t"]], dtype=float) / T_S).astype(int)
    rs.index = _index(rs.n)
    rs.rc_index = rs.index
    rs.stroke = np.asarray(z[km["hn_stroke"]], dtype=float)
    if km["hn_sink"] in z:
        rs.sink10 = np.asarray(z[km["hn_sink"]], dtype=float)
    for dst, src in (("rc_load", "hn_load"), ("rc_att", "hn_att"), ("rc_chat", "hn_chat"),
                     ("rc_chat_corner", "hn_chat_corner"), ("rc_ctarget", "hn_ctarget")):
        if km[src] in z:
            rs.rc[dst] = np.asarray(z[km[src]], dtype=float)
    rs.events = _events(jget(line, km["h_events"]), km)
    rs.t_ready = fnum(jget(line, km["h_t_first_ready"]))
    rs.t_end = float(rs.n.max()) * T_S if len(rs.n) else None
    return rs, None


# ----------------------------------------------------------------------------- per-run metrics

def _names(rs: RunSeries, pred) -> list[tuple[float, str]]:
    return [(t, nm) for t, nm in rs.events if pred(nm)]


def run_metrics(rs: RunSeries, km: dict, prm: dict, level: str, budget_leg: str | None,
                fixed_leg: str | None = None, is_chrono: bool = True) -> dict[str, Any]:
    """M-1, M-2, M-4, M-5, M-8 and the LOC-period inputs of one run (Chrono or harness)."""
    out: dict[str, Any] = {}
    locs = _names(rs, lambda nm: nm.startswith(km["ev_loc"]))
    out["n_loc"] = len(locs)
    out["n_L1"] = cyc(locs[0][0]) if locs else None
    out["n_L"] = cyc(locs[-1][0]) if locs else None
    out["loc_revoked"] = len(_names(rs, lambda nm: nm.startswith(km["ev_revoke"])))
    sgs = _names(rs, lambda nm: nm.startswith(km["ev_sgs"]))
    out["n_sgs"] = cyc(sgs[0][0]) if sgs else None
    out["sgs"] = bool(sgs)
    warn = _names(rs, lambda nm: nm.startswith(km["ev_warn_lift"]))
    out["n_warn_lift"] = cyc(warn[0][0]) if warn else None
    out["n_R"] = cyc(rs.t_ready) if rs.t_ready is not None else None
    out["n_creep"] = cyc(rs.t_creep) if rs.t_creep is not None else None
    out["n_end"] = int(rs.n.max()) if len(rs.n) else None
    out["fault_stroke_end"] = bool(_names(rs, lambda nm: nm.startswith(km["ev_stroke_end"])))
    stroke = rs.stroke
    smax_leg = stroke.max(axis=0)
    gmax = float(smax_leg.max())
    rows = np.where(stroke.max(axis=1) >= gmax - EPS_TH)[0]
    out["n_max"] = int(rs.n[rows].min())
    nmax_leg = {}
    for k, leg in enumerate(LEGS):
        idx = np.where(stroke[:, k] >= smax_leg[k] - EPS_TH)[0]
        nmax_leg[leg] = int(rs.n[idx].min())
    out["n_max_leg"] = nmax_leg
    out["s_max"] = {leg: float(smax_leg[k]) for k, leg in enumerate(LEGS)}
    b_star = fixed_leg or LEGS[int(np.argmax(smax_leg))]
    out["b_star"] = b_star
    out["b_planned"] = budget_leg
    out["g"] = S_GUARD - float(smax_leg[LEGS.index(b_star)]) if fixed_leg is None else S_GUARD - gmax
    n_L, n_R, n_mx = out["n_L"], out["n_R"], out["n_max"]
    n_e = max(n_mx, n_R) if n_R is not None else n_mx
    out["n_e"] = n_e
    out["n_e_leg"] = {leg: (max(nmax_leg[leg], n_R) if n_R is not None else nmax_leg[leg]) for leg in LEGS}

    def svec(n):
        v = rs.at(stroke, n)
        return None if v is None else {leg: float(v[k]) for k, leg in enumerate(LEGS)}

    out["s_L"], out["s_R"] = svec(n_L), svec(n_R)
    z = {name: rs.sink_at(n) for name, n in (("L", n_L), ("R", n_R), ("max", n_mx), ("e", n_e),
                                            ("end", out["n_end"]))}
    out["z"] = {k: (None if v is None else {leg: float(v[i]) for i, leg in enumerate(LEGS)}) for k, v in z.items()}

    def dz(a, b):
        za, zb = out["z"][a], out["z"][b]
        return None if za is None or zb is None else {leg: zb[leg] - za[leg] for leg in LEGS}

    out["dz_post"] = dz("L", "e")                     # C-1
    out["dz_L_max"] = dz("L", "max")
    out["dz_max_R"] = dz("max", "R")
    out["dz_L_R"] = dz("L", "R")
    out["dz_R_end"] = dz("R", "end")
    zl = out["z"]["L"]
    out["dz_post_leg"] = None
    if zl is not None:
        dl = {}
        for leg in LEGS:
            ze = rs.sink_at(out["n_e_leg"][leg])
            dl[leg] = None if ze is None else float(ze[LEGS.index(leg)]) - zl[leg]
        out["dz_post_leg"] = dl
    out["dos"] = None
    if out["s_R"] is not None:
        out["dos"] = {leg: out["s_max"][leg] - out["s_R"][leg] for leg in LEGS}
    out["t_max_minus_L"] = None if n_L is None else (n_mx - n_L) * T_S
    # M-4 records: max sinkage rate after t_L (1.0 s backward difference), secant t_L -> t_R
    out["max_sink_rate"] = None
    if rs.sink is not None and n_L is not None:
        t, s = rs.t_sink, rs.sink
        k0 = int(np.searchsorted(t, n_L * T_S - 1e-9))
        kb = np.searchsorted(t, t - 1.0 - 1e-9)
        sel = np.arange(len(t)) >= k0
        sel &= (t - t[kb]) > 0.5
        if sel.any():
            rate = (s[sel] - s[kb[sel]]) / (t[sel] - t[kb[sel]])[:, None]
            out["max_sink_rate"] = {leg: float(rate[:, k].max()) for k, leg in enumerate(LEGS)}
    # LOC-period inputs
    out["level"] = level
    out["loc_inputs"] = loc_inputs(rs, km, prm, level, n_L)
    out["secant"] = None
    if out["dz_L_R"] is not None:
        fl, fr = rs.rc_at("rc_load", n_L), rs.rc_at("rc_load", n_R)
        if fl is not None and fr is not None:
            out["secant"] = {leg: (out["dz_L_R"][leg] / (fr[k] - fl[k]) if abs(fr[k] - fl[k]) > 0 else None)
                             for k, leg in enumerate(LEGS)}
    # M-8 margin events up to n_L
    out["m_L"], out["m_L_src"] = margin_at(rs, km, n_L)
    out["r4_events"] = len(_names(rs, lambda nm: nm.startswith(km["ev_r4"])))
    out["e3_events"] = [nm for _, nm in _names(rs, lambda nm: nm.startswith(km["ev_e3"]))]
    out["t14_ok"] = None
    ct = rs.rc_at("rc_ctarget", n_L)
    if ct is not None and out["m_L"] is not None:
        out["t14_ok"] = abs(float(np.asarray(ct).ravel()[0]) - (C_STAR + out["m_L"])) <= M_L_TOL
    out["ready"] = rs.t_ready is not None
    if is_chrono:
        out["safety"] = safety(rs, out, km)
    return out


def margin_at(rs: RunSeries, km: dict, n_L: int | None) -> tuple[float | None, str | None]:
    """m_L = c*_run(t_L) - c* from the last E3c10 / R4c30 event up to the last LOC period (7.2)."""
    if n_L is None:
        return None, None
    last = None
    for t, nm in rs.events:
        if cyc(t) > n_L:
            break
        for key, src in ((km["ev_e3"], "E3c10"), (km["ev_r4"], "R4c30")):
            if nm.startswith(key):
                mm = fnum(nm[len(key):].split(":")[0])
                if mm is not None:
                    last = (mm / 1000.0, src)
    if last is None:
        return 0.0, "none"
    return last[0] - C_STAR, last[1]


def loc_inputs(rs: RunSeries, km: dict, prm: dict, level: str, n_L: int | None) -> dict[str, Any] | None:
    """Inputs of the predictors at the last LOC period (7.1, 7.2)."""
    if n_L is None:
        return None
    s = rs.at(rs.stroke, n_L)
    att = rs.rc_at("rc_att", n_L)
    chat = rs.rc_at("rc_chat", n_L)
    corner = rs.rc_at("rc_chat_corner", n_L)
    load = rs.rc_at("rc_load", n_L)
    if s is None or att is None or chat is None or load is None:
        return None
    phi, theta = float(att[0]), float(att[1])
    pk = None
    if "rc_load" in rs.rc:
        ks = [rs.rc_index[n] for n in rs.rc_index if n <= n_L]
        if ks:
            pk = rs.rc["rc_load"][ks].max(axis=0)
    static = prm["static"][level]
    w_hat = {leg: static[leg] - float(load[k]) for k, leg in enumerate(LEGS)}       # Q-1 (a)
    geo = {leg: prm["pad"][leg]["xy"][0] * theta - prm["pad"][leg]["xy"][1] * phi for leg in LEGS}
    rho = {c: prm["corners"][c][0] * theta - prm["corners"][c][1] * phi for c in km["corner_order"]}
    return {"s": {leg: float(s[k]) for k, leg in enumerate(LEGS)}, "phi": phi, "theta": theta,
            "c_hat": float(np.asarray(chat).ravel()[0]),
            "c_hat_corner": (None if corner is None else
                             {c: float(corner[k]) for k, c in enumerate(km["corner_order"])}),
            "W_hat": w_hat, "F_pk": (None if pk is None else {leg: float(pk[k]) for k, leg in enumerate(LEGS)}),
            "ds_geo": geo, "rho": rho}


def safety(rs: RunSeries, m: dict, km: dict) -> dict[str, Any]:
    """Safety records (3.3): FAULT_STROKE_END, T-8 leg lift-off, T-9 crawler re-touch."""
    out = {"fault_stroke_end": m["fault_stroke_end"], "leg_liftoff": None, "crawler_retouch": None}
    if rs.leg_contact is not None and rs.t_sink is not None and m["n_L1"] is not None:
        t = rs.t_sink
        sel = t >= m["n_L1"] * T_S - 1e-9
        legs_hit = []
        for k, leg in enumerate(LEGS):
            zero = (np.asarray(rs.leg_contact)[:, k] <= 0.0) & sel
            run, best = 0, 0
            for v in zero:
                run = run + 1 if v else 0
                best = max(best, run)
            if best >= 100:
                legs_hit.append(leg)
        out["leg_liftoff"] = legs_hit
    if rs.crawler_N is not None and rs.t_sink is not None and rs.t_dep is not None and rs.weight is not None:
        sel = rs.t_sink >= rs.t_dep
        hit = np.asarray(rs.crawler_N)[sel] - 0.01 * rs.weight >= -EPS_F
        out["crawler_retouch"] = bool(hit.any())
    out["note"] = bool(out["fault_stroke_end"] or out["leg_liftoff"] or out["crawler_retouch"])
    return out


def grid_metrics(rs: RunSeries, m: dict, prm: dict) -> dict[str, Any]:
    """M-11 at t_L, t_R, t_max, t_e, t_end for every leg (same-period records only, C-4)."""
    out: dict[str, Any] = {}
    for name, n in (("L", m["n_L"]), ("R", m["n_R"]), ("max", m["n_max"]), ("e", m["n_e"]), ("end", m["n_end"])):
        per = {}
        for k, leg in enumerate(LEGS):
            rec = None
            if n is not None and n in rs.grid_index and all(key in rs.grid for key in
                                                         ("g_n_contact", "g_hull_area", "g_hull_perim", "g_sink",
                                                          "g_sigma")):
                j = rs.grid_index[n]
                nh = float(rs.grid["g_n_contact"][j, k])
                ha, hp = float(rs.grid["g_hull_area"][j, k]), float(rs.grid["g_hull_perim"][j, k])
                zg, sg = float(rs.grid["g_sink"][j, k]), float(rs.grid["g_sigma"][j, k])
                gsp = rs.grid_m[leg]
                valid, ratio, r_sig = grid_validity(nh, gsp, ha, hp, sg, zg, prm["pad"][leg], prm)
                f = grid_factor(nh, gsp, ha, hp, prm["pad"][leg], prm)
                z = m["z"][name][leg] if m["z"].get(name) is not None else None
                rec = {"N_h": nh, "b_hull": (2 * ha / hp if hp else None), "f": f, "valid": bool(valid and f),
                       "NhD2_over_A": ratio, "r_sigma": r_sig}
                if f and z is not None:
                    rec.update({"z_over_f": z / f, "delta_grid": z * (1 - 1 / f),
                                "dz_1n": z * gsp ** 2 / (prm["n"] * prm["pad"][leg]["A"])})
            per[leg] = rec
        out[name] = per
    return out


def valid_f(gm: dict, name: str, leg: str) -> float | None:
    rec = gm.get(name, {}).get(leg)
    return rec["f"] if rec and rec.get("valid") else None


# ----------------------------------------------------------------------------- predictors

def predictors(li: dict | None, m: dict, prm: dict, km: dict, consts: dict, leg: str) -> dict[str, Any]:
    """s_hat for P-A, P-B, P-C, P-D, P-G at leg ``leg`` and the errors e = s_max - s_hat (7.2)."""
    out: dict[str, Any] = {q: None for q in CANDIDATE_ORDER}
    rec: dict[str, Any] = {}
    if li is None or m["m_L"] is None:
        return {"s_hat": out, "e": dict(out), "rec": rec}
    gap = max(C_STAR + m["m_L"] - li["c_hat"], 0.0)
    pa = li["s"][leg] + li["ds_geo"][leg] + gap
    out["P-A"] = pa
    ptype = prm["pad"][leg]["type"]
    kappa = consts.get("kappa", {}).get(ptype)
    dallow = consts.get("delta_allow")
    ctype = consts.get("C_type", {}).get(ptype)
    w = li["W_hat"][leg]
    if kappa is not None:
        out["P-B"] = pa + kappa * max(w, 0.0)
        if dallow is not None:
            out["P-C"] = out["P-B"] + dallow
    dzh = None
    if li["F_pk"] is not None and ctype is not None:
        dzh = {lg: pd_increment(consts["C_type"].get(prm["pad"][lg]["type"]), li["F_pk"][lg], li["W_hat"][lg])
               for lg in LEGS}
        if dzh[leg] is not None:
            out["P-D"] = pa + dzh[leg]
    if dzh is not None and all(v is not None for v in dzh.values()) and li["c_hat_corner"] is not None:
        order = km["corner_order"]
        zk = plane_fit_at([tuple(prm["pad"][lg]["xy"]) for lg in LEGS], [dzh[lg] for lg in LEGS],
                          [prm["corners"][c] for c in order])
        terms = {c: li["c_hat_corner"][c] + li["rho"][c] + zk[i] for i, c in enumerate(order)}
        k_star = min(terms, key=lambda c: (terms[c], order.index(c)))
        out["P-G"] = li["s"][leg] + li["ds_geo"][leg] + max(C_STAR + m["m_L"] - terms[k_star], 0.0) + dzh[leg]
        rec.update({"k_star": k_star, "rho_k_star": li["rho"][k_star], "Zhat_k_star": zk[order.index(k_star)]})
    e = {q: (None if out[q] is None else m["s_max"][leg] - out[q]) for q in CANDIDATE_ORDER}
    return {"s_hat": out, "e": e, "rec": rec}


def h_records(rs: RunSeries, m: dict, prm: dict, km: dict) -> dict[str, Any]:
    """P-A limit records: observed h at t_max and t_e, Z_k* from true sinkage, epsilon (7.2)."""
    li = m["loc_inputs"]
    out: dict[str, Any] = {"h": None, "Z_k_star": None, "eps": None}
    if li is None:
        return out
    hs = {}
    for name, n in (("max", m["n_max"]), ("e", m["n_e"])):
        s = rs.at(rs.stroke, n)
        z, zl = rs.sink_at(n), rs.sink_at(m["n_L"])
        if s is None or z is None or zl is None:
            continue
        vals = [float(s[k]) - li["s"][leg] - li["ds_geo"][leg] - (float(z[k]) - float(zl[k]))
                for k, leg in enumerate(LEGS)]
        hs[name] = {"legs": dict(zip(LEGS, vals)), "mean": float(np.mean(vals)), "spread": float(np.ptp(vals))}
        if name == "e":
            order = km["corner_order"]
            zk = plane_fit_at([tuple(prm["pad"][lg]["xy"]) for lg in LEGS],
                              [float(z[k]) - float(zl[k]) for k in range(4)], [prm["corners"][c] for c in order])
            out["Z_k"] = dict(zip(order, zk))
    out["h"] = hs
    chat_r = rs.rc_at("rc_chat", m["n_R"])
    if chat_r is not None and m["m_L"] is not None:
        out["eps"] = float(np.asarray(chat_r).ravel()[0]) - (C_STAR + m["m_L"])
    return out


def m12_records(rs: RunSeries, m: dict, prm: dict, km: dict) -> list[dict] | None:
    """M-12 per LOC: current c_hat(t_L) and plan A shadow (centred raw tilt mean) from R-G4 (7.5, Q-7 (a))."""
    need = ("m12_corner_plane", "m12_settle_att", "m12_loc_tP", "m12_loc_path")
    if rs.imu is None or any(k not in rs.m12 for k in need):
        return None
    locs = _names(rs, lambda nm: nm.startswith(km["ev_loc"]))
    tps = np.asarray(rs.m12["m12_loc_tP"], dtype=float).ravel()
    paths = [str(p) for p in np.asarray(rs.m12["m12_loc_path"]).ravel()]
    settle = np.asarray(rs.m12["m12_settle_att"], dtype=float).ravel()
    plane = rs.m12["m12_corner_plane"]
    order = km["corner_order"]
    xy = [prm["corners"][c] for c in order]
    t_imu, roll, pitch = rs.imu
    out = []
    for j, (t_l, _) in enumerate(locs):
        if j >= len(tps):
            break
        t_p, path = float(tps[j]), paths[j]
        n_p, n_l = cyc(t_p), cyc(t_l)
        cp, cl = (rs.at(plane, n_p), rs.at(plane, n_l))
        rec = {"loc": j, "path": path, "n_P": n_p, "n_L": n_l, "c_hat_now": None, "c_hat_A": None, "d": None}
        cur = rs.rc_at("rc_chat", n_l)
        if cur is not None:
            rec["c_hat_now"] = float(np.asarray(cur).ravel()[0])
        if cp is None or cl is None:
            out.append(rec)
            continue
        rec["c_min_tP"] = float(np.min(cp))
        w = min(0.5, t_l - t_p)
        sel = (t_imu >= t_p - w - 1e-6) & (t_imu <= t_p + w + 1e-6)
        if path == "3":
            b = [0.0] * 4
        elif sel.any():
            dphi = float(np.mean(roll[sel])) - settle[0]
            dth = float(np.mean(pitch[sel])) - settle[1]
            rho = [y * dphi - x * dth for x, y in xy]
            rel = [r - min(rho) for r in rho]
            if path == "1":
                b = [max(float(cp[k]) - rel[k], 0.0) for k in range(4)]
            elif path == "2":
                b = [float(cp[k]) - rel[k] + 0.005 for k in range(4)]
            else:
                b = None
        else:
            b = None
        if b is not None:
            rec["c_hat_A"] = min(float(cl[k]) - b[k] for k in range(4))
            if rec["c_hat_now"] is not None:
                rec["d"] = rec["c_hat_now"] - rec["c_hat_A"]
        rec["short_window"] = w < 0.3
        out.append(rec)
    return out


# ----------------------------------------------------------------------------- harness

def harness_lines(path: Path | None, km: dict) -> list[dict]:
    if path is None:
        return []
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            out.append(json.loads(raw))
    return out


def harness_shadow_locs(line: dict, km: dict) -> list[dict] | None:
    """M-12 harness records from the shadow record of the line (7.5): per LOC path, periods, c_hat now / plan A."""
    locs = jget(line, km["h_shadow_locs"])
    if not isinstance(locs, list):
        return None
    out = []
    for j, loc in enumerate(locs):
        if not isinstance(loc, dict):
            continue
        now_mm, a_mm = fnum(loc.get(km["hs_now_mm"])), fnum(loc.get(km["hs_shadow_mm"]))
        t_p, t_l = fnum(loc.get(km["hs_t_P"])), fnum(loc.get(km["hs_t_L"]))
        out.append({"loc": j, "path": (None if loc.get(km["hs_path"]) is None else str(loc.get(km["hs_path"]))),
                    "n_P": (None if t_p is None else cyc(t_p)), "n_L": (None if t_l is None else cyc(t_l)),
                    "c_min_tP": (None if fnum(loc.get(km["hs_c_min_tP_mm"])) is None
                                 else fnum(loc.get(km["hs_c_min_tP_mm"])) / 1000.0),
                    "c_hat_now": (None if now_mm is None else now_mm / 1000.0),
                    "c_hat_A": (None if a_mm is None else a_mm / 1000.0),
                    "d": (None if now_mm is None or a_mm is None else (now_mm - a_mm) / 1000.0),
                    "short_window": loc.get(km["hs_short"])})
    return out


def harness_valid(line: dict, km: dict, base: Path) -> tuple[RunSeries | None, str | None]:
    """Q-6 (a): no error, tag equals 1.1, npz sha equals the line value (no end-time condition)."""
    if jget(line, km["h_error"]):
        return None, "error"
    variant = jget(line, km["h_variant"])
    want = CTRL_TAG_VB if variant == "VB" else CTRL_TAG_V0 if variant == "V0" else None
    if want is None or jget(line, km["h_tag"]) != want:
        return None, "tag"
    return load_harness_line(line, base, km)


def pick(lines: list[dict], km: dict, group: str, row: str, variant: str | None, e: float | None,
         shadow: bool | None = None) -> list[dict]:
    out = []
    for ln in lines:
        if jget(ln, km["h_group"]) != group or jget(ln, km["h_row"]) != row:
            continue
        if variant is not None and jget(ln, km["h_variant"]) != variant:
            continue
        if e is not None and (fnum(jget(ln, km["h_e"])) is None or abs(float(jget(ln, km["h_e"])) - e) > 1e-12):
            continue
        if shadow is not None and bool(jget(ln, km["h_shadow"])) != shadow:
            continue
        out.append(ln)
    return out


def harness_constants(hp: list[tuple[dict, RunSeries, dict]], prm: dict) -> dict[str, Any]:
    """7.3 constants from H-P 20 runs (per-leg windows, C-2)."""
    kappa: dict[str, list[float]] = {"front": [], "rear": []}
    ctype: dict[str, list[float]] = {"front": [], "rear": []}
    excluded = {"front": 0, "rear": 0}
    per_run: dict[str, list[float]] = {"front": [], "rear": []}
    dos = []
    used = []
    for line, rs, m in hp:
        li = m["loc_inputs"]
        if li is None or m["dz_post_leg"] is None:
            continue
        used.append(line.get("_id"))
        run_k: dict[str, list[float]] = {"front": [], "rear": []}
        for leg in LEGS:
            dz = m["dz_post_leg"][leg]
            if dz is None:
                continue
            t = prm["pad"][leg]["type"]
            k = dz / max(li["W_hat"][leg], 1.0)
            kappa[t].append(k)
            run_k[t].append(k)
            if li["F_pk"] is not None:
                den = (li["F_pk"][leg] + max(li["W_hat"][leg], 0.0)) ** (1 / N_A) - li["F_pk"][leg] ** (1 / N_A)
                if den > 0:
                    ctype[t].append(dz / den)
                else:
                    excluded[t] += 1
        for t in ("front", "rear"):
            if run_k[t]:
                per_run[t].append(max(run_k[t]))
        if m["dos"] is not None:
            dos.append(m["dos"][m["b_star"]])
    ratio = {t: (max(v) / min(v) if v and min(v) > 0 else None) for t, v in per_run.items()}
    return {"kappa": {t: (max(v) if v else None) for t, v in kappa.items()},
            "C_type": {t: (max(v) if v else None) for t, v in ctype.items()},
            "C_type_excluded": excluded, "delta_allow": (max(dos) if dos else None),
            "kappa_ratio": ratio, "kappa_nonlinear": {t: (r is not None and r > KAPPA_RATIO_FLAG)
                                                      for t, r in ratio.items()},
            "runs_used": used}


# ----------------------------------------------------------------------------- grades

def classify_dc(lo: float, hi: float) -> str:
    """D-c sign of a Delta^corr interval [lo, hi] (T-3)."""
    if gt(lo, 0.003):
        return "+"
    if gt(-hi, 0.003):
        return "-"
    if le(abs(lo), 0.003) and le(abs(hi), 0.003):
        return "0"
    return "?"


def grade_all(rows: dict[str, dict], hrs: dict, consts: dict, prm: dict, km: dict, bundle: str,
              p7: dict | None) -> dict[str, Any]:
    g: dict[str, Any] = {}
    valid = [r for r in R_SET if rows[r]["status"] == "VALID"]
    partial_c3 = rows["C3"]["status"] != "VALID"
    tag_r = ["PARTIAL"] if (bundle == "PARTIAL" and partial_c3) else []
    # D-a
    zc, zcorr, zhn, corr_na = [], [], [], []
    rec_da = {}
    for r in valid:
        m = rows[r]["m"]
        b = m["b_star"]
        if m["dz_post"] is None:
            continue
        zc.append(m["dz_post"][b])
        fl, fe = valid_f(rows[r]["gm"], "L", b), valid_f(rows[r]["gm"], "e", b)
        if fl and fe:
            zcorr.append(m["z"]["e"][b] / fe - m["z"]["L"][b] / fl)
            rec_da[r] = {"grid_change": m["z"]["e"][b] * (fe - fl)}
        else:
            corr_na.append(r)
        for hm in hrs.get(("H-P", r, "e0"), []):
            if hm["dz_post"] is not None:
                zhn.append(hm["dz_post"][b])                      # Q-2 (a): Chrono b*
    z_ch, z_hn = nmax(zc), nmax(zhn)
    if z_ch is None or z_hn is None:
        g["D-a"] = {"grade": "NA", "rows": valid}
    else:
        raw = "ZA-1" if le(z_ch - z_hn, 0.003) else "ZA-2"
        z_corr = nmax(zcorr)
        corr = None if z_corr is None else ("ZA-1" if le(z_corr - z_hn, 0.003) else "ZA-2")
        final = "ZA-2" if "ZA-2" in (raw, corr) else "ZA-1"
        flags = list(tag_r)
        if corr is not None and corr != raw:
            flags.append("grid phase dependent")
        if corr is None:
            flags.append("no grid record")
        if raw == "ZA-2" and corr == "ZA-1":
            flags.append("correction includes grid share")
        g["D-a"] = {"grade": final, "raw": raw, "corr": corr, "Z_ch": z_ch, "Z_corr": z_corr, "Z_hn": z_hn,
                    "correction_m": (z_ch - z_hn) if final == "ZA-2" else None, "corr_na_rows": corr_na,
                    "rows": valid, "n_rows": len(valid), "flags": flags, "records": rec_da}
    # D-b
    o_vals, na_rows = [], []
    for r in valid:
        m = rows[r]["m"]
        b = m["b_star"]
        hv = [hm["dos"][b] for hm in hrs.get(("H-P", r, "VB-e0"), []) if hm["dos"] is not None]
        cv = m["dos"][b] if m["dos"] is not None else None
        vals = [v for v in [cv] + hv if v is not None]
        if cv is None:
            na_rows.append(r)
        if vals:
            o_vals.append(max(vals))
    o = nmax(o_vals)
    g["D-b"] = {"grade": "NA" if o is None else ("OS-MAX" if gt(o, 0.005) else "OS-FINAL"), "O": o,
                "na_rows": na_rows, "rows": valid, "flags": list(tag_r)}
    # D-c
    signs_corr, signs_raw, detail = {}, {}, {}
    for r in valid:
        m = rows[r]["m"]
        b = m["b_star"]
        hv = hrs.get(("H-P", r, "VB-e0"), [])
        if not hv:
            continue
        delta = m["s_max"][b] - hv[0]["s_max"][b]
        zt = m["z"]["max"][b] if m["z"]["max"] is not None else None
        f = valid_f(rows[r]["gm"], "max", b)
        signs_raw[r] = classify_dc(delta, delta)
        if f and zt is not None:
            dg = zt * (1 - 1 / f)
            lo = hi = delta - dg
            sub = False
        elif zt is not None:
            fmin, fmax = F_RANGE[prm["pad"][b]["type"]]
            d1, d2 = zt * (1 - 1 / fmin), zt * (1 - 1 / fmax)
            lo, hi = delta - max(d1, d2), delta - min(d1, d2)
            sub = True
        else:
            continue
        signs_corr[r] = classify_dc(lo, hi)
        gsp = rows[r]["grid_m"][b] if rows[r].get("grid_m") else None
        dz1n = None if (zt is None or gsp is None) else zt * gsp ** 2 / (prm["n"] * prm["pad"][b]["A"])
        detail[r] = {"delta_raw": delta, "corr_lo": lo, "corr_hi": hi, "substitute": sub, "dz_1n": dz1n,
                     "node_step_level": (dz1n is not None and not sub and abs(lo) <= dz1n)}

    def dc_grade(signs: dict) -> str:
        counted = [s for s in signs.values() if s != "?"]
        if not counted:
            return "NA"
        if "+" in counted:
            return "H-OPT"
        if "-" in counted:
            return "H-CONS"
        return "H-OK"

    gc, gr = dc_grade(signs_corr), dc_grade(signs_raw)
    flags = list(tag_r)
    if gc != gr:
        flags.append("grid phase dependent")
    und = [r for r, s in signs_corr.items() if s == "?"]
    if und:
        flags.append("grid phase dependent (sign undetermined): " + ",".join(und))
    g["D-c"] = {"grade": gc, "raw_grade": gr, "signs": signs_corr, "raw_signs": signs_raw, "detail": detail,
                "rows": sorted(signs_corr), "flags": flags}
    # D-d
    excluded = [r for r in valid if rows[r]["m"]["t14_ok"] is False]
    use = [r for r in valid if r not in excluded]
    e_rows = {r: rows[r]["pred"]["e"] for r in use}
    eq, lower = {}, {}
    for q in CANDIDATE_ORDER:
        vals = [e_rows[r][q] for r in use]
        eq[q] = None if (not vals or any(v is None for v in vals)) else max(abs(v) for v in vals)
        lower[q] = any(rows[r]["m"]["sgs"] and e_rows[r][q] is not None and e_rows[r][q] >= 0 for r in use)
    cand = [q for q in CANDIDATE_ORDER if eq[q] is not None]
    if not cand:
        dd = {"grade": "NA"}
    else:
        best = min(eq[q] for q in cand)
        q_star = next(q for q in CANDIDATE_ORDER if eq[q] is not None and abs(eq[q] - best) <= EPS_TH)
        dd = {"grade": "PRED-FAIL" if gt(best, 0.010) else f"PRED-{q_star}", "q_star": q_star,
              "lower_bound_included": lower[q_star]}
    dd.update({"E": eq, "rows": use, "excluded_t14": excluded, "flags": list(tag_r)})
    g["D-d"] = dd
    # D-e (C-3)
    de_rows, need_ok = {}, True
    for r in ("C1", "C2", "C4"):
        if rows[r]["status"] != "VALID":
            need_ok = False
            continue
        m = rows[r]["m"]
        b = m["b_star"]
        gval = S_GUARD - m["s_max"][b]
        zt = m["z"]["max"][b] if m["z"]["max"] is not None else None
        f = valid_f(rows[r]["gm"], "max", b)
        fmin, fmax = F_RANGE[prm["pad"][b]["type"]]
        if zt is None:
            gt_ = None
        elif f:
            g_corr = gval + zt * (1 - 1 / f)
            gt_ = min(gval, g_corr - zt * (1 - 1 / fmax))
        else:
            g_corr = None
            gt_ = gval - zt * (fmax - fmin)
        de_rows[r] = {"g": gval, "g_corr": (g_corr if zt is not None else None), "g_tilde": gt_, "sgs": m["sgs"]}
        if gt_ is None or not ge(gt_, 0.020) or m["sgs"]:
            need_ok = False
    g["D-e"] = {"grade": "NEED-RECHECK" if need_ok else "B1-OPEN", "rows": de_rows}
    # D-f (Q-4 (a))
    c5 = rows["C5"]
    if c5["status"] != "VALID":
        g["D-f"] = {"grade": "NA", "reason": "C5 not VALID"}
    elif not c5["m"]["sgs"]:
        g["D-f"] = {"grade": "FUP-NA"}
    else:
        pairs = hrs.get(("H-M0", "C5", "pairs"), [])
        if not pairs:
            g["D-f"] = {"grade": "NA", "reason": "no H-M0 C5 pair"}
        else:
            any_ready = any(not p["sgs"] and p["ready"] for p in pairs)
            all_sgs = all(p["sgs"] for p in pairs)
            grade = "FUP-IN" if any_ready else ("FUP-OUT" if all_sgs else "NA")
            g["D-f"] = {"grade": grade, "pairs": len(pairs), "flags": (["one pair"] if len(pairs) == 1 else [])}
    # D-g
    q_star = g["D-d"].get("q_star")
    c6 = rows["C6"]
    if c6["status"] != "VALID" or g["D-d"]["grade"] in ("NA", "PRED-FAIL") or q_star is None:
        g["D-g"] = {"grade": "W-NA", "flags": (["PARTIAL"] if bundle == "PARTIAL" and c6["status"] != "VALID" else [])}
    else:
        e6 = c6["pred"]["e"][q_star]
        eqs = g["D-d"]["E"][q_star]
        if e6 is None:
            g["D-g"] = {"grade": "W-NA"}
        else:
            g["D-g"] = {"grade": "W-OK" if le(abs(e6) - eqs, 0.005) else "W-EXT", "e_C6": e6, "E_q": eqs,
                        "ratio": (abs(e6) / eqs if eqs else None)}
    # D-h
    g["D-h"] = dh_grade(hrs.get("HP_lines", []), p7, km)
    return g


def dh_grade(lines: list[dict], p7: dict | None, km: dict) -> dict[str, Any]:
    if p7 is None:
        return {"grade": "K-NA", "reason": "no P7_REF"}
    same, diff, na = [], [], []
    for ln in lines:
        key = jget(ln, km["h_key"])
        if key not in p7:
            na.append(key)
        elif p7[key] == jget(ln, km["h_commands_sha"]):
            same.append(key)
        else:
            diff.append(key)
    grade = "K-DIFF" if diff else ("K-SAME" if same else "K-NA")
    return {"grade": grade, "same": same, "diff": diff, "na": na}


def load_p7(path: Path | None, km: dict) -> dict | None:
    if path is None:
        return None
    out = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        ln = json.loads(raw)
        if jget(ln, km["p7_candidate"]) == "P0":
            out[jget(ln, km["p7_key"])] = jget(ln, km["p7_hash"])
    return out


# ----------------------------------------------------------------------------- row status

def row_status(rid: str, rs: RunSeries | None, res: dict, missing: list[str], rc: Any, km: dict,
               hp_e0_ok: bool) -> tuple[str, list[str]]:
    case, _, _, dur, _, _ = CHRONO_ROWS[rid]
    why: list[str] = []
    if rc is None or rc != 0 or rs is None or missing:
        why.append(f"V-1 rc={rc} missing={missing}")
        return "MISSING", why
    ended_by = any(nm.startswith(km["ev_fault_prefix"]) for _, nm in rs.events)
    if not (rs.t_end is not None and cyc(rs.t_end) >= cyc(dur) - 1) and not ended_by:
        why.append("V-1 end time")
        return "MISSING", why
    ident = []
    if jget(res, km["res_tag"]) != CTRL_TAG_VB:
        ident.append("I-3 tag")
    if jget(res, km["res_expect_ok"]) is not True:
        ident.append("I-3 expect_controller.ok")
    if jget(res, km["res_threads"]) != 4:
        ident.append("I-4 threads")
    if not (jget(res, km["res_hull_req"]) == jget(res, km["res_hull_eff"]) == "fast"):
        ident.append("I-7 hull hook mode")
    if jget(res, km["res_hull_sha"]) != HULL_DLL_SHA:
        ident.append("I-7 dll sha")
    if ident:
        return "INVALID", ident
    if any(nm.startswith(km["ev_reject_prefix"]) for _, nm in rs.events):
        return "MISSING_START", ["V-3 REJ_"]
    if not any(nm.startswith(km["ev_loc"]) for _, nm in rs.events):
        return "NO_LOC", ["V-3 no LOC"]
    if not hp_e0_ok:
        why.append("V-4 no valid harness VB e0 pair (D-c NA)")
    return "VALID", why


# ----------------------------------------------------------------------------- main

def run(args: argparse.Namespace) -> dict[str, Any]:
    km = dict(DEFAULT_KEYMAP)
    if args.keymap:
        km.update(json.loads(Path(args.keymap).read_text(encoding="utf-8")))
    repo = Path(args.repo)
    prm = load_params(repo)
    batch = Path(args.batch)
    bj_path = batch / km["batch_json"]
    if not bj_path.is_file():
        raise InputError(f"{bj_path} missing")
    bj = json.loads(bj_path.read_text(encoding="utf-8"))
    rcs = {jget(c, km["batch_case_name"]): jget(c, km["batch_case_rc"]) for c in jget(bj, km["batch_cases"], [])}
    hbase = Path(args.harness_jsonl).parent if args.harness_jsonl else Path(".")
    lines = harness_lines(Path(args.harness_jsonl) if args.harness_jsonl else None, km)
    for k, ln in enumerate(lines):
        ln["_id"] = k
    # harness runs
    h_ok: dict[int, tuple[RunSeries, dict]] = {}
    h_bad: dict[int, str] = {}
    for k, ln in enumerate(lines):
        rs, why = harness_valid(ln, km, hbase)
        if rs is None:
            h_bad[k] = why or "invalid"
            continue
        row = jget(ln, km["h_row"])
        level = jget(ln, km["h_level"]) or (CHRONO_ROWS[row][1] if row in CHRONO_ROWS else "top")
        m = run_metrics(rs, km, prm, level, None, is_chrono=False)
        h_ok[k] = (rs, m)
    # shadow hash pairs (2.2)
    shadow_ok = True
    for r in CORE:
        on = pick(lines, km, "H-P", r, "VB", 0.0, True)
        off = pick(lines, km, "H-SH0", r, "VB", 0.0, False)
        if not on or not off or jget(on[0], km["h_commands_sha"]) != jget(off[0], km["h_commands_sha"]):
            shadow_ok = False
    # H-P 20 for constants
    hp = [(ln, h_ok[ln["_id"]][0], h_ok[ln["_id"]][1]) for r in R_SET
          for ln in pick(lines, km, "H-P", r, None, None) if ln["_id"] in h_ok]
    consts = harness_constants(hp, prm)
    if args.constants_out:
        Path(args.constants_out).write_text(json.dumps(consts, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    # Chrono rows
    rows: dict[str, dict] = {}
    hrs: dict[Any, Any] = {"HP_lines": [ln for r in R_SET for ln in pick(lines, km, "H-P", r, None, None)]}
    for rid, (case, level, _ms, _dur, bplan, role) in CHRONO_ROWS.items():
        row_dir = batch / km["row_dir"].format(case=case)
        rs, res, missing = load_chrono_row(row_dir, km) if row_dir.is_dir() else (None, {}, ["row dir"])
        grp = "H-W" if rid == "C6" else "H-P"
        vb_e0 = [ln for ln in pick(lines, km, grp, rid, "VB", 0.0) if ln["_id"] in h_ok]
        status, why = row_status(rid, rs, res, missing, rcs.get(case), km, bool(vb_e0))
        entry: dict[str, Any] = {"id": rid, "case": case, "role": role, "status": status, "why": why}
        if status == "VALID":
            m = run_metrics(rs, km, prm, level, bplan)
            entry["m"] = m
            entry["grid_m"] = rs.grid_m
            entry["gm"] = grid_metrics(rs, m, prm) if rs.grid_m is not None else {}
            entry["pred"] = predictors(m["loc_inputs"], m, prm, km, consts, m["b_star"])
            entry["pred_planned_leg"] = predictors(m["loc_inputs"], m, prm, km, consts, bplan)
            entry["h_rec"] = h_records(rs, m, prm, km)
            entry["m12"] = m12_records(rs, m, prm, km)
            b = m["b_star"]
            hm_pairs = []
            for key, sel in (("e0", None), ("VB-e0", "VB")):
                pairs = []
                for ln in pick(lines, km, grp, rid, sel, 0.0):
                    if ln["_id"] in h_ok:
                        rs_h, m_h = h_ok[ln["_id"]]
                        pairs.append(m_h)
                hrs[(grp, rid, key)] = pairs
            for ln in pick(lines, km, grp, rid, None, None):
                if ln["_id"] in h_ok:
                    hm_pairs.append({"variant": jget(ln, km["h_variant"]), "e": jget(ln, km["h_e"]),
                                     "s_max_b": h_ok[ln["_id"]][1]["s_max"][b],
                                     "dz_post_b": (None if h_ok[ln["_id"]][1]["dz_post"] is None
                                                   else h_ok[ln["_id"]][1]["dz_post"][b])})
            entry["M10"] = hm_pairs
        rows[rid] = entry
    # H-M0 C5 pairs (7.2: drop pairs with an R4c30 event; V-4-type invalid lines are absent from h_ok)
    pairs = []
    for ln in pick(lines, km, "H-M0", "C5", None, 0.0):
        if ln["_id"] in h_ok and h_ok[ln["_id"]][1]["r4_events"] == 0:
            pairs.append(h_ok[ln["_id"]][1])
    hrs[("H-M0", "C5", "pairs")] = pairs
    # bundle (3.2)
    hp_vb_e0 = all(any(ln["_id"] in h_ok for ln in pick(lines, km, "H-P", r, "VB", 0.0)) for r in R_SET)
    core_ok = all(rows[r]["status"] == "VALID" for r in CORE)
    if not core_ok or not hp_vb_e0:
        bundle = "UNDETERMINED"
    elif all(rows[r]["status"] == "VALID" for r in CHRONO_ROWS):
        bundle = "COMPLETE"
    else:
        bundle = "PARTIAL"
    p7 = load_p7(Path(args.p7_ref) if args.p7_ref else None, km)
    grades = grade_all(rows, hrs, consts, prm, km, bundle, p7) if bundle != "UNDETERMINED" else {}
    safety_notes = {r: rows[r]["m"]["safety"] for r in rows if rows[r]["status"] == "VALID"
                    and rows[r]["m"]["safety"]["note"]}
    harness_m12 = {}
    if shadow_ok:
        for k, ln in enumerate(lines):
            if k in h_ok and bool(jget(ln, km["h_shadow"])):
                harness_m12[k] = {"group": jget(ln, km["h_group"]), "row": jget(ln, km["h_row"]),
                                  "variant": jget(ln, km["h_variant"]), "e": jget(ln, km["h_e"]),
                                  "locs": harness_shadow_locs(ln, km)}
    return {"tool": "b1_path2", "version": TOOL_VERSION, "rules_sha256": RULES_SHA256, "bundle": bundle,
            "rows": rows, "harness_invalid": h_bad, "shadow_hash_ok": shadow_ok, "constants": consts,
            "harness_m12": harness_m12,
            "grades": grades, "safety_notes": safety_notes, "keymap": km}


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return v if math.isfinite(v) else None
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return _jsonable(obj.tolist())
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True, help="checkout root (02_params, 03_src)")
    ap.add_argument("--batch", required=True, help="Chrono batch folder V5-B1-CREEP")
    ap.add_argument("--harness-jsonl", help="harness b1_H.jsonl (npz paths relative to its folder)")
    ap.add_argument("--p7-ref", help="P7_REF s2d_SC.jsonl")
    ap.add_argument("--keymap", help="JSON overriding DEFAULT_KEYMAP entries")
    ap.add_argument("--constants-out", help="write the path 2 harness constants here")
    ap.add_argument("--out", required=True, help="b1_metrics_path2.json")
    args = ap.parse_args(argv)
    try:
        result = run(args)
    except InputError as exc:
        print(json.dumps({"status": "input_error", "error": str(exc)}))
        return 2
    except Exception as exc:  # noqa: BLE001 - exit-code contract
        print(json.dumps({"status": "internal_error", "error": f"{type(exc).__name__}: {exc}"}))
        return 3
    text = json.dumps(_jsonable(result), indent=1, sort_keys=True) + "\n"
    Path(args.out).write_text(text, encoding="utf-8", newline="\n")
    summary = {"status": "ok", "bundle": result["bundle"],
               "grades": {k: v.get("grade") for k, v in result["grades"].items()},
               "out_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    print(json.dumps(summary))
    return 1 if result["bundle"] == "UNDETERMINED" else 0


if __name__ == "__main__":
    sys.exit(main())
