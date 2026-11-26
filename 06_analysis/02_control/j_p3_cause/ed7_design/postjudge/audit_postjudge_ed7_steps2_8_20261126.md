# 436.9 J-P3 판 7 단계 2~8 판정 후 감사 (verif-protocol-auditor, 2026-11-26)

## 감사 요약
- 본 결과(판정이 끝난 뒤 지시대로 열었다)
  - 판정 report 7개(`judge_60ebb4a4\*\*.json`): status, status_basis, 실패 항목과 detail(t_ready·t_back·gate 이름·WARN 이름), 단위 verdict, cluster, reproduction, count, J-P3·rev7_condition 요약, identity 수, code_identity, inputs sha
  - 실행 jsonl 7개(`j9_main`·`sens`·`confirm_g1`·`ed7_probe_d`·`ed7_t8`·`ed7_cases`·`ed7_probe_a2`)의 필드: `event_output`(gates·pass·t_ready_back_s·att_end_deg·pressure), `values`(t_first_ready_s·after_liftoff·attitude·pressure), `final_phase`, `events` 이름, `commands_sha256`, 정체성 필드
  - 그 밖에 연 것
    - V0 `v5/main.jsonl`의 같은 필드
    - 고정 표 `fixed_table_a2.json`의 verdict·commands_sha256·D 행 필드
    - 키 파일 2개(`judged`·`probe_seen`·`counted_for_k`·`head_only_declared`)
    - probe 6bfb2560 jsonl의 `commands_sha256`
    - `p51_record_compare.json`의 status
    - `.done`·`*.identity.json`·chain log·main_checks 기록
- 대상: 판 7 단계 2~8의 판정 7개
  - 대상 판정: l1ref, t8(P7-1), cases(P7-2), probe-repro(P7-3·P7-9), confirm(6.3), j9main(6.2 ①), sens(6.2 ②)
  - 판정 도구: T′ `60ebb4a4`, `jp3_ed7_judge.py`
  - 실행 커밋: C `8a2a52ce`
  - 시점: 판정 후
- 기준 문서
  - 봉인 명세 `jp3_remedy_spec_v7.md`: `10902ffd…`(`.sha256` 일치, `-text`, 도구 상수 `SPEC_V7_SHA256`와 일치)
  - 정오 1 `jp3_remedy_spec_v7_erratum1.md`: `74c49bda…`
  - 이어받은 판 6 명세 `jp3_remedy_spec_v6.md` 4절(320~401행), 6.1·6.2(414~510행), 11절(770~791행)
  - `v5_criteria.md`: 12절 1단계(227~237행), 11절(207~225행), J 표(55~65행)
  - 실행 전 감사 `audit_prerun_main_ed7_20261126.md`(`dcc6937a…`)
- **판정: 차단 0 / 판정서 확정 전 수정 2 / 기록 14.**
  - j9main(①)과 감도(②)의 `failed`는 규칙대로 확정이다.
    - 독립 재집계가 15·2·1과 군집 실패를 그대로 재현했다.
    - 재현 불일치·설정 결함·판정 불가는 0이다.
    - 실패 18건 모두 위상 산포 표지가 거짓이라 `v5_criteria` 12절의 "조건부"에는 해당하지 않는다.
  - 판 7은 합격이 아니다. 다만 J-P3 경로 2는 아직 판정하지 않았고, 12a·12b는 미실행이다(M-1, 9절).

## 발견 사항 (심각도순)

### [판정서 확정 전 수정][R·I] M-1 판 7 J-P3 경로 2가 실행되지 않았다. 판정서는 J-P3를 "두 경로 판정"으로 적을 수 없다
- 근거
  - 봉인 명세 6.1 657행: "J-P3: 판 6 6.1 꼴에 ③ rev 7(3.5)을 쓴다. 두 경로로 판정한다(11절)."
  - 11절 1018행: "J-P3(③ rev 7)와 T-JR-12b는 판 6과 같이 경로 2 범위다. 넘김 문서는 봉인 뒤 control-expert가 쓴다."
  - 판 6 11절 771~774행은 경로 2 범위를 정했다: j9_main J-P3, 12b, 12a, 감도 행·확인 단계의 J-P3. 판 6 4절 5(390행)에는 구현 확인 단계의 "J-P3 두 경로"도 있다.
  - 정오 1 「경로 2에 넘길 정의 문장」(275~282행)은 넘김 문서에 [정의 E7-P2-1·2]를 옮기라고 정했다.
  - 실측: `j_p3_cause` 최상위 파일 목록(비재귀)에 판 7 넘김(`jp3_rev7_p2_handoff_*`)이 없다.
    - `ed7_p2_*` 결과 폴더가 없다.
    - `git worktree list`에 판 7 경로 2 worktree가 없다.
    - `ed7_design` md Grep에서 `E7-P2-1`은 정오·감사 문서에만 나온다.
- 영향: 판 7 결론은 바뀌지 않는다.
  - 경로 1 J-P3는 모든 판정에서 통과다: j9main 200행·조건 읽기 2791·침범 0, 감도 104·1414·0, confirm 171·2372·0, cases 10·158·0.
  - 실패는 J1~J11과 군집 규칙에서 났다. 이것은 하네스 단독이고 경로 1 몫이다(판 6 11절 775행).
  - 경로 2가 할 수 있는 일은 J-P3 실패를 더하는 것뿐이다. 판 6 판정서 24·325행도 같은 논리를 썼다.
  - 그러나 판정서의 J-P3 칸을 "통과(두 경로)"로 쓰면 사실과 다르다.
