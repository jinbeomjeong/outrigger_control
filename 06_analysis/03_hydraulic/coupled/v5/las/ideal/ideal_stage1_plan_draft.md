# 이상적 센서 정보용 진단 1단계 계획 (DRAFT)

- 작성: control-expert, 2026-11-10. **DRAFT**다. 등록본이 아니다.
- 등록 방식은 **가벼운 등록**이다(사용자 결정 2026-11-09). 판정 등급은 두지 않는다. 등록본은 이 초안에 사용자 결정(10절)을 반영해 `ideal_stage1_plan.md`로 만든다. 실행 전에 그 파일의 sha256과 커밋을 남기고, 키 목록 파일의 sha256을 본문에 적는다.
- 이 문서를 쓰면서 한 일은 저장 결과 읽기와 몇 초짜리 집계뿐이다. 하네스·Chrono는 돌리지 않았다. 집계 스크립트와 출력 경로는 11절에 있다.
- 규약
  - 이산 $T_s$ = 0.1 s(10 Hz)이고 출력 지연은 $d$ = 1이다. IMU는 100 Hz이고, 하네스 내부 덩어리는 1 ms(`LAG_CHUNK_S`)다.
  - C2는 음되먹임이다($u$ = 행정 속도 명령 [m/s]). 행정은 모터 행정 [m]이고 표에서는 mm로 적는다. 힘은 실린더 순 힘 [N]이다.
  - 시각 비교는 $n = \mathrm{round}(t/T_s)$ 정수 주기로 한다.

## 0. 목적과 범위

- 목적: 정보 상한을 잰다. "크롤러 접촉·간극", "패드 침하", "압력 1 kHz 평균"을 제어기가 참값(또는 실현 가능한 평균값)으로 받는다면 무엇이 달라지는지 본다. 대상은 경계 키 문제, 거짓 LOC, 행정 예산이다.
- 이것은 **판정이 아니라 진단**이다. 결과 문구 형식은 "정보 I-x로 집합 S의 지표 m이 a → b"다. 판정 키에 돌린 결과도 **정보용(참값 입력)**이라고 공개한다.
- 범위
  - 1단계 변형은 SHD(그림자), IGA, IGB, IZ, S4 다섯 개다(3절).
  - S1c(크롤러–상부체 상대 기울기계)는 뺀다. 이 모델에서 크롤러는 상부체 강체의 일부라 정의할 수 없다.
  - S2(패드 하중 핀)와 +1 주기 지연 감도, 실기 오차 등급은 2단계로 미룬다.
  - Chrono는 1단계에 없다.
- 기준선: **K1 채택 프리셋**이다. 프리셋은 `C2Config.with_10hz_d1()`이고, LAS-b b0(= 하네스 후보 이름 P0)에 K1 순서 관문이 켜져 있다. 태그는 V0 `final_C4G2_LAS_K1`, VB(③) `final_C4G2_P3_LAS_K1`다(명세 437). A 집합만 K1 끔 팔도 함께 돌린다.
- 구현 원칙
  - c2.py는 고치지 않는다(0줄).
  - 연구용 하위 클래스 `IdealSensorC2`를 `04_scripts/04_hydraulic/coupled/ideal_sensor_targeted.py`에 둔다. 구현은 python-expert가 한다(8절).

### 기호

| 기호 | 뜻 | 단위 |
|---|---|---|
| $t_{lift}$ | 참 크롤러 첫 이탈 시각. 1 ms 참 크롤러 힘이 처음 0이 된 시각(하네스 `values.forces.t_lift_s`, Chrono `p3b.departure.t_departure_s`) | s |
| $t_S$ | 토양 모드 시작(K1 `decisions[0].t_S_s`) | s |
| $t_P$ | S-1 평탄 창 시작 | s |
| $t_{LOC}$ | 첫 LOC 확정(`events.t_loc_first_s`) | s |
| $n_P, n_S$ | $\mathrm{round}(t_P/T_s)$, $\mathrm{round}(t_S/T_s)$. K1은 $n_P > n_S$일 때만 R4c30을 켠다 | 주기 |
| $\chi_{cr}$ | 이상 크롤러 접촉. 지난 주기의 1 ms 덩어리 중 하나라도 참 크롤러 힘 > 0이면 참 | — |
| $g_k$, $g_{min}$ | 이상 크롤러 귀퉁이 간극(상자 4귀퉁이)과 그 최소 | m |
| $c_k$, $c_{min}$ | 제어기의 행정 기반 틈 추정(`clearance_corners_m`) | m |
| $z_i$ | 이상 패드 침하. + 쪽이 패드 바닥이 원 표면 아래 | m |
| $\bar p_{h,i}, \bar p_{r,i}$ | 주기 안 1 ms 표본 100개의 상자 평균 압력(헤드·로드) | Pa |
| $s_{max}$ | 실행 중 최대 행정. SGS 행정 가드는 682.8 mm다 | m |

## 1. 사전 집계 (저장 결과만, 실행 없음)

### 1.1 하네스 K1 Y 행을 K1 팔별로 다시 셈

- 질문: K1 채택(R4c30 순서 관문 기본 켬)으로 11-09 사전 집계가 바뀌는가.
- 답: **바뀌지 않는다.** 이유는 구조적이다. K1은 LOC 뒤의 틈 목표만 바꾸므로, 그보다 앞서 정해지는 $t_S$·$t_P$·$t_{LOC}$은 같은 키에서 K1 끔과 켬이 같다. 저장 행에서도 그대로 확인된다.

