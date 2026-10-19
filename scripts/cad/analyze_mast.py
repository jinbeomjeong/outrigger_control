"""Mast folding analysis: hinge, backstay kinematics, poses, mass properties.

Reads only cached data (no STEP parsing):
    cad/parts_classified.csv   from analyze_parts.py
    cad/cad_summary.json       leg pad positions
    cad/mast_faces.csv         from inspect_mast.py (pin/bore faces with axis points)
    cad/meshes/*.npz|json      from export_meshes.py (tessellated parts)

Writes:
    cad/mast_parts.csv          per-part motion category with reason
    cad/mast_summary.json       hinge, joints, backstay, angles, mass properties
    cad/mast_interference.csv   mesh-level contact sweep (pair, first contact angle, clearance)
    cad/mast_poses.png          side-view bbox layout of both poses
    cad/mast_steps/*.png        tessellated side/isometric views per fold step
    cad/mast_steps/steps.csv    per-step angle, CoG and leg load estimate
    cad/meshes/render_mesh.npz  decimated meshes for drawing (cache)
    cad/meshes/contact_sweep_records.csv  raw sweep distances (cache, --reuse-sweep)

Exact B-rep distances (BRepExtrema) for the closest pairs use cad/mast/*.brep.

Frames. CAD root frame in mm (Y up). Body frame (CLAUDE.md): x = Z_cad,
y = X_cad, z = Y_cad, same origin. The fold angle ``theta`` is positive when
the mast top moves rearward; it is a rotation of -theta about CAD +X (body +y)
through the hinge axis.

Usage:
    python -I scripts/cad/analyze_mast.py [--skip-render]
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import fast_simplification
import trimesh
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PolyCollection
from matplotlib.patches import Rectangle
from OCC.Core.BRep import BRep_Builder
from OCC.Core.BRepExtrema import BRepExtrema_DistShapeShape
from OCC.Core.BRepTools import breptools
from OCC.Core.gp import gp_Trsf
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.TopoDS import TopoDS_Shape
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_parts import (
    BBOX_MAX_COLUMNS,
    BBOX_MIN_COLUMNS,
    CAD_TO_BODY,
    CENTROID_COLUMNS,
    CLASSIFIED_CSV,
    INERTIA_COLUMNS,
    combine_mass_properties,
)
from cad_common import CAD_DIR, SUMMARY_JSON
from export_meshes import MESH_DIR, MESH_INDEX_JSON, load_meshes
from inspect_mast import MAST_BREP_DIR, MAST_FACES_CSV, MAST_INDEX_JSON

MAST_PARTS_CSV = CAD_DIR / "mast_parts.csv"
MAST_SUMMARY_JSON = CAD_DIR / "mast_summary.json"
INTERFERENCE_CSV = CAD_DIR / "mast_interference.csv"
POSES_PNG = CAD_DIR / "mast_poses.png"
STEPS_DIR = CAD_DIR / "mast_steps"
STEPS_CSV = STEPS_DIR / "steps.csv"
RENDER_NPZ = MESH_DIR / "render_mesh.npz"
SWEEP_RECORDS_CSV = MESH_DIR / "contact_sweep_records.csv"

GRAVITY_M_S2 = 9.80665
CASES = ("step", "generic_as_steel")
CASE_LABEL = {"step": "A", "generic_as_steel": "B"}
LEG_ORDER = ("FL", "FR", "RL", "RR")

# Motion categories.
ROTATING = "rotating"
FIXED = "fixed"
LINK_BARREL = "link_backstay_barrel"
LINK_ROD = "link_backstay_rod"
LINK_STATIC = "link_static"
UNRESOLVED = "undetermined"
LEG_ROD_PAD = "excluded_leg_rod_pad"
MOVING = (ROTATING, LINK_BARREL, LINK_ROD)

ROTATING_ASSEMBLIES = {
    "MAST ASSY:1": "마스트 본체(MAST, MAST-2..5, 핀·부시·랙). BUSH-1이 힌지 핀(R75)에 끼워짐",
    "0. DRIVE AUGER ASSY:1": "마스트 전면 랙(MAST 랙기어 Z 2667–2725) 위의 구동부, Y 5258–7130은 마스트만 있는 높이",
    "TOPSHEAVE(조립) ASSY:1": "마스트 상단(Y ≥ 9851, MAST-5 상단면)에 얹힌 탑시브",
    "AUGER TOOL:1": "구동부에 매달린 오거 공구(운송 시 장착 유지 가정)",
    "LOWER GUIDE_ASSY:1": "마스트 하단(MAST:1, Y −649) 앞의 하부 가이드, 다른 지지 부재 없음",
    "윈치:1": "Y 2174–2659 높이에서 닿는 부재가 MAST-2뿐(붐 상단 Y 1775)",
}
LINK_STATIC_ASSEMBLIES = {
    "BOOM:1": "데크와 세로축(CAD Z) 핀(X 470, Y 569)으로 연결된 측방 경사 프레임. 마스트 접기 중 움직이지 않음",
    "BOOM CYL:1": "데크(X −530, Y 459)–붐(X −530, Y 889) 사이 수직 실린더, 붐 측방 경사용. 접기와 무관",
}
UNRESOLVED_ASSEMBLIES = {
    "Hose guide arm:1": "붐에 핀(Y 1710, Z 1329) 결합, 자체 실린더로 움직이는 링크. 운송 자세 미상 → 고정 유지(링크 미반영)",
    "Hose guide CYL:1": "붐(Y 1470, Z 892)–호스 가이드 암(Y 3083, Z 1186) 실린더. 운송 자세 미상 → 고정 유지(링크 미반영)",
}
BACKSTAY = "BACKSTAY CYL:1"

JOINT_CUT_RADIUS_MM = {"hinge": 160.0, "backstay_lower": 115.0, "backstay_upper": 115.0}
CONTACT_DISTANCE_MM = 3.0  # = mesh linear deflection
SAMPLE_SPACING_MM = 8.0
MAX_SAMPLES_PER_PART = 400_000
REFINE_POINTS = 64
SWEEP_STEP_DEG = 0.5
SWEEP_MAX_DEG = 93.0
EXACT_TOUCH_MM = 0.01
EXACT_SCAN_HALF_DEG = 0.6
EXACT_SCAN_STEP_DEG = 0.05
RENDER_TRIANGLE_BUDGET = 300_000
STEP_ANGLES_DEG = (0.0, 15.0, 30.0, 45.0, 60.0, 75.0)

COLORS = {
    FIXED: "#a8a7a0",
    LEG_ROD_PAD: "#7d7c77",
    ROTATING: "#2a78d6",
    LINK_BARREL: "#eb6834",
    LINK_ROD: "#eb6834",
    LINK_STATIC: "#c9541f",
    UNRESOLVED: "#eda100",
}
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------
def rotation_x(angle_rad: float) -> np.ndarray:
    """Rotation matrix about CAD +X (right-handed)."""
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def rigid(rotation: np.ndarray, pivot: np.ndarray, shift=np.zeros(3)) -> np.ndarray:
    """4x4 transform: rotate about ``pivot`` then translate by ``shift`` (mm)."""
    transform = np.eye(4)
    transform[:3, :3] = rotation
    transform[:3, 3] = pivot - rotation @ pivot + shift
    return transform


def apply(transform: np.ndarray, points: np.ndarray) -> np.ndarray:
    return points @ transform[:3, :3].T + transform[:3, 3]


def short_name(path: str) -> str:
    return "/".join(path.split(" / ")[1:])


# --------------------------------------------------------------------------
# Joints from coaxial pin/bore faces
# --------------------------------------------------------------------------
def find_joints(faces: pd.DataFrame) -> pd.DataFrame:
    """Coaxial cylinder clusters shared by different top assemblies.

    A cluster is the set of cylinder faces whose axis is parallel to a CAD
    axis and passes through the same point (rounded to 1 mm) in the plane
    normal to it. Clusters touching two or more top assemblies are joints.
    """
    cylinders = faces[faces["surface_type"] == "cylinder"].copy()
    cylinders["top"] = cylinders["instance_path"].str.split(" / ").str[1]
    rows = []
    for axis_index, axis_name in enumerate("XYZ"):
        column = ["axis_or_normal_x", "axis_or_normal_y", "axis_or_normal_z"][axis_index]
        aligned = cylinders[cylinders[column].abs() > 0.9999].copy()
        others = [i for i in range(3) if i != axis_index]
        point_columns = [f"axis_point_{'xyz'[i]}_mm" for i in range(3)]
        keys = [aligned[point_columns[i]].round(0) for i in others]
        for key, group in aligned.groupby(keys):
            tops = sorted(group["top"].unique())
            if len(tops) < 2:
                continue
            points = group[point_columns].to_numpy()
            weights = group["area_mm2"].to_numpy()
            centre = (points * weights[:, None]).sum(0) / weights.sum()
            spread = np.abs(points[:, others] - centre[others]).max()
            radii = group.groupby("top")["radius_mm"].max().round(1).to_dict()
            rows.append(
                {
                    "axis": axis_name,
                    "point_cad_mm": np.round(centre, 1).tolist(),
                    "assemblies": tops,
                    "max_radius_by_assembly_mm": radii,
                    "face_count": len(group),
                    "axis_point_spread_mm": round(float(spread), 3),
                    "axial_range_mm": [
                        round(float(group[f"bbox_min_{'xyz'[axis_index]}_mm"].min()), 1),
                        round(float(group[f"bbox_max_{'xyz'[axis_index]}_mm"].max()), 1),
                    ],
                    "parts": sorted({short_name(p) for p in group["instance_path"]}),
                }
            )
    return pd.DataFrame(rows)


def pick_joint(joints: pd.DataFrame, axis: str, required: set[str]) -> dict:
    match = joints[
        (joints["axis"] == axis) & joints["assemblies"].map(lambda t: required <= set(t))
    ]
    if len(match) != 1:
        raise SystemExit(f"expected one {axis}-joint with {required}, got {len(match)}")
    return match.iloc[0].to_dict()


def hinge_axis_direction(faces: pd.DataFrame, point: np.ndarray) -> np.ndarray:
    """Area-weighted mean axis of the cylinder faces on the hinge line."""
    cylinders = faces[faces["surface_type"] == "cylinder"]
    points = cylinders[["axis_point_y_mm", "axis_point_z_mm"]].to_numpy()
    near = np.linalg.norm(points - point[1:], axis=1) < 1.0
    axes = cylinders.loc[near, ["axis_or_normal_x", "axis_or_normal_y", "axis_or_normal_z"]]
    axes = axes.to_numpy() * np.sign(axes.to_numpy()[:, :1])
    weights = cylinders.loc[near, "area_mm2"].to_numpy()
    mean = (axes * weights[:, None]).sum(0)
    return mean / np.linalg.norm(mean)


# --------------------------------------------------------------------------
# Backstay cylinder
# --------------------------------------------------------------------------
def backstay_geometry(faces: pd.DataFrame, lower: np.ndarray, upper: np.ndarray) -> dict:
    """Bore floor, gland and piston faces along the cylinder axis -> length range."""
    axis = (upper - lower) / np.linalg.norm(upper - lower)
    own = faces[faces["instance_path"].str.contains(f" / {BACKSTAY} / ")].copy()
    own["solid"] = own["instance_path"].str.split(" / ").str[-1]
    normals = own[["axis_or_normal_x", "axis_or_normal_y", "axis_or_normal_z"]].to_numpy()
    centres = (
        own[BBOX_MIN_COLUMNS].to_numpy() + own[BBOX_MAX_COLUMNS].to_numpy()
    ) / 2
    own["t_mm"] = (centres - lower) @ axis
    is_cap = (own["surface_type"] == "plane") & (np.abs(np.abs(normals @ axis) - 1) < 1e-4)
    coaxial = (own["surface_type"] == "cylinder") & (np.abs(np.abs(normals @ axis) - 1) < 1e-4)
    rod_solid = own.loc[coaxial & (own["radius_mm"].round(1) == 60.0), "solid"]
    bore_radius = 100.0
    rod_radius = 60.0
    full = math.pi * bore_radius**2
    annulus = math.pi * (bore_radius**2 - rod_radius**2)
    caps = own[is_cap]

    def cap_t(solid_tag: str, area: float) -> list[float]:
        chosen = caps[caps["solid"].str.contains(solid_tag) & np.isclose(caps["area_mm2"], area, rtol=1e-3)]
        return sorted(chosen["t_mm"].round(2).tolist())

    barrel_tag, rod_tag = "솔리드3", "솔리드2"
    bore_floor = cap_t(barrel_tag, full)[0]
    gland = cap_t(barrel_tag, annulus)[0]
    piston_bottom = cap_t(rod_tag, full)[0]
    piston_top = cap_t(rod_tag, annulus)[0]
    length_now = float(np.linalg.norm(upper - lower))
    return {
        "lower_pivot_cad_mm": lower.round(1).tolist(),
        "upper_pivot_cad_mm": upper.round(1).tolist(),
        "barrel_solid": barrel_tag,
        "rod_solid": rod_tag,
        "rod_solids_seen": sorted(set(rod_solid)),
        "bore_radius_mm": bore_radius,
        "rod_radius_mm": rod_radius,
        "axial_positions_from_lower_pivot_mm": {
            "bore_floor": bore_floor,
            "piston_bottom": piston_bottom,
            "piston_top": piston_top,
            "gland_inner_face": gland,
        },
        "pin_to_pin_now_mm": round(length_now, 2),
        "pin_to_pin_min_mm": round(length_now - (piston_bottom - bore_floor), 2),
        "pin_to_pin_max_mm": round(length_now + (gland - piston_top), 2),
        "stroke_mm": round((piston_bottom - bore_floor) + (gland - piston_top), 2),
    }


class FoldKinematics:
    """Pose transforms of the moving groups as a function of the fold angle."""

    def __init__(self, hinge: np.ndarray, lower: np.ndarray, upper: np.ndarray):
        self.hinge, self.lower, self.upper = hinge, lower, upper
        self.length_now = float(np.linalg.norm(upper - lower))
        self.direction_now = (upper - lower) / self.length_now

    def mast(self, theta_deg: float) -> np.ndarray:
        return rigid(rotation_x(-math.radians(theta_deg)), self.hinge)

    def upper_pivot(self, theta_deg: float) -> np.ndarray:
        return apply(self.mast(theta_deg), self.upper[None])[0]

    def backstay_length(self, theta_deg: float) -> float:
        return float(np.linalg.norm(self.upper_pivot(theta_deg) - self.lower))

    def _swing(self, theta_deg: float) -> tuple[np.ndarray, np.ndarray, float]:
        upper = self.upper_pivot(theta_deg)
        direction = (upper - self.lower) / np.linalg.norm(upper - self.lower)
        before = math.atan2(self.direction_now[2], self.direction_now[1])
        after = math.atan2(direction[2], direction[1])
        return rotation_x(after - before), direction, float(np.linalg.norm(upper - self.lower))

    def barrel(self, theta_deg: float) -> np.ndarray:
        rotation, _, _ = self._swing(theta_deg)
        return rigid(rotation, self.lower)

    def rod(self, theta_deg: float) -> np.ndarray:
        rotation, direction, length = self._swing(theta_deg)
        return rigid(rotation, self.lower, (length - self.length_now) * direction)

    def transforms(self, theta_deg: float) -> dict[str, np.ndarray]:
        return {
            ROTATING: self.mast(theta_deg),
            LINK_BARREL: self.barrel(theta_deg),
            LINK_ROD: self.rod(theta_deg),
        }

    def angle_for_length(self, length_mm: float) -> float:
        low, high = 0.0, 135.0
        for _ in range(60):
            middle = (low + high) / 2
            if self.backstay_length(middle) > length_mm:
                low = middle
            else:
                high = middle
        return (low + high) / 2


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------
def classify(parts: pd.DataFrame) -> pd.DataFrame:
    categories, reasons, confidences = [], [], []
    for row in parts.itertuples():
        top = row.top_assembly
        if row.group == "leg_rod_pad":
            item = (LEG_ROD_PAD, "다리 이동부(로드+패드), 상부체 정의에서 제외(기존 정의)", "높음")
        elif top in ROTATING_ASSEMBLIES:
            confidence = "중간" if top in ("AUGER TOOL:1", "LOWER GUIDE_ASSY:1", "윈치:1") else "높음"
            item = (ROTATING, ROTATING_ASSEMBLIES[top], confidence)
        elif top == BACKSTAY:
            if "솔리드3" in row.instance_path:
                item = (LINK_BARREL, "백스테이 배럴: 붐 핀(Y 846, Z 1017)을 중심으로 스윙", "높음")
            else:
                item = (LINK_ROD, "백스테이 로드: 마스트 핀(Y 4821, Z 1978)과 함께 이동, 배럴 축을 따라 수축", "높음")
        elif top in LINK_STATIC_ASSEMBLIES:
            item = (LINK_STATIC, LINK_STATIC_ASSEMBLIES[top], "높음")
        elif top in UNRESOLVED_ASSEMBLIES:
            item = (UNRESOLVED, UNRESOLVED_ASSEMBLIES[top], "낮음")
        else:
            item = (FIXED, "상부체 고정부(데크·운전실·하우징·카운터웨이트·크롤러 등)", "높음")
        categories.append(item[0])
        reasons.append(item[1])
        confidences.append(item[2])
    result = parts.copy()
    result["motion_category"] = categories
    result["motion_reason"] = reasons
    result["confidence"] = confidences
    return result


# --------------------------------------------------------------------------
# Mass properties in a pose
# --------------------------------------------------------------------------
def posed_parts(parts: pd.DataFrame, transforms: dict[str, np.ndarray]) -> pd.DataFrame:
    """Copy of the part table with centroids and inertia tensors moved."""
    posed = parts.copy()
    for category, transform in transforms.items():
        mask = posed["motion_category"] == category
        if not mask.any():
            continue
        rotation = transform[:3, :3]
        posed.loc[mask, CENTROID_COLUMNS] = apply(
            transform, posed.loc[mask, CENTROID_COLUMNS].to_numpy()
        )
        tensors = np.zeros((mask.sum(), 3, 3))
        for (i, j), name in INERTIA_COLUMNS.items():
            tensors[:, i, j] = posed.loc[mask, name].to_numpy()
            tensors[:, j, i] = posed.loc[mask, name].to_numpy()
        tensors = np.einsum("ij,njk,lk->nil", rotation, tensors, rotation)
        for (i, j), name in INERTIA_COLUMNS.items():
            posed.loc[mask, name] = tensors[:, i, j]
    return posed


def superstructure_properties(posed: pd.DataFrame) -> dict:
    subset = posed[posed["group"] != "leg_rod_pad"]
    return {case: combine_mass_properties(subset, case).to_report() for case in CASES}


def leg_loads(legs_xy: np.ndarray, mass_kg: float, cog_xy: np.ndarray) -> np.ndarray:
    """Vertical leg reactions (N) of a rigid body on four equal vertical springs.

    The reactions are linear in the pad position, F_i = a + b x_i + c y_i, and
    satisfy force and moment equilibrium about x and y.
    """
    weight = mass_kg * GRAVITY_M_S2
    basis = np.column_stack([np.ones(len(legs_xy)), legs_xy])
    coefficients = np.linalg.solve(basis.T @ basis, weight * np.array([1.0, *cog_xy]))
    return basis @ coefficients


def point_in_polygon(point: np.ndarray, polygon: np.ndarray) -> bool:
    inside = False
    for i in range(len(polygon)):
        a, b = polygon[i], polygon[(i + 1) % len(polygon)]
        if (a[1] > point[1]) != (b[1] > point[1]):
            x_cross = a[0] + (point[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if point[0] < x_cross:
                inside = not inside
    return inside


def tensor_checks(report: dict) -> dict:
    tensor = np.array(report["inertia_about_cog_body_kg_m2"])
    moments = np.sort(np.linalg.eigvalsh(tensor))
    return {
        "symmetric": bool(np.allclose(tensor, tensor.T)),
        "positive_definite": bool(moments[0] > 0),
        "triangle_inequality": bool(moments[0] + moments[1] >= moments[2]),
    }


# --------------------------------------------------------------------------
# Mesh-level contact sweep (surface distance)
# --------------------------------------------------------------------------
class SurfaceSamples:
    """Per-part surface points (vertices + even samples) and KD-trees, original pose."""

    def __init__(self, meshes, spacing_mm: float):
        self.meshes = meshes
        self.spacing = spacing_mm
        self.points: dict[int, np.ndarray] = {}
        self.trees: dict[int, cKDTree] = {}

    def get_points(self, index: int) -> np.ndarray:
        if index not in self.points:
            mesh = self.meshes[index]
            count = int(min(MAX_SAMPLES_PER_PART, mesh.area / self.spacing**2))
            samples = np.zeros((0, 3))
            if count > 0:
                samples, _ = trimesh.sample.sample_surface(mesh, count, seed=0)
            self.points[index] = np.vstack([np.asarray(mesh.vertices), samples])
        return self.points[index]

    def get_tree(self, index: int) -> cKDTree:
        if index not in self.trees:
            self.trees[index] = cKDTree(self.get_points(index))
        return self.trees[index]


def joint_axes(kinematics: "FoldKinematics", theta_deg: float) -> list[tuple[np.ndarray, float]]:
    """Pin axes (points on CAD X lines) and exclusion radii in the current pose."""
    return [
        (kinematics.hinge, JOINT_CUT_RADIUS_MM["hinge"]),
        (kinematics.lower, JOINT_CUT_RADIUS_MM["backstay_lower"]),
        (kinematics.upper_pivot(theta_deg), JOINT_CUT_RADIUS_MM["backstay_upper"]),
    ]


def outside_joints(points: np.ndarray, axes) -> np.ndarray:
    keep = np.ones(len(points), dtype=bool)
    for centre, radius in axes:
        keep &= np.hypot(points[:, 1] - centre[1], points[:, 2] - centre[2]) > radius
    return keep


class ContactSweep:
    """Minimum surface distance between moving parts and the rest over the fold angle.

    Moving-part surface points are transformed into the other part's original
    frame and matched against its KD-tree; the nearest candidates are refined
    with an exact closest-point query on the other mesh. Points inside the
    exclusion cylinders around the three pin axes are ignored (pin, bush and
    eye surfaces are in contact by design).
    """

    def __init__(self, table: pd.DataFrame, meshes, kinematics: FoldKinematics):
        self.table = table
        self.meshes = meshes
        self.kinematics = kinematics
        self.samples = SurfaceSamples(meshes, SAMPLE_SPACING_MM)
        categories = table["motion_category"].to_numpy()
        has_mesh = np.array([len(m.faces) > 0 for m in meshes])
        self.moving = np.flatnonzero(np.isin(categories, MOVING) & has_mesh)
        self.static = np.flatnonzero(~np.isin(categories, MOVING) & has_mesh)
        self.categories = categories
        self.static_lower = np.array([meshes[i].bounds[0] for i in self.static])
        self.static_upper = np.array([meshes[i].bounds[1] for i in self.static])
        self.baseline: dict[tuple[int, int], float] = {}

    def _transform(self, index: int, transforms) -> np.ndarray:
        return transforms.get(self.categories[index], np.eye(4))

    def candidate_pairs(self, theta_deg: float) -> list[tuple[int, int]]:
        transforms = self.kinematics.transforms(theta_deg)
        margin = CONTACT_DISTANCE_MM + SAMPLE_SPACING_MM
        lower, upper = [], []
        for i in self.moving:
            points = apply(self._transform(i, transforms), np.asarray(self.meshes[i].vertices))
            lower.append(points.min(0) - margin)
            upper.append(points.max(0) + margin)
        lower, upper = np.array(lower), np.array(upper)
        overlap = (lower[:, None, :] <= self.static_upper[None]) & (upper[:, None, :] >= self.static_lower[None])
        pairs = [(int(self.moving[a]), int(self.static[b])) for a, b in zip(*np.nonzero(overlap.all(axis=2)))]
        links = [k for k, i in enumerate(self.moving) if self.categories[i] != ROTATING]
        rotating = [k for k, i in enumerate(self.moving) if self.categories[i] == ROTATING]
        for a in links:
            for b in rotating:
                if np.all(lower[a] <= upper[b]) and np.all(upper[a] >= lower[b]):
                    pairs.append((int(self.moving[a]), int(self.moving[b])))
        return pairs

    def distance(self, pair, theta_deg: float) -> float:
        """Minimum distance (mm) from part ``pair[0]`` surface to part ``pair[1]`` surface."""
        transforms = self.kinematics.transforms(theta_deg)
        moving, other = pair
        to_world = self._transform(moving, transforms)
        other_world = self._transform(other, transforms)
        world = apply(to_world, self.samples.get_points(moving))
        world = world[outside_joints(world, joint_axes(self.kinematics, theta_deg))]
        if len(world) == 0:
            return math.inf
        inverse = np.linalg.inv(other_world)
        local = apply(inverse, world)
        low, high = self.meshes[other].bounds
        margin = CONTACT_DISTANCE_MM + SAMPLE_SPACING_MM
        near_box = np.all((local >= low - margin) & (local <= high + margin), axis=1)
        local = local[near_box]
        if len(local) == 0:
            return math.inf
        approx, _ = self.samples.get_tree(other).query(local, k=1)
        order = np.argsort(approx)[:REFINE_POINTS]
        if approx[order[0]] > 3 * SAMPLE_SPACING_MM + CONTACT_DISTANCE_MM:
            return float(approx[order[0]])
        _, exact, _ = trimesh.proximity.closest_point(self.meshes[other], local[order])
        return float(exact.min())

    def load(self, records: pd.DataFrame) -> None:
        """Restore the 0-degree baseline from cached sweep records."""
        start = records[records["theta_deg"] == records["theta_deg"].min()]
        self.baseline = {(int(r.moving), int(r.other)): float(r.distance_mm) for r in start.itertuples()}

    def run(self, angles_deg) -> pd.DataFrame:
        records = []
        for theta in angles_deg:
            for pair in self.candidate_pairs(theta):
                distance = self.distance(pair, theta)
                if theta == angles_deg[0]:
                    self.baseline[pair] = distance
                records.append((theta, *pair, distance))
        return pd.DataFrame(records, columns=["theta_deg", "moving", "other", "distance_mm"])

    def is_contact(self, pair, distance: float) -> bool:
        touching_at_start = self.baseline.get(pair, math.inf) < CONTACT_DISTANCE_MM
        return distance < CONTACT_DISTANCE_MM and not touching_at_start

    def refine_first(self, pair, low: float, high: float) -> float:
        """Bisect the first angle at which ``pair`` comes into contact."""
        for _ in range(10):
            middle = (low + high) / 2
            if self.is_contact(pair, self.distance(pair, middle)):
                high = middle
            else:
                low = middle
        return high


def summarize_contacts(sweep: ContactSweep, records: pd.DataFrame, paths, theta_flat: float) -> pd.DataFrame:
    """One row per pair that comes into contact, plus pairs touching from the start."""
    rows = []
    for (moving, other), group in records.groupby(["moving", "other"]):
        pair = (int(moving), int(other))
        contact = group[[sweep.is_contact(pair, d) for d in group["distance_mm"]]]
        at_flat = group.loc[np.isclose(group["theta_deg"], theta_flat), "distance_mm"]
        touching = sweep.baseline.get(pair, math.inf) < CONTACT_DISTANCE_MM
        if contact.empty and not touching:
            continue
        first = math.nan
        if not contact.empty:
            first = float(contact["theta_deg"].min())
            earlier = group.loc[group["theta_deg"] < first, "theta_deg"]
            if len(earlier):
                first = sweep.refine_first(pair, float(earlier.max()), first)
        rows.append(
            {
                "moving_part": short_name(paths[moving]),
                "moving_category": sweep.categories[moving],
                "other_part": short_name(paths[other]),
                "other_category": sweep.categories[other],
                "status": "touching_at_0deg_excluded" if touching else "contact",
                "first_contact_theta_deg": round(first, 2) if not math.isnan(first) else None,
                "last_contact_theta_deg": float(contact["theta_deg"].max()) if not contact.empty else None,
                "distance_at_flat_mm": round(float(at_flat.iloc[0]), 1) if len(at_flat) else None,
                "distance_at_0deg_mm": round(float(sweep.baseline.get(pair, math.inf)), 1),
            }
        )
    frame = pd.DataFrame(rows)
    return frame.sort_values(["status", "first_contact_theta_deg"]) if len(frame) else frame


def nearest_at(sweep: ContactSweep, records: pd.DataFrame, paths, theta: float, count: int = 12) -> list[dict]:
    """Closest non-touching pairs at one angle (clearance list)."""
    rows = records[np.isclose(records["theta_deg"], theta)].copy()
    rows = rows[[sweep.baseline.get((m, o), math.inf) >= CONTACT_DISTANCE_MM for m, o in zip(rows["moving"], rows["other"])]]
    rows = rows.nsmallest(count, "distance_mm")
    return [
        {"moving_part": short_name(paths[r.moving]), "other_part": short_name(paths[r.other]),
         "distance_mm": round(float(r.distance_mm), 1)}
        for r in rows.itertuples()
    ]


def _load_brep(file_name: str) -> TopoDS_Shape:
    shape = TopoDS_Shape()
    if not breptools.Read(shape, str(MAST_BREP_DIR / file_name), BRep_Builder()):
        raise SystemExit(f"cannot read {file_name}")
    return shape


def _moved(shape: TopoDS_Shape, transform: np.ndarray) -> TopoDS_Shape:
    trsf = gp_Trsf()
    trsf.SetValues(*transform[:3, :].ravel().tolist())
    return shape.Moved(TopLoc_Location(trsf))


class ExactClearance:
    """B-rep distance (BRepExtrema) between cached world-placed parts in a pose."""

    def __init__(self, table: pd.DataFrame, kinematics: FoldKinematics):
        self.index = json.loads(MAST_INDEX_JSON.read_text(encoding="utf-8"))["parts"]
        self.table = table
        self.kinematics = kinematics
        self.shapes: dict[str, TopoDS_Shape] = {}

    def available(self, path: str) -> bool:
        return path in self.index

    def _shape(self, path: str) -> TopoDS_Shape:
        if path not in self.shapes:
            self.shapes[path] = _load_brep(self.index[path])
        return self.shapes[path]

    def distance(self, moving: str, other: str, theta_deg: float) -> float:
        transforms = self.kinematics.transforms(theta_deg)
        shapes = []
        for path in (moving, other):
            category = self.table.loc[self.table["instance_path"] == path, "motion_category"].iloc[0]
            shape = self._shape(path)
            if category in transforms:
                shape = _moved(shape, transforms[category])
            shapes.append(shape)
        extrema = BRepExtrema_DistShapeShape(shapes[0], shapes[1])
        extrema.Perform()
        return float(extrema.Value()) if extrema.IsDone() else math.nan

    def first_touch(self, moving: str, other: str, centre: float) -> float | None:
        """First angle near ``centre`` (+-EXACT_SCAN_HALF_DEG) with zero B-rep distance.

        Scans in EXACT_SCAN_STEP_DEG steps (thin parts can pass through each
        other, so the contact is not monotonic in the angle), then bisects.
        """
        previous = None
        theta = max(0.0, centre - EXACT_SCAN_HALF_DEG)
        while theta <= centre + EXACT_SCAN_HALF_DEG + 1e-9:
            if self.distance(moving, other, theta) <= EXACT_TOUCH_MM:
                if previous is None:
                    return theta
                low, high = previous, theta
                for _ in range(8):
                    middle = (low + high) / 2
                    if self.distance(moving, other, middle) <= EXACT_TOUCH_MM:
                        high = middle
                    else:
                        low = middle
                return high
            previous = theta
            theta += EXACT_SCAN_STEP_DEG
        return None


def exact_checks(exact: ExactClearance, contacts: pd.DataFrame, clearance: list[dict],
                 paths: list[str], theta_flat: float, joint_pairs: set[frozenset]) -> list[dict]:
    """Exact distance at the flat pose and exact first-touch angle for close pairs.

    Pairs whose top assemblies share a pin joint are skipped: their B-rep
    distance is the pin/bush contact itself (the mesh sweep excludes the pin
    zones instead).
    """
    short_to_path = {short_name(p): p for p in paths}
    pairs = []
    if len(contacts):
        for r in contacts[contacts["status"] == "contact"].itertuples():
            if r.first_contact_theta_deg is not None and r.first_contact_theta_deg <= theta_flat + 1.0:
                pairs.append((r.moving_part, r.other_part, r.first_contact_theta_deg))
    for item in clearance:
        pairs.append((item["moving_part"], item["other_part"], None))
    rows, seen = [], set()
    for moving, other, mesh_first in pairs:
        if (moving, other) in seen:
            continue
        seen.add((moving, other))
        tops = frozenset((moving.split("/")[0], other.split("/")[0]))
        if tops in joint_pairs:
            rows.append({"moving_part": moving, "other_part": other,
                         "note": "joint partners (pin contact); see mesh distance outside pin zone"})
            continue
        moving_path, other_path = short_to_path[moving], short_to_path[other]
        if not (exact.available(moving_path) and exact.available(other_path)):
            rows.append({"moving_part": moving, "other_part": other, "note": "BREP not cached"})
            continue
        row = {
            "moving_part": moving,
            "other_part": other,
            "mesh_first_contact_theta_deg": mesh_first,
            "exact_distance_at_flat_mm": round(exact.distance(moving_path, other_path, theta_flat), 2),
            "exact_first_touch_theta_deg": None,
        }
        if mesh_first is not None:
            touch = exact.first_touch(moving_path, other_path, mesh_first)
            row["exact_first_touch_theta_deg"] = None if touch is None else round(touch, 3)
        rows.append(row)
    return rows


def rest_gap(meshes, table: pd.DataFrame, transform: np.ndarray, rest_index: int) -> dict:
    """Vertical gap between the rotated mast and the rest bracket top (vertex level)."""
    rest = meshes[rest_index]
    low, high = rest.bounds
    mask = (table["motion_category"] == ROTATING).to_numpy()
    lowest = math.inf
    for i in np.flatnonzero(mask):
        points = apply(transform, np.asarray(meshes[i].vertices))
        inside = (
            (points[:, 0] >= low[0]) & (points[:, 0] <= high[0])
            & (points[:, 2] >= low[2]) & (points[:, 2] <= high[2])
        )
        if inside.any():
            lowest = min(lowest, float(points[inside, 1].min()))
    return {
        "rest_top_y_cad_mm": round(float(high[1]), 1),
        "rotating_lowest_y_over_rest_cad_mm": round(lowest, 1),
        "gap_mm": round(lowest - float(high[1]), 1),
    }


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
def render_meshes(meshes) -> list[tuple[np.ndarray, np.ndarray]]:
    """Decimated copies for drawing, cached in cad/meshes/render_mesh.npz."""
    if RENDER_NPZ.exists() and RENDER_NPZ.stat().st_mtime > MESH_INDEX_JSON.stat().st_mtime:
        data = np.load(RENDER_NPZ)
        vo, fo = data["vertex_offsets"], data["face_offsets"]
        return [
            (data["vertices"][vo[i] : vo[i + 1]].astype(np.float64), data["faces"][fo[i] : fo[i + 1]])
            for i in range(len(vo) - 1)
        ]
    total = sum(len(m.faces) for m in meshes)
    keep_ratio = RENDER_TRIANGLE_BUDGET / total
    result = []
    for mesh in meshes:
        vertices, faces = np.asarray(mesh.vertices), np.asarray(mesh.faces)
        if len(faces) > 400:
            target = max(200, int(len(faces) * keep_ratio))
            vertices, faces = fast_simplification.simplify(
                vertices.astype(np.float32), faces.astype(np.int32), 1 - target / len(faces)
            )
        result.append((np.asarray(vertices, dtype=np.float64), np.asarray(faces)))
    vertex_offsets = np.cumsum([0] + [len(v) for v, _ in result])
    face_offsets = np.cumsum([0] + [len(f) for _, f in result])
    np.savez_compressed(
        RENDER_NPZ,
        vertices=np.concatenate([v for v, _ in result]).astype(np.float32),
        faces=np.concatenate([f for _, f in result]).astype(np.int32),
        vertex_offsets=vertex_offsets,
        face_offsets=face_offsets,
    )
    return result


VIEWS = {
    # name: (screen-right, screen-up, toward-viewer) in body coordinates
    "side": (np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), np.array([0, -1.0, 0])),
}


def _iso_basis() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    toward_viewer = np.array([-0.75, -1.0, 0.75])
    toward_viewer /= np.linalg.norm(toward_viewer)
    right = np.cross(np.array([0, 0, 1.0]), toward_viewer)
    right /= np.linalg.norm(right)
    up = np.cross(toward_viewer, right)
    return right, up, toward_viewer


VIEWS["iso"] = _iso_basis()


def project_scene(render, categories, transforms, view):
    """Screen polygons, colours and depth of every triangle for one pose."""
    right, up, toward = VIEWS[view]
    light = toward + np.array([0, 0, 0.6])
    light /= np.linalg.norm(light)
    polygons, colours, depths = [], [], []
    for (vertices, faces), category in zip(render, categories):
        if len(faces) == 0:
            continue
        points = vertices
        if category in transforms:
            points = apply(transforms[category], points)
        body = points @ CAD_TO_BODY.T / 1000.0
        triangles = body[faces]
        normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        lengths = np.linalg.norm(normals, axis=1)
        valid = lengths > 0
        triangles, normals = triangles[valid], normals[valid] / lengths[valid, None]
        shade = 0.45 + 0.55 * np.abs(normals @ light)
        base = np.array(matplotlib.colors.to_rgb(COLORS[category]))
        colours.append(np.clip(base[None] * shade[:, None] + 0.12 * (1 - shade[:, None]), 0, 1))
        polygons.append(np.stack([triangles @ right, triangles @ up], axis=2))
        depths.append((triangles @ toward).mean(axis=1))
    polygons = np.concatenate(polygons)
    colours = np.concatenate(colours)
    order = np.argsort(np.concatenate(depths))  # far (small toward) first
    return polygons[order], colours[order]


def project_points(points_body: np.ndarray, view: str) -> np.ndarray:
    right, up, _ = VIEWS[view]
    return np.column_stack([points_body @ right, points_body @ up])


def draw_step(render, categories, step: dict, view: str, limits, png_path: Path) -> None:
    polygons, colours = project_scene(render, categories, step["transforms"], view)
    figure, axes = plt.subplots(figsize=(13, 8), dpi=110)
    axes.add_collection(PolyCollection(polygons, facecolors=colours, edgecolors="none", antialiased=False))
    hinge = project_points(step["hinge_body_m"][None], view)[0]
    axes.plot(*hinge, marker="o", ms=11, mfc="white", mec=INK, mew=2, zorder=5)
    axes.annotate("힌지", hinge, xytext=(8, 8), textcoords="offset points", fontsize=10, color=INK)
    for case, marker in (("step", "X"), ("generic_as_steel", "P")):
        cog = project_points(np.array(step["cog_body_m"][case])[None], view)[0]
        axes.plot(*cog, marker=marker, ms=13, mfc="#e2245c", mec="white", mew=1.5, zorder=6,
                  label=f"상부체 무게중심 (경우 {CASE_LABEL[case]})")
    pads = project_points(step["pads_body_m"], view)
    axes.plot(pads[:, 0], pads[:, 1], ls="none", marker="s", ms=8, mfc="#1baf7a", mec=INK, zorder=6,
              label="다리 패드 바닥 중심")
    if view == "iso":
        for name, point in zip(LEG_ORDER, pads):
            axes.annotate(name, point, xytext=(5, -12), textcoords="offset points", fontsize=8)
    handles = [
        Rectangle((0, 0), 1, 1, color=COLORS[ROTATING], label="회전체(마스트 쪽)"),
        Rectangle((0, 0), 1, 1, color=COLORS[LINK_ROD], label="링크: 백스테이(기구학 반영)"),
        Rectangle((0, 0), 1, 1, color=COLORS[LINK_STATIC], label="링크: 붐·붐 실린더(접기 중 고정)"),
        Rectangle((0, 0), 1, 1, color=COLORS[UNRESOLVED], label="호스 가이드 암·실린더: 링크 미반영(고정)"),
        Rectangle((0, 0), 1, 1, color=COLORS[FIXED], label="고정 상부체"),
    ]
    marker_handles, _ = axes.get_legend_handles_labels()
    axes.legend(handles=handles + marker_handles, loc="upper right", fontsize=8, framealpha=0.9)
    axes.set_xlim(*limits[0])
    axes.set_ylim(*limits[1])
    axes.set_aspect("equal")
    if view == "side":
        axes.set_xlabel("x 전방 [m] (= CAD Z)")
        axes.set_ylabel("z 상방 [m] (= CAD Y)")
    else:
        axes.set_xticks([])
        axes.set_yticks([])
        axes.set_xlabel("등각 투영 (후방-우측-상방에서 봄), 축척 일정")
    a, b = step["cog_body_m"]["step"], step["cog_body_m"]["generic_as_steel"]
    axes.set_title(
        f"{step['label']}  θ = {step['theta_deg']:.2f}° (후방 접힘)   "
        f"백스테이 핀 간 {step['backstay_length_mm']:.0f} mm"
        f"{'' if step['backstay_ok'] else ' (스트로크 범위 밖)'}\n"
        f"무게중심 A x={a[0]:.3f} z={a[2]:.3f} m · B x={b[0]:.3f} z={b[2]:.3f} m   "
        f"{'접촉/간섭: ' + step['interference_note'] if step['interference_note'] else '접촉·간섭 없음(메시 검사)'}",
        fontsize=10,
        loc="left",
    )
    axes.grid(True, color="#e0dfda", lw=0.5)
    figure.tight_layout()
    figure.savefig(png_path)
    plt.close(figure)


def scene_limits(render, categories, steps, view) -> tuple:
    lows, highs = [], []
    for step in steps:
        for (vertices, faces), category in zip(render, categories):
            if len(faces) == 0:
                continue
            points = vertices if category not in step["transforms"] else apply(step["transforms"][category], vertices)
            screen = project_points(points @ CAD_TO_BODY.T / 1000.0, view)
            lows.append(screen.min(0))
            highs.append(screen.max(0))
    low, high = np.min(lows, axis=0) - 0.3, np.max(highs, axis=0) + 0.3
    return (low[0], high[0]), (low[1], high[1])


def contact_sheet(paths: list[Path], titles: list[str], out_path: Path, columns: int = 3) -> None:
    rows = math.ceil(len(paths) / columns)
    figure, axes = plt.subplots(rows, columns, figsize=(6.5 * columns, 4.2 * rows), dpi=110)
    for axis in np.ravel(axes):
        axis.axis("off")
    for axis, path, title in zip(np.ravel(axes), paths, titles):
        axis.imshow(plt.imread(path))
        axis.set_title(title, fontsize=10)
    figure.tight_layout()
    figure.savefig(out_path)
    plt.close(figure)


def draw_pose_layout(table, poses: dict, kinematics, legs_body, png_path: Path) -> None:
    """Side-view (x-z) bbox layout of the upright and folded poses."""
    figure, axes_list = plt.subplots(1, 2, figsize=(16, 7.5), dpi=110, sharey=True)
    for axes, (name, pose) in zip(axes_list, poses.items()):
        posed_bounds = []
        for row in table.itertuples():
            if row.volume_used_mm3 <= 0 and row.motion_category == FIXED:
                continue
            corners = np.array(
                [[x, y, z] for x in (row.bbox_min_x_mm, row.bbox_max_x_mm)
                 for y in (row.bbox_min_y_mm, row.bbox_max_y_mm)
                 for z in (row.bbox_min_z_mm, row.bbox_max_z_mm)]
            )
            if row.motion_category in pose["transforms"]:
                corners = apply(pose["transforms"][row.motion_category], corners)
            body = corners @ CAD_TO_BODY.T / 1000
            low, high = body.min(0), body.max(0)
            posed_bounds.append((low, high, row.motion_category))
        for low, high, category in sorted(posed_bounds, key=lambda item: item[2] in MOVING):
            axes.add_patch(Rectangle((low[0], low[2]), high[0] - low[0], high[2] - low[2],
                                     fill=False, lw=0.5, ec=COLORS[category], alpha=0.8))
        hinge = kinematics.hinge @ CAD_TO_BODY.T / 1000
        lower = kinematics.lower @ CAD_TO_BODY.T / 1000
        upper = kinematics.upper_pivot(pose["theta_deg"]) @ CAD_TO_BODY.T / 1000
        axes.plot(*hinge[[0, 2]], "o", ms=10, mfc="white", mec=INK, mew=2, label="마스트 힌지")
        axes.plot([lower[0], upper[0]], [lower[2], upper[2]], "-", color=COLORS[LINK_ROD], lw=3,
                  label="백스테이 핀–핀")
        axes.plot(*lower[[0, 2]], "^", ms=9, color=INK, label="백스테이 하부 피벗(붐)")
        axes.plot(*upper[[0, 2]], "v", ms=9, color=INK, label="백스테이 상부 피벗(마스트)")
        for case, marker in (("step", "X"), ("generic_as_steel", "P")):
            cog = np.array(pose["cog_body_m"][case])
            axes.plot(cog[0], cog[2], marker, ms=13, mfc="#e2245c", mec="white",
                      label=f"무게중심 경우 {CASE_LABEL[case]}")
        axes.plot(legs_body[:, 0], legs_body[:, 2], "s", ms=8, mfc="#1baf7a", mec=INK, label="다리 패드 바닥")
        axes.set_title(f"{name}: θ = {pose['theta_deg']:.1f}°", loc="left")
        axes.set_xlabel("x 전방 [m]")
        axes.set_aspect("equal")
        axes.grid(True, color="#e0dfda", lw=0.5)
        axes.set_xlim(-7.6, 4.8)
        axes.set_ylim(-1.3, 10.8)
    axes_list[0].set_ylabel("z 상방 [m]")
    axes_list[0].legend(loc="upper left", fontsize=8)
    figure.suptitle("마스트 세운 자세 / 눕힌 자세: 부품 bbox 옆 보기 (x-z, 기체 좌표, 원점 = CAD 원점). "
                    "파랑 회전체, 주황 링크, 노랑 호스 가이드(미반영), 회색 고정", fontsize=10)
    figure.tight_layout()
    figure.savefig(png_path)
    plt.close(figure)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def mesh_volume_check(table: pd.DataFrame, meshes) -> dict:
    watertight = [i for i, m in enumerate(meshes) if len(m.faces) and m.is_watertight]
    brep = table["volume_used_mm3"].to_numpy()
    mesh_volume = np.array([abs(meshes[i].volume) for i in watertight])
    brep_volume = brep[watertight]
    used = brep_volume > 0
    relative = np.abs(mesh_volume[used] - brep_volume[used]) / brep_volume[used]
    return {
        "watertight_parts": len(watertight),
        "parts_with_mesh": int(sum(len(m.faces) > 0 for m in meshes)),
        "total_volume_relative_difference": round(
            float(abs(mesh_volume[used].sum() - brep_volume[used].sum()) / brep_volume[used].sum()), 6
        ),
        "per_part_relative_difference_median": round(float(np.median(relative)), 6),
        "per_part_relative_difference_p95": round(float(np.percentile(relative, 95)), 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skip-render", action="store_true")
    parser.add_argument("--reuse-sweep", action="store_true",
                        help="reuse cad/meshes/contact_sweep_records.csv instead of re-running the sweep")
    arguments = parser.parse_args()
    started = time.perf_counter()

    parts = pd.read_csv(CLASSIFIED_CSV, encoding="utf-8-sig")
    faces = pd.read_csv(MAST_FACES_CSV, encoding="utf-8-sig")
    summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    table = classify(parts)

    # Joints and hinge.
    joints = find_joints(faces)
    hinge_joint = pick_joint(joints, "X", {"MAST ASSY:1", "BOOM:1"})
    lower_joint = pick_joint(joints, "X", {"BACKSTAY CYL:1", "BOOM:1"})
    upper_joint = pick_joint(joints, "X", {"BACKSTAY CYL:1", "MAST ASSY:1"})
    hinge = np.array([0.0, *hinge_joint["point_cad_mm"][1:]])
    lower = np.array([0.0, *lower_joint["point_cad_mm"][1:]])
    upper = np.array([0.0, *upper_joint["point_cad_mm"][1:]])
    hinge_axis = hinge_axis_direction(faces, hinge)
    backstay = backstay_geometry(faces, lower, upper)
    kinematics = FoldKinematics(hinge, lower, upper)

    # Mast axis verticality from the rack gears (straight bars along the mast).
    racks = parts[parts["instance_path"].str.contains("MAST ASSY:1 / RACK GEAR")]
    rack_centres = racks[CENTROID_COLUMNS].to_numpy()
    fit = np.polyfit(rack_centres[:, 1], rack_centres[:, 2], 1)
    mast_tilt_deg = math.degrees(math.atan(fit[0]))  # +: top leans forward (+Z)
    theta_flat = round(90.0 + mast_tilt_deg, 2)
    theta_full_retract = kinematics.angle_for_length(backstay["pin_to_pin_min_mm"])

    # Mesh cache (order mapped to the part table).
    mesh_paths, mesh_list = load_meshes()
    by_path = dict(zip(mesh_paths, mesh_list))
    meshes = [by_path[path] for path in table["instance_path"]]
    paths = table["instance_path"].tolist()
    volume_check = mesh_volume_check(table, meshes)

    # Contact sweep (mesh surface distance), continued past horizontal to find the rest.
    sweep = ContactSweep(table, meshes, kinematics)
    angles = sorted(set(np.round(np.arange(0.0, SWEEP_MAX_DEG + 1e-9, SWEEP_STEP_DEG), 3)) | {theta_flat})
    if arguments.reuse_sweep and SWEEP_RECORDS_CSV.exists():
        records = pd.read_csv(SWEEP_RECORDS_CSV)
        sweep.load(records)
    else:
        records = sweep.run(angles)
        records.to_csv(SWEEP_RECORDS_CSV, index=False)
    contacts = summarize_contacts(sweep, records, paths, theta_flat)
    contacts.to_csv(INTERFERENCE_CSV, index=False, encoding="utf-8-sig")
    real = contacts[contacts["status"] == "contact"] if len(contacts) else contacts
    during_fold = real[real["first_contact_theta_deg"] <= theta_flat + 1e-9] if len(real) else real
    first_theta = float(during_fold["first_contact_theta_deg"].min()) if len(during_fold) else None
    rest_index = int(table.index[table["top_assembly"] == "MAST BK:1"][0])
    rest_rows = real[real["other_part"].str.startswith("MAST BK")] if len(real) else real
    rest_theta = float(rest_rows["first_contact_theta_deg"].min()) if len(rest_rows) else None
    rest_at_flat = rest_gap(meshes, table, kinematics.mast(theta_flat), rest_index)
    clearance_at_flat = nearest_at(sweep, records, paths, theta_flat)
    joint_pairs = {frozenset(j) for j in joints["assemblies"] if len(j) == 2}
    exact_rows = exact_checks(ExactClearance(table, kinematics), contacts, clearance_at_flat, paths,
                              theta_flat, joint_pairs)
    touches = [r for r in exact_rows if r.get("exact_first_touch_theta_deg") is not None]
    during_exact = [r["exact_first_touch_theta_deg"] for r in touches
                    if r["exact_first_touch_theta_deg"] <= theta_flat]
    first_theta_exact = min(during_exact) if during_exact else None
    rest_exact = [r["exact_first_touch_theta_deg"] for r in touches if r["other_part"].startswith("MAST BK")]
    rest_theta_exact = min(rest_exact) if rest_exact else None
    first_theta_step = first_theta_exact if first_theta_exact is not None else (
        first_theta if not touches else None)
    contact_pairs = [
        (int(table.index[table["instance_path"].map(short_name) == r.moving_part][0]),
         int(table.index[table["instance_path"].map(short_name) == r.other_part][0]))
        for r in real.itertuples()
    ] if len(real) else []

    # Poses and steps.
    legs = summary["legs"]
    pads_body = np.array([legs[name]["pad_center_body_m"] for name in LEG_ORDER])
    polygon = pads_body[[0, 1, 3, 2], :2]  # FL, FR, RR, RL around the rectangle

    def pose(theta: float, label: str) -> dict:
        transforms = kinematics.transforms(theta)
        properties = superstructure_properties(posed_parts(table, transforms))
        loads = {
            case: leg_loads(pads_body[:, :2], properties[case]["mass_kg"],
                            np.array(properties[case]["cog_body_m"][:2]))
            for case in CASES
        }
        notes = sorted({
            f"{short_name(paths[m]).split('/')[0]}↔{short_name(paths[o]).split('/')[0]}"
            for m, o in contact_pairs if sweep.is_contact((m, o), sweep.distance((m, o), theta))
        })
        length = kinematics.backstay_length(theta)
        return {
            "label": label,
            "theta_deg": theta,
            "transforms": transforms,
            "properties": properties,
            "cog_body_m": {case: properties[case]["cog_body_m"] for case in CASES},
            "loads_N": loads,
            "hinge_body_m": hinge @ CAD_TO_BODY.T / 1000,
            "pads_body_m": pads_body,
            "backstay_length_mm": length,
            "backstay_ok": backstay["pin_to_pin_min_mm"] - 0.5 <= length <= backstay["pin_to_pin_max_mm"] + 0.5,
            "interference_note": ", ".join(notes),
        }

    upright = pose(0.0, "세운 자세")
    folded = pose(theta_flat, "눕힌 자세(수평)")
    step_angles = list(STEP_ANGLES_DEG) + [theta_flat]
    extra = [a for a in (first_theta_step,) if a is not None and 0 < a < theta_flat]
    step_angles = sorted(set(round(a, 2) for a in step_angles + extra))
    steps = []
    for number, theta in enumerate(step_angles):
        label = f"단계 {number:02d}"
        if first_theta_step is not None and abs(theta - round(first_theta_step, 2)) < 1e-6:
            label += " (첫 간섭)"
        if rest_theta is not None and abs(theta - round(rest_theta, 2)) < 1e-6:
            label += " (받침 접촉)"
        if abs(theta - theta_flat) < 1e-6:
            label += " (수평)"
        steps.append(pose(theta, label))

    # Tables.
    STEPS_DIR.mkdir(parents=True, exist_ok=True)
    step_rows = []
    for number, step in enumerate(steps):
        row = {
            "step": number,
            "label": step["label"],
            "theta_deg": round(step["theta_deg"], 2),
            "backstay_pin_to_pin_mm": round(step["backstay_length_mm"], 1),
            "backstay_within_stroke": step["backstay_ok"],
        }
        for case in CASES:
            tag = CASE_LABEL[case]
            properties = step["properties"][case]
            row[f"mass_{tag}_kg"] = properties["mass_kg"]
            for axis, value in zip("xyz", properties["cog_body_m"]):
                row[f"cog_{tag}_{axis}_body_m"] = value
            loads = step["loads_N"][case]
            for name, load in zip(LEG_ORDER, loads):
                row[f"leg_{name}_{tag}_kN"] = round(load / 1000, 2)
                row[f"leg_{name}_{tag}_pct"] = round(100 * load / loads.sum(), 2)
            row[f"cog_{tag}_inside_leg_rectangle"] = point_in_polygon(
                np.array(properties["cog_body_m"][:2]), polygon
            )
        row["interference"] = step["interference_note"]
        step_rows.append(row)
    pd.DataFrame(step_rows).to_csv(STEPS_CSV, index=False, encoding="utf-8-sig")

    part_columns = ["instance_path", "top_assembly", "motion_category", "motion_reason", "confidence",
                    "mass_step_kg", "mass_generic_as_steel_kg", "group", "is_crawler"]
    table[part_columns].to_csv(MAST_PARTS_CSV, index=False, encoding="utf-8-sig")

    # Category masses and sensitivities.
    category_mass = table.groupby("motion_category")[["mass_step_kg", "mass_generic_as_steel_kg"]].sum().round(1)
    drive = table[table["top_assembly"].isin(["0. DRIVE AUGER ASSY:1", "AUGER TOOL:1"])]
    hose = table[table["motion_category"] == UNRESOLVED]
    sensitivity = {}
    for case in CASES:
        total = folded["properties"][case]["mass_kg"]
        sensitivity[case] = {
            "drive_and_tool_mass_kg": round(float(drive[f"mass_{case}_kg"].sum()), 1),
            "cog_shift_per_1m_drive_travel_along_mast_m": round(float(drive[f"mass_{case}_kg"].sum()) / total, 4),
            "hose_guide_mass_kg": round(float(hose[f"mass_{case}_kg"].sum()), 1),
            "cog_shift_if_hose_guide_moves_1m_m": round(float(hose[f"mass_{case}_kg"].sum()) / total, 4),
        }

    def pose_report(step: dict) -> dict:
        report = {"theta_deg": round(step["theta_deg"], 3)}
        for case in CASES:
            loads = step["loads_N"][case]
            report[case] = {
                **step["properties"][case],
                "tensor_checks": tensor_checks(step["properties"][case]),
                "leg_loads_kN": {n: round(v / 1000, 2) for n, v in zip(LEG_ORDER, loads)},
                "leg_loads_pct": {n: round(100 * v / loads.sum(), 2) for n, v in zip(LEG_ORDER, loads)},
                "cog_inside_leg_rectangle": point_in_polygon(np.array(step["properties"][case]["cog_body_m"][:2]), polygon),
            }
        return report

    reference = summary["mass_properties"]
    reproduction = {
        case: abs(upright["properties"][case]["mass_kg"] - reference[case]["superstructure"]["mass_kg"])
        / reference[case]["superstructure"]["mass_kg"]
        for case in CASES
    }
    output = {
        "frames": "CAD root frame mm (Y up); body x=Z_cad, y=X_cad, z=Y_cad, origin = CAD origin",
        "fold_angle_convention": "theta > 0 folds the mast top rearward: rotation of -theta about CAD +X "
                                 "(= body +y) through the hinge axis",
        "joints_between_assemblies": joints.to_dict("records"),
        "hinge": {
            "point_cad_mm": hinge.round(1).tolist(),
            "point_body_m": (hinge @ CAD_TO_BODY.T / 1000).round(4).tolist(),
            "axis_cad": hinge_axis.round(6).tolist(),
            "axis_body": (CAD_TO_BODY @ hinge_axis).round(6).tolist(),
            "evidence": hinge_joint,
        },
        "backstay": {
            **backstay,
            "lower_pivot_body_m": (lower @ CAD_TO_BODY.T / 1000).round(4).tolist(),
            "upper_pivot_body_m": (upper @ CAD_TO_BODY.T / 1000).round(4).tolist(),
            "pin_to_pin_at_flat_mm": round(kinematics.backstay_length(theta_flat), 2),
            "upper_pivot_at_flat_cad_mm": kinematics.upper_pivot(theta_flat).round(1).tolist(),
            "theta_at_full_retraction_deg": round(theta_full_retract, 3),
            "motion": "retracts while the mast folds rearward",
        },
        "mast_tilt_from_vertical_deg": round(mast_tilt_deg, 5),
        "theta_flat_deg": round(theta_flat, 4),
        "rest_bracket": {"part": "MAST BK:1", "mesh_first_contact_theta_deg": rest_theta,
                         "exact_first_touch_theta_deg": rest_theta_exact, **rest_at_flat},
        "first_contact_during_fold_theta_deg": {"mesh": first_theta, "exact_brep": first_theta_exact},
        "contact_settings": {
            "mesh_linear_deflection_mm": json.loads(MESH_INDEX_JSON.read_text(encoding="utf-8"))["linear_deflection_mm"],
            "contact_distance_mm": CONTACT_DISTANCE_MM,
            "sample_spacing_mm": SAMPLE_SPACING_MM,
            "joint_exclusion_radius_mm": JOINT_CUT_RADIUS_MM,
            "sweep_step_deg": SWEEP_STEP_DEG,
            "sweep_max_deg": SWEEP_MAX_DEG,
            "method": "surface samples of the moving part vs KD-tree of the other part, exact closest point for the nearest; pairs touching at 0 deg excluded",
        },
        "contact_pairs": contacts.to_dict("records") if len(contacts) else [],
        "clearance_at_flat_nearest": clearance_at_flat,
        "exact_brep_checks": exact_rows,
        "category_mass_kg": category_mass.to_dict("index"),
        "mass_properties_superstructure": {"upright": pose_report(upright), "folded_flat": pose_report(folded)},
        "upright_reproduces_cad_summary_rel_diff": reproduction,
        "sensitivity": sensitivity,
        "mesh_volume_check": volume_check,
        "leg_load_model": "rigid body on four equal vertical springs, rigid floor; F_i = a + b x_i + c y_i",
    }
    MAST_SUMMARY_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(f"analysis done in {time.perf_counter() - started:.0f} s", flush=True)

    draw_pose_layout(table, {"세운 자세": upright, "눕힌 자세(수평)": folded}, kinematics, pads_body, POSES_PNG)
    if arguments.skip_render:
        return

    render = render_meshes(meshes)
    categories = table["motion_category"].tolist()
    side_paths, iso_paths, titles = [], [], []
    limits = {view: scene_limits(render, categories, steps, view) for view in ("side", "iso")}
    for number, step in enumerate(steps):
        theta = step["theta_deg"]
        angle_text = f"{theta:03.0f}" if abs(theta - round(theta)) < 1e-6 else f"{theta:06.2f}".replace(".", "p")
        stem = f"step_{number:02d}_{angle_text}deg"
        side_path = STEPS_DIR / f"{stem}.png"
        iso_path = STEPS_DIR / f"{stem}_iso.png"
        draw_step(render, categories, step, "side", limits["side"], side_path)
        draw_step(render, categories, step, "iso", limits["iso"], iso_path)
        side_paths.append(side_path)
        iso_paths.append(iso_path)
        titles.append(f"{step['label']}  θ={step['theta_deg']:.2f}°")
        print(f"rendered {stem}", flush=True)
    contact_sheet(side_paths, titles, STEPS_DIR / "contact_sheet.png")
    contact_sheet(iso_paths, titles, STEPS_DIR / "contact_sheet_iso.png")
    from PIL import Image

    frames = [Image.open(path).convert("P", palette=Image.ADAPTIVE) for path in side_paths]
    frames[0].save(STEPS_DIR / "fold_side.gif", save_all=True, append_images=frames[1:], duration=900, loop=0)
    print(f"done in {time.perf_counter() - started:.0f} s")


if __name__ == "__main__":
    main()
