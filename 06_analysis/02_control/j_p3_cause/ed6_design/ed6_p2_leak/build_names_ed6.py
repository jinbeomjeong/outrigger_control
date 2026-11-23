"""Path-1 name dictionary for the handoff_leak check of the edition 6 path-2 handoff (read-only).

Made by verif-protocol-auditor (pre-seal audit of jp3_remedy_spec_v6.md revision 12), after
``ed5_design/e8_p2_leak/build_names.py``. Sources, all read from the worktree ``ed6-impl`` at
HEAD ac3c25a7 (no file there is written):

* whole modules parsed with ``ast`` (function and class names, module-level assignment names,
  identifier-like string literals, argparse sub-command names):
  ``03_src/outrigger_sim/control/lock_start_b.py`` and ``04_scripts/04_hydraulic/coupled/
  {ed6_probe, ed6_probe_share, jp3_12b_ppred, ed6_key_lists, jp3_12b_plan, d0_plant_split}.py``;
* edition 6 additions only (lines added between bdb1a510 and ac3c25a7, ``git diff -U0``):
  ``c2.py`` (functions / classes whose ``def`` line was added, string literals and assignment
  names on added lines) and ``run_v5.py`` (assignment names and string literals on added lines);
* the edition 5 dictionary ``ed5_design/e8_p2_leak/p1_names_e8.json``;
* hand-listed edition 6 names: tool file names and stems, design / run folder names, analysis
  script and output names, commits, worktree, probe arm and probe setting labels.

Names already present in the sealed earlier path-2 handoffs (handoff 6 and its errata 1 / 8,
and the 4a-7 / 4a-8 / T-JR-12 handoffs) are shared rule vocabulary and are removed. Names of
length < 4 are dropped (handoff_leak minimum). Writes ``p1_names_ed6.json`` next to this file.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed6-impl")
J = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause")
BASE, HEAD = "bdb1a510", "ac3c25a7"
WHOLE = ["03_src/outrigger_sim/control/lock_start_b.py",
         *[f"04_scripts/04_hydraulic/coupled/{n}.py" for n in
           ("ed6_probe", "ed6_probe_share", "jp3_12b_ppred", "ed6_key_lists", "jp3_12b_plan",
            "d0_plant_split")]]
PARTIAL = ["03_src/outrigger_sim/control/c2.py", "04_scripts/04_hydraulic/coupled/run_v5.py"]
SHARED = ["jp3_rev6_p2_handoff_ed5.md", "jp3_rev6_p2_handoff_ed5_e1.md",
          "jp3_rev6_p2_handoff_ed5_e8.md", "jp3_rev5_p2_handoff_4a7.md",
          "jp3_rev5_p2_handoff_4a7e1.md", "jp3_rev5_p2_handoff_4a7e2.md",
          "jp3_rev5_p2_handoff_4a7e3.md", "jp3_rev5_p2_handoff_4a8.md",
          "jp3_rev5_p2_handoff_4a8e1.md", "jp3_rev5_p2_handoff_tjr12.md"]
ED5 = J / "ed5_design" / "e8_p2_leak" / "p1_names_e8.json"
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_\-]{3,}$")


def added_lines(rel: str) -> set[int]:
    out = subprocess.run(["git", "-C", str(WT), "diff", "-U0", BASE, HEAD, "--", rel],
                         capture_output=True, text=True, encoding="utf-8", check=True,
                         stdin=subprocess.DEVNULL).stdout
    lines: set[int] = set()
    for m in re.finditer(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", out, re.M):
        start, count = int(m.group(1)), int(m.group(2) or 1)
        lines.update(range(start, start + count))
    return lines


def collect(tree: ast.AST, keep_line=None) -> dict[str, set[str]]:
    got = {"functions": set(), "constants": set(), "strings": set(), "subcommands": set()}

    def ok(node) -> bool:
        return keep_line is None or getattr(node, "lineno", -1) in keep_line

    body = getattr(tree, "body", [])
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and ok(node):
            got["functions"].add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and ok(node) and (
                keep_line is not None or node in body):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    got["constants"].add(target.id)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and ok(node):
            if IDENT.match(node.value):
                got["strings"].add(node.value)
        elif isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "add_parser":
            if node.args and isinstance(node.args[0], ast.Constant) and ok(node):
                got["subcommands"].add(node.args[0].value)
    return got


def main() -> None:
    names: dict[str, set[str]] = {"functions": set(), "constants": set(), "strings": set(),
                                  "subcommands": set()}
    for rel in WHOLE:
        tree = ast.parse((WT / rel).read_text(encoding="utf-8"))
        for k, v in collect(tree).items():
            names[k] |= v
    for rel in PARTIAL:
        tree = ast.parse((WT / rel).read_text(encoding="utf-8"))
        for k, v in collect(tree, added_lines(rel)).items():
            names[k] |= v
    ed5 = json.loads(ED5.read_text(encoding="utf-8"))
    ed5_names = {n for v in ed5.values() if isinstance(v, list) for n in v}
    stems = [Path(r).stem for r in WHOLE] + ["c2", "run_v5", "lock_start_b"]
    files = {f"{s}.py" for s in stems} | set(stems) | {
        "verdict_runs.py", "v5_options.py", "harness_hydraulics.py", "check_open_delay.py",
        "ed6_check_runner.py", "test_ed6_harness.py", "test_ed6_lock_start_b.py",
        "test_ed6_prelock.py", "d0_split_check_runner.py", "test_d0_plant_split.py",
        "d0_plant_split_summary.py", "build_names_ed6.py", "run_12a_short.ps1",
        "s10_ai_witness", "s11_ai_table", "s20_aii_b", "s21_recheck_h6", "s30_b3",
        "s31_b3_recount", "s32_stiffwarn", "s40_sens_confirm", "s41_keys_review",
        "s50_grid_sample", "s70_12b_kallow", "s71_ppred_rev9", "h6_lock_start_fill",
        "h6_pump_share", "h6_review_report", "b3_early_window", "b3_r5_census",
        "b3_r14_followup", "b3_dynamics_report", "b3_twist_stiffness", "b3_protect_r12_alias",
        "ready_dips", "p1_probe_tables", "p2_stiffness_warn", "stiffwarn_census",
        "b1off_check", "p1_units", "p1_pred_a1a2b", "p1_summary", "stats_v6_summary",
        "ed6_probe_share.json", "ed6_probe.jsonl", "ed6_probe_a1a2b3", "a2_r12_mechanism",
        "j9fail_cause_analysis", "h1_p1_review_report", "d0_attribution_report",
        "p2_report_dynamics_j9main", "s50_grid_sample.csv"}
    folders = {"ed6_design", "stats_v6", "hydraulics_v6", "control_v6", "dynamics_v6",
               "probe_1bd405c8", "prelock_12a_755a15d8", "ed6_probe_a1", "ed6_probe_t4h",
               "b1off_check", "ed6_inputs", "ed6_p2_leak", "ed5_d0_390f88a9",
               "ed5_j9fail_606f8713", "ed5_p2_606f8713", "ed5_judgement_606f8713",
               "d0_plant_split_a1", "j9main_a1", "ed6-impl", "d0-split", "python-ed6", "12a_v2"}
    commits = {"d6ef3611", "01da2583", "ff995a89", "1bd405c8", "e8ddf04e", "95cae09d",
               "755a15d8", "ac3c25a7", "390f88a9", "bdb1a510", "3d17434b", "606f8713"}
    arms = {"a1a2b", "a1a2b3", "a1a2bh", "a1a2b1", "a1a2", "a1b", "a2b"}
    labels = {f"P6-{p}-{a}" for p in ("J", "c005", "c04", "v05", "v15")
              for a in (*arms, "a2", "b")}
    shared = "\n".join((J / name).read_text(encoding="utf-8") for name in SHARED)

    def keep(group: set[str]) -> list[str]:
        out = []
        for n in sorted(group):
            if len(n) < 4:
                continue
            if re.search(rf"(?<![A-Za-z0-9_\-]){re.escape(n)}(?![A-Za-z0-9_\-])", shared):
                continue
            out.append(n)
        return out

    data = {"source": f"ed6-impl {HEAD} ast (whole: {', '.join(WHOLE)}; added lines {BASE}.."
                      f"{HEAD}: {', '.join(PARTIAL)}) + p1_names_e8.json + hand-listed edition 6 "
                      f"names; minus names in {', '.join(SHARED)}",
            "functions": keep(names["functions"]), "constants": keep(names["constants"]),
            "subcommands": keep(names["subcommands"]), "outputs": keep(names["strings"]),
            "files": keep(files), "folders": keep(folders), "commits": keep(commits),
            "probe_labels": keep(arms | labels), "ed5_dictionary": keep(ed5_names)}
    (HERE / "p1_names_ed6.json").write_text(json.dumps(data, indent=1, ensure_ascii=False)
                                            + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: len(v) for k, v in data.items() if isinstance(v, list)}))


if __name__ == "__main__":
    main()
