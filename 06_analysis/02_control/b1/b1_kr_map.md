# B1 K-R 대응표 (원판 9절 K-R, 경로 1 ↔ 경로 2)

- 결과 전 작성, Chrono 본 배치 미열람. 작성 시각 2026-11-12T13:10+09:00(verif-protocol-auditor). 작성에 쓴 자료: 두 도구 코드, 규칙 원판·rev1, prelaunch, G-S 배치 `batch_V5-B1-CREEP-GS_20261112_112555`(키 이름 확인만). 본 배치 `batch_V5-B1-CREEP_20261112_125134`는 열지 않았다.
- 대상 도구: 경로 1 `b1_creep_metrics.py` sha256 `6b6e04acfd0cfb77e53b35981984bd4a9e4ccad2b4ce5446b6e5e7c018dda9d9`(브랜치 `b1-path1-fix` 1ac4849), 경로 2 `path2/b1_path2.py` sha256 `7a9d258fa3182506a82fbdca74c15a1b8a37bd7858cf413f959fe0f4f52183db`(브랜치 `b1-path2-fix` 24a108e).
- 기준 규칙: 원판 `b1_creep_rules.md` 6b99702c 9절("K-R 항목", "값 대조 허용"), rev1 `b1_creep_rules_rev1.md` 9f72af5b(R1-3·R1-4).
- 이 표는 경로 대응만 정한다. 어느 경로의 값도 담지 않는다. 이 표를 경로 2 작성자에게 넘기지 않는다(원판 9절 독립성).

## 0. 공통 규약

| 규약 | 내용 |
|---|---|
| 출력 파일 | 경로 1 = `b1_metrics_path1.json`(아래 `P1.`), 경로 2 = `b1_metrics_path2.json`(아래 `P2.`). 상수는 경로 1 `b1_harness_constants_rev1.json`(= `P1.constants`), 경로 2 `--constants-out` 파일(= `P2.constants`) |
| 행 접두 | `P1.rows.<C>.metrics.` ↔ `P2.rows.<C>.m.`(C = C1~C6). 경로 2는 `VALID` 행에만 `m`·`gm`·`pred`가 있다 |
| 행 범위 | M-1~M-12 수치는 **두 경로 모두 `VALID`인 행만** 대조한다. 행 상태가 다르면 그 행은 K-01에서 이미 불일치다 |
| 다리 | 경로 1 목록 색인 i(0~3) = FL, FR, RL, RR ↔ 경로 2 사전 키 `FL`·`FR`·`RL`·`RR` |
| 모서리 | 경로 1 목록 색인 k(0~3) ↔ 경로 2 `keymap.corner_order[k]` = RR, RL, FR, FL(두 쪽 모두 `CRAWLER_XY_BOX_M` (x_min,y_min), (x_min,y_max), (x_max,y_min), (x_max,y_max) 순) |
| 패드 종류 | 경로 1 `front330`·`rear250` ↔ 경로 2 `front`·`rear` |
| 하네스 실행 이름 | 경로 1 `H-P|C1|VB|e0` 꼴(`group|row|variant|e` + eps의 `:g` 표기) ↔ 경로 2 정수 줄 번호(`b1_H.jsonl`의 빈 줄을 뺀 0부터 센 순번). 대조기는 jsonl 줄의 group·row·variant·e 필드로 줄 번호를 경로 1 이름으로 바꾼다 |
| NA | 경로 1 `"NA"` 또는 null ≡ 경로 2 null 또는 `"NA"`. 한쪽 NA·다른 쪽 수치는 불일치 |
| 시각 | 10 Hz 시각은 정수 주기 n으로만 대조한다(4.5). 경로 1의 `t_*_s`는 n × 0.1이라 따로 대조하지 않는다 |
| 표시(flags) | 등급의 표시 문자열(경로 1 한국어, 경로 2 영어)은 K-R 대상이 아니다(9절 목록에 없음). 판정서에 두 경로 표시를 나란히 적는다(제안) |

허용(9절 "값 대조 허용"): 이산 항목(상태·등급·b*·주기 번호·사건 수·참거짓·문자열·목록) 완전 일치, 길이 [m] 절대차 ≤ 1×10⁻⁹ m. 규칙에 값이 없는 단위는 아래 **제안**을 쓴다(결과 전에 채택 여부를 정한다).

