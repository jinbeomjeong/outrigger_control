"""Build the input definition JSON for paper figures F1 (operating-range diagram) and F2 (soft-slope
verdict map). Reads result JSON only (no simulation).

Inputs:  rev85/finB2_harness_rejudged.json (suite slope, 177), rev85/finB2_h9.json (suite h9, 36)
Output:  rev85/evidence/fig_F1F2_spec.json (read by 09_paper/figures/scripts/figF1_*.py, figF2_*.py)
Usage (python-dev):
  python -I -B 04_scripts/03_control/s9/evidence/build_fig_spec.py <project_root> <out_json>
"""
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
REV = ROOT / "06_analysis" / "02_control" / "s9" / "rev85"
F_SLOPE = REV / "finB2_harness_rejudged.json"
F_H9 = REV / "finB2_h9.json"
SPEC = "00_docs/04_control/s6_control_spec.md"

# --- case definition (04_scripts/03_control/s9/s9_soil_slope.py SLOPES_DEG, REANCHOR_SLOPES_DEG, _scaled_slope)
SLOPES_DEG = {
    "flat": (0.0, 0.0), "nose_down": (0.0, 3.2), "nose_up": (0.0, -3.2),
    "roll_pos": (4.4, 0.0), "roll_neg": (-4.4, 0.0), "edge_nd": (2.2, 1.6),
    "edge_nu": (2.2, -1.6), "rpB": (2.7355, 1.7592),
}
REANCHOR_SLOPES_DEG = {"nose_down": (0.0, 3.2), "nose_down_2p8": (0.0, 2.8)}
DIR_KO = {
    "flat": "평지", "nose_down": "앞내림", "nose_up": "앞들림",
    "roll_pos": "오른쪽(오른쪽 낮음)", "roll_neg": "왼쪽(왼쪽 낮음)",
    "edge_nd": "대각 앞내림(오른쪽 낮음)", "edge_nu": "대각 앞들림(오른쪽 낮음)",
    "rpB": "대각 앞내림 검증 경계점(rpB)",
}
SOFT = ("J1", "J2", "S1")
GUARD_MM = 682.8
H6_STROKE_MM = 23.0
GAP_MIN_MM = 25.0
H6_GAP_SLOPE_MM = 15.0
H6_GAP_FLAT_MM = 13.0
H6_READY_SLOPE_S = 31.0
H6_READY_FLAT_S = 17.0
READY_SLOPE_MAX_S = 120.0


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ready_limit(soil, pad, flat):
    if not flat:
        return READY_SLOPE_MAX_S
    if soil in SOFT and pad == "B":
        return 100.0
    return 90.0


def parse_id(cid):
    parts = cid.split("|")
    group, soil, pad, level, name = parts[:5]
    extra = parts[5:]
    k = None
    direction = name
    if "@k" in name:
        direction, ks = name.split("@k")
        k = float(ks)
    reanchor = group == "H4"
    if reanchor:
        if name == "nose_down_2p8":
            direction, k = "nose_down", 0.875
            roll, pitch = REANCHOR_SLOPES_DEG["nose_down_2p8"]
        else:
            roll, pitch = SLOPES_DEG[name]
            k = 1.0
    elif k is not None:
        r0, p0 = SLOPES_DEG[direction]
        roll, pitch = round(k * r0, 4), round(k * p0, 4)
    else:
        roll, pitch = SLOPES_DEG[name]
        k = 0.0 if name == "flat" else 1.0
    rc = abs(roll) / 4.4 + abs(pitch) / 3.2
    return dict(group=group, soil=soil, pad=pad, auger=level, direction=direction,
                direction_ko=DIR_KO[direction], k=k, floor_roll_deg=roll, floor_pitch_deg=pitch,
                R_c_floor=round(rc, 4), reanchor=reanchor, extra=extra, name=name)


def fail_kind(r):
    if r["verdict"] != "fail":
        return None
    ss = r.get("soil_stop")
    if isinstance(ss, dict):
        if ss.get("stop_with_crawler_loaded"):
            return "soil_stop_with_crawler_loaded"
        return "soil_stop_conditions_not_met"
    return "judged_fail"


def h6(rec, p):
    """Spec 432.4 H-6 (432.4.5 stroke +23 mm, 432.4.4 flat gap -13 mm, 432.4.7 slope gap -15 mm,
    READY +17 s flat / +31 s slope). Soft J1/J2/S1 pass rows only (432.4.5.1 decision (ga))."""
    if p["soil"] not in SOFT or rec["verdict"] != "pass":
        return dict(applies=False, boundary=False, reasons=[])
    flat = p["direction"] == "flat"
    reasons = []
    sm = GUARD_MM - rec["max_stroke_mm"]
    if sm < H6_STROKE_MM:
        reasons.append("stroke")
    gm = None
    if rec.get("rut_ready_mm") is not None:
        gm = rec["rut_ready_mm"] - GAP_MIN_MM
        if gm < (H6_GAP_FLAT_MM if flat else H6_GAP_SLOPE_MM):
            reasons.append("gap")
    lim = ready_limit(p["soil"], p["pad"], flat)
    if rec.get("t_ready_s") is not None and rec["t_ready_s"] + (H6_READY_FLAT_S if flat else H6_READY_SLOPE_S) > lim:
        reasons.append("ready")
    return dict(applies=True, boundary=bool(reasons), reasons=reasons,
                stroke_margin_mm=round(sm, 2), gap_margin_mm=None if gm is None else round(gm, 2),
                ready_limit_s=lim)


CHRONO_PAIRS = {
    "H9|J1|B|top|roll_neg@k0.6": ("X6-rb2", "pass"),
    "H9|J1|B|top|roll_neg@k0.65": ("X6-rb", "stroke_limited_stop"),
    "H9|J1|B|top|roll_pos@k0.6": ("X6-rp2", "fail(P3-5)"),
    "H3|J1|B|top|roll_pos@k0.5": ("X6-rp3", "pass"),
    "H3|J1|B|top|roll_pos@k0.875": ("X6-rp-sa (final) / X4-rp (pre-SGS)", "fail+stop_with_crawler_loaded / fail"),
    "H9|J1|B|top|roll_pos@k0.875": ("X6-rp-sa (final) / X4-rp (pre-SGS)", "fail+stop_with_crawler_loaded / fail"),
    "H3|J1|B|top|nose_down@k0.875": ("X4-nd (final-equivalent, REANCHOR on)", "pass"),
    "H4|J1|B|top|nose_down_2p8": ("X4-nd (final-equivalent, REANCHOR on)", "pass"),
    "H3|J1|B|top|edge_nd@k0.875": ("X4-ed (final-equivalent)", "pass"),
    "H3|J1|B|top|roll_pos@k0.75": ("C-3 (pre-SGS)", "stroke_limited_pass(pre-SGS)"),
    "H9|J1|B|top|roll_pos@k0.75": ("C-3 (pre-SGS)", "stroke_limited_pass(pre-SGS)"),
    "H4|G1|B|top|nose_down": ("C-1 (final-equivalent, REANCHOR on)", "pass"),
    "H1|J1|A|top|roll_pos": ("C-2 (pre-SGS)", "pass, P3-7 record fail(pre-SGS)"),
    "H4|J1|A|top|nose_down": ("C-4 (pre-SGS, REANCHOR on)", "fail FAULT_LIFT_STROKE_LIMIT(pre-SGS)"),
    "H1|J1|B|top|flat": ("B0 P3b_J1_B_top_Fs4 (final)", "pass"),
    "H1|J2|B|top|flat": ("P3b_J2_B_top_Fs4 (final)", "pass"),
}


