## 감사 M-8 사전 재현 대조: 팔 a2, b46bdf8f 재실행과 원본 6bfb2560

모든 항목이 일치합니다. 불일치는 없습니다(`status: match`, 종료 0).

| 대조 항목 | 결과 |
|---|---|
| 줄 집합(job 이름, 실행 시 붙는 필드 제외) | 원본 a2 114줄 = 재현 114줄. 한쪽에만 있는 줄 0, 재현 쪽 오류 줄 0, T4h 파일 이름 불일치 0 |
| `commands_sha256` | **114/114 일치** |
| 새 기록 키(재현 114줄 전부) | `lsb_record.blind.level_done`, `lsb_record.blind.twist_over_limit`, T4h 배열 `lsb_ib_twist_load_N` 모두 있음(빠진 줄 0). 원본에는 두 키가 0줄이라 예상과 맞음 |
| 재현 identity | start·end 모두 HEAD `b46bdf8fdbad730eabf9226c5e1cfed0e980b5e9`, `is_clean: true`. `run_identity_problems` 0건 |
| 고정 표 64행 재계산(sens 40단위 + D 24줄) | `fixed_table_a2.json`(sha `f7754a69…`)과 **모든 행·모든 필드가 일치(차이 0)** |
| 고정 표로 본 규칙 결과 | 재현에서도 6.2와 6.3 모두 `not_failed`로 같음 |

### 고정 표 재계산 방법
- `fixed_table.py`(sha `61341a66…`)는 읽기 전용으로 import했습니다. 그 함수들을 `build()`와 같은 순서로 다시 불렀고, 입력 경로만 인자로 바꿨습니다(원 스크립트에는 입력 경로가 모듈 상수로 박혀 있습니다).
- 이 방법이 믿을 만한지 대조군으로 확인했습니다. 같은 방식으로 원본 입력을 넣어 다시 만든 표가 `fixed_table_a2.json`과 차이 0이었습니다.
- 재현 D 24줄의 ③ rev 7 조건값은 b46bdf8f의 `jp3_rev7_condition.build_report`를 재현 출력에 돌려서 얻었습니다(결과 pass, breach 읽기 0).
  - 고정 표는 원래 `condition_ad7a716e.json`을 읽었습니다.
  - ad7a716e와 b46bdf8f 사이에 `jp3_rev7_condition.py`의 차이는 없습니다(`git diff --stat` 확인).
- 비교에서 뺀 최상위 키는 `inputs`와 `code_identity` 둘뿐입니다(입력 경로와 체크아웃 정보라 구조상 다를 수밖에 없음).

### 산출물
근거 폴더: `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\repro_a2_b46bdf8f\`
- `repro_compare.py`(sha `c5159494…`)
- `compare_result.json`
- `condition_repro.json`
- `fixed_table_repro_a2.json`
- `manifest.json`: 입력 sha 전부, worktree 실행 전후 상태(HEAD b46bdf8f, clean, ignored 포함 status까지 같음)
- `SHA256SUMS`: 5항목, sha `7a371765…`

재현 출력 폴더: `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\b46bdf8f\repro_a2\SHA256SUMS`
- `write-sums --recursive`로 만들었습니다. 117항목(파일 3개 + T4h npz 114개), sha `4a4fc7c0…`
- 재현 jsonl sha256은 `d60306db8073b3ffba285f58e54d8fd9779867d47c4e79e9878d02974f082430`입니다.

### 실행 정보
- 실행: dynamics-dev `python.exe -I -B`, `MKL_THREADING_LAYER=TBB`, 작업 폴더는 worktree 루트.
- 첫 실행은 종료 3(도구 오류)이었습니다. `importlib`로 불러온 모듈을 `sys.modules`에 등록하지 않아 dataclass가 만들어질 때 멈췄습니다. 등록하도록 고친 뒤 다시 돌렸고, 첫 실행에서 쓰인 출력은 없었습니다.
- 정적 점검: ruff에서 BLE001 1건이 나왔습니다. 예상 밖 예외를 모두 종료 3으로 내려는 의도된 코드입니다. codespell은 0건입니다.
- 코드 커밋이나 worktree 수정은 하지 않았습니다. 블라인드 경로에는 접근하지 않았습니다.

### 확인 필요
- 고정 표 스크립트는 명세 sha `ebb79469…`(개정 5)를 고정 입력으로 박아 두었습니다. 지금 작업본 명세 sha는 `788f6014…`입니다. 그래서 이번 대조에서는 명세 sha를 대조하지 않고 기록만 했습니다(`manifest.json`). 앞선 몫 판단 보고에서 적은 "지시된 `6dcccae2…`와 작업본이 다르다"는 문제와 같은 건입니다.

### 앞선 몫 판단 보고(B-2) 요약
이미 보고한 내용이고, 이번 작업으로 바뀐 것은 없습니다.
- 네 요소(A_i, A_ib, A_ii, B3)가 모두 남습니다.
- 팔 2(a2) VBM5 기준 발동 수: B3 140, A_i 269, A_ib 577, A_ii 616
- V0 대비 실패 단위: a2 3, a5 36, a6 5, a1 10
- 근거 폴더: `ed7_design\share_b46bdf8f\`(SHA256SUMS sha `8e9a8823…`)

사용한 스킬: 없음
