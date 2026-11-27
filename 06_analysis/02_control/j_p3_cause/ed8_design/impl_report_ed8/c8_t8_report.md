# 436.9 판 8: C8 완료, T8 일부만 진행(WIP), 4단계 실행 전에 멈춤

## 요약
- **C8 완료.** 실행 커밋은 `56849248371b4916e2fe683265e7abffdd6fb8d7`(ed8-impl 브랜치)이고, 부모는 구현 커밋 `41e107e9`입니다.
  - 키 sha 표, P8-10 시험, run steps 전체(4·5·6·8~10단계 명령, l1ref, check, 건식 실행, 전체 시험, 설정 템플릿)를 넣었습니다.
  - 건식 실행은 종료 0이었습니다. 두 거부 경로(S8-C sha가 다를 때 2, 이미 끝난 census를 다시 돌릴 때 2)도 기대대로 나왔습니다.
  - ps1_lint는 14파일 모두 0, placeholder_scan은 0입니다(허용 자리 2개).
  - 전체 단위 시험에서 새 실패와 새 건너뜀은 없습니다.
- **P8-16을 41e107e9에서 다시 돌려 통과했습니다**(54/54 같음).
- **T8은 일부만 했습니다.** WIP 브랜치 `ed8-judge`에 `01b5cc2c` 하나를 올렸습니다. C8의 자식이며 **판정 커밋 T8이 아닙니다.**
  - 들어간 것: 규칙 핵심(병합, 층 칸, 상태 순서, G′ 5·8단계, Jeffreys, CP95), 4단계 관문 판정(P8-0·1·5·8·15·16), P8-11 바이트 동일 시험.
  - 빠진 것: census와 G′ 판정 도구의 실제 줄 연결, P8-2, l1ref, 12a·12b 판 8. 이 상태로는 4단계 판정을 할 수 없습니다.
- 실제 결과에 판정 도구를 돌린 적은 없습니다. 시험 입력은 모두 합성입니다.

