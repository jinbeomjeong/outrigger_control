## 감사 요약
- 결론: 차단 1건이 남아 아직 봉인할 수 없다. 이전 B-1을 고친 문면이 판 7 판정 도구 일부를 빠뜨렸다. 명세 두 곳(5.2 항목 목록, 4a 판정 불가 목록)에 문장을 더하면 풀린다. 새로 돌릴 실행은 없다.
- 판정: 차단 1 / 실행 전 수정 1 / 기록 6.
- 대상: 436.9 판 7 봉인 전 재확인(시점: 실행 전, 봉인 전)
  - 명세 `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\jp3_remedy_spec_v7.md`
  - 작업본 sha 4d9a902a를 실측했고 지시값과 같다. 1102행(호출의 "1103줄"과 1줄 차이, 끝 개행 차로 봄), LF, BOM 없음, `-text`.
  - 도구 worktree ed7-impl HEAD b46bdf8f, 깨끗한 트리.
- 본 결과: 아래 파일은 상태·건수와 명세 수치 일치 여부만 대조했다. 이 보고에 새 수치는 옮기지 않았다.
  - `share_result.json`: 결정, 팔별 실패 단위 수, 발동 수
  - `compare_result.json`: 상태 필드와 건수
  - `ed7_probe_a2.identity.json`: head·is_clean

## 이전 지적 처리 상태
| 지적 | 상태 | 근거 |
|---|---|---|
| B-1 판정 커밋 | **일부만 풀림**(새 차단 N-1) | 4a(584행), 5.2(629~647행), P7-11(607행), 13절 Q7-U6가 생겼다. 정의·허용 경로·시험 범위·감사·판정 불가 조항은 맞다. T 후보 판정 도구는 실행 경로 정적 import 닫힘(`run_v5`·`ed7_probe`, 73모듈) 밖에 있음을 ast로 확인했다(`harness_hydraulics`만 안). 다만 N-1 참조 |
| B-2 몫 판단 | **풀림** | 552~560행. `share_b46bdf8f\SHA256SUMS`는 6항목, 불일치·빠진 파일 0, sha 0a27f09c(명세 인용과 같음). `share_result.json`의 status decided, 팔별 실패 단위·발동 수·네 요소 남김 결정이 명세 554~556행과 같다. 규칙 정정(550·551행)은 판 6 명세 335~375행의 (a)(b)와 B3 2키 차 예외와 같다. 결과를 본 뒤 정정했다는 공개는 1058행에 있다 |
| M-1 | 풀림 | 245행에 전체 sha 3b88e4a8…를 적었고 파일과 같다 |
| M-2 | 풀림, 하지만 다시 낡음(M-9) | 41·42행에 시점 값을 함께 적었다 |
| M-3 | 풀림 | 641행(키 파일 불변, 판정 도구가 무시), 220행 |
| M-4 | 풀림 | 606행, 620행(197~201행 허용) |
| M-5 | 풀림 | 1019행(O7-1~O7-13), 1045~1046행(305bbb91과 `handback_spec_rev6.md` e0d95bf6이 control SUMS 항목과 같음), 1059행(x·y) |
| M-6 | 대부분 풀림 | probe 폴더 SUMS(8항목, sha 432fc760, 명세 146행과 같음)와 README(condition.json은 결함 판으로 쓰지 않음)를 만들었다. 642행에 조건 도구 출력의 head·is_clean을 넣었다. npz는 R-11 참조 |
| M-7 | 풀림 | 587행, 620행 |
| M-8 | 풀림 | 599행, 1061행. `compare_result.json`: status match, commands 114/114, 한쪽에만 있는 줄 0, 오류 줄 0, 고정 표 64행 차이 0, 6.2·6.3 모두 not_failed, worktree 변화 없음. identity는 b46bdf8f, is_clean true. `j9_runs\b46bdf8f\repro_a2\SHA256SUMS` 117항목 불일치 0(sha 4a4fc7c0, 명세와 같음) |
| R-4·R-5·R-9·R-10 | 풀림 | 496·653·671·741·970행, 982행. `tool_a6fc3dd5` SUMS는 목록 밖 파일 0 |

## 발견 사항 (심각도순)

