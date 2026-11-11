"""E5a: the B-6 G8 jobs through ``g8trace`` with the LOC anchor shadow (record only).

Each output row is the ``g8trace`` row plus ``loc_shadow`` (the shadow record of the run's
controller with a LOC, ``loc_anchor_shadow.record_of``) and ``loc_shadow_controllers`` (how
many controllers the run created). The commands must equal the stored B-6 rows (``sha``);
``g8_shadow_check.py`` compares them.

Usage (dynamics-dev python.exe, cwd = the checkout, PowerShell; env as B-6 ``g8_b6.launch.json``
plus ``OUTRIGGER_LOC_SHADOW=1``)::

    python -I -B 04_scripts/03_control/k2/loc_shadow/g8_shadow.py <checkout> <jobs.json> <out.jsonl>
        [--workers N]

Identity sidecar ``<out>.identity.json`` (start and end). Exit: ``g8trace.main``'s (0 done).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
G8TRACE_DIR = ROOT / "06_analysis" / "02_control" / "touch_phase" / "acceptance" / "g8_safe_stop"
for _folder in (HERE, G8TRACE_DIR):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

import g8trace  # noqa: E402  (installs acc_common and its own c2 wrappers)
import loc_anchor_shadow as shadow  # noqa: E402
import shadow_identity  # noqa: E402

shadow.install()
_ORIGINAL_RUN = g8trace.run
TOOL_FILES = {"g8_shadow.py": HERE / "g8_shadow.py",
              "loc_anchor_shadow.py": HERE / "loc_anchor_shadow.py",
              "g8trace.py": G8TRACE_DIR / "g8trace.py"}


def _loc_record(controllers: list) -> dict | None:
    """The record of the last controller with a confirmed LOC (else the last one's)."""
    records = [shadow.record_of(controller) for controller in controllers]
    records = [record for record in records if record is not None]
    with_loc = [record for record in records if record["n_loc"]]
    if with_loc:
        return with_loc[-1]
    return records[-1] if records else None


def run_with_shadow(job: dict) -> dict:
    """``g8trace.run`` of one job, plus the shadow record (worker)."""
    shadow.clear_registry()
    row = _ORIGINAL_RUN(job)
    controllers = shadow.registered_controllers()
    row["loc_shadow_controllers"] = len(controllers)
    row["loc_shadow"] = _loc_record(controllers)
    shadow.clear_registry()
    return row


def main() -> None:
    out_path = Path(sys.argv[3])
    sidecar = out_path.with_suffix(out_path.suffix + ".identity.json")
    start = shadow_identity.identity(ROOT, TOOL_FILES)
    shadow_identity.write_sidecar(sidecar, {"start": start, "end": None})
    g8trace.run = run_with_shadow
    g8trace.main()
    end = shadow_identity.identity(ROOT, TOOL_FILES)
    shadow_identity.write_sidecar(sidecar, {"start": start, "end": end})
    print(f"identity {sidecar}", flush=True)


if __name__ == "__main__":
    if not shadow.is_enabled(os.environ):
        raise SystemExit(f"set {shadow.ENV_SWITCH}={shadow.ENV_ON}")
    main()