## 1. P8-16 재실행 (구현 커밋 41e107e9)
- **추가 구현 커밋을 둔 이유:** 12b run steps(실행 경로 모듈)가 `jp3_12b_plan.py --edition 8`을 써야 하는데 27c0f046에는 그 인자가 없었습니다. 그래서 구현 커밋 `41e107e9`을 더했습니다(ARMS VBKN0/VBKN, 판 8 계획 바이트 = 판 7). 이 때문에 C8의 부모는 지시문에 적힌 27c0f046이 아니라 41e107e9입니다.
- **결과:** pass, equal 54/54(B_impl 27, L2_impl 27), 남는 run 키 0. 끝 시점 HEAD는 41e107e9, clean True입니다.
  - 출력 폴더: `ed8_design\p816_prerun_41e107e9\`
  - SHA256SUMS: `0921e251dcbd98dbeae7ca67de343fdee00cc4c16b429f1c7ea28b9808070de6`
  - p816_compare.json: `de7ca9d7…6b76`
  - 같은 폴더에 run_p816.ps1을 복사해 두었습니다. 예약 `r-20261126211440-9deb5c`는 해제했습니다.
- p816.jsonl의 sha(`4bbbb2e8…`)는 27c0f046 때와 다릅니다. 줄 기준 비교는 54/54 같습니다.

## 2. C8 (`56849248`, 명세 11.1·P8-10)

### 키 파일
- 41e107e9 트리(clean)에서 다시 만들었습니다. 위치는 `ed8_design\keys_seal_41e107e9\`입니다.
- census `278b332f…c535`(1043줄), held-out `a18b5818…2ee5`(339줄)로, 초안과 sha가 같습니다.

### 바뀐 파일
| 파일 | 내용 |
|---|---|
| `run_v5.py` | `ED8_KEY_FILE_SHA256`에 두 줄 넣음, docstring 고침 |
| `05_tests/unit/test_ed8_run_commit.py`(새 파일, 시험 8개) | 상수, P8-10 재생성(sha·바이트·`lines`를 봉인 폴더와 대조), 봉인 파일 수락(1043 / 339 / 678), 줄을 바꾼 사본·다른 이름 거부 |
| `test_ed8_impl.py` | "빈 표" 경우가 표를 스스로 비우게 고침(C8부터 표가 차므로) |
| `prelaunch_j9\run_steps_ed8\` 14파일(LF, `-text`) | 아래 참조 |

- run_steps_ed8의 공통 파일 `common_ed8.ps1`이 하는 일:
  - C8 설정 읽기, P8-10 범위 검사(부모 = 41e107e9, 03_src 변경 없음, run_v5 diff에 census 줄 있음), 시작·끝 정체성.
  - `NUMBA_CACHE_DIR = ~\.claude\runners\outrigger-ed8\numba_cache\<C8 8자>`를 worktree·결과 루트 밖에 둡니다. worktree에 `.nbi`/`.nbc`가 있으면 시작과 끝에서 멈춥니다.
  - 출력 경로가 이미 있으면 거부, 8~10단계는 S8-C 봉인 확인.
- 실행 방식: ed8_probe 부분(P8-5·8·15·16)은 `conda run --no-capture-output -n dynamics-dev python -I -B`(P8-14 기준과 같음, 규칙 (바)), 나머지는 dynamics-dev `python.exe`를 직접 부릅니다.
- **범위 판단:** `test_ed8_impl.py`도 범위 목록에 넣었습니다("그 값을 단언하는 시험 기대값"으로 봄). C8 범위 밖 변경은 없었습니다.

### C8 커밋을 세 번 amend했습니다
- 5593353b → 27fe07c1 → e6b6ec0c → 56849248. 이유는 건식 실행에서 드러난 결함 두 가지였습니다.
  - `return @()`가 `$null`로 돌아와 `.Count` 오류.
  - `switch`가 내는 `@()`가 `$null` 원소로 바뀌어 `Test-Path $null`.
  - 그리고 주석 속 `<scratch>` 자리 표시를 고쳤습니다.
- 앞의 세 sha로 실행된 것은 없습니다.

### 건식 실행
- 증거: `impl_report_ed8\c8_dry_run_56849248\commands_ed8.json`(`3f8f807b…`)
- 단계 21개의 명령, 환경 변수 `NUMBA_CACHE_DIR`, 출력 경로를 확인했습니다.

### P8-4 전체 단위 시험 (C8)
- 명령: Chrono-dev, `-n 12 --dist loadfile`, `OUTRIGGER_RECORDS_ROOT` 지정. 25분 걸렸습니다.
- 결과: 2 실패, 8605 통과, 134 건너뜀. 끝 시점 HEAD는 C8, clean입니다.
  - 실패 두 건(`test_hydraulics_flow_limit_run::test_coupled_batch_rows_and_resume`, `test_d8x_diag::test_rerun_gives_the_stored_command_hash`)은 base 7fc83456과 66648ea8에서도 실패하던 **기존 실패**입니다.
  - 66648ea8 junit과 비교하면 새 실패와 새 건너뜀은 0입니다(k2 시간 초과 1건은 이번에 통과). 건너뜀은 134로 같습니다.
- 기준선: 명세의 기준선은 "C8의 부모"인 41e107e9입니다. 41e107e9 자체의 전체 시험은 돌리지 않았고, 시험 파일만 다른 66648ea8 junit을 기준으로 썼습니다. 정식 P8-4는 `full_suite_ed8.ps1 -Side base`를 41e107e9 worktree에서 돌려야 합니다.
- 증거(`impl_report_ed8\tests\`): `junit_C8_56849248.xml`(`b747aee6…`), `junit_diff_66648ea8_vs_C8_56849248.txt`, `suite_C8_56849248.log`

### 정적 점검
- ruff: 새 코드는 통과. `run_v5.py` 1034·1039·1043행 E501 세 건은 기존 코드라 고치지 않았습니다.
- codespell: 0건.

## 3. T8 WIP (`ed8-judge` 브랜치 `01b5cc2c`, C8의 자식)

### 커밋에 든 것
- `jp3_ed8_rules.py`: 순수 규칙 함수입니다.
  - census
    - 6.2 병합: 해시 병합, 같은 (설정, 행)의 eps 0 / 0.001 병합, 소유 단계는 C-J→C-S→C-D→C-G 순서의 첫 단계.
    - 병합 단위: 기회·실패·층(구성원 중 하나라도 E면 E). 해시 없는 오류 줄은 병합하지 않고 그 단계를 판정 불가로 둡니다.
    - 5.2 칸: C-J·C-S·C-G × E/N 6칸. C-D 소유 단위는 C-G 칸에서 셉니다. 허용 수 0, 빈 층은 `not_applicable`, 기회 0 단계는 판정 불가.
    - 선택 사용 키 칸, 상태 순서(10절).
  - G′
    - 7.3 5단계 순서: 1차 별칭, n_E < 16이면 E를 N에 합침, n_N < 200이면 판정 불가, E A/A 실패 ≥ 2면 멈춤, n_AA,E = 0이면 합침, n_AA,N = 0과 CP95 > 0.025면 멈춤.
    - Jeffreys 예측 k_N, k_E = 1, MDE80, `ho_k_selection` 레코드(slot_layers 포함).
    - 8단계: 판정 계산 전에 해시만으로 2차 별칭, 동결된 A/A 값으로 k_N 재계산, 층별 해당 없음, G′ 기회가 모두 0이면 판정 불가.
- `jp3_ed8_gate_judge.py`: 4단계 관문 판정입니다. 모두 run step `.done` 기록을 먼저 확인하고, `--out`은 새 경로만 받습니다. 종료 코드는 0/1/2/3입니다.
  - P8-0: b46bdf8f 재현 114줄과 해시 대조, 기준 sha 고정.
  - P8-16: `p816_compare` 재사용.
  - P8-5: 라운드 수와 `twist_stiffness_scale`이 JSON 텍스트로 같을 때만 비교, 15쌍 미만 판정 불가.
  - P8-8: 켬 팔 `short_run_extended`, 5쌍 미만 판정 불가.
  - P8-15: 켬 팔 waiver 미사용 = `n_waiver_done` 0이고 `n_waiver_periods` 0, 20쌍 미만 판정 불가.
  - P8-1: 대체 없는 쌍의 해시 비교.
  - 기록 키는 줄에서 먼저 찾고, 없으면 T4h meta에서 찾습니다. 둘 다 없으면 판정 불가로 두고 0으로 읽지 않습니다.
- 시험 83개, 모두 통과했고 합성 입력만 씁니다.
  - `test_ed8_judge_rules.py` 47개: 빈 집합, 0건, 필드 결측, 판정 불가 경로 포함.
  - `test_ed8_gate_judge.py` 32개: 생산자 꼴 줄을 쓰고, CWD를 다른 폴더에 둔 채 `main`을 끝까지 돌립니다. 상태 분류 전부를 assert합니다(커밋 다른 경우, clean 아님, `.done` 없음, `--out` 있음, 예상 밖 예외 = 3, `--help`).
  - `test_ed8_run_path.py` 4개: C8의 03_src 트리와 실행 경로 모듈 156개가 바이트 같음, closure 불변, 판정 모듈이 실행 경로에 없음, C8 대비 diff는 `04_scripts`·`05_tests`뿐.
- `05_tests/data/ed8_run_path_modules_56849248.json`(`c161bf88…`): C8의 git archive에서 만든 실행 경로 목록입니다. 생성기는 판 7 것을 판 8용으로 고친 `impl_report_ed8\t8_wip\make_run_path_list_ed8.py`입니다(ed8_probe 진입점, run_steps_ed8, core_kind_ed7.ps1 추가).
- ruff(프로젝트 설정)와 codespell은 0건입니다.
- 생산자 꼴 미시험: 관문 판정은 아직 실제 C8 출력 꼴로 돌려 보지 않았습니다. 4단계 출력이 생기면 짧은 건식 판정(출력은 실행 폴더 밖)을 권합니다.

### 남은 T8 작업 (이어서 할 일)
1. **판 7 판정 도구가 ed8 계열에 없습니다.** `60ebb4a4`(ed7-judge)의 `jp3_ed7_judge.py`, `jp3_ed7_rules.py`, `jp3_12b_judge_ed7.py`, `jp3_tjr_judge_ed7.py`, `jp3_rev7_condition.py`·`ed7_condition3_adoption.py` 변경은 ed8-impl 기준 7fc83456의 조상이 아닙니다. 판 8 판정 도구가 이것들을 재사용하려면 먼저 T8에 들여와야 합니다(`cherry-pick -n` 등). 이 두 파일이 C8 실행 경로 목록에 없는지는 시험이 막아 줍니다.
2. census 판정의 줄 연결
   - 단위 입력: C-J는 VBN→VB, LSN<n>→LS<n>로 이름을 바꿔 판 7 항목으로, C-S는 VBN<key> 감도 이름으로, C-D는 J-P3a·FAULT와 V0 비교, C-G는 `v0_grid_comparison`으로 만듭니다.
   - 층은 `ed8_key_lists.stratum_of`로 정하고, 결측은 `setting_defect`입니다.
   - J-P3는 경로 1 줄 단위로 판정합니다. 정체성 검사는 `_ED8` 태그로 합니다.
   - 기록: L-2 면제 사용 줄, 교착 서명, 선택 사용 키 목록(P8-9·P8-9′·P8-14 키).
3. G′ 판정 연결: 5단계 V0 A/A를 C-J (i)로 판정하고 `ho_k_selection.json`을 만듭니다. 8단계 판정도 연결합니다.
4. P8-2(cases), l1ref, 12a(tjr)와 12b 판 8 이름, 8절 4사례 기록.
5. WIP 커밋을 T8 한 커밋으로 합치고, T8 전체 단위 시험(이번에는 WIP라 돌리지 않음), verif 감사를 거칩니다.

## 4. worktree 정리와 제안
- ed8-impl worktree에서 무시 대상 `__pycache__`를 지웠습니다(1차 14개, 전체 시험 뒤 2차 13개. .pyc 83개, numba 파일 28개). `.hypothesis`도 지웠습니다.
- 전체 시험은 `-B`와 `PYTHONDONTWRITEBYTECODE`를 줘도 하위 프로세스 시험이 .pyc를 다시 만듭니다. 그래서 실행 worktree에서 시험을 돌리지 않는 쪽을 권합니다.
- 지금 상태: worktree HEAD는 `ed8-impl` = C8, `status --ignored`는 비어 있습니다. T8 WIP는 브랜치 `ed8-judge`에만 있습니다(체크아웃 없음).
- **제안**
  - C8 실행 worktree는 지금 있는 `C:\workspace\outrigger_control\.claude\worktrees\ed8-impl`(HEAD 56849248)를 그대로 잠가 쓰는 것을 권합니다. 커밋을 이 worktree 안에서 했으므로 `identity --mtime` 경고가 생기지 않습니다. 새 worktree를 만들면 mtime 경고가 납니다.
    - `git -C C:\workspace\outrigger_control worktree lock .claude\worktrees\ed8-impl`
  - T8은 `C:\workspace\outrigger_control\.claude\worktrees\ed8-judge`에 새로 만들기를 권합니다. T8을 완성한 뒤 잠급니다.
    - `git -C C:\workspace\outrigger_control worktree add .claude\worktrees\ed8-judge ed8-judge`
- 메인 checkout에 둘 설정: `prelaunch_j9\ed8_run_config.json`(템플릿에서 run_commit = 56849248…, worktree = 위 경로)입니다. 4단계 전에 `check_ed8.ps1`이 0인지 확인하십시오.

## 5. 검증 요약
| 검증 | 결과 |
|---|---|
| P8-16 @41e107e9 | pass 54/54 |
| C8 시험 8개(test_ed8_run_commit + batches) | 통과, 건너뜀 0 |
| C8 전체 단위 시험 | 2 실패(기존), 새 실패·새 건너뜀 0 |
| C8 건식 실행 | 종료 0 |
| ps1_lint | 14파일 모두 0 |
| placeholder_scan | 0 |
| T8 WIP 시험 83개 | 통과 |
| ruff / codespell (새 코드) | 0 / 0 |
| T8 전체 단위 시험 | 미실행(WIP) |
| pip-audit | 미실행 |

## 확인 필요
1. **A/A 같은 층 대조(7.4):** E를 N에 합친 뒤에도 원래 층으로 짝을 맞추도록 구현했습니다. 또 같은 층 첫 짝의 해시가 같으면 기회에서 빼고 다음 후보로 넘어가지 않게 했습니다. 다른 해석도 가능합니다.
2. **MDE80(7.5):** 명세에 식이 없습니다. "P(Bin(n, p) > k) ≥ 0.8인 최소 p"로 구현했습니다. 공개 수치(n 200에서 2.7 / 4.5 / 5.6 %)와 같은 정의인지 stats-design-expert가 확인해야 합니다.
3. **census 칸:** C-D 소유 병합 단위는 기회와 실패를 모두 C-G 칸에서 세고, C-D 단계는 줄 판정(J-P3a·FAULT)으로만 판정합니다. "6칸" 해석입니다.
4. **P8-15 "면제 사용":** `n_waiver_done`과 `n_waiver_periods`가 모두 0인 줄만 판정 쌍으로 셉니다.
5. **C8 부모:** 41e107e9입니다(지시문의 27c0f046이 아님). 사유는 1절에 적었습니다.

## 메인 세션 권고
- P8-4 기준선(명세대로 C8 부모 41e107e9)이 필요하면, 41e107e9 worktree에서 `full_suite_ed8.ps1 -Side base`를 돌리십시오. 약 25~30분 걸리고 출력은 `~\.claude\runners\…`입니다.

## 위임 필요
- stats-design-expert: 확인 필요 2(MDE80 정의)를 확인.
- python-expert(이어서): 3절 "남은 T8 작업" 1~5.

## 공개 (실제 행위)
- 블라인드 경로(`606f8713\cdry_a1\VBK_c92*`·`VBK_c93*`·`logs\`, `ed6_inputs\x11\selection.json`, worktree 사본)는 열지 않았습니다.
- **규칙 어긋남 1건:** Grep 한 번을 path = ed8-impl **worktree 루트**로 실행했습니다. glob은 `{03_src/outrigger_sim/control/*.py,04_scripts/04_hydraulic/coupled/*.py}`로 좁혔고 결과는 "No matches"였습니다. 블라인드 이름은 나오지 않았습니다.
- 그 밖의 검색 위치
  - Grep·Glob은 worktree의 `04_scripts\04_hydraulic\coupled`, `05_tests\unit`, `03_src\outrigger_sim\control`, `prelaunch_j9\run_steps_ed7`·`run_steps_ed8`·`run_steps\record_helper.ps1`로 하위 경로를 직접 지정했습니다. 명세 파일 1개도 열었습니다.
  - PowerShell 목록 조회는 `j_p3_cause\ed7_design`에서 `make_run_path_list.py`만 찾았습니다.
  - worktree의 `03_src`·`04_scripts`·`05_tests`는 `__pycache__`와 numba 파일만 셌습니다.
- 이번 구간에서 Bash는 git 단일 명령에만 썼고 파이프는 쓰지 않았습니다. 앞 구간에서 Bash 파이프를 쓴 적이 있습니다(이전 보고에 적음).
- 프로세스를 종료하지 않았습니다.
- 결과 파일
  - `p816_prerun_41e107e9`의 run_identity와 progress 파일만 읽었습니다(판정값 없음).
  - P8-14 계획 파일은 ed8_probe `--list` 인자로만 넘겼습니다.
- scratchpad `python-ed8-c8t8`는 지웠습니다. 남길 것은 지우기 전에 근거 폴더로 옮겼습니다.

사용한 스킬: 없음

## 메모리 반영안
- `env_powershell_empty_array_return.md`에 덧붙임: `switch`의 `@()`는 `$null`이고, `@('a') + $null`은 `$null` 원소를 만들며, strict 모드에서 `$null.Count`는 오류입니다. 공통 ps1을 고칠 때마다 건식 실행을 다시 돌립니다.
