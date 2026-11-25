## 감사 요약
- 본 결과: 판정 결과는 열지 않았다. 다음 파일은 판정에 쓰지 않는 방식으로만 읽었다(봉인 전에 공개된 설계 입력이다).
  - `fixed_table_a2.json`: verdict 종류별 건수, R15 나빠짐 플래그, missing·None 필드 수
  - `table7_proposal_all_arms.csv`: `commands_sha256` 열만
  - 키 파일 셋: 플래그와 건수
  - `condition*.json`: 최상위 키 이름
  - 이 보고에는 판정 수치를 옮기지 않았다.
- 대상: 436.9 J-P3 판 7 봉인 전 감사(시점: 실행 전, 봉인 전)
  - 명세 `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\jp3_remedy_spec_v7.md`. 개정 6, sha256 6dcccae2를 실측했고 지시값과 같다. 1036행, LF, BOM 없음, `-text`(text: unset)이다.
  - 도구: worktree ed7-impl HEAD b46bdf8f, 작업 트리 clean.
- 판정: **차단 2 / 실행 전 수정 8 / 기록 13**. 이대로는 봉인할 수 없다.
  - 차단 2건은 명세 문면을 고치거나 결과를 기재하면 풀린다. 다시 실행할 필요는 없다.
  - 실행 전 수정 8건 중 M-1~M-5는 봉인 전 문면 수정이고, M-6·M-7은 봉인 커밋과 run steps 몫이다. M-8은 봉인 전 실행을 권고하는 항목이다.

## 발견 사항 (심각도순)

**[차단][R·I] B-1. "봉인 뒤 도구 커밋"과 실행 커밋 범위 관문(P7-10)이 서로 맞지 않는다. 판정 도구가 어느 커밋에 들어가고 어떤 관문을 거치는지 정의가 없다.**
- 근거
  - 명세 548행 4절 4: "봉인 뒤 도구 커밋: J7 새 비교, 교착 서명, ③ rev 7 판정 키·`plant_seed_artifact` 분류, 확인 단계 키 목록 대조, G1 run_id int"
  - 8절 896~907행 Y7-5·Y7-6: 고정 표 입력, `probe_run`, 재현 대조, 단위 시험
  - 570행 P7-10: "실행 커밋 C의 b46bdf8f 대비 diff는 5.1의 (i)~(iv)뿐 … 그 밖의 변경이 있으면 멈춤"
  - 583행: "담는 것은 (i)~(iv)뿐이다. 그 밖의 코드는 바꾸지 않는다"
  - 589행: P7-3·P7-9 재현은 "C에서 … `commands_sha256`과 **단위 판정**을 대조"한다. 단위 판정에는 봉인 뒤 도구가 필요하다.
  - b46bdf8f의 `jp3_ed7_rules.cluster_judgement`(176~197행)에는 고정 표 합산 경로가 아직 없다.
  - 판 6은 이 공백을 4a로 막았다(판 6 명세 378~386행): 도구 커밋마다 단위 시험과 verif 감사를 거치고, 그 전에는 해당 단계를 판정 불가로 둔다.
  - 판 7의 이어받기 조항(235행 "부록 A의 원문을 그대로 이어받는다")에서 부록 A(1029~1036행)에는 4a가 없다.
- 실패 시나리오
  - 도구를 C에 넣으면 P7-10에서 멈춘다.
  - 도구를 C 뒤의 별도 커밋에 넣으면 그 커밋은 P7-4 suite 밖이고, 감사 관문도 없다. 검증되지 않은 도구로 P7-9 재현과 감도·확인 단계를 판정하게 된다.
  - 어느 쪽이든 봉인 뒤 정오가 생긴다.
- 권장 조치(control-expert 문안): 5.1에 판정 도구 커밋 T를 정의한다.
  - T의 부모 커밋과 허용 경로를 정한다(`04_scripts` 판정 도구와 `05_tests`만 허용, `03_src`와 실행 경로 모듈은 C와 같아야 함).
  - 실행은 C, 판정은 T에서 한다.
  - T에서 돌릴 시험 범위를 정한다(P7-4 꼴).
  - T 뒤에 verif 감사를 둔다.
  - 판 6 4a처럼 "T와 감사 전에는 해당 판정 단계는 판정 불가"를 넣는다. 걸리는 단계: P7-3·P7-9 단위 판정, 6.2, 6.3, J7, ③ rev 7, G1.

