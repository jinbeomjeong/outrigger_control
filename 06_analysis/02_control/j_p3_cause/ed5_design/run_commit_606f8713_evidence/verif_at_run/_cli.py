"""Shared command-line plumbing for the verif tools.

Copied from ``tools/paper/_cli.py`` (tool folders never import each other).

Every tool follows the same contract:

* The full report goes to a UTF-8 file (``--out``); stdout carries a few
  human-readable lines and, as its very last line, a one-line JSON summary
  whose first key is ``"status"`` (``ok``/``findings``/``input_error``/
  ``internal_error``).
* Exit codes: 0 no findings, 1 findings, 2 input error, 3 internal failure.
* Input files are opened read-only and never written.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_INPUT_ERROR = 2
EXIT_INTERNAL_ERROR = 3
STATUS_BY_EXIT_CODE = {
    EXIT_OK: "ok",
    EXIT_FINDINGS: "findings",
    EXIT_INPUT_ERROR: "input_error",
    EXIT_INTERNAL_ERROR: "internal_error",
}

logger = logging.getLogger(__name__)


class InputError(Exception):
    """The input is unusable: missing, unreadable, or an invalid argument."""


@dataclass
class ToolOutcome:
    """What a tool's work function hands back to :func:`run_tool`."""

    exit_code: int
    lines: list[str] = field(default_factory=list)
    summary: dict[str, object] = field(default_factory=dict)


def configure_console() -> None:
    """Force UTF-8 console streams and send log records to stderr."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")
    logging.basicConfig(
        stream=sys.stderr, level=logging.WARNING, format="%(levelname)s: %(message)s"
    )


def require_existing_file(path_text: str | Path, role: str = "input") -> Path:
    """Return the absolute path of an existing file.

    Raises:
        InputError: If the path does not exist or is not a regular file.
    """
    path = Path(path_text).expanduser().resolve()
    if not path.is_file():
        raise InputError(f"{role} file not found: {path}")
    return path


def require_distinct_output(output_path: Path, input_paths: list[Path]) -> None:
    """Refuse to write over any input file.

    Raises:
        InputError: If ``output_path`` points at one of ``input_paths``.
    """
    resolved_output = output_path.resolve()
    for input_path in input_paths:
        if resolved_output == input_path.resolve():
            raise InputError(f"output would overwrite an input file: {output_path}")


def write_report(output_path: Path, text: str) -> None:
    """Write the report as UTF-8, creating the parent folder when needed."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")


def emit_result(lines: list[str], summary: dict[str, object]) -> None:
    """Print the readable lines, then the JSON summary as the last stdout line.

    The summary always starts with ``"status"`` derived from ``exit_code``.
    """
    for line in lines:
        print(line)
    exit_code = summary.get("exit_code")
    status = (
        STATUS_BY_EXIT_CODE.get(exit_code, "unknown")
        if isinstance(exit_code, int)
        else "unknown"
    )
    print(json.dumps({"status": status, **summary}, ensure_ascii=False))


def parse_arguments(
    parser: argparse.ArgumentParser, argv: list[str] | None
) -> argparse.Namespace:
    """Parse arguments; on bad arguments also print the JSON summary line.

    argparse already exits with status 2, which equals ``EXIT_INPUT_ERROR``.
    """
    try:
        return parser.parse_args(argv)
    except SystemExit as exit_request:
        if exit_request.code not in (0, None):
            emit_result(
                [],
                {
                    "ok": False,
                    "exit_code": EXIT_INPUT_ERROR,
                    "error": "invalid arguments",
                },
            )
        raise


def run_tool(work: Callable[[], ToolOutcome]) -> int:
    """Run a tool's work function and map its outcome to an exit code.

    Returns:
        The work function's exit code, ``EXIT_INPUT_ERROR`` for
        :class:`InputError`, or ``EXIT_INTERNAL_ERROR`` for any other
        exception (traceback on stderr).
    """
    try:
        outcome = work()
    except InputError as error:
        logger.error("%s", error)
        emit_result(
            [], {"ok": False, "exit_code": EXIT_INPUT_ERROR, "error": str(error)}
        )
        return EXIT_INPUT_ERROR
    except Exception as error:
        # Last-resort boundary of the CLI: report the bug instead of a bare crash.
        logger.exception("internal failure")
        emit_result(
            [], {"ok": False, "exit_code": EXIT_INTERNAL_ERROR, "error": str(error)}
        )
        return EXIT_INTERNAL_ERROR
    emit_result(
        outcome.lines, {"ok": True, "exit_code": outcome.exit_code, **outcome.summary}
    )
    return outcome.exit_code
