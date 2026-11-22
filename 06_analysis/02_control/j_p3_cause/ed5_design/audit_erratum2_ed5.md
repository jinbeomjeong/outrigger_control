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

---

# 재감사 hand-back 원문(대화 기록 jsonl에서 추출, 2026-11-22 메인)

위 '재감사 기록' 절은 메인이 정리한 요약이다. 아래가 hand-back 원문 전체다(하네스 들여쓰기만 제거).

## 원문 1

<!-- timestamp 2026-11-22T00:20:02.478Z -->
## 감사 요약(정오 2 봉인 전 재감사)
**봉인 전에 고칠 차단이 2건 남았습니다(G-1·G-2).** 둘 다 정오 문장 한두 줄로 닫힙니다. 앞 감사의 F-1과 경고 1·2·4·5·6은 닫혔고, 경고 3은 봉인 뒤 처리로 남아 있습니다.

- 대상: 정오 2 `jp3_remedy_spec_v5_erratum2.md`(sha `472b792e`, CRLF 0, `-text`), 구현 worktree `z4369-ed5`의 `3e30a408`(그 위 `d681f724`), 작업 트리 깨끗함.
- 시점: 결과 전입니다. `j9_runs/` 최상위에는 판 4a 커밋 넷만 있고, 판 5 실행 커밋 폴더는 없습니다.
- 메인이 전한 시험 648건 통과·skip 0은 제가 직접 돌려 확인하지 않았습니다.
- 본 결과: 없습니다. `j9_runs` 안은 Grep하지 않았습니다.

## 앞 감사 항목
- **F-1(기록용 등급 전이가 판정을 막거나 실패를 가림): 닫혔습니다.**
  - 정오: 2-1 27~30행이 입력 결함과 종료 3을 기록으로만 다루고 판정 상태·종료 코드를 바꾸지 않는다고 적습니다.
  - 단계 스크립트: `step6c_vbk.ps1`이 `grade-judge`를 `-ContinueCodes @(0,2,3)`로 부르고, 파일이 없으면 `--<arm>-grade-judge-exit`를 넘깁니다.
  - 판정 도구: `grade_input_problems`가 결함을 `computed: false`로만 남기고 `problems`에 넣지 않습니다(`jp3_12b_judge.py` 723~801행).
- **경고 1(실행 순서): 닫혔습니다.** 2-6에 순서가 있고, `common_ed5.ps1` 머리 주석도 같은 순서와 l1ref 예외를 적습니다.
- **경고 2(L1 기준 재생성 금지): 닫혔습니다.** 2-1 23행과 2-6 102행.
- **경고 3(정오 2 `.sha256`의 목록 항목): 봉인 뒤 처리입니다.** 2-7에 메인 몫으로 적혀 있고, 지금 목록에는 아직 없습니다.
- **경고 4(P-1 거짓 멈춤): 닫혔습니다.**
  - 2-4에 폐포 검사와 내용 경로가 있습니다.
  - 78fd5d2d에서 `3e30a408`까지 `r79_sensor_judge.py`·`h8_noise_judge_4368.py`의 diff가 비어 있음을 다시 확인했습니다.
- **경고 5(L1 기준 줄과 판정 줄 겹침): 문장과 줄 수준 거부는 닫혔습니다.** J-P3 입력에 L1 줄이 있으면 `setting_defect`가 됩니다(`j_p3_inputs.py`). 파일 수준 검사는 G-2를 보십시오.
- **경고 6(2-3 표현): 닫혔습니다.** 2-3 55행.
- 2-8의 T-JR-12a L1 키 파일 `l1_keys_d3c6c57e.json`은 sha `eea8ed0d…`가 실측과 같고, 생성 명령 파일과 함께 추적됩니다.

## 차단

