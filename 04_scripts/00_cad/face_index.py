"""Query the face index of the whole assembly (``01_cad/07_faces/``, C5).

The index is written by ``build_face_index.py``. One row per face of every
occurrence; geometry in CAD world coordinates (``*_cad*``, mm, Y up) and in
body coordinates (``*_body*``, m; x = +Z_cad, y = +X_cad, z = +Y_cad, CAD
origin). The crawler (another model's undercarriage) is indexed only near the
ground unless the index was built with ``--crawler-all``.

Example (scripts in this folder add the folder to ``sys.path`` themselves)::

    import face_index

    # Upward horizontal faces of at least 0.01 m^2 in a body-frame window
    plates = face_index.query(
        kind="plane",
        normal_body=(0, 0, 1),
        tol_deg=5,
        area_min_mm2=1e4,
        bbox=((0.2, 0.4, 0.0), (0.5, 1.3, 0.1)),  # (min xyz, max xyz) body m
    )
    # Bores (concave cylinders) with their axis along body y, radius 20..40 mm
    bores = face_index.query(kind="cylinder", axis_body=(0, 1, 0), convex=False,
                             radius_mm=(20, 40))
    # Everything of one sub-assembly
    jack = face_index.query(top_assembly="FRONT JACK CYL:1")

Columns are described in ``build_face_index.py`` and in
``00_docs/00_cad/cad_review.md`` section 9.
"""

import functools
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cad_common import FACES_DIR

INSTANCE_FACES = FACES_DIR / "instance_faces.csv.gz"
PROTOTYPE_FACES = FACES_DIR / "prototype_faces.csv.gz"
SUMMARY_JSON = FACES_DIR / "face_index_summary.json"
CACHE_NAME = "07_faces"
XYZ = ("x", "y", "z")
BBOX_MODES = ("overlap", "inside", "centroid")

Vector = Sequence[float]
Box = tuple[Vector, Vector]


def _as_bool(column: pd.Series) -> pd.Series:
    mapping = {True: True, False: False, "True": True, "False": False}
    return column.map(mapping).astype("boolean")


@functools.cache
def load(prototypes: bool = False) -> pd.DataFrame:
    """The instance face index (default) or the prototype face table.

    The first call checks the cache manifest (stat only) and warns if the
    files changed since ``check_cache.py --write``.

    Raises:
        FileNotFoundError: If the index was not built yet.
    """
    _warn_if_stale()
    path = PROTOTYPE_FACES if prototypes else INSTANCE_FACES
    if not path.exists():
        raise FileNotFoundError(f"{path} (run build_face_index.py)")
    table = pd.read_csv(path, low_memory=False)
    table["convex"] = _as_bool(table["convex"])
    return table


def summary() -> dict:
    """Counts, crawler selection, timing and provenance of the index."""
    return json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))


def _unit(vector: Vector) -> np.ndarray:
    array = np.asarray(vector, dtype=float)
    norm = np.linalg.norm(array)
    if norm == 0:
        raise ValueError("direction must be non-zero")
    return array / norm


def _angle_mask(
    table: pd.DataFrame, field: str, direction: Vector, tol_deg: float, signed: bool
) -> np.ndarray:
    values = table[[f"{field}_{a}_body" for a in XYZ]].to_numpy()
    cosine = values @ _unit(direction)
    if not signed:
        cosine = np.abs(cosine)
    return np.nan_to_num(cosine, nan=-2.0) >= np.cos(np.radians(tol_deg))


def _range_mask(column: pd.Series, bounds: float | tuple[float, float]) -> np.ndarray:
    low, high = bounds if isinstance(bounds, tuple) else (bounds, bounds)
    return ((column >= low) & (column <= high)).to_numpy()


def _bbox_mask(table: pd.DataFrame, box: Box, mode: str) -> np.ndarray:
    low = np.asarray(box[0], dtype=float)
    high = np.asarray(box[1], dtype=float)
    if mode == "centroid":
        point = table[[f"centroid_{a}_body_m" for a in XYZ]].to_numpy()
        return np.all((point >= low) & (point <= high), axis=1)
    face_low = table[[f"bbox_min_{a}_body_m" for a in XYZ]].to_numpy()
    face_high = table[[f"bbox_max_{a}_body_m" for a in XYZ]].to_numpy()
    if mode == "inside":
        return np.all((face_low >= low) & (face_high <= high), axis=1)
    return np.all((face_high >= low) & (face_low <= high), axis=1)


