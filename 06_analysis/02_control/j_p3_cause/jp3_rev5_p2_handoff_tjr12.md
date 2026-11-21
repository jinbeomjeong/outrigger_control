# 경로 2 넘김 7: T-JR-12 경로 2 독립 재현 범위와 입력(2026-11-21)

- 아래 1절은 덧붙임 4a-8 정오 2의 1절을 바이트 그대로 옮긴 것이다. 앞 넘김과 다르면 이 넘김이 우선한다.
- 2절(재현 범위)·3절(입력)은 규칙 작성자(control-expert)가 정한 범위를 메인이 옮겨 적었다.

## 1. 잠금 창 대조 불일치(`stretch_mismatch`) 오류 줄
- 이 오류 줄은 등급(L2·L3·L4)·설정과 관계없이 **T-JR-14 (가) 실패**로 센다. 그 줄이 든 T-JR 묶음의 결과는 실패다(종료 1).
- 그 묶음의 J-P3는 매기지 않는다. 판정 행을 다시 세지도 않고, `run_error`·판정 불가로 바꾸지도 않는다. 보고에는 그 줄의 key 목록을 남긴다.
- T-JR-15 판정 집합에서는 그 줄에 시드 순 힘·재잠김 열이 없으므로 **판정 불가**다.
- 그 밖의 오류 줄은 4a-7 4.10절 그대로다(판정 설정 줄이면 `run_error`).
- 따라서 경로 2가 검토하던 안(L3·L4 오류 줄은 기록, L2는 판정 불가)은 이 오류 줄에는 쓰지 않는다.


## 2. 재현 범위(P2-1~P2-7)

| # | 재현 항목 | 기대 |
|---|---|---|
| P2-1 | VBJ 묶음 짝 조건: 짝 135, key 집합 = 저장 H-6, L2 줄 1, 새 줄 `v5_setting` = VBJ·`rule_revision` = 5, 기준 줄 `v5_setting` = VBJ0, 정체성(`spec_edition`·`carry_end_rule`·`retract_start_rule`) | 13.9·4a-5 3.1절 |
| P2-2 | B2 증거(양쪽 270줄): ① = k·② > 0(4a-8 정오 1 8절의 k) | 위반 0 |
| P2-3 | 새 FAULT(`warn_fault`의 FAULT 이름 차집합)와 READY 네 경우(4a-3 4.1·4.2절)를 135짝 전부에 | 목록 |
| P2-4 | VBJ 묶음 J-P3: 판정 행(normal 등급) 정확히 1, `jp3a_breach_reads`·`jp3b_breach_over_tol_reads`·`jp3c_breach_reads`를 per-read 자료(T4h)에서 독립 계산, 상태 | 상태 |
| P2-5 | L1 참조 확인(4a-8 4.3절): 설정마다 102줄, 오류 0, `level` L1, `rod_model` `plant_truth`, `v5_setting`, (harness, inner) 집합 = 저장 H-6의 102개. 키 파일은 4.2절 규칙(저장 H-6 첫 출현 순서, 키 `L1|s0|<harness>|<case_index>|<inner>`, 추출본 L1 키와 문자열 같음)으로 다시 만들어 sha 대조 | 통과 |
| P2-6 | L2 통과 → 실패(등급 없는 경로): L2 짝(`L2|s0|g6|52|ref|J1|top|Fs0`)의 `base`(`wall_s` 제외)·`r79` 기록이 같고 그 짝의 L1 참조 줄도 같으면 등급이 같으므로 통과 → 실패 0 | 같음이 확인되면 0 |
| P2-7 | VBH 묶음(대조만): VBH 대 저장 H-6의 새 FAULT·READY(P2-3과 같은 정의), L2 짝(P2-6과 같은 방법) | 대조 값 |

- P2-7은 판정을 바꾸지 않는다(결과 본 뒤). 경로 2 값이 다르면 `불일치`로 보고한다.
- S-1~S-6 등급 자체를 경로 2에서 다시 구현하는 것은 범위 밖이다(P2-6의 필드 동일성 논증으로 대신한다).

## 3. 입력(중립 사본 폴더, 원본과 sha 같음)

- 폴더: `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\bd7ff3b9-880c-4e9e-afd1-7024158f16f4\scratchpad\p2_tjr12_inputs\`(`SHA256SUMS` 폴더 기준으로 먼저 대조)

| 파일 | 뜻 | sha256 |
|---|---|---|
| `stored_H6.json` | 저장 H-6(키 집합, VBH 기준 쪽) | `ea0ab94c…` |
| `dg3_VBJ.json` / `dg3_VBJ0.json` | VBJ·VBJ0 Dg-3 135줄 | `603e4b81…` / `c1201b2d…` |
| `dg3_VBJ_t4h\` / `dg3_VBJ0_t4h\` | 각 135 npz(per-read 자료, P2-4) | 폴더 |
| `dg3_VBH.json` | VBH Dg-3 135줄(P2-7) | `1cf7f866…` |
| `l1_VBJ.json` / `l1_VBJ0.json` | 새 L1 참조 각 102줄 | `4698ee33…` / `9cf0ceae…` |
| `l1_keys.json` | 고정 L1 키 파일(P2-5 재생성 대조) | `eea8ed0d…` |
| `h6_L1_reference.json` | L1 추출본(키 문자열, VBH 쪽 L1) | `a591c3a8…` |

- 데이터 파일의 meta·명령 문자열에는 실행 쪽 경로·이름이 들어 있다. 그 경로를 따라가 다른 파일을 열지 않는다. 판정 출력 폴더와 실행 기록(명령 목록)은 넘기지 않았다.