**G-1(python 확인 필요 1에 대한 답): 정오 문장을 구현에 맞춰야 합니다.**
- 2-1 38행은 "FIXED_INPUTS의 L1 기준 파일 sha 집합(12b 두 개, T-JR-12a 두 개)"이라고 적습니다.
- 그런데 T-JR-12a의 L1 실행은 단계 (6)에서 만들어지므로, 목록(2-6의 6번 순서)보다 늦습니다. 목록에 넣을 수 없습니다.
- 구현(`Assert-NoL1Inputs`, `Get-StepFolder 'dg3'`)처럼 단계 폴더의 실제 파일을 쓰는 쪽이 맞습니다.
- 그대로 봉인하면 봉인 문장이 할 수 없는 일을 요구하게 됩니다.
- 제안 문장: "L1 기준 파일 sha 집합 = 12b 둘(`FIXED_INPUTS`의 sha)과 T-JR-12a 둘(단계 (6) 폴더, `dg3.done`이 가리키는 시도의 실제 파일 sha)."

**G-2(python 확인 필요 2에 대한 답): j9_main 처리 방식을 봉인 전에 정해야 합니다.**
- j9_main은 판 5 실행 범위입니다. 근거는 원판 0절 "재실행 … (7)과 j9_main까지", 6.5, 8절 5입니다.
- 그런데 `run_steps_ed5`에 j9_main 단계 스크립트가 없습니다. 2-6 순서도 9번에서 "(1)~(7)"로 끝납니다. 파일 수준 L1 검사(`Assert-NoL1Inputs`, `common_ed5.ps1` 166~177행)도 부르는 곳이 없습니다.
- 고정 목록은 `run_steps_ed5/*.ps1`를 글롭으로 담습니다. 목록을 만든 뒤 이 폴더에 j9_main 스크립트를 더하면 "목록과 파일이 같아야 시작" 검사에 걸려 이후 모든 단계가 멈춥니다. 그때 가서 해석으로 우회하게 됩니다.
- 단계 (1)~(7)의 시작 자체를 막는 차단은 아닙니다. 다만 `-Part list` 전에 둘 가운데 하나를 정해야 합니다.
  - (가) j9_main 단계 스크립트(`Assert-NoL1Inputs` 호출 포함)를 목록 전에 `run_steps_ed5`에 넣고 실행 전 감사를 받는다. 권장합니다.
  - (나) 2-6에 다음 문장을 넣는다: "j9_main은 T-JR-12b 통과 뒤 같은 실행 커밋에서 별도 단계 폴더·별도 고정 목록·별도 실행 전 감사로 돌린다. `run_steps_ed5`에는 더하지 않는다."

## 경고
1. **`p1_content`가 종료 코드를 대조하지 않는 것은 4a-6 4절 (1)행의 취지에 맞습니다.**
   - 이유: (1)행의 목적은 저장 자료만 읽는 P-1이 다시 돌려도 같게 나오는지 보는 것입니다. 판정 도구가 바뀐 판 5에서는 옛 종료 코드와 같은지가 아니라 출력 내용(정렬한 `runs`·`table`·`unmatched`·`errors`, L1 추출본)과 고정 기대값으로 보는 편이 그 목적에 맞습니다.
   - `t12-selfcheck`는 종료 0이 아니면 멈추고(`Invoke-Judge` 기본값), `base-judge-compare`는 0을 요구합니다(`step1_p1.ps1`).
   - 확인 필요: 78fd5d2d에서 `base-judge-compare` 종료 코드가 0이었는지 봐 주십시오. 4a에서는 이 코드가 기록 도구(`RecordCodeTools`)였으므로, 1이었다면 판 5의 "0 필수"는 4a보다 엄격한 조건이 되어 거짓 멈춤을 낼 수 있습니다. 멈춤 쪽이라 안전하지만 미리 확인해 두십시오.
