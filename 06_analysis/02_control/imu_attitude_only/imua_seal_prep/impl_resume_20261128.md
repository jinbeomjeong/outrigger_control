# 논문 v5 A형 IMU(`_IMUA`) 구현 재개 보고 (python-expert, 2026-11-28)

- 범위: worktree `.claude\worktrees\v5-imua`(브랜치 `v5-imua`, 시작 `2ea96c96`)에서 P-2 나머지, P-5, P-6, P-8, P-7 일부를 구현했다. 봉인·본 실행·하네스 대량 실행은 하지 않았다. master와 판 8·판 9 코드는 가져오지 않았고, `ed9-impl`은 건드리지 않았다.
- 근거로 읽은 문서: `imua_seal_prep/report.md`, `verif_matrix/v5paper_imua_rules_draft.md` 수정 10, `decision_log.md` 836·837행.
- 사용한 스킬: 없음

## 1. 커밋 (브랜치 `v5-imua`, master 미병합)

| 커밋 | 항목 | 내용 |
|---|---|---|
| `dc67af47` | P-2 / P-5 / P-6 | 화면 4개(U-3·U-6)가 A형 인자를 받는다. A형 줄마다 G5 입력과 자세 기록이 붙는다. IND·IND_LAS도 경사계 뒤에서 돈다 |
| `d5df6201` | P-8 | `chrono_t45_replay`가 A형 Chrono 기록을 다시 만든다(C-5 T4/T5) |
| `b0416724` | P-7 일부 | 4.2 분류 서명과 봉인 대조, I-H 정체성 표본 선정 |

- 지금 HEAD는 `b0416724`이고 작업 트리는 깨끗하다.
- 새 파일은 커밋 전에 CRLF로 맞췄다. 기존 파일은 원래 CRLF 그대로다.

## 2. 항목별 구현

### P-2: U-3·U-6 러너 (`v5_rerun.py`)

- `--imu-model inclinometer --imu-gains <preset>`를 받는다.
  - argparse 화면 3개: `s9_slope_fix_candidates`, `s9_soil_slope`, `b5_baseline_compare`
  - 위치 인자 CLI인 `r72_g6_screen`(`split_argv`)
- 거부하는 조합(`SystemExit`, 조용한 기본값 없음): `--v5-setting` 없이 경사계, 프리셋 없는 경사계, 경사계 없는 프리셋.
- 부모가 인자를 해석할 때 환경 변수로 넘긴다. `run_v5`와 같은 방식이다.
  - 주의: full IMU로 해석하면 부모 셸에서 상속된 `V5_IMU_*`를 지운다.
- 워커의 `install_in_worker`에서 설치 순서는 플랜트 옵션 → A형 IMU → `verdict_runs` 기록 계층이다. 기록 계층이 가장 바깥에 남는다.
- 태그
  - C2·ABL은 빌드된 설정에서 `_IMUA`를 받는다: `final_C4G2_P3_LAS_K1_IMUA`, `ABL_LAS_K1_IMUA`, `final_C4G2_LAS_K1_IMUA`.
  - IND·IND_LAS는 제어기에서 받는다: `IND_IMUA`, `IND_LAS_IMUA`.
- `u3_reuse`(D-1 재사용)
  - Q-6은 A형 태그를 기대한다.
  - Q-7(새로 추가)은 D-1 줄의 `imu_sensor`가 이번 실행 설정과 같아야 한다.
  - 재사용 기록은 D-1 줄의 `imu_sensor`·`imua_check_g5`·`imua_record_file`을 옮기고, 기록이 있는 폴더를 `imua_record_source`(D-1 출력의 `<stem>_imua`)로 가리킨다.
- `run_record(..., record_key=)` 인자를 새로 더했다. 화면 4개가 키를 넘긴다(fix candidates는 `suite|id`).

### P-5: 모든 A형 줄의 기록 (새 모듈 `imua_records.py`)

