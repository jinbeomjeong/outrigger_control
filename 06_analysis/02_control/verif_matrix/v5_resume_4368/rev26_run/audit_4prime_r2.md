# 436.8 rev26 4′ 재감사: 정오 2 반영 (판정 전) — verif-protocol-auditor, 2026-11-26

## 감사 요약
- **본 결과**
  - 원 출력(`judge_932f1fb/harness_path1`·`harness_path1_retry1`·`harness_path2`의 `*.json` 72개)은 승인받은 개수 스크립트로만 읽었다.
  - 그 스크립트는 건수와 토큰 경로, 일치한 도구 파일 이름만 출력했고, 값은 출력하지 않았다.
  - 판정서, 판정 후 감사, 436.8 저장 결과(`resume_k1`·`las_k1`·`07_results`)는 열지 않았다. 그 밖에 본 값은 합성 출력과 sha뿐이다.
- **대상**
  - T26 `335004a7`(worktree `rev26-t26`, locked)
  - 변형 3 worktree `rev26-t26x`(HEAD `4fe9a252`, 부모 = T26, 빈 커밋)
- **기준 문서**
  - rev26 `f6591836`
  - 정오 1 `5e3bf3e6`
  - 정오 2 `ec47e9d5`(`.sha256` `f840fdc0`, 6줄)
  - 부록 A r6 `excl_fields_r6.py` `ce5208a8`, 부록 B r6 `36906ff2`
  - `t26_identity.json` `e65e611c`
- **판정: 차단 0 / 실행 전 수정 2 / 기록 9.**
  - 첫 4′의 B-1은 해소됐다.
  - 정오 2 3절 점검표의 판정 전 항목은 모두 충족이다.
  - 다만 메인 할 일(W2-1·W2-2)을 끝낸 뒤에 5단계로 간다. 합성으로 만들지 못한 출력 10개가 남았으므로, 정오 2 3절에 따라 메인이 사용자 확인을 받아야 한다.

## 발견 사항 (심각도순)

### [실행 전 수정][I] W2-1 `rev26_run/erratum2_tests/test_r6_out.json`이 CRLF(242줄)라 E2-8 기대와 어긋난다
- **근거**
  - 정오 2 E2-8(:64)은 conda export 두 파일만 `i/crlf`로 허용하고, "그 밖의 `rev26_run/` 파일은 원문 그대로 `i/lf w/lf attr/-text`"라고 정한다.
  - 작업 트리 바이트를 세어 보니 CRLF가 있는 `rev26_run` 파일은 셋이다: conda export 둘(580·380)과 `erratum2_tests/test_r6_out.json`(242).
  - `check-attr`가 `unset`이라 커밋하면 `i/crlf w/crlf`가 된다.
- **영향**: 판정에는 영향이 없다. 기록 보호 점검(정오 2 3절 기록 보호 행)이 커밋 뒤 불일치로 나온다.
- **권장 조치(메인)**
  - 이 파일을 커밋하기 전에 다음 셋 가운데 하나를 고른다: 커밋에서 빼고 다른 폴더(예: `audit_preseal`류)로 옮긴다 / 판정서에 E2-8 예외로 공개한다 / 만든 사람이 LF로 다시 만든다.
  - 이 파일은 정오 2 봉인 목록에 없다.

### [실행 전 수정][I] W2-2 메인 정리·커밋이 남아 있다(첫 4′ W-3 그대로)
- **메인 추적 트리**가 깨끗하지 않다(`git status --porcelain --untracked-files=no`): ` M .claude/agents/paper-reviewer.md`, ` M .gitattributes`, ` M 00_docs/decision_log.md`
  - 경로 1 `Assert-CleanTree 'start'`(`run_judgement_path1_rev26.ps1:73~79`)가 멈춘다.
- **`.gitattributes`**
  - 작업 트리에 HEAD 대비 `+` 6줄이 있다: E1-5 3줄과 E2-10 3줄. 미커밋이다.
  - 정오 1·2, `rev26_e2_fixed/**`, `rev26_run/**`도 모두 미추적이다.
  - 대상 24개의 `check-attr`는 모두 `unset`이고, ignore에 걸린 것은 0이다.
- **권장 조치**: 아래 "5단계 전 메인 할 일" 순서를 따른다.

