# B1 크리프 근거 규칙 rev2 초안 — 새 예측 형식 재등록 (`V5-B1-PRED`)

- 작성: control-expert, 2026-11-13. **상태: 봉인 전 초안.** 맨 앞 "확인 필요 질문"의 사용자 결정을 받은 뒤 고쳐 봉인한다(`.sha256` 없음 = 실행·판정에 쓰지 않음).
- 원판: `06_analysis/02_control/b1/b1_creep_rules.md`(sha256 `6b99702ce26d6da28fbfe6473b622c7e51419241916cbc101f795828f498774e`, 봉인 `b1_creep_rules.sha256`). rev1: `b1_creep_rules_rev1.md`(sha256 `9f72af5babc36a9164a79163a0c3fa8707a0b8dc71aa3bfe978ebdf33d0905cf`, 봉인 `b1_creep_rules_rev1.sha256`). 둘 다 고치지 않는다. 이 판이 봉인되면 아래 3절 문장이 원판·rev1의 해당 문장보다 우선하고, 새 묶음 `V5-B1-PRED`에만 적용한다. 3절에 없는 문장은 원판·rev1 그대로다.
- **시점: B1 Chrono 6행 결과를 본 뒤의 개정이다.** 판정서 `b1_creep_basis_judgement.md`(sha256 `d59be349eea04668ebf056e556f81380b0aeb8b1372f02f49233843d10adc639`, 작업 사본)가 D-d `PRED-FAIL`을 냈고, 원판 3.3 D-d 효과 칸("B1 설계 전에 새 예측 형식을 재등록한다")과 rev1 U-R1-4 (a)에 따라 이 개정을 쓴다. 사용자 결정 2026-11-13 "재등록 착수"(판정서 부록).
- **검증은 이번 6행과 다른 새 Chrono 행(다른 경사·오거 단계)으로만 한다.** 이번 6행(`batch_V5-B1-CREEP_20261112_125134`)과 하네스 32실행(`b1_H.jsonl`)은 이 개정에서 형식을 고르고 상수를 맞추는 **적합 자료**다. 적합 자료로 낸 오차는 등급에 쓰지 않는다(판정서 1.4 제안 2).
- 이 판의 "B1"은 원판 1.4 이름 겹침 문장 그대로다.

## 확인 필요 질문 (봉인 전 사용자 결정)

| # | 질문 | 선택지 | 권고 |
|---|---|---|---|
| U-R2-1 | 예측 대상 $s_{\max}$의 범위 | (a) **가드 감시 주기**(LEVEL, 첫 LOC 이후, SGS 주기 포함)의 판독 최대 $s^G_{\max}$. 탐침·FAULT 뒤 값은 기록만(R2-1) / (b) 원판 그대로 실행 전체 최대, 탐침 깊이 $d$ = 2 mm를 예측자에 더함 / (c) 원판 그대로 | **(a)**. 가드는 LEVEL에서만 본다(`b1_c3_probe_guard_check.md`). B1은 그 가드에 닿지 않게 $m$을 줄이는 규칙이다. 탐침은 따로 P6 가드(689.8 mm)가 있다 |
| U-R2-2 | SGS 행을 D-d에서 세는 법(빈 곳 나) | (a) **한쪽 판정**: $\hat s \ge s_g$이면 오차 0, 아니면 $e^\ast = s_g - \hat s$(R2-2) / (b) SGS 행을 D-d에서 빼고 행 수만 적음 / (c) 원판 7.4 그대로 | **(a)**. SGS 행이 말하는 사실은 "필요 행정 ≥ $s_g$"뿐이다. (b)는 정보를 버리고, (c)는 정지 값과 예측의 차를 오차로 센다 |
| U-R2-3 | 새 후보 집합(빈 곳 가·다) | (a) **{P-A, P-T, P-DL, P-R}**, 상수는 적합 자료로 고정(R2-3) / (b) {P-A, P-T}만 / (c) 위임 질문(6절) 답을 받은 뒤 정함 | **(a)**, 단 P-DL의 꼴은 6절 T-1·T-2 답이 "기구가 다르다"면 봉인 전에 빼거나 고친다 |
| U-R2-4 | 문턱 | (a) **원판 10 mm·$\varepsilon_{th}$ 그대로**(대칭 $\lvert e\rvert$) / (b) 비대칭(예측 부족 ≤ 5 mm, 과대 ≤ 15 mm) | **(a)**. 결과를 본 뒤 문턱을 바꾸면 결과 의존이 하나 더 생긴다. B1의 안전 쪽(예측 부족) 비중은 B1 설계 문서에서 다룬다 |
| U-R2-5 | 검증 행 | (a) **J2 패드 B ×1.0 6행 + ×1.1 1행**(4절 V1~V7) / (b) (a) + J1 패드 B 1행(V8) / (c) (a)에서 ×1.1 행을 뺌(D-g′ 없음) | **(a)**. B1 근거 범위가 J2이고(원판 14.1), ×1.1은 원판 D-g의 질문을 이어받는다 |
| U-R2-6 | 적합 자료로 낸 오차의 공개 | (a) **판정서에 기록으로 적되 등급에 쓰지 않음** / (b) 적지 않음 | **(a)** |

