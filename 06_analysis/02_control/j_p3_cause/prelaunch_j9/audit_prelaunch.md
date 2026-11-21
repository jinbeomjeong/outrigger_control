# 436.9 J-P3 실행 전 감사(verif-protocol-auditor 리포트 원문, 2026-11-21)

메인 세션이 hand-back 원문 전체를 그대로 저장했다. 결정·정오는 맨 끝 절에 덧붙인다.

---

## 감사 요약
- 의존성 점검: 모두 있음(numpy 2.5.3, pyyaml 6.0.3, git)
- 본 결과: 판정 대상 결과(사례 재생·T-JR·건식 출력)는 아직 없어서 열지 않았다. 대신 다음 저장 자료를 열었다. ① 저장 H-6 `resume_k1/h6_dg3_v4on.json`: 키가 있는지와 그 개수, meta 키 이름만 봤다. ② `baseline_221456d/j9_cases.identity.json`, `resume_k1/h10_reuse_rerun.identity.json`, `h6_dg3_v4on.identity.json`: python 경로, 스레드 변수, affinity mask, git head, is_clean. ③ `j4a_remedy_99e9132b/dryrun_selection.json`: 선정 필드와 명령 문자열. ④ junit 3개: 시험 이름과 상태. `h6_r79_judge.json`은 해시만 봤다. resume_k1 결과의 값은 열지 않았다.
- 대상: 436.9 J-P3 보완의 실행 전 단계 (1)~(7). 시점은 실행 전이다. 코드는 worktree `z4369-jp3`의 `99e9132b`(locked, 깨끗함)이고, master는 `1af65cf0`이다.
- 기준 문서(해시 앞 8자리): `jp3_remedy_spec.md` 판 4a `8be9de22`, 4a-1 `4b122dd0`(`.sha256` 없음), 4a-2 `2f3e36bd`, 4a-3 `f001383a`, 4a-4 `67380b10`, 정오 1 `1ccbe526`, 기준선 SUMS `197ac14e`, FIXED_INPUTS `f35fa862`. 뒤 판이 앞 판을 덮는다(4a-4 > 4a-3 > 4a-2 > 4a-1 > 13절 > 본문).
- 판정: **차단 1 / 실행 전 수정 8 / 기록 15**
  - (1) P-1은 지금 명령대로 돌리면 P-1b `t12-selfcheck`가 반드시 실패한다. (6) T-JR-12는 P-1에 걸려 있으므로 함께 막힌다.
  - (2)~(5), (7)은 B-1과 직접 관계가 없다. 그러나 명령·환경·정체성 검사를 고정하지 않으면 판정 근거가 약하다.
  - B-1을 고치면 코드 커밋이 바뀐다. 그래서 수정 → 새 커밋 고정 → 이 감사의 좁은 재감사를 거친 뒤 일곱 단계를 같은 커밋에서 돌리기를 권한다.

### 단계별 결과

| 단계 | 결과 | 걸린 항목 |
|---|---|---|
| (1) P-1(base-judge → R-2 → t12-selfcheck) | **차단** | B-1. 그 밖에 M-2(자리표시), 기록 R-7·R-8 |
| (2) 5.1 B2 건식 5실행 | 경고(실행 전 수정) | M-2(명령·CWD·환경). 선정 자체는 독립 재확인으로 통과(R-13) |
| (3) 5.2 F-A 경로 동등성 3 run | 경고 | M-1·M-2. 판정 도구 `case-f-path`는 4a-3 5.2와 일치 |
| (4) 사례 재생 A~F·X11 | 경고 | M-1(C·D·X11의 정체성 기록 없음), M-2(스레드 조건 → P4-1 해시), M-5(P4-9 키가 없어도 통과) |
| (5) `j9_t8` 88행 → T-JR-10/11 | 경고 | M-4(t8에 13.6 정체성·B2 검사 없음, T-JR-11 해시 길이 검사 없음), M-2 |
| (6) T-JR-12 VBH·VBJ·VBJ0 각 135 → t12 | **차단**(P-1에 걸림) | B-1, M-3, M-5, M-8 |
| (7) records(T-JR-13~15) | 경고 | M-6(입력이 비어도 통과, T-JR-15 판정 여부 미정 → 확인 필요) |

## 발견 사항 (심각도순)

### [차단][R·E] B-1: P-1b `t12-selfcheck`가 저장 H-6에서 반드시 setting_defect를 낸다
- 근거:
  - `jp3_tjr_judge.py:369`는 `judge_t12`가 언제나 `_check_lines`를 부르게 한다. `:380`에서 `checked = {"new": new_lines, ...}`이고, `:385-387`에서 모든 new 줄에 `rod_reading_evidence_problems`를 적용한다.
  - `j_p3_inputs.py:72-75`는 증거 키(`rod_reading_truth_calls`, `two_pressure_reads`)가 없으면 `"P4 evidence keys missing"`을 돌려준다.
  - `t12_selfcheck`(`:569-588`)는 H-6을 base와 new 양쪽에 넣는다. `selfcheck_problems`(`:552-555`)는 상태가 pass가 아니면 미스로 센다.
  - 저장 H-6을 직접 셌다(키가 있는지만, 값은 보지 않음). 줄 135, `hydraulics_record` 있음 135, `rod_reading_truth_calls` 0, `two_pressure_reads` 0. 4a-3 3.2절도 증거 키는 `3b949f5`에서 더해졌다고 적었고, `jp3_tjr_judge.py:379` 주석도 "the stored H-6 base of VBH has no evidence keys"라고 적었다.
  - 단위 시험 `test_jp3_addendum_4a3.py:248`은 `problems.not_judgeable == [] and problems.failures == []`만 assert하고 `setting_defects`는 보지 않는다. 그래서 시험은 통과하고 실제 절차는 실패한다. `test_jp3_addendum_4a4.py:262-270`도 합성 보고서와 입력 거부만 본다.
