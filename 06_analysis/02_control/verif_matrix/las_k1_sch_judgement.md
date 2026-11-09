# LAS-b K1 S-Ch 판정서 (Chrono SCM 패치 1키)

- 작성: control-expert, 2026-11-09
- 상태: **판정 후 감사 반영판(차단 0, 기록 6, 재집계 일치).** 이 판은 감사 기록에 따라 문구만 고쳤다. 판정 등급과 수치는 그대로다.
- **최종 판정: `통과`**(판정 도구 `status` `pass`, 종료 코드 0, `grade_word` "통과").
  - `stop`·`미달`·`incomplete` 사유가 모두 빈 목록이다. FLAG도 두 행 모두 0건이다.
  - K1은 계획대로 작동했다. decision 1건, `would_block` 참. gateoff는 R4c30을 적용했고 gateon은 막았다.
- 두 경로 재집계 결과는 같다(8절). 115항목에서 불일치 0, 수치 최대 차 0.0이다. 단 E-6a 창 경계 해석 1건은 맞춘 뒤 같아졌고, 그 사실을 8절에 공개한다.
- 사전 예측 중 **Q-C1의 dP 1항목이 범위 밖**이다: 예측 [−12, −1], 관측 **−20**. 예측은 판정 기준이 아니다(원판 5.0.1). 공개와 해석은 4절에 있다.
- K1 채택(프리셋 기본 켬, 새 태그)과 LAS-b P5r4 처리는 **사용자 결정 사항**이다(원판 9절, 계획 9절). 선택지와 권고는 10절에 있다.
- 규약
  - 제어: 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1, C2 음되먹임($u$ = 다리 행정 속도 명령 [m/s])
  - 행정은 모터 행정 [m]이고 표에서는 mm로 적는다. 힘은 실린더 순 힘 또는 SCM 법선력 [N]이다.
  - 시각은 Chrono 절대 시각 [s]이다(정착 8 s 뒤 폐루프 시작, 끝 208 s). 시각 비교는 $n = \mathrm{round}(t/T_s)$ 정수 주기로 한다.
  - 이름 구분: 하네스 키의 `K1`은 크롤러 강성 ×1이다. 순서 관문은 `k1_candidate`(`K1off`·`K1on`)와 `--k1-order-gate`(`off`·`on`)로만 부른다.

| 기호 | 뜻 | 단위 |
|---|---|---|
| $t_P$, $n_P$ | 이번 LOC를 확정한 S-1 평탄 창 꼬리의 첫 표본 시각(`soil.plateau_start_s`), 그 주기 | s, 주기 |
| $t_S$, $n_S$ | LOC 시점의 가장 최근 토양 모드 시작 시각, 그 주기 | s, 주기 |
| dP | $n_P - n_S$. K1은 dP ≤ 0이면 R4c30을 막는다 | 주기 |
| $t_{LOC}$, $n_{LOC}^{K}$ | gateoff의 K1 작동 LOC 시각, 그 주기 | s, 주기 |
| $s_{max}$ | 네 다리 1 ms 모터 행정 최대 중 최대 | m |
| $F_{min}$ | 이탈 뒤 네 다리 실제 실린더 힘 최소 | N |

## 0. 규칙·실행 정체성·파일

### 0.1 규칙·계획

| 파일 | sha256 | 봉인 시각 | 봉인 커밋(커밋 시각) |
|---|---|---|---|
| 원판 `las_k1_rules.md` | `2742c9760ad55a87eccbf73e84025aafe0171a3555e1f54ab19fab24d888e4a0` | 16:24:49 | `ea524f0`(16:25:47) |
| rev1 `las_k1_rules_rev1.md` | `eeee4ab9661babff50117b8ff579aa41e27a98d083f1fc13f46fb5c733e0b4d3` | 17:13:20 | `62fb8d7`(17:13:52) |
| 보충 계획 `las_k1_sch_plan.md` | `b0fe744feca6fd2e2b792a0c000e08c18eb1005f30278d1d0eeaeb2f40d46d9d` | 19:06:08 | `9df5743`(19:07:17) |
| 계획 rev1 `las_k1_sch_plan_rev1.md`(**결과 전**) | `d8f957cbedd39ffec5bc36127dc3a2ec91e1d71335a464ba370dd87643069295` | 19:25:17 | `286556d`(19:26:15) |

- 모든 시각은 2026-11-09, +09:00이다.
- 계획 원판은 19:05:07에 한 번 봉인했다(`802e1643…`). 커밋 전에 판정서 행과 HEAD 주석만 고쳐 다시 봉인했다(원판 첫머리에 공개). 유효한 봉인은 `b0fe744f…` 하나다.
- 네 파일의 sha256을 판정 도구(K-0j)와 경로 2가 지금 각각 다시 계산했고, 모두 봉인 값과 같다.

### 0.2 실행 정체성 (두 행 같음)

| 항목 | 값 | 근거 |
|---|---|---|
| 실행 HEAD | `0c779e67c71bb2fbb08372df044b112bc9ed2ee5`(두 행, `code_state.git_at_start.head`. batch.json 대체 없음) | K-0a |
| 코드 diff | `git diff --quiet 92d22e0 0c779e6 -- 03_src 02_params 04_scripts` 참(rc 0, 경로 2도 다시 실행) | K-0a, rev1 R1-1 |
| dirty | 두 행 빈 목록. prelaunch·postrun `git status` 0줄(허용 목록 빈 목록, rev1 R1-2) | K-0b, K-0d |
| 코드 sha 7개 | 아래 표. 작업 트리 원시(CRLF)와 HEAD blob(LF)이 모두 봉인 값과 같다(prelaunch = postrun) | K-0c, K-0d |
| DLL | `chrono_hull_hook.dll` `cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15`, 69,632 B, `dll_sha_validated` 참 | K-0d, K-0e |
| hull hook effective | result.json `mode` `fast`, `requested` `fast`, `fallback_reason` None. batch.json `hull_hook_effective.mode` `fast`, `mixed_hull_mode` 거짓, progress.log `MIXED_HULL_MODE` 0줄. 행당 호출 11,440,394회, 대체 계산 97회 | K-0e |
| threads | `args.threads` 4, `num_threads_chrono` 4 | K-0f |
| OMP | batch.json `omp_wait_policy` `PASSIVE`, `start_env` `{OMP_WAIT_POLICY: PASSIVE, OUTRIGGER_HULL_HOOK: fast}` | K-0f |
| placement | `pcore`, `affinity_ok` 참, `power_throttling_off_ok` 참, 논리 프로세서 0~15. batch.json `pool` `pcore` | K-0f |
| 인자 | result.json `args`의 다른 키 = {`case`, `k1_order_gate`}. batch.json `argv`(59토큰, 길이 같음)의 차이는 인덱스 58(0부터 셈)의 `--k1-order-gate` 값(`off`→`on`) 하나뿐이다. argv에는 `--case`가 없고, `case`는 result.json `args`에서만 다르다. 고정값 9개(seed 20261026, normal, ideal, 4.0, 200.0, G1, FL:J2, top, `final_C4G2_P3_LAS`) 일치 | K-0g |
| 제어기 태그 | `final_C4G2_P3_LAS`, `expect_controller.ok` 참, `c2_setup.k1_order_gate` `off`/`on` | K-0h |
| 종료 | 두 행 `rc` 0, batch `failed` 거짓 | K-0i |
| 판정 도구 | `las_k1_sch_judge.py` sha256 `39ca4b4f8e814b77773c6033e8c28e90c159655e627f39a3175946fca643ce30` = prelaunch = postrun = judge = 지금 파일 = `git show 0c779e6:` blob(`-text`) = `1ae6735` blob | K-0k |

