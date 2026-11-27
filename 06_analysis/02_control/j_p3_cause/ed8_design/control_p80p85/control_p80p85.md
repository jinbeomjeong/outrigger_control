# 436.9 판 8 4단계 P8-0·P8-5 — 규칙 문면 해석, 결정문, T8⁗ 명세 (control-expert, 2026-11-27)

의존성 점검: 생략했습니다. 이번 과제에는 제어 수치 계산이 없습니다. dynamics-dev는 확인 스크립트를 1회 돌리는 데만 썼습니다(import와 개수 세기). Python과 Julia로 비교할 수치가 없어 Julia 교차 검증은 해당 없습니다.

## 0. 결론
- **문항 1 (208행)**: 208행 "재실행하지 않는다"는 판정 도구를 고쳐 같은 C8 출력을 다시 판정하는 것을 막지 않습니다. 정오는 필요 없고, D-1과 같은 꼴의 결정문(D-2)이면 충분합니다. 결정문 초안은 `p80p85_decision_draft.txt`입니다(봉인 안 함). 정오로 둘지는 확인 필요 1입니다.
- **문항 2 (P8-0 T8‴ 분류)**: T8‴ 출력은 failed가 아니라 **판정 불가(판정 도구 결함, 87/114줄 미비교)**로 적습니다. 비교된 27줄은 기록으로만 둡니다.
- **문항 3 (M-3)**: P8-5 판정 불가로 4단계가 멈추고 미완이 됩니다. 5단계 진입은 사용자에게 물을 대상입니다.
- **문항 4 (판 8 전체 판정)**: 판 8 합격을 조건 없이 쓸 수 없게 됩니다. "PSW가 명령에 닿는 길이 하나뿐임"을 관문으로 확인했다고도 쓸 수 없습니다. census·G′·12a·12b는 그대로 계산할 수 있지만, 그 결과의 귀속에 제한이 생깁니다. 자세한 내용은 4절입니다.
- **감사 B-1을 블라인드 없이 독립 확인했습니다.** 생산자 계획 `ed7_probe.probe_jobs(arms=("a2",), part="all")`으로 확인했습니다.
  - 계획은 114 job이고, 생산자 키 `run_v5.job_key` 기준으로 114개가 모두 다릅니다.
  - gate `row_identity` 기준으로는 27개입니다.
  - 합성 줄에 T8‴ `judge_p80`을 돌리면 failed, run line problems 174, reference 27 jobs가 나옵니다. 감사와 같은 서명입니다.
  - 고정 기준(`e241638d` blob과 메인 checkout 사본 모두)은 sha256 d60306db와 같습니다. 114줄이고, 키 집합이 생산자 계획과 같습니다.
  - 덧붙여, 합성 줄을 역순으로 주면 T8‴는 "differing hashes: 27"을 냅니다. 키별 첫 줄끼리의 짝이 줄 순서에 따라 달라진다는 뜻이고, 감사가 말한 "equal 27은 같은 플랜트끼리의 비교가 보장되지 않는다"를 재현한 것입니다.

## 1. 문항 1 — 208행이 도구 수정 뒤 다시 판정하는 것을 막는가
**막지 않습니다.** 근거는 세 가지입니다.
- **(가) 4절은 "실행"과 "판정"을 나눠 씁니다.**
  - 표의 커밋 칸: "C8 실행, T8 판정"(201·203·205행)
  - 208행 예외 문장: "P8-16 사전 실행은 … 다시 돌 수 있다"
  - 209행: "단계마다 새 출력 경로 … `_a1` 폴더"
  - 11.1(352행): "C8 교체 … 1단계부터 다시"
  - 이 문맥에서 "재실행"은 C8에서 단계를 다시 돌리는 일입니다.
- **(나) 208행의 전제는 "판정 실패"입니다.**
  - P8-0의 실패 조건은 361행 "다르면", 곧 같은 job의 해시가 다른 것입니다.
  - T8‴ 출력에는 그런 비교 결과가 없습니다(`differing` []).
  - 그리고 "멈추고 묻는다"는 이미 했습니다(사용자 결정 2026-11-27).