def build_records(path, suite, src_rel):
    d = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for r in d["records"]:
        if r["suite"] != suite:
            continue
        p = parse_id(r["id"])
        h = h6(r, p)
        cp = CHRONO_PAIRS.get(r["id"])
        out.append({
            "id": r["id"], "source": src_rel, "suite": suite, "candidate": r["candidate"],
            "group": p["group"], "soil": p["soil"], "pad": p["pad"], "auger": p["auger"],
            "direction": p["direction"], "direction_ko": p["direction_ko"], "k": p["k"],
            "floor_roll_deg": p["floor_roll_deg"], "floor_pitch_deg": p["floor_pitch_deg"],
            "R_c_floor": p["R_c_floor"], "reanchor": p["reanchor"],
            "verdict": r["verdict"], "failed_rows": r["failed_rows"], "fail_kind": fail_kind(r),
            "final_phase": r["final_phase"],
            "max_stroke_reading_mm": round(r["max_stroke_mm"], 2),
            "rut_ready_mm": None if r.get("rut_ready_mm") is None else round(r["rut_ready_mm"], 2),
            "t_ready_s": None if r.get("t_ready_s") is None else round(r["t_ready_s"], 1),
            "min_force_after_off_kN": None if r.get("min_force_kN") is None else round(r["min_force_kN"], 2),
            "h6": h,
            "chrono_pair": None if cp is None else {"case": cp[0], "chrono_verdict": cp[1]},
            "hash": r["hash"],
        })
    return out, d


slope, d_slope = build_records(F_SLOPE, "slope", "06_analysis/02_control/s9/rev85/finB2_harness_rejudged.json")
h9, d_h9 = build_records(F_H9, "h9", "06_analysis/02_control/s9/rev85/finB2_h9.json")
assert len(slope) == 177, len(slope)
assert len(h9) == 36, len(h9)

# --- checks against spec 432.4.8 (M1)
soft_pass = [r for r in slope if r["soil"] in SOFT and r["verdict"] == "pass"]
bnd = [r for r in soft_pass if r["h6"]["boundary"]]
chk = {
    "verdicts_slope": dict(Counter(r["verdict"] for r in slope)),
    "pass_by_class": {"rigid": sum(r["verdict"] == "pass" and r["soil"] == "rigid" for r in slope),
                      "G1": sum(r["verdict"] == "pass" and r["soil"] == "G1" for r in slope),
                      "soft": len(soft_pass)},
    "h6_boundary_n": len(bnd),
    "h6_boundary_by_soil_pad": dict(Counter(f"{r['soil']}{r['pad']}" for r in bnd)),
    "h6_boundary_by_group": dict(Counter(r["group"] for r in bnd)),
    "h6_boundary_reasons": dict(Counter("+".join(r["h6"]["reasons"]) for r in bnd)),
    "h6_boundary_ids": [r["id"] for r in bnd],
    "spec_432_4_8_expected": {"n": 17, "soil_pad": {"J1A": 3, "J1B": 5, "J2A": 2, "J2B": 3, "S1A": 4},
                              "group": {"H1": 5, "H2": 4, "H3": 7, "H4": 1},
                              "pass_by_class": {"rigid": 10, "G1": 28, "soft": 56}},
    "verdicts_h9": dict(Counter(r["verdict"] for r in h9)),
    "h9_h6_boundary_ids": [r["id"] for r in h9 if r["h6"]["boundary"]],
}
exp = chk["spec_432_4_8_expected"]
chk["match_spec_432_4_8"] = (chk["h6_boundary_n"] == exp["n"] and chk["h6_boundary_by_soil_pad"] == exp["soil_pad"]
                             and chk["h6_boundary_by_group"] == exp["group"] and chk["pass_by_class"] == exp["pass_by_class"])

# --- H3 vs H9 duplicate cells (spec 430.2: k 0.75 / 0.875 roll_pos same slopes, R9-1)
by_cell = {}
dups = []
for r in slope:
    if r["group"] == "H3" and r["direction"] == "roll_pos":
        by_cell[(r["soil"], r["pad"], r["k"])] = r
for r in h9:
    o = by_cell.get((r["soil"], r["pad"], r["k"]))
    if o is not None and r["direction"] == "roll_pos":
        dups.append({"h3": o["id"], "h9": r["id"], "same_verdict": o["verdict"] == r["verdict"],
                     "stroke_diff_mm": round(r["max_stroke_reading_mm"] - o["max_stroke_reading_mm"], 3),
                     "same_hash": o["hash"] == r["hash"]})
chk["h3_h9_duplicates"] = dups

# --- F2 layout
ROWS = [("rigid", "B", "top")]
for soil in ("G1", "J1", "J2", "S1"):
    ROWS += [(soil, "B", "top"), (soil, "B", "bottom"), (soil, "A", "top")]


def col_key(r):
    d, k = r["direction"], r["k"]
    if r["reanchor"]:
        return f"RA:{d}@k{k:g}"
    if d in ("flat", "rpB"):
        return d
    return f"{d}@k{k:g}"


COLS = [("flat", "평지", "flat", 0.0)]
for d, ks in (("nose_down", (0.5, 0.75, 0.875, 1.0)), ("edge_nd", (0.5, 0.75, 0.875, 1.0)),
              ("roll_pos", (0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.875, 1.0)),
              ("roll_neg", (0.6, 0.65, 0.7, 0.75, 0.8, 0.875, 1.0)),
              ("nose_up", (1.0,)), ("edge_nu", (1.0,))):
    for k in ks:
        COLS.append((f"{d}@k{k:g}", DIR_KO[d], d, k))
