"""Synthetic test of excl_fields_r6 vs excl_fields_r5 (rev26 erratum 2, 4' audit B-1).

1. Build two synthetic judge roots A ("original") and B ("new run") of the rev26 folder form.
2. Run r5 and r6 on each root with that side's own arguments; the r6 list must equal the r5 list except the rules
   name and one added row harness_path2/p2v5c_merge.json [parts, [], sha256] I (checked with list_diff_r5_r6.py too).
3. Each side removes its own I/S/F rows and normalises NT/NM; compare the remainders: r5 must differ only at the
   three part digests, r6 must be equal.
4. Negative cases for list_diff_r5_r6.py.
"""
from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368")
R5 = FIX / "rev26_fixed" / "excl_fields_r5.py"
R6 = FIX / "rev26_e2_fixed" / "excl_fields_r6.py"
LD = FIX / "rev26_e2_fixed" / "list_diff_r5_r6.py"
PY = sys.executable

MAIN = r"C:\synthmain\outrigger_control"
WT = r"C:\synthmain\outrigger_control\.claude\worktrees\rev26-t26"
SIDES = {
    "A": {"commit": "a" * 40, "token": "judge_aaaaaaa", "roots": [],
          "time": "2026-11-16T14:00:00", "win": ("2026-11-16T13:00:00", "2026-11-16T17:00:00"),
          "tool_root": MAIN, "part_sha": ["1" * 64, "2" * 64, "3" * 64]},
    "B": {"commit": "b" * 40, "token": "judge_rev26_bbbbbbb", "roots": [WT],
          "time": "2026-11-27T10:30:00", "win": ("2026-11-27T10:00:00", "2026-11-27T11:00:00"),
          "tool_root": WT, "part_sha": ["4" * 64, "5" * 64, "6" * 64]},
}
SAME = "c" * 64


def build(side, root):
    s = SIDES[side]
    out = f"{MAIN}\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\{s['token']}"
    tool = f"{s['tool_root']}\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\path2_v5c"
    files = {}

    def part(name):
        return {"tool": name, "tool_sha256": s["commit"][:8] * 8, "common_sha256": "d" * 64, "created": s["time"],
                "head_check": {"head": s["commit"], "ok": True}, "seals": {"rev26": {"sha": "e" * 64}},
                "status": "pass", "stop_codes": [],
                "inputs": {"h8": {"path": "07_results/x/h8.json", "sha256": SAME}},
                "R4": {"RD-7": {"J-P3": {"H-9": ["k1", "k2"]}}, "value": 1.25}}

    for name in ("p2v5c_noise", "p2v5c_stage1", "p2v5c_grid"):
        files[f"harness_path2/{name}.json"] = part(f"{name}.py")
    files["harness_path2/p2v5c_merge.json"] = {
        "tool": "p2v5c_stage1.py", "tool_sha256": "9" * 64, "created": s["time"],
        "argv": [f"{tool}\\p2v5c_stage1.py", "--expect-head", s["commit"], "--out",
                 f"{out}\\harness_path2\\p2v5c_merge.json", "merge"],
        "parts": [{"path": f"{out}\\harness_path2\\{n}.json", "sha256": h, "tool": f"{n}.py", "status": "pass",
                   "stop_codes": [], "tool_sha256": "8" * 64, "head": s["commit"]}
                  for n, h in zip(("p2v5c_noise", "p2v5c_stage1", "p2v5c_grid"), s["part_sha"])],
        "R4": {"parts": [{"sha256": SAME}]},  # nested, not top-level: stays compared
        "RD-7_sha256": {"J-P3": {"H-9": SAME}},
        "status": "pass", "stop_codes": []}
    files["harness_path2/other.json"] = {"parts": [{"sha256": SAME}], "inputs": [{"path": f"{MAIN}\\07_results\\a.json",
                                                                                   "sha256": SAME}]}
    files["harness_path2/u3.json"] = {"x": 1}
    files["harness_path2/harness.json"] = {"head_check": {"head": s["commit"]}, "bundles": {"H-3": {}, "H-4": {"tags": ["t"]}},
                                           "v5_options": {"path": f"{s['tool_root']}\\03_src\\v5_options.py"}}
    files["harness_path1/p2v5c_merge.json"] = {"parts": [{"sha256": SAME}]}  # same name, other folder
    files["harness_path1/head_check.json"] = {"head": s["commit"]}
    files["harness_path1/ind_las.json"] = {"rules_seal": {"x": "e" * 64}, "record_state": "기록"}
    files["harness_path1/h2_select.json"] = {"rules": f"{s['tool_root']}\\06_analysis\\02_control\\verif_matrix\\x_rules.md",
                                            "rules_seal": {"a": 1}, "generated": s["time"]}
    files["harness_path1_retry1/head_check.json"] = {"head": s["commit"]}
    for rel, data in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")


