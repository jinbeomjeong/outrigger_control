# 436.9 판 8 4단계(구현 확인) 판정서 — 실행 C8 `56849248` · 판정 T8⁗ `7ea78232`

작성: control-expert, 2026-11-27. **상태: 초안 개정 5(무결성 점검 문구 4건).** 개정 5는 integrity-checker 커밋 전 점검의 문구 결함 4건만 고쳤다(머리말, 2.2 끝 줄, 7절 표, 8.1 끝 줄). 개정 4는 커밋 전 감사 반영 + 확인 필요 A·B 결정 반영 + 짧은 재감사 반영이었다. 개정 2는 7절(npz 백업·LOCAL_ONLY 909줄, 러너 사본), 4.2(O8-34·O8-35), 8.2, 9절, 10.2만 바꿨다. 개정 3은 6.1(E·F [정의] 고정)과 8.2 A만 바꿨다. 개정 4는 재감사 `ed8_design/audit_stage4_judgement/verif_stage4_judgement_recheck.md`(`325b03fd…`, 차단 0)의 M′-1~M′-4와 R′-1~R′-6을 반영했다(0절 52행, 4.2 O8-32·O8-36~O8-38, 5.4 (4), 6절, 7절, 9절, 10.3). 앞 초안(sha `25ce1bbc…`)에 판정 후·커밋 전 감사 `ed8_design/audit_stage4_judgement/verif_stage4_judgement_precommit.md`(`1624f762…`)의 차단 B-1, 커밋 전 수정 M-2~M-9, 기록 R-1~R-9와 사용자 결정(결정 4단계-1~4, 열린 확인 사항 4건 = 감사 확인 필요 3건 + 도구 개선 범위 1건, 2026-11-27; 그 뒤에 생긴 8.2 A·B도 사용자 결정으로 닫힘)을 옮겼다. 판정을 새로 내리지 않았다. P8-4만 결정 4단계-1에 따라 재실행 결과로 판정했다(5.4). 커밋 전에 integrity-checker 점검을 받는다. 봉인 규칙은 바꾸지 않는다. 5단계는 시작하지 않는다(사용자 범위: 4단계 판정서까지).

의존성 점검: 생략했다. 이 판정서에는 제어 수치 계산이 없다. 재집계는 python-dev `-I -B`로 건수만 셌다. Python과 Julia로 비교할 수치가 없으므로 Julia 교차 검증은 해당하지 않는다.

## 머리말

### 기준 문서·결정
| 문서 | sha256 | 관계 |
|---|---|---|
| 봉인 규칙 `j_p3_cause/jp3_remedy_spec_v8_rules.md`(S8-R 개정 3, master `2715230e`) | `35f9eba8f98f93ddb0fa850ff60844ebd7a443f819febcdf0906a5502c121520` | 판정 기준 |
| D-1 결정문 초안 `ed8_design/control_d1_settings/d1_decision_draft.txt`(폴더 SUMS `134c0766`) | `4cf82f2cd8e84a981b95cce1336c895c2a853345e8ea94dabd0a0b3a62420b68` | 판 8 J-P3 판정 10설정. 판정 정의는 바뀌지 않음. 정오가 아님 |
| D-1 보충 `ed8_design/audit_t8ppp/decision_d1_cd_scope_20261127.md` | `6624affef203ba31eff9bbcf938c6f03bd1de19b069113354efe7fe84a073fd7` | C-D J-P3 24줄, 판정 env dynamics-dev, P8-4 env Chrono-dev |
| D-2 결정 `ed8_design/audit_t8ppp/decision_d2_p80p85_20261127.md` | `0a636250b69afe3bc080220701de1d51ffa25511cd281f6801f0e0a330c69808` | P8-0·P8-5 처리, 4단계 미완 규칙, 종합 표기 |
| D-2 결정문 초안 `ed8_design/control_p80p85/p80p85_decision_draft.txt`(폴더 SUMS `d83d6cba`) | `fd85d7f83b33d09a39eee5e4de3cd547df16fd4d8c721d3483169b0774c4d417` | 9절 공개 문장 |
| control 해석 `ed8_design/control_p80p85/control_p80p85.md` | `61e7ae2e4ff4d657764e689d6a5df6b1d56bd9b8024d3c973460c9a2a0422288` | 208행 읽기, 4절 영향, 6절 공개 |
| 4단계 판정서 결정 `ed8_design/audit_t8ppp/decision_stage4_judgement_20261127.md` | `fd79bb76a6490ed9f6f5e1467b949d80d53fbe5bdf028046fd1860060b59cd1d` | 앞 초안 8절 확인 필요 1~5 결정(이 문서에서 "결정 4단계-n"으로 인용). 1: P8-4를 규칙 기준선 직접 대조로 판정, 2: P8-2 경로 2는 census 경로 2와 함께 S8-C 전, 3: 실행 출력 커밋은 판 7 7.5 꼴, 4: 공개 번호 O8-13~, FS24·G4 `effective_shape`는 G′ 판정서 기록 칸 |
| 커밋 전 감사 `ed8_design/audit_stage4_judgement/verif_stage4_judgement_precommit.md` | `1624f7627d13fe2c5bf3bdfb6c0f07c97d8329553e4c612a6e36e07c91ec0210` | 차단 1·커밋 전 수정 9·기록 9. 반영 위치는 각 절에 "감사 B-1"처럼 적었다. 이 보고에는 P8-2 경로 1 사례 행 이름과 건수가 들어 있어 경로 2 작성자에게 넘기지 않는다(6절) |

### 판정 정체성
| 항목 | 값 |
|---|---|
| 실행 커밋 C8 | `56849248371b4916e2fe683265e7abffdd6fb8d7`(worktree `ed8-impl`, locked). `03_src` tree `ed797e8e…` |
| 4단계 실행 | 2026-11-27 13:46:19~16:02:02 KST(`.done` 기준, 러너 로그 마지막 기록도 16:02:02. 앞 초안의 "16:06"은 출처가 없어 고쳤다, 감사 R-4), 9단계(scope·l1ref·p80·p816·p85·p88·p815·t8·cases). 모든 `.done`은 exit 0이고 `previous_attempts`는 비어 있다 |
| 판정 커밋 T8⁗ | `7ea782323c427917709ecbb365a58044449beac2`(worktree `ed8-judge4`, locked). 부모는 T8‴ `2263b246` |
| 관문 판정 | 2026-11-27 20:44:44~20:44:56. dynamics-dev `python.exe -I -B`, 스크립트 `stage4_prejudge_t8pppp/run_stage4_gates_t8pppp.ps1`(`512c556b`), 출력 `j9_runs/56849248/judge_7ea78232/` |
| P8-4 판정 실행(5.4) | T8⁗ 깨끗한 판정 checkout `ed8-judge4`에서 규칙 기준선과 같은 방식(`full_suite_ed8.ps1 -Side run` → `tools/verif/worktree_tests.py`, main 자료 붙임, Chrono-dev 직렬 pytest, affinity 없음) 2026-11-27 21:15:59~23:04:37 KST(wall 6518 s). 러너 `ed8_design/p84_suite_T8pppp_wt_7ea78232/p84wt_runner.ps1`(`c57c887e…`), 판정 기준 목록 `p84\base\existing_failures.txt`(`7fce20f4…`) |
| P8-4 정식 실행(보조, 5.3) | T8⁗ 2026-11-27 20:13:39~20:38:02. Chrono-dev, `pytest 05_tests/unit -n 12 --dist loadfile -p no:cacheprovider`, P 0xFFFF 고정(예약 `r-20261127201336-5670fa`). 판정 worktree에서 pytest만 돌린 꼴이라 규칙 기준선과 방식이 다르다 |
| 대체된 판정 | T8‴ `2263b246` 출력 `j9_runs/56849248/judge_2263b246/`(18:54:00~18:54:14). 보존하고 "대체됨"으로 적는다 |

### 기호
| 기호 | 뜻 |
|---|---|
| $n_{pair}$ | 팔 짝 관문에서 두 팔이 모두 1줄씩 있는 (플랜트, 행) 쌍의 수 |
| $n_{same}$ | 규칙 문면의 선택 조건을 만족해 명령 해시를 대조한 쌍의 수(도구 `judged_pairs`) |
| $n_{min}$ | 관문별 최소 쌍 수. P8-5 15, P8-8 5, P8-15 20(규칙 365·368·376행) |
| $N_{eq}$ | 줄별 `commands_sha256`가 기준과 같은 줄의 수 |

판정 불가 조건: $n_{same} < n_{min}$ (10:346, 12절 해당 행).

## 0. 판정 요약
- **4단계 상태는 미완이다.** 상태 순서(10:338 "판정 실패 > `setting_defect` > `not_judgeable` > 통과")로 단계 상태를 정하면 `not_judgeable`이다. 실패는 0, `setting_defect`는 0, 판정 불가는 1(P8-5)이다.
- **판정 출력 8개(T8⁗)**: 통과 7(p80, p816, p88, p815, t8, cases, l1ref), 판정 불가 1(p85: $n_{same}$ 14 < 15).
- **시험 묶음 관문**: P8-4는 규칙 기준선 직접 대조(T8⁗ worktree_tests 방식, 결정 4단계-1)로 판정한다(5.4). 결과는 통과다(`suite_judgement.json` status pass, 새 실패·핵심 미통과·새 건너뜀 0). P8-6·P8-10·P8-11 재확인도 통과다.
- **요약 문구(조건부 표기)**: "4단계 관문 가운데 판정 출력 7개와 시험 묶음 관문(P8-4·P8-6·P8-10·P8-11)은 통과, P8-5는 판정 불가. 따라서 4단계는 미완이다. P8-2는 경로 1 통과, 경로 2 대조 대기다." 조건 없는 "4단계 통과"는 쓰지 않는다.
- 결정 D-2 4에 따라, 4단계 관문 가운데 하나라도 판정 불가이면 4단계는 미완이다. 그래서 멈추고 묻는다. **5단계 진행은 사용자가 정한다.**
- C8 교체 질문(201행) 대상은 아니다. 실패와 `setting_defect`가 없기 때문이다.
- **재집계(5절)**: 8개 관문의 핵심 건수를 원자료에서 독립 코드로 다시 셌고, 판정 출력과 모두 같았다. 정체성(head·is_clean·규칙 sha·실행 커밋)과 입력 sha(`.done`·출력·기준)를 다시 재어도 모두 일치한다. 커밋 전 감사의 독립 재집계도 모든 핵심 건수가 같았다(감사 C축 표).
- **경로 2**: P8-2(사례 재생)의 J-P3는 경로 2 범위(9:332)에 든다. 경로 2 대조는 census 경로 2와 함께 S8-C 전에 한다(결정 4단계-2). 그때까지 P8-2는 "경로 1 통과, 경로 2 대조 대기"다(6절).
  - 정정: 제 앞 문서 `control_p80p85.md` 7절의 "더할 [정의] 문장 없음"은 P8-0·P8-5에만 맞는 문장이다. 4단계 전체에 대한 답이 아니다.
  - 경로 2 넘김 문장(6.1)에서 "사례 E·F"의 정의 문장을 봉인 규칙 v8 안에서 찾지 못했고, 판 7 정오 1 108행과 v8 363행 원문을 나란히 인용해 6.1에 고정했다(8.2 A 결정됨).
- **P8-4 방식 차이(5.3, 보조)**: 규칙 기준선(C8의 부모 `41e107e9`)은 `worktree_tests.py`로 main 자료를 붙여 돌렸고, T8‴·T8⁗ 정식 실행은 판정 worktree에서 pytest만 돌렸다. 그래서 정식 실행을 기준선과 바로 대조하면 비통과가 117개 더 있다(사유는 모두 "자료 없음", 핵심 패턴 시험 0개). 이 차이 때문에 결정 4단계-1로 같은 방식의 재실행(5.4)을 했고, 사슬 근거는 보조로 둔다.

## 1. 관문별 표

4단계 행(4절 201행)의 순서를 따른다. 상태 칸은 도구 `status`다. 종료 코드 규약은 pass 0 / failed 1 / `setting_defect`·`not_judgeable` 2다. 근거 경로는 `j_p3_cause/` 아래 상대 경로다.

