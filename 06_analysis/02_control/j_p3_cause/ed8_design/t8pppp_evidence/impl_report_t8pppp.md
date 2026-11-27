# 436.9 판 8 판정 도구 T8⁗ 구현 보고 — P8-0(p80) 줄 키 결함 수정 (python-expert, 2026-11-27)

## 0. 요약
- worktree `C:\workspace\outrigger_control\.claude\worktrees\ed8-judge4`(HEAD 2263b246, 커밋하지 않음)에서 명세 `control_p80p85.md` 5절대로 구현했습니다.
  - 바꾼 파일: `jp3_ed8_gate_judge.py`
  - 새 시험 파일: `05_tests/unit/test_ed8_gate_p80_key.py`(17개)
- **명세에 없던 기존 시험 1개를 바꿨습니다.** `test_ed8_jp3_settings.py`의 T8‴ T-e 시험 1개입니다. 이것은 확인 필요 1입니다.
  - 이 시험은 "T8″ 이후 바뀐 경로 = 판정 도구 2개 + 05_tests"를 작업 트리 기준으로 단언했습니다.
  - 그래서 gate 파일을 고치면 반드시 실패합니다. 전체 시험에서 새 실패로 나왔습니다.
  - 비교 범위를 고정 커밋 범위 T8″..T8‴으로 바꿨습니다. T8‴에 대한 원래 단언은 그대로 유지됩니다.
- P8-4 예비 실행 결과입니다(작업 트리, 이 수정 전).
  - 9071개 중 통과 8934, 실패 3, 건너뜀 134
  - T8‴ 정식 junit과 비교하면 상태가 바뀐 시험은 1개(위 T-e)이고, 새 건너뜀은 0개입니다.
  - 수정 뒤에는 바뀐 시험 파일 4개만 따로 다시 돌렸고 81/81 통과했습니다. 수정 뒤 전체 시험은 다시 돌리지 않았습니다. 그래서 정식 P8-4는 커밋 뒤에 다시 돌려야 합니다(메인 세션 권고).
- 블라인드 경로와 경로 2 도구는 어디서도 열지 않았습니다. 실제 C8 출력에 판정 도구를 돌리지 않았고, ed7_probe도 실행하지 않았습니다.

의존성 점검: STAMP(이 세션에서 이미 점검함, 생략)

## 1. 바꾼 것: `04_scripts/04_hydraulic/coupled/jp3_ed8_gate_judge.py`
- **새 함수 `p80_job_key(job) -> str`**
  - 함수 안에서 `import run_v5`를 하고 `run_v5.job_key(dict(job))`를 돌려줍니다.
  - docstring에는 다음을 인용했습니다: spec v8 12 P8-0(361행), `ed7_probe.py:228`(생산자 이어 돌기 키), `run_v5.py:759`(빼는 필드 mask·t4h_dir. setting·`_part`·`_r79_plan`은 키에 남음), 감사 B-1.
- **`hash_table(rows, label, problems, key=row_identity)`**
  - 키워드 `key`를 더했습니다. 기본값이 `row_identity`라서 다른 호출처의 동작은 같습니다.
  - 지역 변수 이름은 `key`에서 `job_key`로 바꿨습니다(인자 이름과 겹치지 않게).
- **`judge_p80`**
  - `run_problems`와 `reference_problems`를 나눴습니다(M-1). 두 표 모두 `key=p80_job_key`로 만듭니다.
  - 기준 쪽 문제는 setting_defects로 갑니다. 문구는 둘입니다.
    - `reference line problems: N`: 오류 줄, 해시 없음, 중복
    - `reference: K jobs, 114 expected`: 기존 문구 그대로
  - setting_defect가 하나라도 있으면 대조하지 않습니다.
    - `reference_compared` false
    - `equal`·`missing`·`extra`·`differing`은 None입니다. 0으로 두지 않습니다(시험 규칙 (다)).
  - run 쪽 줄 문제는 기준 상태와 관계없이 지금처럼 failures `run line problems: N`입니다. missing·extra·differing도 지금처럼 failures입니다. 실패 문구의 순서도 그대로입니다.
  - 보고 키
    - 유지: `rule`, `jobs`(= 서로 다른 기준 키 수)
    - 추가: `key`("run_v5.job_key (spec v8 12 P8-0)"), `run_jobs`, `equal`, `missing`, `extra`, `differing`, `run_line_problems`, `reference_line_problems`, `reference_compared`, `settings_reference`·`settings_run`(job.setting별 줄 수, 해시 없음)
  - setting별 개수는 판정 함수 안의 중첩 함수로 셉니다. 최상위에 정의나 import를 새로 두면 T-e 불변 범위를 깨기 때문입니다.
