"""Auger drive travel on the upright mast: moving parts, travel limits, three levels.

Scenario (user, 2026-10-19): the mast stays upright (CAD pose). The drive
(``0. DRIVE AUGER ASSY``) and the auger tool (``AUGER TOOL``) translate together
along the mast. Three levels are used: top = upper travel limit, bottom = lower
travel limit, middle = halfway.

Reads only cached data (no STEP parsing):
    cad/parts_classified.csv   from analyze_parts.py
    cad/cad_summary.json       leg pad positions, reference mass properties
    cad/meshes/*.npz|json      from export_meshes.py (tessellated parts, 3 mm)
    cad/meshes/render_mesh.npz from analyze_mast.py (decimated meshes for drawing)
    cad/mast/*.brep            from inspect_mast.py (exact distance where cached)

Writes:
    cad/auger_parts.csv        per-row moving/fixed classification with reason
    cad/auger_levels.json      moving set, travel limits with evidence, levels,
                               mass properties per level, leg loads, checks
    cad/auger_levels/*.png     side views of the three levels and a comparison

Mass cases. A = STEP densities ("step"), B = 'generic' as steel and glass 2.5
("generic_as_steel", comparison only), C = STEP densities except the five
AUGER TOOL rows as steel 7.85 g/cm^3 ("tool_steel", reference case of
CLAUDE.md, 2026-10-19). Case C is added here (columns density_tool_steel_g_cm3,
mass_tool_steel_kg); the figures still mark A and B only.

Frames. CAD root frame in mm (Y up). Body frame (CLAUDE.md): x = Z_cad,
y = X_cad, z = Y_cad, same origin (CAD origin). Travel ``delta`` is the
translation of the moving set along CAD +Y (= body +z, the mast axis) from the
CAD pose, in mm (JSON also gives m).

Method (travel limits). Pure translation along Y, so the clearance between a
moving part and a fixed part is a column problem: surface points of both parts
are binned into X-Z cells; in each shared cell the moving part occupies a Y
span [a, b]; fixed points above b give the upward clearance, points below a the
downward one. Cells where the fixed part already lies within [a - tol, b + tol]
at rest (sliding contact: guide shoes on the rails, pinions on the rack, rod in
the bore) are excluded for that pair; rail and rack engagement are checked
separately. The decisive pairs are refined with BRepExtrema (cached BREP) or
the mesh closest-point distance.

Usage:
    python -I scripts/cad/analyze_auger_levels.py [--skip-render]
"""

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import trimesh
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from OCC.Core.BRepExtrema import BRepExtrema_DistShapeShape
from OCC.Core.gp import gp_Trsf, gp_Vec
from OCC.Core.TopLoc import TopLoc_Location

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_mast import (
    CASE_LABEL,
    CASES,
    GRAVITY_M_S2,
    LEG_ORDER,
    _load_brep,
    leg_loads,
    point_in_polygon,
    render_meshes,
    tensor_checks,
)
from analyze_parts import (
    CAD_TO_BODY,
    CENTROID_COLUMNS,
    CLASSIFIED_CSV,
    KG_PER_MM3_PER_G_CM3,
    STEEL_DENSITY_G_CM3,
    combine_mass_properties,
)
from cad_common import CAD_DIR, SUMMARY_JSON
from export_meshes import MESH_INDEX_JSON, load_meshes
from inspect_mast import MAST_INDEX_JSON

AUGER_PARTS_CSV = CAD_DIR / "auger_parts.csv"
AUGER_JSON = CAD_DIR / "auger_levels.json"
FIGURE_DIR = CAD_DIR / "auger_levels"

DRIVE_TOP = "0. DRIVE AUGER ASSY:1"
TOOL_TOP = "AUGER TOOL:1"
MOVING_DRIVE = "moving_drive"
MOVING_TOOL = "moving_tool"
FIXED = "fixed"
LEG_ROD_PAD = "excluded_leg_rod_pad"
MOVING = (MOVING_DRIVE, MOVING_TOOL)

SAMPLE_SPACING_MM = 4.0
MAX_POINTS_PER_PART = 1_500_000
CELL_MM = 5.0
COLOCATED_TOL_MM = 3.0  # = mesh linear deflection
EXACT_TOUCH_MM = 0.01
MESH_TOUCH_MM = 0.5
REFINE_SPACING_MM = 2.0
RAIL_GAP_MM = 20.0
MAST_SEGMENT = re.compile(r"MAST ASSY:1 / MAST(-\d)?:1$")
ROLLING_GEAR = re.compile(r"21\. ELEVATION GEAR:\d / 21\. ELEVATION GEAR:1$|ELEVATION ENCODER:1 / 7\. GEAR:1$")
CRAWLER_GROUND_Y_MM = -1050.9  # crawler bottom = ground in the CAD pose (docs/cad_review.md)

COLORS = {
    FIXED: "#a8a7a0",
    LEG_ROD_PAD: "#7d7c77",
    MOVING_DRIVE: "#2a78d6",
    MOVING_TOOL: "#eb6834",
}
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
COG_COLOR = "#e2245c"
PAD_COLOR = "#1baf7a"
plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

LEVEL_NAMES = ("top", "middle", "bottom")

# Case C (reference mass, CLAUDE.md 2026-10-19): STEP densities, auger tool as steel.
TOOL_STEEL = "tool_steel"
MASS_CASES = (*CASES, TOOL_STEEL)
MASS_CASE_LABEL = {**CASE_LABEL, TOOL_STEEL: "C"}
LEVEL_LABEL = {"top": "상단", "middle": "중단", "bottom": "하단"}


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------
FIXED_REASONS = {
    "MAST ASSY:1": ("마스트 본체·랙기어. 구동부 가이드 캐처가 감싸는 전면 모서리 레일과 승강 피니언이 물리는 랙이 "
                    "여기 있다(구동부가 미끄러지는 고정 궤도)", "높음"),
    "TOPSHEAVE(조립) ASSY:1": ("마스트 상단면(Y 9851) 위에 얹힌 탑시브. 마스트에 고정", "높음"),
    "LOWER GUIDE_ASSY:1": ("마스트 하단(Y −655…−304)에서 레일을 GUIDE PIN·KEY PLATE로 물고 FIX PIN으로 고정된 공구 "
                           "가이드. 좌우 반쪽이 CENTER PIN(Z 3844) 경첩으로 열리는 분할형이고 ADAPTER(내경 R186.5)는 "
                           "교체형 부시로 보임. 구동부와 연결 형상 없음", "중간"),
    "윈치:1": ("MAST-2에 볼트 4개(Z축 R6.9)로 고정된 윈치(Y 2174–2659). 와이어는 모델에 없음", "높음"),
    "Hose guide arm:1": ("붐에 핀(Y 1710, Z 1329) 결합된 호스 가이드 암. 마스트 뒤(Z ≤ 1600)에 있어 구동부(Z ≥ 2523)와 "
                         "연결 형상 없음. 호스는 모델에 없음", "중간"),
    "Hose guide CYL:1": ("붐–호스 가이드 암 사이 실린더(Z ≤ 1241). 구동부와 연결 없음", "중간"),
    "BACKSTAY CYL:1": ("마스트 뒤 기립 실린더. 세운 자세에서 고정", "높음"),
}