| 단위 | 허용 | 근거 |
|---|---|---|
| m | 절대 1e-9 m | 규칙 9절 |
| m/s | 절대 1e-9 m/s | 제안(길이 허용을 그대로) |
| N | 절대 1e-6 N | 제안(rev1 T-15 ε_N과 같은 크기) |
| rad | 절대 1e-12 rad | 제안 |
| 무차원(f, 비, N_h Δ²/A) | 상대 1e-9 | 제안 |
| r_σ | 절대 1e-12 | 제안(T-7 (ii) 허용과 같음) |
| m/N, m/N⁵(κ_z, C_type, 할선) | 상대 1e-9 | 제안(실행 전 감사의 상수 대조 상대차 최대 2.04e-14) |
| s(t_max − t_L) | 절대 1e-9 s | 제안(n 차 × 0.1이라 사실상 이산) |

## 1. 행 상태·묶음 상태

| # | 항목 | 경로 1 | 경로 2 | 비교 | NA·주의 |
|---|---|---|---|---|---|
| K-01 | 행 상태 C1~C6 | `P1.row_states.<C>.status` | `P2.rows.<C>.status` | 완전 일치(어휘 같음: VALID, MISSING, MISSING_START, NO_LOC, INVALID) | 사유 문장(`reasons`·`why`)은 대조하지 않음 |
| K-02 | 묶음 상태 | `P1.bundle` + `P1.blocked` | `P2.bundle` | 짝: (UNDETERMINED, 무엇이든) ↔ UNDETERMINED / (COMPLETE·PARTIAL, `["E-5"]`) ↔ BLOCKED_E5 / (COMPLETE, `[]`) ↔ COMPLETE / (PARTIAL, `[]`) ↔ PARTIAL | E-5 정의가 두 경로에서 다르다(경로 1 `identity.runner_log`, 경로 2 `<case>.log` Traceback). 재감사 발견 1 참조 |
| K-03 | 종료 코드 | 0 / 1 | 0 / 1 | 완전 일치 | 2·3이면 K-R 전 입력 오류 |

## 2. M-1 시각 (VALID 행)

| # | 항목 | 경로 1 `metrics.` | 경로 2 `m.` | 비교 |
|---|---|---|---|---|
| K-04 | n_L1 | `M-1.n_L1` | `n_L1` | 완전 일치 |
| K-05 | n_L | `M-1.n_L` | `n_L` | 완전 일치 |
| K-06 | LOC 취소 수 | `M-1.loc_revokes` | `loc_revoked` | 완전 일치 |
| K-07 | n_R | `M-1.n_R` | `n_R` | 완전 일치 |
| K-08 | n_creep | `M-1.n_creep` | `n_creep` | 완전 일치 |
| K-09 | n_max | `M-1.n_max` | `n_max` | 완전 일치 |
| K-10 | n_end | `M-1.n_end` | `n_end` | 완전 일치 |
| U-01 | t_dep(n_dep) | `M-1.n_dep` | 없음 | **대응 없음**(4절) |

## 3. M-2 행정 예산

| # | 항목 | 경로 1 `metrics.` | 경로 2 `m.` | 비교 |
|---|---|---|---|---|
| K-11 | s_i(t_L) | `M-2.s_L[i]` | `s_L.<leg>` | 1e-9 m |
| K-12 | s_i(t_R) | `M-2.s_R[i]` | `s_R.<leg>` | 1e-9 m |
| K-13 | s_i,max | `M-2.s_max[i]` | `s_max.<leg>` | 1e-9 m |
| K-14 | b* | `M-2.b_star` | `b_star` | 완전 일치(동점 처리가 다름: 경로 1 ε_th 안 첫 다리, 경로 2 정확한 argmax — 실행 전 감사 기록 (1)) |
| K-15 | g | `M-2.g_m` | `g` | 1e-9 m |
| K-16 | SGS 첫 주기 | `M-2.n_sgs` | `n_sgs` | 완전 일치 |
| K-17 | WARN_LIFT_STROKE_LIMITED 첫 주기 | `M-2.n_warn_lift` | `n_warn_lift` | 완전 일치 |
| K-18 | SGS 여부 | `is_sgs` | `sgs` | 완전 일치 |

## 4. M-4 침하

