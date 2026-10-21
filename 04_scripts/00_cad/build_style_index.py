"""Build the STEP colour / layer index (track C11): which colour each part carries in the STEP.

The STEP file is scanned once as text (no full CAD load). Only the presentation entities and
the entities needed to walk from a styled item to its product are parsed:

* presentation: ``STYLED_ITEM``, ``OVER_RIDING_STYLED_ITEM``,
  ``CONTEXT_DEPENDENT_OVER_RIDING_STYLED_ITEM`` (CDORSI), ``PRESENTATION_STYLE_ASSIGNMENT``,
  ``SURFACE_STYLE_USAGE`` .. ``FILL_AREA_STYLE_COLOUR``, ``COLOUR_RGB``,
  ``DRAUGHTING_PRE_DEFINED_COLOUR``, ``SURFACE_STYLE_RENDERING_WITH_PROPERTIES``,
  ``SURFACE_STYLE_TRANSPARENT``, ``CURVE_STYLE``, ``PRESENTATION_LAYER_ASSIGNMENT``,
  ``INVISIBILITY``, ``GROUP`` / ``APPLIED_GROUP_ASSIGNMENT``,
  ``MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION``;
* structure: solids and shells, shape representations and their relationships,
  ``SHAPE_DEFINITION_REPRESENTATION`` -> ``PRODUCT_DEFINITION_SHAPE`` -> ``PRODUCT_DEFINITION``
  -> ``PRODUCT``, ``NEXT_ASSEMBLY_USAGE_OCCURRENCE`` (NAUO) and
  ``CONTEXT_DEPENDENT_SHAPE_REPRESENTATION`` (assembly placement relation -> NAUO).

Every other entity only gets its type recorded (one byte per entity id) so the type of a styled
item's target is known.

Colour resolution per leaf instance (same precedence as a STEP / XCAF viewer):

1. a CDORSI whose item is the shape representation of the instance or of one of its parent
   assemblies and whose style context (chain of assembly placement relations -> NAUOs) is a
   suffix of the instance's occurrence chain overrides everything below that occurrence;
2. a ``STYLED_ITEM`` on a ``MAPPED_ITEM`` (style of a placed sub-representation);
3. ``STYLED_ITEM`` on the solids / shell models of the prototype (part colour);
4. ``STYLED_ITEM`` on single faces (face colour; reported as face counts).

Outputs in ``01_cad/08_style/`` (keys match ``01_cad/06_brep/instances.csv``):

* ``instance_styles.csv``: one row per leaf instance (``instance_path``,
  ``prototype_entry``), resolved display colour ``rgb_hex`` / ``r g b`` (0..1, sRGB as written
  in the STEP), ``transparency`` (0 = opaque), ``colour_source``, number of distinct colours
  on the part and the colour of the part itself without instance override.
* ``prototype_styles.csv``: per prototype: styled solids / faces, distinct colours (solid
  level) and the dominant one.
* ``palette.csv``: every ``COLOUR_RGB`` with its use counts per level.
* ``style_summary.json``: entity counts, which levels carry colours, layers, groups,
  timings and the STEP size / modification time.

Optional ``--xcaf-check``: read the STEP with ``STEPCAFControl_Reader`` (colours and layers on,
~2-3 min, ~4 GB) and compare the XCAF colours of every leaf instance with the text result;
writes ``xcaf_check.json``. Query API: ``style_index.py``.

Usage:
    python -I 04_scripts/00_cad/build_style_index.py [--xcaf-check] [--no-pin]
"""

import argparse
import csv
import json
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import psutil

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cad_common import CAD_DIR, PROJECT_ROOT, STEP_PATH, decode_step_string

STYLE_DIR = CAD_DIR / "08_style"
INSTANCE_STYLES_CSV = STYLE_DIR / "instance_styles.csv"
PROTOTYPE_STYLES_CSV = STYLE_DIR / "prototype_styles.csv"
PALETTE_CSV = STYLE_DIR / "palette.csv"
FACE_STYLES_CSV = STYLE_DIR / "face_styles.csv.gz"
SUMMARY_JSON = STYLE_DIR / "style_summary.json"
XCAF_CHECK_JSON = STYLE_DIR / "xcaf_check.json"
INSTANCES_CSV = CAD_DIR / "06_brep" / "instances.csv"
PROTOTYPES_CSV = CAD_DIR / "06_brep" / "prototypes.csv"
PATH_SEPARATOR = " / "

PRESENTATION_TYPES = {
    "STYLED_ITEM",
    "OVER_RIDING_STYLED_ITEM",
    "CONTEXT_DEPENDENT_OVER_RIDING_STYLED_ITEM",
    "PRESENTATION_STYLE_ASSIGNMENT",
    "PRESENTATION_STYLE_BY_CONTEXT",
    "SURFACE_STYLE_USAGE",
    "SURFACE_SIDE_STYLE",
    "SURFACE_STYLE_FILL_AREA",
    "FILL_AREA_STYLE",
    "FILL_AREA_STYLE_COLOUR",
    "COLOUR_RGB",
    "DRAUGHTING_PRE_DEFINED_COLOUR",
    "SURFACE_STYLE_RENDERING",
    "SURFACE_STYLE_RENDERING_WITH_PROPERTIES",
    "SURFACE_STYLE_TRANSPARENT",
    "CURVE_STYLE",
    "PRESENTATION_LAYER_ASSIGNMENT",
    "INVISIBILITY",
    "GROUP",
    "APPLIED_GROUP_ASSIGNMENT",
    "MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION",
    "DRAUGHTING_MODEL",
}
STRUCTURE_TYPES = {
    "ADVANCED_FACE",
    "MANIFOLD_SOLID_BREP",
    "BREP_WITH_VOIDS",
    "SHELL_BASED_SURFACE_MODEL",
    "CLOSED_SHELL",
    "OPEN_SHELL",
    "ORIENTED_CLOSED_SHELL",
    "ADVANCED_BREP_SHAPE_REPRESENTATION",
    "MANIFOLD_SURFACE_SHAPE_REPRESENTATION",
    "SHAPE_REPRESENTATION",
    "GEOMETRICALLY_BOUNDED_WIREFRAME_SHAPE_REPRESENTATION",
    "SHAPE_REPRESENTATION_RELATIONSHIP",
    "SHAPE_DEFINITION_REPRESENTATION",
    "PRODUCT_DEFINITION_SHAPE",
    "PRODUCT_DEFINITION",
    "PRODUCT_DEFINITION_FORMATION",
    "PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE",
    "PRODUCT",
    "NEXT_ASSEMBLY_USAGE_OCCURRENCE",
    "CONTEXT_DEPENDENT_SHAPE_REPRESENTATION",
    "MAPPED_ITEM",
    "REPRESENTATION_MAP",
}
KEEP_TYPES = PRESENTATION_TYPES | STRUCTURE_TYPES
SOLID_LIKE = {"MANIFOLD_SOLID_BREP", "BREP_WITH_VOIDS", "SHELL_BASED_SURFACE_MODEL"}
REPRESENTATION_TYPES = {
    "ADVANCED_BREP_SHAPE_REPRESENTATION",
    "MANIFOLD_SURFACE_SHAPE_REPRESENTATION",
    "SHAPE_REPRESENTATION",
    "GEOMETRICALLY_BOUNDED_WIREFRAME_SHAPE_REPRESENTATION",
}

_HEAD = re.compile(rb"^#(\d+)\s*=\s*(\(?)\s*([A-Z_0-9]*)")
_SUBTYPE = re.compile(r"([A-Z_][A-Z_0-9]*)\s*\(")


# --------------------------------------------------------------------------
# STEP Part 21 parameter parsing (only for the kept entities)
# --------------------------------------------------------------------------
class Ref(int):
    """Entity reference ``#n``."""


