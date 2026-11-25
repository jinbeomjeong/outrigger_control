## 감사 요약
- 본 결과: 판 7 실행 출력은 없다(`j9_runs\8a2a52ce` 폴더 자체가 없음). 다음 파일은 열었거나 값을 보았다.
  - 판 6 `j9_runs\79495405\l1ref_a1\L1_VBL.json`: `key_presence`로 키 10개가 있는지와 그 건수만 보았다(값은 출력하지 않음).
  - 판 6 `L1_VBL_t4h\*.npz`: 배열 8개 이름이 있는지만 보았다.
  - `l1ref_a1` 아래 npz 파일 이름(Glob, 568개 중 100개).
  - 판 6 `impl_t8.done`: 명령·정체성·종료 코드. 결과 값은 들어 있지 않다.
  - T′ 근거 폴더 `t_scope_check.json`·`suite_record.json`·`worktree_tests.md`, 실행 경로 목록 json.
  - 블라인드 경로와 판 6 `selection.json`은 열지 않았다. 상위 루트(`j_p3_cause`·`j9_runs`·worktree 루트)를 범위로 한 검색도 하지 않았다.
  - 공개: `ref_check`가 비슷한 이름 후보로 `j9_runs/606f8713/cases_a1/logs/…` 이름 몇 개를 화면에 냈다. 블라인드 정의(`cdry_a1/VBK_c92*`·`VBK_c93*`·`cdry_a1/logs/`) 밖의 이름이다.
- 대상·시점: 실행 전. 판정 도구 커밋 T′의 P7-11 재감사와 정오 1 봉인 전 재감사다.
- 기준 문서
  - 봉인 명세 `jp3_remedy_spec_v7.md`: 10902ffd. raw가 `.sha256`과 같고, LF·BOM 없음·`-text`.
  - 정오 1 초안: df5a5dfe. 미추적, LF 262줄, CRLF 0, BOM 없음, `-text`, ignore에 걸리지 않음.
  - C = 8a2a52ce, T = c91065b7, T′ = 60ebb4a4(부모 T).
- 판정: **차단 1 / 실행 전 수정 3 / 기록 14**
  - **T′(코드)는 P7-11을 통과한다.** 범위·목록·`03_src`·시험이 모두 맞고, 앞 차단 B-2·B-3·M-1·R-10·R-11은 코드에서 해소됐다. B-1은 앞 감사의 지적 자체가 틀렸다(아래 R-1). T′ 기준으로 판정 단계에 갈 수 있다.
  - **정오 1은 이대로 봉인하면 안 된다.** 차단 1건(N-B1, 경로 2 넘김)이 있다. 이것과 실행 전 수정 M-a·M-b의 문면을 고친 뒤 봉인할 수 있다. 셋 다 도구 변경은 필요 없고 control-expert의 문면 수정만 필요하다.
  - 실행 단계 1~11은 이 차단으로 막히지 않는다(봉인본 4절 5a). 다만 M-c는 1단계 전에 확인하기를 권고한다.

## 확인 항목별 결론(지시 1~8)
1. **P7-11 범위: 맞음**
   - git으로 직접 대조했다.
     - `git diff --name-status 8a2a52ce 60ebb4a4`: 9경로, 모두 `04_scripts/04_hydraulic/coupled/`·`05_tests/` 아래다.
     - `git diff --stat c91065b7 60ebb4a4`: 4파일.
     - `8a2a52ce:03_src` = `60ebb4a4:03_src` = `c91065b7:03_src` = 0cffdbdf.
   - 실행 경로 목록
     - T′ blob의 sha256과 근거 사본이 모두 e9c852e4…로 같다.
     - 155개 항목의 blob이 C·T′ 양쪽에서 목록 값과 같다(불일치 0, `git cat-file --batch-check`).
     - 바뀐 9경로 중 목록에 든 것은 0이다.
   - 138 대 155: 같은 목록 하나다. 155 = 03_src 밖 Python 닫힘 138 + `run_steps_ed7` 15 + dot-source ps1 2(`run_steps/common.ps1`·`record_helper.ps1`).
   - 독립 재계산이 `t_scope_check.json`(`in_scope`)과 같다.
