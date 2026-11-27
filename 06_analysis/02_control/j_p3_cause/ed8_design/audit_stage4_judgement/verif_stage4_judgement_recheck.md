# 판 8(436.9) 4단계 판정서 개정 3 — 판정 후·커밋 전 짧은 재감사(바뀐 부분만)

## 감사 요약
- 본 결과: `j9_runs/56849248/judge_7ea78232/l1ref.json`의 `runs.<stem>.identity_sources` 전체(정체성 값·값 키·줄 수). P8-4 재실행 junit·suite_judgement 건수(시험 이름·상태). `56849248_LOCAL_ONLY.SHA256SUMS` 머리 4줄이 화면에 나왔다(그중 cases 실행 출력 npz 파일 이름 1개, 이 보고에는 옮기지 않음). 메인 transcript의 도구 결과는 앞 300자와 건수만 봤다. P8-2 경로 1의 판정 값은 보지 않았고 옮기지 않았다.
- 대상: `ed8_design/stage4_judgement/stage4_judgement_ed8.md`. 개정 3이고 sha256 `054abafb…`이다(시작할 때와 보고 직전에 다시 재서 같았다).
- 기준 문서: 규칙 v8 `35f9eba8…`, 판 7 정오 1 `74c49bda…`. 둘 다 `.sha256` 첫 토큰과 같고 `i/lf w/lf attr/-text`다. 결정 4단계 `fd79bb76…`, 앞 감사 `1624f762…`.
- 판정: 차단 0 / 커밋 전 수정 4 / 기록 6.
  - B-1은 해소됐다. P8-4 통과 판정은 규칙 364행과 결정 4단계-1의 문면에 맞다.
  - 커밋 전 수정 4건은 모두 문장·절차 수준이다. 판정 결론(4단계 미완, P8-5 판정 불가)은 바뀌지 않는다.
  - 고친 뒤 커밋할 수 있다.

## 발견 사항

### 차단
없음.

### 커밋 전 수정

**[커밋 전 수정][I] M′-1. `stage4_runner/` SUMS는 `--recursive`로 써야 한다. 기본으로 쓰면 logs 19개가 빠진다**
- 근거
  - 판정서 379·405행은 "`stage4_runner/` 21파일, SUMS는 커밋 직전에 씀"이라고 적었고, 쓰는 방법은 적지 않았다.
  - 폴더 구성은 최상위 2개(`run_stage4.ps1`, `steps_stage4.json`)와 하위 폴더 `logs/` 19개다.
  - `baseline_check.py write-sums <stage4_runner> --dry-run`의 결과는 `entries 2, skipped_folders 1`이다. `--recursive --dry-run`의 결과는 `entries 21, skipped_folders 0`이다.
  - 나머지 SUMS 대상 9개 폴더(`stage4_prejudge`·`_t8ppp`·`_t8pppp`, `judge_2263b246`·`judge_7ea78232`·`_identity_checks`, `stage4_judgement`, `audit_t8ppp`, `audit_stage4_judgement`)에는 하위 폴더가 없다.
- 실패 시나리오: 판 7 꼴(최상위만)로 쓰면 4단계 단계별 `.done`·`.log` 19개의 sha가 SUMS에 없다. 그런데도 "러너 사본 sha 고정"으로 읽히게 된다.
- 권장 조치(control-expert 문장, 메인 실행): 7절 405행에 "`stage4_runner/`는 `write-sums --recursive`(21개)"를 더한다. 메인은 그 꼴로 쓴다.

**[커밋 전 수정][R] M′-2. 개정 3의 6.1과 어긋나는 옛 문장 셋이 남았다**
- 근거
  - 0절 52행: "경로 2 넘김 문장(6.1)에서 '사례 E·F'의 정의 문장을 봉인 규칙 v8 안에서 찾지 못했다(확인 필요 A, 8.2)". A는 423행에서 이미 "결정됨"이다.
  - 6절 345·346행: "그래서 경로 2 넘김에 더할 [정의] 문장은 없다". 또 "넘김 범위"에 6.1의 [정의 P8-2-1]·[정의 P8-2-2]가 없다. 그런데 6.1(351-361행)은 이 둘을 넘김 문장으로 고정했다.
  - 9절 429행: "시작 전에 … 확인 필요 A를 닫는다". 이미 닫혔다.
  - 머리말 3행은 "개정 3은 6.1과 8.2 A만 바꿨다"고 적는다. 그래서 위 세 곳이 갱신되지 않았다.
