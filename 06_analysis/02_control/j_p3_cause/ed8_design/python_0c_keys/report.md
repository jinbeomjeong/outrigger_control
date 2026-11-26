# 판 8 S8-R 0c: 층 입력 키 존재 확인 (python-expert, 봉인 전 기록, 값은 출력하지 않음)

## 결론
- **재접근 시작 목록 `reapproach_starts`**: 네 단계의 사건 행 V0 짝 모두에 있다. 결측 0이다.
- **빠른 사건 키에서 결측이 나왔다(봉인 전에 정해야 함).**
  - C-J·C-S의 V0 짝(저장 `main.jsonl` 줄)에는 `event_output.fast`가 **어느 사건 행에도 없다**.
  - 줄 전체를 키 이름으로 훑어도 `fast`가 들어간 키는 없다.
  - 명세 6.3 문면("사건 행의 V0 짝에 키가 없으면 `setting_defect`")을 그대로 적용하면 C-J 사건 200행과 C-S 사건 260행이 모두 입력 결함이 된다.
- 저장 격자 run(C-D·C-G)에서는 빠른 사건 필드를 찾았다. 위치는 **run 최상위 `fast`**이고 값은 bool이며, 결측 0이다. `event_output` 감싸개는 없다.
- sha256: 명세에 값이 적힌 키 파일 5개는 모두 같다. j9_main.jsonl은 명세에 sha가 없어서 잰 값만 기록했다.

## 단계별 결과 (행 수만)

| 단계 | 사건 행 / 전체 | V0 짝 찾음 | `reapproach_starts` 있음 | 빠른 사건 키 있음 | 결측 행(키 이름) | 빈 목록 |
|---|---|---|---|---|---|---|
| C-J | 200 / 388 (서로 다른 V0 짝 40) | 200 | 200 | **0** | **200 (`event_output.fast`)** | 5 |
| C-S | 260 / 460 (서로 다른 V0 짝 26) | 260 | 260 | **0** | **260 (`event_output.fast`)** | 0 |
| C-D | 12 키 → census 24행(VBN·VBNslow가 V0 짝 하나를 같이 씀). 서로 다른 V0 짝 12 | 12 | 12 (24행 기준 24) | 12 (`fast`, run 최상위) | 0 | 0 |
| C-G | 171 / 171 (서로 다른 V0 짝 171) | 171 | 171 | 171 (`fast`, run 최상위) | 0 | 2 |

- 사건 행은 job `case` ∈ {R12, R14, R15, R16}인 행이다(`verdict_cases.py` 153~171에서 `EventTwin`을 가진 사례). R13은 census에 없다.
- 정상 행은 C-J 188행, C-S 200행이다. 정의상 층 N이라 키 요구가 없으므로 보지 않았다.
- V0 짝 찾기
  - C-J: j9_main job에서 `setting`(VBM·LSM1~4)·`mask`·`t4h_dir`을 뺀 키로 main.jsonl V0 줄을 찾았다. 200행 모두 정확히 1줄씩 맞았고 오류 줄은 0이다.
  - LSM 행도 같은 키의 V0 줄을 층 짝으로 읽었다. 명세의 "LSN의 기준은 같은 키 VBN 줄"은 판정 기준이다. 층은 6.3에 따라 V0 짝에서 정한다고 해석했다.
  - C-S: `v0_pair.job`으로 찾았고 `source`는 460/460이 `v5/main.jsonl V0`이다.
  - C-D: D 12 job이 `confirm_b_grid192.json` 줄과 하나씩 맞고, 그 `v0_pair`로 run을 찾았다.
  - C-G: `run_id`는 171/171이 문자열이라 `int()`로 바꿔 찾았다(C-D는 정수 12/12).
  - 격자 run 183개(C-D 12 + C-G 171) 모두 `commands_sha256`가 `v0_pair.v0_commands_sha256`와 같다.
- 값 타입: `reapproach_starts`는 모두 list다. 격자 `fast`는 모두 bool이다. null 0, 다른 타입 0.
- 빈 목록은 행 단위로 셌다. C-J의 5는 VBM·LSM 행이 같은 V0 짝을 함께 쓰는 것을 포함한 수다. 층 배정은 하지 않았다.
- `fast`의 참·거짓 건수, 재접근 시각, 다리, 층 E/N은 세지도 출력하지도 않았다.

## 빠른 사건 필드 위치 (b·c에서 찾은 것과 a의 결측)
- 격자 run: 최상위 `fast`. 생성 코드는 `04_scripts/03_control/s8/r67_g1_screen.py` 436행 `"fast": is_fast(ev)`이다.
  - `is_fast`는 같은 파일 120~121행이고, 정의는 `depth / ramp > V_MAX`다.
  - 격자 파일 4개(`06_analysis/02_control/touch_phase/acceptance/c4g2_only/grid/grid_r67_main.json`, `grid_r67_top.json`, `grid_r69_bottom.json`, `grid_r69_top.json`) 모두 run 192/192에 `fast`·`event`·`reapproach_starts`가 있다.
