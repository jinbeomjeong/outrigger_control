"""Run the runner judges (``run_S8C.py judge`` / ``run_S6C.py judge``) for the L2b / L1-R rows of
one bundle, named as ``judge_b9f5707/chrono_path1/runner_judge/`` (rev18 R18-2, python-expert
2026-11-15). The runner folder of a row is the parent of ``chrono_rows_judge`` ``rows[].dir``.

Usage: python -I -B runner_judges.py <python.exe> <root> <judge_<B>.json> <prefix> <out dir>
Exit codes: 0 every runner judge exited 0, 1 one did not, 2 input missing.
"""

import json
import subprocess
import sys
from pathlib import Path

CONSISTENCY_REF = Path("06_analysis/02_control/r8_10hz/d1/bundle_c_consistency_ref.json")
"""The ``--consistency-ref`` of the b9f5707 L1-R runner judge outputs (their ``meta``)."""


def command(python: str, root: Path, engine: str, folder: Path, out: Path) -> list[str]:
    if engine == "L2b":
        return [python, "-I", "-B", "-X", "utf8", str(root / "04_scripts/02_chrono/run_S8C.py"),
                "judge", "--batch", str(folder), "--out", str(out)]
    return [python, "-I", "-B", "-X", "utf8", str(root / "04_scripts/02_chrono/run_S6C.py"),
            "judge", "--batch", str(folder), "--out", str(out),
            "--consistency-ref", str(root / CONSISTENCY_REF)]


def main() -> int:
    python, root, judge_path, prefix, out_dir = sys.argv[1:6]
    root, out_dir = Path(root), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = json.loads(Path(judge_path).read_text(encoding="utf-8"))
    codes = {}
    for row in doc["rows"]:
        engine = row.get("engine")
        if engine not in ("L2b", "L1R"):
            continue
        suffix = "verify_S8C" if engine == "L2b" else "verify_S6C"
        out = out_dir / f"{prefix}_{row['case']}.{suffix}.json"
        folder = Path(row["dir"]).parent
        argv = command(python, root, engine, folder, out)
        done = subprocess.run(argv, cwd=root, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", check=False)
        (out_dir / f"{prefix}_{row['case']}.stdout.txt").write_text(
            done.stdout + done.stderr, encoding="utf-8", newline="\n")
        codes[row["case"]] = done.returncode
        print(f"{row['case']} exit {done.returncode}", flush=True)
    (out_dir / f"exit_codes_{prefix}.json").write_text(json.dumps(codes, indent=1) + "\n",
                                                       encoding="utf-8", newline="\n")
    return 0 if codes and all(code == 0 for code in codes.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
