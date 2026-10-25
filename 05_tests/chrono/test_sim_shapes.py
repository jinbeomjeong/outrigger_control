"""C8 simplified shapes: index, frame offsets, visual / collision attachment (``chrono/sim_shapes``).

Uses only the small leg OBJs (rods, pads, pad hulls / CoACD pieces) so that it runs in seconds;
the large superstructure meshes (``*_lowres.obj``, git ignored) are checked if present.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("pychrono")

import pychrono as ch  # noqa: E402

from outrigger_sim.chrono import sim_shapes  # noqa: E402
from outrigger_sim.chrono.bodies import BodyPose, make_leg_moving_parts, make_superstructure  # noqa: E402
from outrigger_sim.geometry import pad_bottom_body_m  # noqa: E402
from outrigger_sim.params import LEG_ORDER, load_params  # noqa: E402

pytestmark = pytest.mark.chrono

if not sim_shapes.INDEX_JSON.exists():  # pragma: no cover - generated data
    pytest.skip("01_cad/09_sim_shapes/sim_shapes.json missing", allow_module_level=True)


@pytest.fixture(scope="module")
def index() -> sim_shapes.SimShapeIndex:
    return sim_shapes.SimShapeIndex.load()


def _world_points(body: ch.ChBody, shape_index: int, local_points: np.ndarray) -> np.ndarray:
    """Body visual-shape points (shape frame) -> world, through the shape frame and the body."""
    frame = body.GetVisualModel().GetShapeFrame(shape_index)
    out = []
    for p in local_points:
        q = frame.TransformPointLocalToParent(ch.ChVector3d(*map(float, p)))
        w = body.TransformPointLocalToParent(q)
        out.append([w.x, w.y, w.z])
    return np.array(out)


def test_index_files_and_frame(index: sim_shapes.SimShapeIndex) -> None:
    assert index.data["frame"]["units"] == "m"
    for leg in LEG_ORDER:
        for name in (f"rod_{leg}", f"pad_{leg}_simple", f"pad_{leg}_cad"):
            entry = index.visual(name)
            assert entry.attach == sim_shapes.LEG and entry.leg == leg
            assert entry.file is not None and entry.file.exists()
        assert index.collision(f"pad_{leg}_hull").pieces == 1
    pieces = sim_shapes.read_obj_pieces(index.collision("pad_FL_hull").file)
    assert len(pieces) == 1 and len(pieces[0][1]) == index.collision("pad_FL_hull").raw["faces"]


@pytest.mark.parametrize("level", ["top", "middle", "bottom"])
def test_superstructure_offsets(index: sim_shapes.SimShapeIndex, level: str) -> None:
    params = load_params(level=level)
    com = np.asarray(params.superstructure.mass_properties.com_m)
    assert np.allclose(sim_shapes.shape_offset_m(params, index.visual("deck")), -com)
    travel = params.superstructure.auger_travel_m
    assert np.allclose(
        sim_shapes.shape_offset_m(params, index.visual("auger")), -com + [0.0, 0.0, travel]
    )


@pytest.mark.parametrize("leg_index", range(4))
@pytest.mark.parametrize("extension", [0.0, 0.3])
def test_pad_visual_lands_on_pad_bottom(
    index: sim_shapes.SimShapeIndex, leg_index: int, extension: float
) -> None:
    """Pad mesh bottom = YAML pad bottom centre at the extension, through the body pose."""
    params = load_params()
    pose = BodyPose((0.1, -0.2, 1.3), (np.cos(0.05), 0.0, np.sin(0.05), 0.0))
    ext = [0.0] * 4
    ext[leg_index] = extension
    body = make_leg_moving_parts(params, ext, pose)[leg_index]
    leg = LEG_ORDER[leg_index]
    mass_before = body.GetMass()
    sim_shapes.attach_leg(body, params, leg_index, index, pad="simple", rod=False)
    assert body.GetVisualModel().GetNumShapes() == 1
    assert body.GetMass() == mass_before
    assert body.GetCollisionModel() is None or body.GetCollisionModel().GetNumShapes() == 0
    vertices, faces = sim_shapes.read_obj_pieces(index.visual(f"pad_{leg}_simple").file)[0]
    bottom = vertices[np.isclose(vertices[:, 2], vertices[:, 2].min(), atol=1e-9)]
    world = _world_points(body, 0, bottom)
    expected = pose.to_world(pad_bottom_body_m(params, leg_index, extension))
    # rear pads: YAML pad bottom is rounded to 0.1 mm (-0.710 vs B-rep -0.710044 m)
    assert np.allclose(world.mean(axis=0), expected, atol=1e-4)
    # bottom face area (mesh normal pointing down) = B-rep pad face of the generated shape:
    # front 0.1071 m^2 (CAD 330 pad), rear 0.0607 m^2 (C8: REXOME35 250 pad) = YAML pad type B
    # (pad_shapes.dwg_rear250, the default type after the bundle of 2026-10-25); a YAML from
    # before the bundle still carries the CAD 0.1071 in legs.<leg>.pad.bottom_area_m2
    brep_area_m2 = index.data["legs"][leg]["pad_face"]["brep_area_m2"]
    a, b, c = (vertices[faces[:, k]] for k in range(3))
    n = np.cross(b - a, c - a)
    down_face_area_m2 = 0.5 * np.linalg.norm(n[n[:, 2] < 0], axis=1).sum()
    assert down_face_area_m2 == pytest.approx(brep_area_m2, rel=1e-6)


@pytest.mark.parametrize(("variant", "rear_area_m2"), [("cad330", 0.1071), ("dwg_rear250", 0.0607)])
def test_pad_variant_shapes(index: sim_shapes.SimShapeIndex, variant: str, rear_area_m2: float) -> None:
    """Pad type selects the rear pad visual / hull (U-PAD 2026-10-25); front pads are the index ones."""
    params = load_params()
    pose = BodyPose((0.0, 0.0, 1.0))
    for leg_index, leg in enumerate(LEG_ORDER):
        visual, hull = sim_shapes.pad_shape_entries(leg, variant, index)
        area = rear_area_m2 if leg in ("RL", "RR") else 0.1071
        for entry in (visual, hull):
            vertices, faces = sim_shapes.read_obj_pieces(entry.file)[0]
            a, b, c = (vertices[faces[:, k]] for k in range(3))
            n = np.cross(b - a, c - a)
            assert 0.5 * np.linalg.norm(n[n[:, 2] < 0], axis=1).sum() == pytest.approx(area, rel=1e-6)
            assert entry.attach == sim_shapes.LEG and entry.leg == leg
        if leg in ("FL", "FR") or variant == "dwg_rear250":
            assert hull is index.collision(f"pad_{leg}_hull")
        body = make_leg_moving_parts(params, [0.0] * 4, pose)[leg_index]
        report = sim_shapes.attach_leg(body, params, leg_index, index, rod=False, pad_variant=variant)
        assert report.visual[body.GetName()] == [visual.name]
        material = ch.ChContactMaterialSMC()
        added = sim_shapes.add_pad_hull(body, params, leg_index, material, pad_variant=variant, index=index)
        assert added.name == hull.name
        assert body.GetCollisionModel().GetNumShapes() == 1


def test_attach_leg_default_unchanged(index: sim_shapes.SimShapeIndex) -> None:
    """pad_variant None keeps the C8 index pad visual (bit-identical scene as before)."""
    params = load_params()
    body = make_leg_moving_parts(params, [0.0] * 4, BodyPose((0.0, 0.0, 1.0)))[2]
    report = sim_shapes.attach_leg(body, params, 2, index)
    assert report.visual[body.GetName()] == ["rod_RL", "pad_RL_simple"]


def test_collision_is_opt_in(index: sim_shapes.SimShapeIndex) -> None:
    params = load_params()
    pose = BodyPose((0.0, 0.0, 1.0))
    body = make_leg_moving_parts(params, [0.0] * 4, pose)[0]
    sim_shapes.attach_leg(body, params, 0, index)
    assert body.GetVisualModel().GetNumShapes() == 2
    assert not body.IsCollisionEnabled()
    material = ch.ChContactMaterialSMC()
    report = sim_shapes.attach_leg(
        body, params, 0, index, pad=None, rod=False,
        collision=("pad_FL_hull", "pad_FL_coacd"), material=material,
    )
    n_coacd = index.collision("pad_FL_coacd").pieces
    assert body.GetCollisionModel().GetNumShapes() == 1 + n_coacd
    assert report.collision[body.GetName()] == ["pad_FL_hull", "pad_FL_coacd"]
    with pytest.raises(ValueError):
        sim_shapes.attach_leg(body, params, 0, index, pad=None, rod=False, collision=("pad_FR_hull",),
                              material=material)
    system = ch.ChSystemSMC()
    system.Add(body)
    with pytest.raises(ValueError):
        sim_shapes.add_collision(body, index.collision("pad_FL_hull"), params, material)


def test_box_primitive_on_superstructure(index: sim_shapes.SimShapeIndex) -> None:
    params = load_params()
    body = make_superstructure(params, BodyPose((0.0, 0.0, 0.0)))
    sim_shapes.add_collision(body, index.collision("track_L_box"), params, ch.ChContactMaterialSMC())
    model = body.GetCollisionModel()
    assert model.GetNumShapes() == 1
    pos = model.GetShapeInstance(0).frame.GetPos()
    centre = np.asarray(index.collision("track_L_box").raw["centre_m"]) - params.superstructure.mass_properties.com_m
    assert np.allclose([pos.x, pos.y, pos.z], centre)


def test_superstructure_visuals_if_built(index: sim_shapes.SimShapeIndex) -> None:
    names = index.default_visual_names(sim_shapes.SUPERSTRUCTURE)
    missing = [n for n in names if not index.visual(n).file.exists()]
    if missing:
        pytest.skip(f"lowres meshes not built: {missing}")
    params = load_params()
    body = make_superstructure(params, BodyPose((0.0, 0.0, 0.0)))
    report = sim_shapes.attach_superstructure(body, params, index, visuals=["mast", "barrel_FL"])
    assert report.visual[body.GetName()] == ["mast", "barrel_FL"]
    assert body.GetVisualModel().GetNumShapes() == 2


# --- upper (carrier) rollers (2026-10-21) ------------------------------------------------------


@pytest.mark.parametrize("side", ["L", "R"])
def test_upper_roller_index(index: sim_shapes.SimShapeIndex, side: str) -> None:
    visual = index.visual(f"upper_roller_{side}")
    assert visual.attach == sim_shapes.SUPERSTRUCTURE and not visual.default
    assert visual.file.exists()
    assert f"upper_roller_{side}" not in index.default_visual_names(sim_shapes.SUPERSTRUCTURE)
    assert "crawler" in index.default_visual_names(sim_shapes.SUPERSTRUCTURE)
    assert not index.visual(sim_shapes.CRAWLER_WITHOUT_UPPER_ROLLERS).default
    cylinders = index.collision(f"upper_roller_{side}_cylinders").raw["cylinders"]
    radii = sorted(round(c["radius_m"], 6) for c in cylinders)
    assert radii == [0.06, 0.06, 0.07]
    treads = sorted(abs(c["centre_m"][1]) for c in cylinders if c["radius_m"] == pytest.approx(0.06))
    assert treads == pytest.approx([0.9855, 1.1045], abs=1e-6)
    assert index.collision(f"upper_roller_{side}_hull").pieces == 1


@pytest.mark.parametrize("side", ["L", "R"])
def test_upper_roller_on_superstructure_frame(index: sim_shapes.SimShapeIndex, side: str) -> None:
    """Tread vertices sit at R 60 mm about the CAD roller axis after the superstructure pose."""
    params = load_params()
    pose = BodyPose((0.3, -0.1, 0.9), (np.cos(0.02), np.sin(0.02), 0.0, 0.0))
    body = make_superstructure(params, pose)
    sim_shapes.attach_upper_rollers(body, params, index, sides=(side,))
    assert body.GetVisualModel().GetNumShapes() == 1
    entry = index.visual(f"upper_roller_{side}")
    vertices, _ = sim_shapes.read_obj_pieces(entry.file)[0]
    axis_point = np.asarray(entry.raw["axis_body_m"])
    tread_y = abs(axis_point[1]) - 0.0595  # 0.9855 m: inner tread centre (span 0.968 ... 1.003 m)
    near = vertices[np.abs(np.abs(vertices[:, 1]) - tread_y) < 0.0180]  # tread edge rings
    assert len(near) > 20
    world = _world_points(body, 0, near)
    axis_world = pose.to_world(axis_point)
    axis_dir = pose.rotation @ np.array([0.0, 1.0, 0.0])
    rel = world - axis_world
    radial = np.linalg.norm(rel - np.outer(rel @ axis_dir, axis_dir), axis=1)
    assert radial.max() == pytest.approx(0.060, abs=2e-4)  # tread R 60 mm (mesh chord <= 0.5 mm)


def test_upper_roller_separate_body_and_cylinders(index: sim_shapes.SimShapeIndex) -> None:
    params = load_params()
    entry = index.visual("upper_roller_L")
    axis_point = np.asarray(entry.raw["axis_body_m"])
    roller = ch.ChBody()
    roller.SetPos(ch.ChVector3d(*map(float, axis_point)))
    report = sim_shapes.attach_upper_rollers(
        roller, params, index, sides=("L",), reference_point_body_m=axis_point,
        collision=("upper_roller_L_cylinders",), material=ch.ChContactMaterialSMC(),
    )
    assert report.visual[roller.GetName()] == ["upper_roller_L"]
    frame = roller.GetVisualModel().GetShapeFrame(0).GetPos()
    assert np.allclose([frame.x, frame.y, frame.z], -axis_point)
    model = roller.GetCollisionModel()
    assert model.GetNumShapes() == 3
    for k in range(3):
        inst = model.GetShapeInstance(k)
        cyl = ch.CastToChCollisionShapeCylinder(inst.shape)
        z_local = inst.frame.TransformDirectionLocalToParent(ch.ChVector3d(0, 0, 1))
        assert np.allclose([z_local.x, z_local.y, z_local.z], [0.0, 1.0, 0.0], atol=1e-12)
        box = cyl.GetBoundingBox()  # shape frame: cylinder axis = z (Chrono 10)
        assert box.max.z - box.min.z == pytest.approx(cyl.GetHeight(), rel=1e-12)
        assert box.max.x - box.min.x == pytest.approx(2 * cyl.GetRadius(), rel=1e-12)
        pos = inst.frame.GetPos()
        assert abs(pos.x) < 1e-9 and abs(pos.z) < 1e-9  # on the roller axis
    with pytest.raises(ValueError):
        sim_shapes.attach_upper_rollers(roller, params, index, sides=("L",), visual=False,
                                        collision=("upper_roller_R_hull",), material=ch.ChContactMaterialSMC())


def test_model_visuals_upper_rollers_no_duplicate(index: sim_shapes.SimShapeIndex) -> None:
    if not index.visual(sim_shapes.CRAWLER_WITHOUT_UPPER_ROLLERS).file.exists():
        pytest.skip("crawler_no_upper_rollers_lowres.obj not built")
    params = load_params()
    pose = BodyPose((0.0, 0.0, 0.0))

    class _Model:  # the attributes attach_model_visuals uses
        pass

    model = _Model()
    model.params = params
    model.superstructure = make_superstructure(params, pose)
    model.legs = make_leg_moving_parts(params, [0.0] * 4, pose)
    report = sim_shapes.attach_model_visuals(
        model, index, superstructure_visuals=["crawler", "barrel_FL"], upper_rollers=True
    )
    names = report.visual[model.superstructure.GetName()]
    assert names == ["crawler_no_upper_rollers", "barrel_FL", "upper_roller_L", "upper_roller_R"]
    default = sim_shapes.attach_model_visuals(model, index, superstructure_visuals=["barrel_FL"])
    assert default.visual[model.superstructure.GetName()] == ["barrel_FL"]
