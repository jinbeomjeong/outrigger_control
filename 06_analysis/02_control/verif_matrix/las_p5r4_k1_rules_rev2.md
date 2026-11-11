# LAS-b P5r4 + K1 재판정 규칙 덧붙임 판 rev2 (두 경로 해석 맞춤, 결과 전, 사용자 승인 2026-11-11)

- **상태: 봉인.** 결과 전, 사용자 승인 2026-11-11(초안 `las_p5r4_k1_rules_rev2_draft.md` 커밋 `3114c61`, sha256 `2ebd64461a0f633872496bd05983527e77612ae8316e0c4e417eee3903b553d0`를 그대로 승인). 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `las_p5r4_k1_rules_rev2.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 본문은 초안과 같고, 이 머리 두 줄과 끝의 "사용자 결정" 절, "봉인 뒤 고칠 것" 절 제목만 바꿨다.
- 원판 `las_p5r4_k1_rules.md`(`5ee2bac0…`)와 rev1(`f39846d6…`)은 고치지 않는다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다.
- 작성: control-expert(경로 2 작성자), 2026-11-11. 기준 브랜치 `worktree-agent-a243ef335c218e144`(rev1 `9bcbcaa`, 경로 2 `efa1d19`).
- **시점: 결과 전.** 대상 행은 0행 실행됐다.
- 근거 자료: 경로 1(python-expert)이 **문장으로** 보낸 해석 7항(메인 세션 전달)과 경로 2의 해석. 경로 1 코드·브랜치·출력은 열지 않았다(원판 10.2 독립성).
- **바꾸지 않는 것**: 대상 행·묶음·키 목록, 판정 기준과 문턱(1 mm, 10,414.589 N, 11,414.589 N, +1.0 s/+5.0 s, 0.8 등), 비트 예측, 등급 우선순위(16.6), 멈춤 조건. 이 판은 **원문이 정하지 않은 경우의 읽는 법**만 정한다.

## RV2-0. 항목 대조표

"등급 영향"은 같은 실행 결과에서 두 해석이 묶음 등급(`통과`/`미달`/`판정 불가`/`stop`)을 다르게 낼 수 있는지를 적는다.

| # | 항목 | 경로 1 해석 | 경로 2 해석 | 같음/다름 | 이 판의 문장 | 등급 영향 |
|---|---|---|---|---|---|---|
| 1 | C-2 (a) verdict | ref `pass`·`allowed_stop` → cand 그 밖 = 위반 | 같음 | 같음 | RV2-1 (확인) | 없음 |
| 2 | 값 None (C-S·C-F, 하네스) | None = 실패 | C-F: ref None → 범위 밖, cand None → 위반. C-S: 수가 아니면 판정 불가 | **다름**(C-S, C-F ref None) | RV2-2 | **있음**(C-S None: 미달 ↔ 판정 불가) |
| 3 | 키 부재 | 판정 불가 | 판정 불가(그 기준만) | 같음(범위만 확인) | RV2-2, RV2-4 | 없음 |
| 4 | Chrono 이륙 전 힘 키 부재 | None으로 읽음 → None 규칙 | `departed` 거짓이면 값 없음(판정), 그 밖의 부재는 CC-F·G-2′C 판정 불가 | **다름**(departed 참인데 키 없음) | RV2-3 | **있음**(미달 ↔ 판정 불가) |
| 5 | 판정 불가의 범위 | (문장 없음) | 하네스: 기준별. Chrono: $I$ 키 부재는 짝 전체, 그 밖은 기준별 | 확인 필요 | RV2-4 | 없음(묶음 등급은 같고 기준별 목록만 다름) |
| 6 | G-S 단계 토큰 | verdict 사례는 계열 `case` 하나, ε은 `e0`·`e+` 두 갈래 | (경로 2는 G-S 목록을 만들지 않음) | 경로 1 해석을 채택 | RV2-5 | 없음(G-S 관문 범위만) |
| 7 | Z-X 대상 키 | Z-T·Z-S·Z-C에서 해시 바뀜 + $\Delta t$ > +1 s인 짝, 10개 넘으면 S-8 ask | 같은 세 묶음, BT-X는 그 키의 ref가 있는 묶음과 대조 | 같음(원판 BT-X 문구 확장) | RV2-6 | 조건부(10개를 넘어 Z-X를 줄이면 예외 짝이 모집단에 남아 R-1/R-2가 바뀔 수 있음. 10개 이하면 없음) |
| 8 | Z-A 단위 키 | `rev.key#rev.label` | (rev.key, rev.label) 쌍 | 같음 | RV2-7 | 없음 |
| 9 | `errors N`과 남은 오류 | `errors N`은 첫 시도 포함, 남은 오류는 `errors_left` | 오류 줄은 모두 셈, 정상 줄이 없는 키 = 미완 | 같음(이름만) | RV2-8 | 없음 |
| 10 | Chrono $t_L$·$t_P$ 출처 | rev1 출처, `loc_corrections`는 기록만 | 같음(앞서 낸 "`locs[0]` 우선" 제안은 **철회**) | 같음 | RV2-9 | 없음 |
| 11 | READY 시각 출처 | (문장 없음, 경로 1 출처는 공개 안 함) | `values.times.t_first_ready_s`, `d1.t_ready_s`는 대조 | 의도된 출처 차이(10.2) | RV2-10 | 조건부(두 출처가 다른 줄이 있을 때만) |
| 12 | C-4 조건 3 "뒤", ℓ 안의 재시작, 끝 시각 없음 | (문장 없음) | 정수 주기로 끝 주기보다 큼, $c_1 \le t \le c_m$, 끝 시각 없으면 예외 아님 | 확인 필요 | RV2-11 | **있음**(예외 여부로 R-1/R-2 미달 ↔ 통과) |
| 13 | `R4_GAINED` | (문장 없음) | cand에 적용된 R4 decision이 있고 ref에는 없음 | 확인 필요 | RV2-12 | 없음(FLAG) |
| 14 | BT-C 자르기 | (문장 없음) | $t_s \le 128.0$ s 포함, 배열 `t_s`·`issued_u_m_s` 내용 | 확인 필요 | RV2-13 | **있음**(경계 행 처리로 일치 ↔ stop) |
| 15 | 관측 요건 | (문장 없음) | `start_s` 있음 그리고 `ramp.periods_applied` ≥ 1 | 원판 문구 그대로 | 없음(원판 6.3) | 없음 |
| 16 | 하네스 K1 토큰 흔적(K-4) | (문장 없음) | `job`에 이름에 `k1`·`las_off`가 든 키가 있으면 stop | 확인 필요 | RV2-14 | **있음**(통과 ↔ stop) |