COLS.append(("rpB", DIR_KO["rpB"], "rpB", None))
for d, k in (("nose_down", 0.875), ("nose_down", 1.0), ("nose_up", 1.0)):
    COLS.append((f"RA:{d}@k{k:g}", DIR_KO[d] + " REANCHOR 켬(H4)", d, k))

cells = defaultdict(list)
for r in slope + h9:
    cells[(f"{r['soil']}|{r['pad']}|{r['auger']}", col_key(r))].append(r["id"])
row_keys = [f"{s}|{p}|{a}" for s, p, a in ROWS]
col_keys = [c[0] for c in COLS]
unplaced = [ids for (rk, ck), ids in cells.items() if rk not in row_keys or ck not in col_keys]
assert not unplaced, unplaced


def col_angle(d, k):
    if d == "rpB":
        return SLOPES_DEG["rpB"]
    r0, p0 = SLOPES_DEG[d]
    if d == "nose_down" and k == 0.875:
        return (0.0, 2.8)
    return (round(k * r0, 4), round(k * p0, 4))


columns = []
for key, ko, d, k in COLS:
    ang = col_angle(d, k if k is not None else 1.0)
    columns.append({"key": key, "direction": d, "label_ko": ko, "k": k,
                    "floor_deg": list(ang), "R_c_floor": round(abs(ang[0]) / 4.4 + abs(ang[1]) / 3.2, 4),
                    "reanchor": key.startswith("RA:"),
                    "group_label": ko.split(" REANCHOR")[0] if not key.startswith("RA:") else "REANCHOR 켬(H4)"})
rows = []
SOIL_KO = {"rigid": "강체", "G1": "G1 다짐 자갈", "J1": "J1(판정 토양)", "J2": "J2", "S1": "S1"}
for s, p, a in ROWS:
    rows.append({"key": f"{s}|{p}|{a}", "soil": s, "pad": p, "auger": a,
                 "label_ko": f"{SOIL_KO[s]} · 패드 {p} · 오거 {'상단' if a == 'top' else '하단'}",
                 "soft": s in SOFT})
grid = []
for rk in row_keys:
    for ck in col_keys:
        ids = cells.get((rk, ck))
        if ids:
            grid.append({"row": rk, "col": ck, "ids": ids, "primary": ids[0]})

