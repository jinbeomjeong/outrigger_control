"""Build the B-rep cache: every prototype of the STEP assembly as a native B-rep file.

The STEP file is read once (XCAF, same reader settings as ``extract_parts.py``
so the OCAF prototype entries match ``01_cad/01_parts/parts.csv``). Each
prototype (product definition) is written once in its own frame; each leaf
occurrence gets one row with its placement. Outputs in ``01_cad/06_brep/``:

* ``prototypes/<entry>.bbrep``: BinTools binary, format version 4, without
  triangulation. Each file is read back and its vertices compared with the
  in-memory shape (write precision check).
* ``prototypes.csv``: entry, file, product name, instance count, material,
  density, solid/shell/face/edge/vertex counts, file size and sha256,
  read-back vertex error.
* ``instances.csv``: ``instance_path`` and ``prototype_entry`` (keys of
  ``parts.csv``), names, depth, ``is_mirrored``, ``scale`` and the 3x4
  placement matrix ``m00 .. m23`` (world <- prototype, CAD mm, Y up).
* ``cache_info.json``: settings, counts, timings, peak memory, STEP size and
  modification time.
* ``build.log``: progress log (git-ignored) for monitoring long runs.

At the end the ``06_brep`` entry of ``01_cad/cache_manifest.json`` is
refreshed (``check_cache.py``).

Load the cache with ``brep_cache.py``; verify it with ``verify_brep_cache.py``.

Usage:
    python -I 04_scripts/00_cad/build_brep_cache.py [--force]
"""

import argparse
import csv
import hashlib
import json
import platform
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import psutil
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL, TopAbs_SOLID, TopAbs_VERTEX
from OCC.Core.XCAFDoc import XCAFDoc_ShapeTool

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brep_cache import (
    CACHE_INFO_JSON,
    INSTANCES_CSV,
    MATRIX_COLUMNS,
    PROTOTYPE_DIR,
    PROTOTYPES_CSV,
    prototype_file_name,
    read_brep,
    shape_vertices,
    write_brep,
)
from cad_common import BREP_DIR, PROJECT_ROOT, STEP_PATH
from check_cache import environment_versions, write_manifest
from extract_parts import (
    PATH_SEPARATOR,
    _count_subshapes,
    _label_entry,
    _label_name,
    _read_material,
    collect_occurrences,
    load_document,
)

BUILD_LOG = BREP_DIR / "build.log"
PROGRESS_EVERY_PROTOTYPES = 50