### [기록] R2-1 정오 2 봉인: 충족
- **`.sha256`**
  - 6줄, LF, BOM 없음이다. 줄 순서가 정오 2 4절 4와 같다.
  - 각 줄의 sha가 파일 raw sha와 모두 같다: `.md` `ec47e9d5`, `excl_fields_r6.py` `ce5208a8`, `excl_fields_r5_to_r6.diff` `273c3715`, `list_diff_r5_r6.py` `e08f5c36`, `rev26_excluded_fields_r6.json` `36906ff2`, `list_diff_r5_r6_stdout.json` `721f4d5f`.
  - 정오 본문에 적힌 세 sha(r6 스크립트, diff, list_diff 도구)도 같다.
- **r5→r6 diff 재현**
  - `rev26_fixed/excl_fields_r5.py` 대 `rev26_e2_fixed/excl_fields_r6.py`를 difflib로 다시 비교했다. 변경 줄 15개가 봉인된 diff의 변경 줄과 같다. r6은 327줄이다.
  - 규칙상 변경은 `SAME_RUN_DIGESTS = {("harness_path2","p2v5c_merge.json"): {("parts","[]","sha256")}}`와 `classify`의 2줄뿐이다(`excl_fields_r6.py`, diff :26·:29~32).
- **`list_diff_r5_r6.py` 재실행**
  - 봉인된 두 목록에 다시 돌렸다(목록만 읽음, 원 출력은 읽지 않음). 종료 0이다.
  - 결과 JSON은 봉인된 `list_diff_r5_r6_stdout.json`과 완전히 같다.
    - `checks` 6개 모두 참
    - `d_files` [68, 68], `d_entries` [1020, 1021], `d_by_cat_r6` {F 172, I 106, NM 87, NT 9, S 647}, `c_entries` [13, 13]
    - 더해진 행은 `harness_path2/p2v5c_merge.json [["parts","[]","sha256"],"I"]` 하나뿐
- **`rev26_fixed/**` 14파일**: T26 blob = HEAD blob = 작업 트리 바이트이고 status 0줄이다. 바뀌지 않았다.
- **T26 판정 도구가 부록 A·B를 읽는가**: WT `verif_matrix/scripts`, `path2`, `path2_v5c`, `04_hydraulic/coupled`의 `*.py`에서 `excl_fields|rev26_fixed|excluded_fields|rev26_e2_fixed`를 찾았다. 0건이다(정오 2 머리말 주장 확인).

### [기록] R2-2 원 출력 쪽 도구 sha 잎 개수 점검(rev26:155, 정오 2 3절): (d) 범위 0건, 충족
- **방법**: 사용자 승인 "judge_932f1fb 원 출력에 값 비출력 개수 스크립트 허용"에 따라 실행했다.
  - 원 출력 `*.json` 72개(68 + d 제외 파일 4)의 잎을 부록 A 토큰 경로로 만들었다.
  - 부록 B r6의 I·S·F 행(접두 일치)을 뺐다.
  - 남은 문자열 잎의 64자리 16진 부분열을 `git show 932f1fb:<허용 목록 29파일>`의 raw·LF·CRLF sha(서로 다른 값 58개)와 대조했다.
- **(d) 범위(부록 B d 목록이 덮는 68파일)**
  - 비교 잎 299,488개, 64자리 16진 잎 2,290개
  - **도구 sha와 같은 것 0건**
- **(d) 범위 밖(참고, 멈춤 대상 아님)**: 모두 57건
  - `harness_path1/head_check.json :: blobs/[]/M4`·`R4` 각 14, `harness_path1_retry1/head_check.json` 같은 꼴 28
    - (g)가 다룬다(rev26:173 "바뀌지 않은 파일의 M4·R4는 원 값, 바뀐 파일은 T26 blob").
  - `harness_path2/u3.json :: tool_sha256` 1
    - (a)(b)가 다룬다. 키 집합과 G-5·G-6 목록을 비교하고, 이 키는 비교하지 않는다.
  - 이 파일들은 부록 B d 목록이 다루지 않는다(`SKIP_D_FILES`).
- **출력 공개**: 건수, 위 토큰 경로, 일치한 도구 파일 이름·꼴만 출력했다. 값은 출력하지 않았다.

