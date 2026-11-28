# 판 9(436.9) 구현 3차 보고 — R3 전 감사 수정 + C9′/T9′ (python-expert, 2026-11-28)

- **성격**: 판 9 설계용 구현이다. 판정이 아니고 봉인 전이다. 규칙 문서는 쓰지 않았다. R3·R4 실행은 하지 않았고, 명령만 9절에 적었다.
- **근거 문서**
  - `ed9_design\audit_r3_prerun\report.md`(차단 2·수정 8)
  - `ed9_design\control_r3_check\report.md`(전체)
  - `ed9_design\stats_r3_check\report.md` 3.2
  - decision_log 4절 끝의 "R3 전 결정" 줄
- `scan_d1_step.json`의 값은 이 보고에 인용하지 않는다.

## 0. 요약
| 항목 | 결과 |
|---|---|
| C9′ (control 8 (a), 4 관문 1) | 실행 커밋 `15d3a4a4f0d3244c242e98856d2228160d090b2d`. 처리 팔 배치 `ed9_keys`·`ed9_t8`·`ed9_cases`를 C-m 켬으로 더했다. C-m 켬 ∧ soil 끔이면 run 뒤 관문에서 거부한다. 고정 worktree는 `ed9-c9b`다(잠금은 메인) |
| T9′ (C9′의 자식) | 판정 커밋 `c79b009a6c318d6c3fb5f4bdb0aa7b26edb44528`, worktree `ed9-t9b`(잠금은 메인). 넣은 것: ED9 run_commit = C9′, ITEM_GROUPS FAULT 판별을 후보 `final`로, census rerun V0 개수·키 집합 검사, M-6 diff 범위 시험 2개, M-7 spec 봉인 관문(`--design-reading`)과 rule 문자열 |
| B-2 | `compare_identity.py --stored-tag-absent <태그>`와 합성 시험. ④ 명령을 고쳤다 |
| M-4 | `d1_prerun\r3c_expected_d1_step.json`(sha `046bd02b…`, 9 job)을 만들었다. ⑥②는 `--allowed-from … --allowed-group r3c_expected --require-allowed-change` |
| stats 3.2 조건 2 | 새 스캐너 `scan_d1_step_rows.py`가 끔 쌍둥이 7줄을 키만 스캔한다. 그 출력이 ③의 허용 집합이다 |
| stats 3.2 조건 3 | `--require-prior <보고>`(여러 번 줄 수 있음)로 ①→②, ④→⑤, ⑥①→⑥② 순서를 단언한다 |
| M-5 | `r3c_run.py --expect-head <40자>`(필수). 시작·끝 HEAD가 다르거나 tracked 변경이 있거나 git 호출이 실패하면 종료 2 |
| control 5 | `compare_identity`에 넣은 것: ③≡② 관문(`--with-d1-reasons`), 경로 표지(`--stored-path-under`/`--new-path-under`), ②≡R3b 겹침(`--only-common --expect-compared 5`) |
| stats R3 권고(R2) | `ml_inject_cm_bands.py`에 `event_band`(에피소드 사건 시각 기준)와 `row_role` 칸을 더했다. 새 출력 `*_ev.*`를 냈고, 옛 출력과 합이 맞는다(아래 6절) |
| 시험 | 33파일, 1546 passed, 31 skipped(모두 pychrono 없음), 실패 0. `junit_skips --critical "test_ed9_\|test_ed8_run_path\|test_ed8_gate_p80_key"` 종료 0(critical_skipped 0) |
| `--list` @C9′ | 678 / 339 / 339 / 7 / 100(끔·켬 같음). 처리 팔: ed9_keys 1043(census)·339(G′), ed9_t8 44, ed9_cases 10. aa2를 `--jobs-file` 없이 돌리면 종료 2(B-1 꼴 재현). 실행 전후 HEAD는 C9′, `status --ignored`는 0줄 |

## 1. 커밋과 worktree
| 이름 | ref | 내용 | 잠금 |
|---|---|---|---|
| `ed9-impl` | 브랜치 ed9-impl, HEAD `c79b009a` | … C9 `86121e8f` → T9 `2deb5fd7` → **C9′ `15d3a4a4`** → **T9′ `c79b009a`** | 안 잠김(작업 브랜치) |
| `ed9-c9b`(새로 만듦) | detached `15d3a4a4f0d3244c242e98856d2228160d090b2d` | C9′ | **메인이 잠근다** |
| `ed9-t9b`(새로 만듦) | detached `c79b009a6c318d6c3fb5f4bdb0aa7b26edb44528` | T9′ | **메인이 잠근다** |
| `ed9-c9`, `ed9-t9`, `ed9-diag` | 그대로 | 손대지 않음 | 잠김(기존) |