def drive_reason(path: str) -> tuple[str, str]:
    """Reason and confidence for a row inside the drive assembly."""
    if "LOCKING CYL" in path:
        return ("구동부 하부 프레임 안의 소형 실린더(X ±597, Y 5347–5709, Z 3380–3445). 마스트(Z ≤ 2725)·레일과 "
                "떨어져 있고 구동부 하위 조립에 속함 → 구동부와 함께 이동", "높음")
    if "GUID CATCHER" in path or "CATHCER PAD" in path or "CATCHER PAD" in path:
        return ("마스트 전면 모서리 레일(X ±295…475, Z 2523–2687)을 감싸는 슬라이드 슈(가이드 캐처)와 패드. "
                "구동부 하위 조립 → 함께 미끄러짐", "높음")
    if "AUGER FRAME ASSY" in path and "솔리드24" in path:
        return ("구동부 프레임의 우측 슬라이드판(docs/cad_mast_review.md 5.2절). 구동부 하위 조립", "높음")
    if "ELEVATION" in path or "NABTESCO" in path:
        return ("마스트 랙(X ±57.7, Z 2667–2725)과 맞물리는 승강 피니언·감속모터·엔코더. 구동부 하위 조립", "높음")
    return ("DRIVE AUGER ASSY 구성품(프레임·회전 기어열·유압 모터·커버). 마스트 레일 위를 함께 이동", "높음")


TOOL_REASON = (
    "오거 공구(육각 로드 외접 r ≈ 120, 하단 캡 R260, 상단 SHACKLE). 로드가 구동부 1st GEAR SHAFT의 육각 소켓"
    "(최소 r 110)을 지나 회전을 받는다. 전제(사용자 2026-10-19)에 따라 구동부와 함께 이동. 단, 상단 SHACKLE은 "
    "와이어 매달기 형상이라 실기에서는 로드가 구동부에 대해 축방향으로 미끄러질 수 있음",
    "중간",
)


def classify(parts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in parts.itertuples():
        top = row.top_assembly
        if row.group == "leg_rod_pad":
            item = (LEG_ROD_PAD, "다리 이동부(로드+패드). 상부체 정의에서 제외(기존 정의)", "높음")
        elif top == DRIVE_TOP:
            item = (MOVING_DRIVE, *drive_reason(row.instance_path))
        elif top == TOOL_TOP:
            item = (MOVING_TOOL, *TOOL_REASON)
        elif top in FIXED_REASONS:
            item = (FIXED, *FIXED_REASONS[top])
        else:
            item = (FIXED, "상부체 고정부(데크·운전실·하우징·카운터웨이트·크롤러·붐·다리 배럴 등). 마스트 전면 이동 "
                           "경로 밖", "높음")
        rows.append(item)
    table = parts.copy()
    table["motion"] = [r[0] for r in rows]
    table["motion_reason"] = [r[1] for r in rows]
    table["confidence"] = [r[2] for r in rows]
    table["sub_assembly"] = table["instance_path"].str.split(" / ").str[2]
    return table


def add_tool_steel_case(table: pd.DataFrame) -> pd.DataFrame:
    """Add case C: STEP densities, but the AUGER TOOL rows (moving_tool) as steel 7.85 g/cm^3."""
    result = table.copy()
    is_tool = result["motion"] == MOVING_TOOL
    result["density_tool_steel_g_cm3"] = result["density_step_g_cm3"].where(~is_tool, STEEL_DENSITY_G_CM3)
    result["mass_tool_steel_kg"] = (result["volume_used_mm3"] * result["density_tool_steel_g_cm3"]
                                    * KG_PER_MM3_PER_G_CM3)
    return result


def short_name(path: str) -> str:
    return "/".join(path.split(" / ")[1:])


# --------------------------------------------------------------------------
# Column (X-Z cell) clearance for vertical translation
# --------------------------------------------------------------------------
def surface_points(mesh: trimesh.Trimesh, spacing_mm: float) -> np.ndarray:
    count = int(min(MAX_POINTS_PER_PART, mesh.area / spacing_mm**2))
    points = np.asarray(mesh.vertices)
    if count > 0:
        samples, _ = trimesh.sample.sample_surface(mesh, count, seed=0)
        points = np.vstack([points, samples])
    return points


def cell_ids(points: np.ndarray) -> np.ndarray:
    ix = np.floor((points[:, 0] + 5000.0) / CELL_MM).astype(np.int64)
    iz = np.floor((points[:, 2] + 5000.0) / CELL_MM).astype(np.int64)
    return ix * 1_000_000 + iz


def cell_centre(cell: int) -> tuple[float, float]:
    ix, iz = divmod(int(cell), 1_000_000)
    return (ix + 0.5) * CELL_MM - 5000.0, (iz + 0.5) * CELL_MM - 5000.0


class ColumnClearance:
    """Vertical clearance between moving and fixed parts on an X-Z cell grid."""

    def __init__(self, meshes, moving: list[int], fixed: list[int], family_of: dict[int, int]):
        self.meshes = meshes
        self.moving = moving
        footprint_low = np.min([meshes[i].bounds[0] for i in moving], axis=0)
        footprint_high = np.max([meshes[i].bounds[1] for i in moving], axis=0)
        margin = 2 * CELL_MM
        self.fixed = [
            i for i in fixed
            if meshes[i].bounds[1][0] >= footprint_low[0] - margin and meshes[i].bounds[0][0] <= footprint_high[0] + margin
            and meshes[i].bounds[1][2] >= footprint_low[2] - margin and meshes[i].bounds[0][2] <= footprint_high[2] + margin
        ]
        # Parts of one track family (mast segments, rack bars) share an owner id so that a shoe sliding
        # from one segment onto the next is not taken as a collision.
        cells, ys, owners, actual = [], [], [], []
        for i in self.fixed:
            points = surface_points(meshes[i], SAMPLE_SPACING_MM)
            cells.append(cell_ids(points))
            ys.append(points[:, 1])
            owners.append(np.full(len(points), family_of.get(i, i), dtype=np.int64))
            actual.append(np.full(len(points), i, dtype=np.int64))
        cells, ys = np.concatenate(cells), np.concatenate(ys)
        owners, actual = np.concatenate(owners), np.concatenate(actual)
        order = np.argsort(cells, kind="stable")
        self.cells, self.ys, self.owners, self.actual = cells[order], ys[order], owners[order], actual[order]
        self.fixed_point_count = int(len(order))

    def pair_table(self) -> pd.DataFrame:
        """Minimum up/down travel to contact for every (moving, fixed) pair sharing a column."""
        records = []
        for m in self.moving:
            points = surface_points(self.meshes[m], SAMPLE_SPACING_MM)
            cells = cell_ids(points)
            unique, inverse = np.unique(cells, return_inverse=True)
            low = np.full(len(unique), np.inf)
            high = np.full(len(unique), -np.inf)
            np.minimum.at(low, inverse, points[:, 1])
            np.maximum.at(high, inverse, points[:, 1])
            left = np.searchsorted(self.cells, unique, "left")
            right = np.searchsorted(self.cells, unique, "right")
            lengths = right - left
            total = int(lengths.sum())
            if total == 0:
                continue
            cell_index = np.repeat(np.arange(len(unique)), lengths)
            offsets = np.concatenate([[0], np.cumsum(lengths)[:-1]])
            index = np.repeat(left - offsets, lengths) + np.arange(total)
            y = self.ys[index]
            owner = self.owners[index]
            actual = self.actual[index]
            a, b = low[cell_index], high[cell_index]
            key = owner * len(unique) + cell_index
            colocated = (y >= a - COLOCATED_TOL_MM) & (y <= b + COLOCATED_TOL_MM)
            excluded = np.isin(key, np.unique(key[colocated]))
            up = np.where(~excluded & (y > b), y - b, np.inf)
            down = np.where(~excluded & (y < a), a - y, np.inf)
            frame = pd.DataFrame({"owner": owner, "actual": actual, "up": up, "down": down,
                                  "cell": unique[cell_index],
                                  "y_fixed": y, "colocated": colocated})
            for other, group in frame.groupby("owner"):
                i_up = int(np.argmin(group["up"].to_numpy()))
                i_down = int(np.argmin(group["down"].to_numpy()))
                up_row, down_row = group.iloc[i_up], group.iloc[i_down]
                records.append({
                    "moving": m,
                    "fixed": int(other),
                    "up_fixed_part": int(up_row["actual"]),
                    "down_fixed_part": int(down_row["actual"]),
                    "up_mm": float(up_row["up"]),
                    "up_cell_xz_mm": cell_centre(up_row["cell"]) if np.isfinite(up_row["up"]) else None,
                    "up_fixed_y_mm": float(up_row["y_fixed"]) if np.isfinite(up_row["up"]) else None,
                    "down_mm": float(down_row["down"]),
                    "down_cell_xz_mm": cell_centre(down_row["cell"]) if np.isfinite(down_row["down"]) else None,
                    "down_fixed_y_mm": float(down_row["y_fixed"]) if np.isfinite(down_row["down"]) else None,
                    "colocated_cells": int(group.loc[group["colocated"], "cell"].nunique()),
                })
        return pd.DataFrame(records)


# --------------------------------------------------------------------------
# Exact refinement of the decisive pairs
# --------------------------------------------------------------------------
def _translated(shape, dy_mm: float):
    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(0.0, dy_mm, 0.0))
    return shape.Moved(TopLoc_Location(trsf))


