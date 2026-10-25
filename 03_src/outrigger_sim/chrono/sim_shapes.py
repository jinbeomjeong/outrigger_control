"""Simplified visual and collision shapes of roadmap C8 (loader + attach helpers).

The shapes are built by ``04_scripts/00_cad/build_sim_shapes.py`` into ``01_cad/09_sim_shapes/``
(index ``sim_shapes.json``, documentation ``00_docs/00_cad/cad_sim_shapes.md``). Every OBJ is
in the **machine body frame** (x forward, y left, z up, origin = CAD origin, metres) in the CAD
pose, with the legs in the retracted state and the auger at its CAD position.

Attachment (``sim_shapes.json`` ``attach_rules``):

* ``superstructure`` shapes go on the superstructure body (COG frame, body axes,
  :mod:`outrigger_sim.chrono.bodies`) with the frame offset
  ``-superstructure.mass_properties.com_m`` (+ ``auger_travel_m`` along z for the auger);
* ``leg`` shapes go on the leg moving part with the offset ``-legs.<leg>.moving_part.com_m``
  (retracted COM; the offset does not depend on the extension because the OBJ is in the
  retracted state and the body moves rigidly along the leg axis).

Visual shapes never change the dynamics. **Collision shapes are opt-in** (``collision=...``)
and change the contact model (and the V verdicts): the default keeps the current contact model
(pad spheres + ground bushing, crawler spheres of layout D, families R14). A flat pad collision
shape on the rigid L1 rod body brings back the edge contact that the swivel model avoids (CLAUDE.md
'다리 기하'); it is meant for a separate pad body on a spherical joint. Collision shapes must be
added before the body is added to the system (Bullet binds the model at ``ChSystem.Add``);
the collision family is left to the caller (R14).

Units SI. pychrono 10.0.0 API (checked 2026-10-21): ``ChTriangleMeshConnected.
CreateFromWavefrontFile``, ``ChVisualShapeTriangleMesh``, ``ChBody.AddVisualShape(shape, frame)``,
``ChCollisionShapeConvexHull(material, vector_ChVector3d)``, ``ChCollisionShapeBox``.
"""

from __future__ import annotations

import functools
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import NDArray

from outrigger_sim.params import LEG_ORDER, Params

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SIM_SHAPES_DIR = PROJECT_ROOT / "01_cad" / "09_sim_shapes"
INDEX_JSON = SIM_SHAPES_DIR / "sim_shapes.json"

SUPERSTRUCTURE = "superstructure"
LEG = "leg"
PAD_CHOICES = ("simple", "cad", None)
"""``simple`` = chamfered octagon plate (exact B-rep plate, 44 triangles), ``cad`` = plate +
gussets (B-rep tessellation), None = no pad visual."""


@dataclass(frozen=True)
class ShapeEntry:
    """One shape of the index (visual mesh or collision candidate)."""

    name: str
    role: str  # "visual" or "collision"
    kind: str  # "mesh", "convex_hull", "convex_decomposition", "box"
    attach: str  # "superstructure" or "leg"
    leg: str | None
    moves_with_auger: bool
    file: Path | None
    pieces: int
    color: tuple[float, float, float] | None
    default: bool
    raw: Mapping[str, Any] = field(repr=False, compare=False)

    @property
    def leg_index(self) -> int | None:
        return None if self.leg is None else LEG_ORDER.index(self.leg)


class SimShapeIndex:
    """``sim_shapes.json`` with resolved file paths."""

    def __init__(self, data: Mapping[str, Any], root: Path = PROJECT_ROOT) -> None:
        self.data = data
        self.root = root
        self.visuals: dict[str, ShapeEntry] = {
            name: self._entry(name, "visual", item) for name, item in data["visual"].items()
        }
        self.collisions: dict[str, ShapeEntry] = {
            name: self._entry(name, "collision", item) for name, item in data["collision"].items()
        }

    def _entry(self, name: str, role: str, item: Mapping[str, Any]) -> ShapeEntry:
        file = item.get("file")
        color = item.get("color")
        return ShapeEntry(
            name=name,
            role=role,
            kind=item.get("kind", "mesh"),
            attach=item["attach"],
            leg=item.get("leg"),
            moves_with_auger=bool(item.get("moves_with_auger", False)),
            file=(self.root / file) if file else None,
            pieces=int(item.get("pieces", 1)),
            color=tuple(float(c) for c in color) if color else None,
            default=bool(item.get("default", False)),
            raw=item,
        )

    @classmethod
    def load(cls, path: Path | None = None) -> SimShapeIndex:
        path = INDEX_JSON if path is None else Path(path)
        root = path.resolve().parents[2]  # <root>/01_cad/09_sim_shapes/sim_shapes.json
        return cls(json.loads(path.read_text(encoding="utf-8")), root)

    def visual(self, name: str) -> ShapeEntry:
        return self.visuals[name]

    def collision(self, name: str) -> ShapeEntry:
        return self.collisions[name]

    def default_visual_names(self, attach: str, leg: str | None = None) -> list[str]:
        return [
            e.name
            for e in self.visuals.values()
            if e.default and e.attach == attach and (attach != LEG or e.leg == leg)
        ]


