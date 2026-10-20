"""Machine geometry derived from the parameters (engine independent).

Leg moving-part and pad-sphere positions in body coordinates as a function of the leg
extension, and the body height at which the pads just touch a level floor. Used by the
Chrono body builder (``chrono/bodies``) and by the analytic static start
(``scenarios/settle``), so both use one definition.

Conventions (``00_docs/01_dynamics/dynamics_model.md`` 1.1, 2.1; YAML ``meta.frame``):
body frame x forward, y left, z up, origin = CAD origin; extension ``e`` moves the moving
part along ``actuator.extension_direction`` (body -z); the pad sphere centre is the swivel
centre, ``legs.<leg>.pad.swivel_center_above_pad_bottom_m`` above the pad bottom
(ASSUMPTION 0.06 m). Units SI.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.params import Params


def extension_direction(params: Params) -> NDArray[np.float64]:
    """Unit extension direction in body coordinates (``actuator.extension_direction``)."""
    direction = np.asarray(params.actuator.extension_direction, dtype=float)
    return direction / np.linalg.norm(direction)


def leg_com_body_m(params: Params, leg_index: int, extension_m: float) -> NDArray[np.float64]:
    """Moving-part centre of mass in body coordinates at ``extension_m``."""
    leg = params.legs[leg_index]
    return np.asarray(leg.moving_part.com_m, dtype=float) + extension_m * extension_direction(
        params
    )


def pad_bottom_body_m(params: Params, leg_index: int, extension_m: float) -> NDArray[np.float64]:
    """Pad bottom centre in body coordinates at ``extension_m``."""
    leg = params.legs[leg_index]
    return np.asarray(
        leg.pad_bottom_center_retracted_m, dtype=float
    ) + extension_m * extension_direction(params)


def pad_sphere_centre_body_m(
    params: Params, leg_index: int, extension_m: float
) -> NDArray[np.float64]:
    """Swivel-ball centre (= L1 pad sphere centre) in body coordinates at ``extension_m``."""
    radius = params.legs[leg_index].pad.swivel_center_above_pad_bottom_m
    return pad_bottom_body_m(params, leg_index, extension_m) - radius * extension_direction(params)


def pads_touching_origin_z_m(
    params: Params, extensions_m: Sequence[float], floor_z_m: float | None = None
) -> NDArray[np.float64]:
    """Per leg: body-origin height (level body) at which that pad bottom touches the floor.

    With the operating extensions all four values are equal (``e_op`` is defined from the
    crawler clearance, ``dynamics_model.md`` 1.3): the "zero" pose of the static 3-DoF model
    (pads just touching, no compression).
    """
    floor = params.ground.crawler_bottom_z_m if floor_z_m is None else float(floor_z_m)
    return np.array(
        [
            floor - pad_bottom_body_m(params, i, float(extensions_m[i]))[2]
            for i in range(len(params.legs))
        ]
    )
