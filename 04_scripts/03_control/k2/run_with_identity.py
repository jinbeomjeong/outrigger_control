"""Run one K-2 step and write its identity sidecar (``k2_commands.json`` ``identity_sidecar``).

The step runners (``acc_d8``, ``acc_launch``, ``run_ps7``, ``g8trace``) keep no return code and, for acc_d8, no raw
argv. This wrapper starts the command unchanged and records, in a JSON sidecar:

* ``argv`` (the raw command after ``--``), ``cwd``, the environment subset (``MKL_THREADING_LAYER``,
  ``*_NUM_THREADS``, ``ACC_*``, ``OMP_WAIT_POLICY``, ``OUTRIGGER_*``);
* the processor affinity mask of this process (the child inherits it; the wrapper never sets one) and the child's
  own mask read right after its start;
* start / end time, the child pid and its return code;
* ``git rev-parse HEAD`` and ``git status --porcelain --untracked-files=no`` of the checkout (``--git-dir``,
  default ``cwd``) at the start and at the end.

The sidecar is written once before the child starts (``"rc": null``) and again at the end, so a crash leaves the
start record. The child's stdout / stderr are not captured (they go where the wrapper's go).

Usage::

    python -I -B run_with_identity.py <sidecar.json> [--git-dir <checkout>] -- <interpreter> <args ...>

Exit: the child's return code; 125 when the wrapper cannot start (bad arguments, an existing sidecar, the command
not found). The last stdout line is JSON.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

EXIT_WRAPPER_ERROR = 125
ENV_NAMES = ("MKL_THREADING_LAYER", "OMP_WAIT_POLICY")
ENV_PREFIXES = ("ACC_", "OUTRIGGER_")
ENV_SUFFIX = "_NUM_THREADS"


def env_subset(environ: dict[str, str]) -> dict[str, str]:
    """The identity environment: named keys, ``*_NUM_THREADS``, ``ACC_*`` and ``OUTRIGGER_*``."""
    return {name: value for name, value in sorted(environ.items())
            if name in ENV_NAMES or name.endswith(ENV_SUFFIX) or name.startswith(ENV_PREFIXES)}


def affinity_mask(pid: int | None = None) -> str | None:
    """Hex affinity mask of a process (this one by default); None when it cannot be read."""
    try:
        import psutil

        cpus = psutil.Process(pid).cpu_affinity()
        return hex(sum(1 << cpu for cpu in cpus))
    except Exception:  # psutil missing, the process gone or access denied: recorded as unknown
        return _affinity_mask_ctypes(pid)


def _affinity_mask_ctypes(pid: int | None) -> str | None:
    if sys.platform != "win32":
        try:
            return hex(sum(1 << cpu for cpu in os.sched_getaffinity(pid or 0)))
        except (AttributeError, OSError):
            return None
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    query_information = 0x1000  # PROCESS_QUERY_LIMITED_INFORMATION
    handle = (kernel32.GetCurrentProcess() if pid is None
              else kernel32.OpenProcess(query_information, False, pid))
    if not handle:
        return None
    process_mask, system_mask = ctypes.c_size_t(), ctypes.c_size_t()
    try:
        ok = kernel32.GetProcessAffinityMask(wintypes.HANDLE(handle), ctypes.byref(process_mask),
                                             ctypes.byref(system_mask))
    finally:
        if pid is not None:
            kernel32.CloseHandle(handle)
    return hex(process_mask.value) if ok else None


def git_state(folder: Path) -> dict:
    """HEAD and the porcelain status (tracked files) of ``folder``; ``error`` when git fails."""
    def run(*args: str) -> tuple[int, str]:
        done = subprocess.run(["git", "-C", str(folder), *args], capture_output=True, text=True,
                              encoding="utf-8", timeout=120, check=False)
        return done.returncode, done.stdout.strip()

    try:
        rc_head, head = run("rev-parse", "HEAD")
        rc_status, status = run("status", "--porcelain", "--untracked-files=no")
    except (OSError, subprocess.SubprocessError) as exc:
        return {"error": repr(exc)}
    if rc_head or rc_status:
        return {"error": f"git rc {rc_head} / {rc_status}", "head": head or None}
    return {"head": head, "status_porcelain": status, "is_clean": status == ""}


def _now() -> str:
    return dt.datetime.now(dt.UTC).astimezone().isoformat(timespec="milliseconds")


def _write(path: Path, record: dict) -> None:
    path.write_text(json.dumps(record, indent=1), encoding="utf-8")


def _parse(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    if "--" not in argv:
        raise ValueError("expected: <sidecar.json> [--git-dir DIR] -- <interpreter> <args ...>")
    split = argv.index("--")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sidecar", type=Path)
    parser.add_argument("--git-dir", type=Path, default=None)
    args = parser.parse_args(argv[:split])
    command = argv[split + 1:]
    if not command:
        raise ValueError("no command after --")
    return args, command


def run(argv: list[str]) -> int:
    try:
        args, command = _parse(argv)
        if args.sidecar.exists():
            raise ValueError(f"sidecar {args.sidecar} exists (new files only)")
        args.sidecar.parent.mkdir(parents=True, exist_ok=True)
    except (ValueError, SystemExit, OSError) as exc:
        print(json.dumps({"exit": EXIT_WRAPPER_ERROR, "error": str(exc)}))
        return EXIT_WRAPPER_ERROR
    cwd = Path.cwd()
    git_folder = args.git_dir or cwd
    record = {"tool": "run_with_identity", "argv": command, "cwd": str(cwd),
              "env": env_subset(dict(os.environ)), "wrapper_python": sys.executable,
              "affinity_mask": affinity_mask(), "child_affinity_mask": None,
              "start": _now(), "end": None, "pid": None, "rc": None,
              "git_start": git_state(git_folder), "git_end": None}
    _write(args.sidecar, record)
    try:
        child = subprocess.Popen(command)  # inherits cwd, env, std streams and the affinity
    except OSError as exc:
        record.update(end=_now(), error=repr(exc), rc=EXIT_WRAPPER_ERROR)
        _write(args.sidecar, record)
        print(json.dumps({"exit": EXIT_WRAPPER_ERROR, "error": repr(exc)}))
        return EXIT_WRAPPER_ERROR
    record.update(pid=child.pid, child_affinity_mask=affinity_mask(child.pid))
    _write(args.sidecar, record)
    try:
        rc = child.wait()
    except KeyboardInterrupt:
        rc = child.wait()
        record["interrupted"] = True
    record.update(end=_now(), rc=rc, git_end=git_state(git_folder))
    _write(args.sidecar, record)
    print(json.dumps({"rc": rc, "sidecar": str(args.sidecar)}))
    return rc


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
