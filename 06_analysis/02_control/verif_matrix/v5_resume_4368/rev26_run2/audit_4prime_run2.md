# 436.8 rev26 2회차 전 4′ 재확인 (정오 3 3절 표 1~10) — verif-protocol-auditor, 2026-11-26

## 감사 요약
- **본 결과**
  - 1회차 출력(`judge_rev26_335004a/`)과 `rev26_stage5/`의 파일 내용(compare·콘솔 로그 포함)은 열지 않았다.
  - 436.8 저장 결과, 원 출력 값, 판정서, 판정 후 감사, 부록 B 내용, 블라인드도 열지 않았다.
  - 본 값은 합성 고정물 출력, sha, 규칙·보고 문서뿐이다.
  - transcript는 도구 **입력**과 결과의 토큰 유무만 봤다. 1회차 콘솔 출력이 담긴 결과 본문은 출력하지 않았다.
- **대상**: T26′ `74c27846cbfab498bd59340d1eaec344f1596b0b`, worktree `rev26-t26b`(locked)
- **기준 문서**: 정오 3 `9d8ae6bc`(`.sha256` `ecf41f33`, 1줄), rev26 `f6591836`, 정오 1 `5e3bf3e6`, 정오 2 `ec47e9d5`, 부록 A r6 `ce5208a8`·B r6 `36906ff2`
- **판정: 차단 0 / 실행 전 수정 1 / 기록 6.**
  - 정오 3 3절 표 1~10이 모두 충족이다.
  - **2회차는 진행할 수 있다.** 단, 실행 전 수정 R3-W1(메인 추적 트리 정리·커밋)을 먼저 끝낸다.

## 정오 3 3절 표 대조
| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| 1 | 정오 3 봉인 | 충족 | `.sha256` 1줄의 sha `9d8ae6bc…`가 `.md` raw와 같다. LF, BOM 없음. rev26 `f6591836`·`e74aeca9`, 정오 1 `5e3bf3e6`·`27f98bae`, 정오 2 `ec47e9d5`·`f840fdc0`, r6 `ce5208a8`·`36906ff2`, r5 `bee9eee7`·`9e1831f5`는 바뀌지 않았다 |
| 2 | T26′ 대조 조건 | 충족 | 아래 R3-1 |
| 3 | worktree | 충족 | HEAD = T26′. `locked rev26 T26b 74c27846 (judge checkout)`. `core.autocrlf=true`(system). `v5_options.py` raw `d2b903a2`. `status --porcelain --ignored` 0줄(합성 실행 전후). 규칙 4개 파일은 `i/lf w/lf attr/-text` |
| 4 | 실행본 | 충족 | 아래 R3-2 |
| 5 | 입력 기준(B-5) | 충족 | 아래 R3-3 |
| 6 | 정체성(u3 합성 1회와 권장 연쇄) | 충족 | 아래 R3-4 |
| 7 | 두 경로 독립(수정 1 작성자) | 충족 | 아래 R3-5 |
| 8 | 판정 도구 실행 횟수 | 충족 | 아래 R3-6 |
| 9 | 1회차 공개 | 충족(내용 대조는 못 함, 기록 R3-7) | 아래 R3-7 |
| 10 | 기록 보호 | 충족(커밋 전이라 `check-attr`만) | 아래 R3-8 |

## 발견 사항 (심각도순)

### [실행 전 수정][I] R3-W1 메인 추적 트리가 깨끗하지 않다. 2회차 자료가 아직 커밋되지 않았다
- **추적 트리**
  - 메인 HEAD는 `6c42df04`다.
  - `git status --porcelain --untracked-files=no`: ` M .gitattributes`(E3-8 줄 추가분), ` M 00_docs/decision_log.md`
  - 경로 1 `Assert-CleanTree 'start'`(`run_judgement_path1_rev26b.ps1:73~79`)가 멈춘다.
- **미추적**: 정오 3 `.md`·`.sha256`, `rev26_run2/**`(실행본 둘, `t26b_identity.json`, `prep_report_run2.md`, `erratum3_handback_full.md`)
- **권장 조치(메인)**
  - `.gitattributes`(E3-8 줄)를 같은 커밋이나 앞선 커밋에 넣는다.
  - 정오 3과 `rev26_run2/**`, 이 보고를 커밋한다.
  - 커밋 뒤 `git ls-files --eol`이 `i/lf w/lf attr/-text`인지, raw sha가 identity 값(`42fdef01`·`2cfae0e9`·`4c110234`)과 같은지 본다. `rev26_run2`에는 지금 CRLF 파일이 없다.
  - `decision_log.md`를 처리한다.
  - 2회차 직전에 `wt_status_before`·`env_inventory_before`를 적는다.

