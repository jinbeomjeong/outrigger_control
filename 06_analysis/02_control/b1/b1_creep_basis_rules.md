# B1 크리프 근거 — Chrono SCM 경사 J2 봉인 후보판 규칙 (`V5-B1-CREEP`)

- 작성: control-expert, 2026-11-10
- 상태: **봉인 후보판. 아직 봉인하지 않았다(`.sha256` 없음).**
  - 봉인 시점: P5r4+K1 판정·채택 결정으로 1절 파라미터가 정해진 뒤다. 파라미터 값을 채운 판을 봉인한다.
  - 파라미터 칸을 채우는 것 말고 바꾸는 것이 있으면 봉인 전이라도 바꾼 곳을 14절 변경 기록에 적는다.
  - 봉인 뒤 바꾸려면 개정판(rev1 …)을 만들고, 결과를 보기 전인지 본 뒤인지를 첫머리에 적는다.
- **2026-11-10 격자 개정(결과 전)**: 2.1절 격자를 0.01 m로 바로잡고, D-c를 격자 인자 보정값으로 등급을 내게 바꿨다(0.4절, 14절). B1 Chrono·하네스 결과와 격자 시험 `b1_gridconv_plan.md` 결과는 아무것도 보기 전이다.
- 봉인 전제 추가: 격자 시험 `b1_gridconv_plan.md`(봉인판)가 `PASS`여야 이 판을 봉인한다(3.0, 9절).
- 앞선 초안: `b1_creep_basis_plan_draft.md`(커밋 `8b390d9`). 이 판이 초안을 대신한다. 초안 2절(봉인 전에 본 자료)은 이 판 0.2절로 그대로 옮겼다.
- 사용자 결정(2026-11-10, 초안 10절)
  - Q1 (다): C1~C5 5행 + ×1.1 C1, 모두 6행
  - Q2 (나): 정식 봉인 + 세 시점 감사
  - Q3: C1m0(Chrono $m$ = 0)은 넣지 않는다. 하네스 $m$ = 0 짝으로 대신한다
  - Q4: 다섯·여섯째 행의 풀은 스케줄러가 정한다
  - Q5 (가): P5r4+K1 판정·채택 결정 뒤에 실행한다
  - Q6: J2 경사 운용 권고 여부는 D-e·D-f 결과를 보고 다시 묻는다
- 성격: **B1 설계 입력을 정하는 등급 판정**이다. 제어기 합격·불합격 판정이 아니다. P3 행·SGS 분류는 기록만 한다(관문에 쓰지 않는다).
- 규약
  - 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1, C2 음되먹임이다($u$ = 행정 속도 명령 [m/s]).
  - **판독 행정** $s_i$: 제어기가 보는 모터 행정이다. Chrono는 `record.npz` `meas.stroke`(10 Hz), 하네스는 `max(plant.sref)`와 같은 양(10 Hz 표본)이다. 가드 $s_{guard}$ = 0.6828 m이고, 이 규칙의 모든 행정 비교는 판독 행정끼리 한다. 참 행정(P3-5)은 기록만 하고 섞지 않는다.
  - 침하 $z_i$: 패드 기하 침하(Chrono `step_series.npz` `pad_sinkage_geometric_m`, 1 ms, + = 깊어짐)다. 하네스는 같은 정의의 패드 요소 침하이고, 3.2절에 따라 저장한다.
  - 시각은 절대 시각 [s]이고, 길이는 표시할 때 mm다.

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
| $\Delta s^{geo}_i$ | LOC 때 정착 자세 $(\hat\phi,\hat\theta)$ → 목표 0으로 갈 때 다리 $i$ 행정 변화(소각 근사, 식과 부호는 6.1) | m |
| $c^\ast$ | 기본 틈 목표 `thresholds.clearance_target_m` = 0.05 m | m |
| $m$ | E3c10 여유(현행 0.03 m) | m |
| $\hat c(k_L)$ | LOC 주기 제어기 틈 추정 | m |
| $\Delta z_i^{post}$ | LOC 뒤 패드 $i$ 추가 침하 | m |
| $\delta_i^{os}$ | 판독 행정 최대 − 첫 READY 때 판독 행정 | m |
| $\hat W_i$ | LOC 뒤 다리 $i$ 하중 증가 추정 = 레벨 정적 분배 하중 − LOC 주기 판독 하중 | N |

### 0.2 봉인 전에 본 자료 (공개)

- 하네스 P0 J2 경사 행정 여유(`v5/soil_defer/judge_S.json` `d10d6f18…c236f0d0`, `info.P0_margin.rows`)

| 키 | 판독 최대 [mm] | 가드 여유 [mm] | 결과 |
|---|---|---|---|
| `J2|B|fdown-rec` VB / V0 | 682.41 / 681.98 | 0.39 / 0.82 | SGS FL |
| `J2|M|fdown-rec` VB e0 / e0.002 | 669.47 / 682.61 | 13.33 / 0.19 | READY / SGS FL |
| `J2|T|fdown-rec` VB e0 | 671.15 | 11.65 | READY |
| `J2|B|diag-rec` V0·VB | 682.43 ~ 682.77 | 0.03 ~ 0.37 | SGS FR |

  `v5/d1.jsonl`(K1 전): `J2|{T,M,B}|fup-rec` 모든 설정 SGS RL.

- 저장 Chrono 7건의 LOC 뒤 침하·행정(`b1/evidence/post_loc_digest_stored.jsonl`, 도구 `post_loc_digest.py`, 초안 2.2 표 그대로). 이 자료로 정한 값은 다음 다섯 가지다.
  - 예측 범위(7절)
  - D-b 문턱 5 mm
  - D-c 문턱 3 mm
  - D-e 문턱 20 mm
  - 예측자 오차 문턱 10 mm
- 정리하면 다음과 같다.
  - READY 뒤 추가 침하는 ≤ 0.14 mm이고, 예외는 끝 재레벨 1건의 4.8 mm다.
  - J1 앞내림 앞 패드의 LOC 뒤 침하는 1.5~3.2 mm, 뒤 패드는 46~48 mm다.
  - $\delta^{os}$는 J1 앞내림 FL 24.2 mm, J1 대각 FR 7.0 mm, J2 평지 2.1~9.9 mm다.
  - 같은 양 Chrono − 하네스는 −0.25 mm(J1 앞내림), −2.0 / −5.4 mm(J2 평지)다.

### 0.3 terramechanics-expert 검토 요약 (2026-11-10, 결과 전, 공개)

검토 원문은 메인 세션이 전달한 요약이다. 이 판은 그 요약을 인용하며, 원문 리포트의 파라미터 표(출처 유형별)가 근거 원본이다.

