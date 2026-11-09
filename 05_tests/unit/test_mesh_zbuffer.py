"""mesh_zbuffer.ZBufferCollection (CAD drawing rasteriser, 2026-11-09): orientation, nearest
surface wins, transparent background, outline at a part change."""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "04_scripts" / "00_cad"))
import mesh_zbuffer as mz  # noqa: E402

pytestmark = pytest.mark.skipif(not mz.available(), reason="numba missing")


def _square(x0, x1, y0, y1):
    return [[(x0, y0), (x1, y0), (x1, y1)], [(x0, y0), (x1, y1), (x0, y1)]]


def _render(outline_pt: float):
    # red square in the upper half (far), blue vertical bar over the full height (near)
    polygons = np.array(_square(0, 1, 0.5, 1) + _square(0.4, 0.6, 0, 1), float)
    depths = np.array([[0, 0, 0]] * 2 + [[1, 1, 1]] * 2, float)
    colours = np.array([[1, 0, 0]] * 2 + [[0, 0, 1]] * 2, float)
    figure, axes = plt.subplots(figsize=(2, 2), dpi=100)
    figure.subplots_adjust(0, 0, 1, 1)
    axes.set_xlim(0, 1)
    axes.set_ylim(0, 1)
    axes.set_axis_off()
    artist = mz.ZBufferCollection(polygons, depths, colours, part_ids=np.array([1, 1, 2, 2]),
                                  normals=np.tile([0, 0, 1.0], (4, 1)),
                                  outline_parts=np.array([True, True, True]), outline_width_pt=outline_pt)
    axes.add_collection(artist, autolim=False)
    figure.canvas.draw()
    image = np.asarray(figure.canvas.buffer_rgba())[:, :, :3].astype(int)
    plt.close(figure)
    return image, artist.stats


def test_orientation_and_depth():
    image, stats = _render(0.0)
    assert image.shape == (200, 200, 3)
    assert image[20, 20].tolist() == [255, 0, 0]      # upper left: red square
    assert image[180, 20].tolist() == [255, 255, 255]  # lower left: empty -> figure background
    assert image[20, 100].tolist() == [0, 0, 255]     # nearer blue bar over the red square
    assert image[180, 100].tolist() == [0, 0, 255]
    assert stats["outline_px"] == 0


def test_outline_at_part_change():
    image, stats = _render(0.72)
    assert stats["outline_px"] > 0
    row = image[20, 76:85].sum(axis=1)
    assert row.min() < 255  # darkened pixels at the red / blue boundary (x = 0.4 -> column 80)
    assert image[20, 20].tolist() == [255, 0, 0]
