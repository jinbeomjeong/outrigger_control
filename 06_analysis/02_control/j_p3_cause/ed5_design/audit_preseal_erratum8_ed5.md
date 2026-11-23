저장 필요: 06_analysis/02_control/j_p3_cause/ed5_design/audit_preseal_erratum8_ed5.md(원문 그대로)

## 감사 요약
- 의존성 점검: 빠진 것 없음(numpy 2.5.3, pyyaml 6.0.3, git).
- 본 결과(값을 읽은 것만 적음):
  - VBK0 b1·b2 결과 줄: READY 시각, `rod_fault` 분류 필드, `t4h_file` 이름. VBK0 b1·b2 T4h는 sha만 쟀다.
  - `12b_vbk0_base_a1/judge/decision.json`: `aa`·`inputs` 블록.
  - `ed5_design/aa_stop_606f8713/aa_fault_floor.json`: 서명과 FAULT 바닥의 일치 여부만 출력했다.
  - `cdry_a1/judge/dry_c.json`: 키 이름과 줄 번호만 출력했고 값은 출력하지 않았다.
  - c 건식 VBK0 T4h: 배열 **이름**만 봤다(`key_presence`).
  - 블라인드 파일은 열지 않았다: `cdry_a1/VBK_c92*`·`VBK_c93*`, `cdry_a1/logs/`, 12b VBK. 12b VBK는 아직 없다.
- 대상·시점: 실행 전, 곧 정오 8 봉인 전 감사다. 기준 문서와 sha 앞 8자리:
  - 원판 `jp3_remedy_spec_v5.md` fe6f5844
  - 정오 1 4721352e, 2 639c54e9, 3 7bab9217, 4 4bc4ecdd, 5 8487bd55, 6 9a92bd34, 7 38fdc574. 모두 `.sha256`과 같다.
  - 정오 8 `jp3_remedy_spec_v5_erratum8.md` ad2643cc. `.sha256`은 아직 없고, 파일은 추적되지 않는다.
  - 판정 도구: worktree `ed5-run5` `jp3_12b_judge.py`. git blob 77eb401f이고 `606f8713`의 blob과 같다(작업 트리가 깨끗하다).
- 판정: 차단 1 / 실행 전 수정 7 / 기록 9.
  - 지금 상태로는 봉인하지 않는다. 경로 2 처리 문장(B-1)을 넣은 뒤 봉인한다.
  - W-1, W-2, W-5, W-7은 문장 수정이라 봉인 전에 고치기를 권한다.
  - W-3(c)~(f), W-4는 구현과 재개 직전 감사에서 닫아도 된다. 다만 정오 8 8-9에 근거 문장이 있어야 한다.

## 요청 항목별 답(요약)
1. (T) 시간 순서와 블라인드
   - 정오 8은 12b VBK 출력보다 먼저다. 12b VBK 출력은 없고, 러너 프로세스도 없다.
   - `dry-c`의 `failures`는 코드상 언제나 빈 목록이다. 건식 VBK의 (1)~(3) 결과를 담을 수 없다(아래 R-8).
   - 정오 8 148행은 함수 범위와 키 목록은 맞다. 그러나 stats-design-expert가 읽은 26~42행의 내용을 실제보다 좁게 적었다(W-2).
2. (R) 부등호, 반올림 경계, 키 표는 대체로 모호하지 않다(대조표). 다만 8-10 정정 목록이 빠짐없지 않다(W-1).
3. (E) `blocks_used`가 비거나, $N_{opp}$ = 0이거나, VBK0 미도달 짝만 있어도 통과로 끝나지 않는다. 남은 위험은 둘이다: 기록 항목의 예외가 종료 3으로 판정을 지우는 것(W-4), 그리고 결정 키가 두 개로 나뉜 것(W-5).
4. (I) 두 커밋 운용 절차에 공백이 6곳 있다(W-3 (a)~(f)).
5. (S) 인용한 sha는 모두 실제 파일과 같다. `-text` 보호가 걸리고, ignore에 걸린 파일은 없다. 다만 `stats_e8_review/`가 커밋 목록에서 빠졌고, 그 `SHA256SUMS`가 CRLF다(W-6).

## 발견 사항 (심각도순)

