# 논문 v5 A형 IMU 구현 재개 2 보고 (python-expert, 2026-11-28)

- 근거 규칙: `verif_matrix/v5paper_imua_rules_draft_r11.md`(수정 11). 사용자 결정 Q-U5(블록 전체 비교), Q-U6(E-2 정의 수정 2건), Q-U3(H-12 해당 없음), 기록 위치는 2.2절.
- 범위: 아래 (1)~(4)만 했다. 하지 않은 것: P-4 TA(경로별 새 인스턴스 몫), 기대 건수 스크립트, u3_neff(stats 결정 대기).
- cad-expert의 C-1 진행 파일은 열지도, 고치지도, 커밋하지도 않았다: `04_scripts/02_chrono/run_S8C.py`, `run_S9.py`, `imua_chrono.py`, `05_tests/unit/test_imua_chrono.py`.
- 사용한 스킬: 없음

## 1. 커밋

- `32ed04fc`(브랜치 `v5-imua`, 부모 `b0416724`, master 미병합)
  - 내 파일 6개만 스테이징했다: `imua_classify.py`, `imua_expected_sensor.py`(새로), `imua_records.py`, `u3_reuse.py`, 시험 2개.
  - worktree에 남은 미커밋 변경은 cad-expert의 C-1 파일 4개뿐이다.
- 새 파일은 커밋 전에 CRLF로 맞췄다.

## 2. 한 일

### (1) `imua_classify.py`를 수정 11 4.2.1에 맞춤

- (iv): t_L ± 0.1 s 창 안 경사계 판독 수 n이 정확히 21이어야 한다. 아니면 평가 불가다. 값 기록에 `n_inclinometer_readings`를 남긴다.
- (vi): t_L + 0.5 s가 기록 마지막 주기 `t_s[-1]`보다 뒤면(1e-9 s 허용) 평가 불가다. 값 기록에 `t_end_s`를 더했다.
- 나머지 정의는 4.2.1이 "채택"으로 둔 그대로다: 대상, t_R·t_L·t_D, (i)·(ii)·(iii)·(v).
- 시험을 더했다.
  - 판독 하나를 빼면 n = 20 → 평가 불가
  - 기록이 t_L + 0.4 s에서 끝나면 평가 불가
  - t_L + 0.5 s가 마지막 주기와 같으면 평가 가능(성립)
- P-7 대조를 다시 돌렸다. 저장된 확인 실행 기록에서 **13/13 기대대로**다.
  - 양성 5 성립: n = 21, `t_end_s`는 t_L보다 9.4~9.9 s 뒤
  - 음성 1 다섯 줄: 대상 아님
  - 합성 음성 2: (vi)에서 불성립
  - A-v5 2줄: 평가 불가(배열 없음)
  - 값은 `b0416724` 때와 같다. 근거: `impl_resume_2_evidence/p7_controls_r11.json`

### (2) 2.2절 기록 위치·키 대조

- 구현과 다른 곳은 없다.
  - 형제 폴더 `<stem>_imua/`, 형식 `imua_attitude/1`, 이름 `<표지>_<SHA-256 12자>.npz`, 배타 쓰기
  - 배열 이름, 묶음별 키 위치(run_v5는 최상위, 화면은 `v5` 블록)
  - 재사용 줄의 `imua_record_source` = H-1 기록 폴더 이름. 아래 (4) 스모크에서 `h1_d1_imua`로 확인했다.
- `meta_json`에는 2.2절 키(`form`, `identity`, `controller_tag`, `imu_sensor`, `F_min_N`, `events`) 말고 기록용 키 3개가 더 있다: `attitude_record_rule`, `true_force_rule`, `has_plant_rows`. 상위집합이다.
- 판정·분류가 쓸 2.2절 규칙 함수를 `imua_records`에 더했다.
  - `locate_record(result_path, block, h1_result_path=)`: 자기 폴더에서 찾고, 재사용 줄이면 `<H-1 결과 폴더>/<imua_record_source>/<file>`로 푼다.
  - `record_status`: `complete` / `missing` / `tag_mismatch` / `keys_absent`.
