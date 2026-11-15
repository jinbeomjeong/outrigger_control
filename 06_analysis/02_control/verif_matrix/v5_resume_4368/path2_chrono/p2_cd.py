"""436.8 common definitions CD-1..CD-11, path 2 implementation (rev24 R24-2 [경로 2] 1, rev25 R25-2 [경로 2] 1-2;
the rev25 common block, sha 0e082b9c..., replaces the rev24 block).

Sources opened for this module (the 판정서 "읽은 것" list carries them with line ranges):
- the rev24 and rev25 handoff files (common blocks and the path 2 lines),
- rev25 additions: spec 421.1 (P3-6 limits), 422.6 (P3-7 weight), v5 criteria rev8 / rev9 3.2 (J-P3), the G6 judge
  `04_scripts/03_control/s8/r76_g6_chrono_judge.py` lines 4-9, 16, 341-348 (G6 gates),
- spec `s6_control_spec.md` (284 P3 table, 285 P-S9-2, 282.4 S-1, 310, 314.1 C-S9-60-3, 419.1, R40-2),
- 원판 7.4 / 8.1 / 8.2 / 9.1-9.3, v5 criteria rev6 3 and rev12 2.1-2.2,
- original judge source `03_src/outrigger_sim/verify/` (`s8_control.py`, `s6_control.py`) for the item names,
  the output layout (`rows`, `metrics[].times_s`, `metrics[].event_window`) and the window time base.

Times: path 2 works in engine absolute time (L2b `pads.npz` / `record.npz` `t`, phases + `settings.start_t_s`).
The original judge writes times relative to `settings.start_t_s`; they are shifted here before any comparison.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path

import numpy as np

import p2_core as C
import p2_rules as R

# ----------------------------------------------------------------------------- context (set by p2_chrono.judge)
CONTEXT: dict = {}   # "s8c_dir": folder of the path 2 original-judge outputs, "repo": checkout, "r3d_c8": R3d C-8 output

# ----------------------------------------------------------------------------- CD-7 reason phrases
REASON_INPUT_MISSING = "원 입력 결측"
REASON_NO_READY = "READY 없음"
REASON_WINDOW = "사건 창 결정 불가"
REASON_JUDGE_HOLD = "원 판정기 보류"
REASON_NO_TLIFT = "t_lift 없음(1 ms 크롤러 법선·10 Hz 구간 대체 모두 없음)"
REASON_NO_JUDGE = "원 판정기 출력 없음"
NA_NO_READY = "해당 없음(READY 없음)"
NA_NOT_TARGET = "해당 없음(대상 행 아님)"
NA_RIGID_BASE = "해당 없음(rigid_base)"
REASON_KEY = "cd7_reason"          # CD-7 reason key on items (K-10: excluded, CD-10 last sentence)
ROW_REASON_KEY = "cd7_row_reason"  # CD-7 one-line reason per row

# ----------------------------------------------------------------------------- CD-2 original judge items
JUDGE_REL_PATH = "verify_S8C.json"          # per batch folder, written by the run script under --s8c-dir
JUDGE_REF_COMMIT = "b9f5707"                # CD-2 (1): R2; the original judge code must equal it (else S-11)
JUDGE_CODE_PATHS = ("03_src", "04_scripts/02_chrono/run_S8C.py", "04_scripts/02_chrono/run_S6C.py")
JUDGE_SHA_FILES = ("03_src/outrigger_sim/verify/s8_control.py", "03_src/outrigger_sim/verify/s6_control.py",
                   "03_src/outrigger_sim/verify/s6_bundle_c.py", "04_scripts/02_chrono/run_S8C.py",
                   "04_scripts/02_chrono/run_S6C.py")
JUDGED_KINDS = ("function", "judged", "anomaly", "replay", "quality", None)
RECORD_KINDS = ("record", "report", "info", "consistency", "comparison", "pair", "sensitivity", "superseded",
                "leak_compare")
HOLD_KIND = "hold"

ITEM_C1 = "C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN"
ITEM_D8_CYL = "D8 min true cylinder force >= F_min + 5 kN"
ITEM_D8_LIFT = "D8 no pad lift-off"
ITEM_P4_MOVING = "4 max moving pressure"
ITEM_P4_OUT = "4 max moving pressure outside the event transient"
ITEM_P4_IN = "4 max pressure in the event transient"
ITEM_P4_SAT = "4 saturation steps"
RECALC_ITEMS = (ITEM_C1, ITEM_D8_CYL, ITEM_D8_LIFT, ITEM_P4_MOVING, ITEM_P4_OUT, ITEM_P4_IN, ITEM_P4_SAT)
ORIGINAL_EXACT_ITEMS = (
    "C-S8-72 U58: head F/A_p in the window <= 350 bar, outside extension samples <= 180 bar "
    "(slow event: whole-run any-state peak <= 350)",
    "R/D8 min force >= F_min + 5 kN", "R/D8 no pad lift-off",
    "D8 attitude last 5 s + mount <= 0.2 deg", "2 attitude +-0.2 (+mount)")
TLIFT_PREFIXES = ("3 F_min (1 ms)", "3 F_min before the event", "5a rocking amplitude",
                  "F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off)")
CD3_SUB_ID = {ITEM_P4_MOVING: "비사건 이동 압력", ITEM_P4_OUT: "W 밖", ITEM_P4_IN: "W 안", ITEM_P4_SAT: "포화"}
C1_MARGIN_N = 5000.0                        # CD-2 table: F_min + 5 kN (= 14,414.589 N)
TLIFT_DIFF_MAX_S = 0.1                      # CD-2 table last-but-one row: diff > 0.1 s + 1e-9 s -> stop
RIGID_CONTACT = "nsc_rigid"                 # R40-6: absent meta = rigid

# ----------------------------------------------------------------------------- CD-3 events and pressure
FLOOR_EVENTS = ("settle_RR_30", "drop_RR_30", "drop_RR_30_probe")
DIAGONAL_LEG = {"FL": "RR", "RR": "FL", "FR": "RL", "RL": "FR"}
T3_TOP_S = 0.82                             # CD-3: three_point_rocking_period_s, top level
WINDOW_CAP_S = 5.0                          # CD-3: t_event + 5 s
READY_EVENT_FALLBACK_S = 5.0                # CD-3: no event_t_s -> first READY + 5 s (floor events only)
WINDOW_DIFF_MAX_S = 0.1                     # CD-3: computed vs original window end > 0.1 s -> stop
IN_WINDOW_BAR = 350.0                       # CD-3: W 안 every state head <= 350 bar
RR_INDEX = 3

# ----------------------------------------------------------------------------- CD-4 P3-7 (spec 284, 285, 314.1)
P37_WINDOW_M = 0.010
P37_SPEED_FRACTION = 0.15
P37_RISE_MAX_N = 2000.0
P37_PLAUSIBILITY = 0.85
P37_RISE_MIN_N = 4000.0                     # 284 P3-7: minimum rise of the loaded windows >= 4 kN
P37_LOADED_FRACTION = 0.01                  # "> 0.01 x (mass_scale x W_ref)" (spec 422.6, rev25 R25-2 2 (나))
P37_RECORD_THRESHOLDS = (("gt1kN", 1000.0, None), ("gt0p05W", None, 0.05))   # 0.05 W_ref record bucket (as before)
P37_GATE_TOL_S = 1e-6                       # 314.1 reconstruction gate |diff| <= 1e-6 s
LW_RESTART_MODES = ("restart", "lwa")       # 419.2 LWa: window restart while a re-approach is active
LW_OFF_MODES = (None, "", "off", "none")

# ----------------------------------------------------------------------------- CD-6 T4 / T5 target rows (v5 rev6 3, rows 1-18)
T45_TARGET_ROWS = frozenset((
    "K0V_top_fup3.5_Fs0", "K0_top_fup3.2_Fs0", "K0V_top_roll5.5_Fs0", "K0_top_fdown3.2_Fs0",
    "K0V_top_fdown3.5_Fs0", "E_G4_Fs8", "K0_top_rpBop_Fs0", "E_RE1bF_Fs0", "E_RE1bF_Fs8", "K8_top_rpB_Fs8",
    "S_top_fdown3.5_wika_Fs8", "K8_top_fdown3.5_Fs8",
    "K0V_top_fup3.5_Fs0_LS1", "K0V_top_fup3.5_Fs0_LS4", "E_G4_Fs8_LS1", "E_G4_Fs8_LS4",
    "E_RE1bF_Fs8_LS1", "E_RE1bF_Fs8_LS4"))
T45_KEYS = ("T4-0", "T4", "T5")

# ----------------------------------------------------------------------------- CD-1 row counts
C5_ROWS_L2B = 24
C5_ROWS_SCM = 11

# ----------------------------------------------------------------------------- CD-11 common item ids
COMMON_ID = {"J11_window": "J11", "J11_record": "J11", "J-P3": "J-P3", "D2": "D2", "T4-0": "T4-0", "T4": "T4",
             "T5": "T5", "FAULT0": "FAULT0", "D8_FAULT0": "FAULT0", "G6-6": "G6-6", "READY_le_120s": "READY_le_120s",
             "identity": "identity", "K1_class": "K1_class", "R9-1_expect_controller": "R9-1",
             "R11-4_commit": "R11-4",
             **{f"P3-{k}": f"P3-{k}" for k in range(1, 10)},
             **{f"E-{k}": f"E-{k}" for k in range(1, 8)}}

# ----------------------------------------------------------------------------- rev25 CD-11 classes and clause ids
CLASS_GRADED, CLASS_GATE, CLASS_RECORD = "등급 항목", "관문", "기록"
GATE_KEYS = ("identity", "K1_class", "R9-1_expect_controller", "R11-4_commit", "T4-0")
# CD-2 override table rows 1..12 (CD-11 clause id `CD-2 표 n줄`)
CD2_TABLE_LINE = {ITEM_C1: 1, ITEM_D8_CYL: 2, ITEM_D8_LIFT: 3, ITEM_P4_MOVING: 4, ITEM_P4_OUT: 5, ITEM_P4_IN: 6,
                  ITEM_P4_SAT: 7, ORIGINAL_EXACT_ITEMS[0]: 8, ORIGINAL_EXACT_ITEMS[1]: 9, ORIGINAL_EXACT_ITEMS[2]: 9,
                  ORIGINAL_EXACT_ITEMS[3]: 10, ORIGINAL_EXACT_ITEMS[4]: 10}
CD2_TABLE_PREFIX_LINE, CD2_TABLE_OTHER_LINE = 11, 12
# C-3 G6 correspondence table (rev25 CD-11): G6 gate -> common id
G6_TABLE = (("G6-1", "P3-1"), ("G6-2", "P3-2"), ("G6-3", "P3-3"), ("G6-4", "P3-4"), ("G6-5", "P3-5"),
            ("G6-6", "G6-6"), ("G6-7", "P3-8"), ("READY_le_120s", "READY_le_120s"))
G6_IDS = tuple(cid for _, cid in G6_TABLE)
SAFE_STOP_IDS = tuple(f"427.9-{n}" for n in range(1, 6))


def _judge_case_names(row) -> set:
    return {str(row.case), row.folder.name}


# ============================================================================= CD-2 (1): provenance of the judge run
def judge_provenance(repo: Path) -> dict:
    """CD-2 (1): the original judge code (`03_src`, `run_S8C.py`, `run_S6C.py`) of this checkout's working tree
    must equal R2 `b9f5707` (git diff empty, else S-11); records the checkout commit and the judge file sha256."""
    out = {"clause": "CD-2 (1)", "reference": JUDGE_REF_COMMIT, "paths": list(JUDGE_CODE_PATHS)}
    try:
        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
        diff = subprocess.run(["git", "-C", str(repo), "diff", "--name-only", JUDGE_REF_COMMIT, "--",
                               *JUDGE_CODE_PATHS], capture_output=True, text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError) as exc:
        out.update(ok=False, stop=f"S-11 (CD-2 (1): git check failed: {exc})")
        return out
    out["checkout_commit"] = head
    out["diff_vs_reference"] = diff
    out["judge_files_sha256"] = {f: (hashlib.sha256((repo / f).read_bytes()).hexdigest()
                                     if (repo / f).exists() else None) for f in JUDGE_SHA_FILES}
    out["ok"] = not diff
    if diff:
        out["stop"] = f"S-11 (CD-2 (1): original judge code differs from {JUDGE_REF_COMMIT}: {diff})"
    return out


_DOCS: dict = {}


def judge_doc_for(row):
    """The path 2 original-judge output of the row's batch folder: `<s8c_dir>/<batch folder>/verify_S8C.json`
    (CD-2 (2): written by the path 2 run into its own output folder). Returns (doc, reason)."""
    s8c = CONTEXT.get("s8c_dir")
    if not s8c:
        return None, REASON_NO_JUDGE + " (--s8c-dir 없음)"
    p = Path(s8c) / row.folder.parent.name / JUDGE_REL_PATH
    if p not in _DOCS:
        if not p.exists():
            _DOCS[p] = (None, f"{REASON_NO_JUDGE} ({row.folder.parent.name}/{JUDGE_REL_PATH})")
        else:
            doc = json.loads(p.read_text(encoding="utf-8"))
            batch = Path(str((doc.get("meta") or {}).get("batch") or ""))
            if batch.name != row.folder.parent.name:
                _DOCS[p] = (None, f"{REASON_NO_JUDGE} (meta.batch {batch.name!r} != {row.folder.parent.name!r})")
            else:
                _DOCS[p] = (doc, None)
    return _DOCS[p]


STAR_CASE = "*"
STAR_SUFFIX = " [case *]"   # rev25 CD-11: common item id of a case `*` item


def judge_rows_of(doc, row) -> list:
    """The original judge's items of the row: its own case rows and (rev25 R25-2 2 (가), a rev24 defect fix) the
    batch-level case `*` rows of the row's batch folder (each judged folder holds the one row)."""
    names = _judge_case_names(row)
    return [r for r in doc.get("rows") or [] if isinstance(r, dict)
            and (str(r.get("case")) in names or str(r.get("case")) == STAR_CASE)]


