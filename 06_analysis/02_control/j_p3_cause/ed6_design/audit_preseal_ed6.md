## 감사 요약
- 본 결과: 판정 대상 결과 수치는 보지 않았다. 연 파일은 다음뿐이다. 판 5 j9_main jsonl(`j9_runs/606f8713/j9main_a1/j9_main.jsonl`, 본 행)에서는 job 키와 `head_only_declared`, probe·b1off jsonl(본 행)에서는 키 존재만, `phase_vb_r5.jsonl`에서는 job 키·설정만 봤다. 블라인드 경로(`606f8713/cdry_a1/**`)는 열지 않았다. Grep·스캔에서도 glob으로 뺐다.
- 대상·시점: 실행 전(판 6 봉인 직전).
  - 명세 `jp3_remedy_spec_v6.md` 개정 12(1ebdb308)
  - 넘김 `jp3_rev6_p2_handoff_ed6.md`(8f160c83)
  - 구현 ed6-impl ac3c25a7(clean, locked, master 미병합)
  - 기준: 판 5 명세 fe6f5844, 정오 1~8(4721352e…8c420e85, 모두 `.sha256`과 같음), v5_criteria 06ed0384
- 판정: **차단 2 / 실행 전 수정 13 / 기록 12**. **지금 상태로는 봉인할 수 없다.** 차단 2건과 실행 전 수정 13건은 모두 명세·넘김 문장을 고치거나 더하면 풀린다. 코드 수정은 필요 없다. 고친 판을 다시 보는 데는 짧은 재감사(문장 대조)면 된다.

## 발견 사항 (심각도순)

**[차단][T] B-1. 봉인 전 판 6 제어기로 12a의 유일한 J-P3 판정 행을 돌린 실행이 공개 목록에 없다**
- 근거
  - `ed6_design/prelock_12a_755a15d8/run_12a_short.ps1:1-14`("Change 12 item 4: short 12a runs of VBL / VBL0"). 이 스크립트는 `dg3_VBL`·`dg3_VBL0`을 키 `L2|s0|g6|52|ref|J1|top|Fs0`·`L3|s0|g6|5|…`로, `L1_VBL`·`L1_VBL0`을 `L1|s0|g6|52|…`로 돌렸다. 실행 시각 2026-11-24 02:23~02:25, 출력은 SHA256SUMS 29항목(해시 불일치 0)이다.
  - 명세 6.6(599행)은 "J-P3 기대 판정 행 수 = 1: 등급이 normal 이하인 키는 L2 키 하나다"라고 한다. 그 키가 위 L2 키다(판 5 `dg3_a1/dg3_VBJ.json` 등에 같은 키가 있다).
  - 명세에는 `prelock`·`755a15d8`가 0회 나온다(Grep). 머리말 본 행 표(54-60행)에도 없다. O6-5(71행)는 "판 6 결과는 아무도 보지 않았다"고 적었다.
- 실패 시나리오: 12a J-P3 결과를 봉인 전에 알 수 있었는데, 판정서에는 미관측처럼 보인다.
- 권장 조치(control-expert 문안 → 메인 봉인)
  - 본 행 표에 "12a 단축 실행(755a15d8, 2026-11-24 02:23): VBL·VBL0 × Dg-3 L2 1키(= 12a 유일한 J-P3 판정 행)·L3 1키, L1 VBL·VBL0 × 1키"를 더한다.
  - O6-6을 새로 둔다: 누가 실행했는지, 무엇을 봤는지, 판 6 설계(개정 12)에 썼는지.
  - O6-5 문장을 "판 6 실행 커밋의 판정 단계 결과는 아무도 보지 않았다. probe 1bd405c8·b1off(e8ddf04e)·12a 단축 실행(755a15d8)은 본 행이다"로 고친다.
  - 12절에도 같은 항목을 더한다.

**[차단][R/E] B-2. 봉인 뒤로 미룬 판정 도구 작업 셋 가운데 Y-6에만 "그 전에는 판정 불가" 관문이 있다**
- 근거
  - ed6-impl에 다음 이름이 없다: `not_applicable_harness`, `j7_stiffness_exempt`, `exempt_applied`(Grep, 04_scripts). Y-5(판 5 읽기 (1)~(3) 규칙화, 8절 681행)는 구현되지 않았다.
  - `jp3_12b_ppred.py:5-6`: "wiring it into jp3_12b_judge.py decide is the tool commit after the seal". 즉 Y-10의 decide 연결도 봉인 뒤다.
  - 명세에는 Y-6에만 관문이 있다(479행 "도구 커밋이 없으면 감도 단계는 판정 불가"). 4절 실행 순서에는 도구 커밋 단계가 없다.
