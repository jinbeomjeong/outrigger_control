# B1 격자 수렴 시험 계획서 — J2 패드 B 단일 패드 0.01 대 0.005 m (`B1-GRIDCONV`)

- 작성: control-expert, 2026-11-10
- 상태: **봉인판**(`b1_gridconv_plan.sha256`). 결과를 하나도 보기 전에 봉인했다.
  - 봉인 뒤 바꾸려면 개정판(rev1 …)을 만들고, 결과를 보기 전인지 본 뒤인지를 첫머리에 적는다.
- 목적: B1 크리프 근거 규칙 후보판(`b1_creep_basis_rules.md`) 2.1절의 패드 격자 0.01 m가 J2 패드 B에서 수렴했는지, 그리고 그 판 D-c의 격자 보정 $z/f$가 격자에 무관한 양인지 확인한다. 이 시험이 `PASS`여야 B1 규칙을 봉인한다(B1 3.0·9절).
- 성격: 수치 모형(SCM 격자) 수렴 확인이다. 제어기 판정이 아니고, 제어기는 돌지 않는다.
- 사용자 결정(2026-11-10)
  - 격자 시험을 0.01 대 0.005 m, RL + FL 4행으로 한다.
  - P1 V16bp를 "봉인 전에 본 자료"로 공개한다(2절).
  - 원래 예측(0.02 대 0.01 m, 패드 절대 차 ≤ 4 mm·Δz 차 ≤ 2 mm; `00_docs/handoff/session_handoff.md` 2.3)은 결과 전에 이 계획서로 개정한다. 그 원래 계획은 실행하지 않았다.
- 규약
  - 침하 $z$: + = 깊어짐 [m], 표시는 mm. 주 값은 패드 바닥 기하 침하 `sinkage_geometric_m`, 법칙 비교(G-1)는 접촉 절점 평균 `sinkage_mean_contact_m`이다. 둘의 차는 P1에서 ≤ 1×10⁻⁸ m였다.
  - 하중 $F$: 연직 [N]. 법칙 비교에는 기록된 SCM 연직력 `Fz_scm_N`을 쓴다.
  - 시각: 실행 시작 기준 절대 시각 [s].

## 1. 기호와 식

$$z_{cont} = \left(\frac{F}{A\,(k_c/b_{poly} + k_\varphi)}\right)^{1/n},\qquad
z_{ref} = \left(\frac{F}{N_h\,\Delta^2\,(k_c/b_{hull} + k_\varphi)}\right)^{1/n} = f\,z_{cont}$$

$$f = \left[\frac{N_h\,\Delta^2\,(k_c/b_{hull} + k_\varphi)}{A\,(k_c/b_{poly} + k_\varphi)}\right]^{-1/n}$$

| 기호 | 정의 | 값·출처 | 단위 |
|---|---|---|---|
| $\Delta$ | 패드 SCM 격자 간격 | 0.01 / 0.005 | m |
| $N_h$ | 패드 다각형 안 접촉 절점 수(σ > 0) | result.json `load_steps.levels[k].end.nodes.n_contact` | — |
| $b_{hull}$ | 접촉 절점 볼록 껍질 $2A_{hull}/P_{hull}$ | 같은 곳 `contact_hull_area_m2`, `contact_hull_perimeter_m` | m |
| $A$, $b_{poly}$ | 패드 다각형 면적, $2A/P$ | 패드 B 후방 0.0607 m²·0.1306 m, 전방 0.1071 m²·0.1714 m(result.json `meta.pad_area_m2`, 다각형은 YAML `pad_shapes`) | m², m |
| $k_c$, $k_\varphi$, $n$ | J2 세트 | 16,430 / 1,724,690 / 0.2(result.json `meta.scm.SetSoilParameters`) | N/m^(n+1), N/m^(n+2), — |
| $N_1$, $N_2$ | 첫째·둘째 유지 하중 | 3절 | N |
| $z_1$, $z_2$ | 첫째·둘째 유지 끝($t$ = 11.0 s, 21.0 s)의 침하 | result.json `load_steps.levels[0].end`, `levels[1].end` | m |
| $\Delta z$ | $z_2 - z_1$ | — | m |

- 근거: Chrono 소스 `SCMTerrain.cpp` 584-588(절점 면적 $\Delta^2$에 σ), 1366-1377(패치 $b$ = 볼록 껍질 $2A/P$), 1475(패치별 Bekker). terramechanics-expert 검토(2026-11-10).
- 같은 $F$ 비율이면 $\Delta z/z_2$는 $f$와 무관하다. 그래서 G-3이 격자 무관이어야 한다.