2. **앞 차단 해소**(T′ 행 번호)

| 항목 | 해소 | 근거 |
|---|---|---|
| B-1 | 변경은 맞고 해롭지 않다. 지적은 틀렸다(R-1) | `_sens_jp3` 1012~1023. 시험 `test_ed7_judge.py:828-863`이 460줄 배치에서 104를 보이고, 859행이 **T 방식(전체 줄 투입)도 104**임을 단언한다 |
| B-2 | 해소 | `r79_condition_entry` 528~549, `r79_condition_basis` 562~573. 12a `jp3_tjr_judge_ed7.py:113-125·133-134`. 12b `jp3_12b_judge_ed7.py:173-204·248-249`. 상태는 조건을 더한 뒤에 정해진다(`jp3_tjr_judge.py:1859-1861`, `jp3_12b_judge.py:1416·1445`) |
| B-3 (1-8) | 해소 | `judge_t8` 1305~1306(`identity_defects`), 1313~1316(`controller_tags`·`expected_tags`) |
| B-3 (1-9) | 해소 | `judge_l1ref` 1549~1582, `r79_line_identity` 1532~1546, `identity_source_values` 371~390 |
| M-1 | 해소 | 1475~1478: `failures` 빈 목록, `hashes["differences"]`를 `setting_defects`로 |
| R-10 | 해소 | 424~425 |
| R-11 | 해소 | 12a `STEP_FILE_OPTIONS` 51~52(`--new-t4h`·`--base-t4h`), 12b 264~265(`--vbk0-t4h`·`--vbk-t4h`, `b<j>=` 분리 289행). 거부 시험 `test_ed7_judge.py:1013-1029` |
| M-5 | 절차로만 해소 | help·docstring 1631~1633. 도구는 위치를 거부하지 않는다(R-6) |

3. **정오 1-20과 T′ 일치: 맞음**
   - 546행: `line_condition`의 결과가 `setting_defect`이고 `missing == ["t_event_s"]`일 때만 `no_event`(조건 읽기 0)다.
   - 539~543행: T4h 파일이나 `T4H_ARRAYS`가 없으면 `setting_defect`다.
   - `t_event_s`가 있으면 `line_condition`이 정상 계산한다(`jp3_rev7_condition.py:219-241`).
   - 12a·12b 래퍼는 조건 읽기 0을 `rev7_condition_records`(기록)로만 넣는다. `r79_condition_basis`가 `not_judgeable` 목록에 아무것도 넣지 않으므로, rev 6 J-P3 판정에는 섞이지 않는다.
   - 1-20의 코드 사실도 맞다. C의 r79 계열 6파일 `t_event_s` Grep이 0건이고, `j_p3_run_record` 1306~1314는 `head_only_declared` False다.
4. **1-16 정정: 사실과 맞다**
   - `j_p3_inputs.py:250-261` `_revision_5_judgement`는 `REV5_JUDGED_SETTINGS`(67~68행, 판 7 몫 62~63행)의 줄만 `rev7`로 보내고, 나머지는 `rev7_record_only`로 보낸다.
   - `jp3_judged_rows`(450~458)는 `rev5/6/7`만 센다. 그래서 T의 판정 행도 104였다.
   - **T에서 기록 6설정의 침범(H-7)은 status에 들어가지 않았다.**
     - `jp3_basis` 468~469행의 `has_judged_breach`는 `rev5/6/7`(판정 몫)만 본다.
     - `j_p3_over_rows` 232~235행의 `status_by_revision`도 판정 몫뿐이다.
   - **T에서는 기록 줄의 줄 단위 결함 수가 status에 들어갈 수 있었다.**
     - 대상은 `rule_missing`·`test_only`·`l1_reference`·`revision_key_missing/mismatch`다(`j_p3_over_rows` 236~237, `jp3_basis` 471~474, `JP3_ROW_DEFECT_COUNTS` `jp3_j9main_judge.py:365`).
   - **T′은 기록 줄을 J-P3 status에 넣지 않는다.** 그 대신 460줄 전체의 6.1 정체성 대조(`judge_sens` 933·947~948)가 status에 남는다.
