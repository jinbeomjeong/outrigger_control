<!-- verif-protocol-auditor 리포트 원문(2026-11-10, 실행 전 다섯 번째 감사). 대상: K-2 _TCL V-2~V-7, 브랜치 k2-path2-rev8 7837531, master 5ab7ae3, k2-run 6a44ff8. 메인 세션이 편집 없이 저장. -->

**차단 0건, 실행 전 수정 1건, 확인 필요 1건** (기록 7건)

## 감사 요약
- **대상과 시점**: K-2 `_TCL` V-2~V-7의 다섯 번째 실행 전 감사입니다.
  - 브랜치 `k2-path2-rev8`의 HEAD는 `7837531`이고 추적 변경은 0입니다. master는 `5ab7ae3`입니다.
  - k2-run은 `6a44ff8`이고 locked 상태입니다. `runs` 폴더가 없으므로 결과는 0건입니다.
- **기준 문서**: 9판 모두 raw sha256이 `.sha256` 첫 토큰과 같습니다. 모두 LF, BOM 없음, `-text`입니다.
  - 원판 a3658197, rev1 5ba081c6, rev2 b3f1b41f, rev3 8bcdb0ed, rev4 82160ff5, rev5 73b87758, rev6 21268203, rev7 52d7dba9, **rev8 e20ac116**, 명세 502b0bb7
- **도구 고정**: HEAD·작업 사본·실행 전 기록 v2~v7이 모두 같습니다.
  - 경로 2 1.6 `82299dd2`
  - `d8x_recount` `d47c10e9`(LF sha 46010967 = raw)
  - 경로 1 `74d72d5e`
  - 평탄화기 `b3851190`
- **판정**: 차단 0 / 실행 전 수정 1 / 기록 7. G-S의 "차단 0" 조건은 충족합니다.
  - 다만 rev8 2.1절이 독립 확인으로 세는 항목 가운데 일부(J3 1 ms 재계산, Chrono 어댑터)는 실제로는 독립이 아닙니다(실행 전 수정 1).
  - 이 문구는 결과 전에 고치는 것을 권합니다(rev9, 코드 변경 없음). 사용자가 판정서 공개로 받아들이면 바로 시작할 수 있습니다.

## 질문별 답
1. **rev8 봉인과 시간 순서: 결과 전에 봉인됐습니다.**
   - 새 작성자 transcript: rev8.md Write 21:54:12, `.sha256` Write 21:55:15(머리 "sealed 21:55:07")
   - 커밋 `87a245f` 21:55:37(1.6 코드, 시험, rev8을 함께 넣음). `7837531` 21:58:21은 기록만 바꿨고 `k2_recount.py`는 바뀌지 않았습니다.
   - 결과는 0건입니다.
2. **R(1.6 J 계산 ↔ 규칙)**: 문턱·적용 범위가 원판 5.1(= D8x 4.1)·11절과 맞습니다(아래 대조표).
   - J1·J2 선이 YAML 9,414.58911 + 5,000 N으로 바뀌어, 경로 1(`d8x_judge.f_d8_N`, YAML)과 같아졌습니다.
   - 저장 R-a 1,102행 대조 결과는 두 가지입니다.
     - 1.5 대 1.6: 실패 항목, 항목 참거짓, 판정 불가 목록의 차이가 0행입니다(제가 따로 재현).
     - selftest-d8x: `d8x_crosscheck` 차이 0, 68 + 6 = 74, 판정 불가 0입니다.