class Log:
    """Print progress to stdout and append it to ``build.log`` with time and memory."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.started_s = time.perf_counter()
        self.process = psutil.Process()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    def __call__(self, message: str) -> None:
        elapsed_s = time.perf_counter() - self.started_s
        rss_gb = self.process.memory_info().rss / 1e9
        line = f"[{elapsed_s:7.1f} s | rss {rss_gb:5.2f} GB] {message}"
        print(line, flush=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def peak_memory_gb(self) -> float:
        """Peak working set of this process (Windows ``peak_wset``)."""
        info = self.process.memory_info()
        return getattr(info, "peak_wset", info.rss) / 1e9


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _matrix_values(location) -> tuple[list[float], float]:
    """Row-major 3x4 matrix (world <- prototype) and scale factor of a location."""
    transformation = location.Transformation()
    values = [transformation.Value(row, column) for row in (1, 2, 3) for column in (1, 2, 3, 4)]
    return values, transformation.ScaleFactor()


def _write_prototype(shape, path: Path) -> float:
    """Write one prototype, read it back, return the max vertex deviation (mm)."""
    write_brep(shape, path)
    original = shape_vertices(shape)
    reread = shape_vertices(read_brep(path))
    if original.shape != reread.shape:
        raise RuntimeError(f"vertex count changed after write: {path}")
    return float(np.abs(original - reread).max()) if len(original) else 0.0


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build(log: Log) -> dict:
    """Read the STEP file and write prototypes, tables and ``cache_info.json``."""
    timings: dict[str, float] = {}
    started_s = time.perf_counter()
    log(f"reading {STEP_PATH.name} ({STEP_PATH.stat().st_size / 1e6:.1f} MB)")
    document = load_document(STEP_PATH)
    timings["step_read_and_transfer_s"] = time.perf_counter() - started_s
    log(f"document ready in {timings['step_read_and_transfer_s']:.0f} s")

    phase_s = time.perf_counter()
    occurrences = collect_occurrences(document)
    groups: dict[str, list] = {}
    for occurrence in occurrences:
        groups.setdefault(_label_entry(occurrence.prototype), []).append(occurrence)
    timings["traverse_s"] = time.perf_counter() - phase_s
    log(f"{len(occurrences)} leaf occurrences, {len(groups)} prototypes")

    if PROTOTYPE_DIR.exists():
        shutil.rmtree(PROTOTYPE_DIR)
    PROTOTYPE_DIR.mkdir(parents=True)

    phase_s = time.perf_counter()
    prototype_rows: list[dict] = []
    instance_rows: list[dict] = []
    for done, (entry, group) in enumerate(groups.items(), start=1):
        label = group[0].prototype
        shape = XCAFDoc_ShapeTool.GetShape(label)
        file_name = prototype_file_name(entry)
        path = PROTOTYPE_DIR / file_name
        deviation_mm = _write_prototype(shape, path)
        material, density = _read_material(label)
        prototype_rows.append(
            {
                "prototype_entry": entry,
                "prototype_file": file_name,
                "product_name": _label_name(label),
                "instance_count": len(group),
                "material": material,
                "density_g_cm3": density,
                "solid_count": _count_subshapes(shape, TopAbs_SOLID),
                "shell_count": _count_subshapes(shape, TopAbs_SHELL),
                "face_count": _count_subshapes(shape, TopAbs_FACE),
                "edge_count": _count_subshapes(shape, TopAbs_EDGE),
                "vertex_count": _count_subshapes(shape, TopAbs_VERTEX),
                "file_bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "readback_max_vertex_error_mm": deviation_mm,
            }
        )
        for occurrence in group:
            values, scale = _matrix_values(occurrence.location)
            rotation = np.reshape(values, (3, 4))[:, :3]
            instance_rows.append(
                {
                    "instance_path": PATH_SEPARATOR.join(occurrence.names),
                    "prototype_entry": entry,
                    "prototype_file": file_name,
                    "product_name": _label_name(label),
                    "instance_name": occurrence.names[-1],
                    "top_assembly": occurrence.names[1] if len(occurrence.names) > 1 else "",
                    "depth": len(occurrence.names) - 1,
                    "is_mirrored": bool(np.linalg.det(rotation) < 0),
                    "scale": scale,
                    **dict(zip(MATRIX_COLUMNS, values, strict=True)),
                }
            )
        if done % PROGRESS_EVERY_PROTOTYPES == 0 or done == len(groups):
            log(f"  wrote {done}/{len(groups)} prototypes")
    timings["write_prototypes_s"] = time.perf_counter() - phase_s

    instance_rows.sort(key=lambda row: row["instance_path"])
    prototype_rows.sort(key=lambda row: [int(part) for part in row["prototype_entry"].split(":")])
    _write_csv(INSTANCES_CSV, instance_rows)
    _write_csv(PROTOTYPES_CSV, prototype_rows)
    timings["total_s"] = time.perf_counter() - started_s

    step_stat = STEP_PATH.stat()
    info = {
        "description": "Prototype B-rep cache of the STEP assembly (CAD root frame, mm, Y up)",
        "generator": str(Path(__file__).resolve().relative_to(PROJECT_ROOT).as_posix()),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "step": {
            "path": STEP_PATH.name,
            "size_bytes": step_stat.st_size,
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(step_stat.st_mtime)),
            "mtime_ns": step_stat.st_mtime_ns,
        },
        "reader": "STEPCAFControl_Reader (names and materials on, colors and layers off)",
        "brep_format": "BinTools binary (.bbrep), format VERSION_4, no triangulation",
        "frame": "prototype files: prototype frame; instances.csv m00..m23: world <- prototype",
        "prototype_count": len(prototype_rows),
        "instance_count": len(instance_rows),
        "mirrored_instance_count": sum(row["is_mirrored"] for row in instance_rows),
        "non_unit_scale_count": sum(abs(row["scale"] - 1.0) > 1e-12 for row in instance_rows),
        "prototype_bytes_total": sum(row["file_bytes"] for row in prototype_rows),
        "readback_max_vertex_error_mm": max(
            row["readback_max_vertex_error_mm"] for row in prototype_rows
        ),
        "timings_s": {key: round(value, 2) for key, value in timings.items()},
        "peak_memory_gb": round(log.peak_memory_gb(), 2),
        "machine": platform.node(),
        "environment": environment_versions(),
    }
    CACHE_INFO_JSON.write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    return info


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="rebuild even if cached")
    arguments = parser.parse_args()
    if INSTANCES_CSV.exists() and not arguments.force:
        print(f"cached: {INSTANCES_CSV} (use --force to rebuild)")
        return
    log = Log(BUILD_LOG)
    info = build(log)
    log(
        f"{info['prototype_count']} prototypes ({info['prototype_bytes_total'] / 1e6:.1f} MB), "
        f"{info['instance_count']} instances, peak memory {info['peak_memory_gb']} GB, "
        f"total {info['timings_s']['total_s']:.0f} s"
    )
    write_manifest(["06_brep"])
    log("manifest entry 06_brep refreshed")


if __name__ == "__main__":
    main()