def run_rules(script, side, root, out):
    s = SIDES[side]
    cmd = [PY, "-I", "-B", "-X", "utf8", str(script), str(out), "--root", str(root), "--commit", s["commit"],
           "--out-token", s["token"], "--main-root", MAIN]
    for d in ("harness_path1", "harness_path1_retry1", "harness_path2"):
        cmd += ["--window", f"{d}={s['win'][0]}/{s['win'][1]}"]
    for r in s["roots"]:
        cmd += ["--checkout-root", r]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def targets(o, toks):
    """(container, key) pairs addressed by a token path."""
    if not toks:
        return []
    t, rest = toks[0], toks[1:]
    if isinstance(o, list):
        keys = range(len(o)) if t == "[]" else ([int(t[1:])] if t.startswith("#") and int(t[1:]) < len(o) else [])
    elif isinstance(o, dict):
        keys = list(o) if t == "{*}" else ([t] if t in o else [])
    else:
        return []
    if not rest:
        return [(o, k) for k in keys]
    out = []
    for k in keys:
        out += targets(o[k], rest)
    return out


def root_re(roots):
    forms = set()
    for r in roots:
        forms |= {r.lower().replace("/", "\\"), r.lower().replace("\\", "/")}
    return [re.compile(re.escape(f), re.IGNORECASE) for f in sorted(forms, key=len, reverse=True)]


def apply(data, rows, side):
    data = copy.deepcopy(data)
    s = SIDES[side]
    nt, nm = root_re([MAIN, *s["roots"]]), root_re([MAIN])
    for toks, cat in rows:
        if cat in ("NT", "NM"):
            for c, k in targets(data, toks):
                v = c[k]
                for rx in (nt if cat == "NT" else nm):
                    v = rx.sub("<ROOT>", v)
                c[k] = v
    dels = {}
    for toks, cat in rows:
        if cat in ("I", "S", "F"):
            for c, k in targets(data, toks):
                dels.setdefault(id(c), (c, set()))[1].add(k)
    for c, ks in dels.values():
        for k in sorted(ks, reverse=True):
            del c[k]
    return data


def leaf_diff(a, b, path=()):
    if type(a) is not type(b):
        return [path]
    if isinstance(a, dict):
        out = [path + (k,) for k in set(a) ^ set(b)]
        for k in set(a) & set(b):
            out += leaf_diff(a[k], b[k], path + (k,))
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [path + ("len",)]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += leaf_diff(x, y, path + (i,))
        return out
    return [] if a == b else [path]


def remainders(rules_json, side, root):
    lst = json.loads(Path(rules_json).read_text("utf-8"))
    rem = {}
    for f in sorted((root).rglob("*.json")):
        rel = f.relative_to(root).as_posix()
        if rel not in lst["d"]:
            continue
        data = json.loads(f.read_text("utf-8"))
        if rel == "harness_path2/harness.json":
            for sub in (("bundles", "H-3"), ("head_check",), ("v5_options",)):
                c = data
                for t in sub[:-1]:
                    c = c[t]
                c.pop(sub[-1], None)
        rem[rel] = apply(data, [(p, c) for p, c in lst["d"][rel]], side)
    return rem