### [기록] R2-3 정체성 필드 덮음 변형 1~3(r6 규칙): 충족. 부록 A 규칙으로 지워지지 않는 차이 0
- **실행**
  - 합성 메인 트리 하나로 실행본 꼴(경로 1: cwd = 합성 메인, 도구 = worktree; 경로 2: cwd = worktree, `--data-root` = 합성 메인)을 세 번 돌렸다.
  - 변형 1: T26 worktree, 토큰 `judge_rev26_335004a`, 22:55:41~22:58:09
  - 변형 2: 같은 worktree, 다른 출력 폴더 `judge_rev26_9999999`, 22:58:30~23:02:27
  - 변형 3: `rev26-t26x`(다른 절대 경로, HEAD `4fe9a252`, 토큰 `judge_rev26_4fe9a25`), 23:02:27~23:05:52
- **비교**
  - 각 쪽은 `excl_fields_r6`의 `Rules`·`classify`로 자기 커밋·토큰·창, `--main-root` = 합성 메인, `--checkout-root` = 자기 worktree를 써서 I·S·F를 지우고 NT·NM을 정규화했다.
  - 변형 1과 2, 1과 3을 대조했다(58파일씩).
- **결과**
  - 파일 집합 차이 0, 잎 차이 0(두 쌍 모두)
  - B-1의 3잎 `p2v5c_merge.json :: parts/[]/sha256`은 세 쪽 모두 r6에서 I로 분류된다.
  - 각 쪽의 merge `parts[].sha256`은 같은 폴더 파트 파일 raw sha와 3/3 같다(E2-11 (5)의 합성 확인).
  - NM 문자열에 worktree 루트(`rev26-t26`·`rev26-t26x`)가 남은 곳: 세 쪽 모두 0
  - 비교 대상 잎의 도구 sha 일치는 세 쪽 모두 `harness_path1/head_check.json :: blobs/[]/M4·R4`뿐이다((g) 대상, (d) 제외 파일).
  - 합성 h11 출력의 `las_k1` 문자열 0(4′ :161)
  - 경로 1 출력의 `--data-root`·`--las-k1-dir` 0
  - 경로 2 출력의 `--data-root` 쌍은 `PAIR_FLAGS` I로 빠진다(차이 0이 그 결과).
  - 변형 3 경로 1 `head_check.json`: `head` = `expected_head` = `4fe9a252`, `diff_exit` 0, `exit_code` 0. 경로 2 harness `head_check.head` = `4fe9a252`
  - 두 worktree 모두 `status --porcelain --ignored` 0줄이었다(전후). `__pycache__`도 남지 않았다.
- **합성 범위(첫 4′보다 넓음)**
  - 경로 1: tool 출력 45/55. `family_table.json`은 도구가 만들지 못해 합성 대체물을 넣었고 비교에서 뺐다.
    - 이번에 새로 만든 출력: `log_errors_run_harness`, `import_check`, `overlap_steps`, `h11`, `x16_records`, `u3_judge`, `keyset_h7`, `keyset_grid_*` 4개
  - 경로 2: 13/14(`d1.json` 없음)

### [기록] R2-4 합성으로 끝내 만들지 못한 출력 10개: 목록과 정적 검토 근거
| 출력 | 합성에서 멈춘 이유 | 정적 검토 근거([추정]) |
|---|---|---|
| 경로 1 `family_table.json` | 저장 원본 sha 대조(`resume_k1_steps.stored_source` :316~330)라 합성 불가 | 표에 루트·시각이 없다(`resume_k1_family.py` :289~296, :337~348). 경로 1 판정 도구에 `datetime` 사용 0건 |
| 경로 1 `anchor_map.json` | v5 `las/las_T*.jsonl` 등 저장 파일 꼴 필요 | `resume4368_judge.py`에 `datetime`·`time.time` 0건. 같은 실행 출력의 sha를 적지 않는다 |
| 경로 1 `k1_class.json`·`r4_lists.json` | anchor_map 없음 / 줄 구조(KeyError `case`) | `family_table` sha를 적는다(:1162, :3607). 표가 결정적이라 원 출력과 같을 것으로 본다 |
| 경로 1 `u3_judge_k1.json` | v4 파일 구조(KeyError) | `datetime` 0건. v4 입력은 추적 파일이고 diff 0(첫 4′ R-5) |
| 경로 1 `u9_judge.json`·`stage1_judge.json` | 줄 구조(KeyError `case`) | `datetime` 0건. 입력 sha만 적는다 |
| 경로 1 `h8_noise_judge.json`·`h6_judge.json`·`h6_r79_judge.json` | r79 판정기 하위 실행 출력 없음 | 같은 실행 출력 sha(`h6_judge_4368.py:288`, `h8_noise_judge_4368.py:517~519`)의 대상인 r79 판정 출력에 경로·시각이 없다(`r79_sensor_judge.py:540~545, 817~819`). `judge_run.last_line`에는 출력 토큰이 들어 I다. `command`는 인자 목록이다 |
| 경로 2 `d1.json` | 합성 h1 꼴(KeyError `level`) | `p2_d1.py:637` `created`(I). argv를 적지 않는다. `--repo`는 표준 출력에만 쓴다(`p2_x16.py:627~629`) |

