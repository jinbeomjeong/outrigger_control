"""C2 R5 레벨링 제어기 다이어그램 세 장(상세 블록도, 개요 블록도, 단계 전이도)을 그린다.

입력: 06_analysis/02_control/c2_r5_diagram_spec.json (control-expert가 코드 기준으로 확정한 명세)
출력(같은 폴더):
  c2_r5_block_diagram.graphml / .png(화면용, 긴 변 3800 px 이하) / _hires.png(200 dpi) / .svg
  c2_r5_block_overview.graphml / .png / .svg   (그룹 단위 거시 블록도, 그룹 사이 엣지를 묶음)
  c2_r5_phase_flow.graphml / .png / .svg

흐름
  1. 명세 JSON -> 그림 모델(노드·그룹·엣지·범례). 라벨 크기는 맑은 고딕(Pillow)으로 잰다.
  2. 좌표: 블록도 두 장은 Graphviz dot(크기 고정 노드 + 크기 고정 라벨 자리)으로 배치하고,
     플랜트 -> 센서 되먹임은 왼쪽 가장자리 버스로 따로 돌린다.
     단계도는 노드 10개라 직접 배치한다(주 경로 한 열, 되돌아가는 엣지는 오른쪽·왼쪽 차선).
  3. 같은 좌표로 PNG·SVG(neato -n2가 주어진 위치·경로·라벨 위치 그대로 그림)와 yEd GraphML을 쓴다.
노드·엣지·라벨 문구는 명세 그대로다. 그림에만 더하는 것은 범례 노드, 상세판의 'LEVEL 루프' 묶음
(명세 layout_hints)이고, 긴 엣지 라벨은 낱말 경계에서 줄만 바꾼다. 개요판의 묶음 라벨은 명세 라벨을 나열한다.

실행 (graphviz dot·neato가 있는 환경, Pillow가 있으면 글자 폭을 잰다):
  C:\\ProgramData\\miniforge3\\envs\\python-dev\\python.exe -I plot_c2_block_diagram.py
  옵션: --spec PATH --out-dir DIR --dot PATH(dot.exe; neato.exe는 같은 폴더) --keep-intermediate DIR
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC = ROOT / "06_analysis" / "02_control" / "c2_r5_diagram_spec.json"
FONT = "Malgun Gothic"
FONT_FILE = r"C:\Windows\Fonts\malgun.ttf"
SCREEN_MAX_PX = 3800
HIRES_DPI = 200
NODE_FS, EDGE_FS, GROUP_FS, LEGEND_FS = 11, 9, 13, 9

# ---------------------------------------------------------------- 공통 스타일

GROUP_STYLE = {  # id -> (그룹 배경, 그룹 테두리, 노드 채움)
    "G_PLANT": ("#ECEFF1", "#546E7A", "#CFD8DC"),
    "G_SENSOR": ("#EEF7EE", "#2E7D32", "#C8E6C9"),
    "G_EST": ("#EAF3FC", "#1565C0", "#BBDEFB"),
    "G_DEC": ("#FFF6EA", "#E65100", "#FFE0B2"),
    "G_LEVEL": ("#FFE9CC", "#E65100", "#FFE0B2"),
    "G_OUT": ("#F6ECF8", "#6A1B9A", "#E1BEE7"),
    "G_OP": ("#FFFDE7", "#F9A825", "#FFF59D"),
}
EDGE_COLOR = "#37474F"
SHADOW_COLOR = "#78909C"
FEEDBACK_COLOR = "#C62828"
LINE_STYLE = {"solid": "line", "dashed": "dashed", "dotted": "dotted"}

PHASE_CLASS = {  # class -> (색, 굵기, 범례 문구)
    "main": ("#212121", 2.6, "H5a 주 경로 (굵은 검정)"),
    "relevel": ("#1565C0", 1.4, "재레벨 (파랑)"),
    "reprobe": ("#00897B", 1.4, "재접지·재탐침 (청록)"),
    "abort": ("#C62828", 1.4, "중단·FAULT (빨강)"),
    "target": ("#6A1B9A", 1.4, "목표 변경 (보라)"),
    "self": ("#757575", 1.2, "자기 루프 = 단계 유지 (회색)"),
}
PHASE_FILL = {
    "start": "#FFFFFF", "CHECK": "#E3F2FD", "IDLE": "#ECEFF1", "TOUCH": "#E8F5E9",
    "LEVEL": "#FFF3E0", "DONE": "#F1F8E9", "PROBE": "#E0F2F1", "REANCHOR": "#EDE7F6",
    "READY": "#C8E6C9", "FAULT": "#FFCDD2",
}

# 상세 블록도
LEVEL_LOOP = ["D_ATT", "D_HEAVE", "D_TWIST", "D_GUARD", "D_MIX", "D_LIMIT"]
PLANT_FEEDBACK = {("PLANT", "S_P"), ("PLANT", "S_S"), ("PLANT", "S_ACC"), ("PLANT", "S_GYRO")}
# 위 -> 아래 순서를 거스르는 엣지: 순위 계산에서 뺀다
BACKWARD_EDGES = {("D_PROBE", "E_BAND"), ("O_CMD", "E_GATE"), ("D_CHECK", "E_SETTLE"), ("D_TOUCH", "E_FLOOR")}
# 배치 전용 보이지 않는 엣지(그림·GraphML에 나오지 않음): 추정 블록을 센서 바로 아래에 모으고
# 판단 블록이 추정 블록 아래에서 시작하게 한다
BLOCK_LAYOUT_ONLY = [("E_ATT", "E_SETTLE", 1), ("E_FORCE", "E_FLOOR", 1)] + [
    ("E_CLR", d, 0) for d in ("D_CHECK", "D_TOUCH", "D_TARGET", "D_GUARD", "D_PROBE", "D_REANCHOR")]
BLOCK_SAME_RANK = [("E_GE1", "E_GE2"), ("D_TARGET", "D_REF"), ("O_RAMP", "O_CMD")]

BLOCK_LEGEND_ROWS = [
    (EDGE_COLOR, "━━━", "실선: 명령·단계 판정에 쓰이는 신호"),
    (SHADOW_COLOR, "╌╌╌", "점선: 그림자·기록 전용 / 미구현 (R6, GE2)"),
    (EDGE_COLOR, "┈┈┈", "점점선: 파라미터·설정 갱신 (느림, 사건 구동)"),
    (FEEDBACK_COLOR, "━━━", "빨간 선: 되먹임 (플랜트 → 센서, 측정 (−) 입력, F_band 갱신, 명령 0 지속)"),
]
BLOCK_LEGEND_NOTES = [
    "이산 T_s = 20 ms, 다리 배열 순서 FL, FR, RL, RR. 오차 e = φ_r − φ_f (음의 되먹임).",
    "출력은 다리 속도 명령뿐 — 위치 기준 s_ref = ∫u dt는 L1 엔진 훅 (c2.py에 위치 명령 없음).",
    "350 bar는 제어기 포화가 아님: READY에서 다리당 1회 경고 사건만. 210 bar 포화는 플랜트 쪽(법칙 C).",
]

# ---------------------------------------------------------------- 글자 크기


class Meter:
    """맑은 고딕(Pillow) 폭·줄 높이. Pillow가 없으면 글자 종류별 근사."""

    def __init__(self) -> None:
        self.fonts = {}
        try:
            from PIL import ImageFont  # noqa: PLC0415
            self._IF = ImageFont
            ImageFont.truetype(FONT_FILE, 10)
        except Exception:  # noqa: BLE001
            self._IF = None

    def _font(self, size):
        if size not in self.fonts:
            self.fonts[size] = self._IF.truetype(FONT_FILE, size)
        return self.fonts[size]

    def size(self, text: str, fs: float) -> tuple[float, float]:
        lines = text.split("\n") if text else [""]
        if self._IF is None:
            w = max(sum(fs * (1.0 if ord(c) > 0x1100 else 0.6) for c in ln) for ln in lines)
            return w, len(lines) * fs * 1.45
        f = self._font(int(round(fs)))
        asc, desc = f.getmetrics()
        return max(f.getlength(ln) for ln in lines), len(lines) * (asc + desc)


def wrap(text: str, width: int) -> str:
    """기존 줄바꿈은 두고, width자보다 긴 줄만 공백에서 나눈다(문구는 그대로)."""
    out = []
    for line in text.split("\n"):
        cur = ""
        for word in line.split(" "):
            if cur and len(cur) + 1 + len(word) > width:
                out.append(cur)
                cur = word
            else:
                cur = f"{cur} {word}" if cur else word
        out.append(cur)
    return "\n".join(out)


def esc_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def q(text: str) -> str:
    t = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{t}"'


# ---------------------------------------------------------------- 그림 모델


def node_rec(nid, label, meter, *, group=None, fill="#FFFFFF", border="#37474F", border_style="line",
             shape="roundrectangle", description="", fs=NODE_FS, min_h=0.0):
    tw, th = meter.size(label, fs)
    w, h = tw + 22, th + 14
    if shape == "ellipse":
        w, h = w * 1.3, h * 1.35
    elif shape == "octagon":
        w, h = w * 1.18, h * 1.3
    return {"id": nid, "label": label, "group": group, "fill": fill, "border": border,
            "border_style": border_style, "shape": shape, "description": description, "fs": fs,
            "w": max(w, 44.0), "h": max(h, 30.0, min_h)}


def edge_rec(eid, s, t, label, meter, *, style="solid", color=EDGE_COLOR, width=1.0, data=None, dot=None):
    lw, lh = meter.size(label, EDGE_FS) if label else (0.0, 0.0)
    return {"id": eid, "source": s, "target": t, "label": label, "style": style, "color": color, "width": width,
            "data": data or {}, "dot": dot or {}, "lw": lw + 8 if label else 0.0, "lh": lh + 4 if label else 0.0}


def legend_rec(rows, notes, meter):
    lines = ["범례"] + [f"{s}  {t}" for _, s, t in rows] + notes
    tw, th = meter.size("\n".join(lines), LEGEND_FS)
    return {"rows": rows, "notes": notes, "text": "\n".join(lines), "w": tw + 26, "h": th + 18}


def block_model(bd: dict, meter: Meter) -> dict:
    groups = {g["id"]: {"id": g["id"], "label": g["label"], "parent": None, "order": g.get("order", 0)}
              for g in bd["groups"]}
    groups["G_LEVEL"] = {"id": "G_LEVEL", "label": "LEVEL 루프", "parent": "G_DEC", "order": 3}
    nodes = []
    for n in bd["nodes"]:
        grp = "G_LEVEL" if n["id"] in LEVEL_LOOP else n["group"]
        _, border, fill = GROUP_STYLE[grp]
        dashed = n.get("style") == "dashed"
        nodes.append(node_rec(n["id"], n["label"], meter, group=grp, fill="#F5F5F5" if dashed else fill,
                              border=SHADOW_COLOR if dashed else border,
                              border_style="dashed" if dashed else "line", description=n.get("code", "")))
    edges = []
    for i, e in enumerate(bd["edges"]):
        fb = bool(e.get("feedback"))
        style = e.get("style", "solid")
        color = FEEDBACK_COLOR if fb else (SHADOW_COLOR if style == "dashed" else EDGE_COLOR)
        key = (e["from"], e["to"])
        dot = {"constraint": "false"} if key in BACKWARD_EDGES else {}
        rec = edge_rec(f"e{i}", e["from"], e["to"], e.get("label", ""), meter, style=style, color=color,
                       width=1.6 if fb else 1.0, data={"signal_style": style, "feedback": fb}, dot=dot)
        rec["bus"] = key in PLANT_FEEDBACK
        edges.append(rec)
    return {"title": "C2 R5 레벨링 제어기 블록도 (상세, 명세 c2_r5_diagram_spec.json)", "groups": groups,
            "nodes": nodes, "edges": edges, "legend": legend_rec(BLOCK_LEGEND_ROWS, BLOCK_LEGEND_NOTES, meter)}


OVERVIEW_ORDER = ["G_SENSOR", "G_EST", "G_OP", "G_DEC", "G_LEVEL", "G_OUT", "G_PLANT"]


def overview_model(bd: dict, meter: Meter) -> dict:
    """그룹 하나 = 블록 하나. 그룹 사이 엣지를 (출발, 도착, 선 종류, 되먹임)으로 묶고 명세 라벨을 나열한다."""
    glabel = {g["id"]: g["label"] for g in bd["groups"]}
    glabel["G_LEVEL"] = "LEVEL 루프"
    gof = {n["id"]: ("G_LEVEL" if n["id"] in LEVEL_LOOP else n["group"]) for n in bd["nodes"]}
    members: dict[str, list] = {}
    for n in bd["nodes"]:
        members.setdefault(gof[n["id"]], []).append(n["label"].split("\n")[0])
    nodes = []
    for gid in OVERVIEW_ORDER:
        bg, border, fill = GROUP_STYLE[gid]
        label = glabel[gid] + "\n" + "\n".join("· " + m for m in members[gid])
        nodes.append(node_rec(gid, label, meter, fill=fill, border=border, shape="roundrectangle",
                              description="그룹 노드: " + ", ".join(n["id"] for n in bd["nodes"] if gof[n["id"]] == gid)))
    bundles: dict[tuple, list] = {}
    for e in bd["edges"]:
        a, b = gof[e["from"]], gof[e["to"]]
        if a == b:
            continue
        key = (a, b, e.get("style", "solid"), bool(e.get("feedback")))
        bundles.setdefault(key, []).append(e)
    edges = []
    for i, ((a, b, style, fb), es) in enumerate(bundles.items()):
        labs = []
        for e in es:
            lab = e.get("label", "").replace("\n", " ")
            if lab and lab not in labs:
                labs.append(lab)
        shown = labs[:5]
        text = ", ".join(shown) + (f" 외 {len(labs) - 5}건" if len(labs) > 5 else "")
        text = f"[{len(es)}] " + text
        color = FEEDBACK_COLOR if fb else (SHADOW_COLOR if style == "dashed" else EDGE_COLOR)
        dot = {"constraint": "false"} if (a, b) in {("G_DEC", "G_EST"), ("G_OUT", "G_EST")} else {}
        rec = edge_rec(f"b{i}", a, b, wrap(text, 34), meter, style=style, color=color, width=1.8 if fb else 1.2,
                       data={"signal_style": style, "feedback": fb, "edge_count": str(len(es)),
                             "members": "; ".join(f"{e['from']}->{e['to']}" for e in es)}, dot=dot)
        rec["bus"] = (a, b) == ("G_PLANT", "G_SENSOR")
        edges.append(rec)
    notes = ["[N] = 묶인 상세 엣지 수, 라벨은 명세 라벨 나열(5개 넘으면 '외 N건'). 그룹 안 엣지는 상세판 참조.",
             "LEVEL 루프는 상세판에서 판단 그룹 안의 묶음이다."] + BLOCK_LEGEND_NOTES[1:2]
    return {"title": "C2 R5 레벨링 제어기 개요 블록도 (명세 c2_r5_diagram_spec.json 그룹 단위)", "groups": {},
            "nodes": nodes, "edges": edges, "legend": legend_rec(BLOCK_LEGEND_ROWS, notes, meter)}


def phase_model(pf: dict, meter: Meter) -> dict:
    nodes = []
    for n in pf["nodes"]:
        key = "start" if n.get("kind") == "start" else n["id"]
        shape = "ellipse" if key == "start" else ("octagon" if n["id"] == "FAULT" else "roundrectangle")
        nodes.append(node_rec(n["id"], n["label"], meter, fill=PHASE_FILL[key],
                              border="#C62828" if n["id"] == "FAULT" else "#37474F", shape=shape,
                              description=n.get("code", n.get("kind", "")),
                              min_h=96.0 if n["id"] == "LEVEL" else 0.0))
    side = {"e10", "e13", "e11", "e14", "e15", "e16", "e17", "e18", "e19"}  # 차선 라벨: 좁게 줄바꿈
    edges = []
    for e in pf["edges"]:
        color, width, _ = PHASE_CLASS[e["class"]]
        lab = wrap(e.get("label", ""), 22 if e["id"] in side else 34)
        edges.append(edge_rec(e["id"], e["from"], e["to"], lab, meter, style=e.get("style", "solid"), color=color,
                              width=width, data={"edge_class": e["class"], "signal_style": e.get("style", "solid")}))
    rows = [(c, "━━━", t) for c, _, t in PHASE_CLASS.values()]
    notes = [f"{', '.join(a['attach'])}: {a['label']}" for a in pf.get("annotations", [])]
    notes += ["LEVEL·DONE 두 번째 진입(REANCHOR completed 뒤 트림)도 같은 LEVEL·DONE 노드다.",
              "기본 COMBINED 접지 판정 + after_probe(H5a)만 그림. PRESSURE 모드는 생략."]
    return {"title": "C2 R5 단계 전이도 (명세 c2_r5_diagram_spec.json)", "groups": {}, "nodes": nodes,
            "edges": edges, "legend": legend_rec(rows, notes, meter)}


# ---------------------------------------------------------------- 기하 도우미 (yEd 좌표: y 아래로 증가)


def poly_route(corners, arrow=8.0):
    """꺾은선 -> Graphviz B-스플라인 제어점(직선 구간) + 화살 끝."""
    tip = corners[-1]
    px, py = corners[-2]
    d = math.dist(tip, (px, py)) or 1.0
    k = min(arrow, d * 0.5) / d
    base = (tip[0] - (tip[0] - px) * k, tip[1] - (tip[1] - py) * k)
    pts = list(corners[:-1]) + [base]
    bez = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        bez += [(a[0] + (b[0] - a[0]) / 3, a[1] + (b[1] - a[1]) / 3),
                (a[0] + 2 * (b[0] - a[0]) / 3, a[1] + 2 * (b[1] - a[1]) / 3), b]
    return {"bez": bez, "tip": tip, "corners": list(corners)}


def _bez(p0, p1, p2, p3, t):
    u = 1 - t
    return (u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1])


def dense(route, n=12):
    bez = route["bez"]
    pts = [bez[0]]
    for i in range(0, len(bez) - 3, 3):
        pts += [_bez(*bez[i:i + 4], k / n) for k in range(1, n + 1)]
    pts.append(route["tip"])
    return pts


def path_mid(route):
    pts = dense(route)
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    half, acc = sum(seg) / 2, 0.0
    for (a, b), s in zip(zip(pts, pts[1:]), seg):
        if acc + s >= half and s > 0:
            t = (half - acc) / s
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        acc += s
    return pts[-1]


def graphml_bends(route):
    if "corners" in route:
        return route["corners"][1:-1]
    bez, out = route["bez"], []
    for i in range(0, len(bez) - 3, 3):
        seg = bez[i:i + 4]
        if i > 0:
            out.append(seg[0])
        out += [_bez(*seg, t) for t in (0.25, 0.5, 0.75)]
    return out


def box(c, w, h):
    return (c[0] - w / 2, c[1] - h / 2, c[0] + w / 2, c[1] + h / 2)


def overlap(a, b, tol=1.0):
    return a[0] < b[2] - tol and b[0] < a[2] - tol and a[1] < b[3] - tol and b[1] < a[3] - tol


def collisions(geo, model):
    """라벨-노드, 라벨-라벨 겹침 목록."""
    nb = {nid: box((v[0], v[1]), v[2], v[3]) for nid, v in geo["nodes"].items()}
    lb = {}
    for e in model["edges"]:
        g = geo["edges"][e["id"]]
        if e["label"]:
            lb[e["id"]] = box(g["lp"], e["lw"], e["lh"])
    out = []
    for eid, b in lb.items():
        for nid, n in nb.items():
            if overlap(b, n):
                out.append(f"label {eid} x node {nid}")
    ids = list(lb)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if overlap(lb[a], lb[b]):
                out.append(f"label {a} x label {b}")
    return out


# ---------------------------------------------------------------- Graphviz 배치 (블록도)


def find_dot(explicit):
    cands = [explicit, os.environ.get("GRAPHVIZ_DOT"), shutil.which("dot"),
             str(Path(sys.prefix) / "Library" / "bin" / "dot.exe"),
             r"C:\ProgramData\miniforge3\envs\python-dev\Library\bin\dot.exe"]
    for c in cands:
        if c and Path(c).is_file():
            return c
    sys.exit("graphviz 'dot'을 찾지 못했다: --dot 경로를 준다")


def neato_of(dot_exe):
    p = Path(dot_exe).with_name("neato" + Path(dot_exe).suffix)
    return str(p) if p.is_file() else (shutil.which("neato") or sys.exit("neato를 찾지 못했다"))


def layout_dot(model, rankdir, work: Path, stem: str, dot_exe: str, extra: list[str]) -> str:
    """크기 고정 노드·라벨 자리로 DOT을 쓴다(글자는 넘기지 않음: 배치만)."""
    L = [f"digraph {stem} {{",
         f"  graph [rankdir={rankdir}, newrank=true, nodesep=0.3, ranksep=0.42, splines=true, pad=0.2];",
         '  node [shape=box, fixedsize=true, label=""];', "  edge [arrowsize=0.8];"]
    children: dict = {}
    for g in model["groups"].values():
        children.setdefault(g["parent"], []).append(g["id"])
    members: dict = {}
    for n in model["nodes"]:
        members.setdefault(n["group"], []).append(n)

    def node_line(n, ind):
        L.append(f'{ind}{n["id"]} [width={n["w"] / 72:.4f}, height={n["h"] / 72:.4f}];')

    def emit(gid, ind):
        L.append(f"{ind}subgraph cluster_{gid} {{")
        L.append(f'{ind}  label=<<TABLE FIXEDSIZE="TRUE" WIDTH="60" HEIGHT="{GROUP_FS + 10}" BORDER="0" CELLPADDING="0">'
                 f'<TR><TD><FONT POINT-SIZE="1"> </FONT></TD></TR></TABLE>>; margin=12;')
        for sub in sorted(children.get(gid, []), key=lambda x: model["groups"][x]["order"]):
            emit(sub, ind + "  ")
        for n in members.get(gid, []):
            node_line(n, ind + "  ")
        L.append(f"{ind}}}")

    for gid in sorted(children.get(None, []), key=lambda x: model["groups"][x]["order"]):
        emit(gid, "  ")
    for n in members.get(None, []):
        node_line(n, "  ")
    for e in model["edges"]:
        if e.get("bus"):
            continue
        attrs = [f'id="{e["id"]}"']
        if e["label"]:
            attrs.append(f'label=<<TABLE FIXEDSIZE="TRUE" WIDTH="{e["lw"]:.0f}" HEIGHT="{e["lh"]:.0f}" '
                         f'BORDER="0" CELLPADDING="0"><TR><TD><FONT POINT-SIZE="1"> </FONT></TD></TR></TABLE>>')
        attrs += [f"{k}={v}" for k, v in e["dot"].items()]
        L.append(f'  {e["source"]} -> {e["target"]} [{", ".join(attrs)}];')
    L += ["  " + x for x in extra]
    L.append("}")
    src = work / f"{stem}.layout.dot"
    src.write_text("\n".join(L), encoding="utf-8")
    out = work / f"{stem}.layout.json"
    subprocess.run([dot_exe, "-Tjson", "-o", str(out), str(src)], check=True)
    return out.read_text(encoding="utf-8")


def _pt(s):
    x, y = s.split(",")[:2]
    return float(x), float(y)


def geo_from_dot(layout_json: str, model) -> dict:
    lay = json.loads(layout_json)
    _, _, _, ury = (float(v) for v in lay["bb"].split(","))

    def yx(p):
        return (p[0], ury - p[1])

    geo = {"nodes": {}, "groups": {}, "edges": {}}
    for o in lay.get("objects", []):
        name = o.get("name", "")
        if name.startswith("cluster_"):
            x0, y0, x1, y1 = (float(v) for v in o["bb"].split(","))
            geo["groups"][name[len("cluster_"):]] = (x0, ury - y1, x1, ury - y0)
        elif "pos" in o:
            c = yx(_pt(o["pos"]))
            geo["nodes"][name] = (c[0], c[1], float(o["width"]) * 72, float(o["height"]) * 72)
    for ge in lay.get("edges", []):
        eid = ge.get("id", "")
        if not eid.startswith(("e", "b")):
            continue
        tip, ctrl = None, []
        for tok in ge["pos"].split():
            if tok.startswith("e,"):
                tip = yx(_pt(tok[2:]))
            elif not tok.startswith("s,"):
                ctrl.append(yx(_pt(tok)))
        r = {"bez": ctrl, "tip": tip or ctrl[-1]}
        if "lp" in ge:
            r["lp"] = yx(_pt(ge["lp"]))
        geo["edges"][eid] = r
    return geo


def route_bus(geo, model):
    """플랜트 -> 센서 되먹임: 그림 왼쪽 가장자리 버스(줄기 공유) -> 위쪽 -> 각 센서 위로."""
    bus = [e for e in model["edges"] if e.get("bus")]
    if not bus:
        return
    xs = [b[0] for b in geo["groups"].values()] + [v[0] - v[2] / 2 for v in geo["nodes"].values()]
    ys = [b[1] for b in geo["groups"].values()] + [v[1] - v[3] / 2 for v in geo["nodes"].values()]
    for e in model["edges"]:  # 다른 엣지의 경로·라벨보다도 바깥에
        r = geo["edges"].get(e["id"])
        if e.get("bus") or r is None:
            continue
        for p in dense(r, 4):
            xs.append(p[0])
            ys.append(p[1])
        if e["label"] and "lp" in r:
            xs.append(r["lp"][0] - e["lw"] / 2)
            ys.append(r["lp"][1] - e["lh"] / 2)
    allx0, ally0 = min(xs), min(ys)
    lwmax = max(e["lw"] for e in bus)
    xb = allx0 - 24 - lwmax / 2
    yb = ally0 - 26
    for k, e in enumerate(bus):
        sx, sy, sw, sh = geo["nodes"][e["source"]]
        tx, ty, tw, th = geo["nodes"][e["target"]]
        ys = sy - sh / 2 + sh * (k + 1) / (len(bus) + 1)
        r = poly_route([(sx - sw / 2, ys), (xb, ys), (xb, yb), (tx, yb), (tx, ty - th / 2)])
        geo["edges"][e["id"]] = r


def place_legend(geo, model, where="right-bottom"):
    lg = model["legend"]
    xs = [b[2] for b in geo["groups"].values()] + [v[0] + v[2] / 2 for v in geo["nodes"].values()]
    ys = [b[3] for b in geo["groups"].values()] + [v[1] + v[3] / 2 for v in geo["nodes"].values()]
    if where == "right-bottom":
        cx, cy = max(xs) + 30 + lg["w"] / 2, max(ys) - lg["h"] / 2
    else:  # below-left
        x0 = min([b[0] for b in geo["groups"].values()] + [v[0] - v[2] / 2 for v in geo["nodes"].values()])
        cx, cy = x0 + lg["w"] / 2, max(ys) + 30 + lg["h"] / 2
    geo["nodes"]["LEGEND"] = (cx, cy, lg["w"], lg["h"])


def block_geometry(model, work, stem, dot_exe, same_rank, layout_only):
    extra = [f"{a} -> {b} [style=invis, weight={w}, id=\"inv{i}\"];" for i, (a, b, w) in enumerate(layout_only)]
    extra += ["{ rank=same; " + "; ".join(s) + "; }" for s in same_rank]
    geo = geo_from_dot(layout_dot(model, "TB", work, stem, dot_exe, extra), model)
    route_bus(geo, model)
    for e in model["edges"]:
        r = geo["edges"][e["id"]]
        if e["label"] and "lp" not in r:
            r["lp"] = path_mid(r)
    place_legend(geo, model, "right-bottom")
    # 참고: yEd centered 모델(경로 중간)에 라벨을 둘 때의 겹침 수
    mid = {"nodes": geo["nodes"], "edges": {k: dict(v, lp=path_mid(v)) for k, v in geo["edges"].items()}}
    geo["midpoint_collisions"] = len(collisions(mid, model))
    return geo


# ---------------------------------------------------------------- 단계도 직접 배치


def phase_geometry(model) -> dict:
    N = {n["id"]: n for n in model["nodes"]}
    E = {e["id"]: e for e in model["edges"]}
    nodes, edges = {}, {}
    col = ["START", "CHECK", "TOUCH", "LEVEL", "DONE", "PROBE", "REANCHOR", "READY"]
    between = {("START", "CHECK"): "e01", ("CHECK", "TOUCH"): "e03", ("TOUCH", "LEVEL"): "e06",
               ("LEVEL", "DONE"): "e07", ("DONE", "PROBE"): "e09", ("PROBE", "REANCHOR"): "e12"}
    y = 0.0
    for i, nid in enumerate(col):
        if i:
            prev = col[i - 1]
            eid = between.get((prev, nid))
            gap = max(46.0, (E[eid]["lh"] + 30) if eid else 56.0)
            if (prev, nid) == ("CHECK", "TOUCH"):  # IDLE -> CHECK 엣지 라벨이 지나갈 자리
                gap = max(gap, E["e05"]["lh"] + 70)
            y += N[prev]["h"] / 2 + gap + N[nid]["h"] / 2
        nodes[nid] = (0.0, y, N[nid]["w"], N[nid]["h"])

    def nb(nid):
        x, yy, w, h = nodes[nid]
        return x - w / 2, yy - h / 2, x + w / 2, yy + h / 2

    for (a, b), eid in between.items():  # 주 경로: 아래로 곧게
        edges[eid] = poly_route([(0.0, nb(a)[3]), (0.0, nb(b)[1])])

    # IDLE: CHECK 왼쪽, 같은 행
    cx0, cy0, cx1, cy1 = nb("CHECK")
    yC = nodes["CHECK"][1]
    gap_i = max(E["e04"]["lw"] + 40, 150.0)
    ix = cx0 - gap_i - N["IDLE"]["w"] / 2
    nodes["IDLE"] = (ix, yC, N["IDLE"]["w"], N["IDLE"]["h"])
    ib = nb("IDLE")
    edges["e04"] = poly_route([(cx0, yC - 10), (ib[2], yC - 10)])
    yb = max(cy1, ib[3]) + 18 + E["e05"]["lh"] / 2
    edges["e05"] = poly_route([(ix + N["IDLE"]["w"] / 4, ib[3]), (ix + N["IDLE"]["w"] / 4, yb),
                               (cx0 - 22, yb), (cx0 - 22, yC + 14), (cx0, yC + 14)])
    # CHECK 자기 루프: 오른쪽
    L = E["e02"]["lw"] / 2 + 18
    edges["e02"] = poly_route([(cx1, yC - 12), (cx1 + L, yC - 12), (cx1 + L, yC + 12), (cx1, yC + 12)])

    # FAULT: LEVEL 왼쪽, 같은 행
    lx0, ly0, lx1, ly1 = nb("LEVEL")
    yL = nodes["LEVEL"][1]
    gap_f = max(E["e08"]["lw"] + 40, 150.0)
    fx = lx0 - gap_f - N["FAULT"]["w"] / 2
    nodes["FAULT"] = (fx, yL, N["FAULT"]["w"], N["FAULT"]["h"])
    edges["e08"] = poly_route([(lx0, yL), (fx + N["FAULT"]["w"] / 2, yL)])

    # 주 경로 라벨 자리(차선 계산의 장애물)
    obstacles = [nb(n) for n in nodes]
    for eid in between.values():
        obstacles.append(box(path_mid(edges[eid]), E[eid]["lw"], E[eid]["lh"]))

    def span_extent(y_lo, y_hi, side):
        xs = [b[2] if side > 0 else b[0] for b in obstacles if b[1] < y_hi and b[3] > y_lo]
        return max(xs) if side > 0 else min(xs)

    # 왼쪽 차선: PROBE -> READY(안쪽), DONE -> READY(바깥)
    yR = nodes["READY"][1]
    rb = nb("READY")
    x_prev = None
    for k, (eid, src) in enumerate((("e13", "PROBE"), ("e10", "DONE"))):
        ys = nodes[src][1]
        lim = span_extent(ys, yR, -1)
        x = lim - 20 - E[eid]["lw"] / 2
        if x_prev is not None:
            x = min(x, x_prev - E["e13"]["lw"] / 2 - 18 - E[eid]["lw"] / 2)
        x_prev = x
        ye = yR - 9 if k == 0 else yR + 9
        edges[eid] = poly_route([(nb(src)[0], ys), (x, ys), (x, ye), (rb[0], ye)])

    # 오른쪽 차선: LEVEL로 되돌아가는 7개, 안쪽부터
    order = [("e16", "DONE"), ("e11", "PROBE"), ("e17", "PROBE"), ("e14", "REANCHOR"), ("e15", "REANCHOR"),
             ("e18", "READY"), ("e19", "READY")]
    seen: dict = {}
    n_in = len(order)
    x_prev, w_prev = None, 0.0
    for k, (eid, src) in enumerate(order):
        cnt = sum(1 for _, s in order if s == src)
        idx = seen.get(src, 0)
        seen[src] = idx + 1
        ys = nodes[src][1] + (0.0 if cnt == 1 else (-9.0 if idx == 0 else 9.0))
        y_in = ly1 - 10 - k * (nodes["LEVEL"][3] - 20) / (n_in - 1)
        lim = span_extent(y_in, ys, +1)
        x = lim + 20 + E[eid]["lw"] / 2
        if x_prev is not None:
            x = max(x, x_prev + w_prev / 2 + 16 + E[eid]["lw"] / 2)
        x_prev, w_prev = x, E[eid]["lw"]
        edges[eid] = poly_route([(nb(src)[2], ys), (x, ys), (x, y_in), (lx1, y_in)])

    # READY 자기 루프: 아래
    L = E["e20"]["lh"] / 2 + 16
    edges["e20"] = poly_route([(-16.0, rb[3]), (-16.0, rb[3] + L), (16.0, rb[3] + L), (16.0, rb[3])])

    geo = {"nodes": nodes, "groups": {}, "edges": edges}
    for e in model["edges"]:
        if e["label"]:
            edges[e["id"]]["lp"] = path_mid(edges[e["id"]])
    # 범례: 모든 것 아래, 왼쪽 정렬
    lbs = [box(edges[e["id"]]["lp"], e["lw"], e["lh"]) for e in model["edges"] if e["label"]]
    x0 = min([b[0] for b in obstacles + lbs] + [p[0] for r in edges.values() for p in r["corners"]])
    y1 = max([b[3] for b in obstacles + lbs] + [p[1] for r in edges.values() for p in r["corners"]])
    lg = model["legend"]
    nodes["LEGEND"] = (x0 + lg["w"] / 2, y1 + 34 + lg["h"] / 2, lg["w"], lg["h"])
    return geo


# ---------------------------------------------------------------- 그리기 (neato -n2: 주어진 좌표 그대로)


def bounds(geo, model, margin=24.0):
    xs, ys = [], []
    for x, y, w, h in geo["nodes"].values():
        xs += [x - w / 2, x + w / 2]
        ys += [y - h / 2, y + h / 2]
    for b in geo["groups"].values():
        xs += [b[0], b[2]]
        ys += [b[1], b[3]]
    for e in model["edges"]:
        r = geo["edges"][e["id"]]
        for p in dense(r, 4):
            xs.append(p[0])
            ys.append(p[1])
        if e["label"]:
            b = box(r["lp"], e["lw"], e["lh"])
            xs += [b[0], b[2]]
            ys += [b[1], b[3]]
    return min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin


def shift(geo, dx, dy):
    geo["nodes"] = {k: (x + dx, y + dy, w, h) for k, (x, y, w, h) in geo["nodes"].items()}
    geo["groups"] = {k: (b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy) for k, b in geo["groups"].items()}
    for r in geo["edges"].values():
        r["bez"] = [(x + dx, y + dy) for x, y in r["bez"]]
        r["tip"] = (r["tip"][0] + dx, r["tip"][1] + dy)
        if "corners" in r:
            r["corners"] = [(x + dx, y + dy) for x, y in r["corners"]]
        if "lp" in r:
            r["lp"] = (r["lp"][0] + dx, r["lp"][1] + dy)


def normalise(geo, model):
    x0, y0, x1, y1 = bounds(geo, model)
    shift(geo, -x0, -y0)
    geo["W"], geo["H"] = x1 - x0, y1 - y0


def render_dot(geo, model) -> str:
    H = geo["H"]

    def gv(p):
        return f"{p[0]:.2f},{H - p[1]:.2f}"

    L = ["digraph R {", "  graph [outputorder=nodesfirst, splines=true, pad=0.1, bgcolor=white];",
         f'  node [fontname="{FONT}", fixedsize=true];',
         f'  edge [fontname="{FONT}", fontsize={EDGE_FS}, arrowsize=0.8];']
    depth = {}
    for gid, g in model["groups"].items():
        d, p = 0, g["parent"]
        while p:
            d, p = d + 1, model["groups"][p]["parent"]
        depth[gid] = d
    for gid in sorted(geo["groups"], key=lambda k: depth.get(k, 0)):
        x0, y0, x1, y1 = geo["groups"][gid]
        bg, border, _ = GROUP_STYLE[gid]
        w = x1 - x0
        title = esc_html(model["groups"][gid]["label"])
        L.append(f'  "grp_{gid}" [pos="{gv(((x0 + x1) / 2, (y0 + y1) / 2))}!", width={w / 72:.4f}, '
                 f'height={(y1 - y0) / 72:.4f}, shape=box, style="rounded,filled", fillcolor="{bg}", '
                 f'color="{border}", penwidth=1.4, labelloc=t, label=<<TABLE BORDER="0" CELLPADDING="3" '
                 f'WIDTH="{max(w - 14, 20):.0f}"><TR><TD ALIGN="LEFT"><FONT POINT-SIZE="{GROUP_FS}">'
                 f'<B>{title}</B></FONT></TD></TR></TABLE>>];')
    for n in model["nodes"]:
        x, y, w, h = geo["nodes"][n["id"]]
        shape = {"ellipse": "ellipse", "octagon": "octagon"}.get(n["shape"], "box")
        style = "rounded,filled" if shape == "box" else "filled"
        if n["border_style"] == "dashed":
            style += ",dashed"
        L.append(f'  {n["id"]} [pos="{gv((x, y))}!", width={w / 72:.4f}, height={h / 72:.4f}, shape={shape}, '
                 f'style="{style}", fillcolor="{n["fill"]}", color="{n["border"]}", penwidth=1.2, '
                 f'fontsize={n["fs"]}, label={q(n["label"])}];')
    lg = model["legend"]
    x, y, w, h = geo["nodes"]["LEGEND"]
    rows = [f'<TR><TD ALIGN="LEFT"><B>범례</B></TD></TR>']
    rows += [f'<TR><TD ALIGN="LEFT"><FONT COLOR="{c}"><B>{esc_html(s)}</B></FONT>  {esc_html(t)}</TD></TR>'
             for c, s, t in lg["rows"]]
    rows += [f'<TR><TD ALIGN="LEFT">{esc_html(t)}</TD></TR>' for t in lg["notes"]]
    L.append(f'  LEGEND [pos="{gv((x, y))}!", width={w / 72:.4f}, height={h / 72:.4f}, shape=box, style=filled, '
             f'fillcolor="#FFFFFF", color="#9E9E9E", fontsize={LEGEND_FS}, label=<<TABLE BORDER="0" '
             f'CELLPADDING="0" CELLSPACING="0">{"".join(rows)}</TABLE>>];')
    L.append(f'  _c0 [pos="0,0!", width=0.01, height=0.01, style=invis, label=""];')
    L.append(f'  _c1 [pos="{geo["W"]:.2f},{H:.2f}!", width=0.01, height=0.01, style=invis, label=""];')
    for e in model["edges"]:
        r = geo["edges"][e["id"]]
        pos = f"e,{gv(r['tip'])} " + " ".join(gv(p) for p in r["bez"])
        attrs = [f'id="{e["id"]}"', f'pos="{pos}"', f'color="{e["color"]}"', f'penwidth={e["width"]}']
        if e["style"] != "solid":
            attrs.append(f'style={e["style"]}')
        if e["label"]:
            text = "<BR/>".join(esc_html(ln) for ln in e["label"].split("\n"))
            attrs += [f'lp="{gv(r["lp"])}"', f'fontcolor="{e["color"]}"',
                      f'label=<<TABLE BORDER="0" CELLPADDING="1" CELLSPACING="0" BGCOLOR="white"><TR><TD>{text}'
                      f'</TD></TR></TABLE>>']
        L.append(f'  {e["source"]} -> {e["target"]} [{", ".join(attrs)}];')
    L.append("}")
    return "\n".join(L)


def render(geo, model, neato, work: Path, out_stem: Path, hires: bool) -> dict:
    src = work / f"{out_stem.name}.render.dot"
    src.write_text(render_dot(geo, model), encoding="utf-8")
    longest_in = max(geo["W"], geo["H"]) / 72
    dpi = min(HIRES_DPI, int(SCREEN_MAX_PX / longest_in))
    subprocess.run([neato, "-n2", "-Tsvg", "-o", str(out_stem.with_suffix(".svg")), str(src)], check=True)
    subprocess.run([neato, "-n2", f"-Gdpi={dpi}", "-Tpng", "-o", str(out_stem.with_suffix(".png")), str(src)],
                   check=True)
    info = {"screen_dpi": dpi, "size_pt": [round(geo["W"]), round(geo["H"])]}
    if hires and dpi < HIRES_DPI:
        hp = out_stem.with_name(out_stem.name + "_hires.png")
        subprocess.run([neato, "-n2", f"-Gdpi={HIRES_DPI}", "-Tpng", "-o", str(hp), str(src)], check=True)
        info["hires"] = str(hp)
    return info


# ---------------------------------------------------------------- yEd GraphML

NS = {
    "": "http://graphml.graphdrawing.org/xmlns",
    "java": "http://www.yworks.com/xml/yfiles-common/1.0/java",
    "sys": "http://www.yworks.com/xml/yfiles-common/markup/primitives/2.0",
    "x": "http://www.yworks.com/xml/yfiles-common/markup/2.0",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "y": "http://www.yworks.com/xml/graphml",
    "yed": "http://www.yworks.com/xml/yed/3",
}
for _p, _u in NS.items():
    ET.register_namespace(_p, _u)
G = "{%s}" % NS[""]
Y = "{%s}" % NS["y"]
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def _sub(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})


def _label(parent, tag, text, **attrs):
    el = _sub(parent, tag, **attrs)
    el.set(XML_SPACE, "preserve")
    el.text = text
    return el


def write_graphml(model, geo, path: Path) -> dict:
    root = ET.Element(G + "graphml")
    root.set("{%s}schemaLocation" % NS["xsi"],
             "http://graphml.graphdrawing.org/xmlns http://www.yworks.com/xml/schema/graphml/1.1/ygraphml.xsd")
    keys = [("d0", "graph", "Description", "string", None), ("d1", "port", None, None, "portgraphics"),
            ("d2", "port", None, None, "portgeometry"), ("d3", "port", None, None, "portuserdata"),
            ("d4", "node", "url", "string", None), ("d5", "node", "description", "string", None),
            ("d6", "node", None, None, "nodegraphics"), ("d7", "graphml", None, None, "resources"),
            ("d8", "edge", "url", "string", None), ("d9", "edge", "description", "string", None),
            ("d10", "edge", None, None, "edgegraphics")]
    names = sorted({k for e in model["edges"] for k in e["data"]})
    ekey = {}
    for i, name in enumerate(names):
        typ = "boolean" if all(isinstance(e["data"].get(name, False), bool) for e in model["edges"]) else "string"
        keys.append((f"d{11 + i}", "edge", name, typ, None))
        ekey[name] = (f"d{11 + i}", typ)
    for kid, for_, an, at, yt in keys:
        k = _sub(root, G + "key", id=kid, **{"for": for_})
        if an:
            k.set("attr.name", an)
            k.set("attr.type", at)
        if yt:
            k.set("yfiles.type", yt)
    graph = _sub(root, G + "graph", id="G", edgedefault="directed")
    _sub(graph, G + "data", key="d0").text = model["title"]

    def add_node(pg, n, geom, text, fs, align="center"):
        cx, cy, w, h = geom
        el = _sub(pg, G + "node", id=n["id"])
        if n.get("description"):
            _sub(el, G + "data", key="d5").text = n["description"]
        sn = _sub(_sub(el, G + "data", key="d6"), Y + "ShapeNode")
        _sub(sn, Y + "Geometry", x=f"{cx - w / 2:.2f}", y=f"{cy - h / 2:.2f}", width=f"{w:.2f}", height=f"{h:.2f}")
        _sub(sn, Y + "Fill", color=n["fill"], transparent="false")
        _sub(sn, Y + "BorderStyle", color=n["border"], raised="false", type=n["border_style"], width="1.0")
        _label(sn, Y + "NodeLabel", text, alignment=align, autoSizePolicy="content", fontFamily=FONT,
               fontSize=fs, fontStyle="plain", hasBackgroundColor="false", hasLineColor="false",
               modelName="internal", modelPosition="c", textColor="#000000", visible="true")
        _sub(sn, Y + "Shape", type=n["shape"])

    children: dict = {}
    for g in model["groups"].values():
        children.setdefault(g["parent"], []).append(g["id"])
    members: dict = {}
    for n in model["nodes"]:
        members.setdefault(n["group"], []).append(n)

    def add_group(pg, gid):
        g = model["groups"][gid]
        bg, border, _ = GROUP_STYLE[gid]
        x0, y0, x1, y1 = geo["groups"][gid]
        el = _sub(pg, G + "node", id=gid)
        el.set("yfiles.foldertype", "group")
        rz = _sub(_sub(_sub(el, G + "data", key="d6"), Y + "ProxyAutoBoundsNode"), Y + "Realizers", active="0")
        for closed in (False, True):
            gn = _sub(rz, Y + "GroupNode")
            cw = max(80.0, len(g["label"]) * 14 + 16)
            _sub(gn, Y + "Geometry", x=f"{x0:.2f}", y=f"{y0:.2f}", width=f"{cw if closed else x1 - x0:.2f}",
                 height=f"{50.0 if closed else y1 - y0:.2f}")
            _sub(gn, Y + "Fill", color=bg, transparent="false")
            _sub(gn, Y + "BorderStyle", color=border, type="line", width="1.4")
            _label(gn, Y + "NodeLabel", g["label"], alignment="left", autoSizePolicy="node_width",
                   backgroundColor=bg, fontFamily=FONT, fontSize=GROUP_FS, fontStyle="bold", hasLineColor="false",
                   modelName="internal", modelPosition="t", textColor="#000000", visible="true")
            _sub(gn, Y + "Shape", type="roundrectangle")
            _sub(gn, Y + "State", closed=str(closed).lower(), closedHeight="50.0", closedWidth=f"{cw:.1f}",
                 innerGraphDisplayEnabled="false")
            _sub(gn, Y + "Insets", bottom="10", bottomF="10.0", left="10", leftF="10.0", right="10",
                 rightF="10.0", top="10", topF="10.0")
            _sub(gn, Y + "BorderInsets", bottom="0", bottomF="0.0", left="0", leftF="0.0", right="0",
                 rightF="0.0", top="0", topF="0.0")
        sub = _sub(el, G + "graph", id=f"{gid}:", edgedefault="directed")
        for c in children.get(gid, []):
            add_group(sub, c)
        for n in members.get(gid, []):
            add_node(sub, n, geo["nodes"][n["id"]], n["label"], n["fs"])

    for gid in children.get(None, []):
        add_group(graph, gid)
    for n in members.get(None, []):
        add_node(graph, n, geo["nodes"][n["id"]], n["label"], n["fs"])
    legend = {"id": "LEGEND", "description": "범례 (그림 주석, 명세 노드 아님)", "fill": "#FFFFFF",
              "border": "#9E9E9E", "border_style": "line", "shape": "rectangle"}
    add_node(graph, legend, geo["nodes"]["LEGEND"], model["legend"]["text"], LEGEND_FS, align="left")

    for e in model["edges"]:
        r = geo["edges"][e["id"]]
        s, t = r["bez"][0], r["tip"]
        sc, tc = geo["nodes"][e["source"]], geo["nodes"][e["target"]]
        el = _sub(graph, G + "edge", id=e["id"], source=e["source"], target=e["target"])
        for name, val in e["data"].items():
            kid, typ = ekey[name]
            _sub(el, G + "data", key=kid).text = str(val).lower() if typ == "boolean" else str(val)
        pl = _sub(_sub(el, G + "data", key="d10"), Y + "PolyLineEdge")
        pe = _sub(pl, Y + "Path", sx=f"{s[0] - sc[0]:.2f}", sy=f"{s[1] - sc[1]:.2f}",
                  tx=f"{t[0] - tc[0]:.2f}", ty=f"{t[1] - tc[1]:.2f}")
        for bx, by in graphml_bends(r):
            _sub(pe, Y + "Point", x=f"{bx:.2f}", y=f"{by:.2f}")
        _sub(pl, Y + "LineStyle", color=e["color"], type=LINE_STYLE[e["style"]], width=f"{e['width']:.1f}")
        _sub(pl, Y + "Arrows", source="none", target="standard")
        if e["label"]:
            _label(pl, Y + "EdgeLabel", e["label"], alignment="center", backgroundColor="#FFFFFF",
                   fontFamily=FONT, fontSize=EDGE_FS, fontStyle="plain", hasLineColor="false", modelName="centered",
                   modelPosition="center", textColor=e["color"], visible="true")
        _sub(pl, Y + "BendStyle", smoothed="false" if "corners" in r else "true")
    _sub(_sub(root, G + "data", key="d7"), Y + "Resources")
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    with open(path, "wb") as fh:
        fh.write(b'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
        fh.write(b"<!-- Created by plot_c2_block_diagram.py -->\n")
        tree.write(fh, encoding="utf-8", xml_declaration=False)
    return {"nodes": len(model["nodes"]), "groups": len(model["groups"]), "edges": len(model["edges"])}


# ---------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--out-dir", type=Path, default=None, help="기본: 명세 파일 폴더")
    ap.add_argument("--dot", default=None, help="dot.exe 경로(neato.exe는 같은 폴더)")
    ap.add_argument("--keep-intermediate", type=Path, default=None, help=".dot·배치 JSON을 남길 폴더")
    args = ap.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    out_dir = args.out_dir or args.spec.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    dot_exe = find_dot(args.dot)
    neato = neato_of(dot_exe)
    work = args.keep_intermediate or Path(tempfile.mkdtemp(prefix="c2_diagram_"))
    work.mkdir(parents=True, exist_ok=True)
    meter = Meter()
    bd, pf = spec["block_diagram"], spec["phase_flow"]
    summary = {"text_metrics": "pillow" if meter._IF else "estimate"}
    try:
        jobs = []
        m = block_model(bd, meter)
        jobs.append((bd["file_stem"], m, block_geometry(m, work, "block", dot_exe, BLOCK_SAME_RANK,
                                                        BLOCK_LAYOUT_ONLY), True))
        m = overview_model(bd, meter)
        jobs.append(("c2_r5_block_overview", m, block_geometry(m, work, "overview", dot_exe, [], []), False))
        m = phase_model(pf, meter)
        jobs.append((pf["file_stem"], m, phase_geometry(m), False))
        for stem, model, geo, hires in jobs:
            normalise(geo, model)
            info = render(geo, model, neato, work, out_dir / stem, hires)
            counts = write_graphml(model, geo, out_dir / f"{stem}.graphml")
            summary[stem] = {**counts, **info, "label_collisions": collisions(geo, model),
                           "yed_midpoint_label_collisions": geo.get("midpoint_collisions", 0)}
    finally:
        if args.keep_intermediate is None:
            shutil.rmtree(work, ignore_errors=True)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