- 실패 시나리오
  - j9_main을 판 5 판정 도구로 판정하면 읽기 (1)~(3)이 빠진 판정이 나온다.
  - 12b decide를 판 5 도구로 돌리면 정오 8의 고정 k(7·9)가 쓰인다. 6.4는 이 값을 판 6에서 금지했다.
- 권장 조치
  - 4절 5 앞에 단계를 넣는다: "봉인 뒤 도구 커밋(Y-5 j9_main 판정 보완, Y-6 감도·확인 판정, Y-10 decide 연결)과 단위 시험, verif 감사. 해당 단계는 그 전에 판정 불가(통과 아님)".
  - 479행의 "감도 단계"가 6.3 (가)와 (나) 격자 판정도 포함한다고 명시한다.

**[실행 전 수정][R] M-1. A(ii) 끝 목격이 문면은 E3, 구현은 단일 읽기다**
- 근거
  - 명세 178행 "또는 E3 Δs ≥ 1.0 mm", 181행 "신장 목격: E3 Δs ≥ 1.0 mm"
  - 구현 `lock_start_b.py:892-896`은 `moved_m = sign*(stroke_m[leg] - fill.start_stroke_m)`(단일 읽기 차)이다. 213행 docstring도 "Retract stroke witness (single reads)"이다.
  - hydraulics `h6_review_report.md:92`는 "Δs ≥ 1.0 mm, σ_Δ 0.14 mm 7σ"로, 단일 읽기 기준이다.
  - probe와 7절 예측은 구현대로 돌았다.
- 권장 조치: 178·181행을 "잠김 출발 읽기 대비 단일 읽기 차 Δs ≥ 1.0 mm"로 고친다. 코드를 바꾸면 P6-3 해시가 깨지므로 코드는 두고 문장만 고친다.

**[실행 전 수정][R] M-2. 출력 경로 순서를 아직 "제안"과 옛 행 번호로 적었다**
- 근거
  - 명세 204행 "구현 때 코드로 다시 고정한다", 8절 Y-1(675행) "(제안: B는 7426 뒤·7434 앞, A는 4746 뒤·4755 앞)"
  - 실제 순서(ac3c25a7 `c2.py`)
    - A 바닥: 4800-4803. `_phase_command`(4791) 뒤, `_slow_near_stroke_end`(4804)와 `_apply_output_ramp`(4806) 앞
    - B3: 7476-7483. `_twist_channel_rate` 앞
    - B1: 7504-7505. `_apply_reapproach_speeds`(7503) 뒤, `_apply_pre_loc_lift_pause`(7506)와 `_apply_lift_stroke_guard`(7513) 앞
- 권장 조치: 위 순서를 커밋 ac3c25a7 기준으로 확정해 적는다.

**[실행 전 수정][R] M-3. B3 끝 사유·재시작 범위·보호 방식이 구현에 있고 문면에는 없다**
- 근거
  - `lock_start_b.py:147-150`: `other_reapproach`(다른 다리의 정식 재접근 시작), `replaced`(새 R-5 예측)
  - `c2.py:10239-10241`
  - protect 뒤 재시작 금지의 범위는 "같은 LEVEL 구간"이다. LEVEL을 벗어나면 `clear_protect_block`으로 풀린다(`c2.py:10134-10136`).
  - 명세 278행의 끝 사유 목록은 `handover·resolved·travel_cap·protect·phase` 다섯이다. 254행은 "다시 시작하지 않으며"로만 적었다.
  - 235행 "어느 쪽을 쓸지는 구현 전에 하나로 고정한다"에 대해, 구현은 고정 문턱(`b3_protect_predictive=False`, 246행)이다.
- 권장 조치: 셋을 문면에 넣는다.

**[실행 전 수정][R] M-4. 3.4 표에서 VBL0의 쓰임이 틀렸다**
- 근거: 286행은 VBL0을 "T8, 12b 기준 팔"이라 적었다. 6.4·6.6·넘김 1.1에서 12b 기준 팔은 VBKL0이고, VBL0은 12a 기준 팔이다.
- 권장 조치: "T8, 12a 기준 팔(6.6)"로 고친다.

