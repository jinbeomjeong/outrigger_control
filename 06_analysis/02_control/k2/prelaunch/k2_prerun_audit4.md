<!-- verif-protocol-auditor 리포트 원문(2026-11-10, 실행 전 네 번째 감사). 대상: K-2 _TCL V-2~V-7, master 5ab7ae3, k2-run 6a44ff8. 메인 세션이 편집 없이 저장. -->

**차단 1건, 실행 전 수정 2건, 확인 필요 2건** (기록 6건)

## 감사 요약
- **대상과 시점**: K-2 `_TCL` V-2~V-7, 실행 전 네 번째 감사입니다.
  - master는 `5ab7ae3`입니다(추적 변경 0).
  - 실행 checkout k2-run은 `6a44ff8`이고 locked 상태입니다. 추적·미추적 변경 0, `runs` 폴더 없음, 결과 0건입니다.
- **기준 문서**: 8판 모두 raw sha256이 `.sha256` 첫 토큰과 같습니다. 모두 LF, BOM 없음, `-text`입니다.
  - 원판 a3658197, rev1 5ba081c6, rev2 b3f1b41f, rev3 8bcdb0ed, rev4 82160ff5, rev5 73b87758, rev6 21268203, **rev7 52d7dba9**, 명세 502b0bb7
- **도구 blob**: HEAD·작업 사본·실행 전 기록이 모두 같습니다.
  - 경로 1 `74d72d5e`
  - 경로 2 1.5 `e1e16a9c`
  - 평탄화기 `b3851190`
  - 래퍼 `fab7664b`
- **판정**: 차단 1 / 실행 전 수정 2 / 기록 6. **아직 바로 시작할 수 없습니다.**
  - 세 번째 감사의 차단·수정 항목은 대부분 닫혔습니다.
  - 그러나 rev7의 "사실 그대로" 공개에 빠진 읽기가 있습니다. 경로 2 작성자가 경로 1이 행 판정(J1~J11)에 쓰는 함수 `d8x_judge.judge_metrics`를 읽었습니다(차단 1).
  - 이 누락은 세 번째 감사가 transcript를 `k2_judge.py`로만 검색한 데서 왔습니다. rev7은 그 목록을 그대로 옮겼습니다.

## 세 번째 감사 항목 처리 상태

| # | 항목 | 상태 | 근거 |
|---|---|---|---|
| 차단 1 | 경로 2 작성자가 경로 1 코드를 읽음 | **부분 닫힘** | rev7 1절의 시각·행위는 transcript와 모두 맞습니다(17:37:23/26/32/35, 17:50:06→17:50:13 Edit, 17:51:09, 19:37:58·19:38:02→19:38:32 rev5 Write). 다만 목록이 빠졌습니다 → 새 차단 1 |
| 수정 1 | `flat_main` 기대값 | **닫힘** | 내용은 아래 세 곳이 같습니다. 래퍼는 `<sidecar> --git-dir DIR -- cmd`를 받고(`run_with_identity.py:108-116`), 평탄화기는 `--arm-dir/--out-dir/--checkout`을 받습니다(`k2_v5_flatten.py:534-536`). 판정 커밋 자리 표시는 기록 c |
|  |  |  | ① `rev7.md:44-68`: sidecar 이름, `--git-dir` main, HEAD = 판정 커밋(평탄화기 b3851190), clean, env, E 마스크, rc 0, 래퍼 명령 |
|  |  |  | ② `prelaunch k2_prelaunch_v*.json` `flat_main_sidecar` |
|  |  |  | ③ README 9.1 |
| 수정 2 | SH-6 J2 | **닫힘** | 경로 1 `k2_judge.py:540-548`(5d28db4)는 J1이 없을 때만 결측으로 세고, J2는 숫자이고 H4가 있을 때만 근접 판정합니다. 경로 2 `k2_recount.py:618`은 H4가 없으면 J2 = None이므로 판정이 같습니다(`:709-714`, `:1597-1602`). crc2 E-1은 problems에 남습니다(`k2_judge.py:946-951`) |
| 수정 3 | T-K2-7 | **근거는 생겼지만 미충족** | 6443 passed / 135 skipped / **3 failed**(`unit_all.out` 72b0484e, 실측 일치) → 실행 전 수정 1 |
| 기록 e·f | G-F 대조 단위, 이어 돌리기 | **닫힘** | rev7 4·5절. P_post r79 tcl 단계의 마스크 `0xFFFF`가 `k2_commands_filled.json`과 같습니다 |