def _parse_parameters(text: str, start: int) -> tuple[list, int]:
    """Parse ``( ... )`` starting at ``text[start] == '('``; return (values, index after ')')."""
    values: list = []
    i = start + 1
    n = len(text)
    while i < n:
        c = text[i]
        if c in " \r\n\t,":
            i += 1
        elif c == ")":
            return values, i + 1
        elif c == "(":
            inner, i = _parse_parameters(text, i)
            values.append(inner)
        elif c == "#":
            j = i + 1
            while j < n and text[j].isdigit():
                j += 1
            values.append(Ref(int(text[i + 1 : j])))
            i = j
        elif c == "'":
            j = i + 1
            chunks = []
            while True:
                k = text.index("'", j)
                if k + 1 < n and text[k + 1] == "'":
                    chunks.append(text[j : k + 2])
                    j = k + 2
                    continue
                chunks.append(text[j:k])
                break
            values.append(decode_step_string("".join(chunks).replace("\n", "").replace("\r", "")))
            i = k + 1
        elif c == "$" or c == "*":
            values.append(None)
            i += 1
        elif c == ".":
            j = text.index(".", i + 1)
            values.append(text[i : j + 1])  # enumeration / logical, kept as ".BOTH."
            i = j + 1
        elif c.isalpha() or c == "_":
            # typed parameter, e.g. LENGTH_MEASURE(1.)
            j = text.index("(", i)
            type_name = text[i:j].strip()
            inner, i = _parse_parameters(text, j)
            values.append((type_name, inner))
        else:
            j = i
            while j < n and text[j] not in ",)":
                j += 1
            token = text[i:j].strip()
            try:
                values.append(float(token))
            except ValueError:
                values.append(token)
            i = j
    raise ValueError("unbalanced parentheses")


def _parse_record(body: str) -> dict[str, list]:
    """Parse ``TYPE(args)`` or a complex ``(A(..)B(..))`` body into {type: args}."""
    body = body.strip()
    records: dict[str, list] = {}
    if body.startswith("("):
        i = 1
        while True:
            match = _SUBTYPE.search(body, i)
            if match is None:
                break
            name = match.group(1)
            args, i = _parse_parameters(body, match.end() - 1)
            records[name] = args
    else:
        match = _SUBTYPE.match(body)
        args, _ = _parse_parameters(body, match.end() - 1)
        records[match.group(1)] = args
    return records


@dataclass
class StepGraph:
    """Kept entities of the STEP file."""

    entities: dict[int, dict[str, list]] = field(default_factory=dict)
    type_code: np.ndarray | None = None  # entity id -> index into type_names (0 = unknown)
    type_names: list[str] = field(default_factory=lambda: [""])
    type_counts: Counter = field(default_factory=Counter)
    line_count: int = 0
    scan_s: float = 0.0

    def type_of(self, entity_id: int) -> str:
        if entity_id in self.entities:
            return next(iter(self.entities[entity_id]))
        if self.type_code is None or entity_id >= len(self.type_code):
            return ""
        return self.type_names[self.type_code[entity_id]]

    def get(self, entity_id: int, type_name: str | None = None) -> list | None:
        record = self.entities.get(entity_id)
        if record is None:
            return None
        if type_name is None:
            return next(iter(record.values()))
        return record.get(type_name)

    def ids_of(self, type_name: str) -> list[int]:
        return [key for key, record in self.entities.items() if type_name in record]


def scan_step(path: Path, log=print) -> StepGraph:
    """One text pass over the DATA section; keep only :data:`KEEP_TYPES` entities."""
    graph = StepGraph()
    codes = np.zeros(10_000_000, dtype=np.uint8)
    name_to_code: dict[str, int] = {}
    started_s = time.perf_counter()
    pending_id = None
    pending_parts: list[bytes] = []
    in_data = False
    with path.open("rb") as handle:
        for raw in handle:
            graph.line_count += 1
            if not in_data:
                if raw.startswith(b"DATA;"):
                    in_data = True
                continue
            if pending_id is not None:
                pending_parts.append(raw)
                if raw.rstrip().endswith(b";"):
                    body = b"".join(pending_parts).decode("latin-1").rstrip().rstrip(";")
                    graph.entities[pending_id] = _parse_record(body)
                    pending_id = None
                continue
            if raw[:1] != b"#":
                if raw.startswith(b"ENDSEC;"):
                    break
                continue
            match = _HEAD.match(raw)
            if match is None:
                continue
            entity_id = int(match.group(1))
            complex_entity = bool(match.group(2))
            type_name = match.group(3).decode()
            if complex_entity and not type_name:
                # "#n=(" alone on the line: the first subtype is on the next line; record as
                # complex and keep only if a kept subtype shows up (checked after joining).
                type_name = "(complex)"
            code = name_to_code.get(type_name)
            if code is None:
                code = len(graph.type_names)
                name_to_code[type_name] = code
                graph.type_names.append(type_name)
            if entity_id >= len(codes):
                codes = np.concatenate([codes, np.zeros(len(codes), dtype=np.uint8)])
            codes[entity_id] = code
            graph.type_counts[type_name] += 1
            keep = complex_entity or type_name in KEEP_TYPES
            if not keep:
                continue
            body_start = raw.index(b"=") + 1
            if raw.rstrip().endswith(b";"):
                body = raw[body_start:].decode("latin-1").rstrip().rstrip(";")
                graph.entities[entity_id] = _parse_record(body)
            else:
                pending_id = entity_id
                pending_parts = [raw[body_start:]]
    # complex entities: keep only those with a kept subtype (e.g. the transformation SRRs)
    for entity_id in [k for k, v in graph.entities.items() if not (set(v) & KEEP_TYPES)]:
        del graph.entities[entity_id]
    # recount complex entities by their kept subtype for the summary
    for record in graph.entities.values():
        if len(record) > 1:
            for name in record:
                graph.type_counts[f"(complex) {name}"] += 1
    graph.type_code = codes
    graph.scan_s = time.perf_counter() - started_s
    log(f"scanned {graph.line_count} lines in {graph.scan_s:.0f} s, kept {len(graph.entities)}")
    return graph


# --------------------------------------------------------------------------
# Style resolution
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Style:
    """Resolved presentation style of one PRESENTATION_STYLE_ASSIGNMENT."""

    rgb: tuple[float, float, float] | None
    transparency: float
    colour_id: int | None
    curve_rgb: tuple[float, float, float] | None = None

    @property
    def hex(self) -> str:
        return rgb_hex(self.rgb) if self.rgb else ""


def rgb_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02x}" for c in rgb)


def _colour(graph: StepGraph, colour_id: int) -> tuple[float, float, float] | None:
    record = graph.entities.get(colour_id, {})
    if "COLOUR_RGB" in record:
        _, r, g, b = record["COLOUR_RGB"]
        return (float(r), float(g), float(b))
    if "DRAUGHTING_PRE_DEFINED_COLOUR" in record:
        name = record["DRAUGHTING_PRE_DEFINED_COLOUR"][0]
        return PREDEFINED_COLOURS.get(name)
    return None


PREDEFINED_COLOURS = {
    "red": (1.0, 0.0, 0.0), "green": (0.0, 1.0, 0.0), "blue": (0.0, 0.0, 1.0),
    "yellow": (1.0, 1.0, 0.0), "magenta": (1.0, 0.0, 1.0), "cyan": (0.0, 1.0, 1.0),
    "black": (0.0, 0.0, 0.0), "white": (1.0, 1.0, 1.0),
}