def judge_metric_of(doc, row):
    names = _judge_case_names(row)
    return next((m for m in doc.get("metrics") or [] if isinstance(m, dict) and str(m.get("case")) in names), None)


# ============================================================================= CD-2 (a): t_lift
def t_lift_a(row):
    """CD-2 (a): the 1 ms crawler-normal lift-off time (v5 rev6 5 t_lift,sus, D-29) in engine absolute time;
    without the 1 ms series the 10 Hz bracket substitute (rev15 D-29, t_b). Returns (t, basis)."""
    if row.cr_basis == "1ms":
        return C.t_lift_sus_d29(row), "1ms_sus"
    if row.cr_basis == "bracket_10Hz":
        tl, _ = C.t_lift(row)
        return tl, "bracket_10Hz"
    return None, row.cr_basis


def _reanchor_windows(row):
    out = []
    for i, (t, name) in enumerate(row.phases):
        if name == "reanchor":
            out.append((t, row.phases[i + 1][0] if i + 1 < len(row.phases) else row.t_end))
    return out


def _is_rigid_crawler(row) -> bool:
    """R40-2 / R40-6 scope: rigid NSC crawler, or a compliant one whose S8-L4 check has not passed."""
    s8 = (row.result.get("settings") or {}).get("s8") or {}
    rigid = str(s8.get("crawler_contact") or RIGID_CONTACT) == RIGID_CONTACT
    return rigid or s8.get("crawler_check_passed") is not True


def _event_abs(row):
    """`result.json` `event_t_s` (run-relative) as engine absolute time, when it is a number."""
    ev = row.result.get("event_t_s")
    if isinstance(ev, bool) or not isinstance(ev, (int, float)):
        return None
    return float(ev) + row.t_offset


def recalc_c1(row, params, tl) -> dict:
    """CD-2 table row 1: raw 1 ms true rod force (path 2 `Row.F`: `F_cyl_min_interval`, airborne samples on the
    20 ms mean) after (a) t_lift, outside REANCHOR and (rev25, decision 98 2) before `event_t_s` when that is a
    number (run-relative: engine time - start_t_s < event_t_s), minimum >= F_min + 5 kN. R40-2 hold (rigid
    crawler, raw min within 8 s of t_lift, slow 1 s centred mean min over the first 8 s >= limit) cannot be
    resolved here (L1 pair / compliant rerun) -> 판정 불가."""
    limit = params["F_min_N"] + C1_MARGIN_N
    out = {"definition": "CD-2 table row 1", "t_lift_s": tl, "limit_N": limit}
    if tl is None:
        out.update(verdict="indeterminate", **{REASON_KEY: REASON_NO_TLIFT})
        return out
    mask = row.tF >= tl - R.CMP_TOL
    for a, b in _reanchor_windows(row):
        mask &= ~((row.tF >= a) & (row.tF <= b))
    out["reanchor_windows_s"] = _reanchor_windows(row)
    ev = _event_abs(row)
    if ev is not None:   # rev25 CD-2 row 1 event cut
        mask &= row.tF < ev
    out["event_cut_s"] = ev
    out["interval"] = (f"t >= {tl:.6f} s" + ("" if ev is None else f", t < {ev:.6f} s (event_t_s)")
                       + ", REANCHOR 밖 (engine absolute time)")
    if not mask.any():
        out.update(verdict="indeterminate", **{REASON_KEY: REASON_INPUT_MISSING + " (t_lift 뒤 표본 없음)"})
        return out
    Fm = np.where(mask[:, None], row.F, np.inf)
    i, leg = np.unravel_index(int(np.argmin(Fm)), Fm.shape)
    vmin = float(Fm[i, leg])
    out.update(min_N=vmin, min_leg=R.LEGS[leg], min_t_s=float(row.tF[i]))
    ok = R.ge(vmin, limit)
    out["verdict"] = "pass" if ok else "fail"
    if ok or not _is_rigid_crawler(row):
        return out
    dt = C.dt_of(row.tF)
    n = int(round(R.HOLD_SLOW_MEAN_S / dt)) | 1
    kern = np.ones(n) / n
    slow = np.stack([np.convolve(row.F[:, j], kern, mode="same") for j in range(4)], axis=1)
    early = mask & (row.tF <= tl + R.HOLD_WINDOW_S + R.CMP_TOL)
    slow_min = float(slow[early].min()) if early.any() else None
    in8 = row.tF[i] <= tl + R.HOLD_WINDOW_S + R.CMP_TOL
    out["hold_check"] = {"min_in_8s": bool(in8), "slow_min_first8_N": slow_min, "threshold_N": limit}
    if in8 and slow_min is not None and R.ge(slow_min, limit):
        out.update(verdict="hold", **{REASON_KEY: REASON_JUDGE_HOLD + " (R40-2 해제 절차를 이 도구가 풀 수 없음)"})
    return out


def recalc_d8_lift(row, tl) -> dict:
    """CD-2 table row 3: pad normal (`pads.npz` `N`) <= 0 1 ms samples from (a) t_lift to the record end = 0."""
    out = {"definition": "CD-2 table row 3", "t_lift_s": tl}
    if tl is None:
        out.update(verdict="indeterminate", **{REASON_KEY: REASON_NO_TLIFT})
        return out
    if row.pad_n is None:
        out.update(verdict="indeterminate", **{REASON_KEY: REASON_INPUT_MISSING + " (pads.npz N)"})
        return out
    sel = row.t_pad >= tl - R.CMP_TOL
    le0 = row.pad_n[sel] <= 0.0 + R.CMP_TOL
    out["interval"] = f"t >= {tl:.6f} s to the record end"
    out["samples_per_leg"] = le0.sum(axis=0).astype(int).tolist()
    out["verdict"] = "pass" if not le0.any() else "fail"
    return out