- **(다) 11.2(354행)는 T8의 범위만 정합니다.** 범위는 04_scripts 판정 도구와 05_tests이고, 실행 경로 바이트가 C8과 같아야 합니다.
  - T8을 하나의 해시로 봉인하지는 않습니다. 판정 커밋은 S8-C의 `<S8C_JUDGE_COMMIT>`(356행)에서 처음 고정됩니다.
  - T8 → T8′ → T8″ → T8‴ 교체가 같은 11.2 아래에서 이미 있었습니다.

**결과 의존 변경이 아닌 이유**
1. 바꿀 것에 자유도가 없습니다.
   - 키는 규칙 361행("`ed7_probe.py --arms a2 --part all` 114줄 = b46bdf8f 재현 줄별 해시")과 생산자 이어 돌기 키 `run_v5.job_key`로 정해집니다. 근거는 `ed7_probe.py:228`, `run_v5.py:759,768-770`이고, 빼는 필드는 mask·t4h_dir뿐입니다.
   - 114줄, 기준 sha, 실패 조건, 상태 순서는 그대로 둡니다.
2. 결함은 자료와 무관합니다. 이 도구는 생산자 꼴의 어떤 올바른 입력에도 통과를 낼 수 없었습니다(자기 대조로 확인). "불리할 때만 고친" 것이 아니라, 이 관문을 계산하려면 반드시 고쳐야 했던 결함입니다.
3. 비교되지 않은 87줄의 해시 대조 결과는 아무도 보지 않았습니다. 감사도 저도 블라인드 원자료를 열지 않았습니다.
4. 다시 판정한 결과는 방향과 관계없이 받습니다. 해시 차이로 실패하면 201·208행대로 멈추고 묻습니다. C8 교체는 승인 뒤에만 합니다.

**D-1과 다른 점(공개)**: D-1은 판정 값을 보기 전에 고쳤습니다. 이번에는 상태 서명(failed, 같음 27, 차이 0)을 본 뒤에 고칩니다.

**정오를 원하실 때의 최소 문장**(선택, 확인 필요 1). 10절 346행 뒤에 더합니다.
> 판정 도구가 봉인 문면의 비교를 따르지 못해 계산되지 않은 판정 항목도 판정 불가다. 이때 11.2 범위 안에서 판정 도구를 고친 새 T8로 그 단계의 관문 전부를 새 출력 폴더에 다시 판정할 수 있다. C8 실행은 다시 하지 않는다. 고친 범위는 판정 정의(줄 수·키·문턱·상태 순서)를 바꾸지 않아야 하고, 고치기 전 출력은 보존한다.
- 저는 결정문을 추천합니다. 결과를 본 뒤 봉인 문면에 절차를 더하는 것도 공개 대상이 되기 때문입니다.
- 어느 쪽이든 판정 정의는 바뀌지 않습니다.

## 2. 문항 2 — P8-0 T8‴ 출력의 분류
- 판정서에는 다음 꼴로 적습니다: "도구 출력 failed(종료 1) → 규칙 분류 **판정 불가**(10:346, 판정 도구 키 결함으로 87/114줄 미비교) → T8⁗ 출력으로 대체".
- 실패가 아닌 이유: 361행의 "다르면"에 해당하는 비교 결과가 없습니다. 도구 failures 칸의 "run line problems: 174"는 규칙이 정한 실패가 아니라 키 접힘의 산물입니다.
- T8‴의 setting_defect "reference: 27 jobs, 114 expected"도 같은 결함의 산물입니다. 기준 sha가 봉인값과 같고, 키 114개가 생산자 계획과 같습니다(`p80_plan_keys.out.json`).
- 비교된 27줄은 기록으로만 둡니다(키별 첫 줄끼리이고 같은 플랜트 짝이 보장되지 않음, 0절). 부분 통과의 근거로 쓰지 않습니다.
- C8 교체 질문(201행) 대상이 아닙니다.

