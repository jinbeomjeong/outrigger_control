# B1 C3 probe 단계 행정 가드 확인 (읽기 전용)

- 작성: control-expert, 2026-11-13. Chrono 실행 없음. 추적 파일 수정 없음(이 파일만 새로 씀).
- 질문(판정서 `b1_creep_basis_judgement.md` 첫머리 안전 기록·1.4 제안 3): C3 `B1_J2_B_top_Fs4_VB_fdown`에서 FL 판독 최대 683.475 mm가 행정 예산 가드 682.8 mm를 0.675 mm 넘었다($n$ = 610, 61.0 s, `probe` 단계, SGS·WARN·FAULT 사건 없음). 가드가 probe에서 동작하지 않는 것이 명세상 설계 의도인가. 0.675 mm 초과는 안전 여유 안인가, 명세 결함인가, 구현 결함인가.
- 규약: 이산 $T_s$ = 0.1 s, 출력 지연 $d$ = 1, $u$ = 다리 행정 속도 명령 [m/s](+ = 신장). "판독 행정"은 제어기가 보는 `Measurements.stroke_m`(Chrono `record.npz` `meas.stroke`, B1 규칙 머리 규약과 같은 양)이다. 길이는 mm로 적는다.

## 1. 결론

**분류: 설계 의도 안, 안전 여유 안. 명세 결함·구현 결함 아님.** 다만 B1 규칙의 지표 정의에는 빈 곳이 있다(3절). 이 빈 곳은 rev2 초안 `b1_creep_rules_rev2_draft.md` R2-1에서 다룬다.

1. 행정 예산 가드(P-S8-28 `WARN_LIFT_STROKE_LIMITED`·`FAULT_LIFT_STROKE_LIMIT`)와 SGS(`FAULT_LIFT_STROKE_LIMIT:soil`)는 명세상 **LEVEL 단계, LOC 확정 뒤**에만 동작한다. 코드도 같다.
2. PROBE 단계에는 따로 **탐침 행정 가드 P6**(명세 20.4, U23 채택)가 있다. 한계는 $s_{soft}$ − 5 mm = 689.8 mm다. C3 탐침은 이 가드를 통과했고(681.267 + 2 = 683.27 mm ≤ 689.8 mm), 정상 순서(신장 먼저)로 돌았다.
3. 683.475 mm는 LEVEL이 끝난 값(DONE 진입 때 681.452 mm)에 탐침 깊이 2 mm와 센서 잡음(σ 0.1 mm)이 더해진 값이다. 탐침은 같은 경로로 되돌아오는 ±2 mm 이동이고, 탐침 뒤 FL은 680.749 mm(62.5 s)로 돌아왔다.
4. 다음 안전 쪽 한계까지 남은 거리(같은 판독 좌표): 탐침 가드 6.3 mm, 행정 끝 FAULT 문턱 10.3 mm, 소프트 끝(센서 끝) 11.3 mm, 플랜트 행정 끝 16.5 mm다. 물리 피스톤 기준으로는 700 mm까지 23.1 mm 남았다.

## 2. 근거

### 2.1 명세 문장

| 위치 | 문장(요지) | 뜻 |
|---|---|---|
| `s6_control_spec.md` 369.2 "조건" 행(14151행) | "상태 LEVEL, LOC 확정 뒤. $s_g = s_{soft}$ − `STROKE_END_MARGIN_M` − `extra_margin_m` = 682.8 mm" | 가드는 LEVEL에서만 본다 |
| 369.2 "위치" 행(14150행) | "`_level`에서 … `leg_speeds = self._apply_lift_stroke_guard(reading, leg_speeds)`" | 호출 위치가 `_level` 하나다 |
| 369.5 T9(14183행) | "LOC 전에는 가드가 작동하지 않는다" | LOC 조건 |
| 427.12.1 항목 4(17760행) | "가드 주기는 LEVEL 안에서만 생기므로 DONE·READY 중 판정 분기(427.3식)는 쓰이지 않는다" | SGS도 LEVEL에서만 생긴다고 명세가 전제한다 |
| 427.12.3(17776행) | "`_record_lift_guard_period`에서, 래치가 있고 `soil_stop` 참이고 LEVEL이면 그 주기에 정지를 예약한다" | SGS 무장도 LEVEL 가드 주기에 묶인다 |
| 20.4 P6(1121~1123행) | "확장 경계 탐침의 순간 행정 여유는 … 그래서 탐침에 행정 가드를 둔다(P6). 탐침 시작 전에 $s_i+d>s_{max}-5$ mm(가정)이면 복귀 먼저(−d → 유지 → +d) … 그래도 $s_i>s_{max}-5$ mm이면 그 다리는 탐침하지 않고 `probe_skipped:stroke_margin`" | 탐침은 따로 가드가 있다. U23 채택(20.5 표) |

