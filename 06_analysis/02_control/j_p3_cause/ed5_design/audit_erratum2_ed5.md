# 판 5 정오 2 봉인 전 감사(verif-protocol-auditor, 2026-11-22) — hand-back 원문

## 감사 요약(판 5 정오 2, 봉인 전)
- **결론: 차단 1건, 경고 6건입니다.** 차단은 정오 2-1이 "기록"이라고 정한 등급 전이를 구현이 판정 경로에 묶어 둔 것입니다. 정오 문장 한 줄과 구현 수정 두 곳을 마친 뒤 봉인하기를 권합니다.
- 대상:
  - 정오 2 `jp3_remedy_spec_v5_erratum2.md`: sha `841386ef`, CRLF 0, `j_p3_cause/** -text`
  - 구현: worktree `z4369-ed5`의 `45b073ad`(2026-11-22 07:59), 작업 트리 깨끗함
  - 탐침 기록: `ed5_design/probes/probes_ed5.json`
- 정오 2가 인용한 정오 1 봉인본 sha `4721352e`는 파일과 `.sha256` 모두와 같습니다.
- 본 결과: 판정 값은 보지 않았습니다. `j9_runs`는 최상위 폴더 이름만 봤습니다.

## 차단

**F-1 [E·R] 기록용인 등급 전이가 12b 판정을 막거나, 실패를 판정 불가로 가립니다**
- 근거 1, 실행 순서:
  - `step6c_vbk.ps1` 49~60행은 12b 판정(`judge`)보다 먼저 팔마다 `grade-judge`를 `Invoke-Judge`로 부릅니다.
  - `Invoke-Judge`는 종료 0이 아니면 단계를 멈춥니다(`run_steps/common.ps1` 304~308행, ContinueCodes 기본 0).
  - `grade-judge`는 L1 기준에 문제가 하나라도 있으면 판정 불가(종료 2)로 끝납니다(`jp3_12b_judge.py` 817~821행). 문제의 예: 오류 줄 하나, 줄 수와 키 수 불일치, `rod_model` 다름.
- 근거 2, 판정 도구 안:
  - `grade_transitions`는 등급 판정 파일의 sha가 다르면 `problems.not_judgeable`에 넣습니다(730~733행).
  - `Problems.status()`는 not_judgeable을 failed보다 먼저 봅니다(157~162행).
  - 그런데 `grade_transitions`는 판정 결과(`found`)를 낸 뒤에 불립니다(996~1003행).
- 정오 2-1은 "등급 전이는 판정이 아니라 기록이다(6.3.7)"라고 적습니다.
- 실패 시나리오:
  - L1 기준 실행의 줄 하나가 오류이면, 새 FAULT·READY 실패가 있어도 12b가 판정 불가(종료 2)가 됩니다.
  - 4a-5 5절에서 종료 2는 다시 돌릴 수 있습니다. 결과를 본 실패가 재실행 경로로 넘어갑니다.
  - 등급 판정 파일 sha가 어긋나는 경우도 같습니다.
- 권고:
  - 정오 2-1에 문장을 더합니다: "등급 전이 입력(L1 기준, grade-judge 파일)의 결함은 등급 전이 기록을 '계산 안 됨'과 그 사유로 공개할 뿐, 12b 판정 상태와 종료 코드를 바꾸지 않는다."
  - python-expert 수정:
    - `step6c_vbk.ps1`: 판정을 먼저 돌리거나, `grade-judge`의 종료 2를 ContinueCodes에 넣습니다.
    - `grade_transitions`: 문제를 `not_judgeable`이 아니라 기록용 문제 목록에 넣습니다.
  - 시험: "실패 + 등급 입력 결함 → 종료 1"을 추가합니다.

