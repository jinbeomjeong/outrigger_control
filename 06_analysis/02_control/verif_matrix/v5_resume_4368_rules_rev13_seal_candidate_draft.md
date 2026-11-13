# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev13 (원판 A-5 앵커 확인: `c6bb55b`..`a861981` 코드 변경의 P-1·P-2 비트 영향, 앵커 유지, H-0과 본 묶음의 `git_at_start`, 경로 2 K-0 수정을 담은 커밋 R에서 G-S 전체, 결과 전, 봉인 후보 초안)

- **상태: 봉인 후보 초안(봉인 전).** 봉인 전에는 실행·판정에 쓰지 않는다. 봉인 때 바꿀 머리 줄은 끝 절에 원문으로 적었다.
- 원판 `v5_resume_4368_rules.md`(sha256 `9019b405…`), rev1(`d9094fda…`), rev2(`497e4614…`), rev3(`dad8dfa6…`), rev4(`7ea87a30…`), rev5(`452a8436…`), rev6(`809e5639…`), rev7(`e81f7d31…`), rev8(`3ecafaaf…`), rev9(`4cf7843c…`), rev10(`62a0bd8d…`), rev11(`9bac4524…`), rev12(`78f1f99b…`)는 고치지 않는다. 이 판은 rev12(sha256 `78f1f99b1bb27473d6e3317c58af195cc3b477829ca1439f390aeeaf32565140`, 봉인 커밋 `61f066f`) 위에 쌓인다. 전체 sha256은 각 판의 `.sha256`에 있다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다.
- **시점: 436.8 본 묶음(H-1~H-10, Chrono C-1~C-8과 probe) 결과가 없을 때(봉인 SEAL_TIME, 봉인 커밋 SEAL_COMMIT).** 0단계 H-0(T-3K)은 사용자 결정(2026-11-13)으로 `a861981`에서 먼저 돌고 있다. 이 판의 작성자는 H-0 출력을 보지 않았고, 메인 세션은 H-0 출력 폴더의 파일 이름 목록만 한 번 보았다(R13-0).
- 작성: control-expert, 2026-11-13. 기준 `a861981`(rev12 R12-6의 앞 최종 Y). 계기: 본 실행 전 감사가 차단 2건을 냈다.
  - 원판 3절 A-5: "`git_at_start`에서 `03_src`·`02_params`·하네스 경로가 `c6bb55b`와 다르면(1.2의 Chrono 전용 1건 제외) 10절 P-1·P-2 비트 예측의 앵커를 실행 전에 다시 정하는 개정을 봉인한다". `c6bb55b`..`a861981`에서 1.2의 예외(`b1_grid_record.py`) 밖의 파일이 바뀌었고, rev1~rev12 어디에도 이 개정이 없다.
  - A-5 첫 문장 "모든 묶음이 같은 `git_at_start`"와, H-0을 `a861981`에서 먼저 돌리고 그 뒤 커밋 R에서 본 묶음을 돌리는 순서가 맞지 않는다. 같은 시기에 경로 2 `p2_t3k`의 K-0 사이드카 읽기 수정(`2d4b390`)이 R에 들어가기로 정해졌다.
- **봉인 준비판이다.** 사용자 결정이 필요한 새 항목은 없다(R13-9 결정 표). 사용자 결정(2026-11-13: rev13으로 처리, H-0은 A-5 대상 아님·먼저 시작, 범위 38개, 허용 목록에 문서 셋, R에 경로 2 수정을 넣고 R에서 G-S 전체, 도구 봉인 목록은 rev12까지)은 R13-1~R13-7에 반영했다. 이 줄은 봉인 때 바뀐다.
- **바꾸지 않는 것**: 숫자 문턱, 등급과 우선순위, 멈춤 조건의 뜻, 묶음 범위와 행 목록, 사전 예측 값(P-1~P-15), P-1·P-2 앵커 파일·sha256·줄 대응(rev1 RV1-5), 두 경로 요건(원판 9.2), K-0 조건(rev6 R6-C2), rev1~rev12의 정의(R13-4·R13-5가 고쳐 쓰는 원판 A-5 첫 문장·원판 0절 1항의 "한 커밋"·rev12 R12-6의 최종 Y와 `git_at_start` 문장만 예외). 이 판은 새 숫자를 쓰지 않는다.

## R13-0. 결과 전 근거와 공개

- 2026-11-13 확인: 436.8 본 묶음 출력이 없다. H-0은 `a861981`에서 돌고 있다.
- 이 판의 작성자는 H-0 출력, G-S 출력의 값, 436.8의 어떤 결과 파일도 열지 않았다. G-S는 폴더 이름(`gs_harness_a861981`, `gs_chrono_a861981`)만 보았다. 경로 2 수정 `2d4b390`은 바뀐 파일 이름·줄 수·blob sha256과 커밋 메시지만 보았고, 코드는 열지 않았다.
- **메인 세션 공개(2026-11-13)**: H-0 실행 중 메인 세션은 H-0 출력 폴더의 파일 이름 목록만 한 번 보았다(`ls`, 17:5x). 파일 내용은 열지 않았다. 이 판의 어떤 정의도 그 목록에 기대지 않는다.
- 판단 근거는 코드 diff뿐이다: `git diff c6bb55b..a861981 -- 03_src 02_params 04_scripts`, `git show a861981:<파일>`, 정적 import 닫힘(R13-1). 실행한 것은 diff 조회와 import 문 정적 분석뿐이다. 시뮬레이션·판정 도구는 돌리지 않았다.
- 읽은 규칙: 원판 0절·1.2·3절 A-5·6절·8.2·9.2·10절·11.2, rev1 RV1-5·RV1-9, rev4 R4-C4, rev6 R6-C2, rev8 R8-4, rev11 R11-4·R11-7, rev12 R12-2·R12-3·R12-6.
- 이 작성자는 경로 2 작성자가 아니다(rev2 R2-0).
- 이 판이 봉인(sha256 확정)되기 전에 H-0 출력의 내용을 연 사람이 있으면, 판정서에 누가 무엇을 언제 열었는지 적는다.

