"""Build a product/material index from the STEP file by streaming its text.

OpenCascade's XCAF reader does not expose the Inventor "material property"
entities reliably, so this script reads them straight from the Part 21 text.
It also records which length units the geometry contexts actually use.

Outputs (in ``cad/``):
    step_products.csv: one row per PRODUCT_DEFINITION with decoded name,
        description, material name, density and how often it is instanced.
    step_header.json: FILE_DESCRIPTION, originating system and unit findings.

Usage:
    python -I scripts/cad/step_text_index.py [--force]
"""

import argparse
import csv
import json
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cad_common import (
    PRODUCTS_CSV,
    STEP_HEADER_JSON,
    STEP_PATH,
    decode_step_string,
)

ENTITY_START = re.compile(r"^#(\d+)=([A-Z_0-9]*)\(")
WANTED_TYPES = {
    "PRODUCT",
    "PRODUCT_DEFINITION_FORMATION",
    "PRODUCT_DEFINITION",
    "PROPERTY_DEFINITION",
    "PROPERTY_DEFINITION_REPRESENTATION",
    "REPRESENTATION",
    "DESCRIPTIVE_REPRESENTATION_ITEM",
    "MEASURE_REPRESENTATION_ITEM",
    "NEXT_ASSEMBLY_USAGE_OCCURRENCE",
}
# Complex entities ("#N=(A() B() ...);") carry the unit definitions.
COMPLEX_TYPE = ""
HEADER_BYTES = 8192


# --------------------------------------------------------------------------
# Minimal Part 21 parameter parser
# --------------------------------------------------------------------------
class _ParameterParser:
    """Parses a STEP parameter list into Python values.

    Strings become ``str``, entity references ``int``, numbers ``float``,
    lists ``list`` and typed values such as ``POSITIVE_RATIO_MEASURE(7.85)``
    become ``(type_name, [arguments])``. ``$``, ``*`` and enumerations are
    returned as ``None``.
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self.position = 0

    def parse_list(self) -> list:
        assert self.text[self.position] == "("
        self.position += 1
        values: list = []
        while True:
            self._skip_spaces()
            if self.text[self.position] == ")":
                self.position += 1
                return values
            values.append(self._parse_value())
            self._skip_spaces()
            if self.text[self.position] == ",":
                self.position += 1

    def _skip_spaces(self) -> None:
        while self.text[self.position] in " \r\n\t":
            self.position += 1

    def _parse_value(self):
        character = self.text[self.position]
        if character == "'":
            return self._parse_string()
        if character == "(":
            return self.parse_list()
        if character == "#":
            return int(self._read_token()[1:])
        token = self._read_token()
        if self.position < len(self.text) and self.text[self.position] == "(":
            return (token, self.parse_list())
        try:
            return float(token)
        except ValueError:
            return None

    def _parse_string(self) -> str:
        self.position += 1
        start = self.position
        while True:
            closing = self.text.index("'", self.position)
            if closing + 1 < len(self.text) and self.text[closing + 1] == "'":
                self.position = closing + 2
                continue
            self.position = closing + 1
            return self.text[start:closing]

    def _read_token(self) -> str:
        start = self.position
        while self.text[self.position] not in ",()' \r\n\t":
            self.position += 1
        return self.text[start : self.position]


def parse_parameters(entity_text: str) -> list:
    """Return the parameters of ``#N=TYPE(...)`` as a Python list."""
    open_index = entity_text.index("(")
    return _ParameterParser(entity_text[open_index:]).parse_list()


# --------------------------------------------------------------------------
# Streaming reader
# --------------------------------------------------------------------------
@dataclass
class StepIndex:
    """Raw entity tables collected from the STEP text."""

    entities: dict[str, dict[int, list]] = field(default_factory=dict)
    complex_entities: dict[int, str] = field(default_factory=dict)
    type_counts: Counter = field(default_factory=Counter)