| 코드 파일 | 작업 트리(CRLF) | blob(LF, `92d22e0` = `0c779e6`) |
|---|---|---|
| `04_scripts/02_chrono/run_S9.py` | `f672622a…23db` | `914f2678…e3d7` |
| `04_scripts/02_chrono/las_k1_chrono_rows.py` | `7e1d01ec…20e0` | `594198ea…4569` |
| `04_scripts/02_chrono/s9_batch.py` | `13e32cca…402e` | `18aee560…46b4` |
| `03_src/outrigger_sim/control/c2.py` | `a75d2780…e0ed`(result.json·batch.json 기록도 같음) | `254921d1…a1de` |
| `03_src/outrigger_sim/control/zero_calibration.py` | `b63a7a47…ffb1`(result.json·batch.json 기록도 같음) | `e55d3dd6…8132` |
| `03_src/outrigger_sim/chrono/hull_hook.py` | `afef13ec…bdc3` | `aae84958…5ece` |
| `04_scripts/03_control/s9/late_loc_rule.py` | `76b54910…5ee4`(LF 파일) | 같음 |

- 행 라벨(batch.json): gateoff `P0`/`K1off`/`off`, gateon `P0`/`K1on`/`on`. 두 행 모두 `las_candidate` `P0`(LAS-b b0)다.

### 0.3 결과 파일 (로컬 전용)

| 파일 | sha256 |
|---|---|
| `07_results/S9/batch_V5-LAS-K1-CHRONO_20261109_193952/batch.json` | `6d55fcb37b0e2114aaf532d659885185c8c3fe23dd8c27a0a41b36b4d80b13a4` |
| `…/progress.log` | `fa795c3a9cb3aedc86723ff40ea33b085cf08d582a7d26377e1f77145403416b` |
| `…/SCh_G1_J2FL_B_top_Fs4_VB_gateoff/result.json` | `7f2adafb8f429806e3bcf8bf23516e49dd96ee71f7f49777e184cbe04db93767` |
| `…/gateoff/step_series.npz` | `e2446e061bdf2540d79e655df0e9ecaa9c9d81ec648f849d1ab53f5f5ea5670c` |
| `…/gateoff/controller_commands.npz` | `7de4ad72c3a5b04571d85b8349abb923f73470184e57f5b78e740fd775f80968` |
| `…/SCh_G1_J2FL_B_top_Fs4_VB_gateon/result.json` | `115d8713c34c6f19490119d7a258cc75dff8767af86439892bfbce4690dfaa8f` |
| `…/gateon/step_series.npz` | `13e81af353354ce052f514f47fd57e70536a69f0115802f2b8adb4b40d6fcff1` |
| `…/gateon/controller_commands.npz` | `a3fe162afa67ee414118c67dc0e2c44dedeaadce4962535ec71543d86a317ddb` |
| `06_analysis/03_hydraulic/coupled/v5/las/k1/sch_prelaunch.json` | `177dd93b7f2e097460ef266ee5e052b3edd6dc44be1a1d70c4d17ad0d7101d27` |
| `…/k1/sch_postrun.json` | `5995afdf058410d79f646a51e7bef02a765669e9a657ac8f1830aabe46bea6e7` |
| `…/k1/judge_SCh.json`(공식 판정 JSON) | `7e19e438cc009f9666998bdb04c613f9b18330bb309626f65548488c5cc8e59b` |

- 위 10개 입력 파일의 sha256은 `judge_SCh.json` `files_read_sha256`과 경로 2의 재계산이 같다.
- 공식 판정 명령: `las_k1_sch_judge.py judge --batch <배치 폴더> --prelaunch <sch_prelaunch.json> --postrun <sch_postrun.json>`(dynamics-dev, 메인 세션 실행). 종료 0, `status` `pass`.
- 러너 로그: `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\k1c\s9_batch_20261109_193951.log`(배치 폴더 경로 1줄뿐).
- 자원 기록(`…\scratchpad\k1c\k1c_20261109_193951.sample.json`, 30 s 간격 189표본): 벽시계 5,659.6 s, CPU 시간 19,601 s, 프로세스 트리 최대 RSS 632 MB, 단일 프로세스 최대 284 MB, 시스템 CPU 평균 16.7 %, 다른 부하 평균 4.3 %.
- 실행 시간: gateoff 5,628 s, gateon 5,658 s. 계획의 가정 12,600 s/행보다 약 0.45배 짧다. 볼록 껍질 훅 fast와 4스레드 영향으로 보지만, 원인을 따로 재지는 않았다(판정과 무관).

## 1. 항목별 판정

### 1.1 정체성 K-0 (계획 2.2, rev1 R1-3)

| # | 결과 | 비고 |
|---|---|---|
| K-0a | 참 | 두 행 HEAD `0c779e6`, 기준 `92d22e0`과 코드 diff 없음 |
| K-0b | 참 | dirty 빈 목록(두 행) |
| K-0c | 참 | c2.py·zero_calibration.py: result.json과 batch.json 두 곳 모두 CRLF 봉인 값 |
| K-0d | 참 | prelaunch·postrun `all_ok` 참, (1)~(5) 차이 0건. 시각 순서는 2절에서 따로 확인 |
| K-0e | 참 | 0.2절 |
| K-0f | 참 | 0.2절 |
| K-0g | 참 | 0.2절 |
| K-0h | 참 | 0.2절 |
| K-0i | 참 | rc 0 / 0 |
| K-0j | 참 | 규칙·계획 4파일 |
| K-0k | 참 | 도구 sha 세 기록 같음(`39ca4b4f…`) |

### 1.2 K1 작동과 구조 K-S (계획 3절)

- **K1 작동**: gateoff `decisions` 1건이 `r4_due_without_gate` 참, `would_block` 참이다. 그래서 K1 작동 LOC다.

| 행 | $t_{LOC}$ [s] | $t_P$ [s] | $t_S$ [s] | $n_P$ | $n_S$ | dP | r4_due | would_block | applied |
|---|---|---|---|---|---|---|---|---|---|
| gateoff | 37.7 | 34.9 | 36.9 | 349 | 369 | **−20** | 참 | 참 | 참(관문 꺼짐) |
| gateon | 37.7 | 34.9 | 36.9 | 349 | 369 | −20 | 참 | 참 | **거짓**(막음) |

- $n_{LOC}^{K}$ = 377(37.7 s)