5. **control 보고 4절**
   - (a) 1-9 범위 축소: 차단할 사안이 아니다(R-4). 다만 문면 두 곳이 아직 옛 요구를 적고 있다(M-a).
   - (b) 12a meta·폴더 결측 = `not_judgeable` 대 1-9 조건 2 = `setting_defect`: 통과 여부에는 영향이 없다(R-3). 실패는 상태 순서상 언제나 앞선다. 문면은 조건 2에 예외 한 줄을 더하기를 권고한다.
6. **정오 1 정합**
   - 인용이 실제와 같다: T′ sha 60ebb4a4…, 부모 c91065b7, T′ 보고 a607aef7, SUMS 36f223e7, 변경 4파일, 2658 통과, HEAD·`is_clean`.
   - 모든 파일:행 인용을 T′ 트리에서 다시 확인했다. 1-8·1-9·1-13·1-16·1-17의 행 번호가 모두 맞다.
   - '판정서에 옮길 것' 목록에는 빠진 것과 모순이 있다(M-a, M-b).
   - 도구 결과
     - `placeholder_scan --pattern-set both`: 8건, 모두 백틱 안의 명령 틀이다. `--skip-inline-code`로는 0이다(R-13).
     - `ref_check`: missing 3건, 모두 설명된다(R-12).
     - `seal_check --sums --rev e241638d --check-tracked`: raw 일치, `cited_ignored` 0. `cited_untracked` 85는 미커밋 근거 폴더다.
     - `baseline_check sums judge_commit_60ebb4a4`: 불일치·누락·목록 밖 0, `cited_untracked` 14.
7. **(E) 빈 집합: 통과로 새는 곳은 없다**
   - l1ref `--runs`
     - 4개보다 적으면 "L1 run … not given"이 `not_judgeable`에 들어간다(1552). 시험 `:998-1010`.
     - 0개는 argparse가 막는다(`nargs="+"`).
     - 줄이 0이면 "no line"(1570~1571), error 줄은 `not_judgeable`, meta가 없으면 정체성 문제 → `setting_defect`다.
     - gate_scan `missing_key_default_pass`(1562)는 오탐이다(1570~1571에 가드가 있다).
   - r79 조건
     - 판정 등급 줄 0 또는 읽기 0이면 결정 14대로 기록 "해당 없음"이다.
     - 이때 rev 6 J-P3의 판정 행 0 처리(판정 불가)는 그대로 남는다.
   - 남은 점은 R-5(줄 수 대조 없음)와 M-c(생산자 꼴 미시험)다.
8. **담당별 구분**
   - 차단 N-B1: control-expert(정오 문면과 경로 2 넘김 문장).
   - M-a·M-b: control-expert.
   - M-c: 메인 세션 권고(건식 확인). 시험을 더하려면 python-expert지만, T″이 필요하므로 지금은 권하지 않는다.

## 발견 사항(심각도순)

### [차단][R] N-B1 결정 14·1-20은 경로 2 범위의 판정 정의를 바꾸는데, 정오는 "경로 2 넘김은 바뀌지 않는다"고 적었다
- 근거
  - 봉인본 11절 1018행: "J-P3(③ rev 7)와 T-JR-12b는 판 6과 같이 경로 2 범위다".
  - 봉인본 1019행의 넘길 정의 문장: "… 판정 집합 추가(3.5), **조건 행 0 = 판정 불가** …".
  - 판 6 11절 772행: 경로 2는 "12b VBKL, 12a"의 J-P3도 판정했다.
  - 정오 1 13행: "경로 2 넘김은 바뀌지 않는다. 이 정오의 항목은 경로 1 실행 절차와 판정 도구(T) 요구다".
  - 그러나 다음 두 결정은 판정 정의다.
    - 1-13 결정 14: 12a·12b에서 조건 읽기 0 = '해당 없음(기록)'.
    - 1-20: r79 줄의 `t_event_s` 부재 = 사건 없음. 봉인본 3.5 507행·6.1 659행의 `setting_defect`를 r79 줄에 한해 좁혔다.
  - 1-20 근거 3(215행)도 "J-P3(③ rev 7)·T-JR-12b는 경로 2 범위"라고 인정한다.
  - ed7 경로 2 넘김 문서는 아직 없다(`ed7_design`, `j_p3_cause` 직접 Glob 0건).