- 실패 시나리오: P-1b는 상태 `setting_defect`(135건), 종료 1로 끝난다. 4a-4 6절 "하나라도 다르면 T-JR-12 실행 전에 멈춘다"와 4a-3 4.1절 "다르면 READY 읽기 결함이므로 멈춘다"가 적용되어, READY 결함이라는 틀린 진단으로 멈춘다. 반대로 이 미스를 사람이 해석으로 넘기면 자기 대조가 보증하려던 것(설정 결함 0)이 공개 없이 바뀐다.
- 권장 조치(python-expert):
  - VBH 묶음에서 증거 검사는 436.9 설정 줄(`v5_setting` ∈ VBH·VBJ·VBJ0 등)에만 적용한다. 고정 sha인 저장 H-6 줄은 증거 검사 대상에서 뺀다.
  - 자기 대조 단위 시험은 실제 H-6으로 `setting_defects == []`와 `status == pass`까지 assert한다.
  - 고친 뒤 새 커밋을 고정하고(worktree lock 갱신) prelaunch 기록을 바꾼다. 이 감사의 B-1·M-3 부분은 다시 감사한다.

### [실행 전 수정][I] M-1: 새 출력의 실행 정체성(git.head·is_clean)을 기록하지 않는 경로가 있고, 어느 판정 도구도 검사하지 않는다
- 근거:
  - `jp3_*.py` 전부에서 `head|is_clean|identity.json`을 Grep하면 맞는 것이 없다. 기준선 경로 문자열만 나온다.
  - `run_v5.py:775-780`: identity sidecar는 `--out`(또는 `--group`)이 있을 때만 쓴다. `--out`이 없으면 worktree의 `v5/<batch>.jsonl`에 정체성 없이 쓴다(`:720-721`).
  - `r79_L3L4_final.py:282`: meta `git_head`는 끝에 한 번만 남고, is_clean은 없다. `_read_partial`(`:168-175`, `:250-252`)로 이어서 돌리면 앞 실행의 줄이 섞여도 head 하나만 남는다.
  - `jp3_case_replay.py`·`jp3_x11_replay.py`에는 identity·git 코드가 없다. 기준선은 외부 래퍼 `baseline_221456d/_runners/identity_mark.py`로 정체성을 남겼다.
- 실패 시나리오: worktree 커밋이 실행 중이나 실행 사이에 바뀌거나, 다른 커밋에서 만든 partial 파일을 이어 돌리면 판 섞임이 드러나지 않는다. 판정 도구는 13.6절 `spec_edition`만 보므로, 같은 판의 다른 코드 커밋을 구별하지 못한다.
- 권장 조치(메인 세션 절차 + python-expert):
  - 모든 실행은 `--out`을 쓴다. C·D·X11·r79 실행은 `identity_mark.py` 같은 start/end 래퍼로 감싼다.
  - 판정 전에 출력 폴더마다 `baseline_check.py identity --expect-commit 99e9132b(또는 새 커밋) --mtime`가 종료 0인지 확인하는 절차를 prelaunch에 넣는다.
  - partial·append 이어 돌리기는 같은 커밋 안에서만 허용한다고 적는다.

### [실행 전 수정][I·R] M-2: 실행 명령이 자리표시로 남아 있고, 출력 위치·인터프리터·스레드 조건이 정해지지 않았다
- 근거:
  - `placeholder_scan --pattern "<…>"` 결과 26건이다. `jp3_prelaunch_h6_selfcheck.json:14-21`에 `<prelaunch>`·`<h6>`·`<judge_sha256 of P-1a>` 등이 있고, `dryrun_selection.json:16392-16394`에 `<sel.json>`·`<root>`가 있다. 기본 패턴(`{NAME}`)으로는 0건이다.
  - `<prelaunch>` 출력 폴더는 inputs에 정의가 없다.
  - 건식 명령의 출력은 CWD 기준 상대 경로 `dryrun_evidence/…`다.
  - prelaunch는 "dynamics-dev python.exe -I -B"인데 호출 지시는 `conda run`이다.
  - 기준선·저장 h10·H-6 identity에는 `MKL/OMP/NUMBA/OPENBLAS_NUM_THREADS=1`, `MKL_THREADING_LAYER=TBB`, mask `0xfff0000`·`0xff0000`이 기록돼 있다. 그러나 이번 실행의 환경 변수는 어디에도 고정되지 않았다. P4-1, T-JR-10/11은 명령 해시 동일성 판정이다.
  - `.gitattributes:154` `06_analysis/02_control/j_p3_cause/** -text`는 그 아래 새 폴더를 덮는다. `06_analysis/03_hydraulic/coupled/v5/j9/` 같은 곳은 `text: unspecified`라 보호되지 않는다(check-attr로 확인).
  - `*.npz`는 `.gitignore:41`에 걸린다.
  - 실행 스크립트(.ps1)가 없어서 `ps1_lint`는 돌릴 대상이 없다.