| # | 결과 | 값 |
|---|---|---|
| K-S1 | 참 | `order_gate.enabled` 거짓/참, `c2_setup.k1_order_gate` `off`/`on` |
| K-S2 | 참 | gateoff `applied` = `r4_due`. `INFO_LOC_FLAT_SOIL_MARGIN` 1건(`:80`, 37.7 s) = `applied` 1, `_SKIPPED` 0건 |
| K-S3 | 참 | gateon `applied` = r4_due ∧ ¬would_block(= 거짓). `_SKIPPED` 1건(`:order`, 37.7 s) = (r4_due ∧ would_block) 1, `INFO_LOC_FLAT_SOIL_MARGIN` 0건 |
| K-S4 | 참 | 두 행 모든 decision에서 $n_P$, $n_S$, dP, `would_block` 재계산이 기록과 같다(불일치 0) |
| K-S5 | 참 | gateon에 주기 377 decision이 있고, `t_P_s` 34.90000000003503, `t_S_s` 36.90000000010142가 gateoff와 부동소수까지 같다 |
| K-S6 | 참 | 끝 `clearance_target_m` gateoff 0.08 m, gateon 0.05 m. gateon에서 뒤 LOC의 R4c30 적용은 없다(LOC 취소 0회). E3c10은 두 행 모두 미적용(`is_applied` 거짓) |
| K-S7 = C-P | 참 | 4.1 아래 |

### 1.3 C-P: LOC까지 명령 같음 (계획 4.1)

| 항목 | 값 |
|---|---|
| 명령 파일 | 두 행 `controller_commands.npz`: `t_s` 2000개(8.1~208.0 s), `issued_u_m_s` 2000×4 |
| 주기 정렬 | 두 행 모두 \|t/0.1 − k\| ≤ 1e-6 |
| prefix | $k < 377$, 두 행 **296행**(8.1~37.6 s) |
| prefix sha256 | 두 행 `6ad6c005c1c2942cecaa65e52942ebc830ffa8a3ff6a7be680177a04b82bada3` |
| `np.array_equal` | 참(`t_s`, `issued_u_m_s` 둘 다) |
| 기록: $k_{diff}$ | 379(37.9 s), $k_{diff} - n_{LOC}^{K}$ = 2 |
| 기록: LOC 주기 명령 | 같음(377·378 주기도 같다) |
| 기록: 전체 명령 sha256 | gateoff `106e9c8e…b5fc`, gateon `4670ef44…f96a`(다름. 다른 행 461개) |
| 기록: $n_{LOC}^{K}$ 전 사건 | 이름·주기 목록 같음 |

### 1.4 E-6형 (gateon 절대 판정, gateoff 기록)

| # | gateon | gateoff | 판정 |
|---|---|---|---|
| E-6a 끝 1 s 크롤러 최대 | 0.0 N(창 [207.0, 208.0] s, 1,001표본, 끝값 0.0 N, 접촉 패치 기록 최대 2) | 0.0 N(같은 창) | 참 / 참 |
| E-6b `grid_end_m` | **58.344 mm**(`ge_25mm`) | 88.293 mm | 참 / 참, FLAG 없음 |
| E-6b′ `end_m`(전 절점) | 58.073 mm | 88.019 mm | FLAG `SCh_end_corner_gap` 없음(문턱 = grid − (2.051 + 5) mm) |
| E-6c 이탈 뒤 `strict_fail` | 이탈 확인 34.913 s, 0건 | 같음 | 참 / 참 |
| E-6c′ 짧은 재접촉 | `transient_flag` 0, `threshold_chatter` 0 | 0 / 0 | FLAG 없음 |
| E-6d READY | phases 마지막 `ready`(95.8 s) | 같음 | 참 / 참 |

- E-6형 등급: `gateon_only_failed`·`both_failed` 모두 빈 목록이다.

### 1.5 짝 비교 (gateon 대 gateoff, 계획 4.3)

| # | 결과 | 값 |
|---|---|---|
| C-2형 | 위반 0 | (a) `p3b.checks` 9개가 두 행 모두 참이다. **None/None 0/9**(양쪽 None으로 해당 없음이 된 항목 0). (b) 두 행 모두 마지막 phase `ready`, 첫 READY 95.8 s. (c) FAULT_·WARN_ 이름은 두 행 모두 0개다 |
| P3 | 위반 0 | `P3-1_crawler_zero_after_ready`, `P3-1_recontact_pass`, `P3-5_within`이 두 행 모두 참이다. **None/None 0/3**(해당 없음 0), `P3_baseline_false` 0 |
| C-S | 위반 0 | $s_{max}$ gateoff 503.034 mm → gateon 473.136 mm, **Δ −29.898 mm** ≤ +1 mm |
| C-F | 위반 0(판정 범위 안) | $F_{min}$ 두 행 **28,899.888 N**(RR, 35.002 s, LOC 37.7 s 전) ≥ 10,414.589 N. Δ 0.0 N. 하네스 `F_judged_min_N`과 같은 양이 아니다(Chrono 실제 실린더 힘) |
| READY | 기록 | 첫 READY 95.8 s / 95.8 s, Δ 0 s(0주기). DONE 83.8 s도 같다 |

- 다리별 $s_{max}$ [mm]: FL 503.03 / 445.10 / 436.83 / 432.75(gateoff) → 473.14 / 415.13 / 406.88 / 402.76(gateon). FL·FR·RL·RR 모두 약 −30 mm 줄었다.
- 다리별 $F_{min}$ [kN]: gateoff 85.711 / 121.253 / 77.851 / 28.900, gateon 85.711 / 121.170 / 77.940 / 28.900. 최소(RR)는 LOC 전에 정해져 비트 단위로 같다. FR·RL 최소(약 93.7 s, 탐침 구간)는 ±0.1 kN 다르다.

### 1.6 기록 (판정 아님)

| 항목 | gateoff | gateon |
|---|---|---|
| 끝 `clearance_target_m` | 0.08 m | 0.05 m |
| P3-5 첫 READY 뒤 바퀴 자국 틈 최소 | 85.151 mm | 55.198 mm |
| `crawler_gap.after_first_ready` grid / all 최소 | 86.632 / 86.334 mm | 56.681 / 56.390 mm |
| 이탈 / 이탈 확인 | 34.813 / 34.913 s | 같음 |
| 토양 모드 시작(`source` `release`) | 36.9 s(1건) | 같음 |
| LOC | 37.7 s(취소 0) | 같음 |
| P3-2 LOC − 이탈 / 한계 | 2.887 s / 2.912 s(여유 **0.025 s**) | 같음 |
| P3-4 끝 자세 \|최대\| | 0.0242° | 0.0233° |
| 이탈 뒤 바퀴 자국 틈 최소(기록) | 1.48 mm | 같음 |
| INFO 이름 차 | `INFO_LOC_FLAT_SOIL_MARGIN`만 있음 | `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED`만 있음 |

