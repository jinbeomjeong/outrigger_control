# U-3·U-6 재실행 규칙 덧붙임 판 1 (정정: g8 로드 판독, P3b 판정 함수)

작성: control-expert, 2026-11-08.

> **상태: 봉인(2026-11-08).** SHA-256과 봉인 시각은 같은 폴더 `u3_u6_rerun_rules_rev1.sha256`에 있다. 이 파일은 더 고치지 않는다.
> - **U-3·U-6 본 실행 전의 정정이다.** 본 것은 구현 코드(master 343de8c)와 python-expert의 g8 VB 단발 확인 1건(`has_rod_reading` = true, J-P3 `pass`)뿐이다. 판정 문턱은 바꾸지 않는다.
> - 두 항목 모두 봉인본을 쓸 때 control-expert가 사실을 잘못 적은 것이다. (1) g8 하네스가 헤드 압력만 읽는다고 적었다. (2) P3b 판정 함수를 `p3_rows`로 적었다. v4가 실제로 쓴 것은 `p3_lite_gates`다.

**고치는 판**: `u3_u6_rerun_rules.md`(SHA-256 `8de318825764114ad14afcec362c87c1e01a2ad47195b8491b1c96056e1960b3`). 여기 적지 않은 항목은 그대로다.

## 1. 바뀌는 항목

| # | 위치 | 앞 문구 | 새 문구 |
|---|---|---|---|
| 1 | 1절 끝 문단 | 이 묶음들은 헤드 압력만 읽는 하네스다 | **g8(비평면 516)을 뺀** 묶음은 헤드 압력만 읽는 하네스다. g8은 `r70_p28_screen`(r69 G8 로드측 하네스)이라 헤드·로드 두 압력을 읽는다(`s9_slope_fix_candidates.ROD_READING_SUITES`) |
| 2 | 4절 "VB 공통" 행 | J-P3 = `no_rod_reading`(헤드 전용 선언 필요) | 헤드 전용 묶음: 그대로. **g8: J-P3 판정 대상**(v5 기준 개정 8·9 그대로: `extend_bound_check` 있음 + ext_moving `sum(breach_reads)` = 0이면 통과, ≥ 1이면 H-7, 기록 없음이면 설정 결함). T4h는 이 묶음의 판정 항목이 아니다 |
| 3 | 4절 P3b 행 | `s9_soil_slope.p3_rows` P3-1~P3-8 | P3b(171)는 **`s9_slope_fix_candidates.p3_lite_gates`**(crawler, Fmin, att, rut ≥ 25 mm, fault_ready). v4 FINAL-B2 P3b와 같은 판정 함수이고, READY 한계는 없고 READY에 도달했는지만 본다. 연구 ①·H6·H9·연구 B·D 행은 그대로 `p3_rows` |
| 4 | 7절 G-4 | 모든 VB 실행이 `no_rod_reading` | 헤드 전용 묶음의 VB 실행은 `no_rod_reading`(선언 있음, 로드 판독 없음). **g8 VB 실행은 `has_rod_reading` = true이고 J-P3 `pass`.** 그 밖(설정 결함·H-7, 헤드 전용 묶음에 로드 판독 있음, g8에 로드 판독 없음)이면 멈춘다 |
| 5 | 7절(추가) G-6 | — | g8 VB 실행의 `WARN_ROD_PRESSURE_FALLBACK` 사건 = 0. 이상 센서라 대체가 생기지 않아야 한다. 생기면 그 키에서 ③가 명령에 닿으므로 멈추고 묻는다(T4h 재생 여부를 그때 정한다) |
| 6 | 5.1 "이전 판" 행(추가 주) | — | v4 g6 저장 기록에는 r72 원 게이트가 없어 G6-7 강등을 다시 적용할 수 없다. 그래서 이전 판 g6 판정은 v4 저장 판정 그대로 쓰고 "G6-7 강등 미적용"으로 표시한다. 기록 항목이라 판정에는 영향이 없다 |

## 2. 근거

| # | 근거 |
|---|---|
| 1 | `04_scripts/03_control/s9/s9_slope_fix_candidates.py` 142행(g8 = `s8/r70_p28_screen.py` set all), 214~216행 `ROD_READING_SUITES = ("g8",)`, 2863행 `head_only_declared = suite not in ROD_READING_SUITES` |
| 2 | 같은 파일 2729~2751행: `_p3b_record`는 `p3_lite_gates`로 판정한다. v4 FINAL-B2 p3b 기록이 이 함수의 결과다 |
| 3 | 로드 판독이 있는 실행에서 ③는 대체 다리에서만 명령에 닿는다(v5 기준 개정 10 2절). G-6이 대체 0을 확인하면 g8 C2 VB의 V0 대비 차는 플랜트 몫이다 |

## 3. 그 밖 (판정 무관, 기록)

- D-1 재사용은 343de8c 뒤의 D-1 실행에서만 가능하다(`d1.u3` 필드, 봉인 6절 Q-3과 같은 취지).
- VB 비용 배율: 봉인 8절 가정 1.5와 다르게 단발 측정에서 2~4배가 나왔다. 배치 추정에만 쓰고 판정과 무관하다. compute-scheduler-expert의 probe로 정한다.