- main.jsonl V0 사건 줄 40/40에서 `event_output` 키 집합에 `fast`가 없다. 줄 전체를 재귀로 훑어도 `fast`를 품은 키는 0이다.
  - 원인: run_v5 사건 경로는 `verdict_runs.py` 498행 `r67.judge_event(...)` 결과를 `event_output`로 넣는다(518행).
  - `judge_event`의 출력(`r67_g1_screen.py` 343~380행)에는 `fast`가 없다. 격자는 436행에서 따로 덧붙인다.
  - `run_v5.py` 600~601행은 `event_output`에서 `twist`만 빼고 복사한다. 그래서 main.jsonl에는 원래 기록되지 않는다.
- main.jsonl 짝에서 빠른 사건을 정할 수 있는 길(구조만, 값은 계산하지 않음)
  - V0 사건 줄의 job `twin` 필드 집합은 `fs_kN,leg,level` 28줄과 없음 12줄이다. **`event` 재정의가 없다.**
  - 그러므로 사건 이름은 사례 기본값이다(`verdict_cases.py` 153~171: R12 `G4`, R14·R15·R16 `RE1bF`).
  - 같은 정의(`verdict_runs.py` 472행 `r67.EVENTS[twin.event]` → `r67.is_fast`)로 정하면 격자 `fast`와 같은 함수가 된다.
  - 이것은 입력 설정(사건 이름)에서 정해지는 처리 전 공변량이다. 다만 이 계산은 층 배정의 일부이므로 여기서 하지 않았다.

## sha256

| 파일 | 잰 값 | 명세 | 일치 |
|---|---|---|---|
| `06_analysis/03_hydraulic/coupled/v5/main.jsonl` | `9ad749907c34c9e9efb77579a8ab6e3b1f86cdc32d36162c0029005ca545b29e` | 앞 8자 `9ad74990` | 예 |
| `j9_runs/8a2a52ce/j9main_a1/j9_main.jsonl` | `c89ec827ce541a53127a0115b8e1185b35e50df9cea2612d4a74b40cc618c122` | 명세에 값 없음 | 기록만 |
| `ed7_design/keys_seal_b46bdf8f/sens_keys_ed7.json` | `be930b75…62a05b1b` | `be930b75…62a05b1b` | 예 |
| `d_grid_keys12.json`(git blob `3ecf61f1:06_analysis/02_control/j_p3_cause/prelaunch_j9/run_records_ed6/d_grid_keys12.json`) | `a995abff…57d87981` | `a995abff…57d87981` | 예 |
| `ed7_design/keys_seal_b46bdf8f/confirm_g1_grid171.json` | `684054ab…5b5dec` | `684054ab…5b5dec` | 예 |
| `ed6_design/keys/confirm_b_grid192.json` | `4e80e69bd2233b994853ae3f60ed0749f2c39c7dbb6390bc012b016efa5cf85b` | 앞 8자 `4e80e69b` | 예 |

- 격자 파일 4개의 sha256(기록)은 `layer_keys_0c.json`의 `grid_files_sha256`에 있다.
- 행 수: C-J 388, C-S 460, C-D 12(census 24), C-G 171. 모두 명세 5.1과 같다.

## 확인 필요 (명세 작성자 control-expert, 봉인 전)
- **명세 6.3·5.1의 C-J·C-S 빠른 사건 키 경로**
  - 규칙 문서: `jp3_remedy_spec_v8_rules.md` 250행("`event_output.fast` 참"), 254~255행(키 경로·결측 = `setting_defect`), 212행.
  - 데이터·코드: main.jsonl V0 사건 줄 40/40에 없음. 기록하지 않는 위치는 `verdict_runs.py` 498·518행, `r67_g1_screen.py` 343~380행 대 436행이다.
  - 가능성 (가): main.jsonl 짝은 사건 이름(job `twin.event`, 없으면 사례 기본값)에 `r67_g1_screen.is_fast(r67.EVENTS[event])`를 적용해 정한다고 적는다. 격자 `fast`와 같은 함수다. 사건 행 키 요구는 `reapproach_starts` 하나로 줄인다.
  - 가능성 (나): 문면 그대로 둔다. 그러면 C-J·C-S 사건 단위 전부가 `setting_defect`가 되어 census가 판정 불가가 된다.
- **LSN 행의 층 짝**: 같은 키의 V0 줄로 읽었다. 6.3 "V0 짝"을 LSN에도 그대로 쓰는지 문면에 한 줄 있으면 구현(Y8-6)이 모호하지 않다.