- 원 출력 쪽 R2-2가 이 10개 원 출력도 포함한 68파일에서 도구 sha 잎 0건을 보였다. 그래서 도구 sha 경로의 불일치 위험은 낮다.
- 그 밖의 run 의존 필드는 5단계에서 처음 드러날 수 있다. 정오 2 3절에 따라 5절 실패 처리 3행을 따르고, 남은 목록이 0이 아니므로 메인이 사용자 확인을 받은 뒤 5단계로 간다.

### [기록] R2-5 `t26_identity.json`(새 sha `e65e611c…`): 충족
- raw sha는 `e65e611c8bbe04131ad9ade778da463e019ef0f60e910970e1af1e4f6c6a2f7e`로 지시값과 같다.
- 내장 `checks` 16개가 모두 참이다. `open_items`는 `[]`다.
- `input_basis_crosscheck`
  - 출처는 `audit_4prime.md` `c95bf8a3`, 145~170행이다.
  - 표 열 4개와 7행이 감사 R-5 표와 셀 단위로 같다.
  - 아래 확인 14줄도 글머리표만 정규화하면 같다.
- 첫 4′ 재계산값 26개가 모두 들어 있다: 실행본 2, M4·retry1·경로 2 M4, 외부 도구 4, 규칙 4, `v5_options`, conda export 2, `test_rev26_p2`, 정오 1·2와 각 `.sha256`, r6 스크립트·목록, 환경 기준값 2, T26.
- 표지 칸(실행본 raw sha, `v5_options`, 정오 1)의 값도 일치한다. 실행본 두 파일 raw sha는 이번 source_guard에서도 `3516ea5e`·`a6f0b90c`다.

### [기록] R2-6 E2-8 줄바꿈 기대(커밋 전이라 `check-attr`만): 충족(W2-1 제외)
- 정오 2 두 파일, `rev26_e2_fixed/**` 5개, `rev26_run/**` 17개, 모두 24개의 `check-attr text`는 `unset`이다. ignore 0이다.
- master 작업 트리 `.gitattributes`에 E2-10 세 줄과 `rev26_run/** -text`가 있다.
- conda export 두 파일은 CRLF 580·380이다(E2-8 예외와 같음). identity에 `conda_list_export_file_eol` = CRLF 원 바이트가 적혀 있다.

### [기록] R2-7 실행 환경 기준값: 있음
- `env_inventory_baseline_4prime`: python-dev `b32b783e`, dynamics-dev `c27f109f`. `recheck_at_prep_e2`도 같다.
- `environment.python-dev.nondeterminism_disclosure` 문장이 있다.
- `env_inventory_before`·`after`는 null 자리다(5단계 때 채움, E2-7).

### [기록] R2-8 정오 2의 해석 항목(E2-4·E2-5·E2-6)은 첫 4′ R-7·R-8과 맞는다
- E2-4((e) = "S-2가 나옴"), E2-5(최상위 태그 차이 → S-13 위험을 판정서 기록), E2-6(범위 밖 실행 2건)을 첫 4′ R-7·R-8과 대조했다. 어긋나지 않는다.
- 두 경로 넘김 대상 [정의] 문장은 없다(정오 2 2절). 그래서 두 경로 독립 조건에는 영향이 없다.

### [기록] R2-9 `rev26-t26x` 처리
- 변형 3 확인은 끝났다. 지금 worktree는 깨끗하다(무시 파일 포함 0줄).
- 메인이 `git worktree remove`로 지운다. 프로젝트 규칙상 브랜치는 남긴다.
- 5단계 실행본은 `rev26-t26`만 가리키므로 남아 있어도 판정 영향은 없다.