- 줄 키 두 개
  - `imua_check_g5`: 확인 실행과 같은 함수(`imua_check_judge.g5_inputs`)로 계산한다. 개정 2 필드가 들어 있다.
  - `imua_record_file`: 자세 기록 파일 이름. 출력 옆 `<출력 stem>_imua/`에 쓴다.
- 기록은 T4h와 같은 꼴의 npz다(형식 `imua_attitude/1`). 배열 이름은 a2 T4h와 같다.
  - `t_s`, `phase`, `command_m_s`
  - `attitude_filtered_deg`, `attitude_true_rad`
  - `inclinometer_t_s`, `inclinometer_rad`, `attitude_true_at_inclinometer_rad`
  - `true_force_N`, `true_force_min_N`(T4h 참값 규칙 그대로)
  - `meta_json`: 형식, 태그, `imu_sensor`, F_min, 제어기 사건 전부, 줄 정체성
- 파일 이름은 `<키>_<정체성 해시 12자>.npz`라서 겹치지 않는다(식별 키 규칙 13).
- 쓰기는 배타적이다. 비어 있지 않은 기록 폴더는 거부한다(`--overwrite`를 줘도). `run_v5` resume에서는 기존 폴더를 허용한다.
- V0·VB·D-1·U-3·U-6 모든 줄에 붙는다. VB의 기존 T4h는 바꾸지 않았다.
- `run_v5`에서 A형은 `--out`이 필수다. 저장된 `v5/<batch>.jsonl`에 섞이지 않게 하려는 것이다.

### P-6: IND·IND_LAS

- `imu_a_harness.make_industry_class`가 C8 제어기 앞에 같은 경사계를 둔다.
  - C8 상수는 바꾸지 않았다.
  - `IndustryC8._update_filters`가 `imu_attitude_samples_rad`를 받으면 그 각도를 C8 자세 저역통과(0.8 s × 2)에 넣는다. C2 A형과 같은 방식이다.
- 메타 `imu_sensor`는 `industry_meta()`다. 게인 프리셋은 넣지 않는다.
- 주기 로그를 남기므로 IND 줄에도 G5 입력과 자세 기록이 붙는다.

### P-8: C-5 T4/T5 재생기 (`chrono_t45_replay.py`)

- A형 기록으로 보는 조건: `_IMUA` 태그와 `imu_sensor` 블록(`controller_meta`나 최상위)이 둘 다 있음.
- 설정을 다시 만들 때 A형 출력을 마지막에 적용한다: `ImuSetting.controller_config`(자세만, 탐침 단서 끔, D1′ explained, 프리셋 게인).
- 모니터 재생은 진단을 끈 채 two-pressure 설정만 읽는다(`contact_replay.replay_fallback_monitor` 문서). 그래서 경사계 자체를 다시 만들 필요가 없다.
- 받아들이는 기준은 기존 관문 그대로다: 설정 같음 + T4-0(재생 하한 = 기록 하한, 상대 1e-12).
- 거부(종료 2): 태그와 블록 중 하나만 있음, 모르는 프리셋, 프리셋과 다른 게인, `_IMUAR`, `_IMUATT-`, `_IDEAL-`.
- 하네스 `t4h_replay`는 지금처럼 `_IMUA`를 거부한다. P-8 범위 밖이다.

### P-7 일부

- `imua_classify.py`
  - E-2 서명 (i)~(vi). 배열이 없거나 창 안에 NaN이 있으면 평가 불가다.
  - E-1·E-3·E-4·E-5·E-6 서명.
  - 다섯 조건 결합. 4.2의 사유 순서를 따른다.
  - `controls` 명령: 4.2 끝의 양성·음성·합성·평가 불가 대조.
- `imua_identity_sample.py`
  - 모집단 4,064줄: D-1 868줄 22칸, U-3 2,228줄 18칸, U-6 968줄 4칸. 규칙 수와 다르면 종료 2.
  - 50줄 선정: 칸마다 1줄 + 6줄, 시드 20261114, D-1 키당 ε 하나. 정준 JSON의 SHA-256을 남긴다.