## 경고
1. **실행 순서의 문장이 서로 다릅니다.**
   - 메인 전달 순서는 "`-Part list` → 커밋"입니다.
   - `prelaunch_ed5.ps1` 머리 주석은 "앞 부분·L1 출력·`common_ed5.ps1`을 메인이 커밋한 뒤 `-Part list`"이고, 단계들은 목록이 추적되어야 시작합니다.
   - 실제 순서는 dry → l1keys → step_l1ref → x11 → (메인 커밋) → list → (목록 커밋) → step0_cdry로 보입니다.
   - `common_ed5.ps1` 7~11행 주석은 옛 스크립트 이름(`prelaunch_dry_select.ps1` 등)과 "목록이 추적되어야 시작"만 적고, l1ref 예외를 적지 않습니다.
   - 정오 2나 실행 전 감사 기록에 순서를 고정하기를 권합니다.
2. **L1 기준 실행을 목록 대조 없이 4a식 시작 검사만으로 돌리는 것은 건전하다고 봅니다.** 근거:
   - 시작 검사가 실행 커밋, 깨끗한 트리, 4a 고정 입력(사례 원본 sha 포함)을 봅니다(`Assert-PrelaunchCommit`, `Initialize-Step`).
   - 키 파일은 고정 원본에서 결정적으로 만들어지고 덮어쓰기를 거부합니다(`jp3_12b_l1_keys.py` 76~88행).
   - 두 L1 출력과 키 파일은 목록에 들어가고, `grade-judge`가 sha·설정·`rod_model`·키 수를 대조합니다.
   - 모두 12b·c 건식 출력보다 앞섭니다.
   - 보강: "12b·c 건식 출력이 생긴 뒤에는 L1 기준을 다시 만들지 않는다. 재시도는 4a-5 5절과 `l1ref.done`이 가리키는 시도를 따른다"는 문장을 정오 2-1에 더하기를 권합니다.
3. **목록 항목에 정오 2의 `.sha256`이 없습니다.** `fixed_inputs_entries.txt`에 정오 1은 본문과 `.sha256`이 모두 있는데, 정오 2는 본문만 있습니다. 봉인 뒤 추가합니다.
4. [추정] **P-1 대 78fd5d2d 대조(2-4)가 거짓 멈춤을 낼 수 있습니다.**
   - `base-judge` 판정 파일의 sha가 같아야 하는데, 78fd5d2d 이후 판정 도구 코드가 바뀌었습니다(d3c6c57e, 판 5).
   - 출력에 코드에 따라 달라지는 내용(도구 sha, 설정 목록 등)이 들어 있으면 sha가 달라집니다.
   - 안전 쪽(멈춤)이라 차단은 아닙니다. python-expert에 출력 내용이 코드와 무관한지 확인받기를 권합니다.
   - 대조할 시도는 `.done` 표지로 고르므로(`jp3_rerun_match.py` 123~133행) p1_a1·a2가 섞일 걱정은 없습니다.
5. [추정] **L1 기준 키가 j9_main 줄과 겹칠 수 있습니다.** 준비 단계에서 돌리는 L1 기준 키 `L1|s0|…`(VBJ)가 j9_main(6.5)이 같은 커밋에서 돌릴 h8 VBJ L1 줄과 같다면, 결정적 재실행이라 그 줄의 값을 미리 보는 셈입니다. j9_main에서 L1 줄이 판정 줄이 아니라 등급 기준일 뿐인지 확인을 권합니다.
6. **2-3절 표현이 구현과 조금 다릅니다.** "추가 스캔(`-ScanExtra`)은 run worktree의 `05_tests` 하나다"라고 적었지만, 구현은 `05_tests`를 항상 스캔하고 `-ScanExtra`로 폴더를 더 받습니다. 문장을 맞추면 됩니다.

## 확인한 항목
- **(T) 결과 전**:
  - `j9_runs/` 최상위는 판 4a 커밋 넷뿐입니다(78fd5d2d·b51ed6e1·d3c6c57e·fa997f4c). 판 5 실행 커밋 폴더와 l1ref 출력은 없습니다.
  - worktree에 커밋 안 된 변경이 없습니다.
