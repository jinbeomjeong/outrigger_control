# 판 9(436.9) R3 실행 전 재감사 (verif-protocol-auditor, 2026-11-28)

## 감사 요약
- 본 결과: 판정 대상 결과 값은 보지 않았다. 열거나 센 것은 아래뿐이다.
  - 봉인 키 파일 `heldout_g_ed8.json`·`r3c_jobs.json`: job key 건수와 겹침 수만 셌다.
  - 저장 진단 jsonl 3개: `controller_tag = final_C4G2_LAS_K1`인 줄 수만 셌다(설정 태그).
  - `r3c_expected_d1_step.json`: 구조와 건수만 봤다.
  - 이 세션 subagent transcript(`agent-a41f0b82…jsonl`): `ml_inject_cm_bands.py`에 대한 Write·Edit 호출 입력만 재생했고, 출력은 sha 앞 8자뿐이다.
- 대상
  - 판 9 봉인 전 진단 실행 R3a·R3b·R3c·R4를 C9′·T9′로 다시 고정한 것
  - 순차 러너 `runner_r3_seq.ps1`(23단계)
- 시점: 실행 전(재감사)
- 기준 문서
  - 앞 감사 `audit_r3_prerun\report.md`
  - decision_log 835행 "R3 전 결정"
  - `impl_report_3.md` c14e33aa
  - `control_r3_check\report.md` 0824f72c
  - `d1_prerun\SHA256SUMS` 68ddb326(48항목, 재귀)
- 판 9 규칙: 아직 봉인되지 않았다. S·T축은 "봉인 없음 — 사전 등록 아님"이다.
- 코드
  - C9′ 15d3a4a4: `ed9-c9b`, 잠김, 사유 커밋이 HEAD와 맞음
  - T9′ c79b009a: `ed9-t9b`, 잠김, 맞음
  - 진단 8e0bce46: `ed9-diag`, **이번에 잠김 확인**
  - 세 worktree 모두 `status --porcelain --ignored` 0줄
- **판정: 차단 0 / 실행 전 수정 0 / 기록 9.**
  - 앞 감사의 차단 B-1·B-2와 실행 전 수정 M-1~M-8은 모두 해소됐다.
  - 러너는 지금 상태로 띄워도 된다.
  - 대조 c1~c9와 R4는 실행 뒤 손으로 돌리는 단계라 아래 "메인 세션 권고" 순서를 지킨다.

