# 덧붙임 4a-7 정오 1 (2026-11-21, control-expert 문안)

- 대상: `jp3_remedy_spec_addendum_4a7.md` 1절·4절. 그 밖의 문장과 봉인 본문·앞 덧붙임은 바뀌지 않는다.
- 근거: 경로 2 작성자의 후속 질문 9건(4a-7 4절을 반영하는 중에 나온 문장 사이의 겹침과 빈 곳).
- 시점: 결과 전 정정이다. 판정 결과는 아직 없다. 봉인 본문 6.2절의 판정 키 표를 기준으로 맞춘다.
- 이 정오의 문장이 4a-7 4절과 다르면 **이 정오가 우선**한다.

## 1. J-P3b 대상 읽기(질문 1)

- 4a-7 4.2절의 "J-P3b: `lock`·`hold` 읽기"는 틀렸다. 봉인 6.2절대로 **J-P3b 판정(`jp3b_breach_over_tol_reads`)은 `hold` 읽기만**이다.
- `lock` 읽기는 판정이 아니다.
  - 플랜트 신장 뒤 잠김: `lock_ext_breach_over_tol_reads`(FLAG)
  - 플랜트 수축 뒤 잠김: `lock_ret_breach_reads`(기록)
- 경로 2의 지금 처리(hold만 판정, lock은 기록)가 맞다.

## 2. 판정 비교값(질문 2)

- 4a-7 4.2절의 "세 판정 모두 비교값은 `jp3_used_bound_Pa`"를 다음으로 바꾼다. 봉인 6.2절의 비교식을 그대로 기록 열에 대응시킨다.

| 판정 | 대상 읽기 | 비교 열 | 허용 |
|---|---|---|---|
| J-P3a | `ext` + `carry_ext` | `jp3_p_tr_Pa` > `jp3_ext_bound_Pa`($\hat p+\delta_m$) | 1 Pa |
| J-P3b | `hold` | `jp3_p_tr_Pa` > `jp3_model_bound_Pa`(④) | 0.6 kN/$A_{ann}$(4a-7 4.11절) |
| J-P3c 갇힌 몫 | `carry_ret`이고 (`jp3_plant_state` ∈ {`locked_ext`, `locked_ret`} 또는 `jp3_p_tr_Pa` > `jp3_p_star_ret_Pa`) | `jp3_p_tr_Pa` > `jp3_used_bound_Pa`(= $\max(\hat p+\delta_m,\ 수축\ 이동\ 모델)$) | 1 Pa |

- J-P3c는 수축 이동 모델 값이 따로 기록되지 않으므로 `jp3_used_bound_Pa`를 쓴다. 그 읽기에서 `jp3_used_bound_Pa` ≥ `jp3_ext_bound_Pa` − 1 Pa가 아니면 `record_defect`다(4a-7 4.2절 그대로).
- `jp3_used_bound_Pa`가 J-P3a 읽기에서 `jp3_ext_bound_Pa`와, J-P3b 읽기에서 `jp3_model_bound_Pa`와 1 Pa 넘게 다른 읽기는 **기록**이다(결함 아님). 모니터의 대체 추정은 판 4a 2.1절 표대로 다른 항(13 bar 바닥, ⑤)을 더할 수 있고, 판정은 6.2절 비교식으로 하기 때문이다. 다른 읽기 수를 보고에 남긴다.
- 비교 열이 NaN인 판정 읽기는 `record_defect`다(4a-7 4.4절 그대로).

## 3. 선언 근거가 없는 줄(질문 3)

- 4a-7 1.1절의 세 단계는 T-JR-10/11의 22잡을 위한 것이다. J-P3 판정 입력의 줄은 다음 순서로 가른다.
  1. 잡음 실행 결과 줄(`level`이 있는 줄)은 이벤트 경로다(두 압력을 읽는다). 선언을 보지 않는다.
  2. 하네스 배치 줄은 1.1절 순서(T4h meta `head_only_declared` → 줄의 `head_only_declared` → 개정 9 3.1·3.3절 사례 표)로 가른다.
  3. 그래도 정해지지 않는 줄(선언 기록이 없고 사례가 표 밖)은 **미선언(이벤트 경로)**으로 본다.
- 3번 줄은 4a-7 1.2절 결함 규칙을 그대로 받는다. 판독이 없거나 record가 없으면 `setting_defect`다. 그래서 잘못 가른 줄은 통과가 아니라 결함으로 드러난다. 경로 2의 처리가 맞다.

