## 판 7 실행 커밋 C 보고

실행 커밋 C를 b46bdf8f의 자식으로 하나 만들고 멈췄습니다. 병합·push·T 작업은 하지 않았습니다.

- **C = `8a2a52ce2c07d2af11a6212a2932d2061261f156`**: worktree `C:\workspace\outrigger_control\.claude\worktrees\ed7-impl`, 브랜치 ed7-impl, 부모 b46bdf8f.
- C의 03_src tree id는 `0cffdbdfc64f6a3daa855f5c2f2fdaf1c7dbf04f`입니다. run steps가 이 값을 단언합니다.
- worktree 상태는 clean이고 untracked 파일도 없습니다.

### 1. diff 요약 (b46bdf8f → C, 18개 파일)
- **(i)** `03_src/outrigger_sim/control/extend_start_bound.py`: 197~201행 한 덩어리(`@@ -197,5 +197,5 @@`)만 바꿨습니다. `JP3_SPEC_EDITION_V7 = "10902ffd"`로 고치고, docstring의 PROVISIONAL 문구를 봉인 사실(개정 6, master e241638d)로 바꿨습니다. 03_src diff는 이것뿐입니다.
- **(ii)** `04_scripts/04_hydraulic/coupled/run_v5.py`: `ED7_KEY_FILE_SHA256`를 명세 5.1 표의 두 값으로 채웠습니다(sens `be930b75…`, G1 `684054ab…`). docstring도 함께 고쳤습니다.
- **(iii)** 새 시험 `05_tests/unit/test_ed7_run_commit.py`(7개):
  - 두 상수 값, rev 7 `identity()["spec_edition"]`, rev 5·6 봉인값이 그대로인지 확인합니다.
  - `ed7_keys`가 봉인되지 않은 바이트를 거부하는지, 봉인 표 항목이면 받는지 확인합니다.
- **(iv)** `06_analysis/02_control/j_p3_cause/prelaunch_j9/run_steps_ed7/` 15개 파일. LF로 두었고 `-text` 속성이며, 판 6 파일은 바꾸지 않았습니다.
  - `common_ed7.ps1`(공용), `core_kind_ed7.ps1`, `check_ed7.ps1`, `dry_run_ed7.ps1`, `full_suite_ed7.ps1`(P7-4), `ed7_run_config.template.json`, 단계 스크립트 9개.

### 2. run steps 목록과 단계별 예상 줄 수
판정 명령은 넣지 않았습니다. 모든 단계는 실행만 합니다.

| 순서 | 스크립트 | 내용 | 줄 |
|---|---|---|---|
| 1 | `step5_impl_ed7.ps1 -Part scope` | P7-10 근거(git diff 4종), 실행 없음 | 0 |
| 2 | `step_l1ref_ed7.ps1` | L1_VBM0·L1_VBM(12b 키 167), L1a_VBM0·L1a_VBM(12a 키 102), P 1/4씩 | 538 |
| 3 | `step5_impl_ed7.ps1 -Part t8` | P7-1, `run_v5 ed7_t8` | 44 |
| 4 | `-Part cases` | P7-2, `ed7_cases`(E·F × 5) | 10 |
| 5 | `-Part probe` | P7-3·P7-9, `ed7_probe --arms a2 --part all` | 114 |
| 6 | `step6_confirm_ed7.ps1` | G1 `ed7_keys` 171 + `ed7_probe --part d` 24 | 195 |
| 7 | `step7_j9main_ed7.ps1` | `ed7_j9_main` | 388 |
| 8 | `step8_sens_ed7.ps1` | `ed7_keys` sens | 460 |
| 9 | `step9_dg3_ed7.ps1` | 12a VBM(0x00FF)·VBM0(0xFF00), H-6 135키 | 270 |
| 10 | `step10a_plan_ed7.ps1` | `jp3_12b_plan.py --edition 7`, 실행 없음 | 0 |
| 11 | `step10b_vbkm0_ed7.ps1 -Phase base` | VBKM0 b1·b2 | 334 |
| 12 | `-Phase b4 -Decision … -DecisionSha256 …` | T 결정이 needs_b4일 때만 | 167 |
| 13 | `step10c_vbkm_ed7.ps1 -Decision … -DecisionSha256 …` | T 결정이 decided일 때, 결정된 블록 | 334(b4 포함 시 501) |