def _iter_entities(step_path: Path):
    """Yield ``(entity_id, type_name, full_text)`` for interesting entities."""
    buffer: list[str] = []
    current: tuple[int, str] | None = None
    with step_path.open("r", encoding="latin-1", newline="") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\r\n")
            if current is None:
                match = ENTITY_START.match(line)
                if match is None:
                    continue
                entity_id, type_name = int(match.group(1)), match.group(2)
                yield entity_id, type_name, None  # count every entity
                if type_name not in WANTED_TYPES and type_name != COMPLEX_TYPE:
                    continue
                current = (entity_id, type_name)
                buffer = [line]
            else:
                buffer.append(line)
            if line.endswith(";"):
                # Part 21 ignores line breaks, including those inside strings.
                yield current[0], current[1], "".join(buffer)
                current = None


def collect_index(step_path: Path) -> StepIndex:
    """Stream the STEP file once and keep the entities this review needs."""
    index = StepIndex()
    for entity_id, type_name, text in _iter_entities(step_path):
        if text is None:
            index.type_counts[type_name or "(complex)"] += 1
            continue
        if type_name == COMPLEX_TYPE:
            index.complex_entities[entity_id] = text
            continue
        table = index.entities.setdefault(type_name, {})
        table[entity_id] = parse_parameters(text)
    return index


# --------------------------------------------------------------------------
# Product / material table
# --------------------------------------------------------------------------
def _material_by_product_definition(index: StepIndex) -> dict[int, dict]:
    """Map PRODUCT_DEFINITION id -> {"material": str, "density": float}."""
    representation_of = {
        params[0]: params[1]
        for params in index.entities.get(
            "PROPERTY_DEFINITION_REPRESENTATION", {}
        ).values()
    }
    representations = index.entities.get("REPRESENTATION", {})
    descriptive_items = index.entities.get("DESCRIPTIVE_REPRESENTATION_ITEM", {})
    measure_items = index.entities.get("MEASURE_REPRESENTATION_ITEM", {})

    materials: dict[int, dict] = {}
    for prop_id, params in index.entities.get("PROPERTY_DEFINITION", {}).items():
        name, description, target = params[0], params[1], params[2]
        if name != "material property" or prop_id not in representation_of:
            continue
        item_ids = representations[representation_of[prop_id]][1]
        entry = materials.setdefault(target, {})
        for item_id in item_ids:
            if description == "material name" and item_id in descriptive_items:
                entry["material"] = decode_step_string(descriptive_items[item_id][0])
            if description == "density of part" and item_id in measure_items:
                _type_name, (value,) = measure_items[item_id][1]
                entry["density_g_cm3"] = value
    return materials


def build_product_rows(index: StepIndex) -> list[dict]:
    """Join PRODUCT_DEFINITION, PRODUCT, materials and usage counts."""
    products = index.entities["PRODUCT"]
    formations = index.entities["PRODUCT_DEFINITION_FORMATION"]
    usages = index.entities.get("NEXT_ASSEMBLY_USAGE_OCCURRENCE", {})
    child_usage_count = Counter(params[4] for params in usages.values())
    parent_usage_count = Counter(params[3] for params in usages.values())
    materials = _material_by_product_definition(index)

    rows = []
    for definition_id, params in sorted(index.entities["PRODUCT_DEFINITION"].items()):
        product_params = products[formations[params[2]][2]]
        material = materials.get(definition_id, {})
        rows.append(
            {
                "product_definition_id": definition_id,
                "product_name": decode_step_string(product_params[1]),
                "product_description": decode_step_string(product_params[2] or ""),
                "material": material.get("material", ""),
                "density_g_cm3": material.get("density_g_cm3", ""),
                "usage_count_as_child": child_usage_count[definition_id],
                "child_count": parent_usage_count[definition_id],
            }
        )
    return rows


