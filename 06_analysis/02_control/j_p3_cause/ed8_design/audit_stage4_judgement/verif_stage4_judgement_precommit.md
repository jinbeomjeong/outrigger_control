## 감사 요약
- **본 결과**: 블라인드 해제(20:50:46) 뒤에 열었습니다.
  - 판정 출력: `judge_7ea78232\*.json` 8개 전체 값, `judge_2263b246\p80.json`의 상태 서명.
  - 원자료: `impl_*_a1`·`l1ref_a1`. 건수·참거짓·태그 분포만 셌습니다. 줄 내용과 해시 값은 출력하지 않았습니다.
  - junit 5개: 시험 이름과 상태.
- **넘김 주의**: 이 보고에는 P8-2 경로 1의 사례 행 이름과 건수가 들어 있습니다. 경로 2 작성자에게 넘기지 마십시오.
- **대상·시점**: 436.9 판 8 4단계 판정서 초안 `ed8_design\stage4_judgement\stage4_judgement_ed8.md`(25ce1bbc), 판정 후·커밋 전입니다.
- **기준 문서**
  - 규칙 `jp3_remedy_spec_v8_rules.md`(35f9eba8): `.sha256`과 같고, `-text`, LF, BOM 없음, 추적됨(seal_check 종료 0).
  - 결정 D-1 보충(6624affe), D-2(0a636250), 4단계 판정서 결정(fd79bb76).
- **판정: 차단 1 / 커밋 전 수정 9 / 기록 9**
  - 재집계(C)는 8개 관문과 P8-4 사슬의 모든 핵심 건수가 판정 출력·판정서와 같습니다.
  - 정체성(head·is_clean·규칙 sha·실행 커밋·`.done`·출력 sha)도 모두 맞습니다.
  - 판정서는 아직 커밋하면 안 됩니다. P8-4 재실행 결과를 넣고, 아래 커밋 전 수정을 반영한 뒤에 커밋합니다.

## 발견 사항 (심각도순)

### [차단][R] B-1. P8-4 행이 사용자 결정 1과 다르게 "통과(사슬 근거)"로 적혀 있다
- 근거
  - 판정서 42·61·100·229·278-282행: "P8-4 통과(사슬 근거, 확인 필요 1)".
  - `audit_t8ppp\decision_stage4_judgement_20261127.md` 1항: "(나) … 직접 대조한다. 그 결과로 P8-4를 판정하고, 사슬 근거는 보조로 적는다."
  - 재실행은 지금 진행 중입니다. `p84wt_driver.log`는 `[run] begin` 21:15:59까지이고, `out\p84.done`은 아직 없습니다.
  - 결정 문서가 판정서보다 늦습니다(21:14 > 21:09). 판정서는 이 결정을 인용하지 않습니다.
- 실패 시나리오: 지금 커밋하면 결정과 다른 근거로 P8-4 통과가 기록됩니다. 재실행이 실패하면 판정서 결론이 틀립니다.
- 권장 조치(control-expert)
  - 42행: "**시험 묶음 관문**: P8-4는 규칙 기준선 직접 대조(T8⁗ worktree_tests 방식, 결정 4단계-1)로 판정한다(5.4). P8-6·P8-10·P8-11 …"로 바꿉니다.
  - 61행 분류 칸: 재실행 결과의 규칙 분류를 적습니다(`suite_judgement.json` status). 사슬 근거는 "보조(5.3)"로 내립니다.
  - 100행: "P8-4를 통과로 받을 때에 한한다(확인 필요 1)"를 "P8-4 판정(5.4)이 통과일 때에 한한다"로 바꿉니다.
  - 아래 "P8-4가 끝난 뒤 넣을 것"에 따라 5.4절을 새로 씁니다.

### [커밋 전 수정][S·I] M-1. 단계 폴더 SUMS가 최상위 파일만 담는다 — T4h npz 906개(J-P3 판정 입력)의 sha가 어디에도 고정되지 않았다
- 근거
  - `baseline_check sums` 결과: 9개 단계 SUMS 모두 mismatch 0·missing 0입니다. 그러나 목록 밖 파일이 958개입니다(cases 15, p80 119, p815 59, p816 59, p85 51, p88 51, t8 49, l1ref 555, scope 0).
  - 판정서 267행도 "최상위 파일만 담은 SUMS"라고 적습니다.
  - cases 판정은 줄의 `t4h_file`로 npz를 읽습니다(`cases.json` `rev7_condition.lines[].t4h_file`). 그런데 판정 출력의 `inputs`에는 jsonl sha만 있습니다.
  - 판 7 판정서 `jp3_ed7_judgement_8a2a52ce.md:323`은 "T4h npz … 단계 폴더 SHA256SUMS가 sha를 고정한다"였습니다. 같은 꼴(272행, 결정 3)이라고 하면 사실과 다릅니다.
  - `large_outputs` 건식 결과
    - LOCAL_ONLY 목록 (b)에는 한도 초과 3개만 들어 있습니다.
    - `needs_add_force` 909개 = npz 906 + `*.partial.jsonl` 3개(`.git/info/exclude:37`). 이 909개는 어떤 목록에도 들지 않습니다.
    - `L1_VBN.json.partial.jsonl`은 이미 ignore에 걸려 있습니다(`exclude_covered`). `exclude_missing` 2는 `L1_VBN.json`·`L1a_VBN.json`입니다.
