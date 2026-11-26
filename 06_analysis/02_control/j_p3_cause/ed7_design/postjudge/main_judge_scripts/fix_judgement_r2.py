import pathlib

doc = pathlib.Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\jp3_ed7_judgement_8a2a52ce.md")
text = doc.read_bytes().decode("utf-8")
lines = text.split("\n")


def replace_once(old, new):
    global text
    assert text.count(old) == 1, old[:60]
    text = text.replace(old, new)


# F-2 title
replace_once("(2026-11-26, control-expert 초안)", "(2026-11-26, control-expert 초안, 메인 수정·판정서 감사 반영)")
# F-2 319
replace_once("(판정 후 감사 M-2, 예정).", "(판정 후 감사 M-2, 처리함).")
# F-1 322
replace_once(
    "T4h npz 1752개는 판 6과 같이 git 제외(로컬)이고 단계 폴더 SHA256SUMS가 sha를 고정한다",
    "T4h npz 1749개와 `l1ref_a1`의 `*.partial.jsonl` 3개(L1_VBM0·L1a_VBM·L1a_VBM0, 기존 `*.partial.jsonl` 제외 규칙)는 "
    "판 6과 같이 git 제외(로컬)이고 단계 폴더 SHA256SUMS가 sha를 고정한다. partial 3개도 같은 백업 폴더에 복사했다(LOCAL_ONLY 목록에는 넣지 않음)",
)
# F-2 374
replace_once("M-2 → 7.5절(로컬 전용 예정, sha는 메인이 채움)", "M-2 → 7.5절(로컬 전용 처리함, 목록 sha 기재)")
# F-2 386
replace_once(
    "- 이 판정서는 아직 판정서 감사를 받지 않았다. 메인이 `judgement_checklist.py`로 대조한다.",
    "- 판정서 감사: `ed7_design/postjudge/audit_judgement_ed7_8a2a52ce_20261126.md`(차단 0, 확정 전 수정 3 반영: F-1 npz 수·partial 3, F-2 상태 문구, F-3 O7-27). "
    "`judgement_checklist.py` 결과: `ed7_design/postjudge/judgement_checklist_r1.md`(missing 2는 감사 R-1에서 충족 확인).",
)
# F-3 O7-27 after O7-26 row
o726 = next(l for l in lines if l.startswith("| O7-26 |"))
o727 = (
    "| O7-27 | 판정서 감사(verif-protocol-auditor) | (a) `j_p3_cause` 최상위 비재귀 `Get-ChildItem -File -Filter \"jp3_remedy_spec_v7*\"`로 명세·정오와 `.sha256` 4개 이름 출력. "
    "(b) Grep 1회의 `path`로 블라인드를 품은 `j_p3_cause`를 썼다(glob `jp3_remedy_spec_v[67]*.md`, 패턴 `ret_breach\\|_flag`, 건수 모드). 출력은 `jp3_remedy_spec_v7.md:1` 한 줄. ripgrep이 `j9_runs` 아래를 순회했을 수 있다. 지시 규칙 위반이다. "
    "(c) `baseline_check sums --base repo-root`(LOCAL_ONLY 목록 검증)가 저장소 루트 전체를 열거했다(블라인드 폴더와 worktree 사본 포함 가능). 출력은 합계 `unlisted 11635` 하나이고 이름은 없다 |"
)
replace_once(o726, o726 + "\n" + o727)
replace_once("- 번호 O7-20~O7-26은 이 판정서에서 새로 붙였다.", "- 번호 O7-20~O7-27은 이 판정서에서 새로 붙였다.")
# R-5 O7-25 note
o725 = next(l for l in lines if l.startswith("| O7-25 |"))
replace_once(o725, o725[:-2] + ". 이 행은 원인 분석 원문 공개 문단(`cause_analysis.md` 286~290행)보다 넓다. 출처 `ed7_design/ed7_j9fail_8a2a52ce/handback_judgement_draft_full.md` 397~400행 |")
# R-4
replace_once(
    "  - (i-b)가 탐침 뒤 다리를 시작점으로 되돌렸다.",
    "  - (해석) (i-b)가 탐침 뒤 다리를 시작점으로 되돌렸다.",
)
replace_once(
    "  - 그래서 재레벨이 \"높게 남은 다리를 고르게 내림\"",
    "  - (해석) 그래서 재레벨이 \"높게 남은 다리를 고르게 내림\"",
)
replace_once(
    "| 11 | FL-Fs4 위험(통계 표 2c) | **실현됐다.**",
    "| 11 | FL-Fs4 위험(통계 표 2c) | **위험 시나리오와 같은 꼴의 실패가 났다(기전 미확인).**",
)
# R-2
replace_once(
    "- T-JR-12b는 미실행이라 경로 2 대상도 없다.",
    "- T-JR-12b는 미실행이라 경로 2 대상도 없다.\n"
    "- 공개(봉인 11절 1021행): 판 6 경로 2 작성자(dynamics-expert)가 판 7 설계 검토(D1·D2)를 맡았다. 그 검토는 경로 2 자료를 열지 않았다고 밝혔다(d7 머리말).",
)
doc.write_bytes(text.encode("utf-8"))
print("ok")
