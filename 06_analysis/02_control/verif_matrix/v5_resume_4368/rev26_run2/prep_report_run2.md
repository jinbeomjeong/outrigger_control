# 436.8 rev26 정오 3 4절 1: 2회차 실행본과 t26b_identity.json 준비 (python-expert, 2026-11-26)

## 0. 요약
- `rev26_run2\`에 2회차 실행본 두 개와 `t26b_identity.json`을 만들었습니다. 실행은 하지 않았습니다.
- 정오 3이 정한 줄만 바뀌었습니다. 1회차 실행본과 M4·M4_retry1 실행본 대비 diff 집합이 정오 3 E3-5·3절 4와 같습니다.
- `ps1_lint`는 종료 0(error 0·warning 0)입니다. `--tag-mode`는 0건입니다. `$AllowListPath2` 15값은 모두 T26′ blob과 같습니다.
- `t26b_identity.json`의 내장 점검 18개가 모두 참입니다.
- 1회차 폴더 `rev26_run\`은 고치지 않았습니다. `rev26_stage5\`와 `judge_rev26_335004a\`는 있는지만 확인했고, 목록이나 내용은 열지 않았습니다.
- 판정 도구·실행본을 실행한 횟수는 0입니다.

## 1. 만든 파일 (`…\v5_resume_4368\rev26_run2\`)
| 파일 | raw sha256 | 비고 |
|---|---|---|
| `run_judgement_path1_rev26b.ps1` | `42fdef019090468581f532c4d8961b6ca070df614707442f783e3b56ffb7b3a7` | LF, 206개 LF 줄(1회차·M4와 같음, 끝 빈 원소를 세면 207) |
| `run_judgement_path2_rev26b.ps1` | `2cfae0e940ea8c04b056af8fe46f6004e9d68cd2b1527e65675fd725a990dd5f` | LF, 456줄(1회차와 같음) |
| `t26b_identity.json` | `4c1102343dad1766fa89649ac82f557dbe78face000f5f681598227b6827897a` | LF |

- 세 파일 모두 `check-attr text` = `unset`입니다. 작업 트리 `.gitattributes`에 E3-8 줄이 있습니다.
- 같은 폴더의 `erratum3_handback_full.md`는 제가 만든 파일이 아닙니다. 열지 않았습니다.

## 2. 실행본 diff 대조
| 실행본 | 기준 | 기준 sha | 다른 줄 | 기대와 일치 |
|---|---|---|---|---|
| 경로 1 | 1회차 `run_judgement_path1_rev26.ps1` | `3516ea5e…` | 13·14·26·27 | 예 |
| 경로 1 | M4 | `868fa7b7…` | 13·14·21·26·27·46·109·116·153·154·155 | 예 |
| 경로 1 | M4_retry1 | `c93cfc5c…` | 13·14·21·26·27·46·109·116 (153~155 같음) | 예 |
| 경로 2 | 1회차 `run_judgement_path2_rev26.ps1` | `a6f0b90c…` | 24·26·27·58·60 | 예 |
| 경로 2 | M4 | `9690f2de…` | 23 뒤 삽입 1줄 + 24·25·26·35·38·39·57~59·61~63·66~71·327·332·336·340·349·362·369·379·384·430 | 예 |

**1회차 대비 바뀐 내용**
- 경로 1
  - 13·14행 `$M4`·`$R4`를 `74c27846cbfab498bd59340d1eaec344f1596b0b`로 바꿨습니다.
  - 26·27행 `$Judge`·`$Co`의 `…\worktrees\rev26-t26\…`를 `…\worktrees\rev26-t26b\…`로 바꿨습니다.
  - 21행 `$Out`은 그대로입니다. 실행하면 `judge_rev26_74c2784`가 됩니다.
- 경로 2
  - 24행 `$WT` → `…\worktrees\rev26-t26b`
  - 26·27행 → T26′
  - 58행 README → `cf854f1afedb587c60f7ed6cd38a9aadc67d4165cc5f8e12b0a993f04dddef0c`
  - 60행 p2_u3 → `d9f9280b55535cb6aedbca499532f1a3752b41503a7a15d9104aa2674460f0ff`
  - 두 값 모두 `git cat-file blob T26′:<파일>`로 다시 계산했고 정오 값과 같습니다. 실행본 생성 스크립트가 다르면 멈추게 해 두었습니다.

**그 밖의 점검**
- unified diff sha256
  - 경로 1: 1회차 대비 `8df0600e…`, M4 대비 `dd6a649b…`, retry1 대비 `ee07a53e…`
  - 경로 2: 1회차 대비 `2e42dcae…`, M4 대비 `0e427d01…`
  - 전문은 identity에 있습니다.
- 토큰 수: 두 실행본 모두 `tag-mode`·`imua`·`pytest`가 0건입니다.
- `$AllowListPath2`
  - 15개이고 모두 T26′ blob과 같습니다. 개수 관문은 `15 expected`로 그대로입니다.
  - 1회차에서 바뀐 값은 README와 p2_u3 둘뿐입니다.
  - 표에 `test_rev26_p2.py`는 없습니다. 이 파일의 T26′ blob은 `4430c1cfba25cf30c4ed23f7cfb8679b5f121c8512b7cd81d74444f7ce9525b1`이고 정오 값과 같습니다.
- ps1_lint: `python-dev -I -B ~/.claude/tools/verif/ps1_lint.py <두 실행본> --format json`을 돌렸습니다. **종료 0**, 파서 AST, 발견 0입니다.

## 3. t26b_identity.json 요약 (점검 18개 모두 참)
- **T26′**
  - `74c27846…`, 부모는 `932f1fb` 하나입니다.
  - T26→T26′에서 바뀐 파일은 `path2/README.md`·`p2_u3.py`·`test_rev26_p2.py` 셋(M)뿐입니다.
  - 규칙 파일·`rev26_fixed/**`·`.gitattributes`는 T26과 diff 0입니다.
  - `ebda7c0c` 대비로는 path2 파일만 다르고, 수정 1 `d6e0630f4dc58efcd8b5856efed62c8d08922431` 대비로는 경로 1 허용 목록 파일만 다릅니다.
- **RD-1 4 대체 조건**
  - 조건 1: 37개이고 T26과 같은 집합입니다. 목록 sha는 `101cead4…`로 1회차와 같습니다. `.gitattributes`는 7절 6줄 추가뿐이고, 규칙 파일은 메인 HEAD와 바이트가 같습니다.
  - 조건 2: 0건입니다. T26′ 추적 수는 03_src 141, 02_params 18입니다.
  - 조건 3: 29개 가운데 바뀌지 않은 10개의 LF sha가 같습니다. 바뀐 파일은 19개입니다.
- **worktree**
  - `rev26-t26b`: HEAD = T26′, `locked rev26 T26b 74c27846 (judge checkout)`, `core.autocrlf=true`(system)
  - `v5_options.py` raw는 `d2b903a2…`이고 (g) 기대값 및 932f1fb CRLF 꼴과 같습니다.
  - 규칙 4개 파일은 T26′ blob, worktree raw, 1회차 값이 모두 같고 `-text`·`w/lf`입니다.
- **외부 도구 sha**: log_errors `3b9a8eac…`, sidecar `0962f639…`, manifest `fa0b72bf…`, compare_r4 `8ff3d32b…`. 모두 1회차와 같습니다.
- **정오 sha**
  - 정오 1 `5e3bf3e6…`(추적됨), 정오 2 `ec47e9d5…`(추적됨)
  - 정오 3 `9d8ae6bc…`(미추적), `.sha256` raw `ecf41f339a031095212fe12a7a383447e2fd689536f44e2005b40c786b80649b`. 정오 3의 `.sha256`이 `.md` sha를 적고 있습니다.
  - 세 정오 모두 T26′에 없습니다.
- **부록 A r6**: 1회차 칸을 옮겼고, 다섯 파일을 다시 계산해 모두 1회차와 같았습니다.
- **`input_basis_crosscheck`**: 1회차 R-5 칸을 그대로 두고 `run2_addendum`을 더했습니다.
  - `git diff T26 T26′ -- p2_u3.py`: diff sha `c376c415…`, +22/−11, 바뀐 줄 33
  - 바뀐 곳: 모듈 docstring, `records_loc`의 screen 키 `r.get("key") or r.get("id")`와 docstring, `u3_pair_key` docstring, 새 `sort_key()`, `recount_u3`의 `sorted(…, key=sort_key)` 2곳
  - 패턴 `data_root|repo|rel_|relative|seal|head|--out|write_|open\(|Path\(`로 바뀐 줄을 검사했더니 0건입니다. `git diff -G`도 0건입니다.
  - 결론: 1회차 R-5 표는 T26′에도 그대로 유효합니다.
- **실행 환경**
  - 1회차 environment 칸을 옮겼습니다. export 파일은 `rev26_run/` 1회차 기록을 가리키고 다시 뽑지 않았습니다. 지금 Python 판도 적었습니다.
  - 4′ 기준값은 python-dev `b32b783e…`, dynamics-dev `c27f109f…`입니다. 지금 다시 계산한 값도 둘 다 같습니다.
- **null 자리**: `env_inventory_before/after`(정오 2 방법), `wt_status_before/after`.
- **`run1_reference`**
  - 1회차 identity `e65e611c…`와 1회차 실행본 sha 둘
  - T26, 준비 커밋 `6c42df04…`
  - 폴더 `rev26_stage5/`·`judge_rev26_335004a/`: 있음만 확인, `contents_opened: false`
  - 종료 코드 path1 1, path2 1, compare_r4 2(출처: 메인 지시와 정오 3 E3-1)
  - 멈춤 원인(p2_u3 종료 3, 5절 2행, 1회로 셈)
  - 메인이 본 로그 줄: 정오 3의 0절 47~51행 5줄을 그대로 옮겼습니다
- **`open_items`**: 없음

## 4. 확인 필요·메인 권고
- 확인 필요: 없음.
- 메인 권고
  - `t26b_identity.json` sha `4c110234…`를 고정해 정오 3의 4′ 재확인에 넘겨 주십시오.
  - 실행 직전에 `wt_status_before`·`env_inventory_before`를 채워 주십시오.
  - 정오 3·`rev26_run2/`를 커밋한 뒤에는 `ls-files --eol`(LF 파일 `i/lf w/lf`)을 확인해 주십시오.

## 5. 공개 (행위 그대로)
- **Read**: 정오 3 전체.
- **git 명령**
  - T26′ 확인: `log -1`, `diff --name-status T26 T26′`, `diff --stat`, `p2_u3.py`의 T26→T26′ diff 전문(경로 2 코드의 바뀐 부분, 정오 3 3절 5 확인용)
  - worktree 확인: `rev26-t26b`의 `rev-parse`·`config`·`check-attr`·`ls-files --eol`(4개 대상 파일), `worktree list --porcelain`
  - 정오 3 `.sha256` 내용(cat)
  - blob 해시: `cat-file blob`(허용 목록 29개, 3개 커밋, 규칙 파일, `test_rev26_p2.py`, `v5_options.py`)
  - 조건 확인: `diff --name-only`(조건 1~3, `ebda7c0c`·`d6e0630f`), `ls-tree -r --name-only T26′ -- 03_src 02_params`(개수만), `ls-files --`(정오 추적 여부)
- **읽은 파일**
  - 1회차 실행본 두 개(편집 원본)와 1회차 `t26_identity.json`(템플릿, sha 확인 뒤)
  - M4·M4_retry1 실행본
  - 외부 도구·부록 r6 다섯 파일·정오 세 파일: 해시만
  - 부록 B r5·r6 목록: 해시만, 내용 미열람
- **1회차 기록 폴더**: `is_dir`로 있는지만 보았습니다. 목록·내용은 열지 않았습니다.
- **열지 않은 것**: 436.8 결과, 판정서, 판정 후 감사, 블라인드 경로, 경로 1 코드. 상위 폴더 검색도 하지 않았습니다.
- **실행한 프로그램**
  - python-dev `-I -B`로 내 스크립트 3개(실행본 생성, identity 작성, 요약) 각 1회
  - ps1_lint 1회
  - 두 env `python -c "import sys; print(sys.version)"`
  - conda list는 돌리지 않았습니다. 종료한 프로세스는 없습니다.
- 처음 쓴 실행본 생성 스크립트에 raw 문자열 결함이 있었습니다(쓰이지 않는 상수). 실행 전에 고쳤고, 출력 파일은 한 번만 만들어졌습니다.
- scratchpad `python-rev26-run2\`는 지웠습니다.

사용한 스킬: 없음
