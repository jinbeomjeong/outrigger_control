## 감사 요약
- 본 결과: `ed8_design\p816_prerun_41e107e9\p816_compare.json`의 status·equal·keys·arm별 counts(1단계 구현 관문 P8-16 사전 실행 판정)와 `run_identity_end.json`의 head·is_clean. 같은 폴더 `p816.jsonl`에서는 키가 있는지와 r79 줄의 T4h 경로 형태만 셌고(값 비출력), r79 T4h 2개의 meta에서는 키 **이름**만 읽었다. 판 8 판정 대상 결과(census·G′·12a/12b)는 아직 없다.
- 감사 대상
  - 시점: 실행 전(판 8, C8·T8 커밋 뒤, 4단계 착수 전)
  - 규칙: S8-R `jp3_remedy_spec_v8_rules.md`(sha256 35f9eba8, `.sha256` 일치, master 2715230e)
  - 커밋: C8 56849248(ed8-impl, 잠금), T8 ecf6c142(ed8-judge, 잠금), 구현 66648ea8·27c0f046·41e107e9
- 판정: **차단 3 / 실행 전 수정 5 / 기록 9**
- **4단계 착수 불가.** 규칙 4절 3단계 "T8 + verif 감사 — 감사 차단 > 0이면 멈춤"(spec:200)과 11.2 "T8과 감사 전에는 4·6·8~10단계 판정 불가"(spec:354)에 해당한다.
  - 진행 조건: T8′(B-1·B-2·B-3·M-2 수정)를 만들고 재감사에서 차단 0을 받는다.
  - 먼저 B-1 처리 방향을 정해야 한다. 그 방향이 C8을 바꾸는 쪽이면 C8 교체(사용자 승인)와 1단계 재시작이 필요하므로, 방향이 정해지기 전에는 4단계 실행도 띄우지 않기를 권한다.

## 발견 사항 (심각도순)

### [차단][E·R·I] B-1. 4단계 P8-15 관문이 r79 4키 때문에 구조적으로 "판정 불가"가 된다
- **근거**
  - 규칙 spec:376 P8-15: "L-2 켬·끔 두 팔을 P8-16 27키에서 돌린다. L-2 면제가 한 번도 쓰이지 않은 줄은 명령이 같다. 20줄 미만이면 판정 불가." 27키에는 판 5 r79 4키가 들어 있다.
  - 실행 쪽: `step4_impl_ed8.ps1:71`이 p815를 `--arms a8,a8_l2_off --r79-plan`(54줄)로 돈다.
  - 판정 쪽: `jp3_ed8_gate_judge.py:324-333` `has_no_waiver`가 `ed8_record.twist_waiver`를 줄에서 찾고, 없으면 `<stem>_t4h/<t4h_file>` meta에서 찾는다(378-396). 둘 다 없으면 None이고, 352-354와 366-367에서 `unread`가 되어 단계 전체가 `not_judgeable`이 된다.
  - 생산자 쪽: `ed8_probe.py:412-413`에서 r79 줄은 `run_r79_row` → `r79_L3L4_final.run_one`이 만든다. `ed8_record`·`probe_stiffness_record`·`ed8_settings`를 붙이는 `verdict_runs.ed8_record_meta`(verdict_runs.py:374-392)는 run_v5 경로에서만 불린다. r79 T4h는 `<t4h_dir>/r79_<setting>/` 하위 폴더에 쓰인다(ed8_probe.py:440).
  - 실측(41e107e9 사전 실행, 같은 생산자): `key_presence --where ed8_probe.arm=L2_impl` 결과 `ed8_record`·`ed8_record.twist_waiver.*`·`probe_stiffness_record`가 23/27이고, 빠진 4줄은 48·49·52·53행(job 키가 `r79_key`·`setting`뿐인 r79 줄)이다.
  - 셈 스크립트(r79 8줄): `<stem>_t4h/<t4h_file>`가 파일인 줄 0/8, 재귀로 찾으면 8/8, 찾은 meta에 `ed8_record`가 있는 줄 0/8. r79 meta에는 `hydraulic_options.ed8_settings`만 있다.
- **실패 시나리오**: 4단계 p815를 돌리면 판정이 a8 팔 r79 4쌍을 읽지 못하고 `not_judgeable`(종료 2)로 멈춘다. 그 뒤 판정 도구를 고치면 출력이 생긴 다음에 도구를 바꾸는 셈이 된다.
- **규칙 대조**
  - 규칙 10절(spec:345)은 "3.8 기록 키 결측"을 기록 실패(판정 상태를 바꾸지 않음)로 둔다.
  - P8-5와 달리 P8-15에는 "기록 키 없는 줄 → 판정 불가" 문장이 없다. 그러므로 도구의 `not_judgeable` 처리는 규칙과 다르다.