spec = {
    "schema": "fig_F1F2_spec/1",
    "created": "2026-10-31",
    "author": "control-expert",
    "purpose": "논문 그림 F1(운용 범위 다이어그램)·F2(연약 경사 판정 지도)의 입력 정의. python-expert가 그린다. 값은 모두 아래 원본 파일·명세 절에서 읽었고 새 계산은 R_c 환산·H-6 규칙 적용(JSON 후처리)뿐이다.",
    "conventions": {
        "axes": "x = floor roll φ [deg], y = floor pitch θ [deg]",
        "sign": "θ > 0 = 앞내림(nose down). 바닥 roll φ > 0 = 왼쪽 들림 = 오른쪽 낮음(s9_soil_slope.py SLOPES_DEG docstring). 그래서 roll_pos = '오른쪽', roll_neg = '왼쪽'(명세 430.3.6 표기).",
        "coordinates": "점 좌표는 바닥 경사(하네스·Chrono 입력)다. 운용 시작 조건 마름모는 크롤러로 선 IMU 자세(φ_g, θ_g)에 대한 식이고, 크롤러 정착이 바닥보다 수십분의 1도 더 기운다(예: X4-nd 바닥 2.8° → 정착 3.034°, C-1 3.2° → 3.543°). 그림에는 바닥 좌표를 쓰고 캡션에 이 차이를 적는다.",
        "R_c": "R_c = |φ|/4.4° + |θ|/3.2°(운용 시작 조건 마름모 비율). R_c_floor는 바닥 경사로 계산한 명목값이다. 정착 자세로 잰 SL-2 R_c는 최종 하네스 JSON에 저장돼 있지 않아(키 없음) 쓰지 않았다. Chrono 점은 명세에 적힌 SL-2 값을 settle_R_c로 따로 둔다.",
        "R_c_to_angle": "하네스 H3·H9는 _scaled_slope(direction, k) = round(k·roll_k1, 4), round(k·pitch_k1, 4)이고 k1 방향 값은 nose_down (0, 3.2), roll_pos (4.4, 0), roll_neg (−4.4, 0), edge_nd (2.2, 1.6)이다. 이 방향들은 k1에서 R_c = 1이라 k = R_c다. 예: 왼쪽 R_c 0.6 → −2.64°, 오른쪽 R_c 0.5 → +2.2°, 앞내림 0.875 → 2.8°, 대각 0.875 → (1.925, 1.4)°. 출처 04_scripts/03_control/s9/s9_soil_slope.py 142~154, 383~385행, 명세 430.2.",
        "verdict_classes": {"pass": "통과", "stroke_limited_stop": "안전 종료(SGS 토양 가드 정지, 427.9·427.12.5)", "fail": "실패"},
        "feedback_and_units": "판정 분류 자료뿐이라 되먹임 부호·이산화 해당 없음. 제어기는 R8 C2 10 Hz(T_s 0.1 s, 출력 지연 1주기) 최종 프리셋(SGS any_loc + R4c30 + L1gs + DSb75), 하네스 H4만 REANCHOR 켬. 행정 mm, 시간 s(루프 기준), 힘 kN, 각 deg.",
    },
    "inputs": {
        "slope_177": {"path": "06_analysis/02_control/s9/rev85/finB2_harness_rejudged.json", "sha256": sha(F_SLOPE),
                      "suite": "slope", "note": "settle v2 재판정본(meta.settle_rejudge). suite h6 32행은 이 그림에서 뺐다(평지 운용 중량 감도)."},
        "h9_36": {"path": "06_analysis/02_control/s9/rev85/finB2_h9.json", "sha256": sha(F_H9), "suite": "h9"},
        "case_definition": "04_scripts/03_control/s9/s9_soil_slope.py(머리말 12~37행, SLOPES_DEG, REANCHOR_SLOPES_DEG, _scaled_slope, H9_*)",
        "spec_sections": [f"{SPEC} 400~400.5(S9SL C-1~C-4)", f"{SPEC} 426.9.G(X4·X5)", f"{SPEC} 427.9·427.12.5(SGS 분류)",
                          f"{SPEC} 430(H9, X6 판정, 좌우 권고 결정)", f"{SPEC} 432.4(H-6), 432.4.7, 432.4.8, 432.5.3",
                          "00_docs/01_dynamics/dynamics_model.md 3.9.7.7(D8 결정), 3.12.6(규칙 A), 439행 표"],
    },
    "groups": {
        "H1": "주 격자: 지반 {G1, J1, J2, S1} × 패드 {B, A} × 8 경사 × 오거 상단 = 64",
        "H2": "오거 하단: 지반 4 × 패드 B × 8 경사 = 32",
        "H3": "타당성 비율: 지반 {J1, J2, S1} × 패드 {B, A} × {nose_down, roll_pos, edge_nd} × k {0.5, 0.75, 0.875}, 상단 = 54",
        "H4": "REANCHOR 켬: 지반 4 × 패드 {B, A} × {(0, 3.2), (0, 2.8)} 상단 + 강체 B 2 + J1 B (0, −3.2) = 19",
        "H5": "강체 기준: 강체 × 8 경사 × 상단 = 8",
        "H9": "좌우 세분(명세 430.2): {J1 B, J1 A, J2 B} × {roll_pos, roll_neg} × k {0.6, 0.65, 0.7, 0.75, 0.8, 0.875}, 상단, F_s 4 kN = 36",
        "common": "F_s 4 kN, 실행 한계 240 s, 정착 훅 harness(정착표 hook_harness), 후보 current = 최종 제어기 하네스",
        "source": "s9_soil_slope.py 머리말, 명세 430.2",
    },
    "h6_rule": {
        "source": "명세 432.4 H-6(432.4.5 행정, 432.4.4 평지 틈, 432.4.7 경사 틈, 432.4.5.1 적용 범위 결정 (가)), 432.4.8 (M1)",
        "applies_to": "연약 J1·J2·S1(패드 A·B)의 pass 행만. G1·강체는 적용하지 않는다.",
        "boundary_if_any": [
            "판독 행정 여유 682.8 − max_stroke_mm < 23 mm",
            "틈 여유 rut_ready_mm − 25 mm < 15 mm(경사) / < 13 mm(평지)",
            "READY t_ready_s + 31 s > 120 s(경사) / + 17 s > P3-6 한계(평지: J1·J2·S1 패드 B 100 s, 그 밖 90 s)",
        ],
        "label_ko": "경계(Chrono 미확인)",
        "check_vs_spec_432_4_8": chk,
    },
    "F2": {
        "title_ko": "연약 경사 하네스 판정 지도(최종 제어기, 177 + H9 36)",
        "records_slope_177": slope,
        "records_h9_36": h9,
        "layout": {
            "rows": rows,
            "columns": columns,
            "cells": grid,
            "row_order_rule": "강체 기준 1행 → 지반 G1·J1·J2·S1(연약도 순)마다 [패드 B 상단, 패드 B 하단, 패드 A 상단]. 패드 A 하단·오거 중단은 177에 없다.",
            "column_order_rule": "방향 묶음(평지 → 앞내림 → 대각 앞내림 → 오른쪽 → 왼쪽 → 앞들림 → 대각 앞들림 → rpB → REANCHOR 켬 H4) 안에서 R_c(=k) 오름차순. 열 머리에 방향(한글)과 k·바닥 각(°)을 두 줄로.",
            "empty_cell": "미실행(회색 빗금). H3는 J1·J2·S1 상단만, H9는 J1 B·J1 A·J2 B 상단만, H2는 패드 B만.",
            "duplicates": "H3 roll_pos k 0.75·0.875와 H9 같은 k는 같은 경사(명세 430.2, R9-1). 셀에 ids 두 개가 있으면 primary(H3)를 칠하고 H9는 주석. 일치 확인은 h6_rule.check_vs_spec_432_4_8.h3_h9_duplicates.",
            "encoding_suggestion": {
                "fill": {"pass": "통과", "stroke_limited_stop": "안전 종료", "fail": "실패"},
                "overlay": "H-6 경계(Chrono 미확인) = pass 칸에 테두리 또는 점 표시; Chrono 짝 있는 칸 = 작은 ◆ 표시(chrono_pair)",
                "fail_kind": "fail 칸 안 글자: soil_stop_with_crawler_loaded = 'S', judged_fail = 실패 행 첫 번호(P3-1 등)",
                "split_option": "한 판에 30열이 넓으면 (a) H1·H2·H3·H5(평지~rpB, 21열) / (b) H9 좌우 세분(roll k 0.6~0.875 두 방향, 3행) / (c) H4 REANCHOR 3열로 나눈다. control 추천은 (a)+(b) 한 판(roll 묶음에 H9 열을 끼워 넣은 지금 열 순서)과 (c) 작은 옆판.",
            },
        },
    },
}

# ------------------------------------------------------------------ F1
spec["h6_rule"]["h9_note"] = ("432.4.8 (M1)은 177만 셌다. H9 36행의 h6 값은 같은 규칙을 적용한 것이다(432.4.7 표의 H9 틈 경계 행과 "
                              "430.3.2 끝 'k 0.6 하네스 행은 새 H-6에서 경계'와 맞는다). Chrono 짝이 있는 행은 chrono_pair로 확인 결과를 함께 본다.")
spec["generator"] = {"script": "control-expert scratchpad build_fig_spec.py(저장소 밖, 입력 읽기 + R_c 환산 + H-6 규칙만)",
                     "run": "python-dev python -I build_fig_spec.py <root> <out>", "check": "h6_rule.check_vs_spec_432_4_8.match_spec_432_4_8 = true"}
