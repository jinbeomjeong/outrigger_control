# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev6 (Chrono 경로 1 집계 새 판의 확인 사항 C-1~C-9, 결과 전, 봉인)

- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev6.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev6_seal_candidate_draft.md`와 1·3·5·9행만 다르다.
- 원판 `v5_resume_4368_rules.md`(sha256 `9019b405…`), rev1(`d9094fda…`), rev2(`497e4614…`), rev3(`dad8dfa6…`), rev4(`7ea87a30…`), rev5(봉인본, `.sha256` 기록)는 고치지 않는다. 전체 sha256은 각 판의 `.sha256`에 있다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다.
- **시점: 436.8 본 실행 결과가 없을 때(봉인 2026-11-13 07:49:42 +09:00, 봉인 커밋 31d543e).** 436.8 본 묶음과 0단계 T-3K는 한 줄·한 행도 돌지 않았다. 있는 것은 G-S 실행뿐이다(R6-0).
- 작성: control-expert, 2026-11-13. 계기는 두 가지다.
  - rev5 R5-A1에 따라 cad-expert가 만든 Chrono 경로 1 대조표 `v5_resume_4368/chrono_path1_rev3_alignment.md`(추적 밖). R3-G3·G4·G5(D8)·G6·G8·G10 여섯 항목이 모두 "다름" 또는 "코드 없음"이었다.
  - 그 결과 정해진 Chrono 경로 1 집계 새 판 `chrono_rows_judge_4368.py`(N-1~N-14)와, 그 과정에서 나온 확인 필요 C-1~C-9, 하네스 경로 1 새 판 구현자의 질문 셋(R6-C)
- **봉인본이다.** 사용자 결정이 필요한 항목은 없었고, C-1~C-9와 경로 1 질문 셋의 정의는 R6-B·R6-C와 R6-9 결정 표에 있다.
- **바꾸지 않는 것**: 숫자 문턱, 등급과 우선순위, 멈춤 조건의 뜻, 묶음 범위와 행 목록, 사전 예측 값, 두 경로 요건(원판 9.2), rev3~rev5의 정의. 이 판은 정의가 열려 있던 경계·입력만 정한다.

## R6-0. 결과 전 근거와 공개

- 2026-11-13 확인: 436.8 본 출력이 없다. G-S 실행만 있다.
- 읽은 것:
  - cad-expert 대조표 `chrono_path1_rev3_alignment.md` 전체(표만, 러너·판정 코드는 이 판을 쓰며 열지 않았다)
  - 명세 `s6_control_spec.md`: 3절 공통 정의(309행), 318·320행(검증 항목 2·4), 7154~7159행(R40-1·R40-2·R40-6), 10510·10520행(S8-A2 판정 힘), 377절, 424.8.1, 427.9, 11025·11820·11836행(t_D)
  - v5 기준 개정 6 5·6절, 원판 6절 120행(SA-4), `d1_selection_rules.md` 11절, 원판 2절(정수 주기 비교)
  - 명세 381절(U-S9-G6c)
  - 기존 G6 판정 함수 `04_scripts/03_control/s8/r72_judge.py`의 G6-7 분기(경로 1·2 새 판 코드가 아닌 v4 판정 함수)
  - 정체성 기록 함수 `04_scripts/03_control/d8x/d8x_record.py` `run_identity`의 필드 정의
  - 판정 값은 읽지 않았다.
- 이 작성자는 경로 2 작성자가 아니다(rev2 R2-0).

## R6-1. 기록해 둘 사실 (cad-expert 대조표 5절)

- **시각 원점**:
  - `run_S8C`(L2b)·`run_S6C`(L1-R)의 `result.json` `phases`는 실행 t0 기준 **상대 시각**이다.
  - `controller_events.json`, `fallback_lock_log`, `pads.npz`, `r8_series.npz`, `record.npz`는 Chrono **절대 시각**이다.
  - `run_S9`(SCM)의 `phases`는 절대 시각이다.
  - 그래서 L2b·L1-R 행에서 단계 창을 쓰는 모든 계산(경로 1 새 판과 경로 2 공통)은 `phases` 시각에 `settings.start_t_s`를 더해 절대 시각으로 바꾼 뒤 쓴다. 바꾸지 않고 섞으면 그 행은 도구 결함(S-11)이다.
- R5-B1의 시각 원점: `fallback_lock_log`·`pads.npz`·`r8_series` `t`는 같은 원점(Chrono `ChSystem` 시각)이다. G-S L2b·L1-R 두 행으로 확인했고, 두 행 모두 `fallback_lock_log`는 빈 목록이었다.

## R6-A. Chrono 경로 1 집계 새 판의 공개 항목 (N-1~N-14 → D-26~D-39)

rev5 R5-A3 표(D-01~D-25)에 이어 판정서 공개 표에 다음을 더한다. 새 판 `04_scripts/02_chrono/chrono_rows_judge_4368.py`는 R5-A1 요건 1~5를 따른다. 공개 diff 대상은 `r76_g6_chrono_judge.py`, `verify/s8_control.py` C1 행, `verify/s6_control.py` `_times`다.

| # | 대조표 N | 묶음 | 항목 | 지금(러너·러너 judge) | 새 판(정의 출처) |
|---|---|---|---|---|---|
| D-26 | N-1 | C-2·C-3 | S-01·02·03·04 안전 정지 | 분류 없음 / 실패로 셈 | 427.9 조건으로 `stroke_limited_stop` = `allowed_stop`(R6-B8, rev3 R3-G3) |
| D-27 | N-2 | C-3 | P3-6 | `within`만 | 거짓이면 FLAG(기록), 한계 90 s(rev3 R3-G4) |
| D-28 | N-3 | C-3 | G6 READY ≤ 120 s | 러너 없음 / 허용 없음 | ≤ 120 s + 10⁻⁹(원판 7.6, rev3 R3-G4) |
| D-29 | N-4 | C-1·C-2·C-5 L2b | D8 t_lift | 10 Hz, 마지막 양수 뒤, 세계 z, 단계 무시 | 개정 6 5절 t_lift, 1 ms `pads.npz` `crawler_normal_N`, 단계 절대 시각 변환(R6-1, rev3 R3-G5) |
| D-30 | N-5 | C-4 등 SCM, C-1 L1-R | D8 t_lift | 없음 / 입력 없음 | SCM: 1 ms `scm_crawler_normal_N`. L1-R: R6-B1 |
| D-31 | N-6 | C-1 | R40-2 보류 해제 | 없음 | 보류 = 판정 불가, 7155행 해제 절차, 못 풀면 묻기(rev3 R3-G6) |
| D-32 | N-7 | C-1~C-5 | 이동 압력 | 1e-6 / SCM 없음 | u_applied ≠ 0(10⁻⁹), 10 Hz 제어 주기 행(R6-B5), F_cyl/A_p, 사건 행 J-5·U58(rev3 R3-G10 Q-13) |
| D-33 | N-8 | SCM | 부상 | 없음 | `scm_pad_normal_N` ≤ 0인 1 ms 표본(rev3 Q-14) |
| D-34 | N-9 | C-2~C-5 SCM | 377 강등과 U-S9-G6c | 없음 | 377 조건, 창 끝 = 첫 확정 LOC + 1 s(R6-B3, rev3 R3-G8). 377이 거짓이면 U-S9-G6c `P3-8_preloc_loss` 분기(R6-C3) |
| D-35 | N-10 | SCM | P3-8 구간 | 최종 LOC, 토양 모드 무시 | min(첫 확정 LOC, 첫 토양 모드 시작)(rev3 Q-10) |
| D-36 | N-11 | SCM | 재접촉 지속 | 끝까지 이어지면 1 ms 짧음 | 표본 수 × 1 ms(rev3 Q-11) |
| D-37 | N-12 | SCM | P3-2 순서 | ≤ + 10⁻⁹ | 최종 LOC < 첫 DONE(엄격)(rev3 Q-12) |
| D-38 | N-13 | SCM | P3-2 하중·취소 LOC | ≥ 0.01 W, 취소 LOC 기록 없음 | > 0.01 W, 취소 LOC 시각의 크롤러 법선 기록(rev3 Q-17) |
| D-39 | N-14 | C-1 | C1 행 재계산 | – | D-29 t_lift와 R6-B2 원값으로 C1 행(보류 포함)을 다시 계산 |

- 판정서는 행마다 러너 값과 새 판 값이 다른 행 수를 D 번호와 함께 적는다.
- t_D(R6-B4)를 다시 정하면 t_D에 기대는 P3 항목(P3-2 시간 조항, P3-3 창, rev2 R2-5 창)도 새 판이 다시 계산한다. 러너 `p3b.departure`와 다른 행 수를 적는다.

## R6-B. 확인 필요 C-1~C-9

### R6-B1. L1-R의 D8 t_lift (C-1)

- 사실: L1-R(`run_S6C`) `pads.npz`에는 1 ms `crawler_normal_N`이 없다. `record.npz` `F_crawler`(제어 주기 10 Hz, 세계 좌표)만 있다.
- **정의**: v5 기준 개정 6 5절의 "10 Hz 구간 대체"를 D8 t_lift에도 쓴다. 그 문장은 "1 ms 크롤러 기록이 없는 실행: F_cr,n > 0인 마지막 10 Hz 표본 t_a, ≤ 0인 첫 표본 t_b"이다.
  - L1-R 행의 D8 t_lift = 단계가 `idle`·`check`·`touch`가 아니고 크롤러 법선 ≤ 0인 **첫** 10 Hz `record.npz` 행의 시각 t_b다. `t_lift_basis` = `bracket_10Hz`이고, t_a도 기록한다.
  - 크롤러 법선은 `F_crawler`의 바닥 법선 성분이다. C1-09~12는 평지(바닥 법선 = 세계 z)라 z 성분과 같다. 바닥이 기울어진 행이 생기면 바닥 법선으로 사영한다.
  - C1-09~12는 기록 행이다(`d1_selection_rules.md` 11절 "기록(D8·P 계산, 실패는 보고)"). 그래서 이 대체는 등급에 영향이 없다. 판정서에 "10 Hz 구간 대체"를 적는다.
  - "판정 불가"로 두지 않는다. 개정 6이 1 ms 기록이 없는 실행의 대체 규칙을 이미 정했기 때문이다.
- 결정 필요: **아니오**.

### R6-B2. R40-2 "원값"과 S8-A2 (C-2)

- **정의**: R40-2 조건 ①의 "원값 최소"는 L2b의 **S8-A2 판정 힘**(`pads.npz` `F_cyl_min_interval`, 부상 표본은 `F_cyl_mean_20ms`)의 최소다.
  - "원값"은 R40-1(7154행)에서 "느린 성분(1 s 중심 평균)"과 맞서는 말이고, 1 ms 판정 힘을 뜻한다.
  - L2b Chrono 판정의 1 ms 판정 힘은 S8-A2로 통일됐다(명세 10510행 "힘은 S8-A2 판정 힘(`pads.F_cyl_min_interval`, 부상 표본은 `F_cyl_mean_20ms`)", 10520행 "판정 힘으로 통일한다").
  - 조건 ③의 "느린 성분"은 같은 판정 힘의 1 s 중심 평균이다.
  - 판정서에 S8-A2가 적용된 표본 수(부상 표본 수)를 행마다 적는다.
- 결정 필요: **아니오**(경로 1 러너 judge의 현행 정의와 같다).

### R6-B3. 377의 "LOC + 1 s" (C-3)

- **정의**: 377의 창 "시작 ~ LOC + 1 s"의 LOC는 **첫 확정 LOC**(뒤에 취소된 것 포함)다.
  - 377(사용자 결정 2026-10-27)은 LOC 사후 취소(L1gs, 2026-10-29 채택) 이전에 쓴 문장이다. 그래서 그때의 "LOC"는 실행의 첫 LOC였다.
  - 377이 강등하는 대상은 P3-8(G6-7) "LOC 전" 재접근이다. rev3 Q-10은 P3-8 구간 끝을 첫 확정 LOC로 정했다. 같은 LOC를 써야 대상 사건과 창이 맞는다.
  - 424.8.1의 "최종 LOC" 규칙은 P3-1·P3-2·P3-7에만 적용된다(424.8.1 첫 문장). 377에는 적용하지 않는다.
  - 판정서에 LOC 취소가 있었던 행 수와, 그 행에서 최종 LOC + 1 s로 계산했다면 강등 결과가 달라졌는지를 기록한다.
- 결정 필요: **아니오**.

### R6-B4. t_D의 "0.1 s 이어짐" 표본 셈 (C-4)

- **정의**: rev2 R2-5의 "0.01 W 미만으로 0.1 s 이상 이어지는 첫 구간"은 1 ms 표본 **100개 이상**이 연속인 구간이다. rev3 R3-G10 Q-11의 지속 정의(표본 수 × 1 ms)를 같이 쓴다.
  - 러너(`run_S9` `crawler_departure`)는 마지막 − 첫 ≥ 0.1 s(101표본)로 센다. 새 판과 경로 2는 100표본 규칙으로 t_D를 다시 계산한다.
  - R6-A 끝 문장대로 t_D에 기대는 항목을 다시 계산하고, 러너 t_D와 다른 행 수와 최대 차(≤ 1 ms 기대)를 적는다.
- 결정 필요: **아니오**(두 지속 정의를 하나로 맞춤).

### R6-B5. 이동 압력의 표본 주기 (C-5)

- **정의**: rev3 Q-13의 이동 압력 표본은 **제어 주기 행(10 Hz)**이다.
  - L2b·L1-R·SCM 모두 `record.npz`의 `u_applied`와 같은 행의 `F_cyl`을 쓴다. 이동 = |u_applied| > 10⁻⁹, 압력 = F_cyl/A_p다.
  - 1 ms 작용 명령 기록은 없다. 영차 유지를 가정해 1 ms로 늘리지 않는다.
  - 근거: 검증 항목 4(명세 320행 "최대 이동 중 압력 ≤ 180 bar")를 판정해 온 러너 judge가 제어 주기 행을 쓴다. rev3 Q-13은 이동 판별(작용 명령)만 정했고 표본 주기는 정하지 않았다.
  - 한계로 공개한다: 제어 주기 사이의 압력 첨두는 이 판정에서 보이지 않는다. 사건 창 안(≤ 350 bar)도 같은 행이다.
- 결정 필요: **아니오**.

### R6-B6. G-S 시각 비교의 허용 (C-6)

- **정의**: rev5 R5-B1의 "두 `t` 열의 첫 공통 시각이 정수 주기로 맞음"은 원판 2절의 **정수 주기 비교** n = round(t/T_s)로 판정한다.
  - 10 Hz 행은 round((t − `settings.start_t_s`)/0.1)이 정수 주기 번호가 되는지 본다.
  - 1 ms 격자는 round(t/10⁻³)가 같은지 본다.
  - 원판 7.6의 10⁻⁹ 비교 허용은 판정 문턱 비교용이고, 누적 부동소수 오차(실측 2.5×10⁻⁸ s)가 있는 시각 격자 대조에는 쓰지 않는다. 새 숫자는 만들지 않는다.
  - 실측 정수 차 최대(1.9×10⁻⁸~2.5×10⁻⁸ s)는 기록한다.
- 결정 필요: **아니오**.

### R6-B7. 열린 채 끝난 잠금 구간 (C-7)

- 사실: `fallback_lock_log`에는 **닫힌** 잠금 구간만, 닫힐 때 그 다리가 FALLBACK 상태일 때만 들어간다. 실행 끝까지 열린 구간은 빠진다.
- **정의**:
  - rev5 R5-B1의 "실제 대체 다리"는 `fallback_lock_log`의 `leg` 집합과, 사건 `WARN_ROD_PRESSURE_FALLBACK:<다리>`가 있는 다리의 **합집합**이다.
  - 사건에만 있는 다리의 열린 구간은 J11 창 끝을 명령 기록에서 다시 계산해 n_late를 낸다(개정 6 6절). 로그와의 10⁻¹² s 대조는 "로그 항목 없음(열린 구간)"으로 적고 판정 불가로 두지 않는다.
  - 로그에 있는데 사건이 없는 다리는 기록 불일치로 S-11이다.
- 결정 필요: **아니오**.

### R6-B8. S-01·02의 안전 정지 (C-8)

- **정의**: 적용한다. `d1_selection_rules.md` 11절은 S-01·02 행을 "P3, READY 120 s, `stroke_limited_stop` 허용"으로 적었다. 그래서 새 판 N-1(427.9 조건 1~5로 `stroke_limited_stop` = `allowed_stop`)을 S-01·02·03·04 네 행에 같이 쓴다(D-26).
- 결정 필요: **아니오**.

### R6-B9. SGS 조건 3 "부상 없음"의 정의 (C-9)

- **정의**: 실행 기록에 패드 법선 접촉력 진값이 있으면 rev3 Q-14 정의(패드 법선 ≤ 0인 1 ms 표본 = 부상)를 쓴다. Chrono SCM은 `step_series.npz` `scm_pad_normal_N`, L2b는 `pads.npz` `N`이다. 그래서 Chrono 새 판 N-1은 Q-14로 판정한다.
  - 하네스 모듈의 "참 F_cyl + 로드 무게가 0에 닿지 않음"은 패드 법선 진값이 없는 하네스의 근사다. rev5 R5-D3대로 하네스에서만 쓰고, 그 식과 dynamics 확인을 공개한다.
  - 두 엔진의 정의가 다르다는 것을 판정서 한계 절에 적는다.
- 결정 필요: **아니오**(rev5 R5-D3의 "플랜트 값 우선" 원칙).

## R6-C. 경로 1 새 판 구현자의 질문

### R6-C1. SA-4 "정지 뒤 네 다리 ≥ F_min"과 "포화 차단 0" (rev3 R3-E5 Q-S6)

- 사실: 하네스 새 판은 지금 두 항목을 다음 값으로 읽는다.
  - "정지 뒤 ≥ F_min": 이륙 뒤 최소. 충분조건이라서 그 값이 F_min 미만이면 판정 불가가 된다.
  - "포화 차단 0": `values.pressure.saturation_leg_chunks` = 0.
- **정의**:
  1. "정지 뒤 네 다리 ≥ F_min"(v5 기준 6절 120행)의 판정량은 **정지 시각(`FAULT_LIFT_STROKE_LIMIT:soil` 주기)부터 실행 끝까지 네 다리 1 ms 참 F_cyl 최소**다. 경로 1 구현자가 v5 S8 계열 하네스 줄에 기록 전용 필드 `values.sa4.F_min_after_stop_N`(다리별, FL·FR·RL·RR)을 더한다(R6-D 표 F-9). 필드가 있으면 그 값으로 판정한다. 필드가 없는 줄은 원래대로 이륙 뒤 최소가 F_min 이상이면 참(충분조건)이고, 아니면 `판정 불가`다.
  2. "포화 차단 0"은 `values.pressure.saturation_leg_chunks` = 0으로 판정한다. 이 필드가 검증 항목 4의 "포화 차단"(명세 320행 ② "레벨링 실행에서 포화 차단 0회")과 같은 정의인지 경로 1 구현자가 필드 설명으로 적는다. G-S에서 그 설명을 확인한다. 정의가 다르면 S-11이다.
- 결정 필요: **아니오**(기록 전용 필드와 정의 확인).

### R6-C2. K-0 정체성 필드의 실제 대응 (rev4 R4-C4)

- 사실: 436.8 하네스 출력의 실제 `.identity.json`(`d8x_record.run_identity` 기록)이 가진 필드는 `python`, `python_version`, `threads`(`MKL_NUM_THREADS`, `OMP_NUM_THREADS`, `NUMBA_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_THREADING_LAYER`), `affinity_mask`, `git`(`head`, `status_porcelain`, `is_clean`), `rules_seals`다. R4-C4가 적은 `code_diff_sha256`·`c2_sha256`·`tools_sha256`·`env.OUTRIGGER_LOC_SHADOW`는 없다. R4-C4가 다른 실행기(B1)의 정체성 꼴을 옮겨 적었다.
- **정의(안 b, 실제 필드로 대응을 바꾼다)**: rev4 R4-C4 표를 다음으로 바꾼다.

| K-0 항목 | 원본 | 조건 |
|---|---|---|
| 커밋 | `.identity.json` `start`·`end`의 `git.head` | 둘이 같고 `git_at_start`와 같다 |
| 작업 트리 | `git.is_clean`, `git.status_porcelain` | 깨끗하거나 실행 전 감사가 허용한 파일뿐 |
| 스레드 | `threads` 다섯 변수 | 넷 = 1, `MKL_THREADING_LAYER` = TBB(원판 6절) |
| 봉인 | `rules_seals` | 모든 항목 `ok` |
| 제어기·도구 sha | T-3K 출력의 줄·헤더 정체성 기록(`las_targeted_rules_rev3.md` K-0이 정한 원본: `c2_sha256`, 도구 `sha256`, `git_head`, 스레드, 작업자, affinity) | 헤더와 모든 줄이 같고, 세 출력(R-0·R-0K·T-3K)이 서로 같다 |
| 금지 env `OUTRIGGER_LOC_SHADOW` | rev1 RV1-9의 방법(단계 파일 env와 러너 시작 env 기록, import 경로 점검) | 원판 4.2 |

  - 정체성 기록에 새 필드를 더하지 않는다(안 a를 쓰지 않는다). 원 규칙 K-0의 원본은 T-3K 출력 자신의 줄·헤더 정체성이기 때문이다.
  - 경로 2는 위 표대로 대조한다. 항목의 원본이 없으면 그 항목은 `판정 불가`다.
- 결정 필요: **아니오**(R4-C4의 필드 출처 정정).

### R6-C3. 377 판정 분기와 `P3-8_preloc_loss` (rev5 R5-D1)

- 사실: 기존 G6 판정 함수(`r72_judge.py`)의 G6-7 처리에는 분기가 셋이다.
  1. `preloc_flag_ok` 참 → `P3-8_demoted`(377)
  2. `preloc_flag_ok` 거짓 ∧ G6-3 참 ∧ FAULT 없음 → `P3-8_preloc_loss`
  3. `preloc_flag_ok` 없음 → `P3-8_unchecked`
- 2번은 사용자 결정 **U-S9-G6c (가)**(명세 381절, 2026-10-28)다: "LOC 전(크롤러 하중 ≥ 0.01 W) 대각 하중 소실은 FLAG(`P3-8_preloc_loss`)다. … 377절 강등은 그대로다."
- **정의**: rev5 R5-D1이 377만 적은 것은 빠뜨림이다. 하네스 D-1 새 판과 Chrono 새 판(D-34)은 **2번 분기도 넣는다**. `d1_selection_rules.md` 11절 H-R-A·H-S-A·S-03·04의 G6 판정은 기존 기준 그대로(D-5)이고, 기존 G6 판정 함수가 이 분기를 가진다.
  - 분기 1·2에 해당하면 G6-7은 FLAG이고 실패가 아니다. 그 항목을 `d1.demoted_items`에 넣는다. `rule`은 377 또는 `U-S9-G6c`, `flag`는 그 이름이다.
  - 분기 3(`preloc_flag_ok` 없음)은 원판 9.3 결측으로 `판정 불가`다. 기존 함수의 `P3-8_unchecked` 꼬리표(실패 유지)는 쓰지 않는다.
  - 경로 2는 R5-D1 4대로 `d1.g6_preloc`과 G6-3·FAULT 기록으로 두 분기를 다시 계산해 대조한다. Chrono는 1 ms 계열로 다시 계산한다(D-34).
- 결정 필요: **아니오**(봉인된 사용자 결정 U-S9-G6c의 적용).

## R6-D. 기록 전용 필드 추가 (rev4 R4-D·rev5 R5-D4 표에 더함)

| # | 출처 | 실행(러너) | 필드 | 내용 | G-S 확인 |
|---|---|---|---|---|---|
| F-9 | R6-C1 | run_v5 S8 계열 하네스 줄 | `values.sa4.F_min_after_stop_N` | 정지 시각 ~ 실행 끝 다리별 1 ms 참 F_cyl 최소 [N] | 예 |
| (설명) | R6-C1 | 같음 | `values.pressure.saturation_leg_chunks` 필드 설명 | 검증 항목 4 "포화 차단"과 같은 정의인지 | 예 |

## R6-9. 결정 표

| 항목 | 권고·정의 | 결정 필요 |
|---|---|---|
| R6-1 시각 원점 | L2b·L1-R `phases`는 상대 시각, `start_t_s`를 더해 절대 시각으로 | 아니오 |
| R6-A 공개 항목 | D-26~D-39(N-1~N-14) | 아니오 |
| R6-B1 L1-R t_lift | 개정 6 5절 10 Hz 구간 대체(t_b), 기록 행 | 아니오 |
| R6-B2 R40-2 원값 | S8-A2 판정 힘 | 아니오 |
| R6-B3 377 LOC | 첫 확정 LOC | 아니오 |
| R6-B4 t_D 표본 셈 | 100표본(표본 수 × 1 ms) | 아니오 |
| R6-B5 이동 압력 표본 | 10 Hz 제어 주기 행, 1 ms 가정 안 함(한계 공개) | 아니오 |
| R6-B6 G-S 시각 비교 | 원판 2절 정수 주기 round 비교, 10⁻⁹ 안 씀 | 아니오 |
| R6-B7 열린 잠금 구간 | 로그 ∪ 대체 사건 다리 | 아니오 |
| R6-B8 S-01·02 안전 정지 | 적용 | 아니오 |
| R6-B9 SGS 부상 | Chrono는 Q-14, 하네스는 근사(R5-D3) | 아니오 |
| R6-C1 SA-4 두 항목 | F-9 정지 뒤 최소, 없으면 충분조건 또는 판정 불가. 포화는 `saturation_leg_chunks` + 정의 확인 | 아니오 |
| R6-C2 K-0 필드 | 실제 `.identity.json` 필드와 T-3K 줄·헤더 정체성으로 대응(안 b) | 아니오 |
| R6-C3 377 분기 | U-S9-G6c `P3-8_preloc_loss` 분기도 넣음, `preloc_flag_ok` 없음 = 판정 불가 | 아니오 |
| R6-D F-9 | `values.sa4.F_min_after_stop_N` | 아니오 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 파일 이름: `v5_resume_4368_rules_rev6_seal_candidate_draft.md` → `v5_resume_4368_rules_rev6.md`(같은 폴더). 초안 파일은 지우지 않고 그대로 둔다.
2. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev6 (Chrono 경로 1 집계 새 판의 확인 사항 C-1~C-9, 결과 전, 봉인)`
3. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev6.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev6_seal_candidate_draft.md`와 1·3·5·9행만 다르다.`
4. 5행("시점")에서 `SEAL_TIME`(예: 2026-11-13 10:00:00 +09:00)과 `SEAL_COMMIT`(봉인 파일을 넣는 커밋의 앞 커밋, 7자리)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
5. 9행("봉인 준비판이다")을 다음으로 바꾼다:
   `- **봉인본이다.** 사용자 결정이 필요한 항목은 없었고, C-1~C-9와 경로 1 질문 셋의 정의는 R6-B·R6-C와 R6-9 결정 표에 있다.`
6. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev6.sha256`에 `<sha256>  v5_resume_4368_rules_rev6.md  sealed <SEAL_TIME 값> (436.8 rev6: Chrono path 1 aggregate new version items D-26..D-39; L2b/L1-R phases relative time; L1-R t_lift by revision 6 10 Hz bracket; R40-2 raw = S8-A2 judged force; 377 window to first LOC + 1 s; t_D 100 samples; moving pressure on 10 Hz control rows; G-S time check by integer period rounding; open lock stretches by fallback events; S-01/02 safe stop; SGS lift by pad normal on Chrono; SA-4 post-stop minimum F-9 and saturation field; K-0 by actual identity fields; U-S9-G6c preloc_loss branch; thresholds and grades unchanged)` 한 줄로 쓴다.
7. `.gitattributes`에 다음을 더한다:
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev6.md -text`
   - `…/v5_resume_4368_rules_rev6.sha256 -text`
   - `…/v5_resume_4368_rules_rev6_seal_candidate_draft.md -text`
8. `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`(봉인본에 `SEAL_TIME`·`SEAL_COMMIT`이 남지 않음)로 확인한 뒤 커밋한다. 봉인 뒤 이 문서를 고치지 않는다. 고칠 것이 생기면 `v5_resume_4368_rules_rev7.md`로 새로 봉인한다.