## 발견 사항 (심각도순)

**[차단][I·T] 1. rev7 1절의 독립성 공개에서 경로 2 작성자가 읽은 경로 1 행 판정 코드가 빠졌습니다. 이 부분은 rev7 2절의 "정렬된 정의" 목록에도 없습니다.**
- **근거(transcript)**: `C:\Users\jinbeom\.claude\projects\C--workspace-outrigger-control\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\subagents\agent-af7124b8517fd4c3a.jsonl`의 tool_use 기록입니다(KST).
  - 15:48:50 `git ls-files | grep d8x_recount|d8x_judge|d8x_record`
  - 15:49:17 `grep -n -E "def (row_items|judge_row|_j[0-9]|_items)|J7|STROKE|WARN_PROBE|REJ_|J1_window|t_crawler_off|120|0\.2\b" 04_scripts/03_control/d8x/d8x_judge.py`
  - **15:49:22 `Read d8x_judge.py offset 115 limit 90`**. 이 범위는 115~204행이고 J1~J11·E-8 정의표(136-150)와 `judge_metrics`(166-190)가 들어 있습니다. 그 4분 뒤인 15:53:36에 경로 2 `k2_recount.py` 첫 판을 Write했습니다.
- **이 코드가 경로 1인 근거**
  - 경로 1은 행 J 항목을 이 함수로 계산합니다: `k2_judge.py:47` `import d8x_judge  # row J items`, `:438`·`:451` `d8x_judge.judge_metrics`.
  - 원판 8절(`k2_touch_creep_rules.md:352`)은 "경로 1의 출력과 코드는 읽지 않는다. J 항목 계산은 D8x 경로 2(`d8x_recount.py`)의 함수를 써도 된다(경로 1과 독립)"입니다. `d8x_recount.py`는 실제로 있습니다(`06_analysis/02_control/d8x/path2/`).
  - 경로 2 docstring도 "does not import or read … `d8x_judge.py`"라고 적었습니다(`k2_recount.py:4`). 프로그램 동작으로는 맞지만 작성 과정으로는 맞지 않습니다.
- **그 밖에 공개되지 않은 읽기(덜 중요함)**
  - 17:37:07 `sed -n 1,80p k2_record.py` + 키 grep. 경로 1이 V-6 SH-1을 이 모듈로 계산합니다(`k2_judge.py:48`, `:1678`). 하네스 기록기이므로 필드 이름 확인으로 볼 여지는 있습니다.
  - 18:10:58 `git show c77ecf5:…/k2_v5_flatten.py | sed -n 1,70p`. 경로 1 입력을 만드는 평탄화기입니다.
- **rev7 문구**: "세 번째 감사가 transcript에서 확인한 행위는 다음과 같다"(`rev7.md:18`)는 1절 제목 "사실 그대로"(`:13`)보다 범위가 좁습니다. 2절 목록(`:36-41`)에는 J1~J11 행 판정이 없습니다. 그래서 지금 문구대로면 판정서는 G-A·G-B·G-C·G-E의 행 판정 일치를 **독립 확인**으로 셉니다. rev7 5절(`:82`)도 행별 결과와 실패 항목 집합을 맞댑니다.
- **실패 시나리오**: J 항목에 공통 해석 실수(경계 `>=`/`>`, J2 H4 조건, E-8 창)가 두 경로에 같이 들어가 있으면, G-F가 일치해도 그 일치가 독립 근거로 판정서에 남습니다. 이는 핵심 판정의 독립성을 사실보다 강하게 적는 것입니다.
- **차단으로 둔 이유**: 세 번째 감사 차단 1과 같습니다. 이번 사실은 사용자가 결정할 때 몰랐던 것입니다. J 항목은 V-5 결과 종류보다 핵심이므로 사용자가 다시 고를 수 있어야 합니다(새 경로 2, 또는 J 항목만 `d8x_recount` 기반으로 다시 쓰기). 그 선택지는 결과가 나오기 전에만 있습니다(원판 8절).
- **풀어 주는 최소 조치**(시작 전)
  - (가) 사용자에게 알리고 같은 결정("공개하고 경로 2 유지")을 적용할지 확인합니다(AskUserQuestion).
  - (나) 유지라면 결과 전에 rev8을 봉인합니다.
    - 1절에 15:48:50~15:49:22 `d8x_judge.py` 읽기, 17:37:07 `k2_record.py`, 18:10:58 평탄화기를 더합니다.
    - 2절 "정렬된 정의"에 **행 판정 J1~J11·E-8(`judge_metrics`)**과 SH-1(`k2_record`)을 더합니다.
    - 실행 전 기록(`independence_disclosure`, README 7.2)도 고칩니다.
  - (다) 경로 2 작성자의 transcript 전체를, 경로 1이 import하는 모든 모듈 이름으로 다시 검색해 목록이 완전한지 확인합니다. 대상: `d8x_judge`, `k2_record`, `v5_options`, `k2_v5_flatten`, `run_with_identity`, `acc_judge` 등. 이번 감사의 검색어는 `k2_judge|k2_v5_flatten|d8x_judge|k2_record.py|5d28db4|74d72d5e|k2-path1|agent-a8c7820f`였습니다.
