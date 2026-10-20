"""Convert the prototype B-rep cache between BinTools binary (.bbrep) and BRepTools ASCII (.brep).

No STEP read: each prototype file listed in ``01_cad/06_brep/prototypes.csv``
is read, written in the other format (no triangulation), read back and
compared with the source shape:

* topology counts (solids, shells, faces, edges, vertices) equal,
* vertex coordinates (exploration order) max abs difference,
* unit-density volume, centroid and inertia (``brepgprop.VolumeProperties``),

with the tolerances of ``verify_brep_cache.py``. Read times of both formats
are measured (warm OS file cache: both files were just read or written), split
into the crawler compound and the rest.

If every prototype passes, ``prototypes.csv`` (file, size, sha256),
``instances.csv`` (``prototype_file``) and ``cache_info.json`` switch to the
new format, ``format_conversion.json`` records the comparison, the source
files are deleted (``--keep-source`` keeps them) and the manifest entry
``06_brep`` is refreshed. On failure nothing is switched or deleted.

Usage:
    python -I 04_scripts/00_cad/convert_brep_cache.py --to binary [--keep-source]
    python -I 04_scripts/00_cad/convert_brep_cache.py --to ascii --keep-source
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import psutil
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GProp import GProp_GProps
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL, TopAbs_SOLID, TopAbs_VERTEX

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brep_cache import (
    BINARY_SUFFIX,
    CACHE_INFO_JSON,
    INSTANCES_CSV,
    PROTOTYPE_DIR,
    PROTOTYPES_CSV,
    prototype_file_name,
    read_brep,
    shape_vertices,
    write_brep,
)
from cad_common import BREP_DIR
from check_cache import sha256_file, write_manifest
from extract_parts import _count_subshapes, _inertia_matrix
from verify_brep_cache import TOLERANCE

CONVERSION_JSON = BREP_DIR / "format_conversion.json"
CONVERT_LOG = BREP_DIR / "convert.log"
CRAWLER_ENTRY = "0:1:1:746"
TOPOLOGY_TYPES = (TopAbs_SOLID, TopAbs_SHELL, TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX)


def _log(message: str) -> None:
    rss_gb = psutil.Process().memory_info().rss / 1e9
    line = f"[{time.strftime('%H:%M:%S')} | rss {rss_gb:5.2f} GB] {message}"
    print(line, flush=True)
    with CONVERT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _timed_read(path: Path):
    started = time.perf_counter()
    shape = read_brep(path)
    return shape, time.perf_counter() - started


def _mass_properties(shape) -> tuple[float, np.ndarray, np.ndarray]:
    properties = GProp_GProps()
    brepgprop.VolumeProperties(shape, properties)
    center = properties.CentreOfMass()
    return (
        properties.Mass(),
        np.array([center.X(), center.Y(), center.Z()]),
        _inertia_matrix(properties),
    )


def compare_shapes(source, target) -> dict:
    """Topology, vertex and mass-property differences between two shapes."""
    same_topology = [_count_subshapes(source, kind) for kind in TOPOLOGY_TYPES] == [
        _count_subshapes(target, kind) for kind in TOPOLOGY_TYPES
    ]
    source_vertices, target_vertices = shape_vertices(source), shape_vertices(target)
    if source_vertices.shape != target_vertices.shape:
        vertex_error = float("inf")
    else:
        vertex_error = (
            float(np.abs(source_vertices - target_vertices).max()) if len(source_vertices) else 0.0
        )
    volume_a, centroid_a, inertia_a = _mass_properties(source)
    volume_b, centroid_b, inertia_b = _mass_properties(target)
    inertia_norm = np.linalg.norm(inertia_a)
    return {
        "same_topology": same_topology,
        "vertex_abs_mm": vertex_error,
        "volume_rel": abs(volume_b - volume_a) / abs(volume_a) if volume_a else abs(volume_b),
        "centroid_abs_mm": float(np.abs(centroid_b - centroid_a).max()) if volume_a else 0.0,
        "inertia_rel": float(np.linalg.norm(inertia_b - inertia_a) / inertia_norm)
        if inertia_norm
        else 0.0,
    }


def _passes(result: dict) -> bool:
    return (
        result["same_topology"]
        and result["vertex_abs_mm"] <= TOLERANCE["vertex_abs_mm"]
        and result["volume_rel"] <= TOLERANCE["volume_relative"]
        and result["centroid_abs_mm"] <= TOLERANCE["centroid_abs_mm"]
        and result["inertia_rel"] <= TOLERANCE["inertia_relative_frobenius"]
    )


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def convert(to_binary: bool) -> tuple[dict, list[dict], dict[str, str]]:
    """Write every prototype in the target format; return report, rows, new names."""
    rows = _read_csv(PROTOTYPES_CSV)
    new_names: dict[str, str] = {}
    records = []
    for number, row in enumerate(rows, start=1):
        entry = row["prototype_entry"]
        source_path = PROTOTYPE_DIR / row["prototype_file"]
        target_name = prototype_file_name(entry, binary=to_binary)
        if target_name == row["prototype_file"]:
            raise SystemExit(f"{entry} is already in the requested format")
        target_path = PROTOTYPE_DIR / target_name
        source, source_read_s = _timed_read(source_path)
        write_brep(source, target_path)
        target, target_read_s = _timed_read(target_path)
        result = compare_shapes(source, target)
        records.append(
            {
                "entry": entry,
                "source_bytes": source_path.stat().st_size,
                "target_bytes": target_path.stat().st_size,
                "source_read_s": source_read_s,
                "target_read_s": target_read_s,
                "pass": _passes(result),
                **result,
            }
        )
        new_names[entry] = target_name
        del source, target
        if number % 100 == 0 or number == len(rows) or entry == CRAWLER_ENTRY:
            _log(f"  {number}/{len(rows)} converted (last {entry})")
    return _summarize(records, to_binary), rows, new_names


def _summarize(records: list[dict], to_binary: bool) -> dict:
    def block(selected: list[dict]) -> dict:
        return {
            "count": len(selected),
            "source_bytes": int(sum(item["source_bytes"] for item in selected)),
            "target_bytes": int(sum(item["target_bytes"] for item in selected)),
            "source_read_s": round(sum(item["source_read_s"] for item in selected), 3),
            "target_read_s": round(sum(item["target_read_s"] for item in selected), 3),
        }

    crawler = [item for item in records if item["entry"] == CRAWLER_ENTRY]
    rest = [item for item in records if item["entry"] != CRAWLER_ENTRY]
    failures = [item["entry"] for item in records if not item["pass"]]
    return {
        "direction": "ascii -> binary" if to_binary else "binary -> ascii",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "tolerance": TOLERANCE,
        "read_time_note": "warm OS file cache, single process, sequential reads",
        "crawler": block(crawler),
        "other_prototypes": block(rest),
        "all": block(records),
        "max_differences": {
            key: float(max(item[key] for item in records))
            for key in ("vertex_abs_mm", "volume_rel", "centroid_abs_mm", "inertia_rel")
        },
        "same_topology_count": int(sum(item["same_topology"] for item in records)),
        "failures": failures,
        "pass": not failures,
    }


def switch(rows: list[dict], new_names: dict[str, str], report: dict, keep_source: bool) -> None:
    """Point the tables at the new files, then delete the old ones."""
    old_paths = [PROTOTYPE_DIR / row["prototype_file"] for row in rows]
    for row in rows:
        row["prototype_file"] = new_names[row["prototype_entry"]]
        path = PROTOTYPE_DIR / row["prototype_file"]
        row["file_bytes"] = path.stat().st_size
        row["sha256"] = sha256_file(path)
    _write_csv(PROTOTYPES_CSV, rows)

    instances = _read_csv(INSTANCES_CSV)
    for row in instances:
        row["prototype_file"] = new_names[row["prototype_entry"]]
    _write_csv(INSTANCES_CSV, instances)

    info = json.loads(CACHE_INFO_JSON.read_text(encoding="utf-8"))
    binary = report["direction"].endswith("binary")
    info["brep_format"] = (
        "BinTools binary (.bbrep), BinTools_FormatVersion_VERSION_4, no triangulation"
        if binary
        else "BRepTools ASCII (.brep), TopTools_FormatVersion_VERSION_3, no triangulation"
    )
    info["prototype_bytes_total"] = int(sum(int(row["file_bytes"]) for row in rows))
    info["format_conversion"] = {
        "script": "04_scripts/00_cad/convert_brep_cache.py",
        "converted_at": report["created_at"],
        "direction": report["direction"],
        "report": CONVERSION_JSON.name,
    }
    CACHE_INFO_JSON.write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    if not keep_source:
        for path in old_paths:
            path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--to", choices=("binary", "ascii"), required=True)
    parser.add_argument("--keep-source", action="store_true", help="do not delete old files")
    arguments = parser.parse_args()
    to_binary = arguments.to == "binary"
    started_s = time.perf_counter()
    CONVERT_LOG.write_text("", encoding="utf-8")
    _log(f"converting prototypes to {arguments.to} ({BINARY_SUFFIX} = binary)")
    report, rows, new_names = convert(to_binary)
    report["total_s"] = round(time.perf_counter() - started_s, 1)
    report["peak_memory_gb"] = round(psutil.Process().memory_info().peak_wset / 1e9, 2)
    CONVERSION_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    _log(f"pass={report['pass']} max={report['max_differences']}")
    if not report["pass"]:
        raise SystemExit(f"conversion failed for {report['failures'][:5]}; nothing switched")
    switch(rows, new_names, report, arguments.keep_source)
    write_manifest(["06_brep"])
    _log(f"switched to {arguments.to}, manifest refreshed, {report['total_s']} s")


if __name__ == "__main__":
    main()
