## 판 7 검토 반영 보고 (a6fc3dd5 → 6bfb2560, ed7-impl)

의존성 점검: 모두 있음. 사용한 스킬: 없음.

### 요약
- 결정된 9개 항목을 모두 반영했고, ed7-impl 브랜치에 커밋 **6bfb2560**(부모 a6fc3dd5) 하나로 올렸습니다. 병합·push는 하지 않았고 worktree는 깨끗합니다.
- 수정한 파일은 모두 기존 파일이라 줄바꿈은 각 파일의 기존 설정을 따랐습니다. 새로 만든 저장소 파일은 없습니다.
- probe·본 실행은 돌리지 않았습니다. 판정값도 만들지 않았습니다.
- 명세(`jp3_remedy_spec_v7.md`)는 열지도 고치지도 않았습니다. 지시문의 결정과 세 검토 원문만 따랐습니다.

### 반영 내용 (항목 번호는 지시문 기준)
1. **유압 1-4 (`check_open_delay.CheckOpenGateP1Patch`)**
   - 잠긴 다리가 신장하다가 `rod_released`가 거짓→참이 되는 순간 `fill_rise_Pa[i] = 0`으로 둡니다(`_extend_step` 재정의).
   - 지운 값이 0보다 클 때만 `rod_check_clear_log`에 `(t_s, leg, cleared_fill_rise_Pa)` 한 줄을 남깁니다(상한 600줄).
   - `summary()`에 `rod_check_clear_count`, `_log`, `_log_columns`, `_log_truncated`를 넣었습니다.
   - 수축 열림 해제는 그대로 base + Δp_fill에서 출발합니다. 해제·새 잠김 때 지우는 동작도 그대로입니다.
2. **유압 1-1**
   - 잠긴 다리가 수축 충전 중이면 `void_fill_m = max(void_fill_m, min(x, void))`를 유지합니다.
   - 중립 바닥은 `max(상승 기반 갇힌 몫, min(void_fill_m, 현재 void))`입니다(`_trapped_floor_m`).
   - `clear_fill`에서 `void_fill_m`도 함께 0으로 지웁니다. 로드 진값은 바꾸지 않았습니다.
3. **유압 2**: `v5_options._check_p1_patch`가 P4(`rod_reading_truth`)가 꺼져 있으면 거부합니다(`ValueError "needs P4"`).
4. **유압 3**
   - 옛 P1 플랜트의 `stale_seed_release`에서 `releases_with_seed`와 `stale_releases`를 이제 **전체 계수**로 셉니다(`stale_seed_counts`). 여기에 `log_rows`와 `log_truncated`를 더했습니다.
   - `jp3_rev7_condition.release_seed_class`는 잘린 기록의 마지막 줄보다 뒤에 오는 침범을 `no_seed`가 아니라 `seed_log_truncated`로 분류합니다. 기록 줄에만 해당하고 판정 상태는 바꾸지 않습니다.
5. **통계 3절 ① (`ed7_key_lists.py`)**
   - G1 줄마다 `counted_for_k`(U832 3군집만 false)와 `judged_fault_jp3`(171줄 모두 true)를 둡니다. 단일 `judged` 플래그는 없앴습니다.
   - 분모는 플래그별로 따로 셉니다: `k_counted_lines` 168, `fault_jp3_judged_lines` 171, `expected_j_p3_judged_rows`(171줄 기준). `g1_pool_ed7.json`에도 같은 두 분모와 `line_flags` 설명이 들어갑니다.
   - bottom-FL-Fs4-RE1bF-ready는 판정에 그대로 둡니다(U832 아님).
6. **제어 4 (Q7-C2, 기록만, 명령 불변)**
   - `ProbeResult.k1_mid_opened`: 역순 탐침에서 K1 중간 읽기까지의 수축 읽기로 `retract_witness_m ≥ s_w,D6`인지입니다. 신장 먼저인 탐침은 None입니다.
   - `d6_witness.rounds` 행에 `is_reversed`와 `k1_mid_opened`를 더했습니다.
   - `d6_witness.reversed_rounds`는 `{"not_substituted": [다리별], "substituted": [다리별]}`입니다. 대체 여부는 라운드가 끝날 때의 로드 상태(FALLBACK)로 판단합니다.
   - 역순 탐침에는 (i-b)를 적용하지 않습니다(기존 동작 그대로이고 시험으로 확인).