## 4. 이름이 적힌 T4h가 없을 때(질문 4)

- 상태 이름은 `record_defect`(판정 불가 부류)다. 경로 2의 처리가 맞다.

## 5. 재잠김 1 bar 초과의 경로 2 집계(질문 5)

- 경로 2는 per-lock 행 `lock_log`의 `dp_tr_step_Pa`로 직접 센다. 절댓값이 10⁵ Pa를 넘으면 센다(같으면 세지 않음). 값이 유한하지 않은 행은 세지 않고, 그 수를 따로 보고한다.
- 직접 센 값이 기록된 `relock_step_over_1bar_count`와 다르면 `record_defect`다.
- `lock_log` 행 수가 상한 2,000행에 닿았으면 전부 다시 셀 수 없으므로 `record_defect`다.
- 대상은 판정 설정 VBJ·LSJ1~4의 결과 줄 전부다. 센서 등급(L3 포함)과 헤드 전용 선언에 관계없다. 재잠김은 플랜트 양이라 판독 오차와 무관하기 때문이다.
- 1 이상이면 실패다(4a-7 4.6절). 경로 2의 처리가 맞다.

## 6. 기록 행으로 내리기 전의 검사(질문 6)

- conservative·old_worst 등급의 VBJ·LSJ 줄도, 기록 행으로 내리기 전에 13.6절 정체성·제어기 태그·헤드 전용 선언 규칙(4a-7 1.2절)을 먼저 본다. 어기면 `setting_defect`다(13.6절: 판정 입력에 들어온 기본값이 아닌 rev 5 행은 등급과 관계없이 결함). 경로 2의 처리가 맞다.

## 7. 판정 행 수 불일치의 위치(질문 7)

- 판정 행 수가 정해진 묶음(13.2·13.9절: T-JR-12 VBJ 묶음은 정확히 1)에서는 다음과 같다.
  - 판정 행이 0이면 `no_judged_runs`
  - 0이 아니지만 정해진 수와 다르면 `judged_row_count_mismatch`
- 두 상태는 모두 판정 불가 부류다. 4a-7 4.10절 우선순위에서 `judged_key_missing` 다음, `H-7` 앞에 둔다. 순서는 `no_judged_runs` > `judged_row_count_mismatch`다.
- 두 경로 대조는 부류로 맞춘다(4a-7 4.10절). 사유 이름이 다르면 보고에 함께 적는다.

## 8. 명령 경계 허용(질문 8)

- ±10⁻¹² m/s 허용을 $u$ = 0 쪽에도 적용한다.
  - $u$가 정확히 0이면 `lock`만 허용한다(`hold` 아님).
  - $0<\lvert u\rvert\le 10^{-12}$ m/s이면 `lock`·`hold` 둘 다 허용한다.
  - $\lvert u\rvert$가 $u_{hold}$ ± 10⁻¹² m/s 안이면 `hold`와 해당 방향의 `carry_*`·`ext`/`ret`를 둘 다 허용한다.
- 경로 2의 처리가 맞다.

## 9. P4 증거(① = ②) 검사(질문 9)

- J-P3 판정에도 넣는다. 봉인 6.4절은 VBJ·LSJ 판정 행의 로드 판독이 플랜트 M2 참값(P4)이라는 전제에 J-P3 판정을 기댄다. 증거 키(`hydraulics_record`의 `rod_reading_truth_calls` ①, `two_pressure_reads` ②)는 그 전제를 확인하는 규칙 용어다(덧붙임 4a-2 B2).
  - 선언 없는(이벤트 경로) VBJ·LSJ1~4 줄: ① = ② > 0이어야 한다. 아니면 `setting_defect`다.
  - 헤드 전용 선언 줄: ① = 0이고 ② = 0이어야 한다(4a-7 1.2절).
  - 증거 키가 없는 줄은 `setting_defect`다.
- 판정 설정 밖 줄(VBH·LSH·VB·LS)의 증거 규칙은 판정 대상이 아니므로 J-P3 경로 2에서는 기록만 한다.

## 10. 바뀌지 않는 것

- 4a-7의 그 밖의 문장, 봉인 6.2절의 키·허용·판정 문장, 4a-7 4.10절의 다른 우선순위는 그대로다.