### [기록] R3-1 T26′ 대조 조건(E3-3): 충족(직접 재계산)
- **커밋 꼴**: T26′의 부모는 `932f1fb` 하나다. T26→T26′ 바뀐 파일은 `path2/README.md`·`p2_u3.py`·`test_rev26_p2.py` 3개(M)뿐이다.
- **조건 1**
  - `git diff --name-only 932f1fb..T26′`는 37개이고 T26과 같은 집합이다.
  - stdout sha `101cead446974df82fc27b954ec13051b877e7b907828c3da9c8ce4fbc2f333f`는 정오 3·1회차 identity 값과 같다.
- **조건 2**: `b9f5707..T26′ -- 03_src 02_params` 0건. 추적 141·18
- **조건 3**: 허용 목록 29개 가운데 바뀌지 않은 10개의 LF 바이트가 같다.
- **브랜치 대조**
  - `ebda7c0c` 대비 다른 파일은 `path2/`·`path2_v5c/` 13개뿐이다.
  - `d6e0630f` 대비 다른 파일은 경로 1 허용 목록 7개뿐이다.
  - 그래서 T26′의 경로 1 파일 = `ebda7c0c`, 경로 2 파일 = `d6e0630f`다.
- **T26 대비 같음**: 규칙 파일(rev26 `.md`·`.sha256`), `rev26_fixed/**`, `.gitattributes`는 diff 0이다.

### [기록] R3-2 2회차 실행본: 정오 3 E3-5의 줄만 바뀌었다
- **경로 1**(`run_judgement_path1_rev26b.ps1` `42fdef01`) 대 1회차 `3516ea5e`
  - 교체는 13·14행(`$M4`·`$R4` = T26′)과 26·27행(`$Judge`·`$Co` → `rev26-t26b`)뿐이다. 207/207줄이다.
  - 21행 `$Out`은 그대로다(→ `judge_rev26_74c2784`).
- **경로 2**(`run_judgement_path2_rev26b.ps1` `2cfae0e9`) 대 1회차 `a6f0b90c`
  - 교체는 24행(`$WT` → `rev26-t26b`), 26·27행(T26′), 58행(README `cf854f1a…`), 60행(p2_u3 `d9f9280b…`)뿐이다. 457/457줄이다.
- **ps1_lint**: 두 파일 모두 종료 0(error·warning·info 0, AST)
- **토큰**: `tag-mode`·`imua`·`pytest` 0건
- **`$AllowListPath2`**
  - 15값이 모두 T26′ blob raw sha와 같다.
  - `test_rev26_p2.py`는 표에 없다. T26′ blob은 `4430c1cf…`이고 정오 3과 같다.
  - "15 expected"는 그대로다.
- **`t26b_identity.json`**: raw `4c1102343dad1766fa89649ac82f557dbe78face000f5f681598227b6827897a`이고 지시값과 같다. 실행본 두 sha가 안에 있고, 내장 `checks` 18개가 모두 참이다.
- 2회차 출력 폴더 `judge_rev26_74c2784`는 아직 없다.

### [기록] R3-3 입력 기준: T26→T26′ `p2_u3.py` diff를 직접 읽었다. 입력 기준에 닿지 않는다
- **바뀐 곳(+22/−11)은 다섯 가지뿐이다**
  - 모듈 docstring
  - `records_loc`의 screen 키 `r.get("key")` → `r.get("key") or r.get("id")`와 그 docstring
  - `u3_pair_key` docstring
  - 새 `sort_key()`
  - `recount_u3`의 `sorted(..., key=sort_key)` 두 곳(짝 키 루프와 `(setting, suite)` 루프)
- `--data-root`·`repo`·상대 경로·봉인·HEAD·출력 쓰기 코드에는 닿지 않는다.
- `sort_key`는 문자열끼리 비교할 때 `(True, s)` 순서라 일반 `sorted`와 순서가 같다.
- 첫 4′의 R-5 표는 T26′에도 그대로 유효하다.