**[실행 전 수정][R] M-5. 299행 "python-expert가 봉인 전에 … 덧붙인다"가 비어 있다(채울 곳이 남음)**
- 근거: 구현에서 A·B 꺼짐 줄에는 `lsb_components` 키가 없다. `verdict_runs.py:287-298` `lock_start_b_meta`가 빈 dict를 돌려주고, `v5_options.py:271-273`이 빈 값을 지운다.
- 권장 조치: "키가 없다"로 확정한다. 5행 "채울 곳은 모두 채웠다"와도 맞춘다.

**[실행 전 수정][I] M-6. 정체성 검사가 구성 요소 목록만 보고 매개변수는 보지 않는다**
- 근거
  - `HydraulicOptions.lsb_parameters`(`v5_options.py:206-229`)로 줄마다 매개변수를 바꿀 수 있다.
  - 줄과 T4h에는 `lsb_settings`가 남는다(`run_v5.py` run_one, `verdict_runs.py:281-295`). b1off 40줄에서 40/40 있음을 `key_presence`로 확인했다.
  - 6.1의 5번 항목은 `lsb_components`만 본다.
- 권장 조치: 경로 1 정체성에 "`lsb_settings`가 봉인 기본값(3.1~3.3 값)과 같다"를 더한다.

**[실행 전 수정][T] M-7. 6.3의 "격자 768은 VB·VBJ(P1~P4)로 돈 적이 없다"(506행)가 VB에 대해서는 사실이 아니다**
- 근거
  - `06_analysis` 전체 json·jsonl을 job 키로 스캔했다. 격자 192줄 가운데 2줄이 `03_hydraulic/coupled/v5/phase_dist/phase_vb_r5.jsonl`(커밋 6be683af, 2026-11-07)에 설정 VB로 있다.
    - `R12 top-FR-Fs0-o0.025-FS24-ready`
    - `R12 top-FL-Fs0-o0.075-FS24-ready`
  - P1~P4 플랜트 설정으로 돈 격자 줄은 0이다. 그래서 미관측 정의 자체는 지켜진다.
- 권장 조치: 문장을 "P1~P4 플랜트로는 돈 적이 없다. 옛 VB(v5 r5)로 2줄이 돌았다(phase_vb_r5)"로 고치고 공개한다.

**[실행 전 수정][R] M-8. 12b seed 선정 출력이 명세와 넘김 어디에도 경로·sha로 고정되어 있지 않다**
- 근거
  - Grep `selection|6687b2dc|ed6_inputs` 결과가 0건이다.
  - 넘김 3.1(119행)은 "선정 출력의 seed·반복 수와 … 일치하는지 본다"고 하는데, 그 선정 출력을 가리키지 않는다.
  - 파일은 `prelaunch_j9/ed6_inputs/x11/selection.json`, sha256 `6687b2dcbd7ec77b0eb28bd8219780967dac4462c16e9e2b57e35e11801f1f70`이다. 이 파일 안 `outputs`의 b1~b4 plan·keys 8개 해시는 실제 파일과 같다.
- 권장 조치: 명세 6.4와 넘김 3.1에 경로와 sha를 넣는다.

**[실행 전 수정][E] M-9. 감도·(가)·(나)에서 줄이나 V0 짝이 빠졌을 때의 처리가 없다**
- 근거
  - 군집 규칙(441-443행)과 격자 "V0 대비 실패 ≤ 1"(504행)은 실패를 세는 규칙이다.
  - 문면에는 J-P3 판정 행 수 불일치만 `setting_defect`로 정해져 있다(439·495행). J1~J11 쪽 줄 수 대조(키 파일 `expected_lines` 184/216/192)는 없다.
  - 격자 192줄 가운데 18줄은 V0가 실패한 줄이다(`v0_pass` false, 기회 174). 이 18줄을 J1~J11에서 어떻게 셀지 문장이 없다.
- 실패 시나리오: 몇 줄이 빠지면 실패 수가 줄어 통과로 판정된다.
- 권장 조치: "키 파일의 줄 가운데 결과가 없거나 V0 짝이 없는 줄이 있으면 그 단계는 판정 불가"를 더하고, V0 실패 18줄의 역할을 확인 필요 1에 따라 정한다.