- 권장 조치(메인): 아래 "7절 처리 순서"대로 합니다. 판정서 7절에 처리 결과(목록 sha, 백업 경로, 개수)를 판 7 7.5처럼 적습니다.

### [커밋 전 수정][C·R] M-2. "기존 실패" 표기가 규칙 기준선과 다르다
- 근거
  - 61행: "실패 2(기존: `test_d8x_diag::…`, `test_hydraulics_flow_limit_run::test_coupled_batch_rows_and_resume`)".
  - 230행: "실패 2개는 모두 기준선에도 있는 성질".
  - 재집계: `test_coupled_batch_rows_and_resume`는 규칙 기준선 `41e107e9`(`p84_suite_41e107e9_56849248\base\junit.xml`)에서 통과입니다. 223행이 적은 117개 가운데 하나입니다.
  - 기준선 실패 목록은 `test_d8x_diag::test_rerun_gives_the_stored_command_hash`와 `test_record::test_default_snapshot_directory_is_results_states`입니다(`run\suite_judgement.json` `existing_failures_record`).
- 권장 문장
  - 61행: "실패 2(`test_d8x_diag::…`는 규칙 기준선의 기존 실패, `test_coupled_batch_rows_and_resume`는 기준선 통과이고 판정 worktree에 `07_results` 자료가 없어 실패 — 5.3의 117개 중 1)".
  - 230행: "실패 2개는 C8 판정 worktree 꼴(`junit_C8_56849248.xml`)에도 같은 이름으로 있고 관문 시험이 아니다".

### [커밋 전 수정][R] M-3. P8-0 행이 규칙 361행 괄호의 "7fc83456 명령 불변 8 job"을 다루지 않는다
- 근거
  - 규칙 361행: "(7fc83456 명령 불변 8 job, `ed7_probe.py --arms a2 --part all` 114줄 = …)".
  - 이 8 job은 단위 시험 `test_ed8_harness::test_switch_off_runs_keep_the_stored_hashes_and_keys`입니다(`ed8_design/impl_report_ed8/report.md:97`, `control_k1_window/report.md:139`).
  - 판정서 62-63행은 `p80.json`(114줄)만 인용합니다.
  - T8⁗ 정식 junit과 C8 run junit에서 `test_ed8_harness` 6개는 모두 통과입니다(감사 확인).
- 권장 문장(63행 핵심 수 칸 끝): "8 job 대조는 `test_ed8_harness::test_switch_off_runs_keep_the_stored_hashes_and_keys` 통과(P8-4 junit, 5.4)".

### [커밋 전 수정][R] M-4. 결정 문서 fd79bb76이 판정서에 반영되지 않았다
- 머리말 표(10-17행)에 행을 하나 더합니다: `audit_t8ppp/decision_stage4_judgement_20261127.md` | `fd79bb76a6490ed9f6f5e1467b949d80d53fbe5bdf028046fd1860060b59cd1d` | 확인 필요 1~5 결정.
- 8절(277-289행): 다섯 항목을 "결정됨(결정 4단계-n)"으로 바꿉니다.
- 6절 239행 "규칙의 시점" 칸: "정하지 않음" 뒤에 "→ census 경로 2와 함께 S8-C 전(결정 4단계-2)"을 더합니다.
- 7절
  - 행 추가: 4단계 러너 사본 폴더(결정 4단계-3).
  - 행 추가: P8-4 재실행 근거 폴더(예: `ed8_design/p84_suite_T8pppp_wt_7ea78232/`).
  - 260행 "감사·결정 원문 7개" → 8개(지금 8개).
- 9절 296행: "예상 약 30분"을 "약 108분(C8 원형 6458.9 s)"으로 바꿉니다. 이미 실행 중이므로 "실행함"으로 적습니다.

### [커밋 전 수정][T] M-5. O8-29의 근거를 찾았다
- 근거: 메인 transcript `c52f3f13-1809-41e7-8ed4-76fbbd933dd2.jsonl`, 2026-11-27T09:59:27Z(18:59:27 KST).
  - 명령: `$r = "…\j9_runs\56849248"; Get-ChildItem $r -Filter *.done | ForEach-Object Name`.
  - 결과: "blind_guard 차단: 'get-childitem'가 블라인드 경로의 상위 폴더 …56849248를 훑는다 … (변수 값을 대입해 읽음)". 출력은 없습니다.
  - 이 세션에서 훅에 막힌 메인 호출은 이것 1회뿐입니다.