## 0. 이 개정 전에 본 것 (공개)

| 자료 | 본 범위 | 쓴 곳 |
|---|---|---|
| 판정서 `b1_creep_basis_judgement.md` | 전체(등급·행 요약·D-d 표·부록 결정) | 전체 |
| 경로 1·2 출력 `b1_metrics_path1.json`(`6ad863ab…`), `b1_metrics_path2.json`(`5c3185c4…`) | 경로 1 `rows.<C>.metrics`(M-1·M-2·M-4·M-6·`p_a_limit`·`predictor_inputs`·R1-4) | 1절 분해 |
| Chrono 6행 `07_results/S9/batch_V5-B1-CREEP_20261112_125134/<case>/` | `record/record.npz`(`meas.stroke`, `meas.stroke_corrected`, `s_ref`), `r8_series.npz`(`phase`, `issued_u`, `probed_leg`), `step_series.npz`(`pad_sinkage_geometric_m`, `scm_pad_normal_N`), `record/b1_grid_record.npz`(`load_read_N`), `result.json`(`phases`, `events`, `controller_meta`) | 1절 |
| 하네스 `06_analysis/03_hydraulic/coupled/v5/b1/b1_H.jsonl`(`a7099db6…`)과 npz | `stroke_read_m`, `phase`(28실행, H-SH0 제외) | 1.2 |
| 코드(읽기만) | `c2.py` 8199~8263·8300~8317·7429~7443·6001~6009·9617~9650, `ground_contact.py` 826~862, `chrono/l2b_engine.py` 10~27·198~215 | 1.1, R2-1 |

- 확인 계산 스크립트(scratchpad `ctrl-b1c3/`, dynamics-dev `-I -B`, 판정 값 아님): `phase_max.py`, `decompose_pa.py`, `post_loc_load.py`, `fault_rise.py`, `harness_phase_max.py`. 아래 수치는 이 계산과 판정서 값이다.
- 보지 않은 것: LAS-b P5r4+K1 결과(원판 0.2.2 그대로), 경로 1·2 도구 코드.

## 1. 결과에서 본 빈 곳 (판정서 1.4 제안 1)

### 1.1 (가) READY 행 예측 부족 +6~+14 mm의 몫

P-A 오차는 운동학 항등식(원판 7.2, $s_i(t) - s_i(t_L) = \Delta s^{geo}_i + h_i + \Delta z_i$)으로 나눌 수 있다.

$$e_b(\text{P-A}) = \underbrace{\Delta z_b(t_L\!\to\!t_{\max})}_{\text{①}} + \underbrace{h_b(t_{\max}) - \bar h(t_{\max})}_{\text{②}} + \underbrace{\bar h(t_{\max}) - (c^\ast + m_L - \hat c(t_L))^+}_{\text{③}}$$

| 기호 | 정의 | 단위 |
|---|---|---|
| $h_i$ | 다리 $i$의 관측 heave $s_i - s_i(t_L) - \Delta s^{geo}_i - \Delta z_i$(원판 7.2) | mm |
| $\bar h$ | 네 다리 평균 $h$ | mm |
| ① | 예산 다리 자신의 LOC → $t_{\max}$ 침하(P-A에 없음) | mm |
| ② | 예산 다리 차등(탐침 상승, 비틀림·자세 잔차) | mm |
| ③ | 평균 heave가 P-A heave 항을 넘은 양(크롤러 모서리 항 + 틈 루프 과도) | mm |

| 행 | $e$(P-A) | ① | ② (그중 탐침 상승) | ③ (모서리 항 / 과도) | $t_{\max}$ 단계 |
|---|---|---|---|---|---|
| C1 | +6.100 | 3.514 | 2.643 (1.580) | −0.057 (−2.435 / +2.378) | probe |
| C2 | +10.450 | 6.448 | 2.819 (0.797) | +1.183 (−1.080 / +2.262) | probe |
| C3 | +13.661 | 3.767 | 3.235 (1.634) | +6.659 (+3.765 / +2.894) | probe |

