"""Build simplified visual and collision shapes for the Chrono model (roadmap C8).

Inputs (caches only, the STEP file is not read):
    01_cad/01_parts/parts_classified.csv     part table (B-rep volume and bbox per instance)
    01_cad/05_meshes/parts_mesh.npz          per-instance BRepMesh tessellation (3 mm / 0.5 rad)
    01_cad/02_legs/legs/*_10_1.brep          leg moving part (rod + piston + pad), world placed
    01_cad/06_brep/derived/crawler/crawler_collision.json   track B-rep volume / bbox / box
    02_params/rexome33.yaml                  retracted offsets, pad values (comparison only)

Outputs (01_cad/09_sim_shapes/):
    visual/<group>_lowres.obj       simplified visual meshes of the superstructure groups
                                    (deck, mast, auger, crawler) - git ignored (*_lowres.obj)
    visual/barrel_<leg>.obj         leg barrel (superstructure)
    visual/rod_<leg>.obj            rod + piston + boss (leg moving part above the pad split)
    visual/pad_<leg>_cad.obj        pad plate + 4 gussets (B-rep tessellation)
    visual/pad_<leg>_simple.obj     chamfered octagon plate built from the B-rep bottom face
    visual/upper_roller_<side>.obj  upper (carrier) roller; visual/crawler_no_upper_rollers_lowres.obj
    collision/*.obj                 collision candidates (convex hulls, CoACD / V-HACD pieces;
                                    one OBJ object ``o piece_<k>`` per convex piece)
    sim_shapes.json                 index: frame, attachment rules, statistics, provenance
    work/*.npz                      intermediate meshes (git ignored by *.npz)

Frame of every OBJ: machine body frame (x forward = +Z_cad, y left = +X_cad, z up = +Y_cad),
origin = CAD origin, metres, CAD pose; legs in the **retracted** state (CAD pose +
``legs.<leg>.retracted_offset_from_cad_m`` along +z), auger (drive + tool) at the CAD
position (travel 0; the loader adds ``superstructure.auger_travel_m``). Loader:
``03_src/outrigger_sim/chrono/sim_shapes.py``.

Stages (default all): ``meshes`` (superstructure groups), ``legs`` (rods, pads), ``hulls``,
``decompose`` (CoACD / V-HACD in child processes), ``upper_rollers`` (crawler carrier rollers from
``derived/crawler/parts/upper_roller_*.bbrep``: visual OBJ, hull, primitive cylinders, crawler visual
without them), ``index``.

CPU: the process and its children run on the E-cores (logical processors 16-27) at
below-normal priority unless ``--cpu os``; ``--cpu pcore`` pins to the P-cores (logical 0-15).

Usage (project root, Chrono-dev python):
    python -I 04_scripts/00_cad/build_sim_shapes.py [--stage NAME ...] [--workers 2] [--cpu ecore|pcore|os]

Options for replaced leg shapes (REXOME35 cylinders, 00_docs/00_cad/cad_cylinder_vs_drawing.md; defaults keep the
CAD sources and 01_cad/09_sim_shapes/):
    --leg-source JSON   per-leg B-rep overrides {"RL": {"moving": path, "barrel": path}, ...} (paths absolute or
                        relative to the project root). Same convention as 01_cad/02_legs/legs/*.brep: CAD frame mm,
                        CAD pose (retracted - legs.<leg>.retracted_offset_from_cad_m). "moving" replaces the rod +
                        piston + pad solid 10 (split at pad bottom + 25 mm as before; every piece above the plane
                        except the largest goes to the pad, e.g. the socket housing of a ball-joint pad); "barrel"
                        replaces the parts_mesh.npz tessellation of group barrel_<leg> by a B-rep tessellation.
                        Cache: 01_cad/02_legs/rexome35/ (moving_<leg>.brep, barrel_<leg>.brep).
    --out-dir DIR       write visual/, collision/, work/ and sim_shapes.json under DIR instead of 01_cad/09_sim_shapes
                        (trial runs, e.g. in a scratch folder)
    --groups NAME ...   stage ``meshes`` only for these groups (e.g. barrel_RL barrel_RR); results merge into the state
    --hull-only KEY ... stage ``hulls`` only for these inputs (e.g. rod_RL rod_RR); results merge into the state
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cad_common import CAD_DIR, LEGS_DIR, PARTS_DIR, PROJECT_ROOT  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT / "03_src"))

OUT_DIR = CAD_DIR / "09_sim_shapes"
VISUAL_DIR = OUT_DIR / "visual"
COLLISION_DIR = OUT_DIR / "collision"
WORK_DIR = OUT_DIR / "work"
INDEX_JSON = OUT_DIR / "sim_shapes.json"
CLASSIFIED_CSV = PARTS_DIR / "parts_classified.csv"
MESH_NPZ = CAD_DIR / "05_meshes" / "parts_mesh.npz"
MESH_INDEX_JSON = CAD_DIR / "05_meshes" / "index.json"
CRAWLER_COLLISION_JSON = CAD_DIR / "06_brep" / "derived" / "crawler" / "crawler_collision.json"
PARAMS_YAML = PROJECT_ROOT / "02_params" / "rexome33.yaml"
UPPER_ROLLERS_CSV = CAD_DIR / "06_brep" / "derived" / "crawler" / "crawler_upper_rollers.csv"
UPPER_ROLLER_LINEAR_MM = 0.5
UPPER_ROLLER_ANGULAR_RAD = 0.2
UPPER_ROLLER_BBOX_MARGIN_MM = 2.0  # crawler visual components inside the roller bbox + this ...
UPPER_ROLLER_DUPLICATE_DIST_MM = 5.0  # ... and with every vertex within this of the roller mesh = duplicates

LEG_ORDER = ("FL", "FR", "RL", "RR")
ROD_PAD_BREP = {
    "FL": "FRONT_JACK_CYL_1___10_1.brep",
    "FR": "FRONT_JACK_CYL_2___10_1.brep",
    "RL": "REAR_JACK_CYL_1___10_1.brep",
    "RR": "REAR_JACK_CYL_2___10_1.brep",
}
CAD_TO_BODY = np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])  # body <- CAD
MM = 1e-3
E_CORES = list(range(16, 28))
P_CORES = list(range(0, 16))

# --- grouping of the superstructure (top assemblies, parts_classified.csv) ------------------
MAST_TOPS = frozenset({
    "MAST ASSY:1", "TOPSHEAVE(조립) ASSY:1", "LOWER GUIDE_ASSY:1", "윈치:1", "BACKSTAY CYL:1",
    "BOOM:1", "BOOM CYL:1", "Hose guide arm:1", "Hose guide CYL:1",
})
AUGER_TOPS = frozenset({"0. DRIVE AUGER ASSY:1", "AUGER TOOL:1"})
CRAWLER_TOP = "REX33-REX33 - 5J286105:1"
SUPERSTRUCTURE_GROUPS = ("deck", "mast", "auger", "crawler")
GROUP_COLORS = {
    "deck": (0.66, 0.65, 0.63), "mast": (0.80, 0.55, 0.20), "auger": (0.16, 0.47, 0.84),
    "crawler": (0.30, 0.30, 0.32), "barrel": (0.85, 0.75, 0.25), "rod": (0.62, 0.64, 0.68),
    "pad": (0.11, 0.69, 0.48), "upper_roller": (0.89, 0.42, 0.15),
}
# Crawler components are assigned to a track when their whole bbox lies outside |X_cad| = 690 mm (tracks span
# |X_cad| 690.6 ... 1366.0 mm, crawler_collision.json); the rest is the centre frame.
TRACK_SPLIT_X_MM = 690.0

# --- visual decimation (per connected component of the 3 mm tessellation) -------------------
DROP_DIAG_MM = 40.0  # components smaller than this (bolts, nuts, washers) are dropped
Q_REDUCTIONS = (0.995, 0.99, 0.98, 0.95, 0.9, 0.8, 0.65, 0.5, 0.3)
Q_VOL_TOL = 0.05  # accepted relative volume change of a component (about its own centroid)
Q_BBOX_TOL_MM = 10.0  # accepted bbox change of a component
CLUSTER_MIN_FACES = 2000  # fallback vertex clustering only for components above this size
CLUSTER_CELLS_MM = (20.0, 10.0, 5.0)  # coarsest first

# --- legs ---------------------------------------------------------------------------------------
PAD_SPLIT_HEIGHT_MM = 25.0  # = YAML legs.<leg>.pad_body.split_plane_above_pad_bottom_m
LEG_LINEAR_DEFLECTION_MM = 0.2
LEG_ANGULAR_DEFLECTION_RAD = 0.2
LEG_DECIMATE_VOL_TOL = 0.002
LONG_EDGE_MIN_M = 0.2

# --- convex decomposition targets: name -> (input mesh key, tool, settings) -----------------
COACD_COMMON = {"max_ch_vertex": 64, "seed": 0, "preprocess_mode": "auto"}
DECOMPOSE_TARGETS: dict[str, dict] = {
    **{f"pad_{leg}_coacd": {"input": f"pad_cad_{leg}", "tool": "coacd",
                            "settings": {"threshold": 0.02, "preprocess_resolution": 100}}
       for leg in LEG_ORDER},
    **{f"moving_{leg}_coacd": {"input": f"moving_{leg}", "tool": "coacd",
                               "settings": {"threshold": 0.03, "preprocess_resolution": 100}}
       for leg in LEG_ORDER},
    "track_L_coacd": {"input": "track_L", "tool": "coacd",
                      "settings": {"threshold": 0.05, "max_convex_hull": 32, "preprocess_resolution": 60}},
    "track_R_coacd": {"input": "track_R", "tool": "coacd",
                      "settings": {"threshold": 0.05, "max_convex_hull": 32, "preprocess_resolution": 60}},
    "track_L_vhacd": {"input": "track_L", "tool": "vhacd",
                      "settings": {"maxConvexHulls": 32, "maxNumVerticesPerCH": 64, "resolution": 400000}},
    "pad_FL_vhacd": {"input": "pad_cad_FL", "tool": "vhacd",
                     "settings": {"maxConvexHulls": 16, "maxNumVerticesPerCH": 64, "resolution": 400000}},
    "deck_coacd": {"input": "deck", "tool": "coacd",
                   "settings": {"threshold": 0.08, "max_convex_hull": 32, "preprocess_resolution": 60}},
    "mast_coacd": {"input": "mast", "tool": "coacd",
                   "settings": {"threshold": 0.08, "max_convex_hull": 32, "preprocess_resolution": 60}},
    "auger_coacd": {"input": "auger", "tool": "coacd",
                    "settings": {"threshold": 0.08, "max_convex_hull": 32, "preprocess_resolution": 60}},
}
HULL_TARGETS = ("track_L", "track_R", "deck", "mast", "auger", *[f"rod_{leg}" for leg in LEG_ORDER])


# ============================================================================================
# helpers
# ============================================================================================
def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:  # --out-dir / --leg-source outside the project
        return path.resolve().as_posix()


# per-leg B-rep overrides (--leg-source); empty = CAD sources
LEG_SOURCE: dict[str, dict[str, Path]] = {}


def set_output_dir(out_dir: Path) -> None:
    """Redirect every output path (--out-dir)."""
    global OUT_DIR, VISUAL_DIR, COLLISION_DIR, WORK_DIR, INDEX_JSON, STATE_JSON
    OUT_DIR = Path(out_dir).resolve()
    VISUAL_DIR, COLLISION_DIR, WORK_DIR = OUT_DIR / "visual", OUT_DIR / "collision", OUT_DIR / "work"
    INDEX_JSON = OUT_DIR / "sim_shapes.json"
    STATE_JSON = WORK_DIR / "state.json"


def load_leg_source(path: Path) -> dict[str, dict[str, Path]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for leg_name, entry in raw.items():
        if leg_name not in LEG_ORDER:
            raise SystemExit(f"--leg-source: unknown leg {leg_name}")
        out[leg_name] = {}
        for kind, value in entry.items():
            if kind not in ("moving", "barrel"):
                raise SystemExit(f"--leg-source {leg_name}: unknown key {kind}")
            p = Path(value)
            p = p if p.is_absolute() else PROJECT_ROOT / p
            if not p.exists():
                raise SystemExit(f"--leg-source {leg_name}.{kind}: {p} missing")
            out[leg_name][kind] = p
    return out


def moving_brep_path(leg_name: str) -> Path:
    return LEG_SOURCE.get(leg_name, {}).get("moving", LEGS_DIR / "legs" / ROD_PAD_BREP[leg_name])


def source_record(path: Path) -> dict:
    return {"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def place_cpu(mode: str) -> dict:
    """Pin this process: ``ecore`` = E-cores at below-normal priority, ``pcore`` = P-cores
    (logical 0-15) at normal priority, ``os`` = no placement."""
    info = {"mode": mode}
    if mode == "os":
        return info
    try:
        import psutil

        process = psutil.Process()
        if mode == "pcore":
            process.cpu_affinity(P_CORES)
            info.update(affinity=P_CORES, priority="normal")
            return info
        process.cpu_affinity(E_CORES)
        process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        info.update(affinity=E_CORES, priority="below_normal")
    except Exception as error:  # noqa: BLE001 - placement is optional
        info["error"] = repr(error)
    return info


def signed_volume(vertices: np.ndarray, faces: np.ndarray, origin=None) -> float:
    """Signed enclosed volume (divergence theorem); ``origin`` defaults to the coordinate origin."""
    if len(faces) == 0:
        return 0.0
    v = np.asarray(vertices, float)
    if origin is not None:
        v = v - origin
    a, b, c = v[faces[:, 0]], v[faces[:, 1]], v[faces[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


def used_bbox(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    used = np.asarray(vertices)[np.unique(faces)]
    return np.array([used.min(0), used.max(0)])


def cad_to_body_m(vertices_mm: np.ndarray) -> np.ndarray:
    return (np.asarray(vertices_mm, float) @ CAD_TO_BODY.T) * MM


def bbox_cad_to_body_m(bbox_mm: np.ndarray) -> np.ndarray:
    corners = cad_to_body_m(np.asarray(bbox_mm, float))
    return np.array([corners.min(0), corners.max(0)])


def write_obj(path: Path, pieces: list[tuple[np.ndarray, np.ndarray]], header: list[str]) -> dict:
    """Write one OBJ with an ``o piece_<k>`` object per (vertices, faces) piece (metres)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    offset = 1
    n_v = n_f = 0
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for line in header:
            handle.write(f"# {line}\n")
        for k, (v, f) in enumerate(pieces):
            if len(pieces) > 1:
                handle.write(f"o piece_{k}\n")
            handle.write("".join(f"v {x:.6f} {y:.6f} {z:.6f}\n" for x, y, z in np.asarray(v, float)))
            ff = np.asarray(f, np.int64) + offset
            handle.write("".join(f"f {a} {b} {c}\n" for a, b, c in ff))
            offset += len(v)
            n_v += len(v)
            n_f += len(f)
    os.replace(tmp, path)
    return {"file": rel(path), "bytes": path.stat().st_size, "vertices": n_v, "faces": n_f,
            "pieces": len(pieces)}


