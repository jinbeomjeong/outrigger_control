## 감사 요약
- 본 결과: 판 7 실행 출력은 없다. 이번에 연 것은 다음뿐이다.
  - 정오 1(e5e73119, 1~30행과 126~280행)
  - control 반영 보고 `handback_erratum1_reaudit_fix.md`(9c500a85)
  - 봉인 명세는 Grep으로만 봤다: `jp3_*` 배열 이름 2곳
  - 판 원판 `jp3_remedy_spec.md` 545행(배열 이름 존재)
  - 블라인드 경로와 판 6 `selection.json`은 열지 않았다.
  - **공개(절차 위반 1회)**: 배열 이름이 어느 봉인 문서에 있는지 찾으려고 Grep을 한 번 돌렸다. `path` = `06_analysis/02_control/j_p3_cause`(블라인드를 품은 상위 폴더)에 glob `jp3_remedy_spec*.md`, 건수 모드였다.
    - 출력은 최상위 명세·정오 8개 파일의 건수뿐이었고, 블라인드 경로의 이름·건수는 나오지 않았다.
    - 다만 ripgrep이 `j9_runs` 아래를 순회했을 수 있다(O7-13과 같은 종류).
    - 판정서 공개 목록에 O7-19로 더할 것을 권고한다.
- 대상·시점: 실행 전. 정오 1 봉인 전 확인 감사이고, 바뀐 행과 그 정합만 봤다.
- 기준 문서
  - 봉인 명세 10902ffd(`.sha256` 8cfd1981)
  - 정오 1 e5e73119a7ee…ffd83(280줄, LF만, CRLF 0, BOM 없음, `-text`, ignore 아님, 미추적)
  - T′ 60ebb4a4: worktree clean, HEAD 그대로
- 판정: **차단 0 / 실행 전 수정 0 / 기록 4**
  - **정오 1(e5e73119)은 봉인 가능하다.**
  - 기록 R-a·R-b는 봉인 전에 한 줄씩 고치면 더 좋다. 필수는 아니다.

## 확인 항목별 결론
1. **N-B1: 해소**
   - 13행: 1-13(결정 14, 12a·12b 한정)과 1-20 정하는 것 1~2를 경로 2에 [정의]로 넘긴다. 그 밖은 넘김 불변이다.
   - 219행: 판단 3을 좁혔다("사건 없음 처리도 판정 정의이므로 경로 2에 [정의]").
   - 247행(목록 16번), 265·272행: 11절 1019행 "조건 행 0 = 판정 불가 (12a·12b는 1-13·1-20)" 단서가 들어갔다.
   - **E7-P2-1과 T′ 동작이 같다**
     - 대상 줄
       - 12a: VBM 쪽 판정 센서 등급(ideal·normal) 줄. T′ `condition_lines`(`jp3_tjr_judge_ed7.py:100-110`)이 error가 아닌 줄 중 `is_judged_grade`인 줄이다.
       - 12b: 6.3.7 (4) 판정 쌍(기회·VBKM0 READY 없음)의 VBKM 판정 등급 줄. T′ `judged_condition_lines`(`jp3_12b_judge_ed7.py:173-185`)가 `JUDGED_CATEGORIES = (OPPORTUNITY, VBK0_NOT_READY)`(`jp3_12b_judge.py:141`)를 쓴다.
     - 침범 = 사용 상계 − 진값 < −1 Pa(`jp3_rev7_condition.py:150-151`)이면 실패다.
     - 판정 줄 전체의 조건 읽기 0(판정 줄 0 포함) → '해당 없음(기록)'이다(`summarize` 257행 → `r79_condition_basis` 570~572행). rev 6 판정은 그대로다.
     - 그 밖의 하위 명령은 판정 불가다(`condition_basis` 519~520행).
   - **E7-P2-2와 T′ 동작이 같다**
     - T4h 파일이나 배열 7개가 없으면 `setting_defect`다(539~543행, 배열 목록은 `T4H_ARRAYS` 85~86행과 같다).
     - 결측이 `t_event_s` 하나뿐이면 `no_event`(546행)다.
     - `t_event_s`가 있으면 정상 계산한다.
   - **누설**
     - `handoff_leak.py`를 274~280행만 잘라 돌렸다. 이름 사전은 `build-names --py` T′의 `jp3_ed7_judge`·`jp3_tjr_judge_ed7`·`jp3_12b_judge_ed7`·`jp3_rev7_condition`·`j_p3_inputs`·`jp3_12b_judge`·`jp3_tjr_judge`와 `--extra` 8개다.
     - 공유 문서를 봉인 v7 하나만 주면 `jp3_t_s`·`jp3_class`·`jp3_plant_state`·`jp3_p_tr_Pa`·`jp3_used_bound_Pa` 5개가 `name_leak`(outputs)으로 나왔다.
     - 이 이름들은 436.9 원판 `jp3_remedy_spec.md`(545행 등, 판 6.3 T4h 배열 정의)와 덧붙임 4a-2·4a-7에 있는 공유 정의 이름이다. 원판을 `--shared`에 더하면 **누설 0**(종료 0)이다.
     - 파일:행, 경로 1 함수·모듈 이름은 없다. 메인이 넘길 때 `handoff_leak`의 `--shared`에 원판을 넣어야 같은 결과가 나온다.
