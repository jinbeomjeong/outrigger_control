## 감사 요약(짧은 재감사)
- 대상·시점·기준 문서: [시점] 실행 전, 판 6 J-P3 재감사.
  - 정오 3 `06_analysis/02_control/j_p3_cause/jp3_remedy_spec_v6_erratum3.md`(bae389a3, `.sha256` dc2a4c40)
  - 봉인본 07a55e17, 정오 1 1d4f7539, 정오 2 20a60e57
  - 새 실행 커밋 79495405(aa3e6c4a의 자식 1커밋, `03_src` tree f6bb6033 = ac3c25a7)
  - worktree `C:\workspace\outrigger_control\.claude\worktrees\ed6-run6`: HEAD 79495405, 깨끗함, locked
- 본 결과: 판 6 결과는 없다. 판정값은 보지 않았다. 키 파일은 R15 줄 수만 셌다.
- **판정: 차단 0 / 실행 전 수정 1 / 기록 3**. 정오 3의 세 항목이 도구에 맞게 반영됐다. 앞 감사의 실행 전 수정 1~3과 기록 4·9도 반영됐다. 실행 전 수정 1(새 실행 커밋에서 P6-4 확인과 근거 커밋)만 처리하면 실행해도 된다.

## 반영 확인(앞 감사 → 79495405)

| 앞 감사 | 반영 | 근거 |
|---|---|---|
| 실행 전 수정 1: suite_aa3e6c4a 미추적 | 스테이징됨(A). 커밋되면 닫힘 | `git status`: 11파일 A. `baseline_check sums`: 오류 0 |
| 실행 전 수정 2: 격자 FAULT 키 결측이 통과로 읽힘 | 반영 | `jp3_ed6_judge.py` `GRID_REQUIRED_KEYS`(다섯 키 = 정오 3 3-2). `judge_grid`에서 `matched_lines` 바로 뒤, FAULT 읽기 전에 `grid_key_problems`를 돌려 NotJudgeable(종료 2). `missing_keys`는 None을 "있음"으로 센다(3-2 셋째 줄과 같음) |
| 실행 전 수정 3: sens R15 나빠짐 | 반영 | `sens_r15_worsening`: `_j2_value_N`과 `phase_scatter(off=V0, on=설정)`을 쓰고, worse = 구분됨 그리고 E < 0. **`Path(keys_path).name == "sens_keys_v2.json"`일 때만 돈다(정오 3 9항)**. 실패는 failures(종료 1)이고 사유에 설정·S·E·값을 적는다. 군집 규칙 밖이고 `weak_basis`를 기록한다. 줄 결측·None은 not_judgeable. 상태 순서는 바뀌지 않았다 |
| 기록 4: KEY_PRESENCE 12b 배열 | 반영(단일 출처) | `tuple(dict.fromkeys(("t_s", *judge12b.T4H_ARRAYS, *judge12b.T4H_REV6_ARRAYS)))`에 `jp3_r59_end_guard_substeps`가 들어간다. `grid_rows`는 `GRID_REQUIRED_KEYS` + warnings로 바뀌었다(`gates` → `gates.fault0`이고, 상위 키를 포함한다) |
| 기록 9: 고정 목록 커밋 시점 문구 | 반영 | `common_ed6.ps1` 21~25행, `prelaunch_ed6.ps1` 3~8행: "commits it before step 5 v0d0" |

## 확인한 사실
- 정오 3 9항(범위)
  - R15 줄 수: `sens_keys_v2.json` 8줄(4설정 × 2위상), `confirm_a_keys_v2.json` 0, `confirm_b_grid192.json` 0(key_presence `--where job.case=R15`, 값 비출력).
  - 그래서 키 파일 이름으로 범위를 거는 것이 정오 3 문면과 같다.
- 기존 sens 시험의 의미
  - `test_ed6_judges.py`의 `sens_judge` 고정틀은 `sens_r15_worsening`을 "위상 산포 안 / worse False"로 바꿔 끼울 뿐이다.
  - `test_sens_probe_units_stop_and_cluster_rule`의 판정 경로(멈춤·군집)는 바뀌지 않았다.
  - 새 `test_sens_r15_worsening_in_the_status`는 한 설정만 사유에 남는 경우와 판정 불가가 통과가 아닌 경우를 덮는다.
  - `test_ed6_erratum3.py` 8건은 정오 3 3-1 시험 목록 6종과 3-3을 덮는다. 3-2 시험 5건은 `test_ed6_judges.py`에 있고 키 하나씩 빼는 방식이다.
  - `junit_subset_79495405.xml`: 1,056 중 1,034 통과, 실패 0, skip 22. skip은 모두 저장 자료 시험이다. `--critical "test_ed6_(erratum3|judges)"`로 critical_skipped 0이다. 새 시험 이름은 subset에 모두 있다.
  - `junit_worktree_tests_79495405.xml`: 293 통과, skip 0.