# ============================================================================= CD-3 events, windows, pressure
def event_class(row, v_max_m_s) -> dict:
    """CD-3 closed event-row rule."""
    res = row.result
    setting = (res.get("settings") or {}).get("event")
    if setting in FLOOR_EVENTS:
        return {"class": "floor", "settings_event": setting, "has_event_t_s": res.get("event_t_s") is not None}
    ev = res.get("event")
    spec = ev.get("spec") if isinstance(ev, dict) else None
    out = {"class": "none", "settings_event": setting, "has_event_t_s": res.get("event_t_s") is not None}
    if not isinstance(spec, dict) or spec.get("kind") != "settle":
        return out
    leg, depth, ramp = spec.get("leg"), spec.get("depth_m"), spec.get("ramp_s")
    if leg not in R.LEGS or depth is None or res.get("event_t_s") is None:
        return out
    speed = math.inf if not ramp or float(ramp) <= 0.0 else float(depth) / float(ramp)
    out["speed_m_s"] = None if math.isinf(speed) else speed
    if speed > v_max_m_s:
        out.update({"class": "fast_settle", "settle_leg": leg, "event_legs": [leg, DIAGONAL_LEG[leg]]})
    return out


def _t3_of(row):
    level = (row.result.get("settings") or {}).get("level")
    return T3_TOP_S, ([] if level == "top" else ["T3_from_top_level"])


def _rr_last_reground(row, t_ev):
    """CD-3: after t_event the last 1 ms sample with RR pad normal <= 0, its next sample time; no lift -> t_event;
    lifted to the record end -> None."""
    sel = row.t_pad >= t_ev
    t = row.t_pad[sel]
    lifted = row.pad_n[sel, RR_INDEX] <= 0.0
    if not lifted.any():
        return t_ev, False
    last = int(np.flatnonzero(lifted)[-1])
    return (float(t[last + 1]) if last + 1 < len(t) else None), True


def event_window(row, ev: dict, metric) -> dict:
    """CD-3 window W = [t_event, W end] in engine absolute time. Floor event: computed here (definition); the
    original judge's recorded end (`metrics[].event_window.pressure_end_s` + start_t_s) is compared. Fast settle:
    the original judge's recorded window is read (CD-3 allows it); without it, t_event + 5 s when the 1 ms
    `airborne` / ball-centre record is absent, else 판정 불가 (the U-S8-32 split is not reimplemented)."""
    out = {"class": ev["class"]}
    jw = (metric or {}).get("event_window") if isinstance(metric, dict) else None
    judge_end = None
    if isinstance(jw, dict) and jw.get("pressure_end_s") is not None:
        judge_end = float(jw["pressure_end_s"]) + row.t_offset
    out["judge_end_s"] = judge_end
    t_ev = _event_abs(row)
    if t_ev is None and ev["class"] == "floor":
        t_R = C.first_phase_time(row, "ready")
        if t_R is not None:
            t_ev = t_R + READY_EVENT_FALLBACK_S
            out["t_event_basis"] = "first READY + 5 s"
    elif t_ev is not None:
        out["t_event_basis"] = "event_t_s"
    out["t_event_s"] = t_ev
    if t_ev is None:
        out.update(ok=False, **{REASON_KEY: REASON_WINDOW + " (t_event 없음)"})
        return out
    t3, notes = _t3_of(row)
    out["T3_s"] = t3
    out["notes"] = notes
    cap = t_ev + WINDOW_CAP_S
    if ev["class"] == "floor":
        if row.pad_n is None:
            out.update(ok=False, **{REASON_KEY: REASON_WINDOW + " (pads.npz N 없음)"})
            return out
        reground, lifted = _rr_last_reground(row, t_ev)
        end = cap if reground is None else min(reground + t3, cap)
        out.update(method="computed (CD-3 floor)", rr_last_reground_s=reground, rr_lifted=lifted)
    else:
        if judge_end is not None:
            end = judge_end
            out["method"] = "original judge window read (CD-3)"
        else:
            keys = set(np.load(row.folder / "pads.npz").files)
            if "airborne" not in keys or "ball_centre_world" not in keys:
                end = cap
                out["method"] = "computed (CD-3 fast settle, no airborne / ball-centre record)"
            else:
                out.update(ok=False, **{REASON_KEY: REASON_WINDOW + " (원 판정기 창 기록 없음, U-S8-32 분할 미구현)"})
                return out
    out.update(start_s=t_ev, end_s=end, ok=True)
    if out["method"].startswith("computed") and judge_end is not None:
        out["diff_vs_judge_s"] = end - judge_end
    return out


def _pressure_record(row, params):
    rp = row.folder / "record" / "record.npz"
    if not rp.exists():
        return None
    rec = np.load(rp)
    A = np.array(params["head_area_m2"])
    t = np.asarray(rec["t"], float)
    p_bar = np.asarray(rec["F_cyl"], float) / A[None, :] / 1e5
    u = np.asarray(rec["u_applied"], float)
    return t, p_bar, u


def _peak(t, p_bar, mask, states=None) -> dict:
    if not mask.any():
        return {"max_bar": None, "leg": None, "t_s": None, "samples": 0}
    v = np.where(mask, p_bar, -np.inf)
    i, leg = np.unravel_index(int(np.argmax(v)), v.shape)
    out = {"max_bar": float(v[i, leg]), "leg": R.LEGS[leg], "t_s": float(t[i]), "samples": int(mask.sum())}
    if states is not None:
        out["state"] = states[i, leg]
    return out


def _state_of(u):
    return np.where(u > R.MOVING_U_EPS, "extend", np.where(u < -R.MOVING_U_EPS, "retract", "hold"))


def cd3_items(row, params, ev, win) -> dict:
    """CD-3 sub-items: non-event moving pressure, W 밖 (extension <= 180 bar; retraction recorded), W 안 (every
    state <= 350 bar) and saturation (extension samples >= 210 bar = 0; event rows outside W)."""
    rec = _pressure_record(row, params)
    out = {}
    names = (ITEM_P4_MOVING, ITEM_P4_SAT) if ev["class"] == "none" else (ITEM_P4_OUT, ITEM_P4_IN, ITEM_P4_SAT)
    if rec is None:
        for k in names:
            out[k] = {"verdict": "indeterminate", REASON_KEY: REASON_INPUT_MISSING + " (record/record.npz)"}
        return out
    t, p_bar, u = rec
    ext = u > R.MOVING_U_EPS
    ret = u < -R.MOVING_U_EPS
    if ev["class"] == "none":
        moving = ext | ret
        pk = _peak(t, p_bar, moving)
        out[ITEM_P4_MOVING] = dict(pk, definition="CD-3 non-event", limit_bar=R.MOVING_BAR,
                                   interval="record.npz 전 표본, |u_applied| > 1e-9 m/s",
                                   verdict="pass" if pk["max_bar"] is None or R.le(pk["max_bar"], R.MOVING_BAR)
                                   else "fail")
        sat = ext & (p_bar >= R.SATURATION_BAR - R.CMP_TOL)
        out[ITEM_P4_SAT] = {"definition": "CD-3 saturation (non-event)", "count": int(sat.sum()),
                            "interval": "record.npz 전 표본, u_applied > 1e-9 m/s",
                            "count_per_leg": sat.sum(axis=0).astype(int).tolist(),
                            "verdict": "pass" if not sat.any() else "fail"}
        return out
    if not win.get("ok"):
        for k in names:
            out[k] = {"verdict": "indeterminate", REASON_KEY: win.get(REASON_KEY) or REASON_WINDOW}
        return out
    inside = (t >= win["start_s"] - R.CMP_TOL) & (t <= win["end_s"] + R.CMP_TOL)
    outside = ~inside[:, None]
    w_text = f"W = [{win['start_s']:.6f}, {win['end_s']:.6f}] s"
    pk_out = _peak(t, p_bar, outside & ext)
    out[ITEM_P4_OUT] = dict(pk_out, definition="CD-3 event W 밖 extension", limit_bar=R.MOVING_BAR,
                            interval=f"{w_text} 밖, u_applied > 1e-9 m/s",
                            retract_record=_peak(t, p_bar, outside & ret),
                            verdict="pass" if pk_out["max_bar"] is None or R.le(pk_out["max_bar"], R.MOVING_BAR)
                            else "fail")
    pk_in = _peak(t, p_bar, np.repeat(inside[:, None], 4, axis=1), states=_state_of(u))
    out[ITEM_P4_IN] = dict(pk_in, definition="CD-3 event W 안 every state", limit_bar=IN_WINDOW_BAR,
                           interval=f"{w_text} 안, 모든 상태",
                           verdict="pass" if pk_in["max_bar"] is None or R.le(pk_in["max_bar"], IN_WINDOW_BAR)
                           else "fail")
    sat = outside & ext & (p_bar >= R.SATURATION_BAR - R.CMP_TOL)
    out[ITEM_P4_SAT] = {"definition": "CD-3 saturation (event: outside W)", "count": int(sat.sum()),
                        "interval": f"{w_text} 밖, u_applied > 1e-9 m/s",
                        "count_per_leg": sat.sum(axis=0).astype(int).tolist(),
                        "verdict": "pass" if not sat.any() else "fail"}
    return out


def _window_verdict_change(row, params, ev, win) -> bool | None:
    """CD-3: would the original judge's window end change a W 밖 / W 안 / 포화 verdict?"""
    if win.get("judge_end_s") is None or not win.get("ok"):
        return None
    alt = dict(win, end_s=win["judge_end_s"])
    a, b = cd3_items(row, params, ev, win), cd3_items(row, params, ev, alt)
    return any(a[k]["verdict"] != b[k]["verdict"] for k in a)


# ============================================================================= CD-2 row items
def classify_item(name: str):
    if name in RECALC_ITEMS:
        return "recalc"
    if name in ORIGINAL_EXACT_ITEMS:
        return "original"
    if any(name.startswith(p) for p in TLIFT_PREFIXES):
        return "original_tlift"
    return "original_other"


def _use_of(kind):
    if kind == HOLD_KIND:
        return "hold"
    if kind in JUDGED_KINDS:
        return "judged"
    if kind in RECORD_KINDS:
        return "record"
    return "runner_unjudged"


def _flag_of(j) -> bool:
    return bool(j.get("flag")) or (j.get("kind") == "anomaly" and "FLAG" in str(j.get("note") or ""))


def _word(passed, use):
    if use == "hold":
        return "hold"
    if use == "record":
        return "record"
    if use == "runner_unjudged":
        return "runner_unjudged"
    if passed is None:
        return "runner_unjudged"
    return "pass" if passed else "fail"