## 3. 검증

| 시험 | 결과 |
|---|---|
| 기본값(full IMU) 동작 보존 스모크: 화면마다 1키 + run_v5 d1 V0·VB = 9런(b5는 C2·ABL·IND 3런) | `2ea96c96`과 편집 후 두 번(편집 직후, HEAD `b0416724`)을 비교했다. 9런 모두 `commands_sha256`·`logged_commands_sha256`·태그가 같다. `_imua` 폴더는 생기지 않는다 |
| A형 스모크(같은 키, `v5_A`) | 10런 모두 오류 없음. 기대 태그 6종이 다 나왔다(V0 `final_C4G2_LAS_K1_IMUA`, VB·U-6 C2 `final_C4G2_P3_LAS_K1_IMUA`, `ABL_LAS_K1_IMUA`, `IND_IMUA`, `IND_LAS_IMUA`). 기록 10개, 각 기록의 참 자세 NaN은 마지막 1주기뿐 |
| 첫 A형 스모크의 결함 | `s9_soil_slope` 부모 프로세스에 `03_src` 경로가 없어 `file_meta`가 `ModuleNotFoundError`로 실패했다. `imu_a_harness`가 경로를 스스로 붙이게(append) 고친 뒤 D를 다시 돌려 통과했다 |
| 대상 회귀 (dynamics-dev, `-m "not slow"`, 18개 파일) | 524 통과, 0 실패, 34 skip, 17 slow 제외 |
| skip 재실행: `worktree_tests.py`(종료 1) | 94 통과, skip 0. 대상은 `test_chrono_t45_replay`(slow인 stage 3 rev7 18행 회귀 포함), `test_imua_check_judge`(19), `test_v5_setting_records`, 새 시험. 종료 1은 경고 2건뿐이다: probe 모듈 `imua_records`·`v5_rerun`을 그 시험 파일들이 import하지 않음. 원본 불변 True, status 줄 수 32 → 32 |
| HEAD에서 새 시험 + `test_imu_a_harness` | 56 통과(subprocess 끝까지 도는 시험 4개는 제외하고 돌렸다. 그 4개는 위 회귀·`worktree_tests` 실행에서 통과) |
| P-7 대조, 저장된 확인 실행 기록 | 13/13이 기대와 같다. 양성 5(A2 G5b), 음성 1 다섯 줄(R0), 합성 음성 2 한 줄(`leg_reapproach_start`), 평가 불가 2(A-v5) |
| 양성 대조 값 | 간격 0.6~2.1 s, 필터 0.0744~0.0776°, 탐침 변화 0.069~0.090°, 경사계 오차 ≤ 0.0153°, 최소 힘 66.3~74.1 kN. 규칙 초안의 A2 관측과 맞는다 |
| ruff / codespell | 새 코드 위반 0. 남은 E501 6건은 원래 있던 줄이다. codespell `ABL`(제어기 이름)은 오탐이라 거른다 |

- 남은 skip 10건(pychrono 없음): `test_v5_switch_tags` run_S9 기대 9건, `test_las_t3` run_S8C 1건. Chrono-dev 시험이다. 이번에 바꾸지 않은 Chrono 러너만 대상이라 검증 공백은 아니다.
- 커버리지(pytest 프로세스 안, 변경 줄 기준)
  - `imua_records` 92 %: 미커버 6줄
  - `imu_a_harness` 90 %: 1줄
  - `chrono_t45_replay`: 변경 줄 0줄 미커버
  - `u3_reuse`: 2줄(`_a_type_reuse_fields` 본문, 279~280행)
  - `run_v5`: 24줄(`run_one` A형 분기, `main`의 기록 폴더 준비)
  - `v5_rerun`: 20줄(`a_type_record` 본문, IND 태그)
  - `run_v5`·`v5_rerun`의 미커버 줄은 subprocess 워커에서 돈다. A형 스모크에서 실행은 확인했지만 pytest 커버리지로는 측정되지 않았다(검증 공백 아님, 측정 공백).
  - `u3_reuse` 279~280행은 A형 `--reuse-d1` 실행 경로다. 스모크도 돌지 않았다(검증 공백).