def resolve_style(graph: StepGraph, psa_id: int) -> Style:
    """Walk PSA -> SURFACE_STYLE_USAGE -> ... -> colour; also rendering transparency."""
    rgb = None
    colour_id = None
    transparency = 0.0
    curve_rgb = None
    psa = graph.get(psa_id, "PRESENTATION_STYLE_ASSIGNMENT") or graph.get(
        psa_id, "PRESENTATION_STYLE_BY_CONTEXT")
    for style_id in (psa[0] if psa else []):
        if not isinstance(style_id, int):
            continue  # e.g. NULL_STYLE(.NULL.)
        record = graph.entities.get(style_id, {})
        if "SURFACE_STYLE_USAGE" in record:
            side_style = graph.get(record["SURFACE_STYLE_USAGE"][1], "SURFACE_SIDE_STYLE")
            for element_id in side_style[1]:
                element = graph.entities.get(element_id, {})
                if "SURFACE_STYLE_FILL_AREA" in element:
                    fill = graph.get(element["SURFACE_STYLE_FILL_AREA"][0], "FILL_AREA_STYLE")
                    for fill_colour_id in fill[1]:
                        fasc = graph.get(fill_colour_id, "FILL_AREA_STYLE_COLOUR")
                        if fasc:
                            colour_id = int(fasc[1])
                            rgb = _colour(graph, colour_id)
                elif "SURFACE_STYLE_RENDERING_WITH_PROPERTIES" in element:
                    _, render_colour, properties = element["SURFACE_STYLE_RENDERING_WITH_PROPERTIES"]
                    for property_id in properties:
                        transparent = graph.get(property_id, "SURFACE_STYLE_TRANSPARENT")
                        if transparent:
                            transparency = float(transparent[0])
                    if rgb is None and render_colour is not None:
                        colour_id = int(render_colour)
                        rgb = _colour(graph, colour_id)
        elif "CURVE_STYLE" in record:
            curve_colour = record["CURVE_STYLE"][3]
            if isinstance(curve_colour, Ref):
                curve_rgb = _colour(graph, curve_colour)
    return Style(rgb, transparency, colour_id, curve_rgb)


@dataclass
class Assembly:
    """Product / representation structure of the STEP assembly."""

    rep_product: dict[int, int]  # main shape representation -> PRODUCT_DEFINITION
    pd_name: dict[int, str]  # PRODUCT_DEFINITION -> product name
    item_rep: dict[int, int]  # representation item (solid, mapped item) -> representation
    rep_owner: dict[int, int]  # geometry representation -> main representation of its product
    shell_faces: dict[int, list[int]]
    solid_shells: dict[int, list[int]]
    srr_nauo: dict[int, int]  # assembly placement relation -> NAUO
    nauo: dict[int, tuple[str, int, int]]  # NAUO -> (name, parent PD, child PD)
    pd_reps: dict[int, list[int]]  # PRODUCT_DEFINITION -> main representations
    pd_children: dict[int, list[int]]  # parent PD -> NAUOs


def build_assembly(graph: StepGraph) -> Assembly:
    pdf_product = {}
    for key in graph.ids_of("PRODUCT_DEFINITION_FORMATION") + graph.ids_of(
        "PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE"
    ):
        args = graph.get(key)
        pdf_product[key] = int(args[2])
    pd_name = {}
    for key in graph.ids_of("PRODUCT_DEFINITION"):
        args = graph.get(key, "PRODUCT_DEFINITION")
        product = graph.get(pdf_product[int(args[2])], "PRODUCT")
        pd_name[key] = product[1] or product[0]
    pds_definition = {
        key: int(graph.get(key, "PRODUCT_DEFINITION_SHAPE")[2])
        for key in graph.ids_of("PRODUCT_DEFINITION_SHAPE")
    }
    rep_product: dict[int, int] = {}
    pd_reps: dict[int, list[int]] = defaultdict(list)
    for key in graph.ids_of("SHAPE_DEFINITION_REPRESENTATION"):
        definition, rep = graph.get(key, "SHAPE_DEFINITION_REPRESENTATION")
        target = pds_definition.get(int(definition))
        if target in pd_name:
            rep_product[int(rep)] = target
            pd_reps[target].append(int(rep))
    item_rep: dict[int, int] = {}
    for key, record in graph.entities.items():
        for name in record:
            if name in REPRESENTATION_TYPES:
                for item in record[name][1]:
                    item_rep.setdefault(int(item), key)
    # Non-transform SRRs tie geometry representations to the product's main representation.
    rep_owner: dict[int, int] = {}
    srr_nauo: dict[int, int] = {}
    cdsr_rel = {}
    for key in graph.ids_of("CONTEXT_DEPENDENT_SHAPE_REPRESENTATION"):
        relation, pds = graph.get(key, "CONTEXT_DEPENDENT_SHAPE_REPRESENTATION")
        cdsr_rel[int(relation)] = pds_definition.get(int(pds))
    for key, record in graph.entities.items():
        if "SHAPE_REPRESENTATION_RELATIONSHIP" not in record:
            continue
        if "REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION" in record:
            srr_nauo[key] = cdsr_rel.get(key)
            continue
        args = record["SHAPE_REPRESENTATION_RELATIONSHIP"]
        rep1, rep2 = int(args[2]), int(args[3])
        if rep1 in rep_product and rep2 not in rep_product:
            rep_owner[rep2] = rep1
        elif rep2 in rep_product and rep1 not in rep_product:
            rep_owner[rep1] = rep2
    for rep in rep_product:
        rep_owner.setdefault(rep, rep)
    nauo = {}
    pd_children: dict[int, list[int]] = defaultdict(list)
    for key in graph.ids_of("NEXT_ASSEMBLY_USAGE_OCCURRENCE"):
        args = graph.get(key, "NEXT_ASSEMBLY_USAGE_OCCURRENCE")
        nauo[key] = (args[1] or args[0], int(args[3]), int(args[4]))
        pd_children[int(args[3])].append(key)
    shell_faces = {}
    for name in ("CLOSED_SHELL", "OPEN_SHELL"):
        for key in graph.ids_of(name):
            shell_faces[key] = [int(face) for face in graph.get(key, name)[1]]
    solid_shells = {}
    for key in graph.ids_of("MANIFOLD_SOLID_BREP"):
        solid_shells[key] = [int(graph.get(key, "MANIFOLD_SOLID_BREP")[1])]
    for key in graph.ids_of("BREP_WITH_VOIDS"):
        name, outer, voids = graph.get(key, "BREP_WITH_VOIDS")
        shells = [int(outer)]
        for void in voids:  # ORIENTED_CLOSED_SHELL(name, *, closed shell, orientation)
            oriented = graph.get(int(void), "ORIENTED_CLOSED_SHELL")
            shells.append(int(oriented[2]) if oriented else int(void))
        solid_shells[key] = shells
    for key in graph.ids_of("SHELL_BASED_SURFACE_MODEL"):
        solid_shells[key] = [int(s) for s in graph.get(key, "SHELL_BASED_SURFACE_MODEL")[1]]
    return Assembly(rep_product, pd_name, item_rep, rep_owner, shell_faces, solid_shells,
                    srr_nauo, nauo, dict(pd_reps), dict(pd_children))


def main_rep_of_item(assembly: Assembly, item: int) -> int | None:
    rep = assembly.item_rep.get(item)
    if rep is None:
        return None
    return assembly.rep_owner.get(rep, rep)


def place_one_pcore() -> dict:
    """Pin this process to one P-core logical processor and switch off EcoQoS (Windows)."""
    info: dict = {"mode": "one_pcore"}
    if sys.platform != "win32":
        return info
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    fn = k32.GetSystemCpuSetInformation
    fn.argtypes = [ctypes.c_void_p, wintypes.ULONG, ctypes.POINTER(wintypes.ULONG),
                   wintypes.HANDLE, wintypes.ULONG]
    fn.restype = wintypes.BOOL
    need = wintypes.ULONG(0)
    fn(None, 0, ctypes.byref(need), None, 0)
    buffer = (ctypes.c_ubyte * need.value)()
    if not fn(buffer, need.value, ctypes.byref(need), None, 0):
        return info
    raw = bytes(buffer)
    sets, offset = [], 0
    while offset < need.value:
        size = int.from_bytes(raw[offset : offset + 4], "little")
        if int.from_bytes(raw[offset + 4 : offset + 8], "little") == 0:
            sets.append({"group": int.from_bytes(raw[offset + 12 : offset + 14], "little"),
                         "logical": raw[offset + 14], "efficiency_class": raw[offset + 18]})
        offset += size
    best = max(s["efficiency_class"] for s in sets)
    logical = sorted(s["logical"] for s in sets if s["efficiency_class"] == best and s["group"] == 0)
    chosen = logical[-1]
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    process = k32.GetCurrentProcess()
    k32.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    info["affinity_ok"] = bool(k32.SetProcessAffinityMask(process, 1 << chosen))
    info["logical_processor"] = chosen

    class PowerThrottlingState(ctypes.Structure):
        _fields_ = [("Version", wintypes.ULONG), ("ControlMask", wintypes.ULONG),
                    ("StateMask", wintypes.ULONG)]

    state = PowerThrottlingState(1, 0x1, 0x0)
    k32.SetProcessInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                          wintypes.DWORD]
    info["power_throttling_off_ok"] = bool(
        k32.SetProcessInformation(process, 4, ctypes.byref(state), ctypes.sizeof(state)))
    return info


