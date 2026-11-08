# J1 흙 점성 R 감도 열린 루프 Chrono 3행 (`V5-OPENLOOP-R`) — 행 정의와 판정 항목

- 작성: cad-expert, 2026-11-08. **정의만 했다. 실행은 사용자 승인 대기다.**
- 목적: 1.7절(F-6)의 후방 골 기구 가운데 "후방만 닿은 동안 크롤러 앞쪽이 SCM 점성 항 $R\dot z$로 시간 기준 크리프를 한다"는 몫이 R에 얼마나 민감한지 본다(`v5_paper_runs_judgement.md` 1.6·1.7절, `prop_dip_*.json`).
- 행 정의 코드: `04_scripts/02_chrono/s9_batch.py` `v5_openloop_r_rows`(묶음 `V5-OPENLOOP-R`). 시험: `05_tests/unit/test_v5_paper_rows.py::test_openloop_r_rows_add_only_the_soil_damping_override`.

## 1. 기준 행과 바꾼 것

| 항목 | 값 |
|---|---|
| 기준 행 | 저장 `07_results\S9\batch_V5-OPENLOOP-V0_20261108_123517\P3a_J1_B_V0`(v4 `batch_P3a_20261026_092653\P3a_J1_B`와 `series.npz` 비트 동일, 1.1절) |
| 기준 argv | `run_S9.py machine --soil J1 --pad-variant dwg_rear250 --grid 0.01 --crawler-grid 0.04 --settle-dashpot zrp --lift-s 28 --level top --threads 4 --abort-on-limit` |
| 바꾼 것 | 끝에 `--soil-override damping_R=<R>`만 붙인다. `run_S9 load_inputs`가 J1 세트의 `chrono.damping_R`을 바꾼다. 이 실행의 SCM 지형은 하나다(`--soil-patch` 없음). 그래서 네 패드와 크롤러 모두에 같은 R이 들어간다 |
| 기존 경로 | `--soil-override KEY=VALUE`는 이미 있었다(`run_S9.py` 5994행, `_soil_overrides` 2362행, `scm_model.load_soil_set` overrides). run_S9는 고치지 않았다 |
| 기록 | `result.json` `meta.scm.soil.chrono.damping_R`, `soil.overrides`, `SetSoilParameters.damping_R`(기준 행 992000.0으로 확인) |
| `check-sources` | 세 행 모두 `ok_expected_diff`. 차이는 `soil_override` = `['damping_R=<R>']` 하나다 |

Chrono 근거(chrono-rag, PyChrono 10.0.0): `SCMLoader::ComputeInternalForces`가 `m_damping_R`을 읽는다(`src/chrono_vehicle/terrain/SCMTerrain.cpp:1394`). 법선 응력에 $-V_n R$을 더하고 자르지 않는다(1459~1465행, `scm_soil_sets.json` `chrono_source_checks.normal_law`). `SetSoilParameters`가 자르는 값은 `elastic_K`뿐이다(148~165행). 그래서 R은 그대로 들어간다.

## 2. 행 표

| 행 | `damping_R` [Pa·s/m] | J1 기준 대비 | 출처 | 행 메타 |
|---|---|---|---|---|
| `P3a_J1_B_V0_R888k` | 8.876×10⁵ (`damping_R=887600`) | 0.8948 | 9.92×10⁵ × 0.8948(VB 공급 비, 지시값) | `soil_damping_R_Pa_s_m`, `soil_damping_R_base_Pa_s_m` 992000, `soil_damping_R_ratio` |
| `P3a_J1_B_V0_R600k` | 6×10⁵ | 0.6048 | J1 `sensitivity.damping_R_Pa_s_m`(Lysmer 유사 Vs 200 m/s) | 같음 |
| `P3a_J1_B_V0_R300k` | 3×10⁵ | 0.3024 | 같은 감도 목록(Vs 100 m/s) | 같음 |

공통 메타(`batch.json` 행에 복사): `threads` 4, `run_env` {`OMP_WAIT_POLICY`: `PASSIVE`}, `planned_pool` pcore, `source_run`, `pair_case` `P3a_J1_B_V0`, `v5_setting` `V0_R…`.

- `run_env`는 s9_batch가 자식 프로세스 환경에 넣는다(`_case_env`). 이 키가 없는 행은 그대로다. 실행 셸에도 같은 값을 둔다.
- 기준 행은 PASSIVE를 결과에 기록하지 않았다. 메모리 규칙(SCM PASSIVE 비트 동일, 2026-11-08 실측)에 따라 같은 조건으로 본다(**가정**).
- J1 기준 R 9.92×10⁵의 근거는 `basis_R`이다(크롤러 탄성 heave 가지에서 ζ 0.2). 바꾼 값들은 이 가정의 감도다.

## 3. 비용

- 기준 행 실측: 실행 시계 2,176.7 s, 배치 시계 2,214.6 s(P, 2슬롯, 6.05 ms/스텝, 360,000 스텝).
- 행 추정 `est_s` 2,215 s(P), E 2,769 s(×1.25, **가정**). R은 스텝 수를 바꾸지 않는다. SCM 비용은 마디·광선이 정한다. 그래서 같은 비용으로 잡았다(**가정**).
- 3행 P 3슬롯 동시면 약 2,215~2,700 s, 2슬롯이면 약 4,430 s다(P 3슬롯 × 4스레드 = 12 논리 코어. 2슬롯보다 느려질 수 있다. 배치표는 compute-scheduler-expert가 낸다).
- `--threads`가 다르면 결과 비트가 달라진다. 그래서 4를 바꾸지 않는다.