## 4. 동작 변경·공개 API 변경

- `chrono_t45_replay`
  - `_IMUA` 기록을 이제 재생한다(전에는 종료 2).
  - `STUDY_TAG_INFIXES`에서 `_IMUA`를 뺐다. 대신 `REFUSED_IMU_SUFFIXES = ("_IMUAR",)`를 두었다.
  - 새 공개 함수: `a_type_setting`.
- `v5_rerun`
  - `RerunOptions.imu`, `run_record(record_key=)`, `a_type_record`, `installed_imu`, `industry_class`를 더했다.
  - `options_from_args`·`split_argv`가 `V5_IMU_*`를 내보내거나 지운다.
- `run_v5`: A형은 `--out`이 필수다. 경사계 실행에서 `verdict_runs._finish`를 감싸 플랜트·제어기를 붙잡는다(기록만).
- `imu_a_harness`
  - import할 때 `03_src`를 `sys.path` 끝에 붙인다(없을 때만).
  - 새 함수: `make_industry_class`, `log_readings`, `a_type_setting_of`, `with_industry_imu_tag`, `ImuSetting.industry_meta`.
- `b5_baseline_compare.IndustryC8._update_filters`가 자세 표본을 받는다. 자세 표본이 없는 기본 경로의 결과는 같다(스모크로 확인).
- `u3_reuse.Plan`에 `d1_path` 필드를 더했다.

## 5. 남은 항목

| # | 항목 | 상태 |
|---|---|---|
| P-4 | TA(판정 도구 A형 모드 + `--allowed-src-changes`) | **미착수**. 두 경로 독립과 TA 기준 커밋 때문이다(6절 확인 필요 1) |
| P-7 | E-1(U-3)·E-2(D-1) 기대 건수 스크립트 | 미구현. stats 방법(`q2_sim.py`·`e1_oc.py`)과 436.8 H-1·H-3 저장 READY 값이 필요하다 |
| P-7 | `u3_neff.py` 수정(S-4) | 미구현. 6절 확인 필요 6 |
| P-7 | I-H 50줄 재실행 수단 | `run_v5` d1에 키 부분집합 인자가 없다(`--jobs-file`은 j9 배치 전용). U-3·U-6은 `--ids-from` 부분 파일로 된다 |
| P-7 | 분류 결합의 관문 ID 대응(4.4) | TA 판정 출력의 항목 이름이 정해진 뒤 상수로 고정한다. 지금 `classify`는 `gate_in_family`를 입력으로 받는다 |
| C-1 | Chrono 경로 | cad-expert 몫이다(7절 명세) |
| G-d | Chrono A형 가동 확인 1행 | C-1 뒤. P-8의 실제 기록 수용 시험도 이 행으로 한다 |

## 6. 확인 필요

