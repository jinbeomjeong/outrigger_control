## 판 7 판정 도구 커밋 T′ 보고 (감사 차단 3건 반영)

**T′ = `60ebb4a412c0b9eb20323efa536a35a0caa8c30b`** (브랜치 `ed7-judge`, 계보 C `8a2a52ce` → T `c91065b7` → T′). 차단 B-1~B-3과 M-1을 모두 반영했다. T′ 시험 범위 2658개가 전부 통과했고, P7-11 범위도 다시 맞다. worktree는 clean이고 lock 상태 그대로다. 병합·push는 하지 않았다.

### 1. 항목별 반영 위치
| 감사 항목 | 반영 내용 | 위치 |
|---|---|---|
| **B-1** (결정 13) | sens J-P3는 키 파일 `judged` 줄(판정 4설정)만 판정한다. 기록 6설정의 J-P3·③ 조건은 기록으로만 남긴다(`J-P3_record_settings`). `judged` 플래그가 그 줄의 설정과 어긋나면 setting_defect다 | `jp3_ed7_judge._sens_jp3` |
| **B-2** (결정 14) | 12a `t12 --bundle VBM`(새 쪽)과 12b `judge`(6.3.7 (4) VBKM 줄)에 ③ rev 7 조건 판정을 더했다. 대상은 판정 등급(ideal·normal) 줄이다. 침범은 실패, T4h `T4H_ARRAYS` 결측은 setting_defect, 조건 읽기 0은 "해당 없음(기록)"이고 rev 6 J-P3 판정은 그대로다. j9main·sens·confirm·cases는 지금처럼 0이면 판정 불가다 | `jp3_ed7_judge.r79_condition_entry`·`r79_condition_judgement`·`r79_condition_basis`·`is_judged_grade`, `jp3_tjr_judge_ed7.add_condition`, `jp3_12b_judge_ed7._with_condition`·`judged_condition_lines` |
| **B-3** (정오 1-8) | t8에 VBM·VBM0 줄 전체의 6.1 정체성 대조를 넣고, 실제 태그(`controller_tags`)와 기대 태그를 기록한다. 다르면 setting_defect다 | `judge_t8` |
| **B-3** (정오 1-9 조건 1~3) | 새 하위 명령 `l1ref --runs L1_VBM0 L1_VBM L1a_VBM0 L1a_VBM`. 각 run 옆 `<stem>_t4h`를 쓴다 | `judge_l1ref`·`r79_line_identity`·`identity_source_values` |
| **R-10** | ③ 켬 줄에 ③ 기록이 없고 head-only 선언도 없으면 정체성 문제로 잡는다 | `ed7_identity_problems` |
| **M-1** (결정 15) | probe-repro의 P7-3 해시 불일치와 P7-9 행 불일치를 둘 다 setting_defect로 바꿨다(실패 아님). 시험도 고쳤다 | `judge_probe_repro`, `_probe_hash_match` |
| **R-11** | 단계 소속 검사에 T4h 폴더를 포함했다: 12b는 `--vbk0-t4h`·`--vbk-t4h`, 12a는 `--new-t4h`·`--base-t4h` | 두 래퍼의 `STEP_FILE_OPTIONS` |
| **M-5** | `--out`은 judge worktree 밖, 단계 폴더 밖에 둔다는 전제를 적었다 | `jp3_ed7_judge` help·docstring, 두 래퍼 docstring |

`l1ref` 하위 명령의 동작:
- 줄마다 6.1 항목 전부를 줄이나 T4h meta에서 대조한다. 대상은 태그, `p1_patch`, `lsb_components`·`lsb_settings`·`probe_d6_settings`이다.
- ③ 켬 줄은 기록 rev 7·10902ffd와 `run_extend_start_revision` 7을, ③ 끔 줄은 기록이 없음을 본다.
- 두 출처 모두에 없는 항목은 setting_defect다.
- 항목별·출처(행·meta)별로 읽은 값의 digest와 대표값, 개수를 `identity_sources`에 기록한다. ③ 기록은 정체성 키만 남긴다.

### 2. 검증
- **P7-11 범위**(`t_scope_check.json`, `in_scope`):
  - C 대비 변경 경로는 9개이고 모두 `04_scripts/`·`05_tests/` 아래다.
  - 실행 경로 목록(155개 파일) 가운데 바뀐 파일은 0개, `03_src` tree는 C와 같다.
  - 시험 2건(blob 동일, 닫힘 동일)도 통과했다.
- **T′ 시험 범위**(84개 파일, 새 시험은 `test_ed7_judge.py` 안에 있음):
  - worktree_tests로 E 코어 0x0FFF0000에서 돌렸다(19:06~19:57).
  - **2658 통과, 실패·오류·건너뜀·xfail 0.**
  - 기준 목록 `571f42a1…` 대조 `pass`: 새 실패 0, 핵심 미통과 0, 새 건너뜀 0.
  - HEAD는 시작·끝 모두 `60ebb4a4`, is_clean은 둘 다 True다.
  - probe 모듈 `outrigger_sim`·`jp3_ed7_judge`는 worktree에서 import됐다.