## 4. 판정 항목 (dynamics-expert 권고 항목, 값 판정은 dynamics-expert 몫)

모두 기준 행 V0과 같은 정의로 `series.npz`에서 계산한다. 정의는 `paper_runs/scripts/prop_dip_timebase.py`·`prop_dip_crawler.py`·`openloop_compare.py`의 `analyse`를 그대로 쓴다. 이 스크립트들은 `RUNS`를 코드에 박아 두었다. 그래서 R 행 3개를 더한 비교 스크립트가 필요하다(실행 뒤 작성).

| # | 항목 | 정의(시각은 절대 시각 t, 들어 올림 시작 8 s) | V0 기준값 | 출처 |
|---|---|---|---|---|
| R-1 | 이륙 전 후방 최소 $F_a$와 시각 | RL / RR 실린더 힘의 크롤러 이륙 전 최솟값과 그 시각(전방 접지 기준 상대 시각도) | 11.66 / 11.73 kN, 전방 접지 +0.0704 s | `prop_dip_timebase.json` V0 `F_rear_min_kN`·`t_min_rel_front_contact_s` |
| R-2 | 전방 접지 순간 후방 힘 | 전방 접지 표본 $k_f$에서 RL / RR 힘 | 17.82 / 17.71 kN | 같은 파일 `F_rear_at_front_contact_kN` |
| R-3 | 전방 하중 이동 골 깊이 | R-1 최솟값 − R-2 값 | −6.16 / −5.98 kN | `dip_from_front_contact_kN` |
| R-4 | 크롤러 앞끝 침하(시간 기준) | 후방 접지 뒤 +0.04 / 0.08 / 0.10 / 0.12 / 0.14 s의 크롤러 앞끝 Δz, 0.06~0.14 s 침하 속도 | +0.14 s −0.559 mm, −7.22 mm/s | `by_time`, `crawler_front_sink_rate_mm_s_0p06_0p14` |
| R-4b | 후방→전방 접지 간격 | 시각 차, 명령 행정 차 | 0.148 s(24.2985 → 24.4466 s), 3.10 mm | `t_rear_contact_s`, `t_front_contact_s`, `contact_gap_sref_mm` |
| R-4c | 전방 접지 전 후방 피크 | RL / RR 최댓값(후방 접지~전방 접지) | 18.96 / 18.87 kN | `rear_peak_before_front_kN` |
| R-5 | 후방 패드 하중 상실 | (a) R-1 < $F_{min}$ 9.415 kN이면 FLAG(명세 11047, 열린 루프 기록). (b) RL / RR SCM 패드 법선 힘이 0이 되는 표본이 있으면 하중 상실로 기록(시각·길이) | (a) 없음(+2.25 / +2.32 kN 여유), (b) 없음 | 1.2절 |
| R-6 | 정착 상태 차이 | 끝 침하 FL / FR / RL / RR, 이륙 시각, 이륙 뒤 크리프, 크리프 정지 시각(모든 패드 1 s 침하 속도 < 0.1 mm/s), 끝 Δroll / Δpitch, 힘 피크 비, 최대 $s_{motor}$, P3a-1~5, 종료 코드 | 61.9 / 48.9 / 89.7 / 77.8 mm, 이륙 +19.086 s, 크리프 정지 이륙 뒤 4.05 s, −0.288 / −0.271°, 0.431, 580.0 mm, 통과 / 0 | 1.2절 표 |

- 단위 함정: `prop_dip_timebase.py`의 `F_rear_at_front_contact_kN`·`F_rear_min_kN`은 키 이름과 달리 **N**으로 저장돼 있다(52~53행, `/1e3` 없음). 위 표는 kN으로 환산한 값이다. 새 비교 스크립트에서는 kN으로 맞춘다.
- 정적 평형 점검: 끝 0.1 s 창 `equilibrium_rel_error`. 기준 4.3×10⁻⁶이고 기준은 ≤ 1 %다.
- 기대 방향(R을 낮추면 R-4 침하 속도와 R-1·R-3이 어떻게 바뀌는가)은 정하지 않았다. 사전 예측은 dynamics-expert가 실행 전에 적는다.

## 5. 실행 명령 초안 (승인 뒤, G-D 비용 측정이 끝난 뒤)

```powershell
$env:OMP_WAIT_POLICY = 'PASSIVE'
& C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I -X utf8 -u `
  C:\workspace\outrigger_control\04_scripts\02_chrono\s9_batch.py check-sources V5-OPENLOOP-R
& C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I -X utf8 -u `
  C:\workspace\outrigger_control\04_scripts\02_chrono\s9_batch.py run V5-OPENLOOP-R --parallel 3
```

- 슬롯 수(2 또는 3)는 compute-scheduler-expert 배치표를 따른다. 30분 넘게 CPU를 쓰므로 `reserve.py add`로 등록한다.
- 출력: `07_results\S9\batch_V5-OPENLOOP-R_<stamp>\P3a_J1_B_V0_R{888k,600k,300k}`.