# --------------------------------------------------------------------------
# Header and units
# --------------------------------------------------------------------------
def _read_header(step_path: Path) -> dict:
    head = step_path.read_bytes()[:HEADER_BYTES].decode("latin-1")
    description = re.search(
        r"FILE_DESCRIPTION\(\s*(?:/\*.*?\*/)?\s*\('(.*?)'\)", head, re.DOTALL
    )
    system = re.search(r"originating_system \*/ '(.*?)'", head)
    stamp = re.search(r"time_stamp \*/ '(.*?)'", head)
    schema = re.search(r"FILE_SCHEMA \(\('(.*?)'\)\)", head)
    return {
        "file_description": description.group(1) if description else None,
        "originating_system": system.group(1) if system else None,
        "time_stamp": stamp.group(1) if stamp else None,
        "schema": schema.group(1) if schema else None,
    }


def _describe_units(index: StepIndex) -> dict:
    """Report which unit entities the geometric contexts reference."""
    unit_text = {}
    contexts = {}
    for entity_id, text in index.complex_entities.items():
        si_unit = re.search(r"SI_UNIT\((.*?)\)", text)
        if si_unit and "UNIT()" in text:
            kind = re.search(r"(LENGTH|MASS|PLANE_ANGLE|SOLID_ANGLE)_UNIT", text)
            unit_text[entity_id] = {
                "kind": kind.group(1) if kind else "?",
                "si_unit": si_unit.group(1),
            }
        if "GEOMETRIC_REPRESENTATION_CONTEXT" in text:
            refs = re.search(
                r"GLOBAL_UNIT_ASSIGNED_CONTEXT\(\((.*?)\)\)", text, re.DOTALL
            )
            unit_refs = re.findall(r"#(\d+)", refs.group(1)) if refs else []
            contexts[entity_id] = [int(ref) for ref in unit_refs]

    context_length_units = Counter()
    for unit_refs in contexts.values():
        for ref in unit_refs:
            if unit_text.get(ref, {}).get("kind") == "LENGTH":
                context_length_units[unit_text[ref]["si_unit"]] += 1
    return {
        "unit_entities": {str(key): value for key, value in unit_text.items()},
        "geometric_context_count": len(contexts),
        "length_unit_used_by_geometric_contexts": dict(context_length_units),
    }


def _density_unit_note(index: StepIndex) -> dict:
    """Summarise the derived unit attached to the density measures."""
    measure_units = Counter(
        params[2]
        for params in index.entities.get("MEASURE_REPRESENTATION_ITEM", {}).values()
    )
    return {
        "density_measure_count": sum(measure_units.values()),
        "note": (
            "Density measures use DERIVED_UNIT(GRAM^1, CENTI METRE^3) as written by "
            "Inventor (the exponent sign is +3, but the values, e.g. 7.85 for steel, "
            "are g/cm^3)."
        ),
    }


def write_outputs(index: StepIndex, step_path: Path) -> None:
    rows = build_product_rows(index)
    PRODUCTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with PRODUCTS_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    header = _read_header(step_path)
    header["file_size_bytes"] = step_path.stat().st_size
    header["units"] = _describe_units(index)
    header["density"] = _density_unit_note(index)
    header["entity_counts_top"] = dict(index.type_counts.most_common(40))
    STEP_HEADER_JSON.write_text(
        json.dumps(header, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="rebuild even if cached")
    arguments = parser.parse_args()

    if PRODUCTS_CSV.exists() and STEP_HEADER_JSON.exists() and not arguments.force:
        print(f"cached: {PRODUCTS_CSV.name}, {STEP_HEADER_JSON.name} (use --force)")
        return
    started_s = time.perf_counter()
    index = collect_index(STEP_PATH)
    write_outputs(index, STEP_PATH)
    elapsed_s = time.perf_counter() - started_s
    print(f"wrote {PRODUCTS_CSV} and {STEP_HEADER_JSON} in {elapsed_s:.0f} s")


if __name__ == "__main__":
    main()