**[차단][R·I] N-1. T 항목 목록과 "T 전 판정 불가" 목록에 판 7 설정 이름을 읽는 판정 도구가 빠져 있다. P7-1·P7-2·j9_main·12a·12b를 판정할 도구가 C에도 T에도 정해져 있지 않다.**
- 근거
  - b46bdf8f의 판정 도구는 판 6 설정 이름에 묶여 있다.
    - `jp3_ed6_judge.py` 117행: j9main 대응 `6: {"VBL": "VB", "LSL1": …}`
    - 같은 파일 941·945행: t8이 `"VBL"`/`"VBL0"`를 쓴다
    - 같은 파일 67행: cases가 VBL·LSL1~4를 쓴다
    - `jp3_tjr_judge.py` 228·229·661행: 12a 묶음이 VBL/VBL0이다
    - 12b 판정은 `jp3_12b_judge_ed6.py`이고 VBKL 계열이다
  - VBM·LSM·VBKM·VBM0을 아는 스크립트는 `run_v5`·`ed7_*`·`jp3_ed7_rules`·`jp3_12b_plan`·`j_p3_inputs`뿐이다(git grep). `ed7_t8`·`ed7_cases` 배치를 쓰는 판정 코드는 0건이다.
  - 명세 583행 4절 5는 "C에서 P7-10, P7-0~P7-6, P7-3·P7-9는 해시까지만"이라고 한다. P7-1(T8)과 P7-2(사례 재생 J-P3 판정 키 0)은 C에서 판정하라고 적혀 있다. 그런데 C는 상수만 바꾸므로(P7-10) 그 도구를 넣을 수 없다.
  - 584행과 647행의 판정 불가 목록은 "P7-3·P7-9 단위 판정, 6.2(감도), 6.3, J7, ③ rev 7"뿐이다. j9_main(6.2 앞 절반), 12a·12b(6.4), P7-1·P7-2가 없다.
  - 5.2 항목 1~10에도 j9main 판 7 대응, t8·cases·12a·12b 판 7 대응이 없다.
- 실패 시나리오: 실행 뒤 이 관문들을 즉석 스크립트(감사·시험 밖)로 판정하게 되거나, 정오가 생긴다. P7-1·P7-2는 멈춤 관문이라, 검증되지 않은 도구로 통과·멈춤이 정해진다.
- 권장 조치(control-expert 문안, 두 곳)
  1. 5.2 항목에 "판 7 설정(VBM·LSM1~4·VBM0·VBKM·VBKM0·VBM<key>)을 읽는 모든 판정 하위 명령"을 넣는다. 꼽을 것: `j9main --edition 7` 대응, `t8`(P7-1), `cases`(P7-2), `hash-match` 대상, 12a 묶음 VBM/VBM0, 12b VBKM/VBKM0와 P-pred 입력, 감도, G1.
  2. 4a와 5.2의 판정 불가 목록을 "4절 5의 P7-1·P7-2·P7-3·P7-9 판정과 6~10단계의 모든 판정"으로 넓힌다. 그리고 4절 5 문장에서 P7-1·P7-2 판정을 T 뒤로 옮긴다. P7-0·P7-6은 단위 시험(`test_ed7_harness.py`, `test_ed7_units.py`)이 덮으므로 P7-4에서 판정해도 된다.
  - 담당: 명세는 control-expert, T 구현은 python-expert.

**[실행 전 수정][S] M-9. 41행의 "현재 값" `ad37ad0e…`가 다시 낡았다.**
- control_v7_review `SHA256SUMS`는 지금 e0d45969…(13항목)다. 10:18:07에 수정됐고, 명세 마지막 저장(10:17:35)보다 늦다. `handback_spec_rev6_audit.md`·`handback_spec_rev6_final.md`가 더해진 것이다.
- seal_check는 41행 ad37ad0e를 `quoted_unresolved`로 냈다.
- 조치: "개정 6 감사 반영 시점 값"으로 표기를 바꾼다. 아니면 그 폴더 SUMS를 봉인 전에 마지막으로 굳힌 뒤 값을 다시 넣는다. 이 폴더에 handback이 더해질 때마다 같은 일이 생긴다.

**[기록] R-11. probe 폴더 T4h npz 654개는 어느 SUMS에도 없다.**
- probe 폴더 SUMS는 8항목이고, `ed7_probe_t4h\SHA256SUMS`는 없다. 목록 밖 파일 654개.
- repro 폴더는 npz 114개를 SUMS에 넣었다.
- `git add -f`로 커밋하면 git blob이 고정하므로 판정 영향은 없다. 일관성을 위해 npz 줄을 더하기를 권한다.

**[기록] R-12. 남은 낡은 문구**
- 1031행 "FL-Fs4 줄의 추출 오프셋은 봉인 때 공개한다": 1044행에서 이미 공개했다.
- 194행 "C는 b46bdf8f에서 상수만 바꾸므로 … 상수 줄 외에는": 지금은 docstring과 run steps도 허용한다.
- 4절 번호 순서가 4 → 5 → 4a다. 4a가 5 뒤에 있다.

