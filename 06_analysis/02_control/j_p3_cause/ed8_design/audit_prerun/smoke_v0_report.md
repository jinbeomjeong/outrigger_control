# 436.9 판 8 C8 V0 한 줄 스모크 보고 (재감사 M′-3, control NB-1 결정 6.1)

## 요약
C8의 실제 생산자 V0 줄 2개가 NB-1 해석의 전제를 모두 만족했습니다. T8″ 코드로 스텁 없이 돌린 정체성 검사와 A/A 판정도 예외나 판정 불가 없이 끝났습니다.

- **두 줄 모두 전제를 만족**
  - 오류 없음, `controller_tag`가 있고 `final_C4G2_LAS_K1`과 같음.
  - `V0_ABSENT_KEYS` 10개 가운데 값이 있는 키 0개.
  - `hydraulic_options`·`hydraulics_record`는 null.
  - `lock_window_alignment` 없음, `t4h_file` 없음.
  - `event_output`과 `event_output.reapproach_starts` 키는 있음.
- **T8″ 판정 결과**(T8″ `5955f25b`, ed8-judge2 코드, 스텁 없음, Chrono-dev)
  - 두 줄의 `v0_identity_problems`: 둘 다 문제 없음.
  - `aa_pair_verdict`(짝 1개): 예외 없음, `j11_state` = "입력 없음", 판정 결과는 bool. bool 값은 출력하지 않았습니다.
  - A/A 판정의 판정 불가 항목 이름: 없음. 본인 설정으로 기록한 항목은 J11 하나입니다.
  - 조건 V0의 기준 통과 판정도 bool로 계산됐습니다.

## 실행 내용
- **checkout**: 새 detached worktree `C:\workspace\outrigger_control\.claude\worktrees\ed8-smoke`(HEAD `56849248371b4916e2fe683265e7abffdd6fb8d7`)를 만들었습니다. 잠긴 ed8-impl은 쓰지 않았습니다.
- **job 선택**: `select_jobs.py`가 저장 `main.jsonl`(sha 9ad74990)과 봉인 held-out 키(sha a18b5818)를 확인한 뒤 job 키만 읽었습니다.
  - G′ 조건 V0와 **같은 꼴의 job은 저장 main.jsonl에 없습니다.**
    - G′ 조건 V0 twin 필드: `event`, `fs_kN`, `leg`, `level`, `timing`.
    - 저장 R12 V0 twin 필드: `fs_kN`, `leg`, `level`(28줄). 꼴은 `job_forms.py`로 키만 셌습니다.
  - 그래서 저장된 R12 twin V0 가운데, 정렬했을 때 첫 (row, group)에서 `offset_s`만 다른 두 job을 골랐습니다.
    - R12, twin `{fs_kN, leg, level}`, offset 0.0과 0.05.
    - 이 꼴의 twin은 사건 이름이 없어 사례 기본값을 따릅니다. 사례 R12의 기본 사건은 G4입니다.
- **실행** `run_smoke.py`(dynamics-dev `python.exe -I -B`, cwd는 ed8-smoke)
  - 쓴 경로: C8 코드의 `run_v5.run_one`, `_run_pool`(spawn, 작업자당 작업 1개), `_write_identity`.
  - 환경: 스레드 변수 1과 TBB(run steps와 같음), `OUTRIGGER_RECORDS_ROOT=main`, `NUMBA_CACHE_DIR`은 runner 폴더 하위.
  - mask `0x000C`(P코어 1개, 논리 2개). 시작 전 status.py에서 유효 예약 0, 고정 0이었습니다.
  - 두 줄 모두 final ready, 각 약 27 s.
  - 실행 정체성은 시작·끝 모두 head C8, clean True였습니다.
  - 관찰: 실행 로그에 `WARN_ROD_PRESSURE_FALLBACK` 이벤트 이름이 한 줄 찍혔습니다. 줄에 `lock_window_alignment` 블록은 없으므로 J11은 "입력 없음"으로 기록됐고, 결정문의 해석대로입니다.
- **확인** `check_smoke.py`(Chrono-dev, ed8-judge2 코드 import): 키와 종류만 `smoke_check.json`에 썼고 판정 값은 쓰지 않았습니다.

## 출력 (메인이 근거 폴더로 옮길 것)
- 위치: `C:\Users\jinbeom\.claude\runners\outrigger-ed8\smoke_v0_56849248\`
- `SHA256SUMS`(9항목, sha `842cb9877b850f932bb54936fe3b59f1b599e8a2e36a5d5cb890e6beb2810e8a`)가 덮는 파일:
  - 실행 결과: `v0_smoke.jsonl`(2줄), `v0_smoke.identity.json`, `jobs.json`, `run_smoke.log`, `smoke_check.json`
  - 스크립트: `select_jobs.py`, `job_forms.py`, `run_smoke.py`, `check_smoke.py`
- numba 캐시 폴더 두 개는 지웠습니다(내가 만든 캐시).

## 정리 확인
- ed8-smoke의 `03_src`·`04_scripts`·`05_tests`에서 `.nbi`·`.nbc`·`__pycache__` 0개, `status --porcelain --ignored` 비어 있음.
  - 그 뒤 `git worktree remove .claude/worktrees/ed8-smoke`로 지웠고, 폴더가 없어진 것을 확인했습니다.
- ed8-impl과 ed8-judge2의 `status --porcelain --ignored`도 둘 다 비어 있습니다.

## 확인 필요
- 스모크 job은 G′ 조건 V0와 꼴이 다릅니다. twin에 `event`·`timing`이 없어 G4 기본 사건입니다. G′ 꼴(RE1bF 등 twin 사건 명시) 줄로 전제를 다시 확인하려면 저장되지 않은 job을 새로 돌려야 합니다. 이번 지시 범위("저장 main.jsonl의 job")를 벗어나므로 돌리지 않았습니다.

## 공개 (실제 행위)
- **규칙 위반 1회:** Grep 한 번의 path로 ed8-smoke **worktree 루트**를 썼습니다(glob으로 `run_v5.py`·`common.ps1` 두 파일만 지정, 결과 "No matches"). 블라인드 이름·건수는 나오지 않았습니다. 그 뒤로는 파일을 직접 지정했습니다.
- 블라인드 경로는 열지 않았습니다. 저장 main.jsonl과 held-out 키는 job 키·꼴만 읽었습니다.
- Bash는 git worktree add·remove 두 번에 썼고, 파이프는 없습니다(`> /dev/null` 리디렉션만 씀).
- 프로세스는 종료하지 않았습니다. scratchpad는 쓰지 않았고, 모든 파일은 runner 폴더에 있습니다.

사용한 스킬: 없음