- 실패 시나리오
  - 경로 2가 봉인 문장과 이 정오("넘김 불변")만 받는다고 하자. r79 줄에는 `t_event_s`가 구조적으로 늘 없으므로(1-20 사실 3) 다음처럼 갈린다.
    - 경로 2: 12a·12b ③ rev 7 조건이 `setting_defect`(3.5 507행) 또는 판정 불가(1019행)다.
    - 경로 1(T′): 같은 줄이 '해당 없음(기록)'이다.
  - 이 두 경로 불일치는 결과와 무관하게 **결정적으로** 생긴다. 12a·12b가 두 경로 일치 판정을 할 수 없거나, 한쪽을 골라야 하는 상황이 된다.
- 권장 조치(control-expert, 정오 봉인 전)
  - 13행을 고친다: "경로 2 넘김에 1-13(결정 14, 12a·12b 한정)과 1-20 1~2를 [정의] 문장으로 더한다. 그 밖은 바뀌지 않는다".
  - 봉인본 1019행 "조건 행 0 = 판정 불가"에 "(12a·12b는 1-13·1-20)" 단서를 정오 표에 넣는다.
  - 1-20 근거 3의 문장은 "사건 시각을 새로 정의하면 판정 집합이 바뀐다"로 좁힌다. 지금 문장은 '정의하지 않음'에는 넘김 변경이 필요 없다고 읽힌다.
  - 메인은 경로 2 넘김을 쓸 때 이 두 문장이 들어갔는지 확인한다. 넘김 전에는 `handoff_leak.py`로 상대 경로 이름 누설과 공통 블록 sha를 본다.

### [실행 전 수정][T] M-a 1-9에서 거둔 12a·12b 출처별 값 기록 요구가 두 곳에 남아 있다
- 근거
  - 정오 1 133행: "T′은 … 12a·12b 줄의 정체성도 같은 방식으로 출처별 값을 남긴다".
  - 같은 절 137행: "12a·12b의 출처별 값 기록 요구를 **거두고** l1ref 기록으로 대신한다".
  - 「판정서에 옮길 것」 6번(230행): "L1 기준·12a·12b 줄의 출처별 정체성 값". 14번(238행)과 모순이다.
  - 코드: `identity_source_values` 호출은 1577행 하나뿐이다.
- 실패 시나리오: 봉인 뒤 `judgement_checklist`가 6번을 12a·12b report에서 찾는다. report에 없는 값이라 missing이 되거나, 판정서가 없는 값을 인용하게 된다.
- 권장 조치(control-expert): 133행 마지막 문장을 지운다(또는 "12a·12b는 대조만"으로 고친다). 6번을 "T8 VBM0 실제 태그, L1 기준 4개의 출처별 정체성 값(l1ref)"으로 고친다.

### [실행 전 수정][T] M-b 「판정서에 옮길 것」에 빠진 공개 항목
- 근거
  - 머리말 17행의 공개: control-expert의 `04_scripts/03_control` `t_event_s` Grep이 옛 touch_phase c4g2 러너 JSON의 값 몇 줄을 화면에 냈다. 이것이 목록(224~238행)에 없다.
  - T′ 보고 5절의 공개(판 6 `79495405/l1ref_a1/L1_VBL.json` 줄·`base`·`r79` 키 이름, 하네스 종류 수, T4h 배열 이름 출력)가 정오 어디에도 없다.
  - 이 감사의 공개(맨 위 「본 결과」)도 없다.
- 권장 조치(control-expert): 목록에 "15. 머리말 공개(T′ 채움 때 Grep 화면 노출), T′ 보고 5절 공개, 재감사 공개"를 더한다. O7 번호를 붙일지도 정한다(O7-14·15 다음).

