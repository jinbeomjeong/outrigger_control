# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev17 (H-12 첫 파일 관문의 하한 판독 허용 오차, 관문 재실행 절차, 봉인 파일 커밋 S5 위치, 결과 본 뒤 개정, 봉인 후보 초안)

- **상태: 봉인 후보 초안(봉인 전).** 봉인 전에는 실행·판정에 쓰지 않는다. 봉인 때 바꿀 머리 줄은 끝 절에 원문으로 적었다.
- 원판~rev15는 고치지 않는다. 이 판은 rev16(sha256 `b38991943a565a020488d1046dd6e0b5c71276cf925715fa5ba844d8819d0683`, 봉인 2026-11-15 09:58:22 +09:00, 봉인 기준 커밋 R3 `576eb87`, 봉인 파일 커밋 S4 `98ea664`, 브랜치 `z4373-s4`) 위에 쌓인다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다. 용어(봉인 기준 커밋, 봉인 파일 커밋)는 rev16 4행과 같다.
- **시점: rev16 새 실행 중(10:03:44 `_go.flag` 뒤), H-11 10실행 종료, H-12 `gate rest` 멈춤 뒤, Chrono C-9~C-11 8행 실행 중(봉인 SEAL_TIME, 봉인 기준 커밋 SEAL_COMMIT).** 이 판은 결과를 본 뒤의 개정이다. 본 자료는 R17-0에 모두 적었다.
- 작성: control-expert, 2026-11-15. 기준: R2 `b9f5707`(실행), R3 `576eb87`, S4 `98ea664`.
  - 계기: rev16 R16-9 4 (다)의 첫 파일 관문 조건 "`recorded_lower_max_abs_N` = 0"이 부동소수 반올림 크기의 값(9.094947017729282e-13 N)으로 거짓이 되어 `gate rest`가 멈췄다(R16-9 5의 멈춤).
  - 사용자 결정 57(2026-11-15)을 R17-1~R17-3에 반영했다.
- **봉인 준비판이다.** 봉인 전에 답이 필요한 항목은 없다(확인 필요 0). 이 줄은 봉인 때 바뀐다.
- **바꾸지 않는 것**: 숫자 문턱(판정 문턱 0.6 kN, F_min 9,414.589 N 등), 등급과 우선순위(원판 8.1), 멈춤 조건의 뜻(원판 8.2), 묶음 범위와 행 목록, 사전 예측, 두 경로 요건, 실행 커밋 R2, rev16의 다른 모든 조항. 이 판이 바꾸는 것은 R16-9 4 (다)의 비교 허용 오차 하나와, 그에 따른 관문 재실행 절차, 봉인 파일 커밋의 위치뿐이다.

## R17-0. 결과 본 뒤 개정의 공개 (본 자료 목록)