- **권장 조치(확인 필요 1의 선택에 따라)**
  - (가) T8′(python-expert): P8-15에서 기록을 읽지 못한 쌍은 판정 쌍에서 빼고 기록 실패로 적은 뒤 나머지에서 20쌍 이상을 요구한다. 생산자 꼴 시험으로 r79 줄 4개를 넣는다.
  - (나) 같은 방향의 대체 판별: 3.8 "면제 DONE은 `INFO_TWIST_UNSETTLED`를 낸다"에 따라 이 이름이 없는 줄은 면제가 없다고 보고 판정한다. 규칙 해석이므로 control-expert 확인이 필요하다.
  - (다) r79 경로에 기록을 붙이는 방법은 C8을 바꿔야 하므로 1단계부터 다시 해야 한다. 권하지 않는다.
  - 근거 판정에서 VBM 23키 가운데 면제를 쓰지 않은 줄이 20 이상이어야 한다. F8-19("L-2는 3줄에서만 작동")로 보면 여유가 얇다[추정].

### [차단][R] B-2. G′ 8단계가 5단계에서 뺀 1차 별칭 슬롯을 다시 넣거나, G′ 전체를 setting_defect로 만든다
- **근거**
  - 규칙 spec:291: 1차 별칭은 "빼고 기록".
  - `jp3_ed8_rules.stage5_selection`은 별칭을 뺀 슬롯만 `slot_layers`에 넣는다(462-468).
  - `jp3_ed8_judge.judge_heldout`(770-788)은 339줄 모두를 단위로 만들고 `first_aliases`를 읽지 않는다.
  - `rules.heldout_judgement` → `_unit_layer`(576-582)는 합침이면 모든 단위를 N으로 돌려 별칭도 센다. 합치지 않았으면 별칭 슬롯에서 `RuleInputError`가 난다.
  - 합성 실험(T8 `jp3_ed8_rules` 직접 호출, 별칭 5 + N 250)
    - E 0(합침): `status failed`, N `n 255`, `failures 5`. 별칭 5개가 들어가 실패로 셌다.
    - E 20(합치지 않음): `held-out unit 'A0': slot 'A0' has no layer`가 나서 G′ 전체가 setting_defect가 된다.
  - T8 시험(`test_ed8_judge_rules.py` 291-390)에는 별칭 슬롯이 든 8단계 사례가 없다.
- **실패 시나리오**: 합침 경우에는 별칭 단위가 $n_N$을 늘린다. $k_N$ 재계산(7.5)과 실패 수가 바뀌어 G′ 판정이 틀릴 수 있다. 합치지 않은 경우에는 별칭이 하나만 있어도 G′를 판정할 수 없다.
- **권장 조치**(python-expert, T8′)
  - `heldout_judgement`(또는 래퍼)에서 `selection["first_aliases"]` 슬롯을 2차 별칭 판단과 병합 전에 빼고 기록한다.
  - 두 경우(합침·합치지 않음)의 합성 시험을 넣는다.

### [차단][E·I] B-3. 5단계 `stage5` 판정이 실제 V0 줄에서 도구 오류(종료 3)로 끝난다
- **근거**
  - `jp3_ed8_judge.judge_stage5`(741)는 모든 5단계 줄(설정 V0)에 `identity_defects`를 돈다.
  - 그 함수는 판 7 `setting_identity("V0")`를 부르고, 이것이 `run_v5.options_of("V0")`로 간다. V0는 `"V0": (False, {})`(run_v5.py:123)이라 options가 None이고, `jp3_ed7_judge._setting_identity_json`(316-323)이 `jp3_ed7_judge.SettingDefect`를 던진다.
  - 이 클래스는 `Exception`을 바로 상속한다(jp3_ed7_judge.py:178). ed8 `main`은 `gate.SettingDefect`·`rules.RuleInputError`·`gate.NotJudgeable`만 받으므로(910-913) 예외가 일반 예외 처리로 떨어져 종료 3이 되고, `--out`이 쓰이지 않는다.
  - 합성 실험(Chrono-dev, T8 모듈, 줄 1개): `{"result":"raised","class":"jp3_ed7_judge.SettingDefect","caught_by_ed8_main":false,"message":"setting V0 has no hydraulic options"}`.
  - 끝까지 도는 시험 `test_stage5_main_end_to_end_with_stubbed_readings`는 `identity_defects`를 스텁으로 바꿨다(test_ed8_judge.py:362).
- **실패 시나리오**: 5단계 V0 678줄을 돌린 뒤 `ho_k_selection.json`을 만들 수 없다. 도구를 출력 뒤에 고쳐야 한다.
- **권장 조치**(python-expert, T8′)
  - V0 줄의 정체성 기대값을 판 8 규칙에서 정한다. 예: V0 `controller_tag` = `final_C4G2_LAS_K1`, ED8·LSB 필드 없음, ③ 기록 없음. control-expert 확인이 필요하다(확인 필요 2).
  - 스텁 없이 실제 정체성 함수로 V0 줄을 넣는 시험을 추가한다.