def read_obj(path: Path) -> list[tuple[np.ndarray, np.ndarray]]:
    """Pieces (``o`` objects) of an OBJ written by :func:`write_obj` (global vertex indices)."""
    pieces, vertices, faces = [], [], []
    start = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("v "):
            vertices.append([float(t) for t in line.split()[1:4]])
        elif line.startswith("f "):
            faces.append([int(t.split("/")[0]) - 1 for t in line.split()[1:4]])
        elif line.startswith("o ") and (faces or vertices[start:]):
            if faces:
                pieces.append((np.array(vertices[start:]), np.array(faces) - start))
            start, faces = len(vertices), []
    if faces:
        pieces.append((np.array(vertices[start:]), np.array(faces) - start))
    return pieces


def mesh_stats(vertices: np.ndarray, faces: np.ndarray, brep_volume: float | None,
               brep_bbox: np.ndarray | None, origin=None) -> dict:
    """Faces, volume (signed, about ``origin``, default global origin) and bbox vs the B-rep."""
    vol = signed_volume(vertices, faces, origin)
    box = used_bbox(vertices, faces) if len(faces) else np.zeros((2, 3))
    out = {"faces": int(len(faces)), "vertices": int(len(vertices)), "volume": vol,
           "bbox_min": box[0].tolist(), "bbox_max": box[1].tolist()}
    if brep_volume:
        out["volume_rel_to_brep"] = vol / brep_volume - 1.0
    if brep_bbox is not None:
        diff = np.abs(box - np.asarray(brep_bbox))
        out["bbox_abs_diff"] = float(diff.max())
        out["bbox_abs_diff_xyz"] = diff.max(0).tolist()
    return out


# ============================================================================================
# stage: superstructure meshes
# ============================================================================================
def group_of(row) -> str:
    if row.leg:
        return f"{'barrel' if row.group == 'leg_barrel' else 'rodpad'}_{row.leg}"
    if row.top_assembly in MAST_TOPS:
        return "mast"
    if row.top_assembly in AUGER_TOPS:
        return "auger"
    if row.top_assembly == CRAWLER_TOP:
        return "crawler"
    return "deck"


def load_parts_and_meshes():
    import trimesh

    index = json.loads(MESH_INDEX_JSON.read_text(encoding="utf-8"))
    data = np.load(MESH_NPZ)
    vertices, faces = data["vertices"], data["faces"]
    vo, fo = data["vertex_offsets"], data["face_offsets"]
    by_path = {}
    for i, path in enumerate(index["instance_paths"]):
        v = vertices[vo[i] : vo[i + 1]].astype(np.float64)
        f = faces[fo[i] : fo[i + 1]].astype(np.int64)
        by_path[path] = (v, f)
    parts = pd.read_csv(CLASSIFIED_CSV, encoding="utf-8-sig")
    parts["leg"] = parts["leg"].fillna("")
    if set(parts.instance_path) != set(by_path):
        raise SystemExit("parts_classified.csv and parts_mesh.npz list different instances")
    parts["sim_group"] = [group_of(row) for row in parts.itertuples()]
    meshes = []
    for path in parts.instance_path:
        v, f = by_path[path]
        mesh = trimesh.Trimesh(v, f, process=False)
        if len(f):
            mesh.merge_vertices()
        meshes.append(mesh)
    mesh_info = {k: index[k] for k in ("mesher", "linear_deflection_mm", "angular_deflection_rad")}
    return parts, meshes, mesh_info


def components(mesh) -> list[np.ndarray]:
    import trimesh

    if len(mesh.faces) == 0:
        return []
    labels = trimesh.graph.connected_component_labels(mesh.face_adjacency, node_count=len(mesh.faces))
    order = np.argsort(labels, kind="stable")
    cuts = np.flatnonzero(np.diff(labels[order])) + 1
    return np.split(order, cuts)