- 실패 시나리오:
  - 스레드나 MKL 계층이 다르면 P4-1·T-JR-10/11에서 거짓 해시 불일치가 나 멈춘다.
  - 출력이 worktree나 보호 밖 폴더에 남으면 커밋 때 CRLF로 바뀌거나 npz가 조용히 빠진다.
  - 명령을 실행 때 손으로 채우면 사전 고정이 아니게 된다.
- 권장 조치(메인 세션, 필요하면 compute-scheduler-expert): 일곱 단계의 구체 명령 파일(.ps1 또는 md)을 하나로 고정한다. 담을 것:
  - 메인 checkout 절대경로 출력 폴더(`j_p3_cause/<run 폴더>/` 아래)
  - worktree CWD
  - 인터프리터 형식
  - 스레드 변수 다섯 개, workers·mask
  - 고정한 뒤 `ps1_lint.py`와 `placeholder_scan --pattern "<[A-Za-z_][^>]*>"`가 종료 0인지 본다.

### [실행 전 수정][E·I] M-3: t12가 줄의 설정(`v5_setting`)·rev 5를 묶음과 대조하지 않는다
- 근거:
  - `jp3_tjr_judge.py:341-387`: 키 집합·L2 수·등급·READY·증거만 본다.
  - `_dg3_identity`(`:485-490`)는 `rule_revision != 5`이면 빈 목록을 돌려준다.
  - 저장 H-6 줄에도 `v5_setting`이 있다(135/135). 그래서 검사할 수 있다.
  - 실행 시점에는 `verdict_runs.plant_options_record` → `harness_hydraulics.check_last_extend_start`(`verdict_runs.py:675`)가 ③ 옵션과 controller 일치를 본다. 이것이 완화 요인이다.
- 실패 시나리오: `--new`에 base와 같은 파일을 주거나, VBJ와 VBJ0을 바꿔 주거나, VB로 돌린 파일을 주면 135짝이 항등으로 통과한다(빈 비교의 통과).
- 권장 조치(python-expert):
  - new 줄 `v5_setting` = 묶음 이름(VBH·VBJ)이고 `rule_revision` = 5인지 본다.
  - VBJ 묶음의 base 줄은 `v5_setting` = VBJ0인지 본다.
  - base 파일 sha ≠ new 파일 sha인지 본다.
  - 어기면 setting_defect다.

### [실행 전 수정][I] M-4: t8(T-JR-10/11)에 13.6절 정체성·B2 증거 검사가 없고, T-JR-11 해시 비교에 길이 검사가 없다
- 근거:
  - `jp3_tjr_judge.py:162-337`: t8 경로에는 `identity_problems`·`rod_reading_evidence_problems` 호출이 없다.
  - 13.6절: "판정 도구 … 기본값이 아닌 행 … `spec_edition`이 봉인 값과 다른 rev 5 행도 `setting_defect`".
  - `_t_jr_11`(`:251-253`)은 `commands_sha256`를 `!=`로만 비교한다. T-JR-10은 64자 검사를 한다(`jp3_t8_rules.py:73`, `_same_hash` `:276`).
- 실패 시나리오: 옛 판 코드 출력이나 시험 규칙 출력이 VBH·VBJ 줄로 섞여도 t8은 해시만 보고 판정한다. 해시가 None·짧은 값으로 같으면 T-JR-11이 통과한다.
- 권장 조치(python-expert): VBH·VBJ 줄에 `compare.identity_problems`를 적용한다. VBH·VBJ·VBJ0 줄에 B2 증거 검사를 적용한다. T-JR-11에 64자 검사를 넣는다. 적용 범위는 "확인 필요 3"이다.

### [실행 전 수정][E] M-5: 키가 없으면 0으로 읽혀 통과하는 곳 두 곳
- 근거:
  - `extend_start_bound.py:1862-1863` `total()`: `int(sum(record.get(key) or []))`. t12 VBJ의 J-P3(`jp3_tjr_judge.py:493-508`)가 이 함수를 쓴다. 판정 키가 없으면 0이 되고 pass로 간다. 4a-2 R2의 "키가 없으면 0으로 두지 않고 판정 불가" 원칙과 다르다.
  - `jp3_baseline_compare.py:490`: P4-9 `sum(check.get("retract_tracker_dominated_reads") or [0])`. `gate_scan`의 `missing_key_default_pass`가 잡은 것이다. 5.7절 P4-9는 "빈 집계를 통과로 읽지 않게"를 명시한다.
- 실패 시나리오: 기록 함수가 바뀌거나 빠져 키가 없는 rev 5 행이 들어오면, J-P3와 P4-9가 통과로 나온다.
- 권장 조치(python-expert): 판정 키는 길이 4 목록인지 확인하고, 아니면 판정 불가로 한다(`judged_key_problems` `:384-392`와 같은 꼴).

