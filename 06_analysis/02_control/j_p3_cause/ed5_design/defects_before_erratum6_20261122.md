# python-expert: 판 5 정오 6 전 결함 점검 (2026-11-22, 실행 커밋 ae9d0b2d)

(hand-back 원문 그대로)

## 436.9 ed5 정오 6 전 결함 점검 (실행 커밋 ae9d0b2d, 점검만 함)

**요약: 정오 6에서 다룰 항목은 아래 D-1~D-6입니다.**

| 번호 | 심각도 | 내용 | 상태 |
|---|---|---|---|
| D-1 | High | 이번 멈춤의 원인 | 확인됨 |
| D-2 | High | rev 6 줄에 P4-2를 적용할 때의 정의 충돌 | 추정, 명세 판단 필요 |
| D-3 | High | 새 실행 커밋의 x11 준비가 반드시 멈추는 문제 | 확인됨, 이번 결함과 같은 꼴 |
| D-4 | Med | 새 커밋의 dry 선정이 멈추는 문제 | 확인됨 |
| D-5 | Med | `test_d1a` 시험 환경 실패 | 확인됨 |
| D-6 | Med | 이 결함을 놓친 시험 공백 | 확인됨 |

- 그 밖에 "설정 이름 변경이 짝짓기에 반영 안 됨" 꼴은 더 찾지 못했습니다.
- 판정 값, 비교 수치, 행별 결과, judge 파일은 보지 않았습니다. 본 것은 키·열 이름의 존재, 설정·태그·revision 표지, 행 수뿐입니다.
- 짝짓기를 건너뛰는 건식 실행은 하지 않았습니다. 파일은 바꾸지 않았습니다.

### 1. `cases_a1` 출력의 P4 입력 존재 확인 (값 없이)
- **확인한 것**
  - `jp3_baseline_compare.py`가 짝짓기 뒤 읽는 행 키: `commands_sha256`, `t4h_file`, `hydraulic_options.rod_reading_truth`
  - `hydraulics_record` 키: `rod_reading_truth_calls`, `two_pressure_reads`, `relock_step_over_1bar_count`, `p1_retract_seed_*` 네 개
  - `extend_bound_check` 키: `rule_revision`, `spec_edition`, `carry_end_rule`, `retract_start_rule`, `class_reads`(6분류), `jp3_judged_row`, `jp3a/b/c_*`(길이 4), `retract_tracker_dominated_reads`(길이 4), `retract_tracker_stretch_log`
  - 씨앗 기록 열 `net_force_seed_step_N`, `m2_shift_clipped`
  - T4h 8열(`NEW_TRACE_COLUMNS`), `meta_json.head_only_declared`
- **rev 6 줄 15개**(B: VBH·LSH1~4, E: VBJ·LSJ1~4, D: VBG6)
  - 위 키와 열이 **모두 있습니다**.
  - 정체성(rev 6 봉인값과 같은지, 참·거짓만 봄)은 15줄 모두 일치합니다. `jp3_judged_row`는 bool입니다.
  - `jp3_class_names`는 기준선 T4h와 같습니다. 기준선 T4h에는 `jp3_source_names` 열이 없으며, 도구도 요구하지 않습니다.
- **rev 4 줄**(A: VB·LS1~4, C: VBG4): `extend_bound_check` 키와 jp3 추적 열이 없습니다. 기준선 쪽 T4h에도 `jp3_t_s`가 없으므로 도구가 "not_applicable"로 처리하는 4a와 같은 경로입니다.
- **결론**: 구조적으로 막힌 곳은 D-1(VBG5 짝) 하나입니다. 다만 짝짓기 예외로 **P4 검사가 판 5 출력에 한 번도 닿지 않았으므로**, 도구를 고친 뒤 처음 도는 검사들에 D-2 위험이 있습니다.

### 2. 남은 단계 정적 점검 (설정 이름·revision·태그 반영 여부)

