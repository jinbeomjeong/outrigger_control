# 436.9 판 8 명시 twin V0 스모크 보고 (재감사 K-7 선택 스모크)

## 요약
- **세 줄 모두 NB-1 전제를 만족했습니다.** RE1bF·FS24·G4 각 1개이며 모두 G′ 슬롯이 아닙니다.
  - 오류 없음.
  - `controller_tag` = `final_C4G2_LAS_K1`.
  - `V0_ABSENT_KEYS` 10개 가운데 값이 있는 키 0개.
  - `hydraulic_options`·`hydraulics_record`는 null.
  - `lock_window_alignment`·`t4h_file` 없음.
  - `event_output.reapproach_starts` 키 있음.
  - 사건 목록 길이: RE1bF 9, FS24 1, G4 0. 모두 200 절단 아님.
- **T8″ 판정 결과**(T8″ `5955f25b`, ed8-judge2 코드, 스텁 없음, Chrono-dev)
  - `v0_identity_problems`: 세 줄 모두 문제 없음.
  - `aa_pair_verdict`: 같은 (row, group)인 줄이 RE1bF와 G4 두 줄이어서 짝 1개만 돌렸습니다. 예외 없음, `j11_state` = "입력 없음", 결과는 bool. bool 값은 출력하지 않았습니다.
    - 두 줄의 group(`G4|level|leg|fs`)이 같았지만 사건은 서로 다릅니다. 즉 이 짝은 G′ A/A처럼 같은 사건끼리 짝지은 것이 아니라 사건이 다른 짝이며, 판정 경로가 돌아가는지만 본 것입니다.
    - FS24 줄은 group이 달라 짝을 만들지 않았습니다.
  - 형상: `effective_shape`의 출처는 RE1bF가 twin, FS24·G4는 RE1bF 기본값이었습니다. 기본값 (0.030, 0.05)에 대한 `shape_severity`는 셋 다 "same"이었습니다.

## 실행 내용
- **checkout**: 새 detached worktree `C:\workspace\outrigger_control\.claude\worktrees\ed8-smoke2`(HEAD C8 `56849248…`)를 만들었습니다. 실행 정체성은 시작·끝 모두 head C8, clean True였습니다.
- **job**(`make_jobs.py`)
  - 저장 격자 조건 `ed6_design\keys\confirm_b_grid192.json`(sha 4e80e69b 확인)의 job 가운데, twin에 `event`·`timing`이 있고 offset 0.0인 본 조건에서 사건별로 첫 job을 골랐습니다(정렬 기준은 job 키). 설정은 V0입니다.
  - RE1bF에는 `depth_m` 0.030·`ramp_s` 0.05를 명시했습니다.
  - **held-out 단언**(실행 전, sha a18b5818 확인)
    - 5단계 job 1356개(각 슬롯의 `v0_pair` + `aa_order[:3]`)에 셋 다 없습니다.
    - 키 파일 전체 job 2751개(VBN job, 모든 aa 후보 포함)에도 없습니다.
    - 지시문의 "1356 job"은 5단계 실행 job 수입니다. 키 파일의 모든 V0 job(`aa_order` 전체)은 2412개라 처음 단언이 실패했고, 두 집합 모두로 검사하도록 고쳤습니다.
- **실행**: 지난 스모크와 같은 `run_smoke.py`(sha 같은 사본)를 썼습니다.
  - dynamics-dev `python.exe -I -B`, cwd는 ed8-smoke2.
  - 스레드 변수 1과 TBB, `OUTRIGGER_RECORDS_ROOT=main`, `NUMBA_CACHE_DIR`은 runner 폴더 하위.
  - **mask 0x000C만 사용했습니다**(P코어 1개, 작업자 3개가 그 두 논리 CPU를 나눠 씀). 시작 전 status.py에서 유효 예약 0, 고정 0이었습니다.
  - 세 줄 모두 final ready, 각 32~37 s.
  - 로그에 `WARN_ROD_PRESSURE_FALLBACK` 이벤트 이름이 보였습니다. 줄에 `lock_window_alignment` 블록은 없습니다.
- **확인**: `check_smoke.py`가 키와 종류만 `smoke_check.json`에 썼습니다.

## 출력 (메인이 근거 폴더로 옮길 것)
- 위치: `C:\Users\jinbeom\.claude\runners\outrigger-ed8\smoke_v0twin_56849248\`
- `SHA256SUMS`(8항목, sha `0e84a83ecc405dd262ea1b1c5b0b68c12ac3a7186738df8cd5bd5278b2076456`)가 덮는 파일:
  - 실행 결과: `v0_smoke.jsonl`(3줄), `v0_smoke.identity.json`, `jobs.json`, `run_smoke.log`, `smoke_check.json`
  - 스크립트: `make_jobs.py`, `run_smoke.py`, `check_smoke.py`
- numba 캐시는 지웠습니다.

## 정리 확인
- ed8-smoke2의 `03_src`·`04_scripts`·`05_tests`에서 `.nbi`·`.nbc`·`__pycache__` 0개, `status --porcelain --ignored` 비어 있음.
  - 그 뒤 `git worktree remove`로 지웠고, 폴더가 없어진 것을 확인했습니다.
- ed8-impl과 ed8-judge2의 `status --porcelain --ignored`도 둘 다 비어 있습니다.

## 확인 필요
- **`effective_shape`가 FS24·G4 twin에도 RE1bF 기본값 (0.030, 0.05)을 줍니다.** T8″ 구현은 "twin에 형상 필드가 없으면 RE1bF 기본값"이라 사건 이름을 보지 않습니다.
  - G′ 형상 기록은 같은 슬롯(같은 사건)의 짝끼리만 비교하므로 판정·기록 결과는 바뀌지 않습니다. 형상 필드는 (나) RE1bF 슬롯에만 있습니다.
  - 다만 "FS24·G4의 실효 형상"으로 읽히면 뜻이 틀립니다. 사건별 기본값(`r67.EVENTS[event]`)을 쓸지 control-expert 확인이 필요합니다. 결정문 3.3 문면은 RE1bF 기본값만 적고 있습니다.

## 공개 (실제 행위)
- 블라인드 경로는 열지 않았습니다.
- Grep·Glob은 쓰지 않았습니다. 파일은 스크립트 안에서 경로를 직접 지정했습니다: 격자 키, held-out 키, 실행 출력.
- held-out 키와 격자 키는 job 키만 비교했고, 판정 값은 출력하지 않았습니다.
- Bash는 git worktree add·remove 두 번에 썼고, 파이프는 없습니다(`> /dev/null` 리디렉션만 씀).
- 프로세스는 종료하지 않았습니다. scratchpad는 쓰지 않았습니다.

사용한 스킬: 없음