**[실행 전 수정][E] M-10. 6.5의 `key_presence` 대상 키·배열 목록이 정해지지 않았다**
- 근거: 605행은 "새 기록 키 `lsb_*`, T4h 배열"이라고만 적었다.
- 권장 조치: 판정이 실제로 읽는 이름을 적는다. 적어도 줄의 `lsb_components`·`lsb_settings`·`head_only_declared`·`hydraulics_record.extend_bound_check.*`와 T4h meta `head_only_declared`가 들어가야 한다.

**[실행 전 수정][T] M-11. P6-2 "사례별 A(i)·A(ii)·B 발동 수를 구현 뒤 고정"(381행)의 고정 값이 없다**
- 근거: ed6 시험에 사례 재생 발동 수 고정이 없다(`test_ed6_harness.py` 시험 목록).
- 실패 시나리오: 실행 커밋의 첫 실행 값을 그대로 기준으로 삼으면 멈춤 조건이 공허해진다.
- 권장 조치: 봉인 전에 값을 고정하거나, 멈춤 조건을 "J-P3 판정 키 > 0"만 남기고 발동 수는 기록으로 바꾼다.

**[실행 전 수정][T] M-12. 블라인드 파일 건수 오염 공개**
- 근거: 58행 "c 건식 VBK는 블라인드 유지". control-expert의 j9_runs 전체 Grep(count)이 `606f8713/cdry_a1/VBK_c92·c93 .partial.jsonl`의 경고 건수를 출력했다(호출자 보고).
- 권장 조치: O6-7을 둔다. "control-expert가 <날짜> j9_runs 전체 Grep(건수 모드, 패턴 <…>)을 돌렸고, 출력에 블라인드 VBK_c92·c93 partial jsonl의 건수가 들어 있었다. 줄 내용은 보지 않았다. 판 6 설계에 그 건수를 쓰지 않았다(또는 쓴 곳)"를 적는다. 58행에 "(건수 노출 O6-7)"을 덧붙인다.
- 참고: 12b seed 선정 스캔은 이 블라인드 파일을 열지 않았다. 대신 판 5 키 목록 `ed5_inputs/x11/c92_keys.txt`·`c93_keys.txt`로 대신했다(`selection.json` `scan_keys_files`). 그래서 seed 충돌 판정에는 영향이 없다.

**[실행 전 수정][T] M-13. probe 몫 도구에 쓰인 규칙과 4절 2의 문면이 두 곳에서 다르다**
- 근거(`ed6_probe_share.py`@1bd405c8, probe 시작 23:48 전에 커밋됨)
  - 29-30행·306-314행: B3에는 "no activation rule"이다. 명세 357행은 "발동 0이면 (a)대로 뺀다"고 적었다.
  - 31-32행: "A(i) is also kept when a2b has more stall-signature lines on c04"는 문면에 없는 유지 규칙이다.
- 결과 영향: 없다. B3는 20단위 발동했고 A(i)는 규칙 (b)로도 남는다.
- 권장 조치: "실제로 쓴 몫 규칙"을 문면에 적고 공개한다.

**[기록]**
1. 4절 2(330행)의 probe 날짜가 틀렸다. "2026-11-24 23:48~00:29"가 아니라 2026-11-23 23:48:31~2026-11-24 00:28:58이다(`runner.log`, identity start).
2. 낡은 표기가 남아 있다.
   - 1·3행 "(초안)": 봉인 때 고친다.
   - 6행·60행 "8절 1~3", "8절 1"은 4절 2~3이어야 한다. 81행 "(8절)"은 4절 5~9이다.
   - 102행 B3 "후보", 142행 "Q6-10으로 둔다", 425행 "잠정안"은 이미 닫힌 결정이다.
   - 516행 "(초안, 봉인 때 고정)"은 지금 고정한다.
   - 절 순서가 6.4 → 6.6 → 6.5로 되어 있다.
3. 488행 "개정 12: 만듦, ac3c25a7"과 달리 `confirm_b_grid192.json`은 95cae09d에서 만들어졌다(파일의 `code_identity.head`). v2 키 파일 둘은 ac3c25a7이다.
4. 넘김 3행이 "(개정 9 기준)"이라 적었지만 내용은 개정 12까지 담았다(v2 sha, 104/56, 20000×10). "개정 12"로 고친다.
5. P-pred 가장자리 경우(결과 영향 없음, 기록)
   - 구현은 `max(n_both,1)`(`jp3_12b_ppred.py:250`)을 쓴다.
   - 구현은 p̄ ≥ 1이거나 사례가 2개 미만이면 ρ = 0으로 둔다(203행). 넘김 3.2와 명세 6.4는 p̄ ≤ 0만 정의했다.
   - 넘김 "p_c = 0이면 π_i = p_c": 구현은 ρ > 0일 때 k/(a+n)을 계산한다. Beta 추출에서 p_c = 0은 확률 0이라 실제로는 나오지 않는다.