## 3. 문항 3 — 4단계 멈춤 칸(201)과 P8-5 행(365)의 관계(M-3)
- 201행은 실패·`setting_defect`의 멈춤을 정합니다. "그 둘만 멈춘다"고 쓰지는 않았습니다. P8-5 행은 판정 불가에 "(멈춤)"을 붙였습니다. 두 문장은 어긋나지 않고, 관문 행이 더 구체적인 문장입니다.
- 반대 읽기도 있습니다. 6단계 칸(203행)은 판정 불가를 적었는데 4단계 칸에는 없으니, 일부러 뺐다고 볼 수 있습니다. 그러나 P8-5 행의 "(멈춤)"이 명시돼 있으므로 이 읽기는 받지 않습니다.
- 10:338에 따라 판정 불가는 통과가 아닙니다. 그래서 **4단계 관문 하나라도 통과가 아니면 4단계는 끝나지 않은 것**입니다.
- 따라서 P8-5 판정 불가 → 4단계 멈춤·미완 → 5단계 진입은 사용자 질문 대상입니다.
- 참고: P8-8·P8-15 행은 판정 불가에 "(멈춤)"을 붙이지 않았습니다. 일반 읽기("4단계 판정 불가는 모두 미완")를 채택할지는 확인 필요 3입니다. T8‴에서 둘 다 pass라 지금 영향은 없습니다.
- 진입 판단용 정보(결정 아님)
  - 5단계는 V0만 돌므로 P8-5(VBN 구성의 PSW)와 무관합니다.
  - 5·6단계의 기준 V0 타당성(옛 설정 명령 불변)은 P8-0에 기댑니다. 그래서 5단계 전에 P8-0 통과(T8⁗)가 필요합니다.

## 4. 문항 4 — P8-5 판정 불가가 판 8 판정에 주는 영향
- 봉인 규칙에는 "판 8 합격" 종합 조건 문장이 없습니다. 판 7 6.3 761행의 꼴("확인 단계가 실패하면 … 합격이 아니다")도 판 8 부록 A 목록에 없습니다.
- 그래서 읽기의 기준은 0절 81행 판정 구조, 4절의 판정(관문) 행, 10:338입니다. 이 결정문은 "4절 판정(관문) 행이 모두 통과일 때만 판 8 합격을 조건 없이 쓴다"로 읽습니다(확인 필요 2).
- **못 말하게 되는 것**
  - "4단계 구현 확인이 모두 통과했다"
  - "PSW가 명령에 닿는 길이 `state.twist_stiffness_scale` 하나뿐임을 P8-5 관문으로 확인했다"
  - census·G′가 실패할 때, 그 실패를 PSW 구현 누출과 설계 탓으로 나눌 관문 근거
- **남는 것**
  - P8-6(1회차 K1_sc 값, T8‴ 통과)
  - 16절 N-1 전제 시험 둘(P8-4 안): ProbeResult 기존 필드의 비트 동일, 그리고 새 필드를 읽는 곳이 `_update_twist_stiffness_scale`뿐이라는 정적 시험. P8-4가 T8⁗ 판정에서 통과로 확정될 때에 한합니다.
  - 비교된 14쌍의 명령 차이 0(기록)
  - census·G′·12a·12b는 PSW를 포함한 VBN 구성 전체를 결과로 판정하므로 계산할 수 있습니다.
- 판정서 문장 꼴: 결과 판정 단계가 모두 통과하더라도 "판 8 결과 판정 통과, 구현 확인 P8-5 판정 불가(사용자 결정으로 진행)"로 적습니다. 이것을 합격으로 볼지는 사용자가 정합니다.

## 5. T8⁗ 구현 명세 (python-expert; T8‴ 2263b246의 자식, C8 불변)
**위치**: 잠긴 `ed8-judge3`에는 쓰지 않습니다. 새 worktree를 만듭니다: `git -C C:\workspace\outrigger_control worktree add .claude\worktrees\ed8-judge4 -b ed8-judge4 2263b246`(메인이 만들거나 지시). 정션은 만들지 않습니다.

