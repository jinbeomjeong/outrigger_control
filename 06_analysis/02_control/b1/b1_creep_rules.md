# B1 크리프 근거 — Chrono SCM 경사 J2 규칙 원판 봉인 후보 (`V5-B1-CREEP`)

- 작성: control-expert, 2026-11-11. 작성 기준 master `7a469f7`(작성 시점 HEAD. 실행 HEAD가 아니다).
- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `b1_creep_rules.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다. 봉인 후보 초안 `b1_creep_basis_rules_seal_candidate_draft.md`(sha256 `6724a8aed4f8b3a9a32a493d5f7ec226352090432eaa64d19bd90c57c24f13a6`)와 이 줄과 10.0절 "답 원문" 줄만 다르다. 봉인 파일 이름은 `b1_creep_rules.md`다(메인 세션, 2026-11-12).
- **시점: 결과 전.** B1 Chrono 6행·하네스 32실행(그림자 켬 28 + 끈 짝 4)·G-S 건조 실행은 0행 실행됐다. LAS-b P5r4+K1 결과는 보지 않았다(0.2.2).
- **이 파일 = 한 파일 원판(사용자 결정 U-1 (a), 2026-11-11).** 다음 둘을 합쳤다. 두 파일은 고치지 않고, 봉인 뒤에는 이 파일만 실행·판정에 쓴다.
  - 봉인 후보판 `b1_creep_basis_rules.md`(sha256 `7c782632aa9796a5109a5bce9035beff844bb4f290b7cd60c4f25ae5eb8c1524`, 커밋 `ba84f53`, 봉인된 적 없음)
  - 초안 v2 `b1_creep_basis_rules_v2_draft.md`(sha256 `bf88cc6516fdd84aea772d77ed987808dde618241e9cc3c3fdbe00bd5324913d`, 추적 안 됨)
- **이미 봉인된 전제(바꾸지 않음)**: 격자 시험 계획 `b1_gridconv_plan.md`(`0e909bf1186a4cc90e40353d25244ee4a76a04cdabe48235e7051f9a111e9b24`) + rev1 `b1_gridconv_plan_rev1.md`(`3f354eb7c122584c7e65e66bb2eeaf33e27cfa9b445521a9802bdf8962d1da9e`), 판정 `b1_gridconv_judgement.md`(`a483ac48582c3171654d3e9e6f213bb11c3436b64d3396bea75da50e8a89e56b`) `PASS`.
- 봉인 뒤 바꾸려면 개정판(rev1 …)을 만들고 결과를 보기 전인지 본 뒤인지를 첫머리에 적는다.
- 사용자 결정
  - 2026-11-10(초안 10절): Q1 (다) C1~C5 + ×1.1 C1 = 6행. Q2 (나) 정식 봉인 + 세 시점 감사. Q3 C1m0(Chrono $m$ = 0) 없음, 하네스 $m$ = 0 짝으로 대신. Q4 다섯·여섯째 행 풀은 스케줄러가 정함. Q6 J2 경사 운용 권고 여부는 D-e·D-f 결과를 보고 다시 묻는다.
  - 2026-11-10: Q5 (가) P5r4+K1 판정·채택 결정 뒤 실행 → **2026-11-11 사전 결정으로 대상 제어기가 P5r4 결과와 무관해졌다(1.2).** 실행 시점은 1.3.
  - 2026-11-10: 격자 개정 결정 1~4, D-c 대체 범위 분류, R-6(문턱 그대로).
  - 2026-11-11: U-1 (a) 한 파일 원판, U-2 (a) TR-1~TR-8 재검토(답 대기, 10.0), U-3 (b) D-a 보수 쪽(TR-1 답 뒤 확정), U-4 (a) M-12 기록만, U-5 (a) H-M0 `enable` 유지 + `margin_m` 0, U-6 (a) G-S 건조 실행 함, U-7 (a) 하네스 그림자 켬 + 끈 짝 4개.
  - 2026-11-11(사전): P5r4가 '통과'여도 지금 프리셋 전환 없이 v5 뒤 후보로 기록, v5 제어기 = `final_C4G2_LAS_K1`.
- 성격: **B1 설계 입력을 정하는 등급 판정**이다. 제어기 합격·불합격 판정이 아니다. P3 행·SGS 분류는 기록만 한다(관문에 쓰지 않는다).
- 규약
  - 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1, C2 음되먹임이다($u$ = 행정 속도 명령 [m/s]).
  - **판독 행정** $s_i$: 제어기가 보는 모터 행정이다. Chrono는 `record.npz` `meas.stroke`(10 Hz), 하네스는 `max(plant.sref)`와 같은 양(10 Hz 표본)이다. 가드 $s_{guard}$ = 0.6828 m이고, 이 규칙의 모든 행정 비교는 판독 행정끼리 한다. 참 행정(P3-5)은 기록만 하고 섞지 않는다.
  - 침하 $z_i$: 패드 기하 침하(Chrono `step_series.npz` `pad_sinkage_geometric_m`, 1 ms, + = 깊어짐)다. 하네스는 같은 정의의 패드 요소 침하이고, 3.2절에 따라 저장한다.
  - 시각은 절대 시각 [s]이고 비교는 정수 주기다(4.5). 길이는 표시할 때 mm, 도구는 m다.

## 0. 배경과 봉인 전에 본 것

### 0.1 목적

- B1은 LOC 주기 $k_L$에 다리별 최대 판독 행정을 예측해, E3c10 경사 틈 여유 $m$을 [0, 30] mm 안에서 줄이는 규칙이다(decision_log 4절, 11-09).
- 이 규칙은 그 예측식의 두 플랜트 항과 하네스 보정 여부를 등급으로 정한다.
  - LOC 뒤 침하 $\Delta z^{post}$
  - 과도 초과 $\delta^{os}$
  - 하네스 보정 여부

$$\hat s_{i,\max} = s_i(k_L) + \Delta s^{geo}_i + \left(c^\ast + m - \hat c(k_L)\right)^+ + \Delta z_i^{post} + \delta_i^{os}$$

| 기호 | 정의 | 단위 |
|---|---|---|
| $s_i(k_L)$ | 마지막 LOC 주기의 다리 $i$ 판독 행정 | m |
| $\Delta s^{geo}_i$ | LOC 때 정착 자세 $(\hat\phi,\hat\theta)$ → 목표 0으로 갈 때 다리 $i$ 행정 변화(소각 근사, 식과 부호는 7.1) | m |
| $c^\ast$ | 기본 틈 목표 `thresholds.clearance_target_m` = 0.05 m | m |
| $m$ | 실행 틈 목표 여유(E3c10 현행 0.03 m, 정의는 7.2 $m_L$) | m |
| $\hat c(k_L)$ | LOC 주기 제어기 틈 추정 | m |
| $\Delta z_i^{post}$ | LOC 뒤 패드 $i$ 추가 침하, 창 $t_L \to t_e$, $t_e = \max(t_{\max}, t_R)$(C-1) | m |
| $\delta_i^{os}$ | 판독 행정 최대 − 첫 READY 때 판독 행정 | m |
| $\hat W_i$ | LOC 뒤 다리 $i$ 하중 증가 추정 = 레벨 정적 분배 하중 − LOC 주기 판독 하중 | N |

### 0.2 봉인 전에 본 자료

#### 0.2.1 본 것 (공개)

- 하네스 P0 J2 경사 행정 여유(`v5/soil_defer/judge_S.json` `d10d6f18…c236f0d0`, `info.P0_margin.rows`)

| 키 | 판독 최대 [mm] | 가드 여유 [mm] | 결과 |
|---|---|---|---|
| `J2|B|fdown-rec` VB / V0 | 682.41 / 681.98 | 0.39 / 0.82 | SGS FL |
| `J2|M|fdown-rec` VB e0 / e0.002 | 669.47 / 682.61 | 13.33 / 0.19 | READY / SGS FL |
| `J2|T|fdown-rec` VB e0 | 671.15 | 11.65 | READY |
| `J2|B|diag-rec` V0·VB | 682.43 ~ 682.77 | 0.03 ~ 0.37 | SGS FR |

  `v5/d1.jsonl`(K1 전): `J2|{T,M,B}|fup-rec` 모든 설정 SGS RL.

- 저장 Chrono 7건의 LOC 뒤 침하·행정(`b1/evidence/post_loc_digest_stored.jsonl`, 도구 `post_loc_digest.py`, 초안 2.2 표 그대로). 이 자료로 예측 범위(8절), D-b 5 mm, D-c 3 mm, D-e 20 mm, 예측자 오차 10 mm를 정했다.
  - READY 뒤 추가 침하는 ≤ 0.14 mm이고, 예외는 끝 재레벨 1건의 4.8 mm다.
  - J1 앞내림 앞 패드의 LOC 뒤 침하는 1.5~3.2 mm, 뒤 패드는 46~48 mm다.
  - $\delta^{os}$는 J1 앞내림 FL 24.2 mm, J1 대각 FR 7.0 mm, J2 평지 2.1~9.9 mm다.
  - 같은 양 Chrono − 하네스는 −0.25 mm(J1 앞내림), −2.0 / −5.4 mm(J2 평지)다.
- 격자 시험 판정서(0.4)와 P1 V16bp(0.4).
- LOC 앵커 검토 `06_analysis/02_control/k2/judgement/loc_anchor_review.md` 0~3.1절, 그림자 진단 `06_analysis/02_control/k2/loc_shadow/hsh_report.md` 0·1·4절(B1·P5r4 결과가 아니다).
- P5r4+K1 **규칙** rev3 `verif_matrix/las_p5r4_k1_rules_rev3.md` 첫머리와 RV3-0.4 표(규칙 형식만).
- 코드(읽기만): `03_src/outrigger_sim/control/c2.py` 200~225·2166~2215·8955~9070행, `04_scripts/02_chrono/s9_batch.py` 391~437행, `04_scripts/02_chrono/run_S9.py` 445~500행, `04_scripts/03_control/k2/loc_shadow/loc_anchor_shadow.py` 40~80행. `03_src/outrigger_sim/control/`의 마지막 커밋은 `ba3adcc`(K-2, 클래스·프리셋 끔)다(2026-11-11 `git log`).

#### 0.2.2 보지 않은 것 (금지)

- LAS-b P5r4+K1 결과: `06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/` 폴더 전체, `06_analysis/02_control/verif_matrix/p5k_judge/`, `07_results/S9/batch_V5-LAS-P5R4-K1*`.

### 0.3 terramechanics-expert 검토 요약 (2026-11-10, 결과 전, 공개)

검토 원문은 메인 세션이 전달한 요약이다. 원문 리포트의 파라미터 표(출처 유형별)가 근거 원본이다. 2026-11-11 재검토 항목은 10.0절이다.

| 항목 | 검토 값·내용 | 출처 유형 | 반영한 곳 |
|---|---|---|---|
| SCM 패드 침하 기구 | 지나간 최대 하중의 Bekker 침하 + 점성 지연 $\tau = R/(n\,p/z)$ ≈ 0.4~0.5 s(J2). 시간 의존 크리프(압밀·2차 압축)와 전단 유발 침하는 없다 | Chrono 소스(`SCMTerrain.cpp` `SCMLoader::ComputeInternalForces`: σ를 τ보다 먼저 정하고 되먹임 없음) | 14.1 모형 범위 |
| J2 민감도 | $k_{eq}$ 4 %, $n$ 0.02 차로 침하가 20 mm 이상 바뀐다 | 세트 파라미터 감도(유도식) | 14.1 D-e 해석 제한 |
| 지지력 이용률 | $p/q_{ult}$ 약 0.82~0.87. 파괴 근처라 Bekker 침하는 하한이다 | 유도식(지지력 계산) | 14.1 |
| 격자 인자 $f$(2차 검토) | SCM 패드 힘은 패드 다각형 안 접촉 절점 수 $N_h$ × $\Delta^2$에 σ가 걸리고, Bekker $b$는 접촉 절점 볼록 껍질의 $2A/P$다. 그래서 침하가 연속 Bekker 값의 $f$배가 된다(0.4). J2, 격자 0.01 m의 위상 범위는 $f-1$ 후방 −1.3~+4.2 %, 전방 −2.8~+5.0 % | Chrono 소스(`SCMTerrain.cpp` 584-588, 1366-1377, 1475) + 유도식 + 절점 위상 스캔 | 0.4, D-a·D-c, 3.4, 6.1 |
| 절점 하나 계단 | $\delta z_{1n} = z\,\Delta^2/(nA)$. J2, $\Delta$ 0.01 m에서 후방 0.82 %·$z$(약 1.0 mm), 전방 0.47 %·$z$(약 0.5 mm). 첫 후보판의 "앞 1.6·뒤 3.8 mm"는 0.02 m 값이라 폐기 | 유도식 | D-c 표시 |
| 패드 접선 유연도 | 앞 3.6 / 뒤 7.9 mm/kN(2.2배) | 유도식(Bekker 접선) | 7.3 $\kappa_z$ 패드 종류별 |
| ×1.1 침하 배율 | 접선 유연도 ∝ $F^{1/n-1} = F^4$, ×1.1이면 $z$ 1.61배. 저장 REM 1.57~1.74 | 유도식 + 저장 Chrono | 8절 P-9 |
| 시작 조건 | `--start-limit record_only` 권고(T-6) | 운용 판단 | 1.1 `START_LIMIT` |
| 문턱 | 3 / 5 / 10 / 20 / +5 mm 그대로(사용자 결정, R-6) | — | 3.3. 2026-11-11 재검토(10.0) |

### 0.4 SCM 격자 인자 (2026-11-10, 결과 전, 공개)

SCM 패드 하중은 $F = N_h\,\Delta^2\,(k_c/b_{hull} + k_\varphi)\,z^n$이고, 연속 Bekker는 $F = A\,(k_c/b_{poly} + k_\varphi)\,z^n$이다. 같은 $F$에서

$$z_{grid} = f\,z_{cont},\qquad f = \left[\frac{N_h\,\Delta^2\,(k_c/b_{hull} + k_\varphi)}{A\,(k_c/b_{poly} + k_\varphi)}\right]^{-1/n}$$

| 기호 | 정의 | 단위 |
|---|---|---|
| $\Delta$ | 패드 SCM 격자 간격(`--grid`) | m |
| $N_h$ | 패드 다각형 안 접촉 절점 수(σ > 0, `node_stats_in_outline` `n_contact`) | — |
| $b_{hull}$ | 접촉 절점 볼록 껍질 $2A_{hull}/P_{hull}$(`contact_hull_area_m2`, `contact_hull_perimeter_m`) | m |
| $A$, $b_{poly}$ | 패드 다각형 면적, $2A/P$(YAML `pad_shapes`; 패드 B 후방 0.0607 m²·0.1306 m, 전방 0.1071 m²·0.1714 m) | m², m |
| $k_c, k_\varphi, n$ | J2 세트(`02_params/scm_soil_sets.json`): 16,430 N/m^(n+1), 1,724,690 N/m^(n+2), 0.2 | — |
| $f$ | 격자 인자. $f > 1$이면 격자 침하가 연속값보다 깊다 | — |

- 하중 계단 $\Delta F$에 대한 $\Delta z$도 같은 $f$배이므로 $\Delta z/z$는 격자와 무관하다. 바뀌는 것은 절대 침하(그래서 절대 행정)다.
- $f$는 패드가 격자에 대해 어디 놓였는지(xy 오프셋·요)에 따라 바뀐다. 패드가 기울거나 미끄러지면 실행 중에도 바뀐다.
- 위상 범위($f - 1$, J2, `evidence/gridconv_scan/phase_band.txt`)

| 격자 $\Delta$ [m] | 후방 250 | 전방 330 | 절점 하나 계단 $\Delta^2/(nA)$ 후방 / 전방 |
|---|---|---|---|
| 0.02 | −22 ~ +29 % | −8 ~ +12 % | 3.3 % / 1.9 % |
| 0.01 | −1.3 ~ +4.2 % | −2.8 ~ +5.0 % | 0.82 % / 0.47 % |
| 0.005 | −0.8 ~ +1.6 % | −0.5 ~ +1.3 % | 0.21 % / 0.12 % |

- P1 `V16bp_J2_B_RL_{2cm,1cm}`(2026-10-26, 단일 패드 RL 72.81 kN, `07_results/S9/batch_P1_V16_20261026_032113/`): 침하 2 cm 95.27 mm, 1 cm 118.60 mm. 각 격자의 이산 기준 $f\,z_{cont}$(95.27 / 118.65 mm)와 0.05 % 안(`evidence/gridconv_scan/p1_levels.txt`). 0.02 m를 버린 근거다.
- 저장 J1·J2 Chrono 레벨링 결과는 모두 패드 0.01 m(U-S9G-1, `run_S9.py` `P3B_PAD_GRID_M`)다(`evidence/gridconv_scan/grid_census.txt`).
- **GC PASS → 0.01 m 확정 근거**: 판정서 `a483ac48…8a89e56b`, 두 경로 `PASS`, 대조 127항목 불일치 0.
  - Chrono가 각 격자의 이산 Bekker 법칙을 따랐다(G-1 최대 3.1×10⁻⁶).
  - $z/f$가 격자와 무관했다(G-2 최대 1.1×10⁻⁴ mm, G-3 ≤ 1.0×10⁻⁶).
  - 원시 **절대** 침하는 0.01 대 0.005 m에서 RL +2.74 mm, FL −0.80 mm 다르다. D-c(절대 행정)를 보정값으로 등급 내는 이유다(3.3).
  - 같은 시험의 **증분** 침하 차는 RL +0.347 mm(Δz 16.6 mm 중), FL −0.076 mm다(판정서 2.2 E-6·E-8, terramechanics TR-1). D-a를 보수 쪽으로 등급 내는 이유는 이 값이 아니라 실행 중 접촉 절점 변화다(3.3 D-a, 10.0 TR-1).
  - 범위: 위상 0 오프셋 한 점, 단일 패드, J2, 패드 B.

## 1. 파라미터와 대상 제어기

### 1.1 값

| 이름 | 값 | 근거 |
|---|---|---|
| `CTRL_TAG_VB` | `final_C4G2_P3_LAS_K1` | 1.2 |
| `CTRL_TAG_V0` | `final_C4G2_LAS_K1` | 1.2 |
| `CTRL_PRESET` | `C2Config.with_10hz_d1()` 프리셋 그대로(LAS-b 이륙 접근 감속 켬, K1 순서 관문 켬, K-2 `_TCL` 끔, 그 밖 CLAUDE.md "제어기" 행). 래퍼 없음 | 1.2 |
| `P7_REF` | `06_analysis/03_hydraulic/coupled/v5/soil_defer/s2d_SC.jsonl`(sha256 `70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa`, 추적 안 됨)의 P0 줄(`s2d.candidate == "P0"`) `commands_sha256` 집합, 키는 줄의 `d1.key`로 H-P 실행 키와 맞춘다 | 후보판 1절 `not_adopted` 규칙 |
| `HULL_DLL_SHA` | `cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15`(`hull_hook.VALIDATED_DLL_SHA256`) | 격자 시험 prelaunch. 실행 전 감사에서 코드 상수와 다시 대조 |
| `START_LIMIT` | `record_only` | terramechanics T-6 권고(0.3). cad-expert 구현 확인이 실패하면 개정판 |
| 실행 커밋 `HEAD_M` | 이 규칙에 값을 적지 않는다. 정의: 봉인판과 구현(13절 R-7·R-8·R-4·R-13)이 병합된 master 커밋으로, 1.2 프리셋 조건 I-17을 만족하고 깨끗한 checkout(또는 그 커밋 고정 worktree)인 것. 전체 sha를 prelaunch에 적는다 | 4절 I-1·I-10 |
| 하네스 커밋 | `HEAD_M`과 같다(다르면 prelaunch에 이유와 함께 적고, 그 커밋도 I-17을 만족해야 한다) | I-9 |
| 풀 | 배치표(compute-scheduler-expert)의 행별 P/E. 프로젝트 규칙상 P 우선(Q4) | I-6 |

- 이 판에 미정 값 칸은 없다. 남은 빈칸은 10.0절 TR 답 칸뿐이고, 그 칸이 채워지기 전에는 봉인하지 않는다.

### 1.2 대상 제어기를 P5r4 결과와 무관하게 정한 판단

**판단: 정해도 된다.** 근거는 다음과 같다.

1. 사용자 사전 결정(2026-11-11): P5r4가 '통과'여도 지금은 프리셋을 전환하지 않고 v5 뒤 후보로 기록하며, v5 제어기는 `final_C4G2_LAS_K1`이다. 그래서 P5r4 판정이 어느 쪽이든 R8 프리셋 기본값과 태그는 바뀌지 않는다.
2. 후보판이 파라미터를 P5r4 결정 뒤로 미룬 이유는 "채택 전환이 E3c10·LOC 취소·SGS·DSb75의 기본값을 바꿀 수 있어서"였다(후보판 1절). 전환이 없으면 그 갈래가 없다. K-2(`_TCL`)는 11-11에 채택하지 않았으므로 그 갈래도 없다.
3. B1은 "운용 제어기의 경사 틈 여유를 줄이는" 설계 입력이다. 그 근거는 운용(v5) 제어기에서 재야 한다. P5r4 후보 제어기로 재면 v5 B1 근거가 아니다.
4. `03_src/outrigger_sim/control/`의 마지막 커밋은 `ba3adcc`(K-2, 클래스·프리셋 끔)이고, K1 전환(`b0979d1`, 병합 `b53d890`·감사 수정 `e67dae8`) 뒤 프리셋 기본값을 켠 커밋은 없다(2026-11-11 `git log`, 코드 줄은 읽기만).

남는 위험과 처리

| # | 위험 | 처리 |
|---|---|---|
| CR-1 | P5r4 관련 코드가 병합되면서 프리셋 기본값이 바뀌거나(실수) 래퍼가 겹친다 | I-17: `HEAD_M`의 `C2Config.with_10hz_d1()` 설정 덤프를 기준 커밋 `e67dae8`의 덤프와 비교한다. 두 덤프에 다 있는 필드는 값이 같아야 하고, `e67dae8` 뒤 새로 생긴 필드는 클래스 기본값(끔)과 같아야 한다. 하나라도 어기면 실행하지 않는다 |
| CR-2 | v5 뒤 P5r4(또는 다른 후보)가 채택되면 이 B1 근거가 그 제어기에 맞지 않을 수 있다 | 16절 알려진 한계로 적는다. 채택 전환이 E3c10, R4c30, K1 순서 관문, LOC 취소(L1gs), SGS, DSb75, LAS-b 중 하나의 동작을 바꾸면 B1 근거를 다시 낸다(그 전환 규칙에 적는다) |
| CR-3 | `P7_REF`(`s2d_SC.jsonl`)가 K1 전 명령일 수 있어 D-h가 `K-DIFF`로 나온다 | D-h는 정보 등급이다. `K-DIFF` 키는 0.2 하네스 여유를 B1 근거로 쓰지 않는다(3.3 그대로) |

### 1.3 실행 시점

- **사용자 결정 N-1 (a)(2026-11-11)**: Q5 (가)("P5r4+K1 판정·채택 결정 뒤 실행")를 다음으로 바꾼다. 대상 제어기는 P5r4 판정과 무관하다(1.2).
  - 봉인 커밋은 P5r4+K1 Chrono 재실행의 postrun 뒤에 한다(실행 중 master 커밋 금지 규칙).
  - 실행 조건: 이 판의 봉인과 실행 전 감사 차단 0, 그리고 P5r4+K1 Chrono 재실행이 끝남. **P5r4 판정은 기다리지 않는다.**
  - P코어 배치는 compute-scheduler-expert 배치표로 정한다.

### 1.4 태그 규칙

- `--expect-controller`와 하네스 태그는 1.1 값과 **문자열 완전 일치**로 확인한다. 접미사(`_K1`, `_LAS`)나 접두로 판별하지 않는다. `final_C4G2_K1`(LAS-b 끔 + K1), `final_C4G2_LAS`(K1 전), `final_C4G2_P3`(③ 단독), `final_C4G2_LAS_K1_TCL`(K-2)은 모두 다른 제어기다.
- ③(VB) 여부를 코드가 판별해야 하면 `v5_options.is_extend_start_tag`를 쓴다. 집합 `EXTEND_START_TAGS`는 쓰지 않는다.
- `s9_batch.v5_vb_rows()`는 `--expect-controller`를 `V5_P3_CONTROLLER` = `final_C4G2_P3`로 바꾼다(`s9_batch.py:391, 423-437`). **B1 행은 이 함수로 만들지 않는다.** `v5_vb_argv()`로 옵션만 받고 `--expect-controller final_C4G2_P3_LAS_K1`을 붙인다.
- 이름 겹침: 이 규칙의 "B1"은 명세 426.9.B1(연구 B ×1.1), 3단계 H-7의 "B1", 2026-10-26 P2 해석 보완 B1~B5와 다르다. "K1"은 R4c30 순서 관문이고 touch-phase K1(탈락)·하네스 키 토큰 `K1`(크롤러 강성 ×1)과 다르다.

## 2. 실행 단위

### 2.1 Chrono 6행 (`run_S9.py level`, 묶음 `V5-B1-CREEP`)

- 공통 조건
  - `--soil J2`(균일), `--pad-variant dwg_rear250`(패드 B), `--fs-kN 4`
  - VB 옵션 `s9_batch.v5_vb_argv()` + `--expect-controller final_C4G2_P3_LAS_K1`(1.4), 시드 P3b 기본
  - 압력 `normal`, IMU `ideal`, 격자 `--grid 0.01 --crawler-grid 0.04`(U-S9G-1 M14s 이중 터레인), `--settle-dashpot zrp`, `--threads 4`, `--start-limit record_only`, `--b1-grid-record full`(6절 격자·제어기 주기 기록, cad-expert 구현)

| ID | 사례 이름 | 오거 | `--floor-roll` / `--floor-pitch` [°] | 질량 | `--duration` [s] | 예산 다리 | 역할 |
|---|---|---|---|---|---|---|---|
| C1 | `B1_J2_B_bottom_Fs4_VB_fdown` | bottom | 0 / 2.8 | 1.0 | 160 | FL | 핵심 |
| C2 | `B1_J2_B_middle_Fs4_VB_fdown` | middle | 0 / 2.8 | 1.0 | 160 | FL | 핵심 |
| C3 | `B1_J2_B_top_Fs4_VB_fdown` | top | 0 / 2.8 | 1.0 | 160 | FL | 보조 |
| C4 | `B1_J2_B_bottom_Fs4_VB_diag` | bottom | 1.925 / 1.4 | 1.0 | 160 | FR | 핵심 |
| C5 | `B1_J2_B_top_Fs4_VB_fup` | top | 0 / −2.8 | 1.0 | 160 | RL | 핵심 |
| C6 | `B1_J2_B_bottom_Fs4_m1p1_VB_fdown` | bottom | 0 / 2.8 | `--mass-scale 1.1` | 180 | FL | 감도(×1.1) |

- 인자 순서는 cad-expert가 행 모듈로 한 번 정해 prelaunch에 전개 argv와 sha256을 적는다. I-2는 그 전개 argv와 `batch.json cases[].argv`를 한 글자씩 비교한다.
- **예산 다리 $b$**: 표의 다리가 미리 정한 예산 다리다. 판독 최대가 다른 다리에서 나오면 그 다리를 실제 예산 다리 $b^\ast$로 기록한다. 모든 지표는 $b$와 $b^\ast$ 둘 다 내고, 등급에는 $b^\ast$를 쓴다.
- C6의 180 s 근거: J2 ×1.1 평지는 READY가 약 118 s이고, FINAL-REP는 180 s가 필요했다.

### 2.2 하네스 짝 (E코어, `run_v5.py d1` 부분 집합, 태그 `final_C4G2_P3_LAS_K1` / `final_C4G2_LAS_K1`)

| 묶음 | 내용 | 실행 수 |
|---|---|---|
| H-P | C1~C5 키 × {VB, V0} × e {0, 2e-3}, $m$ = 0.03 | 20 |
| H-W | C6: `J2|B|fdown-rec` ×1.1 × {VB, V0} × e {0, 2e-3} | 4 |
| H-M0 | C1·C5 키 × {VB, V0} × e 0, $m$ = 0(연구용 하위 클래스, `enable` 유지 + `margin_m = 0`, 2.4) | 4 |
| H-SH0 | H-P VB e0 4실행(C1·C2·C4·C5 키)의 그림자 끈 짝 | 4 |

- H-P·H-W·H-M0 28실행은 모두 `OUTRIGGER_LOC_SHADOW=1`(기록 전용 그림자)로 돌린다(U-7 (a)).
- H-SH0 4실행과 해당 그림자 켬 4실행의 명령 해시가 모두 같아야 그림자 기록을 쓴다. 하나라도 다르면 그림자 기록을 버리고, 그림자 끈 28실행을 다시 돌려 그것을 판정에 쓴다(M-12는 하네스 쪽 `NA`).
- 하네스가 질량 배율을 지원하지 않으면 H-W는 비고, C6은 D-c에서 빠진다(3.1 V-4).
- 각 실행은 10 Hz 다리별 판독 행정·패드 침하·하중·자세·틈 추정·주기 기록을 npz로 남긴다(python-expert 구현).

### 2.3 G-S 건조 실행 (U-6 (a))

- 목적: 본 실행 전에 argv 꼴마다 러너가 시작·정체성 검사·기록 필드를 통과하는지 본다. 판정 값을 보지 않는다.
- 대상: Chrono argv 꼴 2개(C1 꼴, C6 꼴), `--duration 10`. 하네스 H-P VB e0 1실행, H-M0 1실행. 같은 `HEAD_M`, 같은 env·풀.
- 출력으로 보는 것: rc, `expect_controller.ok`, 태그 문자열, `hull_hook` 값, `num_threads_chrono`, 5.1 격자 기록·M-4h·M-12 입력 필드의 **키 이름 존재 여부**, H-M0의 E3c10 사건 이름(값 제외), 러너 로그 `errors N`. 힘·행정·침하·시각 값은 출력하지 않는다.
- 공개: 판정서 1절에 시각·명령·출력 범위를 적는다. 건조 실행 폴더는 본 배치와 다른 이름으로 두고, 끝나면 키 목록만 남긴다.
- 실패하면 원인을 고치고(코드 수정이면 `HEAD_M`이 바뀐다) 다시 건조 실행한다. 이 판의 문장을 바꿔야 하면 개정판이다.

### 2.4 옵션 × 단계 겹침 표

cad-expert·python-expert가 실제 코드 줄로 칸을 확인하고(확인자·시각을 prelaunch에 적음), 실행 전 감사가 대조한다.

| 옵션 | 바꾸는 단계·설정 | 겹칠 수 있는 옵션 | 겹치면 생기는 일 | 정한 처리 |
|---|---|---|---|---|
| `v5_vb_argv()` | 유량 포화, 밸브 τ, 로드측 해제, 잠금 겹침·닫힘 지연, 잠금 창 플랜트 추종, ③ 추적 | `v5_vb_rows()` | 기대 태그가 `final_C4G2_P3`로 덮임 → I-3 실패 | 1.4: `v5_vb_rows()` 금지 |
| `--expect-controller` | 러너 태그 검사 | 래퍼·프리셋 | 같은 규칙을 두 번 켬 | 래퍼 없이 프리셋만, `controller_meta`로 확인(I-3·I-17) |
| `--start-limit record_only` | `target.acceptance` OFF만(`run_S9.py:464-500`). LEVEL 경로·S-3·P-S8-28·REANCHOR는 프리셋 그대로 | 시작 조건(V-3) | 시작 거부가 구조적으로 생기지 않음 → `MISSING_START` 0이 정상 | V-3 그대로, $R_c$ > 1이면 기록 |
| `--mass-scale 1.1`(C6) | 플랜트 질량·관성 ×1.1, 무게중심 유지 | 제어기 질량(D1″ 명목) | 제어기에 배율이 새면 감도 실행이 아님 | I-11 |
| H-M0 $m$ = 0 | E3c10 `margin_m` = 0 | R4c30(`flat_soil_margin_m` 0.03) | `enable=False`로 끄면 E3c10이 안 켜진 것으로 보여 정착 기울기 ≤ 1°일 때 R4c30이 +30 mm를 대신 켤 수 있다(`c2.py:8988-9013`) | `enable` 유지 + `margin_m = 0`(U-5 (a)). E3c10이 +0으로 실행 목표를 정해 R4c30이 막힌다. 기대 사건 `INFO_LOC_CLEARANCE_MARGIN:50` |
| `OUTRIGGER_LOC_SHADOW=1`(하네스만) | 그림자 훅, 기록 추가 | 명령 경로 | 명령이 바뀌면 판정 실행이 아님 | 2.2 H-SH0 해시 짝 |
| `OUTRIGGER_HULL_HOOK` | SCM 볼록 껍질 fast | 상속 env | 계획 밖 값 상속 | 실행 셸에서 지우고 미설정(기본 fast). I-7 |
| 격자 기록 R-G1~R-G3 | 기록만(`GetNodeInfo` 읽기) | 패드 힘 | 기록이 힘을 바꾸면 판정 실행이 아님 | 켬·끔 짧은 짝 `step_series.npz` 비트 동일(5.1) |
| `OMP_WAIT_POLICY=PASSIVE`, `--threads 4` | 실행 정체성 | 풀 배치 | 스레드 수가 다르면 비트가 다르다 | I-4·I-5 |

## 3. 관문과 등급

### 3.0 처리 순서

```
TR 답(10.0) → S-0 봉인 → 구현 병합(HEAD_M) → 경로 2 sha 고정 → 하네스 28 + H-SH0 4
→ K 상수 고정(7.3) → G-S 건조 실행 → 실행 전 감사 → prelaunch(추적 밖)
→ Chrono 6 → postrun → 경로 2 → 경로 1 → K-R 대조 → 등급 → 판정서 → 판정 후 감사 → integrity → 커밋
```

### 3.1 행 유효성 (각 Chrono 행)

| 코드 | 조건 | 실패 시 |
|---|---|---|
| V-1 | rc 0, `result.json`·`record/record.npz`·`step_series.npz` 존재, 끝 주기 $n_{end} \ge n_{dur} - 1$(T-11) 또는 SGS·FAULT로 끝난 정상 종료 | 1회 `--resume`(4.3). 다시 실패하면 `MISSING` |
| V-2 | 실행 정체성 I-1~I-17 모두 참(4절) | `INVALID`(다시 돌리지 않는다. 원인을 판정서에 적는다) |
| V-3 | 시작 거부 없음(시작 거부 = 이름이 `REJ_`로 시작하는 사건이 하나라도 있음). LOC가 1회 이상 있음 | 시작 거부면 `MISSING_START`(다시 돌리지 않는다). LOC가 없으면 `NO_LOC` |
| V-4 | 짝 하네스 VB e0 실행이 있고 유효함. (사용자 결정 2026-11-12 Q-6 (a)) 하네스 줄 유효 = 오류 없음(meta `error` 없음·rc 0), 태그가 1.1 값과 문자열 일치, 줄이 가리키는 npz의 sha256이 줄에 적힌 값과 일치(끝 시각 조건은 두지 않음) | 짝이 없으면 그 행의 D-c 값은 `NA`. 다른 등급은 낸다 |

- 행 상태는 `VALID` / `MISSING` / `MISSING_START` / `NO_LOC` / `INVALID` 가운데 하나다.

### 3.2 빈 집합 금지 (묶음 상태)

| 묶음 상태 | 조건 |
|---|---|
| `COMPLETE` | 6행 모두 `VALID` |
| `PARTIAL` | 핵심 4행(C1·C2·C4·C5) 모두 `VALID`, C3·C6 가운데 `VALID`가 아닌 행 ≥ 1 |
| `UNDETERMINED`(판정 불가) | 핵심 행 가운데 하나라도 `VALID`가 아님, 또는 하네스 H-P VB e0 짝 5개 가운데 하나라도 없음 |

- 등급(3.3)은 `COMPLETE`·`PARTIAL`에서만 낸다.
- 각 등급은 계산에 쓴 행 ID 목록과 행 수를 함께 적는다. 계산 대상 행이 0개인 등급은 통과로 세지 않고 `NA`다.
- `PARTIAL`에서는 빠진 행이 바꿀 수 있는 등급에 `PARTIAL` 표시를 붙인다. C3가 빠지면 $\mathcal R$을 쓰는 D-a·D-b·D-c·D-d, C6가 빠지면 D-g다(표시만, 등급 계산은 남은 행으로).
- 더하는 조건

| # | 조건 | 처리 |
|---|---|---|
| E-1 | 하네스 줄 가운데 meta가 없거나 태그가 1.1과 다름 | 그 줄은 없는 것으로 센다. H-P VB e0 짝이 빠지면 `UNDETERMINED` |
| E-2 | 7.3 상수를 계산할 다리·실행이 0개 | 그 상수 `NA` → 그 상수를 쓰는 후보(P-B·P-C는 $\kappa_z$·$\delta_{allow}$, P-D·P-G는 $C_{type}$) `NA`. D-d는 남은 후보로 내고 "후보 축소"를 적는다 |
| E-3 | D-f의 H-M0 C5 짝이 7.2에 따라 빠져 0개 | D-f = `NA`(계산 불가)로 적는다(`FUP-NA`와 구분) |
| E-4 | M-12가 모든 LOC에서 `NA` | "M-12 기록 없음"만 적는다(등급 영향 없음) |
| E-5 | 러너 로그 단계별 `errors N` 합 > 0이고 `errors_left` > 0 | 판정 전 차단(I-12) |
| E-6 | 도구가 선택한 행 수가 0인데 등급이 나옴 | 도구 결함. 판정 후 감사 E에서 차단 |

- 도구는 묶음 이름(`V5-B1-CREEP`)과 행 ID(C1~C6), 하네스 묶음 이름(H-P 등)으로 행을 고른다. 태그로 고르지 않는다. 태그는 정체성 확인(I-3·I-9)에만 쓴다.

### 3.3 설계 입력 등급

$\mathcal{R}$ = 핵심 4행 + C3(VALID일 때) = ×1.0 행 집합이다. 행정·침하는 모두 실제 예산 다리 $b^\ast$ 값이다. 문턱 비교 꼴은 4.4다.

| 코드 | 양 | 등급 규칙 | B1 설계에서의 효과 |
|---|---|---|---|
| **D-a 크리프 허용** | $Z_{ch} = \max_{r\in\mathcal R} \Delta z^{post}_{b^\ast}(r)$, $\Delta z^{post} = z(t_e) - z(t_L)$(LOC 마지막 → 창 끝 $t_e = \max(t_{\max}, t_R)$, $t_R$ 없으면 $t_{\max}$; C-1), $Z_{hn}$ = 같은 양 하네스 H-P VB·V0 e0 최대((사용자 결정 2026-11-12 Q-2 (a)) 하네스 양은 짝 Chrono 행 $r$의 $b^\ast$ 다리 값으로 잰다. 하네스 자신의 $b^\ast$가 아니다). 보정 $Z^{corr}_{ch} = \max_r \Delta z^{post,corr}_{b^\ast}(r)$, $\Delta z^{post,corr} = z(t_e)/f(t_e) - z(t_L)/f(t_L)$(0.4, 6) | 원시 등급: `ZA-1` $Z_{ch} \le Z_{hn} + 3$ mm / `ZA-2` 그 밖. 보정 등급: 같은 규칙을 $Z^{corr}_{ch}$로. **최종 등급: 둘 중 하나라도 `ZA-2`이면 `ZA-2`, 둘 다 `ZA-1`이면 `ZA-1`(U-3 (b), 보수 쪽. TR-1 찬성으로 확정).** 두 등급이 다르면 "격자 위상 의존"을 붙인다. **조건(C-5, 사용자 결정 2026-11-11)**: (가) 보정값은 $t_L$·$t_e$ 두 주기 모두 유효한 격자 기록(M-11 유효성 검사 통과)이 있을 때만 계산한다. 하나라도 없거나 무효면 그 행의 보정값은 `NA`, 원시값만 쓰고 "격자 기록 없음"을 붙인다(대체 범위를 쓰지 않는다). 모든 행이 `NA`면 보정 등급 `NA`, 최종 등급 = 원시 등급. (나) 원시만 `ZA-2`이고 보정은 `ZA-1`이면 B1 하네스 보정량은 원시 초과량 $Z_{ch} - Z_{hn}$을 쓰고 "격자 몫 포함 보정"으로 적는다. (다) 행마다 $z_{b^\ast}(t_e)\,(f(t_e) - f(t_L))$를 기록한다(등급에 안 씀, (사용자 결정 2026-11-12 Q-3 (a)) 기록 시각 $t_e$ 통일). 기록용으로 $z(t_{\max}) - z(t_L)$도 낸다. 이유: 격자 시험의 원시 차 RL +2.74 mm는 절대 침하 차이고 증분 차는 +0.35 mm(Δz 16.6 mm 중)였다. D-a의 증분 $\Delta z^{post}$에서 격자 몫은 $f$가 일정하면 $(f-1)\Delta z^{post}$(후방 60 mm에서 ≤ 2.5 mm)다. 그러나 $t_L \to t_{\max}$ 사이 접촉 절점이 바뀌면 절점 하나당 후방 약 1.1 mm·전방 약 0.45 mm가 더해진다. 그래서 원시값만으로는 격자 몫과 침하 몫을 가를 수 없다(terramechanics TR-1) | $Z_{B1} = \max(Z_{ch}, Z^{corr}_{ch}, Z_{hn}) + Z_{soil}$. $Z_{soil}$은 **가정**이다(TR-8 후보 Z0 0 mm / Z1 2 mm / Z2 $0.1\,z_{b^\ast}(t_R)$ / Zf 현장 평판 유지 시험값, 10.0). B1 설계 문서는 Z1·Z2를 감도로 쓰고 Zf가 오면 바꾼다. `ZA-2`이면 B1 하네스 스윕의 침하 항을 Chrono 쪽으로 보정한다 |
| **D-b 과도 초과** | $O = \max_{r\in\mathcal R} \max(\delta^{os}_{b^\ast,ch}, \delta^{os}_{b^\ast,hn})$. (사용자 결정 2026-11-12 Q-2 (a)) $\delta^{os}_{b^\ast,hn}$은 짝 H-P **VB e0** 실행의, 짝 Chrono 행 $b^\ast$ 다리 값이다(V0·e0.002는 산포로 기록만) | `OS-MAX`: $O$ > 5 mm / `OS-FINAL`: $O$ ≤ 5 mm | `OS-MAX`면 B1은 "예상 최대 행정"을 쓰고 허용값 $O$를 더한다. `OS-FINAL`이면 "예상 최종 행정"을 써도 된다. READY가 없는 행(SGS)은 $\delta^{os}$ = `NA`이고, 행 수에서 뺀 것을 적는다 |
| **D-c 하네스 대응** | 원시 $\Delta_r = s_{b^\ast,\max}^{ch} - s_{b^\ast,\max}^{hn,\text{VB e0}}$. 격자 몫 $\delta^{grid}_r = z_{b^\ast}(t_{\max})\,(1 - 1/f_{b^\ast}(t_{\max}))$. 보정 $\Delta^{corr}_r = \Delta_r - \delta^{grid}_r$. 하네스 패드 요소는 연속 Bekker라 $f \equiv 1$(14절, R-10) | **등급은 보정값 $\Delta^{corr}_r$로 낸다.** `H-OK`: 모든 $\lvert\Delta^{corr}_r\rvert \le 3$ mm / `H-CONS`: $\Delta^{corr}_r < -3$인 행 ≥ 1이고 $> 3$인 행 0 / `H-OPT`: $\Delta^{corr}_r > 3$인 행 ≥ 1. 원시 $\Delta_r$로도 계산해 함께 적고, 다르면 "격자 위상 의존". **기록 없음**: 행의 $f_{b^\ast}(t_{\max})$를 6절 기록으로 정할 수 없으면 대체 범위 $\delta^{grid}_r \in z_{b^\ast}(t_{\max})\,[1 - 1/f_{\min},\ 1 - 1/f_{\max}]$(0.4 표 0.01 m 행, 패드 종류별)를 쓰고 $\Delta^{corr}_r$ 구간 전체로 분류한다. 구간 전체가 +3 mm 위일 때만 "+", 전체가 −3 mm 아래일 때만 "−", 전체가 [−3, +3] mm 안이면 "0". 문턱에 걸치면 "격자 위상 의존(부호 미확정)"이고 세지 않는다. 미확정 행이 있으면 등급에 표시와 행 ID를 붙이고, 전부 미확정이면 `NA`. 대체 범위로 분류한 행에는 "대체 범위"를 붙인다 | `H-OK`·`H-CONS`: 하네스 스윕을 그대로 B1 근거로 쓴다(`H-CONS`는 차를 여유로 기록). `H-OPT`: 방향별(fdown·diag·fup) 최대 $\Delta^{corr}_r$을 더하고 그 방향은 B1 채택 전에 Chrono 확인 행을 둔다. 원시 `H-OPT`·보정 아님이면 B1 설계 문서는 원시 $\Delta_r$을 위상 몫으로 적는다. **절점 계단 표시**: 행마다 $\delta z_{1n} = z_{b^\ast}(t_{\max})\,\Delta^2/(n A_{b^\ast})$를 적고 $\lvert\Delta^{corr}_r\rvert \le \delta z_{1n}$인 행에 "절점 계단 수준"(등급 불변) |
| **D-d 예측자** | 후보 $q \in$ {P-A, P-B, P-D, P-G, P-C}(7.2, P-D는 C-2, P-G는 R-3 사용자 결정)의 $E_q = \max_{r\in\mathcal R}\lvert e_{b^\ast}(r, q)\rvert$. SGS 행은 $s_{\max}$를 가드 도달 값으로 둔다(하한, 7.4). (사용자 결정 2026-11-12 Q-5 (a)) T-14 대조가 어긋난 행은 D-d의 모든 후보에서 뺀다(뺀 행 ID를 적는다). 남은 행 가운데 어느 한 행에서라도 $e(r,q)$가 `NA`인 후보 $q$는 $E_q$ = `NA`(후보끼리 같은 행 집합으로 비교) | `PRED-q`: $E_q$ 최소인 $q$(같으면 P-A → P-B → P-D → P-G → P-C 순으로 단순한 쪽) / `PRED-FAIL`: 최소 $E_q$ > 10 mm | `PRED-q`면 B1은 그 형식을 쓴다. `PRED-FAIL`이면 B1 설계 전에 새 예측 형식을 재등록한다(개정판). 후보 밖 형식은 쓰지 않는다. 판정서에는 $E_q$ 옆에 M-12의 $E_{\text{P-A*}}$를 적는다(7.5) |
| **D-e B1 필요성** | C1·C2·C4의 Chrono 가드 여유 $g_r = s_{guard} - \max_i s_{i,\max}$, SGS 사건 | `NEED-RECHECK`: 세 행 모두 $\tilde g_r = \min\big(g_r,\ g^{corr}_r - z_{b^\ast}(t_{\max})(1 - 1/f_{\max})\big) \ge$ 20 mm이고 SGS 0 / `B1-OPEN`: 그 밖(C-3, 사용자 결정 2026-11-11). $f_{\max}$는 0.4 표 0.01 m 위상 범위 상단(패드 종류별). 그 행의 $t_{\max}$ 격자 기록이 없거나 무효면 $\tilde g_r = g_r - z_{b^\ast}(t_{\max})(f_{\max} - f_{\min})$ | `NEED-RECHECK`면 사용자에게 B1 필요성과 J2 경사 운용 권고(Q6)를 다시 묻는다. 판정서에 $g^{corr} = g + \delta^{grid}$와 위상 범위로 정한 $g$ 범위를 병기한다. 판정과 Q6 질문에는 "SCM 명목 세트 안의 여유이고 실토양 여유가 아니다. $k_{eq}$ −4 %이면 침하가 +22~30 mm 늘어난다"를 적는다(TR-4) |
| **D-f fup 범위** | C5 Chrono SGS 여부, H-M0 C5 짝 VB·V0($m$ = 0)의 SGS 여부 | `FUP-OUT`: C5 SGS이고 H-M0 C5 두 짝 모두 SGS / `FUP-IN`: C5 SGS이고 H-M0 짝 중 하나라도 READY / `FUP-NA`: C5 SGS 없음. (사용자 결정 2026-11-12 Q-4 (a)) 짝 하나가 7.2(R4c30 사건) 또는 V-4로 빠진 경우: C5가 SGS이고 남은 짝 하나가 SGS면 `FUP-OUT` + "짝 1개", 남은 짝이 READY면 `FUP-IN` + "짝 1개", 둘 다 빠지면 `NA`(E-3) | `FUP-OUT`: B1 범위(0~30 mm)로 풀 수 없다. 운용 권고 문제로 분리해 사용자에게 묻는다(Q6). `FUP-IN`: B1 대상 방향에 fup를 넣는다 |
| **D-g ×1.1 감도** | $e_{b^\ast}(\text{C6}, q^\ast)$($q^\ast$ = D-d가 고른 형식, 상수는 7.3 그대로), $E_{q^\ast}$ | `W-OK`: $\lvert e(\text{C6})\rvert \le E_{q^\ast}$ + 5 mm / `W-EXT`: 그 밖 / `W-NA`: C6가 VALID가 아니거나 D-d가 `PRED-FAIL` | `W-EXT`면 B1 예측자에 질량(하중) 항이 필요하다(B1 설계 문서에서 다룸). C6 값은 D-a~D-c 최대 계산에 넣지 않고 따로 적는다. 문턱은 고정 +5 mm로 둔다(TR-5: $E_{q^\ast}$ ≤ 10 mm에서 비례 꼴 $1.61E$와 차 ≤ 1.1 mm, $E$ < 8.2 mm에서 고정 꼴이 더 엄격, 비례 꼴은 토양 $n$을 규칙에 넣음). 판정서에 비 $\lvert e(\mathrm{C6})\rvert / E_{q^\ast}$를 기록한다(기록, 1.61 근처면 "오차가 침하와 같이 커짐") |
| **D-h 기준 정합(P-7)** | `P7_REF`의 해당 키 대 H-P 20실행의 명령 해시 | `K-SAME`: 모두 같음 / `K-DIFF`: 하나라도 다름 / `K-NA`: 기준에 그 키가 없음 | `K-DIFF`면 해시가 다른 키를 적고 그 키의 0.2 하네스 여유를 B1 근거로 쓰지 않는다. 등급 계산은 그대로 한다 |

- 안전 기록(관문 아님): `FAULT_STROKE_END`, 다리 부상(T-8), 크롤러 재착지(T-9)가 있으면 `SAFETY_NOTE`로 판정서 첫머리에 적고 그날 바로 메인 세션에 보고한다. 다른 행은 계속 돈다.

### 3.3.1 사용자 결정 2026-11-11: 판정 정의 변경 C-1~C-5 (terramechanics 재검토 반영, 결과 전)

아래 C-1~C-5는 **사용자 결정 2026-11-11로 모두 채택**했다(C-1 (A), C-2 (가)(나)(다), C-3, C-4 (가)(나), C-5 (가)(나)(다)). 본문(3.3 표, 4.4, 5·6·7·9절)에 넣었다. 이 절의 문장과 본문이 다르게 읽히면 이 절이 맞다. 단 2026-11-12 결정(R-3 P-G 추가, 15절 Q-1~Q-8)으로 바뀐 D-d 후보 집합·동점 순서와 7.1 자세 입력은 본문이 맞다. C-4 (가)의 격자 기록 주기는 사용자 결정으로 **실행 전체 10 Hz**이고, 대체 조항은 6절이다.

| # | 근거 | 채택 문장 | 바뀐 곳 | 판단 |
|---|---|---|---|---|
| C-1 | TR-2 | (A) **침하 창 끝** $t_e = \max(t_{\max}, t_R)$($t_R$ 없으면 $t_{\max}$). D-a와 0.1 예측식의 $\Delta z^{post}$는 $z(t_e) - z(t_L)$이다. $z(t_{\max}) - z(t_L)$은 기록한다. 이유: $\delta^{os}$가 $s(t_R)$ 기준이라 창을 $t_{\max}$에서 끊으면 $z(t_R) - z(t_{\max})$(저장 결과 2.3~4.6 mm)가 어느 항에도 들어가지 않는다. / (B) 창은 그대로 두고 D-b에 $\delta^{os*} = s_{\max} - s(t_R) + [z(t_R) - z(t_{\max})]$를 쓴다 / (C) 바꾸지 않음 | 0.1 식, 3.3 D-a, M-4, M-11의 $\tau$ 목록에 $t_e$ 추가, 7.3 | **(A)**. "LOC 뒤 침하 전부"라는 D-a의 뜻에 맞고, D-d 오차 $e$는 $s_{\max}$를 직접 써서 영향이 없다 |
| C-2 | TR-3 | (가) **후보 P-D 추가**: P-A + $\Delta z_i$, $\Delta z_i = C_{type}\,[(F^{pk}_{L,i} + \max(\hat W_i,0))^{1/n_a} - (F^{pk}_{L,i})^{1/n_a}]$. $C_{type}$은 하네스 H-P 20실행에서 패드 종류별 최대, $n_a$ = 0.2(**가정 지수**, J2 세트 값), $F^{pk}_{L,i}$ = LOC까지 지나간 최대 패드 하중(판독). D-d 동점 순서는 P-A → P-B → P-D → P-C. (나) **$\kappa_z$·$C_{type}$ 적합 창을 다리별** $t_{e,i}$(C-1 (A)를 채택하면 그 정의, 아니면 다리별 판독 행정 최대 주기 $t_{\max,i}$)로 잰다. (다) 상수 파일에 패드 종류별 실행별 $\kappa$ 최대/최소 비를 기록하고 > 1.5이면 "κ 비선형"(표시만) | 7.2 후보 표, 7.3, 3.3 D-d·D-g, 9절 구현 요구 | **(가)(나)(다) 모두**. 선형 $\kappa$는 $n$ = 0.2에서 하중 10 % 낮은 다리를 34 % 과대 예측해 C5 RL(15~60 mm)에서 10 mm를 넘기 쉽다. P-D는 하네스 상수만 쓰므로 Chrono 결과 전에 고정할 수 있다. $n_a$를 실기 제어기가 모른다는 점은 B1 설계 문서의 가정으로 남는다 |
| C-3 | TR-4 | `NEED-RECHECK`는 세 행 모두 $\min\big(g,\ g^{corr} - z_{b^\ast}(t_{\max})(1 - 1/f_{\max})\big) \ge$ 20 mm이고 SGS 0일 때만. $f_{\max}$는 0.4 표 0.01 m 위상 범위 상단(패드 종류별). 그 행의 격자 기록이 없거나 무효(C-4)면 $g - z_{b^\ast}(t_{\max})(f_{\max} - f_{\min})$을 쓴다 | 3.3 D-e, T-5 | **채택**. `NEED-RECHECK`는 덜 보수 쪽 결론이라 격자 위상 하단까지 넣는 것이 맞다 |
| C-4 | TR-6 | (가) M-11의 $f_i(\tau)$는 $\tau$와 **같은 10 Hz 주기 $n$의 기록**으로만 정한다(T-7의 "간격 > 10주기" 규칙을 지움). R-G1은 **실행 전체 10 Hz**(사용자 결정). 결과 전 비용 측정에서 비용이 5 %를 넘으면 6절 대체 조항의 창 기록으로 바꾼다. (나) $N_h \ge 3$을 지우고 **유효성 검사**로 바꾼다: (i) $N_h \in [0.95,\ 1.05]\cdot A/\Delta^2$, (ii) $n\,\lvert\sum\sigma\Delta^2 - N_h\Delta^2(k_c/b_{hull} + k_\varphi)z^n\rvert / \sum\sigma\Delta^2 \le 0.005$(R-G1 `sigma_sum_area_N`·`sinkage_geometric_m`). 하나라도 실패하면 그 시각 $f$는 "기록 무효"이고 D-c 대체 범위와 C-5 (가)를 적용한다 | 5 M-11, 6 R-G1, 4.4 T-7, 3.3 D-c 기록 없음 정의 | **(가)(나) 채택**. 저장 J1 경사 재구성에서 $t_L \to t_{\max}$ $\Delta f$가 최대 0.106(15절점)이었고 128기록 중 8개가 정적 위상 범위 밖이었다. 1 s 간격이면 그 변화를 놓친다 |
| C-5 | TR-1 | D-a 보수 쪽 계산 조건. (가) 보정 $\Delta z^{post,corr}$는 $t_L$·$t_{\max}$(C-1 (A)면 $t_e$) **두 주기 모두** 유효한 격자 기록이 있을 때만 계산한다. 하나라도 없으면 보정 등급 `NA`, 원시 등급만 쓰고 "격자 기록 없음"을 붙인다(대체 범위를 쓰지 않는다: 구간 폭이 약 7 mm라 3 mm 문턱에 늘 걸친다). (나) 원시만 `ZA-2`이고 보정은 `ZA-1`이면 B1 하네스 보정량은 원시 초과량 $Z_{ch} - Z_{hn}$을 쓰고 "격자 몫 포함 보정"으로 적는다. (다) 행마다 $z_{b^\ast}(t_e)\,(f(t_e) - f(t_L))$를 기록한다(등급에 안 씀. C-1에 맞춰 $t_e$로 통일, 본문 3.3 D-a와 같음 (사용자 결정 2026-11-12 Q-3 (a)); 참고로 $z(t_{\max})(f(t_{\max}) - f(t_L))$도 기록) | 3.3 D-a, M-11 | **(가)(나)(다) 채택**. 성능 손실(B1이 $m$을 덜 줄임)만 있고 안전 손실은 없다 |

### 3.4 격자 위상이 문턱에 주는 영향 (결과 전 평가, 기록)

크기 기준: 격자 0.01 m, J2. 절대 침하 $z$ ≈ 후방 120 mm·전방 95 mm에서 격자 몫 $z(1-1/f)$는 후방 약 −1.6 ~ +4.8 mm, 전방 약 −2.7 ~ +4.5 mm다. 실행 중 패드가 움직이면 $t_L$과 $t_{\max}$ 사이에 $f$가 바뀔 수 있다(M-4h, 6절).

| 등급 | 영향 | 근거 | 처리 |
|---|---|---|---|
| D-a | 중간 | $f$가 일정하면 $(f-1)\Delta z^{post}$(후방 15~60 mm에서 ≤ 약 2.5 mm)만 남는다. $f$가 바뀌면 $z\,\delta f$가 더해진다. 문턱 3 mm와 같은 크기 | 원시·보정 보수 쪽 등급(U-3 (b)), 다르면 "격자 위상 의존" |
| D-b | 낮음 | $t_R \to t_{\max}$ 같은 패드 행정 차, 그 사이 침하 변화가 작다(0.2: READY 뒤 ≤ 0.14 mm) | 처리 없음 |
| D-c | **높음** | Chrono 절대 행정 대 하네스($f \equiv 1$) 절대 행정의 차라 격자 몫이 통째로 들어간다 | 보정값으로 등급, 원시 병기 |
| D-d | 낮음 ~ 중간 | Chrono 자신의 $s_i(t_L)$에서 출발하므로 절대 격자 몫은 빠지고 $t_L \to t_{\max}$ 침하 몫만 남는다 | 판정서에 $E_q$와 $Z_{ch} - Z^{corr}_{ch}$를 나란히 |
| D-e | 중간 | 가드 여유 $g$는 Chrono 절대 행정이라 격자 몫이 들어간다(약 5 mm 대 20 mm) | 원시 $g$로 등급, $g^{corr}$와 범위 병기 |
| D-f | 낮음 ~ 중간 | 가드 근처 행에서만 뒤집힐 수 있다 | C5의 $g$와 $\delta^{grid}$를 판정서에 |
| D-g | 중간 | ×1.1은 $z$가 약 1.6배라 격자 몫도 그만큼 크다 | C6의 $\delta^{grid}$를 판정서에 |
| D-h | 없음 | 하네스 명령 해시만 본다 | — |

## 4. 실행 정체성·재실행·문턱 비교

### 4.1 정체성

| 코드 | 조건 | 출처 |
|---|---|---|
| I-1 | 실행 커밋 = `HEAD_M`(1.1 정의), checkout 깨끗함(추적 파일 변경 0) | prelaunch, result.json `code_state` |
| I-2 | 6행 argv가 2.1절 표와 prelaunch 전개 argv와 한 글자씩 같음. 전개 argv와 sha256을 prelaunch에 적음 | prelaunch, batch.json `cases[].argv` |
| I-3 | `--expect-controller final_C4G2_P3_LAS_K1`이고 러너 보고 태그가 문자열로 같음(`expect_controller.ok` 참), 제어기 클래스 `C2Controller` | result.json `c2_setup`, `controller_meta` |
| I-4 | `num_threads_chrono` = 4 | result.json |
| I-5 | 자식 env `OMP_WAIT_POLICY=PASSIVE` | batch.json 기록값 |
| I-6 | 풀이 배치표의 행별 풀과 같음. 실행 중 affinity 변경은 판정서에 | batch.json `pool`, 배치표 |
| I-7 | `hull_hook` requested = effective = `fast`, DLL sha = `HULL_DLL_SHA`, `MIXED_HULL_MODE` 없음 | result.json `hull_hook`, batch.json |
| I-8 | `params_file` 지문 = 봉인 때 YAML(`02_params/rexome33.yaml`) sha(prelaunch에 적음) | result.json |
| I-9 | 하네스 32실행: 하네스 커밋(1.1), 태그 = 1.1 값, H-M0는 연구 하위 클래스 이름과 `margin_m = 0`·`enable` 참이 meta에 있음, 그림자 켬·끔이 meta에 있음 | 하네스 jsonl meta |
| I-10 | 시작 직전·끝난 직후 `git rev-parse HEAD`와 `git status --porcelain --untracked-files=no`가 같고 추적 변경 0. 실행 중 그 checkout에 병합·checkout 없음 | prelaunch, postrun |
| I-11 | C6 제어기 질량 = YAML 명목(배율 누수 없음), 플랜트 질량 = 명목 × 1.1 | C6 `result.json` |
| I-12 | 러너 로그 단계별 `errors N` 비영이면 `errors_left` = 0일 때만 진행, 첫 시도 오류는 판정서에 기록 | `tools/verif/log_errors.py` |
| I-13 | 추적 파일에 `{이름}` 자리표시 없음. prelaunch 값은 추적 밖(배치 폴더)에 채움 | `tools/verif/placeholder_scan.py --allow`(허용 = `b1_creep_prelaunch_draft.md`) |
| I-14 | 실행 셸에서 지운 env·더한 env 목록, 인터프리터 플래그(`-I` 포함) | prelaunch |
| I-15 | 실제 argv와 rc를 `batch.json`에 남김(러너가 남기지 않으면 래퍼가) | batch.json |
| I-16 | G-S 건조 실행 기록(2.3)이 본 실행 시작보다 앞섬 | prelaunch `dry_run` |
| I-17 | `HEAD_M`의 `C2Config.with_10hz_d1()` 설정 덤프 대 `e67dae8` 덤프: 공통 필드 값 같음, `e67dae8` 뒤 새 필드는 클래스 기본값과 같음(1.2 CR-1) | prelaunch `preset_dump_diff`(python-expert 도구, sha 고정) |

- 실행 전 기록 틀: 같은 폴더 `b1_creep_prelaunch_draft.md`(추적 틀, 값은 배치 폴더에 채움).

### 4.3 재실행

- 오류·결과 파일 누락(V-1 실패)이면 그 행만 1회 `--resume`한다. 조건은 같은 `HEAD_M`, 같은 배치 폴더다.
- 원 로그·폴더는 배치 밖 `attempt1/`로 옮긴다(지우지 않는다). 판정서에 `rerun_of`를 적는다.
- 시작 거부·`NO_LOC`·`INVALID`는 다시 돌리지 않는다.
- 하네스 실행은 결정적이므로 오류 행은 같은 커밋에서 다시 돌리고 출력 해시를 적는다.

### 4.4 문턱 비교 꼴

허용 $\varepsilon_{th}$ = 1×10⁻⁹ m. 문턱과 차가 $\varepsilon_{th}$ 안이면 "같다"로 보고 아래 포함 쪽으로 분류한다. 이 허용은 두 경로 **값 대조 허용**(9절)과 다른 문장이다. 두 경로는 같은 꼴로 비교한다. 이 표에 없는 문턱이 도구에 있으면 실행 전 감사 R에서 차단한다.

| # | 문턱 | 통과(앞) 쪽 꼴 |
|---|---|---|
| T-1 | D-a 3 mm(원시·보정 각각) | $Z - Z_{hn} - 0.003 \le \varepsilon_{th}$이면 `ZA-1` |
| T-2 | D-b 5 mm | $O - 0.005 > \varepsilon_{th}$이면 `OS-MAX` |
| T-3 | D-c ±3 mm | $\lvert\Delta^{corr}_r\rvert - 0.003 \le \varepsilon_{th}$이면 "0", $\Delta^{corr}_r - 0.003 > \varepsilon_{th}$이면 "+", $-\Delta^{corr}_r - 0.003 > \varepsilon_{th}$이면 "−". 대체 범위의 구간 끝도 이 꼴 |
| T-4 | D-d 10 mm | $\min_q E_q - 0.010 > \varepsilon_{th}$이면 `PRED-FAIL`. 같음 판단 $\lvert E_q - E_{q'}\rvert \le \varepsilon_{th}$ |
| T-5 | D-e 20 mm | $\tilde g_r - 0.020 \ge -\varepsilon_{th}$(C-3) |
| T-6 | D-g $E_{q^\ast}$ + 5 mm | $\lvert e(\mathrm{C6})\rvert - E_{q^\ast} - 0.005 \le \varepsilon_{th}$이면 `W-OK` |
| T-7 | M-11 격자 기록 유효성(C-4) | 같은 주기 $n_{rec} = n_\tau$ 기록이 없으면 "기록 없음". (i) $0.95\,A/\Delta^2 \le N_h \le 1.05\,A/\Delta^2$($N_h$ 정수, 경계는 실수 비교 $\varepsilon$ = 1×10⁻⁹), (ii) 법칙 잔차 $r_\sigma - 0.005 \le 10^{-12}$(무차원). 하나라도 어기면 "기록 무효" |
| T-8 | 다리 부상: 첫 LOC($n_{L1}$) 이후 접촉력 0이 0.1 s 이상 | 1 ms 계열 연속 표본 ≥ 100 |
| T-9 | 크롤러 재착지: `p3b.t_departure_s` 이후 0.01 W 이상, $W$ = `p3b.weight_N` | $F_{cr} - 0.01W \ge -10^{-6}$ N |
| T-10 | 격자 기록 비용 5 % | 켬/끔 벽시계 비 − 1.05 ≤ 0. "끔" = `--b1-grid-record` 없음(기존 `s9_rows[].pad_nodes` 계산은 그대로, 새 npz 기록만 끔), "켬" = `--b1-grid-record full` |
| T-11 | V-1 끝 시각 | $n_{end} \ge n_{dur} - 1$ |
| T-12 | P-2 크리프 정지(예측, 기록) | `p3b.creep_stop` 저장값을 그대로 읽음 |
| T-13 | M-12 표시 5 mm | $\lvert E_{\text{P-A}} - E_{\text{P-A*}}\rvert - 0.005 > \varepsilon_{th}$이면 "앵커 단일 표본 의존" |
| T-14 | 7.2 $m_L$ 대조 | 사건 정수 mm → m 값과 제어기 상태 `clearance_target_m`의 차 ≤ 5×10⁻⁴ m(정수 mm 반올림)이면 같음 |

### 4.5 시각과 표본

- 10 Hz 시각($t_L$, $t_{L1}$, $t_R$, $t_{\max}$, $t_{end}$, 사건 시각)은 정수 주기 $n = \mathrm{round}(t/0.1)$로 저장·비교한다. "같은 표본"은 $n$이 같다는 뜻이다.
- 1 ms 계열 조회는 `searchsorted(t, τ − 1e-9)`이고 $\tau = n \cdot 0.1$ s다.
- $t_{\max}$ = 모든 다리 판독 행정 최대가 처음 나온 $n$(최대 비교는 $\varepsilon_{th}$, 같은 최대면 가장 작은 $n$).

## 5. 지표 정의 (경로 1·2가 같은 정의로 계산)

- $t_L$ = 마지막 LOC(`crawler_liftoff_confirmed`의 마지막, 취소 뒤 재LOC 포함), $t_{L1}$ = 첫 LOC, $t_R$ = 첫 READY 진입(P3-5 `t_first_ready_s`), $t_{\max}$(4.5), $t_{end}$ = 마지막 표본

| 코드 | 양 | 식 |
|---|---|---|
| M-1 | 시각 | $t_{dep}$, $t_{L1}$, $t_L$, LOC 취소 수, $t_R$, $t_{creep}$(`p3b.creep_stop.t_final_s`), $t_{\max}$ |
| M-2 | 행정 예산 | $s_i(t_L)$, $s_i(t_R)$, $s_{i,\max}$, $b^\ast = \arg\max_i s_{i,\max}$, $g = s_{guard} - s_{b^\ast,\max}$, SGS·`WARN_LIFT_STROKE_LIMITED` 시각 |
| M-4 | 침하 | $t_e = \max(t_{\max}, t_R)$($t_R$ 없으면 $t_{\max}$), $\Delta z^{post}_i = z_i(t_e) - z_i(t_L)$(C-1). 다리별 창 끝 $t_{e,i} = \max(t_{\max,i}, t_R)$, $t_{\max,i}$ = 다리 $i$ 판독 행정 최대가 처음 나온 주기, $\Delta z^{post}_{i,e_i} = z_i(t_{e,i}) - z_i(t_L)$(7.3 적합용). 기록용 $z_i(t_{\max}) - z_i(t_L)$, $z_i(t_R) - z_i(t_{\max})$, $z_i(t_R) - z_i(t_L)$, $z_i(t_{end}) - z_i(t_R)$, LOC 뒤 최대 침하율(1.0 s 후진 차분), $\Delta z_i / \Delta F_i$(할선, $t_L \to t_R$) |
| M-5 | 과도 초과 | $\delta^{os}_i = s_{i,\max} - s_i(t_R)$($t_R$ 없으면 `NA`), $t_{\max} - t_L$ |
| M-6 | 예측자 오차 | $e_i(q) = s_{i,\max} - \hat s^{(q)}_{i,\max}$(+ = 예측 부족) |
| M-4h | 패드 수평 변위(기록) | $\lVert \Delta \mathbf{r}_{i,xy} \rVert$($t_L \to t_{\max}$, 지면 고정 좌표). Chrono는 패드 바디 위치, 하네스는 패드 요소 접선 변위. 등급에 쓰지 않는다 |
| M-7 | 크롤러 | $t_L$·$t_R$·$t_{end}$의 격자 참 틈(P3-5), 제어기 틈 추정, 이탈 뒤 최대 크롤러 하중 |
| M-8 | 규칙 작동 | E3c10(`INFO_LOC_CLEARANCE_MARGIN:<mm>`), R4c30(`INFO_LOC_FLAT_SOIL_MARGIN:<mm>`, `..._SKIPPED:order`), `INFO_LOC_REVOKED`, `order_gate.decisions` 수, DSb75 HOLD·RELEASE 사유, SGS, P30fz·LWa |
| M-9 | P3 행(기록) | `p3b` P3-1~P3-8, SL 분류 |
| M-10 | 짝 차 | M-2·M-4·M-5의 Chrono − 하네스 VB e0. e0.002·V0는 산포로 |
| M-11 | 격자 인자(Chrono) | 다리 $i$, $\tau \in \{t_L, t_R, t_{\max}, t_e, t_{end}\}$의 $N_h$, $b_{hull}$, $f_i(\tau)$, $z_i/f_i$, $\delta^{grid}_i(\tau)$, $\delta z_{1n,i}(\tau)$, $\Delta z^{post,corr}_i$, $\Delta^{corr}_r$, $g^{corr}$, $\tilde g$, $z(t_e)(f(t_e) - f(t_L))$, 유효성 검사 값 $N_h\Delta^2/A$와 $r_\sigma$. $f_i(\tau)$는 6절 기록 가운데 **주기 $n_\tau$와 같은 주기의 기록**으로만 정하고(C-4), T-7의 유효성 검사를 통과해야 쓴다. 법칙 잔차 $r_\sigma = n\,\lvert\Sigma_\sigma - N_h\Delta^2(k_c/b_{hull} + k_\varphi)z^n\rvert / \Sigma_\sigma$, $\Sigma_\sigma$ = `sigma_sum_area_N`, $z$ = `sinkage_geometric_m`. 하네스는 $f \equiv 1$ |
| M-12 | LOC 앵커(기록) | 7.5 |

## 6. B1 Chrono 행 기록 요구 (구현 cad-expert, 봉인 전 확인)

| 항목 | 시각 | 내용 | 출처 함수 |
|---|---|---|---|
| R-G1 | **실행 전체 10 Hz**(모든 제어 주기, 사용자 결정 2026-11-11) | 다리별 `n_inside`, `n_contact`, `contact_hull_area_m2`, `contact_hull_perimeter_m`, `sinkage_geometric_m`, `sigma_sum_area_N` 등 8필드, 모양 (n, 4) | `03_src/outrigger_sim/chrono/scm_model.py` `node_stats_in_outline`. 같은 다섯 필드는 커밋 `f1efed7`부터 모든 level 실행의 `result.json` `s9_rows[].pad_nodes`에 10 Hz로 이미 있다(cad-expert 2026-11-12) |
| R-G2 | 10 Hz | 다리별 패드 바디 중심 xy [m](지면 고정), 요 [rad] | 패드 바디 자세 |
| R-G3 | 실행 시작 | 패드 격자 $\Delta$, SCM 평면 원점·회전, 패드 다각형(기체 국부), $b_{poly}$ | npz meta |
| R-G4 | 100 Hz(IMU 표본마다) | IMU 원시 기울기(비력 기울기) roll·pitch [rad], 키 `imu_*` | IMU 센서 모델 출력 |
| R-C1 | 10 Hz(제어 주기마다) | 제어기 주기 기록(경로 1·2 공통 입력). 키: `n`(정수 주기, (n,)), `load_read_N`(다리별 판독 하중, (n,4)), `att_raw_rad`(주기 평균 원시 기울기 roll·pitch = 제어기 `_period_raw_attitude_rad`, (n,2)), `c_hat_m`(제어기 틈 추정 $\hat c$, (n,)), `c_hat_corner_m`(모서리별 $\hat c_k$, (n,4), 7.2 P-G), `c_target_m`(실행 틈 목표 $c^\ast_{run}$, (n,)) | C2 제어기 상태(읽기만) |

- **기록 파일**: `record/b1_grid_record.npz` 한 파일에 R-G1~R-G4·R-C1을 담는다. 키 이름은 cad-expert 구현이 정하되 R-C1은 위 이름을 쓴다. 실제 키 목록과 모양은 prelaunch에 전개하고, 경로 1·2는 그 목록의 같은 키만 읽는다. R-G1 다섯 필드가 npz와 `s9_rows[].pad_nodes`에 둘 다 있으면 두 값이 같아야 한다(다르면 그 행의 격자 기록 전부 "기록 무효").
- **격자 기록 주기 = `full`(실행 전체 10 Hz) 확정.** 결과 전 비용 측정(cad-expert 2026-11-12, 판정 값 출력 없음): 켬/끔 `step_series.npz` 비트 동일, 벽시계 비 0.996(T-10 통과). 측정 명령·폴더·비를 prelaunch에 적는다.
- **대체 조항(쓰지 않음, 기록용)**: T-10을 넘었다면 쓰려던 창 기록은 $[t_{L1} - 1\,\text{s},\ t^{\uparrow} + 2\,\text{s}]$와 첫 READY 진입 앞뒤 1 s를 10 Hz, 나머지를 1 s로 두는 것이었다. 온라인 근사: 첫 READY 전에는 10 Hz로 계산하고, 저장은 규칙 집합(창 안 주기 + 1 s 간격)만 하며, READY 뒤 늦은 재상승이면 그 전에 지난 주기는 "기록 없음"이다. `full`이 확정됐으므로 이 조항은 적용하지 않는다. 다시 쓰려면 개정판이다.
- R-G2는 사후 재구성용(등급 계산에 쓰지 않음)이다.
- 기록 필드가 빠진 행은 `INVALID`가 아니라 D-c 대체 범위·C-5 (가)·M-12 `NA`로 처리한다. 단 R-C1이 빠지면 그 행의 M-6·D-d는 `NA`다(예측자 입력 없음).
- 기록 추가는 패드 힘·명령을 바꾸지 않아야 한다(읽기 전용). 위 켬·끔 짝의 비트 동일 결과를 prelaunch에 적는다.

## 7. 예측자 후보 (LOC 주기 정보만)

### 7.1 기하

- 패드 위치 $(x_i, y_i)$는 YAML `legs.<leg>.pad_bottom_center_retracted_m[0:2]`(기체 좌표, = `C2Geometry.pad_xy_m`)에서 읽는다.
- $\Delta s^{geo}_i = x_i\,\hat\theta_{L} - y_i\,\hat\phi_{L}$(소각 근사). **기체 원점(선회 링 중심축)을 고정하고 자세만 0으로 돌릴 때의 행정 변화**다. 네 다리 평균을 뺀 꼴이 아니고, 원점의 상하 이동은 틈 항 $(c^\ast + m_L - \hat c)^+$가 맡는다. pitch > 0 = 앞내림, roll > 0 = 왼쪽 위. 앞내림이면 앞 다리가 늘어나고, 왼쪽 위면 왼쪽 다리가 줄어든다.
- **자세 입력** $(\hat\phi_L, \hat\theta_L)$ = $t_L$ 주기($n_L$)의 **주기 평균 원시 기울기**(R-C1 `att_raw_rad`, 제어기 `_period_raw_attitude_rad`, S-3 편향과 같은 입력) [rad]. 필터 자세는 쓰지 않는다(τ 0.8 s × 2단 지연 때문에 예산 다리가 10~20 mm 과대 예측된다, dynamics-expert R-3).
- **R-3 확인(dynamics-expert, 결과 전, 저장 기록, 사용자 결정 2026-11-12로 닫음)**: 식과 부호가 맞다. 저장 X4-nd에서 예산 다리 FL의 $\Delta s^{geo}$ 대입 결과는 +42.3 mm(산포 3.7 mm)이고 부호를 뒤집으면 산포 178 mm다. X4-ed FR은 +58.7 mm(산포 4.7 mm), 뒤집으면 233 mm다. 같은 보고에서 P-A 꼴의 오차는 X4-nd +1.9 mm, X4-ed −18.2 mm였고, P-G 꼴로는 −4.7 mm(끝 틈 초과)였다. 이 값은 B1 결과가 아니라 저장 J1 행 재계산이다(공개).

### 7.2 후보와 $m_L$

| 후보 | $\hat s^{(q)}_{i,\max}$ |
|---|---|
| P-A | $s_i(t_L) + \Delta s^{geo}_i + (c^\ast + m_L - \hat c(t_L))^+$ |
| P-B | P-A + $\kappa_z\,\max(\hat W_i, 0)$ |
| P-C | P-B + $\delta_{allow}$ |
| P-D | P-A + $C_{type(i)}\,\big[(F^{pk}_{L,i} + \max(\hat W_i, 0))^{1/n_a} - (F^{pk}_{L,i})^{1/n_a}\big]$(C-2) |

| 기호(P-D) | 정의 | 단위 |
|---|---|---|
| $C_{type}$ | 패드 종류별(전방 330 / 후방 250) 상수, 7.3 | m/N^(1/n_a) |
| $n_a$ | 0.2. **가정 지수**(J2 세트 $n$). 실기 제어기는 $n$을 모르므로 B1 설계 문서에서 가정으로 다룬다 | — |
| $F^{pk}_{L,i}$ | LOC 주기($n_L$)까지 지나간 다리 $i$ 판독 하중(R-C1 `load_read_N`) 최대. SCM 소성 가지가 지나간 최대를 기억하기 때문 | N |

| 후보 | $\hat s^{(q)}_{i,\max}$ |
|---|---|
| P-G | $s_i(t_L) + \Delta s^{geo}_i + \big(c^\ast + m_L - \min_k(\hat c_k + \rho_k + \hat Z_k)\big)^+ + \Delta\hat z_i$(R-3 사용자 결정 2026-11-12) |

| 기호(P-G) | 정의 | 단위 |
|---|---|---|
| $\hat c_k$ | $n_L$ 주기 크롤러 모서리 $k$의 제어기 틈 추정(R-C1 `c_hat_corner_m`). $\min_k \hat c_k = \hat c(t_L)$ | m |
| $\rho_k$ | $x_k\,\hat\theta_L - y_k\,\hat\phi_L$, $(x_k, y_k)$ = 크롤러 모서리(`CRAWLER_XY_BOX_M`), 자세 입력은 7.1과 같음 | m |
| $\Delta\hat z_i$ | P-D가 예측한 다리 $i$ 추가 침하 $C_{type(i)}\,[(F^{pk}_{L,i} + \max(\hat W_i,0))^{1/n_a} - (F^{pk}_{L,i})^{1/n_a}]$ | m |
| $\hat Z_k$ | 네 패드의 $(x_i, y_i, \Delta\hat z_i)$로 맞춘 최소제곱 평면 $\Delta z = a + b\,y - c\,x$(지지 행렬 꼴, 아래)의 모서리 $(x_k, y_k)$ 값 | m |
| $Z_k$ | 같은 평면을 LOC 뒤 실제 패드 침하 $\Delta z_i = z_i(t) - z_i(t_L)$(네 패드)로 맞춘 모서리 값(기록·검증용) | m |
| $h$ | 원점 heave(네 다리 공통 행정 변화) | m |
| $\varepsilon$ | $\hat c_{est}(t_R) - (c^\ast + m_L)$, DONE이 허용한 끝 틈 초과. $\hat c_{est}(t_R)$ = $t_R$ 주기 R-C1 `c_hat_m`, $t_R$ 없으면 `NA` | m |

**식의 출처와 부호(Q-8, dynamics-expert R-3 보고 원문, 사용자 결정 2026-11-12로 확정)**. 기체 좌표 x 전방·y 좌측, pitch $\theta$ > 0 앞내림, roll $\phi$ > 0 왼쪽 위.

- `c2.py` 지지 행렬 $A_i = [1,\ y_i,\ -x_i]$, 패드 수직 변위 $= A_i\,[z,\ \phi,\ \theta]^T$. `predicted_strokes_m`(`c2.py:3226-3248`): pad_rise $= y_i\,d\phi - x_i\,d\theta$. 자세 변화 $(d\phi, d\theta) = (-\hat\phi_L, -\hat\theta_L)$이면 $\Delta s^{geo}_i = x_i\,\hat\theta_L - y_i\,\hat\phi_L$.
- 모서리 쪽 heave는 같은 꼴로 $c^\ast - \min_k(c_k + \rho_k)$이고, $\rho_k = x_k\,\hat\theta_L - y_k\,\hat\phi_L$($(x_k, y_k)$ = `CRAWLER_XY_BOX_M` 모서리, 자세 입력은 7.1과 같은 $t_L$ 주기 평균 원시 기울기).
- 운동학 항등식: $s_i(t) - s_i(t_L) = \Delta s^{geo}_i + h + \Delta z_i$. 틈 루프가 끝날 때 $h = c^\ast + m_L - \min_k(\hat c_k + \rho_k + Z_k) + \varepsilon$.
- $Z_k$가 들어가는 이유: 행정 기반 틈 추정은 패드 침하를 틈 증가로 본다. 그래서 예측에서는 $Z_k$ 대신 예측 침하 $\Delta\hat z_i$(P-D)로 맞춘 평면 값 $\hat Z_k$를 쓴다.
- P-G는 위 항등식에 $\varepsilon = 0$, $\Delta z_i = \Delta\hat z_i$, $Z_k = \hat Z_k$를 넣은 꼴이다. 근거(저장 X4-nd/X4-ed, 결과 전, 공개): 참 $\Delta z$를 넣으면 오차 −4.7 mm이고, 이는 $\varepsilon$ 4.6 / 4.7 mm와 0.1 mm 안에서 같다.
- 관측 $h$ = $s_i - s_i(t_L) - \Delta s^{geo}_i - \Delta z_i$(네 다리 공통. 저장 X4-nd/X4-ed에서 다리 사이 산포 3.7 / 4.7 mm). 행마다 네 다리 값과 그 평균·산포를 기록한다.
- 한계: $(\cdot)^+$ 절단. LEVEL에서 하강 heave가 있으면 P-G는 과대 예측한다(미확인).
- P-G는 LOC 주기 정보와 7.3 상수만 쓴다. $C_{type}$이 `NA`면 P-G도 `NA`(E-2).
- **P-A의 한계(기록)**: P-A는 $\rho_k$와 $Z_k$를 넣지 않는다. 그래서 행마다 다음을 기록한다(등급에 안 씀): 관측 $h$($t_{\max}$와 $t_e$에서), $\rho_{k^\ast}$, $Z_{k^\ast}$와 $\hat Z_{k^\ast}$($k^\ast$ = P-G의 min 모서리), $\varepsilon$.

$$\hat W_i = W^{static}_{i,\ell} - F^{nom}_i(n_L)$$

| 기호 | 정의 | 단위 |
|---|---|---|
| $W^{static}_{i,\ell}$ | YAML `superstructure.auger_levels.<level>.static_leg_loads_N`의 다리 $i$ 값(행의 오거 단계 $\ell$, C6은 × 1.1 하지 않음 — 제어기 명목) | N |
| $F^{nom}_i(n_L)$ | LOC 주기의 `PressureForces.nominal` 다리 $i$ 값 | N |

- (사용자 결정 2026-11-12 Q-1 (a)) 위 $\hat W_i$ 정의(0.1 표의 "레벨 정적 분배 하중 − LOC 주기 판독 하중"을 이 두 출처로 고정).

$$m_L = c^{\ast}_{run}(t_L) - c^\ast$$

| 기호 | 정의 | 단위 |
|---|---|---|
| $c^{\ast}_{run}(t_L)$ | 마지막 LOC 주기까지 나온 `INFO_LOC_CLEARANCE_MARGIN:<mm>`(E3c10) 또는 `INFO_LOC_FLAT_SOIL_MARGIN:<mm>`(R4c30)의 마지막 값(정수 mm → m). 둘 다 없으면 $c^\ast$ | m |
| $m_L$ | P-A에 넣는 여유 | m |

- 근거(코드 읽기): 한 LOC에서 E3c10이 켜지면 R4c30은 평가하지 않고, 실행 목표가 이미 있으면 R4c30이 켜지지 않는다. E3c10은 한 실행에 한 번이고 LOC 취소 뒤에도 남는다(`c2.py:8964-9013`).
- 제어기 실행 목표(R-C1 `c_target_m`의 $n_L$ 값, 하네스는 같은 이름의 주기 기록)와 T-14로 대조한다. 다르면 그 행의 D-d는 `NA`이고 이유를 적는다.
- H-M0: `margin_m = 0`, `enable` 유지. 기대 사건 `INFO_LOC_CLEARANCE_MARGIN:50`. R4c30 사건이 나오면 그 짝은 $m$ = 0 짝이 아니므로 D-f에서 빼고 적는다(E-3).

### 7.3 상수 (하네스에서만, Chrono 결과 전에 고정)

- $\kappa_z$: **패드 종류별, 다리별 창(C-2).** $\kappa_{z,F}$(전방 330, FL·FR)와 $\kappa_{z,R}$(후방 250, RL·RR)는 H-P 20실행의 해당 종류 다리 전부의 $\Delta z^{post}_{i,e_i}/\max(\hat W_i, 1\,\text{N})$ 최대 [m/N]($t_{e,i}$는 M-4). P-B는 다리 $i$의 패드 종류 값을 쓴다. 근거: 접선 유연도 앞 3.6 / 뒤 7.9 mm/kN(0.3).
- $C_{type}$(P-D): 같은 다리·창에서 $\Delta z^{post}_{i,e_i} / \big[(F^{pk}_{L,i} + \max(\hat W_i,0))^{1/n_a} - (F^{pk}_{L,i})^{1/n_a}\big]$의 패드 종류별 최대. 분모 ≤ 0인 다리(하중 증가 없음)는 적합에서 빼고 뺀 수를 적는다. 쓸 다리가 0개면 $C_{type}$ `NA` → P-D `NA`(E-2).
- κ 비 기록: 패드 종류별로 실행마다 $\kappa$ 값(그 실행에서 그 패드 종류 다리들의 $\Delta z^{post}_{i,e_i}/\max(\hat W_i, 1\,\text{N})$ 최댓값)을 내고 실행 사이 최대/최소 비를 적는다. > 1.5이면 "κ 비선형"(표시만, 등급 불변).
- $\delta_{allow}$: H-P 20실행의 $b^\ast$ 다리 $\delta^{os}$ 최대 [m].
- 기록: `b1_harness_constants.json`(값, 쓴 실행 목록, 도구 sha). 그 sha를 실행 전 감사 보고와 prelaunch에 적은 뒤에만 Chrono를 시작한다.

### 7.4 SGS 행

- SGS로 멈춘 행의 $s_{\max}$는 하한이다. 그런 행의 $e$는 `lower_bound` 표시를 붙인다.
- D-d에서 $e$ < 0인 SGS 행은 그대로 쓰고, $e$ ≥ 0이면 하한으로 쓴다. 그 값으로 `PRED-q`가 나와도 판정서에 "하한 포함"을 적는다.

### 7.5 M-12 LOC 앵커 기록 (U-4 (a), 등급에 쓰지 않음)

- 배경: LOC 틈 추정 앵커는 평탄 창 시작 $t_P$ 주기의 0.1 s 원시 기울기 한 표본을 쓴다. 균일 연약 지면에서 영향은 낙관 ≤ +2.7 mm, 비관 ≥ −5.5 mm였다(`loc_anchor_review.md` 0절). P-A의 $(c^\ast + m_L - \hat c)^+$ 항에 들어가고 D-d 문턱 10 mm와 같은 자릿수다.
- LOC마다 기록: 경로 ①/②/③(검토 2절), $c_{min}(t_P)$, $n_P$·$n_L$, 현행 $\hat c(t_L)$, 안 A 그림자 $\hat c_A(t_L)$(중심 원시 기울기 평균, 반창 $w = \min(0.5, t_L - t_P)$ s), $d = \hat c - \hat c_A$, P-A\*(P-A에서 $\hat c$ 대신 $\hat c_A$)의 $e$와 $E_{\text{P-A*}}$.
- 하네스: 2.2 그림자 기록(H-SH0 해시 같을 때만). Chrono: R-G4 `imu_*`(100 Hz)와 R-C1로 사후 재구성(경로 1·2가 각각, 문장 정의로). 필드가 없으면 `NA`(행 상태 불변).
- (사용자 결정 2026-11-12 Q-7 (a)) Chrono M-12의 방법. (a) 위처럼 R-G4로 두 경로가 따로 사후 재구성 / (b) Chrono 러너에 기록 전용 `loc_anchor_shadow`를 붙이고, 켬·끔 짧은 짝 명령 해시가 같을 때만 그 기록을 씀 / (c) Chrono M-12는 `NA`.
- 판정서: D-d 표 옆에 $E_q$, $E_{\text{P-A*}}$, $\max\lvert d\rvert$. T-13이면 "앵커 단일 표본 의존"(표시만).

## 8. 방향 예측 (기록, 등급에 쓰지 않음)

| # | 예측 |
|---|---|
| P-1 | C1~C3 FL의 $\Delta z^{post}$ 0~15 mm, 뒤 패드보다 작음. C5 RL 15~60 mm, ×1.0 다섯 행 중 최대 |
| P-2 | READY → 끝 추가 침하 ≤ 5 mm(재레벨이 없으면 ≤ 0.5 mm). $t_{creep}$ ≤ 마지막 READY + 30 s. $t_{creep}$는 SCM 패드 하중·점성 정착 시각이고 실토양 크리프 종료가 아니다(TR-7) |
| P-3 | 원시 $\Delta_r$ ∈ [−8, +3] mm. 0 또는 음이 더 많음(원시값 기준). 보정 $\Delta^{corr}_r$ 범위 예측은 등록하지 않는다 |
| P-4 | $\delta^{os}$: fdown·fup 5~30 mm, diag 3~15 mm |
| P-5 | C1은 SGS 또는 $g$ < 10 mm. `FAULT_STROKE_END` 0, 다리 부상 0 |
| P-6 | C5 SGS(RL), Chrono 가드 시각 ≤ 하네스 VB e0 가드 시각 |
| P-7 | `P7_REF`에 그 키가 있으면 `K-SAME`. Chrono E3c10 LOC의 `order_gate.decisions` 0 |
| P-8 | P-A의 $e$ > 0이 모든 VALID 행에서 성립, $E_{\text{P-C}}$ ≤ 10 mm |
| P-9 | C6: C1보다 $g$가 작거나 SGS가 이르다. `W-EXT` 예상(×1.1이면 $z$ 1.61배, 저장 REM 1.57~1.74배) |
| P-10 | 모든 LOC의 앵커 경로 ②는 0건. $\lvert d\rvert \le$ 5.5 mm, $d$ > 0은 ≤ +2.7 mm |
| P-11 | ×1.0 C1~C5에서 R4c30 사건 0, `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order` 0. $m_L$은 0.03 또는 0 |
| P-12 | H-M0 4실행의 E3c10 사건 값은 50 mm 또는 사건 없음, R4c30 사건 0 |
| P-13 | G-S 건조 실행은 첫 시도에서 모든 필드 검사를 통과하지 못할 수 있다(R-G1~R-G4·M-4h 미구현, 13절) |
| P-14 | (terramechanics T-P1) ×1.0 행의 $z(t_R) - z(t_{\max})$ ≥ 0이고 예산 다리에서 ≤ 6 mm |
| P-15 | (T-P2) J2 경사 행의 $t_L \to t_{\max}$ 예산 다리 $\lvert\Delta f\rvert$ ≤ 0.03(후방 ≤ 약 4절점) |
| P-16 | (T-P3) C5 RL의 P-B 오차가 C1~C4 예산 다리보다 크다 |
| P-17 | (T-P4) `t_final_s`가 나온 행에서 그 시각 뒤 예산 다리 하중 변화 ≤ 0.5 kN |

## 9. 두 경로 재집계

| 경로 | 담당 | 고정 시점 | 출력 |
|---|---|---|---|
| 경로 1 | python-expert 지표 도구(`b1_creep_metrics.py` 가칭, `evidence/post_loc_digest.py`를 정식 도구로 옮기고 확장) | 실행 전 감사 전에 sha 고정 | `b1_metrics_path1.json` |
| 경로 2 | control-expert 독립 스크립트(경로 1 코드·출력을 보지 않음, numpy·json만) | **Chrono 결과 전**에 sha 고정, 하네스 짝 출력으로 시험 | `b1_metrics_path2.json` |

- 구현 요구(2026-11-12 추가): P-G와 $\rho_k$·$\hat Z_k$(7.2), 7.1 자세 입력 = R-C1 `att_raw_rad`, $\hat W_i$ 출처(7.2), P-A 한계 기록 항목, D-d 행 제외·후보 `NA` 규칙, D-f 짝 1개 경우, V-3 `REJ_`, V-4 하네스 유효 조건, T-8·T-9 시각·W, κ 비의 실행 κ, `P7_REF` 줄 선택, R-C1·`b1_grid_record.npz`와 `pad_nodes` 일치 검사, M-12 방법(Q-7). 구현 요구(2026-11-11 사용자 결정 C-1~C-5 포함): 창 끝 $t_e$·다리별 $t_{e,i}$(M-4), P-D와 $C_{type}$·κ 비(7.2·7.3), D-a 조건 (가)(나)(다), D-e $\tilde g$, M-11 같은 주기 규칙과 유효성 검사(T-7), 6절 대체 창 처리, M-11(0.4 식의 $f$, $z/f$, $\delta^{grid}$, $\delta z_{1n}$, $\Delta z^{post,corr}$, $\Delta^{corr}$, $g^{corr}$), D-a 원시·보정·최종 등급, D-c 보정·원시 이중 등급, 표시("격자 위상 의존"·"대체 범위"·"절점 계단 수준"·"앵커 단일 표본 의존"), M-12, 7.2 $m_L$, 4.4 비교 꼴, 4.5 정수 주기. 토양 상수는 `02_params/scm_soil_sets.json`, $A$·$b_{poly}$는 YAML `pad_shapes`에서 읽는다(손으로 적지 않는다).
- 순서: postrun → 경로 2 실행(출력 sha 기록) → 경로 1 실행 → 대조(K-R).
- K-R 항목: 행 상태, 묶음 상태, M-1~M-12의 모든 수치, 7.2 $m_L$, 7.3 상수(경로 2가 하네스에서 따로 계산), 4.4 문턱마다 행별 분류 결과, 등급 D-a~D-h와 계산 행 목록.
- 값 대조 허용: 이산 항목(상태·등급·$b^\ast$·주기 번호·사건 수) 완전 일치, 실수 절대차 ≤ 1×10⁻⁹ m. **4.4 $\varepsilon_{th}$와 섞지 않는다.**
- 불일치면 그 항목이 들어가는 등급은 `UNDETERMINED`다. 도구를 결과에 맞춰 고치지 않는다. 원인이 정의 해석 차이면 개정판으로 정의를 고친 뒤 두 경로를 다시 돌리고 첫머리에 적는다.
- 경로 2 작성자는 경로 1의 코드·출력을 보지 않는다. 정렬은 이 규칙의 문장으로만 한다.

## 10. terramechanics 재검토와 감사

### 10.0 TR 재검토 답 칸 (U-2 (a), 메인 세션이 terramechanics-expert에 맡김)

2026-11-10 검토(0.3)는 격자 시험 결과(원시 차 RL +2.74 mm·FL −0.80 mm) 전이었다. 아래 칸을 모두 채우기 전에는 봉인하지 않는다. 답으로 문턱·식이 바뀌면 해당 절을 고치고 16절에 적는다(결과 전이어야 한다).

| # | 질문 | 관련 | 답(출처 유형) | 반영 |
|---|---|---|---|---|
| TR-1 | D-a 3 mm를 원시 침하로 재는 것이 격자 위상 몫($\lvert f-1\rvert z$, 절점 계단 후방 약 1.0 mm)과 가를 수 있는 크기인가. 원시·보정 보수 쪽(U-3 (b))이 맞는가 | T-1, 3.3 D-a | **3 mm 유지.** +2.74 mm는 절대 침하 차이고 증분 격자 차는 RL +0.347 mm다. $f$ 일정이면 격자 몫은 전방 예산 다리(≤ 15 mm)에서 ≤ 0.75 mm, 후방 60 mm에서 ≤ 2.5 mm라 문턱이 그 위다. 원시로 가를 수 없는 경우는 후방 $\Delta z^{post}$ ≳ 60 mm, 또는 $N_h$가 후방 ≥ 3·전방 ≥ 7절점 바뀔 때다. 보수 쪽 등급에 찬성, 조건 (가)(나)(다)(유도식 + 격자 시험 + 저장 결과 재구성, 확신 중) | D-a 이유 문장 교체(반영), "TR-1 답 뒤 확정" 표시 지움(반영), 조건은 C-5(사용자 결정 2026-11-11, 반영) |
| TR-2 | D-b 5 mm: 점성 지연 $\tau$ ≈ 0.4~0.5 s 동안의 침하가 $\delta^{os}$와 $\Delta z^{post}$ 중 어디로 들어가는가. $t_{\max}$ 정의가 맞는가 | T-2, M-5 | **5 mm 유지.** $\tau$ 0.46~0.59 s(Chrono 소스 식, R은 탄성 가지 유도값)라 LOC 때 남은 지연은 1.4~1.8 s 안에 풀려 전부 $\Delta z^{post}$로 들어간다. 정의 빈틈: $t_{\max} < t_R$이면 $z(t_R) - z(t_{\max})$(저장 2.3~4.6 mm)가 어느 항에도 없다. 권고 (A) $t_e = \max(t_{\max}, t_R)$. $\kappa$ 적합은 다리별 창(확신 높음) | C-1(사용자 결정 2026-11-11, 반영) |
| TR-3 | D-d 10 mm와 패드 종류별 선형 $\kappa_z$: $n$ = 0.2에서 접선 유연도 ∝ $F^4$이면 ×1.0 안의 다리별 하중 차에서도 선형 상수가 10 mm 안에 들 수 있는가 | T-4, 7.3 | **10 mm 유지.** 선형 $\kappa$는 구조적으로 약하다(최대값 $\kappa$이면 하중 10 % 낮은 다리 34 % 과대, $\hat W/F$ 0.2이면 할선/접선 1.49). FL 예산 다리는 10 mm 안 가능, C5 RL은 어렵다. 거듭제곱 후보 P-D·다리별 창·κ 비 기록 권고(유도식, 확신 중) | C-2(사용자 결정 2026-11-11, 반영) |
| TR-4 | D-e 20 mm: 명목 세트 가드 여유 20 mm를 "B1 재확인"으로 읽어도 되는가 | T-5, 14.1 | **20 mm 유지**, SCM 명목 세트 안의 문장으로만 읽는다. $k_{eq}$ −4 %이면 침하 +22~30 mm. `NEED-RECHECK`에 격자 위상 하단까지 넣은 보수 조건 권고(유도값, 확신 높음) | D-e 해석 문장(반영), 보수 조건 C-3(사용자 결정 2026-11-11, 반영) |
| TR-5 | D-g +5 mm: ×1.1 침하 1.61배에서 고정 +5 mm가 적절한가, 비례 꼴이 나은가 | T-6, P-9 | **고정 +5 mm 유지.** $E_{q^\ast}$ ≤ 10 mm에서 비례 꼴과 차 ≤ 1.1 mm, $E$ < 8.2 mm에서 고정이 더 엄격, 비례 꼴은 $n$을 규칙에 넣음. 비 $\lvert e(\mathrm{C6})\rvert/E_{q^\ast}$ 기록 권고(확신 높음) | D-g 문장·기록(반영) |
| TR-6 | 경사 2.8° J2에서 패드 기울기·미끄럼으로 $f$가 실행 중 바뀌는 크기. T-7(1.0 s·$N_h$ ≥ 3)이 충분한가 | T-7, M-4h | **수정 필요.** 정적 위상 범위는 레벨링 실행의 $f$를 덮지 못한다(저장 J1 경사 $\Delta f$ 최대 0.106·15절점, 128기록 중 8개 범위 밖). 1.0 s 간격은 길다. 같은 10 Hz 주기 기록(또는 LOC~$t_{\max}$ + 2 s 창), $N_h \ge 3$ 대신 유효성 검사(저장 결과 재구성 + 유도식, 확신 중~높음) | C-4(사용자 결정 2026-11-11, 반영) |
| TR-7 | 크리프 정지 기준(1.0 s 창 < 0.1 mm/s)이 점성 모형에서 정착을 뜻하는가 | T-12, P-2 | **유지, 해석 문장 고정.** SCM 안에서는 패드 하중 정지(후방 ≤ 11 N/s)와 점성 지연 소멸(남은 지연 ≤ 23 µm)을 뜻한다. 실토양 압밀·2차 압축의 끝은 뜻하지 않는다. 절점 변화가 정지 시각을 늦출 수 있다(Chrono 소스, 확신 높음 SCM 한정) | 14.1·8절 P-2 해석 문장(반영) |
| TR-8 | $Z_{soil}$(실토양 크리프 허용). 등급에는 안 쓰고 B1 설계 문서에서 쓴다 | 3.3 D-a 효과 | **가정.** 레벨링 창(약 60 s) 압밀 [추정] 0.05~1.6 mm, 1 h 0.4~12 mm. 비배수 크리프 상한 없음. 후보 Z0 0 mm / Z1 2 mm / Z2 $0.1\,z_{b^\ast}(t_R)$(약 10~13 mm) / Zf 현장 평판 유지 시험값. 현장 시험 필요(근거 약함, 확신 낮음) | D-a 효과 칸 가정 표기(반영) |

- 답 원문: `06_analysis/02_control/b1/b1_tr_review_draft.md`(terramechanics-expert, 2026-11-11, sha256 `0ae7ddfc514eedc876440930742b84a609252abf2411bf65433f7556742a211f`, 봉인 커밋에 함께 넣음).
- TR-1~TR-8 답은 모두 채웠다. 봉인을 막는 것은 3.3.1 C-1~C-5 사용자 확인뿐이다.

### 10.1 세 시점 감사

| 시점 | 감사 범위 | 차단 조건 |
|---|---|---|
| 실행 전 | S(봉인 sha, 10.0 TR-1~7 칸 채움, `.gitattributes -text`, 격자 시험 봉인 sha·`PASS`), E(3.2 빈 집합 규칙이 도구에 있음), I(4.1 항목을 prelaunch가 기록, 6절 격자 기록 켬·끔 비트 동일, I-17 덤프 비교, 2.3 건조 실행 기록), R(경로 1 정의가 5·7절·M-11·M-12·4.4·4.5와 같음, 2.4 겹침 표 칸 확인), T(봉인 → 구현 → 경로 2 sha → 하네스 → 상수 → 건조 실행 → prelaunch 순서) | 하나라도 차단 → 실행하지 않음 |
| 판정 후 | C(K-R), E(등급별 행 수), I(V-2 결과), T(경로 2 출력 sha가 경로 1 실행보다 앞섬) | 차단 → 판정서 커밋 보류 |
| 전환 후 | 이 판의 태그(1.1)가 실행 때 프리셋 태그와 같은지, 래퍼·프리셋 이중 적용 없음, 접미사로 대상을 고르는 곳 없음 | 차단 → 개정판 |

- 전환 후 감사는 프리셋 전환이 없으므로(1.2) 봉인 직전에 한 번 한다.
- 감사는 verif-protocol-auditor가 하고, 도구는 `tools/verif` seal_check·gate_scan·record_check·timeline·log_errors·placeholder_scan이다.

## 11. 결과물

- `07_results/S9/batch_V5-B1-CREEP_<stamp>/`(Chrono 6행), 건조 실행 `07_results/S9/batch_V5-B1-CREEP-GS_<stamp>/`(키 목록만 남김)
- 하네스 출력 `06_analysis/03_hydraulic/coupled/v5/b1/b1_H.jsonl` + npz(그림자 켬 28, 끈 짝 4)
- `b1_harness_constants.json`, `B1_prelaunch.json`(배치 폴더에 채움, 판정 뒤 `06_analysis/02_control/b1/prelaunch/`에 사본 커밋)
- `b1_metrics_path1.json` / `b1_metrics_path2.json`
- 판정서 `06_analysis/02_control/b1/b1_creep_basis_judgement.md`: 등급표, 행 상태, 예측 대조, `SAFETY_NOTE`, 건조 실행 공개, D-e·D-f에 따른 사용자 질문

## 12. 비용·순서 (가정)

| 항목 | 벽시계 | 근거 |
|---|---|---|
| Chrono C1~C5 | 행당 7,000~10,000 s(P, threads 4, fast) | REM 상단 6,500 s × 160/120 외삽, 경사 ±15 %. 패드 0.01 m 저장 행 외삽이라 2.1 격자와 맞음 |
| Chrono C6 | 9,000~12,500 s | 같음 |
| 격자 기록 | ≤ +5 % | T-10 |
| E 풀 | × 1.5 | SCM 실측 |
| 6행 | P 4 + 2(두 물결) 약 4.5~6.3 h | 풀은 Q4 |
| G-S 건조 실행 | Chrono 2행 약 10~20 분 병렬, 하네스 수 분 | 가정 |
| 하네스 28 + 짝 4 | E 4~8 워커 약 15~25 분 | H-SH 줄당 1.2~4 분 |
| 재집계 | 각 수 분 | — |

- P코어 순서: P5r4+K1 Chrono 재실행 → 이 6행(1.3) → 436.8. D8x Chrono 19행은 B-G1 미달로 실행하지 않았다. 배치는 compute-scheduler-expert.

## 13. 남은 확인

| # | 상태(2026-11-11) | 누가 |
|---|---|---|
| R-1 파라미터 | **닫힘**(1.1·1.2). 실행 시점만 N-1 | — |
| R-2 `--start-limit`·지형 크기·M-4h 필드 | `record_only`로 정함, 구현 확인 열림 | cad-expert |
| R-3 7.1 기하 부호 | **닫힘**(dynamics-expert 확인, 사용자 결정 2026-11-12, 7.1) | — |
| R-4 하네스 질량 배율 | 열림(`run_v5.py`에서 `mass_scale` 못 찾음, grep) | python-expert |
| R-5 $Z_{soil}$ | TR-8 | terramechanics-expert |
| R-6 문턱 | 다시 엶(10.0 TR-1~TR-7) | terramechanics-expert |
| R-7 격자·제어기 기록 R-G1~R-G4·R-C1 | 진행. R-G1 다섯 필드는 `f1efed7`부터 `s9_rows[].pad_nodes`(10 Hz)에 있다(2026-11-11 grep은 이름을 놓쳤다). `--b1-grid-record full`과 `b1_grid_record.npz`(R-G1 8필드·R-G2·R-G3·R-G4) 구현 중, R-C1 키 추가 필요. 켬·끔 비트 동일·비 0.996 측정됨 | cad-expert |
| R-8 경로 1 도구 | 열림(9절 구현 요구) | python-expert |
| R-9 격자 시험 | 닫힘(`PASS`) | — |
| R-10 하네스 연속 Bekker($f \equiv 1$) | 열림(`04_scripts/03_control/s9/s9_soil_closed_loop.py:144-146` 식, v5 `run_v5.py d1`이 같은 클래스를 쓰는지) | python-expert |
| R-11 저장 경계 행 위상 재구성 | 닫힘(`evidence/grid_phase/`) | — |
| R-13 H-M0 연구 하위 클래스, 하네스 그림자 연결 | 열림 | python-expert |
| R-14 I-17 설정 덤프 비교 도구 | 열림 | python-expert |

## 14. 가정

- 원본에 없어서 정한 값: `--duration` 160 s(C6 180 s), 비용, 8절 예측 범위, 3.3 문턱(3 / 5 / 10 / 20 / +5 mm, TR 재검토로 유지), 7.4 SGS 하한 처리, 5절 침하 창 끝($t_e = \max(t_{\max}, t_R)$, C-1), M-11 유효성 검사 범위 [0.95, 1.05]·법칙 잔차 0.005(terramechanics TR-6 제안값), P-D 지수 $n_a$ = 0.2, κ 비 표시 1.5, C-3의 $f_{\max}$·$f_{\min}$로 0.01 m 위상 범위를 쓰는 것, 6절 대체 창 폭(−1 s, +2 s, READY 앞뒤 1 s), D-c 대체 범위의 $f_{min}$·$f_{max}$로 0.4 표 0.01 m 행을 쓰는 것, 3.4 영향 크기, 격자 기록 비용 한계 5 %, $\varepsilon_{th}$ = 1×10⁻⁹ m, T-8 연속 100표본, T-9 1×10⁻⁶ N, T-13 5 mm, T-14 5×10⁻⁴ m, 건조 실행 10 s·꼴 2개, I-17 기준 커밋 `e67dae8`.
- 압력 `normal`·IMU `ideal`은 판정 실행 관례다. 하네스 $f \equiv 1$은 R-10 확인 전 가정이다.
- 0.4의 $f$ 식은 정적 Bekker 처녀 분기다. 점성 지연·탄성 재하·접촉 절점 가장자리의 부분 σ는 넣지 않았다(P1 V16bp 0.05 % 일치가 근거).
- 안 A 반창 $w = \min(0.5, t_L - t_P)$ s는 `loc_anchor_shadow.py` `MAX_HALF_WINDOW_S`와 같다(코드 읽기). 경로 2는 이 문장에서 다시 구현한다.

### 14.1 모형 범위 (terramechanics 검토, 0.3)

- SCM 패드 침하는 지나간 최대 하중의 Bekker 침하와 점성 지연으로 정해진다. 압밀·2차 압축 같은 시간 의존 크리프와 전단 유발 침하는 없다. $\Delta z^{post}$와 D-a는 이 모형 안의 양이고, 실토양 몫 $Z_{soil}$은 B1 설계 문서에서 따로 더한다.
- 크리프 정지 시각(1.0 s 창 < 0.1 mm/s)은 SCM에서 패드 하중 정지(후방 ≤ 11 N/s)와 점성 지연 소멸(남은 지연 ≤ 23 µm)을 뜻한다. 실토양 압밀·2차 압축의 끝을 뜻하지 않는다. 격자 절점 변화가 정지 시각을 늦출 수 있다(TR-7).
- $Z_{soil}$은 가정이다(TR-8 후보 Z0/Z1/Z2/Zf, 10.0). 근거가 될 현장 평판 유지 시험(운용 접지압 1.1~1.2 MPa까지 단계 하중, 단계마다 ≥ 10 min 유지, 판 폭 2개 이상, 침하-시간 곡선)은 사용자 조치다.
- 점성 지연 $\tau$에 쓴 $R$(1.103×10⁶ Pa·s/m)은 탄성 가지 ζ 0.2에서 정한 유도값이고, 소성 가지 지연에 그대로 쓴 것은 모형 그대로의 계산이다.
- D-e 가드 여유는 SCM 명목 세트 값이다. J2 침하는 $k_{eq}$ 4 %, $n$ 0.02 차로 20 mm 이상 바뀌므로 실토양 여유로 읽지 않는다. $p/q_{ult}$ 약 0.82~0.87이라 Bekker 침하는 하한이다.

## 15. 남은 결정

| # | 결정 | 선택지 | 권고 |
|---|---|---|---|
| N-1 | 실행 시점(Q5 (가) 변경) | **정함: (a)**(사용자 결정 2026-11-11). 1.3 | — |
| C-1~C-5 | 판정 정의 변경(terramechanics 재검토) | **정함: 모두 채택**(사용자 결정 2026-11-11). 3.3.1 | — |
| R-3 | 7.1 기하·자세 입력·P-G | **정함**(사용자 결정 2026-11-12, dynamics-expert 확인) | — |

**사용자 결정 2026-11-12(경로 1 구현 피드백·R-3 반영): Q-1~Q-7 모두 (a), Q-8 (a) dynamics-expert R-3 원문 식으로 확정(7.2). 남은 사용자 결정은 없다.**

| # | 내용 | 선택지 | 정함 | 위치 |
|---|---|---|---|---|
| Q-1 | $\hat W_i$ 출처 | (a) YAML `static_leg_loads_N`(행의 오거 단계, 명목 질량) − LOC 주기 `PressureForces.nominal` / (b) 정적 분배를 실행 시작 정착 하중으로 | **(a)**. 두 경로가 같은 출처를 읽고, 제어기도 명목 질량을 쓴다(C6 × 1.1 안 함) | 7.2 |
| Q-2 | 하네스 비교 다리·실행 | (a) 하네스 양은 짝 Chrono 행 $b^\ast$ 다리 값, $Z_{hn}$은 H-P VB·V0 e0 최대, D-b 하네스 $\delta^{os}$는 H-P VB e0만 / (b) 하네스 자신의 $b^\ast$ | **(a)**. 같은 다리끼리 비교해야 D-a·D-b·D-c가 같은 양이다 | 3.3 D-a·D-b |
| Q-3 | C-5 (다) 기록 시각 | (a) $z(t_e)(f(t_e) - f(t_L))$로 통일, $t_{\max}$ 값은 참고 / (b) $t_{\max}$ | **(a)**. C-1 창 끝과 같아야 D-a 보정값과 같은 시각이다 | 3.3 D-a, 3.3.1 C-5 |
| Q-4 | D-f 짝 1개 경우 | (a) 남은 짝이 SGS면 `FUP-OUT`, READY면 `FUP-IN`, 둘 다 "짝 1개" / (b) 남은 짝이 SGS면 `FUP-OUT` + "짝 1개", 아니면 `NA`(경로 1 제안) | **(a)**. 원 규칙 `FUP-IN`이 "짝 중 하나라도 READY"라 남은 짝 READY면 이미 성립한다. (b)는 더 보수적 | 3.3 D-f |
| Q-5 | D-d 행 제외·후보 `NA` | (a) T-14 어긋난 행은 모든 후보에서 빼고, 남은 행 중 하나라도 `NA`인 후보는 $E_q$ `NA` / (b) 후보마다 쓸 수 있는 행으로 $E_q$(행 수 병기) | **(a)**. 후보끼리 같은 행 집합으로 비교한다 | 3.3 D-d |
| Q-6 | 하네스 V-4 유효 조건 | (a) 오류 없음·태그 일치·npz sha 일치, 끝 시각 조건 없음 / (b) (a) + 하네스 끝 시각 ≥ 설정 끝 − 0.1 s | **(a)**. 하네스는 결정적이고 끝 시각 조건의 Chrono 뜻(중단 감지)이 없다 | 3.1 V-4 |
| Q-7 | Chrono M-12 방법 | (a) R-G4 `imu_*`로 두 경로가 따로 사후 재구성 / (b) Chrono 러너에 기록 전용 `loc_anchor_shadow` + 켬·끔 짝 해시 / (c) `NA` | **(a)**. 러너를 바꾸지 않고, 두 경로가 python-expert 그림자 코드 출력을 같이 읽지 않아 독립이다. R-G4가 없으면 (c) | 7.5 |
| Q-8 | P-G의 $\rho_k$·$\hat Z_k$ 부호 규약 | (a) dynamics-expert R-3 보고 원문 식과 대조해 확정(이 판의 문장을 그 식으로 고침) / (b) 이 판의 문장 그대로 | **(a)**. 메인 세션 요약에서 옮긴 식이라 두 경로가 다르게 읽을 수 있다 | 7.2 |

## 16. 변경 기록 (봉인 전)

- 2026-11-10: 후보판 작성(초안 `8b390d9` 대비 C6·정식 봉인·H-M0·등급화·D-g·D-h·파라미터 절·SGS 하한), terramechanics 검토 반영, 격자 개정(0.02 → 0.01 m, D-c 보정 등급, 0.4·3.4·M-11·5.1), D-c 대체 범위 분류 변경, 격자 시험 결과 반영, 판정서 인용 sha 갱신. 자세한 문장은 후보판 14절(`7c782632…`).
- 2026-11-11 초안 v2(`bf88cc65…`): 제어기 갈래, 태그 규칙, 겹침 표, G-S 건조 실행, $m_L$ 두 사건, H-M0 꼴, M-12, 문턱 비교 꼴, 정수 주기, 정체성 I-10~I-16, TR 항목, 순서.
- 2026-11-11 이 판(합친 원판 후보, 결과 전). 사용자 결정 U-1~U-7과 사전 결정(P5r4 '통과'여도 전환 없음)을 반영했다.
  - 후보판 1절의 미정 값 칸을 없앴다: 태그·프리셋·`P7_REF`(전체 sha)·`HULL_DLL_SHA`(전체)·`START_LIMIT`를 값으로, `HEAD_M`·하네스 커밋·풀을 정의로 바꿨다(1.1). 판단 근거 1.2, 위험 CR-1~CR-3, I-17 추가.
  - D-a 최종 등급을 원시·보정 보수 쪽으로 바꿨다(U-3 (b), TR-1 답 뒤 확정 표시).
  - 하네스에 H-SH0 짝 4개를 더해 32실행이 됐다(U-7 (a)). 6절에 R-G4(IMU 원시 기울기)를 더했다(M-12 재구성).
  - 10.0 TR 답 칸을 두고, TR-1~TR-7이 비어 있으면 봉인하지 않게 했다.
  - 절 번호를 다시 매겼다(후보판 5.1 → 6, 6 → 7, 7 → 8, 8 → 9, 9 → 10.1, 12 → 13, 13 → 14).
  - B1 Chrono·하네스·건조 실행 결과와 P5r4+K1 결과는 보지 않았다.
- 2026-11-11 같은 판 갱신(결과 전, control-expert). 사용자 결정 N-1 (a)와 terramechanics 재검토 `b1_tr_review_draft.md`를 반영했다. B1 결과와 P5r4+K1 결과는 보지 않았다.
  - 바로 반영(정의 불변): 1.3 실행 시점(N-1 (a), 봉인 커밋은 P5r4 Chrono postrun 뒤), 0.4 격자 시험 근거 문장(절대 +2.74 mm / 증분 +0.347 mm), 3.3 D-a 이유 문장 교체와 "TR-1 답 뒤 확정" 표시 제거, D-a 효과 칸 $Z_{soil}$ 가정 표기(Z0/Z1/Z2/Zf), D-e 해석 문장, D-g 고정 +5 mm 근거와 비 기록, 8절 P-2 해석과 P-14~P-17(terramechanics 사전 예측), 10.0 TR-1~TR-8 답 칸, 14.1 TR-7 해석·TR-8 가정·R 출처.
  - 결과 전 정의 변경 C-1~C-5를 제안했다(3.3.1). 문턱 숫자(3 / 5 / 10 / 20 / +5 mm)는 바꾸지 않았다.
- 2026-11-11 같은 판 갱신 2(결과 전, control-expert). **사용자 결정 2026-11-11: C-1~C-5 모두 채택**, 격자 기록 주기는 실행 전체 10 Hz(비용 > 5 %면 창 기록으로 바꾸는 대체 조항, 판단은 결과 전 비용 측정). B1 결과와 P5r4+K1 결과는 보지 않았다.
  - C-1: 침하 창 끝 $t_e = \max(t_{\max}, t_R)$를 0.1 기호표, 3.3 D-a, M-4, M-11에 넣었다. $z(t_{\max}) - z(t_L)$은 기록으로 남겼다.
  - C-2: 후보 P-D(7.2 표·기호표), $C_{type}$·다리별 창 $t_{e,i}$·κ 비 기록(7.3), D-d 후보 집합과 동점 순서(P-A → P-B → P-D → P-C), E-2를 고쳤다.
  - C-3: D-e `NEED-RECHECK`를 $\tilde g_r$로 바꾸고 T-5를 고쳤다.
  - C-4: M-11을 같은 주기 기록 + 유효성 검사(i)(ii)로, T-7을 그 비교 꼴로, R-G1을 실행 전체 10 Hz + 대체 조항으로 바꿨다. $N_h \ge 3$과 "간격 1.0 s" 규칙은 지웠다.
  - C-5: D-a 보정 계산 조건 (가)(나)(다)를 넣었다(대체 범위 안 씀, 원시 초과량 보정, $z(t_e)(f(t_e) - f(t_L))$ 기록).
  - 3.3.1 머리를 "사용자 결정 2026-11-11"로 바꾸고, 15절 남은 결정을 "없음"으로 했다. 9절 구현 요구에 위 항목을 더했다.
- 2026-11-12 같은 판 갱신 3(결과 전, control-expert). B1 결과와 P5r4+K1 결과는 보지 않았다.
  - **사용자 결정(R-3, dynamics-expert 확인)**: 7.1 문구를 "기체 원점 고정·자세만 0, 네 다리 평균을 뺀 꼴 아님"으로 바꾸고, 다리 위치 출처를 `legs.<leg>.pad_bottom_center_retracted_m[0:2]`로 정했다. **자세 입력을 필터 자세에서 $t_L$ 주기 평균 원시 기울기로 바꿨다(정의 변경).** R-3 근거 문장을 넣고 R-3을 닫았다. **후보 P-G를 추가**했다(7.2). D-d 후보 집합과 동점 순서는 P-A → P-B → P-D → P-G → P-C이고, E-2를 고쳤다. P-A 한계 문장과 기록 항목($h$, $\rho_{k^\ast}$, $\hat Z_{k^\ast}$, $\varepsilon$)을 넣었다.
  - **cad-expert 피드백**: R-G1 다섯 필드가 `f1efed7`부터 `s9_rows[].pad_nodes`에 있음(13절 R-7 정정), T-10 "끔" 정의, 비용 측정(비트 동일, 0.996)으로 `full` 확정, 2.1 공통 조건에 `--b1-grid-record full`, 대체 조항의 온라인 근사 문장(적용 안 함), 기록 파일 `b1_grid_record.npz`.
  - **제어기 주기 기록 R-C1**(`n`, `load_read_N`, `att_raw_rad`, `c_hat_m`, `c_hat_corner_m`, `c_target_m`)을 6절에 넣었다. T-14 대조 출처를 `c_target_m`로 바꿨다.
  - **경로 1 피드백 12항**: 바로 반영한 것은 ⑤ PARTIAL 표시 범위, ⑦ V-3 `REJ_`, ⑧ T-8·T-9 시각과 $W$, ⑨ κ 비의 실행 κ, ⑩ `P7_REF` 줄 선택이다. 사용자 확인 대기로 둔 것은 ① Q-1, ② Q-2, ③ Q-3, ④ Q-4, ⑥ Q-5, ⑪ Q-6, ⑫ Q-7이고, R-3 식 부호는 Q-8이다(15절).
- 2026-11-12 같은 판 갱신 4(결과 전, control-expert). **사용자 결정 2026-11-12: Q-1~Q-7 모두 (a), Q-8은 dynamics-expert R-3 보고 원문 식으로 확정.** 본문의 "사용자 확인 대기" 표시를 결정 표시로 바꿨다. 7.2에 지지 행렬 $A_i = [1, y_i, -x_i]$, `predicted_strokes_m`(`c2.py:3226-3248`) 부호, 모서리 heave 꼴, 운동학 항등식, $Z_k$·$\hat Z_k$ 평면, 관측 $h$, $\varepsilon$, $(\cdot)^+$ 절단 한계, 저장 X4-nd/X4-ed 근거(−4.7 mm ≈ $\varepsilon$ 4.6/4.7 mm)를 넣었다. 15절 남은 결정은 없다. B1 결과와 P5r4+K1 결과는 보지 않았다.

## 17. 알려진 한계

- 대상 제어기는 v5 `final_C4G2_LAS_K1`(VB `final_C4G2_P3_LAS_K1`)이다. v5 뒤 다른 후보(P5r4 등)가 채택돼 E3c10, R4c30, K1 순서 관문, LOC 취소, SGS, DSb75, LAS-b 가운데 하나의 동작이 바뀌면 이 근거는 그 제어기에 그대로 쓰지 않고 다시 낸다(1.2 CR-2).
- LOC 앵커 단일 표본 결함은 고치지 않은 제어기 그대로다(사용자 결정 11-11, 수정은 v5 뒤). M-12는 크기만 기록한다.