### [기록] R3-4 경로 2 u3 합성 1회와 권장 연쇄 1회(E3-7 6): 기대 종료 코드표 안에서 끝났다
- **합성 입력**
  - 경로 1 시험 builder(T26′ `test_resume4368_supplement4._build_inputs`) 위에 U-3 파일을 다섯 꼴로 다시 썼다.
    - `u3_C_*`: screen `key` 3줄
    - `u3_D_*`: screen `id`만 3줄(연구 D 꼴)
    - `u3_p3b_*`: suite 있는 wrapper 3줄
    - `u3_slope_*`: suite 없는 wrapper 3줄
    - 나머지: builder 꼴
  - 연구 키 파일(`s9/rev85` 셋)은 합성 `--data-root` 아래에 두었다(T26′ `test_rev26_p2` 고정물 함수 재사용).
- **실행 꼴**: `run_judgement_path2_rev26b.ps1`의 14단계 인자 그대로 실행했다(cwd = `rev26-t26b`, `--data-root` = 합성 메인, `--expect-head` T26′, 매니페스트 사본 복사). 2026-11-26 23:54:39~23:55:10
- **연쇄(u3부터 끝 단계까지) 결과**
  | 단계 | 종료 | 기대표 |
  |---|---|---|
  | u3 | 2 | (0,1,2) 안 |
  | v5j_u9 | 2 | 안 |
  | c16 | 1 | 안 |
  | items | 0 | 안 |
  | v5c_stage1 | 2 | 안 |
  | v5c_grid | 2 | 안 |
  | v5c_noise | 2 | 안 |
  | v5c_merge | 2 | 안 |
  - 이 단계들에 치명 표지(S-1·P2-SHA)는 0이다. `head_check.ok`는 해당 단계 모두 true다.
  - 합성이라 merge `not_merged`는 true다(파트의 S-11). 실행본에서는 이것이 throw 조건이고, 합성 데이터 꼴 때문에 생긴 결과다.
- **u3 앞 단계(참고)**: 합성 데이터 꼴 때문에 실행본 꼴에서 멈춤 조건이 났다.
  - anchors: S-1(부록 B 키 원본 없음)
  - g3: 종료 2(G-3 거짓)
  - d1: 종료 3(h1 꼴)
  - 1회차 실데이터에서는 이 세 단계를 통과해 u3까지 갔다(정오 3 E3-1). 그래서 도구 결함의 증거로 보지 않는다.
- **u3 짝 키**
  - `U-3.differences` 528개 키 가운데 null·빈 키는 0이다. 다섯 꼴이 모두 문자열 키로 짝지어졌다.
    - D 꼴: `H8|rigid|B|top|flat` 등 id 그대로
    - C 꼴: key 그대로
    - suite 있는 wrapper: `p3b|H1|J1|B|top|k0`
    - suite 없는 wrapper: `slope|edge|top|0` id 그대로
  - `vb_unique_fail`과 `G-5_list`에 D 꼴 키와 wrapper 키가 들어 있다. 종료 3은 재현되지 않았다.
- **null이 보인 곳은 `U-3.counts.{V0,VB}`의 suite 열쇠 `"null"`뿐이다.** 이것은 짝 키가 아니라 suite 열쇠다(R26-1 설계, 첫 4′ R-9 6절 6).
  - 6단계에서 E3-4 "(a) null 키"를 셀 때 이 suite 열쇠를 짝 키로 세지 않도록 판정서에 적기를 권한다(기록).
- **합성 G-1**: builder 파일끼리 suite 없는 같은 id(`k0…`)가 겹쳐서 나온 중복 키다. 합성 고정물의 결과이고, 새 다섯 꼴 줄에서 나온 것이 아니다.
- 합성 전후 `rev26-t26b`의 `status --porcelain --ignored`는 0줄이었다. path2 `__pycache__`도 없다.
- **변형 1~3은 다시 하지 않았다(정오 3 3절 6의 판단).** 근거를 직접 확인했다.
  - T26→T26′ 실행 코드 변경은 `p2_u3.py`뿐이다(R3-1).
  - diff가 출력 정체성 필드에 닿지 않는다(R3-3).
  - 출력 `u3.json`은 (d) 범위 밖이다.

### [기록] R3-5 수정 1 작성자(`agent-ac916be4…`)의 경로 1·1회차 출력 열람: 0
- **범위**: 첫 핸드백 뒤(2026-11-26T11:12:40Z~) 도구 호출 23개(14:22:19Z~14:28:26Z)
- 경로 1 코드·출력, `judge_rev26_335004a/`, `rev26_stage5/`, 436.8 결과를 연 호출은 0이다.
- 걸린 것은 핸드백 본문(보고서 문장 안의 이름)과 자기 시험 파일 편집뿐이다.
- 1회차 `u3.err` 오류 추적은 메인이 SendMessage로 넘긴 것으로 보인다. 정오 3 0절·E3-2에 공개되어 있다.