- **(E) `ungraded`**: 그 자체는 기록입니다. 개수·원인만 공개하고 판정 상태에 들어가지 않습니다(736~759행). 문제는 F-1의 입력 결함 경로뿐입니다.
- **(I) 탐침 기록**:
  - 형식 `{"results":[{key, setting, commit, purpose, output}]}`이 정오 2-3과 같고, 세 줄도 2-3과 같습니다.
  - 키에 `cand=` 접두가 없지만 스캔 정규식이 접두를 선택으로 받으므로 문제없습니다.
- **(I) 건식 생성 키**:
  - 생성 seed는 25에서 시작하고, 같은 키가 스캔에 있을 때만 올라갑니다(`jp3_dryrun_evidence.py` 119·215~216·326행).
  - `seed_max`는 기록값일 뿐입니다. 탐침의 `s30` 키 때문에 24가 30으로 바뀌어도 생성 키는 `s25` 그대로입니다.
  - 시험 수정(`test_jp3_addendum_4a4.py` 213~217행)은 이 점과 맞습니다.
- **(R) 그 밖**:
  - L1 키 꼴 `L1|s0|<harness>|<index>|<inner>`, 처음 나온 순서, 사례 원본의 L1 작업인지 확인하는 동작이 2-1과 같습니다.
  - 팔별 L1 설정(VBK0 → VBJ0, VBK → VBJ, plant_truth)도 2-1과 같습니다(772~806행).
  - L1 출력 json은 git 무시 규칙에 걸리지 않습니다. T4h npz는 무시되지만 grade-judge는 json만 읽습니다.

## 실행한 검증
- sha·CRLF 확인, git 조회(`log`, `show --stat`, `status`, `check-ignore -v`), `j9_runs` 최상위 목록.
- 정오 2, 탐침 기록, `step_l1ref.ps1`, `prelaunch_ed5.ps1`, `fixed_inputs_entries.txt`, `common_ed5.ps1` 머리, `jp3_12b_l1_keys.py`, `jp3_12b_judge.py`(grade·status 부분), `jp3_rerun_match.py`·`jp3_dryrun_evidence.py`·`step6c_vbk.ps1`·`common.ps1`의 해당 줄을 읽었습니다.
- 만든 파일은 없습니다. 메모리 `C:\Users\jinbeom\.claude\agent-memory\verif-protocol-auditor\audit_pitfalls.md`에 한 줄을 더했습니다(기록 항목이 판정을 막거나 가리는 경로).
- 사용한 스킬: 없음


---

# 재감사 기록(2026-11-22, verif-protocol-auditor)

메인 주: 재감사 hand-back 원문 3건은 이 세션 대화 기록에 남아 있다. 아래에는 각 원문의 판정 결론과 차단·경고 항목을 그대로 적는다. 결정과 정오는 이 절 뒤에 덧붙인다.

