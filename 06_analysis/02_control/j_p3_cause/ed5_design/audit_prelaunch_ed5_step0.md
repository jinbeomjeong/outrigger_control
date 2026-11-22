# 판 5 실행 전 감사(step0_cdry 직전, 2026-11-22, verif-protocol-auditor) — hand-back 원문

<!-- timestamp 2026-11-22T05:25:35.006Z -->
## 감사 요약
- 본 결과(판정 값은 열지 않았습니다):
  - `l1ref_a1\L1_VBJ.err` 앞 4줄. 제어기 경고 이름과 그 수치(`WARN_PROBE_STIFFNESS_OUT_OF_RANGE:<값>`)입니다.
  - `key_presence` 출력. L1 기준 두 파일(`L1_VBJ0.json`·`L1_VBJ.json`)에서 `base.t_ready_s`가 없거나 null인 행의 수와 위치가 보였습니다. 도구가 null을 '없음'으로 셉니다.
  - python-expert scratchpad `junit_fix20.xml`의 property. 단위 시험의 합성 수치(P4-6·P4-7 표)입니다.
  - L1 기준 줄은 정오 2 2-1에 따라 판정 줄이 아닙니다. 위 값은 리포트에 옮기지 않았습니다.
- 대상: 판 5 판정 단계 첫 단계 `step0_cdry`의 실행 전 감사
  - 실행 커밋 dba05b3f(worktree `ed5-run`, 잠김), master 0a80914d
- 기준 문서
  - 원판 `jp3_remedy_spec_v5.md` fe6f5844
  - 정오 1 4721352e, 정오 2 639c54e9, 정오 3 7bab9217
  - 경로 2 발췌 3ce9ecd8 / e1 b87d665c
  - 고정 목록 `FIXED_INPUTS_dba05b3f.SHA256SUMS` b1b01251
- 판정: **차단 2 / 실행 전 수정 4 / 기록 9 — step0_cdry를 시작할 수 없습니다.** B-1 때문에 이대로 돌리면 네 실행이 모두 시작 직후 끝납니다(종료 2 → 단계 종료 3). 고치려면 코드를 바꿔야 해서 실행 커밋도 새로 정해야 합니다.

## 발견 사항 (심각도순)

### [차단][R·E] B-1. c 건식의 고장 계획과 키 파일이 맞지 않아 러너 가드가 모든 실행을 거부합니다
- 근거(모두 dba05b3f 코드)
  - `step0_cdry.ps1:11` `$Plan = "$X11Folder\c90_91_plan.json"`을 네 실행(VBK0·VBK × c90·c91)에 똑같이 줍니다. 실행마다 키 파일은 시드 하나만 담은 `${Run}_keys.txt`입니다(20~23행).
  - 러너: `r79_L3L4_final.py:238-246`은 키 파일 목록으로 `screen.apply_rod_fault_guard(keys)`를 부릅니다.
  - `r79_sensor_screen.py:1099-1114` → `rod_fault_plan.py:166-176` `key_problems`는 계획 키와 작업 키가 **정확히 같기**를 요구합니다("plan keys that are no job of the run"). 다르면 `r79_sensor_screen.py:1125-1129`에서 작업 시작 전에 `SystemExit(2)`입니다.
  - 기존 시험도 같은 동작을 확인합니다: `test_x10_rod_fault.py:446`(계획에 작업 밖 키가 있으면 거부).
  - 직접 대조(값 비출력): `c90_91_plan.json`은 160키, `c90_keys.txt`·`c91_keys.txt`는 각 80키입니다. 계획에만 있는 키가 80개라 **거부**됩니다.
    - b1~b4(167/167)와 T-CK·DROPOUT 8쌍(2/2)은 모두 일치합니다.
  - 원인: `jp3_12b_plan.py:305-308`은 c 건식 계획을 하나로, 키 파일을 시드별로 씁니다. `jp3_12b_judge.py:955-986`(dry-c)은 c90=·c91= 실행 파일을 따로 요구하고, 줄마다 `plan_sha256`이 합본 계획 sha여야 합니다(999-1004행).
    - 그래서 단계 스크립트만 고쳐서는 맞출 수 없습니다. 시드별 계획을 만들면 sha가 달라져 setting_defect가 되고, 한 파일로 160키를 돌리면 dry-c가 키 불일치(`load_lines` "other")로 판정 불가를 냅니다.
