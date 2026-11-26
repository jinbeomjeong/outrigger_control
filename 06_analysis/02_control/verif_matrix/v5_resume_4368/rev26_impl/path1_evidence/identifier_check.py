"""Identifier-only equivalence check of the rev26 path 1 changes (no judgement run, no data).

1. AST facts of ``u6_line_check`` (R26-3) and ``ind_las_record_words`` (R26-2): which string
   constants / attributes / called names they use; no suffix-cutting call.
2. Every ``mode_tag`` call site and every 4.1 tag constant compared outside ``mode_tag``.
3. Truth table: the R26-3 function against a literal transcription of the rule sentence over a
   synthetic (controller, tag) domain, in both tag modes.
4. The R26-2 function against a literal transcription of the 1.2 table over a synthetic domain.
5. Every ``ROOT`` / ``Path.cwd`` / ``default=`` path site in the path 1 files (input basis table).

Usage: python -I -B identifier_check.py <worktree> <out.json>
"""

import ast
import itertools
import json
import sys
from pathlib import Path

CUT_CALLS = {"removesuffix", "removeprefix", "rstrip", "lstrip", "strip", "endswith",
             "startswith", "split", "rsplit", "replace", "partition", "rpartition",
             "is_extend_start_tag", "switch_base_tag", "fullmatch", "match", "search", "sub"}
PATH1_FILES = (
    "04_scripts/04_hydraulic/coupled/judge_stage1_4368.py",
    "04_scripts/04_hydraulic/coupled/judge4368_common.py",
    "04_scripts/04_hydraulic/coupled/u3_judge_4368.py",
    "04_scripts/04_hydraulic/coupled/h8_noise_judge_4368.py",
    "04_scripts/04_hydraulic/coupled/h6_judge_4368.py",
    "06_analysis/02_control/verif_matrix/scripts/resume4368_judge.py",
)
TAG_NAMES = {"TAG_V0", "TAG_P3", "TAG_ABL", "TAG_C4_OFF_V0", "TAG_C4_OFF_VB", "T3_ALL_OFF_TAG"}


def function_facts(tree: ast.Module, name: str) -> dict:
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    strings, names, attributes, calls = set(), set(), set(), set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and sub is not \
                node.body[0].value:
            strings.add(sub.value)
        elif isinstance(sub, ast.Name):
            names.add(sub.id)
        elif isinstance(sub, ast.Attribute):
            attributes.add(sub.attr)
        if isinstance(sub, ast.Call):
            func = sub.func
            calls.add(func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "?"))
    return {"strings": sorted(strings), "names": sorted(names),
            "attributes": sorted(attributes), "calls": sorted(calls),
            "suffix_cutting_calls": sorted(calls & CUT_CALLS)}


def tag_sites(tree: ast.Module) -> dict:
    """mode_tag call sites (enclosing function) and 4.1 tag names used outside mode_tag."""
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node

    def enclosing(node):
        while node in parents:
            node = parents[node]
            if isinstance(node, ast.FunctionDef):
                return node.name
        return "<module>"

    mode_calls, bare = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "mode_tag":
            mode_calls.append(f"{enclosing(node)}:{node.lineno}")
        if isinstance(node, ast.Name) and node.id in TAG_NAMES and isinstance(node.ctx, ast.Load):
            parent = parents.get(node)
            inside_mode = isinstance(parent, ast.Call) and getattr(parent.func, "id", "") == \
                "mode_tag"
            if not inside_mode:
                bare.append(f"{node.id} in {enclosing(node)}:{node.lineno}")
    return {"mode_tag_calls": mode_calls, "tag_names_not_in_mode_tag": bare}


def rule_r26_3(line: dict, imua: bool) -> bool:
    """Rev26 R26-3 sentence, transcribed: both fields there, controller one of four, tag equal."""
    table = {"C2": "final_C4G2_P3_LAS_K1", "ABL": "ABL_LAS_K1", "IND": "IND",
             "IND_LAS": "IND_LAS"}
    if "controller" not in line or not isinstance(line.get("v5"), dict) \
            or "controller_tag" not in line["v5"]:
        return False
    if line["controller"] not in table:
        return False
    return line["v5"]["controller_tag"] == table[line["controller"]] + ("_IMUA" if imua else "")