- 합은 세 행 모두 $e$와 0.001 mm 안에서 같다(검산).
- 모서리 항 = $-\rho_{k^\ast} - Z_{k^\ast}(t_{\max}) + \hat c(t_L) - \hat c_{k^\ast}(t_L)$, 과도 = $\bar h(t_{\max}) - [c^\ast + m_L - (\hat c_{k^\ast} + \rho_{k^\ast} + Z_{k^\ast}(t_{\max}))]$. $\rho_{k^\ast}$는 −2.06 / −8.59 / −17.82 mm로 $\lvert\Delta s^{geo}_b\rvert$(1.76 / 10.38 / 21.87 mm)와 같이 커진다.
- 탐침 상승은 가드가 보지 않는 값이다(`b1_c3_probe_guard_check.md`). LEVEL 최대로 바꾸면 $e$는 +4.520 / +9.653 / +12.027 mm다(R2-1).
- **P-A가 담지 않는 몫**: ① 예산 다리 자신의 LOC 뒤 침하 3.5~6.4 mm, ③ 틈 루프 과도 2.3~2.9 mm, 자세에 따라 커지는 모서리·차등 몫(C3에서 약 5 mm). rev1 R1-1의 $\hat W$는 이 다리들에서 음이라 P-B·P-D가 ①을 담지 못했다.
- $\delta^{os}$(19.9~23.2 mm)가 큰 이유: $t_{\max}$(LOC 뒤 15~29 s) 뒤에 뒤 패드 침하가 크게 늘어(C3 RL $\Delta z$ 17.2 → 47.8 mm) 행정 기반 틈 추정이 커지고, 틈 루프가 다리를 내린다(C3 $\bar h$ 81.4 → 55.7 mm). 최대 행정은 침하가 다 끝나기 전에 나온다.

### 1.2 (나) SGS 행 하한

- 원판 7.4는 SGS 행 $s_{\max}$를 하한으로 읽고, $e < 0$(예측 > 기록)을 그대로 $E_q$에 넣었다. 그래서 C4 −27.390 mm가 $E_q$를 정했다.
- 기록된 SGS 행 $s_{\max}$는 SGS 주기 뒤 FAULT 단계 값이다. C4 FR: SGS 주기 $n$ 505 판독 679.791 mm, 출력 0 뒤 밸브 τ 0.1 s·$d$ = 1 관성으로 `s_ref`가 680.798 mm에서 멈추고, 판독 최대 681.197 mm는 그 위 잡음(σ 0.1 mm)이다. LEVEL 최대와의 차: C4 +1.942, C5 +1.803, C6 +1.924 mm. 하네스(잡음 없음)는 +0.24~+0.53 mm다.
- SGS 행이 말하는 것은 "그 실행의 필요 행정 ≥ $s_g$"다. P-A 예측은 C4 708.587, C6 704.812 mm로 $s_g$ 682.8 mm 이상이었다. 한쪽 판정이면 두 행 모두 "일치"다.

### 1.3 (다) 하중 재분배로 설명되지 않는 예산 다리 침하

- rev1 7절의 알려진 한계가 Chrono에서도 나왔다: 예산 다리 $\hat W$ C1 FL −1,005, C3 FL −1,555, C5 RL −841 N(C2 FL +228 N)인데 LOC 뒤 침하는 9.9~13.3 mm다.
- 확인 계산: READY 행 예산 다리의 SCM 패드 법선력(`scm_pad_normal_N`)이 LOC 뒤에 LOC 전 최대를 넘었다.

| 행 | LOC 전 최대 [kN] | LOC 뒤 최대 [kN] (단계, 시각) | 초과 | $\Delta z$ 단계별 [mm] level / probe / reanchor |
|---|---|---|---|---|
| C1 FL | 119.766 | 122.605 (probe, 114.2 s) | +2.4 % | 3.315 / 2.310 / 6.277 |
| C2 FL | 119.315 | 122.527 (probe, 133.8 s) | +2.7 % | 6.826 / 3.528 / 2.988 |
| C3 FL | 120.365 | 122.810 (probe, 112.8 s) | +2.0 % | 3.591 / 3.014 / 3.258 |

- J2 세트 $n$ = 0.2이면 Bekker 정적 침하는 $\Delta z / z \approx (1/n)\,\Delta F/F$ = 5 × 2~2.7 % = 10~13 %이고, $z(t_L)$ ≈ 88~91 mm에서 9~12 mm다. 기록된 $\Delta z^{post}$ 9.9~13.3 mm와 같은 자릿수다. 즉 침하는 "LOC 뒤 하중 재분배"가 아니라 **"LOC 뒤 동작(LEVEL 자세 보정, 탐침 밀기, REANCHOR 하중 이동)이 지나간 최대를 넘긴 하중"**으로 설명될 가능성이 크다. 이 해석은 control-expert 확인 계산이고, 기구 확인은 6절 위임 질문이다.
- 예측 대상이 $s^G_{\max}$(첫 LEVEL 안)이면 ①은 그 앞 LEVEL 몫(3.3~6.8 mm 가운데 $t^G_{\max}$ 앞 부분)만 들어간다. 탐침·REANCHOR 몫은 D-a(LOC 뒤 침하 전부)에 들어간다.

## 2. 범위