spec["F1"] = {
    "title_ko": "운용 범위 다이어그램(roll–pitch 바닥 경사 평면)",
    "axes": {"x": "바닥 roll φ [deg] (+ = 오른쪽 낮음)", "y": "바닥 pitch θ [deg] (+ = 앞내림)",
             "suggested_limits_deg": {"x": [-6.0, 6.0], "y": [-4.0, 4.0]}, "aspect": "equal"},
    "layers": [
        {
            "id": "verification_diamond",
            "label_ko": "강체 검증 범위 |φ|/5.5° + |θ|/3.5° ≤ 1",
            "draw": True, "style": "얇은 점선, 채우지 않음",
            "shape": "diamond", "vertices_deg": [[5.5, 0], [0, 3.5], [-5.5, 0], [0, -3.5]],
            "note": "요청의 '상자'가 아니라 마름모다: D8 결정 안 2(dynamics_model.md 3.9.7.7, 439행 표 '|φ_g|/5.5° + |θ_g|/3.5° ≤ 1'). 하네스 rpB (2.7355, 1.7592)가 이 변 위의 점이다(2.7355/5.5 + 1.7592/3.5 = 1.000). CLAUDE.md의 '바닥 경사 5.5° / 3.5°'는 이 마름모의 꼭짓점이다.",
            "source": "00_docs/01_dynamics/dynamics_model.md 3.9.7.7·439행; CLAUDE.md 레벨링 시작 조건 행",
        },
        {
            "id": "operating_start_diamond",
            "label_ko": "운용 시작 조건 |φ|/4.4° + |θ|/3.2° ≤ 1(R_c ≤ 1)",
            "draw": True, "style": "실선, 연한 채움",
            "shape": "diamond", "vertices_deg": [[4.4, 0], [0, 3.2], [-4.4, 0], [0, -3.2]],
            "applies_to": "크롤러로 선 IMU 자세(φ_g, θ_g). 강체·로드 굽힘 근거 운용 한계(앞뒤 3.2° / 좌우 4.4°, D8 결정 기록 2026-10-21).",
            "source": "dynamics_model.md 3.9.7.7 결정 기록, 3.12.6 권고 규칙(목표 0이면 같은 식); CLAUDE.md",
        },
        {
            "id": "target_range_rule_A",
            "label_ko": "목표 범위(pitch ±3°, roll ±4° + 규칙 A)",
            "draw": False,
            "reason": "목표 범위는 데크 목표 자세 (φ_t, θ_t)의 수용 규칙이고 F1의 축(바닥 경사)과 다른 변수다. 레벨링 목표는 0(데크 수평)이고, 목표 0에서 규칙 A의 절대 마름모는 운용 시작 조건 마름모와 같은 식이 된다(dynamics_model.md 3.12.6 '권고 규칙은 목표가 0이면 D8 운용 한계 시작 조건과 같다'). 그리면 같은 마름모가 두 번 나오고 뜻이 섞인다. 캡션 한 문장으로 둔다.",
            "geometry_if_needed": {"axis_caps_deg": {"pitch": [-3.0, 3.0], "roll": [-4.0, 4.0]},
                                   "rule_A": "|φ_t − φ_g|/4.4 + |θ_t − θ_g|/3.2 ≤ 1 그리고 |φ_t|/4.4 + |θ_t|/3.2 ≤ 1"},
            "source": "dynamics_model.md 3.12.6; CLAUDE.md 목표 범위 행",
        },
        {
            "id": "J1B_soft_recommendation",
            "label_ko": "연약 J1 · 패드 B 운용 권고(Chrono 확인)",
            "draw": True, "style": "굵은 실선 다각형, 변마다 status별 선 모양(confirmed = 실선, interpolated = 파선, open = 선 없음)",
            "scope": "판정 토양 J1, 패드 B(기본), 오거 상단, F_s 4 kN, 최종 제어기. J2 B·패드 A에는 쓰지 않는다(아래 note).",
            "limits": {
                "left_roll_neg": {"value_deg": -2.64, "R_c": 0.6, "status": "Chrono 통과 X6-rb2(가드 여유 2.9 mm)", "source": "명세 430.3.3·430.3.4 결정 (가)"},
                "right_roll_pos": {"value_deg": 2.2, "R_c": 0.5, "status": "Chrono 통과 X6-rp3(틈 32.6 mm, 하한 대비 7.6 mm)", "source": "명세 430.3.6 결정 (가)·430.3.7"},
                "nose_down": {"value_deg": 2.8, "R_c": 0.875, "status": "Chrono 통과 X4-nd(최종 동치 (a))", "source": "명세 426.9.G.2·426.9.G.5·432.1·432.4.8 (M2)"},
                "diagonal_nose_down": {"value_deg": [1.925, 1.4], "R_c": 0.875, "status": "Chrono 통과 X4-ed(최종 동치 (a)), 오른쪽 낮음 쪽만", "source": "명세 426.9.G.4·432.4.8 (M2)"},
                "nose_up": {"value_deg": None, "status": "권고 없음 → '미확인'", "source": "명세 426.9.G.5·432.4.8에 앞들림 연약 권고 없음. 하네스 J1 B 상단 nose_up (0, −3.2)·edge_nu (2.2, −1.6)은 stroke_limited_stop, H4 J1 B nose_up도 stroke_limited_stop, k < 1 앞들림 하네스·Chrono 없음"},
            },
            "polygon_upper_half": {
                "vertices_deg": [[-2.64, 0.0], [-2.64, 0.88], [0.0, 2.8], [1.925, 1.4], [2.2, 1.2], [2.2, 0.0]],
                "closed_by": "θ = 0 선(open 변)",
                "edges": [
                    {"from": [-2.64, 0.0], "to": [-2.64, 0.88], "status": "interpolated", "note": "왼쪽 한계를 앞내림 쪽으로 연장(시험 없음)"},
                    {"from": [-2.64, 0.88], "to": [0.0, 2.8], "status": "interpolated", "note": "R_c 0.875 마름모, 왼쪽 낮음 + 앞내림 사분면. 대각 시험은 오른쪽 낮음 쪽(edge_nd)뿐이라 대칭 가정"},
                    {"from": [0.0, 2.8], "to": [1.925, 1.4], "status": "confirmed", "note": "R_c 0.875 마름모, 두 끝점 Chrono 통과(X4-nd, X4-ed)"},
                    {"from": [1.925, 1.4], "to": [2.2, 1.2], "status": "interpolated", "note": "R_c 0.875 마름모 위, 시험 없음"},
                    {"from": [2.2, 1.2], "to": [2.2, 0.0], "status": "interpolated", "note": "오른쪽 한계를 앞내림 쪽으로 연장(시험 없음)"},
                    {"from": [2.2, 0.0], "to": [-2.64, 0.0], "status": "open", "note": "한계가 아님. 평지 (0, 0) Chrono 통과(B0). 아래는 앞들림 미확인"},
                ],
                "vertex_derivation": "(−2.64, 0.88): θ = 3.2(0.875 − 2.64/4.4) = 0.88; (2.2, 1.2): θ = 3.2(0.875 − 2.2/4.4) = 1.2. 다각형 = {θ ≥ 0, R_c ≤ 0.875, −2.64 ≤ φ ≤ 2.2}.",
            },
            "nose_up_unconfirmed_region": {
                "draw": True, "style": "빗금, 글자 '앞들림: 연약 J1 B 권고 미확인'",
                "region": "운용 시작 조건 마름모의 θ < 0 반쪽 [[4.4, 0], [0, −3.2], [−4.4, 0]]",
                "decision": "control 판단: 앞들림은 운용 시작 조건 안이라도 연약 지반 권고 근거가 없으므로 '불가'로 칠하지 않고 '미확인'으로 둔다. 하네스 k 1 점(안전 종료)은 점으로만 보인다.",
            },
            "note": "J2 B는 '하네스 경계(비단조: roll_pos k 0.5 재접촉 실패), Chrono 미확인'(430.3.7). 패드 A는 하네스상 좌우 3.85°(k 0.875)까지 통과(430.3.1), 앞내림 k 0.875는 J1 A에서도 안전 종료(432.4.8 M2). 오른쪽 2.2~2.64°는 '크롤러 틈 목표 미달이 날 수 있는 영역', 왼쪽 2.64° 초과는 '목표 미달 안전 정지가 날 수 있는 영역'(430.3.7 결론 문구). 오른쪽 2.2° 통과는 그 각도 1건이고 2.2° 아래 모든 각의 틈을 보장하지 않는다(430.3.7 해석).",
        },
    ],
}