- 권장 조치(사용자 결정): 둘 중 하나를 정한다.
  - (가) 판 6처럼 경로 2를 실행한다. 넘김 문서는 control-expert가 쓰고 `handoff_leak --shared`에 원판 `jp3_remedy_spec.md`를 포함한다. 실행은 경로 1을 보지 않은 에이전트가 한다.
  - (나) 판정서에 "J-P3 경로 1 통과, 경로 2 미실행(불합격이 경로 1 몫에서 확정되어 생략)"으로 적는다.

### [판정서 확정 전 수정][I] M-2 판정 출력·실행 출력은 아직 미추적이고, 원격 한도(10⁸ B)를 넘는 파일이 4개다
- 근거
  - `git status --porcelain`: `?? j9_runs/8a2a52ce/`, `?? …/judge_60ebb4a4/`, `?? ed7_design/ed7_j9fail_8a2a52ce/`
  - 속성은 `text: unset`(-text)이고 ignore에는 걸리지 않는다(`check-ignore` 종료 1).
  - 10⁸ B 초과 파일
    - `l1ref_a1\L1_VBM.json` 205,047,146
    - `L1a_VBM.json` 125,654,550
    - `L1_VBM.json.partial.jsonl` 120,913,189
    - `sens_a1\sens.jsonl` 101,212,673
- 실패 시나리오: 판정서와 함께 그대로 커밋하면 push가 거부된다. 또는 큰 파일만 빠진 채 SUMS가 그 파일을 가리키는 상태가 된다.
- 권장 조치(메인): 판정서 커밋 전에 `tools\integrity\large_outputs.py <폴더> --backup <백업>`을 건식으로 돌린 뒤 `--apply`한다. 판 6처럼 `LOCAL_ONLY.SHA256SUMS`를 두고 `git status --ignored`로 인용 파일을 확인한다.

### [기록][C] R-1 독립 재집계가 판정과 모두 일치한다(아래 재집계 표)
- 방법
  - 판정 도구 모듈을 import하지 않는 python-dev 스크립트로 셌다.
  - 대상: VB 대 V0, LS1~4 대 VB, 감도 460단위 대 V0
  - 정의 출처
    - `v5_criteria.md` J 표 55~65행의 J1~J10(J11은 대체 다리 n_late)
    - 판 6 6.2 읽기 (1)·(2)(439~441행)
    - 판 7 6.1 J7 새 비교(662~666행): 이름 집합(숫자 마디 제거)과 (이름, 다리, 사유) 집합 차
    - 감도 강성 예외 단독 조건(판 6 489~494행, 판 7 698행, 감도 10설정)
  - 군집 규칙은 6.2 680~682·691행을 따라 미관측 실패와 고정 표 실패를 합해 셌다.
- 차이: 도구 `fallback_triples`(`jp3_ed7_rules.py` 82~97행)는 다리마다 첫 사유만 쓴다. 이 재집계는 다리의 모든 사유를 쓴다. 이번 자료에서는 대체(fallback) 사건이 없어 결과 차이가 0이다(감사 기록용).

### [기록][R] R-2 판정 명령 인자는 맞다
- l1ref·t8·cases·probe-repro·confirm
  - `judge_probe_stop.ps1`·`judge_confirm_stop.ps1`는 실행 전 감사 초안(213~244행)과 인자·경로가 같다.
  - `--grid-root`는 메인 checkout이다. confirm `v0_missing` 0으로 확인했다.
- j9main·sens는 초안이 없었다(실행 전 감사 「검사하지 못한 것」 297행). 도구 docstring 84~88행·parser 1594~1611행과 대조했고 맞다.
  - j9main: `--edition 7`(choices (7,) 필수), `--rows`, `--v0`, `--step-done`, `--out`
  - sens: `--keys …\keys_seal_b46bdf8f\sens_keys_ed7.json`, `--fixed-table`
- 고정 입력 sha는 report `inputs`에 `pinned: true`로 남았고 `PINNED_SHA256`(151~160행)과 같다: V0 `9ad74990`, 고정 표 `f7754a69`, 감도 키 `be930b75`, G1 키 `684054ab`, D 짝 `4e80e69b`, 참조 probe `1107b309`, probe 키 `189dbb13`.
- 실행은 dynamics-dev `python.exe -I -B` 직접 호출, cwd T′, `NUMBA_CACHE_DIR`는 TEMP였다. `--run-commit` 재정의는 쓰지 않았고 report `run_commit` = C다(R-14).

### [기록][R] R-3 상태 순서와 재현 우선은 규칙과 같다
- `status_of`(283~291행)의 순서: failures > setting_defects > not_judgeable > pass. 명세 6.1 661행과 같다.
- 재현 대조를 집계보다 먼저 하고, 불일치면 집계 없이 `setting_defect`로 끝낸다(6.1 672행).
  - sens: 939~942행
  - confirm: D 24줄, 1165~1170행
  - probe-repro: 1475~1478행(정오 1-17·결정 15)