- 실패 시나리오: 메인이 346행 "넘김 범위"만 보고 경로 2 지시문을 만들면 E·F 원문 두 개가 빠진다. 그러면 경로 2가 10줄을 고를 수 없다(8.2 A가 적은 문제가 다시 생김).
- 권장 문장(control-expert)
  - 52행: "… 찾지 못했고, 판 7 정오 1 108행과 v8 363행 원문을 나란히 인용해 6.1에 고정했다(8.2 A 결정됨)".
  - 345행: "판정 정의를 바꾼 [정의] 문장은 없다. 다만 P8-2 사례 정체는 6.1의 원문 인용 둘을 넘긴다".
  - 346행 넘김 범위 끝에 "6.1 [정의 P8-2-1]·[정의 P8-2-2](원천 문서에서 메인이 직접 옮김)"를 더한다.
  - 429행 "확인 필요 A를 닫는다"를 지운다.

**[커밋 전 수정][T] M′-3. O 목록에 메인 행위 두 가지가 없다**
- 근거(메인 transcript `c52f3f13-….jsonl`, transcript_scope 21:00 이후와 직접 파싱)
  - (가) **메인 Bash 파이프 9회**, 14:03:12Z~14:20:50Z(23:03~23:21 KST)다. 위치는 L2384·2521·2529·2543·2577·2640·2790·2797행과 메모리 덧붙이기 2846행이다. 읽은 곳은 P8-4 재실행 러너 출력, 근거 폴더, LOCAL_ONLY, RUN_ALL, 백업 폴더다.
    - 그중 14:20:45Z(L2790)는 `grep "\.npz" RUN_ALL.SHA256SUMS | head -2`였다. 출력에 `impl_cases_a1` 아래 npz 파일 이름 2개와 sha가 나왔다. 이것은 P8-2 경로 1 실행 출력 이름이다. 메인은 경로 2 넘김을 만드는 쪽이다.
    - 같은 꼴의 control-expert 노출(10.2: "목록 머리 4줄 … 파일 이름 1개")은 공개돼 있다. 메인 쪽만 빠졌다. 앞 감사 M-6과 같은 기준이다.
  - (나) **PID 58136 훅 고아 재개**
    - 14:04:20Z(23:04:20 KST) `resume_thread.py --pid 58136 --tid 52048 --started "2026-11-27 18:38:42"` dry-run 결과는 `ready 1`이었다. 대상 명령줄은 `python-dev python.exe -I -B …/tools/verif/blind_guard.py`였다.
    - 14:04:27Z `--apply` 결과는 `resumed 1, exited 1`이었다.
    - 이 세션 transcript(메인 + 서브에이전트 18개)에는 09:30~09:50Z(18:30~18:50 KST)에 그 시각의 도구 호출이 없다. 메인은 09:35:05Z~09:44:32Z에 AskUserQuestion 응답을 기다리고 있었다. 같은 시각에 다른 세션 3개(`C--workspace`, `ct-sensor-simulation`, `leak-simulation`)가 활동 중이었다.
    - [추정] 다른 세션 호출의 훅이다. 이 판의 호출이라는 근거는 없다.
- 공개 목록에 넣어야 하는가(지시 6의 판단): **넣는 것이 맞다(기록 행).**
  - 4.2 표는 "블라인드·검색 규칙 관련 사건"을 다룬다. 이 사건은 블라인드 목록이 유효하던 때(18:38 < 20:50:46)에 생긴 blind_guard 인스턴스의 정지이고, 그것을 메인이 손댄 프로세스 행위다.
  - 지킨 호출을 특정하지 못했다는 사실 자체가 공개할 내용이다.
  - 노출은 없다(프로세스 재개만 했고 파일은 읽지 않았다).
- 권장 조치(control-expert): 4.2에 다음 두 행을 더한다.
  - O8-36(메인 Bash 파이프 9회, 23:03~23:21 KST. 노출: 러너 출력·목록 머리, RUN_ALL npz 줄 2개의 파일 이름·sha(cases 실행 출력), 값 없음)
  - O8-37(23:04 PID 58136 blind_guard 훅 고아 재개. 18:38:42부터 Suspended. 이 세션에는 그 시각 호출이 없음, 지킨 호출 미상, 노출 없음)

