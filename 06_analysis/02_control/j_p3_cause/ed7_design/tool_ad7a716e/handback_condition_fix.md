## 조건 도구 head-only 수정과 재실행 (ad7a716e)

승인받은 수정안 1~7을 그대로 반영했습니다. 저장된 probe 출력에 조건 도구를 새 파일로 다시 돌린 결과, 종료 0, summary status **`pass`**입니다.

### 상태 분포 (`condition_ad7a716e.json`, 654줄)

| 상태 | 건수 | 내용 |
|---|---|---|
| head_only | 252 | 판정 플랜트 210 + 기록 플랜트(L) 42 |
| judged | 339 | |
| record | 63 | |
| not_judgeable | 0 | |
| setting_defect | 0 | |

summary 원문(해석 없이 옮김): `{"status":"pass","judged_lines":339,"judged_lines_with_condition":320,"judged_condition_reads":4079,"judged_breach_reads":0,"record_lines":63,"head_only_lines":{"judged_plant":210,"record_plant":42},"states":{"head_only":252,"judged":339,"record":63},"record_artifact_reads":0}`

- 새 출력: `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\6bfb2560\ed7_probe_a1\condition_ad7a716e.json`, sha256 `9bd2dba8…`
- 기존 `condition.json`(sha256 `88c01e5f…`)은 건드리지 않았습니다. 출력 폴더의 다른 기존 파일도 고치거나 지우지 않았습니다.

### 바뀐 내용
커밋 **ad7a716e**(ed7-impl, 부모 6bfb2560)이고 병합·push는 하지 않았습니다. 바뀐 파일은 `jp3_rev7_condition.py`와 `test_ed7_units.py` 두 개입니다.

1. **head-only 선언 판단**: 판 4a-7 1.1 순서를 따릅니다.
   - T4h meta의 `head_only_declared`를 먼저 보고, 없으면 줄의 값을 봅니다.
   - 둘 다 없으면 event 경로로 보고 엄격하게 다룹니다.
   - 이를 위해 `read_t4h`가 조건 배열, 전체 배열 이름, `meta_json`을 함께 읽습니다.
2. **선언된 줄**: 어느 플랜트든 상태 `head_only`가 되고 판정 집합과 `judged_lines` 분모에서 빠집니다.
3. **모순 줄**: head-only로 선언됐는데 `jp3_*` 조건 배열이나 `t_event_s`가 있는 줄입니다.
   - 판정 플랜트에서는 `setting_defect`, 옛 플랜트에서는 `not_judgeable`로 둡니다(사용자 결정대로).
   - 무엇이 모순인지는 `head_only_contradictions`에 적습니다.
4. **선언이 없는 줄**: 배열이나 사건 시각이 없으면 지금처럼 `setting_defect`입니다.
5. **summary 키 추가**: `states`(전체 상태 건수)와 `head_only_lines`(플랜트 종류별)를 더했습니다.
   - `judged_lines`와 `record_lines`는 head-only 줄을 빼고 셉니다.
   - stdout 마지막 줄 JSON에도 같은 키가 들어갑니다.
   - docstring에도 이 상태들을 적었고, 종료 코드는 그대로입니다.
6. **읽기 방식**: rows 파일을 한 줄씩 스트리밍으로 읽게 바꿨습니다(154.8 MB 대응).
7. **새 시험**
   - head-only, 선언 없음, meta 우선, 모순(판정 플랜트와 옛 플랜트) 경우를 각각 확인합니다.
   - 생산자 출력 꼴(T4h 이름만 있는 줄, `<stem>_t4h` 폴더)로 CWD를 입력과 다른 폴더에 둔 채 `main`을 끝까지 돌립니다(종료 0, 상태 분포 단언).

### 검증
- **ruff**: 바뀐 두 파일에서 위반 0.
- **ed7 시험** (`test_ed7_units` + `test_ed7_harness`; Chrono-dev, 하네스는 dynamics-dev): 63 통과, skip 0.
  - P7-0(옛 플랜트 7줄의 명령 해시가 79495405와 같음)과 P7-1 미리보기(VBM R12 = VBM0 R12)가 이 안에 포함됩니다.
- **관련 시험 22파일** (`-n 8`): 851 통과, 18 skip.
  - skip은 6bfb2560 때와 같은 저장 자료 skip입니다. 그 파일들은 이번에 바꾼 도구를 import하지 않아서 worktree_tests는 다시 돌리지 않았습니다. 6bfb2560에서는 0 skip이었습니다.
  - 그중 2개는 `X10_BASE_ROOT` 미설정으로 나는 설계상 skip입니다.
- 전체 suite(303파일)는 돌리지 않았습니다.

### 근거
`C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\tool_ad7a716e\`
- `tests\`: ed7 시험과 관련 시험의 JUnit, 로그
- `manifest.json`: 조건 도구 재실행 명령, 종료 코드, stdout 마지막 줄, 출력 sha256, 기존 `condition.json` sha256
- `SHA256SUMS`: 5항목, sha256 `fed120d4…`

### 규칙 준수
- 검색은 worktree의 `04_scripts`, `05_tests`와 `j9_runs\6bfb2560\` 아래로만 했습니다. 블라인드 경로에는 닿지 않았습니다.
- 스크립트는 Write로 쓴 파일을 PowerShell에서 `-I -B`로만 실행했습니다. 종료한 프로세스는 없습니다.
- scratchpad `python-ed7cond2\`는 지웠습니다.

사용한 스킬: 없음.

### 위임 필요
- **control-expert (명세 개정 3)**: 다음 두 문장을 넣어야 합니다.
  - head-only로 선언된(정상 경로) 줄은 ③ rev 7 조건에 해당하지 않으며, 상태 `head_only`로 판정 집합 밖 기록이 된다.
  - 선언과 모순되는 줄은 판정 플랜트에서 setting_defect다.
- **본 실행 전**: 러너 마지막 단계가 ad7a716e 이후의 도구를 쓰는지 확인해 주십시오. `ed7_j9_main`에는 정상 경로 행이 있어서, 옛 도구를 쓰면 같은 defect가 다시 납니다.
