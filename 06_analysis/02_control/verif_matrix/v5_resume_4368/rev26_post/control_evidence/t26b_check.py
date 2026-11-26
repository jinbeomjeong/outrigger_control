"""rev26 erratum 3: RD-1 4 conditions 1..3 for T26' and runner-relevant blob sha (git objects only, no results)."""
import hashlib
import json
import subprocess

REPO = r"C:\workspace\outrigger_control"
WT = r"C:\workspace\outrigger_control\.claude\worktrees\rev26-t26b"
M4, T26, T26B, R2 = "932f1fb1724f074e4ee93a9c02193c7c840d13c4", "335004a7ad9f5f988e7543dd98d45bf2b96e4294", \
    "74c27846cbfab498bd59340d1eaec344f1596b0b", "b9f5707d7f3f7a26230b25f4edbc1fec587ca612"
B = "06_analysis/02_control/verif_matrix/v5_resume_4368"
P1 = ["04_scripts/04_hydraulic/coupled/judge_stage1_4368.py", "04_scripts/04_hydraulic/coupled/judge4368_common.py",
      "04_scripts/04_hydraulic/coupled/u3_judge_4368.py", "04_scripts/04_hydraulic/coupled/h8_noise_judge_4368.py",
      "04_scripts/04_hydraulic/coupled/h6_judge_4368.py", "04_scripts/04_hydraulic/coupled/README_judges_4368.md",
      "06_analysis/02_control/verif_matrix/scripts/resume4368_judge.py", "05_tests/unit/test_judges_4368.py",
      "05_tests/unit/test_judges_4368_h6_h8.py", "05_tests/unit/test_resume4368.py",
      "05_tests/unit/test_resume4368_rev1.py", "05_tests/unit/test_resume4368_rev16.py",
      "05_tests/unit/test_resume4368_supplement4.py", "05_tests/unit/test_resume4368_supplement5.py"]
P2 = [f"{B}/path2/{n}" for n in ("README.md", "p2_4368.py", "p2_u3.py", "p2_v5j.py", "p2_x16.py", "test_p2_4368.py",
                                  "test_p2_u3.py", "test_p2_v5j.py", "test_p2_x16.py")] + \
     [f"{B}/path2_v5c/{n}" for n in ("README.md", "p2v5c_common.py", "p2v5c_grid.py", "p2v5c_noise.py",
                                      "p2v5c_stage1.py", "test_p2v5c.py")]


def git(*a, cwd=REPO, raw=False):
    p = subprocess.run(["git", "-C", cwd, *a], capture_output=True, timeout=120)
    assert p.returncode == 0, (a, p.stderr)
    return p.stdout if raw else p.stdout.decode("utf-8")


def blob(c, f):
    return git("cat-file", "blob", f"{c}:{f}", raw=True)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def lf(b):
    return b.replace(b"\r\n", b"\n")


out = {}
n_t26 = git("diff", "--name-only", f"{M4}..{T26}").splitlines()
n_t26b = git("diff", "--name-only", f"{M4}..{T26B}").splitlines()
out["cond1_names_t26_count"], out["cond1_names_t26b_count"] = len(n_t26), len(n_t26b)
out["cond1_same_set"] = n_t26 == n_t26b
out["cond1_names_lf_joined_sha256_t26b"] = sha("\n".join(n_t26b).encode())
out["t26_to_t26b"] = git("diff", "--name-status", f"{T26}..{T26B}").splitlines()
out["cond2_src_params_changed"] = git("diff", "--name-only", f"{R2}..{T26B}", "--", "03_src", "02_params").splitlines()
out["parent"] = git("rev-parse", f"{T26B}^").strip()
out["parents_count"] = len(git("rev-list", "--parents", "-n", "1", T26B).split()) - 1
c3 = {"unchanged_equal": 0, "unchanged_differ": [], "changed": []}
for f in P1 + P2:
    a, b = blob(M4, f), blob(T26B, f)
    if f in n_t26b:
        c3["changed"].append(f)
    elif sha(lf(a)) == sha(lf(b)):
        c3["unchanged_equal"] += 1
    else:
        c3["unchanged_differ"].append(f)
out["cond3"] = {"files": len(P1 + P2), "unchanged_equal": c3["unchanged_equal"],
                "unchanged_differ": c3["unchanged_differ"], "changed_count": len(c3["changed"])}
out["allow_path2_t26b_raw"] = {f.split(B + "/")[1]: sha(blob(T26B, f)) for f in P2}
out["allow_path2_t26_raw_changed_vs_t26b"] = [f.split(B + "/")[1] for f in P2 if blob(T26, f) != blob(T26B, f)]
out["allow_path1_t26_vs_t26b_changed"] = [f for f in P1 if blob(T26, f) != blob(T26B, f)]
out["test_rev26_p2_t26b_raw"] = sha(blob(T26B, f"{B}/path2/test_rev26_p2.py"))
out["rules_files_t26b_vs_t26"] = [f for f in n_t26b if (f.startswith("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26")
                                                     or "/rev26_fixed/" in f or f == ".gitattributes")
                                  and blob(T26, f) != blob(T26B, f)]
with open(WT + r"\03_src\outrigger_sim\hydraulics\v5_options.py", "rb") as fh:
    out["wt_v5_options_raw"] = sha(fh.read())
out["wt_autocrlf"] = git("config", "core.autocrlf", cwd=WT).strip()
out["wt_head"] = git("rev-parse", "HEAD", cwd=WT).strip()
out["wt_status_porcelain_lines"] = len(git("status", "--porcelain", cwd=WT).splitlines())
print(json.dumps(out, indent=1))
