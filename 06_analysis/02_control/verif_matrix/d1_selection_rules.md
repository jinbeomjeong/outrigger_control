# D-1 검증 행렬: Chrono 선별 규칙과 판정 기준 (사전 봉인)

작성: control-expert, 2026-11-08.

> **상태: 봉인(2026-11-08).** SHA-256과 봉인 시각은 같은 폴더 `d1_selection_rules.sha256`에 있다. 이 파일은 더 고치지 않는다. 바꿔야 하면 `d1_selection_rules_rev<N>.md`를 덧붙인다(v5 기준 선례).
> - **결과를 보기 전의 봉인이다.** D-1 하네스(H-R·H-S)는 아직 돌지 않았고 하네스 D-1 지원 코드(python-expert P-1~P-6)도 아직 없다. 본 것은 행 정의 문서, Chrono 행 정의 코드(`d1_chrono_rows.py`), 사용자 결정뿐이다.
> - 사용자 결정(`00_docs/decision_log.md` 4절): D-1~D-5(11-07), U1~U8(11-08), PS-a 검증 경계 제외·경사 PS-c `dsb_gated_off` 기록 행·S-01/02 후보에 fup-rec 포함(선별 규칙에 맡김)(11-08), ③ revision 4 채택 = VB 제어기 `final_C4G2_P3`(11-08, v5 기준 개정 8).
> - **D-5**: 판정 기준은 기존 명세 기준 그대로다. 이 문서가 새로 정하는 것은 선별 규칙(2~7절)과 크롤러 ×3 옮겨 읽기 규칙(8절)뿐이다. 선별 규칙은 어떤 행의 판정도 바꾸지 않는다.

## 0. 입력과 출처

| 입력 | 위치 | SHA-256(앞 16자리) |
|---|---|---|
| 행 정의 최종표(dynamics-expert, U1~U8 반영) | control-expert 세션 scratchpad `dyn_d1\d1_rows_final.md` | `578325c70d4cc359` |
| dynamics 확인(U7 2×2 규칙 원문 3.3절) | 같은 폴더 `d1_dynamics_check.md` | `8c7065522635cd62` |
| 제안서(선별 규칙 초안 6절) | scratchpad `ctrl_v5s3\verif_matrix_proposal.md` | `c75135c29dc8055e` |
| Chrono 행 정의 | `04_scripts/02_chrono/d1_chrono_rows.py`(master 3d848a7) | `6aa0e64659708ea2` |

scratchpad 파일은 지워질 수 있으므로 이 문서가 쓰는 정의는 아래에 모두 옮겨 적었다. 행 정의표의 "③ 꺼짐·`final_C4G2`" 고정 칸은 v5 기준 개정 8(VB = `final_C4G2_P3`, V0 = `final_C4G2`)이 대신한다.

## 1. 규약·기호

| 기호 | 뜻 | 단위·값 |
|---|---|---|
| 기체 축 | x 전방, y 좌측, z 위. roll > 0 = 좌측 위, pitch > 0 = 앞내림 | — |
| (roll, pitch) | 바닥 평면 자세, $R_f = R_y(\theta)R_x(\varphi)$(하네스 `Plant` 규약). 값은 `s9_soil_slope._scaled_slope`의 float | deg |
| $F_{min}$ | 다리 최소 실린더 순 힘 | 9.415 kN |
| $s_{end}$ | 행정 끝 판정 기준 | 0.6848 m |
| $\varepsilon$ | 하네스 위상 오프셋 | {0, 2×10⁻³} |
| VB / V0 | v5 VB 플랜트 + `final_C4G2_P3` / 옵션 끔 + `final_C4G2` | — |
| K | 하네스 크롤러 강성 배율(U6: 법선·접선 ×3, 감쇠 ×√3, 정착 맵 ×1) | ×1, ×3 |
| T / M / B | 오거 상단 / 중단 / 하단 | — |
| 되먹임 | 음되먹임 $u=r-y$ 경로, 10 Hz($T_s$ 0.1 s), 출력 지연 $d$ = 1(R8 C2) | — |

## 2. 범위: 무엇을 고르는가

`s9_batch list D1-CHRONO` 후보 22행(C2 10, C1 4, S 8) + `D1-PSC` 선택 7행 가운데 아래 세 가지만 하네스 결과로 정한다. 나머지는 고정 행이다.