### [실행 전 수정][I·R] M-c 새 정체성 대조를 r79 생산 경로의 판 7 출력에 한 번도 돌려 보지 않았다(동어반복 시험뿐)
- 근거
  - C의 `05_tests/unit/test_ed7_*.py`에는 r79 경로(`r79_sensor_screen`·`las_t3_dg3`·`L1_VBM`) 시험이 없다(Grep 0건).
  - `test_ed7_harness.py:134-146`의 판 7 정체성·T4h meta 시험은 run_v5 줄(VBM_R12 등)만 본다.
  - T′의 l1ref·12a·12b 시험(`test_ed7_judge.py:952-1010`, 890~948)은 meta를 기대값 함수 `ed7.setting_identity()`로 만든다. 그래서 생산 쪽의 정규화(`meta_for_json` 이중 적용, 키 배치)가 다르면 잡지 못한다.
  - T′ 보고 2절의 "생산자 꼴 끝까지 실행"은 probe-repro·confirm·sens·j9main·cases뿐이다. t8·l1ref·12a·12b는 빠졌다.
  - 판 7 꼴 r79 출력은 아직 없다(`j9_runs/b46bdf8f`·`6bfb2560` 아래 json 0건).
  - 정황상 큰 위험은 아니다.
    - r79는 `r67.install_v5_setting` → `verdict_runs.install_plant_options`(`r67_g1_screen.py:546-561`)를 거쳐 run_v5와 같은 설치를 쓰고, meta는 `lock_start_b_meta`·`probe_d6_meta`(`r79_sensor_screen.py:1214-1215`)로 쓴다.
    - 조건 배열은 `extend_bound_check.trace_arrays()` → `jp3_*`(`extend_start_bound.py:1562-1564,1732-1755`)다.
    - 판 6 L1_VBL 167줄·npz 167개에서 `t_s`·`phase`·`jp3_*` 5종과 `meta_json`이 모두 있었고, 줄에는 `hydraulics_record.extend_bound_check`·`head_only_declared`가 있었다(`key_presence` 종료 0/1, 없는 키는 `t_event_s`·`lsb_components`뿐으로 예상대로).
- 실패 시나리오
  - 2단계(l1ref) 첫 판정에서 `lsb_settings`·`probe_d6_settings`의 정규화가 달라 결정적 `setting_defect`가 날 수 있다.
  - t8에서 R-10(③ 기록 없음)이 실데이터 꼴과 달라 결정적 `setting_defect`가 날 수도 있다.
  - 그러면 출력이 있는 상태에서 T″을 만들어야 한다(M-6의 문제가 다시 생긴다).
- 권장 조치(메인 세션 권고, 실행 1단계 전)
  - 출력 경로를 `j9_runs\8a2a52ce` 밖·C worktree 밖에 두고, r79 VBM·VBM0 각 1키와 ed7_t8 1쌍을 건식으로 돌린다.
  - 그 출력에 `key_presence.py --key controller_tag,hydraulic_options.p1_patch,hydraulics_record.extend_bound_check,run_extend_start_revision,head_only_declared,t4h_file`과 `--npz-dir … --array t_s,phase,jp3_t_s,jp3_class,jp3_plant_state,jp3_p_tr_Pa,jp3_used_bound_Pa,meta_json`을 돌린다.
  - 이어서 T′ `l1ref`·`t8`(stand-in `.done`, 판정 출력도 밖)을 돌려 정체성 문제가 0인지 확인한다.
  - 이 건식 출력은 판정에 쓰지 않는 기록으로 둔다.
  - 하기 어렵다면, 2단계 `.done` 직후 다른 단계를 시작하기 전에 T′ `l1ref`를 먼저 돌리는 순서를 정오나 실행 메모에 적는다.

### [기록]
1. **R-1(앞 감사 B-1 철회)**
   - 앞 감사 B-1의 두 주장은 모두 틀렸다.
     - "판정 행 260 ≠ 104로 결정적 `setting_defect`"
     - "기록 설정 J-P3 H-7이 감도 실패로 세어진다"
   - J-P3 공용 모듈의 설정 필터(`j_p3_inputs.py:250-261`)를 따라가지 않은 추적 오류였다. 정오 1-16의 사실 정정은 맞다.
   - T에서 status에 들어갈 수 있었던 것은 기록 줄의 줄 단위 결함 수뿐이다(위 4). T′ 변경은 범위를 명시한 것이고, 판정 결과를 바꾸지 않는다.
