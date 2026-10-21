"""Load parts of the STEP assembly from the B-rep cache, without reading the STEP file.

The cache in ``01_cad/06_brep/`` is written by ``build_brep_cache.py``:

* ``prototypes/<entry>.bbrep``: one file per prototype (product definition) in
  its own frame, BinTools binary format, no triangulation. ``<entry>`` is the
  OCAF label entry with ``:`` replaced by ``_`` (``0:1:1:375`` ->
  ``0_1_1_375.bbrep``). ``convert_brep_cache.py`` converts the folder between
  binary and BRepTools ASCII (``.brep``); both are readable here, the file
  listed in ``prototypes.csv`` is the one loaded.
* ``prototypes.csv``: one row per prototype (entry, file, product name,
  instance count, material, topology counts, file hash).
* ``derived/``: small use-specific results (e.g. crawler ground faces and
  collision shapes) made from prototype files by other scripts.
* ``instances.csv``: one row per leaf occurrence. ``instance_path`` and
  ``prototype_entry`` are the keys of ``01_cad/01_parts/parts.csv``. The
  placement ``m00 .. m23`` is the 3x4 affine matrix (row-major) that maps
  prototype coordinates to CAD world coordinates (mm, Y up).

Frames: CAD root frame, mm, Y up. Placed shapes are identical to the shapes
``extract_parts.py`` measured (``prototype.Moved(occurrence location)``).

Example (scripts in this folder add the folder to ``sys.path`` themselves)::

    import brep_cache

    jacks = list(brep_cache.iter_instances(r"JACK CYL"))
    shape = brep_cache.load_part(jacks[0].instance_path)          # placed, mm
    local = brep_cache.load_part(jacks[0].prototype_entry, placed=False)
    compound = brep_cache.load_compound(jacks)
"""

import csv
import functools
import re
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from OCC.Core.BinTools import BinTools_FormatVersion_VERSION_4, bintools
from OCC.Core.BRep import BRep_Builder, BRep_Tool
from OCC.Core.BRepTools import breptools
from OCC.Core.gp import gp_Trsf
from OCC.Core.TopAbs import TopAbs_VERTEX
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.TopoDS import TopoDS_Compound, TopoDS_Shape, topods
from OCC.Core.TopTools import TopTools_FormatVersion_VERSION_3

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cad_common import BREP_DIR, PROJECT_ROOT

PROTOTYPE_DIR = BREP_DIR / "prototypes"
PROTOTYPES_CSV = BREP_DIR / "prototypes.csv"
INSTANCES_CSV = BREP_DIR / "instances.csv"
CACHE_INFO_JSON = BREP_DIR / "cache_info.json"
DERIVED_DIR = BREP_DIR / "derived"
CRAWLER_PARTS_CSV = DERIVED_DIR / "crawler" / "crawler_contact_parts.csv"
CRAWLER_UPPER_ROLLERS_CSV = DERIVED_DIR / "crawler" / "crawler_upper_rollers.csv"
CACHE_NAME = "06_brep"
BINARY_SUFFIX = ".bbrep"  # BinTools binary (default)
ASCII_SUFFIX = ".brep"  # BRepTools ASCII (legacy, legs/mast caches)

# Row-major 3x4 placement matrix columns of instances.csv.
MATRIX_COLUMNS = tuple(f"m{row}{column}" for row in range(3) for column in range(4))


@dataclass(frozen=True)
class Instance:
    """One leaf occurrence of the assembly as stored in ``instances.csv``."""

    instance_path: str
    prototype_entry: str
    prototype_file: str
    product_name: str
    instance_name: str
    top_assembly: str
    depth: int
    is_mirrored: bool
    matrix: tuple[float, ...]  # 12 values, row-major 3x4, world <- prototype (mm)

    @property
    def transform(self) -> np.ndarray:
        """4x4 homogeneous placement (world <- prototype, mm)."""
        return np.vstack([np.reshape(self.matrix, (3, 4)), [0.0, 0.0, 0.0, 1.0]])

    def trsf(self) -> gp_Trsf:
        """Placement as an OpenCascade transformation."""
        transformation = gp_Trsf()
        transformation.SetValues(*self.matrix)
        return transformation


def prototype_file_name(entry: str, binary: bool = True) -> str:
    """File name of a prototype (``0:1:1:5`` -> ``0_1_1_5.bbrep`` or ``.brep``)."""
    return entry.replace(":", "_") + (BINARY_SUFFIX if binary else ASCII_SUFFIX)