@functools.lru_cache(maxsize=1)
def load_index() -> SimShapeIndex:
    """The project index (read once)."""
    return SimShapeIndex.load()


def shape_offset_m(params: Params, entry: ShapeEntry) -> NDArray[np.float64]:
    """Position of the OBJ frame origin (body frame origin, CAD) in the body COG frame [m].

    Raises:
        ValueError: Unknown ``attach``.
    """
    if entry.attach == SUPERSTRUCTURE:
        offset = -np.asarray(params.superstructure.mass_properties.com_m, dtype=float)
        if entry.moves_with_auger:
            offset = offset + np.array([0.0, 0.0, float(params.superstructure.auger_travel_m)])
        return offset
    if entry.attach == LEG:
        if entry.leg_index is None:
            raise ValueError(f"leg shape {entry.name} has no leg")
        return -np.asarray(params.legs[entry.leg_index].moving_part.com_m, dtype=float)
    raise ValueError(f"unknown attach {entry.attach!r} of {entry.name}")


def read_obj_pieces(path: Path) -> list[tuple[NDArray[np.float64], NDArray[np.int64]]]:
    """(vertices, faces) per ``o`` object of an OBJ written by ``build_sim_shapes.py``."""
    pieces: list[tuple[NDArray[np.float64], NDArray[np.int64]]] = []
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    start = 0

    def flush() -> None:
        if faces:
            pieces.append((np.array(vertices[start:], float), np.array(faces, np.int64) - start))

    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("v "):
            vertices.append([float(t) for t in line.split()[1:4]])
        elif line.startswith("f "):
            faces.append([int(t.split("/")[0]) - 1 for t in line.split()[1:4]])
        elif line.startswith("o "):
            flush()
            start, faces = len(vertices), []
    flush()
    return pieces


@functools.lru_cache(maxsize=64)
def _trimesh_connected(path: str) -> ch.ChTriangleMeshConnected:
    mesh = ch.ChTriangleMeshConnected.CreateFromWavefrontFile(path, False, False)
    if mesh is None or mesh.GetNumTriangles() == 0:
        raise RuntimeError(f"cannot read OBJ {path}")
    return mesh


def _chvec(a: Sequence[float] | NDArray[np.float64]) -> ch.ChVector3d:
    x, y, z = (float(c) for c in np.asarray(a, dtype=float).reshape(3))
    return ch.ChVector3d(x, y, z)


def _require_file(entry: ShapeEntry) -> Path:
    if entry.file is None or not entry.file.exists():
        raise FileNotFoundError(
            f"{entry.name}: {entry.file} missing (run 04_scripts/00_cad/build_sim_shapes.py)"
        )
    return entry.file


def add_visual(
    body: ch.ChBody,
    entry: ShapeEntry,
    params: Params,
    *,
    color: Sequence[float] | None = None,
    offset_m: Sequence[float] | NDArray[np.float64] | None = None,
) -> ch.ChVisualShapeTriangleMesh:
    """Add one visual mesh to ``body`` (no effect on dynamics).

    Args:
        offset_m: OBJ frame origin in the body COG frame; default :func:`shape_offset_m`. For a
            separate body whose COG frame has the body axes, pass ``-reference_point_body_m``
            (see :func:`attach_upper_rollers`).
    """
    if entry.kind != "mesh" and entry.role == "visual":
        raise ValueError(f"{entry.name} is not a mesh")
    shape = ch.ChVisualShapeTriangleMesh()
    shape.SetMesh(_trimesh_connected(str(_require_file(entry))))
    shape.SetMutable(False)
    shape.SetName(entry.name)
    rgb = color if color is not None else entry.color
    if rgb is not None:
        shape.SetColor(ch.ChColor(*(float(c) for c in rgb)))
    offset = shape_offset_m(params, entry) if offset_m is None else np.asarray(offset_m, dtype=float)
    body.AddVisualShape(shape, ch.ChFramed(_chvec(offset), ch.QUNIT))
    return shape


