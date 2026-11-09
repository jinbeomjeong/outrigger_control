"""D-1 controller verification matrix: the reduced-harness rows H-R and H-S (definitions only).

Source: ``d1_rows_final.md`` 0 .. 3 (dynamics-expert 2026-11-08, user decisions U1 .. U8 in
``00_docs/decision_log.md`` 4) and ``d1_dynamics_check.md`` 5 (P-1 .. P-6). The rows run through
``run_v5.py d1`` (VB / V0 pair x phase eps {0, 2e-3}, output ``d1.jsonl``); ``d1_runs.py``
executes one row. Nothing here runs the harness.

Row groups (``d1_rows_final.md`` 2 and 3):
  H-R-0     rigid, auger T / M / B x flat + 5 operating + 5 validation slopes x crawler x1 / x3  66
  H-R-A     ``rigid+J1@<leg>`` x T / M / B x 6 slope@leg x crawler x1 / x3                      36
  H-R-A-stop  T, fup-op, ``rigid+J1@RL``, x1, record "stroke stop expected"                       1
  H-R-A-J2 / H-R-A-S1  T, flat, ``rigid+J2@FL`` / ``rigid+S1@FL``, x1, record                    2
  H-S-0     G1 / J1 / J2 x T / M / B x flat + 5 recommended slopes                               54
  H-S-1     S1 flat x T / M / B                                                                   3
  H-S-A     ``G1+J1@<leg>`` x T / M / B x 6 slope@leg                                            18
  H-S-A-J2  T, flat, ``G1+J2@FL``, record                                                         1
  H-S-C     PS-c, J1 / J2 x T / M / B, flat: c-slow / c-mid / c-edge / c-fast @FL, c-mid @RL      30
  H-S-C-g   PS-c c-mid, J1 x T / M / B x fdown-rec@FL / diag-rec@FR, record ``dsb_gated_off``     6
            (user decision 2026-11-08: the six sloped PS-c rows are in)
  = H-R 105 + H-S 112 = 217 rows x 2 settings x 2 phases = 868 runs.

Slopes: ``s9_soil_slope._scaled_slope(direction, k)`` (rounded to 1e-4 deg); the settle-table key
of a soil row is built from these floats (``settle_table_key``, ``{:g}``).

D8x group ``H-R-X`` (``06_analysis/02_control/d8x/d8x_rules.md`` 3 R-c, 9.2 item 2), not part of
:func:`all_rows` / the ``d1`` batch: rigid, pad B, F_s 4 kN, the eight R-c floors of the D8x point
file (explicit angles, not ``_scaled_slope``) x T / M / B x crawler x1 / x3 = 48 rows.
:func:`d8x_jobs` gives VB / V0 x eps {0, 2e-3} with K1 off (192) or VB / V0 x eps 0 with K1 on
(96); every job carries ``k1``. Run by ``run_v5.py d1 --group H-R-X --k1 off|on``.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
S9_DIR = ROOT / "04_scripts" / "03_control" / "s9"
D8X_DIR = ROOT / "04_scripts" / "03_control" / "d8x"

D1_BATCH = "d1"
D1_SOURCE = "dyn_d1/d1_rows_final.md 2-3 (2026-11-08, U1-U8) + H-S-C-g (user decision 2026-11-08)"
D1_SETTINGS = ("VB", "V0")
D1_EPS = (0.0, 2e-3)
LEVELS = ("top", "middle", "bottom")
LEVEL_LETTER = {"top": "T", "middle": "M", "bottom": "B"}
RIGID = "rigid"
PAD = "B"
FS_KN = 4.0
CRAWLER_SCALES = (1.0, 3.0)
DIAG_OP_K = 1.0 / 1.1714545
"""rpB x 1 / 1.1714545 = (2.3351, 1.5017) deg, R_c = 1 (U2: rigid diagonal along rpB)."""

SLOPES: dict[str, tuple[str, float]] = {
    "flat": ("flat", 1.0),
    "fdown-op": ("nose_down", 1.0),
    "fup-op": ("nose_up", 1.0),
    "roll+op": ("roll_pos", 1.0),
    "roll-op": ("roll_neg", 1.0),
    "diag-op": ("rpB", DIAG_OP_K),
    "fdown-val": ("nose_down", 3.5 / 3.2),
    "fup-val": ("nose_up", 3.5 / 3.2),
    "roll+val": ("roll_pos", 1.25),
    "roll-val": ("roll_neg", 1.25),
    "diag-val": ("rpB", 1.0),
    "fdown-rec": ("nose_down", 0.875),
    "fup-rec": ("nose_up", 0.875),
    "roll-rec": ("roll_neg", 0.6),
    "roll+rec": ("roll_pos", 0.5),
    "diag-rec": ("edge_nd", 0.875),
    "fdown-psa": ("nose_down", 0.75),
    "fup-psa": ("nose_up", 0.75),
    "diag-psa-soil": ("edge_nd", 1.0),
}
"""``d1_rows_final.md`` 1: slope name -> (``s9_soil_slope.SLOPES_DEG`` direction, ratio k)."""
RIGID_SLOPES = ("flat", "fdown-op", "fup-op", "roll+op", "roll-op", "diag-op",
                "fdown-val", "fup-val", "roll+val", "roll-val", "diag-val")
SOIL_SLOPES = ("flat", "fdown-rec", "fup-rec", "roll-rec", "roll+rec", "diag-rec")
RIGID_PATCH_POINTS = (("flat", "FL"), ("flat", "RL"), ("fdown-psa", "FL"), ("fup-psa", "RL"),
                      ("roll-op", "RL"), ("diag-op", "FR"))
SOIL_PATCH_POINTS = (("flat", "FL"), ("flat", "RL"), ("fdown-psa", "FL"), ("fup-psa", "RL"),
                     ("roll-op", "RL"), ("diag-psa-soil", "FR"))
SOIL_BASES = ("G1", "J1", "J2")
PSC_SOILS = ("J1", "J2")

READY_LIMITS_S = {"H-R": (90.0, 120.0)}
"""(flat, slope) READY limit of the rigid rows (``d1_rows_final.md`` 2, unchanged). The soil rows
take the spec 421.1 limit per soil and patch (:func:`soil_ready_limit_s`)."""
READY_RULES = ("d1_selection_rules_rev1.md 1 (sealed 2026-11-08): H-S READY = spec 421.1 "
               "(s9_soil_slope.ready_limit_s)")
RULES_REV1_PATH = (ROOT / "06_analysis" / "02_control" / "verif_matrix"
                   / "d1_selection_rules_rev1.md")

TAG_STROKE_STOP_ALLOWED = "stroke_limited_stop_allowed"
TAG_STROKE_STOP_EXPECTED = "stroke_stop_expected"
TAG_ASSUMED_BOUNDARY = "ASSUMED_BOUNDARY"
TAG_J2_ROLL_BOUNDARY = "J2_roll_harness_boundary_non_monotonic"
TAG_J2_PATCH = "J2_patch_boundary"
TAG_S1_LIMIT = "S1_MODEL_LIMIT_NOTE"
TAG_DSB_GATED_OFF = "dsb_gated_off"
TAG_DSB_TARGET = "dsb75_target"
ROLE_JUDGE = "judge"
ROLE_RECORD = "record"


@dataclass(frozen=True)
class SinkEvent:
    """PS-c progressive sink (``d1_rows_final.md`` 3): Poly345 ``depth_mm`` over ``ramp_s`` under
    ``leg``, at ``timing`` "ready" (READY + 5 s) or "level" (mid of LOC and the first DONE)."""

    name: str
    leg: str
    depth_mm: float
    ramp_s: float
    timing: str


PSC_PROFILES = {
    "c-slow": (11.5, 20.0, "ready"),
    "c-mid": (20.0, 6.0, "level"),
    "c-edge": (15.0, 8.0, "level"),
    "c-fast": (30.0, 4.0, "level"),
}
"""Name -> (d [mm], T [s], timing)."""
PSC_POINTS = (("c-slow", "FL"), ("c-mid", "FL"), ("c-edge", "FL"), ("c-fast", "FL"),
              ("c-mid", "RL"))
PSC_SLOPED_POINTS = (("fdown-rec", "FL"), ("diag-rec", "FR"))


def sink_event(name: str, leg: str) -> SinkEvent:
    depth_mm, ramp_s, timing = PSC_PROFILES[name]
    return SinkEvent(name, leg, depth_mm, ramp_s, timing)


@dataclass(frozen=True)
class D1Row:
    """One harness row (a combination; run with VB and V0 and both phases)."""

    group: str
    base: str
    level: str
    slope_name: str
    roll_deg: float
    pitch_deg: float
    ready_limit_s: float
    crawler_k_scale: float = 1.0
    patch_soil: str | None = None
    patch_leg: str | None = None
    sink: SinkEvent | None = None
    role: str = ROLE_JUDGE
    tags: tuple[str, ...] = field(default=())

    @property
    def soil(self) -> str:
        """``<base>`` or the r72 string ``<base>+<patch>@<leg>``."""
        if self.patch_soil is None:
            return self.base
        return f"{self.base}+{self.patch_soil}@{self.patch_leg}"

    @property
    def path(self) -> str:
        """Harness path: ``event`` (426.3 PS-c), ``g6`` (r72 PS-a) or ``steady`` (s9 slope)."""
        if self.sink is not None:
            return "event"
        if self.patch_soil is not None:
            return "g6"
        return "steady"

    @property
    def key(self) -> str:
        key = (f"D1|{self.group}|{self.soil}|{LEVEL_LETTER[self.level]}|{self.slope_name}"
               f"|K{self.crawler_k_scale:g}")
        if self.sink is not None:
            key += f"|{self.sink.name}@{self.sink.leg}"
        if TAG_DSB_GATED_OFF in self.tags:
            key += f"|{TAG_DSB_GATED_OFF}"
        return key

    @property
    def is_flat(self) -> bool:
        return self.roll_deg == 0.0 and self.pitch_deg == 0.0

    def to_job(self) -> dict:
        """JSON form (the ``d1`` entry of a ``run_v5`` job; also the job identity)."""
        out = asdict(self)
        out["tags"] = list(self.tags)
        out["key"] = self.key
        return out

    @classmethod
    def from_job(cls, entry: dict) -> D1Row:
        values = {k: v for k, v in entry.items() if k != "key"}
        values["tags"] = tuple(values.get("tags") or ())
        if values.get("sink") is not None:
            values["sink"] = SinkEvent(**values["sink"])
        row = cls(**values)
        if entry.get("key") not in (None, row.key):
            raise ValueError(f"D-1 row key {entry['key']!r} does not match its fields ({row.key})")
        return row


# ------------------------------------------------------------------------------------- slopes
def _slope_module():
    if str(S9_DIR) not in sys.path:
        sys.path.insert(0, str(S9_DIR))
    import s9_soil_slope

    return s9_soil_slope


def slope_deg(name: str) -> tuple[float, float]:
    """(roll, pitch) [deg] of a D-1 slope name (``_scaled_slope`` floats)."""
    direction, k = SLOPES[name]
    if direction == "flat":
        return 0.0, 0.0
    return _slope_module()._scaled_slope(direction, k)


def text_sha256(path: Path) -> str | None:
    """SHA-256 of a text file with LF line ends (None without the file)."""
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def ready_rule_record(path: Path = RULES_REV1_PATH) -> dict:
    """The READY rule of the rows: text, the rev1 file name and its SHA-256 (read from the file;
    None when the file is absent, e.g. in a worktree without the sealed text)."""
    return {"text": READY_RULES, "rules": path.name, "sha256": text_sha256(path)}


def soil_ready_limit_s(soil: str, roll_deg: float, pitch_deg: float) -> float:
    """Spec 421.1 READY limit of a pad B soil row (``d1_selection_rules_rev1.md`` 1): slope
    120 s, flat on a uniform J1 / J2 / S1 100 s, any other flat (G1, ``G1+<w>@<leg>``) 90 s."""
    case = {"soil": soil, "pad": PAD, "roll_deg": roll_deg, "pitch_deg": pitch_deg}
    return float(_slope_module().ready_limit_s(case))


def _ready_limit(group: str, soil: str, slope_name: str, roll_deg: float,
                 pitch_deg: float) -> float:
    if group.startswith("H-R"):
        flat_s, slope_s = READY_LIMITS_S["H-R"]
        return flat_s if slope_name == "flat" else slope_s
    return soil_ready_limit_s(soil, roll_deg, pitch_deg)


def _row(group: str, base: str, level: str, slope_name: str, **kwargs) -> D1Row:
    roll, pitch = slope_deg(slope_name)
    patch_soil, patch_leg = kwargs.get("patch_soil"), kwargs.get("patch_leg")
    soil = base if patch_soil is None else f"{base}+{patch_soil}@{patch_leg}"
    return D1Row(group, base, level, slope_name, roll, pitch,
                 ready_limit_s=_ready_limit(group, soil, slope_name, roll, pitch), **kwargs)


# --------------------------------------------------------------------------------------- rows
def rigid_rows() -> list[D1Row]:
    """H-R (105): uniform rigid, PS-a on a rigid base and the three record rows."""
    rows = [_row("H-R-0", RIGID, level, name, crawler_k_scale=scale)
            for level in LEVELS for name in RIGID_SLOPES for scale in CRAWLER_SCALES]
    rows += [_row("H-R-A", RIGID, level, name, crawler_k_scale=scale, patch_soil="J1",
                  patch_leg=leg, tags=(TAG_STROKE_STOP_ALLOWED,))
             for level in LEVELS for name, leg in RIGID_PATCH_POINTS for scale in CRAWLER_SCALES]
    rows.append(_row("H-R-A-stop", RIGID, "top", "fup-op", patch_soil="J1", patch_leg="RL",
                     role=ROLE_RECORD, tags=(TAG_STROKE_STOP_EXPECTED,)))
    rows.append(_row("H-R-A-J2", RIGID, "top", "flat", patch_soil="J2", patch_leg="FL",
                     role=ROLE_RECORD, tags=(TAG_J2_PATCH,)))
    rows.append(_row("H-R-A-S1", RIGID, "top", "flat", patch_soil="S1", patch_leg="FL",
                     role=ROLE_RECORD, tags=(TAG_S1_LIMIT,)))
    return rows


def _soil_tags(base: str, slope_name: str) -> tuple[str, ...]:
    tags = [TAG_STROKE_STOP_ALLOWED]
    if slope_name == "fup-rec":
        tags.append(TAG_ASSUMED_BOUNDARY)
    if base == "J2" and slope_name in ("roll-rec", "roll+rec"):
        tags.append(TAG_J2_ROLL_BOUNDARY)
    return tuple(tags)


def soil_rows() -> list[D1Row]:
    """H-S (112): uniform soil, S1 flat, PS-a on G1, PS-c flat and the six sloped PS-c rows."""
    rows = [_row("H-S-0", base, level, name, tags=_soil_tags(base, name))
            for level in LEVELS for base in SOIL_BASES for name in SOIL_SLOPES]
    rows += [_row("H-S-1", "S1", level, "flat") for level in LEVELS]
    rows += [_row("H-S-A", "G1", level, name, patch_soil="J1", patch_leg=leg,
                  tags=(TAG_STROKE_STOP_ALLOWED,))
             for level in LEVELS for name, leg in SOIL_PATCH_POINTS]
    rows.append(_row("H-S-A-J2", "G1", "top", "flat", patch_soil="J2", patch_leg="FL",
                     role=ROLE_RECORD, tags=(TAG_J2_PATCH,)))
    rows += [_row("H-S-C", base, level, "flat", sink=sink_event(name, leg),
                  tags=(TAG_DSB_TARGET,))
             for level in LEVELS for base in PSC_SOILS for name, leg in PSC_POINTS]
    rows += [_row("H-S-C-g", "J1", level, name, sink=sink_event("c-mid", leg), role=ROLE_RECORD,
                  tags=(TAG_DSB_GATED_OFF,))
             for level in LEVELS for name, leg in PSC_SLOPED_POINTS]
    return rows


def all_rows() -> list[D1Row]:
    """H-R then H-S (217 rows).

    Raises:
        RuntimeError: Two rows with one key.
    """
    rows = rigid_rows() + soil_rows()
    keys = [row.key for row in rows]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise RuntimeError(f"duplicate D-1 row keys {duplicates[:5]}")
    return rows


def jobs() -> list[dict]:
    """``run_v5`` jobs: every row x VB / V0 x eps {0, 2e-3} (setting outermost)."""
    return [{"d1": row.to_job(), "eps": eps, "setting": setting}
            for setting in D1_SETTINGS for row in all_rows() for eps in D1_EPS]


# ------------------------------------------------------------------------------- D8x H-R-X
D8X_GROUP = "H-R-X"
D8X_EPS = {"off": D1_EPS, "on": (0.0,)}
"""Rules 3 R-c: K1 off runs eps {0, 2e-3}, the K1-on pair runs eps 0 only."""


def _d8x_record_module():
    if str(D8X_DIR) not in sys.path:
        sys.path.insert(0, str(D8X_DIR))
    import d8x_record

    return d8x_record


def d8x_rows(points_path: Path | None = None) -> list[D1Row]:
    """H-R-X (48): the R-c floors of the point file x T / M / B x crawler x1 / x3."""
    record = _d8x_record_module()
    floors = record.rc_floor_angles(record.load_points(points_path))
    flat_s, slope_s = READY_LIMITS_S["H-R"]
    return [D1Row(D8X_GROUP, RIGID, level, name, roll, pitch,
                  ready_limit_s=flat_s if roll == 0.0 and pitch == 0.0 else slope_s,
                  crawler_k_scale=scale)
            for level in LEVELS for name, (roll, pitch) in floors.items()
            for scale in CRAWLER_SCALES]


def d8x_jobs(k1: str, points_path: Path | None = None) -> list[dict]:
    """``run_v5`` jobs of H-R-X with K1 ``off`` (192) or ``on`` (96), setting outermost.

    Raises:
        ValueError: ``k1`` is not ``off`` / ``on``.
    """
    if k1 not in D8X_EPS:
        raise ValueError(f"k1 must be one of {sorted(D8X_EPS)}, got {k1!r}")
    rows = d8x_rows(points_path)
    return [{"d1": row.to_job(), "eps": eps, "setting": setting, "k1": k1}
            for setting in D1_SETTINGS for row in rows for eps in D8X_EPS[k1]]


# ------------------------------------------------------------------------------------ listing
def settle_keys_needed(rows: list[D1Row]) -> list[str]:
    """Settle-table keys of the soil-based rows (base soil, auger level, slope)."""
    _slope_module()
    import s9_soil_closed_loop as sl

    keys = {sl.settle_table_key(row.base, row.level, (row.roll_deg, row.pitch_deg))
            for row in rows if row.base != RIGID}
    return sorted(keys)


def missing_settle_keys(rows: list[D1Row], table_path: Path | None = None) -> list[str]:
    """Needed keys absent from the settle table (``$S9_SETTLE_TABLE`` or the default table)."""
    _slope_module()
    import s9_soil_closed_loop as sl

    path = Path(table_path or os.environ.get(sl.SETTLE_TABLE_ENV) or sl.DEFAULT_SETTLE_TABLE)
    table = json.loads(path.read_text(encoding="utf-8"))[sl.SETTLE_TABLE_BLOCK]
    return [key for key in settle_keys_needed(rows) if key not in table]


RUN_COST_CORE_S = {"steady": 75.0, "g6": 85.0, "event": 150.0}
"""Wall per run [core s] by harness path (ASSUMPTION: the v5 r5 rerun mean 73 core s for the
steady / event rows; G6 a little above (per-pad soil kernel); a PS-c row runs the base to its
event time twice plus the branch). Refine with ``runner_summary`` after the run."""


def cost_estimate(job_list: list[dict]) -> dict:
    """Core seconds by path and in total (:data:`RUN_COST_CORE_S`)."""
    by_path: dict[str, int] = {}
    for job in job_list:
        path = D1Row.from_job(job["d1"]).path
        by_path[path] = by_path.get(path, 0) + 1
    core_s = sum(RUN_COST_CORE_S[path] * count for path, count in by_path.items())
    return {"runs_by_path": by_path, "core_s": core_s}


def list_report(job_list: list[dict], table_path: Path | None = None) -> str:
    """Text of ``run_v5.py d1 --list``: rows per group, runs, missing settle rows, cost."""
    rows = [D1Row.from_job(job["d1"]) for job in job_list]
    unique = {row.key: row for row in rows}
    per_group: dict[str, int] = {}
    for row in unique.values():
        per_group[row.group] = per_group.get(row.group, 0) + 1
    missing = missing_settle_keys(list(unique.values()), table_path)
    cost = cost_estimate(job_list)
    rigid = sum(count for group, count in per_group.items() if group.startswith("H-R"))
    soil = sum(count for group, count in per_group.items() if group.startswith("H-S"))
    lines = [f"D-1 harness rows: {len(unique)} (H-R {rigid}, H-S {soil}), runs {len(job_list)}",
             "rows per group: " + ", ".join(f"{k} {v}" for k, v in per_group.items()),
             f"settle-table keys needed {len(settle_keys_needed(list(unique.values())))}, "
             f"missing {len(missing)}" + (f": {missing}" if missing else ""),
             f"cost (ASSUMPTION): {cost['runs_by_path']} -> {cost['core_s'] / 3600:.1f} core h"]
    lines += ready_limit_lines(list(unique.values()))
    return "\n".join(lines)


def ready_limit_lines(rows: list[D1Row]) -> list[str]:
    """Rows per READY limit, then one ``<key>  READY <limit> s`` line per row."""
    per_limit: dict[float, int] = {}
    for row in rows:
        per_limit[row.ready_limit_s] = per_limit.get(row.ready_limit_s, 0) + 1
    counts = ", ".join(f"{limit:g} s {count}" for limit, count in sorted(per_limit.items()))
    rule = ready_rule_record()
    lines = [f"READY limit ({READY_RULES}, sha256 {rule['sha256']}): {counts}"]
    width = max((len(row.key) for row in rows), default=0)
    lines += [f"  {row.key:<{width}}  READY {row.ready_limit_s:g} s" for row in rows]
    return lines
