"""Q8-5: how the worktree tag functions read the proposed edition 8 tags (read only).

Usage: python -I -B tag_check.py <worktree root> <out json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CANDIDATE_TAGS = (
    "final_C4G2_P3X_LAS_K1_LSB",        # edition 7 VBM (reference)
    "final_C4G2_LAS_K1_LSB",            # edition 7 VBM0 (reference)
    "final_C4G2_P3X_LAS_K1_LSB_E8",     # proposed VBN
    "final_C4G2_LAS_K1_LSB_E8",         # proposed VBN0
    "final_C4G2_P3X_LAS_K1_E8_LSB",     # alternative order (E8 before LSB)
    "final_C4G2_P3X_E8_LAS_K1_LSB",     # alternative: E8 on the base tag
)
FUNCTIONS = ("switch_base_tag", "extend_start_revision_of_tag", "is_extend_start_tag",
             "is_liftoff_slow_tag", "is_order_gate_tag", "is_lock_start_b_tag",
             "is_touch_creep_tag")


def main() -> int:
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    sys.path.insert(0, str(root / "03_src"))
    from outrigger_sim.hydraulics import v5_options

    module_file = Path(v5_options.__file__).resolve()
    if root.resolve() not in module_file.parents:
        raise SystemExit(f"v5_options imported from {module_file}, not the worktree")
    table = {}
    for tag in CANDIDATE_TAGS:
        table[tag] = {name: getattr(v5_options, name)(tag) for name in FUNCTIONS}
        table[tag]["with_lock_start_b_tag"] = v5_options.with_lock_start_b_tag(tag)
    result = {"module_file": str(module_file),
              "extend_start_revision_of_base_tag": v5_options.EXTEND_START_REVISION_OF_BASE_TAG,
              "table": table}
    out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({tag: row["extend_start_revision_of_tag"] for tag, row in table.items()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