- 정오 3 3-1 사전 예측 재계산
  - 정오 3 표의 값으로 다시 셌다: S = 0.5 kN, E = (8.73 + 2.05)/2 − (−0.22 − 0.72)/2 = +5.86 kN. v05는 +5.865 kN이다.
  - 위상마다 차의 부호가 같으므로 "구분됨, 나아짐"이다. 표와 같다.
  - `phase_scatter`(judge_stage1_4368.py:533~550)가 정오 3 4항 정의(|E| > S, 위상차 모두 0이 아님, 부호 같음)와 같다.
- 고정 목록: `fixed_inputs_entries_ed6.txt`에 정오 3 md와 `.sha256` 두 줄이 더해졌다. 목록 도구가 sidecar 일치를 검사한다.
- 실행 설정: `ed6_run_config.json`의 run_commit이 7949540527ba…(전체 sha)이고 placeholder_scan 종료 0이다.
- 건식 근거: `dry_commands_ed6_79495405.json`은 15개 종료 코드가 모두 0이고, 단계 identity_start head가 모두 79495405다.
- 기타 대조
  - merge-base(79495405, master)는 여전히 96dd7bf2다. 그래서 기존 실패 목록 eb108f3d를 다시 써도 정오 2 2-2와 맞다.
  - 정오 3과 md·sha256은 `-text`, LF, BOM 없음, raw 해시 = 봉인 해시다(seal_check 종료 0, 4개 판 모두 raw 일치).
  - `ps1_lint`(16파일)·`placeholder_scan --pattern-set both`(16파일, 허용 2)는 종료 0이다.
  - `baseline_check sums`: `tool_79495405`·`control_v6`·`suite_aa3e6c4a` 모두 0이다.
  - `gate_scan`(jp3_ed6_judge.py)의 경고 5건은 앞 감사와 같은 거짓 양성이다(정체성 단언, s8 기본값, 기록용 경로). 새 함수 `sens_r15_worsening`의 `rows_by.get(setting, [])`는 판정 불가로 가므로 안전하다.

## 발견 사항