### [실행 전 수정][R·E] M-1. census `--selection-keys`(선택 사용 키 칸)의 입력이 정해지지 않았다
- **근거**
  - 규칙 5.2(spec:238)와 13절 13은 "선택 사용 키 / 그 밖" 두 칸 기록을 요구한다.
  - 도구(`jp3_ed8_judge.py:593, 610, 552-563`)는 필수 입력 `{"jobs": [...]}`을 sha 고정 없이 읽는다. 파일이 없으면 파일 오류로 종료 3이 된다. 내용이 job 형식과 다르면 조용히 0건이 된다.
  - 대조할 때 `setting`을 빼므로, 같은 job의 다른 설정 단위(C-S `VBN<key>` 등)까지 "선택 사용"으로 셀 수 있다. P8-14 키는 플랜트 M·LSM4·Mslow 구분이 있다.
  - 규칙 10절(spec:345)에서 기록 실패는 닫힌 목록이고 "목록 밖 문제는 setting_defect"다. 지금 동작(종료 3 또는 조용한 0)은 이와 다르다.
- **권장 조치**(6단계 전)
  - 만드는 주체와 형식을 정한다. P8-9 20키, P8-9′, P8-14 VBM 23키를 run_v5 job 꼴로 바꾸고 설정까지 맞춘다(spec:245에 R2 e0.001·S4 e0.002·S8 e0 포함이라고 적혀 있다).
  - 파일 sha를 판정 보고에 고정한다.
  - 대조 0건이면 setting_defect로 처리한다.
  - 기대 건수를 단언한다.

### [실행 전 수정][E] M-2. ed8 판정 도구가 재사용한 판 7 읽기 함수의 예외 클래스를 상태로 바꾸지 않는다
- **근거**
  - `jp3_ed8_judge.main`(910-926)은 `jp3_ed7_judge.SettingDefect`·`jp3_ed7_judge.NotJudgeable`을 받지 않는다. 이 두 클래스를 상태로 바꾸는 곳은 `l1ref`(853-856)뿐이다.
  - census·heldout·cases가 부르는 판 7 함수(`t4h_folders_of`, `metric_of`, `d_lines_of`, `jp3_of_rows`, 정체성)의 입력 결함은 모두 종료 3이 된다. 종료 3은 통과로 새지 않지만 결과가 나온 뒤 도구를 고치게 만든다.
- **권장 조치**: B-3과 함께 ed8 `main`에서 두 클래스를 각각 setting_defect·not_judgeable로 바꾸고 시험을 넣는다(python-expert).

### [실행 전 수정][I] M-3. P8-4 기준선과 run worktree의 numba 캐시
- **근거**
  - 규칙 P8-4(spec:364): "기준선은 C8의 부모에서". 부모는 41e107e9다.
  - 구현 보고는 41e107e9 전체 시험을 돌리지 않았고 66648ea8 junit으로 대신했다(c8_t8_report.md:61). 그 사이 27c0f046·41e107e9가 run_v5 배치·`jp3_12b_plan`·시험을 바꿨다.
  - `full_suite_ed8.ps1`(37-41)은 `NUMBA_CACHE_DIR`를 정하지 않는다. 구현 보고는 전체 시험 뒤 run worktree에서 numba 파일 28개를 지웠다고 적었다(c8_t8_report.md:109).
  - 단계 시작·끝 검사(common_ed8.ps1:117-118·218-219·244-245)는 worktree `04_scripts` 안에 `.nbi`·`.nbc`가 있으면 종료 3으로 멈춘다.
  - P8-4의 T8 하위 명령은 없다. 판정은 `jp3_ed6_suite.py judge`(full_suite_ed8.ps1:56)다.
- **권장 조치**(메인)
  - 41e107e9 detached checkout에서 `-Side base`를 돌린다.
  - `-Side run`은 C8과 같은 커밋의 별도 checkout에서 돌리거나, `NUMBA_CACHE_DIR`를 runner 폴더로 준 뒤 돌린다. 돌린 뒤 run worktree에 `.nbi`·`.nbc`가 없는지 확인한다.
  - P8-10 판정 근거는 scope 단계 기록(diff 3종)과 C8 `test_ed8_run_commit`(P8-4 시험 안)라는 점을 판정서에 적는다.

### [실행 전 수정][R] M-4. 12b 8절 "4사례를 뺀 P-pred 입력 통계" 기록이 나오지 않는다
- **근거**
  - 규칙 spec:327: "4사례를 뺀 사례 수·P-pred 입력 통계"와 "4사례의 VBKN0 교착 서명"을 따로 낸다.
  - T8 `four-case`는 줄·사례 수와 교착 서명만 낸다(t8_report.md:73, 확인 필요 4).
- **권장 조치**: "P-pred 입력 통계"의 뜻을 정한다(확인 필요 3). VBKN0 b1·b2 기회·미도달 수 등이 후보다. 정해지면 10단계 전에 T8′에 넣는다.