6. `lock_start_b.py:236` docstring은 이동량을 "|n_j τ̇| T"로 적었다. 실제 셈은 `c2.py:10250-10252`의 가장 빠른 다리 기준(명세대로)이다. 낡은 docstring이다.
7. `ed6_design/stats_v6/SHA256SUMS`가 CRLF다(37줄). -text라 그대로 커밋된다. LF로 다시 쓰기를 권한다(stats-design-expert 또는 메인).
8. 키 파일 메타(`generation_command` `ed6_key_lists.py`, `rows: run_v5.required_rows()`)가 경로 1 도구 이름을 경로 2 입력에 싣는다. 이름만이고 코드·출력은 아니다. 공개 문구로 처리하면 된다.
9. 명세가 "프리셋에서 켠다"(110행)라고 했지만, 구현은 프리셋(`with_10hz_d1`)이 아니라 설정의 `lsb_components`로 켠다(`c2.py:2604-2607`, `run_v5.py:207-215`). 뜻은 같다.
10. 도구 표시 가운데 오탐인 것
    - placeholder_scan 9건은 모두 LaTeX 첨자 `{B}`·`{B3}`·`{READY}`와 사건 틀 `<leg>`·`<j>`다.
    - ref_check `ref_missing` 22건은 미추적 폴더 안의 bare 이름이다. 22건 모두 디스크에 있다.
    - gate_scan의 `tag_single_compare` 2건(`ed6_key_lists.py:125` 설정명 "V0", `ed6_probe_share.py:162` PROBE_TAG)과 `all_without_count_guard` 1건은 판정에 영향이 없다.
11. b1off 40줄에서 `extend_bound_check.rule_revision`·`spec_edition`이 10줄 없다. 이 10줄은 S1·S5 헤드 전용 줄이고, 6.1의 "None이면 2·3번 보지 않음"에 해당한다.
12. V0 기준 `v5/main.jsonl`은 `.git/info/exclude`로 미추적이다. sha 9ad74990은 판 5 문서와 `jp3_fixed_inputs.py`에 고정되어 있어 이어받는다.

## 규칙↔도구 대조표 (요약, ac3c25a7)

| 항목 | 명세 | 구현 | 판단 |
|---|---|---|---|
| A(i) N_trig / D_trig / η / s_wA / Δu / u_cap / N_cap | 10 / 0.5 mm / 0.25 / 0.4 mm / 0.2 / 1.05 / 50 (3.1) | `lock_start_b.py:167-179` 같음, E3 = 3읽기 평균(446-452) | 같음 |
| A(ii) κ, N_lock, ψ, β, V_line×0.5, L0r, β_hose, p_cr, band, e, void β | 3.2 | 185-212행 같음(band 16/13.328 kN) | 같음 |
| A(ii) 끝 Δs 목격 | E3 1.0 mm | 단일 읽기(892-896) | **다름(M-1)** |
| 로드 목격 | max(3 bar, 0.5(p_open−p_r0)) | 877-878, 897 | 같음 |
| B3 배율 ≤ 1, 가장 빠른 다리 셈, 명령 전 검사, 0.065, 35 kN, N_B3 2 | 3.3 | `c2.py:10250-10289`, `lock_start_b.py:998-1008`, 231-246 | 같음 |
| B3 끝 사유 | 5개 | 7개 | **다름(M-3)** |
| 봉인 구성 | {A_i, A_ii, B3}, B1 꺼짐 | `run_v5.py:182-186` `LSB_COMPONENTS_SEALED` | 같음 |
| 감도 4설정 | c_v 0.005/0.04, vol 0.5/1.5 | `run_v5.py:193-194` | 같음 |
| 태그·기저 | `_LSB` → `_K1` → `_LAS` 순으로 떼기 | `v5_options.py:771-780`(`_TCL`을 먼저 뗌) | 같음 |
| A·B 꺼짐 줄의 `lsb_components` | [] 또는 키 없음(미정) | 키 없음 | 문면 확정 필요(M-5) |
| P-pred | α 0.10, 20000×10, seed 20261125, b4 B안 | `jp3_12b_ppred.py:62-67, 237-263` | 같음(가장자리 차는 기록 5) |
| 키 파일 sha·줄 수·판정 행 | 70f4bb6d 184/104/80, 75413549 216/56/160, 4e80e69b 192/192/0 | 재계산 같음 | 같음 |
| j9_main 판정 행 200(R12 160·R14 10·R15 10·R16 20, 설정마다 40) | 6.2 | 판 5 j9_main `head_only_declared`로 재계산 같음 | 같음 |
| 감도 ∪ (가) = j9_main VBJ 100키, 겹침 0, probe_seen 32 = D0 8키 × 4 | 6.2·6.3 | 재계산 같음(헤드 전용 표시 불일치 0) | 같음 |