| 선별 | Chrono 칸 | 후보(Chrono 행 이름) | 하네스 근거 행 |
|---|---|---|---|
| S1 roll 부호 | C2-03(M), C2-07(B) | `D1C2_<level>_roll4.4_Fs4` (4.4, 0) / `D1C2_<level>_rollm4.4_Fs4` (−4.4, 0) | H-R-0, 같은 오거, roll+op / roll−op, K ×1·×3, $\varepsilon$ 2개, **VB** |
| S2 연약 경사 | S-01(M), S-02(B) | `D1S_J1_B_<level>_Fs4_r1p925_p1p4`(diag-rec), `..._rm2p64_p0`(roll−rec), `..._r0_pm2p8`(fup-rec, `ASSUMED_BOUNDARY`) | H-S-0, J1, 같은 오거, 같은 세 경사, $\varepsilon$ 2개, **VB** |
| S3 PS-c 포함 | D1-PSC | 기준 `D1PSC_J1_B_top_Fs4_sp{FL,RL}J1_base`, 사건 `D1PSC_J1_B_top_Fs4_FL_{cslow,cmid,cedge,cfast}`, `..._RL_cmid` | H-S-C, J1, 상단, 평지, 같은 다리·프로파일, $\varepsilon$ 2개, **VB** |

고정 행(선별 없음): C2-01·02·04·05·06·08, C1-09~12(크롤러 ×3 L1 V0 기록, 8절 규칙으로 읽음), S-03·04. 하네스 기록 행(H-R-A-stop, H-R-A-J2, H-R-A-S1, H-S-A-J2, H-S-C-g `dsb_gated_off`)은 선별에 쓰지 않는다. V0 실행은 선별 순위에 쓰지 않고 4.3 기준선 실패 판정과 8절에만 쓴다.

## 3. 입력 필드 (P-6 결과 기록, 실행마다)

하네스 결과 기록의 `d1` 묶음에 아래 이름으로 넣는다(python-expert P-6). Chrono 행의 같은 양은 Chrono 판정 도구가 같은 이름으로 낸다(9절 짝 기록용). **필드가 하나라도 없는 실행이 있으면 선별 스크립트는 선별하지 않고 끝난다(종료 코드 2).**

| 필드 | 뜻 | 단위 |
|---|---|---|
| `d1.key` | (묶음 ID, 오거, 지반 또는 K, 바닥 (roll, pitch), 부분 침하·다리·프로파일, 플랜트 VB/V0, $\varepsilon$) | — |
| `d1.verdict` | 그 행 묶음의 **기존 판정기** 결과(강등 규칙 적용 뒤): `pass` / `fail` / `allowed_stop`(행 정의가 `stroke_limited_stop`을 허용한 행에서 그 종료). FLAG는 `pass` | — |
| `d1.fail_items` | 실패 항목 이름 목록 | — |
| `d1.F_judged_min_N` | 기존 판정이 $F_{min}$과 비교하는 양: H-R = 크롤러 이륙 뒤 실행 끝까지 네 다리 1 ms 실제 $F_{cyl}$ 최소(D8·P), H-S = P3-3 이탈 뒤 최소, PS-c = 426.3 E-3 양 | N |
| `d1.F_first_level_min_N` | 첫 LEVEL 구간(처음 LEVEL에 들어간 때부터 첫 DONE까지, DONE이 없으면 실행 끝까지) 네 다리 1 ms 실제 $F_{cyl}$ 최소(P-6) | N |
| `d1.t_ready_s`, `d1.t_ready_limit_s` | 기존 판정이 한계와 비교하는 첫 READY 시각(같은 기준점)과 그 한계(H-R 평지 90 / 경사 120 s, H-S 평지 100 / 경사 120 s). READY 없음 = `null` | s |
| `d1.att_judged_deg` | 기존 판정이 0.2°와 비교하는 자세 양: H-R = D8 끝 자세 양, H-S = P3-4 `p34_absmax_overall_deg`, PS-c = E-5 끝 1 s 평균 max(\|roll\|, \|pitch\|) | deg |
| `d1.stroke_max_m` | 실행 전체·네 다리의 실제 모터 행정 최대(P-6) | m |
| `d1.imu_R_c` | IMU 환산 $R_c$(정착 맵 `crawler_from_floor`, P-6). 기록 | — |
| `d1.dsb75_events` | `INFO_DIFF_SINK_HOLD`·`INFO_DIFF_SINK_RELEASE` 사건(시각, 축, \|r\| mm/s, 해제 사유)(P-6) | — |
| `d1.j_p3` | v5 기준 개정 8·9의 J-P3 상태(`pass` / `H-7` / `no_rod_reading` / 설정 결함) | — |