def add_collision(
    body: ch.ChBody,
    entry: ShapeEntry,
    params: Params,
    material: ch.ChContactMaterial,
    *,
    offset_m: Sequence[float] | NDArray[np.float64] | None = None,
) -> int:
    """Add a collision candidate (convex hull pieces, a box or a cylinder set) to ``body``;
    returns the number of collision shapes added.

    This changes the contact model: use only in a model variant judged by dynamics-expert.

    Args:
        offset_m: OBJ frame origin in the body COG frame; default :func:`shape_offset_m`.

    Raises:
        ValueError: ``body`` is already in a system (add collision shapes before
            ``ChSystem.Add``), or the entry is not a collision shape.
    """
    if entry.role != "collision":
        raise ValueError(f"{entry.name} is not a collision shape")
    if body.GetSystem() is not None:
        raise ValueError(f"add collision shapes to {body.GetName()!r} before ChSystem.Add")
    offset = shape_offset_m(params, entry) if offset_m is None else np.asarray(offset_m, dtype=float)
    body.EnableCollision(True)
    if entry.kind == "cylinder_set":
        # Chrono 10 cylinder axis = shape-frame z; the stored rotation turns it to the roller axis
        for cylinder in entry.raw["cylinders"]:
            w, x, y, z = (float(c) for c in cylinder["rotation_wxyz"])
            centre = np.asarray(cylinder["centre_m"], dtype=float) + offset
            body.AddCollisionShape(
                ch.ChCollisionShapeCylinder(
                    material, float(cylinder["radius_m"]), float(cylinder["height_m"])
                ),
                ch.ChFramed(_chvec(centre), ch.ChQuaterniond(w, x, y, z)),
            )
        return len(entry.raw["cylinders"])
    if entry.kind == "box":
        half = np.asarray(entry.raw["half_extents_m"], dtype=float)
        w, x, y, z = (float(c) for c in entry.raw["rotation_wxyz"])
        centre = np.asarray(entry.raw["centre_m"], dtype=float) + offset
        body.AddCollisionShape(
            ch.ChCollisionShapeBox(material, *(2.0 * half)),
            ch.ChFramed(_chvec(centre), ch.ChQuaterniond(w, x, y, z)),
        )
        return 1
    count = 0
    for vertices, _ in read_obj_pieces(_require_file(entry)):
        points = ch.vector_ChVector3d([_chvec(v) for v in vertices + offset])
        body.AddCollisionShape(ch.ChCollisionShapeConvexHull(material, points), ch.ChFramed())
        count += 1
    return count


@dataclass
class AttachReport:
    """What the attach helpers added (names per body)."""

    visual: dict[str, list[str]] = field(default_factory=dict)
    collision: dict[str, list[str]] = field(default_factory=dict)

    def add(self, kind: str, body: ch.ChBody, name: str) -> None:
        getattr(self, kind).setdefault(body.GetName(), []).append(name)


def attach_superstructure(
    body: ch.ChBody,
    params: Params,
    index: SimShapeIndex | None = None,
    *,
    visuals: Iterable[str] | None = None,
    collision: Iterable[str] = (),
    material: ch.ChContactMaterial | None = None,
    report: AttachReport | None = None,
) -> AttachReport:
    """Superstructure visuals (default: deck, mast, auger, crawler, 4 barrels).

    Args:
        collision: Collision entries to add (e.g. ``("track_L_coacd", "track_R_coacd")``);
            empty = keep the current contact model (default).
        material: Contact material for ``collision`` (required if any).
    """
    index = load_index() if index is None else index
    report = AttachReport() if report is None else report
    names = index.default_visual_names(SUPERSTRUCTURE) if visuals is None else list(visuals)
    for name in names:
        entry = index.visual(name)
        if entry.attach != SUPERSTRUCTURE:
            raise ValueError(f"{name} attaches to {entry.attach}")
        add_visual(body, entry, params)
        report.add("visual", body, name)
    _add_collisions(body, params, index, collision, material, SUPERSTRUCTURE, None, report)
    return report