## 재집계 표 (봉인 준비값, 결과값 아님)

| 항목 | 명세 값 | 재계산 | 판단 |
|---|---|---|---|
| 감도 줄 / 판정 행 / 헤드 전용 | 184 / 104 / 80 | 184 / 104 / 80 (설정마다 R12 18·R14 2·R15 2·R16 4) | 같음 |
| (가) 줄 / 판정 행 | 216 / 56 | 216 / 56 (설정마다 R12 14) | 같음 |
| (나) 줄 / 판정 행 / V0 통과 | 192 / 192 / 174 | 192 / 192 / 174 | 같음 |
| 인용 sha(probe jsonl, b1off jsonl, 판 5 j9_main, s50 csv, L1 키) | efbf5d23, cbdb4d28, 883a2538, 6170e240, eea8ed0d | 같음 | 같음 |
| 설계 폴더 SHA256SUMS 10개 | – | 해시 불일치 0, 빠진 파일 0 | 같음 |

## 확인 단계 미관측 여부 (T)
- (가) 216줄: 키는 판 5 j9_main VBJ 키와 같다(설계 의도). 감도 플랜트(c005·c04·v05·v15)로 돈 기록은 06_analysis 전체 스캔에서 0건이다. probe·D0 키와 겹침도 0이다.
- (나) 192줄: P1~P4 플랜트로 돈 기록은 0건이다. 옛 VB로 2줄이 돌았다(M-7).
- 12b seed 50~53
  - 예약 목록 `[25,80,81,90-93,95-99]`과 겹치지 않는다.
  - 06_analysis에서 `L2[|_]s5[0-3][|_]`(cdry_a1 제외)는 선정 출력 8파일에만 있다.
  - 05_tests의 4건은 다른 사례 토큰(`x0`·`ref`)을 쓴 합성 키다.
  - `seed_repeats` 0이다.

## 경로 2 넘김 누설 검사
- 사전: `06_analysis/02_control/j_p3_cause/ed6_design/ed6_p2_leak/p1_names_ed6.json`. 1006개 이름을 담았고, `build_names_ed6.py`로 만들었다.
  - ed6-impl ac3c25a7의 다음 파일 전체를 ast로 읽었다: lock_start_b, ed6_probe, ed6_probe_share, jp3_12b_ppred, ed6_key_lists, jp3_12b_plan, d0_plant_split
  - c2.py·run_v5.py는 bdb1a510 이후 추가된 줄만 넣었다.
  - 판 5 사전 `p1_names_e8.json`과 판 6 폴더·커밋·팔 이름을 더했다.
  - 앞 넘김 10개(ed5·e1·e8·4a7·4a7e1~e3·4a8·4a8e1·tjr12)에 나오는 이름은 뺐다.
- 결과
  - 허용 없이 돌리면 48줄, 15개 이름이 걸린다. 모두 명세가 정의한 규칙 용어(설정 이름 VBL0·VBKL·VBKL0·LSL1·LSL4, 태그 `final_C4G2_P3W_LAS_K1_LSB`·`final_C4G2_P3W`·`_LSB`, 판정이 읽는 키 `lsb_components`·`A_ii`·`hydraulic_options`·`volume_scale`)이거나 LaTeX 기호(alpha·tau_C·tau_R)다.
  - 이 15개를 `--allow`로 주면 **누설 0**(종료 0)이다.
  - 대소문자 무시 검사는 23줄, 5개 이름이다(REVISION·ready·vbk0·JEFFREYS·ALPHA). 모두 일반 단어나 설정 VBK0이다.
  - **양성 대조**: scratchpad 사본에 2줄을 넣었다(`jp3_12b_ppred.py`, `_vector_ramp_outside_lock_start`, `probe_1bd405c8`, `a1a2b3`, `ac3c25a7`, `LSB_COMPONENTS_SEALED`). 2줄, 6개 이름이 모두 잡혔다.
