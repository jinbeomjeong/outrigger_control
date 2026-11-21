# 실행 전 좁은 재감사 5 (verif-protocol-auditor, 2026-11-21) — 원문 그대로

## 감사 요약
- 판정: **B(차단) 0 / M(중간) 2 / N(참고) 8.**
  - 단계 (1)~(4b)는 지금 시작할 수 있다. 사용자 승인은 이미 받았다.
  - 단계 (5) t8은 **M-1(VBJ0 이벤트 줄의 ③ record 규칙 충돌)을 정오 한 줄로 정한 뒤** 판정 도구를 돌린다. 실행 자체는 막지 않는다.
  - M-2(78fd5d2d 시험 근거가 저장소에 없음)는 판정서 전에 보완한다.
  - (6)·(7)은 바뀐 것이 없다. 지난 감사 결론 그대로 실행할 수 있다.
- 대상: 좁은 재감사 5, 시점 실행 전.
  - 실행 커밋: worktree `z4369-jp3` `78fd5d2d03e40ac7d9143429f602b58255c762fc`(locked, `git status --porcelain` 빈 출력, 부모 fa997f4c).
  - master: `36e121b4`.
- 기준 문서(sha 앞 8자리):
  - 앞 판: 지난 감사와 같다(판 4a `8be9de22` … 4a-6 `ae49bf4e`).
  - 4a-7 `364e2136`, 정오 1 `c6eac886`, 정오 2 `e9cf5e31`: 모두 추적되고, raw 해시가 봉인과 같다.
  - 고정 목록: `FIXED_INPUTS_78fd5d2d.SHA256SUMS` `2183fdc9`.
- 본 결과:
  - `j9_runs/fa997f4c/t8_a1/j9_t8.jsonl`: `key_presence`로 키가 있는지만 셌다(값 비출력). 필터로 쓴 것은 설정·사례 이름이다.
  - `prelaunch_j9/evidence_precheck_fa997f4c/precheck_fa997f4c.json`: 건수·이름만 있는 보고다.
  - 판정 값과 판정 보고는 열지 않았다.