1. **P-4 TA의 작성 방식과 기준 커밋**
   - (가) 두 경로 독립: TA의 (i) A형 판정 모드와 (ii) `--allowed-src-changes`는 경로 1 도구(`resume4368_judge.py` 등)와 경로 2 도구(`p2_*.py`) 양쪽을 고친다. 한 작성자가 두 경로를 다 쓰면 규칙 10에 어긋난다. rev26 T26처럼 경로별 새 인스턴스 둘이 필요하다.
   - 나는 이번에 경로 1 쪽 C-5 재생기(P-8)를 고쳤고 경로 1 C-5 판정기(`04_scripts/02_chrono/chrono_bundle_grade_4368.py`)를 Grep으로 열었다. 그러니 경로 2 작성자가 되면 안 된다.
   - (나) 기준: T26′ = `74c27846`(브랜치 `rev26-t26b`, 바탕 `932f1fb1`)이다. A형 실행 코드는 master `976aa771` 위의 `v5-imua`에 있다. `932f1fb1`..`976aa771` 사이에 `03_src`·`02_params` 6파일이 바뀌었다(판 5 코드). TA를 어떻게 만들든 `git diff T26..TA`에 그 차이가 들어간다. 그래서 초안 3.1 1항("T26..TA ⊆ A형 허용 집합")은 문언 그대로 충족할 수 없다.
   - 규칙 수정 11에서 TA의 정의(예: T26′과 `v5-imua` HEAD의 병합)와 허용 집합(실제 diff 목록을 파일로 고정 + 파일마다 비트 동일 근거)을 정해야 한다. 같은 성격인 G-b와 함께 정한다.
   - T26에는 이미 `--tag-mode`가 있다(R26-3). TA는 여기에 값 `imua`를 더하는 것으로 본다.
2. **P-5의 위치**
   - 초안은 "모든 줄에 T4h 자세 배열"이라고 쓴다. 구현은 T4h를 바꾸지 않고 형제 폴더 `<stem>_imua/`에 T4h와 같은 꼴의 기록을 따로 둔다. 436.8 판정기가 `<stem>_t4h/`를 훑기 때문이다.
   - 수정 11에 기록 위치와 키(`imua_record_file`, 재사용 줄의 `imua_record_source`)를 적어야 한다.
3. **E-2 정의에서 구현이 정한 부분**: 초안이 명시하지 않은 곳이다. 수정 11에서 채택하거나 고친다.
   - t_L 표본 = READY → LEVEL 뒤 첫 LEVEL 주기
   - t_D = t_R 전 마지막 DONE 진입
   - (iv)는 t_L ± 0.1 s의 모든 경사계 판독(21개)
   - (v)는 [t_R, t_L] 주기의 `true_force_min_N` 최소
   - 배열 없음 또는 창 안 NaN = 평가 불가
4. **P-6 해석**: "AttitudeEstimator 출력 대신 경사계 자세"를 "경사계 각도를 C8 저역통과(τ 0.8 s × 2) 입력으로"로 구현했다. 필터를 거치지 않고 경사계 값을 그대로 쓰는 해석이 맞다면 고쳐야 한다. control-expert 확인이 필요하다.
5. **`imu_sensor` 블록 비교 범위**: 실제 블록은 초안 1절 표(`{"model", "gains_preset"}`, IND `{"model"}`)의 상위집합이다(게인 수치, sensor, raw_imu, controller). TA 판정이 키 일부만 볼지 블록 전체를 볼지 정해야 한다.
6. **`u3_neff.py` 수정 위치**: 이 파일은 master의 stats 근거 폴더 `verif_matrix/v5paper_imua_stats/`(SHA256SUMS 있음)에 있다. 고치면 SUMS가 낡는다. 새 파일(예: `u3_neff_r2.py`)로 둘지, stats-design-expert가 할지 정해야 한다. E-1·E-2 기대 건수 스크립트도 방법 소유가 stats라 함께 정한다.
7. **경로 2 C-5 재생**: 경로 2 C-5 도구가 따로 T4/T5 재생을 하고 `_IMUA`를 거부하는지는 확인하지 않았다(두 경로 독립 때문에 열지 않음). 그렇다면 경로 2용 P-8을 경로 2 인스턴스에 맡겨야 한다.
8. **출력 이름 표(G-c) 제안**
   - H-1: `06_analysis/02_control/verif_matrix/v5paper_imua/run_<RA7>/h1_d1.jsonl`(+ `h1_d1_imua/`)
   - U-3·U-6: `06_analysis/02_control/v5_rerun/imua/<이름>.json`(+ `_imua/`). `check_out_path`는 `v5_rerun/` 바로 아래만 막으므로 하위 폴더는 허용된다.