# --------------------------------------------------------------------------
# Part and instance colours
# --------------------------------------------------------------------------
SURFACE_KIND = {
    "PLANE": "plane",
    "CYLINDRICAL_SURFACE": "cylinder",
    "CONICAL_SURFACE": "cone",
    "SPHERICAL_SURFACE": "sphere",
    "TOROIDAL_SURFACE": "torus",
    "B_SPLINE_SURFACE_WITH_KNOTS": "bspline",
}
LEVEL_OF_TARGET = {"ADVANCED_FACE": "face", "MAPPED_ITEM": "mapped_item", "POLYLINE": "curve"}


@dataclass
class PartStyle:
    """Colours written on one leaf product (prototype), faces in STEP solid / shell order."""

    pd: int
    name: str
    solid_ids: list[int]
    solid_styles: list[Style | None]
    face_ids: list[int] = field(default_factory=list)
    face_solid: list[int] = field(default_factory=list)  # index into solid_ids
    face_own: list[Style | None] = field(default_factory=list)  # style on the face itself
    face_kind: list[str] = field(default_factory=list)
    solid_reps: list[int] = field(default_factory=list)  # geometry representation per solid

    def subset(self, solid_indices: list[int]) -> "PartStyle":
        """The same part restricted to some solids (XCAF splits mixed products)."""
        keep = {old: new for new, old in enumerate(solid_indices)}
        part = PartStyle(self.pd, self.name, [self.solid_ids[i] for i in solid_indices],
                         [self.solid_styles[i] for i in solid_indices],
                         solid_reps=[self.solid_reps[i] for i in solid_indices])
        for i, solid in enumerate(self.face_solid):
            if solid in keep:
                part.face_ids.append(self.face_ids[i])
                part.face_solid.append(keep[solid])
                part.face_own.append(self.face_own[i])
                part.face_kind.append(self.face_kind[i])
        return part

    def effective(self, face: int) -> Style | None:
        own = self.face_own[face]
        return own if own is not None else self.solid_styles[self.face_solid[face]]

    def colour_counts(self) -> Counter:
        """(hex, transparency) -> number of faces showing it (face style, else solid style)."""
        return Counter(
            (style.hex, style.transparency) if style is not None and style.rgb else ("", 0.0)
            for style in (self.effective(i) for i in range(len(self.face_ids)))
        ) or Counter({("", 0.0): 0})

    def solid_colour_counts(self) -> Counter:
        return Counter(
            (style.hex, style.transparency) if style is not None and style.rgb else ("", 0.0)
            for style in self.solid_styles
        )


@dataclass
class Occurrence:
    names: tuple[str, ...]  # root product name, then NAUO names
    chain: tuple[int, ...]  # NAUO ids, root first
    pd: int

    @property
    def path(self) -> str:
        return PATH_SEPARATOR.join(self.names)


def leaf_occurrences(assembly: Assembly) -> list[Occurrence]:
    """All leaf occurrences of the product tree (path names as in ``instances.csv``)."""
    child_pds = {child for _, _, child in assembly.nauo.values()}
    roots = [pd for pd in assembly.pd_children if pd not in child_pds]
    leaves: list[Occurrence] = []
    pending = [Occurrence((assembly.pd_name[root],), (), root) for root in roots]
    while pending:
        occurrence = pending.pop()
        children = assembly.pd_children.get(occurrence.pd)
        if not children:
            leaves.append(occurrence)
            continue
        for nauo_id in children:
            name, _, child = assembly.nauo[nauo_id]
            pending.append(
                Occurrence((*occurrence.names, name), (*occurrence.chain, nauo_id), child))
    return leaves


def part_styles(graph: StepGraph, assembly: Assembly, styled: dict[int, Style],
                pds: set[int]) -> dict[int, PartStyle]:
    """Solid and face styles of every product definition in ``pds``."""
    owned: dict[int, list[int]] = defaultdict(list)
    for rep, owner in assembly.rep_owner.items():
        owned[owner].append(rep)
    parts = {}
    for pd in pds:
        solids: list[int] = []
        solid_reps: list[int] = []
        for main_rep in assembly.pd_reps.get(pd, []):
            reps = sorted(owned.get(main_rep, [main_rep]), key=lambda r: r != main_rep)
            for rep in reps:
                for name, args in graph.entities.get(rep, {}).items():
                    if name in REPRESENTATION_TYPES:
                        items = [int(i) for i in args[1] if graph.type_of(int(i)) in SOLID_LIKE]
                        solids += items
                        solid_reps += [rep] * len(items)
        part = PartStyle(pd, assembly.pd_name[pd], solids, [styled.get(s) for s in solids],
                         solid_reps=solid_reps)
        for solid_index, solid in enumerate(solids):
            for shell in assembly.solid_shells.get(solid, []):
                for face in assembly.shell_faces.get(shell, []):
                    part.face_ids.append(face)
                    part.face_solid.append(solid_index)
                    part.face_own.append(styled.get(face))
                    surface = graph.get(face, "ADVANCED_FACE")[2]
                    part.face_kind.append(SURFACE_KIND.get(graph.type_of(int(surface)), "other"))
        parts[pd] = part
    return parts


@dataclass
class Override:
    style: Style
    entity_id: int
    chain: tuple[int, ...]
    names: tuple[str, ...]


def instance_overrides(graph: StepGraph, assembly: Assembly, root_name: str
                       ) -> tuple[dict[tuple[int, ...], Override], list[str]]:
    """CDORSI -> {NAUO chain (root first): override} and a list of consistency problems."""
    overrides: dict[tuple[int, ...], Override] = {}
    problems: list[str] = []
    for key in graph.ids_of("CONTEXT_DEPENDENT_OVER_RIDING_STYLED_ITEM"):
        _, styles, item, _, context = graph.get(key, "CONTEXT_DEPENDENT_OVER_RIDING_STYLED_ITEM")
        chain = tuple(assembly.srr_nauo.get(int(c)) for c in context)
        if None in chain:
            problems.append(f"#{key}: style context is not an assembly placement")
            continue
        for parent, child in zip(chain, chain[1:]):
            if assembly.nauo[parent][2] != assembly.nauo[child][1]:
                problems.append(f"#{key}: style context chain is not contiguous")
        if assembly.pd_name.get(assembly.nauo[chain[0]][1]) != root_name:
            problems.append(f"#{key}: style context does not start at the root")
        if assembly.rep_product.get(int(item)) != assembly.nauo[chain[-1]][2]:
            problems.append(f"#{key}: item is not the representation of the last occurrence")
        names = (root_name, *(assembly.nauo[n][0] for n in chain))
        if chain in overrides:
            problems.append(f"#{key}: second override for {PATH_SEPARATOR.join(names)}")
        overrides[chain] = Override(resolve_style(graph, int(styles[0])), key, chain, names)
    return overrides, problems


def _fmt(value: float) -> str:
    return f"{value:.6g}"


def _write_csv(path: Path, rows: list[dict], gz: bool = False) -> None:
    import gzip

    opener = (lambda: gzip.open(path, "wt", encoding="utf-8", newline="")) if gz else (
        lambda: path.open("w", encoding="utf-8-sig", newline=""))
    with opener() as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _hex_rgb(hex_text: str) -> tuple[float, float, float]:
    return tuple(int(hex_text[i : i + 2], 16) / 255.0 for i in (1, 3, 5))


def _entry_key(entry: str) -> list[int]:
    return [int(x) for x in entry.split(":")] if entry else [10**9]