2. **단계 (6)의 기록 도구가 실패하면 판정 단계 (7)이 막힙니다.**
   - `l1_overlap`과 `l1_hash_record`가 기본값(종료 0만 계속)으로 불립니다(`step6_dg3.ps1` 끝부분).
   - `l1_overlap`은 2-1 39행이 정한 기록인데, 종료 2(L1 파일 없음)가 나면 단계 (6)이 멈추고 `dg3.done`이 생기지 않습니다. 단계 (7)(`step7_records.ps1`은 `dg3`를 요구)이 시작하지 못합니다. F-1과 같은 꼴입니다.
   - 권고: `-ContinueCodes @(0,2,3)`로 바꾸고 "계산 안 됨"을 기록하게 합니다. `l1_hash_record`(4a-8 4.5)가 멈춤 항목인지 기록 항목인지도 4a-8 원문으로 확인합니다.
3. **등급 전이 계산 중 예외가 나면 판정 종료 코드가 바뀝니다.**
   - `grade_transitions`는 입력 검사만 기록으로 돌리고, 계산 자체(`h8.grade_lines` 등)는 try로 감싸지 않습니다. 그 안에서 예외가 나면 12b 판정 전체가 종료 3이 됩니다.
   - 2-1 27행("판정 상태와 종료 코드는 바꾸지 않는다")에 맞게 예외도 `computed: false`로 받게 하기를 권합니다(python-expert).
4. **새 경로에서 빈 집합이나 0건으로 통과하는 곳은 없습니다.**
   - 줄 수준 L1 거부는 멈춤 쪽입니다.
   - `l1_overlap`은 명령 해시가 없으면 "다름"으로 셉니다.
   - 폐포 검사의 종료 2·3은 멈춥니다.
   - 내용 경로에서 한쪽에만 항목이 없으면 비교가 달라져 멈춥니다.
   - 판정 행 0과 기회 짝 0은 판정 불가입니다(1083·997행).
5. **정보: 절 번호가 2-6 → 2-8 → 2-7 순서입니다.** 봉인 전에 정리하면 인용이 쉽습니다.

## 실행한 검증
- sha·CRLF 확인, `git log`/`git diff --stat`·`git diff`(`45b073ad..3e30a408`, 78fd5d2d 대비 판정 코드 세 파일), `ls-files --error-unmatch`, `j9_runs` 최상위 목록.
- 정오 2 전문과 다음 파일의 해당 부분을 읽었습니다: `step6c_vbk.ps1`, `step1_p1.ps1`, `step6_dg3.ps1`, `common_ed5.ps1`, `jp3_12b_judge.py`(grade·l1-overlap), `jp3_rerun_match.py`(`p1_content`), `j_p3_inputs.py`(L1 거부), 단계 의존 목록, `RecordCodeTools`.
- 만든 파일과 원본 쓰기는 없습니다. 사용한 스킬: 없음

## 원문 2

<!-- timestamp 2026-11-22T01:42:19.126Z -->
## 감사 요약(정오 2 봉인 직전 재감사)
**봉인 전에 고칠 차단이 3건 남았습니다(H-1~H-3).** 셋 다 j9_main 판정 도구 `jp3_j9main_judge.py`에 있고, 둘은 판정 결과가 실패를 숨기는 쪽으로 갈 수 있습니다. 앞 재감사의 G-1·G-2와 경고 2·3은 닫혔습니다.

- 대상: 정오 2 `jp3_remedy_spec_v5_erratum2.md`(sha `a9430c2b`, CRLF 0), 구현 worktree `z4369-ed5`의 `4dcab9ef`(작업 트리 깨끗함).
- 시점: 결과 전입니다. `j9_runs/`에는 판 4a 커밋 넷만 있습니다.
- 메인이 전한 시험 664건 통과는 제가 직접 돌려 확인하지 않았습니다.
- 본 결과: 없습니다.