- 시간 순서: T8‴ 판정(18:54) 뒤, 블라인드 목록을 비운 시각(`blind_paths.json` mtime 20:50:46) 전입니다.
- 권장 문장(162행): "| O8-29 | 메인 세션, 2026-11-27 18:59:27 KST | `j9_runs\56849248`에 `Get-ChildItem -Filter *.done` 1회, blind_guard가 막음(변수 대입 판정) | 없음 | 메인 transcript 09:59:27Z(verif 판정 후 감사가 확인) |".

### [커밋 전 수정][T] M-6. O 목록에 빠진 행위가 있다
- 근거: transcript_scope(이 세션 subagent 14개와 메인, 2026-11-27 12:00 이후)와 문서 대조.
  - (가) compute-scheduler-expert(a8a18cd7)가 Bash 파이프를 3회 썼습니다(12:14:44Z·12:14:54Z·12:14:59Z = 21:14 KST, `cat *.ps1 | head -80` 등). 읽은 곳은 P8-4 러너·근거 폴더이고, 블라인드는 아닙니다. 판정서(21:09)보다 뒤라 빠진 것입니다.
  - (나) D-2 결정문 9(마) 둘째 줄("결정문 작성은 판정 출력 p80.json·p85.json(단일 파일)과 … 고정 기준만 읽었다", `p80p85_decision_draft.txt:95`)과 `control_p80p85.md:248`의 "도구 거부 1건"이 O 표에 없습니다. 결정문 9절은 "판정서에 옮김"입니다.
  - 나머지 비교: O8-27 (1), O8-28 (2), O8-31 (1)은 transcript와 맞습니다.
- 권장 조치: O8-32((가))를 더하고, O8-26 옆에 (나)를 한 줄로 옮깁니다.

### [커밋 전 수정][R·I] M-7. 7절과 9절의 "SUMS 없는 폴더" 수가 다르다
- 근거
  - 9절 293·298행은 "SUMS가 없는 6개 폴더"입니다.
  - 7절 표의 "없음"은 7행입니다(257·258·259·260·264·265·266행).
  - 표에 없는 `j9_runs/56849248/_identity_checks/`(md 8개, 미추적)도 SUMS가 없습니다.
- 권장 조치: "SUMS 없는 7개 폴더 + `_identity_checks`"로 맞추고, 처리 순서는 아래대로 적습니다.

### [커밋 전 수정][I] M-8. 블라인드를 해제했는데 P8-2 경로 2가 남아 있다 — 경로 2 작성자에게 막을 자료를 6절에 적어야 한다
- 근거
  - 블라인드 목록을 비운 시각은 20:50:46입니다.
  - 규칙 9:335는 "경로 2 작성자는 경로 1 코드·출력 … 열지 않는다"입니다.
  - 이 판정서 1·5절, `recount_stage4.json`, `judge_*/cases.json`, `impl_cases_a1/`은 P8-2 경로 1 출력입니다.
- 권장 문장(6절 245행 뒤): "경로 2 작성자는 이 판정서, `stage4_judgement/` 재집계 출력, `judge_2263b246/`·`judge_7ea78232/`, `j9_runs/56849248/impl_cases_a1/`와 4단계 감사 hand-back을 열지 않는다. 메인은 경로 2를 시작하기 전에 이 경로들을 블라인드 목록에 다시 넣는다."

### [커밋 전 수정][T] M-9. O8-13의 시각과 범위 문장이 부정확하다
- 근거
  - 142행 "4단계 실행은 15:59~16:02(`impl_cases.done`)였다": 이것은 cases 단계 시각입니다(`.done` started 15:59:16, done 16:02:02). 4단계 전체는 13:46:19~16:02:02입니다.
  - "판정 값을 보기 전"은 O8-20의 겹침(판정 전 점검이 낸 관문 내용과 겹치는 값)을 전제로 해야 맞습니다.
- 권장 문장: "4단계 cases 단계는 15:59~16:02였다 … 판정 값을 보기 전에 했다(다만 판정 전 점검 값이 관문 내용과 겹친 것은 O8-20)".