- 담당: 메인 세션(질문, 기록), control-expert(rev8. 경로 2 작성자이므로 경로 1 코드는 열지 않음).

**[실행 전 수정][I] 1. T-K2-7 "기존 단위 시험 전부 통과"를 글자 그대로는 충족하지 못했습니다(3 failed). 원인은 코드가 아니라 환경·데이터 의존으로 보이지만, 그 근거가 일부는 전언입니다.**
- **실패 3건 판단**
  1. `test_d8x_chrono_rows::test_earlier_rows_meta_argv_unchanged`: 데이터 의존이 **코드로 확인됩니다**.
     - k2-run에는 `07_results`가 있지만 그 안에는 `states_L1R`(72파일)뿐입니다.
     - `v5_stage3_las_rows.results_root()`(`v5_stage3_las_rows.py:51-58`)는 `07_results` 폴더가 있으면 main checkout으로 돌아가지 않습니다. 그래서 저장 S9 batch를 못 찾고, `hash_comparable`·`est_pool_s`·`stored_argv_check` 같은 행 필드가 바뀝니다.
     - 이 키들은 `STORED_RESULT_ROW_KEYS`(`d8x_case_hashes.py:44`)에서 빠지지 않습니다. 실패 내용이 `missing`이 아니라 `changed`인 것도 이것으로 설명됩니다. 기록의 "저장 S9 결과가 없음"은 사실이지만 원인은 정확히 이 폴백입니다.
  2. `test_d8x_diag::test_rerun_gives_the_stored_command_hash`: 환경 의존이 **[추정]**입니다.
     - docstring은 "needs dynamics-dev (numba)"입니다(`test_d8x_diag.py:4-5`).
     - 같은 성격의 T-K2-2(K-2 끔 D8x 대표 5행 `commands_sha256` = 저장값)는 dynamics-dev에서 통과했습니다(`gs.out`).
     - 그러나 "passes in dynamics-dev"라는 기록(prelaunch `T-K2-7_full_unit_tests.failures[1]`)에는 로그가 없습니다.
  3. `test_hydraulics_flow_limit_run::test_coupled_batch_rows_and_resume`: 데이터 의존이 **확인됩니다**. k2-run에 `07_results/S9/batch_FINAL-REP_20261030_223359/P3b_J1_B_top_Fs4/result.json`이 없고 main checkout에는 있습니다.
- **기록의 부정확한 점**: "fails the same way at ba3adcc (before K-2)"라고 적었지만, `ba3adcc`는 "K-2 TOUCH creep latch in C2" 커밋 자체입니다. K-2 이전이 아닙니다. 또 이 재현에도 로그가 없습니다.
- **코드 범위**: 6a44ff8→5ab7ae3 사이에 `03_src`·`02_params`·`04_scripts/02_chrono`·`touch_phase`·`d8x`는 바뀌지 않았습니다. 바뀐 것은 K-2 시험 4파일뿐입니다.
- **영향**: G-S 조건입니다(원판 7절 "구현 시험 9.2 통과", 실패하면 "실행 안 함"). 등급에는 영향이 없습니다.
- **권장 조치(메인 세션, 시작 전, 약 2~3분, E코어)**: 세 시험을 각각 전제가 맞는 곳에서 돌리고 로그를 `gs_evidence`에 넣습니다.
  - 1·3은 main checkout(5ab7ae3, 같은 코드, `07_results` 있음)에서 Chrono-dev로 돌립니다.
  - 2는 main checkout 또는 k2-run에서 dynamics-dev로 돌립니다.
  - 통과하면 T-K2-7을 "환경·데이터 전제가 맞는 곳에서 전부 통과"로 기록합니다. 실행하지 않으려면 확인 필요 1에서 사용자가 이 해석을 받아들여야 합니다.

