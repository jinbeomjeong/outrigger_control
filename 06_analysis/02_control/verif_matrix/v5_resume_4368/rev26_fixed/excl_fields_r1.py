"""rev26 (d)/(c) excluded fields, revision 1 (verif audit B-2, W-2, W-7): narrow RD-5 rules on tokenised paths.

Normative rule (the same function is applied to the original and to the new output of each file):
  * Paths are JSON arrays of tokens: dict keys as strings (dots inside a key are kept), ``"[]"`` for every element
    of a list, ``"{*}"`` for every key of a dict that has more than 40 keys IN THE ORIGINAL OUTPUT (row-id maps;
    the decision is taken on the original and reused for the new output).
  * S (seal blocks of the judge run, RD-5 "봉인 블록"): a TOP-LEVEL key of the output named ``rules_seal``,
    ``seals``, ``rules_sha256``, ``rules_rev*_sha256``, ``rules_rev13_to_rev25_sha256``, ``rules_revisions``,
    ``seals_ok``, ``seals_eol_only``, ``rules_match_seal``, ``rules_sealed_sha256`` -> the whole subtree (deeper keys
    of the same names belong to the input records, e.g. sidecar seal checks, and stay compared).
  * S (tool strings and tool sha, RD-5 "도구 판·규칙 설명 문자열, 도구 sha"): key named ``tool``, ``tool_sha256``,
    ``script``, ``script_sha256``, ``version``, ``new_version``, ``old_tool``, ``existing_tool``, ``judge_tool``,
    ``meta_script`` -> only when the value is a scalar or a path/sha block (below).
  * S (input path / sha blocks, RD-5): a dict or list whose every leaf is a string that is a file path or a 40/64-hex
    digest, under a key named ``files``, ``inputs``, ``paths``, ``files_sha256``, ``inputs_sha256``,
    ``input_sha256`` or ``input_files`` -> excluded. Digests of judgement lists (``RD-7_sha256``, ``RD-13_sha256``,
    ``list_sha256``, ``r4_rev13_25_sha256`` ...) stay compared.
  * F (free-text reasons, RD-5): key named ``problems``, ``why``, ``note``, ``notes``, ``times_note``, ``reason``,
    ``reasons``, ``message``, ``messages``, ``detail``, ``details``, ``description``, ``comment``, ``comments`` ->
    only when the value is a string, null, or a list of strings. The ``compare_r4.py`` C16 list (437-455) applies
    the same way, only inside ``x16_records.json`` and ``c16.json``.
  * I (identity of THIS judge run, RD-5): a scalar string leaf whose value holds the tool commit (``--commit``,
    short or full), the run output folder token (``--out-token``), or an ISO date-time inside the run window of its
    folder (``--window <folder>=<start>/<end>``); key names ``created``, ``generated``, ``started``, ``finished``,
    ``timestamp``, ``stamp``, ``updated_at``, ``run_at``, ``created_at``, ``generated_at``, ``started_at``,
    ``finished_at`` with a scalar value.
  * I (argument lists, RD-5 "그 원소만"): inside lists or strings under keys ``argv``, ``args``, ``cmd``,
    ``command``, ``commands_run``: only the ELEMENTS that hold the output folder token or are a tool script path
    (ending ``.py`` / ``.ps1``), as ``[..., "argv", <index>]`` (index tokens are written ``"#<i>"``); a ``cmd`` /
    ``command`` scalar string is excluded only when it holds the output folder token.
  * Physical times, verdict values and every structured node not matched above stay compared.
Scope groups: ``d`` = every file except path 2 ``u3.json``, path 1 ``ind_las.json``, path 1 ``head_check.json``
(both folders) and the path 2 ``harness.json`` subtrees ``bundles.H-3``, ``head_check``, ``v5_options``;
``c`` = path 1 ``ind_las.json``. No value is printed.

Usage: python -I -B -X utf8 excl_fields_r1.py <out.json> --root <judge dir> --commit 932f1fb1724f074e4ee93a9c02193c7c840d13c4
         --out-token judge_932f1fb --window harness_path1=2026-11-16T16:29:00/2026-11-16T16:30:30 ...
Exit 0 written, 2 input error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path

DIRS = ("harness_path1", "harness_path1_retry1", "harness_path2")
SKIP_D_FILES = {("harness_path2", "u3.json"), ("harness_path1", "ind_las.json"),
                ("harness_path1", "head_check.json"), ("harness_path1_retry1", "head_check.json")}
SKIP_D_SUBTREES = {("harness_path2", "harness.json"): (("bundles", "H-3"), ("head_check",), ("v5_options",))}
C_FILES = {("harness_path1", "ind_las.json")}
C16_FILES = {"x16_records.json", "c16.json"}
WIDE = 40
SEAL_NAMES = {"rules_seal", "seals", "rules_sha256", "rules_rev13_to_rev25_sha256", "rules_revisions", "seals_ok",
              "seals_eol_only", "rules_match_seal", "rules_sealed_sha256"}
SEAL_RE = re.compile(r"^rules_rev\d+_sha256$")
TOOL_NAMES = {"tool", "tool_sha256", "script", "script_sha256", "version", "new_version", "old_tool",
              "existing_tool", "judge_tool", "meta_script"}
F_NAMES = {"problems", "why", "note", "notes", "times_note", "reason", "reasons", "message", "messages", "detail",
           "details", "description", "comment", "comments"}
C16_NAMES = {"problems", "why", "note", "times_note", "G6_rule", "G6_source", "rc_source", "files", "files_sha256",
             "folder", "identity (detail)", "duration_expected_s", "window", "dt_s", "file_sha256", "out_root",
             "identity_dir"}
TIME_NAMES = {"created", "generated", "started", "finished", "timestamp", "stamp", "updated_at", "run_at",
              "created_at", "generated_at", "started_at", "finished_at"}
ARG_NAMES = {"argv", "args", "cmd", "command", "commands_run"}
INPUT_BLOCK_NAMES = {"files", "inputs", "paths", "files_sha256", "inputs_sha256", "input_sha256", "input_files"}
"""Input path / sha blocks (RD-5). Digests of judgement lists (``RD-7_sha256``, ``RD-13_sha256``, ``list_sha256``
...) are verdict-derived and stay compared."""
ISO = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?")
HEX = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
PATHLIKE = re.compile(r"[\\/]|\.(json|jsonl|npz|md|py|ps1|txt|csv|sha256)$")


def leaves(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from leaves(v)
    elif isinstance(o, list):
        for v in o:
            yield from leaves(v)
    else:
        yield o


def is_path_sha_block(o) -> bool:
    if not isinstance(o, (dict, list)):
        return False
    vals = list(leaves(o))
    return bool(vals) and all(isinstance(v, str) and (HEX.match(v) or PATHLIKE.search(v)) for v in vals)


def is_scalar(o) -> bool:
    return not isinstance(o, (dict, list))


class Rules:
    def __init__(self, commit: str, out_token: str, windows: dict[str, tuple[dt.datetime, dt.datetime]]):
        self.commit_tokens = {commit, commit[:7], commit[:8], commit[:12]}
        self.out_token = out_token
        self.windows = windows

    def iso_in_window(self, folder: str, s: str) -> bool:
        w = self.windows.get(folder)
        if w is None:
            return False
        for m in ISO.finditer(s):
            try:
                t = dt.datetime.fromisoformat(m.group(0).replace(" ", "T"))
            except ValueError:
                continue
            if t.tzinfo is not None:
                t = t.astimezone().replace(tzinfo=None)
            if w[0] <= t <= w[1]:
                return True
        return False

    def identity_value(self, folder: str, v) -> bool:
        if not isinstance(v, str):
            return False
        return (any(tok in v for tok in self.commit_tokens) or self.out_token in v
                or self.iso_in_window(folder, v))


def walk(o, path, acc, rules: Rules, folder: str, fname: str, skips):
    if any(tuple(path[:len(s)]) == s for s in skips):
        return
    if isinstance(o, dict):
        collapse = len(o) > WIDE
        for k, v in o.items():
            tok = "{*}" if collapse else str(k)
            p = path + [tok]
            if any(tuple(p[:len(s)]) == s for s in skips):
                continue
            if not collapse:
                cat = classify(str(k), v, rules, folder, fname, depth=len(path))
                if cat == "ARGS":
                    for i, el in enumerate(v if isinstance(v, list) else []):
                        if isinstance(el, str) and (rules.out_token in el or el.endswith((".py", ".ps1"))):
                            acc.add((tuple(p + [f"#{i}"]), "I"))
                    if isinstance(v, str) and rules.out_token in v:
                        acc.add((tuple(p), "I"))
                    continue
                if cat is not None:
                    acc.add((tuple(p), cat))
                    continue
            walk(v, p, acc, rules, folder, fname, skips)
    elif isinstance(o, list):
        for x in o:
            walk(x, path + ["[]"], acc, rules, folder, fname, skips)
    else:
        if rules.identity_value(folder, o):
            acc.add((tuple(path), "I"))


def classify(name: str, v, rules: Rules, folder: str, fname: str, depth: int = 0):
    if (name in SEAL_NAMES or SEAL_RE.match(name)) and depth == 0:
        return "S"
    if name in TOOL_NAMES and (is_scalar(v) or is_path_sha_block(v)):
        return "S"
    if name in INPUT_BLOCK_NAMES and is_path_sha_block(v):
        return "S"
    f_ok = v is None or isinstance(v, str) or (isinstance(v, list) and all(isinstance(x, str) for x in v))
    if name in F_NAMES and f_ok:
        return "F"
    if fname in C16_FILES and name in C16_NAMES and (f_ok or is_scalar(v) or is_path_sha_block(v)):
        return "F"
    if name in ARG_NAMES:
        return "ARGS"
    if name in TIME_NAMES and is_scalar(v):
        return "I"
    if is_scalar(v) and rules.identity_value(folder, v):
        return "I"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--root", required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--out-token", required=True)
    ap.add_argument("--window", action="append", default=[])
    a = ap.parse_args()
    root = Path(a.root)
    if not root.is_dir():
        print(json.dumps({"status": "input_error", "detail": "root"}))
        return 2
    windows = {}
    for w in a.window:
        folder, span = w.split("=", 1)
        s, e = span.split("/", 1)
        windows[folder] = (dt.datetime.fromisoformat(s), dt.datetime.fromisoformat(e))
    rules = Rules(a.commit, a.out_token, windows)
    out = {"scope_d_skipped_files": sorted(f"{x}/{y}" for x, y in SKIP_D_FILES),
           "scope_d_skipped_subtrees": {f"{x}/{y}": [list(s) for s in v] for (x, y), v in SKIP_D_SUBTREES.items()},
           "scope_c_files": sorted(f"{x}/{y}" for x, y in C_FILES), "d": {}, "c": {}}
    counts = {"d": Counter(), "c": Counter()}
    for d in DIRS:
        for f in sorted((root / d).glob("*.json")):
            key = (d, f.name)
            data = json.load(open(f, encoding="utf-8"))
            for group in ("d", "c"):
                if group == "d" and key in SKIP_D_FILES:
                    continue
                if group == "c" and key not in C_FILES:
                    continue
                acc = set()
                walk(data, [], acc, rules, d, f.name, SKIP_D_SUBTREES.get(key, ()) if group == "d" else ())
                rows = sorted(acc)
                out[group][f"{d}/{f.name}"] = [[list(p), c] for p, c in rows]
                counts[group].update(c for _, c in rows)
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps({"status": "ok", "d_files": len(out["d"]), "d_paths": sum(len(v) for v in out["d"].values()),
                      "d_by_cat": dict(counts["d"]), "c_paths": sum(len(v) for v in out["c"].values()),
                      "c_by_cat": dict(counts["c"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