- 이번 재현 불일치: sens 40단위 0, D 24줄 0, probe 114줄 0, 고정 표 40+24 0.
- 상태 결합에서 j9main·sens의 setting_defects·not_judgeable는 비어 있다. 실패가 결함·판정 불가를 가린 경우가 아니다.

### [기록][R] R-4 "고정 표 본 단위는 실패만 더한다"와 "D VBM 실패는 G1 k=3에 더한다"가 맞게 적용됐다
- 감도
  - 고정 표 40단위는 통과 39·실패 1(`VBMslow S7 e0.001`, J3)이다.
  - `cluster_judgement_with_fixed`(`jp3_ed7_rules.py` 254~283행)는 실패 단위만 `failed_phases`에 더하고(270~271행), 통과 단위는 더하지 않는다.
  - 이번 실행에서 probe 단위의 재실행 verdict는 재현 대조에만 쓰였고 세지 않았다(`sens_outcome` 958~974행).
  - 결과: `VBMslow S7`은 미관측 `e0`(J3, t_ready 76.4 → 102.9)과 고정 `e0.001`을 합해 실패 위상 2개가 되어 실패한다(6.2 681행).
  - 단독 실패 (설정, 행)은 `VBMslow R12 top-FL-Fs0` 하나로 k = 4 이하다.
  - 고정 표만으로는 단독 1이라 실패가 아니었다. 봉인 조건(692행)과 모순이 없다.
- 확인 단계
  - 고정 표 D 24행 가운데 `is_counted_for_k`인 것은 VBM 12행이고, 그중 V0 실패는 0이다. 그래서 더할 값은 0이다(`d_vbm_fixed_failures` 1140~1143행, report `d_fixed_vbm_failures: []`).
  - G1 기회 168줄의 실패 3에 0을 더해 total = 3 = k다. `total > k`일 때만 실패이므로(`confirmation_judgement` 315행) 통과다. 명세 6.3 736행 "k = 3 이하"와 맞다.

### [기록][E·C] R-5 확인 단계는 경계(total = k)에서 통과했다. 예측 문장 x는 틀렸다
- G1에서 `event_output.pass`가 참이 아닌 줄은 3줄이고 모두 `counted_for_k` 참이다(독립 재집계 3, retract WARN 0).
  - `R12_bottom-FR-Fs0-o0.0-RE1bF-ready`: `U832_pair_union`
  - `R12_bottom-FL-Fs4-o0.0-RE1bF-ready`: `U832_pair_union`. 봉인 6.3 743~744행·12절 1037·1049행이 공개한 "FL-Fs4 o0.0 위험" 줄이다.
  - `R12_bottom-FR-Fs8-o0.0-FS24-ready`: `end_att`, 끝 단계 level
- P7-5 예측(6.3 748행, 기록용)과의 대조. 판정서에 적는다.
  - x = 0.24~1.08줄 → 관측 3: 틀림
  - FAULT 0 → 0: 맞음
  - J-P3 침범 0 → 0: 맞음
  - 교착 서명 y ≤ 3 → `stall_signature_lines` 0: 맞음

### [기록][I] R-6 정체성은 모두 맞다
- 7개 report의 `code_identity`
  - checkout `…\.claude\worktrees\ed7-judge`, head `60ebb4a4…`, `is_clean` true
  - 감사 끝에 다시 본 T′: HEAD 같음, `status --porcelain --untracked-files=all` 0항목
- 7개 report의 `inputs.rows.run_commit` = `8a2a52ce…`이고 `step_done_sha256`이 현재 `.done` sha와 같다.
- `.done` 7개
  - `exit_code` 0, `commit` = C
  - `identity_start`·`identity_end`의 head = C, `is_clean` true
  - `folder` = 각 `_a1`
- 원시 줄 정체성(독립 스캔)
  - 태그
    - ③ 켬 줄은 모두 `final_C4G2_P3X_LAS_K1_LSB`다.
    - t8 VBM0 22줄은 `final_C4G2_LAS_K1_LSB`다. t8 report `controller_tags`가 기대와 같다.
  - `lsb_components`는 모든 줄이 {A_i, A_ib, A_ii, B3}다.
  - ③ 기록이 있는 줄은 모두 `(rule_revision 7, spec_edition "10902ffd")`다.
    - j9main 200, sens 260, g1 171, D 24, t8 4, cases 10, probe 78
    - 기록이 없는 줄은 head-only 선언이거나 ③ 끔이다(j9main 188, sens 200, t8 40, probe 36). 판정 도구 `identity_defects`는 7개 report 모두 0이다.
  - `ED7_SPEC_EDITION` = `SPEC_V7_SHA256[:8]`(129행)이고, 상수는 봉인 sha와 같다(seal_check `--const` 종료 0).
- l1ref: 4 run(167·167·102·102줄) 모두 `identity_problems` 0이고, `identity_sources`가 남았다.

### [기록][E] R-7 통과 판정들은 빈 집합으로 통과하지 않았다