def cd2_items(row, params) -> dict:
    """CD-2 L2b row item block: the original judge's items of the row with the CD-2 count and the override table.
    Grade inside the block (CD-2 count): any judged-class `passed` False -> fail (미달); else any hold (or a
    recalculated item not computable) -> 판정 불가; judged-class passed True count 0 -> 판정 불가; else pass."""
    out = {"clause": "CD-2 (rev25 common block)", "layer": "original judge run by path 2 + CD-2 overrides"}
    doc, why = judge_doc_for(row)
    if doc is None:
        out.update(verdict="indeterminate", entries=[], **{REASON_KEY: why})
        return out
    jrows = judge_rows_of(doc, row)
    metric = judge_metric_of(doc, row)
    out["judge_meta"] = {"batch_folder": row.folder.parent.name, "rows_for_case": len(jrows),
                         "judge_revision_head": str((doc.get("meta") or {}).get("judge_revision") or "")[:80]}
    if not jrows:
        out.update(verdict="indeterminate", entries=[], **{REASON_KEY: REASON_NO_JUDGE + " (그 행 항목 0)"})
        return out
    tl, basis = t_lift_a(row)
    out["t_lift"] = {"t_lift_s": tl, "basis": basis}
    ev = event_class(row, params["v_max_m_s"])
    out["event"] = ev
    win = event_window(row, ev, metric) if ev["class"] != "none" else None
    out["window"] = win
    cd3 = cd3_items(row, params, ev, win or {})
    stops = []
    if win is not None and win.get("diff_vs_judge_s") is not None:
        changed = _window_verdict_change(row, params, ev, win)
        win["judge_window_changes_verdict"] = changed
        if abs(win["diff_vs_judge_s"]) > WINDOW_DIFF_MAX_S or changed:
            stops.append("CD-3: computed window end vs original judge "
                         f"{win['diff_vs_judge_s']:+.6f} s (> 0.1 s or verdict change): stop and ask")
    entries = []
    names = {str(j.get("item")) for j in jrows}
    need_tlift_check = any(classify_item(n) == "original_tlift" for n in names)
    if need_tlift_check:
        out["t_lift_check"] = _tlift_check(row, tl, basis, metric)
        if not out["t_lift_check"]["ok"]:
            stops.append("CD-2 t_lift 차 확인: " + out["t_lift_check"]["reason"] + " (stop and ask)")
    for j in jrows:
        entries.append(_entry(row, params, j, tl, ev, cd3, stops))
    out["entries"] = entries
    out.update(_cd2_grade(entries))
    out["flags"] = sorted({e["item"] for e in entries if e["flag"]})
    out["runner_unjudged"] = [{"item": e["item"], "note": e["orig_note"]} for e in entries
                              if e["use"] == "runner_unjudged"]
    if stops:
        out["stop"] = "; ".join(stops)
    if out["verdict"] == "indeterminate":
        out[REASON_KEY] = out.get(REASON_KEY) or "; ".join(
            sorted({e.get(REASON_KEY) or e["item"] for e in entries if e["verdict"] in ("hold", "indeterminate")})
        ) or "판정 종류 통과 항목 0"
    return out


LEGACY_D8P_KEYS = ("D8_F_after_liftoff", "D8_end_attitude", "D8_READY", "D8_pressure", "D8_FAULT0")


def use_cd2(items, keys, row, params):
    """CD-2 for an L2b row of C-1 / C-2 (and C-5): the row items are the original judge's items. The earlier
    path 2 D8.P items stay as records (values unchanged) and leave the graded keys; their stop text is kept
    under `stop_superseded_cd2` (the C1 / R40-2 handling is now the CD-2 recalculation)."""
    for k in LEGACY_D8P_KEYS:
        if k in keys:
            keys.remove(k)
        it = items.get(k)
        if isinstance(it, dict):
            it["graded"] = False
            if "stop" in it:
                it["stop_superseded_cd2"] = it.pop("stop")
    items["CD-2"] = cd2_items(row, params)
    keys.append("CD-2")


def _tlift_check(row, tl, basis, metric) -> dict:
    """CD-2 table: per row the original judge lift-off time (10 Hz, `metrics[].times_s.liftoff` + start_t_s) vs
    (a) t_lift (1 ms basis rounded up to the first control-period sample >= it; bracket basis as is)."""
    jl = ((metric or {}).get("times_s") or {}).get("liftoff") if isinstance(metric, dict) else None
    judge_abs = None if jl is None else float(jl) + row.t_offset
    a = C.up_to_control_instant(row, tl) if basis == "1ms_sus" else tl
    out = {"judge_liftoff_s": judge_abs, "t_lift_a_s": tl, "t_lift_a_compared_s": a, "basis": basis}
    if judge_abs is None or a is None:
        out.update(ok=False, reason="차를 계산할 수 없음 (원 판정기 이륙 시각 또는 (a) t_lift 없음)")
        return out
    d = judge_abs - a
    out["diff_s"] = d
    out["ok"] = abs(d) <= TLIFT_DIFF_MAX_S + R.CMP_TOL
    if not out["ok"]:
        out["reason"] = f"|차| {abs(d):.6f} s > 0.1 s"
    return out


def _entry(row, params, j, tl, ev, cd3, stops) -> dict:
    name = str(j.get("item"))
    kind = j.get("kind")
    handling = classify_item(name)
    use = _use_of(kind)
    star = str(j.get("case")) == STAR_CASE
    e = {"item": name, "kind": kind, "handling": handling, "orig_passed": j.get("passed"),
         "orig_value": j.get("value"), "orig_limit": j.get("limit"), "orig_note": str(j.get("note") or "")[:300],
         "flag": _flag_of(j), "cd3_sub_id": CD3_SUB_ID.get(name), "case_star": star,
         "common_id": name + (STAR_SUFFIX if star else ""), "table_line": _table_line(name, handling)}
    passed = j.get("passed")
    if handling == "recalc":
        rc = _recalc(row, params, name, tl, ev, cd3, stops)
        e["recalc"] = rc
        e["interval"] = rc.get("interval")
        if use == "record":
            e["recalc_record_only"] = "기록 종류로 나온 재계산 항목: 판정에 쓰지 않고 두 값만 남김"
        elif use in ("judged", "hold"):
            v = rc.get("verdict")
            if v == "pass":
                passed, use = True, "judged"
            elif v == "fail":
                passed, use = False, "judged"
            else:                                  # hold / indeterminate (not computable) -> hold class
                passed, use = None, "hold"
            e["changed"] = (passed != j.get("passed")) or (use == "hold") != (kind == HOLD_KIND)
            if e["changed"]:
                e["cd7_change_reason"] = (f"재계산 값으로 판정(CD-2 표): 원 판정기 passed={j.get('passed')!r} "
                                          f"kind={kind!r} -> 재계산 {v}")
    if use == "judged" and passed is None:
        use = "runner_unjudged"   # CD-2: a judged-class item with passed None is 러너 미판정 (not counted)
    e["passed"] = passed
    e["use"] = use
    e["verdict"] = _word(passed, use)
    if e["verdict"] == "pass" and e["flag"]:
        e["verdict"] = "flag"
    if e["verdict"] in ("hold", "indeterminate"):
        e[REASON_KEY] = (e.get("recalc") or {}).get(REASON_KEY) or (REASON_JUDGE_HOLD + ": " + e["orig_note"][:120])
    elif e["verdict"] == "runner_unjudged":
        e[REASON_KEY] = f"러너 미판정 (kind {kind!r}, passed {j.get('passed')!r}): " + (e["orig_note"][:120] or "-")
    return e


def _table_line(name: str, handling: str) -> int:
    """rev25 CD-11 clause id `CD-2 표 n줄`: the override-table row of the item (prefix row 11, other / case `*` 12)."""
    if name in CD2_TABLE_LINE:
        return CD2_TABLE_LINE[name]
    return CD2_TABLE_PREFIX_LINE if handling == "original_tlift" else CD2_TABLE_OTHER_LINE


def _recalc(row, params, name, tl, ev, cd3, stops) -> dict:
    if name == ITEM_C1:
        return recalc_c1(row, params, tl)
    if name == ITEM_D8_LIFT:
        return recalc_d8_lift(row, tl)
    if name == ITEM_D8_CYL:
        stops.append(f"CD-2: '{ITEM_D8_CYL}' appeared (table: 0 rows expected; window end not readable) -> ask")
        return {"verdict": "indeterminate", REASON_KEY: "적용 행 0으로 정의된 항목이 나옴(창 끝 미정)"}
    if name in cd3:
        return cd3[name]
    stops.append(f"CD-2/CD-3: '{name}' on a {ev['class']!r} row is outside the table's row class -> ask")
    return {"verdict": "indeterminate", REASON_KEY: "덮어쓰기 표 적용 행과 행 판별이 어긋남"}


def _cd2_grade(entries) -> dict:
    counted = [e for e in entries if e["use"] in ("judged", "hold")]
    judged = [e for e in entries if e["use"] == "judged"]
    n_pass = sum(1 for e in judged if e["passed"] is True)
    if any(e["passed"] is False for e in counted):
        g = "fail"
    elif any(e["use"] == "hold" for e in counted):
        g = "indeterminate"
    elif n_pass == 0:
        g = "indeterminate"
    else:
        g = "pass"
    return {"verdict": g, "n_judged": len(judged), "n_judged_pass": n_pass,
            "n_hold": sum(1 for e in counted if e["use"] == "hold"),
            "n_record": sum(1 for e in entries if e["use"] == "record"),
            "n_runner_unjudged": sum(1 for e in entries if e["use"] == "runner_unjudged")}


# ============================================================================= CD-4 P3-7
def _cylinder_areas(repo: Path):
    import yaml  # PyYAML (dynamics-dev)
    y = yaml.safe_load((repo / R.REPO_MARKER).read_text(encoding="utf-8"))
    head = np.array([float(y["legs"][g]["cylinder"]["head_area_m2"]) for g in R.LEGS])
    ann = np.array([float(y["legs"][g]["cylinder"]["annulus_area_m2"]) for g in R.LEGS])
    return head, ann