- 실패 시나리오
  - 네 실행이 모두 종료 2로 끝나고, `Wait-Runs`가 `Stop-Step 3`을 냅니다(`common.ps1:274-278`).
  - 출력은 없지만 `cdry_a1` 폴더가 생깁니다. 그러면 `step_l1ref.ps1:13-18`이 `cdry_a*` 폴더가 있다는 이유로 L1 기준 재생성을 거부합니다.
  - 정오 2 2-6("12b·c 건식 출력이 하나라도 생긴 뒤에는 1~4b를 다시 돌리지 않는다")을 이 폴더에 적용하는지도 해석이 갈립니다.
- 권장 조치
  - 지금은 step0을 시작하지 않습니다.
  - python-expert(설계 선택은 control·메인)에게 다음 중 하나를 맡깁니다.
    - (a) X-11이 c90·c91 계획을 따로 쓰고, dry-c가 실행별 계획 sha를 대조하게 한다.
    - (b) 팔마다 160키 한 실행으로 돌리고, dry-c가 팔당 파일 하나를 받게 한다.
    - 가드를 '계획 ⊇ 작업'으로 푸는 안은 X-10 정체성 가드를 약하게 하므로 권하지 않습니다.
  - 어느 안이든 실행 커밋이 바뀝니다. 2-6 순서 1~7(dry, l1keys, step_l1ref, x11 — 기존 `ed5_inputs\x11`이 있으면 거부 —, ckdrop, v0sample, list)을 새 커밋에서 다시 해야 합니다. 12b·c 건식 출력이 아직 없으므로 2-6이 허용합니다.
  - 시뮬레이션 없는 끝까지 도는 시험을 더합니다: 단계 스크립트마다 (계획, 키 파일) 쌍에 `load_plan` + `key_problems`를 적용한다.

### [차단][T·R] B-2. P5-2 고정 값이 계산·기록되지 않았고, 단계 (4)에 대조 경로도 없습니다
- 근거
  - 규칙
    - 원판 192행 "구현 뒤, 실행 전에 같은 코드 경로로 계산해 봉인 기록에 고정한다"
    - 원판 197행 P5-2 멈춤 "고정 수와 차 > 0"
    - 원판 467행 8절 1: "… P5-2·P5-4 고정 값 계산·기록" 뒤에 "2. c 건식 확인"
    - 정오 1 1A(53-64행), 2절 72행
  - 찾은 결과
    - `06_analysis` 전체에서 `jp3_p5_fixed_values.py` 출력 표지("P5-2 (fixed after implementation", "dominated_reduction")가 0건입니다. FIXED 목록에도 없습니다.
    - `jp3_r58_witness_carries`를 쓰는 코드는 `jp3_p5_fixed_values.py`와 `jp3_12b_judge.py`뿐입니다.
    - `step4a_cases.ps1:28-38`은 baseline_compare·x11·P5-1만 부르고, 사례별 rev 6 수를 고정값과 대조하지 않습니다.
  - 도구와 규칙도 어긋납니다: `jp3_p5_fixed_values.py:114-115`의 `judged_key_total`은 X11을 뺀 모든 줄을 더합니다. 정오 1 64행은 "P4 켬 rev 6 줄만 더한다"고 정했습니다(11절 위임 "P5-2 집계를 1A절 대상으로 나눔"이 반영되지 않았습니다).
  - P5-4(기록)도 만들어지지 않았습니다.
