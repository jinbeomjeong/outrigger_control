"""Verify the B-rep cache (01_cad/06_brep) against parts.csv and the older B-rep caches.

Reads only cache files (no STEP read). Checks:

1. Keys: ``instance_path`` set, ``prototype_entry`` and ``product_name`` per
   row equal to ``01_cad/01_parts/parts.csv``.
2. Mass properties of every instance recomputed from the cache (unit density,
   ``brepgprop.VolumeProperties`` on the prototype, then the placement):
   volume, world centroid, world inertia about the centroid, world bbox
   (``brepbndlib.AddOptimal`` on the placed shape) against ``parts.csv``.
3. Assembly bbox (union of instance bboxes) against ``parts.csv``.
4. Identity with the world-placed B-rep files of ``02_legs/legs`` (8 files)
   and ``04_mast/mast`` (index.json): topology counts and vertex coordinates.
5. Query timing: one part, all prototypes, one compound of all instances.

Writes ``01_cad/06_brep/verification.json``.

Usage:
    python -I 04_scripts/00_cad/verify_brep_cache.py
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GProp import GProp_GProps
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_VERTEX

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brep_cache
from cad_common import BREP_DIR, LEGS_DIR, MAST_DIR, PARTS_CSV
from extract_parts import _count_subshapes, _inertia_matrix
from inspect_legs import _safe_file_stem

VERIFICATION_JSON = BREP_DIR / "verification.json"
LEG_BREP_DIR = LEGS_DIR / "legs"
MAST_INDEX_JSON = MAST_DIR / "mast" / "index.json"

# Acceptance (relative to the parts.csv value, or absolute in mm).
TOLERANCE = {
    "volume_relative": 1e-6,
    "centroid_abs_mm": 1e-6,
    "inertia_relative_frobenius": 1e-6,
    "bbox_abs_mm": 1e-6,
    "vertex_abs_mm": 1e-9,
}
# Parts with |volume| below this (surface-only bodies) skip the centroid and
# inertia comparison, whose relative value is meaningless there.
MIN_VOLUME_MM3 = 1e-3
GROUP_PATTERNS = {
    "legs (JACK CYL)": r"JACK CYL",
    "mast (MAST)": r"MAST",
    "auger (DRIVE AUGER ASSY / AUGER TOOL)": r"DRIVE AUGER ASSY|AUGER TOOL",
}
INERTIA_COLUMNS = ("xx", "yy", "zz", "xy", "xz", "yz")


def _prototype_properties() -> dict[str, tuple[float, np.ndarray, np.ndarray]]:
    """Unit-density volume, centroid and inertia of every prototype (own frame)."""
    result = {}
    for row in brep_cache.prototypes():
        properties = GProp_GProps()
        brepgprop.VolumeProperties(brep_cache.load_prototype(row["prototype_entry"]), properties)
        center = properties.CentreOfMass()
        result[row["prototype_entry"]] = (
            properties.Mass(),
            np.array([center.X(), center.Y(), center.Z()]),
            _inertia_matrix(properties),
        )
    return result


def _bbox(shape) -> np.ndarray:
    box = Bnd_Box()
    brepbndlib.AddOptimal(shape, box, False, False)
    return np.full(6, np.nan) if box.IsVoid() else np.array(box.Get())


def _inertia_from_row(row) -> np.ndarray:
    values = {key: getattr(row, f"inertia_{key}_mm5") for key in INERTIA_COLUMNS}
    return np.array(
        [
            [values["xx"], values["xy"], values["xz"]],
            [values["xy"], values["yy"], values["yz"]],
            [values["xz"], values["yz"], values["zz"]],
        ]
    )


def compare_parts(parts: pd.DataFrame, properties: dict) -> pd.DataFrame:
    """One row per instance with the deviations from parts.csv."""
    records = []
    for row in parts.itertuples(index=False):
        instance = brep_cache.get_instance(row.instance_path)
        volume, centroid_local, inertia_local = properties[instance.prototype_entry]
        transform = instance.transform
        rotation = transform[:3, :3]
        centroid = rotation @ centroid_local + transform[:3, 3]
        inertia = rotation @ inertia_local @ rotation.T
        reference_inertia = _inertia_from_row(row)
        bbox = _bbox(brep_cache.load_part(row.instance_path))
        reference_bbox = np.array(
            [getattr(row, f"bbox_{side}_{axis}_mm") for side in ("min", "max") for axis in "xyz"]
        )
        solid = abs(row.volume_mm3) > MIN_VOLUME_MM3
        records.append(
            {
                "instance_path": row.instance_path,
                "volume_mm3": volume,
                "volume_rel": abs(volume - row.volume_mm3) / max(abs(row.volume_mm3), 1e-300)
                if solid
                else abs(volume - row.volume_mm3),
                "centroid_abs_mm": float(
                    np.abs(
                        centroid - [row.centroid_x_mm, row.centroid_y_mm, row.centroid_z_mm]
                    ).max()
                )
                if solid
                else np.nan,
                "inertia_rel": float(
                    np.linalg.norm(inertia - reference_inertia) / np.linalg.norm(reference_inertia)
                )
                if solid
                else np.nan,
                "bbox_abs_mm": float(np.nanmax(np.abs(bbox - reference_bbox)))
                if np.isfinite(reference_bbox).all()
                else np.nan,
                "solid": solid,
                "bbox": bbox,
            }
        )
    return pd.DataFrame(records)


def _stats(frame: pd.DataFrame) -> dict:
    solid = frame[frame["solid"]]
    return {
        "instances": len(frame),
        "with_volume": len(solid),
        "volume_rel_max": float(solid["volume_rel"].max()) if len(solid) else None,
        "centroid_abs_mm_max": float(solid["centroid_abs_mm"].max()) if len(solid) else None,
        "inertia_rel_max": float(solid["inertia_rel"].max()) if len(solid) else None,
        "bbox_abs_mm_max": float(frame["bbox_abs_mm"].max()),
        "zero_volume_abs_volume_max_mm3": float(frame.loc[~frame["solid"], "volume_rel"].max())
        if (~frame["solid"]).any()
        else None,
    }


def _passes(stats: dict) -> bool:
    return (
        stats["volume_rel_max"] <= TOLERANCE["volume_relative"]
        and stats["centroid_abs_mm_max"] <= TOLERANCE["centroid_abs_mm"]
        and stats["inertia_rel_max"] <= TOLERANCE["inertia_relative_frobenius"]
        and stats["bbox_abs_mm_max"] <= TOLERANCE["bbox_abs_mm"]
    )


def _topology(shape) -> tuple[int, int, int]:
    return tuple(
        _count_subshapes(shape, kind) for kind in (TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX)
    )


def compare_world_breps(pairs: list[tuple[str, Path]]) -> dict:
    """Compare cached placed parts with existing world-placed B-rep files."""
    rows = []
    for instance_path, path in pairs:
        cached = brep_cache.load_part(instance_path)
        existing = brep_cache.read_brep(path)
        cached_vertices = brep_cache.shape_vertices(cached)
        existing_vertices = brep_cache.shape_vertices(existing)
        same_count = cached_vertices.shape == existing_vertices.shape
        deviation = (
            float(np.abs(cached_vertices - existing_vertices).max())
            if same_count and len(cached_vertices)
            else (0.0 if same_count else np.inf)
        )
        rows.append(
            {
                "file": path.name,
                "same_topology_counts": _topology(cached) == _topology(existing),
                "vertex_abs_mm_max": deviation,
            }
        )
    frame = pd.DataFrame(rows)
    return {
        "files": len(frame),
        "same_topology_counts": int(frame["same_topology_counts"].sum()),
        "vertex_abs_mm_max": float(frame["vertex_abs_mm_max"].max()),
        "pass": bool(
            frame["same_topology_counts"].all()
            and frame["vertex_abs_mm_max"].max() <= TOLERANCE["vertex_abs_mm"]
        ),
    }


def leg_pairs() -> list[tuple[str, Path]]:
    pairs = []
    for instance in brep_cache.iter_instances(r"JACK CYL"):
        path = LEG_BREP_DIR / f"{_safe_file_stem(instance.instance_path.split(' / '))}.brep"
        if path.exists():
            pairs.append((instance.instance_path, path))
    return pairs


def mast_pairs() -> list[tuple[str, Path]]:
    index = json.loads(MAST_INDEX_JSON.read_text(encoding="utf-8"))["parts"]
    return [(path, MAST_INDEX_JSON.parent / name) for path, name in index.items()]


def timing() -> dict:
    """Cold-cache query times (seconds) from the B-rep cache."""
    brep_cache.clear_memory_cache()
    started = time.perf_counter()
    jack = next(brep_cache.iter_instances(r"FRONT JACK CYL:1"))
    brep_cache.load_part(jack.instance_path)
    one_part_s = time.perf_counter() - started

    started = time.perf_counter()
    for row in brep_cache.prototypes():
        brep_cache.load_prototype(row["prototype_entry"])
    all_prototypes_s = time.perf_counter() - started

    started = time.perf_counter()
    brep_cache.load_compound(brep_cache.instances())
    compound_s = time.perf_counter() - started
    return {
        "one_part_cold_including_index_s": round(one_part_s, 3),
        "all_prototypes_cold_s": round(all_prototypes_s, 2),
        "compound_all_instances_warm_s": round(compound_s, 3),
    }


def main() -> None:
    started_s = time.perf_counter()
    report: dict = {"tolerance": TOLERANCE, "min_volume_mm3": MIN_VOLUME_MM3}
    report["timing"] = timing()
    print(f"timing {report['timing']}", flush=True)

    parts = pd.read_csv(PARTS_CSV, encoding="utf-8-sig")
    cache = pd.read_csv(brep_cache.INSTANCES_CSV, encoding="utf-8-sig")
    joined = parts.merge(
        cache, on="instance_path", how="outer", indicator=True, suffixes=("", "_c")
    )
    both = joined[joined["_merge"] == "both"]
    report["keys"] = {
        "parts_rows": len(parts),
        "cache_rows": len(cache),
        "only_in_parts": int((joined["_merge"] == "left_only").sum()),
        "only_in_cache": int((joined["_merge"] == "right_only").sum()),
        "prototype_entry_mismatch": int(
            (both["prototype_entry"] != both["prototype_entry_c"]).sum()
        ),
        "product_name_mismatch": int((both["product_name"] != both["product_name_c"]).sum()),
        "is_mirrored_mismatch": int((both["is_mirrored"] != both["is_mirrored_c"]).sum()),
    }
    print(f"keys {report['keys']}", flush=True)

    phase_s = time.perf_counter()
    properties = _prototype_properties()
    report["prototype_properties_s"] = round(time.perf_counter() - phase_s, 1)
    phase_s = time.perf_counter()
    deviations = compare_parts(parts, properties)
    report["instance_compare_s"] = round(time.perf_counter() - phase_s, 1)

    overall = _stats(deviations)
    overall["pass"] = _passes(overall)
    report["mass_properties_all"] = overall
    groups = {}
    for label, pattern in GROUP_PATTERNS.items():
        mask = deviations["instance_path"].str.contains(pattern, regex=True)
        groups[label] = _stats(deviations[mask])
    report["mass_properties_groups"] = groups
    worst = deviations[deviations["solid"]].nlargest(3, "volume_rel")
    report["worst_volume_rel"] = worst[["instance_path", "volume_rel"]].to_dict("records")

    boxes = np.vstack(deviations["bbox"].to_numpy())
    union = np.concatenate([np.nanmin(boxes[:, :3], axis=0), np.nanmax(boxes[:, 3:], axis=0)])
    reference = np.concatenate(
        [
            parts[[f"bbox_min_{axis}_mm" for axis in "xyz"]].min().to_numpy(),
            parts[[f"bbox_max_{axis}_mm" for axis in "xyz"]].max().to_numpy(),
        ]
    )
    report["assembly_bbox_mm"] = {
        "cache": union.round(4).tolist(),
        "parts_csv": reference.round(4).tolist(),
        "abs_max_mm": float(np.abs(union - reference).max()),
    }
    print(f"mass properties {overall}", flush=True)

    report["legs_identity"] = compare_world_breps(leg_pairs())
    print(f"legs {report['legs_identity']}", flush=True)
    report["mast_identity"] = compare_world_breps(mast_pairs())
    print(f"mast {report['mast_identity']}", flush=True)

    report["pass"] = bool(
        overall["pass"]
        and report["assembly_bbox_mm"]["abs_max_mm"] <= TOLERANCE["bbox_abs_mm"]
        and report["legs_identity"]["pass"]
        and report["mast_identity"]["pass"]
        and not any(value for key, value in report["keys"].items() if not key.endswith("rows"))
    )
    report["total_s"] = round(time.perf_counter() - started_s, 1)
    VERIFICATION_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"pass={report['pass']} in {report['total_s']} s -> {VERIFICATION_JSON}")


if __name__ == "__main__":
    main()