### [실행 전 수정][I·R] M-5. 생산자 꼴 미시험 범위(항목 5)
- **근거**
  - census·heldout·cases·l1ref·12a/12b 판정은 판 7 읽기를 스텁으로 바꿔 시험했다(t8_report.md:101).
  - 실제 생산자 꼴로 확인한 범위에서 이미 두 결함(B-1, B-3)이 나왔다.
- **권장 조치**(메인)
  - 4단계 출력이 생기면 판정 전에 `key_presence.py`로 키 존재만 본다.
    - 대상: `impl_t8`·`impl_cases`(run_v5 꼴)와 `impl_p85/p88/p815`
    - 키: `commands_sha256`, `t4h_file`, `controller_tag`, `hydraulic_options`, `lsb_components`, `lsb_settings`, `probe_d6_settings`, `hydraulics_record.extend_bound_check`, 사건 줄의 `event_output.reapproach_starts`, `ed8_record.reapproach_runs`, `ed8_record.twist_waiver.n_waiver_done`, `ed8_record.twist_waiver.n_waiver_periods`, `probe_stiffness_record`
    - 같은 방법으로 r79 줄도 따로 본다.
  - census 전에 `impl_t8` 줄을 census 읽기 경로(정체성, `metric_of`, J-P3, 층 함수)에 넣는 스모크 시험을 T8′ 시험이나 출력 밖 건식 판정으로 한다. 상태만 보고 값은 보지 않는다.

### [기록]
- **R-1 [I]** r79 경로(12b VBKN·VBKN0, l1ref, P8-15·P8-16 KM0 줄)에는 3.5·3.6 기록이 없다.
  - 빠진 것: `ed8_record`(재접근 실행·면제 기록), `probe_stiffness_record`, 최상위 `ed8_settings`.
  - 규칙 10절 기록 실패 (1)에 해당하므로 판정서에 적는다.
  - 고치려면 C8을 바꿔야 한다.
- **R-2 [I]** T8 정체성 검사는 `hydraulic_options`(그 안의 `ed8_settings` 스위치 3개)만 비교한다.
  - 3.6 정체성 목록의 `probe_k1_scale_settings`(δ), `r8.stiffness_warning_range`, `twist_completion_relax.waiver_max_rise_N`·`waiver_margin_N`은 비교하지 않는다(jp3_ed7_judge.py:299-313, 393-434).
  - run_v5 경로는 생산자 가드 `check_last_ed8`(verdict_runs.py:887-888)와 단계 정체성(HEAD·03_src tree)으로 덮인다.
  - 판정서에 이 범위를 적고, T8′에서 보완하기를 권한다.