### 바꿀 파일 (이 파일과 05_tests만)
1. `04_scripts/04_hydraulic/coupled/jp3_ed8_gate_judge.py`
   - **새 함수 `p80_job_key(job) -> str`**
     - 함수 안에서 `import run_v5`(t8과 같은 지연 import)를 하고 `run_v5.job_key(dict(job))`를 돌려줍니다.
     - docstring에 spec v8 12 P8-0(361행), `ed7_probe.py:228`(생산자 이어 돌기 키), `run_v5.py:759`(빼는 필드 mask·t4h_dir; setting·`_part`·`_r79_plan`은 키에 남음)를 인용합니다.
   - **`hash_table(rows, label, problems, key=row_identity)`**: 키워드 `key`를 더합니다. 기본값을 두므로 다른 동작은 바뀌지 않습니다.
   - **`judge_p80`**
     - `run_problems`와 `reference_problems`를 따로 둡니다(감사 M-1).
     - 두 표 모두 `key=p80_job_key`로 만듭니다.
     - 기준 쪽 문제는 `setting_defects`로 갑니다. 해당하는 경우는 오류 줄, 해시 없음, 키 중복(`reference line problems: N`), 그리고 서로 다른 기준 키 수 ≠ 114(`reference: K jobs, 114 expected`, 기존 문구)입니다. 근거는 10:345 "목록 밖 문제는 입력 결함"입니다.
     - 기준에 문제가 있으면 missing·extra·differing을 failures로 세지 않습니다. 이때 `reference_compared: false`로 둡니다. 봉인 꼴이 아닌 기준과의 대조는 규칙의 비교가 아니기 때문입니다.
     - run 쪽 문제(오류·해시 없음·중복)는 지금처럼 failures `run line problems: N`입니다. missing·extra·differing도 지금처럼 failures입니다.
     - 보고 키
       - 둡니다: `jobs`(= 기준 키 수)
       - 더합니다: `run_jobs`, `equal`, `missing`, `extra`, `differing`, `run_line_problems`, `reference_line_problems`, `reference_compared`, `key`(문자열 "run_v5.job_key (spec v8 12 P8-0)"), `settings_reference`·`settings_run`(job.setting별 줄 수. 입력 정체성이고 해시 값은 넣지 않음)
     - 지금의 `line_problems`는 소비처를 Grep으로 확인합니다(`*.py`·`*.ps1`, 범위는 04_scripts·05_tests와 메인 `ed8_design` 하위 스크립트 폴더를 직접 지정). 없으면 없애고, 있으면 run 쪽만 담게 둡니다. 어느 쪽으로 했는지 보고합니다.
   - **모듈 docstring의 `p80` 단락**: 키(생산자 job_key, setting 유지)와 기준 쪽 문제의 분류를 적습니다.
2. 시험
   - 새 파일 `05_tests/unit/test_ed8_gate_p80_key.py`
   - 기존 `test_ed8_gate_judge.py`는 바꾸지 않습니다. 기존 p80 시험은 setting이 하나라 그대로 통과해야 합니다.