[차단][R·T] B-1. 경로 2 발췌(넘김 6)에 정오 8과 같은 뜻의 정오가 없다
- 근거
  - 경로 2 발췌는 12b 판정 문장을 담는다.
    - `jp3_rev6_p2_handoff_ed5.md:3`: "옮긴 것은 4절(규칙)과 6.3절(T-JR-12b 관문)의 정의 문장뿐이다. 6.3절은 … 판정 문장, A/A를 다룬다."
    - 같은 파일 `:135` "판정은 0 건수다.", `:137` "(2) 첫 READY +30 s 초과 0", `:138` "(3) READY 상실 0"
    - 같은 파일 `:146~150` "2.8 A/A 바닥 멈춤 … 3개 이상이면 멈추고 다시 묻는다", `:77`
  - 앞선 정오는 경로 2를 따로 다뤘다.
    - 정오 1 `:4`: 같은 뜻의 정오 `jp3_rev6_p2_handoff_ed5_e1.md`를 둔다.
    - 정오 2 `:18`: "경로 2 발췌는 바뀌지 않는다. 이 정오의 항목은 모두 경로 2 범위(규칙, T-JR-12b 판정 문장) 밖에 있는 …"
  - 원판 `:387` X-9와 `:534`는 경로 2 발췌를 봉인과 같은 커밋으로 낸다고 정했다.
  - 정오 8은 경로 2 범위 안의 문장(6.3.7 (2)(3), 6.3.8, 6.3.1 seed 문장)을 바꾸면서 "경로 2"를 한 번도 언급하지 않는다(Grep 0건).
- 실패 시나리오: 경로 2가 발췌 그대로 판정하면 두 경로가 갈린다.
  - $n_{23}$이 1~7이면 경로 1은 `pass`, 경로 2는 0 건수 실패다.
  - 경로 2가 A/A를 계산하면 2.8에 따라 멈춘다.
- 권장 조치(control-expert): 다음 둘 가운데 하나를 정오 8 머리말에 넣고 같은 커밋으로 봉인한다.
  - (가) 경로 2 정오 `jp3_rev6_p2_handoff_ed5_e8.md`를 둔다.
    - 담을 것: 2.7 (2)(3)을 $n_{23}$ 허용 규칙으로 바꿈, 2.8 폐지, 2.1 77행 seed 문장, 교착 서명(기록)
    - 빼야 할 것: 경로 1 이름(`jp3_12b_judge`, 함수 이름, 행 번호, 판정 파일 키 구현명)
    - 봉인 전 확인: `handoff_leak.py`
  - (나) "12b는 경로 2로 판정하지 않는다"를 사용자 결정 근거와 함께 적는다(확인 필요 1).

[실행 전 수정][R] W-1. 8-10 정정 목록이 빠짐없지 않다(원판·정오 1~7에 충돌 문장이 남는다)
- 근거(목록에 없는 곳)
  - 원판 `:79`(0절 요약): "판정은 0 건수(새 FAULT, READY +30 s 초과·상실)…, A/A 바닥 멈춤"
  - 원판 `:311`(6.3.7 첫 문단): "판정은 0 건수다."
    - 8-2는 "(2)·(3) 두 문장"만 바꾼다고 하므로 이 문장이 남는다.
  - 원판 `:295~296`(6.3.5): "$N_{opp}<0.9N$이면 b3을 더한다", "b3을 더한 뒤에도 $N_{opp}$ < 301이면 …"
    - 8-8.1(b3 요구 = 종료 2, b3 실행 없음)과 충돌한다.
  - 원판 `:403`(7절 X-13 구현 항목): "A/A 멈춤이면 종료 2 `aa_floor_stop`이다."
    - 8-10 231행은 이곳을 "원판 **6.6** X-13"으로 적었다. 6.6(`:367~373`)에는 X-13이 없다. 위치를 잘못 적었다.
  - 원판 `:456`(7.2 구현 시험): "A/A 3쌍이면 종료 2(`aa_floor_stop`)이고, VBK 파일을 읽지 않는다"
    - 8-8.3 7번("A/A 4쌍 → `decided`/`needs_b4`")과 정면으로 충돌한다.
  - 정오 2 `:103`(2-6): "앞 단계가 종료 0으로 끝나기 전에는 다음으로 가지 않는다."
    - 종료 2로 끝난 `12b_vbk0_base`의 출력을 다시 쓰는 것(8-1.3, 8-9 1번)과 충돌한다.
- 범위가 서로 다르다
  - 8-9 216행: "원판 8절 4.(6) 1~6 대체"
  - 8-10 229행: "2번 항목을 8-9의 2번으로 바꾼다"
- 실패 시나리오: 6행의 우선 조항으로 해석상 정리는 된다. 그러나 구현자가 원판 7.2 시험 목록을 따르면 `aa_floor_stop` 시험이나 0 건수 문장이 남는다. 8-10은 빠짐없는 목록처럼 읽힌다.
- 권장 조치(control-expert): 위 6곳을 8-10에 더한다. 위치 오기를 고친다. 8절 4.(6)의 대체 범위를 하나로 정한다.