## 4′ 점검표 (정오 2 3절)
| 항목 | 결과 |
|---|---|
| (새) 정오 2 봉인: `.sha256` 6줄 = raw sha, list_diff 재실행 종료 0·기대값, `rev26_fixed/**` 불변 | 충족(R2-1) |
| 도구 sha 잎(:155): 원 출력 쪽, 부록 B r6, 값 비출력 | (d) 범위 0건, 충족(R2-2) |
| 정체성 필드 덮음(:156~162), r6, 변형 1~3 | 충족(R2-3). 못 만든 출력 10개는 목록과 정적 근거(R2-4) |
| `t26_identity.json` 새 sha, `input_basis_crosscheck` = R-5, 재계산값 | 충족(R2-5) |
| 기록 보호(E2-8) | `check-attr` 충족. `test_r6_out.json` CRLF(W2-1) |
| 실행 환경 기준값 | 있음(R2-7) |
| 나머지(첫 4′ R-1~R-6·R-13) | 다시 하지 않음(정오 2 3절). 해당 sha는 R2-5에서 재확인 |

## 5단계 진행 가부
- **조건부 가능.** 판정 전 4′ 항목에 차단은 없다.
- 아래 1~5를 끝내야 한다.
- 합성 미산출 10개(R2-4)가 남았으므로 사용자 확인을 받는다(정오 2 3절 "남은 목록이 0이 아니면 메인이 사용자 확인을 받은 뒤 5단계로 간다").

## 메인 세션 권고 (5단계 전 남은 메인 할 일, 순서대로)
1. `rev26-t26x` worktree를 지운다(`git worktree remove`, 브랜치는 남김).
2. W2-1: `rev26_run/erratum2_tests/test_r6_out.json`의 처리 방식을 정한다(옮김 / 공개 예외 / LF 재생성).
3. 메인 추적 트리를 정리한다: `.claude/agents/paper-reviewer.md`, `00_docs/decision_log.md`
4. 커밋한다.
   - (①) master `.gitattributes`(작업 트리 `+` 6줄)를 먼저 넣거나 같은 커밋에 넣는다.
   - (②) 정오 1·2의 `.md`·`.sha256`, `rev26_e2_fixed/**` 5개, `rev26_run/**`(identity `e65e611c`, 실행본 둘, conda export 둘, prep 보고, handback, `audit_4prime.md`, 이 보고 `audit_4prime_r2.md`)
   - 커밋 뒤 `git ls-files --eol`을 확인한다: conda export 둘은 `i/crlf w/crlf attr/-text`, 나머지는 `i/lf w/lf attr/-text`. raw sha가 identity·봉인 값과 같아야 한다.
   - `rev26_e2_fixed/`에는 봉인 뒤 파일을 더하지 않는다.
5. 5단계 직전
   - `git -C <rev26-t26> status --porcelain`가 0줄인지 보고 `wt_status_before`에 적는다(보조로 `--ignored`).
   - 두 env `stable_inventory`를 다시 계산해 `env_inventory_before`에 적는다.
   - 메인 추적 트리 0줄을 확인한다.
   - 다른 에이전트가 메인에 쓰는 작업을 멈춘다(지금 ed8 구현 등이 돌고 있다. 합성 실행 중 CPU 부하 71%를 관측했다).
   - 이어서 경로 1·2 실행본과 `compare_r4.py`를 돌린다. 끝난 직후 `wt_status_after`와 `env_inventory_after`를 적는다.
6. 6단계(판정 후 감사)에서 E2-11 (5)를 원·새 출력 각 쪽에서 건수로 대조한다.

## 검사하지 못한 것
- R2-4의 10개 출력을 합성으로 끝까지 돌리지 못했다(정적 검토만).
- 실데이터에 기대는 항목(IND_LAS 줄 controller, 최상위 태그와 v5 태그의 일치, u6 쌍이 넷뿐인지)은 5단계에서 드러난다(첫 4′ R-8·R-9, 정오 2 E2-5).
- `ls-files --eol` 점검: 커밋 전이라 하지 않았다.

## 실행한 검증
- **인터프리터**
  - 대조·해시·개수: python-dev `-I -B`(MKL_THREADING_LAYER=TBB)
  - 합성 경로 1: dynamics-dev `python.exe -I -B`(x16·log_errors·sidecars는 python-dev)
  - 합성 경로 2: `conda run -n dynamics-dev python -I -B`