- `test_ed7_judge.py`는 70개 시험이다. 새로 넣은 것:
  - B-1: 봉인 키 파일 460줄 배치 꼴 합성 시험. 판정 행이 104(기대값)이고, 기록 설정 줄의 침범은 status에 들어가지 않는다.
  - B-2: 조건 항목 단위 시험(사건 시각 없음, 배열 결측, 침범, 통과). 12a는 판정 등급 줄만 본다. 12b는 decide→judge를 끝까지 돌렸다: 조건 배열이 없으면 setting_defect, 배열이 있고 사건 시각이 없으면 pass + "해당 없음" 기록.
  - B-3: t8의 VBM0 다른 태그 → setting_defect(태그 기록 포함). l1ref는 끝까지 실행했을 때 pass, 두 출처 모두 결측이면 setting_defect.
  - R-10, R-11 시험.
- **생산자 꼴 끝까지 실행 재실행**: b46bdf8f 재현 줄로 probe-repro·confirm·sens·j9main·cases를 돌렸고 모두 통과했다. R-10을 더한 뒤에도 실데이터의 정체성 결함은 0이다.
- **도구 점검**(clean T′, b46bdf8f 줄): 해시 114/114, 고정 표 차이 0이다. setting_defect의 원인은 초안 `spec_edition` 78줄뿐이다(C 줄은 10902ffd여야 하므로 기대한 결과).
- ruff·codespell: 0건.

### 3. 근거
`C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\judge_commit_60ebb4a4\` — `SHA256SUMS` 13개 항목(재귀), sha256 `36f223e7a1ea22dc01c0de466a981e30b82b23f1935ce4ec9b81327abb40e0c9`.
- 범위: `t_scope_check.json`, `t_test_range.txt`, 실행 경로 목록 사본
- 시험: `suite_T\`(junit, suite_judgement, suite_record, worktree_tests.md)
- 도구 점검: report와 stand-in `.done`
- 스크립트 3개, 커밋 메시지

scratchpad `python-ed7Tp`는 지웠다.

### 4. 확인 필요
1. **B-1의 260 계산이 실측과 다르다.** 합성 시험에서 460줄 전체를 넣어도 판정 행은 104였다. `j_p3_inputs.ED7_JUDGED_SETTINGS`(REV5 판정 설정 표)가 이미 기록 6설정을 `rev7_record_only`로 돌리기 때문이다. 이번 변경은 범위를 명시해 의도를 고정한 것이고 판정 결과는 바뀌지 않는다. 감사 원문 수정 여부는 verif-protocol-auditor·메인이 정한다.
2. **B-2는 사실상 항상 "해당 없음"이다.** r79 줄(12a dg3, 12b VBKM)에는 사건 시각 `t_event_s`가 없다. ed6 l1ref 실출력의 줄·T4h meta 키 이름으로 확인했다(g6·g8·ref 하네스, `base`에 사건 시각 없음). 그래서 사건 시각을 줄의 `t_event_s`로만 읽고, 없으면 상태 `no_event`(조건 읽기 0)로 둔다. 실행 단계를 거치면 조건 항목은 사실상 늘 "해당 없음(기록)"이 된다(T4h 배열 결측은 여전히 setting_defect).
   - r79 하네스의 무엇을 "사건 시각"으로 볼지(예: g6 weak-leg 사건, 12b rod fault 주입 시각)는 규칙 문면이 정해야 한다. 대리 시각은 만들지 않았다.
   - control-expert 정오 문면이나 사용자 결정이 필요하다.
3. 조건 판정은 판정 등급(ideal·normal) 줄만 대상으로 했다. rev 6 판정 집합의 등급 규칙에 맞춘 것이고, conservative·old_worst 줄은 조건에서 빠진다.
4. `l1ref`는 run steps에 없다. 판정 단계에서 메인이 `--runs`(l1ref 단계 폴더의 json 4개)와 `--step-done <l1ref.done>`을 주고 돌린다.

### 5. 공개(블라인드 절차)
- 감사 원문, 정오 1, `79495405/l1ref_a1/L1_VBL.json`은 경로를 지정해 읽었다. l1ref 파일은 줄·`base`·`r79` 키 이름, 하네스 종류 수, T4h 배열 이름만 출력했고 값은 출력하지 않았다.
- 블라인드 경로와 판 6 `selection.json`은 열지 않았다. 상위 루트 대상 검색은 하지 않았다.

### 6. 위임 필요
- T′의 P7-11 재감사(verif-protocol-auditor)는 메인이 맡긴다.
- 확인 필요 2(r79 사건 시각)는 control-expert에 넘긴다.

사용한 스킬: 없음
메모리 반영안: 없음(이번 실행은 앞 보고의 `tool_edition_wrapper_patch.md`로 충분하다)
