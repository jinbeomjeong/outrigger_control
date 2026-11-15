# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev16 (하네스 두 경로 판정 S-13 뒤: 규칙 공백 두 곳, 두 경로 하네스 도구 수정 R4, 경로 2 앵커 읽기, J11·격자 J-P3 읽기, G-3 짝·G-6 T4h·Chrono 확인 행 등록, J-P3 미달·판독 모형 한계, 결과 본 뒤 개정, 봉인 후보 초안)

- **상태: 봉인 후보 초안(봉인 전).** 봉인 전에는 실행·판정에 쓰지 않는다. 봉인 때 바꿀 머리 줄은 끝 절에 원문으로 적었다.
- 원판 `v5_resume_4368_rules.md`(sha256 `9019b405…`), rev1(`d9094fda…`), rev2(`497e4614…`), rev3(`dad8dfa6…`), rev4(`7ea87a30…`), rev5(`452a8436…`), rev6(`809e5639…`), rev7(`e81f7d31…`), rev8(`3ecafaaf…`), rev9(`4cf7843c…`), rev10(`62a0bd8d…`), rev11(`9bac4524…`), rev12(`78f1f99b…`), rev13(`383bffc1…`), rev14(`baedeab4…`), rev15(`0162561c…`)는 고치지 않는다. 이 판은 rev15(sha256 `0162561c3866412f06ef3be0b3a62434e4a9ba5a37c9003be4df2f373af545ef`, 봉인 기준 커밋 `b9f5707`, 봉인 파일 커밋 `cc0d9b8`, 브랜치 `z4372-seal`) 위에 쌓인다. 용어: **봉인 기준 커밋**(SEAL_COMMIT) = 봉인 파일을 넣는 커밋의 부모, **봉인 파일 커밋** = 봉인 파일 세 개를 담은 커밋. 전체 sha256은 각 판의 `.sha256`에 있다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다.
- **시점: R2 `b9f5707` 하네스 본 묶음의 두 경로 판정 출력을 모두 본 뒤, Chrono 결과 일부(R16-0 2의 Chrono 분류 출력과 저장 행)를 본 뒤, PS-c 2행 실행 중, C-2 4행 rc 0 종료(봉인 SEAL_TIME, 봉인 기준 커밋 SEAL_COMMIT).** 이 판은 결과를 본 뒤의 개정이다. 본 자료는 R16-0에 모두 적었다. C-2는 종료 코드만 전달받았고, C-2·PS-c의 결과 내용은 본 자료에 들어가지 않는다.
- 작성: control-expert, 2026-11-15. 기준 R2 = `b9f5707`(rev14 R14-3), 판정 도구 커밋 R3 = `576eb87`(통합 브랜치 `z4373-r3v2`, R16-12 1).
  - 계기: 하네스 두 경로 판정(`judge_b9f5707/harness_path1`, `harness_path2` A·B판)에서 H-3·H-4·H-6~H-9의 등급·목록·분류가 갈렸다(원판 8.2 S-13). 원인은 두 경로 도구의 읽기 결함과 규칙 공백 두 곳이었다. 멈추고 물을 사유(S-6, G-5, G-6, H-7)도 함께 나왔다.
  - 사용자 결정(2026-11-15) 1~7과 결정 50~56(2026-11-15), python-expert·cad-expert 확인과 실행 준비, verif-protocol-auditor 봉인 전 감사 두 차례(첫째: 차단 3·권고 9·확인 필요 4, 대상 초안 `e69a597a`; 둘째: 차단 1(준비물 도구 결함, 고쳐짐)·권고, 대상 초안 `de2b2b89`)를 R16-1~R16-15b에 반영했다.
- **봉인 준비판이다.** 봉인 전에 답이 필요한 항목은 없다(확인 필요 0). 이 줄은 봉인 때 바뀐다.
- **바꾸지 않는 것**: 숫자 문턱, 등급과 우선순위(원판 8.1), 멈춤 조건의 뜻(원판 8.2), 기존 묶음의 범위와 행 목록, 사전 예측 값 P-1~P-15, P-1·P-2 앵커(rev1 RV1-5, rev13 R13-3), 두 경로 요건(원판 9.2), 이미 돈 실행의 argv·코드, 모든 기존 묶음의 실행 커밋 `git_at_start` = R2(rev14 R14-3). 이 판이 더하는 것은 새 기록 묶음(H-11, H-12, C-9~C-11), 그 행 정의와 사전 예측, 원 규칙이 정하지 않은 읽기, 그리고 도구 커밋의 구조(R16-12)다.
- **글머리 표시**: 각 절에서 경로 2에 넘기는 글머리는 **[정의]**로, 넘기지 않는 사실·참고 수치 글머리는 **[사실]**·**[참고]**로 머리에 적는다. 경로 2에 넘기는 범위는 R16-10 3 표가 원본이다.

## R16-0. 결과 본 뒤 개정의 공개 (본 자료 목록)

- 이 판은 하네스 본 묶음의 두 경로 판정 출력과 Chrono 결과 일부가 나온 뒤에 쓴다. 문턱·등급·멈춤 조건의 뜻은 바꾸지 않는다.
- **이 판을 쓰기 전에 사람·도구가 본 것**(2026-11-15)
  1. 메인 세션이 두 경로 출력을 요약한 것: S-6 67줄, G-5 집합(경로 1의 5키, 경로 2 A의 2키, B의 3키), H-7 J-P3 5줄, J11 6줄(경로 2) / 153줄 판정 불가(경로 1), u3 G-6 3줄, H-8 seedext, 경로 2의 S-5 앵커 질문, 경로 1의 S-2 1,553줄·S-3 242줄, G-3 기록 없음.
  2. 이 작성자(control-expert, 도메인 검토)가 직접 연 것(읽기 전용, 2026-11-15)
     - 두 경로 판정 출력: 경로 1 `k1_class.json`, `u3_judge.json`, `h8_noise_judge.json`, `record_check.json`, `chrono_path1/k1_classification_7_2.json`(Chrono 행 51개의 7.2 분류), 경로 2 `p2h_harness.json`, `p2h_harness_b.json`, `p2h_u3.json`, `p2h_u3_b.json`.
     - 원 데이터: `resume_k1/` 아래 `h8_noise_{V0,VB}.json`, `h8_seedext_VB.json`, `h6_dg3_v4on.json`, `h9_stage1.jsonl`, `h10_reuse_rerun.jsonl`(와 그 T4h npz), `h9_grid/*.json`, `v5_rerun/las_k1/` 아래 u3·u6 결과, 저장 기준선 `v5/noise_v0`, `noise_vb`, `noise_vb_m2r4`, `dg3/dg3_v4_on.json`, `seedext/r79_VB_seedext.json`.
     - 저장 Chrono: `07_results/S9/batch_JOURNAL-AUGER_20261031_165543`, `batch_P3b_20261026_122444`, `batch_k1soil_G1_20261105`, `batch_G6P_20261029_144418`, `batch_V5-RESUME-K1-C3/C4/C5_*`의 `batch.json`·`result.json`.
     - 코드(읽기만): `two_pressure.py` 2185~2216행, `b5_baseline_compare.py` 347~366행, `p2_u3.py` 1~209행, `r69_g8_screen.py` 85·223행, `s9_soil_slope.py` 44~52·720~740행, `run_b9f5707/run_harness.ps1` 26~47행(단계 argv·Env).
  3. 이 작성자가 그 자료에서 확인한 사실(아래 각 절 [사실] 글머리의 근거)
     - S-6 67줄은 모두 G1 균일이고 결정 67건이 모두 dP = −5주기다.
     - 저장 Chrono G1 행은 모두 `soil_mode_t_s` = null이다: G1 균일 6행(패드 B 3, A 3)과, 배치가 다른 G1 일색 10행(`batch_k1soil_G1_20261105`, `--soil-patch FL:G1`, 60 s, `batch.json` 없음).
     - G-5 차이의 원인: 경로 2가 settle_v2의 축별 목록을 스칼라로 읽었고, r72 377·U-S9-G6c 강등을 빠뜨렸다.
     - 경로 2 S-5(1,844/86/86)는 "같음 + 저장 해시 없음"의 합이다. 저장 파일에는 `base.commands_sha256`만 있다. VB 3줄 차이는 dg3 대체 키이고, `dg3_v4_on`과는 비트가 같다.
     - J11 기록 필드는 `n_late_fallback`이다(`n_late` 없음, 153/153). 경로 2의 6줄은 모두 V5·V7이다.
     - J-P3 5줄은 2개 시나리오다(R12 bottom FL Fs4와 격자 `r69_bottom|…|FL|G4|0.0`은 숫자가 같음).
  4. 메인 세션이 전달한 확인 결과(2026-11-15): python-expert의 G-3 argv·키·비교 필드, G-6 T4h 경로와 값 출처 조사, cad-expert의 Chrono 행 argv·격자·실행 방식·정체성 점검·실행 준비(칸 마스크, 정체성 도구, 출력 폴더), verif-protocol-auditor의 봉인 전 감사. 모두 코드·저장 행 argv·규칙 본문만 보았고 판정 등급은 쓰지 않았다(메인 세션 전달).
  5. **hydraulics-expert 원인 분석**(2026-11-15, 결과를 본 뒤의 분석): J-P3 2개 시나리오와 G-6 g8 3키의 원인이다. 근거 자료는 `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\hyd-4368`(스크립트·출력·npz 83개 파일)다. 메인 세션이 요약을 전달했다. 이 작성자는 요약만 보았고, 그 폴더의 파일은 열지 않았다. 요약 내용은 R16-15 2와 R16-15a에 적었다.
  6. 이 결함 목록(R16-5~R16-9)은 **메인 세션과 도메인 검토(control-expert)가 두 경로의 출력을 모두 보고 정리한 것**이다. 두 경로 작성자 자신이 상대 출력을 보고 고친 것이 아니다(원판 9.2 "상대 출력을 본 뒤에는 어느 경로도 고치지 않는다"). 경로 2 작성자에게는 R16-10 3 표의 [정의] 글머리만 준다.
- 사후 개정이므로 판정서에는 이 목록을 그대로 싣는다. 값을 본 뒤 정한 읽기(R16-3~R16-9)는 판정 결과 옆에 "결과 본 뒤 정한 읽기"로 적는다.
- 이 작성자는 경로 2 작성자가 아니다(rev2 R2-0).

## R16-1. S-13의 처리 (사용자 결정 1)

- **[정의]**
  1. 하네스 묶음 H-1~H-10의 첫 두 경로 판정 출력(`judge_b9f5707/harness_path1/`, `harness_path2/`의 A·B판, 경로 1 sha256 목록 `sha256_manifest.txt` `303d6421…`)은 **기록으로만** 둔다. S-13 경과로 판정서에 싣고, 등급·사전 예측 대조·한계 문장의 근거로 쓰지 않는다(rev14 R14-2와 같은 처리).
  2. 시뮬레이션은 다시 돌리지 않는다. R2 실행 기록(`resume_k1/`, `v5_rerun/las_k1/`)을 그대로 두고 R4 도구(R16-12)로 두 경로를 다시 판정한다. `--git-at-start`에는 R2를 준다(rev15 R15-1 2).
  3. 재판정에서 등급이 다시 갈리면 원판 S-13 그대로 멈추고 묻는다.
- 결정 필요: **아니오**(사용자 결정 1).

## R16-2. 새 묶음과 S-15 대조값