- 실패 시나리오: 단계 (4)에서 P5-2 멈춤 조건 "고정 수와 차 > 0"을 판정할 수 없습니다. 결과를 본 뒤 고정하면 사전 예측이 아니게 됩니다.
- 권장 조치
  - python-expert에게 맡길 것
    - 1A 대상만 더하도록 집계 수정
    - 고정 기록 생성(실행 커밋, 명령, sha를 FIXED에 넣음)
    - step4a(와 4b의 F 갈래)에 대조 단계 추가
  - B-1과 같은 새 커밋에 넣고, 원판 8절 순서대로 c 건식 전에 고정합니다.

### [실행 전 수정][E] W-1. 단계 (6)에서 VBJ J-P3 H-7로 멈춘 시도를 다시 돌릴 수 있습니다
- 근거
  - `common_ed5.ps1:67`이 `tool:t12_VBJ`를 `$RecordCodeTools`에 넣습니다.
  - H-7은 `record_gates_ed5.ps1:47-51`이 내고, `common_ed5.ps1:171-173`의 `Stop-Step 1`로 멈춥니다. 이때 codes에는 `record_gate:t12_VBJ.json`=사유 문자열만 남습니다.
  - `common.ps1:203-206` `Read-PreviousStops`는 `tool:*`=1이면서 기록 목록 밖인 것만 거부합니다. `.stop`의 `exit_code`는 읽지 않습니다.
- 실패 시나리오: 판정 실패(H-7)를 본 뒤 `dg3_a2`를 다시 돌릴 수 있습니다. 4a-5 5.4와 정오 2 2-10의 취지(본 뒤 선택적 재실행 금지)에 어긋납니다.
- 권장 조치(python-expert): H-7로 멈출 때 판정 실패 표지(예: `judged:t12_VBJ_jp3`=1)를 남기고 `Read-PreviousStops`가 그것을 읽게 합니다. 또는 `.stop`의 `exit_code`=1을 거부합니다. 시험도 더합니다. 단계 (6) 전에 고칩니다.

### [실행 전 수정][S·T] W-2. P5-3 junit이 프로젝트에 남아 있지 않고, 어느 커밋에서 돌렸는지 기록이 없습니다
- 근거
  - 원판 198·440행: "junit을 남기고 `junit_skips.py --critical`로 확인"
  - 저장소에는 ed5 junit이 없습니다(Glob 0).
  - python-expert scratchpad `python-ed5impl\junit_fix20.xml`
    - 시작 12:52:09, 779 통과. `junit_skips --critical … --fail-on-skip` 종료 0, skip 0, xfail 0
    - `test_x10_rod_fault` 78건 포함, skip 0
  - 그때 HEAD는 fcf57a41입니다. fcf57a41 → dba05b3f 차이는 주석뿐입니다(`git diff fcf57a41 c9083c65`).
  - scratchpad는 지워질 수 있습니다.
- 권장 조치(메인 세션 권고): 새 실행 커밋에서 7.2 시험을 `X10_BASE_ROOT`와 `--junitxml`로 다시 돌립니다. junit을 저장소(ed5_design 등)에 커밋하고 `junit_skips.py --critical … --fail-on-skip`이 종료 0인지 봅니다.

### [실행 전 수정][E] W-3. "ĉ ≥ 0.5면 멈춤"에 코드 관문이 없습니다
- 근거
  - `jp3_12b_judge.py:1028-1031`: dry-c는 c 값과 관계없이 `written`(종료 0)을 냅니다. 49-53행 docstring은 판단을 메인에 둡니다.
  - `step1_p1.ps1:13`의 Requires가 `@()`이고, 어느 단계도 `cdry`를 요구하지 않습니다.
- 권장 조치: step1이 `cdry.done`을 요구하고 dry_c.json의 `c`가 0.5 미만인지 대조하게 합니다(python-expert). 아니면 메인의 판단을 실행 기록에 남깁니다.

