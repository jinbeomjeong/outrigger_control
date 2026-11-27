# 세션 0d95027e 블라인드 범위 호출 ↔ 판 7·판 8 오염 보고(O7·O8) 대조 (판정 후, 2026-11-26)

## 감사 요약
- 본 결과: 세션 transcript(메인 1개, 서브에이전트 117개)의 도구 입력을 읽었다. 도구 결과는 블라인드 관련 호출에서 건수·토큰 수·이름 꼴(글자를 `a`, 숫자를 `9`로 바꾼 모양)·"봉인 명세에 이미 적힌 이름인가" 참거짓·`Test-Path`의 True/False만 출력했다. 블라인드 토큰이 든 줄은 가렸다. 판정 대상 결과 파일(jsonl·npz)은 열지 않았다.
- 대상: 세션 0d95027e, 기간 2026-11-25 00:00 KST(= 11-24T15:00Z)부터. 블라인드 목록은 `.claude\blind_paths.json`(565fda22)이다. 대조 기준은 판 7 판정서 `jp3_ed7_judgement_8a2a52ce.md`(994102b7) 7.4절 O7-14~O7-27, 봉인 명세 `jp3_remedy_spec_v7.md`(10902ffd) O7-1~O7-13, 정오 1 `jp3_remedy_spec_v7_erratum1.md`(74c49bda) O7-14~O7-19, 판 8 규칙 `jp3_remedy_spec_v8_rules.md`(35f9eba8) O8-1~O8-12이다.
- 도구는 `transcript_scope.py`(실행 시작 때 sha c3c5185a)이다. 도구 호출은 5,505개, 발견은 199개(error 14, warning 98, info 87)다.
- 판정: 차단 0 / 실행 전 수정 0 / 기록 14. 판 7 판정(불합격)은 바뀌지 않는다. 새로 드러난 블라인드 **내용** 노출은 없다. 이름 노출은 봉인 명세 O7-10에 이미 적힌 이름이 다시 출력된 것뿐이다. 블라인드 파일의 존재 확인이 1회 있었다(메인 세션 `Test-Path`). 판 8 판정서에 넣을 누락분 O8-13~O8-25 초안을 아래에 적었다.

## 1. 지정 확인 항목

| 항목 | 시각(UTC / KST) | 결과 출력에 나온 것 | 대응 |
|---|---|---|---|
| 메인 `foreach … Test-Path … x11\selection.json` (error) | 11-25 15:41:51Z / 11-26 00:41 | 2줄: 경로 2개와 존재 여부(블라인드 파일 = True, 판 6 실행 폴더 쪽 후보 = False). 내용·건수는 없다. 이름은 블라인드 파일 자기 경로뿐이다 | **누락** → O8-21 |
| verif `a77b34b9` PowerShell 블라인드 조각 (error) | 11-25 17:11:13Z / 11-26 02:11 | `$ex=@('--exclude',…)` 제외 인자 배열이다(**오탐**: 배열 변수를 거친 제외 인자를 도구가 제외로 읽지 못함). 출력은 `ref_check` 요약 JSON 2줄(건수)뿐이고 블라인드 이름·내용은 없다. 같은 감사의 후보 이름 노출은 O7-23에 있다 | 오탐 (O7-23 ✓) |
| verif `a77b34b9` Grep 상위 폴더 | 11-25 17:07:14Z | `path` = ed7-impl worktree `…\prelaunch_j9`, glob `*.ps1`, 건수 모드. 출력은 ps1 57줄의 건수이고 블라인드 토큰은 0이다 | O7-21 ✓ |
| 같은 감사의 Grep `j_p3_cause` | 11-25 17:10:26Z | 0건 | O7-22 ✓ |
| 같은 감사의 Bash 파이프 | 11-25 17:14:53Z | 블라인드와 무관(git 출력 `head -1`) | **누락** → O8-24 |
| python-expert 보고의 "O8 밖 non-info 19건" | 11-26 KST | 같은 창·서브에이전트만으로 다시 세니 **22건**이다. 지정한 다섯 에이전트에서 18건, 같은 창의 `a77b34b9`에서 4건이다. 지정 다섯 에이전트의 18건 가운데 O7에 있는 것이 8건(a367044b 4건 = O7-24 (a)(b)(c), a2299dcf 2건 = O7-25, a0fede17 2건 = O7-27 (a)(b)), 누락이 10건(아래 O8-22·O8-23·O8-24·O8-25)이다. `a77b34b9` 4건은 O7-21, O7-22, 오탐 1, 파이프 1이다. 19건과의 차이는 셈 범위 차이로 보이나 확인하지 않았다 [추정] | 표 2 |

## 2. 발견별 대조표 (블라인드 범위. 파이프와 코드 폴더 검색은 3절)

시각은 UTC(괄호 안 KST)다. 분류·심각도는 도구 값이고, "당시 목록 밖"은 판 6 `selection.json`이 O7-14(11-25 16:18 KST) 뒤에 블라인드로 추가된 것을 뜻한다.

