"""Path-1 name dictionary for the handoff_leak check of the path-2 erratum 8 (read-only).

Source: the run-commit judge ``jp3_12b_judge.py`` (worktree ed5-run5) parsed with ``ast``:
function names, module constants, sub-command names, and every string literal used as a dict
key or compared/stored as a short identifier-like token. Plus the erratum 8 implementation
names (new judge-file keys, step and folder names) and the runner / tool file names.
Names already present in the sealed path-2 handoff 6 or its erratum 1 are the shared rule
vocabulary (record keys the judge reads, event, array and setting names) and are removed.
Writes ``p1_names_e8.json`` next to this script.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
JUDGE = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed5-run5\04_scripts"
             r"\04_hydraulic\coupled\jp3_12b_judge.py")
J = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause")
SHARED = [J / "jp3_rev6_p2_handoff_ed5.md", J / "jp3_rev6_p2_handoff_ed5_e1.md"]
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_\-]{3,}$")


def main() -> None:
    tree = ast.parse(JUDGE.read_text(encoding="utf-8"))
    functions, constants, strings, subcommands = set(), set(), set(), set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            functions.add(node.name)
        elif isinstance(node, ast.Assign) and node in tree.body:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    constants.add(target.id)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if IDENT.match(node.value):
                strings.add(node.value)
        elif isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "add_parser":
            if node.args and isinstance(node.args[0], ast.Constant):
                subcommands.add(node.args[0].value)
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            constants.add(node.target.id)
    erratum8 = {"ready_rule", "n_ready_loss", "n_ready_plus30", "n_vbk_worse", "allow_k",
                "blocks_used", "n_vbk0_worse", "n_vbk0_worse_loss", "n_vbk0_worse_plus30",
                "stall_signature_pairs", "stall_signature_vbk0_lines",
                "stall_signature_computed", "stall_signature_reasons", "by_cell", "by_block",
                "aa_floor", "n_fault_judged", "ready_outcome", "12b_decide_e8",
                "12b_vbk0_base", "12b_vbk0_base_a1", "step6c_vbk", "step6b_vbk0",
                "step8_j9main", "aa_floor_stop"}
    files = {"jp3_12b_judge.py", "jp3_12b_judge", "las_t3_dg3.py", "las_t3_dg3",
             "jp3_run_identity.py", "jp3_run_identity", "decision.json", "dry_c.json",
             "aa_fault_floor", "aa_inspect", "e8_review_check", "e8_rule_sim"}
    folders = {"aa_stop_606f8713", "stats_e8", "stats_e8_review", "cdry_a1", "run_steps_ed5",
               "prelaunch_j9", "ed5_design", "j9_runs"}
    # re-audit (audit_preseal_erratum8_ed5_reaudit.md 3): commits, step / folder / analysis
    # script names, judge internals, worktree, list and sub-command names, plus the new step
    # names of erratum 8 8-9 and the run-step helper names.
    reaudit = {"606f8713", "9460b2e0", "12b_vbk", "l2_floor", "aa_baserate", "aa_detail",
               "aa_stall", "aa_stall_twist", "aa_stall_lock", "aa_falsefail", "aa_inspect",
               "aa_fault_floor", "input_record", "classify_pair", "cmd_dry_c", "ed5-run5",
               "FIXED_INPUTS", "decide", "dry-c", "grade-judge", "l1-overlap",
               "12b_decide_e8_b4", "12b_vbk0_b4", "common_ed5", "Assert-FixedInputs",
               "Assert-RunCommit", "Invoke-Tool", "Initialize-Step", "e8_p2_leak"}
    shared = "\n".join(p.read_text(encoding="utf-8") for p in SHARED)

    def keep(names: set[str]) -> list[str]:
        out = []
        for n in sorted(names):
            if len(n) < 4:
                continue
            if re.search(rf"(?<![A-Za-z0-9_\-]){re.escape(n)}(?![A-Za-z0-9_\-])", shared):
                continue
            out.append(n)
        return out

    data = {"source": f"{JUDGE} (ast) + erratum 8 implementation names; minus names in "
                      "handoff 6 and its erratum 1",
            "functions": keep(functions), "constants": keep(constants),
            "subcommands": keep(subcommands), "outputs": keep(strings | erratum8),
            "files": keep(files), "folders": keep(folders), "reaudit": keep(reaudit)}
    (HERE / "p1_names_e8.json").write_text(json.dumps(data, indent=1, ensure_ascii=False),
                                           encoding="utf-8")
    print(json.dumps({k: len(v) for k, v in data.items() if isinstance(v, list)}))


if __name__ == "__main__":
    main()