| 팔(K1 / LAS 후보) | 고유 행 | 거짓 토양 모드(행, $t_S - t_{lift}$) | 정상 토양 모드 | 거짓 LOC(행) | $t_{LOC} - t_{lift}$ [s] |
|---|---|---|---|---|---|
| K1 끔 / P0 | 74 | 5(+0.45 ~ +0.85, 중앙 +0.54) | 26 | 8 | 중앙 +0.73, 최대 +3.02 |
| K1 켬 / P0 | 225 | 5(같은 5키, 같은 값) | 177 | 8(같은 8키) | 중앙 +0.98, p90 +1.19, 최대 +3.81 |
| K1 끔 / P5r4 | 30 | 2(+0.93, +1.35) | 10 | 1 | 중앙 +0.97 |
| K1 켬 / P5r4 | 222 | 2(같은 2키) | 10 | 1(같은 키) | 중앙 +1.28, 최대 +3.02 |

- 11-09 사전 집계 값과의 대응
  - 거짓 토양 모드 "14행 = 7키": 14 = 5 + 5 + 2 + 2(팔별 합)이고, 7키 = 행 id와 LAS 후보 쌍 7개(P0 5 + P5r4 2)다. 행 id로는 6개다. J2 패치 `VB|e0`가 P0와 P5r4 양쪽에 있다.
  - 경계 키(`G1+J1@FL|T|VB|e0`)는 **P5r4에서만** 거짓 토양 모드다. 채택 프리셋 P0에서는 토양 모드 자체가 시작되지 않는다(K1 판정서 2.1).
  - 거짓 LOC "9행"은 P0 8키 + P5r4 1키(J2 `T|diag-rec|VB|e0`, P0 8키에도 있다)다. 11-09 표의 "J1 3행"은 J1 `M|roll+rec` 1키와 H-S-C-g J1 `diag-rec` 2키다.
  - LOC 지연 중앙값이 팔마다 다른 것(+0.73 ~ +1.28 s)은 팔마다 키 구성이 달라서다(K1 켬 P0 225행은 Y-Pa R4 행 165를 포함한다). 같은 키끼리는 값이 같다.
- 결론: 11-09 값(거짓 토양 모드 14행 = 7키, 거짓 LOC 9행, LOC 지연 중앙값 +1.06 s·최대 +3.81 s)은 K1 채택 뒤에도 그대로 쓴다. 채택 프리셋(P0)만 보면 거짓 토양 모드는 5행 id, 거짓 LOC는 8행 id다.

### 1.2 Chrono 저장 행 (REM 10행, S-Ch 2행)

| 묶음 | 행 | $t_S - t_{lift}$ [s] | $t_{LOC,first} - t_{lift}$ [s] | $t_{LOC,final} - t_{lift}$ [s] | LOC 취소 |
|---|---|---|---|---|---|
| REM J2 B 상·중·하단 VB(끔/켬/forced) | 6 | −9.62 ~ −9.68(정상) | +1.98 ~ +2.03 | 같음 | 없음 |
| REM J2 ×1.1 V0·VB(끔/켬/forced) | 4 | −20.05 ~ −20.12(정상) | +1.18 ~ +1.95 | +3.08 ~ +4.05 | 있음 |
| REM J1 ×1.1 VB 끔 | 1 | −14.91(정상) | +1.39 | +2.99 | 있음 |
| **S-Ch** G1 + J2 패치@FL(끔/켬) | 2 | **+2.09(거짓 토양 모드)** | +2.89 | 같음 | 없음 |

- 관문 끔·켬 짝은 LOC 전 시각이 모두 같다(REM 3짝, S-Ch 1짝). Chrono에서도 K1은 LOC 전 경로를 바꾸지 않는다.
- Chrono에서 확인된 것
  - 패치 키의 거짓 토양 모드가 Chrono에서도 나온다. 하네스(+0.45 ~ +0.85 s)보다 늦다(+2.09 s).
  - 진짜 연약 지면에서는 거짓 토양 모드가 없다(10/10 정상). 거짓 LOC(LOC가 참 이탈보다 앞섬)도 0/10이다.
  - Chrono LOC 지연은 첫 LOC +1.2 ~ +2.0 s, 취소 뒤 재LOC +3.0 ~ +4.1 s다. 하네스 중앙값 +1.06 s보다 길다. 하네스는 이 지표에서 낙관 쪽이다.
- K1 알려진 한계 F2(K1이 첫 R4 LOC를 막으면 R4c30이 끝까지 없음)는 취소·재LOC 경로에서 생긴다. I-G는 LOC 시각을 접촉 정보로 정하므로 이 경로가 줄어드는지도 본다(지표 M-9).

## 2. 이상 신호 정의 (1단계)

- 공통 규칙
  - 표본 순간은 10 Hz로, 압력·행정과 같은 $t_k$(주기 끝)다. 추가 지연은 0이고, 출력 지연 $d$ = 1은 그대로 둔다.
  - 잡음·바이어스·탈락은 0이다(S4는 예외, 아래).
  - 참값은 하네스 플랜트에서 `IdealSource`로만 읽는다. 제어기 파라미터는 명목값을 그대로 쓴다. 감도 실행의 플랜트 덮어쓰기가 제어기로 새지 않게 하기 위해서다.

| # | 신호 | 정의 | 하네스 출처(구현 확인은 python-expert) | 확인 |
|---|---|---|---|---|
| S1a | $\chi_{cr}$ | 지난 주기 1 ms 덩어리 중 하나라도 참 크롤러 힘 > 0 | `control_period`의 `rec["crmax"]`(acc[15] 최대) | Q-D1 |
| S1b | $g_k$, $g_{min}$ | 크롤러 상자 4귀퉁이(`crawler_corners_xy_m`)에서 바닥 평면까지의 거리. 노드 최소는 `crawler_node_heights`로 따로 기록한다 | 하네스 바닥 평면 $n\cdot(r + R c_k)$ | Q-D2 |
| S3 | $z_i$, $\dot z_i$ | 패드 침하(+ = 원 표면 아래). 속도는 주기 차분 | `plant.soil.z`(강체 다리는 0), 소성분 `soil.sp`는 기록만 | Q-D4, Q-T1 |
| S4 | $\bar p_{h,i}$, $\bar p_{r,i}$ | 주기 안 1 ms 덩어리 100개의 압력 상자 평균. 센서 오차 모델은 덩어리마다 적용한다(행이 쓰는 등급 그대로) | `control_period` 래퍼에서 덩어리마다 `plant.pressure()` 누적 | 신호 정의 확인 없음(실현 가능 변경) |

