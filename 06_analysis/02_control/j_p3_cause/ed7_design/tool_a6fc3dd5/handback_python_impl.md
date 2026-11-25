## 판 7 구현 보고 (436.9 J-P3, 명세 v7 개정 2, sha 85ce6e2a…)

의존성 점검: 확인한 항목은 모두 OK입니다. 사용한 스킬: 없음.

### 1. Q7-C3 토큰 충돌 점검: 충돌 없음
- 기준 커밋 79495405의 `03_src`, `04_scripts`, `05_tests`, `00_docs`, `02_params`에서 `git grep`으로 다음 토큰을 찾았습니다: `VBM*`, `LSM1~4`, `VBKM*`, `P3X`, `A_ib`, `probe_d6`, `p1_patch`, `stale_seed_release`, `plant_seed_artifact`, `"P7-`. 걸린 것은 PNG 바이너리의 우연 일치 2건뿐이고, 코드와 문서에는 하나도 없었습니다.
- 태그 판별은 접두가 아니라 기저 태그 사전으로 합니다(`extend_start_revision_of_tag`).
  - `final_C4G2_P3X` → 7
  - P3W → 6, P3 → 4로 그대로 판별됩니다(시험으로 확인).
- 접두 규칙과의 관계
  - `VBM`·`LSM`은 `"VB"`/`"LS"` 접두(③-on 기대 행)에 맞게 걸립니다.
  - `VBKM`/`VBKM0`만 로드 고장 접두 `VBK`에 걸리고, `VBM`은 걸리지 않습니다.
  - probe 이름은 `P7-<plant>-<arm>`입니다(판 6 `P6-` 관례).
- meta 이름: `probe_d6_settings`, `p1_patch`. 플랜트 기록 키: `stale_seed_release`.

### 2. 커밋
`a6fc3dd5`(ed7-impl 브랜치, 부모 79495405)에 커밋했습니다. 병합·push는 하지 않았고 worktree는 깨끗합니다. 새 파일은 커밋 전에 CRLF로 바꿨습니다(autocrlf 저장소).

### 3. 바뀐 내용 요약
- **Y7-1 `lock_start_b.py`, `c2.py`**: 구성 요소 `A_ib`를 더했습니다.
  - 사각 구간: 작용 명령이 `0<|u|≤u_hold`로 25주기 같은 부호일 때입니다. 정지 기준은 k_s+2..k_s+4 읽기의 E3이고 0.1 mm입니다.
  - 조건 3: (다)가 기본이고 초안·(나)는 `ib_condition` 옵션입니다. `_update_completion`과 같은 `is_on_target`·`_is_clearance_done`·relax `max_twist_N`을 씁니다.
  - 왕복 래치, 예측형 보호(0.85 mm, 41 MN/m, F_min+5 kN), 구현 주의 (가)(나)(다)를 넣었습니다.
  - 기록 `lsb_record.blind`와 `lsb_ib_*` 배열은 A_ib가 켜졌을 때만 생깁니다. `ib_*` 필드는 A_ib 없이는 바꿀 수 없고 meta에도 나오지 않습니다(판 6 meta 불변).
- **Q7-C1 인용(a6fc3dd5)**: `c2.py`
  - `_update_completion` 7804, `is_on_target` 7815
  - `_is_clearance_done` 7845
  - relax `max_twist_N` 1979
  - A(i)-b 입력 `_blind_fill_inputs` 10234(한계값 10246)
- **Y7-2 D6 증인과 탐침 수축**: `ground_contact.ProbeD6Settings`, `C2Config.probe_d6`, `two_pressure.probe_round_finished(witness=)`
  - 증인은 E3 0.3 mm입니다. 미개방 라운드에서 `INFO_D6_NOT_OPENED:<leg>`, 연속 2회면 `WARN_PROBE_RETRACT_NOT_OPENED:<leg>`를 냅니다.
  - (i-b) 위치 목표는 저속 1 mm/s이고, 상한은 `need_ub + 깊이 + 0.2 mm`입니다. `need_ub`는 추적기와 같은 함수 `retract_need_upper_bound`(추출만 했고 수치는 같음)를 씁니다.
  - 기록 `probe_d6_record`
