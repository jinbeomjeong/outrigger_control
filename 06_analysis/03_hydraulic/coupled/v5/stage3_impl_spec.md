# v5 3단계 구현 명세 (cad-expert 지시용)

작성: control-expert, 2026-11-07. 판정 규칙은 `v5_criteria_rev6.md`(개정 6, SHA-256 `fd511703…`, **봉인 2026-11-07 11:13:35 +09:00**), 계획은 `stage3_plan.md`이다.

| 항목 | 내용 |
|---|---|
| 기준 코드 | 작성 때 master 1ef9aa5. **현재 master b6b295c**(M2 r5 `flow_limited_r5`, R-1~R-6과 새 묶음은 5f57175·29b16df·c4ca6bb로 구현됨, ③ v2 기본 꺼짐, `R79_T4H_DIR`). 이후 `extend_bound_check` 커밋 예정 |
| 3단계 실행 | ③ 꺼짐 VB로 실행한다. 조용한 비용 측정 뒤 사용자 승인을 받아 시작한다(`stage3_plan.md` 7절) |
| 하네스 시드 확장 | VB **r5**·V0, 2키 × 25시드(개정 6 9절) |
| 담당 | Chrono 실행기·행 정의(`run_S8C.py`, `run_S9.py`, `s9_batch.py`, `03_src/outrigger_sim/chrono/*`): cad-expert. 판정 도구(`04_scripts/04_hydraulic/coupled/*`): cad-expert 또는 python-expert(메인 세션이 정한다) |
| 실행 환경 | Chrono-dev(실행기, L2b), dynamics-dev(판정 도구, `-I -B`) |
| 금지 | 옵션을 모두 끈 실행의 명령·플랜트 값은 비트 동일이어야 한다(B-2, B-4, B-5). 3단계 VB Chrono 기록에 R-6을 돌리는 것은 개정 6 봉인 뒤에만 한다. 셸 heredoc과 `python -` 금지, Python은 PowerShell 도구로 실행 |

## 1. 기록 추가 (R-1 ~ R-5)

모두 **M2·LC 등 v5 옵션을 켠 실행에서만** 키를 쓴다. 옵션 없는 실행의 `result.json`·`pads.npz` 숫자 배열·meta는 지금과 같아야 한다. 예외: `pads.npz`의 `meta_json`에 새 필드 이름이 들어가는 것은 B-4 판정 선례(11-06, `v5_fields`)와 같이 허용한다. 단, 메인 세션 보고에 차이 키를 적는다.

### R-1 M2 해제 기록

| 항목 | 내용 |
|---|---|
| 위치 | `L2bForceActuator._shift_reference_for_rod_pressure`(`l2b_actuator.py:601`)에서 `oil.releases_of_last_call`로 해제를 받는 곳과, 그 다리가 다시 잠기는 곳(`oil.locked` 전이) |
| 출력 | `result.json` `hydraulics_record.m2_releases`(리스트). 크면 실행 폴더 `m2_releases.json`으로 하고 `result.json`에는 경로와 건수만 |
| 해제마다 필드 | `leg`(0~3), `t_rel_s`(해제를 처리한 훅의 시각), `p_r0_Pa`(잠금 앵커), `p_rel_Pa`(해제 훅의 잠김 법칙 로드 압력), `delta_used_Pa`(실제로 쓴 Δ), `delta_ref_Pa`(개정 6 7절 기준 Δ: 해제 훅 $c$에서 잠김 법칙의 $p_{r0}-p_{r,locked}(c_{rel})$, $k_{out}$ 유한이면 $G_r k_h/(k_2 A_{ann})$. $G_r/A_{ann}$를 쓰지 않는다), `V_Pa`(구간 $\sum\lvert\Delta\hat p\rvert$), `D_m`(구간 $\max\lvert s_{ref}-s_{ref}(t_{rel})\rvert$), `p_start_Pa`(시드가 있으면 시드), `p_hat_start_Pa`, `k_h_at_rel_N_m`, `was_lifted`(해제 직전 잠김 동안 그 다리 패드가 공중이었는지: `airborne` 또는 패드 수직력 ≤ 0이 있었는지), `t_end_s`, `end_reason`(`lock` / `run_end`), `p_end_Pa`, `w_end`, `shift_sum_m`(구간 동안 훅마다 실제 `shift_reference`에 넣은 값의 **훅 정확 누적**, 부호는 $s_{ref}$ 기준. 1 ms 표본 차분으로 만들지 않는다), `clipped_steps` |
| 시험 | 단위: 몸체 고정 L2b 1다리로 M2-14와 같은 사건(뜬 FR, 로드 약 85 bar, 해제 후 재접근)을 만든다. `shift_sum_m`이 개정 5 3.1 $S_{M2}$와 1 µm + $(A_{ann}/(\beta A_h))VD$ 안이고, `delta_used − delta_ref`의 이동 환산이 < 0.2 µm인지 확인한다($k_{out}$ 유한·무한 각 1건). 옵션 없는 실행에는 키가 없다 |

