## 요약
사용자 결정 1~3을 ed7-impl에 새 커밋 **b46bdf8f**(부모 9d8e78a4)로 반영했다. 병합·push는 하지 않았고 worktree는 clean이다. 명령은 바뀌지 않았다(기록 키만 추가).

고정 해석으로 채택 도구를 다시 돌린 결과는 **status `decided`, 결론 = 팔 2(a2) 유지**다. 기록용 32개 조합도 모두 a2다.

## 1. 기록 키(명세 담당이 3.1·7절을 이 이름에 맞추면 된다)
- **범위**: `A_ib`가 켜진 실행에서만 생긴다. 기존 판 7 `lsb_*` 관례와 같다. 판 6 설정과 `A_ib`가 꺼진 설정에는 키가 생기지 않는다(시험으로 확인).
- **`lsb_record.blind.level_done`**: LEVEL → DONE마다 한 항목 `{t_s, path, twist_load_N}`이다.
  - `path`는 `"strict"` 또는 `"relax"`다.
    - strict: |D| < done_twist_N이거나 relax가 꺼진 경우
    - relax: DONE 주기의 P-S8-29 완화 조건으로 끝난 경우. 기존 `INFO_TWIST_UNSETTLED`와 같은 판별이다.
  - 구현: `c2._note_level_done` → `LockStartB.note_level_done`
- **`lsb_record.blind.twist_over_limit`**: `{limit_N, entries, periods, episodes:[{start_t_s, end_t_s, periods, max_abs_twist_N}]}`
  - 대상: LEVEL 주기 중 |D|가 조건 (다)의 상한을 넘은 구간이다.
  - 상한: `ib_twist_limit_N`, 없으면 relax `max_twist_N`(R8 프리셋 15 kN).
  - `entries`가 |D|>15 kN 진입 수다.
  - `end_t_s`는 넘지 않은 첫 주기이거나 다른 단계로 바뀐 주기다. 열려 있는 구간은 `None`이다.
- **T4h 배열 `lsb_ib_twist_load_N`**: 매 제어 갱신(10 Hz)의 D 값이다. 행이 없으면 NaN이다.
- 조건 (다) 판정은 같은 상한 함수(`_twist_limit_N`·`_is_twist_over_limit`)로 묶었다. 값은 그대로다.
- 이미 끝난 probe 6bfb2560 출력에는 이 키들이 없다. 7절 표의 "|D|>15 진입 수"·"DONE 경로" 칸은 b46bdf8f 이후 실행 출력에서 채워야 한다.

## 2. 채택 도구 해석 고정
- 기본 판정: `FIXED_READING` = J7 ed7_new(이름·다리·사유) + 감도 J7 강성 경고 예외(Mslow·Mfast·Mc005·Mc04) + 플랜트 VBM 5개(L 제외) + 비율 분모 = twist_grew 값이 있는 shot + n_rev 합.
- `--interp-grid`: 32개 조합을 `decision.interp_grid`에 기록만 한다(`record_only: true`, 상태에는 쓰지 않음).
- 팔 3·4가 둘 다 채택 조건을 만족하면 지금은 `undecided`로 둔다(명세 개정 5에서 정함).

결과 파일(새 파일): `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\6bfb2560\ed7_probe_a1\adoption_b46bdf8f.json`(sha256 186d703c…2000). 기존 condition*.json과 adoption_9d8e78a4.json은 그대로 두었다.

| 항목(고정 해석) | a2 | a3 | a4 |
|---|---|---|---|
| V0 대비 실패 단위 | 3 (M FL-Fs8, Mc04 FR-Fs0-o0.05, Mslow S7) | 2 (Mc04 FR-Fs0-o0.05 통과) | 3 |
| \|D\| 키운 shot 비율 | 24/47 = 0.511 | 28/53 = 0.528 | 0.511 |
| 네 다리 동시 / n_rev 합 / 래치 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |

| 기준 | a3 대 a2 | a4 대 a2 |
|---|---|---|
| ① 실패 단위가 엄격히 적음 | 통과 | 실패 |
| ② 새 실패 단위 0 | 통과 | 통과 |
| ③ 비틀림 지표가 나쁘지 않음 | **실패**(비율 0.528 > 0.511) | 통과 |
| 채택 | 안 됨 | 안 됨 |