3. **2.3절 차이 5건: 등급 영향도 거짓 통과도 없습니다.** 실제 데이터에서 작동하지 않거나, 경로 2가 더 엄격해서 G-F가 판정 불가로 갑니다(보수적).
   - **J2 범위**: `reanchor_intervals`는 기록기가 `reanchor_started` 사건으로 만듭니다(`d8x_record.py:233-245`, `k2_chrono_rows.py:543`). 그래서 두 조건은 같은 행을 고릅니다. 사건만 있고 구간이 없는 합성 행에서는 1.6만 J2 fail입니다(더 엄격).
   - **J7**: c2의 행정 사건은 모두 `<base>:<legs>` 형태라 기본 이름이 정확히 맞습니다. `FAULT_STROKE_END_X`(가상)는 경로 1 J7 / 1.6 J8로 나뉩니다. 행은 둘 다 fail이고, 실패 항목 집합이 달라 G-F 판정 불가입니다.
   - **E-2 NaN**: 1.6만 fail입니다(더 엄격). 규칙 E-9와 맞습니다.
   - **문자열 사건**: d8x 블록 사건은 `[[float, str]]`이므로(`d8x_record.py:315`) 작동하지 않습니다.
     - 탐침: `C2Event(... name='FAULT_X')` 문자열을 1.5는 놓쳤고, 1.6과 경로 1은 잡습니다.
     - `t_s=np.float64(..)` 꼴이면 1.6이 ValueError로 종료 3이 됩니다. 실제 데이터에는 없는 형식입니다.
   - **F_D8 0.11 mN**: J1 선은 경로 1과 같아졌습니다. SH-6 선은 1.6이 `9414.589 + 7000`(`k2_recount.py:71,801`)이고 경로 1은 YAML입니다. J1이 0.11 mN 폭 안에 떨어질 때만 G-F 판정 불가가 됩니다.
4. **독립성 공개: 두 transcript 모두 완전하지 않습니다.** 근거는 아래 실행 전 수정 1과 기록 a입니다.
   - 경로 2 이전 작성자: 15:50:22 `d8x_spec.py` 상수 grep이 빠졌습니다. `d8x_spec`은 `d8x_judge`가 import하는 경로 1 모듈입니다.
   - 새 작성자: 공개 내용이 transcript와 맞습니다.
     - 경로 1 파일 Read·Grep 0건입니다. `grep -rln` 출력(21:49:47)에 파일 이름 2개가 나온 것과, `ls` 출력(21:41:01)에 이름이 나온 것뿐입니다.
     - 메인 세션 지시문에도 경로 1 코드가 없습니다.
   - 공개되지 않은 반대 방향 읽기가 있습니다. 경로 1 작성자(python-expert)가 경로 2 코드를 읽었고, 두 경로 출력을 행마다 비교했습니다.
5. **실행 전 기록**: v2~v7은 `bundle`·`pool`·`steps`만 다릅니다.
   - 실측과 같은 값: rules 9판과 명세의 sha, 경로 2 blob, `j_items_via` blob과 LF sha, 경로 1 blob, 평탄화기 blob, 재실행 로그 2개 sha
   - `rules_check_scope`와 README `:193`은 정정됐습니다("rev7·rev8은 감사가 seal_check로 대조").
6. **빈 집합 관문**: 새 코드에 새 문제는 없습니다.
   - `d8x_ra_crosscheck`는 `n > 0`을 확인합니다. selftest는 `total == 74`를 확인합니다.
   - `gate_scan` warning 2건(`:386` points_check, `:1884` selftest_v5_stored)은 1.5부터 있던 것이고 판정 경로 밖입니다.
7. **바로 시작할 수 있는지**: 차단은 없습니다. 실행 전 수정 1을 rev9로 처리하거나 사용자가 받아들이면 시작할 수 있습니다.

## 발견 사항 (심각도순)