| 단계·도구 | 결과 | 근거 |
|---|---|---|
| P5-1 `jp3_p51_compare.py` (모든 단계 대 78fd5d2d) | 문제 없음 | 짝 규칙(`job`에서 `mask`·`t4h_dir` 제외, VBG6→VBG5)으로 값 없이 짝을 맞춰 봤습니다. cases 15/15, cd 2/2, x11 1/1, casef 15/15(같은 묶음인 p5fixed 출력으로 확인), fpath 3/3, 한쪽에만 있는 행 0. job 필드 이름이 4a와 같습니다. t8은 `run_v5` 묶음 설정 이름이 78fd5d2d 뒤 바뀌지 않았습니다(diff 확인) |
| (4b) casef `jp3_case_judge.py case-f` | 문제 없음 | 이번 커밋 F 행의 설정 15개와 job이 `CASE_F_GROUPS`·`CASE_F_JOB`(jp3_case_judge.py:88-92)과 같습니다 |
| (5) t8 `jp3_tjr_judge.py t8` | 문제 없음 | rev 6을 받습니다(`HOLD_REVISIONS` (5, 6), :202-206, :378-383). rev 6 새 키 5개(`jp3_r58_witness_carries`·`jp3_r59_substeps`·`jp3_r510_candidates`·`r59_end_guard_substeps`·`r59_nan_stroke_substeps`)는 모두 `extend_bound_check` 안에 있어 T-JR-10 기록 대조에서 빠집니다(`jp3_t8_rules.py:13`, :49-56). `hydraulics_record` 최상위 키 이름은 4a와 같습니다 |
| (6) dg3·t12 | 문제 없음(정적) | r79 키로 짝짓고, `v5_setting` 이름과 `HOLD_REVISIONS`(:678)로 검사합니다. 78fd5d2d dg3는 `.done` 대신 `dg3.stop`으로 폴더를 찾고(`common_ed5.ps1:122-134`), 그 dg3 파일 셋은 로컬에 있습니다 |
| 12b `jp3_12b_judge.py` | 문제 없음(일부는 실측) | 태그는 `extend_start_revision_of_tag`로 네 꼴을 판별합니다(:598-603). 줄 읽기와 존재 검사는 c dry `dry-c`에서 실제 VBK·VBK0 줄로 돌았습니다. decide·judge·grade-judge는 실데이터로 돈 적이 없습니다 |
| (7) records `t4h_replay`·`records` | 구조 문제 없음, 실행 확인 없음 | 저장 T4h 표지가 h10 426개·H-6 135개 모두 `final_C4G2_P3_LAS_K1`, `tracked_bound`, bound rev 4입니다. 그래서 "edition 3 기록 거부"(t4h_replay.py:285-291) 대상이 아닙니다. `check_extend_start`는 rev 6을 허용합니다(v5_options.py:501-504). 판정은 `REPLAY_REVISION = 6`(:235-240)을 요구합니다. 다만 이 단계는 4a에서도 실행된 적이 없습니다 |
| ckdrop `jp3_ckdrop_plan.py` | D-3 연동 주의 | 씨앗이 충돌하면 +1로 옮기도록 설계돼 멈추지 않습니다. 그러나 `TAKEN_SEEDS = {25, 90, 91, 95..99}`(:46)가 하드코딩돼 있어 D-3·D-4에서 씨앗을 바꾸면 함께 바꿔야 합니다 |
| (8) j9main `jp3_j9main_judge.py` | 문제 없음 | `SETTING_MAP`(VBJ→VB, LSJn→LSn, :79). 저장 `main.jsonl` 종단 시험이 짝짓기를 단언합니다(`J_vs_V0 runs == 100`, `no_reference == {}`, LS 72; test_jp3_j9main.py:456-484) |

### 3. 정오 5 5-3 스캔 제외 한계의 범위
- **dry** (`jp3_dryrun_evidence.py`)
  - 제외는 `SCAN_EXCLUDED_FOLDER = "02_control/j_p3_cause/j9_runs/"`(:158, 4a-6 G-1)뿐입니다.
  - 새 커밋에서 `-Part dry`를 돌리면 ae9d0b2d `prelaunch_j9/ed5_inputs/dry_selection.json`의 s25(g6·g8·ref)를 찾고, s26으로 밀려 G-3 Stop(:322-328)이 납니다. → D-4