class Refiner:
    """Travel to first contact for one pair: BRepExtrema if both BREPs are cached, else mesh distance."""

    def __init__(self, meshes, paths):
        self.meshes = meshes
        self.paths = paths
        self.index = json.loads(MAST_INDEX_JSON.read_text(encoding="utf-8"))["parts"]
        self.shapes = {}
        self.points = {}

    def _shape(self, i: int):
        if i not in self.shapes:
            self.shapes[i] = _load_brep(self.index[self.paths[i]])
        return self.shapes[i]

    def exact_available(self, m: int, f: int) -> bool:
        return self.paths[m] in self.index and self.paths[f] in self.index

    def distance(self, m: int, f: int, travel_mm: float, exact: bool) -> float:
        if exact:
            extrema = BRepExtrema_DistShapeShape(_translated(self._shape(m), travel_mm), self._shape(f))
            extrema.Perform()
            return float(extrema.Value()) if extrema.IsDone() else math.nan
        if m not in self.points:
            self.points[m] = surface_points(self.meshes[m], REFINE_SPACING_MM)
        points = self.points[m] + np.array([0.0, travel_mm, 0.0])
        low, high = self.meshes[f].bounds
        near = np.all((points >= low - 20.0) & (points <= high + 20.0), axis=1)
        if not near.any():
            return math.inf
        _, distance, _ = trimesh.proximity.closest_point(self.meshes[f], points[near])
        return float(distance.min())

    def ray_travel(self, m: int, f: int, sign: float) -> float:
        """Mesh travel to contact by casting rays along +-Y (moving points to fixed mesh and back)."""
        travels = []
        for source, target, direction in ((m, f, sign), (f, m, -sign)):
            if source not in self.points:
                self.points[source] = surface_points(self.meshes[source], REFINE_SPACING_MM)
            points = self.points[source]
            low, high = self.meshes[target].bounds
            near = ((points[:, 0] >= low[0] - 1) & (points[:, 0] <= high[0] + 1)
                    & (points[:, 2] >= low[2] - 1) & (points[:, 2] <= high[2] + 1))
            if not near.any():
                continue
            origins = points[near]
            directions = np.tile([0.0, direction, 0.0], (len(origins), 1))
            locations, ray_index, _ = self.meshes[target].ray.intersects_location(origins, directions,
                                                                                 multiple_hits=True)
            if len(locations):
                gaps = (locations[:, 1] - origins[ray_index, 1]) * direction
                gaps = gaps[gaps > 1e-6]
                if len(gaps):
                    travels.append(float(gaps.min()))
        return min(travels) if travels else math.inf

    def first_contact(self, m: int, f: int, estimate_mm: float, sign: float) -> dict:
        """Travel (signed, mm) at which the pair first touches."""
        exact = self.exact_available(m, f)
        rest = self.distance(m, f, 0.0, exact)
        if not exact:
            travel = self.ray_travel(m, f, sign)
            if not np.isfinite(travel) or travel > estimate_mm + 200.0:
                return {"method": "mesh ray cast", "travel_mm": None,
                        "rejected": "no contact within column estimate + 200 mm (cell artifact)"}
            return {
                "method": "mesh ray cast along the mast axis (3 mm deflection, 2 mm samples on both parts)",
                "travel_mm": round(sign * travel, 2),
                "distance_at_rest_mm": round(rest, 2) if np.isfinite(rest) else None,
                "distance_at_contact_mm": round(self.distance(m, f, sign * travel, False), 2),
                "distance_5mm_before_mm": round(self.distance(m, f, sign * max(0.0, travel - 5.0), False), 2),
            }
        touch = EXACT_TOUCH_MM
        low = max(0.0, estimate_mm - 25.0)
        high = estimate_mm + 10.0
        while self.distance(m, f, sign * high, exact) > touch and high < estimate_mm + 200.0:
            high += 20.0
        while low > 0 and self.distance(m, f, sign * low, exact) <= touch:
            low = max(0.0, low - 25.0)
        if self.distance(m, f, sign * high, exact) > touch:
            return {"method": "BRepExtrema (cached BREP)", "travel_mm": None,
                    "distance_at_rest_mm": round(rest, 2),
                    "rejected": "no B-rep contact within column estimate + 200 mm (cell artifact)"}
        for _ in range(14):
            middle = (low + high) / 2
            if self.distance(m, f, sign * middle, exact) <= touch:
                high = middle
            else:
                low = middle
        return {
            "method": "BRepExtrema (cached BREP), bisection to 0.01 mm",
            "travel_mm": round(sign * high, 2),
            "distance_at_rest_mm": round(rest, 2),
            "distance_5mm_before_mm": round(self.distance(m, f, sign * max(0.0, high - 5.0), exact), 2),
        }