| # | 항목 | 경로 1 `metrics.M-4.` | 경로 2 `m.` | 비교 |
|---|---|---|---|---|
| K-19 | n_e | `n_e` | `n_e` | 완전 일치 |
| K-20 | n_e,i | `n_e_leg[i]` | `n_e_leg.<leg>` | 완전 일치 |
| K-21 | n_max,i | `n_max_leg[i]` | `n_max_leg.<leg>` | 완전 일치 |
| K-22 | z_i(t_L), z_i(t_R), z_i(t_max), z_i(t_e), z_i(t_end) | `z_L`, `z_R`, `z_max`, `z_e`, `z_end` `[i]` | `z.L`, `z.R`, `z.max`, `z.e`, `z.end` `.<leg>` | 1e-9 m(5 × 4값) |
| K-23 | Δz^post_i | `dz_post[i]` | `dz_post.<leg>` | 1e-9 m |
| K-24 | Δz^post_(i,e_i)(다리별 창) | `dz_post_leg_window[i]` | `dz_post_leg.<leg>` | 1e-9 m |
| K-25 | z(t_max) − z(t_L) | `dz_L_to_max[i]` | `dz_L_max.<leg>` | 1e-9 m |
| K-26 | z(t_R) − z(t_max) | `dz_max_to_R[i]` | `dz_max_R.<leg>` | 1e-9 m |
| K-27 | z(t_R) − z(t_L) | `dz_L_to_R[i]` | `dz_L_R.<leg>` | 1e-9 m |
| K-28 | z(t_end) − z(t_R) | `dz_R_to_end[i]` | `dz_R_end.<leg>` | 1e-9 m |
| K-29 | 할선 Δz/ΔF(t_L → t_R) | `secant_L_to_R_m_per_N[i]` | `secant.<leg>` | 상대 1e-9(제안) |
| X-01 | LOC 뒤 최대 침하율 | `max_rate_after_L_m_s` | `max_sink_rate` | **제외(한 경로 기록, 판정서 공개)** — 사용자 결정 2026-11-12 |
| U-02 | M-4h 패드 수평 변위·요 변화 | `metrics.M-4h` | 없음 | **대응 없음** |

## 5. M-5 과도 초과

| # | 항목 | 경로 1 `metrics.M-5.` | 경로 2 `m.` | 비교 |
|---|---|---|---|---|
| K-30 | δ^os_i | `delta_os[i]` | `dos.<leg>` | 1e-9 m. t_R 없으면 둘 다 null |
| K-31 | t_max − t_L | `t_max_minus_t_L_s` | `t_max_minus_L` | 1e-9 s(제안) |

## 6. M-6 예측자 오차와 7.1·7.2 LOC 주기 입력

| # | 항목 | 경로 1 | 경로 2 | 비교 |
|---|---|---|---|---|
| K-32 | ŝ^(q) at b*(q = P-A, P-B, P-D, P-G, P-C) | `metrics.M-6.predictions.<q>[b*]` | `rows.<C>.pred.s_hat.<q>` | 1e-9 m |
| K-33 | e(q) at b* | `metrics.M-6.errors.<q>[b*]` | `rows.<C>.pred.e.<q>` | 1e-9 m |
| K-34 | e(q) at 계획 예산 다리 b(2.1 표) | `metrics.M-6.errors.<q>[b]`(b = `rows.<C>.b`) | `rows.<C>.pred_planned_leg.e.<q>` | 1e-9 m |
| K-35 | 하한 표시(7.4) | `metrics.M-6.lower_bound` | `m.sgs` | 완전 일치 |
| K-36 | P-G 모서리 k* | `metrics.M-6.p_g_terms.k_star`(색인) | `rows.<C>.pred.rec.k_star`(이름) | 모서리 규약으로 바꿔 완전 일치 |
| K-37 | ρ_(k*) | `metrics.M-6.p_g_terms.rho_k_star` | `rows.<C>.pred.rec.rho_k_star` | 1e-9 m |
| K-38 | Ẑ_(k*) | `metrics.M-6.p_g_terms.Z_hat_k_star` | `rows.<C>.pred.rec.Zhat_k_star` | 1e-9 m |
| K-39 | 자세 입력 (φ̂_L, θ̂_L) | `metrics.predictor_inputs.att_L_rad[0]`, `[1]` | `m.loc_inputs.phi`, `theta` | 1e-12 rad(제안) |
| K-40 | ĉ(t_L) | `metrics.predictor_inputs.c_hat_L_m` | `m.loc_inputs.c_hat` | 1e-9 m |
| K-41 | ĉ_k(t_L) | `metrics.predictor_inputs.c_hat_corner_L_m[k]` | `m.loc_inputs.c_hat_corner.<corner>` | 1e-9 m |
| K-42 | Δs^geo_i | `metrics.predictor_inputs.ds_geo[i]` | `m.loc_inputs.ds_geo.<leg>` | 1e-9 m |
| K-43 | ρ_k | `metrics.predictor_inputs.rho[k]` | `m.loc_inputs.rho.<corner>` | 1e-9 m |
| K-44 | Ŵ_i, Ê_i, F^pk_L,i | `metrics.predictor_inputs.W_hat[i]`, `E_hat[i]`, `F_pk[i]` | `m.loc_inputs.W_hat.<leg>`, `E_hat.<leg>`, `F_pk.<leg>` | 1e-6 N(제안) |
| K-45 | 합 비 ΣF/ΣW^static | `metrics.predictor_inputs.load_sum_over_static` | `m.loc_inputs.sum_ratio` | 상대 1e-9(제안) |
| U-03 | 예측·오차의 나머지 두 다리 | `M-6.predictions`·`errors`의 b*·b 밖 다리 | 없음 | **대응 없음** |
| U-04 | P-G 보조 값 Δẑ_i, 틈 항, 네 모서리 Ẑ_k | `M-6.p_g_terms.dz_hat`, `lift_m`, `Z_hat` | 없음 | **대응 없음** |

