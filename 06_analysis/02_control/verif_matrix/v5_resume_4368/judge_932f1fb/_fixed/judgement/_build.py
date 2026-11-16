"""Assemble the harness judgement draft: body.md + verbatim extracts (block JD-6, supplement disclosure tables,
K-R definition table, sealed rule sentences, G-S / wrapper sha lists). Usage: python -I _build.py <scratchpad> <repo> <rules_dir> <out.md>
"""
import hashlib
import sys
from pathlib import Path

SP, REPO, RULES, OUT = (Path(a) for a in sys.argv[1:5])
HO = SP / "r4-handoff"


def lines(p):
    return Path(p).read_text("utf-8").split("\n")


def section(p, head_prefix):
    """Lines after the first '## ' heading starting with head_prefix, up to the next '## ' heading."""
    ls = lines(p)
    i = next(n for n, l in enumerate(ls) if l.startswith("## ") and l[3:].startswith(head_prefix))
    out = []
    for l in ls[i + 1:]:
        if l.startswith("## "):
            break
        out.append(l)
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out)


def table_after(p, marker):
    ls = lines(p)
    i = next(n for n, l in enumerate(ls) if marker in l)
    j = next(n for n in range(i + 1, len(ls)) if ls[n].startswith("|"))
    out = []
    for l in ls[j:]:
        if not l.startswith("|"):
            break
        out.append(l)
    return "\n".join(out)


def after(text_line, key):
    k = text_line.index(key) + len(key)
    return text_line[k:].strip()


def quote(s):
    return "\n".join("> " + l if l.strip() else ">" for l in s.split("\n"))


inc = {}
inc["INC_JD6"] = table_after(HO / "r4_common_block_draft.md", "**[판정서] JD-6 공개 목록**")
inc["INC_S12"] = section(HO / "supplement_r4_1.md", "공개 대상")
inc["INC_S3"] = section(HO / "supplement_r4_2.md", "공개 대상")
inc["INC_S4"] = section(HO / "supplement_r4_3.md", "공개 대상")
inc["INC_S5"] = section(HO / "supplement_r4_4.md", "공개 대상")
inc["INC_S6"] = section(HO / "supplement_r4_5.md", "판단 요약")
inc["INC_KR6"] = section(SP / "r4-source" / "r4_kr_cross_path.md", "6. 정의 차이 표")

r3 = lines(RULES / "v5_resume_4368_rules_rev3.md")
l = next(x for x in r3 if "**한계 공개(판정서 한계 절에 그대로 적는다)**" in x)
inc["INC_R3E3"] = quote(after(l, "**한계 공개(판정서 한계 절에 그대로 적는다)**: "))
r16 = lines(RULES / "v5_resume_4368_rules_rev16.md")
l = next(x for x in r16 if "판정서 한계 절에 그대로 적는다: \"경로 2 작성자의 rev16 파일 접근" in x)
inc["INC_R1610"] = quote(after(l, "판정서 한계 절에 그대로 적는다: "))
l = next(x for x in r16 if "판정서 한계 절에 그대로 적는다: \"R4 두 경로 도구의 수정 항목" in x)
inc["INC_R160"] = quote(after(l, "판정서 한계 절에 그대로 적는다: "))
i = next(n for n, x in enumerate(r16) if "**판정서 한계 절에 그대로 적을 문장**" in x)
block = [after(r16[i], "**판정서 한계 절에 그대로 적을 문장**: ")]
n = i + 1
while not block[-1].rstrip().endswith('수 있다."'):
    block.append(r16[n])
    n += 1
inc["INC_R1615A"] = quote("\n".join(block))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


gs = REPO / "06_analysis/02_control/verif_matrix/v5_resume_4368/gs_harness_b9f5707"
files = sorted(p for p in gs.rglob("*") if p.is_file())
rows = ["- 하네스 G-S 출력 `v5_resume_4368/gs_harness_b9f5707/`(R2): 파일 %d개." % len(files),
        "  - 폴더 안 sha 목록 `gs_files_sha256.txt` sha256 `%s`" % sha(gs / "gs_files_sha256.txt"),
        "  - `gs_report.json` sha256 `%s`" % sha(gs / "gs_report.json"),
        "  - 위 두 파일로 157개 전부를 대조한다(이 판정서에 파일별로 옮기지 않음).",
        "", "- H-11·H-12 래퍼 `07_results/S9/R4368X_b9f5707_20261115_013947/_tools/harness/`(D416)", "",
        "| 파일 | sha256 |", "|---|---|"]
tools = REPO / "07_results/S9/R4368X_b9f5707_20261115_013947/_tools"
for p in sorted((tools / "harness").iterdir()):
    if p.is_file():
        rows.append("| `%s` | `%s` |" % (p.name, sha(p)))
rows += ["", "- 그 밖 `_tools/`", "", "| 파일 | sha256 |", "|---|---|"]
for p in sorted(tools.iterdir()):
    if p.is_file():
        rows.append("| `%s` | `%s` |" % (p.name, sha(p)))
inc["INC_GS"] = "\n".join(rows)