### [실행 전 수정][E·R] M-6: `records`(T-JR-13~15)는 입력이 비어도 pass이고, T-JR-15 순 힘 초과를 실패로 세지 않는다
- 근거:
  - `jp3_tjr_judge.py:793-798`: `--replay`·`--dg3`·`--lock-rows`는 `nargs="*"`, 기본값 `[]`이다. `:714`는 `lock_rows`가 있을 때만 0행 판정 불가를 낸다.
  - `:722`: `T-JR-15_seed_rows_over_1N`은 기록만 하고 상태를 바꾸지 않는다(docstring ":56 records never fails").
  - 4a-2 3.4절은 "판정: 모든 행 |ΔF_seed| ≤ 1 N … 판정 행 0 = 판정 불가"이고, 4a-2 B4는 "T-JR-13~15는 기록하고, T-JR-15 순 힘은 3절 열"이다. 둘이 다르다.
  - T-JR-13의 "오류 0"은 도구가 읽지 않는다. 재생 보고 수(426·135)도 대조하지 않는다. `t4h_replay`의 시험 전용 보고(`judged: False`, `t4h_replay.py:461-463`)도 거부하지 않는다.
  - T-JR-13 재생 명령(`t4h_replay … --extend-start-revision 5`의 입력·출력)이 고정되지 않았다.
- 실패 시나리오: 인자를 빼먹으면 T-JR-13~15가 "pass"로 기록된다. T-JR-15가 판정 항목이라면 1 N 초과가 있어도 통과다.
- 권장 조치: python-expert가 빈 입력을 판정 불가로 하고, 재생 보고 수·시험 전용 보고를 검사하게 한다. T-JR-15를 판정으로 볼지는 "확인 필요 1"에서 정한다. 판정이면 초과를 실패(종료 1)로 바꾼다. 메인 세션은 T-JR-13 명령을 M-2 명령 파일에 넣는다.

### [실행 전 수정][R] M-7: 실행 실패 처리표가 없다
- 근거:
  - 13.5절은 "관문 실패·판정 불가면 멈춤"만 정한다. 실행 오류·중단 뒤 다시 돌려도 되는지, 출력 이름, 결과를 본 것으로 치는 시점, 남은 partial의 처리를 정한 표가 없다.
  - 도구 동작은 이렇다. `run_v5._done_keys`(`run_v5.py:591-612`)는 오류 줄을 done으로 세지 않고, 같은 파일에 append로 다시 돌린다. 그러면 오류 줄과 성공 줄이 함께 남는다. t8(`jp3_tjr_judge.py:289-291`), case(`jp3_case_judge.py:115-117`), baseline(`jp3_baseline_compare.py:203-205`)은 그 파일을 영구히 판정 불가로 둔다.
  - r79 partial(`r79_L3L4_final.py:168-175`, `:252`)은 오류 레코드도 done으로 남긴다. 그러면 t12가 판정 불가가 된다(`jp3_tjr_judge.py:396-397`).
  - 판정 도구 종료 3(error)은 4a-2 B4 표(0/1/2)에 없다.
- 실패 시나리오: 오류가 난 뒤 같은 `--out`으로 다시 돌리면 그 묶음은 다시 판정할 수 없다. 새 이름으로 돌리면 "결과 본 뒤 재실행" 여부가 기록되지 않는다.
- 권장 조치(control-expert 덧붙임 문안 → 메인 세션): 단계별 종료 코드·오류 줄·중단에 대한 조치표를 만든다. 담을 것: 새 출력 폴더 규칙, partial 삭제 금지·보존, 다시 돌릴 때 공개 문구, 종료 3의 뜻.

### [실행 전 수정][R] M-8: T-JR-12 새 쪽 판정 파일과 키 입력이 고정되지 않았다
- 근거:
  - `jp3_tjr_judge.py:76`의 docstring에는 `r79_sensor_judge.py judge <judge.json> <dg3 file> <H-8 VB L1 extract> --s4-late-loc`라는 손 명령만 있다. 이 L1 추출본이 P-1a의 `h6_base_judge_L1_reference.json`과 같은지 검사하는 곳이 없다.
  - VBJ 묶음의 `--base-judge-sha256`은 선택 인자다(`:537-539`).
  - 4a-3 4.4절은 "새 쪽 판정 파일도 같은 명령 꼴로"를 요구한다.
  - 키 입력은 `--keys "<keys>"`라는 자리표시다(`:75`). `read_keys_file`은 `.json`의 `results[].key`를 읽는다(`r79_L3L4_final.py:178-195`).
- 실패 시나리오: base와 new 판정 파일이 다른 L1 참조로 만들어지면 L2 등급 전이가 생긴다. 거짓 실패나 거짓 통과가 날 수 있다.
- 권장 조치(python-expert·메인 세션): VBH·VBJ·VBJ0 판정 파일을 P-1a와 같은 L1 추출본(sha assert)으로 만드는 하위 명령이나 고정 명령을 둔다. 판정 파일 sha를 실행 전 기록에 남기고 VBJ에도 sha를 넘긴다. 키는 sha가 고정된 목록 파일로 준다(예: `--keys-file` 저장 H-6, meta `keys_file.sha256` 대조).