- S4 주파수 특성: 상자 평균 $H(f) = \mathrm{sinc}(f T_s)$, 군지연 50 ms다.
  - heave 8.88 Hz에서 $|H|$ ≈ 0.12(−18 dB)다.
  - 로킹 약 3 Hz에서 $|H|$ ≈ 0.86(−1.3 dB)이고, 위상 지연은 3 Hz에서 54°다.
  - 10 Hz 순간 표본의 heave 앨리어싱(8.88 Hz → 1.12 Hz)이 −18 dB 줄어든다.

## 3. 변형

| 코드 | 이름 | 제어기에 주는 것 | 바뀌는 판정 | 해시 기대 |
|---|---|---|---|---|
| **SHD** | 그림자 | 아무것도 주지 않는다. $\chi_{cr}$, $g_k$, $z_i$, $\bar p$를 기록만 하고, I-G 규칙의 "그랬다면" 결정(거짓 토양 모드, 이상 LOC 시각)도 기록만 한다 | 없음 | **기준과 같음**(관문 G-1) |
| **IGA** | I-G-a 여유 유지 | $\chi_{cr}$, $g_k$ | ① 토양 모드 시작(S-2)에 "$\chi_{cr}$ 참" 조건을 더한다(래치 해제 규칙은 그대로). ② LOC = $\chi_{cr}$ 거짓 2주기 연속 ∧ $g_{min}$ > 2 mm(히스테리시스 1 mm). $t_P$ = 첫 $\chi_{cr}$ 거짓 주기, $\hat W$ = 그 주기 하중 합. S-1 창은 기록만 한다. ③ LOC 취소(L1gs) = LOC 뒤 $\chi_{cr}$ 참 1주기(최대 2회 유지). ④ 틈 $c_k := g_k$(S-3 편향·LOC 앵커는 끔). R4c30·E3c10 **여유 규칙은 그대로**이고 입력만 참값이다. ⑤ 행정 가드의 "틈 충분" 판단에 $g_{min}$을 쓴다. K1 관문은 켠 채로 두고, 이상 $n_P$와 $n_S$로 계산한다 | 바뀜 |
| **IGB** | I-G-b 여유 끔 | IGA와 같음 | IGA + **R4c30·E3c10 끔**(여유의 근거가 추정 불확실성이므로 참값이면 끈다. 목표 = 참 틈 50 mm) | 바뀜 |
| **IZ** | 침하 보정 | $z_i$ | ① 틈 $c_k^{corr}$: 패드 바닥 높이 $z_{retr} - s_i + z_i$로 평면 맞춤. LOC·접촉 규칙은 그대로다. ② DSb75 잔차 $r = \dot z_L - \dot z_R$(지금은 $(\dot s_L - \dot s_R) - w\dot\phi$) | 연약 지면에서 바뀜, **강체에서는 기준과 같음**(관문 G-2) |
| **S4** | 압력 1 kHz 평균 | $\bar p_{h}$, $\bar p_{r}$을 순간 표본 자리에 넣는다 | 압력을 쓰는 모든 판정: TOUCH, 하한·F_min, LAS-b 관문, LOC 하중 합, D1·D1″, R-5 대체, 로드 배수 보류 | 거의 모든 행에서 바뀜 |

- 임계값 가정(원본에 없음): LOC 간극 문턱 2 mm, 히스테리시스 1 mm, 디바운스 2주기, 취소 1주기. 10절 Q-5에서 확인한다.
- 덮어쓰는 메서드(11-09 설계 검토): `_update_crawler_zone`/`_hold_crawler_zone_until_liftoff`, `_update_liftoff_window`, `_watch_loc_revoke`, `_clearance_corners_m`, `_diff_sink_rates_m_s`. S4는 제어기 메서드를 덮어쓰지 않는다. 하네스 래퍼가 평균값으로 `Measurements`를 만든다(`signals.py`는 그대로 둔다).
- **S4와 D1″ 시각 정렬(위험)**
  - D1″의 $f_z$는 주기 마지막 IMU 10 ms 부분 평균이다. $\bar p$는 주기 중심(50 ms 앞)을 본다. 그래서 바운스 중에는 잔차 $r = \sum F - M_{eff} f_z$에 상쇄되지 않은 heave 성분이 남는다.
  - 하드웨어 확인 ⑤는 "압력·IMU 정렬 ≤ 5 ms, 20 ms가 어긋나면 거짓 헤드 고장"이었다. S4는 이 조건을 구조적으로 45 ms 어긋나게 만든다.
  - 그래서 S4 행에는 **정렬 잔차를 기록만** 한다. 같은 주기 10개 IMU 부분 평균의 평균 $\bar f_z$로 만든 $\bar r = \sum \bar F - M_{eff}\bar f_z$다. 명령에는 쓰지 않는다. `Measurements.imu_specific_force_samples_m_s2`에 10개 표본이 있으므로 래퍼에서 계산할 수 있다.
  - 정렬을 제어에 쓰는 변형 S4a를 1단계에 넣을지는 10절 Q-3에서 정한다.

## 4. 집합과 키 목록

- 키 목록 파일: `ideal_stage1_keys_draft.json`(이 폴더). 목록 sha256 규칙은 `sha256(LF.join(sorted(ids)) + LF)`다. K1 판정서의 목록 sha와 같은 규칙이다(A_P0가 `4cdc9bfe…`, A_P5r4가 `56177ba0…`로 K1 판정서 값과 같다).
- 행 id는 `d1.key` = `<행 키>|<setting>|e<eps>`다.