## 2. 봉인 전에 본 자료 (공개)

| 자료 | 내용 | sha256 |
|---|---|---|
| P1 `V16bp_J2_B_RL_2cm`(2026-10-26) | 단일 패드 RL, J2, 72.81 kN, 격자 0.02 m: $N_h$ 157, $b_{hull}$ 0.1256 m, 침하 95.271 mm, $z_{ref}$ 95.274 mm($z/z_{ref} - 1$ = −0.0000) | `result.json` `dea9384d973ab9916f91692459881514ab91147806ac6569ac33af94d65017b9` |
| P1 `V16bp_J2_B_RL_1cm`(2026-10-26) | 같은 조건, 0.01 m: $N_h$ 601, $b_{hull}$ 0.1255 m, 침하 118.604 mm, $z_{ref}$ 118.652 mm(−0.0004) | `result.json` `2d1c0d7ae9330b1e76bc494d516f5aede1c1a71e717e0c386a59904c024d4ac6` |
| P1 V16 J1 RL·FL 2/1/0.5 cm | 같은 법칙 대조(J1). 유지 끝 $|z/z_{ref} - 1|$ ≤ 0.0075 | `evidence/gridconv_scan/p1_levels.txt` |

- P1 결과 폴더: `07_results/S9/batch_P1_V16_20261026_032113/`(git 제외).
- terramechanics 스캔(2026-11-10). 원본은 terramechanics-expert scratchpad `terra\`이고, 같은 바이트를 `06_analysis/02_control/b1/evidence/gridconv_scan/`에 복사했다(sha 동일 확인).

| 파일 | sha256 | 내용 |
|---|---|---|
| `grid_census.txt` | `37d13a3d8eb579bf948f2338c50def61d7ab4d471ba203c5724b7122192a995f` | 저장 S9 결과의 격자 조사(J1·J2 레벨링은 모두 0.01 m) |
| `grid_census.py` | `b1a5afa86d018e3fc8a40b6ed173b8cf0293d4c7f96b510268553dc514ea8a81` | 위 스크립트 |
| `p1_dump.txt` | `05a896e38a5833ac8a3fb6dc6c6154e896d7d0323a09ee1b720e73bd55346fb8` | P1 V16bp 2 cm result.json 덤프 |
| `p1_dump.py` | `3b7f8ee41fa9040cc437bab120be76dad9ebad0a272bda99c4a0f32b82628a2e` | 위 스크립트 |
| `p1_levels.txt` | `058957b3aa2c185e5561a5b738ff44da8b520e2fb1cbf5930623c6b4fe755aa1` | P1 유지 끝 법칙 대조 표 |
| `p1_levels.py` | `91222f3304cd801e6d8aacb6ff711347f80596ee845185e8864d16ef2696e92b` | 위 스크립트(G-1 경로 B의 원형) |
| `phase_band.txt` | `20e1c2e52a0960913f2afbaaafa237b50d7717fc53a1be4a26679011235fec02` | 격자 위상 범위 $f - 1$, 이 시험 하중의 예측 |
| `phase_band.py` | `4458c2e73c26381c65021b07ed88b88637eed2b1fcbb8569ff02b4e4dcfb62d7` | 위 스크립트 |
| `machine_phase.txt` | `32c4c80c684b94ce62fc20664f96c925f8d74519bdff1a21e01be3523477c5e3` | 기계 실행 패드 위치의 $f - 1$ |
| `machine_phase.py` | `2a04a2d091e1455276dc7cd00c4464915426cf1a45bb79c1f6863902e1c5f556` | 위 스크립트 |
| `mdelta.txt` | `db41966d43500e3d27d38bea1ff70e104fa828e517624054319bbcc09ffd3fa9` | SCM 격자 간격 반올림 점검(상대차 0) |
| `mdelta.py` | `a3b02b6c4690c1ee085f8e6a32fecfdd9c8cdaa4a218323d3b61a9bdbbcd11c9` | 위 스크립트 |

- 예측 재계산(control-expert, 독립): `evidence/gridconv_scan/gc_pred.py`와 출력 `gc_pred.json`. sha는 7절 표에 적는다.

## 3. 실행 행

### 3.1 공통 조건

- 실행기 `04_scripts/02_chrono/run_S9.py single-pad`, env Chrono-dev, 실행 커밋은 이 계획서를 담은 master 커밋 이후의 깨끗한 checkout(`HEAD_G`, prelaunch에 적음)
- `--soil J2 --pad-variant dwg_rear250 --level top --joint fixed --threads 4`(P1 V16bp와 같은 연결; `--scm-shear`·`--stiffness-mode`·`--ray-shape`·`--dt`·`--k-sw`·`--terrain-size`는 기본값 `bprime`·`series`·`mesh`·1e-4·1.5e4·1.2 1.2)
- 패드 시작 위치 오프셋 0(기본, SCM 평면 원점 = 패드 중심)
- 하중: Poly345 3 s 램프 → 8 s 유지 → Poly345 2 s → 8 s 유지(끝 21 s). `--normal-load` $N_2$, `--load-steps` $N_1/N_2$,1.0, `--load-ramp 3 --step-ramp 2 --step-hold 8`
- env: `OMP_WAIT_POLICY=PASSIVE`(시작 전), `OUTRIGGER_HULL_HOOK` 미설정(fast), `OUTRIGGER_PLACEMENT`는 배치표대로(기본 권고 `ecore`)
- 묶음 폴더 `07_results/S9/batch_B1-GRIDCONV_<stamp>/`, `--case`는 아래 ID 이름

### 3.2 행

| ID | `--case` | `--leg` | `--grid` [m] | `--normal-load` [N] | `--load-steps` | $N_1$ → $N_2$ [kN] |
|---|---|---|---|---|---|---|
| GC-1 | `GC1_J2_B_RL_1cm` | RL | 0.01 | 74850 | `0.97327989,1.0` | 72.85 → 74.85 |
| GC-2 | `GC2_J2_B_RL_0p5cm` | RL | 0.005 | 74850 | `0.97327989,1.0` | 72.85 → 74.85 |
| GC-3 | `GC3_J2_B_FL_1cm` | FL | 0.01 | 122010 | `0.98016556,1.0` | 119.59 → 122.01 |
| GC-4 | `GC4_J2_B_FL_0p5cm` | FL | 0.005 | 122010 | `0.98016556,1.0` | 119.59 → 122.01 |

- 하중 근거: $N_1$은 J2 설계 하중(P1 `design_loads_N` RL 72.81·FL 119.15 kN) 근처, $N_2 - N_1$ ≈ 2.0 / 2.4 kN은 B1 레벨링에서 LOC 뒤 다리 하중 증가 크기(가정).
- GC-1 argv 예(한 줄):
  `run_S9.py single-pad --soil J2 --pad-variant dwg_rear250 --level top --leg RL --joint fixed --grid 0.01 --threads 4 --normal-load 74850 --load-steps 0.97327989,1.0 --load-ramp 3 --step-ramp 2 --step-hold 8 --case GC1_J2_B_RL_1cm --out-root 07_results/S9/batch_B1-GRIDCONV_<stamp>`

### 3.3 행 유효성

| 코드 | 조건 | 실패 시 |
|---|---|---|
| V-1 | rc 0, `result.json` 있음, `load_steps.levels` 2개, 끝 시각 ≥ 21.0 − 1e-6 s | 1회 재실행(원 폴더는 `attempt1/`로 옮김). 다시 실패하면 `MISSING` |
| V-2 | argv가 3.2 표와 한 글자씩 같음, `meta.num_threads_chrono` 4, `placement.omp_wait_policy` `PASSIVE`, `meta.scm.grid_m` = 표 값, `meta.scm.SetSoilParameters`가 1절 J2 값, `meta.scm.plane_point_world_m` = (0, 0, 0), 패드 시작 위치 인자 없음(오프셋 0), `settle_end.x_mm`·`y_mm`의 절대값 ≤ 1e-3 mm(P1: 0 ~ 1e-18 mm), `hull_hook` requested = effective = `fast` | `INVALID`(다시 돌리지 않는다) |
| V-3 | 두 유지 끝 모두 $N_h$ ≥ 3이고 $b_{hull}$ 있음 | `INVALID` |

- 묶음 상태: 4행 모두 `VALID`면 `COMPLETE`. 하나라도 아니면 `UNDETERMINED`이고 판정을 내지 않는다(빈 집합 통과 금지). 짝(GC-1·2, GC-3·4)의 한쪽이 없으면 그 짝의 G-2~G-5는 `NA`이고 `NA`는 통과로 세지 않는다.

## 4. 판정 지표

$k$ = 1, 2(유지 끝 $t$ = 11.0, 21.0 s), 짝 $p$ ∈ {RL(GC-1·2), FL(GC-3·4)}.

| 코드 | 양 | 문턱 | 역할 |
|---|---|---|---|
| G-1 법칙 일치 | 행·유지 끝마다 $\varepsilon_1 = n\,|z^{node}_k - z_{ref,k}|/z^{node}_k$. $z_{ref}$는 기록된 $F$ = `Fz_scm_N`, $N_h$, $b_{hull}$로 계산(1절). $n\varepsilon$는 압력 법칙의 상대 잔차와 같다 | ≤ 0.5 %(8개 값 모두) | **관문.** 하나라도 실패하면 그 자리에서 멈추고 `REJECT`(G-2 이하는 계산만 하고 판정에 쓰지 않는다) |
| G-2 보정 수렴 | 짝·유지 끝마다 $|z_k/f_k(0.01) - z_k/f_k(0.005)|$, $z$ = `sinkage_geometric_m`, $f$는 그 유지 끝 기록으로 계산 | ≤ 1 mm(4개 값 모두) | **관문.** 초과하면 `REJECT` |
| G-3 증분 비율 | 짝마다 $|\Delta z/z_2\,(0.01) - \Delta z/z_2\,(0.005)|$ | ≤ 0.002(2개 값 모두) | **관문.** 초과하면 `HOLD` |
| G-4 원시값 | 짝마다 $z_2(0.01) - z_2(0.005)$, $\Delta z(0.01) - \Delta z(0.005)$, $z_1$ 차, 행마다 $f_1$, $f_2$, $N_h$, $b_{hull}$ | — | 기록. 5절 예측 확인에 쓴다 |
| G-5 계단 응답 | 짝마다 $r(t) = (z(t) - z_1)/(z_2 - z_1)$, $t \in [11.0, 21.0]$ s, `node_series` 0.1 s 표본(같은 시각끼리), $\max_t |r_{0.01}(t) - r_{0.005}(t)|$ | ≤ 0.05 | 기록. 넘으면 판정서에 `G5_FLAG`(판정 불변) |

- 판정
  - `PASS`: 묶음 `COMPLETE`, G-1·G-2·G-3 모두 문턱 안
  - `REJECT`: G-1 실패 또는 G-2 > 1 mm
  - `HOLD`: G-1·G-2는 통과, G-3 실패(증분이 격자에 따라 다름. B1 D-a·D-d의 전제가 흔들린다)
  - `UNDETERMINED`: 묶음 `UNDETERMINED`
- 반올림: 문턱 비교는 반올림 없는 배정밀도 값으로 한다. 표시는 mm 소수 셋째 자리, 비율 소수 다섯째 자리다.

## 5. 사전 예측

| # | 양 | 예측 | 근거 |
|---|---|---|---|
| E-1 | G-1 최대 $\varepsilon_1$ | ≤ 0.1 % | P1 V16bp 1 cm $|z/z_{ref} - 1|$ 0.0004 → $n\varepsilon$ 0.008 % |
| E-2 | G-2 최대 | ≤ 0.3 mm | 법칙이 맞으면 $z/f = z_{cont}$로 격자 무관. 남는 것은 동적·법칙 잔차(0.05 % × 130 mm ≈ 0.07 mm) |
| E-3 | G-3 최대 | ≤ 0.0005 | 법칙상 0(1절) |
| E-4 | G-5 최대 | ≤ 0.02 | 같은 $\tau$ 식, 법칙 잔차만 |
| E-5 | RL 원시 $z_2(0.01) - z_2(0.005)$ | **+2.7 mm**(136.2 − 133.4) | 위상 0 오프셋의 $f$: 0.01 m 1.0365, 0.005 m 1.0156, $z_{cont}$ 131.39 mm |
| E-6 | RL 원시 $\Delta z$ 차 | **+0.35 mm**(17.25 − 16.90) | 같음 |
| E-7 | FL 원시 $z_2$ 차 | **−0.80 mm**(95.06 − 95.86) | $f$ 0.9907 / 0.9991, $z_{cont}$ 95.94 mm |
| E-8 | FL 원시 $\Delta z$ 차 | **−0.08 mm**(9.06 − 9.14) | 같음 |

- 예측 확인: E-5~E-8 원시값이 각각 예측 ±0.5 mm 안이면 `예측 확인`, 아니면 `예측 불일치`(판정과 별개, 기록). `예측 불일치`이고 `PASS`이면 판정서에 위상 기록($N_h$, $b_{hull}$)과 2절 스캔의 차이를 적는다.
- 독립 재계산(control-expert, `gc_pred.py`): E-5 +2.750, E-6 +0.348, E-7 −0.808, E-8 −0.077 mm, $\Delta z/z_2$ RL 0.12665·FL 0.09532(격자 무관)로 위 예측과 맞는다.
- 확인 조건(사용자 결정): 원시값이 예측 ±0.5 mm 안. 기각 조건(사용자 결정): G-1 실패 또는 G-2 > 1 mm.

## 6. 결과별 처리

| 판정 | 처리 |
|---|---|
| `PASS` | B1 규칙 2.1 패드 격자 0.01 m 확정 근거로 쓴다. B1 0.4절에 이 판정서 sha를 적고 B1 봉인 절차(P5r4 결정 뒤)로 간다. D-c 보정 $z/f$를 격자 무관 양으로 쓴다 |
| `REJECT` | B1 봉인 보류. 원인 분석(법칙 잔차가 어느 유지 끝·격자에서 나는지, $N_h$·$b_{hull}$ 기록, 동적 지연 τ)을 terramechanics-expert·cad-expert와 한다. 0.01 m를 유지할지, 격자를 바꿀지, D-c 보정을 버릴지는 분석 뒤 사용자에게 묻는다 |
| `HOLD` | B1 봉인 보류. 증분 차의 원인을 분석하고, B1 D-a·D-d 문턱에 격자 증분 오차를 더할지 사용자에게 묻는다 |
| `UNDETERMINED` | 빠진 행만 1회 다시 돌린다(3.3). 그래도 없으면 사용자에게 묻는다 |

## 7. 판정 경로·비용·순서

- 경로 A: control-expert `gridconv_judge.py`(numpy·json만, 결과 전에 sha 고정, 이 계획서 봉인 뒤 결과 전에 커밋). 출력 `b1_gridconv_metrics_A.json`.
- 경로 B: terramechanics-expert가 `p1_levels.py` 형식으로 G-1·G-4를 따로 계산한다(경로 A 코드를 import하지 않음). 출력 `b1_gridconv_metrics_B.json`.
- 대조: 행 상태·판정은 완전 일치, 실수는 절대차 ≤ 1×10⁻⁹ m(비율 ≤ 1×10⁻⁹). 다르면 판정은 `UNDETERMINED`이고 정의 차이를 찾는다(도구를 결과에 맞춰 고치지 않는다).
- 판정서: `06_analysis/02_control/b1/b1_gridconv_judgement.md`(지표 표, 예측 대조, 두 경로 sha).
- 비용(가정, P1 V16 단일 패드 실측 us/step × 1.5(E) × 210,000 스텝): GC-1 약 260 s, GC-3 약 480 s, GC-2 약 1,300 s, GC-4 약 1,300~2,200 s. 직렬 약 0.9~1.2 h, 4행 동시면 가장 긴 행 기준 약 0.4~0.6 h(경합 미반영). 풀·동시 수는 compute-scheduler-expert 배치표로 정한다.
- 순서: 봉인 → 경로 A 스크립트 sha 고정 → 배치표 → 실행 → 경로 A → 경로 B → 대조 → 판정서. B1 Chrono 6행과 독립이고 P5r4 결정을 기다리지 않는다.

| 예측 재계산 파일 | sha256 |
|---|---|
| `evidence/gridconv_scan/gc_pred.py` | `d0d22b979f09e751e0bd53595c47851114648fab49ed116e7a9d2c9943619d3b` |
| `evidence/gridconv_scan/gc_pred.json` | `119f5059106b5e0752a644f08e787b94e575d091b9845ecfcc9f638965770d3b` |

## 8. 가정

- $N_2 - N_1$(RL 2.0·FL 2.42 kN), 유지 8 s(τ ≈ 0.4~0.5 s의 16배 이상), 램프 3 s·2 s, G-5 문턱 0.05, `HOLD` 등급, 경로 B 담당, 비용은 원본에 없어서 정한 값이다.
- 단일 패드 `--joint fixed`는 P1 V16bp와 같게 하려고 정했다. 레벨링 행의 구면 조인트·기울기·수평 이동은 이 시험 범위 밖이다(그 위상 변화는 B1 5.1 기록 M-11로 본다).
- 이 시험은 위상 0 오프셋 한 점이다. 위상 범위 전체는 2절 스캔(유도식)에 기대고, Chrono로 확인하지 않는다.
- 0.005 m 행이 기준이다. 0.005 m 자체의 위상 오차(후방 −0.8~+1.6 %, 전방 −0.5~+1.3 %)는 G-2가 $z/f$를 비교하므로 판정에 들어가지 않고, 원시값 G-4에만 남는다.