def rule_r26_2(fields: dict) -> list:
    out = []
    if fields.get("adapter_defect") is True:
        out.append("IND_LAS:adapter_defect")
    n = fields.get("gate_unreadable")
    if type(n) is int and n > 0:
        out.append(f"IND_LAS:판독 불가 {n}")
    keys_ok = (type(fields.get("record_state")) is str and type(fields.get("adapter_defect")) is bool
               and type(fields.get("gate_unreadable")) is int)
    if not keys_ok or fields["record_state"] != "기록":
        out.append("IND_LAS:기록 상태 미정")
    return out


def truth_tables(judge) -> dict:
    controllers = ["C2", "ABL", "IND", "IND_LAS", "C2_K1", "", None, ...]
    tags = ["final_C4G2_P3_LAS_K1", "ABL_LAS_K1", "IND", "IND_LAS", "final_C4G2_LAS_K1",
            "final_C4G2_P3_LAS_K1_IMUA", "ABL_LAS_K1_IMUA", "IND_IMUA", "IND_LAS_IMUA",
            "final_C4G2_P3", "final_C4G2_P3_LAS_K1_TCL", None, ...]
    rows, differ = 0, []
    for imua in (False, True):
        judge.set_tag_mode("imua" if imua else "4368")
        for controller, tag in itertools.product(controllers, tags):
            line = {"case": "x"}
            if controller is not ...:
                line["controller"] = controller
            if tag is not ...:
                line["v5"] = {"controller_tag": tag}
            passed = judge.u6_line_check(line)[1] == []
            rows += 1
            if passed != rule_r26_3(line, imua):
                differ.append([imua, repr(controller), repr(tag)])
    judge.set_tag_mode("4368")
    r2_rows, r2_differ = 0, []
    values = {"record_state": ["기록", "기록 불완전", None, ...],
              "adapter_defect": [True, False, "true", ...],
              "gate_unreadable": [0, 1, 3, -1, True, None, "2", ...]}
    for combo in itertools.product(*values.values()):
        fields = {k: v for k, v in zip(values, combo) if v is not ...}
        got = judge.ind_las_record_words(fields)
        want = rule_r26_2(fields)
        word = "기록 불완전" if want else "기록 완료"
        r2_rows += 1
        if got != {"state": word, "status": word, "markers": want}:
            r2_differ.append(repr(fields))
    return {"R26-3": {"rows": rows, "differ": differ},
            "R26-2": {"rows": r2_rows, "differ": r2_differ}}


def path_sites(worktree: Path) -> dict:
    out = {}
    for rel in PATH1_FILES:
        text = (worktree / rel).read_text(encoding="utf-8")
        hits = []
        for number, line in enumerate(text.splitlines(), start=1):
            if ("default=ROOT" in line or "ROOT /" in line or "Path.cwd" in line
                    or "default=RULES_DIR" in line):
                hits.append(f"{number}: {line.strip()[:110]}")
        out[rel] = hits
    return out


def main() -> int:
    worktree, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    judge_path = worktree / PATH1_FILES[5]
    tree = ast.parse(judge_path.read_text(encoding="utf-8"))
    for folder in ("03_src", "04_scripts/04_hydraulic/coupled", str(judge_path.parent)):
        sys.path.insert(0, str(worktree / folder))
    import resume4368_judge as judge  # noqa: PLC0415

    report = {
        "u6_line_check": function_facts(tree, "u6_line_check"),
        "ind_las_record_words": function_facts(tree, "ind_las_record_words"),
        "tag_sites": tag_sites(tree),
        "truth_tables": truth_tables(judge),
        "U6_CONTROLLER_TAGS": judge.U6_CONTROLLER_TAGS,
        "U6_TAG_PATH": judge.U6_TAG_PATH,
        "path_sites": path_sites(worktree),
    }
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    tables = report["truth_tables"]
    print(json.dumps({"r26_3_rows": tables["R26-3"]["rows"],
                      "r26_3_differ": len(tables["R26-3"]["differ"]),
                      "r26_2_rows": tables["R26-2"]["rows"],
                      "r26_2_differ": len(tables["R26-2"]["differ"]),
                      "suffix_cutting_calls": report["u6_line_check"]["suffix_cutting_calls"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