| 항목 | 검토 값·내용 | 출처 유형 | 이 판에서 반영한 곳 |
|---|---|---|---|
| SCM 패드 침하 기구 | 지나간 최대 하중의 Bekker 침하 + 점성 지연 $\tau = R/(n\,p/z)$ ≈ 0.4~0.5 s(J2). 시간 의존 크리프(압밀·2차 압축)와 전단 유발 침하는 없다 | Chrono 소스(`SCMTerrain.cpp` `SCMLoader::ComputeInternalForces`: σ를 τ보다 먼저 정하고 되먹임 없음) | 13절 모형 범위 |
| J2 민감도 | $k_{eq}$ 4 %, $n$ 0.02 차로 침하가 20 mm 이상 바뀐다 | 세트 파라미터 감도(유도식) | 13절 D-e 해석 제한 |
| 지지력 이용률 | $p/q_{ult}$ 약 0.82~0.87. 파괴 근처라 Bekker 침하는 하한이다 | 유도식(지지력 계산) | 13절 |
| 격자 인자 $f$(2026-11-10 2차 검토) | SCM 패드 힘은 패드 다각형 안 접촉 절점 수 $N_h$ × $\Delta^2$에 σ가 걸리고, Bekker $b$는 접촉 절점 볼록 껍질의 $2A/P$다. 그래서 침하가 연속 Bekker 값의 $f$배가 된다(식은 0.4). J2, 격자 0.01 m의 위상 범위는 $f-1$ 후방 −1.3~+4.2 %, 전방 −2.8~+5.0 %다 | Chrono 소스(`SCMTerrain.cpp` 584-588, 1366-1377, 1475) + 유도식 + 절점 위상 스캔 | 0.4, 3.3 D-a·D-c, 3.4, 5.1 |
| 절점 하나 계단 | $\delta z_{1n} = z\,\Delta^2/(nA)$. J2, $\Delta$ 0.01 m에서 후방 0.82 %·$z$(약 1.0 mm), 전방 0.47 %·$z$(약 0.5 mm). **첫 후보판의 "앞 1.6·뒤 3.8 mm"는 0.02 m 값이라 폐기**했다 | 유도식(격자·패드 면적·$n$) | 3.3 D-c 표시 |
| 패드 접선 유연도 | 앞 3.6 / 뒤 7.9 mm/kN(2.2배) | 유도식(Bekker 접선) | 6.3 $\kappa_z$ 패드 종류별 |
| ×1.1 침하 배율 | 접선 유연도 ∝ $F^{1/n-1} = F^4$, ×1.1이면 $z$ 1.61배. 저장 REM 1.57~1.74 | 유도식 + 저장 Chrono(REM ×1.1 대 ×1.0) | 7절 P-9 |
| 시작 조건 | `--start-limit record_only` 권고(T-6) | 운용 판단 | 12절 R-2 |
| 문턱 | 3 / 5 / 10 / 20 / +5 mm 그대로(사용자 결정, R-6 닫힘) | — | 3.3 |

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
- $f$는 패드가 격자에 대해 어디 놓였는지(위상: xy 오프셋·요)에 따라 바뀐다. 패드가 기울거나 미끄러지면 실행 중에도 바뀐다.
- 위상 범위($f - 1$, J2, terramechanics 스캔 `evidence/gridconv_scan/phase_band.txt`)

| 격자 $\Delta$ [m] | 후방 250 | 전방 330 | 절점 하나 계단 $\Delta^2/(nA)$ 후방 / 전방 |
|---|---|---|---|
| 0.02 | −22 ~ +29 % | −8 ~ +12 % | 3.3 % / 1.9 % |
| 0.01 | −1.3 ~ +4.2 % | −2.8 ~ +5.0 % | 0.82 % / 0.47 % |
| 0.005 | −0.8 ~ +1.6 % | −0.5 ~ +1.3 % | 0.21 % / 0.12 % |

- 봉인 전에 본 Chrono 자료: P1 `V16bp_J2_B_RL_{2cm,1cm}`(2026-10-26, 단일 패드 RL 72.81 kN, `07_results/S9/batch_P1_V16_20261026_032113/`). 침하 2 cm 95.27 mm, 1 cm 118.60 mm이고, 각 격자의 이산 기준 $f\,z_{cont}$(95.27 / 118.65 mm)와 0.05 % 안에서 맞았다(`evidence/gridconv_scan/p1_levels.txt`). 이 자료가 0.02 m를 버린 근거다.
- 저장 J1·J2 Chrono 레벨링 결과는 모두 패드 0.01 m(U-S9G-1, `run_S9.py` `P3B_PAD_GRID_M`)다. 0.02 m는 G1·S1과 P1·P2 시험 행에만 썼다(`evidence/gridconv_scan/grid_census.txt`). 0.2절 저장 Chrono 7건과 11절 비용 추정도 0.01 m 값이다.
- 0.01 대 0.005 수렴은 `b1_gridconv_plan.md`(봉인)로 확인한다. 그 결과가 `PASS`일 때만 이 판을 봉인한다.
- **GC PASS → 0.01 m 확정 근거(2026-11-10)**: 판정서 `b1_gridconv_judgement.md` sha256 `c0a847b24a6db40375d05e43d7b458d5767458501fb54d45e5a1464748b28bb1`. 계획 원판 `0e909bf1…` + rev1 `3f354eb7…`. 두 경로 `PASS`, 대조 127항목 불일치 0.
  - Chrono가 각 격자의 이산 Bekker 법칙을 따랐다. G-1 최대 3.1×10⁻⁶.
  - $z/f$가 격자와 무관했다. G-2 최대 1.1×10⁻⁴ mm, G-3 ≤ 1.0×10⁻⁶.
  - 원시 침하는 0.01 대 0.005 m에서 RL +2.74 mm, FL −0.80 mm 다르다. 이것이 D-c를 보정값 $\Delta^{corr}$로 등급 내는 이유다.
  - 범위: 위상 0 오프셋 한 점, 단일 패드, J2, 패드 B. 레벨링 행의 $N_h$ 변화는 M-11·5.1 기록으로 본다.
  - 봉인 전제 "격자 시험 `PASS`"(3.0·9절)는 충족됐다. 봉인 시점은 그대로 P5r4 결정 뒤다.

## 1. 파라미터 (P5r4+K1 결과로 정함, 봉인 전에 채움)

| 이름 | 정하는 규칙 | 채울 값 |
|---|---|---|
| `P5R4_OUTCOME` | P5r4+K1 판정서와 사용자 채택 결정 | `adopted` / `not_adopted` / **(미정)** |
| `CTRL_TAG_VB` | `not_adopted` → `final_C4G2_P3_LAS_K1`. `adopted` → 채택 전환이 정한 VB 태그 | **(미정)** |
| `CTRL_TAG_V0` | 같은 규칙, V0 태그(`final_C4G2_LAS_K1` 또는 전환 태그) | **(미정)** |
| `CTRL_PRESET_NOTE` | 프리셋이 바꾼 기본값 목록. `not_adopted`면 "K1 채택 프리셋 그대로" | **(미정)** |
| `HEAD_M` | 실행할 master 커밋. 파라미터를 반영한 판의 병합 뒤, 깨끗한 checkout이어야 한다 | **(미정)** |
| `P7_REF` | 예측 P-7(K1·P5r4가 이 키들의 명령을 바꾸는지)의 기준 명령 해시 집합. `not_adopted`면 `s2d_SC.jsonl`(`70e91ec1…c6cb08aa`) P0 `commands_sha256`. `adopted`면 "기준 없음, P-7 기록 생략" | **(미정)** |
| `HULL_DLL_SHA` | `hull_hook.VALIDATED_DLL_SHA256`(현행 `cec997d7…`) | 봉인 때 전체 값 |

- `P5R4_OUTCOME`이 `adopted`이고 전환이 E3c10·LOC 취소·SGS·DSb75 가운데 하나의 기본값을 바꾸면, 이 판은 그대로 봉인하지 않는다. 0.2 자료와 7절 예측을 새 제어기로 다시 보고 개정한 뒤 봉인한다(그 사실을 첫머리에 적는다).
- 파라미터를 채운 뒤 바꾸는 것은 개정이다.

## 2. 실행 단위

### 2.1 Chrono 6행 (`run_S9.py level`, 묶음 `V5-B1-CREEP`)

- 공통 조건
  - `--soil J2`(균일), `--pad-variant dwg_rear250`(패드 B), `--fs-kN 4`
  - VB 설정 `s9_batch.v5_vb_argv()`, `--expect-controller {CTRL_TAG_VB}`, 시드 P3b 기본
  - 압력 `normal`, IMU `ideal`, 격자 `--grid 0.01 --crawler-grid 0.04`(U-S9G-1 M14s 이중 터레인. 첫 후보판의 `--grid 0.02`는 오기라 결과 전에 고쳤다, 14절), `--settle-dashpot zrp`, `--threads 4`