| # | 시각 | 에이전트(작업) | 도구 | 분류 / 심각도 | 출력에 블라인드 (내용·건수·이름) | 대응 |
|---|---|---|---|---|---|---|
| 1 | 11-24 15:43:52 (11-25 00:43) | compute-scheduler `ad890273` (판 7 suite 러너) | Glob `path`=`j_p3_cause`, `suite_*` | search_ancestor_scope / warning | 없음. 출력 6개 가운데 5개가 하위 폴더 파일이다 → Glob이 재귀로 `j9_runs`를 순회했다 | **누락** O8-13 |
| 2 | 11-24 15:44:12 | python `a04570b6` (고정 표) | Glob worktree 루트, `04_scripts/**/…` | ancestor / info | 확인 안 함(패턴 고정 폴더는 블라인드 밖) | **누락** O8-19 |
| 3 | 11-24 23:28:58 ×2 | control `a87bd58c` (개정 6) | Glob `j_p3_cause` ×2 | warning | 없음 | O7-13 ✓ |
| 4 | 11-25 00:40:20 | verif `aac40632` (판 7 봉인 전 감사) | Bash `git ls-files -- 'prelaunch_j9/*confirm_b_grid192*'` | ancestor_listing / error(당시 목록 밖) | 없음(맞는 이름 0개) | **누락** O8-14 |
| 5 | 11-25 00:48:50 | 같음 | PowerShell 임시 `refs.py`, 검색 기준 `j9_runs`·ed7-impl worktree 루트 (도구가 잡지 못함) | — | 이름 3개. 셋 다 봉인 명세 O7-10에 이미 적힌 이름이고, 찾지 못한 참조 목록 꼴이다 [추정]. 내용·건수는 없다 | **누락** O8-14 |
| 6 | 11-25 07:17:01·07:17:02·07:17:21 | python `a0f6f094` (판 6 docstring 별건) | Glob 루트 ×2(warning 1, info 1), Grep `j_p3_cause` glob content | warning | 없음(이름 3·6개, erratum1 본문 16줄) | **누락** O8-15 |
| 7 | 11-25 07:17:05 | python `ae7b1c86` (실행 커밋 C) | Glob worktree 루트 | info | 0건 | **누락** O8-16 |
| 8 | 11-25 07:17:18 | 같음 | Grep `path`=ed7-impl wt `…\prelaunch_j9`, 좁힘 없음, content | error(당시 목록 밖) | 없음(ps1 3줄) | **누락** O8-16 |
| 9 | 11-25 07:18:41 | 같음 | Bash `git ls-files prelaunch_j9/{5개}` + `ls prelaunch_j9/` | error + warning | 블라인드 폴더 아래 이름은 없다. `ed6_inputs/x11` 추적 이름 9줄(그중 1줄은 `selection.json` 자기 이름) | **누락** O8-16 |
| 10 | 11-25 07:18:47 | 같음 | `Get-Content selection.json` 1회차(키 이름·명령·scan 30줄·run_commands 4줄) | fragment / error(당시 목록 밖) | **내용 있음**(그 파일의 키·명령 줄). 블라인드 이름 토큰은 0이다 | **O7-14 부분**(1회차 누락) → O8-16 |
| 11 | 11-25 07:18:50 | 같음 | `Get-Content selection.json` 2회차(`inputs`) | error | 블라인드 이름 토큰 30개(파일 이름 꼴 10개와 `logs` 경로 줄) | O7-14 ✓ |
| 12 | 11-25 07:40:40 | python `af4af02e` (도구 보완) | scratch 합성 저장소 `New-Item …\cdry_a1\logs` | fragment / error ×2 | 합성 fixture 이름뿐 | **오탐** |
| 13 | 11-25 07:43:55 ×2, 07:44:34, 07:47:27, 07:48:44, 08:02:48 | python `a68bbfd1` (판정 커밋 T) | Glob wt 루트 ×2(info), Grep ed7-judge wt `prelaunch_j9`(glob ps1), Grep wt 루트 ×2(glob py), `Get-ChildItem` wt 루트(인자 오류로 실행되지 않음) | warning·info | 없음(Grep 3회 모두 0건) | **누락** O8-17 |
| 14 | 11-25 09:23:31, 09:28:27 | verif `a729ca19` (T 감사·실행 전 감사, `audit_prerun_T_erratum1`) | Grep ed7-impl wt `prelaunch_j9`(glob ps1, 0건), Grep ed7-judge wt 루트(glob `**/j_p3_inputs.py`, 26줄) | warning | 없음 | **누락** O8-18 |
| 15 | 11-25 09:32:42 / 09:33:09 / 09:33:23 | 같음 | `$ex=@(--exclude …)` + `ref_check` ×3 | fragment / error ×3 | 앞의 두 회는 없음. 셋째 회(`--rev e241638d` 명세)에 이름 2개가 나왔다. ① `ref_missing` 줄의 블라인드 패턴 꼴 이름 1개는 명세 O7-10 글을 그대로 인용한 것이다. ② "git 작업 트리에도 비슷한 이름" 후보 1개는 `cdry_a1` 아래 블라인드 정의 밖 이름이고, 감사 원문 R-14에 있으며 O7-10에도 이미 적힌 이름이다. `cdry_a1` 폴더 자체는 제외하지 않았으므로 그 안을 순회했다 | **누락** O8-18 (조각 자체는 오탐) |
| 16 | 11-25 11:49:28, 11:52:36 | control `afdac11e` (정오 1 T′ 채움) | Glob ed7-judge wt 루트 ×2 | info | 확인 안 함(패턴 `04_scripts/**`) | **누락** O8-19 |
| 17 | 11-25 12:15:44 | verif `ada99fa7` (T′·정오 1 재감사) | Glob `j_p3_cause`, `*{ed7,v7}*{p2,…}*` | warning | 0건 | **누락** O8-20 |
| 18 | 11-25 14:58:16 | 같음(확인 감사) | Grep `j_p3_cause` 건수 | warning | 명세 8개 건수 | O7-19 ✓ |
| 19 | 11-25 15:41:51 | **메인** | `Test-Path` 블라인드 파일 | fragment / error | 존재 여부만(True). 내용 없음 | **누락** O8-21 |
| 20 | 11-25 16:13:13 | python `a1dfd1ce` (실행 준비) | `Get-ChildItem "$j\606f8713"` 등 (도구가 잡지 못함, 계산 경로) | — | 폴더 이름 `cdry_a1` 2회(블라인드의 부모 이름) | O7-20 ✓ |
| 21 | 11-25 17:07~17:11 | verif `a77b34b9` | 1절 | — | 1절 | O7-21·22 ✓, 오탐 |
| 22 | 11-26 04:03:14 (13:03) | verif `a367044b` (판정 후 감사) | Glob 루트 `…/jp3_remedy_spec_v7*` | warning | 없음(4개 이름) | **누락** O8-22 |
| 23 | 11-26 04:05:35, 04:13:13·23, 04:16:20 | 같음 | Glob 루트 v5_criteria, `gci -Directory`·`-File`, `git ls-files` | warning | 없음 | O7-24 (a)(c)(b) ✓ |
| 24 | 11-26 04:13:05 ×2, 04:16:12 | 같음 | Glob 루트(패턴 `…/ed7_design/…`, `…/ed6_design/…`) | info | 확인 안 함 | **누락** O8-19 |
| 25 | 11-26 04:05:17, 04:05:35 | control `a2299dcf` (원인 분석) | `$b='…j9_runs'; Get-ChildItem $b -Directory` ×2 (도구가 잡지 못함) | — | 폴더 이름들 | O7-25 ✓ |
| 26 | 11-26 04:05:21 | 같음 | Bash `cd j_p3_cause; ls` | ancestor_listing / warning | 블라인드 토큰 0(`j_p3_cause` 최상위 이름) | **누락**(O7-25 범위 밖) O8-23 |
| 27 | 11-26 04:07:40, 04:09:50 | 같음 | Grep wt 루트 ×2(glob py) | warning | 없음 | O7-25 ✓ |
| 28 | 11-26 04:58:24 (13:58) | **메인** | `$r='…j9_runs'; Get-ChildItem $r -File -Filter '*8a2a52ce*LOCAL_ONLY*'` (도구가 잡지 못함) | — | 없음(비블라인드 1개와 sha) | **누락** O8-21 |
| 29 | 11-26 04:59:46, 05:08:01 | verif `a0fede17` (판정서 감사) | `gci -Filter v7*`, Grep `j_p3_cause` | warning | 없음 | O7-27 (a)(b) ✓ |
| 30 | 11-26 05:24:39·40 | stats `a3e4d098` | Glob `j_p3_cause` ×2 | warning | 없음 | O8-10 ✓ |
| 31 | 11-26 06:40:52~06:44:24 | stats `a50adde6` | Glob 루트 ×4(warning 2, info 2) | — | 없음 | O8-7 ✓ |
| 32 | 11-26 06:42:30 | python `a84e5dcd` | Grep ed8-impl wt 루트 | warning | — | O8-9 ✓ |
| 33 | 11-26 08:01:14·19·28, 08:09:06·24 | verif `aee5ec0b` (S8-R 봉인 전 감사) | `ls ed6_inputs/`, Grep `j_p3_cause`, `gci $r -Filter`, 파이프 2 | warning | `x11` 이름 1개 등 | O8-12 (1)~(4) ✓ |
| 34 | 11-26 08:11:24 | 같음 | `git grep … 7fc83456 -- '*.py'` + `git worktree list` | ancestor_listing / warning | 없음(36줄, 블라인드 토큰 0). 7fc83456 트리에는 블라인드 부모 폴더가 있다(cat-file 종료 0) | **누락** O8-25 |
| 35 | 11-26 10:06~10:07 ×5 | control `a65e86a8` (논문 v5 IMUA 조사) | Glob v5-imua wt 루트 | info | — | 해당 없음: 그 worktree(2ea96c96, 11-22)에는 블라인드 사본이 없다(cat-file 종료 128) |
| 36 | 11-26 10:28~10:32 | python `ac916be4`·`a2b9da21` (436.8 rev26 경로 1·2) | `ls .claude/worktrees/`(warning, worktree 이름 목록), 메인 루트 `git ls-files '*v5paper_imua_rules*'`(error, 출력 비블라인드 1), rev26-p1 `git ls-files`(error)·Grep(warning), rev26-p2 Glob(info), 파이프 5 | — | 없음 | rev26-p1·p2(932f1fb1)에는 블라인드 사본이 없다(종료 128) → 해당 호출은 실질적으로 해당 없음. 메인 루트 `ls-files`와 `ls .claude/worktrees`는 **확인 필요**(판 8 밖 작업) |