### [실행 전 수정][I·S] W-4. 로컬 전용 `L1_VBJ.json`이 추적되지 않고 제외 규칙도 없습니다
- 근거
  - `git status`가 `?? …/l1ref_a1/L1_VBJ.json`을 보이고, `git check-ignore`는 종료 1입니다.
  - 2026-11-21 정책 항목은 `.git/info/exclude:76-80`에 있습니다(dg3_VBH/VBJ, d3c6c57e l1_VBJ).
  - 보호 구조 자체는 건전합니다.
    - 단계마다 107줄을 모두 다시 해시합니다(`common_ed5.ps1:75-92`).
    - grade-judge가 목록 sha를 대조합니다(`jp3_12b_judge.py:873`).
    - `Assert-NoL1Inputs`가 목록 sha를 씁니다(`common_ed5.ps1:228`).
    - 다만 사본이 없습니다. 2-1 때문에 12b·c 건식 뒤에는 다시 만들 수 없습니다.
- 권장 조치(메인): exclude 한 줄을 더하고, 저장소 밖에 sha를 붙인 백업을 둡니다. B-1로 커밋이 바뀌면 새 L1 파일에도 같게 합니다.

### [기록]
1. [I] 실행 정체성
   - `$RunCommit`·worktree HEAD가 dba05b3f이고 추적 트리가 깨끗합니다(`status --porcelain --untracked-files=no` 빈 출력).
   - L1 identity의 start·end 네 블록 모두 head dba05b3f, is_clean True입니다(`baseline_check identity` 종료 0).
   - 줄 수준 meta `git_head` dba05b3f, 키 파일 sha 일치, 167/167, 설정 VBJ0/VBJ, `plant_truth`, VBJ 태그 `final_C4G2_P3W_LAS_K1`·`run_extend_start_revision` 6.
2. [I] 러너 env `PYTHONUNBUFFERED`·`PYTHONIOENCODING`(`run_l1ref.ps1:8-9`)
   - 모든 Python이 `-I -B`로 뜨므로 무시됩니다(`common.ps1:38`, 250-256).
   - multiprocessing 워커도 `-I` 플래그를 이어받습니다. 결과에 영향이 없고 identity에도 기록되지 않습니다.
3. [I] numba 캐시
   - ed5-run의 ignored `__pycache__` 3곳에 l1ref 시작(13:09)에 만들어진 numba 캐시가 있고, 뒤 실행이 이를 읽습니다.
   - 같은 PC라 영향은 없을 것으로 봅니다 [추정].
4. [R] 판 4.6 정체성의 비대칭
   - T-JR-12a는 rev 5·6을 모두 받습니다(`jp3_baseline_compare.py:85` `HOLD_REVISIONS=(5,6)`, `jp3_tjr_judge.py:678`).
   - 12b는 6만 받습니다(`jp3_12b_judge.py:590-604`). 섞이면 `defect_mixed_hold_revisions`(`extend_start_bound.py:2240-2244`)입니다.
5. [E] A/A `aa_floor_stop` 뒤 "사용자 답 전 재실행 금지"(6.3.8)는 코드로 막지 않습니다(종료 2는 재시도 허용). 운용 규칙으로 둡니다.
6. [S] 도구 결과 가운데 오탐과 설계상 결과
   - `seal_check --sums` 107건 `sums_entry_missing`은 목록 기준 폴더 차이에서 온 오탐입니다.
   - `timeline` `rule_after_results` 8건도 오탐입니다. `git log --follow`의 복사 감지(C093)가 옛 identity를 끌어왔습니다. 실제 첫 커밋은 60494022 14:01:03, 필드 시각은 13:09:25입니다.
   - `baseline_check sums`의 cited_untracked·ignored 8건은 설계상 결과입니다: 저장 입력 5개, 로컬 전용 dg3 2개, L1_VBJ.
7. [I] 꺾쇠 자리표시
   - `placeholder_scan --pattern-set both`가 63건을 냈지만 모두 ps1 주석이나 문서용 명령 문자열입니다(`<run commit 8>`, `selection.json`·`dry_selection.json`의 `<out>`·`<plans>`·`<root>`·`<sel.json>`).
   - 중괄호 0건, `ps1_lint` 0건이고, `Assert-Ed5Configured`가 `<ED5_`를 막습니다(`common_ed5.ps1:34-45`).