| ID | 사례 이름 | 오거 | `--floor-roll` / `--floor-pitch` [°] | 질량 | `--duration` [s] | 예산 다리 | 역할 |
|---|---|---|---|---|---|---|---|
| C1 | `B1_J2_B_bottom_Fs4_VB_fdown` | bottom | 0 / 2.8 | 1.0 | 160 | FL | 핵심 |
| C2 | `B1_J2_B_middle_Fs4_VB_fdown` | middle | 0 / 2.8 | 1.0 | 160 | FL | 핵심 |
| C3 | `B1_J2_B_top_Fs4_VB_fdown` | top | 0 / 2.8 | 1.0 | 160 | FL | 보조 |
| C4 | `B1_J2_B_bottom_Fs4_VB_diag` | bottom | 1.925 / 1.4 | 1.0 | 160 | FR | 핵심 |
| C5 | `B1_J2_B_top_Fs4_VB_fup` | top | 0 / −2.8 | 1.0 | 160 | RL | 핵심 |
| C6 | `B1_J2_B_bottom_Fs4_m1p1_VB_fdown` | bottom | 0 / 2.8 | `--mass-scale 1.1` | 180 | FL | 감도(×1.1) |

- **예산 다리 $b$**
  - 위 표의 다리가 미리 정한 예산 다리다.
  - 실행 결과 판독 최대가 다른 다리에서 나오면, 그 다리를 실제 예산 다리 $b^\ast$로 기록한다.
  - 모든 지표는 $b$와 $b^\ast$ 둘 다 낸다. 등급에는 $b^\ast$를 쓴다.
- C6의 180 s 근거: J2 ×1.1 평지는 READY가 약 118 s이고, FINAL-REP는 180 s가 필요했다.
- `--start-limit`는 cad-expert가 정해 봉인 전에 채운다(값: **(미정)**). 그 값은 6행 모두 같아야 하고, `--expect-controller` 점검을 통과해야 한다(I-3).

### 2.2 하네스 짝 (E코어, `run_v5.py d1` 부분 집합, 태그 `{CTRL_TAG_VB}` / `{CTRL_TAG_V0}`)

| 묶음 | 내용 | 실행 수 |
|---|---|---|
| H-P | C1~C5 키 × {VB, V0} × e {0, 2e-3}, $m$ = 0.03 | 20 |
| H-W | C6: `J2|B|fdown-rec` ×1.1 × {VB, V0} × e {0, 2e-3} | 4 |
| H-M0 | C1·C5 키 × {VB, V0} × e 0, $m$ = 0(연구용 설정 교체, c2.py 불변) | 4 |

- 모두 28실행이다.
- 하네스가 질량 배율을 지원하지 않으면 H-W는 비고, C6은 D-c에서 빠진다(3절 V-4).
- 각 실행은 10 Hz 다리별 판독 행정·패드 침하·하중·자세·틈 추정·주기 기록을 npz로 남긴다(python-expert 구현).

## 3. 관문과 등급

### 3.0 처리 순서

```
GC 격자 시험(b1_gridconv_plan.md) PASS → S-0 봉인 → H 하네스 28 → K 상수 고정(6.3) → 실행 전 감사
  → prelaunch → Chrono 6 → postrun → 경로 2 → 경로 1 → K-R 대조 → 등급 → 판정서 → 판정 후 감사
```

- GC가 `REJECT`이면 이 판은 봉인하지 않고 분석한다(격자 시험 계획서 6절).

### 3.1 행 유효성 (각 Chrono 행)

| 코드 | 조건 | 실패 시 |
|---|---|---|
| V-1 | rc 0, `result.json`·`record/record.npz`·`step_series.npz` 존재, 끝 시각 ≥ `--duration` − 0.1 s 또는 SGS·FAULT로 끝난 정상 종료 | 1회 `--resume`(4.3). 다시 실패하면 `MISSING` |
| V-2 | 실행 정체성 I-1~I-9 모두 참(4절) | `INVALID`(다시 돌리지 않는다. 원인을 판정서에 적는다) |
| V-3 | 시작 거부(시작 조건) 없음. LOC가 1회 이상 있음 | 시작 거부면 `MISSING_START`(다시 돌리지 않는다). LOC가 없으면 `NO_LOC` |
| V-4 | 짝 하네스 VB e0 실행이 있고 V-1에 해당하는 조건을 만족 | 짝이 없으면 그 행의 D-c 값은 `NA`. 다른 등급은 낸다 |

- 행 상태는 `VALID` / `MISSING` / `MISSING_START` / `NO_LOC` / `INVALID` 가운데 하나다.

### 3.2 빈 집합 금지 (묶음 상태)

| 묶음 상태 | 조건 |
|---|---|
| `COMPLETE` | 6행 모두 `VALID` |
| `PARTIAL` | 핵심 4행(C1·C2·C4·C5) 모두 `VALID`, 보조·감도(C3·C6) 가운데 `VALID`가 아닌 행 ≥ 1 |
| `UNDETERMINED`(판정 불가) | 핵심 행 가운데 하나라도 `VALID`가 아님, 또는 하네스 H-P VB e0 짝 5개 가운데 하나라도 없음 |

- 등급(3.3)은 `COMPLETE`·`PARTIAL`에서만 낸다.
- 각 등급은 계산에 쓴 행 ID 목록과 행 수를 함께 적는다. 계산 대상 행이 0개인 등급은 통과로 세지 않고 `NA`다.
- `PARTIAL`에서는 빠진 행이 바꿀 수 있는 등급(C3: D-d, C6: D-g)에 `PARTIAL` 표시를 붙인다.

### 3.3 설계 입력 등급 (초안 D-a~D-f를 등급·관문으로)

$\mathcal{R}$ = 핵심 4행 + C3(VALID일 때) = ×1.0 행 집합이다. 행정·침하는 모두 실제 예산 다리 $b^\ast$ 값이다.