2. **R-2**
   - T′의 `J-P3_record_settings_judged_rows`는 구조적으로 늘 0이다. 기록 설정은 `REV5_JUDGED_SETTINGS` 밖이라 `rev7`이 `no_judged_runs`가 되기 때문이다. 시험 `:856`도 0을 단언한다.
   - 기록 설정의 침범은 `J-P3_record_settings.rev7_record_only.runs_with_breach`(`:855`)에 있다.
   - 「판정서에 옮길 것」 11번("침범이 있으면 그 내용")은 이 키를 읽게 적기를 권고한다.
3. **R-3(control 4절 (b))**
   - 12a `bundle_problems` 67~69·75~77행은 T4h 폴더나 meta가 통째로 없으면 `not_judgeable`이다. meta는 있는데 항목이 없으면 `ed7_identity_problems`가 `setting_defect`로 잡는다(415·418행).
   - VBM 쪽에서 T4h 파일이 없으면 조건 항목이 `setting_defect`다(539~543).
   - 그래서 실질 차이는 VBM0(기준 쪽)의 meta 결측이 `not_judgeable`로 남는 것뿐이다. 실패가 늘 앞서므로 통과 여부와 실패 은폐에는 영향이 없다.
   - 봉인본 6.1 673행("어긋나면 `setting_defect`")·조건 2와 상태 이름만 다르다. 1-9 조건 2에 "12a는 폴더·meta 통째 결측을 `not_judgeable`로 둔다(아래)"를 한 줄 더하면 문면이 맞는다.
4. **R-4(control 4절 (a))**
   - 1-9 조건 3을 l1ref로 축소한 것은 기록 요구의 축소이고, 판정 항목이 아니다.
   - 12a·12b의 대조 자체(조건 1·2)는 T′이 전부 한다: 12a 79~81행, 12b 80~94·218~231행.
   - 세 줄 종류가 같은 생산 함수(`run_job`·`write_t4h`)에서 나온다.
   - 차단이 아니고, T″도 필요 없다.
5. **R-5**
   - l1ref는 run마다 줄 수를 L1 키 파일(`l1_keys_12b.txt`·`l1_keys_d3c6c57e.json`)과 대조하지 않는다.
   - 같은 이름의 `--runs`가 둘이면 뒤 것이 조용히 덮는다(1551). 다만 단계 폴더 소속 검사가 다른 폴더를 거부하므로 실질 위험은 낮다.
   - 판정 후 감사에서 run별 `lines`를 키 파일 수와 대조한다.
6. **R-6(M-5)**: `--out` 위치는 help 문장(1631~1633)뿐이고 도구가 거부하지 않는다. 판정 후 감사에서 report의 `code_identity.is_clean`과 단계 폴더 `sums`의 목록 밖 파일 0을 본다.
7. **R-7(R-1 확장)**: `probe-repro --expect-spec-edition`(기본 10902ffd, 1621)과 모든 하위 명령의 `--run-commit`(1610)은 CLI로 바꿀 수 있다. 판정 후 감사에서 report `inputs.rows.run_commit` = C와 spec_edition 기대값을 대조한다.
8. **R-8**
   - `judge_commit_60ebb4a4\suite_T\suite_record.json`의 `worktree_tests_exit`는 1이다.
   - 원인은 경고뿐이다: `data_literal_not_rebased` 7건, `rebase_never_used` 1건(`worktree_tests.md` 101~112). pytest는 0이고, `junit_skips`로 2658/2658 통과, skip·xfail 0, critical_skipped 0이다.
   - T′ 보고에는 이 종료 1이 적혀 있지 않다. 판정서에 적을 때는 "경고 8, 시험 실패 없음"으로 적는다.
9. **R-9**: ed7-judge worktree의 lock 사유가 아직 "judge commit T c91065b7"이다. HEAD는 T′이다. 사유를 고치는 일은 메인 몫이다.
10. **R-10**: `jp3_12b_judge_ed7.py:264-267`에 `STEP_FILE_OPTIONS` 뒤 문자열 docstring이 둘 있다(앞 것만 docstring). 동작에는 영향이 없다.
11. **R-11**
    - 근거 폴더(`run_commit_8a2a52ce`, `suite_8a2a52ce`, `judge_commit_c91065b7`, `judge_commit_60ebb4a4`, `postseal`)와 정오 1은 미추적이다. `-text`는 걸려 있고 ignore에는 걸리지 않는다(`git check-ignore` 종료 1).
    - 1-19대로 정오 봉인 때 함께 커밋하고 `postseal` SUMS를 만든다.
    - 이 감사 원문을 `postseal`에 저장한 뒤 SUMS를 마지막에 쓴다.
