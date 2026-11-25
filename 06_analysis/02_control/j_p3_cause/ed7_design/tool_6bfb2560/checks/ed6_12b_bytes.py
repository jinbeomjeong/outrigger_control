"""Edition 5 / 6 bytes of jp3_12b_plan unchanged: run the a6fc3dd5 module and the working tree
module on one synthetic tree (with blind-named folders) and compare every output byte.

Usage: python -I -B ed6_12b_bytes.py <scratch> <old tree> <new tree>
"""

from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path


def load(tree: Path):
    for name in ("jp3_12b_plan", "jp3_fixed_inputs", "test_jp3_12b_tools"):
        sys.modules.pop(name, None)
    sys.path[:0] = [str(tree / "04_scripts" / "04_hydraulic" / "coupled"),
                    str(tree / "05_tests" / "unit")]
    plan = importlib.import_module("jp3_12b_plan")
    tools = importlib.import_module("test_jp3_12b_tools")
    del sys.path[:2]
    return plan, tools


def build_tree(root: Path) -> Path:
    run = root / "06_analysis" / "02_control" / "j_p3_cause" / "j9_runs" / "606f8713"
    dry = run / "cdry_a1"
    key_text = json.dumps({"key": "L2|s50|g6|0|x0|top|Fs0"})
    for folder in (dry / "VBK_c92_b1", dry / "logs", dry / "VBK0_c92"):
        folder.mkdir(parents=True)
        (folder / "run.json").write_text(key_text, encoding="utf-8")
    return root / "06_analysis"


def digests(folder: Path) -> dict[str, str]:
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(folder.iterdir())}


def main() -> None:
    scratch, old_tree, new_tree = (Path(arg) for arg in sys.argv[1:4])
    work = scratch / "ed6_bytes"
    scan_root = build_tree(work / "repo")
    extra = work / "tests"
    extra.mkdir()
    result = {}
    for edition, kwargs in ((5, {}), (6, {"excludes": ("*VBK_c9*",)})):
        outputs = {}
        for name, tree in (("old", old_tree), ("new", new_tree)):
            plan, tools = load(tree)
            noise = work / f"noise_{edition}_{name}.json"
            sha = tools.write_noise(noise)
            out = work / f"out_{edition}_{name}"
            plan.select(noise, scan_root, out, noise_sha256=sha, edition=edition,
                        extra_roots=(extra,), **kwargs)
            outputs[name] = digests(out)
        # selection.json holds the noise path, which differs by name: compare it without it
        texts = {}
        for name in ("old", "new"):
            document = json.loads((work / f"out_{edition}_{name}" / "selection.json")
                                  .read_text(encoding="utf-8"))
            document["inputs"]["noise"]["path"] = "<noise>"
            texts[name] = json.dumps(document, sort_keys=True)
        plans_same = {key: outputs["old"][key] == outputs["new"].get(key)
                      for key in outputs["old"] if key != "selection.json"}
        result[f"edition_{edition}"] = {"plan_files_same": plans_same,
                                        "selection_same_but_noise_path": texts["old"]
                                        == texts["new"],
                                        "files": sorted(outputs["new"])}
    (scratch / "ed6_12b_bytes.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