- K-32~K-38은 7.2 식의 입력이 같아야 같다. 입력(K-39~K-45)을 같이 대조하면 불일치 원인을 좁힐 수 있다.
- 경로 2는 n_L 주기의 s·자세·ĉ·하중 가운데 하나라도 없으면 `loc_inputs` 전체가 null이고 모든 예측이 null이다. 경로 1은 항목별로 null이다. 6절 "R-C1이 빠지면 M-6·D-d NA"에서는 같은 결론이지만, 하나만 빠진 경우 K-39~K-45의 나머지 값이 한쪽에만 있을 수 있다. 이 경우 K-39~K-45는 불일치로 세되 그 원인을 판정서에 적는다(제안).

## 7. M-7, M-8, M-9, M-10

| # | 항목 | 경로 1 | 경로 2 | 비교 |
|---|---|---|---|---|
| U-05 | M-7 크롤러(t_L·t_R·t_end의 ĉ와 격자 참 틈, P3-5 틈, 이탈 뒤 최대 크롤러 하중) | `metrics.M-7.c_hat_m.*`, `clear_true_m.*`, `p3_5.*`, `crawler_max_after_departure_N` | 없음(ĉ(t_L)만 K-40) | **대응 없음** |
| K-46 | M-8 E3c10 사건 목록 | `metrics.M-8.E3c10` | `m.e3_events` | 목록 완전 일치 |
| K-47 | M-8 R4c30 사건 수 | `len(metrics.M-8.R4c30)` | `m.r4_events` | 완전 일치 |
| K-48 | M-8 LOC 취소 수 | `metrics.M-8.loc_revoked` | `m.loc_revoked` | 완전 일치 |
| K-49 | M-8 SGS | `metrics.M-8.sgs > 0` | `m.sgs` | 완전 일치(경로 2는 참거짓만) |
| U-06 | M-8 나머지(`..._SKIPPED:order` 수, `order_gate.decisions` 수, DSb75 HOLD 수·RELEASE 사유, P30fz, LWa, SGS 사건 수) | `metrics.M-8.R4_skipped_order`, `order_gate_decisions`, `dsb75_hold`, `dsb75_release_reasons`, `P30fz_pauses`, `LWa_restarts`, `sgs` | 없음 | **대응 없음** |
| U-07 | M-9 P3 행 | `metrics.M-9` | 없음 | **대응 없음** |
| K-50 | M-10 s_max 짝 차(b*) | `P1.pair_differences.<C>.s_max` | `m.s_max.<b*> − (rows.<C>.M10` 가운데 `variant` VB·`e` 0인 항목`).s_max_b` | 1e-9 m |
| K-51 | M-10 Δz^post 짝 차(b*) | `P1.pair_differences.<C>.dz_post` | `m.dz_post.<b*> − (M10` VB·e0`).dz_post_b` | 1e-9 m |
| K-52 | M-10 하네스 s_max 산포(VB·V0 × e0·e0.002) | `P1.pair_differences.<C>.harness_s_max_spread` [min, max] | `rows.<C>.M10[].s_max_b`의 [min, max] | 1e-9 m |
| U-08 | M-10 s_L·s_R·δ^os·g 짝 차 | `P1.pair_differences.<C>.s_L`, `s_R`, `delta_os`, `g` | 없음 | **대응 없음** |

- K-50~K-52의 짝 묶음은 C1~C5 = H-P, C6 = H-W(두 경로 같음).

## 8. M-11 격자 인자 (VALID 행, τ ∈ L, R, max, e, end, 다리 i)