2. **M-a·M-b·M-c: 반영됐고 서로 모순 없음**
   - M-a
     - 136행: 12a·12b는 대조만, 출처별 값은 l1ref만이다.
     - 234행(6번): l1ref `runs.<stem>.identity_sources`, 12a·12b는 문제 목록만 인용한다.
     - 140행(거둠)·242행(14번)과 맞는다.
     - 옛 문장 "12a·12b도 출처별 값을 남긴다"는 정오 어디에도 남지 않았다.
   - M-b
     - 243~246행: O7-16(23행 머리말 공개와 연결), O7-17(T′ 보고 5절), O7-18(재감사 ref_check와 본 결과)
   - M-c
     - 207~208행: 기록이고 판정에 쓰지 않는다. 출력은 C worktree 밖·`j9_runs\8a2a52ce` 밖이고, 문제가 나오면 1단계 전에 사용자에게 알린다.
     - 248행(17번), 271행 표가 같은 문면이다.
     - 207행에 `judge_commit_60ebb4a4/` 함께 커밋(R-11)도 들어갔다.
3. **R-2·R-3·R-8·R-13: 반영됨**
   - R-2, 239행: 기록 설정 침범은 `J-P3_record_settings.rev7_record_only.runs_with_breach`에서 읽고, `…_judged_rows`는 쓰지 않는다. T′ 키 이름과 같다(`_sens_jp3` 1024~1028, 시험 `:855-856`).
   - R-3, 134행: 조건 2 단서(12a 폴더·meta 통째 결측 = `not_judgeable`, 67~69·75~77행)가 들어갔다. 141행과 같다.
   - R-8, 178행: 경고 8(7+1), 시험 실패 0, `junit_skips` 2658/2658이다. 근거 `worktree_tests.md` 101~112행과 맞는다.
   - R-13, 203행: `judge_60ebb4a4`로 채웠다.
4. **인용 sha: 실제와 같음**
   - 재감사 a56baf38cfb1ec41430cbbc49cd479b51d861528bb8149a39f870dbe22d6c59d(24행)
   - 앞 감사 8c9800c9, T′ 보고 a607aef7, SUMS 36f223e7, C 보고 9cabb1c2, T 보고 769a6089
   - Get-FileHash로 모두 쟀다.
5. **`placeholder_scan --pattern-set both --skip-inline-code`**: 미해결 0(종료 0, skipped 11)
6. **`ref_check --rev 60ebb4a4 --exclude <블라인드 3·.claude·판 6 selection.json>`**
   - missing 3건은 앞과 같은 설명된 항목이다: 62행 `d_grid_keys12.json`(3ecf61f1 blob), 118행 예시 경로 `j9_runs/p51_record_8a2a52ce/`, 147행 사용자 도구 `tools/verif/baseline_check.py`.
   - untracked 26건: 앞 21건 + 새로 인용한 `postseal`·근거 파일이다. 미커밋이고 ignore는 아니다.
   - 후보 목록은 화면에 내지 않게 잘라서 봤다.
7. **LF·BOM·`-text`: 맞음**
   - 정오: LF 280, CRLF 0, BOM 없음, `text: unset`, ignore 아님.
   - `postseal/audit_prerun_Tprime_erratum1_20261125.md`도 `-text`다.
8. **차단 0, 정오 1(e5e73119) 봉인 가능**

