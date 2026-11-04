"""Run an existing harness script of the pinned checkout with the candidate combination on the preset.

Usage: python -I -B acc_launch.py <script.py in the checkout> [script arguments ...]
Env: acc_common (ACC_WT, ACC_COMBO); ACC_PROVENANCE: file for the code and preset record;
ACC_R79_INCLUDE_PAD_A=1: r79_L3L4_final keeps the pad A reference rows (the Q-E denominator 855 holds them).
The patch runs at import, so spawned pool workers (which re-import this file as ``__mp_main__``) get it too.
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import acc_common  # noqa: E402

acc_common.install()


def main() -> None:
    script = Path(sys.argv[1]).resolve()
    if acc_common.wt_root() not in script.parents:
        raise SystemExit(f"{script} is not in the pinned checkout")
    sys.argv = [str(script), *sys.argv[2:]]
    sys.path.insert(0, str(script.parent))
    if os.environ.get("ACC_PROVENANCE"):
        acc_common.write_provenance(Path(os.environ["ACC_PROVENANCE"]), {"script": str(script), "argv": sys.argv[1:]})
    spec = importlib.util.spec_from_file_location(script.stem, script)
    module = importlib.util.module_from_spec(spec)
    sys.modules[script.stem] = module
    spec.loader.exec_module(module)
    if os.environ.get("ACC_R79_INCLUDE_PAD_A") == "1":
        module.PAD_A_INNER = re.compile(r"$^")
    module.main()
    bad = acc_common.main_tree_modules()
    if bad:
        raise SystemExit(f"main-tree modules imported: {bad[:5]}")


if __name__ == "__main__":
    main()