**[실행 전 수정][S·I] 2. 실행 전 기록은 "rev7 대조는 경로 1과 감사가 한다"고 적었지만, 경로 1에는 rev7 봉인 대조가 없습니다.**
- 근거
  - `seal_check --const k2_judge.py:RULES_REV7_SHA256` → `const_not_found`
  - `code_pin_missing`: 경로 1이 고정한 판은 원판~rev6뿐입니다(`k2_judge.py:53-69` `SEALED_RULES`, docstring "path 1 checks the original and rev1 .. rev6 seals")
  - `grep 52d7dba9|rev7` in `04_scripts/03_control/k2` → 0건
  - 그런데 README `:187`과 prelaunch `path2.rules_check_scope`는 "rev7 … is checked by path 1 and the audits"라고 적었습니다.
- 실패 시나리오: 판정 때 rev7(G-F 대조 단위, `flat_main` 기대값)이 바뀌어도 두 경로 모두 멈추지 않습니다. 봉인 자체는 지금 맞습니다.
- 권장 조치(둘 중 하나)
  - 기록을 "rev7 봉인은 판정 전·후 감사가 `seal_check`로 대조한다"로 고칩니다(메인 세션). 이 경우 경로 1 blob은 바뀌지 않습니다.
  - 경로 1에 rev7 상수를 더합니다(python-expert). 이 경우 새 blob을 고정해야 합니다.
- 차단 1의 rev8을 쓰면 rev8도 같은 방식으로 처리해야 합니다. 경로 1·2 모두 rev8 상수가 없게 됩니다.

**[기록]**
- **(a) 판정 항목과 문턱**: 바뀌지 않았습니다. rev7은 수치를 새로 정하지 않습니다. 1e-9는 원판 8절 값 그대로입니다. 5절 "V-5 공통 = 한 값(경로 1은 OR)"은 대조 형식만 정한 것입니다.
- **(b) 남은 경로 차이(세 번째 감사 기록 a·b·c)**
  - 끔 팔 오류 행 범위, 잡음 키 대조, crc2 처리입니다.
  - crc2는 경로 1이 E-1 건수를, 경로 2가 키 sha를 전역 판정 불가로 봅니다. 대상이 다르지만 둘 다 보수적입니다.
  - 생기면 G-F 판정 불가이고 거짓 통과는 없습니다.
- **(c) `flat_main` HEAD 기대값**: `{JUDGE_COMMIT}` 자리 표시입니다(prelaunch `flat_main_sidecar.head`). rev7은 "실행 전 기록에 적은 커밋"이라고 했지만 지금 기록에는 값이 없습니다. 평탄화기 blob은 고정돼 있으므로 판정 전 재생성 직전에 커밋을 적으면 됩니다.
- **(d) 봉인 시각**: rev7 `.sha256` 머리는 "sealed 20:51:13"입니다. transcript에서 rev7.md Write는 20:51:11, `.sha256` Write는 20:51:22, 커밋 `a16d06a`는 20:51:33입니다. 결과는 0건이므로 **결과 전 봉인이 확인됩니다**.
- **(e) gate_scan(judge·recount·flatten)**: warning 4건입니다. 세 번째 감사와 같고 모두 오탐입니다. 경로 1 변경(SH-6·crc2)은 빈 집합 문제를 새로 만들지 않았습니다.
- **(f) 실행 전 기록의 묶음 간 일관성**: `k2_prelaunch_v2~v7`은 `bundle`·`pool`·`steps`만 다릅니다. 다음 값은 모두 실측과 같습니다.
  - rules 8판 sha
  - gs 로그 3개 sha
  - k2-run `c2.py` f58ee42b
  - 세 도구 blob
  - 셸에 `OUTRIGGER_*`·`ACC_*` 없음
  - `k2` 미병합 브랜치 없음

## 규칙↔도구 대조표 (이번 변경분)