| # | 항목 | 경로 1 `rows.<C>.grid.points.<τ>[i].` | 경로 2 `rows.<C>.gm.<τ>.<leg>.` | 비교 |
|---|---|---|---|---|
| K-53 | 기록 상태 | `state` = `no_record` / `invalid` / `valid` | 값 null / `valid` 거짓 / `valid` 참 | 완전 일치 |
| K-54 | N_h | `N_h` | `N_h` | 완전 일치(정수) |
| K-55 | N_h Δ²/A | `N_h_d2_over_A` | `NhD2_over_A` | 상대 1e-9(제안) |
| K-56 | b_hull | `b_hull_m` | `b_hull` | 1e-9 m. K-53이 valid인 칸만 |
| K-57 | r_σ | `r_sigma` | `r_sigma` | 1e-12(제안). K-53이 valid인 칸만 |
| K-58 | f | `f` | `f` | 상대 1e-9(제안). K-53이 valid인 칸만 |
| K-59 | z/f, δ^grid | `z_over_f`, `delta_grid` | `z_over_f`, `delta_grid` | 1e-9 m. K-53이 valid인 칸만(경로 2는 invalid 칸에도 값을 낸다) |
| K-60 | δz_1n | `dz_1n` | `dz_1n` | 1e-9 m. K-53이 valid인 칸만(경로 1은 기록 없는 칸에도 값을 낸다) |
| K-61 | Δz^post,corr_i | `rows.<C>.grid.dz_post_corr[i]` | 유도: `gm.e.<leg>.z_over_f − gm.L.<leg>.z_over_f`(두 칸 모두 valid일 때, 아니면 null) | 1e-9 m |
| K-62 | z(t_e)(f(t_e) − f(t_L)) at b*(C-5 (다)) | `rows.<C>.grid.z_e_df_eL[b*]` | `P2.grades.D-a.records.<C>.grid_change`(R 행만) | 1e-9 m |
| U-09 | z(t_max)(f(t_max) − f(t_L))(C-5 (다) 참고), T-7 (i)·(ii) 따로, b* 밖 다리의 K-62 | `grid.z_max_df_maxL`, `points.*.check_i`·`check_ii`, `z_e_df_eL[i≠b*]` | 없음 | **대응 없음** |

- 6절 pad_nodes 일치: 경로 1 `rows.<C>.pad_nodes_check.consistent` ↔ 경로 2 `pad_nodes_check.<C>.mismatch`의 부정. K-R 9절 항목은 아니지만, 다르면 K-53이 갈리므로 같이 본다(경로 1은 8필드 완전 일치, 경로 2는 5필드 상대 1e-12. G-S 두 행에서는 두 기준 모두 차이 0).

## 9. M-12 LOC 앵커

| # | 항목 | 경로 1 | 경로 2 | 비교 |
|---|---|---|---|---|
| X-02 | Chrono M-12 전부 | `P1.m12.chrono.*`, `rows.<C>.shadow` | `rows.<C>.m12` | **제외(한 경로 기록, 판정서 공개)** — 사용자 결정 2026-11-12 |
| X-03 | E_P-A*·e(P-A*)·T-13 "앵커 단일 표본 의존"(Chrono·하네스 모두) | `P1.m12.E_P_A_m`, `E_P_A_star_m`, `anchor_single_sample`, `m12.harness.<run>.e_P_A_star_m` | 없음 | **제외(한 경로 기록, 판정서 공개)** — 사용자 결정 2026-11-12 |
| K-63 | 하네스 그림자 사용 가능(H-SH0 짝 해시 같음) | `P1.shadow_pairs.all_same` | `P2.shadow_hash_ok` | 완전 일치 |
| K-64 | 하네스 LOC별 경로 ①②③, n_P, n_L | `P1.m12.harness.<run>.locs[j].path`, `n_P`, `n_L` | `P2.harness_m12.<줄 번호>.locs[j].path`, `n_P`, `n_L` | 완전 일치. 실행 이름은 0절 규약 |
| K-65 | 하네스 c_min(t_P), ĉ(t_L), ĉ_A(t_L), d | `locs[j].c_min_tP_m`, `c_hat_m`, `c_hat_A_m`, `d_m` | `locs[j].c_min_tP`, `c_hat_now`, `c_hat_A`, `d` | 1e-9 m |
| K-66 | 하네스 max\|d\| | `P1.m12.harness.<run>.max_abs_d_m` | 유도: `harness_m12.<줄 번호>.locs[].d` 절대값 최대 | 1e-9 m |

- 경로 1은 그림자 기록이 없는 실행을 `"NA"`로 적고, 경로 2는 그 줄을 출력하지 않는다. 그림자 켬 줄 집합(H-P 20 + H-W 4 + H-M0 4, 하네스 meta 기준)에서만 대조한다(제안).

## 10. 7.2 m_L

| # | 항목 | 경로 1 `rows.<C>.metrics.predictor_inputs.` | 경로 2 `rows.<C>.m.` | 비교 |
|---|---|---|---|---|
| K-67 | m_L | `m_L.m_L_m` | `m_L` | 1e-9 m |
| K-68 | m_L 출처 | `m_L.source` = `INFO_LOC_CLEARANCE_MARGIN` / `INFO_LOC_FLAT_SOIL_MARGIN` / null | `m_L_src` = `E3c10` / `R4c30` / `none` | 어휘를 바꿔 완전 일치 |
| K-69 | T-14 대조 | `t14.checked`, `t14.ok` | `t14_ok` | 짝: (checked 거짓) ↔ null, (checked 참, ok 참) ↔ 참, (checked 참, ok 거짓) ↔ 거짓 |