## 4. 여유 $m$과 순위

### 4.1 실행마다의 여유

$$m_F=\frac{F_{judged}-F_{min}}{F_{min}},\quad m_T=\frac{T_{lim}-t_{READY}}{T_{lim}},\quad m_a=\frac{0.2°-a}{0.2°},\quad m_s=\frac{s_{end}-s_{max}}{s_{end}}$$

| 묶음 | $m$ |
|---|---|
| H-R(D8·P), H-S(P3) | $m=\min(m_F, m_T, m_a, m_s)$. READY가 없으면 $m_T$를 빼고 나머지 셋의 최소 |
| PS-c(H-S-C) | $m=\min(m_F, m_a, m_s)$(READY 복귀는 E-5 판정에 이미 있다) |

| 기호 | 필드 |
|---|---|
| $F_{judged}$ | `d1.F_judged_min_N` |
| $t_{READY}$, $T_{lim}$ | `d1.t_ready_s`, `d1.t_ready_limit_s` |
| $a$ | `d1.att_judged_deg` |
| $s_{max}$ | `d1.stroke_max_m` |

### 4.2 후보 값(여러 실행을 묶을 때)

- 후보 하나의 실행 집합: S1 = (K ×1, ×3) × ($\varepsilon$ 2개) = 4 실행, S2·S3 = $\varepsilon$ 2개 = 2 실행. 모두 VB.
- 후보 등급 = 실행 등급의 최악(`fail` < `allowed_stop` < `pass`). 후보 $m$ = 실행 $m$의 최소. 후보의 동점 보조값은 $m$이 최소인 실행의 값을 쓴다.
- S1에서 K ×1·×3을 함께 묶는 이유: Chrono C2는 강체 NSC 크롤러(K → ∞ 극한)라 하네스의 어느 한 배율과도 같지 않다. 두 배율 중 나쁜 쪽을 쓴다.

### 4.3 순위 (작을수록 먼저 고른다)

1. 등급: `fail` → `allowed_stop` → `pass`.
2. 같은 등급 안에서 $m$ 오름차순.
3. $m$ 차가 10⁻³ 미만이면 동점: (a) `d1.F_first_level_min_N`가 작은 쪽, (b) 그래도 같으면(차 < 1 N) `d1.stroke_max_m`가 큰 쪽, (c) 그래도 같으면(차 < 0.1 mm) 고른 실행의 $\varepsilon$가 0인 쪽, (d) 마지막으로 Chrono 행 이름의 사전순.

- **기준선 실패**: 고른 후보의 등급이 `fail`이고, 그 `fail` 실행과 같은 키(플랜트만 V0)의 V0 실행도 `fail`이면 그 칸에서 다음 순위 후보를 하나 더 고른다. 칸당 상한 2행.
- VB만의 실패(같은 키 V0는 통과)는 선별 전에 10절 관문 G-3에서 멈춘다.

## 5. S1: C2 roll 부호

- 칸마다(C2-03 = M, C2-07 = B) 후보 둘(roll+op, roll−op)을 4.3 순위로 비교해 1행을 고른다. 4.3 기준선 실패면 두 부호 모두(2행).
- 고른 부호는 Chrono 행 이름 하나로 출력한다. 고르지 않은 부호의 하네스 값도 함께 적는다.

## 6. S2: S-01·S-02 연약 경사

- 칸마다(S-01 = M, S-02 = B) 후보 셋(diag-rec, roll−rec, fup-rec)을 4.3 순위로 비교해 1행을 고른다.
- **fup-rec(U3 가정 경계)**: 하네스 등급이 `pass` 또는 `allowed_stop`이면 다른 둘과 같은 조건으로 겨룬다. 등급이 `fail`이면 그 칸 후보에서 빼고 "가정 경계 미성립"으로 기록하며, 앞들림 경계 재결정을 사용자 질문으로 올린다(제어기 결함으로 읽지 않는다, 행 정의 3절). 이때 나머지 둘에서 고른다. 이 제외는 G-3 멈춤 대상이 아니다.
- 4.3 기준선 실패면 다음 순위 하나를 더한다(상한 2행).