- 두 행 공통 INFO: `INFO_PRESSURE_ZERO_CALIBRATED`, `INFO_TOUCH_TWIST_HOLD:0.220`(33.4 s), `INFO_LIFTOFF_SLOW:RR`(34.6 s), `INFO_LIFT_PAUSED:RR`(34.7 s), `INFO_LIFTOFF_SLOW_END:sum`(35.1 s), `INFO_D1_IMU_MASS_SOURCE`, `INFO_TWIST_UNSETTLED:-14.1`(83.8 s), `INFO_FLOOR_NONPLANAR`(97.8 s).
- **P3-2 여유 0.025 s(공개)**: LOC가 이탈 뒤 2.887 s에 확정돼 한계 2.912 s에 가깝다. LOC는 K1이 작동하기 전에 정해지므로 두 행이 같고, K1과 관계없다. 이 키의 Chrono 고유 여유로 기록한다.

## 2. 시간 순서 (K-0d는 시각 순서를 보지 않으므로 직접 대조)

| 시각(+09:00) | 사건 | 출처 |
|---|---|---|
| 16:24:49 / 16:25:47 | 원판 봉인 / `ea524f0` | `.sha256`, git |
| 17:13:20 / 17:13:52 | rev1 봉인 / `62fb8d7` | 같음 |
| 18:55:06 / 18:56:12 | 행 정의·`--k1-order-gate` `f805aba` / 병합 `f25b043` | git |
| 19:02:08 | Y 판정서 `986f1a0` | git |
| 19:05:07 | 계획 첫 봉인(`802e1643…`, 무효, 공개됨) | 계획 첫머리 |
| 19:06:08 / 19:07:17 | 계획 봉인 / `9df5743` | `.sha256`, git |
| 19:07:47 | `92d22e0`(S1/S2 렌더 2파일, S-Ch import 경로 밖) | git, rev1 R1-0 |
| 19:20:58 | 건조 prelaunch 1회차: `stop`((2) 거짓) | 7.4절 |
| 19:25:17 / 19:26:15 | 계획 rev1 봉인 / `286556d` | `.sha256`, git |
| 19:26:30 / 19:29:44 | 판정 도구 `7c46931` / rev1 반영 `1ae6735` | git |
| 19:29:31 | 건조 prelaunch 2회차: `pass`(도구 `39ca4b4f`) | 7.4절 |
| 19:30:28 | 도구 병합 `0c779e6`(= 실행 HEAD) | git |
| 19:30:35 | 행 생성 점검 `rows_check.json`(rev1 R1-4.1) | 파일 시각 |
| 19:39:24 | verif-protocol-auditor 실행 전 감사 보고(차단 0) | 실행 전 감사 보고 시각 |
| 19:39:36 | 메인 세션 T-9/SK-5 결정 메모 | 파일 시각 |
| 19:39:40 | prelaunch `pass` | `sch_prelaunch.json` `taken_utc` 10:39:40Z |
| 19:39:52 | START 2행(P 2슬롯, pid 109376 / 188928) | progress.log |
| 21:13:40 / 21:14:10 | END gateoff rc 0 / END gateon rc 0 | progress.log |
| 21:14:11 | 배치 끝 `failed=False` | progress.log |
| 21:24:52 | postrun `pass`(차이 0), 이어서 judge `pass` | `taken_utc` 12:24:52Z(같은 초. judge가 postrun sha `5995afdf…`를 읽었으므로 postrun이 먼저다) |

- 실행 중(19:39:52~21:14:10) master 커밋은 없다. `git log --since 19:30:29` 결과가 비어 있고 HEAD는 지금도 `0c779e6`이다.
- prelaunch < START < END < postrun < judge 순서가 성립한다. 도구 커밋(19:29:44)과 병합(19:30:28)은 rev1 봉인(19:25:17) 뒤이고 prelaunch 앞이다.
- result.json 쓰기 시각: gateoff 21:13:39, gateon 21:14:10. 둘 다 END 줄과 맞다.

## 3. Q-C1~Q-C4 대조 (계획 6.1, 판정 기준 아님)

| # | 항목 | 예측 | 관측 | 안/밖 |
|---|---|---|---|---|
| Q-C1 | gateoff `soil_mode_start` | ≥ 1 | 1(36.9 s) | 안 |
| Q-C1 | `INFO_LOC_FLAT_SOIL_MARGIN:80` | 정확히 1 | 1 | 안 |
| Q-C1 | 끝 `clearance_target_m` | 0.08 m | 0.08 m | 안 |
| Q-C1 | **K1 작동 LOC의 dP** | **[−12, −1], 중앙 −6** | **−20** | **밖** |
| Q-C1 | `would_block` | 참 | 참 | 안 |
| Q-C1 | $n_{LOC} - n_S$ | [1, 10] | 8 | 안 |
| Q-C1 | $t_{LOC}$ | [30, 40] s | 37.7 s | 안 |
| Q-C2 | gateon `_SKIPPED:order` / R4 사건 | 1 / 0 | 1 / 0 | 안 |
| Q-C2 | gateon 끝 `clearance_target_m` | 0.05 m | 0.05 m | 안 |
| Q-C2 | C-P, $k_{diff} - n_{LOC}$ | 참, [0, 5] | 참, 2 | 안 |
| Q-C2 | $s_{max}$ gateoff / gateon / Δ | [480, 530] / [450, 500] / [−35, −25] mm | 503.03 / 473.14 / −29.90 mm | 안 |
| Q-C2 | C-S | 통과 | 통과 | 안 |
| Q-C2 | $F_{min}$ | LOC 전이면 Δ 0, 두 행 ≥ 10,414.589 N | 최소 35.002 s(LOC 전), Δ 0.0 N, 28,899.9 N | 안 |
| Q-C3 | gateon E-6a | 0.0 N | 0.0 N | 안 |
| Q-C3 | `grid_end_m` gateon / gateoff / Δ | [30, 70] / [60, 100] / [−35, −25] mm | 58.34 / 88.29 / −29.95 mm | 안 |
| Q-C3 | gateon E-6c / E-6d | 이탈, strict 0 / `ready` | 같음 | 안 |
| Q-C3 | P3-5 READY 뒤 틈 gateon / gateoff | [35, 70] / [65, 100] mm | 55.20 / 85.15 mm | 안 |
| Q-C3 | C-2형·P3 위반, 새 FAULT·WARN | 0 | 0 | 안 |
| Q-C3 | READY Δt | [−5, +2] s | 0.0 s | 안 |
| Q-C3 | 전체 | `통과` | `통과` | 안 |
| Q-C4 | K1 미작동 분기 | Q-C1이 맞으면 해당 없음 | K1 작동 → 해당 없음 | — |

- 판정 도구 `predictions` 표 29항목(Q-C1 7, Q-C2 11, Q-C3 11) 중 28항목이 범위 안이고, 범위 밖은 dP 하나다. 위 표는 그 29항목을 묶어 적었다. 경로 2가 다시 센 예측값(dP 안/밖, grid_end Δ, $n_{LOC}-n_S$, R4·`_SKIPPED` 사건 수, 토양 모드 수)도 같다.

## 4. dP −20 이탈의 공개와 해석

### 4.1 사실

