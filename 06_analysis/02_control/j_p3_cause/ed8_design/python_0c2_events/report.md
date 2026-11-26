# 판 8 S8-R 개정 3 0c′: 사건 행의 사건 이름·사건 다리가 정해지는지 확인 (python-expert, 봉인 전 기록, 값은 출력하지 않음)

## 결론
- **네 단계의 사건 행 모두 사건 이름이 정해진다.** 정해지지 않은 행은 0, `r67.EVENTS`에 없는 이름도 0이다.
- **사건 다리도 모든 사건 행에서 정해진다.** 정해지지 않은 행은 0, `r67.LEGS`에 없는 다리도 0이다.
- 명세 6.3의 "사건 이름을 정할 수 없는 사건 행 → `setting_defect`"에 걸리는 행은 없다. 봉인 전에 따로 정할 것이 없다.
- 입력 sha256 6개는 모두 명세와 같다. 이번에는 j9_main.jsonl도 5.1에 적힌 전체 sha와 같다.
- 행 수: C-J 388, C-S 460, C-D 12(census 24), C-G 171. 명세 5.1과 같다.

## 단계별 결과 (행 수만)

| 단계 | 사건 행 | 이름: twin `event` | 이름: 사례 기본값 | 이름 미정 | `EVENTS`에 없음 | 다리: twin `leg` | 다리: 기본값 | 다리 미정 |
|---|---|---|---|---|---|---|---|---|
| C-J | 200 / 388 | 0 | 200 | 0 | 0 | 140 | 60 | 0 |
| C-S | 260 / 460 | 0 | 260 | 0 | 0 | 140 | 120 | 0 |
| C-D | 12 키(census 24) | 12 | 0 | 0 | 0 | 12 | 0 | 0 |
| C-G | 171 / 171 | 171 | 0 | 0 | 0 | 171 | 0 | 0 |

- 사건 행은 사례의 기본 twin이 `EventTwin`인 행이다. 사례 기본값은 `verdict_cases.py` CASES에서 읽었고, 사건 행의 사례는 R12·R14·R15·R16이다.
  - R13은 결정을 내리면 `SS_FS4_TWIN`(사건 SS)이 되는데, SS는 `EVENTS`에 없다. 하지만 census 네 단계에 R13 행은 0이므로 영향이 없다. 사례를 알 수 없는 행도 0이다.
- C-D는 키 12개 기준으로 셌다. VBN과 VBNslow 두 census 행은 키 파일의 같은 job을 쓰므로, census 24행 기준으로는 모든 수가 두 배다.

## 단위 job과 twin의 꼴 (필드 이름만)
- `EventTwin` 필드(`verdict_cases.py` 61~75행): `stored_key, stored_file, event, leg, timing, offset_s, fs_kN, level, event_time_s`.
- 단위 job twin의 키 집합은 아래와 같다. 모든 키가 `EventTwin` 필드 안에 있고, 필드 밖 키가 있는 행은 0이다.
  - C-J(j9_main 줄 `job`, 설정 VBM·LSM1~4): `fs_kN,leg,level` 140행, twin 없음 60행
  - C-S(sens_keys 줄 `job`, 설정 VBM<key>): `fs_kN,leg,level` 140행, twin 없음 120행
  - **C-D(판정 job = `d_grid_keys12.json` `jobs[*].job`, 키 파일 쪽)**: `event,fs_kN,leg,level,timing` 12행
  - **C-G(판정 job = `confirm_g1_grid171.json` `lines[*].job`, 키 파일 쪽)**: `event,fs_kN,leg,level,timing` 171행
- twin은 `run_v5._case_of`(477~490행)에서 `replace(case.twin, **job["twin"])`로 사례 기본 twin을 덮어쓴다. 그래서 twin에 키가 없으면 사례 기본값이 쓰인다. 6.3의 순서와 같다.
- Y8-9의 `depth_m`·`ramp_s`는 지금 `EventTwin` 필드에 없다. 다만 census 단위 job에도 그 키가 없으므로 census의 사건 이름 결정에는 영향이 없다(참고).

## 교차 확인 (일치 건수만)
- C-S: 단위 job과 `v0_pair.job`은 case와 twin이 같다. 260/260이다.
- C-J: V0 짝은 job에서 `setting`·`mask`·`t4h_dir`만 뺀 키로 찾는다. 그래서 twin은 정의상 같다.
- C-D·C-G: 키 파일 job으로 정한 사건 이름이 V0 격자 run의 `event`와 같다(C-D 12/12, C-G 171/171). 격자 run에는 `leg` 키가 없어서 다리는 대조하지 못했다.
- C-J·C-S의 V0 짝 main.jsonl 줄에는 최상위 `event`·`leg`가 없고, `event_output`에도 없다(40/40). 그래서 기록과는 대조할 수 없었다.
  - `event_names`는 dict형이다. 바닥 사건 이름이 아닌 것으로 보여 대조에 쓰지 않았고, 타입만 기록했다.
- 짝을 찾지 못한 사건 행은 0이다. 짝 찾기 방식은 0c와 같다.

