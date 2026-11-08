# v5 유압 연성 인수 기준 — 개정 8 (v5 VB 정의에 ③ revision 4 포함, ext_moving 판정 항목, 채택 조건 4 면제 기록)

작성: control-expert, 2026-11-08.

> **상태: 봉인(2026-11-08).** SHA-256과 봉인 시각은 같은 폴더 `v5_criteria_rev8.sha256`에 있다. 이 파일은 더 고치지 않는다.
> - **결과를 본 뒤의 결정이다.** ③ 채택은 Dg-2 v4, Dg-3 v4(135키), 3단계 Chrono 판정(`stage3_judgement.md`)을 모두 본 뒤에 정했다. 특히 **채택 권고 조건 4(과보수 p90 증가 ≤ 2 kN) 미충족을 Dg-3 v4 폐루프 근거로 면제**했다(4절). 이 면제는 결과를 보기 전에 정한 권고 조건을 결과를 보고 푼 것이다.
> - 사용자 결정(2026-11-08, `decision_log.md` 4절 "사용자 결정(11-08): ① ③ revision 4 채택…"): ① ③ revision 4 채택(v5 VB 정의에서만 켬, 태그 `final_C4G2_P3`), 모니터 재신장은 ③이 해결(안 A 구현 안 함), ext_moving `breach_reads` = 0 판정 항목화, 수축 이동 중 초과는 한계. ② 조건 4 미충족은 Dg-3 v4 폐루프 근거로 면제하고 개정 8·논문 한계에 명시.
> - **적용 시점**: 봉인 뒤의 모든 VB·LS 판정. 저장 결과는 7절의 해시 대조를 통과하면 그대로 `final_C4G2_P3` 결과로 읽는다(새 실행 없음). 대체 135키는 Dg-3 v4 결과로 바꿔 넣는다.

**고치는 판**: 아래 여덟 판을 순서대로 덮어 읽은 판이다. 앞 판들과 각 `.sha256`은 고치지 않는다. 여기 적지 않은 항목은 앞 판 그대로다.

| 판 | 파일 | SHA-256(앞 16자리) |
|---|---|---|
| 봉인본 | `v5_criteria.md` | `06ed0384fb942cfd` |
| 개정 1 | `v5_criteria_rev1.md` | `cbfac2b2de571500` |
| 개정 2 | `v5_criteria_rev2.md` | `e120474b8ebd721e` |
| 개정 3 | `v5_criteria_rev3.md` | `7084da25c6129681` |
| 개정 4 | `v5_criteria_rev4.md` | `642e96f9cfd20a9c` |
| 개정 5 | `v5_criteria_rev5.md` | `945f714660cd3ec7` |
| 개정 6 | `v5_criteria_rev6.md` | `fd5117031ef460cf` |
| 개정 7 | `v5_criteria_rev7.md` | `9ccde7a5a4128317` |

규약: 음되먹임 $u=r-y$ 경로, $T_s$ 0.1 s(10 Hz), 출력 지연 $d$ = 1, 압력 bar(게이지), 힘 kN, 시각 s. 상태 되먹임·관측기 식은 쓰지 않는다(이 판은 대체 경로 추정기와 판정 정의만 다룬다).

## 1. 개정 번호·사유

| 항목 | 내용 |
|---|---|
| 개정 번호 | 개정 8 |
| 종류 | (1) VB 정의 변경: 제어기에 ③ `extend_start_rule = "tracked_bound"`(revision 4)를 넣는다. (2) 판정 항목 추가: `extend_bound_check` ext_moving `breach_reads` = 0. (3) 이름 정리: `T4h-P3` → VB T4h, `T4-P3` → VB T4. (4) 대체 행 판정 출처를 Dg-3 v4로 바꾼다. (5) 채택 권고 조건 4 면제의 기록. 문턱 0.6 kN, J1~J11, H-1~H-19, 개정 7의 E·B1은 바꾸지 않는다 |
| 사유 | 사용자 결정 2026-11-08 ①·②. 근거는 `p3_extend_start_spec.md` 12·13절(Dg-2 v4, Dg-3 v4)과 `stage3_judgement.md` 2절(Chrono 23행 신장 이동 중 초과 641 → 0) |
| 결과를 본 상태 | 1·2단계 r5 전부, 3단계 Chrono 34건·시드 확장 100건·3단계 판정·H-7 추가 분석, Dg-2 v4(398기록), Dg-3 v4(135키 꺼짐·켬), 모니터 재신장 설계안 오프라인 재생을 보았다(6절) |

