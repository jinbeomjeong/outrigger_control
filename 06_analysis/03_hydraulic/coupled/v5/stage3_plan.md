# v5 3단계(Chrono) 계획 — D-3 확정본

작성: control-expert, 2026-11-07. 사용자 결정(11-07, 아래 0절)을 반영한 **확정본**이다. 판정 규칙은 `v5_criteria_rev6.md`(개정 6), 구현 명세는 `stage3_impl_spec.md`에 있다.

| 항목 | 내용 |
|---|---|
| 기준 | 봉인본 → 개정 1~5 → **개정 6**(`v5_criteria_rev6.md`, SHA-256 `fd511703…`, **봉인 2026-11-07 11:13:35 +09:00**) |
| 코드 | master **b6b295c**(M2 r5 `flow_limited_r5`, 제어기 `final_C4G2`, ③ `tracked_bound` v2는 기본 꺼짐 옵션). 이후 `extend_bound_check` 커밋 예정. 3단계 실행 코드는 그 커밋 뒤 회귀를 거쳐 고정한다 |
| 1·2단계 | r5 재실행·재판정 통과(`stage1_judgement.md` R5절, `stage2_judgement.md` 14~17절) |
| ③ | 사용자 결정(11-07): 기본 꺼짐 유지, 채택은 3단계 뒤. **3단계 Chrono는 ③ 꺼짐 VB로 돌린다**(T4·T5에 켬 재생 `T4-P3` 기록 덧붙임) |
| 시작 | **조용한 비용 측정(7.2절) 뒤 사용자 승인을 받아 시작한다** |
| 제어 | 음되먹임, $T_s$ 0.1 s, 출력 지연 $d$ = 1. 강체 L2b-NSC(강체 크롤러, 물리 스텝 $10^{-4}$ s), 토양 SCM(`run_S9`) |
| 단위 | 힘 kN, 압력 bar(게이지), 시각 s, 행정 mm, 벽시계 s |
| 앞 단계 | 1단계 통과(`stage1_judgement.md` R4절), 2단계 통과(`stage2_judgement.md` 13절). 대체 경로 `잠정` |

## 0. 사용자 결정 (11-07)

| # | 결정 | 계획 반영 |
|---|---|---|
| 1 | 범위 **(다)**: 25건 + 토양 VB 3행 + V0v 3행 | 토양 VB = `V5-VB` 3행(S1·S6·S8), V0v = 같은 3행 + `--valve-tau-s 0.1`만 |
| 2 | 계열 $\mathcal F$: FL FS24 $F_s$ 0 READY δ 0.05 VB + V0 짝 | `G1R_FS24_FL_top_o050_Fs0` VB·V0 |
| 3 | 잡음 `g8|22`·`g6|56`: 하네스 시드 확장, VB·V0 각 25시드 | 100 하네스 실행, Chrono 이식 없음 |
| 4 | R12 V0 위상 0.05 짝 1건 추가 | `E_G4_Fs4_ph0.05` V0(C4G2) |
| 5 | 순서대로 자동 진행: 개정 6 봉인 → 구현·회귀 → 조용한 비용 측정 → 실행. 회귀 실패, 비용 초과, 멈춤 조건이면 멈추고 묻는다 | 7.4절 진행 관문 |
| 6 | (11-07, hydraulics-expert H-a 답 뒤) **L2b 모델을 먼저 고친다.** 신장 뒤 잠금에서 M2 추적 압력을 앵커로 쥐게 바꾼다 | 0.1절 |
| 7 | 앵커 식 B안 $p_{r0}=\max(p_{ext}+\max(p_{tr}-p^*,0),p_{floor})$. L2b와 하네스를 같은 식으로, 법칙 키 `flow_limited_r5`. 누설 없음, RET는 $p_{ret}$ 유지 | 0.1절, 개정 6 14절 |
| 8 | 1·2단계 VB·LS 약 3,300건을 r5로 재실행·재판정, V0 재사용 | 0.2절 |
| 9 | 대체 시작값 ③ 보강을 병행 설계(기본 꺼짐, 채택은 묻는다) | `p3_extend_start_spec.md` |
| 10 | 이후는 추천값대로 자동 진행 | 0.2절 순서 |