| 판정 | 판정 대상 수(기대) | 근거 |
|---|---|---|
| t8 | 22쌍(22 job × VBM/VBM0 = 44줄), 대체 있는 쌍 0 | 독립: 대체 없는 22쌍의 `commands_sha256`이 모두 같음 |
| cases | 10줄(`CASE_ROWS` 10), J-P3 판정 10, 조건 읽기 158 | 원시 10줄, 오류 0 |
| probe-repro | 114줄 대조(기대 114), 고정 표 40단위 + D 24행 | 독립: 6bfb2560 a2와 job별 해시 114/114 같음 |
| confirm | D 24(기대 24), G1 171(키 171), 기회 168, J-P3 171(키 `expected_j_p3_judged_rows` 171), 조건 읽기 2372 | 독립: D 해시 다중집합이 고정 표와 같음, G1 key 대응 누락 0 |
| j9main | 388줄, VB 100쌍·LS 4×72쌍, 기준 짝 없음 0, J-P3 200(head-only 아님 200 = 기대 200, 정오 1-11) | 독립 스캔 `head_only_declared` 거짓 200 |
| sens | 460줄 = 키 460, 단위 460(probe 40·미관측 144·기록 276), J-P3 104(키 judged ∧ head-only 아님 104) | 키 파일 judged·probe_seen 직접 셈 |
| l1ref | 538줄(4 run) | `lines` 0이면 판정 불가(1570~1571행) |

- 오류 줄: 7개 jsonl 모두 0(독립 스캔). M-2(a) `key_presence --key commands_sha256` 기록 3개가 모두 "발견 사항 없음"이다(t8·cases 54행, G1 171행, j9main·sens 848행).

### [기록][T] R-8 시간 순서는 맞다
- 커밋
  - 봉인 e241638d: 11-25 15:25
  - C: 16:33
  - T: 17:20
  - T′: 19:05
  - 정오 1 265dc641: 11-26 00:14
  - run prep eba3d0f5: 02:22:24
- 러너와 판정의 시각(chain log)
  - 러너 시작 02:22:42
  - probe 정지 03:56:39 → 판정 03:58:48~52
  - confirm 실행 10:30:16~10:58:05 → 판정 11:07:46
  - j9main 시작 11:11:33, sens 끝 12:53:21 → 판정 12:58:14·12:58:22, 판정 SUMS 12:58:42
- 판정 report의 시각 근거는 mtime뿐이다(미추적, timeline `mtime_only_basis` 4). chain log와 identity 시작 시각(예: j9main `11:11:36`)이 같은 순서를 받친다.
- 규칙 파일은 결과 뒤에 바뀌지 않았다(seal_check 일치, 새 정오 파일 없음).

### [기록][R] R-9 j9main VB 실패 15 중 14가 `WARN_PROBE_STIFFNESS_OUT_OF_RANGE`(J7)이다. 이 경고의 예외는 j9main에 적용되지 않는 것이 규칙이다
- 실패 줄
  - R12 top-FL/FR/RL/RR-Fs8의 두 위상(8)
  - R14 두 위상(2)
  - R7 eps 0~0.003(4)
  - 나머지 1: S7 eps 0.002 J3(t_ready 77.0 → 100.7, 한계 100 s)
- 규칙
  - 판 6 6.2 488행: "적용하지 않는 것: `VBL`·`VBL0`·`LSL1~4`(j9_main) … J7은 지금 문면 그대로 판정한다"
  - 판 7 6.2 698행: 적용 이름 목록 = 판정 4설정 + 기록 6설정
- 도구의 `_j9main_items`는 예외를 부르지 않는다(805~839행). 감도에서는 예외가 79단위에 쓰였다.
- 강성 경고를 빼도 S7 J3과 LS4 L-a·L-b가 남는다. 결론은 같다.

### [기록][R] R-10 j9main 판정 실패 직후, 같은 스크립트에서 sens를 이어 판정했다
- `judge_sens_stop.ps1`은 j9main과 sens를 조건 없이 차례로 돈다. j9main 종료 1을 본 뒤 묻지 않고 sens를 판정했다.
- 판 6 4절 399~400행의 멈춤은 "다음으로 가지 않는다 / 재실행하지 않는다"이고, 대상은 다음 단계 실행이다. sens 실행은 판정 전에 이미 끝나 있었고(5a 허용), 판정 뒤 실행은 없었다. 러너는 `[pause] sens`이고 dg3는 시작하지 않았다. 규칙 위반은 아니다.
- 판정서에 "j9main·sens는 한 번에 판정했다"고 공개한다.

### [기록][E] R-11 `gate_scan` 경고 5건(jp3_ed7_judge·rules)은 이번 판정 결과에 영향이 없다
- `unit_verdicts` 697행 `by_unit.get(unit, [])`
  - 항목은 실패·기록일 때만 생긴다. 기준 짝 없음은 `no_reference` → `NotJudgeable`(922~923행)로 따로 처리된다.
  - 독립 재집계가 같은 통과 집합을 냈다.
- `judge_l1ref` 1559행: 빈 결과는 1570~1571행이 판정 불가로 보낸다.
- `step_output_problems` 231행과 `stall_record` 594행: `.done`의 `folder`가 절대 경로이고, T4h는 `locate_t4h`로 찾는다. 이 둘은 기록(교착 서명)용이다.
- `is_stall_signature_ed7` `all` 158행: 기록 전용 함수다.

### [기록][I] R-12 판정 뒤 SUMS 재대조가 파일로 남지 않았다. 감사가 다시 했고 일치한다
- main_checks에는 판정 직전의 `sums_check_*_r1.md`만 있다.
- 감사 재실행: `baseline_check sums --no-git`
  - 단계 폴더 7개: 568·52·18·123·210·396·468 항목
  - `judge_60ebb4a4`: 14 항목
  - 8개 모두 종료 0, 불일치·누락·목록 밖 0