**[실행 전 수정][I] 1. 경로 1 작성자가 경로 2 코드를 읽고 출력을 비교했는데 공개되지 않았습니다. 그런데 rev8 2.1은 그 영향을 받은 부분을 "독립 확인"으로 셉니다.**
- **근거(transcript `subagents\agent-a8c7820f450c38187.jsonl`, KST)**
  - 16:05:01 `git show d98b31b:04_scripts/03_control/k2/k2_recount.py`를 scratch `k2impl\k2_recount.py.txt`로 복사했습니다.
  - 16:05:09~16:07:28 그 사본을 Grep(FIELD 지도, `series_dir`, `manifest[` 등)하고 Read했습니다. 범위는 1~200, 200~240, 285~345, 450~600, 600~680행입니다.
    - 이 범위에 J3 시계열 재계산(`t >= t_touch - 1e-9`)이 있습니다.
    - judge_row의 "J3 row != series recount → 판정 불가"와 "J3 not available"(d98b31b `:313-321`)도 있습니다.
    - v5_bundle, recount, recount_v6도 들어 있습니다.
  - 16:09:18 경로 1 판정부(`judge_tail.py.txt`)를 Write했습니다. 여기에 Chrono J3 1 ms 코드 `after_touch = t_s >= row["t_touch_s"] - 1e-9`가 들어 있습니다(현재 `k2_judge.py:1629-1632`).
  - 16:26:34·16:26:46 `compat_check.py`로 smoke 출력에서 `path1_verdict`/`path2_verdict`, SH1, SH2, J3all4, `path2_nj`/`path1_nj`를 행마다 맞대 출력했습니다.
- **기존 공개**: rev6 5절, rev7 1절(`rev7.md:31`), README `:183`은 "경로 1도 경로 2를 일부 참조(docstring, `false_latches`)"라고만 적었습니다. 세 번째 감사도 "경로 1 작성자 transcript 전수 확인 안 함"으로 남겼습니다.
- **rev8 2.1(`rev8.md:44-58`)**: "J3 1 ms 재계산", "J6 잠김(Chrono)", "J10(Chrono)" 어댑터의 두 경로 일치를 독립 확인으로 셉니다.
  - 그러나 경로 1의 해당 부분은 경로 2 1.x를 읽은 2분 뒤에 쓰였습니다.
  - 1.6 `j3_series_count`도 새 작성자가 21:41:21에 1.5(`limit 640`, series_metrics 포함)를 읽은 뒤 같은 식으로 다시 썼습니다.
  - 그래서 두 경로의 J3 1 ms 코드는 모두 경로 2 1.x에서 나왔습니다.
- **J1~J11 핵심은 그대로 독립입니다**: 경로 1은 `d8x_judge.judge_metrics`(D8x 경로 1, K-2 이전 코드)이고 경로 2는 `d8x_recount`입니다. 원판 8절이 허용한 독립 경로입니다.
- **규칙 8과의 관계**: 규칙 8은 경로 2만 제한하므로 위반은 아닙니다. 문제는 rev8이 봉인한 독립성 분류가 사실보다 강하다는 것입니다.
- **실패 시나리오**: J3(K-2가 겨냥하는 핵심 항목)의 Chrono 1 ms 창 해석에 공통 실수가 있으면 V-6 G-E가 두 경로에서 같이 틀립니다. 그러면 G-F 일치가 "독립 확인"으로 판정서에 남습니다.
- **권장 조치(시작 전, 결과 보기 전)**: control-expert(경로 2 작성자이므로 경로 1 코드는 열지 않음)가 rev9를 봉인합니다.
  - (가) 2.1에서 "J3 1 ms 재계산"과 Chrono J6 잠김·J10·필드 어댑터를 2.2 "정렬된 정의"로 옮깁니다.
  - (나) 경로 1 작성자의 읽기를 공개 표로 적습니다(위 시각, compat_check 포함).
  - (다) 기록 a(`d8x_spec`)를 더합니다.
  - 메인 세션은 실행 전 기록의 `independence_disclosure`와 README 7.2를 같이 고칩니다.
  - 판정·문턱·코드는 바뀌지 않습니다.

