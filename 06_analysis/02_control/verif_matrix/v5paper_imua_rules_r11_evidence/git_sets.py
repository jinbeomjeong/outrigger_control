"""Collect file-name sets for the TA definition (names only, no file contents).

Path-2 tool contents are never read; for the T26' side only counts per top folder,
03_src/02_params entries and the intersection with the v5-imua side are printed.
"""
import json
import subprocess
import sys
from collections import Counter

REPO = r"C:\workspace\outrigger_control"
OUT = sys.argv[1]


def git(*args):
    r = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True,
                       encoding="utf-8")
    return r.returncode, r.stdout, r.stderr


def names(a, b, *paths):
    rc, out, err = git("diff", "--name-only", a, b, "--", *paths) if paths else \
        git("diff", "--name-only", a, b)
    if rc != 0:
        raise SystemExit(err)
    return sorted(x for x in out.splitlines() if x)


def full(rev):
    return git("rev-parse", rev)[1].strip()


res = {}
B9 = full("b9f5707")
res["revs"] = {k: full(k) for k in ["b9f5707", "932f1fb1", "976aa771", "74c27846",
                                     "b0416724", "2ea96c96", "335004a7"]}
res["anc_b9_in_932"] = git("merge-base", "--is-ancestor", B9, "932f1fb1")[0] == 0
res["anc_932_in_976"] = git("merge-base", "--is-ancestor", "932f1fb1", "976aa771")[0] == 0
res["anc_976_in_imua"] = git("merge-base", "--is-ancestor", "976aa771", "b0416724")[0] == 0
res["anc_932_in_t26p"] = git("merge-base", "--is-ancestor", "932f1fb1", "74c27846")[0] == 0
res["anc_335_in_t26p"] = git("merge-base", "--is-ancestor", "335004a7", "74c27846")[0] == 0

t26p = names("932f1fb1", "74c27846")
imua_all = names("932f1fb1", "b0416724")
res["t26p_side_count"] = len(t26p)
res["t26p_side_top"] = dict(Counter(x.split("/")[0] for x in t26p))
res["t26p_side_src_params"] = [x for x in t26p if x.startswith(("03_src/", "02_params/"))]
res["intersection_t26p_imua"] = sorted(set(t26p) & set(imua_all))
res["imua_side_count"] = len(imua_all)
res["imua_side_top"] = dict(Counter(x.split("/")[0] for x in imua_all))
res["b9_to_932_src_params"] = names(B9, "932f1fb1", "03_src", "02_params")
res["m932_to_976_src_params"] = names("932f1fb1", "976aa771", "03_src", "02_params")
res["m976_to_imua_src_params"] = names("976aa771", "b0416724", "03_src", "02_params")
res["b9_to_imua_src_params"] = names(B9, "b0416724", "03_src", "02_params")
res["m932_to_imua_src_params"] = names("932f1fb1", "b0416724", "03_src", "02_params")
res["m976_to_imua_all"] = names("976aa771", "b0416724")
res["m932_to_976_all_top"] = dict(Counter(x.split("/")[0]
                                          for x in names("932f1fb1", "976aa771")))
res["m932_to_976_04_scripts"] = [x for x in names("932f1fb1", "976aa771")
                                 if x.startswith("04_scripts/")]
res["m932_to_976_05_tests"] = [x for x in names("932f1fb1", "976aa771")
                               if x.startswith("05_tests/")]
res["gitattributes_changed_imua"] = ".gitattributes" in imua_all

# trial merge (writes objects only, no refs, no working tree)
rc, out, err = git("merge-tree", "--write-tree", "--name-only", "74c27846", "b0416724")
res["merge_tree_rc"] = rc
lines = out.splitlines()
res["merge_tree_tree"] = lines[0] if lines else None
res["merge_tree_conflict_lines"] = lines[1:]
if rc == 0 and lines:
    tree = lines[0]
    d = names("74c27846", tree)
    res["t26p_to_trial_merge_count"] = len(d)
    res["t26p_to_trial_merge_equals_imua_side"] = (set(d) == set(imua_all))
    d2 = names("b0416724", tree)
    res["imua_to_trial_merge_equals_t26p_side"] = (set(d2) == set(t26p))
    res["t26p_to_trial_merge_src_params"] = [x for x in d
                                            if x.startswith(("03_src/", "02_params/"))]

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in res.items()
                  if k not in ("m976_to_imua_all",)}, ensure_ascii=False, indent=1))