**[커밋 전 수정][I] M′-4. 6절 347행 "경로 2 작성자가 열면 안 되는 자료" 목록이 규칙 9:335 범주보다 좁다(앞 감사 M-8의 제 권장 문장이 좁았음)**
- 근거
  - 규칙 335행: "경로 2 작성자는 경로 1 코드·출력·브랜치·blob과 감사가 인용한 경로 1 줄을 열지 않는다."
  - 347행 목록은 이 판정서, `stage4_judgement/`, `judge_2263b246/`·`judge_7ea78232/`, `impl_cases_a1/`, 4단계 감사 hand-back뿐이다. 다음이 빠졌다.
    - 경로 1 판정 코드·브랜치·blob: worktree `ed8-judge`·`ed8-judge2`·`ed8-judge3`·`ed8-judge4`와 같은 이름의 브랜치, T8 계열 커밋의 `jp3_ed8_judge.py` 등
    - `stage4_prejudge*/`: `stage4_prejudge_t8ppp/cases_jp3_rows_smoke.json`은 cases 판정 행 스모크이고, `prejudge_report.md`는 O8-20 겹침 값을 담고 있다
    - `t8ppp_evidence/`·`t8pppp_evidence/`: 경로 1 도구 구현 보고
    - `audit_t8ppp/`·`audit_prerun/`: 경로 1 코드 줄을 인용한 감사
    - `j9_runs/56849248/RUN_ALL.SHA256SUMS`·`56849248_LOCAL_ONLY.SHA256SUMS`와 백업 폴더: cases npz 이름·sha
    - `stage4_runner/`와 러너 원본: cases 로그
- 실패 시나리오: 메인은 347행대로 `blind_paths.json`을 만든다. 그러면 위 폴더들은 기계적으로 막히지 않고, 경로 2 작성자가 판정 행 수·경로 1 코드를 볼 수 있다.
- 권장 조치(control-expert): 347행에 위 범주를 더하거나, "규칙 9:335 범주 전부(경로 1 판정 코드 worktree·브랜치·blob, 판정 전 점검·구현 보고·감사 폴더, 실행 출력 sha 목록과 백업)"를 한 줄로 더한다. 공유할 결정 문장(D-1 보충 1·2항 등)은 메인이 원천에서 직접 옮긴다. 경로 2 시작 전에 고쳐도 되지만, 목록의 원본이 이 판정서이므로 커밋 전에 고치기를 권한다.

### 기록

**[기록][T] R′-1. O8-32의 "읽은 곳" 문구**: 12:14:44Z 호출이 읽은 곳은 정식 실행 러너 `runners/outrigger-ed8/p84_t8pppp_7ea78232`였다. 12:14:54Z는 `p84_suite_41e107e9_56849248/run`, 12:14:59Z는 `runners/outrigger-ed8/p84/run`이었다. 셋 다 재실행 러너(`p84wt_7ea78232`)가 아니라 그것을 설계하려고 읽은 앞 실행들이다. "P8-4 재실행 러너·근거 폴더"를 "P8-4 정식·기준선 러너와 근거 폴더(재실행 설계용)"로 고치기를 권한다. 노출 판단(블라인드 아님)은 같다.

**[기록][I] R′-2. `npz_local_only.py`의 실행 위치와 원자성**
- 실행한 파일은 scratchpad `main-npzbackup\npz_local_only.py`였다(L2807 dry-run, L2822 `--apply`). 그 뒤 L2832에서 repo로 복사했고, 사본 sha는 `71c27a51`이다. 실행과 복사 사이에 Write는 없었다. 판정서 391행의 "스크립트 `stage4_judgement/npz_local_only.py`"는 내용상 같은 파일이다. "scratchpad 사본으로 실행, 실행 뒤 같은 바이트를 근거로 복사"를 한 줄 더하면 정확하다.
- 코드(31-72행)는 판정서 설명과 같다.
  - 복사 전에 RUN_ALL sha를 대조한다(44행).
  - 이미 있는 백업은 덮어쓰지 않는다(51행).
  - 복사 뒤 사본을 다시 해시한다(58행).
  - 문제가 있으면 목록에 덧붙이지 않고 종료 1로 끝난다(61-64행).
  - 목록은 LF로 덧붙인다(66행).