모든 단계에 공통으로 걸린 동작:
- **새 출력 경로 강제(M-7)**: 출력은 `j9_runs\<C8>\<단계>_a<N>\`에 둡니다. 시도 폴더가 있거나, 출력 파일·T4h 폴더가 이미 있으면 거부합니다(종료 2).
- **정체성 기록**: 시작과 끝에 HEAD·is_clean·03_src tree를 기록합니다. 다르면 종료 3이고 `.done`을 남기지 않습니다.
- **입력 sha 단언**: 각 단계 시작에서 P7-10 범위를 다시 검사하고, 입력 파일 sha를 확인합니다. 대상은 봉인 명세 `10902ffd…`, 키 2종, L1 키 2종(판 6 값)입니다. common.ps1의 고정 입력 검사도 그대로 돕니다.
- **Get-CoreKind 수정**: `core_kind_ed7.ps1`가 common.ps1의 Get-CoreKind를 대체합니다. 마스크를 P/E/mixed로 판별하고, 잘못된 마스크는 종료 3입니다. 단계 기록 `core:<라벨>`과 `record.py --core`에 이 값이 들어갑니다(record.py가 `mixed`를 받는 것도 확인했습니다).

### 3. 검증 결과
- **P7-10 범위**: diff 경로 18개가 모두 (i)~(iv) 안에 있습니다. 03_src는 위의 한 덩어리뿐이고, `Get-ScopeProblem`이 건식 모든 단계에서 통과했습니다.
- **시험 (C에서 다시 실행, 시작·끝 HEAD = C, clean)**: Chrono-dev
  - `test_ed7_run_commit.py` + `test_ed7_units.py`: 68개 통과.
  - `test_ed7_harness.py`: 7개 통과(140 s), 건너뜀 0, xfail 0.
  - P7-0(옛 플랜트 7줄 해시 = 79495405, `test_p7_0_edition_6_settings_keep_the_run_hashes`) 통과.
  - P7-1 미리보기(VBM R12 = VBM0 R12, `test_p7_1_preview_vbm_and_vbm0_command_the_same_on_r12`) 통과.
- **ps1_lint**: 새 ps1 14개 모두 종료 0. 오류·경고 0, AST 파서 사용.
- **placeholder_scan `--pattern-set both`**: 종료 0. 남은 자리는 허용한 두 개뿐입니다: `<ED7_RUN_COMMIT>`, `<ED7_RUN_WORKTREE>`(템플릿).
- **건식 `dry_run_ed7.ps1`(C 기준)**: 13단계 모두 종료 0입니다. 마지막에 끝난 단계를 다시 돌리면 2로 거부되는 것도 확인했습니다.
  - mixed 마스크 0x0FFFFFFF는 `mixed`로, P 1/4 마스크는 `P`로 기록됐습니다. 별도 시험에서 E 마스크는 `E`로 나왔습니다.
- **거부 동작 시험(건식) 16건이 모두 기대대로였습니다**:
  - 시도 폴더가 이미 있음 → 2
  - 선행 단계 없음 → 3
  - 27번을 넘는 비트의 마스크 → 3
  - 같은 시도 재실행 → 2
  - `-MaskHex` 없음 → 3
  - 설정 파일 없음 → 3, 자리 표시가 남음 → 3, HEAD가 아닌 커밋 → 3
  - b4에 `-Decision` 없음 → 3, 상태가 needs_b4가 아님 → 2
  - 결정 파일 sha 불일치 → 2
  - decided인데 b4 단계가 끝나지 않음 → 2
  - `check_ed7.ps1` → 0
- **argparse·줄 수 (`--list`, 시뮬레이션 없음)**: t8 44, cases 10, j9_main 388, sens 460, G1 171, probe a2 114, probe d 24(P7-M-a2 12 + P7-Mslow-a2 12)로 모두 맞습니다. 봉인 키 2종은 새 `ED7_KEY_FILE_SHA256`로 받아들여졌습니다. `las_t3_dg3.py`는 env 없이 `--help`를 받지 않습니다(판 6과 같은 인자라 실행 시 문제는 아님).
- **ruff**: 내가 쓴 코드는 통과입니다. run_v5.py의 E501 3건(927·932·936행 argparse help)은 b46bdf8f부터 있던 위반이라 고치지 않았습니다. codespell은 0건입니다.

### 4. 근거 폴더
`C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\run_commit_8a2a52ce\` (파일 56개)
- 내용: diff·patch, 시험 로그·junit(C와 커밋 전), lint json, 건식 `commands_ed7.json`·요약·로그, 거부 시험, 줄 수, core kind 확인, 검증 스크립트, `manifest.json`.
- `manifest.json` sha256 `1aae47f19e8e48d44da2325819a9ad4fa0a04778090d2bffa8ed8bce2446c87d`
- `SHA256SUMS`(write-sums --recursive, 56항목) sha256 `43cb87c75133558434047f30eac359cc919fccb6f5d704e156557353b2a20431`
- scratchpad 하위 폴더는 지웠습니다.

### 5. 메인이 다음에 할 일
1. **실행 worktree와 mtime 주의(확인 필요 1)**: 단계마다 끝에 `baseline_check identity --mtime`을 돌립니다. `git worktree add`로 C를 새로 받으면 C가 바꾼 18개 파일의 mtime이 커밋 시각보다 늦어 경고(종료 1)가 나고, 단계가 종료 2로 멈춥니다(과거 사례 78fd5d2d·876d8a49).
   - ed7-impl은 18개 모두 커밋 시각보다 앞입니다(0/18, `mtime_vs_commit.json`).
   - 권고: **ed7-impl 자체를 C의 잠긴 실행 worktree로 쓰고**(`git worktree lock`), T는 C에서 새 worktree를 만들어 거기서 커밋하십시오.
2. **설정 파일**: 메인 checkout에 `prelaunch_j9\ed7_run_config.json`을 템플릿에서 만들어 run_commit과 worktree를 채운 뒤, `check_ed7.ps1`로 종료 0을 확인합니다.
3. **P7-4 suite(메인 세션 권고, 장시간)**: `<C worktree>\06_analysis\02_control\j_p3_cause\prelaunch_j9\run_steps_ed7\full_suite_ed7.ps1 -Side run -Worktree <C worktree> -OutDir C:\Users\jinbeom\.claude\runners\outrigger-ed7-suite\run_8a2a52ce -ExpectCommit 8a2a52ce2c07d2af11a6212a2932d2061261f156 -BaselineList <base existing_failures.txt> -BaselineSha256 571f42a1074b7d506be885d9c3a68f22b2661821e011e83d751bc6ac06ecabeb`
   - 기준 목록은 기존 runner의 `base\existing_failures.txt` 또는 `ed7_design\suite_b46bdf8f\base\`의 사본입니다.
   - 규모는 b46bdf8f 때(8688개)와 같습니다.
   - 쓰는 판정 도구 `jp3_ed6_suite.py`의 핵심 범위 패턴에는 `test_ed7_*`가 없습니다. 다만 test_ed7의 새 실패·새 건너뜀은 기준 목록 대조로 실패 처리됩니다.
4. **배치**: run_v5 단계(t8·cases·probe·confirm·j9main·sens)의 `-MaskHex`·`-Workers`는 compute-scheduler-expert 배치표로 정합니다. r79 단계(l1ref·dg3·12b)는 판 6처럼 P 1/4 고정입니다.
5. **실행 순서**: 위 표 순서이고, `.done`만 순서를 강제합니다. 판정이 T 뒤에 오므로, 단계 사이에 T 판정을 기다릴지는 메인이 정합니다(명세 "순서와 멈춤은 판 6 4절과 같다").

### 6. T 착수에 필요한 정보
- **출력 위치**: `06_analysis\02_control\j_p3_cause\j9_runs\8a2a52ce\` 아래 단계별 폴더입니다.
  - `impl_t8_a1\ed7_t8.jsonl`, `impl_cases_a1\ed7_cases.jsonl`, `impl_probe_a1\ed7_probe_a2.jsonl`
  - `confirm_a1\confirm_g1.jsonl`·`ed7_probe_d.jsonl`
  - `j9main_a1\j9_main.jsonl`, `sens_a1\sens.jsonl`
  - `dg3_a1\dg3_VBM(0).json`와 `VBM(0)_t4h`
  - `l1ref_a1\L1_VBM0|L1_VBM|L1a_VBM0|L1a_VBM.json`
  - `12b_plan_a1\x11\selection.json`(sha는 `.done`의 `selection_sha256`), `12b_vbkm0_a1\VBKM0_b1|b2.json`
  - 각 단계의 `step_record.json`과 `.done`
- **12b 결정 파일 형식(확인 필요 2)**: run steps는 T decide 출력에서 `status`(`needs_b4`/`decided`)와 `blocks`(b1·b2·b4의 부분집합)를 읽고, 파일 sha를 인자로 받아 대조합니다. P7-11 때문에 T가 run steps를 바꿀 수 없으므로, T의 decide 출력이 이 형식이어야 합니다.
- **실행 경로 모듈(P7-11에 따라 T에서 바꿀 수 없음)**:
  - 진입: `run_v5.py`, `ed7_probe.py`, `las_t3_dg3.py`, `jp3_run_identity.py`, `jp3_12b_plan.py`, `run_steps_ed7\*.ps1`
  - 이들의 정적 import 닫힘
  - 5.2가 요구하는 "C에서 만든 목록 파일(sha 고정)"은 이번에 만들지 않았습니다. T 감사 전에 별도 작업으로 만들어야 합니다.
- **판정 불가 범위**: P7-1·P7-2·P7-3·P7-9와 6~10단계의 모든 판정은 T와 그 감사 전에는 판정 불가입니다(5a). 

### 확인 필요
1. 위 5-1의 mtime 문제: 실행 worktree를 ed7-impl로 할지, 새 worktree로 하고 경고를 다른 방식으로 처리할지.
2. 위 6의 12b 결정 파일 형식.
3. **12b plan 위치·범위**: dg3 뒤에 두었습니다(판 7 출력 스캔 포함을 위해). 판 6은 실행 전 prelaunch에서 만들었습니다.
   - `--scan-required` 루트는 `j9_runs\79495405`(기록 B·C·D는 그 아래 `records_after_stop`으로 가정), `6bfb2560`, `b46bdf8f`, 이번 실행 루트입니다.
   - `--scan-exclude`는 빼고 도구의 블라인드 접두 가지치기에 맡겼습니다.
   - 명세(`jp3_remedy_spec_v7.md` 6.4·Y7-7)가 시점·루트를 문장으로 정하지 않았으므로 확인이 필요합니다.
4. **FIXED_INPUTS 목록 없음**: `jp3_fixed_inputs_list.py`에 `--edition 7`이 없고 C 범위상 추가할 수도 없습니다. 그래서 각 단계가 입력 sha를 하드코딩으로 직접 단언하게 했습니다(판 6 6.6 꼴과 다름).

### 공개(블라인드·절차)
- **블라인드 파일 이름 노출**: 판 6의 12b 계획 명령을 알아내려고 `prelaunch_j9\ed6_inputs\x11\selection.json`의 `inputs` 블록을 통째로 출력했습니다. 그 안의 `scan_excluded_files`에 블라인드 경로(`606f8713/cdry_a1/VBK_c92*`·`VBK_c93*`·`cdry_a1/logs/`) 아래 파일 이름 14개가 있어 그대로 노출됐습니다.
  - 내용·값·건수 이외의 정보는 읽지 않았고, 블라인드 경로 자체는 Read·Grep·Glob하지 않았습니다.
- **j9_runs 경로 확인**: `j9_runs\79495405`, `…\records_after_stop`, `j9_runs\6bfb2560`, `j9_runs\b46bdf8f`가 있는지 `Test-Path`로 확인했습니다(지정 경로 단건, 검색 아님).
- **실행 규칙 위반 1건**: Bash에서 `| wc -l` 파이프를 한 번 썼습니다. 정상 종료했고 Suspended는 없었습니다.

### 메모리 반영안
`tool_blind_prefix_walk.md`에 한 단락을 더했습니다: 판 6 `selection.json`의 `scan_excluded_files`처럼 기록 파일도 블라인드 이름을 담는다, 그러니 필드를 골라 읽는다. MEMORY.md 색인 줄도 고쳤습니다.

사용한 스킬: 없음
