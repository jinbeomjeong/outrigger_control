# 436.8 rev26 정오 1 반영: 실행본 대조와 t26_identity.json 재작성 (python-expert, 2026-11-26)

## 0. 요약
- 정오 1 4절 1~2를 마쳤습니다.
  - 경로 1 실행본(메인 수정본 `3516ea5e…`)을 M4·M4_retry1 두 기준과 대조했습니다. 결과는 정오 3절 표와 같습니다.
  - 경로 2 실행본(`a6f0b90c…`)은 고치지 않았고, M4 대비 diff가 그대로입니다.
  - ps1_lint는 두 실행본 모두 종료 0입니다(error 0·warning 0·info 0).
  - `t26_identity.json`을 새로 만들었습니다. 내장 점검 9개가 모두 참입니다.
- 판정 도구·하위 명령·실행본을 실행한 횟수는 0입니다.
- **새로 확인 필요 1건**: python-dev의 `conda list --export` 출력이 실행할 때마다 달라집니다. 같은 패키지의 dist-info가 둘씩 있어서입니다. 그래서 stdout sha를 환경 정체성으로 쓸 수 없습니다(5절 1).

## 1. 만든·옮긴 파일 (`…\v5_resume_4368\rev26_run\`)
| 파일 | raw sha256 | 비고 |
|---|---|---|
| `t26_identity.json` | `b96dce6ec60aa8d72474d675117b26701ccecd28126b74bf67fa6548f5382ed7` | 새로 씀, LF |
| `superseded\t26_identity_draft0_c7298f64.json` | `7903fa6250ea7f893adf242456dcbeff81c62b7b0518a98f0a16532773fe413c` | 첫 초안(`prep_report.md`의 identity)입니다. 덮어쓰지 않고 옮겼습니다. 필요 없으면 메인이 지워 주세요 |

- 그대로 둔 파일
  - `run_judgement_path1_rev26.ps1` `3516ea5e…`(메인 수정본)
  - `run_judgement_path2_rev26.ps1` `a6f0b90c…`
  - `conda_list_export_dynamics-dev.txt` `6cca76b4…`
  - `conda_list_export_python-dev.txt` `d5d66884…`(5절 1 참고)
- 작업 중 실패한 시도가 두 번 있었습니다. 둘 다 같은 이름 `t26_identity.json`으로 썼다가 지웠습니다.
  - 첫째: 점검 1개가 실패한 판(python-dev export 불일치)이었습니다.
  - 둘째: 메모 문장을 고치기 전 판이었습니다.
  - 남은 것은 위 최종본 하나입니다.

## 2. 실행본 diff 대조 (정오 3절 표)
| 실행본 | 기준 | 기준 sha | 다른 줄(기준 줄 번호) | 정오 3절과 일치 |
|---|---|---|---|---|
| 경로 1 `3516ea5e…` | M4 | `868fa7b7…` | 13·14·21·26·27·46·109·116·153·154·155 | 예 |
| 경로 1 | M4_retry1 | `c93cfc5c…` | 13·14·21·26·27·46·109·116 (153~155 바이트 같음) | 예 |
| 경로 2 `a6f0b90c…` | M4 | `9690f2de…` | 23 뒤 `$WT` 1줄 삽입. 교체 24·25·26·35·38·39·57~59·61~63·66~71·327·332·336·340·349·362·369·379·384·430 | 예 |

- 대조 방법: 선언한 삽입 줄을 빼고 줄마다 맞대어 다른 줄 집합이 표의 집합과 같은지 보았습니다. unified diff 전문과 sha도 identity에 넣었습니다.
  - 경로 1 vs M4: `b84f9090…`
  - 경로 1 vs retry1: `e886ef29…`
  - 경로 2 vs M4: `ee1bfcac…`
