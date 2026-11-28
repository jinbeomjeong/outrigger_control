"""Edition 9 R3 pre-check (control-expert, 2026-11-28; tool behaviour only, no result file).

Feeds the J4 texts of the pair judge to the T9 ``jp3_ed8_judge._group_of_item``. The pair J4 text
comes from ``judge_stage1_r5.J_fails`` (``J4 fail: final <V0 phase> -> <candidate phase>``,
wrapped by ``jp3_ed7_judge._item_text``); the source lines are printed from the file itself.

Usage (dynamics-dev ``python -I -B``)::

    python t9_item_group_check.py <T9 worktree> <out json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

COUPLED = Path("04_scripts") / "04_hydraulic" / "coupled"
R5 = Path("06_analysis") / "03_hydraulic" / "coupled" / "v5" / "paper_runs" / "scripts" / \
    "judge_stage1_r5.py"


def main() -> int:
    worktree, out = Path(sys.argv[1]), Path(sys.argv[2])
    if out.exists():
        print(json.dumps({"status": "input_error", "reason": f"{out} exists"}))
        return 2
    for path in (worktree / COUPLED, worktree / "03_src"):
        sys.path.insert(0, str(path))
    import jp3_ed7_judge as ed7
    import jp3_ed8_judge as judge

    source = (worktree / R5).read_text(encoding="utf-8").splitlines()
    j4_lines = {n: source[n - 1] for n in range(124, 132)}
    phases = ("fault", "fault_reground", "done", "level", "probe", "idle")
    texts = [ed7._item_text({"item": "J4", "kind": "fail", "detail": f"final ready -> {p}"})
             for p in phases]
    texts.append(ed7._item_text({"item": "J4", "kind": "fail",
                                 "detail": "first READY reached by V0, not by the setting"}))
    texts.append(ed7._item_text({"item": "J4", "kind": "fail", "detail": "final fault"}))
    groups = {text: sorted(judge._group_of_item(text)) for text in texts}
    report = {"judge_file": judge.__file__, "r5_file": str(worktree / R5),
              "r5_J4_source_lines": j4_lines, "FAULT_PHASE_PREFIX": judge.FAULT_PHASE_PREFIX,
              "groups": groups}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": "ok", "groups": groups}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