- **B1 방향 = fdown·diag.** J2 fup(앞들림)은 사용자 결정 2026-11-13(Q6, 판정서 부록)으로 **B1 범위에서 빼고 운용 권고(시작 조건 축소 등)로 분리했다.** 이 판은 fup 행을 돌리지 않고 D-f를 계산하지 않는다. 운용 권고값 분석은 이 규칙 밖이다.
- 원판 등급 D-a(`ZA-2`), D-b(`OS-MAX`), D-c(`H-OPT`), D-e(`B1-OPEN`), D-f(`FUP-OUT`), D-h(`K-SAME`)는 판정서 값 그대로 둔다. 이 판은 그것들을 다시 내지 않는다. 새 묶음에서 같은 지표는 **기록**으로만 낸다(D-c′는 4.2).
- 이 판이 내는 등급: D-d′(새 예측 형식), D-g′(×1.1 감도). 그리고 D-c 효과 칸의 "fdown은 B1 채택 전에 Chrono 확인 행"을 새 fdown 행이 겸한다(기록, 4.2).
- 모형 범위는 원판 14.1 그대로다(SCM 명목 세트 안의 결론, 실토양 결론 아님).

## 3. 바꾸는 문장

### R2-1 예측 대상 $s^G_{\max}$ (원판 M-2 $s_{\max}$·M-6 $e$·4.5 $t_{\max}$의 D-d′·D-g′ 쓰임을 대체, U-R2-1 (a))

$$\mathcal G = \{n : n \ge n_{L1},\ \text{phase}(n) = \texttt{level}\} \cup \{n_{sgs}\},\qquad s^G_{i,\max} = \max_{n\in\mathcal G} s_i(n),\qquad b^G = \arg\max_i s^G_{i,\max}$$

| 기호 | 정의 | 단위 |
|---|---|---|
| $\mathcal G$ | 가드 감시 주기 집합(행정 예산 가드가 판정할 수 있는 주기, `c2.py` 8209·8211) | — |
| phase($n$) | Chrono `r8_series.npz` `phase`, 하네스 npz `phase`의 주기 $n$ 문자열(정수 주기 $n$ = round($t$/0.1)로 맞춤) | — |
| $n_{L1}$ | 첫 LOC 주기(원판 5절 $t_{L1}$) | — |
| $n_{sgs}$ | SGS 첫 주기(사건 `FAULT_LIFT_STROKE_LIMIT:soil` 시각). SGS 없으면 빈 집합 | — |
| $s_i(n)$ | 판독 행정(원판 머리 규약) | m |
| $b^G$ | 가드 감시 주기의 실제 예산 다리(같으면 원판 순서 FL, FR, RL, RR 앞) | — |
| $t^G_{\max}$ | $s^G_{b^G,\max}$가 처음 나온 주기(4.5 꼴) | — |

- D-d′·D-g′의 오차는 $e^G_i(q) = s^G_{i,\max} - \hat s^{(q)}_{i,\max}$이고 $b^G$ 값을 쓴다.
- 기록(등급에 안 씀): 탐침 최대 $s^P_{\max}$(phase = `probe`), 그 탐침 시작 판독과의 차, P6 한계 $s_{soft}$ − 5 mm까지 남은 거리. SGS 행의 SGS 뒤 최대와 $s^G_{\max}$의 차. 원판 $s_{\max}$·$g$도 그대로 낸다.
- $\mathcal G$가 빈 행(LOC 뒤 LEVEL 주기가 없음)은 D-d′에서 `NA`다.

### R2-2 SGS 행 한쪽 판정 (원판 7.4를 D-d′·D-g′에서 대체, U-R2-2 (a))

SGS 행 $r$(가드 첫 주기 정지)의 후보 $q$ 오차는

$$e^\ast(r, q) = \max\big(0,\ s_g - \hat s^{(q)}_{b^G,\max}\big),\qquad s_g = 0.6828\ \text{m}$$

- $\hat s \ge s_g$이면 "가드에 닿을 것을 맞혔다"로 0이다. $\hat s < s_g$이면 적어도 $s_g - \hat s$만큼 모자랐으므로 그 값을 + 오차로 센다.
- READY 행은 $e^G$ 그대로(대칭)다. $E'_q = \max_{r \in \mathcal V}\lvert e(r, q)\rvert$, $e$는 READY 행 $e^G$, SGS 행 $e^\ast$다.
- SGS도 READY도 없이 끝난 행(FAULT·시간 끝)은 D-d′에서 빼고 행 ID를 적는다.
- 판정서에는 SGS 행 수, READY 행 수, $E'_q$를 정한 행이 어느 쪽인지 적는다.

### R2-3 후보 집합 (원판 3.3 D-d 후보·동점 순서, 7.2 후보 표를 D-d′에서 대체, U-R2-3 (a))

모든 후보는 LOC 주기($n_L$) 정보와 4.3 상수만 쓴다. 원판 P-A의 $\Delta s^{geo}_i$, $(c^\ast + m_L - \hat c(t_L))^+$, $m_L$, 7.1 자세 입력은 그대로다.