## 앞 감사 항목 해소 표
| 항목 | 상태 | 근거 |
|---|---|---|
| **B-1** aa2·aa3 `-JobsFile` 누락 | **해소** | `runner_r3_seq.ps1`: `-JobsFile …heldout_g_ed8.json`이 붙은 held-out·same-shape 배치 8곳(Grep 건수 8), 단계 23개. 즉석 스크립트로 steps json 10개 run 단계를 같은 인자로 `run_v5 --list` 건조 실행했다. 모두 exit 0이고 커밋이 worktree HEAD와 같고 출력 경로가 아직 없다. 건수 678/339/339/7/100 ×2. 실행 뒤 `ed9-c9b` `status --ignored` 0줄 |
| **B-2** ④ 태그 비교 | **해소** | `compare_identity.py:86-110` `stored_tag_of`: 저장 줄에 태그가 없을 때만 `--stored-tag-absent` 값으로 읽는다. c4 명령에 `--stored-tag-absent final_C4G2_LAS_K1`(`impl_report_3.md:239`). 합성 시험 4건(`check_phase3_tools.py`, impl 6절) |
| **M-1** P/E 분할 | **해소** | 순차 `0xFFFF`·worker 8(`runner_r3_seq.ps1:13`, 모든 단계 `-MaskHex 0xFFFF -Workers 8`, r3c `--mask 0xFFFF --workers 8`). 5단계와 같은 배치다. 예약 `0xFFFF` TTL 180분이고 단계마다 갱신한다(`:49-51`) |
| **M-2** 오류 줄 + `.done exit 0` | **해소(부분)** | run_v5 단계마다 바로 뒤에 `key_presence --absent-key error --key controller_tag --key commands_sha256`(켬은 `--key d1_settings` 추가)가 있고, StopOnFail이다. 1 job G-S 사전 점검은 없다(기록 R2-4) |
| **M-3** ed8_j7a 기록 | **해소** | 계획에서 뺐다(decision_log 835, `impl_report_3.md:226`) |
| **M-4** ⑥② 허용 집합 | **해소** | `r3c_expected_d1_step.json` 046bd02b: 그룹 `r3c_expected`, `d1_step_keys` 9개, 원천 `r3c_jobs.json` d542db7c를 기록. c7은 `--allowed-from … --allowed-group r3c_expected --require-allowed-change` |
| **M-5** r3c HEAD 단언 | **해소** | `r3c_run.py:99-108`·`:120-127`·`:149-153`·`:186-192`: `--expect-head` 필수(40자). 시작에서 어긋나면 아무것도 돌리지 않고 2, 끝에서 어긋나면 `head_problem`을 기록하고 2, git 실패는 깨끗함으로 읽지 않는다. `ed9-diag`도 잠갔다 |
| **M-6** diff 범위 시험 | **해소** | `test_ed9_judge_tool.py:330-336`: (a) checkout ↔ `ED9_RUN_COMMIT`의 차이는 판정 도구 3개와 `05_tests/`뿐이어야 한다. `:339-348`: (b) C8 → `ED9_RUN_COMMIT`의 `03_src`와 실행 경로 변경이 정확히 5파일이어야 한다. `git diff --name-only 86121e8f 15d3a4a4`(8파일) 중 실행 경로는 `run_v5.py`·`verdict_runs.py`뿐이고, C8→C9 3파일(03_src)과 합쳐 5다 |
| **M-7** 자리표시 | **해소** | `jp3_ed8_judge.py`(T9′) `spec_problem`과 `main`. 판정 하위 명령 5개(`JUDGING_COMMANDS`)는 spec이 64자 소문자 16진수가 아니면 판정하기 전에 `setting_defect`. `--design-reading`(census·stage5·heldout)일 때만 자리표시를 돌리고 `design_reading: true`를 붙인다. 봉인 sha에 이 플래그를 주면 거부한다. 시험 `test_ed9_judge_tool.py:254-304`(매개변수 7, stage5 main 3, ed8 키 보존). rule 문자열은 `RuleSet.rule_text`(`jp3_remedy_spec_v9_rules.md …, T9`)이고 ed8은 바이트 동일(시험 `:198-199`·`:304`) |
| **M-8** 출력 위치 | **해소** | 출력 루트 `ed9_design\r3_runs\`(아직 없음, `d1_prerun` SUMS 밖). `git check-attr text` = unset(`-text`, 대표 경로 2개) |
| R-1 NUMBA 캐시 공유 | 해소 | 순차라 동시 쓰기가 없다. 캐시는 `numba_cache\15d3a4a4`(step_r3), r3c는 `r3c_1..3` |

## 새 점검 (요청 항목)

### run_commit 하나 고정
- T9′ `ED9_RUN_COMMIT = 15d3a4a4f0d3…`가 ed9 규칙 집합의 유일한 run commit이다(`RULE_SETS["ed9"]`).
- R3a·R3b 10단계 모두 `-Commit 15d3a4a4…`, worktree `ed9-c9b`다.
- r3c ①②는 `--expect-head 15d3a4a4…`, ③은 진단 커밋 `8e0bce46`이다. ③은 판정 입력이 아니다.
- R4는 `checked_step(.done, …, C9′)`로 `.done` commit과 끝 identity를 본다.
- ed8은 C8 그대로다(시험 `:204`).

### ITEM_GROUPS 시험이 실제 생산자 문장을 쓰는지
**예.**
- `test_ed9_judge_tool.py:382-404`가 실제 생산자 `judge_stage1_4368.old.J_fails`(= `judge_stage1_r5.J_fails`, `06_analysis\03_hydraulic\coupled\v5\paper_runs\scripts\judge_stage1_r5.py:126-128` `f"final {base['final']} -> {on['final']}"`)와 `ed7._item_text`로 문장을 만든다.
- 그 문장이 `J4 fail: final ready -> <후보>`인지 단언하고, fault·fault_reground는 `fault`, level·touch는 `end_state`로 분류되는지 본다. 위상 값 인자가 있을 때와 문장만 있을 때를 모두 본다.
- 입력 metric dict 자체는 합성이다. `final` 키는 생산자 `metrics`의 `"final": rec["final_phase"]`(`judge_stage1_r5.py:53`)와 같은 이름이다.
- 판정 경로 `aa_pair_verdict`는 `treatment.get("final")`을 넘긴다(T9′ 1490-1491). `metric_of` → `judge_stage1_4368.metrics` → `old.metrics`로 `final`이 채워진다.
- `test_item_groups_of_texts`(`:358-373`)에는 옛 꼴 `final fault`가 남아 있다. V0 자기 실패 문장(control 6절)이라 맞는 꼴이다.

### `--require-prior` 순서
`compare_identity.py:214-239` `checked_priors`의 동작:
- 앞 보고가 없거나 `identical`이 아니거나, 이번 `--stored`의 sha가 앞 보고의 stored·new 입력에 없으면 InputError → not_judgeable(종료 2). 이때 보고는 쓰지 않는다(`main` `:396-398`보다 앞).
- 명령표 대조
  - c2 ← c1: c2 stored = c1 stored($S 3파일)
  - c5 ← c4: c5 stored = c4 new(census_v0_off)
  - c7 ← c6a·b·c: c7 stored = 각 c6의 new(off_plain)
- 세 경우 모두 sha 포함 관계가 성립한다.
- 앞 보고가 `as_expected`이면 거부된다. 지금 사슬은 앞 단계가 모두 identical 기대라 맞다.

### census rerun V0 개수·키 검사
- `check_census_v0_rerun`(T9′ 779-808)의 기준
  - `run_v5 batch_jobs("main")`의 V0 job 키 집합 == rerun 줄 키 집합
  - 100줄
  - 설정은 V0만
  - 어긋나면 SettingDefect
- 키 함수 `ed8_key_lists.plain_job_key`는 `rerun_v0_rows_by_job`(757-771)과 같다. 거기서 오류 줄과 중복은 NotJudgeable이다.
- 시험 `:231-248`(99줄, 바깥 job, 다른 설정).
- R4(stage5)는 census를 쓰지 않으므로 이번 실행 범위 밖이다.

### soil 관문
- `verdict_runs.py`(C9′) `d1_median_record`: C-m 켬 ∧ `soil.enable` False이면 RuntimeError. 오류 줄이 되고 key_presence 단계에서 멈춘다.
- 끔 프로세스에는 걸리지 않는다.
- run 뒤 검사라 계산에는 영향이 없다.
- spawn worker 시험 `test_ed9_cm_switch.py:208-244`(켬 거부, 끔 통과, 프리셋 soil 켬).

### 명령표 c1~c9와 R4의 빈 집합·허용 집합 처리
- 상태 결합 `compare_identity.py:287-293`: `differs`(허용 밖 차이·스위치·경로 표지·바뀌어야 할 허용 job이 그대로) ≻ `not_judgeable`(0개 대조, `--expect-compared` 불일치, 누락·여분·중복·오류 줄) ≻ `as_expected` ≻ `identical`. 실패가 판정 불가에 가려지지 않는다.
- c3: 허용 집합(끔 쌍둥이 스캔)이 비면 바뀌어야 할 job이 0이므로 identical이 기대값이다. 맞다.
  - `scan_d1_step_rows.py`는 줄 0개나 오류 줄이 있어도 exit 0이다. 다만 c3 쪽에서 0개 대조·오류 줄이 not_judgeable이 되므로 실패 쪽으로 닫힌다(기록 R2-5).
- c9: `--only-common --expect-compared 5`. 봉인 키 파일로 다시 셌다.
  - R3b 네 배치의 job key: 678 / 339 / 339 / 7, 모두 고유하고 배치 사이 중복 0(1363 고유)
  - r3c 59와 겹치는 것: 정확히 5이고, 반복 0
  - 설정은 모두 V0
  - 따라서 `repeated new jobs` 때문에 잘못 not_judgeable이 될 일은 없다.
- c6a·b·c: 저장 진단 줄 7·34·20줄이 모두 `controller_tag = final_C4G2_LAS_K1`이다(`key_presence --where`). `--stored-tag-absent`는 쓰이지 않고 해도 없다. 끔 비교 태그가 맞는다.
- c7·c8 경로 표지
  - `path_marker_problem`(`:157-169`)은 `diag.two_pressure_file`이 없으면 그 자체를 문제로 본다(실패 쪽으로 닫힘).
  - c7: 양쪽 `$WT`(ed9-c9b)
  - c8: stored `$WT`, new `$WTD`(ed9-diag)
- R4(T9′ stage5) 빈 집합 처리는 앞 감사 R-7과 같다(바뀌지 않음, diff 확인).
  - `candidate_not_run`·n_N < 200 → not_judgeable(`jp3_ed8_rules.py:614-622`)
  - 파일 수·job 불일치, same-shape 목록 불일치, 사이드카 배치·C-m 불일치 → setting_defect·not_judgeable
  - `--design-reading`이 없으면 판정 전에 setting_defect

### impl 확인 필요 2 — C9′가 T9의 자식이라 판정 도구 변경을 품는 것
- 판단: **다시 만들 필요 없다(기록).**
- 실행 경로 쪽 근거
  - C9′ 트리의 `jp3_ed8_*` 판정 파일은 C8 실행 경로 목록 밖이다.
  - M-6 (b) 시험이 실행 경로 변경을 정확히 5파일로 고정한다.
  - `test_run_path_closure_is_unchanged_here`가 checkout 기준 정적 import 폐포 = C8 목록을 지킨다.
- 판정 쪽 근거: 판정 커밋은 T9′ 하나다(`RULE_SETS["ed9"]`).
- 남는 위험: `ed9-c9b`에는 T9판 판정 도구가 들어 있다. 거기서 판정을 돌리면 T9′가 아니다. R4는 `ed9-t9b`에서만 돌린다(R2-2).

### impl 확인 필요 3 — R3c ③(ed9-diag, C9 기반)과 c8 관문으로 충분한지
- 판단: **충분하다.**
- C9 → C9′ 실행 경로 차이는 두 가지다.
  - `run_v5.py`: 배치 표 추가뿐이다(`ED9_ARM_BATCHES`, 인자 규칙, `ed8_batch_jobs` 이름 변환). r3c_run이 부르는 `run_one`은 바뀌지 않았다.
  - `verdict_runs.py`: run 뒤 soil 관문뿐이다. soil 켬 줄에서는 계산이 같다.
- `two_pressure.py`는 C9 = C9′다(03_src 변경 없음, `git diff --stat 86121e8f 15d3a4a4 -- 03_src` 0).
- 따라서 ③과 ②의 계산 경로 차이는 진단 커밋의 trace 패치(`two_pressure.py` +175/−4)뿐이다. c8(`--with-d1-reasons`, 명령·끝 위상·WARN/FAULT·D1 INFO 사유)가 그것을 실측으로 가린다.
- 다르면 ③만 버리는 규칙이 명령표에 있다(`impl_report_3.md:253`).
- 기록: ③ 쪽 verdict_runs에는 soil 관문이 없다(C9판). ③은 기록 전용이라 영향이 없다(R2-3).

### `ml_inject_cm_bands.py` 수정 전 사본이 없는 것의 영향
- **영향: 작다. 그리고 원본이 정확히 복원 가능하다.**
- 이 세션 subagent transcript `agent-a41f0b8241033371e.jsonl`에서 이 파일의 Write·Edit 입력 26회를 순서대로 재생했다(즉석 스크립트, sha만 출력).
  - 2026-11-28T07:01:14의 Edit 직후 상태의 LF 바이트 sha가 **364a7672…로 정확히 일치**한다(06:59:48 Write + 07:01:02~07:01:14 Edit 5회).
  - 마지막 Edit(07:57:05) 상태는 현재 파일 7a651277…과 같다.
- 옛 출력 3개(`ml_inject_cm_bands.csv` a1d87d90, `ml_inject_cm_runs.csv` 813166df, provenance)는 그대로다. `check_bands_ev.py`가 새 출력을 `event_band`로 합치면 옛 CSV와 다른 행이 0이라고 보고한다(impl 5절).
- R3 실행과는 무관하다. P9-D1-5·6 등록부(봉인 전 확인값)가 옛 출력과 옛 스크립트 sha를 인용한다면, 복원 사본을 `scripts\history\ml_inject_cm_bands_364a7672.py`로 두는 것을 권한다(메인 세션 권고 5).

## 발견 사항 (기록, 심각도순)
- **R2-1 [T·R] 봉인 때 판정 커밋이 한 번 더 바뀐다.**
  - `ED9_RULE_DOCUMENT = "jp3_remedy_spec_v9_rules.md"`는 가정 이름이다(impl 확인 필요 1). `ED9_SPEC_SHA256`도 자리표시다.
  - 봉인 뒤 T9″에서 이 두 상수만 바뀌는지 `baseline_check.py blobs --rev c79b009a --rev <T9″>`와 diff로 확인한다.
  - R4를 T9″에서 다시 돌려(이때는 `--design-reading` 없이) `spec_sha256`·`design_reading`·`rule`·`judge_code` 밖의 출력이 같은지 본다. 이것이 등록부 ①("같은 경로 건식 실행")의 경로 동일성 근거가 된다(앞 감사 M-7 권고 유지).
- **R2-2 [I] 옛 C9·T9 worktree(`ed9-c9`·`ed9-t9`)와 `ed9-c9b` 안의 T9판 판정 도구가 남아 있다.**
  - 판정은 `ed9-t9b`에서만, 실행은 `ed9-c9b`에서만 한다.
  - T9′는 C9 `.done`을 setting_defect로 거부한다(run commit 불일치). 그래서 잘못 섞이면 실패 쪽으로 닫힌다.
- **R2-3 [I]** ③(ed9-diag)의 verdict_runs는 C9판이라 soil 관문이 없다. 기록 전용 줄이라 영향은 없다.
- **R2-4 [E] 1 job G-S 사전 점검이 없다.** 스위치 설치 결함이 있으면 R3a 첫 단계(약 1시간)가 끝나고 key_presence 단계에서야 멈춘다.
  - 실패 쪽으로 닫히지만 시간이 든다. 선택 사항이다.
- **R2-5 [E] `scan_d1_step_rows.py`는 0줄이나 오류 줄이 있어도 exit 0이다.**
  - 결과 파일에 `lines`·`error_lines` 칸은 남는다.
  - c3가 not_judgeable로 잡으므로 실패 쪽으로 닫힌다.
  - 등록부에 끔 쌍둥이 스캔을 적을 때 `lines = 7`, `error_lines = 0`을 함께 적는다.
- **R2-6 [R] 판정 근거 시험 범위**
  - `junit_t9b.xml`: tests 1577, passed 1546, skipped 31(모두 pychrono 없음), failed 0, xfail 0, critical_skipped 0(`junit_skips.py` 종료 0).
  - 33파일 묶음에는 `test_two_pressure_d1_median.py`(C-m 단위 시험)가 들지 않는다. 03_src는 C9 = C9′라 2차 보고의 `ed9-diag`·Chrono-dev 결과(84 passed, 21 skipped)가 그대로 유효하다고 본다[추정].
- **R2-7 [R] c1~c9·스캔·R4는 러너 밖의 손 단계다.**
  - `--require-prior`가 c2·c5·c7의 앞 단계만 강제한다.
  - R4가 c1~c5 결과를 읽지는 않는다. stats 조건 5(R3b가 예측과 어긋나면 그 x를 k 봉인에 쓰지 않음)는 절차로 지킨다.
- **R2-8 [I] 값이 담긴 로그**: `r3_runs\*\*_a1\run_v5.log`는 job마다 `final_phase`와 해시 앞 8자를 찍는다(앞 감사 R-4와 같음). 러너 로그 `logs_seq\`에는 STOP·DONE과 key_presence 건수만 남는다.
- **R2-9 [I] step_r3.ps1(3ce05c58, 바뀌지 않음)의 남은 표기**
  - 머리 주석 "-Root a NEW folder under ed9_design\d1_prerun"이 낡았다.
  - exit 2가 "출력 있음"과 "run_v5 인자 오류"를 함께 뜻한다(앞 감사 R-3).
  - 실패한 단계를 다시 돌리는 규칙(`_a1` 고정)은 여전히 정해지지 않았다. 실패하면 새 `-Root`(예 `r3a_off_15d3a4a4_r2`)를 쓰고 공개한다는 식으로 미리 적어 둘 것을 권한다.

## 규칙↔도구 대조표 (이번에 바뀐 것)
| 설계 요구 | 도구 위치 | 판단 |
|---|---|---|
| 처리 팔 배치 C-m 켬(control 8 (a)) | `run_v5.py`(C9′) `ED9_ARM_BATCHES`, `D1_MEDIAN_BATCHES` | 같음. R3 범위 밖(impl 7절 `--list`: 1043/339/44/10) |
| C-m 켬 ∧ soil 끔 거부(control 4 관문 1) | `verdict_runs.py`(C9′) `d1_median_record` | 같음 |
| ITEM_GROUPS FAULT = 후보 끝 위상(control 6) | T9′ `_group_of_item`·`j4_candidate_phase`·`aa_pair_verdict` | 같음. 기록칸만 바뀌고 status 불변(ed8 포함, impl 3절) |
| census rerun 100·키 집합(control 7 조건 2) | T9′ `check_census_v0_rerun` | 같음 |
| ③ ≡ ②, ② ≡ R3b 겹침, 경로 표지(control 5) | `compare_identity` `--with-d1-reasons`·`--only-common --expect-compared`·`--*-path-under`, 명령 c8·c9·c7 | 같음 |
| 끔 쌍둥이 대조는 봉인 전 정체성 관문(stats 권고) | `scan_d1_step_rows.py` → c3 `--allowed-from … --require-allowed-change` | 같음(R2-5) |
| ① → ②, ④ → ⑤ 순서(stats 3.2 조건 3) | `--require-prior` | 같음. ⑥①→⑥②도 포함 |
| R3 배치 = 순차 0xFFFF·8(사용자 결정) | `runner_r3_seq.ps1` | 같음 |

## 확인 필요
- Q2-1 (사용자·control) R3 단계가 실패했을 때 다시 돌리는 규칙(새 `-Root` 접미사, 공개 방식). 실행 전에 한 줄로 정해 두기를 권한다(R2-9).
- Q2-2 (stats) `ml_inject_cm_bands.py` 옛 판을 transcript에서 복원해 history에 둘지, 등록부가 옛 출력을 인용할지 새 `_ev` 출력을 인용할지.

## 위임 필요
- python-expert(급하지 않음, 봉인 전)
  - `scan_d1_step_rows.py`: `lines == 0` 또는 `error_lines > 0`이면 종료 1(R2-5)
  - step_r3.ps1 머리 주석과 exit 코드 분리(R2-9). 이 파일은 compute-scheduler 소유일 수 있다.
- `tools/verif` 후보(python-expert): 앞 감사에서 낸 "steps json 단계별 `--list` 건조 실행" 점검. 이번에 같은 일을 즉석 스크립트로 다시 했다. impl의 `phase3_checks\list_counts.py`가 원형이다.

## 메인 세션 권고
1. 시작 직전에 `status.py`로 다른 tenant의 `0xFFFF` 고정과 예약이 없는지 본다. 이어 `runner_r3_seq.ps1`을 띄운다(약 2.3~2.5시간, §3 감시·§4 예약). 감시에서 진행은 `progress_peek.py`로만 센다. 출력 jsonl과 `run_v5.log`는 열지 않는다(R2-8).
2. (선택) 띄우기 전에 상태마다 1 job G-S를 돌린다(scratch 하위 새 `--out`, R2-4).
3. 러너가 끝나면 `impl_report_3.md` 9절 4~6을 순서대로 손으로 돌린다: 스캔 → c1, c2, c3, c4, c5, c6a·b·c, c7, c8, c9 → R4.
   - 각 단계의 stdout `status`와 종료 코드만 본다.
   - R4는 c1·c2·c3·c4·c5가 모두 exit 0일 때만 등록부에 쓴다(stats 조건 5, R2-7).
   - c8이 differs이면 ③만 버린다.
   - R4는 `ed9-t9b`에서 `--design-reading`을 붙여 돌린다.
4. 실행 전후 `step_check.py <r3_runs>\<root>\<step>.done --expect-commit 15d3a4a4f0d3244c242e98856d2228160d090b2d`로 확인한다. r3c는 log.json의 `head_problem`이 null인지 본다.
5. `ml_inject_cm_bands.py` 364a7672 복원(선택)
   - 복원 스크립트를 쓰는 것은 메인 또는 python-expert 몫이다.
   - 방법: `agent-a41f0b8241033371e.jsonl`에서 이 파일 이름의 Write(06:59:48)와 이어진 Edit 5회(07:01:02~07:01:14)를 순서대로 적용하고 LF로 저장한다.
   - 결과의 sha가 364a7672…인지 확인한 뒤 `d1_prerun\scripts\history\`에 둔다. 넣은 뒤 그 폴더 SUMS를 다시 쓴다.
6. R3 출력 폴더 `r3_runs\`의 SHA256SUMS는 대조·R4까지 끝난 뒤 마지막에 쓴다(`write-sums --recursive` 또는 `--plan`).

## 검사하지 못한 것
- R3c `r3c_run.py`의 실제 실행 경로(건조 실행 하위 명령이 없음). 인자와 시작 관문은 코드로만 확인했다.
- 1546 passed의 재현(감사자 규칙상 pytest 미실행). junit 파일만 검사했다.
- `gen_steps_r3_seq.py` 본문. 생성물 `steps_r3_seq.json`과 러너를 직접 점검했으므로 생략했다.
- `stats_r3_check\report.md` 본문(decision_log 835의 채택 4건 문장과 impl 3차 보고 서술 기준으로 봤다).
- ed8 스모크 불변(블라인드, 앞 감사와 같음).

## 실행한 검증
- 인터프리터
  - python-dev `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`MKL_THREADING_LAYER=TBB`)
  - dynamics-dev `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B`(`PYTHONDONTWRITEBYTECODE=1`, scratch NUMBA): run_v5 `--list` 10회, `ed9-c9b`에서