- **Y7-3 P1 보완**: `check_open_delay.CheckOpenGateP1Patch`, `harness_hydraulics`, `v5_options.P1PatchSetting`
  - (a) 충전 진값과 중립 가둠, (c) 체적 분리(β는 P1 전용), (d) 시드 경로 제거, k_ext b0를 넣었습니다.
  - 옛 P1 플랜트에는 기록 키 `stale_seed_release`만 더했습니다(jsonl의 `hydraulics_record`와 T4h meta, 명령 불변).
  - 설정은 `VBM`·`LSM1~4`·`VBM0`·`VBKM`·`VBKM0`과 감도 10개(판정 slow/fast/c005/c04, 기록 b069/b16/h05/h15/d05/d15)입니다.
- **Y7-4 ③ rev 7**: revision 7은 rev 6과 같은 상계입니다. 태그는 `final_C4G2_P3X`, `rule_revision` 7입니다. `jp3_rev7_condition.py`는 조건 행을 판별하고 `plant_seed_artifact`로 분류하며, 조건 행이 0이면 not_judgeable로 둡니다. HOLD_REVISIONS를 (5,6,7)로 바꿨습니다(중복 상수 3곳과 t4h_replay 포함).
- **Y7-5 `jp3_ed7_rules.py`**
  - `j7_items_ed7`: (이름, 다리, 사유)로 비교하고, 사유가 없으면 `unknown`, 주기 차는 기록으로 남깁니다. 기존 `j7_items`는 그대로 뒀습니다.
  - 교착 서명(조건 1 고정), 감도 대표 4·기록 6 분리, (설정, 행) 군집 규칙 k=4, U832
- **Y7-6 `ed7_key_lists.py`, `ed7_probe.py`**
  - probe 654줄 = 15키 × 6플랜트 × 7팔(630) + D 12키 × {M, Mslow} × a2(24). D 키는 git blob(sha `a995abff…`)과 대조합니다.
  - 감도 460줄 중 판정 184줄입니다.
  - G1 풀은 192군집이고, V0 섞인 3군집과 후보 없는 19군집을 빼면 171줄입니다. U832 3줄을 빼면 판정 168줄입니다. G1 키 파일은 `--g1-seed`(봉인 때 정함)가 있어야 씁니다.
  - run_v5 배치: `ed7_j9_main`(388줄), `ed7_t8`(44), `ed7_cases`(10), `ed7_keys`. `ed7_keys`의 봉인 sha 목록은 봉인 전까지 비어 있어서 지금은 모든 키 파일을 거부합니다.
- **Y7-7 `jp3_12b_plan.py --edition 7`**: seed 50~53과 예약 규칙은 그대로입니다. `--scan-required <root>`(반복, 1개 이상 필수)로 모든 형식을 훑습니다(.json/.jsonl/.txt/.csv/.ps1/.py, .npz 문자열 배열 포함). 팔은 VBKM0/VBKM입니다.

### 4. 시험
- **P7-0** (`test_ed7_harness.py`, dynamics-dev 하위 프로세스): 다음 7개 줄의 명령 해시가 79495405 실행 출력과 **같습니다**.
  - VBL R12/S5, LSL1 R12, LSL4 S5, VBLc04 S5, VBLv15 R12, VBL0 S5
  - 판 7 키는 없고 `stale_seed_release`만 있습니다.
  - V0/VB/VBJ 등은 판 6 P6-0 시험으로 통과했습니다.
- **VBM 쪽 결과**
  - VBM 신원, 기록, 배열을 확인했습니다.
  - P7-1 미리보기: VBM R12 해시와 VBM0 R12 해시가 같습니다.
  - probe 2줄 실행과 조건 도구를 다른 폴더에서 끝까지 돌렸습니다.
- **시험 결과 표**