- **x11** (`jp3_12b_plan.py`)
  - 설계상 `j9_runs`와 dry 출력까지 스캔합니다(:146-161, 6.3.1).
  - dry 씨앗 90·91은 고정이고, 그 키가 스캔에 있으면 NotUsable로 멈춥니다(:248-253).
  - ae9d0b2d의 `j9_runs/ae9d0b2d/cdry_a1/*.json`과 `ed5_inputs/x11/c90·c91_plan.json`에 그 키가 있으므로 **새 커밋의 x11은 반드시 멈춥니다**. 폴더를 `j9_runs`로 옮겨도 피할 수 없습니다. → D-3
  - 블록 씨앗 40~43은 ae9d0b2d b-계획과 겹쳐 50~53으로 옮겨집니다. 설계대로이며 반복 수가 기록됩니다.
- **test_d1a** (`05_tests/unit/test_jp3_addendum_4a4.py:200-215`): 메인 checkout `06_analysis`를 다시 스캔하므로, 현재 판의 `ed5_inputs/dry_selection.json`이 있으면 항상 실패합니다. → D-5

### 4. 결함 목록 (control 전달용)

**D-1 [High, 확인] 사례 D의 기준선 대조 짝짓기**
- 위치: `04_scripts/04_hydraulic/coupled/jp3_baseline_compare.py:251-273` (`pair_rows`: `job` 전체를 키로 하고 설정 대응 없음), :671-675 (짝짓기 예외가 모든 P4 검사보다 먼저). `prelaunch_j9/run_steps_ed5/step4a_cases.ps1:29-30`.
- 근거 명세:
  - 정오 1 2절 "사례 D는 새 시험 전용 설정 `VBG6`로 돌린다", "판 5에서 `VBG5`는 돌리지 않는다"
  - 같은 절 [요청 밖 추가]: VBG5↔VBG6 대응은 78fd5d2d와의 T8 해시(P5-1)에만 정했습니다.
  - 원판 209행 "사례 재생(A~F·X11·F-A): 판 4a 정의 그대로다. 기대값은 P5-1·P5-2다"
  - 221456d 기준선 대조에서 D를 어떻게 다룰지는 어디에도 없습니다.
- 증상: `not_judgeable ['VBG5: 0 new rows']`. A~E 전부의 P4-1~P4-9가 실행되지 않았습니다.
- 고칠 방향:
  - (a) 짝 키에 VBG6→VBG5 대응을 넣고(P5-1 `SETTING_OF_PREVIOUS_EDITION`과 같은 방식) D에도 P4를 겁니다.
  - (b) 기준선 VBG5 행을 대조 집합에서 빼고 그 사실을 보고 키로 남깁니다. D는 5.3 D 행, P5-1, P5-2로만 판정합니다.
- 명세 판단: **필요**. (a)라면 D에 적용할 P4 항목도 정해야 합니다(D-2).

**D-2 [High, 추정: 정의 충돌] rev 6 줄 대 rev 5 기준선의 P4-2(그리고 P4-4·P4-9) 적용**
- 위치: `jp3_baseline_compare.py:534-566` (`_read_counts`: "used bound new ≥ baseline − 1 Pa", 올라간 읽기는 4a-2 2.2 사슬 사유 `stretch_source`·`lookback`·`inherit`·`tracker_chain`로만 설명), :448-498 (`chain_explanation`), :585-591 (허용 분류 변화는 EXT→CARRY_ext와 RET→CARRY_ret뿐), :612-622 (P4-9), :652-666 (P4-4 씨앗 수가 기준선과 같은지).
- 근거 명세:
  - 원판 4.2 R5-9: 해제 증거 뒤 $\hat p$를 감압 상계로 갱신합니다.
  - 원판 4.3 R5-10: R5-9 뒤 HOLD 후보를 $\max(13+p_h/3,\ p_{ret,i},\ \hat p+\delta_m)$로 바꿉니다.
  - 원판 208행 "rev 6은 비교값만 바꾼다", 209행 "판 4a 정의 그대로", 4.5 "바꾸는 것은 `_LockStretch`·`_CarryState` 후보, 추적기 $\hat p$, 기록뿐이다".
  - P4-2의 예측(낮아짐 0, 올라감은 rev 5 사슬로 설명)은 rev 5 대 rev 5(4a) 비교의 성질입니다. rev 6 메커니즘은 그 사유 목록 밖에서 한계를 바꿀 수 있습니다.