## R13-1. A-5 확인 범위 ("하네스 경로"의 뜻, 사용자 결정: 38개)

- 원판 1.2는 "하네스 경로"의 범위를 적지 않았다. 이 판은 다음 합집합으로 정한다.
  1. `04_scripts/04_hydraulic`, `04_scripts/03_control`(436.8 하네스 러너와 판정 도구가 있는 곳).
  2. H-1 러너 `04_scripts/04_hydraulic/coupled/run_v5.py`의 정적 import 닫힘(함수 안 import까지 모두 따라간 과대 추정, `a861981` 기준 149개 모듈 파일). 여기서 1 밖의 변경 파일이 셋 나온다.
     - `04_scripts/01_dynamics/run_mast_flex_c2_check.py`, `04_scripts/01_dynamics/run_s6_slope_boundary_check.py`: 하네스 플랜트 `FlexPlant`·`KPlant`. `c2py_r8d1_closed_loop.py` → `r8d1_td2` 경로로 들어온다.
     - `04_scripts/02_chrono/run_S9.py`: `s9/late_loc_rule.py`의 `_run_s9()`가 판정 함수 `p32_late_loc_block`·`crawler_departure`·`recontact_events`를 빌려 쓴다.
- P-1·P-2는 H-1 줄의 `commands_sha256`(10 Hz 명령 배열의 해시, rev1 RV1-5)만 예측한다. 그래서 판단 기준은 "그 파일의 변경이 H-1 줄의 10 Hz 명령 배열을 바꿀 수 있는가"이다. 판정 값·기록 블록·정체성 기록의 변화는 P-1·P-2와 관계가 없다. 그것은 각 묶음의 원 규칙과 G-S가 다룬다.
- `c6bb55b`..`a861981` 변경 수: `03_src` 2(`b1_grid_record.py` 추가, `hostcpu.py` 수정), `02_params` 0, 하네스 경로 38(`04_scripts/03_control` 13, `04_scripts/04_hydraulic` 23, `04_scripts/01_dynamics` 2). `04_scripts/02_chrono`의 변경 17개(`git diff --no-renames --name-status c6bb55b..a861981 -- 04_scripts/02_chrono`)는 Chrono 행 생성·실행·판정 도구이고 P-1·P-2 앵커가 없으므로 A-5 대상이 아니다. `run_S9.py`만 위 2의 판정 함수로 R13-2에 적는다.
- 변경이 없는 것(같은 diff에 없음): `03_src/outrigger_sim/control/c2.py`를 포함한 `03_src` 나머지, `02_params/rexome33.yaml`, `d1_rows.py`(H-1 작업 목록과 `run_v5.job_key` 대응), `harness_flow.py`, `harness_hydraulics.py`, `run_control_comparison.py`, `s9_soil_closed_loop.py`, `c2py_r8d1_closed_loop.py`, `r8d1_td*.py`, `d8x_record.py`.

## R13-2. 파일별 영향 판단 (코드 diff 근거, 결과 데이터 안 봄)

분류:
- **기록**: 실행이 끝난 뒤 제어기·플랜트·결과를 읽어 결과 사전에 키를 더할 뿐이다.
- **기본값 옛 산술**: 새 선택 인자다. H-1이 그 인자를 주지 않으면 `c6bb55b`와 같은 연산을 같은 순서로 한다.
- **경로 밖**: H-1 러너의 정적 import 닫힘에 없다. H-1 명령에 닿을 수 없다.

