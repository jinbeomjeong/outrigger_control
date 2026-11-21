# 경로 2 넘김 3: 덧붙임 4a-7 정오 2 발췌(1·2·3·5절, 2026-11-21)

- 원문 `jp3_remedy_spec_addendum_4a7_erratum2.md`의 1·2·3·5절을 바이트 그대로 옮겼다. 4절(경로 1 실행 전제·사전 대조)은 넣지 않았다. 앞 넘김 2보다 이 정오가 우선한다.

## 1. 비교 열 일치 검사(정오 1 2절의 "기록" 문장을 대신함)

- 봉인 6.2절의 비교 대상은 $\hat p+\delta_m$(J-P3a)과 ④(J-P3b)다. 6.3절 기록 열 `jp3_used_bound_Pa`(모니터가 그 읽기에 쓴 값)는 기록 정의상 다음과 같다.
  - `ext`·`carry_ext` 읽기: `jp3_ext_bound_Pa`와 같은 값($\hat p+\delta_m$, 13 bar 바닥 없음)
  - `lock`·`hold` 읽기: `jp3_model_bound_Pa`와 같은 값(④, ⑤가 섞이기 전)
  - `carry_ret` 읽기: $\max(\hat p+\delta_m,\ 수축\ 이동\ 모델)$
- 그래서 두 경로가 `jp3_used_bound_Pa`로 세든, `jp3_ext_bound_Pa`·`jp3_model_bound_Pa`로 세든 같은 수가 나와야 한다.
- **정오 1 2절의 "1 Pa 넘게 다른 읽기는 기록(결함 아님)" 문장을 다음으로 바꾼다.**
  - J-P3a 대상 읽기에서 |`jp3_used_bound_Pa` − `jp3_ext_bound_Pa`| > 1 Pa이면 `record_defect`(판정 불가)다.
  - J-P3b 대상 읽기에서 |`jp3_used_bound_Pa` − `jp3_model_bound_Pa`| > 1 Pa이면 `record_defect`(판정 불가)다.
  - 기록 정의상 같아야 하는 값이 다르므로 기록 결함이다.
- 정오 1 2절의 비교 열 표(J-P3a = `jp3_ext_bound_Pa`, J-P3b = `jp3_model_bound_Pa`, J-P3c = `jp3_used_bound_Pa`)와 J-P3c의 used ≥ ext − 1 Pa 검사는 그대로다.

## 2. J-P3c에서 $p^*_{last}$가 NaN일 때

- `carry_ret` 읽기에서 `jp3_p_star_ret_Pa`가 NaN이면 **갇힌 몫(판정)**으로 본다.
  - 6.3절대로 $p^*_{last}$는 이동 중인 다리에서만 값이 있다. 잠긴 다리의 NaN은 6.2절 (가)에 따라 어차피 갇힌 몫이다.
  - 이동 중인데 NaN이면 채움 몫이라는 근거가 없으므로 판정 쪽(보수)에 둔다.
- 정오 1 2절 J-P3c 행의 대상 조건을 다음으로 읽는다: `carry_ret`이고 (`jp3_plant_state` ∈ {`locked_ext`, `locked_ret`} 또는 `jp3_p_tr_Pa` > `jp3_p_star_ret_Pa` 또는 `jp3_p_star_ret_Pa`가 NaN).
- 비교 열(`jp3_used_bound_Pa`)이나 참값(`jp3_p_tr_Pa`)이 NaN인 판정 읽기는 그대로 `record_defect`다(4a-7 4.4절).

## 3. P4 증거 검사의 적용 범위(정오 1 9절 보충)

- 정오 1 9절의 P4 증거 검사(`rod_reading_truth_calls` ①, `two_pressure_reads` ②)는 **436.9 하네스 실행 결과 줄에만** 건다. 하네스 배치 줄과 잡음 실행 결과 줄이 대상이다.
  - 적용 설정: 판정 설정 VBJ·LSJ1~4. 그리고 덧붙임 4a-2 B2·4a-5 2절·4a-7 1.2절이 정한 묶음(사례 F E 군, 사례 재생 E 군, T-JR-12 VBJ0 기준 줄, T-JR-10/11 줄)이다.
  - 436.9 본 실행(j9_main)의 J-P3 판정 입력도 같은 규칙을 적용한다. 판정 행을 고르기 전에 본다.
- 다음에는 적용하지 않는다. P4는 하네스 플랜트 옵션이라 이 기록들에는 증거 키가 원래 없고, 6.1절 판정 행도 아니기 때문이다.
  - 저장 T4h를 다시 재생한 보고(T-JR-13): 모니터만 저장 T4h로 다시 만든다.
  - Chrono 행: L2b 플랜트에는 P1~P4를 넣지 않는다(판 4a 3절 끝).
- 이 두 기록의 J-P3 값은 기록·대조용이다. 증거 키가 없다는 이유로 결함으로 보지 않는다.

## 5. 바뀌지 않는 것

- 봉인 6.2절의 판정 키·허용·판정 문장, 정오 1의 그 밖의 절, 4a-7의 그 밖의 절은 그대로다.
- 판정 집합과 기대값은 바뀌지 않는다. 1절은 같은 수를 두 열로 검사하는 기록 결함 규칙이고, 2절은 NaN 처리, 3절은 적용 범위, 4절은 실행 전제와 사전 점검이다.