- 메인 세션의 Bash 파이프 9건과 `run_in_background` 2건은 표에서 뺐다. 메인 세션은 서브에이전트 공통 실행 규칙의 대상이 아니다.
- O7·O8에 있으나 도구가 잡지 못한 것(경로가 스크립트 안·계산값·도구 출력이라서)은 O7-15, O7-17, O7-18, O7-20(내 보조 검색으로 확인), O7-23, O7-25의 목록 명령(보조 검색으로 확인), O7-27 (c), O8-12 (5)다. 정상적인 한계다.

## 3. 블라인드와 무관한 절차 발견
- **Bash 파이프(서브에이전트, 금지 규칙)**: 모두 git·grep·sed 출력을 자르는 용도이고, 다룬 경로는 블라인드 밖이다.

  | 에이전트 | 횟수 | 들어간 O8 초안 |
  |---|---|---|
  | `aac40632` verif | 24 | O8-14 |
  | `a437d6e7` python(B-2) | 1 | O8-24 |
  | `aa51b41b` compute | 2 | O8-24 |
  | `a4c90a59` integrity | 3 | O8-24 |
  | `a0f6f094` python | 1 | O8-15 |
  | `ae7b1c86` python | 3 | O8-16 |
  | `a729ca19` verif | 1 | O8-18 |
  | `a77b34b9` verif | 1 | O8-24 |
  | `a2299dcf` control | 2 | O8-23 |
  | `a27776e7` python | 5 | O8-24 |
  | `aee5ec0b` verif | 2 | O8-12 (4) ✓ |
  | `ac916be4`·`a2b9da21` python(rev26) | 5 | 확인 필요 |