- 하네스 실행의 m_L은 경로 2 출력에 없다(U-10).

## 11. 7.3 상수 (하네스에서만, 지금 대조 가능)

| # | 항목 | 경로 1 `constants.` | 경로 2 `constants.` | 비교 |
|---|---|---|---|---|
| K-70 | κ_z,F / κ_z,R | `kappa_z_m_per_N.front330` / `.rear250` | `kappa.front` / `.rear` | 상대 1e-9(제안) |
| K-71 | C_type,F / C_type,R | `C_type.front330` / `.rear250` | `C_type.front` / `.rear` | 상대 1e-9(제안) |
| K-72 | δ_allow | `delta_allow_m` | `delta_allow` | 1e-9 m |
| K-73 | 적합·제외 다리 수(κ·C, 종류별) | `fit.<t>.kappa_fit`, `kappa_excluded`, `c_fit`, `c_excluded` | `kappa_fit_legs.<t>`, `kappa_excluded_legs.<t>`, `C_type_fit_legs.<t>`, `C_type_excluded_legs.<t>` | 완전 일치(주: 경로 1은 Δz 또는 Ŵ가 NA인 다리를 제외 수에 넣고, 경로 2는 세지 않는다. 지금 하네스에서는 실행 전 감사가 수 일치를 확인했다) |
| K-74 | 적합 다리 목록 | `fit.<t>.kappa_fit_legs`, `c_fit_legs`(`run|leg` 문자열) | `kappa_fit_list.<t>`, `C_type_fit_list.<t>`(group·row·variant·e·leg 사전) | 집합 완전 일치(0절 이름 규약) |
| K-75 | 최대를 정한 실행·다리 | `fit.<t>.kappa_argmax`, `c_argmax` | `kappa_argmax.<t>`, `C_type_argmax.<t>` | 완전 일치(0절 이름 규약) |
| K-76 | κ 비, κ 비선형 | `kappa_ratio.<t>.ratio`, `kappa_ratio.<t>.kappa_nonlinear` | `kappa_ratio.<t>`, `kappa_nonlinear.<t>` | 비 상대 1e-9(제안, `inf`는 문자열 일치), 표시 완전 일치 |
| K-77 | R1-3 감도 W_fit 600·2,000 N | `sensitivity."600"`·`."2000"`의 K-70·K-71·K-73~K-76 항목 | `sensitivity."600"`·`."2000"`의 같은 항목 | K-70~K-76과 같은 방법 |
| K-78 | 쓴 실행 목록 | `runs_used` − `no_loc_runs` | `runs_used`(줄 번호) | 집합 완전 일치(0절 이름 규약) |
| K-79 | R1-4 하네스 기록(H-P·H-W·H-M0) | `redistribution_records.<run>.n_L`, `load_sum_over_static`, `W_hat`, `E_hat_minus_F_pk`, `stroke_rate_at_n_L_m_s`, `flags` 비어 있지 않음 | `P2.harness_R1_4.<줄 번호>.record.n_L`, `sum_ratio`, `W_hat`, `E_minus_Fpk`, `stroke_speed_nL`, `redistribution_assumption_off` | n_L·표시 완전 일치, 비 상대 1e-9, N 1e-6, m/s 1e-9(제안) |
| K-80 | R1-4 Chrono 행 기록 | `rows.<C>.metrics.R1-4.*`(K-79와 같은 키) | `rows.<C>.R1_4.*`(K-79와 같은 키) | K-79와 같음 |

- K-70~K-79는 하네스와 상수 파일만 쓰므로 Chrono 결과 전에 대조할 수 있다(실행 전 감사가 K-70·K-71·K-73·K-74 일치를 이미 확인).

## 12. 4.4 문턱별 행별 분류