- 경로 1의 21행은 `judge_rev26_$(…)/harness_path1`입니다(retry1의 `_retry1` 아님, E1-1).
- 줄 수: 경로 1은 LF로 끝나는 줄 206개로 M4와 같습니다. 정오의 "207줄"은 끝 빈 원소까지 센 값이라 같은 파일입니다. 경로 2는 456줄(M4 455 + 1)입니다.
- 토큰 grep(대소문자 무시): `tag-mode`·`imua`·`pytest`가 두 실행본 모두 0건입니다(㉡).
- `$AllowListPath2`
  - 15개이고, 값 15개가 모두 `git cat-file blob T26:<파일>` raw sha256과 같습니다.
  - 표에 `test_rev26_p2.py`는 없습니다.
  - 개수 관문 문자열은 `15 expected`로 그대로입니다.
- ps1_lint: `python-dev -I -B ~/.claude/tools/verif/ps1_lint.py <두 실행본> --format json`을 실행했습니다. **종료 0**, 파서 AST, 발견 0이고 `case_variant_overwrite`도 없습니다.

## 3. t26_identity.json 요약
- **`checks`(모두 참)**
  - 실행본이 정오 3절과 일치하고 `--tag-mode`가 0건
  - `$AllowListPath2` 15개 = T26이고 `test_rev26_p2` 없음
  - ps1_lint 두 실행본 종료 0
  - 정오 1 sha
  - RD-1 4 대체 조건 1·2·3
  - `v5_options.py` CRLF 잎 = `d2b903a2…`
  - dynamics-dev export 재확인 일치
- **`erratum1`**
  - 경로 `…/v5_resume_4368_rules_rev26_erratum1.md`, raw sha `5e3bf3e6…`(기대값과 같음)
  - `.sha256` 파일 sha `27f98bae…`, 안에 위 sha가 들어 있음
  - 미추적이고 T26에 없음(정오 머리말대로)
- **`location_note`**: `rev26_run/t26_identity.json`, 정오 1 E1-4입니다.
- **`stage5_runners`**: 두 실행본의 sha·EOL·줄 수·토큰 수, 경로 1은 `vs_M4`와 `vs_M4_retry1`, 경로 2는 `vs_M4`, 153~155 = retry1 참.
- **`allow_list_path2`**: 15행입니다. `not_listed_new_file_t26_blob_raw_sha256` = `3e8166b2132a530d4330f6c150fb594eb0c12f87fbd3e4c2df9ee8cc76ca2877`을 유지했고 정오 값과 같습니다.
- **`changed_files`**: 37개, 목록 sha `101cead4…`(첫 초안과 같음), `test_rev26_p2.py` 포함.
- **`master_gitattributes_e1_5`**
  - E1-5 세 줄이 작업 트리 `.gitattributes`에 있습니다. HEAD `2715230e`에는 아직 없습니다(`committed: false`).
  - `rev26_run` 파일 셋과 정오 파일 둘의 `check-attr text`는 `unset`입니다.
  - `ls-files --eol`은 미추적이라 커밋 뒤 4′가 볼 몫으로 적었습니다.
- **그대로 다시 계산해 넣은 것**: worktree(HEAD = T26, locked, `core.autocrlf=true` system), 규칙 4개 파일, 외부 도구 네 개 sha, `v5_options`. 값은 첫 초안과 같습니다.
- **`open_items`**: 정오 1로 닫힌 1~3은 `closed_items`로 옮겼습니다(각 E1 항목 근거). 새로 1건을 넣었습니다(아래 5절 1).
- **null로 둔 것**: `wt_status_before`·`wt_status_after`·`input_basis_crosscheck`(4′ 몫)는 null 자리 그대로입니다.

## 4. 실행 환경 기록
| env | Python | 저장 export sha | 오늘 재확인 | 순서 무관 목록 sha(`stable_inventory`) |
|---|---|---|---|---|
| dynamics-dev | 3.12.15 | `6cca76b4…` | 같음 | `c27f109fa9015b5d38f5a8fe7edf72e136d6bdac0aff0f969704222844283cc8`(conda-meta 477, dist-info 348, 중복 0) |
| python-dev | 3.13.15 | `d5d66884…` | **다름**(`49d6cf4b…`, `faad5d83…`) | `b32b783e582f26d708e9d9d6d3db57e458364f7129fc69d4677af8818906a817`(conda-meta 280, dist-info 236, 중복 4) |

