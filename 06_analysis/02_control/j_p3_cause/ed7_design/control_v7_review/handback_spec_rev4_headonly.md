## 판 7 명세 개정 4 추가: 결정 6(head-only 줄) 반영

결정 6을 개정 4 안에서 명세에 반영했습니다. 코드는 고치지 않았고 봉인도 하지 않았습니다.

- 명세: `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\jp3_remedy_spec_v7.md`
- 직전 sha256: `b79f9cfc…`(653줄)
- **새 sha256: `eae2b90b6c9b7c8473bbaee02164b76ebe4a224ac6570e5398d93e0049ad1717`**(661줄)

### 바뀐 곳
| 위치 | 바뀐 내용 |
|---|---|
| 머리 개정 표 4행 | "사용자 결정 5개"를 "6개"로 고치고, 6번 근거로 진단 원문 경로를 붙였습니다. |
| 개정 4 결정 목록 | 6번을 그대로 적었습니다. 근거로 진단 원문 `ed7_design/tool_6bfb2560/handback_condition_diag.md`(sha256 `ee95465d…`), probe 재실행 없음, python-expert 새 커밋을 함께 적었습니다. |
| 개정 4 바뀐 절 표 | 「3.5, 6.1」 행을 더했습니다. |
| 3.5 | 인용 블록 뒤에 「head-only 줄」 항목을 넣었습니다(아래). |
| 6.1 | J-P3 조건 행 판별 아래에 같은 규칙을 요약했습니다. `head_only`는 상태 순서(실패 > `setting_defect` > `not_judgeable` > 통과)에 들지 않는 줄 단위 기록 상태라고 명시했습니다. |
| 12절 | 공개 한 줄을 더했습니다(아래). |

3.5에 넣은 「head-only 줄」 규칙은 다음과 같습니다.
- **판단 순서**: T4h meta `head_only_declared` → 줄 `head_only_declared` → 둘 다 없으면 event 경로(보수)로 봅니다. 판 4a-7 1.1과 `is_head_only_line` 규약과 같습니다.
- **선언된 줄**: 상태 `head_only`(해당 없음, 기록)로 두고 판정 줄과 분모에서 뺍니다.
- **모순 줄**: 선언은 head-only인데 ③ 배열이나 `t_event_s`가 있으면 판정 플랜트에서 `setting_defect`입니다.
- **event 경로 줄**: 배열이나 사건 시각이 없으면 지금처럼 `setting_defect`입니다.

12절에 넣은 공개 문장의 내용은 다음과 같습니다.
- probe 6bfb2560의 조건 도구 초회 실행에서 head-only 252줄이 결함으로 분류됐다. 판정 플랜트 210줄은 `setting_defect`, L 플랜트 42줄은 `not_judgeable`이었다.
- 원인은 도구 결함이고, probe는 다시 돌리지 않았다.
- 규칙은 도구 출력의 건수 분류를 본 뒤 적었고, 판정 지표 값은 보지 않았다.

### 작업 범위
- Read는 진단 원문과 명세에만 썼습니다.
- PowerShell로 `tool_6bfb2560` 폴더 목록을 보고 sha를 계산했습니다. 그 폴더의 `SHA256SUMS`는 `2f712058…`입니다.
- Grep은 명세에만 썼습니다.
- scratchpad는 쓰지 않았고, 블라인드 경로는 어느 도구의 대상에도 넣지 않았습니다.

사용한 스킬: 없음