### [기록] 
- R-1 [S] 4a-1에 `.sha256`이 없다(`seal_check` `seal_missing`). 해시는 FIXED_INPUTS 3행 `4b122dd0…`으로 고정돼 있고 실제 파일과 같다.
- R-2 [S] 기준선 SUMS는 CRLF 27줄(`-text`)이다(`baseline_check` `sums_crlf`). `jp3_baseline_compare.py:144-145`가 `\r`을 뗀다. 4a-1 1절과 맞다. SUMS 27개 파일은 해시가 모두 같다(불일치·누락·목록 밖 0). 기준선 identity 6블록은 모두 head `221456d`, is_clean True다(`baseline_check identity` 종료 0).
- R-3 [S] FIXED_INPUTS 31줄은 실제 파일과 31/31 같다.
  - main.jsonl과 resume_k1 9개는 git 밖이다. main.jsonl은 `.git/info/exclude:23`. 4a-3 5.4절이 허용한다.
  - T4h SUMS 두 개는 426/426, 135/135로 같고, 누락·추가 0이다. manifest 해시도 재검토 2.3절 값(`e9af5b85…`, `7e1fc01f…`)과 같다.
  - **T4h SUMS의 경로는 T4h 폴더 기준이다.** SUMS 위치나 저장소 루트 기준이 아니다. FIXED_INPUTS는 루트 기준이다. 이 기준을 적은 문서가 없으므로 머리말이나 README에 적기를 권한다(integrity 오탐의 원인).
- R-4 [S] 재검토 4a4e1 2.1·2.5절의 "추적 아니오"는 지난 값이다. 덧붙임 4a-2~정오 1, prelaunch_j9, j4a_remedy_* SUMS는 모두 `1af65cf0`에서 처음 커밋됐고 HEAD에 있다. 줄바꿈은 `-text`, CRLF 0이다. 키 파일만 의도대로 CRLF 1이다.
- R-5 [S] 기준선 npz 18개는 강제 추가로 추적 중인데 `.gitignore:41:*.npz`에 걸린다(`cited_ignored_tracked`). 새 T4h npz도 `git add -f` 없이는 조용히 빠진다.
- R-6 [I] 저장 h10·H-6의 identity sidecar(head `b9f5707`, clean, 스레드 1/TBB)가 FIXED_INPUTS에 없다. 4a-3 3.1절의 "identity git.head `b9f5707`, `is_clean` true" 주장을 받치는 파일이므로 고정 목록에 더하기를 권한다.
- R-7 [I] P-1a 출력(`h6_base_judge.json`·`_L1_reference.json`)은 만든 뒤 FIXED_INPUTS에 넣어야 한다(4a-3 4.4·5.4절). 그러면 FIXED_INPUTS sha가 `f35fa862`에서 바뀐다. 또 `h8_noise_judge_4368.reference_extract`(`:444-450`)는 L1 참조 파일을 조용히 덮어쓴다. 판정 파일 쪽(`jp3_tjr_judge.py:603-604`)만 덮어쓰기를 거부한다.
- R-8 [R] R-2 `--stored-h6-judge`의 sha는 대조하지 않는다(재검토 권고 1, 보류). 도구 보고서 `inputs`에 입력 sha가 남으므로, 판정 후 감사에서 FIXED_INPUTS 24행(`f8352c5d…`)과 대조한다.
- R-9 [E] `gate_scan`의 `tag_single_compare` 5건(`jp3_tjr_judge.py:223`, `jp3_case_judge.py:180·213·353`, `jp3_dryrun_evidence.py:268`)은 sha가 고정된 입력이나 고정 설정 이름에 대한 비교다. 어긋나면 판정 불가로 가는 안전한 쪽이라 거짓 양성으로 본다.
- R-10 [E] `case-f`에 `*_X11` 행이 섞이면 `setting_defect`가 아니라 `not_judgeable`이다(`jp3_case_judge.py:229-231`). 종료 코드는 2로 같고 이름표만 4a-2 X11과 다르다.
- R-11 [E] T-JR-01 근거(junit, `j4a_remedy_99e9132b`):
  - full: 통과 7,516 / 실패 2 / skip 132 / xfail 0
  - main2: 667 / 0 / 9
  - gap: 57 / 1
  - 실패: `test_d8x_diag::test_rerun_gives_the_stored_command_hash`와 gap의 `test_chrono_t45_replay::test_rev7_regression_on_the_stage3_records`(55 ≠ 23). 둘 다 J4a-17 예외로 분류됐다(`jp3_impl_rereview_4a2.md:39`).
  - 13.10절 skip 3건은 junit_full에서 통과했다.
  - `junit_skips`: xfail·xpass 0, critical_skipped 0. 판정서에 "전부 통과"라고 쓰지 않고 예외 2건과 skip 9건(근거 시험 아님)을 적는다.
- R-12 [T] 시간 순서:
  - 4a-2~정오 1의 첫 커밋은 `1af65cf0`(2026-11-21 08:25:02)이고, 코드 `99e9132b`는 08:15:17이다.
  - j9·T-JR·건식·P-1 출력은 저장소·worktree 어디에도 없다(Glob 0).
  - 4a-2 1절과 4a-3 1절은 사후 정정이라고 명시돼 있다. 4a-4와 정오 1은 결과 전 정의다.