- 정오 1-10 끝 문장대로 각 report `inputs.rows.outputs[].sha256`을 단계 SUMS와 대조했다. 9개 파일 모두 같다.
- 판정서에는 "판정 뒤 재대조: 감사가 수행, 일치"로 적거나, 메인이 r2 기록을 남긴다.

### [기록][T] R-13 감사 중 다른 작업이 `ed7_design\ed7_j9fail_8a2a52ce\`에 쓰고 있었다
- 그 폴더의 파일 시각은 13:08~13:12이고, 폴더 수정 시각은 13:18:48이다. 모두 판정 뒤의 원인 분석이다.
- 판정서에는 이 분석이 판정 뒤에 시작됐다고 적는다.
- source_guard 경고("형제 항목 수정 시각만 변경 1건(ed7_design)")가 이 쓰기다. 이 감사의 쓰기는 아니다.

### [기록][R] R-14 그 밖
- 판정 도구에는 `--run-commit` 재정의 인자가 있다(1610행). 이번에는 쓰이지 않았고 report가 값을 기록한다.
- 감도 기록 6설정 실패 3단위(공개 대상, 6.2 678행)
  - `VBMb069 S7 e0.003`: J3
  - `VBMh05 S7 e0.002`: J3·J4
  - `VBMh15 S7 e0.002`: J3
- 감도 기록 설정의 J-P3는 `rev7_record_only` 156행 판정·침범 0이다. `J-P3_record_settings_judged_rows`는 0이다. 구조적으로 늘 0이므로 쓰지 않는다(정오 1-16 239행).
- 교착 서명은 j9main 388·sens 460·G1 171줄 모두 0줄이다(기록).
- R15 나빠짐은 없다(j9main·감도 모두 "구분됨", 나빠짐 거짓). S8·L-c·L-e·stops는 0이다.
- P5-1형 33줄 기록(정오 1-7, 결정 16): `j9_runs\p51_record_8a2a52ce\compare\p51_record_compare.json` status `equal`(sha `2eb71be6…`, 추적됨).

## 규칙↔도구 대조표 (R축)

| 규칙 | 원문 위치 | 도구 | 판단 |
|---|---|---|---|
| 상태 순서 실패 > 결함 > 판정 불가 > 통과 | 명세 6.1 661행 | `status_of` 283~291 | 맞음 |
| 재현 대조를 집계 전에, 불일치 = `setting_defect`, 집계 안 함 | 6.1 672, 6.2 693, 6.3 715 | sens 939~942, confirm 1165~1170 | 맞음 |
| P7-3·P7-9 불일치 = `setting_defect` | 정오 1-17 | `judge_probe_repro` 1475~1478 | 맞음 |
| 군집 k = 4, 4설정 합산, 2위상 이상 실패 | 6.2 680~682 | `cluster_judgement_with_fixed` 272~276, `SENSITIVITY_CLUSTER_K` 61 | 맞음 |
| 고정 표 실패만 더함 | 6.2 691 | 270~271(실패만), `fixed_failed_units` 247~251 | 맞음 |
| 미관측 = 판정 4설정 ∧ `probe_seen` 거짓, 기록 6설정 무시 | 6.2 684·686, 5.2 항목 7 | `sens_units` 995~998 | 맞음(키 파일 judged∧probe_seen 40) |
| 감도 J-P3 = 키 judged 줄, 기대 104 | 정오 1-16 | `_sens_jp3` 1012~1019 | 맞음 |
| G1 기회 실패 + D VBM 고정 실패 ≤ k = 3 | 6.3 736 | `confirmation_judgement` 314~318 | 맞음(경계 통과) |
| j9main 합격 = VB J1~J11 0, LS L-a·L-b·L-c·L-e, J-P3 | 판 6 6.2 443 | `j9main_basis` 844~849 | 맞음 |
| 읽기 (1) J1 짝 단위, (2) L-b 상대 | 판 6 6.2 440~441 | `pair_items` 253~255, `l_b` 815~816 | 맞음 |
| L-a = VB 통과 행의 LS J1·J2·J4·J6·J7 | `v5_criteria` 169 | `l_a` 812~814(`L_A_ITEMS`) | 맞음 |
| J7 = (이름, 다리, 사유) 집합 차, 모든 J7 비교에 | 6.1 662~664, 정오 1-6 | `replace_j7` 626~641(두 표) | 맞음 |
| 강성 예외는 감도 10설정만 | 판 6 6.2 487~488, 판 7 6.2 698 | `unit_table`(감도만) 675 | 맞음 |
| j9main J-P3 기대 200, 다르면 `setting_defect` | 정오 1-11 | `J9_MAIN_JUDGED_ROWS` 138, `jp3_basis` 478~479 | 맞음 |
| 조건 읽기 0 = 판정 불가(12a·12b 제외) | 정오 1-13 161 | `condition_basis` 519~520 | 맞음(이번 읽기 > 0) |

## 재집계 표 (C축)

