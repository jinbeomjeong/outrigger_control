## 감사 요약
- 본 결과
  - T8‴ 판정 출력 `j9_runs\56849248\judge_2263b246\*.json` 8개: 최상위 키 이름과 값의 형(型)을 봤습니다.
  - 그중 7개(p80 제외)는 대조 스크립트를 자기 자신과 돌려 시험하면서 `status` 문자열을 봤습니다. 앞 감사에서 이미 보고한 값입니다.
  - p85·p88·p815는 `pairing_problems`가 빈 목록인지(참/거짓), p816은 `counts` 안에 `duplicated`·`missing` 상태가 있는지(참/거짓)만 봤습니다.
  - 고정 기준 `b46bdf8f\repro_a2\ed7_probe_a2.jsonl`(블라인드 아님)에서는 setting별 줄 수, 해시가 같은지 다른지(bool), 건수만 냈습니다. 해시 값은 출력하지 않았습니다.
  - 블라인드 원자료(`impl_*_a1\`, `l1ref_a1\`, worktree 사본)는 열지 않았습니다.
- 대상: 436.9 판 8 4단계 관문 재판정용 판정 도구 T8⁗ `7ea78232`(ed8-judge4, locked). 부모는 T8‴ `2263b246`, 실행 커밋은 C8 `56849248`. 시점은 실행 전(판정 전)입니다.
- 기준 문서: `jp3_remedy_spec_v8_rules.md` 35f9eba8. `.md.sha256` 첫 토큰과 같습니다. 인덱스·작업 트리 모두 LF이고 `-text`입니다.
- 근거 문서 sha를 다시 재어 지시와 같음을 확인했습니다.
  - `control_p80p85\SHA256SUMS` d83d6cba, `control_p80p85.md` 61e7ae2e
  - `t8pppp_evidence\SHA256SUMS` 4b1a75a2, `impl_report_t8pppp.md` a7c0defd
  - `verif_p80p85_postjudge.md` a17bcebd, `p80p85_decision_draft.txt` fd85d7f8
- **판정: 차단 0 / 실행 전 수정 1 / 기록 7.** 재판정을 실행할 수 있습니다. 조건은 하나입니다. 지금 같은 checkout에서 돌고 있는 P8-4가 끝나고, 그 `__pycache__`를 지운 뒤에 실행해야 합니다(M-1).

## 발견 사항 (심각도순)

### [실행 전 수정][I·E] M-1. P8-4 정식 실행이 지금 ed8-judge4에 ignored `__pycache__`를 쓰고 있음 — 재판정은 그 실행이 끝나고 정리된 뒤에만
- **근거**
  - 러너 `C:\Users\jinbeom\.claude\runners\outrigger-ed8\p84_t8pppp_7ea78232\p84_step.ps1`
    - `:36`: pytest를 `-WorkingDirectory ed8-judge4`로 띄웁니다.
    - `p84_driver.log`: `[start] 20:13:39`, pytest PID 16836
    - `git_before.txt`: HEAD 7ea78232, 상태 줄 0
  - 그 뒤 `git -C ed8-judge4 status --porcelain --ignored`
    - 20:18에 11줄, 20:26에 12줄이었고 모두 `!! …/__pycache__/`입니다.
    - `coupled\__pycache__`에는 `v5_rerun`(20:14:18), `resume_k1_record`(20:16:43), `verdict_*`·`d1_*`(20:26) 같은 pyc가 쌓이고 있습니다.
    - 내 스모크(20:17~20:18)가 import한 모듈(gate·run_v5·ed7_probe·ed8_probe)의 pyc는 없습니다. 이 항목들은 내 것이 아니라 P8-4 것입니다.
  - 러너는 실행 뒤 `pycache_paths.txt`만 남기고 지우지는 않습니다(`:47-50`).
- **실패 시나리오**
  - P8-4 도중이나 정리 전에 재판정을 띄우면, 수정안은 시작 전 `--ignored` 검사에서 멈춥니다(안전).
  - 그런데 판정 도구 자신의 `code_identity`(`jp3_ed8_gate_judge.py:216`)는 `status --porcelain`만 봅니다(`--ignored` 없음). 그래서 옛 스크립트처럼 검사를 빼고 돌리면 출력 json에는 `is_clean true`가 찍힙니다. ignored 오염을 잡는 곳은 스크립트 관문 하나뿐입니다.
- **권장**(메인)
  - P8-4 `p84.done`을 확인합니다.
  - `t8pppp_evidence\clean_pycache.py`(ed8-judge4 고정, `!! …__pycache__`만 지움)를 실행합니다.
  - `status --porcelain --ignored`가 0줄인지 확인한 뒤 아래 5절 수정안을 실행합니다. 수정안은 `p84.done`이 없으면 시작을 거부하게 넣었습니다.

### [기록][R] R-1. 명세 5절 대조 — 일치 (볼 것 1)
- **AST 대조**(python-dev 즉석 `scope.py`): `git show 2263b246:` 대 `7ea78232:`의 gate 최상위 문장을 비교했습니다.
  - 바뀐 것: 모듈 docstring, `hash_table`, `judge_p80`
  - 새로 생긴 것: `p80_job_key`
  - 없어진 것: 0. 그 밖에 바뀐 것: 0. 순서: 같음
- **"하지 말 것" 정의·상수는 모두 바이트가 같습니다.**
  - 정의: `RUNTIME_JOB_KEYS`(:100), `row_identity`(:227-230), `probe_pairs`·`judge_arm_pairs`(:326-451), `judge_t8`(:476-519), `run_command`·`main`
  - 상수: `P80_LINES`, `P80_REFERENCE_SHA256`, `RUN_COMMIT`, `SPEC_V8_SHA256`, `ARM_PAIRS`, `MIN_SAME_PAIRS`, `UNREAD_PAIRS_LEFT_OUT`
  - 다른 모듈 blob도 2263b246과 같습니다: `jp3_ed8_judge.py`, `jp3_tjr_judge_ed8.py`, `jp3_ed8_rules.py`, `p816_compare.py`, `run_v5.py`, `ed7_probe.py`, `ed8_probe.py`, `j_p3_inputs.py`, `jp3_ed7_judge.py`, `jp3_t8_rules.py`, `test_ed8_gate_judge.py`(11/11 true)
- **`p80_job_key`**(:248-260)
  - `run_v5.job_key(dict(job))`를 돌려줍니다(`run_v5.py:759` `RUNTIME_JOB_KEYS = ("mask","t4h_dir")`, `:768-770`).
  - 생산자 쓰기 경로와도 맞습니다. `d0_plant_split.py:231-236` `_write_line`이 mask·t4h_dir를 떼고 씁니다. 생산자 이어 돌기 키 `ed7_probe.py:228`과 같은 키입니다.
- **`hash_table`**(:263-277): `key=row_identity` 기본값이 있습니다. 이 함수의 호출처는 `judge_p80` 두 곳뿐입니다(04_scripts `*.{py,ps1}` Grep).
- **`judge_p80`**(:280-322)
  - run·reference 문제 목록을 나눴습니다.
  - 기준 쪽 문제와 "≠114 jobs"는 `setting_defects`로 갑니다.
  - 이때 `reference_compared` false이고, `equal`·`missing`·`extra`·`differing`은 None입니다(0이 아님).
  - run 쪽 문제는 failures로 가고, 문구 순서는 그대로입니다.
  - 보고 키는 명세 목록 전부이고 `line_problems`는 없앴습니다. 소비처는 끝난 확인 스크립트 `control_p80p85\p80_plan_keys.py:38`(T8‴ worktree 고정) 하나라 영향이 없습니다.
- 규칙 대조: `spec:361` "114줄 = b46bdf8f 재현 줄별 해시", `:345`(목록 밖 문제 = 입력 결함), `:338`(상태 순서)와 같습니다(표 참고).

### [기록][C·R] R-2. p80 기준 자기 대조 스모크 — pass·114·114 (볼 것 2)
- 실행: dynamics-dev `-X utf8 -I -B`, cwd는 scratchpad, `PYTHONDONTWRITEBYTECODE=1`, `NUMBA_CACHE_DIR`는 scratchpad. 잠긴 T8⁗의 gate를 import하는 진단입니다(판정에 쓰지 않음).
- **고정 기준**
  - `git show e241638d:…/ed7_probe_a2.jsonl` blob의 sha = `P80_REFERENCE_SHA256`: true
  - 메인 checkout 사본 = blob: true
  - 114줄, error 줄 0, 기준 job에 mask·t4h_dir 없음
- **`judge_p80(기준, 기준)`**
  - pass, jobs 114, run_jobs 114, equal 114
  - missing·extra·differing 0, 줄 문제 0/0, `reference_compared` true
  - run 쪽을 섞은 경우(seed 20261127)와 두 쪽을 모두 뒤집거나 섞은 경우에도 똑같이 pass·114입니다. 줄 순서와 무관합니다.
- **생산자 계획** `ed7_probe.probe_jobs(arms=("a2",), part="all")`
  - 114 job이고, 독립 구현 키(mask·t4h_dir만 뺀 정렬 JSON)로 서로 다른 키가 114개입니다.
  - 계획 키 집합 = 기준 키 집합: true
  - `gate.p80_job_key` = 독립 키 = `run_v5.job_key`: 계획·기준 모두 true
  - 옛 `row_identity` 기준으로는 27키(회귀 확인)
  - setting 분포: M 27, Mslow 27, Mfast·Mc005·Mc04·L 각 15
- **변형 시험**(감사자 독립 구성)
  - 같은 행의 두 플랜트 해시를 맞바꿈 → failed, differing 2, equal 112. 플랜트끼리 짝지어지지 않음을 확인했습니다(T8‴ 키라면 놓치는 꼴).
  - Mslow D키 한 줄 변경 → failed, differing 1. 그 키에 `"setting": "P7-Mslow-a2"`가 있습니다.
  - run 한 줄을 오류 줄로 → failed(run line problems 1 + missing 1)
  - 기준 중복 줄 → setting_defect, 비교 안 함, 대조 값 None
  - **run 0줄 → failed(missing 114)**: 빈 run이 통과하지 않습니다.
- **CLI 끝까지**: 합성 `.done`, rows = 기준 바이트 사본, `--reference` = 메인 사본, cwd = scratchpad.
  - 종료 0, pass 114/114
  - `key` = "run_v5.job_key (spec v8 12 P8-0)", `judge_code.head` = 7ea78232, `is_clean` true, `reference.pinned` true, `line_problems` 키 없음
  - 같은 `--out`으로 다시 실행하면 종료 2(덮어쓰기 거부)
- 뒤에 ed8-judge4 HEAD는 7ea78232이고 추적 변경은 0입니다. ignored 줄 수는 내 실행 전후가 같았고, 늘어난 것은 P8-4 것입니다(M-1).

### [기록][E] R-3. `test_ed8_jp3_settings.py` 변경 — 수용 가능, 판정서에 공개 (볼 것 3)
- **diff**(`2263b246..7ea78232`): `T8PPP_COMMIT` 상수를 더했습니다. 그리고 `test_e_changes_since_t8pp_are_the_two_judges_and_tests`(:299-305)의 비교를 `diff --name-only T8PP`(작업 트리)에서 `diff --name-only T8PP T8PPP`(고정 범위)로 바꿨습니다. 허용 목록 `T8PPP_CHANGED_PATHS`(:63-64)와 단언문은 그대로입니다.
- **수용 근거**
  - (a) 옛 꼴은 자식 판정 커밋이 gate를 고치기만 하면 구조적으로 실패합니다. T8⁗가 아니라 시험 설계 문제입니다.
  - (b) 빠진 기능은 T8″ 대비 작업 트리 변경을 잡는 것입니다. 이것은 새 `test_changes_since_t8ppp_are_the_gate_and_tests_only`(`test_ed8_gate_p80_key.py:304-308`, 2263b246 대비 HEAD와 작업 트리, gate와 `05_tests/**`만 허용)와 `test_working_tree_changes_since_c8_stay_off_the_run_path`(:312-319)가 넘겨받았습니다.
  - (c) T8″..T8‴ 실제 변경은 판정 도구 2개와 그 시험 파일이라 허용 목록 안입니다(integrity 확인과 같음).
- **한계(기록)**
  - 고정 범위라서 이 시험은 앞으로 항상 통과하는 "기록"이 됩니다. 관문 구실은 새 T-e가 합니다.
  - 시험 ID가 같아서 P8-4 junit 대조에는 "passed → passed"로만 나옵니다. 본문이 T8⁗에서 바뀌었다는 사실은 판정서 P8-4 항에 따로 적어야 드러납니다.
  - 새 T-e도 다음 판정 커밋에서 같은 문제가 생깁니다(impl 확인 필요 2).

### [기록][S·R] R-4. P8-11 실행 경로 바이트 = C8, 11.2 범위 — 일치 (볼 것 4)
- `scope.py`(python-dev) 결과
  - `05_tests/data/ed8_run_path_modules_56849248.json`의 `files` 156개: `56849248:` 대 `7ea78232:` blob 불일치 0
  - `03_src` 트리 C8 = T8⁗이고, 목록의 `src_tree` 값과도 같습니다.
  - `diff --name-only 56849248 7ea78232` 24개: 04_scripts·05_tests 밖 0개, 실행 경로 목록 안 0개
  - `diff 2263b246 7ea78232` = gate, `test_ed8_gate_p80_key.py`, `test_ed8_jp3_settings.py`
  - 조상: C8·T8·T8″·T8‴가 모두 T8⁗의 조상입니다(`merge-base --is-ancestor`).
  - 목록 json은 T8에서 생겨 C8에는 없습니다. 앞 판에서 받은 그대로입니다.
- `seal_check.py <spec> --const gate:SPEC_V8_SHA256 --const jp3_ed8_judge:SPEC_V8_SHA256`: gate 상수는 맞습니다. `const_not_found` 1건은 `jp3_ed8_judge.py:1426`이 `gate.SPEC_V8_SHA256`를 이어 쓰는 모듈 경유 고정이라 거짓 양성입니다.
- `worktree_locks.py --worktree ed8-judge4`: 종료 0(locked, stale 0)
- 고정 입력: 기준(d60306db)·p816 기준(89efe66f)·`v5\main.jsonl`(9ad74990)의 실제 sha가 도구 상수와 같습니다.
- `baseline_check.py sums`
  - `t8pppp_evidence`: 15항목, 불일치·결측·목록 밖 0, CRLF 0
  - `control_p80p85`: 4항목, 같음
  - `cited_untracked`(16·5)는 R-6을 봅니다.
- `baseline_check identity`는 해당 대상이 없어 돌리지 않았습니다. 판정 출력에는 identity `git` 블록이 아니라 `judge_code`가 있고, 그것은 대조 스크립트가 봅니다.
- `ref_check.py control_p80p85.md --rev 7ea78232 --rev master --exclude .claude --exclude <블라인드 2종>`
  - `ref_missing` 4: 블라인드 패턴 문자열, scratchpad 폴더 이름, 에이전트 메모리 경로 2. 모두 저장소 밖 참조라 정상입니다.
  - `ref_untracked` 17: 아직 커밋하지 않은 근거·판정 출력입니다(R-6).
- 판정 근거 시험 P8-6(`test_p86_…`)과 P8-10(`test_p8_10_…`)은 P8-4 묶음 안의 시험입니다(`audit_prerun\verif_c8_t8.md:87,240`). 그래서 이번 P8-4 재실행이 4단계 단일 T8에 맞게 이 둘도 다시 판정합니다.

### [기록][R·E] R-5. 같은 결함 계열(공용 키가 줄별 관문을 접음)은 다른 관문에 없음 (볼 것 6, T8⁗ 기준)
- 생산자 계획으로 판정 키의 유일성을 셌습니다(`smoke.py`).

| 관문 | 판정 키(코드) | 생산자 계획 | 계획 줄 | 서로 다른 키 | 짝 키(두 팔 모두 있음) |
|---|---|---|---|---|---|
| p85 | (팔, plant, `row_identity`) `gate:335` | `ed8_probe.probe_jobs(("p816",), M·LSM4·Mslow, a8·a8_psw_off)` | 46 | 46 | 23/23 |
| p88 | 같음 | 같음(a8·a8_h3_off) | 46 | 46 | 23/23 |
| p815 | 같음 | 모든 plant, a8·a8_l2_off | 54 | 54 | 27/27 |
| p816 | (팔, plant, `row_identity`) `p816_compare.py:69-115` | 모든 plant, B_impl·L2_impl | 54 | 54 | 27/27 |
| t8 | setting 유지 자체 키 `gate:484-495` | `run_v5.p3_hash_jobs(main.jsonl)` × VBN·VBN0 | 22 job | 44 | – |
| cases | `run_v5.job_key` `jp3_ed8_judge.py:437-458, 1325` | `ed8_batch_jobs(ed8_cases)` | 10 | 10 | – |
| l1ref | 조인 없음(파일·줄별 정체성) `jp3_ed7_judge.py:1549-1582` | – | – | – | – |

- 팔 짝 관문이 접히지 않는 이유가 코드에 있습니다.
  - `ed8_probe.probe_jobs`(:378-388)가 `run_v5.job_key`(setting 포함)로 계획을 중복 제거합니다.
  - setting ↔ (plant, 팔)이 일대일입니다(`split_setting_name`, :416).
  - `_part`·`_r79_plan`은 worker에서 떼어집니다(:410-411).
- 접힘이 생겨도 조용히 통과하지는 않습니다. `probe_pairs`는 `len != 1`을 `pairing_problems` → setting_defect로 보내고(:342-343), p816은 `duplicated` → 비통과로 보냅니다(:122-123). T8‴ 출력에서 p85·p88·p815 `pairing_problems`는 빈 목록이었고, p816 `counts`에 `duplicated`·`missing` 상태는 없었습니다.
- 내 앞 R-3을 T8⁗ 기준으로 다시 확인했습니다. 결함은 p80에만 있었고 T8⁗에서 고쳐졌습니다.

### [기록][E] R-6. 근거 폴더 미추적·기타
- `t8pppp_evidence\`(16)와 `control_p80p85\`(5)는 미추적입니다. ignore에는 걸리지 않습니다(`cited_ignored` 0). 판정서가 이 sha들을 인용하므로 판정서 커밋에 함께 넣습니다.
- `v5\main.jsonl`(t8 고정 입력)은 `.git/info/exclude:23`으로 로컬 제외라 추적되지 않습니다. T8‴와 같고, sha 고정과 `pinned_input`(→ setting_defect)으로 보호됩니다.
- `gate_scan`: `row_value_path_no_base` 1건(`gate:187` `step_output_problems`의 `.done` `folder`). AST로 T8‴와 같은 부분이고, 그 `folder`는 `Complete-Step`이 절대 경로로 씁니다(T8‴ 8개가 그 값으로 정상 판정됨). 새 문제가 아닙니다.
- 기준에 문제가 있으면서 run 쪽에도 문제가 있을 때 failed가 앞서는 분기(impl 확인 필요 3, 결정 6)가 있습니다. 그러나 CLI 경로에서는 기준 sha가 고정돼 있고 고정 기준의 문제는 0이라, 이 분기에는 닿지 않습니다.

### [기록][I] R-7. source_guard strict 위반 1건은 P8-4가 만든 폴더
- `verify --strict-additions` 결과: "원본 불변: 위반 — 입력 폴더에 항목 추가 1건(__pycache__)"
- 추가된 항목은 `ed8-judge4\04_scripts\04_hydraulic\coupled\__pycache__`입니다(첫 pyc 20:14:18).
- 스냅숏은 20:13:20, P8-4 시작은 20:13:39입니다. 그 안의 pyc 이름은 모두 내가 import하지 않은 모듈이고, 내 실행은 `-B`였습니다.
- 입력 파일 15개의 해시·크기·mtime은 모두 같습니다(아래 줄).

## 규칙↔도구 대조표 (T8⁗)

| 항목 | 규칙 | 도구 | 판단 |
|---|---|---|---|
| P8-0 대상 | `spec:361` 114줄, 줄별 해시 | `gate:97` `P80_LINES=114`, `:302-303` | 같음 |
| P8-0 줄 정체성 | 서로 다른 114 job(setting = 플랜트) | `:248-260` `run_v5.job_key`, `:298-299` | 같음(B-1 해소, 스모크 114/114) |
| run 결측·중복·오류 | `spec:361` "다르면 멈춤"(실패) | `:304, 307-314` failures | 같음(결정 6) |
| 기준 쪽 문제 | `spec:345` 목록 밖 = setting_defect | `:300-303, 305-307` 비교 안 함, None | 같음(M-1 해소) |
| 상태 순서 | `spec:338` | `jp3_ed8_rules.status_of`(blob 불변) | 같음 |
| 팔 짝·t8·p816·cases·l1ref | 4절·12절 | blob과 AST 불변 | T8‴와 같음 |
| T8 범위 | `spec:354` 11.2 | diff C8: 04_scripts·05_tests만, 실행 경로 156 불일치 0 | 같음 |
| P8-4 | `spec:364` 새 실패·새 건너뜀 | 러너 진행 중 | 판정 전(M-1) |

## 재판정 명령 수정안 (볼 것 5) — 원문
- 아래 두 파일은 메인이 저장합니다(.ps1·.py, 원문 그대로). 제안 위치는 `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\stage4_prejudge_t8pppp\`입니다.
- 검사 결과
  - `ps1_lint.py`: 종료 0(ast, 0건)
  - `placeholder_scan.py --pattern-set both`(두 파일): 종료 0(unfilled 0)
  - 대조 스크립트 자기 시험
    - T8‴ 폴더를 자기 자신과 대조: 7개 모두 same, 새 폴더 정체성 false라서 종료 1. 정체성 검사가 작동함을 뜻합니다.
    - 없는 폴더: 종료 2
- 기대 종료 코드: p85는 결정 D-2 3에 따라 not_judgeable(종료 2)이 예상됩니다. 그래서 스크립트 전체 종료는 1로 끝나는 것이 정상일 수 있습니다. 관문별 줄 `<name> exit N`을 보고 판단합니다.

### `run_stage4_gates_t8pppp.ps1`
```powershell
#Requires -Version 7
# Stage 4 gate re-judgement at T8'''' 7ea78232 (decision D-2, 2026-11-27: the eight stage 4 gates
# again with the fixed P8-0 line key; C8 is not rerun; judge_2263b246 is kept as superseded).
# Copy of stage4_prejudge_t8ppp\run_stage4_gates_t8ppp.ps1 with the judge checkout, the head, the
# output folder, the numba cache and the clean checks changed; the gate arguments are the same.
# Run by the main session after the formal P8-4 at 7ea78232 has ended (its p84.done) and its
# ignored __pycache__ folders in ed8-judge4 are removed (t8pppp_evidence\clean_pycache.py).
# Exit: 0 every gate exit 0 / 1 a gate exit other than 0 (stop and ask) / 4 the judge checkout
# changed during the run (stop and ask). A throw before the first gate writes nothing.
$ErrorActionPreference = 'Stop'
$JudgeRoot = 'C:\workspace\outrigger_control\.claude\worktrees\ed8-judge4'
$JudgeHead = '7ea782323c427917709ecbb365a58044449beac2'
$Py = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$RunRoot = 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\56849248'
$OutRoot = Join-Path $RunRoot 'judge_7ea78232'
$P84Done = 'C:\Users\jinbeom\.claude\runners\outrigger-ed8\p84_t8pppp_7ea78232\out\p84.done'
if (Test-Path -LiteralPath $OutRoot) { throw "output folder exists: $OutRoot" }
if (-not (Test-Path -LiteralPath $P84Done)) { throw "P8-4 at 7ea78232 has not ended: $P84Done" }
$headBefore = (& git -C $JudgeRoot rev-parse HEAD)
if ($LASTEXITCODE -ne 0) { throw 'git rev-parse failed' }
if ($headBefore.Trim() -ne $JudgeHead) { throw "judge HEAD $headBefore" }
$dirtyBefore = @(& git -C $JudgeRoot status --porcelain --ignored)
if ($LASTEXITCODE -ne 0) { throw 'git status failed' }
if ($dirtyBefore.Count -ne 0) {
    throw "judge checkout not clean (tracked, untracked or ignored): $($dirtyBefore.Count) lines"
}
$env:MKL_THREADING_LAYER = 'TBB'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:NUMBA_CACHE_DIR = 'C:\Users\jinbeom\.claude\runners\outrigger-ed8\numba_cache\judge_7ea78232'
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
foreach ($gateName in $Codes.Keys) { Write-Output "$gateName exit $($Codes[$gateName])" }
$headAfter = (& git -C $JudgeRoot rev-parse HEAD)
$dirtyAfter = @(& git -C $JudgeRoot status --porcelain --ignored)
if ($headAfter.Trim() -ne $JudgeHead -or $dirtyAfter.Count -ne 0) {
    Write-Output "STOP: judge checkout changed (head $headAfter, $($dirtyAfter.Count) status lines)"
    exit 4
}
$nonZero = @($Codes.Keys | Where-Object { $Codes[$_] -ne 0 })
if ($nonZero.Count -ne 0) { exit 1 }
exit 0
```
- 옛 `run_stage4_gates_t8ppp.ps1`(87ddc7fe)과 다른 점
  - 판정 루트 ed8-judge4, HEAD 7ea78232, 출력 `judge_7ea78232`(있으면 거부), numba 캐시 폴더
  - `p84.done` 선행 조건
  - 앞·뒤 깨끗함 검사 모두 `--ignored`. 옛 스크립트의 뒤 검사는 `--ignored`가 없었고 경고만 냈습니다.
  - git 실패 검사, 종료 코드 0·1·4
- 8개 관문의 인자는 바이트 그대로입니다.

### `compare_stage4_t8ppp_t8pppp.py`
```python
"""Stage 4 after-compare (control_p80p85.md 5 "메인 순서" 5; decision D-2): the seven gates
other than p80 judged at T8'''' (judge_7ea78232) against T8''' (judge_2263b246).

Reads only the judge output JSON files of the two folders (never a run line). Prints, per gate,
the two statuses, booleans (status, status_basis, count fields, whole report without
``judge_code``) and the NAMES of the report fields that differ; never a field value, a list
entry or a hash. The judge identity of the new folder (head 7ea78232, clean) is checked for all
eight files, p80 included (identity only).

Usage (python-dev): python.exe -I -B compare_stage4_t8ppp_t8pppp.py OLD_FOLDER NEW_FOLDER
  OLD_FOLDER = j9_runs/56849248/judge_2263b246, NEW_FOLDER = j9_runs/56849248/judge_7ea78232
Exit: 0 every gate the same / 1 a difference or an identity problem / 2 an input error.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

GATES = ("p816", "p85", "p88", "p815", "t8", "cases", "l1ref")
OLD_HEAD = "2263b2461238da7f93eda147838c01c847315561"
NEW_HEAD = "7ea782323c427917709ecbb365a58044449beac2"
NOT_COMPARED = ("judge_code",)
MISSING = object()


def load(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path.name}: not a JSON object")
    return document


def count_fields(report: dict) -> dict:
    """Top-level numbers and booleans, and the length of every top-level list."""
    counts = {}
    for key, value in report.items():
        if key in NOT_COMPARED:
            continue
        if isinstance(value, (bool, int, float)) or value is None:
            counts[key] = value
        elif isinstance(value, list):
            counts[f"len({key})"] = len(value)
    for key, value in (report.get("status_basis") or {}).items():
        counts[f"len(status_basis.{key})"] = len(value) if isinstance(value, list) else value
    return counts


def identity_ok(report: dict, head: str) -> bool:
    code = report.get("judge_code") or {}
    return code.get("head") == head and code.get("is_clean") is True


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(json.dumps({"status": "input_error", "reason": "two folders expected"}))
        return 2
    old_dir, new_dir = Path(argv[0]), Path(argv[1])
    try:
        old = {gate: load(old_dir / f"{gate}.json") for gate in GATES}
        new = {gate: load(new_dir / f"{gate}.json") for gate in GATES}
        new_p80 = load(new_dir / "p80.json")
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}))
        return 2
    rows, all_same = [], True
    identity = {"p80": identity_ok(new_p80, NEW_HEAD)}
    for gate in GATES:
        a, b = old[gate], new[gate]
        fields = sorted((set(a) | set(b)) - set(NOT_COMPARED))
        differing = [key for key in fields if a.get(key, MISSING) != b.get(key, MISSING)]
        ca, cb = count_fields(a), count_fields(b)
        row = {"gate": gate, "status_old": a.get("status"), "status_new": b.get("status"),
               "status_same": a.get("status") == b.get("status"),
               "status_basis_same": a.get("status_basis") == b.get("status_basis"),
               "count_fields_same": ca == cb,
               "count_fields_differing": sorted(k for k in set(ca) | set(cb)
                                                if ca.get(k, MISSING) != cb.get(k, MISSING)),
               "whole_same": not differing, "fields_differing": differing,
               "old_identity_ok": identity_ok(a, OLD_HEAD)}
        identity[gate] = identity_ok(b, NEW_HEAD)
        all_same &= row["status_same"] and row["status_basis_same"] and row["count_fields_same"] \
            and row["whole_same"] and row["old_identity_ok"]
        rows.append(row)
    for row in rows:
        print(json.dumps(row, ensure_ascii=False))
    all_same &= all(identity.values())
    summary = {"status": "same" if all_same else "differs", "new_identity_ok": identity}
    print(json.dumps(summary))
    return 0 if all_same else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```
- 실행 명령(재판정 스크립트가 끝난 뒤, PowerShell):
```powershell
$env:MKL_THREADING_LAYER='TBB'; & C:\ProgramData\miniforge3\envs\python-dev\python.exe -X utf8 -I -B C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\stage4_prejudge_t8pppp\compare_stage4_t8ppp_t8pppp.py C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\56849248\judge_2263b246 C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\56849248\judge_7ea78232
```
- 출력하는 것: 관문별 두 상태 문자열, 참·거짓, 다른 필드의 이름만. 값·목록 항목·해시는 출력하지 않습니다.
- "whole_same"은 `judge_code` 밖의 전체 보고를 비교합니다. 여기에는 `inputs`(단계 `.done` sha, 출력 sha)와 `rule` 문자열이 들어 있습니다. 다른 관문의 코드와 입력이 바뀌지 않았으므로 모두 같아야 합니다.
- 종료 1이면 멈추고 묻습니다(명세 5절 5).

## 확인 필요
1. `test_ed8_jp3_settings.py` 변경을 받으면 판정서 P8-4 항에 다음을 적을지 정합니다(감사 권고: 적음). "같은 시험 ID의 본문이 T8⁗에서 고정 범위로 바뀌어 기록이 됐고, 범위 관문은 새 T-e가 맡는다."

## 위임 필요
- 없음. 이번 결함은 없습니다.
- `tools/verif 후보`(python-expert, 지난 감사 제안 유지): "기준 자기 대조 + 그룹 맞바꿈" 검사
  - 입력: 판정 도구 비교 함수, 기준 jsonl, 그룹 필드(setting)
  - 출력: 서로 다른 조인 키 수 대 줄 수, 그룹을 맞바꾼 뒤 differing 수
  - 종료 코드: 다르면 1

## 메인 세션 권고
1. P8-4(`p84_t8pppp_7ea78232`, PID 16836) 종료를 기다립니다. 진행 중이라 건드리지 않았습니다.
2. P8-4가 끝나면 다음을 확인합니다.
   - `junit_skips.py <junit_T8pppp_7ea78232.xml> --critical "test_ed8_|test_p86|test_p8_10|test_ed7_judge|test_ed7_adoption|test_v5_options"`
   - T8‴ 정식 junit과의 `junit_diff.py` 대조: 기대값은 9071개, 실패 2(기존), 건너뜀 134, changed 0, only_B 17
3. `t8pppp_evidence\clean_pycache.py` → `git -C ed8-judge4 status --porcelain --ignored` 0줄 확인
4. 위 `run_stage4_gates_t8pppp.ps1` → 대조 스크립트
5. 근거 폴더 `t8pppp_evidence`·`control_p80p85`(와 새 `stage4_prejudge_t8pppp`)는 판정서 커밋 전에 추적합니다(`cited_untracked`).

## 검사하지 못한 것
- 블라인드 원자료(`impl_*_a1\`, `l1ref_a1\`). 그래서 실제 C8 p80 줄에서 `run_v5.job_key`가 114개로 유일한지는 확인하지 못했습니다. 생산자 쓰기 경로(`d0_plant_split.py:231-236`)와 계획 = 기준 키로 정황만 확인했고, 재판정 출력의 `run_jobs`·`settings_run`이 이를 대신합니다.
- 시험 실행: 지시에 따라 ed8-judge4에서 돌리지 않았습니다. 새 시험 17개는 정식 P8-4에 맡깁니다.
- 수정안 ps1의 실제 실행: 결과 파일을 만드는 명령이라 돌리지 않았습니다. lint와 자리표시 검사만 했습니다.

## 실행한 검증
- python-dev `-I -B`(`MKL_THREADING_LAYER=TBB`)
  - depcheck: STAMP
  - `source_guard snapshot`·`verify`(strict 포함)
  - `seal_check`(const 2), `baseline_check sums` ×2, `ref_check`(블라인드 `--exclude`, `.claude` 제외), `gate_scan`(gate 1개), `ps1_lint`, `placeholder_scan --pattern-set both`, `worktree_locks`
  - 즉석 스크립트: `struct.py`(판정 출력 키 구조), `scope.py`(AST·blob·실행 경로·조상), 대조 스크립트 자기 시험, `-c` 한 줄(pairing_problems·p816 상태 bool)
- dynamics-dev `-X utf8 -I -B`(cwd는 scratchpad, `PYTHONDONTWRITEBYTECODE=1`, `NUMBA_CACHE_DIR`는 scratchpad)
  - `smoke.py`: 잠긴 T8⁗ gate·run_v5·ed7_probe·ed8_probe·p816_compare를 import했습니다. 진단 전용입니다.
  - 자식으로 gate CLI를 2회 실행했습니다(출력은 scratchpad).
- git 조회
  - Bash: log, status, diff, ls-files(`--eol`·`--error-unmatch`), check-attr, check-ignore, worktree list
  - PowerShell: show
- **공개**
  - Bash에서 `git worktree list --porcelain | grep` 파이프 1회를 썼습니다. 정의 위반이고 출력은 정상 종료했습니다.
  - Glob 1회(`j_p3_cause`를 path로 한 `jp3_remedy_spec_v8_rules*`)가 blind_guard에 막혔습니다. 출력은 없습니다. 그 뒤 단일 경로 `Test-Path`로 대신했습니다.
  - ref_check를 잘못된 `--repo` 경로로 1회 실행했고, 결과는 버렸습니다.
- 읽은 파일
  - 감사 요약 문서: `verif_p80p85_postjudge.md`, `control_p80p85.md`, `decision_d2_p80p85_20261127.md`, `impl_report_t8pppp.md`, `integrity_t8pppp_precommit.md`(전체), `clean_pycache.py`
  - 실행 스크립트: `run_stage4_gates_t8ppp.ps1`, P8-4 러너 `p84_step.ps1`·`_runner.log`·`p84_driver.log`·`git_before.txt`
  - 명세: 190~214, 334~373행
  - ed8-judge4 코드: gate 전체, `test_ed8_gate_p80_key.py` 전체, `p816_compare.py` 40~153행, `jp3_ed8_judge.py` 430~464·1318~1377행, `jp3_ed7_judge.py` `judge_l1ref`, `ed7_probe.py` 120~259행, `ed8_probe.py` 300~553행, `run_v5.py` 755~774행
  - 메모리 `audit_pitfalls.md` 일부
- 검색 범위(모두 단일 파일이거나 블라인드를 품지 않은 하위 폴더, 코드 glob)
  - ed8-judge4 `04_scripts`(`*.{py,ps1}`), `coupled`(`{run_v5,ed7_probe}.py`·`jp3_ed8_*.py`·단일 파일들), `05_tests\unit\test_ed8_jp3_settings.py`
  - 메인 `ed8_design`(`*.md`, 파일 목록 모드), `stage4_prejudge\prejudge_report.md`, `audit_prerun\verif_c8_t8.md`, `audit_t8ppp\verif_t8ppp_prejudge.md`
  - Glob: `audit_t8ppp`, `t8pppp_evidence`, `control_p80p85`, `stage4_prejudge_t8ppp`, `p84_suite_T8ppp_2263b246`, `judge_2263b246`, `runners\outrigger-ed8`
  - 경로 2 도구는 열지 않았습니다.
- 만든 뒤 지운 파일: scratchpad `verif-t8pppp\`(스크립트 5개, 수정안 2개, `guard.json`, CLI 합성 `.done`·rows·출력). 폴더째 지웠고 `Test-Path` False를 확인했습니다. 저장소와 ed8-judge4에는 쓰지 않았습니다.
- 메모리: `agent-memory\verif-protocol-auditor\audit_pitfalls.md`의 2026-11-27 항목에 재감사 요령(그룹 맞바꿈, 다른 조인 키 census, 고정 범위 시험 수용 조건, 같은 checkout의 시험 묶음이 남기는 pycache)을 Edit로 덧붙였습니다.
- 원본 불변: 위반 — 입력 폴더에 항목 추가 1건(__pycache__) (strict. 추가 항목 `ed8-judge4\04_scripts\04_hydraulic\coupled\__pycache__`는 20:13:39 시작한 P8-4 pytest PID 16836의 산물, R-7)
- 원본 불변: 확인 — 원본 쓰기 0회, 기존 항목 변경·삭제 0건 (sha jp3_remedy_spec_v8_rules.md 35f9eba8…, jp3_remedy_spec_v8_rules.md.sha256 e19aaa48…, jp3_ed8_gate_judge.py f3b0565c…, test_ed8_gate_p80_key.py cf9bd2cd…, test_ed8_jp3_settings.py b824b3d5…, run_stage4_gates_t8ppp.ps1 87ddc7fe…, ed7_probe_a2.jsonl d60306db…, p80.json 1077f3ab…, p816.json b14d770b…, p85.json 8db37778…, p88.json 39c7909c…, p815.json 990b985a…, t8.json eb0c4aef…, cases.json 54999935…, l1ref.json 20815752…, 폴더 added_only: 새 항목만 생김, ~$ 임시 파일 없음) · 경고: 입력 폴더에 항목 추가 1건(__pycache__)
- 사용한 스킬: 없음
