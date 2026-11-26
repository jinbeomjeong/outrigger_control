# 판 8 S8-R 개정 1: Q8-4·Q8-5·Q8-11·Q8-12 하네스 사실 확인 (python-expert, 읽기 전용)

- 대상: worktree `C:\workspace\outrigger_control\.claude\worktrees\ed8-impl`, HEAD `7fc834565b0f2c75ea55a2dd2b23b3e59b37d06c`. 추적 파일은 바꾸지 않았다(`git status --untracked-files=no` 빈 출력).
- 의존성 점검: 모두 있음.
- 구현·커밋은 하지 않았다. held-out 후보 조건도 실행하지 않았다. 실행한 것은 순수 함수 호출(태그 함수)과 저장 파일의 키 존재 확인뿐이다.
- 블라인드 경로(`606f8713/cdry_a1/VBK_c92*`·`VBK_c93*`·`cdry_a1/logs/`, `prelaunch_j9/ed6_inputs/x11/selection.json`)는 열지 않았다. 상위 폴더도 검색 범위로 쓰지 않았다. 검색 범위는 worktree의 `03_src`·`04_scripts`·`05_tests`·`00_docs`·`02_params`와 아래에 적은 개별 파일 경로뿐이다.
- 산출물(`python_q8_checks\`): 점검 스크립트 4개(`scan_tokens.py`, `tag_check.py`, `layer_input_check.py`, `d_pair_check.py`)와 출력 4개(`token_scan.json`, `tag_check.json`, `layer_input.json`, `d_pair.json`).
  - 출력에는 키 이름, 구조, 건수만 있다. 재접근 시작 값, 통과 여부 같은 값은 없다.

---

## 1. Q8-4 seed: 판정 하네스에는 궤적을 바꾸는 seed가 없다 (이상 센서, 결정적)

**결론**
- dynamics의 판단("결정적, seed는 손잡이 아님")은 코드로 맞다.
- `run_v5` → `verdict_runs` 경로에는 job 인자에도, 함수 인자에도 seed가 없다. 난수를 쓰는 곳도 없다.
- 센서는 이상 센서(플랜트 참값)다. 잡음 모델이 켜지는 경로는 이 하네스에 없다.

**근거 (worktree 행 번호)**
- `04_scripts/04_hydraulic/coupled/run_v5.py`
  - 26행: 모듈 docstring에 "Deterministic (no noise)".
  - 807~861행 `run_one`: job에서 읽는 키는 `mask`, `eps`, `setting`, `eta_v`, `contact`, `d1`, `k1`, `mass_scale`, `case`, `decision`, `offset_s`, `twin`, `timing`, `u9_metrics`뿐이다. seed 키는 없다.
  - 46~48행: 스레드 수 1. 774행·1089행: 실행마다 새 spawn 프로세스(`maxtasksperchild=1`).
- `04_scripts/04_hydraulic/coupled/verdict_runs.py`
  - 667~716행 `execute`: seed 인자가 없다.
  - 사건 경로 `_run_event`(574~643행)는 r51·r67 하네스를 쓴다. 정상 경로 `_run_steady`(545~570행)는 `s9_soil_slope.run_one`을 쓴다.
- 이상 센서 (사건 경로)
  - `04_scripts/03_control/s8/r51_reapp_closed_loop.py` 328~349행 `control_period`: `Measurements`를 플랜트 참값으로 만든다. `head_pressure = plant.pressure()/ha`, `stroke = plant.sref`, `stroke_corrected = plant.x`, IMU는 1 ms 가속도 평균, 자이로는 `plant.w`다.
  - 같은 파일 docstring 9행 "ideal sensors (no noise)", 32행 "Deterministic (no random numbers)".
  - `r67_g1_screen.py` docstring 10행 "Ideal sensors", 54행 "Deterministic".
  - 로드 압력 분리는 `r64_g4_closed_loop.py` 192행 `with_two_pressures`(결정적 계산)다. VBJ 이후 플랜트는 `harness_hydraulics.py` 484~496행 `with_plant_truth_pressures`(M2 참값)를 쓰고, 1159~1160행에서 설치된다.
- 이상 센서 (정상 경로)
  - `04_scripts/03_control/s9/s9_soil_closed_loop.py` 412~423행에 `SensorError`(seed가 있는 잡음)가 있다. 이 잡음은 `case["sensor"]`가 있을 때만 켜진다(526~529행).
  - 그런데 `s9_soil_slope.py` 559~570행 `run_case_input`은 `"sensor"` 키를 넣지 않는다. 그래서 판정 하네스에서는 이 경로에 닿지 않는다.
- 등급 기록: `harness_hydraulics.py` 502~506행 `_SENSOR_GRADE = ["ideal"]`은 기록 전용이다. `declare_sensor_grade`를 부르는 곳은 r79뿐이다(`r79_sensor_screen.py` 287~292행).
- 난수 검색
  - `default_rng`, `np.random`, `RandomState`, `SeedSequence`를 검색했다. `coupled\*.py`에서는 시험 파일과 키 추출·P-pred 도구에서만 나온다.
  - `03_control\{s8,s9(sensor 경로 제외),m1_check,r8d1 c2py}`의 실행 경로 모듈에서는 나오지 않는다.
  - `03_src`에서는 `sensors/*`(SensorSuite 등)과 `ml/*`에서만 나온다. SensorSuite를 만드는 곳은 `r79_sensor_screen.py`와 Chrono 스크립트뿐이다.

**seed가 궤적을 바꾸는 곳 (판 8 G′와 무관, 참고)**
- T-JR-12b 경로인 `04_scripts/03_control/s8/r79_sensor_screen.py`다.
  - `LEVELS` 133~141행: L2 = normal 등급, IMU `normal_zeroed`.
  - `SensorSuite(imu, leg, seed)` 329~341행. `case_seed` 295~297행.
  - `jp3_12b_plan.py` 123행 `LEVEL = "L2"`, 108행 블록 seed_index 50~53.
- 12b의 seed 50~53은 센서 잡음 seed다. census와 G′ 하네스와는 별개다.
- 낱말 주의: `verdict_runs.py` 463~466행의 `stale_seed_release`(판 7 `plant_seed_artifact`)는 P1 플랜트의 물리 상태 "seed"다. 난수 seed가 아니다.

---

## 2. Q8-5 이름 충돌

### 2.1 설정 이름 VBN 계열: 문자 충돌 0

- 검색: `scan_tokens.py`로 파일 1545개를 봤다.
  - `03_src`·`04_scripts`·`05_tests`는 `*.py`, `00_docs`·`02_params`는 `*.md`·`*.yaml`·`*.json`.
  - Grep 도구로 대소문자를 무시하고 다시 봤다.
- 결과: `VBN` 0건, `LSN` 0건, `VBKN` 0건. 기존 이름의 일부로 들어간 경우(부분 문자열)도 없다.
  - 대소문자 무시 검색에서 `lsn`에 걸린 것은 `s2_defer_targeted.py`의 `_SoilSnapshot`(…`lSn`…)뿐이다. 설정 이름이 아니다.
- 실행 시 `run_v5.ALL_SETTINGS`에 이름을 더하는 프로브의 이름:
  - `P6-<plant>-<arm>`(`ed6_probe.py` 92·114행)
  - `P7-…`(`ed7_probe.py` 80·133행)
  - `P8-…`(`ed8_probe.py` 97·124행)
  - `VBG4`·`VBG6`(`jp3_case_replay.py` 40행)
  - VBN 계열과 겹치지 않는다.

**이름으로 판별하는 코드 (충돌은 아니고 구현 때 볼 곳)**

| 위치 | 동작 | 판 8 영향 |
|---|---|---|
| `r79_sensor_screen.py` 1301~1303행 `is_p3_setting` = `startswith(("VB","LS"))` | VBN0·VBKN0도 ③ 켬으로 분류된다. 1280행 J-P3 기록 입력에 쓰인다 | 지금 VBM0·VBKM0·VBL0도 똑같이 분류된다(새 문제 아님) |
| `ed7_condition3_adoption.py` 117행 `name.removeprefix("VB")` | VBM<key> → M<key> 프로브 플랜트 | 판 8에 재사용하면 VBN<key> → `N<key>`(정의 없음). 재사용할 때만 해당(Low) |
| `jp3_12b_plan.py` 127~133행 r79 키 정규식 `L\d+[A-Za-z]*\|s(\d+)\|` | r79 수준 토큰(L0~L4) | `LSN1`은 L 바로 뒤가 숫자가 아니어서 걸리지 않는다 |
| `run_v5.py` 978~981행 `--settings` | `ALL_SETTINGS` 이름과 정확히 같아야 통과 | 충돌 없음 |

**구현 때 목록에 넣어야 하는 곳 (빠지면 실행 거부·누락)**
- `run_v5.ROD_FAULT_SETTINGS`(282행): VBKN·VBKN0을 넣는다. r79가 이 목록으로 계획 파일과 설정의 짝을 강제한다(`r79_sensor_screen.py` 1061~1067행).
- `T4H_SETTINGS`(656~657행)
- `ALL_SETTINGS`(286~287행)

### 2.2 태그 접미사 `_E8`: 문자 충돌은 0이지만, 지금 코드는 ③ rev 7로 판별하지 못한다 (구현 필요)

**문자 충돌**
- 대소문자를 구분하면 `_E8`은 0건이다.
- 같은 낱말로 쓰이는 기존 토큰(대소문자 무시 `e8` 48건, `_e8` 35건)은 모두 다른 뜻이다.
  - **판 5 정오 8의 약칭 "e8"**: 실행 단계 이름 `12b_decide_e8`, `step6b_decide_e8`, `list_e8`, `E8FixedLists`, 문서 이름 `jp3_rev6_p2_handoff_ed5_e8.md`, `audit_resume_e8_tool8.md`, `stats_e8/`, 시험 이름 `05_tests/unit/test_jp3_12b_erratum8.py`의 `test_e8_*`(31건).
  - **D8x 기준 E-8**: `k2_recount.py` 57·77·595행 `e8_check`, `E8_MIN_WINDOW_S`.
  - **U-S8-1 "P7 + E8"**: `00_docs/decision_log.md` 820행.
- 문자열 비교는 대소문자를 구분하므로 기능 충돌은 없다. 다만 문서에서는 "e8 = 판 5 정오 8"과 섞여 읽힐 수 있다(Low).
- 참고: `_ED8`은 `verdict_runs.py` 328~340행의 내부 변수 `_ED8_RECORD`로 이미 쓰인다.

**판별 실패 (worktree `v5_options`를 실제로 import해 호출, `tag_check.json`)**

| 태그 | `switch_base_tag` | `extend_start_revision_of_tag` | `is_lock_start_b_tag` | `is_order_gate_tag` | `is_liftoff_slow_tag` |
|---|---|---|---|---|---|
| `final_C4G2_P3X_LAS_K1_LSB`(판 7 VBM, 대조) | `final_C4G2_P3X` | **7** | True | True | True |
| `final_C4G2_P3X_LAS_K1_LSB_E8`(VBN 초안) | 태그 그대로 | **None** | False | False | False |
| `final_C4G2_LAS_K1_LSB_E8`(VBN0 초안) | 태그 그대로 | None(③ 끔이라 기대값과 같음) | **False** | False | False |
| `final_C4G2_P3X_LAS_K1_E8_LSB`(다른 순서) | `final_C4G2_P3X_LAS_K1_E8` | None | True | False | False |
| `final_C4G2_P3X_E8_LAS_K1_LSB`(기본 태그 뒤) | `final_C4G2_P3X_E8` | None | True | True | True |

- 원인: `03_src/outrigger_sim/hydraulics/v5_options.py`의 접미사 처리.
  - `_split_tail`(842~847행)은 끝의 `_TCL`과 `_LSB`만 떼어 낸다.
  - `switch_base_tag`(933~942행)는 그다음 `_K1`과 `_LAS`만 떼어 낸다.
  - `extend_start_revision_of_tag`(953~960행)는 남은 기본 태그를 `EXTEND_START_REVISION_OF_BASE_TAG`(99~102행)에서 찾는다.
  - 그래서 `_E8`을 어느 자리에 두어도 rev 7을 돌려주지 않는다.
  - `with_lock_start_b_tag`도 `_E8` 태그 뒤에 `_LSB`를 한 번 더 붙인다(`…_LSB_E8_LSB`).
- 영향: 이 함수들은 `04_scripts`의 18개 파일에서 69번 부른다. 지금 상태로 VBN 줄을 판정하면 다음이 생긴다.
  - ③ 판별이 None이 되어 J-P3 판정 집합에서 빠지거나 정체성 결함(`setting_defect`)이 된다.
  - VBN0의 `_LSB` 판별도 실패한다.
- 필요한 일(Y8-2 범위)
  - `v5_options`의 접미사 문법에 판 8 접미사를 넣는다. `_split_tail`에서 떼는 순서, `with_switch_tags`에서 붙이는 순서와 그 조건이 되는 config 스위치를 정하고 단위 시험을 더한다.
  - 시험 기대값: VBN 태그 → rev 7, VBN0 태그 → None이면서 `is_lock_start_b_tag` True.
  - 옛 태그의 결과는 그대로여야 한다(P8-0 성격).
  - 접미사 이름을 `_E8`으로 유지할지는 명세 작성자가 정한다.

---

## 3. Q8-11 층 E 입력: 사건 행 V0 짝에는 키가 모두 있다. 정상 행에는 구조상 없다

**확인 결과 (`layer_input_check.py`, `d_pair_check.py`, 값은 보지 않고 키·구조·건수만)**

| 입력 | 확인 | 결과 |
|---|---|---|
| 저장 V0 `06_analysis/03_hydraulic/coupled/v5/main.jsonl` | sha256 앞 8자 `9ad74990` 일치 | 1200줄, V0 100줄(오류 줄 0, 키 중복 0) |
| └ V0 사건 줄(R12 32, R14 2, R15 2, R16 4) | `event_output.reapproach_starts` | **40/40 있음**, 모두 `[숫자, 문자열]` 쌍의 목록 |
| └ V0 정상 줄(S·R 정상 행) | `event_output` | **60/60이 빈 dict**(키 없음). `run_v5.py` 847~848행은 `result.get("event_output") or {}`를 복사하고, 정상 경로는 `event_output`를 만들지 않는다 |
| `ed6_design/keys/confirm_b_grid192.json` | sha256 `4e80e69b…` 전체 일치 | v0_pair 192/192가 저장 격자 run을 찾고 `commands_sha256`도 일치. 격자 파일 4개(`grid_r67_main.json`, `grid_r67_top.json`, `grid_r69_bottom.json`, `grid_r69_top.json`) |
| └ 격자 run | 키 위치 | **`runs[run_id].reapproach_starts`(run 최상위) 192/192**. `event_output` 감싸개는 없다 |
| `ed7_design/keys_seal_b46bdf8f/confirm_g1_grid171.json` | sha256 `684054ab…` 일치 | 171/171 찾음, 해시 일치, 키는 run 최상위에 있음. **`run_id`가 문자열로 저장돼 있다**(grid192는 정수) |
| `ed7_design/keys_seal_b46bdf8f/sens_keys_ed7.json` | sha256 `be930b75…` 일치 | v0_pair = `{job, source}`(main.jsonl). 사건 짝 260/260 있음, 정상 짝 200/200 없음 |
| D 12키 `3ecf61f1:…/run_records_ed6/d_grid_keys12.json`(git blob) | sha256 `a995abff…` 일치 | 파일에 v0_pair가 없다(필드: `first_breach_leg`, `job`, `t4h_file`). 12 job이 모두 grid192 줄과 정확히 1개씩 맞는다 → grid192의 v0_pair로 찾을 수 있다 |

**V0 재실행 없이 층 E를 계산할 수 있다.** 다만 T8 구현과 명세 문구에 다음이 필요하다.

1. **정상 행 처리 (명세 6.3 문구, 확인 필요)**
   - 6.3에는 "V0 짝 줄에 `reapproach_starts`가 없으면 … `setting_defect`"라고 되어 있다. 이 문장을 모든 단위에 적용하면, 정상 행 단위가 전부 입력 결함이 된다.
     - C-J: VBN 60 + LSN 32×4. C-S: 200.
   - 정상 행은 `SteadyTwin`이다(`verdict_cases.py` 48~59행, 123~152행). 정의상 층 N이다.
   - 키 필수 조건은 "사건 행(`EventTwin` 사례 R12/R14/R15/R16, 격자 행)"에만 걸어야 한다.
2. **경로가 둘이다**
   - main.jsonl 줄: `event_output.reapproach_starts`.
   - 저장 격자 run(C-D·C-G의 V0 짝): `runs[run_id].reapproach_starts`.
   - G1 171의 문자열 `run_id`는 정수로 바꿔 읽는다. 참고로 `jp3_ed6_judge.py` 741행 `grid_v0_run`은 정수 비교를 한다.
3. **시각의 기준과 정밀도 (확인 필요)**
   - 시작 시각은 사건 시각 기준 상대값이고 0.01 s로 반올림돼 있다(`r67_g1_screen.py` 276행 `e.t_s - t_ev`, 357행 `round(tt, 2)`). 그래서 "≤ 0.45 s"는 실제 0.445~0.455 s 사이에서 반올림에 따라 갈린다.
   - 분기는 사건 0.5 s 전에 시작한다(`verdict_runs.py` 606~608행 `stop_t = target - PRE_S`, `r67` 247·276행 `ctrl.events[n0:]`). 그래서 목록에 **음수 시각(사건 전 시작)**이 들어갈 수 있다.
   - "사건 뒤 가장 이른 시작"을 0 ≤ t ≤ 0.45로 읽을지, 음수 시작도 넣을지 문면에 적어야 한다.
   - 다리 문자열은 재접근을 시작한 다리다. 사건 다리는 job twin의 `leg`이고, 없으면 사례 기본값이다(R12·R14 RR, R15·R16 FL, `verdict_cases.py` 153~171행).
4. **정의가 같다는 근거**
   - 시작 목록을 만드는 줄(`r67_g1_screen.py` 357~359행)은 생성 커밋 `7862ef62`(2026-10-27) 뒤로 바뀌지 않았다(`git log -L`).
   - main.jsonl V0와 저장 격자는 같은 정의로 기록된 것으로 본다. 다만 저장 격자를 만든 커밋 자체는 확인하지 않았다(추정).

---

## 4. Q8-12 held-out 원천 인자

| 원천 | job 인자로 받는가 | 근거 | 필요한 변경 |
|---|---|---|---|
| (가) 임의 오프셋(0.0125 등) | **받는다** | `run_v5.py` 730~731행 `replace(case.twin, offset_s=float(job["offset_s"]))` → `verdict_runs.py` 608행 `t_event = … + twin.offset_s`. 값 제한 없음. T4h 이름 `o0.0125`도 구별된다(674·679행) | 없음 |
| (다) twin F_s 임의 값(1·3·6 kN) | **받는다** | `run_v5.py` 732~733행 `replace(case.twin, **job["twin"])` → `verdict_runs.py` 590행 `r67.make_base(…, twin.fs_kN)` → `r51_reapp_closed_loop.py` 80~83행 `seal_N = [fs, fs, 0.8333 fs, 0.8333 fs]`(연속값) → 302행 `plant.Fs`. `harness_hydraulics.py` 726행도 `plant.Fs`를 쓴다. T4h 이름 `Fs1`·`Fs3`·`Fs6`는 구별된다. 선례: D 12키에 이미 `fs_kN` 2.0이 있다(`ed7_probe.py` 116행) | 없음 |
| (나) 사건 깊이·램프(RE1bF 25 mm/0.05 s, 30 mm/0.04 s) | **받지 못한다** | `EventTwin`(`verdict_cases.py` 62~75행)에 깊이·램프 필드가 없다. 사건 형상은 이름으로만 고른다: `verdict_runs.py` 587행 `r67.EVENTS[twin.event]`, `r67_g1_screen.py` 95~99행 RE1bF = 30 mm / 0.05 s 고정. job twin에 `depth` 같은 키를 넣으면 `dataclasses.replace`에서 TypeError, 없는 사건 이름이면 KeyError가 난다. 둘 다 오류 줄이 된다(`run_v5.py` 859~861행) → 6.2 (마)에 따라 판정 불가 | 아래 |

**(나)를 쓰려면 필요한 변경 (실행 경로 모듈이므로 C8 전 구현 커밋에 넣는다)**
- 안 A(권장)
  - `EventTwin`에 선택 필드 `depth_m`·`ramp_s`(기본 None)를 더한다.
  - `verdict_runs._run_event`(587행)는 두 값이 주어지면 `{"depth": …, "ramp": …}`를 만들고, 아니면 지금처럼 `r67.EVENTS[event]`를 쓴다.
  - `run_v5.GRID_TWIN_FIELDS`(650행)와 `t4h_file_name`(668~687행)에 두 필드를 넣는다. 넣지 않으면 25 mm 줄과 30 mm 줄의 T4h 파일 이름이 같아져 덮어쓴다.
  - 기록의 `event`(631행)는 이름 그대로이므로, 판정 도구는 job twin에서 깊이를 읽어야 한다.
  - 두 형상 모두 빠른 사건이다(0.5 m/s, 0.75 m/s > `V_MAX` 0.020924 m/s, `r67` 120~121행). 판정 창 규칙은 RE1bF와 같다.
  - 범위: `verdict_cases.py`, `verdict_runs.py`, `run_v5.py`, 시험.
- 안 B(권장하지 않음): `r67.EVENTS`에 새 이름을 더한다.
  - r67 스크린 job은 `EVENTS` 전체를 돈다(`r67_g1_screen.py` 425행). 그래서 r67 스크린의 job 출력(run 수)이 바뀐다.
  - `resume_k1_steps.py` 127~128행 `GRID_EVENTS`(3개 전제)와도 어긋난다.

**명령 불변 조건 (P8-0)**
- (가)(다)는 코드를 바꾸지 않으므로 해당 없다.
- (나) 안 A: 새 필드가 없는 job은 지금과 같은 코드 경로를 타고 job_key도 같다. 원리상 명령은 비트 동일하다.
- 다만 바뀐 모듈은 실행 경로 모듈이다. P8-0 대조(7fc83456 명령 불변 8 job, `ed7_probe.py --arms a2 --part all` 114줄)로 확인해야 한다. 114줄에는 RE1bF D키가 들어 있어 바뀐 줄(587행)을 지난다.
- P8-11(T8에서 실행 경로 모듈이 C8과 바이트 동일)과는 충돌하지 않는다. 구현 → C8 → T8 순서이기 때문이다.

**G′ job을 넣는 방법 (참고)**
- 일반 job 파일 입력은 봉인 키 배치뿐이다(`--jobs-file`, `sealed_key_jobs` 422~440행, 이름과 sha를 `ED7_KEY_FILE_SHA256`로 대조).
- 판 8 키 배치와 `ED8_KEY_FILE_SHA256`이 필요하다. 이미 11.1의 C8 계획에 들어 있다.
- `sealed_key_jobs`는 설정 이름과 줄 수만 검사하고 twin 필드는 검사하지 않는다. 키 파일 생성기(Y8-6)에서 twin 필드를 `EventTwin` 필드와 대조하라고 권한다. 오타 필드는 실행 뒤 오류 줄(판정 불가)로만 드러난다.

---

## 확인 필요 (명세 작성자에게)

- **명세 6.3 "키 결측 = `setting_defect`"의 적용 범위**
  - 정상 행 V0 짝에는 `event_output`가 구조상 없다(main V0 60/60, sens 짝 200/200).
  - "사건 행만 키 필수, 정상 행은 층 N"으로 적어야 하는지 정해야 한다.
  - 규칙 문서: `jp3_remedy_spec_v8_rules.md` 207행 ↔ 코드: `run_v5.py` 847~848행, `verdict_cases.py` 48~59행.
- **층 E 시각 판정**
  - 사건 전 음수 시작을 넣을지(0 ≤ t ≤ 0.45로 읽을지), 0.01 s 반올림 값으로 비교한다는 점을 문면에 적을지 정해야 한다.
  - 규칙 문서: 205행 ↔ 코드: `r67_g1_screen.py` 276·357행, `verdict_runs.py` 606~608행.
- **태그 접미사 `_E8`**
  - 지금 `v5_options`로는 rev 7 판별이 None이다. 접미사 문법 확장은 구현 필수다(Y8-2).
  - 이름은 대소문자 구분으로 충돌이 없지만, 문서의 "e8"(판 5 정오 8)과 섞여 읽힐 수 있다. 이름을 유지할지 정해야 한다.
  - 규칙 문서: 130행 ↔ 코드: `v5_options.py` 842~847·933~960행.
- **G′ 원천 (나)**
  - 지금 하네스로는 쓸 수 없다. 안 A를 구현해 넣을지, 7.1 규칙대로 원천에서 뺄지 봉인 전에 정해야 한다.
  - 규칙 문서: 220·222행 ↔ 코드: `verdict_cases.py` 62~75행, `verdict_runs.py` 587행.

## 실행한 검증

- 의존성 점검 `depcheck.ps1`: 모두 있음.
- `scan_tokens.py`(python-dev `-I -B`): 종료 0, 파일 1545개.
- `tag_check.py`: 종료 0. worktree의 `03_src\outrigger_sim\hydraulics\v5_options.py`에서 import된 것을 단언했다.
- `layer_input_check.py`: 첫 실행은 종료 1이었다. G1 171의 문자열 `run_id`에서 TypeError가 났다. 정수 변환을 넣고 다시 실행해 종료 0. 이 사실이 위 3절의 `run_id` 형식 발견이다.
- `d_pair_check.py`: 종료 0.
- 점검 스크립트에 ruff를 돌렸다: ISC004 3건. 의도한 경로 문자열 이어 붙이기다. sha 일치로 경로가 맞음을 확인했다. 실행한 그대로 보관하려고 고치지 않았다.
- Grep 도구로 코드를 직접 읽어 확인한 행 번호는 본문에 적었다.
- 나의 scratchpad 하위 폴더 `python-ed8chk\`는 지웠다.

사용한 스킬: 없음