| 집합 | 내용 | 행 | 목록 sha256 | 출처 | 보는 것 |
|---|---|---|---|---|---|
| A_P0 | 채택 프리셋에서 거짓 토양 모드인 5행(J2 패치@FL T V0/VB × e0/e0.002, J1 패치@FL B V0 e0.002) | 5 | `4cdc9bfe100a4b7d7504df8621eff2fd32660604ab423a61a070ca7a634c5da6` | S-C, Y-Pa | I-G·IZ가 거짓 토양 모드를 없애는지, K1과 같은 결과인지 |
| A_boundary_P0 | 경계 키 `D1\|H-S-A\|G1+J1@FL\|T\|flat\|K1\|VB\|e0`(P0에서는 대조군) | 1 | `f7952299c05840ab8cbc914a3ff75b0d3d21e320b67e14f68ce62230f5a2672a` | S-C, Y-Sa | 해가 없는지 |
| A_P5r4 | P5r4에서 거짓 토양 모드인 2행(경계 키, J2 패치 VB e0) | 2 | `56177ba0a566a28b3fb8422872118b8392f4b1bcb06e7b01065ac6bce061c8a5` | Y-0b, Y-Sb | P5r4 처리가 남아 있을 때만(Q-2) |
| B | 거짓 LOC 8행(J1 `M\|roll+rec` 1, J2 `M\|roll+rec` 2, J2 `T\|diag-rec` 2, J2 `T\|roll+rec` 1, H-S-C-g J1 `diag-rec` 2) | 8 | `454661b3875f581e0ec85964adb9d332858132cac8c4611fd76bc7b2956bb6bc` | S-C | P3-1 회복 수, SGS 정지 수, LOC 시각 |
| C | S2D S-C 그림자 진입 68키(`judge_S.json` `info.P0_margin.rows`, sha `ff5272ce…a2ad`)에서 A·B를 뺀 것. J2 fdown 8키와 H-S-C-g J1 fdown 12키를 포함하고, S2D lost/new/both 키(옛 D 집합)도 전부 여기에 들어 있다 | 67 | `78fae79813e3c4cfffb7724468a5008055e6b263327fe9c3129ccd8ffb2efe91` | S-C | 682.8 mm까지의 여유 분포, `FAULT_LIFT_STROKE_LIMIT` 수 |
| E | S-C 나머지에서 그룹별 비례 층화 40(`random.Random(20261109)`): H-S-0 16, H-S-C 13, H-S-A 7, H-R-A-J2·H-R-A-S1·H-S-1·H-S-C-g 각 1 | 40 | `fb48215aef3ed7967df027ca600c60004c41d5d9a13dcf8f9536c86d13d976da` | S-C | 해가 없는지 |
| F | 강체 b0 행(`las_T1` 48 + `las_T2` 184, 고유 192)에서 층화 40(`random.Random(20261110)`): H-R-A 30, H-R-0 10 | 40 | `38ee1c5585b620e84888a4852a96816334fc3fdf7dbde03524d7bc139fd49c8f` | las_T1·T2 | 해가 없는지. IZ 해시 불변 |
| P0 합집합 | A_P0 ∪ A_boundary_P0 ∪ B ∪ C ∪ E ∪ F | **161** | `ea5de7ed68694ccaf7715111bf2106da24d6ddac15c107a1a7bd86308b116e2f` | — | — |

- 11-09 설계 검토 대비 바뀐 점(공개)
  - C는 68키 그대로(A와 겹치는 1키를 A로 옮겨 67)다. 11-09의 "164행/변형"은 근삿값이었고, 지금은 161행/변형이다.
  - D는 C의 부분집합이라 따로 두지 않는다.
  - F의 모집단은 P0 강체 행(las_T1·T2)이다. P5r4 강체 행인 revA_RT는 기준 해시로 쓸 수 없어서다. 키 집합은 같은 192키다.
- 층화 추출 코드는 11절 `key_sets.py`다. 등록 때 같은 시드로 다시 만들어 sha가 같은지 본다.

### 4.1 헤드 압력 고장 주입 회귀 묶음 H-F (S4 전용)

- 왜 필요한가: D1의 한 주기 계단 문턱은 `max_step_Pa` = 100 bar다(`two_pressure.py` 516행). 센서 점프 $J$가 주기 안 $\varphi$ 지점에 들어오면 S4 평균 판독은 두 주기에 걸쳐 $(1-\varphi/T_s)J$와 $(\varphi/T_s)J$만큼 바뀐다. 그래서 $\max(\varphi, T_s-\varphi)/T_s \cdot J$ < 100 bar이면 **계단 규칙이 점프를 보지 못한다.** $J$ = 150 bar이면 $\varphi$ ∈ (33, 67) ms에서 그렇다.
- 도구: `04_scripts/03_control/s8/r64_g4_closed_loop.py`(축소 6자유도 폐루프, 프리셋 `with_10hz_d1`, 이상 센서, FAULT_REGROUND 323절). 저장 결과 `06_analysis/02_control/s8/rev64/r64_g4_closed_loop.json`은 24행이고 wall 88.7 s, 12 워커였다.
  - 필요한 수정(python-expert): 고장을 1 ms 덩어리 단위 센서 점프로 넣는다. 지금은 "무장 시각 뒤 첫 10 Hz 표본"에 넣는다. 그리고 S4 평균 경로를 더한다.
  - 기준 팔(순간 표본)에서도 덩어리 단위 주입은 지금 동작과 같아야 한다. 무장 시각 뒤 첫 표본에 반영된다. 관문 G-4로 본다.
- 행렬: 6사례(FS24_FR/RL × F_s 0·8, quiet_FR_Fs0, G4_RR_Fs4) × 주기 안 위상 $\varphi$ ∈ {1, 20, 33, 50, 67, 90} ms × $J$ ∈ {150, 250} bar × {기준, S4} = **144행**. 행당 약 43 s(저장값)이고 12 워커면 약 9 min이다.
- 보는 것
  - 첫 `FAULT_HEAD_PRESSURE` 시각(기준 대비 주기 차)과 놓친 수
  - FAULT_REGROUND 표적·결과(G4-1 ~ G4-8, 323.7/323.9 정의)
  - `INFO_HEAD_PRESSURE_FAULT_REASON`