- C9′는 T9의 자식이다. 브랜치를 한 줄로 이었기 때문이다. 그래서 C9′ 트리에는 T9의 판정 도구 변경이 들어 있다.
  - 이 변경은 실행 경로 밖이다. M-6 (b) 시험이 실행 경로 목록과 `03_src`로 걸러 확인한다.
  - 판정 변경이 없는 실행 커밋이 필요하면 C9 위에 다시 만들 수 있다(확인 필요 2).
- `git diff --stat 2deb5fd7 15d3a4a4`: `run_v5.py`, `verdict_runs.py`, `test_ed9_cm_switch.py`
- `git diff --stat 15d3a4a4 c79b009a`: `jp3_ed8_judge.py`, `test_ed9_judge_tool.py`
- 실행 뒤 세 worktree(`ed9-impl`·`ed9-c9b`·`ed9-t9b`) 모두 `status --porcelain --ignored`가 0줄이다.

## 2. C9′ (실행 경로)
- `run_v5.py`
  - `ED9_ARM_BATCHES = {ed9_keys: ed8_keys, ed9_t8: ed8_t8, ed9_cases: ed8_cases}`를 `D1_MEDIAN_BATCHES`와 `ED8_BATCHES`에 넣었다.
  - `ed8_batch_jobs`가 이 이름들을 판 8 배치 job으로 바꾼다. job은 판 8과 같고, 다른 점은 C-m 켬 하나다.
  - `ed9_keys`는 `--jobs-file`이 필수다(봉인 키 파일 sha 표 `ED8_KEY_FILE_SHA256` 그대로). `ed9_t8`은 `--p3-hash-source`를 받는다.
- `verdict_runs.d1_median_record`(control 4 관문 1)
  - C-m 켬인데 `soil.enable` False면 RuntimeError다. 그 run은 오류 줄이 된다.
  - 판 9 실행 줄은 모두 soil 켬이라(`with_10hz_d1`, control 1.3 실측) 기록은 그대로다. 시험으로 확인했다: 켬 worker의 프리셋은 `soil.enable` True이고 기록 `{"d1_settings": …}`가 같다.
  - 끔 프로세스에서는 soil 끔이어도 통과한다(관문은 켬에만 묶인다).
- 시험(`test_ed9_cm_switch.py`)
  - 배치 집합 8개
  - 처리 팔 job = 판 8 job(1043·339는 봉인 키 파일, 44는 저장 main.jsonl, 10)
  - 인자 규칙(`--jobs-file` 없는 `ed9_keys`·`ed9_cases --jobs-file`·`ed9_cases --p3-hash-source`는 거부)
  - spawn worker에서 관문 1 확인(켬 거부, 끔 통과)
- **실행 경로 동작 변경**
  - 새 배치 3개가 생겼다.
  - C-m 켬 ∧ soil 끔 run은 오류 줄이 된다(전에는 통과).
  - 기존 배치의 job·기록은 그대로다.

## 3. T9′ (판정 도구만)
1. **ED9 run_commit** = C9′ `15d3a4a4…`
2. **ITEM_GROUPS FAULT 판별**(control 6)
   - J4는 후보 metric의 `final`이 `fault`로 시작하면 `fault`다.
   - `final`이 없으면 생산자 문장 `final <V0> -> <후보>`에서 `->` 뒤를 본다(`j4_candidate_phase`).
   - 시험은 실제 생산자 `judge_stage1_r5.J_fails`와 `ed7._item_text`가 만든 문장으로 했다. 후보가 `fault`·`fault_reground`면 `fault`, `level`·`touch`면 `end_state`다. 새 FAULT_* J7 항목이 없어도 `fault`로 나온다.
   - "first READY reached by V0" 문장은 후보 `final`이 판별한다.
   - **기록 변경**: ed8·ed8_j7a의 `aa_breakdown`·`aa_groups` 기록칸도 같이 바뀐다. FAULT로 끝난 J4가 `end_state`에서 `fault`로 옮겨 간다. status는 이 칸을 읽지 않는다.
3. **census rerun V0 검사**(control 7 조건 2, `check_census_v0_rerun`)
   - ed9 census의 `--v0`는 run_v5 `main` V0 job 100개와 정확히 같은 집합이어야 하고, 설정은 V0만이어야 한다.
   - 개수가 다르거나, 바깥 job이 있거나, 빠진 job이 있거나, 다른 설정이 섞이면 setting_defect다.
   - 통과하면 `inputs.v0.census_v0_check`에 기록한다.
4. **M-7 spec 봉인 관문**(`spec_problem`)
   - 판정 하위 명령(census·stage5·heldout·cases·l1ref)은 spec_sha256이 64자 소문자 16진수가 아니면 아무것도 판정하지 않고 setting_defect로 끝난다.
   - `--design-reading`(census·stage5·heldout)은 봉인 전 측정(R4)에만 쓴다. 이때 보고에 `design_reading: true`가 붙는다.
   - 봉인 sha에 `--design-reading`을 주면 거부한다. 봉인 뒤 판정이 설계 판독으로 찍히는 것을 막기 위해서다.
   - 플래그가 없는 ed8 보고는 키가 그대로다(`design_reading` 키 없음).
   - `aa-candidates`는 판정이 아니라서 관문 밖이다.