[실행 전 수정][T] W-2. 8-7 148행의 공개 문장이 사실보다 좁다. "확인 대상" 문장은 확인 결과로 바꾼다
- 근거
  - `dry_c.json`(43줄)의 키 줄 번호(값은 보지 않음): L26 `categories`(L27~31 분류 다섯), L33 `changed_opportunity_pairs`, L34 `c`, L35 `trigger_share`, L36 `problems`(L37 `setting_defects`, L38 `not_judgeable`, L39 `failures`), L41 `status`, L42 `exit`.
  - 148행은 26~42행을 "(`problems.failures`·`not_judgeable` 빈 목록, `status` `written`, `exit` 0)"이라고만 적었다. 실제 범위에는 분류 수, 바뀐 짝 수, `c`, `trigger_share`, `setting_defects`도 있다.
  - 맞는 부분
    - 최상위 키 목록 10개는 사실과 같다.
    - `cmd_dry_c` 1010~1057행, `classify_pair` 410~438행이라는 범위도 맞다.
- 권장 조치(control-expert): 148행을 다음과 같이 고친다. 근거는 R-8.
  - stats-design-expert가 읽은 범위에는 `categories`, `changed_opportunity_pairs`, `c`, `trigger_share`, `problems` 세 목록, `status`, `exit`가 있었다.
  - `failures`는 `dry-c` 경로에서 쓰는 곳이 없어 언제나 빈 목록이다.
  - 따라서 이 파일에는 VBK (1)~(3) 결과가 없다.
  - VBK에서 나온 양은 `c`뿐이다. `c`는 F0~F2u에만 썼고 $k_{allow}$(c = 1)와는 무관하다.
  - 8-12 247행의 남은 일 "verif: `dry-c` 경로 확인"은 끝난 것으로 적는다.

[실행 전 수정][I] W-3. 두 커밋 운용(8-9)의 정체성 증명에 공백이 있다
- (a) diff 한정을 검증하는 수단이 없다
  - 210행 "한정한다"만 있다.
  - 권장: `git diff --name-only 606f8713 <도구 커밋>`을 기록하고 허용 경로 목록과 대조한다. 목록을 벗어나면 멈춘다는 문장을 둔다.
- (b) 폐포 검사가 정적 import만 본다
  - `las_t3_dg3.py:39,59~63`은 `importlib`로 `05_tests/unit/pre_las_preset_runner.py`를 실행한다(LAS off일 때).
  - 8-9가 diff에 "시험"을 허용하므로, 이 파일은 정적 폐포 밖에 있으면서 바뀔 수 있다.
  - 권장: 이 파일 변경을 금지하거나 폐포 입구에 더한다.
  - [추정] 12b VBK·VBK0는 LAS 켬이라 이 경로를 실행하지 않으므로 영향은 낮다.
- (c) 실행 스크립트가 도구 커밋에서 바뀐다
  - 8-9 210행은 "실행 스크립트" 변경을 허용한다.
  - 시뮬레이션의 env·인자를 만드는 곳이 ps1이다: `step6c_vbk.ps1:28~31`의 `Get-R79Environment`, `-Workers 4`, mask, `--affinity`.
  - 폐포 검사는 ps1을 보지 않는다. 그런데 VBK0 b1·b2를 다시 쓰므로 VBK와 b4 VBK0는 같은 조건이어야 한다.
  - 권장: VBK·b4 VBK0 identity(`threads` 5개, `python`, `python_version`, `git.head`, `rules_seals`)와 env가 b1·b2 VBK0와 같은지 대조한다. 허용 차이는 8-1.2 33행대로 설정, 계획 경로, T4h 폴더, mask다.
- (d) 8-1.3 고정값을 누가 대조하는지 없다
  - FIXED_INPUTS는 파일 목록이라 T4h 요약(파일이 아니라 다이제스트)을 담지 못한다.
  - 권장: `12b_decide_e8` 단계가 `decision.inputs.vbk0.b{1,2}.run_sha256`과 `t4h_sha256_digest`를 8-1.3 값과 대조하고, 다르면 멈추게 한다.
  - npz 334개는 9460b2e0에 추적되어 있으므로 개별 sha로 목록에 넣을 수도 있다.
- (e) 멈춘 단계의 출력을 받는 규칙이 없다
  - `12b_vbk0_base`는 `.stop`(종료 2)으로 끝났고 `.done`이 없다.
  - `step6c_vbk.ps1:11~13`은 `.done`이 있는 VBK0 단계만 입력·선행 조건으로 받는다. 정오 2 2-6 103행과도 충돌한다(W-1).
  - 권장: 8-9에 "`12b_vbk0_base_a1`을 (d)의 sha 대조로 받는다"는 수용 규칙을 둔다.
