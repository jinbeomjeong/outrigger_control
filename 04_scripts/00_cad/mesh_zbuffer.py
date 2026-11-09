"""Exact z-buffer rasteriser for the shaded CAD drawings (2026-11-09).

The drawing mesh ``render_mesh_v5.npz`` (build_render_mesh_v5.py) is the undecimated CAD
tessellation, 6.4 M triangles. Drawn as a matplotlib PolyCollection (one Path object per
triangle, painter sort) it needs tens of GB; the old decimated mesh (1.2 M triangles) already
took 6-14 GB per figure. This module draws the same triangles as one raster image:

* per output pixel x ``supersample`` (default 3 x 3), the nearest triangle wins (numba kernel,
  barycentric depth). Surfaces within ``tie`` [same unit as the depths, m] of the nearest one
  keep the painter rule (later triangle in centroid-depth order wins), so coplanar parts do
  not alternate pixel by pixel. Same kernel as the paper figure script fig1_layout.py
  (journal_v1/figscripts, 2026-11-08), which drew the V5 reference figures;
* the face colours of the visible triangles are box-averaged to the output pixels
  (anti-aliased fill, transparent where no triangle covers the pixel);
* optional outlines from the part-id / normal buffers: a part outline where the visible part
  changes, a crease where the normal of one part turns by more than ``crease_angle_deg``
  between neighbouring pixels. Hidden lines never appear. Parts flagged off in
  ``outline_parts`` (small parts, see render_layout_views.EdgeStyle.min_part_px) draw no
  outline against each other or against the parts around them.

The artist is a matplotlib ``Collection`` so that callers keep ``ax.add_collection(...)``. It
renders at draw time for the final axes box and renderer dpi; the triangles are mapped with
``transData`` (any affine axes, also inverted).

Units: ``polygons`` in data units (screen right / up, body m in the CAD scripts), ``depths``
toward the viewer in the same unit (larger = nearer).
"""

from __future__ import annotations

import numpy as np
from matplotlib.collections import Collection
from matplotlib.transforms import Bbox

try:
    from numba import njit
except ImportError:  # pragma: no cover
    njit = None

SUPERSAMPLE = 3
TIE_M = 5e-4  # depth tie band [m], as fig1_layout.ZBUFFER_TIE
STRIP_ROWS = 256  # output rows per colour / outline strip (memory bound)


if njit is not None:

    @njit(cache=True, nogil=True)
    def _zbuffer_kernel(u, v, z, w, h, index, zbuf, tie):  # pragma: no cover (numba)
        """u, v: (n, 3) pixel coordinates (pixel centres at integers, v downward); z: (n, 3)
        depth toward the viewer. Pixel centres inside or on a triangle are tested; the nearest
        surface wins, ties within ``tie`` go to the later triangle (painter order)."""
        for t in range(u.shape[0]):
            ax, ay, bx, by, cx, cy = u[t, 0], v[t, 0], u[t, 1], v[t, 1], u[t, 2], v[t, 2]
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-12:
                continue
            c0 = max(0, int(np.ceil(min(ax, bx, cx))))
            c1 = min(w - 1, int(np.floor(max(ax, bx, cx))))
            r0 = max(0, int(np.ceil(min(ay, by, cy))))
            r1 = min(h - 1, int(np.floor(max(ay, by, cy))))
            if c1 < c0 or r1 < r0:
                continue
            inv = 1.0 / den
            za, zb, zc = z[t, 0], z[t, 1], z[t, 2]
            for r in range(r0, r1 + 1):
                y = float(r)
                for c in range(c0, c1 + 1):
                    x = float(c)
                    l1 = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) * inv
                    if l1 < -1e-9:
                        continue
                    l2 = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) * inv
                    if l2 < -1e-9:
                        continue
                    l3 = 1.0 - l1 - l2
                    if l3 < -1e-9:
                        continue
                    d = l1 * za + l2 * zb + l3 * zc
                    if d >= zbuf[r, c] - tie:
                        if d > zbuf[r, c]:
                            zbuf[r, c] = d
                        index[r, c] = t


def available() -> bool:
    return njit is not None