| 시험 | 범위 | 결과 |
|---|---|---|
| ed7 시험 (a6fc3dd5) | `test_ed7_units`, `test_ed7_harness` | 51 통과, 0 skip |
| 저장 자료 시험 (`worktree_tests.py`) | two_pressure 6개, `test_ed6_lock_start_b`, `test_jp3_rev6` | 343 통과, **skip 0**. 도구 종료 1은 skip 메시지 문자열에 대한 경고 14건뿐 |
| 커밋 직전 관련 98개 파일 (Chrono-dev) | 판 6 하네스 시험 포함 | 2442 통과, 1 실패, 49 skip |

- 그 1 실패: `test_ed6_lock_start_b`의 ROD_FAULT_SETTINGS 튜플 단언입니다. 판 7 이름이 추가되어 생긴 것이라 커밋에서 시험을 고쳤습니다. 49 skip은 모두 위 저장 자료 시험으로 0이 됐습니다.
- **판 6 시험 문구 수정 2곳** (판 7 추가에 따른 것): `test_jp3_rev6`의 ROD_FAULT 튜플과 "(5, 6, 7)" 메시지
- **전체 suite(303파일)는 실행하지 않았습니다.** 아래 권고에 명령을 적었습니다.
- **ruff**: 새로 생긴 위반은 0입니다. 남은 E501 4건(`harness_hydraulics.py:21`, `run_v5.py` 924/929/933)은 기준 커밋에도 있던 것입니다.
- **codespell**: `ABL`(태그 이름, 기존)만 걸렸습니다.

### 5. 건식 실행
`dynamics-dev python.exe -I -B`로 worktree 루트에서 돌렸습니다. 새 명령이 모두 argparse에 실제로 닿았고, 실행 출력 파일은 만들지 않았습니다.
- `ed7_probe --list`(+`--workers 20 --mask 0x0FFFFFFF`): 654
- `--part d`: 24
- 잘못된 팔: 종료 2
- `ed7_j9_main` 388, `ed7_cases` 10, `ed7_t8`(`--p3-hash-source`) 44
- `ed7_keys`: 거부(봉인 전)
- 조건 도구: 입력 오류 종료 2