- 예측 [−12, −1]주기는 **하네스** 근거로 정했다. 같은 키의 하네스 값은 Y-Pa P0 VB e0 −8, 그 밖 P0 −4~−8, Y-0b P5r4 −15다.
- Chrono 관측은 −20이다($t_P$ 34.9 s, $t_S$ 36.9 s). 하네스 P0보다 12주기(1.2 s) 더 음이다.
- dP의 부호는 예측과 같다. 그래서 K1 분류(관문 막음)는 바뀌지 않는다. 오히려 관문 문턱(dP > 0)에서 20주기(2.0 s) 떨어져 있어, 예측(1~12주기)보다 분류 여유가 크다.
- K-S5가 두 행의 $t_P$·$t_S$가 부동소수까지 같음을 보였다. LOC 전 명령도 비트 단위로 같다(C-P). 따라서 −20은 실행 잡음이나 K1의 영향이 아니라, 이 키의 Chrono 경로가 결정적으로 낸 값이다.

### 4.2 해석 (결과를 본 뒤 읽은 기록. 판정에는 쓰지 않는다)

- **평탄 창 시작 뒤 토양 모드 해제까지 약 2 s가 걸린다.** gateoff 명령·행정 기록은 다음과 같다.
  - 34.6 s: `INFO_LIFTOFF_SLOW:RR`(LAS-b 이륙 접근 감속 시작, 시작 다리 RR, ρ 0.303)
  - 34.7 s: `INFO_LIFT_PAUSED:RR`(P-S8-30 느린 들어 올림, 30주기). 발행 명령이 약 20 mm/s에서 34.9 s에 네 다리 2.2~5.2 mm/s로 내려간다.
  - 34.813 s: 크롤러 이탈(SCM 크롤러 법선력 < 0.01 W, 0.1 s 유지 → 34.913 s 확인)
  - 34.9 s: $t_P$(S-1 평탄 창 꼬리 시작). 이 뒤 네 다리 평균 행정 속도는 3.3~4.2 mm/s(≈ 0.16 $v_{max}$)이고 크롤러 힘은 0 N이다.
  - 36.9 s: 토양 모드 시작(`source` `release`, 기준 행정 0.3718 m)
  - 37.7 s: LOC 확정, R4c30 평가. 37.8 s부터 명령이 다시 오른다.
  - 즉 느린 들어 올림 속도(≈ 3.3 mm/s)에서 해제 조건이 차기까지 20주기가 걸렸다. 하네스는 같은 키에서 4~8주기였다. 이 차이는 Chrono SCM 크롤러 제하·패치 J2 침하 경로와 하네스 크롤러 모델의 차이에서 오는 것으로 본다. 해제 조건의 어느 항이 20주기를 정했는지는 분해하지 않았다(추정).
- **봉인 전에 볼 수 있었던 근거**: 계획 7절의 저장 Chrono 1건(2026-10-28, 옛 제어기, 같은 바닥·패치·패드·오거·$F_s$)이 `controller_meta.soil`에 $t_P$ 33.0 s, 토양 모드 35.0 s를 담고 있다. 이 값으로 dP를 계산하면 **−20**이다.
  - 계획 7절은 이 실행의 이탈 33.02 s, 토양 모드 35.0 s, LOC 35.4 s를 봤다고 적었다. 그러나 `t_P_s` 필드를 읽지 않았고, 예측을 하네스 dP로 정했다.
  - `t_P_s`는 이번 판정 중(결과를 본 뒤) 해석을 위해 처음 읽었다. 7.5절에 공개한다.
  - 옛 제어기(LAS-b 이전)에서도 같은 −20이 나왔다. 그래서 이 지연이 LAS-b b0만의 산물은 아니라고 본다.
- **교훈**: 하네스에서 정한 주기 단위 예측은 Chrono에서 크게 벗어날 수 있다. 같은 바닥의 저장 Chrono 기록이 있으면 그 $t_P$·$t_S$로 예측 범위를 정해야 했다.
- **K1 채택 판단에 주는 뜻**(10절)
  - 패치형 키에서는 Chrono가 하네스보다 더 음으로 치우쳤다. 그래서 막아야 할 곳을 확실히 막는다.
  - 반대로 진짜 연약 지면 키(하네스 dP +31~+96, Y-0b·Y-0c)에서 같은 방향의 치우침이 생기면, R4c30을 켜야 할 곳의 여유가 줄어든다.
    - 이 키에서 본 치우침(−12주기)을 그대로 옮겨도 최소 +31 → 약 +19로 문턱 위다.
    - 하지만 Chrono에서 확인한 것은 아니다.

## 5. 재실행

- 없다. progress.log `START` 2, `END` 2, `RESUME_SKIP` 0, `SKIP` 0, `MIXED_HULL_MODE` 0이다.
- 판정 도구 `rerun`: 두 행 모두 `attempt1/` 폴더 없음, 1회차 result.json 없음.
- `--resume`·`--keys`·`--limit`·`--only`·`--row-filter`를 쓰지 않았다. 배치 2행 전체를 한 번의 `s9_batch run`(P 2슬롯)으로 돌렸다.
- git 시간 초과(Suspended git 추정)는 없다. 두 행 `git_at_start.head`가 정상 값이고, batch.json으로 대체하지 않았다.

## 6. 실행 전 감사와 메인 세션 결정

### 6.1 verif-protocol-auditor 실행 전 감사 기록 6건

- 감사 결론(메인 세션 보고): **차단 0**. 실행 전 처리 항목 1건(T-9 대 SK-5, 6.2)이 있었고, 메인 세션이 처리한 뒤 실행했다.
- 아래 표는 메인 세션이 실행 전 감사 보고 원문(verif-protocol-auditor, 11-09 19:3x)에서 옮겼다(판정서 초판 작성자는 원문을 받지 못했다).
- **감사가 기록한 도구 커밋·sha256(R1-3)**: `06_analysis/02_control/verif_matrix/scripts/las_k1_sch_judge.py`, sha256 `39ca4b4f8e814b77773c6033e8c28e90c159655e627f39a3175946fca643ce30`(LF, `-text`, git blob `565fff9d` = 작업 트리), 도입 커밋 `1ae6735`(19:29:44), 병합 `0c779e6`(19:30:28). `8bee8e8`·`7c46931`판은 같은 blob `934d1628`(rev1 작성 때 본 판, R1-7 공개). → K-0k 값 `39ca4b4f…ce30`과 같다.

