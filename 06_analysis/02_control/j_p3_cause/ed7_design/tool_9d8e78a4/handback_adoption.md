의존성 점검: 이 세션에서 이미 점검함(STAMP), 필요한 것은 모두 있음.

## 요약
명세 4.2의 조건 3 채택 규칙을 도구로 만들어 ed7-impl에 커밋했다(9d8e78a4). probe 6bfb2560 출력에 돌린 결과는 **status `decided`, 결론 = 팔 2(a2) 유지**다. 아래 「확인 필요」에 적은 열린 해석 다섯 가지를 조합한 32가지 모두에서 결론이 a2로 같다. 해석이나 권고는 붙이지 않았다.

## 한 일
- 도구: `C:\workspace\outrigger_control\.claude\worktrees\ed7-impl\04_scripts\04_hydraulic\coupled\ed7_condition3_adoption.py`
- 시험: `C:\workspace\outrigger_control\.claude\worktrees\ed7-impl\05_tests\unit\test_ed7_adoption.py`(합성 줄 29건)
- 커밋: 9d8e78a4(ed7-impl, 부모 ad7a716e). 병합·push는 하지 않았다.
- 결과(새 파일): `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\6bfb2560\ed7_probe_a1\adoption_9d8e78a4.json`(sha256 70675fdc…dcd2). 같은 폴더의 기존 condition*.json은 건드리지 않았다.
- 근거 폴더: `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\tool_9d8e78a4\`
  - manifest.json: 실행 명령, 입력·출력 sha
  - tests\: JUnit과 로그
  - checks\: 교차 확인 스크립트와 결과
  - SHA256SUMS: write-sums로 만듦, 항목 5개, 파일 sha 5de18a7f…
- 입력 sha
  - probe jsonl: 1107b309…
  - 키 파일 `tool_6bfb2560\keys\probe_keys_ed7.json`: 189dbb13…(`--keys-sha256`로 확인)
  - V0 `06_analysis\03_hydraulic\coupled\v5\main.jsonl`: 9ad74990…(`jp3_fixed_inputs.MAIN_JSONL_SHA256`와 같음)
- 실행 상태
  - 실행 정체성: probe run 시작·끝이 6bfb2560 clean, 도구 checkout은 9d8e78a4 clean(`--require-clean`).
  - 실행 기록 점검: 654/654줄, 빠진 job·반복 job·error 줄 0, line_problems 0. 줄별로 tag·components·ib_condition·hydraulic_options·probe 블록·blind 블록을 대조했다.

## 규칙 항목별 결과
- 대상: 본 부분(main) 15키, 팔 a2·a3·a4.
- 실패 단위: (플랜트, 키) 단위로 센다. V0 대비 실패는 판 6 probe 몫 도구와 같은 방식이다. `_full_items`의 J1~J11 fail 항목과, R15 나빠짐(두 R15 키)을 센다.
- 비틀림 지표: n_rev·래치·네 다리 동시 트리거는 모든 팔·플랜트에서 0이다. 비율 칸은 "|D|를 키운 shot / 분모 shot"이다. 비율의 분모 해석 두 가지(known/all)는 이번 데이터에서 같은 값이다(모든 shot에 twist_grew 값이 있음).

| 해석(plants·stiffness) | 팔 | 실패 단위 | \|D\| 키운 비율 | 네 다리 동시 | n_rev | 래치 |
|---|---|---|---|---|---|---|
| vbm5·none | a2 | 11 | 24/47 = 0.511 | 0 | 0 | 0 |
| | a3 | 10 | 28/53 = 0.528 | 0 | 0 | 0 |
| | a4 | 11 | 24/47 = 0.511 | 0 | 0 | 0 |
| all6·none | a2 / a3 / a4 | 12 / 11 / 12 | 29/57 = 0.509 / 34/64 = 0.531 / 0.509 | 0 | 0 | 0 |
| vbm5·sens_exempt | a2 / a3 / a4 | 3 / 2 / 3 | 위와 같음(vbm5) | 0 | 0 | 0 |
| all6·sens_exempt | a2 / a3 / a4 | 4 / 3 / 4 | 위와 같음(all6) | 0 | 0 | 0 |

J7 해석 두 가지(ed6_share, ed7_new)는 모든 그룹에서 실패 키가 같다(probe 줄에 대체 사건 차이가 없음).

| 기준(문턱) | a3 대 a2 | a4 대 a2 |
|---|---|---|
| ① 실패 단위가 a2보다 엄격히 적음 | 통과(모든 해석에서 1 적음) | 실패(같음) |
| ② 새 실패 단위 0 | 통과(0) | 통과(0) |
| ③ 비틀림 지표가 나쁘지 않음(네 지표 모두 a2 이하) | **실패**: \|D\| 키운 비율 0.528 > 0.511(all6은 0.531 > 0.509). 나머지 세 지표는 0 = 0 | 통과 |
| 채택 | 안 됨 | 안 됨 |

- 규칙상 결론: 32개 해석 모두 결과가 `a2`다. 그래서 팔 2(조건 3 (다))를 유지한다.
- a3와 a2의 실패 단위 차이는 Mc04 `R12_top-FR-Fs0-o0.05` 하나다(a2·a4에서 J1 gate end_att, J4 final ready→probe, J5 t_back 22.55→None 실패, a3에서는 통과).
- 그 밖의 실패 단위는 세 팔이 같다.
  - 대부분은 J7 `WARN_PROBE_STIFFNESS_OUT_OF_RANGE`다: M·Mc005·Mc04·L의 `R12_top-FL-Fs8-o0.0`, Mslow 7키.
  - Mslow `S7_e0.001`은 J3(t_ready 77.1→102.9 s)에서도 실패한다.

## Q7-C4 판단용 사실(654줄 전체, 두 부분·모든 팔)

| 항목 | 건수 |
|---|---|
| `WARN_PROBE_RETRACT_NOT_OPENED`가 난 줄 / 다리 | **0 / 0**(event_names·events 둘 다 봄) |
| D6 증인 기록이 있는 줄 | 346. c2 팔 90줄은 증인이 꺼져 있어 기록이 없다. 나머지 기록 없는 줄은 탐침 라운드가 없는 줄이다 |
| 증인 라운드 수 | 2336(팔별: a1 352, a2 476, a3 384, a4 380, a5 380, a6 364) |
| 판정 불가 라운드(`not_judgeable_rounds`) | 0 |
| 역순 라운드(`is_reversed` 참) | 0 |
| 역순 라운드 비대체 / 대체(`reversed_rounds`) | 0 / 0 |
| 기록 키가 빠진 증인 블록 | 0 |
| WARN 경로(역순 여부), WARN의 J7 영향 | 해당 줄이 없어 0건. 도구는 분류를 낸다: 경로 reversed_all/some/not_reversed, J7 영향 only/other/no_v0_reference |

- 참고 1: c2 팔은 증인이 꺼져 있어, 역순 라운드가 있었는지 이 기록으로는 알 수 없다.
- 참고 2: D부분 24줄은 저장 V0 main.jsonl에 짝이 없다. WARN이 났다면 J7 영향은 `no_v0_reference`로 분류된다.

## 검증
- pytest(Chrono-dev, 커밋 내용, clean tree): `test_ed7_adoption.py` + `test_ed7_units.py` 85 passed, skip 0, xfail 0. JUnit은 근거 폴더에 있다.
  - 시험 범위: 기준 각각, 해석 의존, both_qualify, 판정 불가, 상태 순서, 키 결측을 0으로 읽지 않음.
  - main 끝까지 시험: 생산자 꼴 줄(맨 T4h 이름, `<stem>_t4h`, identity)을 다른 CWD에서 돌렸다. 기존 --out 거부, 키 sha 불일치, 예상 밖 예외 = 종료 3도 본다.
- 독립 교차 확인: 판 6 도구 `ed6_probe_share.group_judgement`를 같은 18그룹(6플랜트 × a2~a4)에 돌렸다. 실패 키가 18/18 같다.
- ruff(프로젝트 설정, `--no-cache`)·codespell 통과. `-W error` 컴파일 통과, `--help` 정상.
- 실행 시간: 약 3 s. 그래서 진행 파일은 두지 않았다.

## 확인 필요
명세 4.2에 없는 해석이다. 고르지 않고 32개 조합을 모두 계산했고, 이번 데이터에서는 결론이 바뀌지 않는다. 봉인 문면에서 정할 거리다.
1. "V0 대비 실패"의 J7: 판 6 probe 몫 방식(기간 비교) 대 6.1 새 J7((이름, 다리, 사유))
2. 감도 J7 강성 경고 예외(6.2)를 probe의 Mslow·Mfast·Mc005·Mc04 단위에 적용하는지
3. 실패 단위를 셀 플랜트: VBM 5개 대 대조 L 포함 6개
4. "|D|를 키운 트리거 비율"의 분모: twist_grew 값이 있는 shot 대 전체 shot
5. n_rev 집계: 합 대 줄별 최대
6. 그 밖: 팔 3·4가 둘 다 채택 조건을 만족할 때 무엇을 고를지 명세에 없다(이번에는 해당 없음). 도구는 이 경우를 `undecided`로 낸다.

## 블라인드 경로 관련(사실대로)
- worktree 루트를 경로로 준 Glob이 3번 있었다. 패턴은 모두 `04_scripts/04_hydraulic/coupled/...`로 좁혔고, 셋 다 결과가 0건이었다. 블라인드 폴더 이름·파일은 출력에 나오지 않았다.
- worktree에서 `git status --short`를 실행했다. 출력에 06_analysis 항목은 없었다.
- 그 밖의 검색·읽기 범위
  - Grep: worktree 03_src·04_scripts
  - 목록 조회: 메인 checkout의 `j9_runs\6bfb2560\`, `ed7_design\`(폴더 이름만, tool_6bfb2560 아래), `ed7_design\tool_ad7a716e\`
  - 읽기: 명세, V0 `06_analysis\03_hydraulic\coupled\v5\main.jsonl`
- 블라인드 경로(`606f8713\cdry_a1\...`)는 열거나 검색하지 않았다.

## 정리
scratchpad `python-ed7adopt\`는 지웠다.

사용한 스킬: 없음