- (f) 남은 단계를 어느 커밋 스크립트로 돌리는지 없다
  - 대상: (7) T-JR-13~15, T-CK·DROPOUT, j9_main
  - 8-10이 2-9.6에 더한 `ready_rule.verdict`·`allow_k` 대조는 step8 스크립트를 바꿔야 가능하다. 606f8713판 `step8_j9main.ps1:30~35`는 sha·`status`·`exit`만 본다. 그러므로 이 대조는 도구 커밋에만 있다.
  - 반면 시뮬레이션 정체성은 606f8713이다.
  - 권장: 단계마다 (스크립트 커밋, `--expect-commit`)을 표로 정한다. 12b VBK와 판정은 `step6c_vbk.ps1` 한 단계에 함께 들어 있으므로, 한 단계 안에서 정체성 기대가 둘로 갈린다는 점도 표에 적는다.

[실행 전 수정][E] W-4. 기록 항목의 예외가 판정 전체를 종료 3으로 지울 수 있다
- 근거
  - 8-8.2 189행은 "배열 없음"만 `stall_signature_computed` false로 정했다.
  - `main()`은 그 밖의 예외를 모두 종료 3으로 바꾼다(`jp3_12b_judge.py:1215~1218`).
  - 예외가 날 수 있는 곳
    - 서명 계산: `t_s`와 `motor_stroke_m`의 길이 불일치, `phase` 대소문자(도구 안에서도 `phase_fault_pairs`는 소문자로, `trigger_phase`는 대문자로 바꾼다)
    - `n_vbk0_worse_plus30`: 8-6 140행 "기회 짝에서 (VBK0 − VBK)…"는 VBK READY가 None일 때 정의가 없다.
    - `by_cell`·`by_block`
- 실패 시나리오: 판정 항목은 계산됐는데, 기록 계산 한 곳의 TypeError 때문에 `status` `error`(종료 3)가 된다. 실패가 셈해졌어도 종료 1이 사라진다(정오 2 2-10의 취지에 반한다).
- 권장 조치
  - control-expert:
    - 기록 항목(서명, `n_vbk0_worse*`, `by_cell`, `by_block`)은 `grade_transitions`(1128~1137행)처럼 예외 시 computed false와 사유를 남기고 상태·종료 코드는 그대로 둔다고 적는다.
    - `n_vbk0_worse_plus30` 대상을 "두 쪽 모두 READY에 닿은 기회 짝"으로 명시한다.
    - `phase` 비교는 소문자 비교로 명시한다.
  - python-expert: 구현에 반영한다.

[실행 전 수정][R·E] W-5. 결정 기록 키가 둘로 나뉜다. 없는 키를 어떻게 다루는지 미정이다
- 근거
  - 8-8.1 163행은 새 키 `blocks_used`를 둔다.
  - 기존 `blocks`는 판정의 짝 순회(`jp3_12b_judge.py:635`)와 VBK 실행 블록 선택(`step6c_vbk.ps1:19`)에 쓰인다.
  - 8-8.2 167행은 `blocks_used`만 검사한다.
  - "allow_k가 … 다르거나"라고만 적어, 키가 없을 때는 정하지 않았다.
  - 8-10 2-9.6 추가 문장(233행)도 `ready_rule` 블록이 없을 때를 정하지 않았다.
- 실패 시나리오: 구현 결함으로 `blocks` ≠ `blocks_used`이면, 돌린 블록과 허용 규칙의 블록이 다르다. 그래도 not_judgeable이 되지 않는다.
- 권장 조치(control-expert): 다음 셋을 명시한다.
  - `set(blocks_used) == set(blocks)`가 아니면 not_judgeable
  - `allow_k`·`blocks_used`가 없으면 not_judgeable
  - 2-9.6에서 `ready_rule` 블록이나 키가 없으면 "통과 아님"

[실행 전 수정][S] W-6. `stats_e8_review/`가 커밋 목록에 없다. 그 `SHA256SUMS`는 CRLF다
- 근거
  - 8-12 250행의 메인 커밋 대상은 "`aa_stop_606f8713/`·`stats_e8/`"뿐이다.
  - 정오 8 11·71·122행은 `stats_e8_review`의 파일 sha를 판정 근거로 인용한다.
  - `git status --ignored`: `?? …/stats_e8_review/`(추적 안 됨, ignore 아님)
  - `baseline_check sums`: 해시는 2/2 일치하지만 `sums_crlf`(CRLF 2줄)이다.
  - `-text`가 걸려 있어 CRLF 그대로 커밋된다.
- 권장 조치(메인)
  - `stats_e8_review/`를 함께 커밋한다.
  - 커밋 전에 그 `SHA256SUMS`를 LF로 다시 쓴다(stats-design-expert에게 맡기거나 메인이 한다).
  - `stats_e8/`과 `aa_stop/`의 SUMS는 LF이고 일치한다(mismatch·missing·unlisted 0).