## 재감사 1(정오 2 sha 472b792e, 구현 3e30a408)
- 결론: 차단 2건(G-1, G-2). 앞 감사의 F-1과 경고 1·2·4·5·6은 닫힘. 경고 3은 봉인 뒤 처리.
- G-1: 2-1 38행의 "FIXED_INPUTS의 L1 기준 sha 집합(12b 둘, T-JR-12a 둘)"을 고쳐야 함. T-JR-12a L1은 단계 (6)에서 생기므로 목록에 넣을 수 없음. 제안: "12b 둘(FIXED_INPUTS sha) + T-JR-12a 둘(단계 (6) 폴더, dg3.done이 가리키는 시도의 실제 파일 sha)".
- G-2: j9_main은 판 5 범위(원판 0절, 6.5, 8절 5)인데 run_steps_ed5에 단계 스크립트가 없음. 고정 목록이 run_steps_ed5/*.ps1을 글롭으로 담으므로 목록 뒤에 추가하면 모든 단계가 멈춤. (가) 목록 전 스크립트 추가(권장) 또는 (나) 별도 묶음 문장.
- 경고 1: p1_content가 종료 코드를 대조하지 않는 것은 4a-6 4절 (1)행 취지에 맞음. 78fd5d2d base-judge-compare 종료 코드 확인 권고.
- 경고 2: 단계 (6) 기록 도구(l1_overlap, l1_hash_record)가 기본값으로 불려 실패 시 단계 (7)을 막음.
- 경고 3: grade_transitions 계산 중 예외가 판정 종료 코드를 바꿈.
- 경고 4: 새 경로에 빈 집합·0건 통과 없음.
- 경고 5: 절 번호 순서.

## 재감사 2(정오 2 sha a9430c2b, 구현 4dcab9ef)
- 결론: 차단 3건(H-1~H-3, 모두 jp3_j9main_judge.py). G-1·G-2와 경고 2·3 닫힘. 기록 묶음 T-CK·DROPOUT은 판정 경로를 막지 않음.
- H-1 [E]: r15_worsening의 "판정 불가"·"no R15 pair"가 _status에서 보이지 않아 통과 처리됨.
- H-2 [I·R]: j9_main 판정이 rev 6 정체성을 확인하지 않음(rev 5 줄 혼입 시 통과 가능).
- H-3 [E·R]: 기준선 실패 기록이 R15에만 있어 2-9.3 210행과 맞지 않음. (가) 전 행 확대(권장) 또는 (나) 문장 한정.
- 경고 1: own_item_failures 조건은 대체로 맞음. J3 D-11 강체 기록 분기 누락, J8·J9 전제 확인 필요.
- 경고 2: 판정 불가가 실패보다 앞섬(종료 2 재실행 경로).
- 경고 3: L-c, S8 정지값의 조용한 건너뜀.
- 경고 4: V0 표본 판정이 정체성 확인보다 먼저 돎.
- 경고 5: rev 6 통과 경로 시험 없음.
- 경고 6: 2-7.2 낡은 목록, step8 비용 주석.

## 재감사 3(정오 2 sha 55e87c6e, 구현 a0e06a8e)
- 결론: **정오 2 문안은 봉인 가능(문안 차단 0)**. 실행 전 구현 차단 1건(K-1).
- H-1·H-2·H-3, 경고 3 닫힘. 2-10 상태 순서가 12b Problems, jp3_baseline_compare.Problems(T8·사례·T-JR), P5-1, j9_main status_basis에 들어감. 12b J-P3 H-7은 has_judged_breach로 직접 읽음.
- K-1 [E·R] 실행 전 차단: T-JR-12a VBJ 줄의 J-P3 H-7이 기록으로 처리되어 멈추지 않음(step6_dg3.ps1 81~84행 ContinueCodes @(0,1), RecordCodeTools의 tool:t12_VBJ, _dg3_j_p3가 결합 상태만 봄). 원판 6.2가 이미 판정으로 정하므로 정오 수정 아님.
- 경고 1: 2-10.1 (5)의 _worse_status 문장이 구현과 다름(봉인 전 수정 권고).
- 경고 2: 12b 판정 파일 jp3.status 혼동 가능.
- 경고 3: skip 6건(test_chrono_t45_replay 5, test_las_off_chrono 1)은 봉인 차단 아님, 실행 전 확인 항목. test_x10_rod_fault 2건(X10_BASE_ROOT 없음)은 P5-3 대상이라 실행 전 skip 0 통과 필요.

## 결정·조치(메인)
- G-2: 사용자 결정 (가) 지금 단계 스크립트 추가(2026-11-22).
- j9_main 범위: 사용자 결정 (가) H-10 본 부분만(2026-11-22).
- H-3: 2-9.3 문장대로 (가) 전 행 확대로 구현.
- 경고 1(재감사 3)·경고 2: control이 정오 2에 반영(최종 sha 639c54e9).
- 정오 2 봉인: sha256 639c54e98db2ca21ef67c6795ac0856675d8e938f63601a76c11fa6d49383790(2026-11-22).
- K-1, 재감사 3 경고 2(필드)·3(skip): python-expert에 넘김. 실행 전 감사에서 닫힘을 확인한다.