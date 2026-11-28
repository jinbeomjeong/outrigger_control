"""Names-only check: Chrono C-5 judge files changed between R3f and the TA parents.

Path-2 folders are reported as counts only (no names, no contents).
"""
import json
import subprocess
import sys

REPO = r"C:\workspace\outrigger_control"
P2 = ("06_analysis/02_control/verif_matrix/v5_resume_4368/path2/",
      "06_analysis/02_control/verif_matrix/v5_resume_4368/path2_v5c/")


def git(*a):
    r = subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True,
                       encoding="utf-8")
    if r.returncode not in (0, 1):
        raise SystemExit(r.stderr)
    return r.returncode, r.stdout


def names(a, b):
    return sorted(x for x in git("diff", "--name-only", a, b)[1].splitlines() if x)


R3F = git("rev-parse", "8a0c843")[1].strip()
res = {"R3f": R3F,
       "r3f_anc_932": git("merge-base", "--is-ancestor", R3F, "932f1fb1")[0] == 0}
for lab, a, b in [("r3f_to_932", R3F, "932f1fb1"), ("m932_to_t26p", "932f1fb1", "74c27846"),
                  ("m932_to_imua", "932f1fb1", "b0416724")]:
    d = names(a, b)
    res[lab] = {
        "chrono_or_t45_04_scripts": [x for x in d if x.startswith("04_scripts/") and (
            "chrono" in x or "t45" in x or "t4h" in x or "4368" in x
            or "resume4368" in x)],
        "verif_scripts": [x for x in d if x.startswith(
            "06_analysis/02_control/verif_matrix/scripts/")],
        "path2_count": sum(1 for x in d if x.startswith(P2)),
        "src_params": [x for x in d if x.startswith(("03_src/", "02_params/"))],
    }
json.dump(res, open(sys.argv[1], "w", encoding="utf-8"), indent=1)
print(json.dumps(res, indent=1))
