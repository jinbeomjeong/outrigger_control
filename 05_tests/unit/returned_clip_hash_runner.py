"""One stored harness row with the returned-command clip on or off; writes its command hash.

Helper of ``test_c2_returned_clip.py``: the harness needs dynamics-dev (numba), the tests run in
Chrono-dev. The row runs through ``verdict_runs`` with the flow limit off, the path whose hash
equals the stored harness hash.

Usage:
  python -I -B returned_clip_hash_runner.py <case id> <on|off> <out.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "03_src"
COUPLED_DIR = PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled"
MAIN_TREE_ROOT = Path(r"C:\workspace\outrigger_control")
"""``r8d1_td.py`` inserts a folder of this tree whichever checkout it runs in."""
FLOW_LIMIT_OFF_ETA_V = 0.95
HOLD_EVENT_TEXT = "DIFF_SINK_HOLD"


class _ThisCheckoutSysPath(list):
    """``sys.path`` whose ``insert`` maps a main-tree folder onto this checkout (git worktree)."""

    def insert(self, index, folder) -> None:
        path = Path(folder)
        if path.is_relative_to(MAIN_TREE_ROOT) and not path.is_relative_to(PROJECT_ROOT):
            folder = str(PROJECT_ROOT / path.relative_to(MAIN_TREE_ROOT))
        super().insert(index, folder)


sys.path = _ThisCheckoutSysPath(sys.path)
for _path in (COUPLED_DIR, SOURCE_DIR):
    sys.path.insert(0, str(_path))


def _preset_without_clip() -> None:
    from outrigger_sim.control import c2

    switched_preset = c2.C2Config.with_10hz_d1

    def preset(self, **keywords):
        keywords.setdefault("clip_returned_command", False)
        return switched_preset(self, **keywords)

    c2.C2Config.with_10hz_d1 = preset


def _modules_outside_project() -> list[str]:
    """Project modules imported from the main tree in a worktree run (empty in the main tree)."""
    foreign = []
    for module in list(sys.modules.values()):
        file_name = getattr(module, "__file__", None)
        if file_name is None:
            continue
        path = Path(file_name).resolve()
        if path.is_relative_to(MAIN_TREE_ROOT) and not path.is_relative_to(PROJECT_ROOT):
            foreign.append(str(path))
    return foreign


def main() -> None:
    case_id, clip_switch, out_path = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    if clip_switch == "off":
        _preset_without_clip()

    import numpy as np
    import verdict_runs
    from harness_flow import FlowSetting
    from verdict_cases import CASES

    setting = FlowSetting(is_enabled=False, eta_v=FLOW_LIMIT_OFF_ETA_V)
    result, series = verdict_runs.execute(CASES[case_id], setting, None)
    if "error" in result:
        raise RuntimeError(f"{case_id}: {result['error']}\n{result.get('tb')}")
    report = {
        "case": case_id,
        "clip": clip_switch,
        "hash": result["commands_sha256"],
        "peak_command_m_s": float(np.abs(series["command"]).max()),
        "hold_events": sum(HOLD_EVENT_TEXT in name for _, name in result["events"]),
        "foreign_modules": _modules_outside_project(),
    }
    out_path.write_text(json.dumps(report), encoding="utf-8")


if __name__ == "__main__":
    main()