- **R-3 [S·T]** 근거 폴더 추적 상태
  - `keys_seal_41e107e9\`(2개)와 `p816_prerun_41e107e9\`는 git 미추적이다(ignore 아님). 단 p816 폴더의 npz 54개는 ignore에 걸린다.
  - `baseline_check sums`: p816 폴더 64항목 해시 모두 일치. impl_report_ed8 SUMS는 T8 증거 5개를 담지 않는다(`t8_report.md`, `t8/imported_from_60ebb4a4.json`, `tests/junit_T8_ecf6c142.xml`, `junit_diff_C8_vs_T8_ecf6c142.txt`, `suite_T8_ecf6c142.log`).
  - 메인 할 일: S8-C 전에 커밋하고, npz는 LOCAL_ONLY 목록과 백업에 넣고, SUMS는 다시 쓴다.
- **R-4 [R]** C8 diff는 `run_v5.py`(sha 표 + 457행 docstring 1줄), `test_ed8_impl.py` 3줄, `test_ed8_run_commit.py`, run_steps_ed8 14개다. docstring과 test_ed8_impl은 11.1 "시험 기대값"으로 해석해 범위 안에 넣었다(common_ed8.ps1:62-64). 03_src 변경은 0이다.
- **R-5 [T]** C8의 부모는 41e107e9다(27c0f046 아님, 이유: `jp3_12b_plan --edition 8`). 41e107e9에서 P8-16 사전 실행은 pass, B_impl 27·L2_impl 27 equal, 추가 키 0, 끝 head 41e107e9, clean이다. 규칙 1단계 "구현 커밋에서 먼저 통과"를 만족한다.
- **R-6 [I]** 12b 충돌 스캔 키 파일 `ed5_inputs\x11\c92_keys.txt`·`c93_keys.txt`는 sha가 고정되지 않았다(common_ed8.ps1:140-141, 존재만 검사). 판 7에서 이어받은 것이다.
- **R-7 [R]** 구현자 확인 필요 (1)(2)(5) 판단은 아래 "확인 필요 판단" 표에 적었다. 모두 차단 아님이다.
- **R-8 [E]** `gate_scan` 경고 5건은 모두 오탐이다.
  - `row_value_path_no_base`(gate:172): `.done`의 절대 `folder`이고, 상대 경로면 setting_defect로 닫힌다.
  - `tag_single_compare` 3건(judge:357·362·516): 태그가 아니라 봉인 키 파일 설정 이름과 자체 라벨이다. 0건이면 기회 0이 되어 판정 불가로 닫힌다.
  - `empty_selection_sum_pass`(rules:560): `n_units == 0`이면 해당 없음, 합계 0이면 판정 불가로 처리한다.
- **R-9 [R]** 봉인 키 파일 구조는 규칙과 같다.
  - census 1043줄, C-J 388(VBN 100, LSN1~4 각 72), C-S 460(10설정 × 46, 판정 184), C-D 24(VBN 12, VBNslow 12), C-G 171. 옛 이름(VBM·LSM) 0, job 1043개 모두 다르다.
  - held-out 339줄, (가) 171·(나) 48·(다) 120, aa_order 길이 3·15·7, seed 20261127, `numpy.random.default_rng`, (원천, 슬롯) 오름차순, 슬롯 중복 없음.
  - sha 278b332f…·a18b5818…는 C8 상수, T8 `PINNED_SHA256`, `common_ed8.ps1`과 같다. 초안 사본과도 같다.

## 규칙↔도구 대조표
| 규칙(path:line) | 도구(path:line) | 판단 |
|---|---|---|
| 5.1 census 1043·키 sha(spec:218-222) | run_v5.py:466-469, jp3_ed8_judge.py:97-102·224-231, common_ed8.ps1:126-129 | 같음. 키 파일 구조 R-9 |
| 5.1 VBM→VBN·LSM→LSN | 키 파일 설정(R-9), CJ_LABEL judge:92 | 같음 |
| 5.1 V0 짝(main.jsonl sha 9ad74990, plain key, 192 v0_pair, run_id 정수) | judge:258-264, ed8_key_lists.py:349-368 | 같음 |
| 5.2 C-J (i)(ii)(iii) | judge:324-390 | 같음. (ii)는 줄 단위(허용 0에서 같거나 더 엄함) |
| 5.2 C-D 소유 → C-G 칸 | rules:50·179·205 | 같음 |
| 5.2 빈 층 해당 없음, 단계 기회 0 = 판정 불가 | rules:208-225 | 같음 |
| 5.2 선택 사용 키 칸 | judge:552-563 | 입력 미정(M-1) |
| 6.2 (가)~(바) | rules:132-182; phase_of `e0`·`e0.001`(jp3_ed7_judge.py:726-730) | 같음 |
| 6.3 사건 twin/기본값, `fast` 미사용, 대각, 0 ≤ t·round(t,3) ≤ 0.450, 결측 = setting_defect | ed8_key_lists.py:291-338, judge:291-299 | 같음 |
| 6.4 U832 셈 | judge:526-537(제외 없음) | 같음 |
| 7.3 5단계 순서 | rules:447-495 | 같음 |
| 7.3 1차 별칭 제외(8단계까지) | rules:523-582, judge:770-788 | **다름(B-2)** |
| 7.3 2차 별칭은 계산 전, 해시로만 | rules:540-549 | 같음 |
| 7.4 A/A 같은 층·최대 3회·같은 해시면 넘어가지 않음·합친 뒤 원래 층(사용자 확정) | rules:54-60·373-416, judge:677-716 | 같음 |
| 7.5 Jeffreys k·k_E 1·MDE80 | rules:256-338 | 같음(stats 재현) |
| 7.6 FAULT 0·J-P3 | judge:786-797 | 같음 |
| 8 12b 4사례 기록 | jp3_12b_judge_ed8 `four-case` | 일부(M-4) |
| 10 상태 순서·기록 실패 닫힌 목록 | rules:81-93 | 순서는 같음. P8-15 기록 결측 처리는 다름(B-1) |
| 3.6 정체성 | jp3_ed7_judge.py:393-434(판 8 태그로 바꿔 씀) | 일부(R-2). V0 줄 처리 불가(B-3) |
| P8-0 114줄·기준 sha | gate:249-266·84-87 | 같음 |
| P8-1 대체 없는 쌍 | gate:400-443 | 같음 |
| P8-5 15쌍, 기록 결측 = 판정 불가 | gate:303-310·370-371 | 같음 |
| P8-8 5쌍 | gate:313-321 | 같음 |
| P8-15 20쌍 | gate:324-333 | **r79 줄 판정 불가(B-1)** |
| P8-16 두 시점·완결성 27/27 | p816_compare.py:75-152, gate:471-485, step4_impl_ed8.ps1:68 | 같음 |
| P8-10 C8 범위·재생성 | common_ed8.ps1:192-209, test_ed8_run_commit(C8 junit 통과, skip 없음) | 같음(R-4) |
| P8-11 T8 범위 | `git diff --stat 56849248 ecf6c142`(04_scripts 판정 도구 11개·05_tests만), test_ed8_run_path 4건(T8 junit 통과) | 같음 |

## 항목 4: C8 5단계 러너의 aa2·aa3 조건과 판정 도구 짝 규칙
- **러너**
  - `step5_heldout_v0_ed8.ps1 -Part aa2|aa3`는 조건 없이 339슬롯 전부의 `aa_order[1]`·`aa_order[2]`를 돈다(run_v5.py:461·510-513).
  - "as 7.4 needs"는 코드가 아니라 메인의 실행 판단이다.
- **판정**
  - `slot_inputs`(judge:699-713)는 `aa_order[:3]`를 차례로 읽다가 처음 빠진 줄에서 멈춘다.
  - 후보 층은 판정 도구가 같은 `stratum_of`로 직접 다시 계산한다.
  - 같은 층 첫 후보에서 결정하고, 같은 해시면 넘어가지 않고 제외한다(사용자 확정과 같음). 결정 뒤 후보는 무시하고 기록한다.
  - 필요한 후보가 빠졌으면 `RuleInputError`가 나서 setting_defect가 된다(rules:412-414).
- **판단**
  - 짝 규칙과 층 함수는 같다.
  - 메인이 aa2·aa3를 골라서 돌리면 "setting_defect 뒤 추가 실행 → 재판정" 고리가 생긴다. **5단계에서 aa2·aa3를 조건 없이 모두 돌리기를 권한다.** V0만 돌리므로 오염이 없고, 도구가 남는 후보를 무시한다.
  - 지금은 B-3 때문에 `stage5` 판정 자체가 불가하다.

## 확인 필요 판단(t8_report.md 확인 필요 1~5)
| # | 판단 | 차단 여부 |
|---|---|---|
| (1) 기준 통과 = V0 자기 J항목에 `fail` 없음 | v8에는 6.1 "기준 통과" 정의가 없다. `own_item_failures` 상태는 fail·flag·record·undetermined이고(jp3_j9main_judge.py:618-630), undetermined를 통과로 보면 기회가 늘어 보수 쪽이다. 판 6·7 "V0 통과 전제"와 같은 읽기다. C-D·C-G는 키 파일의 `v0_pass`를 쓴다 | 아님. 판정서에 해석 공개 |
| (2) C-J (ii) 줄 단위 | 허용 0이라 병합 단위로 세도 합격·불합격은 같다. 기준(VBN) 실패 LSN 위반도 세므로 더 엄하다 | 아님 |
| (3) `--selection-keys` 생성 주체 | M-1 | 6단계 전 수정 |
| (4) 8절 P-pred 입력 통계 범위 | M-4 | 10단계 전 수정 |
| (5) J-P3 판정 행 수 기대값 없음 | 규칙 9절 "판정 때 T4h로 센다"와 같다. 0이면 판정 불가(jp3_ed7_judge.py:475-477) | 아님 |

## 확인 필요
1. **B-1 처리 방향**: (가) 기록 결측 쌍을 판정 쌍에서 빼고 기록 실패로 적은 뒤 20쌍 이상을 요구 / (나) `INFO_TWIST_UNSETTLED` 부재로 면제 없음을 판별 / (다) r79에 기록을 붙이도록 C8 교체(1단계부터). 권고는 (가)이고, 판정서에 기록 실패 (1)로 공개한다. 사용자·control-expert가 정한다.
2. **B-3**: 5단계 V0 줄의 정체성 기대값(태그, ED8·LSB 필드 없음, ③ 기록 없음)을 판 8 규칙으로 무엇이라 정할지(control-expert).
3. **M-4**: "P-pred 입력 통계"의 정의.
4. **5단계 aa2·aa3**: 조건 없이 전부 돌릴지(권고) 정한다.
5. stats 확인 필요 3(공개 MDE 표에서 도달할 수 없는 칸의 주석)은 판정서에서 처리한다.

## 위임 필요
- **python-expert(T8′, ed8-judge 위 새 커밋, C8 불변)**
  - B-1(가): `jp3_ed8_gate_judge.judge_arm_pairs`에서 p815 기록 결측 쌍을 기록 실패로 분리하고, r79 꼴 줄 시험을 넣는다.
  - B-2: `heldout_judgement`·`judge_heldout`이 `first_aliases`를 빼게 하고, 합침·합치지 않음 시험을 넣는다.
  - B-3: V0 줄 정체성을 처리하고, 스텁 없이 끝까지 도는 시험을 넣는다.
  - M-2: ed8 `main`에서 `jp3_ed7_judge.SettingDefect`·`NotJudgeable`을 상태로 바꾼다.
  - M-1: selection-keys 파일 형식, sha 기록, 0건 = setting_defect.
  - (권고) R-2: 3.6 `ed8_settings` 필드 비교.
  - 바꾼 뒤 T8′ 전체 시험(새 실패·새 skip 0)과 P8-11 시험을 다시 돈다.
- **control-expert**: 확인 필요 1(B-1 (나)를 고를 경우), 2, 3.
- **verif-protocol-auditor**: T8′ 재감사.
- `tools/verif 후보`(python-expert): "생산자 경로별 기록 키 결측 + T4h 하위 폴더 경로 해석" 검사. 입력은 jsonl과 `<stem>_t4h`, 출력은 경로별(job 키 집합) 키 존재 수와 meta 폴백 도달 수, 종료 1은 폴백 미도달. 이번에는 즉석 스크립트로 했다.

## 메인 세션 권고 (4단계 전 할 일, 항목 6)
1. T8′ 커밋, 재감사 차단 0, 그 다음 4단계(규칙 4절 3단계 멈춤 조건).
2. `prelaunch_j9\ed8_run_config.json`을 메인 checkout에 만든다.
   - 템플릿: `run_steps_ed8\ed8_run_config.template.json`
   - `run_commit` = `56849248371b4916e2fe683265e7abffdd6fb8d7`, `worktree` = `C:\workspace\outrigger_control\.claude\worktrees\ed8-impl`
   - 지금은 없다.
3. run worktree의 `check_ed8.ps1`이 종료 0인지 확인한다. 확인 항목: 설정, HEAD·clean·부모, P8-10 범위, 03_src tree, numba 위치, 고정 입력과 판 8 입력 sha.
   - 지금 확인한 것: P8-0 기준 `j9_runs\b46bdf8f\repro_a2\ed7_probe_a2.jsonl`이 있다. 출력 `j9_runs\56849248`과 numba 캐시 폴더는 아직 없다.
4. P8-4: M-3대로 41e107e9 base, C8 run을 돌린다(별도 checkout 또는 `NUMBA_CACHE_DIR` 지정, 끝나면 `.nbi`·`.nbc` 0 확인). 각 25~30분이고, 배치는 compute-scheduler-expert에 받는다.
5. 4단계 배치: compute-scheduler-expert의 마스크·워커로 scope → l1ref → p80 → p816 → p85 → p88 → p815 → t8 → cases 순서로 돈다. 각 단계는 앞 단계 `.done`이 필요하다. 출력은 `j9_runs\56849248\<step>_a1`이다.
6. 4단계 출력 뒤 M-5 키 존재 점검 → T8′ 관문 판정. P8-15는 B-1 결정대로 한다.
7. S8-C 전: R-3의 커밋·LOCAL_ONLY·SUMS를 처리하고, `keys_seal_41e107e9` 추적을 확인한다.

## 검사하지 못한 것
- `jp3_12b_judge_ed8.py`·`jp3_tjr_judge_ed8.py`·판 7에서 들여온 판정 함수의 세부(판 7 T′ 감사본 blob과 같다는 기록에 의존). 12b `four-case` 사례 틀 대조 코드.
- G′ seed 추출(`condition_index`·aa 순서)의 독립 재현. 정렬과 크기만 확인했다.
- P8-10 키 재생성의 독립 실행(결과 파일을 만드는 하위 명령이라 실행하지 않음). C8 junit의 해당 시험 통과와 sha 일치로 대신했다.
- `check_ed8.ps1`·`dry_run_ed8.ps1` 실제 실행(설정 파일 없음, 메인 작업).
- 판 5~7 판정 읽기(436.8 지표, J-P3 경로 1)의 생산자 꼴 실행(M-5).
- 41e107e9 전체 시험(M-3).
- handoff_leak: 경로 2 넘김 전이므로 해당 없음.

## 실행한 검증
- **인터프리터**
  - python-dev `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`MKL_THREADING_LAYER=TBB`): verif 도구, 즉석 셈 스크립트, `jp3_ed8_rules` 합성 실험.
  - Chrono-dev `python.exe -I -B`(`PYTHONDONTWRITEBYTECODE=1`, `NUMBA_CACHE_DIR`=scratchpad): `jp3_ed8_judge.identity_defects` 합성 1줄 실험.