def compare_face_kinds(face_rows: list[dict]) -> dict:
    """Surface kind per (prototype_entry, face_index) vs the C5 face index (07_faces).

    STEP order equals TopExp order if the kinds agree everywhere (B-spline-like STEP surfaces
    written as complex entities are "other" here and count as a match for "bspline").
    """
    import gzip

    path = CAD_DIR / "07_faces" / "prototype_faces.csv.gz"
    if not path.exists():
        return {"available": False}
    ours = {(row["prototype_entry"], row["face_index"]): row["kind"] for row in face_rows}
    compared = equal = 0
    examples = []
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row["prototype_entry"], int(row["face_index"]))
            if key not in ours:
                examples.append({"missing": list(key)}) if len(examples) < 5 else None
                continue
            compared += 1
            kind = ours[key]
            if kind == row["kind"] or (kind == "other" and row["kind"] == "bspline"):
                equal += 1
            elif len(examples) < 5:
                examples.append({"key": list(key), "step": kind, "faces_index": row["kind"]})
    return {"available": True, "rows_compared": compared, "rows_equal": equal,
            "examples": examples}


def build(log=print) -> dict:
    """Scan the STEP, resolve colours, write the tables and the summary."""
    timings: dict[str, float] = {}
    started_s = time.perf_counter()
    graph = scan_step(STEP_PATH, log)
    timings["text_scan_s"] = graph.scan_s
    phase_s = time.perf_counter()
    assembly = build_assembly(graph)
    styled: dict[int, Style] = {}
    target_types: Counter = Counter()
    psa_cache: dict[int, Style] = {}
    for key in graph.ids_of("STYLED_ITEM"):
        _, styles, item = graph.get(key, "STYLED_ITEM")
        target_types[graph.type_of(int(item))] += 1
        psa = int(styles[0])
        if psa not in psa_cache:
            psa_cache[psa] = resolve_style(graph, psa)
        if int(item) in styled:
            raise RuntimeError(f"two STYLED_ITEMs on #{item}")
        styled[int(item)] = psa_cache[psa]

    leaves = leaf_occurrences(assembly)
    roots = {occurrence.names[0] for occurrence in leaves}
    if len(roots) != 1:
        raise RuntimeError(f"expected one root product, got {roots}")
    root_name = roots.pop()
    overrides, override_problems = instance_overrides(graph, assembly, root_name)
    parts = part_styles(graph, assembly, styled, {occurrence.pd for occurrence in leaves})

    with INSTANCES_CSV.open(encoding="utf-8-sig", newline="") as handle:
        cache_rows = list(csv.DictReader(handle))
    cache_by_path = {row["instance_path"]: row for row in cache_rows}
    by_path: dict[str, list[Occurrence]] = defaultdict(list)
    for occurrence in leaves:
        by_path[occurrence.path].append(occurrence)
    duplicates = {path: len(items) for path, items in by_path.items() if len(items) > 1}
    unmatched_text = sorted(set(by_path) - set(cache_by_path))
    unmatched_cache = sorted(set(cache_by_path) - set(by_path))
    # XCAF splits a product whose shape representation mixes solids, surface models and
    # wireframes into unnamed sub-components "=>[entry]"; map each to the matching group of
    # representation items (same face count) of the parent product.
    with PROTOTYPES_CSV.open(encoding="utf-8-sig", newline="") as handle:
        prototype_counts = {row["prototype_entry"]: row for row in csv.DictReader(handle)}
    split_parts: dict[str, PartStyle] = {}
    split_notes: dict[str, str] = {}
    for path in unmatched_cache:
        parent, _, last = path.rpartition(PATH_SEPARATOR)
        if not last.startswith("=>[") or parent not in by_path:
            raise RuntimeError(f"instances.csv path not found in the STEP text: {path}")
        entry = cache_by_path[path]["prototype_entry"]
        whole = parts[by_path[parent][0].pd]
        groups: dict[int, list[int]] = defaultdict(list)
        for index, rep in enumerate(whole.solid_reps):
            groups[rep].append(index)
        want = int(prototype_counts[entry]["face_count"])
        matches = [idx for idx in groups.values() if len(whole.subset(idx).face_ids) == want]
        if len(matches) == 1:
            split_parts[path] = whole.subset(matches[0])
            split_notes[path] = f"representation group with {want} faces of the parent product"
        else:
            split_parts[path] = whole.subset([]) if want == 0 else whole
            split_notes[path] = ("no faces: no colour of its own" if want == 0
                                 else "no unique face-count match: whole parent part")

    # prototype entry <-> STEP product definition (must be one-to-one)
    entry_pd: dict[str, set[int]] = defaultdict(set)
    for path, items in by_path.items():
        if path in cache_by_path:
            entry_pd[cache_by_path[path]["prototype_entry"]].update(o.pd for o in items)
    ambiguous_entries = {entry: sorted(pds) for entry, pds in entry_pd.items() if len(pds) > 1}
    pd_entry = {next(iter(pds)): entry for entry, pds in entry_pd.items() if len(pds) == 1}

    # ---- instance rows
    instance_rows = []
    resolved_uses: Counter = Counter()
    source_counts: Counter = Counter()
    entry_part: dict[str, PartStyle] = {}
    for row in cache_rows:
        path = row["instance_path"]
        if path in split_parts:
            occurrence = by_path[path.rpartition(PATH_SEPARATOR)[0]][0]
            part = split_parts[path]
        else:
            occurrence = by_path[path][0]
            part = parts[occurrence.pd]
        entry_part[row["prototype_entry"]] = part
        counts = part.colour_counts()
        (part_hex, part_transparency), part_faces = counts.most_common(1)[0]
        override = None
        for depth in range(len(occurrence.chain), 0, -1):
            override = overrides.get(occurrence.chain[:depth])
            if override is not None:
                break
        if override is not None and override.style.rgb:
            rgb_value, transparency = override.style.hex, override.style.transparency
            source = ("instance_override" if len(override.chain) == len(occurrence.chain)
                      else "assembly_override")
            override_path = PATH_SEPARATOR.join(override.names)
        else:
            rgb_value, transparency = part_hex, part_transparency
            source = "part" if part_hex else "none"
            override_path = ""
        source_counts[source] += 1
        resolved_uses[rgb_value] += 1
        r, g, b = _hex_rgb(rgb_value) if rgb_value else (float("nan"),) * 3
        instance_rows.append({
            "instance_path": row["instance_path"],
            "prototype_entry": row["prototype_entry"],
            "product_name": row["product_name"],
            "top_assembly": row["top_assembly"],
            "rgb_hex": rgb_value,
            "r": _fmt(r), "g": _fmt(g), "b": _fmt(b),
            "transparency": _fmt(transparency),
            "colour_source": source,
            "override_path": override_path,
            "override_step_id": f"#{override.entity_id}" if override is not None else "",
            "part_rgb_hex": part_hex,
            "part_face_share": _fmt(part_faces / max(1, len(part.face_ids))),
            "part_colour_count": len([key for key in counts if key[0]]),
            "layer": "",
        })

    # ---- prototype rows and face-level rows
    prototype_rows = []
    face_rows = []
    for entry, part in sorted(entry_part.items(), key=lambda item: _entry_key(item[0])):
        pd = part.pd
        counts = part.colour_counts()
        (dominant, transparency), dominant_faces = counts.most_common(1)[0]
        differing = 0
        for i, face in enumerate(part.face_ids):
            own = part.face_own[i]
            solid_style = part.solid_styles[part.face_solid[i]]
            if own is not None and solid_style is not None and own.hex != solid_style.hex:
                differing += 1
            shown = own if own is not None else solid_style
            face_rows.append({
                "prototype_entry": entry,
                "face_index": i,  # = TopExp_Explorer(prototype, FACE) order (xcaf_check.json)
                "solid_order": part.face_solid[i],
                "step_face_id": f"#{face}",
                "kind": part.face_kind[i],
                "rgb_hex": shown.hex if shown is not None else "",
                "transparency": _fmt(shown.transparency) if shown is not None else "",
                "source": "face" if own is not None else ("solid" if shown is not None else "none"),
                "solid_rgb_hex": solid_style.hex if solid_style is not None else "",
            })
        prototype_rows.append({
            "prototype_entry": entry,
            "product_name": prototype_counts[entry]["product_name"],
            "step_product": part.name,
            "step_product_definition": f"#{pd}",
            "solid_count": len(part.solid_ids),
            "styled_solid_count": sum(s is not None for s in part.solid_styles),
            "face_count": len(part.face_ids),
            "styled_face_count": sum(s is not None for s in part.face_own),
            "faces_differing_from_solid": differing,
            "dominant_rgb_hex": dominant,
            "dominant_face_share": _fmt(dominant_faces / max(1, len(part.face_ids))),
            "transparency": _fmt(transparency),
            "solid_colours": ";".join(
                f"{h or 'none'}:{n}" for (h, _), n in part.solid_colour_counts().most_common()),
            "face_colours": ";".join(
                f"{h or 'none'}:{n}" for (h, _), n in counts.most_common() if n),
        })

    # ---- palette
    uses: dict[str, Counter] = defaultdict(Counter)
    transparencies: dict[str, set] = defaultdict(set)
    for item, style in styled.items():
        if style.rgb is None:
            continue
        uses[style.hex][LEVEL_OF_TARGET.get(graph.type_of(item), "solid")] += 1
        transparencies[style.hex].add(style.transparency)
    for override in overrides.values():
        if override.style.rgb:
            uses[override.style.hex]["instance_override"] += 1
            transparencies[override.style.hex].add(override.style.transparency)
    colour_ids: dict[str, list[int]] = defaultdict(list)
    for key in graph.ids_of("COLOUR_RGB"):
        colour_ids[rgb_hex(_colour(graph, key))].append(key)
    palette_rows = []
    for hex_value in sorted(colour_ids, key=lambda h: (-resolved_uses[h], -sum(uses[h].values()))):
        r, g, b = _colour(graph, colour_ids[hex_value][0])
        palette_rows.append({
            "rgb_hex": hex_value, "r": _fmt(r), "g": _fmt(g), "b": _fmt(b),
            "colour_rgb_entities": len(colour_ids[hex_value]),
            "transparency": ";".join(_fmt(t) for t in sorted(transparencies[hex_value])),
            "solid_uses": uses[hex_value]["solid"],
            "face_uses": uses[hex_value]["face"],
            "instance_override_uses": uses[hex_value]["instance_override"],
            "curve_uses": uses[hex_value]["curve"],
            "instances_resolved": resolved_uses[hex_value],
        })
    timings["resolve_s"] = time.perf_counter() - phase_s

    STYLE_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(INSTANCE_STYLES_CSV, instance_rows)
    _write_csv(PROTOTYPE_STYLES_CSV, prototype_rows)
    _write_csv(PALETTE_CSV, palette_rows)
    _write_csv(FACE_STYLES_CSV, face_rows, gz=True)
    face_index_check = compare_face_kinds(face_rows)

    solids_total = sum(1 for record in graph.entities.values() if set(record) & SOLID_LIKE)
    step_stat = STEP_PATH.stat()
    summary = {
        "description": "STEP colour / layer index (C11): presentation entities of the STEP file "
                       "resolved to prototypes and leaf instances",
        "generator": Path(__file__).resolve().relative_to(PROJECT_ROOT).as_posix(),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "step": {"path": STEP_PATH.name, "size_bytes": step_stat.st_size,
                 "mtime": time.strftime("%Y-%m-%dT%H:%M:%S",
                                        time.localtime(step_stat.st_mtime)),
                 "mtime_ns": step_stat.st_mtime_ns},
        "method": "one text pass over the DATA section (no CAD kernel); STYLED_ITEM targets "
                  "resolved to faces / solids / products, CDORSI style contexts resolved to "
                  "NAUO chains; keys joined to 06_brep/instances.csv by instance_path",
        "entity_counts": {name: graph.type_counts.get(name, 0)
                          for name in sorted(PRESENTATION_TYPES)},
        "data_lines": graph.line_count,
        "styled_item_targets": dict(target_types),
        "levels": {
            "layer": "none: 0 PRESENTATION_LAYER_ASSIGNMENT",
            "solid": f"{target_types['MANIFOLD_SOLID_BREP'] + target_types['BREP_WITH_VOIDS']} "
                     f"of {solids_total} solids / shell models styled",
            "face": f"{target_types['ADVANCED_FACE']} of "
                    f"{graph.type_counts.get('ADVANCED_FACE', 0)} faces styled",
            "instance_override": f"{len(overrides)} CDORSI (colour of an assembly occurrence)",
            "curve": f"{target_types['POLYLINE']} POLYLINE styled",
            "mapped_item": f"{target_types['MAPPED_ITEM']} MAPPED_ITEM styled (NULL_STYLE, the "
                           "overridden style of all CDORSI)",
        },
        "colours": {
            "colour_rgb_entities": graph.type_counts.get("COLOUR_RGB", 0),
            "distinct_rgb": len(colour_ids),
            "presentation_style_assignments": len(psa_cache),
            "transparencies": sorted({_fmt(s.transparency) for s in psa_cache.values()}),
        },
        "groups": [
            {"name": graph.get(int(graph.get(k)[0]))[0],
             "items": dict(Counter(graph.type_of(int(i)) for i in graph.get(k)[1]))}
            for k in graph.ids_of("APPLIED_GROUP_ASSIGNMENT")],
        "override_chain_depths": dict(Counter(len(o.chain) for o in overrides.values())),
        "override_problems": override_problems,
        "instances": {
            "leaf_occurrences_text": len(leaves),
            "instances_csv_rows": len(cache_rows),
            "duplicate_paths_text": duplicates,
            "unmatched_text_paths": unmatched_text[:20],
            "unmatched_text_path_count": len(unmatched_text),
            "ambiguous_prototype_entries": ambiguous_entries,
            "xcaf_split_sub_components": split_notes,
            "colour_source_counts": dict(source_counts),
            "instances_with_multi_colour_parts": sum(
                1 for row in instance_rows if row["part_colour_count"] > 1),
        },
        "prototypes": {
            "count": len(prototype_rows),
            "with_face_styles": sum(1 for row in prototype_rows if row["styled_face_count"]),
            "with_faces_differing_from_solid": sum(
                1 for row in prototype_rows if row["faces_differing_from_solid"]),
            "faces_differing_from_solid": sum(
                row["faces_differing_from_solid"] for row in prototype_rows),
            "multi_colour": sum(1 for row in prototype_rows if ";" in row["face_colours"]),
            "face_rows": len(face_rows),
            "face_rows_with_own_style": sum(row["source"] == "face" for row in face_rows),
        },
        "face_index_check_vs_07_faces": face_index_check,
        "colour_note": "r g b = COLOUR_RGB values as written by Inventor (0..1 display values, "
                       "not linearised); rgb_hex = round(255 * value). Face order: solid by "
                       "solid in representation item order, shell by shell, face list order.",
        "timings_s": {key: round(value, 2) for key, value in timings.items()},
    }
    summary["timings_s"]["total_s"] = round(time.perf_counter() - started_s, 2)
    summary["peak_memory_gb"] = round(
        getattr(psutil.Process().memory_info(), "peak_wset", 0) / 1e9, 2)
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"wrote {STYLE_DIR} in {summary['timings_s']['total_s']:.0f} s")
    return {"summary": summary, "parts": parts, "pd_entry": pd_entry,
            "instance_rows": instance_rows, "entry_part": entry_part,
            "overrides": [(PATH_SEPARATOR.join(o.names), o.style.hex, len(o.chain), o.entity_id)
                          for o in overrides.values()]}


