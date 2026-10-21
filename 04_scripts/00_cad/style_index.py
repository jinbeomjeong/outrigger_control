"""Query the STEP colour index (C11) written by ``build_style_index.py`` (no STEP parsing).

Tables in ``01_cad/08_style/`` (keys of ``01_cad/06_brep/instances.csv``):

* ``instance_styles.csv``: per leaf instance, ``rgb_hex`` = display colour with the
  Inventor assembly appearance overrides (CDORSI) applied, ``part_rgb_hex`` = dominant colour
  of the part itself (face colour, else solid colour; what the OCCT XCAF reader attaches).
* ``prototype_styles.csv``: per prototype entry.
* ``face_styles.csv.gz``: per prototype face, ``face_index`` = ``TopExp_Explorer(prototype,
  TopAbs_FACE)`` order, the same numbering as ``01_cad/07_faces``.
* ``palette.csv``: the 60 distinct STEP colours.

Colours are the STEP ``COLOUR_RGB`` values (0..1 display values, sRGB) as ``#rrggbb``. The STEP
has no layers (0 ``PRESENTATION_LAYER_ASSIGNMENT``).

Example::

    import style_index

    colour = style_index.instance_colour(instance_path)              # "#ff4d06"
    colours = style_index.colours_for(paths, mode="part", default="#a8a7a0")
    faces = style_index.face_colours("0:1:1:2")                      # {face_index: "#..."}
"""

import csv
import functools
import gzip
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cad_common import CAD_DIR

STYLE_DIR = CAD_DIR / "08_style"
INSTANCE_STYLES_CSV = STYLE_DIR / "instance_styles.csv"
PROTOTYPE_STYLES_CSV = STYLE_DIR / "prototype_styles.csv"
FACE_STYLES_CSV = STYLE_DIR / "face_styles.csv.gz"
PALETTE_CSV = STYLE_DIR / "palette.csv"
MODES = ("display", "part")
FALLBACK_COLOUR = "#a8a7a0"  # analyze_parts.OTHER_PART_COLOR


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


@functools.cache
def _instances() -> dict[str, dict]:
    _warn_if_stale()
    return {row["instance_path"]: row for row in _read(INSTANCE_STYLES_CSV)}


@functools.cache
def _prototypes() -> dict[str, dict]:
    return {row["prototype_entry"]: row for row in _read(PROTOTYPE_STYLES_CSV)}


def instance_style(instance_path: str) -> dict:
    """Full row of ``instance_styles.csv`` (KeyError if the path is unknown)."""
    return _instances()[instance_path]


def instance_colour(instance_path: str, mode: str = "display",
                    default: str | None = FALLBACK_COLOUR) -> str | None:
    """``#rrggbb`` of a leaf instance.

    Args:
        instance_path: Key of ``06_brep/instances.csv`` / ``01_parts/parts.csv``.
        mode: ``"display"`` (assembly appearance overrides applied, as Inventor shows it) or
            ``"part"`` (the part's own dominant face colour, no overrides).
        default: Returned when the STEP gives no colour (one surface-only crawler shell).
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    row = _instances()[instance_path]
    value = row["rgb_hex"] if mode == "display" else row["part_rgb_hex"]
    return value or default


def colours_for(instance_paths, mode: str = "display",
                default: str | None = FALLBACK_COLOUR) -> list[str | None]:
    """:func:`instance_colour` for many paths (e.g. ``parts_classified.csv`` row order)."""
    return [instance_colour(path, mode, default) for path in instance_paths]


def transparency(instance_path: str) -> float:
    """STEP transparency of the display colour (0 opaque; 0.34 / 0.6 occur on glass)."""
    return float(_instances()[instance_path]["transparency"])


def prototype_style(prototype_entry: str) -> dict:
    """Row of ``prototype_styles.csv`` (solid / face colour counts, dominant colour)."""
    return _prototypes()[prototype_entry]


@functools.cache
def _faces() -> dict[str, dict[int, str]]:
    table: dict[str, dict[int, str]] = {}
    with gzip.open(FACE_STYLES_CSV, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            table.setdefault(row["prototype_entry"], {})[int(row["face_index"])] = row["rgb_hex"]
    return table


def face_colours(prototype_entry: str) -> dict[int, str]:
    """{face_index (07_faces numbering): '#rrggbb' or ''} of one prototype (no overrides)."""
    return dict(_faces().get(prototype_entry, {}))


def palette() -> list[dict]:
    """Rows of ``palette.csv`` (most used display colour first)."""
    return _read(PALETTE_CSV)


def clear_memory_cache() -> None:
    for function in (_instances, _prototypes, _faces):
        function.cache_clear()


def _warn_if_stale() -> None:
    try:
        from check_cache import warn_if_stale
    except ImportError:
        return
    warn_if_stale(["08_style"])