def query(
    kind: str | Sequence[str] | None = None,
    *,
    normal_body: Vector | None = None,
    axis_body: Vector | None = None,
    tol_deg: float = 5.0,
    convex: bool | None = None,
    area_min_mm2: float | None = None,
    area_max_mm2: float | None = None,
    radius_mm: float | tuple[float, float] | None = None,
    bbox: Box | None = None,
    bbox_mode: str = "overlap",
    instance: str | None = None,
    product: str | None = None,
    top_assembly: str | None = None,
    include_uncertain: bool = True,
    table: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Filter the instance face index; all given conditions must hold.

    Args:
        kind: Face kind(s): ``plane``, ``cylinder``, ``cone``, ``sphere``,
            ``torus``, ``bspline``, ``bezier``, ``revolution``, ``extrusion``,
            ``offset``, ``other``.
        normal_body: Outward plane normal (body frame) within ``tol_deg``;
            only planes have a normal. The sign matters ((0, 0, 1) = faces
            looking up, i.e. top faces).
        axis_body: Axis of cylinders, cones, spheres, tori (body frame)
            within ``tol_deg``; sign ignored.
        tol_deg: Angle tolerance for ``normal_body`` and ``axis_body`` (deg).
        convex: For revolved faces: True = shaft or boss, False = bore or hole.
        area_min_mm2, area_max_mm2: Face area bounds (mm^2).
        radius_mm: Exact radius or ``(min, max)`` range (mm).
        bbox: ``((x_min, y_min, z_min), (x_max, y_max, z_max))`` in body m.
        bbox_mode: ``overlap`` (face bbox touches the box), ``inside`` (face
            bbox inside the box) or ``centroid`` (face centroid inside).
        instance, product, top_assembly: Regular expressions searched in
            ``instance_path``, ``product_name`` and ``top_assembly``.
        include_uncertain: False drops faces of face-only parts and faces
            outside solids (orientation not reliable).
        table: Table to filter (default: :func:`load`).

    Returns:
        Matching rows (a copy), in index order.

    Raises:
        ValueError: On an unknown ``bbox_mode`` or a zero direction.
    """
    if bbox_mode not in BBOX_MODES:
        raise ValueError(f"bbox_mode must be one of {BBOX_MODES}")
    data = load() if table is None else table
    mask = np.ones(len(data), dtype=bool)
    if kind is not None:
        kinds = [kind] if isinstance(kind, str) else list(kind)
        mask &= data["kind"].isin(kinds).to_numpy()
    if area_min_mm2 is not None:
        mask &= (data["area_mm2"] >= area_min_mm2).to_numpy()
    if area_max_mm2 is not None:
        mask &= (data["area_mm2"] <= area_max_mm2).to_numpy()
    if radius_mm is not None:
        mask &= _range_mask(data["radius_mm"], radius_mm)
    if convex is not None:
        mask &= (data["convex"] == convex).fillna(False).to_numpy(dtype=bool)
    if not include_uncertain:
        mask &= ~data["normal_uncertain"].to_numpy(dtype=bool)
    for column, pattern in (
        ("instance_path", instance),
        ("product_name", product),
        ("top_assembly", top_assembly),
    ):
        if pattern is not None:
            mask &= data[column].str.contains(re.compile(pattern), na=False).to_numpy()
    if bbox is not None:
        mask &= _bbox_mask(data, bbox, bbox_mode)
    if normal_body is not None:
        mask &= _angle_mask(data, "normal", normal_body, tol_deg, signed=True)
    if axis_body is not None:
        mask &= _angle_mask(data, "axis", axis_body, tol_deg, signed=False)
    return data[mask].copy()


def _warn_if_stale() -> None:
    try:
        from check_cache import warn_if_stale
    except ImportError:  # pragma: no cover - check_cache sits in the same folder
        return
    warn_if_stale([CACHE_NAME])