## RV2-1. C-2 (a) verdict (확인)

- ref `d1.verdict` ∈ {`pass`, `allowed_stop`}이고 cand `d1.verdict`가 그 집합 밖(`fail`, None, 그 밖의 값)이면 위반이다.
- 근거: `las_k1_rules.md` 4.3 C-2형 (a)("그 밖으로 바뀌지 않는다"), `las_k1_rules_rev1.md` R1-2(cand None 위반), `las_rev_targeted_rules.md` 5.2 (a).

## RV2-2. 값이 None인 경우 (하네스 C-F·C-S, Chrono CC-F·CC-S·G-2′C)

원문 판단:
- `las_rev_targeted_rules.md` 5.0은 **필드가 없으면 판정 불가**, **값이 None이면 기준별로 정한다**고 적는다. 정한 예는 모두 "cand가 기준을 보이지 못하면 위반"의 꼴이다. `d1.items` cand None → 위반, `d1.verdict` cand None → 위반, 위상 격자 F None → 미달. 반대로 기준선(L) 쪽 None은 비교에서 빼고 목록으로 적는다(READY: 둘 다 None → 빼고 적음, L None·cand 값 → 개선).
- 그래서 "None = 실패"(경로 1)는 **cand 쪽 None**에 맞다. 기준선 쪽 None을 실패로 세는 근거는 원문에 없다. "None → 판정 불가"(경로 2의 C-S)도 원문 근거가 약하다. 5.0은 판정 불가를 필드 **부재**에만 쓴다.

문장:
1. **C-F·CC-F**: ref 값이 None이면 그 짝은 범위 밖이다(범위 조건 "ref ≥ 10,414.589 N"을 만족하지 않는다). 건수를 `ref_none`으로 적는다. ref가 범위 안이고 cand 값이 None이면 위반이다.
2. **C-S·CC-S**: cand 값이 None이면 위반이다. ref 값이 None이고 cand 값이 있으면 위반이 아니다. "증가 ≤ 0.001 m"를 계산할 기준이 없으므로 범위 밖으로 보고 `ref_none`으로 적는다. 둘 다 None이면 범위 밖이고 같이 적는다.
3. **G-2′C**: cand `F_min_after_N` 또는 `F_min_transient_N` 값이 None이면 위반이다.
4. 필드(키) 자체가 없으면 그 기준에서 그 짝은 판정 불가다(5.0, 원판 8.1 상태 2). 단 RV2-3의 경우는 예외다.
5. Chrono의 다리별 목록(`F_min_after_N`, `F_min_transient_N`, `s_motor_max_m`)은 원소 가운데 하나라도 None이면 값 None으로 본다. 다리별 최소·최대는 모든 원소가 수일 때만 계산한다.

