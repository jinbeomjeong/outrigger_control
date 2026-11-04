"""Hopsan 모델 구조도 재생성 스크립트.

.hmf가 유일한 원본이다. 부품·포트·연결·파라미터 값은 실행할 때 .hmf(와 그 파일이 참조하는
LU_*.csv)에서 읽는다. 이 파일에는 배치(좌표 규칙)와 표시 형식만 있다.
.hmf에 없는 부품을 그리거나 .hmf의 연결을 빠뜨리면 실행이 실패한다.

실행(python-dev):
  C:\\ProgramData\\miniforge3\\envs\\python-dev\\python.exe -I -B make_hopsan_diagrams.py [--out-dir DIR]

산출: <키>_<이름>.graphml(yEd), .png(같은 모델을 matplotlib으로 그림), overview.png, verification.json
의존: matplotlib, pillow, lxml, defusedxml, ~/.claude/tools/graphml(_ywriter, _ygraphml)
포트 종류는 Hopsan 설치본 기본 라이브러리(.hpp)에서 읽는다.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

os.environ.setdefault("MKL_THREADING_LAYER", "TBB")
sys.stdout.reconfigure(encoding="utf-8")
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path.home() / ".claude" / "tools" / "graphml"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from defusedxml import ElementTree as SafeET  # noqa: E402
from lxml import etree  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle  # noqa: E402
from PIL import ImageFont  # noqa: E402

import _ywriter as yw  # noqa: E402
from _ygraphml import Geometry, format_number, g_tag, y_tag  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
HYD = REPO / "04_scripts" / "04_hydraulic"
HOPSAN_LIB = Path(r"C:\Program Files\Hopsan\componentLibraries\defaultLibrary")
FONT = r"C:\Windows\Fonts\malgun.ttf"
FONT_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"
YED_FONT = "Dialog"

# 도메인 색: 파랑·주황은 적록 색각 이상에서도 갈리는 축이고, 신호는 무채색 + 점선 + 화살표로 한 번 더 구분한다.
DOMAIN = {
    "hydraulic": dict(ko="유압", en="Hydraulic", line="#0072B2", fill="#BBDAF0", group="#F3F8FC", text="#00507D", style="line"),
    "mechanic": dict(ko="기계 부하", en="Mechanic", line="#D55E00", fill="#F8CBA8", group="#FEF7F1", text="#9C4400", style="line"),
    "signal": dict(ko="입력 신호", en="Signal", line="#4D4D4D", fill="#E2E2E2", group="#F9F9F9", text="#333333", style="dashed"),
}
INK = "#1A1A1A"
MUTED = "#595959"
LINE_H = {9: 13, 10: 14, 11: 15, 12: 17, 13: 18, 14: 19, 18: 25}


# ------------------------------------------------------------------ 글자 측정
_fonts: dict = {}


def font(size: int, bold: bool = False):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_BOLD if bold else FONT, size)
    return _fonts[key]


def tw(text: str, size: int, bold: bool = False) -> float:
    return max((font(size, bold).getlength(s) for s in text.split("\n")), default=0.0)


def ascent(size: int, bold: bool = False) -> float:
    return font(size, bold).getmetrics()[0]


# ------------------------------------------------------------------ 모델
@dataclass
class Text:
    text: str
    rx: float
    ry: float
    w: float
    h: float
    size: int = 10
    bold: bool = False
    color: str = INK
    align: str = "center"
    kind: str = "body"  # body | port


@dataclass
class Node:
    key: str
    role: str  # component | title | note | legend
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0
    fill: str | None = None
    border: str | None = None
    style: str = "line"
    bw: float = 1.0
    shape: str = "rectangle"
    texts: list[Text] = field(default_factory=list)
    domain: str = ""
    typename: str = ""
    group: str | None = None

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    @property
    def rect(self):
        return self.x, self.y, self.x + self.w, self.y + self.h


@dataclass
class Edge:
    start: str
    sport: str
    end: str
    eport: str
    domain: str
    pts: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class Group:
    domain: str
    x: float
    y: float
    w: float
    h: float
    label: str


# ------------------------------------------------------------------ .hmf 읽기
def read_hmf(path: Path) -> dict:
    root = SafeET.parse(path).getroot()
    systems = root.findall(".//system")
    if len(systems) != 1:
        raise SystemExit(f"{path}: 하위 시스템이 있는 모델은 이 스크립트 범위 밖이다 ({len(systems)})")
    sysm = systems[0]
    comps = {}
    for c in sysm.find("objects"):
        comps[c.get("name")] = {
            "tag": c.tag,
            "type": c.get("typename"),
            "params": {p.get("name"): p.get("value") for p in c.findall("./parameters/parameter")},
            "units": {p.get("name"): p.get("unit") for p in c.findall("./parameters/parameter") if p.get("unit")},
        }
    conns = [
        (c.get("startcomponent"), c.get("startport"), c.get("endcomponent"), c.get("endport"))
        for c in sysm.find("connections")
    ]
    return {"path": path, "system": sysm.get("name"), "sim": dict(sysm.find("simulationtime").attrib), "comps": comps, "conns": conns}


def read_library(types: set[str]) -> dict:
    """부품 형식별 포트 선언(전력 포트와 도메인, 입력·출력 변수)을 Hopsan 라이브러리에서 읽는다."""
    pat = re.compile(r'(addPowerPort|addInputVariable|addOutputVariable)\s*\(\s*"([^"]+)"\s*(?:,\s*"([^"]*)")?')
    lib = {}
    index = {p.stem: p for p in HOPSAN_LIB.rglob("*.hpp")}
    for t in types:
        if t not in index:
            raise SystemExit(f"Hopsan 라이브러리에 {t}.hpp 가 없다: {HOPSAN_LIB}")
        src = index[t].read_text(encoding="utf-8", errors="replace")
        e = {"power": {}, "inputs": set(), "outputs": set()}
        for kind, name, second in pat.findall(src):
            if kind == "addPowerPort":
                e["power"][name] = second
            elif kind == "addInputVariable":
                e["inputs"].add(name)
            else:
                e["outputs"].add(name)
        lib[t] = e
    return lib


def port_domain(lib_entry: dict, port: str) -> str:
    node = lib_entry["power"].get(port)
    if node == "NodeHydraulic":
        return "hydraulic"
    if node == "NodeMechanic":
        return "mechanic"
    if port in lib_entry["inputs"] or port in lib_entry["outputs"]:
        return "signal"
    raise SystemExit(f"라이브러리에 없는 포트: {port}")


def type_domain(typename: str) -> str:
    if typename.startswith("Hydraulic"):
        return "hydraulic"
    if typename.startswith("Mechanic"):
        return "mechanic"
    if typename.startswith("Signal"):
        return "signal"
    raise SystemExit(f"도메인을 알 수 없는 형식: {typename}")


def read_csv_points(path: Path) -> list[tuple[float, float]]:
    return [tuple(float(x) for x in line.split(",")[:2]) for line in path.read_text(encoding="ascii").split() if line]


# ------------------------------------------------------------------ 값 표시
def g5(v: float, digits: int = 5) -> str:
    s = f"{v:.{digits}g}"
    if "e" in s:
        m, e = s.split("e")
        s = f"{m}e{int(e)}"
    return s


FORMATS = {
    "raw": lambda v: g5(float(v)),
    "raw7": lambda v: g5(float(v), 7),
    "m2": lambda v: f"{g5(float(v))} m²",
    "m3": lambda v: f"{g5(float(v))} m³",
    "m": lambda v: f"{g5(float(v))} m",
    "Ns": lambda v: f"{g5(float(v), 6)} N·s/m",
    "Nm": lambda v: f"{g5(float(v))} N/m",
    "GPa": lambda v: f"{g5(float(v) / 1e9)} GPa",
    "barabs": lambda v: f"{g5(float(v) / 1e5)} bar abs",
    "bar": lambda v: f"{g5(float(v) / 1e5)} bar",
    "kN": lambda v: f"{g5(float(v) / 1e3)} kN",
    "kg": lambda v: f"{g5(float(v), 6)} kg",
    "s": lambda v: f"{g5(float(v))} s",
    "leak": lambda v: f"{g5(float(v))} (m³/s)/Pa",
    "m3s": lambda v: f"{g5(float(v))} m³/s",
    "rho": lambda v: f"{g5(float(v))} kg/m³",
    "str": str,
}

# (파라미터 키, 표시 이름, 형식). 단위는 .hmf의 unit 속성 또는 Hopsan 라이브러리 선언, abs는 hopsan_single_leg.py 머리말.
PARAM_LINES = {
    "HydraulicCylinderC": [
        ("A_1#Value", "A_1", "m2"), ("A_2#Value", "A_2", "m2"), ("s_l#Value", "s_l", "m"),
        ("V_1#Value", "V_1", "m3"), ("V_2#Value", "V_2", "m3"), ("B_p#Value", "B_p", "Ns"),
        ("Beta_e#Value", "Beta_e", "GPa"), ("c_leak#Value", "c_leak", "leak"), ("use_sl", "use_sl", "str"),
        ("P1#Pressure", "P1 초기 압력", "barabs"), ("P2#Pressure", "P2 초기 압력", "barabs"),
        ("P3#Position", "P3 초기 위치", "m"), ("P3#Force", "P3 초기 힘", "kN"),
    ],
    "MechanicTranslationalMass": [("m", "m", "kg"), ("B#Value", "B", "Ns"), ("k#Value", "k", "Nm")],
    "MechanicTranslationalSpring": [("k#Value", "k", "Nm"), ("P1#Force", "초기 힘", "kN")],
    "MechanicForceTransformer": [("F#Value", "F", "kN"), ("P1#Force", "P1 초기 힘", "kN")],
    "Signal1DLookupTable": [("filename", "filename", "str")],
    "HydraulicFlowSourceQ": [("q#Value", "q", "m3s")],
    "HydraulicPressureSourceC": [("p#Value", "p", "barabs")],
    "HydraulicTankC": [("p", "p", "barabs")],
    "HydraulicPressureReliefValve": [
        ("p_max#Value", "p_max", "barabs"), ("tao#Value", "tao", "s"), ("p_h#Value", "p_h", "bar"),
        ("k_cs", "k_cs", "leak"), ("k_cf", "k_cf", "leak"), ("q_nom", "q_nom", "m3s"),
    ],
    "HydraulicOverCenterValve": [
        ("p_ref#Value", "p_ref", "barabs"), ("p_h#Value", "p_h", "bar"), ("a_ratio#Value", "a_ratio", "raw"),
        ("tao", "tao", "s"), ("k_cs", "k_cs", "leak"), ("k_cf", "k_cf", "leak"),
        ("q_nom", "q_nom", "m3s"), ("p_nom", "p_nom", "bar"),
    ],
    "Hydraulic22Valve": [
        ("C_q#Value", "C_q", "raw"), ("rho#Value", "rho", "rho"), ("d#Value", "d", "m"), ("f#Value", "f", "raw"),
        ("x_vmax#Value", "x_vmax", "m"), ("omega_h", "omega_h", "raw"), ("delta_h", "delta_h", "raw"),
    ],
    "HydraulicTurbulentOrifice": [("A#Value", "A", "m2")],
    "SignalRamp": [("y_0#Value", "y_0", "raw7"), ("y_A#Value", "y_A", "raw7"), ("t_start#Value", "t_start", "s"), ("t_end#Value", "t_end", "s")],
    "SignalTime": [],
    "SignalAdd": [],
    "HydraulicPlugQ": [],
}


def component_lines(name: str, comp: dict, conns: list) -> list[str]:
    wired = {ep for a, sp, b, ep in conns if b == name}
    lines = []
    for key, label, kind in PARAM_LINES[comp["type"]]:
        if key not in comp["params"]:
            continue
        value = FORMATS[kind](comp["params"][key])
        base = key.split("#")[0]
        if key.endswith("#Value") and base in wired:
            lines.append(f"{label}: 신호 입력 (#Value {value})")
        else:
            lines.append(f"{label} = {value}")
    return lines or ["(파라미터 없음)"]


# ------------------------------------------------------------------ 부품 노드 크기
def make_component(name: str, comp: dict, lib: dict, conns: list, sides: dict, min_h: float = 0, min_w: float = 0) -> Node:
    """sides = {port: (side, 절대좌표 또는 None)}. 좌표는 place 단계에서 정한다."""
    entry = lib[comp["type"]]
    params = component_lines(name, comp, conns)
    connected = {sp for a, sp, b, ep in conns if a == name} | {ep for a, sp, b, ep in conns if b == name}
    unconnected_out = sorted(entry["outputs"] - connected)
    dom = type_domain(comp["type"])
    pad = {"L": 8.0, "R": 8.0}
    for port, (side, _) in sides.items():
        if side in pad:
            pad[side] = max(pad[side], tw(port, 10, True) + 16)
    has_t = any(s == "T" for s, _ in sides.values())
    has_b = any(s == "B" for s, _ in sides.values())
    top_res = 15 if has_t else 2
    bot_res = 15 if has_b else 3
    unconn = f"미연결 출력: {', '.join(unconnected_out)}" if unconnected_out else ""
    pw = max(tw(s, 10) for s in params)
    if unconn:
        pw = max(pw, tw(unconn, 9))
    cw = max(tw(name, 12, True), tw(comp["type"], 10), pw) * 1.05
    w = max(pad["L"] + cw + pad["R"], min_w)
    block_h = 17 + 14 + 14 * len(params) + (13 if unconn else 0)
    h = max(top_res + block_h + bot_res + 6, min_h)
    node = Node(key=name, role="component", w=round(w), h=round(h), domain=dom, typename=comp["type"],
                fill=DOMAIN[dom]["fill"], border=DOMAIN[dom]["line"], style=DOMAIN[dom]["style"], bw=1.5,
                shape="roundrectangle" if dom == "mechanic" else "rectangle", group=dom)
    avail_top = top_res + (node.h - top_res - bot_res - block_h) / 2
    y = avail_top
    node.texts.append(Text(name, 0, y, node.w, 17, 12, True, INK))
    y += 17
    node.texts.append(Text(comp["type"], 0, y, node.w, 14, 10, False, MUTED))
    y += 14
    left = pad["L"] + (node.w - pad["L"] - pad["R"] - pw) / 2
    node.texts.append(Text("\n".join(params), left, y, pw * 1.03, 14 * len(params), 10, False, INK, "left"))
    y += 14 * len(params)
    if unconn:
        node.texts.append(Text(unconn, left, y, pw * 1.03, 13, 9, False, MUTED, "left"))
    return node


def add_port_labels(node: Node, sides: dict, lib_entry: dict) -> dict[str, tuple[float, float]]:
    """포트 이름을 노드 안쪽 경계에 쓰고 포트 절대좌표를 돌려준다."""
    points = {}
    for port, (side, pos) in sides.items():
        color = DOMAIN[port_domain(lib_entry, port)]["text"]
        width = tw(port, 10, True) + 1
        if side in "LR":
            py = node.cy if pos is None else pos
            rx = 3 if side == "L" else node.w - width - 3
            ry = py - node.y - 7
            points[port] = (node.x if side == "L" else node.x + node.w, py)
        else:
            px = node.cx if pos is None else pos
            rx = px - node.x - width / 2
            ry = 1 if side == "T" else node.h - 15
            points[port] = (px, node.y if side == "T" else node.y + node.h)
        node.texts.append(Text(port, rx, ry, width, 14, 10, True, color, "left", "port"))
    return points


# ------------------------------------------------------------------ 배치 도구
def stack(nodes: list[Node], cx: float, top: float, gap: float) -> float:
    y = top
    for n in nodes:
        n.x, n.y = cx - n.w / 2, y
        y += n.h + gap
    return y - gap


def center(n: Node, cx: float, cy: float) -> None:
    n.x, n.y = cx - n.w / 2, cy - n.h / 2


def group_box(nodes: list[Node], domain: str) -> Group:
    x0 = min(n.x for n in nodes) - 15
    x1 = max(n.x + n.w for n in nodes) + 15
    y0 = min(n.y for n in nodes) - 15 - 22
    y1 = max(n.y + n.h for n in nodes) + 15
    d = DOMAIN[domain]
    return Group(domain, x0, y0, x1 - x0, y1 - y0, d["ko"])


GROUP_HEADER = 37  # 자식 위 여백 15 + 헤더 22
SIG_TOP = 128


# ------------------------------------------------------------------ 그림별 포트 위치·배치
def sides_locked(conns):
    """A: 잠김."""
    return {
        "Clock": {"out": ("R", None)}, "LU_F": {"in": ("L", None), "out": ("R", None)},
        "PlugA": {"P1": ("R", None)}, "PlugB": {"P1": ("R", None)},
        "Rod": {"P1": ("L", None), "P2": ("B", None)}, "Kg": {"P1": ("T", None), "P2": ("B", None)},
        "Sup": {"P1": ("T", None), "P2": ("B", None)}, "Load": {"P1": ("T", None), "F": ("R", None)},
        "Cyl": {"P1": ("L", 0), "P2": ("L", 0), "P3": ("R", 0)},
    }


def layout_A(n, _):
    center(n["Clock"], 0, 0)
    w_h = max(n["PlugA"].w, n["PlugB"].w)
    cx_p = 45 + w_h / 2
    cx_c = cx_p + w_h / 2 + 70 + n["Cyl"].w / 2
    cx_m = cx_c + n["Cyl"].w / 2 + 90 + n["Rod"].w / 2
    lane = cx_m + n["Rod"].w / 2 + 45
    cy_s = SIG_TOP + GROUP_HEADER + n["LU_F"].h / 2
    center(n["LU_F"], cx_m, cy_s)
    center(n["Clock"], cx_m - n["LU_F"].w / 2 - 70 - n["Clock"].w / 2, cy_s)
    sig_bot = cy_s + n["LU_F"].h / 2 + 15
    body = sig_bot + 18 + GROUP_HEADER
    bot = stack([n["Rod"], n["Kg"], n["Sup"], n["Load"]], cx_m, body, 28)
    n["Cyl"].h = round(bot - body)
    center(n["Cyl"], cx_c, body + n["Cyl"].h / 2)
    y1 = n["Rod"].cy
    center(n["PlugA"], cx_p, y1)
    y2 = bot - n["PlugB"].h / 2 - 8
    center(n["PlugB"], cx_p, y2)
    ports = {"Cyl": {"P1": ("L", y1), "P2": ("L", y2), "P3": ("R", y1)}}
    routes = {("LU_F", "out", "Load", "F"): [(lane, cy_s), (lane, n["Load"].cy)]}
    return ports, routes


def sides_cb(conns):
    s = sides_locked(conns)
    s["CB"] = {"P1": ("R", None), "P2": ("L", None), "P_CONTROL": ("B", None)}
    s["TankCB"] = {"P1": ("R", None)}
    s["TankPilot"] = {"P1": ("T", None)}
    return s


def layout_B(n, _):
    wt = n["TankCB"].w
    cx_t = 45 + wt / 2
    cx_v = cx_t + wt / 2 + 60 + n["CB"].w / 2
    lane_v = cx_v + n["CB"].w / 2 + 28
    cx_c = lane_v + 40 + n["Cyl"].w / 2
    cx_m = cx_c + n["Cyl"].w / 2 + 90 + n["Rod"].w / 2
    lane = cx_m + n["Rod"].w / 2 + 45
    cy_s = SIG_TOP + GROUP_HEADER + n["LU_F"].h / 2
    center(n["LU_F"], cx_m, cy_s)
    center(n["Clock"], cx_m - n["LU_F"].w / 2 - 70 - n["Clock"].w / 2, cy_s)
    sig_bot = cy_s + n["LU_F"].h / 2 + 15
    body = sig_bot + 18 + GROUP_HEADER
    bot_h = stack([n["PlugA"], n["CB"], n["TankPilot"], n["PlugB"]], cx_v, body, 26)
    bot_m = stack([n["Rod"], n["Kg"], n["Sup"], n["Load"]], cx_m, body, 28)
    bot = max(bot_h, bot_m)
    n["Cyl"].h = round(bot - body)
    center(n["Cyl"], cx_c, body + n["Cyl"].h / 2)
    y1 = n["Rod"].cy
    center(n["PlugA"], cx_v, y1)
    center(n["TankCB"], cx_t, n["CB"].cy)
    center(n["PlugB"], cx_v, bot - n["PlugB"].h / 2)
    y2 = n["PlugB"].cy
    ports = {"Cyl": {"P1": ("L", y1), "P2": ("L", y2), "P3": ("R", y1)}}
    routes = {
        ("LU_F", "out", "Load", "F"): [(lane, cy_s), (lane, n["Load"].cy)],
        ("CB", "P1", "Cyl", "P1"): [(lane_v, n["CB"].cy), (lane_v, y1)],
    }
    return ports, routes


def sides_moving(conns):
    return {
        "Clock": {"out": ("B", None)},
        "LU_q": {"in": ("T", None), "out": ("B", None)}, "LU_Bp": {"in": ("T", None), "out": ("B", None)},
        "LU_open": {"in": ("T", None), "out": ("B", None)}, "LU_pline": {"in": ("T", None), "out": ("B", None)},
        "LU_F": {"in": ("T", None), "out": ("R", None)},
        "QA": {"P1": ("R", None), "q": ("T", None)},
        "PRV": {"P1": ("R", None), "P2": ("L", None)}, "TankR": {"P1": ("R", None)},
        "VB": {"PP": ("R", None), "PA": ("L", None), "in": ("T", None)},
        "PsB": {"P1": ("R", None), "p": ("T", None)},
        "Rod": {"P1": ("L", None), "P2": ("B", None)}, "Kg": {"P1": ("T", None), "P2": ("B", None)},
        "Sup": {"P1": ("T", None), "P2": ("B", None)}, "Load": {"P1": ("T", None), "F": ("R", None)},
        "Cyl": {"P1": ("L", 0), "P2": ("L", 0), "P3": ("R", 0), "B_p": ("T", None)},
    }


def layout_C(n, _):
    c0 = 45 + 110 + max(n["PsB"].w, n["LU_pline"].w) / 2 - 110
    c0 = max(c0, 170)
    c1 = c0 + max(n["PsB"].w, n["LU_pline"].w) / 2 + 45 + max(n["VB"].w, n["LU_open"].w) / 2
    tank_cx = c1 + 18 + n["TankR"].w / 2
    c2 = max(tank_cx + n["TankR"].w / 2 + 50, c1 + n["VB"].w / 2 + 30) + max(n["PRV"].w, n["QA"].w, n["LU_q"].w) / 2
    lane_v = c2 + max(n["PRV"].w, n["QA"].w) / 2 + 28
    cx_c = lane_v + 40 + n["Cyl"].w / 2
    cx_m = cx_c + n["Cyl"].w / 2 + 90 + n["Rod"].w / 2
    lane = cx_m + n["Rod"].w / 2 + 45
    # 신호: Clock 한 줄, 그 아래 버스, LU 한 줄
    clock_top = SIG_TOP + GROUP_HEADER
    center(n["Clock"], c0, clock_top + n["Clock"].h / 2)
    bus = clock_top + n["Clock"].h + 16
    lu_top = bus + 16
    for name, cx in (("LU_pline", c0), ("LU_open", c1), ("LU_q", c2), ("LU_Bp", cx_c), ("LU_F", cx_m)):
        center(n[name], cx, lu_top + n[name].h / 2)
    sig_bot = lu_top + n["LU_F"].h + 15
    body = sig_bot + 18 + GROUP_HEADER
    bot_m = stack([n["Rod"], n["Kg"], n["Sup"], n["Load"]], cx_m, body, 28)
    y1 = n["Rod"].cy
    center(n["QA"], c2, y1)
    prv_top = n["QA"].y + n["QA"].h + 24
    center(n["PRV"], c2, prv_top + n["PRV"].h / 2)
    center(n["TankR"], tank_cx, n["PRV"].cy)
    vb_top = max(n["PRV"].y + n["PRV"].h, n["TankR"].y + n["TankR"].h) + 24
    center(n["VB"], c1, vb_top + n["VB"].h / 2)
    y2 = n["VB"].cy
    center(n["PsB"], c0, y2)
    bot = max(bot_m, n["VB"].y + n["VB"].h)
    n["Cyl"].h = round(bot - body)
    center(n["Cyl"], cx_c, body + n["Cyl"].h / 2)
    ports = {"Cyl": {"P1": ("L", y1), "P2": ("L", y2), "P3": ("R", y1), "B_p": ("T", None)}}
    routes = {("LU_F", "out", "Load", "F"): [(lane, n["LU_F"].cy), (lane, n["Load"].cy)],
              ("PRV", "P1", "Cyl", "P1"): [(lane_v, n["PRV"].cy), (lane_v, y1)]}
    for name, cx in (("LU_open", c1), ("LU_q", c2), ("LU_Bp", cx_c), ("LU_F", cx_m)):
        routes[("Clock", "out", name, "in")] = [(c0, bus), (cx, bus)]
    return ports, routes


def sides_cbtest(conns):
    return {
        "R1": {"out": ("R", None)}, "R2": {"out": ("R", None)},
        "Add": {"in1": ("L", 0), "in2": ("L", 0), "out": ("R", None)},
        "Tank": {"P1": ("R", None)}, "Tank2": {"P1": ("R", None)},
        "CB": {"P1": ("L", None), "P2": ("R", None)}, "OrfR": {"P1": ("L", None), "P2": ("R", None)},
        "Mass": {"P1": ("L", None), "P2": ("B", None)}, "Load": {"P1": ("T", None), "F": ("R", None)},
        "Cyl": {"P1": ("L", 0), "P2": ("L", 0), "P3": ("R", 0)},
    }


def layout_D(n, _):
    # 유압 방향은 Tank - 밸브 - Cyl 순서로 왼쪽→오른쪽. 포트는 .hmf 이름대로(밸브 P1이 실린더 쪽)
    n_cb, n_or = n["CB"], n["OrfR"]
    wt = max(n["Tank"].w, n["Tank2"].w)
    wv = max(n_cb.w, n_or.w)
    cx_t = 45 + wt / 2
    cx_v = cx_t + wt / 2 + 60 + wv / 2
    cx_c = cx_v + wv / 2 + 70 + n["Cyl"].w / 2
    cx_m = cx_c + n["Cyl"].w / 2 + 90 + n["Mass"].w / 2
    lane = cx_m + n["Mass"].w / 2 + 45
    r_w = max(n["R1"].w, n["R2"].w)
    cx_r = cx_m - n["Add"].w / 2 - 70 - r_w / 2
    top = SIG_TOP + GROUP_HEADER
    bot_s = stack([n["R1"], n["R2"]], cx_r, top, 16)
    center(n["Add"], cx_m, (top + bot_s) / 2)
    n["Add"].h = max(n["Add"].h, 90)
    center(n["Add"], cx_m, (top + bot_s) / 2)
    ya = n["Add"].cy
    sig_bot = bot_s + 15
    body = sig_bot + 18 + GROUP_HEADER
    bot_m = stack([n["Mass"], n["Load"]], cx_m, body, 34)
    y1 = n["Mass"].cy
    center(n_cb, cx_v, max(y1, body + n_cb.h / 2))
    y1 = n_cb.cy
    center(n["Mass"], cx_m, y1)
    bot_m = stack([n["Mass"], n["Load"]], cx_m, n["Mass"].y, 34)
    center(n["Tank"], cx_t, y1)
    y2 = n_cb.y + n_cb.h + 40 + n_or.h / 2
    center(n_or, cx_v, y2)
    center(n["Tank2"], cx_t, y2)
    bot = max(bot_m, n_or.y + n_or.h)
    n["Cyl"].h = round(max(bot - body, n["Cyl"].h))
    center(n["Cyl"], cx_c, body + n["Cyl"].h / 2)
    ports = {
        "Cyl": {"P1": ("L", y1), "P2": ("L", y2), "P3": ("R", y1)},
        "Add": {"in1": ("L", ya - 18), "in2": ("L", ya + 18), "out": ("R", None)},
        "CB": {"P1": ("R", None), "P2": ("L", None)}, "OrfR": {"P1": ("R", None), "P2": ("L", None)},
    }
    mid = (cx_r + r_w / 2 + cx_m - n["Add"].w / 2) / 2
    routes = {
        ("R1", "out", "Add", "in1"): [(mid, n["R1"].cy), (mid, ya - 18)],
        ("R2", "out", "Add", "in2"): [(mid, n["R2"].cy), (mid, ya + 18)],
        ("Add", "out", "Load", "F"): [(lane, ya), (lane, n["Load"].cy)],
    }
    return ports, routes


def sides_lockedcyl(conns):
    return {
        "Ramp": {"out": ("R", None)},
        "TankH": {"P1": ("R", None)}, "TankR": {"P1": ("R", None)},
        "OrfH": {"P1": ("R", None), "P2": ("L", None)}, "OrfR": {"P1": ("R", None), "P2": ("L", None)},
        "Mass": {"P1": ("L", None), "P2": ("B", None)}, "Load": {"P1": ("T", None), "F": ("R", None)},
        "Cyl": {"P1": ("L", 0), "P2": ("L", 0), "P3": ("R", 0)},
    }


def layout_E(n, _):
    wt = max(n["TankH"].w, n["TankR"].w)
    wv = max(n["OrfH"].w, n["OrfR"].w)
    cx_t = 45 + wt / 2
    cx_v = cx_t + wt / 2 + 60 + wv / 2
    cx_c = cx_v + wv / 2 + 70 + n["Cyl"].w / 2
    cx_m = cx_c + n["Cyl"].w / 2 + 90 + n["Mass"].w / 2
    lane = cx_m + n["Mass"].w / 2 + 45
    top = SIG_TOP + GROUP_HEADER
    center(n["Ramp"], cx_m, top + n["Ramp"].h / 2)
    sig_bot = top + n["Ramp"].h + 15
    body = sig_bot + 18 + GROUP_HEADER
    bot_m = stack([n["Mass"], n["Load"]], cx_m, body, 34)
    y1 = n["Mass"].cy
    center(n["OrfH"], cx_v, y1)
    center(n["TankH"], cx_t, y1)
    n["Cyl"].h = max(n["Cyl"].h, round(bot_m - body))
    center(n["Cyl"], cx_c, body + n["Cyl"].h / 2)
    y2 = n["Cyl"].y + n["Cyl"].h - 30
    center(n["OrfR"], cx_v, y2)
    center(n["TankR"], cx_t, y2)
    ports = {"Cyl": {"P1": ("L", y1), "P2": ("L", y2), "P3": ("R", y1)}}
    routes = {("Ramp", "out", "Load", "F"): [(lane, n["Ramp"].cy), (lane, n["Load"].cy)]}
    return ports, routes


# ------------------------------------------------------------------ 시나리오 주석(hmf·CSV에서 생성)
def rel(p: Path) -> str:
    return str(p.relative_to(REPO)).replace("/", "\\")


def scen_path(s: str) -> Path:
    return HYD / "hopsan_models" / s / f"leg_{s}.hmf"


def curve(points, fmt=lambda v: g5(v)) -> str:
    pts = [p for p in points if p[0] < 999]
    if all(p[1] == pts[0][1] for p in pts):
        return f"{fmt(pts[0][1])} 일정"
    if len(pts) > 1 and pts[0][0] == 0 and pts[1][1] == pts[0][1]:
        pts = pts[1:]
    return " → ".join(f"{g5(t, 7)} s {fmt(v)}" for t, v in pts)


def compare_to_base(base: dict, other: dict) -> dict:
    types = {n: (base["comps"][n]["type"], other["comps"][n]["type"])
             for n in base["comps"] if n in other["comps"] and base["comps"][n]["type"] != other["comps"][n]["type"]}
    return {
        "same_component_names": set(base["comps"]) == set(other["comps"]),
        "same_connections": sorted(base["conns"]) == sorted(other["conns"]),
        "type_differences": types,
    }


def notes_locked(models) -> list[str]:
    out = []
    base = models["S1"]
    for s in ("S1", "S1f", "S3", "S4p", "S5"):
        m = models[s]
        rod = m["comps"]["Rod"]
        f = curve(read_csv_points(m["path"].parent / "LU_F.csv"), lambda v: g5(v / 1e3))
        if rod["type"] == base["comps"]["Rod"]["type"]:
            rtxt = "Rod = 그림과 같음"
        else:
            fs, fk, b = rod["params"]["f_s#Value"], rod["params"]["f_k#Value"], rod["params"]["b#Value"]
            rtxt = f"Rod 형식 다름: {rod['type']} (f_s = {g5(float(fs) / 1e3)} kN, f_k = {g5(float(fk) / 1e3)} kN, b = {g5(float(b))}, m 같음)"
        out.append(f"{s}: stop {m['sim']['stop']} s, {rtxt}")
        out.append(f"      LU_F.csv [kN]: {f}")
    return ["연결·부품 이름은 다섯 파일 모두 같다. 그림의 값은 leg_S1.hmf이고, 시나리오별 차이는 아래뿐이다."] + out


def notes_cb(models) -> list[str]:
    m = models["S4"]
    f = curve(read_csv_points(m["path"].parent / "LU_F.csv"), lambda v: g5(v / 1e3))
    return [
        "leg_S1.hmf 구조에 CB·TankCB·TankPilot 3부품과 CB 연결 3개를 더한 모델이다(나머지 부품 형식과 연결은 같다).",
        f"S4: stop {m['sim']['stop']} s, LU_F.csv [kN]: {f}",
        "p_ref 355 bar abs는 설정 350 bar g에 대기압 보정 1 bar × (1 + a_ratio 4)를 더한 값이다(hopsan_single_leg.py).",
        "CB.P_CONTROL(파일럿)은 TankPilot에 이어져 탱크압으로 고정된다.",
    ]


def notes_moving(models) -> list[str]:
    out = ["연결·부품 형식은 세 파일 모두 같다. 그림의 값은 leg_S2.hmf이고, 차이는 값뿐이다."]
    for s in ("S2", "S2r", "S2b"):
        m = models[s]
        d = m["path"].parent
        out.append(f"{s}: stop {m['sim']['stop']} s, Sup.m = {g5(float(m['comps']['Sup']['params']['m']), 6)} kg")
        out.append(f"      LU_q [m³/s]: {curve(read_csv_points(d / 'LU_q.csv'))}")
        out.append(f"      LU_open [m]: {curve(read_csv_points(d / 'LU_open.csv'))}")
        out.append(f"      LU_Bp [N·s/m]: {curve(read_csv_points(d / 'LU_Bp.csv'))}")
        out.append(f"      LU_pline: {curve(read_csv_points(d / 'LU_pline.csv'), lambda v: g5(v / 1e5) + ' bar abs')}   LU_F: {curve(read_csv_points(d / 'LU_F.csv'), lambda v: g5(v / 1e3) + ' kN')}")
    return out


def dims(cyl: dict) -> tuple[float, float]:
    a1 = float(cyl["params"]["A_1#Value"])
    a2 = float(cyl["params"]["A_2#Value"])
    bore = math.sqrt(4 * a1 / math.pi)
    rod = math.sqrt(max(4 * (a1 - a2) / math.pi, 0.0))
    return bore * 1e3, rod * 1e3


def notes_cbtest(m) -> list[str]:
    b, r = dims(m["comps"]["Cyl"])
    r1, r2 = m["comps"]["R1"]["params"], m["comps"]["R2"]["params"]
    peak = float(r1["y_0#Value"]) + float(r1["y_A#Value"]) + float(r2["y_0#Value"]) + float(r2["y_A#Value"])
    return [
        f"단독 모델. 이름은 CB이지만 typename은 {m['comps']['CB']['type']}이다(S4의 CB는 HydraulicOverCenterValve).",
        f"A_1·A_2에서 환산한 치수: 보어 ø{b:.0f} mm, 로드 ø{r:.0f} mm(전방 실린더 도면값과 같음). use_sl = false.",
        "별도 스프링 부품이 없다. Mass의 k#Value가 다른 다리가 넘겨받는 몫의 스프링이다(s8 문서 4.5절).",
        f"R1 + R2 최종값은 {g5(peak, 7)}이다(.hmf). s8 문서 4.5절과 cb_ref.py는 700 kN을 적고 있어 저장본과 다르다.",
        "p_max 331 bar abs는 크래킹 압력이다(s8 문서 4.5절).",
    ]


def notes_lockedcyl(m) -> list[str]:
    b, r = dims(m["comps"]["Cyl"])
    return [
        "단독 모델. OrfH·OrfR의 면적 A = 0으로 두 챔버를 막아 잠근다.",
        f"A_1·A_2에서 환산한 치수: 보어 ø{b:.0f} mm, 로드 ø{r:.0f} mm(전방 실린더 도면값과 같음).",
        "s_l = 0.001 m, use_sl = false: 행정 끝을 쓰지 않는다. V_1 = A_1 × (0.05 + 0.659) m, V_2 = A_2 × (0.05 + 0.041) m(s8 문서).",
        "Mass의 k·x_min·x_max는 .hmf에 없어 Hopsan 라이브러리 기본값을 쓴다(k 기본값은 0).",
    ]


L2_TOPOLOGY = "REXOME33 옛 치수(115/110 mm) 기준, 뒤집은 위상: 배럴 고정 — 실린더 — 로드 — 스프링 — 질량  (l2_hydraulic_model_spec.md 6.1절)"

FIGURES = [
    dict(key="A", file="A_locked", hmf="hopsan_models/S1/leg_S1.hmf", title="그림 A. 잠김", short="잠김",
         scen="시나리오: S1, S1f, S3, S4p, S5 (S1f·S5는 Rod 형식이 다르다, 아래 주석)", scen_short="S1, S1f, S3, S4p, S5",
         sides=sides_locked, layout=layout_A, min_h={}, notes=notes_locked, topo=True,
         diff="밸브 없음. 두 챔버를 PlugQ로 막음"),
    dict(key="B", file="B_locked_cb", hmf="hopsan_models/S4/leg_S4.hmf", title="그림 B. 잠김 + 카운터 밸런스(CB)", short="잠김 + CB",
         scen="시나리오: S4", scen_short="S4", sides=sides_cb, layout=layout_B, min_h={}, notes=notes_cb, topo=True,
         diff="A + HydraulicOverCenterValve, 탱크 2개"),
    dict(key="C", file="C_moving", hmf="hopsan_models/S2/leg_S2.hmf", title="그림 C. 이동", short="이동",
         scen="시나리오: S2, S2r, S2b", scen_short="S2, S2r, S2b", sides=sides_moving, layout=layout_C, min_h={}, notes=notes_moving, topo=True,
         diff="유량원·릴리프·22밸브·압력원, 신호 5개"),
    dict(key="D", file="D_cb_test", hmf="s8_cb/CbLeg.hmf", title="그림 D. CB 시험", short="CB 시험",
         scen="시나리오: 단독 (s8_cb/CbLeg.hmf, 전방 실린더 값)", scen_short="단독", sides=sides_cbtest, layout=layout_D, min_h={}, notes=None, topo=False,
         diff="릴리프 밸브를 CB로 사용, 램프 2개 합"),
    dict(key="E", file="E_locked_cyl", hmf="h61/LockedCyl.hmf", title="그림 E. 잠긴 실린더", short="잠긴 실린더",
         scen="시나리오: 단독 (h61/LockedCyl.hmf, 전방 실린더 값)", scen_short="단독", sides=sides_lockedcyl, layout=layout_E, min_h={}, notes=None, topo=False,
         diff="A = 0 오리피스로 잠금, 램프 1개"),
]
SCENARIO_GROUPS = {"A": ["S1", "S1f", "S3", "S4p", "S5"], "B": ["S4"], "C": ["S2", "S2r", "S2b"]}


# ------------------------------------------------------------------ 그림 만들기
def text_node(key, role, x, y, lines, size=12, bold=False, color=INK, fill=None, border=None, pad=0):
    lh = LINE_H[size]
    w = tw("\n".join(lines), size, bold) * 1.03 + 2 * pad
    h = lh * len(lines) + 2 * pad
    n = Node(key=key, role=role, x=x, y=y, w=round(w) + 2, h=round(h) + 1, fill=fill, border=border, bw=1.0)
    n.texts.append(Text("\n".join(lines), pad, pad, n.w - 2 * pad, lh * len(lines), size, bold, color, "left"))
    return n


def build_figure(cfg: dict, lib: dict, models: dict) -> dict:
    m = read_hmf(HYD / cfg["hmf"])
    comps, conns = m["comps"], m["conns"]
    sides = cfg["sides"](conns)
    unknown = set(comps) ^ set(sides)
    if unknown:
        raise SystemExit(f"{cfg['key']}: 배치표와 .hmf의 부품이 다르다: {sorted(unknown)}")
    nodes = {n: make_component(n, comps[n], lib, conns, sides[n], min_w=0) for n in comps}
    ports_abs, routes = cfg["layout"](nodes, conns)
    for n, s in ports_abs.items():
        sides[n] = s
    # 레이아웃 뒤 높이가 바뀐 노드(Cyl 등)는 글자 블록을 다시 가운데에 놓기 위해 다시 만든다.
    points = {}
    for name, node in nodes.items():
        fresh = make_component(name, comps[name], lib, conns, sides[name], min_h=node.h, min_w=node.w)
        fresh.x, fresh.y, fresh.w, fresh.h = node.x, node.y, node.w, node.h
        nodes[name] = fresh
        points[name] = add_port_labels(fresh, sides[name], lib[comps[name]["type"]])
    edges = []
    used_routes = set()
    for conn in conns:
        a, sp, b, ep = conn
        dom_a = port_domain(lib[comps[a]["type"]], sp)
        dom_b = port_domain(lib[comps[b]["type"]], ep)
        if dom_a != dom_b:
            raise SystemExit(f"{conn}: 포트 도메인이 다르다 {dom_a} / {dom_b}")
        if conn in routes:
            bends = list(routes[conn])
            used_routes.add(conn)
        else:
            bends = []
        pts = [points[a][sp]] + bends + [points[b][ep]]
        edges.append(Edge(a, sp, b, ep, dom_a, pts))
    if set(routes) - used_routes:
        raise SystemExit(f"{cfg['key']}: .hmf에 없는 연결의 경로가 있다: {set(routes) - used_routes}")

    groups = []
    for dom in ("signal", "hydraulic", "mechanic"):
        children = [n for n in nodes.values() if n.domain == dom]
        if children:
            groups.append(group_box(children, dom))

    extras = []
    extras.append(text_node("title", "title", 40, 16, [cfg["title"] + f" — {Path(cfg['hmf']).name}"], 18, True))
    subs = [cfg["scen"]]
    if cfg["topo"]:
        subs.append(L2_TOPOLOGY)
    subs.append(f"부품 {len(comps)}개 · 연결 {len(conns)}개   원본: {rel(HYD / cfg['hmf'])}")
    extras.append(text_node("subtitle", "title", 40, 44, subs, 12, False, INK))

    all_rects = [n.rect for n in nodes.values()] + [(g.x, g.y, g.x + g.w, g.y + g.h) for g in groups]
    pts_all = [p for e in edges for p in e.pts]
    bottom = max(max(r[3] for r in all_rects), max(p[1] for p in pts_all)) + 22
    left = 30.0

    # 범례
    y = bottom
    extras.append(text_node("legend_title", "legend", left, y, ["범례"], 12, True))
    y += 20
    for dom, d in DOMAIN.items():
        sw = Node(key=f"legend_{dom}", role="legend", x=left, y=y + 1, w=40, h=16, fill=d["fill"], border=d["line"],
                  style=d["style"], bw=1.5, shape="roundrectangle" if dom == "mechanic" else "rectangle")
        extras.append(sw)
        desc = {"hydraulic": "유압: 실선 파랑", "mechanic": "기계: 실선 주황, 둥근 상자", "signal": "신호: 점선 회색, 화살표는 출력→입력"}[dom]
        extras.append(text_node(f"legend_{dom}_text", "legend", left + 48, y, [desc], 11))
        y += 22
    ln = ["노드 경계 안의 굵은 글자는 포트 이름이고, 글자 색은 포트 도메인이다.",
          "압력 abs는 절대압. 값이 신호로 들어오는 입력은 '신호 입력'으로 적었다."]
    extras.append(text_node("legend_note", "legend", left, y + 2, ln, 10, False, MUTED))
    legend_w = max(tw("\n".join(ln), 10) * 1.03, 300)

    # 시나리오 주석
    note_lines = cfg["notes"](models) if cfg["notes"] else None
    if note_lines is None:
        note_lines = {"D": notes_cbtest, "E": notes_lockedcyl}[cfg["key"]](m)
    extras.append(text_node("scenario_note", "note", left + legend_w + 30, bottom, note_lines, 11, False, INK,
                            fill="#FFFBE6", border="#8C8C8C", pad=7))
    return {"cfg": cfg, "model": m, "nodes": nodes, "edges": edges, "groups": groups, "extras": extras}


# ------------------------------------------------------------------ 자동 점검
def rect_hit(seg, r, shrink=0.5):
    (x1, y1), (x2, y2) = seg
    lo_x, hi_x = sorted((x1, x2))
    lo_y, hi_y = sorted((y1, y2))
    return hi_x > r[0] + shrink and lo_x < r[2] - shrink and hi_y > r[1] + shrink and lo_y < r[3] - shrink


def rects_overlap(a, b, m=0.0):
    return a[0] < b[2] - m and b[0] < a[2] - m and a[1] < b[3] - m and b[1] < a[3] - m


def check_figure(fig: dict) -> list[str]:
    problems = []
    nodes, edges, groups, extras = fig["nodes"], fig["edges"], fig["groups"], fig["extras"]
    every = list(nodes.values()) + extras
    for i, a in enumerate(every):
        for b in every[i + 1:]:
            if rects_overlap(a.rect, b.rect):
                problems.append(f"노드 겹침: {a.key} / {b.key}")
    for i, a in enumerate(groups):
        for b in groups[i + 1:]:
            if rects_overlap((a.x, a.y, a.x + a.w, a.y + a.h), (b.x, b.y, b.x + b.w, b.y + b.h)):
                problems.append(f"그룹 겹침: {a.label} / {b.label}")
    for g in groups:
        gr = (g.x, g.y, g.x + g.w, g.y + g.h)
        for n in every:
            if n.group != g.domain and rects_overlap(gr, n.rect):
                problems.append(f"그룹 {g.label} 안에 다른 노드: {n.key}")
    # 글자가 노드 안에 들어가고 서로 겹치지 않는지
    for n in nodes.values():
        boxes = []
        for t in n.texts:
            lines = t.text.split("\n")
            real = max(tw(s, t.size, t.bold) for s in lines)
            x0 = t.rx + (t.w - real) / 2 if t.align == "center" else t.rx
            r = (x0, t.ry, x0 + real, t.ry + t.h)
            if r[0] < 1 or r[2] > n.w - 1 or r[1] < 0 or r[3] > n.h:
                problems.append(f"글자 넘침: {n.key} '{lines[0]}' {tuple(round(v) for v in r)} in {n.w}x{n.h}")
            boxes.append((t, r))
        for i, (t1, r1) in enumerate(boxes):
            for t2, r2 in boxes[i + 1:]:
                if rects_overlap(r1, r2, 0.5):
                    problems.append(f"글자 겹침: {n.key} '{t1.text[:12]}' / '{t2.text[:12]}'")
    # 엣지: 직각, 다른 노드·주석 통과, 다른 망과 교차
    nets = {}

    def find(k):
        nets.setdefault(k, k)
        while nets[k] != k:
            k = nets[k]
        return k

    for e in edges:
        nets[find((e.start, e.sport))] = find((e.end, e.eport))
    segs = []
    for e in edges:
        for p, q in zip(e.pts, e.pts[1:]):
            if abs(p[0] - q[0]) > 0.01 and abs(p[1] - q[1]) > 0.01:
                problems.append(f"직각 아님: {e.start}.{e.sport}-{e.end}.{e.eport} {p}->{q}")
            segs.append((e, (p, q)))
            for n in every:
                if n.key not in (e.start, e.end) and rect_hit((p, q), n.rect):
                    problems.append(f"엣지가 노드를 지남: {e.start}.{e.sport}-{e.end}.{e.eport} / {n.key}")
            for n in (nodes[e.start], nodes[e.end]):
                if rect_hit((p, q), n.rect):
                    problems.append(f"엣지가 자기 끝 노드 안으로 들어감: {e.start}.{e.sport}-{e.end}.{e.eport} / {n.key}")
        for g in groups:
            hx = g.x + 8
            head = (hx, g.y, hx + tw(g.label, 13, True), g.y + 22)
            for p, q in zip(e.pts, e.pts[1:]):
                if rect_hit((p, q), head):
                    problems.append(f"엣지가 그룹 제목을 지남: {e.start}.{e.sport}-{e.end}.{e.eport} / {g.label}")
    for i, (e1, (p1, q1)) in enumerate(segs):
        for e2, (p2, q2) in segs[i + 1:]:
            if find((e1.start, e1.sport)) == find((e2.start, e2.sport)):
                continue
            if rect_hit((p1, q1), (min(p2[0], q2[0]) - 1, min(p2[1], q2[1]) - 1, max(p2[0], q2[0]) + 1, max(p2[1], q2[1]) + 1)):
                problems.append(f"엣지 교차: {e1.start}.{e1.sport}-{e1.end}.{e1.eport} / {e2.start}.{e2.sport}-{e2.end}.{e2.eport}")
    return sorted(set(problems))


# ------------------------------------------------------------------ PNG
FP = FontProperties(fname=FONT)
FPB = FontProperties(fname=FONT_BOLD)


def bounds(fig: dict):
    rs = [n.rect for n in list(fig["nodes"].values()) + fig["extras"]] + [(g.x, g.y, g.x + g.w, g.y + g.h) for g in fig["groups"]]
    pts = [p for e in fig["edges"] for p in e.pts]
    x1 = max(max(r[2] for r in rs), max(p[0] for p in pts))
    y1 = max(max(r[3] for r in rs), max(p[1] for p in pts))
    return x1 + 25, y1 + 20


def draw_edge(ax, e: Edge, scale=1.0):
    d = DOMAIN[e.domain]
    xs, ys = zip(*e.pts)
    sig = e.domain == "signal"
    ax.plot(xs, ys, color=d["line"], lw=(1.3 if sig else 2.0) * scale, ls=(0, (4, 2.5)) if sig else "-",
            solid_capstyle="butt", zorder=3)
    if sig:
        (x0, y0), (x1, y1) = e.pts[-2], e.pts[-1]
        ln = math.hypot(x1 - x0, y1 - y0) or 1
        ux, uy = (x1 - x0) / ln, (y1 - y0) / ln
        a, b = 9 * max(scale, 1 / 1), 4
        ax.add_patch(Polygon([(x1, y1), (x1 - a * ux - b * uy, y1 - a * uy + b * ux), (x1 - a * ux + b * uy, y1 - a * uy - b * ux)],
                             closed=True, color=d["line"], zorder=4))


def draw_box(ax, x, y, w, h, n: Node, zorder=2):
    kw = dict(facecolor=n.fill or "none", edgecolor=n.border or "none", lw=n.bw if n.border else 0,
              ls="-" if n.style == "line" else (0, (4, 2.5)), zorder=zorder)
    if n.shape == "roundrectangle":
        ax.add_patch(FancyBboxPatch((x + 6, y + 6), w - 12, h - 12, boxstyle="round,pad=6,rounding_size=7", **kw))
    else:
        ax.add_patch(Rectangle((x, y), w, h, **kw))


def render_png(fig: dict, path: Path, dpi=150):
    W, H = bounds(fig)
    f = plt.figure(figsize=(W / 72, H / 72), dpi=dpi)
    ax = f.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")
    f.patch.set_facecolor("white")
    for g in fig["groups"]:
        d = DOMAIN[g.domain]
        ax.add_patch(Rectangle((g.x, g.y), g.w, g.h, facecolor=d["group"], edgecolor=d["line"], lw=1.0, ls=(0, (6, 3)), zorder=1))
        ax.add_patch(Rectangle((g.x, g.y), g.w, 22, facecolor=d["fill"], edgecolor="none", zorder=1.1))
        ax.text(g.x + 8, g.y + 3 + ascent(13, True), g.label, fontproperties=FPB, fontsize=13, color=d["text"], va="baseline", zorder=1.2)
    for e in fig["edges"]:
        draw_edge(ax, e)
    for n in list(fig["nodes"].values()) + fig["extras"]:
        if n.fill or n.border:
            draw_box(ax, n.x, n.y, n.w, n.h, n)
        for t in n.texts:
            fp = FPB if t.bold else FP
            lh = t.h / max(len(t.text.split("\n")), 1)
            for i, s in enumerate(t.text.split("\n")):
                lw = tw(s, t.size, t.bold)
                x = n.x + t.rx + ((t.w - lw) / 2 if t.align == "center" else 0)
                ax.text(x, n.y + t.ry + i * lh + ascent(t.size, t.bold), s, fontproperties=fp, fontsize=t.size, color=t.color,
                        va="baseline", ha="left", zorder=5)
    f.savefig(path, dpi=dpi, facecolor="white")
    plt.close(f)


def render_overview(figs: list[dict], path: Path):
    f = plt.figure(figsize=(21, 13), dpi=120)
    f.patch.set_facecolor("white")
    f.text(0.018, 0.965, "Hopsan 모델 개요: 구조가 다른 5종", fontproperties=FPB, fontsize=22, color=INK)
    f.text(0.018, 0.938, "상자 안 글자는 .hmf의 부품 이름이다. 값과 포트 이름은 그림 A~E를 본다.", fontproperties=FP, fontsize=13, color=MUTED)
    slots = [(0.015, 0.49, 0.32, 0.41), (0.34, 0.49, 0.32, 0.41), (0.665, 0.49, 0.32, 0.41), (0.015, 0.02, 0.32, 0.41), (0.34, 0.02, 0.32, 0.41)]
    for fig, slot in zip(figs, slots):
        ax = f.add_axes(slot)
        ax.axis("off")
        rs = [n.rect for n in fig["nodes"].values()] + [(g.x, g.y, g.x + g.w, g.y + g.h) for g in fig["groups"]]
        pts = [p for e in fig["edges"] for p in e.pts]
        x0, y0 = min(min(r[0] for r in rs), min(p[0] for p in pts)) - 10, min(min(r[1] for r in rs), min(p[1] for p in pts)) - 10
        x1, y1 = max(max(r[2] for r in rs), max(p[0] for p in pts)) + 10, max(max(r[3] for r in rs), max(p[1] for p in pts)) + 10
        span = max(x1 - x0, (y1 - y0) * slot[2] * 21 / (slot[3] * 13))
        ax.set_xlim(x0, x0 + span)
        span_y = span * slot[3] * 13 / (slot[2] * 21)
        ax.set_ylim(y0 + span_y, y0)
        pts_per_unit = slot[2] * 21 * 72 / span
        cfg = fig["cfg"]
        ax.set_title(f"{cfg['key']}. {cfg['short']}  ({cfg['scen_short']})  부품 {len(fig['nodes'])} · 연결 {len(fig['edges'])}",
                     fontproperties=FPB, fontsize=15, color=INK, loc="left", pad=6)
        for g in fig["groups"]:
            d = DOMAIN[g.domain]
            ax.add_patch(Rectangle((g.x, g.y), g.w, g.h, facecolor=d["group"], edgecolor=d["line"], lw=0.8, ls=(0, (6, 3)), zorder=1))
        for e in fig["edges"]:
            draw_edge(ax, e, scale=0.8)
        for n in fig["nodes"].values():
            draw_box(ax, n.x, n.y, n.w, n.h, n)
            box_pt = n.w * pts_per_unit - 4
            fs = min(12.0, 10.0 * box_pt / tw(n.key, 10, True))
            ax.text(n.cx, n.cy, n.key, fontproperties=FPB, fontsize=fs, color=INK, ha="center", va="center", zorder=5)

    # 대응표 + 범례
    ax = f.add_axes((0.675, 0.03, 0.31, 0.42))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(1, 0)
    ax.text(0, 0.03, "그림과 시나리오 대응", fontproperties=FPB, fontsize=15, color=INK)
    y = 0.11
    cols = [0.0, 0.07, 0.42]
    for c, h in zip(cols, ("그림", "시나리오", "구조의 특징")):
        ax.text(c, y, h, fontproperties=FPB, fontsize=12, color=MUTED)
    ax.plot([0, 1], [y + 0.02, y + 0.02], color="#BFBFBF", lw=1)
    y += 0.075
    for fig in figs:
        cfg = fig["cfg"]
        ax.text(cols[0], y, cfg["key"], fontproperties=FPB, fontsize=12, color=INK)
        ax.text(cols[1], y, cfg["scen_short"], fontproperties=FP, fontsize=12, color=INK)
        ax.text(cols[2], y, cfg["diff"], fontproperties=FP, fontsize=11.5, color=INK)
        y += 0.075
    ax.text(0, y + 0.005, "S1f·S5의 Rod는 MechanicTranslationalMassWithCoulombFriction이다(연결은 같음).", fontproperties=FP, fontsize=11, color=INK)
    y += 0.06
    ax.text(0, y, "S2b는 Sup.m만 1e9 kg이고 CSV 일정이 다르다. _ts5e-06 파일은 스텝만 다르다.", fontproperties=FP, fontsize=11, color=INK)
    y += 0.09
    for dom, d in DOMAIN.items():
        ax.add_patch(Rectangle((0, y - 0.03), 0.06, 0.04, facecolor=d["fill"], edgecolor=d["line"], lw=1.5, ls="-" if d["style"] == "line" else (0, (4, 2.5))))
        ax.text(0.08, y, {"hydraulic": "유압: 실선 파랑", "mechanic": "기계: 실선 주황", "signal": "신호: 점선 회색, 화살표"}[dom], fontproperties=FP, fontsize=12, color=INK)
        y += 0.065
    f.savefig(path, dpi=120, facecolor="white")
    plt.close(f)


# ------------------------------------------------------------------ GraphML
def free_label(realizer_shape, t: Text):
    attrs = {
        "alignment": t.align, "autoSizePolicy": "content", "fontFamily": YED_FONT, "fontSize": str(t.size),
        "fontStyle": "bold" if t.bold else "plain", "hasBackgroundColor": "false", "hasLineColor": "false",
        "height": format_number(t.h), "horizontalTextPosition": "center", "iconTextGap": "4",
        "modelName": "free", "modelPosition": "anywhere", "textColor": t.color.upper(),
        "verticalTextPosition": "bottom", "visible": "true", "width": format_number(t.w), "x": format_number(t.rx),
    }
    el = etree.Element(y_tag("NodeLabel"), attrs)
    el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    el.set("y", format_number(t.ry))
    el.text = t.text
    realizer_shape.addprevious(el)


def write_graphml(fig: dict, path: Path) -> None:
    cfg = fig["cfg"]
    title = f"{cfg['title']} / {cfg['scen']} / 원본 {rel(HYD / cfg['hmf'])}"
    root, graph, keys = yw.new_document(True, title)
    custom = {}
    for i, (name, owner) in enumerate((("hmf_role", "node"), ("hmf_component", "node"), ("hmf_typename", "node"), ("hopsan_domain", "node"),
                                       ("hmf_start_port", "edge"), ("hmf_end_port", "edge"), ("hopsan_domain_edge", "edge"))):
        kid = f"d{11 + i}"
        el = etree.Element(g_tag("key"), {"attr.name": name, "attr.type": "string", "for": owner, "id": kid})
        graph.addprevious(el)
        custom[name] = kid

    def add_node(parent_graph, nid, n: Node):
        fill = (n.fill or "#FFFFFF").upper()
        border = (n.border or "#000000").upper()
        style = yw.BoxStyle(fill, border, n.style, n.bw)
        ls = yw.LabelStyle(YED_FONT, 10, INK)
        el = yw.append_shape_node(parent_graph, nid, keys["node_graphics"], geometry=Geometry(n.x, n.y, n.w, n.h),
                                  shape=n.shape, box_style=style, label=None, label_style=ls)
        realizer = el.find(f"{g_tag('data')}/{y_tag('ShapeNode')}")
        if not n.fill:
            realizer.find(y_tag("Fill")).set("transparent", "true")
            realizer.find(y_tag("Fill")).attrib.pop("color")
        if not n.border:
            realizer.find(y_tag("BorderStyle")).set("hasColor", "false")
        shape_el = realizer.find(y_tag("Shape"))
        for t in n.texts:
            free_label(shape_el, t)
        yw.append_text_data(el, custom["hmf_role"], n.role)
        if n.role == "component":
            yw.append_text_data(el, custom["hmf_component"], n.key)
            yw.append_text_data(el, custom["hmf_typename"], n.typename)
            yw.append_text_data(el, custom["hopsan_domain"], n.domain)
        return el

    ids = {}
    for gi, g in enumerate(fig["groups"]):
        d = DOMAIN[g.domain]
        gid = f"n{gi}"
        label_h = 22
        gg = yw.GroupGraphics(
            label=yw.LabelBox(g.label, 0, 0, g.w, label_h), closed_label_width=max(tw(g.label, 13, True) + 16, 80),
            label_style=yw.LabelStyle(YED_FONT, 13, d["text"].upper()),
            box_style=yw.BoxStyle(d["group"].upper(), d["line"].upper(), "dashed", 1.0), label_fill=d["fill"].upper(),
            open_geometry=Geometry(g.x, g.y, g.w, g.h), closed_geometry=Geometry(g.x, g.y, max(tw(g.label, 13, True) + 16, 80), 50), closed=False)
        gnode = yw.append_group_node(graph, gid, keys["node_graphics"], gg)
        yw.append_text_data(gnode, custom["hmf_role"], "group")
        sub = yw.nested_graph(gnode, f"{gid}:", True)
        children = [n for n in fig["nodes"].values() if n.domain == g.domain]
        for ci, n in enumerate(children):
            nid = f"{gid}::n{ci}"
            ids[n.key] = nid
            add_node(sub, nid, n)
    base = len(fig["groups"])
    for i, n in enumerate(fig["extras"]):
        add_node(graph, f"n{base + i}", n)
    for ei, e in enumerate(fig["edges"]):
        d = DOMAIN[e.domain]
        src, dst = fig["nodes"][e.start], fig["nodes"][e.end]
        sig = e.domain == "signal"
        eg = yw.EdgeGraphics(
            source_offset=(e.pts[0][0] - src.cx, e.pts[0][1] - src.cy), target_offset=(e.pts[-1][0] - dst.cx, e.pts[-1][1] - dst.cy),
            bends=e.pts[1:-1], line_color=d["line"].upper(), line_style="dashed" if sig else "line", line_width=1.3 if sig else 2.0,
            arrow_source="none", arrow_target="standard" if sig else "none", label=None, label_style=yw.LabelStyle(YED_FONT, 10, INK))
        el = yw.append_polyline_edge(graph, f"e{ei}", ids[e.start], ids[e.end], keys["edge_graphics"], eg,
                                     text_data=((keys["edge_description"], f"{e.start}.{e.sport} — {e.end}.{e.eport}"),))
        yw.append_text_data(el, custom["hmf_start_port"], e.sport)
        yw.append_text_data(el, custom["hmf_end_port"], e.eport)
        yw.append_text_data(el, custom["hopsan_domain_edge"], e.domain)
    yw.append_resources(root, keys["resources"])
    yw.write_document(root, path)


# ------------------------------------------------------------------ 대조(저장한 파일을 다시 읽어 .hmf와 비교)
def verify_graphml(path: Path, model: dict) -> dict:
    root = SafeET.parse(path).getroot()
    ns = "{http://graphml.graphdrawing.org/xmlns}"
    keymap = {k.get("id"): k.get("attr.name") for k in root.findall(f"{ns}key")}

    def data(el):
        return {keymap.get(d.get("key")): (d.text or "") for d in el.findall(f"{ns}data") if keymap.get(d.get("key"))}

    comp, by_id, roles = {}, {}, {}
    for node in root.iter(f"{ns}node"):
        dd = data(node)
        roles[dd.get("hmf_role")] = roles.get(dd.get("hmf_role"), 0) + 1
        if dd.get("hmf_role") == "component":
            comp[dd["hmf_component"]] = dd["hmf_typename"]
            by_id[node.get("id")] = dd["hmf_component"]
    conns = []
    for edge in root.iter(f"{ns}edge"):
        dd = data(edge)
        conns.append((by_id[edge.get("source")], dd["hmf_start_port"], by_id[edge.get("target")], dd["hmf_end_port"]))
    hmf_types = {n: c["type"] for n, c in model["comps"].items()}
    # 파라미터 표시값이 라벨에 들어 있는지
    label_text = "\n".join((e.text or "") for e in root.iter("{http://www.yworks.com/xml/graphml}NodeLabel"))
    return {
        "hmf_components": len(hmf_types), "graph_components": len(comp),
        "hmf_connections": len(model["conns"]), "graph_edges": len(conns),
        "components_equal": comp == hmf_types,
        "connections_equal": sorted(conns) == sorted(model["conns"]),
        "other_nodes": {k: v for k, v in roles.items() if k != "component"},
        "typenames_in_labels": all(t in label_text for t in hmf_types.values()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    scen_models = {s: read_hmf(scen_path(s)) for ss in SCENARIO_GROUPS.values() for s in ss}
    fig_models = [read_hmf(HYD / c["hmf"]) for c in FIGURES]
    types = {c["type"] for m in fig_models for c in m["comps"].values()} | {c["type"] for m in scen_models.values() for c in m["comps"].values()}
    lib = read_library(types)
    # 그림 범위 밖 형식(MassWithCoulombFriction)도 라이브러리에는 있어야 한다.
    PARAM_LINES.setdefault("MechanicTranslationalMassWithCoulombFriction", [("m", "m", "kg"), ("b#Value", "b", "Ns"), ("f_s#Value", "f_s", "kN"), ("f_k#Value", "f_k", "kN")])

    # 그림 주석이 말하는 사실을 .hmf로 확인한다. 어긋나면 그림을 만들지 않는다.
    for s in SCENARIO_GROUPS["A"]:
        c = compare_to_base(scen_models["S1"], scen_models[s])
        assert c["same_component_names"] and c["same_connections"], s
    for s in SCENARIO_GROUPS["C"]:
        c = compare_to_base(scen_models["S2"], scen_models[s])
        assert c["same_component_names"] and c["same_connections"] and not c["type_differences"], s
    s1, s4 = scen_models["S1"], scen_models["S4"]
    assert set(s4["comps"]) - set(s1["comps"]) == {"CB", "TankCB", "TankPilot"} and set(s1["comps"]) <= set(s4["comps"])
    assert set(s1["conns"]) <= set(s4["conns"]) and len(s4["conns"]) - len(s1["conns"]) == 3
    assert all(s1["comps"][n]["type"] == s4["comps"][n]["type"] for n in s1["comps"])
    assert read_hmf(HYD / "s8_cb" / "CbLeg.hmf")["comps"]["CB"]["type"] == "HydraulicPressureReliefValve"
    assert s4["comps"]["CB"]["type"] == "HydraulicOverCenterValve"
    for s, model in scen_models.items():
        b, r = dims(model["comps"]["Cyl"])
        assert round(b) == 115 and round(r) == 110, (s, b, r)

    figs = [build_figure(c, lib, scen_models) for c in FIGURES]
    report = {"figures": {}, "scenario_groups": {}, "step_variants": {}, "unconnected": {}}
    failed = False
    for fig in figs:
        cfg = fig["cfg"]
        problems = check_figure(fig)
        gpath = out / f"{cfg['file']}.graphml"
        ppath = out / f"{cfg['file']}.png"
        write_graphml(fig, gpath)
        render_png(fig, ppath)
        v = verify_graphml(gpath, fig["model"])
        v["layout_problems"] = problems
        report["figures"][cfg["key"]] = {"graphml": str(gpath), "png": str(ppath), **v}
        if problems or not (v["components_equal"] and v["connections_equal"]):
            failed = True
        # 미연결 부품·포트
        m = fig["model"]
        un = {"components": [], "power_ports": [], "outputs": [], "inputs_unwired_count": 0}
        conn_ports = {(a, b) for a, b, _, _ in m["conns"]} | {(c, d) for _, _, c, d in m["conns"]}
        for name, c in m["comps"].items():
            if not any(x == name for x, _ in conn_ports):
                un["components"].append(name)
            e = lib[c["type"]]
            un["power_ports"] += [f"{name}.{p}" for p in e["power"] if (name, p) not in conn_ports]
            un["outputs"] += [f"{name}.{p}" for p in sorted(e["outputs"]) if (name, p) not in conn_ports]
            un["inputs_unwired_count"] += sum(1 for p in e["inputs"] if (name, p) not in conn_ports)
        report["unconnected"][cfg["key"]] = un
    for key, group in SCENARIO_GROUPS.items():
        base = scen_models[group[0]]
        report["scenario_groups"][key] = {s: compare_to_base(base, scen_models[s]) for s in group}
    for ss in SCENARIO_GROUPS.values():
        for s in ss:
            a = scen_models[s]
            b = read_hmf(HYD / "hopsan_models" / s / f"leg_{s}_ts5e-06.hmf")
            same_params = all(a["comps"][n]["params"] == b["comps"][n]["params"] and a["comps"][n]["type"] == b["comps"][n]["type"] for n in a["comps"]) and set(a["comps"]) == set(b["comps"])
            report["step_variants"][s] = {
                "timestep": (a["sim"]["timestep"], b["sim"]["timestep"]),
                "same_components_params": same_params,
                "same_connections": sorted(a["conns"]) == sorted(b["conns"]),
            }
    render_overview(figs, out / "overview.png")
    (out / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in report["figures"].items():
        print(k, {x: v[x] for x in ("hmf_components", "graph_components", "hmf_connections", "graph_edges", "components_equal", "connections_equal", "other_nodes", "typenames_in_labels")})
        for p in v["layout_problems"]:
            print("  PROBLEM", p)
    print(json.dumps({"ok": not failed}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