| # | 감사 기록 | 처리 |
|---|---|---|
| 1 | [실행 전 수정][R] T-9(결측 시 `incomplete` 우선)가 원판 SK-5(C-2형·P3·C-S·C-F 위반 → 즉시 `미달`)를 가릴 수 있다(`las_k1_sch_judge.py:1874-1877`). 통과로 새지는 않는다 | 메인 세션 결정 (나), 6.2. 이번 결과는 결측 0이라 해당 없음 |
| 2 | [기록][I·T] 실행 중·판정 완료 전 병합 금지. 34c08e8(`test_s2_defer.py`)은 코드 diff 경로 안이라 postrun (2)·재실행 prelaunch를 거짓으로 만들고, 9c98823(문서)도 HEAD를 바꿔 K-0d stop. 다른 worktree 커밋은 영향 없음 | 실행~judge 동안 master 커밋·병합 0건(git log 대조). 대기 브랜치는 판정 뒤 병합 |
| 3 | [기록][T] K-0d는 prelaunch가 첫 START 앞, postrun이 두 END 뒤인지 검사하지 않는다(`check_k0d` 740~762행). 재실행 때 prelaunch 기본 경로 덮어쓰기 주의. prelaunch 종료 0이 아니면 띄우지 않는다 | 2절 시간 순서에서 progress.log와 직접 대조(prelaunch 19:39:40 < START 19:39:52, postrun 21:24:52 > END 21:14:10). 재실행 없음. prelaunch 종료 0 확인 뒤 띄움 |
| 4 | [기록][E] 빈 집합 검사는 통과로 새지 않는다(E-6c 이탈 없음 → 실패, 빈 prefix → C-P 거짓, `decisions` None → incomplete). 남는 공백: C-2(a)·P3 양쪽 None은 해당 없음(None/None 건수 공개), 블록 결측 `incomplete`가 K-0보다 먼저 돌아옴. gate_scan 경고 15건은 모두 오탐 | 이번 결과: 블록 결측 0, prefix 296행 일치, E-6c 이탈 확인. C-2(a)·P3 None/None 건수는 1.5절 표에 적었다(C-2(a) 0/9, P3 0/3, `P3_baseline_false` 0) |
| 5 | [기록][R] 드문 경로 두 가지(잘못 통과 없음): `s_motor_max_m`·`F_min_after_N` 목록 안 None → TypeError 종료 3, K-S6에서 gateoff R4c30 적용 뒤 LOC 취소·목표 유지 설정 꺼짐·뒤 LOC 없음이면 끝 목표 0.05 m로 거짓 stop 가능(c2.py:8529-8531) | 이번 결과: 두 목록에 None 없음, gateoff 끝 목표 0.08 m(취소 없음). 해당 없음 |
| 6 | [기록][T] 시간 순서·공개 확인: 규칙 16:24:49 → rev1 17:13:20 → 계획 19:06:08(9df5743) → 92d22e0 19:07:47 → 도구 초판 19:21:15 → 계획 rev1 19:25:17(286556d) → 1ae6735 19:29:44 → 병합 19:30:28. 결과 0건. 봉인 전에 본 자료는 계획 7절·R1-7. scratch 건조 실행 2회(19:20:58, 19:29:31)는 정체성만 기록 | 2절·7절에 반영. 건조 실행 2회 공개(7절) |

- 각주(건수): 실행 전 감사 원문의 요약 줄은 "실행 전 수정 1, 기록 6"이지만, 본문의 기록 표제는 5개다. 요약 줄 쪽의 실수로 보고, 위 표 6행(실행 전 수정 1 + 기록 5)은 본문과 같다.
- 감사 뒤 도구를 바꾸지 않았다. 도구 sha가 prelaunch부터 judge까지 같다(K-0k).

### 6.2 T-9/SK-5 메인 세션 결정 메모 (인용)

- 파일: `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\k1sch\main_session_decision_T9.md`
  - sha256 `7a4b66d219948fc5cb1f810a09e389720400281fbeb9971492b415e38c8db16f`
  - 쓴 시각 19:39:36. prelaunch(19:39:40) 앞이고, S-Ch 결과가 생기기 전이다.

> Pre-run audit (blocking 0) raised one pre-run item: `las_k1_sch_judge.py final_status` returns `incomplete` when any value is missing, even if an independent C-2/P3/C-S/C-F violation exists. Plan original line 10 says the K1 rules (original, rev1) take precedence where readings differ, and rules SK-5 says a C-2/P3/C-S/C-F violation is an immediate `fail`.
>
> Decision: option (나). The tool is NOT changed before the run (tool sha 39ca4b4f... stays, K-0k intact). If the judge returns `incomplete` with non-empty `fail_reasons` that do not depend on the missing values, the judgement report applies SK-5 by hand: grade = `fail`, missing values disclosed.

- **이번에는 적용할 일이 없었다.**
  - `incomplete_reasons`·`missing_values_info`·`fail_reasons`가 모두 빈 목록이다.
  - rev1 R1-5의 결측 판정값 4종(E-6b `grid_end_m`, E-6a 끝 창, C-S `s_motor_max_m`, C-F `F_min_after_N`)이 두 행 모두 있다. **결측 사유 건수는 0이다**(rev1 R1-8-6).
  - 그래서 손으로 등급을 바꾸지 않았다. 도구 `status` `pass`를 그대로 옮겼다.

## 7. 공개 체크리스트

### 7.1 계획 8절 14항

| # | 항목 | 내용 |
|---|---|---|
| 1 | 짝 없는 키·목록 밖·중복 | batch.json `cases`는 정확히 두 이름이다. `pair_case`가 서로를 가리킨다. 목록 밖 0, 중복 0, 짝 없는 행 0 |
| 2 | 빈 집합 통과 금지 | 이탈 확인 있음(34.913 s). prefix 296행(≥ 1). decisions 1건(비지 않음). E-6a 창 1,001표본 |
| 3 | 부분 기록 | `{"error": …}` 블록 0. `git_at_start` 정상(batch.json 대체 없음). 필수 블록 6종 모두 있음 |
| 4 | 재실행 기록 | 5절(없음) |
| 5 | 이름 혼동 | 행마다 `las_candidate` P0/P0, `k1_candidate` K1off/K1on, `k1_order_gate` off/on을 집계했다(0.2절). 하네스 키의 `K1`은 크롤러 강성이다 |
| 6 | 정확한 사건 이름 | `:` 앞 이름으로 셌다. `INFO_LOC_FLAT_SOIL_MARGIN` 1/0, `_SKIPPED` 0/1(gateoff/gateon) |
| 7 | 정수 주기 비교 | $n_P$, $n_S$, $n_{LOC}$, prefix, READY Δ 모두 round(t/0.1)로 비교했다 |
| 8 | sha 기준 | 기록 sha(c2·zero_calibration)는 CRLF 열과 대조했다. blob(LF)은 prelaunch·postrun이 따로 확인했다. 섞지 않았다 |
| 9 | 실행 중 작업 트리 고정 | prelaunch = postrun(차이 0). 실행 중 커밋 0(2절) |
| 10 | 봉인·커밋·도구·실행 시각 순서 | 2절 표 |
| 11 | 미달·stop 우선순위 | 둘 다 없음 |
| 12 | 결과 본 뒤 규칙 변경 금지 | 문턱(E-6b 25 mm, 1 mm, 10,414.589 N, 1.0 s, 0.0 N)을 바꾸지 않았다. 결과 뒤 새 판도 없다. 8절의 E-6a 창 경계 허용치(1e-9 s)는 경로 2를 도구·run_S9 관례에 맞춘 것이다. 판정값(최대 0.0 N)은 어느 쪽이든 같다 |
| 13 | 볼록 껍질 대체 동작 | `hull_hook_effective.mode` fast(두 행), `fallback_reason` None, 명시 모드 fast. 조용한 off 대체 없음 |
| 14 | 두 경로 재집계 | 8절 |

- 원판 `las_k1_rules.md` 8절 항목도 따로 적는다.
  - #4 resume·`--keys`·`--limit`: 쓰지 않았다(5절). `--only`·`--row-filter`도 쓰지 않았다.
  - #5 본 뒤 버린 줄: **0건**