**[차단][R·T] B-2. 봉인 전 조건인 "probe 몫 판단"의 결과와 도구 대조가 명세 어디에도 없다.**
- 근거
  - 547행 4절 3: "봉인: **probe 몫 판단**·조건 3 채택·예측 표·확인 단계 키 목록과 seed 뒤"
  - 526행: "몫 판단 규칙: 판 6 4절 2와 같다(동률이면 남김, 발동 0일 때만 뺌). 실제로 쓸 도구의 규칙을 문면과 대조해 공개한다."
  - 999행: "probe 결과 전부와 몫 판단, 조건 3 채택 결과(봉인 전 채움)"
  - 명세와 `ed7_design\**\*.md`에서 "몫 판단·a5·a6·발동 0·동률"을 Grep했다. 조건 3 채택(4.2, 539~545행)만 있고, 팔 a5(2 − B3)·a6(2 − A(i))의 몫 판단 결과·발동 수·도구는 0건이다.
  - 3.6의 486행은 구성 요소를 {A_i, A_ib, A_ii, B3}로 정해 두었다. 그 근거 단계가 비어 있다.
- 실패 시나리오: probe에서 B3나 판 6 A(i)의 발동이 0이었다면, 규칙상 그 요소를 빼야 한다. 그러면 봉인 구성과 판정 설정이 바뀐다. 지금 문면으로는 확인할 수 없다.
- 권장 조치(control-expert, 필요하면 python-expert 도구 실행): 4.2에 몫 판단 결과를 적는다.
  - 요소별 발동 수, 팔 2 대 팔 5·6의 V0 대비 실패 단위
  - 쓴 도구와 그 sha
  - 규칙 문면 대조 공개
  - 결과를 본 뒤 정했다는 표시(12절)

**[실행 전 수정][S] M-1. 봉인 전에 채우기로 한 자리가 남아 있다.**
- 221행: hydraulics_v7 `SHA256SUMS`가 "메인 갱신 중, `3b88e4a8…` 계열; 봉인 전에 최종 sha 기입" 상태다. 현재 파일 sha 앞 16자는 3b88e4a87f9a8df8이다.
- 199행의 "봉인 전 확인 필요: 없음"과 어긋난다.
- placeholder_scan(`--pattern-set both --skip-inline-code`)은 종료 0이었다. 이 산문 자리는 도구가 잡지 못한다.
- 조치(control-expert): 전체 sha를 기입한다.

**[실행 전 수정][S] M-2. 개정 3 근거 표의 폴더 SUMS sha 두 개가 현재 파일과 다르다.**
- 41행 control_v7_review `d62c22ea…`는 현재 `ad37ad0e…`다. 이 파일은 09:38에 바뀌었고, 명세 최종 저장(09:37)보다 늦다.
- 42행 hydraulics_v7_review `8ff7c74b…`는 현재 `20028dd1…`다.
- 개별 파일 sha(41c99910·e9827b14)는 맞는다. 폴더에 handback이 더해져 SUMS가 바뀐 것이다.
- 조치: "개정 3 시점 값"이라고 표기하거나 현재 값으로 바꾼다.

**[실행 전 수정][R·E] M-3. 감도 `probe_seen` 범위 수정 방안이 봉인되는 키 파일 sha와 맞지 않는다.**
- 문면
  - 897행: "키 목록에 `probe_run` 플래그를 두거나, 기록 6설정의 `probe_seen`을 거짓으로 고친다"
  - 196행: "봉인 뒤 도구 커밋 몫"
- 봉인 대상: 578행 `ED7_KEY_FILE_SHA256["sens_keys_ed7.json"]` = be930b75…
- 실측
  - 봉인할 `sens_keys_ed7.json`은 460줄이다. `probe_seen` 참은 10설정 × 10 = 100줄이고, 기록 6설정도 각 10줄씩 참이다.
  - `run_v5.sealed_key_jobs`(419~437행)는 sha가 다르면 SystemExit로 실행을 막는다.