## 볼 것별 결과

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| (1) | 4a-7 1절 t8 줄 규칙과 빈 집합 | 구현 일치. 표와 일반 문장 사이의 충돌 1건은 M-1 | `jp3_tjr_judge.py` `t8_line_problems`. 선언 줄: record·①·② 있으면 결함. 이벤트 VBH·VBJ: rev 5와 정체성(rev 5 record가 있을 때만), ② > 0, VBH ① = 0, VBJ ① = ②. VBJ0: ① = ② > 0. VB: record 필수, 판정 불가 사유에 더해짐. `t8_split_problems`: 설정마다 (18, 4)가 아니면 판정 불가. 줄이 없으면 (0, 0)이 되어 판정 불가(E축 적합). 증거 키가 없으면 결함. 선언 판별은 T4h meta → 줄 → `verdict_cases` steady 경로 순서다(`jp3_baseline_compare.is_head_only_line`, `j_p3_inputs.harness_head_only_declared`). fa997f4c t8 출력에는 네 설정 모두 22줄에 `head_only_declared`·증거 2키·`job.case`가 있다(key_presence 4/4). 그래서 판별할 수 있다 |
| (2) | 4a-7 2절과 정오 2 4절 재실행 대조 | 적합 | `jp3_rerun_match.py`. `cases_ae`는 짝·행별로 64자 해시, P4-3a 합계, relock, P4-4 두 키, P4-9 합계, P4-2 세 수, 순 힘 초과 행, 상태, `tool:baseline_compare`를 본다. `casef`는 15행 해시, VB harness 해시, F-A·F-B·F-E 상태(부분 함수로 다시 판정, 고정 grid sha 확인), 상태, `tool:case_f`를 본다. 양쪽 이름 집합이 다르면 종료 2, 값이 다르면 1이다. 보고에는 이름(`compared`·`differing`·`one_side_only`)만 남는다. 명령 파일은 `--old`에 fa997f4c 하나만 준다. step4a는 compare 직후, step4b는 case-f 직후에 대조한다. 0이 아니면 `Invoke-Judge`로 멈추고, 1이면 `Read-PreviousStops`가 재시도를 거부한다 |
| (3) | 정오 1 9절·정오 2 3절 P4 증거 적용 범위 | 적합 | t12: `_check_lines`가 `v5_setting` ∈ VBJ·LSJ1~4 줄에 `judged_line_evidence_problems`를 건다. r79 줄은 `level`이 있어 이벤트로 보고 ① = ② > 0을 요구한다. VBJ0 기준 줄은 B2만 본다. `baseline_compare`: `JUDGED_SETTINGS` 행에만 건다(T4h meta로 판별). case-f: F-E 행에 건다. `records`(T-JR-13 재생, T-JR-15)와 Chrono 경로는 diff에 없어 바뀌지 않았다 |
| (4) | 정오 2 1·2절과 경로 1 기록 정의 | 일치 | `two_pressure.py:2657-2685` `_hold_trace_row`: 잠김(lock·hold)이면 `used = model_Pa`, `model_bound_Pa = model_Pa`로 같은 목록이다(열린 구간 없으면 둘 다 NaN). `ext`·`carry_ext`이면 `used = extend_Pa`, `ext_bound_Pa = extend_Pa`. `carry_ret`이면 `max(extend_Pa, 수축 이동 모델)`. 그래서 정오 2 1절의 "1 Pa 넘게 다르면 record_defect"는 경로 1 기록에서는 생기지 않는 검사다 |
| (5) | `Assert-SimulationPathsUnchanged` | 적합(정오 2 4절보다 엄격) | `common.ps1:380-403`: 허용은 판정·대조 도구 4개와 `05_tests/` 접두뿐이다. 나머지가 하나라도 바뀌면 종료 3이고 "ask the user"를 띄운다. step1 `:10`에서 `Initialize-Step`(커밋·트리·고정 입력 확인) 바로 뒤, 첫 실행(base-judge) 전에 돈다. `git diff --stat`은 `logs/git_diff_stat_fa997f4c.txt`에 남는다. 실제 diff 9파일은 모두 허용 목록 안이다 |
| (6) | 실행 전 도구 | 아래 | |

- `seal_check --sums --rev 36e121b4 --check-tracked`: 12판 raw 일치. error 0, warning 1(`seal_missing` 4a-1), info 18. 지난번의 4a-6 `seal_name_mismatch`는 해소됐다(`.sha256` `7f256ee5`).
- `baseline_check sums FIXED_INPUTS_78fd5d2d --base repo-root --rev 36e121b4`: 72줄, mismatch 0, missing 0, CRLF 0.
  - `cited_untracked` 15와 `cited_ignored` 1은 resume_k1 저장 파일·identity sidecar와 `v5/main.jsonl`(`.git/info/exclude`)이다. 4a-3 5.4가 허용하는 git 밖 고정이다.
  - `sums_unlisted` 8은 N-6이다.
- `placeholder_scan run_steps\*.ps1 --pattern-set both`: 0.
- `ps1_lint` 9개: 0.
- `gate_scan`(도구 4개): warning 11. 모두 읽고 판단했다.
  - `tag_single_compare` 8: 고정 설정 이름 비교라 거짓 양성이다.
  - `missing_key_default_pass` `jp3_rerun_match.py:255`: 빈 inputs이면 루프 뒤 `Missing`(종료 2)이라 거짓 양성이다.
  - `jp3_tjr_judge.py:933-936` `dg3_input_problems`: `results`가 없으면 다른 설정 검사를 건너뛴다. 다만 t12의 135짝·L2 1 검사가 뒤에서 판정 불가로 잡는다(N-3).
  - `row_value_path_no_base` `jp3_rerun_match.py:256`: case-f 보고 `inputs[].path`로 grid를 연다. 명령 파일이 절대경로를 주고 sha도 확인하므로 실해는 없다(N-4).
  - `missing_key_default` `:313`(info): 설정이 없으면 (0, 0)이 되어 판정 불가로 가는 안전한 쪽이다.