### [기록][C] R-1. P8-5의 "같지 않음" 9쌍의 실제 사유
- 23쌍 모두 라운드 수가 같습니다. 9쌍은 라운드별 `twist_stiffness_scale`이 비트 단위로 다를 뿐입니다(감사 재집계: `struct.pack('<d')` 비교).
- 64행 "라운드 수 또는 라운드별 스케일이 다름"을 "라운드 수는 23쌍 모두 같고, 9쌍은 라운드별 스케일이 비트 단위로 다름"으로 고치기를 권합니다.
- D-2 문서는 sha로 인용되므로 고치지 않습니다.
- (선택) 비선택 9쌍도 두 팔의 `commands_sha256`이 같습니다.
  - 적는다면 "기록, 규칙상 판정 쌍이 아니며 통과 근거로 쓰지 않는다"를 붙입니다.
  - 넣을지는 control·사용자가 정합니다. 결과를 본 뒤 P8-5를 다르게 읽는 근거로 쓰이지 않게 하려면 넣지 않는 쪽도 정당합니다.

### [기록][C] R-2. P8-16 재집계 방식
- 작성자 재집계는 키 없는 다중집합 대조입니다(`recount_stage4.py:173-192`). 규칙 377행은 "키별 기준 표(팔, 키, `commands_sha256`)"를 요구합니다.
- 감사가 키별로 다시 셌습니다. 키는 (팔, 플랜트, job − {mask, t4h_dir, setting} 또는 r79 `key`)입니다. 결과는 54/54 같음, run에만 0, 기준에만 0, 중복 키 0입니다.
- 5.2 200행에 "키별 대조(감사 재집계)도 54/54"를 더하기를 권합니다.

### [기록][T] R-3. T8″ 시각이 커밋 시각이 아니다
- 3절 124행의 T8″ `5955f25b` 01:28:23은 author date입니다. committer date는 01:58:21입니다. 나머지 판정 커밋은 두 시각이 같습니다.
- "(작성 01:28:23, 커밋 01:58:21)"로 적기를 권합니다.

### [기록][T] R-4. 23행 "13:46~16:06"
- `.done` 기준은 13:46:19~16:02:02입니다. 16:06의 출처를 찾지 못했습니다. 러너 로그 마지막 기록도 16:02:02입니다.

### [기록][I] R-5. 판정 전 `__pycache__` 정리를 공개하지 않았다
- 정식 P8-4는 20:38에 잠긴 `ed8-judge4`에 `__pycache__` 13개를 남겼습니다(`p84_suite_T8pppp_7ea78232/git_after.txt`).
- 메인이 같은 시각(transcript 11:38:21Z)에 `t8pppp_evidence/clean_pycache.py`로 지웠습니다. 그 뒤 20:44에 관문 판정을 했습니다. 이것은 verif 재감사 M-1(`verif_t8pppp_prejudge.md:18-28`)의 처리입니다.
- 3절에 한 줄로 적기를 권합니다. 판정 출력의 `is_clean`은 ignored 파일을 보지 않습니다.

### [기록][T] R-6. 블라인드 해제 시각
- 5.1 186행에 시각 20:50:46을 더하기를 권합니다. control-expert의 원자료 접근(20:54 KST)은 그 뒤입니다(transcript로 확인).

### [기록][R] R-7. 규칙 13절 공개 항목과 O8-1~O8-12를 옮기지 않았다
- 규칙 13절 공개 항목 1~20("판정서에 옮김")과 머리말 O8-1~O8-12가 이 판정서에 없습니다.
- judgement_checklist 결과: 규칙 항목 53개 가운데 대부분이 ambiguous이고, missing 1개(7.5 `ho_k_selection.json`)는 G′ 판정서 몫입니다.
- 4단계 판정서가 이를 맡지 않는다면 4절 첫머리에 다음을 한 줄로 적기를 권합니다: "13절 1~20과 O8-1~O8-12는 판 8 최종 판정서에 옮긴다(이 문서는 4단계 관문만)."

### [기록][T] R-8. O8-20에 더할 겹침
- 판정 전 점검은 C-J 단위 판정·C-S `unit_verdicts`·G′ 줄 읽기 함수를 4단계 줄에 메모리에서 돌려 "판정 가능 수"를 냈습니다(`prejudge_report.md:58·66·70`).
- 통과·실패 수는 아닙니다. 그래도 O8-20 (바)로 적기를 권합니다.

### [기록][R][추정] R-9. l1ref의 출처별 정체성 값
- 판 7 정오 1 "판정서에 옮길 것" 6(`jp3_remedy_spec_v7_erratum1.md:234`, l1ref `runs.<stem>.identity_sources`)이 판 8 l1ref 관문에 이어지는지 문면이 분명하지 않습니다. 판정서 71행은 l1ref 근거를 "판 7 정오 1 1-9"로 적습니다.
- 이어진다면 `judge_7ea78232/l1ref.json`의 해당 키를 인용하는 한 줄이 필요합니다(확인 필요 2).