CH = "07_results/S9/"
EV = "06_analysis/02_control/s9/rev85/evidence/"
chrono = [
    {"id": "X6-rb2", "case": "S9SL_X6rb_J1_B_top_Fs4_rm2p64_p0", "folder": CH + "batch_RV6_20261031_025137/S9SL_X6rb_J1_B_top_Fs4_rm2p64_p0",
     "soil": "J1", "pad": "B", "auger": "top", "floor_deg": [-2.64, 0.0], "direction": "roll_neg", "k": 0.6, "R_c_floor": 0.6,
     "verdict": "pass", "verdict_ko": "통과", "safe_stop": False, "controller": "final_SGS_R4", "final_equivalent": True,
     "key_values": "가드 여유 2.93 mm(판독 679.87 mm), READY 82.6 s, 틈 47.6 mm, 이탈 뒤 최소 63.05 kN, 정착 기울기 2.65°",
     "harness_pair": "H9|J1|B|top|roll_neg@k0.6 (pass)", "spec": "430.3.3", "evidence": [EV + "final_x_rb2_judge.json", EV + "x6rb2_digest.json"]},
    {"id": "X6-rb", "case": "S9SL_X6rb_J1_B_top_Fs4_rm2p86_p0", "folder": CH + "batch_FINAL-REP_20261030_223359/S9SL_X6rb_J1_B_top_Fs4_rm2p86_p0",
     "soil": "J1", "pad": "B", "auger": "top", "floor_deg": [-2.86, 0.0], "direction": "roll_neg", "k": 0.65, "R_c_floor": 0.65,
     "verdict": "stroke_limited_stop", "verdict_ko": "안전 종료", "safe_stop": True, "controller": "final (SGS + R4c30)", "final_equivalent": True,
     "key_values": "42.4 s FAULT_LIFT_STROKE_LIMIT:soil:FL, 정지 뒤 최소 68.3 kN, 크롤러 0 N, READY 0, 끝 roll 0.155°",
     "harness_pair": "H9|J1|B|top|roll_neg@k0.65 (pass, 하네스 낙관)", "spec": "430.3.2", "evidence": [EV + "x6_stop_check.json", EV + "final_rep_x6_digest.json"]},
    {"id": "X6-rp3", "case": "S9SL_X6rb_J1_B_top_Fs4_r2p2_p0", "folder": CH + "batch_RV6_20261031_091226/S9SL_X6rb_J1_B_top_Fs4_r2p2_p0",
     "soil": "J1", "pad": "B", "auger": "top", "floor_deg": [2.2, 0.0], "direction": "roll_pos", "k": 0.5, "R_c_floor": 0.5,
     "verdict": "pass", "verdict_ko": "통과", "safe_stop": False, "controller": "final_SGS_R4", "final_equivalent": True,
     "key_values": "틈 32.63 mm, 판독 612.40 mm(가드 여유 70.4 mm), READY 80.3 s, 최소 64.98 kN, 정착 기울기 2.20°",
     "harness_pair": "H3|J1|B|top|roll_pos@k0.5 (pass)", "spec": "430.3.7", "evidence": [EV + "final_x_rp3_judge.json", EV + "x6rp3_digest.json"]},
    {"id": "X6-rp2", "case": "S9SL_X6rb_J1_B_top_Fs4_r2p64_p0", "folder": CH + "batch_RV6_20261031_070613/S9SL_X6rb_J1_B_top_Fs4_r2p64_p0",
     "soil": "J1", "pad": "B", "auger": "top", "floor_deg": [2.64, 0.0], "direction": "roll_pos", "k": 0.6, "R_c_floor": 0.6,
     "verdict": "fail", "verdict_ko": "실패(틈)", "fail_rows": ["P3-5"], "safe_stop": False, "controller": "final_SGS_R4", "final_equivalent": True,
     "key_values": "첫 READY 뒤 틈 24.84 mm < 25 mm(0.16 mm 미달), 그 밖 행 통과, 판독 631.01 mm(가드 여유 51.8 mm), 정착 기울기 2.645°",
     "harness_pair": "H9|J1|B|top|roll_pos@k0.6 (pass, H-6 틈 경계)", "spec": "430.3.5", "evidence": [EV + "final_x_rp2_judge.json", EV + "x6rp2_digest.json"]},
    {"id": "X6-rp-sa", "case": "S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0", "folder": CH + "batch_FINAL-REP_20261030_223359/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0",
     "soil": "J1", "pad": "B", "auger": "top", "floor_deg": [3.85, 0.0], "direction": "roll_pos", "k": 0.875, "R_c_floor": 0.875,
     "verdict": "fail", "verdict_ko": "실패(크롤러 하중 진 안전 정지)", "fail_kind": "stop_with_crawler_loaded", "safe_stop": True,
     "controller": "final (SGS any_loc)", "final_equivalent": True,
     "key_values": "40.6 s FAULT_LIFT_STROKE_LIMIT:soil:FR, 정지 때 크롤러 7.79 kN > 0.01 W, 정지 뒤 네 다리 최소 64.0 kN, SA-4 통과, 끝 roll 0.565°",
     "harness_pair": "H3|J1|B|top|roll_pos@k0.875 (stroke_limited_stop)", "spec": "430.4.1", "evidence": [EV + "x6_stop_check.json"]},
    {"id": "X4-rp", "case": "S9SL_X4rp_J1_B_top_Fs4_r3p85_p0", "folder": CH + "batch_RV1_20261030_111615/S9SL_X4rp_J1_B_top_Fs4_r3p85_p0",
     "soil": "J1", "pad": "B", "auger": "top", "floor_deg": [3.85, 0.0], "direction": "roll_pos", "k": 0.875, "R_c_floor": 0.875, "settle_R_c": 0.896,
     "verdict": "fail", "verdict_ko": "실패(이전 판)", "safe_stop": False, "controller": "pre-SGS (c2.py f2ffce3…, 명령 = 05708b2)", "final_equivalent": False,
     "superseded_by": "X6-rp-sa", "draw_default": False,
     "key_values": "가드 SHIFT_DOWN → 크롤러 재착지 181 kN, 왼쪽 다리 1.2 kN, FAULT; SL-1 stroke_limited_fail",
     "harness_pair": "H3|J1|B|top|roll_pos@k0.875", "spec": "426.9.G.3", "evidence": []},
    {"id": "X4-nd", "case": "S9SL_X4nd_J1_B_top_Fs4_r0_p2p8", "folder": CH + "batch_RV1_20261030_111615/S9SL_X4nd_J1_B_top_Fs4_r0_p2p8",
     "soil": "J1", "pad": "B", "auger": "top", "floor_deg": [0.0, 2.8], "direction": "nose_down", "k": 0.875, "R_c_floor": 0.875,
     "settle_deg": [0.001, 3.034], "settle_R_c": 0.948, "reanchor": True,
     "verdict": "pass", "verdict_ko": "통과(P3-7 기록 행 실패)", "safe_stop": False, "controller": "pre-final 3434912(명령 = 05708b2), 최종 동치 (a)", "final_equivalent": True,
     "key_values": "READY 97.1 s, 틈 122.5 mm, 최대 행정 645.4 mm(가드 여유 37.4 mm), REANCHOR 통과",
     "harness_pair": "H3|J1|B|top|nose_down@k0.875 (pass) / H4|J1|B|top|nose_down_2p8 (pass)", "spec": "426.9.G.2, 432.1(ZIC 기각으로 (a))", "evidence": []},
    {"id": "X4-ed", "case": "S9SL_X4ed_J1_B_top_Fs4_r1p925_p1p4", "folder": CH + "batch_RV1_20261030_111615/S9SL_X4ed_J1_B_top_Fs4_r1p925_p1p4",
     "soil": "J1", "pad": "B", "auger": "top", "floor_deg": [1.925, 1.4], "direction": "edge_nd", "k": 0.875, "R_c_floor": 0.875, "settle_R_c": 0.902,
     "verdict": "pass", "verdict_ko": "통과(P3-7 기록 행 실패)", "safe_stop": False, "controller": "pre-final 3434912, 최종 동치 (a)", "final_equivalent": True,
     "key_values": "READY 62.4 s, 틈 69.2 mm, 최대 행정 FR 653.1 mm(여유 29.7 mm), 최소 63.7 kN",
     "harness_pair": "H3|J1|B|top|edge_nd@k0.875 (pass)", "spec": "426.9.G.4, 432.1", "evidence": []},
    {"id": "C-1", "case": "S9SL_C1_G1_B_top_Fs4_r0_p3p2", "folder": CH + "batch_S9SL_20261029_144406/S9SL_C1_G1_B_top_Fs4_r0_p3p2",
     "soil": "G1", "pad": "B", "auger": "top", "floor_deg": [0.0, 3.2], "direction": "nose_down", "k": 1.0, "R_c_floor": 1.0,
     "settle_deg": [0.0001, 3.543], "settle_R_c": 1.107, "reanchor": True,
     "verdict": "pass", "verdict_ko": "통과", "safe_stop": False, "controller": "2026-10-29 최종 코드(D안 + E3c10 + LWa), 최종 동치 (a)", "final_equivalent": True,
     "key_values": "P3-1~P3-8 통과, READY 85.0 s, 틈 89.2 mm, RA 통과; SL-2 R_c 1.107 > 1(운용 모드면 시작 거부, record_only)",
     "harness_pair": "H4|G1|B|top|nose_down (pass)", "spec": "400.1, 400.5, 432.1", "evidence": []},
    {"id": "C-2", "case": "S9SL_C2_J1_A_top_Fs4_r4p4_p0", "folder": CH + "batch_S9SL_20261029_144406/S9SL_C2_J1_A_top_Fs4_r4p4_p0",
     "soil": "J1", "pad": "A", "auger": "top", "floor_deg": [4.4, 0.0], "direction": "roll_pos", "k": 1.0, "R_c_floor": 1.0,
     "settle_deg": [4.41, 0.06], "settle_R_c": 1.021,
     "verdict": "pass_P3-7_record_fail", "verdict_ko": "통과(P3-7 기록 행만 실패, 이전 판)", "safe_stop": False,
     "controller": "2026-10-29 최종 코드(SGS 전)", "final_equivalent": False,
     "final_note": "가드 경고 WARN_LIFT_STROKE_LIMITED:FR 49.7 s가 있어 최종 제어기(SGS)에서는 결과가 달라진다((b), 432.1). 재실행 없음",
     "key_values": "READY 81.1 s, 틈 59.0 mm, 최소 60.7 kN",
     "harness_pair": "H1|J1|A|top|roll_pos (pass)", "spec": "400.2, 400.5, 432.1", "evidence": []},
    {"id": "C-3", "case": "S9SL_C3_J1_B_top_Fs4_r3p3_p0", "folder": CH + "batch_S9SL_20261029_144406/S9SL_C3_J1_B_top_Fs4_r3p3_p0",
     "soil": "J1", "pad": "B", "auger": "top", "floor_deg": [3.3, 0.0], "direction": "roll_pos", "k": 0.75, "R_c_floor": 0.75, "settle_R_c": 0.768,
     "verdict": "stroke_limited_pass", "verdict_ko": "행정 제한 통과(이전 판)", "safe_stop": False,
     "controller": "2026-10-29 최종 코드(SGS 전)", "final_equivalent": False,
     "final_note": "가드 경고 49.5·69.3 s → 최종 제어기에서는 SGS 안전 정지 가능성이 크다(426.9.G.5, 추정, 재실행 없음). 하네스 최종 H3·H9 J1 B roll_pos k 0.75는 pass(H-6 행정·틈 경계)",
     "key_values": "틈 21.9 mm(< 25, 가드 FR 677.8 mm), READY 80.3 s, 최소 63.0 kN",
     "harness_pair": "H3|J1|B|top|roll_pos@k0.75", "spec": "400.4, 400.5, 426.9.G.5, 432.1", "evidence": []},
    {"id": "C-4", "case": "S9SL_C4_J1_A_top_Fs4_r0_p3p2", "folder": CH + "batch_S9SL_20261029_144406/S9SL_C4_J1_A_top_Fs4_r0_p3p2",
     "soil": "J1", "pad": "A", "auger": "top", "floor_deg": [0.0, 3.2], "direction": "nose_down", "k": 1.0, "R_c_floor": 1.0, "settle_R_c": 1.081, "reanchor": True,
     "verdict": "fail", "verdict_ko": "실패(FAULT_LIFT_STROKE_LIMIT, 이전 판)", "safe_stop": False,
     "controller": "2026-10-29 최종 코드(SGS 전)", "final_equivalent": False,
     "final_note": "가드 작동 사례라 최종 제어기(SGS)에서는 안전 종료로 바뀔 것으로 본다((b), 432.1, 재실행 없음). 하네스 최종 H4 J1 A nose_down = stroke_limited_stop",
     "key_values": "READY 없음, 93.2 s FAULT_LIFT_STROKE_LIMIT:FR, 전방 관입 약 100 mm",
     "harness_pair": "H4|J1|A|top|nose_down (stroke_limited_stop)", "spec": "400.3, 400.5, 432.1", "evidence": []},
    {"id": "B0", "case": "P3b_J1_B_top_Fs4", "folder": CH + "batch_FINAL-REP_20261030_223359/P3b_J1_B_top_Fs4",
     "soil": "J1", "pad": "B", "auger": "top", "floor_deg": [0.0, 0.0], "direction": "flat", "k": 0.0, "R_c_floor": 0.0,
     "verdict": "pass", "verdict_ko": "통과", "safe_stop": False, "controller": "final (SGS + R4c30)", "final_equivalent": True,
     "key_values": "READY 74.2 s, 틈 66.3 mm, 0.047°", "harness_pair": "H1|J1|B|top|flat", "spec": "432.5.2",
     "evidence": [EV + "final_rep_flat_digest.json"]},
    {"id": "B0prime", "case": "P3b_J2_B_top_Fs4", "folder": CH + "batch_FINAL-REP_20261030_223359/P3b_J2_B_top_Fs4",
     "soil": "J2", "pad": "B", "auger": "top", "floor_deg": [0.0, 0.0], "direction": "flat", "k": 0.0, "R_c_floor": 0.0,
     "verdict": "pass", "verdict_ko": "통과(P3-2 FLAG)", "safe_stop": False, "controller": "final (SGS + R4c30)", "final_equivalent": True,
     "key_values": "READY 81.5 s, 틈 72.3 mm, 0.056°", "harness_pair": "H1|J2|B|top|flat", "spec": "432.5.2",
     "evidence": [EV + "final_rep_flat_digest.json"], "draw_default": False},
]
spec["F1"]["chrono_points"] = {
    "items": chrono,
    "encoding_suggestion": {
        "marker_by_verdict": {"pass": "채운 원", "stroke_limited_stop": "채운 사각(안전 종료)", "fail": "×", "fail+safe_stop": "× 위 사각 테두리(X6-rp-sa)",
                              "pass_P3-7_record_fail": "채운 원", "stroke_limited_pass": "속 빈 사각"},
        "fill_by_controller": "final_equivalent true = 진한 색, false(C-2·C-3·C-4, X4-rp) = 회색 속 빈 표시 + 범례 '이전 판(SGS 전)'",
        "soil_pad_filter": "본판은 J1 · 패드 B만(권고 다각형과 같은 범위). C-1(G1 B)·C-2·C-4(J1 A)는 다른 표식 또는 옆판",
        "overlap": "(3.85, 0)에 X6-rp-sa와 X4-rp가 겹친다. X4-rp는 draw_default false(필요하면 살짝 옮긴 회색 표식). (0, 3.2)에 C-1(G1 B)과 C-4(J1 A)가 겹친다",
        "labels": "점 옆에 id와 바닥 각, 예 'X6-rb2 −2.64°'",
    },
}

