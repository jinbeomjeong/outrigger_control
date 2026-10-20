"""Tessellate every part of the STEP assembly into one world-placed mesh cache.

Each prototype is meshed once with ``BRepMesh_IncrementalMesh`` and written as
binary STL by OpenCascade (fast C++ path), then loaded with trimesh and placed
with the occurrence transform. All part meshes go into one compressed archive:

* ``01_cad/05_meshes/parts_mesh.npz``: ``vertices`` (float32, mm, CAD world frame),
  ``faces`` (int32, indices local to each part), ``vertex_offsets`` and
  ``face_offsets`` (part i owns rows ``offsets[i]:offsets[i+1]``).
* ``01_cad/05_meshes/index.json``: part order (``instance_path``, identical to
  ``01_cad/01_parts/parts.csv``), mesh settings, STEP size and modification time.

``*.npz`` is git-ignored; the archive is a regenerable cache.

Frames: CAD root frame, mm, Y up.

Usage:
    python -I 04_scripts/00_cad/export_meshes.py [--force] [--linear-mm 3] [--angular-rad 0.5]
"""

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import trimesh
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.StlAPI import StlAPI_Writer
from OCC.Core.XCAFDoc import XCAFDoc_ShapeTool

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cad_common import MESH_DIR, STEP_PATH
from extract_parts import (
    PATH_SEPARATOR,
    _label_entry,
    _rotation_and_translation,
    collect_occurrences,
    load_document,
)

MESH_NPZ = MESH_DIR / "parts_mesh.npz"
MESH_INDEX_JSON = MESH_DIR / "index.json"


def _prototype_mesh(shape, linear_mm: float, angular_rad: float, work: Path):
    """Mesh a prototype shape in its own frame; returns (vertices, faces)."""
    BRepMesh_IncrementalMesh(shape, linear_mm, False, angular_rad, True)
    stl_path = work / "part.stl"
    writer = StlAPI_Writer()
    writer.SetASCIIMode(False)
    if not writer.Write(shape, str(stl_path)):
        return np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int64)
    mesh = trimesh.load_mesh(str(stl_path), file_type="stl", process=True)
    return np.asarray(mesh.vertices), np.asarray(mesh.faces)


def export(linear_mm: float, angular_rad: float) -> None:
    """Mesh all occurrences and write the archive and the index."""
    document = load_document(STEP_PATH)
    occurrences = collect_occurrences(document)
    cache: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    paths, vertex_blocks, face_blocks = [], [], []
    vertex_offsets, face_offsets = [0], [0]
    with tempfile.TemporaryDirectory() as work_dir:
        work = Path(work_dir)
        for number, occurrence in enumerate(occurrences):
            entry = _label_entry(occurrence.prototype)
            if entry not in cache:
                shape = XCAFDoc_ShapeTool.GetShape(occurrence.prototype)
                cache[entry] = _prototype_mesh(shape, linear_mm, angular_rad, work)
            local_vertices, faces = cache[entry]
            rotation, translation = _rotation_and_translation(occurrence.location)
            vertices = local_vertices @ rotation.T + translation
            if np.linalg.det(rotation) < 0:  # mirrored instance: keep outward normals
                faces = faces[:, ::-1]
            paths.append(PATH_SEPARATOR.join(occurrence.names))
            vertex_blocks.append(vertices.astype(np.float32))
            face_blocks.append(faces.astype(np.int32))
            vertex_offsets.append(vertex_offsets[-1] + len(vertices))
            face_offsets.append(face_offsets[-1] + len(faces))
            if number % 200 == 0:
                print(f"{number}/{len(occurrences)} parts", flush=True)
    MESH_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        MESH_NPZ,
        vertices=np.concatenate(vertex_blocks),
        faces=np.concatenate(face_blocks),
        vertex_offsets=np.array(vertex_offsets, dtype=np.int64),
        face_offsets=np.array(face_offsets, dtype=np.int64),
    )
    stat = STEP_PATH.stat()
    MESH_INDEX_JSON.write_text(
        json.dumps(
            {
                "step_path": str(STEP_PATH),
                "step_size_bytes": stat.st_size,
                "step_mtime": time.strftime(
                    "%Y-%m-%dT%H:%M:%S", time.localtime(stat.st_mtime)
                ),
                "mesher": "BRepMesh_IncrementalMesh (absolute deflection)",
                "linear_deflection_mm": linear_mm,
                "angular_deflection_rad": angular_rad,
                "frame": "CAD root frame, mm, Y up; instances already placed",
                "part_count": len(paths),
                "vertex_count": vertex_offsets[-1],
                "face_count": face_offsets[-1],
                "instance_paths": paths,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"{len(paths)} parts, {face_offsets[-1]} triangles -> {MESH_NPZ}")


def load_meshes() -> tuple[list[str], list[trimesh.Trimesh]]:
    """Read the archive back as one trimesh per part (same order as the index)."""
    index = json.loads(MESH_INDEX_JSON.read_text(encoding="utf-8"))
    data = np.load(MESH_NPZ)
    vertices, faces = data["vertices"], data["faces"]
    vertex_offsets, face_offsets = data["vertex_offsets"], data["face_offsets"]
    meshes = []
    for i in range(len(index["instance_paths"])):
        v = vertices[vertex_offsets[i] : vertex_offsets[i + 1]].astype(np.float64)
        f = faces[face_offsets[i] : face_offsets[i + 1]]
        meshes.append(trimesh.Trimesh(v, f, process=False))
    return index["instance_paths"], meshes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="re-export if cached")
    parser.add_argument("--linear-mm", type=float, default=3.0)
    parser.add_argument("--angular-rad", type=float, default=0.5)
    arguments = parser.parse_args()
    if MESH_NPZ.exists() and not arguments.force:
        print(f"cached: {MESH_NPZ} (use --force to rebuild)")
        return
    started_s = time.perf_counter()
    export(arguments.linear_mm, arguments.angular_rad)
    print(f"done in {time.perf_counter() - started_s:.0f} s")


if __name__ == "__main__":
    main()