- 고장 없는 행의 거짓 경보는 따로 센다. 1단계 161행 전체에서 SHD 대 S4의 `FAULT_HEAD_PRESSURE`, `WARN_ROD_PRESSURE_FALLBACK`, `INFO_PRESSURE_STEP:*`(사유별), `check_draining` 보류 수, `WARN_CRAWLER_RECONTACT_SUSPECTED`를 비교한다(지표 M-11).
- v5 D1 하네스에는 헤드 고장 주입 경로가 없다. 그 경로를 새로 넣는 안과 Chrono G4H(run_S8C)는 2단계 후보다(Q-4).

## 5. 실행 행렬과 건수

| 묶음 | 변형 | 집합 | 팔 | 행 |
|---|---|---|---|---|
| I-0 사전 점검 | SHD | A_P0 5 + A_boundary 1 + F 4 + E 4(목록 앞에서부터) | K1 켬 | 14 |
| I-1 | SHD, IGA, IGB, IZ, S4 | P0 합집합 161 | K1 켬 | 805 |
| I-1k | SHD, IGA, IGB, IZ | A_P0 + A_boundary_P0 (6) | **K1 끔** | 24 |
| I-1p(선택, Q-2) | SHD, IGA, IGB, IZ | A_P5r4 (2) | K1 켬 / 끔 | 16 |
| H-F | 기준, S4 | 4.1 행렬 | 프리셋 | 144 |
| **합계** | | | | **843**(I-1p 포함 시 859) + I-0 14 |

- I-0은 I-1 전에 돈다. 관문 G-1이 실패하면 I-1을 시작하지 않는다.
- I-1 SHD 161행이 곧 기준선이다. 따로 "기준" 실행을 두지 않고 SHD 해시가 저장 해시와 같은지로 대신한다(6절 G-1).

### 5.1 비용 추정 (저장 wall_s 기준, 가정)

| 항목 | 값 |
|---|---|
| 집합별 저장 wall 합(행당 1스레드) | A 6행 0.18 h, B 0.28 h, C 1.95 h, E 1.36 h, F 0.89 h → **4.65 core-h/변형** |
| I-1 | 5 × 4.65 = 23.3 core-h |
| I-1k / I-1p | 0.73 / 약 0.5 core-h |
| 하위 클래스·1 kHz 기록 부담 | +15 %(가정, I-0에서 측정해 갱신) |
| H-F | 약 1.7 core-h(144 × 43 s) |
| **합계** | **약 29 core-h** |
| 벽시계(P 16 워커) | 약 1.9 h. 가장 긴 행은 348 s(E의 H-S-C)라 꼬리는 6 min 안쪽이다 |
| 벽시계(E 12 워커, 1.7배) | 약 4.1 h |

- 저장 wall_s를 낸 실행의 풀(P/E) 기록은 등록 전에 확인한다. K1 Y 묶음은 마스크 `0FFF5500`, 16 워커였다.
- 지금은 P코어에서 D8x 하네스가 돈다. 배치표는 compute-scheduler-expert에게 받는다. D8x가 끝난 뒤 P에서 도는 쪽을 권한다.
- Chrono는 없다. SCM 1행이 수 시간이라 1단계 범위 밖이다.

## 6. 실행 전 감사 (셋만, 사용자 결정)

| # | 항목 | 통과 조건 |
|---|---|---|
| V-1 태그 | 모든 행의 `controller_tag`가 10절 Q-1에서 고른 형식이다. 형식 (가)의 예는 `final_C4G2_LAS_K1_IDEAL-<코드>`(V0), `final_C4G2_P3_LAS_K1_IDEAL-<코드>`(VB), K1 끔 팔은 `final_C4G2_LAS_IDEAL-<코드>` / `final_C4G2_P3_LAS_IDEAL-<코드>`다. 코드는 `SHD`·`IGA`·`IGB`·`IZ`·`S4`(하이픈 없는 대문자)다. 행마다 `ideal.base_tag`(= `v5_options.controller_tag(options, config)`의 값)와 `ideal.variant`가 기록돼 있어야 한다. `v5_options.is_liftoff_slow_tag`·`is_order_gate_tag`·`is_extend_start_tag`가 IDEAL 행에서 모두 거짓이어야 하고, 이것은 의도된 동작이다 | 위반 0 |
| V-2 결과 폴더 | 결과가 `06_analysis/03_hydraulic/coupled/v5/las/ideal/`에만 있다. 묶음 파일은 `ideal_<묶음>_<코드>.jsonl`이다. 기존 `las/k1/`, `soil_defer/` 파일의 sha256이 실행 전후로 같다 | 위반 0 |
| V-3 그림자 해시 | SHD 행의 `commands_sha256`가 저장 해시와 같다. 저장 해시는 K1 켬 P0 기준으로 A_P0 = Y-Pa, A_boundary·B·C·E = S-C(K-4에 따라 `would_block` 거짓 행은 K1 끔·켬 해시가 같다), F = las_T1·T2, K1 끔 팔 = S-C다 | 161 + 6(+2) / 같은 수 |

- 관문(실행 중 도구가 본다. 감사 항목은 아니다)
  - G-1: I-0 14/14와 I-1 SHD 161/161이 V-3을 만족한다. 실패하면 멈추고 원인(코드 차이 대 하위 클래스 누출)을 분석한다.
  - G-2: IZ의 F 40행 해시가 SHD와 같다(강체에서 $z_i$ = 0).
  - G-3: IGA와 IGB의 A_P0·A_boundary 해시가 같다(예측 P-A2. 어긋나도 멈추지 않고 공개한다).
  - G-4: 두 가지를 본다. (i) 옛 주입 규칙으로 옛 24행 설정을 다시 돌리면 저장 `r64_g4_closed_loop.json`의 FAULT 시각·표적과 같다(프리셋이 K1 채택판으로 바뀌어 다르면 공개하고 (ii)만 본다). (ii) 기준 팔(순간 표본)에서 덩어리 단위 주입과 옛 주입("무장 시각 뒤 첫 표본")의 FAULT 시각·표적이 같다.