- **verif 도구**
  - `seal_check`(규칙): 종료 0, raw = LF = 봉인, `-text`, CRLF·BOM 0, 추적됨
  - `seal_check --const …jp3_ed8_gate_judge.py:SPEC_V8_SHA256`: 종료 0
  - `ps1_lint`(run_steps_ed8 ps1 13개): 종료 0
  - `placeholder_scan --pattern-set both`
    - run_steps_ed8 14개: 템플릿 자리 2개(`<ED8_RUN_COMMIT>`·`<ED8_RUN_WORKTREE>`)
    - 건식 `commands_ed8.json`·`dry_ed8_run_config.json`: 0
  - `gate_scan`(T8 판정 도구 5개): 경고 5, 모두 오탐(R-8)
  - `junit_skips --critical "test_ed8_|test_ed7_judge|test_ed7_adoption|test_v5_options"`: C8·T8·66648ea8 모두 critical_skipped 0. 실패 2(C8·T8, 기존)·3(66648ea8), skipped 134. P8-6 `test_p86_…`과 P8-10 `test_p8_10_…`은 C8에서 통과, P8-11 4건은 T8에서 통과
  - `worktree_locks`(ed8-impl·ed8-judge): 종료 0, lock 사유가 HEAD와 맞음
  - `key_presence`(p816_prerun_41e107e9 `p816.jsonl`, arm별)
  - `baseline_check sums`(p816_prerun_41e107e9, impl_report_ed8)
  - `ref_check`: 규칙 파일, `--rev 56849248 --rev 2715230e`, 블라인드 3개 `--exclude`
    - ref_missing 2개는 예정 산출물 `ho_k_selection.json`과 13절 19의 정정된 잘못 경로다(정상)