## RV2-3. Chrono 이륙 전 행의 힘 키 (`p3b.P3-3_leg_force`)

원문 판단:
- 원판 10.1: "Chrono 제어 FAULT·안전 정지로 끝남 → **결측이 아니다**. CC-2로 판정한다."
- run_S9는 크롤러 departure 뒤에만 `F_min_after_N`·`F_min_transient_N`을 쓰고, departure가 없으면 키를 쓰지 않는다. 이 사실은 실행 도구 field-check(`CONDITIONAL_KEY_PATHS`, cad-expert `ff07ac9`)에 있다.
- 따라서 departure가 없어 키가 없는 행은 10.1의 "판정하는 행"이다. 값은 None으로 읽고 RV2-2를 쓴다. 이 점은 경로 1과 같다.
- 그러나 departure가 **있었는데** 키가 없거나 departure 기록 자체가 없으면, 이는 기록 결함이다. 5.0의 필드 부재(판정 불가)에 해당한다. 이 경우를 None(실패)으로 세면 기록 결함이 미달로 둔갑한다.

문장:
1. `p3b.departure.departed`가 거짓이고 두 키가 모두 없으면, 두 값은 None이다. RV2-2로 판정한다(ref면 CC-F 범위 밖, cand면 CC-F(ref 범위 안일 때)·G-2′C 위반). 짝 기록에 `no_departure`를 적는다.
2. 두 키 중 하나라도 없는데 `departed`가 참이거나 `departed` 키가 없으면, 그 짝은 CC-F·G-2′C에서 판정 불가다. 다른 기준(CC-2, CC-S, CK-1C, CC-R)은 그대로 판정한다.

## RV2-4. 판정 불가의 범위 (원판 16.6 1의 "원소")

- 하네스: 짝의 판정 불가는 **그 필드를 읽는 기준에만** 걸린다.
  - C-2: `commands_sha256`, `final_phase`, `event_names`, `values.times.t_first_ready_s`, D-1 짝은 `d1`·`d1.items`·`d1.verdict`·`d1.fail_items`, R1-3 표류.
  - P3: `d1.items`, R1-3 표류. C-F: `d1.F_judged_min_N`. C-S: `d1.stroke_max_m`. CK-1: `k1.decisions`. R-1/R-2: `commands_sha256`, `values.times.t_first_ready_s`. PAIR_DIVERGE 전제: `las.start_t_s`, `commands_sha256`.
- Chrono: $I$ 키가 한 행이라도 없으면 원판 6.3 문구대로 **그 짝 전체**가 판정 불가다(CC-R 모집단에서도 뺀다). `phases`·`P3-6_ready` 부재도 짝 전체다. 그 밖(힘 RV2-3, `s_motor_max_m` 부재)은 그 기준만이다.
- 묶음 등급은 16.6대로 같다. 기준별 목록이 두 경로에서 같아야 한다(K-10).

## RV2-5. G-S 단계 토큰 (원판 16.2 (가))

- 단계 = (계열 토큰, 격자 종류) × setting × ε 갈래.
  - 계열 토큰은 `d1.key`의 둘째 토큰이다(`H-S-0` 등). `job.case`가 있는 verdict 사례는 모두 계열 `case` 하나로 묶는다.
  - ε 갈래는 `e0`(ε = 0)와 `e+`(ε ≠ 0) 둘이다.
- 근거: 16.2 (가)는 verdict 사례의 계열을 정하지 않았다. 경로 1의 해석을 채택한다.

## RV2-6. Z-X 대상 키와 BT-X (원판 4.2, 4.4 BT-X, 6.2 R-1/R-2, 8.2 S-8)

- Z-X 대상 = Z-T·Z-S·Z-C 세 묶음의 짝 가운데, 해시가 바뀌고 READY $\Delta t$ > +1.0 s인 짝의 ref 키다. Z-C는 R-1/R-2를 판정하므로 넣는다. 원판 BT-X 문구의 "Z-T/Z-S"를 이렇게 넓힌다.
- BT-X: Z-X ref 해시 = 그 키가 속한 묶음의 새 ref 해시.
- 대상이 10개를 넘으면 Z-X를 돌리기 전에 묻는다(4.2의 "≤ 10", S-8과 같은 처리). 묻지 않고 일부만 돌리지 않는다.
- Z-X 줄이 없는 짝은 예외가 아니고 R-1/R-2 모집단에 남는다(`las_rev_targeted_rules.md` 6 "근거가 없으면 예외도 없다").

## RV2-7. Z-A 단위 키

- Z-A 줄의 단위 키는 (`rev.key`, `rev.label`)이고, 문자열로 적을 때는 `rev.key#rev.label`이다. 라벨만 쓰면 VB·V0이 겹친다.
- 저장 P5 짝(K-A1~K-A4, M)은 라벨의 앞머리 `P5r4-`를 `P5-`로 바꾼 같은 `rev.key`의 줄이다.