- `log_errors`: 새 실행 로그가 없어 생략했다.
- `junit_skips`: 78fd5d2d 근거 junit이 저장소에 없어 돌리지 못했다(M-2).

## 발견 사항

### [M][R] M-1: VBJ0 이벤트 줄의 ③ record — 4a-7 1.2절 표와 일반 결함 문장이 다르다. 도구는 표를 따른다
- 근거:
  - 4a-7 1.2절 표의 VBJ0 이벤트 행은 "③ 꺼짐이라 정체성 해당 없음. ① = ② > 0"이고 record 요구가 없다.
  - 같은 절 결함 목록 첫 줄은 "선언 없는(이벤트 경로) 줄에서 ② = 0이거나 **③ record가 없다**" → `setting_defect`로, 설정을 가리지 않는다.
  - 도구 `t8_line_problems`는 record를 VBH·VBJ(rev 5)와 VB에만 요구하고 VBJ0에는 요구하지 않는다.
  - fa997f4c t8 출력의 키 개수(값 비출력): VBJ0 R12·R14·R15·R16 각 1줄은 `hydraulics_record.extend_bound_check`가 0/1이다. VB·VBH·VBJ의 같은 4잡은 모두 1/1이다.
- 실패 시나리오: 결함 문장을 글자대로 읽으면 VBJ0 이벤트 4줄이 `setting_defect`이고, T-JR-11은 판정 불가다. 도구 해석(표)대로면 판정이 진행된다. 같은 규칙을 경로 2나 판정서가 문장대로 읽으면 두 결론이 갈린다.
- 권장 조치(control-expert 정오 한 줄 → 메인): "③ record 요구는 ③을 켠 설정(VBH·VBJ·VB)에만 적용한다. VBJ0 이벤트 줄은 record가 없는 것이 정상이다." 결과 전이고 기대값은 바뀌지 않는다. 단계 (5) 판정 전에 둔다. 도구 변경은 필요 없다.

### [M][E] M-2: 실행 커밋 78fd5d2d의 시험 근거(junit)가 저장소에 없다
- 근거:
  - `j_p3_cause/j4a_remedy_78fd5d2d*` 폴더가 없다(Glob 0).
  - `FIXED_INPUTS_78fd5d2d`에도 78fd5d2d 근거 SUMS가 없다. 근거 SUMS는 fa997f4c까지만 있다(72줄 중 50·51행).
  - "7,747 통과·기존 실패 2·gap 기존 1"은 보고로만 받았다. `junit_skips`로 skip·xfail을 확인하지 못했다.
- 실패 시나리오: 판정서가 "T-JR-01·판정 도구 시험 통과"를 인용할 근거 파일이 없다.
- 권장 조치(메인·python-expert): 앞 회차처럼 `j4a_remedy_78fd5d2d/`(junit_full·main2·gap, 요약, 다이제스트, SHA256SUMS)를 저장·커밋하고, 판정 후 감사에서 `junit_skips`로 확인한다. 실행 시작을 막지는 않는다(실행 코드는 바뀌지 않음, 다이제스트 동일 보고).

### [N]
- N-1 [I] 기준선 `baseline_221456d/j9_cases.jsonl` 5행에 `relock_step_over_1bar_count` 키가 없다(도구 보완 사실). **판정 영향은 없다.**
  - P4-3a 재잠김은 새 행에서만 읽는다(`jp3_baseline_compare.judged_key_problems`, `hydraulics = new`).
  - P4-4가 기준선과 비교하는 것은 `p1_retract_seed_count`·`p1_retract_seed_step_max_bar`뿐이다.
  - rerun_match `cases_ae`도 두 시도의 새 행만 읽는다.
  - 판정서에는 "기준선에는 그 키가 없다(221456d 코드 시점)"를 각주로 적는다.
