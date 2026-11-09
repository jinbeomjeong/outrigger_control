"""R8 C2 levelling-loop crossover frequency, read from the control-expert loop analysis.

``run_mast_bending_check.py`` compares the coupled rocking modes with the levelling loop
bandwidth. It used to carry the R7 constant 0.064 Hz (Kp 0.4 s^-1 / 2 pi, 50 Hz loop). The
R8 C2 value now comes from the loop analysis result:

    06_analysis/02_control/r8_10hz/d1/r8d1_final.json
    rows[*] = [row_name, {controller: {..., "wgc": {"z", "phi", "theta", "tw"}}}]

``wgc`` is the gain crossover in rad/s per channel (s6_control_spec.md 132.1: C2 0.11 ~ 0.21
rad/s). The row name is ``<level>_<support>_<beta>_<mast support>[_<variant>]``; the support
token is ``pads`` (crawler lifted, the levelling state) or ``crawler`` (legs retracted, crawler
on the floor). Only the pad rows are used: the crawler-supported roll crossover drops to about
0.017 Hz, which is not the levelling state, and the pad maximum is the conservative side for
the mode-coupling estimate (largest bandwidth, closest to the rocking band).

Like ``leg_extension_peaks.py`` this module does not import 03_src, so the dynamics checks stay
independent of the simulation code.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
R8D1_FINAL_JSON = PROJECT_ROOT / "06_analysis" / "02_control" / "r8_10hz" / "d1" / "r8d1_final.json"
CONTROLLER_KEY = "C2_tv0.1"  # R8 C2, valve time constant 0.1 s
CROSSOVER_KEY = "wgc"
ATTITUDE_AXES = ("phi", "theta")  # roll, pitch
PAD_SUPPORT = "pads"
CRAWLER_SUPPORT = "crawler"
KNOWN_SUPPORTS = (PAD_SUPPORT, CRAWLER_SUPPORT)
SUPPORT_TOKEN_INDEX = 1  # <level>_<support>_...
CROSSOVER_REPLACES = "R7 constant F_CROSSOVER_HZ 0.064 (Kp 0.4 s^-1 / 2 pi, 50 Hz loop)"
REDUCTION = (
    "max over the pad-supported rows (support token 'pads') of wgc phi and theta, / 2 pi; "
    "crawler-supported rows ('crawler') excluded"
)


class ControlCrossoverError(RuntimeError):
    """r8d1_final.json is missing, malformed, or holds no pad-supported row."""


@dataclass(frozen=True)
class LevellingCrossover:
    """Largest R8 C2 attitude-loop crossover of the pad-supported cases, with its provenance.

    Attributes:
        crossover_hz: Largest roll / pitch gain crossover over the pad rows [Hz].
        crossover_rad_s: The same value in rad/s.
        row_name: Row that carries the maximum.
        axis: Channel that carries the maximum (``phi`` or ``theta``).
        n_pad_rows: Number of pad-supported rows used.
        crawler_min_hz: Smallest roll / pitch crossover of the excluded crawler rows [Hz],
            ``None`` when the file has no crawler row.
        source: File, SHA-256, key path and reduction, for the result JSON.
    """

    crossover_hz: float
    crossover_rad_s: float
    row_name: str
    axis: str
    n_pad_rows: int
    crawler_min_hz: float | None
    source: dict[str, Any]


def _project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def _support_token(row_name: str, path: Path) -> str:
    parts = row_name.split("_")
    token = parts[SUPPORT_TOKEN_INDEX] if len(parts) > SUPPORT_TOKEN_INDEX else ""
    if token not in KNOWN_SUPPORTS:
        # An unknown support would be silently dropped or kept; stop instead.
        raise ControlCrossoverError(
            f"{path}: row {row_name!r} has support token {token!r}, expected one of "
            f"{KNOWN_SUPPORTS}"
        )
    return token


def _row_crossovers_rad_s(row: Any, path: Path) -> tuple[str, dict[str, float]]:
    """Return (row name, {axis: wgc rad/s}) of one ``rows`` entry."""
    if not (isinstance(row, list) and len(row) == 2 and isinstance(row[0], str)):
        raise ControlCrossoverError(f"{path}: a rows entry is not [name, results]")
    row_name, results = row
    controller = results.get(CONTROLLER_KEY) if isinstance(results, dict) else None
    crossover = controller.get(CROSSOVER_KEY) if isinstance(controller, dict) else None
    if not isinstance(crossover, dict):
        raise ControlCrossoverError(
            f"{path}: row {row_name!r} has no {CONTROLLER_KEY} / {CROSSOVER_KEY}"
        )
    values: dict[str, float] = {}
    for axis in ATTITUDE_AXES:
        value = crossover.get(axis)
        is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
        if not is_number or not math.isfinite(value) or value <= 0.0:
            raise ControlCrossoverError(
                f"{path}: row {row_name!r} {CONTROLLER_KEY} / {CROSSOVER_KEY} / {axis} is not "
                f"a positive number ({value!r})"
            )
        values[axis] = float(value)
    return row_name, values


def load_levelling_crossover(path: Path = R8D1_FINAL_JSON) -> LevellingCrossover:
    """Read the R8 C2 roll / pitch crossover and return the pad-supported maximum.

    Args:
        path: r8d1_final.json to read (default: the project result file).

    Returns:
        The maximum crossover over the pad rows and its provenance record.

    Raises:
        ControlCrossoverError: The file or a key is missing, a value is not a positive
            number, a row has an unknown support token, or no row is pad-supported.
    """
    if not path.is_file():
        raise ControlCrossoverError(f"{path} not found (control-expert R8 D1 loop analysis)")
    raw = path.read_bytes()
    tree = json.loads(raw.decode("utf-8"))
    rows = tree.get("rows") if isinstance(tree, dict) else None
    if not isinstance(rows, list):
        raise ControlCrossoverError(f"{path}: key 'rows' is not a list")

    pad_rows: list[tuple[str, dict[str, float]]] = []
    crawler_values_rad_s: list[float] = []
    for row in rows:
        row_name, values = _row_crossovers_rad_s(row, path)
        if _support_token(row_name, path) == PAD_SUPPORT:
            pad_rows.append((row_name, values))
        else:
            crawler_values_rad_s.extend(values.values())
    if not pad_rows:
        raise ControlCrossoverError(f"{path}: no pad-supported row (support token 'pads')")

    best_row, best_axis, best_rad_s = "", "", -math.inf
    for row_name, values in pad_rows:
        for axis, value in values.items():
            if value > best_rad_s:
                best_row, best_axis, best_rad_s = row_name, axis, value
    crawler_min_hz = min(crawler_values_rad_s) / (2.0 * math.pi) if crawler_values_rad_s else None

    source = {
        "file": _project_relative(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "key": f"rows[*][1] / {CONTROLLER_KEY} / {CROSSOVER_KEY} / {{phi, theta}} (rad/s)",
        "reduction": REDUCTION,
        "max_row": best_row,
        "max_axis": best_axis,
        "n_pad_rows": len(pad_rows),
        "n_crawler_rows_excluded": len(rows) - len(pad_rows),
        "crawler_rows_min_Hz": crawler_min_hz,
        "doc": "00_docs/04_control/s6_control_spec.md 132.1 (C2 crossover 0.11 ~ 0.21 rad/s)",
        "replaces": CROSSOVER_REPLACES,
    }
    return LevellingCrossover(
        crossover_hz=best_rad_s / (2.0 * math.pi),
        crossover_rad_s=best_rad_s,
        row_name=best_row,
        axis=best_axis,
        n_pad_rows=len(pad_rows),
        crawler_min_hz=crawler_min_hz,
        source=source,
    )