- **즉석 스크립트**(scratchpad `verif-rev26-4p2\`, 보고 전 폴더째 삭제)
  - `seal2_check.py`: 봉인, diff 재현, list_diff 재실행(`--out` scratchpad), 속성, identity sha
  - `identity_check.py`, `ib_check.py`, `ib2.py`: identity 값·R-5 대조
  - `orig_sha_count.py`: 원 출력 개수, 값 비출력
  - `build_synth.py`: 경로 1 시험 `_build_inputs` 재사용, 손으로 만든 파일
  - `augment.py`
  - `run_synth.py`: 실행본 꼴, 경로 1 52단계 + 경로 2 14단계, 3변형, 그 가운데 변형 1은 보강 뒤 다시 실행
  - `compare3.py`: `excl_fields_r6` Rules·classify import
  - `merge_self.py`
- **git 조회**: cat-file, ls-tree, diff, status(`--ignored`), check-attr, check-ignore, ls-files --eol, worktree list, log, config
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha v5_resume_4368_rules_rev26.md f6591836…, v5_resume_4368_rules_rev26.sha256 e74aeca9…, v5_resume_4368_rules_rev26_erratum1.md 5e3bf3e6…, v5_resume_4368_rules_rev26_erratum1.sha256 27f98bae…, v5_resume_4368_rules_rev26_erratum2.md ec47e9d5…, v5_resume_4368_rules_rev26_erratum2.sha256 f840fdc0…, excl_fields_r6.py ce5208a8…, excl_fields_r5_to_r6.diff 273c3715…, list_diff_r5_r6.py e08f5c36…, rev26_excluded_fields_r6.json 36906ff2…, list_diff_r5_r6_stdout.json 721f4d5f…, excl_fields_r5.py bee9eee7…, rev26_excluded_fields_r5.json 9e1831f5…, t26_identity.json e65e611c…, run_judgement_path1_rev26.ps1 3516ea5e…, run_judgement_path2_rev26.ps1 a6f0b90c…, audit_4prime.md c95bf8a3…, conda_list_export_dynamics-dev.txt 6cca76b4…, conda_list_export_python-dev.txt d5d66884…, .gitattributes fab6c64f…, 디렉터리 목록 동일, ~$ 임시 파일 없음) · 경고: 형제 항목 수정 시각만 변경 1건(.git)
  - `.gitattributes` sha `fab6c64f`는 작업 트리의 정오 2 줄이 들어간 판이다. 감사 중에는 바뀌지 않았다.
- 사용한 스킬: 없음

## 공개 (행위 그대로)
- **연 문서(Read)**
  - 정오 2 전체, `prep_report_e2.md` 전체
  - `excl_fields_r5_to_r6.diff` 전체, `list_diff_r5_r6.py` 전체
  - `erratum2_tests/test_r6.py` 1~25행
  - T26 `u3_judge_k1.py` 120~125행
- **스크립트가 읽은 것**
  - `t26_identity.json`(구조·sha)
  - `audit_4prime.md` R-5 절
  - 두 부록 B 목록(list_diff, 개수 스크립트의 제외 행)
  - 원 출력 72개(개수 스크립트만, 값 비출력)
  - M4 실행본 두 개(허용 목록 이름 추출)
- **Grep**
  - WT 도구 폴더 4곳(부록 이름, `datetime` 사용, 개수 모드)
  - `u3_judge_k1.py`(v4 파일 이름)
  - 합성 출력과 로그 폴더(scratchpad)
- **합성 실행에서 메인 `_fixed` 사본을 썼다(원 출력 아님)**
  - 매니페스트 사본(`fa0b72bf`): 합성 출력 폴더로 바이트 복사
  - sidecar 사본: 합성 `resume_k1`에 실행
- **판정 도구 실행**
  - T26·t26x 판정 도구를 합성 고정물(scratchpad)에만 돌렸다. 436.8 저장 결과에는 0회다.
  - `family_table.json`은 도구가 만들지 못한 단계 뒤에 합성 대체물을 넣어 다음 단계(k1_class·r4_lists)를 시도했고, 비교에서는 뺐다.
- **규칙 위반 1건**: scratchpad 스크립트 하나(`ib2.py`)를 PowerShell `Set-Content`로 썼다(Write 도구를 써야 했음). scratchpad 안이고, 지웠다.
- **진행 확인**
  - 백그라운드 실행 1건(변형 2·3)의 진행을 Glob·Grep·`Get-CimInstance`(내 명령줄 패턴 조회만)로 확인했다.
  - 종료한 프로세스는 없다.
- **열지 않은 것**: 블라인드 경로(worktree 사본 포함), 판정서, 판정 후 감사, 436.8 저장 결과, 부록 B 값(목록은 행·범주로만 처리)
- **지운 것**: scratchpad `verif-rev26-4p2\` 전체