| 후보 | $\hat s^{(q)}_{i,\max}$ | 담는 몫(1절) |
|---|---|---|
| P-A | 원판 그대로 | 기준 |
| P-T | P-A + $O_T$ | ①②③을 상수 하나로 |
| P-DL | P-A + $\Delta\hat z^{dyn}_i$ | ① LOC 뒤 동하중 침하(1.3) |
| P-R | P-A + $\lambda\,\lvert\Delta s^{geo}_i\rvert + O_R$ | ②③의 자세 비례 몫 + 상수 |

$$\Delta\hat z^{dyn}_i = z_{J2}\big(F^{pad}_{L,i}\big)\left[(1+\rho_{dyn})^{1/n} - 1\right],\qquad z_{J2}(F) = \left(\frac{F}{A_i\,(k_c/b_{poly,i} + k_\varphi)}\right)^{1/n},\qquad F^{pad}_{L,i} = F^{pk}_{L,i} - F^{nom}_{s,i}$$

| 기호 | 정의 | 단위 |
|---|---|---|
| $O_T$ | 상수 여유(4.3) | m |
| $\rho_{dyn}$ | LOC 뒤 패드 하중이 지나간 최대를 넘는 비(4.3) | — |
| $z_{J2}(F)$ | J2 세트 연속 Bekker 정적 침하(원판 0.4 식에서 $f$ = 1). $k_c, k_\varphi, n$ = `02_params/scm_soil_sets.json` J2(16,430, 1,724,690, 0.2), $A_i$, $b_{poly,i}$ = YAML `pad_shapes` 패드 B(원판 0.4 표) | m |
| $F^{pk}_{L,i}$ | 원판 7.2 정의 그대로(판독 하중 `load_read_N`의 $n \le n_L$ 최대) | N |
| $F^{nom}_{s,i}$ | YAML `actuator.seal_friction` 공칭(전방 4 kN, 후방 × 0.8333). 판독 하중이 신장 중 마찰을 더한 값이라 뺀다(rev1 F-1) | N |
| $\lambda$, $O_R$ | 자세 비례 계수와 상수(4.3) | —, m |

- 동점 순서: P-A → P-T → P-DL → P-R(상수가 적은 쪽 먼저).
- `PRED-q′`: $E'_q$ 최소인 $q$ / `PRED-FAIL′`: 최소 $E'_q$ > 10 mm(T-4 꼴 그대로).
- 원판 P-B·P-D·P-G·P-C는 D-d′ 후보가 아니다. 새 묶음에서 기록으로만 낸다(rev1 상수 그대로).
- P-DL은 J2 세트 $n$·$k$를 예측자에 넣는다. 실기 제어기는 이 값을 모르므로 B1 설계 문서의 가정으로 남는다(원판 C-2 $n_a$와 같은 처리).

### R2-4 K-77 문장 (원판 7.3 κ 비 문장과 rev1 R1-3 κ 비·감도 문장에 덧붙임)

- **적합 다리 0개로 κ 비가 `NA`이면 "κ 비선형" 표시도 `NA`로 적는다(참·거짓으로 적지 않는다).** rev1 R1-3 감도($W_{fit}$ 600·2,000 N)에도 같다. 근거: 판정서 4.3 K-77(경로 1 null, 경로 2 false로 갈린 정의 해석 차이), 사용자 결정 2026-11-12.

### R2-5 문턱 표 추가 (원판 4.4 표에 세 줄)

| # | 문턱 | 통과(앞) 쪽 꼴 |
|---|---|---|
| T-16 | R2-2 한쪽 판정 | $\hat s - s_g \ge -\varepsilon_{th}$이면 $e^\ast$ = 0 |
| T-17 | R2-1 단계 선택 | phase 문자열이 정확히 `level`(대소문자 그대로). $n \ge n_{L1}$은 정수 비교 |
| T-18 | 4.3 상수 적합 비교 | $\lvert$적합 후보 값 − 최대$\rvert \le 10^{-12}$ m(또는 무차원)이면 같은 최대로 보고 작은 행 ID를 기록 |

## 4. 새 묶음 `V5-B1-PRED`

### 4.1 검증 행 후보 (Chrono, `run_S9.py level`, 제안)

공통 조건은 원판 2.1 그대로다(J2 균일, `--pad-variant dwg_rear250`, `--fs-kN 4`, VB 옵션 `v5_vb_argv()` + `--expect-controller final_C4G2_P3_LAS_K1`, 압력 `normal`, IMU `ideal`, `--grid 0.01 --crawler-grid 0.04`, `--settle-dashpot zrp`, `--threads 4`, `--start-limit record_only`, `--b1-grid-record full`, 시드 P3b 기본).