### 0.1 L2b 신장 잠금 앵커 수정과 일정 지연 (결정 6)

| 항목 | 내용 |
|---|---|
| 발견 | 지금 L2b는 신장 뒤 잠글 때 M2 추적 압력을 버리고 YAML `p_r0_after_extend_Pa` 2 bar(가정)로 로드 압력을 재설정한다(`l2b_rod_side.py:139-145`, `rod_chamber.py:315`·`:524-527`). 이는 M2 r3·r4의 "u = 0이면 유지" 가정과 맞지 않는다. 체크가 닫히면 로드실은 추적 압력으로 갇힌다(누설 시상수 약 120~300 s, 가정). hydraulics-expert H-a, scratchpad `hyd_s3\H_answers.md` |
| 영향 | 짧은 신장(수축 잠금 뒤 누적 신장 < 약 0.4 mm) 뒤 잠긴 다리의 로드 압력, 헤드 판독, 무릎 힘(FL s 0.3 m에서 2 bar 6.1 kN 대 34.8 bar 74 kN), T4의 위험(4절) |
| 수정 명세 | hydraulics-expert `hyd_s3\r5_spec.md`(B안, 결정 7). L2b는 cad-expert, 하네스는 python-expert가 구현한다 |
| 확인 3가지의 답 | (1) M2 끔은 2 bar 규칙 그대로(비트 동일, B-2·B-4·B-5). (2) 하네스도 같은 식으로 고친다 → 1·2단계 M2 켬 행 재실행(결정 8). (3) 법칙 키 `flow_limited_r5` |
| H-a | T4-A를 없애고 앵커 계수기로 대신한다(개정 6 4.5절). 대체 시작값 ③ 보강은 `p3_extend_start_spec.md`(기본 꺼짐 옵션, 채택은 묻는다) |

### 0.2 갱신 일정 (결정 6~10)