8. [R] `ref_check`의 missing·untracked는 모두 아직 없는 출력, 맨 이름, sha로 고정한 추적 밖 입력입니다. `run_harness.out.log`는 전체 경로에 있습니다.
9. [R] 두 경로
   - `handoff_leak`이 9줄을 잡았지만 모두 규칙 어휘(sha256, LEVEL, events, fault)입니다. 경로 1 파일·줄기·함수 이름은 0건입니다(사전 884개는 run commit 코드 ast에서 뽑음).
   - 두 발췌에 공통 블록 표지가 없어 블록 sha 대조는 해당 없습니다.
   - 발췌 sha는 `.sha256` 원시값과 같고, e1이 원판 발췌 3ce9ecd8을 인용합니다.

## 요청 항목 점검 결과
| # | 항목 | 결과 |
|---|---|---|
| 1 | `log_errors l1ref_a1\logs` | 종료 0(로그 3, errors 0). `.err`에 Traceback 0 |
| 2 | `placeholder_scan` | brace 종료 0. both 63건은 모두 주석·문서(기록 7). `--allow`는 쓰지 않음 |
| 3 | `ps1_lint`(run_steps_ed5 17개 + common·record_helper) | 19파일, AST, 종료 0 |
| 4 | `key_presence` | **건식 출력이 아직 없습니다**(cdry·단계 (2) 미실행). 대신 L1 출력을 봤습니다: `L1_VBJ_t4h` 167 npz 모두 rev 6 배열 5개 + `motor_stroke_m`·`command_m_s`·`phase`·`meta_json`(종료 0), `L1_VBJ0_t4h` 4배열(종료 0). `rod_fault.*`·`rod_fault_applied`는 계획이 있는 실행에만 생기므로 cdry 전에 볼 수 없습니다. dry-c가 같은 존재 관문을 안에서 걸어 결측이면 종료 2입니다(`jp3_12b_judge.py:288-316`, 1000-1012) |
| 5 | `seal_check --sums --rev --check-tracked` | 봉인 6판 raw 일치, 모두 -text·LF·추적, 인용 13개 추적. `--sums` 부분은 오탐(종료 1) |
| 5 | `baseline_check sums --base repo-root` | 107항목, 불일치 0, 결측 0, CRLF 0. 설계상 8건으로 종료 1 |
| 5 | `baseline_check identity` | 종료 0 |
| 5 | `ref_check` | 원판 1, 정오 1 1, 정오 2 1, 정오 3 0(종료 코드). 모두 차단 아님 |
| 6 | `junit_skips --critical --fail-on-skip` | 저장소 junit 없음 → W-2. scratchpad junit 2개 종료 0, X-10 78건 skip 0 |
| 7 | `handoff_leak` | 기록 9 |
| – | FIXED_INPUTS | 107줄 = `fixed_inputs_entries.txt` 전개(독립 재전개 107/107, 차집합 0). 정오 2 .md(69행)·.sha256(5행), 정오 3 .md(6행)·.sha256(7행) 포함. LF, BOM 없음 |
| – | 정오 3 순서가 단계 스크립트에 들어갔는지 | 들어 있습니다. `step6_dg3.ps1:83-92`(VBH 기록 관문, VBJ `-VbjJp3`), `common_ed5.ps1:166-174`, `record_gates_ed5.ps1:43-71`(H-7 → 1, J-P3 없음·0행 → 2, 결함·판정 불가 → 2, 목록 밖 실패 → 2, 나머지 진행). 3-1 (1)~(3)과 같습니다. P-1은 `step1_p1.ps1:26-32`(ContinueCodes 0,1)·54-57 → `Get-P1CompareStop`(`record_gates_ed5.ps1:73-81`) |
| – | 지난 감사 실행 전 항목 ① R-2 → P-1 종료 2 | 코드: `jp3_tjr_judge.py:1765` `report["record_failures"] = []`(dba05b3f). 시험: `test_jp3_ed5_erratum1.py:622-633`(두 경로 모두 "2\|"), 636-649 |
| – | 지난 감사 실행 전 항목 ② 13.9 실패 + 목록 밖 실패 → 2 | `test_jp3_ed5_erratum1.py:603-610`. 두 시험 모두 junit_fix20에 통과로 있습니다(pwsh가 없으면 skip이 아니라 assert 실패) |
| – | CWD 경로 결함 | `gate_scan`의 `row_value_path_no_base` 2건. `jp3_fixed_inputs_list.py:147`은 `_relative`가 repo 밖이면 NotUsable, `jp3_rerun_match.py:280`은 is_file이 거짓이면 Missing(종료 2). 둘 다 닫힌 쪽으로 실패합니다. 12b는 폴더 + 이름으로 잇습니다(`jp3_12b_judge.py:278-279`). dry-c 끝까지 도는 시험은 있습니다(`test_jp3_12b_tools.py:1036-1043`, `cwd_elsewhere`). 다만 합성 world라 실제 러너 가드와 (계획, 키) 조합은 거치지 않았고, B-1은 이 공백에서 나왔습니다 |