| 코드 | 양 | 등급 규칙 | B1 설계에서의 효과 |
|---|---|---|---|
| **D-a 크리프 허용** | $Z_{ch} = \max_{r\in\mathcal R} \Delta z^{post}_{b^\ast}(r)$(LOC 마지막 → $t_{\max}$), $Z_{hn}$ = 같은 양 하네스 H-P VB·V0 e0 최대 | `ZA-1`: $Z_{ch} \le Z_{hn} + 3$ mm / `ZA-2`: 그 밖 | 크리프 허용값 $Z_{B1} = \max(Z_{ch}, Z_{hn}) + Z_{soil}$. $Z_{soil}$은 terramechanics T-2 답이다. 답이 오기 전이면 B1 설계 문서에서 `Z_soil 미정`으로 막는다. `ZA-2`이면 B1 하네스 스윕의 침하 항을 Chrono 쪽으로 보정해야 한다. **격자 보정 기록**: 행마다 $\Delta z^{post,corr}_{b^\ast} = z_{b^\ast}(t_{\max})/f_{b^\ast}(t_{\max}) - z_{b^\ast}(t_L)/f_{b^\ast}(t_L)$(0.4, 5.1)을 함께 적고, $Z_{ch}$ 대신 그 최대 $Z^{corr}_{ch}$로 등급을 셌을 때 등급이 다르면 "격자 위상 의존"을 붙인다. **등급은 원시값 $Z_{ch}$로 낸다** |
| **D-b 과도 초과** | $O = \max_{r\in\mathcal R} \max(\delta^{os}_{b^\ast,ch}, \delta^{os}_{b^\ast,hn})$ | `OS-MAX`: $O$ > 5 mm / `OS-FINAL`: $O$ ≤ 5 mm | `OS-MAX`면 B1은 "예상 최대 행정"을 쓰고 허용값 $O$를 더한다. `OS-FINAL`이면 "예상 최종 행정"을 써도 된다. READY가 없는 행(SGS)은 $\delta^{os}$ = `NA`이고, 행 수에서 뺀 것을 적는다 |
| **D-c 하네스 대응** | 원시 $\Delta_r = s_{b^\ast,\max}^{ch} - s_{b^\ast,\max}^{hn,\text{VB e0}}$. 격자 몫 $\delta^{grid}_r = z_{b^\ast}(t_{\max})\,(1 - 1/f_{b^\ast}(t_{\max}))$(Chrono, 0.4). 보정 $\Delta^{corr}_r = \Delta_r - \delta^{grid}_r$. $r \in \mathcal R$. 하네스 패드 요소는 연속 Bekker라 $f \equiv 1$로 둔다(13절) | **등급은 보정값 $\Delta^{corr}_r$로 낸다(사용자 결정 (가), 2026-11-10).** `H-OK`: 모든 $|\Delta^{corr}_r| \le 3$ mm / `H-CONS`: $\Delta^{corr}_r < -3$인 행 ≥ 1이고 $\Delta^{corr}_r > 3$인 행 0 / `H-OPT`: $\Delta^{corr}_r > 3$인 행 ≥ 1. 같은 규칙을 원시 $\Delta_r$로도 계산해 함께 적고, 두 등급이 다르면 등급에 "격자 위상 의존"을 붙인다. **기록 없음**: 행의 $f_{b^\ast}(t_{\max})$를 5.1 기록으로 정할 수 없으면 대체 범위 $\delta^{grid}_r \in z_{b^\ast}(t_{\max})\,[1 - 1/f_{\min},\ 1 - 1/f_{\max}]$(0.4 표 0.01 m 행, 패드 종류별)를 쓰고, $\Delta^{corr}_r$ 구간 전체로 행을 분류한다(사용자 결정 2026-11-10). 구간 전체가 +3 mm 위(아래 끝 > 3 mm)일 때만 "+"(낙관), 구간 전체가 −3 mm 아래(위 끝 < −3 mm)일 때만 "−", 구간 전체가 [−3, +3] mm 안이면 "0"이다. 구간이 +3 mm 또는 −3 mm 문턱에 걸치면 그 행은 "격자 위상 의존(부호 미확정)"이고 "+"·"−"·"0" 어느 쪽으로도 세지 않는다. 부호 미확정 행이 1개 이상이면 D-c 등급에 "격자 위상 의존"과 미확정 행 ID를 붙인다. 모든 행이 부호 미확정이면 D-c는 `NA`다(3.2 빈 집합 금지). 대체 범위로 분류한 행에는 "대체 범위"를 붙인다 | `H-OK`·`H-CONS`: 하네스 스윕을 그대로 B1 근거로 쓴다(`H-CONS`는 차를 여유로 기록). `H-OPT`: 하네스 스윕에 방향별(fdown·diag·fup) 최대 $\Delta^{corr}_r$을 더하고, 그 방향은 B1 채택 전에 Chrono 확인 행을 둔다(B1 규칙에서 정함). 원시 등급이 `H-OPT`이고 보정 등급이 아니면, B1 설계 문서는 원시 $\Delta_r$을 Chrono 실행 격자(0.01 m)의 위상 몫으로 적는다. **절점 계단 표시**: 행마다 $\delta z_{1n} = z_{b^\ast}(t_{\max})\,\Delta^2/(n A_{b^\ast})$($\Delta$ 0.01 m, J2 $n$ = 0.2; 참고 후방 약 1.0 mm·전방 약 0.5 mm)를 적고, 등급을 만든 행 가운데 $|\Delta^{corr}_r| \le \delta z_{1n}$인 행에 "절점 계단 수준"을 붙인다. 이 표시는 등급을 바꾸지 않는다 |
| **D-d 예측자** | 후보 $q \in$ {P-A, P-B, P-C}(6.2)의 $E_q = \max_{r\in\mathcal R}|e_{b^\ast}(r, q)|$. SGS 행은 $s_{\max}$를 가드 도달 값으로 둔다(하한, 6.4) | `PRED-q`: $E_q$ 최소인 $q$(같으면 P-A → P-B → P-C 순으로 단순한 쪽) / `PRED-FAIL`: 최소 $E_q$ > 10 mm | `PRED-q`면 B1은 그 형식을 쓴다. `PRED-FAIL`이면 B1 설계 전에 새 예측 형식을 재등록한다(개정판). 후보 밖 형식은 쓰지 않는다 |
| **D-e B1 필요성** | C1·C2·C4의 Chrono 가드 여유 $g_r = s_{guard} - \max_i s_{i,\max}$, SGS 사건 | `NEED-RECHECK`: 세 행 모두 $g_r \ge$ 20 mm이고 SGS 0 / `B1-OPEN`: 그 밖 | `NEED-RECHECK`면 사용자에게 B1 필요성과 J2 경사 운용 권고(Q6)를 다시 묻는다. B1 설계는 그 답 뒤에 한다 |
| **D-f fup 범위** | C5 Chrono SGS 여부, H-M0 C5 짝 VB·V0($m$ = 0)의 SGS 여부 | `FUP-OUT`: C5 Chrono SGS이고 H-M0 C5 두 짝 모두 SGS / `FUP-IN`: C5 SGS이고 H-M0 짝 중 하나라도 READY / `FUP-NA`: C5 SGS 없음 | `FUP-OUT`: B1 범위(0~30 mm)로 풀 수 없다. 운용 권고 문제로 분리해 사용자에게 묻는다(Q6). `FUP-IN`: B1 대상 방향에 fup를 넣는다 |
| **D-g ×1.1 감도** | $e_{b^\ast}(\text{C6}, q^\ast)$($q^\ast$ = D-d가 고른 형식, 상수는 6.3 그대로), $E_{q^\ast}$ | `W-OK`: $|e(\text{C6})| \le E_{q^\ast}$ + 5 mm / `W-EXT`: 그 밖 / `W-NA`: C6가 VALID가 아니거나 D-d가 `PRED-FAIL` | `W-EXT`면 B1 예측자에 질량(하중) 항이 필요하다. 이 판에서는 정하지 않고 B1 설계 문서에서 다룬다. C6 값은 D-a~D-c 최대 계산에 넣지 않고 따로 적는다 |
| **D-h 기준 정합(P-7)** | `P7_REF`가 있으면 H-P 20실행의 명령 해시 대 기준 | `K-SAME`: 모두 같음 / `K-DIFF`: 하나라도 다름 / `K-NA`: 기준 없음 | `K-DIFF`면 해시가 다른 키를 적고, 그 키의 0.2 하네스 여유를 B1 근거로 쓰지 않는다(새 하네스 값을 쓴다). 등급 계산은 그대로 한다 |

- 안전 기록(관문 아님): `FAULT_STROKE_END`, 다리 부상(접촉력 0이 0.1 s 이상), 크롤러 재착지(이탈 뒤 0.01 W 이상)가 있으면 `SAFETY_NOTE`로 판정서 첫머리에 적는다. 그날 바로 메인 세션에 보고한다. 다른 행은 계속 돈다.

### 3.4 격자 위상이 문턱에 주는 영향 (결과 전 평가, 기록)

크기 기준: 격자 0.01 m, J2. 절대 침하 $z$ ≈ 후방 120 mm·전방 95 mm(0.4 단일 패드 값)에서 격자 몫 $z(1-1/f)$는 후방 약 −1.6 ~ +4.8 mm, 전방 약 −2.7 ~ +4.5 mm다. 실행 중 패드가 움직이면 $t_L$과 $t_{\max}$ 사이에 $f$가 바뀔 수 있다(M-4h, 5.1 기록으로 본다).