| 항목 | 규칙 | 경로 1 (74d72d5e) | 경로 2 (e1e16a9c) | 판단 |
|---|---|---|---|---|
| SH-6 결측 | J1 없음만(`rev6.md:34`) | `:540-543` | `:709-710`, `:1597-1598` | 일치 |
| SH-6 J2 근접 | H4 행만 | `has_h4` 및 숫자(`:546-547`) | 숫자(H4 없으면 None, `:618`) | 일치 |
| crc2 E-1 | 원판 E-1 3,822에 포함 | problems(`:946-951`) | 키 sha → 전역 판정 불가 | 기록 b |
| rev7 봉인 | – | **없음** | 없음(사용자 결정) | 실행 전 수정 2 |
| `flat_main` | rev7 3 | 입력 검사 아님(README `:269`) | 읽지 않음 | 판정 후 감사가 확인 |

## 확인 필요
1. **차단 1**: 경로 2 작성자가 경로 1의 행 판정 함수(`d8x_judge.judge_metrics`)를 읽은 사실이 새로 확인됐습니다. 같은 결정("공개하고 유지", 그리고 J 항목을 정렬된 정의로 표기)을 적용할지, 새 경로 2(또는 J 항목만 `d8x_recount` 기반으로 다시 쓰기)를 고를지 정해 주십시오. 다시 쓰는 선택은 시작 전에만 가능합니다.
2. **실행 전 수정 1**: 세 시험을 전제가 맞는 곳에서 다시 돌리지 않는다면, 3 failed를 T-K2-7 충족(환경·데이터 의존 실패 제외)으로 받아들일지 정해 주십시오. 제 판단으로는 1·3은 코드로 데이터 의존이 확인되고, 2는 [추정]입니다.

## 위임 필요
- **control-expert**(확인 필요 1에서 유지를 고르면): rev8 봉인. 1절 공개 보완(15:48:50~15:49:22 `d8x_judge.py`, 17:37:07 `k2_record.py`, 18:10:58 평탄화기)과 2절 정렬 목록에 J1~J11·E-8·SH-1을 더합니다. 경로 1 코드는 열지 않습니다.
- **python-expert**(실행 전 수정 2에서 코드 쪽을 고르면): `k2_judge.py` `SEALED_RULES`에 rev7(그리고 rev8) 상수를 더하고, 새 blob을 실행 전 기록에 고정합니다.
- **python-expert(tools/verif)**: `gate_scan.py --no-git` 종료 2(이전 감사에서 이어짐, 이번에는 재확인하지 않음).

## 메인 세션 권고
- 시작 전: 확인 필요 1을 묻습니다. rev8(또는 다른 결정)을 봉인하고 커밋합니다. 실행 전 수정 1의 세 시험을 E코어로 돌립니다. 실행 전 기록 `rules_check_scope`와 README `:187`을 고칩니다.
- 판정 전 `flat_main` 재생성 직전에 `{JUDGE_COMMIT}`을 적습니다.
- 그 밖에는 세 번째 감사 권고 그대로입니다. 판정이 끝날 때까지 `04_scripts/03_control/k2/` 판정 도구를 바꾸는 병합을 하지 않습니다. 이어 돌리기는 argv·cwd·env·마스크를 그대로 씁니다.

## 검사하지 못한 것
- 세 실패 시험의 재실행(규칙상 하네스·시험 실행은 하지 않음, 메인 세션 권고로 올림).
- 메인 세션이 경로 2 작성자에게 보낸 "정의 요약" 메시지 본문에 코드가 들어 있었는지(user 메시지 본문은 대조하지 않았습니다).
- 경로 2 작성자가 Grep·Glob 도구 결과로 경로 1 내용을 봤을 가능성은 위 검색어 범위까지만 봤습니다.
- 경로 1 작성자(python-expert) transcript 전수.
- C축(결과 0건).

## 실행한 검증
- 인터프리터: python-dev `-I -B -X utf8`, `MKL_THREADING_LAYER=TBB`. 대상 프로젝트 import는 없습니다.
- verif 도구
  - `seal_check.py --repo . "06_analysis/02_control/k2/k2_touch_creep_rules*.md" --code 04_scripts/03_control/k2 --const …k2_judge.py:RULES_REV7_SHA256 --const …:RULES_REV6_SHA256 --const …k2_recount.py:REV6_SHA256`
    - 8판 raw 일치, `-text`, LF
    - const: rev6 2/2, rev7 `const_not_found`
    - `code_pin_missing` 2
  - `gate_scan.py`(judge, recount, flatten): warning 4