| 순서 | 일 | 담당 | 시간(추정) | 관문(어기면 멈추고 묻기) |
|---|---|---|---|---|
| 1 | r5 구현: L2b(cad-expert), 하네스(python-expert), 단위 시험 A-1~A-8·A-H | 구현 담당 | 반나절 | A 시험 통과 |
| 1′ | ③ 옵션 구현(python-expert, 기본 꺼짐, T-P3-1~5) | python-expert | 1과 병행 | T-P3-1 비트 동일 |
| 2 | 회귀: B-2, B-4, B-5, B-7, S7 L2b, 하네스 V0 시드 0~4, M2-12·14b·14c(r5) | 메인 세션 | 1~2 h | 개정 6 14.4절(H-16) |
| 3 | **개정 6 봉인 — 끝**(2026-11-07 11:13:35 +09:00, SHA-256 `fd511703…`, 코드 c4ca6bb) | control-expert | - | 1·2단계 재실행이 r5 키를 판정에 쓰려면 개정 6이 필요하다(개정 5 #1은 r4만 허용). 그래서 재실행 **전**에 봉인한다. 3단계 정의도 함께 봉인한다(3단계 결과 없음) |
| 4 | 1·2단계 r5 재실행: 1단계 1,030 + $t_a$ 1, 위상 분포 32, 격자 768, 잡음 1,503 = 3,334 | 메인 세션(compute-scheduler) | **약 3~4 h**(r4 재실행 3시간 20분 실측, 20 worker) | 오류 0 |
| 5 | 재판정(개정 1~6 규칙, 위상 분포 규칙 그대로) + Dg-2(`T4h-P3`) + Dg-3(③ 옵션 폐루프 약 150실행, 약 15분) | control-expert / 메인 세션 | 1~2 h | H-1~H-11, H-7(T4h 앵커 위험, 14.5절) |
| 6 | ③ 채택 여부 질문(Dg 결과와 함께). 채택이면 개정 7 | 사용자 | - | - |
| 7 | 3단계 구현(`stage3_impl_spec.md`, r5 위) + 회귀 | cad-expert | 반나절 | H-16 |
| 8 | 조용한 비용 측정 P-A·P-B | 메인 세션 | 1.5 h | 7.2절 |
| 9 | 하네스 시드 확장 100 + Chrono 34건(③ 꺼짐 VB, 비용 측정 뒤 사용자 승인) | 메인 세션 | 10~25 h(7.3절, 기준 178,126 s) | 개정 6 멈춤 조건 |
| 10 | 3단계 판정 | control-expert | 2~3 h | - |

- 1·3단계 사이 지연: 원래 계획 대비 **약 1일**이다(r5 구현 반나절 + 회귀 + 재실행 3~4 h + 재판정).
- 사용자 지시 순서("r5 구현 → 재실행 → 재판정 → 개정 6 봉인 → 3단계")와 다른 점: 개정 6 봉인을 재실행 **앞**으로 옮겼다. 이유는 위 3번이다. 재실행 결과를 보기 전에 법칙 키와 재판정 규칙(14절)을 봉인해야 결과를 본 뒤 규칙을 고르는 일이 없다.
- 4번에서 T4h가 r5 앵커 때문에 초과하면 H-7로 멈춘다. 이때 같은 기록의 `T4h-P3` 값과 함께 ③ 채택을 묻는다(6번을 앞당김).

## 1. 공통 인자

| 이름 | 인자 | 근거 |
|---|---|---|
| VB 강체(`run_S8C`) | `--flow-eta-v 0.85 --flow-dp-comp-bar 10 --flow-dp-unload-bar 20 --flow-width-bar 1 --flow-law priority --rod-release-force --lock-overlap-ratio 0.02 --lock-closing-delay-s 0.05 --lock-window-follows-plant` | `s9_batch.V5_VB_ARGS` − `valve_tau_s`. 강체 행은 행 정의가 밸브 0.1 s를 켠다(`run_S8C.py:1122`) |
| VB 토양(`run_S9`) | 위 + `--valve-tau-s 0.1` | `s9_batch.v5_vb_argv()` |
| LS1 / LS4 | VB의 LC 값을 1 % / 50 ms, 2 % / 100 ms로 | 봉인 8절 |
| V0 강체 | 옵션 없음(`final_C4G2` 프리셋) | B-2·B-4 비트 동일 대상 |
| V0v 토양 | 저장 행 argv + `--valve-tau-s 0.1`만 | 결정 1 |
| 강체 실행 형식 | `run_S8C.py run --set <set> --only <id> --tag v5s3_<설정>_<id> --approved --workers p7 <인자>` | 비용 probe 형식 |
| 토양 실행 형식 | `run_S9.py level …`(저장 행 argv) `--expect-controller final_C4G2` | `s9_batch` 행 |
| M2 법칙 키 | M2 켬 행 `m2_law: flow_limited_r5`, 끔 행은 키 없음 | 개정 6 2절 #9 |

## 2. 최종 행 목록 (Chrono 34건)

### 2.1 봉인 13.5의 25건

| # | 묶음 | 행 | 실행기·세트 | 설정 | 판정(개정 6) |
|---|---|---|---|---|---|
| 1~12 | T4·T5 | K0V_top_fup3.5_Fs0, K0_top_fup3.2_Fs0, K0V_top_roll5.5_Fs0, K0_top_fdown3.2_Fs0, K0V_top_fdown3.5_Fs0, E_G4_Fs8, K0_top_rpBop_Fs0, E_RE1bF_Fs0, E_RE1bF_Fs8, K8_top_rpB_Fs8, S_top_fdown3.5_wika_Fs8, K8_top_fdown3.5_Fs8 | run_S8C `p1r` | VB | 2절 T4·T5 |
| 13~15 | T4 감도 | K0V_top_fup3.5_Fs0, E_G4_Fs8, E_RE1bF_Fs8 | 같음 | LS1 | 같음 |
| 16~18 | T4 감도 | 같은 3행 | 같음 | LS4 | 같음 |
| 19, 20 | ④ R12 | E_G4_Fs4, E_G4_Fs4_ph0.05 | run_S8C `p1r` | VB | 기록(6절) |
| 21~25 | ⑤ S6 | `P3b_J2_B_top_Fs4_m1p1_t180_seed{20261026,27,28,29}`, `…_seed20261026_flow` | run_S9 level(`V5-S6SEED` 그대로) | 끔 ×4(램프 경로), 유량 0.85 ×1 | 기록(13.6) |

### 2.2 결정으로 더한 9건

| # | 묶음 | 행 | 실행기 | 설정 | 짝 | 판정 |
|---|---|---|---|---|---|---|
| 26 | 토양 VB | S1 `P3b_J1_B_top_Fs4` | run_S9(`V5-VB`) | VB | 32 | 기록 행(7절 멈춤 조건) |
| 27 | 토양 VB | S6 `P3b_J2_B_top_Fs4_m1p1_t180` | 같음 | VB | 33 | 같음 |
| 28 | 토양 VB | S8 `S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0` | 같음 | VB | 34 | 같음 + 봉인 6절(F-5) |
| 29 | $\mathcal F$ | `G1R_FS24_FL_top_o050_Fs0` | run_S8C(새 세트 `v5rec`) | VB | 30 | 기록 행 |
| 30 | $\mathcal F$ | 같음 | 같음 | V0 | - | 짝 |
| 31 | ④ 짝 | E_G4_Fs4_ph0.05 | run_S8C `p1r` | V0(C4G2) | 20 | 기록 |
| 32~34 | 토양 V0v | 26~28과 같은 행, `_v0v` | run_S9(`V5-V0V`) | V0v | - | 짝 |

- 토양 VB 3행은 `V5-VB` 정의를 그대로 쓴다(`check-sources V5-VB` ok, 차이 = VB 인자 10개).
- 21번은 저장 S6와 시드가 같지만 C4G2 전 제어기 실행이므로 다시 돈다.
- ④ V0 위상 0은 저장 FINAL-R-C4G2 E_G4_Fs4(C4G2, 856 s E)를 쓴다.

### 2.3 하네스 (결정 3)

| 키 | 설정 | 시드 | 건 |
|---|---|---|---|
| `g6|56` = `ref|J2|top|Fs0` | VB r5, V0 | L2, 시드 색인 0~24 | 50 |
| `g8|22` = `slope|rpB|top|4.0|FR|raised|140.0` | VB r5, V0 | 같음 | 50 |

판정은 개정 6 8절(기록, 시드 0~4는 2단계 저장 행과 해시 대조).

## 3. 토양 밸브 켬 기준

| 항목 | VB(26~28) | V0v(32~34) |
|---|---|---|
| argv | `V5-VB` 행 | 저장 FINAL-REP / FINAL-REP-X argv + `--valve-tau-s 0.1` |
| `check-sources` 허용 차이 | VB 인자 10개 | `valve_tau_s` 하나 |
| 밸브 | $\tau_v$ 0.1 s, `amp_ramp="none"`, 명령 램프 꺼짐 | 같음 |
| 뜻 | VB − V0v = 유량 + M2 + LC 효과(하네스 VB − V0와 같은 대비) | V0v − 저장 V0(램프) = 밸브 경로 효과(기록) |

V0v의 뜻(hydraulics-expert H-c, 개정 6 8.1절)
- 옵션은 하네스 V0와 같다.
- 로드 판독 법칙, SCM, $F_s$ 4 kN, 센서·시드는 다르다.
- 그래서 V0v 값을 하네스 V0 값과 직접 대조하지 않는다. VB − V0v 짝 차의 방향과 크기만 하네스 VB − V0와 비교한다.

## 4. T4·T5 기록 사양 요약

자세한 것은 `stage3_impl_spec.md`.

| ID | 내용 |
|---|---|
| R-1 | M2 해제 기록(해제마다 Δ 사용값·기준값, $p_{start}$, $\hat p_{start}$, $p_{end}$, $w_{end}$, $k_h$, 이동 합) |
| R-2 | M2 잘림 시각 + Chrono $t_{lift}$로 pre/post 분리 |
| R-3 | 1 ms 크롤러 수직력 |
| R-4 | Chrono `lock_window_alignment`(잠금 사건 = `law_locked` 전이) |
| R-5 | 1 ms `m2_p_hat_Pa`·`m2_shift_cum_m` |
| R-6 | `chrono_t45_replay.py`(T4-0, T4, T5) |

하네스 T4h 꼬리(미잠김 3,416 표본, 최대 8.23 kN)는 Chrono T4가 `law_locked` = 0 표본까지 판정해서 대신한다.

**사전 등록 위험**(수계산, 판정 아님)
- r3·r4 법칙의 신장 감압은 유량 제한이다. 34.8 → 13 bar가 1 % $v_{max}$에서 약 0.99 s, 10 % $v_{max}$에서 약 0.10 s다(M2-10 1.188 s에서 환산).
- 이동량으로는 FL 0.145~0.325 mm, RL 0.184~0.380 mm다(행정 0.6~0.02 m, hydraulics-expert H-a). 그래서 수축 잠금 뒤 누적 신장이 약 0.4 mm 미만이면 잠금 때 로드 압력이 대체 시작값 13 bar보다 높을 수 있다. 그 경우 T4 초과는 최대 FL 8.23 kN, RL 6.86 kN이다.
- hydraulics-expert 답(11-07): 지금 L2b는 신장 잠금 때 2 bar로 재설정하므로 **잠긴 표본에서는 위험이 가려진다.** 꼬리(`law_locked` = 0)에서만 드러난다(꼬리 길이 ≤ 0.02 $v_{max}$에서 0.050 s, 1.0 $v_{max}$에서 0.441 s).
- 결정 6으로 L2b를 고치면 잠긴 표본에서도 드러난다. 수정 뒤 T4에 앵커 보정 재생(T4-A)이 필요한지는 hydraulics-expert 판단을 받아 개정 6 H-a로 정한다.
- T4 초과가 나오면 H-7로 멈춘다. 대체 시작값 ③ 보강은 제어기 결정이라 별도로 묻는다.

## 5. L2b r4 확인

개정 6 6절. 해제마다 실측 이동 합 대 $S_{M2}=A_{ann}(\hat p_{start}-\hat p_{end})/k_h$, 1 hook Δ 차, 뜬 다리 재접근의 이중 계산 여부, 이륙 뒤 잘림.

## 6. ④ 표 구성

| 위상 | 저장 켬(`final_SGS_R4`) | 저장 끔(`final_SGS_R4`) | V0 C4G2 | VB C4G2 |
|---|---|---|---|---|
| 0 | 12.42 | 11.14 | FINAL-R-C4G2 저장 | 19번 |
| 0.05 s | 10.92 | 11.83 | 31번 | 20번 |

값: RR 창 뒤 1 ms 최소와 0.5 s 평균 [kN]. 기록만.

## 7. 비용과 일정

### 7.1 오염된 probe(참고, `07_results/S9/batch_V5-PROBE_20261106/_sample`)

| probe | 내용 | 벽시계 [s] | 다른 부하 |
|---|---|---|---|
| probe_flow | 토양 S1 유량, 46 s | 3,610 | 28.5 % |
| probe_vb | 토양 S1 VB, 46 s | 4,316 | 40.5 % |
| probe_rigid_flow | K24_top_fdown3.5_Fs4 유량 | 1,205 | 72.1 % |
| probe_rigid_vb | 같은 행 VB | 1,300 | 72.1 % |

조용한 V0 기준: FINAL-R-C4G2 K24_top_fdown3.5_Fs4 751 s(E), P 환산 694 s.

### 7.2 조용한 재측정 (결정 5의 3번째 단계, 메인 세션이 compute-scheduler로)

| probe | 명령 | 예상 | 기준(이보다 크면 멈춤) |
|---|---|---|---|
| P-A | `run_S8C.py run --set rest --only K24_top_fdown3.5_Fs4 --tag probe_rigid_vb_quiet --approved --workers p7` + VB 강체 인자 | 약 944 s(P) | > 1,230 s(추정 × 1.3) |
| P-B | `run_S9.py level --soil J1 --pad-variant dwg_rear250 --level top --fs-kN 4 --grid 0.01 --crawler-grid 0.04 --settle-dashpot zrp --threads 4 --duration 46 --pressure-grade normal …`(probe_vb와 같은 argv, 구현 뒤 코드) + VB 토양 인자 | 약 3,600 s(probe_flow 오염값과 같은 수준) | > 4,700 s |

- 둘 다 단독, P코어 고정 + EcoQoS 해제, `sample.py` 동반. 벽시계·CPU·RSS만 읽는다(개정 6 9절).
- 두 값으로 7.3 표를 다시 계산한다. 다시 계산한 34건 합이 198,000 s(개정 6 10절 봉인값, 앞 계획 152,100 s × 1.3)를 넘으면 멈추고 묻는다. 계획 기준값은 7.3절의 178,126 s다.

### 7.3 34건 예상 (P코어 기준)

**기준값: `s9_batch.py list V5-STAGE3`의 `est_s` 순차 합 178,126 s(49.5 h).** 배치 도구가 쓰는 값이라 이것 하나를 계획 기준으로 둔다(11-07, master b6b295c에서 확인).

| 묶음 | 건 | `est_s` 합 [s] | 앞 계획 추정 [s] | 차이 원인 |
|---|---|---|---|---|
| T4·T5 VB | 12 | 10,076 | 12,400 | 행 정의가 p1r 저장 벽시계 기반 추정을 쓴다(앞 계획은 FINAL-R-C4G2 대리값 × 보정) |
| T4 감도 LS1·LS4 | 6 | 6,176 | 7,100 | 같음 |
| ④ VB 2 + V0 1 | 3 | 3,094 | 3,100 | - |
| ⑤ S6 시드 | 5 | 79,380 | 58,800 | **끔 4건의 `est_s`가 P 16,800 s**(FINAL-REP-X의 풀 추정값)로 실측 11,954 s(P 1슬롯)보다 1.4배 크다. 켬 1건은 12,180 대 11,026 |
| 토양 VB | 3 | 38,540 | 37,300 | COUPLED 풀 추정 + 180 s 대 COUPLED 실측 × 1.2 |
| 토양 V0v | 3 | 38,540 | 31,100 | `est_s`가 VB 행과 같은 값(밸브만 켬 차이를 반영하지 않음) |
| $\mathcal F$ VB + V0 | 2 | 2,320 | 2,300 | - |
| **합** | **34** | **178,126(49.5 h)** | 152,100 | 대부분(약 +19,400 s)이 S6 끔 4건의 풀 추정값이다 |
| 하네스 시드 확장 | 100 | 하네스 약 10분(20 worker) | | |

- 실측(조용한 P 1슬롯) 쪽으로 보면 합은 약 158,700 s다(S6 끔 4건을 11,954 s로 바꾼 값). `est_s`는 그보다 보수적이다.
- **비용 관문은 봉인값을 그대로 쓴다.** 개정 6 10절은 "다시 계산한 34건 합 > 198,000 s면 멈춤"이다. 기준값 178,126 s 대비 여유는 1.11배다. P-A·P-B로 다시 계산한 합을 이 198,000 s와 비교한다.

**완료 시간**(기준값 178,126 s)
- 동시 2건(가장 긴 작업 먼저): 약 89,000 s ≈ **25 h**.
- 권고 배치: 토양 11건(`--threads 4`)을 P 풀에 4건씩, 강체 23건(단일 스레드)을 E 풀에 겹친다. 약 **10~13 h**(추정). 배치표는 compute-scheduler-expert가 정한다.
- 30분을 넘으므로 long-running-task-monitor 15분 주기 점검을 한다.
- **시작은 조용한 비용 측정 뒤 사용자 승인을 받아서 한다.**
### 7.4 진행 순서와 관문 (결정 5)

| 단계 | 일 | 담당 | 관문(어기면 멈추고 묻기) |
|---|---|---|---|
| 0 | r5 구현·회귀, 개정 6 봉인, 1·2단계 r5 재실행·재판정, ③ 채택 질문 | 0.2절 순서 1~6 | 0.2절 관문 |
| 1 | (개정 6은 0.2절 3번에서 봉인) | - | - |
| 2 | 구현(`stage3_impl_spec.md`) | cad-expert(+ python-expert 도구) | 단위 시험, T4-0을 3단계 밖 V0 기록에서 통과 |
| 3 | 회귀 B-2·B-4·B-5·B-6·B-7·B-8, 새 묶음 `check-sources` | 메인 세션 | 모두 통과 |
| 4 | 조용한 비용 측정 P-A, P-B | 메인 세션 | 7.2 기준 |
| 5 | 하네스 시드 확장 100 | 메인 세션 | 오류 0, 시드 0~4 해시 일치 |
| 6 | Chrono 34건(③ 꺼짐 VB. 비용 측정 뒤 **사용자 승인**을 받아 시작) | 메인 세션 | 실행 중 저장소 코드 수정 금지(또는 고정 사본). 오류 0. 실행 중 멈춤 조건(H-7, H-9, 6절 (c), 7절)은 판정 때 본다 |
| 7 | 판정 `stage3_judgement.md` | control-expert | Python + Julia 집계 대조 |

## 8. 수행한 작업

| 명령 | 결과 |
|---|---|
| `Chrono-dev python -I -B 04_scripts\02_chrono\s9_batch.py list V5-VB` / `V5-S6SEED` | 3행 / 5행 |
| `… s9_batch.py check-sources V5-VB` / `V5-S6SEED` / `COUPLED_eta085` | 모두 ok |
| scratchpad `ctrl_v5s3\t45_rows.py`(Chrono-dev) | 13.5 12행 + E_G4_Fs4·_ph0.05 모두 `p1r`, `pilot_check` |
| scratchpad `ctrl_v5s3\probe_summary.py`, `batch_walls.py`, `noise_keys.py`(dynamics-dev) | 7.1 표, 저장 벽시계, 잡음 키 |

scratchpad: `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\ctrl_v5s3\`.

## 9. 가정

| 가정 | 값 |
|---|---|
| 강체 VB 비용 | (V0 + 180 s) × 1.08 |
| 토양 VB/유량, V0v/유량 | 1.2, 1.0 |
| 일정 오차·비용 멈춤 문턱 | ±30 %, 계획 × 1.3 |
| $\mathcal F$ 위상 | 0.050 s |
| 잡음 시드 수 | 25(사용자 결정) |

## 10. 위임

| 대상 | 일 |
|---|---|
| cad-expert(+ python-expert) | `stage3_impl_spec.md` 전부 |
| hydraulics-expert | 개정 6 보류 H-a·H-b·H-c(메인 세션이 묻는 중) |
| dynamics-expert | 개정 6 보류 D-a·D-b(같음) |
| compute-scheduler-expert | P-A·P-B 단독 배치, 34건 + 하네스 100 배치표 |