## 7. S3: D1-PSC 포함 여부

D1-PSC는 선택 행이다. 아래 촉발 조건이 하나도 없으면 **돌리지 않고** "하네스 근거로 생략"과 값을 기록한다. 촉발되면 그 프로파일의 사건 행과 그 다리의 기준 행(`depends_on`)을 넣는다.

| # | 촉발(하네스 H-S-C, J1·상단·평지, VB, 해당 프로파일의 $\varepsilon$ 2개 실행 중 하나라도) | 넣는 행 |
|---|---|---|
| T1 | 등급 `fail`(426.3 E-1~E-7 또는 행정 ≤ 684.8 mm 위반) | 그 프로파일 + 기준 |
| T2 | DSb75 작동이 설계 역할과 다름: c-slow에서 `INFO_DIFF_SINK_HOLD` ≥ 1(READY 뒤라 무장되지 않아야 함), 또는 c-mid·c-fast에서 두 $\varepsilon$ 모두 `INFO_DIFF_SINK_HOLD` 0 | 그 프로파일 + 기준 |
| T3 | 판정 양이 한계 가까이: $F_{judged}$ < 1.1 $F_{min}$(10.36 kN), $a$ > 0.15°, $s_{max}$ > 0.6428 m(DSb75 해제 행정) 중 하나 | 그 프로파일 + 기준 |

- c-edge의 작동 여부는 촉발 조건이 아니다(경계라 어느 쪽도 설계와 맞다). $\varepsilon$ 사이 작동 차이는 기록한다.
- 중단·하단·J2의 H-S-C 결과는 대응 Chrono 행이 없다. 그 실패는 하네스 판정으로 보고하고 Chrono 행을 자동으로 더하지 않는다.
- H-S-C-g(`dsb_gated_off`)는 기록 행이다. 촉발에 쓰지 않는다.

## 8. 크롤러 ×3: L1 V0 결과를 VB로 옮겨 읽는 규칙 (U7, dynamics-expert 3.3절 그대로)

대상 칸 $j$ = (오거 T, B) × (평지, diag-op (2.3351, 1.5017)), Chrono C1-09~12와 같은 칸. 하네스 H-R-0의 2×2(K ×1/×3 × VB/V0)에서

$$\bar m_h(P,k)=\tfrac12\big[m_h(P,k,\varepsilon{=}0)+m_h(P,k,\varepsilon{=}2\times10^{-3})\big]$$

$$\Delta_{V0}=\bar m_h(V0,3)-\bar m_h(V0,1),\qquad \Delta_{VB}=\bar m_h(VB,3)-\bar m_h(VB,1),\qquad I=\Delta_{VB}-\Delta_{V0}$$

| 기호 | 뜻 |
|---|---|
| $m_h(P,k,\varepsilon)$ | 하네스 실행의 4.1 H-R 여유(플랜트 $P$, 배율 $k$) |
| $\sigma_j$ | 칸 $j$의 위상 산포 = 네 조합 $(P,k)$의 $\lvert m_h(\cdot,\varepsilon{=}0)-m_h(\cdot,\varepsilon{=}2\times10^{-3})\rvert$ 최대 |
| $m_C(V0,3)$ | Chrono C1 행 결과에 4.1 H-R 식을 적용한 값 |

규칙(이 순서로 처음 맞는 것 하나):
1. $\Delta_{VB}\neq0$, $\Delta_{V0}\neq0$, 부호가 같고 $\lvert I\rvert\le0.5\max(\lvert\Delta_{VB}\rvert,\lvert\Delta_{V0}\rvert)$ → **옮겨 읽음**: $\hat m_C(VB,3)=m_C(V0,3)+[\bar m_h(VB,3)-\bar m_h(V0,3)]$(기록 문구, 판정 아님).
2. $\lvert\Delta_{VB}\rvert<\sigma_j$이고 $\lvert\Delta_{V0}\rvert<\sigma_j$ → "크롤러 강성 영향 없음".
3. 그 밖 → 옮겨 읽지 않음, "VB 크롤러 감도 미확정".