- 4a와 다른 점: 4a는 새 줄과 기준선이 모두 rev 5였습니다. 판 5에서는 B·E(·D)가 rev 6 대 rev 5입니다.
- 위험: 도구를 그대로 두면 정의상 rev 6 동작이 "P4-2 실패"로 셀 수 있습니다. **값을 보지 않았으므로 실제로 그런지는 모릅니다.**
- 고칠 방향:
  - (a) rev 6 줄의 P4-2·P4-4·P4-9를 기록으로 낮추고, 판정은 P5-1·P5-2와 사례별 5.3 조건으로 합니다.
  - (b) rev 6 사유(R5-8 목격, R5-9 소단계, R5-10 후보)를 사슬 설명에 더하는 새 예측을 정합니다.
  - (c) P4-1(T8 명령 해시)만 rev 6에도 판정으로 둡니다(4.5와 맞음).
- 명세 판단: **필요** (control, 결과를 보기 전에 정해야 합니다).

**D-3 [High, 확인] 새 실행 커밋에서 x11 준비가 반드시 멈춤**
- 위치: `jp3_12b_plan.py:85` (`DRY_SEEDS = (90, 91)` 고정), :248-253 (dry 키가 스캔에 있으면 NotUsable), :146-161 (스캔은 `j9_runs` 포함, 6.3.1). 연동: `jp3_ckdrop_plan.py:46` (`TAKEN_SEEDS`).
- 근거 명세: 원판 6.3.1(스캔 범위, 충돌 시 블록 씨앗 +10), 6.3.10(c 건식 씨앗 90·91), 정오 5 5-3("다시 돌리면 앞 시도의 출력에 걸린다… 다시 돌려야 하면 멈추고 묻는다").
- 증상(정적 확인): ae9d0b2d c dry 출력 `j9_runs/ae9d0b2d/cdry_a1/VBK*_c90·c91.json`과 `ed5_inputs/x11/c9x_plan.json`에 s90·s91 키가 있어 NotUsable(종료 2)이 납니다. 보관 위치를 옮겨도 `j9_runs`가 스캔되므로 피할 수 없습니다.
- 고칠 방향:
  - (a) 다시 준비할 때의 c 건식 씨앗을 새로 고정합니다(예: 92·93). ckdrop `TAKEN_SEEDS`도 함께 바꿉니다.
  - (b) dry 씨앗에도 블록처럼 증가 규칙을 둡니다.
  - (c) 대체된 준비 출력(`j9_runs/<옛 커밋>`)을 스캔에서 빼는 규칙을 둡니다. 6.3.1 "아무것도 빼지 않는다"를 바꾸는 것입니다.
- 함께 정할 것: ae9d0b2d c 건식 결과는 이미 봤습니다(관문 통과). 같은 씨앗을 다시 쓸지(재현) 새 씨앗을 쓸지는 봉인 규칙의 판단입니다.
- 명세 판단: **필요**.