- R-13 [C] 건식 r79 키를 독립으로 재확인했다.
  - 06_analysis json·jsonl 3,276개를 다시 스캔했다(선정 당시 3,266개). r79 키 2,324, seed 최대 24다.
  - 생성 키 `L2|s25|g6|0|g6|G1+J1@FL|top|Fs0`는 어떤 결과의 `"key"` 값에도 없다. 문자열로는 문서 3개, 선정 파일 2개, 키 파일에만 있다. H-6 135키에도 없다.
  - 키 파일은 33바이트 CRLF이고, sha `1a79e02f…`가 고정값과 같다.
  - 이벤트 잡 R14/eps 0/offset 0.025는 선정 기록상 합집합 밖이다.
- R-14 [R] `run_v5 --list` 건조 실행(dynamics-dev) 결과: j9_cases 15, j9_case_f 15, j9_case_f_path 3, j9_t8 88(`--p3-hash-source` 고정 sha), j9_main 388. 명세 건수와 같다. 실행 뒤 worktree `git status` 출력은 비어 있었다.
- R-15 [I] 건식 명령의 출력 `dryrun_evidence/`는 CWD를 기준으로 worktree 루트 안에 생긴다. json은 ignore되지 않는다. `run_identity`가 `--untracked-files=no`라서 is_clean에는 영향이 없다(`d8x_record.py:348-352`). 다만 결과가 메인 checkout 밖에 남는다(M-2에서 처리).

## 규칙↔도구 대조표

| 규칙(원문 위치) | 도구(위치) | 판단 |
|---|---|---|
| 4a-3 2: T-JR-10/11 표본 22행(`p3_hash_jobs`), 정확히 22짝 | `jp3_tjr_judge.py:108,167-169`; `run_v5.py:346-362` | 일치 |
| 4a-3 3.1 A·B·기록 일치·C 기록, 저장 태그·rev 4 assert | `jp3_t8_rules.py:49-94`; `jp3_tjr_judge.py:220-241` | 일치(R-9 참고) |
| 4a-3 3.2 허용 경로 표 | `jp3_t8_rules.py:13-25` | 일치(키 이름 대조) |
| 4a-4 4: VB 기록이 누락·오류·다른 해시면 T-JR-10만 판정 불가 | `jp3_tjr_judge.py:196-204,259-270` | 일치 |
| 4a-4 5: 고정 sha(h10·main·H-6·base-judge sha·select·grid) | `jp3_fixed_inputs.py:11-34`; `jp3_tjr_judge.py:313,333,526-540`; `run_v5.py:651-661`; `jp3_case_judge.py:436-437` | 일치. `--stored-h6-judge`는 미대조(R-8) |
| 13.6 t8 경로의 정체성·B2 | 없음 | **불일치(M-4)** |
| 13.9 / 4a-3 4: 135짝, L2 1, L2만 pass→fail, READY 표, 새 FAULT, 결과 없는 짝은 판정 불가 | `jp3_tjr_judge.py:341-482` | 일치. 설정 대조가 없음(M-3) |
| 4a-3 4.4: VBJ0 base 증거 | `:376-387` | 일치 |
| 4a-4 6 자기 대조 기대표 | `:543-588` | 기대표와 코드는 일치. **실제 H-6에서는 반드시 실패(B-1)** |
| 정오 1 R-2: 기록, 종료 1 = 차이 | `:635-699` | 일치 |
| 4a-3 5.1 / 4a-4 1~3 / 정오 1: 합집합 밖, s25, 같은 실행기·환경, keys_file sha | `jp3_dryrun_evidence.py:143-246,264-350,398-419` | 일치(R-13) |
| 4a-3 5.2 F-A 경로: runs[0..2], 접두 해시, 10⁻⁹, 0.075 거부 | `jp3_case_judge.py:334-398` | 일치 |
| 13.3 P4-5a / 4a-1: +10.674 ± 0.05, X11 정체성, LSJ4 해시 | `jp3_case_judge.py:147-208` | 일치 |
| 13.8 F-A/B/E, B2 | `jp3_case_judge.py:225-331` | 일치(R-10) |
| 13.1 / 4a-1 / 4a-2 2·3: SUMS sha, CRLF, 판정 행 > 0, 클래스 읽기 > 0(rev 5), P4-2 사슬, P4-4 시드 | `jp3_baseline_compare.py:135-500` | 일치. P4-9는 키가 없으면 통과(M-5) |
| 13.2 판정 행 0 = 판정 불가 | `extend_start_bound.py:1870-1877`; `jp3_baseline_compare.py:462-463`; t12 `expected_judged_runs=1` | 일치. records만 예외(M-6) |
| 4a-2 3.4 T-JR-15 순 힘 "판정" | `jp3_tjr_judge.py:704-723`(기록만) | **확인 필요 1 / M-6** |
| 4a-2 B4 종료 0/1/2 | 도구는 0/1/2/3 | 종료 3이 규칙 표에 없음(M-7) |
| 5.5 T-JR-12 `dg3_keys.txt` | 저장소에 없음. 4a-3이 H-6 135키로 대체 | 키 입력 고정 필요(M-8) |