def read_brep(path: Path) -> TopoDS_Shape:
    """Read one B-rep file; ``.bbrep`` is BinTools binary, anything else BRepTools ASCII.

    Raises:
        FileNotFoundError: If the file does not exist.
        RuntimeError: If OpenCascade cannot parse it.
    """
    if not path.exists():
        raise FileNotFoundError(path)
    shape = TopoDS_Shape()
    if path.suffix == BINARY_SUFFIX:
        ok = bintools.Read(shape, str(path))
    else:
        ok = breptools.Read(shape, str(path), BRep_Builder())
    if not ok or shape.IsNull():
        raise RuntimeError(f"cannot read B-rep file {path}")
    return shape


def write_brep(shape: TopoDS_Shape, path: Path) -> None:
    """Write without triangulation; the suffix selects binary (``.bbrep``) or ASCII.

    Raises:
        RuntimeError: If OpenCascade reports a write failure.
    """
    if path.suffix == BINARY_SUFFIX:
        ok = bintools.Write(shape, str(path), False, False, BinTools_FormatVersion_VERSION_4)
    else:
        ok = breptools.Write(shape, str(path), False, False, TopTools_FormatVersion_VERSION_3)
    if not ok:
        raise RuntimeError(f"B-rep write failed: {path}")


def shape_vertices(shape: TopoDS_Shape) -> np.ndarray:
    """Coordinates of all vertices in exploration order (N x 3, shape units)."""
    points = []
    explorer = TopExp_Explorer(shape, TopAbs_VERTEX)
    while explorer.More():
        point = BRep_Tool.Pnt(topods.Vertex(explorer.Current()))
        points.append((point.X(), point.Y(), point.Z()))
        explorer.Next()
    return np.asarray(points, dtype=float).reshape(-1, 3)


# --------------------------------------------------------------------------
# Index tables
# --------------------------------------------------------------------------
def _parse_instance(row: dict) -> Instance:
    return Instance(
        instance_path=row["instance_path"],
        prototype_entry=row["prototype_entry"],
        prototype_file=row["prototype_file"],
        product_name=row["product_name"],
        instance_name=row["instance_name"],
        top_assembly=row["top_assembly"],
        depth=int(row["depth"]),
        is_mirrored=row["is_mirrored"] == "True",
        matrix=tuple(float(row[column]) for column in MATRIX_COLUMNS),
    )


@functools.cache
def instances() -> tuple[Instance, ...]:
    """All leaf occurrences, in ``instance_path`` order (same as ``parts.csv``).

    The first call also runs a quick freshness check of the cache against the
    manifest and warns if the STEP file or cache files changed.
    """
    _warn_if_stale()
    with INSTANCES_CSV.open(encoding="utf-8-sig", newline="") as handle:
        return tuple(_parse_instance(row) for row in csv.DictReader(handle))


@functools.cache
def _by_path() -> dict[str, Instance]:
    return {item.instance_path: item for item in instances()}


@functools.cache
def _by_entry() -> dict[str, tuple[Instance, ...]]:
    grouped: dict[str, list[Instance]] = {}
    for item in instances():
        grouped.setdefault(item.prototype_entry, []).append(item)
    return {entry: tuple(items) for entry, items in grouped.items()}


@functools.cache
def prototypes() -> tuple[dict, ...]:
    """Rows of ``prototypes.csv`` as dictionaries (strings as stored)."""
    with PROTOTYPES_CSV.open(encoding="utf-8-sig", newline="") as handle:
        return tuple(csv.DictReader(handle))


def get_instance(instance_path: str) -> Instance:
    """Return the occurrence with this exact ``instance_path``.

    Raises:
        KeyError: If the path is not in the cache.
    """
    try:
        return _by_path()[instance_path]
    except KeyError:
        raise KeyError(f"instance not in B-rep cache: {instance_path!r}") from None


def instances_of(prototype_entry: str) -> tuple[Instance, ...]:
    """All occurrences of one prototype (empty if the entry is unknown)."""
    return _by_entry().get(prototype_entry, ())


def iter_instances(
    pattern: str | re.Pattern | None = None,
    *,
    top_assembly: str | None = None,
    prototype_entry: str | None = None,
) -> Iterator[Instance]:
    """Yield occurrences filtered by path regex, top assembly and/or prototype.

    Args:
        pattern: Regular expression searched in ``instance_path``.
        top_assembly: Exact ``top_assembly`` name (e.g. ``"FRONT JACK CYL:1"``).
        prototype_entry: Exact prototype entry (e.g. ``"0:1:1:375"``).
    """
    matcher = re.compile(pattern) if isinstance(pattern, str) else pattern
    for item in instances():
        if matcher is not None and not matcher.search(item.instance_path):
            continue
        if top_assembly is not None and item.top_assembly != top_assembly:
            continue
        if prototype_entry is not None and item.prototype_entry != prototype_entry:
            continue
        yield item


# --------------------------------------------------------------------------
# Shapes
# --------------------------------------------------------------------------
@functools.cache
def _file_by_entry() -> dict[str, str]:
    return {row["prototype_entry"]: row["prototype_file"] for row in prototypes()}