- **코드 폴더 전체 검색(`watched_scope`, info) 69건, 22개 에이전트**: 대상은 `04_scripts` 자체(메인과 worktree)이고 모두 glob `*.py` 등으로 좁혔다. 블라인드 상위 폴더가 아니다. O8-6·O8-8·O8-11이 그중 3개 작업을 공개했다. 나머지는 규칙 위반이 아니므로 O8에 낱낱이 옮길 필요는 없다고 본다(확인 필요 2).
- compute `ad890273`(11-24 15:44:37Z)은 ed7-impl `05_tests`에서 패턴 `cdry_a1|VBK_c9[23]|606f8713`을 Grep했다. 출력은 시험 코드 29줄이다. 블라인드 패턴과 같은 꼴의 이름이 코드 글자로 나왔다(파일 이름 꼴 5개 포함, 이름 11개 가운데 7개는 봉인 명세에 이미 있다). 블라인드 경로를 연 것은 아니어서 기록에서 뺐다 [추정: 새 노출 아님].

## 발견 사항 (심각도순)
모두 **[기록]**이다. 판정 결론에는 영향이 없고 판정서에 적을 것들이다.

1. [기록][T·I] O7 목록에 빠진 블라인드 범위 호출 13묶음(위 표의 "누락"). 판 8 오염 보고 O8-13~O8-25 초안을 4절에 둔다. 근거는 transcript 줄이다. 각 행의 에이전트 id와 tool_use id 끝 8자리는 아래와 같다.
   - `ad890273` oW7sGYXP
   - `aac40632` LPctXsVZ·HJFpTdGM
   - `a0f6f094` 6NhMMV6H·a1QbTWGJ·dsmzmgLQ
   - `ae7b1c86` ui46GXn6·b69YWkJX·eWBW2LHQ·duNEBdVD
   - `a68bbfd1` axFWQMax·ikxfsESr·PK4T3LAd·ZZxEA99C·jejdyeir·XSjnsiCh
   - `a729ca19` FpJHBVth·D2RafKtv·RfQn291u
   - `afdac11e` 1XSCuect·KE4zHzJS
   - `ada99fa7` vkvZ5XRG
   - 메인 WPk41XHK·Hr1TTHWJ
   - `a367044b` MwPM21uh·Bn5tzQre·RuSp8bV3·kzjioKxD
   - `a2299dcf` QCmWtWN3
   - `aee5ec0b` KA6AoQ6V