| # | 묶음 | 줄·행 수 | 지위 | 정의 |
|---|---|---|---|---|
| H-11 | U-3·U-6 G-3 짝(V0 설정 = 옵션 없음) | 실행 10(비교 짝 8) | 관문(u3 원판 7절 G-3) | R16-8 |
| H-12 | u3 g8 G-6 3키의 T4h 기록 실행 | 3(대체 경로로 가면 대체 3, R16-9 6) | 기록(rev1 #5) | R16-9 |
| C-9 | S-6 확인: Chrono G1 균일 관문 켬/끔 짝 | 2 | 기록 | R16-11 1 |
| C-10 | G-5 확인: g6 강체 + S1 앞 패드, VB/V0 × FL·FR | 4 | 기록 | R16-11 2 |
| C-11 | seedext 확인: J2 균일 상단 F_s 0, VB/V0 | 2 | 기록 | R16-11 3 |

- **[정의]** S-15(원판 5.1·5.2)의 대조값에 위 다섯 줄을 더한다. 기존 묶음의 묶음별 값(rev3 R3-F1, 하네스 9,570줄)은 그대로다. S-15는 묶음별 값만 대조한다.
- **[정의]** 원판 8.1의 기록 묶음(H-7, IND_LAS, C-4 기록 항목, C-6·C-7, C-8)에 H-12, C-9, C-10, C-11을 더한다. 이 묶음들은 `기록 완료` / `기록 불완전`이다. H-11은 관문이므로 등급이 없다. H-11이 거짓이면 H-3·H-4를 판정하지 않고 멈춘다(u3 원판 7절).
- **[정의]** 원판 4.2의 `--k1-order-gate` 금지는 C-9 끔 팔에는 적용하지 않는다. 그 팔은 `--k1-order-gate off`가 정의다. 기대값은 R16-11 1이다. 다른 새 행에는 금지가 그대로다.
- **[정의] 원판 11.1·11.2의 적용**(사용자 결정 54의 4: G-S 면제 + 대체 점검)
  - 11.1 옵션 × 단계 겹침 표: 새 묶음 H-11·H-12·C-9~C-11의 행을 **넣는다**. python-expert(하네스)·cad-expert(Chrono)가 행 종류 × (프리셋·래퍼·argv·env) 칸을 채우고 실행 전 감사가 대조한다.
  - 11.2 G-S 건조 실행: 새 묶음은 **면제**한다. 대신 다음을 한다.
    - H-11: 각 스크립트의 인자 파싱 dry 점검. 실물은 `<OUT>\H-11\h11_key_selection.json`(6실행, 키 10, R16-8 표와 일치)이다.
    - H-12: 설치 점검 `<OUT>\H-12\h12_check_install.json`과 첫 T4h 파일의 `--check-recorded` 확인(R16-9 4)
    - C-9~C-11: 행마다 실행 전·뒤 정체성 점검(R16-11b 1, R16-14 3)
    - 11.1 표의 실물은 `<OUT>\_tools\harness\table_11_1.md`다.
  - 면제 사실과 대체 점검 결과는 판정서에 공개한다.

## R16-3. 규칙 공백 1: ABL 줄의 4.2 기대값 (사용자 결정 1)

- **[사실]** H-4 ABL 242줄(`controller` = `ABL`, 태그 `ABL_LAS_K1`)의 `liftoff_approach_slow.settings.require_soil_response`는 `False`다. `b5_baseline_compare.ablation_config`(347~366행)가 이 값을 설계로 넣는다. ABL은 토양 응답을 끄므로, 이 값이 참이면 LAS-b가 시작하지 못한다(사용자 결정 2026-11-08, 같은 함수 docstring). 원판 4.2 기록 확인 문장 "9값이 프리셋 값"은 줄 종류별 기대값을 H-0에만 정했다(rev11 R11-1). 그래서 경로 1이 S-3을 냈다.
- **[정의]** ABL 줄의 원판 4.2 기대값은 프리셋 값이다. 다만 `liftoff_approach_slow.settings.require_soil_response`는 `False`다. 그 밖의 8값, K1 관문(`flat_soil_margin_order_gate` = true), `k1_order_gate_effective` = true는 프리셋 그대로다. `slope_clearance_margin.settings.flat_soil_margin_m` = 0은 ABL 정의값이다(명세 429.11, 같은 함수). 이 둘 밖의 값이 다르면 S-3이다.
  - 줄 종류 판별은 줄의 `controller` 필드(`ABL`)와 태그(`ABL_LAS_K1`)가 함께 맞을 때만 한다. 하나만 맞으면 판별 입력 결함이고 S-3이다(rev11 R11-1과 같은 꼴).
  - C2·IND·IND_LAS 줄은 앞 판 그대로다.
- 결정 필요: **아니오**(사용자 결정 1, 2026-11-08 결정의 적용).

## R16-4. 규칙 공백 2: V0 결과의 `hydraulic_options` 블록 부재 (rev8 R8-1b 보완, 사용자 결정 1)

- **[사실]** H-8 잡음 V0 1,503줄과 seedext V0 50줄(합 1,553)에 `hydraulic_options` 블록이 없다. rev8 R8-1b는 "블록이 없으면 재계산 불가"(R8-1d로 S-2)라고 정했다. R8-1e의 확인 사실은 블록이 있는 VB·H-7 기록만 보았다.
- **[정의]**(R8-1b ③ 칸의 보완): r79 결과 항목의 `v5_setting`이 `V0`이면 `hydraulic_options` 블록이 없는 것은 ③ 끔이다. V0은 "v5 플랜트 옵션 모두 끔"이다(u3 원판 1절 V0 행, v5 기준 8절). 그 밖의 재계산 입력(`resume_k1.applicable`, LAS-b `enable`, K1 관문)은 R8-1b 그대로 있어야 한다.
  - `v5_setting`이 없거나 V0가 아니면서 블록이 없으면 앞 판 그대로 재계산 불가이고 S-2다.
  - 재계산 태그는 R8-1c대로 정하고 최상위 태그와 같아야 한다. 다르면 S-2다.
- **[참고]** 이 읽기로 1,553줄의 재계산 태그는 `final_C4G2_LAS_K1`이 된다.
- 결정 필요: **아니오**(사용자 결정 1).

## R16-5. 경로 2의 S-5 앵커 읽기 (사용자 결정 1·54의 2)

- **[정의]**
  1. 원판 7.2 미작동 행의 "10절 비트 예측(P-1·P-2) 앵커 또는 저장 행 해시"에서 앵커는 rev1 RV1-5의 P-1·P-2 앵커 파일뿐이다(rev13 R13-3). rev1 RV1-3.2의 키 원본(`v5/dg3/dg3_v4_on.json`, `v5/noise_{v0,vb}/*`, `v5/seedext/*`)은 앵커가 아니다. 그래서 그 파일과 해시가 달라도 S-5가 아니다. rev13 R13-2 #19("H-8에는 P-1·P-2 앵커가 없다")와 같은 읽기다.
  2. 키 원본과의 대조는 **기록**("미작동 확인", 원판 5.5 문구)으로 두 경로가 함께 낸다.
     - 새 줄의 최상위 `commands_sha256`을 키 원본 같은 키 줄의 `base.commands_sha256`과 비교한다. 키 원본에는 최상위 `commands_sha256`이 없다.
     - H-8 VB 잡음에서 dg3가 대체한 키(L3 134 + L2 1, rev1 RV1-3.2)는 `v5/noise_vb` 대신 `v5/dg3/dg3_v4_on.json`과 비교한다. 그 키의 키 원본은 ③ 끔 실행이라서다.
     - 저장 줄에 해시 필드가 없으면 "저장 해시 없음"으로 센다.
     - 판정서에는 묶음별 같음·다름·없음 수를 적는다. 다름은 python-expert에 원인 확인을 넘긴다(공개, 멈춤 아님).
- **[사실] 공개**(사용자 결정 54의 2): 원판 7.2의 "또는 저장 행 해시"에서 저장 행 비교를 S-5에서 빼 기록으로 돌린 것은 **결과를 본 뒤 정한 읽기**다. 판정서에 그렇게 적는다. 이 작성자가 본 값(R16-0 3)으로는 이 읽기가 판정 결과를 바꾸지 않는다: 저장 해시가 있는 미작동 줄은 모두 같았고(dg3 대체 키는 `dg3_v4_on`과 같음), 다른 줄은 없었다.
- **[참고]** 이 작성자가 본 값(판정 값 아님): H-8 V0 같음 407 / 없음 450, VB 같음 434 / 없음 450 / 다름 3(dg3 대체 키, `dg3_v4_on`과 같음), H-6 같음 46 / 없음 40, seedext VB 같음 25 / 없음 25.
- 결정 필요: **아니오**(사용자 결정 1, 54의 2).

## R16-6. J11의 하네스 읽기 (사용자 결정 1, 경로 1·2 공통)

- **[사실]**
  - 하네스 줄의 J11 기록은 `lock_window_alignment.n_late_fallback`(정수)과 `n_late_fallback_by_leg`(다리별)이다. 최상위 `n_late` 키는 없다(H-9 대체 다리 줄 153/153).
  - v5 기준 8절은 V4~V8을 "참고, 합격 판정 없음"(`unit_status: below_criteria_reference_only`)으로 정했다. 1단계 판정서는 J11(n_late_fallback)을 VB·LS·item8·overlap에서만 판정했다.
- **[정의]**
  1. rev3 R3-C7의 "n_late"는 하네스 줄에서 `lock_window_alignment.n_late_fallback_by_leg`(실제 대체 다리, `fallback_legs`의 다리)다. 실제 대체 다리 n_late > 0의 멈춤(H-7, LS는 L-e)은 이 값으로 본다. 대체 다리가 있는 줄에서 이 키가 없거나 None이면 앞 판 그대로 판정 불가다.
  2. J11 멈춤의 적용 설정은 VB, LS1~LS4, item8(VB), overlap(VB)이다. V0~V8·L1·L2와 pressure_only의 J11 값은 기록이다(v5 기준 8절, 1단계 판정서 2절 표).
- **[참고]** 이 읽기로 H-9 V5·V7의 n_late_fallback > 0 6줄은 기록이다.
- 결정 필요: **아니오**(사용자 결정 1).

## R16-7. H-9 격자 J-P3 (경로 1 보완, 사용자 결정 1·4)

- **[정의]** H-9 격자 VB 768 run 각각에 rev3 R3-C8·rev4 R4-A2·rev8 R8-2의 J-P3을 적용한다. 입력은 run의 `hydraulics_record.extend_bound_check`(`breach_reads`, ext_moving)다. 경로 1은 `judge_stage1_4368.py`(또는 R16-12 허용 목록 안의 경로 1 하네스 도구)에 격자 등급을 넣는다. 경로 2는 앞 판 그대로다. 두 경로 모두 run 단위 위반 목록(격자 파일, `results[]`·`runs[]` 위치, 다리, 판독 수, 최소 간격 [bar], 첫 위반 시각 [s])을 낸다.
- 결정 필요: **아니오**(사용자 결정 1).

## R16-8. H-11: U-3·U-6 G-3 짝 실행 (사용자 결정 1·54의 1·54의 4, u3 원판 7절 G-3)

- **[사실]** u3 원판 7절 G-3("스크립트마다 2키를 옵션 없이 돌린 명령 해시 = 같은 커밋의 기존 출력")은 관문이다. 436.8 행 목록에는 이 실행이 없었다(경로 1 `no G-3 record`).
- **[정의] 비교 대상**(u3 rev2 #11을 고쳐 씀, 사용자 결정 54의 1): G-3은 "V0 설정이 옵션 없음과 같다"는 검사다. rev2 #11의 비교 대상 "같은 커밋에서 옵션 없이 돌린 LAS 태그 출력"을 "**R2에서 `--v5-setting V0`으로 돈 출력**(H-3의 V0 출력, U-6은 R16-8 실행 표의 V0 팔)"으로 고쳐 쓴다. 옵션 없는 실행은 R2에서 새로 돈다.
- **[정의] 옵션 없음**: 기준은 H-3·H-4의 R2 실행 argv와 Env(`run_b9f5707/run_harness.ps1` 26~47행)다.
  - argv에서 `--v5-setting <설정>`, `--reuse-d1 <파일>`, `--ids-from <파일>`, `--pad <패드>`를 빼고 아래 표의 키 좁히기 인자로 대신한다. 출력 경로는 `<OUT>\H-11\` 아래로 바꾼다.
  - **작업자 수와 affinity**: 작업자 수와 affinity는 명령 해시에 영향이 없으므로 R2와 다를 수 있다(작업마다 spawn, 작업자당 1스레드). 해시 같음 관문(아래)이 이를 확인한다. 이번 값은 배치표에 따른다: 하네스 전체 `--workers 2`·`--affinity 0x0F000000`(E 24–27), r72는 위치 인자 `2`와 env `R72_AFFINITY=0x0F000000`(R2는 workers 8, 마스크 `0x00FF0000`).
  - `s9_soil_slope.py`만 2키 키 파일 `<OUT>\_tools\harness\h11_D_keys.json`(`H8|rigid|B|top|flat`, `H8|G1|B|top|flat|FL:g20`)을 `--ids-from <그 파일> --pad B`로 넘긴다. 이 두 인자는 키 선택이고 v5 플랜트 옵션이 아니다. 키 파일과 그 sha256을 판정서에 적는다.
  - 준비물(`<OUT>\_tools\harness\`)의 `h11_h12_check.py`는 기계 점검(파일·키 수·정체성 기록 유무)만 하는 도구다. G-3 관문 판정은 R4의 두 경로 도구가 한다.
  - **env**는 R2 `run_harness.ps1`의 해당 단계 Env에서 두 곳만 다르다: `R72_FILTER`를 더하고, `R72_AFFINITY`는 위 작업자·affinity 글머리대로 `0x00FF0000` → `0x0F000000`이다. R2 값: `u3_p3b_V0`·`u3_g8_V0`·`u3_D_V0` = `@{}`, `u3_C_V0` = `R72_SET=x426`, `R72_PATH=per_leg`, `S9_SETTLE_HOOK=p0`, `R72_AFFINITY=0x00FF0000`, `u6_main_VB` = `R72_PATH=per_leg`(b5 두 팔 모두). 실제 argv·env와 R2의 차이는 사이드카 `<OUT>\H-11\h11_argv_env_vs_R2.json`에 남긴다.
  - 인터프리터는 dynamics-dev `python.exe` 직접 호출이다(`run_harness.ps1`과 같다).
- **[정의] 키 좁히기와 비교 필드**

| 스크립트 | 키 좁히기 | 비교 필드 |
|---|---|---|
| `s9_slope_fix_candidates.py` | `--ids "<키1>;<키2>"`(`;` 구분) | `records[].hash`(16자리 hex, g8은 r69 `cmd_sha256`) |
| `r72_g6_screen.py` | env `R72_FILTER=g6\|G1+J1@FL\|top\|Fs8,g6r\|rigid+J1@FL\|top\|Fs8` | `results[].commands_sha256` |
| `s9_soil_slope.py --groups H8` | `--ids-from <OUT>\_tools\harness\h11_D_keys.json --pad B` | `results[].run.commands_sha256` |
| `b5_baseline_compare.py --cases A1-rigid,A1-J1 --controllers C2` | `--cases` | `records[].commands_sha256`(`controller` == `C2`) |

- **[정의] 실행 10건, 비교 짝 8쌍**

| 스크립트 | 키(묶음, id) | 새 실행 | 비교 대상 |
|---|---|---|---|
| `s9_slope_fix_candidates.py` | (p3b, `base\|G1\|B\|top\|Fs0`), (g8, `slope\|edge\|top\|4.0\|ref\|none\|0\|proj`) | 옵션 없음 2 | `las_k1/u3_p3b_V0.json`, `u3_g8_V0.json` 같은 id |
| `r72_g6_screen.py` | `g6\|G1+J1@FL\|top\|Fs8`, `g6r\|rigid+J1@FL\|top\|Fs8` | 옵션 없음 2 | `las_k1/u3_C_V0.json` 같은 key |
| `s9_soil_slope.py --groups H8` | `H8\|rigid\|B\|top\|flat`, `H8\|G1\|B\|top\|flat\|FL:g20` | 옵션 없음 2 | `las_k1/u3_D_V0.json` 같은 id |
| `b5_baseline_compare.py` | `A1-rigid`, `A1-J1`(main) | 옵션 없음 2 + `--v5-setting V0` 2 | 같은 키의 두 팔끼리 |

- **[정의] 수 검사**: 도구는 위 표의 8키를 열거한다. 키마다 옵션 없는 출력에 정확히 1줄, 비교 대상 출력에 정확히 1줄이 있어야 한다. 0줄이거나 2줄 이상(중복 줄)이면 그 짝은 거짓이다.
- **[정의] 관문**: 8쌍 모두 같은 필드의 해시가 같으면 G-3 참이다. 하나라도 다르거나 수 검사가 거짓이면 G-3 거짓이고, H-3·H-4를 판정하지 않고 멈춘다(u3 원판 7절). 판정은 두 경로가 따로 낸다(사용자 결정 54의 4).
- **[정의] 커밋 정체성**: 옵션 없는 출력에는 `v5` 블록과 커밋 기록이 없다(`file_meta` = `{}`). 그래서 실행마다 `04_scripts/04_hydraulic/coupled/resume_k1_identity.py <out> --moment start` / `--moment end`로 감싸고, 그 기록의 커밋이 R2이고 clean이어야 한다. 다르면 원판 8.2 S-12다.
- **[정의] 출력**: `<OUT>\H-11\`(R16-14 4). 부산물(`_compare.csv`·`_cases.csv`·`_kstar.csv`)도 함께 둔다.
- **[참고]** 키 고른 근거: 스크립트마다 강체 1키와 토양 1키다. 토양 키는 K1 결정이 있는 줄(S-6 줄 포함)이라 옵션 경로가 관문 경로를 바꾸지 않았는지도 함께 본다. D 줄 강체 키는 python-expert 제안이다(처음 초안의 두 키가 모두 G1이었음). 8키 모두 R2 출력에 한 건씩 있고 태그는 `final_C4G2_LAS_K1`이다(python-expert 확인). `--ids-from`이 있으면 키를 2개로 좁힐 때 `v5_rerun.select_known`(295~305행)이 SystemExit를 내고, `--pad`는 `--ids-from` 없이 거부된다(191~192행). `s9_soil_slope.py`의 `--filter`는 부분 문자열이라 G1 11개가 잡힌다.
- **[참고]** 사전 예측 P-16: 8쌍 모두 같다. 근거는 V0 = "v5 플랜트 옵션 모두 끔"(u3 원판 1절)과 `v5_rerun` 옵션의 기본값 경로다.
- 결정 필요: **아니오**(사용자 결정 1, 54의 1·4, python-expert 확인 반영).

## R16-9. H-12: u3 g8 G-6 3키 T4h 확인 (사용자 결정 5·50의 3·51·54의 3, rev1 #5)

- **[사실]**
  - g8 VB 3키에서 이상 센서인데도 `WARN_ROD_PRESSURE_FALLBACK`이 났다: `slope|edge|top|4.0|FR|raised|20.0|proj`(RL D3, 25.0 s), `slope|rpB|top|4.0|FR|raised|20.0|proj`, `slope|edgeMr|top|4.0|FL|raised|20.0|proj`. D3은 수축 이동 진단이다(`two_pressure.py` 2216행). 원인은 하네스 로드 판독 모형의 산물이다(R16-15a).
  - u3 실행은 T4h를 남기지 않았다. `s9_slope_fix_candidates.py`에는 T4h 기록 인자가 없고, R2 안에 같은 명령으로 T4h를 남기는 다른 경로가 없다(python-expert 확인: `run_v5._t4h_request`는 steady·verdict 하네스 전용, r79 `R79_T4H_DIR`는 키 집합·바닥·실행 경로가 다름).
- **[정의]**
  1. **래퍼**: 기록 전용 포착 래퍼(R2 밖의 새 코드)로 R2 `run_harness.ps1` 39행(`u3_g8_VB`)의 argv를 돈다.
     - argv에서 `--ids-from`·`--pad`를 빼고 `--ids "<3키>"`(`;` 구분)로 좁힌다. 작업자는 `--workers 3`이다(작업자 수와 affinity는 명령 해시에 영향이 없어 R2와 다를 수 있고, 3의 해시 조건이 이를 확인한다). env는 R2 그 단계 Env(`@{}`) 그대로다. 인터프리터는 dynamics-dev `python.exe` 직접 호출이다.
     - 래퍼는 제어기·플랜트 계산을 바꾸지 않고 실행 뒤 값으로 T4h만 쓴다. 래퍼 파일은 추적 경로 밖 `<OUT>\_tools\harness\`에 두고, sha256은 실행 전 감사에서 고정해 판정서에 적는다.
     - **래퍼와 R2 러너의 차이(공개)**: ① 화면 스크립트를 `__main__`이 아니라 모듈 이름으로 불러온다. ② 레코드에 `t4h_capture` 키가 더해진다. ③ T4h meta `job.contact`에 실제 판정 이름이 들어간다. 이 차이가 계산에 영향을 주는지는 3의 정체성 조건과 4의 첫 파일 확인으로 드러난다.
     - 준비물의 `h11_h12_check.py`는 기계 점검만 한다. 6의 판정은 R4 도구가 한다.
  2. **T4h 형식**: r79 Dg-3 꼴(`resume_k1/h6_dg3_v4on_t4h/*.npz`와 같은 키).
     - 배열: `t_s`, `head_pressure_Pa`, `rod_pressure_Pa`, `motor_stroke_m`, `command_m_s`, `phase`, `seal_band_N`, `true_force_N`, `true_force_min_N`, `locked`, `lock_events`, `lower_reading_N`, `lower_estimate_N`
     - `meta_json` 키: `job`, `controller_tag`, `hydraulic_options`, `head_only_declared`(= `False`), `commands_sha256`, `fallback_start_s`, `lower_reading_rule`, `zero_offset_N`, `pressure_offset_allowance_N`, `pressure_offset_allowance_from_s`, `two_pressure_settings`, `F_min_N`, `period_s`, `events`, `tension_truth`, `extend_bound_check`, `true_force_rule`
     - 값의 출처: `lower_estimate_N`·`seal_band_N` = `verdict_runs.period_arrays(ctrl)`(`verdict_runs.py` 103~133·156~157행), `lower_reading_N` = `lower_estimate_N` + `seal_band_N`(COMBINED 판정, r79 1034~1037행, `r69_g8_screen.py` 121행), `fallback_start_s` = `ctrl.events`의 첫 `WARN_ROD_PRESSURE_FALLBACK:<leg>` 시각, 나머지 = `write_t4h_record`(312~351행).
  3. **정체성 조건**(모두 참이어야 그 키의 T4h를 쓴다)
     - 16자리 `records[].hash`가 `las_k1/u3_g8_VB.json`의 같은 id와 같다.
     - 64자리 `v5.logged_commands_sha256`이 R2 VB 값과 같다(전체 값의 원본은 `u3_g8_VB.json`, 앞 8자리 `59aa2262`·`95b0e051`·`0ffde01e`).
     - T4h `meta_json.commands_sha256`이 위 logged 값과 같다.
     - T4h 파일이 정확히 3개다.
     - 래퍼 실행을 `resume_k1_identity.py <out> --moment start` / `--moment end`로 감싸고, 커밋이 R2·clean이다.
  4. **첫 파일 확인 = 공식 폴더에 들이기 전 확인**(11.2 대체 점검): 세 키를 병렬로 돌리므로 T4h 3개가 먼저 `<OUT>\H-12\t4h_staging\`에 써진다. 그다음 차례는 다음과 같다.
     - (가) 첫 키(`slope|edge|top|4.0|FR|raised|20.0|proj`)의 파일만 공식 폴더 `<OUT>\H-12\t4h\`로 옮긴다.
     - (나) 그 폴더에 `t4h_replay.py --check-recorded`를 돌린다.
     - (다) `settings_equal`이 참이고 `recorded_lower_max_abs_N` = 0일 때만 나머지 두 파일을 옮긴다. 아니면(`checked_run_config`의 RuntimeError, `t4h_replay.py` 264~270행 포함) 옮기지 않고 5로 간다.
     - 판정서에는 이 차례와 staging·공식 폴더의 파일 목록·sha256을 적는다(공개).
  5. **어긋날 때의 대체 경로**(사용자 결정 54의 3): 3이나 4가 어긋나면 **멈추고 메시지 박스로 사용자에게 묻는다.** 사용자가 대체를 고르면 다음으로 돈다.
     - 대체 실행: 1과 같은 argv·env·3키, T4h를 run_v5 꼴(`resume_k1/h10_reuse_rerun_t4h/*.npz`와 같은 키: `t_s`, `head_pressure_Pa`, `rod_pressure_Pa`, `motor_stroke_m`, `command_m_s`, `phase`, `seal_band_N`, `true_force_N`, `true_force_min_N`, `locked`, `lock_events`, `meta_json`)로 남긴다. 출력 `<OUT>\H-12b\`.
     - S-15 건수: H-12 대체 3(H-12 3을 대신, 같은 묶음 값 3).
     - 정체성 조건: 3의 첫 넷(16자리 hash, 64자리 logged, T4h meta, 파일 3개)과 identity 기록. `--check-recorded`는 하지 않고, 그 사실을 판정서에 공개한다.
  6. **판정**(기록 묶음): `t4h_replay.py <out> <T4h 폴더>`(자기 설정, ③ 켬)와 `--check-recorded`(Dg-3 꼴일 때). v5 기준 개정 8 2절(VB T4h)·H-7 정의대로 읽는다. 잠긴 표본에서 하한 − 진값 > 0.6 kN이면 H-7이고 멈춘다. 잠기지 않은 꼬리와 수축 이동 표본은 기록이다(개정 8 92행).
     - **빈 창 막기**(사용자 결정 55의 2): 키마다 **실제 대체 다리**(`meta_json.fallback_start_s`가 있는 다리)에서 `fallback_start_s` 뒤의 잠긴 표본(T4h `locked` = 1이고 작용 명령 0인 판정 표본) 수를 센다. 네 다리 합계로 세지 않는다. 어느 키든 이 수가 0이면 그 키는 판정하지 않고 묶음을 `기록 불완전`으로 둔다. 수의 출처는 T4h 배열 `locked`·`command_m_s`·`t_s`와 `meta_json.fallback_start_s`다.
  7. **출력**: `<OUT>\H-12\`(결과 JSON, `t4h_staging\`, `t4h\` 3개, 정체성 기록). 6의 판정은 공식 폴더 `t4h\`의 파일만 읽는다.
- **[참고]** 사전 예측 P-17: 세 키 모두 잠긴 표본 초과 0이다(잠긴 표본 수 ≥ 1 전제). 근거는 1단계 T4h 388건의 최대 하한 − 진값 = −1.63 kN과 u3 g8 기록의 `margin_min_s_fallback` = +0.126 s다. 꼬리·수축 이동 표본의 초과는 예측하지 않는다. 남은 위험(python-expert): spawn 자식에 패치가 걸리지 않을 수 있음(패치는 모듈 최상위), import 순서와 스레드 env, 후보 클래스 `current`가 config를 바꾸는지 미확인. 이 위험들은 3·4의 확인으로 드러난다.
- 결정 필요: **아니오**(사용자 결정 50의 3, 51, 54의 3, python-expert 확인 반영).

## R16-10. 두 경로 하네스 도구 수정 목록 (사용자 결정 1·53·54)

1. **경로 1**(python-expert)
   - (a) J11: R16-6 읽기(`n_late_fallback_by_leg`, 적용 설정).
   - (b) H-9 격자 J-P3 등급(R16-7).
   - (c) 4.2 기록 확인: ABL 줄 기대값(R16-3).
   - (d) R8-1 태그 재계산: V0 블록 부재(R16-4).
   - (e) 하네스 도구의 봉인 확인 목록에 rev13~rev16 추가(R16-13).
   - (f) H-11 관문(R16-8), H-12 판정(R16-9), C-9~C-11 기록 항목과 정체성(R16-11, R16-11b, R16-14 3). `result.json`과 R16-11b 2의 파일을 직접 읽는다.
2. **경로 2**(경로 2 작성자)
   - (a) settle_v2: `residual_deg`·`attitude_error_deg`는 축별 [roll, pitch] 목록이다. 명세 398.3을 축마다 적용하고, `attitude_tol_deg`(축별)와 `attitude_ok`를 `result`의 같은 이름 값과 K-10 꼴로 대조한다.
   - (b) r72 계열(g6, 연구 C)의 등급: 기록의 `verdict`·`pass`를 그대로 쓰지 않는다. `gates`, `preloc_flag_ok`, G6-3, FAULT 기록에 rev6 R6-C3의 세 분기를 적용한다: `preloc_flag_ok` 참이면 `P3-8_demoted`(377), `preloc_flag_ok` 거짓 ∧ G6-3 참 ∧ FAULT 없음이면 `P3-8_preloc_loss`(U-S9-G6c), `preloc_flag_ok` 없음이면 판정 불가. 그다음 424.11.2·419.8·U-S9-G6d를 적용한다(u3 원판 4절 "같은 판정 함수").
   - (c) u6 키 계열 분류: u6 키(예: `G|g6|G1+J1@FL|top|Fs0|C2`)는 안쪽 키의 지면 토큰으로 나눈다. `+<토양>@<다리>`는 패치 계열이고, 토양 토큰만 있으면 균일 계열이다. 안쪽 키에 지면 토큰이 없을 때만 미분류(rev1 RV1-6, 균일로 다룸)다.
   - (d) S-5·저장 해시: R16-5 [정의].
   - (e) J11: R16-6 [정의].
   - (f) 봉인 확인 목록에 rev13~rev16 추가(R16-13).
   - (g) C-9~C-11 기록 항목과 정체성(R16-11 행 이름 표·각 행의 기록 항목, R16-11b 1, R16-11b 2의 입력 파일 목록, R16-14 4의 출력 위치). 새 파일 `path2/p2_x16.py`.
   - (h) H-11 읽기(사용자 결정 54의 4): R16-8 [정의] 글머리(비교 대상, 키 좁히기·비교 필드 표, 실행·짝 표, 수 검사, 관문, 커밋 정체성, 출력)로 G-3 참거짓을 따로 낸다.
3. **경로 2에 넘기는 글머리**(원판 9.2, 사용자 결정 53·54의 1·55의 1). 아래 표의 글머리만 준다. 경로 2 지시문에는 "rev16의 다른 절·글머리는 열지 않는다"를 넣고, 경로 2 판정서의 9.2 읽은 것 목록으로 확인한다. 경로 1의 코드·출력과 이 작성자의 검토 메모는 주지 않는다.
   - 경로 2 작성자는 S4에서 갈라진 브랜치에서 일하므로 rev16 전문 파일에 기술적으로 접근할 수 있다(사용자 결정 55의 1). 접근을 막지 않고 위 지시와 읽은 것 목록 확인으로 막는다. 판정서 한계 절에 그대로 적는다: "경로 2 작성자의 rev16 파일 접근은 기술적으로 막지 않았다. 다른 절을 열지 않는다는 지시와 경로 2 판정서의 읽은 것 목록으로 확인했다."

| 절 | 넘기는 글머리 | 넘기지 않는 글머리 |
|---|---|---|
| R16-1 | [정의] 1~3 | – |
| R16-2 | 표, [정의] 넷(S-15, 기록 묶음, `--k1-order-gate` 예외, 11.1·11.2 적용) | – |
| R16-3 | [정의] | [사실] |
| R16-4 | [정의] | [사실], [참고] |
| R16-5 | [정의] 1·2 | [사실] 공개, [참고] |
| R16-6 | [정의] 1·2 | [사실], [참고] |
| R16-7 | [정의] | – |
| R16-8 | [정의] 전부(비교 대상, 옵션 없음, 키 좁히기·비교 필드 표, 실행·짝 표, 수 검사, 관문, 커밋 정체성, 출력) | [사실], [참고] 둘 |
| R16-10 | 2 (a)~(h)와 이 3 | 1(경로 1 목록) |
| R16-11 | 공통 조건 [정의], 행 이름 표, 1의 끔 팔 기대값(S-2 판 섞임 예외 포함), 1의 P-18 읽기 전제, 각 행의 "기록 항목" 글머리 | 각 행의 바탕 행·하네스 근거·사전 예측·읽기, 격자·시간 근거 |
| R16-11b | 1, 2 | – |
| R16-14 | 4(출력 위치) | 그 밖 |

   - 이 판의 결함 목록이 두 경로 출력을 본 뒤에 정리된 것이라는 사실(R16-0 6)은 판정서 한계 절에 그대로 적는다: "R4 두 경로 도구의 수정 항목은 메인 세션과 도메인 검토가 첫 두 경로 출력을 대조해 정리했다. 그래서 재판정의 두 경로는 수정 항목의 선택에서 독립이 아니다. 각 수정의 구현과 재판정 값은 경로마다 따로 만들었다."
- 결정 필요: **아니오**(사용자 결정 1, 53, 54).

## R16-11. 추가 Chrono 확인 행 C-9~C-11 (사용자 결정 2·3·6·7)

- **[정의] 공통 조건**
  - 엔진은 SCM이다(`run_S9.py level`). 원판 6절 SCM 정체성(`--threads 4`, `OMP_WAIT_POLICY=PASSIVE`, P코어, 볼록 껍질 훅 fast, `MIXED_HULL_MODE` 없음)을 지키고, 직접 실행 행의 대체 키는 R16-11b 1이다. 어긋나면 S-4다.
  - 공통 꼬리: `--pad-variant dwg_rear250 --level top --settle-dashpot zrp --threads 4 --pressure-grade normal --seed 20261026`. 아래 표의 `T`가 이 꼬리다.
  - V0 = `--expect-controller final_C4G2_LAS_K1`(v5 인자 없음). VB = `--expect-controller final_C4G2_P3_LAS_K1` + VB 인자 `--flow-eta-v 0.85 --flow-dp-comp-bar 10 --flow-dp-unload-bar 20 --flow-width-bar 1 --flow-law priority --valve-tau-s 0.1 --rod-release-force --lock-overlap-ratio 0.02 --lock-closing-delay-s 0.05 --lock-window-follows-plant --extend-start-tracked`(= R2 `s9_batch.v5_vb_argv()`, C-5 VB 행과 같음).
  - 실행 방식: 직접 실행(`run_S9.py level … --case <행 이름> --out-root <OUT>\<묶음>\`). 정체성은 R16-11b 1, 배치는 R16-14 5다.
  - 모두 기록 행이다. 원판 8.1 등급을 만들지 않는다(R16-11a).
- **[정의] 행 이름과 argv(글자 그대로)**

| # | 행 이름(`--case`) | argv(`run_S9.py` 뒤, `T` = 공통 꼬리) |
|---|---|---|
| 1 | `R4368X_G1_B_top_Fs4_V0_gateon` | `level --soil G1 T --fs-kN 4 --grid 0.02 --crawler-grid 0.04 --duration 120 --imu-grade ideal --expect-controller final_C4G2_LAS_K1 --approved --case R4368X_G1_B_top_Fs4_V0_gateon` |
| 2 | `R4368X_G1_B_top_Fs4_V0_gateoff` | `level --soil G1 T --fs-kN 4 --grid 0.02 --crawler-grid 0.04 --duration 120 --imu-grade ideal --k1-order-gate off --expect-controller final_C4G2_LAS --approved --case R4368X_G1_B_top_Fs4_V0_gateoff` |
| 3 | `R4368X_rigidS1FL_B_top_Fs4_V0` | `level --soil S1 --rigid-base FL T --fs-kN 4 --grid 0.02 --duration 160 --imu-grade ideal --expect-controller final_C4G2_LAS_K1 --approved --note "model-limit stress case: S1 patch under a front pad on a rigid base, outside the Bekker validity range (436.8 rev16 C-10)" --case R4368X_rigidS1FL_B_top_Fs4_V0` |
| 4 | `R4368X_rigidS1FL_B_top_Fs4_VB` | 3과 같고 `--expect-controller final_C4G2_P3_LAS_K1` + VB 인자, `--case R4368X_rigidS1FL_B_top_Fs4_VB` |
| 5 | `R4368X_rigidS1FR_B_top_Fs4_V0` | 3과 같고 `--rigid-base FR`, `--case R4368X_rigidS1FR_B_top_Fs4_V0` |
| 6 | `R4368X_rigidS1FR_B_top_Fs4_VB` | 5와 같고 `--expect-controller final_C4G2_P3_LAS_K1` + VB 인자, `--case R4368X_rigidS1FR_B_top_Fs4_VB` |
| 7 | `R4368X_J2_B_top_Fs0_L2_V0` | `level --soil J2 T --fs-kN 0 --grid 0.01 --crawler-grid 0.04 --duration 120 --imu-grade normal_zeroed --expect-controller final_C4G2_LAS_K1 --approved --case R4368X_J2_B_top_Fs0_L2_V0` |
| 8 | `R4368X_J2_B_top_Fs0_L2_VB` | 7과 같고 `--expect-controller final_C4G2_P3_LAS_K1` + VB 인자, `--case R4368X_J2_B_top_Fs0_L2_VB` |

  - 묶음: C-9 = 1·2, C-10 = 3~6, C-11 = 7·8. 출력은 `<OUT>\C-9\`, `<OUT>\C-10\`, `<OUT>\C-11\`(R16-14 4).
- **[참고] 격자·시간 근거(cad-expert)**: C-10 `--grid 0.02`는 `run_S9.py` 225행 `P3B_PAD_GRID_M`의 S1 = 0.02와 저장 S1 행 8개. C-11 120 s는 J2 균일 선례(READY 74~82 s). C-10 160 s는 저장 G6 S1 행(`G6_G1_B_top_Fs4_spS1FL`)과 같은 길이(하네스 g6 READY 62.9~66.0 s, SCM S1은 계속 침하). `--crawler-grid`는 `--rigid-base`와 함께 쓸 수 없다.

1. **C-9 (S-6 확인, 사용자 결정 2)**: G1 균일, 관문 켬/끔 단일 변수 짝, V0
   - **[정의] 끔 팔 기대값**(C-4 끔 팔과 같은 꼴): 태그 `final_C4G2_LAS`, `c2_setup.k1_order_gate` = `off`, `c2_setup.k1_order_gate_effective` = false, `controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate` = false, `liftoff_approach_slow.settings` 9값은 프리셋(LAS-b 켬), `c2_setup.las_off` 없음 또는 거짓. 켬 팔은 원판 4.2 그대로다. 한 묶음 C-9 안에 `final_C4G2_LAS_K1`과 `final_C4G2_LAS` 두 판이 있는 것은 정의이므로 원판 8.2 S-2의 "한 묶음 안에 두 판이 섞였다"에 해당하지 않는다(이 묶음에 한한 예외).
   - **[정의] 기록 항목**: 두 팔의 `decisions`(dP 포함), 토양 모드 시작 시각, LOC 시각, 두 팔 `controller_commands.npz` sha256 같음 여부, 최대 행정 [mm], 끝 rut 틈 [mm], P3-1~P3-9, 첫 READY [s], rc, 마지막 표본 시각 [s].
   - [참고] 바탕 행: 저장 `batch_JOURNAL-AUGER_20261031_165543/P3b_G1_B_top_Fs4`(`--expect-controller final_SGS_R4`), 태그만 바꿈.
   - [참고] 하네스 근거: S-6 67줄은 모두 G1 균일이고 결정 67건이 모두 dP = −5주기(t_S − t_P = 0.5 s). V0 p3b `base|G1|B|top|Fs4`는 n_P 213, n_S 218에서 막혔다. VB G1 줄은 대부분 R4c30 평가 자체가 없다.
   - [참고] 사전 예측 P-18: 두 팔 모두 `slope_clearance_margin.order_gate.decisions` = [](토양 모드 시작 없음)이고 두 팔의 `controller_commands.npz` sha256이 같다(437.1). 근거: 저장 Chrono G1 행이 모두 `soil_mode_t_s` = null, R4c30 적용 0(G1 균일 6행: 패드 B 3·A 3, G1 일색이지만 배치가 다른 10행: `batch_k1soil_G1_20261105`, `--soil-patch FL:G1`, 60 s, `batch.json` 없음).
   - **[정의] P-18 읽기의 전제**(빈 창 막기): 두 팔 모두 rc 0, 마지막 표본 시각 ≥ `--duration` − 0.1 s, 첫 READY 있음, 같은 `--threads`(4), 둘 다 pcore. 하나라도 거짓이면 P-18을 읽지 않고 묶음을 `기록 불완전`으로 둔다.
   - [참고] 읽기: P-18이 맞으면 S-6 67줄을 "하네스 G1 토양 모드 시작에 따른 하네스 전용 현상, 엔진에서는 R4c30 미해당"으로 읽고 사용자에게 S-6 처리(기록)를 묻는다. 켬 팔에 dP ≤ 0으로 막힌 결정이 있으면 S-6이 엔진에서도 성립하므로 두 팔의 행정·틈 차와 함께 묻는다(원판 8.2 S-6).
2. **C-10 (G-5 확인, 사용자 결정 3)**: g6 강체 바탕 + S1 앞 패드 패치, F_s 4, 상단, VB/V0 × FL·FR
   - **[정의] 기록 항목**: 다리별 F^a_min·F^t_min과 그 시각, F < F_min 시간, F < F_min + 2 kN 시간(원판 7.4 정의), G6-1~G6-7, P3-3, 끝 단계, 최대 행정, 패치 다리 침하 [mm], rc, 마지막 표본 시각 [s].
   - [참고] `--rigid-base <LEG> --soil S1`: "rigid SMC base … with --soil SCM under LEGS only"(R2 `run_S9.py` 도움말).
   - [참고] 하네스 근거: VB 최소 실제 F_cyl 5.75 / 6.84 kN, V0 11.46 / 10.20 kN(FL / FR, F_min 9.415 kN). VB 실패 항목 G6-3·G6-7, V0 G6-7(U-S9-G6c FLAG).
   - [참고] **모형 타당 범위 밖**: 저장 Chrono `G6_G1_B_top_Fs4_spS1FL`(`batch_G6P_20261029_144418`) 행 note "S1 patch under a front pad, p/q_ult about 9.5 = outside the Bekker validity range; SCM keeps sinking without a bearing failure, so a pass or a fail is not a physical prediction". C-10도 같은 앞 패드 S1이라 F_min 위아래는 물리 예측이 아니고, 판정서에도 그렇게 적는다.
   - [참고] 사전 예측 P-19: 같은 다리에서 VB 최소 F_a ≤ V0 최소 F_a(방향만). 크기와 F_min 위아래는 예측하지 않는다.
   - [참고] 읽기: G-5(u3 원판 5.1 "VB 고유 실패 → 묻는다")의 답에 쓰는 자료다. C-10 결과로 G-5 등급을 자동으로 바꾸지 않는다.
3. **C-11 (seedext 확인, 사용자 결정 6)**: J2 균일, 상단, F_s 0, VB/V0, 잡음 L2 상당
   - **[정의] 기록 항목**: 첫 LOC 시각, LOC 주기의 1 ms 크롤러 법선 최대 [N]과 그 값 / W, 0.01 W 위아래, LOC 취소 수, 첫 READY, rc, 마지막 표본 시각 [s].
   - [참고] 하네스 L2 = 압력 normal + IMU `normal_zeroed`(`r79_sensor_screen.py` 25·132행), Chrono `--imu-grade` 선택지에 `normal_zeroed`가 있다(`run_S9.py` 4205행).
   - [참고] 하네스 근거: seedext `L2|g6|56|ref|J2|top|Fs0` VB 16/25, V0 1/25가 r79 S-5(LOC 때 크롤러 ≥ 0.01 W, 거짓 LOC)로 실패했다(stage3 U-4와 같음).
   - [참고] 사전 예측: 하지 않는다. 시드 하나(20261026, 하네스 seedext와 잡음 열이 다름)이고, 하네스와 엔진의 J2 LOC 시점 차이가 알려져 있다(437.5).

### R16-11a. C-9~C-11과 H-11·H-12를 436.8 결론에 넣는 방식 (사용자 결정 7, 50의 2)

- **[정의]**
  - H-11은 관문이다. 결과가 H-3·H-4 판정의 전제가 된다.
  - H-12와 C-9~C-11은 **436.8 판정서 안의 별도 확인(기록 묶음)**이다. 원판 8.1의 묶음 등급과 v5 종합 판정(판정 묶음 상태의 최악)에는 들어가지 않는다.
  - S-6(C-9), G-5(C-10), G-6(H-12)의 멈춤 질문에 대한 답의 근거로 판정서에 싣는다. seedext(C-11)는 알려진 한계 문장의 근거로 싣는다.
- [참고] 근거: 결과를 본 뒤에 고른 행이라 등급에 넣으면 사후 선택이 등급을 바꾼다(원판 9.2, rev14 R14-2). C-10은 모형 타당 범위 밖, C-11은 시드 하나다. 기존 기록 행(C-8 O-C5)도 같은 지위다. 고르지 않은 안: C-9~C-11을 판정 묶음으로 두는 안(비권고).
- 결정 필요: **아니오**(사용자 결정 50의 2).

### R16-11b. C-9~C-11의 정체성과 기록 항목을 내는 곳

1. **[정의] 정체성(rev15 R15-6 대체의 확장)**
   - rev11 R11-4 5항("`code_at_launch` 없음 = S-12")의 대체(rev15 R15-6, PS-c G-S 1행)를 C-9~C-11 8행으로 넓힌다.
   - 행마다 다음 기록이 있어야 한다. 하나라도 없거나 어긋나면 S-12(커밋)·S-4(SCM 정체성)다.
     - 시작 정체성 파일(gs_identity 꼴, 정체성 도구 `x16_identity.py`): HEAD = R2 `b9f5707d7f3f7a26230b25f4edbc1fec587ca612`, `git status --porcelain --untracked-files=no` 빈 출력, `env`(start env), 금지 env 다섯의 유무(`OUTRIGGER_LOC_SHADOW`, `OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED`, `OUTRIGGER_HULL_HOOK_DLL`, `OUTRIGGER_HULL_HOOK`, `MIXED_HULL_MODE`: 모두 없음), DLL sha256.
     - 끝 정체성 파일(같은 도구 `post`, 행 끝): 끝 HEAD, `git status --porcelain --untracked-files=no`, `git reflog` 5항목, 금지 env 다섯의 유무를 기록하고 시작 파일과 대조한다. HEAD가 시작과 같고, 시작 시각 뒤에 새 reflog 항목이 없어야 한다(있으면 도구 exit 1). 금지 env 다섯은 시작과 끝 양쪽에 기록한다.
     - `result.json`: `code_state.git_at_start` = R2, `num_threads_chrono` = 4, `placement` 마스크(= 그 행의 칸 마스크, R16-14 5)와 `placement.omp_wait_policy` = `PASSIVE`, `hull_hook.mode` = `"fast"`, `hull_hook.dll_sha_validated` = true, `hull_hook.dll_sha256` = `cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15`.
   - 원판 6절 SCM 칸의 대응: start env = 시작 정체성 파일 `env`, 풀 = `placement` 마스크, `OMP_WAIT_POLICY` = `placement.omp_wait_policy`, 훅 = 위 hull 세 값.
   - 정체성 도구 `x16_identity.py`의 sha256은 실행 전 감사에서 고정하고 판정서에 적는다. 다른 Chrono 행에는 R11-4 그대로다.
2. **[정의] 기록 항목을 내는 곳**
   - R3 `chrono_rows_judge_4368.py`는 `code_at_launch`가 필수이고 `R4368X_*` 행 id가 manifest·`G6_ROW_NAMES`에 없다. R16-12가 이 도구를 R3..R4 diff 0으로 두므로 C-9~C-11의 기록은 이 도구로 내지 않는다.
   - **경로 1**: R4의 `resume4368_judge.py` 하위 명령이 각 행 폴더를 직접 읽는다(R16-11 기록 항목, 1의 정체성).
   - **경로 2**: `path2/p2_x16.py`가 따로 읽는다(원판 9.1 C-8 행 꼴).
   - 두 경로가 읽는 행 폴더 파일(`run_S9.py level` 행): `result.json`, `controller_commands.npz`, `step_series.npz`, `r8_series.npz`, `completion_series.npz`, `flow_series.npz`(VB 행만, `--flow-eta-v`가 있을 때), `record/record.npz`, `record/meta.json`, 그리고 1의 정체성 파일 둘. `completion_series.npz`는 모든 행에 필수다.
   - 기록 항목은 K-10 꼴로 대조한다. 맞지 않으면 그 행은 `기록 불완전`이고 python-expert에 원인 확인을 넘긴다(기록 묶음이라 S-13 아님).
   - 이 행들에는 R3 Chrono 도구의 S-12 판정을 쓰지 않는다. 1로 대신한다.
- 결정 필요: **아니오**(사용자 결정 2·3·6·7, cad-expert 확인 반영).

## R16-12. 도구 커밋 R3·R4의 구조와 허용 목록

- **[정의] 순서**(방법 1: 봉인 먼저. 메인 checkout의 HEAD는 새 실행이 끝날 때까지 R2 그대로)
  1. **R3 통합 브랜치**(메인 세션, 만들어졌음): R2 `b9f5707` 위의 통합 브랜치 `z4373-r3v2`(worktree `C:\workspace\z4373-r3v2`)에 rev15 R15-2 순서 4의 차례대로 `--no-ff` 병합했다: `z4372-seal`(S3 `cc0d9b8`) → `z4372-p1judge`(끝 `4653a52`) → `z4372-p2chrono`(`5a84e94`) → `z4372-p2t45`(끝 `a36c711`) → `z4372-manifest`(끝 `fb09350`). 마지막 병합 커밋 **R3 = `576eb87`**이다. rev15 R15-2의 R3 조건과 manifest 재생성 확인을 이 브랜치에서 한다. 이 문장은 rev15 R15-2 순서 4의 "메인 checkout에서 병합"을 "통합 브랜치에서 병합하고 메인은 뒤에 fast-forward"로 고쳐 쓴다(R3의 커밋·blob은 같다).
     - **R3 대상 manifest 끝 = `fb09350`**(사용자 결정 56). rev15 R15-2 순서 1·4와 R15-5가 R3 병합 대상을 `z4372-manifest` `57828fc`로 고정한 것을 이렇게 고쳐 쓴다. `fb09350`은 `57828fc`의 자식이고, 시험 파일 `05_tests/unit/test_v5_resume_4368_chrono_rows.py` 한 파일만 고친다(+23/−2, rev15 R15-2 허용 목록 (라) 안). manifest json(LF blob `f00cd5d8…`), 생성기, 판정 도구는 바뀌지 않았다.
     - [사실] 고친 이유: `57828fc`는 `cmd_manifest`가 O-C5 행을 `manifest_oc5_rows`로 바꿨는데 시험 기대값을 그대로 두어, `57828fc` 하나로도 `test_stored_manifest_table_and_scope`가 실패했다. 같은 파일의 `test_c4_and_c8_diffs`는 O-C5 state 파일이 있으면 R2 때부터 실패했고, 이제 state를 명시한다. `576eb87`에서 관련 시험 5개 파일이 199 passed다(O-C5 state가 있을 때와 없을 때 같다). `b9f5707..576eb87`의 변경 파일은 22개다.
     - [사실] **쓰지 않는 R3 후보(공개)**: 처음 만든 `z4373-r3`(끝 `99ad4dc`, `57828fc` 병합)는 시험 1건 실패로 쓰지 않는다. 브랜치는 지우지 않고 기록으로 남긴다. `99ad4dc`와 `576eb87`의 차이는 위 시험 파일 하나뿐이다.
     - 이 고쳐 씀은 Chrono 결과 일부와 R3 후보의 시험 결과를 본 뒤의 개정이다. 판정서에 그렇게 적는다.
  2. **봉인 S4**: 이 판의 봉인 파일 커밋 S4를 R3 `576eb87` 위에 만든다(부모 = R3 = 봉인 기준 커밋 SEAL_COMMIT = `576eb87`). 그래서 rev15 파일이 S4 아래에 있고 R16-13 봉인 목록 시험이 S-1로 깨지지 않는다.
  3. **하네스 도구 브랜치**: 경로 1 `z4373-p1harness`와 경로 2 `z4373-p2harness`를 S4에서 가른다. 각 작성자는 이 브랜치에서 R16-10 1·2를 구현하고 하네스 도구 봉인 목록에 rev13~rev16을 넣는다.
  4. **R4 통합 브랜치**(메인 세션): S4에서 `z4373-r4`를 만들고 `z4373-p1harness` → `z4373-p2harness`를 `--no-ff` 병합한다. 마지막 병합 커밋이 **R4**다. 병합에서 충돌을 손으로 풀었다면 그 결과를 판정 전 감사가 본다. S4가 R3 위에 있으므로 S3·S4의 `.gitattributes` 줄 추가는 차례로 쌓이고 충돌하지 않는다.
  5. **새 실행**(R16-14): 메인 checkout R2에서 PS-c `.done` 뒤에 시작한다. 끝날 때까지 메인에는 커밋·병합·fast-forward를 하지 않는다.
  6. **R3 적용과 Chrono 판정**: 새 실행이 모두 끝난 뒤 메인을 `git merge --ff-only z4373-r3v2`로 R3 `576eb87`에 맞춘다. **ff 전에 다음이 모두 참이어야 한다.** ff 뒤에는 R2에서 다시 돌릴 길이 없으므로, 재실행이 필요한 경우는 모두 ff 전에 끝낸다.
     - Chrono 8행 모두 x16 `post`가 ok다.
     - `h11_h12_check.py`가 종료 0이다. 또는 H-12가 대체 경로로 갔으면 H-12b 실행까지 끝났다.
     - 러너 로그 폴더마다 `tools/verif/log_errors.py`가 종료 0이다: `<OUT>\_runners\logs_*`, `<OUT>\H-11\logs_A`, `<OUT>\H-11\logs_B`, `<OUT>\H-12\logs`.
     - (위 조건은 ff 전 조건이다.) ff 뒤: **C-1~C-8 판정, C-5 경로 2 재판정, R3 G-S 읽기는 R4 적용 전에 R3 도구로 끝낸다.** 이 문장이 rev15 R15-1 3의 둘째 문장(R2 뒤 허용 커밋과 R3 뒤 커밋 제한)을 대신한다: R2 뒤 메인의 커밋은 R3와 R4(와 그 안의 브랜치 커밋)만 허용하고, R3 적용 뒤 R4 적용 전, R4 적용 뒤 판정이 끝날 때까지는 판정서·감사 기록만 더한다.
  7. **R4 적용과 하네스 재판정**: 6이 끝난 뒤 메인을 `git merge --ff-only z4373-r4`로 R4에 맞춘다. 하네스 재판정(R16-1)과 H-11·H-12·C-9~C-11의 판정·기록을 R4 도구로 한다. 모든 판정 도구의 `--git-at-start`는 R2다.
  8. **R4 뒤 Chrono 판정은 하지 않는다.** R4가 고치는 파일에 Chrono 판정 하위 명령이 함께 들어 있기 때문이다: 경로 2 `path2/p2_4368.py`의 `chrono`·`openloop`·`oc5k`, 경로 1 `resume4368_judge.py`의 `oc5`·`fmin-time`. 이 하위 명령의 판정 출력은 R3에서 낸 것만 쓴다. R4 뒤 Chrono 재판정이 필요하면 새 봉인 개정을 거친다. C-9~C-11의 기록은 R16-11b 2대로 R4 도구가 낸다.
  - 메인 세션이 1·2·4의 통합 브랜치를 만들고, 하네스 도구 작성자는 3의 브랜치(S4 위)에서 작업한다.
- **[정의] R4 조건**(모두 참이어야 하네스 재판정을 한다. 거짓이면 판정하지 않고 멈춘다, 원판 8.2 S-11)
  - `git diff --name-only b9f5707..R4 -- 03_src 02_params`가 비어 있다.
  - `git diff --name-only b9f5707..R4 -- 04_scripts`가 정확히 다음 9개 안이다: R3 몫 `04_scripts/02_chrono/chrono_rows_judge_4368.py`, `04_scripts/02_chrono/chrono_rows_judge_4368_README.md`, `04_scripts/02_chrono/v5_resume_4368_chrono_rows.py`, R4 몫 `04_scripts/04_hydraulic/coupled/judge_stage1_4368.py`, `judge4368_common.py`, `u3_judge_4368.py`, `h8_noise_judge_4368.py`, `h6_judge_4368.py`, `README_judges_4368.md`. 이 조건으로 하네스·Chrono 러너와 실행 경로 전부가 R2..R4 diff 0이다. 확인 대상으로 이름을 적으면 `run_S9.py`·`run_S8C.py`·`run_S6C.py`·`s9_batch.py`, `04_scripts/03_control/` 전부, `04_scripts/01_dynamics/` 전부, rev13 R13-2 표에서 "H-1 닫힘" 칸이 `예`·`예(플랜트)`·`예(이벤트 경로)`·`러너`·`단계 생성`인 행의 파일 14개(`run_v5.py`, `d1_runs.py`, `verdict_runs.py`, `verdict_metrics.py`, `resume_k1_record.py`, `v5_rerun.py`, `u3_reuse.py`, `r67_g1_screen.py`, `s9_soil_slope.py`, `s9_settle_rejudge.py`, `s9_slope_fix_candidates.py`, `run_mast_flex_c2_check.py`, `run_s6_slope_boundary_check.py`, `resume_k1_steps.py`), 그리고 R13-1이 적은 변경 없는 경로 파일(`d1_rows.py`, `harness_flow.py`, `harness_hydraulics.py`, `run_control_comparison.py`, `s9_soil_closed_loop.py`, `c2py_r8d1_closed_loop.py`), `las_t3_dg3.py`, `r79_L3L4_final.py`, `r79_sensor_screen.py`, `r72_g6_screen.py`, `b5_baseline_compare.py`, `resume_k1_identity.py`다.
  - Chrono 판정 도구(`chrono_rows_judge_4368.py`, 그 README, `v5_resume_4368_chrono_rows.py`, `chrono_rows_manifest.json`, `v5_resume_4368/path2_chrono/` 전부)는 R3..R4 diff 0이다.
  - `git diff --name-only R3..R4`의 모든 파일이 다음 허용 목록 안이다.
    - (가) `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev16.md`, `…_rev16.sha256`, `…_rev16_seal_candidate_draft.md`
    - (나) `.gitattributes`에 (가) 세 파일의 `-text` 줄 3개만 더한 것(지운 줄 0)
    - (다) 경로 1: 위 R4 몫 `04_scripts/04_hydraulic/coupled/` 여섯 파일, `06_analysis/02_control/verif_matrix/scripts/resume4368_judge.py`, `05_tests/unit/test_judges_4368.py`, `test_judges_4368_h6_h8.py`, `test_resume4368*.py`(새 파일 `test_resume4368_rev16.py` 포함)
    - (라) 경로 2: `06_analysis/02_control/verif_matrix/v5_resume_4368/path2/` 아래 `README.md`·`p2_4368.py`·`p2_u3.py`·`p2_v5j.py`·`test_p2_4368.py`·`test_p2_u3.py`·`test_p2_v5j.py`·`p2_x16.py`(새)·`test_p2_x16.py`(새), `path2_v5c/` 아래 `README.md`·`p2v5c_common.py`·`p2v5c_grid.py`·`p2v5c_noise.py`·`p2v5c_stage1.py`·`test_p2v5c.py`
    - (마) rev8 R8-4의 판정서·감사 기록, `00_docs/decision_log.md`·`00_docs/00_roadmap.md`·`00_docs/handoff/session_handoff.md`
  - R4 blob 표: R4를 만든 뒤 (다)·(라) 파일의 `git show R4:<파일>` LF 바이트 sha256 표를 판정서 부록에 싣는다. 판정 전 감사가 감사한 브랜치 끝 blob과 대조한다. R4 blob과 다른 도구로 낸 출력은 쓰지 않는다.
- [참고] `z4372-p2chrono`(5a84e94)가 이미 `path2/p2_4368.py`·README·`test_p2_4368.py`·`path2_v5c/p2v5c_common.py`(`P2_CORE_SHA` 424e12f9 → 0ccc5186)·README를 고쳤다. 하네스 도구 브랜치를 R3 위(S4)에서 가르는 것은 이 겹침의 병합 충돌을 없애기 위해서다(봉인 전 감사 차단 1).
- 결정 필요: **아니오**(사용자 결정 1, 감사 차단 1 반영).

## R16-13. 봉인 확인 목록

- **[정의]** 이 절은 rev15 R15-7 셋째 글머리("하네스 판정 도구와 그 밖의 도구 목록은 rev12까지 그대로")를 하네스 판정 도구에 한해 고쳐 쓴다.
- **[정의]** R4의 경로 1 하네스 도구(`judge4368_common.py`의 봉인 목록과 그것을 읽는 하네스 판정기, `resume4368_judge.py`)와 경로 2 하네스 도구(`path2/p2_4368.py`, `path2_v5c/p2v5c_common.py`의 봉인 목록)는 rev13·rev14·rev15·rev16 파일과 봉인 sha를 넣는다. 두 경로를 같게 한다. 다르거나 없으면 원판 8.2 S-1이다.
- **[정의]** Chrono 판정 도구는 rev15 R15-7 그대로다(rev15까지). Chrono 도구에 대한 rev16 확인은 `tools/verif/seal_check.py`로 한다.
- 결정 필요: **아니오**(두 경로 대칭).

## R16-14. 새 실행의 커밋·위치·배치 (사용자 결정 50의 4)

1. **[정의] 커밋·위치**: H-11·H-12·C-9~C-11의 실행 코드는 R2 `b9f5707`이다. 실행은 **메인 checkout**(R2, clean)에서, 지금 도는 실행(PS-c 2행)이 모두 끝나고 `.done`이 써진 뒤에 한다. 별도 worktree에서는 실행하지 않는다.
   - 시작 관문: 모든 러너는 `<OUT>\_go.flag`와 PS-c `06_analysis\02_control\verif_matrix\v5_resume_4368\run_b9f5707\c2_oc5\logs_c2_psc\c2_psc2.done`을 함께 기다린다. 메인 세션은 `.done`을 확인한 뒤에만 `_go.flag`를 만든다.
2. **[정의] 병합 시점**: R3·R4의 메인 적용은 새 실행이 모두 끝난 뒤다(R16-12 6·7). 이 문장이 rev15 R15-1 3의 R3 병합 시점을 늦춰 고쳐 쓴다. 새 실행 중에는 메인에 커밋·병합·fast-forward를 하지 않는다(원판 A-5 둘째 문장, S-12). 통합 브랜치와 도구 브랜치의 커밋은 메인의 HEAD·작업 트리를 바꾸지 않는다.
3. **[정의] 정체성 점검**(실행 전 감사가 본다)
   - 실행 전(묶음마다 1회, Chrono는 R16-11b 1의 시작 파일로 행마다도 남김): HEAD = `b9f5707d7f3f7a26230b25f4edbc1fec587ca612`, `git status --porcelain --untracked-files=no` 빈 출력, DLL sha256 `cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15`, 금지 env 다섯(`OUTRIGGER_LOC_SHADOW`, `OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED`, `OUTRIGGER_HULL_HOOK_DLL`, `OUTRIGGER_HULL_HOOK`, `MIXED_HULL_MODE`) 없음, Chrono start env `OMP_WAIT_POLICY=PASSIVE`·`OUTRIGGER_PLACEMENT=pcore`·`OUTRIGGER_PCORE_MASK=<칸 마스크>`.
   - 실행 뒤(Chrono 행마다): R16-11b 1의 `result.json` 값과 끝 정체성 파일. 어긋나면 S-4(훅·스레드·풀) 또는 S-12(커밋)다.
   - 하네스 실행(H-11·H-12): 실행마다 `resume_k1_identity.py <out> --moment start` / `--moment end`. 커밋 = R2·clean. env는 R2 `run_harness.ps1`의 해당 단계 Env에서 `R72_FILTER` 추가와 `R72_AFFINITY` `0x00FF0000` → `0x0F000000`만 다르다(R16-8, 사이드카 `<OUT>\H-11\h11_argv_env_vs_R2.json`). 인터프리터는 dynamics-dev `python.exe` 직접 호출이다.
   - **하네스 금지 env 증명**: 하네스 각 실행 앞에 `harness_env_guard` 단계를 둔다. 같은 러너의 형제 단계인 이 단계가 러너 env(WMI로 뜬 러너의 env 블록, 그 단계의 `os.environ`)에서 금지 env 다섯의 유무를 기록하고, 하나라도 있으면 exit 1로 멈춘다. 실행 단계의 단계별 Env에 금지 키가 없다는 것은 steps JSON에서 정적으로 확인한다. 이 둘로 원판 4.2의 하네스 금지 env를 증명한다.
   - 정체성 도구 `x16_identity.py`와 H-12 래퍼의 sha256은 실행 전 감사에서 고정한다.
   - 정체성 기록에 남는 규칙 sha는 `<OUT>\_tools\rows.json`의 `rules_label`에서 읽는다. 봉인 뒤 메인 세션이 `regen.ps1 -RulesLabel "rev16 sealed <sha>"`로 준비물을 다시 만들어 이 값을 봉인 sha로 맞춘다. 실행 전 감사가 그 값을 본다.
4. **[정의] 출력 위치**: `<OUT>` = `C:\workspace\outrigger_control\07_results\S9\R4368X_b9f5707_20261115_013947\`(git 무시 경로, `batch_` 접두 없음). 하위 폴더 `H-11\`, `H-12\`(대체 경로면 `H-12b\`), `C-9\`, `C-10\`, `C-11\`, 정체성 도구 `<OUT>\_tools\x16_identity.py`. 판정서에는 폴더 전체 경로와 정체성 파일·도구의 sha256을 적는다.
5. **[정의] Chrono 배치**(cad-expert 실행 준비, 칸마다 4스레드, `OUTRIGGER_PCORE_MASK`로 고정, 칸 안에서는 차례로 2행)

| 칸 | 마스크 | 첫 행 | 둘째 행 |
|---|---|---|---|
| X1 | `0x0F00` | `R4368X_J2_B_top_Fs0_L2_V0` | `R4368X_rigidS1FL_B_top_Fs4_VB` |
| X2 | `0xF000` | `R4368X_J2_B_top_Fs0_L2_VB` | `R4368X_rigidS1FR_B_top_Fs4_V0` |
| Y1 | `0x000F` | `R4368X_G1_B_top_Fs4_V0_gateon` | `R4368X_rigidS1FR_B_top_Fs4_VB` |
| Y2 | `0x00F0` | `R4368X_G1_B_top_Fs4_V0_gateoff` | `R4368X_rigidS1FL_B_top_Fs4_V0` |

   - 행마다 시작 정체성(행 직전) → `run_S9.py` → 끝 정체성(행 직후)을 차례로 남긴다. 각 행 `result.json`의 `placement` 마스크가 그 칸 마스크와 같아야 한다.
   - 하네스 H-11·H-12의 배치는 compute-scheduler-expert가 정한다. 30분이 넘는 묶음은 `reserve.py`로 예약한다.
   - [참고] SCM 8행 예상 약 2.7~3.3 h(cad-expert 추정).
6. **[정의]** 원판 8.2 S-12("한 묶음 안 커밋이 둘 이상")는 새 묶음마다 R2 하나로 판단한다.
- 결정 필요: **아니오**(사용자 결정 50의 4, cad-expert 실행 준비 반영).

## R16-15. G-5·J-P3·S-6·G-6·seedext의 처리 (사용자 결정 2~6·51)

1. **G-5**(사용자 결정 3): 정답 집합은 경로 1의 5키다: `H9|J1|B|top|roll_pos@k0.6`, `g6r|rigid+S1@FL|top|Fs4`, `g6r|rigid+S1@FR|top|Fs4`, `slope|edge|top|4.0|RL|raised|20.0|proj`, `slope|edgeMr|top|4.0|RR|raised|20.0|proj`. 단, R4 재판정에서 두 경로가 같은 집합을 내야 한다(R16-1 3).
   - g8 두 키(T2, 올린 다리 래치 > 3.0 s)와 h9 k0.6(P3-5, R_c 0.6 > J1·B 오른쪽 낮음 운용 권고 0.5)은 VB 한계로 기록한다. u3 원판 5.1의 묶음 문구는 "VB 고유 실패 5(한계 기록 3, 확인 중 2)"로 쓴다.
   - g6 `rigid+S1@FL`·`@FR`의 처리는 C-10 결과를 받아 사용자가 정한다(R16-11 2).
2. **J-P3 2개 시나리오**(사용자 결정 4·51): H-7(개정 8 3.2 "≥ 1이면 H-7")로 확정한다.
   - 시나리오 ①: R12 bottom FL Fs4의 VB·LS2·LS3(H-10)과 격자 `r69_bottom|…|4.0|ready|FL|G4|0.0`(H-9). 기록값이 서로 같다.
   - 시나리오 ②: 격자 `r67_top|…|8.0|ready|FR|G4|0.075`.
   - **등급: `미달` 확정**(사용자 결정 51, 결정 50의 1 "판정 보류"를 푼다). H-9 격자와 H-10은 원판 8.1의 `미달`이다. 등급 문턱(ext_moving `breach_reads` 합 = 0, v5 기준 개정 8 3.2)과 원판 8.1의 우선순위는 바꾸지 않는다. 이 귀결은 결과를 본 뒤의 결정으로 판정서에 적는다.
   - **원인(한계로 공개, hydraulics-expert 분석, R16-0 5)**
     - J-P3 위반은 ③ 추정기의 공백이다. rev4 시드(`_seed_extension_after_lock`, `two_pressure.py` 2312~2320행)는 신장 명령일 때만 반례 조건 ④의 값을 넘긴다. 잠김과 신장 사이에 P5의 −2 µm/s 미세 수축이 한 주기라도 끼면 ④ 값(102.7 bar)을 넘기지 못하고 p_ret 30.6 bar에서 시작한다. 실기에서도 생길 수 있는 경로다.
     - 이번 사례는 대체 다리가 0이라 명령에 닿지 않았고, F_min도 넘지 않았다. 최악 과대는 8.27 kN이고 0.2~0.4 s 동안이다.
     - LS 감도에서 결과가 갈린 것은 재잠김 시각(Δt)과 플랜트 산물 P-1(수축 하강을 유량 상한 없는 1차 지연으로 다룸) 때문이다. 그래서 LS1·LS4와 오프셋 0.05 짝의 통과는 **거짓 통과**로 공개한다. 이 통과들을 ③ 상계가 맞다는 근거로 쓰지 않는다.
3. **S-6 67줄**(사용자 결정 2): C-9 결과를 받아 사용자가 정한다. 그 전에는 H-3·H-8 S-6 멈춤이 그대로다. 67줄은 모두 원 규칙(H-7′)으로는 통과다. 대가(행정 −29.45~−31.88 mm, 끝 rut 틈 −29.37~−30.86 mm, 최소 43.7 mm)는 판정서에 적는다.
4. **G-6 g8 3키**(사용자 결정 5·51): H-12(R16-9) 결과로 닫는다. 원인은 R16-15a다.
5. **seedext**(사용자 결정 6): C-11 결과를 기록으로 더한다. H-8 L2 판정(VB 4/835, CP 상계 1.09 % < 3 %)은 바꾸지 않는다. stage3 U-4의 "VB 체계적 악화 의심(하네스)"는 알려진 한계로 이어 적는다.
- 결정 필요: **아니오**(사용자 결정 2~6, 51). G-5 g6·S-6의 최종 처리는 C-9·C-10 뒤에 묻는다.

## R16-15a. 하네스 로드 판독 모형의 한계 공개 (사용자 결정 51·52)

- **[사실]**(hydraulics-expert 분석, R16-0 5): VB/LS 하네스에서 제어기가 받는 로드 판독은 M2 참값이 아니라 잠김 법칙의 값이다. `with_two_pressures`의 p_r은 수축 중에도 2.0 bar로 남는데, M2 참값은 26~27 bar다. 같은 산물이 V0 하네스에도 있다.
- **판정서 한계 절에 그대로 적을 문장**: "VB/LS 하네스에서 제어기의 로드 판독은 M2 참값이 아니라 잠김 법칙 값이다. 그래서 다음이 생긴다.
  - u3 g8 VB 3키의 `WARN_ROD_PRESSURE_FALLBACK`(D3)은 이 판독 산물이 만든 오탐이다. 수축 중 판독 p_r ≈ 2.0 bar, 참값 26~27 bar.
  - 이동 중 헤드 판독도 같은 이유로 왜곡된다.
  - T4h에 남는 `rod_pressure_Pa`로는 ext_moving 판정을 정확히 재생할 수 없다.
  하네스 판정 항목(J-P3 `breach_reads`, F_min, 행정, 자세)은 하네스 플랜트 참값으로 계산하므로 판정 자체는 유효하다. 다만 대체 경로·진단(D2·D3)·T4h 재생의 하네스 결과는 이 판독 모형에 기대며, 실기·Chrono보다 낙관이거나 비관일 수 있다."
- G-6(R16-9 H-12)은 래퍼 T4h로 공식 확인하는 방식을 그대로 둔다(사용자 결정 51). 이 분석은 원인 근거로만 쓴다. H-12 판정서에는 "D3 오탐의 원인은 R16-15a"를 함께 적는다.
- 결정 필요: **아니오**(사용자 결정 51).

## R16-15b. 436.8의 결론과 436.9로 넘기는 개선 (사용자 결정 52)

- **정의**
  1. 436.8은 rev16과 R2 실행 기록의 재판정(R16-1)으로 닫는다.
  2. 결론 문장의 틀은 "현 제어기(`final_C4G2_LAS_K1` / `final_C4G2_P3_LAS_K1`)·현 하네스 기준 `미달`(J-P3, H-9 격자·H-10) + 하네스 로드 판독 모형 한계 공개(R16-15a)"다. 다른 묶음의 상태와 S-6·G-5·G-6의 처리는 재판정과 사용자 결정 뒤에 이 틀에 더한다.
  3. 개선은 436.8과 별건인 **436.9**로 넘긴다. 하네스 로드 판독을 M2로 교체하고, ③ A/B안과 플랜트 E(P-1·P-2)를 다룬다. 설계·구현은 별도 worktree에서 하고, VB 묶음을 다시 돌린다.
  4. 436.9의 결과는 436.8의 결론·등급·판정서를 바꾸지 않는다. 436.8 판정서에는 "개선은 436.9에서 다룬다"는 한 줄만 적는다.
- 결정 필요: **아니오**(사용자 결정 52).

## R16-16. 결정 표

| 항목 | 권고·정의 | 결정 필요 |
|---|---|---|
| R16-0 사후 개정 공개 | 본 자료 목록(Chrono 결과 일부, hydraulics 분석 포함), 결함 목록의 출처(메인 세션 + 도메인 검토), C-2·PS-c 결과 미포함 | 아니오 |
| R16-1 S-13 처리 | 첫 두 경로 출력은 기록, 시뮬레이션 재실행 없이 R4 도구로 재판정, 다시 갈리면 S-13 | 결정됨: 사용자 결정 1(2026-11-15) |
| R16-2 새 묶음·S-15·11.1·11.2 | H-11 실행 10(짝 8), H-12 3, C-9 2, C-10 4, C-11 2. C-9 끔 팔만 `--k1-order-gate` 허용. 11.1 표에 새 묶음 행을 넣고, 11.2 G-S는 면제 + 대체 점검 | 결정됨: 사용자 결정 54의 4 |
| R16-3 ABL 4.2 | `require_soil_response` False, `flat_soil_margin_m` 0만 다름 | 결정됨: 사용자 결정 1 |
| R16-4 V0 블록 부재 | `v5_setting` V0 ∧ 블록 없음 = ③ 끔 | 결정됨: 사용자 결정 1 |
| R16-5 S-5 앵커 | 앵커 = P-1·P-2뿐. 키 원본 대조는 기록(`base.commands_sha256`, dg3 대체 키는 `dg3_v4_on`). 결과 본 뒤 정한 읽기로 공개, 이번 값에서는 결과 불변 | 결정됨: 사용자 결정 1, 54의 2 |
| R16-6 J11 | `n_late_fallback_by_leg`, 멈춤은 VB·LS·item8·overlap만 | 결정됨: 사용자 결정 1 |
| R16-7 격자 J-P3 | 경로 1에 run 단위 J-P3 등급 | 결정됨: 사용자 결정 1 |
| R16-8 G-3 짝 | 비교 대상 = R2 V0 출력(u3 rev2 #11 고쳐 씀), 옵션·env 정의, 키 좁히기·비교 필드, 8쌍, 수 검사, 두 경로 판정 | 결정됨: 사용자 결정 54의 1·4 |
| R16-9 G-6 T4h | 기록 전용 래퍼, r79 Dg-3 꼴, 정체성 다섯, 공식 폴더에 들이기 전 첫 파일 `--check-recorded`, 어긋나면 멈추고 묻고 대체(run_v5 꼴 3, `H-12b`), 대체 다리 기준 잠긴 표본 0이면 기록 불완전 | 결정됨: 사용자 결정 50의 3, 54의 3, 55의 2 |
| R16-10 도구 수정·경로 2 글머리 | 경로 1 (a)~(f), 경로 2 (a)~(h), 경로 2에는 R16-10 3 표의 [정의] 글머리만, "다른 절은 열지 않는다", 파일 접근은 막지 않음(한계 공개) | 결정됨: 사용자 결정 1, 53, 54의 1·4, 55의 1 |
| R16-11 Chrono 확인 행 | 행 이름 8개 글자 그대로, argv 확정, C-9 끔 팔 기대값·S-2 예외, P-18 전제, P-19 | 아니오(cad-expert 확인, 감사 권고 반영) |
| R16-11a 결론 반영 | 기록 묶음, 등급 밖, 멈춤 질문의 근거로만 | 결정됨: 사용자 결정 50의 2 |
| R16-11b 정체성·기록 위치 | R15-6 대체를 8행으로, 시작·끝 정체성, 원판 6절 대체 키, 행 폴더 파일 8종, 기록은 R4 하네스 쪽 두 경로 도구 | 아니오 |
| R16-12 R3·R4 구조 | `z4373-r3v2`(R2 + 5 병합, R3 = `576eb87`, manifest 끝 `fb09350`, `z4373-r3` `99ad4dc`는 쓰지 않음) → S4(부모 R3) → p1harness·p2harness → `z4373-r4`, ff 전 조건(x16 post 8행, `h11_h12_check.py` 또는 H-12b, `log_errors.py`) 뒤 메인 ff-only로 R3, Chrono 판정을 R3로 끝낸 뒤 ff-only로 R4, R4 뒤 Chrono 판정 없음, 04_scripts diff 9개 안 | 아니오(감사 반영) |
| R16-13 봉인 목록 | 하네스 도구 두 경로에 rev13~rev16 | 아니오 |
| R16-14 실행 위치·배치 | 메인 checkout R2 clean, `_go.flag` ∧ PS-c `.done` 관문, `<OUT>` 고정, 칸 X1·X2·Y1·Y2 마스크와 행 순서, 행마다 시작·끝 정체성, `harness_env_guard`, 규칙 sha는 `rows.json` `rules_label`(봉인 뒤 `regen.ps1`) | 결정됨: 사용자 결정 50의 4 |
| R16-15 처리 | G-5 5키(한계 3, 확인 2), J-P3 H-7 → `미달` 확정, 원인·LS1·LS4 거짓 통과는 한계 공개, S-6·g6는 C-9·C-10 뒤 질문, G-6은 H-12, seedext는 기록 | 결정됨: 사용자 결정 2~6, 51 |
| R16-15a 판독 모형 한계 | 로드 판독 = 잠김 법칙 값(M2 참값 아님), D3 오탐, 이동 중 헤드 판독 왜곡, T4h `rod_pressure_Pa`로 ext_moving 재생 불가, 판정은 참값 기준이라 유효 | 결정됨: 사용자 결정 51 |
| R16-15b 결론·436.9 | 436.8 = rev16 + R2 재판정으로 마감, "미달(J-P3) + 판독 모형 한계 공개", 개선은 436.9(별건, 436.8 불변) | 결정됨: 사용자 결정 52 |

### 결과 본 뒤 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-15 | 1 | 사용자 결정 2026-11-15: S-13은 rev16 + 두 경로 하네스 도구 수정 + 재판정, 시뮬레이션 재실행 없음. 규칙 공백 두 곳, G-3 짝, 경로 2 S-5 앵커 읽기, 9.2 공개 | R16-1~R16-8, R16-10, R16-12 |
| 2026-11-15 | 2 | 사용자 결정 2026-11-15: S-6 G1 균일 67줄은 Chrono G1 짝 1개(P3b G1 관문 켬/끔)로 확인 | R16-11 1, R16-15 3 |
| 2026-11-15 | 3 | 사용자 결정 2026-11-15: G-5 정답은 경로 1의 5키, g8·h9는 한계 기록, g6 rigid+S1@FL/FR는 Chrono VB/V0 짝으로 확인 | R16-11 2, R16-15 1 |
| 2026-11-15 | 4 | 사용자 결정 2026-11-15: J-P3 2개 시나리오는 H-7 확정, ③ 대체 경로 한계로 공개, 원인 분석은 hydraulics-expert(별건) | R16-15 2 |
| 2026-11-15 | 5 | 사용자 결정 2026-11-15: G-6 g8 3키는 T4h 재생으로 확인(rev1 #5) | R16-9, R16-15 4 |
| 2026-11-15 | 6 | 사용자 결정 2026-11-15: H-8 seedext `L2\|g6\|56\|ref\|J2\|top\|Fs0`는 지금 Chrono VB/V0 짝으로 확인 | R16-11 3, R16-15 5 |
| 2026-11-15 | 7 | 사용자 결정 2026-11-15: 추가 Chrono 행은 rev16에 행 정의·사전 예측·판정 기준과 함께 등록한 뒤 실행하고, 436.8 결론에 넣는 방식은 rev16이 정한다 | R16-11, R16-11a |
| 2026-11-15 | 50 | 사용자 결정 50(2026-11-15): ① J-P3 H-7 확정의 등급 귀결은 판정 보류(51이 대체). ② R16-11a 권고안 채택. ③ G-6 T4h는 (가) 기록 전용 래퍼. ④ 새 실행은 지금 도는 실행이 끝난 뒤 메인 checkout(R2, clean)에서, worktree 절차 없음, DLL은 메인에 있음, R3·R4 병합은 새 실행 뒤, 출력은 git 무시 경로, 정체성은 `resume_k1_identity.py`(하네스)와 gs_identity 꼴(Chrono) | R16-9, R16-11a, R16-12, R16-14 |
| 2026-11-15 | 51 | 사용자 결정 51(2026-11-15): J-P3는 `미달` 확정(판정 보류 해제, H-9 격자·H-10 원판 8.1 미달), G-6은 래퍼 T4h 공식 확인 유지(분석은 원인 근거), 판독 모형 한계는 지금 반영 | R16-15 2, R16-15a |
| 2026-11-15 | 52 | 사용자 결정 52(2026-11-15): 436.8은 rev16과 R2 재판정으로 마감, 결론은 현 제어기·현 하네스 기준 "미달(J-P3) + 판독 모형 한계 공개". 개선(하네스 로드 판독 M2 교체, ③ A/B안, 플랜트 E(P-1·P-2))은 436.9 별건, worktree에서 설계·구현, VB 묶음 재실행 | R16-15b |
| 2026-11-15 | 53 | 사용자 결정 53(2026-11-15): 경로 2에 R16-11의 "기록 항목" 문장과 R16-11b 1의 정체성 문장을 함께 준다(결함 목록이 아니라 새 기록 묶음의 정의). 경로 1의 코드·출력은 주지 않는다 | R16-10 3 |
| 2026-11-15 | 56 | 사용자 결정 56(2026-11-15): R3 대상 manifest 끝을 `fb09350`(`57828fc` + 시험 파일 `test_v5_resume_4368_chrono_rows.py`만, +23/−2)으로 한다. R3 = `576eb87`(`z4373-r3v2`). 처음 R3 후보 `z4373-r3` `99ad4dc`는 시험 1건 실패로 쓰지 않고 기록으로 남긴다 | R16-12 1·2, 봉인 절 1·5 |
| 2026-11-15 | 55 | 사용자 결정 55(2026-11-15): ① 경로 2 작성자의 rev16 파일 접근은 기술적으로 막지 않고, "다른 절은 열지 않는다" 지시와 읽은 것 목록 확인으로 막으며 이를 한계로 공개한다. ② H-12의 "잠긴 표본 0이면 기록 불완전"은 키마다 실제 대체 다리의 `fallback_start_s` 뒤 잠긴 표본으로 센다(네 다리 합계 아님, 출처 T4h `locked`·`fallback_start_s`) | R16-9 6, R16-10 3 |
| 2026-11-15 | 54 | 사용자 결정 54(2026-11-15, 봉인 전 감사의 확인 필요 4건): ① G-3 = "V0 설정이 옵션 없음과 같다" 검사, u3 rev2 #11의 비교 대상을 R2 V0 출력으로 고쳐 씀. 경로 2에는 [정의] 글머리만 넘기고 "다른 절은 열지 않는다"를 지시. ② R16-5 S-5 좁힘은 결과 본 뒤 정한 읽기로 공개(이번 값에서는 결과 불변). ③ H-12가 어긋나면 멈추고 메시지 박스로 묻고, 대체 argv·건수·정체성은 미리 적음. ④ H-11은 두 경로로 판정, 새 묶음은 11.2 G-S 면제 + 대체 점검 | R16-2, R16-5, R16-8, R16-9, R16-10 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. R16-12 순서 1의 R3 통합 브랜치 `z4373-r3v2`는 만들어졌다. 그 마지막 병합 커밋 R3 `576eb87`이 봉인 기준 커밋(SEAL_COMMIT)이다.
2. 파일 이름: `v5_resume_4368_rules_rev16_seal_candidate_draft.md`를 같은 폴더에 `v5_resume_4368_rules_rev16.md`로 복사한다. 초안 파일은 지우지 않는다.
3. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev16 (하네스 두 경로 판정 S-13 뒤: 규칙 공백 두 곳, 두 경로 하네스 도구 수정 R4, 경로 2 앵커 읽기, J11·격자 J-P3 읽기, G-3 짝·G-6 T4h·Chrono 확인 행 등록, J-P3 미달·판독 모형 한계, 결과 본 뒤 개정, 봉인)`
4. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev16.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev16_seal_candidate_draft.md`와 1·3·5·9행만 다르다.`
5. 5행("시점")에서 `SEAL_TIME`(예: 2026-11-15 10:00:00 +09:00)과 `SEAL_COMMIT`(R3 `576eb87`)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
6. 9행("봉인 준비판이다")을 다음으로 바꾼다:
   `- **봉인본이다.** 봉인 전 확인 필요는 없었고, 사용자 결정(2026-11-15) 1~7과 결정 50~56, 봉인 전 감사 두 차례(대상 초안 `e69a597a`, `de2b2b89`)의 차단·권고는 R16-0~R16-16에 반영했다.`
7. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev16.sha256`에 `<sha256>  v5_resume_4368_rules_rev16.md  sealed <SEAL_TIME 값> (436.8 rev16: after the harness two-path judgement at R2 b9f5707 (S-13 on H-3, H-4, H-6..H-9) and part of the Chrono results, on top of rev15; thresholds, grades and stop meanings unchanged, seen-data list disclosed incl. the hydraulics-expert analysis; defect list compiled by the main session and the domain review from both outputs (disclosed); first harness two-path outputs kept as record, harness re-judged at R4 without new simulation; ABL 4.2 expectation require_soil_response False and flat_soil_margin_m 0 by design; V0 r79 results without a hydraulic_options block = extend start off; S-5 anchors = P-1 / P-2 only, key-source comparison as record on base.commands_sha256 (dg3 substituted keys against dg3_v4_on), a reading decided after the results, unchanged outcome here; harness J11 = n_late_fallback_by_leg, stop on VB / LS / item8 / overlap only; path 1 grid J-P3 per run; new bundles H-11 G-3 (V0 setting equals the option-free path, compares with the R2 V0 output, 10 runs, 8 pairs, count check, both paths), H-12 g8 G-6 T4h 3 (record-only wrapper, r79 Dg-3 T4h, five identity conditions, first file --check-recorded, stop and ask on mismatch, pre-registered run_v5 form fallback H-12b 3, zero locked samples = record incomplete), C-9 G1 gate on / off V0 2 (off arm expectations, S-2 mixed-version exception, P-18 preconditions), C-10 rigid+S1 FL / FR VB / V0 4 (outside the Bekker validity range), C-11 J2 top Fs0 L2 VB / V0 2, eight row names literal, record bundles outside the grade, predictions P-16..P-19, G-S exempt with substitute checks, 11.1 table rows added; R15-6 identity extended to the 8 Chrono rows with start / end identity files, SCM identity substitute keys and the row-folder file list, record items read by the R4 harness-side tools of both paths; R3 = 576eb87 built on the integration branch z4373-r3v2 with the manifest tip fb09350 (57828fc plus a test-file-only fix, user decision 56, rewrites the 57828fc of rev15 R15-2 and R15-5, decided after seeing results), the unused candidate z4373-r3 99ad4dc kept and disclosed, seal commit S4 on 576eb87, harness tool branches from S4, R4 on z4373-r4, main fast-forwarded to R3 after the new runs, C-1..C-8, C-5 path 2 and R3 G-S readings finished with R3 tools before R4, no Chrono judgement after R4, 04_scripts diff R2..R4 within nine files, R4 blob table; new runs in the main checkout at R2 after PS-c, output C:\workspace\outrigger_control\07_results\S9\R4368X_b9f5707_20261115_013947\, four 4-thread cells X1 0x0F00 / X2 0xF000 / Y1 0x000F / Y2 0x00F0; path 2 given only the [definition] bullets of the R16-10 3 table; harness tool seal lists rev13..rev16 on both paths; G-5 set = path 1 five keys, J-P3 fail confirmed for the H-9 grid and H-10 with the cause and LS1 / LS4 false passes disclosed; harness rod reading model limit disclosed; 436.8 closed by rev16 and the R2 re-judgement, improvements moved to 436.9; ff to R3 only after all x16 post checks, h11_h12_check.py (or H-12b) and log_errors.py pass; runners wait for _go.flag and the PS-c .done; harness_env_guard per harness run; identity rules label from rows.json regenerated after the seal; H-12 zero-locked-sample check per actual fallback leg after fallback_start_s; path 2 file access not technically blocked, instruction and read list disclosed; user decisions 2026-11-15 1..7, 50..56)` 한 줄로 쓴다.
8. `.gitattributes`에 다음 3줄을 더한다(지우는 줄 없음, R16-12 (나)). **`git add`보다 먼저** 한다. 속성이 없는 채로 추가하면 작업 복사본 줄 끝이 바뀔 수 있다.
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev16.md -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev16.sha256 -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev16_seal_candidate_draft.md -text`
9. 확인
   - `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`를 돌린다.
   - `placeholder_scan`은 중괄호 없는 `SEAL_TIME`·`SEAL_COMMIT`을 잡지 못한다. 그래서 봉인본 5행을 Grep으로 따로 본다: `SEAL_TIME`과 `SEAL_COMMIT`이 5행에 없어야 한다. 이 절의 안내 문구에는 이 이름들이 남는다(rev12~rev15와 같은 선례).
10. `git add`(세 파일과 `.gitattributes`)와 봉인 파일 커밋 S4를 R3 위에 만든다(R16-12 순서 2). 메인 checkout의 HEAD는 바꾸지 않는다. 그 뒤 `regen.ps1 -RulesLabel "rev16 sealed <sha>"`로 준비물의 규칙 라벨을 맞춘다(R16-14 3). 봉인 뒤 이 문서를 고치지 않는다. 고칠 것이 생기면 `v5_resume_4368_rules_rev17.md`로 새로 봉인한다.