**D-4 [Med, 확인] 새 커밋의 dry 선정이 G-3로 멈춤**
- 위치: `jp3_dryrun_evidence.py:158` (`SCAN_EXCLUDED_FOLDER`는 `j9_runs/`만), :322-328 (s25가 아니면 Stop).
- 근거 명세: 4a-6 G-1(사용자 결정 2026-11-21: `j9_runs/` 제외), G-3, 정오 5 5-3.
- 증상: ae9d0b2d `prelaunch_j9/ed5_inputs/dry_selection.json`의 s25가 잡혀 s26으로 밀리고, 판정 불가로 멈춥니다.
- 고칠 방향:
  - (a) 코드 변경 없이 절차로 처리합니다. ae9d0b2d `ed5_inputs`를 `j9_runs/ae9d0b2d/ed5_inputs/`로 옮깁니다(dba05b3f·8003083d 때와 같은 방식, 커밋 45e1d67a·5d617a1b). 이때 새 선정은 같은 s25 키를 다시 만듭니다. 그 키의 dry 실행(`j9_runs/ae9d0b2d/dry_a1`)은 이미 돌았습니다.
  - (b) 스캔에서 `prelaunch_j9/ed5_inputs/`를 뺍니다(G-1 확장).
- 명세 판단: (a)는 기존 규칙 안이지만 같은 키를 다시 쓰는 것이 괜찮은지 확인이 필요합니다. (b)는 **필요**합니다.

**D-5 [Med, 확인] `test_d1a` 시험 환경 실패 (정오 5 5-2에서 이미 공개)**
- 위치: `05_tests/unit/test_jp3_addendum_4a4.py:200-215`.
- 고칠 방향:
  - (a) 저장된 `dry_selection.json`에 기록된 스캔 파일 목록(경로·sha)만 다시 스캔해, 다시 만든 선정이 저장본과 같은지 단언합니다. 그러면 준비 출력과 무관하게 재현을 증명합니다.
  - (b) 현재 판의 `ed5_inputs`를 빼고 스캔합니다.
- 명세 판단: 불필요(시험 수정). D-4 (b)를 고르면 그와 맞춥니다.

**D-6 [Med, 확인] D-1을 놓친 시험 공백**
- 위치: 판 5 시험에 `jp3_baseline_compare.main`을 실제 기준선 꼴(cd: VBG4·VBG5)과 판 5 출력 꼴(VBG4·VBG6, rev 6 정체성)로 끝까지 도는 시험이 없습니다. `VBG6`이 나오는 시험은 P5-1·입력 쪽(`test_jp3_ed5_erratum1.py:87-119`)뿐입니다.
- 근거: 자체 점검 규칙 (가)(생산자 실제 출력 꼴로 `main`을 끝까지)와 (나)(문제 분류 전부를 단언).
- 고칠 방향: 기준선 행을 복사해 설정·정체성만 판 5 꼴로 바꾼 합성 입력으로 `main` 종단 시험을 만들고, 짝 수와 분류 전부를 단언합니다. 판 5 출력 자체를 시험 입력으로 쓰면 판정을 미리 돌리는 셈이 되므로 쓰지 않습니다.
- 같은 꼴의 다른 공백(Low): `test_jp3_j9main.py:477-478`의 종단 시험은 상태를 0/1/2 어느 것이든 받습니다(짝 수는 단언함). records·12b judge·decide는 실제 출력 꼴의 종단 시험이 없습니다.
- 명세 판단: 불필요.

### 참고
- 러너가 만든 dry·fpath·cases 출력(`j9_runs/ae9d0b2d/dry_a1`·`fpath_a1`·`cases_a1`, `dry.done`·`fpath.done`·`cases.stop`, `_identity_checks` 3개)은 아직 미추적입니다. 새 커밋 준비 전에 커밋할지 정해 주십시오(D-4 (a)로 보관할 때 같이).
- 이 목록이 정한 순서(이번에는 구현하지 않음): 정오 6(control) → 도구와 시험 수정(python-expert: D-1·D-2 결정 반영, D-3 씨앗과 ckdrop 연동, D-4·D-5, D-6 시험) → 새 실행 커밋 → 준비 재실행.

### 실행한 검증
- 값을 내지 않는 즉석 스크립트 5개로 키 존재, P5-1 짝, 기록 키 이름, T4h 메타 표지를 확인했습니다. 실행 뒤 지웠습니다.
- 도구, 시험, 명세 줄을 Grep과 Read로 대조했습니다. 파일은 바꾸지 않았습니다.

사용한 스킬: 없음