def compact(vertices: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    used, inverse = np.unique(faces, return_inverse=True)
    return np.asarray(vertices)[used], inverse.reshape(-1, 3)


def cluster_vertices(vertices: np.ndarray, faces: np.ndarray, cell: float):
    """Vertex clustering (render_S2_gifs.cluster_mesh): snap to a grid, average, drop degenerates."""
    key = np.floor(vertices / cell).astype(np.int64)
    unique, inverse = np.unique(key, axis=0, return_inverse=True)
    inverse = inverse.ravel()
    sums = np.zeros((len(unique), 3))
    np.add.at(sums, inverse, vertices)
    new_vertices = sums / np.bincount(inverse, minlength=len(unique))[:, None]
    new_faces = inverse[faces]
    ok = ((new_faces[:, 0] != new_faces[:, 1]) & (new_faces[:, 1] != new_faces[:, 2])
          & (new_faces[:, 0] != new_faces[:, 2]))
    new_faces = new_faces[ok]
    if len(new_faces):
        _, first = np.unique(np.sort(new_faces, axis=1), axis=0, return_index=True)
        new_faces = new_faces[np.sort(first)]
    return compact(new_vertices, new_faces) if len(new_faces) else (new_vertices[:0], new_faces)


def decimate_component(v: np.ndarray, f: np.ndarray) -> tuple[np.ndarray, np.ndarray, str]:
    """Most aggressive quadric reduction within the volume / bbox tolerances, else clustering."""
    import fast_simplification

    centre = v.mean(0)
    vol0 = signed_volume(v, f, centre)
    box0 = used_bbox(v, f)
    if len(f) <= 64:
        return v, f, "kept"
    for reduction in Q_REDUCTIONS:
        v2, f2 = fast_simplification.simplify(v.astype(np.float32), f.astype(np.int32),
                                              target_reduction=reduction, agg=7)
        if len(f2) == 0:
            continue
        v2 = np.asarray(v2, float)
        f2 = np.asarray(f2, np.int64)
        vol = signed_volume(v2, f2, centre)
        if (abs(vol - vol0) <= Q_VOL_TOL * max(abs(vol0), 1e-12)
                and np.abs(used_bbox(v2, f2) - box0).max() <= Q_BBOX_TOL_MM):
            return v2, f2, f"quadric_{reduction:g}"
    if len(f) >= CLUSTER_MIN_FACES:
        for cell in CLUSTER_CELLS_MM:
            v3, f3 = cluster_vertices(v, f, cell)
            if (len(f3) and np.abs(used_bbox(v3, f3) - box0).max() <= Q_BBOX_TOL_MM
                    and abs(signed_volume(v3, f3, centre) - vol0) <= Q_VOL_TOL * max(abs(vol0), 1e-12)):
                return v3, f3, "cluster"
    return v, f, "kept"


def barrel_from_brep(leg_name: str, path: Path) -> dict:
    """Group record of barrel_<leg> from a B-rep override (--leg-source): tessellation at the leg deflections,
    closed-mesh decimation within LEG_DECIMATE_VOL_TOL; same record keys as the parts-mesh path."""
    started = time.perf_counter()
    shape = read_ascii_brep(path)
    p = volume_properties(shape)
    v_mm, f, skipped = tessellate(shape, LEG_LINEAR_DEFLECTION_MM, LEG_ANGULAR_DEFLECTION_RAD)
    v2, f2, reduction = decimate_closed(v_mm, f, LEG_DECIMATE_VOL_TOL)
    brep_volume_m3 = p["volume_mm3"] * MM**3
    brep_bbox_body = bbox_cad_to_body_m(np.array(p["bbox_mm"]))
    body_v = cad_to_body_m(v2)
    name = f"barrel_{leg_name}"
    record = {
        "parts": 1, "brep_volume_m3": brep_volume_m3, "brep_bbox_body_m": brep_bbox_body.tolist(),
        "source_mesh": mesh_stats(cad_to_body_m(v_mm), f, brep_volume_m3, brep_bbox_body),
        "visual_mesh": mesh_stats(body_v, f2, brep_volume_m3, brep_bbox_body),
        "components": 1, "component_methods": {f"brep_override_decimate_{reduction:g}": 1},
        "dropped_small_components": {"components": 0, "faces": 0},
        "brep_override": {**source_record(path), "valid": p["valid"],
                          "tessellation": {"linear_deflection_mm": LEG_LINEAR_DEFLECTION_MM,
                                           "angular_deflection_rad": LEG_ANGULAR_DEFLECTION_RAD,
                                           "faces": int(len(f)), "skipped_faces": skipped}},
    }
    header = [f"C8 visual mesh '{name}' (build_sim_shapes.py, B-rep override {rel(path)})",
              "frame: machine body axes (x fwd, y left, z up), origin CAD origin, metres, CAD pose"]
    record["obj"] = write_obj(VISUAL_DIR / f"{name}.obj", [(body_v, f2)], header)
    np.savez_compressed(WORK_DIR / f"{name}.npz", vertices=body_v, faces=f2)
    record["time_s"] = time.perf_counter() - started
    log(f"meshes {name}: B-rep override {rel(path)}, {len(f)} -> {len(f2)} faces, "
        f"vol {record['visual_mesh']['volume_rel_to_brep']:+.4f}")
    return record


def stage_meshes(state: dict, only_groups: list[str] | None = None) -> None:
    names = [*SUPERSTRUCTURE_GROUPS, *[f"barrel_{leg}" for leg in LEG_ORDER]]
    if only_groups:
        unknown = sorted(set(only_groups) - set(names))
        if unknown:
            raise SystemExit(f"--groups: unknown {unknown}")
        names = [n for n in names if n in only_groups]
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    groups = {}
    override = {n: LEG_SOURCE[n[7:]]["barrel"] for n in names
                if n.startswith("barrel_") and "barrel" in LEG_SOURCE.get(n[7:], {})}
    for name, path in override.items():
        groups[name] = barrel_from_brep(name[7:], path)
    names = [n for n in names if n not in override]
    if names:
        parts, meshes, mesh_info = load_parts_and_meshes()
        state["mesh_source"] = mesh_info
        crawler_collision = json.loads(CRAWLER_COLLISION_JSON.read_text(encoding="utf-8"))
    for name in names:
        started = time.perf_counter()
        sub = parts[parts.sim_group == name]
        brep_volume_mm3 = float(sub.volume_mm3.sum())
        brep_bbox_mm = np.array([[sub.bbox_min_x_mm.min(), sub.bbox_min_y_mm.min(), sub.bbox_min_z_mm.min()],
                                 [sub.bbox_max_x_mm.max(), sub.bbox_max_y_mm.max(), sub.bbox_max_z_mm.max()]])
        src_v, src_f, out_v, out_f = [], [], [], []
        track_pieces = {"L": [], "R": [], "C": []}
        methods: dict[str, int] = {}
        dropped = {"components": 0, "faces": 0}
        n_src_v = n_out_v = 0
        for i in sub.index:
            mesh = meshes[i]
            for comp in components(mesh):
                v, f = compact(mesh.vertices, mesh.faces[comp])
                src_v.append(v)
                src_f.append(f + n_src_v)
                n_src_v += len(v)
                box = used_bbox(v, f)
                if np.linalg.norm(box[1] - box[0]) < DROP_DIAG_MM:
                    dropped["components"] += 1
                    dropped["faces"] += len(f)
                    methods["dropped"] = methods.get("dropped", 0) + 1
                    continue
                v2, f2, method = decimate_component(v, f)
                methods[method.split("_")[0]] = methods.get(method.split("_")[0], 0) + 1
                out_v.append(v2)
                out_f.append(f2 + n_out_v)
                n_out_v += len(v2)
                if name == "crawler":
                    side = ("L" if box[0, 0] > TRACK_SPLIT_X_MM else "R" if box[1, 0] < -TRACK_SPLIT_X_MM
                            else "C")
                    track_pieces[side].append((v, f, v2, f2))
        sv, sf = np.vstack(src_v), np.vstack(src_f)
        ov, of = np.vstack(out_v), np.vstack(out_f)
        body_v = cad_to_body_m(ov)
        brep_bbox_body = bbox_cad_to_body_m(brep_bbox_mm)
        record = {
            "parts": int(len(sub)),
            "brep_volume_m3": brep_volume_mm3 * MM**3,
            "brep_bbox_body_m": brep_bbox_body.tolist(),
            "source_mesh": mesh_stats(cad_to_body_m(sv), sf, brep_volume_mm3 * MM**3, brep_bbox_body),
            "visual_mesh": mesh_stats(body_v, of, brep_volume_mm3 * MM**3, brep_bbox_body),
            "components": int(sum(methods.values())),
            "component_methods": methods,
            "dropped_small_components": dropped,
            "time_s": None,
        }
        file_name = f"{name}_lowres.obj" if name in SUPERSTRUCTURE_GROUPS else f"{name}.obj"
        header = [f"C8 visual mesh '{name}' (build_sim_shapes.py)",
                  "frame: machine body axes (x fwd, y left, z up), origin CAD origin, metres, CAD pose"]
        record["obj"] = write_obj(VISUAL_DIR / file_name, [(body_v, of)], header)
        np.savez_compressed(WORK_DIR / f"{name}.npz", vertices=body_v, faces=of)
        if name == "crawler":
            record["tracks"] = {}
            for side in ("L", "R", "C"):
                items = track_pieces[side]
                if not items:
                    continue
                n1 = n2 = 0
                a_v, a_f, b_v, b_f = [], [], [], []
                for v, f, v2, f2 in items:
                    a_v.append(v), a_f.append(f + n1)
                    b_v.append(v2), b_f.append(f2 + n2)
                    n1 += len(v)
                    n2 += len(v2)
                av, af = cad_to_body_m(np.vstack(a_v)), np.vstack(a_f)
                bv, bf = cad_to_body_m(np.vstack(b_v)), np.vstack(b_f)
                ref = crawler_collision["groups"].get({"L": "left", "R": "right", "C": "center"}[side])
                ref_vol = ref["brep_volume_mm3"] * MM**3 if ref else None
                ref_box = (bbox_cad_to_body_m(np.array([ref["brep_bbox"]["min_mm"], ref["brep_bbox"]["max_mm"]]))
                           if ref else None)
                record["tracks"][side] = {
                    "source_mesh": mesh_stats(av, af, ref_vol, ref_box),
                    "visual_mesh": mesh_stats(bv, bf, ref_vol, ref_box),
                    "brep_volume_m3": ref_vol,
                    "brep_bbox_body_m": ref_box.tolist() if ref_box is not None else None,
                    "brep_source": rel(CRAWLER_COLLISION_JSON),
                }
                np.savez_compressed(WORK_DIR / f"track_{side}.npz", vertices=bv, faces=bf)
        record["time_s"] = time.perf_counter() - started
        groups[name] = record
        log(f"meshes {name}: {record['source_mesh']['faces']} -> {record['visual_mesh']['faces']} faces, "
            f"vol {record['visual_mesh']['volume_rel_to_brep']:+.4f}, {record['time_s']:.0f} s")
    if only_groups:
        state.setdefault("groups", {}).update(groups)
    else:
        state["groups"] = groups


# ============================================================================================
# stage: legs (rod, pad) from the leg B-rep
# ============================================================================================
def read_ascii_brep(path: Path):
    from OCC.Core.BRep import BRep_Builder
    from OCC.Core.BRepTools import breptools
    from OCC.Core.TopoDS import TopoDS_Shape

    shape = TopoDS_Shape()
    if not breptools.Read(shape, str(path), BRep_Builder()):
        raise SystemExit(f"cannot read {path}")
    return shape


def volume_properties(shape) -> dict:
    """Unit-density volume properties (CAD frame, mm): volume, centroid, inertia about centroid."""
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.BRepCheck import BRepCheck_Analyzer
    from OCC.Core.BRepGProp import brepgprop
    from OCC.Core.GProp import GProp_GProps

    props = GProp_GProps()
    brepgprop.VolumeProperties(shape, props)
    c = props.CentreOfMass()
    m = props.MatrixOfInertia()
    box = Bnd_Box()
    brepbndlib.AddOptimal(shape, box, False, False)
    return {"volume_mm3": props.Mass(), "centroid_mm": [c.X(), c.Y(), c.Z()],
            "inertia_mm5": [[m.Value(r, k) for k in (1, 2, 3)] for r in (1, 2, 3)],
            "bbox_mm": np.array(box.Get()).reshape(2, 3).tolist(),
            "valid": bool(BRepCheck_Analyzer(shape).IsValid())}


def tessellate(shape, linear_mm: float, angular_rad: float) -> tuple[np.ndarray, np.ndarray, int]:
    """BRepMesh triangulation of every face (orientation applied), merged vertices; CAD mm."""
    import trimesh
    from OCC.Core.BRep import BRep_Tool
    from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
    from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_REVERSED
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopLoc import TopLoc_Location
    from OCC.Core.TopoDS import topods

    BRepMesh_IncrementalMesh(shape, linear_mm, False, angular_rad, True).Perform()
    verts, tris, skipped, offset = [], [], 0, 0
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        explorer.Next()
        location = TopLoc_Location()
        triangulation = BRep_Tool.Triangulation(face, location)
        if triangulation is None:
            skipped += 1
            continue
        trsf = location.Transformation()
        nodes = []
        for k in range(1, triangulation.NbNodes() + 1):
            p = triangulation.Node(k).Transformed(trsf)
            nodes.append((p.X(), p.Y(), p.Z()))
        local = []
        for k in range(1, triangulation.NbTriangles() + 1):
            a, b, c = triangulation.Triangle(k).Get()
            local.append((a - 1, c - 1, b - 1) if face.Orientation() == TopAbs_REVERSED else (a - 1, b - 1, c - 1))
        verts.extend(nodes)
        tris.extend([(a + offset, b + offset, c + offset) for a, b, c in local])
        offset += len(nodes)
    mesh = trimesh.Trimesh(np.array(verts), np.array(tris), process=False)
    mesh.merge_vertices(digits_vertex=6)
    return np.asarray(mesh.vertices), np.asarray(mesh.faces, np.int64), skipped


def split_rod_pad(shape, pad_bottom_y_mm: float):
    """Boolean split at Y_cad = pad bottom + 25 mm (same as export_params.split_rod_pad)."""
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCC.Core.gp import gp_Pnt
    from OCC.Core.TopAbs import TopAbs_SOLID
    from OCC.Core.TopExp import TopExp_Explorer

    (x0, y0, z0), (x1, _, z1) = volume_properties(shape)["bbox_mm"]
    margin = 10.0
    lower = BRepPrimAPI_MakeBox(gp_Pnt(x0 - margin, y0 - margin, z0 - margin),
                                gp_Pnt(x1 + margin, pad_bottom_y_mm + PAD_SPLIT_HEIGHT_MM, z1 + margin)).Shape()
    plate = BRepAlgoAPI_Common(shape, lower).Shape()
    upper = BRepAlgoAPI_Cut(shape, lower).Shape()
    pieces = []
    explorer = TopExp_Explorer(upper, TopAbs_SOLID)
    while explorer.More():
        pieces.append(explorer.Current())
        explorer.Next()
    pieces.sort(key=lambda s: -volume_properties(s)["volume_mm3"])
    return plate, pieces[0], pieces[1:]


def make_compound(shapes):
    from OCC.Core.BRep import BRep_Builder
    from OCC.Core.TopoDS import TopoDS_Compound

    compound = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(compound)
    for s in shapes:
        builder.Add(compound, s)
    return compound


def summed_properties(shapes) -> dict:
    """Per-solid GProp sum (step-brep-cache note: compound VolumeProperties can be 2e-6 off)."""
    from OCC.Core.BRepGProp import brepgprop
    from OCC.Core.GProp import GProp_GProps

    total = GProp_GProps()
    for s in shapes:
        p = GProp_GProps()
        brepgprop.VolumeProperties(s, p)
        total.Add(p, 1.0)
    c = total.CentreOfMass()
    m = total.MatrixOfInertia()
    return {"volume_mm3": total.Mass(), "centroid_mm": [c.X(), c.Y(), c.Z()],
            "inertia_mm5": [[m.Value(r, k) for k in (1, 2, 3)] for r in (1, 2, 3)]}


def pad_bottom(shape) -> dict:
    """Lowest -Y_cad planar face: area, outward normal (XDir x YDir, REVERSED flips), polygon."""
    from OCC.Core.BRep import BRep_Tool
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
    from OCC.Core.BRepGProp import brepgprop
    from OCC.Core.BRepTools import BRepTools_WireExplorer, breptools
    from OCC.Core.GeomAbs import GeomAbs_Plane
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_REVERSED
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopoDS import topods

    best = None
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        explorer.Next()
        surface = BRepAdaptor_Surface(face, True)
        if surface.GetType() != GeomAbs_Plane:
            continue
        pos = surface.Plane().Position()
        x, y = pos.XDirection(), pos.YDirection()
        n = np.cross([x.X(), x.Y(), x.Z()], [y.X(), y.Y(), y.Z()])
        if face.Orientation() == TopAbs_REVERSED:
            n = -n
        if n[1] > -0.999:
            continue
        level = surface.Plane().Location().Y()
        if best is None or level < best[1]:
            best = (face, level, n)
    face, level, normal = best
    props = GProp_GProps()
    brepgprop.SurfaceProperties(face, props)
    c = props.CentreOfMass()
    wire_points = []
    wire = BRepTools_WireExplorer(breptools.OuterWire(face))
    while wire.More():
        p = BRep_Tool.Pnt(wire.CurrentVertex())
        wire_points.append([p.X(), p.Y(), p.Z()])
        wire.Next()
    return {"y_cad_mm": level, "area_mm2": props.Mass(), "centroid_cad_mm": [c.X(), c.Y(), c.Z()],
            "normal_cad": normal.tolist(), "polygon_cad_mm": wire_points}


def polygon_area(xy: np.ndarray) -> float:
    x, y = xy[:, 0], xy[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def side_angle_deg(xy: np.ndarray) -> float:
    """Direction of the long (square) sides from the body x axis, folded to [0, 90) deg."""
    angles = []
    edges = np.linalg.norm(np.roll(xy, -1, axis=0) - xy, axis=1)
    # long sides: >= LONG_EDGE_MIN_M (CAD 330 pad: 270 vs 42 mm), or >= half the longest edge for smaller pads
    # (REXOME35 rear 250 pad: 190 vs 42 mm); identical selection for the CAD pads
    long_min = min(LONG_EDGE_MIN_M, 0.5 * float(edges.max()))
    for a, b in zip(xy, np.roll(xy, -1, axis=0), strict=True):
        d = b - a
        if np.hypot(*d) >= long_min:
            angles.append(np.degrees(np.arctan2(d[1], d[0])) % 90.0)
    angles = np.array(angles)
    # circular mean on a 90 deg period
    mean = np.degrees(np.angle(np.exp(1j * np.radians(angles) * 4).mean())) / 4 % 90.0
    return float(mean)


def inset_polygon(xy: np.ndarray, distance: float) -> np.ndarray:
    """Inward offset of a convex counter-clockwise polygon (edge lines moved by ``distance``)."""
    n = len(xy)
    lines = []
    for i in range(n):
        a, b = xy[i], xy[(i + 1) % n]
        d = (b - a) / np.linalg.norm(b - a)
        inward = np.array([-d[1], d[0]])
        lines.append((a + distance * inward, d))
    out = []
    for i in range(n):
        (p1, d1), (p2, d2) = lines[i - 1], lines[i]
        t = np.linalg.solve(np.column_stack([d1, -d2]), p2 - p1)
        out.append(p1 + t[0] * d1)
    return np.array(out)


def trimesh_props(vertices_m: np.ndarray, faces: np.ndarray) -> dict:
    import trimesh

    m = trimesh.Trimesh(vertices_m, faces, process=False)
    return {"volume_m3": float(m.volume), "com_m": m.center_mass.tolist(),
            "inertia_unit_density_m5": m.moment_inertia.tolist(), "watertight": bool(m.is_watertight)}


def brep_props_body(props: dict, offset_z_m: float) -> dict:
    inertia = CAD_TO_BODY @ np.array(props["inertia_mm5"]) @ CAD_TO_BODY.T * MM**5
    return {"volume_m3": props["volume_mm3"] * MM**3,
            "com_m": (CAD_TO_BODY @ np.array(props["centroid_mm"]) * MM + [0, 0, offset_z_m]).tolist(),
            "inertia_unit_density_m5": (0.5 * (inertia + inertia.T)).tolist()}


def compare_props(mesh: dict, brep: dict) -> dict:
    mi, bi = np.array(mesh["inertia_unit_density_m5"]), np.array(brep["inertia_unit_density_m5"])
    return {"volume_rel": mesh["volume_m3"] / brep["volume_m3"] - 1.0,
            "com_abs_m": float(np.linalg.norm(np.array(mesh["com_m"]) - brep["com_m"])),
            "inertia_frobenius_rel": float(np.linalg.norm(mi - bi) / np.linalg.norm(bi))}


def decimate_closed(v: np.ndarray, f: np.ndarray, tol: float) -> tuple[np.ndarray, np.ndarray, float]:
    import fast_simplification

    vol0 = signed_volume(v, f, v.mean(0))
    for reduction in (0.9, 0.8, 0.7, 0.5, 0.3):
        v2, f2 = fast_simplification.simplify(v.astype(np.float32), f.astype(np.int32),
                                              target_reduction=reduction, agg=7)
        v2, f2 = np.asarray(v2, float), np.asarray(f2, np.int64)
        if len(f2) and abs(signed_volume(v2, f2, v.mean(0)) / vol0 - 1.0) <= tol:
            return v2, f2, reduction
    return v, f, 0.0


def stage_legs(state: dict) -> None:
    from outrigger_sim.params import load_params

    params = load_params()
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    legs = {}
    for index, leg_name in enumerate(LEG_ORDER):
        started = time.perf_counter()
        leg = params.legs[index]
        offset = float(leg.retracted_offset_from_cad_m)
        path = moving_brep_path(leg_name)
        shape = read_ascii_brep(path)
        bottom = pad_bottom(shape)
        plate, rod, gussets = split_rod_pad(shape, bottom["y_cad_mm"])
        whole_p = volume_properties(shape)
        plate_p = volume_properties(plate)
        rod_p = volume_properties(rod)
        pad_cad_p = summed_properties([plate, *gussets])
        moving_p = summed_properties([plate, rod, *gussets])

        def to_body(v_mm):
            return cad_to_body_m(v_mm) + np.array([0.0, 0.0, offset])

        record = {"brep": source_record(path), "retracted_offset_from_cad_m": offset,
                  "valid": {"whole": whole_p["valid"], "plate": plate_p["valid"], "rod": rod_p["valid"]},
                  "gusset_count": len(gussets)}
        # --- tessellate rod and pad plate + gussets
        pieces = {"rod": [rod], "pad_cad": [plate, *gussets], "moving": [plate, rod, *gussets]}
        brep_props = {"rod": brep_props_body(rod_p, offset), "pad_cad": brep_props_body(pad_cad_p, offset),
                      "moving": brep_props_body(moving_p, offset)}
        meshes = {}
        for key, shapes in pieces.items():
            v_mm, f, skipped = tessellate(make_compound(shapes), LEG_LINEAR_DEFLECTION_MM, LEG_ANGULAR_DEFLECTION_RAD)
            v2, f2, reduction = decimate_closed(v_mm, f, LEG_DECIMATE_VOL_TOL)
            vb = to_body(v2)
            meshes[key] = (vb, f2)
            box_brep = bbox_cad_to_body_m(np.array(volume_properties(make_compound(shapes))["bbox_mm"])) + [0, 0, offset]
            record[key] = {
                "tessellation": {"linear_deflection_mm": LEG_LINEAR_DEFLECTION_MM,
                                 "angular_deflection_rad": LEG_ANGULAR_DEFLECTION_RAD,
                                 "faces": int(len(f)), "skipped_faces": skipped},
                "decimation_target_reduction": reduction,
                "brep": brep_props[key],
                "brep_bbox_body_m": box_brep.tolist(),
                "mesh": trimesh_props(vb, f2),
                "stats": mesh_stats(vb, f2, brep_props[key]["volume_m3"], box_brep),
            }
            record[key]["mesh_vs_brep"] = compare_props(record[key]["mesh"], brep_props[key])
            np.savez_compressed(WORK_DIR / f"{key}_{leg_name}.npz", vertices=vb, faces=f2)
        header = ["frame: machine body axes, origin CAD origin, metres, leg retracted state"]
        record["rod"]["obj"] = write_obj(VISUAL_DIR / f"rod_{leg_name}.obj", [meshes["rod"]],
                                         [f"C8 rod + piston + boss of {leg_name} (B-rep split at pad bottom + 25 mm)", *header])
        record["pad_cad"]["obj"] = write_obj(VISUAL_DIR / f"pad_{leg_name}_cad.obj", [meshes["pad_cad"]],
                                             [f"C8 pad plate + {len(gussets)} gussets of {leg_name} (B-rep)", *header])
        # --- pad bottom face (B-rep) and the simplified chamfered octagon plate
        poly_cad = np.array(bottom["polygon_cad_mm"])
        poly_body = to_body(poly_cad)
        bottom_z = float(poly_body[:, 2].mean())
        centre_body = (CAD_TO_BODY @ np.array(bottom["centroid_cad_mm"])) * MM + [0, 0, offset]
        xy = poly_body[:, :2]
        if polygon_area(xy) < 0:
            xy = xy[::-1]
        thickness_mm = plate_p["bbox_mm"][1][1] - plate_p["bbox_mm"][0][1]
        # side height (B-rep, measure_side_height) and chamfer = thickness - side height (45 deg)
        side_height_m = float(state["pad_side_height_m"])
        chamfer_m = thickness_mm * MM - side_height_m
        top_xy = inset_polygon(xy, chamfer_m)
        points = np.vstack([np.column_stack([xy, np.full(len(xy), bottom_z)]),
                            np.column_stack([xy, np.full(len(xy), bottom_z + side_height_m)]),
                            np.column_stack([top_xy, np.full(len(xy), bottom_z + thickness_mm * MM)])])
        import trimesh

        simple = trimesh.convex.convex_hull(points)
        sv, sf = np.asarray(simple.vertices), np.asarray(simple.faces, np.int64)
        record["pad_simple"] = {
            "definition": "convex hull of the B-rep bottom octagon at z_b and z_b + side height and the octagon "
                          "inset by the chamfer (thickness - side height, 45 deg) at z_b + thickness",
            "side_height_m": side_height_m, "chamfer_m": chamfer_m, "thickness_m": thickness_mm * MM,
            "mesh": trimesh_props(sv, sf),
            "brep_plate": brep_props_body(plate_p, offset),
            "stats": mesh_stats(sv, sf, plate_p["volume_mm3"] * MM**3,
                                bbox_cad_to_body_m(np.array(plate_p["bbox_mm"])) + [0, 0, offset]),
        }
        record["pad_simple"]["mesh_vs_brep_plate"] = compare_props(record["pad_simple"]["mesh"],
                                                                   record["pad_simple"]["brep_plate"])
        record["pad_simple"]["obj"] = write_obj(
            VISUAL_DIR / f"pad_{leg_name}_simple.obj", [(sv, sf)],
            [f"C8 simplified pad of {leg_name}: chamfered octagon plate (convex)", *header])
        record["pad_simple"]["collision_obj"] = write_obj(
            COLLISION_DIR / f"pad_{leg_name}_hull.obj", [(sv, sf)],
            [f"C8 collision candidate: pad plate of {leg_name} as one convex hull (= pad_{leg_name}_simple)", *header])
        np.savez_compressed(WORK_DIR / f"pad_simple_{leg_name}.npz", vertices=sv, faces=sf)
        # --- pad comparison: B-rep face, YAML, simple mesh bottom
        yaml_xy = np.array(leg.pad.polygon_xy_m) + np.array(leg.pad_bottom_center_retracted_m)[:2]
        normal_body = CAD_TO_BODY @ np.array(bottom["normal_cad"])
        normal_body /= np.linalg.norm(normal_body)
        down = sf[(np.cross(sv[sf[:, 1]] - sv[sf[:, 0]], sv[sf[:, 2]] - sv[sf[:, 0]]) @ [0, 0, 1]) < 0]
        tri = sv[down]
        down_area = 0.5 * float(np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1).sum())
        record["pad_face"] = {
            "brep_area_m2": bottom["area_mm2"] * MM**2,
            "brep_polygon_area_m2": polygon_area(xy),
            "brep_normal_body": normal_body.tolist(),
            "brep_tilt_from_vertical_deg": float(np.degrees(np.arccos(min(1.0, -normal_body[2])))),
            "brep_side_angle_deg": side_angle_deg(xy),
            "brep_bottom_z_m": bottom_z,
            "brep_centroid_body_m": centre_body.tolist(),
            "brep_polygon_xy_body_m": xy.tolist(),
            "yaml_bottom_area_m2": float(leg.pad.bottom_area_m2),
            "yaml_polygon_area_m2": polygon_area(yaml_xy),
            "yaml_side_angle_deg": side_angle_deg(yaml_xy),
            "yaml_pad_bottom_center_retracted_m": list(leg.pad_bottom_center_retracted_m),
            "yaml_polygon_max_vertex_diff_m": float(np.abs(_match_polygon(xy, yaml_xy)).max()),
            "simple_down_face_area_m2": down_area,
            "simple_bottom_z_m": float(sv[:, 2].min()),
        }
        record["time_s"] = time.perf_counter() - started
        legs[leg_name] = record
        log(f"legs {leg_name}: pad area {record['pad_face']['brep_area_m2']:.6f} m2, angle "
            f"{record['pad_face']['brep_side_angle_deg']:.3f} deg, simple vol "
            f"{record['pad_simple']['mesh_vs_brep_plate']['volume_rel']:+.2e}, {record['time_s']:.1f} s")
    state["legs"] = legs


def _match_polygon(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Vertex differences after matching every vertex of ``a`` to the nearest of ``b``."""
    d = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    return a - b[d.argmin(1)]


def measure_side_height(state: dict) -> None:
    """Height of the vertical pad side faces above the bottom face (B-rep, FL), for the simple pad."""
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.GeomAbs import GeomAbs_Plane
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopoDS import topods

    heights = {}
    for leg_name in LEG_ORDER:
        shape = read_ascii_brep(moving_brep_path(leg_name))
        y0 = pad_bottom(shape)["y_cad_mm"]
        sides = []
        explorer = TopExp_Explorer(shape, TopAbs_FACE)
        while explorer.More():
            face = topods.Face(explorer.Current())
            explorer.Next()
            surface = BRepAdaptor_Surface(face, True)
            if surface.GetType() != GeomAbs_Plane:
                continue
            d = surface.Plane().Axis().Direction()
            if abs(d.Y()) > 1e-3:
                continue
            box = Bnd_Box()
            brepbndlib.AddOptimal(face, box, False, False)
            _, lo, _, _, hi, _ = box.Get()
            if abs(lo - y0) < 1e-3:
                sides.append(hi - y0)
        heights[leg_name] = max(sides)
    state["pad_side_height_mm"] = heights
    values = np.array(list(heights.values()))
    if np.ptp(values) > 1e-6:
        raise SystemExit(f"pad side heights differ: {heights}")
    state["pad_side_height_m"] = float(values[0]) * MM


# ============================================================================================
# stage: convex hulls
# ============================================================================================
def load_work(key: str) -> tuple[np.ndarray, np.ndarray]:
    data = np.load(WORK_DIR / f"{key}.npz")
    return data["vertices"], data["faces"]


def stage_hulls(state: dict, only: list[str] | None = None) -> None:
    import trimesh

    if only and set(only) - set(HULL_TARGETS):
        raise SystemExit(f"--hull-only: unknown {sorted(set(only) - set(HULL_TARGETS))}")
    hulls = {}
    for key in (only or HULL_TARGETS):
        v, f = load_work(key)
        hull = trimesh.Trimesh(v[np.unique(f)], process=False).convex_hull
        ref_vol, ref_box = reference_of(state, key)
        stats = mesh_stats(np.asarray(hull.vertices), np.asarray(hull.faces), ref_vol, ref_box)
        stats["volume_ratio_to_brep"] = float(hull.volume / ref_vol) if ref_vol else None
        stats["obj"] = write_obj(COLLISION_DIR / f"{key}_hull.obj",
                                 [(np.asarray(hull.vertices), np.asarray(hull.faces))],
                                 [f"C8 collision candidate: convex hull of '{key}'",
                                  "frame: machine body axes, origin CAD origin, metres"])
        hulls[f"{key}_hull"] = {"input": key, **stats}
        log(f"hull {key}: {len(hull.faces)} faces, vol ratio {stats['volume_ratio_to_brep']:.3f}")
    if only:
        state.setdefault("hulls", {}).update(hulls)
    else:
        state["hulls"] = hulls


def reference_of(state: dict, key: str) -> tuple[float | None, np.ndarray | None]:
    """B-rep volume (m^3) and bbox (body m) of an input mesh key."""
    groups = state.get("groups", {})
    if key in groups:
        g = groups[key]
        return g["brep_volume_m3"], np.array(g["brep_bbox_body_m"])
    if key.startswith("track_"):
        t = groups["crawler"]["tracks"][key[-1]]
        return t["brep_volume_m3"], np.array(t["brep_bbox_body_m"])
    for prefix in ("rod", "pad_cad", "moving"):
        if key.startswith(prefix + "_") and key[len(prefix) + 1:] in LEG_ORDER:
            r = state["legs"][key[len(prefix) + 1:]][prefix]
            return r["brep"]["volume_m3"], np.array(r["brep_bbox_body_m"])
    return None, None


# ============================================================================================
# stage: convex decomposition (child processes)
# ============================================================================================
def decompose_one(name: str) -> None:
    """Child process: run one decomposition target and write OBJ + work/<name>.json."""
    import trimesh

    spec = DECOMPOSE_TARGETS[name]
    v, f = load_work(spec["input"])
    started = time.perf_counter()
    if spec["tool"] == "coacd":
        import coacd

        coacd.set_log_level("error")
        settings = {**COACD_COMMON, **spec["settings"]}
        parts = coacd.run_coacd(coacd.Mesh(np.asarray(v, float), np.asarray(f, np.int32)), **settings)
        pieces = [(np.asarray(pv, float), np.asarray(pf, np.int64)) for pv, pf in parts]
        tool_version = getattr(coacd, "__version__", "conda coacd 1.0.14")
    else:
        settings = dict(spec["settings"])
        mesh = trimesh.Trimesh(v, f, process=False)
        parts = mesh.convex_decomposition(**settings)
        parts = parts if isinstance(parts, list) else [parts]
        pieces = []
        for p in parts:
            if isinstance(p, dict):
                pieces.append((np.asarray(p["vertices"], float), np.asarray(p["faces"], np.int64)))
            else:
                pieces.append((np.asarray(p.vertices, float), np.asarray(p.faces, np.int64)))
        import vhacdx

        tool_version = f"vhacdx {vhacdx.__version__}"
    elapsed = time.perf_counter() - started
    hulls = [trimesh.Trimesh(pv, pf, process=False).convex_hull for pv, pf in pieces]
    out = {
        "input": spec["input"], "tool": spec["tool"], "tool_version": tool_version, "settings": settings,
        "time_s": elapsed, "pieces": len(pieces),
        "vertices_per_piece_max": int(max(len(h.vertices) for h in hulls)),
        "faces_total": int(sum(len(h.faces) for h in hulls)),
        "sum_piece_volume_m3": float(sum(h.volume for h in hulls)),
        "bbox_min": np.min([h.bounds[0] for h in hulls], axis=0).tolist(),
        "bbox_max": np.max([h.bounds[1] for h in hulls], axis=0).tolist(),
        "cpu_affinity": _affinity(),
    }
    out["obj"] = write_obj(COLLISION_DIR / f"{name}.obj",
                           [(np.asarray(h.vertices), np.asarray(h.faces)) for h in hulls],
                           [f"C8 collision candidate '{name}': {spec['tool']} convex decomposition of '{spec['input']}', "
                            f"{len(hulls)} convex pieces (convex hull of each tool piece)",
                            "frame: machine body axes, origin CAD origin, metres"])
    (WORK_DIR / f"{name}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


def _affinity():
    try:
        import psutil

        return psutil.Process().cpu_affinity()
    except Exception:  # noqa: BLE001
        return None


def stage_decompose(state: dict, workers: int, cpu: str, only: list[str] | None) -> None:
    import psutil

    names = only or list(DECOMPOSE_TARGETS)
    env = dict(os.environ)
    env["CONDA_PREFIX"] = str(Path(sys.executable).parent)  # coacd finds _coacd.dll through it
    threads = str(max(1, len(E_CORES) // max(1, workers)))
    env.update(OMP_NUM_THREADS=threads, OPENBLAS_NUM_THREADS="1")
    queue = list(names)
    running: list[tuple[str, subprocess.Popen, float]] = []
    results = state.setdefault("decompositions", {})
    while queue or running:
        while queue and len(running) < workers:
            name = queue.pop(0)
            log_path = WORK_DIR / f"{name}.log"
            handle = log_path.open("w", encoding="utf-8")
            proc = subprocess.Popen([sys.executable, "-I", str(Path(__file__).resolve()), "--decompose-one", name,
                                     "--cpu", cpu, *(["--out-dir", str(OUT_DIR)] if OUT_DIR != CAD_DIR / "09_sim_shapes"
                                                     else [])],
                                    stdout=handle, stderr=subprocess.STDOUT, env=env, cwd=str(PROJECT_ROOT))
            if cpu != "os":
                try:
                    child = psutil.Process(proc.pid)
                    child.cpu_affinity(E_CORES)
                    child.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                except Exception as error:  # noqa: BLE001
                    log(f"cannot place {name}: {error!r}")
            running.append((name, proc, time.perf_counter()))
            log(f"decompose start {name} (pid {proc.pid})")
        time.sleep(1.0)
        for item in list(running):
            name, proc, t0 = item
            if proc.poll() is None:
                continue
            running.remove(item)
            path = WORK_DIR / f"{name}.json"
            if proc.returncode != 0 or not path.exists():
                results[name] = {"error": f"exit {proc.returncode}, see {rel(WORK_DIR / (name + '.log'))}"}
                log(f"decompose FAILED {name}: exit {proc.returncode}")
                continue
            record = json.loads(path.read_text(encoding="utf-8"))
            ref_vol, ref_box = reference_of(state, record["input"])
            record["brep_volume_m3"] = ref_vol
            record["sum_piece_volume_ratio_to_brep"] = record["sum_piece_volume_m3"] / ref_vol if ref_vol else None
            if ref_box is not None:
                record["bbox_abs_diff_m"] = float(np.abs(np.array([record["bbox_min"], record["bbox_max"]]) - ref_box).max())
            results[name] = record
            log(f"decompose done {name}: {record['pieces']} pieces, vol ratio "
                f"{record['sum_piece_volume_ratio_to_brep']:.3f}, {record['time_s']:.0f} s")


# ============================================================================================
# stage: upper (carrier) rollers of the crawler (derive_crawler_upper_rollers.py cache)
# ============================================================================================
def _merge_intervals(intervals: list[tuple[float, float]], tol: float = 0.05) -> list[tuple[float, float]]:
    merged: list[list[float]] = []
    for lo, hi in sorted(intervals):
        if merged and lo <= merged[-1][1] + tol:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    return [(a, b) for a, b in merged]


def upper_roller_cylinders(roller_solid, axis_cad_mm: np.ndarray) -> list[dict]:
    """Convex cylinders R60 (treads) and R70 (flange) coaxial with the roller axis (X_cad).

    Outward-facing test: revolved face convex iff ``Position().Direct() != reversed``
    (face-index rule). Spans are the merged X_cad extents (AddOptimal) of the faces.
    """
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.GeomAbs import GeomAbs_Cylinder
    from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_REVERSED
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopoDS import topods

    found: dict[float, list[tuple[float, float]]] = {}
    explorer = TopExp_Explorer(roller_solid, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        explorer.Next()
        surface = BRepAdaptor_Surface(face, True)
        if surface.GetType() != GeomAbs_Cylinder:
            continue
        cylinder = surface.Cylinder()
        axis = cylinder.Axis()
        d, p = axis.Direction(), axis.Location()
        if abs(abs(d.X()) - 1.0) > 1e-6:
            continue
        if np.hypot(p.Y() - axis_cad_mm[1], p.Z() - axis_cad_mm[2]) > 0.5:
            continue
        convex = cylinder.Position().Direct() != (face.Orientation() == TopAbs_REVERSED)
        radius = round(cylinder.Radius(), 3)
        if not convex or radius not in (60.0, 70.0):
            continue
        box = Bnd_Box()
        brepbndlib.AddOptimal(face, box, False, False)
        x0, _, _, x1, _, _ = box.Get()
        found.setdefault(radius, []).append((x0, x1))
    out = []
    for radius, spans in sorted(found.items()):
        for k, (x0, x1) in enumerate(_merge_intervals(spans)):
            out.append({"name": f"{'tread' if radius == 60.0 else 'flange'}_{k}", "radius_m": radius * MM,
                        "height_m": (x1 - x0) * MM, "x_cad_span_mm": [x0, x1],
                        "centre_m": (CAD_TO_BODY @ np.array([0.5 * (x0 + x1), axis_cad_mm[1], axis_cad_mm[2]])
                                     * MM).tolist(),
                        # Chrono cylinder axis = local z; rotate -90 deg about x so local z = body +y
                        "rotation_wxyz": [float(np.cos(-np.pi / 4)), float(np.sin(-np.pi / 4)), 0.0, 0.0]})
    return out


def stage_upper_rollers(state: dict) -> None:
    """Visual mesh, convex hull and primitive cylinders of the upper rollers; crawler mesh
    variant without the components that belong to the upper rollers (duplicate display)."""
    import trimesh

    import brep_cache

    started = time.perf_counter()
    rows = list(pd.read_csv(UPPER_ROLLERS_CSV, encoding="utf-8-sig").itertuples())
    crawler_v, crawler_f = load_work("crawler")
    crawler = trimesh.Trimesh(crawler_v, crawler_f, process=False)
    comps = components(crawler)
    comp_boxes = np.array([used_bbox(crawler_v, crawler_f[c]) for c in comps])
    removed_mask = np.zeros(len(comps), bool)
    out = {}
    for row in rows:
        side = row.side
        name = f"upper_roller_{side}"
        path = PROJECT_ROOT / row.file
        shape = brep_cache.read_brep(path)
        from OCC.Core.TopAbs import TopAbs_SOLID
        from OCC.Core.TopExp import TopExp_Explorer

        solids = []
        explorer = TopExp_Explorer(shape, TopAbs_SOLID)
        while explorer.More():
            solids.append(explorer.Current())
            explorer.Next()
        props = summed_properties(solids)
        brep = brep_props_body(props, 0.0)
        brep_box = np.array([[row.bbox_min_x_body_m, row.bbox_min_y_body_m, row.bbox_min_z_body_m],
                             [row.bbox_max_x_body_m, row.bbox_max_y_body_m, row.bbox_max_z_body_m]])
        v_mm, f, skipped = tessellate(shape, UPPER_ROLLER_LINEAR_MM, UPPER_ROLLER_ANGULAR_RAD)
        vb = cad_to_body_m(v_mm)
        com = np.array(brep["com_m"])
        # mass properties only on the roller solid: BRepMesh skips one chamfer cone face
        # (80.5 mm^2) on 3 bolts, so the whole-part mesh is not closed
        roller_solid = max(solids, key=lambda s: volume_properties(s)["volume_mm3"])
        rv_mm, rf, rskipped = tessellate(roller_solid, UPPER_ROLLER_LINEAR_MM, UPPER_ROLLER_ANGULAR_RAD)
        mesh_p = trimesh_props(cad_to_body_m(rv_mm), rf)
        roller_brep = brep_props_body(summed_properties([roller_solid]), 0.0)
        record = {
            "brep": source_record(path), "solids": len(solids), "csv_volume_mm3": float(row.volume_mm3),
            "brep_volume_rel_to_csv": props["volume_mm3"] / float(row.volume_mm3) - 1.0,
            "brep_mass_kg_7.85": props["volume_mm3"] * 7.85e-6, "csv_mass_kg": float(row.mass_kg),
            "brep_bbox_body_m": brep_box.tolist(),
            "tessellation": {"linear_deflection_mm": UPPER_ROLLER_LINEAR_MM,
                             "angular_deflection_rad": UPPER_ROLLER_ANGULAR_RAD, "faces": int(len(f)),
                             "skipped_faces": skipped},
            "brep_props": brep,
            "stats": mesh_stats(vb, f, brep["volume_m3"], brep_box, origin=com),
            "stats_note": "volume about the B-rep COM (mesh not closed: skipped faces)",
            "roller_solid": {"faces": int(len(rf)), "skipped_faces": rskipped, "mesh": mesh_p,
                             "brep": roller_brep, "mesh_vs_brep": compare_props(mesh_p, roller_brep)},
            "axis_body_m": [row.roller_axis_x_body_m, row.roller_axis_y_body_m, row.roller_axis_z_body_m],
        }
        header = [f"C8 upper (carrier) roller {side}: roller solid + bracket bolts/washers "
                  f"({len(solids)} solids, {rel(path)})",
                  "frame: machine body axes, origin CAD origin, metres, CAD pose"]
        record["obj"] = write_obj(VISUAL_DIR / f"{name}.obj", [(vb, f)], header)
        hull = trimesh.Trimesh(vb, f, process=False).convex_hull
        hv, hf = np.asarray(hull.vertices), np.asarray(hull.faces)
        record["hull"] = mesh_stats(hv, hf, brep["volume_m3"], brep_box)
        record["hull"]["volume_ratio_to_brep"] = float(hull.volume / brep["volume_m3"])
        record["hull"]["obj"] = write_obj(COLLISION_DIR / f"{name}_hull.obj", [(hv, hf)],
                                          [f"C8 collision candidate: convex hull of upper roller {side}",
                                           header[1]])
        # primitive cylinders from the B-rep faces of the roller solid (largest solid)
        axis_cad = CAD_TO_BODY.T @ np.array(record["axis_body_m"]) / MM
        cylinders = upper_roller_cylinders(roller_solid, axis_cad)
        record["cylinders"] = cylinders
        record["cylinders_check"] = {
            "count_tread_flange": [sum(c["name"].startswith("tread") for c in cylinders),
                                   sum(c["name"].startswith("flange") for c in cylinders)],
            "csv_tread_diameter_mm": float(row.tread_diameter_mm), "csv_tread_width_mm": float(row.tread_width_mm),
            "csv_tread_spans_x_cad_mm": row.tread_spans_x_cad_mm,
            "csv_flange_diameter_mm": float(row.flange_diameter_mm), "csv_flange_width_mm": float(row.flange_width_mm),
        }
        # duplicate display: crawler visual components lying inside the roller bbox (+margin)
        margin = UPPER_ROLLER_BBOX_MARGIN_MM * MM
        in_box = np.all(comp_boxes[:, 0] >= brep_box[0] - margin, axis=1) & np.all(
            comp_boxes[:, 1] <= brep_box[1] + margin, axis=1)
        roller_mesh = trimesh.Trimesh(vb, f, process=False)
        inside = np.zeros_like(in_box)
        rejected = []
        for k in np.flatnonzero(in_box):
            points = crawler_v[np.unique(crawler_f[comps[k]])]
            _, dist, _ = trimesh.proximity.closest_point(roller_mesh, points)
            if dist.max() <= UPPER_ROLLER_DUPLICATE_DIST_MM * MM:
                inside[k] = True
            else:
                rejected.append({"faces": int(len(comps[k])), "max_distance_mm": float(dist.max() / MM),
                                 "volume_m3": signed_volume(crawler_v, crawler_f[comps[k]], com),
                                 "bbox_body_m": comp_boxes[k].tolist()})
        removed_mask |= inside
        sel = [comps[k] for k in np.flatnonzero(inside)]
        removed_faces = np.concatenate(sel) if sel else np.zeros(0, np.int64)
        removed_vol = sum(signed_volume(crawler_v, crawler_f[c], com) for c in sel)
        record["crawler_overlap"] = {
            "components_inside_bbox": int(inside.sum()), "faces": int(len(removed_faces)),
            "volume_m3": removed_vol, "volume_rel_to_roller_brep": removed_vol / brep["volume_m3"] - 1.0,
            "bbox_margin_mm": UPPER_ROLLER_BBOX_MARGIN_MM, "max_distance_mm": UPPER_ROLLER_DUPLICATE_DIST_MM,
            "in_bbox_not_duplicate": rejected,
        }
        out[side] = record
        log(f"upper roller {side}: {len(f)} faces, vol {record['stats']['volume_rel_to_brep']:+.2e}, "
            f"cylinders {record['cylinders_check']['count_tread_flange']}, crawler overlap "
            f"{record['crawler_overlap']['components_inside_bbox']} comps "
            f"({record['crawler_overlap']['volume_rel_to_roller_brep']:+.3f})")
    keep = [comps[k] for k in np.flatnonzero(~removed_mask)]
    kv, kf = compact(crawler_v, crawler_f[np.concatenate(keep)])
    group = state["groups"]["crawler"]
    rollers_volume = sum(r["brep_props"]["volume_m3"] for r in out.values())
    variant = {
        "removed_components": int(removed_mask.sum()),
        "brep_volume_m3": group["brep_volume_m3"] - rollers_volume,
        "visual_mesh": mesh_stats(kv, kf, group["brep_volume_m3"] - rollers_volume,
                                  np.array(group["brep_bbox_body_m"])),
    }
    variant["obj"] = write_obj(VISUAL_DIR / "crawler_no_upper_rollers_lowres.obj", [(kv, kf)],
                               ["C8 crawler visual mesh without the upper rollers (crawler_lowres.obj minus "
                                "the components inside the upper-roller bboxes)",
                                "frame: machine body axes, origin CAD origin, metres, CAD pose"])
    state["upper_rollers"] = {"rollers": out, "crawler_variant": variant,
                              "source": source_record(UPPER_ROLLERS_CSV),
                              "time_s": time.perf_counter() - started}
    log(f"crawler without upper rollers: {variant['visual_mesh']['faces']} faces, removed "
        f"{variant['removed_components']} components, {time.perf_counter() - started:.0f} s")


# ============================================================================================
# stage: index
# ============================================================================================
def primitives(state: dict) -> dict:
    """Primitive collision candidates (box / cylinder) in the same frame."""
    crawler = json.loads(CRAWLER_COLLISION_JSON.read_text(encoding="utf-8"))
    out = {}
    for side, key in (("L", "left"), ("R", "right")):
        box = crawler["groups"][key]["box"]
        out[f"track_{side}_box"] = {
            "kind": "box", "attach": "superstructure", "centre_m": box["centre_body_m"],
            "half_extents_m": box["half_extents_body_m"], "rotation_wxyz": [1, 0, 0, 0],
            "volume_ratio_to_brep": box["volume_ratio_to_brep"], "source": rel(CRAWLER_COLLISION_JSON)}
    for leg_name in LEG_ORDER:
        face = state["legs"][leg_name]["pad_face"]
        xy = np.array(face["brep_polygon_xy_body_m"])
        angle = np.radians(face["brep_side_angle_deg"])
        u = np.array([np.cos(angle), np.sin(angle)])
        w = np.array([-u[1], u[0]])
        side_u = float(np.ptp(xy @ u))
        side_w = float(np.ptp(xy @ w))
        thickness = state["legs"][leg_name]["pad_simple"]["thickness_m"]
        centre = np.array(face["brep_centroid_body_m"]) + [0, 0, 0.5 * thickness]
        half = 0.5 * angle
        out[f"pad_{leg_name}_box"] = {
            "kind": "box", "attach": "leg", "leg": leg_name, "centre_m": centre.tolist(),
            "half_extents_m": [0.5 * side_u, 0.5 * side_w, 0.5 * thickness],
            "rotation_wxyz": [float(np.cos(half)), 0.0, 0.0, float(np.sin(half))],
            "bottom_area_m2": side_u * side_w,
            "bottom_area_rel_to_brep": side_u * side_w / face["brep_area_m2"] - 1.0,
            "note": "square of the long-side envelope (corner chamfers 30 x 30 mm ignored)"}
    return out


def stage_index(state: dict, started_s: float, cpu_info: dict) -> None:
    from outrigger_sim.params import load_params

    params = load_params()
    visual = {}
    for name in SUPERSTRUCTURE_GROUPS:
        g = state["groups"][name]
        visual[name] = {"file": g["obj"]["file"], "attach": "superstructure", "leg": None,
                        "moves_with_auger": name == "auger", "color": GROUP_COLORS[name],
                        "faces": g["visual_mesh"]["faces"], "default": True}
    for leg_name in LEG_ORDER:
        g = state["groups"][f"barrel_{leg_name}"]
        visual[f"barrel_{leg_name}"] = {"file": g["obj"]["file"], "attach": "superstructure", "leg": leg_name,
                                        "moves_with_auger": False, "color": GROUP_COLORS["barrel"],
                                        "faces": g["visual_mesh"]["faces"], "default": True}
        legrec = state["legs"][leg_name]
        visual[f"rod_{leg_name}"] = {"file": legrec["rod"]["obj"]["file"], "attach": "leg", "leg": leg_name,
                                     "moves_with_auger": False, "color": GROUP_COLORS["rod"],
                                     "faces": legrec["rod"]["obj"]["faces"], "default": True}
        visual[f"pad_{leg_name}_simple"] = {"file": legrec["pad_simple"]["obj"]["file"], "attach": "leg",
                                            "leg": leg_name, "moves_with_auger": False,
                                            "color": GROUP_COLORS["pad"],
                                            "faces": legrec["pad_simple"]["obj"]["faces"], "default": True}
        visual[f"pad_{leg_name}_cad"] = {"file": legrec["pad_cad"]["obj"]["file"], "attach": "leg",
                                         "leg": leg_name, "moves_with_auger": False, "color": GROUP_COLORS["pad"],
                                         "faces": legrec["pad_cad"]["obj"]["faces"], "default": False}
    collision = {}
    for leg_name in LEG_ORDER:
        legrec = state["legs"][leg_name]
        collision[f"pad_{leg_name}_hull"] = {
            "kind": "convex_hull", "file": legrec["pad_simple"]["collision_obj"]["file"], "attach": "leg",
            "leg": leg_name, "pieces": 1, "faces": legrec["pad_simple"]["collision_obj"]["faces"],
            "volume_rel_to_brep_plate": legrec["pad_simple"]["mesh_vs_brep_plate"]["volume_rel"]}
    for name, record in state.get("hulls", {}).items():
        key = record["input"]
        leg_name = key[-2:] if key[-2:] in LEG_ORDER else None
        collision[name] = {"kind": "convex_hull", "file": record["obj"]["file"],
                           "attach": "leg" if key.startswith("rod_") else "superstructure", "leg": leg_name,
                           "moves_with_auger": key == "auger", "pieces": 1, "faces": record["faces"],
                           "volume_ratio_to_brep": record["volume_ratio_to_brep"]}
    for name, record in state.get("decompositions", {}).items():
        if "error" in record:
            continue
        key = record["input"]
        leg_name = key[-2:] if key[-2:] in LEG_ORDER else None
        collision[name] = {"kind": "convex_decomposition", "tool": record["tool"], "file": record["obj"]["file"],
                           "attach": "leg" if leg_name and not key.startswith("barrel") else "superstructure",
                           "leg": leg_name, "moves_with_auger": key == "auger", "pieces": record["pieces"],
                           "faces": record["faces_total"],
                           "volume_ratio_to_brep": record["sum_piece_volume_ratio_to_brep"]}
    for name, record in primitives(state).items():
        collision[name] = record
    upper = state.get("upper_rollers")
    if upper:
        variant = upper["crawler_variant"]
        visual["crawler_no_upper_rollers"] = {
            "file": variant["obj"]["file"], "attach": "superstructure", "leg": None, "moves_with_auger": False,
            "color": GROUP_COLORS["crawler"], "faces": variant["visual_mesh"]["faces"], "default": False,
            "note": "crawler_lowres minus the upper-roller components; use with upper_roller_<side> visuals"}
        for side, rec in upper["rollers"].items():
            visual[f"upper_roller_{side}"] = {
                "file": rec["obj"]["file"], "attach": "superstructure", "leg": None, "side": side,
                "moves_with_auger": False, "color": GROUP_COLORS["upper_roller"], "faces": rec["obj"]["faces"],
                "default": False, "axis_body_m": rec["axis_body_m"], "axis_dir_body": [0.0, 1.0, 0.0],
                "note": "already contained in 'crawler'; default off (duplicate display)"}
            collision[f"upper_roller_{side}_hull"] = {
                "kind": "convex_hull", "file": rec["hull"]["obj"]["file"], "attach": "superstructure", "leg": None,
                "side": side, "pieces": 1, "faces": rec["hull"]["obj"]["faces"],
                "volume_ratio_to_brep": rec["hull"]["volume_ratio_to_brep"]}
            collision[f"upper_roller_{side}_cylinders"] = {
                "kind": "cylinder_set", "attach": "superstructure", "leg": None, "side": side,
                "cylinders": rec["cylinders"], "pieces": len(rec["cylinders"]),
                "note": "treads D120 x 35 (2) + flange D140 (1), coaxial, axis body y; Chrono cylinder local z "
                        "rotated to body +y"}
    index = {
        "schema": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "frame": {
            "axes": "machine body axes: x forward = +Z_cad, y left = +X_cad, z up = +Y_cad",
            "origin": "CAD origin (body frame origin, CLAUDE.md)",
            "units": "m",
            "pose": "CAD pose; legs in the retracted state (CAD + legs.<leg>.retracted_offset_from_cad_m along +z); "
                    "auger (drive + tool) at the CAD position, the loader adds superstructure.auger_travel_m along +z",
            "rotation_body_from_cad": CAD_TO_BODY.tolist(),
        },
        "attach_rules": {
            "superstructure": "shape frame = body COG frame translated by -superstructure.mass_properties.com_m "
                              "(+ auger_travel_m z if moves_with_auger)",
            "leg": "shape frame = leg moving-part COG frame translated by -legs.<leg>.moving_part.com_m "
                   "(retracted COM, independent of the extension)",
        },
        "visual": visual,
        "collision": collision,
        "groups": state.get("groups", {}),
        "legs": state.get("legs", {}),
        "hulls": state.get("hulls", {}),
        "decompositions": state.get("decompositions", {}),
        "upper_rollers": state.get("upper_rollers", {}),
        "settings": {
            "superstructure_visual": {"drop_component_bbox_diag_mm": DROP_DIAG_MM, "quadric_reductions": Q_REDUCTIONS,
                                      "quadric_component_volume_tol": Q_VOL_TOL,
                                      "quadric_component_bbox_tol_mm": Q_BBOX_TOL_MM,
                                      "cluster_min_faces": CLUSTER_MIN_FACES, "cluster_cells_mm": CLUSTER_CELLS_MM,
                                      "track_split_x_cad_mm": TRACK_SPLIT_X_MM,
                                      "groups": {"mast": sorted(MAST_TOPS), "auger": sorted(AUGER_TOPS),
                                                 "crawler": [CRAWLER_TOP],
                                                 "deck": "every other top assembly except the jack cylinders",
                                                 "barrel_<leg>": "parts_classified group leg_barrel"}},
            "legs": {"pad_split_height_mm": PAD_SPLIT_HEIGHT_MM, "linear_deflection_mm": LEG_LINEAR_DEFLECTION_MM,
                     "angular_deflection_rad": LEG_ANGULAR_DEFLECTION_RAD,
                     "decimation_volume_tol": LEG_DECIMATE_VOL_TOL,
                     "pad_side_height_mm": state.get("pad_side_height_mm")},
            "decompose_targets": DECOMPOSE_TARGETS, "coacd_common": COACD_COMMON,
        },
        "provenance": {
            "script": source_record(Path(__file__)),
            "inputs": [source_record(p) for p in (CLASSIFIED_CSV, MESH_NPZ, MESH_INDEX_JSON, CRAWLER_COLLISION_JSON,
                                                  PARAMS_YAML, *[moving_brep_path(n) for n in LEG_ORDER],
                                                  *[s["barrel"] for s in LEG_SOURCE.values() if "barrel" in s],
                                                  *([UPPER_ROLLERS_CSV] if state.get("upper_rollers") else []))],
            "params_level_for_check": str(params.level),
            "mesh_source": state.get("mesh_source"),
            "cpu": cpu_info,
            "total_time_s": time.perf_counter() - started_s,
            "peak_wset_gb": _peak_gb(),
        },
    }
    INDEX_JSON.write_text(json.dumps(index, ensure_ascii=False, indent=1, default=_json_default), encoding="utf-8")
    log(f"wrote {rel(INDEX_JSON)}")


def _json_default(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, tuple):
        return list(obj)
    raise TypeError(type(obj))


def _peak_gb():
    try:
        import psutil

        return psutil.Process().memory_info().peak_wset / 1e9
    except Exception:  # noqa: BLE001
        return None


STATE_JSON = WORK_DIR / "state.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stage", nargs="*",
                        choices=("meshes", "legs", "hulls", "decompose", "upper_rollers", "index"))
    parser.add_argument("--only", nargs="*", help="decomposition targets (default all)")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--cpu", choices=("ecore", "pcore", "os"), default="ecore")
    parser.add_argument("--decompose-one", help=argparse.SUPPRESS)
    parser.add_argument("--leg-source", type=Path, help="JSON per-leg B-rep overrides (see module docstring)")
    parser.add_argument("--out-dir", type=Path, help="output folder instead of 01_cad/09_sim_shapes")
    parser.add_argument("--groups", nargs="*", help="stage meshes only for these groups")
    parser.add_argument("--hull-only", nargs="*", help="stage hulls only for these inputs")
    args = parser.parse_args()
    if args.out_dir:
        set_output_dir(args.out_dir)
    if args.leg_source:
        LEG_SOURCE.update(load_leg_source(args.leg_source))
    cpu_info = place_cpu(args.cpu)
    cpu_info.update(leg_source={k: {kk: rel(vv) for kk, vv in v.items()} for k, v in LEG_SOURCE.items()},
                    out_dir=rel(OUT_DIR))
    if args.decompose_one:
        decompose_one(args.decompose_one)
        return
    started = time.perf_counter()
    stages = args.stage or ["meshes", "legs", "hulls", "decompose", "upper_rollers", "index"]
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE_JSON.read_text(encoding="utf-8")) if STATE_JSON.exists() else {}

    def save():
        STATE_JSON.write_text(json.dumps(state, ensure_ascii=False, indent=1, default=_json_default), encoding="utf-8")

    if "meshes" in stages:
        stage_meshes(state, args.groups)
        save()
    if "legs" in stages:
        measure_side_height(state)
        stage_legs(state)
        save()
    if "hulls" in stages:
        stage_hulls(state, args.hull_only)
        save()
    if "decompose" in stages:
        stage_decompose(state, args.workers, args.cpu, args.only)
        save()
    if "upper_rollers" in stages:
        stage_upper_rollers(state)
        save()
    if "index" in stages:
        stage_index(state, started, cpu_info)
    log(f"done in {time.perf_counter() - started:.0f} s")


if __name__ == "__main__":
    main()