| 등급 | 영향 | 근거 | 이 판의 처리 |
|---|---|---|---|
| D-a | 중간 | $\Delta z^{post}$는 같은 패드의 차라 $f$가 일정하면 $(f-1)\Delta z^{post}$(후방 15~60 mm에서 ≤ 약 2.5 mm)만 남는다. $f$가 $t_L \to t_{\max}$에 바뀌면 $z\,\delta f$가 더해진다. 문턱 3 mm와 같은 크기 | 원시값으로 등급, $\Delta z^{post,corr}$ 병기, 등급이 다르면 "격자 위상 의존" |
| D-b | 낮음 | $\delta^{os}$는 $t_R \to t_{\max}$ 같은 패드 행정 차이고, 그 사이 침하 변화가 작다(0.2: READY 뒤 ≤ 0.14 mm) | 처리 없음 |
| D-c | **높음** | Chrono 절대 행정 대 하네스(연속, $f \equiv 1$) 절대 행정의 차라 격자 몫 $z(1-1/f)$가 통째로 들어간다. 후방 +4.8 mm까지로 문턱 3 mm보다 크다 | 보정값 $\Delta^{corr}$로 등급(사용자 결정 (가)), 원시 병기 |
| D-d | 낮음 ~ 중간 | 예측자는 Chrono 자신의 $s_i(t_L)$에서 출발하므로 절대 격자 몫은 빠지고 $t_L \to t_{\max}$ 침하 몫만 남는다(D-a와 같은 크기, 문턱 10 mm) | 처리 없음. 판정서에 $E_q$와 D-a의 $Z_{ch} - Z^{corr}_{ch}$를 나란히 적는다 |
| D-e | 중간 | 가드 여유 $g$는 Chrono 절대 행정이라 격자 몫이 들어간다(문턱 20 mm 대 약 5 mm) | 등급은 원시 $g$로 낸다. 판정서에 $g^{corr} = g + \delta^{grid}$와 0.01 m 위상 범위로 정한 $g$ 범위를 병기한다 |
| D-f | 낮음 ~ 중간(이 판 추가 평가) | SGS 여부는 가드 근처 행에서만 격자 몫으로 뒤집힐 수 있다 | 처리 없음. C5의 $g$와 $\delta^{grid}$를 판정서에 적는다 |
| D-g | 중간 | ×1.1은 $z$가 약 1.6배라 격자 몫도 그만큼 크다. 문턱은 $E_{q^\ast}$ + 5 mm | 처리 없음. C6의 $\delta^{grid}$를 판정서에 적는다 |
| D-h | 없음 | 하네스 명령 해시만 본다 | — |

## 4. 실행 정체성

| 코드 | 조건 | 출처 |
|---|---|---|
| I-1 | 실행 커밋 = `HEAD_M`, checkout이 깨끗함(추적 파일 변경 0) | prelaunch `git_at_start`, result.json `code_state` |
| I-2 | 6행 argv가 2.1절 표와 한 글자씩 같음(`v5_vb_argv()` 전개 포함). prelaunch에 전개된 argv와 그 sha256을 적는다 | `B1_prelaunch.json`, batch.json `cases[].argv` |
| I-3 | `--expect-controller {CTRL_TAG_VB}`이고 러너가 보고한 태그가 같음(`expect_controller.ok` 참), 제어기 클래스 `C2Controller` | result.json `c2_setup`, `controller_meta` |
| I-4 | `num_threads_chrono` = 4 | result.json |
| I-5 | 자식 env `OMP_WAIT_POLICY=PASSIVE` | batch.json 기록값 |
| I-6 | 풀이 스케줄러 배치표의 풀과 같음(P 또는 E, 행마다 prelaunch에 적은 값). 실행 중 affinity 변경은 판정서에 적는다 | batch.json `pool`, 배치표 |
| I-7 | `hull_hook` requested = effective = `fast`, DLL sha = `HULL_DLL_SHA`, batch.json `MIXED_HULL_MODE` 없음 | result.json `hull_hook`, batch.json |
| I-8 | `params_file` 지문 = 봉인 때 YAML(`02_params/rexome33.yaml`) sha | result.json |
| I-9 | 하네스 28실행: 같은 `HEAD_M`(또는 prelaunch에 적은 하네스 커밋), 태그 = `{CTRL_TAG_VB}`/`{CTRL_TAG_V0}`, H-M0는 연구용 하위 클래스 이름과 $m$ = 0이 meta에 있음 | 하네스 jsonl meta |

### 4.3 재실행

- 오류·결과 파일 누락(V-1 실패)이면 그 행만 1회 `--resume`한다. 조건은 같은 `HEAD_M`, 같은 배치 폴더다.
- 원 로그·폴더는 배치 밖 `attempt1/`로 옮긴다(지우지 않는다). 판정서에 `rerun_of`를 적는다.
- 시작 거부·`NO_LOC`·`INVALID`는 다시 돌리지 않는다.
- 하네스 실행은 결정적이므로, 오류 행은 같은 커밋에서 다시 돌리고 출력 해시를 적는다.

## 5. 지표 정의 (경로 1·2가 같은 정의로 계산)

시각 기준은 다음과 같다.

- $t_{L}$ = 마지막 LOC(`crawler_liftoff_confirmed`의 마지막, 취소 뒤 재LOC 포함)
- $t_{L1}$ = 첫 LOC
- $t_R$ = 첫 READY 진입(P3-5 `t_first_ready_s`)
- $t_{\max}$ = 모든 다리 판독 행정 최대가 처음 나온 10 Hz 표본 시각
- $t_{end}$ = 마지막 표본

| 코드 | 양 | 식 |
|---|---|---|
| M-1 | 시각 | $t_{dep}$, $t_{L1}$, $t_L$, LOC 취소 수, $t_R$, $t_{creep}$(현행 규칙 1.0 s 창 < 0.1 mm/s, `p3b.creep_stop.t_final_s`), $t_{\max}$ |
| M-2 | 행정 예산 | $s_i(t_L)$, $s_i(t_R)$, $s_{i,\max}$, $b^\ast = \arg\max_i s_{i,\max}$, $g = s_{guard} - s_{b^\ast,\max}$, SGS·`WARN_LIFT_STROKE_LIMITED` 시각 |
| M-4 | 침하 | $\Delta z^{post}_i = z_i(t_{\max}) - z_i(t_L)$. 기록용으로 $z_i(t_R) - z_i(t_L)$, $z_i(t_{end}) - z_i(t_R)$, LOC 뒤 최대 침하율(1.0 s 후진 차분), $\Delta z_i / \Delta F_i$(할선, $t_L \to t_R$)도 낸다. 1 ms 계열은 10 Hz 시각과 같은 시각 이하 마지막 표본을 쓴다(`searchsorted(t, τ − 1e-9)`) |
| M-5 | 과도 초과 | $\delta^{os}_i = s_{i,\max} - s_i(t_R)$($t_R$ 없으면 `NA`), $t_{\max} - t_L$ |
| M-6 | 예측자 오차 | $e_i(q) = s_{i,\max} - \hat s^{(q)}_{i,\max}$(+ = 예측 부족). 6절 식으로 낸다 |
| M-4h | 패드 수평 변위(기록, 권고) | 패드 $i$ 수평 변위 $\lVert \Delta \mathbf{r}_{i,xy} \rVert$($t_L \to t_{\max}$, 지면 고정 좌표). Chrono는 패드 바디 위치(cad-expert가 기록 필드를 정함), 하네스는 패드 요소 접선 변위. 등급에 쓰지 않는다 |
| M-7 | 크롤러 | $t_L$·$t_R$·$t_{end}$의 격자 참 틈(P3-5), 제어기 틈 추정, 이탈 뒤 최대 크롤러 하중 |
| M-8 | 규칙 작동 | E3c10(`INFO_LOC_CLEARANCE_MARGIN:<mm>`), `INFO_LOC_REVOKED`, `order_gate.decisions` 수, DSb75 HOLD·RELEASE 사유, SGS, P30fz·LWa |
| M-9 | P3 행(기록) | `p3b` P3-1~P3-8, SL 분류 |
| M-10 | 짝 차 | M-2·M-4·M-5의 Chrono − 하네스 VB e0. e0.002·V0는 산포로 적는다 |
| M-11 | 격자 인자(Chrono) | 다리 $i$, 시각 $\tau \in \{t_L, t_R, t_{\max}, t_{end}\}$의 $N_h$, $b_{hull}$, $f_i(\tau)$(0.4 식), $z_i(\tau)/f_i(\tau)$, $\delta^{grid}_i(\tau) = z_i(\tau)(1 - 1/f_i(\tau))$, $\delta z_{1n,i}(\tau)$, $\Delta z^{post,corr}_i$, $\Delta^{corr}_r$, $g^{corr}$. $f_i(\tau)$는 5.1 기록 가운데 시각 ≤ $\tau$인 마지막 기록으로 정하고, 그 기록과 $\tau$의 간격이 1.0 s를 넘거나 $N_h$ < 3이면 "기록 없음"(3.3 D-c 대체 범위)이다. 하네스는 $f \equiv 1$ |