# --------------------------------------------------------------------------
# Optional cross-check with the OCCT XCAF reader (colours and layers on)
# --------------------------------------------------------------------------
def _quantity_hex(colour) -> tuple[str, str]:
    """(hex of the sRGB values, hex of the linear values) of a Quantity_Color."""
    from OCC.Core.Quantity import Quantity_TOC_RGB, Quantity_TOC_sRGB

    def values(kind):
        try:
            return colour.Values(kind)
        except TypeError:  # older wrappers with out-parameters
            return colour.Red(), colour.Green(), colour.Blue()

    return rgb_hex(values(Quantity_TOC_sRGB)), rgb_hex(values(Quantity_TOC_RGB))


def xcaf_check(result: dict, log=print) -> dict:
    """Compare the text result with the colours the OCCT XCAF reader attaches."""
    from OCC.Core.IFSelect import IFSelect_RetDone
    from OCC.Core.Quantity import Quantity_Color
    from OCC.Core.STEPCAFControl import STEPCAFControl_Reader
    from OCC.Core.TCollection import TCollection_ExtendedString
    from OCC.Core.TDF import TDF_LabelSequence
    from OCC.Core.TDocStd import TDocStd_Document
    from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_SOLID
    from OCC.Core.TopExp import TopExp_Explorer, topexp
    from OCC.Core.TopLoc import TopLoc_Location
    from OCC.Core.TopTools import TopTools_IndexedMapOfShape
    from OCC.Core.XCAFApp import XCAFApp_Application
    from OCC.Core.XCAFDoc import (
        XCAFDoc_ColorGen,
        XCAFDoc_ColorSurf,
        XCAFDoc_ColorTool,
        XCAFDoc_DocumentTool,
        XCAFDoc_ShapeTool,
    )

    from extract_parts import DOCUMENT_FORMAT, _label_entry, _label_name, _referred_label, \
        _sub_labels

    started_s = time.perf_counter()
    application = XCAFApp_Application.GetApplication()
    document = TDocStd_Document(TCollection_ExtendedString(DOCUMENT_FORMAT))
    application.NewDocument(TCollection_ExtendedString(DOCUMENT_FORMAT), document)
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.SetMatMode(True)
    reader.SetColorMode(True)
    reader.SetLayerMode(True)
    if reader.ReadFile(str(STEP_PATH)) != IFSelect_RetDone:
        raise RuntimeError("STEP read failed")
    log("XCAF: STEP parsed, transferring ...")
    if not reader.Transfer(document):
        raise RuntimeError("STEP transfer failed")
    read_s = time.perf_counter() - started_s
    log(f"XCAF: document ready in {read_s:.0f} s")
    shape_tool = XCAFDoc_DocumentTool.ShapeTool(document.Main())
    colour_tool = XCAFDoc_DocumentTool.ColorTool(document.Main())
    layer_tool = XCAFDoc_DocumentTool.LayerTool(document.Main())
    layers = TDF_LabelSequence()
    layer_tool.GetLayerLabels(layers)
    colours = TDF_LabelSequence()
    colour_tool.GetColors(colours)

    def label_colour(label) -> tuple[str, str] | None:
        colour = Quantity_Color()
        for kind in (XCAFDoc_ColorSurf, XCAFDoc_ColorGen):
            if XCAFDoc_ColorTool.GetColor(label, kind, colour):
                return _quantity_hex(colour)
        return None

    # all occurrences (assemblies and leaves): path -> (label, component chain, location)
    roots = TDF_LabelSequence()
    shape_tool.GetFreeShapes(roots)
    nodes: dict[str, tuple] = {}
    leaves = []
    pending = [(roots.Value(i), [_label_name(roots.Value(i))], [], TopLoc_Location())
               for i in range(1, roots.Length() + 1)]
    while pending:
        label, names, components, location = pending.pop()
        nodes[PATH_SEPARATOR.join(names)] = (label, components, location)
        if not XCAFDoc_ShapeTool.IsAssembly(label):
            leaves.append((label, names, components, location))
            continue
        for component in _sub_labels(label):
            pending.append((_referred_label(component), [*names, _label_name(component)],
                            [*components, component],
                            location.Multiplied(XCAFDoc_ShapeTool.GetLocation(component))))
    instance_rows = {row["instance_path"]: row for row in result["instance_rows"]}
    instance_check, overrides_check = _instance_colour_checks(
        document, roots.Value(1), nodes, leaves, instance_rows, result["overrides"],
        label_colour, log)

    # prototype face colours in TopExp order vs text face order
    entry_part: dict[str, PartStyle] = result["entry_part"]
    proto_labels = {}
    for label, _, _, _ in leaves:
        proto_labels.setdefault(_label_entry(label), label)
    face_checked = face_equal = kind_checked = kind_equal = 0
    face_mismatch_entries = []
    use_srgb = True  # solid / face colours matched in sRGB (2026-10-21 run)
    pick = 0
    face_errors: list[str] = []
    for entry, label in proto_labels.items():
        part = entry_part.get(entry)
        if part is None:
            continue
        try:
            xcaf_sequence, text_sequence = _face_sequences(label, part, label_colour, pick)
        except Exception as error:  # keep the long XCAF read useful even if one part fails
            face_errors.append(f"{entry}: {type(error).__name__}: {error}")
            continue
        face_checked += 1
        if xcaf_sequence == text_sequence:
            face_equal += 1
        elif len(face_mismatch_entries) < 20:
            same = sum(x == y for x, y in zip(xcaf_sequence, text_sequence))
            face_mismatch_entries.append({
                "prototype_entry": entry, "faces_xcaf": len(xcaf_sequence),
                "faces_text": len(text_sequence), "equal_positions": same})
    report_faces_errors = face_errors[:20]
    report = {
        "description": "Text-scan colours vs OCCT STEPCAFControl_Reader (colour and layer mode on)",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "occt_reader_s": round(read_s, 1),
        "total_s": round(time.perf_counter() - started_s, 1),
        "peak_memory_gb": round(
            getattr(psutil.Process().memory_info(), "peak_wset", 0) / 1e9, 2),
        "xcaf_layers": layers.Length(),
        "xcaf_colour_table_entries": colours.Length(),
        "leaf_instances": len(leaves),
        "instance_overrides": overrides_check,
        "instance_display_colour": instance_check,
        "face_sequence_check": {
            "colour_space_used": "sRGB" if use_srgb else "linear",
            "prototypes_checked": face_checked,
            "prototypes_equal": face_equal,
            "mismatch_examples": face_mismatch_entries,
            "errors": report_faces_errors,
            "meaning": "per prototype, effective face colour (face, else solid, else part) in "
                       "TopExp_Explorer(prototype, FACE) order (= face_index of 07_faces) equals "
                       "the text face order of face_styles.csv",
        },
    }
    XCAF_CHECK_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"XCAF check written: {XCAF_CHECK_JSON}")
    return report