**[기록] R-13. `ed7_design\audit_preseal\`에는 폴더 SUMS가 없다.** 두 파일의 sha는 명세 152행 값과 같다(001cf38c, 88788261).

**[기록] R-14. 1062행 "고정 표의 명세 시점" 판단은 실측과 맞는다.**
- 고정 표에 실제 설정 이름 묶음(a), 설정별 R15 나빠짐 플래그(b), D 줄의 조건 읽기와 줄 전체 침범 두 필드(c)가 있다. 앞 감사에서 확인했다.
- 사전 재현의 64행 재계산 차이도 0이다.
- "control 확인" 부분은 파일 근거가 `handback_spec_rev6_final.md`뿐이다.

**[기록] R-15. 사전 재현은 affinity 0xfffffff(P+E)에서 돌았고 commands가 114/114 같았다.** 배치(placement)가 정체성이 아님을 보탠다.

**[기록] R-16. 사용자 결정 11(155행)의 "python-expert 계산 중, 결과는 따로 넘김"은 결정 원문 그대로다.** 결과는 4.2에 채워져 있다.

## 남은 빈 곳
- S(봉인본 sha): 193행, 505행, 614행
- C(실행 커밋 sha): 193행
- 그 밖에는 없다. placeholder_scan(`--pattern-set both --skip-inline-code`)은 종료 0이었고, "채울·기입·계산 중·자리" 산문도 Grep으로 따로 확인했다. 155·156·162·170행의 "자리"는 결정·이력 원문이고 결과는 채워져 있다.

## 봉인 커밋 파일 목록 (경로 직접 지정 `git status --porcelain --ignored -uall`)
- untracked, ignore 아님 → 그대로 add
  - 명세 1개
  - `ed7_design\` 아래 19개 폴더, 파일 284개: audit_preseal 2, control_v7_review 43, dynamics_v7 16, fixed_table 8, hydraulics_v7 16, hydraulics_v7_review 24, keys_seal 8, repro_a2_b46bdf8f 7, share 7, stats_v7 29, stats_v7_review 7, stats_v7_stopcond 7, suite 28, tool_6bfb2560 26, tool_9d8e78a4 7, tool_a6fc3dd5 16, tool_ad7a716e 7, tool_b46bdf8f 11
  - `j9_runs\6bfb2560\ed7_probe_a1\` 8개(README·SUMS·json)
  - `j9_runs\b46bdf8f\repro_a2\` 4개. repro jsonl 28,956,485 B는 ignore에 걸리지 않으므로 일반 add 대상이다.
  - `j9_runs\6bfb2560_LOCAL_ONLY.SHA256SUMS`
- ignore에 걸린 것
  - npz 654개(`j9_runs\6bfb2560\ed7_probe_a1\ed7_probe_t4h\`)와 npz 114개(`j9_runs\b46bdf8f\repro_a2\ed7_probe_a2_t4h\`): `.gitignore:41 *.npz`, `git add -f` 필요. probe 쪽은 파일당 0.5 MB 이하다.
  - `ed7_probe.jsonl` 1개: `.git/info/exclude:107`, LOCAL_ONLY. **LOCAL_ONLY jsonl은 이 1개뿐이다.**
- 줄바꿈 보호: 새 파일 모두 text: unset(`-text`).
- 키 생성 입력: grid_r67/r69 6개와 `confirm_b_grid192.json`은 이미 추적 중이다. V0 `main.jsonl`은 exclude:23에 걸리고 판 6부터 그랬다.
- SUMS 상태(`baseline_check sums`)
  - share 6, repro_a2_b46bdf8f 6, j9 repro 117, probe 8, tool_a6fc3dd5 15, control_v7_review 13: 모두 불일치 0, 빠진 파일 0, CRLF 0.
  - 목록 밖 파일: probe 폴더 npz 654, control_v7_review 29(하위 폴더에 자체 SUMS 있음).

## 위임 필요
- control-expert: N-1 문안(5.2 항목 확장, 4a·5.2 판정 불가 목록 확장, 4절 5 문장), M-9, R-12
- 메인: R-11(npz SUMS 줄), R-13(audit_preseal SUMS), 봉인 커밋의 `git add -f`

## 검사하지 못한 것
- ref_check는 지시대로 쓰지 않았다.
- `share_calc.py`와 `repro_compare.py`의 계산을 독립 재구현하지 않았다. 출력 상태·건수와 명세의 대조만 했다.
- T 도구는 아직 없어서 E축은 T 뒤 감사로 넘긴다.

## 실행한 검증
- 인터프리터: python-dev `-I -B` + `MKL_THREADING_LAYER=TBB`. dynamics-dev는 이번에 쓰지 않았다.
- 도구
  - seal_check `--quoted/--hash-files/--sums --check-tracked`: quoted_unresolved 138건 = 7절 cmd 112 + 개정 sha 4 + 시점·외부 값 + 41행 ad37ad0e
  - baseline_check sums × 6
  - placeholder_scan
  - source_guard snapshot/verify(입력 61개)
- 즉석 스크립트(scratchpad `verif-ed7seal2\`, 보고 전 폴더째 삭제)
  - seal 요약
  - 04_scripts ast import 닫힘 계산
- git 조회: grep, check-ignore, check-attr, status `--ignored`(경로 직접 지정), ls-files
- 블라인드 경로와 상위 루트(`j_p3_cause`·`j9_runs`·`06_analysis`·worktree 루트)를 대상으로 한 검색은 없다. Bash 파이프도 쓰지 않았다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v7.md 4d9a902a…, jp3_remedy_spec_v6.md 07a55e17…, SHA256SUMS e0d45969…, SHA256SUMS aaa00b00…, … ed7_probe_a2.jsonl d60306db…, ed7_probe_a2.progress.json 5d6b83c0…, SHA256SUMS 4a4fc7c0…, 디렉터리 목록 동일, ~$ 임시 파일 없음). 도구 출력 그대로가 아니고 가운데 sha 목록을 줄였다. folder_status unchanged, 경고 0.
- 메모리: `audit_pitfalls.md`의 기존 항목에 (h)(i)를 덧붙였다.
- 사용한 스킬: 없음
