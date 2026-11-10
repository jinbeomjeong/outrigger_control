# K-2 규칙 덧붙임 rev4 (결과 전, 2026-11-10)

- 작성: control-expert, 2026-11-10. 봉인 정보는 같은 폴더의 `k2_touch_creep_rules_rev4.sha256`.
- 원판(`a3658197…7263`), rev1(`5ba081c6…4776`), rev2(`b3f1b41f27030c75aec726d2a3feb5abc36697864e0d83766a8fe0c4460394ea`), rev3(`8bcdb0ed1fdf6d730ac781929e93b233972d1e80566e1ae14ffb7ddf049d6e61`)를 고치지 않고 아래만 덧붙인다. 다르면 rev4 > rev3 > rev2 > rev1 > 원판 순으로 맞다.
- 시점: V-1~V-7 결과 0건.
  - 경로 2를 rev2 1절대로 고친 뒤, 저장된 **최종 제어기 인수 출력**(`touch_phase/acceptance/{grid,soil,d8,noise,regression,g8_safe_stop}`, `touch_phase/ps7_E.json`)을 두 팔에 같은 파일로 넣어 형식을 점검했다. 이 출력들은 criteria.md 인수에서 통과로 판정된 것이다.
  - rev2 1절 문구 그대로면 세 군데가 이 통과 출력을 실패로 낸다. 셋 다 rev2가 criteria.md를 옮길 때 문구를 잘못 구체화한 것이다. criteria.md와 기존 판정기(`acc_judge.py`)의 뜻으로 되돌린다. 판정을 완화하는 것이 아니라 원래 기준으로 돌아가는 것이다. K-2 결과는 보지 않았다.

## 1. rev2 1절 정정

**(a) 오류 행.** "`error` 키가 있는 행"을 "`error` 키의 값이 비어 있지 않은 행"(None, 빈 문자열, 빈 목록은 오류 아님)으로 바꾼다.
- 근거: G8 구동기(`g8trace.py`)는 모든 행에 `"error": null`을 쓴다. 저장 G8 83행이 전부 "오류"로 셌다.

**(b) 잡음 SGS 설정 불일치.** "원 실행 `results[]`마다 `controller_settings` = `meta.preset_settings`"를 "`controller_settings`와 `meta.preset_settings`의 **`lift_stroke_guard.` 키**(SGS 설정)가 같다"로 바꾼다.
- 근거: criteria.md 문구는 "SGS `controller_settings` 불일치 0"이다. 저장 잡음 출력에서 L2 855행은 `target.gyro_noise_std_rad_s`(잡음 수준별 자이로 잡음, 설계상 다름) 한 키만 meta와 달랐다.
- 그 밖의 키는 비교하지 않는다. SGS 키가 하나도 없으면 결측(E-9 실패)으로 센다.

**(c) 회귀 r79 판정 `unmatched`.** 회귀 묶음 절대 항목에서 "r79 판정 파일 `unmatched` = 0"을 뺀다. 그 값은 기록한다. `errors` = 0과 공통 오류 행 0은 그대로 둔다.
- 근거: criteria.md 회귀 행의 기준은 "L1·L2·토양·경사 행 통과→실패 0"뿐이고, `unmatched` 항목이 없다.
- 저장 회귀 r79 판정에는 구조상 `unmatched` 1키(`cand=current#L2|s2|g6|55|ref|J1|bottom|Fs4`, L1 기준이 없는 L2 행)가 있다. 이 키는 2절의 기록 49에 들어 있다.
- 잡음 L2 묶음의 `unmatched` = 0은 criteria.md 잡음 문구 그대로 남긴다.

## 2. 점검 결과 (판정 아님, 결과 전 형식 점검)

경로 2(이 판을 반영한 `k2_recount.py` 1.3)의 V-5 묶음 함수에 저장 인수 출력을 두 팔로 같게 넣은 결과다.

| 묶음 | 행 수 | 절대 항목 | 비고 |
|---|---|---|---|
| 격자 | 768 | 통과 | |
| 토양 | 60 | 통과 | |
| D8 | 576 | 통과 | |
| 잡음 L2 | 855 | 통과 | CP·unmatched·errors·false_loc·SGS |
| 회귀 | 93 | 통과 | 판정 키 sha `2900db88…`, 기록 키 sha `d4f58334…` 일치 |
| PS-7 | 20 | 통과 | |
| G8 | 83 | 통과 | |

- 공통 항목(provenance, K-2 증거)은 저장 출력에 해당 기록이 없어 점검하지 못했다.