- 이 작성자가 본 것(2026-11-15, 메인 세션 전달과 읽기 전용 확인)
  1. 메인 세션 전달: H-11 10실행 모두 exit 0(env_guard·identity 포함). H-12 래퍼 `u3_g8_VB_t4h.json` exit 0(53 s), staging T4h 3개, `gate first`로 첫 키 `slope_edge_top_4.0_FR_raised_20.0_proj.npz`(sha256 `c3e577dc…`)를 `t4h\`로 옮김, `t4h_replay --check-recorded` exit 0(`runs` 1, `J-P3` pass, settings 같음, RuntimeError 없음), `gate rest` exit 1(`recorded_lower_max_abs_N` = 9.094947017729282e-13 N). 나머지 두 파일(`edgeMr FL`, `rpB FR`)은 staging에 남음. Chrono 8행은 pre 모두 ok, 실행 중. 같은 첫 파일 확인 출력 `<OUT>\H-12\t4h_first_check.json`의 필드(그대로): `runs_over` = 1, 행 `over_0p6kN` = 1, `over_0p6kN_by_leg` = {FR: 1}, `max_excess_N` = 1110.48 N, `provisional_pass` = False, `unlocked_tail_over_0p6kN_by_leg` = {RL: 1}, `max_excess_vs_window_min_N` = 7702.5 N, `judged_samples_by_leg` = FL 157, FR 320, RL 168, RR 154. **공개: 메인 세션과 이 판의 작성자는 이 H-7 관련 값을 본 상태에서 이 판을 쓰고 봉인한다.** 이 판이 바꾸는 것은 도구 일관성 관문(재생 하한 = 기록 하한)의 허용 오차뿐이고, H-7 판정 문턱(0.6 kN)과는 무관하다.
  2. 이 작성자가 연 것(읽기만): `<OUT>\_tools\harness\h12_t4h_gate.py`(sha256 `821fb9df298703f6c3d66bbda521125fd8b1b0dced6b019cda48b1f35e5e44f2`) 1~175행, `steps_h12.json`, `run_h12.ps1`의 대기·`SkipDone` 부분(22·118~174행), `h11_h12_check.py`의 머리말과 해시 비교 부분, rev16 봉인본.
  3. 확인한 사실: `h12_t4h_gate.py` 82행이 `row.get("recorded_lower_max_abs_N") != 0.0`으로 정확한 0을 요구한다. `h11_h12_check.py`는 이 값을 쓰지 않는다. rev16 봉인본에서 이 조건이 나오는 곳은 R16-9 4 (다) 한 곳(봉인본 173행)이다.
- 판정 결과(J-P3, H-7 등)의 값은 이 판을 정하는 데 쓰지 않았다. 판정서에는 이 목록과 "결과 본 뒤 정한 허용 오차"를 그대로 적는다.

## R17-1. 하한 판독 차이의 허용 오차 (사용자 결정 57)

- **[정의]** rev16 R16-9 4 (다)의 "`recorded_lower_max_abs_N` = 0"을 "**`recorded_lower_max_abs_N` ≤ 1e-6 N**"으로 고쳐 쓴다. 이 범위 안이면 재생 하한과 기록 하한이 같다(부동소수 반올림)고 본다. 다른 조건(`runs` 1, 첫 파일 이름, `settings_equal` 참, RuntimeError 없음)은 그대로다. rev16에서 같은 조건이 나오는 곳은 R16-9 4 (다) 하나다. R16-9 5(대체 경로)와 R16-11b에는 이 조건이 없다.
- **[사실]** 관측값 9.094947017729282e-13 N은 float64 계산의 반올림 크기다. 하한 판독은 수 kN~수십 kN 크기의 압력·면적 곱의 합이고, float64 상대 정밀도 약 2.2e-16에 그 크기를 곱하면 1e-12 N 안팎이 된다.
- **[사실]** 1e-6 N은 판정에 영향이 없다: H-7 판정 문턱 0.6 kN(600 N)보다 약 6×10⁸배(9자리 가까이) 작고, F_min 9,414.589 N의 약 1×10⁻¹⁰배다. 관측값은 1e-6 N보다 약 6자리 작다.
- **[참고]** 원판 7.6의 비교 허용("|v − c| ≤ e"는 e + 1e-9(그 단위)까지 참)으로 읽어도 관측값은 같음이다. 이 판은 사용자 결정 57대로 이 비교에만 1e-6 N을 명시한다.
- 결정 필요: **아니오**(사용자 결정 57).

## R17-2. 관문 재실행 절차 (사용자 결정 57)

- **[정의]**
  1. 재실행은 하지 않는다. 같은 3파일(staging 2개, `t4h\` 1개)로 관문만 다시 돌린다. 첫 파일 확인은 이미 끝난 출력 `<OUT>\H-12\t4h_first_check.json`을 쓴다(`check_first`를 다시 돌리지 않는다). `gate first`도 다시 돌리지 않는다.
  2. **관문 도구(권고안 (가))**: `h12_t4h_gate.py`의 새 판을 만든다.
     - 바꾸는 것은 `first_check_problems`의 비교 한 줄(`!= 0.0` → 값이 없거나 1e-6 N을 넘으면 문제)과 머리말·docstring의 규칙 인용(rev17 R17-1)뿐이다. 허용 오차는 상수 `LOWER_TOL_N = 1e-6`으로 두고, 출력 로그 항목에 그 값과 실제 값을 함께 남긴다. 명령줄 인자는 바꾸지 않는다. 그래서 `steps_h12.json`의 `h12_t4h_gate_rest` 명령은 그대로 쓸 수 있다.
     - 옛 판은 같은 폴더에 `h12_t4h_gate.r16.py`로 남긴다(sha256 `821fb9df298703f6c3d66bbda521125fd8b1b0dced6b019cda48b1f35e5e44f2`, 기록). 새 판 `h12_t4h_gate.py`의 sha256은 `5c6b78dade3b2918600f771062536272533257e8c893534473eefd2ae06e7312`이다. 실행 전 감사가 이 값을 고정하고 판정서에 적는다. 새 판과 옛 판의 diff를 판정서에 싣는다.
  3. **다시 돌리는 방법**: 러너를 그대로 다시 띄운다(`run_h12.ps1`에는 param 블록이 없고 `$SkipDone = $true`가 기본이다. 예: `launch_harness.ps1 -Which H12`). 이때 `.done` 표지가 있는 단계(env_guard, identity, capture, `gate first`, `check_first`)는 건너뛰고, 남은 `h12_t4h_gate_rest` → 그 뒤 단계(`h11_h12_check.py` 포함)만 돈다.
     - 러너의 대기 조건(`_go.flag`, H-11 두 `identity_end.done`)은 이미 참이라 바로 시작한다.
     - 다시 띄운 러너에서는 env_guard 단계가 건너뛰어진다. 남은 단계는 파일 이동과 점검이라 계산 env와 무관하다. 그래서 금지 env 증명은 첫 러너의 env_guard 기록으로 대신하고, 그 사실을 판정서에 적는다.
  4. 성공 조건: `gate rest` exit 0, `t4h\` 3파일·staging 0파일, 그 뒤 `h11_h12_check.py`(H-12 4조건)가 종료 0. 그다음 R16-9 6의 판정은 R4 도구가 한다(rev16 그대로).
  5. 새 판 `gate rest`도 거짓이면(1e-6 N 초과 또는 다른 조건) R16-9 5대로 멈추고 메시지 박스로 묻는다.
- **[참고] 고르지 않은 안 (나)**: 메인 세션이 rev17 규칙에 따라 두 파일을 손으로 옮기고 기록하는 방식. 도구 수정이 없어 sha 재고정이 필요 없지만, 이동이 도구 로그(`t4h_gate.json`)와 러너 `.done` 표지에 남지 않아 `h11_h12_check.py` 앞뒤의 기록 사슬이 끊긴다. 그래서 (가)를 권고한다.
- 결정 필요: **아니오**(사용자 결정 57. (가)는 권고안).

## R17-2a. 첫 파일의 H-7 관련 사실과 적용 다리 범위의 공백

- **[사실]** 첫 키(`slope|edge|top|4.0|FR|raised|20.0|proj`)의 실제 대체 다리는 RL(D3)이다. `t4h_replay`는 네 다리 모두를 강제로 대체해 재생한다. 그 재생에서 강제 대체된 FR 다리에 잠긴 표본 초과(> 0.6 kN)가 1건 나왔다(`over_0p6kN_by_leg` = {FR: 1}, `max_excess_N` = 1110.48 N). 실제 대체 다리 RL에는 잠기지 않은 꼬리 초과 1건이 있다(`unlocked_tail_over_0p6kN_by_leg` = {RL: 1}, 기록 항목).
- **[사실]** P-17(세 키 모두 잠긴 표본 초과 0)과의 대조는 판정서에서 한다. 이 판은 그 대조를 하지 않는다.
- **[사실]** rev16 R16-9 6은 H-7(잠긴 표본 하한 − 진값 > 0.6 kN)을 네 다리 모두(강제 대체 재생)에 적용할지, 실제 대체 다리에만 적용할지 정하지 않았다. 이 공백은 위 관측값 때문에 드러났다.
- **[정의]** 이 판은 그 범위를 정하지 않는다(지금 정하면 결과를 본 뒤의 선택이 된다). R4 판정에서 이 공백에 걸리는 값이 있으면 규칙 그대로 멈추고 사용자에게 묻는다.
- 결정 필요: **아니오**(R4 판정 때 묻는다).

## R17-3. 봉인 파일 커밋 S5의 위치와 R16-12 맞춤

- **[정의]**
  1. rev17의 봉인 파일 커밋 S5는 S4 `98ea664` 위에 만든다. 봉인 기준 커밋(SEAL_COMMIT) = S4 `98ea664`다. S5가 바꾸는 것은 rev17의 세 파일과 `.gitattributes`의 `-text` 3줄뿐이다.
  2. rev16 R16-12 순서 2·3·4의 "S4"를 "S5(S4 위)"로 읽는다: 하네스 도구 브랜치 `z4373-p1harness`·`z4373-p2harness`는 S5에서 가르고, R4 통합 브랜치 `z4373-r4`도 S5에서 만든다. 그래서 R4 아래에 rev16·rev17이 모두 있다.
  3. 하네스 도구 봉인 목록(rev16 R16-13)에 rev17도 넣는다. 두 경로를 같게 한다. Chrono 판정 도구의 봉인 목록은 rev15까지 그대로이고(rev16 R16-13), rev16·rev17 확인은 `tools/verif/seal_check.py`로 한다.
  4. R4 조건(rev16 R16-12)의 허용 목록 (가)·(나)에 rev17의 세 파일(`v5_resume_4368_rules_rev17.md`, `…_rev17.sha256`, `…_rev17_seal_candidate_draft.md`)과 그 `-text` 3줄을 더한다. 그 밖의 R4 조건(`03_src`·`02_params` diff 0, `04_scripts` 9개 안, Chrono 판정 도구 diff 0)은 그대로다.
  5. 이 판은 메인 checkout의 HEAD를 바꾸지 않는다(R2 그대로, rev16 R16-14 2). H-12 관문 도구는 git 무시 경로(`<OUT>\_tools\harness\`)에 있어 커밋이 필요 없다.
- **[사실]** 하네스 도구 브랜치 `z4373-p1harness`·`z4373-p2harness`는 아직 만들지 않았다. 지금 있는 z4373 브랜치는 `z4373-r3`, `z4373-r3v2`, `z4373-s4` 셋이다(메인 세션 `git branch --list 'z4373-*'`, 2026-11-15). 그래서 두 브랜치는 S5에서 처음 가른다.
- 결정 필요: **아니오**(메인 세션 확인으로 닫힘).

## R17-4. 결정 표

| 항목 | 정의·권고 | 결정 필요 |
|---|---|---|
| R17-0 사후 개정 공개 | 본 자료 목록, 판정 값은 쓰지 않음 | 아니오 |
| R17-1 허용 오차 | R16-9 4 (다) `recorded_lower_max_abs_N` = 0 → ≤ 1e-6 N(부동소수 반올림), 0.6 kN·F_min 대비 영향 없음 | 결정됨: 사용자 결정 57 |
| R17-2 관문 재실행 | 재실행 없음, `gate rest`만, (가) 새 도구 판(상수 1e-6, 인자 불변, sha `5c6b78da…`, 옛 판 `h12_t4h_gate.r16.py` `821fb9df…`), 러너를 그대로 다시 띄움(SkipDone 기본 켬), 그 뒤 `h11_h12_check.py` |
| R17-2a H-7 다리 범위 | 첫 파일의 강제 대체 FR 초과 1건·실제 대체 RL 기록, P-17 대조는 판정서, 범위 공백은 R4 판정 때 멈추고 물음 | 아니오(판정 때 물음) | 결정됨: 사용자 결정 57((가) 권고) |
| R17-3 S5 위치 | S5는 S4 `98ea664` 위(SEAL_COMMIT = `98ea664`), 하네스 도구 브랜치(아직 없음)와 `z4373-r4`는 S5에서 가름, 봉인 목록에 rev17, R4 허용 목록에 rev17 세 파일 | 아니오(메인 세션 확인: 두 브랜치 아직 없음) |

### 결과 본 뒤 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-15 | 57 | 사용자 결정 57(2026-11-15): rev17 짧은 개정으로 하한 판독 차이(`recorded_lower_max_abs_N`) ≤ 1e-6 N을 같음(부동소수 반올림)으로 정의한다. 재실행 없이 같은 3파일로 `gate rest`만 다시 돌리고, 첫 파일 확인은 끝난 출력을 쓴 뒤 나머지 2파일을 들인다. 결과 본 뒤 개정으로 공개한다 | R17-1, R17-2 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 봉인 전 확인 필요는 없다(R17-3의 브랜치 상태는 메인 세션 확인으로 적었다).
2. 파일 이름: `v5_resume_4368_rules_rev17_seal_candidate_draft.md`를 같은 폴더에 `v5_resume_4368_rules_rev17.md`로 복사한다. 초안 파일은 지우지 않는다.
3. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev17 (H-12 첫 파일 관문의 하한 판독 허용 오차, 관문 재실행 절차, 봉인 파일 커밋 S5 위치, 결과 본 뒤 개정, 봉인)`
4. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev17.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev17_seal_candidate_draft.md`와 1·3·5·9행만 다르다.`
5. 5행("시점")에서 `SEAL_TIME`(예: 2026-11-15 11:00:00 +09:00)과 `SEAL_COMMIT`(S4 `98ea664`)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
6. 9행("봉인 준비판이다")을 다음으로 바꾼다:
   `- **봉인본이다.** 봉인 전 확인 필요는 없었고(하네스 도구 브랜치는 아직 없어 S5에서 가른다, R17-3), 사용자 결정 57(2026-11-15)은 R17-1~R17-3에 반영했다.`
7. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev17.sha256`에 `<sha256>  v5_resume_4368_rules_rev17.md  sealed <SEAL_TIME 값> (436.8 rev17: after the H-12 gate rest stop on top of rev16; R16-9 4 (c) recorded_lower_max_abs_N = 0 rewritten as <= 1e-6 N (float64 rounding; observed 9.09e-13 N; about 6e8 times below the 0.6 kN threshold, 1e-10 of F_min), decided after seeing the value (user decision 57); no rerun, same three files, existing first-file check output, gate rest only with a new h12_t4h_gate.py version (constant LOWER_TOL_N 1e-6, arguments unchanged, old version kept as h12_t4h_gate.r16.py 821fb9df, new version 5c6b78da fixed by the pre-run audit), runner relaunched as is (SkipDone on by default) then h11_h12_check.py; the H-7 values of the first-file check (forced FR over 1, 1110.48 N; actual fallback leg RL) were seen before the seal and disclosed, the H-7 leg-scope gap of R16-9 6 is not decided here and stops for a question at the R4 judgement; Chrono judge seal lists stay at rev15 with seal_check.py for rev16 / rev17; seal commit S5 on S4 98ea664, harness tool branches (not yet created) and z4373-r4 cut from S5, rev17 in the harness tool seal lists and the R4 allow list; thresholds, grades and stop meanings unchanged)` 한 줄로 쓴다.
8. `.gitattributes`에 다음 3줄을 더한다(**`git add`보다 먼저**, 지우는 줄 없음):
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev17.md -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev17.sha256 -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev17_seal_candidate_draft.md -text`
9. 확인: `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`를 돌리고, 봉인본 5행에 `SEAL_TIME`·`SEAL_COMMIT`이 남지 않았는지 Grep으로 따로 본다. 이 절의 안내 문구에는 이 이름들이 남는다.
10. `git add`(세 파일과 `.gitattributes`)와 봉인 파일 커밋 S5를 S4 `98ea664` 위에 만든다. 메인 checkout의 HEAD는 바꾸지 않는다. 봉인 뒤 이 문서를 고치지 않는다.