| ID | 사례 이름(제안) | 오거 | roll / pitch [°] | $R_c$ | 질량 | `--duration` [s] | 예상 예산 다리 | 이번 6행과 다른 점 |
|---|---|---|---|---|---|---|---|---|
| V1 | `B1P_J2_B_bottom_Fs4_VB_fdown2p4` | bottom | 0 / 2.4 | 0.75 | 1.0 | 160 | FL | 경사 |
| V2 | `B1P_J2_B_top_Fs4_VB_fdown2p4` | top | 0 / 2.4 | 0.75 | 1.0 | 160 | FL | 경사 |
| V3 | `B1P_J2_B_middle_Fs4_VB_fdown2p0` | middle | 0 / 2.0 | 0.625 | 1.0 | 160 | FL | 경사 |
| V4 | `B1P_J2_B_middle_Fs4_VB_diag0p75` | middle | 1.65 / 1.2 | 0.75 | 1.0 | 160 | FR | 경사·오거 |
| V5 | `B1P_J2_B_top_Fs4_VB_diagL0p75` | top | −1.65 / 1.2 | 0.75 | 1.0 | 160 | FL | 경사·오거·대각 방향(거울) |
| V6 | `B1P_J2_B_top_Fs4_VB_diag` | top | 1.925 / 1.4 | 0.875 | 1.0 | 160 | FR | 오거(C4와 같은 경사) |
| V7 | `B1P_J2_B_middle_Fs4_m1p1_VB_fdown2p4` | middle | 0 / 2.4 | 0.75 | `--mass-scale 1.1` | 180 | FL | ×1.1 감도(D-g′) |
| V8(선택, U-R2-5 (b)) | `B1P_J1_B_middle_Fs4_VB_fdown2p4` | middle | 0 / 2.4 | 0.75 | 1.0 | 160 | FL | 토양 J1(일반화 확인) |

- $R_c = \lvert\phi\rvert/4.4° + \lvert\theta\rvert/3.2°$(CLAUDE.md 레벨링 시작 조건). 이번 6행은 모두 $R_c$ 0.875(J1 B 운용 권고 경계)였다. 새 행은 0.625~0.875로, READY 행이 늘어 대칭 오차 행이 많아지기를 기대한다(예상, 확인 안 됨).
- 패드 A(`cad330`) 행은 넣지 않는다. B1 근거가 패드 B 기본이고, 패드 A는 후방 면적이 커서 다른 질문이 된다(필요하면 다음 개정).
- 행 수·비용(가정, 이번 묶음 실측 기반): ×1.0 행 벽시계 6,600~8,900 s(4스레드, P코어, 동시 2~4행). V1~V7 7행은 4행 + 3행 두 물결로 약 4.5~5 h(P코어). V8을 넣으면 같은 두 물결 안에 들어간다. 배치는 compute-scheduler-expert, 실행은 메인 세션(30분 넘음 → long-running-task-monitor).
- 하네스 짝(E코어): V1~V8 키 × {VB, V0} × e0(16실행, 수 분/실행 수준). 새 경사·대각 키가 `run_v5.py d1`에 없으면 키 추가가 필요하다(위임 필요, python-expert).
- 행 유효성·묶음 상태·정체성·재실행·G-S는 원판 3.1·3.2·4.1~4.3·2.3을 묶음 이름과 행 ID만 바꿔 쓴다. 핵심 행 = V1~V6(×1.0). `COMPLETE` = V1~V7(V8 있으면 포함) 모두 `VALID`. `PARTIAL` = V1~V6 가운데 `VALID` ≥ 5. 그 밖 `UNDETERMINED`.
- G-S는 argv 꼴이 이번 묶음과 다를 때만 한다(V8 토양 J1 꼴 1개). 같은 `HEAD_M`이면 V1~V7 꼴은 이번 G-S(`batch_V5-B1-CREEP-GS_20261112_112555`)와 `--floor-*`·`--level`·`--mass-scale` 값만 다르다(확인 필요: 실행 전 감사).

### 4.2 등급과 기록

| 코드 | 양 | 등급 규칙 | 행 집합 |
|---|---|---|---|
| **D-d′ 예측자** | $E'_q$(R2-2) | `PRED-q′` / `PRED-FAIL′`(R2-3) | $\mathcal V$ = V1~V6(+V8) 가운데 `VALID`이고 T-14 일치인 행 |
| **D-g′ ×1.1 감도** | $e(\text{V7}, q^\ast)$, $E'_{q^\ast}$ | `W-OK′`: $\lvert e(\text{V7})\rvert \le E'_{q^\ast}$ + 5 mm / `W-EXT′` / `W-NA′`(V7가 VALID가 아니거나 `PRED-FAIL′`) | V7 |
| 기록 D-c′ | 원판 D-c 식 그대로(새 행 대 하네스 VB e0) | 등급 없음. fdown 행(V1~V3)의 $\Delta^{corr}$는 원판 D-c 효과 칸 "fdown Chrono 확인 행"의 값으로 B1 설계 문서에 넘긴다 | V1~V6 |
| 기록 D-a′·D-b′·D-e′ | 원판 식 그대로 | 등급 없음 | V1~V6 |