- 다만 `--apply`에서는 문제를 파일별로 판정하는 동안 앞 파일들이 이미 복사된다. 문제가 생기면 백업만 일부 남고 목록은 그대로다. 이번 실행은 문제 0이어서 영향이 없다.

**[기록][R] R′-3. 개정 3의 읽기 공개가 없다**: 10절에는 10.1(개정 1)과 10.2(개정 2)만 있다. 개정 3에서 읽은 줄(정오 1 108행, v8 363행)이 10.2 범위 안이면 "개정 3은 새로 읽은 파일 없음" 한 줄로 충분하다.

**[기록][R] R′-4. `.git/info/exclude` 행 번호**: 판정서 390행은 "112-114행"이라고 적었다. 112행은 주석(`# … 56849248: outputs over the size limit …`)이고, 두 파일은 113·114행이다(`git check-ignore -v`). 뜻은 같다.

**[기록][E] R′-5. 5.4 (4)의 `critical_absent`**: 앞 감사 199행은 `critical_absent` 0도 요구했다. 5.4 (4)는 `critical_skipped`·`xpassed` 0만 명시한다. 같은 문단의 이름별 수(7패턴 모두 1개 이상, 전부 통과)가 이것을 대신하고, `junit_skips_critical.json` findings에도 `critical_absent`가 없다. 판단에는 영향이 없다.

**[기록][T] R′-6. 감사자 자신의 위반**: 이 재감사 중 14:28:27Z(23:28 KST)에 Bash 파이프 1회를 썼다(`git ls-tree -r --name-only 7ea78232 | grep …; git log -1 --format=%B ecf6c142 | head -40`). 읽은 것은 커밋 트리의 파일 이름과 T8 커밋 메시지이고, 블라인드 경로는 아니다. O 목록에 감사 행위로 한 줄 더할지는 메인이 정한다.

## 지시 항목별 확인 결과

### 1. B-1 해소 — 5.4 P8-4 판정: **맞음**
- `baseline_check.py sums …\p84_suite_T8pppp_wt_7ea78232\SHA256SUMS`의 결과는 entries 17, mismatch 0, missing 0, unlisted 0, crlf 0, cited_ignored 0이다. `cited_untracked` 18은 미추적 폴더라서 나온 것이고 커밋 전이면 정상이다. SUMS 파일 sha는 `47a0b484…`이고 판정서 277행과 같다.
- 다시 센 값(python-dev, 독립 XML 파싱)
  - `junit.xml` sha `dfe7fc14…`는 `suite_judgement.json`·`suite_record.json`의 sha와 같다. 시험 9119: passed 9102, failed 2, skipped 15, xfail 0, 중복 0.
  - `suite_judgement.json`: status `pass`, findings 세 개 모두 `[]`. baseline_list sha `7fce20f4…`는 근거 폴더 `p84_suite_41e107e9_56849248/base/existing_failures.txt`를 다시 잰 값과 같다(입력 경로는 러너 쪽 `p84\base` 사본). existing_failures_record는 failed 2(`test_d8x_diag::test_rerun_gives_the_stored_command_hash`, `test_record::test_default_snapshot_directory_is_results_states`)와 skipped 15다.
  - `p84.done` `exit=0 wall_s=6518`. driver log `[before] status_lines=0`, `[run] end exit=0`, `[after] status lines=14 pycache lines=13`. `git_after.txt`는 `.hypothesis/`와 `__pycache__` 13개다.
  - `worktree_tests.md` 머리: worktree `ed8-judge4`, 데이터 root main, pytest 6504.2 s, 시험 9119, probe `outrigger_sim` worktree, 바뀐 데이터 경로 47회, 원본 불변 True, 실행 폴더 삭제 False, 오류 2·경고 44·참고 287. 판정서 300행과 같다.
  - `junit_skips_critical.json`: critical 7패턴, `critical_skipped` 0, `xpassed` 0, 범주 `skipped` 15·`test_failed` 2.
  - 이름별: p86 1, `test_p8_10_` 2, `test_ed8_run_path` 4, `test_ed8_gate_p80_key` 17, PSW 둘 각 1, 8 job 1, `test_ed8_harness` 6. 모두 통과다. `test_ed8_*`는 354개 모두 통과다.
  - `junit_ed8_compare_T8pppp_formal_vs_wt.txt`: 354/354, changed 0, only 0.