## 앞 항목
- **G-1(L1 기준 sha 집합): 닫혔습니다.**
  - 정오 2-7.1 133행: 12b 둘은 목록 sha, T-JR-12a 둘은 `dg3.done`이 가리키는 시도의 실제 파일입니다.
  - `common_ed5.ps1` `Assert-NoL1Inputs`(187~203행)도 같고, `dg3.done`이나 파일이 없으면 종료 2로 멈춥니다.
- **G-2(j9_main 단계): 닫혔습니다.**
  - 2-6의 10번 순서와 2-7.1이 있습니다.
  - `step8_j9main.ps1`이 다음을 합니다:
    - 선행 단계 9개 확인
    - 12b 판정 파일의 sha·`status pass`·`exit 0` 대조(29~43행)
    - V0 표본 키 파일 sha 대조
    - `Assert-NoL1Inputs`, 판정
  - 12b 판정 도구는 `exit`를 기록하고(1179행), `step6c`는 `judge_file`·`judge_sha256`를 표지에 남깁니다.
- **경고 2(단계 6의 기록 도구가 단계 7을 막음): 닫혔습니다.** `l1_hash_record`·`l1_overlap`을 `Invoke-RecordTool`로 부릅니다.
- **경고 3(등급 전이 계산 중 예외): 닫혔습니다.** `grade_transitions` 전체를 try로 감싸, 예외가 나면 `computed: false`로 남깁니다.
- **기록 묶음 T-CK·DROPOUT: 판정 경로를 막지 않습니다.**
  - `step7b_ckdrop`은 `records` 뒤에 돌고, 기록 도구는 `Invoke-RecordTool`로 부릅니다.
  - `step8`의 선행 목록에 `ckdrop`이 없습니다.
  - seed 80·81은 x11 스캔보다 늦게 만들어지므로 12b seed와 상관이 없습니다.

## 차단

**H-1 [E] R15 "나빠짐" 판정이 판정 불가일 때 통과로 처리됩니다**
- 근거: `r15_worsening`(430~449행)은 짝은 있는데 J2 값이 없으면 `state: "판정 불가"`와 `failures: []`를 돌려줍니다. 짝이 없으면 `"no R15 pair"`입니다. `_status`(354~365행)는 이 상태를 보지 않습니다.
- 실패 시나리오: R15 J2 값이 비면(None) 2-9.3이 유일하게 판정하는 R15 항목이 비어서 `pass`가 됩니다. j9_main 행은 `check_rows`가 모두 있다고 보장하므로, 정상이라면 짝은 있어야 합니다.
- 권고: 두 상태를 모두 `not_judgeable_items`에 넣고, 그 시험을 추가합니다(python-expert).

**H-2 [I·R] j9_main 판정이 rev 6 정체성을 확인하지 않습니다**
- 근거:
  - 2-7.1 141행은 "rev 5 줄이 섞이면 `setting_defect`"이고, 130행은 VBJ·LSJ가 rev 6(태그 기저 `final_C4G2_P3W`)이라고 적습니다.
  - `jp3_j9main_judge.py`는 줄의 태그 revision을 그대로 `REVISION_KEY`로 넘길 뿐(263~287행), 6인지 보지 않습니다.
  - `j_p3_over_rows`(`j_p3_inputs.py` 191~213행)는 revision 5·6을 따로 판정하고, 섞여도 `setting_defect`로 만들지 않습니다.
  - `check_rows`도 태그를 보지 않습니다.
- 실패 시나리오: 실수로 rev 5 VBJ·LSJ 줄이 j9_main에 들어오면 rev 5 규칙으로 판정되어 통과할 수 있습니다. 12b는 태그와 `rule_revision` 6을 확인하는데 j9_main에는 없는 비대칭입니다.
- 권고: VBJ·LSJ 모든 줄에서 다음을 요구하고, 아니면 `setting_defect`로 둡니다. 시험도 추가합니다.
  - `extend_start_revision_of_tag(tag) == 6`
  - 줄의 `run_extend_start_revision == 6`
  - `extend_bound_check.rule_revision == 6`

