"""436.8 path 1 judge of T-3K (H-0), new version (rules rev5 R5-A1; ``las_targeted_rules_rev5``).

The verdict code is ``las_t3_judge._judge_t3_rev5`` (K-0 .. K-7, H-T3-0 .. H-T3-6) with three
definitions replaced (rev5 R5-A3):

  D-20  Dg-3 folder (off / v4_on) from the line's recorded ``two_pressure.extend_start_rule``
        (``tracked_bound`` = v4_on), not from the key-list entry (rev3 R3-D1). The key-list
        folder is still compared with the record (K-3) and listed in ``dg3_folders``.
  D-21  K-0 identity from the ``.identity.json`` sidecars (rev4 R4-C4 table): ``head`` start =
        end = ``git_at_start``; clean tree; code diff, ``c2.py`` and tool sha256 start = end
        (c2 also = ``git_at_start``'s); thread variables 1 and ``MKL_THREADING_LAYER`` TBB;
        no ``OUTRIGGER_LOC_SHADOW``; the R-0 / R-0K / T-3K values equal (else H-T3-3). A field
        not in the sidecar is ``판정 불가`` unless G-S confirms a counterpart (listed as a
        candidate, never accepted here).
  D-22  K-6 READY +5.0 s and stroke +0.001 m are compared with the rules 7.6 allowance 1e-9
        (``(X, X + 1e-9]`` is not a violation, rev3 R3-D4).

Usage (dynamics-dev or python-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/las_t3_judge_4368.py --out <report.json>
      --r0 <R-0 jsonl> --r0k <R-0K jsonl> --t3 <T-3K jsonl> --baseline <v5/d1.jsonl>
      --identity <R-0 .identity.json> --identity <R-0K ...> --identity <T-3K ...>
      --git-at-start <commit> [--keys <key list>] [--r0k-keys <R-0K key list>]
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
FORBIDDEN_ENV = "OUTRIGGER_LOC_SHADOW"
SIDECAR_FIELDS = {
    "head": ("head", "git.head"),
    "is_clean": ("is_clean", "git.is_clean"),
    "status_porcelain": ("status_porcelain", "git.status_porcelain"),
    "code_diff_sha256": ("code_diff_sha256",),
    "c2_sha256": ("c2_sha256",),
    "tools_sha256": ("tools_sha256",),
    "env": ("env", "threads"),
}
"""Rev4 R4-C4 field -> the dotted names accepted in a sidecar record (the d8x ``run_identity``
writes ``git.*`` and ``threads``; the same values, rev4 table)."""


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


def sidecar_value(record: dict, field: str) -> tuple[str | None, Any]:
    for name in SIDECAR_FIELDS[field]:
        found, value = _dotted(record, name)
        if found:
            return name, value
    return None, None


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


def identity_rows(sidecar: dict, git_at_start: str, c2_at_start: str | None) -> dict:
    """Rev4 R4-C4 rows of one sidecar: ``pass`` / ``fail`` / ``판정 불가`` with the evidence."""
    start, end = _moment(sidecar, "start"), _moment(sidecar, "end")
    if start is None or end is None:
        return {"state": "판정 불가", "rows": {}, "reason": "start or end record missing"}
    rows = {}
    values = {}
    for field in SIDECAR_FIELDS:
        names = (sidecar_value(start, field), sidecar_value(end, field))
        values[field] = (names[0][1], names[1][1])
        if names[0][0] is None:
            rows[field] = {"state": "판정 불가", "reason": "field not in the sidecar"}
    head = values["head"]
    if "head" not in rows:
        rows["head"] = _state(head[0] == head[1] and str(head[0]).startswith(git_at_start), head)
    if "is_clean" not in rows:
        rows["is_clean"] = _state(
            values["is_clean"][0] is True,
            values["status_porcelain"][0],
            note="dirty files allowed only when the pre-run audit says so",
        )
    for field in ("code_diff_sha256", "tools_sha256"):
        if field not in rows:
            rows[field] = _state(values[field][0] == values[field][1], values[field])
    if "c2_sha256" not in rows:
        c2 = values["c2_sha256"]
        rows["c2_sha256"] = _state(c2[0] == c2[1] == c2_at_start, [*c2, c2_at_start])
    if "env" not in rows:
        env = values["env"][0] or {}
        is_ok = (
            all(str(env.get(name)) == "1" for name in ONE_THREAD_VARIABLES)
            and env.get("MKL_THREADING_LAYER") == THREAD_LAYER
        )
        rows["env"] = _state(is_ok, env)
        rows["forbidden_env"] = (
            {"state": "판정 불가", "reason": f"{FORBIDDEN_ENV} not recorded"}
            if FORBIDDEN_ENV not in env
            else _state(not env.get(FORBIDDEN_ENV), env.get(FORBIDDEN_ENV))
        )
    states = {row["state"] for row in rows.values()}
    state = "fail" if "fail" in states else ("판정 불가" if "판정 불가" in states else "pass")
    return {
        "state": state,
        "rows": rows,
        "compared": {
            k: values[k][0]
            for k in ("head", "code_diff_sha256", "c2_sha256", "tools_sha256", "env")
        },
    }


def _state(is_ok: bool, evidence: Any, note: str | None = None) -> dict:
    out = {"state": "pass" if is_ok else "fail", "evidence": evidence}
    if note:
        out["note"] = note
    return out


def k0_identity(paths: list[Path], git_at_start: str, header_identities: dict) -> dict:
    """D-21 over the three sidecars, with the output-header identities as G-S candidates."""
    c2_at_start = c2_sha256_at(git_at_start)
    sidecars = {
        str(p): identity_rows(common.read_json(p), git_at_start, c2_at_start) for p in paths
    }
    compared = [s.get("compared") for s in sidecars.values() if s.get("compared")]
    same = all(c == compared[0] for c in compared[1:]) if compared else False
    states = [s["state"] for s in sidecars.values()]
    state = (
        "H-T3-3"
        if not same
        else "H-T3-0"
        if "fail" in states
        else "판정 불가"
        if "판정 불가" in states
        else "pass"
    )
    return {
        "state": state,
        "sidecars": sidecars,
        "three_outputs_same": same,
        "c2_sha256_at_git_at_start": c2_at_start,
        "gs_candidates_from_headers": header_identities,
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
    headers = {
        label: (base.read_jsonl(path)[0] or {}).get("identity")
        for label, path in (("R-0", args.r0), ("R-0K", args.r0k), ("T-3", args.t3))
    }
    identity = k0_identity(list(args.identity), args.git_at_start, headers)
    folders = dg3_folders(base.read_jsonl(args.t3)[1], entries)
    findings = [f"stop {stop}" for stop in result["stops"]]
    if identity["state"] != "pass":
        findings.append(f"K-0 identity (R4-C4): {identity['state']}")
    if any(not row["same"] for row in folders):
        findings.append("Dg-3 key-list folder differs from the recorded rule (K-3)")
    return {
        "t3_result": result,
        "K-0_identity_R4C4": identity,
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