- 규칙 기준선 `p84_suite_41e107e9_56849248/base/junit.xml`과 직접 대조한 결과
  - A 8782(통과 8765·실패 2·건너뜀 15), B 9119, A에만 1, B에만 338(전부 통과), changed 0. 8782 + 338 − 1 = 9119다.
  - 비통과 집합(이름, 상태)은 A와 B에서 같다(17 = 17).
  - `test_coupled_batch_rows_and_resume`는 통과다. `junit_compare_rule_baseline_vs_wt.txt` 첫 줄도 같은 수다.
- 앞 감사 199~215행 1~7번 항목: 1~7이 모두 5.4 (1)~(7)에 있다(5번의 `critical_absent`는 R′-5).
- 기준선에만 있는 시험 `test_ed7_adoption::test_both_candidates_qualifying_is_not_decided`
  - `git log 41e107e9..7ea78232 -- test_ed7_adoption.py ed7_condition3_adoption.py`의 결과는 `ecf6c142`(2026-11-26T22:50:30, author와 committer 같음) 하나뿐이다. `git log -S`도 같은 커밋이다.
  - blob을 비교했다. `ecf6c142` = `60ebb4a4` = `7ea78232`이고, 시험 blob은 `de891586`, 모듈 blob은 `5402b7ca`다. `41e107e9`은 시험 `6b35bc71`이다. 커밋 메시지("Edition 7 judge tools brought from the edition 7 judge commit 60ebb4a4 … ed7_condition3_adoption.py, test_ed7_adoption.py")와 맞는다.
  - `git diff 41e107e9 ecf6c142`에서 docstring "until then ``undecided``"인 시험 하나가 지워지고 세 시험(`…_and_equal_keep_arm_2`, `…_the_better_one_is_adopted`, `…_with_crossing_failures_keep_arm_2`)이 들어왔다. 셋 다 이번 실행에서 통과다.
  - 판정서 309-310행 설명은 git 기록과 맞는다. 규칙 364행의 멈춤 조건(새 실패·핵심 미통과·새 건너뜀)은 "기준선에만 있는 시험"을 포함하지 않는다. 핵심 패턴에 `test_ed7_*`는 없다. 바뀐 파일은 T8 범위(11.2, `04_scripts`·`05_tests`) 안에 있다. 그래서 "영향 없음, 기록"은 규칙 문면에 맞는 읽기다.
- C8 조건 동일성 표의 `no_data_paths` 275 → 285
  - 두 `worktree_tests.md`의 발견 표를 분류별로 셌다. C8 run은 참고 277 = `no_data_paths` 275 + `probe_worktree` 1 + `rebase_unmatched` 1이고, 재실행은 287 = 285 + 1 + 1이다. 경고(29 + 15)와 오류(2)는 같다.
  - `no_data_paths` 위치의 차집합은 재실행에만 10개, C8에만 0개다. 그 10개는 `git diff --diff-filter=A --name-only 56849248 7ea78232 -- 05_tests/unit`의 10개(`test_ed7_judge.py`, `test_ed8_gate_judge.py`, `test_ed8_gate_p80_key.py`, `test_ed8_jp3_settings.py`, `test_ed8_judge.py`, `test_ed8_judge_rules.py`, `test_ed8_run_path.py`, `test_ed8_t8p.py`, `test_ed8_t8pp.py`, `test_ed8_t8pp_records.py`)와 정확히 같다.
- 그 밖의 조건
  - `full_suite_ed8.ps1`: C8 트리 blob `232dbc2c`, ed8-impl HEAD = C8, 작업 트리 수정 0.
  - `worktree_tests.py`: sha `991c3833`, mtime 2026-11-25 16:46:54.
  - 러너 `p84wt_runner.ps1`은 out 폴더가 있으면 거부한다. HEAD와 `--ignored` 0을 확인하고, 기준 목록 sha가 다르면 종료 3이다. 판정서 표와 맞는다.
  - `ed8-judge4`는 지금 HEAD `7ea78232`이고 `status --porcelain --ignored`가 0줄이다.
- 결정 4단계-1 문면("깨끗한 checkout … worktree_tests 꼴 … base/junit.xml과 직접 대조 … 그 결과로 판정, 사슬 근거는 보조")과 맞는다. 0절 45행, 1절 62행, 5.4 (8), 5.3 머리의 "보조"가 모두 그 꼴이다.