- $m$은 최소 항이라 항이 바뀌면 불연속이다. 그래서 같은 2×2를 $m_F$, $m_T$, $m_a$, $m_s$ 각각에도 계산해 기록한다. 칸의 문구는 $m$의 규칙 결과로 정하고, 항별 결과가 다르면 함께 적는다.
- C1 행 자체의 판정은 기록이다(실패는 보고). 이 규칙은 C1 판정을 바꾸지 않는다.

## 9. 하네스–Chrono 짝 기록

Chrono 행마다 같은 키의 하네스 VB 실행($\varepsilon$ 2개)의 등급·$m$·항별 값과 Chrono 값을 나란히 적는다. 등급 방향이 다르면(하네스 통과·Chrono 실패 등) "모델 차이"로 기록한다. C2(강체 크롤러)는 하네스 K ×1·×3 둘 다 적는다.

## 10. 관문 (선별 전, 하나라도 걸리면 멈추고 묻는다)

| # | 관문 | 처리 |
|---|---|---|
| G-1 | 하네스 실행 오류 0, `--list` 건수가 행 정의(H-R 105 조합·420 실행, H-S 106 조합·424 실행, H-S-C-g 6 조합·24 실행)와 같음 | 다르면 멈춤 |
| G-2 | 3절 필드가 모든 실행에 있음 | 없으면 멈춤(종료 코드 2) |
| G-3 | **판정 행**(H-R-0, H-R-A, H-S-0, H-S-1, H-S-A, H-S-C)에서 VB `fail`이고 같은 키 V0가 `pass`인 실행이 없음. 예외: 6절 fup-rec | 있으면 멈추고 묻는다(v5 플랜트 고유 실패 가능성, 행 정의를 바꿀 수 있음) |
| G-4 | VB 실행의 J-P3에 설정 결함·H-7 없음(v5 기준 개정 8·9) | 있으면 멈춤 |
| G-5 | 선별 스크립트의 SHA-256과 이 문서의 SHA-256이 선별 출력에 적혀 있음 | 없으면 선별 결과로 쓰지 않음 |

- 기준선 실패(VB·V0 모두 `fail`)는 멈추지 않는다. 판정 결과로 보고하고 4.3 규칙으로 선별한다.
- 판정 행의 실패 자체는 하네스 판정 결과다. 선별 규칙이 지우거나 강등하지 않는다.

## 11. 판정 기준 (D-5: 기존 기준 그대로)

| 행 | 판정 | 근거 |
|---|---|---|
| H-R-0, H-R-A | s6 D8·P: 이륙 뒤 1 ms ≥ $F_{min}$, 끝 자세 ≤ 0.2°, READY 평지 90 / 경사 120 s, 이동 ≤ 180 bar, 잠김 ≤ 350 bar, FAULT 0, 행정 가드 분류. H-R-A는 + G6-1~G6-7(+ 강등 377, 424.11.2), `stroke_limited_stop` 허용 | 행 정의 2절 |
| H-S-0, H-S-1 | P3-1~P3-9(`P3-4_verdict`), READY 평지 100 / 경사 120 s, `stroke_limited_stop` 허용, 토양 사건 0.5 s 평균(v5 3.1 ⑦). fup-rec는 `ASSUMED_BOUNDARY`(6절), J2 roll±는 "하네스 경계(비단조)" 주석 | 행 정의 3절 |
| H-S-A | P3 + G6-1~G6-7, `stroke_limited_stop` 허용 | 같음 |
| H-S-C | 426.3 E-1~E-7(slow·fast 구분) + 행정 ≤ 684.8 mm, DSb75 기록 | 같음 |
| 기록 행 | 판정 아님. H-R-A-stop의 기대 = 행정 가드 계열 종료 + 이동 ≤ 210 bar·잠김 ≤ 350 bar + 이륙 뒤 $F_{min}$ 위반 없음, 다르면 "기대 불일치" 기록 | 같음 |
| C2-01~08 | D8·P + v5 기록, 꼬리표 "이륙 뒤 8 s 강체 크롤러 상한"(S8-L1·L5). READY 창 $\sum F_c$·하중 중심은 기록 | 행 정의 4절 |
| C1-09~12 | 기록(D8·P 계산, 실패는 보고), 8절 규칙 | 같음 |
| S-01·02 | P3, READY 120 s, `stroke_limited_stop` 허용 | 같음 |
| S-03·04 | P3 + G6 | 같음 |
| D1-PSC(포함될 때) | 426.3 E-1~E-7 + 행정 ≤ 684.8 mm + DSb75 기록 | 같음 |
| VB 실행 공통 | v5 기준(개정 7·8·9)이 VB 실행에 정한 항목(J-P3, Chrono T4·T5)은 그 기준이 정한 범위대로 적용·기록한다. 이 문서는 그 범위를 넓히거나 줄이지 않는다 | v5 기준 |