# appendix E: R4 blob table (main session TSV, verbatim cells)
blob = SP / "judgement-r4" / "r4_blob_table.tsv"
tsv = [l.split("\t") for l in blob.read_text("utf-8").splitlines() if l.strip()]
head, body = tsv[0], tsv[1:]
brows = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
for r in body:
    brows.append("| " + " | ".join("`%s`" % c if i < len(r) - 1 else c for i, c in enumerate(r)) + " |")
same = sum(1 for r in body if r[-1].strip() == "yes")
brows.append("")
brows.append("- 행 %d, 같음(`yes`) %d." % (len(body), same))
inc["INC_BLOB"] = "\n".join(brows)

# appendix F: identity files
ident = REPO / "07_results/S9/R4368X_b9f5707_20261115_013947/_identity"
irows = ["| 파일 | sha256 |", "|---|---|"]
for p in sorted(ident.iterdir()):
    if p.is_file():
        irows.append("| `%s` | `%s` |" % (p.name, sha(p)))
irows.append("")
irows.append("- 파일 %d개." % (len(irows) - 3))
inc["INC_IDENT"] = "\n".join(irows)

# appendix C: _fixed list (source, name inside _fixed/, raw sha256)
V = REPO / "06_analysis/02_control/verif_matrix/v5_resume_4368"
fixed = [
    ("baseline", SP / "main/r4_baseline_sets.json"), ("baseline", SP / "main/r4_baseline_sets.sha256"),
    ("manifest", SP / "r4-p2/p2_manifest_draft.json"),
    ("compare", SP / "main/r4run/compare_r4.py"), ("compare", SP / "main/r4run/test_compare_r4.py"),
    ("compare", SP / "main/r4run/compare_r4_result.json"),
    ("grade", HO / "r4_grade_compare_table.md"),
    ("run", SP / "r4-p1/run_judgement_path1_draft.ps1"), ("run", SP / "main/r4run/final/run_judgement_path1_M4.ps1"),
    ("run", SP / "main/r4run/final/run_judgement_path1_M4_retry1.ps1"),
    ("run", SP / "main/r4run/run_judgement_path2.ps1"), ("run", SP / "main/r4run/final/run_judgement_path2_M4.ps1"),
    ("run", SP / "main/r4run/final/tests_path1.txt"), ("run", SP / "main/r4run/final/tests_path2.txt"),
    ("inputs", SP / "main/r4run/inputs_before.json"), ("inputs", SP / "main/r4run/inputs_after.json"),
    ("tools", SP / "main/sidecars_b9f5707.py"),
    ("handoff", HO / "r4_common_block_draft.md"),
] + [("handoff", HO / ("supplement_r4_%d.md" % i)) for i in range(1, 6)] + [
    ("handoff/final", p) for p in sorted((HO / "final").glob("*.md"))
] + [
    ("h0", V / "h0_judge/t3_k1_a861981_move_manifest.txt"),
] + [("audit", p) for p in sorted((SP / "r4-source").glob("*.md"))] + [
    ("judgement", SP / "judgement-r4/_p7_p11.py"), ("judgement", SP / "judgement-r4/p7_p11.json"),
    ("judgement", SP / "judgement-r4/r4_blob_table.tsv"), ("judgement", SP / "judgement-r4/_build.py"),
    ("judgement", SP / "judgement-r4/body.md"),
    ("judgement", SP / "judgement-r4/_unchanged_blobs.py"), ("judgement", SP / "judgement-r4/r4_unchanged_blobs.json"),
]
frows = ["| # | 원 경로 | `_fixed/` 안 이름 | sha256 |", "|---|---|---|---|"]
for n, (sub, p) in enumerate(fixed, 1):
    p = Path(p)
    assert p.is_file(), p
    try:
        src = "`scratchpad\\" + str(p.relative_to(SP)).replace("/", "\\") + "`"
    except ValueError:
        src = "`" + str(p.relative_to(REPO)).replace("\\", "/") + "`"
    frows.append("| %d | %s | `_fixed/%s/%s` | `%s` |" % (n, src, sub, p.name, sha(p)))
frows.append("")
frows.append("- 파일 %d개. `judgement/body.md`·`_build.py`는 이 판정서를 다시 조립하는 원본이다(이 판정서 = body.md + 원문 끼움). "
             "`body.md`·`_build.py`의 sha는 조립 때 값이고, 판정서를 다시 고치면 바뀐다(메인이 복사 때 다시 잰다)." % len(fixed))
frows.append("- 이 판정서 뒤에 생기는 감사 리포트(재감사 등)는 메인이 같은 폴더(`_fixed/audit/`)에 더한다.")
inc["INC_FIXED"] = "\n".join(frows)

text = (SP / "judgement-r4" / "body.md").read_text("utf-8")
text = text.replace("@@BLOB_SHA@@", sha(blob))
for k, v in inc.items():
    marker = "@@%s@@" % k
    assert text.count(marker) >= 1, (k, text.count(marker))
    text = text.replace(marker, v)
assert "@@INC_" not in text and "@@BLOB_SHA@@" not in text
OUT.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8", newline="\n")
print({"lines": text.count("\n") + 1, "sha256": sha(OUT), "includes": {k: v.count("\n") + 1 for k, v in inc.items()}})