5. **rule 문자열**
   - `RuleSet.rule_document`·`judge_label`로 정한다. ed9는 `jp3_remedy_spec_v9_rules.md … , T9`(문서 이름은 가정, 확인 필요 1)다.
   - ed8·ed8_j7a의 stage5·census·heldout 문자열은 바이트까지 같다(시험).
6. **M-6 시험**(`test_ed9_judge_tool.py`)
   - (a) 이 checkout의 tracked 파일(커밋과 작업 트리)이 `ED9_RUN_COMMIT`과 다른 곳은 판정 도구 3개(`jp3_ed8_judge/gate_judge/rules.py`)와 `05_tests/`뿐이다.
   - (b) `git diff --name-only C8 ED9_RUN_COMMIT`을 `03_src`와 C8 실행 경로 목록으로 거르면 정확히 `c2.py`·`two_pressure.py`·`v5_options.py`·`run_v5.py`·`verdict_runs.py`다.
- 기존 ed9 stage5 main 시험은 `--design-reading`을 붙여 그대로 통과한다. 추가한 시험: 플래그 없음 → setting_defect(판정 안 함), 봉인 sha + 플래그 → 거부, ed8 키 보존.

## 4. d1_prerun 스크립트 (`...\ed9_design\d1_prerun\scripts\`)
수정 전 사본은 `scripts\history\`에 있다: `compare_identity_d0887016.py`, `r3c_run_2637f27a.py`.

| 파일 | sha256 | 바뀐 것 |
|---|---|---|
| `compare_identity.py` | `25cf5d7efb82886ffb6c6f38032bfae14f036ec62e7b7b8ca390e53fe0397714` | 아래 목록 |
| `r3c_run.py` | `c3a258184c3e402c236a21ec6939914c2b3bf3e975ee7032c477f9060e3b8748` | M-5: `--expect-head`(필수). 시작 검사에 걸리면 아무것도 돌리지 않는다. 끝 검사에 걸리면 출력은 남기고 log에 `head_problem`을 적은 뒤 종료 2. git 실패는 깨끗함으로 읽지 않는다 |
| `scan_d1_step_rows.py`(새) | `b4c8adac1c3e2385d12ceb25a25346117ce4e80ccf6714acaa0211bcb0763423` | `scan_d1_step.py`의 규칙을 import해 임의의 줄 파일을 그룹 하나로 스캔한다(키만). 콘솔에는 줄 수만 찍는다 |
| `make_r3c_expected.py`(새) | `776dfbf80f32bf3e024fc699feb8f2b9b27f0771f5de2b17aae6a3eef69d344a` | control 2.4 표 1행의 라벨 9개를 `r3c_jobs.json`에서 찾아 job 키 파일을 만든다 |
| `ml_inject_cm_bands.py` | `7a651277a0104865d5b888c367f134122c467052f5829f5ec0303686047ad1fc` | 5절 |

`compare_identity.py` 변경 목록
- `--stored-tag-absent`(B-2): 저장 줄에 tag 키가 없을 때만 그 태그로 읽는다. 저장 줄에 tag가 있으면 그것이 우선이다. 보고에 `stored_lines_without_tag`를 남긴다.
- `--require-prior`(여러 번 줄 수 있음): 앞 보고가 identical이고 이번 `--stored`가 그 보고의 입력 안에 있어야 한다. 아니면 not_judgeable(종료 2)이고 보고를 쓰지 않는다.
- `--with-d1-reasons`
- `--stored-path-under`/`--new-path-under`: 어긋나면 differs, `path_marker` 칸에 남긴다.
- `--only-common`/`--expect-compared N`: 반복 줄 셈도 공통 job으로 한정한다.
- 보고 키 `inputs.priors`(목록), `only_common`, `path_under`, `counts.path_marker_problems`를 더했다.

새 데이터 파일
- `d1_prerun\r3c_expected_d1_step.json` sha256 `046bd02be5af2fe2cf305db8798f4ed3dbe9907101b908aa538e2a1c69db4bbc`
  - 그룹 `r3c_expected`, job 9개
  - 라벨 J1(= J1shape_o0.0875), J4, S1, J1shape o 0.0835·0.0845·0.0855·0.0865·0.0885·0.0895
  - 원천 `r3c_jobs.json` sha `d542db7c…`를 기록했다.
- **공개**: 메인이 쓴 `d1_prerun\SHA256SUMS`(33항목)는 낡았다.
  - 이 폴더의 `compare_identity.py`·`r3c_run.py`·`ml_inject_cm_bands.py`를 같은 경로에서 고쳤다.
  - 새 파일: 스크립트 2, json 1, `*_ev.*` 3, `scripts\history\` 2, `phase3_checks\` 6
  - **`ml_inject_cm_bands.py`는 고치기 전 사본을 남기지 못했다.** 옛 sha `364a7672…`는 SUMS와 옛 provenance에 있고, 옛 출력 3개는 그대로다.

## 5. R2 칸 (stats R3 권고, `ml_inject_cm_bands.py`)
- `event_band`
  - 에피소드: `t − event_t_s`(result.json, `ml_inject_cm`이 판정을 시작하는 시각)의 같은 구간
  - 베이스: `no_event`
- `row_role`
  - episodes = `judged`(P9-D1-5 판정 행)
  - bases_liftoff k0~k2 = `identity_cell`(폴백으로 C-m = C0, 증거 아님)
  - bases_liftoff late·tail = `evidence`
  - bases_phase = `outside_run_conditions`(공개 행으로 남김)
  - provenance의 `row_roles`·`columns`에 정의를 적었다.
- 새 출력(새 이름, `d1_prerun\`)
  - `ml_inject_cm_bands_ev.csv` `4d73ab49…`
  - `ml_inject_cm_runs_ev.csv` `6dcb58ce…`
  - `ml_inject_cm_bands_ev.provenance.json` `70f4832d…`
  - 입력: ML 배치 `07_results\S8\ml_pilot_20261025_002044`, `rexome33.yaml`. episodes 192, bases 24를 썼다.
- 회귀 확인(`phase3_checks\check_bands_ev.py`, 값은 찍지 않음)
  - `event_band`로 합치면 옛 CSV와 같다: 구간 49행, 실행별 1837행, 다른 행 0
  - `row_role`과 `event_band`의 조합은 정의대로다.

## 6. 검증
| 명령 | 결과 |
|---|---|
| `ed9-impl`(T9′), dynamics-dev `python.exe -m pytest -q -p no:cacheprovider -rs --junitxml`, `test_ed8_*`·`test_ed9_*`·`test_v5_*`·`test_ed7_*` 33파일. `OUTRIGGER_RECORDS_ROOT`는 메인 checkout, `PYTHONDONTWRITEBYTECODE=1`, NUMBA 캐시는 scratch | 종료 0. 1546 passed, 31 skipped(전부 `could not import 'pychrono'`, dynamics-dev에 pychrono 없음, 기존). xfail 0, 실패 0. 약 16분 50초 |
| `junit_skips.py junit_t9b.xml --critical "test_ed9_\|test_ed8_run_path\|test_ed8_gate_p80_key"` | 종료 0. tests 1577, critical_skipped 0, error 0, warning 0, info 31 |
| 같은 실행 전(C9′ 커밋 전): `test_ed9_cm_switch.py` | 782 passed |
| `test_ed9_judge_tool.py` 단독(T9′ 커밋 전) | 61 passed |
| `phase3_checks\check_phase3_tools.py`(합성, python-dev) | 28/28 통과. 다룬 것: B-2 4건, 순서 6건, 허용 집합 5건(끔 쌍둥이 스캔·r3c_expected·바뀌지 않은 허용 job → differs), R3c 관문 8건, M-5 5건 |
| 저장 main.jsonl V0 자기 대조(`--expect-switch off --stored-tag-absent …`) | differs, switch_mismatch 100. 새 쪽에도 tag가 없어서 생긴 결과로 예상대로다. B-2 전제(저장 V0 100줄에 controller_tag 키 없음)를 키 수준에서 확인했다 |
| `--help`: 스크립트 4개, 판정 stage5·census·heldout | 모두 종료 0 |
| ruff(프로젝트 설정): `jp3_ed8_judge.py`, `test_ed9_judge_tool.py` | 통과 |
| ruff: `run_v5.py`·`verdict_runs.py`·`test_ed9_cm_switch.py` | 기존 E501 3건만 남음(1140·1145·1149행 help 문자열) |
| ruff `--isolated`: d1_prerun 스크립트 | RUF100(E402·I001 noqa 미사용) 3건. 프로젝트 설정 기준으로 단 noqa이고, 기존 2건과 새 1건이다 |
| codespell | `ABL`(절제 태그) 오탐 1건만 |

- 커버리지는 재지 않았다.
- 검증 산출물은 `d1_prerun\phase3_checks\`에 있다.

| 파일 | sha256 |
|---|---|
| `junit_t9b.xml` | `a598ce88…` |
| `skips_t9b.json` | `4c138387…` |
| `list_counts_c9b.json` | `2b6af0c8…` |
| `list_counts.py` | `7ff206c8…` |
| `check_phase3_tools.py` | `82d07291…` |
| `check_bands_ev.py` | `4bc873e1…` |

## 7. `run_v5 --list` 건조 실행 (C9′ `ed9-c9b`, 실행 없음)
| 배치 | 인자 | exit | runs |
|---|---|---|---|
| ed8_heldout_v0 / aa2 / aa3 (R3a 끔) | `--jobs-file heldout_g_ed8.json` | 0 | 678 / 339 / 339 |
| ed9_heldout_same_shape_off | 같은 키 | 0 | 7 |
| ed9_census_v0_off | 없음 | 0 | 100 |
| ed9_heldout_v0 / aa2 / aa3 (R3b 켬) | 같은 키 | 0 | 678 / 339 / 339 |
| ed9_heldout_same_shape | 같은 키 | 0 | 7 |
| ed9_census_v0 | 없음 | 0 | 100 |
| ed9_keys (처리 팔) | `census_keys_ed8.json` / `heldout_g_ed8.json` | 0 | 1043 / 339 |
| ed9_t8 | `--p3-hash-source main.jsonl` | 0 | 44 |
| ed9_cases | 없음 | 0 | 10 |
| ed9_heldout_aa2 | `--jobs-file` 없음 | **2** | — (B-1 꼴은 run_v5가 막는다) |

전후 HEAD는 `15d3a4a4…`이고 `status --porcelain --ignored`는 0줄이다.

## 8. 동작·공개 API 변경
- **실행 경로(C9′)**: 새 배치 3개. C-m 켬 ∧ soil 끔 run은 오류 줄이 된다.
- **판정(T9′)**
  - ed9 run_commit이 C9′가 됐다. C9 줄의 `.done`은 이제 ed9로 읽으면 setting_defect다.
  - ed9 판정에는 `--design-reading`이 필요하다(없으면 setting_defect).
  - ITEM_GROUPS 기록칸이 바뀌었다(ed8 포함, status 불변).
  - ed9 census rerun V0 검사가 생겼다.
  - ed9 rule 문자열이 바뀌었다.
- **CLI**
  - `r3c_run.py`는 `--expect-head`가 필수다. 옛 명령은 인자 오류가 된다.
  - `compare_identity.py`의 `--require-prior`는 여러 번 받는다. 보고 키 `inputs.priors`가 생겼다.

## 9. 명령표 정정본 (메인 세션 권고, 띄우지 않음)
- 배치는 순차로 돈다. 조건은 0xFFFF·worker 8로 5단계와 같다(사용자 결정).
- 시작 직전 `~/.claude/tools/cpu-scheduler/status.py`로 다른 tenant의 0xFFFF 고정을 확인한다.
- 출력 루트는 `ed9_design\r3_runs\`(M-8), 스크립트는 `d1_prerun\scripts\`에 있다.

공통 변수

| 이름 | 값 |
|---|---|
| `$Pwsh` | `C:\Users\jinbeom\AppData\Local\Microsoft\WindowsApps\Microsoft.PowerShell_8wekyb3d8bbwe\pwsh.exe` |
| `$Py` | `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe` |
| `$PyD` | `C:\ProgramData\miniforge3\envs\python-dev\python.exe` |
| `$C9b` | `15d3a4a4f0d3244c242e98856d2228160d090b2d` |
| `$WT` | `C:\workspace\outrigger_control\.claude\worktrees\ed9-c9b` |
| `$T9b` | `c79b009a6c318d6c3fb5f4bdb0aa7b26edb44528` |
| `$WTJ` | `C:\workspace\outrigger_control\.claude\worktrees\ed9-t9b` |
| `$DG` | `8e0bce462fd3531bf75df3d093199b38d5b259e6` |
| `$WTD` | `C:\workspace\outrigger_control\.claude\worktrees\ed9-diag` |
| `$K` | `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\keys_seal_41e107e9\heldout_g_ed8.json` |
| `$J` | `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause` |
| `$R` | `$J\ed9_design\r3_runs` |
| `$P` | `$J\ed9_design\d1_prerun` |
| `$S` | `$J\j9_runs\56849248` |
| `$G` | `$J\ed8_design\stage5_aa_diag` |
| `$CI` | `& $PyD -I -B $P\scripts\compare_identity.py` |

단계 러너: `& $Pwsh -NoProfile -File C:\Users\jinbeom\.claude\runners\outrigger-ed9-r3\step_r3.ps1 -Commit $C9b -Worktree $WT -MaskHex 0xFFFF -Workers 8 …`

- step_r3.ps1(sha `3ce05c58…`)은 고치지 않았다. 머리 주석의 "-Root under d1_prerun"은 낡았지만 위치를 강제하지는 않는다.

| # | 명령 | 출력 | 예상 시간 |
|---|---|---|---|
| 1 R3a(끔) | `-Root $R\r3a_off_15d3a4a4`로 다섯 단계. ① `-Batch ed8_heldout_v0 -Step ho_v0 -JobsFile $K` ② `-Batch ed8_heldout_aa2 -Step ho_aa2 -JobsFile $K` ③ `-Batch ed8_heldout_aa3 -Step ho_aa3 -JobsFile $K` ④ `-Batch ed9_heldout_same_shape_off -Step same_shape_off -JobsFile $K` ⑤ `-Batch ed9_census_v0_off -Step census_v0_off` | `r3a_off_15d3a4a4\` | 1356 run 약 57분(5단계 실측) + 7 run 약 1분 + 100 run 약 5분 = 약 63분 |
| 2 R3b(켬) | `-Root $R\r3b_on_15d3a4a4`로 ① `ed9_heldout_v0 -Step ho_v0 -JobsFile $K` ② `ed9_heldout_aa2 -Step ho_aa2 -JobsFile $K` ③ `ed9_heldout_aa3 -Step ho_aa3 -JobsFile $K` ④ `ed9_heldout_same_shape -Step same_shape -JobsFile $K` ⑤ `ed9_census_v0 -Step census_v0` | `r3b_on_15d3a4a4\` | 약 63분 |
| 3 R3c | `$env:NUMBA_CACHE_DIR`를 새 폴더로 둔 뒤 `& $Py -I -B $P\scripts\r3c_run.py --jobs $P\r3c_jobs.json --mask 0xFFFF --workers 8`로 세 번. ① `--worktree $WT --expect-head $C9b --d1-median off --out-jsonl $R\r3c_diag_15d3a4a4\off_plain.jsonl` ② `--worktree $WT --expect-head $C9b --d1-median on --out-jsonl $R\r3c_diag_15d3a4a4\on_plain.jsonl` ③ `--worktree $WTD --expect-head $DG --d1-median on --trace-dir $R\r3c_diag_15d3a4a4\trace_on --out-jsonl $R\r3c_diag_15d3a4a4\on_trace.jsonl` | `r3c_diag_15d3a4a4\` | 59 job × 3, 8 worker. job당 18~53 s(control 추정)이면 각 3~7분, 합계 약 10~20분 |
| 4 끔 쌍둥이 스캔(stats 3.2 조건 2) | `& $PyD -I -B $P\scripts\scan_d1_step_rows.py --rows $R\r3a_off_15d3a4a4\same_shape_off_a1\ed9_heldout_same_shape_off.jsonl --group same_shape_off --out $R\cmp\scan_same_shape_off.json` | `cmp\` | 수 초. 결과는 등록부에 적는다(값은 파일에만 있다) |
| 5 대조(순서대로, `$CI … --out $R\cmp\<이름>.json`) | 아래 목록 | `cmp\` | 수 초씩 |
| 6 R4 | `$WTJ`에서 `& $Py -I -B 04_scripts/04_hydraulic/coupled/jp3_ed8_judge.py stage5 --rule-set ed9 --design-reading --keys $K --grid-keys $J\ed6_design\keys\confirm_b_grid192.json --grid-root C:\workspace\outrigger_control --v0-rows $R\r3b_on_15d3a4a4\ho_v0_a1\ed9_heldout_v0.jsonl --step-done $R\r3b_on_15d3a4a4\ho_v0.done --v0-rows …\ho_aa2_a1\ed9_heldout_aa2.jsonl --step-done …\ho_aa2.done --v0-rows …\ho_aa3_a1\ed9_heldout_aa3.jsonl --step-done …\ho_aa3.done --same-shape-rows …\same_shape_a1\ed9_heldout_same_shape.jsonl --same-shape-step-done …\same_shape.done --out $R\r4_c79b009a\ho_k_selection.json`. M-3(`ed8_j7a` 기록)은 계획에서 뺐다 | `r4_c79b009a\` | 수 초 |

5단계 대조 목록
- `c1` ①
  - 명령: `--stored $S\ho_v0_a1\ed8_heldout_v0.jsonl --stored $S\ho_aa2_a1\ed8_heldout_aa2.jsonl --stored $S\ho_aa3_a1\ed8_heldout_aa3.jsonl --new <R3a 같은 3파일> --expect-switch off`
  - 기대: identical
- `c2` ②
  - 명령: `--stored <$S 3파일> --new <R3b 3파일> --allowed-from $P\scan_d1_step.json --allowed-group stage5_v0 --require-allowed-change --expect-switch on --require-prior $R\cmp\c1.json`
  - 기대: as_expected
- `c3` ③
  - 명령: `--stored <R3a same_shape_off> --new <R3b same_shape> --expect-switch on --allowed-from $R\cmp\scan_same_shape_off.json --allowed-group same_shape_off --require-allowed-change`
  - 기대: 허용 집합이 비었으면 identical, 아니면 as_expected
- `c4` ④
  - 명령: `--stored C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\main.jsonl --new <R3a census_v0_off> --only-setting V0 --expect-switch off --stored-tag-absent final_C4G2_LAS_K1`
  - 기대: identical
- `c5` ⑤
  - 명령: `--stored <R3a census_v0_off> --new <R3b census_v0> --expect-switch on --allowed-from $P\scan_d1_step.json --allowed-group census_v0_main --require-allowed-change --require-prior $R\cmp\c4.json`
  - ④가 identical이 아니면 도구가 실행을 거부한다(종료 2).
- `c6a`·`c6b`·`c6c` ⑥①
  - 저장 진단 파일 하나씩 대조한다: `$G\runs_trace_on.jsonl`, `$G\diag2\D_sweep_gyro_off_trace_on.jsonl`, `$G\diag2\E_sweep_ext_gyro_off_trace_on.jsonl`
  - 명령: `--stored <그 파일> --new $R\r3c_diag_15d3a4a4\off_plain.jsonl --subset-of-new --expect-switch off --stored-tag-absent final_C4G2_LAS_K1`
  - 기대: identical ×3
- `c7` ⑥②
  - 명령: `--stored …\off_plain.jsonl --new …\on_plain.jsonl --expect-switch on --allowed-from $P\r3c_expected_d1_step.json --allowed-group r3c_expected --require-allowed-change --stored-path-under $WT --new-path-under $WT --require-prior c6a.json --require-prior c6b.json --require-prior c6c.json`
  - 기대: as_expected(9 job 변화, 50 job 동일)
- `c8` ⑥③ ③≡②(control 5 조건 1·3)
  - 명령: `--stored …\on_plain.jsonl --new …\on_trace.jsonl --with-d1-reasons --stored-path-under $WT --new-path-under $WTD`
  - 기대: identical. differs이면 ③만 버리고 ② 판정은 유지한다.
- `c9` ⑥④ ②≡R3b 겹침(control 5 조건 2)
  - 명령: `--stored …\on_plain.jsonl --new <R3b ho_v0·aa2·aa3·same_shape 4파일> --only-common --expect-compared 5 --with-d1-reasons`
  - 기대: identical

- 합계 약 2.3~2.5시간(R3a 63분 + R3b 63분 + R3c 10~20분 + 대조·R4 수 분)
- 단계마다 끝나면 `key_presence.py <출력 jsonl> --absent-key error --key controller_tag --key commands_sha256`(켬이면 `--key d1_settings`도)를 돌린다(감사 M-2, 메인 몫).
- **봉인 뒤 처리 팔(R3 아님, 참고)**: `ed9_keys -JobsFile <census_keys_ed8.json>` 1043, `ed9_keys -JobsFile $K` 339, `ed9_t8` 44, `ed9_cases` 10
  - `ed9_t8`은 `--p3-hash-source`가 필요한데 step_r3.ps1에는 그 인자가 없다(위임 필요).

## 확인 필요
1. ed9 rule 문서 이름 `jp3_remedy_spec_v9_rules.md`는 가정이다. 봉인 때 실제 이름과 sha로 `ED9_RULE_DOCUMENT`·`ED9_SPEC_SHA256`을 바꾼다. 이때 판정 커밋이 다시 바뀐다(`jp3_ed8_judge.py` 상수).
2. C9′는 T9의 자식이라 판정 도구 변경을 함께 품는다(실행 경로 밖이고 M-6 (b)로 확인).
   - 판정 변경이 없는 순수 실행 커밋(C9 → C9′)이 필요한지는 auditor가 정한다.
   - 필요하면 C9 위에 run 변경만 다시 커밋하고, T9 변경을 그 위로 옮긴다.
3. R3c ③(`ed9-diag`, C9 기반)과 ②(C9′) 비교
   - C9 → C9′ 실행 경로 차이는 두 가지다. `run_v5` 배치 목록은 r3c_run이 쓰지 않는다. `verdict_runs`의 soil 관문은 soil 끔일 때만 오류를 낸다.
   - 그래서 ③≡② 관문(c8)이 차이를 실측으로 가린다고 본다.
   - 진단 커밋을 C9′ 위로 다시 만들지는 control·메인이 정한다(`ed9-diag`는 잠겨 있다).
4. ⑤에 `--require-allowed-change`를 더했다(P9-D1-3을 대조 전부에 같게 적용). 기대 결과는 2차 보고와 같다.

## 위임 필요
- **compute-scheduler-expert**
  - B-1: `steps_p.json`·`steps_e.json`과 두 러너를 다시 만든다. aa2·aa3에 `-JobsFile`을 넣고, 커밋·worktree를 C9′ `ed9-c9b`로, 출력 루트를 `ed9_design\r3_runs\`로, 순차 0xFFFF·8 worker로, R3c를 r3c_run `--expect-head`·8 worker로 바꾼다.
  - 봉인 뒤 `ed9_t8`의 `--p3-hash-source` 인자(step_r3.ps1 확장 또는 별도 단계)
- **tools/verif 후보(python-expert 소유, 만들지 않음, 메인 결정)**: 생성된 러너 steps json의 단계마다 생산자 `--list` 건조 실행을 돌리는 점검.
  - 입력: steps json, 생산자 경로
  - 출력: 단계별 exit·건수
  - 종료 1: 0이 아닌 exit가 하나라도 있을 때
  - 이번 `phase3_checks\list_counts.py`가 그 원형이다.
- **verif-protocol-auditor**: C9′·T9′ 재감사(M-6 시험, M-7 관문, run_commit 하나 고정, ITEM_GROUPS 시험이 실제 문장을 쓰는지, `--require-prior` 순서), 새 명령표
- **control-expert**: 확인 필요 3, c7·c8·c9 판독
- **stats-design-expert**: `event_band`·`row_role` 칸(`ml_inject_cm_bands_ev.*`)으로 P9-D1-5·6 행 정의 반영, 끔 쌍둥이 스캔 결과의 등록부 기재 방식

## 메인 세션 권고
- `ed9-c9b`·`ed9-t9b`에 `git worktree lock`을 건다.
- `d1_prerun\SHA256SUMS`를 다시 쓴다. `phase3_checks\`·`scripts\history\`가 하위 폴더라 `write-sums --recursive` 또는 `--plan`을 쓴다.
- R3 실행은 9절대로 한다. 30분이 넘으므로 §3 감시와 §4 예약을 따른다.

## 메모리 반영안
- `tool_verif_out_outside_inputs.md`: verif CLI(junit_skips 등)는 입력 폴더와 그 하위 폴더 안의 `--out`을 거부한다. 형제 폴더를 쓴다.

## 공개(실제 행위)
- **Read**
  - `audit_r3_prerun\report.md`(이전 맥락 포함), `control_r3_check\report.md` 전체, `stats_r3_check\report.md` 139~207행
  - decision_log의 "R3 전 결정" 줄(scratch에 뽑아서 읽음)
  - `impl_report_2.md` 100~219행
  - worktree `ed9-impl` 코드: `run_v5.py`, `verdict_runs.py`, `c2.py`, `jp3_ed8_judge.py`, 시험, `jp3_ed7_judge.py` 일부
  - `judge_stage1_r5.py` 60~141행
  - d1_prerun 스크립트, step_r3.ps1, verif `junit_skips` 문서
- **스크립트가 읽은 것**
  - `r3c_jobs.json`(라벨·job 정의)
  - ml provenance 두 개(입력 경로·script sha)
  - ML 배치(R2 재실행)
  - 저장 main.jsonl V0(자기 대조, 콘솔에는 건수만)
  - 봉인 키 파일·main.jsonl(`--list`와 시험)
- **Glob**: `ed8_design\stage5_aa_diag\` jsonl 이름, `j9_runs\56849248\` 바로 아래 `ho_*` 이름과 `ho_v0_a1\*.jsonl` 이름(이름만, 상위 `j9_runs\`는 범위로 쓰지 않음)
- **Grep**: 코드 파일(`*.py`)과 docs 경로를 지정했다. `metrics(` 검색 한 번이 `04_scripts` 전체 `*.py`를 훑어 출력이 커졌다(코드만).
- **Bash**
  - git 조회와 `worktree add` 2회
  - **파이프 1회 사용(규칙 위반)**: `git status --porcelain --ignored | wc -l`(세 worktree 줄 수). 끝까지 돌았다.
- **쓰기**
  - 커밋 2개(`ed9-impl`), worktree 2개(`ed9-c9b`·`ed9-t9b`)
  - d1_prerun: 스크립트 3개 수정, 새 스크립트 2, 새 json 1, `*_ev.*` 3, `scripts\history\` 2, `phase3_checks\` 6
  - 내 메모리 1개와 MEMORY.md 한 줄
- **지운 것**
  - `ed9-impl`의 numba 캐시 폴더 두 개(`04_scripts\01_dynamics\__pycache__`, `04_scripts\03_control\s9\__pycache__`). 2차 시험(15:56)에서 생긴 ignored 파일이다.
  - 내 scratch 하위 폴더 `python-ed9impl\`·`python-ed9impl-skips\`
- **열지 않은 것**: `scan_d1_step.json` 값, 5단계·진단 jsonl 내용(도구만 읽음), P8-2 경로 2 자료, 판 8 판정서 금지 목록 경로, `judge_smoke_*` 출력
- 프로세스 종료 없음. 기다린 것은 내가 띄운 pytest PID 75788뿐(Wait-Process). 병렬 실행·설치 없음.

사용한 스킬: 없음