def _reapproach_active(row, t):
    out = np.zeros(len(t), bool)
    for iv in C.reapproach_intervals(row):
        end = iv["end_s"] if iv["end_s"] is not None else np.inf
        out |= (t >= iv["start_s"] - R.CMP_TOL) & (t < end - R.CMP_TOL)
    return out


def _tail_rise(e, F, idx):
    """Minimal tail covering 10 mm from the end, rise = polyfit slope x 0.010 (end-point difference < 3)."""
    es = e[idx]
    j = max(i for i in range(len(idx)) if es[-1] - es[i] >= P37_WINDOW_M - 1e-12)
    tail = idx[j:]
    et, Ft = e[tail], F[tail]
    if len(tail) >= 3:
        slope = float(np.polyfit(et - et.mean(), Ft, 1)[0])
    else:
        slope = float((Ft[-1] - Ft[0]) / (et[-1] - et[0]))
    return tail, slope * P37_WINDOW_M, float(Ft.mean())


def s1_windows(row, t, u, e, F, w_ref, v_max, lwa: bool, stop_at_loc=True):
    """S-1 window replay (spec 282.4 S-1, 285 P-S9-2, 314.1 C-S9-60-3): LEVEL samples, same-sample `u_applied`
    all >= 0 and mean >= 0.15 v_max else the window clears; LWa (419.2, meta mode `restart`) clears it while a
    re-approach is active; after a LOC the scan resumes after the next `INFO_LOC_REVOKED`. Returns the
    evaluations [(t_end, rise, tail_mean, t_tail_first)] and the last LOC (t_P = first tail sample, t_LOC).
    `stop_at_loc` False (true-value record pass): no LOC test, every window evaluation is kept."""
    ph = C.phase_at(row, t)
    active = _reapproach_active(row, t) if lwa else np.zeros(len(t), bool)
    revokes = sorted(tr for tr, _ in C.events_named(row, R.EVENT_LOC_REVOKED))
    win, evals, last = [], [], (None, None)
    resume_after = -np.inf
    for k in range(len(t)):
        if t[k] <= resume_after + R.CMP_TOL or ph[k] != "level":
            continue
        if active[k]:
            win = []
            continue
        uk = u[k]
        if not (np.all(uk >= -R.CMP_TOL) and uk.mean() >= P37_SPEED_FRACTION * v_max - R.CMP_TOL):
            win = []
            continue
        win.append(k)
        if e[win[-1]] - e[win[0]] < P37_WINDOW_M - 1e-12:
            continue
        tail, rise, mean_F = _tail_rise(e, F, win)
        evals.append((float(t[k]), rise, mean_F, float(t[tail[0]])))
        if stop_at_loc and mean_F >= P37_PLAUSIBILITY * w_ref and rise <= P37_RISE_MAX_N:
            last = (float(t[tail[0]]), float(t[k]))
            later = [tr for tr in revokes if tr >= t[k] - R.CMP_TOL]
            if not later:
                break
            resume_after = later[0]
            revokes = [tr for tr in revokes if tr > resume_after + R.CMP_TOL]
            win = []
    return evals, last


def _crawler_after(row, t_s):
    k = int(np.searchsorted(row.t_cr, t_s - R.CMP_TOL))
    return None if k >= len(row.t_cr) else float(row.cr[k])


def _loaded_min(row, evals, threshold_N):
    loaded = [(ev[1], ev[0]) for ev in evals if (c := _crawler_after(row, ev[0])) is not None and c > threshold_N]
    if not loaded:
        return None, None
    rise, t_end = min(loaded)
    return rise, t_end


def p3_7(row, params, judged=True) -> dict:
    """CD-4 P3-7 (spec 284 table, defined in 314.1 C-S9-60-3; path 2 had no definition): reading-based S-1
    windows (`record.npz` `meas.stroke` mean, sum p_h A_p - p_r A_ann); judged on the windows whose end crawler
    true normal (first 1 ms `scm_crawler_normal_N` sample at or after the end) > 0.01 x mass_scale x W_ref (spec
    422.6, rev25 R25-2 2 (나); S-1 plausibility stays 0.85 W_ref): min rise >= 4 kN;
    none -> "부담 창 없음" (pass). Reconstruction gate: t_P, t_LOC = meta `c2_soil.t_P_s`, `t_loc_s` within
    1e-6 s (t_P = first sample of the 10 mm tail, which reproduces the meta). Records: > 1 kN and > 0.05 W_ref
    minima, and the true-value version (`F_cyl`, `s_motor`, up to the LOC time)."""
    out = {"clause": "spec 284 P3-7 / 314.1 C-S9-60-3 (CD-4: 명세 원문 정의로 계산)",
           "verdict_role": "judged" if judged else "record"}
    soil = row.result.get("c2_soil") or {}
    rp = row.folder / "record" / "record.npz"
    w_ref = soil.get("W_ref_N")
    mode = ((row.result.get("controller_meta") or {}).get("liftoff_window_reapproach") or {}).get("mode")
    out["lw_mode"] = mode
    if not rp.exists() or w_ref is None or row.cr is None:
        out.update(verdict="indeterminate", **{REASON_KEY: REASON_INPUT_MISSING + " (record.npz / c2_soil.W_ref_N)"})
        return out
    lw = str(mode).lower() if mode is not None else None
    if lw not in LW_RESTART_MODES and mode not in LW_OFF_MODES:
        out.update(verdict="indeterminate", **{REASON_KEY: f"S-1 창 규칙 {mode!r} 재구성 미구현"})
        return out
    rec = np.load(rp)
    keys = set(rec.files)
    need = {"t", "u_applied", "meas.stroke", "meas.head_pressure", "meas.rod_pressure", "F_cyl", "s_motor"}
    if not need <= keys:
        out.update(verdict="indeterminate", **{REASON_KEY: REASON_INPUT_MISSING + f" ({sorted(need - keys)})"})
        return out
    head, ann = _cylinder_areas(CONTEXT.get("repo") or C._repo_of_tool())
    t = np.asarray(rec["t"], float)
    u = np.asarray(rec["u_applied"], float)
    e = np.asarray(rec["meas.stroke"], float).mean(axis=1)
    F = (np.asarray(rec["meas.head_pressure"], float) * head
         - np.asarray(rec["meas.rod_pressure"], float) * ann).sum(axis=1)
    lwa = lw in LW_RESTART_MODES
    w_ref = float(w_ref)
    v_max = params["v_max_m_s"]
    evals, (tp, tl) = s1_windows(row, t, u, e, F, w_ref, v_max, lwa)
    gate_p = _same_time(tp, soil.get("t_P_s"))
    gate_l = _same_time(tl, soil.get("t_loc_s"))
    scale = _mass_scale(row)
    thr = P37_LOADED_FRACTION * scale * w_ref   # rev25 R25-2 2 (나): spec 422.6 W_plant = mass_scale x W_ref
    out.update(reconstruct_ok=gate_p and gate_l, t_P_rec_s=tp, t_loc_rec_s=tl,
               t_P_meta_s=soil.get("t_P_s"), t_loc_meta_s=soil.get("t_loc_s"), n_windows=len(evals),
               loaded_threshold_N=thr, W_ref_N=w_ref, mass_scale=scale,
               interval="LEVEL S-1 창(LOC까지), 창 끝 크롤러 참 법선 > 0.01 x mass_scale x W_ref")
    if not out["reconstruct_ok"]:
        out.update(verdict="indeterminate", **{REASON_KEY: "P3-7 재구성 관문 불일치 (t_P·t_LOC vs meta > 1e-6 s)"})
        return out
    rise, t_end = _loaded_min(row, evals, thr)
    out.update(rise_min_loaded_N=rise, t_end_at_min_s=t_end,
               crawler_at_end_N=None if t_end is None else _crawler_after(row, t_end))
    for name, abs_N, frac in P37_RECORD_THRESHOLDS:
        r2, _ = _loaded_min(row, evals, abs_N if abs_N is not None else frac * w_ref)
        out[f"rise_min_{name}_N_record"] = r2
    e_true = np.asarray(rec["s_motor"], float).mean(axis=1)
    F_true = np.asarray(rec["F_cyl"], float).sum(axis=1)
    cut = t <= (tl if tl is not None else np.inf) + R.CMP_TOL
    ev_true, _ = s1_windows(row, t[cut], u[cut], e_true[cut], F_true[cut], w_ref, v_max, lwa, stop_at_loc=False)
    out["rise_min_loaded_true_N_record"], _ = _loaded_min(row, ev_true, thr)
    if rise is None:
        out.update(within=True, verdict="pass", note="부담 창 없음 (통과로 셈)")
    else:
        out["within"] = R.ge(rise, P37_RISE_MIN_N)
        out["verdict"] = "pass" if out["within"] else "fail"
    if not judged:
        out["record_verdict"] = out["verdict"]
        out["verdict"] = "record"
    return out


def _mass_scale(row) -> float:
    """Run argument `mass_scale` (`result.json` `args.mass_scale`); absent -> 1 (rev25 CD-4)."""
    v = (row.result.get("args") or {}).get("mass_scale")
    return 1.0 if v is None else float(v)