| # | 파일 | 변경 | H-1 닫힘 | 판단 | 근거(diff) |
|---|---|---|---|---|---|
| 1 | `03_src/outrigger_sim/chrono/b1_grid_record.py` | 추가 | 과대 추정에만(`run_S9` 경유) | 영향 없음 | 원판 1.2 예외. `run_S9.py`가 `--b1-grid-record`를 받을 때만 import(6268~6271행) |
| 2 | `03_src/outrigger_sim/hostcpu.py` | +107 (`e237e97`) | 과대 추정에만 | 영향 없음(배치 전용) | `MASK_ENV`(`OUTRIGGER_PCORE_MASK`·`OUTRIGGER_ECORE_MASK`)가 없으면 `place_process`는 옛 마스크·옛 기록 그대로다. 바뀌는 것은 affinity뿐이고, 하네스 결과는 스레드·affinity와 무관하다(원판 6절 스레드 행). `loc_anchor_shadow` import 없음(rev1 RV1-9) |
| 3 | `04_scripts/04_hydraulic/coupled/run_v5.py` | +112/−23 | 러너 | 영향 없음 | `--out`(출력·identity 사이드카·T4h 폴더 경로), `--settings`·`--one-per-setting`(H-1 명령에 없음, `resume_k1_steps.run_v5_step`), `--overlap-reference`·`RUN_V5_OVERLAP_REFERENCE`(overlap 묶음만), `mass_scale` 전달(작업에 키가 없으면 1.0), 줄에 `resume_k1` 키 복사(기록). `job_key`와 `run_one`의 실행 경로는 그대로 |
| 4 | `.../coupled/d1_runs.py` | +41/−5 | 예 | 영향 없음 | `mass_scale` 기본 1.0. 변경 없는 `d1_rows.py`의 작업에는 `mass_scale` 키가 없다. 1.0이면 `SlopeCase(mass_scale=1.0)`은 필드 기본값과 같고, `s9_soil_slope`는 1.0이 아닐 때만 키·`case_id`를 바꾼다(360·566행). `demoted_items`·`g6_preloc`는 기록이고, `resume_k1` 블록은 `k1` 작업(D8x)에만 붙는다 |
| 5 | `.../coupled/verdict_runs.py` | +72/−6 | 예 | 영향 없음(기록) | `_finish`가 `commands_sha256`을 만든 뒤 `t_check_start_s`·`sa4`·`resume_k1`·`case_floor_deg`를 더한다. `plant_options_record(config=None)`은 옛 동작 |
| 6 | `.../coupled/verdict_metrics.py` | +14/−2 | 예 | 영향 없음(기록) | `saturation_rule` 문자열 키만 더함 |
| 7 | `.../coupled/resume_k1_record.py` | 추가 | 예 | 영향 없음(기록) | 실행 뒤 `controller.meta()`·`events`·`config`를 읽어 사전을 만든다. 명령을 만든 뒤에 불리고, 작업마다 새 spawn 작업자(`maxtasksperchild=1`)다 |
| 8 | `.../coupled/v5_rerun.py` | +13 | 예 | 영향 없음 | 태그 상수·`las_k1` 폴더 상수, `run_record`에 `resume_k1` 기록 |
| 9 | `.../coupled/u3_reuse.py` | +10/−8 | 예 | 영향 없음 | H-3 재사용 Q-6의 기대 태그·입력 이름만 |
| 10 | `04_scripts/03_control/s8/r67_g1_screen.py` | +26/−5 | 예(이벤트 경로) | 영향 없음(기록) | `v5_job_record`·`v5_branch_record`는 분기 실행이 끝나고 `commands_sha256`을 만든 뒤 `resume_k1` 블록과 태그용 `config`를 더한다. 다음 분기는 원본의 `deepcopy`에서 시작한다 |
| 11 | `04_scripts/03_control/s9/s9_soil_slope.py` | +14/−1 | 예 | 영향 없음(기록) | `run_one` 끝에서 `settle_v2`를 기록한다(결과만 읽음) |
| 12 | `.../s9/s9_settle_rejudge.py` | +85 | 예 | 영향 없음(기록) | `settle_v2_record`는 결과 사전과 침하 표만 읽음 |
| 13 | `.../s9/s9_slope_fix_candidates.py` | +3/−1 | 예 | 영향 없음(기록) | `slope_record_fields`에 `settle_v2` 복사 |
| 14 | `04_scripts/01_dynamics/run_mast_flex_c2_check.py` | +233/−4 (`57ea622`) | 예(플랜트) | 영향 없음(기본값 옛 산술) | `physics_flex`에 `lockm` 등 인자를 더했다. `lockm` = 0(`_init_lock_state` 기본)이면 새 분기 셋(`P + frod`, `_update_rod_lock`·`_solve_leg_l1r`, `Pn + frod`)을 모두 건너뛰고 `elif fmode == 0` 이하 옛 식을 같은 순서로 계산한다. `@nb.njit(cache=True)`(fastmath 없음)라 부동소수 연산 순서가 그대로 남는다. `pressure()`도 `lockm` = 0이면 옛 값 |
| 15 | `04_scripts/01_dynamics/run_s6_slope_boundary_check.py` | +39 (`57ea622`) | 예(플랜트) | 영향 없음(기본값 옛 산술) | `case["rcfg"]`에 `lock_stiffness` 키가 없으면 `set_lock_stiffness`를 부르지 않는다(`lockm` 0 유지). 그 키를 넣는 곳은 `acc_d8.py`(D8x, env `ACC_D8X_LOCK_STIFFNESS`)뿐이고 `d1_rows.py`에는 없다 |
| 16 | `04_scripts/02_chrono/run_S9.py` | +298/−7 | 과대 추정(`late_loc_rule` 경유) | 영향 없음 | 하네스가 쓰는 판정 함수 `p32_late_loc_block`·`crawler_departure`·`recontact_events`의 본문은 그대로다. 판정 함수라 명령과 무관 |
| 17 | `.../coupled/resume_k1_steps.py` | 추가 | 단계 생성 | 영향 없음 | H-1 명령 = `run_v5.py d1 --workers W --mask M --out resume_k1/h1_d1.jsonl`. 작업자 수·마스크는 명령 비트와 무관하다(작업마다 spawn, 스레드 변수 1). 단계 `env`의 금지 env는 실행 전 감사가 본다(원판 11.1, rev1 RV1-9) |
| 18 | `04_scripts/03_control/s8/r79_L3L4_final.py` | +67/−1 | 경로 밖(H-8 러너) | P-1·P-2 무관 | `--keys-file`(rev1 RV1-3.2), 메타 기록 |
| 19 | `.../s8/r79_sensor_screen.py` | +47/−1 | 경로 밖(H-8) | P-1·P-2 무관 | `resume_k1`·`commands_sha256` 기록, 기록용 로그 설치(rev3 R3-E4). H-8에는 P-1·P-2 앵커가 없다 |
| 20 | `.../touch_phase/acceptance/acc_d8.py` | +38/−5 | 경로 밖 | P-1·P-2 무관 | `--lock-stiffness`(D8x 연구 팔, 없으면 옛 동작) |
| 21 | `.../s9/b5_baseline_compare.py` | +3 | 경로 밖 | P-1·P-2 무관 | `liftoff_slow_events` 기록 |
| 22 | `04_scripts/03_control/b1/b1_harness.py`, `b1/b1_record.py` | 추가 | 경로 밖 | P-1·P-2 무관 | B1 연구 러너. 자기 프로세스에서만 `C2Controller.update`를 감싼다 |
| 23 | `.../k2/k2b_probe/e1_smatrix_probe.py`, `k2/loc_shadow/g8_shadow_check.py`, `k2/loc_shadow/hsh_summary.py` | 추가 | 경로 밖 | P-1·P-2 무관 | 진단·요약 스크립트 |
| 24 | `.../coupled/d1_judge_4368.py`, `h6_judge_4368.py`, `h8_noise_judge_4368.py`, `judge4368_common.py`, `judge_stage1_4368.py`, `las_t3_judge_4368.py`, `u3_judge_4368.py`, `u3_judge_k1.py`, `u9_judge_4368.py` | 추가 | 경로 밖 | P-1·P-2 무관 | 경로 1 판정 도구(실행 뒤 jsonl만 읽음) |
| 25 | `.../coupled/resume_k1_family.py`, `resume_k1_family_f.py`, `resume_k1_identity.py` | 추가 | 경로 밖 | P-1·P-2 무관 | 계열 표, 계열 F 줄 정리, identity 사이드카 기록 |
| 26 | `.../coupled/las_p5r4k1_targeted.py`, `test_las_p5r4k1_targeted.py`, `README_judges_4368.md` | 추가 | 경로 밖 | P-1·P-2 무관 | P5r4 연구 러너, 단위 시험, 설명 문서 |