h_pts = []
for r in slope + h9:
    if r["soil"] in ("J1", "J2") and r["auger"] == "top" and not (r["soil"] == "J2" and r["pad"] == "A"):
        h_pts.append({"id": r["id"], "series": f"{r['soil']}{r['pad']}" + ("_RA" if r["reanchor"] else ""),
                      "floor_deg": [r["floor_roll_deg"], r["floor_pitch_deg"]], "R_c_floor": r["R_c_floor"],
                      "verdict": r["verdict"], "h6_boundary": r["h6"]["boundary"], "h6_reasons": r["h6"]["reasons"],
                      "fail_kind": r["fail_kind"]})
spec["F1"]["harness_points"] = {
    "note": "하네스 최종 제어기 판정(F2와 같은 기록). 본판 권장 = series 'J1B'(H1·H3·H9 상단). J1A·J2B는 옆판 또는 끄기. '_RA'는 H4 REANCHOR 켬(같은 좌표에 겹치므로 기본 끔). 같은 좌표의 H3·H9 중복(roll_pos k 0.75·0.875)은 한 번만 그린다.",
    "draw_series_default": ["J1B"],
    "encoding": "작은 표식: pass = 속 빈 원(H-6 경계면 점선 원), stroke_limited_stop = 속 빈 사각, fail = 작은 ×",
    "h9_roll_boundary_summary": {
        "source": "명세 430.3.1 표(P36sa 후보 열 = 최종 제어기), finB2_h9.json",
        "k_b_pass_continuous": {"J1B_roll_neg": 0.65, "J1B_roll_pos": "0.75(엄격 0.6; k 0.65 P3-5 경계 잡음)", "J2B_roll_neg": 0.65, "J2B_roll_pos": 0.7, "J1A": "≥ 0.875"},
    },
    "items": h_pts,
}
spec["judgements"] = [
    "F1 강체 검증 범위는 상자가 아니라 마름모(|φ|/5.5 + |θ|/3.5 ≤ 1)로 그린다(dynamics_model.md 439행, rpB가 그 변 위).",
    "목표 범위(규칙 A)는 F1에 그리지 않는다: 축 변수가 다르고, 목표 0에서 운용 시작 조건 마름모와 같은 식이다.",
    "앞들림은 '불가'가 아니라 '미확인' 빗금으로 둔다(연약 권고 근거 없음, 하네스 k 1만 안전 종료).",
    "J1 B 권고 다각형은 θ ≥ 0 반쪽만 닫고, 확인된 변(X4-nd–X4-ed 사이 R_c 0.875)과 보간 변(좌우 한계의 앞내림 쪽 연장, 왼쪽 낮음 대각)을 선 모양으로 구분한다.",
    "Chrono 점은 최종 제어기·최종 동치 (a)와 이전 판(SGS 전, (b))을 구분한다. C-2·C-3·C-4·X4-rp는 이전 판이다.",
    "F2 R_c는 바닥 명목값이다. 정착 SL-2 R_c는 최종 하네스 JSON에 없다.",
]

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in chk.items() if k not in ("h6_boundary_ids",)}, ensure_ascii=False, indent=1))
print("boundary ids:")
for i in chk["h6_boundary_ids"]:
    print(" ", i)
print("cells:", len(grid), "rows", len(rows), "cols", len(columns))