## 규칙↔도구 대조표(이번 판에서 본 것)
| 규칙 | 도구 | 판단 |
|---|---|---|
| 6.3.10 seed 90·91, 160짝, 셀 표(정오 1 8A: 90 = rank 0~79, 91 = rank 80~159) | selection.json dry, c90/c91 키 80/80, 계획 앵커 τ_C 80·τ_R 80, `delay_reads` 0 | 맞음 |
| 6.3.10 실행 가능 | `step0_cdry.ps1:11-23` ↔ `rod_fault_plan.py:166-176` | **안 맞음(B-1)** |
| 6.3.10 c = 명령이 바뀐 기회 짝 비율, 판정 행 0 = 판정 불가 | `jp3_12b_judge.py:1013-1029` | 맞음 |
| 6.3.10 ĉ ≥ 0.5 멈춤 | 코드 없음 | W-3 |
| 6.6 존재 관문 | `jp3_12b_judge.py:133-139`, 288-316 | 맞음 |
| 정오 1 0.2 b1~b4 = 40~43, 반복 0, `05_tests` 스캔 | selection.json blocks, seed_repeats 0, scan_extra = ed5-run `05_tests` | 맞음 |
| 2-6 순서 | 커밋·로그 시각: dry 13:06 → l1keys 13:06 → l1ref 13:09~13:47 → x11 13:58 → ckdrop·v0sample 13:59 → 60494022 14:01:03 → list → 0a80914d 14:01:34 | 맞음 |
| 5절 P5-2 고정 | 기록·대조 경로 없음 | B-2 |
| 2-10 상태 순서 | `jp3_12b_judge.py:164-174`, `jp3_baseline_compare.py:152-159`, `jp3_j9main_judge.py:421-427` | 실패 우선, 맞음 |

## 확인 필요
- 원판 8절은 "2. c 건식 → 3. 실행 전 감사 → 사용자 승인 → 4. 단계"입니다. 이번 감사는 c 건식 앞에 있습니다. c 건식 뒤 단계 (1) 전에 감사와 승인을 한 번 더 할지 정해야 합니다(정오 2 2-6은 감사 위치를 적지 않았습니다).
- B-1을 고치는 경로(a·b)와 새 실행 커밋으로 prelaunch 1~7을 다시 하는 것(기존 `ed5_inputs\x11`·`ckdrop`·dry 출력의 처리, 새 폴더 이름)은 사용자·control의 결정입니다.
- B-2: P5-2 고정은 "같은 코드 경로로 계산"이라 사례 재생 A~F를 실행 전에 한 번 돌리는 일이 됩니다. 이 순서(8절 1, c 건식 전)를 그대로 따를지 확인이 필요합니다.