- **git(조회만)**
  - `worktree list --porcelain`, `log`, `merge-base --is-ancestor`(2715230e는 C8의 조상이 아님, 규칙대로 7fc83456 위)
  - `diff --stat`(C8 대 41e107e9, T8 대 C8, 41e107e9 대 27c0f046), `show 56849248:05_tests/unit/test_ed8_run_commit.py`
  - `check-attr`, 두 worktree `status --porcelain --ignored`(감사 전후 모두 비어 있음)
- **해시**: 키 파일 4개(봉인 사본·초안 사본) Get-FileHash
- **즉석 스크립트**(scratchpad `verif-ed8-prerun\`, 보고 전에 폴더째 지움)
  - `r79_lookup.py`·`meta_keys.py`: 셈과 키 이름만 출력
  - `keys_census.py`: 키 파일 구조
  - `alias_probe.py`: B-2
  - `v0_identity_probe.py`: B-3
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v8_rules.md 35f9eba8…, jp3_remedy_spec_v8_rules.md.sha256 e19aaa48…, report.md b2773b2a…, c8_t8_report.md 38bfef00…, t8_report.md eb23520a…, stats_t8_check.md 1e1dd61b…, SHA256SUMS d9e4f2ba…, census_keys_ed8.json 278b332f…, heldout_g_ed8.json a18b5818…, SHA256SUMS 0921e251…, p816_compare.json de7ca9d7…, commands_ed8.json 3f8f807b…, dry_ed8_run_config.json 6cdb0859…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 에이전트 메모리: `audit_pitfalls.md`에 한 항목(두 번째 생산자 경로의 기록 결측, V0 전용 단계 정체성 오류, 앞 단계에서 뺀 항목의 재유입)을 더하고 `MEMORY.md` 색인 한 줄을 고쳤다.
- 사용한 스킬: 없음

## 공개(행위 그대로)
- 블라인드 파일(`j9_runs\606f8713\cdry_a1\VBK_c92*`·`VBK_c93*`·`logs\`, `prelaunch_j9\ed6_inputs\x11\selection.json`, worktree 사본)은 열지도, Grep·Glob 대상으로 쓰지도 않았다.
- **규칙 어긋남 1건**: Bash `git ls-tree --name-only 2715230e 06_analysis/02_control/j_p3_cause/`로 블라인드를 품은 상위 폴더 `j_p3_cause`의 최상위 목록(비재귀)을 한 번 출력했다. 나온 이름은 `j9_runs`·`prelaunch_j9` 등 폴더·파일 이름이다. 블라인드 파일 이름과 블라인드 하위 내용은 나오지 않았다.
- `ref_check`의 비슷한 이름 후보로 블라인드가 아닌 `j9_runs\78fd5d2d\dry_a1\selection.json` 같은 경로가 화면에 나왔다.
- Grep·Glob 범위로 지정한 곳
  - worktree 하위 경로: `ed8-impl\04_scripts\04_hydraulic\coupled`(`*.py`), `ed8-impl\05_tests\unit`, `…\prelaunch_j9\run_steps_ed8`, `ed8-judge\04_scripts\04_hydraulic\coupled`(`*.py`), `ed8-judge\05_tests\unit`
  - 단일 파일: junit xml, 실행 경로 목록 json
  - `ed8_design` 하위 폴더 셋
  - worktree 루트·`06_analysis`·`02_control`·`j_p3_cause`·`j9_runs`·`prelaunch_j9`는 검색 path로 쓰지 않았다.
- `Test-Path`를 블라인드가 아닌 단일 경로 5개에 썼다: `j9_runs\56849248`, `j9_runs\b46bdf8f\repro_a2\ed7_probe_a2.jsonl`, `prelaunch_j9\ed8_run_config.json`, `prelaunch_j9\run_steps_ed8`, runner numba 폴더.
- Bash는 조회용 git과 메모리 파일 `wc`·`tail`에만 썼다. 파이프는 쓰지 않았다.
- 판정 도구 함수를 import한 것은 합성 입력 실험 두 번(B-2·B-3)뿐이다. 실제 결과에 판정 도구를 돌리지 않았다.
- 프로세스를 종료하지 않았다.
