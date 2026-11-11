"""Run identity of the LOC shadow drivers (H-SH, E5a): checkout, code, interpreter, env.

Written as a JSON sidecar next to the output at the start and again at the end of a batch.
Standard library only (``psutil`` optional, for the affinity mask).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ENV_NAMES = ("MKL_THREADING_LAYER", "OMP_WAIT_POLICY", "R72_PATH", "R79_AFFINITY",
             "CONDA_PREFIX", "PYTHONDONTWRITEBYTECODE")
ENV_PREFIXES = ("ACC_", "OUTRIGGER_")
ENV_SUFFIX = "_NUM_THREADS"
GIT_TIMEOUT_S = 120
CODE_PATHS = ("03_src", "04_scripts", "02_params", "06_analysis/02_control/touch_phase")
C2_PATH = Path("03_src") / "outrigger_sim" / "control" / "c2.py"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                               encoding="utf-8", timeout=GIT_TIMEOUT_S, check=True)
    return completed.stdout.strip()


def env_subset(environ: dict[str, str] | None = None) -> dict[str, str]:
    environ = os.environ if environ is None else environ
    return {name: value for name, value in sorted(environ.items())
            if name in ENV_NAMES or name.endswith(ENV_SUFFIX) or name.startswith(ENV_PREFIXES)}


def affinity_mask() -> str | None:
    try:
        import psutil
    except ImportError:
        return None
    cpus = psutil.Process().cpu_affinity()
    return hex(sum(1 << cpu for cpu in cpus))


def identity(root: Path, tool_files: dict[str, Path]) -> dict:
    """HEAD, tracked changes, code diff digest, c2.py and tool sha256, interpreter, env, mask."""
    status = _git(root, "status", "--porcelain", "--untracked-files=no")
    code_diff = _git(root, "diff", "HEAD", "--", *CODE_PATHS)
    return {
        "time": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "root": str(root), "head": _git(root, "rev-parse", "HEAD"),
        "status_porcelain": status, "is_clean": status == "",
        "code_diff_sha256": hashlib.sha256(code_diff.encode("utf-8")).hexdigest(),
        "c2_sha256": file_sha256(root / C2_PATH),
        "c2_blob": _git(root, "rev-parse", f"HEAD:{C2_PATH.as_posix()}"),
        "tools_sha256": {name: file_sha256(path) for name, path in sorted(tool_files.items())},
        "python_executable": sys.executable, "python_version": sys.version,
        "argv": list(sys.argv), "env": env_subset(), "affinity_mask": affinity_mask(),
        "pid": os.getpid(),
    }


def write_sidecar(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1), encoding="utf-8")