### [기록] R3-6 436.8 저장 결과에 판정 도구가 돈 기록: 1회차 1번뿐(1회차 뒤 ~ 4′ 0)
- 이 세션 transcript(메인과 subagents)의 셸 호출(2026-11-26T12:00Z~)을 훑었다.
- 실행본이 띄워진 것은 메인 `2026-11-26T14:19:32Z` `pwsh -File …\runners\outrigger-rev26-stage5\run_stage5.ps1` 1번뿐이다(끝 14:21Z).
- 그 뒤 판정 도구·실행본 실행은 0이다. 나머지 일치는 git·해시·ps1_lint와 감사·준비 에이전트의 조회였다.
- 이 감사의 실행은 모두 합성(scratchpad)이다.

### [기록] R3-7 1회차 공개(정오 3 0절): 기록은 있다. 판정 낱말은 없지만 결과 정보는 있다. 실제 출력과의 대조는 하지 못했다
- **있는 것**: 0절 47~51행에 메인이 본 줄이 적혀 있다.
  - 경로 1 0이 아닌 단계 7줄
  - 경로 2 `stopped`·`end gate`, u3 오류 추적
  - compare 끝 줄 `{"exit_code": 2, "equal": 5, "differ": 0, "missing": 16, …}`
  - 사용자 결정(공개하고 진행)
- **내용**: 등급 낱말(통과·미달·판정 불가)은 없다. 다만 두 가지는 결과 정보다. 정오 3도 그렇게 적었다.
  - 단계 종료 1 = findings 유무
  - 두 경로 대조 일치 건수
- **대조하지 못한 것**
  - 메인 transcript 입력으로 보면, 메인은 `path1_console.log -Tail 12`, `path2_console.log -Tail 12`, `compare_console.log -Tail 4`, harness_path2 `logs` 목록과 `*u3*` 파일 `-Tail 15`, `end_gate.txt`를 출력했다(2026-11-26T14:21:12Z·14:21:19Z).
  - 0절 기록은 "끝 1줄"·"7줄" 등으로 요약되어 있다. 실제로 화면에 나온 줄 전체와 같은지는 그 출력이 1회차 내용이라 이 감사가 열지 않았다(금지).
- **권장**: 메인이 판정서 공개에 "출력한 명령(`-Tail 12/12/4/15`)과 화면에 나온 줄 전부"를 transcript에서 그대로 옮기기를 권한다(감사 리포트 원문 저장 규칙과 같은 방식).

### [기록] R3-8 기록 보호(E3-8): 충족(커밋 전)
- master 작업 트리 `.gitattributes`에 다음 줄이 있다: `rev26_run2/** -text`, `rev26_stage5/** -text`, `rev26_stage5_run2/** -text`, 정오 3 `.md`·`.sha256` `-text`
- `check-attr text = unset`인 대상
  - `rev26_run2/` 5파일, 정오 3 둘
  - 가상 경로 `judge_rev26_74c2784/harness_path1/x.json`, `rev26_stage5_run2/x.txt`
- 메인이 1회차 뒤 `rev26_run/erratum2_tests`를 `rev26_e2_tests/`로 옮기고 `-text` 줄을 더했다(메인 transcript 14:16·14:18Z). 이로써 첫 재감사 W2-1은 해소됐다.

## 2회차 진행 가부
- **진행 가능(조건부).** R3-W1(추적 트리 정리와 커밋)을 끝낸 뒤 진행한다. 정오 3 3절 6의 판단(변형 1~3 생략)은 이 감사의 확인과 맞는다.

## 메인 세션 권고 (2회차 전 남은 메인 할 일)
1. `00_docs/decision_log.md`를 처리한다(커밋 또는 정리). `.gitattributes`(E3-8)를 커밋한다.
2. 정오 3 `.md`·`.sha256`과 `rev26_run2/**`(이 보고 `audit_4prime_run2.md` 포함)를 커밋한다. 커밋 뒤 `ls-files --eol`이 `i/lf w/lf attr/-text`인지, raw sha가 identity·정오 값과 같은지 확인한다.
3. 판정서 공개용으로 1회차 화면 출력 전문을 메인 transcript에서 옮긴다(R3-7 권장).
4. 2회차 직전 확인
   - 메인 `git status --porcelain --untracked-files=no` 0줄
   - `git -C …\rev26-t26b status --porcelain`(+ `--ignored`) 0줄 → `wt_status_before`
   - 두 env `stable_inventory` → `env_inventory_before`
   - 다른 에이전트의 메인 쓰기 작업을 멈춘다.
