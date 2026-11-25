## probe 6bfb2560 조건 도구 `setting_defect` 진단 (고치기 전 보고)

### 결론
결함은 **조건 도구(`jp3_rev7_condition.py`)**에 있습니다. probe에는 문제가 없습니다.
- 걸린 252줄은 모두 **head-only로 선언된 정상(steady) 경로 줄**입니다. 이 경로에는 원래 ③ 추적 배열과 사건 시각이 없으므로, 조건이 정당하게 **해당 없음**인 줄입니다.
- 그런데 도구가 판정 플랜트(p1_patch 켬)의 줄이면 배열이나 `t_event_s`가 없을 때 무조건 `setting_defect`로 분류합니다(`line_condition` 첫 분기).
- 그래서 판정 플랜트 5종 × 42줄 = **210줄이 setting_defect**, L 플랜트의 42줄이 not_judgeable이 됐습니다. 252 = 210 + 42입니다.
- probe를 다시 돌릴 필요는 없습니다(0줄). 저장된 jsonl과 T4h를 고친 도구로 다시 읽으면 됩니다.
- 이 결함은 앞 보고의 커밋 6bfb2560에도 그대로 있습니다. 제 단위 시험에 head-only 줄이 없어서 놓쳤습니다.

### 근거 (구조·건수만, 판정 지표 값은 보지 않음)
- 출력 폴더의 T4h는 654개 모두 있습니다. 경로나 이름 불일치는 없습니다(`t4h_file`이 654줄 모두 가리키는 파일이 존재).
- 케이스별 구조는 아래와 같습니다. 줄 수는 6플랜트 × 7팔에 D부(M·Mslow × a2)를 더한 것입니다.

| 케이스 (키 수) | 경로 | `t_event_s` | T4h `jp3_*` 5개 배열 | `hydraulics_record.extend_bound_check` | `head_only_declared` (줄 / T4h meta / `is_head_only_line`) | 줄 수 |
|---|---|---|---|---|---|---|
| R12 ((가)·C 3 + D0 일부, D부 12) | event | 있음 | 있음 | 있음, reads > 0 | False / False / False | 318 |
| R15 (D0 2) | event | 있음 | 있음 | 있음 | False / False / False | 84 |
| R2 e0.001·e0.003 | steady | None | 없음 | None | True / True / True | 84 |
| S1 (D0) | steady | None | 없음 | None | True / True / True | 42 |
| S4 e0.002 | steady | None | 없음 | None | True / True / True | 42 |
| S5 (D0) | steady | None | 없음 | None | True / True / True | 42 |
| S7 e0.001 | steady | None | 없음 | None | True / True / True | 42 |

- 정상 경로 줄은 7팔(a1~a6, c2)과 6플랜트(L, M, Mslow, Mfast, Mc005, Mc04) 모두에서 같은 꼴입니다. 팔이나 플랜트에 따른 저장 조건 차이는 없습니다.
  - 정상 경로(`verdict_runs._run_steady`, s9_soil_slope)는 head-only 하네스입니다. 플랜트의 ③ 검사 `extend_bound_check`가 만들어지지 않으므로 `jp3_trace_arrays`가 None이고, T4h에 `jp3_*`가 없습니다.
  - 사건이 없으니 `t_event_s`도 None입니다.
  - 이것은 판 4a-7 이후의 기존 규약(`jp3_baseline_compare.is_head_only_line`, `ed6_key_lists.is_head_only`, 정상 경로 = head-only 선언)과 같습니다. `ed7_key_lists`도 이미 `head_only_declared` 줄을 J-P3 기대 행에서 뺍니다.
- 조건 도구의 다른 분류는 이 표로 맞아떨어집니다.
  - judged 339 = 판정 플랜트 event 줄 (5 × 63 + D부 24)
  - record 63 = L 플랜트 event 줄
  - not_judgeable 42 = L 플랜트 steady 줄

### 수정안 (조건 도구만 고침, 아직 커밋하지 않음)
1. `line_condition`에서 배열이나 사건 시각을 보기 전에 head-only 선언을 확인합니다.
   - 판단 순서는 4a-7 1.1과 같습니다: T4h meta의 `head_only_declared` → 줄의 `head_only_declared` → 둘 다 없으면 event 경로로 봅니다(보수).
   - `read_arrays`는 `meta_json`도 함께 읽게 합니다.