- `u3_reuse`가 문자열 대신 그 상수(`RECORD_SOURCE_KEY`)를 쓰게 바꿨다.

### (3) `imua_expected_imu_sensor.json` 생성 스크립트 (`04_scripts/04_hydraulic/coupled/imua_expected_sensor.py`)

- 칸
  - `harness_c2` = `ImuSetting("inclinometer", "v5_A").to_meta()`
  - `harness_ind` = `industry_meta()`
  - 둘 다 JSON 값으로 바꿔 저장한다. 블록 전체 비교용 함수 `blocks_equal`을 함께 둔다(키 순서 무관).
  - `chrono_c2`는 `null`, `chrono_c2_status`는 `"pending C-1"`(자리만).
- `--chrono-result <C-1 사례>/result.json`을 주면 그 기록의 `controller_meta.imu_sensor`를 넣는다. 받는 조건은 1.1절 그대로다: `harness_c2`와 `raw_imu`에서만 다르고 `rate_noise_std` 키가 없어야 한다.
- 함께 기록하는 것: checkout HEAD, `is_clean`(git이 실패하면 `null`), 스크립트 LF sha.
- 종료 코드: 0 기록 / 1 Chrono 블록 불일치(아무것도 쓰지 않음) / 2 입력 오류(이미 있는 `--out` 포함) / 3 도구 오류.
- 후보 파일: `impl_resume_2_evidence/imua_expected_imu_sensor.candidate_32ed04fc.json`.
  - HEAD `32ed04fc`, `is_clean` false다. cad-expert 미커밋 파일 때문이다.
  - 봉인용 파일은 1.1절대로 RA checkout에서 다시 만든다.

### (4) A형 `--reuse-d1` 경로 스모크 (지난 보고의 검증 공백 `u3_reuse` 279~280행)

- 입력
  - D-1 A형 2줄(V0, ε 0): `D1|H-S-0|G1|T|flat|K1`, `D1|H-S-0|J1|T|flat|K1`. run_v5 `main`에 batch_jobs만 바꾸는 구동기(`reuse_smoke/d1_subset.py`)를 썼다.
  - U-3 slope V0 2키(`H1|G1|B|top|flat`, `H1|J1|B|top|flat`): `--reuse-d1`, `--imu-model inclinometer --imu-gains v5_A`
- 결과(`reuse_smoke/check_reuse.out.txt`)
  - G1은 표본 키로 U-3 경로에서 돌았다. 기록 명령 해시가 D-1 줄과 같았다: `8f9cba86…`.
  - J1은 `reuse: "d1"`로 재사용됐다. 함께 확인한 것:
    - 태그 `final_C4G2_LAS_K1_IMUA`, `imu_sensor` v5_A, G5 있음
    - `imua_record_source = "h1_d1_imua"`
    - 기록을 H-1 폴더로 풀면 `complete`(`meta_json.controller_tag`가 줄 태그와 같다)
  - 두 실행 모두 종료 0, 오류 줄 없음.

## 3. 검증

| 시험 | 결과 |
|---|---|
| 커밋 전 대상 시험(dynamics-dev, `-m "not slow"`): `test_imua_*` 5개, `test_imu_a_harness`, `test_s9_slope_fix_candidates`, `test_v5_rerun` | **199 통과, 0 실패, skip 0**(`junit_precommit.xml`, `junit_skips` 종료 0). `IMUA_DATA_ROOT` = 메인 checkout이라 저장 자료 대조 시험도 skip 없이 돌았다 |
| ruff(`--no-cache`), codespell | 바꾼 파일 위반 0. codespell은 `abl`(제어기 이름) 오탐을 걸렀다 |
| P-7 대조 | 13/13 기대대로(위 (1)) |
| `--reuse-d1` 스모크 | 위 (4) |