- 즉석 스크립트(scratchpad `verif\`, 보고 전에 폴더째 지웠습니다)
  - `tx.py`: 경로 2 transcript tool_use 추출
  - `pre_cmp.py`: prelaunch v2~v7 비교와 sha 재계산
- 조회
  - git: log, diff, ls-tree, rev-parse, hash-object, status, worktree list, branch --no-merged
  - PowerShell: Get-FileHash, ConvertFrom-Json, Test-Path
  - Read·Grep: 규칙, 도구, 시험, `s9_batch`, `v5_stage3_las_rows`
- 메모리 갱신: `audit_pitfalls.md`에 1개 항목(공개 목록이 이전 감사 검색 범위를 그대로 옮김 → 경로 1이 import하는 모듈까지 transcript를 다시 검색, "revN 봉인을 경로 1이 대조" 주장 대조)을 더했고 `MEMORY.md` 색인을 갱신했습니다.
- 최종 판정 직전에 다시 확인했습니다: master 5ab7ae3, k2-run 6a44ff8, `runs` 없음, `d8x_judge.py:166-190` `judge_metrics`와 `k2_judge.py:438,451` 호출 그대로입니다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha k2_touch_creep_rules_rev1.md 5ba081c6…, k2_touch_creep_rules_rev2.md b3f1b41f…, k2_touch_creep_rules_rev3.md 8bcdb0ed…, k2_touch_creep_rules_rev4.md 82160ff5…, k2_touch_creep_rules_rev5.md 73b87758…, k2_touch_creep_rules_rev6.md 21268203…, k2_touch_creep_rules_rev7.md 52d7dba9…, k2_touch_creep_rules.md a3658197…, k2_touch_creep_rules_rev1.sha256 fdf6d8ca…, k2_touch_creep_rules_rev2.sha256 2fd7dc24…, k2_touch_creep_rules_rev3.sha256 de03d989…, k2_touch_creep_rules_rev4.sha256 735815f4…, k2_touch_creep_rules_rev5.sha256 f3e5eb8e…, k2_touch_creep_rules_rev6.sha256 e31f6204…, k2_touch_creep_rules_rev7.sha256 9d702767…, k2_touch_creep_rules.sha256 6a7d3b25…, k2_dyn_spec.md 502b0bb7…, k2_points_5p5_3p5.json a15cbe95…, k2_commands.json ce6e04a2…, k2_expect.json ecef70d2…, k2_fields.json 0c5aafc4…, k2_manifest.json 807e3690…, k2_prelaunch_v2.json 4056f5ff…, k2_prelaunch_v3.json c83ca042…, k2_prelaunch_v4.json 0f8ce20f…, k2_prelaunch_v5.json b6d78d6d…, k2_prelaunch_v6.json 371496ed…, k2_prelaunch_v7.json bff96c76…, k2_prerun_audit.md fe971e24…, k2_prerun_audit3.md 7a813da3…, k2_prerun_reaudit.md bb2ba773…, k2_v3_keys.txt 506b93a4…, k2_v5_regression_keys.json f2970048…, make_prelaunch.py bb89541a…, README.md 7534aae0…, regression_keys.py 31ee5cc9…, gs_chrono.out 2fc2bfee…, gs.out d397b00f…, unit_all.out 72b0484e…, aff.json 68bb2fb1…, build_runners.py 7182fb37…, k2_commands_filled.json 402a1ef3…, k2_placement_20261110.json f349ce4e…, k2_sched_lanes.json 1b5fc744…, p_main_done_markers.txt ac277f80…, state.json 257a8ab2…, steps_E_pre.json b725bdfe…, steps_E_V6_off.json 1ec165c4…, steps_E_V6_tcl.json d04502cf…, steps_E_V7.json 0713920f…, steps_P_main.json 033496df…, steps_P_post.json 5dd80d49…, k2run_E_pre.ps1 5e8a85db…, k2run_E_V6_off.ps1 8c25c06e…, k2run_E_V6_tcl.ps1 cff4c587…, k2run_E_V7.ps1 e5c94ae7…, k2run_P_main.ps1 1c4c4c58…, k2run_P_post.ps1 434c109b…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