## 규칙↔도구 대조표 (1.6 J 항목)
| 항목 | 규칙(원판 5.1·11, D8x 4.1) | 경로 2 1.6(`d8x_recount`) | 경로 1(`d8x_judge`/`k2_judge`) | 판단 |
|---|---|---|---|---|
| J1·J2 | ≥ F_D8, J2는 H4가 돈 행 | `num_item ≥ 14414.58911`, H4 = 구간 또는 사건(`d8x_recount.py:335-338`) | YAML + 5 kN, H4 = 구간(`d8x_judge.py:176-189`) | 일치. 범위 차이는 작동하지 않음 |
| J3 | 1 ms, TOUCH 끝부터, ≤ 0 N, 0 | `j3_series_count`(`k2_recount.py:257-272`) | 하네스는 행 필드, Chrono는 `:1629-1632` | 일치. **독립 아님**(수정 1) |
| J4·J5·J6 이동 | 0.2°·120 s·210 bar | 상수 `:71-73` | `d8x_spec:83-85` | 일치 |
| J6 잠김 | 350 bar, Chrono, 필드가 있을 때 | `_chrono_j6_locked`. None이면 적용 안 함 | 항상 판정. None이면 fail(`:1637-1640`) | 기록 c |
| J7·J8·J9 | 행정 / FAULT / WARN(허용 1개) | 기본 이름 정확 비교(`:271-291`) | 접두어 비교(`d8x_judge.py:122-131`) | 실데이터에서 같음 |
| J10 | 0, Chrono | `num_item(v == 0)`. None이면 판정 불가 + fail | `in (0, False)`. None이면 fail | 행 판정은 다름(보수적) |
| J11 | 빈 목록, 하네스 | `list_item`. None이면 fail | 같음 | 일치 |
| E-2 | TOUCH 시작·끝, 이탈, READY | 끝·이탈·READY만, 유한수 확인 | 끝·이탈·READY만, None 확인 | **두 경로 모두 TOUCH 시작을 보지 않음**(기록 b) |
| E-3·E-10 | REJ 0 / 창 < 1 s면 판정 불가 | 같음 | 같음 | 일치 |

## 확인 필요
1. **실행 전 수정 1**: 둘 중 하나를 골라 주십시오.
   - (가) 결과 전에 rev9를 봉인해 J3 1 ms와 Chrono 어댑터를 "정렬된 정의"로 옮기고, 경로 1 작성자의 읽기를 공개합니다.
   - (나) rev8 그대로 시작하고, 판정서에 이 사실을 공개해 해당 일치를 독립으로 세지 않습니다.
   - (가)는 코드 변경이 없어 짧습니다. (나)는 판정서가 봉인 문구와 어긋나게 됩니다.

## 기록
- **a. rev8 1절 표의 누락**: 15:50:22 `grep -n -E "^(STROKE_EVENTS|WARN_ALLOWED|READY_LIMIT_S|ATTITUDE_LIMIT_DEG|MOVING_LIMIT_BAR|LIFT_WINDOW_MIN_S|LOCKED_LIMIT_BAR)" d8x_spec.py`가 빠졌습니다(이전 작성자).
  - 메인 세션 검색어에 `d8x_spec`(`d8x_judge.py:45`가 import)이 없었습니다.
  - 값은 규칙 문턱과 같고, 1.6의 문턱은 `d8x_recount`에서 오므로 영향은 낮습니다. rev9에 넣으면 됩니다.
  - 그 밖의 행(15:48:50~20:50:30)은 transcript와 모두 맞습니다.
- **b. E-2 "TOUCH 시작"을 두 경로 모두 보지 않습니다**(원판 `:430`). 1.5부터 같았던 정렬된 누락입니다.
  - 행에는 `k2.touch_start_s`(`k2_record.py:280`)와 Chrono `t_touch_start_s`(`k2_chrono_rows.py:616`)가 있습니다.
  - 판정 후 감사에서 None 수를 전수로 셉니다. 0이면 영향이 없습니다.
- **c. 경로 2 J6 잠김 None 처리**: 값이 None이면 적용 안 함(n/a)으로 둡니다. 1.5부터 같고, E-9 문구대로면 fail입니다.
  - 경로 1은 fail이므로 생기면 G-F 판정 불가입니다(보수적).
  - 기록기가 None을 쓰는 것은 잠김 표본이 전혀 없을 때뿐입니다(`k2_chrono_rows.py:625`).