- 하네스도 같은 식을 쓴다. 판독 행정은 10 Hz 주기 기록이고, 침하는 패드 요소 침하다.

### 5.1 B1 Chrono 행 기록 요구 (구현 cad-expert, 봉인 전 확인)

| 항목 | 시각 | 내용 | 출처 함수 |
|---|---|---|---|
| R-G1 | $t_L$(각 LOC 확정 주기), $t_R$(첫 READY 진입 주기), $t_{end}$, 그리고 1 s 간격(가능하면 10 Hz) | 다리별 `n_inside`, `n_contact`, `contact_hull_area_m2`, `contact_hull_perimeter_m`, `sinkage_geometric_m`, `sigma_sum_area_N` | `03_src/outrigger_sim/chrono/scm_model.py:502` `node_stats_in_outline` |
| R-G2 | 10 Hz | 다리별 패드 바디 중심 xy [m](지면 고정 좌표), 요 [rad] | 패드 바디 자세 |
| R-G3 | 실행 시작 | 패드 격자 $\Delta$, SCM 평면 원점·회전, 패드 다각형(기체 국부 좌표), $b_{poly}$ | `meta.scm` |

- $t_{\max}$는 실행이 끝나야 정해지므로 실행 중에는 R-G1 정시 기록으로 덮는다. 1 s 간격이면 $t_{\max}$ 앞 마지막 기록까지 최대 1 s이고, M-11 규칙(≤ 1.0 s)에 들어간다. 10 Hz가 벽시계 비용 5 % 안이면 10 Hz로 한다(cad-expert가 비용을 재서 정하고 prelaunch에 적는다).
- R-G2는 R-G1 사이 시각의 $N_h$를 기하로 다시 셀 때 쓴다(사후 재구성, 등급 계산에는 쓰지 않고 기록만).
- 기록은 `record.npz` 또는 별도 `grid_nodes.npz`로 남긴다. 키 이름은 cad-expert가 정하고 경로 1·2가 같은 키를 읽는다. 기록 필드가 빠진 행은 `INVALID`가 아니라 D-c 대체 범위로 처리한다(3.3).
- 이 기록 추가는 패드 힘을 바꾸지 않아야 한다(읽기 전용 `GetNodeInfo`). cad-expert는 기록 켬·끔 짧은 짝 1건으로 `step_series.npz` 비트 동일을 확인하고 prelaunch에 적는다.

## 6. 예측자 후보 (LOC 주기 정보만)

### 6.1 기하

- 패드 위치 $(x_i, y_i)$는 YAML `legs`(기체 좌표)에서 읽는다.
- $\Delta s^{geo}_i = x_i\,\hat\theta_{L} - y_i\,\hat\phi_{L}$(공통 모드 제외, 소각 근사)
  - $\hat\phi_L, \hat\theta_L$ = $t_L$ 주기의 필터 자세(제어기 값) [rad]
  - pitch > 0 = 앞내림, roll > 0 = 왼쪽 위
  - 앞내림($\hat\theta > 0$)이면 앞 다리($x_i > 0$)가 늘어난다. 왼쪽 위($\hat\phi > 0$)이면 왼쪽 다리($y_i > 0$)가 줄어든다.
- **부호 확인은 실행 전 dynamics-expert가 한다.** 저장 X4-nd 기록으로 예산 다리 $\Delta s^{geo}$ 부호가 맞는지 보고, 틀리면 이 식의 부호를 봉인 전에 고친다(변경 기록).

### 6.2 후보

| 후보 | $\hat s^{(q)}_{i,\max}$ |
|---|---|
| P-A | $s_i(t_L) + \Delta s^{geo}_i + (c^\ast + m_L - \hat c(t_L))^+$, $m_L$ = 그 실행의 LOC 때 적용 여유(E3c10 작동이면 0.03, 아니면 0) |
| P-B | P-A + $\kappa_z\,\max(\hat W_i, 0)$ |
| P-C | P-B + $\delta_{allow}$ |

### 6.3 상수 (하네스에서만, Chrono 결과 전에 고정)

- $\kappa_z$: **패드 종류별로 따로 정한다.** $\kappa_{z,F}$(전방 330, FL·FR)와 $\kappa_{z,R}$(후방 250, RL·RR)는 H-P 20실행의 해당 종류 다리 전부(예산 다리만이 아님)의 $\Delta z^{post}_i/\max(\hat W_i, 1\,\text{N})$ 최대 [m/N]다. P-B는 다리 $i$의 패드 종류 값을 쓴다.
  - 근거: terramechanics 검토의 접선 유연도는 앞 3.6 / 뒤 7.9 mm/kN(2.2배)이다(0.3).
  - **결과 전 후보 정의 변경(공개)**: 2026-11-10 후보판 첫 작성 때는 예산 다리 단일 $\kappa_z$였다. 하네스·Chrono B1 결과를 보기 전, 검토를 받고 바꿨다.
- $\delta_{allow}$: H-P 20실행의 $b^\ast$ 다리 $\delta^{os}$ 최대 [m]
- 기록: `b1_harness_constants.json`(값, 쓴 실행 목록, 도구 sha)
- 고정 시점: 그 sha를 실행 전 감사 보고와 prelaunch에 적은 뒤에만 Chrono를 시작한다(T 순서).

### 6.4 SGS 행

- SGS로 멈춘 행의 $s_{\max}$는 실제 최대(가드 근처)다. 멈추지 않았다면 더 늘었을 것이므로 이 값은 하한이다.
- 그런 행의 $e$는 `lower_bound` 표시를 붙인다.
- D-d 계산에서 $e$ < 0(과대 예측)인 SGS 행은 그 값을 그대로 쓴다. $e$ ≥ 0이면 하한으로 쓴다. 실제 오차는 그보다 크거나 같으므로, 이 값으로 `PRED-q`가 나와도 판정서에 "하한 포함"을 적는다.

## 7. 방향 예측 (기록, 등급에 쓰지 않음)

| # | 예측 |
|---|---|
| P-1 | C1~C3 FL의 $\Delta z^{post}$ 0~15 mm, 뒤 패드보다 작음. C5 RL 15~60 mm, ×1.0 다섯 행 중 최대 |
| P-2 | READY → 끝 추가 침하 ≤ 5 mm(재레벨이 없으면 ≤ 0.5 mm). $t_{creep}$ ≤ 마지막 READY + 30 s |
| P-3 | 원시 $\Delta_r$ ∈ [−8, +3] mm. 0 또는 음이 더 많음(첫 후보판 예측 그대로, 원시값 기준). 보정 $\Delta^{corr}_r$의 범위 예측은 따로 등록하지 않는다(2026-11-10 격자 개정) |
| P-4 | $\delta^{os}$: fdown·fup 5~30 mm, diag 3~15 mm |
| P-5 | C1은 SGS 또는 $g$ < 10 mm. `FAULT_STROKE_END` 0, 다리 부상 0 |
| P-6 | C5 SGS(RL), Chrono 가드 시각 ≤ 하네스 VB e0 가드 시각 |
| P-7 | `P7_REF`가 있으면 `K-SAME`. Chrono E3c10 LOC의 `order_gate.decisions` 0 |
| P-8 | P-A의 $e$ > 0이 모든 VALID 행에서 성립, $E_{\text{P-C}}$ ≤ 10 mm |
| P-9 | C6: C1보다 $g$가 작거나 SGS가 이르다. **`W-EXT` 예상**: ×1.0 하네스에서 정한 선형 $\kappa_z$로는 ×1.1의 침하 증가를 못 따라간다. 근거는 접선 유연도 ∝ $F^{1/n-1} = F^4$라 ×1.1이면 $z$가 1.61배이고, 저장 REM ×1.1 대 ×1.0이 1.57~1.74배라는 것이다(0.3). 결과 전 변경(첫 후보판은 `W-OK`), 공개 |