- 표의 파일 수: `03_src` 2 + 하네스 경로 38(`03_control` 13 + `04_hydraulic` 23 + `01_dynamics` 2) + `run_S9.py`(판정 함수만) 1.
- **남는 위험(공개)**: 기록 추가 가운데 예외를 낼 수 있는 곳이 있다.
  - 예: `verdict_runs.sa4_record`는 토양 정지 뒤 `TRUE_FORCE`가 유한하지 않으면 `ValueError`를 낸다. `plant.Wr`가 없으면 `AttributeError`가 난다.
  - 이런 예외는 명령 비트를 바꾸지 않고 그 줄을 `error` 줄로 만든다. 앵커가 있는 키의 줄이 `error`이면 rev1 RV1-5의 "키마다 정확히 1줄" 대조에서 S-7로 드러난다. 조용히 지나가는 경로는 없다.
- `numba` `cache=True` 함수의 서명이 바뀌어 첫 실행에서 다시 컴파일된다. 컴파일은 연산 순서를 바꾸지 않는다(fastmath 없음). 비트 같음의 최종 확인은 P-1·P-2 자체다.

## R13-3. 앵커 결정: 유지

- **정의**: P-1·P-2 비트 예측의 앵커를 다시 정하지 않는다. 앵커 파일 5개와 그 sha256, 고르는 줄, `run_v5.job_key` 대응, 키 수, "키마다 정확히 1줄"은 rev1 RV1-5 그대로다. 원판 10절 P-1·P-2의 예측 내용과 원판 8.2 S-7(어긋나면 판정 전에 멈추고 원인을 본다)도 그대로다.
- 근거: R13-2의 변경은 모두 세 가지 가운데 하나다. H-1 명령 경로 밖이거나, 경로 안에서 기록 전용이거나, H-1이 주지 않는 선택 인자이고 그 기본값이 `c6bb55b`의 연산을 그대로 남긴다. 그래서 `c6bb55b`에서 세운 예측(P-2: `hsh_report.md` "`c6bb55b`에서 456/456", P-1: 저장 앵커)이 같은 근거로 R에서도 선다.
- 이 판이 원판 A-5가 요구한 "앵커를 다시 정하는 개정"이고, 판단 결과는 "다시 정하지 않음"이다. A-5의 이 조건은 이 판 봉인으로 충족된다. 다만 R13-4의 확인(R의 `03_src`·`02_params`·`04_scripts`가 `a861981`과 같음)이 참일 때만이다.
- P-1·P-2가 어긋나면(S-7) 원인 확인은 R13-2 표의 경로 안 항목(#3~#16)부터 본다. 이 판은 그 순서를 권할 뿐 판정을 바꾸지 않는다.
- 결정 필요: **아니오**(코드 diff에서 바로 나오는 판단, 사용자 결정 2026-11-13 "rev13으로 처리").

## R13-4. 커밋 R과 `git_at_start` (원판 A-5 첫 문장과 원판 0절 1항을 고쳐 씀)

- **정의**:
  1. **H-0**(T-3K)의 `git_at_start` = `a861981`. 사용자 결정(2026-11-13): H-0은 A-5 대상이 아니고 먼저 시작한다. 근거: A-5의 앵커 조건은 P-1·P-2(H-1)만 다룬다. H-0의 비트·정체성 대조는 `las_targeted_rules` 원판~rev5와 이 문서 rev4 R4-C4·rev6 R6-C2(K-0)가 정한다.
  2. **본 묶음**(H-1~H-10, Chrono C-1~C-8, probe, J_P 재실행이 생기면 `JP`)의 `git_at_start` = 커밋 R 하나다. 원판 A-5의 "모든 묶음이 같은 `git_at_start`"는 "본 묶음은 모두 같은 `git_at_start` R"로 읽는다.
  3. **R의 모양**(rev12 선례와 같음):
     - 봉인 커밋 S: 부모 = `a861981`(5행의 봉인 커밋 값 = `a861981`). S가 바꾸는 것은 아래 (가) 세 파일과 (나) `.gitattributes` 6줄뿐이다.
     - R = S 위에서 브랜치 `z4370-p2id`(커밋 `2d4b390`, 경로 2 K-0 사이드카 읽기 수정, 부모 `a861981`)를 `--no-ff`로 병합한 커밋. 부모는 S와 `2d4b390` 둘이다.
     - `a861981`..R 사이 커밋은 S와 `2d4b390` 둘뿐이고, 둘 다 아래 허용 목록 안의 파일만 바꾼다(S = (가)·(나), `2d4b390` = (다)).
     R의 조건(모두 참이어야 한다):
     - R이 위 모양이다(`git rev-list --parents -n 1 R`의 부모가 S와 `2d4b390`, S의 부모가 `a861981`).
     - `git diff --name-only a861981..R -- 03_src 02_params 04_scripts`의 출력이 비어 있다. 이것이 R에서 A-5의 확인이다(`c6bb55b`..R의 차이가 R13-2 표와 같다는 뜻).
     - `git diff --name-only a861981..R`의 모든 파일이 허용 목록 안이다.
       - (가) `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev13.md`, `v5_resume_4368_rules_rev13.sha256`, `v5_resume_4368_rules_rev13_seal_candidate_draft.md`
       - (나) `.gitattributes`에 `-text` 줄 6개를 더한 것만(`git diff a861981..R -- .gitattributes`에서 더한 줄 6개, 지운 줄 0개): (가) 세 파일의 3줄과, 본 묶음 출력 폴더의 다음 3줄. 출력 폴더 줄은 `core.autocrlf=true`에서 결과 파일을 커밋할 때 줄 끝 변환으로 sha가 깨지는 것을 막는다(실행 전 감사 지적 4).
         - `06_analysis/03_hydraulic/coupled/v5/las/t3_k1/** -text`
         - `06_analysis/03_hydraulic/coupled/v5/resume_k1/** -text`
         - `06_analysis/02_control/v5_rerun/las_k1/** -text`
       - (다) 경로 2 `06_analysis/02_control/verif_matrix/v5_resume_4368/path2/` 아래의 `p2_t3k.py`, `test_p2_t3k.py`, `README.md`. 세 파일 모두 R의 git blob sha256(`git show R:<파일>`)이 `2d4b390`의 blob과 같다: `p2_t3k.py` `ede708d8d45797ecb1f27949c020e44474c06f52bf0aafb71eb1eb4ad55055fb`, `test_p2_t3k.py` `c82e098f9a0bb3fdb789b9d6c241a23bdd9286c6ea12ca77310c052ddcc9e7a9`, `README.md` `35bf8bf91424ae8fea08ab39e7a07b4868da7724214d4c3210a69d7a2ff61e64`
       - (라) rev8 R8-4의 판정서·감사 기록
       - (마) `00_docs/decision_log.md`·`00_docs/00_roadmap.md`·`00_docs/handoff/session_handoff.md`의 문서 갱신
     - 하나라도 거짓이면 본 묶음을 시작하지 않는다. 고칠 길은 두 가지다. R을 다시 만들거나, 바뀐 코드에 대해 새 개정으로 A-5 판단을 다시 하고 R13-5의 G-S를 돈다.
  4. 원판 0절 1항의 "한 커밋에서 한 번만"은 "실행 코드가 한 상태(`03_src`·`02_params`·`04_scripts`가 같은 커밋들)에서 한 번만"으로 읽는다. `a861981`과 R은 실행 코드가 같다(3의 둘째 조건). 둘의 차이는 판정 쪽 경로 2 도구(다)와 문서뿐이다.
- 근거: (가)·(나)·(라)·(마)의 파일은 어떤 러너·판정 도구도 읽지 않는다.
  - 436.8 경로 1 도구의 봉인 목록은 이름을 하나씩 적은 고정 목록이고 rev12에서 끝난다(`judge4368_common.py` 80행, `chrono_rows_judge_4368.py` 97행).
  - `a861981`의 `03_src`·`04_scripts`에서 규칙 파일·`verif_matrix`·`.sha256`을 대상으로 한 `glob`·`rglob`·`iterdir`·`listdir`을 `git grep`으로 찾으면 436.8 도구에는 없다. 있는 것은 D8x 규칙 폴더의 `run_d8x_g0_rev3.py`뿐이다.
  - 하네스 identity의 `rules_seals`는 `d8x_spec.seal_report()`(D8x 규칙)라 rev13과 무관하다.
  - (다)는 판정 도구이고 실행 코드가 아니다. 그래서 그 영향은 R13-5의 G-S가 확인한다.
- 결정 필요: **아니오**(사용자 결정 2026-11-13: rev13으로 처리, H-0 먼저, 허용 목록, R에 경로 2 수정).

## R13-5. 순서와 G-S (rev12 R12-6을 Y = R로 적용)

- **순서**:
  1. 이 판을 봉인한다(sha256과 봉인 시각 확정). 본 실행 중에는 메인 checkout을 dirty로 만들지 않는다. 그래서 H-0 끝 사이드카가 써지기 전에는 봉인 파일을 checkout 밖(scratchpad 등)에서 확정한다.
  2. H-0 끝 사이드카(`.identity.json`의 `end` 기록)가 써진 뒤, 그리고 어느 본 묶음보다도 먼저, R13-4 3의 모양으로 R을 만든다: (a) 봉인 파일 셋과 `.gitattributes` 6줄을 넣고 `tools/verif/seal_check.py`로 확인한 뒤 `a861981` 바로 위에 봉인 커밋 S를 만든다. (b) S 위에서 `z4370-p2id`(`2d4b390`)를 `--no-ff`로 병합한다. 이 병합 커밋이 R이다.
  3. **R에서 G-S 전체를 다시 돈다**: 하네스 G-S, Chrono G-S, 두 경로의 G-S 확인(경로 1 `gs-check`·G-S 하위 명령, 경로 2 `gs-load` 등). 도구에는 `--git-at-start R`을 준다(rev12 R12-3). 출력은 untracked `gs_harness_<R>/`·`gs_chrono_<R>/`에 두고, sha는 판정서에 적는다(rev11 R11-6).
  4. R의 G-S가 원판 11.2·rev11·rev12대로 통과하면 H-1과 Chrono 본 묶음을 R에서 시작한다. 통과하지 않으면 본 묶음을 시작하지 않는다(원판 8.2 S-11).
  5. R 뒤에는 본 묶음이 모두 끝날 때까지 커밋·병합하지 않는다(원판 A-5 둘째 문장, S-12). G-S 출력은 untracked이므로 커밋하지 않는다.
- **R12-6과의 관계**: R12-6은 문장 그대로 적용하되 최종 Y = R이다. "R에서 이 판 봉인 뒤 G-S 전체를 다시 돌린 것을 원판 11.2 충족으로 본다." 본 묶음의 `git_at_start`는 R이거나, R 위에 판정서·감사 기록만 더한 커밋이다. 판정서·감사 기록만 더한 커밋은 본 묶음이 끝난 뒤에만 만든다. `a861981`을 포함해 R보다 앞선 커밋의 G-S는 기록만 하고 인용하지 않는다(rev11 R11-7·rev12 R12-6과 같은 이유).
- **H-0의 원판 11.2**: H-0 줄은 `a861981`에서 돌고, `a861981`의 G-S는 위 문장대로 인용하지 않는다. H-0의 11.2 근거는 R의 G-S다. 그 G-S에는 H-0 줄 종류(R-0·R-0K·T-3K, rev11 R11-1)가 들어 있다. `a861981`과 R은 실행 코드가 같으므로(R13-4 3) R에서 확인한 키 경로는 H-0 줄에도 그대로 있다. R의 G-S가 H-0 줄 종류에서 통과하지 않으면, H-0의 판정은 하지 않고 멈춘다(S-11).
- **R11-4(S-12 커밋 정체성)와의 관계**: 대조 기준은 "판정서에 적은 `git_at_start`"이고 묶음마다 따로 적는다(R13-6).
  - 본 묶음: Chrono 행의 `code_at_launch.git.head`, level·L2b·L1-R 행의 `result.json` `code_state.git_at_start`, 하네스 줄·identity의 커밋은 모두 R이다.
  - H-0: 기록은 `a861981`이다.
  - 다르면 원판 8.2 S-12다(R11-4 5항 그대로).
- **K-0(rev6 R6-C2)과의 관계**: H-0의 `.identity.json` `start`·`end` `git.head`는 서로 같고 H-0의 `git_at_start` `a861981`과 같아야 한다. 그래서 봉인 커밋 S와 R은 H-0 끝 사이드카가 써진 뒤에만 만든다(순서 2). H-0 실행 중에 S나 R을 만들면 `end` 기록이 R을 가리켜 K-0이 거짓이 되고, 실행 중 커밋이라 S-12에도 걸린다. 작업 트리 조건("깨끗하거나 실행 전 감사가 허용한 파일뿐")도 있으므로, H-0 실행 중에는 봉인 파일과 경로 2 수정을 메인 checkout에 두지 않는다(순서 1).
- **S-12**: S와 R은 실행 중인 묶음이 없을 때 만든다. S를 만들기 전에 H-0 밖의 묶음이 `a861981`에서 시작했으면, R을 만들지 않고 멈춘 뒤 묻는다.
- 결정 필요: **아니오**(사용자 결정 2026-11-13: R에 경로 2 수정, R에서 G-S 전체, 그 뒤 본 묶음).

## R13-6. 판정에서 두 커밋과 K-0 두 읽기를 다루는 방법

- H-0과 본 묶음의 `git_at_start`가 다른 것은 허용한다(R13-4). 한 묶음 안에서 커밋이 둘 이상이면 원판 S-12 그대로 멈춘다.
- 판정 도구의 `--git-at-start`(rev12 R12-3, 필수)에는 그 묶음의 값을 준다. H-0(T-3K 판정, K-0 포함)은 `a861981`, 본 묶음은 R이다. 판정 도구는 R에서 돌린다. H-0의 경로 2 판정도 R의 `p2_t3k.py`(R13-4 (다))로 한다.
- 묶음 사이 비교: H-0의 출력을 다른 묶음의 비트 앵커로 쓰는 규칙은 없다. P-1의 T-1·T-2 앵커는 저장 파일 `las_T1.jsonl`·`las_T2.jsonl`이다(rev1 RV1-5). H-0의 판정은 본 묶음의 시작 조건(원판 A-3, S-14)으로만 쓰인다. 그래서 두 커밋의 차이는 판정 값에 닿지 않는다.
- **K-0 사이드카 두 읽기(공개)**: `resume_k1_identity.py`는 사이드카에 기록을 덧붙이므로 `start`·`end`가 각각 여러 개일 수 있다.
  - R의 경로 2(`p2_t3k.py`, `2d4b390`)는 `start`·`end`를 기록 목록으로 읽고, R6-C2의 조건을 모든 기록에 적용한다.
  - 경로 1은 `start`·`end`의 마지막 기록만 읽는다.
  - head 밖의 항목도 두 경로가 다른 기록을 본다. 경로 1은 `rules_seals`와 작업 트리(`git.is_clean`·`status_porcelain`)를 `end` 기록까지 보고, `affinity_mask`도 비교한다. 경로 2는 이 항목들을 `start` 기록 기준으로 본다.
  - R6-C2의 문장("`start`·`end`의 `git.head`")은 기록이 여러 개일 때를 정하지 않는다. 이 판은 그 정의를 새로 정하지 않는다.
  - 판정서에는 H-0 사이드카마다 `start`·`end` 기록 수와 두 경로의 K-0 결과를 원판 9.2 "두 경로 정의가 다른 곳" 표로 공개한다.
  - 기록이 하나씩이면 두 읽기는 같다. 여러 개이고 등급이 다르면 원판 8.2 S-13(그 묶음 `판정 불가`, 두 출력을 그대로 적고 묻는다)이다.
- 판정서(원판 13절 1항)에 적을 것:
  - 묶음별 `git_at_start`(H-0 `a861981`, 본 묶음 R)
  - `git diff --name-status a861981..R`의 출력 전체와 R13-4 3 조건들의 확인 결과((다)의 blob sha256 대조 포함)
  - `git diff --name-status c6bb55b..R -- 03_src 02_params 04_scripts/01_dynamics 04_scripts/03_control 04_scripts/04_hydraulic`의 출력이 R13-2 표와 같다는 확인
  - R의 G-S 목록과 sha(R13-5), 이 판의 봉인 확인(R13-7), K-0 두 읽기 표(H-0 사이드카마다 `start`·`end` 기록 수, `git.head`뿐 아니라 `rules_seals`·작업 트리·`affinity_mask`를 각 경로가 어느 기록으로 보았는지와 그 결과)
- 결정 필요: **아니오**(사용자 결정 2026-11-13: 차이는 판정서에 공개).

## R13-7. rev13 봉인 확인과 도구 봉인 목록

- 경로 1 도구의 봉인 확인 목록(`chrono_rows_judge_4368.py` `RULES_SEALS`, `judge4368_common.py`, `resume4368_judge` 봉인 목록)은 rev12까지 그대로 둔다. 사용자 결정(2026-11-13)이고, 코드 변경을 줄이기 위해서다.
- **경로 2 도구(`p2_*`)의 봉인 목록에도 rev13을 넣지 않는다.** 경로 2는 R에서 이미 바뀌지만(R13-4 (다)), 넣지 않는다. 이유는 셋이다.
  - (1) 넣으면 경로 2만 rev13을 확인하는 비대칭이 생긴다. 같은 S-1 조건을 두 경로가 다르게 판정하게 된다.
  - (2) (다)의 내용이 `2d4b390`과 달라진다. 그러면 blob sha256 조건과 그 수정의 검토 범위가 넓어진다.
  - (3) rev13은 경로 2가 읽는 판정 정의를 바꾸지 않는다. K-0 읽기 차이는 R13-6에서 공개로만 다룬다.
- 목록에 rev13이 없는 것은 원판 S-1이 아니다. rev13의 sha256은 `tools/verif/seal_check.py`로 확인한다. 확인 시점은 본 묶음마다 실행 전 감사(원판 A-10)와 판정서 커밋 전이다. 다르거나 `.sha256`이 없으면 원판 8.2 S-1(전 묶음 멈춤)이다.
- 결정 필요: **아니오**(사용자 결정 2026-11-13, 경로 2 목록은 같은 이유로 권고대로).

## R13-9. 결정 표

| 항목 | 권고·정의 | 결정 필요 |
|---|---|---|
| R13-1 확인 범위 | `03_src`·`02_params` + 하네스 경로 38(`04_hydraulic` 23, `03_control` 13, H-1 러너 정적 import 닫힘의 `01_dynamics` 2) + `run_S9.py` 판정 함수. Chrono `02_chrono` 17은 A-5 대상 아님 | 결정됨: 사용자 결정 2026-11-13(38개) |
| R13-2 파일별 판단 | 모든 변경이 경로 밖·기록 전용·기본값 옛 산술. 남는 위험은 예외로 생기는 `error` 줄이고 S-7로 드러남 | 아니오 |
| R13-3 앵커 | 유지(rev1 RV1-5 그대로, P-1·P-2·S-7 그대로). 이 판이 A-5의 개정 | 결정됨: 사용자 결정 2026-11-13(rev13으로 처리) |
| R13-4 R과 `git_at_start` | H-0 `a861981`, 본 묶음 R = 봉인 커밋 S(부모 `a861981`, rev13 세 파일 + `.gitattributes` 6줄) 위에서 `2d4b390`을 `--no-ff`로 병합한 커밋(실행 코드 diff 0, 허용 목록 (가)~(마)만, 경로 2 세 파일은 `2d4b390` blob과 같음). "한 커밋" = 실행 코드 한 상태 | 결정됨: 사용자 결정 2026-11-13(H-0 먼저, 허용 목록에 문서 셋, R에 경로 2 수정) |
| R13-5 순서·G-S | rev13 봉인(checkout 밖) → H-0 끝 사이드카 → 봉인 커밋 S → `2d4b390` `--no-ff` 병합 = R → R에서 G-S 전체(하네스·Chrono·두 경로) → 통과 뒤 본 묶음. R12-6은 Y = R. H-0의 11.2 근거도 R의 G-S. K-0·R11-4·S-12는 묶음별 `git_at_start`로 | 결정됨: 사용자 결정 2026-11-13(R에서 G-S 전체) |
| R13-6 두 커밋·K-0 두 읽기 | 묶음별 `--git-at-start`. 경로 2 모든 기록 / 경로 1 마지막 기록의 차이는 판정서에 공개, 등급이 다르면 S-13 | 결정됨: 사용자 결정 2026-11-13(공개) |
| R13-7 봉인 확인 | 경로 1·경로 2 도구 목록 모두 rev12까지, rev13은 `seal_check.py`로 실행 전 감사·판정서 커밋 전 | 결정됨: 사용자 결정 2026-11-13(경로 1), 경로 2는 대칭을 위해 같게 |

### 결과 전 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-13 | A-5 처리 | 사용자 결정 2026-11-13: rev13으로 처리 | R13-1~R13-3 |
| 2026-11-13 | H-0 순서 | 사용자 결정 2026-11-13: H-0은 A-5 대상 아님, `a861981`에서 먼저 시작. R은 H-0 끝 사이드카 뒤·H-1이 든 하네스 러너 시작 전에 만들고, 본 묶음의 `git_at_start`는 R | R13-4, R13-5, R13-6 |
| 2026-11-13 | 범위 | 사용자 결정 2026-11-13: A-5 범위 38개(`04_scripts/01_dynamics` 2개 포함) | R13-1 |
| 2026-11-13 | 허용 목록 | 사용자 결정 2026-11-13: R 허용 목록에 decision_log·roadmap·handoff 문서를 넣음 | R13-4 3 (마) |
| 2026-11-13 | 경로 2 수정·G-S | 사용자 결정 2026-11-13: R에 경로 2 K-0 수정(`2d4b390`)을 넣고 R에서 G-S 전체(하네스·Chrono·두 경로)를 다시 돈 뒤 본 묶음 시작. 두 경로의 K-0 읽기 차이는 판정서에 공개 | R13-4 3 (다), R13-5, R13-6 |
| 2026-11-13 | 봉인 목록 | 사용자 결정 2026-11-13: 도구 봉인 목록은 rev12까지 고정, rev13은 `seal_check.py` | R13-7 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 파일 이름: `v5_resume_4368_rules_rev13_seal_candidate_draft.md` → `v5_resume_4368_rules_rev13.md`(같은 폴더). 초안 파일은 지우지 않고 그대로 둔다.
2. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev13 (원판 A-5 앵커 확인: `c6bb55b`..`a861981` 코드 변경의 P-1·P-2 비트 영향, 앵커 유지, H-0과 본 묶음의 `git_at_start`, 경로 2 K-0 수정을 담은 커밋 R에서 G-S 전체, 결과 전, 봉인)`
3. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev13.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev13_seal_candidate_draft.md`와 1·3·5·9행만 다르다.`
4. 5행("시점")에서 `SEAL_TIME`(예: 2026-11-13 10:00:00 +09:00)과 `SEAL_COMMIT`(봉인 파일을 넣는 커밋의 부모 = `a861981`, R13-4 3)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
5. 9행("봉인 준비판이다")을 다음으로 바꾼다:
   `- **봉인본이다.** 사용자 결정이 필요한 새 항목은 없었고, 사용자 결정(2026-11-13: rev13으로 처리, H-0은 A-5 대상 아님·먼저 시작, 범위 38개, 허용 목록에 문서 셋, R에 경로 2 수정을 넣고 R에서 G-S 전체, 도구 봉인 목록은 rev12까지)은 R13-1~R13-7과 R13-9 결정 표에 반영했다.`
6. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev13.sha256`에 `<sha256>  v5_resume_4368_rules_rev13.md  sealed <SEAL_TIME 값> (436.8 rev13: original A-5 anchor check on top of rev12; scope 03_src / 02_params / 38 harness files (04_hydraulic 23, 03_control 13, 01_dynamics 2 from the static import closure of the H-1 runner run_v5.py) plus run_S9 judgement helpers, Chrono 02_chrono not A-5; every c6bb55b..a861981 change is outside the H-1 command path, record only after the commands, or an option whose default keeps the c6bb55b arithmetic (mass_scale 1.0, lockm 0, no lock_stiffness key, MASK_ENV unset), exceptions become error lines = S-7; P-1 / P-2 anchors kept as rev1 RV1-5, S-7 unchanged; git_at_start H-0 = a861981 (user decision: H-0 not A-5, first), main bundles = commit R = --no-ff merge of z4370-p2id (2d4b390) on the seal commit whose parent is a861981, with no change in 03_src / 02_params / 04_scripts and only the rev13 files, 6 added .gitattributes -text lines (the 3 rev13 files and the output folders v5/las/t3_k1/**, v5/resume_k1/**, v5_rerun/las_k1/** against core.autocrlf=true), the path 2 K-0 fix of 2d4b390 (p2_t3k.py ede708d8, test_p2_t3k.py, README.md, same blobs), judgement / audit records and decision_log / roadmap / handoff docs; "one commit" = one run-code state; order rev13 seal outside the checkout -> H-0 end sidecar -> R -> full G-S at R (harness, Chrono, both paths, --git-at-start R) -> main bundles, R12-6 with Y = R, earlier G-S record only, H-0 11.2 by the R G-S; K-0 / R11-4 / S-12 against the git_at_start of each bundle; K-0 sidecar read as all records (path 2) vs last record (path 1), and rules_seals / work tree / affinity_mask by end (path 1) vs start (path 2) records, disclosed in the judgement, grade difference = S-13; rev13 not in the path 1 or path 2 tool seal lists, checked by seal_check.py before each bundle and before the judgement commit; user decisions 2026-11-13; thresholds and grades unchanged)` 한 줄로 쓴다.
7. `.gitattributes`에 다음 6줄을 더한다(지우는 줄 없음, R13-4 3 (나)). 뒤의 3줄은 `core.autocrlf=true`에서 결과 파일을 커밋할 때 sha가 깨지는 것을 막는다:
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev13.md -text`
   - `…/v5_resume_4368_rules_rev13.sha256 -text`
   - `…/v5_resume_4368_rules_rev13_seal_candidate_draft.md -text`
   - `06_analysis/03_hydraulic/coupled/v5/las/t3_k1/** -text`
   - `06_analysis/03_hydraulic/coupled/v5/resume_k1/** -text`
   - `06_analysis/02_control/v5_rerun/las_k1/** -text`
8. `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`로 확인한다. 봉인본의 5행 자리 값(`SEAL_TIME`·`SEAL_COMMIT`)이 값으로 바뀌었는지 본다. 이 절의 안내 문구에는 두 이름이 남는다(rev12와 같은 선례). 그 뒤 봉인 커밋 S를 만든다(부모 `a861981`, 커밋 시점은 R13-5 순서 2). 봉인 뒤 이 문서를 고치지 않는다. 고칠 것이 생기면 `v5_resume_4368_rules_rev14.md`로 새로 봉인한다.