2. [기록][T] 자기 공개 문장이 실제 호출과 다르다. `ed7_design/postseal/handback_judge_commit_T.md` 90행은 "검색 범위는 모두 경로를 직접 지정했다"고 적었다. 그러나 같은 작업에서 ed7-judge worktree 루트를 `path`로 쓴 Grep이 2회, `prelaunch_j9` Grep이 1회 있었다(행 13). O8-9와 같은 꼴이다. sha로 인용되는 보고이므로 고치지 않고 O8-17에 적는다.
3. [기록][T] O7-14는 `selection.json` 출력 2회 가운데 둘째(`inputs`)만 적었다. 첫째(07:18:47Z)는 블라인드 이름 없이 그 파일의 키 이름·명령 줄을 출력했다(행 10). 이 파일이 블라인드 목록에 들어가기 전의 일이다.
4. [기록][T] 메인 세션의 블라인드 파일 `Test-Path` 1회(행 19)는 존재 여부만 출력했다. 메인의 `j9_runs` 최상위 필터 목록 1회(행 28)는 도구가 잡지 못했다.
5. [기록][E] `blind_guard`·`transcript_scope`는 "얕은 패턴 Glob이면 훅 통과"로 판단한다. 그러나 Claude Code Glob은 `path`가 상위 폴더일 때 맨 이름 패턴(`suite_*`, `jp3_*ed6*.md`)도 하위 폴더까지 맞춘다. 행 1의 출력 6개 가운데 5개가 하위 폴더 파일이었고, O7-13 원문도 같은 현상을 적었다. 그러므로 `path=j_p3_cause` + 맨 이름 패턴은 `j9_runs` 순회를 동반한다. → 위임 필요(python-expert).
6. [기록][E] `transcript_scope`는 공백 없는 작은따옴표 대입 `$b='…'; Get-ChildItem $b -Directory`를 풀어 읽지 못했다(행 25·28). 같은 꼴이 메인과 control에 3회 있었다. 또 `$ex=@('--exclude',…)` 배열을 블라인드 조각 error로 잡는다(오탐 4회, 행 15·21). → 위임 필요(python-expert).

## 4. 판 8 판정서 오염 보고 덧붙임 초안 (O8-13~)

