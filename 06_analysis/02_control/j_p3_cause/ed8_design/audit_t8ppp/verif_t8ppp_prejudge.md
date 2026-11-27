## 감사 요약
- 의존성 점검: 모두 있음(numpy 2.5.3, pyyaml 6.0.3, git, CHECKED 2026-11-27 18:16)
- 본 결과: 판정 값은 보지 않았습니다. 연 파일은 둘입니다. `j9_runs\56849248\impl_cases.done`(단계 기록: 종료 코드·커밋·정체성)과 `_identity_checks\impl_cases_a1.md`(정체성 점검, "발견 사항 없음")입니다. 나머지 7개 `_identity_checks\*.md`는 "발견 사항 없음" 문자열 건수만 셌습니다(8/8). 블라인드 `impl_*_a1\`·`l1ref_a1\`과 worktree 사본은 Read·Grep·Glob·스캔 어디에도 쓰지 않았습니다.
- 대상: T8‴ = `2263b2461238da7f93eda147838c01c847315561`(ed8-judge3, locked). 부모는 T8″ 5955f25b, C8은 56849248. 시점은 실행 전(4단계 관문 판정 전)입니다.
- 기준 문서: `jp3_remedy_spec_v8_rules.md` sha256 `35f9eba8`(`.sha256` `e19aaa48`와 일치, master 2715230e, LF, `-text`)
- 명세: `control_d1_settings.md` `c84ebb38`, `d1_settings.json` `c4838c47`. 구현 보고: `impl_report_t8ppp.md` `aba8232f`(SUMS `cc09451b`)
- 판정: 차단 0 / 실행 전 수정 2 / 기록 6
  - D-1·D-1b·D-1c 수정은 명세 4절대로 들어갔습니다. P8-11 바이트 조건도 독립 대조로 충족합니다.
  - 4단계 관문 판정은 할 수 있습니다. 조건은 셋입니다: P8-4 실행이 끝나고, 판정 checkout을 정리하고, 판정 명령을 T8‴로 바꾼 뒤.
  - P8-4 수치는 판정하지 않았습니다.

## 발견 사항 (심각도순)

### [실행 전 수정][I·E] M-1. P8-4 러너가 판정 checkout ed8-judge3 안에서 지금 돌고 있고 ignored `__pycache__`를 만들고 있다
- 근거
  - 프로세스 조회 결과(읽기만): PID 92564가 `Chrono-dev python.exe -I -B -m pytest 05_tests/unit -n 12 --dist loadfile … --junitxml=C:\Users\jinbeom\.claude\runners\outrigger-ed8\p84_t8ppp_2263b246\out\…`이고, 시작은 18:17:27입니다. 자식 프로세스들이 `…\ed8-judge3\05_tests\unit\*.py`, `…\ed8-judge3\04_scripts\…\d0_plant_split.py`를 실행합니다. `pre_k1_preset_runner.py`는 `-I`만 있고 `-B`가 없습니다.
  - `git -C ed8-judge3 status --porcelain --ignored`에 `!! …/__pycache__/`가 11개, 다시 보니 13개였습니다(03_src 4, 04_scripts 9). 추적 파일 변경(porcelain)은 없습니다.
  - source_guard `--strict-additions`가 입력 폴더 `__pycache__` 추가 1건으로 위반을 냈습니다. 스냅숏은 18:16:36으로 P8-4 시작보다 앞섭니다. 제 실행은 `-B`와 `PYTHONDONTWRITEBYTECODE=1`을 붙였으므로 P8-4 탓으로 봅니다([추정]).
  - 판정 도구의 `code_identity`는 `git status --porcelain`(ignored 제외)만 봅니다(`jp3_ed7_judge.py:269-276`, `jp3_ed8_gate_judge.py:210-217`). 그래서 `is_clean`에는 영향이 없습니다. 반면 prejudge 판정 명령 초안의 마지막 검사(`status --porcelain --ignored` 빈 출력, `prejudge_report.md:157`)는 실패합니다.
- 실패 시나리오
  - P8-4가 끝나기 전에 관문 판정을 돌리면 P8-4와 같은 checkout을 함께 씁니다. P8-4의 T-e 시험(`test_ed8_jp3_settings.py:298-313`, 작업 트리 diff·rglob)과 판정이 겹칩니다.
  - 남은 pyc 때문에 "판정 checkout 깨끗함" 공개 문구가 사실과 달라집니다.
- 권장 조치(메인)
  - P8-4 `.done`·종료를 확인한 뒤 `git -C ed8-judge3 status --porcelain --ignored`가 보여 주는 `__pycache__` 경로만 하나씩 지정해 지웁니다.
  - 빈 출력을 확인하고 관문 판정을 시작합니다. 아래 수정 명령이 이 검사로 시작합니다.

### [실행 전 수정][R] M-2. prejudge 판정 명령 초안이 T8″(ed8-judge2, `judge_5955f25b`)를 가리킨다
- 근거
  - `prejudge_report.md:140,143`: `$j = …\ed8-judge2`, `$o = "$r\judge_5955f25b"`
  - 규칙 11.2(`jp3_remedy_spec_v8_rules.md:354`)와 prejudge 4절은 단일 T8을 요구합니다. 4단계 관문과 census·G′를 같은 판정 커밋으로 판정해야 합니다.
  - `Test-Path`(단일 경로) 결과 `j9_runs\56849248\judge_5955f25b`, `judge_2263b246`, `judge`는 모두 없습니다. 그러니 T8″로 판정한 출력은 아직 없고, 단일 T8 원칙을 지킬 수 있습니다.
- 권장 조치(메인): 아래 "판정 명령 수정안"(`run_stage4_gates_t8ppp.ps1`)을 씁니다.
  - 판정 루트 ed8-judge3, HEAD 고정 검사, 출력 `judge_2263b246`(있으면 거부), `--ignored` 포함 깨끗함 검사를 넣었습니다.
  - `ps1_lint` 종료 0, `placeholder_scan --pattern-set both` 종료 0입니다.

### [기록][E] K-1. census 단계의 J-P3는 기대 판정 행 수를 단언하지 않는다. 이름이 일부 빠지면 조용히 기록 칸으로 간다
- 근거
  - `jp3_ed8_judge.py:331` `ed7.jp3_basis(jp3, None)`(기대 수 None)
  - `j_p3_inputs.py:253-260`: 판정 튜플에 없는 설정의 줄은 `rev7_record_only`·`rev7_unjudged_setting_runs`로 가고, 결함으로 잡히지 않습니다.
  - 기대 수를 대조하는 곳은 cases뿐입니다(`jp3_ed8_judge.py:1333-1335`, 10). 규칙 9:332는 census J-P3 판정 집합을 C-J 388, C-S 184, C-D 24, C-G 171로 정합니다.
  - D-1과 같은 결함이 다시 생기면(이름 일부만 누락) 0이 아니므로 not_judgeable도 되지 않습니다.
- 지금 판정에 닿지 않는 이유(경로 추적)
  - census 단계가 `jp3_of`에 넘기는 줄의 설정은 모두 판정 10설정 안에 있습니다: C-J VBN·LSN1~4(`:537,568`), C-S `judged_vs_V0` 역할 줄만(`:649-651`), C-D VBN·VBNslow(`:706,724`), C-G·G′ VBN.
  - T-a가 10설정 = 규칙 리터럴 = run_v5 집합임을 단언합니다(`test_ed8_jp3_settings.py:136-150`).
- 권장 조치: 도구는 고치지 않습니다(새 판정 커밋이 필요해짐). 판정서에서 단계별 `J-P3_judged_rows`가 388/184/24/171이고 `J-P3.rev7_unjudged_setting_runs`가 없거나 0인지 확인하는 항목을 둡니다(판정 후 감사 C축에서 재집계 대상).

### [기록][I] K-2. ed8-judge3 잠금 사유에 커밋 접두가 없다
- 근거: `worktree_locks.py` 종료 0이지만 info `lock_reason_no_commit`이 나왔습니다(`"436.9 ed8 T8''' judge checkout"`). 또 ed8-judge2의 잠금 사유는 아직 "T8'' 5955f25b (judge checkout)"입니다.
- 권장(메인): `git worktree unlock`/`lock --reason "ed8 T8''' 2263b246 (judge checkout)"`으로 바꿉니다. ed8-judge2는 ed8-judge처럼 "superseded by T8''' 2263b246"로 둡니다.

### [기록][R] K-3. 판정 도구 env가 지시문과 도구 문면에서 다르다
- 근거: 지시문은 "판정 도구 Chrono-dev"라고 합니다. 반면 도구 docstring(`jp3_ed8_judge.py:71`, `jp3_tjr_judge_ed8.py:15`), prejudge 초안(`prejudge_report.md:141`), C8 실행(`impl_cases.done:39`)은 모두 dynamics-dev입니다.
- 영향: J-P3 행 수에는 영향이 없습니다(결정적 집계). 관문 판정이 지표를 다시 계산하므로 판정서에 env를 고정해 적어야 합니다. → 확인 필요 1

### [기록][R] K-4. 새 기록 키 `J-P3_judged_settings`
- 근거: `jp3_ed8_judge.py:334`. cases 보고서 최상위(`:1344` 펼침)와 census·heldout의 `J-P3` 묶음에 실립니다. 상태 계산은 읽지 않습니다(`rules.status_of(basis)`).
- 영향: 판정과는 무관합니다. 경로 1·2 보고서의 키 집합을 엄격하게 비교하는 도구가 있으면 키가 하나 더 보입니다.

### [기록][T] K-5. 공개 문구: T8‴ 수정은 4단계 출력의 키·꼴 점검 뒤, 판정 값을 보기 전에 했다
- 근거
  - 4단계 실행: `impl_cases.done:6-7` 15:59~16:02
  - prejudge 점검: 키·꼴·행 수만 봤고, `jp3_cause_probe`는 판정 행 0→10만 냈습니다(`prejudge_report.md:92-95`).
  - T8‴ 커밋: 2026-11-27 18:15:13
  - 판정 출력 폴더는 아직 없습니다(M-2).
- 권장: 판정서 공개 항목에 넣습니다(control 결정문 초안 `d1_decision_draft.txt` 6항과 같은 내용).

### [기록][E] K-6. gate_scan 경고 7건은 모두 T8‴ 이전 코드다
- `tag_single_compare` 7건(예: `jp3_ed8_judge.py:310` `setting == V0_SETTING`, 태그가 아니라 설정 비교)입니다.
- 새로 더한 줄 262-293·321-338에서 나온 발견은 없습니다.

## 지시 항목별 답

### 1. 판 8 이름이 빠진 설정 이름 튜플·집합 전수 검색
- 방법
  - 즉석 AST 스캔으로 판 8 판정 진입 7모듈의 정적 import 폐포 192모듈을 훑었습니다. 진입 모듈은 `jp3_ed8_judge`, `jp3_ed8_gate_judge`, `jp3_tjr_judge_ed8`, `jp3_12b_judge_ed8`, `p816_compare`, `ed8_key_lists`, `ed8_selection_keys`입니다.
  - 범위는 ed8-judge3 `04_scripts`(rglob *.py)와 `03_src`(*.py)이고, 코드만 파싱하고 import는 하지 않았습니다.
  - 설정 이름처럼 보이는 문자열(`VB*`·`LS*`·`V0`)을 담은 tuple·list·set·dict, 비교식, startswith를 뽑았습니다.
  - 그와 별도로 Grep으로 `from j_p3_inputs import`·`REV5_JUDGED_SETTINGS`·`P3_OFF_SETTINGS`를 찾았습니다(04_scripts·03_src, glob *.py).
- import 바인딩
  - 튜플을 이름으로 가져가는 곳은 `jp3_tjr_judge.py:197` `from j_p3_inputs import REV5_JUDGED_SETTINGS` 하나입니다. T8‴가 `_tjr_judged_settings`(`jp3_tjr_judge_ed8.py:40-51`)로 다시 묶고 되돌립니다.
  - 나머지 import(`is_p3_expected`, `j_p3_over_rows`, `has_judged_breach`, `HOLD_REVISIONS` 등)는 함수나 판정 무관 상수입니다. 호출할 때 모듈 전역을 읽으므로 덮어쓰기가 닿습니다.
  - 03_src에는 해당 없음(0건)입니다.
- 판 7 이름은 있고 판 8 이름은 없는 집합(스캔 결과 19건)의 판정 경로 도달 여부

| 위치 | 이름 | 판 8 경로 도달 | 판단 |
|---|---|---|---|
| `j_p3_inputs.py:39` `P3_OFF_SETTINGS`, `:62/:67` `ED7_/REV5_JUDGED_SETTINGS` | VBM… | 도달(J-P3) | T8‴ 덮어쓰기 대상(D-1·D-1b). `jp3_of` 안에서만 판 8 이름이 붙음 |
| `jp3_ed7_judge.py:136` `SETTING_MAP_ED7` | VBM·LSM1~4 | 판 7 `judge_j9main`(:767-794)만 | 판 8은 자기 `CJ_LABEL`(`jp3_ed8_judge.py:112`)을 씀. 해당 없음 |
| `jp3_ed7_judge.py:142,145,147` `D_COUNTED_SETTING`·`PROBE_*_PLANTS` | VBM… | 판 7 probe·D(:1409-1436)만 | 해당 없음 |
| `jp3_ed7_judge.py:1279,1315-1316` `judge_t8` | VBM·VBM0 | 판 7 t8만 | 판 8 t8은 gate `T8_SETTINGS=("VBN","VBN0")`(`jp3_ed8_gate_judge.py:92,445`) |
| `jp3_ed7_judge.py:1516` `L1_RUNS` | VBM… | `judge_l1ref` | 판 8이 `ed7.L1_RUNS`를 판 8 이름으로 바꾸고 되돌림(`jp3_ed8_judge.py:1348-1368`) |
| `jp3_ed7_rules.py:59-60` `SENSITIVITY_JUDGED/RECORD`(`split_sensitivity` :162-173, 판 7 `judge_sens` :920-1016) | VBM<key> | 판 7만 | 판 8 C-S는 `run_v5.ED8_SENSITIVITY_SETTINGS`·`_RECORD_SETTINGS`(`jp3_ed8_judge.py:616`, 강성 예외 10설정 = 규칙 5.2:233 "이어받음") |
| `jp3_ed7_rules.py:72` `U832_CLUSTERS` | (군집) | 판 8 미사용 | 규칙 6.4와 맞음 |
| `ed8_key_lists.py:72,204,231`, `ed8_selection_keys.py:58`, `p816_compare.py:46` | VBM·LSM4·VBKM0 | 키 생성·기준 대응 | 판 7 원천 키 → 판 8 대응(규칙 5.1 "VBM → VBN")이므로 의도된 값 |
| `run_v5.py:264,278,311,443` | VBM… | 실행 경로(C8 바이트) | 판정 아님 |

- 판 6 이하 이름만 있는 집합
  - `jp3_tjr_judge.py:201-259` `T8_*`·`JP3_LINE_SETTINGS`·`T_JR_14/15`는 4a 하위 명령 전용입니다.
  - `jp3_tjr_judge.py:228-230,661,1079-1080` `BUNDLE_BASE*`·`RUN_BASE_BUNDLES`·`ED6_LINE_SETTINGS`·`PLANT_TRUTH_SETTINGS`·`DG3_JUDGE_SETTINGS`는 `edition_7()`이 실행 시점의 `ED7_BUNDLE/BASE`로 늘립니다(`jp3_tjr_judge_ed7.py:146-158`). 판 8에서는 `edition_8()`이 그 값을 VBN/VBN0로 바꾼 상태입니다(`jp3_tjr_judge_ed8.py:60-61`).
  - l1-hash-record 이름은 표시 문구뿐입니다(`jp3_tjr_judge.py:1213`).
  - `jp3_ed6_judge`·`jp3_baseline_compare`·`jp3_j9main_judge.SETTING_MAP`는 판 8 경로에서 호출되지 않습니다(판 8은 `_full_items`·`apply_reading_1`·`s8_items` 등에 설정을 인자로 넘김).
- 관문별 J-P3 호출: 덮어쓰기 안쪽인지

| 관문 | J-P3 호출 | 덮어쓰기 안 |
|---|---|---|
| cases P8-2 | `jp3_ed8_judge.py:1329` `jp3_of` | 예(:328-329) |
| census C-J / C-S / C-D / C-G | `:568 / :651 / :724 / :738` `jp3_of` | 예 |
| G′ | `:1289` `jp3_of` | 예 |
| 12a t12 | `jp3_tjr_judge._check_lines`(:676-684), `_dg3_j_p3`(:836-874, 이름 무관) | 예(`edition_8` → `ed8_jp3_settings` → `_tjr_judged_settings`) |
| 12b | `jp3_12b_judge.py:907` `has_judged_breach`만 | 해당 없음(이름 무관) |
| t8·p80·p816·p85·p88·p815 | J-P3 없음(gate에 `jp3_of`·`j_p3_over_rows` 호출 0) | 해당 없음 |
| l1ref | J-P3 없음(정체성) | 해당 없음 |
| ③ rev 7 조건 | `jp3_rev7_condition`이 `p1_patch`로 판별(:77,176) | 이름 무관 |

- `ed8.jp3_of`는 판 7 단계 함수(`judge_j9main`·`judge_sens`·`judge_t8`·`judge_probe_repro`)를 부르지 않습니다(`jp3_ed8_judge.py`의 `ed7.*(` 호출 21곳을 확인). 그래서 덮어쓰기 밖에서 J-P3로 가는 다른 길이 없습니다.

### 2. 덮어쓰기가 판 8 문맥 안에서만 켜지는지
- 정적 확인
  - `ed8_jp3_settings`를 쓰는 파일은 `jp3_ed8_judge.py`·`jp3_tjr_judge_ed8.py`뿐입니다(Grep 04_scripts *.py·*.ps1).
  - `jp3_ed8_judge`를 import하는 모듈은 `jp3_tjr_judge_ed8`·`jp3_12b_judge_ed8`(덮어쓰기 호출 없음)뿐입니다. `ed8_selection_keys`는 docstring 언급뿐입니다.
  - 판 6·7 진입 모듈과 `jp3_tjr_judge`·`j_p3_inputs`는 판 8 모듈을 import하지 않습니다(T-e 7개 + 제 Grep).
- 동적 동작(코드 읽기)
  - 덮어쓰기는 함수 호출 범위의 `try/finally`로 원래 객체를 되돌립니다(`jp3_ed8_judge.py:280-292`, `jp3_tjr_judge_ed8.py:40-51,62-66`). import 때는 아무것도 바꾸지 않습니다.
  - 중첩해도 `_with_names`가 이름을 중복 없이 더하고(:274-276), 바깥 값으로 되돌립니다.
  - 덮어쓰기 안에서도 판 6·7 이름은 그대로 있습니다(뒤에 붙임). 규칙 3.6:159("이전 판 입력에는 VBN 계열 없음")에 따라 판 6·7 입력의 결과는 같습니다.
- 시험: T-b 5개(예외 뒤 복원, `is` 원 객체, tjr 바인딩)와 T-e 9개가 T8‴에서 통과했습니다. T8″ 코드에 새 시험을 얹으면 의도대로 실패했습니다.
  - `junit_Tf_cwd_outside.xml`: `junit_skips --critical 'test_ed8_jp3_settings|test_ed8_run_path'` 종료 0, 23/23, skip·xfail 0
  - `junit_newtests_on_T8pp_5955f25b.xml`: 11 실패
- 결론: 새는 곳을 찾지 못했습니다.

### 3. P8-11(실행 경로 바이트 = C8)
- 독립 대조(git 객체만, 판정 도구 import 없음, python-dev)
  - 목록 `05_tests/data/ed8_run_path_modules_56849248.json`(T8‴ blob)의 156개 파일: C8 blob = T8‴ blob이 156/156이고, 목록 blob = C8 blob입니다.
  - `git diff --name-only C8 T8‴` 23개 파일 가운데 목록에 든 것은 0개이고, 모두 `04_scripts/`·`05_tests/` 아래입니다.
  - `03_src` 트리는 C8 = T8‴ = 목록 `ed797e8e…`입니다.
  - `j_p3_inputs.py`가 목록에 있습니다(json:513).
- `test_ed8_run_path.py`는 제가 돌리지 않았습니다. 같은 checkout에서 P8-4 전체 시험(이 파일 포함)이 돌고 있기 때문입니다(M-1). P8-4 junit에서 `junit_skips.py <junit> --critical 'test_ed8_run_path|test_ed8_jp3_settings'` 종료 0(skip 0·실패 0)을 확인해 주십시오(메인 세션 권고 2).
- 도구 결과

| 도구 | 결과 | 판단 |
|---|---|---|
| `seal_check` 규칙 + `--code` 판 8 판정 3파일, `--rev` master 07c818ce `--check-tracked` | 종료 0. 일치, `-text`, LF, BOM 없음. 코드 고정 `jp3_ed8_gate_judge.py:87` 35f9eba8 = 규칙 | 통과 |
| `seal_check` 같은 규칙 + `--sums t8ppp_evidence\SHA256SUMS --rev 2263b246 --check-tracked` | 종료 1. `cited_untracked` 24(규칙·`.sha256`·SUMS·증거 21) | 규칙 봉인 2715230e는 C8 조상이 아닙니다(`merge-base --is-ancestor` 1). 규칙은 master에만 있고 증거 폴더는 미추적입니다. 판정에는 영향이 없고 증거 커밋은 메인 몫입니다(권고 3) |
| `baseline_check sums` t8ppp_evidence | mismatch 0, missing 0, unlisted 0, CRLF 0. `cited_untracked` 22 | 같음 |
| `baseline_check sums` control_d1_settings | mismatch 0, missing 0, unlisted 0. `cited_untracked` 6 | 같음 |
| `baseline_check identity` | 직접 실행하지 않음. 대상 단계 폴더가 블라인드입니다 | 러너가 만든 `_identity_checks\*.md` 8개 모두 "발견 사항 없음"(1개 전문, 8개 건수). cases는 start·end head C8, is_clean True |
| `ref_check control_d1_settings.md --rev 2263b246 --rev 07c818ce --exclude …` | 종료 1. `ref_missing` 3, `ref_untracked` 13 | missing 3은 모두 해가 없습니다: (1) 하지 말 것 목록의 블라인드 경로 문구 `j9_runs\56849248\impl_*_a1\`(:103), (2) 지운 scratchpad 하위 폴더 이름(:174), (3) control 메모리 파일 이름(:205). untracked는 미커밋 근거 문서입니다 |
| `worktree_locks` | 종료 0, info 1(K-2) | 기록 |

### 4. 값 없는 cases 스모크(J-P3 판정 행 수만)
- 방식
  - T8‴의 실제 래퍼 `jp3_ed8_judge.jp3_of`를 부릅니다(스텁 없음, 판정과 같은 `gate.read_rows`·`ed7.t4h_folders_of`).
  - 출력은 행 수, 설정별 줄 수, 판정 행 수, `runs_expected`·`rule_missing_runs`·`rev7_unjudged_setting_runs` 같은 구조 카운트, 그리고 J-P3 setting_defect·not_judgeable 문구(구조 사유)뿐입니다.
  - J-P3 상태·H-7·침범 수·실패 문구·③ 조건 결과·줄 값은 내지 않습니다. 모듈이 찍는 stdout·stderr는 가두고 줄 수만 냅니다.
- 건조 실행(제가 실행): dynamics-dev, cwd ed8-judge3, `--dry`(행 없음)
  - 종료 0, `tuples_restored` true, `modules_outside_judge_root` [], 갇힌 출력 0줄
  - 판정 행 0, not_judgeable 문구 ["J-P3 0 judged rows", "J-P3 no_p3_runs"](빈 입력이라 예상대로)
  - 실행 뒤 ed8-judge3 추적 변경 없음
- 기대값(실제 실행): `judged_rows` 10, `counts.runs_expected` 10, 나머지 카운트 0, 문구 목록 둘 다 빈 목록, `error_rows` 0 → 종료 0
- 공개(스모크 결과를 판정서에 적을 때): 이 스모크는 P8-2의 setting_defect·not_judgeable 쪽 일부(판정 행 수 ≠ 10 여부)를 드러냅니다. pass/fail(침범)은 드러내지 않습니다. prejudge 공개 1과 같은 성격입니다.
- 정적 점검: `ruff check --isolated --select E,F,B,UP` 0건, `ps1_lint` 종료 0, `placeholder_scan --pattern-set both` 종료 0(py·ps1 둘 다)
- 두 파일은 저장소 안 새 폴더 `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\stage4_prejudge_t8ppp\`에 메인이 저장해 주십시오. 블라인드를 품지 않은 폴더입니다. 블라인드 경로는 ps1 안에 단일 파일 경로로만 들어 있습니다.

`cases_jp3_rows_smoke.py`(제가 쓴 원문 그대로):
```python
"""Value-free smoke at T8''' (D-1): the J-P3 judged row count of the P8-2 cases lines.

Prints one JSON line with counts and structural reasons only: never a J-P3 status, a breach
count, a failure text, the ③ rev 7 condition or any line value. Everything the judge modules
print while reading is captured and only its line count is reported.

Exit 0: judged rows 10, runs expected 10, no rule-missing / unjudged-setting / key rows, the
C8 tuples restored. Exit 1: a count differs. Exit 2: argument or input error. Exit 3: error.

Usage (from the judge worktree root, dynamics-dev or the env the judge runs in):
  python -I -B cases_jp3_rows_smoke.py --judge-root JUDGE_ROOT --rows CASES_JSONL
  python -I -B cases_jp3_rows_smoke.py --judge-root JUDGE_ROOT --dry   (no rows: import check)
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from collections import Counter
from pathlib import Path

EXPECTED_JUDGED = 10
COUNT_KEYS = ("runs_expected", "rule_missing_runs", "test_only_setting_runs",
              "l1_reference_runs", "revision_key_missing_runs", "revision_key_mismatch_runs",
              "rev7_unjudged_setting_runs", "rev6_unjudged_setting_runs",
              "rev5_unjudged_setting_runs")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--judge-root", type=Path, required=True)
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    root = args.judge_root.resolve()
    if args.dry == (args.rows is not None):
        print(json.dumps({"status": "input_error", "reason": "give --rows or --dry"}))
        return 2
    if args.rows is not None and not args.rows.is_file():
        print(json.dumps({"status": "input_error", "reason": "--rows is not a file"}))
        return 2
    for path in (root / "04_scripts" / "04_hydraulic" / "coupled", root / "03_src"):
        sys.path.insert(0, str(path))
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        import j_p3_inputs
        import jp3_ed7_judge as ed7
        import jp3_ed8_gate_judge as gate
        import jp3_ed8_judge as ed8

        saved = (j_p3_inputs.REV5_JUDGED_SETTINGS, j_p3_inputs.P3_OFF_SETTINGS)
        rows = [] if args.dry else gate.read_rows(args.rows)
        good = [row for row in rows if "error" not in row]
        folders = () if args.dry else tuple(ed7.t4h_folders_of(args.rows, good))
        report = ed8.jp3_of(good, folders)  # the T8''' wrapper itself (J-P3 + ③ condition)
        _, jp3_defects, jp3_unjudged = ed7.jp3_basis(report["J-P3"], None)  # failures unused
        restored = (j_p3_inputs.REV5_JUDGED_SETTINGS is saved[0]
                    and j_p3_inputs.P3_OFF_SETTINGS is saved[1])
        modules = {name: getattr(module, "__file__", None) for name, module in (
            ("j_p3_inputs", j_p3_inputs), ("jp3_ed7_judge", ed7), ("jp3_ed8_gate_judge", gate),
            ("jp3_ed8_judge", ed8))}
    jp3 = report["J-P3"]
    counts = {key: jp3.get(key) for key in COUNT_KEYS if key in jp3}
    outside = sorted(name for name, file in modules.items()
                     if file is None or not Path(file).resolve().is_relative_to(root))
    out = {"rows": len(rows), "error_rows": len(rows) - len(good),
           "lines_by_setting": dict(sorted(Counter(
               str((row.get("job") or {}).get("setting")) for row in good).items())),
           "judged_rows": report["J-P3_judged_rows"],
           "judged_settings_record": report.get("J-P3_judged_settings"),
           "hold_revision_blocks": sorted(key for key in jp3 if key in ("rev5", "rev6", "rev7")),
           "counts": counts,
           "jp3_setting_defect_texts": jp3_defects,
           "jp3_not_judgeable_texts": jp3_unjudged,
           "tuples_restored": restored, "modules_outside_judge_root": outside,
           "captured_output_lines": len(captured.getvalue().splitlines())}
    if args.dry:
        out["status"] = "dry"
        print(json.dumps(out, ensure_ascii=False))
        return 0 if restored and not outside else 1
    ok = (out["judged_rows"] == EXPECTED_JUDGED and counts.get("runs_expected") == EXPECTED_JUDGED
          and not any(counts.get(key) for key in COUNT_KEYS if key != "runs_expected")
          and not jp3_defects and not jp3_unjudged and restored and not outside
          and out["error_rows"] == 0)
    out["status"] = "ok" if ok else "count_mismatch"
    print(json.dumps(out, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - the type only, never a message with values
        print(json.dumps({"status": "error", "type": type(exc).__name__}))
        sys.exit(3)
```

`run_cases_jp3_rows_smoke.ps1`(원문 그대로):
```powershell
# T8''' D-1 value-free smoke: J-P3 judged row count of the P8-2 cases lines (expected 10).
# Prints and keeps only counts and structural reasons (cases_jp3_rows_smoke.py); never a status,
# a breach count or a line value. The blind rows file is named here only, never listed or read
# by anything else. Run by the main session.
$ErrorActionPreference = 'Stop'
$Judge = 'C:\workspace\outrigger_control\.claude\worktrees\ed8-judge3'
$JudgeHead = '2263b2461238da7f93eda147838c01c847315561'
$Py = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$CaseRows = 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\56849248\impl_cases_a1\ed8_cases.jsonl'
$SmokeDir = 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\stage4_prejudge_t8ppp'
$SmokePy = Join-Path $SmokeDir 'cases_jp3_rows_smoke.py'
$SmokeOut = Join-Path $SmokeDir 'cases_jp3_rows_smoke.json'

if (-not (Test-Path -LiteralPath $SmokePy)) { throw "smoke script missing: $SmokePy" }
if (Test-Path -LiteralPath $SmokeOut) { throw "output exists (new path only): $SmokeOut" }
$head = (& git -C $Judge rev-parse HEAD).Trim()
if ($head -ne $JudgeHead) { throw "judge HEAD $head is not $JudgeHead" }
$dirty = & git -C $Judge status --porcelain
if ($dirty) { throw 'judge checkout has tracked or untracked changes' }

$env:MKL_THREADING_LAYER = 'TBB'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:NUMBA_CACHE_DIR = 'C:\Users\jinbeom\.claude\runners\outrigger-ed8\numba_cache\smoke_2263b246'

Push-Location -LiteralPath $Judge
try {
    $dryLines = @(& $Py -I -B $SmokePy --judge-root $Judge --dry)
    $dryCode = $LASTEXITCODE
    $lines = @(& $Py -I -B $SmokePy --judge-root $Judge --rows $CaseRows)
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}
$last = if ($lines.Count) { $lines[-1] } else { '' }
[System.IO.File]::WriteAllText($SmokeOut, "$last`n", [System.Text.UTF8Encoding]::new($false))
Write-Output "dry exit $dryCode : $(if ($dryLines.Count) { $dryLines[-1] })"
Write-Output "smoke exit $code"
Write-Output $last
$after = & git -C $Judge status --porcelain
if ($after) { Write-Output 'WARNING: judge checkout changed by the smoke' }
```
- env를 Chrono-dev로 정하면(확인 필요 1) `$Py`만 바꿉니다.
- 스모크는 P8-4와 같은 checkout을 읽기만 하고 가볍습니다(10줄). 그래도 M-1 정리 뒤에 돌리기를 권합니다.

### 5. 경로 2의 판정 집합(규칙 정의 문장 대조만)
경로 2 도구는 열지 않았습니다. 경로 2에 넘기는 정의 문장 9:331-334에서 판정 설정을 이끌어 내면 아래와 같습니다.

| 9:332 범위 | 설정 근거(규칙 문장) | 설정 |
|---|---|---|
| C-J 388 | 5.1:218 "VBN 100 + LSN1~4 각 72" | VBN, LSN1~4 |
| C-S 판정 4설정 184 | 3.6:156 "slow·fast·c005·c04 판정", 5.2:233 | VBNslow, VBNfast, VBNc005, VBNc04 |
| C-D 24 | 5.1:220 "D 12키 × {VBN, VBNslow}" | VBN, VBNslow |
| C-G 171, G′ | 5.1:221, 7.1:282 "설정 VBN" | VBN |
| P8-2 | 12:363 "E·F × {VBN, LSN1~4}" | VBN, LSN1~4 |
| 12a | 8:324 "VBN 대 VBN0"(③ 끔 VBN0은 기준) | VBN |
| 12b·T-JR-12b | 8:325 "VBKN·VBKN0" | VBKN |

- 합집합은 10설정이고, `ED8_JP3_JUDGED_SETTINGS`(`jp3_ed8_judge.py:262-263`)와 같습니다.
- 주의 1(문면 해석 위험): 5.2:234 "VBNslow 12줄은 기록"은 V0 비교(C-G 칸 집계)에 관한 문장입니다. 9:332는 C-D 24줄 전체를 J-P3 판정 집합에 넣습니다. 경로 2 작성자가 5.2:234를 J-P3에도 적용하면 C-D J-P3가 12 대 24로 갈립니다. 경로 1은 24줄을 판정합니다(T-c 24). → 확인 필요 2, 위임 필요 1
- 주의 2: 기록 6설정(VBNb069…d15)의 J-P3는 두 경로 모두 판정하지 않습니다(5.2:233 "기록 6설정은 기록", 10:344).

## 규칙↔도구 대조표(이번 변경 범위)

| 규칙 원문 | 도구 | 일치 |
|---|---|---|
| 3.6:154 `VBN`·`LSN1~4` 판 8 판정 | `ED8_JP3_JUDGED_SETTINGS` 앞 5개(`jp3_ed8_judge.py:262`) | 예 |
| 3.6:156 `VBN<key>` slow·fast·c005·c04 판정, b069·b16·h05·h15·d05·d15 기록 | 판정 4개는 튜플에 있고 기록 6개는 없음. T-a가 run_v5 집합과 대조(`test_ed8_jp3_settings.py:142-145`) | 예 |
| 3.6:157 `VBKN` 12b | 튜플에 있음(12b는 자기 경로로 판정) | 예 |
| 3.6:155·157 VBN0·VBKN0 ③ 끔 | `ED8_P3_OFF_SETTINGS`(:269) → `is_p3_expected` 거짓 | 예 |
| 5.1:229·10:338·10:346 판정 행 0 = 판정 불가 | `ed7.jp3_basis` "J-P3 0 judged rows" → not_judgeable(`jp3_ed7_judge.py:475-477`) | 예 |
| 12 P8-2 "10줄 J-P3 판정 키 0" | cases 판정 행 ∉ {0, 10}이면 setting_defect, 0이면 판정 불가(`jp3_ed8_judge.py:1333-1335`) | 예 |
| 9:332 census 줄 수 388/184/24/171 | 단언 없음(`expected_rows=None`, :331) | 해당 조항 없음, K-1 기록 |
| 11.2 T8 diff는 04_scripts 판정 도구와 05_tests뿐, 실행 경로 바이트 = C8 | 독립 git 대조 통과(3항) | 예 |

## 확인 필요
1. 4단계·census 판정 도구를 어느 env로 돌립니까? 지시문은 Chrono-dev, 도구 docstring·prejudge 초안·C8 실행은 dynamics-dev입니다(K-3). 판정서에 고정할 값을 정해 주십시오.
2. C-D J-P3 판정 집합이 24줄(VBN 12 + VBNslow 12)이라는 것을 경로 2 넘김 범위(9:332 "C-D 24")만으로 충분하다고 볼까요, 아니면 5.2:234 "VBNslow 12줄은 기록"의 범위(V0 비교에 한함)를 해석 결정문에 한 줄 더할까요? control 결정문 초안 `d1_decision_draft.txt`가 판정 10설정을 적고 있으니 거기 넣는 것이 자연스럽습니다(봉인 정의 변경은 아님).
3. control 확인 필요 2(결정문을 정오로 봉인할지)는 아직 열려 있는 것으로 보입니다. 판정 전에 사용자 결정이 필요합니다.

## 위임 필요
1. 경로 2 담당(경로 2 J-P3 도구 작성 에이전트)
   - 경로 2 도구가 판 8 J-P3 판정 집합을 9:332의 줄 수·키 그대로(C-J 388, C-S 184, C-D 24, C-G 171, P8-2 10, G′ 339, 12a VBN, 12b VBKN) 고르는지 확인합니다. 설정 이름 목록을 하드코딩했다면 위 5항의 10설정과 같은지도 봅니다.
   - 넘길 자료는 규칙 9절·판 7 11절 정의 문장과 위 5항의 규칙 문장 표뿐입니다. 경로 1 코드·`ED8_JP3_JUDGED_SETTINGS`·이 감사의 경로 1 줄 번호는 넘기지 않습니다.
2. `tools/verif` 후보(python-expert)
   - 검사 이름: "판 이름 튜플 누락 스캔"
   - 입력: 진입 모듈 목록, 저장소 루트, 옛 판 접두(VBM·LSM·VBKM)·새 판 접두(VBN·LSN·VBKN)
   - 출력: import 폐포 안에서 옛 판 이름은 있고 새 판 이름은 없는 문자열 집합·비교식의 `path:line`과 대입 이름, 그리고 `from X import <대문자 상수>` 바인딩 목록
   - 종료 코드: 0 없음 / 1 발견 / 2 입력 오류
   - 이번에 즉석 AST 스크립트로 했고, D-1과 같은 결함이 판마다 되풀이되는 계열입니다.

## 메인 세션 권고
1. P8-4(PID 92564)가 끝난 뒤 ed8-judge3의 `__pycache__`를 경로 지정으로 지웁니다. `git -C ed8-judge3 status --porcelain --ignored` 빈 출력을 확인한 뒤 위 스모크와 관문 판정을 돌립니다(M-1).
2. P8-4 junit에 `junit_skips.py <p84 junit> --critical 'test_ed8_run_path|test_ed8_jp3_settings'`를 돌려 종료 0(실패·skip 0)을 확인합니다. P8-4 수치 판정은 별도입니다.
3. 판정서가 인용하기 전에 근거 폴더 `ed8_design\t8ppp_evidence\`, `control_d1_settings\`, `stage4_prejudge\`, `audit_t8ppp\`(그리고 새 `stage4_prejudge_t8ppp\`)를 커밋합니다. 지금은 모두 `cited_untracked`이고 SUMS 대조는 맞습니다. 이 감사 hand-back은 그 폴더들이 아니라 별도 감사 폴더에 둡니다(SUMS가 낡지 않게).
4. 관문 판정 명령 수정안 `run_stage4_gates_t8ppp.ps1`(`ps1_lint` 0, `placeholder_scan` 0). 원문 그대로:
```powershell
# Stage 4 gate judgement at T8''' 2263b246 (prejudge_report.md 4 draft with the judge checkout,
# the output folder and the clean check changed). Run by the main session after P8-4 ends and the
# P8-4 __pycache__ folders in ed8-judge3 are removed. Stop and ask on any exit other than 0.
$ErrorActionPreference = 'Stop'
$JudgeRoot = 'C:\workspace\outrigger_control\.claude\worktrees\ed8-judge3'
$JudgeHead = '2263b2461238da7f93eda147838c01c847315561'
$Py = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$RunRoot = 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\56849248'
$OutRoot = Join-Path $RunRoot 'judge_2263b246'
if (Test-Path -LiteralPath $OutRoot) { throw "output folder exists: $OutRoot" }
$head = (& git -C $JudgeRoot rev-parse HEAD).Trim()
if ($head -ne $JudgeHead) { throw "judge HEAD $head" }
$dirty = & git -C $JudgeRoot status --porcelain --ignored
if ($dirty) { throw 'judge checkout not clean (tracked, untracked or ignored files)' }
$env:MKL_THREADING_LAYER = 'TBB'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:NUMBA_CACHE_DIR = 'C:\Users\jinbeom\.claude\runners\outrigger-ed8\numba_cache\judge_2263b246'
$Gate = '04_scripts/04_hydraulic/coupled/jp3_ed8_gate_judge.py'
$Ed8 = '04_scripts/04_hydraulic/coupled/jp3_ed8_judge.py'
$Codes = [ordered]@{}
Push-Location -LiteralPath $JudgeRoot
try {
    & $Py -I -B $Gate p80 --rows "$RunRoot\impl_p80_a1\ed7_probe_a2.jsonl" --step-done "$RunRoot\impl_p80.done" --reference 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\b46bdf8f\repro_a2\ed7_probe_a2.jsonl' --out "$OutRoot\p80.json"
    $Codes['p80'] = $LASTEXITCODE
    & $Py -I -B $Gate p816 --rows "$RunRoot\impl_p816_a1\p816.jsonl" --step-done "$RunRoot\impl_p816.done" --reference 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\control_level_deadlock\probe_8a2a52ce\raw\runs.jsonl' --out "$OutRoot\p816.json"
    $Codes['p816'] = $LASTEXITCODE
    & $Py -I -B $Gate p85 --rows "$RunRoot\impl_p85_a1\p85.jsonl" --step-done "$RunRoot\impl_p85.done" --out "$OutRoot\p85.json"
    $Codes['p85'] = $LASTEXITCODE
    & $Py -I -B $Gate p88 --rows "$RunRoot\impl_p88_a1\p88.jsonl" --step-done "$RunRoot\impl_p88.done" --out "$OutRoot\p88.json"
    $Codes['p88'] = $LASTEXITCODE
    & $Py -I -B $Gate p815 --rows "$RunRoot\impl_p815_a1\p815.jsonl" --step-done "$RunRoot\impl_p815.done" --out "$OutRoot\p815.json"
    $Codes['p815'] = $LASTEXITCODE
    & $Py -I -B $Gate t8 --rows "$RunRoot\impl_t8_a1\ed8_t8.jsonl" --step-done "$RunRoot\impl_t8.done" --main-jsonl 'C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\main.jsonl' --out "$OutRoot\t8.json"
    $Codes['t8'] = $LASTEXITCODE
    & $Py -I -B $Ed8 cases --rows "$RunRoot\impl_cases_a1\ed8_cases.jsonl" --step-done "$RunRoot\impl_cases.done" --out "$OutRoot\cases.json"
    $Codes['cases'] = $LASTEXITCODE
    & $Py -I -B $Ed8 l1ref --rows "$RunRoot\l1ref_a1\L1_VBN0.json" --rows "$RunRoot\l1ref_a1\L1_VBN.json" --rows "$RunRoot\l1ref_a1\L1a_VBN0.json" --rows "$RunRoot\l1ref_a1\L1a_VBN.json" --step-done "$RunRoot\l1ref.done" --out "$OutRoot\l1ref.json"
    $Codes['l1ref'] = $LASTEXITCODE
}
finally {
    Pop-Location
}
foreach ($name in $Codes.Keys) { Write-Output "$name exit $($Codes[$name])" }
$after = & git -C $JudgeRoot status --porcelain
if ($after) { Write-Output 'WARNING: judge checkout changed' }
```
   - 인자는 prejudge 초안과 같고, 바뀐 것은 판정 루트·출력 폴더·깨끗함 검사·종료 코드 모음입니다.
   - 판정 명령이 읽는 키에는 T8‴가 새로 더한 것이 없습니다(이름 덮어쓰기만). 그래서 prejudge의 `key_presence` 결과(`kp_run_v5.json` 등 종료 0)가 그대로 유효하고, 제가 다시 돌리지 않았습니다.
5. 판정서 확인 항목: K-1(단계별 J-P3 판정 행 수·`rev7_unjudged_setting_runs`), K-5(수정 시점 공개)

## 검사하지 못한 것
- `test_ed8_run_path.py`·`test_ed8_jp3_settings.py`를 T8‴ 커밋 상태에서 다시 돌리지 않았습니다. 같은 checkout에서 P8-4가 돌고 있습니다. 증거 junit(커밋 전 작업 트리, 커밋 blob과 sha 일치)과 P8-4 junit으로 대신합니다.
- 실제 cases 줄에 대한 스모크: 블라인드라서 메인 몫입니다.
- 경로 2 도구: 열지 않았습니다(위임 1).
- 12b 본 경로(VBKN0 블록·selection): 이름 튜플과 무관해 범위 밖입니다.
- P8-4 수치 판정: 요청 범위 밖입니다.

## 실행한 검증
- 인터프리터
  - python-dev `-I -B`(`MKL_THREADING_LAYER=TBB`, 한글 출력은 `-X utf8`): verif 도구 전부와 즉석 스크립트 `name_scan.py`(AST만, import 없음), `p811_check.py`(git 객체만)
  - dynamics-dev `-I -B`(`PYTHONDONTWRITEBYTECODE=1`, `NUMBA_CACHE_DIR`=scratchpad 하위, cwd ed8-judge3): 스모크 `--dry` 1회
  - 판정 도구 함수를 재집계에 쓰지 않았습니다.
- 도구와 종료 코드
  - `seal_check` 2회(0, 1: cited_untracked)
  - `baseline_check sums` 2회(1: untracked만)
  - `gate_scan` 1회(1: 기존 경고 7)
  - `ref_check` 1회(1)
  - `junit_skips` 3회(0·1·1, 보고 수치와 같음)
  - `worktree_locks` 1회(0)
  - `ps1_lint` 2회(0)
  - `placeholder_scan` 3회(1 → docstring 자리표시를 고친 뒤 0, 0)
  - ruff `--no-cache --isolated` 1회(0)
  - `depcheck` 1회
- git 조회(Bash): `show --stat`, `diff`, `diff --name-status`, `log --oneline`, `worktree list --porcelain`, `ls-files --error-unmatch`·`--eol`, `check-attr`, `merge-base --is-ancestor`, `status --porcelain [--ignored]`
- PowerShell 조회
  - `Get-CimInstance Win32_Process`: 명령줄에 `ed8-judge3|pytest`가 든 프로세스 목록만, 종료하지 않음
  - `Test-Path` 단일 경로 4개
  - 메모리 파일 줄 수
- 만든 뒤 지운 것: scratchpad `verif-t8ppp\`(`guard.json`, `name_scan.py`, `p811_check.py`, 스모크 py·ps1, 판정 명령 ps1, numba 캐시). 폴더째 지웠고 남은 것은 없습니다. ed8-judge3에 쓴 파일은 없습니다(추적 변경 0).
- 공개(읽은 파일·검색 범위)
  - Read(메인 checkout)
    - `control_d1_settings.md` 전체, `impl_report_t8ppp.md` 전체
    - `jp3_remedy_spec_v8_rules.md` 1~459, `prejudge_report.md` 전체
    - `j9_runs\56849248\impl_cases.done`, `_identity_checks\impl_cases_a1.md`
    - 메모리 `audit_pitfalls.md` 233~235, `MEMORY.md`
  - Read(ed8-judge3)
    - `j_p3_inputs.py` 25~299, `jp3_j9main_judge.py` 270~334
    - `jp3_ed7_judge.py` 120~159·326~365·440~519·600~759·1500~1599
    - `jp3_ed8_judge.py` 1~260·295~339·500~759·1230~1379
    - `jp3_tjr_judge_ed7.py`·`jp3_tjr_judge_ed8.py`·`test_ed8_jp3_settings.py` 전체
    - `jp3_tjr_judge.py` 640~699·830~1009·1196~1235, `jp3_ed7_rules.py` 150~179, `run_v5.py` 286~325
  - Grep
    - ed8-judge3 `04_scripts`(glob `*.py`; `*.{py,ps1}` 파일 목록), `03_src`(glob `*.py`)
    - `04_scripts\04_hydraulic\coupled`(지정 모듈 brace glob 3회)
    - 단일 파일: `jp3_ed8_judge.py`, `jp3_rev7_condition.py`, `05_tests\data\ed8_run_path_modules_56849248.json`
    - 메인 `j9_runs\56849248\_identity_checks`(glob `*.md`, 건수)
    - 메모리 파일
  - Glob: `ed8_design\control_d1_settings`, `t8ppp_evidence`, `audit_t8ppp`, `j9_runs\56849248\_identity_checks`(모두 `*`)
  - 스크립트 범위: `name_scan.py`는 ed8-judge3 `04_scripts`·`03_src` 아래 `*.py`만 rglob으로 파싱했습니다(06_analysis·블라인드 사본 밖).
- 규칙 위반 공개 2건
  - (1) Bash에서 파이프 1회: `git show 2263b246:05_tests/data/ed8_run_path_modules_56849248.json | head -c 1200`(실행 경로 목록 머리 1.2 kB, 블라인드 무관). 금지된 Bash 파이프입니다.
  - (2) `ref_check --exclude`가 명세 103행의 블라인드 경로 문구(`j9_runs\56849248\impl_*_a1\`, 상대 조각)에 걸리지 않았습니다(`excluded_references` 0). 도구는 그 조각을 저장소 루트 기준(`<repo>\j9_runs\…`, 없는 경로)으로 풀었고 실제 블라인드 폴더에는 닿지 않았습니다. 비슷한 이름 후보로 나온 것은 `06_analysis/02_control/s9/rev81/impl_*.json` 5개(블라인드 아님)뿐입니다.
- blind_guard 훅에 막힌 시도: 없음
- 메모리 반영
  - `audit_pitfalls.md`에 1항을 더했습니다: 동결된 공용 모듈의 이름 튜플을 context manager로 바꾸는 패턴의 점검 4가지와 값 없는 스모크 방식.
  - `MEMORY.md` 색인 줄 끝에 키워드를 더했습니다.
- 원본 불변: 확인 — 원본 쓰기 0회, 기존 항목 변경·삭제 0건 (sha jp3_remedy_spec_v8_rules.md 35f9eba8…, jp3_remedy_spec_v8_rules.md.sha256 e19aaa48…, control_d1_settings.md c84ebb38…, d1_settings.json c4838c47…, impl_report_t8ppp.md aba8232f…, SHA256SUMS cc09451b…, prejudge_report.md 19c4fc76…, jp3_ed8_judge.py c01004b1…, jp3_tjr_judge_ed8.py 14c10caf…, test_ed8_jp3_settings.py bfd37f3f…, j_p3_inputs.py 1fde53b8…, 폴더 added_only: 새 항목만 생김, ~$ 임시 파일 없음) · 경고: 입력 폴더에 항목 추가 1건(__pycache__)
  - 같은 state로 `verify --strict-additions`를 돌리면 위반입니다(`__pycache__` 추가 1건). 원인은 스냅숏(18:16:36) 뒤 18:17:27에 시작한 P8-4 러너로 봅니다([추정], M-1).
- 사용한 스킬: 없음