- 원판 3.3 D-d 효과 칸 그대로: `PRED-q′`면 B1은 그 형식을 쓴다. `PRED-FAIL′`이면 B1 설계 전에 다시 재등록하거나, B1을 닫고 운용 권고로 돌릴지 사용자에게 묻는다.
- 적합 자료(C1~C6, 하네스 32)로 낸 $E'_q$는 판정서에 기록으로만 적는다(U-R2-6 (a)).

### 4.3 상수 (적합 자료에서만, 새 Chrono 행 전에 고정)

| 상수 | 적합 행·다리 | 규칙 |
|---|---|---|
| $O_T$ | C1~C3(READY)의 $b^G$ | $\max_r e^G(r, \text{P-A})$. 그리고 SGS 행 C4·C6에서 $e^\ast(\text{P-T})$ = 0인지 확인(아니면 그 행 값까지 키움) |
| $\rho_{dyn}$ | C1~C4·C6의 $b^G$ | $\max_r \big[F^{pad,true}_{b^G}(\text{peak},\ n_L < n \le n^G_{\max}) / F^{pad,true}_{b^G}(\text{peak},\ n \le n_L) - 1\big]^+$, $F^{pad,true}$ = `step_series.npz` `scm_pad_normal_N`(1 ms 전체 표본). 적합에만 참 하중을 쓰고 예측자는 판독 하중만 쓴다 |
| $\lambda$ | C1~C3의 $b^G$ | $e^G(r, \text{P-A})$를 $\lvert\Delta s^{geo}_{b^G}(r)\rvert$에 맞춘 1차 최소제곱(절편 포함)의 기울기. 기울기 < 0이면 $\lambda$ = 0 |
| $O_R$ | C1~C3의 $b^G$ | $\max_r\big[e^G(r, \text{P-A}) - \lambda\lvert\Delta s^{geo}_{b^G}(r)\rvert\big]$(위 포락) |

- C5(fup)는 범위 밖이라 적합에도 쓰지 않는다(2절). 하네스는 Chrono보다 낙관적이라(`H-OPT`) 새 상수 적합에 쓰지 않는다. 하네스 32실행은 기록(새 후보를 하네스에 대입한 오차)만 낸다.
- 두 경로가 이 문장만으로 상수를 계산하고(원판 9절·rev1 4절 절차), 상대차 ≤ 1×10⁻⁹·적합 행 목록 일치를 확인한 뒤 상수 파일 sha를 실행 전 감사와 prelaunch에 적는다. 그 다음에만 새 Chrono를 시작한다.
- 상수 값은 이 문서에 적지 않는다(rev1 0절과 같은 이유). 다만 1.1에서 공개한 값으로 $O_T$의 크기는 약 12 mm(C3)임을 이미 알 수 있다(공개).
- 적합 자료가 3행(READY)이라 P-R은 과적합 위험이 크다. 이 위험은 검증 행으로만 잰다.

## 5. 바꾸지 않는 것

- 문턱 3 / 5 / 10 / 20 / +5 mm, $\varepsilon_{th}$ = 1×10⁻⁹ m, T-1~T-15.
- 원판·rev1 등급 값(판정서), 원판 D-a~D-h의 정의(새 묶음 기록에 그대로 씀).
- 판독 행정 정의, 정수 주기, 1 ms 조회 꼴(원판 4.5).
- P-A 식, $m_L$, T-14, 7.1 자세 입력, rev1 R1-1 $\hat W$(기록 후보 P-B·P-D·P-G에서).
- 대상 제어기 `final_C4G2_P3_LAS_K1` / `final_C4G2_LAS_K1`, 프리셋 그대로(원판 1.1·1.2·1.4). 실행 전 프리셋 덤프 대조 I-17은 그대로 한다.
- 원판 14.1 모형 범위, 알려진 한계.

## 6. 위임 필요 (봉인 전 답을 받으면 R2-3 P-DL 꼴을 확정)

### 6.1 dynamics-expert