## 2. 바뀌는 항목

| # | 앞 판 위치 | 앞 판 문구 | 새 문구 |
|---|---|---|---|
| 1 | 봉인본 8절 VB 행 "v5 기준 구성" | 플랜트 옵션(유량 $\eta_v$ 0.85 priority, M2, LC 0.02 / 0.05 s, 창이 플랜트를 따름, $\tau_v$ 0.1 s) + 제어기 `final_C4G2` | 플랜트 옵션 그대로 + 제어기 **`final_C4G2_P3`** = `final_C4G2` + `TwoPressureSettings.extend_start_rule = "tracked_bound"`(revision 4, 매개변수는 `p3_extend_start_spec.md` 3절 표 기본값). 3.1절 |
| 2 | 봉인본 8절 LS1~LS4 | VB 위 LC 감도 | 같은 `final_C4G2_P3`(VB와 제어기가 같아야 LS − VB가 LC 감도만 뜻한다) |
| 3 | 봉인본 9절 T4h, 개정 6 14.5 `T4h-P3`(기록) | T4h = 실행 설정(③ 꺼짐) 재생, `T4h-P3` = ③ 켬 재생 기록 | **VB·LS T4h = ③ 켬 설정으로 재생한 값**(판정). 이름 `T4h-P3`는 쓰지 않는다. ③ 꺼짐 재생은 `T4h-const`(기록)로 부른다. 판정 표본·문턱은 앞 판 그대로(잠긴 표본 판정, 꼬리 기록) |
| 4 | 개정 6 4.7 `T4-P3`(Chrono, 기록) | ③ 켬 재생은 기록 | 봉인 뒤 VB·LS Chrono 실행은 meta에 ③ 켬이 들어 있으므로 4.1 "감시기 설정 재구성"이 그대로 ③ 켬 감시기를 만든다. 그 T4·T5가 판정이다(개정 7 E·B1 적용). **3단계 저장 18행(③ 꺼짐 실행)의 판정 문구는 바꾸지 않는다**(개정 6 `불일치` 확정 + 개정 7 참고 재판정). 그 행의 ③ 켬 재생은 기록으로 남는다 |
| 5 | 없음 | - | **새 판정 항목 J-P3**: VB·LS 모든 실행(하네스, Chrono L2b, SCM)에서 `hydraulics_record.extend_bound_check`의 ext_moving `sum(breach_reads)` = 0. 3.2절 |
| 6 | 봉인본 10절 잡음 L2·L3 VB | r5 VB 잡음 출력 | 대체 다리가 있는 135키(L2 1, L3 134, `dg3_keys.txt`)는 **Dg-3 v4 켬 결과**(`dg3/dg3_v4_on.json`, T4h형 `dg3/v4_on_t4h/`)로 바꿔 넣는다. 나머지 키는 r5 VB 결과 그대로(T8, 7절 해시 대조로 확인) |
| 7 | `p3_extend_start_spec.md` 5절 채택 권고 조건 4 | 과보수 p90 증가 ≤ 2 kN(기록, 넘으면 비용으로 적음) | **미충족, 면제**(사용자 결정 ②). 4절 |

## 3. 정의

### 3.1 VB 제어기 `final_C4G2_P3`