## RV2-8. 오류 줄 수

- 실행 도구의 `errors N`은 그 묶음의 모든 오류 줄(첫 시도 포함)이다.
- 원판 16.3 "재실행 뒤 남은 오류 0"은 다음을 뜻한다. **정상 줄이 하나도 없는 (팔, 키)의 수**(`errors_left`)가 0이다.
- 두 판정 경로는 `errors_total`(오류 줄 수)과 `errors_left`를 모두 출력한다.

## RV2-9. Chrono $t_L$·$t_P$ 출처 (rev1 RV1-1 확인)

- rev1 RV1-1의 출처 그대로다. 사건 `events`, `controller_meta.soil`, 첫 LOC 주기의 `order_gate.decisions`를 쓴다.
- run_S9 `loc_corrections.locs[]`는 대조 기록으로만 쓴다. 등급·FLAG 계산에 쓰지 않는다.

## RV2-10. READY 시각 출처 (원판 10.2)

- 경로 2는 `values.times.t_first_ready_s`, 경로 1은 자신의 출처를 쓴다(10.2의 의도된 출처 차이).
- 두 출처의 값이 다른 줄이 있으면 그 줄을 쓰는 짝의 C-2 (b)·R-1/R-2 결과는 K-10에서 불일치가 된다. 판정서는 그 짝을 공개하고 확정하지 않는다(원판 10.2 K-10, 문턱은 그대로).

## RV2-11. C-4 예외 조건 (원판의 원판 6, A안 6)

- ℓ 안의 재시작: `done_clock.resets` 가운데 시각이 $c_1 \le t \le c_m$인 것($c_1$, $c_m$ = `clock_starts_s`의 첫·끝).
- "LAS-b 끝 그리고 램프 끝 **뒤**": 재시작 시각의 정수 주기가 기준 끝 주기보다 **크다**. 기준 끝은 `las.ramp.end_t_s`이고, 없으면 `las.end_t_s`다. 같은 주기는 "뒤"가 아니다.
- 기준 끝 시각이 둘 다 없으면 예외가 아니다(근거가 없으면 예외도 없다).

## RV2-12. `R4_GAINED` (원판 6.2, 6.3)

- cand에 `r4_due_without_gate` 참·`applied` 참인 decision이 있고, ref에는 그런 decision이 하나도 없다. FLAG다.

## RV2-13. BT-C 비교 (원판 4.4)

- 비교 대상은 `controller_commands.npz`의 배열 `t_s`·`issued_u_m_s`이고, 두 배열의 모양·자료형·값이 모두 같아야 "같음"이다.
- C3와 REM R8은 $t_s \le 128.0$ s(경계 포함)인 행만 쓴다. C1과 REM R7은 전체를 쓴다.

## RV2-14. 하네스 K1·LAS 꺼짐 토큰 흔적 (원판 9 K-3·K-4)

- 하네스 줄의 `job` dict에 이름이 `k1`·`k1_candidate`·`k1_order_gate`·`las_off`인 키가 있으면 "K1 토큰 흔적"으로 보고 K-4 위반(stop)이다.
- `k1.k1_candidate` 같은 기록 필드의 값은 이 판정에 쓰지 않는다(기록만).

## 사용자 결정 (2026-11-11, 결과 전)

등급 영향이 있는 항목(RV2-2, RV2-3, RV2-6(10개 초과 때만), RV2-10(출처 차이가 있을 때만), RV2-11, RV2-13, RV2-14)을 포함해 모든 문장을 초안 제안대로 승인했다(사용자, 2026-11-11, 메인 세션 전달). 대상 행은 승인·봉인 때 0행이었다.

## 봉인 뒤 두 경로가 고칠 것 (판정 도구는 이 판 문장대로 맞춘 뒤 결과 전 고정한다, 원판 10.2)

- 경로 2
  - RV2-2: C-S·CC-S cand None을 위반으로 바꾼다(지금은 판정 불가). ref None은 범위 밖으로 바꾼다.
  - RV2-8: `errors_left` 출력을 더한다.
  - RV2-14: 키 이름 집합을 맞춘다. 지금은 이름에 `k1`·`las_off`가 든 모든 키를 본다.
- 경로 1(문장으로 전달)
  - RV2-2: ref 쪽 None을 실패로 세지 않는다.
  - RV2-3: 키 부재 + departed 참·부재는 None이 아니라 판정 불가로 본다.
  - RV2-6: BT-X 대조 묶음을 맞춘다.
  - RV2-11·RV2-13·RV2-14: 위 문장과 같은지 확인한다.