**H-3 [E·R](python 확인 요청 1에 대한 답) 기준선 실패 기록이 R15에만 있어 2-9.3 첫 항목과 맞지 않습니다**
- 근거:
  - 2-9.3 210행: "같은 짝에서 V0도 그 항목을 실패하면 VBJ 실패로 세지 않는다. 짝·항목별로 '기준선 실패'로 기록한다." 이 문장은 R15만이 아니라 모든 행에 적용됩니다.
  - 그런데 436.8 경로 1 정의는 V0가 실패한 경우 아무 항목도 내지 않습니다. 예: `j1_items`·`j2_items`·`j3_items`(`judge_stage1_4368.py` 216~281행)는 `base` 통과가 조건이고, 아니면 빈 목록을 돌려줍니다.
  - 그래서 R15 밖의 기준선 실패는 기록 없이 사라집니다. `baseline_failures.counted`는 0으로 박혀 있습니다.
  - V0 값이 None이어도 같습니다. 예: J2에서 `before`가 None이면 `is_at_least`가 False라 VBJ J2는 판정되지 않고 흔적도 없습니다.
- 실패 시나리오: V0와 VBJ가 같은 항목을 함께 실패하거나 V0 기록이 비면, VBJ의 그 항목은 판정도 기록도 없이 빠집니다. "기준선 실패 제외가 실패를 숨기지 않는가"의 유일한 안전장치가 기록인데, 그 기록이 R15에만 있습니다.
- 권고(둘 중 하나):
  - (가) 구현을 전 행으로 넓힙니다. VBJ·LSJ의 모든 (행, 위상) 짝에서 V0가 실패한 항목(`own_item_failures(V0)`)과 VBJ 자신의 상태를 기록하고, V0 값 None도 사유와 함께 남깁니다. 권장합니다.
  - (나) 2-9.3 210행을 R15로 한정하는 문장으로 고칩니다. 다만 그러면 None으로 빠지는 경우가 공개되지 않습니다.

## 경고
1. **(python 확인 요청 2에 대한 답) `own_item_failures`의 항목별 조건(457~497행)은 대체로 "V0가 그 항목을 실패한다"는 해석에 맞습니다.**
   - 맞는 항목:
     - J1: 사건 행은 V0 자신의 관문, 정상 행은 비통과 등급(S8 제외)
     - J2: F_min 미만 또는 None
     - J3: 연약 행의 미도달·한계 초과
     - J4: 끝이 READY가 아님, 정상 행은 READY 없음
     - J5·J6·J10: 절대 한계
   - 다른 점 둘:
     - (a) J3은 D-11의 강체 기록 행 분기(`case_floor` 기준, 282~286행 뒤)를 다루지 않습니다.
     - (b) docstring은 "J8·J9는 전제가 없다"고 적지만, J8·J9는 `old.J_fails`에서 J4~J10과 함께 나옵니다(`j_items` 384~389행). `judge_stage1_r5.J_fails`에서 J8·J9가 V0 통과를 전제하는지 확인이 필요합니다[추정].
   - H-3을 (가)로 고치면 이 함수가 전 행의 기록 근거가 되므로, (a)·(b)도 함께 맞추십시오.
2. **판정 불가가 실패보다 앞섭니다.** `_status`는 `no_reference`·판정 불가 항목·J-P3 판정 행 0을 실패보다 먼저 봅니다. 실패가 있어도 종료 2가 되고, 4a-5에서 종료 2는 다시 돌릴 수 있습니다. 실패가 하나라도 있으면 `failed`(종료 1)를 앞세우고 판정 불가 사유는 함께 기록하기를 권합니다. 이전에 12b에서 본 것과 같은 꼴입니다.
3. **L-c와 S8 정지값에 조용히 건너뛰는 곳이 있습니다.**
   - `limit_cycle_suspects`는 같은 group의 V0 기준이 없으면 `continue`로 넘어갑니다(390행).
   - `s8_items`는 `margin_at_stop_kN`·`max_after_stop_kN`이 None이면 정지 조건을 보지 않습니다(419~426행).
   - 둘 다 판정 불가로 보내기를 권합니다.
