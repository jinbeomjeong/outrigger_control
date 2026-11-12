"""436.8 path 1 judge of T-3K (H-0), new version (rules rev5 R5-A1, rev6 R6-C2).

The verdict code is ``las_t3_judge._judge_t3_rev5`` (K-0 .. K-7, H-T3-0 .. H-T3-6) with three
definitions replaced (rev5 R5-A3):

  D-20  Dg-3 folder (off / v4_on) from the line's recorded ``two_pressure.extend_start_rule``
        (``tracked_bound`` = v4_on), not from the key-list entry (rev3 R3-D1). The key-list
        folder is still compared with the record (K-3) and listed in ``dg3_folders``.
  D-21  K-0 identity, rev6 R6-C2 table (plan b: the actual ``d8x_record.run_identity`` fields
        of the ``.identity.json`` ``start`` / ``end`` records): ``git.head`` start = end =
        ``git_at_start``; ``git.is_clean`` (``status_porcelain`` as evidence); the five
        ``threads`` (four = 1, ``MKL_THREADING_LAYER`` TBB); every ``rules_seals`` entry ``ok``;
        ``affinity_mask`` start = end; head / threads / affinity equal over R-0, R-0K, T-3K (else
        H-T3-3). Controller and tool sha256 come from the T-3K outputs' line / header
        identities (``las_t3_judge._header_problems``: every line = its header, three headers
        equal; else H-T3-3; ``c2_sha256`` vs ``git_at_start`` recorded).
        ``OUTRIGGER_LOC_SHADOW`` by the rev1 RV1-9 ``resume4368_judge import-check`` report
        (``--import-check``). A missing field or report is ``판정 불가``.
  D-22  K-6 READY +5.0 s and stroke +0.001 m are compared with the rules 7.6 allowance 1e-9
        (``(X, X + 1e-9]`` is not a violation, rev3 R3-D4).

Usage (dynamics-dev or python-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/las_t3_judge_4368.py --out <report.json>
      --r0 <R-0 jsonl> --r0k <R-0K jsonl> --t3 <T-3K jsonl> --baseline <v5/d1.jsonl>
      --identity <R-0 .identity.json> --identity <R-0K ...> --identity <T-3K ...>
      --git-at-start <commit> [--import-check <RV1-9 report>]
      [--keys <key list>] [--r0k-keys <R-0K key list>]
      [--las-rules-dir <las_targeted rules dir>] [--rules-dir <verif_matrix>]
Exit codes: 0 passed, 1 a stop / 판정 불가, 2 input error, 3 internal error.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.append(str(_path))

import judge4368_common as common  # noqa: E402
import las_h7  # noqa: E402
import las_t3  # noqa: E402
import las_t3_judge as base  # noqa: E402

DEFINITION_CHANGES = ("D-20", "D-21", "D-22")
TRACKED_BOUND = "tracked_bound"
C2_PATH = "03_src/outrigger_sim/control/c2.py"
ONE_THREAD_VARIABLES = (
    "MKL_NUM_THREADS",
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMBA_NUM_THREADS",
)
THREAD_LAYER = "TBB"
SIDECAR_FIELDS = (
    "git.head",
    "git.is_clean",
    "git.status_porcelain",
    "threads",
    "affinity_mask",
    "rules_seals",
)
"""Rev6 R6-C2: the ``d8x_record.run_identity`` fields K-0 reads from ``start`` and ``end``."""
IMPORT_CHECK_SECTION = "RV1-9"
"""``resume4368_judge import-check`` report section (rev6 R6-C2 forbidden-env row)."""


# --------------------------------------------------------------------------------------- D-20
def recorded_folder(line: dict) -> str:
    """Rev3 R3-D1: v4_on when the run recorded the tracked-bound ③ start rule."""
    return "v4_on" if line.get("extend_start_rule") == TRACKED_BOUND else "off"


_original_expected_tag = base.expected_tag


def expected_tag_4368(
    entry: dict, line: dict, las_on: bool, gate_on: bool | None = None
) -> str | None:
    """``las_t3_judge.expected_tag`` with the Dg-3 folder taken from the record (D-20)."""
    if entry["kind"] == las_t3.KIND_DG3:
        entry = {**entry, "folder": recorded_folder(line)}
    return _original_expected_tag(entry, line, las_on, gate_on)


def dg3_folders(lines: list[dict], entries: dict[str, list[dict]]) -> list[dict]:
    """Record: key-list folder vs recorded folder of every Dg-3 line."""
    by_key = {
        e["line_key"]: e
        for bundle in entries.values()
        for e in bundle
        if e.get("kind") == las_t3.KIND_DG3
    }
    out = []
    for line in lines:
        entry = by_key.get(base.line_key(line))
        if entry is not None:
            out.append(
                {
                    "line_key": entry["line_key"],
                    "key_list": entry["folder"],
                    "recorded": recorded_folder(line),
                    "same": entry["folder"] == recorded_folder(line),
                }
            )
    return out


# --------------------------------------------------------------------------------------- D-22
def install_allowance() -> dict:
    """D-22: the K-6 limits become ``X + 1e-9`` (the comparison stays ``>``)."""
    las_h7.READY_INCREASE_LIMIT_S = 5.0 + common.COMPARE_EPS
    las_h7.STROKE_INCREASE_LIMIT_M = 0.001 + common.COMPARE_EPS
    base.expected_tag = expected_tag_4368
    return {
        "READY_INCREASE_LIMIT_S": las_h7.READY_INCREASE_LIMIT_S,
        "STROKE_INCREASE_LIMIT_M": las_h7.STROKE_INCREASE_LIMIT_M,
    }


# --------------------------------------------------------------------------------------- D-21
def _dotted(record: dict, dotted: str) -> tuple[bool, Any]:
    node: Any = record
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return False, None
        node = node[part]
    return True, node


def c2_sha256_at(commit: str) -> str | None:
    completed = subprocess.run(  # noqa: S603 (fixed git arguments, read only)
        ["git", "-C", str(ROOT), "show", f"{commit}:{C2_PATH}"], capture_output=True, check=False
    )
    return hashlib.sha256(completed.stdout).hexdigest() if completed.returncode == 0 else None


def _moment(sidecar: dict, moment: str) -> dict | None:
    records = sidecar.get(moment)
    if isinstance(records, list):
        return records[-1] if records else None
    return records


def _state(is_ok: bool, evidence: Any, note: str | None = None) -> dict:
    out = {"state": "pass" if is_ok else "fail", "evidence": evidence}
    if note:
        out["note"] = note
    return out


def _missing(field: str) -> dict:
    return {"state": common.NOT_JUDGEABLE, "reason": f"{field} not in the sidecar"}


def identity_rows(sidecar: dict, git_at_start: str) -> dict:
    """Rev6 R6-C2 sidecar rows of one ``.identity.json`` (``d8x_record.run_identity``)."""
    start, end = _moment(sidecar, "start"), _moment(sidecar, "end")
    if start is None or end is None:
        return {"state": common.NOT_JUDGEABLE, "rows": {}, "reason": "start or end missing"}
    values = {}
    for field in SIDECAR_FIELDS:
        found = (_dotted(start, field), _dotted(end, field))
        values[field] = (found[0][1], found[1][1]) if found[0][0] and found[1][0] else None
    rows: dict[str, dict] = {}
    head = values["git.head"]
    rows["head"] = (
        _missing("git.head")
        if head is None
        else _state(head[0] == head[1] and str(head[0]).startswith(git_at_start), head)
    )
    clean = values["git.is_clean"]
    rows["work_tree"] = (
        _missing("git.is_clean")
        if clean is None
        else _state(
            clean[0] is True,
            (values["git.status_porcelain"] or (None,))[0],
            note="dirty files allowed only when the pre-run audit says so",
        )
    )
    threads = values["threads"]
    rows["threads"] = _missing("threads") if threads is None else _threads_row(threads[0])
    seals = values["rules_seals"]
    rows["rules_seals"] = (
        _missing("rules_seals")
        if seals is None
        else _state(_seals_ok(seals[0]) and _seals_ok(seals[1]), _seal_names(seals[0]))
    )
    affinity = values["affinity_mask"]
    rows["affinity_mask"] = (
        _missing("affinity_mask")
        if affinity is None
        else _state(affinity[0] == affinity[1], affinity)
    )
    return {
        "state": _worst(row["state"] for row in rows.values()),
        "rows": rows,
        "compared": {
            "head": None if head is None else head[0],
            "threads": None if threads is None else threads[0],
            "affinity_mask": None if affinity is None else affinity[0],
        },
    }


def _threads_row(threads: dict | None) -> dict:
    threads = threads or {}
    is_ok = (
        all(str(threads.get(name)) == "1" for name in ONE_THREAD_VARIABLES)
        and threads.get("MKL_THREADING_LAYER") == THREAD_LAYER
    )
    return _state(is_ok, threads)


def _seals_ok(seals: Any) -> bool:
    return (
        isinstance(seals, dict)
        and bool(seals)
        and all(isinstance(entry, dict) and entry.get("ok") is True for entry in seals.values())
    )


def _seal_names(seals: Any) -> list[str] | None:
    return sorted(seals) if isinstance(seals, dict) else None


def _worst(states) -> str:
    states = set(states)
    if "fail" in states:
        return "fail"
    return common.NOT_JUDGEABLE if common.NOT_JUDGEABLE in states else "pass"


def header_identity_row(paths: dict[str, Path], c2_at_start: str | None) -> dict:
    """Rev6 R6-C2 "제어기·도구 sha": the T-3K output line / header identities
    (``las_targeted_rules_rev3`` K-0 source: every line = its header, three headers equal)."""
    headers, lines = {}, {}
    for label, path in paths.items():
        headers[label], lines[label] = base.read_jsonl(path)
    problems = base._header_problems(headers, lines)  # noqa: SLF001 (the K-0 header check)
    identities = {label: (h or {}).get("identity") for label, h in headers.items()}
    c2_values = {label: (i or {}).get("c2_sha256") for label, i in identities.items()}
    return {
        **_state(not problems, problems),
        "identities": identities,
        "c2_sha256_vs_git_at_start": {
            "git_at_start": c2_at_start,
            "same": all(v == c2_at_start for v in c2_values.values()),
        },
    }


def forbidden_env_row(import_check: Path | None) -> dict:
    """Rev6 R6-C2 ``OUTRIGGER_LOC_SHADOW``: the rev1 RV1-9 ``resume4368_judge import-check``
    report (step env and import closure); no report = ``판정 불가``."""
    if import_check is None:
        return {"state": common.NOT_JUDGEABLE, "reason": "no RV1-9 import-check report"}
    report = common.read_json(import_check)
    if report.get("section") != IMPORT_CHECK_SECTION or "problems" not in report:
        return {"state": common.NOT_JUDGEABLE, "reason": f"{import_check} is no RV1-9 report"}
    return _state(not report["problems"], report["problems"])


def k0_identity(
    sidecar_paths: list[Path],
    git_at_start: str,
    output_paths: dict[str, Path],
    import_check: Path | None,
) -> dict:
    """D-21 (rev6 R6-C2 table) over the three sidecars and the three outputs."""
    sidecars = {str(p): identity_rows(common.read_json(p), git_at_start) for p in sidecar_paths}
    compared = [s.get("compared") for s in sidecars.values() if s.get("compared")]
    same = len(compared) == len(sidecar_paths) and all(c == compared[0] for c in compared[1:])
    header = header_identity_row(output_paths, c2_sha256_at(git_at_start))
    forbidden = forbidden_env_row(import_check)
    states = [s["state"] for s in sidecars.values()] + [header["state"], forbidden["state"]]
    if not same or header["state"] == "fail":
        state = "H-T3-3"
    elif "fail" in states:
        state = "H-T3-0"
    elif common.NOT_JUDGEABLE in states:
        state = common.NOT_JUDGEABLE
    else:
        state = "pass"
    return {
        "state": state,
        "sidecars": sidecars,
        "three_sidecars_same": same,
        "controller_tool_sha_from_headers": header,
        "forbidden_env_RV1_9": forbidden,
    }


# --------------------------------------------------------------------------------------- main
def judge(args: argparse.Namespace) -> dict:
    limits = install_allowance()
    keys_path = args.keys or las_t3.KEYS_PATH
    r0k_keys_path = args.r0k_keys or las_t3.R0K_KEYS_PATH
    try:
        result = base._judge_t3_rev5(
            args.r0,
            args.r0k,
            args.t3,
            keys_path,  # noqa: SLF001
            r0k_keys_path,
            args.baseline,
            args.las_rules_dir,
        )
    except (OSError, KeyError, ValueError) as exc:
        raise common.InputError(repr(exc)) from exc
    entries = las_t3.bundle_entries(las_t3.load_key_list(keys_path))
    outputs = {"R-0": args.r0, "R-0K": args.r0k, "T-3": args.t3}
    identity = k0_identity(list(args.identity), args.git_at_start, outputs, args.import_check)
    folders = dg3_folders(base.read_jsonl(args.t3)[1], entries)
    findings = [f"stop {stop}" for stop in result["stops"]]
    if identity["state"] != "pass":
        findings.append(f"K-0 identity (R6-C2): {identity['state']}")
    if any(not row["same"] for row in folders):
        findings.append("Dg-3 key-list folder differs from the recorded rule (K-3)")
    return {
        "t3_result": result,
        "K-0_identity_R6C2": identity,
        "dg3_folders": folders,
        "K-6_limits": limits,
        "findings": findings,
        "note": "base K-0 header-identity check stays inside t3_result (record)",
    }


def parser() -> argparse.ArgumentParser:
    out = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    common.add_common_arguments(out)
    out.add_argument("--r0", type=Path, required=True)
    out.add_argument("--r0k", type=Path, required=True)
    out.add_argument("--t3", type=Path, required=True)
    out.add_argument("--baseline", type=Path, required=True, help="stored v5/d1.jsonl")
    out.add_argument(
        "--identity",
        type=Path,
        action="append",
        required=True,
        help=".identity.json of R-0, R-0K and T-3K (three times)",
    )
    out.add_argument("--git-at-start", required=True)
    out.add_argument(
        "--import-check",
        type=Path,
        default=None,
        help="resume4368_judge import-check report (rev1 RV1-9; none = forbidden env 판정 불가)",
    )
    out.add_argument("--keys", type=Path, default=None)
    out.add_argument("--r0k-keys", type=Path, default=None)
    out.add_argument("--las-rules-dir", type=Path, default=las_t3.RULES_DIR)
    return out


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return common.run_judge(
        judge,
        args,
        script=Path(__file__).resolve(),
        old_tools=(HERE / "las_t3_judge.py", HERE / "las_h7.py"),
        changes=DEFINITION_CHANGES,
    )


if __name__ == "__main__":
    sys.exit(main())