| 항목 | 판정 값 | 재집계 값 | 차이 | 판단 |
|---|---|---|---|---|
| j9main VB 실패 (행, 위상, 항목) | 15(J7 14, J3 1) | 15(J7 14, J3 1), 집합 같음 | 0 | 일치 |
| j9main L-a | 2(LS4 R12 top\|FR\|0\|0.05: J1 gate end_att, J4 ready→probe) | 같은 2 | 0 | 일치 |
| j9main L-b(상대) | 1(같은 짝 J5, t_back 38.65 → None) | 같은 1 | 0 | 일치 |
| j9main J11 대체 다리 n_late > 0 | 0(stops 0) | 0(대체 사건 0) | 0 | 일치 |
| 감도 실패 단위(460) | 6(판정 3, 기록 3) | 6, id 집합 같음 | 0 | 일치 |
| 감도 probe 40단위 verdict | 39 통과·1 실패(고정 표와 차이 0) | 실패는 `VBMslow S7 e0.001`뿐 | 0 | 고정 표 39/1과 일치 |
| 군집: 다위상 / 단독 | `VBMslow S7` / 1(`VBMslow R12 top-FL-Fs0`) | 같음 | 0 | 실패(다위상) 일치 |
| confirm G1 기회 실패 + D | 3 + 0 = 3 ≤ 3 | 3(pass 거짓 3, retract WARN 0) + 0 | 0 | 통과 일치(경계) |
| G1·D FAULT 줄 | 0·0 | 0·0 | 0 | 일치 |
| t8 대체 없는 쌍 해시 같음 | 22/22 | 22/22 | 0 | 일치 |
| probe a2 해시 대조 | 114 같음 | 114 같음 | 0 | 일치 |
| J-P3 판정 행 수 | 200 / 104 / 171 / 10 | head-only 아님 200, 키 judged∧head-only 아님 104, 키 171, 원시 10 | 0 | 일치(J-P3 값 자체는 재계산 안 함) |

## 9항 분류(판 7 결론)
- ① j9main `failed`와 ② 감도 `failed`는 규칙상 확정이다.
  - 실패 항목이 J1~J11이다. 이것은 하네스 단독이고 경로 1 몫이며, 판정 후 감사가 재집계한다(판 6 11절 775행). 재집계가 일치했다.
  - setting_defect·not_judgeable는 0이고, 재현 불일치도 0이다.
  - 실패 18건(VB 15, LS 3)의 `base_other_phase_has_it`가 모두 거짓이다. 그래서 `v5_criteria` 12절 233행 "조건부(실패가 위상 산포 안에서만)"는 성립하지 않는다.
  - 실패는 기준선에 속하지 않는다(`baseline_failures.counted` 0이고, 15건 모두 V0 통과 → VB 실패).
- 판 7 합격은 아니다(확정).
  - 판 6 6.2 443행의 합격 조건(이어받음)이 깨졌다. 판 7 0절 304행은 판정을 ①~⑤로 정하는데 ①②가 실패했다.
  - `v5_criteria` 11절 H-2·H-6이 걸렸고, 사용자 결정은 "멈춤"이었다.
  - 문구 주의: 판 7 명세에서 "판 7은 합격이 아니다"를 명시한 문장은 확인 단계(③)뿐이다(761행). `v5_criteria` 12절 234행의 "불합격"은 "11절 항목이 사용자 결정으로도 풀리지 않음"이다. 판 6 판정서처럼 "불합격"으로 쓰려면 근거 문장(판 6 6.2 443행 + 12절 234행 + 사용자 멈춤 결정)을 함께 인용한다(확인 필요 1).
- 경로 2 J-P3는 남아 있다(M-1). 결론에는 영향이 없다.
- 12a(T-JR-12a, dg3)·12b(pre10a, 12b_plan, 12b_vbkm0, b4, VBKM)는 **미실행**이다. 실패 뒤 멈춤 규칙(판 6 4절 400행)과 사용자 결정에 따른 것이다.
  - 도구가 낸 `not_judgeable`이 아니고, 통과도 아니다. 판 6 판정서 213~244행 꼴로 "미실행"이라 적는다.
  - 미실행에 걸린 항목: 정오 1-1, 1-2 조건 1, 1-3, 1-13·1-20의 12a·12b 실측, 1-9의 12a·12b 문제 목록, 6.4 P-pred, 12b seed 50~53.
  - seed 50~53은 계속 미사용이다. 다음 판이 이 seed를 쓰려면 충돌 스캔에 판 7 출력(l1ref_a1의 r79 키 포함)을 넣어야 한다(6.4 768행과 같은 논리).

## 정오 1 「판정서에 옮길 것」 17항목