- **`line_problems` 키는 없앴습니다.**
  - Grep으로 찾은 소비처는 control의 확인 스크립트 `ed8_design\control_p80p85\p80_plan_keys.py:38` 하나뿐입니다.
  - 이 스크립트는 `WT = ...\ed8-judge3`(T8‴)로 고정돼 있어 T8⁗ 출력을 읽지 않습니다. 이미 실행이 끝났고 출력(`.out.json`)도 저장돼 있습니다.
  - 다만 이 스크립트를 ed8-judge4로 바꿔 다시 돌리면 KeyError가 납니다.
  - 그 밖의 소비처: 04_scripts·05_tests·ed8_design의 `*.py`/`*.ps1`, `~/.claude/runners`, 판정 명령 수정안이 든 `verif_t8ppp_prejudge.md`에서 gate의 이 키를 읽는 곳은 0건입니다. 다른 모듈의 같은 이름 함수는 무관합니다.
- **모듈 docstring의 `p80` 단락**: 줄 키(생산자 job_key, setting 유지), 기준 쪽 문제 = setting_defect(10:345)와 대조 안 함, run 쪽은 failures를 적었습니다.
- **바이트 그대로 둔 것**
  - 명세 "하지 말 것"의 정의·상수·CLI
  - `RUNTIME_JOB_KEYS`, `row_identity`, 팔 짝 관문, `judge_t8`, `run_command`, `main`, `P80_LINES`, `P80_REFERENCE_SHA256` 등
  - 시험 T-e가 AST 소스 구간으로 확인합니다.

## 2. 시험: `05_tests/unit/test_ed8_gate_p80_key.py`(새 파일, 17개)