## 위임 필요
- python-expert
  - B-1: X-11 계획 구조 또는 dry-c 수정과 시험, (계획, 키 파일) 가드 대조 시험
  - B-2: `jp3_p5_fixed_values.py:114-115`를 1A 대상만 더하도록 고치기, P5-2 고정 기록 생성, step4a·4b 대조 단계
  - W-1: H-7 재시도 거부와 시험
  - W-3: step1의 cdry·c 관문
- control-expert: B-1 안 선택에 따른 6.3.10 문장(실행 단위) 영향, B-2 고정 기록의 형식
- python-expert: `tools/verif` 후보
  - `timeline.py`: 첫 커밋을 `--follow` 없이 판별(복사 감지 오탐)
  - `seal_check.py --sums`: `--base repo-root`
  - `key_presence.py`: null을 결측으로 셀 때 그 수가 결과를 드러낸다는 경고나 옵션

## 메인 세션 권고
- 고친 뒤 새 실행 커밋에서 7.2 시험을 돌립니다: `X10_BASE_ROOT=C:\workspace\outrigger_control\.claude\worktrees\x10base`와 `--junitxml`(저장소에 남김). 그다음 `junit_skips.py <junit> --critical "test_x10_rod_fault|test_jp3_rev6|test_jp3_12b_tools|test_jp3_ed5_erratum|test_jp3_j9main|test_jp3_ckdrop|test_jp3_p5_fixed_values|test_jp3_p51_compare" --fail-on-skip`가 종료 0인지 봅니다. worktree 저장 자료 시험이면 `tools/verif/worktree_tests.py`를 씁니다.
- 새 prelaunch 뒤, step0 전에 재감사를 받습니다(좁게: B-1·B-2·W-1~W-3).
- 그 뒤 단계 (2) 건식이 끝나면 `key_presence --npz-dir <dry_a1의 r79 VBJ·VBH *_t4h> --array jp3_t_s,jp3_r58_witness,jp3_r59_substeps,jp3_r510_candidates,jp3_r59_end_guard_substeps,meta_json`이 종료 0인지 봅니다(정오 1 9.2 (다)).

## 검사하지 못한 것
- 7.2 시험의 dba05b3f 재실행. 하네스를 돌리는 시험이 있어 이 에이전트 규칙상 돌리지 않았고, scratchpad junit으로 갈음했습니다.
- 단계 (1)~(8) 스크립트의 끝까지 도는 동작. step0·6·6b·6c·7b·1·2·4a·4b는 읽었고, 3·5·7·8은 Requires와 머리 주석만 봤습니다.
- `jp3_j9main_judge.py`·`jp3_case_judge.py` 판정 논리 전수(gate_scan 후보 가운데 단계 (4)~(8)용은 코드 확정을 하지 않았습니다).
- P5-1 비교 도구의 세부.

## 실행한 검증
- 인터프리터: python-dev `-I -B`(+ `-X utf8`, `MKL_THREADING_LAYER=TBB`). 프로젝트 모듈은 import하지 않았습니다.
- 도구
  - `depcheck`(STAMP)
  - `source_guard snapshot/verify --strict-additions`(입력 72)
  - `log_errors`
  - `placeholder_scan`(both, brace)
  - `ps1_lint`(19)
  - `seal_check --repo … --sums … --rev 0a80914d --check-tracked`
  - `baseline_check sums --base repo-root` / `identity`
  - `ref_check` ×4
  - `key_presence`(L1 줄 키, `--npz-dir` ×2)
  - `junit_skips --critical --fail-on-skip`
  - `handoff_leak --blocks`
  - `gate_scan`(jp3_* 25파일)
  - `timeline`
