# 436.9 J-P3 보완 명세 판 5 정오 5 (2026-11-22, control-expert 문안)
- 대상
  - 원판 `jp3_remedy_spec_v5.md`(sha256 `fe6f58446c10a3e2fef88e90e2a9c8ccc7bb3843075e35ac9d4305ebf0b77257`)
  - 봉인된 정오 1~4: 정오 1 `4721352eba5d7c453da9b0977ec433e33a37766c2327b999f6d38c4d6d276cd9`, 정오 2 `639c54e98db2ca21ef67c6795ac0856675d8e938f63601a76c11fa6d49383790`, 정오 3 `7bab9217d6941545a80501144c08bf8c1a25278fffe889fa44d11f2dd1ca3608`, 정오 4 `4bc4ecddba1af599ebc3f76c824873bd88fc6be71d5e8748da37332fb73de706`
  - 원판과 정오 1~4는 고치지 않는다. 내용이 다르면 이 정오가 우선한다.
- 시점: 판정 단계(c 건식, 단계 (1)~(7)) 결과 전이다.
  - 실행 커밋 `ae9d0b2d`에서 P5-3을 처음 실행했을 때 시험 1건(`test_jp3_addendum_4a4.py::test_d1a_selection_of_the_stored_data`)이 실패해 멈췄다. 이 정오는 그 뒤에 썼다.
  - **공개: P5-3의 시험 집합은 이 실패를 본 뒤에 확정했다.** 집합은 실패한 시험 이름으로 고르지 않고, 아래 규칙으로 정했다.

## 5-1. P5-3의 시험 집합
- P5-3("단위 시험(7.2절) 전부 통과")의 집합은 다음 두 가지다.
  1. 판 5 구현 범위(`5632b618..실행 커밋`) 안에서 새로 생긴 `05_tests/unit/test_*.py` 전부(병합으로 들어온 파일 포함). 실행 커밋 `ae9d0b2d`에서는 다음 10개다.
     - `test_jp3_rev6.py`
     - `test_jp3_12b_tools.py`
     - `test_jp3_p51_compare.py`
     - `test_jp3_p5_fixed_values.py`
     - `test_jp3_ed5_erratum1.py`
     - `test_jp3_ed5_erratum2.py`
     - `test_jp3_ed5_prelaunch_fix.py`
     - `test_jp3_ckdrop.py`
     - `test_jp3_j9main.py`
     - `test_s9_batch_inputs_exit.py`
  2. 7.2 "X-10 비트 동일"·"고장 주입"을 담은 `test_x10_rod_fault.py`. `X10_BASE_ROOT`(X-10 이전 커밋 checkout)를 지정해 돌린다.
  3. 판 5 구현 범위(`df95158d..실행 커밋`)에서 기존 시험 파일에 새로 더해진 시험 함수. 실행 커밋 `ae9d0b2d`에서는 `test_jp3_prelaunch_audit2.py`의 `test_n1_t12_mismatch_line_is_a_setting_defect`, `test_t12_record_failures_are_the_13_9_list`, `test_n1_t12_command_lock_window_mismatch_exit_2` 3개다. 노드 이름으로 돌리며 판정은 1·2와 같다(감사 P-1 제안 문장). 판 5가 고치기만 한 기존 함수는 넣지 않는다.
- 판정은 원판 5절 그대로다.
  - 실패·skip·xfail이 0이어야 한다.
  - junit을 저장한다.
  - `junit_skips.py --critical`이 종료 0이어야 한다.
- 판 5가 고친 판 4a 시험 파일은 회귀 기록으로 돌린다.
  - 실패는 원인과 함께 공개한다.
  - 원인이 코드 결함이면 멈추고 묻는다.
  - 원인이 시험 환경이면 기록하고, 다음 커밋에서 시험을 고친다.
  - 회귀 기록에서 `test_chrono_t45_replay`가 skip되면 그 사실을 판정서에 공개한다. 봉인 재생 도구의 동작이 그대로인지 실행으로 확인하는 유일한 시험이기 때문이다.

## 5-2. `test_d1a` 실패의 처리
- 원인은 시험 환경이다. 판 5 준비 출력 `prelaunch_j9/ed5_inputs/dry_selection.json`의 생성 키 s25가 시험의 `06_analysis` 재스캔에 잡혔다. 실행 경로는 저장된 선정을 읽기만 한다.
- 시험이 확인하려던 내용("건식 선정이 고정 키를 재현한다")은 실행 커밋의 `-Part dry` 종료 0으로 이미 확인됐다. 이 단계는 생성 키와 키 파일 sha가 정오 1 9.1 표와 다르면 멈춘다.
- 단계 기록에 `dry_selection.json`과 세 키 파일의 sha를 남긴다: g6 `1a79e02f…`, g8 `b7c7470a…`, ref `95ce6f27…`.

## 5-3. 준비 단계 재시도의 한계
- 건식 선정과 12b 선정의 스캔은 이 판의 준비 출력 폴더 `prelaunch_j9/ed5_inputs/`를 빼지 않는다. 그래서 정오 2 2-6의 1~4b를 같은 커밋에서 다시 돌리면 앞 시도의 출력에 걸린다.
- 판 5에서는 1~4b를 다시 돌리지 않는다. 다시 돌려야 하면 멈추고 묻는다.
- 스캔 제외는 다음 개정에서 고친다.