## 7. 위임 필요(cad-expert): C-1 인터페이스 명세 (핸드오프)

- **인자**
  - `run_S8C`·`run_S9`에 `--imu-model {full,inclinometer}`(기본 full)와 `--imu-gains {study_Ag,v5_A,v5_A2}`를 더한다.
  - 경사계에는 프리셋이 필수다. 경사계 없는 프리셋은 거부한다. `imu_a_harness.add_arguments`·`setting_from_arguments`와 이름·선택지를 같게 한다.
- **제어기 설정**: 다른 설정을 모두 마친 뒤(프리셋 → engine fallback ratio → v5 옵션·③) **마지막에** `imu_a_harness.ImuSetting(model, gains).controller_config(config, rate_noise_std=0.0)`를 적용한다. P-8 재생기가 같은 순서로 다시 만든다.
- **태그**
  - `v5_options.with_switch_tags(..., config)`가 `final_C4G2_LAS_K1_IMUA` / `final_C4G2_P3_LAS_K1_IMUA`를 낸다.
  - `--expect-controller`는 이 문자열과 그대로 같아야 한다.
  - `controller_tag`(또는 `v5_hydraulics.controller_tag`)와 `c2_setup.expect_controller.name`에 같은 값을 기록한다.
- **센서**
  - `SensorSuite(..., attitude_sensor=AttitudeSensorConfig(AttitudeSensorKind.INCLINOMETER))`. 원시 IMU는 오차 없음(이상 등급, G-e): 필터·지연·분해능만.
  - 제어기는 `Measurements.imu_attitude_samples_rad`(10 ms × 10개 / 0.1 s)를 받는다. `pychrono.sensor`는 쓰지 않는다.
- **기록(`result.json`)**
  - `controller_meta.imu_sensor` = `ImuSetting.to_meta()` 그대로: `model`, `gains_preset`, `attitude_kp`, `attitude_ki`, `guard_kg`, `sensor`, `raw_imu`, `controller`.
  - 0이 아닌 GE1′ 잡음을 쓰면 `rate_noise_std` 키를 더한다.
  - P-8은 `model = inclinometer`, 아는 프리셋, 프리셋과 같은 게인을 요구한다. 어긋나면 종료 2로 멈춘다.
- **자세 기록(E-2 분류용)**
  - 사례 폴더에 `imua_attitude.npz`(형식 `imua_attitude/1`)를 둔다. 키는 `imua_records`와 같다: `t_s`, `phase`, `command_m_s`, `attitude_filtered_deg`, `attitude_true_rad`, `inclinometer_t_s`, `inclinometer_rad`, `attitude_true_at_inclinometer_rad`, `true_force_N`, `true_force_min_N`.
  - `true_force_*`는 `pads.npz`의 `F_pressure` / `F_pressure_min_interval`을 0.5 ms 규칙으로 맞춘 값이다.
  - `meta_json`: form, controller_tag, imu_sensor, F_min_N, 제어기 사건 (t, name) 전부.
- **수용 시험**
  - 인자 없이 짧은 강체 1행이 비트 동일.
  - 인자를 주면 메타 `imu_sensor` 확인.
  - G-d L2b 1행에서 `chrono_t45_replay`의 `settings_equal` 참 + `t4_0` 참.
- **환경**: Chrono-dev. dynamics-dev에는 pychrono가 없어 관련 시험 10건이 skip된다.

## 8. 메인 세션 권고 (봉인·실행 전 감사 뒤에만, 지금 띄우지 말 것)