| # | 문턱 | 경로 1 | 경로 2 | 비교 |
|---|---|---|---|---|
| K-81 | T-3 D-c 행별 보정 분류 | `P1.grades.D-c.per_row.<C>.corr_class` = `+`·`-`·`0`·`undetermined` | `P2.grades.D-c.signs.<C>` = `+`·`-`·`0`·`?` | `undetermined` ↔ `?`로 바꿔 완전 일치. 경로 1에는 z(t_max)가 없는 행도 `undetermined`로 있고 경로 2에는 그 행이 없다 → 그런 행은 대조에서 뺀다(제안) |
| K-82 | T-3 D-c 행별 원시 분류 | `per_row.<C>.raw_class` | `raw_signs.<C>` | K-81과 같음(이 경우 두 경로 모두 행이 있다) |
| K-83 | T-5 D-e 행별 충족 | `P1.grades.D-e.per_row.<C>.meets` | 유도: `rows.<C>.g_tilde`가 null이 아니고 `g_tilde − 0.020 ≥ −1e-9`이고 `sgs` 거짓 | 완전 일치 |
| K-84 | T-7 격자 기록 유효성(행·τ·다리) | K-53 | K-53 | K-53과 같음 |
| K-85 | T-8 다리 부상(행별) | `P1.safety_notes.<C>`에 `T-8 leg <다리>` 문장 | `P2.rows.<C>.m.safety.leg_liftoff`(다리 목록) | 다리 집합 완전 일치(경로 1은 안전 기록이 있는 행만 키가 있다 → 없으면 빈 집합) |
| K-86 | T-9 크롤러 재착지(행별) | `P1.safety_notes.<C>`에 `T-9` 문장 있음 | `P2.rows.<C>.m.safety.crawler_retouch` | 참거짓 완전 일치 |
| K-87 | T-11 V-1 끝 시각 | K-01에 들어 있음 | K-01 | — |
| K-88 | T-12 P-2 크리프 정지 | K-08 | K-08 | — |
| K-89 | T-14 | K-69 | K-69 | — |
| X-04 | T-13 | — | — | **제외**(X-03) |

- T-1·T-2·T-4·T-6은 행별이 아니라 묶음 값 비교라 13절 등급에서 본다. T-10은 도구 밖(prelaunch).

## 13. 등급 D-a~D-h와 계산 행 목록

| # | 등급 | 경로 1 `P1.grades.<code>.` | 경로 2 `P2.grades.<code>.` | 비교 |
|---|---|---|---|---|
| K-90 | D-a 등급·원시·보정 | `grade`, `raw_grade`, `corr_grade` | `grade`, `raw`, `corr` | 완전 일치(`corr_grade` "NA" ↔ `corr` null) |
| K-91 | D-a 수치 | `Z_ch`, `Z_corr`, `Z_hn` | `Z_ch`, `Z_corr`, `Z_hn` | 1e-9 m |
| K-92 | D-a 계산 행 | `rows` | `rows`에서 `rows.<C>.m.dz_post`가 null인 행을 뺀 것 | 집합 완전 일치 |
| K-93 | D-a 하네스 보정량 | `harness_correction_m` | `correction_m` | 1e-9 m. **정의가 다름**: 경로 1은 (원시 ZA-2, 보정 ZA-1)일 때만, 경로 2는 최종 ZA-2이면 항상 값(실행 전 감사 기록 (3), 미수정). (원시 ZA-2, 보정 ZA-2 또는 NA)이면 구조적으로 갈린다 |
| K-94 | D-b 등급·O | `grade`, `O_m` | `grade`, `O` | 등급 완전 일치, O 1e-9 m |
| K-95 | D-b 계산 행·뺀 행 | `rows`, `dropped_no_ready` | `rows` − `na_rows`, `na_rows` | 집합 완전 일치 |
| K-96 | D-c 등급·원시 등급 | `grade`, `raw_grade` | `grade`, `raw_grade` | 완전 일치 |
| K-97 | D-c 행별 수치 | `per_row.<C>.raw_m`, `corr_low_m`, `corr_high_m` | `detail.<C>.delta_raw`, `corr_lo`, `corr_hi` | 1e-9 m |
| K-98 | D-c 행별 대체 범위·절점 계단 | `per_row.<C>.flags`에 `대체 범위` / `절점 계단 수준` | `detail.<C>.substitute` / `node_step_level` | 참거짓 완전 일치 |
| K-99 | D-c 계산 행 | `rows` 가운데 z(t_max)가 있는 행(`flags`에 `침하 기록 없음`이 없는 행) | `rows` | 집합 완전 일치 |
| K-100 | D-d 등급·q*·E_q | `grade`, `q_star`, `E_q.<q>` | `grade`, `q_star`, `E.<q>` | 등급·q* 완전 일치, E_q 1e-9 m(NA ↔ null) |
| K-101 | D-d 계산 행·T-14 제외 행 | `rows`, (5행 R 가운데 VALID) − `rows` | `rows`, `excluded_t14` | 집합 완전 일치 |
| K-102 | D-e 등급·행 | `grade`, `rows` | `grade`, `rows`의 키 | 완전 일치 |
| K-103 | D-e 행별 g, g^corr, g̃, SGS | `per_row.<C>.g_m`, `g_corr_m`, `g_tilde_m`, `sgs` | `rows.<C>.g`, `g_corr`, `g_tilde`, `sgs` | 1e-9 m, SGS 완전 일치 |
| K-104 | D-f 등급 | `grade` | `grade` | 완전 일치 |
| K-105 | D-f 계산 짝 수 | `len(rows) − 1`(rows = C5 + 쓴 H-M0 짝) | `pairs`(정수) | 완전 일치. 경로 2에 짝 이름 목록이 없다(U-11) |
| K-106 | D-g 등급·수치 | `grade`, `e_C6_m`, `E_q_star_m`, `ratio` | `grade`, `e_C6`, `E_q`, `ratio` | 등급 완전 일치, e·E 1e-9 m, 비 상대 1e-9(제안) |
| K-107 | D-g 계산 행 | `rows`(`["C6"]` 또는 빈 목록) | 없음(암묵 C6) | 경로 2 등급이 W-NA가 아니면 `["C6"]`로 본다(제안) |
| K-108 | D-h 등급 | `grade` | `grade` | 완전 일치. 등급 순위가 다름: SAME과 NA가 섞이면 경로 1 K-NA, 경로 2 K-SAME(실행 전 감사 기록 (4), 미수정) |
| K-109 | D-h 실행별 상태 | `per_run.<run>` = K-SAME / K-DIFF / K-NA(20실행) | `same`, `diff`, `na`(d1 키 목록) | 실행별로 d1 키(하네스 줄 `d1_key`)를 거쳐 상태 완전 일치, 세 목록 크기 합 20 |
| U-12 | D-a Z_soil 후보(Z2)·Z_B1 바탕값, D-e g^corr 범위, D-d 하한 표시 정의(경로 1 SGS 행이 있으면, 경로 2 q*의 SGS 행 e ≥ 0일 때만) | `Z_soil_candidates`, `Z_B1_before_soil_m`, `per_row.*.g_corr_band_m`, `flags`의 `하한 포함` | 없음 / 다른 정의 | **대응 없음**(판정서 기록 항목) |

