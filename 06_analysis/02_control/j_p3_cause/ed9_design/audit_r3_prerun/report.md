# 판 9(436.9) 봉인 전 진단 실행 R3a·R3b·R3c·R4 — 실행 전 감사 (verif-protocol-auditor, 2026-11-28)

## 감사 요약
- 본 결과: 없음. 판정 대상 결과 값은 열지 않았다. 대신 다음을 보았다.
  - 저장 진단 jsonl 4개(`ed8_design\stage5_aa_diag\`)와 `v5\main.jsonl` V0 100줄: 키가 있는지와 줄 수, 태그의 서로 다른 값 수만 셌다. 값은 출력하지 않았다.
  - `r3c_jobs.json`: 설정 이름 분포를 셌다(V0 59).
- 대상: 판 9 봉인값을 재는 진단 실행 R3a(끔)·R3b(켬)·R3c(진단 59 job ×3)·R4(ed9 stage5 판정 도구 측정). 판정 실행이 아니다.
- 시점: 실행 전.
- 기준 문서: 판 9 규칙은 아직 봉인되지 않았다(S·T축은 "봉인 없음 — 사전 등록 아님"). 기준으로 삼은 문서는 다음과 같다.
  - 설계 입력: `control_cm_switch\report.md` ce692fc9, `stats_impl_check\report.md` 3ccbf233, decision_log 835행
  - 구현 보고: `impl_report.md` 0ee87231, `impl_report_2.md` 87e0479e
  - 판 8 규칙: `jp3_remedy_spec_v8_rules.md` 35f9eba8(`.sha256` e19aaa48)
- 코드: C9 86121e8f(`ed9-c9`, 잠김), T9 2deb5fd7(`ed9-t9`, 잠김), 진단 8e0bce46(`ed9-diag`, 잠기지 않음)
- 러너: `step_r3.ps1` 3ce05c58, `runner_p.ps1`·`runner_e.ps1`·`steps_p.json`·`steps_e.json`(compute-scheduler 배치안, 추가 대상)
- **판정: 차단 2 / 실행 전 수정 8 / 기록 8.**
  - 차단 B-1을 고치기 전에는 러너를 띄우지 않는다. 띄우면 각 러너 둘째 단계에서 멈추고, 재시도할 경로도 없다.
  - B-2는 실행 뒤 대조 ④가 반드시 `differs`로 끝나는 결함이다. 실행 전에 대조 방식을 고쳐야 한다.

## 발견 사항 (심각도순)

### 차단

**[차단][R·E] B-1. 두 러너의 aa2·aa3 단계에 `-JobsFile`이 빠졌다. run_v5가 인자 오류(exit 2)로 끝나 각 러너가 둘째 단계에서 멈춘다.**
- 근거
  - `C:\Users\jinbeom\.claude\runners\outrigger-ed9-r3\steps_p.json:3-4`(`r3a_ho_aa2`·`r3a_ho_aa3`), `steps_e.json:3-4`(`r3b_ho_aa2`·`r3b_ho_aa3`), `runner_p.ps1:25-26`, `runner_e.ps1:25-26`. 네 단계 모두 `-JobsFile` 인자가 없다.
  - Grep 패턴 `"id":"r3[ab]_ho_aa[23]".*JobsFile`: 0건(최종 보고 직전에 다시 확인).
  - `ed9-c9\04_scripts\04_hydraulic\coupled\run_v5.py:1152-1156`: `ED8_HELDOUT_AA_BATCHES`와 `ED9_JOBS_FILE_BATCHES`(`:488-489`, ed9 aa2·aa3 포함)는 `--jobs-file`이 필수다. 없으면 `parser.error`다.
  - 건조 실행으로 확인했다(`ed9-c9`, dynamics-dev `-I -B`, scratch NUMBA 캐시, 실행 뒤 `status --porcelain --ignored` 0줄).

    | 배치 | `--jobs-file` 없음 | `--jobs-file` 있음 |
    |---|---|---|
    | `ed8_heldout_aa2 --list` | `error: --jobs-file belongs to …`, exit 2 | 339 runs, exit 0 |
    | `ed9_heldout_aa3 --list` | exit 2 | 339 runs, exit 0 |

  - `impl_report_2.md:190-191`의 9절 명령표도 aa2·aa3에 `-JobsFile $K`를 적지 않았다. 원인이 된 것으로 본다.
- 실패 시나리오
  - P 러너: R3a `ho_v0`(678 run, 약 1시간)이 끝난다. 이어 `ho_aa2`에서 step_r3가 `ho_aa2_a1`을 먼저 만들고(`step_r3.ps1:46`), run_v5가 exit 2로 끝난다(`:63`). StopOnFail이라 R3a 나머지와 R3c가 모두 시작되지 않는다(`runner_p.ps1:199-201`). E 러너 R3b도 같다.
  - 같은 `-Root`·`-Step`으로 다시 돌리면 `ho_aa2_a1`이 이미 있어 exit 2로 거부된다(`step_r3.ps1:38-40`). `_a1`이 고정이라 둘째 시도 경로가 없다.
  - step_r3의 exit 2는 "출력 있음"과 "run_v5 인자 오류"를 함께 뜻해 원인을 가르기 어렵다(기록 R-3).
- 권장 조치(메인 / compute-scheduler-expert)
  - steps_p·steps_e의 aa2·aa3 네 단계에 `-JobsFile C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\keys_seal_41e107e9\heldout_g_ed8.json`을 넣고 러너를 다시 만든다.
  - 다시 만든 뒤 단계마다 같은 인자로 `run_v5.py <batch> [--jobs-file K] --list`를 건조 실행한다. 기대 건수: 678 / 339 / 339 / 7 / 100(이번 감사에서 확인한 값).
  - impl_report_2 9절 표의 정정은 python-expert에 맡긴다.

**[차단][R·E] B-2. 대조 ④(census 끔 ↔ 저장 main.jsonl, `--expect-switch off`)는 태그 비교 때문에 100줄 모두 `switch_mismatch`가 되어 `differs`(exit 1)가 확정이다.**
- 근거
  - `key_presence.py …\v5\main.jsonl --where job.setting=V0 --key controller_tag …` 결과: `controller_tag`가 V0 100줄 중 100줄에 없고, `d1_settings`도 100줄 모두 없다. `commands_sha256`·`final_phase`는 있다.
  - `compare_identity.py:69-82`: `expected_tag = stored.get("controller_tag")`가 None이다. 끔 비교에서는 새 줄의 `controller_tag`가 None이어야 같다고 본다.
  - C9 V0 줄에는 태그가 붙는다.
    - `verdict_runs.py:941-944`: 옵션 없는 run에도 `controller_tag`를 붙인다.
    - `test_ed9_cm_switch.py:88`: `controller_tag(None, plain) == "final_C4G2_LAS_K1"`.
  - 따라서 새 `ed9_census_v0_off` 100줄은 모두 `controller_tag` 불일치다. `compare_identity.py:195-196`에서 `switch_mismatch`가 `differs`로 이어진다.
  - impl_report_2 6절의 "main.jsonl V0 자기 대조(identical 100)"는 저장 파일끼리 비교한 것이라 이 문제가 드러나지 않았다.
- 실패 시나리오
  - 계획(`impl_report_2.md:152`·`:193` ④)은 identical을 기대한다. 그런데 하네스가 옛 실행본과 비트 단위로 같아도 ④는 `differs`가 된다.
  - 그러면 "C9 하네스가 저장 줄을 재현하는가"라는 질문의 답이 태그 차이에 가려진다. ⑤ census 켬↔끔은 영향이 없다.
- 권장 조치(python-expert)
  - `compare_identity.py`에 저장 줄에 태그 키가 없을 때의 규칙을 둔다. 예: `--stored-tag-absent <기대 V0 태그>`로 저장 None을 기대 태그로 바꾼다. 또는 ④에서는 태그 비교를 빼고 3필드만 본다고 명시하는 옵션을 둔다.
  - 어느 쪽이든 실행 전에 규칙 초안이나 실행 계획에 고정한다. 합성 시험(저장 줄에 태그 키 없음)도 더한다.

### 실행 전 수정

**[실행 전 수정][C·E] M-1. P/E 동시 배치에서는 끔·켬 비교마다 코어 종류가 함께 바뀐다(추가 대상 (1)·(3)).**
- 근거: 배치
  - R3a(끔)·R3c는 P `0x3FFF`(worker 7, R3c 4)다(`steps_p.json:2-9`).
  - R3b(켬)는 E `0x03FF0000`(worker 10)이다(`steps_e.json:2-6`).
  - 저장 C8 5단계 줄은 `0xFFFF`·8 P였다(`~\.claude\runners\outrigger-ed8\stage5\run_stage5.ps1:26-27`).
- 근거: 정체성 관문은 배치를 보지 않는다
  - `jp3_ed8_gate_judge.py:168-189` `step_output_problems`는 exit_code·commit·end identity·folder만 본다.
  - `jp3_ed8_judge.py:1625-1644` `batch_switch_problems`는 batch·d1_median만 본다.
  - `compare_identity.py`는 줄 내용만 보고 `.done`은 읽지 않는다.
  - 그래서 마스크·worker 차이는 어떤 관문에도 걸리지 않는다.
  - 기록은 남는다: `.done` `codes.mask`·`workers`(`step_r3.ps1:69`), 사이드카 `threads`·`affinity_mask`(`d8x_record.py:374-380` `run_identity`), r3c `log.json` `mask`·`workers`(`r3c_run.py:124-127`).
- 결과가 worker 수·코어와 무관하다는 코드 근거(추가 대상 (3))
  - job마다 단일 스레드다. `run_v5.py:46-48`이 `MKL/OMP/OPENBLAS/NUMBA_NUM_THREADS`를 기본 1로, `MKL_THREADING_LAYER`를 TBB로 둔다(setdefault). 사용자·시스템 환경에는 이 변수들이 없다(확인함). `verdict_runs.py:20-22`도 같고, `r3c_run.py:108-110`은 강제로 1을 둔다.
  - job마다 새 spawn 프로세스다(`maxtasksperchild=1`, `run_v5.py:1305`, `r3c_run.py:133`).
  - worker는 마스크 전체에 고정될 뿐 코어별로 나뉘지 않는다(`s9_soil_slope.py:1674-1692`).
  - job key는 `mask`·`t4h_dir`를 뺀다(`run_v5.py` RUNTIME_JOB_KEYS, `compare_identity.py:50`). 판정과 대조는 job key로 짝지으므로 `imap_unordered`의 줄 순서는 영향이 없다.
  - 그래서 worker 수(7·8·10)는 영향이 없다고 판단한다.
- 코어 종류(P 대 E)
  - [추정] i7-14700 하이브리드는 두 코어의 ISA가 같아 MKL·numba 경로가 같을 것으로 본다.
  - 이 하네스에서 P와 E가 비트 단위로 같다는 직접 증거는 저장소에서 찾지 못했다. `s6_control_spec.md:13725`는 E끼리 두 번 돌려 해시 20/20이 같았다는 기록이다.
- 실패 시나리오
  - 다음 비교가 모두 P와 E를 가로지른다: ② R3b(E) ↔ 저장 5단계(P), ③ same_shape_off(P) ↔ same_shape(E), ⑤ census_off(P) ↔ census(E).
  - 코어 효과가 있다면 C-m 효과와 섞여 `differs`가 나온다. stats 조건 5에 따라 멈추므로 결과가 잘못 확정되지는 않지만, 원인을 가를 수 없다.
  - 봉인 뒤 5단계 해시 재생("R3b와 같은 커밋·인터프리터 호출 방식", stats 3절)의 배치 조건도 정해져 있지 않다.
- 권장 조치(메인 / compute-scheduler-expert, 아래 중 하나)
  - (가) **순차 `0xFFFF`·8**: 5단계와 같은 배치. R3a → R3b → R3c 순서이고 합계 약 2시간 20분 이상이다. 가장 단순하다.
  - (나) 병렬을 유지하되 E 러너 맨 앞에 끔 대조 단계를 하나 더한다. 예: `ed9_census_v0_off`를 E에서 새 `-Root`(예 `r3e_placement_86121e8f`)로 100 run, 약 5분. R3a(P)의 `census_v0_off`와 `compare_identity --expect-switch off`로 대조하면 같은 커밋·같은 스위치에서 배치 차이만 남는다. identical이면 P·E 무관함의 실행 근거가 된다. 이 판독 규칙(다르면 멈추고 P에서 다시 돌린다)을 실행 전에 적어 둔다.
  - 어느 쪽이든 측정 배치(마스크·worker)를 판 9 등록부에 공개 항목으로 적는다.

**[실행 전 수정][E·I] M-2. run_v5는 job 오류를 오류 줄로 남기고 exit 0으로 끝난다. 그 위에 `.done exit_code 0`이 써진다.**
- 근거
  - `run_v5.py:1043-1044`: 모든 예외를 오류 줄로 바꾼다. run 뒤 관문 `d1_median_record`의 RuntimeError(`verdict_runs.py:390-406`, 호출 `:941`)도 같은 길로 간다.
  - `run_v5.py:1291-1293`: 오류 줄이 있어도 exit 0이다.
  - `step_r3.ps1:63-71`: exit 0이면 `.done`을 쓴다.
- 판단과 실패 시나리오
  - 뒤 단계는 실패 쪽으로 닫힌다. `compare_identity.py:135-137`·`:188`이 새 오류 줄을 `not_judgeable`로 보고, `jp3_ed8_judge.py:1471`·`:1485`도 NotJudgeable로 본다.
  - 그러나 스위치 설치 결함이 있으면 1시간 동안 1356줄이 모두 오류 줄이어도 러너는 성공으로 끝난다.
  - `log_errors.py`는 run_v5가 `errors N` 줄을 찍지 않아 아무것도 잡지 못한다.
- 권장 조치(메인)
  - 단계마다 끝난 뒤 `key_presence.py <출력 jsonl> --absent-key error --key controller_tag --key commands_sha256`을 돌린다. 켬 배치는 `--key d1_settings`도 더한다. 종료 0을 확인한다.
  - 긴 실행 전에 상태마다 1 job G-S를 돌린다(scratch 하위 새 `--out`, 켬 1·끔 1, 약 1분). 같은 키 검사로 "스위치 설치 → 태그·`d1_settings` → 관문" 경로가 실제 run에서 도는지 본다. 단위 시험 `test_c_m_worker_presets_tags_and_gates`(`test_ed9_cm_switch.py:167-172`)는 프리셋만 시험하고 run 하나 전체는 돌리지 않는다.

**[실행 전 수정][R] M-3. R4의 `--rule-set ed8_j7a`(기록)를 R3a에 돌리면 run commit이 달라 setting_defect가 확정이다.**
- 근거
  - `jp3_ed8_judge.py:256`: `RuleSet("ed8_j7a", …)`의 `run_commit`이 기본값 `gate.RUN_COMMIT` = C8 56849248이다(`:222`, `jp3_ed8_gate_judge.py:91`).
  - R3a `.done`의 `commit`은 C9다(`step_r3.ps1:65`).
  - `checked_step`(`jp3_ed8_gate_judge.py:179-180`, 호출 `jp3_ed8_judge.py:1534`)이 `SettingDefect`를 낸다.
  - 계획 `impl_report_2.md:194`는 "같은 꼴로 `--rule-set ed8_j7a`(기록)는 R3a에 돈다"고 적었다.
- 권장 조치(python-expert / control-expert)
  - 이 기록 측정이 필요하면 C9 끔 줄을 읽는 규칙 집합(예 `ed8_j7a_c9`, `run_commit=ED9_RUN_COMMIT`, `is_d1_median=False`)을 T9에 더한다. 그러려면 판정 도구 커밋이 바뀐다.
  - 필요 없으면 계획에서 지운다.

**[실행 전 수정][R] M-4. R3c ⑥②(켬 ↔ 끔)에는 허용 집합이 없다. 설계가 바뀌기를 기대하는 9 job 때문에 결과가 늘 `differs`다.**
- 근거
  - `impl_report_2.md:193` ⑥: "② on ↔ off `--expect-switch on`". `--allowed-from`이 없다.
  - `control_cm_switch\report.md:180-181`: C0에서 D1_step FAULT가 난 고유 9 job은 사유가 바뀌고, 나머지 50 job은 비트 동일해야 한다.
  - `compare_identity.py:191-196`: 허용 집합이 없으면 다른 줄이 하나라도 있으면 `differs`다.
- 실패 시나리오
  - 도구 상태로는 "50개 비트 동일" 판정(다르면 멈춤)과 "9개 변화" 기록을 가를 수 없다. 보고서의 `differing` job key 목록을 손으로 9 job과 대조해야 한다.
- 권장 조치(python-expert)
  - control 2.4의 9 job 목록을 job key 파일로 고정한다. 예: `r3c_expected_d1_step.json`(sha를 기록).
  - 그 파일을 `--allowed-from`(또는 새 `--allowed-keys`)으로 넘기고 `--require-allowed-change`와 함께 돌린다.
  - `scan_d1_step.json`에 R3c 그룹이 있는지는 블라인드라 확인하지 않았다(확인 필요 Q-3).

**[실행 전 수정][I] M-5. `r3c_run.py`는 worktree HEAD와 깨끗함을 기록만 하고 단언하지 않는다. ③이 쓰는 `ed9-diag`는 잠기지 않았다.**
- 근거
  - `r3c_run.py:79-87`·`:127`·`:154`: start·end `head`·`is_clean`을 log.json에 남긴다. 기대 커밋 인자도 거부 로직도 없다.
  - `worktree_locks.py` 결과: `ed9-diag`는 unlocked다.
  - step_r3는 R3a·R3b에서 HEAD를 단언한다(`step_r3.ps1:41-45`·`:64`). R3c 단계는 step_r3를 거치지 않는다(`runner_p.ps1:29-31`).
- 권장 조치
  - 메인: 실행 전에 `ed9-diag`에 `git worktree lock`을 건다.
  - python-expert: `r3c_run.py`에 `--expect-head <40자>`를 더한다. 시작·끝 HEAD가 다르거나 tracked 변경이 있으면 종료 2로 한다.
  - 당장 고치지 않는다면, 실행 뒤 log.json의 start·end `head`·`is_clean`과 레코드의 `diag.two_pressure_file` 경로를 대조하는 것을 필수 단계로 적는다.

**[실행 전 수정][R·I] M-6. 판정 근거 시험을 고정 범위로 다시 묶은 뒤, T9·C9 자신의 diff 범위를 지키는 시험이 없다.**
- 근거
  - `git diff 7ea78232 2deb5fd7`에서 `test_ed8_gate_p80_key.py:294-325`와 `test_ed8_run_path.py:47-88`의 HEAD·작업 트리 비교가 고정 커밋 비교로 바뀌었다(T8‴↔T8⁗, C8↔T8⁗).
  - 의미: "T8⁗는 판정 도구만 바꿨다", "C8→T8⁗ 사이 실행 경로가 바뀌지 않았다"는 그대로 참이다.
  - 다만 이제는 과거 커밋끼리만 비교하므로 어떤 HEAD에서 돌려도 늘 참이다. T9 checkout을 지키는 역할은 사라졌다.
  - `test_run_path_closure_is_unchanged_here`(`test_ed8_run_path.py:82-`)만 checkout 기준으로 남았다.
  - ed9에는 대체 시험이 없다. `test_ed9_*.py`에서 `name-only|ls-tree|hash-object`는 0건이다.
  - 이번 감사에서 손으로 확인한 것
    - `git diff --stat 86121e8f 2deb5fd7`: 판정 도구 3개와 시험 2개뿐이다. `ed8_run_path_modules_56849248.json`의 실행 경로 목록에 든 것은 없다.
    - C8→C9 실행 경로 변경은 `c2.py`·`two_pressure.py`·`v5_options.py`·`run_v5.py`·`verdict_runs.py`다.
- 권장 조치(python-expert, 판 9 봉인용 판정 커밋 전)
  - `test_ed9_judge_tool.py`에 두 시험을 더한다.
    - (a) `git diff --name-only ED9_RUN_COMMIT <judge commit>` ⊂ {판정 도구, 05_tests}
    - (b) `git diff --name-only C8 ED9_RUN_COMMIT` 중 실행 경로 목록 파일 = 위 5개(03_src 3 + 04_scripts 2)
  - 메인은 `baseline_check.py blobs --rev 86121e8f --rev 2deb5fd7 <실행 경로 목록>`으로 확인한다.

**[실행 전 수정][T·I] M-7. `ED9_SPEC_SHA256` 자리표시: R4에서는 문자열 그대로 기록되고, 거부하는 관문이 없다.**
- 근거
  - `jp3_ed8_judge.py:249`: `ED9_SPEC_SHA256 = "<ED9_SPEC_SHA256>"`
  - `:1564`·`:1947`: 보고서 `spec_sha256`에 그 문자열을 그대로 쓴다.
  - 규칙 파일 해시와 대조하는 코드는 ed8에도 없다. 상수만 기록한다(`gate.SPEC_V8_SHA256`, seal_check `--const` 일치 확인).
  - stage5 보고서의 `"rule"` 문자열도 ed9에서 여전히 `"jp3_remedy_spec_v8_rules.md 7.3 .. 7.5"`다(`:1562`).
- 판단
  - R4(봉인 전 측정)에서는 자리표시가 "빈 자리로 통과"하지 않는다. 출력에 그대로 남아 설계 판독이라는 표지가 된다. R4에는 허용된다.
  - 다만 봉인 뒤 판정에 이 T9를 그대로 쓰면 자리표시가 남은 채 판정 출력이 나온다.
- 권장 조치(python-expert, 봉인 직후 판정 커밋 T9′)
  - 상수를 봉인 sha로 바꾼다.
  - `spec_sha256`가 64자 16진수가 아니면 `setting_defect`로 끝나게 하고, 시험을 둔다.
  - `rule` 문자열을 판 9 문서로 바꾼다.
  - T9→T9′ diff가 상수·문자열뿐인지 blob으로 확인한다.
  - R4를 T9′에서 한 번 더 돌려 `spec_sha256`·`judge_code` 밖이 같은지 본다. 등록부 ①("같은 경로 건식 실행")의 경로 동일성 근거가 된다.

**[실행 전 수정][I] M-8. 출력 위치: 새 출력 폴더가 모두 이미 SUMS를 쓴 `d1_prerun\` 아래에 생긴다.**
- 근거
  - `baseline_check sums d1_prerun\SHA256SUMS` 결과: entries 33, mismatch 0, missing 0, unlisted 0(지금은 맞다).
  - `-Root …\d1_prerun\r3a_off_86121e8f` 등 출력 폴더 넷(`r3a_off_*`·`r3b_on_*`·`r3c_diag_*`·`r4_2deb5fd7`)이 이 폴더 아래에 생기면 재귀 SUMS는 바로 낡는다.
  - `*.npz`는 `.gitignore:41`에 걸린다. T4h가 생기면 로컬 전용이다.
  - 새 출력의 줄바꿈 보호(`git check-attr text` = unset, 즉 `-text`)는 걸려 있다.
- 권장 조치(메인)
  - 출력 루트를 형제 폴더(예 `ed9_design\r3_runs\`)로 옮긴다. 옮기지 않으면 실행 뒤 SUMS 다시 쓰기를 `write-sums --plan`에 미리 정해 둔다.
  - 출력에 npz와 큰 파일(1e8 B 초과)이 생기면 판 8처럼 LOCAL_ONLY와 `large_outputs.py`로 다룬다.

### 기록

- **R-1 [I]** 두 러너가 같은 NUMBA 캐시 `…\outrigger-ed9-r3\numba_cache\86121e8f`(`step_r3.ps1:19`)를 동시에 쓴다. 판 9는 R3a(P)와 R3b(E)를 병렬로 돌리기 때문이다.
  - 결과 비트에는 영향이 없다고 본다[추정]. numba는 임시 파일을 쓴 뒤 교체한다.
  - 병렬을 유지하면 러너별 폴더로 나누기를 권한다.
  - 별개로, 지금 RAM 여유는 약 14.7 GB다(`status.py`). R3a 7 + R3b 10 + R3c 4 worker가 동시에 돌면 메모리가 빠듯할 수 있다[추정]. MemoryError는 오류 줄이 되어 실패 쪽으로 닫힌다(M-2).
- **R-2 [I]** step_r3의 깨끗함 판정은 `--untracked-files=no`다(`step_r3.ps1:24`). 판정 도구 `code_identity`(`jp3_ed8_gate_judge.py:218`)는 미추적 파일도 센다. 지금 세 worktree는 `status --porcelain --ignored`가 0줄이다.
- **R-3 [R]** 실패 처리표가 없다.
  - `step_r3.ps1:12`: exit 2가 "출력 있음"이다. 그런데 `:63`이 run_v5의 exit 2(인자 오류)를 그대로 돌려준다.
  - 실패한 단계를 다시 돌리는 규칙(새 Step 이름? `_a2`?)이 계획에 없다. B-1과 함께 정한다.
- **R-4 [I]** 값이 담긴 로그: `run_v5.log`(`step_r3.ps1:56`)는 job마다 `final_phase`와 `commands_sha256` 앞 8자를 찍는다(`run_v5.py:1314-1316`).
  - 측정 결과이므로 메인은 열지 않거나, 열면 공개 목록에 적는다.
  - 러너 로그(`logs_p`·`logs_e`)에는 STOP·DONE 줄과 라벨 상태만 남는다(`r3c_run.py:148-152`).
- **R-5 [S]** 실행 입력의 커밋 상태
  - 미추적: `r3c_run.py`·`compare_identity.py`·`r3c_jobs.json`·`make_r3c_jobs.py`가 미추적이다. sha는 SUMS에만 있다(baseline_check `cited_untracked` 34). r3c log.json은 `r3c_run.py`의 sha를 남기지 않는다.
  - 키 파일: `heldout_g_ed8.json`·`confirm_b_grid192.json`은 master에서는 추적되지만 T9 트리에는 없다(`ref_check` `ref_untracked`). run_v5는 절대 경로로 읽고 sha를 대조한다(`run_v5.py:578`).
  - `v5\main.jsonl`은 추적되지 않는다. compare 보고서 `inputs`에 sha가 남는다.
- **R-6 [R]** ITEM_GROUPS의 FAULT 판별은 J4 상세 문자열 `final fault*`에 기댄다(`jp3_ed8_judge.py:266`). impl 확인 필요 4와 같다. 기록 모드라 판정에는 영향이 없다.
- **R-7 [E]** compare_identity의 빈 집합·누락 처리를 확인했다. 결함이 아니다.
  - 0개 대조, 누락·여분·중복·오류 줄은 `not_judgeable`(exit 2)이다(`compare_identity.py:180-190`).
  - 상태 결합 순서가 `differs` ≻ `not_judgeable` ≻ `as_expected` ≻ `identical`이라, 실패가 판정 불가에 가려지지 않는다(`:195-202`).
  - R4는 다음 경우 모두 판정 불가다: 후보 줄 없음(`candidate_not_run`, `jp3_ed8_rules.py:614-619`), 파일 수·job 불일치(`stage5_completeness` `:1647-1665`), 같은 형상 목록이 하네스와 다름(`:1684-1685`), 오류 줄(`:1471`·`:1485`).
  - 사이드카 배치·C-m 불일치는 setting_defect다(`:1625-1644`).
  - `--v0-rows` 순서를 바꾸면 사이드카 배치가 어긋나 setting_defect다.
- **R-8 [R]** 태그 384 조합 시험(`test_ed9_cm_switch.py:31-68`)의 범위
  - 기저 6 {None·P3·P3H·P3W·P3X·ABL} × 접미사 6개 {`_LAS`,`_K1`,`_LSB`,`_TCL`,`_CM`,`_ED8`}의 켬·끔 2⁶ = 384다. 정해진 순서의 모든 조합이다.
  - 각 조합에서 `switch_base_tag`, ③ revision(4·5·6·7·None), 모든 `is_*_tag`를 확인한다. 접미사를 하나씩 더할 때 순서·멱등성도 확인한다.
  - `v5_options.py`의 ③ 기저 상수는 P3·P3H·P3W·P3X 넷으로 모두 포함된다.
  - 순서가 어긋난 태그(예 `_CM_LSB`)는 시험 밖이다. 생산자가 만들지 않는 꼴이다.
  - `_split_tail` 순서는 ED8 → CM → TCL → LSB다(`v5_options.py:912-920`).
  - ③ 판별은 기준 태그 `extend_start_revision_of_tag`(`:1067-1074`)로 한다.

## 규칙↔도구 대조표 (판 9 규칙 미봉인 — 설계 입력 기준)
| 설계 요구(원문 위치) | 도구 위치 | 판단 |
|---|---|---|
| 프리셋 인자 기본 끔, `two_pressure = replace` 한 곳(control 1.3 (1)) | `c2.py` diff: 인자 `:2860`, replace `:2975` | 같음 |
| 켬 배치 집합(1.3 (2)) | `run_v5.py` `D1_MEDIAN_BATCHES` `:478-479`, 끔 쌍둥이 `:483-484` | 같음. `ed9_heldout_same_shape` 포함 |
| worker 설치, 명시 False 거부, 다른 값 재설치 거부(1.3 (3), 1.6) | `run_v5.py:1296-1306`, `verdict_runs.py:352-387` | 같음. 래퍼는 kwargs만 넣는다. 위치 인자로 넘기는 경우는 막지 않는다(현재 호출자 없음, 기록) |
| 설정에서 붙는 태그, `_CM`은 `_ED8` 앞(1.3 (4)) | `v5_options.py:980-994`·`:1077-` | 같음 |
| `d1_settings`는 켬일 때만(1.3 (5)) | `verdict_runs.py:405`, `LINE_RECORD_KEYS` 끝 | 같음 |
| 이어 돌리기 거부(1.3 (6)) | `run_v5.py:1048-1076` | 같음. step_r3는 새 경로만 쓰므로 실행에서는 이 경로를 거치지 않는다 |
| run 뒤 관문, 두 갈래(1.3 (7)) | `verdict_runs.py:941`·`:944`·`:961` | 같음. 실패는 오류 줄이 된다(M-2) |
| `.done`·사이드카에 배치 기록(1.3 (2)) | `.done` `codes.batch`(`step_r3.ps1:67`), 사이드카 `batch`·`d1_median`(`run_v5.py:1288-1293`) | 같음. 판정 도구는 사이드카를 본다(`jp3_ed8_judge.py:1625`) |
| 세는 줄은 R3b 줄만(stats 3 조건 1) | `jp3_ed8_judge.py:1543-1551`: 주어진 경로만 읽고 정체성 결함이면 setting_defect | 같음 |
| 층·기준 통과는 C9 켬 줄로 다시 정한다(조건 2) | `slot_inputs` `:1470-1476`: 조건 줄 = 주어진 줄 | 같음 |
| 새 7 job은 끔도 돌린다(조건 3) | `steps_p.json:5`, `ED9_OFF_TWIN_BATCHES` | 같음(B-1과 무관, JobsFile 있음) |
| 처리 팔 스위치 상태 확인(조건 4) | `treatment_tags`·`d1_switch_problems` `:231-339` | R4 범위 밖(V0만). 코드는 있다 |
| R3b가 예측과 다르면 봉인 전 멈춤(조건 5) | 도구 사이 연결이 없다. compare ② 결과 → R4 | 절차상 연결만 있다. "①②③⑤ exit 0일 때만 R4 값을 등록부에 쓴다"를 실행 계획에 적는다(메인 세션 권고) |
| census 끔 ↔ 저장 대조 identical(impl 7절) | `compare_identity --expect-switch off` | **차단 B-2** |
| R3c 50개 비트 동일 / 9개 변화(control 2.4) | ⑥② 허용 집합 없음 | **M-4** |
| R4 ed8_j7a 기록(impl 9절) | `RuleSet ed8_j7a` run_commit C8 | **M-3** |
| `ED9_SPEC_SHA256` | 자리표시를 그대로 기록 | **M-7** |

## 확인 필요
- Q-1 (control·stats) 배치 선택: M-1 (가) 순차 `0xFFFF`·8, 또는 (나) 병렬 + E 끔 대조 단계. (나)를 고르면 판독 규칙(다르면 멈춤 → P에서 다시)을 실행 전에 고정한다.
- Q-2 (python·control) B-2를 어떻게 고칠지: 저장 줄에 태그 키가 없을 때의 기대 태그, 또는 ④에서 태그 비교 제외.
- Q-3 (python) ⑥②의 허용 집합 출처. `scan_d1_step.json`에 진단 job 그룹이 있는지는 블라인드라 보지 않았다. 없으면 control 2.4 목록을 job key 파일로 고정한다.
- Q-4 (control·stats) R4 `ed8_j7a` 기록을 유지할지(M-3).
- Q-5 (stats) 봉인 뒤 5단계 해시 재생의 배치 조건을 규칙에 넣을지(M-1).

## 위임 필요
- python-expert
  - B-2: `compare_identity.py`에 저장 줄에 태그가 없을 때의 규칙 + 합성 시험
  - M-3: 규칙 집합 추가 또는 계획 삭제
  - M-4: 허용 job key 파일과 인자
  - M-5: `r3c_run.py --expect-head`
  - M-6: ed9 diff 범위 시험 2개
  - M-7: T9′ 자리표시 거부 관문·rule 문자열
  - impl_report_2 9절 명령표 정정(aa2·aa3 `-JobsFile`)
- compute-scheduler-expert
  - B-1: steps_p·steps_e·두 러너 재생성(aa2·aa3에 `-JobsFile`)
  - M-1 (가) 또는 (나) 배치
  - R-1: 러너별 NUMBA 캐시
- control-expert / stats-design-expert: Q-1·Q-4·Q-5
- `tools/verif` 후보(python-expert): 생성된 러너 steps json의 단계마다 생산자 `--list` 건조 실행을 자동으로 돌리는 점검(입력: steps json과 생산자 경로, 출력: 단계별 exit·건수, 종료 1 = 하나라도 0이 아닌 exit). 이번 B-1 같은 결함을 잡는다.

## 메인 세션 권고
1. B-1을 고친 러너에서 단계마다 `--list` 건조 실행을 한다. 기대: 678 / 339 / 339 / 7 / 100. scratch NUMBA 캐시를 쓰고, 끝난 뒤 `ed9-c9` `status --porcelain --ignored`가 0줄인지 본다.
2. 실행 전에 `git worktree lock .claude\worktrees\ed9-diag`를 건다(M-5).
3. 상태마다 1 job G-S(켬·끔)를 돌리고 `key_presence --absent-key error --key controller_tag --key d1_settings`로 확인한다(M-2).
4. 단계마다 끝난 뒤 다음을 본다.
   - `step_check.py <Root>\<Step>.done --expect-commit 86121e8f6f45c24e32ceee680a307355bdfe3ba4`
   - `key_presence … --absent-key error`
   - R3c: log.json의 start·end head와 is_clean
5. 대조 ①②③⑤⑥는 B-2·M-4를 고친 뒤 돌린다. R4 값은 ①②③⑤가 exit 0일 때만 등록부에 쓴다(stats 조건 5).
6. 판정 근거 시험(797·368 묶음)은 `--junitxml`로 다시 돌리고 `junit_skips.py --critical "test_ed9_|test_ed8_run_path|test_ed8_gate_p80_key"`로 skip 0을 확인한다. 33파일 실행에는 skip이 약 38개 있다.
7. ed8 스모크 불변(T9: N 11/310, E 0/24, j7a 3/310)은 블라인드라 확인하지 않았다. 메인이 `judge_smoke_320a1f64`와 `judge_smoke_2deb5fd7`의 ed8·ed8_j7a 출력을 `judge_code`·`inputs`를 뺀 채 비교해 "같음/다름"과 다른 최상위 키 이름만 출력하는 스크립트로 확인하고, 연 범위를 공개 목록에 적는다.

## 검사하지 못한 것
- ed8 스모크 수치 불변: judge_smoke 출력은 블라인드다. sha만 SUMS와 대조했다(mismatch 0).
- 저장 5단계 jsonl(`j9_runs`)의 `controller_tag` 존재: 블라인드다. impl 보고의 ed9 스모크 setting_defect(1356 + 7줄)로 미루어 있다고 본다[추정].
- `scan_d1_step.json`의 그룹 이름과 허용 집합(블라인드).
- 시험 797·368 passed의 재현: pytest를 돌리지 않았다(감사자 규칙).
- P·E 코어의 비트 동일성 실증(M-1).
- `hydraulics_pressure_sampling\report.md`·`stats_aa_j7\report.md`·`control_d1_rule\report.md` 본문은 읽지 않았다(sha만 source_guard로 고정했다). 이번 실행 감사 항목은 control_cm_switch·stats_impl_check 두 문서로 충분하다고 판단했다.
- C-J·C-S의 J7 닫힌 목록 적용(stats 위임 항목)은 호출 위치만 Grep했다(`jp3_ed8_judge.py:1284-1286`). R4 범위 밖이다.

## 실행한 검증
- 의존성 점검: STAMP(이 세션에서 이미 점검함)
- 인터프리터
  - python-dev `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`MKL_THREADING_LAYER=TBB`): verif 도구와 즉석 스크립트
  - dynamics-dev `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B`(`PYTHONDONTWRITEBYTECODE=1`, scratch `NUMBA_CACHE_DIR`): run_v5 `--list` 건조 실행 8회, `ed9-c9`에서