| 항목 | 값 |
|---|---|
| 기준 | `final_C4G2`(명세 433.1). 프리셋 `C2Config.with_10hz_d1()`의 `extend_start_tracked` 기본값은 **꺼짐 유지**, `TwoPressureSettings` 클래스 기본값 `"constant"` 유지. 그래서 `final_C4G2` 태그의 저장 결과·명령 해시는 바뀌지 않는다 |
| 켜는 곳 | v5 VB 정의에서만: 하네스 VB·LS1~LS4 설정, Chrono `s9_batch.v5_vb_argv()`로 만드는 VB 행과 그 LS 행 |
| 켜지 않는 곳 | V0~V3, L1, L2(제어기 `final_C4G2`). V4~V8(M1c 신장 쪽과 ③ 조합은 설정 단계에서 거부, `v5_options.check_extend_start`) |
| revision | 4(잠김 → 신장 첫 주기 전 $\hat p\leftarrow\max(\hat p, ④)$). revision 3 이하 meta는 재생 거부 |
| 대체가 없는 실행 | 추적기 값이 힘 하한에 들어가지 않으므로 명령은 ③ 꺼짐과 비트 동일(T8). meta에만 `extend_start_rule`, `extend_start_revision`, `extend_bound_check`가 더해진다 |
| V0·VB 짝의 뜻 | 대체 다리가 있는 실행에서만 VB − V0에 ③ 몫이 섞인다. 그런 실행은 표에 `대체 있음`으로 표시한다 |

### 3.2 J-P3: 신장 이동 중 상계 위반

| 기호 | 뜻 | 단위 |
|---|---|---|
| $p_{tr}$ | 플랜트 로드측 추적 압력 진값(`extend_bound_check` 입력) | bar |
| $\hat p$ | ③ 추적기 상계(다리별, 10 Hz 판독마다) | bar |
| $\delta_m$ | 상계 여유 0.5 bar(`p3_extend_start_spec.md` 6절, 가정) | bar |
| ④ | 모니터 모델 상계(잠긴 구간, 판독 상계 ⑤를 합치기 전) | bar |

- **ext_moving(판정)**: 작용 명령 > 0(신장 이동)인 판독에서 $p_{tr}>\hat p+\delta_m$인 판독 수 = `breach_reads`. 실행의 네 다리 합이 **0이면 통과**, ≥ 1이면 **H-7**(대체 경로 `불일치`, 멈춤)이다. 추적기는 모든 다리에서 그림자로 돌므로 대체 다리가 없는 실행도 이 항목을 시험한다.
- `margin_used_reads`($p_{tr}>\hat p$) > 0: FLAG(기록).
- ext_locked: `locked_breach_over_tol_reads` > 0이면 FLAG(교차 확인). 잠긴 표본의 판정은 VB T4h(하네스)·VB T4(Chrono)다.
- `extend_bound_check`가 없거나 `null`인 VB·LS 실행: 설정 결함, 판정하지 않고 멈춘다.
- 정의의 원본은 `03_src/outrigger_sim/control/extend_start_bound.py`의 `ExtendBoundCheck` docstring(revision 4 시점)이다.

## 4. 채택 조건 4 면제 (결과를 본 뒤의 결정)

| # | 조건(사전, `p3_extend_start_spec.md` 5절) | 값 | 판정 |
|---|---|---|---|
| 1 | Dg-2 켬 잠김·꼬리 초과 0 | 잠김 0, 꼬리 129(하네스 꼬리 인공값, 기록) | 잠김 충족 |
| 2 | Dg-3 L2 통과→실패 0, 새 FAULT 0, 첫 READY +30 s 초과 0 | 0 / 0 / 0(READY 최대 +12.3 s 1키) | **충족** |
| 3 | T-P3-5 T8 비트 동일 | 20/20 | 충족 |
| 4 | Dg-2 과보수 p90 증가 ≤ 2 kN | 구간 끝 +4.1 kN, 신장 뒤 구간 끝 +8.7 kN | **미충족 → 면제** |

