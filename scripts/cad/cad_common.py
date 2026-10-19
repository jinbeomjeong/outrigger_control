"""Shared helpers for the CAD review scripts.

The scripts in this folder are run with ``python -I`` (isolated mode), which
keeps the script directory off ``sys.path``. Each script therefore inserts this
folder into ``sys.path`` explicitly before importing this module.
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STEP_PATH = PROJECT_ROOT / "REXOME33_Assy_r3(미니어쳐).stp"
CAD_DIR = PROJECT_ROOT / "cad"

PRODUCTS_CSV = CAD_DIR / "step_products.csv"
STEP_HEADER_JSON = CAD_DIR / "step_header.json"
PARTS_CSV = CAD_DIR / "parts.csv"
SUMMARY_JSON = CAD_DIR / "cad_summary.json"

MM_PER_M = 1000.0
# STEP stores densities in g/cm^3; 1 g/cm^3 = 1000 kg/m^3.
KG_PER_M3_PER_G_PER_CM3 = 1000.0

_X2_BLOCK = re.compile(r"\\X2\\([0-9A-Fa-f]*)\\X0\\")
_X4_BLOCK = re.compile(r"\\X4\\([0-9A-Fa-f]*)\\X0\\")
_X_SINGLE = re.compile(r"\\X\\([0-9A-Fa-f]{2})")


def _decode_hex_block(hex_text: str, digits_per_char: int) -> str:
    characters = []
    for start in range(0, len(hex_text), digits_per_char):
        code_point = int(hex_text[start : start + digits_per_char], 16)
        characters.append(chr(code_point))
    return "".join(characters)


def decode_step_string(raw: str) -> str:
    """Decode STEP (ISO 10303-21) string escapes into a Python string.

    Handles ``\\X2\\...\\X0\\`` (UCS-2), ``\\X4\\...\\X0\\`` (UCS-4),
    ``\\X\\HH`` (ISO 8859-1) and the doubled apostrophe ``''``.

    Args:
        raw: String content as written in the STEP file, without the
            surrounding apostrophes.

    Returns:
        The decoded text.
    """
    text = _X2_BLOCK.sub(lambda match: _decode_hex_block(match.group(1), 4), raw)
    text = _X4_BLOCK.sub(lambda match: _decode_hex_block(match.group(1), 8), text)
    text = _X_SINGLE.sub(lambda match: chr(int(match.group(1), 16)), text)
    return text.replace("''", "'")