- 명령
  - `worktree_locks.py`: 종료 0. c9·t9 confirmed, diag unlocked
  - git: worktree 4개의 HEAD와 status(0줄), `git log`·`git diff --stat`(C8→C9, C9→T9, C9→diag), `git diff 9ec94e7a 86121e8f`(실행 경로 3파일), `git diff 7ea78232 2deb5fd7`(시험 8파일), `ls-files --error-unmatch`, `check-attr text eol`, `check-ignore -v`, `merge-base`
  - run_v5 `--list`
    - `--jobs-file` 없음: ed8_heldout_aa2·ed9_heldout_aa3 exit 2
    - `--jobs-file` 있음: aa2·aa3 339, ed8·ed9_heldout_v0 678, same_shape·same_shape_off 7
    - census_v0·census_v0_off: 100
    - 실행 뒤 `ed9-c9` `status --porcelain --ignored` 0줄
  - `ps1_lint.py` step_r3·runner_p·runner_e: 종료 0(info 2, Tee|Out-Host는 거짓 양성)
  - `placeholder_scan.py --pattern-set both`(step_r3·두 러너·steps json 2개)
    - 1차: 종료 1. `<Root>`·`<Step>`·`<LogDir>` 6건, 모두 주석 줄(`step_r3.ps1:7`, `runner_*.ps1:95·98`)
    - `--allow LogDir --allow Root --allow Step`: 종료 0
  - `seal_check.py jp3_remedy_spec_v8_rules.md --const jp3_ed8_gate_judge.py:SPEC_V8_SHA256`: 종료 0
  - `baseline_check.py sums d1_prerun\SHA256SUMS`: mismatch 0·missing 0·unlisted 0, `cited_untracked` 34(종료 1, 커밋 전이라 기록)
  - `ref_check.py impl_report_2.md --rev 2deb5fd7 --exclude j9_runs --exclude .claude`: 서술 속 이름에서 `ref_missing` 18, `ref_untracked` 20(기록)
  - `gate_scan.py compare_identity.py r3c_run.py`: 종료 0(job key dict info만)
  - `key_presence.py v5\main.jsonl --where job.setting=V0 --key controller_tag --key commands_sha256 --key final_phase --key d1_settings`: controller_tag·d1_settings 100/100 없음(B-2 근거)
  - 즉석 스크립트 `diag_keys.py`(키 이름·건수만 출력): 저장 진단 jsonl 4개 각각 job key가 `r3c_jobs.json`과 모두 맞았다(7·7·34·20). `controller_tag`는 모두 있고 서로 다른 값은 1개, `d1_settings`는 0이다. `r3c_jobs` 59는 모두 고유다.
  - python `-c`: `r3c_jobs.json`의 설정 분포 V0 59
  - `cpu-scheduler\status.py`: 고정 tenant·예약 없음, RAM 여유 약 14.7 GB
  - 환경 변수(User·Machine)의 스레드 변수: 모두 없음