| 명세 | 시험 |
|---|---|
| T-a | `test_p80_key_is_the_producer_job_key`: 계획 114 job(mask·t4h_dir 포함)에서 `p80_job_key == run_v5.job_key`, 서로 다른 키 114, `RUNTIME_JOB_KEYS == ("mask","t4h_dir")`, setting 분포 {M 27, Mslow 27, Mfast·Mc005·Mc04·L 각 15} / `test_t8ppp_row_identity_folds_the_plan_into_27_keys`(회귀 기록) |
| T-b | 섞은 사본(seed 20261127)과 대조하면 pass·114·114 / Mslow D키 1줄 → differing 1, 키에 `"setting": "P7-Mslow-a2"` / 플랜트끼리 해시가 같고 Mfast 한 case만 다름 → differing 1 / Mc04 한 줄 뺌 → missing 1 / 중복 → `run_line_problems` 1("twice") / run 오류 줄 → failed(`run line problems: 1`, `missing jobs: 1`) |
| T-c | 기준에 오류 줄, 해시 없음, 중복 줄(115번째 줄)을 각각 넣음 → `setting_defect`, failures [], `reference_line_problems` 1, `run_line_problems` [], `reference_compared` false, 대조 값 None / 기준 113줄 → `setting_defect`, 대조 안 함 |
| T-d | `git show e241638d:...ed7_probe_a2.jsonl`(`-C` worktree 루트). git 실패나 sha 불일치는 assert 실패이고 skip은 없습니다. sha는 bool로만 단언해 해시가 출력되지 않습니다. `judge_p80(ref, ref)` → pass, 114/114, 문제 0. 기준 키 집합 = 계획 키 집합 |
| T-d + 규칙 (가) | `main p80` 끝까지 실행: 실제 고정 기준 바이트를 tmp에 쓰고, `.done` 꼴을 만들고, CWD는 다른 폴더입니다. 자기 대조 → 종료 0 pass. 한 줄 해시 변경 → 종료 1, `differing hashes: 1` |
| T-e | `test_other_gates_are_the_t8ppp_source`: 2263b246 blob, HEAD blob, 작업 파일의 최상위 문장 가운데 {judge_p80, hash_table, p80_job_key}와 모듈 docstring을 뺀 나머지의 소스 구간(줄 끝 정규화)이 셋 다 같음 / `test_changes_since_t8ppp_are_the_gate_and_tests_only`: `diff 2263b246 HEAD` ∪ `diff 2263b246`(작업 트리) ⊂ {gate, 05_tests/**} |
| T-f | 기존 `test_ed8_run_path.py` 4개 통과. 추가로 `test_working_tree_changes_since_c8_stay_off_the_run_path`: 작업 트리 diff C8 ⊂ 04_scripts·05_tests이고 실행 경로 목록 밖 |
| T-g | `test_ed8_gate_judge.py`는 바꾸지 않았고(blob = 2263b246) 전부 통과 |
| T-h | 새 시험을 절대 경로·`-p no:cacheprovider`로 cwd = worktree 루트에서 17 passed(종료 0), cwd = 저장소 밖 scratchpad 폴더에서 17 passed(종료 0). 실행 뒤 그 폴더에 파일 0개. 실행 뒤 `status --porcelain --ignored`에는 의도한 변경만 남음 |

- 생산자 꼴 시험(규칙 (가′))은 정상 줄과 오류 줄(`{"job", "error"}`) 두 종류를 모두 넣었습니다.
- 생산자 꼴이 아닌 하위 명령(규칙 (다′))은 해당하지 않습니다. T-d와 main 시험이 실제 고정 기준(생산자 출력)을 씁니다.

## 3. 기존 시험 변경(05_tests, 명세 금지 목록 밖) — 확인 필요 1
- `05_tests/unit/test_ed8_jp3_settings.py::test_e_changes_since_t8pp_are_the_two_judges_and_tests`(T8‴ D-1의 T-e)
  - 원래는 `git diff --name-only 5955f25b`(작업 트리)의 경로가 `T8PPP_CHANGED_PATHS`(판정 도구 2개) 또는 05_tests 안에 있는지 봤습니다. T8⁗가 gate를 바꾸므로 구조적으로 반드시 실패합니다.
  - 전체 시험에서 passed → failure로 나왔고, 메시지는 `AssertionError: 04_scripts/04_hydraulic/coupled/jp3_ed8_gate_judge.py`입니다.
- 바꾼 내용
  - 상수 `T8PPP_COMMIT = "2263b246…"`을 더했습니다.
  - 비교를 `git diff --name-only T8PP_COMMIT T8PPP_COMMIT`(고정 범위)로 바꿨습니다. docstring에 그 이유와 T8⁗ 쪽 확인 위치를 적었습니다.
  - 허용 목록은 넓히지 않았습니다.
- T8‴의 깨끗한 checkout에서는 두 비교가 같은 결과를 내므로, T8‴에 대한 단언의 세기는 같습니다. T8⁗의 범위는 새 T-e(`2263b246` 기준)가 맡습니다.
- 이 변경이 마음에 들지 않으면 되돌리면 됩니다. 그 경우 P8-4에 새 실패 1개가 남습니다.
- 같은 한계: 새 T-e `test_changes_since_t8ppp_are_the_gate_and_tests_only`도 다음 판정 커밋(T8⁵)이 다른 파일을 바꾸면 똑같이 실패합니다. 명세 T-e 꼴(`2263b246 HEAD`)을 그대로 따랐기 때문입니다.

## 4. P8-4 예비 실행(T8⁗ 작업 트리, 3절 수정 전)
- 조건: Chrono-dev `-I -B -m pytest 05_tests/unit -n 12 --dist loadfile -p no:cacheprovider --junitxml=…`
  - 환경: `OUTRIGGER_RECORDS_ROOT=C:\workspace\outrigger_control`, `PYTHONDONTWRITEBYTECODE=1`, `NUMBA_CACHE_DIR`·`HYPOTHESIS_STORAGE_DIRECTORY`는 scratchpad
  - cwd = ed8-judge4
  - 시작 전 `status.py`: 유효 예약 0, pinned tenant 0. affinity는 고정하지 않았습니다.
  - 드라이버 PID 107072, 2026-11-27 19:38:36 → 20:04:11

| 실행 | 시험 | 통과 | 실패 | 오류 | 건너뜀 | 시간 |
|---|---|---|---|---|---|---|
| T8‴ 정식 junit `p84_suite_T8ppp_2263b246\junit_T8ppp_2263b246.xml` | 9054 | – | 2 | – | 134 | – |
| **T8⁗ 작업 트리** | 9071 (= 9054 + 새 17) | 8934 | 3 | 0 | 134 | 1534.8 s |

- `junit_diff.py` 비교 결과: only_A 0, only_B 17(새 시험 17개 모두 passed), changed 1(3절의 T-e, passed → failure)
- 기존 실패 2개(T8‴와 같음): `test_hydraulics_flow_limit_run::test_coupled_batch_rows_and_resume`, `test_d8x_diag::test_rerun_gives_the_stored_command_hash`
- 새 건너뜀 0(134 → 134). xfail은 없습니다.
- xdist 순서 의존 파일(`test_k2_chrono_runner`·`test_s8_soil_restore`)은 이번에는 오가지 않았습니다(changed 목록에 없음).
- pytest 종료 코드 1(실패 3). stderr 로그는 0 바이트입니다.
- 3절 수정 뒤 단독 재실행: `test_ed8_jp3_settings.py` + 새 시험 + `test_ed8_gate_judge.py` + `test_ed8_run_path.py` → 81 passed, 종료 0
- 전체 시험은 수정 뒤에 다시 돌리지 않았습니다. 정식 P8-4는 메인 세션 권고를 봅니다.
- 실행 뒤 ignored `__pycache__` 13개가 생겨 있었습니다(`PYTHONDONTWRITEBYTECODE`를 받지 않는 시험 자식 프로세스로 추정. T8‴ 정식 실행에도 `pycache_paths.txt`가 있었습니다).
  - `clean_pycache.py`로 `git status --porcelain --ignored`의 `!! …/__pycache__/` 경로만 골라 지웠습니다.
  - 지운 경로: 03_src/outrigger_sim{,/control,/hydraulics,/sensors}, 04_scripts/01_dynamics, 02_chrono, 03_control{,/d8x,/r8d1,/s8,/s9,/touch_phase/acceptance}, 04_hydraulic/coupled

## 5. 바이트·범위 대조(`byte_check_T8pppp.json`, Python subprocess 스크립트 하나)
- C8 실행 경로 목록 156개 파일: 작업 파일 blob 불일치 0
- 03_src: HEAD 트리 = 목록 트리, 작업 트리 diff 없음
- "하지 말 것" 파일 8개의 작업 파일 blob = 2263b246 blob(모두 true): `jp3_ed8_judge.py`, `jp3_tjr_judge_ed8.py`, `jp3_ed8_rules.py`, `p816_compare.py`, `run_v5.py`, `ed7_probe.py`, `j_p3_inputs.py`, `test_ed8_gate_judge.py`
- `git diff --name-only 2263b246`(작업 트리) = gate, `test_ed8_jp3_settings.py`. 추적되지 않은 파일은 새 시험 1개입니다.
- `git diff --name-only 56849248`(작업 트리): 23개. 04_scripts·05_tests 밖 0개, 실행 경로 목록 안 0개
- ruff(worktree pyproject 설정, `--no-cache`)·codespell·`git diff --check`: 바꾼 3개 파일 모두 0건(종료 0)
- 줄 끝(작업 파일)
  - gate와 `test_ed8_jp3_settings.py`는 autocrlf로 CRLF이고 섞이지 않았습니다(gate 607/607, settings 333/333).
  - 새 시험 파일은 LF입니다.

## 6. 커밋할 파일(작업 파일 raw sha256)

| 파일 | 상태 | sha256 |
|---|---|---|
| `04_scripts/04_hydraulic/coupled/jp3_ed8_gate_judge.py` | M | `f3b0565c15428511ee4598a702c3431bb49a6fcd97f177f928100a08e1fd5c11` |
| `05_tests/unit/test_ed8_gate_p80_key.py` | ?? (새 파일) | `cf9bd2cd639dad56b66d69d70f6ddd813d83401e4160ff0612435063635e296d` |
| `05_tests/unit/test_ed8_jp3_settings.py` | M | `b824b3d5cb5e4bb08a055b3be5d97f13b4e1e2c59c178b5108fb126b001e70f2` |

마지막 `git -C ed8-judge4 status --porcelain --ignored`(HEAD 2263b246):
```
 M 04_scripts/04_hydraulic/coupled/jp3_ed8_gate_judge.py
 M 05_tests/unit/test_ed8_jp3_settings.py
?? 05_tests/unit/test_ed8_gate_p80_key.py
```

제안 커밋 메시지:
```
436.9 ed8 judge commit T8'''': P8-0 line key = producer job key (audit B-1, M-1)

- jp3_ed8_gate_judge: p80_job_key = run_v5.job_key (setting, the plant of
  the ed7_probe a2 lines, stays in the key; spec v8 12 P8-0); hash_table
  takes the key (default row_identity, the arm-pair gates unchanged);
  judge_p80 keeps run and reference line problems apart: a reference
  problem or a reference of not 114 jobs is a setting defect and nothing
  is compared (reference_compared false); run problems stay failures;
  report keys run_jobs, run/reference_line_problems, settings_* (line_problems removed)
- test_ed8_gate_p80_key: T-a .. T-h of control_p80p85.md 5 (producer plan
  lines, the pinned e241638d reference against itself, main end to end
  from another cwd, the other gates' source equal to T8''')
- test_ed8_jp3_settings: the T8''' scope test reads the fixed range
  T8''..T8''' (it read the working tree and failed on any later judge commit)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01S2ErLKQQpuRHeBUsoPmLoF
```

## 7. 증거 파일(`C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\t8pppp_evidence\`, SUMS는 메인이 씀)

| 파일 | sha256 |
|---|---|
| `junit_T8pppp_worktree.xml` | `813acf7a7fbffb7762fcf8e5d12124349141b11a6d2d4a5771c323de72205186` |
| `suite_T8pppp_worktree.txt` / `.err.txt`(0 B) | `0b5047e0296074daabe13b757edeb80a94018d671789245729a33b88ed490111` / `e3b0c442…b855` |
| `junit_compare_T8ppp_formal_vs_T8pppp.txt` | `65f1992c72ad83269c04b84ee5eaeb1a7706926674c4e5c74932865df2927d04` |
| `junit_T8pppp_changed_files_alone.xml` / `T8pppp_changed_files_alone.txt` | `43a5b6f83f0cedbe7c0c89be164b7962efb167eb01701befb9986d47cb2b709b` / `d8cbe48bc35fe4ec4edf3c2fe144892563ea38cea2a507046e3cf23603f33c9f` |
| `byte_check_T8pppp.json` / `byte_check.py` | `13af11e17d7893e7ef013859da175eb2b10865a8b53143e0f09c6a343d7dc8ef` / `be2314a90a30f06eee29127cef7f358a1668c2d2f0c8b7cc4eb790a4bd0f55bc` |
| `suite_T8pppp_worktree.ps1`(실행 드라이버) | `cf51e6e3dd27b376f60d0d7a83ce25224a11de77c0098693279a27d3e5e1fe2a` |
| `clean_pycache.py` | `981b94d3c267f7ee1be8f52896064b390cc5b4a23154253d17a37089ddbcc278` |
| `git_before.txt` / `git_after.txt` | `df94f3f7…f895` / `ef427ec8…e8d9` |
| `time_start.txt` / `time_end.txt` | `b18c5965…0e` / `2dd94454…c7` |

- `suite_T8pppp_worktree.txt`에는 기존 실패 `test_d8x_diag`의 assert가 시험 자료의 명령 해시 두 개를 찍은 줄이 있습니다. 시험 자체의 출력이고, P8-0 기준이나 블라인드 자료의 값은 아닙니다.
- 드라이버 ps1 안의 경로는 scratchpad를 가리킵니다(실행 기록용). scratchpad 폴더는 지웠습니다.

## 확인 필요
1. **3절의 기존 시험 변경**(`test_ed8_jp3_settings.py` T-e를 고정 범위 T8″..T8‴으로 바꿈)을 받을지 정해 주십시오.
   - 명세 5절은 "05_tests만"을 허용했고, 바꾸지 말라고 한 파일은 `test_ed8_gate_judge.py`뿐입니다. 하지만 기존 시험의 비교 대상을 바꾸는 일이므로 감사 확인 대상입니다.
   - 되돌리면 P8-4에 구조적 새 실패 1개가 남습니다.
   - 다른 길: 허용 목록에 gate를 더하는 것. 이 길은 T8‴ 단언을 약하게 만들어 추천하지 않습니다.
2. **새 T-e의 한계**: 명세 꼴(`2263b246 HEAD`, 작업 트리 포함)이라서 다음 판정 커밋이 gate·05_tests 밖을 바꾸면 실패합니다. 지금은 문제가 없습니다. 판 8 안에서 또 판정 커밋을 만들게 되면 같은 처리가 필요합니다.
3. (낮음) 기준에 문제가 있어도 run 쪽 줄 문제는 failures로 셉니다(failed가 setting_defect보다 앞섬). 명세 "run 쪽 문제는 지금처럼 failures"를 그대로 읽은 것입니다. 기준 sha가 고정돼 있어 CLI 경로에서는 기준 문제에 닿을 수 없습니다.

## 메인 세션 권고
- 커밋 뒤 정식 P8-4: 깨끗한 T8⁗ checkout에서 `p84_suite_T8ppp_2263b246\p84_step.ps1`과 같은 꼴(Chrono-dev `-n 12 --dist loadfile`, 자동 재실행 없음)로 돌려 주십시오.
  - 출력: `~/.claude/runners/outrigger-ed8/p84_t8pppp_<앞 8자>/`
  - 예상 시간: 약 26분
  - 비교 기준선: `junit_T8ppp_2263b246.xml`, 비교 스크립트: `junit_diff.py`
  - 기대 결과: 9071개, 실패 2(기존), 건너뜀 134, changed 0, only_B 17
- 그 뒤에는 명세 5절 "메인 순서" 2~6(재감사 → 4단계 관문 8개 재판정)입니다.

## 위임 필요
- verif-protocol-auditor(`[시점] 실행 전`): T8⁗ 재감사. p80 기준 자기 대조 스모크(새 시험 T-d·main 시험이 같은 일을 함), T-e 불변 범위, P8-11, 그리고 확인 필요 1의 기존 시험 변경.
- (감사 제안의 tools/verif "기준 자기 대조" 도구는 이번 범위에서 만들지 않았습니다.)

## 공개(읽은 파일·검색 범위)
- **Read**
  - 명세 `control_p80p85\control_p80p85.md`(전체), `p80_plan_keys.py`(전체)
  - `audit_t8ppp\verif_p80p85_postjudge.md`(전체), `decision_d2_p80p85_20261127.md`(전체)
  - `t8ppp_evidence\impl_report_t8ppp.md` 90~164행
  - `p84_suite_T8ppp_2263b246\p84_step.ps1`·`junit_diff.py`
  - ed8-judge4: `jp3_ed8_gate_judge.py`(전체), `ed7_probe.py` 100~269행, `test_ed8_gate_judge.py`(전체), `test_ed8_run_path.py`(전체), `test_ed8_jp3_settings.py` 1~75행
  - scratchpad의 내 실행 로그
- **Grep**(모두 `glob`으로 코드 파일만, 또는 단일 파일)
  - ed8-judge4: `04_scripts`(`*.{py,ps1}`), `05_tests`(`*.{py,ps1}`), `04_hydraulic\coupled`(`{run_v5,ed7_probe}.py`), `05_tests\unit`(`*.py`, `test_ed8_*.py`), 단일 파일 `test_ed8_run_path.py`·`test_ed8_jp3_settings.py`·`ed7_probe.py`
  - 메인: `ed8_design`(`*.{py,ps1}` 그리고 `*.md`에서 `run_stage4_gates_t8ppp` 이름만), 단일 파일 `audit_t8ppp\verif_t8ppp_prejudge.md`(건수)
  - `C:\Users\jinbeom\.claude\runners`(`*.{py,ps1}`, 파일 목록 모드. 나온 것은 지난 실행의 05_tests 사본뿐)
  - scratchpad 내 suite 로그(단일 파일)
- **Glob**: `ed8_design\p84_suite_T8ppp_2263b246\` 한 폴더
- **git**
  - Bash 짧은 조회: ed8-judge4 `status`·`rev-parse`
  - PowerShell: `diff --check`·`diff --stat`·`diff`(settings 파일)·`status`
  - 시험·스크립트 안의 git: `show 2263b246:/HEAD:<gate>`, `show e241638d:<기준>`, `diff --name-only`, `hash-object`, `rev-parse`, `ls-tree`, `ls-files --others`
- **고정 기준**: 시험이 git blob으로만 읽었습니다. 해시 값은 출력·보고하지 않았습니다. 메인 checkout 사본은 열지 않았습니다.
- **블라인드**(`j9_runs\56849248\impl_*_a1\`, `l1ref_a1\`, worktree 사본): Read·Grep·Glob·스캔 어디에도 쓰지 않았습니다. 블라인드를 품은 상위 폴더(j9_runs, 56849248, j_p3_cause, 06_analysis, 저장소 루트, worktree 루트)를 검색 범위로 쓰지 않았습니다. 경로 2 도구는 열지 않았습니다.
- **쓰기**
  - ed8-judge4: 위 3개 파일. 정션·링크는 없습니다.
  - 메인 checkout: `t8pppp_evidence\` 새 폴더(14개 파일)
  - 잠긴 ed8-judge3·ed8-judge2·ed8-impl, 규칙 파일, 03_src에는 쓰지 않았습니다.
- **프로세스**: 내가 띄운 PowerShell 드라이버 PID 107072(pytest 자식 포함)는 스스로 끝났습니다. 종료 명령은 쓰지 않았습니다.
- **scratchpad**: `…\scratchpad\python-t8pppp\`만 썼고 폴더째 지웠습니다(`Test-Path` False).
- **종료 코드**: depcheck STAMP, 전체 pytest 1(실패 3), 바뀐 파일 단독 pytest 0, T-h 두 번 0, ruff 0, codespell 0, `diff --check` 0, byte_check 0, clean_pycache 0

## 메모리 반영안
- `agent-memory\python-expert\tool_parent_diff_tests_break_children.md`: "부모 커밋 이후 변경" 범위 시험이 작업 트리나 HEAD를 읽으면 다음 판정 커밋에서 반드시 실패합니다. 전체 시험 전에 grep으로 찾고, 고정 범위로 다시 고정한 뒤 공개합니다. MEMORY.md 색인에 1줄을 더했습니다.

사용한 스킬: 없음