## 확인 필요
1. **T-JR-15 시드 순 힘**: 4a-2 3.4절("판정: 모든 행 ≤ 1 N")과 4a-2 B4("T-JR-13~15는 기록")가 다르다.
   - 판정이라면 `records`가 초과를 실패(종료 1)로 내야 한다(python-expert).
   - 기록이라면 3.4절이 P4-4·T-JR-18에만 적용된다는 문장이 덧붙임에 필요하다(control-expert).
2. **B-1 수정 시점**: 고친 뒤 새 커밋 하나로 (1)~(7)을 모두 돌릴지(권장), 아니면 (2)~(5)를 `99e9132b`에서 먼저 돌리고 판정 도구만 새 커밋에서 쓸지 정해야 한다. 재검토 4a4e1 2.6절은 worktree 커밋 하나를 "모든 실행·판정 도구"로 적었다.
3. **13.6절과 B2를 t8에도 적용할지**: 13.6절은 "판정 도구" 전반을, 4a-2 B2는 사례 F E 군, j9_cases E, T-JR-12 VBJ0을 명시한다. t8의 VBH·VBJ·VBJ0 줄도 포함하는지 정해야 한다(M-4).

## 위임 필요
- python-expert(worktree `z4369-jp3`):
  - B-1: `jp3_tjr_judge.py:376-387`에서 증거 검사를 436.9 설정 줄로 한정한다. `test_jp3_addendum_4a3.py:248`은 실제 H-6으로 `setting_defects == []`와 status pass까지 assert하게 바꾼다.
  - M-3: t12에서 new 줄 `v5_setting`·`rule_revision` = 5, VBJ base = VBJ0, base sha ≠ new sha를 검사한다.
  - M-4: t8의 VBH·VBJ에 `identity_problems`, VBH·VBJ·VBJ0에 B2 증거 검사, T-JR-11에 64자 검사를 넣는다.
  - M-5: `extend_start_bound.py:1862-1863`과 `jp3_baseline_compare.py:490`에서 키가 없으면 판정 불가로 한다.
  - M-6: `records`가 빈 입력을 판정 불가로 하고, 재생 보고 수·`judged: False`를 검사하게 한다. T-JR-15는 확인 필요 1에 따른다.
  - M-8: 새 쪽 판정 파일 생성 하위 명령을 둔다(L1 추출본 sha assert, 출력 sha 보고). VBJ에도 판정 파일 sha를 받는다.
  - R-7: `reference_extract`가 기존 파일을 덮어쓰지 않게 한다.
- control-expert: M-7 실행 실패 처리표와 확인 필요 1의 덧붙임 문안.
- 메인 세션: M-1·M-2 구체 명령 파일과 정체성 확인 절차, R-3 경로 기준 표기, R-6·R-7 FIXED_INPUTS 갱신.
- 위임 필요(python-expert): tools/verif 후보
  - `placeholder_scan`의 기본 패턴에 JSON 명령 필드의 `<name>` 꼴을 넣는 선택지. 입력은 prelaunch json, 출력은 자리표시 목록, 종료 0/1/2.
  - "고정 저장 입력이 판정 도구의 줄별 검사 키를 갖는지" 점검. 입력은 판정 도구가 요구하는 키 목록과 저장 파일, 출력은 키별 개수(값 없음), 종료 0/1/2. 이번에는 즉석 스크립트로 했다.

## 메인 세션 권고
- B-1·M-3~M-6·M-8을 고친 뒤 새 커밋을 고정(lock)하고, 이 감사의 좁은 재감사를 받는다. 대상은 B-1과 M 항목, `seal_check`·`ref_check`·`placeholder_scan`·`ps1_lint` 재실행이다.
- 그다음 P-1(저장 자료만: base-judge → FIXED_INPUTS 갱신·커밋 → R-2 → t12-selfcheck)을 메인 세션이 돌린다.
- 각 실행 출력 폴더마다 판정 전에 `baseline_check.py identity --expect-commit <실행 커밋> --mtime`를 돌린다.
- 판정서 커밋 직전에 판정 후 감사를 받는다. `judgement_checklist`, `seal_check --quoted --hash-files`, 재집계를 본다.

## 검사하지 못한 것
- `handoff_leak.py`: 경로 2(B5) 넘김 문서가 아직 없어 돌릴 대상이 없다.
- `log_errors.py`: 러너 로그가 없다.
- `ps1_lint.py`: 실행 스크립트(.ps1)가 없다(M-2).
- `jp3_case_replay.py`(C·D)와 `t4h_replay`의 rev 4 → rev 5 재생 경로는 정체성 유무만 봤다. 동작은 따라가지 않았다.
- P-1a `base-judge`·R-2·self-check, 건식 실행, 사례 재생은 실행 금지라 돌리지 않았다. B-1은 코드 경로와 저장 H-6의 키 개수로 확정했다.
- 재검토 4a4e1의 J4a 이전 항목(R5-6·R5-7 구현 정합)은 이번 범위 밖이다.
- C축 재집계: 판정 대상 결과가 없다. 건식 키 선정만 독립으로 재확인했다(R-13).