- 저장 파일(같은 폴더 `SHA256SUMS`)
  - `build_names_ed6.py` 7aa1b6d1
  - `p1_names_ed6.json` 4435372e
  - `leak_p2_ed6_raw.json` dae7af2a
  - `leak_p2_ed6_allowed.json` e0f4046b
  - `leak_p2_ed6_allowed_ignorecase.json` e9c5e825
  - `leak_positive_control_ed6.json` 4d7340b5
  - `leak_run_ed6.json` 18fbb6c2(허용 목록과 사유)

## 봉인 커밋에 넣을 파일 (모두 지금 미추적, `-text`는 모두 걸려 있음)
1. `jp3_remedy_spec_v6.md`와 `.sha256`, `jp3_rev6_p2_handoff_ed6.md`와 `.sha256`. 둘 다 LF이고 BOM이 없다.
2. `ed6_design/`
   - `stats_v6/`(SUMS가 CRLF, 기록 7), `hydraulics_v6/`, `control_v6/`, `dynamics_v6/`
   - `probe_1bd405c8/`(`b1off_check/`, `stiffwarn_census/` 포함)
   - `keys/`(5개 json, SHA256SUMS 없음 → 만들 것을 권함)
   - `prelock_12a_755a15d8/`
   - `ed6_p2_leak/`
   - **`*.npz`는 `.gitignore:41`에 걸린다**: `prelock_12a_755a15d8/*_t4h/*.npz` 6개, `b1off_check/ed6_probe_a1a2b3_t4h/*.npz` 40개. 근거로 남기려면 `git add -f`(D0 npz도 이렇게 추적되어 있음)를 쓴다.
3. `prelaunch_j9/ed6_inputs/x11/` 9개 파일(`selection.json` 6687b2dc 포함)
4. `j9_runs/1bd405c8/ed6_probe_a1/`: jsonl이 86 MB이고 t4h npz는 ignore된다. 커밋하거나 `1bd405c8/ed6_probe_a1_LOCAL_ONLY.SHA256SUMS`(606f8713 관례)로 처리할지 메인이 정한다. 명세는 jsonl sha를 인용한다.
5. 이미 추적됨: `ed5_d0_390f88a9/`, `ed5_j9fail_606f8713/`(SUMS에 없는 파일 4개는 기록), L1 키 파일, V0 격자 json

## 고칠 문장 목록 (봉인 전)
- 명세
  - 54-60행 본 행 표(probe 실행 결과, b1off, 12a 단축 실행), O6-5, O6-6·O6-7 신설, 58행(B-1·M-12)
  - 4절: 도구 커밋 단계 추가, 479행 범위(B-2)
  - 178·181행 E3 → 단일 읽기(M-1)
  - 204행과 Y-1의 출력 경로 순서 확정(M-2)
  - 235·254·278행의 B3 사유·범위·보호 방식(M-3)
  - 286행 VBL0(M-4), 299행(M-5), 6.1에 `lsb_settings`(M-6)
  - 506행(M-7), 488행(기록 3)
  - 6.4와 넘김 3.1에 selection 경로·sha(M-8)
  - 6.2·6.3 줄 누락 처리와 V0 실패 18줄(M-9), 6.5 key_presence 목록(M-10), P6-2(M-11)
  - 4절 2에 실제로 쓴 몫 규칙(M-13), 330행 날짜, 기록 2의 낡은 표기
  - 12절에 B-1·M-7·M-12·M-13 공개 추가
- 넘김: 3행 "개정 12", 3.1 selection 경로·sha. 기록 5의 가장자리 정의는 선택이다.

## 확인 필요
1. 격자 (나)에서 V0 실패 18줄(`v0_pass` false)을 J1~J11에서 판정 대상에 넣을지, 넣으면 "V0 대비 실패" 정의를 어떻게 볼지, 아니면 FAULT 0·J-P3만 볼지(control-expert·stats).
2. 12a 단축 실행(B-1) 결과를 누가 열었는지, 판 6 설계·개정 12에 썼는지. 공개 문구는 실제 행위대로 쓴다(control-expert·python-expert에게 확인).
3. 블라인드 건수 노출(M-12)의 Grep 패턴과 날짜. 공개 문구에 필요하다.
4. probe 출력 jsonl(86 MB)을 커밋할지, LOCAL_ONLY로 둘지.