- N-2 [R] 정오 2 3절 "436.9 본 실행(j9_main)의 J-P3 판정 입력도 같은 규칙"은 `j_p3_inputs.py`(경로 1 j9_main 판정)에 아직 들어가지 않았다(diff에 없음). 이번 단계 (1)~(7) 밖이므로 j9_main 실행 전 감사에서 본다.
- N-3 [E] `dg3_input_problems`(`jp3_tjr_judge.py:933-936`)는 `results`가 없는 파일을 통과시킨다. t12가 135짝 불일치로 판정 불가를 내므로 결론에는 영향이 없다. 정리 후보다.
- N-4 [I] rerun_match `casef`는 case-f 보고 `inputs[].path`의 grid를 연다(sha 확인함). 경로는 명령 파일의 절대경로(`Get-FixedPath`)라 작업 폴더와 무관하다.
- N-5 [R] 증거 사전 대조(정오 2 4절): 판정 행 10줄 모두 규칙에 맞고 어긋남은 0이다(`precheck_fa997f4c.json`, 이름·건수만). case F의 판별 근거는 사전 대조가 `t4h_meta`, case-f 도구가 사례 표(`is_head_only_line(row, None)`)로 서로 다르다. R12는 어느 쪽으로도 이벤트라 결과가 같다.
- N-6 [S] `baseline_check sums --base repo-root`가 SUMS 폴더(`prelaunch_j9`)의 목록 밖 파일 8개(옛 목록·감사·P1 목록 등)를 `sums_unlisted`로 낸다. 저장소 전역 목록에서는 의미 없는 검사다. 선택 개선 후보: repo-root 모드에서는 unlisted를 끄거나 info로 낮춘다(`위임 필요(python-expert): tools/verif 후보`).
- N-7 [R] 4a-7 2.2절의 "판정 전 `git diff --stat` 기록"은 step1의 `logs/`에 남는다. 단계 (2)~(7)은 `Assert-RunCommit`이 같은 커밋을 보장하므로 따로 기록하지 않는다. 충분하다.
- N-8 [I] 다이제스트·diff: `git diff --stat fa997f4c 78fd5d2d`는 9파일이고, 03_src·하네스·실행기는 바뀌지 않았다. 다이제스트 동일은 보고값이다(M-2와 함께 근거 폴더에 저장 권장).

## 확인 필요
1. M-1: VBJ0 이벤트 줄의 ③ record 요구를 표(요구 없음)로 읽을지 정오로 확정한다. 단계 (5) 판정 전이다.

## 위임 필요
- control-expert: M-1 정오 문안(결과 전, 한 줄).
- python-expert(선택): N-3 정리, N-6 `baseline_check` repo-root unlisted 처리.

## 메인 세션 권고
- 단계 (1)~(4b)를 시작한다(사용자 승인됨).
- 단계 (5) 전에 M-1 정오를 저장·커밋한다.
- 판정서 전에 M-2 근거 폴더를 저장하고, 판정 후 감사를 받는다.

## 검사하지 못한 것
- 78fd5d2d junit(M-2).
- 시험 코드 내용(H-2 (a)~(f), 시험 5파일).
- 명령 파일 실행 동작: 정적으로만 읽었다.