| # | 항목 | 지금 채울 수 있음 | 근거·비고 |
|---|---|---|---|
| 1 | 1-1 12b 계획 시점 | 설계 문장만 | 12b_plan 미실행, `selection_sha256` 없음 |
| 2 | 1-2 조건 3(표·C sha·run steps 경로), 조건 1 기록 | 조건 3은 됨. 조건 1은 안 됨 | 10a 미실행이라 c92·c93 확인 기록 없음 → "해당 없음(미실행)" |
| 3 | 1-4 O7-14 | 됨 | 정오 1-4 89행 문장 |
| 4 | 1-6 J7 범위 | 됨 | R-2·대조표 |
| 5 | 1-7 P7-2 축소, P5-1형 33줄 결과 | 됨 | cases 10줄 통과, `p51_record_compare.json` equal |
| 6 | 1-8·1-9 T8 VBM0 태그, l1ref `identity_sources` | 됨(12a·12b 문제 목록은 미실행) | t8 `controller_tags`, l1ref `runs.<stem>.identity_sources` |
| 7 | 1-10 SUMS 작성·판정 직전 대조 | 됨 | `main_checks\sums_write_*_r1`·`sums_check_*_r1`. 판정 뒤 재대조는 R-12 |
| 8 | 1-13 12a·12b 조건 '해당 없음' | 규칙 공개만 | 실측 없음(미실행) |
| 9 | 1-14 P7-4 통과, T → T′ | 됨 | 정오 1-14 |
| 10 | 1-15 O7-15 | 됨 | — |
| 11 | 1-16 감도 판정 집합, 기록 설정 침범 | 됨 | `rev7_record_only.runs_with_breach` 0(156행 판정) |
| 12 | 1-17 재현 불일치 = setting_defect | 됨 | 이번 불일치 0 |
| 13 | 1-20 12a·12b 사건 시각, `no_event_lines` 대 판정 등급 줄 | 규칙 공개만 | 실측 없음(미실행) |
| 14 | 1-9 12a·12b 출처별 기록 축소, 12a 결측 = not_judgeable | 규칙 공개만 | 실측 없음 |
| 15 | O7-16~O7-19 | 됨 | 이 감사의 블라인드 절차 공개(아래)도 더한다 |
| 16 | 경로 2 [정의] 추가 | 결정 사실만 | 넘김 문서·경로 2 실행 없음(M-1) |
| 17 | 1-19 1단계 전 건식 확인 | 됨 | `ed7_design\dry_mc_8a2a52ce\` |

- 17항목 밖에서 판정서에 적을 것
  - 봉인 12절 공개 항목 전부(1023~1067행)
  - R-5의 예측 대조와 FL-Fs4 o0.0 줄 실패
  - R-9의 강성 경고 비중
  - R-14의 감도 기록 설정 실패 3
  - R-10의 한 번에 판정한 사실
  - R-13의 판정 뒤 원인 분석 시점
  - 판정서 초안이 생기면 `judgement_checklist.py --rules "…/jp3_remedy_spec_v7*.md" --judgement <판정서>`로 대조하고, ambiguous 항목은 원문을 읽는다.

## 확인 필요
1. 판 7 결론 문구: "불합격"으로 쓸지, "합격 아님(① j9main·② 감도 판정 실패, 사용자 멈춤 결정)"으로 쓸지 정한다. 근거 문장은 9항에 적었다. 규칙상 결론(합격 아님)은 같다.
2. 판 7 J-P3 경로 2를 실행할지 정한다(M-1의 (가)·(나)).
3. 12a·12b를 "미실행"으로 적고 판 7을 닫을지 정한다. 또는 기록용으로 따로 돌릴지 정한다. 기록용으로 돌리면 판정이 아니고, 결과를 본 자료가 늘어난다는 점을 공개해야 한다.

## 위임 필요
- tools/verif 후보(python-expert): `j_items_recount`
  - 입력: 판정 jsonl, 기준 jsonl, 설정 대응, 감도 예외 설정 목록
  - 출력: (설정, 행, 위상, 항목) 실패 집합과 판정 json(`J_vs_V0`·`LS_vs_VB`·`units`) 대조
  - 종료 코드: 0 일치 / 1 차이 / 2 입력 오류
  - 이유: 지금 `pair_recount.py`는 원시 통과 표지만 받는다. J3·J4·J5·J7(이름·(이름, 다리, 사유))·읽기 (1)·L-a·L-b는 이번에도 즉석 스크립트로 셌다. 판 5·판 6·판 7에서 같은 재집계가 반복되고 있다.

## 메인 세션 권고
- 판정서 커밋 전 절차
  - M-2: `large_outputs.py` 건식 → `--apply`, `LOCAL_ONLY.SHA256SUMS`, `git status --ignored`
  - R-12의 판정 뒤 SUMS 재대조를 r2 기록으로 남긴다(선택).
  - 이 감사 원문은 `postjudge\` 폴더에 저장한다. 판정 SUMS 폴더(`judge_60ebb4a4`)에는 더하지 않는다.
- M-1을 (가)로 정하면 control-expert가 판 7 경로 2 넘김을 쓰고, `handoff_leak.py`로 확인한 뒤 경로 2 에이전트에 넘긴다.

## 검사하지 못한 것
- J-P3 rev 6/7 판정 값과 ③ rev 7 조건 읽기의 침범 판별: T4h 배열과 상계 식으로 재계산하지 않았다. 판정 행 수와 report의 침범 0만 대조했다. 이것은 경로 2의 몫이다.
- confirm의 저장 V0 격자 run 쪽 판정(`v0_grid_comparison`)과 D 24행의 V0 verdict·조건 읽기 값: 해시 다중집합과 G1 쪽 pass·WARN만 재집계했다.
- 고정 표 64행의 단위 판정 재계산(probe-repro P7-9): 해시 일치만 독립으로 봤다. 감도 probe 40단위 verdict는 R-1 재집계로 간접 확인했다.
- R15 나빠짐 통계, L-c 리밋 사이클, S8 F-5, 교착 서명, l1ref `identity_sources`의 값 내용: 다시 계산하지 않았다.
- J8·J9·J10은 재집계에 넣었다(실패 0). J11은 대체 다리 n_late만 봤다.

## 실행한 검증
- 인터프리터: python-dev `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`-X utf8`, `MKL_THREADING_LAYER=TBB`). 프로젝트·판정 모듈은 import하지 않았다.
- 의존성 점검: STAMP(이 세션에서 이미 확인).
- verif 도구
  - `baseline_check sums --no-git` ×8(종료 0)
  - `seal_check`(명세·정오, `--const jp3_ed7_judge.py:SPEC_V7_SHA256`): 종료 0
  - `timeline`(규칙 2 × report 4): 종료 1, `mtime_only_basis` 4·`seal_time_missing` 2, after 0
  - `gate_scan`(판정 도구 2파일): 종료 1, warning 5, R-11