def attach_leg(
    body: ch.ChBody,
    params: Params,
    leg_index: int,
    index: SimShapeIndex | None = None,
    *,
    pad: str | None = "simple",
    rod: bool = True,
    collision: Iterable[str] = (),
    material: ch.ChContactMaterial | None = None,
    report: AttachReport | None = None,
    pad_variant: str | None = None,
) -> AttachReport:
    """Rod and pad visuals of one leg moving part (L1: rod + pad are one body).

    Args:
        pad: ``simple``, ``cad`` or None (see :data:`PAD_CHOICES`).
        collision: e.g. ``("pad_FL_hull",)``; empty = current pad sphere only (default).
        pad_variant: None (default) = the C8 index pad visual as before. A pad type
            (``outrigger_sim.pad_variants``, e.g. ``"cad330"``) draws that type's simple pad
            (``pad="simple"`` only; the ``cad`` visual exists for the C8 index pads only).
    """
    if pad not in PAD_CHOICES:
        raise ValueError(f"pad must be one of {PAD_CHOICES}, got {pad!r}")
    if pad_variant is not None and pad not in ("simple", None):
        raise ValueError(f"pad_variant needs pad='simple' or None, got {pad!r}")
    index = load_index() if index is None else index
    report = AttachReport() if report is None else report
    leg = LEG_ORDER[leg_index]
    if rod:
        add_visual(body, index.visual(f"rod_{leg}"), params)
        report.add("visual", body, f"rod_{leg}")
    if pad:
        entry = (index.visual(f"pad_{leg}_{pad}") if pad_variant is None
                 else pad_shape_entries(leg, pad_variant, index)[0])
        add_visual(body, entry, params)
        report.add("visual", body, entry.name)
    _add_collisions(body, params, index, collision, material, LEG, leg, report)
    return report


def pad_shape_entries(
    leg: str, pad_variant: str | None = None, index: SimShapeIndex | None = None, table: Any = None
) -> tuple[ShapeEntry, ShapeEntry]:
    """(simple pad visual, convex pad hull) of ``leg`` for a pad type (U-PAD 2026-10-25).

    ``pad_variant`` None = the default type (``dwg_rear250``). Shapes that are in the C8 index
    (front pads; rear 250 pads) come from the index; the type A rear 330 pads come from
    ``01_cad/09_sim_shapes/pad_variants/`` (``export_pad_variants.py``). Same frame and attach
    rule as the index (leg moving part, retracted state).
    """
    from outrigger_sim.pad_variants import load_pad_variants

    index = load_index() if index is None else index
    table = load_pad_variants() if table is None else table
    shape = table.variant(pad_variant).leg(leg)
    if shape.hull_in_c8_index:
        return index.visual(shape.visual_simple_name), index.collision(shape.hull_name)
    base_visual = index.visual(f"pad_{leg}_simple").raw
    base_hull = index.collision(f"pad_{leg}_hull").raw
    visual = ShapeEntry(
        name=shape.visual_simple_name, role="visual", kind="mesh", attach=LEG, leg=leg,
        moves_with_auger=False, file=shape.visual_simple_file, pieces=1,
        color=tuple(float(c) for c in base_visual["color"]) if base_visual.get("color") else None,
        default=False, raw={"file": str(shape.visual_simple_file), "attach": LEG, "leg": leg},
    )
    hull = ShapeEntry(
        name=shape.hull_name, role="collision", kind=base_hull["kind"], attach=LEG, leg=leg,
        moves_with_auger=False, file=shape.hull_file, pieces=1, color=None, default=False,
        raw={"file": str(shape.hull_file), "attach": LEG, "leg": leg, "kind": base_hull["kind"]},
    )
    return visual, hull


def add_pad_hull(
    body: ch.ChBody,
    params: Params,
    leg_index: int,
    material: ch.ChContactMaterial,
    *,
    pad_variant: str | None = None,
    offset_m: Sequence[float] | NDArray[np.float64] | None = None,
    index: SimShapeIndex | None = None,
    report: AttachReport | None = None,
) -> ShapeEntry:
    """Add the convex pad hull of a pad type to ``body`` (before ``ChSystem.Add``).

    For the L1 leg moving part the default offset applies; for a separate SCM pad body (S9:
    pad body + spherical joint) pass ``offset_m`` = OBJ frame origin in that body's COG frame
    (e.g. ``-legs.<leg>.pad_body.com_m`` in the retracted state, body axes). Returns the entry.
    """
    leg = LEG_ORDER[leg_index]
    _, hull = pad_shape_entries(leg, pad_variant, index)
    add_collision(body, hull, params, material, offset_m=offset_m)
    if report is not None:
        report.add("collision", body, hull.name)
    return hull