def zbuffer_index(u: np.ndarray, v: np.ndarray, depths: np.ndarray, shape: tuple[int, int],
                  tie: float = TIE_M) -> np.ndarray:
    """Visible triangle per pixel (-1 = empty) for pixel coordinates u, v (n, 3)."""
    if njit is None:  # pragma: no cover
        raise RuntimeError("numba is required for the z-buffer renderer")
    rows, cols = shape
    index = np.full(shape, -1, dtype=np.int32)
    zbuf = np.full(shape, -np.inf)
    _zbuffer_kernel(np.ascontiguousarray(u, dtype=np.float64), np.ascontiguousarray(v, dtype=np.float64),
                    np.ascontiguousarray(depths, dtype=np.float64), cols, rows, index, zbuf, float(tie))
    return index


def _dilate(mask: np.ndarray, radius_px: int) -> np.ndarray:
    if radius_px <= 0:
        return mask
    padded = np.pad(mask, radius_px)
    height, width = mask.shape
    grown = np.zeros_like(mask)
    for dy in range(-radius_px, radius_px + 1):
        for dx in range(-radius_px, radius_px + 1):
            if dx * dx + dy * dy <= radius_px * radius_px:
                grown |= padded[radius_px + dy: radius_px + dy + height, radius_px + dx: radius_px + dx + width]
    return grown