- 커버리지는 이번에 다시 재지 않았다. 지난 보고의 미커버 2줄(`u3_reuse` 279~280행)은 위 스모크의 부모 프로세스에서 실행됐다.
- 근거 폴더: `C:\workspace\outrigger_control\06_analysis\02_control\imu_attitude_only\imua_seal_prep\impl_resume_2_evidence\`
  - `p7_controls_r11.json`
  - `imua_expected_imu_sensor.candidate_32ed04fc.json`
  - `junit_precommit.xml`
  - `reuse_smoke/`: 구동기, 키 파일, 출력, `_imua` 기록, 콘솔 로그, 점검 스크립트와 출력
  - `SHA256SUMS`: `baseline_check write-sums --recursive`, 15항목, sha `46729664…`. 근거 폴더에 파일을 더하면 다시 써야 한다.

## 4. 동작 변경·공개 API 변경

- `imua_classify.e2_signature`: (iv)·(vi) 조건에 걸리면 평가 불가를 낸다. 결과 값에 `t_end_s`가 더해졌다. 나머지 판정은 같다.
- 새 공개 함수·상수
  - `imua_records.locate_record`, `record_status`, `RECORD_SOURCE_KEY`
  - `imua_classify.E2_INCLINOMETER_READINGS`
  - 새 스크립트 `imua_expected_sensor.py`
- 기본(full IMU) 경로에 닿는 변경은 없다. 바꾼 파일은 분류·기록 헬퍼와 `u3_reuse` 상수 참조뿐이다. 그래서 기본값 동작 보존 스모크는 다시 돌리지 않았다.

## 5. 확인 필요

1. 2.2절 `meta_json` 키 목록에 구현의 기록용 키 3개(`attitude_record_rule`, `true_force_rule`, `has_plant_rows`)를 더 적을지, "상위집합 허용"으로 둘지 정해야 한다. 지금 구현은 상위집합이다. 판정 쪽이 `meta_json`을 키 집합 전체로 비교하면 결정이 필요하다.
2. 봉인용 `imua_expected_imu_sensor.json`을 만드는 인터프리터. 블록 값은 env와 무관하지만, 실행 기록과 맞추려면 dynamics-dev `python.exe -I -B`로 만들 것을 권한다. 후보는 python-dev로 만들었다.

## 6. 위임 필요

- (cad-expert) C-1 명세는 지난 보고 7절 그대로다. 덧붙일 것 하나: C-1 기록이 생기면 `imua_expected_sensor.py --chrono-result <사례>/result.json`이 종료 0이어야 한다. 이것이 `raw_imu` 외 키 일치를 확인하는 수용 시험이다.
- (경로별 새 인스턴스) P-4 TA. 나는 경로 1 C-5 재생기를 고쳤으므로 경로 2를 맡을 수 없다.
- (stats-design-expert) E-1·E-2 기대 건수, `u3_neff`(Q-S1).

## 7. 공개 (연 파일·검색 범위·규칙)

- **연 파일**
  - `v5paper_imua_rules_draft_r11.md`: 76~240, 537~606, 690~739행
  - v5-imua의 `imua_classify.py`·`imua_records.py`·`u3_reuse.py`와 시험 파일
  - 확인 실행 T4h npz 12개(controls)
- **Grep**: `v5paper_imua_rules_draft_r11.md` 제목만.
- **git(Bash)**: worktree의 `status`·`log`만.
- 위반은 없다.
  - Bash 파이프, heredoc, `python -`는 쓰지 않았다.
  - `j9_runs`, 경로 2 도구, cad-expert의 C-1 파일은 열지 않았다.
  - 종료한 프로세스는 없다. 내 스모크 PID만 기다렸다.
- 스모크 출력은 프로젝트 근거 폴더에 직접 썼다(지시대로).
- scratchpad `python-imua\`에 남은 것: 커밋 메시지 `msg4.txt`, 구동기 원본 `d1_subset.py`(근거 폴더에 사본). 지난 작업분도 그대로다.