- 줄 수(규칙 초안 2절): H-1 868, H-3 2,228(명령 18개), H-4 968(b5 명령 4개: wide C2·ABL·IND / wide IND_LAS / main 두 개), I-H 50.
- 명령 꼴: 436.8 `resume_k1_steps.u3_steps`·`u6_steps`·`run_v5_step`과 같고, 끝에 `--imu-model inclinometer --imu-gains v5_A`를 붙이며 출력만 6절 확인 필요 8의 이름으로 바꾼다.
  - H-1: `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B 04_scripts/04_hydraulic/coupled/run_v5.py d1 --workers N --mask <M> --out <H-1 출력> --imu-model inclinometer --imu-gains v5_A`
  - H-3 slope·h9의 `--reuse-d1`은 A형 H-1 출력을 가리킨다.
- 예상 시간 근거: 규칙 초안 추정(plan) 약 83 코어·h.
  - 이번 스모크 시간은 근거로 쓸 수 없다. A형 스모크는 4코어에 약 9프로세스를 몰아 돌렸다.
  - 혼자 돈 D 한 줄만 비교하면 full 58.8 s / A형 59.8 s다.
- 배치는 compute-scheduler-expert에 맡긴다. 러너 위치는 `~/.claude/runners/outrigger_control-v5paper-imua/`.

## 9. 공개 (연 파일·검색 범위·규칙 위반)

- **연 파일(Read)**
  - `imua_seal_prep/report.md`, `v5paper_imua_rules_draft.md`, `decision_log.md` 837행(scratchpad로 뽑아 읽음)
  - v5-imua의 `04_scripts`·`03_src`·`05_tests` 파일
  - main checkout `v5/imua_check_a2/evidence/a2_relevel.py`
- **Glob·Grep 범위**
  - v5-imua의 `04_scripts`·`03_src`·`05_tests`·`06_analysis/02_control/s9`(rev84·85 키 파일)
  - main checkout의 `v5/imua_check`, `v5/imua_check_a2` 폴더 목록, `verif_matrix/v5paper_imua_stats` 목록·머리글
  - 경로 1 C-5 판정기 `04_scripts/02_chrono/chrono_bundle_grade_4368.py`(Grep만)
- **읽은 데이터**: 확인 실행 T4h npz 12개(controls).
- **열지 않은 것**: `j_p3_cause/j9_runs/`, 판 8 경로 2 자료, 경로 2 도구(`p2_*`, `p2v5c_*`)는 Read·Grep·Glob 모두 하지 않았다.
- **규칙 위반 2건(노출 없음)**
  - Bash 파이프 1회: `git diff --name-only 932f1fb1 976aa771 -- 03_src 02_params | wc -l`. 결과는 "6", 끝났고 고아 프로세스는 없다.
  - scratchpad 밖 임시 파일 1회: `$env:TEMP\x.py`(HEAD판 `v5_rerun.py`를 ruff로 비교하려던 것)를 쓰고 곧바로 지웠다.
- **scratchpad**: `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\c52f3f13-1809-41e7-8ed4-76fbbd933dd2\scratchpad\python-imua\`에 근거를 남겼다. 3절 근거라 지우지 않았다.
  - 스모크 출력 `smoke_before`·`smoke_after`·`smoke_after2`·`smoke_after3`·`smoke_imua`·`smoke_imua2`
  - 비교 파일 `digests_before.json`·`digests_after3.json`·`digests_imua.json`
  - `controls1.json`, `ih_sample.json`(후보 sha `29d451b1…`, 봉인 때 실행 커밋에서 다시 만든다), `wtt_report.md`, `junit_p2p8.xml`, `regress_p2p8.log`, `cov_p2p8.json`
  - 스크립트 `smoke.ps1`·`digests.py`·`regress.ps1`·`changed_cov.py`

## 10. 메모리 반영안

- `C:\Users\jinbeom\.claude\agent-memory\python-expert\tool_parent_side_path_setup.md`(새로, MEMORY.md 색인 한 줄): 부모 프로세스에 새로 넣은 코드가 소스 경로가 없는 CLI 하나에서만 실패할 수 있다. 진입 CLI마다 스모크하고, 스모크 도중에는 소스를 고치지 않는다.