- 감사 대상 env는 dynamics-dev다. 실행 정체성(git head, dirty, 도구 sha, 스레드 = 1, `MKL_THREADING_LAYER=TBB`)은 K1 Y 묶음과 같은 블록으로 행마다 기록하지만, 감사 항목에는 넣지 않는다(가벼운 등록).

## 7. 지표와 방향 예측

### 7.1 지표 (짝 = 같은 행 id·같은 팔, SHD 대 변형)

| # | 지표 | 정의 |
|---|---|---|
| M-1 | verdict 등급 | `d1.verdict`(pass / fail / allowed_stop / fault)의 전이표 |
| M-2 | READY 시각 | $\Delta t_{READY}$ [s] |
| M-3 | FAULT·SGS 정지 수 | `FAULT_LIFT_STROKE_LIMIT`(`:soil` 포함), `FAULT_STROKE_END` 등 이름별 |
| M-4 | 행정 여유 | 682.8 mm − $s_{max}$ [mm] 분포 |
| M-5 | 이탈 뒤 최소 힘 | 참 $F_{cyl}$ 최소 − F_min [kN](F_min = 9.415 kN) |
| M-6 | P3-1·P3-5 | READY 뒤 크롤러 하중 0, 참 틈 ≥ 25 mm |
| M-7 | LOC 시각 오차 | $t_{LOC} - t_{lift}$ [s] |
| M-8 | 거짓 LOC·거짓 토양 모드 수 | 1.1절 정의(거짓 토양 모드: $t_S > t_{lift} + 0.05$ s) |
| M-9 | LOC 취소·재LOC | `INFO_LOC_REVOKED` 수, 첫 R4 LOC가 막힌 뒤 R4c30이 끝까지 없는 행(F2 경로) 수 |
| M-10 | 틈 추정 오차 | $c_{min} - g_{min}$, $c^{corr}_{min} - g_{min}$ [mm], LOC 때와 READY 때(SHD 기록) |
| M-11 | 압력 진단 사건 | 4.1절 목록의 이름별 수(S4 대 SHD) |
| M-12 | 끝 자세 | 끝 \|roll\|, \|pitch\| [deg], 데드밴드 0.03° 대비 |

### 7.2 방향 예측 (판정 아님, 등록 때 그대로 봉인)

| # | 집합·변형 | 예측 |
|---|---|---|
| P-A1 | A_P0 · IGA/IGB/IZ | IGA·IGB: 5/5에서 토양 모드가 시작되지 않고, R4c30 평가(`decisions`)가 없다. IZ: 거짓 토양 모드가 ≥ 3/5에서 사라진다(보정된 틈이 늦게 20 mm에 닿아 LOC가 먼저 온다). 확신은 낮다 |
| P-A2 | A_P0 · IGA 대 IGB | 해시가 같다(평지라 E3c10이 없고 토양 모드가 없어 R4c30도 없다) |
| P-A3 | A_P0 · IGA 대 K1 켬 SHD | $s_{max}$ 차 ∈ [0, +15] mm, 중앙 약 +9 mm. 근거: 행정 기반 추정 틈은 패치 침하만큼 부풀어 있다(K1 설계 추정 약 9 mm). 참 틈 50 mm까지 더 들어 올린다. **11-09 검토의 "≤ 1 mm" 예측을 이 값으로 바꾼다**(결과 전 변경, 공개) |
| P-A4 | A_P0+boundary · K1 끔 팔 | IGA·IGB·IZ에서 K1 끔과 켬의 해시가 같다(정보가 있으면 K1이 할 일이 없다). SHD K1 끔은 S-C 해시와 같다 |
| P-B1 | B · IGA/IGB | 거짓 LOC 0/8. $t_{LOC} - t_{lift}$ ∈ [+0.1, +0.3] s(디바운스 2주기) |
| P-B2 | B · IGA/IGB | J2 `roll+rec` 3행 가운데 P3-1이 회복되는 행 ≥ 2. `diag-rec` 2행의 SGS 정지(allowed_stop)는 ≥ 1행 남는다(행정 예산 문제가 따로 있다) |
| P-B3 | B · IZ | 거짓 LOC는 8/8 그대로다(LOC 규칙을 바꾸지 않는다) |
| P-C1 | C · IGA, IZ | $s_{max}$이 늘고(중앙 +3 ~ +12 mm), SGS 정지 수는 같거나 는다 |
| P-C2 | C · IGB | $s_{max}$이 준다(R4c30·E3c10 +30 mm가 빠지고 부풀림 보정분이 일부 상쇄해 중앙 −10 ~ −25 mm). SGS 정지 수는 같거나 준다. J2 fdown 8키 중 SGS 정지가 사라지는 키 ≥ 3 |
| P-L1 | 전체 · IGA/IGB | M-7 중앙이 +0.98 s(K1 켬 P0)에서 ≤ +0.3 s로 준다 |
| P-L2 | 전체 · IGA/IGB | `INFO_LOC_REVOKED` 수와 F2 경로 수가 같거나 준다 |
| P-E1 | E, F · 모든 변형 | 새 fail ≤ 1/80 짝(IGA·IGB·IZ 각각). \|$\Delta t_{READY}$\| ≤ 2 s인 짝 ≥ 90 % |
| P-F1 | F · IZ | 40/40 해시가 SHD와 같다(G-2) |
| P-S1 | 전체 · S4 | 해시는 거의 모든 행에서 바뀐다(≥ 150/161). verdict 전이는 ≤ 3행이다. M-5 하한 추정의 주기 간 흔들림(표준편차)이 준다 |
| P-S2 | 전체 · S4 | 물리 계단이 평균으로 퍼져 `INFO_PRESSURE_STEP:*`이 준다. `check_draining` 비율 규칙(ρ = 0.5, 순간 표본으로 보정한 값)이 어긋나 `WARN_ROD_PRESSURE_FALLBACK`이 같거나 는다 |
| P-S3 | 전체 · S4 | D1″ 정렬이 깨져 거짓 `FAULT_HEAD_PRESSURE`이 ≥ 1행에서 생길 수 있다. 정렬 잔차 기록 $\bar r$의 최대 \|변화\|/(\|Δp_h\|A_p)는 순간 잔차보다 작다 |
| P-H1 | H-F · S4, $J$ = 150 bar | 계단 규칙이 $\varphi$ = 50 ms에서 놓친다(6사례 모두). $\varphi$ = 33·67 ms는 경계다(100 bar 근처, 수치 오차로 갈린다). $\varphi$ ≤ 20 ms는 같은 주기, $\varphi$ = 90 ms는 한 주기 늦게 잡는다 |
| P-H2 | H-F · S4, $J$ = 250 bar | 모든 $\varphi$에서 잡는다. $\varphi$ ≥ 67 ms에서는 한 주기 늦다 |
| P-H3 | H-F · S4 | 놓친 행의 FAULT는 다른 검사(범위·D2 상계)로 늦게 오거나 끝까지 없다. 이 경우 G4-4(재접지 뒤 최소 힘)가 나빠지는 행이 생긴다 |