- 명령
  - `worktree_locks.py --worktree`(ed9 다섯 개): 종료 0, 5개 모두 잠김·confirmed
  - git: HEAD·status(ed9-c9b·t9b·diag·impl 0줄), `log -3 c79b009a`, `diff --stat` 세 범위, `diff --name-only 86121e8f 15d3a4a4`, `diff 2deb5fd7 15d3a4a4`(run_v5·verdict_runs), `diff 15d3a4a4 c79b009a`(judge), `check-attr text`
  - 즉석 `list_steps.py`(steps_r3_seq.json의 run_v5 단계 10개 `--list`, 커밋·마스크·worker·기존 출력): 모두 exit 0, 건수 맞음, 출력 경로 없음. 뒤 `ed9-c9b` `status --ignored` 0줄
  - 즉석 `overlap.py`(키 파일·r3c_jobs job key 건수만): 위 c9 수치
  - 즉석 `recover.py`(transcript Write·Edit 재생, sha 앞 8자만): 364a7672 MATCH, 최종 7a651277
  - `ps1_lint.py runner_r3_seq.ps1 step_r3.ps1`: 종료 0(info 1, Tee|Out-Host 거짓 양성)
  - `placeholder_scan.py runner_r3_seq.ps1 steps_r3_seq.json step_r3.ps1 --pattern-set both --allow LogDir --allow Root --allow Step`: 종료 0. 허용 5건이 모두 주석 속 표기다
  - `baseline_check.py sums d1_prerun\SHA256SUMS`: entries 48, mismatch 0·missing 0·unlisted 0, cited_untracked 49(커밋 전 기록)
  - `junit_skips.py phase3_checks\junit_t9b.xml --critical "test_ed9_|test_ed8_run_path|test_ed8_gate_p80_key"`: 종료 0
  - `key_presence.py <저장 진단 3파일> --where controller_tag=final_C4G2_LAS_K1 --key controller_tag`: 7/7, 34/34, 20/20
  - `r3c_expected_d1_step.json` 구조 확인(python `-c`): 그룹 1, 키 9
  - `Get-FileHash step_r3.ps1`: 3CE05C58
- 만든 뒤 지운 파일: scratchpad `verif-ed9r3b\`(list_steps.py·overlap.py·recover.py·numba·guard.json, 폴더째)
- 원본 불변: 확인 — 원본 쓰기 0회, 기존 항목 변경·삭제 0건 (sha impl_report_3.md c14e33aa…, SHA256SUMS 68ddb326…, compare_identity.py 25cf5d7e…, r3c_run.py c3a25818…, scan_d1_step_rows.py b4c8adac…, make_r3c_expected.py 776dfbf8…, ml_inject_cm_bands.py 7a651277…, r3c_expected_d1_step.json 046bd02b…, r3c_jobs.json d542db7c…, report.md 0824f72c…, decision_log.md f49a1cd7…, step_r3.ps1 3ce05c58…, 폴더 added_only: 새 항목만 생김, ~$ 임시 파일 없음) · 경고: 입력 폴더에 항목 추가 1건(gen_steps_r3_seq.py)
  - 추가 1건은 감사 중에 compute-scheduler가 만든 생성 스크립트 사본이다.
- 메모리 갱신: `audit_pitfalls.md` "Pre-seal measurement runs" 항목에 (g) transcript 재생 복원법을 더했다.
- 사용한 스킬: 없음