def prototype_path(entry: str) -> Path:
    """Path of the prototype file listed in ``prototypes.csv`` (binary by default)."""
    return PROTOTYPE_DIR / _file_by_entry().get(entry, prototype_file_name(entry))


@functools.cache
def _prototype_shape(entry: str) -> TopoDS_Shape:
    return read_brep(prototype_path(entry))


def load_prototype(entry: str) -> TopoDS_Shape:
    """Shape of one prototype in its own frame (mm). Files are read once.

    The returned handle is a fresh ``TopoDS_Shape`` that shares the cached
    geometry, so ``Move``/``Location`` on it do not change the cache.
    """
    shape = _prototype_shape(entry)
    return shape.Located(shape.Location())


def place(shape: TopoDS_Shape, instance: Instance) -> TopoDS_Shape:
    """Return ``shape`` moved by the placement of ``instance`` (CAD world, mm)."""
    return shape.Moved(TopLoc_Location(instance.trsf()))


def load_part(key: str, placed: bool = True) -> TopoDS_Shape:
    """Load a part by instance path or prototype entry.

    Args:
        key: An ``instance_path`` or a ``prototype_entry`` of ``parts.csv``.
        placed: For an instance path, apply its placement (CAD world frame).
            For a prototype entry, ``placed=True`` is allowed only when the
            prototype has exactly one occurrence; use ``placed=False`` for the
            prototype frame.

    Raises:
        KeyError: If the key is neither a known path nor a known entry.
        ValueError: If a shared prototype is requested with ``placed=True``.
    """
    if key in _by_path():
        instance = _by_path()[key]
        shape = load_prototype(instance.prototype_entry)
        return place(shape, instance) if placed else shape
    occurrences = instances_of(key)
    if not occurrences:
        raise KeyError(f"neither an instance path nor a prototype entry: {key!r}")
    shape = load_prototype(key)
    if not placed:
        return shape
    if len(occurrences) != 1:
        raise ValueError(
            f"prototype {key} has {len(occurrences)} occurrences; pass an "
            "instance path or placed=False"
        )
    return place(shape, occurrences[0])


def load_compound(items: Iterable[Instance | str], placed: bool = True) -> TopoDS_Compound:
    """Build one compound from occurrences (``Instance`` objects or paths)."""
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    for item in items:
        path = item.instance_path if isinstance(item, Instance) else item
        builder.Add(compound, load_part(path, placed=placed))
    return compound


def load_crawler_part(kind: str, side: str, index: int) -> TopoDS_Shape:
    """One crawler contact part of layout D (``derive_crawler_parts.py``), CAD world, mm.

    Args:
        kind: ``roller``, ``end_shoe`` or ``flat_shoe``.
        side: ``L`` (left, body +y) or ``R``.
        index: 0-based ``order_index`` (ascending body x); for ``roller`` and
            ``end_shoe`` it is the index into the YAML arrays
            ``contact.crawler.sphere_layout.roller_x_m`` / ``end_shoe_x_m``.

    Raises:
        KeyError: If the index table has no such part.
    """
    with CRAWLER_PARTS_CSV.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if (row["kind"], row["side"], int(row["order_index"])) == (kind, side, index):
                return read_brep(PROJECT_ROOT / row["file"])
    raise KeyError(f"no crawler part {kind} {side} {index} in {CRAWLER_PARTS_CSV}")


def load_crawler_upper_roller(side: str, index: int = 0) -> TopoDS_Shape:
    """Upper (carrier) roller part of one track (``derive_crawler_upper_rollers.py``), CAD world, mm.

    The part is the roller solid (wheel, shaft boss and bracket, merged in the
    CAD shrinkwrap) plus its bracket bolts and washers; the seat block on the
    track frame is not included.

    Args:
        side: ``L`` (left, body +y) or ``R``.
        index: 0-based ``order_index`` (ascending body x); the CAD has one per side.

    Raises:
        KeyError: If the index table has no such part.
    """
    with CRAWLER_UPPER_ROLLERS_CSV.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if (row["side"], int(row["order_index"])) == (side, index):
                return read_brep(PROJECT_ROOT / row["file"])
    raise KeyError(f"no upper roller {side} {index} in {CRAWLER_UPPER_ROLLERS_CSV}")


def clear_memory_cache() -> None:
    """Forget loaded shapes and tables (files are re-read on the next call)."""
    for cached in (_prototype_shape, instances, _by_path, _by_entry, prototypes, _file_by_entry):
        cached.cache_clear()


def _warn_if_stale() -> None:
    """Quick manifest check of this cache (stat only, no hashing)."""
    try:
        from check_cache import warn_if_stale
    except ImportError:  # pragma: no cover - check_cache sits in the same folder
        return
    warn_if_stale([CACHE_NAME])