## 12. 선별 출력 (스크립트, python-expert P-5 확장)

- 입력: 하네스 결과 JSON(3절 필드). 출력 JSON: 선별 칸마다 고른 Chrono 행 이름, 후보 전부의 등급·$m$·항별 값·동점 보조값, 4.3 기준선 실패 여부, fup-rec 제외 여부, D1-PSC 촉발 조건별 값과 넣는 행, 8절 칸마다 $\Delta_{V0}$·$\Delta_{VB}$·$I$·$\sigma_j$·규칙 번호(전체와 항별), 이 문서와 스크립트의 SHA-256.
- 종료 코드: 0 선별 완료, 1 관문(G-1·G-3·G-4) 걸림, 2 입력 누락(G-2).

### 12.1 봉인 시험값 (스크립트 단위 시험에 그대로 쓴다)

| # | 입력 | 기대 |
|---|---|---|
| 1 | S1 M: roll+ 실행 $m$ = 0.120, 0.118, 0.110, 0.111(모두 `pass`), roll− = 0.105, 0.109, 0.1095, 0.108(`pass`) | roll− (`D1C2_middle_rollm4.4_Fs4`) |
| 2 | 1과 같되 roll+ 최소 0.1100, roll− 최소 0.1105; 최소 실행의 `F_first_level_min_N` roll+ 57,100, roll− 55,000 | 동점 → roll− |
| 3 | roll+ 한 실행이 `allowed_stop`($m$ 0.30), roll− 모두 `pass`($m$ 0.05) | roll+ |
| 4 | S2 M: fup-rec 한 실행 `fail`(V0 `pass`), diag-rec $m$ 최소 0.08, roll−rec 0.06 | roll−rec 선택, fup-rec "가정 경계 미성립" 질문, G-3 멈춤 없음 |
| 5 | 8절: $\bar m_h$(V0,1) 0.20, (V0,3) 0.17, (VB,1) 0.19, (VB,3) 0.15, $\sigma_j$ 0.005 | 규칙 1, $\hat m_C(VB,3)=m_C(V0,3)-0.02$ |
| 6 | 8절: $\Delta_{V0}$ = +0.003, $\Delta_{VB}$ = −0.002, $\sigma_j$ 0.004 | 규칙 2 |
| 7 | S3: 모든 프로파일 `pass`, c-mid·c-fast 두 $\varepsilon$ 모두 HOLD ≥ 1, c-slow HOLD 0, 최소 $F_{judged}$ 12.0 kN, $a$ 최대 0.06°, $s_{max}$ 최대 0.55 m | D1-PSC 생략 |
| 8 | 7과 같되 FL c-fast 한 $\varepsilon$에서 $s_{max}$ 0.650 m | `..._FL_cfast` + `..._spFLJ1_base` |

## 13. 가정

| 가정 | 값 | 근거 |
|---|---|---|
| 동점 문턱 | $m$ 차 < 10⁻³, $F$ 차 < 1 N, 행정 차 < 0.1 mm | 제안서 6절(10⁻³) + 이번에 정함 |
| S1에서 K ×1·×3 최악 | 두 배율 묶음 | Chrono 강체 크롤러는 어느 배율과도 같지 않음 |
| T3 한계 근처 | 1.1 $F_{min}$, 0.15°, 0.6428 m | 이번에 정함(한계의 10 %, 75 %, DSb75 해제 행정) |
| 칸당 상한 | 2행 | 제안서 6절 #5 |
| 8절 위상 산포 | 네 조합의 위상 차 최대 | U7 "위상 산포"를 이번에 수치로 정함 |
