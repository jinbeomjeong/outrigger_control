# 436.9 판 8 D-1: J-P3 판정 설정 이름 목록을 규칙 원문으로 확정 (control-expert, 2026-11-27)

의존성 점검: 생략했습니다. 이번 과제에는 제어 수치 계산이 없고, dynamics-dev는 import 확인 스크립트를 1회 돌리는 데만 썼습니다. 수치를 Python과 Julia로 비교할 대상이 없어 Julia 교차 검증도 해당 없습니다.

## 0. 결론
- **판 8에서 J-P3로 판정하는 설정은 10개입니다**: VBN, LSN1~4, VBNslow, VBNfast, VBNc005, VBNc04, VBKN. 판 7 꼴과 같습니다.
- **판정 대상이 아닌 설정**
  - VBN0·VBKN0: ③을 끈 설정입니다.
  - VBNb069·b16·h05·h15·d05·d15: C-S 기록 6설정입니다.
- **수정의 성격은 구현 결함입니다**(도구가 봉인 규칙을 따라가지 못함). 판정 집합은 봉인 문면 3.6·5.1·5.2·9절에 다 있으므로 정오는 필요 없습니다. 판정 정의는 바뀌지 않고, 경로 2에 넘길 [정의] 문장도 바뀌지 않습니다. 대신 해석·구현 결정문 초안 1건을 냈습니다(봉인 안 함, 3절).
- **새로 확인한 제약(중요)**: 공용 모듈 `j_p3_inputs.py`는 **C8 실행 경로 모듈**입니다.
  - 근거: `05_tests/data/ed8_run_path_modules_56849248.json:513`. `harness_hydraulics.py:59`가 이 모듈을 import합니다.
  - 규칙 11.2와 P8-11은 T8 계열 커밋에서 실행 경로 모듈이 C8과 바이트 같기를 요구합니다. 그래서 T8‴에서 이 파일을 고칠 수 없습니다. 고치면 `test_ed8_run_path.py:76-85`가 실패하고, C8 교체(사용자 승인, 1단계부터 다시)가 필요해집니다.
  - 따라서 수정 위치는 **판 8 판정 도구 안에서만 켜지는 범위 한정 덮어쓰기**입니다(4절).
- **같은 계열 결함 2건을 더 찾았습니다**
  - **D-1b(잠재)**: `j_p3_inputs.P3_OFF_SETTINGS`(`:39`)에 VBN0·VBKN0이 없습니다. ③-off 태그를 단 VBN0 줄도 J-P3 기대 줄이 되고, 규칙 키가 없으니 `rule_missing`으로 setting_defect가 됩니다(합성 확인 2절). 호출 지점을 대조한 결과, 판 8 경로 1 명령 가운데 VBN0·VBKN0 줄을 `jp3_of`에 넘기는 곳은 없습니다. 그래서 지금 판정에는 닿지 않습니다.
  - **D-1c(`_check_lines`, 조용한 누락, 코드 읽기로 확인)**: 12a(`t12 --bundle VBN`)에서 VBN 줄의 "J-P3 줄 P4 증거" 검사(`jp3_tjr_judge.py:680-684`)를 건너뜁니다. 판 7에서는 VBM이 튜플에 있어 이 검사를 했습니다.

## 1. 판 8 J-P3 판정 대상 목록 (봉인본 sha256 `35f9eba8…121520`, `.sha256` 파일과 일치 확인, 커밋 2715230e)

| 설정 | 판정되는 곳 | 규칙 근거(줄) |
|---|---|---|
| VBN | C-J (iii), C-D, C-G, P8-2, G′, 12a | 3.6:154("판 8 판정"), 5.1:218·220·221, 5.2:232·234·235, 7.1:282, 7.6:319, 8:324, 9:331-332, 12 P8-2:363 |
| LSN1~4 | C-J (iii), P8-2 | 3.6:154, 5.1:218, 5.2:232, 9:332, 12:363 |
| VBNslow | C-S, C-D(24줄 J-P3a 관문. V0 비교만 기록) | 3.6:156, 5.1:219·220, 5.2:233·234, 9:332("C-D 24"), 부록 A:450 |
| VBNfast·VBNc005·VBNc04 | C-S | 3.6:156("slow·fast·c005·c04 판정"), 5.1:219, 5.2:233, 9:332("C-S 판정 4설정 184"), A:450 |
| VBKN | 12b·T-JR-12b | 3.6:157, 8:325, 9:332 |