def _same_time(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= P37_GATE_TOL_S


# ============================================================================= CD-4 / CD-5 P3 items
P3_KEYS = tuple(f"P3-{k}" for k in range(1, 10)) + ("FAULT0",)


def add_p3_7(items, keys, row, params, judged=True):
    items["P3-7"] = p3_7(row, params, judged=judged)
    if judged and "P3-7" not in keys and not _safe_stop_row(items):
        keys.append("P3-7")
    elif _safe_stop_row(items):
        items["P3-7"]["record_only"] = "soil-guard stop row: grade by spec 427.9 conditions 1-5 (rev19 R19-1)"


def _safe_stop_row(items) -> bool:
    return isinstance(items.get("safe_stop_427_9"), dict)


def apply_ready_none(items, keys, row) -> dict | None:
    """CD-5: no first READY. P3-1 READY-window condition -> 해당 없음, the departure recontact condition judged;
    P3-4 / P3-5 -> 해당 없음; P3-6 judged -> 미달 (already), recorded -> value 해당 없음; READY <= 120 s -> 미달.
    Record-only items (427.9 branch, recorded P3-6) keep their verdict and get the 해당 없음 value text."""
    if C.first_phase_time(row, "ready") is not None:
        return None
    applied = []
    p31 = items.get("P3-1")
    if isinstance(p31, dict):
        strict = [ev for ev in p31.get("recontacts") or [] if ev.get("class") == "strict_fail"]
        p31["ready_window_condition"] = NA_NO_READY
        if p31.get("verdict") not in ("record",) and not p31.get("record_only"):
            p31["verdict"] = "fail" if strict else ("flag" if p31.get("flags") else "pass")
            p31.pop("reason", None)
        p31[REASON_KEY] = "CD-5: READY 조건 해당 없음(READY 없음), 첫 이탈 뒤 재접촉 조건만 판정"
        applied.append("P3-1")
    for k in ("P3-4", "P3-5"):
        it = items.get(k)
        if isinstance(it, dict):
            it["value_cd5"] = NA_NO_READY
            if not it.get("record_only") and it.get("verdict") != "record":
                it["verdict"] = "na"
            it.pop("reason", None)
            it[REASON_KEY] = NA_NO_READY
            applied.append(k)
    it = items.get("P3-6")
    if isinstance(it, dict):
        if it.get("judged") and not it.get("record_only"):
            it["verdict"] = "fail"
            it[REASON_KEY] = "CD-5: READY 없음 -> 미달"
        else:
            it["value_cd5"] = NA_NO_READY
            it[REASON_KEY] = NA_NO_READY
        applied.append("P3-6")
    if isinstance(items.get("G6-6"), dict):
        items["G6-6"][REASON_KEY] = "CD-5: READY 없음 -> 미달"
    return {"clause": "CD-5", "applied_to": applied}


def scm_grade_guard(items, keys) -> dict | None:
    """CD-4: an SCM row whose P3 grade items without 해당 없음 / 기록 are 0 is 판정 불가 (원판 9.3)."""
    graded = [k for k in keys if k in P3_KEYS and items.get(k, {}).get("verdict") not in ("na", "record")]
    if _safe_stop_row(items) or graded:
        return None
    guard = {"verdict": "indeterminate", "clause": "CD-4 last sentence",
             REASON_KEY: "해당 없음·기록을 뺀 P3 등급 항목 0"}
    items["CD-4_grade_guard"] = guard
    keys.append("CD-4_grade_guard")
    return guard


# ============================================================================= rev25 CD-4 P3-6 (decision 98 1)
P36_SOFT_SETS = ("J1", "J2", "S1")
P36_PAD_B = "dwg_rear250"
P36_SLOPE_S, P36_SOFT_REAR_S, P36_FLAT_S = 120.0, 100.0, 90.0
REAR_LEGS = ("RL", "RR")


def _patch_sets(text) -> dict | None:
    """`soil_patch` "LEG:SET" entries (comma separated; legs joined by '+' allowed) -> {leg: set}; None if unreadable."""
    out = {}
    if text in (None, ""):
        return out
    for part in str(text).split(","):
        if ":" not in part:
            return None
        legs, soil = part.split(":", 1)
        for leg in legs.replace("/", "+").split("+"):
            if leg.strip() not in R.LEGS:
                return None
            out[leg.strip()] = soil.strip()
    return out


def p3_6_limit(row):
    """rev25 CD-4 P3-6 limit (spec 421.1, first matching line): floor slope (`floor_roll` or `floor_pitch` != 0)
    120 s; flat, pad type B (`pad_variant` = dwg_rear250) and both rear pads on J1 / J2 / S1 (`soil_patch` set where
    it covers the leg, else `soil`) 100 s; other flat 90 s. Returns (limit or None, basis)."""
    a = row.result.get("args") or {}
    if float(a.get("floor_roll") or 0.0) != 0.0 or float(a.get("floor_pitch") or 0.0) != 0.0:
        return P36_SLOPE_S, "421.1 ① 바닥 경사"
    patch = _patch_sets(a.get("soil_patch"))
    if patch is None:
        return None, f"soil_patch {a.get('soil_patch')!r} 읽기 불가"
    rear = [patch.get(leg, a.get("soil")) for leg in REAR_LEGS]
    if a.get("pad_variant") == P36_PAD_B and all(s in P36_SOFT_SETS for s in rear):
        return P36_SOFT_REAR_S, f"421.1 ② 평지·패드 B·후방 {rear}"
    return P36_FLAT_S, "421.1 ③ 그 밖 평지"


def set_p3_6(items, keys, row, judged: bool):
    """rev25 CD-4: P3-6 = first READY after the closed-loop start <= the 421.1 limit; judged on C-5 SCM rows (and the
    C-2 S rows as before), recorded on C-3 G6 / C-4 / C-8 / PS-c base rows and on 427.9 safe-stop rows."""
    limit, basis = p3_6_limit(row)
    record_only = (items.get("P3-6") or {}).get("record_only")
    if limit is None:
        it = {"clause": "CD-4 P3-6 (spec 421.1)", "verdict": "indeterminate", "judged": judged, "limit_basis": basis,
              REASON_KEY: REASON_INPUT_MISSING + f" ({basis})"}
    else:
        it = C.ready_item(row, limit, f"CD-4 P3-6 READY <= {limit:g} s (spec 421.1)", judged=judged)
        it["limit_basis"] = basis
        it["interval"] = f"폐루프 시작 ~ 첫 READY, 한계 {limit:g} s"
    if record_only:
        it["record_only"] = record_only
    items["P3-6"] = it
    graded = judged and not _safe_stop_row(items)
    if graded and "P3-6" not in keys:
        keys.append("P3-6")
    elif not graded and "P3-6" in keys:
        keys.remove("P3-6")


# ============================================================================= rev25 CD-11 C-3 G6 correspondence
def g6_split(items, keys, row, graded: bool):
    """rev25 CD-11 G6 table: G6-6 = no FAULT and READY reached; `READY_le_120s` = first READY <= 120 s after the
    closed-loop start (separate). On the C-3 G6 rows both are grade items (FAULT0 becomes a record there); on
    C-4 / C-8 they are record values; on a 427.9 safe-stop row they are records."""
    fault = C.fault_present(row)["any"]
    t_R = C.first_phase_time(row, "ready")
    rel = None if t_R is None else t_R - row.loop_start
    items["G6-6"] = {"clause": "CD-11 G6 대응표 G6-6 (FAULT 없음 그리고 READY 도달)", "fault": fault,
                     "ready_reached": t_R is not None, "verdict": "pass" if (not fault and t_R is not None) else "fail"}
    items["READY_le_120s"] = {"clause": "CD-11 G6 대응표 READY_le_120s (폐루프 시작 기준 첫 READY <= 120 s)",
                              "t_ready_rel_s": rel, "interval": "폐루프 시작 ~ 첫 READY, 한계 120 s",
                              "verdict": "pass" if (rel is not None and R.le(rel, R.G6_READY_S)) else "fail"}
    if t_R is None:
        for k in ("G6-6", "READY_le_120s"):
            items[k][REASON_KEY] = "CD-5: READY 없음 -> 미달"
    safe = _safe_stop_row(items)
    for k in ("G6-6", "READY_le_120s"):
        if safe:
            items[k]["record_only"] = "soil-guard stop row: grade by spec 427.9 conditions 1-5"
        if graded and not safe:
            if k not in keys:
                keys.append(k)
        elif k in keys:
            keys.remove(k)
    if graded and "FAULT0" in keys:
        keys.remove("FAULT0")
        items["FAULT0"]["cd11_role"] = "기록 (C-3: FAULT 없음은 G6-6 안)"


# ============================================================================= rev25 CD-11 gates, CD-1 J-P3 on C-1..C-3
def apply_rev25_row(bundle: str, row, items, keys, record_row: bool):
    """rev25: (1) CD-1 J-P3 is a grade item of the ③-on rows of every judged bundle C-1..C-5 (C-1..C-3 get it here;
    a record row keeps it as a record); (2) CD-11 gates (`identity`, `K1_class`, `R9-1`, `R11-4`, `T4-0`) leave the
    grade; a failing gate gets a stop (the bundle stops before judgement)."""
    import p2_kinds as K   # local import: p2_kinds imports this module's siblings only
    if bundle in ("C-1", "C-2", "C-3") and "J-P3" not in items:
        items["J-P3"] = K.jp3_item(row)
        if not record_row and items["J-P3"].get("verdict") != "na":
            keys.append("J-P3")
    for g in GATE_KEYS:
        if g in keys:
            keys.remove(g)
        it = items.get(g)
        if not isinstance(it, dict):
            continue
        it["cd11_class"] = CLASS_GATE
        failed = it.get("verdict") in ("indeterminate", "fail", "hold") or (
            g == "K1_class" and it.get("cls") == "indeterminate")
        if failed and not it.get("stop"):
            it["stop"] = f"CD-11 관문 실패 ({g}): " + str(it.get("reason") or it.get(REASON_KEY) or "판정 불가")[:200]


# ============================================================================= rev25 CD-8 SCM D8 values
def scm_d8_values(row, params) -> dict:
    """rev25 CD-8 8 (SCM row D8): (1) t_lift = t_lift,sus rule (CD-2 (a)) on the 1 ms crawler normal series that
    t_D uses (`scm_crawler_normal_N`); (2) min 1 ms true F_cyl after t_lift to the record end with leg and time;
    (3) last 5 s absolute max of the true deck roll / pitch (`step_series.npz` `roll_pitch_deg`, vs target) +
    0.02 deg mount; (4) `scm_pad_normal_N` <= 0 1 ms samples after t_lift."""
    tl = C.t_lift_sus_d29(row) if row.cr is not None else None
    out = {"clause": "CD-8 8 (SCM D8)", "t_lift_s": tl,
           "crawler_series": "step_series.npz scm_crawler_normal_N (t_D와 같은 계열)"}
    if tl is not None:
        sel = row.tF >= tl - R.CMP_TOL
        Fs = np.where(sel[:, None], row.F, np.inf)
        i, leg = np.unravel_index(int(np.argmin(Fs)), Fs.shape)
        out["min_after_t_lift"] = {"min_N": float(Fs[i, leg]), "leg": R.LEGS[leg], "t_s": float(row.tF[i])}
        selp = row.t_pad >= tl - R.CMP_TOL
        le0 = row.pad_n[selp] <= 0.0 + R.CMP_TOL
        out["pad_lift_samples"] = int(le0.sum())
        out["pad_lift_samples_per_leg"] = le0.sum(axis=0).astype(int).tolist()
    else:
        out["min_after_t_lift"] = None
        out["pad_lift_samples"] = None
    w0 = row.t_end - R.D8_LAST_WINDOW_S
    sel_a = row.t_att >= w0 - R.CMP_TOL
    val = float(np.max(np.abs(row.att[sel_a] - np.array(row.target_deg)))) if sel_a.any() else None
    out["end_attitude_with_mount_deg"] = None if val is None else val + R.D8_MOUNT_DEG
    out["end_attitude_window_s"] = [w0, row.t_end]
    return out


# ============================================================================= CD-6 T4 / T5 target rows
def apply_t45_targets(items, keys, row):
    """CD-6: T4-0 / T4 / T5 are graded only on the 18 rows of v5 rev6 3 (1-18); other C-5 rows 해당 없음."""
    if row.case in T45_TARGET_ROWS and row.engine == "l2b":
        for k in T45_KEYS:
            if k not in keys:
                keys.append(k)
        return
    for k in T45_KEYS:
        if k in keys:
            keys.remove(k)
        prev = items.get(k) or {}
        items[k] = {"verdict": "na", "clause": "CD-6 (v5 rev6 3 rows 1-18)", "value": NA_NOT_TARGET,
                    REASON_KEY: NA_NOT_TARGET,
                    "replay_record": {kk: prev.get(kk) for kk in ("verdict", "over_0p6kN") if kk in prev} or None}


# ============================================================================= CD-7 reasons
NEEDS_REASON = ("indeterminate", "hold", "na", "runner_unjudged")


def _reason_from(it: dict) -> str | None:
    for k in (REASON_KEY, "reason", "stop", "value_cd5", "value"):
        v = it.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()[:300]
    return None


def attach_reasons(rows) -> list:
    """CD-7: every 판정 불가 / 러너 미판정 / 해당 없음 / not-computable item and every row that is not a plain
    pass gets a one-line reason (`cd7_reason`, `cd7_row_reason`). Returns the items whose reason stayed empty."""
    empty = []
    for r in rows:
        bad = []
        for k, it in r["items"].items():
            if not isinstance(it, dict):
                continue
            if it.get("verdict") in NEEDS_REASON:
                rs = _reason_from(it)
                it[REASON_KEY] = rs or ""
                if not rs:
                    empty.append(f"{r['case']}: {k}")
                if rs and k in r["judged_keys"] and it.get("verdict") in ("indeterminate", "hold"):
                    bad.append(f"{k}: {rs}")
            for e in it.get("entries") or []:
                if e.get("verdict") in NEEDS_REASON and not e.get(REASON_KEY):
                    empty.append(f"{r['case']}: {k} / {e['item'][:60]}")
        if r["status"] in ("판정 불가", "기록 불완전"):
            r[ROW_REASON_KEY] = "; ".join(bad)[:500] or _first_stop(r) or ""
            if not r[ROW_REASON_KEY]:
                empty.append(f"{r['case']}: row")
        elif r["status"] == "미달":
            fails = [k for k in r["judged_keys"] if (r["items"].get(k) or {}).get("verdict") == "fail"]
            r[ROW_REASON_KEY] = "미달 항목: " + ", ".join(fails)
        else:
            r[ROW_REASON_KEY] = ""
    return empty


def _first_stop(r):
    for k, it in r["items"].items():
        if isinstance(it, dict) and it.get("stop"):
            return f"{k}: {it['stop']}"[:300]
    return None


# ============================================================================= CD-11 item list
SAFE_STOP_CONDITIONS = ("1_stop_reason_soil", "2_no_fault_stroke_end", "3_no_leg_lift_from_level_start",
                        "4_min_after_departure_ge_Fmin", "5_moving_le_180bar_saturation0")
RECORD_LIST_KEYS = ("D2", "P3-9", "J11_record") + P3_KEYS + G6_IDS + ("CD-8_record", "CD-9_record")


def clause_id(common_id: str, cls: str, g6_row: bool, table_line=None) -> str:
    """rev25 CD-11 clause id table."""
    if cls == CLASS_GATE:
        return "CD-11 관문"
    if cls == CLASS_RECORD:
        return "CD-11 기록"
    if table_line is not None:
        return f"CD-2 표 {table_line}줄"
    if g6_row and common_id in G6_IDS:
        return "CD-11 G6 대응표"
    if common_id in ("T4", "T5"):
        return "CD-6"
    if common_id in ("J11", "J-P3"):
        return "CD-1 ①"
    if common_id.startswith("E-"):
        return f"명세 426.3 {common_id}"
    if common_id.startswith("427.9-"):
        return f"명세 427.9 조건 {common_id.split('-')[-1]}"
    if common_id.startswith("P3-") or common_id == "FAULT0":
        return f"CD-4 {common_id}"
    return "CD-4 마지막 문장" if common_id == "CD-4_grade_guard" else "-"


def _entry_row(common_id, cls, path2, it, g6_row, method="재계산", table_line=None, verdict=None, reason=None):
    return {"common_id": common_id, "class": cls, "path2_item": path2,
            "clause_id": clause_id(common_id, cls, g6_row, table_line),
            "description": str((it or {}).get("clause") or (it or {}).get("definition") or "")[:160],
            "method": method, "interval": (it or {}).get("interval") or "",
            "verdict": (it or {}).get("verdict") if verdict is None else verdict,
            "reason": ((it or {}).get(REASON_KEY) or "") if reason is None else reason}


def _cd2_entries(it, g6_row, record_row):
    out = []
    for e in it.get("entries") or []:
        cls = CLASS_GRADED if (e["use"] in ("judged", "hold") and not record_row) else CLASS_RECORD
        out.append(dict(_entry_row(e.get("common_id") or e["item"], cls, f"CD-2/{e['item']}",
                                   {"clause": "CD-2 / 원 판정기 verify_S8C", "interval": e.get("interval")}, g6_row,
                                   method="재계산" if e["handling"] == "recalc" else "원 판정기 실행",
                                   table_line=None if cls == CLASS_RECORD else e.get("table_line"),
                                   verdict=e["verdict"],
                                   reason=e.get(REASON_KEY) or e.get("cd7_change_reason") or ""),
                        cd3_sub_id=e.get("cd3_sub_id"), cd2_table_line=e.get("table_line")))
    for name, key in (("t_lift 차 확인", "t_lift_check"), ("사건 창 끝 차 확인", "window")):
        blk = it.get(key)
        if isinstance(blk, dict) and (key != "window" or blk.get("diff_vs_judge_s") is not None):
            ok = blk.get("ok") if key == "t_lift_check" else "CD-3: computed" not in str(it.get("stop", ""))
            out.append(_entry_row(name, CLASS_GATE, f"CD-2/{key}", blk, g6_row, verdict="pass" if ok else "fail",
                                  reason="" if ok else "멈춤"))
    return out


def _safe_stop_entries(ss, g6_row):
    out = []
    for n, cond in enumerate(SAFE_STOP_CONDITIONS, start=1):
        v = (ss.get("conditions") or {}).get(cond)
        word = "pass" if v is True else ("fail" if v is False else "indeterminate")
        out.append(_entry_row(f"427.9-{n}", CLASS_GRADED, f"safe_stop_427_9.{cond}", ss, g6_row, verdict=word,
                              reason="" if v is not None else ", ".join(ss.get("missing_inputs") or []) or
                              "조건 계산 불가"))
    return out


def item_list(bundle: str, rows, record_bundle=False) -> dict:
    """rev25 CD-11: per row every item with its class (등급 항목 / 관문 / 기록), common id, path 2 name, clause id,
    description, method, interval, verdict and reason. CD-2 is expanded into the original judge items (case `*`
    items carry ` [case *]`), a 427.9 safe-stop row into 427.9-1..5. Each graded row needs >= 1 grade item
    (verdict other than 해당 없음); record rows (rule / earlier-revision record rows, record bundles) and the
    C-1 L1-R rows are exempt; the list has one entry per bundle row."""
    lst, problems = [], []
    g6_row = bundle == "C-3"
    for r in rows:
        record_row = record_bundle or r["status"] in ("기록 완료", "기록 불완전")
        entries, seen = [], set()
        for k in r["judged_keys"]:
            it = r["items"].get(k) or {}
            seen.add(k)
            if k == "CD-2":
                entries += _cd2_entries(it, g6_row, record_row)
            elif k == "safe_stop_427_9":
                entries += _safe_stop_entries(it, g6_row)
            else:
                cls = CLASS_RECORD if record_row else CLASS_GRADED
                entries.append(_entry_row(COMMON_ID.get(k, k), cls, k, it, g6_row,
                                          method="원 판정기 실행" if k in T45_KEYS else "재계산"))
        for k in ("T4", "T5", "J-P3"):   # 등급 항목 class even when 해당 없음 on this row
            it = r["items"].get(k)
            if isinstance(it, dict) and k not in seen:
                seen.add(k)
                entries.append(_entry_row(COMMON_ID.get(k, k), CLASS_RECORD if record_row else CLASS_GRADED, k, it,
                                          g6_row, method="원 판정기 실행" if k in T45_KEYS else "재계산"))
        for k in GATE_KEYS:
            it = r["items"].get(k)
            if isinstance(it, dict):
                seen.add(k)
                entries.append(_entry_row(COMMON_ID.get(k, k), CLASS_GATE, k, it, g6_row,
                                          method="원 판정기 실행" if k in T45_KEYS else "재계산"))
        for k in RECORD_LIST_KEYS:
            it = r["items"].get(k)
            if isinstance(it, dict) and k not in seen:
                entries.append(_entry_row(COMMON_ID.get(k, k), CLASS_RECORD, k, it, g6_row,
                                          verdict=it.get("record_verdict") or it.get("verdict")))
        graded = [x for x in entries if x["class"] == CLASS_GRADED and x["verdict"] not in ("na", "record")]
        outside = r.get("engine") == "l1r"   # C-1 L1-R record rows: outside the common block (scope sentence)
        if not record_row and not outside and not graded:
            problems.append(f"{r['case']}: 등급 항목 0")
        ent = {"row": r["case"], "status": r["status"], "record_row": record_row, "items": entries}
        if outside:
            ent["scope"] = "L1-R 기록 행(공통 블록 적용 밖, 앞 판 그대로)"
        lst.append(ent)
    if len(lst) != len(rows):
        problems.append(f"목록 행 {len(lst)} != 묶음 행 {len(rows)}")
    out = {"clause": "CD-11 (rev25)", "bundle": bundle, "rows": lst, "problems": problems}
    if problems:
        out["stop"] = "CD-11: " + "; ".join(problems)
    return out


# ============================================================================= CD-8 C-8 record values
C8A_TAG = ("Kc3", "VB")


def c8_values(row, items, params) -> dict:
    """rev25 CD-8 / 원판 7.4 record values of one O-C5 row; `missing` lists the absent ones (해당 없음 counts).
    F^a = per-leg minimum of the 1 ms true F_cyl from t_D to the record end, F^t = the same series in
    [t_D, t_D + 8 s) (each with its sample time); P3-5 on a rigid_base row = 해당 없음(rigid_base); D8 = SCM D8
    values (1)-(4); G6 = the eight gate values (G6-1..G6-5, G6-7 = the P3 values; G6-6 and READY_le_120s apart)."""
    res = row.result
    t_D = items["departure"]["t_D_s"]
    vals = {}
    vals["Fa_min_after_departure"] = _per_leg_min(row, row.F, t_D)
    vals["Ft_min_transient_8s"] = _per_leg_min(row, row.F, t_D, None if t_D is None else t_D + R.FMIN_REC_WINDOW_S)
    if (res.get("args") or {}).get("rigid_base") and isinstance(items.get("P3-5"), dict):
        items["P3-5"]["value_cd9"] = NA_RIGID_BASE
        items["P3-5"][REASON_KEY] = NA_RIGID_BASE + " (사용자 결정 100의 1)"
    full = items.get("Fmin_time_full") or {}
    vals["t_below_Fmin_s"] = full.get("t_below_Fmin_s")
    vals["t_below_Fmin_plus2k_s"] = full.get("t_below_Fmin_plus2k_s")
    p33 = items.get("P3-3") or {}
    vals["P3-3_within"] = None if p33.get("verdict") in (None, "indeterminate") else p33.get("verdict") == "pass"
    las = (res.get("controller_meta") or {}).get("liftoff_approach_slow")
    if isinstance(las, dict):   # block present: None = LAS-b did not start / end (a value, not a missing record)
        vals["las_start_s"] = las.get("start_s") if las.get("start_s") is not None else "시작 없음"
        vals["las_end_s"] = las.get("end_s") if las.get("end_s") is not None else "끝 없음"
        vals["las_end_reason"] = las.get("end_reason") if las.get("end_reason") is not None else "끝 사유 없음"
    else:
        vals["las_start_s"] = vals["las_end_s"] = vals["las_end_reason"] = None
    dec = (((res.get("controller_meta") or {}).get("slope_clearance_margin") or {}).get("order_gate") or {})
    vals["k1_decisions"] = dec.get("decisions")
    rc = items.get("R_c") or {}
    vals["R_c"] = rc.get("R_c")
    vals["crawler_attitude_deg"] = rc.get("crawler_attitude_deg")
    a = res.get("args") or {}
    vals["floor_deg"] = [a.get("floor_roll"), a.get("floor_pitch")]
    vals["crawler_kn_scale"] = _kn_scale(row)
    for k in P3_KEYS + ("G6-6", "READY_le_120s"):
        it = items.get(k)
        na = it.get("value_cd9") or it.get("value_cd5") if isinstance(it, dict) else None
        if not isinstance(it, dict) or (it.get("verdict") == "indeterminate" and not na):
            vals[k] = None
        else:
            vals[k] = na or it.get("record_verdict") or it.get("verdict")
    d8 = scm_d8_values(row, params)
    items["CD-8_D8"] = dict(d8, verdict="record")
    vals["D8_t_lift_s"] = d8["t_lift_s"]
    vals["D8_min_after_t_lift"] = d8["min_after_t_lift"]
    vals["D8_end_attitude_with_mount_deg"] = d8["end_attitude_with_mount_deg"]
    vals["D8_pad_lift_samples"] = d8["pad_lift_samples"]
    vals["G6"] = {gate: vals.get(cid) for gate, cid in G6_TABLE}
    missing = [k for k, v in vals.items() if v is None or (isinstance(v, list) and any(x is None for x in v))
               or (k == "G6" and any(x is None for x in v.values()))]
    return {"clause": "CD-8 / 원판 7.4 기록 항목 (rev25)", "values": vals, "missing": missing,
            "note": "D8 t_lift 계열 = step_series.npz scm_crawler_normal_N (t_D와 같은 계열); 강체 바닥 쪽 크롤러 "
                    "하중을 담는지는 판정서에 적는다"}


def _per_leg_min(row, series, t0, t1=None):
    """Per-leg minimum of a 1 ms series over [t0, t1) (t1 None = to the record end) and each minimum's time."""
    if t0 is None:
        return None
    sel = row.tF >= t0 - R.CMP_TOL
    if t1 is not None:
        sel &= row.tF < t1 - R.CMP_TOL
    if not sel.any():
        return None
    F = series[sel]
    tt = row.tF[sel]
    arg = F.argmin(axis=0)
    return {"min_N": F.min(axis=0).tolist(), "t_s": [float(tt[i]) for i in arg]}


def _kn_scale(row):
    argv = row.argv
    if "--crawler-kn-scale" in argv:
        i = argv.index("--crawler-kn-scale")
        try:
            return float(argv[i + 1])
        except (IndexError, ValueError):
            return None
    v = (row.result.get("args") or {}).get("crawler_kn_scale")
    return 1.0 if v is None else float(v)


def is_c8a(case: dict, row) -> bool:
    cid = str(case.get("criteria_id") or (case.get("r4368") or {}).get("criteria_id") or "")
    if cid == "C-8a":
        return True
    if cid == "C-8b":
        return False
    return all(tok in row.case for tok in C8A_TAG)


def c8a_s9_record(row, m74: dict) -> dict:
    """CD-8: C-8a S-9 -> not a stop, L-5 known limit, when m and the minimum leg equal this path's R3d output
    (K-10 numbers |a - b| <= 1e-9 max(1, |a|, |b|)); else 원판 7.4 stop."""
    out = {"clause": "CD-8 (사용자 결정 60 (A)·88)", "m_N": m74.get("m_N"),
           "min_leg": (m74.get("per_leg") or {}).get("min_leg")}
    ref = _r3d_c8_row(row.case)
    if ref is None:
        out.update(r3d_equal=False, stop="S-9 (CD-8: R3d C-8 출력 없음 -> 원판 7.4 멈춤)")
        return out
    rm = (ref.get("items") or {}).get("m_7_4") or {}
    a, b = out["m_N"], rm.get("m_N")
    same_m = a is not None and b is not None and abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))
    same_leg = out["min_leg"] == (rm.get("per_leg") or {}).get("min_leg")
    out.update(r3d_m_N=b, r3d_min_leg=(rm.get("per_leg") or {}).get("min_leg"), r3d_equal=same_m and same_leg)
    if not out["r3d_equal"]:
        out["stop"] = "S-9 (CD-8: m 또는 최소 다리가 R3d와 다름 -> 원판 7.4 멈춤)"
    else:
        out["known_limit"] = "L-5 (S-9 처리됨: 사용자 결정 60 (A)·88, 멈춤 목록 밖)"
    return out