2. head-only로 선언된 줄은 새 상태 `head_only`(해당 없음, 기록)로 둡니다. 판정 집합과 `judged_lines` 분모에는 넣지 않습니다.
   - 다만 선언은 head-only인데 `jp3_*` 배열이나 `t_event_s`가 있으면 모순입니다. 판정 플랜트에서는 이 경우를 `setting_defect`로 둡니다.
3. event 경로 줄(선언 없음 포함)에 배열이나 사건 시각이 없으면 지금처럼 `setting_defect`입니다.
4. `summarize`에 `head_only_lines`(판정 플랜트, 기록 플랜트 각각)를 더합니다. 판정 줄 수에는 event 경로 줄만 셉니다.
5. 모듈 docstring의 상태 표에 `head_only`를 더합니다. 종료 코드는 바꾸지 않습니다.
6. 시험을 더합니다.
   - 정상 경로 줄(배열 없음, `t_event_s` None, 선언 True)이 판정 플랜트에서 `head_only`가 되고 상태에 영향이 없는 것
   - 선언이 없는 같은 줄이 `setting_defect`가 되는 것
   - 모순 줄
   - 생산자 출력 꼴(행에 파일 이름만 있음) 그대로, CWD를 입력과 다른 폴더에 둔 채 `main`을 끝까지 돌리는 시험 하나
7. 고친 뒤에는 저장된 `ed7_probe.jsonl`에 도구를 **새 `--out` 파일**로 다시 돌립니다. 기존 `condition.json`은 건드리지 않습니다(도구가 덮어쓰기를 거부함). 이때 head_only 252, judged 339, record 63이 예상되고, 상태는 판정 줄의 조건 읽기로 정해집니다.

### 재실행 범위
- probe: **0줄** (모든 T4h와 줄은 정상).
- 조건 도구: 수정 커밋 뒤 저장 출력에 대해 한 번(수 분).
- 본 실행 전에 같은 수정이 필요합니다. `ed7_j9_main`에는 정상 경로 행이 들어 있으므로, 고치지 않으면 그 행도 같은 식으로 defect가 됩니다.

### 확인 필요
- head-only 줄의 상태 이름(`head_only`)과, 그 줄을 판정 집합 밖 기록으로 두는 해석을 명세 개정 3에 명시해야 합니다(control-expert). 지금 명세(지시문 인용 3.5·6.1)는 "판정 줄에 T4h나 사건 시각이 없으면 setting_defect"이고, head-only 예외는 적혀 있지 않은 것으로 압니다(명세는 열지 않았음).
- 모순 줄(선언은 head-only인데 ③ 배열이 있음)을 setting_defect로 둘지는 제 판단입니다.

### 수행·규칙
- 읽은 것: `j9_runs\6bfb2560\ed7_probe_a1\`의 jsonl(스트리밍, 구조 키만), T4h npz의 배열 이름과 `meta_json`의 `head_only_declared`, 폴더 목록. 그리고 worktree의 `jp3_rev7_condition.py`, `verdict_runs.py`, `jp3_baseline_compare.py`, `ed6_key_lists.py` 일부.
  - 조건 침범 수, 간격, 압력 등 판정 지표 값은 읽지 않았습니다. `extend_bound_check`는 존재 여부와 reads > 0 여부만 봤습니다.
- 출력 폴더의 파일은 고치거나 지우지 않았습니다. 코드도 고치지 않았고 커밋하지 않았습니다.
- 검색은 `j9_runs\6bfb2560\`와 worktree의 `03_src`, `04_scripts`만 대상으로 했습니다. 블라인드 경로는 열지도 검색하지도 않았습니다.
- 실행 방식: Write로 쓴 스크립트를 PowerShell에서 python-dev / dynamics-dev `-I -B`로 돌렸습니다.
- scratchpad `python-ed7cond\`는 지웠습니다.

사용한 스킬: 없음.

### 위임 필요
- **python-expert(본인, 승인 뒤)**: 위 수정안 1~7을 반영하고, ed7-impl에 커밋하고, 조건 도구를 새 `--out`으로 다시 실행합니다.
- **control-expert**: 명세 개정 3에 head-only 줄을 해당 없음(기록)으로 둔다는 문장을 넣습니다.