- 명세는 "탐침은 LEVEL 예산 가드 밖이고 P6가 맡는다"를 한 문장으로 적어 두지는 않았다. 그러나 369.2의 조건·위치와 20.4 P6를 함께 읽으면 두 가드의 역할이 나뉜다. LEVEL 가드는 들어 올림(heave·자세 루프 출력)이 행정을 먹는 것을 막고, P6는 되돌아오는 2 mm 탐침이 행정 끝에 닿는 것을 막는다.
- 20.4 본문의 "FAULT(679 mm, 2 s 지속)"는 옛 행정 치수 때 값이다. 지금 FAULT 문턱은 693.8 mm다(2.3). 기록 차이일 뿐이고 코드 동작과 무관하다(명세 개정 필요 없음, 메모로만 둔다).

### 2.2 코드 줄 (`03_src/outrigger_sim/control/c2.py`, 작업 사본 sha256 `f58ee42b…`, 마지막 변경 커밋 `ba3adcc`. B1 실행 커밋 `bd64cc4`와 같은 내용)

| 줄 | 내용 | 무장 조건 |
|---|---|---|
| 8209~8210 | `if not settings.enable or self._state.phase is not C2Phase.LEVEL: return leg_speeds` | 단계 = LEVEL |
| 8211~8212 | `if not self._is_liftoff_confirmed(): return leg_speeds` | LOC 확정 |
| 8229~8234 | $s_g$ = `stroke_soft_max_m` − `STROKE_END_MARGIN_M`(433행, 0.010) − `extra_margin_m`(1898행, 0.002) = 694.8 − 10 − 2 = 682.8 mm. 가드 다리 = $u_i > 0$ 그리고 $s_i + u_i \cdot 2 T_s \ge s_g$(`lookahead_periods` 2, 1901행) | — |
| 8247~8263 | `_record_lift_guard_period` → 첫 주기 `WARN_LIFT_STROKE_LIMITED`(8262) → `_note_soil_guard_period`(8263) | 가드 주기에서만 |
| 8300~8317 | SGS 무장 `any_loc` = `_is_liftoff_confirmed()`(8304~8305), 정지 예약(8316~8317) | 가드 주기 + LOC |
| 7429 | `_apply_lift_stroke_guard`의 유일한 호출(`_level` 안, 7255행부터) | — |
| 7433~7443 | 행정 끝 FAULT(`_update_stroke_end_fault`, 7660~7666)와 끝 절단(`_clip_at_stroke_ends`, 7677~7685)도 `_level` 안 | — |
| 6001~6009 | DONE → PROBE로 바꾸고 `_probe_step` 호출(`_hold_probe_or_relevel`). 이 경로는 `_level`을 지나지 않는다 | — |
| 9617~9650 | `_probe_step`: `ProbeRound(..., stroke_max_m=geometry.stroke_soft_max_m, ...)`(9634) | — |
| 3206~3209 | `stroke_soft_max_m` = min(`stroke_max_m` 0.70, 측정 끝 0.6948) = 694.8 mm | — |

`03_src/outrigger_sim/control/ground_contact.py`(작업 사본 sha256 `83339ea8…`)

| 줄 | 내용 |
|---|---|
| 149 | 탐침 깊이 `depth_m` = 2×10⁻³ m |
| 200~203 | `stroke_guard_margin_m` = 5×10⁻³ m(가정, 명세 20.4 P6) |
| 826~839 | `_first_move_sign`: 한계 = `stroke_max_m` − margin = 689.8 mm. $s + d \le$ 한계면 신장 먼저(+1), $s \le$ 한계면 복귀 먼저(−1), 그 밖은 건너뜀(None) |
| 841~862 | 건너뛴 다리 `probe_skipped:stroke_margin`(c2.py 9646~9647에서 사건) |