> **r5 위에서 구현(사용자 결정 11-07)**: M2 r5(B안 앵커, 하네스·L2b, `hyd_s3\r5_spec.md`)가 먼저 들어간다. 이 명세의 구현은 r5 커밋 위에서 하고, 1·2단계 r5 재실행·재판정 뒤에 착수한다(`stage3_plan.md` 0.2절). T4-A는 두지 않는다. R-6에는 ③ 옵션 재생 `--extend-start tracked_bound`(`p3_extend_start_spec.md` 4절 #8)를 더한다.

### R-1b 앵커 계수기 (개정 6 4.5절, r5)

`result.json` `hydraulics_record`에 다리별로 `ext_lock_excess_count`(신장 뒤 잠금 중 $p_{r0}-p_{ext}$ > 0.1 bar), `ext_lock_excess_max_bar`, `ext_lock_risk_count`(> 11 bar), `ext_lock_knee_max_kN`을 둔다. 잠금마다 $p_{tr}$, $p^*$, $p_{r0}$, $dF_{knee}$를 R-1 해제 기록과 같은 파일에 남긴다. 하네스 기록(python-expert, r5 명세)과 이름을 같게 한다.

### R-2 M2 잘림 시각과 이륙 분리

- `release.shift_m(...)` 호출(`l2b_actuator.py:615`)에 `t_s=<훅 시각>`을 넘겨 `RodReleaseShift.clip_times_s`가 채워지게 한다. 하네스와 같은 함수다.
- 실행 끝에 R-3의 $t_{lift}$로 하네스와 같은 키를 낸다: `m2_clipped_steps_pre_lift`, `m2_clipped_steps_post_lift`, `m2_clip_split_t_lift_s`, `m2_law`. 이륙이 없으면 null을 넘겨 모두 post로 센다. 하네스의 `harness_hydraulics.last_armed_record(t_lift_s)` 분리 함수를 그대로 부르고 복제하지 않는다.
- 위치: `v5_plant.plant_records`(또는 `rod_release_record`)에 $t_{lift}$ 인자를 더한다.

### R-3 Chrono 이륙 시각

| 항목 | 내용 |
|---|---|
| 정의(개정 6 5절, D-a 반영) | 단계가 `idle`·`check`·`touch`가 아니고 크롤러 법선 수직력 $F_{cr,n}$ ≤ 0인 첫 1 ms 표본의 시각(`== 0.0` 아님) |
| 강체 입력(새 키) | `L2bPadRecorderS8` `V5_FIELDS`에 `crawler_normal_N`(float64, 표본 스텝 끝 `superstructure.GetContactForce()`·`n_world`), `crawler_normal_max_interval_N`(float64, 표본 사이 10스텝 최댓값, `F_pressure_max_interval` 방식), 선택 `crawler_contacts_active`(int16). v5 옵션 행에서만 쓰고, 옵션 끈 실행의 기존 배열은 비트 동일 |
| 토양 입력 | `step_series.npz` `scm_crawler_normal_N`(이미 1 ms) |
| 단계 | `verdict_metrics.chunk_phases` 규칙. 입력 `s8_series.npz` `t`·`phase`, 없으면 `r8_series.npz` |
| 출력 | `result.json` `hydraulics_record`: `t_lift_s`, `t_lift_sus_s`($F_{cr,n}$ ≤ 0.01 $W$가 끝까지 유지되기 시작한 시각), `t_lift_basis`(`1ms`/`bracket_10Hz`), `relift_contacts`(재접촉 표본 수·최대·마지막 시각), `false_liftoff`(이륙 뒤 0.01 $W$ 초과가 0.1 s 넘게 이어졌는지), `m2_clipped_steps_in_lift_transient`([t_lift, t_lift_sus] 안 잘림 수) |
| 10 Hz 대체 | 1 ms 크롤러 기록이 없으면 $t_a$(> 0 마지막 10 Hz), $t_b$(≤ 0 첫 10 Hz). split = $t_a$ + 1 ms, $(t_a, t_b)$ 사이 잘림 수를 `m2_clipped_steps_unresolved`로 |
| 시험 | 저장 V0 강체 기록 하나에서 값이 나오고 LOC 이전임을 확인. 토양 `probe_vb`(1 ms)에서 41.401 s 근처가 나오는지(dynamics-expert 실측) |

### R-4 Chrono 잠금 창 정합

- `04_scripts/04_hydraulic/coupled/lock_window_alignment.py`의 함수를 그대로 쓰고, Chrono 입력 어댑터만 더한다(`chrono_lock_window.py` 또는 같은 파일의 함수).
- 입력: `r8_series.npz` `issued_u`(작용 명령은 한 표본 뒤), 감시기 설정 meta(`lock_window_valve_tau_s`, `lock_window_eps_m_s`, `lock_window_closing_delay_s`, 주기), `pads.npz` `law_locked` 전이(1 ms, −1은 잠김으로 본다), 제어기 meta `fallback_lock_log`·`fallback_lock_current`.
- 출력: 하네스 `lock_window_alignment` 결과와 같은 키(`n_late_by_leg`, `n_late_fallback`, unjudged 수, 대체 다리 창 대조 최대 차).
- 판정 도구 출력이다(실행 폴더에 쓰지 않는다).

### R-5 (선택) 1 ms M2 상태

`pads.npz` `V5_FIELDS`에 `m2_p_hat_Pa`, `m2_shift_cum_m`(다리별, M2 켬 행만)을 더한다. 해제 구간을 하네스 함수로 오프라인 재생하는 대조에 쓴다. 비용이 크면 생략하고 보고한다.

## 2. 판정 도구 R-6 `chrono_t45_replay.py`

위치: `04_scripts/04_hydraulic/coupled/chrono_t45_replay.py`. 사용: `python -I -B … chrono_t45_replay.py <out_json> <case_or_batch> [...] [--t5]`. 정의는 개정 6 4절이고, 아래는 구현 요구다.

| # | 요구 |
|---|---|
| 1 | 입력: `contact_episode.build_episode(case_dir)`로 10 Hz 표. 진값은 `pads.npz` `F_pressure`를 직접 읽는다(`true_force_N` 쓰지 않음). 정렬: `j = searchsorted(t_pads, t_k − 1e-9)`, $\lvert t_{pads,j}-t_k\rvert$ ≤ 0.5 ms. `law_locked`·`airborne`·`F_pressure_min_interval`도 같은 $j$ |
| 2 | 설정 재구성: `t4h_replay.run_config`와 같은 방식(Chrono 프리셋 = 실행 meta의 제어기 설정 + `apply_lock_window`, $\tau_v$ = 실행 meta 밸브 값). 다시 만든 `two_pressure.to_meta()`가 `result.json` 제어기 meta와 같지 않으면 예외 |
| 3 | T4-0: 강제 없이 `replay_fallback_monitor(episode, events=실제 사건, …)`. 결과 `lower`가 `episode["lower_reading_N"]`과 비트(또는 상대 1e-12) 같은지. 영점(`zero_offset_N`)·E-6 공제(`offset_allowance_N`, `offset_allowance_from_s`)는 실행 meta에서 읽는다. 다르면 그 행 `t4_0: false`, 판정 값 출력 안 함 |
| 4 | T4: 네 다리 `(t_0, WARN_ROD_PRESSURE_FALLBACK:<leg>)` 강제. 판정 표본 = 작용 명령 0.0 & 진값 있음. 분류 `locked`(1)/`tail`(0)/`unarmed`(−1, 판정 안 함). 초과 = `lower − F_p` > 600 N |
| 5 | T5(`--t5`): 다리별, 명령 0 구간별, 구간 안 모든 표본 m에서 그 다리만 대체 시작. 비용을 줄이려면 m 직전까지의 감시기 상태를 `copy.deepcopy`로 저장해 재사용해도 된다. 단 T5 결과가 순진한 전체 재생과 같은지 한 행에서 대조한다 |
| 6 | 출력(행마다): `t4_0`, `settings_equal`, 다리별 `judged_locked`, `judged_tail`, `unarmed`, `airborne_judged`, `over_0p6kN_locked/tail`, `max_excess_N`(+ 시각·분류), `max_excess_vs_window_min_N`, 과보수 p50/p90/p99(구간 끝), `tail_ready_extend_samples`, T5 `starts`, `over_0p6kN`, `max_excess_N`. 요약: 18행 합, 결과 문구 후보 |
| 7 | 단위 시험: (a) 하네스 T4h 기록과 같은 형식 합성 Episode에서 `t4h_replay`와 같은 값, (b) 3단계 밖의 저장 V0 Chrono 기록(FINAL-R-C4G2 강체 행 하나)에서 T4-0 통과, (c) 정렬 허용 밖 표본은 진값 없음 |

## 3. 새 묶음과 행 정의 (`s9_batch.py`, `run_S8C.py`)

### 3.1 공통

- 강체 행은 FINAL-R 형식(`s8c: True`, `fixed_pcore`는 compute-scheduler 배치에 맡긴다)이다. argv = `S8C + ["run", "--set", <set>, "--only", <id>, "--tag", f"v5s3_{setting}_{id}", "--approved", "--workers", "p7"] + <설정 인자>`.
- 행 키: `criteria_id`(개정 6 3절 번호), `v5_setting`(`VB`·`LS1`·`LS4`·`V0`·`V0v`), `group`, `rep_bundle`, `source_run`(V0 짝 또는 저장 행), `pair_case`(짝 행 이름), `est_s`(`stage3_plan.md` 7.3), `note`.
- 상수 추가: `V5_VB_RIGID_ARGS = V5_VB_ARGS − valve_tau_s`, `V5_LS_ARGS = {"LS1": (0.01, 0.05), "LS4": (0.02, 0.1)}`.
- 모든 행의 제어기는 `final_C4G2`다. 토양 행은 `--expect-controller final_C4G2`를 쓰고, 강체 행은 `code_at_launch`에 제어기 해시를 기록한다(FINAL-R 선례).

### 3.2 묶음

| 묶음 | 행 | 설정 | 비고 |
|---|---|---|---|
| `V5-T45` | 개정 6 3절 1~12(`p1r`) | VB 강체 | 12 |
| `V5-T45LS` | K0V_top_fup3.5_Fs0, E_G4_Fs8, E_RE1bF_Fs8 × LS1·LS4 | VB에서 `--lock-overlap-ratio`·`--lock-closing-delay-s`만 바꿈 | 6, 이름 `…_LS1`, `…_LS4`(태그·폴더) |
| `V5-R12` | E_G4_Fs4 VB, E_G4_Fs4_ph0.05 VB, E_G4_Fs4_ph0.05 V0 | VB / V0(인자 없음) | 3 |
| `V5-REC` | `G1R_FS24_FL_top_o050_Fs0` VB, V0 | VB / V0 | 2, 새 세트 `v5rec`(3.3) |
| `V5-VB` | 기존 그대로(S1·S6·S8) | VB 토양 | 3, 변경 없음 |
| `V5-V0V` | `V5-VB`와 같은 3행, `case` 뒤 `_v0v` | 저장 argv + `--valve-tau-s 0.1` | 3, `source_expected_diffs = {"valve_tau_s": 0.1}` |
| `V5-S6SEED` | 기존 그대로 | | 5, 변경 없음 |
| `V5-STAGE3` | 위 7묶음의 합 | | **34**. 실행 편의용 합본(행 이름 중복 없음 확인) |

### 3.3 새 행 `G1R_FS24_FL_top_o050_Fs0` (`run_S8C.py`)

- C-S8-72 `G1R_FS24_FL_top_Fs0`(사건 FS24, 다리 FL, 앵커 READY, 상단, $F_s$ 0)과 같은 사건·앵커이고 **위상만 0.050 s**다.
- 이름은 C-S8-74 규칙 `_c74_case_id("FS24", "FL", G1_READY_ANCHOR, 0.050, "top", 0.0)` = `G1R_FS24_FL_top_o050_Fs0`이다.
- 새 세트 `v5rec`(`SET_NAMES`에 추가)에 넣는다. 기존 `G1_CASES`·`C74_CASES`·`g1`·`c74` 세트의 정의와 해시는 바꾸지 않는다.
- 사건 시각 = READY + 5 s + 0.050 s(`run_S8C.py:1594` 규칙). 판정 값은 C-S8-72와 같은 `event_state` 기록과 `judge_chrono_v5`/S8 사건 판정기의 창 뒤 1 ms·0.5 s 값.

## 4. `check-sources` 확장

| 묶음 | 확인 |
|---|---|
| `V5-V0V` | 토양 level 행: 저장 `result.json` args 대비 차이가 `valve_tau_s` 하나 |
| 강체 묶음(`V5-T45`, `V5-T45LS`, `V5-R12`, `V5-REC`) | 지금은 `not_level`로 건너뛴다. 새 확인: (a) 행 id가 지정 세트의 `case_set`에 있음, (b) argv의 v5 인자 = 설정 정의(VB/LS/V0)와 정확히 같음(`hydraulic_options_from_args` + `flow_setting_from_args`로 파싱해 대조), (c) V0 행은 v5·유량 인자 없음, (d) 대조할 저장 실행이 없으면 `no_source`로 표시하고 실패로 보지 않음 |
| `V5-STAGE3` | 위 전부 + 행 34, 이름 중복 0 |

출력은 지금 형식(`ok` / `DIFFERS`, 종료 코드 1)을 따른다.

## 5. 회귀

| ID | 내용 | 기준 |
|---|---|---|
| B-2 | 하네스 V0 23행 황금값(`golden_off`) | 23/23 명령 해시 같음 |
| B-4 | 강체 Chrono `hash_G1L_Fs0` 재실행 | `command_hash` f624ed94…, `record`·`pads`·`r8_series`·`s8_series` 숫자 배열 전부 비트 동일(`final_c4g2_values.json` `hash_check`). `pads.npz` `meta_json` 차이는 키 목록으로 보고 |
| B-5 | 토양 짧은 행(옵션 없음, `--duration 34`) | 저장 `batch_FINAL-C4G2_20261105/P3b_J1_B_top_Fs4` 앞부분 `completion_series`·`controller_commands`·`r8_series`·`step_series`·`record` 비트 동일(`equal_nan`) |
| B-6 | `s9_batch.py check-sources` `FINAL-REP --expect-controller final_C4G2`, `V5-VB`, `V5-S6SEED`, `V5-V0V`, `V5-STAGE3` | 모두 ok |
| B-7 | `05_tests/unit` 전체, `05_tests/chrono/test_l2b_actuator.py`, `test_actuator_valve`, `test_l2b_s8`, `test_l2b_closed_loop`, `test_l2b_v5_options.py` + 새 시험(R-1~R-6) | 실패 0(지금 5,639 통과·건너뜀 7 기준) |
| B-8 | `git diff 09_paper`, `02_params/rexome33.yaml` | 변화 없음 |
| V-r5 | M2 켬 L2b 짧은 실행 1건(강체, 3단계 행이 아닌 K24_top_fdown3.5_Fs4 VB, `--duration` 짧게)에서 R-1·R-1b·R-2·R-3 키가 나오고 `m2_law` = `flow_limited_r5` | 키 존재, 값은 판정하지 않음 |

## 6. 끝 조건과 보고

- 커밋 단위: (1) R-1~R-3·R-5 기록, (2) R-4·R-6 도구, (3) 행·묶음·`check-sources`. 커밋마다 B-2와 B-7, 마지막에 B-4·B-5·B-6·B-8을 돈다. 커밋 전 integrity-checker 점검은 메인 세션이 챙긴다.
- 보고에 적을 것: 바꾼 파일·함수, 새 키 목록, 회귀 결과(숫자), `s9_batch.py list V5-STAGE3` 출력(34행과 `est_s`), T4-0 단위 시험 결과, 남은 결함.
- 3단계 VB 기록에 R-6을 돌리지 않는다(개정 6 봉인 전 금지).
