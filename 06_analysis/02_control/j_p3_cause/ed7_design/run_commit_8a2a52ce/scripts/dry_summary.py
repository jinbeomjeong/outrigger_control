"""Summarise a dry run of the edition 7 run steps (commands_ed7.json) into a text file."""

import json
import sys
from pathlib import Path


def summarise(commands_path: Path) -> list[str]:
    document = json.loads(commands_path.read_text(encoding="utf-8-sig"))
    lines = [f"run_commit {document['run_commit']}", "exit codes:"]
    lines += [f"  {code}  {name}" for name, code in document["exit_codes"].items()]
    for step in sorted(document["steps"], key=lambda item: item["folder"]):
        codes = step["codes"]
        start, end = codes.get("identity_start", {}), codes.get("identity_end", {})
        lines.append(f"\n[{step['step']}] {step['folder']}")
        lines.append(f"  scope: {codes.get('scope')}")
        lines.append(f"  identity start: head={start.get('head')} clean={start.get('is_clean')} "
                     f"src_tree={start.get('src_tree')}")
        lines.append(f"  identity end:   head={end.get('head')} clean={end.get('is_clean')} "
                     f"src_tree={end.get('src_tree')}")
        for name, value in codes.items():
            if name.startswith(("core:", "input:", "decision", "selection", "evidence:")):
                lines.append(f"  {name} = {value}")
        for command in step["commands"] or []:
            lines.append(f"  cmd {command['label']} mask={command.get('mask')} "
                         f"workers={command.get('workers')}")
            lines.append(f"      {command['command']}")
            if command.get("environment"):
                lines.append(f"      env {json.dumps(command['environment'], sort_keys=True)}")
    return lines


def main() -> int:
    commands_path, out_path = (Path(argument) for argument in sys.argv[1:3])
    out_path.write_text("\n".join(summarise(commands_path)) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
