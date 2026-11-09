"""Build the drawing mesh ``01_cad/05_meshes/render_mesh_v5.npz`` (V5, 2026-11-08).

The V5 drawing mesh replaces ``render_mesh.npz`` (fast_simplification decimation to a
300 000-triangle budget, analyze_mast.render_meshes up to 2026-11-08), whose decimation tore
holes into faces (grilles, thin covers) in every shaded CAD figure. V5 is:

* all 1214 parts of ``05_meshes/parts_mesh.npz`` (BRepMesh_IncrementalMesh, linear deflection
  3 mm, angular 0.5 rad, export_meshes.py; NOT decimated), re-ordered from index.json order to
  the ``01_parts/parts_classified.csv`` row order (matched by instance_path) so it drops in for
  the old render mesh;
* the perforated plates listed in :data:`FILL` drawn as slot-filled plates: union of the
  plate-parallel faces (|n . plate normal| > 0.9) projected to the plate plane, holes dropped
  (exterior rings only), extruded over the full plate thickness (PCA normal extent, snapped
  to the CAD axis within 2 deg). The two 33 mm roof-cover grilles tore in the decimated mesh;
  the five 3.2 mm sheets show as near-black hole grids when drawn undecimated.

The list was chosen (2026-11-08, Fig. 11(a) tear diagnosis) from a scan of all parts that are
thin in one CAD axis (<= 60 mm and <= 8 % of the second extent, >= 300 faces) with >= 20 holes
in the union of the plate-parallel faces; the auger rings, frame plates and engine housing side
plates of that scan stay as tessellated.

Same npz layout as the old render mesh: ``vertices`` float32 (CAD mm, Y up, CAD world frame),
``faces`` int32 (per-part local vertex indices), ``vertex_offsets`` / ``face_offsets`` int64
(1215 entries). The npz is written with explicitly fixed zip timestamps (1980-01-01, which is
also what numpy 2.5 savez_compressed writes), so a rebuild from the same inputs is
byte-identical. Checked 2026-11-09: this script reproduces the 2026-11-08 reference build
(sha256 4521b9f7..., session scratchpad fig11a_tear/build_v5_mesh.py) bit for bit
(``--reference``).

Inputs (read only):
    01_cad/05_meshes/parts_mesh.npz, index.json      export_meshes.py
    01_cad/01_parts/parts_classified.csv             analyze_parts.py
    01_cad/05_meshes/history/render_mesh.npz         old decimated mesh (optional, bbox report only)

Writes:
    01_cad/05_meshes/render_mesh_v5.npz   (about 43.5 MB, git ignored)
    01_cad/05_meshes/render_mesh_v5.json  build record (sources, filled plates, timings)

Usage (project root, Chrono-dev):
    python -I 04_scripts/00_cad/build_render_mesh_v5.py [--force] [--reference <render_mesh_v5.npz>]
    then  python -I 04_scripts/00_cad/check_cache.py --write --cache 05_meshes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
import trimesh
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cad_common import MESH_DIR, PARTS_DIR, PROJECT_ROOT

PARTS_MESH_NPZ = MESH_DIR / "parts_mesh.npz"
MESH_INDEX_JSON = MESH_DIR / "index.json"
CLASSIFIED_CSV = PARTS_DIR / "parts_classified.csv"
RENDER_V5_NPZ = MESH_DIR / "render_mesh_v5.npz"
RENDER_V5_JSON = MESH_DIR / "render_mesh_v5.json"
OLD_RENDER_NPZ = MESH_DIR / "history" / "render_mesh.npz"

ROOT = "REXOME33_Assy_r3(미니어쳐) / "
# Perforated plates drawn slot-filled (instance_path of parts_classified.csv).
FILL = tuple(ROOT + p for p in (
    "SIDE HOUSING_ROOF COVER:1 / 솔리드1:1",           # 33 mm grille, 338 slots
    "SIDE HOUSING_ROOF COVER:1 / 솔리드3:1",           # 33 mm grille, 664 slots
    "SIDE HOUSING_ROOF COVER:1 / 솔리드29:1",          # 3.2 mm sheet, 64 holes
    "CABIN HOUSING_R1:1 / COOLLER COVER_1:1",          # 3.2 mm sheet, 267 holes
    "CABIN HOUSING_R1:1 / COOLLER COVER_2:1",          # 3.2 mm sheet, 240 holes
    "SIDE HOUSING_(ENGINE)_R1:1 / ENGINE_COVER_2:1 / 솔리드60:1",  # 3.2 mm sheet, 173 holes
    "SIDE HOUSING_(ENGINE)_R1:1 / ENGINE_COVER_3:1 / 솔리드62:1",  # 3.2 mm sheet, 150 holes
))
ARRAY_NAMES = ("vertices", "faces", "vertex_offsets", "face_offsets")
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def filled_plate(v: np.ndarray, f: np.ndarray):
    """Slot-filled copy of a perforated plate (v in CAD mm, float64)."""
    centre = v.mean(0)
    _, _, vt = np.linalg.svd(v - centre, full_matrices=False)
    e1, e2, n = vt[0], vt[1], vt[2]
    # Snap to the nearest CAD axis if the PCA normal is within 2 deg of it (the plates are
    # axis-aligned in the CAD; louvres tilt the PCA normal by ~0.4 deg and the slab would then
    # overshoot the plate bbox by up to 9 mm).
    k = int(np.argmax(np.abs(n)))
    if np.abs(n[k]) > np.cos(np.radians(2.0)):
        n = np.eye(3)[k] * np.sign(n[k])
        e1 = np.eye(3)[(k + 1) % 3]
        e2 = np.cross(n, e1)
    w = (v - centre) @ n
    tri = v[f]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-30)
    flat = np.abs(fn @ n) > 0.9
    uv = (tri[flat] - centre) @ np.stack([e1, e2], 1)
    polys = [Polygon(t) for t in uv]
    union = shapely.union_all([p.buffer(0.01) for p in polys if p.area > 0])  # 0.01 mm weld
    geoms = list(union.geoms) if hasattr(union, "geoms") else [union]
    shells = [Polygon(g.exterior).buffer(-0.01) for g in geoms if g.area > 1.0]  # undo the weld
    vs, fs, off = [], [], 0
    for s in shells:
        m = trimesh.creation.extrude_polygon(s, float(np.ptp(w)))
        loc = m.vertices
        world = centre + loc[:, :1] * e1 + loc[:, 1:2] * e2 + (loc[:, 2:3] + w.min()) * n
        vs.append(world)
        fs.append(m.faces + off)
        off += len(world)
    nv, nf = np.vstack(vs), np.vstack(fs)
    tm = trimesh.Trimesh(nv, nf, process=True)
    info = {"plate_thickness_mm": round(float(np.ptp(w)), 3), "plate_normal_cad": np.round(n, 6).tolist(),
            "plate_parallel_faces": int(flat.sum()), "shells": len(shells),
            "slots_filled": int(sum(len(g.interiors) for g in geoms)),
            "face_area_with_slots_mm2": round(float(union.area), 1),
            "face_area_filled_mm2": round(float(sum(s.area for s in shells)), 1),
            "faces_before": int(len(f)), "faces_after": int(len(nf)),
            "bbox_full_mm": [np.round(v.min(0), 2).tolist(), np.round(v.max(0), 2).tolist()],
            "bbox_filled_mm": [np.round(nv.min(0), 2).tolist(), np.round(nv.max(0), 2).tolist()],
            "bbox_max_abs_diff_mm": round(float(max(np.abs(nv.min(0) - v.min(0)).max(),
                                                     np.abs(nv.max(0) - v.max(0)).max())), 3),
            "filled_watertight": bool(tm.is_watertight)}
    return nv, nf, info


def write_npz_deterministic(path: Path, arrays: dict[str, np.ndarray]) -> None:
    """np.savez_compressed layout (zip64 deflate entries ``<name>.npy``), timestamps fixed here
    rather than left to the numpy version."""
    tmp = path.with_name(path.stem + ".tmp.npz")
    with zipfile.ZipFile(tmp, mode="w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        for name, array in arrays.items():
            info = zipfile.ZipInfo(name + ".npy", date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            with archive.open(info, "w", force_zip64=True) as handle:
                np.lib.format.write_array(handle, np.asanyarray(array), allow_pickle=False)
    tmp.replace(path)


def cache_valid() -> bool:
    """True if render_mesh_v5.npz exists and is newer than the tessellation index."""
    return RENDER_V5_NPZ.exists() and RENDER_V5_NPZ.stat().st_mtime > MESH_INDEX_JSON.stat().st_mtime


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def build() -> dict:
    """Write render_mesh_v5.npz and render_mesh_v5.json; returns the build record."""
    started = time.perf_counter()
    tab = pd.read_csv(CLASSIFIED_CSV, encoding="utf-8-sig")
    paths = json.loads(MESH_INDEX_JSON.read_text(encoding="utf-8"))["instance_paths"]
    pos = {p: i for i, p in enumerate(paths)}
    if len(pos) != len(tab) or set(pos) != set(tab.instance_path):
        raise SystemExit("index.json and parts_classified.csv list different parts")
    perm = [pos[p] for p in tab.instance_path]
    with np.load(PARTS_MESH_NPZ) as d:
        v, f, vo, fo = d["vertices"], d["faces"], d["vertex_offsets"], d["face_offsets"]
    old = None
    if OLD_RENDER_NPZ.exists():
        with np.load(OLD_RENDER_NPZ) as d:
            old = d["vertices"], d["vertex_offsets"]
    vs, fs, plates, bbox_dev = [], [], {}, []
    for row, j in enumerate(perm):
        pv, pf = v[vo[j]:vo[j + 1]].astype(np.float64), f[fo[j]:fo[j + 1]]
        path = tab.instance_path.iloc[row]
        if old is not None:
            r = old[0][old[1][row]:old[1][row + 1]]
            if len(pv) and len(r):
                bbox_dev.append(max(np.abs(pv.min(0) - r.min(0)).max(), np.abs(pv.max(0) - r.max(0)).max()))
        if path in FILL:
            pv, pf, info = filled_plate(pv, pf)
            plates[path] = {"csv_row": row, **info}
        vs.append(pv.astype(np.float32))
        fs.append(np.asarray(pf, dtype=np.int32))
    if len(plates) != len(FILL):
        raise SystemExit(f"filled {len(plates)} of {len(FILL)} plates")
    MESH_DIR.mkdir(parents=True, exist_ok=True)
    write_npz_deterministic(RENDER_V5_NPZ, {
        "vertices": np.concatenate(vs), "faces": np.concatenate(fs),
        "vertex_offsets": np.cumsum([0] + [len(x) for x in vs]).astype(np.int64),
        "face_offsets": np.cumsum([0] + [len(x) for x in fs]).astype(np.int64)})
    sources = [PARTS_MESH_NPZ, MESH_INDEX_JSON, CLASSIFIED_CSV] + ([OLD_RENDER_NPZ] if old is not None else [])
    record = {
        "file": _relative(RENDER_V5_NPZ), "sha256": sha256_file(RENDER_V5_NPZ),
        "bytes": RENDER_V5_NPZ.stat().st_size,
        "script": _relative(Path(__file__)),
        "sources": {_relative(p): sha256_file(p) for p in sources},
        "mesher_of_parts_mesh": "BRepMesh_IncrementalMesh, linear deflection 3.0 mm, angular 0.5 rad (index.json)",
        "order": "parts_classified.csv row order (parts_mesh.npz is index.json order; matched by instance_path)",
        "units_frame": "vertices CAD mm, CAD world frame (Y up); body frame = CAD_TO_BODY (x = Z_cad, y = X_cad, z = Y_cad)",
        "zip_timestamps": "fixed 1980-01-01 00:00:00 (byte-reproducible rebuild)",
        "parts": len(vs), "faces": int(sum(len(x) for x in fs)), "vertices": int(sum(len(x) for x in vs)),
        "bbox_vs_old_render_mesh_max_mm": round(float(max(bbox_dev)), 2) if bbox_dev else None,
        "filled_plates": plates,
        "note": ("perforated grille (SIDE HOUSING_ROOF COVER 솔리드1, 솔리드3) and perforated sheet covers "
                 "(ROOF COVER 솔리드29, CABIN HOUSING COOLLER COVER_1/_2, ENGINE_COVER_2/_3) drawn as "
                 "slot-filled plates"),
        "replaces": "01_cad/05_meshes/render_mesh.npz (decimated, now history/render_mesh.npz)",
        "build_s": round(time.perf_counter() - started, 1),
    }
    RENDER_V5_JSON.write_text(json.dumps(record, indent=1, ensure_ascii=False), encoding="utf-8")
    return record


def compare_reference(reference: Path) -> dict:
    """Array-level and zip-entry-level comparison with another render_mesh_v5.npz build.

    ``bit_identical_after_timestamp_rewrite``: our arrays re-zipped with the reference's
    per-entry timestamps (in memory) give the reference file's sha256.
    """
    import io

    result = {"reference": str(reference), "reference_sha256": sha256_file(reference),
              "ours_sha256": sha256_file(RENDER_V5_NPZ)}
    result["bit_identical"] = result["reference_sha256"] == result["ours_sha256"]
    with np.load(reference) as a, np.load(RENDER_V5_NPZ) as b:
        result["arrays"] = {name: {"equal": bool(np.array_equal(a[name], b[name])),
                                   "dtype": [str(a[name].dtype), str(b[name].dtype)],
                                   "shape": [list(a[name].shape), list(b[name].shape)]}
                            for name in ARRAY_NAMES}
    result["arrays_equal"] = all(item["equal"] for item in result["arrays"].values())
    with zipfile.ZipFile(reference) as za, zipfile.ZipFile(RENDER_V5_NPZ) as zb:
        ia, ib = za.infolist(), zb.infolist()
        result["zip_entries"] = [
            {"name": x.filename, "crc_equal": x.CRC == y.CRC, "compressed_equal": x.compress_size == y.compress_size,
             "reference_date_time": list(x.date_time), "ours_date_time": list(y.date_time)}
            for x, y in zip(ia, ib, strict=True)]
        stamps = {x.filename: x.date_time for x in ia}
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as out:
            for y in ib:
                info = zipfile.ZipInfo(y.filename, date_time=stamps[y.filename])
                info.compress_type = zipfile.ZIP_DEFLATED
                with out.open(info, "w", force_zip64=True) as handle, zb.open(y) as src:
                    for block in iter(lambda: src.read(1 << 20), b""):
                        handle.write(block)
    result["sha256_after_timestamp_rewrite"] = hashlib.sha256(buffer.getvalue()).hexdigest()
    result["bit_identical_after_timestamp_rewrite"] = (
        result["sha256_after_timestamp_rewrite"] == result["reference_sha256"])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="rebuild even if the cache is newer than index.json")
    parser.add_argument("--reference", type=Path, help="compare the result with this render_mesh_v5.npz")
    arguments = parser.parse_args()
    if cache_valid() and not arguments.force:
        print(f"cached: {RENDER_V5_NPZ} (use --force to rebuild)")
        record = json.loads(RENDER_V5_JSON.read_text(encoding="utf-8")) if RENDER_V5_JSON.exists() else {}
    else:
        record = build()
    summary = {key: record.get(key) for key in ("file", "sha256", "bytes", "parts", "faces", "vertices",
                                                 "bbox_vs_old_render_mesh_max_mm", "build_s")}
    if arguments.reference:
        summary["reference_check"] = compare_reference(arguments.reference)
    print(json.dumps(summary, indent=1, ensure_ascii=True))
    if arguments.reference and not summary["reference_check"]["arrays_equal"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