### 2. M-2~M-9, R-1~R-9 반영: 모두 반영됨(표본 확인)
- M-2: 63행(2b)과 274행에 권장 문장 그대로 있다.
- M-3: 65행.
- M-4: 머리말 18행 결정 행, 8.1 1~5 "결정됨", 6절 340행 "→ census 경로 2와 함께 S8-C 전(결정 4단계-2)", 7절 새 행 둘(378·379), `audit_t8ppp` "8개"(374행, Glob 실제 8개), 9절 431행 "약 108분".
- M-5: O8-29(168행). transcript 09:59:27Z와 시각·명령·"변수 대입" 사유가 같다. 이 세션의 실제 훅 차단은 이 1회뿐이다(07:33Z는 blind_guard 자체 시험, 실제 호출 차단 아님).
- M-6: O8-32, O8-26 (2).
- M-7: 396-405행의 7 + `_identity_checks` + 새 폴더 2, 9절 428행 같은 수.
- M-8: 347행(범위가 좁은 문제는 M′-4).
- M-9: 148행.
- R-1: 66·115행의 "라운드 수는 23쌍 모두 같고 … 비트 단위로 다르다". 비선택 9쌍의 해시 같음은 넣지 않았다(사용자 결정과 맞음).
- R-2: 210행. R-3: 127행. R-4: 25행. R-5: 132행. R-6: 196행. R-7: 142행. R-8: 155행 (바).
- R-9: 5.2 아래 표. 판 7 정오 1 234행("L1 기준 4개의 출처별 정체성 값(l1ref report `runs.<stem>.identity_sources`)")과 같은 꼴이다. VBN0 실제 태그는 73행에 있다.

### 3. l1ref `identity_sources` 표: 글자 그대로 같음
- `l1ref.json`(`810fa864…`)의 4 run × 7 항목 × row/meta를 표 226-239행 56칸과 대조했다. 칸마다 값 키(16자)가 하나뿐이고 키가 같다. 줄 수가 같고, 백틱 값(`final_C4G2_…_ED8`, `<absent>`, `null`, `["A_i","A_ib","A_ii","B3"]`, `7`)은 원문 문자열이나 `json.dumps(separators=(",",":"))`와 같다. 불일치는 0이다.
- 약칭 값 242-244행(P1, EBC7, D6)과 248행(LSB 전문)은 원문 직렬화와 글자 그대로 같다.
- "row와 같음"·"같음"·"P1" 같은 줄임은 221·241행에 설명이 있고, 값 키로 원문과 이어진다(해석을 더하지 않음).

### 4. 6.1 경로 2 넘김 문장: 인용은 글자 그대로이고 해석은 섞이지 않음
- [정의 P8-2-1]: "E = R12 bottom-FL-Fs4 o0.0" / "F = `j9_case_f` FR 행"은 정오 1 108행의 부분 문자열과 백틱까지 같다. 잘라 낸 부분("× {VBL, LSL1~4} 5줄")은 357행에 밝혔다.
- [정의 P8-2-2]: 인용과 "행 전체"가 v8 363행 `| P8-2 | 사례 재생 E·F × {VBN, LSN1~4} 10줄 J-P3 판정 키 0 | 판정(관문) | > 0 |`과 같다.
- sha 두 개는 `.sha256`과 같다.
- L→M→N 대응은 쓰지 않았다. 360행 "판 사이 설정 이름의 대응은 규칙 문서에 적혀 있지 않음"이 사용자 결정 문면과 맞는다.
- 353행의 "262·268·423행의 E는 층 E"는 확인했다. 세 행 모두 층 E·E 후보 사건이다. 이 문장은 인용 밖이고, 이 판정서는 넘기지 않으므로 문제없다.
- 6절 금지 자료와 다시 블라인드한다는 문장은 347행에 있다. 범위가 좁은 문제는 M′-4, 6절 다른 문장과 어긋나는 문제는 M′-2다.