[실행 전 수정][T] W-7. 블라인드 목록이 파일 이름 나열이라 형제 파일이 빠진다
- 근거
  - 8-7 151행은 `VBK_c92.json`, `VBK_c93.json`, partial, `_t4h/`, `logs/`를 나열한다.
  - `cdry_a1`에는 `VBK_c92.identity.json`·`VBK_c93.identity.json`도 있다(추적됨).
  - VBK0 identity로 본 키 구조: `time`, `threads`, `git`, `affinity_mask`, `rules_seals`.
  - [추정] 결과 값은 없다. 하지만 시작·끝 시각으로 실행 시간이 드러나고, 실행 시간은 시간 초과 수의 약한 신호다.
- 권장 조치(control-expert): 블라인드를 글롭 `cdry_a1/VBK_c92*`·`VBK_c93*`로 적는다. 메인은 python-expert 위임 지시에 "블라인드 파일을 시험 픽스처로 쓰지 않는다"를 넣는다.

[기록][C] R-1. 97행 "c 건식 VBK0에 모두 있다"의 근거 표기가 부정확하다
- `aa_fault_floor.py:178~181`은 READY가 있는 줄을 건너뛴다. 그래서 `signature_arrays_missing` 0은 c 건식 미도달 2줄만 본 값이다.
- 문장 자체는 사실이다. 이번 감사에서 `key_presence --npz-dir`로 c92·c93 VBK0 160파일에 `t_s`, `phase`, `motor_stroke_m`이 모두 있음을 확인했다(종료 0).
- 출처는 이 확인으로 바꿔 적기를 권한다.

[기록][C] R-2. 82행 "2개 이상일 확률 약 0.3~0.5 %"
- 같은 기대 수(0.07~0.11)를 Poisson으로 계산하면 0.23~0.56 %다.
- 다른 모형이면 그대로 둬도 된다. stats-design-expert가 확인한다.

[기록][S] R-3. `aa_stop_606f8713/SHA256SUMS`의 sha(e387907e…)가 정오 8 본문에 인용되지 않았다
- 8-9 FIXED_INPUTS에 들어가므로 판정에는 영향이 없다.
- 8-1의 근거 폴더이므로 본문에도 인용하기를 권한다.

[기록][R] R-4. 8-2 "중단"의 뜻
- 러너 error 줄은 판정 도구에서 not_judgeable로 간다(`load_lines` 275~276행).
- 그러므로 READY 상실의 "중단"은 제어기 수준의 중단으로 읽힌다. 원판 314행과 같은 낱말이다.

[기록][R] R-5. 52행 T4h 요약 규칙의 서술
- `input_record`(367~378행)는 `"{sha256}  {이름}\n"`을 이름순으로 이어 붙여 sha256을 낸다.
- 함수 이름을 인용했으므로 정의로는 충분하다. 서술은 근사다.

[기록][T] R-6. $k_{allow}$는 판정 짝의 VBK0 쪽을 본 뒤에 정했다
- 83·149행에 공개되어 있다.
- VBK0 자료로는 VBK 결과를 알 수 없다. VBK0 미도달 짝은 규칙상 $n_{23}$에서 빠진다.
- 정해진 멈춤(A/A) 뒤 사용자 결정으로 바꾼 개정이다. 판정서에 이 순서를 그대로 적는다.

[기록][E] R-7. $N_{opp}$, 블록, 판정 행 0의 처리
- `blocks_used`가 빈 집합이면 not_judgeable이다(8-8.2 167행).
- $N_{opp}$ = 0이면 not_judgeable이다(1125~1126행 그대로).
- VBK0 미도달 짝만 있으면 $n_{23}$ = 0이다. 그래도 $N_{opp}$ = 0이라 not_judgeable이다. 단 (1)·(4)에서 실패가 있으면 2-10 순서로 `failed`다.
- b3이 필요하면 종료 2다(8-8.1).
- 통과로 새는 빈 집합은 없다. `gate_scan`(현행 도구): 발견 0, `missing_key_default` info 1.

[기록][R] R-8. 요청 1의 코드 확인 결과(`dry-c`가 `failures`에 쓰는 경로)
- 확인한 파일은 실행 커밋 blob이다. `git hash-object`와 `git ls-tree 606f8713`이 77eb401f로 같다.
- `Problems.failures`에 append하는 곳은 넷뿐이다. 이 세 함수는 `cmd_judge` 1124행에서만 불린다.
  - 654행 `judge_pairs`: (1)
  - 683·686행 `_judge_ready`: (3)·(2)
  - 703행 `_judge_jp3`: (4)