## 규칙↔도구 대조표(판정서 1절)
| 행 | 규칙 | 판정서 분류 | 판정 출력 | 감사 판단 |
|---|---|---|---|---|
| P8-10 | 371 | 통과 2/2 | scope.done exit 0, junit 2/2 | 맞음 |
| P8-4 | 364 | 통과(사슬) | 정식 junit | **B-1, M-2** |
| P8-0 3a | 361, 10:346 | 판정 불가 → 대체 | `judge_2263b246/p80.json` failed, jobs 27, equal 27, `run line problems: 174`, `reference: 27 jobs, 114 expected` | 맞음(D-2 1) |
| P8-0 3b | 361 | 통과 | 114/114 | 맞음. 8 job 인용 빠짐(M-3) |
| P8-5 | 365 | 판정 불가(멈춤) | 23쌍, 14 < 15 | 맞음(사유 문구는 R-1) |
| P8-8 | 368 | 통과 | 23쌍, 6 ≥ 5 | 맞음 |
| P8-15 | 376, 10:345 | 통과 + 기록 실패 (1) | 27쌍, 21 ≥ 20, unread KM0 4 | 맞음(닫힌 목록 (1) = 3.8 기록 키) |
| P8-6 | 366 | 통과 | junit 1/1 | 맞음(재실행 junit으로 다시 확인) |
| P8-16 | 377 | 통과 | 54/54 | 맞음(키별 R-2) |
| P8-1 | 362 | 통과 | 22, 차이 0, 대체 쌍 0 | 맞음 |
| P8-2 | 363, 9:332 | 경로 1 통과, 경로 2 대기 | 10줄, breach 0 | 맞음(결정 4단계-2) |
| l1ref | 201 | 통과 | 167/167/102/102 | 맞음 |
| P8-11 | 372 | 통과 | diff 24파일, 모두 04_scripts·05_tests | 맞음(`git diff --name-only` 재확인) |

- 4단계 상태: D-2 4·5의 "미완"과 종합 표기가 0·2절에 맞게 반영됐습니다(40-44·105-109행).
- 상태 순서(10:338)를 적용하면 `not_judgeable`입니다.

## 재집계 표(C축, 감사 독립 스크립트, 판정 모듈·작성자 스크립트 import 없음)
| 항목 | 판정서·출력 값 | 재집계 | 차이 | 판단 |
|---|---|---|---|---|
| P8-0 줄·키·같음 | 114/114/114, 차이·결측·남음 0 | run·기준 각 114줄, 오류 0, 중복 0, 같음 114 | 0 | 같음 |
| P8-0 setting 분포 | 27·27·15·15·15·15 | 같음 | 0 | 같음 |
| P8-16 | 54/54 | 키별 54/54, 팔 B 27·L2 27 | 0 | 같음 |
| P8-5 | 짝 23, 판정 14 | 짝 23, 선택 14, 비선택 9, 기록 없음 0, 차이 0 | 0 | 같음 |
| P8-8 | 짝 23, 판정 6 | 짝 23, 선택 6, 차이 0 | 0 | 같음 |
| P8-15 | 짝 27, 판정 21, unread 4 | 선택 21, 비선택 2, 기록 없음 4(KM0) | 0 | 같음 |
| P8-1 | 22, 차이 0, 대체 0 | job 22 완결 22, 대체 0, 차이 0, 해시 없음 0 | 0 | 같음 |
| P8-2 | 10줄, rev 7 ×10, breach 0 | 오류 0, 기록 10, 세 breach 필드 결측 0·합 0, 태그 단일 | 0 | 같음 |
| l1ref | 167/167/102/102 | 같음, 태그 단일, 오류 줄 0 | 0 | 같음 |
| `.done` 9개 | exit 0, `previous_attempts` 빈 목록 | 같음, sha 8개가 출력의 `step_done_sha256`과 같음 | 0 | 같음 |
| P8-4 사슬 | 8782/8789/8741/9054/9071, 비통과 136 = 136, 117(건너뜀 116·실패 1), 핵심 0, NOTSET 3, only_B 17 통과, changed 0, `test_ed8_*` 354 통과 | 모두 같음 | 0 | 같음(M-2 표기만) |
| 인용 sha 34개 | 판정서 각 칸 | 앞자리 모두 일치 | 0 | 같음 |

## P8-4가 끝난 뒤 판정서에 넣을 것(5.4 신설)과 판단 기준
1. **종료와 상태**
   - `out\p84.done` `exit=`. full_suite 규약은 0 통과 / 1 실패 / 2 판정 불가 / 3 오류입니다.
   - driver log `[run] end exit=`와 `[after] status lines=… pycache lines=… head=`.
2. **`out\suite_judgement.json`**
   - `status`.
   - `findings.new_failure`·`core_not_passing`·`new_skip_or_xfail`가 모두 `[]`인지.
   - `inputs.baseline_list.sha256`이 `7fce20f4…`인지.
   - `inputs.junit.sha256`을 다시 잰 값이 `out\junit.xml`과 같은지.
   - `counts`, `existing_failures_record`.
   - 기대: 실패는 기준선 기존 2개(`test_d8x_diag`, `test_record`)뿐, 건너뜀은 기준선 꼴. `test_coupled_batch_rows_and_resume`는 통과해야 합니다.