| # | 규칙 행 | 관문 | 도구 출력 | 규칙 분류 | 핵심 수 | 근거 | sha256 앞 8자 |
|---|---|---|---|---|---|---|---|
| 1 | 12 P8-10 (371) | C8 범위, census 키 재생성 | `impl_scope.done` codes.scope "41e107e9 → 56849248 in scope", exit 0. P8-4 안의 `test_ed8_run_commit::test_p8_10_regenerated_files_have_the_sealed_sha256`, `…_equal_the_sealed_folder` 2/2 통과 | 통과 | 2/2 | `j9_runs/56849248/impl_scope.done`, P8-4 junit(5.4, 정식 junit에서도 통과) | `e805b3f9`, junit `dfe7fc14`(정식 `f6696c14`) |
| 2 | 12 P8-4 (364) | 단위 시험 전부(기준선은 C8의 부모에서) | **규칙 기준선 직접 대조(5.4)**: `suite_judgement.json` status `pass`, p84.done `exit=0`. 시험 9119, 통과 9102, 실패 2(`test_d8x_diag::test_rerun_gives_the_stored_command_hash`, `test_record::test_default_snapshot_directory_is_results_states`, 둘 다 기준선 목록 failed), 오류 0, 건너뜀 15(모두 기준선 목록에 있음). `new_failure`·`core_not_passing`·`new_skip_or_xfail` 모두 `[]`, 기준 목록 sha `7fce20f4…`. `test_hydraulics_flow_limit_run::test_coupled_batch_rows_and_resume` 통과 | **통과**(규칙 기준선 직접 대조, 결정 4단계-1). 사슬 근거는 보조(5.3) | 5.4 표 | `ed8_design/p84_suite_T8pppp_wt_7ea78232/` | SUMS `47a0b484`, suite_judgement `c7011ae5`, junit `dfe7fc14` |
| 2b | (보조) | T8⁗ 정식 실행 | 9071개, 통과 8935, 실패 2(`test_d8x_diag::…`는 규칙 기준선의 기존 실패, `test_coupled_batch_rows_and_resume`는 기준선 통과이고 판정 worktree에 `07_results` 자료가 없어 실패 — 5.3의 117개 중 1), 오류 0, 건너뜀 134. T8‴ 정식 대비 only_A 0, only_B 17(새 시험, 모두 통과), changed 0 | 판정 근거 아님(보조) | 5.3 표 | `ed8_design/p84_suite_T8pppp_7ea78232/` | SUMS `afc9330a`, junit `f6696c14`, 대조 `junit_compare_T8ppp_formal_vs_T8pppp_formal.txt` |
| 3a | 12 P8-0 (361) | 옛 설정 명령 불변 114줄, **T8‴ 출력** | `failed`(종료 1): jobs 27, equal 27, differing 0. failures "run line problems: 174", setting_defect "reference: 27 jobs, 114 expected" | **판정 불가**(10:346. 판정 도구 줄 키 결함으로 87/114줄 미비교) → T8⁗로 대체 | 비교된 27줄은 기록만 | `j9_runs/56849248/judge_2263b246/p80.json`, 감사 B-1 | `1077f3ab` |
| 3b | 12 P8-0 (361) | 같음, **T8⁗ 출력** | `pass` | 통과 | jobs 114, run_jobs 114, $N_{eq}$ 114, missing·extra·differing 0, 줄 문제 run 0·기준 0, `reference_compared` true. setting 분포 run = 기준 = {P7-M-a2 27, P7-Mslow-a2 27, P7-Mfast·Mc005·Mc04·L-a2 각 15}. 8 job 대조는 `test_ed8_harness::test_switch_off_runs_keep_the_stored_hashes_and_keys` 통과(P8-4 junit, 5.4; 감사 M-3) | `judge_7ea78232/p80.json`(기준 `j9_runs/b46bdf8f/repro_a2/ed7_probe_a2.jsonl` `d60306db` pinned) | `abb49dee` |
| 4 | 12 P8-5 (365) | PSW 켬·끔 23키 | `not_judgeable` | **판정 불가(멈춤)** | $n_{pair}$ 23, $n_{same}$ 14 < 15. 판정한 14쌍의 명령 차이 0(기록). unread·hashless·malformed·pairing 0. **판정되지 않은 쌍(기록)**: 9쌍. 사유: 라운드 수는 23쌍 모두 같고, 이 9쌍은 라운드별 `twist_stiffness_scale`이 비트 단위로 다르다(규칙 365행의 "같지 않음"). 근거: 원자료 `j9_runs/56849248/impl_p85_a1/p85.jsonl`(`91a00b30…`, 폴더 SUMS `21dc1a76…`), 사유 집계는 커밋 전 감사 R-1(`1624f762…`). 값은 옮기지 않는다(사용자 결정 2026-11-27) | `judge_7ea78232/p85.json` | `9145e6ed` |
| 5 | 12 P8-8 (368) | H3′ 켬·끔 23키 | `pass` | 통과 | $n_{pair}$ 23, $n_{same}$ 6 ≥ 5(여유 1), differing 0 | `judge_7ea78232/p88.json` | `ddcd12cb` |
| 6 | 12 P8-15 (376) | L-2 켬·끔 27키 | `pass` | 통과 + 기록 실패 (1) | $n_{pair}$ 27, $n_{same}$ 21 ≥ 20(여유 1), differing 0. r79 KM0 4쌍은 3.8 기록 키가 없어 판정 쌍에서 뺐다(10:345 기록 실패 (1). 판정 상태는 바뀌지 않음. 사용자 결정 B-1 (가) 2026-11-26, T8′에서 결과 전 구현) | `judge_7ea78232/p815.json` | `5200d180` |
| 7 | 12 P8-6 (366) | 1회차 $K1_{sc}$ 상대차 ≤ 1e-9 | P8-4 안의 `test_ed8_impl_harness::test_p86_first_round_scale_stiffness_equals_the_replay` 통과 | 통과 | 1/1 | P8-4 junit(5.4, 정식 junit에서도 통과) | `dfe7fc14`(정식 `f6696c14`) |
| 8 | 12 P8-16 시점 2 (377) | 검토 팔 재현, C8 재확인 | `pass` | 통과 | B_impl 27/27, L2_impl 27/27 equal, 합계 54/54, extra 0 | `judge_7ea78232/p816.json`(기준 `ed8_design/control_level_deadlock/probe_8a2a52ce/raw/runs.jsonl` `89efe66f` pinned) | `51d7a2da` |
| 9 | 12 P8-1 (362) | VBN = VBN0 해시(22쌍 키) | `pass` | 통과 | judged 22, differing 0, 대체 다리 기록 쌍 0 | `judge_7ea78232/t8.json`(main.jsonl `9ad74990` pinned) | `ece1a400` |
| 10 | 12 P8-2 (363) | 사례 E·F × {VBN, LSN1~4} 10줄 J-P3 | `pass` | **경로 1 통과, 경로 2 대조 대기**(6절, 결정 4단계-2) | 10줄(R12, VBN·LSN1~4 각 2), `J-P3_judged_rows` 10, rev 7 판정 10, jp3a·jp3b(over tol)·jp3c breach 0, `rev7_unjudged_setting_runs` 0, `rule_missing_runs` 0, ③ 조건 판정 줄 10(조건 읽기 117, breach 0), `identity_defects` 0 | `judge_7ea78232/cases.json` | `c703af50` |
| 11 | 8절 l1ref(판 7 정오 1 1-9) | L1 기준 정체성 | `pass` | 통과 | L1_VBN0 167, L1_VBN 167, L1a_VBN0 102, L1a_VBN 102줄, `identity_problems` 0. 태그 VBN0 `final_C4G2_LAS_K1_LSB_ED8`, VBN `final_C4G2_P3X_LAS_K1_LSB_ED8`. 출처별 정체성 값은 5.2 아래 표 | `judge_7ea78232/l1ref.json` | `810fa864` |
| 12 | 12 P8-11 (372), 3단계 관문 재확인 | T8 범위·실행 경로 바이트 | verif 재감사 R-4: 실행 경로 156파일의 C8 blob = T8⁗ blob, `diff 56849248 7ea78232`는 24파일이고 모두 04_scripts·05_tests 안이며 실행 경로 0. P8-4 안의 `test_ed8_run_path` 4/4 통과(5.4 재실행·정식 모두) | 통과 | 156/156, 4/4 | `ed8_design/audit_t8ppp/verif_t8pppp_prejudge.md` | `872bfe14` |

- 공통 정체성(8개 출력)
  - `judge_code.head` 7ea78232, `is_clean` true
  - `spec_v8_sha256` 35f9eba8
  - `inputs.rows.run_commit` 56849248
- 단계 `.done` sha(출력 `inputs.rows.step_done_sha256`과 재측정값 일치)
  - p80 `20eddc46…`, p816 `be22836b…`, p85 `2b6e3255…`, p88 `2235acd2…`, p815 `c772b1bd…`, t8 `a774f422…`, cases `99332bc9…`, l1ref `4ace3004…`
- 뒤 대조(D-2 결정문 5-3, 기록): p80을 뺀 7개 출력을 T8‴ 출력과 비교했다. status·status_basis·수 필드와 `judge_code`를 뺀 전체 보고가 같다.
  - 대조 스크립트: `stage4_prejudge_t8pppp/compare_stage4_t8ppp_t8pppp.py`(`8cfe3408`), 종료 0
  - 이 판정서 작성 중 다시 돌린 출력: `stage4_judgement/compare_t8ppp_t8pppp_rerun.txt`(`8d09c700`)

## 2. 4단계 상태와 남는 제한

### 2.1 상태
- 4단계 = **미완**(결정 D-2 4, 규칙 10:338). P8-5 행의 판정 불가에는 "(멈춤)"이 붙어 있다(365행).
- 4단계 멈춤 칸(201행)에는 판정 불가가 적혀 있지 않다. 그래도 관문 하나라도 통과가 아니면 단계는 끝나지 않은 것으로 읽는다(감사 M-3, D-2 결정문 6-3, 사용자 결정 D-2 4).
- 5단계 진행은 사용자 결정 대상이다. 판단에 쓸 정보는 다음과 같다(결정 아님).
  - 5단계는 V0만 돌린다(4절 210행). 그래서 P8-5(VBN 구성의 PSW)와는 무관하다.
  - 5·6단계 기준 V0의 타당성(옛 설정 명령 불변)은 P8-0에 기댄다. P8-0은 T8⁗에서 114/114로 통과했다.

### 2.2 P8-5 판정 불가가 남기는 제한(`control_p80p85.md` 4절, D-2 결정문 7절)
- **말할 수 없게 되는 것**
  - "4단계 구현 확인이 모두 통과했다"
  - "PSW가 명령에 닿는 길이 `state.twist_stiffness_scale` 하나뿐임을 P8-5 관문으로 확인했다"
  - census·G′가 실패할 때, 그 실패를 PSW 구현 누출과 설계 탓으로 나눌 관문 근거
- **남는 것**
  - P8-6 통과(1회차 $K1_{sc}$)
  - 16절 N-1 전제 시험 둘(P8-4 안): `ProbeResult` 기존 필드가 비트 단위로 같음, 새 필드를 읽는 곳이 `_update_twist_stiffness_scale`뿐임(정적 시험). P8-4 판정(5.4)이 통과일 때에 한한다. 5.4 재실행에서 두 시험(`test_ed8_impl::test_psw_stuck_reads_move_the_scale_mid_and_keep_k1`, `test_ed8_impl::test_psw_fields_are_read_by_the_scale_update_only`)은 실행돼 통과했고, P8-4는 통과다.
  - 판정한 14쌍의 명령 차이 0(기록. 통과 근거로 쓰지 않는다)
  - census·G′·12a·12b는 PSW를 포함한 VBN 구성 전체를 결과로 판정하므로 그대로 계산할 수 있다. 다만 결과의 귀속은 위 제한을 받는다.
- 문턱 15에는 봉인 전 예상 쌍 수와 그 근거가 적혀 있지 않았다(감사 M-2, 4.1 O8-17).

### 2.3 종합 표기 규칙(사용자 결정 D-2 5)
- 뒤 결과 판정이 모두 통과해도 조건 없는 "판 8 합격"은 쓰지 않는다.
- 대신 "판 8 결과 판정 통과, 구현 확인 P8-5 판정 불가(사용자 결정으로 진행)"로 적는다.
- "PSW가 명령에 닿는 길이 하나뿐"이라는 주장의 관문 근거로 P8-5를 쓰지 않는다.
- 이 꼴을 합격으로 볼지는 사용자가 정한다. 봉인 규칙에는 판 8 종합 조건 문장이 없다(판 7 6.3 761행 꼴은 부록 A 밖).

### 2.4 기록 항목(판정 상태를 바꾸지 않음)
- P8-15 기록 실패 (1): r79 KM0 4쌍(`cand=current#L2|s40|g6|52|ref|J1|top|Fs0`, `…|g6|56|ref|J2|top|Fs0`, `…|g6|59|ref|J2|bottom|Fs4`, `…|s41|ref|16|J1|B|0,0`)
- P8-5 판정되지 않은 쌍: 9쌍. 사유는 "라운드 수는 같고 라운드별 스케일이 비트 단위로 다름"이다. 근거 파일은 `impl_p85_a1/p85.jsonl`(`91a00b30…`)과 커밋 전 감사 R-1(`1624f762…`)이다. 값은 옮기지 않는다(1절 4행, 사용자 결정 2026-11-27).
- P8-8과 P8-15는 최소 쌍 수보다 1쌍 많을 뿐이다(6/5, 21/20).
- T8‴ P8-0에서 비교된 27줄의 "같음"은 같은 플랜트끼리의 짝이 보장되지 않는다. 그래서 기록으로만 둔다.

## 3. 판정 커밋 이력(11.2 단일 T8)

규칙 11.2(354행)는 T8의 범위만 정한다. T8은 C8의 자식이고, diff는 `04_scripts` 판정 도구와 `05_tests`뿐이며, 실행 경로 모듈은 C8과 바이트가 같아야 한다. T8을 하나의 해시로 봉인하지 않는다. 판정 커밋은 S8-C `<S8C_JUDGE_COMMIT>`(356행)에서 처음 고정된다. 교체는 모두 같은 11.2 아래에서 했다.

| 판 | 커밋 | 시각(KST) | worktree | 교체 사유(이 커밋을 버린 이유) | 4단계 판정 출력 |
|---|---|---|---|---|---|
| T8 | `ecf6c1428fb2cd71097ff56aa13f21406d3452c7` | 2026-11-26 22:50:30 | `ed8-judge`(locked) | 실행 전 감사 `audit_prerun/verif_c8_t8.md`: 차단 B-1(P8-15가 r79 4키 때문에 구조적으로 판정 불가), B-2(G′가 1차 별칭을 다시 넣음), B-3(5단계 V0 정체성 함수가 종료 3), M-1·M-2·M-4, R-2 | 없음 |
| T8′ | `2bf16b31e771d3ef3b427a360fb3312a747af21c` | 2026-11-27 00:23:41 | `ed8-judge2` 계열 | 재감사 `audit_prerun/verif_t8p.md`: 차단 NB-1(5단계 A/A가 실제 V0 줄에서 모든 쌍 판정 불가), M′-1·M′-2, R′-4. B-1은 사용자 결정 (가)(2026-11-26)대로 이 커밋에서 "빼고 기록 실패 (1)"로 구현했다 | 없음 |
| T8″ | `5955f25baa2bc0ebc8d7587747752d46def8cbb4` | 2026-11-27 작성 01:28:23, 커밋 01:58:21(감사 R-3. 다른 판은 두 시각이 같음) | `ed8-judge2`(locked) | 판정 전 점검 `stage4_prejudge/prejudge_report.md`: 차단 D-1(판 8 J-P3 설정 이름이 없어 P8-2·census·G′ J-P3가 항상 판정 불가) | 없음(`judge_5955f25b` 없음, verif_t8ppp M-2) |
| T8‴ | `2263b2461238da7f93eda147838c01c847315561` | 2026-11-27 18:15:13 | `ed8-judge3`(locked, superseded) | 판정 후 감사 `audit_t8ppp/verif_p80p85_postjudge.md`: 차단 B-1(P8-0 줄 키가 setting을 떼어 114 job → 27키), M-1(기준 쪽 문제가 run 실패에 섞임) | `judge_2263b246/`(8개, 보존·대체됨) |
| **T8⁗** | `7ea782323c427917709ecbb365a58044449beac2` | 2026-11-27 20:11:38 | `ed8-judge4`(locked) | — | `judge_7ea78232/`(8개) + P8-4 정식 |