- `cmd_dry_c`(1010~1057행)가 부르는 경로는 `failures`에 쓰지 않는다.
  - `dry_run_keys`: 973행 `setting_defects`
  - `load_dry_arm` → `load_lines`: 273·276·284행 `not_judgeable`, 278행 `setting_defects`
  - `check_presence`: 322행 `not_judgeable`
  - 1027행: `setting_defects`
  - `classify_pair`: 416~434행 `setting_defects`
  - 1053행: `not_judgeable`
- 결론: `dry_c.json`의 `failures`는 입력과 무관하게 언제나 빈 목록이다. 건식 VBK의 (1)~(3) 판정 결과를 담을 수 없다.
- 다른 두 빈 목록이 드러내는 것
  - `not_judgeable` 빈 목록: VBK 줄이 모두 있고 error 줄이 없으며, 판정 키·T4h 배열이 있다는 존재 정보다.
  - `setting_defects` 빈 목록: 계획 sha, `v5_setting`, (가)(나)(다), 주입·래치·트리거 전 대체가 VBK0와 같다는 짝 동일성 정보다.
  - 둘 다 READY 시각이나 FAULT 사건이 아니다.
- `status` `written`·`exit` 0은 이미 알려진 사실이다(`cdry.done`, 이후 단계 진행).
- 오염 경로는 없다. 공개 문장만 고친다(W-2).

[기록][S] R-9. 도구 보고 가운데 예상된 것과 오탐
- `seal_check`: 정오 8 `seal_missing`과 `rule_untracked`는 봉인 전이라 예상된 것이다.
  - CRLF·BOM 발견은 없다(정오 8은 LF, BOM 없음).
  - `_draft.md`의 seal 없음은 판이 아니다.
- `ref_check`: `ref_missing` 14는 추적 안 된 폴더 안 파일을 맨 이름으로 적은 경우라 오탐이다. Glob으로 모두 있음을 확인했다. `12b_vbk.done`은 앞으로 생긴다.

## 규칙↔도구 대조표 (정오 8 ↔ 실행 커밋 `jp3_12b_judge.py`, 구현 전 차이)
| 항목 | 정오 8 | 현행 도구 | 판단 |
|---|---|---|---|
| (2) 지연 비교 | 정오 8 61행: `round(VBK−VBK0, 6) > 30`, 정오 8 199행 `round(x, 6)` | 685행: 같은 식 | 같다. 바뀌는 것은 짝마다 실패를 더하지 않는 점(683·686행 → 세기) |
| 경계 시험값 | 정오 8 197~198행 | python-dev 3.13.15 재계산: 130.000001은 센다. 130.0, 130.0000004, 130.0000005는 30.0이라 세지 않는다. `round(30.0000005, 6)` = 30.0 | 문장과 같다 |
| 허용 | b1·b2 ≤ 7, b1·b2·b4 ≤ 9, b3 = 종료 2 | 없음(0 건수) | 새로 구현한다. 부등호(`≤` 통과, `>` 실패)는 8-8.3 1·2와 일관된다 |
| A/A 정의 | 6.3.8 정의 그대로 기록 | 442~459행: 같은 정의, 505~506행에서 멈춤 | 멈춤을 지우고, 키를 `aa_floor`로 바꾼다 |
| b3 | 요구되면 종료 2 | 515~526행: `needs_b3`(종료 0) | 바뀐다. 원판 6.3.5도 고쳐야 한다(W-1) |
| 상태 순서 | 2-10 그대로 | 165~175행: failed > setting_defect > not_judgeable > pass | 같다 |
| 결정 기록 검사 | `blocks_used`·`allow_k` 대조 | 724행: `status` decided만 본다 | 더한다. W-5 |
| 종료 코드 표 | `aa_floor_stop` 삭제 | 81·1150행 | 지운다 |
| 통과 문장 분모 | $N_1$ | 1139~1142행: `n_opp` | 바뀐다(`n_fault_judged`) |
| 교착 서명 | 기록. 4조건(20 s − 1e-6, < 1 mm, 마지막 단계 level/probe, PHASE_FAULT 없음) | 없음 | `aa_fault_floor.py:83~96`의 구현이 문장과 같다. 도구 구현에서 W-4를 반영한다 |
| seed | b1~b4 = 40~43(정오 1 0절) | `selection.json` blocks: 40·41·42·43 | 같다 |