# --------------------------------------------------------------------------
# Rail and rack engagement
# --------------------------------------------------------------------------
def covered_intervals(y: np.ndarray, gap_mm: float) -> list[list[float]]:
    y = np.sort(y)
    breaks = np.flatnonzero(np.diff(y) > gap_mm)
    starts = np.concatenate([[0], breaks + 1])
    ends = np.concatenate([breaks, [len(y) - 1]])
    return [[round(float(y[s]), 1), round(float(y[e]), 1)] for s, e in zip(starts, ends)]


def engagement_limits(table: pd.DataFrame, meshes) -> dict:
    """Travel range over which every guide shoe stays on its rail and every pinion on the rack."""
    paths = table["instance_path"]
    mast_rows = np.flatnonzero((table["top_assembly"] == "MAST ASSY:1").to_numpy())
    mast_points = np.vstack([surface_points(meshes[i], SAMPLE_SPACING_MM) for i in mast_rows])
    shoes = np.flatnonzero(paths.str.contains(f"{DRIVE_TOP} / 27. GUID CATCHER").to_numpy())
    rails = []
    for side, sign in (("left_+X", 1), ("right_-X", -1)):
        mine = [i for i in shoes if np.sign(meshes[i].bounds[0][0]) == sign]
        low = np.min([meshes[i].bounds[0] for i in mine], axis=0)
        high = np.max([meshes[i].bounds[1] for i in mine], axis=0)
        inside = ((mast_points[:, 0] >= low[0]) & (mast_points[:, 0] <= high[0])
                  & (mast_points[:, 2] >= low[2]) & (mast_points[:, 2] <= high[2]))
        intervals = covered_intervals(mast_points[inside, 1], RAIL_GAP_MM)
        rail = max(intervals, key=lambda iv: iv[1] - iv[0])
        rails.append({
            "side": side,
            "shoe_footprint_x_mm": [round(float(low[0]), 1), round(float(high[0]), 1)],
            "shoe_footprint_z_mm": [round(float(low[2]), 1), round(float(high[2]), 1)],
            "rail_y_intervals_mm": intervals,
            "rail_y_mm": rail,
            "shoes_y_mm": [round(float(low[1]), 1), round(float(high[1]), 1)],
            "travel_mm": [round(rail[0] - float(low[1]), 1), round(rail[1] - float(high[1]), 1)],
        })
    racks = table[paths.str.contains("MAST ASSY:1 / RACK GEAR")]
    rack_intervals = covered_intervals(
        np.concatenate([np.linspace(r.bbox_min_y_mm, r.bbox_max_y_mm, 400) for r in racks.itertuples()]),
        RAIL_GAP_MM,
    )
    rack = max(rack_intervals, key=lambda iv: iv[1] - iv[0])
    gears = table[paths.map(lambda p: bool(ROLLING_GEAR.search(p)))]
    pinion_low = float(gears["bbox_min_y_mm"].min())
    pinion_high = float(gears["bbox_max_y_mm"].max())
    return {
        "rack_gears": {short_name(r.instance_path): [round(r.bbox_min_y_mm, 1), round(r.bbox_max_y_mm, 1)]
                       for r in gears.itertuples()},
        "rails": rails,
        "rack_y_mm": rack,
        "rack_y_intervals_mm": rack_intervals,
        "pinions_y_mm": [round(pinion_low, 1), round(pinion_high, 1)],
        "rack_travel_mm": [round(rack[0] - pinion_low, 1), round(rack[1] - pinion_high, 1)],
        "criterion": "all guide shoes inside the rail Y span; all rack gears (4 elevation pinions + encoder gear) "
                     "inside the rack Y span",
    }


# --------------------------------------------------------------------------
# Mass properties
# --------------------------------------------------------------------------
def shifted(table: pd.DataFrame, travel_mm: float) -> pd.DataFrame:
    posed = table.copy()
    mask = posed["motion"].isin(MOVING)
    posed.loc[mask, "centroid_y_mm"] = posed.loc[mask, "centroid_y_mm"] + travel_mm
    return posed


def level_report(table: pd.DataFrame, travel_mm: float, pads_body: np.ndarray, polygon: np.ndarray) -> dict:
    posed = shifted(table, travel_mm)
    superstructure = posed[posed["group"] != "leg_rod_pad"]
    moving = posed[posed["motion"].isin(MOVING)]
    report = {}
    for case in MASS_CASES:
        properties = combine_mass_properties(superstructure, case).to_report()
        loads = leg_loads(pads_body[:, :2], properties["mass_kg"], np.array(properties["cog_body_m"][:2]))
        moving_properties = combine_mass_properties(moving, case).to_report()
        report[case] = {
            **properties,
            "tensor_checks": tensor_checks(properties),
            "leg_loads_kN": {n: round(v / 1000, 2) for n, v in zip(LEG_ORDER, loads)},
            "leg_loads_pct": {n: round(100 * v / loads.sum(), 2) for n, v in zip(LEG_ORDER, loads)},
            "cog_inside_leg_rectangle": point_in_polygon(np.array(properties["cog_body_m"][:2]), polygon),
            "moving_set_mass_kg": moving_properties["mass_kg"],
            "moving_set_cog_body_m": moving_properties["cog_body_m"],
        }
    return report


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
SIDE_RIGHT = np.array([1.0, 0.0, 0.0])
SIDE_UP = np.array([0.0, 0.0, 1.0])
SIDE_TOWARD = np.array([0.0, -1.0, 0.0])


def project_side(render, motions, travel_mm: float):
    light = SIDE_TOWARD + np.array([0, 0, 0.6])
    light /= np.linalg.norm(light)
    polygons, colours, depths = [], [], []
    for (vertices, faces), motion in zip(render, motions):
        if len(faces) == 0:
            continue
        points = vertices.copy()
        if motion in MOVING:
            points[:, 1] += travel_mm
        body = points @ CAD_TO_BODY.T / 1000.0
        triangles = body[faces]
        normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        lengths = np.linalg.norm(normals, axis=1)
        valid = lengths > 0
        triangles, normals = triangles[valid], normals[valid] / lengths[valid, None]
        shade = 0.45 + 0.55 * np.abs(normals @ light)
        base = np.array(matplotlib.colors.to_rgb(COLORS[motion]))
        colours.append(np.clip(base[None] * shade[:, None] + 0.12 * (1 - shade[:, None]), 0, 1))
        polygons.append(np.stack([triangles @ SIDE_RIGHT, triangles @ SIDE_UP], axis=2))
        # Moving parts are drawn on top so the drive stays visible in front of the mast.
        depths.append((triangles @ SIDE_TOWARD).mean(axis=1) + (100.0 if motion in MOVING else 0.0))
    polygons = np.concatenate(polygons)
    colours = np.concatenate(colours)
    order = np.argsort(np.concatenate(depths))
    return polygons[order], colours[order]


