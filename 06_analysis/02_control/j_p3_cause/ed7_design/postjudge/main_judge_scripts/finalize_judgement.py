import pathlib

root = pathlib.Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause")
doc = root / "jp3_ed7_judgement_8a2a52ce.md"
keep = root / "ed7_design" / "ed7_j9fail_8a2a52ce" / "handback_judgement_draft_full.md"

text = doc.read_bytes().decode("utf-8")
if not keep.exists():
    keep.write_bytes(text.encode("utf-8"))

marker = "\n---\n\n**보고(판정서 밖)**"
idx = text.find(marker)
assert idx > 0, "trailer marker not found"
body = text[:idx].rstrip("\n") + "\n"

old_line = "  - 처리 뒤 sha는 메인이 채운다: LOCAL_ONLY_SUMS_PATH, LOCAL_ONLY_SUMS_SHA256, BACKUP_PATH"
new_line = (
    "  - 처리 결과(메인, 2026-11-26): `tools\\integrity\\large_outputs.py --apply`로 4개를 로컬 전용(ignore)으로 돌렸다. "
    "sha 고정 목록 `j9_runs/8a2a52ce_LOCAL_ONLY.SHA256SUMS`(sha256 "
    "`d49f40d1119c1c885bf42230731da564b49ec4c2d9d31046b8db4bd74da2ed4a`), "
    "백업 `C:\\Users\\jinbeom\\.claude\\backups\\outrigger-ed7\\j9_runs_8a2a52ce\\`(4개 + 목록). "
    "T4h npz 1752개는 판 6과 같이 git 제외(로컬)이고 단계 폴더 SHA256SUMS가 sha를 고정한다"
)
assert body.count(old_line) == 1
body = body.replace(old_line, new_line)

old_o720 = "| O7-20 | 실행 준비 | `j9_runs\\606f8713` 최상위 목록을 열람했다(메인 보고, 하위 폴더 안은 열지 않음) |"
new_o720 = (
    "| O7-20 | 실행 준비(python-expert, 실행 설정·자원 추정 작업) | `j9_runs\\606f8713` 최상위 목록을 비재귀로 열람했다(폴더·파일 이름만, `cdry_a1` 안은 열지 않음). "
    "같은 작업에서 `j_p3_cause` 최상위에 `jp3_remedy_spec_v7*` 이름 필터를 1회 썼다(명세 4개 이름). 근거 `ed7_design/run_prep/handback_run_config_prep.md` |"
)
assert body.count(old_o720) == 1
body = body.replace(old_o720, new_o720)

doc.write_bytes(body.encode("utf-8"))
print("ok", len(body.splitlines()), "lines")
