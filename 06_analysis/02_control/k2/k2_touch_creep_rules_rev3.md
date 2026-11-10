# K-2 규칙 덧붙임 rev3 (결과 전, 2026-11-10)

- 작성: control-expert, 2026-11-10. 봉인 정보는 같은 폴더의 `k2_touch_creep_rules_rev3.sha256`.
- 원판(`a3658197…7263`), rev1(`5ba081c6…4776`), rev2(`b3f1b41f27030c75aec726d2a3feb5abc36697864e0d83766a8fe0c4460394ea`)를 고치지 않고 아래만 덧붙인다. 다르면 rev3 > rev2 > rev1 > 원판 순으로 맞다.
- 시점: V-1~V-7 결과 0건. 경로 2를 rev2에 맞게 고치다가 발견했다. rev2 4절 표의 대조 기준 값이 반올림 표기라, rev2가 정한 "상대차 ≤ 1e-9"로는 맞는 행도 판정 불가가 된다. 그래서 대조 기준을 실행 YAML에서 계산한 값으로 바로잡는다. 판정 항목과 문턱은 바뀌지 않으므로 등급 영향은 없다.

## 1. rev2 4절 V-3 E-5 대조 기준 (대체)

- 대조 대상: 행의 `k2.aug.plant_aug`(KPlant 기록: `preset`, `options`, `resolved`).
- 기준 값: **실행 checkout(`6a44ff8`)의 `02_params/rexome33.yaml`에서 같은 식으로 계산한 값**이다. 상대차 ≤ 1e-9, 0이면 절대차 ≤ 1e-12로 대조한다. rev2 표의 0.233093·2.0924e-3은 이 값을 반올림한 표기다.

| 양 | `resolved` 키 | 기준 값(YAML 계산, 2026-11-10 확인) | 식 |
|---|---|---|---|
| 크롤러 kt/kn 배수 | `crawler_kt_rel` | 0.23309250561413625 | `contact.rigid_floor.L1`의 `kt_per_pad_N_m / kn_per_pad_N_m` 평균 |
| $F_s$ 전방 | `seal_fs_front_N` | 4000.0 | 공칭 |
| $F_s$ 후방 배수 | `seal_fs_rear_scale` | 0.8333 | `actuator.seal_friction.rear_scale` |
| 이동 중 축 감쇠비 | `pad_zeta_moving` | 0.10 | 명세. `cn_moving_N_s_m` = `cn_lock_N_s_m` × 0.10/0.03 |
| 열림 문턱(AUG_eps) | `valve_open_eps_m_s` | 0.00209243016 | 0.1 × `actuator.max_speed_m_s` |
| 열림 문턱(그 밖, 감쇠 팔) | `valve_open_eps_m_s` | 1e-6 | `actuator.rod_side.lock_eps_m_s` |
| 크롤러 c 배수(AUG_crc2) | `crawler_c_scale` | 2.0 | 명세 |

- **팔별 기대 키 집합(`options`)**: 키 집합이 같아야 한다(빠진 키·더 있는 키 모두 판정 불가).

| 팔 | `preset` | `options` 키 |
|---|---|---|
| H0 | `none` | `options == {}` |
| L1eq | `l1eq` | `crawler_kt_rel` |
| L1eq_fs | `l1eq_fs` | `crawler_kt_rel`, `seal_fs_front_N` |
| L1eq_zm | `l1eq_zm` | `crawler_kt_rel`, `pad_zeta_moving` |
| AUG | `aug` | `crawler_kt_rel`, `seal_fs_front_N`, `pad_zeta_moving` |
| AUG_crc2 | `aug_crc2` | AUG + `crawler_c_scale` |
| AUG_eps | `aug_eps` | AUG + `valve_open_eps_m_s` |

- `resolved`의 값은 위 표와 같아야 한다. 값은 `options`에 있는 양만 본다. 다만 `valve_open_eps_m_s`는 모든 팔의 `resolved`에 있다(H0도 1e-6).
- 그 밖: `k2.aug.arm` = 팔 이름, `k2.aug.is_kplant` = 참.
- I-9(rev2 4절)의 V-3 열림 비율은 `k2.aug.valve_open_fraction_touch_to_lift`(길이 4 목록)다. V-6 L1은 `k2_row.json`의 `valve_open_fraction_touch_to_lift`(다리 4개 사전)다.

## 2. rev2 4절 V-6 E-5 키

- `k2_row.json`의 `moving_damping`과 `pad_zeta_moving`을 본다. L1 4행은 `moving_damping` 참이고 `pad_zeta_moving` = 0.10이다. L2b 4행은 `moving_damping` 거짓이고 `pad_zeta_moving`은 None이다.