3. **`out\suite_record.json`**: side run, worktree `ed8-judge4`, head 7ea78232, `worktree_tests_exit`.
4. **`out\worktree_tests.md` 머리**
   - probe가 `outrigger_sim` worktree인지.
   - "원본 불변 True", "실행 폴더 삭제 False".
   - "바뀐 데이터 경로 N회"(C8 원형 47회)와 시험 수.
5. **관문 시험**: `junit_skips.py out\junit.xml --critical` 결과에 `critical_skipped`·`critical_absent`·`xpassed`가 0이어야 합니다. 정규식 대상:
   - `test_p86_first_round_scale_stiffness_equals_the_replay`
   - `test_p8_10_`
   - `test_ed8_run_path`
   - `test_ed8_gate_p80_key`
   - `test_ed8_impl::test_psw_stuck_reads_move_the_scale_mid_and_keep_k1`
   - `test_ed8_impl::test_psw_fields_are_read_by_the_scale_update_only`(N-1 전제 둘)
   - `test_ed8_harness::test_switch_off_runs_keep_the_stored_hashes_and_keys`(P8-0 8 job)
   - 이것이 필요한 이유: 핵심 패턴(ed6 정오 2 2-2)에는 `test_ed8_*`가 없습니다.
6. **정식 실행과 대조**: `test_ed8_*` 354개의 상태가 T8⁗ 정식 junit과 같은지 봅니다. 다르면 그 자체가 발견입니다.
7. **원형 C8 run과의 조건 동일성**(같으면 "같음", 다르면 기록)
   - 같음
     - `full_suite_ed8.ps1`(ed8-impl, C8 바이트)
     - `worktree_tests.py`(sha256 앞 `991c3833`, mtime 11-25 — 끝난 뒤 다시 잼)
     - 기준 목록 sha, Chrono-dev, 직렬 실행, affinity 없음
   - 다름
     - numba 캐시: 원형은 base 쪽과 공유해 미리 채워진 캐시, 이번은 새 폴더.
     - 대상 worktree: 원형은 새 detached `ed8-suite-c8`, 이번은 잠긴 판정 checkout(시작 시 `--ignored` 0줄).
     - 메인 자료 시점: 13:45 → 21:16.
8. **실패 처리**
   - status failed: P8-4 판정 실패입니다. 상태 순서상 4단계는 "판정 실패"가 됩니다. 멈추고 묻습니다. 다시 돌리지 않고, 사슬 근거로 대체하지 않으며, C8 교체는 승인 뒤에만 합니다.
   - exit 2·3: 판정 불가·오류로 적고 보고합니다.
