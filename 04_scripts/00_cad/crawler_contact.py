"""Crawler contact points of the shared parameters (layout D, rollers + gapped end shoes).

Single place where the scripts in ``04_scripts/00_cad`` and ``04_scripts/02_chrono`` turn
``02_params/rexome33.yaml`` ``contact.crawler.sphere_layout`` into contact points
(00_docs/03_chrono/chrono_build_plan.md R13, 00_docs/01_dynamics/dynamics_model.md 3.8):

* 2 tracks at y = +/- ``track_centre_y_m`` (left = +y first);
* per track one point at each ``roller_x_m`` (gap 0: bottom on the floor) and one at each
  ``end_shoe_x_m`` with bottom = floor + ``end_shoe_gap_m`` (same order). The end-shoe
  points are unilateral: they touch only after their gap has closed. In Chrono the sphere is
  simply placed ``gap`` higher;
* 2 x (6 + 6) = 24 points, all on the superstructure body, one material
  (``contact.crawler.kn_per_sphere_N_m``, ``gn_per_sphere_1_s``).

Frame: body (x forward, y left, z up, origin = CAD origin), metres. The point heights are
given relative to the floor (``gap_m``); callers add ``ground.crawler_bottom_z_m`` and any
lift themselves. The YAML is not modified here; it is read through ``Params.get`` or as a
plain mapping (``yaml.safe_load``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

LAYOUT_PATH = "contact.crawler.sphere_layout"
SUPPORTED_SCHEME = "rollers_plus_gapped_end_shoes"
ROLLER, END_SHOE = "roller", "end_shoe"


@dataclass(frozen=True)
class CrawlerContactLayout:
    """Crawler contact points (body frame, m). Order: left track then right track; per track
    rollers (``roller_x_m`` order) then end shoes (``end_shoe_x_m`` order)."""

    scheme: str
    track_centre_y_m: float
    sphere_radius_m: float
    xy_m: np.ndarray  # (n, 2)
    gap_m: np.ndarray  # (n,) height of the point bottom above the floor at the reference pose
    kind: tuple[str, ...]  # ROLLER or END_SHOE per point
    side: tuple[str, ...]  # "L" (+y) or "R" (-y) per point

    @property
    def n_points(self) -> int:
        return len(self.gap_m)

    @property
    def is_roller(self) -> np.ndarray:
        return np.array([k == ROLLER for k in self.kind])

    @property
    def x_extent_m(self) -> tuple[float, float]:
        """Smallest and largest x over all points (rollers and end shoes)."""
        return float(self.xy_m[:, 0].min()), float(self.xy_m[:, 0].max())

    def bottoms_m(self, floor_z_m: float, lift_m: float = 0.0) -> np.ndarray:
        """(n, 3) contact-point bottoms: z = floor + lift + gap."""
        return np.column_stack([self.xy_m, floor_z_m + lift_m + self.gap_m])

    def sphere_centres_m(self, floor_z_m: float, lift_m: float = 0.0) -> np.ndarray:
        """(n, 3) sphere centres: bottoms raised by the sphere radius."""
        centres = self.bottoms_m(floor_z_m, lift_m)
        centres[:, 2] += self.sphere_radius_m
        return centres

    def summary(self) -> dict:
        """JSON-ready description (for result files)."""
        return {
            "source": f"02_params/rexome33.yaml {LAYOUT_PATH}",
            "scheme": self.scheme,
            "n_points": self.n_points,
            "n_roller_points": int(self.is_roller.sum()),
            "n_end_shoe_points": int((~self.is_roller).sum()),
            "track_centre_y_m": self.track_centre_y_m,
            "x_extent_m": list(self.x_extent_m),
            "end_shoe_gap_range_m": [
                float(self.gap_m[~self.is_roller].min()),
                float(self.gap_m[~self.is_roller].max()),
            ],
            "sphere_radius_m": self.sphere_radius_m,
        }


def layout_from_mapping(layout: Mapping) -> CrawlerContactLayout:
    """Build the contact points from the ``contact.crawler.sphere_layout`` mapping."""
    scheme = str(layout["scheme"])
    if scheme != SUPPORTED_SCHEME:
        raise ValueError(
            f"{LAYOUT_PATH}.scheme = {scheme!r}; only {SUPPORTED_SCHEME!r} is supported"
        )
    yc = float(layout["track_centre_y_m"])
    rollers = np.asarray(layout["roller_x_m"], dtype=float)
    shoes = np.asarray(layout["end_shoe_x_m"], dtype=float)
    gaps = np.asarray(layout["end_shoe_gap_m"], dtype=float)
    radius = float(layout["sphere_radius_m"])
    if yc <= 0.0 or radius <= 0.0:
        raise ValueError(f"{LAYOUT_PATH}: track_centre_y_m and sphere_radius_m must be > 0")
    if rollers.ndim != 1 or shoes.ndim != 1 or not len(rollers) or shoes.shape != gaps.shape:
        raise ValueError(
            f"{LAYOUT_PATH}: roller_x_m, end_shoe_x_m, end_shoe_gap_m must be "
            "1-D lists; end_shoe_gap_m has one entry per end_shoe_x_m"
        )
    if (gaps < 0.0).any():
        raise ValueError(f"{LAYOUT_PATH}.end_shoe_gap_m must be >= 0 (unilateral, raised)")
    xy, gap, kind, side = [], [], [], []
    for label, y in (("L", yc), ("R", -yc)):
        for x in rollers:
            xy.append((x, y))
            gap.append(0.0)
            kind.append(ROLLER)
            side.append(label)
        for x, g in zip(shoes, gaps, strict=True):
            xy.append((x, y))
            gap.append(g)
            kind.append(END_SHOE)
            side.append(label)
    return CrawlerContactLayout(
        scheme, yc, radius, np.array(xy), np.array(gap), tuple(kind), tuple(side)
    )


def layout_from_params(params) -> CrawlerContactLayout:
    """Same from ``outrigger_sim.params.Params`` (``params.get``) or a plain YAML dict."""
    if isinstance(params, Mapping):
        node = params
        for key in LAYOUT_PATH.split("."):
            node = node[key]
        return layout_from_mapping(node)
    return layout_from_mapping(params.get(LAYOUT_PATH))
