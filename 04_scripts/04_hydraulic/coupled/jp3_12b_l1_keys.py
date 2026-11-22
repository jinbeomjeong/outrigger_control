"""436.9 edition 5 erratum 2 2-1: the L1 key file of the 12b grade reference runs.

From the 167 L2 cases of the fixed case source (``h8_noise_VB.json``, sha256 of
``jp3_fixed_inputs.NOISE_VB_SHA256``; ``jp3_12b_plan.l2_cases``, first-appearance order) one
key ``L1|s0|<harness>|<case_index>|<inner>`` per distinct (harness, inner), in the order of
their first case. The key file (one key per line, LF) is the ``--keys-file`` of the two L1
runs (VBJ0 and VBJ, ``R79_ROD_MODEL=plant_truth``) that ``grade-judge`` reads as the L1
reference of the VBK0 and the VBK arm; its sha256 goes into ``FIXED_INPUTS_<run commit 8>``.
Only key strings are read (no value of the case source).

Usage (python-dev or Chrono-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_12b_l1_keys.py --noise <h8_noise_VB.json>
      --out <ed5_inputs>/l1_keys_12b.txt

Exit 0 written, 2 not usable (not the fixed source, not 167 cases, an existing ``--out``),
3 a tool error. The stdout's last line is JSON with ``status``, the key count, the sha256 and
the output path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import jp3_12b_plan as plan  # noqa: E402

L1_LEVEL = "L1"
L1_SEED = 0
EXIT_WRITTEN, EXIT_NOT_USABLE, EXIT_ERROR = 0, 2, 3


def l1_keys(cases: list[str], source_l1_keys: list[str] | None = None) -> list[str]:
    """One L1 key per distinct (harness, inner) of the cases (``L2|<harness>|<index>|<inner>``),
    in the order of their first case, with the case index of that first case.

    ``source_l1_keys`` (the source's own L1 keys): when given, each generated key must be one
    of them (the runner's ``--keys-file`` takes table-rule jobs only).

    Raises:
        plan.NotUsable: A generated key is not an L1 job of the source.
    """
    keys, seen = [], set()
    for case in cases:
        _, harness, index, *inner = case.split("|")
        identity = (harness, "|".join(inner))
        if identity in seen:
            continue
        seen.add(identity)
        keys.append("|".join([L1_LEVEL, f"s{L1_SEED}", harness, index, *inner]))
    if source_l1_keys is not None:
        missing = [key for key in keys if key not in set(source_l1_keys)]
        if missing:
            raise plan.NotUsable(f"{len(missing)} L1 keys are no L1 job of the case source "
                                 f"(first {missing[0]})")
    return keys


def source_l1_keys(noise: dict) -> list[str]:
    """The plain ``L1|s0|...`` keys of the case source (key strings only)."""
    return [plan.plain_key(line["key"]) for line in noise["results"]
            if line.get("level") == L1_LEVEL]


def write_l1_keys(noise: Path, out: Path, noise_sha256: str = plan.fixed.NOISE_VB_SHA256) -> dict:
    """The key file (module docstring) and its record.

    Raises:
        plan.NotUsable: Not the fixed source, not 167 cases, or an existing ``out``.
    """
    problem = plan.fixed.sha_problem(noise, noise_sha256, "--noise")
    if problem is not None:
        raise plan.NotUsable(problem)
    if out.exists():
        raise plan.NotUsable(f"{out} exists (never overwritten)")
    source = json.loads(noise.read_text(encoding="utf-8"))
    cases = plan.l2_cases(source)
    if len(cases) != plan.CASE_COUNT:
        raise plan.NotUsable(f"{len(cases)} L2 cases, {plan.CASE_COUNT} expected")
    keys = l1_keys(cases, source_l1_keys(source))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write("".join(f"{key}\n" for key in keys))
    return {"keys": len(keys), "cases": len(cases),
            "sha256": hashlib.sha256(out.read_bytes()).hexdigest(), "out": str(out)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--noise", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        record = write_l1_keys(args.noise, args.out)
    except plan.NotUsable as exc:
        print(f"not usable: {exc}", file=sys.stderr)
        print(json.dumps({"status": "not_usable", "out": str(args.out)}))
        return EXIT_NOT_USABLE
    except Exception as exc:  # noqa: BLE001 (every other failure is a tool error)
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(json.dumps({"status": "error", "out": str(args.out)}))
        return EXIT_ERROR
    print(json.dumps({"status": "written", **record}))
    return EXIT_WRITTEN


if __name__ == "__main__":
    sys.exit(main())
