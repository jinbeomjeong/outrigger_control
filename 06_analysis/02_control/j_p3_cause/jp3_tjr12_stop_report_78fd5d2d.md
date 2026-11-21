# 436.9 J-P3 j9_main 실행 78fd5d2d: 단계 (6) T-JR-12 멈춤 보고(13.5절, 사실만)

## 1. 실행
- 실행 커밋: `78fd5d2d03e40ac7d9143429f602b58255c762fc`(worktree `z4369-jp3`)
- 출력: `06_analysis/02_control/j_p3_cause/j9_runs/78fd5d2d/dg3_a1/`
- 시작 2026-11-21 18:21:16 +09:00, 멈춤 18:59:42 +09:00
- 단계 (1)~(5)는 종료 0이다(앞 커밋 기록 `1bdaeea7`).

| 항목 | 종료 코드 |
|---|---|
| Dg-3 실행 VBH / VBJ / VBJ0(135키, `--keys-file` 저장 H-6) | 0 / 0 / 0 |
| 출력 정체성 확인 | 0 |
| r79 등급 판정 VBH / VBJ / VBJ0 | 0 / 0 / 0 |
| T-JR-12 VBH | **1**(실패) |
| T-JR-12 VBJ | **2**(판정 불가) |

- 단계 (7)(T-JR-13~15)은 돌리지 않았다(4a-5 5.1절 멈춤).

## 2. VBH 묶음(VBH 대 저장 H-6 rev 4): 실패
- 짝 135, L2 판정 행 1(pass → pass), `l2_pass_to_fail` 0
- **새 FAULT 2키**(`FAULT_LIFT_STROKE_LIMIT`, FR):
  - `L3|s0|g8|32|slope|rpB|top|4.0|RR|raised|200.0`
  - `L3|s1|g8|19|slope|rpB|top|4.0|FL|raised|170.0`
- **READY 실패 11키**: READY 없음 9키, 30 s 넘게 늦음 2키
  - `L3|s0|g6|104|g6r|rigid+S1@RL|top|Fs0`(177.3 s → 없음)
  - `L3|s0|g6|106|g6r|rigid+S1@RL|bottom|Fs0`(107.4 → 없음)
  - `L3|s2|g6|106|g6r|rigid+S1@RL|bottom|Fs0`(126.5 → 없음)
  - `L3|s1|g6|65|g6r|rigid+J1@FL|top|Fs4`(73.2 → 107.3)
  - `L3|s2|g6|69|g6r|rigid+J1@FR|top|Fs4`(67.7 → 231.3)
  - `L3|s0|ref|11|rigid|B|0,3.5`(118.5 → 없음)
  - `L3|s0|g8|2|slope|edge|top|4.0|FL|raised|170.0`(81.6 → 없음)
  - `L3|s1|g8|9|slope|edge|top|4.0|RL|raised|140.0`(64.3 → 없음)
  - `L3|s1|g8|11|slope|edge|top|4.0|RL|raised|200.0`(64.2 → 없음)
  - `L3|s1|g8|15|slope|edge|top|4.0|RR|raised|200.0`(64.6 → 없음)
  - `L3|s2|g8|1|slope|edge|top|4.0|FL|raised|140.0`(62.4 → 없음)
- 기록:
  - 둘 다 READY 없음 5키, READY 개선 2키
  - L3 등급 전이: pass → pass 94, flag → flag 20, fail → fail 10, pass → fail 7, flag → fail 3
  - `retract_tracker_dominated_reads` 7,338, `retract_tracker_over_tol_reads` 7,338, `retract_tracker_false_drop_reads` 509
  - `ret_after_gate_s` 349개, 최대 5.3 s(분해능 0.1 s)
- 입력 sha256:
  - 저장 H-6 `ea0ab94c…`
  - H-6 판정 파일 `d95627ac…`
  - `dg3_VBH.json` `1cf7f866…`
  - VBH 판정 파일 `b7f81009…`
- 원인 분류(덧붙임 4a-8 1절): **실제 판정 실패**(판정 도구 결함 없음)
  - 13키 모두 원 줄로 다시 계산해 같았다.
  - 명령 해시가 같은 짝은 115/135다(대체 다리 없는 2행 포함).
  - 명령이 바뀐 20행은 모두 대체 다리가 있는 행이다. 그중 19행은 바뀐 다리에서 `retract_tracker_dominated_reads` > 0이다.
  - VBH 판정 파일: 판정 행 135, 짝 없음 0, 오류 0.
- 결과를 본 것: t12 보고(종료 1)를 쓴 때, 그리고 control-expert가 원인 분류를 위해 위 키의 READY·FAULT·명령 해시·`rod_fallback`·`retract_tracker_*` 기록을 연 때(2026-11-21, 사용자 결정 1).

## 3. VBJ 묶음(VBJ 대 VBJ0): 판정 불가, 결과를 보지 않음
- 판정 값(`t12_VBJ.json`, VBJ·VBJ0 등급 판정 파일)은 열지 않았다.
- 원인 셋(판정 값이 아닌 설정 증거 키와 코드에서 확인):
  1. B2 증거: g8 계열 40줄은 VBJ·VBJ0 모두 ① = 2·②다(나머지 95줄은 ① = ②). 4a-2 B2의 "① = ②"는 G8 경로의 이중 판독(순수 함수, 값 불변)을 반영하지 않았다. 앞선 건식 확인은 g6 키 하나만 돌렸다.
  2. L1 참조 짝: VBJ·VBJ0 줄은 `rod_model` = `plant_truth`인데, P-1a L1 참조(sha `a591c3a8…`)는 167줄 모두 `dyn_map`이다. 등급 판정 짝 키가 `rod_model`을 포함하므로 짝이 0이다.
  3. r79 등급 판정 하위 명령이 판정 행 0인 판정 파일을 종료 0으로 썼다.
- 입력 sha256: `dg3_VBJ.json` `603e4b81…`(로컬 전용), `dg3_VBJ0.json` `c1201b2d…`

## 4. T-JR-12 상태
- 13.9절 기준으로 **실패**다(VBH 묶음 실패).
- VBJ 묶음은 덧붙임 4a-8대로 고친 뒤 다시 판정한다. 실행 전 사용자 승인을 받는다.
- 정식 T-JR-12 판정서는 그 뒤에 쓴다.
- 다음 단계는 판 5(봉인 9절 C1~C3, 2.10절 안 B 조건)다.

## 5. 로컬 전용 파일
- `dg3_VBH.json`(167,317,196 B), `dg3_VBJ.json`(161,168,847 B)은 git에 넣지 않는다.
- sha는 `j9_runs/78fd5d2d/dg3_a1_LOCAL_ONLY.SHA256SUMS`에 있다.
- 출력·partial·T4h는 지우거나 고치지 않는다(4a-5 5.2절).