def draw_level_axes(axes, render, motions, level: dict, all_levels: dict, pads_body, limits, compact=False):
    polygons, colours = project_side(render, motions, level["travel_mm"])
    axes.add_collection(PolyCollection(polygons, facecolors=colours, edgecolors="none", antialiased=False))
    axes.axhline(CRAWLER_GROUND_Y_MM / 1000, color=INK_SECONDARY, lw=0.8, ls=":")
    axes.text(limits[0][0] + 0.1, CRAWLER_GROUND_Y_MM / 1000 - 0.25, "지면(크롤러 바닥, CAD 자세)", fontsize=7,
              color=INK_SECONDARY)
    for name, other in all_levels.items():
        if name == level["name"]:
            continue
        cog = other["mass"]["step"]["cog_body_m"]
        axes.plot(cog[0], cog[2], marker="X", ms=7, mfc="none", mec=COG_COLOR, mew=1, zorder=6)
    for case, marker in (("step", "X"), ("generic_as_steel", "P")):
        cog = level["mass"][case]["cog_body_m"]
        axes.plot(cog[0], cog[2], marker=marker, ms=12 if not compact else 9, mfc=COG_COLOR, mec="white",
                  mew=1.3, zorder=7, ls="none", label=f"상부체 무게중심 (경우 {CASE_LABEL[case]})")
    axes.plot(pads_body[:, 0], pads_body[:, 2], ls="none", marker="s", ms=7, mfc=PAD_COLOR, mec=INK, zorder=7,
              label="다리 패드 바닥 중심")
    marks = level["marks_body_z_m"]
    x_text = 4.2
    for key, label in (("drive_top", "구동부 상단"), ("drive_bottom", "구동부 하단"),
                       ("tool_top", "공구 상단"), ("tool_bottom", "공구 하단")):
        z = marks[key]
        axes.plot([3.95, 4.15], [z, z], color=INK_SECONDARY, lw=0.8, zorder=8)
        axes.text(x_text, z, f"{label} z={z:.3f}", ha="left", va="center", fontsize=7 if compact else 8,
                  color=INK, zorder=9)
    a = level["mass"]["step"]["cog_body_m"]
    b = level["mass"]["generic_as_steel"]["cog_body_m"]
    axes.annotate(f"G_A ({a[0]:.3f}, {a[2]:.3f})", (a[0], a[2]), xytext=(10, -14), textcoords="offset points",
                  fontsize=8, color=COG_COLOR, zorder=9)
    axes.set_xlim(*limits[0])
    axes.set_ylim(*limits[1])
    axes.set_aspect("equal")
    axes.set_xlabel("x 전방 [m] (= CAD Z)")
    axes.set_ylabel("z 상방 [m] (= CAD Y)")
    axes.grid(True, color="#e0dfda", lw=0.5)
    axes.set_title(
        f"{LEVEL_LABEL[level['name']]}: 이동량 Δ = {level['travel_mm'] / 1000:+.3f} m "
        f"(범위의 {level['percent_of_range']:.0f} %)\n"
        f"G_A = ({a[0]:.3f}, {a[1]:.3f}, {a[2]:.3f}) m · G_B = ({b[0]:.3f}, {b[1]:.3f}, {b[2]:.3f}) m",
        fontsize=9 if compact else 10, loc="left")


def legend_handles():
    return [
        Rectangle((0, 0), 1, 1, color=COLORS[MOVING_DRIVE], label="이동: 구동부 DRIVE AUGER ASSY"),
        Rectangle((0, 0), 1, 1, color=COLORS[MOVING_TOOL], label="이동: 오거 공구 AUGER TOOL"),
        Rectangle((0, 0), 1, 1, color=COLORS[FIXED], label="고정 상부체"),
        Rectangle((0, 0), 1, 1, color=COLORS[LEG_ROD_PAD], label="다리 이동부(상부체 제외)"),
        Line2D([], [], ls="none", marker="X", ms=10, mfc=COG_COLOR, mec="white", label="상부체 무게중심 A (STEP 밀도)"),
        Line2D([], [], ls="none", marker="P", ms=10, mfc=COG_COLOR, mec="white", label="상부체 무게중심 B (가정 밀도)"),
        Line2D([], [], ls="none", marker="X", ms=7, mfc="none", mec=COG_COLOR, label="다른 단계의 무게중심 A"),
        Line2D([], [], ls="none", marker="s", ms=7, mfc=PAD_COLOR, mec=INK, label="다리 패드 바닥 중심"),
    ]