## 발견 사항(모두 기록)
1. **R-a**: 1-13 T′ 요구(165행) 끝 문장 "조건 항목 상태 `not_applicable`과 그 줄 수를 report에 남긴다"가 T′와 다르다.
   - T′에는 `not_applicable` 상태가 없다.
   - report에는 줄 상태 `no_event`, `rev7_condition.summary.no_event_lines`, `rev7_condition_records`("해당 없음, 기록")가 남는다(552~573행).
   - 이 문장은 이번 변경 전부터 있었는데, 앞 재감사에서 놓쳤다.
   - 판정 후 `judgement_checklist`가 `not_applicable`을 찾을 수 있다.
   - 권고: "`no_event` 줄 수(`no_event_lines`)와 `rev7_condition_records`"로 바꾼다.
2. **R-b**: 1-16 사실 정정(187행) 끝 문장 "기록 설정 J-P3 침범이 T의 감도 상태에 들어갔는지는 … 확인하지 않았다(재감사 확인 대상)"가 재감사 답(확인 항목 4)을 반영하지 않았다.
   - 재감사 답: T에서 기록 설정 침범(H-7)은 status에 들어가지 않았고, 줄 단위 결함 수 5종만 들어갈 수 있었다. T′은 기록 줄을 J-P3 status에 넣지 않고, 460줄 정체성 대조는 남는다.
   - 권고: 그 사실로 바꾼다.
3. **R-c**: 1-9 130행 "첫 실측은 l1ref"는 M-c 결정 뒤에는 "첫 실측은 1단계 전 건식 확인(1-19), 판정 실측은 l1ref"가 맞다. 문면 차이일 뿐이다.
4. **R-d(공개)**: 이 감사의 Grep 1회(맨 위 「본 결과」)를 판정서 공개 목록에 O7-19로 더하기를 권고한다.

## 위임 필요
- control-expert(선택, 봉인 전이면 좋음): R-a 165행, R-b 187행, R-c 130행, R-d 목록 15번에 O7-19 추가. 고치면 sha가 바뀌므로 메인이 새 sha로 봉인한다. 이번 확인 결과는 바뀐 그 줄들에만 영향을 준다.

## 메인 세션 권고
1. 정오 1을 봉인한다: `.sha256`(LF), 근거 폴더 5개(`run_commit_8a2a52ce`, `suite_8a2a52ce`, `judge_commit_c91065b7`, `judge_commit_60ebb4a4`, `postseal`)와 함께 커밋한다. 커밋 전에 `git status --ignored`를 본다. 이 확인 감사 원문을 `postseal`에 저장한 뒤 `postseal` SUMS를 마지막에 쓴다.
2. 경로 2 넘김 문서에 E7-P2-1·E7-P2-2를 그대로 옮긴다. `handoff_leak.py <넘김> --names <build-names 사전>`의 사전은 `--shared`에 봉인 v7과 436.9 원판 `jp3_remedy_spec.md`를 모두 넣어 만든다(원판을 빼면 T4h 배열 이름 5개가 누설로 나온다).
3. 1단계 전 M-c 건식 확인(1-19). ed7-judge lock 사유를 T′로 갱신한다.

## 검사하지 못한 것
- 바뀐 행 밖의 정오 본문은 전체 재감사하지 않았다(지시 범위). 단, R-a·R-c는 범위를 읽다가 눈에 띈 것이다.
- 경로 2 넘김 문서는 아직 없어 보지 않았다.

## 실행한 검증
- 인터프리터: python-dev `-I -B`(`MKL_THREADING_LAYER=TBB`). 프로젝트 env와 판정 도구 import는 쓰지 않았다.
- 해시: Get-FileHash로 정오와 `postseal` 11개 파일. python 한 줄로 정오의 CRLF·BOM을 셌다.
- git(조회): `check-attr text`, `check-ignore -v`, ed7-judge `rev-parse`·`status --porcelain`(clean).
- 도구(`~/.claude/tools/verif`)
  - `placeholder_scan`(--skip-inline-code): 0
  - `ref_check`: missing 3, 설명됨
  - `handoff_leak build-names` + scan(274~280행 블록): 원판 공유 포함 시 누설 0
- 즉석 스크립트: `cut.py`(정오 274~280행을 scratchpad txt로 자름). scratchpad `verif-ed7Tp2\`는 폴더째 지웠다(Test-Path False).
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v7.md 10902ffd…, jp3_remedy_spec_v7.md.sha256 8cfd1981…, jp3_remedy_spec_v7_erratum1.md e5e73119…, handback_erratum1_reaudit_fix.md 9c500a85…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
