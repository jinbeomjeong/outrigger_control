"""436.9 prelaunch audit M-1: the run identity (interpreter, thread variables, affinity, git
head and ``is_clean``) of a run whose runner writes none (``jp3_case_replay.py``,
``jp3_x11_replay.py``, the r79 Dg-3 runner ``las_t3_dg3.py``), next to its output as
``<output stem>.identity.json`` -- the record ``run_v5._write_identity`` writes and
``baseline_221456d/_runners/identity_mark.py`` wrote for the baseline.

Sub-commands:

``mark``  ``<output> start|end``: append one record (the ``identity_mark.py`` form).
``wrap``  ``<output> -- <command ...>``: the start record, the command (this process's
          environment and working folder; its exit code is this one's), the end record (also
          after a failed or interrupted command).

Both refuse (exit 2, nothing written) when the sidecar already holds a record of another git
head: an appended or resumed output stays within one commit (prelaunch audit M-1).

Exit codes: ``mark`` 0 written, 2 refused; ``wrap`` the command's exit code, 2 refused before it
started.

Usage (dynamics-dev, project root of the worktree; the main session writes the commands):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_run_identity.py wrap
      <folder>/case_C.jsonl -- <dynamics-dev python.exe> -I -B
      04_scripts/04_hydraulic/coupled/jp3_case_replay.py --out <folder>/case_C.jsonl ...
  python -I -B .../jp3_run_identity.py wrap <folder>/dg3_VBH.json -- <python.exe> -I -B
      04_scripts/04_hydraulic/coupled/las_t3_dg3.py <root> run <folder>/dg3_VBH.json ...
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

MOMENTS = ("start", "end")
REFUSED_EXIT = 2


def sidecar_path(output: Path) -> Path:
    """``run_v5._write_identity``'s sidecar of an output file."""
    return output.with_name(output.stem + ".identity.json")


def recorded_heads(output: Path) -> set[str | None]:
    """The git heads of the records already next to ``output`` (empty: no sidecar)."""
    sidecar = sidecar_path(output)
    if not sidecar.exists():
        return set()
    stored = json.loads(sidecar.read_text(encoding="utf-8"))
    return {(record.get("git") or {}).get("head")
            for moment in MOMENTS for record in stored.get(moment) or []}


def current_head(run_v5) -> str:
    """The git head of the worktree this file belongs to (``run_v5.ROOT``; "" = git failed,
    ``d8x_record._git``)."""
    import d1_rows

    return (d1_rows._d8x_record_module().git_state(run_v5.ROOT) or {}).get("head") or ""


def head_problem(output: Path, run_v5) -> str | None:
    """Why ``output`` cannot take a record of this commit (None = it can)."""
    head = current_head(run_v5)
    if not head:
        return "no git head (git failed): no identity record"
    other = sorted(str(value) for value in recorded_heads(output) if value != head)
    if other:
        return (f"{sidecar_path(output)} holds records of git head {other}, this run is {head}: "
                "a resumed or appended output stays within one commit")
    return None


def _run_v5():
    import run_v5

    if Path(run_v5.ROOT).resolve() != HERE.parents[2].resolve():
        raise SystemExit(f"run_v5 ROOT {run_v5.ROOT} is not this tree {HERE.parents[2]}")
    return run_v5


def mark(output: Path, moment: str) -> int:
    """One identity record (``identity_mark.py``)."""
    run_v5 = _run_v5()
    problem = head_problem(output, run_v5)
    if problem is not None:
        print(f"refused: {problem}", file=sys.stderr)
        return REFUSED_EXIT
    run_v5._write_identity(output, moment)
    print(json.dumps({"identity": moment, "sidecar": str(sidecar_path(output))}))
    return 0


def wrap(output: Path, command: list[str]) -> int:
    """Start record, the command, end record; the command's exit code."""
    run_v5 = _run_v5()
    problem = head_problem(output, run_v5)
    if problem is not None:
        print(f"refused: {problem}", file=sys.stderr)
        return REFUSED_EXIT
    run_v5._write_identity(output, "start")
    exit_code = None
    try:
        exit_code = subprocess.run(command, check=False).returncode  # noqa: S603 (given command)
    finally:
        run_v5._write_identity(output, "end")
        print(json.dumps({"identity": "start/end", "sidecar": str(sidecar_path(output)),
                          "command_exit": exit_code}))
    return exit_code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    mark_parser = commands.add_parser("mark")
    mark_parser.add_argument("output", type=Path)
    mark_parser.add_argument("moment", choices=MOMENTS)
    wrap_parser = commands.add_parser("wrap")
    wrap_parser.add_argument("output", type=Path)
    wrap_parser.add_argument("child", nargs=argparse.REMAINDER,
                             help="-- <command ...>")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "mark":
        return mark(args.output, args.moment)
    child = args.child[1:] if args.child[:1] == ["--"] else args.child
    if not child:
        parser.error("wrap needs -- <command ...>")
    return wrap(args.output, child)


if __name__ == "__main__":
    sys.exit(main())