## 재집계 표 (독립 스크립트, 판정 도구 import 없음)
| 항목 | 정오 8 값 | 재집계 | 차이 | 판단 |
|---|---|---|---|---|
| A/A 센 쌍 | 4/167, 키 4개(정오 8 22~25행) | 4/167, 키 집합 같음, decision.json `counted`와 같음 | 0 | 맞음 |
| 두 seed 모두 미도달 | 2쌍(정오 8 27행) | 2쌍, 키 같음 | 0 | 맞음 |
| 4쌍의 READY 표 | 정오 8 22~25행 | 0.1 s 반올림으로 모두 같음. 다리·국면(RL τ_C, FR τ_R, RL τ_R, RL τ_C)도 같음 | 0 | 맞음 |
| 둘 다 도달한 짝의 \|ΔREADY\| | 162쌍, 중앙값·90 %·99 %·최대 | 162쌍. 네 값 모두 0.1 s 반올림이 문장과 같음 | 0 | 맞음 |
| $N_{opp}$(b1·b2) | 327 ≥ 300.6 | 327 | 0 | 맞음 |
| VBK0 b1·b2 미도달 줄 | 7 | 7 | 0 | 맞음 |
| 서명 | 12b는 5(b1 g6\|52·56·59, b2 g6\|56·ref\|16), 아님 2(g8\|30), c 건식은 1/1 | `aa_fault_floor.json`과 같음 | 0 | 맞음 |
| (1) 바닥 | 0/167, VBK0 FAULT 줄 0/334, c 건식 0/160 | 같음, 분해 불일치 0 | 0 | 맞음 |
| τ_C 8/248의 95 % 구간 | 1.4~6.3 % | Clopper-Pearson 1.40~6.26 % | 반올림 | 맞음 |
| 8-5 표($P_1$) | F0 4.2·22.6·53, F2u 6.2·31.7·67, F3 28.6·86.7·99.7, 결합 32.0/32.1, 87.0/88.8, 93.6 | 손 재계산($1-e^{-c\cdot334\cdot q}$)이 모두 일치 | 반올림 | 맞음 |
| 고정 sha와 T4h 요약 | b1 87e76b0b…/561438f1…, b2 205079fe…/b0c4a79b… | 실제 파일 sha와 요약(167파일씩) 모두 같음. decision.json `inputs`와도 같음 | 0 | 맞음 |
| 인용 sha | 원판·정오 1~7, `stats_e8` SUMS 8b906fb9, `e8_review_check.py` ab2b0764, `.json` 78fe9724 | 모두 같음 | 0 | 맞음 |

## 확인 필요
1. 12b에 경로 2 판정을 쓰는가. 넘김 6(`jp3_rev6_p2_handoff_ed5.md` 2절)은 12b를 포함한다. 쓰지 않는다면 그 결정과 근거를 정오 8에 적는다(B-1).
2. 8-9 이후 단계를 어떻게 돌리는가: (7), T-CK·DROPOUT, j9_main 각각의 스크립트 커밋과 시뮬레이션 커밋(W-3 (f)).

## 위임 필요
- control-expert: B-1(경로 2 정오 또는 미사용 문장), W-1, W-2, W-4 문장, W-5, W-7, R-1 출처 표기. 고친 뒤 정오 8을 다시 감사한다.
- stats-design-expert: R-2(82행 확률 표기). W-6의 `stats_e8_review/SHA256SUMS` LF 재작성(또는 메인이 한다).
- python-expert(8-8 구현 때): W-3 (c)(d)(e)를 실행 스크립트에 반영하고 W-4를 도구에 반영한다.
- python-expert: `tools/verif` 후보 하나.
  - 검사: `ref_check.py`
  - 증상: 추적 안 된 폴더 안 파일을 맨 이름으로 인용하면 `ref_missing`("작업 트리에도 없음")으로 낸다. 실제로는 작업 트리에 있다.
  - 입력: 정오 8. 출력: `ref_missing` 14, 종료 1.
  - 기대: `ref_untracked`(warning)로 분류.

## 메인 세션 권고
- 경로 2 정오를 둔다면 봉인 전에 `handoff_leak.py <e8 넘김> --names <경로 1 이름 사전>`으로 누설을 확인한다.
- 정오 8 봉인 커밋에 함께 넣을 것: `.sha256`, `aa_stop_606f8713/`, `stats_e8/`, `stats_e8_review/`(W-6). 넣기 전에 `git status --ignored`로 다시 확인한다. 이번 확인에서는 ignore 0건이었다.
- 재개 직전 실행 전 감사에서 볼 것
  - W-3 (a)~(f)
  - 8-8.3 커버리지 표(정오 7 7-4)
  - `junit_skips.py --critical`
  - `ps1_lint.py`
  - `placeholder_scan.py --pattern-set both`
  - `key_presence.py`: 판정이 읽는 키, VBK0 `t_s`·`phase`·`motor_stroke_m`