### 7.2 rev1 R1-8 6항

| # | 항목 | 내용 |
|---|---|---|
| 1 | rev1 sha256·봉인·커밋 시각 | `d8f957cb…9295`, 19:25:17 → `286556d` 19:26:15(+58 s) |
| 2 | R1-1 기준 커밋 변경 이유·import 근거·감사 재확인 | rev1 R1-0·R1-1. 실행 HEAD `0c779e6`에서도 `92d22e0` 대비 코드 diff 없음. 감사 재확인 결과(import 근거 `git grep` 0건 등)는 6.1 #6·감사 보고 |
| 3 | K-0k 세 sha와 감사 기록 sha | 세 sha 같음(`39ca4b4f…`). 감사 기록 sha(`39ca4b4f…`, 6.1 머리)와 같다 |
| 4 | 행 생성 점검(R1-4.1) | `las_k1_chrono_rows.py --out <scratchpad>\k1sch\rows_check.json`(Chrono-dev, 19:30:35). `ok` 참, 두 행 `status` `ok`, `diffs` 빈 목록, `order_gate` 거짓/참. 종료 코드는 출력 파일에 없다(메인 세션 보고로 0) |
| 5 | I-1~I-9와 구현자 원문 목록 | 감사는 I-1~I-9가 모두 도구와 맞는다고 확인했다(구현자 원문 목록은 감사도 받지 못해 대조하지 않았다, 감사 보고 "규칙↔도구 대조"). 이번 결과에서 I-6(미작동 분기), I-7·I-9(결측), I-8(0~25 mm + E-6a 거짓)은 해당 경우가 생기지 않았다 |
| 6 | R1-5 `incomplete` 사유 건수 | 0 |

### 7.3 봉인 전에 본 데이터 (계획 7절, rev1 R1-7 그대로)

- 계획 원판 봉인 전
  - 원판·rev1 전문
  - Y 판정서(커밋 판 `fdb8fab4…`)
  - 코드(`f25b043`)의 지정 범위
  - 저장 Chrono 1건(`batch_G6P_20261028_154030/G6_G1_B_top_Fs4_spJ2FL`: `p3b.checks`, FL $s_{max}$ 472.9 mm, READY 뒤 틈 55.9 mm, 이탈·LOC·토양 모드 시각, phases, 끝 1 s 크롤러 0.0 N, 명령 npz 형식)
  - 명세 E-6·426.9·R4c30 행
  - 파일·DLL 해시
- 계획 rev1 봉인 전: 건조 prelaunch 1회차 결과, 도구 `8bee8e8` 전문, git 기록과 import 조사
- S-Ch 결과는 두 봉인 모두 0건이었다.
- **사전 예측의 수치는 위 자료를 본 뒤 정했다.** 하네스 Y 묶음 값과 저장 Chrono 1건이 근거다.

### 7.4 건조 실행 2회 (prelaunch만, 결과 전)

| 회차 | 파일 | 시각 | HEAD | 도구 sha | 결과 |
|---|---|---|---|---|---|
| 1 | `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\py_sch_judge\sch_prelaunch_dry.json` | 19:20:58 | `92d22e0` | `19b63a35…`(rev1 전 도구) | `stop`: (2) `code_diff_empty` 거짓(f25b043 기준, `92d22e0`이 렌더 2파일을 넣음). (1)·(3)~(6) 참 |
| 2 | `…\scratchpad\py_sch_judge\sch_prelaunch_dry_rev1.json` | 19:29:31 | `286556d` | `39ca4b4f…`(= 본 실행 도구) | `pass`: (1)~(6) 모두 참 |

- 1회차가 계획 rev1(R1-1 기준 커밋 `92d22e0`, R1-2 빈 허용 목록, R1-3 K-0k)의 계기다. rev1 R1-0에 공개되어 있다.
- 두 회차 모두 실행 전이고 결과 파일을 만들지 않았다.

### 7.5 봉인 뒤 판정 전에 본 것

- 메인 세션 보고: 배치 시작·종료 시각, rc, wall, 실행 조건, prelaunch·postrun·judge 요약, 사전 예측 대조 요약(dP 이탈 포함)
- 이 판정서를 쓰며 읽은 것
  - `judge_SCh.json` 전체, 두 행 result.json의 판정 블록, npz, batch.json, progress.log, 자원 기록
  - 4.2 해석을 위한 gateoff 사건·명령·행정 기록(34~38 s)
  - 저장 Chrono 1건의 `controller_meta.soil.t_P_s`(33.0 s)·`soil_mode_t_s`(35.0 s)
- 이것들을 보고 바꾼 규칙·기준·문턱·등급은 없다.

## 8. 두 경로 재집계

| 경로 | 방법 | 결과 |
|---|---|---|
| 1 | 판정 도구 `las_k1_sch_judge.py judge`(sha256 `39ca4b4f…`) → `judge_SCh.json` | `pass` |
| 2 | control-expert 독립 집계 `recount_sch.py`. 판정 도구·run_S9·s9_batch·프로젝트 모듈을 import하지 않는다. json·numpy·hashlib과 읽기 전용 `git diff --quiet`만 쓰고, result.json·npz·batch.json·progress.log·prelaunch·postrun·규칙 파일만 읽는다. K-0a~k, K-S1~7, prefix, E-6a~d, C-2형·P3·C-S·C-F·READY, 기록·예측값을 따로 구현했다 | `pass`, stop 0, fail 0 |

| 비교 | 결과 |
|---|---|
| 항목 수 | 115. K-0 11개와 K-S 7개의 참거짓, K1 결정 필드, prefix 기록, 두 행 E-6 값, 짝 비교 값, 기록 값, 예측 값, 행 라벨, progress.log 건수, 읽은 파일 sha 10개, 최종 status·사유 목록 |
| 불일치 | **0** |
| 수치 최대 절대 차 | **0.0**(허용 1e-9) |
| 불리언·건수·주기·해시 | 완전 일치 |

- **공개(1회차 불일치 2종 4항목)**: 경로 2 첫 실행에서 E-6a 창 표본 수가 1,000(경로 1은 1,001)이었고, 창 첫 시각도 달랐다(두 행).
  - 원인: 1 ms 시각 값의 부동소수 누적이다. 왼쪽 끝 표본 $t$ = 207.00000000574815 s가 $t_{end} - 1.0$ = 207.00000000578135 s보다 약 3e-11 s 작다.
  - 도구는 run_S9 P3B 창 관례인 경계 허용치 1e-9 s(`WINDOW_EDGE_TOLERANCE_S`)를 쓴다. 경로 2는 처음에 허용치 없이 셌다.
  - 경로 2에 같은 1e-9 s 허용치를 넣어 다시 셌다. 허용치 없는 값(1,000표본, 최대 0.0 N)도 기록으로 남겼다.
  - 판정값(창 최대 0.0 N, E-6a 참)은 두 정의에서 같다. 계획 4.2는 "창 약 1,000표본"이라고만 적어 경계 표본을 정하지 않았다.
  - 경로 2는 첫 불일치를 본 뒤 도구 관례(허용 1e-9 s)에 맞췄다. 그래서 **이 한 항목(E-6a 창 경계)은 두 경로가 서로 독립이 아니다.** 판정 후 감사의 독립 재집계는 두 정의(허용치 없음, 1e-9 s)로 각각 셌고, 두 행 모두 둘 다 최대 0.0 N이었다.