9. **근거 폴더와 정리**
   - `out\` 전체, runner ps1, driver log, run_console.log를 새 근거 폴더로 복사하고 SUMS를 씁니다. 61행에 suite_judgement·junit·SUMS sha를 인용합니다.
   - `__pycache__`가 남았으면, 6·8~10단계 판정 전에 경로를 지정해 지우고 기록합니다.

## 7절 처리 순서 제안(판 7 7.5 꼴 + 결정 4단계-3)
1. P8-4 재실행이 끝날 때까지 기다리고, 위 5.4를 넣습니다(B-1).
2. `large_outputs.py j9_runs\56849248 --backup ~\.claude\backups\outrigger-ed8\j9_runs_56849248\`는 건식으로 이미 봤습니다. 이제 `--apply`를 돌립니다.
   - 결과: `j9_runs/56849248_LOCAL_ONLY.SHA256SUMS`(3개), exclude 2줄(`L1_VBN.json`·`L1a_VBN.json`), 백업과 sha 확인.
   - **`git add`보다 먼저** 해야 200 MB 파일이 스테이지에 올라가지 않습니다.
3. ignore에 걸린 한도 안 파일 909개(npz 906 + partial 3)는 결정 3("npz는 LOCAL_ONLY 목록과 백업")대로 처리합니다.
   - 처리: 같은 LOCAL_ONLY 목록에 더하거나 별도 목록을 만들고, 백업에 복사합니다. S8-R 머리말의 `ed8_design_LOCAL_ONLY.SHA256SUMS`(npz 196)가 선례입니다.
   - sha를 한 번에 고정하는 방법: `baseline_check write-sums j9_runs\56849248 --recursive --name RUN_ALL.SHA256SUMS`. 감사 건식 결과는 entries 1047, would_write입니다. 기존 단계 SUMS(인용됨)는 고치지 않습니다.
   - 도구 공백: `large_outputs`가 `needs_add_force` 파일을 목록에 넣지 않는 점은 tools 후보로 올립니다.
4. `judge_2263b246/`·`judge_7ea78232/`·`_identity_checks/`에 SUMS를 씁니다. 3의 RUN_ALL을 쓰면 3을 이 단계 뒤로 옮깁니다.
5. ed8_design 근거 폴더 SUMS: `stage4_prejudge`, `_t8ppp`, `_t8pppp`, P8-4 재실행 근거 폴더, 4단계 러너 사본. `stage4_judgement`는 md를 확정한 뒤에 씁니다.
6. `audit_t8ppp` SUMS와 이 감사 hand-back 폴더(예: `ed8_design/audit_stage4_judgement/`) SUMS는 맨 마지막에 씁니다.
7. `git status --ignored`로 확인합니다. ignore에 걸린 것이 npz 906·partial 4·한도 초과 2뿐이고, 나머지 인용 파일(판정 출력, 단계 jsonl·SUMS, junit, 판정서)은 ignore에 걸리지 않아야 합니다.
   - 감사 확인: 근거 폴더 15곳에 ignored 0개. `p80.json`·`ed7_probe_a2.jsonl`·`impl_cases.done`·판정서 md는 ignore에 걸리지 않음. `-text` 속성 걸림.
8. integrity-checker → 커밋 순서로 갑니다.

## 확인 필요
1. 경로 2(P8-2) 넘김에 "사례 E·F" 행을 정하는 정의 문장이 들어가는지. 판 7 정오 1 1-7 "E·F × {VBM, LSM1~4} 10줄"의 E·F 정의 원천이 그 문장입니다. 규칙 9:333 목록에 없으면 경로 2가 경로 1 출력 없이 10줄을 고를 수 없습니다(control-expert).
2. R-9: 판 7 정오 1 "판정서에 옮길 것" 6(l1ref `identity_sources`)이 판 8 l1ref에 이어지는지.
3. R-1 (선택): 비선택 9쌍의 명령 해시 같음을 기록으로 적을지(사용자).

## 위임 필요
- python-expert(`tools/verif` 후보 2건)
  - (1) `large_outputs.py`: `needs_add_force` 파일(ignore에 걸린 한도 안 파일)도 LOCAL_ONLY 목록·백업에 넣는 옵션. 입력은 실행 폴더, 출력은 목록·백업, 종료 0/1/2.
  - (2) [추정] `transcript_scope.py`: blind_guard가 막은 호출(tool_result의 "PreToolUse … blind_guard 차단")을 별도 분류로 보고. 이번에 임시 절대경로 목록으로 돌렸을 때 메인 09:59:27Z 차단 1건과 verif 차단 2건이 나오지 않았습니다. 목록 root가 scratchpad였던 탓일 수 있습니다.
- control-expert: B-1, M-2~M-4, M-6, M-7, M-8, M-9와 R-1~R-8의 문장 수정.

## 메인 세션 권고
- P8-4 재실행은 건드리지 마십시오. 끝나면 `out\` 복사 → `junit_skips --critical` → 5.4 작성 순서로 진행합니다.
- 7절 처리 순서 2~7은 메인이 실행합니다.
- 경로 2(P8-2·census) 시작 전에 M-8의 경로를 블라인드 목록에 다시 넣으십시오.

## 검사하지 못한 것
- P8-4 재실행 결과(실행 중).
- O8-21(판정 전 점검 python-expert)과 그 이전 단계의 transcript. 이 세션 subagent 폴더의 12:00 이후 기록에는 없었습니다(다른 세션으로 보임).
- 4단계 러너 `run_stage4.ps1`의 lint. 이미 실행이 끝났고 결정 3으로 사본만 넣습니다.
- `j9_runs/56849248` 전체 1047파일 794 MB 수치는 다시 재지 않았습니다(RUN_ALL 건식 entries 1047만 확인).
- 판정 도구 코드 자체는 이번 범위에서 다시 읽지 않았습니다. 앞 재감사(verif_t8pppp)가 맡은 부분입니다.

## 실행한 검증
- 인터프리터: python-dev `-I -B`(`-X utf8`, `MKL_THREADING_LAYER=TBB`). 프로젝트 모듈·판정 모듈은 import하지 않았습니다.
- 도구와 종료 코드
  - `depcheck`: STAMP.
  - `seal_check`(규칙): 종료 0.
  - `judgement_checklist`(규칙·D-2·결정 4단계·control_p80p85 대 판정서): 종료 1, missing 1(G′ 몫).
  - `baseline_check sums` 단계 9개: mismatch·missing 0, unlisted 958.
  - `baseline_check write-sums --recursive --dry-run`: would_write 1047.
  - `large_outputs` 건식: over_limit 3, exclude_missing 2, needs_add_force 909.
  - `log_errors`(stage4 로그): 종료 0. 단, "errors N" 줄이 없어 공허한 검사입니다.
  - `transcript_scope`: 이 세션 15개 transcript, bash_pipe 6건.
- git 조회: `log`, `diff --name-only`, `merge-base --is-ancestor`, `worktree list`, `check-ignore -v`, `check-attr`, `status --porcelain --ignored --untracked-files=all`(근거 폴더).
- 즉석 스크립트(scratchpad `verif-s4judgement\`, 모두 지움, `Test-Path` False)
  - 구조 엿보기 3개: 키 이름·형만.
  - `recount_audit.py`: 독립 재집계.
  - `shas.py`: 인용 sha 34개.
  - `junit_audit.py`·`junit_notset.py`: junit 사슬.
  - `tr_blocks.py`·`tr_find.py`·`tr_one.py`: transcript에서 명령·시각만.
  - 임시 블라인드 목록 `tsrepo\.claude\blind_paths.json`.
- **읽은 파일**
  - 판정서 전체, 규칙 전체(1-459행), 결정 3개, `p80p85_decision_draft.txt` 전체, `control_p80p85.md` 155-256행.
  - `prejudge_report.md` 1-82·201-230행.
  - `verif_t8ppp_prejudge.md` 59-63·462-466행, `verif_t8pppp_prejudge.md` 386-392행, `verif_p80p85_postjudge.md` 2·204행.
  - 판 7 판정서 314-333행, 판 7 정오 1(Grep "1-9").
  - `judge_7ea78232` 8개, `judge_2263b246\p80.json`, `.done` 9개.
  - P8-4 근거 폴더 소형 파일, `full_suite_ed8.ps1`(ed8-impl, 읽기만), 러너 `p84wt_runner.ps1`·driver log(읽기만), stage4 러너 로그.
  - 원자료 jsonl·json: 스크립트로 건수만.
- **검색 범위**
  - Grep: 단일 파일, `ed8_design`(glob `*.md`·`*.{md,ps1}`), `audit_t8ppp`(`*.md`), `ed8-judge4\05_tests\unit`(`test_*.py`·`test_ed8_*.py`), `tools\verif`(`*.py`).
  - Glob: projects 폴더의 세션 jsonl 1개.
  - `Get-ChildItem`: `j9_runs\56849248`와 단계 폴더(해제 뒤), runner 폴더.
  - `j_p3_cause` 루트·`06_analysis`·worktree 루트는 검색 범위로 쓰지 않았습니다. 경로 2 도구는 열지 않았습니다.
- **쓰기**
  - 메모리 `audit_pitfalls.md`에 1항목을 더했고, `MEMORY.md` 색인 줄을 늘렸습니다.
  - 잠긴 worktree, 실행 중 러너, `ed8-judge4`·`ed8-impl`에는 쓰지 않았고, 프로세스도 종료하지 않았습니다.
- **재확인**: 보고 직전에 판정서 sha 25ce1bbc(변화 없음), 러너 미완(`p84.done` 없음), `audit_t8ppp` 8개를 확인했습니다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v8_rules.md 35f9eba8…, jp3_remedy_spec_v8_rules.md.sha256 e19aaa48…, compare_t8ppp_t8pppp_rerun.txt 8d09c700…, junit_critical_stage4.json 0f8cdb49…, junit_critical_stage4.py b0523d21…, p84_baseline_chain_stage4.json 23eec0b7…, p84_baseline_chain_stage4.py 97cc7bda…, recount_stage4.json c39c689e…, recount_stage4.py 47bc2c37…, stage4_judgement_ed8.md 25ce1bbc…, decision_d1_cd_scope_20261127.md 6624affe…, decision_d2_p80p85_20261127.md 0a636250…, decision_stage4_judgement_20261127.md fd79bb76…, integrity_t8ppp_precommit.md 2f8ceab5…, integrity_t8pppp_precommit.md b74feaa8…, verif_p80p85_postjudge.md a17bcebd…, verif_t8ppp_prejudge.md e07f643d…, verif_t8pppp_prejudge.md 872bfe14…, cases.json c703af50…, l1ref.json 810fa864…, p80.json abb49dee…, p815.json 5200d180…, p816.json 51d7a2da…, p85.json 9145e6ed…, p88.json ddcd12cb…, t8.json ece1a400…, cases.json 54999935…, l1ref.json 20815752…, p80.json 1077f3ab…, p815.json 990b985a…, p816.json b14d770b…, p85.json 8db37778…, p88.json 39c7909c…, t8.json eb0c4aef…, impl_cases.done 99332bc9…, impl_p80.done 20eddc46…, impl_p815.done c772b1bd…, impl_p816.done be22836b…, impl_p85.done 2b6e3255…, impl_p88.done 2235acd2…, impl_scope.done e805b3f9…, impl_t8.done a774f422…, l1ref.done 4ace3004…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