## 검사하지 못한 것
- VBK T4h에 `t_s`가 있는지: 블라인드라 보지 않았다. 정오 8은 없으면 기록 결함으로 처리한다고 정했다.
- 사람이나 에이전트가 블라인드 파일을 실제로 열었는지: 파일 접근 기록이 없다. 확인한 것은 분석 스크립트(`aa_stop`, `stats_e8`, `stats_e8_review`)가 `VBK_c9*`·`logs`를 읽지 않는다는 것뿐이다(Grep).
- `stats_e8`의 시뮬레이션(F3·F3h·F4·MDE80)을 다시 돌리지 않았다. 8-5 표만 손으로 다시 계산했다.
- 8-1.2 원인 분석의 세부(행정 폭 0.40~0.66 mm, 고장 전 0.26 mm)를 다시 계산하지 않았다.
- 도구 커밋이 아직 없어 8-8 구현을 대조하지 못했다.

## 실행한 검증
- 의존성 점검: `depcheck.ps1`(CHECKED).
- 해시: `Get-FileHash`로 원판, 정오 1~8, 각 `.sha256`, `stats_e8`·`stats_e8_review`·`aa_stop` SUMS와 인용 파일, 경로 2 넘김 6과 정오 1을 쟀다.
- git 조회
  - `git rev-parse`, `git hash-object`, `git ls-tree 606f8713`(판정 도구 blob 동일)
  - `git check-attr text eol`: 정오 8, SUMS, 결과 파일 모두 text unset(`-text`). `core.autocrlf` true지만 보호된다.
  - `git check-ignore -v`, `git status --ignored --porcelain`: ignore 0건
  - `git ls-files`: `12b_vbk0_base_a1` npz 334개와 `cdry_a1` 추적 확인
  - `git show --stat 9460b2e0`
- verif 도구(python-dev `-I -B`, `MKL_THREADING_LAYER=TBB`)
  - `baseline_check.py sums` × 3: mismatch 0. `cited_untracked`는 커밋 전이라 예상된 것. `stats_e8_review`는 `sums_crlf`.
  - `seal_check.py --repo … "jp3_remedy_spec_v5*.md" --code <worktree coupled>`
  - `ref_check.py`(정오 8)
  - `gate_scan.py`(현행 판정 도구)
  - `key_presence.py --npz-dir` × 4(VBK0 b1·b2, c92·c93): 종료 0
- 즉석 스크립트(python-dev `-I -B -X utf8`, scratchpad `verif-e8preseal\`)
  - `chk.py`: 고정 sha·요약 재계산, decision·dry_c 키 배치(값 비출력), 반올림 경계
  - `recount.py`: A/A, $N_{opp}$, 미도달, CP, Poisson
  - `pct.py`: 백분위, 4쌍 표
  - `ff.py`: 서명·FAULT 바닥
  - `idkeys.py`, `idend.py`: identity 키 구조
  - 끝난 뒤 하위 폴더를 통째로 지웠다(확인: 없음). worktree에 `__pycache__`가 생기지 않았다.
- 실행 중인 러너가 없는지 확인: `Get-CimInstance Win32_Process`(조회만)
- 12b 출력이 없는지 확인: `Get-ChildItem *12b*`(메인과 worktree의 `j9_runs`)
- 최종 판정 직전에 source_guard verify로 입력 25개가 감사 중 바뀌지 않았음을 다시 확인했다. 정오 8은 여전히 ad2643cc다.
- 메모리: `audit_pitfalls.md`에 일반 함정 한 항목을 더했고 `MEMORY.md` 색인을 갱신했다(Edit).
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v5.md fe6f5844…, jp3_remedy_spec_v5.md.sha256 0dd1676c…, jp3_remedy_spec_v5_erratum1.md 4721352e…, jp3_remedy_spec_v5_erratum1.md.sha256 d508c2df…, jp3_remedy_spec_v5_erratum2.md 639c54e9…, jp3_remedy_spec_v5_erratum2.md.sha256 054bfb8d…, jp3_remedy_spec_v5_erratum3.md 7bab9217…, jp3_remedy_spec_v5_erratum3.md.sha256 29f02a7f…, jp3_remedy_spec_v5_erratum4.md 4bc4ecdd…, jp3_remedy_spec_v5_erratum4.md.sha256 0422bf7d…, jp3_remedy_spec_v5_erratum5.md 8487bd55…, jp3_remedy_spec_v5_erratum5.md.sha256 aef4a8cf…, jp3_remedy_spec_v5_erratum6.md 9a92bd34…, jp3_remedy_spec_v5_erratum6.md.sha256 eadc3068…, jp3_remedy_spec_v5_erratum7.md 38fdc574…, jp3_remedy_spec_v5_erratum7.md.sha256 5192e12a…, jp3_remedy_spec_v5_erratum8.md ad2643cc…, SHA256SUMS 8b906fb9…, SHA256SUMS 22a456f4…, SHA256SUMS e387907e…, 12b_vbk0_base.stop ee4b0660…, decision.json 445a13e7…, VBK0_b1.json 87e76b0b…, VBK0_b2.json 205079fe…, jp3_12b_judge.py 43779009…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