4. **V0 표본을 판정한 뒤에 정체성 확인을 합니다.** `step8`에서 `v0_sample` 판정(61행)이 `Invoke-IdentityCheck`(70행)보다 먼저 돕니다. 공통 규칙은 "어떤 판정 도구보다 먼저 정체성 확인"입니다(`common.ps1` 312행). 표본 실행 직후에도 정체성 확인을 부르기를 권합니다.
5. **실제 rev 6 통과 경로를 확인하는 시험이 없습니다.** `test_judge_end_to_end_on_stored_lines`(207~235행)는 어떤 상태든 받아들입니다. rev 6 줄만 있을 때 J-P3와 j9_main이 `pass`(종료 0)가 되는지 보는 합성 시험이 없습니다. revision 4 쪽이 비었을 때 합친 상태가 판정 불가로 떨어지지 않는지 시험으로 확인하기를 권합니다.
6. **정보: 남은 일 목록과 비용 주석이 낡았습니다.** 2-7.2 남은 일 목록에 이미 끝난 항목(F-1 등)이 그대로 있습니다. `step8` 머리 주석의 비용 "6,779 s"도 2-7.1의 6,036 s × 1.25와 다릅니다. 봉인 전에 정리하면 좋습니다.

## 실행한 검증
- sha·CRLF 확인, `git log`/`diff --stat`/`diff`(`3e30a408..4dcab9ef`), `j9_runs` 최상위 목록.
- 정오 2의 85~257행을 읽었습니다. 다음 코드의 해당 부분도 읽었습니다:
  - `jp3_j9main_judge.py` 전체
  - `step8_j9main.ps1`·`step7b_ckdrop.ps1`
  - `common_ed5.ps1`의 `Assert-NoL1Inputs`
  - `judge_stage1_4368.py`의 `j_items`·`j1_items`~`j3_items`·`sa4_items`
  - `j_p3_inputs.j_p3_over_rows`
  - `test_jp3_j9main.py`
  - `jp3_12b_judge.py`의 grade 부분
- 만든 파일과 원본 쓰기는 없습니다. 사용한 스킬: 없음

## 원문 3

<!-- timestamp  -->
## 판정
**정오 2 문안(sha `55e87c6e`)은 봉인 가능합니다.** 문안 자체를 막는 차단은 0건입니다. 다만 **실행 전에 반드시 고칠 구현 차단이 1건(K-1)** 있습니다. 판 5 원판 6.2가 이미 그 동작을 정하고 있으므로 정오 문장을 고칠 일은 아니고, 실행 전 감사에서 닫히는지 확인해야 합니다.

- 구현: worktree `z4369-ed5`의 `a0e06a8e`, 작업 트리 깨끗함. 시점은 결과 전이고, `j9_runs`에는 판 4a 커밋 넷만 있습니다.
- 본 결과: 없습니다. 시험은 제가 돌리지 않았습니다(메인 보고: 889 통과, 8 skip).

## 앞 감사 항목
- **H-1(R15 판정 불가 → 통과): 닫혔습니다.** `r15_worsening`이 "no R15 pair"와 "판정 불가"(J2 값 None)를 판정 불가 항목으로 돌립니다(`r15_not_judgeable`). 통과로 가지 않습니다.
- **H-2(rev 6 정체성): 닫혔습니다.** `line_identity_problems`가 다음을 봅니다. 하나라도 어긋나면 setting_defect 사유입니다.
  - 태그 기저 `final_C4G2_P3W`이고 태그가 revision 6을 가리키는지
  - `run_extend_start_revision`이 있으면 6인지, 없으면 `hydraulic_options`의 세 플래그가 모두 참인지(키와 옵션이 어긋나도 결함)
  - ③ 기록이 있으면 `rule_revision` 6과 `spec_edition` `fe6f5844`인지
  - 2-10.1 (1)·(3)과 같습니다.