- VBKN의 J-P3는 12b 도구가 자기 경로로 판정합니다. `jp3_12b_judge.py`는 `j_p3_inputs`에서 `has_judged_breach`만 씁니다(:907).
- 그래도 판 6 VBKL·판 7 VBKM처럼 공용 판정 튜플에 넣어 둡니다(대칭). 판 8 경로 1 명령 가운데 VBKN 줄을 `jp3_of`에 넘기는 곳은 없습니다.

| 대상 아님 | 이유 | 근거 |
|---|---|---|
| VBN0 | ③ 끔. T8 P8-1 해시 짝, 12a 기준 팔 | 3.6:155, 8:324, 12 P8-1:362, A:451 |
| VBKN0 | ③ 끔. 12b 기준 팔·P-pred 입력 바닥 | 3.6:157, 8:325 |
| VBNb069·b16·h05·h15·d05·d15 | C-S 기록 설정. ③은 켜져 있지만 J-P3 판정 집합 밖 | 3.6:156, 5.2:233("기록 6설정은 기록"), 9:332, 10:344 |

- 판 7 대조: 판 7 3.6 표(v7 521-525행)와 6.2(678행)의 판정 4설정, 도구 `ED7_JUDGED_SETTINGS`(`j_p3_inputs.py:62-66`, 기록 6설정 제외)와 같은 꼴입니다. 부록 A:450 "이름만 VBN<key>"로 옮기면 위 목록이 됩니다.
- run_v5 대조(C8과 같은 `run_v5.py:294-310`): `ED8_SETTINGS` 18개 = 판정 10 + ③ 끔 2 + 기록 6으로 빠짐없이 나뉩니다. 판정 10 = `ED8_JUDGED_SETTINGS` + VBKN + `ED8_SENSITIVITY_SETTINGS`입니다(합성 확인 `proposed_equals_rule_sets` true).
- 개정·정오·해석 결정문 대조
  - `audit_prerun\control_nb1_decision.md`·`control_nb1_followup.md`: J-P3 설정 집합을 바꾸는 문장이 없습니다. nb1_decision:92는 "J-P3는 A/A 표에서 뺀다, G′ 7.6에서 VBN 줄 단위"입니다.
  - `spec_drafts\` rev0~rev2c의 3.6 표·경로 2 범위 문장: 봉인본과 같습니다.

## 2. 도구 대조 (ed8-judge2 HEAD 5955f25b, 읽기·import만)

| 위치 | 현재 | 영향 |
|---|---|---|
| `j_p3_inputs.py:67-68` `REV5_JUDGED_SETTINGS` | 판 8 이름 0개 | `_revision_5_judgement`(:253-259)에서 판 8 줄이 모두 `others`로 가서 `no_judged_runs`가 됩니다. 이어서 `jp3_ed7_judge.jp3_basis`(:476-477)가 "J-P3 0 judged rows"를 냅니다(D-1) |
| `j_p3_inputs.py:39` `P3_OFF_SETTINGS` | VBN0·VBKN0 없음 | `is_p3_expected`(:143-151): ③-off 태그 → 설정 접두 "VB" → 기대 줄 → 규칙 키 없음 → `rule_missing` setting_defect(D-1b, 잠재) |
| `jp3_tjr_judge.py:197` `from j_p3_inputs import REV5_JUDGED_SETTINGS` | 같은 튜플 객체에 묶인 이름. **`j_p3_inputs`만 고치면 바뀌지 않습니다** | `_check_lines`:680에서 VBN 줄의 판정 줄 증거 검사를 건너뜁니다(D-1c). :676의 줄 증거 검사는 `jp3_tjr_judge_ed7.py:156`이 `ED6_LINE_SETTINGS`에 VBN·VBN0를 더해 줘서 됩니다(`jp3_tjr_judge_ed8.py:40-44` → `edition_7`) |
| `jp3_ed8_judge.py:282-295` `jp3_of` | `ed7.jp3_of_rows`(`jp3_ed7_judge.py:485-488`) → `jp3_j9main_judge.j_p3_rows`(:275-299, `is_p3_expected` :292) → `j_p3_over_rows` | 호출 지점: C-J :525, C-S :608(판정 줄만, 기록 설정 제외), C-D :681(VBN+VBNslow), C-G :695, G′ :1246, cases :1286(`CASE_ROWS` 10 검사 :1290). 모두 같은 함수라 덮어쓰기 하나로 다 고쳐집니다 |
| 12b(`jp3_12b_judge_ed8/ed7/…`) | 공용 튜플 안 씀 | 영향 없음 |
| gate(`jp3_ed8_gate_judge.py`) | J-P3 안 씀 | 영향 없음 |
| `jp3_rev7_condition.py` | 판정 플랜트를 이름이 아니라 `p1_patch`로 판별(:78) | 영향 없음 |
| `ed7.d_lines_of`(C-D J-P3a 읽기) | `extend_bound_check`를 직접 읽음(:1095-1107). 이름 튜플 없음 | 영향 없음 |

- 합성 확인(값 없는 가짜 줄, 실행 출력 안 읽음): `d1_tuple_probe.py` → `d1_tuple_probe.out.json`, dynamics-dev `conda run … python -I -B`, 종료 0.
  - 지금: cases 꼴 10줄 판정 0(`no_judged_runs`), C-S 4 → 0, C-D 24 → 0, VBN0·VBKN0 ③-off 태그 `is_p3_expected` 참.
  - 덮어쓰기 안: 판정 10 / 4 / 24, 기록 6 → 0(그대로), VBN0·VBKN0 기대 아님, tjr 바인딩에 VBN 있음·VBN0 없음.
  - 나온 뒤: 원래 튜플로 돌아옴, 판 7 이름 판정 10 그대로.
  - 판 8 이름은 이전 판 튜플 어디에도 없습니다(`ed8_names_absent_from_older_tuples` true). 3.6:159에 따르면 이전 판 입력에는 VBN 계열 줄이 없습니다. 그래서 판 8 문맥 안에서도 판 6·7 입력의 결과는 같고, 판 8 문맥 밖에서는 값 자체가 C8 값입니다.
- 시험이 못 잡은 이유: `test_ed8_judge.py:694`가 `jp3_of`를 통째로 스텁합니다.
- 다른 이름 튜플 훑기(감사 참고): `T8_JUDGED_SETTINGS`·`T8_P4_SETTINGS`·`T_JR_15_JUDGED_SETTINGS`·`JP3_LINE_SETTINGS`(판 4a·436.9), `jp3_baseline_compare.JUDGED_SETTINGS`(판 4a), `jp3_ed7_judge`의 `D_COUNTED_SETTING`·`PROBE_*_PLANTS`·`SETTING_MAP_ED7`·`L1_RUNS`(판 7 전용 함수).
  - 판 8 `cd_stage`는 "VBN"을 스스로 거르고, 판 8에는 자기 `L1_RUNS`가 있습니다.
  - 제가 읽은 호출 지점에서는 판 8 경로가 이 튜플들을 쓰지 않았습니다. 다만 전수 추적은 아니므로 재감사 몫으로 남깁니다.
- 관찰(결함 아님): 판 7 감도 단계는 기록 설정 J-P3를 `J-P3_record_settings`로 남겼습니다(test_ed7_judge.py:852-855). 판 8 `cs_stage`는 판정 줄만 넘기고 그 기록이 없습니다. 판 8 규칙 5.2:238의 census 보고 항목에 이것이 없으므로 고치지 않습니다.

## 3. 수정 성격 판단과 결정문 초안
- **구현 결함입니다. 정오는 필요 없습니다.**
  - 판정 집합은 3.6 표의 "쓰임" 칸, 5.1·5.2, 9:332에 정해져 있습니다.
  - 16절 Y8-2의 설정 목록 지시(ALL_SETTINGS·T4H_SETTINGS·ROD_FAULT_SETTINGS)에 J-P3 판정 튜플이 빠진 것은 구현 과제 목록의 누락이지 판정 정의의 누락이 아닙니다.
- 판 7 9절과 대조했습니다. 줄 수·키·상태 순서·"판정 행 0 = 판정 불가"가 모두 바뀌지 않으므로 경로 2 넘김(9:332-334)에 더할 [정의] 문장은 없습니다.
- T8″의 not_judgeable은 10:346대로의 판정 불가였고, 통과로 읽힌 적은 없습니다.
- 결정문 초안: `d1_decision_draft.txt`(아래 경로). 내용은 다음 여섯 가지입니다. 봉인은 하지 않았습니다.
  1. 판정 10설정
  2. 대상 아님 8설정
  3. 구현 위치(실행 경로 제약 때문에 판정 도구 쪽 덮어쓰기)
  4. 판정 정의·경로 2 무변경
  5. 11.2 단일 T8‴
  6. 판정서 공개 문구(D-1·D-1b, 판정 값 보기 전 수정)

## 4. python-expert 구현 명세 (T8‴ = ed8-judge2 5955f25b의 자식, C8 불변)

### 바꿀 파일 (이 두 파일과 새 시험만)
1. `04_scripts/04_hydraulic/coupled/jp3_ed8_judge.py`
   - 상수 둘을 더합니다(docstring에 규칙 줄 인용: 3.6:154-157, 5.1, 5.2, 9:332).
     - `ED8_JP3_JUDGED_SETTINGS = ("VBN", "LSN1", "LSN2", "LSN3", "LSN4", "VBKN", "VBNslow", "VBNfast", "VBNc005", "VBNc04")`
     - `ED8_P3_OFF_SETTINGS = ("VBN0", "VBKN0")`
   - `ed8_jp3_settings()` contextmanager를 더합니다.
     - `j_p3_inputs.REV5_JUDGED_SETTINGS`와 `j_p3_inputs.P3_OFF_SETTINGS`를 저장한 뒤 원래 값 + 판 8 이름(중복 없이 뒤에 붙임)으로 바꿉니다.
     - `finally`에서 원래 **객체**로 되돌립니다.
   - `jp3_of`: `ed7.jp3_of_rows(rows, folders)` 호출을 `with ed8_jp3_settings():` 안에서 합니다.
   - (선택, 기록) 반환 dict에 `"J-P3_judged_settings": list(ED8_JP3_JUDGED_SETTINGS)`를 더합니다. 상태 계산은 이 값을 읽지 않습니다.
2. `04_scripts/04_hydraulic/coupled/jp3_tjr_judge_ed8.py` `edition_8()`
   - `ed8.ed8_jp3_settings()`에 들어갑니다.
   - 추가로 `tjr7.tjr.REV5_JUDGED_SETTINGS`(= `jp3_tjr_judge` 모듈의 import 바인딩)를 덮어쓴 `j_p3_inputs.REV5_JUDGED_SETTINGS`로 바꾸고, 원래 바인딩을 저장했다가 되돌립니다.
   - 순서: 기존 `ed8_identity` 안쪽이든 바깥쪽이든 되돌림이 모두 `finally`에 있으면 됩니다.

### 하지 말 것
- `j_p3_inputs.py`를 고치지 않습니다(C8 실행 경로 모듈, json:513. 고치면 P8-11 실패 → C8 교체).
- `jp3_tjr_judge.py`, `jp3_ed7_judge.py`, `jp3_j9main_judge.py`, `jp3_ed6_judge.py`, `jp3_12b_judge*.py`, `jp3_ed8_gate_judge.py`, `jp3_ed8_rules.py`, `run_v5.py`, `03_src`는 바이트 그대로 둡니다. 이전 판 재현이 바뀌지 않게 하고, 다른 관문 로직도 바꾸지 않습니다.
- 판 8 문맥을 모듈 import 때 켜지 않습니다. 함수 호출 범위 안에서만 켭니다.
- 블라인드 출력(`j9_runs\56849248\impl_*_a1\`, `l1ref_a1\`)을 시험 자료로 쓰지 않습니다. 같은 job을 생산자로 다시 돌려 블라인드 값을 재생성하는 것도 하지 않습니다.

### 시험 (새 파일 예: `05_tests/unit/test_ed8_jp3_settings.py`)
- **T-a 규칙·run_v5 대조**
  - `set(ED8_JP3_JUDGED_SETTINGS) == set(run_v5.ED8_JUDGED_SETTINGS) | {"VBKN"} | set(run_v5.ED8_SENSITIVITY_SETTINGS)`
  - 판정 10과 `ED8_SENSITIVITY_RECORD_SETTINGS`, `ED8_P3_OFF_SETTINGS`가 서로 겹치지 않습니다.
  - 셋의 합집합이 `set(run_v5.ED8_SETTINGS)`(18개)입니다.
  - 판정·기록 이름은 `run_v5.ED8_SETTINGS[n][1].get("extend_start_rev7") is True`이고, ③ 끔 이름은 그 키가 없습니다.
- **T-b 덮어쓰기 의미와 복원**
  - 문맥 안: `is_p3_expected(ED8_P3_OFF_TAG, "VBN0"/"VBKN0")`는 거짓, `is_p3_expected(ED8_TAG, 판정 10)`은 참입니다.
  - 문맥 밖: 두 튜플이 C8 값과 같습니다(`git show 56849248:04_scripts/04_hydraulic/coupled/j_p3_inputs.py`에서 파싱하거나 리터럴로 비교). `jp3_tjr_judge.REV5_JUDGED_SETTINGS is j_p3_inputs.REV5_JUDGED_SETTINGS`입니다.
  - 문맥 안에서 예외가 나도 복원됩니다.
- **T-c 생산자 꼴 줄로 `jp3_of` 판정 행 수 단언**
  - `jp3_of` / `ed7.jp3_of_rows` / `j_p3_rows` / `j_p3_over_rows` / `j_p3_judgement_rev5`는 **스텁하지 않습니다**.
  - 줄 구성
    - job은 `run_v5.ed8_batch_jobs(run_v5.ED8_CASES_BATCH)`(10개)입니다.
    - `controller_tag`는 `ED8_TAG`입니다.
    - `hydraulics_record.extend_bound_check`는 03_src ③ rev 7 코드가 만든 기록(rule_revision 7, spec_edition 10902ffd)이거나, 이미 본 판 7 VBM 저장 줄의 기록을 그대로 복사한 것입니다.
    - `head_only_declared` 거짓, `event_output` 비어 있지 않음.
  - 스텁은 T4h 읽기 둘만 허용합니다: `judge_stage1_4368.rod_reading` → 참, `jp3_ed7_judge.condition_judgement` → pass 요약. 사유를 주석으로 남깁니다.
  - 단언
    - `ed8.jp3_of(lines, ())["J-P3_judged_rows"] == 10`
    - basis에 "J-P3 0 judged rows"·"J-P3 no_judged_runs"가 없음
    - **회귀 감시**: 같은 줄을 문맥 밖 `ed7.jp3_judged_rows(ed7.jp3_of_rows(lines, ()))`로 세면 0. T8″에서 이 시험이 실패해야 합니다.
  - 매개변수 사례
    - C-S 판정 4설정 각 1줄 → 4
    - C-D VBN 12 + VBNslow 12 → 24
    - 기록 6설정 → 판정 0, `rev7_unjudged_setting_runs` 6, setting_defect 없음
    - cases 10줄 + VBN0 줄 1(③-off 태그, ③ 기록·규칙 키 없음) → 판정 10, `runs_expected` 10, `rule_missing_runs` 0
- **T-d 12a `_check_lines`**
  - `jp3_tjr_judge_ed8.edition_8()` 안에서 `tjr.REV5_JUDGED_SETTINGS`에 VBN이 있고 VBN0이 없습니다.
  - 판정 줄 증거가 모자란 VBN new 줄 → `_check_lines`가 `compare.judged_line_evidence_problems`의 setting_defect 문구를 더합니다(그 문구만 단언하고, `_dg3_identity` 문구는 따로 둡니다).
  - 같은 호출을 판 8 문맥 밖에서 하면 그 문구가 없습니다(T8″의 조용한 누락 재현).
- **T-e 이전 판 불변**
  - `git diff --name-only 5955f25b HEAD`가 {`jp3_ed8_judge.py`, `jp3_tjr_judge_ed8.py`, `05_tests/…`}의 부분집합입니다.
  - 기존 `test_ed8_run_path.py` 4개가 통과합니다(C8 바이트).
  - `ed8_jp3_settings`를 쓰는 곳은 판 8 두 모듈과 시험뿐입니다(정적 검사).
  - 판 6·7 진입 모듈(`jp3_ed6_judge`, `jp3_ed7_judge`, `jp3_tjr_judge_ed7`, `jp3_12b_judge_ed7`, `jp3_j9main_judge`)은 `jp3_ed8_judge`를 import하지 않습니다(정적 import 검사).
- **T-f CWD 분리**
  - 새 시험을 cwd = ed8-judge2 루트와 cwd = 저장소 밖 임시 폴더에서 각각 절대 경로로 돌려(`-p no:cacheprovider`) 둘 다 통과해야 합니다.
  - 끝난 뒤 `git status --porcelain --ignored`가 빈 출력이어야 합니다.
- **P8-4 방침**: T8″ 기준 대비 전체 단위 시험에서 새 실패·새 건너뜀이 0이어야 합니다. 새 시험 수를 보고합니다.

## 5. 공개 항목 (읽은 파일·검색 범위)
- **Read**
  - `stage4_prejudge\prejudge_report.md`(전체)
  - 봉인 규칙 `jp3_remedy_spec_v8_rules.md`(전체, 1~459행), `.sha256`
  - `jp3_remedy_spec_v7.md` 493~532·654~773행(+ Grep 절 제목·"J-P3")
- **ed8-judge2 Read**
  - `j_p3_inputs.py` 1~300, `run_v5.py` 200~329
  - `jp3_ed8_judge.py` 1~330·480~704·1195~1304
  - `jp3_ed7_judge.py` 440~519·1060~1108
  - `jp3_j9main_judge.py` 270~329
  - `jp3_tjr_judge.py` 190~269·640~699(+ `_dg3_j_p3` 836~881)
  - `jp3_tjr_judge_ed7.py`·`jp3_tjr_judge_ed8.py`(전체)
  - `jp3_baseline_compare.py` 1005~1079
  - `test_ed8_run_path.py`(전체), `test_ed6_judges.py` 185~209, `test_ed7_judge.py` 835~862
- **ed8-judge2 Grep(단일 파일)**: `v5_options.py`, `jp3_rev7_condition.py`, `harness_hydraulics.py`, `ed8_run_path_modules_56849248.json`, `jp3_j9main_judge.py`, `jp3_ed7_judge.py`
- **Grep 폴더**
  - ed8-judge2 `04_scripts\04_hydraulic\coupled`(glob `*.py`·지정 모듈 이름 brace glob, 여러 번)
  - `05_tests`·`05_tests\unit`(glob `*.py`·`test_ed8*.py`)
  - `03_src`(glob `*.py`)
  - `ed8_design\audit_prerun`(glob `*.md`·`control_nb1_*.md`)
  - `ed8_design\spec_drafts`(glob 없음. 블라인드를 품지 않는 초안 폴더)
- **규칙 위반 공개 2건**
  - (1) 첫 호출 Glob이 `path` = `…\j_p3_cause`(블라인드를 품은 상위 폴더), 패턴 `jp3_remedy_spec_v8_rules*`였습니다. blind_guard 훅이 막아 출력은 없었습니다.
  - (2) Grep 1회의 `path`로 **worktree 루트** `C:\workspace\outrigger_control\.claude\worktrees\ed8-judge2`를 썼습니다(glob `{03_src,04_scripts,05_tests}/**/*.py`, 파일 목록 모드, 패턴 `j_p3_inputs`). 결과는 "No files found"였고 블라인드 이름·건수 노출은 없습니다. 블라인드 사본을 품을 수 있는 루트를 범위로 쓴 규칙 위반입니다.
- **블라인드**: `j9_runs\56849248\impl_*_a1\`, `l1ref_a1\`와 worktree 사본은 Read·Grep·Glob·목록 어디에도 쓰지 않았습니다. `stage4_prejudge\`의 수치 결과 파일은 열지 않았습니다(보고서 md만).
- 판정 도구는 돌리지 않았습니다. 판정 모듈은 합성 확인 스크립트 안에서 import만 했습니다(`j_p3_inputs`, `jp3_tjr_judge`, `run_v5`). 메모리 안 덮어쓰기는 복원을 확인했고(`restored` true), 파일은 바꾸지 않았습니다.
- ed8-judge2 `git status --porcelain --ignored`는 작업 뒤 빈 출력, HEAD 5955f25b입니다.
- 규칙 파일·ed8-impl·ed8-judge2는 고치지 않았습니다.
- 셸 명령은 PowerShell만 썼고 Bash·파이프는 쓰지 않았습니다. 프로세스를 종료하지 않았습니다. scratchpad 하위 `control-d1\`은 지웠습니다.
- **산출물**(`C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\control_d1_settings\`)

| 파일 | sha256 |
|---|---|
| `d1_settings.json`(목록·근거·도구 대조·제약) | `c4838c47592a0bbc6bd932bf0494a5e82e9aaf739418e8ff4a5896f6473ffe09` |
| `d1_decision_draft.txt`(해석·구현 결정문 초안) | `4cf82f2cd8e84a981b95cce1336c895c2a853345e8ea94dabd0a0b3a62420b68` |
| `d1_tuple_probe.py` | `c78b72daf1aa9a3173807987e17556d55fd2c94e9ce21626a3be5b60fc092262` |
| `d1_tuple_probe.out.json` | `084582ecdb1db1317e1e7deb8ecee846e29d4f46d16fcd588f17696f6fd25629` |

  - 폴더 SUMS는 쓰지 않았습니다(메인이 이 md 저장 뒤 씁니다).
- 요청 범위 밖 추가: D-1b(③-off 목록)와 D-1c(12a `_check_lines`)를 같은 결함 계열로 명세에 넣었습니다. 새 판정 규칙은 없습니다.

## 6. 확인 필요 질문
1. **D-1b(VBN0·VBKN0을 ③-off 목록에)도 T8‴에 넣을까요?**
   - 추천: 넣습니다.
   - 판정 결과에는 영향이 없습니다(판 8 경로 1에서 닿지 않음).
   - 판 6 VBL0·VBKL0, 판 7 VBM0·VBKM0과 대칭이고, `jp3_of`를 VBN0 줄에 부르면 setting_defect가 되는 함정을 없앱니다(prejudge 스모크 t8 VBN0에서 실제로 났습니다).
2. **결정문 처리**
   - 추천: 정오로 봉인하지 않고, 결정문을 T8‴ 근거와 판정서 공개 항목으로 둡니다. 판정 정의가 바뀌지 않기 때문입니다.
   - 정오를 원하시면 `d1_decision_draft.txt`를 정오 문안으로 바꿔 드리겠습니다.

## 7. 위임·핸드오프
- **python-expert**: 4절 구현(T8‴). 커밋 해시는 메인이 고정합니다.
- **verif-protocol-auditor**: T8‴ 재감사를 맡깁니다.
  - 판 8 이름이 빠진 이름 튜플을 전수 검색합니다: `*_JUDGED_SETTINGS`, `*_LINE_SETTINGS`, `P3_OFF_SETTINGS`, `from … import <TUPLE>` 바인딩.
  - 덮어쓰기가 판 8 문맥에서만 켜지는지 봅니다.
  - `j_p3_inputs.py` 등 실행 경로 바이트가 C8과 같은지 봅니다(P8-11).
  - 블라인드 권한이 있는 쪽에서 cases 판정 행 수(10)만 보는 스모크를 판정 값 없이 합니다.
  - 경로 2 도구도 9:332 판정 집합(판 8 10설정)을 그대로 쓰는지 확인합니다. 저는 경로 2 도구를 열지 않았습니다.

메모리 반영: `judged-tuple-in-run-path-module.md`를 더하고 MEMORY.md 색인 1줄을 더했습니다. 새 판 설정 이름이 공용 튜플에 빠지는 함정, 실행 경로 모듈 제약, import 바인딩에 관한 내용입니다.

사용한 스킬: 없음