- 최종 상태: 4단계 관문 8개와 P8-4가 모두 T8⁗ 하나로 판정됐다. P8-4는 T8⁗ 판정 checkout의 worktree_tests 방식 재실행(5.4)으로 판정했다. P8-6·P8-10·P8-11 시험도 같은 P8-4 junit 안에 있다(정식 junit에서도 같은 상태).
- 판정 전 정리(감사 R-5): 정식 P8-4(20:38 끝)가 잠긴 `ed8-judge4`에 `__pycache__` 13개를 남겼다(`p84_suite_T8pppp_7ea78232/git_after.txt`). 메인이 transcript 11:38:21Z(20:38:21 KST)에 `t8pppp_evidence/clean_pycache.py`로 지운 뒤 20:44에 관문 판정을 했다(verif 재감사 `verif_t8pppp_prejudge.md` M-1의 처리). 판정 출력의 `is_clean`은 ignored 파일을 보지 않으므로 이 정리는 출력에 나타나지 않는다.
- 재실행 뒤 정리: 5.4 재실행이 `ed8-judge4`에 다시 `__pycache__` 13개와 `.hypothesis/`를 남겼고, 메인이 지웠다(O8-33). 그 뒤 `status --porcelain --ignored`는 0줄이다(이 개정 작성 중 다시 확인, head `7ea78232`).
- 6·8~10단계도 T8⁗로 판정한다(D-2 결정문 5-1). T8⁗를 다시 바꾸면 4단계 관문 전부를 새 판정 커밋으로 다시 판정해야 한다.
- 범위 확인(verif 재감사 R-4)
  - C8·T8·T8″·T8‴가 모두 T8⁗의 조상이다.
  - `diff 2263b246 7ea78232`는 gate, `test_ed8_gate_p80_key.py`, `test_ed8_jp3_settings.py` 셋이다.
  - "하지 말 것" 정의·상수는 AST·blob 기준으로 바이트가 같다.

## 4. 공개(오염·행위 보고, O 목록)

- 이 문서는 4단계 관문만 다룬다. 규칙 13절 공개 항목 1~20과 S8-R 머리말 O8-1~O8-12는 판 8 최종 판정서에 옮긴다(감사 R-7).
- 번호는 S8-R 오염 보고 O8-1~O8-12에 이어 붙였다(결정 4단계-4). 사실이 문서와 다른 곳은 "차이" 칸에 적었다.

### 4.1 판정 경로의 공개
| # | 내용 | 근거 |
|---|---|---|
| O8-13 | **D-1 수정(T8‴)은 4단계 출력의 키·꼴을 점검한 뒤, 판정 값을 보기 전에 했다(다만 판정 전 점검 값이 관문 내용과 겹친 것은 O8-20).** 4단계 전체 실행은 13:46:19~16:02:02였고, 그중 cases 단계는 15:59:16~16:02:02(`impl_cases.done`)였다(감사 M-9). 판정 전 점검은 키·꼴·행 수만 봤고, 원인 실험(`jp3_cause_probe`)은 판정 행 0 → 10만 냈다. T8‴ 커밋은 18:15:13이고, 그 시점에 판정 출력 폴더는 없었다. 같은 계열의 D-1b(③-off 목록에 VBN0·VBKN0)와 D-1c(12a `_check_lines`)도 함께 고쳤다. 판 8 경로 1에서 이 둘에 닿는 호출은 없어 판정 결과에는 영향이 없다 | verif_t8ppp K-5, `d1_decision_draft.txt` 6 |
| O8-14 | **D-2 수정(T8⁗)은 4단계 판정 출력의 상태 서명(P8-0 failed, 같음 27, 차이 0)을 본 뒤에 했다.** 고친 것은 둘뿐이다. (1) 줄 키를 규칙 361행과 생산자 `run_v5.job_key`에 맞췄다. (2) 기준 쪽 줄 문제를 run 실패에서 떼어 setting_defect로 두었다. 114줄, 기준 sha, 실패 조건, 상태 순서는 바꾸지 않았다. run 쪽 결측·중복·오류 줄의 분류(failed)는 결과를 본 뒤에도 바꾸지 않았다(결정 D-2 6). 처리 결정은 T8⁗ 재판정 결과를 보기 전에 정했다 | `p80p85_decision_draft.txt` 2-3·9(가), 결정 D-2 머리말 |
| O8-15 | **T8‴에서 비교되지 않은 87줄의 해시 대조 결과는 T8⁗ 재판정 전까지 아무도 보지 않았다.** 판정 후 감사와 결정문 작성자 모두 블라인드 원자료를 열지 않았다. T8‴ `p80.json`에는 "twice" 키 목록만 있고 해시 값은 없다 | verif_p80p85 "검사하지 못한 것", 결정문 3-3 |
| O8-16 | **실행 전에 잡지 못한 경로(감사자·작성자 누락).** 기준 파일은 실행 전에도 열 수 있었고, 기준을 자기 자신과 대조하는 스모크 한 번이면 드러났다. (가) 실행 전 감사 `audit_prerun/verif_c8_t8.md` 154행은 상수와 sha만 대조했다. (나) 판정 전 점검 `stage4_prejudge/prejudge_report.md` 42·54행은 키 존재와 sha만 봤다. (다) T8‴ 판정 전 재감사 `audit_t8ppp/verif_t8ppp_prejudge.md` 111행은 gate 하위 명령을 범위에서 뺐다. (라) 단위 시험 `05_tests/unit/test_ed8_gate_judge.py` 56-58행은 setting이 하나인 합성 줄만 썼다. (마) 명세 작성자(control-expert)는 P8-0 행에 줄 대응 키를 적지 않았고, D-1 대조에서도 gate를 "J-P3 안 씀, 영향 없음"으로만 봤다 | 결정문 9(나) |
| O8-17 | **P8-5 판정 불가.** $n_{same}$ 14 < 15다. 문턱 15는 봉인 전 감사 권고(M-9)에 따라 개정 3에서 정했다. 그러나 예상되는 같은 쌍 수와 그 계산 근거는 봉인 전에 적지 않았다(판정 후 감사 M-2. 개정 3 작성자는 control-expert). 결과를 본 뒤 문턱을 바꾸지 않았고, 키를 더해 다시 실행하지도 않았다(사용자 결정 2026-11-27) | 결정문 9(다) |
| O8-18 | **명세 밖 시험 변경.** T8⁗ 구현자가 `05_tests/unit/test_ed8_jp3_settings.py::test_e_changes_since_t8pp_are_the_two_judges_and_tests`(T8‴ T-e)의 비교를 작업 트리 기준 `diff 5955f25b`에서 고정 범위 `diff 5955f25b 2263b246`으로 바꿨다. 옛 꼴은 자식 판정 커밋이 gate를 고치면 구조적으로 실패한다. 허용 목록은 넓히지 않았다. **같은 시험 ID의 본문이 T8⁗에서 고정 범위로 바뀌어 기록이 됐고, 범위 관문은 새 T-e(`test_ed8_gate_p80_key.py::test_changes_since_t8ppp_are_the_gate_and_tests_only`)가 맡는다.** P8-4 junit 대조에는 "passed → passed"로만 보인다. 새 T-e도 다음 판정 커밋이 gate·05_tests 밖을 바꾸면 같은 문제가 생긴다 | `impl_report_t8pppp.md` 3절·확인 필요 1·2, verif_t8pppp R-3·확인 필요 1 |
| O8-19 | **P8-4 조건 차이.** (가) 정식 실행(T8‴·T8⁗)은 러너가 P 0xFFFF로 고정했고 예약을 걸었다. python-expert의 예비 실행은 affinity를 고정하지 않았다. (나) 규칙 기준선 실행(C8 부모 `41e107e9` 대 C8, `p84_suite_41e107e9_56849248`)은 `tools/verif/worktree_tests.py`(main 자료 붙임, 건너뜀 15)로 돌렸다. T8 사슬의 정식 실행은 판정 worktree에서 pytest만 돌렸다(`OUTRIGGER_RECORDS_ROOT`만 지정, 건너뜀 134). 5.3·5.4와 결정 4단계-1을 본다. (나)는 이 판정서 재집계에서 처음 적는 것이다. (다) 이 차이 때문에 결정 4단계-1(결정 문서는 앞 초안보다 늦은 21:14 작성)로 T8⁗를 기준선과 같은 방식으로 다시 돌렸다(5.4). 이 재실행은 결과(앞 초안의 사슬 근거 수치)를 본 뒤 정한 실행이다. 판정 규칙(364행)과 기준 목록은 바꾸지 않았다 | `p84_suite_T8pppp_7ea78232/p84_t8pppp_runner.ps1` 13·29행, `impl_report_t8pppp.md` 4절, `p84_baseline_chain_stage4.json`, `p84_suite_T8pppp_wt_7ea78232/p84wt_runner.ps1` |
| O8-20 | **T8‴ 단계의 이전 점검 결과가 관문 내용과 겹친다.** 판정 전 점검(②③)은 키·꼴·건수만 냈다. 그러나 다음 값은 관문 내용과 겹친다. (가) "run_v5 판 8 줄 `WARN_ROD_PRESSURE_FALLBACK` 0건": P8-1의 대체 다리 기록 쌍 0과 겹친다. (나) "P8-15 r79 4줄 기록 없음 → 빠짐": P8-15 기록 실패 (1)과 겹친다. (다) "12b 정체성 스모크 결함 0": l1ref 관문의 정체성 부분과 겹친다(공개 1). (라) cases `identity_defects` 0. (마) 원인 실험의 판정 행 0 → 10. (바) 판정 전 점검은 C-J 단위 판정·C-S `unit_verdicts`·G′ 줄 읽기 함수를 4단계 줄에 메모리에서 돌려 "판정 가능 수"를 냈다. 통과·실패 수는 아니다(감사 R-8) | `prejudge_report.md` 1절 표·2절 공개 1, 58·66·70행 |