**[실행 전 수정][E·T] 1. P6-4(전체 단위 시험)는 새 실행 커밋 79495405에서 아직 판정되지 않았다**
- 근거
  - 정오 1 1-1: "P6-4는 실행 커밋에서 다시 돈다"
  - 정오 2 2-2: 판정은 실행 커밋의 시험
  - 현재 판정 근거 `suite_aa3e6c4a/suite_judgement.json`(status pass)은 aa3e6c4a의 결과다. 79495405 run 쪽은 `~/.claude/runners/outrigger-ed6-suite/run2\`에서 실행 중이다.
- 실패 시나리오: 새 커밋의 판정 도구 변경(jp3_ed6_judge.py가 맨 위에서 `jp3_12b_judge`를 import함)이 전체 시험에서 깨지는 경우를 모른 채 실행에 들어간다.
- 권장 조치(메인)
  - run2의 `suite_judgement.json`이 status pass이고 new_failure·core_not_passing·new_skip_or_xfail가 0인지 확인한다. 그 뒤 근거 폴더(예: `ed6_design/suite_79495405/`)로 옮기고 SHA256SUMS와 함께 커밋한다. 확인 시점은 l1ref 전(늦어도 step5 v0d0 전)이다.
  - 같은 명령에 `--critical`을 넓게 걸어 확인하길 권한다(앞 감사 기록 5). 예: `test_(jp3_|ed6_|run_v5|lock_start_b|c2|extend_start_bound|hydraulics_check_open_delay|hydraulics_v5_options|d0_plant_split|r79_)`.

**[기록][R] 2. 정오 2의 행 번호 인용이 새 실행 커밋에서 낡았다**
- 근거: 정오 2 2-6 "`jp3_ed6_judge.py` 48~52·793~829행"은 aa3e6c4a 기준이다. 79495405에서는 hash-match 함수가 아래로 밀렸다(gate_scan 기준 약 +15행).
- 정오 2 머리의 "실행 커밋 aa3e6c4a" 문장은 정오 3(20~22행: 다시 바뀜, 메인이 sha를 적음)이 대체한다. 모순은 아니다.
- 판정서는 "aa3e6c4a 기준 행"이라고 밝히거나 79495405 행으로 인용한다.

**[기록][R] 3. 정오 3 3-1 7항의 출처 표기 오류**
- 근거: "정오 2 M-9의 줄 누락 규칙"에서 M-9는 봉인 개정 13(봉인 전 감사 M-9, 봉인 6.2·6.3 "줄 누락")의 항목이다. 정오 2에는 없다. 규칙 내용은 같으므로 판정에는 영향이 없다.

**[기록][E] 4. 키 파일 이름 조건 자체를 끝까지 묶는 시험은 없다**
- 근거: `sens_judge` 고정틀은 `sens_r15_worsening`을 늘 바꿔 끼운다. 그래서 `judge_sens`가 confirm_a 키 파일에서 R15 판정을 "not applicable"로 두는지(파일 이름 조건)를 실제 경로로 검사하는 시험은 없다.
- 코드는 jp3_ed6_judge.py `judge_sens` 안의 `if Path(keys_path).name == R15_KEY_FILE else {}`로 단순하다. confirm_a에는 R15 줄이 0이라 결과도 같다. 기록만 한다.

## 모순 점검(정오 3 ↔ 봉인본·정오 1·2)
- 봉인 6.2 "R15는 감도 판정에 기여하지 않는다"를 정오 3은 "군집 규칙의 증거로 세지 않음, 멈춤 조건은 남음"으로 읽고 명시적 우선순위를 둔다. 봉인 6.2의 "probe가 덮는 32단위 … 하나라도 V0 대비 실패하면 멈춘다"와도 맞는다. 모순은 없다.
- 봉인 6.6(key_presence로 판정 불가)과 정오 3 3-2("step 스크립트의 key_presence 호출은 두지 않아도 된다, 도구가 같은 검사")도 모순이 없다. 격자 판정에 한해 6.6을 구현한 것이다. 다른 단계(j9main·sens·cases)는 앞 감사대로 개수 관문·정체성 검사로 결측이 판정 불가 또는 defect로 간다.
- 정오 1 1-1(실행 커밋은 65eba746의 자손, `03_src` = ac3c25a7)을 79495405가 만족한다. 정오 2 2-3 조건 1~2(단계별 정체성, lock)도 유지된다. 조건 3(데이터 입력 고정)에는 정오 3이 더해졌다. 조건 4(실행 커밋 인용)는 판정서 몫이다.
- 경로 2 넘김은 바뀌지 않는다(정오 3 19행). 세 항목 모두 경로 1 도구 몫이라 11절 범위와도 맞는다.

## 확인 필요
- 없음.

## 위임 필요
- 없음. 발견 4의 시험 보강은 선택이다(python-expert, 판정에 필요하지 않음).

## 메인 세션 권고
- run2 P6-4 결과를 확인하고 근거를 커밋한다(발견 1). 이 확인 전에는 l1ref를 시작하지 않길 권한다.
- 지금 스테이징한 정오 3·근거·suite_aa3e6c4a·감사 원문·설정 파일을 커밋한다. 그 뒤 `ref_check`의 `ref_untracked`(감사 원문)가 사라진다. 남는 `ref_missing v5/main.jsonl`은 앞 감사 기록 6·11과 같은 짧은 경로·ignore 파일이다.
  - 감사 원문 `audit_prerun_ed6_aa3e6c4a.md`에는 앞 리포트의 특징 문자열(발견 9, 넓힌 critical, 실행한 검증, 원본 불변 줄)이 모두 있다. 전문이 저장된 것으로 보인다.

## 검사하지 못한 것
- run2(79495405) 전체 시험 결과. 실행 중이라 기다리지 않았다.
- 79495405에서 run_v5 격자 줄의 다섯 키가 실제로 나오는지. 건식 실행이 출력을 만들지 않는다. 결측이면 이제 판정 불가로 멈추므로 안전하다.

## 실행한 검증
- 인터프리터: python-dev `python.exe -I -B`(TBB), PowerShell. 프로젝트 모듈은 import하지 않았다.
- `git diff aa3e6c4a 79495405`(6파일 전부 읽음)
- `seal_check`(4판), `baseline_check sums` 3목록, `ref_check`(정오 3, --rev 79495405), `ps1_lint` 16, `placeholder_scan --pattern-set both` 16, `gate_scan` 1, `junit_skips`(subset·worktree junit), `key_presence`(키 파일 R15 줄 수)
- git: HEAD·status·tree·merge-base·check-attr·ls-files --eol, 건식 json 요약
- 만든 뒤 지운 파일: scratchpad `auditor-ed6rerun\`(guard.json, seal.md, ref.md, gate.md). 폴더째 삭제했다. 실행 뒤 worktree에 미추적 파일 0을 확인했다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v6_erratum3.md bae389a3…, jp3_remedy_spec_v6_erratum3.md.sha256 dc2a4c40…, jp3_remedy_spec_v6.md 07a55e17…, jp3_remedy_spec_v6_erratum1.md 1d4f7539…, jp3_remedy_spec_v6_erratum2.md 20a60e57…, ed6_run_config.json 38bc653a…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