def _instance_colour_checks(document, root, nodes: dict, leaves: list, instance_rows: dict,
                            overrides: list, label_colour, log=print) -> tuple[dict, dict]:
    """Instance-level colours as OCCT 8 holds them, compared with the text result.

    (a) SHUO inventory (``XCAFDoc_ShapeTool.GetAllComponentSHUO`` on every component label);
    (b) per CDORSI occurrence: colour on its component label, SHUO with the same path, and the
        style key of the located occurrence in ``XCAFPrs::CollectStyleSettings``;
    (c) per leaf instance: effective face colours the way ``XCAFPrs_AISObject`` dispatches the
        styles of ``CollectStyleSettings(root)`` (most specific key wins: face, solid, the
        instance shape, then its parent assemblies), dominant colour by face count.
    """
    from OCC.Core.Quantity import Quantity_ColorRGBA
    from OCC.Core.TDF import TDF_AttributeSequence
    from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_SOLID
    from OCC.Core.TopExp import TopExp_Explorer, topexp
    from OCC.Core.TopTools import TopTools_IndexedMapOfShape
    from OCC.Core.TopLoc import TopLoc_Location
    from OCC.Core.XCAFDoc import XCAFDoc_GraphNode, XCAFDoc_ShapeTool
    from OCC.Core.XCAFPrs import XCAFPrs_IndexedDataMapOfShapeStyle, xcafprs

    from extract_parts import _label_entry, _label_name

    # (a) SHUO inventory
    shuo_paths: dict[str, str | None] = {}
    seen = set()
    for path, (_, components, _) in nodes.items():
        if not components:
            continue
        component = components[-1]
        entry = _label_entry(component)
        if entry in seen:
            continue
        seen.add(entry)
        attributes = TDF_AttributeSequence()
        if not XCAFDoc_ShapeTool.GetAllComponentSHUO(component, attributes):
            continue
        parent = path.rpartition(PATH_SEPARATOR)[0]
        for k in range(1, attributes.Length() + 1):
            node = XCAFDoc_GraphNode.DownCast(attributes.Value(k))
            names = [_label_name(component)]
            current = node
            while current.NbChildren() > 0:
                current = current.GetChild(1)
                names.append(_label_name(current.Label().Father()))
            found = label_colour(node.Label())
            shuo_paths[PATH_SEPARATOR.join([parent, *names])] = found[0] if found else None
    log(f"XCAF: {len(shuo_paths)} SHUO")

    # (c) presentation styles of the whole document
    settings = XCAFPrs_IndexedDataMapOfShapeStyle()
    xcafprs.CollectStyleSettings(root, TopLoc_Location(), settings, Quantity_ColorRGBA())
    log(f"XCAF: CollectStyleSettings -> {settings.Size()} styled keys")

    def key_colour(shape) -> str | None:
        index = settings.FindIndex(shape)
        if index == 0:
            return None
        style = settings.FindFromIndex(index)
        if not style.IsSetColorSurf():
            return None
        return _quantity_hex(style.GetColorSurf())[0]

    def node_key(path: str) -> str | None:
        label, _, location = nodes[path]
        return key_colour(XCAFDoc_ShapeTool.GetShape(label).Moved(location))

    # (b) every CDORSI occurrence
    by_class: Counter = Counter()
    override_rows = []
    for path, hex_value, depth, entity_id in overrides:
        node = nodes.get(path)
        if node is None:
            by_class["occurrence not in XCAF tree"] += 1
            continue
        label, components, _ = node
        component_found = label_colour(components[-1])
        component_hex = component_found[0] if component_found else None
        shuo_hex = shuo_paths.get(path)
        key_hex = node_key(path)
        if key_hex == hex_value:
            cls = "read: style on the located occurrence"
        elif component_hex == hex_value:
            cls = "read: colour on the component label only"
        elif shuo_hex == hex_value:
            cls = "read: SHUO colour only"
        else:
            cls = "not read by OCCT"
        by_class[f"depth {depth}: {cls}"] += 1
        override_rows.append({"path": path, "depth": depth, "cdorsi": f"#{entity_id}",
                              "text": hex_value, "component_label": component_hex,
                              "shuo": shuo_hex, "presentation_key": key_hex, "class": cls})
    overrides_check = {
        "cdorsi": len(overrides),
        "shuo_in_document": len(shuo_paths),
        "classes": dict(sorted(by_class.items())),
        "examples": [row for row in override_rows if row["class"] == "not read by OCCT"][:10]
        + [row for row in override_rows if row["class"] != "not read by OCCT"][:5],
    }

    # (c) per leaf: effective colour
    classes: Counter = Counter()
    examples = []
    for label, names, _, location in leaves:
        path = PATH_SEPARATOR.join(names)
        row = instance_rows.get(path)
        if row is None:
            classes["not in text result"] += 1
            continue
        inherited = None
        for depth in range(len(names), 0, -1):
            inherited = node_key(PATH_SEPARATOR.join(names[:depth]))
            if inherited is not None:
                break
        shape = XCAFDoc_ShapeTool.GetShape(label)
        face_map = TopTools_IndexedMapOfShape()
        topexp.MapShapes(shape, TopAbs_FACE, face_map)
        solid_of_face: dict[int, str | None] = {}
        solids = TopExp_Explorer(shape, TopAbs_SOLID)
        while solids.More():
            solid = solids.Current()
            solid_hex = key_colour(solid.Moved(location))
            faces = TopExp_Explorer(solid, TopAbs_FACE)
            while faces.More():
                solid_of_face.setdefault(face_map.FindIndex(faces.Current()), solid_hex)
                faces.Next()
            solids.Next()
        counts: Counter = Counter()
        faces = TopExp_Explorer(shape, TopAbs_FACE)
        while faces.More():
            face = faces.Current()
            colour = (key_colour(face.Moved(location)) or solid_of_face.get(face_map.FindIndex(face))
                      or inherited or "")
            counts[colour] += 1
            faces.Next()
        occt_hex = counts.most_common(1)[0][0] if counts else (inherited or "")
        display, part = row["rgb_hex"], row["part_rgb_hex"]
        if occt_hex == display:
            cls = "OCCT = display (override rule)"
        elif occt_hex == part:
            cls = "OCCT = part colour (override not visible in OCCT)"
        elif not counts:
            cls = "no faces"
        else:
            cls = "other"
        source = row["colour_source"]
        classes[f"{source}: {cls}"] += 1
        if cls == "other" and len(examples) < 10:
            examples.append({"path": path, "display": display, "part": part, "occt": occt_hex,
                             "occt_face_colours": dict(counts.most_common(3))})
    instance_check = {
        "leaf_instances": len(leaves),
        "classes_by_text_source": dict(sorted(classes.items())),
        "other_examples": examples,
        "method": "XCAFPrs::CollectStyleSettings(root) keys looked up per located face, solid, "
                  "instance and parent occurrence (most specific wins, as XCAFPrs_AISObject "
                  "dispatches styles); dominant colour by face count vs instance_styles.csv",
    }
    return instance_check, overrides_check