| # | 때 | 내용 | 처리 |
|---|---|---|---|
| O8-13 | 판 7 suite 러너 계획(compute-scheduler-expert, 2026-11-25 00:43 KST) | Glob 1회, `path` = `…\j_p3_cause`, 패턴 `suite_*`. Glob이 하위 폴더까지 맞춰(출력 6개 중 5개가 `ed6_design/…`·`review_evidence/…` 아래) 블라인드를 품은 `j9_runs` 아래를 순회했다. 출력은 그 6개 이름뿐이고 블라인드 이름·건수·내용은 없었다 | 공개 |
| O8-14 | 판 7 봉인 전 감사(verif-protocol-auditor, 11-25 09:40~10:21 KST) | (1) `git ls-files -- '…/prelaunch_j9/*confirm_b_grid192*'` 1회. 인덱스 전체에 글롭 pathspec을 썼고 맞는 이름은 0개였다. 그때 판 6 `selection.json`은 블라인드 목록 밖이었다. (2) 명세 참조 경로 확인용 임시 스크립트 1회의 검색 기준 폴더로 `j9_runs`와 ed7-impl worktree 루트를 줬다. 출력은 찾지 못한 참조 이름 목록이고, 그중 3개는 봉인 명세 O7-10에 이미 적힌 이름이다. 스크립트가 지워져 폴더를 순회했는지는 확인할 수 없다. (3) 금지된 Bash 파이프 24회(블라인드 밖 git·grep·sed 출력 자르기) | 공개 |
| O8-15 | 판 6 docstring 별건(python-expert, 11-25 16:17 KST) | Glob 2회, `path` = 저장소 루트(패턴 `…/j_p3_cause/jp3_remedy_spec_v6_erratum*.md`, `…/ed6_design/*audit*`, 출력 이름 3·6개). Grep 1회, `path` = `…\j_p3_cause`(glob `jp3_remedy_spec_v6_erratum*.md`, 내용 모드, 출력은 정오 1 본문 16줄). Bash 파이프 1회. 블라인드 이름·건수는 없었다 | 공개 |
| O8-16 | 판 7 실행 커밋 C(python-expert, 11-25 16:17~16:33 KST, O7-14와 같은 작업) | (1) Grep 1회, `path` = ed7-impl worktree `…\prelaunch_j9`, glob 없이 내용 모드(패턴 `Get-CoreKind`, 출력 ps1 3줄). (2) `git ls-files`로 `prelaunch_j9` 하위 폴더 5개를 나열하고 `ls prelaunch_j9/`를 1회 돌렸다. 출력 77줄에 `ed6_inputs/x11` 아래 추적 파일 이름 9줄이 있다(그중 1줄은 판 6 `selection.json` 자기 이름). 블라인드 폴더 아래 이름은 없다. (3) O7-14의 `inputs` 출력 바로 앞에 판 6 `selection.json`을 한 번 더 열어 최상위 키 이름·생성 명령·`scan` 블록 30줄·`run_commands` 4줄을 출력했다. 블라인드 이름은 없었다. (4) worktree 루트 Glob 1회(0건), Bash 파이프 3회. (1)~(3)은 `selection.json`이 블라인드 목록에 들어가기 전이다 | 공개 |
| O8-17 | 판 7 판정 커밋 T(python-expert, 11-25 16:43~17:02 KST) | Grep 3회, `path` = ed7-judge worktree. `…\prelaunch_j9`에 glob `run_steps*/*.ps1`로 1회, worktree 루트에 glob `{03_src,04_scripts}/**/*.py` 등으로 2회 했고, 출력은 모두 0건이다. worktree 루트 Glob 2회(패턴 `04_scripts/**`)는 T 보고 6절에 공개돼 있었으나 O7에 옮기지 않았다. worktree 루트 `Get-ChildItem` 1회는 인자 오류로 실행되지 않았다. T 보고(`handback_judge_commit_T.md` 90행)의 "검색 범위는 모두 경로를 직접 지정했다"는 실제 호출과 다르다(sha로 인용되는 보고는 고치지 않고 여기 적는다) | 공개 |
| O8-18 | 판 7 T 감사·실행 전 감사(verif-protocol-auditor, `audit_prerun_T_erratum1_20261125.md`, 11-25 18:23~18:33 KST) | (1) Grep 1회, `path` = ed7-impl worktree `…\prelaunch_j9`(glob `run_steps*/*.ps1`, 0건). (2) Grep 1회, `path` = ed7-judge worktree 루트(glob `**/j_p3_inputs.py`, 출력은 그 파일 26줄). (3) `ref_check`(제외: 블라인드 3패턴, `.claude`, 판 6 `selection.json`, `cdry_a1` 폴더 자체는 제외 안 함)가 비슷한 이름 후보로 `cdry_a1` 아래 블라인드 정의 밖 파일 이름 1개를 출력했다(감사 원문 R-14). 같은 출력의 `ref_missing` 줄 1개는 명세 O7-10 행의 블라인드 패턴 꼴 이름을 인용으로 되풀이했다. 두 이름 모두 봉인 명세 O7-10에 이미 적혀 있다. (4) Bash 파이프 1회 | 공개 |
| O8-19 | 판 7·8 여러 작업의 루트 Glob(패턴의 고정 폴더는 블라인드 밖) | `path`에 저장소 루트나 블라인드 사본을 품은 worktree 루트를 준 Glob이다. 고정 표 계산(python, 11-25 00:44 KST) 1회, 정오 1 T′ 채움(control, 11-25 20:49·20:52 KST) 2회, 판 7 판정 후 감사(verif, 11-26 13:13·13:16 KST) 3회다. O8-15·O8-16·O8-17의 루트 Glob도 같은 꼴이다. 출력에 블라인드 이름·건수는 없었다. "블라인드를 품은 상위 폴더는 glob을 좁혀도 path로 쓰지 않는다" 규칙 위반이다(O8-7의 info 2회와 같은 꼴) | 공개 |
| O8-20 | 정오 1 재감사(verif-protocol-auditor, 11-25 21:15 KST, O7-19와 같은 에이전트) | Glob 1회, `path` = `…\j_p3_cause`, 패턴 `*{ed7,v7}*{p2,path2,handoff,넘김}*`, 0건. 맨 이름 패턴 Glob은 하위 폴더까지 맞추므로 `j9_runs` 아래를 순회했다 | 공개 |
| O8-21 | 메인 세션(11-26 00:41 KST, 13:58 KST) | (1) 판 6 `prelaunch_j9/ed6_inputs/x11/selection.json`(블라인드 파일)과 판 6 실행 폴더 안 같은 이름 후보 경로에 `Test-Path` 1회. 출력은 두 경로와 존재 여부(블라인드 파일은 있음)뿐이고 내용은 읽지 않았다. (2) 블라인드를 품은 `j9_runs` 최상위에 비재귀 `Get-ChildItem -File -Filter '*8a2a52ce*LOCAL_ONLY*'` 1회(출력은 비블라인드 파일 1개와 sha) | 공개 |
| O8-22 | 판 7 판정 후 감사(verif-protocol-auditor, 11-26 13:03 KST, O7-24와 같은 감사) | Glob 1회, `path` = 저장소 루트, 패턴 `06_analysis/02_control/j_p3_cause/jp3_remedy_spec_v7*`(출력 4개 이름). O7-24 (a)의 Glob과 별개다 | 공개 |
| O8-23 | 판 7 원인 분석(control-expert, 11-26 13:05 KST, O7-25와 같은 작업) | `cd …\j_p3_cause; ls` 1회로 `j_p3_cause` 최상위 이름을 출력했다(O7-25는 `j9_runs` 목록만 적음). Bash 파이프 2회 | 공개 |
| O8-24 | 금지된 Bash 파이프(블라인드 무관, 위 행 밖) | 판 7 B-2 probe 몫 계산(python) 1회, a2 재현 배치(compute-scheduler) 2회, 봉인 커밋 무결성(integrity) 3회, 본 실행 전 감사(verif, O7-21~23 감사) 1회, 판 8 P-1~P-3 구현(python) 5회. 모두 git·grep 출력을 자르는 용도이고 블라인드 경로를 다루지 않았다 | 공개 |
| O8-25 | S8-R 봉인 전 감사(verif-protocol-auditor, 11-26 17:11 KST, O8-12 보충) | `git grep -n -E … 7fc83456 -- '*.py'` 1회. 블라인드 사본을 담은 커밋 트리 전체를 pathspec `*.py`로 검색했고, 출력은 .py 줄이다. `git worktree list` 1회(worktree 이름 목록). 블라인드 이름·건수는 없었다 | 공개 |