- 즉석 스크립트(모두 값 비출력, scratchpad에서 지움): X-11 선정 요약, FIXED 전개 대조, L1 정체성, (계획, 키) 가드 대조, junit 파일 범위, 경로 1 이름 사전 생성
- git: 조회만(log, diff, status, ls-files, check-ignore, check-attr, worktree list)
- 만든 뒤 지운 것: `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\bd7ff3b9-880c-4e9e-afd1-7024158f16f4\scratchpad\verif-protocol-auditor-ed5pre\` 전체. 남긴 부산물은 없습니다.
- 메모리 갱신: `audit_pitfalls.md`(3항목), `MEMORY.md` 색인
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v5.md fe6f5844…, jp3_remedy_spec_v5.md.sha256 0dd1676c…, jp3_remedy_spec_v5_erratum1.md 4721352e…, jp3_remedy_spec_v5_erratum1.md.sha256 d508c2df…, jp3_remedy_spec_v5_erratum2.md 639c54e9…, jp3_remedy_spec_v5_erratum2.md.sha256 054bfb8d…, jp3_remedy_spec_v5_erratum3.md 7bab9217…, jp3_remedy_spec_v5_erratum3.md.sha256 29f02a7f…, common_ed5.ps1 bca56c3e…, fixed_inputs_entries.txt 1cd96da9…, prelaunch_ed5.ps1 8133318d…, record_gates_ed5.ps1 bf7e7bc5…, step_l1ref.ps1 935d019e…, step0_cdry.ps1 38add1e5…, step1_p1.ps1 9152a599…, step2_dry.ps1 53a49b6d…, step3_fpath.ps1 b30111dc…, step4a_cases.ps1 dfe44ac3…, step4b_casef.ps1 639a7884…, step5_t8.ps1 c13a193d…, step6_dg3.ps1 31e0634e…, step6b_vbk0.ps1 52c22177…, step6c_vbk.ps1 43d6907e…, step7_records.ps1 fab0465a…, step7b_ckdrop.ps1 460d9670…, step8_j9main.ps1 2f8e97a4…, common.ps1 308041cf…, record_helper.ps1 c1de0464…, FIXED_INPUTS_dba05b3f.SHA256SUMS b1b01251…, jp3_rev6_p2_handoff_ed5_e1.md b87d665c…, jp3_rev6_p2_handoff_ed5_e1.md.sha256 566d3984…, jp3_rev6_p2_handoff_ed5.md 3ce9ecd8…, jp3_rev6_p2_handoff_ed5.md.sha256 46746226…, dry_selection_r79_key_g8.txt b7c7470a…, dry_selection_r79_key_ref.txt 95ce6f27…, dry_selection.json 533e1cb6…, j9main_v0_sample_keys.command.txt aa736ae0…, j9main_v0_sample_keys.json 7da16a4f…, l1_keys_12b.txt 9f815533…, ckdrop_selection.json 7d411988…, dropout_FL_plan.json b9645722…, dropout_FR_plan.json 630f49c7…, dropout_keys.txt ac8cc9c9…, dropout_RL_plan.json b05ce5f4…, dropout_RR_plan.json 1e158a8a…, tck_FL_plan.json e427bc00…, tck_FR_plan.json 752a6e3b…, tck_keys.txt e2a0e79c…, tck_RL_plan.json fb760588…, tck_RR_plan.json 7f39d569…, b1_keys.txt 6383abf3…, b1_plan.json 65bde6ac…, b2_keys.txt 70425890…, b2_plan.json f85f81b5…, b3_keys.txt 4325b640…, b3_plan.json d7818cb5…, b4_keys.txt 03363fdc…, b4_plan.json a97061b1…, c90_91_plan.json 9330cb97…, c90_keys.txt 19caacb7…, c91_keys.txt 5f768a32…, selection.json ab8b47c3…, l1ref_a1_LOCAL_ONLY.SHA256SUMS 7558abba…, l1ref.done 0c958287…, L1_VBJ.identity.json 6c59b9ab…, L1_VBJ.json 47e57ecd…, L1_VBJ.json.partial.jsonl ba899183…, L1_VBJ0.identity.json 11a20602…, L1_VBJ0.json 70083e3c…, L1_VBJ0.json.partial.jsonl 3dcb759a…, step_record.json 0c958287…, l1ref_a1.md e6109199…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 최종 판정 직전 다시 확인: worktree HEAD dba05b3f·깨끗함, master 0a80914d, 입력 72개 불변(위 source_guard verify)
- 사용한 스킬: 없음
