"""rev26 normative exclusion / normalisation rules for the (d) and (c) comparisons, revision 5.

Revision history: r1 (verif audit B-2: narrow RD-5 rules), r2 (re-audit N-1/N-2: tool-diff blocks, nested seal
copies, commit tokens in arguments, checkout-root normalisation), r3 (re-audit 2 W-f/W-g/W-h/N-3b: all-occurrence
root replacement, tool-location vs input roots, input path/sha blocks compared, argument lists compared as filtered
sequences, this docstring), r4 (re-audit 4 B-5: the input-base flag ``--data-root`` of the T26 path 2 tools and of
the path 1 ``resume_k1_family.py`` is an identity pair like ``--root``), r5 (re-audit 5 B-6: NT also covers the rev26
section 2 W data locations, files the tools read from their own checkout by design).

The same rules are applied by EACH SIDE to its own output files with its own arguments (tool commit, output-folder
token, run windows, checkout roots); each side removes its own excluded entries and normalises its own N entries;
the remainders must be equal.

Paths
  JSON arrays of tokens: dict keys as strings (dots inside a key stay in one token), ``"[]"`` for every element of a
  list, ``"{*}"`` for every key of a dict with more than 40 keys IN THE ORIGINAL OUTPUT (decided on the original and
  reused for the new output), ``"#<i>"`` for an element of an argument list (index of the original, informative).

Excluded categories
  S  seal blocks: a TOP-LEVEL key (in ``u3_judge.json`` also a key directly under ``G-3``) named ``rules_seal``,
     ``seals``, ``rules_sha256``, ``rules_rev<n>_sha256``, ``rules_rev13_to_rev25_sha256``, ``rules_revisions``,
     ``seals_ok``, ``seals_eol_only``, ``rules_match_seal``, ``rules_sealed_sha256`` -> whole subtree.
  S  tool-diff blocks: ``diff_vs_existing``, ``definition_changes`` (any depth, whole subtree); ``common_sha256`` (any
     depth); every ``*_sha256`` key directly under an ``imports`` dict.
  S  tool strings / tool sha: ``tool``, ``tool_sha256``, ``script``, ``script_sha256``, ``version``,
     ``new_version``, ``old_tool``, ``existing_tool``, ``judge_tool``, ``meta_script`` when the value is a scalar or a
     block whose every leaf is a path string or a 40/64-hex digest.
  F  free text: ``problems``, ``why``, ``note(s)``, ``times_note``, ``reason(s)``, ``message(s)``, ``detail(s)``,
     ``description``, ``comment(s)`` when the value is a string, null or a list of strings; the ``compare_r4.py``
     437-455 C16 names only inside ``x16_records.json`` / ``c16.json`` under the same condition (or a scalar).
  I  identity of this judge run: a scalar string leaf holding the tool commit (full, 7, 8, 12 characters), the run
     output-folder token, or an ISO date-time inside the run window of its folder; scalar values of keys
     ``created``, ``generated``, ``started``, ``finished``, ``timestamp``, ``stamp``, ``updated_at``, ``run_at``,
     ``created_at``, ``generated_at``, ``started_at``, ``finished_at``.
  I  argument lists (keys ``argv``, ``args``, ``cmd``, ``command``, ``commands_run``): the ELEMENTS that hold the
     output-folder token or the tool commit (e.g. the value of ``--expect-head``), tool script paths (``.py`` /
     ``.ps1``), the flags ``--root``, ``--data-root`` and ``--allowed-src-changes`` with their next element. The comparison removes
     these elements and compares the remaining SEQUENCE (positions after removal, not original indices). A scalar
     ``cmd`` / ``command`` string is excluded only when it holds the output-folder token or the tool commit.
  Input path / sha blocks are NOT excluded (re-audit 2 W-g): same inputs must give the same values.

Normalised categories (not excluded)
  NT  tool location: a string (leaf or argument element) holding a checkout root whose remainder after the root
      starts with a tool folder (``03_src``, ``04_scripts``, ``05_tests``,
      ``06_analysis/02_control/verif_matrix/scripts``, ``06_analysis/02_control/verif_matrix/v5_resume_4368/path2``,
      ``06_analysis/03_hydraulic/coupled/v5/paper_runs/scripts``) or with a W data location of rev26 section 2 (files
      read from the tool checkout by design): a rules file directly in ``06_analysis/02_control/verif_matrix/``
      (``*.md``, ``*.sha256``, no subfolder), ``06_analysis/03_hydraulic/coupled/v5/v5_criteria*.md``, ``02_params/``,
      ``06_analysis/00_dynamics/slope_crawler_settle.json``, ``06_analysis/00_dynamics/pad_bekker_p0_soilsets.json``,
      ``06_analysis/02_control/s8/rev76/``, ``06_analysis/02_control/s8/s8_rev52_cs836_scope.json``,
      ``06_analysis/02_control/s9/rev80/``, ``06_analysis/02_control/verif_matrix/v5_resume_4368/chrono_rows_manifest.json``.
      Every occurrence of EVERY checkout root (main checkout and the judge worktree) is replaced by ``<ROOT>``.
  NM  input / other location: any other string holding a checkout root. Every occurrence of the MAIN checkout root
      only is replaced by ``<ROOT>``; a judge-worktree root left in such a string is a mismatch (inputs must be read
      from the main checkout).
  Replacement: case-insensitive, both separator forms (``\\`` and ``/``), longest root first, all occurrences.

Scope groups
  ``d`` = every output file except path 2 ``u3.json``, path 1 ``ind_las.json``, path 1 ``head_check.json`` (both
  folders), and the path 2 ``harness.json`` subtrees ``bundles.H-3``, ``head_check``, ``v5_options``;
  ``c`` = path 1 ``ind_las.json``. No value is printed.

Usage (dynamics-dev or python-dev):
  python -I -B -X utf8 excl_fields_r5.py <out.json> --root <judge output dir> --commit <tool commit>
      --out-token <output-folder token> --window <folder>=<start>/<end> [...]
      --main-root <main checkout> [--checkout-root <judge worktree> ...]
Exit 0 written, 2 input error. Output JSON is LF.
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
TOOL_DIFF_NAMES = {"diff_vs_existing", "definition_changes"}
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
PAIR_FLAGS = {"--root", "--data-root", "--allowed-src-changes"}
TOOL_DIRS = ("03_src", "04_scripts", "05_tests", "06_analysis/02_control/verif_matrix/scripts",
             "06_analysis/02_control/verif_matrix/v5_resume_4368/path2",
             "06_analysis/03_hydraulic/coupled/v5/paper_runs/scripts")
W_DATA_PREFIXES = ("02_params/", "06_analysis/00_dynamics/slope_crawler_settle.json",
                   "06_analysis/00_dynamics/pad_bekker_p0_soilsets.json", "06_analysis/02_control/s8/rev76/",
                   "06_analysis/02_control/s8/s8_rev52_cs836_scope.json", "06_analysis/02_control/s9/rev80/",
                   "06_analysis/02_control/verif_matrix/v5_resume_4368/chrono_rows_manifest.json")
W_DATA_RE = re.compile(r"^(06_analysis/02_control/verif_matrix/[^/]+\.(md|sha256)"
                       r"|06_analysis/03_hydraulic/coupled/v5/v5_criteria[^/]*\.md)(?=$|[\s\"'`)\],;])")
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


def is_scalar(o) -> bool:
    return not isinstance(o, (dict, list))


def is_path_sha_block(o) -> bool:
    if is_scalar(o):
        return False
    vals = list(leaves(o))
    return bool(vals) and all(isinstance(v, str) and (HEX.match(v) or PATHLIKE.search(v)) for v in vals)


class Rules:
    def __init__(self, commit, out_token, windows, main_root, other_roots):
        self.commit_tokens = {commit, commit[:7], commit[:8], commit[:12]}
        self.out_token = out_token
        self.windows = windows
        self.roots = self._forms([main_root, *other_roots])

    @staticmethod
    def _forms(roots):
        forms = set()
        for r in roots:
            forms |= {r.lower().replace("/", "\\"), r.lower().replace("\\", "/")}
        return sorted(forms, key=len, reverse=True)

    def root_kind(self, v):
        """None, 'NT' (tool location) or 'NM' (other location) for a string holding a checkout root."""
        if not isinstance(v, str):
            return None
        low = v.lower()
        kind = None
        for r in self.roots:
            start = 0
            while True:
                i = low.find(r, start)
                if i < 0:
                    break
                rest = low[i + len(r):].lstrip("\\/").replace("\\", "/")
                if (any(rest.startswith(t) for t in TOOL_DIRS) or rest.startswith(W_DATA_PREFIXES)
                        or W_DATA_RE.match(rest)):
                    return "NT"
                kind = "NM"
                start = i + len(r)
        return kind

    def has_commit(self, v):
        return isinstance(v, str) and any(t in v for t in self.commit_tokens)

    def iso_in_window(self, folder, s):
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

    def identity_value(self, folder, v):
        return isinstance(v, str) and (self.has_commit(v) or self.out_token in v or self.iso_in_window(folder, v))


def classify(name, v, rules, folder, fname, path):
    depth = len(path)
    seal_scope = depth == 0 or (fname == "u3_judge.json" and path == ["G-3"])
    if (name in SEAL_NAMES or SEAL_RE.match(name)) and seal_scope:
        return "S"
    if name in TOOL_DIFF_NAMES:
        return "S"
    if name == "common_sha256" or (name.endswith("_sha256") and path[-1:] == ["imports"]):
        return "S"
    if name in TOOL_NAMES and (is_scalar(v) or is_path_sha_block(v)):
        return "S"
    f_ok = v is None or isinstance(v, str) or (isinstance(v, list) and all(isinstance(x, str) for x in v))
    if name in F_NAMES and f_ok:
        return "F"
    if fname in C16_FILES and name in C16_NAMES and (f_ok or is_scalar(v)):
        return "F"
    if name in ARG_NAMES:
        return "ARGS"
    if name in TIME_NAMES and is_scalar(v):
        return "I"
    if is_scalar(v) and rules.identity_value(folder, v):
        return "I"
    if is_scalar(v):
        return rules.root_kind(v)
    return None


def walk(o, path, acc, rules, folder, fname, skips):
    if isinstance(o, dict):
        collapse = len(o) > WIDE
        for k, v in o.items():
            p = path + ["{*}" if collapse else str(k)]
            if any(tuple(p[:len(s)]) == s for s in skips):
                continue
            if not collapse:
                cat = classify(str(k), v, rules, folder, fname, path)
                if cat == "ARGS":
                    args(v, p, acc, rules)
                    continue
                if cat is not None:
                    acc.add((tuple(p), cat))
                    continue
            walk(v, p, acc, rules, folder, fname, skips)
    elif isinstance(o, list):
        for x in o:
            walk(x, path + ["[]"], acc, rules, folder, fname, skips)
    elif rules.identity_value(folder, o):
        acc.add((tuple(path), "I"))
    else:
        kind = rules.root_kind(o)
        if kind:
            acc.add((tuple(path), kind))


def args(v, p, acc, rules):
    if isinstance(v, str):
        if rules.out_token in v or rules.has_commit(v):
            acc.add((tuple(p), "I"))
        elif rules.root_kind(v):
            acc.add((tuple(p), rules.root_kind(v)))
        return
    if not isinstance(v, list):
        return
    skip_next = False
    for i, el in enumerate(v):
        tok = tuple(p + [f"#{i}"])
        if skip_next:
            acc.add((tok, "I"))
            skip_next = False
            continue
        if not isinstance(el, str):
            continue
        if el in PAIR_FLAGS:
            acc.add((tok, "I"))
            skip_next = True
        elif rules.out_token in el or rules.has_commit(el) or el.endswith((".py", ".ps1")):
            acc.add((tok, "I"))
        elif rules.root_kind(el):
            acc.add((tok, rules.root_kind(el)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--root", required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--out-token", required=True)
    ap.add_argument("--window", action="append", default=[])
    ap.add_argument("--main-root", required=True)
    ap.add_argument("--checkout-root", action="append", default=[])
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
    rules = Rules(a.commit, a.out_token, windows, a.main_root, a.checkout_root)
    out = {"rules": "excl_fields_r5", "scope_d_skipped_files": sorted(f"{x}/{y}" for x, y in SKIP_D_FILES),
           "scope_d_skipped_subtrees": {f"{x}/{y}": [list(s) for s in v] for (x, y), v in SKIP_D_SUBTREES.items()},
           "scope_c_files": sorted(f"{x}/{y}" for x, y in C_FILES), "d": {}, "c": {}}
    counts = {"d": Counter(), "c": Counter()}
    for d in DIRS:
        for f in sorted((root / d).glob("*.json")):
            key = (d, f.name)
            data = json.load(open(f, encoding="utf-8"))
            for group in ("d", "c"):
                if (group == "d" and key in SKIP_D_FILES) or (group == "c" and key not in C_FILES):
                    continue
                acc = set()
                walk(data, [], acc, rules, d, f.name, SKIP_D_SUBTREES.get(key, ()) if group == "d" else ())
                rows = sorted(acc)
                out[group][f"{d}/{f.name}"] = [[list(p), c] for p, c in rows]
                counts[group].update(c for _, c in rows)
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps({"status": "ok", "d_files": len(out["d"]), "d_entries": sum(len(v) for v in out["d"].values()),
                      "d_by_cat": dict(counts["d"]), "c_entries": sum(len(v) for v in out["c"].values()),
                      "c_by_cat": dict(counts["c"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