- **d. 2.3절 표에서 빠지거나 부정확한 것**: 동작이 아니라 표 문구 문제입니다.
  - J10 None 행이 이제 `fail_items`에도 J10을 넣습니다(행은 원래 판정 불가).
  - 문자열 사건에서 1.5는 "문자열 전체를 이름으로 봄"이 아니라, 탐침에서 `FAULT_X`를 아예 놓쳤습니다.
  - SH-6 선 0.11 mN이 경로 1과 다릅니다.
- **e. T-K2-7: 닫혔습니다.**
  - 메인 세션 transcript(12:39:48Z)에서 명령에 세 시험 ID, `5ab7ae3`, 마스크 `0x0FFF0000`, `-p no:cacheprovider`가 그대로 확인됩니다. 로그 sha도 기록과 같습니다.
  - 코드 범위: `6a44ff8`→`5ab7ae3`→`7837531`에서 `03_src`, `02_params`, `04_scripts`, `05_tests`, `d8x`의 변경은 K-2 판정 도구 3개(k2_judge, k2_recount, k2_v5_flatten)와 K-2 시험 4개뿐입니다. 세 시험과 그 import 대상은 같습니다.
  - 남은 약점: 로그가 `-q`라 시험 ID가 없습니다. 다음에는 `-rA`를 권합니다.
- **f. 병합 전 정리**
  - `k2_prerun_audit4.md`가 main에 미추적으로만 있고 브랜치에 없습니다. 앞선 감사 원문처럼 이번 감사와 함께 그대로 커밋하는 것을 권합니다. `-text`가 적용되고 LF입니다.
  - main의 미추적 `gs_evidence/t_k2_7_rerun_*.out`은 브랜치 것과 바이트가 같습니다. 병합이 "untracked would be overwritten"으로 멈출 수 있습니다[추정]. 병합 전에 옮겨 두십시오.
- **g. seal_check `const_mismatch`(D8X_RECOUNT_SHA256)는 오탐입니다.** 이 상수는 규칙이 아니라 코드 해시입니다. LF·raw sha 46010967과 blob d47c10e9를 실측해 확인했습니다.

## 위임 필요
- **control-expert**(확인 필요 1에서 (가)를 고르면): rev9 봉인. 실행 전 수정 1의 (가)~(다)를 넣습니다. 경로 1 코드는 열지 않습니다.
- **메인 세션**: 실행 전 기록 `independence_disclosure`와 README 7.2 정정, audit4·audit5 원문 커밋, 미추적 로그 정리.

## 메인 세션 권고
- 시작 전: 확인 필요 1을 묻습니다. (가)면 rev9를 봉인·커밋하고 실행 전 기록을 다시 만듭니다. 그다음 `k2-path2-rev8`을 병합합니다.
  - 이 병합은 판정 도구를 바꾸므로 결과가 나오기 전이어야 합니다.
  - 병합 뒤 판정이 끝날 때까지 `04_scripts/03_control/k2/`와 `d8x/path2/`를 바꾸는 병합을 하지 않습니다.
- 판정 후 감사 몫: rev7·rev8(·rev9) seal_check, E-2 TOUCH 시작 None 수, J6 잠김 None 수.

## 검사하지 못한 것
- `d8x_recount` 작성자(D8x 경로 2)가 `d8x_judge`를 읽었는지(D8x 감사 범위)
- 경로 1 작성자 transcript의 Grep 결과 본문 전수(tool_use 입력과 scratch 사본 Read만 봤습니다)
- 단위 시험 41 + 55건 재실행(selftest-d8x만 다시 돌렸습니다)
- C축(결과 0건)

## 실행한 검증
- 인터프리터
  - python-dev `-I -B -X utf8`, `MKL_THREADING_LAYER=TBB`
  - 경로 2 확인만 dynamics-dev `conda run -n dynamics-dev python -I -B`