class ZBufferCollection(Collection):
    """Triangles drawn as one z-buffered raster (module docstring)."""

    def __init__(self, polygons, depths, colours, *, part_ids=None, normals=None, outline_parts=None,
                 edge_colours=None, outline_width_pt: float = 0.0, crease_angle_deg: float = 35.0,
                 supersample: int = SUPERSAMPLE, tie: float = TIE_M, zorder: float = 1.8, **kwargs):
        super().__init__(zorder=zorder, **kwargs)
        polygons = np.asarray(polygons, dtype=np.float64)
        depths = np.asarray(depths, dtype=np.float64)
        centre = depths.mean(axis=1)
        # painter order (centroid depth, far first) decides the ties; no copy if already sorted
        order = None if np.all(centre[1:] >= centre[:-1]) else np.argsort(centre, kind="stable")

        def take(array, dtype):
            if array is None:
                return None
            array = np.asarray(array, dtype=dtype)
            return array if order is None else array[order]

        self._polygons = take(polygons, np.float64)
        self._depths = take(depths, np.float64)
        colours = take(colours, np.float32)
        self._colours = colours[:, :3]
        self._alpha = colours[:, 3] if colours.shape[1] == 4 else None
        if self._alpha is not None and np.all(self._alpha == 1.0):
            self._alpha = None
        self._part_ids = take(part_ids, np.int32)
        self._normals = take(normals, np.float32)
        self._outline_parts = None if outline_parts is None else np.asarray(outline_parts, dtype=bool)
        self._edge_colours = take(edge_colours, np.float32)
        self._outline_width_pt = float(outline_width_pt)
        self._cos_crease = float(np.cos(np.radians(crease_angle_deg)))
        self._supersample = int(supersample)
        self._tie = float(tie)
        self.stats: dict = {}

    # -- matplotlib -----------------------------------------------------------------------
    def get_datalim(self, transData):
        if len(self._polygons) == 0:
            return Bbox.null()
        xy = self._polygons.reshape(-1, 2)
        return Bbox([xy.min(axis=0), xy.max(axis=0)])

    def get_paths(self):
        return []

    def draw(self, renderer):
        if not self.get_visible() or len(self._polygons) == 0:
            return
        image, x0, y0 = self._render(renderer)
        if image is None:
            return
        gc = renderer.new_gc()
        gc.set_clip_rectangle(self.axes.bbox)
        clip_path = self.get_clip_path()
        if clip_path is not None:
            gc.set_clip_path(clip_path)
        renderer.draw_image(gc, x0, y0, image)
        gc.restore()
        self.stale = False

    # -- raster -----------------------------------------------------------------------------
    def _render(self, renderer):
        magnification = renderer.get_image_magnification()
        bx0, by0, bx1, by1 = self.axes.bbox.extents  # display units
        x0, y0 = int(np.floor(bx0)), int(np.floor(by0))
        cols_out = int(np.ceil(bx1 * magnification)) - int(np.floor(bx0 * magnification))
        rows_out = int(np.ceil(by1 * magnification)) - int(np.floor(by0 * magnification))
        if cols_out <= 0 or rows_out <= 0:
            return None, 0, 0
        k = self._supersample
        top = y0 + rows_out / magnification
        display = self.axes.transData.transform(self._polygons.reshape(-1, 2)).reshape(-1, 3, 2)
        u = (display[:, :, 0] - x0) * magnification * k - 0.5
        v = (top - display[:, :, 1]) * magnification * k - 0.5
        del display
        rows, cols = rows_out * k, cols_out * k
        index = zbuffer_index(u, v, self._depths, (rows, cols), self._tie)
        del u, v
        edges = self._part_ids is not None and self._outline_width_pt > 0
        width_px = self._outline_width_pt / 72.0 * renderer.dpi * magnification * k
        radius = max(0, int(round((width_px - 1.0) / 2.0)))
        out = np.zeros((rows_out, cols_out, 4), dtype=np.float32)
        line_pixels = 0
        band = STRIP_ROWS * k
        for r0 in range(0, rows, band):
            r1 = min(rows, r0 + band)
            # one-row / radius halo so outlines across strip borders are found
            h0, h1 = max(0, r0 - 1 - radius), min(rows, r1 + 1 + radius)
            sub = index[h0:h1]
            on = sub >= 0
            safe = np.where(on, sub, 0)
            premult = np.zeros((*sub.shape, 4), dtype=np.float32)
            alpha = np.where(on, 1.0 if self._alpha is None else self._alpha[safe], 0.0).astype(np.float32)
            premult[..., :3] = self._colours[safe] * alpha[..., None]
            premult[..., 3] = alpha
            if edges:
                line = self._lines(sub, on, safe, radius)
                line_pixels += int(line[(r0 - h0):(r1 - h0)].sum())
                colour = (self._edge_colours[safe] if self._edge_colours is not None
                          else np.zeros((*sub.shape, 3), dtype=np.float32))
                premult[line, :3] = colour[line]
                premult[line, 3] = 1.0
            premult = premult[(r0 - h0):(r1 - h0)]
            out[r0 // k:r1 // k] = premult.reshape((r1 - r0) // k, k, cols_out, k, 4).mean(axis=(1, 3))
        alpha = out[..., 3:4]
        out[..., :3] = np.where(alpha > 0, out[..., :3] / np.maximum(alpha, 1e-12), 0.0)
        self.stats = {"buffer_px": [int(rows), int(cols)], "supersample": k, "triangles": int(len(self._polygons)),
                      "covered_px": int((index >= 0).sum()), "outline_px": line_pixels,
                      "outline_radius_px": radius}
        image = np.round(np.clip(out, 0.0, 1.0) * 255).astype(np.uint8)
        # draw_image takes row 0 at the bottom (x0, y0 = lower left); the buffer has row 0 at top.
        return np.ascontiguousarray(image[::-1]), x0, y0

    def _lines(self, sub, on, safe, radius):
        """Outline + crease mask of one strip (buffer pixels)."""
        ids = np.where(on, self._part_ids[safe], 0)
        allowed = np.ones(int(ids.max()) + 1 if ids.size else 1, dtype=bool)
        if self._outline_parts is not None:
            n = min(len(allowed), len(self._outline_parts))
            allowed[:n] = self._outline_parts[:n]
        allowed[0] = True  # background
        ok = allowed[ids]
        seed = np.zeros(sub.shape, dtype=bool)
        normals = self._normals[safe] if self._normals is not None else None
        for axis in (0, 1):
            if axis == 0:
                a, b = (slice(None, -1), slice(None)), (slice(1, None), slice(None))
            else:
                a, b = (slice(None), slice(None, -1)), (slice(None), slice(1, None))
            ida, idb = ids[a], ids[b]
            pair_ok = ok[a] & ok[b]
            change = (ida != idb) & pair_ok
            seed[a] |= change
            if normals is not None:
                same = (ida == idb) & (ida > 0) & ok[a]
                dot = np.einsum("ijk,ijk->ij", normals[a], normals[b])
                seed[a] |= same & (dot < self._cos_crease)
        return _dilate(seed, radius)