- 만든 뒤 지운 파일: scratchpad `verif-ed9r3\diag_keys.py`·`guard.json`·`numba\`(폴더째 삭제). 프로젝트·worktree에 남긴 부산물은 없다(`status --ignored` 0줄).
- 최종 판정 직전에 다시 확인한 것: Grep `"id":"r3[ab]_ho_aa[23]".*JobsFile`가 0건이다(B-1 그대로).
- 원본 불변: 확인 — 원본 쓰기 0회, 기존 항목 변경·삭제 0건 (sha impl_report.md 0ee87231…, impl_report_2.md 87e0479e…, SHA256SUMS dc426158…, compare_identity.py d0887016…, r3c_run.py 2637f27a…, make_r3c_jobs.py f52fc5d4…, r3c_jobs.json d542db7c…, step_r3.ps1 3ce05c58…, heldout_g_ed8.json a18b5818…, confirm_b_grid192.json 4e80e69b…, jp3_remedy_spec_v8_rules.md 35f9eba8…, jp3_remedy_spec_v8_rules.md.sha256 e19aaa48…, report.md a5bdeffc…, report.md 09201253…, report.md f0b112d7…, report.md 3ccbf233…, report.md ce692fc9…, decision_log.md 008c8de8…, 폴더 added_only: 새 항목만 생김, ~$ 임시 파일 없음) · 경고: 입력 폴더에 항목 추가 4건(runner_e.ps1, runner_p.ps1, steps_e.json 외 1건); 형제 항목 수정 시각만 변경 1건(ed9_design)
  - 추가 4건은 감사 중에 compute-scheduler 배치안이 만든 러너 파일이다. ed9_design의 수정 시각 변화는 감사 폴더 생성으로 본다[추정].
- 메모리 갱신: `audit_pitfalls.md`에 "Pre-seal measurement runs" 항목을 더하고 `MEMORY.md` 색인을 고쳤다.
- 사용한 스킬: 없음