## 14. 대응 없음 목록 (결과 전에 처리를 정할 것)

| # | 항목 | 규칙 근거 | 한쪽 |
|---|---|---|---|
| U-01 | M-1 t_dep | 5 M-1 | 경로 1만 |
| U-02 | M-4h | 5 M-4h(기록) | 경로 1만 |
| U-03 | M-6 b*·b 밖 두 다리 | 5 M-6(e_i) | 경로 1만 |
| U-04 | P-G 보조 값 | 7.2 | 경로 1만 |
| U-05 | M-7 전부(ĉ(t_L) 빼고) | 5 M-7 | 경로 1만 |
| U-06 | M-8 나머지 | 5 M-8 | 경로 1만 |
| U-07 | M-9 | 5 M-9(기록) | 경로 1만 |
| U-08 | M-10 s_L·s_R·δ^os·g | 5 M-10 | 경로 1만 |
| U-09 | M-11 일부 | 5 M-11, C-5 (다) | 경로 1만 |
| U-10 | 하네스 실행별 M-1~M-11 값(Z_hn·하네스 δ^os·s_max의 원값, 하네스 m_L) | 5절 "M-1~M-12"가 하네스 실행을 포함하는지 문장에 없음 | 경로 1만(`P1.harness.<run>`). 경로 2는 M10 일부·R1-4·M-12 locs·등급 집계만 출력 |
| U-11 | D-f 짝 이름 목록 | 3.2 "계산에 쓴 행 ID 목록" | 경로 1만 |
| U-12 | 13절 마지막 줄 | 3.3·3.3.1·7.4 | 경로 1만 또는 정의 다름 |

- 모두 등급 계산에 쓰이지 않는 기록 항목이거나(U-01~U-09, U-12), 등급 계산에는 쓰이지만 그 결과가 K-90~K-109로 대조되는 중간값(U-10)이다.
- 9절 문자대로면 이 항목들도 K-R 대상이다. 사용자 결정 2026-11-12의 세 항목처럼 "한 경로 기록, K-R 제외, 판정서 공개"로 할지, 결과 전에 경로 2 출력에 더할지를 Chrono 결과 전에 정한다.

## 15. 집계

- 대조 항목 K-01~K-109: 109개(행·다리·모서리·τ별로 펼치기 전 개수). 이 가운데 유도 대응(한쪽 값을 정해진 식으로 바꿔 대조) K-50·K-51·K-52·K-61·K-66·K-83, 규약 변환 K-02·K-36·K-68·K-69·K-81.
- 제외 X-01~X-04: 4개(사용자 결정 2026-11-12의 세 항목 = X-01, X-02, X-03, 그리고 X-03에 따른 T-13 X-04).
- 대응 없음 U-01~U-12: 12개(14절).