def main():
    res = {}
    roots = {}
    for side in SIDES:
        roots[side] = HERE / f"synth_{side}"
        build(side, roots[side])
        for tag, script in (("r5", R5), ("r6", R6)):
            out = HERE / f"list_{side}_{tag}.json"
            res[f"{side}_{tag}_stdout"] = run_rules(script, side, roots[side], out)
        rec = HERE / f"list_diff_{side}.json"
        p = subprocess.run([PY, "-I", "-B", "-X", "utf8", str(LD), str(HERE / f"list_{side}_r5.json"),
                            str(HERE / f"list_{side}_r6.json"), "--out", str(rec)],
                           capture_output=True, text=True, timeout=60)
        so = json.loads(p.stdout.strip().splitlines()[-1])
        raw = rec.read_bytes()
        res[f"{side}_list_diff"] = {"rc": p.returncode, "out": so,
                                    "out_file_equal_stdout": json.loads(raw) == so and b"\r" not in raw}
    for tag in ("r5", "r6"):
        ra = remainders(HERE / f"list_A_{tag}.json", "A", roots["A"])
        rb = remainders(HERE / f"list_B_{tag}.json", "B", roots["B"])
        diffs = {f: [list(map(str, d)) for d in leaf_diff(ra.get(f), rb.get(f))] for f in sorted(set(ra) | set(rb))}
        res[f"e2e_{tag}"] = {f: d for f, d in diffs.items() if d}
        res[f"e2e_{tag}_files"] = len(diffs)
    # negative cases for list_diff_r5_r6.py
    base = json.loads((HERE / "list_A_r6.json").read_text("utf-8"))
    neg = {}
    cases = {}
    c1 = json.loads((HERE / "list_A_r5.json").read_text("utf-8"))
    c1["rules"] = "excl_fields_r6"
    cases["no_added_row"] = c1
    c2 = copy.deepcopy(base)
    c2["d"]["harness_path2/other.json"].append([["parts", "[]", "sha256"], "I"])
    cases["extra_added_row"] = c2
    c3 = copy.deepcopy(base)
    c3["d"]["harness_path1/h2_select.json"] = [r for r in c3["d"]["harness_path1/h2_select.json"] if r[1] != "I"]
    cases["removed_row"] = c3
    c4 = copy.deepcopy(base)
    c4["c"]["harness_path1/ind_las.json"] = []
    cases["c_changed"] = c4
    for name, doc in cases.items():
        p = HERE / f"neg_{name}.json"
        p.write_text(json.dumps(doc), encoding="utf-8", newline="\n")
        q = subprocess.run([PY, "-I", "-B", "-X", "utf8", str(LD), str(HERE / "list_A_r5.json"), str(p)],
                           capture_output=True, text=True, timeout=60)
        neg[name] = {"rc": q.returncode, "checks": json.loads(q.stdout.strip().splitlines()[-1])["checks"]}
    res["list_diff_negative"] = neg
    bad = HERE / "missing.json"
    q = subprocess.run([PY, "-I", "-B", "-X", "utf8", str(LD), str(bad), str(bad)], capture_output=True, text=True,
                       timeout=60)
    res["list_diff_input_error_rc"] = q.returncode
    # verdict
    exp_r5 = {"harness_path2/p2v5c_merge.json": [["parts", str(i), "sha256"] for i in range(3)]}
    got_r5 = {f: sorted(d) for f, d in res["e2e_r5"].items()}
    ok = (res["A_list_diff"]["rc"] == 0 and res["B_list_diff"]["rc"] == 0
          and res["A_list_diff"]["out_file_equal_stdout"] and res["B_list_diff"]["out_file_equal_stdout"]
          and got_r5 == {f: sorted(v) for f, v in exp_r5.items()} and res["e2e_r6"] == {}
          and all(v["rc"] == 1 for v in neg.values()) and res["list_diff_input_error_rc"] == 2)
    res["status"] = "ok" if ok else "fail"
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