## 실행한 검증
- 의존성 점검: `STAMP`(이 세션에서 이미 점검함, 모두 있음).
- `event_names_0c2.py`(python-dev `-I -B`): **종료 0**. 끝줄은 `status ok`, `shas_ok`·`rows_ok`·`all_event_rows_resolved`가 모두 true다.
  - 사례 기본값, `EventTwin` 필드, `r67.EVENTS`의 키, `LEGS`는 소스에서 `ast`로 읽었다. 프로젝트 모듈은 import하지 않았고 코드도 실행하지 않았다.
  - 출력에는 소스 sha256도 기록했다: verdict_cases.py `ae874bc9…cf0f`, r67_g1_screen.py `1aad3a5f…0d62`.
  - 처음 두 번 실행은 종료 3(도구 오류)으로 끝났다. 원인은 `ast.literal_eval`이 변수 이름 인자(`resolve_case` 안의 `VerdictCase(case_id, …)`, `R67_FILE`)에 걸린 것이다. CASES 리터럴과 `event`·`leg` 인자만 읽도록 고쳤다.
- 음성 대조(scratchpad, 지운 뒤): 아래 경우가 모두 결함으로 잡히는 것을 확인했다. 종료 0이다.
  - twin 사건이 `EVENTS` 밖
  - 결정된 R13(SS)
  - `EventTwin` 밖 twin 키(`depth_m`)
  - `LEGS` 밖 다리
  - 알 수 없는 사례
  - 사건 행이 0인 단계(완료로 보지 않음)
- 값 노출 없는 탐침 1회(scratchpad, 지운 뒤): main.jsonl V0 사건 줄 40줄의 `event_names`·`events`·`event`·`leg` 타입과 있음/없음만 셌다.
- ruff(`--line-length 100`, 프로젝트 pyproject 규칙): 첫 실행에서 E501 6건, B905 2건이 나왔다. 고친 뒤 통과했다.
  - 출력 json은 고치기 전후의 SHA256이 같다(`c885d339…f46f`).
- codespell: 0건.
- 산출물 폴더 `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\python_0c2_events\`
  - 스크립트 `event_names_0c2.py`(sha256 `585b7f4c…dd39`)
  - 결과 `event_names_0c2.json`(sha256 `c885d339…f46f`)
  - `SHA256SUMS`는 만들지 않았다. report.md가 저장된 뒤 메인이 쓴다.
- scratchpad 하위 폴더 `python-ed8-0c2\`는 지웠다.

## 공개 (행위 그대로)
- Read로 연 파일
  - `ed8_design\python_0c_keys\report.md`, `layer_keys_0c.py`, `structure.json`
  - 명세 `jp3_remedy_spec_v8_rules.md` 186~270행
  - `04_scripts\04_hydraulic\coupled\verdict_cases.py` 1~200행, 238~245행
  - `verdict_runs.py` 494~523행
  - `run_v5.py` 470~499행
  - `04_scripts\03_control\s8\r67_g1_screen.py` 85~124행. 여기서 `EVENTS`의 깊이·램프 상수(코드 상수)가 화면에 보였다.
  - 내가 만든 `event_names_0c2.json`
- Grep: 모두 파일 하나를 path로 직접 지정했다.
  - 명세 파일: 패턴 `^#+ |0c′|0c'`
  - `verdict_runs.py`, `run_v5.py`: 패턴 `twin`
  - `r67_g1_screen.py`: 패턴 import·`EVENTS`·`LEGS` 등
  - `verdict_cases.py`: 패턴 import·`resolve_case`
  - `harness_flow.py`: 패턴 import·`sys.path`
  - `04_scripts` 폴더 전체 path 검색은 하지 않았다.
- Glob
  - path `ed8_design\python_0c_keys`, 패턴 `*`
  - path `ed8_design\python_0c2_events`, 패턴 `*`. 폴더가 아직 없어서 오류로 끝났다.
- 스크립트가 직접 연 데이터 파일(내용 읽기)
  - main.jsonl
  - `j9_runs\8a2a52ce\j9main_a1\j9_main.jsonl`(파일 하나 직접 지정)
  - `sens_keys_ed7.json`, `confirm_g1_grid171.json`, `confirm_b_grid192.json`
  - V0 격자 파일: 짝의 `file`이 가리키는 파일만 열었다(0c와 같은 4개 범위).
  - git blob `git show 3ecf61f1:…/d_grid_keys12.json`(파일 하나 직접 지정)
  - 소스 `verdict_cases.py`, `r67_g1_screen.py`
- 블라인드 경로는 열지 않았고 검색 범위에도 넣지 않았다.
  - 블라인드 경로: `j9_runs\606f8713\cdry_a1\` 아래, `prelaunch_j9\ed6_inputs\x11\selection.json`, worktree 사본
  - 검색 path로 쓰지 않은 상위 폴더: 저장소 루트, worktree 루트, `06_analysis`, `j_p3_cause`, `j9_runs`, `prelaunch_j9`, `04_scripts`
- 값 노출
  - 사건 이름별 건수, 다리별 건수, E 후보 수, 층 배정, 재접근 시각은 세지도 출력하지도 않았다.
  - 다만 json의 `source_facts.default_event_in_EVENTS`에는 사례별 코드 기본값이 `EVENTS`에 있는지가 bool로 기록돼 있다(R13만 false).

사용한 스킬: 없음
