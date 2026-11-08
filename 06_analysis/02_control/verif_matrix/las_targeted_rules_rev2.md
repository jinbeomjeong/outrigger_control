# LAS-b 표적·채택 규칙 덧붙임 판 2 (정정: 헤드 전용 실행의 L̂ 복원 규칙)

작성: control-expert, 2026-11-08.

> **상태: 봉인(2026-11-08).** SHA-256과 봉인 시각은 같은 폴더 `las_targeted_rules_rev2.sha256`에 있다. 이 파일은 더 고치지 않는다.
> - **고치는 판**:
>   - `las_targeted_rules.md`(`00b48fd834d81b9d499015f2d44380623e9fbcb2f1515913a8fd0589503eaf40`)
>   - `las_targeted_rules_rev1.md`(`0d5f59f8e4a09448b93e0cde42adb7d23c2f99f6b365809876efaa6212d27625`)
>   - 여기 적지 않은 항목은 그대로다. 채택 기준 C1~C6, S7′, 실행 목록, H-1~H-8, B-1~B-3, R-1~R-6이 그렇다.
> - **채택 전, 표적 결과를 보기 전의 정정이다.**
> - 본 것:
>   1. python-expert rev1 결과(`scratchpad\las_py2\`): H-8 통과, V-1 22건, V-2 3건, R-2 274건 δ = 0.0 N, b0 그림자 2,047건 중 판정 불가 822건(R-5 멈춤).
>   2. control-expert의 헤드 전용 복원 계산(`scratchpad\ctrl_liftoff\headonly_restore.py`, 3절).
>   3. 코드: `c2.py` `_read`·`_load_estimate_N`(COMBINED: `lower − _leg_seal_bands_N()`), `two_pressure.py` `read`(로드 압력 없음 또는 `HEAD_ONLY`: 네 판독 모두 `head_only = p_h A_h`, 이어 `_corrected`로 lower에서 영점 오프셋과 E-6 허용값을 뺌).
> - 사용자 결정(2026-11-08): 헤드 전용 L̂ 복원 규칙을 먼저 검토한다. 안 되면 재실행(약 19.8 CPU·h)한다.

## 1. 바뀌는 항목

| # | 위치 | 앞 | 새 |
|---|---|---|---|
| 1 | rev1 4절 | R-1(`t4h_replay` 폐루프 재생)이 로드 판독이 없는 실행에서는 돌지 않아 판정 불가였다 | **R-7 헤드 전용 규칙 H**로 복원한다(2절) |
| 2 | rev1 R-5 | 판정 불가 > 100이면 멈춤 | 규칙 H를 적용한 **뒤의** 판정 불가 수로 센다 |
| 3 | 멈춤 | H-1~H-8 | **H-9** 추가(2절 R-9) |

## 2. 규칙

| # | 규칙 |
|---|---|
| R-7 대상 | 로드측 판독이 컨트롤러에 들어가지 않은 실행이다. T4h에 `rod_pressure_Pa`가 없거나 전부 NaN이거나, 실행 설정이 `LoadEstimate.HEAD_ONLY`이거나, 기록에 `head_only_declared` = 참인 경우다. 어느 쪽인지는 python-expert가 기록 출처별(main·item8·p3_hash·u9_targeted·D-1)로 코드에서 확인해 도구에 적는다 |
| R-7 식 | $\hat L_{i,k} = p_{h,i,k} A_{h,i} - z_i - a_i(t_k) - b_{i,k}$. $p_h$ = T4h `head_pressure_Pa`(컨트롤러 입력값), $A_h$ = 헤드 면적(YAML, `geometry.head_area_m2`), $z$ = meta `zero_offset_N`, $a(t)$ = E-6 허용값(meta `pressure_offset_allowance_N`·`_from_s`가 있으면 그 값, 없으면 `t4h_replay.rebuilt_offset_allowance`로 사건·설정에서 다시 만듦), $b_k$ = T4h `seal_band_N`(그 주기의 다리별 띠). `ContactJudge.PRESSURE` 실행이면 $b = 0$ |
| R-7 제외 | LOC 전에 헤드 고장 사건(헤드 압력 보류 `_held_head_Pa`를 거는 사건)이 있는 기록은 판정 불가로 둔다. 영점 교정(CHECK) 전 주기는 관문 구간(LEVEL)이 아니므로 쓰지 않는다 |
| R-8 검증 | (가) 3절 D-1 헤드 전용 18건(이미 0.000 N). (나) 판정 불가 822건의 기록 출처별 표본을 관문 기록 래퍼로 재실행해 저장 L̂와 비교한다. main 2, item8 1, p3_hash 1, u9_targeted 2 = 6건 이상이고, VB·V0와 eps 0·> 0을 섞는다. 비교는 LOC 전 LEVEL 주기 $\max\lvert \hat L_{rec} - \hat L_{stored}\rvert$로 한다. 예상 약 10~15분(18 worker) |
| R-9 모드 | (가)·(나) 모두 ≤ 1 N이면 정확 모드다(rev1 R-3). 1 N 초과 ≤ 500 N이면 띠 모드다(rev1 R-4, δ = 관측 최대값). 그 밖이면 **H-9 멈춤**: 사용자에게 822건 재실행(관문 기록 래퍼, 약 19.8 CPU·h, 18 worker 약 1.1~1.5 h 벽시계)을 묻는다 |
| R-10 | 규칙 H로 판정한 기록은 그림자 출력에 `mode: head_only_rule`와 출처를 남긴다. V-2(미작동 3건 재실행 해시 일치)에 규칙 H 기록을 1건 이상 넣는다 |

## 3. 근거(헤드 전용 복원 오차, D-1 V-1 관문 기록 18건)

식 R-7로 다시 만든 L̂과 컨트롤러가 기록한 `lower_estimate_N`(`verdict_runs LoggedController._logged_lower_estimate_N`)의 최대 절대차.

| 묶음 | 건수 | 전 주기 최대 [N] | LOC 전 LEVEL 최대 [N] | 판독(`lower_reading_N`)과 $p_h A_h - z - a$ 최대 [N] |
|---|---|---|---|---|
| H-R-0 강체(T·M·B, flat·diag-op·fdown-op·roll+op, V0·VB) | 9 | 0.000 | 0.000 | 0.000 |
| H-R-A(J1@FR·FL·RL, V0·VB) | 9 | 0.000 | 0.000 | 0.000 |

- 이 18건은 모두 `rod_pressure_Pa` 기록이 없고(헤드 전용), 영점 오프셋·허용값은 0이다.
- 참고(대상 밖): 로드 판독이 있는 R12·R14·R15 관문 기록 4건에서는 이 식의 오차가 LOC 전 0.75~3.8 kN, 전 주기 15~22 kN이다. 로드 판독 실행은 규칙 H를 쓰지 않고 rev1 R-1(재생 모니터)을 쓴다.
- 남은 불확실성: 판정 불가 822건(main 752, item8 24, p3_hash 18, u9_targeted 28)은 D-1과 기록 경로가 다를 수 있다. 0이 아닌 영점 오프셋, E-6 허용값, 센서 오차 등급이 다를 수 있다. 그래서 R-8 (나)의 출처별 표본 검증이 필수다.

## 4. 다시 할 것

1. python-expert: `las_shadow.py`에 규칙 H, 대상 판별, 헤드 고장 제외, 출처 표시를 넣는다. R-8 (나) 표본 재실행 하위 명령을 둔다. 단위 시험은 식, 오프셋·허용값 시각, PRESSURE 판정 b = 0, 대상 판별이다.
2. R-8 (가)·(나) → R-9 모드 결정 → b0(채택 변형) 그림자 판정을 다시 한다. 판정 불가 수에 R-5(> 100이면 멈춤)를 적용한다.
3. 표적 T-0~T-2는 이 판과 무관하게 진행한다(그림자 판정은 채택 뒤 재실행 범위를 정할 때만 쓴다).