### 4.2 블라인드·검색 규칙 관련 사건
| # | 누가·언제 | 내용 | 노출 | 근거·차이 |
|---|---|---|---|---|
| O8-21 | 판정 전 점검 ②③(python-expert, 2026-11-27 저녁) | 전역 `settings.json` JSON 오류로 blind_guard 훅이 등록되지 않은 채 돌았다. 그 시점에 `j9_runs/56849248/`는 블라인드 목록에 없었다(판 7 목록 시기). 9개 단계 폴더를 목록했고, 출력 파일은 스크립트로 키 이름·건수·꼴만 셌다 | 값 출력 없음(O8-20 겹침 제외) | `prejudge_report.md` 8절, 메인 기록. 훅을 고친 뒤 재시작했고, 그 뒤 `impl_*_a1/`·`l1ref_a1/`을 블라인드로 지정했다 |
| O8-22 | control-expert, D-1 해석 | (1) 첫 Glob의 `path`가 `…\j_p3_cause`(블라인드를 품은 상위 폴더)였고 패턴은 `jp3_remedy_spec_v8_rules*`였다. 훅이 막았다. (2) Grep 1회의 `path`로 worktree 루트 `ed8-judge2`를 썼다(glob `{03_src,04_scripts,05_tests}/**/*.py`, 결과 없음) | 없음 | `control_d1_settings.md` 5절 |
| O8-23 | control-expert, NB-1 후속 | Grep 1회의 `path`로 worktree 루트 `ed8-judge2`를 썼다(glob `*.py`, 패턴 `def lock_window_alignment`, 파일 목록, 출력 .py 1개). 앞 결정문 작성 때는 Glob 1회(`**/judge_stage1_r5.py`, path `ed8-judge2\04_scripts`, 결과 없음)를 썼다 | 없음 | `control_nb1_followup.md` 6절, `control_nb1_decision.md` 9절. **차이**: 지시문의 "control·python worktree 루트 Grep 각 1회"와 달리, 문서상 control의 worktree 루트 Grep은 2회다(O8-22 (2), O8-23). python의 1회는 S8-R O8-9에 이미 있다 |
| O8-24 | stats-design-expert, NB-1 검토 | (1) 맨 이름 Glob(`*`) 3회: path `…\ed8_design\impl_report_ed8`, `…\ed8_design\audit_prerun`, `…\j9_runs\8a2a52ce\judge_60ebb4a4`. (2) path `…\j9_runs\79495405`의 Glob 4회(0건)와 비재귀 하위 폴더 목록 1회. (3) PowerShell 재귀 `Get-ChildItem`(`*.jsonl`·`*judge*.json`)을 `j9_runs\8a2a52ce`·`79495405` 등에. (4) Glob path `…\ed6_design`·`verif_matrix`·`04_scripts`. (5) Grep path `04_scripts\04_hydraulic\coupled`. 그 시점의 블라인드는 판 7 목록(`j9_runs\606f8713\` 등)이었고, 판 8 4단계 출력은 아직 없었다 | 파일 이름·크기 | `audit_prerun/stats_nb1.md` 243-251행. **차이**: 지시문은 맨 이름 Glob 3회만 적었다. 문서에는 (2)~(5)도 공개돼 있다 |
| O8-25 | stats-design-expert, NB-1 추가 | 사용자 허락(2026-11-27)으로 판 8 출력 `ed8_design/p816_prerun_41e107e9/p816.jsonl`(`4bbbb2e8`)의 L2_impl 23줄에서 J9·J11 건수 8개만 셌다 | 건수 | `stats_nb1_addendum.md` 오염 보고 |
| O8-26 | 판정 후 감사(verif), D-2 결정문 작성(control-expert) | (1) 판정 후 감사: PowerShell `Test-Path` 묶음 명령 1회가 blind_guard에 막혔다(출력 없음). 또 기준 파일(블라인드 아님, 판 7 본 자료)의 최상위 `final_phase`·`harness_class` 값별 건수가 화면에 나왔다. (2) D-2 결정문 9(마) 둘째 줄: 결정문 작성은 판정 출력 `p80.json`·`p85.json`(단일 파일)과 블라인드가 아닌 고정 기준(`e241638d` blob, 메인 checkout 사본)만 읽었다. 같은 작성의 도구 거부 1건: 출력 해시와 scratchpad 삭제를 묶은 PowerShell 명령 1개가 경로 보호 규칙에 막혔고(실행 없음) 나눠 다시 실행했다(감사 M-6 (나)) | 기준 파일 건수 | `verif_p80p85_postjudge.md` 2·204행, `p80p85_decision_draft.txt` 93-95행, `control_p80p85.md` 248행 |
| O8-27 | T8‴ 판정 전 재감사(verif) | (1) Bash 파이프 1회(`git show 2263b246:05_tests/data/ed8_run_path_modules_56849248.json \| head -c 1200`). (2) `ref_check --exclude`가 명세의 블라인드 경로 조각에 걸리지 않았다(실제 블라인드 폴더에는 닿지 않음) | 실행 경로 목록 머리 1.2 kB | `verif_t8ppp_prejudge.md` 463-465행. **차이**: 지시문은 (1)만 적었다 |
| O8-28 | T8⁗ 판정 전 재감사(verif) | (1) Glob 1회(path `j_p3_cause`, `jp3_remedy_spec_v8_rules*`)가 훅에 막혔다. (2) Bash 파이프 1회(`git worktree list --porcelain \| grep`). (3) `ref_check`를 잘못된 `--repo`로 1회 돌렸고 결과는 버렸다 | 없음 | `verif_t8pppp_prejudge.md` 388-391행. **차이**: (3)은 지시문에 없다 |
| O8-29 | 메인 세션, 2026-11-27 18:59:27 KST | `j9_runs\56849248`에 `Get-ChildItem -Filter *.done` 1회, blind_guard가 막음(변수 대입 판정). 시점은 T8‴ 판정(18:54) 뒤, 블라인드 목록을 비운 20:50:46 전이다. 이 세션에서 훅에 막힌 메인 호출은 이 1회다 | 없음(막혔으므로 열람 없음) | 메인 transcript `c52f3f13-…jsonl` 09:59:27Z(커밋 전 감사가 확인, 감사 M-5) |
| O8-30 | 메인 세션 | 4단계 전 커밋 준비에서 `baseline_check.py write-sums --force`로 근거 폴더 SUMS를 다시 썼다. gitignore된 npz가 빠져 `p816_prerun_41e107e9`·`p816_prerun_27c0f046`·`p816_prerun_66648ea8`의 SUMS가 바뀌었다(규칙 위반). integrity-checker가 찾았고, 같은 날 원래 꼴로 되돌렸다(`0921e251…`·`fd9605f1…`는 인용값과 같음, `384431fe…`). `impl_report_ed8\SHA256SUMS`는 인용값 `d9e4f2ba…`로 되돌리지 못하고 새로 썼다(`e6bcab7d…`) | 없음 | `ed8_design/sums_notes_20261127.md`(`870823e3`, master 추적) |
| O8-31 | 이 판정서 작성(control-expert) | (1) Bash 파이프 1회(`git ls-files <폴더> \| head -n 0`, 출력 없음). (2) 첫 Glob의 `path`가 `…\j_p3_cause`(패턴 `jp3_remedy_spec_v8*`)였다. 블라인드 목록이 빈 뒤라 훅은 막지 않았다. (3) 블라인드 해제 뒤 4단계 원자료를 재집계 스크립트로 읽었다(건수·참거짓·라벨만). (4) 개정 1 작성(블라인드 목록 빈 상태): P8-4 재실행 근거 폴더 전체, 판정 출력 `l1ref.json`의 `identity_sources` 값(5.2 아래 표로 옮김), `p85.json`의 키 이름(Grep `-o`, 값 없음), `RUN_ALL.SHA256SUMS`의 패턴별 건수, `impl_p85_a1/SHA256SUMS`를 읽었다. Bash 파이프는 쓰지 않았다 | 건수, l1ref 정체성 값 | 10절 |
| O8-32 | compute-scheduler-expert(`a8a18cd7`), 2026-11-27 21:14 KST(12:14:44Z·12:14:54Z·12:14:59Z) | Bash 파이프 3회(`cat *.ps1 \| head -80` 등). 읽은 곳은 P8-4 정식·기준선 러너와 근거 폴더(재실행 설계용: 12:14:44Z `runners/outrigger-ed8/p84_t8pppp_7ea78232`, 12:14:54Z `p84_suite_41e107e9_56849248/run`, 12:14:59Z `runners/outrigger-ed8/p84/run`; 재감사 R′-1)이고 블라인드가 아니다. 앞 초안(21:09)보다 뒤라 빠져 있었다(감사 M-6 (가)) | 없음(러너 스크립트 머리) | 커밋 전 감사 `transcript_scope` |
| O8-33 | 메인 세션, 5.4 재실행 뒤(23:04 이후) | `ed8-judge4`의 `__pycache__` 13개와 `.hypothesis/`(이번 실행이 만든 pytest 캐시, 279 파일)를 지웠다. 지운 뒤 `status --porcelain --ignored` 0줄(이 개정에서 다시 확인). 6·8~10단계 판정 전 정리다 | 없음 | 메인 지시문, `p84_suite_T8pppp_wt_7ea78232/git_after.txt`·`pycache_paths.txt` |
| O8-34 | 메인 세션, 개정 1 뒤(사용자 결정 2026-11-27) | T4h npz 906개를 백업 `~/.claude/backups/outrigger-ed8/j9_runs_56849248/`의 repo 상대 경로 아래로 복사하고(복사 전 RUN_ALL sha 대조, 복사 뒤 사본 sha 재측정 같음), `j9_runs/56849248_LOCAL_ONLY.SHA256SUMS`를 3줄(`7faba722…`)에서 909줄(`47ab36a5…`)로 늘렸다. 늘어난 목록 사본도 백업에 넣었다. 스크립트 `ed8_design/stage4_judgement/npz_local_only.py`(`71c27a51…`). 실행 폴더의 파일은 바꾸지 않았다 | 없음(sha·경로만) | 메인 지시문. 이 개정에서 목록 sha·줄 수와 RUN_ALL npz 906줄 대조(차이 0)를 다시 확인 |
| O8-35 | 메인 세션, 개정 1 뒤 | 4단계 러너 `~/.claude/runners/outrigger-ed8/stage4/`의 21파일(`run_stage4.ps1`, `steps_stage4.json`, `logs/` 19)을 `ed8_design/stage4_runner/`로 복사했다. 원본과 sha가 같다(메인 확인) | 없음 | 메인 지시문. 이 개정에서 파일 수 21을 다시 셈 |
| O8-36 | 메인 세션, 2026-11-27 23:03~23:21 KST(14:03:12Z~14:20:50Z) | Bash 파이프 9회. 읽은 곳은 P8-4 재실행 러너 출력, 근거 폴더, LOCAL_ONLY, RUN_ALL, 백업 폴더다(메모리 덧붙이기 1회 포함). 14:20:45Z의 `grep "\.npz" RUN_ALL.SHA256SUMS \| head -2` 출력에 RUN_ALL의 cases npz 줄 2개(`impl_cases_a1` 아래 파일 이름과 sha)가 나왔다. P8-2 경로 1 실행 출력 이름이다. 값은 보지 않았다 | 파일 이름 2·sha 2(cases 실행 출력), 값 없음 | 재감사 `verif_stage4_judgement_recheck.md`(`325b03fd…`) M′-3 (가), 메인 transcript |
| O8-37 | 메인 세션, 2026-11-27 23:04 KST(14:04:20Z dry-run `ready 1`, 14:04:27Z `--apply` `resumed 1, exited 1`) | `resume_thread.py`로 PID 58136(python-dev `python.exe -I -B …/tools/verif/blind_guard.py`, 훅 고아)을 재개했다. 이 프로세스는 18:38:42부터 Suspended였다. 그 시각 이 세션(메인 + 서브에이전트)에는 도구 호출이 없었다. 그 훅이 지킨 호출은 **미상**이다([추정] 다른 세션의 호출, 사용자 결정 2026-11-27 "미상으로 기록"). 다른 세션의 기록은 열지 않았다 | 없음(프로세스 재개만, 파일 열람 없음) | 재감사 M′-3 (나), 메인 transcript |
| O8-38 | 재감사(verif-protocol-auditor), 2026-11-27 23:28 KST(14:28:27Z) | Bash 파이프 1회(`git ls-tree -r --name-only 7ea78232 \| grep …; git log -1 --format=%B ecf6c142 \| head -40`). 읽은 것은 커밋 트리의 파일 이름과 T8 커밋 메시지이고 블라인드 경로가 아니다 | 없음(파일 이름·커밋 메시지) | 재감사 R′-6 |

### 4.3 해석 결정의 공개(5단계·G′ 판정서로 넘길 문장)
4단계 판정에는 쓰지 않는다. 5단계 이후 판정서에 옮길 공개 문장의 위치만 고정한다.
- **FS24·G4 형상 기록 값**: T8″ 이후 `effective_shape`는 twin에 형상 필드가 없으면 사건 이름을 보지 않고 RE1bF 기본값 (0.030 m, 0.05 s)을 준다. 그래서 FS24·G4 twin에도 RE1bF 기본값이 채워진다.
  - 근거: `audit_prerun/smoke_v0twin_report.md` 17·49-51행, 결정문 `control_nb1_followup.md` 3.3(89행 "없으면 `r67.EVENTS["RE1bF"]`의 (0.030, 0.05)로 본다")
  - 영향: 형상 기록은 같은 슬롯(같은 사건) 짝끼리만 비교하고, 형상 필드는 (나) RE1bF 슬롯에만 있다. 그래서 판정·기록 결과는 바뀌지 않는다.
  - 주의: 이 값을 "FS24·G4의 실효 형상"으로 읽으면 뜻이 틀린다. 스모크 보고의 확인 필요(사건별 기본값을 쓸지)는 결정 4단계-4로 닫혔다: 도구를 고치지 않고 G′ 판정서 기록 칸에 "사건 이름 미참조 RE1bF 기본값"으로 적는다.
  - 이 공개는 `control_nb1_decision.md`·`stats_nb1.md`·`stats_nb1_addendum.md`에는 없다.
- **5단계 A/A 항목 범위(NB-1)**: `control_nb1_followup.md` 4절 공개 문장(99-113행)을 쓴다. 이 문장은 `control_nb1_decision.md` 5절을 대체한다. 그 안의 자리에 다음을 넣는다.
  - [Q-1]: `stats_nb1.md` 85-89행. 둘째 문단은 `stats_nb1_addendum.md` 31-33행 개정안으로 바꾼다.
  - [Q-3]: `stats_nb1.md` 146·148행
- 핵심 문장(인용)
  - "두 항목은 V0와 비교하지 않는 처리 팔 절대 항목이다(J9: 이륙 뒤 클립 > 0, J11: 대체 다리 늦은 잠김 > 0). 그래서 그 실패는 위상 산포가 아니라 VBN 고유 성질로 보고, 다른 항목으로 보정된 허용 $k_N$을 함께 쓴다(읽기 (나))."(followup 105행)
  - "단위당 J9·J11 단독 실패율 $q$의 95 % 상한은 줄 독립 가정에서 0.11 %(2,702줄)다."(addendum 33행)
  - "이 효과는 J9·J11 비대칭(G′ 쪽 귀무율을 높여 엄해지는 쪽)과 작용하는 곳이 달라, 평균으로 일부 상쇄되더라도 멈춤과 검정력에서는 상쇄되지 않는다."(stats_nb1 148행)

## 5. 재집계(C축)

### 5.1 방법
- 스크립트는 `ed8_design/stage4_judgement/`에 있다. 판정 모듈은 import하지 않는다. 규칙 문면을 자체 코드로 구현했다. 출력은 건수·참거짓·라벨 분포뿐이고, 해시·지표 값·줄 내용은 내지 않는다.
- 실행: PowerShell, `C:\ProgramData\miniforge3\envs\python-dev\python.exe -X utf8 -I -B <script> <out>`, `MKL_THREADING_LAYER=TBB`, `PYTHONDONTWRITEBYTECODE=1`
- 원자료: `j9_runs/56849248/impl_*_a1/`, `l1ref_a1/`(4단계 판정 뒤 2026-11-27 20:50:46에 블라인드 목록을 비움, `blind_paths.json` mtime. control-expert의 원자료 접근은 20:54 KST로 그 뒤다, 감사 R-6), 기준 2개(pinned sha 재측정 일치)

| 파일 | sha256 | 종료 | 내용 |
|---|---|---|---|
| `recount_stage4.py` | `47bc2c3765300717742e12d752b3a428fac3e26386d0b9b4caedcfaf449faf2e` | 0 | 8개 관문 재집계와 정체성 |
| `recount_stage4.json` | `c39c689ee57684d32aee7752b2a949a6321745ea5ff254beef2927079ca32c3d` | – | summary `{"recount_matches_tool": true, "identity_ok": true, "rule_status_matches_tool": true, "status": "same"}` |
| `junit_critical_stage4.py` / `.json` | `b0523d21…` / `0f8cdb49…` | 0 | P8-4 junit의 관문 시험 상태 |
| `p84_baseline_chain_stage4.py` / `.json` | `97cc7bda…` / `23eec0b7…` | 0 | P8-4 규칙 기준선 대조(5.3) |
| `compare_t8ppp_t8pppp_rerun.txt` | `8d09c700…` | 0 | D-2 뒤 대조 재실행 출력 |

### 5.2 관문별 재집계
| 관문 | 재집계 정의(규칙 줄) | 판정 출력 | 재집계 | 같음 |
|---|---|---|---|---|
| P8-0 | job에서 `mask`·`t4h_dir`만 뺀 정렬 JSON 키로 run 114줄·기준 114줄을 줄별 대조(361) | jobs 114, run_jobs 114, equal 114, 차이 0 | run 114줄(오류 0, 해시 없음 0), 서로 다른 키 run 114·기준 114, 중복 0, equal 114, differing·missing·extra 0. setting 분포 6종 일치. T8‴ 꼴 키(setting·`_part`·`_r79_plan`도 뺌)로 접으면 27(B-1 재현). 규칙 분류 pass | 예 |
| P8-16 | 팔별 27줄의 `commands_sha256` 다중집합 = 기준 원천의 같은 팔(B·L2) 다중집합(377, 키 없는 독립 대조) | equal 54, keys 54, 팔별 27 | run 팔 B_impl 27·L2_impl 27. 기준 원천 팔 B 27·L1 27·L2 27·B0 1(82줄). 다중집합 B_impl = B, L2_impl = L2. 해시 없음 0. 규칙 377행의 키별 기준 표 대조는 커밋 전 감사 재집계가 했다: 키 (팔, 플랜트, job − {mask, t4h_dir, setting} 또는 r79 `key`)로 54/54 같음, run에만 0, 기준에만 0, 중복 키 0(감사 R-2) | 예 |
| P8-5 | (팔, plant, job − {mask, t4h_dir, setting, _part, _r79_plan}) 짝, 라운드별 `twist_stiffness_scale` JSON 같음(365) | pairs 23, judged 14, not_judgeable | 줄 46(팔별 23), 짝 23, 짝 문제 0, 선택 14, 비선택 9, 기록 없음 0, 판정 쌍 차이 0 → not_judgeable(14 < 15) | 예 |
| P8-8 | 켬 팔 `ed8_record.reapproach_runs[*].short_run_extended`가 모두 거짓(368) | pairs 23, judged 6, pass | 짝 23, 선택 6, 비선택 17, 차이 0 → pass(6 ≥ 5) | 예 |
| P8-15 | 켬 팔 `ed8_record.twist_waiver` `n_waiver_done`·`n_waiver_periods` 모두 0. 기록 없는 쌍은 빼고 기록 실패 (1)(376, 10:345) | pairs 27, judged 21, unread 4, pass | 짝 27, 기록 없음 4, 비선택 2, 선택 21, 비정수 0, 차이 0 → pass(21 ≥ 20) | 예 |
| P8-1 | job − {mask, t4h_dir, setting} 짝의 VBN·VBN0 해시. `WARN_ROD_PRESSURE_FALLBACK` 사건 쌍은 기록(362) | judged 22, differing 0, 기록 0 | 줄 44(VBN 22·VBN0 22), job 22·완결 22, 대체 다리 쌍 0, 판정 22, 차이 0 | 예 |
| P8-2 | 10줄의 `hydraulics_record.extend_bound_check`(rev 7) jp3a·jp3b(over tol)·jp3c breach 합(363) | `J-P3_judged_rows` 10, rev7 judged 10, breach 0 | 줄 10(R12, VBN·LSN1~4 각 2), 오류 0, 기록 10, `rule_revision` 7 ×10, 세 breach 합 0. 세 필드는 리스트 꼴이라 숫자 리스트는 합, 그 밖은 길이로 셌다 | 예 |
| l1ref | 4파일 `results` 길이와 `controller_tag` 분포 | 167·167·102·102, identity 문제 0 | 167·167·102·102, 태그 분포 같음 | 예 |
| 정체성 | 8개 출력의 head·is_clean·규칙 sha·실행 커밋, `.done` sha와 출력 sha 재측정, 기준·main.jsonl sha | – | 모두 참 | 예 |

#### l1ref 출처별 정체성(`runs.<stem>.identity_sources`, 5.2 l1ref 행에 딸림)
- 근거: 판정 출력 `j9_runs/56849248/judge_7ea78232/l1ref.json`(`810fa864…`, T8⁗). 감사 R-9가 인용한 판 7 정오 1 "판정서에 옮길 것" 6(`jp3_remedy_spec_v7_erratum1.md:234`, 이 개정 작성자는 다시 읽지 않음)의 꼴로 옮긴다(사용자 결정 2026-11-27).
- 칸 읽기: 각 칸은 그 출처(row = 줄, meta = 결과 메타)의 서로 다른 값과 줄 수다. 네 run 모두 출처마다 값이 하나뿐이고, 줄 수는 그 run의 전체 줄 수(167·167·102·102)와 같다. 대괄호는 도구가 낸 값 키(16자)다. `<absent>`는 도구가 결측을 적은 값이다.
- 도구 판정: 네 run 모두 `identity_problems` 0, status `pass`. 이 표는 기록이며 해석을 더하지 않는다.

| 항목 | 출처 | L1_VBN0 (VBN0, 167줄) | L1_VBN (VBN, 167줄) | L1a_VBN0 (VBN0, 102줄) | L1a_VBN (VBN, 102줄) |
|---|---|---|---|---|---|
| `controller_tag` | row | `final_C4G2_LAS_K1_LSB_ED8` ×167 [`d80a97a824226b34`] | `final_C4G2_P3X_LAS_K1_LSB_ED8` ×167 [`08c45da86c903d50`] | `final_C4G2_LAS_K1_LSB_ED8` ×102 [`d80a97a824226b34`] | `final_C4G2_P3X_LAS_K1_LSB_ED8` ×102 [`08c45da86c903d50`] |
| `controller_tag` | meta | row와 같음 ×167 [`d80a97a824226b34`] | row와 같음 ×167 [`08c45da86c903d50`] | row와 같음 ×102 [`d80a97a824226b34`] | row와 같음 ×102 [`08c45da86c903d50`] |
| `hydraulic_options.p1_patch` | row | P1 ×167 [`9a06cbde1af7eb6f`] | P1 ×167 [`9a06cbde1af7eb6f`] | P1 ×102 [`9a06cbde1af7eb6f`] | P1 ×102 [`9a06cbde1af7eb6f`] |
| `hydraulic_options.p1_patch` | meta | P1 ×167 [`9a06cbde1af7eb6f`] | P1 ×167 [`9a06cbde1af7eb6f`] | P1 ×102 [`9a06cbde1af7eb6f`] | P1 ×102 [`9a06cbde1af7eb6f`] |
| `lsb_components` | row | `<absent>` ×167 [`43d9bcb84acb9bbb`] | `<absent>` ×167 [`43d9bcb84acb9bbb`] | `<absent>` ×102 [`43d9bcb84acb9bbb`] | `<absent>` ×102 [`43d9bcb84acb9bbb`] |
| `lsb_components` | meta | `["A_i","A_ib","A_ii","B3"]` ×167 [`c58c148a9231e603`] | 같음 ×167 [`c58c148a9231e603`] | 같음 ×102 [`c58c148a9231e603`] | 같음 ×102 [`c58c148a9231e603`] |
| `lsb_settings` | row | `<absent>` ×167 [`43d9bcb84acb9bbb`] | `<absent>` ×167 [`43d9bcb84acb9bbb`] | `<absent>` ×102 [`43d9bcb84acb9bbb`] | `<absent>` ×102 [`43d9bcb84acb9bbb`] |
| `lsb_settings` | meta | LSB ×167 [`fe4b4a0711f329e5`] | LSB ×167 [`fe4b4a0711f329e5`] | LSB ×102 [`fe4b4a0711f329e5`] | LSB ×102 [`fe4b4a0711f329e5`] |
| `probe_d6_settings` | row | `<absent>` ×167 [`43d9bcb84acb9bbb`] | `<absent>` ×167 [`43d9bcb84acb9bbb`] | `<absent>` ×102 [`43d9bcb84acb9bbb`] | `<absent>` ×102 [`43d9bcb84acb9bbb`] |
| `probe_d6_settings` | meta | D6 ×167 [`eac3925b404640e2`] | D6 ×167 [`eac3925b404640e2`] | D6 ×102 [`eac3925b404640e2`] | D6 ×102 [`eac3925b404640e2`] |
| `extend_bound_check` | row | `null` ×167 [`74234e98afe7498f`] | EBC7 ×167 [`90936802dc11a2cc`] | `null` ×102 [`74234e98afe7498f`] | EBC7 ×102 [`90936802dc11a2cc`] |
| `extend_bound_check` | meta | `null` ×167 [`74234e98afe7498f`] | EBC7 ×167 [`90936802dc11a2cc`] | `null` ×102 [`74234e98afe7498f`] | EBC7 ×102 [`90936802dc11a2cc`] |
| `run_extend_start_revision` | row | `<absent>` ×167 [`43d9bcb84acb9bbb`] | `7` ×167 [`7902699be42c8a8e`] | `<absent>` ×102 [`43d9bcb84acb9bbb`] | `7` ×102 [`7902699be42c8a8e`] |
| `run_extend_start_revision` | meta | `<absent>` ×167 [`43d9bcb84acb9bbb`] | `<absent>` ×167 [`43d9bcb84acb9bbb`] | `<absent>` ×102 [`43d9bcb84acb9bbb`] | `<absent>` ×102 [`43d9bcb84acb9bbb`] |

표의 약칭 값(네 run 모두 같은 값 키의 값을 `l1ref.json`에서 그대로 옮김):
- P1 [`9a06cbde1af7eb6f`]: `{"line_scale":1.0,"dead_scale":1.0,"bulk_modulus_Pa":1000000000.0,"k_ext_form":"b0"}`
- EBC7 [`90936802dc11a2cc`]: `{"rule_revision":7,"spec_edition":"10902ffd","carry_end_rule":"inherit_when_gate_shut","retract_start_rule":"with_tracker","identity_consistent":true}`
- D6 [`eac3925b404640e2`]: `{"witness":true,"witness_m":0.0003,"not_opened_warn_rounds":2,"retract_position_target":false,"retract_slow_speed_m_s":0.001,"retract_extra_margin_m":0.0002,"head_reading_margin_Pa":900000.0,"witness_mode":"record"}`
- LSB [`fe4b4a0711f329e5`]:

```json
{"components":["A_i","A_ib","A_ii","B3"],"hold_speed_ratio":0.01,"a1_trigger_periods":10,"a1_trigger_travel_m":0.0005,"a1_motion_ratio":0.25,"a1_witness_m":0.0004,"a1_step_m_s":0.0002,"a1_cap_m_s":0.00105,"a1_cap_periods":50,"a2_extend":false,"a2_lock_periods":2,"a2_fill_factor":1.0,"a2_fill_speed_ratio":1.0,"a2_hold_after_fill_s":null,"a2_psi":6.0,"a2_bulk_modulus_Pa":1600000000.0,"a2_line_volume_m3":0.0001425,"a2_hose_bulk_modulus_Pa":1000000000.0,"a2_crack_Pa":100000.0,"a2_tank_Pa":200000.0,"a2_rod_dead_length_m":0.02,"a2_head_dead_length_m":0.05,"a2_friction_band_N":[16000.0,16000.0,13328.0,13328.0],"a2_reading_margin_Pa":400000.0,"a2_void_estimate":true,"a2_void_head_bulk_modulus_Pa":1600000000.0,"a2_void_rod_bulk_modulus_Pa":690000000.0,"a2_retract_witness_m":0.001,"a2_rod_witness_min_Pa":300000.0,"a2_rod_witness_ratio":0.5,"a2_extend_witness_m":0.001,"a2_on_fallback_legs":false,"b1_exit_margin_N":2000.0,"b1_exit_samples":3,"b2_required_samples":null,"b3_end_periods":2,"b3_travel_cap_fraction":0.065,"b3_max_periods":null,"b3_protect_margin_N":35000.0,"b3_protect_predictive":false,"b3_predictive_margin_N":5000.0,"b3_twist_stiffness_N_m":21700000.0,"ib_blind_periods":25,"ib_still_m":0.0001,"ib_reference_skip_reads":2,"ib_condition":"with_twist","ib_twist_limit_N":null,"ib_latch_reversals":2,"ib_protect":true,"ib_protect_travel_m":0.00085,"ib_protect_stiffness_N_m":41000000.0,"ib_protect_margin_N":5000.0,"ib_record_after_s":1.0}
```

- cases J-P3 판정 행 10을 확인했다. 판정 출력의 `J-P3_judged_rows` 10, `runs_expected` 10, `rev7_unjudged_setting_runs` 0, `rule_missing_runs` 0이고, 재집계의 ③ rev 7 기록도 10줄이다. 판정 전 값 없는 스모크 `stage4_prejudge_t8ppp/cases_jp3_rows_smoke.json`(`db26fce9`, T8‴)의 judged_rows 10과도 같다.

### 5.3 P8-4 보조: 정식 실행과 사슬 근거(판정은 5.4)
이 절은 앞 초안의 사슬 근거다. 결정 4단계-1에 따라 판정 근거가 아니라 보조 기록으로 둔다.

| junit | 방식 | 시험 | 통과 | 실패 | 건너뜀 |
|---|---|---|---|---|---|
| 기준선 `41e107e9`(`p84_suite_41e107e9_56849248/base/junit.xml`) | `worktree_tests.py`, main 자료 붙임 | 8782 | 8765 | 2 | 15 |
| C8 run(같은 폴더 `run/junit.xml`, `suite_judgement.json` pass: 새 실패·핵심 미통과·새 건너뜀 0) | 같음 | 8789 | 8772 | 2 | 15 |
| C8 판정 worktree 꼴(`impl_report_ed8/tests/junit_C8_56849248.xml`, `b747aee6`) | pytest만 | 8741 | 8605 | 2 | 134 |
| T8‴ 정식 | pytest만, P 0xFFFF | 9054 | 8918 | 2 | 134 |
| **T8⁗ 정식** | pytest만, P 0xFFFF | 9071 | 8935 | 2 | 134 |

- T8⁗ 비통과 136개 = C8 판정 worktree 꼴의 비통과 136개다(이름이 모두 같고, C8 꼴에서 통과한 것이 T8⁗에서 비통과인 시험 0개).
- 기준선 `41e107e9`와 바로 대조하면 T8⁗ 비통과 가운데 117개가 기준선에서 통과였다.
  - 건너뜀 116: 사유는 모두 `07_results`·batch·records "not present/absent"
  - 실패 1: `test_hydraulics_flow_limit_run::test_coupled_batch_rows_and_resume`, worktree `07_results/S9/batch_FINAL-REP…` 파일 없음
  - 핵심 패턴(`test_jp3_*`, `test_ed6_*`, `test_run_v5*`, `test_lock_start_b*`, `test_c2*`, `test_extend_start_bound*`) 시험은 0개
  - 그 밖에 기준선에 없는 매개변수 꼴 `[NOTSET]` 건너뜀 3개가 있다
- **읽기**
  - 비통과 증가는 실행 방식(판정 worktree에 `07_results` 없음) 탓이다. T8 계열 변경 탓이 아니다.
  - 사슬로 보면 새 실패·새 건너뜀은 0이다. (1) C8 대 기준선은 같은 방식에서 0이다. (2) C8 판정 worktree 꼴과 T8⁗ 정식은 같은 방식에서 비통과 집합이 같다. (3) T8⁗ 대 T8‴ 정식은 changed 0이다.
  - 앞 초안 시점에는 규칙 문면 "기준선은 C8의 부모에서"를 같은 방식으로 직접 대조한 실행이 T8⁗에 없었다. 결정 4단계-1로 그 실행을 했고(5.4), P8-4는 5.4로 판정한다.
- 관문 시험(T8⁗ 정식): `test_ed8_*` 354개 모두 통과(그중 `test_ed8_run_path` 4, `test_ed8_gate_p80_key` 17, `test_ed8_gate_judge` 37, `test_ed8_jp3_settings` 23). P8-6 1/1, P8-10 2/2 통과. 실패 2개는 C8 판정 worktree 꼴(`junit_C8_56849248.xml`)에도 같은 이름으로 있고 관문 시험이 아니다(감사 M-2).

### 5.4 P8-4 판정: 규칙 기준선 직접 대조(결정 4단계-1, 감사 B-1)
근거 폴더 `ed8_design/p84_suite_T8pppp_wt_7ea78232/`(SHA256SUMS `47a0b48401eca2ee52db367132efe681decc11647efbc662aee494029cfc46c3`, 17개). 이 개정 작성 중 다시 재어 17개 모두 SUMS와 같고 목록 밖·결측 파일은 0이다. 실행 출력 원본은 러너 폴더 `~/.claude/runners/outrigger-ed8/p84wt_7ea78232/out/`이고, 근거 폴더는 그 사본이다(메인이 복사).

**(1) 종료와 상태**
| 항목 | 값 | 근거 |
|---|---|---|
| `p84.done` | `exit=0 wall_s=6518` | `p84.done`(`7da4e192…`) |
| driver log | `[before] head=7ea78232… status_lines=0`(21:15:59), `[run] end exit=0 wall_s=6518`(23:04:37), `[after] status lines=14 pycache lines=13 head=7ea78232…` | `p84wt_driver.log`(`4c5862f4…`) |
| 실행 뒤 ignored 14줄 | `.hypothesis/` 1 + `__pycache__` 13(C8 원형 run과 같은 꼴). 메인이 지웠다(O8-33) | `git_after.txt`(`715a7102…`), `pycache_paths.txt` |
| `suite_record.json` | side run, worktree `ed8-judge4`, head `7ea78232…`, `worktree_tests_exit` 1(실패 시험 있음 = pytest 종료 1. C8 원형 run도 1), junit sha `dfe7fc14…` | `suite_record.json`(`83ccb485…`) |

**(2) `suite_judgement.json`(`c7011ae5…`)** — 규칙 364행의 멈춤 조건(새 실패·핵심 미통과·새 건너뜀)을 보는 판정 출력이다.
| 항목 | 값 |
|---|---|
| `status` | `pass` |
| `findings.new_failure` / `core_not_passing` / `new_skip_or_xfail` | `[]` / `[]` / `[]` |
| `inputs.baseline_list.sha256` | `7fce20f4ab74c6e2137a9cd29d7e60e18d6459cce00b88d774618102fe0ae953`(규칙 기준선 `p84_suite_41e107e9_56849248/base/existing_failures.txt`와 같음) |
| `inputs.junit.sha256` | `dfe7fc14833d8bae081ccdae0e0c8e69534987ca34c4ad3fb82f6322c416ea7a`(근거 폴더 `junit.xml`을 다시 잰 값과 같음) |
| `counts` | 시험 9119: 통과 9102, 실패 2, 오류 0, 건너뜀 15, xfail 0 |
| `existing_failures_record` | 실패 2 = `test_d8x_diag::test_rerun_gives_the_stored_command_hash`, `test_record::test_default_snapshot_directory_is_results_states`(둘 다 기준선 목록 failed). 건너뜀 15는 모두 기준선 목록 skipped |
| 핵심 패턴 | `test_jp3_*`, `test_ed6_*`, `test_run_v5*`, `test_lock_start_b*`, `test_c2*`, `test_extend_start_bound*`(판 6 정오 2 2-2) |

- `test_hydraulics_flow_limit_run::test_coupled_batch_rows_and_resume`는 통과했다(감사 M-2의 기대와 같음. 정식 실행의 실패는 판정 worktree에 `07_results`가 없던 탓이다).

**(3) `worktree_tests.md` 머리**: worktree `ed8-judge4`, 데이터 root 메인 checkout, 바꾼 폴더 `07_results`. pytest 6504.2 s, 시험 9119. probe `outrigger_sim` worktree. 실행 중 바뀐 데이터 경로 47회, 원본 불변 True, 실행 폴더 삭제 False. 오류 2·경고 44·참고 287.

**(4) 관문 시험(`junit_skips_critical.json`, `3bf212f9…`)**: critical 7패턴의 `critical_skipped` 0, `critical_absent` 0(findings에 `critical_absent` 범주 없음, 아래 이름별 수로 7패턴 모두 1개 이상; 재감사 R′-5), `xpassed` 0. 7패턴의 시험이 모두 실행돼 통과했다(이 개정에서 `junit.xml`을 이름·상태로 다시 셈: `test_p86_first_round_scale_stiffness_equals_the_replay` 1, `test_p8_10_` 2, `test_ed8_run_path` 4, `test_ed8_gate_p80_key` 17, `test_ed8_impl::test_psw_*` 2(N-1 전제 둘), `test_ed8_harness::test_switch_off_runs_keep_the_stored_hashes_and_keys` 1(P8-0 8 job), `test_ed8_harness` 전체 6). 핵심 패턴에 `test_ed8_*`가 없어 이 확인을 따로 둔다.

**(5) 정식 실행과의 대조**(`junit_ed8_compare_T8pppp_formal_vs_wt.txt`, `a6a1b10a…`): `test_ed8_*` 354개의 상태가 T8⁗ 정식 junit과 같다(둘 다 354 통과, changed 0, only_A 0, only_B 0).

**(6) 규칙 기준선 대비**(`junit_compare_rule_baseline_vs_wt.txt`, `d9511e0f…`; A = `p84_suite_41e107e9_56849248/base/junit.xml` 8782, B = 이번 9119)
- changed 0, B에만 있는 시험 338개는 모두 통과.
- A에만 있는 시험 1개: `test_ed7_adoption::test_both_candidates_qualifying_is_not_decided`.
  - git 기록(판정 checkout `ed8-judge4`, `git log -S … 41e107e9..7ea78232 -- 05_tests/unit/test_ed7_adoption.py`): T8 `ecf6c142`(2026-11-26 22:50:30)에서 없어졌다. 이 커밋은 판 7 판정 커밋 `60ebb4a4`의 판 7 판정 도구와 시험을 그대로 가져왔다(커밋 메시지). `git diff 41e107e9 ecf6c142`에서 이 시험(본문: 개정 5 전까지 `undecided`)은 세 시험 `test_both_candidates_qualifying_and_equal_keep_arm_2`, `…_the_better_one_is_adopted`, `…_with_crossing_failures_keep_arm_2`(개정 5의 결정 꼴)로 바뀌었다. 셋은 이번 실행에서 통과다. `ecf6c142` 뒤 `7ea78232`까지 이 파일과 `ed7_condition3_adoption.py`를 바꾼 커밋은 없다.
  - P8-4 영향 판단: 없음. 규칙 364행의 멈춤 조건은 새 실패·핵심 미통과·새 건너뜀이고, 기준선에만 있는 시험은 셋 어디에도 들지 않는다. 이 시험은 핵심 패턴 밖(`test_ed7_*`)이고, 바뀐 곳은 T8 범위(11.2: `04_scripts` 판정 도구와 `05_tests`) 안이며 실행 경로 밖이다(P8-11). `suite_judgement.json` findings도 비어 있다. 기록으로 둔다.

**(7) C8 원형 run과의 조건 동일성**(C8 원형 = `p84_suite_41e107e9_56849248/run_p84.ps1`·`p84_driver.log`·`run/`)
| 조건 | C8 원형 run | 이번 재실행 | 판단 |
|---|---|---|---|
| 호출 | `run_p84.ps1` → `full_suite_ed8.ps1 -Side run -Worktree … -OutDir … -ExpectCommit … -BaselineList … -BaselineSha256 …` | `p84wt_runner.ps1` → 같은 스크립트·같은 인자 | 같음 |
| `full_suite_ed8.ps1` | `ed8-impl` 경로 | 같은 경로. 지금 blob `232dbc2c…` = C8 트리의 blob(`git ls-tree 56849248`), `ed8-impl` HEAD = C8, 작업 트리 수정 없음 | 같음 |
| `tools/verif/worktree_tests.py` | 실행 때 sha 기록 없음 | sha256 `991c3833…`, mtime 2026-11-25 16:46:54 KST(두 실행 시작보다 앞, 이 개정에서 다시 잼) | 같음(mtime 기준) |
| 시험 인터프리터 | Chrono-dev(`full_suite_ed8.ps1` 21행) | 같음 | 같음 |
| 실행 꼴 | 직렬 pytest, affinity·우선순위 변경 없음, `PYTHONDONTWRITEBYTECODE=1`(37행) | 같음(러너 3-5행 주석, 같은 스크립트) | 같음 |
| 기준 목록 | `p84\base\existing_failures.txt` `7fce20f4…` | 같은 파일, 러너가 실행 전 sha 확인(31-32행) | 같음 |
| 대상 worktree | 새 detached `ed8-suite-c8`(C8 `56849248`) | 잠긴 판정 checkout `ed8-judge4`(T8⁗ `7ea78232`), 시작 전 `status --porcelain --ignored` 0줄 | 다름(대상 커밋이 다르므로 설계상) |
| numba 캐시 | `p84\numba_cache`, base 쪽 실행과 공유(base가 먼저 채움) | 새 폴더 `p84wt_7ea78232\numba_cache` | 다름 |
| 메인 자료 시점 | 11:57:35~13:45:33 | 21:15:59~23:04:37 | 다름 |
| pytest 시간 | 6458.9 s | 6504.2 s(러너 wall 6518 s) | 기록 |
| 시험 수 | 8789 | 9119(= 기준선 8782 + B에만 338 − A에만 1) | 기록 |
| worktree_tests 종료 / probe | 1 / `outrigger_sim` worktree | 1 / 같음 | 같음 |
| 바뀐 데이터 경로·원본 불변·실행 폴더 삭제 | 47회·True·False | 47회·True·False | 같음 |
| 발견 범주 | 오류 `test_failed` 2; 경고 `data_literal_not_rebased` 29, `skipped` 15; 참고 `no_data_paths` 275, `probe_worktree` 1, `rebase_unmatched` 1 | 같음, 다만 `no_data_paths` 285 | `no_data_paths` +10은 C8 → T8⁗에서 더해진 시험 파일 10개(`git diff --diff-filter=A 56849248 7ea78232 -- 05_tests/unit`)와 같다. 나머지 범주는 같음 |
| 실행 뒤 ignored | `.hypothesis/` + `__pycache__` 13 | 같음(14줄) | 같음 |

**(8) 판정**: P8-4 **통과**. 규칙 364행의 멈춤 조건(새 실패·핵심 미통과·새 건너뜀)이 모두 0이다(`suite_judgement.json` status pass, p84.done exit 0). 5.3의 사슬 근거는 보조다. 2.2의 N-1 전제 시험 둘과 P8-0 8 job 시험, P8-6·P8-10·P8-11 시험도 이 junit에서 통과했다.

## 6. 경로 2 대조
- 9:332의 경로 2 범위는 census J-P3 판정 집합(C-J 388, C-S 판정 4설정 184, C-D 24, C-G 171), **사례 재생(P8-2)**, G′, 12a·12b, T-JR-12b다.
- 관문별로 보면 다음과 같다.

| 관문 | 경로 2 범위 | 상태 | 규칙의 시점 |
|---|---|---|---|
| P8-0, P8-1, P8-4, P8-5, P8-6, P8-8, P8-10, P8-11, P8-15, P8-16, l1ref | 아님 | – | – |
| **P8-2 cases J-P3** | **예**(9:332 "사례 재생(P8-2)") | 경로 1 통과(판정 행 10, 침범 0). 경로 2 미실행 | 정하지 않음. census만 "S8-C 전에 끝낸다" → census 경로 2와 함께 S8-C 전(결정 4단계-2) |

- 판정 정의 대조: 4단계에서 판정 정의(판정 집합·0건·결측 처리·상태 이름)를 바꾼 개정은 없다.
  - D-1은 구현이 봉인 문면을 따르게 한 것이다(결정문 4, 보충 3).
  - D-2는 P8-0 도구 결함 처리와 P8-5 판정 불가 인정이다.
  - 그래서 판정 정의를 바꾼 [정의] 문장은 없다. 다만 P8-2 사례 정체는 6.1의 원문 인용 둘을 넘긴다.
- 넘김 범위: 규칙 정의 문장 9:331-334, 판 7 11절 정의 문장, 판 7 정오 1 [정의 E7-P2-1·2], "J-P3는 병합하지 않고 줄 단위로 판정한다". 그리고 D-1 보충 1·2항 문장(C-D 24줄; 5.1:220, 5.2:234, 9:332), 6.1 [정의 P8-2-1]·[정의 P8-2-2](원천 문서에서 메인이 직접 옮김)이다. 경로 1 코드·줄 번호·출력, 이 판정서의 재집계 값은 넘기지 않는다.
- **경로 2 작성자가 열면 안 되는 자료**(규칙 9:335, 감사 M-8): 이 판정서, `ed8_design/stage4_judgement/` 재집계 출력, `j9_runs/56849248/judge_2263b246/`·`judge_7ea78232/`, `j9_runs/56849248/impl_cases_a1/`, 4단계 감사 hand-back(`ed8_design/audit_stage4_judgement/`, 그 밖의 4단계 감사 원문). 개정 4에서 넓힘(재감사 M′-4, 사용자 결정 2026-11-27 "이 판정서에서 넓힘"):
  - 경로 1 판정 코드: worktree `.claude/worktrees/ed8-judge`·`ed8-judge2`·`ed8-judge3`·`ed8-judge4`, 같은 이름의 브랜치, T8 계열 커밋(T8 `ecf6c142`·T8′ `2bf16b31`·T8″ `5955f25b`·T8‴ `2263b246`·T8⁗ `7ea78232`)의 blob(`jp3_ed8_judge.py` 등)
  - 판정 전 점검: `ed8_design/stage4_prejudge/`, `stage4_prejudge_t8ppp/`, `stage4_prejudge_t8pppp/`
  - 경로 1 도구 구현 보고: `ed8_design/t8ppp_evidence/`, `t8pppp_evidence/`
  - 경로 1 코드 줄을 인용한 감사: `ed8_design/audit_t8ppp/`, `ed8_design/audit_prerun/`, 이 감사 폴더 `ed8_design/audit_stage4_judgement/`(커밋 전 감사·재감사 원문)
  - 실행 출력 sha 목록과 백업: `j9_runs/56849248/RUN_ALL.SHA256SUMS`, `j9_runs/56849248_LOCAL_ONLY.SHA256SUMS`, 백업 `C:\Users\jinbeom\.claude\backups\outrigger-ed8\j9_runs_56849248\`
  - 4단계 러너: 사본 `ed8_design/stage4_runner/`와 원본 `~/.claude/runners/outrigger-ed8/stage4/`
  - 규칙 9:335 범주 전부(경로 1 코드·출력·브랜치·blob과 감사가 인용한 경로 1 줄). 위 목록에 없더라도 이 범주에 들면 열지 않는다. 공유할 결정 문장(D-1 보충 1·2항, 6.1 [정의] 등)은 메인이 원천에서 직접 옮긴다.
- **메인은 경로 2를 시작하기 전에 이 경로들을 블라인드 목록(`.claude/blind_paths.json`)에 다시 넣는다.** 블라인드 목록은 2026-11-27 20:50:46에 비웠으므로 지금은 기계적 차단이 없다.
- 경로 2 작성자가 고를 판정 집합은 판 8 J-P3 10설정이고, 규칙 문장에서 이끌어 낸다(verif_t8ppp 5항 표). P8-2는 E·F × {VBN, LSN1~4} 10줄이다(규칙 363행. E·F 정의 문장은 6.1·확인 필요 A).
- 이후 단계로 넘길 것: census 단계별 J-P3 판정 행 수가 388/184/24/171이고 `rev7_unjudged_setting_runs`가 0인지(verif_t8ppp K-1). 도구는 census에서 기대 행 수를 단언하지 않으므로 6단계 판정서에서 확인 항목으로 둔다.

### 6.1 경로 2 넘김 문장(P8-2 사례 E·F, 사용자 결정 2026-11-27)
- 아래 두 [정의] 문장은 원문 그대로이고 해석을 더하지 않는다. 메인은 이 문장을 두 원천 문서에서 직접 옮겨 넘긴다. 이 판정서는 경로 2 작성자에게 넘기지 않는다(6절 열면 안 되는 자료).
- 봉인 규칙 v8 안에서 "사례 E·F"가 나오는 곳은 12절 P8-2 행(363행) 하나뿐이다(규칙 전문을 `E·F`·`사례 E`·`사례 F`로 검색). 규칙 262행·268행·423행의 "E"는 층 E(E 후보 사건)이고 사례 E가 아니다.

| # | [정의] 문장(원문 그대로) | 출처 |
|---|---|---|
| [정의 P8-2-1] 사례 정체 | "E = R12 bottom-FL-Fs4 o0.0" / "F = `j9_case_f` FR 행" | 판 7 정오 1 `06_analysis/02_control/j_p3_cause/jp3_remedy_spec_v7_erratum1.md`(sha256 `74c49bdaddf3fa63feeb70dd24b04823d517df2dbdc7b72c7592e70b1ef81a5b`, `.sha256`과 같음) 1-7 절 108행의 사례 정체 부분. 같은 행의 판 6 설정 집합·줄 수 부분(각 사례 뒤 "× {VBL, LSL1~4} 5줄")은 옮기지 않았다 |
| [정의 P8-2-2] 판 8 설정 집합과 줄 수 | "사례 재생 E·F × {VBN, LSN1~4} 10줄 J-P3 판정 키 0" | 판 8 봉인 규칙 `06_analysis/02_control/j_p3_cause/jp3_remedy_spec_v8_rules.md`(sha256 `35f9eba8f98f93ddb0fa850ff60844ebd7a443f819febcdf0906a5502c121520`) 12절 363행 P8-2 행 예측 칸. 행 전체: `| P8-2 | 사례 재생 E·F × {VBN, LSN1~4} 10줄 J-P3 판정 키 0 | 판정(관문) | > 0 |` |

- 판 사이 설정 이름의 대응은 규칙 문서에 적혀 있지 않음(사용자 결정 2026-11-27로 두 원문을 나란히 인용).
- **고정 상태: 고정**(사용자 결정 2026-11-27, 8.2 A 결정됨).

## 7. 판정서 커밋에 넣을 근거 폴더

| 폴더(`06_analysis/02_control/j_p3_cause/` 아래) | git | SUMS sha256 | 메모 |
|---|---|---|---|
| `ed8_design/t8ppp_evidence/` | 미추적 | `cc09451b…` | T8‴ 구현 보고 `aba8232f` |
| `ed8_design/t8pppp_evidence/` | 미추적 | `4b1a75a2…` | T8⁗ 구현 보고 `a7c0defd` |
| `ed8_design/control_d1_settings/` | 미추적 | `134c0766…` | D-1 |
| `ed8_design/control_p80p85/` | 미추적 | `d83d6cba…` | D-2 |
| `ed8_design/stage4_prejudge/` | 미추적 | **없음**(커밋 직전 작성) | 판정 전 점검 `prejudge_report.md` `19c4fc76` |
| `ed8_design/stage4_prejudge_t8ppp/` | 미추적 | **없음**(커밋 직전 작성) | 스모크·T8‴ 판정 명령 `87ddc7fe` |
| `ed8_design/stage4_prejudge_t8pppp/` | 미추적 | **없음**(커밋 직전 작성) | T8⁗ 판정 명령 `512c556b`, 대조 `8cfe3408` |
| `ed8_design/audit_t8ppp/` | 미추적 | **없음**(커밋 직전 작성) | 감사·결정 원문 8개(결정 4단계 `fd79bb76` 포함). 감사 폴더이므로 SUMS는 커밋 직전에 마지막으로 쓴다 |
| `ed8_design/p84_suite_41e107e9_56849248/` | 미추적 | `c144525b…` | P8-4 규칙 기준선 |
| `ed8_design/p84_suite_T8ppp_2263b246/` | 미추적 | `96f0d41c…` | |
| `ed8_design/p84_suite_T8pppp_7ea78232/` | 미추적 | `afc9330a…` | P8-4 정식(보조, 5.3) |
| `ed8_design/p84_suite_T8pppp_wt_7ea78232/`(새) | 미추적 | `47a0b484…` | **P8-4 판정 근거(5.4)**. 17개(러너 `out\` 사본, runner ps1, driver log, run_console.log, 대조 스크립트 2·출력 2, `junit_skips_critical.json`) |
| `ed8_design/stage4_runner/`(새) | 미추적 | **없음**(커밋 직전 작성, `--recursive`) | 4단계 러너 `~/.claude/runners/outrigger-ed8/stage4/` 사본 **넣음**(결정 4단계-3, 메인, O8-35): 21파일 = `run_stage4.ps1`, `steps_stage4.json`, `logs/` 19(단계 9개의 `.log`·`.done`과 `_runner.log`). 메인이 원본과 sha가 같음을 확인했고, 이 개정에서 파일 수 21을 다시 셈 |
| `ed8_design/stage4_judgement/`(새) | 미추적 | **없음**(커밋 직전 작성) | 재집계 스크립트·출력 7개, 메인의 `npz_local_only.py`(`71c27a51…`) + 이 판정서 md. md 확정 뒤 SUMS를 쓴다 |
| `ed8_design/audit_stage4_judgement/`(새) | 미추적 | **없음**(커밋 직전 작성) | 커밋 전 감사 hand-back `1624f762…`. 감사 폴더이므로 SUMS는 마지막에 쓴다 |
| `j9_runs/56849248/judge_2263b246/` | 미추적 | **없음**(커밋 직전 작성) | 8 json(대체됨) |
| `j9_runs/56849248/judge_7ea78232/` | 미추적 | **없음**(커밋 직전 작성) | 8 json(최종) |
| `j9_runs/56849248/_identity_checks/` | 미추적 | **없음**(커밋 직전 작성) | md 8개 |
| `j9_runs/56849248/` 실행 출력(9 단계 폴더, `.done` 9) | 미추적 | 단계 폴더 9개에 최상위 파일만 담은 SUMS가 있음(예: `impl_p80_a1` `b0161ef9…`, `l1ref_a1` `6be9a605…`). 폴더 전체는 `RUN_ALL.SHA256SUMS`(아래) | 전체 1047파일, 794.1 MiB(832.7 MB, 832,684,186 B) |

- **실행 출력 커밋(결정 4단계-3, 판 7 판정서 7.5 꼴, 감사 M-1)**
  - 단계 폴더 SUMS는 최상위 파일만 담는다. 그래서 T4h npz 906개(J-P3 판정 입력, cases 판정이 줄의 `t4h_file`로 읽음)와 `*.partial.jsonl`의 sha는 단계 SUMS에 없다. 판 7 판정서 7.5의 "단계 폴더 SUMS가 npz sha를 고정한다"와는 꼴이 다르다(감사 M-1).
  - 실행 폴더 전체 sha 고정: `j9_runs/56849248/RUN_ALL.SHA256SUMS`(sha256 `db24b030891fd43d0a9048afbb48d7cab9facdbf52fb4913910addc3ddd41ef7`, 1047줄. 그중 npz 906, `*.partial.jsonl` 4, `judge_*` 16, `_identity_checks` 8을 포함; 이 개정에서 줄 수·패턴별 건수만 다시 셈). 기존 단계 SUMS(인용됨)는 고치지 않았다.
  - 원격 한도(10^8 B) 초과 3파일 `l1ref_a1/L1_VBN.json` 204,050,544 B, `l1ref_a1/L1_VBN.json.partial.jsonl` 120,350,859 B, `l1ref_a1/L1a_VBN.json` 125,073,208 B: LOCAL_ONLY 목록 `j9_runs/56849248_LOCAL_ONLY.SHA256SUMS`와 백업 `C:\Users\jinbeom\.claude\backups\outrigger-ed8\j9_runs_56849248\`로 고정했다(메인, `large_outputs.py --apply`). `.git/info/exclude` 113·114행(112행은 주석, 재감사 R′-4)이 `L1_VBN.json`·`L1a_VBN.json`을 빼고, `L1_VBN.json.partial.jsonl`은 37행 `*.partial.jsonl`로 빠진다.
  - T4h npz 906개(`.gitignore:41 *.npz`로 git에서 빠짐): 메인이 백업 폴더의 repo 상대 경로 아래로 복사하고 같은 LOCAL_ONLY 목록에 더했다(사용자 결정 2026-11-27, O8-34). 복사 전에 RUN_ALL sha와 대조했고, 복사 뒤 사본 sha도 다시 재서 같았다(메인 확인). 스크립트 `ed8_design/stage4_judgement/npz_local_only.py`(sha256 `71c27a514bd65077ed8510da114187b2f497f2f34ded7454aeee27f6a65bdf92`). 메인은 scratchpad 사본(`main-npzbackup\npz_local_only.py`)으로 실행했고, 실행 뒤 같은 바이트를 근거로 복사했다(재감사 R′-2). `--apply`는 파일별로 판정하는 동안 앞 파일을 먼저 복사하므로, 문제가 생기면 백업만 일부 남고 목록은 그대로인 꼴이다. 이번 실행은 문제 0이라 영향이 없다.
  - **LOCAL_ONLY 목록(최종)**: `j9_runs/56849248_LOCAL_ONLY.SHA256SUMS`, sha256 `47ab36a572e7835490abe9dd192dff0c12f73a596afd76dcf334c7a7be679604`, 909줄 = 한도 초과 3 + npz 906. 앞 판(3줄, `7faba722…`)을 대체한다. 늘어난 목록의 사본도 백업 폴더에 있고 sha가 같다. 이 개정에서 다시 확인: 목록 sha와 줄 수, npz 906줄의 (sha, 실행 폴더 상대 경로)가 RUN_ALL의 npz 906줄과 모두 같음(차이 0), 백업 폴더의 npz 파일 수 906.
  - 그 밖에 ignore로 빠지는 파일: `*.partial.jsonl` 3(`L1_VBN0`·`L1a_VBN0`·`L1a_VBN`, `.git/info/exclude:37`). sha는 RUN_ALL에 있고, 백업 폴더에 사본이 있다.
  - 이로써 결정 4단계-3("한도 초과 3파일과 npz는 LOCAL_ONLY 목록과 백업으로 sha를 고정, 나머지 커밋, 4단계 러너 사본을 근거에 넣는다")을 채웠다.
  - 나머지 실행 출력(판정 출력, 단계 jsonl·json·SUMS, `.done`)은 커밋한다.
- **커밋 직전에 SUMS를 쓸 폴더**(감사 M-7: 7개 + `_identity_checks`)
  1. `ed8_design/stage4_prejudge/`
  2. `ed8_design/stage4_prejudge_t8ppp/`
  3. `ed8_design/stage4_prejudge_t8pppp/`
  4. `j9_runs/56849248/judge_2263b246/`
  5. `j9_runs/56849248/judge_7ea78232/`
  6. `j9_runs/56849248/_identity_checks/`
  7. `ed8_design/stage4_judgement/`(이 md 확정 뒤)
  8. `ed8_design/audit_t8ppp/`(감사 폴더, 마지막)
  - 이 개정에서 더해진 새 폴더: `ed8_design/stage4_runner/`(사본 넣음, 21파일), `ed8_design/audit_stage4_judgement/`(감사 폴더, 마지막).
  - `stage4_runner/`는 `write-sums --recursive`(21개)로 쓴다. 기본(최상위만)으로 쓰면 `logs/` 19개가 빠진다(재감사 M′-1). 나머지 SUMS 대상 폴더에는 하위 폴더가 없다.
  - 참고: RUN_ALL은 이 SUMS들보다 먼저 쓰였으므로 4~6의 새 SUMS 파일은 RUN_ALL 목록에 들지 않는다. RUN_ALL의 기존 줄은 그대로 유효하다.
- 판정서 커밋 전 verif 감사의 hand-back은 `stage4_judgement/` 밖의 별도 폴더(`ed8_design/audit_stage4_judgement/`)에 두었다. 그래야 인용 SUMS가 낡지 않는다.
- `git status --ignored`로 인용 파일이 ignore에 걸려 빠지지 않는지 메인이 본다. 기대: ignore에 걸리는 것은 npz 906·partial 4·한도 초과 2뿐이고, 판정 출력·단계 jsonl·SUMS·junit·판정서는 걸리지 않는다(감사 7절 처리 순서 7).

## 8. 결정 기록과 남은 확인 필요

### 8.1 앞 초안 확인 필요 1~5: 결정됨(결정 4단계, `fd79bb76…`)
1. **P8-4 판정 근거**: 결정됨(결정 4단계-1). (나) T8⁗ 깨끗한 checkout에서 worktree_tests 방식으로 다시 돌려 규칙 기준선과 직접 대조하고, 그 결과로 판정한다. 사슬 근거는 보조. → 실행함, 통과(5.4). 2.2의 N-1 전제 시험 귀속도 5.4를 따른다.
2. **P8-2 경로 2 시점과 4단계 표기**: 결정됨(결정 4단계-2). census 경로 2와 함께 S8-C 전에 한다. 그때까지 "경로 1 통과, 경로 2 대조 대기"(1절 10행, 6절).
3. **실행 출력 커밋 범위**: 결정됨(결정 4단계-3). 판 7 7.5 꼴, 한도 초과 3파일과 npz는 LOCAL_ONLY 목록과 백업으로 sha 고정, 나머지 커밋, 4단계 러너 사본을 근거에 넣는다. → 처리 끝남(7절: LOCAL_ONLY 909줄 `47ab36a5…`, 백업, 러너 사본 `ed8_design/stage4_runner/`).
4. **공개 번호**: 결정됨(결정 4단계-4). O8-13~로 이어 붙인다(4절).
5. **FS24·G4 `effective_shape`**: 결정됨(결정 4단계-4). 도구를 고치지 않고 G′ 판정서 기록 칸에 적는다(4.3).
- 열린 확인 사항 4건(사용자 결정 2026-11-27; 커밋 전 감사 확인 필요 3건 + 도구 개선 범위 1건): (1) 경로 2 E·F 정의 문장은 규칙에서 원문 그대로 뽑아 6.1에 고정 → 아래 A. (2) l1ref `identity_sources`는 5.2 아래 표로 옮김. (3) P8-5 판정되지 않은 9쌍은 건수·사유·근거 sha만, 값은 옮기지 않음(1절 4행, 2.4). (4) 도구 개선은 판정서 범위 밖(커밋 뒤 따로). 그 뒤에 생긴 8.2 A(E·F 인용 방식)·B(npz 백업)도 사용자 결정으로 닫혔다.

### 8.2 남은 확인 필요(이 개정에서 생김)
- **A. 사례 E·F 정의 문장**(6.1): 봉인 규칙 v8에는 "사례 E·F"를 정하는 정의 문장이 없고, 363행의 이름만 있다. 경로 2 넘김에 무엇을 E·F 정의로 줄지(예: 감사가 원천으로 본 판 7 정오 1 1-7의 정의 문장을 [정의]로 더함) 사용자가 정한다. 정하기 전에는 P8-2 경로 2를 시작할 수 없다(경로 2는 경로 1 출력 없이 10줄을 골라야 한다).
  - 개정 2(사용자 결정: 판 7 정오 1의 1-7에서 원문 발췌): 원천 `jp3_remedy_spec_v7_erratum1.md`(sha256 `74c49bdaddf3fa63feeb70dd24b04823d517df2dbdc7b72c7592e70b1ef81a5b`, 다시 잰 값이 `.sha256`과 같음) 1-7(105-114행)을 대조했다. 사례 이름(E·F)과 줄 수(사례당 5줄, 합 10줄)는 363행과 맞는다. 그러나 1-7의 정의 문장이 적는 설정 집합은 판 6 `{VBL, LSL1~4}`(108행)와 판 7 `{VBM, LSM1~4}`(106·111행)이고, 363행의 `{VBN, LSN1~4}`와 문면이 다르다. 지시(집합이 어긋나면 고치지 않음)에 따라 6.1은 고치지 않았고 고정 상태도 "불완전"으로 둔다. 판 사이 설정 이름의 대응을 넘김 문장으로 어떻게 적을지 사용자 결정이 필요하다.
  - **결정됨**(개정 3, 사용자 결정 2026-11-27): 두 원문을 나란히 인용한다. 판 7 정오 1 108행의 사례 정체 부분과 판 8 규칙 363행의 설정 집합·줄 수를 6.1에 [정의 P8-2-1]·[정의 P8-2-2]로 고정했다. 판 사이 설정 이름의 대응은 쓰지 않는다. 6.1 고정 상태는 "고정"이다.
- **B. npz 906개의 백업**(7절): 닫힘(사용자 결정 2026-11-27: 백업에 복사하고 목록에 추가). 메인이 처리했고(O8-34), LOCAL_ONLY 목록은 909줄 `47ab36a5…`다.

## 9. 위임 필요·메인 세션 권고
- **verif-protocol-auditor**: 커밋 전 감사(`1624f762…`)를 받았다. 이 개정의 반영을 다시 볼지(짧은 재확인)는 메인이 정한다.
- **integrity-checker**: 판정서와 근거 폴더 SUMS·인용 sha 정합. 특히 7절 "커밋 직전에 SUMS를 쓸 폴더"(SUMS 없는 7개 폴더 + `_identity_checks`, 새 폴더 2)를 본다.
- **경로 2 담당(메인이 정함)**: P8-2 J-P3(결정 4단계-2, census 경로 2와 함께 S8-C 전). 넘길 것은 6절·6.1의 규칙 정의 문장뿐이다. 시작 전에 6절의 자료를 블라인드 목록에 다시 넣는다.
- **메인 세션 권고**
  - P8-4 재실행: 실행함(결정 4단계-1). 약 108분(wall 6518 s, C8 원형 6458.9 s). 출력 `~/.claude/runners/outrigger-ed8/p84wt_7ea78232/`, 근거 사본 `ed8_design/p84_suite_T8pppp_wt_7ea78232/`.
  - large_outputs.py `--apply`, LOCAL_ONLY·백업(npz 906 포함, 909줄 `47ab36a5…`), RUN_ALL: 메인이 했다(7절, O8-34).
  - 4단계 러너 사본: `ed8_design/stage4_runner/`에 넣음(21파일, 메인, O8-35).
  - SUMS 쓰기(7절 목록, 감사 폴더는 마지막)
  - integrity → master 커밋
- 5단계는 사용자 결정 뒤에만 시작한다.

## 10. 이 초안 작성의 공개(읽은 파일·검색 범위)
- **Read(메인 checkout)**
  - `.claude/blind_paths.json`(목록 비어 있음 확인)
  - 규칙 v8 1-100·180-459행, v7 1015-1024행
  - `audit_t8ppp/` 결정 2개·verif 3개 전체(integrity 2개는 Grep 요약 줄만)
  - `control_p80p85/control_p80p85.md`·`p80p85_decision_draft.txt` 전체
  - `control_d1_settings/control_d1_settings.md`·`d1_decision_draft.txt` 전체
  - `t8pppp_evidence/impl_report_t8pppp.md` 전체
  - `audit_prerun/`: `control_nb1_decision.md` 100-256행, `control_nb1_followup.md`·`smoke_v0twin_report.md`·`stats_nb1_addendum.md` 전체, `stats_nb1.md` 1-20·225-257행, `verif_c8_t8.md` 1-60·77-88행
  - `stage4_prejudge/prejudge_report.md` 전체, `sums_notes_20261127.md`
  - P8-4 폴더: `p84.done`, `p84_step.ps1`, `p84_driver.log` 2개, `junit_compare` 2개, `suite_judgement.json`
  - 판정 출력: `judge_7ea78232/` 8개(l1ref는 일부 줄), `judge_2263b246/p80.json`(Grep), `impl_scope.done`, `cases_jp3_rows_smoke.json`
  - 프로젝트 메모리 `ed8-stage4-authorization-20261127.md`
- **Read·Grep(ed8-judge4, 읽기만)**: `jp3_ed8_gate_judge.py` 320-519행과 상수 Grep, `run_v5.py` 755-774행, `jp3_t8_rules.py` `has_fallback_event`(59-79행)
- **Grep 범위**
  - `ed8_design`(glob `*.md`, 형상 기본값 패턴), `audit_prerun`(glob `*.md`·`verif_*.md`)
  - 단일 파일: `control_t8p_decisions.md`, `t8p_report.md`, `impl_report_t8ppp.md`, `stats_nb1.md`, `stats_nb1_addendum.md`, `control_nb1_*.md`, `prejudge_report.md`, `l1ref.json`, p84 러너 ps1
- **Glob**
  - `audit_t8ppp`, `judge_7ea78232`, `control_p80p85`, `control_d1_settings`, `audit_prerun`, `t8ppp_evidence`, `t8pppp_evidence`, `stage4_prejudge*` 3개, p84 폴더 3개, `impl_report_ed8`(`**/*.xml`)
  - `j_p3_cause`(패턴 `jp3_remedy_spec_v8*`, O8-31 (2))
- **PowerShell**
  - `j9_runs/56849248` 최상위와 단계 폴더 8개의 목록, 재귀 파일 수·크기(블라인드 해제 뒤)
  - `Get-FileHash`
  - `L1_VBN0.json` 첫 200바이트(구조 확인)
  - junit XML 파싱(시험 이름)
  - `junit_skips.py` 1회: 종료 1(기존 실패 2 때문). 출력에 건너뜀 이름과 기존 실패 assert 문구가 나왔는데, 시험 자료의 해시 앞부분이고 판정 자료 값은 아니다
- **스크립트**
  - scratchpad `peek_keys.py`: 6개 파일의 키 이름·라벨 수만. 지웠다
  - 5.1의 스크립트 3개와 대조 스크립트 재실행
  - 판정 도구는 돌리지 않았고 판정 모듈을 import하지 않았다
- **Bash**: `git log`, `worktree list`, `check-ignore`, `status --porcelain`. 파이프 1회는 O8-31 (1)이다
- **쓰기**
  - `ed8_design/stage4_judgement/` 7개(스크립트 3, 출력 4)
  - 에이전트 메모리 `suite-baseline-runner-mode.md`, `path2-scope-per-gate.md`와 MEMORY.md 2줄
  - 잠긴 worktree·규칙 파일·다른 근거 폴더에는 쓰지 않았다
  - scratchpad `control-s4judgement\`는 지웠다(`Test-Path` False)
- 경로 2 도구는 열지 않았다. 프로세스를 종료하지 않았다.

### 10.1 개정 1 작성의 공개(2026-11-27, 블라인드 목록 빈 상태)
- **Read**: 커밋 전 감사 `verif_stage4_judgement_precommit.md` 전체, 결정 4단계 `fd79bb76` 전체, 이 판정서 전체, 규칙 v8 328-377행, `p80p85_decision_draft.txt` 70-96행, `control_p80p85.md` 240-255행, P8-4 재실행 근거 폴더의 작은 파일 전부와 `worktree_tests.md` 1-361행, `p84_suite_41e107e9_56849248/`의 `run_p84.ps1`·`p84_driver.log`·`run/suite_record.json`·`run/worktree_tests.md` 머리·`SHA256SUMS`, `judge_7ea78232/l1ref.json` 1-70행, `impl_p85_a1/SHA256SUMS`, `.git/info/exclude`(Grep)
- **Grep**: 규칙 v8 단일 파일(`E·F|사례 E|사례 F`, `사례|R12|cases`), `p85.json` 키 이름(`-o`), `RUN_ALL.SHA256SUMS` 건수 모드(`\.npz$`, `partial|_identity_checks|judge_`), `p80p85_decision_draft.txt` 단일 파일
- **Glob**: `p84_suite_T8pppp_wt_7ea78232`, `p84_suite_41e107e9_56849248`, `ed8_design`(패턴 `*stage4*`), 러너 `~/.claude/runners/outrigger-ed8/stage4`
- **git(Bash, 파이프 없음)**: `ed8-judge4`에서 `log -S`·`show --stat`·`diff 41e107e9 ecf6c142 -- test_ed7_adoption.py`·`log -- test_ed7_adoption.py ed7_condition3_adoption.py`·`status --porcelain --ignored`(0줄); 메인 checkout에서 `log -1`(시각 3개), `diff --diff-filter=A/AM --name-only 56849248 7ea78232 -- 05_tests`, `ls-tree 56849248 full_suite_ed8.ps1`; `ed8-impl`에서 `rev-parse`·`status`·`hash-object`
- **PowerShell**: `Get-FileHash`(인용 파일 6개, LOCAL_ONLY·RUN_ALL), LOCAL_ONLY 목록 내용, RUN_ALL 줄 수, 백업 폴더 파일 목록·크기, `impl_p85_a1`·`audit_t8ppp` 파일 이름 목록, `full_suite_ed8.ps1`의 패턴 줄(`Select-String`), mtime 변환
- **스크립트**(python-dev `-X utf8 -I -B`, scratchpad `control-expert-stage4fix\`): `facts.py`(새 근거 폴더 SUMS 대조, `worktree_tests.md` 발견 범주 수, 인용 sha, `l1ref.json` `identity_sources` 요약), `crit.py`(재실행 junit의 관문 시험 이름·상태 수). 판정 모듈은 import하지 않았고 판정 도구는 돌리지 않았다. 두 스크립트와 출력은 작성 뒤 지웠다(scratchpad 하위 폴더 `Test-Path` False)
- **쓰기**: 이 판정서만 Edit로 고쳤다. 근거 파일(재집계 스크립트·출력, 대조 출력)과 SUMS가 있는 근거 폴더, 잠긴 worktree, 규칙 파일에는 쓰지 않았다
- 판 7 정오 1과 경로 2 도구는 열지 않았다. 프로세스를 종료하지 않았다

### 10.2 개정 2 작성의 공개(2026-11-27)
- **Read·Grep**: 봉인 규칙 문서 `jp3_remedy_spec_v7_erratum1.md`(Grep `1-7|E·F|사례 E|사례 F`, Read 105-114행). 경로 1 코드·출력이 아니다(메인 지시)
- **PowerShell**: `Get-FileHash`(정오 1과 `.sha256`, LOCAL_ONLY 목록, `npz_local_only.py`, 백업의 목록 사본), LOCAL_ONLY 줄 수·npz 줄 수, LOCAL_ONLY와 RUN_ALL의 npz 906줄 (sha, 상대 경로) 대조(`Compare-Object`, 차이 0), `stage4_runner` 파일 수, 백업 npz 파일 수. 대조 중 목록 머리 4줄이 화면에 나왔다(경로 1 실행 출력 파일 이름 1개 포함, 이 판정서에는 옮기지 않음)
- **쓰기**: 이 판정서만 Edit로 고쳤다. 6.1은 고치지 않았다(8.2 A)

### 10.3 개정 3·4 작성의 공개(2026-11-27)
- **개정 3**: 새로 읽은 파일은 없다(재감사 R′-3). 6.1에 인용한 세 조각이 원천에 글자 그대로 있는지 `Select-String -SimpleMatch`로 확인했다(판 7 정오 1 108행, v8 규칙 363행; 둘 다 10.2 범위 안). `Get-FileHash`로 이 판정서 sha를 쟀다
- **개정 4**: 재감사 원문 `ed8_design/audit_stage4_judgement/verif_stage4_judgement_recheck.md`(`325b03fd…`) 전체를 읽었다. 이 판정서를 Grep(단일 파일, 고칠 행 찾기)했다. 그 밖의 파일·폴더는 열지 않았다
- **쓰기**: 이 판정서만 Edit로 고쳤다. 근거 폴더·scratchpad에는 쓰지 않았다. 프로세스를 종료하지 않았다

사용한 스킬: 없음