7. **제어 3**: A(i)-b 발사 기록 `shots[].completion_known`과 다리별 `triggers_completion_unknown`을 더했습니다.
8. **인용·주석 정정**
   - Q7-C1의 relax `max_twist_N` 인용은 c2.py 1979(클래스 기본값)가 아니라 프리셋 `R8_TWIST_RELAX_MAX_TWIST_N`(c2.py 1598, `with_10hz_d1`에서 2909에 적용)입니다. `lock_start_b.py`의 두 docstring에도 그렇게 적었습니다.
   - `ed7_probe.py` S4 근거는 지시 문안대로 고쳤습니다. 키 e0.002는 유지했습니다.
9. **12b 블라인드 (`jp3_12b_plan.py`)**
   - 상수 `ED7_BLIND_PREFIXES` 3개(지시문의 블라인드 경로)를 경로 성분 패턴으로 둡니다(fnmatch, 대소문자 무시, `os.path.abspath`의 성분 기준, resolve 없음).
   - edition 7에서는 모든 탐색(`--scan-root`, `--scan-extra`, `--scan-required`, `--scan-exclude` 목록)을 `os.scandir`로 직접 돌면서, 이름으로 먼저 걸러 냅니다. 블라인드 항목은 열거·stat·읽기 전에 빠지고 그 아래로 들어가지 않습니다.
   - 루트나 `--scan-keys-file`이 블라인드 안이면 경로를 적지 않고 종료 2로 멈춥니다.
   - `selection.json`에는 `blind_prefixes_applied: 3`과 안내 문구만 들어갑니다.
   - edition 5·6은 기존 `rglob` 경로를 그대로 씁니다.

### 검증
- **P7-0** (`test_ed7_harness`): 옛 플랜트 7줄의 명령 해시가 79495405 실행 출력과 같습니다. `stale_seed_release` 키 집합 단언은 새 키(`log_rows`, `log_truncated`)를 포함하도록 고쳤고, `releases_with_seed == log_rows`(잘림 없음)도 확인합니다.
- **P7-1 미리보기**: VBM R12와 VBM0 R12의 해시가 같습니다.
- **ed7 시험** (`test_ed7_units` + `test_ed7_harness`, Chrono-dev, 하네스는 dynamics-dev): 61 통과, skip 0.
  - 새 단위 시험은 다음을 확인합니다.
    - 탐침 C 꼴: 갇힌 20.48 bar 뒤 신장하면 `rod_released` 시점에 0이 되고 한 줄이 기록됩니다. 헤드는 그 뒤에 열립니다. 헤드 열림까지 걸린 시간이 상승이 없던 게이트와 같습니다.
    - 플랜트 자신의 `_start_release`로 본 해제 출발: lag 출발 = base이고, M2 `ReleaseStart`가 상승 없던 경우와 같습니다.
    - 수축 해제는 여전히 base + Δp_fill에서 출발합니다.
    - 탐침 B 꼴: void 1 mm에 0.5 mm를 채운 뒤 중립 3 s 동안 x가 0.5 mm로 유지되고, void가 0.3 mm로 줄면 바닥도 따라 줄어듭니다.
    - P4가 꺼져 있으면 거부합니다.
    - 기록 잘림: 계수, `log_truncated`, `seed_log_truncated` 분류.
    - G1 두 분모 168/171과 J-P3 기대 행 수.
    - witness 행 필드와 대체/비대체 역순 라운드 수, 역순 탐침의 `k1_mid_opened` 참/거짓/None, `completion_known`.
    - 12b 블라인드: 블라인드 경로에 `os.scandir`, `os.stat`, `Path.read_bytes`가 닿으면 실패하도록 감싼 합성 트리입니다. 블라인드 파일에 충돌 키(s50)를 넣었는데 seed가 50~53 그대로이고, 출력 어디에도 이름이 없습니다. 블라인드 루트는 거부됩니다. edition 6은 여전히 그 파일을 읽습니다(60).
- **관련 시험 23파일** (Chrono-dev, -n 8): 905 통과, 18 skip.
  - skip은 모두 저장 자료 관련입니다. 그중 16개는 아래 두 실행에서 0이 됐습니다.
  - 남은 2개는 `test_x10_rod_fault`의 `X10_BASE_ROOT` 미설정이고, 이번 변경과 무관하게 설계상 나는 skip입니다.