12. **R-12**: `ref_check --rev 60ebb4a4 --exclude <블라인드 3·.claude·판 6 selection.json>`의 missing 3건은 모두 설명된다.
    - `d_grid_keys12.json`: 3ecf61f1 blob, 1-2 표에 그렇게 적혀 있다.
    - `j9_runs/p51_record_8a2a52ce/`: 앞으로 만들 예시 경로다.
    - `tools/verif/baseline_check.py`: 사용자 도구 `~/.claude/tools/verif`다. `~/.claude/` 접두를 붙이면 더 분명하다.
    - untracked 21건은 T′ 트리 밖(master 봉인물·미커밋 근거)이라 생긴 것이다.
13. **R-13**: `placeholder_scan`의 꺾쇠 8건은 모두 백틱 안 명령 틀이다(70·134·152·200행). 1-18(200행)의 `<T′ 앞 8자>`는 지금 `60ebb4a4`로 채울 수 있다.
14. **R-14**: 1-20 4(216행) "12a·12b에서 조건을 빼도 시드 제거 확인이 빠지지는 않는다"는 j9 계열에서 조건이 판정된다는 전제에 선다. 그 판정(조건 읽기 > 0)은 j9main·감도·확인·cases에서 0이면 판정 불가로 남는다(1-13). 문면과 도구가 같다.

## 규칙↔도구 대조표(이번 범위)
| 규칙 | T′ 위치 | 판단 |
|---|---|---|
| 1-8 T8 정체성·VBM0 태그 기록 | `judge_t8` 1305~1316, `ed7_identity_problems` 393~434 | 맞음(실데이터 꼴은 M-c) |
| 1-9 조건 1·2(r79 전부 대조, 결측 = `setting_defect`) | l1ref 1532~1546, 12a 57~82, 12b 80~94·218~231 | 맞음. 12a 통째 결측만 `not_judgeable`(R-3) |
| 1-9 조건 3(출처별 값) | l1ref 1577 | l1ref만. 문면 정리 필요(M-a) |
| 1-13 결정 14 | 562~573(r79), 512~521(j9 계열) | 맞음 |
| 1-16 결정 13 | `_sens_jp3` 1006~1032 | 맞음. 기록 침범은 `rev7_record_only`(R-2) |
| 1-17 결정 15 | 1475~1478 | 맞음 |
| 1-18 `--out` 위치 | help뿐 | 절차(R-6) |
| 1-20 사건 시각 부재 | 528~549(546) | 맞음 |
| 6.1 상태 순서 | `status_of` 283~291, 두 래퍼의 `problems.status()` | 맞음 |
| 11절 경로 2 범위 | 정오 13행 | **어긋남(N-B1)** |

## 확인 필요
- Q-1(N-B1): 결정 14와 1-20을 경로 2에도 [정의]로 넘기는지. 사용자 결정 14를 양쪽 경로에 같이 쓰는 것이 자연스러운 해석이고, 이 감사는 그렇게 가정했다. 경로 2는 봉인 문장 그대로 두고, 12a·12b ③ rev 7 조건을 두 경로 일치 대상에서 빼는 다른 길도 있다. 어느 쪽이든 정오에 적어야 한다.
- Q-2(M-c): 1단계 전 r79·t8 건식 확인을 할지, 2단계 직후 l1ref 판정을 먼저 하는 순서로 대신할지.

## 위임 필요
- control-expert(정오 1, 봉인 전)
  - N-B1: 13행, 1019행 단서, 1-20 근거 3 문장
  - M-a: 133행, 목록 6번
  - M-b: 목록 15번
  - 권고: R-2(11번 키 이름), R-3(조건 2 예외 한 줄), R-13(200행 채움)