- 예측은 판정 기준이 아니다. 어긋나면 그대로 공개한다.
- 상한 문구 예: "정보 IGB로 집합 C의 SGS 정지가 a → b", "S4로 $J$ = 150 bar 헤드 점프 탐지 누락이 0 → k/36".

## 8. 구현 명세 (python-expert)

1. `04_scripts/04_hydraulic/coupled/ideal_sensor_targeted.py`
   - `IdealSensorC2(C2Controller)` 하나에 변형 플래그(`SHD`/`IGA`/`IGB`/`IZ`/`S4`)를 둔다. 3절의 메서드만 덮어쓰고, SHD에서는 기록만 한다.
   - `IdealSource`: 하네스 래퍼가 매 주기 채우는 읽기 전용 참값($\chi_{cr}$, $g_k$, 노드 최소, $z_i$, `soil.sp`, $\bar p$, $\bar f_z$)이다. 제어기는 명목 파라미터만 쓴다.
   - K1 관문: 프리셋 값을 쓰되, K1 끔 팔은 False를 **명시적으로 설치**한다(D8x `install_k1_order_gate` 결함과 같은 조용한 실패를 막기 위해서다). 행마다 `c2_setup.k1_order_gate`와 그 실제 값(effective)을 기록한다.
2. `control_period` 래퍼(1 ms 덩어리 누적)
   - `crmax`, 귀퉁이 간극, 압력 100표본 평균(센서 오차는 덩어리마다)을 계산한다.
   - S4에서만 평균값으로 `Measurements`를 만든다. 다른 변형은 순간 표본 그대로다.
3. 기록 블록 `ideal`: `variant`, `base_tag`, 키 목록 sha, 주기별 그림자(`chi_cr`, `g_min`, `c_min`, `c_corr_min`, `z`, `r_dsb_ideal`, `r_bar_aligned`), 거짓 토양 모드·거짓 LOC 표시, 이상 LOC 결정 시각
4. 러너: `--bundle I-0|I-1|I-1k|I-1p --variant ...`, `--keys-file ideal_stage1_keys.json`(sha 대조), `--resume`, `--workers`, `--affinity`. 실행 정체성 블록은 `k1_targeted.run_identity`와 같은 형식으로 한다.
5. H-F: `r64_g4_closed_loop.py`에 덩어리 단위 주입과 S4 경로를 더한다. 원본을 고치지 않고 감싸는 별도 파일로 하는 쪽이 낫다. G-4 시험을 함께 낸다.
6. 시험
   - SHD 해시 불변(대표 3행)
   - IZ 강체 해시 불변
   - IGA LOC 규칙 단위 시험(2주기, 히스테리시스)
   - S4 평균값(상수 압력 → 같은 값, 계단 → 두 주기 분할)
   - 태그 술어가 IDEAL 행에서 거짓인지
   - K1 끔 팔 관문 False가 실제로 걸렸는지
7. 태그 소비 도구 보호: `t4h_replay.py`(120행, 태그에서 관문을 추론)와 `chrono_t45_replay.py`(907·920행)가 IDEAL 태그를 만나면 조용히 관문 끔으로 재생한다. IDEAL 태그면 거부하도록 하거나, 최소한 그 사실을 시험으로 고정한다(형식 (가)를 고를 때).
- 집계: 경로 1은 python-expert의 `ideal_stage1_judge.py`다. 경로 2는 control-expert의 독립 재집계(프로젝트 모듈을 import하지 않음)다. 판정 등급이 없으므로 두 경로는 지표 값이 같은지만 본다(수치 허용 1e-9).

## 9. 신호 정의 확인 질문 (실행 전, dynamics-expert · terramechanics-expert)

| # | 대상 | 질문 |
|---|---|---|
| Q-D1 | S1a 접촉(dynamics) | 하네스 크롤러 콘크리트 스프링 압축(약 3.8 mm)과 끝 슈 간극 노드를 "접촉"으로 셀지. $\chi_{cr}$ = "1 ms 덩어리 중 하나라도 $F_{cr} > 0$"이 접촉 스위치(리밋 스위치·압력 매트)의 이상화로 맞는지, 아니면 하중 문턱(예: > 1 kN)이 필요한지 |
| Q-D2 | S1b 기준면(dynamics) | 간극을 (가) 변형 표면(바퀴 자국)까지 잴지, (나) 미변형 표면(트랙 밖 레이저)까지 잴지. 하네스는 바퀴 자국이 없어 둘이 같다. P3-5(바퀴 자국 틈 ≥ 25 mm)와 기준을 맞출지. 귀퉁이 4점 대 노드 최소 중 무엇을 $g_{min}$으로 할지 |
| Q-D3 | S2 힘 관계(dynamics, 2단계용) | $F_{pad}$와 $F_{cyl}$의 관계(실 마찰 $F_s$, 로드 무게·관성, 구면 조인트). 2단계 전에 답을 받는다 |
| Q-D4 | S3 기준면(dynamics) | `plant.soil.z`(하네스)와 `m.pad_sinkage_m()`(SCM 평면 기준)이 같은 양인지. 패드 기울기에서 패드 중심과 귀퉁이 중 무엇을 쓸지 |
| Q-T1 | S3 기준면(terramechanics) | 실제 지면 거리계는 패드 옆 미변형 표면 + 융기(bulldozing)를 본다. 소성 침하·융기를 어떻게 나눠 "침하"로 줄지. J1·J2 세트에서 융기 크기의 근거 범위 |