- **`tools\verif\worktree_tests.py`** (6bfb2560): two_pressure 저장 자료 6파일, `test_ed6_lock_start_b`, `test_jp3_rev6`에서 343 통과, **skip 0**. 원본 불변 True입니다. 도구 종료 1은 skip 메시지 문자열 경고 14건뿐입니다(전과 같음).
- **`test_v5_setting_records`** (`OUTRIGGER_RECORDS_ROOT` = 메인 checkout): 16 통과, skip 0.
- **VBM 쪽 명령 변화**: a6fc3dd5 트리(git archive)와 비교했습니다. VBM R12, VBM0 R12, VBMslow S5, VBMslow R12 네 줄 모두 해시가 같습니다.
  - 이 네 줄에서는 `rod_check_clear_count` 0이라 1-4 경로가 발동하지 않았습니다. 해제는 모두 수축 열림 경로였습니다.
  - 바뀐 VBM 줄은 이 미리보기 범위에서 없습니다. probe·본 실행의 다른 줄에서는 바뀔 수 있습니다.
- **edition 5·6 출력 불변**: a6fc3dd5와 6bfb2560의 `jp3_12b_plan`을 같은 합성 트리에서 돌렸습니다. plan·key 파일은 바이트가 같고, `selection.json`도 noise 경로만 빼면 같습니다.
- **건식** (dynamics-dev, worktree 루트):
  - `ed7_probe --list` 654, `--part d` 24, 잘못된 팔 종료 2
  - `ed7_j9_main` 388, `ed7_cases` 10, `ed7_t8` 44, `ed7_keys`는 봉인 전이라 거부
  - 조건 도구는 입력 오류로 종료 2
  - 12b `--edition 7` 합성 루트는 seed 50~53, 블라인드 이름 0개
  - 블라인드 `--scan-required`는 종료 2
- **키 목록**: probe 654줄과 sens 460줄은 a6fc3dd5와 줄 내용이 같습니다. `g1_pool`은 192 / 섞인 3 / 후보 없음 19 / 적격 171 / U832 3 / k 168 / FAULT·J-P3 171입니다.
- **ruff**: 새 위반 0. 남은 E501 `harness_hydraulics.py:21`은 기존 것입니다.
- **codespell**: 기존 `ABL` 2건뿐입니다.
- **실행하지 않은 것**: 전체 suite(303파일), mypy(프로젝트 설정 없음).