- 처리 원칙: 위 행에 블라인드 **내용** 노출은 없다. 이름 노출은 O8-14 (2)와 O8-18 (3)의 이미 공개된(O7-10) 이름 재출력뿐이다. 존재 확인은 O8-21 (1) 1회다.
- 436.8 rev26과 논문 v5 작업 호출(표 행 35·36)은 확인 필요 1에 둔다.

## 5. 판 7 판정서 정오 초안 (짧게)
> **정오(2026-11-26, 세션 transcript 대조)**: 7.4절 O7 목록에 transcript의 블라인드 범위 호출이 다 들어 있지 않았다. 빠진 호출은 판 8 판정서 오염 보고 O8-13~O8-25에 적었다. 블라인드 파일 내용의 노출은 없다. 이름은 봉인 명세 O7-10에 이미 적힌 이름이 다시 출력된 것뿐이다(O8-14·O8-18). 블라인드 파일 존재 확인 1회는 메인 세션이다(O8-21). O7-14의 판 6 `selection.json`은 2회 출력됐다(1회차는 키 이름·명령·scan 블록, 블라인드 이름 없음, O8-16). T 보고의 "검색 범위는 모두 직접 지정"은 실제 호출과 다르다(O8-17). 판정 결론은 바뀌지 않는다.

## 확인 필요
1. 판 8 밖 작업(436.8 rev26 경로 1·2 python, 논문 v5 IMUA 조사 control, 11-26 19:02~19:32 KST)의 호출을 O8에 넣을지 정해야 한다.
   - 메인 루트 `git ls-files '*v5paper_imua_rules*'`(인덱스 전체, 출력 비블라인드 1개)
   - `ls .claude/worktrees/`(worktree 이름 목록)
   - 파이프 5회
   - rev26-p1·p2(932f1fb1)와 v5-imua(2ea96c96) worktree 루트 검색은 그 트리에 블라인드 사본이 없어 실질적으로 해당 없다.
2. 코드 폴더 전체 검색 69건(info)을 O8에 한 줄로 요약할지, 공개 대상에서 뺄지 정해야 한다. 블라인드 규칙 위반은 아니다. O8-6·O8-8·O8-11은 "지시 범위 해석에 따라 위반일 수 있다"로 적었다.
3. O8-21(메인 세션)의 공개 문구를 메인 세션이 사실대로 확인해야 한다.

## 위임 필요 (python-expert, `tools/verif`)
- `transcript_scope.py` / `_blind_shell.py`: 공백 없는 작은따옴표 대입 `$b='C:\…\j9_runs'; Get-ChildItem $b -Directory`를 풀어 읽지 못한다. 재현은 세션 0d95027e의 `a2299dcf` JUL69AwF·QsUbH3oe와 메인 Hr1TTHWJ다. 2026-11-26 19:36 KST 판(e75d0fd7)으로 다시 돌려도 발견 수가 같다.
- `blind_guard.py`·`transcript_scope.py`: "얕은 패턴 Glob → 훅 통과"는 사실과 다르다. Claude Code Glob은 맨 이름 패턴도 하위 폴더까지 맞춘다(재현 `ad890273` oW7sGYXP, 출력 6개 중 5개가 하위 폴더 파일). 상위 폴더 `path` + 맨 이름 패턴을 재귀로 보고 막거나 warning 이상으로 올려야 한다.
- `transcript_scope.py`: `$ex=@('--exclude', "…블라인드…")` 배열을 써서 `@ex`로 넘긴 제외 인자를 블라인드 조각 error로 잡는다(오탐 4회: `a729ca19` Ub6QBmNi·hu2JhfLX·RfQn291u, `a77b34b9` 2TjPmxxZ). 제외 배열 꼴을 인식하거나 info로 낮추는 것을 권한다.
- README 1105행 "O8 밖 발견(info 제외) 19건"을 같은 창으로 다시 세면 22건이다(이 보고 1절). 셈 범위를 적어 달라.

## 메인 세션 권고
- 저장 뒤 판 8 판정서를 쓸 때 4절 O8-13~O8-25를 넣고, 판 7 판정서에 5절 정오를 덧붙인다(봉인 S8-R 문면은 고치지 않는다, 사용자 결정 2026-11-26).