## 실행한 검증
- python-dev(`C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`, `MKL_THREADING_LAYER=TBB`):
  - `seal_check.py --repo … "06_analysis/02_control/j_p3_cause/jp3_remedy_spec*.md" --sums baseline_221456d/SHA256SUMS --rev HEAD --check-tracked --code <worktree coupled>`: 종료 1. seal_missing 1(4a-1), cited_ignored_tracked 18(info). 6판 중 5판 raw 일치, error 0.
  - `baseline_check.py sums … --rev HEAD`: 종료 1(sums_crlf warning). 불일치·누락·목록 밖 0.
  - `baseline_check.py identity … --expect-commit 221456d`: 종료 0.
  - `ref_check.py --rev HEAD` / `--rev 99e9132b`(4a-3·4a-4·정오 1): ref_missing 다수. 모두 git 밖 저장 파일의 줄인 경로 표기였다. FIXED_INPUTS 31개 전체 경로의 존재·sha는 즉석 스크립트로 31/31 확인했다.
  - `gate_scan.py`(jp3_* 6개 + extend_start_bound.py): warning 6.
  - `junit_skips.py`(junit_full·main2·gap): gap에서 test_failed 1과 critical_absent(정규식 불일치, 정보성)가 나왔다. 그 밖은 0.
  - `placeholder_scan.py`: 기본 패턴 0. `<…>` 패턴 26.
  - 즉석 스크립트 `fixed_check.py`(FIXED_INPUTS·T4h SUMS·manifest), `junit_pick.py`, `h6_keys.py`(키가 있는지만), `sel_check.py`(건식 키 재스캔).
- dynamics-dev(`conda run -n dynamics-dev python -I -B`, `PYTHONDONTWRITEBYTECODE=1`, CWD worktree): `run_v5.py <batch> --list` 5회. 실행 뒤 worktree `git status --porcelain`은 비어 있었다. worktree의 `__pycache__`는 2026-11-20 22:32 것이 남아 있었고, 이 감사에서 만든 것이 아니다.
- git 조회: `ls-files --error-unmatch`, `ls-tree`, `check-ignore -v --no-index`, `check-attr text eol`, `log --diff-filter=A`, `worktree list --porcelain`, `rev-parse`.
- 최종 판정 직전에 `jp3_tjr_judge.py:380`, `j_p3_inputs.py:73`, `test_jp3_addendum_4a3.py:248`을 다시 Grep했고, worktree HEAD `99e9132b`(깨끗함)와 master `1af65cf0`도 다시 확인했다. 바뀐 것은 없다.
- 만든 뒤 지운 파일: scratchpad `verif-jp3-prelaunch\`(guard_inputs.txt, guard.json, fixed_check.py, junit_pick.py, h6_keys.py, sel_check.py). 폴더째 지웠고 Test-Path는 False다.
- 메모리: `agent-memory\verif-protocol-auditor\audit_pitfalls.md`에 한 항목을 더했다(저장 파일 자기 대조 vs 나중에 더한 줄별 검사, 시험의 문제 종류 일부만 assert). `MEMORY.md` 색인도 갱신했다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec.md 8be9de22…, jp3_remedy_spec.md.sha256 174e6fb7…, jp3_remedy_spec_addendum_4a1.md 4b122dd0…, jp3_remedy_spec_addendum_4a2.md 2f3e36bd…, jp3_remedy_spec_addendum_4a2.md.sha256 19063b36…, jp3_remedy_spec_addendum_4a3.md f001383a…, jp3_remedy_spec_addendum_4a3.md.sha256 3045bb46…, jp3_remedy_spec_addendum_4a4.md 67380b10…, jp3_remedy_spec_addendum_4a4.md.sha256 c50c5aac…, jp3_remedy_spec_addendum_4a4_erratum1.md 1ccbe526…, jp3_remedy_spec_addendum_4a4_erratum1.md.sha256 27255e69…, SHA256SUMS 197ac14e…, FIXED_INPUTS.SHA256SUMS f35fa862…, h10_reuse_rerun_t4h.SHA256SUMS 3d0ed49a…, h6_dg3_v4on_t4h.SHA256SUMS c426f518…, jp3_prelaunch_h6_selfcheck.json b41e71ae…, dryrun_selection.json c1c94ce5…, SHA256SUMS db2a2d31…, dryrun_selection_r79_key.txt 1a79e02f…, SHA256SUMS 8235c5ce…, SHA256SUMS 82b6a851…, SHA256SUMS dba494a8…, jp3_impl_rereview_4a4e1.md 634357df…, main.jsonl 9ad74990…, h10_reuse_rerun.jsonl ce526b1f…, h6_dg3_v4on.json ea0ab94c…, grid_r67_top.json 7160f9f1…, h6_r79_judge.json d95627ac…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음

---

## 메인 세션 덧붙임: 사용자 결정(2026-11-21)

- 확인 필요 1: T-JR-15 시드 순 힘 ≤ 1 N은 **판정**이다(초과 = 실패, 종료 1). 봉인 5.5절 합격 칸·4a-2 3.4절을 따르고, 4a-2 B4 표의 "기록"은 덧붙임 4a-5에서 정정한다.
- 확인 필요 2: B-1·M 항목을 고친 **새 커밋 하나로 (1)~(7) 전부** 실행·판정한다. 새 커밋을 lock하고 좁은 재감사 뒤 고정 목록을 다시 만든다.
- 확인 필요 3: 13.6절 정체성 검사와 B2 증거 검사를 t8의 VBH·VBJ·VBJ0 줄에도 **적용**하고, T-JR-11에 64자 해시 검사를 넣는다.