## 8. 두 경로 재집계

| 경로 | 담당 | 고정 시점 | 출력 |
|---|---|---|---|
| 경로 1 | python-expert 지표 도구(`b1_creep_metrics.py` 가칭, `evidence/post_loc_digest.py`를 정식 도구로 옮기고 확장) | 실행 전 감사 전에 sha 고정 | `b1_metrics_path1.json` |
| 경로 2 | control-expert 독립 스크립트(경로 1 코드를 import하지 않음, numpy·json만) | **Chrono 결과 전**에 sha 고정, 하네스 짝 출력으로 시험 | `b1_metrics_path2.json` |

- **격자 지표 구현 요구(2026-11-10)**: 경로 1 도구(python-expert)는 M-11(0.4 식의 $f$, $z/f$, $\delta^{grid}$, $\delta z_{1n}$, $\Delta z^{post,corr}$, $\Delta^{corr}$, $g^{corr}$)과 D-c 보정·원시 이중 등급, "격자 위상 의존"·"대체 범위"·"절점 계단 수준" 표시, D-a·D-e 병기를 낸다. 토양 상수는 `02_params/scm_soil_sets.json`, $A$·$b_{poly}$는 YAML `pad_shapes`에서 읽는다(손으로 적지 않는다). 경로 2도 같은 양을 따로 계산한다.
- 순서: postrun → 경로 2 실행(출력 sha 기록) → 경로 1 실행 → 대조(K-R).
- K-R 대조 항목은 다음과 같다.
  - 행 상태(3.1), 묶음 상태(3.2)
  - M-1·M-2·M-4·M-5·M-6·M-11의 모든 수치
  - 6.3 상수(경로 2가 하네스에서 따로 다시 계산)
  - 등급 D-a~D-h와 각 등급의 계산 행 목록
- 허용
  - 이산 항목(상태·등급·$b^\ast$·시각 표본 번호·사건 수)은 완전 일치해야 한다.
  - 실수 항목은 같은 입력이므로 절대차 ≤ 1×10⁻⁶ mm(1×10⁻⁹ m)다.
  - 시각은 같은 표본이어야 한다.
- 불일치가 나면 그 항목이 들어가는 등급은 `UNDETERMINED`다. 도구를 결과에 맞춰 고치지 않는다. 원인이 정의 해석 차이면 개정판으로 정의를 고친 뒤 두 경로를 다시 돌리고, 그 사실을 첫머리에 적는다.

## 9. 세 시점 감사와 시간 순서

| 시점 | 감사 범위 | 차단 조건 |
|---|---|---|
| 실행 전 | S(봉인 sha·파라미터 칸 모두 채움·`.gitattributes -text`, 격자 시험 `b1_gridconv_plan.md` 봉인 sha와 그 판정 `PASS`), E(3.2 빈 집합 규칙이 도구에 있음), I(4절 항목을 prelaunch가 기록, 5.1 격자 기록이 켜져 있고 기록 켬·끔 비트 동일 확인이 prelaunch에 있음), R(경로 1 도구의 정의가 5·6절·M-11과 같음), T(격자 시험 판정 → 봉인 → 하네스 → 상수 고정 → 경로 2 sha 고정 → prelaunch 순서) | 하나라도 차단 → 실행하지 않음 |
| 판정 후 | C(두 경로 대조 K-R), E(등급별 행 수), I(V-2 결과), T(경로 2 출력 sha가 경로 1 실행보다 앞섬) | 차단 → 판정서 커밋 보류 |
| 전환 후 | 파라미터 결속: 봉인판 `CTRL_TAG_*`가 P5r4 결정 뒤 실제 프리셋 태그와 같은지, 래퍼·프리셋 이중 적용 없음, `_K1`(또는 전환) 접미사로 대상을 고르는 곳 | 차단 → 개정판 |

- 전환 후 감사는 P5r4+K1 채택 전환이 있으면 그 전환 직후, 없으면 파라미터를 채운 봉인 직전에 한 번 한다.
- 감사는 verif-protocol-auditor가 하고, 도구는 `tools/verif` seal_check·gate_scan·record_check·timeline이다.

## 10. 결과물

- `07_results/S9/batch_V5-B1-CREEP_<stamp>/`(Chrono 6행)
- 하네스 출력 `06_analysis/03_hydraulic/coupled/v5/b1/b1_H.jsonl` + npz
- `b1_harness_constants.json`, `B1_prelaunch.json`
- `b1_metrics_path1.json` / `b1_metrics_path2.json`
- 판정서 `06_analysis/02_control/b1/b1_creep_basis_judgement.md`: 등급표, 행 상태, 예측 대조, `SAFETY_NOTE`, D-e·D-f에 따른 사용자 질문

## 11. 비용·순서 (가정)

- Chrono 행당 7,000~10,000 s(J2 경사 160 s, P 4병렬, threads 4, fast; REM 상단 6,500 s × 160/120 외삽, 경사 ±15 %)
- C6(×1.1, 180 s)은 약 9,000~12,500 s
- E 풀이면 × 1.5
- 6행: P 4 + 2(두 물결)이면 약 4.5~6.3 h. 풀 배정은 compute-scheduler-expert가 정한다(Q4).
- 하네스 28실행: E코어 4워커 약 15분
- 위 Chrono 비용은 패드 0.01 m 저장 행(REM) 외삽이라 2.1절 격자(0.01 m)와 맞는다. 첫 후보판의 0.02 m였다면 이 외삽은 성립하지 않았다.
- 격자 시험 4행(`b1_gridconv_plan.md` 7절): 단일 패드 21 s, 직렬 약 0.9~1.2 h(E 풀, P1 실측 us/step 외삽)
- P코어 순서: D8x Chrono 19행 → P5r4+K1 Chrono 12행 → 판정·채택 결정 → 파라미터 채움·봉인·감사 → **이 6행**

## 12. 남은 확인 필요

| # | 내용 | 누가 |
|---|---|---|
| R-1 | 1절 파라미터 전부(P5r4+K1 판정·채택 결정 뒤) | 사용자 결정 → 메인 세션이 채움 |
| R-2 | `--start-limit` 값과 `--expect-controller` 정합, J2 경사 SCM 지형 크기, M-4h 패드 수평 변위 기록 필드. **권고(terramechanics T-6): `--start-limit record_only`로 정한다**(J2 경사 크롤러 정착 기울기 증가로 $R_c$ > 1이 되어 시작 거부 결측이 날 위험) | cad-expert |
| R-3 | 6.1 기하 부호 확인(X4-nd 저장 기록) | dynamics-expert |
| R-4 | 하네스 질량 배율·$m$ 교체 지원 여부(H-W·H-M0) | python-expert |
| R-5 | $Z_{soil}$(T-2 실토양 크리프 허용). 이 규칙의 등급에는 쓰지 않고 B1 설계 문서에서 쓴다 | terramechanics-expert |
| R-6 | **닫힘(2026-11-10)**: 문턱 3 / 5 / 10 / 20 / +5 mm 그대로 봉인(terramechanics 검토 뒤 사용자 결정) | — |
| R-7 | 5.1 격자 기록(R-G1~R-G3) 구현, 10 Hz 가능 여부(비용 ≤ 5 %), 기록 켬·끔 비트 동일 확인 | cad-expert |
| R-8 | 경로 1 도구에 M-11·D-c 이중 등급·병기 구현(8절) | python-expert |
| R-9 | 격자 시험 `b1_gridconv_plan.md` 4행 실행·판정(봉인 전제) | 메인 세션(배치표 compute-scheduler-expert, 실행 cad-expert 명령) → control-expert 판정 |
| R-10 | 하네스 패드 요소가 연속 Bekker($b$ = YAML `bekker_b_m`, $f \equiv 1$)인지 확인(`04_scripts/03_control/s9/s9_soil_closed_loop.py:144-146`이 그 식이다. v5 `run_v5.py d1` 경로가 같은 클래스를 쓰는지) | python-expert |
| R-11 | 저장 경계 행의 격자 위상 사후 재구성 | cad-expert(별도 작업, 이 판 범위 밖) |