## 검사하지 못한 것
- 지워진 임시 스크립트 `verif-ed7seal\refs.py`(O8-14 (2))가 `j9_runs`를 실제로 순회했는지는 확인하지 못했다. 출력 머리 줄 꼴("candidate refs … found … not found")로 보아 이름 대조로 추정한다.
- info 발견 가운데 출력을 열어 보지 않은 것(행 2·16·24의 루트 Glob 6회): 패턴의 고정 폴더가 블라인드 밖이라 블라인드 이름이 나올 수 없다고 보고 확인하지 않았다.
- 스크립트 파일 안에서 여는 경로(`python x.py`)는 도구 한계로 보지 못한다. 보조 검색은 도구 입력 글자만 본다.
- 2026-11-25 00:00 KST 이전 기간(O7-1~O7-12 대상 기간)은 이번 창 밖이다.

## 실행한 검증
- 의존성 점검: STAMP(생략).
- 인터프리터는 python-dev `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`MKL_THREADING_LAYER=TBB`, 한글 출력은 `-X utf8`)이다.
- `transcript_scope.py <메인 jsonl> <subagents 폴더> --blind-list <repo>\.claude\blind_paths.json --since 2026-11-25T00:00:00+09:00 --watch 04_scripts --max-chars 400 --format json/md`: 종료 1, 호출 5,505, 발견 199. 도구가 바뀐 뒤 e75d0fd7 판으로 `--until 2026-11-26T10:35Z`를 주고 다시 돌렸다. 발견 수는 같다(199 / error 14 / warning 98 / info 87).
- 보조 스크립트(scratchpad `verif-o-crosscheck`, 모두 지움)는 아래와 같다. 모두 도구 입력 전체와 결과의 메타·토큰 수·이름 꼴만 출력했다.
  - 발견 요약
  - 상세(입력 전체, 결과 길이·블라인드 토큰 수, 블라인드 줄은 가린 미리보기)
  - 이름 꼴·봉인 명세 포함 여부
  - 에이전트 첫 지시문 앞 230자
  - 도구가 잡지 못한 블라인드 인접 폴더 언급 입력 목록
- git(조회만): `git show -s --format` 커밋 6개 시각, `git cat-file -e <커밋>:…/j9_runs/606f8713/cdry_a1` 6회(종료 코드만: 932f1fb1·2ea96c96 = 없음, HEAD·60ebb4a4·47b184af·7fc83456 = 있음).
- 메인 transcript는 이 세션이 쓰는 중인 파일이라 source_guard 입력에서 뺐다(시작 때 24,548줄).
- 원본 불변: 위반 — 원본 내용 변경 1건(transcript_scope.py); 형제 항목 내용 변경 3건(README.md, _blind_selftest.py, _blind_shell.py) · 경고: 형제 항목 수정 시각만 변경 1건(ed8_design)
  - 해석: 내가 고친 것이 아니다. 감사 중 다른 에이전트가 `~/.claude/tools/verif`의 `transcript_scope.py`(19:36:24 KST, e75d0fd7)·`_blind_shell.py`(19:35:52)·README·`_blind_selftest.py`를 고쳤고(transcript에 python-expert `a7975803`의 같은 시간대 편집 기록이 있다), `ed8_design` 폴더 시각도 바뀌었다.
  - 봉인·판정 입력 4개(blind_paths.json·판 7 판정서·명세 v7·정오 1·판 8 규칙)는 바뀌지 않았다.
  - 최종 판정은 새 판으로 다시 돌린 결과(같은 수)와 원래 실행을 함께 기준으로 한다.
- 메모리 `audit_pitfalls.md`에 한 항목을 덧붙이고 `MEMORY.md` 색인 줄을 고쳤다.
- 사용한 스킬: 없음

## 공개(이 감사의 행위 그대로)
- 블라인드 경로와 그 상위 폴더(`j_p3_cause`, `j9_runs`, `prelaunch_j9`, worktree 루트)를 Grep·Glob 범위로 쓰지 않았다.
  - Grep은 파일 경로를 직접 지정해서만 했다: 판 7 판정서, 명세 v7, 정오 1, 판 8 규칙, `ed7_design/postseal` 안 감사·보고 2개, verif README.
  - Glob은 `ed7_design\postseal` 폴더에 1회 했다(블라인드 상위 아님).
- `blind_paths.json`을 Read했다.
- transcript를 읽을 때 블라인드 관련 호출의 결과는 다음만 출력했다. 블라인드 이름 자체는 출력하지 않았다.
  - 토큰 수
  - 이름 꼴(`aaa_a99.aaaa`, `aaaa_a9/aaa9_a99.aaaa`)
  - "봉인 명세 v7 본문에 이미 있는 이름인가" 참거짓
  - 출력 머리 줄의 일반 낱말
  - `Test-Path`의 True/False
- 블라인드와 무관한 호출 몇 개는 결과 미리보기를 봤다. 블라인드 토큰 줄은 가렸다.
- 블라인드 부모 폴더(`cdry_a1`)가 커밋 6개에 있는지 `git cat-file -e`로 종료 코드만 확인했다. 폴더 안 이름은 나열하지 않았다.
- PowerShell에서 `> $null`(출력 버림) 1회를 썼다. 파일 쓰기는 없었다.
- Bash 도구는 쓰지 않았다.