### 하지 말 것
- 바이트 그대로 둘 것: `RUNTIME_JOB_KEYS`, `row_identity`, `probe_pairs`, `_scale_list`, `is_same_scale`, `has_no_extension`, `has_no_waiver`, `PAIR_SELECTORS`, `judge_arm_pairs`, `line_lookup`, `judge_t8`, `run_command`, 단계 기록 점검, CLI·종료 코드, 상수 `P80_LINES`·`P80_REFERENCE_SHA256`·`RUN_COMMIT`·`SPEC_V8_SHA256`·`ARM_PAIRS`·`MIN_SAME_PAIRS`·`UNREAD_PAIRS_LEFT_OUT`. 팔 짝 관문은 (팔, plant, `row_identity`) 짝이 맞습니다(감사 R-3).
- 다른 파일도 고치지 않습니다: `jp3_ed8_judge.py`·`jp3_tjr_judge_ed8.py`(T8‴의 D-1 변경 그대로), `jp3_ed8_rules.py`, `p816_compare.py`, `run_v5.py`, `ed7_probe.py`, `j_p3_inputs.py`, `03_src`. 실행 경로 모듈은 P8-11 대상입니다.
- run 쪽 줄 문제의 분류(failed)를 바꾸지 않습니다. 결과를 본 뒤 분류를 바꾸지 않기 위해서입니다.
- 블라인드(`j9_runs\56849248\impl_*_a1\`, `l1ref_a1\`, worktree 사본)를 열거나 시험 자료로 쓰지 않습니다. ed7_probe를 돌려 C8 줄을 재생성하지 않습니다. 실제 C8 출력에 판정 도구를 돌리지 않습니다(메인 몫).
- `ed8-judge3`에 쓰지 않습니다.

### 시험 (T-a~)
- **T-a 생산자 키 일치**
  - 계획 `ed7_probe.probe_jobs(arms=("a2",), part="all")`의 각 job(mask·t4h_dir를 더한 꼴)에서 `gate.p80_job_key(j) == run_v5.job_key(j)`입니다.
  - 서로 다른 키가 114개입니다.
  - `run_v5.RUNTIME_JOB_KEYS == ("mask", "t4h_dir")`입니다.
  - setting 분포가 {P7-M-a2 27, P7-Mslow-a2 27, P7-Mfast·Mc005·Mc04·L-a2 각 15}입니다.
  - 회귀 기록: `len({gate.row_identity(j)}) == 27`(옛 키가 접히는 이유를 시험으로 남김).
- **T-b 생산자 꼴 114줄(합성 해시)**
  - 기준 = 같은 줄을 고정 seed로 섞은 것 → pass, jobs 114, equal 114
  - Mslow D키 한 줄의 해시를 바꿈 → failed, differing 1, 그 키에 `"setting": "P7-Mslow-a2"`가 있음
  - 플랜트끼리 해시가 같고 한 플랜트 한 case만 다름 → failed, differing 1
  - run에서 한 setting의 줄 하나를 뺌 → failed, missing 1
  - run 줄 하나를 중복 → failed, `run_line_problems` 1("twice")
  - run 오류 줄 → failed
- **T-c 기준 쪽 문제 = setting_defect**
  - 기준에 오류 줄, 해시 없음, 중복 키, 113줄 가운데 하나를 넣고 run은 정상으로 둡니다.
  - 기대: status `setting_defect`, failures [], `reference_line_problems` 비어 있지 않음, `run_line_problems` [], `reference_compared` false
- **T-d 고정 기준 자기 대조(skip 금지)**
  - 바이트는 `git -C <ROOT> show e241638d:06_analysis/02_control/j_p3_cause/j9_runs/b46bdf8f/repro_a2/ed7_probe_a2.jsonl`로 얻습니다(공유 object store).
    - 이 파일은 C8·T8 트리에는 없습니다(`e241638d`는 C8의 조상이 아님, 확인함).
    - blob sha256이 `P80_REFERENCE_SHA256`과 같음을 오늘 확인했습니다.
  - git 실패나 sha 불일치는 시험 실패입니다.
  - `judge_p80(ref, ref)` → pass, jobs 114, equal 114, 문제 0
  - 기준 키 집합 = 계획 키 집합
  - 해시 값은 출력하지 않습니다.
- **T-e 다른 관문 불변**
  - `ast`로 HEAD의 gate 파일과 `git show 2263b246:<gate 경로>`를 비교합니다. 최상위 정의 가운데 {`judge_p80`, `hash_table`, `p80_job_key`(새로 추가)}와 모듈 docstring을 뺀 나머지의 소스가 같아야 합니다.
  - `git diff --name-only 2263b246 HEAD`가 {gate 파일, `05_tests/**`}의 부분집합이어야 합니다.
- **T-f P8-11**
  - 기존 `test_ed8_run_path.py`가 통과해야 합니다(C8 바이트).
  - `git diff --name-only 56849248 HEAD`가 04_scripts 판정 도구와 05_tests 안에 있어야 합니다.
- **T-g 기존 시험**: `test_ed8_gate_judge.py` 전부가 바뀌지 않은 채 통과해야 합니다.
- **T-h CWD 분리**
  - 새 시험을 cwd = 새 worktree 루트와 cwd = 저장소 밖 임시 폴더에서, 각각 절대 경로·`-p no:cacheprovider`로 돌려 둘 다 통과해야 합니다.
  - 끝난 뒤 `git status --porcelain --ignored`가 빈 출력이어야 합니다.
- **P8-4 방침**: T8‴ 기준선 대비 전체 단위 시험(Chrono-dev, 앞 실행과 같은 env)에서 새 실패·새 건너뜀이 0이어야 합니다. 새 시험 수를 보고합니다.

### 메인 순서 (참고)
1. python-expert T8⁗ 구현
2. verif-protocol-auditor 재감사(`[시점] 실행 전`). gate p80 하위 명령에 "기준 자기 대조" 스모크를 포함합니다.
3. 새 실행 스크립트와 실행 전 점검 도구(placeholder_scan·ps1_lint)
4. 4단계 관문 8개(p80, p816, p85, p88, p815, t8, cases, l1ref)와 P8-4를 T8⁗로 판정합니다(dynamics-dev, 새 폴더 `j9_runs\56849248\judge_<T8⁗ 앞 8자>\`).
5. 뒤 대조(기록): p80을 뺀 7개의 T8⁗ 출력이 T8‴ 출력과 status·status_basis·수 필드가 같은지 봅니다. 다르면 멈추고 묻습니다.
6. `judge_2263b246\`은 보존하고 "대체됨"으로 적습니다.

## 6. 판정서 공개 문장 초안
(결정문 `p80p85_decision_draft.txt` 9절과 같습니다.)

**(가) P8-0 판정 도구 결함, 결과를 본 뒤 고침**
- 4단계 관문을 T8‴(2263b246)로 판정했을 때 P8-0 출력은 failed였다.
- 판정 후 감사가 원인을 판정 도구의 줄 키 결함으로 확정했다. 공용 줄 키가 setting을 떼어 114 job이 27키로 접혔고, 87줄은 비교되지 않았다. 고정 기준을 자기 자신과 대조해도 같은 서명이 나와, 실행 자료와 무관한 결함이다.
- 결과(상태 서명: failed, 같음 27, 차이 0)를 본 뒤 도구를 고쳤다(T8⁗ <해시: 메인이 덧붙임으로 고정>).
- 고친 것은 둘뿐이다. (1) 줄 키를 규칙 361행과 생산자 `run_v5.job_key`에 맞췄다. (2) 기준 쪽 줄 문제를 run 실패에서 떼어 setting_defect로 두었다. 114줄, 기준 sha, 실패 조건, 상태 순서는 바꾸지 않았다.
- 비교되지 않은 87줄의 해시 대조 결과는 T8⁗ 재판정 전까지 아무도 보지 않았다. 판정 후 감사와 결정문 작성자 모두 블라인드 원자료를 열지 않았다.
- T8‴에서 비교된 27줄은 같은 플랜트끼리의 짝이 보장되지 않아 기록으로만 둔다.
- 단일 판정 커밋 원칙에 따라 4단계 관문 8개와 P8-4를 T8⁗로 새 출력 폴더에 다시 판정했다. T8‴ 출력은 보존했고 대체됐다.

**(나) 실행 전에 잡지 못한 경로(감사자·작성자 누락)**
- 기준 파일은 실행 전에도 열 수 있었다. 기준을 자기 자신과 대조하는 스모크 한 번이면 드러났다.
- 실행 전 감사(`audit_prerun/verif_c8_t8.md` 154행)는 상수와 sha만 대조했다.
- 판정 전 점검(`stage4_prejudge/prejudge_report.md` 42·54행)은 키 존재와 sha만 봤다.
- T8‴ 판정 전 재감사(`audit_t8ppp/verif_t8ppp_prejudge.md` 111행)는 gate 하위 명령을 범위에서 뺐다.
- 단위 시험(`test_ed8_gate_judge.py` 56-58행)은 setting이 하나인 합성 줄만 썼다.
- 명세 작성자(control-expert)는 P8-0 행에 줄 대응 키를 적지 않았다. D-1 대조에서도 gate를 "J-P3 안 씀, 영향 없음"으로만 보고 p80 키는 보지 않았다.

**(다) P8-5 판정 불가**
- P8-5는 같은 쌍 14 < 15로 판정 불가다(규칙 365행). 판정되지 않은 9쌍은 규칙상 "같지 않음" 쌍이다(라운드 수 또는 라운드별 스케일이 다름, 감사 R-1).
- 문턱 15는 봉인 전 감사 권고(M-9)에 따라 개정 3에서 정했다. 그러나 예상되는 같은 쌍 수와 그 계산 근거는 봉인 전에 적지 않았다(판정 후 감사 M-2. 개정 3 작성자는 control-expert).
- 결과를 본 뒤 문턱을 바꾸지 않았고, 키를 더해 다시 실행하지도 않았다(사용자 결정 2026-11-27).
- 비교된 14쌍의 명령 차이 0은 기록이다.

**(라) 4단계 상태**: P8-5 판정 불가로 4단계는 끝나지 않았다. 5단계 진행은 사용자가 따로 정한다.

**(마) 접근**
- 판정 후 감사의 PowerShell Test-Path 묶음 명령 1회가 blind_guard에 막혔다(출력 없음).
- 결정문 작성은 판정 출력 p80.json·p85.json(단일 파일)과 블라인드가 아닌 고정 기준만 읽었다.

## 7. 경로 2 대조
- 9:332의 경로 2 범위(census J-P3, P8-2, G′, 12a·12b, T-JR-12b)에 P8-0·P8-5는 없습니다.
- 판정 집합, 0건·결측 처리, 상태 이름이 바뀌지 않습니다.
- 그래서 경로 2 넘김에 더할 [정의] 문장은 없습니다.

## 확인 필요
1. D-2를 결정문으로 둘지(추천), 1절의 최소 정오 문장으로 봉인할지.
2. 판 8 종합 문장의 읽기: "4절 판정(관문) 행이 모두 통과일 때만 판 8 합격을 조건 없이 쓴다". 그리고 P8-5 판정 불가 상태로 진행해 결과 판정이 모두 통과하면 그것을 합격으로 볼지(4절).
3. M-3 일반 읽기: P8-8·P8-15처럼 "(멈춤)"이 없는 관문의 판정 불가도 4단계 미완으로 볼지(지금은 영향 없음).
4. (낮음) T8⁗에서 run 쪽 결측·중복·오류 줄을 T8‴처럼 failed로 둡니다. 10:346 읽기로는 판정 불가일 수도 있습니다. 결과를 본 뒤 분류를 바꾸지 않으려고 그대로 두기를 추천합니다. 감사 증거로는 run 줄 114줄 모두 해시가 있어, 이 분기에 닿을 가능성은 낮습니다.

## 위임 필요
- **python-expert**: 5절 T8⁗ 구현(새 worktree `ed8-judge4`, 커밋 해시는 메인이 고정).
- **verif-protocol-auditor**: T8⁗ 재감사.
  - p80 자기 대조 스모크
  - T-e 불변 범위
  - P8-11
  - 재판정 뒤 7개 뒤 대조 확인
- **python-expert(tools/verif 후보, 감사 제안)**: "기준 자기 대조" 검사 도구.
- **stats-design-expert**: 해당 없음. 문턱을 바꾸지 않습니다.

## 메인 세션 권고
- 5절 "메인 순서"대로 진행합니다. 판정 실행(8개 + P8-4)은 메인이 띄웁니다. 수 분 이내로 예상합니다.

## 산출물 (`C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\control_p80p85\`)
| 파일 | sha256 |
|---|---|
| `p80p85_decision_draft.txt`(결정문 D-2 초안, 봉인 안 함) | `fd85d7f83b33d09a39eee5e4de3cd547df16fd4d8c721d3483169b0774c4d417` |
| `p80_plan_keys.py`(생산자 계획·기준 키 확인, 개수만 출력) | `da2f26fa060eea3d02c5caf0cfe80afcfcbcd770bbbf8ad5bfd0b4a4526aee5c` |
| `p80_plan_keys.out.json` | `d809ef6e426db186e314aa4a4007707b47fb29a59092019cc7e8c68b170f522c` |
- 폴더 SUMS는 쓰지 않았습니다(메인이 이 md 저장 뒤 씁니다).
- 실행 명령: `conda run -n dynamics-dev python -X utf8 -I -B <파일>`, cwd는 scratchpad, `PYTHONDONTWRITEBYTECODE=1`, `NUMBA_CACHE_DIR`은 scratchpad. 종료 0이었고, 뒤에 `ed8-judge3` `status --porcelain --ignored` 빈 출력, HEAD 2263b246을 확인했습니다.

## 공개 (읽은 파일·검색 범위)
- **Read**
  - `audit_t8ppp\verif_p80p85_postjudge.md`(전체)
  - 규칙 `jp3_remedy_spec_v8_rules.md` 1~459행(전체)
  - `control_d1_settings\control_d1_settings.md`·`d1_decision_draft.txt`(전체)
  - `audit_t8ppp\decision_d1_cd_scope_20261127.md`
  - `jp3_remedy_spec_v7.md` 735~779행
  - 판정 출력 `j9_runs\56849248\judge_2263b246\p85.json`(전체), `p80.json` 1~10행
- **ed8-judge3 Read(읽기만)**
  - `jp3_ed8_gate_judge.py`(전체)
  - `ed7_probe.py` 100~269행
  - `jp3_ed8_rules.py` 70~99행
  - `test_ed8_gate_judge.py` 1~100행
- **Grep(모두 단일 파일)**
  - 규칙 v8, 규칙 v7
  - `judge_2263b246\p80.json`(상태·문제 줄 패턴. 키 이름만 나오고 해시 값은 없음)
  - ed8-judge3 `run_v5.py`, `05_tests\data\ed8_run_path_modules_56849248.json`
  - 폴더 범위 Grep·Glob은 쓰지 않았습니다.
- **git(Bash, 짧은 조회만)**
  - 기준 파일 `ls-files`(메인·ed8-judge3)와 `check-attr`
  - 기준 파일 추가 커밋 `log --diff-filter=A`
  - `merge-base --is-ancestor e241638d 56849248`
  - blob `cat-file -t`
  - ed8-judge3 `status`·`rev-parse`
- **스크립트가 읽은 것**
  - 고정 기준(블라인드 아님): `e241638d` blob과 메인 checkout 사본
  - ed8-judge3 모듈 import(`ed7_probe`, `run_v5`, `jp3_ed8_gate_judge`), 쓰기 없음
- **블라인드**: `impl_*_a1\`, `l1ref_a1\`와 worktree 사본은 Read·Grep·Glob·목록·스크립트 어디에도 쓰지 않았습니다. 경로 2 도구는 열지 않았습니다.
- **도구 거부 1건**: 출력 해시와 scratchpad 삭제를 묶은 PowerShell 명령 1개가 경로 보호 규칙에 막혔습니다(`"$dst\*"`를 삭제 대상으로 오인). 실행된 것은 없습니다. 명령을 나눠 다시 실행했습니다.
- 규칙 파일·`ed8-judge3`·`ed8-impl`은 고치지 않았습니다. 프로세스를 종료하지 않았습니다. scratchpad `control-p80p85\`는 지웠고, `Test-Path` False를 확인했습니다.
- 요청 범위 밖 추가
  - 4절 판 8 종합 조건이 규칙에 없다는 점을 지적하고 읽기를 제안했습니다(확인 필요 2).
  - T8⁗ 명세에서, 기준에 문제가 있으면 run 대조를 세지 않는 조항을 넣었습니다. 기준 sha가 고정돼 있어 실제로는 닿지 않는 방어 조항입니다.
- 메모리: `agent-memory\control-expert\per-line-gate-join-key.md`를 더했고, `MEMORY.md` 색인 1줄을 더했습니다.

사용한 스킬: 없음