## 13. 가정

- `--duration` 160 s(C6 180 s), 비용, 7절 예측 범위, 3.3 문턱(3 / 5 / 10 / 20 / +5 mm), 6.4 SGS 하한 처리, 5절 침하 기준 시각($t_{\max}$)은 원본에 없어서 정한 값이다.
- 압력 `normal`·IMU `ideal`은 판정 실행 관례다.
- 격자 개정(2026-11-10)에서 정한 값: M-11의 기록 간격 한계 1.0 s와 $N_h$ ≥ 3, D-c 대체 범위의 $f_{min}$·$f_{max}$로 0.4 표 0.01 m 행을 쓰는 것(분류 규칙 자체는 사용자 결정), 3.4 영향 크기($z$ 후방 120·전방 95 mm 기준), 5.1 10 Hz 비용 한계 5 %. 하네스 $f \equiv 1$은 R-10 확인 전 가정이다.
- 0.4의 $f$ 식은 정적 Bekker 처녀 분기다. 점성 지연($R$)·탄성 재하($K$)·접촉 절점 가장자리의 부분 σ는 넣지 않았다. P1 V16bp에서 이 식과 Chrono가 0.05 % 안에서 맞은 것이 그 근거다(유지 하중 끝 값).

### 13.1 모형 범위 (terramechanics 검토, 0.3)

- SCM의 패드 침하는 지나간 최대 하중의 Bekker 침하와 점성 지연($\tau = R/(n\,p/z)$ ≈ 0.4~0.5 s, J2)으로 정해진다.
  - 압밀·2차 압축 같은 시간 의존 크리프와 전단 유발 침하(slip sinkage)는 없다(SCMTerrain.cpp `SCMLoader::ComputeInternalForces`, σ를 τ보다 먼저 정하고 되먹임 없음).
  - 이 규칙의 $\Delta z^{post}$와 D-a는 이 모형 안의 양이고, 실토양 몫 $Z_{soil}$은 B1 설계 문서에서 따로 더한다.
- D-e의 가드 여유는 SCM 명목 세트의 값이다.
  - J2 침하는 $k_{eq}$ 4 %, $n$ 0.02 차로 20 mm 이상 바뀌므로 실토양 여유로 읽지 않는다.
  - $p/q_{ult}$가 약 0.82~0.87로 파괴 근처라 Bekker 침하는 하한이다.

## 14. 변경 기록 (봉인 전)

- 2026-11-10 후보판 작성: 초안 `8b390d9` 대비 다음을 바꿨다.
  - C6 추가(Q1 다)
  - 정식 봉인 형식(Q2 나)
  - H-M0 하네스 $m$ = 0 짝(Q3)
  - D-a~D-f를 등급으로 바꾸고 D-g(×1.1)·D-h(P-7 기준 정합)를 더함
  - 파라미터 절(Q5)
  - 예측자 SGS 하한 처리
- 2026-11-10 terramechanics 검토 반영(결과 전)
  - 0.3 검토 요약을 공개했다
  - 13.1 모형 범위를 더했다(SCM 침하 기구, D-e 해석 제한)
  - D-c에 격자 양자 표시를 더했다(등급 불변)
  - M-4h 패드 수평 변위를 기록 항목으로 더했다
  - 6.3 $\kappa_z$를 패드 종류별로 바꿨다(후보 정의 변경)
  - P-9 예측을 `W-OK`에서 `W-EXT` 예상으로 바꿨다
  - R-2에 `record_only` 권고를 적었다
  - R-6을 닫았다(문턱 그대로)
- 2026-11-10 격자 개정(결과 전, control-expert). **B1 Chrono 6행·하네스 28실행·격자 시험 4행 모두 실행 전이고, 어떤 결과도 보지 않았다.** 근거는 terramechanics-expert 2차 검토(2026-11-10, 스캔 `evidence/gridconv_scan/`, 0.4)와 봉인 전에 본 P1 V16bp(공개, 0.4)다. 사용자 결정 2026-11-10 1~4.
  - 2.1 격자 `--grid 0.02` → `--grid 0.01 --crawler-grid 0.04`. 0.02는 U-S9G-1(J1·J2 패드 1 cm), 0.2절 저장 Chrono 7건, 11절 비용 외삽과 맞지 않는 오기였다(결정 1)
  - 0.3 "격자 절점 침하 양자" 행을 격자 인자 $f$ 행과 "절점 하나 계단" 행(0.01 m, 후방 약 1.0·전방 약 0.5 mm)으로 바꿨다. 첫 후보판의 "앞 1.6·뒤 3.8 mm"(0.02 m 값)는 폐기했다
  - 0.4 SCM 격자 인자 절을 새로 넣었다(식, 위상 범위 표, P1 V16bp 공개, 저장 결과 격자 조사)
  - D-c: 등급을 보정값 $\Delta^{corr} = \Delta - \delta^{grid}$로 내고 원시 등급을 병기, 다르면 "격자 위상 의존", 기록 없으면 대체 범위(결정 3 (가)). "격자 양자 수준" 표시를 "절점 계단 수준"($\delta z_{1n}$, 0.01 m)으로 이름과 값을 바꿔 유지했다
  - D-a: $\Delta z^{post,corr}$ 기록과 등급 차 표시를 넣었다(등급은 원시값)
  - 3.4 격자 위상 영향 표, M-11 격자 지표, 5.1 Chrono 행 기록 요구(cad-expert), 8절 경로 1 구현 요구(python-expert)를 넣었다
  - 3.0·9절: 격자 시험 `b1_gridconv_plan.md` `PASS`를 봉인 전제로 넣었다(결정 2). 그 계획서의 원래 예측(0.02 대 0.01, 패드 절대 차 ≤ 4 mm·Δz 차 ≤ 2 mm, 인계 문서 2.3)은 결과 전에 0.01 대 0.005 4행으로 개정됐다
  - 7절 P-3을 원시값 예측으로 못 박았다(보정값 예측은 등록하지 않음)
  - 12절 R-7~R-11, 13절 가정을 더했다
  - 저장 경계 행의 위상 사후 재구성은 이 판에 넣지 않았다(결정 4, cad-expert 별도)
  - 첫머리 "9절 변경 기록"을 "14절 변경 기록"으로 바로잡았다(절 번호 오기)
- 2026-11-10 D-c 대체 범위 분류 변경(결과 전, 사용자 결정 2026-11-10). 격자 개정 커밋 `71bf74d`의 "위 끝 기준" 분류(위 끝 > 3이면 "+")를, 구간 전체가 +3 mm 위일 때만 "+", 전체가 −3 mm 아래일 때만 "−", 문턱에 걸치면 "격자 위상 의존(부호 미확정)"으로 바꿨다. 부호 미확정 행은 세지 않고 등급에 표시하며, 전부 미확정이면 `NA`다. B1 Chrono·하네스·격자 시험 결과는 모두 보기 전이다
- 2026-11-10 격자 시험 결과 반영(GC 판정 뒤, B1 결과 전). `b1_gridconv_judgement.md`(sha256 `c0a847b2…48b28bb1`) `PASS`를 0.4절에 "0.01 m 확정 근거"로 적었다(계획 6절). 2.1 격자, D-c 등급 규칙, 문턱, 예측은 바꾸지 않았다. B1 Chrono 6행·하네스 28실행 결과는 아직 보지 않았다