- 명세 369.2의 조건(LEVEL, LOC 확정 뒤)과 코드 8209·8211이 같고, 명세 20.4 P6의 식($s_i + d > s_{max} - 5$ mm면 복귀 먼저, $s_i > s_{max} - 5$ mm면 건너뜀)과 `_first_move_sign`이 같다. **구현 결함 없음.**
- C3 `controller_meta.lift_stroke_guard`: `settings.enable` 참, `soil_stop` 참, `soil_stop_scope` `any_loc`, `periods` 0, `soil_guard_first_s` null. 실행 내내 가드 주기가 한 번도 없었다(LEVEL 판독 최대 681.841 mm, $n$ 575, 3.1).
- probe 설정(같은 meta): `depth_m` 0.002, `stroke_guard_margin_m` 0.005, `profile` trapezoid, `move_duration_s` 0.56, `hold_s` 0.4.

### 2.3 C3 FL 기록 (확인 계산, 판정 값 아님)

입력: `07_results/S9/batch_V5-B1-CREEP_20261112_125134/B1_J2_B_top_Fs4_VB_fdown/` `record/record.npz`, `r8_series.npz`, `step_series.npz`, `result.json`. 스크립트: scratchpad `ctrl-b1c3/probe_trace.py`, `truth_vs_read.py`, `phase_max.py`(dynamics-dev, `-I -B`).

| $n$ | $t$ [s] | 단계 | 발행 $u_{FL}$ [mm/s] | 판독 행정 [mm] | 피스톤 `meas.stroke_corrected` [mm] |
|---|---|---|---|---|---|
| 575 | 57.5 | level | — | **681.841**(LEVEL 최대) | — |
| 596 | 59.6 | done | −0.106 | 681.452 | 675.039 |
| 597 | 59.7 | probe(FL) | −0.143 | 681.267(탐침 시작) | — |
| 598~607 | 59.8~60.7 | probe | 0.496 → 3.571 → 0.020(사다리꼴) | 증가 | — |
| 608~612 | 60.8~61.2 | probe(유지) | 0 | 683.474~683.475(최대, $n$ 610) | 676.881 |
| 613~622 | 61.3~62.2 | probe | −0.020 → −3.571 → −0.496 | 감소 | — |
| 625 | 62.5 | probe | 0 | 680.749 | 674.302 |
| 698 | 69.8 | level | 0 | (탐침 끝, LEVEL 재진입) | — |

- 사다리꼴 명령의 합은 $\sum u\,T_s$ = 2.000 mm(= `depth_m`)다. 판독 상승 2.208 mm 가운데 0.21 mm는 잡음(σ 0.1 mm)·밸브 지연이다.
- 탐침 가드 판정(시작 주기 $n$ 597): $s + d$ = 681.267 + 2.000 = 683.267 mm ≤ 689.8 mm → 신장 먼저. 정상 경로다.
- FL은 $n$ 597 탐침 전 LEVEL 판독 최대 681.841 mm로, 가드 682.8 mm보다 0.959 mm 아래였다. 가드는 LEVEL 동안 작동할 일이 없었다($s_i + 2T_s u_i < s_g$).
- 같은 묶음의 다른 READY 행도 판독 최대가 탐침에서 나왔다: C1 FL 680.176 mm($n$ 747, LEVEL 최대 678.596), C2 FL 678.929 mm($n$ 733, LEVEL 최대 678.132). SGS 행(C4·C5·C6)의 판독 최대는 SGS 뒤 FAULT 단계의 정지 관성(밸브 τ 0.1 s + $d$ = 1로 약 1 mm)과 잡음이다(rev2 초안 2.2).

### 2.4 다음 안전 쪽 한계

판독 좌표는 L2b 플랜트의 `s_ref`(기름 부피 좌표, 행정 제한기가 자르는 좌표, `chrono/l2b_engine.py` 23~27·212~213행)다. 피스톤 위치 `meas.stroke_corrected`보다 $F/k_h$(약 119 kN / 1.8×10⁷ N/m ≈ 6.6 mm)만큼 크다.