- 경로 2 넘김 작성자(메인이 정함): N-B1 문장 반영
- python-expert: 없음(T″ 불요)

## 메인 세션 권고
1. 정오 1을 위 문면대로 고친 뒤 sha를 다시 재고 `.sha256`을 만든다. 근거 폴더 5개와 함께 커밋한다(커밋 전 `git status --ignored`). `postseal` SUMS는 이 감사 원문을 저장한 뒤 마지막에 쓴다.
2. M-c 건식 확인(Q-2 답에 따라)을 실행 1단계 전에 한다. 출력은 C worktree 밖, `j9_runs\8a2a52ce` 밖에 둔다.
3. ed7-judge lock 사유를 T′로 갱신한다(`git worktree lock --reason`은 먼저 unlock이 필요하니 판정 전 시점에 한다).
4. 앞 감사 권고 1~10(배치·단계별 SUMS·c92·c93 확인·`--step-done`·`--spec`·`log_errors`·`key_presence`)은 그대로 유효하다. 판정 명령에는 `l1ref --runs <4개> --step-done <l1ref .done> --out <T′ worktree 밖·단계 폴더 밖>`을 더한다.

## 검사하지 못한 것
- T′ 판정 도구를 실제 판 7 데이터에 돌리지 않았다(출력 없음, 본 실행 금지). l1ref·t8·12a·12b의 실데이터 동작은 코드 추적과 판 6 키·배열 존재로만 보았다(M-c).
- 경로 2 도구와 넘김(아직 없음)은 보지 않았다.
- `verdict_runs.install_plant_options`가 r79 제어기에 D6 설정을 넣는 경로는 함수 호출까지만 따라갔다(run_v5와 같은 함수라는 데까지).
- T′ 시험 범위 84파일 목록(`t_test_range.txt`)은 다시 도출하지 않았다. junit 2658건만 확인했다.

## 실행한 검증
- 인터프리터: python-dev `-I -B`(`MKL_THREADING_LAYER=TBB`). 프로젝트 env와 판정 도구 import는 쓰지 않았다.
- git(조회): `rev-parse`(부모·03_src tree), `diff --name-status/--stat/본문`(C→T′, T→T′, 판정 파일 3개), `cat-file --batch-check`(목록 155 × C·T′), `check-attr text eol`, `check-ignore -v`, `status --porcelain`(두 worktree, 모두 clean), `worktree list --porcelain`.
- 해시: `Get-FileHash`로 명세·정오·T′ 보고·SUMS·앞 감사·control 보고를 쟀다. python으로 정오의 CRLF·BOM을 셌다.
- 도구(`~/.claude/tools/verif`)
  - `seal_check --sums ×5 --rev e241638d --check-tracked`: raw 일치, `cited_untracked` 85, `cited_ignored` 0
  - `baseline_check sums judge_commit_60ebb4a4`: 불일치·누락·목록 밖 0, `cited_untracked` 14
  - `placeholder_scan --pattern-set both`: 8 → `--skip-inline-code` 0
  - `ref_check --rev 60ebb4a4 --exclude …`: missing 3(설명됨), untracked 21
  - `junit_skips suite_T`: 2658/0/0
  - `gate_scan` T′ 3파일: warning 5, 코드로 판별(row path 3건은 절대 경로라 오탐, l1ref는 가드가 있어 오탐, `unit_verdicts`는 앞 감사 R-9)
  - `key_presence`(판 6 L1_VBL 줄 키, npz 배열 이름): 값은 출력하지 않음
- 즉석 스크립트: `scope.py`(목록 blob 대조). scratchpad `verif-ed7Tp\`에 두었고 폴더째 지웠다(Test-Path False).
- 메모리: `audit_pitfalls.md`에 한 항목, `MEMORY.md` 색인 한 줄을 Edit로 더했다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v7.md 10902ffd…, jp3_remedy_spec_v7.md.sha256 8cfd1981…, jp3_remedy_spec_v7_erratum1.md df5a5dfe…, handback_T_prime_60ebb4a4.md a607aef7…, handback_erratum1_Tprime_fill.md 83507be0…, audit_prerun_T_erratum1_20261125.md 8c9800c9…, SHA256SUMS 36f223e7…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