| # | 질문 | 입력 |
|---|---|---|
| D-1 | C1~C3 예산 다리 FL의 패드 법선력이 LOC 뒤 LOC 전 최대를 +2.0~2.7 % 넘었다(1.3 표). 단계별(LEVEL 자세 보정, 탐침 밀기 $S_{ii} d$, REANCHOR 뒤 다리 하중 이동, 들어 올림 감속 관성 $m\,a$, 실 마찰 부호 변화) 하중 수지를 기록으로 나눠 달라. 특히 $t^G_{\max}$ 앞 첫 LEVEL에서 넘은 몫 | Chrono 6행 `step_series.npz` `scm_pad_normal_N`·`F_cyl_N`, `r8_series.npz` `phase`, `b1_grid_record.npz` `load_read_N` |
| D-2 | rev1 R1-1 $\hat W$(LOC 주기 재분배)가 예산 다리에서 음인데 LEVEL 중 그 다리 하중이 오르는 이유가 4점 지지 하중 분배(자세 0으로 갈 때 분배 변화, 비틀림 루프 $D$)로 설명되는가. 설명되면 LOC 주기 정보로 쓸 수 있는 꼴(예: 자세 보정량에 비례하는 하중 증가)을 제안해 달라 | 같음 + YAML `static_leg_loads_N` |
| D-3 | 판독 행정(L2b `s_ref`, 기름 부피 좌표)이 피스톤보다 $F/k_h$ ≈ 6.6 mm 크다(`b1_c3_probe_guard_check.md` 2.4). 실기 내장 행정 센서는 피스톤을 읽는다(CLAUDE.md 모델 규약). 가드·FAULT 문턱을 판독 좌표로 두는 지금 규약이 실기에서 보수 쪽인지 확인해 달라(유압 쪽은 hydraulics-expert와 함께) | `chrono/l2b_engine.py` 10~27행, `record.npz` `s_ref`·`meas.stroke_corrected` |

### 6.2 terramechanics-expert

| # | 질문 | 입력 |
|---|---|---|
| T-1 | J2 SCM에서 예산 패드 하중이 지나간 최대를 2~2.7 % 넘을 때 $\Delta z/z \approx (1/n)\Delta F/F$로 9~12 mm가 나오는 것이 SCM 소성 가지·점성 지연 $\tau = R/(n\,p/z)$ ≈ 0.4~0.5 s로 설명되는가. 다른 기구(접촉 절점 변화, 패드 기울기, M-4h 수평 변위 ≤ 1.2 mm, 전단 유발 침하)의 몫이 있는가 | 1.3 표, 판정서 2.2·2.4($r_\sigma$ 기록 무효 행) |
| T-2 | P-DL에 J2 세트 연속 Bekker $z_{J2}(F)$(격자 인자 $f$ = 1)를 쓰는 것이 타당한가. 격자 위상 범위(전방 −2.8~+5.0 %)를 $\rho_{dyn}$ 적합·예측에 어떻게 붙일지 | 원판 0.4, `scm_soil_sets.json` |
| T-3 | 탐침 뒤 하중이 지나간 최대 아래로 돌아올 때(재하중) SCM이 추가 소성 침하를 만들지 않는지(탄성 `elastic_K`만) | Chrono 소스(chrono-rag MCP) |
| T-4 | 실토양에서는 시간 의존 크리프가 더해진다(원판 14.1). P-DL·$Z_{soil}$(TR-8) 감도를 B1 설계 문서에 어떻게 붙일지 | 원판 10.0 TR-8 |

### 6.3 python-expert (구현, 봉인 뒤)

- 경로 1·2 도구에 R2-1·R2-2·R2-3·R2-4·R2-5와 4.3 상수 계산을 넣는다(두 경로는 서로 보지 않음, 원판 9절).
- `run_v5.py d1`에 V1~V8 경사·대각 키를 더한다(하네스 짝).
- cad-expert: V1~V8 행 모듈·전개 argv(원판 2.1 꼴).

## 7. 알려진 한계

- 적합 자료가 READY 3행·SGS 2행이다. P-T·P-R 상수는 이 행들의 최대로 정해 검증 행에서 과대 예측(성능 손실)이 날 수 있다. 안전 손실은 SGS(안전 정지)다.
- P-DL의 $\rho_{dyn}$은 "LOC 뒤 동작이 만드는 하중 초과"를 상수 하나로 둔다. 자세 보정량·오거 단계에 따라 달라지면 검증 행에서 드러난다(D-1 답에 따라 꼴을 바꿀 수 있음).
- 한쪽 판정(R2-2)은 SGS 행에서 과대 예측을 세지 않는다. SGS가 많은 묶음에서는 $E'_q$가 READY 행 몇 개로 정해진다(행 수를 판정서에 적는 이유).
- $\mathcal G$는 "LEVEL"만 본다. LEVEL 밖에서 행정이 가드를 넘는 경우(탐침, REANCHOR)는 B1의 예측 대상이 아니고, P6·끝 절단이 맡는다(`b1_c3_probe_guard_check.md`).
- fup은 범위 밖이다(2절). 운용 권고는 따로 분석한다.

## 8. 봉인 때 바꿀 것

- 확인 필요 질문의 결정을 표 "결정" 칸에 적고, 선택에 따라 R2-1~R2-3·4절을 고친 뒤 머리 첫째 줄을 "상태: 봉인"으로 바꾼다. 봉인 파일 이름 `b1_creep_rules_rev2.md`, sha는 `b1_creep_rules_rev2.sha256`(메인 세션).
- 봉인 전 verif-protocol-auditor 감사(실행 전 시점)는 4.3 상수 고정 뒤, 새 Chrono 시작 전에 받는다.