## 위임 필요
- control-expert(명세·넘김 문안): 위 고칠 문장 목록 전부
- python-expert: `lock_start_b.py:236` docstring 수정(기록 6). 봉인 뒤 Y-5·Y-6·Y-10 도구 커밋과 단위 시험(B-2). 사례 재생 발동 수 고정(M-11을 고정 쪽으로 정할 때). 실행 커밋은 ac3c25a7의 제어기 blob을 그대로 둔다.
- stats-design-expert: `stats_v6/SHA256SUMS` LF 재작성(기록 7). 격자 V0 실패 18줄 처리(확인 필요 1).

## 메인 세션 권고
- 고친 판(개정 13)을 짧게 재감사한다: 문장 대조, handoff_leak 재실행(사전 재사용), placeholder·ref 재확인.
- 봉인 커밋 전에 `git status --ignored -- 06_analysis/02_control/j_p3_cause`로 npz·대용량 파일이 빠지지 않는지 본다.

## 검사하지 못한 것
- 판정 도구(Y-5·Y-6·Y-10 연결)는 아직 없어서 E축 코드 추적을 하지 못했다. 봉인 뒤 도구 커밋 감사에서 본다.
- 구현 시험을 실행하지 않았다(P6-4 junit_skips 대상 없음). 시뮬레이션은 돌리지 않았다.
- 명세가 미추적이라 timeline(T) 도구로 개정 시각을 git 근거로 볼 수 없었다. probe 전 규칙 고정은 도구 커밋 시각(ff995a89 23:17, 1bd405c8 23:28 < probe 23:48)으로 대신 확인했다.
- 블라인드 cdry_a1 안의 seed 충돌은 선정 도구가 대신 쓴 판 5 키 목록으로만 확인됐다.

## 실행한 검증
- 인터프리터: python-dev `python.exe -I -B`(MKL_THREADING_LAYER=TBB). 실행은 PowerShell 도구에서 했다.
- 도구
  - placeholder_scan `--pattern-set both`: 9건, 모두 오탐
  - ref_check: missing 22는 bare 이름 오탐, untracked 19
  - seal_check: `seal_missing`·`rule_untracked` 각 2, 기준 판 일치
  - baseline_check sums ×10: 해시 불일치 0
  - gate_scan(ed6 도구 4개)
  - handoff_leak ×4(허용 없음 / 허용 / 대소문자 무시 / 양성 대조)
  - log_errors(probe·prelock): 0
  - key_presence(b1off jsonl·npz)
- git 조회: diff, show, check-attr, check-ignore, ls-files, status, log
- 즉석 스크립트(scratchpad `auditor-ed6seal`): 키 대조, 사례별 판정 행 수, 격자 키 전체 스캔, VB 적중 확인, 선정 출력 확인, 양성 대조 사본. 보고 전에 폴더째 지웠다.
- 만든 파일(유지): `ed6_design/ed6_p2_leak/` 8개(위 목록, SHA256SUMS 포함). 에이전트 메모리 `audit_pitfalls.md`·`MEMORY.md`에 한 항목을 더했다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v6.md 1ebdb308…, jp3_rev6_p2_handoff_ed6.md 8f160c83…, jp3_remedy_spec_v5.md fe6f5844…, jp3_remedy_spec_v5.md.sha256 0dd1676c…, jp3_rev6_p2_handoff_ed5.md 3ce9ecd8…, jp3_rev6_p2_handoff_ed5_e1.md b87d665c…, jp3_rev6_p2_handoff_ed5_e8.md ef33e619…, jp3_ed5_j9main_judgement_606f8713.md 9a54ffac…, sens_keys_v2.json 70f4bb6d…, confirm_a_keys_v2.json 75413549…, confirm_b_grid192.json 4e80e69b…, sens_keys.json c0130488…, confirm_a_keys.json 5fc2a8fb…, selection.json 6687b2dc…, ed6_probe.jsonl efbf5d23…, SHA256SUMS 157e1ccb…, stats_v6_summary.md f0e512a8…, 디렉터리 목록 동일, ~$ 임시 파일 없음) · 경고: 형제 항목 수정 시각만 변경 1건(ed6_design). 지시받은 새 폴더 `ed6_p2_leak/`를 만들어 생긴 변경이다.
- 사용한 스킬: 없음