### 5. 7절 실행 출력 커밋: 수·sha는 맞고, SUMS 목록은 M′-1만
- LOCAL_ONLY: sha `47ab36a5…`, 909줄, CRLF 0, BOM 없음, 끝 LF. 한도 초과 3(`L1_VBN.json`, `L1_VBN.json.partial.jsonl`, `L1a_VBN.json`)과 npz 906이다. 앞 3줄만의 sha는 `7faba722`로, 판정서 392행의 앞 판과 같다(덧붙이기였음).
- RUN_ALL: sha `db24b030…`, 1047줄(경로 중복 0). npz 906, partial 4, `judge_*` 16, `_identity_checks` 8, 그 밖 113이다.
- 대조: LOCAL_ONLY 909줄이 모두 RUN_ALL에 있고 sha 차이 0이다. npz 집합은 양쪽 906으로 같다. 실행 폴더의 실제 파일 909개를 다시 재도 LOCAL_ONLY와 같다.
- 백업 `C:\Users\jinbeom\.claude\backups\outrigger-ed8\j9_runs_56849248\`
  - 파일 913개다: npz 906, 한도 초과 3(repo 상대 경로), 목록 사본 1(LOCAL_ONLY와 sha 같음), 최상위 partial 3.
  - LOCAL_ONLY 909줄의 백업 사본은 결측 0, sha 차이 0이다.
  - 최상위 partial 3(`L1_VBN0`·`L1a_VBN0`·`L1a_VBN`)은 RUN_ALL sha와 같다.
- ignore: `L1_VBN.json`·`L1a_VBN.json`은 `.git/info/exclude:113·114`, partial은 `:37`에 걸린다(R′-4). RUN_ALL·LOCAL_ONLY·판정서·러너 사본은 ignore에 걸리지 않고 `text: unset`(-text)이다.
- `stage4_runner/` 21파일은 `runners/outrigger-ed8/stage4/` 21파일과 이름·sha가 모두 같다(한쪽에만 있는 파일 0, 차이 0).
- `npz_local_only.py`: 판정서 설명대로 동작한다(R′-2).
- "커밋 직전에 SUMS를 쓸 폴더": 미추적 근거 폴더 15개 가운데 SUMS가 없는 10개가 모두 목록(1~8과 새 2)에 있다. 빠진 폴더는 없다. `stage4_runner`는 `--recursive`가 필요하다(M′-1).
- 참고: 커밋 뒤 RUN_ALL로 `baseline_check sums`를 다시 돌리면 새 SUMS 3개(`judge_*`·`_identity_checks`)가 `sums_unlisted`로 나온다. 판정서 406행에 이미 적혀 있으니 결함이 아니다.

### 6. 공개 목록 O8-29, O8-32~O8-35
- O8-29: 맞음(위 M-5).
- O8-32: 시각·횟수는 맞다(transcript_scope 12:14:44/54/59Z). 문구는 R′-1.
- O8-33: 맞음. 14:06:55Z `clean_pycache.py`가 `removed 13`이었고, `.hypothesis` Count 279였다. 14:07:02Z `Remove-Item` 뒤 `status lines 0`, HEAD `7ea78232`였다. 지금 다시 봐도 0줄이다.
- O8-34: 맞음(5절 대조). 실행 위치 문구는 R′-2.
- O8-35: 맞음. 14:21:38Z "copied 21, same: True"였고, 감사가 다시 대조해도 같다.
- 빠진 것: 메인 Bash 파이프 9회와 cases npz 이름 2개 노출, PID 58136 재개(M′-3). PID 58136은 공개 목록에 넣어야 한다고 판단한다.

## 확인 필요
1. M′-3 (나): PID 58136 행을 "지킨 호출 미상, 이 세션 호출 없음([추정] 다른 세션)"으로 적을지, 다른 세션 transcript까지 확인한 뒤 적을지(메인·사용자). 감사는 다른 프로젝트 transcript를 열지 않았다.
2. M′-4: 경로 2 금지 목록을 이 판정서에서 넓힐지, 경로 2 지시문에서 처리할지(메인). 감사 권고는 이 판정서에서 넓히는 쪽이다(목록 원본이 여기 있음).

## 위임 필요
- control-expert: M′-1(405행 한 줄), M′-2(52·345·346·429행), M′-3(O8-36·O8-37 두 행), M′-4(347행), 기록 R′-1~R′-4 문구.
- tools/verif 후보(python-expert): 없음.

## 메인 세션 권고
- SUMS를 쓸 때 `stage4_runner/`는 `baseline_check.py write-sums <폴더> --recursive`로 쓴다(dry-run에서 21 entries 확인함). 나머지 9개 폴더는 하위 폴더가 없어 기본으로 써도 된다. 감사 폴더 두 곳(`audit_t8ppp/`, `audit_stage4_judgement/`)은 이 재감사 원문을 저장한 뒤 마지막에 쓴다.
- 고친 뒤 integrity-checker로 인용 sha(판정서 새 sha, 폴더 SUMS)를 대조하고 커밋한다.

## 검사하지 못한 것
- PID 58136이 지킨 호출이 무엇이었는지(다른 세션 transcript는 열지 않았다).
- 판정서의 다른 절(1~5.3, 3절 등)은 바뀐 부분이 아니라서 다시 대조하지 않았다(앞 감사 결과를 그대로 둔다).
- 앞 판 LOCAL_ONLY(3줄) 파일 자체는 남아 있지 않다. sha는 지금 목록의 앞 3줄로 확인했다.

## 실행한 검증
- 인터프리터: python-dev `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`-X utf8`, `MKL_THREADING_LAYER=TBB`). 프로젝트 모듈과 판정 모듈은 import하지 않았다.
- 도구
  - `baseline_check.py sums`(P8-4 근거 폴더, 종료 1 = `cited_untracked`만)
  - `baseline_check.py write-sums --dry-run`(`stage4_runner`, 기본과 `--recursive`)
  - `transcript_scope.py`(subagents 폴더 + 메인 jsonl, `--since 2026-11-27T21:00`, 종료 1 = bash_pipe 13: compute 3, 메인 9, 감사자 1)
  - `source_guard.py` snapshot/verify