- 실패 시나리오: 키 파일을 고치면 sha가 달라져 실행이 거부된다. 상수를 바꾸면 P7-10에서 멈춘다. 고치지 않고 도구가 기록 6설정을 본 단위로 읽으면, 없는 고정 표 값을 찾다 `setting_defect`가 난다.
- 조치(control-expert 문안): 수정은 판정 도구에서만 한다고 명세에 고정한다. 본 단위 = SENSITIVITY_JUDGED ∧ `probe_seen`이고, 키 파일은 그대로 둔다.

**[실행 전 수정][I] M-4. "03_src diff는 한 줄"(P7-10) 문구와 상수 docstring이 충돌한다.**
- `extend_start_bound.py` 197행이 상수다.
- 198~201행 docstring: "PROVISIONAL: the draft revision 2 (85ce6e2a...) … the seal replaces it".
- 값만 바꾸면 docstring이 틀린 설명으로 남는다. docstring을 고치면 P7-10에서 멈춘다.
- 조치: P7-10에 "그 상수 정의(값 줄과 docstring)"를 허용하거나, docstring을 그대로 둔다고 명시한다.

**[실행 전 수정][T] M-5. 12절(판정서에 옮길 것) 공개 목록이 빠졌다.**
- (a) 961행은 "O7-1~O7-7", 979행은 O7-8·O7-9만 옮긴다. O7-10~O7-13은 12절에 없다.
- (b) 결정 9(x·y)의 출처와 시점이 12절에 없다.
  - y는 판 6 관측 비율을 올린 값이고, x는 귀무 기대다. 둘 다 판 7 구현 모형의 예측이 아니다.
  - 정한 시점은 고정 표·G1 추출 뒤이고 G1 실행 전이다.
- (c) seed 고정의 근거 고리가 명세에 없다.
  - seed는 명세 초안 sha 305bbb91…(키 manifest 38~41행이 입력으로 고정)에 들어 있었다.
  - 그 초안은 키 생성(08:37:35) 전인 `handback_spec_rev6.md`(08:36:33, 5~6행에 sha 305bbb91·seed 20261126)에 기록돼 있다.
- (d) 987행 제목 "G1 seed와 고정 표 해석은 결과를 본 뒤 정했다"와 본문("추출 결과 전에")이 어긋난다.
- 조치(control-expert): 12절에 O7-10~O7-13, x·y 출처, 305bbb91 인용을 넣고 987행 제목을 고친다.