def _r3d_c8_row(case_name):
    p = CONTEXT.get("r3d_c8")
    if not p or not Path(p).exists():
        return None
    doc = json.loads(Path(p).read_text(encoding="utf-8"))
    return next((r for r in doc.get("rows") or [] if r.get("case") == case_name), None)


# ============================================================================= CD-9 C-4 record status
def c4_record(row, items) -> dict:
    """CD-9: values needed per C-4 row: P3-1..P3-9 / FAULT0 (해당 없음 included), t_D, per-leg min cylinder
    force after departure with its leg and time, run R_c. rigid_base rows: P3-5 = 해당 없음(rigid_base)."""
    rigid = (row.result.get("args") or {}).get("rigid_base")
    if rigid and isinstance(items.get("P3-5"), dict):
        items["P3-5"]["value_cd9"] = NA_RIGID_BASE
        items["P3-5"][REASON_KEY] = NA_RIGID_BASE + " (사용자 결정 88)"
    t_D = (items.get("departure") or {}).get("t_D_s")
    p33 = items.get("P3-3") or {}
    vals = {"t_D_s": t_D, "R_c": (items.get("R_c") or {}).get("R_c"),
            "min_after_departure": None if p33.get("min_N") is None else
            {"min_N": p33["min_N"], "min_t_s": p33.get("min_t_s"), "min_leg": p33.get("min_leg")}}
    for k in P3_KEYS:
        it = items.get(k)
        if not isinstance(it, dict):
            vals[k] = None
        elif it.get("value_cd9") or it.get("value_cd5"):
            vals[k] = it.get("value_cd9") or it.get("value_cd5")
        elif it.get("verdict") == "indeterminate":
            vals[k] = None
        else:
            vals[k] = it.get("record_verdict") or it.get("verdict")
    missing = [k for k, v in vals.items() if v is None]
    status = "기록 완료" if not missing else "기록 불완전"
    out = {"clause": "CD-9", "rigid_base": rigid, "values": vals, "missing": missing, "record_status": status,
           "verdict": "record" if not missing else "indeterminate"}
    out[REASON_KEY] = "" if not missing else "기록 값 없음: " + ", ".join(missing)
    return out