## 실행한 검증
- 의존성 점검: `STAMP`(이 세션에서 이미 점검함, 모두 있음).
- `key_presence.py`(python-dev `-I -B`)
  - 대상: main.jsonl, `--where job.setting=V0 --where job.case=<R12|R14|R15|R16>`, 키 `event_output.reapproach_starts,event_output.fast`.
  - 네 번 모두 **종료 1**(`key_absent` 1). 원인은 `event_output.fast` 결측이다(R12 0/32, R14 0/2, R15 0/2, R16 0/4). `reapproach_starts`는 32/32·2/2·2/2·4/4다.
  - 도구는 행 선택(V0 짝 찾기)과 격자의 중첩 `results[*].runs[*]`를 다루지 못한다. 그래서 단계별 짝 찾기는 즉석 스크립트로 했다.
- `probe_structure.py`: 종료 0. 필드 이름과 설정·사례 건수만 본다.
- `probe_fast_field.py`: 종료 0. `fast`를 품은 키 경로만 찾는다.
- `layer_keys_0c.py`: **종료 1**(`keys_complete: false`, 원인은 위 C-J·C-S `fast` 결측). sha·행 수 확인은 통과했다.
- ruff
  - 첫 실행에서 `layer_keys_0c.py` E501 1건이 나왔다(프로젝트 줄 길이 100).
  - 한 줄을 둘로 나누고 다시 돌리니 통과했다. 다시 실행한 출력은 처음 출력과 SHA256이 같다(scratchpad에서 비교한 뒤 지움).
  - 나머지 두 스크립트는 통과했다.
- codespell: 세 스크립트에서 0건.
- 산출물 폴더 `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\python_0c_keys\`
  - 스크립트: `layer_keys_0c.py`, `probe_structure.py`, `probe_fast_field.py`
  - 결과: `layer_keys_0c.json`, `structure.json`, `fast_field.json`, `key_presence_main_v0_R12.json`·`_R14`·`_R15`·`_R16`(도구 출력 사본)
  - `SHA256SUMS`는 만들지 않았다. report.md가 저장된 뒤 메인이 쓴다.
- scratchpad 하위 폴더 `python-ed8-0c\`는 지웠다.

## 공개 (행위 그대로)
- Read로 연 파일
  - 명세 `jp3_remedy_spec_v8_rules.md` 1~120행, 179~308행
  - `ed8_design\python_q8_checks\report.md` 100~218행, 같은 폴더의 `layer_input_check.py`·`d_pair_check.py`
  - `~/.claude/tools/verif/README.md` 1~223행, 427~486행
  - `04_scripts\03_control\s8\r67_g1_screen.py` 340~449행
  - `04_scripts\04_hydraulic\coupled\verdict_cases.py` 150~179행, `verdict_runs.py` 470~524행·575~634행, `run_v5.py` 585~609행
  - 내가 만든 json 3개
- Grep(모두 파일 또는 하위 폴더를 path로 직접 지정)
  - 명세 파일: 패턴 `^#+ `, `j9_main\.jsonl|9ad74990|4e80e69b|grid_r6`
  - `python_q8_checks\report.md`
  - 판정서 파일 `j_p3_cause\jp3_ed7_judgement_8a2a52ce.md`: 패턴 `j9_main\.jsonl`, `j9_main`(출력 20줄)
  - `verdict_cases.py`
  - 파일 2개(`run_v5.py`·`verdict_runs.py`)로 좁힌 glob과 path `04_scripts\04_hydraulic\coupled`
  - `r67_g1_screen.py`
  - verif README
  - **`04_scripts` 폴더 자체**를 path로, glob `*.py`, 패턴 `"fast"|\bfast\b\s*[:=]`, 출력 .py 34줄. 블라인드를 품은 상위 폴더는 아니지만 코드 폴더 전체 검색이다.
- Glob: path `ed8_design\python_q8_checks`(패턴 `*`) 1회.
- 스크립트가 직접 연 데이터 파일
  - 내용 읽기: main.jsonl, `j9_runs\8a2a52ce\j9main_a1\j9_main.jsonl`(파일 하나 직접 지정), `sens_keys_ed7.json`, `confirm_g1_grid171.json`, `confirm_b_grid192.json`, 격자 파일 4개(위 경로)
  - git blob: `git show 3ecf61f1:06_analysis/02_control/j_p3_cause/prelaunch_j9/run_records_ed6/d_grid_keys12.json`(파일 하나 직접 지정, 목록 열거 없음)
- 블라인드 경로는 열지 않았고 검색 범위에도 넣지 않았다. 해당 경로는 `j9_runs\606f8713\cdry_a1\` 아래, `prelaunch_j9\ed6_inputs\x11\selection.json`, worktree 사본이다. 저장소 루트·worktree 루트·`06_analysis`·`j_p3_cause`·`j9_runs`·`prelaunch_j9`는 검색 path로 쓰지 않았다.
- 값 노출
  - 재접근 시각·다리·`fast` 참거짓·통과 플래그·층 배정은 출력하지 않았다.
  - 빈 목록 수(C-J 5행, C-G 2행)는 지시대로 셌다.

사용한 스킬: 없음