**[실행 전 수정][S·I] M-6. probe 출력 폴더에 해시 목록이 없고, npz가 ignore에 걸린다(봉인 커밋 몫).**
- `j9_runs\6bfb2560\ed7_probe_a1\`
  - `6bfb2560_LOCAL_ONLY.SHA256SUMS`에는 jsonl 하나만 있다(1107b309, `.git/info/exclude:107`).
  - condition.json(결함 판), condition_ad7a716e.json(고정 표 입력, manifest 기준 9bd2dba8), adoption_9d8e78a4/b46bdf8f.json(544행 인용, sha 없음), identity·progress json은 어떤 SUMS에도 없다.
  - T4h npz 654개는 `.gitignore:41 *.npz`에 걸린다. 합계 143.3 MB, 파일당 최대 0.5 MB라 `git add -f`가 가능하다.
- `condition.json`과 `condition_ad7a716e.json`에는 코드 정체성(head) 필드가 없다. 결함 판과 수정 판은 파일 이름으로만 구분된다.
- 조치
  - 메인: 폴더 SUMS를 만든다(`baseline_check write-sums`). npz는 `git add -f` 또는 LOCAL_ONLY 목록에 넣는다. SUMS나 README에 "condition.json = 6bfb2560 도구 결함 판, 판정에 쓰지 않음"을 적는다.
  - python-expert: 봉인 뒤 도구에서 조건 도구 출력에 head·is_clean을 넣는다.

**[실행 전 수정][I·E] M-7. D 24줄 재실행 출력 경로가 이어쓰기와 이미 한 줄 건너뛰기 때문에 실제로 재실행되지 않을 수 있다.**
- `ed7_probe.run_batch`는 `done = run_v5._done_keys(out)`로 이미 있는 키를 건너뛰고 `out.open("a")`로 이어 쓴다.
- P7-3(589행, C에서 a2 114행, D 24 포함)과 확인 단계(554행 `--part d --out <확인 단계 출력 폴더>\ed7_probe_d.jsonl`)가 같은 24줄을 두 번 돈다.
- 같은 경로를 쓰면 확인 단계는 0줄을 돌고 앞 출력을 재사용한다.
- 조치(python-expert, run steps (iv)): 단계별로 새 출력 경로를 쓰고, 경로가 이미 있으면 거부하게 한다(판 6 328349a9 꼴).

**[실행 전 수정][I] M-8. 봉인 뒤 재현 관문(P7-3·P7-9)이 봉인 전에는 일부만 확인됐다.**
- b46bdf8f에서 6bfb2560 줄과 commands를 대조한 것은 8 job뿐이다(`tool_b46bdf8f\checks\probe_repro_compare.json`, 872행).
- 봉인 뒤 하나라도 다르면 `setting_defect`이고 그 단계는 판정 불가다(569행·631행·653행).
- 감도 단계는 고정 표(P7-<plant>-a2 이름)와 실제 `VBM<key>` 이름의 줄을 commands로 대조한다.
  - 옵션 dict는 import로 확인한 결과 5/5 동일하다(dynamics-dev, 아래 실행한 검증).
  - 이름이 다른 두 설정의 commands가 같음을 단언하는 시험은 없다. [추정] 위험은 낮다.
- 조치: 아래 "메인 세션 권고"의 봉인 전 실행.

**[기록][I] R-1. O7-10(블라인드 파일 이름 3개 노출): 차단 아님.**
- 노출된 것은 이름과 키 `ext_starts`가 있다는 사실뿐이다. 값은 노출되지 않았다.
- 블라인드 폴더는 git 추적이라 worktree마다, 앞으로 만들 C에도 사본이 생긴다.
- 12b 도구는 접두로 막는다. `jp3_12b_plan.py` 187~244행(`ED7_BLIND_PREFIXES`·`_unblinded_files`·`excluded_files`)에서 확인했다.
- 판정서에 공개하는 것은 M-5에서 다룬다.

**[기록] R-2. O7-11·O7-12·O7-13**: 출력 노출은 없다고 보고됐다. 순회 가능성 공개로 충분하다.

**[기록][E] R-3. suite 첫 시도 중단**
- 중단된 첫 시도의 로그는 `[start] suite-base` 한 줄에서 끝나고 release가 없다. 중단 전 결과로 쓴 것은 없다.
- 다시 돈 suite: base 79495405는 3588 s, run b46bdf8f는 3775 s, 둘 다 `.done exit=0`이다.
- `junit_skips --critical "test_ed7_|test_jp3_|test_extend_start_bound|test_lock_start_b|test_run_v5"`의 `critical_skipped`는 0이다. 실패 2건과 skip 15건은 기준 목록 범위다.
- 공개 문단(985행)으로 충분하다. P7-4는 C에서 다시 한다(587행).
- `suite_record.json`에는 is_clean이 없다. C의 P7-4 기록에는 넣기를 권고한다.

**[기록] R-4. 낡은 문구**
- 163행 "Q7-C10(x·y) 열림"과 1016행 "닫힘"이 다르다.
- 210행 "봉인 전에 커밋 blob과 대조": 이미 끝났다. f2fddc68의 blob 00bca52b가 작업본 hash-object와 같다.
- 999행 "(봉인 전 채움)".
- 872행 "봉인 전 P7-3에서 … 실행 커밋으로": 봉인 뒤 일이다.
- O7-13이 O7-12보다 앞에 있다.

**[기록][R] R-5. ③ rev 7 조건 행 수를 셀 수 있는 단계가 아니다.**
- 472행·596행은 "키 목록 단계에서 행 수를 센다"고 하지만, 키 파일만으로는 셀 수 없다. T4h가 필요하다.
- 도구 `jp3_rev7_condition.summarize`(242~270행)는 판정 때 0이면 `not_judgeable`로 둔다. 빈 집합이 통과로 가지는 않는다.

**[기록][I] R-6. 판정 플랜트 판별 기준**
- `jp3_rev7_condition.is_judged_plant`(173행)는 옵션에 `p1_patch`가 있으면 판정 플랜트로 본다. 이름 비교가 아니라서 좋다.
- VBM0·VBKM0도 판정 플랜트로 걸린다. 그 줄이 섞이면 `setting_defect`로 막히는 쪽이다. [추정]

**[기록] R-7. 개정 2~5 원문과 초안 305bbb91은 sha만 있고 원문이 보존되지 않았다.**
- 8~11행이 `quoted_unresolved`로 나온다.
- 고정 표 입력은 개정 5 `ebb79469`이고 manifest에 고정돼 있다.

**[기록] R-8. V0 `06_analysis\03_hydraulic\coupled\v5\main.jsonl`은 `.git/info/exclude:23`에 걸린다.** 판 6부터 그랬다. sha 9ad74990은 manifest에 고정돼 있다.

**[기록] R-9. D 키 blob(3ecf61f1)은 master에 병합되지 않은 ed6-records 브랜치에만 있다(worktree는 lock 상태).**
- blob sha를 실측했고 a995abff…로 같다.
- 시험 `test_probe_d_keys_equal_the_record_part_d_blob`은 blob에 닿지 못하면 skip한다. 그러면 P7-4의 새 skip으로 잡힌다.
- 브랜치는 유지해야 한다.

**[기록] R-10. `tool_a6fc3dd5\SHA256SUMS`에 `handback_python_impl.md`가 없다.** 223행이 인용하는 파일이다.

**[기록][T] R-11. 시간 근거가 모두 mtime뿐이다.**
- timeline에서 `mtime_only_basis` 4건, `seal_time_missing` 1건이 나왔다.
- 키·고정 표 manifest에 생성 시각 필드가 없다. 순서는 해시 사슬(키 manifest → 초안 305bbb91, 고정 표 manifest → 개정 5)과 handback mtime으로 뒷받침된다.

**[기록] R-12. suite 핵심 패턴(`suite_judgement.json` core_patterns)에 `test_ed7_*`가 없다.** 새 시험은 기준 목록 면제가 없어서 실해는 없다.

**[기록] R-13. 채택 도구가 "팔 3·4 둘 다 만족"이면 `undecided`를 낸다(`ed7_condition3_adoption.py` 457~461행).** 명세 544행이 공개한다. 실제 결론은 a2라 영향이 없다.

## 규칙↔도구 대조표
| 항목 | 명세 | 도구(b46bdf8f) | 결과 |
|---|---|---|---|
| 조건 3 고정 해석 | 531~536행 | `ed7_condition3_adoption.py` 113~114행 `FIXED_READING_VALUES` (j7 ed7_new, sens_exempt는 감도 플랜트에만, vbm5, known_shots, n_rev sum) | 같음 |
| J7 예외 | 605~608행 | `jp3_ed7_rules.py` 40~44행 `J7_EXEMPT_WARNINGS`={STIFFNESS}, 119~121행 빈 집합은 예외 아님 | 같음 |
| head_only | 476~479행, 597행 | `jp3_rev7_condition.py` 177~222행 (meta → 줄 → event 경로, 모순은 판정 플랜트에서 setting_defect) | 같음 |
| 상태 순서 | 599행 | 같은 파일 247~256행 (fail > setting_defect > not_judgeable, 조건 읽기 0이면 not_judgeable) | 같음 |
| 군집 규칙 | 618~620행 | `cluster_judgement` 176~197행 (단위 0이면 not_judgeable) | 같음. 고정 표 합산은 아직 없음(B-1) |
| G1 플래그 | 912행 | 키 파일: `counted_for_k` 거짓 3줄은 U832 세 군집, `judged_fault_jp3` 171줄 모두 참, 171/168/171, run_id는 str 171 | 같음 |
| G1 추출 | 657~660행 | 독립 재도출(`default_rng(20261126)`, 정렬 군집, 섞임 3·후보 없음 18 제외): 171/171 같은 오프셋 | 같음 |
| 12b 블라인드 | 926행 | `ED7_BLIND_PREFIXES` 187~191행, `_unblinded_files`, `excluded_files` | 같음 |
| D 24줄 명령 | 554행 | `ed7_probe.py --part d --list`는 24, `--part all --list`는 654 | 같음 |
| 키 파일 sha·상수 | 578행·918행 | sens be930b75, G1 684054ab, pool 07dd1374, probe 189dbb13, D a995abff를 모두 실측 | 같음 |
| 7절 cmd·판정 열 | 729~850행 | CSV a2 행 114/114가 commands 앞 8자 일치. 고정 표 64/64 일치, 단위 판정 64/64 일치, 범위 밖 50 | 같음 |
| P7-10 | 570행 | docstring 198~201행 | M-4 |
| 봉인 뒤 도구 커밋 | 548행 | P7-10·583행과 충돌 | B-1 |

## 재집계 표(값 비공개, 일치 여부만)
| 항목 | 명세 | 재집계 | 판단 |
|---|---|---|---|
| 고정 표만으로 6.2 실패 여부 | 실패 아님 | 2위상 이상 실패한 군집 0, 단독 실패 ≤ k, R15 나빠짐 플래그는 4설정 모두 거짓 | 같음 |
| 고정 표만으로 6.3 실패 여부 | d = 0, J-P3a·FAULT 0 | D VBM 실패 0, 조건 침범 0, 줄 J-P3a 0, fault_reasons 0 | 같음 |
| 고정 표 결측 | 0 | verdict missing 0/40, v0_verdict missing 0/24 | 같음 |

## 확인 필요
- B-1: 판정 도구 커밋 T의 위치(C의 자식인지, 별도 브랜치인지)와 실행·판정 커밋 분리를 사용자가 정해야 한다.
- B-2: 몫 판단 결과가 기록 없이 이미 판단됐는지, 아직 하지 않았는지.

## 위임 필요
- control-expert: B-1·B-2·M-1~M-5·R-4·R-5의 명세 문면
- python-expert(봉인 뒤 도구 커밋): M-3(본 단위 = 판정 4설정 ∧ `probe_seen`, 키 파일 불변), M-6(조건 도구 출력에 head·is_clean), M-7(run steps 새 경로 거부)
- 메인: M-6의 SUMS와 `git add -f`

## 메인 세션 권고
- (M-8, 봉인 전) b46bdf8f clean worktree에서 `ed7_probe.py --arms a2 --part all`(114행)을 새 출력 경로로 돌린다. 그 출력과 `j9_runs\6bfb2560\ed7_probe_a1\ed7_probe.jsonl`의 a2 줄을 `commands_sha256`로 전부 대조한다. compute-scheduler-expert 배치표를 거친다.
- 가능하면 감도 4설정의 본 단위 10키를 `VBM<key>` 이름으로도 1회 돌려 P7 이름 줄과 commands를 대조한다.
- 봉인 커밋 전에 `git status --ignored`로 볼 목록
  - `j9_runs\6bfb2560\ed7_probe_a1\ed7_probe_t4h\*.npz` 654개: `.gitignore:41`, `add -f` 필요
  - `ed7_probe.jsonl`: exclude:107, LOCAL_ONLY
  - V0 `main.jsonl`: exclude:23
  - `ed7_design\**`와 명세: untracked이지만 ignore는 0이다(seal_check `cited_ignored`는 jsonl 1건뿐).

## 검사하지 못한 것
- `ref_check.py`는 돌리지 않았다.
  - 블라인드 폴더가 git 추적이라 후보 이름 목록에 블라인드 이름이 나올 수 있다. 이 도구에는 제외 옵션이 없다.
  - 대신 명세의 백틱 경로를 블라인드 패턴을 먼저 빼고 직접 경로로만 확인했다. 경로 형태 참조는 모두 있고, 없는 것은 맥락상 맨 이름과 3ecf61f1 blob 경로뿐이다.
- 봉인 뒤 판정 도구(J7 CLI, G1·감도 판정, 고정 표 합산)는 아직 없어서 E·R축을 보지 못했다. T 커밋 뒤 감사 대상이다.
- `key_presence`로 b46bdf8f 신규 기록 키·배열이 실제 출력에 있는지 보지 못했다. 6bfb2560 출력에는 원래 없는 키다. `tool_b46bdf8f` 8 job 확인에 의존했다.
- run steps(iv)와 ps1이 아직 없어서 `ps1_lint`·`log_errors`·`placeholder_scan`(실행 자료)은 해당 없다.

## 실행한 검증
- 인터프리터
  - python-dev `-I -B` + `MKL_THREADING_LAYER=TBB`: verif 도구와 즉석 스크립트
  - dynamics-dev `-I -B` + `PYTHONDONTWRITEBYTECODE=1`: `ed7_probe --list` 2회, 설정 옵션 동일성 import 1회. 판정 함수는 쓰지 않았다.
- 도구
  - `seal_check.py --quoted/--hash-files/--sums --check-tracked`: 종료 1
    - SUMS 17개 불일치 0
    - quoted_unresolved 130건 = 7절 cmd 112 + 개정 sha·M-2·외부 파일. 외부 파일은 따로 확인해 모두 같았다(57d0faa7, 07a003ba, 06ed0384, 9ad74990, 4e80e69b, a995abff, 00bca52b).
  - `baseline_check.py sums` × 17: 모두 mismatch 0·missing 0
  - `placeholder_scan.py --pattern-set both --skip-inline-code`: 종료 0
  - `junit_skips.py`
  - `gate_scan.py`(ed7 도구 5개): 경고 3건은 모두 코드를 읽어 거짓 양성으로 판단했다(rev7 summarize 255행, stall 145행 창 비지 않음, warn_j7_effect 514행 앞 가드).
  - `timeline.py`
  - git 조회: log, ls-tree, check-ignore, check-attr, merge-base
- 만든 뒤 지운 파일: scratchpad `verif-ed7seal\`의 즉석 스크립트 12개, seal.json·gate.md·timeline.md·guard.json. 폴더째 지웠다.
- 절차 공개
  - Bash에서 파이프(`ls … | grep -v`, `ls | wc -l`)를 2회 썼다. 정의 규칙 위반이고, Suspended는 생기지 않았다.
  - worktree의 `__pycache__`는 03:53 suite 때 생긴 것이다. 내 실행 뒤 새 pyc는 없다.
  - source_guard가 ed7_design 폴더 mtime 변경 1건을 경고했다. 디렉터리 목록은 같고, 내가 쓴 것이 아니다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v7.md 6dcccae2…, jp3_remedy_spec_v6.md 07a55e17…, jp3_remedy_spec_v6.md.sha256 e216a6ab…, jp3_remedy_spec_v6_erratum1.md 1d4f7539…, jp3_remedy_spec_v6_erratum2.md 20a60e57…, jp3_remedy_spec_v6_erratum3.md bae389a3…, jp3_ed6_judgement_79495405.md e40c35d4…, SHA256SUMS ad37ad0e…, SHA256SUMS aaa00b00…, SHA256SUMS 4ef909ed…, SHA256SUMS 4160cafb…, SHA256SUMS 3b88e4a8…, SHA256SUMS 20028dd1…, SHA256SUMS ede263c5…, SHA256SUMS b8fad2e1…, SHA256SUMS e94a8f0f…, SHA256SUMS aa765826…, SHA256SUMS 4e4779e4…, SHA256SUMS 37376a81…, SHA256SUMS 2f712058…, SHA256SUMS 0f793271…, SHA256SUMS 4e87e43e…, SHA256SUMS 630c6b66…, SHA256SUMS 71b3ffc5…, confirm_g1_grid171.json 684054ab…, g1_pool_ed7.json 07dd1374…, handback_keys.md 2ba3b868…, manifest.json 71646a3e…, sens_keys_ed7.json be930b75…, verify_g1.json 92bf0e26…, verify_g1.py 063292aa…, fixed_table_a2.csv 89190eec…, fixed_table_a2.json f7754a69…, fixed_table_rule_check.py 08428563…, fixed_table_rule_check.txt d7e576d2…, fixed_table.py 61341a66…, handback_fixed_table.md 477fb051…, manifest.json 1f0c891d…, 디렉터리 목록 동일, ~$ 임시 파일 없음) · 경고: 형제 항목 수정 시각만 변경 1건(ed7_design)
- 메모리 갱신: `C:\Users\jinbeom\.claude\agent-memory\verif-protocol-auditor\audit_pitfalls.md`에 1항목, `MEMORY.md` 색인 줄을 갱신했다.
- 사용한 스킬: 없음