- **H-3(기준선 실패 기록): 닫혔습니다.** `baseline_failures`가 모든 (행, 위상) 짝에 대해 기준 쪽이 실패한 항목을 기록합니다. 값 없음 표시와 판정 쪽 상태도 함께 남기고, LSJ는 VBJ를 기준으로 봅니다.
- **경고 3(L-c 조용히 건너뜀): 닫혔습니다.** V0 기준이나 `n_rev`가 없으면 판정 불가입니다.
- **2-10 상태 순서: 다음 도구에 들어갔습니다.**
  - 12b `Problems.status`
  - `jp3_baseline_compare.Problems`(T8·사례·T-JR 공용)
  - P5-1(`differ` 우선)
  - j9_main `status_basis`: 실패 → 설정 결함 → 판정 불가 → 통과, 사유는 모두 남김
- **12b J-P3 H-7:** `j_p3_judgement_rev5` 결과에서 `has_judged_breach`로 직접 읽습니다. 그 결과가 VBK 줄만의 판정이라 위치가 맞습니다.

## 실행 전 차단

**K-1 [E·R] T-JR-12a VBJ 줄의 J-P3 H-7이 기록으로 처리되어 멈추지 않습니다**
- 근거:
  - 원판 6.2(212행): "13.9절 지표와 지배 읽기 감소율은 판정·멈춤 조건이 아니다. 같은 줄의 P5-1과 **VBJ 줄 J-P3(6.1)는 그대로 적용한다**."
  - 그런데 `step6_dg3.ps1` 81~84행은 `t12_VBJ`를 `-ContinueCodes @(0, 1)`로 부릅니다.
  - `common_ed5.ps1` 64행은 `tool:t12_VBJ`를 `RecordCodeTools`에 넣어, 종료 1을 기록으로 봅니다(재시도도 허용).
  - `t12`의 종료 1에는 13.9 지표 실패(기록)와 `_dg3_j_p3`의 "VBJ: J-P3 H-7"(판정)이 섞여 있습니다(`jp3_tjr_judge.py` 798~816행).
  - 또 `_dg3_j_p3`는 `j_p3_judgement_rev5`의 상태 하나만 봅니다. 위반과 결함이 함께 있으면 setting_defect로 분류되어, 2-10.1 (5)의 "H-7 직접 읽기"가 빠져 있습니다.
- 실패 시나리오: rev 6 VBJ의 Dg-3 줄에 J-P3 위반이 나도 단계 (6)은 계속 진행되고, 그 실패는 기록으로만 남습니다. 2-10의 취지인 "실패를 숨기지 않는다"에 어긋납니다.
- 권고(python-expert):
  - `t12 --bundle VBJ` 보고의 `J-P3` 판정을 단계 스크립트가 따로 읽어, H-7이면 단계 종료 1로 멈춥니다. 다른 방법으로는 t12가 J-P3 실패를 별도 종료 코드나 필드로 내게 할 수 있습니다.
  - `_dg3_j_p3`에도 `has_judged_breach`를 적용합니다.
  - 시험 둘을 추가합니다:
    - "13.9 지표 실패만 → 계속"
    - "J-P3 H-7 → 멈춤"
  - VBH 묶음은 A7에 따라 J-P3가 기록이므로 지금 처리 그대로 둡니다.