| 한계 | 값 [mm] | 좌표 | C3 최대 683.475 mm에서 남은 거리 [mm] | 출처 |
|---|---|---|---|---|
| LEVEL 행정 예산 가드 $s_g$ | 682.8 | 판독 | −0.675(LEVEL 밖이라 적용 안 됨) | c2.py 8229~8231 |
| 탐침 가드 P6 | 689.8 | 판독 | 6.325 | ground_contact.py 834 |
| 행정 끝 FAULT 문턱(2 s 지속) | 693.8 | 판독 | 10.325 | c2.py 7672~7674, `stroke_end_fault_margin_m` 0.001 |
| 끝 절단(신장 0으로) | 694.7 | 판독 | 11.225 | c2.py 7683, `stroke_end_clip_margin_m` 0.0001 |
| 소프트 끝 = 센서 측정 끝 | 694.8 | 판독 | 11.325 | c2.py 3209, YAML `legs.*.extension_range_m` |
| 플랜트 행정 끝 | 700.0 | 판독(`s_ref` 범위) | 16.525 | `plant_s8.oil_law.stroke_m` 0.7 |
| 물리 피스톤의 행정 끝 | 700.0 | 피스톤 | 23.119(피스톤 676.881) | `meas.stroke_corrected` |

- **0.675 mm 초과는 안전 여유 안이다.** 탐침 가드 한계까지 6.3 mm, FAULT 문턱까지 10.3 mm 남았다. 설계상 탐침 최대는 "LEVEL 끝 값 + 2 mm + 잡음"이고, LEVEL 가드가 LEVEL 끝 값을 대략 682.8 mm 아래로 묶으므로 탐침 최대는 약 685 mm 아래다. P6는 LEVEL 끝 값이 687.8 mm를 넘을 때만 순서를 바꾼다.

## 3. B1 규칙 쪽 빈 곳 (제어기 결함이 아님)

- B1 원판 M-2는 $s_{\max}$를 "실행 전체 판독 최대"로, $g = s_{guard} - s_{b^\ast,\max}$로 정의했다. 그러나 가드는 LEVEL에서만 본다. 그래서 READY 행의 $s_{\max}$·$g$에는 가드가 보지 않는 탐침 상승(C1 +1.580, C2 +0.797, C3 +1.634 mm, 판독 최대 − LEVEL 최대)이 들어갔다. C3의 $g$ < 0은 이 정의 때문이다.
- SGS 행의 $s_{\max}$도 SGS 뒤 FAULT 단계 값이다(C4 FR +1.942, C5 RL +1.803, C6 FR +1.924 mm, 판독 최대 − LEVEL 최대). 원판 7.4는 이것을 "하한"으로 읽었으나, 실제로는 정지 관성·잡음이다.
- 이번 등급 영향(판정서 2.5 해석 메모와 같은 꼴의 확인 계산): LEVEL 최대로 바꿔도 C3 P-A 오차는 +12.027 mm라 D-d는 `PRED-FAIL` 그대로다. D-e는 C1 $g$ 4.204, C2 4.668 mm로 20 mm와 멀어 `B1-OPEN` 그대로다. 판정서는 고치지 않는다(봉인 규칙대로 낸 등급이다).
- 처리: rev2 초안 R2-1(예측 대상 = 가드 감시 주기의 판독 최대 $s^G_{\max}$, 탐침 최대는 따로 기록)로 넘긴다.

## 4. 제안 (구현 없음)

| # | 제안 | 담당 | 필요성 |
|---|---|---|---|
| 1 | 명세에 "LEVEL 행정 예산 가드(369.2)는 PROBE·REANCHOR·DONE·READY에서 보지 않는다. PROBE는 20.4 P6가, REANCHOR는 `_clip_at_stroke_ends`(5525행)가 맡는다"는 한 문장을 369.2 표 아래에 더한다 | control-expert(명세 개정, 사용자 결정 뒤) | 선택(문서 명확화). 동작 변경 없음 |
| 2 | 20.4의 "FAULT(679 mm, 2 s 지속)"에 "옛 치수 값, 현행 693.8 mm" 주석 | control-expert | 선택 |
| 3 | 코드 변경 없음. python-expert 위임 없음 | — | — |

- 결함이 아니므로 구현 위임은 없다.