5. 2회차를 돌린다: 경로 1은 메인 cwd, 경로 2는 자체 `Set-Location`, 이어서 `compare_r4.py`(폴더 `judge_rev26_74c2784`). 직후 `wt_status_after`·`env_inventory_after`를 적는다.
6. 6단계 감사 지시에 넣을 것: E3-4 null 키는 짝 키로 센다(`counts`의 suite `"null"` 열쇠는 제외, R3-4). 2회차 출력 폴더와 커밋 T26′

## 검사하지 못한 것
- 정오 3 0절 기록과 1회차 실제 화면 출력의 일치(R3-7, 1회차 내용 열람 금지)
- 경로 2 u3 앞 세 단계(anchors·g3·d1)를 합성으로 통과시키지 못했다(합성 데이터 꼴). 1회차 실데이터에서 통과한 사실은 정오 3 E3-1 기록에 기댄다.
- 실데이터에 기대는 항목(D 꼴 연구 키, null 키 유무, IND_LAS·최상위 태그)은 2회차에서 드러난다.

## 실행한 검증
- **인터프리터**
  - 대조·해시·스캔: python-dev `-I -B`(MKL_THREADING_LAYER=TBB)
  - 합성 builder: dynamics-dev `python.exe -I -B`
  - 합성 경로 2: `conda run -n dynamics-dev python -I -B`(cwd = `rev26-t26b`), 백그라운드 1회. 내가 띄운 것이고 스스로 끝났다(종료 0).
- **즉석 스크립트**(scratchpad `verif-rev26-4p3\`, 보고 전 폴더째 삭제)
  - `static3.py`: 1~5·10, git 조회·해시·difflib
  - `build_u3.py`: T26′ 시험 builder 재사용
  - `run_p2.py`: 실행본 꼴 14단계
  - `scan3.py`·`scan_main.py`: transcript 입력 스캔
- **도구**: `ps1_lint.py`(종료 0)
- **git 조회**: rev-list, diff(name-status·name-only·p2_u3 전문), ls-tree, cat-file, worktree list, config, status(`--ignored`), check-attr, ls-files --eol, rev-parse
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha v5_resume_4368_rules_rev26.md f6591836…, v5_resume_4368_rules_rev26_erratum1.md 5e3bf3e6…, v5_resume_4368_rules_rev26_erratum2.md ec47e9d5…, v5_resume_4368_rules_rev26_erratum3.md 9d8ae6bc…, v5_resume_4368_rules_rev26_erratum3.sha256 ecf41f33…, excl_fields_r6.py ce5208a8…, rev26_excluded_fields_r6.json 36906ff2…, run_judgement_path1_rev26b.ps1 42fdef01…, run_judgement_path2_rev26b.ps1 2cfae0e9…, t26b_identity.json 4c110234…, t26_identity.json e65e611c…, path2_fix1_report.md 11684684…, .gitattributes d11c1811…, 디렉터리 목록 동일, ~$ 임시 파일 없음) · 경고: 형제 항목 수정 시각만 변경 1건(.git)
- 사용한 스킬: 없음

## 공개 (행위 그대로)
- **연 문서(Read)**: 정오 3 전체, `prep_report_run2.md` 전체, `path2_fix1_report.md` 전체
- **본 diff·코드**: `git diff T26 T26′ -- p2_u3.py` 전문, T26′ `p2_u3.py` `TAG` 줄(Grep)
- **transcript**
  - `agent-ac916be4`: 11:12:40Z 이후 도구 입력, 결과의 토큰 유무만
  - 이 세션 메인과 subagents: 12:00Z 이후 셸 입력
  - 메인: 14:10Z 이후 실행본·로그 관련 입력
  - 1회차 콘솔 출력이 담긴 결과 본문은 출력하지 않았다.
- **합성 실행에서 메인 매니페스트 사본(`_fixed`, `fa0b72bf`)을 합성 출력 폴더로 바이트 복사했다(원 출력 아님).**
- **열지 않은 것**: `judge_rev26_335004a/`, `rev26_stage5/`(파일 내용·목록), 436.8 저장 결과, 원 출력, 판정서, 판정 후 감사, 부록 B 내용, 블라인드(상위 폴더 검색·맨 이름 Glob 없음)
- **판정 도구 실행**: T26′ 경로 2 도구를 합성 고정물(scratchpad)에만 14단계 1회 돌렸다. 436.8 저장 결과에는 0회다.
- **종료한 프로세스**: 없음
- **지운 것**: scratchpad `verif-rev26-4p3\` 전체