### 근거 폴더
`C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\tool_6bfb2560\`
- 내용: `keys\`(3), `dry_run\`(script, json, 합성 12b selection), `tests\`(ed7·관련·setting_records JUnit과 로그, worktree_tests 보고·JUnit), `checks\`(VBM 비교, 경로 계수, ed5/6 12b 바이트 비교 스크립트와 결과), `manifest.json`
- `SHA256SUMS`: 23항목, sha `e9ba6030…`(`baseline_check.py write-sums --recursive`)
- scratchpad `python-ed7fix`는 지웠습니다.

### 동작 변경·공개 API 변경
- **VBM 계열 플랜트** (1·2): 신장 로드 체크가 열리면 Δp_fill이 0이 되고, 부분 void 충전이 중립에서 남습니다. 옛 플랜트와 판 6 설정은 영향이 없습니다(P7-0).
- **기록 키**
  - 옛 P1 플랜트 `stale_seed_release`에 `log_rows`와 `log_truncated`가 더해졌습니다. `releases_with_seed`의 의미도 "기록 줄 수"에서 "전체 계수"로 바뀌었습니다(잘림이 없으면 값은 같음).
  - VBM `line_fill_gate` 요약에 `rod_check_clear_*`가 더해졌습니다.
  - 그 밖에 D6 witness 행과 `reversed_rounds`, A(i)-b 발사의 `completion_known`, `triggers_completion_unknown`, 조건 도구의 분류 `seed_log_truncated`가 새로 생겼습니다.
- **G1 키 파일 스키마**: 줄의 `judged` → `counted_for_k` / `judged_fault_jp3`, 문서의 `judged_lines` → `k_counted_lines` / `fault_jp3_judged_lines`. 봉인 뒤 판정 CLI는 이 이름을 읽어야 합니다. 아직 소비하는 코드는 없습니다.
- **P1 보완 옵션**: P4 없이 `p1_patch`를 쓰면 이제 거부됩니다.

### 확인 필요
1. **(유압)** 로드 체크가 열릴 때 Δp_fill만 지우고 `void_fill_m`은 남겨 두었습니다. 바닥압의 로드 챔버는 B 라인에서 기름을 받을 뿐 잃지 않는다고 봤기 때문입니다. 해제나 새 잠김 때는 함께 지웁니다. hydraulics-expert의 확인을 권합니다.
2. **(제어)** 대체/비대체는 라운드가 끝날 때의 로드 상태로 셉니다. `completion_known`은 실제로 발사한 트리거에만 기록하고, 보호·래치로 막힌 트리거에는 기록하지 않습니다.
3. **검증 공백**: "M2 순 이동 = 상승 없을 때와 같음"은 플랜트 `_start_release`가 받는 입력(lag 출발, `ReleaseStart`)이 같다는 것으로 확인했습니다. 전체 플랜트 루프에서 1-4 경로가 실제로 발동하는 줄은 미리보기 4줄 안에 없었습니다.
4. `JP3_SPEC_EDITION_V7 = "85ce6e2a"`는 여전히 임시값입니다(봉인 때 교체).

### 공개 (블라인드 절차)
- worktree 루트를 대상으로 Grep을 두 번 블라인드 제외 glob 없이 돌렸습니다.
  - 토큰(`fill_rise|clear_fill|…`) 내용 검색 1회: 출력이 커서 파일로 저장됐고, 미리보기만 봤습니다.
  - `*.py` glob 검색 1회.
- worktree에는 추적된 `06_analysis`도 있으므로 순회는 일어났습니다. 화면에 나온 결과에 블라인드 경로는 없었습니다.
- 그 뒤 검색은 `03_src`, `04_scripts`, `05_tests`와 개별 파일로만 했습니다. 실제 06_analysis 스캔(12b)은 하지 않았고, 합성 트리만 썼습니다.

### 메인 세션 권고
1. **probe** (봉인 전, 654줄): 지금은 커밋이 바뀌었으므로 출력 폴더를 새 커밋 이름으로 둘 것을 권합니다.
   ```
   cd C:\workspace\outrigger_control\.claude\worktrees\ed7-impl
   $env:MKL_THREADING_LAYER='TBB'
   & C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B 04_scripts/04_hydraulic/coupled/ed7_probe.py --out C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\6bfb2560\ed7_probe_a1\ed7_probe.jsonl --workers 20 --mask 0x0FFFFFFF
   ```
   - 비용(앞 측정 그대로): 한가할 때 1줄 74 s, 부하가 있으면 약 150 s입니다. 합계 약 14~27 CPU-h, 20 worker면 약 45~85분입니다. compute-scheduler-expert 배치표를 먼저 받아 주십시오.
   - 진행 파일은 `ed7_probe.progress.json`입니다. 끝나면 `jp3_rev7_condition.py --rows <jsonl> --out <...>`를 돌립니다.
2. **전체 단위 suite**: 판 6 `full_suite_ed6.ps1` 방식으로 base·run 양쪽을 돌립니다(수 시간 예상).
3. **봉인 때**
   - G1 seed로 `ed7_key_lists.py --only confirm_g1_grid171.json --g1-seed <seed>`
   - `ED7_KEY_FILE_SHA256`과 `JP3_SPEC_EDITION_V7` 고정
   - 12b는 `--edition 7 --scan-required …`로 실제 실행합니다(이제 블라인드 접두를 탐색하지 않음).

### 위임 필요
- **control-expert (명세 개정 3)**: 다음을 반영하도록 넘겨 주십시오.
  - 1-4 지우기 시점(로드 체크 파일럿 열림)과 그 기록 키
  - 1-1 void 몫을 가두는 규칙
  - P4 필수
  - G1 두 플래그와 분모 이름
  - D6 witness 새 기록 필드와 `reversed_rounds`, `completion_known`
  - 12b edition 7의 블라인드 접두 규칙(출력에는 "제외 접두 N개 적용"만 남음)
  - 옛 플랜트 기록 키 변경(`log_rows`, `log_truncated`, 전체 계수)
- **hydraulics-expert**: 확인 필요 1.
- **python-expert (다음 작업, 봉인 뒤)**: 판정 CLI가 G1의 `counted_for_k` / `judged_fault_jp3`를 읽게 연결합니다. 감도 4설정 합산 CLI(통계 위임 (2))와 U832 기록 표(통계 위임 (3))는 이번 범위 밖이라 남겨 두었습니다.

### 메모리 반영안
- `C:\Users\jinbeom\.claude\agent-memory\python-expert\tool_blind_prefix_walk.md`(새 파일, 색인 1줄): rglob은 블라인드 폴더 안까지 열거·stat한다. scandir로 이름부터 걸러 내고, 접근하면 실패하도록 감싼 시험을 둔다. Grep은 `03_src`, `04_scripts`, `05_tests`로 좁힌다.