- 즉석 스크립트 s1~s11(scratchpad `verif-ed7post\`): report 구조, j9main·감도 재집계, 통과 판정 건수, 정체성 스캔, sha 대조, 해시 재현, 위상 산포 표지, G1 실패
- git 조회: `rev-parse`, `status --porcelain`, `log -1`, `worktree list`, `check-attr`, `check-ignore -v`, `ls-files --error-unmatch`
- 만든 파일
  - scratchpad `verif-ed7post\`(스크립트, guard state, seal·timeline md): 보고 전에 폴더째 지웠다.
  - 도구 출력이 큰 1회는 하네스가 `C:\Users\jinbeom\.claude\projects\C--workspace-outrigger-control\0d95027e-6012-4053-b99a-1e505935768c\tool-results\b1iyi0g91.txt`에 저장했다(하네스 관리 경로, 지우지 않음).
  - 메모리: `audit_pitfalls.md`·`MEMORY.md`에 프로젝트 무관 함정 1항목을 더했다.
- 블라인드 절차 공개(판정서 15번에 더함)
  - (a) Glob 1회: path = 메인 checkout 루트, 패턴 `06_analysis/**/v5_criteria*.md`. 블라인드를 품은 `06_analysis` 아래를 재귀 순회했다. 출력은 `v5_criteria*.md` 16개 이름뿐이고, 블라인드 이름·건수는 나오지 않았다.
  - (b) `git ls-files -- "*jp3_ed6_judgement_79495405.md" "*jp3_ed5_judgement*.md"`: 전체 index에 글롭 pathspec을 썼다. 출력은 1개 파일 이름뿐이다.
  - (c) `j_p3_cause` 최상위 비재귀 `Get-ChildItem -File`·`-Directory`로 최상위 파일·폴더 이름을 화면에 냈다. `j9_runs` 안으로는 들어가지 않았다.
  - 블라인드 경로(`606f8713\cdry_a1\VBK_c92*`·`VBK_c93*`·`logs\`, worktree 사본, 판 6 `selection.json`)는 Read·Grep·Glob 대상으로 지정하지 않았다.
- 최종 판정 직전에 다시 확인한 것
  - console.log 7개 status: pass 5, failed 2
  - T′ HEAD `60ebb4a4`, status 0항목
  - 감사 중 바뀐 것은 다른 작업의 `ed7_j9fail_8a2a52ce` 쓰기뿐이다(R-13). 판정 입력은 바뀌지 않았다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v7.md 10902ffd…, jp3_remedy_spec_v7.md.sha256 8cfd1981…, jp3_remedy_spec_v7_erratum1.md 74c49bda…, jp3_remedy_spec_v7_erratum1.md.sha256 b1cfb220…, audit_prerun_main_ed7_20261126.md dcc6937a…, SHA256SUMS c7d9548a…, l1ref.json 58065781…, t8.json 1a0c6327…, cases.json c5cdd453…, probe-repro.json a3e61d78…, confirm.json 02175169…, j9main.json 0b87b60b…, sens.json b178de9e…, console.log 644a1231…, console.log 3afc9d60…, console.log 35537d6a…, console.log 35c1cfa3…, console.log d29d4817…, console.log 3fca07fb…, console.log 69eb4ccb…, j9_main.jsonl c89ec827…, sens.jsonl 44c4789c…, confirm_g1.jsonl 64be3f72…, ed7_probe_d.jsonl 36671c0e…, ed7_t8.jsonl 9ba6e2a9…, ed7_cases.jsonl 6bda01de…, ed7_probe_a2.jsonl dd6afcc5…, j9main.done 303091a0…, sens.done 9e3f35ad…, confirm.done dbe72606…, impl_t8.done b0ac99c3…, impl_cases.done f8a585c8…, impl_probe.done a06b6e6b…, l1ref.done 9d21d982…, main.jsonl 9ad74990…, fixed_table_a2.json f7754a69…, sens_keys_ed7.json be930b75…, confirm_g1_grid171.json 684054ab…, confirm_b_grid192.json 4e80e69b…, judge_probe_stop.ps1 08a631e8…, judge_confirm_stop.ps1 5a564003…, judge_sens_stop.ps1 5f2fefd2…, chain_ed7_a3.log 513f4604…, chain_ed7_a2.log ed03c87d…, chain_ed7_a1.log c30bc44f…, 디렉터리 목록 동일, ~$ 임시 파일 없음) · 경고: 형제 항목 수정 시각만 변경 1건(ed7_design)
- 사용한 스킬: 없음