- 즉석 스크립트(scratchpad `verif-stage4-recheck\`, 모두 지움, `Test-Path` False)
  - `p84.py`: junit 대조, 관문 이름 수, junit_skips 요약
  - `cats.py`: worktree_tests 발견 분류, no_data_paths 차집합
  - `l1ref.py`·`l1cmp.py`: identity_sources 추출, 표 56칸·약칭 4줄 대조
  - `lo.py`: LOCAL_ONLY·RUN_ALL·백업·실제 파일 대조
  - `runner.py`: 러너 사본 대조
  - `tx.py`~`tx4.py`: 메인·서브에이전트 transcript 도구 호출 시각·명령 앞부분·결과 건수만
- git(조회만): `log`, `log -S`, `diff`, `rev-parse`, `ls-tree`, `hash-object`, `status --porcelain [--ignored]`, `check-ignore -v`, `check-attr text`, `ls-files --eol`, `worktree list --porcelain`
- PowerShell: `Get-FileHash`, 파일 목록, 줄 수
- 위반 1건: R′-6(Bash 파이프 1회)
- 메모리: `agent-memory\verif-protocol-auditor\audit_pitfalls.md`에 일반 함정 한 항목을 더하고, `MEMORY.md` 색인 줄 끝에 덧붙였다(Edit).
- 최종 판정 직전에 판정서 sha를 다시 재서 `054abafb…`로 같음을 확인했다(감사 중 바뀌지 않음).
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha stage4_judgement_ed8.md 054abafb…, jp3_remedy_spec_v8_rules.md 35f9eba8…, jp3_remedy_spec_v8_rules.md.sha256 e19aaa48…, jp3_remedy_spec_v7_erratum1.md 74c49bda…, decision_stage4_judgement_20261127.md fd79bb76…, verif_stage4_judgement_precommit.md 1624f762…, SHA256SUMS 47a0b484…, junit.xml 0e4208a5…, 56849248_LOCAL_ONLY.SHA256SUMS 47ab36a5…, RUN_ALL.SHA256SUMS db24b030…, l1ref.json 810fa864…, npz_local_only.py 71c27a51…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음

## 커밋 가능 여부
차단은 0건이다. M′-1~M′-4를 고치면 커밋할 수 있다. M′-1은 SUMS를 쓸 때 메인이 `--recursive`를 쓰는 것으로도 해결되지만, 판정서 문장도 함께 고치기를 권한다. 고친 결과는 문장 대조만 하면 되므로 다시 감사할 필요는 없다고 본다. 판정 결론(4단계 미완: P8-5 판정 불가, P8-4 통과, P8-2 경로 1 통과·경로 2 대조 대기)은 이 재감사로 바뀌지 않는다.