- 경로 2 파일(control-expert scratchpad `k1sch_judge\`)
  - `recount_sch.py`(sha256 `5e5d2a27…da33`) → `recount.json`(`86b7702e…a28c`)
  - `explore.py`(구조 조회), `dp_interpret.py`(4.2 해석 자료)
  - 실행: `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I <파일>`(PowerShell)

## 9. 결론

- **S-Ch 판정은 `통과`다.** Y 묶음(하네스, `통과`)과 합쳐 원판 순서 Y-0 → Y-P → Y-S → Y-T → S-Ch가 모두 끝났다. 위반·멈춤·결측은 없다.
- Chrono SCM에서 K1은 설계대로 작동했다.
  - LOC 전 명령은 비트 단위로 같다(prefix 296행).
  - 관문은 패치 키의 R4c30(+30 mm)만 막았다.
  - 그 결과 최대 행정 −29.90 mm, 끝 크롤러 틈(격자) −29.95 mm였다. 하네스 Y-Pa −30.01 mm와 0.1 mm 안에서 같다.
  - 끝 크롤러 하중 0, 이탈 뒤 strict 재접촉 0, READY 시각 같음, $F_{min}$ 같음.
- 대가는 크롤러 틈이다. 끝 틈 88.3 → 58.3 mm, READY 뒤 바퀴 자국 틈 85.2 → 55.2 mm. E-6b 기준 25 mm 위로 33 mm 여유가 남는다.
- 사전 예측 29항목 중 dP 1항목이 범위 밖이었다(−20 대 [−12, −1]). 부호와 분류는 맞았고, 원인은 하네스 근거로 예측을 정한 데 있다(4절).

## 10. 다음 할 일과 사용자 결정 사항

### 10.1 K1 채택 (사용자 결정)

| 선택지 | 내용 | 장점 | 남는 위험·비용 |
|---|---|---|---|
| (가) 채택 | 프리셋 `with_10hz_d1()` 기본 켬(`flat_soil_margin_order_gate=True`). 새 태그(예: VB `final_C4G2_P3_LAS_K1`, V0 `final_C4G2_LAS_K1`). 전환 전 재현 러너를 둔다 | LAS-b 경계 키 C-S가 −0.116 mm로 풀린다. 패치형 키의 불필요한 +30 mm 행정을 없앤다. 하네스 562줄과 Chrono 1짝에서 위반 0 | 진짜 연약 지면에서 Chrono dP 부호(> 0)를 확인하지 않았다(4.2). 태그 전환은 verif-protocol-auditor `전환 후` 감사와 태그 집합(`EXTEND_START_TAGS`, `_LAS` 접미사) 점검이 필요하다 |
| (나) 조건부 채택(**권고**) | (가)와 같다. 단 전환 전에 저장 Chrono 연약 지면 결과(S9 FINAL-REP 등 토양 모드가 있는 행)의 `controller_meta.soil`에서 $t_P$·$t_S$를 읽어 그림자 dP를 센다. 새 실행은 없다. R4c30을 켜야 할 행이 모두 dP > 0이면 전환한다. 기준은 읽기 전에 봉인한다 | 추가 Chrono 없이 4.2의 남은 위험을 닫는다 | 저장 결과가 옛 제어기일 수 있다. 그 경우 dP 정의(`plateau_start_s`, `soil_mode_t_s`)가 같은지 먼저 확인한다 |
| (다) 보류·기각 | 프리셋 그대로(K1 꺼짐) | 변경 없음 | LAS-b P5r4는 경계 키 C-S +30.10 mm로 계속 미달이다. 패치형 키는 틈 80 mm 목표(+30 mm 행정)를 유지한다 |

- 권고 근거: 하네스와 Chrono 모두 통과했다. 남은 근거 공백은 한 가지(연약 지면 Chrono의 dP 부호)이고, 저장 결과 읽기로 닫을 수 있다.
- 채택 뒤 할 일
  - 태그 전환 회귀: K1이 작동하지 않는 행의 명령 해시가 같은지 본다. Y-T 192/192가 같은 유형의 근거다.
  - 명세·CLAUDE.md 기준값 갱신(메인 세션)
  - 코드 기본값 전환은 python-expert 몫이다.

### 10.2 LAS-b P5r4 처리 (사용자 결정)

| 선택지 | 내용 | 비고 |
|---|---|---|
| (가) P5r4 종결, P0(b0) 유지(**권고**) | LAS-b 채택 프리셋은 지금의 b0(P0) 그대로 둔다. P5r4는 "K1 없이 경계 키 C-S 미달, K1과 함께면 하네스 Y-S 통과"로 기록한다 | S-Ch는 P0만 확인했다. P5r4의 Chrono 근거는 없다 |
| (나) P5r4 + K1로 LAS-b 재판정 | K1 채택(10.1 가·나)이 먼저다. 그 뒤 P5r4 + K1을 새 봉인 규칙(LAS-b A안 기준 승계)과 Chrono 확인으로 다시 판정한다 | 새 봉인·감사·Chrono 실행이 필요하다. P5r4가 P0보다 무엇을 더 주는지는 이 판정서 범위 밖이라 여기서 평가하지 않았다. 사용자가 P5r4의 이득을 원할 때만 권한다 |

### 10.3 그 밖 (원판 9절 그대로 사용자 결정)

- B1(P0 J2 fdown 행정 예산, LOC 때 예상 최종 행정으로 경사 틈 여유 축소)
- 이상적 센서 진단
- 재개 검증 436.8

### 10.4 이 판정서 뒤 바로 할 일

1. (완료) verif-protocol-auditor 판정 후 감사: 차단 0, 기록 6, 이 판에 반영.
2. (완료) 판정서·decision_log 커밋. 결과 파일(`*.json`)은 로컬 전용이다.
3. (완료, 11-09 21:4x) 사용자 결정: 10.1 K1은 조건부 채택(저장 Chrono 연약 지면 결과의 그림자 dP 확인, 기준은 읽기 전 봉인), 10.2 LAS-b P5r4는 K1 채택 뒤 P5r4+K1 재판정.

## 11. 한계

- Chrono 근거는 패치 키 1짝(2행)뿐이다. 진짜 연약 지면, 경사, 오거 중·하단, 잡음 등급, P5r4는 Chrono로 보지 않았다.
- 4.2의 지연 원인(어느 해제 조건 항이 20주기를 정했는지)은 분해하지 않았다. 하네스와의 차이를 크롤러 모델 차이로 보는 것은 추정이다.
- P3-2 여유 0.025 s는 K1과 무관하지만, 이 키에서 LOC 확정 지연이 조금만 늘어도 P3-2 위반(FLAG 규칙 419.8 적용 대상인지 별도 확인)이 될 수 있는 위치다.
- 실행 시간이 계획 가정의 약 0.45배였다. 원인은 재지 않았다.