- **면제 근거**(`p3_extend_start_spec.md` 13.3절): 조건 4는 개루프 대리 지표다. 과보수(하한 < 진값)는 안전 쪽이고, 대가는 대체 다리의 ABOVE가 늦어 재접근이 길어지는 폐루프 비용이다. 조건 2가 그 비용을 실제 대체 135키 폐루프에서 직접 쟀다. 판정은 키별로 꺼짐과 같고(L2 0 / L3 9), 새 FAULT 0, READY는 1키만 +12.3 s다.
- **면제는 결과를 본 뒤의 결정이다.** 조건 4는 결과를 보기 전에 정한 권고 조건이었다. 조건 4를 지키려면 보수 매개변수(B 호스 계수 1.40, $\bar C_r$ 감도 끝값)를 줄여야 하는데, 그러면 상계 주장(3절)이 약해진다. 이번 범위에서는 하지 않았다.
- **남는 위험(논문 한계에 적는다)**: 실제 대체가 있는 Chrono 폐루프는 없다(3단계 실제 대체 0, J11). Chrono 개루프 재생의 신장 이동 과보수 꼬리는 p99 11.6 kN, 최대 45.4 kN이다(재설계안 3.1절). 하네스 폐루프에서는 판정 영향이 없었다.

## 5. 재신장 낙관과 수축 이동 중 초과

| 항목 | 처리 | 근거 값 |
|---|---|---|
| 기본 모니터 신장 이동 추정(13 bar 상수)의 낙관 | **③이 해결**. ③ 켬이면 신장 이동 추정이 $\max(13\ \text{bar}, \hat p+\delta_m)$가 된다. 안 A(`moving_extend_rule = "tracked"`)는 구현하지 않는다 | Chrono 3단계 23행 오프라인: 신장 이동 중 하한 − 진값 > 0.6 kN 641 → 0. Dg-3 v4: ext_moving `breach_reads` 0(최소 간격 0.50 bar), 실제 대체 다리 이동 중 > 0.6 kN 1,407(최대 13.13 kN) → 1,088(3.31 kN), 남은 것은 모두 L3 센서 오차 몫(13.2절 귀속) |
| 수축 이동 중 초과 | **알려진 한계**(판정 항목 아님). ③는 신장 쪽만 다룬다. H-7 처리(개정 7)가 수축 추정 수정을 고르지 않았다 | Chrono 3단계 23행 993 표본, 최대 10.6 kN(실 마찰 기전). Dg-3 실제 사건 재생 168 |
| 기록 | Chrono T4 판정마다 이동 중 표본 비교(하한 − 진값, 작용 명령 ≠ 0, 신장·수축 따로)를 기록한다 | 개정 6·7에서 이동 중 표본은 판정 표본이 아니다 |

## 6. 개정 7과의 관계와 결과를 본 뒤 바꾼 사실

- **개정 7의 E(CHECK 공중 수축 꼬리 제외)·가드·B1(센서 오차 행 고유분)은 그대로 유효하다.** 다음 Chrono T4·T5 판정부터 적용하는 전향 규칙이라는 점도 같다. 봉인 뒤의 VB Chrono 실행은 ③ 켬이므로, 그 판정은 ③ 켬 감시기 + 개정 7 규칙으로 한다.
- 개정 7 5절의 3단계 참고 재판정(T4 75 → 0, T5 104 → 0)은 ③ 꺼짐 실행 설정의 값이다. 3단계 ③ 켬 재생에서도 T4·T5 원 초과는 75 / 104로 꺼짐과 같았다(`p3_extend_start_spec.md` 12절 읽기). 초과 기전(수축 꼬리, 센서 오차 행)이 ③과 무관하기 때문이다.

| 시점(11-08) | 본 결과 | 바꾼 것 |
|---|---|---|
| 새벽 | 3단계 판정 전부, 신장 이동 중 641 → 0(③ 켬 재생) | 없음 |
| 오전 | H-7 추가 분석, 개정 7 봉인 | 개정 7 |
| 오전 | Dg-3 v4(135키), 모니터 재신장 E-6 재구성(135/135 재현, 안 A 잔여 921 = L3 센서 몫) | 판정서 13절, 결정 묶음 |
| 이 판 | 위와 같음 | 사용자 결정 ①·②로 VB 정의·J-P3·조건 4 면제를 봉인 |