- verif 도구
  - `seal_check`(9판 raw 일치, `-text`, LF. `code_pin_missing` 2 = rev7·rev8 상수 없음, 기록과 같음. `const_mismatch` 1 = 오탐)
  - `gate_scan k2_recount.py`(warning 2, 이전과 같음)
- 경로 2 read-only 확인
  - `k2_recount.py selftest-d8x --out <scratch>`: ok, 74, crosscheck 차이 0
  - 1.5(`git show 5ab7ae3:`) 대 1.6 judge_row 1,102행 비교와 합성 탐침 6개
- 즉석 스크립트(scratchpad `verif\`, 보고 전에 폴더째 지웠습니다)
  - `tx.py`·`umsg.py`·`p1tx.py`·`p1cmd.py`·`mainrun.py`: transcript 3개 조회
  - `cmp15.py`: 1.5 대 1.6 비교
  - `pre_cmp.py`: 실행 전 기록 대조
- 조회: git log·diff·show·rev-parse·hash-object·check-attr·ls-files·worktree·branch, Get-FileHash, Read·Grep
- 최종 판정 직전에 다시 확인했습니다: 브랜치 HEAD `7837531`(변경 0), k2-run `6a44ff8`, `runs` 없음, master `5ab7ae3`, rev8 `:48` 문구 그대로입니다.
- 메모리 갱신: `audit_pitfalls.md`에 "반대 방향 독립성(경로 1이 경로 2를 읽음), transitive import 검색" 항목을 더했고 `MEMORY.md` 색인을 갱신했습니다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha k2_touch_creep_rules_rev1.md 5ba081c6…, k2_touch_creep_rules_rev1.sha256 fdf6d8ca…, k2_touch_creep_rules_rev2.md b3f1b41f…, k2_touch_creep_rules_rev2.sha256 2fd7dc24…, k2_touch_creep_rules_rev3.md 8bcdb0ed…, k2_touch_creep_rules_rev3.sha256 de03d989…, k2_touch_creep_rules_rev4.md 82160ff5…, k2_touch_creep_rules_rev4.sha256 735815f4…, k2_touch_creep_rules_rev5.md 73b87758…, k2_touch_creep_rules_rev5.sha256 f3e5eb8e…, k2_touch_creep_rules_rev6.md 21268203…, k2_touch_creep_rules_rev6.sha256 e31f6204…, k2_touch_creep_rules_rev7.md 52d7dba9…, k2_touch_creep_rules_rev7.sha256 9d702767…, k2_touch_creep_rules_rev8.md e20ac116…, k2_touch_creep_rules_rev8.sha256 591d35e0…, k2_touch_creep_rules.md a3658197…, k2_touch_creep_rules.sha256 6a7d3b25…, k2_dyn_spec.md 502b0bb7…, k2_commands.json ce6e04a2…, k2_expect.json ecef70d2…, k2_fields.json 0c5aafc4…, k2_manifest.json 807e3690…, k2_prelaunch_v2.json 718f6bfe…, k2_prelaunch_v3.json cb0f0a34…, k2_prelaunch_v4.json 15a71bee…, k2_prelaunch_v5.json da79d593…, k2_prelaunch_v6.json 311ba3e3…, k2_prelaunch_v7.json f937fd9f…, k2_v5_regression_keys.json f2970048…, README.md 1f995b78…, make_prelaunch.py 4dbe6e4d…, gs_chrono.out 2fc2bfee…, gs.out d397b00f…, t_k2_7_rerun_chrono.out 950b7525…, t_k2_7_rerun_dyn.out 8dcd4097…, unit_all.out 72b0484e…, k2_recount.py 1951c5ea…, k2_judge.py 1e6ad75b…, d8x_recount.py 46010967…, test_k2_recount.py 046ee2fd…, k2_prerun_audit4.md f41bec33…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
