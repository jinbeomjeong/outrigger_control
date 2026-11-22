"""rev26 (d) excluded-field list of the 436.8 R4 judge outputs (RD-5 categories), by key name and value form.

Scope: every JSON output of judge_932f1fb/{harness_path1, harness_path1_retry1, harness_path2} except the rev26
targets (path 2 ``u3.json``, path 2 ``harness.json`` subtree ``bundles.H-3``, path 1 ``ind_las.json``).
A leaf is excluded when it falls in an RD-5 category:
  I  execution identity: the tool checkout commit (value holds the M4 commit 932f1fb), run time (ISO date-time
     value, or key name with time/stamp/started/finished/generated/created), output location (value holds
     ``judge_932f1fb`` / ``harness_path``), or a key named out/out_dir/out_root/output/cwd/argv/args/cmd/command
  S  seal / rule / tool strings and sha blocks: key name holding seal / rules_ / rule_sha / tool / script /
     judge_sha / sources / source_sha / version / python / interpreter / host
  F  free-text reason keys: problems, why, note(s), times_note, reason, message, detail, description, comment,
     and the C16 RD-5 / CD-10 list of compare_r4.py 437-455
Values are read only to test these forms; no value is printed. List indices are written ``[]``; dict levels with
more than 40 keys (row-id maps) are written ``{*}``. Output JSON: {file: [[path, category], ...]}, plus counts.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\judge_932f1fb")
DIRS = ("harness_path1", "harness_path1_retry1", "harness_path2")
SKIP_FILES = {("harness_path2", "u3.json"), ("harness_path1", "ind_las.json")}
SKIP_SUBTREE = {("harness_path2", "harness.json"): "bundles.H-3"}
ISO = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")
I_NAME = re.compile(r"^(out|out_dir|out_root|output|outputs|cwd|argv|args|cmd|command|commands_run|run_dir|"
                    r"created|created_at|generated|generated_at|started|started_at|finished|finished_at|"
                    r"timestamp|stamp|updated_at|run_at)$", re.I)
S_NAME = re.compile(r"seal|^rules_|rule_sha|rules_sha|tool|script|judge_sha|^sources?$|source_sha|version|"
                    r"python|interpreter|^host", re.I)
F_NAMES = {"problems", "why", "note", "notes", "times_note", "reason", "reasons", "message", "messages", "detail",
           "details", "description", "comment", "comments", "G6_rule", "G6_source", "rc_source", "files",
           "files_sha256", "folder", "identity (detail)", "duration_expected_s", "window", "dt_s",
           "file_sha256", "out_root", "identity_dir"}
WIDE = 40
TIME_EXCEPT = re.compile(r"^(t_|time_to_|.*_time_s$|.*_t_s$|t$)", re.I)  # physical times of the runs stay compared


def category(name: str, value) -> str | None:
    if name in F_NAMES:
        return "F"
    if S_NAME.search(name):
        return "S"
    if isinstance(value, str):
        if "932f1fb" in value:
            return "I"
        if "judge_932f1fb" in value or "harness_path" in value:
            return "I"
        if ISO.search(value):
            return "I"
    if I_NAME.search(name) and not TIME_EXCEPT.match(name):
        return "I"
    return None


def walk(o, path, acc, skip_prefix):
    if skip_prefix and (path == skip_prefix or path.startswith(skip_prefix + ".")):
        return
    if isinstance(o, dict):
        collapse = len(o) > WIDE
        for k, v in o.items():
            name = "{*}" if collapse else str(k)
            p = f"{path}.{name}" if path else name
            if skip_prefix and (p == skip_prefix or p.startswith(skip_prefix + ".")):
                continue
            cat = None if collapse else category(str(k), v if not isinstance(v, (dict, list)) else None)
            if cat is not None:
                acc.add((p, cat))
                continue  # the whole subtree is excluded with its key
            walk(v, p, acc, skip_prefix)
    elif isinstance(o, list):
        for x in o:
            walk(x, f"{path}[]", acc, skip_prefix)
    elif isinstance(o, str):
        cat = category(path.rsplit(".", 1)[-1].rstrip("[]"), o)
        if cat == "I" and ("932f1fb" in o or "judge_932f1fb" in o or "harness_path" in o or ISO.search(o)):
            acc.add((path, "I"))


out, counts, leaves = {}, Counter(), Counter()
for d in DIRS:
    for f in sorted((ROOT / d).glob("*.json")):
        if (d, f.name) in SKIP_FILES:
            continue
        data = json.load(open(f, encoding="utf-8"))
        acc = set()
        walk(data, "", acc, SKIP_SUBTREE.get((d, f.name)))
        rows = sorted(acc)
        out[f"{d}/{f.name}"] = [list(r) for r in rows]
        for p, c in rows:
            counts[c] += 1
            leaves[(p.rsplit(".", 1)[-1], c)] += 1
json.dump({"scope_skipped": sorted(f"{a}/{b}" for a, b in SKIP_FILES),
           "scope_skipped_subtrees": {f"{a}/{b}": s for (a, b), s in SKIP_SUBTREE.items()},
           "files": out}, open(sys.argv[1], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("files", len(out), "paths", sum(len(v) for v in out.values()), dict(counts))
for (leaf, c), n in sorted(leaves.items(), key=lambda x: (-x[1], x[0])):
    print(f"  {c} {leaf}: {n}")