## 3. Q7-C4
- `jp3_ed7_rules.py`에 다음을 두었다.
  - `J7_EXEMPT_WARNINGS = {WARN_PROBE_STIFFNESS_OUT_OF_RANGE}`
  - `is_j7_stiffness_exempt`: 단독 조건, 빈 집합은 예외가 아니다.
  - `RETRACT_NOT_OPENED_WARNING`
- 채택 도구는 이 함수를 쓴다.
- 확인 결과: `WARN_PROBE_RETRACT_NOT_OPENED`는 어떤 J7 예외 목록에도 없었다(jp3_ed7_rules, 채택 도구, jp3_ed6_judge는 강성 경고만 예외로 둔다).
- 시험으로 고정했다.
  - 예외 집합이 강성 경고 하나뿐이다.
  - retract WARN만 있거나 강성 경고와 섞이면 예외가 아니다.
  - V0에 없는 retract WARN은 `j7_items_ed7`에서 fail이다.
  - 채택 도구에서 retract WARN 단위는 감도 플랜트에서도 실패로 센다.

## 검증
- **P7-0·P7-1**(`test_ed7_harness`, 하네스 dynamics-dev)
  - 옛 플랜트 7줄의 명령 해시가 79495405와 같다.
  - VBM R12와 VBM0 R12의 해시가 같다.
  - VBM 줄에 새 키가 있다. R12는 `level_done` 1개 이상이다.
- **probe 재현성**: b46bdf8f에서 `ed7_probe`를 8 job 돌렸다(M·Mc04 × a2·a3 × R12_top-FR-Fs0-o0.05·R12_top-FL-Fs8-o0.0). 저장된 6bfb2560 줄과 비교하면 commands_sha256 8/8이 같고, 8/8 모두 새 키 3개가 있다. error는 0이다.
- **ed7 시험**(units + adoption + harness, Chrono-dev, 커밋 내용): 101 passed, skip 0, xfail 0
- **관련 17파일**(-n 8: c2·lock_start_b·ed6·jp3_rev6·ground_contact·two_pressure·v5 설정/태그): 780 passed, 13 skipped
  - skip 13개는 모두 two_pressure 2파일의 `07_results/S8` 저장 자료 skip이다.
  - 이 2파일을 `tools\verif\worktree_tests.py`로 다시 돌렸다(b46bdf8f, 메인 checkout 자료): 73 passed, **skip 0**, probe 모듈은 worktree 것, 원본 불변.
  - 종료 1은 `data_literal_not_rebased` 경고 5건이고, 이전과 같다.
- ruff(`--no-cache`)·codespell: 변경 파일 모두 통과
- 하지 않은 것: 전체 suite, mypy(프로젝트 설정 없음)

## 근거
`C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\tool_b46bdf8f\`
- manifest.json: 키 이름, 실행 명령, 출력 sha
- tests\: ed7·관련 subset·worktree_tests JUnit, 로그, 보고서
- checks\: probe 재현 비교 스크립트와 json
- SHA256SUMS: 항목 9개, 파일 sha 58859664…(write-sums --recursive)

## 동작 변경
- 명령은 바뀌지 않았다(P7-0, P7-1, probe 8줄 해시 동일).
- 기록 키가 추가됐다: 위 1의 jsonl 키 두 개와 T4h 배열 하나.
- 채택 도구 출력 구조가 바뀌었다.
  - 이전 `decision.outcomes`·`readings`는 없어졌다.
  - 대신 `decision.fixed_reading`이 있고, 선택하면 `decision.interp_grid`가 붙는다.
  - stdout 마지막 줄의 `readings`·`outcome_kinds`는 `grid_readings`로 바뀌었다.

## 블라인드 경로
- Grep 대상은 worktree의 03_src·04_scripts·05_tests뿐이었다.
- 경로를 지정해 열거나 쓴 파일: worktree의 `test_ed7_harness.py`, main checkout의 `j9_runs\6bfb2560\`, `ed7_design\tool_b46bdf8f\`, tool_6bfb2560의 handback·related 로그.
- worktree 루트나 06_analysis를 대상으로 검색·Glob은 하지 않았다.
- `worktree_tests.py`는 지정한 시험 2파일만 복사했고, `07_results` 경로만 메인 checkout으로 바꿨다.

## 정리
scratchpad `python-ed7rec\`는 지웠다.

사용한 스킬: 없음