## 7. 재실행 범위와 해시 대조 (메인 세션 실행용)

### 7.1 범위

| 묶음 | 처리 | 새 실행 |
|---|---|---|
| 1단계 VB 100·LS 288·item8 VB 6·overlap VB 4 | 대체 다리 0(저장 `main.jsonl`·`item8.jsonl`·`overlap.jsonl`의 `FALLBACK` 사건 행 0) → T8로 그대로 | 없음(7.2 표본 대조) |
| 2단계 격자 768 VB, 잡음 L1 171 VB | 대체 0(`stage2_judgement.md` 677·751행) → 그대로 | 없음 |
| 2단계 잡음 L2·L3 VB, 대체 없는 키 | 그대로 | 없음 |
| 2단계 잡음 L2·L3 VB, 대체 135키 | **Dg-3 v4 켬 결과로 바꿔 넣는다**(2절 #6). 판정: L2 실패 0(키별 꺼짐과 같음), L3 9(기록), J-P3 통과(ext_moving 0), 새 FAULT 0 | 없음(이미 실행, 2026-11-08 08:05, 오류 0) |
| 3단계 Chrono VB 12·LS 6·토양 VB 11 | 실제 대체 0(J11) → 명령 불변. 판정 문구는 2절 #4대로 그대로 | 없음(7.3 표본 대조) |
| 1단계 참고 V5·V7 대체 행 | VB가 아니므로 대상 아님(M1c 조합은 거부) | 없음 |
| 검증 행렬 D-1, U-3 하네스 V0·VB 짝 | 처음부터 `final_C4G2_P3`(VB 쪽)로 돈다 | 그 묶음의 실행 |

**전제(python-expert 구현, 03_src·04_scripts)**: (a) 하네스 VB·LS1~LS4 설정이 제어기 ③ 켬으로 돈다(`run_v5.py` 설정·잡음 러너). (b) `s9_batch.v5_vb_argv()`와 Chrono 러너에 ③ 켬 인자. (c) 결과 meta의 제어기 태그 `final_C4G2_P3`. (d) 프리셋·클래스 기본값 불변 시험(T-P3-1)과 T-P3-5. (e) `t4h_replay`·`chrono_t45_replay`가 ③ 켬 실행의 meta에서 감시기 설정을 재구성한다(지금은 `--extend-start tracked_bound` 덮어쓰기; ③ 켬 meta면 덮어쓰기 없이 같은 설정이 나와야 개정 6 4.1 설정 비교가 성립). 이 구현 커밋 뒤에 7.2·7.3을 돌린다.

### 7.2 하네스 대조 22행 (사례마다 1행)

- 입력: `06_analysis/03_hydraulic/coupled/v5/main.jsonl`(r5, ③ 꺼짐)의 `job.setting` = `"VB"`인 행 가운데 사례(`job.case`)마다 파일 순서상 첫 행. 앞 계획의 "20행"(T-P3-5 표본)은 저장소에 목록이 없어 이 규칙으로 다시 정했다(22사례 모두 덮음).
- 실행: 아래 `job` 22개를 ③ 켬 VB로 돌린다(새 묶음 이름 예: `p3_hash`, 출력 `06_analysis/03_hydraulic/coupled/v5/p3_hash.jsonl`). 저장 벽시계 합 1,362 s → 8 worker면 약 3~4분.
- **기대(모두 만족해야 통과)**: ① `commands_sha256`이 저장 행과 64자리 같다. ② `event_names`·`events`가 같다. ③ `hydraulics_record`에서 ③ 관련 키를 뺀 나머지가 같다. ④ `extend_bound_check`가 `null`이 아니고 ext_moving `sum(breach_reads)` = 0. ⑤ meta `extend_start_rule` = `"tracked_bound"`, revision 4.

| # | `main.jsonl` 줄 | `job` | 저장 `commands_sha256`(앞 16자리) |
|---|---|---|---|
| 1 | 1111 | R1, eps 0.002 | `c92c0efbe2749d36` |
| 2 | 456 | R2, eps 0.002 | `1d7bfdcedda80de5` |
| 3 | 1131 | R3, eps 0.0 | `48a1645a52982257` |
| 4 | 1135 | R4, eps 0.0 | `37bf35d552db9c87` |
| 5 | 1112 | R5, eps 0.002 | `9e3bb5ec28929b94` |
| 6 | 1114 | R6, eps 0.002 | `31b7fda934bfc2ae` |
| 7 | 462 | R7, eps 0.0 | `2e2db1dee90e32bc` |
| 8 | 1119 | R8, eps 0.0 | `ee8a997c6f376353` |
| 9 | 1125 | R9, eps 0.0 | `a406023b22068b81` |
| 10 | 1126 | R10, eps 0.002 | `3c0a2db2be99f425` |
| 11 | 1129 | R11, eps 0.0 | `01f858de27430745` |
| 12 | 397 | R12, eps 0.0, offset 0.0, twin top FL $F_s$ 8 | `0df0c58b04c1aa46` |
| 13 | 430 | R14, eps 0.0, offset 0.05 | `887f84e528f7e6e3` |
| 14 | 427 | R15, eps 0.0, offset 0.05 | `55bca14142a32c9b` |
| 15 | 426 | R16, eps 0.0, offset 0.05 | `25f053f17fc5c46e` |
| 16 | 431 | S1, eps 0.0 | `ceb20b3ce24d9ade` |
| 17 | 1139 | S2, eps 0.002 | `8aa56d2a11369896` |
| 18 | 1132 | S3, eps 0.0 | `c109a7edbba77f82` |
| 19 | 441 | S4, eps 0.0 | `53a664eedb44e20e` |
| 20 | 449 | S5, eps 0.0 | `63fe4c965a162fb7` |
| 21 | 447 | S7, eps 0.001 | `4b3ef58da2d7ba30` |
| 22 | 445 | S8, eps 0.0 | `6f9b39edd3513398` |

비교는 저장 행의 64자리 전체로 한다(표는 식별용 앞 16자리).

### 7.3 Chrono 대조 2행 (L2b VB, 강체)

| 행 | 저장 실행(③ 꺼짐) | 고른 이유 | 저장 벽시계 |
|---|---|---|---|
| `E_G4_Fs8` | `07_results/S8/v5s3_VB_E_G4_Fs8_20261107_214226/E_G4_Fs8` | G4 급침하 사건, $F_s$ 8(CHECK 수축 꼬리, 개정 7 E 표본 2), 3단계 T4 판정 행 | 1,341 s |
| `S_top_fdown3.5_wika_Fs8` | `07_results/S8/v5s3_VB_S_top_fdown3.5_wika_Fs8_20261107_222708/S_top_fdown3.5_wika_Fs8` | 센서 오차 모델 행(B1 대상), RR 잠김 REANCHOR | 1,164 s |

- 실행: `07_results/S9/batch_V5-STAGE3_20261107_184341/batch.json`의 같은 행 `argv`(`run_S8C.py run --set … --only <case> … --lock-window-follows-plant`)에 ③ 켬 인자를 더하고 태그만 `v5p3_VB_<case>`로 바꾼다. P코어 2건 동시면 약 23분(저장 벽시계 기준, 경합 보정 전).
- **기대(모두 만족해야 통과)**: ① `record/record.npz`의 아래 네 배열이 비트 동일(`np.ascontiguousarray(a).tobytes()`의 SHA-256, P3-10 규약). ② `controller_events.json`의 사건 목록(이름·시각)이 같다(파일 바이트가 아니라 내용 비교; 경로·시각 문자열이 섞일 수 있다). ③ `result.json` 제어기 meta 차이가 ③ 키(`extend_start_rule`, `extend_start_revision`, `extend_bound_check` 내용)뿐이다. ④ ext_moving `sum(breach_reads)` = 0.

| 행 | 배열 | 모양 | 저장 SHA-256 |
|---|---|---|---|
| E_G4_Fs8 | `u_applied` | 948 × 4 | `793b816e769074229e598f29b8e6825b473814a305f79482ba60bcee1c3fb8ef` |
| E_G4_Fs8 | `u_cmd` | 948 × 4 | `d7df90542d137a00ed090233be76a33009e6e9345ae63915c487964b9496ec22` |
| E_G4_Fs8 | `F_cyl` | 948 × 4 | `3823afd977545ab0c3229f5ffa6d11514e63c047f817a7ffd2ac0a781e8dd2cd` |
| E_G4_Fs8 | `body_quat_wxyz` | 948 × 4 | `625e1e07d0512595a2adb4aeae7ef6d9f6cf55fe824dc9102c9c98879c00cc06` |
| S_top_fdown3.5_wika_Fs8 | `u_applied` | 890 × 4 | `fc63355085b78c7bcd693999d7c7d9055e80d9d986b58ba85d32e3b6c27d6d2b` |
| S_top_fdown3.5_wika_Fs8 | `u_cmd` | 890 × 4 | `867634ce5d6a95de22ffc8474068e9ea5a95416bf5f98313ff315ae76d1d5815` |
| S_top_fdown3.5_wika_Fs8 | `F_cyl` | 890 × 4 | `19de3e78afbbe052ae1a8f5b98525377aabc82966f03e5e4e099ca19df85f70e` |
| S_top_fdown3.5_wika_Fs8 | `body_quat_wxyz` | 890 × 4 | `70a4da9df199a2a2a661bf54ca12fd36efa9c471b1421c054abe727408f550af` |

(저장 값은 control-expert가 2026-11-08에 저장 `record.npz`에서 계산했다. 계산 스크립트는 대조 도구에 다시 구현한다.)

### 7.4 판정

| 결과 | 처리 |
|---|---|
| 22 + 2 모두 통과 | 7.1 표대로 저장 VB·LS 결과를 `final_C4G2_P3` 결과로 읽는다. 대체 경로 문구는 앞 판 규칙 그대로(3단계 확정 `불일치` + 개정 7 참고) |
| 하나라도 명령·사건이 다름 | **멈춤.** T8 결함(대체 없는 실행에서 ③가 명령에 닿음)으로 python-expert에 넘긴다. 저장 결과를 ③ 결과로 읽지 않는다 |
| ④ ext_moving 위반 ≥ 1 | H-7(J-P3 실패). 멈추고 묻는다 |
| SCM 토양 행 | 대조하지 않는다(실제 대체 0, 1행 약 8,800 s). 대체가 생기는 SCM 실행이 나오면 그 행만 다시 본다 |

## 8. 판정 문구 영향

| 단계 | 앞 문구 | 이 판 뒤 |
|---|---|---|
| 1단계 | 합격(로드 센서 정상 경로), 대체 경로 잠정 | 같음. VB T4h(③ 켬) 잠긴 표본 초과 0(Dg-2 v4) |
| 2단계 | L2 CP 판정 통과, L3 기록 | 같음(대체 135키의 키별 판정이 꺼짐과 같음). J-P3 통과 |
| 3단계 | 개정 6 `불일치`(H-7) 확정 + 개정 7 참고 `일치(부분)` 상당 | **바꾸지 않는다** |
| 다음 Chrono T4 | - | ③ 켬 실행 설정 + 개정 7 E·B1 + J-P3 |

## 9. 가정

| 가정 | 값 | 근거 |
|---|---|---|
| $\delta_m$ | 0.5 bar | `p3_extend_start_spec.md` 6절 |
| 보수 매개변수 | B 호스 계수 1.40, $\bar C_r$ 감도 끝값 | 같은 명세 3절, hydraulics-expert 검토 |
| 하네스 대조 행 | 사례마다 첫 VB 행 22개 | 7.2절(이번에 정함) |
| Chrono 대조 행 | E_G4_Fs8, S_top_fdown3.5_wika_Fs8 | 7.3절(이번에 정함) |