## 실행한 검증
- python-dev(`-I -B`, TBB): `seal_check`, `baseline_check sums --base repo-root`, `placeholder_scan --pattern-set both`, `ps1_lint`, `gate_scan`(도구 4개), `key_presence`(fa997f4c t8: 설정별 키 4개, 설정·사례별 `extend_bound_check`).
- git 조회: `log`, `status --porcelain`, `worktree list`, `diff --stat`/`diff fa997f4c 78fd5d2d`(판정 도구 4개).
- 읽은 코드: `two_pressure.py:2657-2716`, `j_p3_inputs.harness_head_only_declared`, `common.ps1:374-412`, step1·step4a.
- 최종 판정 직전에 worktree HEAD `78fd5d2d`가 깨끗한지 다시 확인했다.
- 만든 뒤 지운 파일: scratchpad `verif-prelaunch5\`(guard.json, seal.md). 폴더째 지웠고 Test-Path는 False다.
- 메모리: `audit_pitfalls.md`에 한 항목을 더했다(설정별 표 vs 일반 결함 문장).
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_addendum_4a1.md 4b122dd0…, jp3_remedy_spec_addendum_4a2.md 2f3e36bd…, jp3_remedy_spec_addendum_4a2.md.sha256 19063b36…, jp3_remedy_spec_addendum_4a3.md f001383a…, jp3_remedy_spec_addendum_4a3.md.sha256 3045bb46…, jp3_remedy_spec_addendum_4a4_erratum1.md 1ccbe526…, jp3_remedy_spec_addendum_4a4_erratum1.md.sha256 27255e69…, jp3_remedy_spec_addendum_4a4.md 67380b10…, jp3_remedy_spec_addendum_4a4.md.sha256 c50c5aac…, jp3_remedy_spec_addendum_4a5_erratum1.md a7a0c973…, jp3_remedy_spec_addendum_4a5_erratum1.md.sha256 5c0be4d7…, jp3_remedy_spec_addendum_4a5.md 562c4e9f…, jp3_remedy_spec_addendum_4a5.md.sha256 b45e407c…, jp3_remedy_spec_addendum_4a6.md ae49bf4e…, jp3_remedy_spec_addendum_4a6.md.sha256 7f256ee5…, jp3_remedy_spec_addendum_4a7_erratum1.md c6eac886…, jp3_remedy_spec_addendum_4a7_erratum1.md.sha256 7568a047…, jp3_remedy_spec_addendum_4a7_erratum2.md e9cf5e31…, jp3_remedy_spec_addendum_4a7_erratum2.md.sha256 01c692a2…, jp3_remedy_spec_addendum_4a7.md 364e2136…, jp3_remedy_spec_addendum_4a7.md.sha256 3c1fb375…, jp3_remedy_spec.md 8be9de22…, jp3_remedy_spec.md.sha256 174e6fb7…, audit_prelaunch.md e62bc724…, audit_prelaunch2.md 2da391b8…, audit_prelaunch3.md bbe7cf5b…, audit_prelaunch4.md 506d5a59…, FIXED_INPUTS_325b77a8.SHA256SUMS 5aeb5f96…, FIXED_INPUTS_78fd5d2d.SHA256SUMS 2183fdc9…, FIXED_INPUTS_b51ed6e1.SHA256SUMS ccebf70d…, FIXED_INPUTS_d84ba7bd.SHA256SUMS 00736c77…, FIXED_INPUTS_fa997f4c.SHA256SUMS 792f6bbe…, FIXED_INPUTS.SHA256SUMS f35fa862…, h10_reuse_rerun_t4h.SHA256SUMS 3d0ed49a…, h6_dg3_v4on_t4h.SHA256SUMS c426f518…, P1_OUTPUTS_b51ed6e1.SHA256SUMS 9f2db2e9…, P1_OUTPUTS_fa997f4c.SHA256SUMS dbdcd504…, README.md 7b6dd983…, evidence_precheck.py 9e5b7904…, precheck_fa997f4c.json 62470e7b…, SHA256SUMS 01439ffe…, common.ps1 840544bb…, step1_p1.ps1 50d95530…, step2_dry.ps1 03ae0674…, step3_fpath.ps1 623ef15d…, step4a_cases.ps1 da7e8b28…, step4b_casef.ps1 fad03187…, step5_t8.ps1 21c75381…, step6_dg3.ps1 70b4bf4f…, step7_records.ps1 0a6a9141…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음

---

## 메인 결정(2026-11-21)

- 차단 0 → 단계 (1)~(4b) 시작(사용자 승인 범위). M-1은 control-expert 정오 3 문안으로 단계 (5) 판정 전에 정하고, M-2는 python-expert가 `j4a_remedy_78fd5d2d/` 근거 폴더를 만들어 판정서 전에 커밋한다. N-6(baseline_check repo-root unlisted)·N-3은 선택 정리 후보로 남긴다.