- `stable_inventory`는 이번에 새로 넣은 칸입니다. `<env>\conda-meta\*.json` 이름과 `Lib\site-packages\*.dist-info` 이름을 정렬해 LF로 이은 sha256입니다.

## 5. 확인 필요
1. **python-dev `conda list --export`가 재현되지 않습니다.**
   - 원인: site-packages에 dist-info가 둘씩 있는 프로젝트가 4개 있습니다.
     - onnxruntime 1.30.0/1.31.0
     - platformdirs 4.11.12/4.13.0
     - protobuf 7.35.1(conda)/7.36.2(pip)
     - soupsieve 3.0.3(conda)/2.10(pip)
   - 연달아 3번 돌렸더니 protobuf·soupsieve 줄이 바뀌었습니다. dist-info 수정 시각은 9-29·10-14이고 오늘 바뀐 설치는 없습니다. 그래서 실제로 import되는 판도 모호합니다.
   - 규칙 rev26 :109는 "`conda list --export` sha"를 실행 환경 정체성으로 정합니다. 그런데 python-dev에서는 이 값이 실행마다 달라질 수 있어, 5단계 전후 대조에 쓰면 거짓 불일치가 납니다.
   - 가능성 (가): python-dev는 `stable_inventory.sha256`으로 대조한다. 정오나 4′ 판단이 필요합니다.
   - 가능성 (나): export sha를 그대로 쓰되 비결정성을 판정서에 공개한다.
   - dynamics-dev는 중복이 0이고 재확인 결과도 같습니다.
   - 중복 dist-info 정리(pip 쪽 제거 등)는 환경 변경이라 하지 않았습니다. 하려면 사용자 결정이 필요합니다.
2. **메인 checkout 추적 트리**: `.gitattributes`(E1-5, 미커밋)가 수정 상태로 더해졌습니다. `paper-reviewer.md`·`decision_log.md`도 여전히 수정 상태입니다. 경로 1 `Assert-CleanTree 'start'` 전에 커밋이나 정리가 필요합니다(정오 4절 5).

## 6. 공개 (행위 그대로)
- **연 파일**
  - 정오 1 전체(Read)
  - `.sha256` 파일 내용(Get-Content)
- **해시만 계산**
  - 두 실행본, retry1, 정오 파일·`.sha256`
  - git blob: 허용 목록 29개, 규칙 4개 파일(부록 B json 포함, 바이트만 해시하고 내용 출력 없음), `v5_options.py`, `test_rev26_p2.py`
- **git 명령**
  - 메인: `diff -- .gitattributes`, `check-attr`, `status --porcelain -- rev26_run 정오`, `rev-parse`·`log`·`diff --name-status`·`diff -U0 .gitattributes`(T26), `ls-files -- <정오>`, `worktree list --porcelain`
  - worktree: `config`·`check-attr`·`ls-files --eol`(4개 대상 파일)
- **실행**
  - ps1_lint 1회
  - python-dev `-I -B`로 내 스크립트 2개(identity 작성은 3회 시도, 요약은 2회)
  - `conda list -n <env> --export`: identity 실행마다 env 2개, 그리고 python-dev만 수동으로 3회 더
  - 각 env의 `python -I -B -c "import sys; print(sys.version)"`
  - `Get-ChildItem`으로 python-dev site-packages의 protobuf·soupsieve dist-info 폴더 시각과 `INSTALLER`를 확인
- **열지 않은 것**: 436.8 결과 json, 판정서, 판정 후 감사, 블라인드 경로, 두 경로 코드 본문. 상위 폴더 검색은 하지 않았습니다.
- **종료한 프로세스는 없습니다.** 내가 띄운 python(PID 62336, 35132 등)은 `Wait-Process`로 기다렸습니다.
- scratchpad `python-rev26-e1\`은 지웠습니다.

사용한 스킬: 없음