- 답이 1단계 정의를 바꾸면 등록본에 반영한다. 등록 뒤에 바뀌면 공개한다.

## 10. 확인 필요 (사용자 결정)

| # | 질문 | 선택지 | 추천 |
|---|---|---|---|
| Q-1 | K1 채택 뒤 태그 형식 | (가) 접미사 `<base_tag>_IDEAL-<코드>`. 예: `final_C4G2_LAS_K1_IDEAL-IGA`, `final_C4G2_P3_LAS_K1_IDEAL-IGA`, K1 끔 `final_C4G2_LAS_IDEAL-IGA`. 기존 술어(`_LAS`·`_K1`·③)가 모두 거짓이 되어 기존 집합에 섞이지 않는다. 대신 태그에서 관문을 추론하는 재생 도구 2개는 IDEAL 행을 거부해야 한다(8절 7). (나) 중간 삽입 `final_C4G2_IDEAL-<코드>_LAS_K1`. 술어가 참이 되어 `_LAS`·`_K1` 집합에 섞인다. (다) 표준 태그 그대로 + `ideal.variant` 필드만. 폴더 분리에만 기댄다 | **(가)** |
| Q-2 | A_P5r4 2행(I-1p 16행) 포함 | (가) 넣음(약 0.5 core-h, P5r4+K1 재판정과 함께 쓸 수 있다) (나) 뺌(채택 프리셋 P0만) | P5r4+K1 재판정이 진행 중이면 **(가)**, P5r4를 접었으면 (나) |
| Q-3 | S4와 D1″ 정렬 | (가) S4는 압력만 평균하고, 정렬 잔차는 기록만 한다 (나) S4a 변형(D1″ $f_z$도 같은 창 평균)을 1단계에 추가한다(+161행, 약 5.4 core-h). 하위 클래스가 감시기 읽기 경로를 덮어써야 한다 | **(가)**. 거짓 헤드 고장이 나오면 S4a를 2단계에 넣는다 |
| Q-4 | 헤드 고장 회귀 도구 | (가) `r64_g4` 축소 폐루프 144행(약 9 min, 플랜트는 옛 축소 모델) (나) v5 D1 하네스에 주입 경로를 새로 넣는다(코드 약 150줄 추가) (다) Chrono G4H(수 시간) | **(가)**. (나)·(다)는 2단계 |
| Q-5 | I-G 임계값(가정) | LOC 간극 2 mm, 히스테리시스 1 mm, 디바운스 2주기, 취소 1주기를 그대로 둘지 | 그대로(Q-D1 답에 따라 조정) |
| Q-6 | 실행 시점 | D8x 하네스(P) 뒤 P 16 워커(약 1.9 h) 또는 지금 E 12 워커(약 4.1 h) | D8x 뒤 P. 시작은 승인 뒤 |

## 11. 사전 집계에 쓴 것 (재현)

- 스크립트(control-expert scratchpad `ideal1\`, dynamics-dev `python -I`, 모두 읽기 전용)
  - `prescreen_k1arm.py` → `prescreen_k1arm.json`(1.1·1.2절)
  - `key_sets.py` → `key_sets.json`(4절 집합, 비용 wall 합)
  - `write_keys.py` → 이 폴더의 `ideal_stage1_keys_draft.json`
- 11-09 사전 집계 원본은 이전 세션 scratchpad의 `ideal_sensor\prescreen.py`다.
- 읽은 저장 파일
  - `v5/las/k1/k1_Y{0,P,S,T}.jsonl`
  - `v5/soil_defer/s2d_SC.jsonl`(sha `70e91ec1…08aa`), `v5/soil_defer/judge_S.json`
  - `v5/las/las_T1.jsonl`, `las_T2.jsonl`
  - `07_results/S9/batch_V5-LAS-K1-REM_20261109_235554/*/result.json`, `batch_V5-LAS-K1-CHRONO_20261109_193952/*/result.json`
  - `06_analysis/02_control/s8/rev64/r64_g4_closed_loop.json`

## 12. 한계

- 모든 근거는 하네스다. 하네스는 LOC 지연(1.2절)과 J1 패치에서 낙관 쪽이다. 1단계는 효과의 방향과 상한의 크기를 보는 것이고, 실기 이득을 보증하지 않는다.
- 이상 신호는 잡음·바이어스·탈락이 0이다. 실기 센서로 옮길 때의 오차(간극계 1~2 mm 잡음·진흙 반사·로킹 앨리어싱, 거리계 융기·식생)는 2단계에서 다룬다.
- H-F의 플랜트는 v5 유압 연성 하네스가 아니라 옛 축소 폐루프다. D1 계단 규칙의 탐지·누락은 판독 경로만의 문제라 결론의 방향은 옮겨 쓸 수 있다. 다만 FAULT_REGROUND 결과(G4-4 등)의 크기는 v5 플랜트에서 다를 수 있다.
- S4의 1 kHz 평균은 실기 수집 장치(1 kHz ADC, 디지털 필터 군지연)가 되는지를 전제한다. 하드웨어 확인 U-R8-9 ⑤의 타임스탬프 정렬 조건과 함께 봐야 한다.
