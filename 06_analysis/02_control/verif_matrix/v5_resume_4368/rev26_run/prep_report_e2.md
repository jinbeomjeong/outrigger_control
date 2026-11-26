# 436.8 rev26 정오 2 4절 5: t26_identity.json 재작성 (python-expert, 2026-11-26)

## 0. 요약
- `rev26_run\t26_identity.json`을 정오 2 4절 5대로 다시 썼습니다. 새 raw sha256은 **`e65e611c8bbe04131ad9ade778da463e019ef0f60e910970e1af1e4f6c6a2f7e`**(LF)입니다.
- 내장 `checks`는 16개이고 모두 참입니다. 이전 9개에 이번에 7개를 더했습니다.
- 실행본·외부 도구·규칙 파일·정오 1·`v5_options`·conda export·`test_rev26_p2` 해시 23개를 다시 계산했습니다. 모두 이전 판 값과 같습니다. `rev26_fixed/**`는 T26·HEAD와 diff 0입니다.
- 판정 도구·하위 명령·실행본 실행은 0회입니다. 부록 B r6 목록은 해시만 계산했습니다.

## 1. 파일
| 파일(`rev26_run\` 아래) | raw sha256 | 비고 |
|---|---|---|
| `t26_identity.json` | `e65e611c8bbe04131ad9ade778da463e019ef0f60e910970e1af1e4f6c6a2f7e` | 새로 씀 |
| `superseded\t26_identity_e1_b96dce6e.json` | `b96dce6ec60aa8d72474d675117b26701ccecd28126b74bf67fa6548f5382ed7` | 정오 1 판. 옮기기만 하고 바이트는 그대로 |
| `superseded\t26_identity_draft0_c7298f64.json` | `7903fa62…` | 첫 초안(그대로) |

- 새 identity의 `supersedes` 칸에 이전 판의 경로와 sha를 적었습니다.
- 스크립트는 시작할 때 이전 판 sha가 `b96dce6e…`인지 먼저 확인합니다.

## 2. 더한 칸·바꾼 칸
- **`input_basis_crosscheck`(E2-9)**
  - `audit_4prime.md`(sha `c95bf8a3…`, 정오 2 값과 같음) 145~170행의 R-5 절을 그대로 옮겼습니다. 표 열 4개, 행 7개, 아래 확인 줄 14개입니다(:153 추적 입력 확인과 NM의 WT 루트 잔존 0 포함).
  - 사람이 다시 쓰지 않았습니다. 감사 파일에서 기계로 옮겼습니다.
  - `input_basis_crosscheck_note`가 이 출처를 가리킵니다.
- **실행 환경(E2-7·E2-8)**
  - `environment.python-dev.nondeterminism_disclosure`에 공개 문장을 넣었습니다. 내용은 중복 dist-info 4개, 캡처마다 다른 sha, export sha는 기록으로만 둔다는 것, 전후 대조는 `stable_inventory`로 한다는 것, python-dev 단계는 이 넷을 import하지 않는다는 감사 R-10입니다.
  - 두 env에 `conda_list_export_file_eol` = CRLF 원 바이트를 적었습니다. 실측은 각 580/580, 380/380 CRLF입니다.
  - `env_inventory_before`·`env_inventory_after`: method는 기존 `stable_inventory.method`입니다. `command`·`time`과 env별 `sha256`·`conda_meta_count`·`dist_info_count`는 null 자리로 두었습니다(5단계 때 채움).
  - `env_inventory_baseline_4prime`
    - 4′ 기준값: python-dev `b32b783e…`, dynamics-dev `c27f109f…`
    - 지금 다시 계산한 값(`recheck_at_prep_e2`)도 둘 다 기준값과 같습니다. 건수는 280/236, 477/348입니다.
- **open_items / closed_items**
  - python-dev 항목을 `closed_items` 4번으로 옮겼습니다. 닫은 근거는 `정오 2 E2-7로 닫음 …`입니다.
  - `open_items`는 빈 목록입니다.
- **`erratum2`(㉣)**
  - `.md` raw `ec47e9d5…`이고 기대값과 같습니다.
  - `.sha256` raw `f840fdc0a7fc51d2ce4219e1f916ba0b52685e15150a270ec6f877bba92d7c61`, 6줄이고 `.md` sha를 적고 있습니다.
  - `.md`와 `.sha256` 모두 미추적이고, `in_t26: false`입니다.
- **`appendix_a_r6`(㉣)**: 다섯 파일의 raw sha가 모두 `.sha256` 줄과 같습니다. 정오 본문에 sha가 적힌 세 파일도 본문 값과 같습니다. 다섯 파일 모두 미추적입니다.

  | 역할 | 파일 | sha256 |
  |---|---|---|
  | r6 스크립트 | `excl_fields_r6.py` | `ce5208a8…` |
  | r5→r6 diff | `excl_fields_r5_to_r6.diff` | `273c3715…` |
  | list_diff 도구 | `list_diff_r5_r6.py` | `e08f5c36…` |
  | 부록 B r6 목록 | `rev26_excluded_fields_r6.json` | `36906ff25fe6437c865f6269fe6a308cfa80acc154bac06228b28dbf6f49c443` |
  | list_diff 결과 | `list_diff_r5_r6_stdout.json` | `721f4d5f9508a8a549fe8a118e28f52c659ab20ae6ee5416b035329e61e3b948` |

  - list_diff 결과 파일 내용은 E2-2 기대값과 같습니다.
    - `status` ok, `checks` 6개 모두 참
    - `d_files` [68, 68], `d_entries` [1020, 1021], `d_by_cat_r6` {F 172, I 106, NM 87, NT 9, S 647}, `c_entries` [13, 13]
  - r5 두 파일은 `r5_files_kept`로 적었습니다.
- **`recheck_against_previous`**: 해시 23개의 기록값·현재값·같음 여부와 `rev26_fixed` diff(작업 트리와 HEAD 모두 T26 대비 0)를 담았습니다.
- **그대로 둔 칸**: `stage5_runners`, `allow_list_path2`(15행, `test_rev26_p2.py` 칸 `3e8166b2…`), `ps1_lint`(종료 0), `erratum1`, `location_note`, `wt_status_before`·`wt_status_after`(null 자리), RD-1 4 조건 기록은 정오 1 판 그대로입니다.

## 3. 재계산 확인 (이전 판 대비, 23개 모두 같음)
- 실행본: 경로 1 `3516ea5e…`, 경로 2 `a6f0b90c…`
- 기준 실행본: M4 `868fa7b7…`, M4_retry1 `c93cfc5c…`, 경로 2 M4 `9690f2de…`
- 외부 도구: log_errors `3b9a8eac…`, sidecar 사본 `0962f639…`, manifest 사본 `fa0b72bf…`, compare_r4 `8ff3d32b…`
- 규칙 4개 파일: T26 blob과 worktree raw sha 각 2개, 모두 기존 값과 같음(`f6591836…`, `e74aeca9…`, `bee9eee7…`, `9e1831f5…`)
- 정오 1: `.md` `5e3bf3e6…`, `.sha256` `27f98bae…`
- 기타: worktree `v5_options.py` `d2b903a2…`, conda export `6cca76b4…`·`d5d66884…`, `test_rev26_p2.py` blob `3e8166b2…`

## 4. 확인 필요·메인 권고
- 확인 필요: 없음.
- 메인 권고
  - 새 sha `e65e611c…`를 고정해 4′ 재감사에 넘겨 주십시오.
  - `rev26_run\`에는 다른 작업자가 만든 파일도 있습니다: `erratum2_tests\`(파일 4개), `erratum1_handback_full.md`, `erratum2_handback_full.md`, `prep_report_e1.md`. 커밋할 때 E2-8 줄바꿈 점검 대상인지 메인이 판단해야 합니다. 저는 이 파일들을 만들거나 열지 않았습니다.

## 5. 공개 (행위 그대로)
- **Read**
  - 정오 2 전체
  - `audit_4prime.md`는 Grep으로 표제 목록을 보고, 145~170행(R-5)과 230~242행(R-10·R-11)만 읽었습니다.
  - 정오 2 `.sha256` 내용(Get-Content)
- **스크립트가 읽은 것**
  - `list_diff_r5_r6_stdout.json`(JSON으로 읽음, 개수·참거짓만 있음)
  - 이전 identity
  - 감사 파일의 R-5 절
- **해시만 계산**
  - `rev26_e2_fixed` 다섯 파일. 부록 B r6 목록은 내용을 열지 않았습니다.
  - 정오 2 두 파일
  - 이전 identity가 고정한 해시 23개 대상
- **git 명령**: `cat-file blob`(T26 규칙 파일·`test_rev26_p2`·정오 2 존재 확인), `ls-files --`(정오 2·`rev26_e2_fixed` 추적 여부), `diff --name-only T26 [HEAD] -- rev26_fixed`
- **파일 목록**: `rev26_e2_fixed\`, `rev26_run\`(자기 결과 확인용)
- **env 확인**: 두 env의 `conda-meta`·`site-packages` 이름 목록을 `stable_inventory`로 다시 계산했습니다. conda list는 이번에 돌리지 않았습니다.
- **열지 않은 것**: 436.8 결과 json, 판정서, 판정 후 감사, 블라인드 경로, 두 경로 코드. 상위 폴더 검색도 하지 않았습니다.
- **프로세스**: 띄운 프로세스는 python-dev 스크립트 2개(identity 작성 1회, 요약 1회)입니다. 종료한 프로세스는 없습니다.
- scratchpad `python-rev26-e2\`는 지웠습니다.

사용한 스킬: 없음