def render_figures(render, motions, levels: dict, pads_body, limits) -> list[str]:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for index, name in enumerate(LEVEL_NAMES, start=1):
        figure, axes = plt.subplots(figsize=(10, 12), dpi=110)
        draw_level_axes(axes, render, motions, levels[name], levels, pads_body, limits)
        axes.legend(handles=legend_handles(), loc="upper left", fontsize=7.5, framealpha=0.92)
        figure.tight_layout()
        path = FIGURE_DIR / f"level_{index}_{name}_side.png"
        figure.savefig(path)
        plt.close(figure)
        written.append(str(path.relative_to(CAD_DIR.parent)))
    figure = plt.figure(figsize=(25, 12), dpi=100)
    grid = figure.add_gridspec(1, 4, width_ratios=[1, 1, 1, 1.05])
    for column, name in enumerate(LEVEL_NAMES):
        axes = figure.add_subplot(grid[0, column])
        draw_level_axes(axes, render, motions, levels[name], levels, pads_body, limits, compact=True)
        if column:
            axes.set_ylabel("")
    axes = figure.add_subplot(grid[0, 3])
    polygon = pads_body[[0, 1, 3, 2]]
    axes.fill(polygon[:, 0], polygon[:, 1], color=PAD_COLOR, alpha=0.08)
    axes.plot(*np.vstack([polygon, polygon[:1]])[:, :2].T, color=PAD_COLOR, lw=1)
    for name_leg, pad in zip(LEG_ORDER, pads_body):
        axes.plot(pad[0], pad[1], "s", ms=7, mfc=PAD_COLOR, mec=INK)
        axes.annotate(name_leg, pad[:2], xytext=(6, 4), textcoords="offset points", fontsize=8)
    for case, marker in (("step", "X"), ("generic_as_steel", "P")):
        points = np.array([levels[n]["mass"][case]["cog_body_m"] for n in LEVEL_NAMES])
        axes.plot(points[:, 0], points[:, 1], "-", color=COG_COLOR, lw=0.8)
        for n, point in zip(LEVEL_NAMES, points):
            axes.plot(point[0], point[1], marker=marker, ms=10, mfc=COG_COLOR, mec="white", ls="none")
    lines = ["상부체 무게중심 (x, y, z) [m]"]
    for case in CASES:
        for n in LEVEL_NAMES:
            c = levels[n]["mass"][case]["cog_body_m"]
            lines.append(f"{LEVEL_LABEL[n]} {CASE_LABEL[case]}: ({c[0]:.3f}, {c[1]:+.3f}, {c[2]:.3f})")
    axes.text(-2.9, -3.5, "\n".join(lines), fontsize=8, va="bottom",
              bbox=dict(fc="white", ec="#c9c8c2", lw=0.6))
    centre = pads_body[:, :2].mean(axis=0)
    axes.plot(*centre, "+", ms=12, color=INK)
    axes.annotate("다리 사각형 중심", centre, xytext=(6, -12), textcoords="offset points", fontsize=8)
    axes.set_xlim(-3.0, 2.8)
    axes.set_ylim(-3.6, 1.8)
    axes.set_aspect("equal")
    axes.set_xlabel("x 전방 [m]")
    axes.set_ylabel("y 좌측 [m]")
    axes.grid(True, color="#e0dfda", lw=0.5)
    axes.set_title("위에서 본 무게중심(x-y)과 다리 패드\n(세 단계 모두 x·y는 거의 같고 z만 변함)", fontsize=10, loc="left")
    figure.legend(handles=legend_handles(), loc="lower center", ncol=8, fontsize=8, framealpha=0.95)
    figure.suptitle("오거 3단계(상단·중단·하단) 옆 보기 비교: 기체 좌표(원점 = CAD 원점), 축 범위 고정", fontsize=12)
    figure.tight_layout(rect=(0, 0.04, 1, 0.97))
    path = FIGURE_DIR / "levels_compare.png"
    figure.savefig(path)
    plt.close(figure)
    written.append(str(path.relative_to(CAD_DIR.parent)))
    return written


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def pair_rows(pairs: pd.DataFrame, paths, motions, column: str, count: int = 8) -> list[dict]:
    rows = pairs[np.isfinite(pairs[column])].nsmallest(count, column)
    direction = column.split("_")[0]
    out = []
    for r in rows.itertuples():
        cell = getattr(r, f"{direction}_cell_xz_mm")
        out.append({
            "moving_part": short_name(paths[r.moving]),
            "moving_group": motions[r.moving],
            "fixed_part": short_name(paths[r.fixed]),
            f"{direction}_travel_estimate_mm": round(float(getattr(r, column)), 1),
            "contact_column_cad_x_z_mm": [round(cell[0], 1), round(cell[1], 1)] if cell else None,
            "fixed_surface_y_cad_mm": round(float(getattr(r, f"{direction}_fixed_y_mm")), 1),
            "colocated_cells_excluded": int(r.colocated_cells),
        })
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skip-render", action="store_true")
    arguments = parser.parse_args()
    started = time.perf_counter()
    timings = {}

    parts = pd.read_csv(CLASSIFIED_CSV, encoding="utf-8-sig")
    summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    table = add_tool_steel_case(classify(parts))
    paths = table["instance_path"].tolist()
    motions = table["motion"].tolist()

    mesh_paths, mesh_list = load_meshes()
    by_path = dict(zip(mesh_paths, mesh_list))
    meshes = [by_path[path] for path in paths]
    has_mesh = np.array([len(m.faces) > 0 for m in meshes])
    moving = [i for i in range(len(table)) if motions[i] in MOVING and has_mesh[i]]
    fixed = [i for i in range(len(table)) if motions[i] not in MOVING and has_mesh[i]]
    drive_rows = [i for i in moving if motions[i] == MOVING_DRIVE]
    tool_rows = [i for i in moving if motions[i] == MOVING_TOOL]

    # Mast axis direction from the rack bars (straight, along the whole mast).
    racks = table[table["instance_path"].str.contains("MAST ASSY:1 / RACK GEAR")]
    rack_centres = racks[CENTROID_COLUMNS].to_numpy()
    slope_x = np.polyfit(rack_centres[:, 1], rack_centres[:, 0], 1)[0]
    slope_z = np.polyfit(rack_centres[:, 1], rack_centres[:, 2], 1)[0]
    axis_cad = np.array([slope_x, 1.0, slope_z]) / math.hypot(1.0, slope_x, slope_z)
    mast_axis = {
        "evidence": f"least-squares line through {len(racks)} rack-bar centroids (CAD Y -506.5 ... 9848.5 mm)",
        "axis_cad": np.round(axis_cad, 8).tolist(),
        "axis_body": np.round(CAD_TO_BODY @ axis_cad, 8).tolist(),
        "tilt_from_body_z_deg": round(math.degrees(math.acos(axis_cad[1])), 6),
        "rack_centroid_x_spread_mm": round(float(np.ptp(rack_centres[:, 0])), 3),
        "rack_centroid_z_spread_mm": round(float(np.ptp(rack_centres[:, 2])), 3),
    }

    # Track families: the mast segments (rails, box) and the rack bars.
    mast_segments = [i for i in fixed if MAST_SEGMENT.search(paths[i])]
    rack_bars = [i for i in fixed if "MAST ASSY:1 / RACK GEAR" in paths[i]]
    family_of = {i: mast_segments[0] for i in mast_segments} | {i: rack_bars[0] for i in rack_bars}
    family_name = {mast_segments[0]: "MAST ASSY:1/MAST:1 … MAST-5:1 (merged rail family)",
                   rack_bars[0]: "MAST ASSY:1/RACK GEAR (merged rack family)"}
    family_members = {mast_segments[0]: mast_segments, rack_bars[0]: rack_bars}
    rolling = [i for i in drive_rows if ROLLING_GEAR.search(paths[i])]

    # Column clearance.
    t0 = time.perf_counter()
    clearance = ColumnClearance(meshes, moving, fixed, family_of)
    pairs = clearance.pair_table()
    timings["column_clearance_s"] = round(time.perf_counter() - t0, 1)
    pairs["group"] = [motions[m] for m in pairs["moving"]]
    rolling_mask = pairs["moving"].isin(rolling) & (pairs["fixed"] == rack_bars[0])
    pairs = pairs[~rolling_mask].reset_index(drop=True)

    def fixed_label(owner: int, actual: int) -> str:
        if owner in family_name:
            return f"{short_name(paths[actual])} [{family_name[owner]}]"
        return short_name(paths[actual])

    t0 = time.perf_counter()
    refiner = Refiner(meshes, paths)
    candidates = {}
    sliding_pairs = []
    rejected_pairs = []
    for key, rows, column, sign in (
        ("drive_up", drive_rows, "up_mm", 1.0),
        ("tool_up", tool_rows, "up_mm", 1.0),
        ("drive_down", drive_rows, "down_mm", -1.0),
        ("tool_down", tool_rows, "down_mm", -1.0),
    ):
        subset = pairs[pairs["moving"].isin(rows) & np.isfinite(pairs[column])].nsmallest(40, column)
        direction = column.split("_")[0]
        chosen = None
        for row in subset.itertuples():
            estimate = float(getattr(row, column))
            # Stop once the column estimates are clearly beyond the refined contact.
            if chosen is not None and estimate > abs(chosen["travel_mm"]) + 30.0:
                break
            m, owner = int(row.moving), int(row.fixed)
            f = int(getattr(row, f"{direction}_fixed_part"))
            cell = getattr(row, f"{direction}_cell_xz_mm")
            item = {
                "moving_part": short_name(paths[m]),
                "fixed_part": fixed_label(owner, f),
                "column_estimate_mm": round(sign * estimate, 1),
                "contact_column_cad_x_z_mm": [round(cell[0], 1), round(cell[1], 1)],
                "fixed_surface_y_cad_mm": round(float(getattr(row, f"{direction}_fixed_y_mm")), 1),
            }
            members = family_members.get(owner, [owner])
            rest = min(refiner.distance(m, g, 0.0, refiner.exact_available(m, g)) for g in members)
            if rest <= COLOCATED_TOL_MM:
                # Sliding along the family at rest: the exact distance stays 0 while sliding, so the
                # column estimate (co-located cells excluded) is the result.
                item |= {"method": "column estimate, sliding pair (5 mm cells, 4 mm samples)",
                         "travel_mm": round(sign * estimate, 1), "distance_at_rest_mm": round(rest, 3)}
                sliding_pairs.append(item)
            else:
                item |= refiner.first_contact(m, f, estimate, sign)
                if item["travel_mm"] is None:
                    rejected_pairs.append(item)
                    continue
            if chosen is None or abs(item["travel_mm"]) < abs(chosen["travel_mm"]):
                chosen = item
        candidates[key] = chosen
    timings["refine_s"] = round(time.perf_counter() - t0, 1)

    engagement = engagement_limits(table, meshes)
    rail_low = max(r["travel_mm"][0] for r in engagement["rails"])
    rail_high = min(r["travel_mm"][1] for r in engagement["rails"])

    def extent(rows: list[int]) -> tuple[float, float]:
        return (float(min(meshes[i].bounds[0][1] for i in rows)), float(max(meshes[i].bounds[1][1] for i in rows)))

    drive_low_y, drive_high_y = extent(drive_rows)
    tool_low_y, tool_high_y = extent(tool_rows)
    pads_z = [summary["legs"][n]["pad_center_body_m"][2] for n in LEG_ORDER]
    ground = {
        "crawler_bottom_ground_y_cad_mm": CRAWLER_GROUND_Y_MM,
        "tool_bottom_y_cad_mm": round(tool_low_y, 1),
        "travel_until_tool_touches_crawler_ground_mm": round(CRAWLER_GROUND_Y_MM - tool_low_y, 1),
        "lowest_pad_bottom_body_z_m": round(min(pads_z), 4),
        "travel_until_tool_reaches_pad_bottom_level_mm": round(min(pads_z) * 1000 - tool_low_y, 1),
        "note": "tool below ground = drilling; not a travel limit of the drive (user premise)",
    }

    # Limits. Upper: the moving set (drive + tool) translates as one body -> min of both.
    upper_drive = candidates["drive_up"]["travel_mm"]
    upper_tool = candidates["tool_up"]["travel_mm"]
    upper = min(upper_drive, upper_tool, rail_high, engagement["rack_travel_mm"][1])
    upper_source = ("tool_up" if upper == upper_tool else "drive_up" if upper == upper_drive else "engagement")
    lower_drive = candidates["drive_down"]["travel_mm"]
    lower_tool = candidates["tool_down"]["travel_mm"]
    lower = max(lower_drive, rail_low, engagement["rack_travel_mm"][0])
    lower_source = "drive_down" if lower == lower_drive else "engagement"
    middle = (upper + lower) / 2
    travels = {"top": upper, "middle": middle, "bottom": lower}
    print(json.dumps({"candidates": candidates, "rail_travel_mm": [rail_low, rail_high],
                      "rack_travel_mm": engagement["rack_travel_mm"]}, ensure_ascii=False, indent=1, default=float),
          flush=True)
    if upper <= lower:
        raise SystemExit(f"empty travel range: lower {lower} mm, upper {upper} mm")

    # Mass properties per level.
    legs = summary["legs"]
    pads_body = np.array([legs[name]["pad_center_body_m"] for name in LEG_ORDER])
    polygon = pads_body[[0, 1, 3, 2], :2]
    current = level_report(table, 0.0, pads_body, polygon)
    reference = summary["mass_properties"]
    reproduction = {}
    for case in CASES:
        ref = reference[case]["superstructure"]
        mass_rel = abs(current[case]["mass_kg"] - ref["mass_kg"]) / ref["mass_kg"]
        cog_diff = float(np.max(np.abs(np.array(current[case]["cog_body_m"]) - np.array(ref["cog_body_m"]))))
        inertia_diff = float(np.max(np.abs(np.array(current[case]["inertia_about_cog_body_kg_m2"])
                                           - np.array(ref["inertia_about_cog_body_kg_m2"]))))
        reproduction[case] = {"mass_rel_diff": mass_rel, "cog_max_abs_diff_m": cog_diff,
                              "inertia_max_abs_diff_kg_m2": inertia_diff}

    span = upper - lower
    levels = {}
    for name in LEVEL_NAMES:
        travel = travels[name]
        levels[name] = {
            "name": name,
            "travel_mm": round(travel, 2),
            "travel_m": round(travel / 1000, 5),
            "percent_of_range": round(100 * (travel - lower) / span, 2),
            "marks_body_z_m": {
                "drive_bottom": round((drive_low_y + travel) / 1000, 4),
                "drive_top": round((drive_high_y + travel) / 1000, 4),
                "tool_bottom": round((tool_low_y + travel) / 1000, 4),
                "tool_top": round((tool_high_y + travel) / 1000, 4),
            },
            "mass": level_report(table, travel, pads_body, polygon),
        }
    current_percent = round(100 * (0.0 - lower) / span, 2)

    # Moving-set summary.
    moving_table = table[table["motion"].isin(MOVING)]
    moving_summary = {
        "rows": int(len(moving_table)),
        "rows_with_volume": int((moving_table["volume_used_mm3"] > 0).sum()),
        "by_group": {
            group: {
                "rows": int((moving_table["motion"] == group).sum()),
                "mass_step_kg": round(float(moving_table.loc[moving_table["motion"] == group, "mass_step_kg"].sum()), 1),
                "mass_generic_as_steel_kg": round(
                    float(moving_table.loc[moving_table["motion"] == group, "mass_generic_as_steel_kg"].sum()), 1),
                "mass_tool_steel_kg": round(
                    float(moving_table.loc[moving_table["motion"] == group, "mass_tool_steel_kg"].sum()), 1),
            }
            for group in MOVING
        },
        "mass_step_kg": round(float(moving_table["mass_step_kg"].sum()), 1),
        "mass_generic_as_steel_kg": round(float(moving_table["mass_generic_as_steel_kg"].sum()), 1),
        "mass_tool_steel_kg": round(float(moving_table["mass_tool_steel_kg"].sum()), 1),
        "y_extent_cad_mm": {"drive": [round(drive_low_y, 1), round(drive_high_y, 1)],
                            "tool": [round(tool_low_y, 1), round(tool_high_y, 1)]},
        "heaviest_drive_sub_assemblies_step_kg": moving_table[moving_table["motion"] == MOVING_DRIVE]
        .groupby("sub_assembly")["mass_step_kg"].sum().nlargest(8).round(1).to_dict(),
        "boundary_decisions": [
            {"part": "LOCKING CYL / LOCKING CYL_MIR", "decision": "이동(구동부)", "confidence": "높음"},
            {"part": "GUID CATCHER ×6, CATCHER PAD (슬라이드 슈·패드)", "decision": "이동(구동부)", "confidence": "높음"},
            {"part": "AUGER FRAME ASSY 솔리드24 (슬라이드판)", "decision": "이동(구동부)", "confidence": "높음"},
            {"part": "AUGER TOOL (로드·캡·조인트 핀·섀클)", "decision": "이동(공구, 사용자 전제)", "confidence": "중간"},
            {"part": "LOWER GUIDE_ASSY", "decision": "고정(마스트 하단)", "confidence": "중간"},
            {"part": "Hose guide arm / Hose guide CYL", "decision": "고정(붐)", "confidence": "중간"},
            {"part": "윈치", "decision": "고정(마스트)", "confidence": "높음"},
            {"part": "와이어·호스", "decision": "모델에 없음(질량 0)", "confidence": "높음"},
            {"part": "TOPSHEAVE, MAST ASSY(랙 포함)", "decision": "고정", "confidence": "높음"},
        ],
    }

    sensitivity = {
        case: {
            "moving_mass_kg": current[case]["moving_set_mass_kg"],
            "superstructure_mass_kg": current[case]["mass_kg"],
            "cog_z_shift_per_1m_travel_m": round(current[case]["moving_set_mass_kg"] / current[case]["mass_kg"], 5),
        }
        for case in MASS_CASES
    }

    part_columns = ["instance_path", "top_assembly", "sub_assembly", "motion", "motion_reason", "confidence",
                    "mass_step_kg", "mass_generic_as_steel_kg", "mass_tool_steel_kg", "bbox_min_y_mm", "bbox_max_y_mm", "group", "is_crawler"]
    table[part_columns].to_csv(AUGER_PARTS_CSV, index=False, encoding="utf-8-sig")

    output = {
        "frames": "CAD root frame mm (Y up); body x=Z_cad, y=X_cad, z=Y_cad (m), origin = CAD origin",
        "travel_convention": "travel = translation of drive + tool along CAD +Y (= body +z) from the CAD pose; "
                             "inertia about the CoG in body axes (tensor notation, off-diagonal = -integral xy dm)",
        "scenario": "mast upright (CAD pose); drive + auger tool translate together along the mast (user, 2026-10-19)",
        "mass_cases": {
            "step": "A: STEP densities as written (Inventor 'generic' = 1.0 g/cm^3 kept)",
            "generic_as_steel": "B (comparison only): 'generic' 1.0 -> steel 7.85, glass/window -> 2.5 g/cm^3",
            TOOL_STEEL: "C (reference, provisional, CLAUDE.md 2026-10-19): STEP densities except the 5 AUGER TOOL "
                        "rows -> steel 7.85 g/cm^3",
        },
        "mast_axis": mast_axis,
        "moving_set": moving_summary,
        "travel_limit_candidates": candidates,
        "sliding_pairs_checked": sliding_pairs,
        "column_hits_rejected_by_exact_check": rejected_pairs,
        "rolling_pairs_excluded": {"moving": [short_name(paths[i]) for i in rolling],
                                   "fixed": "MAST ASSY:1/RACK GEAR (all bars)",
                                   "reason": "rack and pinion roll on each other; covered by the engagement check"},
        "nearest_pairs": {
            "drive_up": pair_rows(pairs[pairs["group"] == MOVING_DRIVE], paths, motions, "up_mm"),
            "tool_up": pair_rows(pairs[pairs["group"] == MOVING_TOOL], paths, motions, "up_mm"),
            "drive_down": pair_rows(pairs[pairs["group"] == MOVING_DRIVE], paths, motions, "down_mm"),
            "tool_down": pair_rows(pairs[pairs["group"] == MOVING_TOOL], paths, motions, "down_mm"),
        },
        "engagement": engagement,
        "ground": ground,
        "range": {
            "upper_travel_mm": round(upper, 2),
            "upper_source": upper_source,
            "upper_drive_only_travel_mm": upper_drive,
            "lower_travel_mm": round(lower, 2),
            "lower_source": lower_source,
            "lower_alternative_tool_contact_travel_mm": lower_tool,
            "lower_alternative_tool_at_crawler_ground_mm": ground["travel_until_tool_touches_crawler_ground_mm"],
            "span_mm": round(span, 2),
            "current_cad_pose_percent_of_range": current_percent,
            "default_rule": "upper = first contact of drive or tool (they move as one body); lower = drive "
                            "mechanism limit (drive parts vs fixed parts); tool going below the lower guide or "
                            "ground is treated as drilling (user, 2026-10-19)",
        },
        "levels": levels,
        "current_cad_pose": {"travel_mm": 0.0, "mass": current},
        "reproduces_cad_summary_superstructure": reproduction,
        "sensitivity": sensitivity,
        "settings": {
            "mesh_linear_deflection_mm": json.loads(MESH_INDEX_JSON.read_text(encoding="utf-8"))["linear_deflection_mm"],
            "sample_spacing_mm": SAMPLE_SPACING_MM,
            "cell_mm": CELL_MM,
            "colocated_tolerance_mm": COLOCATED_TOL_MM,
            "exact_touch_mm": EXACT_TOUCH_MM,
            "mesh_touch_mm": MESH_TOUCH_MM,
            "fixed_parts_in_footprint": len(clearance.fixed),
            "fixed_points": clearance.fixed_point_count,
            "moving_parts_with_mesh": len(moving),
            "gravity_m_s2": GRAVITY_M_S2,
            "leg_load_model": "rigid body on four equal vertical springs, rigid floor; F_i = a + b x_i + c y_i",
        },
        "timings_s": timings,
    }

    if not arguments.skip_render:
        t0 = time.perf_counter()
        render = render_meshes(meshes)
        limits = ((-3.3, 6.0), (-1.5, 12.2))
        output["figures"] = render_figures(render, motions, levels, pads_body, limits)
        output["figure_axis_limits_body_m"] = {"x": limits[0], "z": limits[1]}
        timings["render_s"] = round(time.perf_counter() - t0, 1)

    timings["total_s"] = round(time.perf_counter() - started, 1)
    AUGER_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps({"range": output["range"], "candidates": candidates, "timings": timings},
                     ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
