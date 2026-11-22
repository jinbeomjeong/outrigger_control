"""436.9 edition 5 erratum 2 2-1 (file level, recommended): no L1 reference run is a j9_main
judged input.

Before a j9_main judge command: the sha256 of every ``--input`` file against the sha256 of the
four L1 reference runs (erratum 2 2-7.1 / G-1: the two 12b ``l1ref`` runs by their
``FIXED_INPUTS`` sha256, ``--l1-reference-sha256``; the two T-JR-12a L1 runs of the attempt
``dg3.done`` names by their files, ``--l1-reference``). A shared sha256 is a setting defect and
the judge does not start (the line-level refusal of ``j_p3_inputs`` covers J-P3 only, not J1 ..
J11).

Usage (python-dev, read only but for ``--out``):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_l1_input_guard.py
      --l1-reference-sha256 <12b VBJ sha> --l1-reference-sha256 <12b VBJ0 sha>
      --l1-reference <dg3>/l1_VBJ.json --l1-reference <dg3>/l1_VBJ0.json
      --input <j9_main rows> [--input ...] --out <report.json>

Exit 0 ``clean``, 2 ``setting_defect`` (a shared sha256) or ``not_judgeable`` (a file missing,
an existing ``--out``), 3 ``error``. The stdout's last line is JSON with ``status``, the counts
and the report path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

L1_REFERENCE_COUNT = 4
"""Two 12b L1 references (VBJ, VBJ0) and two T-JR-12a L1 references (VBJ, VBJ0)."""
EXIT_CLEAN, EXIT_STOP, EXIT_ERROR = 0, 2, 3


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def guard(l1_references: list[Path], inputs: list[Path],
          l1_shas: list[str] | None = None) -> dict:
    """The report (module docstring). ``l1_shas``: L1 references given by sha256 (erratum 2
    G-1: the two 12b runs by their ``FIXED_INPUTS`` sha256)."""
    l1_shas = [sha.lower() for sha in l1_shas or []]
    missing = [str(path) for path in [*l1_references, *inputs] if not Path(path).is_file()]
    if missing:
        return {"status": "not_judgeable", "missing": missing}
    count = len(l1_references) + len(l1_shas)
    if count != L1_REFERENCE_COUNT:
        return {"status": "not_judgeable",
                "reason": f"{count} L1 references, {L1_REFERENCE_COUNT} expected"}
    references = {file_sha256(path): str(path) for path in l1_references}
    references.update({sha: f"(fixed list sha256 {sha[:12]})" for sha in l1_shas})
    shared = [{"input": str(path), "l1_reference": references[sha]}
              for path in inputs if (sha := file_sha256(path)) in references]
    return {"rule": "jp3_remedy_spec_v5_erratum2.md 2-1 (file level)",
            "status": "setting_defect" if shared else "clean", "inputs": len(inputs),
            "l1_references": [{"path": path, "sha256": sha} for sha, path in references.items()],
            "shared": shared}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--l1-reference", type=Path, action="append", default=[],
                        help="an L1 reference run file (its sha256 is read)")
    parser.add_argument("--l1-reference-sha256", action="append", default=[],
                        help="an L1 reference run by its fixed list sha256 (erratum 2 G-1)")
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        print(json.dumps({"status": "not_judgeable", "reason": "--out exists"}))
        return EXIT_STOP
    try:
        report = guard(args.l1_reference, args.input, args.l1_reference_sha256)
    except Exception as exc:  # noqa: BLE001 (every other failure is a tool error)
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(json.dumps({"status": "error"}))
        return EXIT_ERROR
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1)
    print(json.dumps({"status": report["status"], "shared": len(report.get("shared", [])),
                      "out": str(args.out)}))
    return EXIT_CLEAN if report["status"] == "clean" else EXIT_STOP


if __name__ == "__main__":
    sys.exit(main())