## 경고
1. **2-10.1 (5)의 문장이 구현과 다릅니다(봉인 전에 고치기를 권함).**
   - 문장: "`_worse_status`의 순위도 … 맞춘다. 이 함수를 쓰는 다른 판 5 도구도 같은 순서가 된다."
   - 실제: 새 순서는 `j_p3_over_rows(edition5_order=True)`를 쓰는 j9_main에만 적용되고, 기본 순서는 그대로입니다. 다른 사용처는 `t4h_replay`(T-JR-13에서 J-P3 상태는 기록뿐, `jp3_tjr_judge.py` 1379행)와 봉인 도구 `chrono_t45_replay`입니다.
   - 판정 결과는 바뀌지 않지만 봉인 문장의 사실 진술이 틀리게 남습니다.
   - 제안 문장: "새 순서는 j9_main(`edition5_order=True`)에서만 쓴다. 12b는 rev 6 판정에서 H-7을 직접 읽는다. `t4h_replay`(T-JR-13, J-P3 기록)와 봉인 재생 도구는 기존 순서를 그대로 쓴다."
2. **12b 판정 파일의 `jp3.status`는 혼동을 부를 수 있습니다.**
   - `jp3.status`는 `j_p3_judgement_rev5` 자신의 상태입니다. 그래서 `jp3.status`가 `setting_defect`인데 최상위 `status`는 `failed`이고 `problems.failures`에 "J-P3 H-7"이 있는 경우가 생깁니다.
   - 권고:
     - 판정서 규칙에 "12b 판정은 최상위 `status`와 `problems`로 읽고, `jp3.status`는 내부 함수의 상태(기록)다"라고 적습니다.
     - 파일에 `jp3.h7_from_judged_rows`(참·거짓) 필드를 더합니다.
3. **skip 6건은 봉인 차단이 아니고 실행 전 확인 항목으로 봅니다.**
   - 공용 함수의 기본 경로가 바뀌지 않는 근거: 기본 순서 `STATUS_ORDER`가 그대로이고, `revision_status` 변환은 `edition5_order`일 때만 일어납니다. 마지막 결함 처리 `_worse_status(x, "setting_defect")`는 `STATUS_ORDER`의 맨 끝이 setting_defect이므로, 옛 코드의 무조건 대입과 결과가 같습니다. 봉인 도구의 결과는 코드상 같습니다.
   - 다만 이 판단은 정적 확인뿐이라 검증 공백이 남습니다. 실행 전 감사 전까지 다음을 권합니다.
     - `test_chrono_t45_replay` 5건과 `test_las_off_chrono` 1건: 저장 자료가 있는 메인 checkout에서 돌려 통과를 확인합니다. 그럴 수 없으면 위 근거를 실행 전 감사 기록에 남깁니다.
     - `test_x10_rod_fault` 2건: `X10_BASE_ROOT` 없이 skip된 (i) 비트 동일 시험은 원판 7.2 X-10 항목입니다. P5-3("skip은 미통과") 대상이므로, 실행 전에 `X10_BASE_ROOT`를 주고 skip 0으로 통과해야 합니다. 이것은 P5-3 멈춤 조건입니다.
   - 또 `j_p3_inputs.py`는 Dg-3·L1 러너의 import 폐포에 들어 있습니다. 판 5 재실행은 전체를 다시 돌리므로 문제는 없지만, 폐포가 바뀐 사실은 실행 기록의 `git diff --stat`에 드러납니다.

## 실행한 검증
- sha·CRLF·절 목록 확인, `git log`/`diff --stat`/`diff`(`4dcab9ef..a0e06a8e`): `j_p3_inputs`, 12b·baseline_compare·case_judge·p51·tjr 판정 도구.
- 정오 2 160~315행을 읽었습니다.
- `jp3_j9main_judge.py`의 `status_basis`·`_status`·정체성·L-c·R15·`baseline_failures`를 읽었습니다.
- `jp3_tjr_judge.py`의 `_dg3_j_p3`와 T-JR-13 부분, `step6_dg3.ps1`·`common_ed5.ps1`의 해당 줄을 읽었습니다.
- `j_p3_over_rows`·`_worse_status`·`has_judged_breach`의 사용처를 Grep했습니다.
- 만든 파일과 원본 쓰기는 없습니다. 사용한 스킬: 없음