def _add_collisions(
    body: ch.ChBody,
    params: Params,
    index: SimShapeIndex,
    names: Iterable[str],
    material: ch.ChContactMaterial | None,
    attach: str,
    leg: str | None,
    report: AttachReport,
) -> None:
    names = list(names)
    if names and material is None:
        raise ValueError("collision shapes need a contact material")
    for name in names:
        entry = index.collision(name)
        if entry.attach != attach or (attach == LEG and entry.leg != leg):
            raise ValueError(f"{name} attaches to {entry.attach} {entry.leg or ''}".strip())
        add_collision(body, entry, params, material)
        report.add("collision", body, name)


UPPER_ROLLER_SIDES = ("L", "R")
CRAWLER_WITHOUT_UPPER_ROLLERS = "crawler_no_upper_rollers"


def attach_upper_rollers(
    body: ch.ChBody,
    params: Params,
    index: SimShapeIndex | None = None,
    *,
    sides: Iterable[str] = UPPER_ROLLER_SIDES,
    reference_point_body_m: Sequence[float] | NDArray[np.float64] | None = None,
    visual: bool = True,
    collision: Iterable[str] = (),
    material: ch.ChContactMaterial | None = None,
    report: AttachReport | None = None,
) -> AttachReport:
    """Upper (carrier) roller visuals ``upper_roller_<side>`` (and optional collision shapes).

    The ``crawler`` visual already contains the upper rollers. Use these shapes either with
    the ``crawler_no_upper_rollers`` visual on the superstructure (same picture, separate
    shapes), or on separate roller bodies (track-drive model T).

    Args:
        reference_point_body_m: None = ``body`` is the superstructure (offset
            ``-superstructure com``). Otherwise ``body`` is a separate body whose COG frame has
            the body axes and whose COG sits at this point of the CAD-pose body frame (e.g. the
            roller axis point ``index.visual('upper_roller_L').raw['axis_body_m']`` or the
            roller centre of mass); the shapes get the offset ``-reference_point_body_m``.
        collision: e.g. ``("upper_roller_L_cylinders",)`` or ``("upper_roller_L_hull",)``;
            empty = none (default). Each name must belong to one of ``sides``.
    """
    index = load_index() if index is None else index
    report = AttachReport() if report is None else report
    sides = tuple(sides)
    offset = (
        None
        if reference_point_body_m is None
        else -np.asarray(reference_point_body_m, dtype=float).reshape(3)
    )
    if visual:
        for side in sides:
            name = f"upper_roller_{side}"
            add_visual(body, index.visual(name), params, offset_m=offset)
            report.add("visual", body, name)
    names = list(collision)
    if names and material is None:
        raise ValueError("collision shapes need a contact material")
    for name in names:
        entry = index.collision(name)
        if entry.raw.get("side") not in sides or not name.startswith("upper_roller_"):
            raise ValueError(f"{name} is not an upper-roller shape of sides {sides}")
        add_collision(body, entry, params, material, offset_m=offset)
        report.add("collision", body, name)
    return report


def attach_model_visuals(
    model: Any,
    index: SimShapeIndex | None = None,
    *,
    pad: str | None = "simple",
    superstructure_visuals: Iterable[str] | None = None,
    upper_rollers: bool = False,
) -> AttachReport:
    """Visuals only, on a built model with ``params``, ``superstructure`` and ``legs``
    (e.g. :class:`outrigger_sim.chrono.model.L1Model`). Safe after ``ChSystem.Add``; a
    visualization system must bind the shapes afterwards (``vis.BindAll()`` or attach the
    system after this call).

    Args:
        upper_rollers: Draw the upper rollers as separate shapes on the superstructure (fixed,
            the leveling model has no roller bodies): the default ``crawler`` visual is
            replaced by ``crawler_no_upper_rollers`` so nothing is drawn twice. False (default)
            = previous behaviour (rollers drawn as part of ``crawler``).
    """
    index = load_index() if index is None else index
    report = AttachReport()
    names = (
        index.default_visual_names(SUPERSTRUCTURE)
        if superstructure_visuals is None
        else list(superstructure_visuals)
    )
    if upper_rollers:
        names = [CRAWLER_WITHOUT_UPPER_ROLLERS if n == "crawler" else n for n in names]
    attach_superstructure(model.superstructure, model.params, index, visuals=names, report=report)
    if upper_rollers:
        attach_upper_rollers(model.superstructure, model.params, index, report=report)
    for i, leg_body in enumerate(model.legs):
        attach_leg(leg_body, model.params, i, index, pad=pad, report=report)
    return report
