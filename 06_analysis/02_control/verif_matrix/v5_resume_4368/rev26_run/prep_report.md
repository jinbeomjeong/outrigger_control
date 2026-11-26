# 436.8 rev26 5단계 실행본·t26_identity.json 초안 준비 보고 (python-expert, 2026-11-26)

## 0. 요약
- 5단계 실행본 두 개와 `t26_identity.json` 초안을 `…\v5_resume_4368\rev26_run\`에 만들었다. **실행하지 않았다.** 판정 도구·하위 명령을 부른 횟수는 0이다.
- 두 실행본과 M4 실행본의 diff는 2절 "바꾸는 줄"뿐이다(기계 대조 결과 일치).
- **ps1_lint는 종료 1이다(경로 1 실행본, error 1건).** M4 실행본에 이미 있던 `$Grid` 덮어쓰기 결함을 그대로 물려받았다. 이것은 2절("이 줄만 바꾼다")과 4′("ps1_lint 종료 0")가 함께 성립할 수 없다는 뜻이다. 고치지 않았고, 아래 확인 필요 1로 올린다. **이 상태로는 5단계로 가면 안 된다.**
- RD-1 4 대체 조건 1~3은 모두 충족한다. `v5_options.py` 줄바꿈 잎은 기대값과 같다. 외부 도구 sha 네 개도 규칙의 접두와 모두 맞는다.

## 1. 만든 파일 (모두 `C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\rev26_run\`)
| 파일 | raw sha256 | 크기(B) | 비고 |
|---|---|---|---|
| `run_judgement_path1_rev26.ps1` | `c7298f649b64ca3c0530c75ae63aec5502903e02cab73181590bdd4e0e0214ad` | 15,897 | LF, 207줄(M4와 같음) |
| `run_judgement_path2_rev26.ps1` | `a6f0b90ca7e0747303ea11ccee5da9a20f388c320d480c80396fe6ac86dd145c` | 26,531 | LF, 457줄(M4 456 + `$WT` 1줄) |
| `t26_identity.json` | `7903fa6250ea7f893adf242456dcbeff81c62b7b0518a98f0a16532773fe413c` | 60,376 | 초안, LF |
| `conda_list_export_dynamics-dev.txt` | `6cca76b4300c362481bb7454d5f35b82ce13038c95d4ba78d184ff6d54532d38` | 17,358 | `conda list -n dynamics-dev --export`의 stdout 원 바이트 |
| `conda_list_export_python-dev.txt` | `d5d668845af0375786b1bb91ecd175ff8aceb16ea56980ab85f7d8617c2d0f63` | 11,058 | 같은 꼴 |

- 원본 M4 실행본의 raw sha256은 경로 1 `868fa7b7…`, 경로 2 `9690f2de…`다(둘 다 `judge_932f1fb\_fixed\run\`, `-text`, LF).
- `rev26_run/`은 `.gitattributes`의 `-text` 대상이 아니다(확인 필요 4).

## 2. diff 대조표 (M4 실행본 → 5단계 실행본)
기계 대조 방법: 선언한 삽입 줄을 빼고 두 파일을 한 줄씩 맞대어, 다른 줄 집합이 선언한 교체 줄 집합과 같은지 보았다. 결과는 두 파일 모두 `only_declared_lines_changed = true`다. 아래 표의 줄 번호는 M4 기준이다.

**경로 1** (unified diff sha256 `a87c14b0…`)
| 2절 항목 | M4 줄 | 바뀐 내용 |
|---|---|---|
| 1 | 13, 14 | `$M4`·`$R4` → `335004a7ad9f5f988e7543dd98d45bf2b96e4294` |
| 4 | 21 | `$Out = "$Base/judge_rev26_$($M4.Substring(0, 7))/harness_path1"`. `judge_` 뒤에 `rev26_`만 넣었다. 실제 값은 `judge_rev26_335004a/harness_path1` |
| 2 | 26 | `$Judge = 'C:\workspace\outrigger_control\.claude\worktrees\rev26-t26\06_analysis\02_control\verif_matrix\scripts\resume4368_judge.py'` |
| 2 | 27 | `$Co = 'C:\workspace\outrigger_control\.claude\worktrees\rev26-t26\04_scripts\04_hydraulic\coupled'` |
| 3 | 46 | `$FirstSidecars = '06_analysis/02_control/verif_matrix/v5_resume_4368/judge_932f1fb/_fixed/tools/sidecars_b9f5707.py'`. 2절 문면대로 cwd(메인) 상대 `/` 경로다. 사이드카는 자기 경로를 출력에 적지 않는다(argv 1~3만 씀) |
| 6 | 109 | family_table: `"$Out/family_table.json", '--data-root', '.'` |
| 5 | 116 | h11: `'--h11-dir', "$X/H-11", '--las-k1-dir', '06_analysis/02_control/v5_rerun/las_k1', '--out', …` |
| 7 | — | `--root`는 더하지 않았다 |
| 그대로 | 12, 15, 16, 입력 변수, 주석 | 바꾸지 않았다. 5·44~45행 주석의 M4 문구도 그대로다 |

**경로 2** (unified diff sha256 `ee1bfcac…`)
| 2절 항목 | M4 줄 | 바뀐 내용 |
|---|---|---|
| 2 | 23 뒤 삽입 | `$WT = 'C:\workspace\outrigger_control\.claude\worktrees\rev26-t26'` |
| 2 | 24 | `Set-Location -LiteralPath $WT` |
| 1 | 25, 26 | `$M4`·`$R4` → T26 |
| 5 | 35 | `$ManifestSource = 'C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\judge_932f1fb\_fixed\manifest\p2_manifest_draft.json'`. cwd가 worktree이므로 절대 경로로 썼다. `$ManifestSha256`(36행)은 그대로이고, 사본 sha와 같다 |
| 3 | 38, 39 | `$P2 = "$WT\$Base\path2"`, `$V5c = "$WT\$Base\path2_v5c"` |
| 4 | 57~59, 61~63, 66~71 | `$AllowListPath2` 값 → T26 raw blob sha256(12줄). 60·64·65행(`p2_v5j.py`·`test_p2_v5j.py`·`test_p2_x16.py`)은 932f1fb와 blob이 같아 값이 그대로다 |
| 7 | 327, 332, 336, 340, 349, 362, 369, 379, 384 | `'--out', "$Out\<파일>"` 쌍 바로 뒤에 `'--data-root', $Repo`. 대상은 harness·anchors·jp·g3·u3·c16·v5c_stage1·v5c_grid·v5c_noise다. seal·d1·items·v5j_u9·v5c_merge는 손대지 않았다 |
| 6 | 430 | `$Out = "$Repo\$Base\judge_rev26_$($M4.Substring(0, 7))\harness_path2"` |
| 그대로 | 23(`$Repo`), 40~46 입력 변수, 28~29 `$Conda`·`$CondaPython`, 206행 개수 검사 "15" | 바꾸지 않았다 |

**인자가 실제로 받아들여지는지(git grep·git show로 T26 코드 확인, 실행은 하지 않음)**
- `resume4368_judge.py`(5352행)에 `--las-k1-dir`가 있다.
- `resume_k1_family.py`는 위치 인자 `out` 다음에 `--data-root`를 받는다.
- `p2_4368`·`p2_x16`·`p2_u3`·`p2v5c_common.add_common_args`는 `--data-root`를 최상위 파서에 둔다. 그래서 하위 명령 이름 앞에 넣어도 된다.

**`$AllowListPath2` 표** (T26 raw blob sha256, `git cat-file blob T26:<파일>`)
| 파일(`…/v5_resume_4368/` 아래) | T26 값 | 932f1fb 대비 |
|---|---|---|
| path2/README.md | `a45c4e1c8f2fc247a52f7bc03e1193d55baddefdd72841958f2d90d9741e0f1d` | 바뀜 |
| path2/p2_4368.py | `4c89a3758983083b768a30ffef13990e5030212d9765df0d086a05d254a687d2` | 바뀜 |
| path2/p2_u3.py | `7ec2d245bcdf42890c78fc00010a774a666a163c29487f57516b3ca1b954911f` | 바뀜 |
| path2/p2_v5j.py | `b815771dcaee69f5b474a7a6328f7699631d4c69309a973314a0ba3eaf06ecb8` | 같음 |
| path2/p2_x16.py | `4bd6b19ba308d10f9c894de820ebee6f202e67bc36bff176220b88ea08b21d03` | 바뀜 |
| path2/test_p2_4368.py | `a965ab75f3b41059609ff0f5637463002f9312cea79cc55df24e5392cdd9c855` | 바뀜 |
| path2/test_p2_u3.py | `98d9d7f255dbc6c09b26a9f2659c01be11adbaf63624946ebd3adfe662b7d9a7` | 바뀜 |
| path2/test_p2_v5j.py | `017d432730bc6e52d11fc116cd29692f1af3b38b4d098b53f80edb7a061f9092` | 같음 |
| path2/test_p2_x16.py | `c7efdefd7e7c6633823d6283d72086623055c6c73acafc40307b64b695f890d8` | 같음 |
| path2_v5c/README.md | `b5952a9acac1472a69cf10a1ef93ea124e340f91d0259677250f43b21a8a5daf` | 바뀜 |
| path2_v5c/p2v5c_common.py | `f15e75a4433a572f3a9ac5b34df71460a19bac6cbad422522dd2ff1abb8cb232` | 바뀜 |
| path2_v5c/p2v5c_grid.py | `0d9c6d0f661f9334c7b259eb83b661c45161b901c31cbea7699f09b6350abc44` | 바뀜 |
| path2_v5c/p2v5c_noise.py | `48fe9cb1b43d9fea02043f58381697fe60009fb8cfd52490b7fb6cff4aecf687` | 바뀜 |
| path2_v5c/p2v5c_stage1.py | `6b5a10841d6a61efd89173cfb7351616c31946490fe36c9a448d0e41c7fcad34` | 바뀜 |
| path2_v5c/test_p2v5c.py | `65537a8e3864213ae3f457a20273268e81ea6c240b1ba41b3e7b3eeff9e31cd6` | 바뀜 |

- 이 값들은 path2_report 1절의 b587a84 blob 값과 모두 같다.
- M4 실행본의 원래 표 값 15개는 932f1fb blob raw sha와 모두 같았다.
- path2_report 8-1이 요청한 확인도 했다. `p2v5c_common.P2_CORE_SHA`(`4c89a375…`)는 T26의 `p2_4368.py` blob과 같다.

## 3. ps1_lint 결과
- 명령: `python-dev -I -B C:\Users\jinbeom\.claude\tools\verif\ps1_lint.py <경로1 실행본> <경로2 실행본> --format json`. 파서는 AST이고 구문 오류는 두 파일 모두 0이다.
- **종료 1.** 경로 2는 발견 0이다.
- 경로 1에서 error 1건이 나왔다. 종류는 `case_variant_overwrite`다.
  - 153행 `foreach ($grid in 'grid_r67_main', …)`가 62행 `$Grid`(격자 4파일 배열)를 덮어쓴다.
  - 덮어쓴 값을 159행(stage1_judge `--grid`)과 183행(stroke_H-9)이 읽는다.
- 이 결함은 M4 실행본에 원래 있던 것이고, 2절이 허용한 줄 밖이라 그대로 남았다. ps1_lint README도 이 사고 판을 예로 든다.
  - 원 판정에서는 `run_judgement_path1_M4_retry1.ps1`이 루프 변수를 `$gname`으로 바꾸고 출력 폴더를 `harness_path1_retry1`로 해서 다시 돌았다.
  - M4와 retry1을 직접 diff해 보니 다른 곳은 21행과 153~155행뿐이다.
  - 부록 A 범위 문장은 `stage1_judge.json`·`stroke_H-9.json`의 원 출력을 retry1 판으로 쓴다고 정한다.
- 이대로 돌리면 두 단계가 `$Grid` = `'grid_r69_top'` 문자열 하나로 돈다. 그러면 원 출력과 달라져 (d) 불일치, 곧 "판정 불가(rev26 기대 효과 불일치)"가 될 가능성이 크다(추정, 실행하지 않음).

## 4. t26_identity.json 초안 요약
- **T26**: `335004a7ad9f5f988e7543dd98d45bf2b96e4294`. 부모는 `932f1fb…`이고 커밋 제목도 기록했다.
- **바뀐 파일**: `git diff --name-status 932f1fb..T26` 37개. 목록을 LF로 이은 sha는 `101cead4…`다.
  - 경로 1 허용 목록 7개, 경로 2 도구 폴더 13개(새 파일 `test_rev26_p2.py` 포함), 규칙 파일 16개(`.md`·`.sha256`과 `rev26_fixed/**` 14개), `.gitattributes` 1개.
- **RD-1 4 대체 조건**
  - 조건 1: 모두 허용 집합 안이다.
    - `.gitattributes`는 7절 `-text` 6줄 추가뿐이다(삭제 0, 주석 줄 없음).
    - 규칙 파일·`rev26_fixed/**`는 master와 `git diff` 0이다.
    - 4′에서 고정할 "바뀐 파일 목록"은 지금 목록으로 두었다.
  - 조건 2: `git diff --name-only b9f5707..T26 -- 03_src 02_params`는 비어 있다.
  - 조건 3: 허용 목록 29개(경로 1 14개 + 경로 2 15개) 가운데 바뀌지 않은 10개를 보았다. LF sha256이 932f1fb와 모두 같다(raw blob도 같다).
- **worktree**
  - HEAD = T26, 브랜치 `rev26-t26`, `locked rev26 T26 335004a7 (judge checkout)`
  - `core.autocrlf=true`이고 출처는 `C:/Program Files/Git/etc/gitconfig`(system)다.
- **4개 대상 규칙 파일**: T26 blob sha와 worktree raw sha가 같다. `check-attr text`는 `unset`, `ls-files --eol`은 `i/lf w/lf attr/-text`다. `.md`는 `f6591836…`, `.sha256`은 `e74aeca9…`, `excl_fields_r5.py`는 `bee9eee7…`, `rev26_excluded_fields_r5.json`은 `9e1831f5…`다.
- **외부 도구 sha**(모두 규칙의 접두와 일치)
  - `log_errors.py`: `3b9a8eac9177a2e3…`
  - sidecar 사본: `0962f6397aaf3b16…`
  - 매니페스트 사본: `fa0b72bf90694455…`
  - `compare_r4.py`(`judge_932f1fb/_fixed/compare/`): `8ff3d32ba0aaf561…`
  - 저장소 사본 세 개는 메인 HEAD의 blob과도 같다.
- **실행 환경**: conda 26.7.2
  - dynamics-dev: Python 3.12.15, export sha `6cca76b4…`, 580줄
  - python-dev: Python 3.13.15, export sha `d5d66884…`, 380줄
- **v5_options.py**: worktree raw sha는 `d2b903a2…`다. 이는 932f1fb blob(LF `a88ad603…`)의 CRLF 꼴 sha이고, (g)의 기대값과 같다.
- **비워 둔 칸**
  - `wt_status_before`·`wt_status_after`: 명령 자리만 두고 시각·출력은 null이다(5단계 때 메인이 채움).
  - `input_basis_crosscheck`: null이다. 4′ 감사 몫이라고 적고 두 구현 기록 3절을 가리켰다.
- **함께 담은 것**: `stage5_runners`(편집 목록, unified diff, 대조 결과), `ps1_lint` 결과(종료 1과 발견), `open_items`(아래 확인 필요 1~3).

## 5. 확인 필요
1. **[차단] 경로 1 `$Grid` 덮어쓰기: 2절 "이것뿐"과 4′ "ps1_lint 종료 0"이 충돌한다.** 근거는 규칙 `v5_resume_4368_rules_rev26.md:89~98`(바꾸는 줄)과 `:145`(4′ ps1_lint)다. 실행본 쪽은 `rev26_run\run_judgement_path1_rev26.ps1:153~155` ↔ `judge_932f1fb\_fixed\run\run_judgement_path1_M4_retry1.ps1:153~155`다.
   - 가능성 (가): 2절대로 둔다. ps1_lint 종료 1이 남고, stage1_judge·stroke_H-9의 (d) 불일치가 예상된다.
   - 가능성 (나): retry1처럼 153~155행 루프 변수만 `$gname`으로 바꾼다. 3줄이 바뀌고 2절 diff 조건을 넘으므로 규칙 개정 또는 사용자 결정이 필요하다.
   - 어느 쪽이든 결정 뒤 실행본 sha와 `t26_identity.json`을 다시 만들어야 한다.
2. **`path2/test_rev26_p2.py`를 `$AllowListPath2`에 넣지 않았다.** 근거는 셋이다.
   - (i) 2절 경로 2의 4번은 "`$AllowListPath2`(56~72행) → T26 blob **값**"이라 값 교체만 정한다.
   - (ii) 실행본 시작 관문이 표 개수를 15로 검사한다(M4 206행 `(라) table has … 15 expected`, 새 실행본 207행). 이 줄은 바꾸는 줄에 없으므로, 16번째를 넣으면 시작 관문이 멈춘다.
   - (iii) 표의 출처가 RD-1 4 / rev16:325의 "(라) 15 files"다.
   - 이 파일은 시험 파일이라 판정 출력에 닿지 않는다. 그리고 T26 HEAD 관문이 트리 전체를 고정한다.
   - 반대쪽 가능성: 4′ "바뀐 파일 목록"에는 이 파일이 들어가 있다. 실행본 blob 관문도 바뀐 경로 2 파일 전부를 덮어야 한다고 읽으면 넣어야 한다. 이 경우 206행 개수 변경이 함께 필요하다.
   - 이 파일의 T26 blob raw sha는 `3e8166b2132a530d4330f6c150fb594eb0c12f87fbd3e4c2df9ee8cc76ca2877`이다(identity에 적음).
3. **`t26_identity.json` 위치**: 규칙 `:84`·`:109`는 `rev26_fixed/t26_identity.json`이라고 적는다. 지시대로 `rev26_run/`에 두었다(identity의 `location_note`). 4′·6단계가 규칙 문면의 경로를 찾을 수 있으므로 감사 지시문에 이 위치를 적어야 한다.
4. **`rev26_run/`은 `-text`가 아니다.** 시스템 `core.autocrlf=true`라서 커밋한 뒤 새 checkout에서는 CRLF로 풀린다. 그러면 기록한 실행본 sha(LF 바이트)와 달라질 수 있다. 메인 작업 트리 파일은 그대로다. 커밋할 계획이면 `.gitattributes`(master)에 `rev26_run/** -text`를 더할지 정해야 한다. T26의 `.gitattributes`는 건드리지 않는다.

## 6. 메인 세션 권고 (5단계 전)
- 메인 checkout의 추적 트리가 지금 깨끗하지 않다(` M .claude/agents/paper-reviewer.md`, ` M 00_docs/decision_log.md`). 경로 1 실행본의 `Assert-CleanTree 'start'`(cwd = 메인)가 시작에서 멈춘다. 5단계 전에 정리해야 한다.
- 두 실행본은 `-Only` 없이, 규칙 7절대로 worktree 깨끗함(W-i)을 앞뒤로 기록하고 띄운다. 경로 1은 `rev26_run` 실행본을 메인 cwd에서 부른다. 경로 2는 스스로 `Set-Location $WT`를 한다.

## 7. 공개 (행위 그대로)
- **연 파일(Read)**
  - 규칙 `v5_resume_4368_rules_rev26.md` 1~248행: 0~7절과 부록 A 문장. 부록 B 절은 표제만 보았다.
  - M4 실행본 두 개 전체
  - `rev26_impl\path1_report.md` 1~30·105~134행, `path2_report.md` 19~54·150~209·249~336행
  - ps1_lint README의 ps1_lint 관련 줄(Grep)
- **Grep**
  - `_fixed\tools\sidecars_b9f5707.py`: `argv`·`__file__` 줄만 보았다(사이드카가 자기 경로를 출력에 적는지 확인).
  - `rev26_impl\*.md`
  - `~/.claude/tools/verif/README.md`
- **Glob**
  - `~/.claude/tools`: `**/compare_r4.py`, 결과 없음
  - `judge_932f1fb\_fixed\run`: `*`. 실행본 폴더이고, 이름 목록 7개를 보았다.
- **git 명령**
  - T26 확인: `rev-parse`, `log -1`, `diff --name-status 932f1fb..T26`
  - `.gitattributes` diff, T26↔master 규칙 파일 diff, 조건 2 diff
  - worktree 확인: `worktree list --porcelain`, worktree `config core.autocrlf`·`rev-parse HEAD`·`check-attr`·`ls-files --eol`(4개 대상 파일)
  - 개별 파일 확인: `check-attr`·`ls-files --eol`(M4 실행본·사이드카·매니페스트 사본), `git ls-files -- '*compare_r4.py'`·`'*compare_r4*'`(이름 패턴, 결과 5개 가운데 `compare_r4_result.json`은 열지 않음)
  - T26 코드의 인자 정의 확인: `git grep`(`--las-k1-dir`·`add_argument`·`data-root`·`add_common_args`)과 `git show`(파서 주변 수십 줄)
  - 두 실행본 비교: `git diff --no-index`(M4 ↔ M4_retry1)
  - 메인 추적 트리 확인: `git status --porcelain --untracked-files=no`
  - blob 해시: `git cat-file blob`으로 해시만 계산(허용 목록 29개, 규칙 파일 4개, `v5_options.py`, `test_rev26_p2.py`)
- **부록 B 파일** `rev26_excluded_fields_r5.json`: git blob과 worktree 파일의 바이트를 sha256 계산에만 넣었다(4′ 대상 파일 sha 기록용). 내용은 출력하지도, 읽지도 않았다.
- **실행한 프로그램**
  - python-dev `-I -B`로 내 스크립트 3개(실행본 생성, identity 작성, 요약)를 돌렸다.
  - ps1_lint를 1회 돌렸다(정적 검사, 실행본은 실행하지 않음).
  - `conda.exe --version`, `conda.exe list -n <env> --export`를 env 2개에 돌렸다.
  - 각 env `python.exe -I -B -c "import sys; print(sys.version)"`을 돌렸다.
  - identity 스크립트는 conda list가 느려서 셸이 백그라운드로 넘겼다(약 4분). 그 동안 내 PID 22460을 `Wait-Process`로 기다렸고, 종료한 프로세스는 없다.
- **판정 도구·하위 명령 실행 0회.** 436.8 결과 json, 판정서, 판정 후 감사, 블라인드 경로는 열지 않았고 검색 대상에 넣지 않았다. 상위 폴더를 검색 path로 쓰지 않았다(Glob은 `_fixed\run`과 `~/.claude/tools`만).
- **지운 것**
  - 첫 생성 시도에서 만든 실행본 2개와 scratch 기록 1개를 지웠다. 내 대조 코드가 삽입 + 교체 묶음을 미선언 변경으로 오판해서였다. 대조 방식을 고친 뒤 다시 만들었고 내용 결함은 아니었다.
  - scratchpad `python-rev26-run\`은 보고 전에 지웠다.

사용한 스킬: 없음