def _face_sequences(label, part: "PartStyle", label_colour, pick: int) -> tuple[list[str], list[str]]:
    """Effective face colours: XCAF in TopExp order, text in STEP order."""
    from OCC.Core.TDF import TDF_LabelSequence
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.TopExp import TopExp_Explorer, topexp
    from OCC.Core.TopTools import TopTools_IndexedMapOfShape
    from OCC.Core.XCAFDoc import XCAFDoc_ShapeTool

    shape = XCAFDoc_ShapeTool.GetShape(label)
    face_map = TopTools_IndexedMapOfShape()
    topexp.MapShapes(shape, TopAbs_FACE, face_map)
    order = []
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        order.append(face_map.FindIndex(explorer.Current()))
        explorer.Next()
    face_colour: dict[int, str] = {}
    solid_colour_faces: dict[int, str] = {}
    sub_labels = TDF_LabelSequence()
    XCAFDoc_ShapeTool.GetSubShapes(label, sub_labels)
    for i in range(1, sub_labels.Length() + 1):
        sub = sub_labels.Value(i)
        found = label_colour(sub)
        if found is None:
            continue
        sub_shape = XCAFDoc_ShapeTool.GetShape(sub)
        if sub_shape.ShapeType() == TopAbs_FACE:
            face_colour[face_map.FindIndex(sub_shape)] = found[pick]
        else:
            inner = TopExp_Explorer(sub_shape, TopAbs_FACE)
            while inner.More():
                solid_colour_faces.setdefault(face_map.FindIndex(inner.Current()), found[pick])
                inner.Next()
    own = label_colour(label)
    xcaf_sequence = [face_colour.get(i) or solid_colour_faces.get(i) or (own[pick] if own else "")
                     for i in order]
    text_sequence = [(part.effective(i).hex if part.effective(i) else "")
                     for i in range(len(part.face_ids))]
    return xcaf_sequence, text_sequence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--xcaf-check", action="store_true",
                        help="cross-check with the OCCT XCAF reader (~2-3 min, ~4 GB)")
    parser.add_argument("--no-pin", action="store_true", help="do not pin to one P-core")
    arguments = parser.parse_args()
    if not arguments.no_pin:
        print(place_one_pcore(), flush=True)
    result = build()
    if arguments.xcaf_check:
        report = xcaf_check(result)
        print(json.dumps({k: v for k, v in report.items() if k != "instance_mismatch_examples"},
                         ensure_ascii=False, indent=1))
    from check_cache import write_manifest

    write_manifest(["08_style"])
    print("manifest entry 08_style refreshed")


if __name__ == "__main__":
    main()