### 6. 근거
`C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\tool_a6fc3dd5\`
- keys 3개, dry_run, 시험 로그와 JUnit, worktree_tests 보고, P7-0 기준 해시 추출 스크립트, `manifest.json`
- `SHA256SUMS`: 14항목, sha `4e87e43e…`

### 확인 필요
1. **래치**: 반대 부호 트리거가 3번째가 되는 순간 래치를 걸고, 그 발사는 하지 않게 구현했습니다.
2. **보호**: 막힌 주기는 매번 세고, 사건 `INFO_LSB_BLIND_PROTECT`는 구간당 한 번만 냅니다. `WARN_PROBE_RETRACT_NOT_OPENED`는 다리당 한 번(`_event_once`), `INFO_D6_NOT_OPENED`는 라운드마다 냅니다.
3. **조건 3의 완료 플래그가 없는 주기**(LEVEL 완료를 평가하지 않은 주기)는 "열림"으로 봅니다. A(i)-b의 `u=0`/부호 끝은 그 주기의 요청 명령으로 판정합니다(판 6 A(i)와 같은 출처).
4. **(i-b) 적용 범위**: 신장 먼저 하는 사다리꼴 탐침에만 적용했습니다. 헤드 판독이 없으면 저속 구간은 없습니다.
   - **Q7-C2**: 역순 탐침(수축 먼저)의 K1 중간 읽기는 첫 이동 명령의 절반 시점입니다. 사행정 안이라 피스톤이 서 있을 수 있습니다. 판정은 control-expert가 해야 합니다.
5. **(a) 구현 선택** (hydraulics 확인 권고)
   - void를 먼저 채웁니다.
   - 중립 배수는 기존 법칙을 쓰되, 갇힌 몫을 바닥으로 둡니다.
   - 신장 쪽 로드 체크 열림 판정에는 갇힌 상승을 넣지 않은 p_r을 씁니다.
   - Δp_fill은 해제 때와 새 잠김마다 지웁니다.
6. **probe 키 15개 해석**
   - 반사실 C의 FR-Fs0 위상은 (가)의 FR o0.0/o0.05와 겹친다고 봤습니다. RL-Fs0은 o0.0입니다.
   - **S4 위상 e0.002는 제가 골랐습니다**(d2_dwells에서 체류 행이 가장 많은 위상).
7. **U832 3군집**: 판 6 `records_after_stop/A_a1/grid_judge.json`의 실제 실패 3개(bottom-FL-Fs2, FR-Fs2, FR-Fs4, RE1bF-ready)로 정했습니다. 명세의 약식 표기에 들어가는 bottom-FL-Fs4는 판정에 넣었습니다.
8. **`JP3_SPEC_EDITION_V7 = "85ce6e2a"`는 임시값**(초안 개정 2)입니다. 봉인 sha로 바꿔야 합니다. 신원값이라 명령에는 영향이 없습니다.
9. **12b 블라인드 열거 위험**: `jp3_12b_plan`(판 6과 같은 방식)은 스캔 루트(06_analysis)를 rglob하고, 제외 파일의 **경로를 selection.json에 적습니다**. 블라인드 경로 "열거 금지" 규칙과 충돌할 수 있습니다. 그래서 실제 06_analysis 스캔은 돌리지 않았고, 합성 자료 시험만 했습니다.
10. **옛 플랜트 기록 변경**: VBL 등의 T4h meta와 jsonl에 `stale_seed_release`가 새로 들어갑니다. 명령은 같지만, T4h 파일 sha를 비교하는 도구가 있으면 영향이 있습니다.

### 메인 세션 권고
1. **probe** (봉인 전, 654줄)
   ```
   cd C:\workspace\outrigger_control\.claude\worktrees\ed7-impl
   $env:MKL_THREADING_LAYER='TBB'
   & C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B 04_scripts/04_hydraulic/coupled/ed7_probe.py --out C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\a6fc3dd5\ed7_probe_a1\ed7_probe.jsonl --workers 20 --mask 0x0FFFFFFF
   ```
   - 비용: 한가할 때 1줄 74 s를 쟀습니다. 부하가 있으면 약 150 s로 봅니다. 그래서 약 49,000~98,000 CPU-s(14~27 CPU-h)이고, 20 worker면 약 45~85분입니다. compute-scheduler-expert 배치표를 먼저 받아 주십시오.
   - 진행 파일: `ed7_probe.progress.json`
   - 끝나면 `jp3_rev7_condition.py --rows <위 jsonl> --out <...>`로 ③ 조건 행 수와 P7-8을 확인합니다.
2. **전체 단위 suite**: 판 6 `full_suite_ed6.ps1` 방식으로 base와 run 양쪽을 돌립니다(수 시간 예상).
3. **봉인 때 할 일**
   - G1 seed로 `ed7_key_lists.py --only confirm_g1_grid171.json --g1-seed <seed>` 실행
   - `ED7_KEY_FILE_SHA256`과 `JP3_SPEC_EDITION_V7` 고정
   - 12b `--edition 7 --scan-required …` 실행(9번 블라인드 문제를 먼저 결정)

### 위임 필요 / 남은 일
- **python-expert(다음 작업)**
  - probe 몫과 조건 3 채택 판정 도구(명세 4.2 규칙). 봉인 전에 필요합니다.
  - 봉인 뒤 판정 CLI 연결: J7 새 비교·교착 서명·감도 분리·G1, 12b VBKM 판정
- **control-expert**: Q7-C2, 확인 필요 1~3
- **hydraulics-expert**: 확인 필요 5

참고: worktree에 numba·바이트코드 캐시 `__pycache__`가 생겼습니다. git ignore 대상이고 트리는 깨끗합니다. scratchpad `python-ed7`는 지웠습니다.
