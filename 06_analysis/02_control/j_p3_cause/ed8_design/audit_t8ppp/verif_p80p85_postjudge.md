## 감사 요약
- 본 결과: 판정 출력 `judge_2263b246\p80.json`(전체: 줄 문제 목록, 상태 근거, 입력 sha)과 `p85.json`(전체). 나머지 6개 출력은 정체성 필드와 `status`만 봤습니다. 기준 `j9_runs\b46bdf8f\repro_a2\ed7_probe_a2.jsonl`(블라인드 아님, 판 7 본 자료)에서는 구조만 셌습니다: 키 이름, `job.setting` 분포, 키별 `commands_sha256` 서로 다른 값의 개수(해시 값은 출력하지 않음). 이 과정에서 기준 파일의 최상위 `final_phase`·`harness_class` 값별 건수도 화면에 나왔습니다(기준 파일 값이고 판정 대상 값은 아닙니다). 판정 대상 원자료(블라인드)는 열지 않았습니다.
- 대상: 436.9 판 8 4단계 관문 판정 가운데 p80(P8-0)과 p85(P8-5). 판정 도구는 T8‴ `2263b246`(ed8-judge3), 실행 커밋은 C8 `56849248`, 시점은 판정 후입니다.
- 기준 문서: `jp3_remedy_spec_v8_rules.md` 35f9eba8. `.md.sha256` e19aaa48과 맞습니다.
- 판정: 차단 1(P8-0 판정 도구 키 결함) / 실행 전 수정 3 / 기록 3.
  - **P8-0의 failed는 관문 실패가 아니라 도구 결함의 산물입니다.** 규칙대로라면 87/114줄이 비교되지 않은 판정 불가입니다.
  - **P8-5의 not_judgeable은 규칙과 도구가 정한 그대로의 결과입니다.** 도구 결함은 없습니다.
  - 어느 쪽을 확정하든 사용자 결정이 필요합니다.

## 발견 사항 (심각도순)

### [차단][R·E] B-1. P8-0의 키 함수가 `setting`을 떼어 114 job이 27키로 접힘 — "twice" 174건, setting_defect, 87/114줄 미비교의 공통 원인
- **원인 (b)를 확정했습니다.** 판정 도구가 같은 job을 두 번 읽는 것이 아니라, 키에서 job을 가르는 필드를 뺍니다.
  - `jp3_ed8_gate_judge.py:94`: `RUNTIME_JOB_KEYS = ("mask", "t4h_dir", "setting", "_part", "_r79_plan")`
  - `:221-224`: `row_identity`가 이 키들을 뺍니다.
  - `:242-255`: `hash_table`은 같은 키의 두 번째 줄부터 `"{label}: {key} twice"`로 넘기고, 비교표에는 첫 줄만 넣습니다.
  - 이 공용 키는 팔 짝 관문(p85·p88·p815, `:279-299`)을 위한 것입니다. 거기서는 팔이 `setting`(`P8-<plant>-<arm>`)에 들어 있고 플랜트는 `ed8_probe` 블록에서 읽으니 맞습니다.
  - 그런데 P8-0 생산자 `ed7_probe.py`에서는 `setting = P7-<plant>-a2`(`ed7_probe.py:133-134, 193-197`)가 **플랜트를 가르는 job 정체성**입니다. 생산자의 이어 돌기 키 `run_v5.job_key(job)`에도 setting이 들어 있습니다(`:227-228`).
- **기준 파일 구조**(재계산, 스크립트 `ref_struct.py`·`ident.py`)
  - 114줄, `job.setting` 6종: P7-M-a2 27, P7-Mslow-a2 27, P7-Mfast·Mc005·Mc04·L-a2 각 15.
  - 이는 6플랜트 × 15키(main) + 2플랜트(M, Mslow) × 12 D키 = 114와 맞습니다(`ed7_probe.py:188-198`).
  - setting을 빼면 서로 다른 키가 27개입니다. 키당 줄 수는 6줄 15키, 2줄 12키입니다.
- **도구로 재현했습니다**(dynamics-dev `-I -B`, cwd는 scratchpad, `PYTHONDONTWRITEBYTECODE=1`)
  - 잠긴 도구의 `judge_p80(기준, 기준)`, 즉 기준 파일을 자기 자신과 대조하면 출력 p80.json과 같은 서명이 나옵니다: `failed`, failures `["run line problems: 174"]`, setting_defects `["reference: 27 jobs, 114 expected"]`, equal 27/jobs 27.
  - 같은 프로세스에서 키에 setting만 남기면 `pass`, jobs 114, 줄 문제 0입니다.
  - **즉 이 상태는 실행 데이터와 무관하게 도구만으로 생깁니다.**
  - 뒤에 `git -C ed8-judge3 status --porcelain --ignored`는 빈 출력, HEAD 2263b246이었습니다.
- **(a) 생산자 중복은 아닙니다**(정황 4가지, 원자료는 보지 않음)
  - `impl_p80.done:4,31`: exit 0, `previous_attempts []`
  - `_identity_checks\impl_p80_a1.md:8-9`: start·end 블록 각 1개, 이어 돌기 없음
  - p80.json의 run 쪽 "twice" 87줄과 reference 쪽 87줄은 키 다중집합이 똑같습니다(15키 × 5, 12키 × 1). 기준의 플랜트 구조와 같습니다.
  - run 쪽에 "no command hash"가 0건이라 해시 있는 줄은 27 + 87 = 114입니다.
  - 한계: "run 114줄의 (job + setting)이 모두 서로 다르다"는 블라인드 원자료로만 확정됩니다.
- **(c) 규칙이 반복 실행을 정한 것도 아닙니다.** 규칙 12 P8-0(`spec:361`)은 "`ed7_probe.py --arms a2 --part all` 114줄 = b46bdf8f 재현 줄별 해시"입니다. 서로 다른 114 job의 줄별 대조를 뜻합니다.
- **"114 expected"의 출처**
  - 규칙 `spec:361`의 "114줄", 도구 상수 `P80_LINES = 114`(`gate:91`, docstring `:9-12, 89`).
  - 상수는 맞습니다. `len(expected)`(`:264`)가 접힌 키 수 27을 세기 때문에 어긋납니다.
  - "reference 27 jobs"는 기준 114줄이 키 결함으로 27로 접힌 값입니다.
- **실패 시나리오와 지금 결과의 뜻**
  - 87줄씩은 비교 자체가 되지 않았습니다. 기준 쪽에서 보면 첫 줄은 27키 모두 P7-M-a2이고, 비교되지 않은 87줄은 M 밖의 플랜트 전부(Mslow D키 12줄 포함)입니다.
  - 규칙이 P8-0을 둔 이유는 "114줄은 RE1bF D키를 포함해 Y8-9가 바꾸는 줄을 지난다"(`spec:361`)입니다. 그 범위 가운데 Mslow 쪽은 확인되지 않았습니다.
  - "equal 27"도 run 쪽과 기준 쪽의 같은 setting 줄끼리 비교한 것인지 보장되지 않습니다. 생산자는 `imap_unordered`로 줄을 씁니다(`ed7_probe.py:238`). 그래서 키별 첫 줄이 두 파일에서 같은 플랜트라는 보장이 없습니다. 실제로 두 파일의 "twice" 순서는 서로 다릅니다.
  - 기준에서 키 3개는 플랜트끼리 해시가 겹칩니다(서로 다른 해시 4/6 1키, 5/6 2키). 그래서 플랜트가 어긋난 짝도 우연히 같게 나올 수 있습니다[추정].
- **시험이 못 잡은 이유**
  - `05_tests\unit\test_ed8_gate_judge.py:56-58`의 `p80_rows`는 setting 하나(`P7-M-a2`)에 줄마다 다른 case를 씁니다.
  - 생산자 꼴(같은 case가 여러 setting에 걸침)이 아니라서 :61-81의 시험이 모두 접힘을 지나칩니다.
- **판정 전 점검과 앞 감사가 못 잡은 이유**
  - `stage4_prejudge\prejudge_report.md:42`는 p80 114줄의 `commands_sha256`·`job` 키 존재만 셌습니다.
  - 같은 문서 `:54`의 스모크는 `pinned_input`(sha)만 불렀고, `hash_table`·`row_identity`는 부르지 않았습니다.
  - 내 앞 감사 `audit_prerun\verif_c8_t8.md:154`는 "P8-0 114줄·기준 sha | gate:249-266·84-87 | 같음"으로 상수와 sha만 대조했습니다.
  - `audit_t8ppp\verif_t8ppp_prejudge.md:111`은 gate 하위 명령을 J-P3 설정 점검에서 "해당 없음"으로 뺐습니다.
  - 기준 파일은 실행 전에도 열 수 있었습니다. "기준을 자기 자신과 대조"하는 스모크 한 번이면 잡혔습니다. **감사자 누락으로 공개합니다.**
- **권장 조치**: 위임 필요(python-expert) 1을 봅니다. 처리 길은 확인 필요 1입니다.

### [실행 전 수정][E] M-1. reference 쪽 줄 문제가 run 실패 수에 섞임
- 근거: `gate:261-263`에서 run과 reference가 같은 `problems` 목록을 씁니다. 그 길이가 `:269`에서 `"run line problems: N"`(failures)이 됩니다.
- 174 = run 87 + reference 87입니다.
- 실패 시나리오: 기준 파일 쪽 결함(오류 줄, 해시 없음)이 "run 실패"로 표시됩니다. 원래는 고정 입력 결함(setting_defect)인데, 상태 순서상 failed로 갑니다.
- 권장: B-1과 함께 run·reference 목록을 나누고, reference 쪽 문제는 setting_defect로 둡니다(python-expert).

### [실행 전 수정][R] M-2. P8-5 문턱 15의 근거와 예상 "같은 쌍" 수가 봉인 전에 기록되지 않음
- 근거: 문턱 15는 내 앞 감사 M-9의 "최소 줄 수를 적어라" 권고(`audit_preseal\verif_preseal_s8r.md:150-156`)에 대한 개정 3 응답에서 나왔습니다(`audit_preseal\control_rev3_handback_notes.md:15`). 거기에는 숫자만 있고, 23키에서 몇 쌍이 같을지에 대한 사전 예측이나 근거가 없습니다.
- 같은 메모 `:30`은 "재생에서 mid 이동은 다리 단위로 흔해(방향 A 21/67) 고른 줄이 최소 수에 못 미칠 위험이 컸다"고 적었습니다. 위험은 알고 있었습니다.
- 영향: 실현된 14 < 15가 "예상 밖"인지 판단할 사전 기준이 없습니다. 그래서 문턱을 고치는 길은 모두 결과를 본 뒤의 결정이 됩니다.
- 다음 판에서 권장: 최소 쌍 수 관문에는 봉인 전에 예상 쌍 수와 그 계산 출처를 함께 적습니다(control-expert, stats-design-expert).

### [실행 전 수정][R] M-3. 4단계 멈춤 칸과 P8-5 행의 판정 불가 처리가 다름
- 근거
  - `spec:201`의 4단계 멈춤 칸: "실패·`setting_defect`면 멈추고 묻는다". 판정 불가가 없습니다.
  - `spec:203`의 6단계: "실패·`setting_defect`·판정 불가 → …"
  - `spec:365`의 P8-5 행: "15줄 미만이면 판정 불가(멈춤)"
- 지금은 P8-5 행 문장으로 멈춤이 분명합니다. 그러나 4단계 표만 읽으면 판정 불가가 통과로 넘어갈 여지가 있습니다.
- 확인 필요 2에 함께 올렸습니다.

### [기록][E] R-1. P8-5에서 판정 안 된 9쌍은 규칙이 정한 "같지 않음" 쌍입니다
- 도구 경로를 차례로 지우면 9쌍이 남는 길은 하나뿐입니다(`gate:359-404`).
  - `pairing_problems` 0: 23키 모두 켬·끔 팔이 1줄씩 있어 생산자 결측이 없습니다(`:295-297`).
  - `unread` 0: 스케일 기록 결측이 없습니다(`:370-372`).
  - `malformed` 0: P8-5 선택자는 bool/None만 냅니다.
  - `hashless` 0.
  - 남는 길은 `:376-377`(`is_same_scale` 거짓)뿐입니다. 9쌍 모두 "라운드 수 또는 라운드별 `twist_stiffness_scale`이 두 팔에서 다름"입니다.
- 규칙 대조: `spec:365`의 "같음 = 라운드 수가 같고 라운드별 스케일이 비트 단위로 같다(None 포함)". 도구 `:312-319`는 두 리스트를 `json.dumps` 텍스트로 비교합니다.
  - float의 `repr`는 왕복이 정확하고, 두 팔 모두 같은 코드가 써서 표기 차이가 생기지 않습니다. 정의 차이는 없다고 봅니다.
  - 예외는 NaN payload 같은 극단 경우뿐입니다[추정].
- 분류: 9쌍은 규칙상 판정 밖입니다. 도구 필터 결함이나 생산자 결측이 아니고, 기록 실패 (1)도 아닙니다(`spec:345`의 목록은 기록 키 결측입니다).
- 9쌍을 "라운드 수가 다름"과 "값이 다름"으로 나누려면 블라인드 원자료가 필요합니다. 확인 필요 4로 올렸습니다.
- 문턱 읽기: "같은 줄이 15줄 미만"의 줄은 키(쌍) 단위로 읽는 것이 자연스럽고, 도구(`:398`, `selected < 15`)도 그렇게 셉니다. 두 팔 줄 수(28)로 읽으면 P8-15의 "20줄"(27키, 54줄)이 거의 공허해지므로 그 읽기는 맞지 않습니다.
- p85.json은 failures []이고 비교된 14쌍의 `differing`은 []입니다. 판정 불가 상태이므로 판정서에는 "비교된 쌍의 차이 0"을 기록으로만 적고 통과 근거로 쓰지 않습니다.

### [기록][I] R-2. 판정 출력 8개의 정체성 — 모두 같음
- 도구: 즉석 스크립트 `ident.py`(python-dev). `record_check.py identity`는 쓰지 않았습니다. 이 json들에는 레코드 목록이 없어 `no_records`가 나기 때문입니다.
- 8개 모두 같은 값입니다.
  - `judge_code.head` 2263b2461238…, `is_clean` true
  - `spec_v8_sha256` 35f9eba8
  - `inputs.rows.run_commit` 56849248
- `.done` 확인
  - 각 `step_done_sha256`을 `.done`에서 다시 잰 값과 맞습니다(8/8).
  - `.done` 안은 모두 exit 0, commit 56849248, end identity 56849248·clean, `previous_attempts` 0입니다.
- 기준 sha
  - p80 기준 `pinned` true, d60306db를 다시 재어 맞습니다.
  - p816 기준 89efe66f를 다시 재어 맞습니다.
- 출력 파일(`impl_*_a1\*.jsonl`) sha는 블라인드라 다시 재지 않았습니다(검사하지 못한 것).

### [기록][R] R-3. 결함은 p80에만 있습니다
- p88·p815는 같은 `row_identity`를 쓰지만 짝 키가 (팔, 블록의 plant, 키)라서 맞습니다(`gate:288`).
- t8은 setting을 남기는 자체 키를 씁니다(`:437-438`). p816은 `p816_compare`를 씁니다.
- 그래서 B-1이 이미 pass로 판정된 6개 관문의 내용을 오염시키지는 않습니다. 다만 단일 T8 문제는 남습니다(확인 필요 1).

## 규칙↔도구 대조표

| 항목 | 규칙 | 도구 | 판단 |
|---|---|---|---|
| P8-0 대상 줄 | `spec:361` 114줄, 줄별 해시 | `gate:91` `P80_LINES = 114` | 같음 |
| P8-0 줄 정체성 | 114개 서로 다른 job(생산자 `ed7_probe.py:193-197`, setting = 플랜트) | `gate:94, 221-224`가 setting을 빼 27키로 접음 | **다름(B-1)** |
| P8-0 중복·결측 = 실패 | `spec:361` "다르면 멈춤", docstring `gate:9-12` | `:251-253` "twice" | 실제 중복이 아닌 도구 산물(B-1) |
| P8-0 run·기준 문제 구분 | 기준은 고정 입력(`spec:345`: 목록 밖 = setting_defect) | `:261-269`가 한 목록으로 run 실패에 합침 | 다름(M-1) |
| P8-5 같음 정의 | `spec:365` | `gate:302-319` | 같음 |
| P8-5 스케일 기록 결측 | `spec:365` 판정 불가 | `:394-395` | 같음(이번 0건) |
| P8-5 최소 | `spec:365` 15줄 미만 판정 불가(멈춤) | `:98, 398-399` | 같음 |
| 상태 순서 | `spec:338` | `jp3_ed8_rules.py:81-93` | 같음 |
| 4단계 멈춤 | `spec:201` 실패·setting_defect | – | P8-5 행 "(멈춤)"과 표 칸이 다름(M-3) |

## 판정서에 적는 방법(분류안, 결정 아님)
- **P8-0**
  - 도구 출력은 failed(종료 1)입니다. 그러나 원인은 판정 도구의 키 결함입니다. 근거는 B-1, 특히 기준을 자기 자신과 대조해도 같은 서명이 재현된다는 점입니다. 관문 실패(명령 해시 차이)는 아닙니다.
  - setting_defect "reference 27 jobs"도 고정 입력 결함이 아닙니다. 기준 sha는 봉인값과 맞습니다.
  - 규칙 10(`spec:346`, "계산되지 않은 판정 항목 … 판정 불가")로 보면 **P8-0 = 판정 불가(87/114줄 비교 안 됨, 도구 결함)**가 규칙에 맞는 분류입니다.
  - 비교된 27줄의 같음은 같은 setting 줄끼리의 짝이 보장되지 않습니다(B-1). 그래서 기록으로만 적습니다.
  - 실패 처리표(`spec:201`)의 "C8 교체" 질문 대상은 아닙니다. 생산자 결함 근거가 없습니다.
- **P8-5**
  - 판정 불가(같은 쌍 14 < 15, `spec:365`, 멈춤)입니다. 9쌍은 규칙상 판정 밖입니다(R-1).
  - failures는 비었습니다. 실패도 setting_defect도 아닙니다.
- 두 건 모두 "결과(상태)를 본 뒤의 처리"이므로 판정서 공개 항목에 넣습니다.

## 확인 필요
1. **P8-0 처리 길**(사용자 결정. 규칙 해석은 control-expert)
   - (가) **T8⁗ 도구 수정**
     - 내용: p80 전용 키(setting 유지)와 M-1, 생산자 꼴 시험을 넣고 verif 재감사를 거칩니다.
     - 11.2 범위(04_scripts·05_tests만 바뀌고 C8 바이트는 그대로)에 맞고, C8 재실행·교체가 필요 없습니다.
     - 단일 T8 읽기(`verif_t8p.md:15`)를 지키려면 이미 pass인 6개와 p85를 포함해 4단계 8개를 모두 T8⁗로 다시 판정하고, 6·8단계도 T8⁗로 갑니다.
     - 다른 7개는 결정적이라 같은 상태가 나와야 합니다. 다르게 나오면 그 자체가 발견입니다.
     - 결과(상태 서명)를 본 뒤의 도구 수정이므로 공개합니다. 다만 키는 규칙 `spec:361`과 생산자 `job_key`로 정해지고, 비교되지 않은 87줄의 해시 결과는 아직 아무도 보지 않았습니다. 그래서 결과에 맞춘 선택은 아니라고 적을 수 있습니다.
     - `spec:208`의 "재실행하지 않는다"가 판정 도구를 다시 돌리는 것까지 막는지는 문면이 정하지 않습니다.
   - (나) **정오**: (가)를 허용하는 문장(판정 후 판정 도구 결함의 처리, 규칙 10 목록에 "판정 도구 결함 = 판정 불가" 추가)이 필요할지 control-expert가 정합니다. 114줄 범위를 줄이는 정오는 결과를 본 뒤 관문을 바꾸는 것이라 권하지 않습니다.
   - (다) **그대로 인정**
     - failed로 두면 구현 결함으로 잘못 기록되고, C8 교체 질문까지 이어집니다. 근거와 어긋납니다.
     - 판정 불가로만 두면 P8-0이 관문으로서 끝나지 않아 4단계가 미완입니다. Y8-9가 걸린 Mslow D키 12줄이 확인되지 않은 채 남습니다.
2. **P8-5 처리 길**
   - (가) **판정 불가 인정**: P8-5 행대로 멈춥니다. 5·6단계로 넘어갈지는 사용자 결정입니다. 4단계 표 칸과 P8-5 행 문장이 다르니(M-3) 어느 쪽을 따르는지 판정서에 적습니다.
   - (나) **정오로 문턱을 14 이하로**: 실현값 14를 본 뒤라 결과 의존 변경입니다. stats-design-expert 평가와 공개가 필요하고, 권하지 않습니다.
   - (다) **키를 더해 다시 실행(C8에서 새 단계)**: P8-5 키 집합(23키) 정오가 필요합니다. "9쌍이 다르다"를 안 뒤 키를 고르는 위험이 있으니, 키는 규칙 문장으로 먼저 고정합니다.
   - (라) **대체 증거**(16절 N-1 전제 시험 둘, P8-6)를 정오로 인정: 결과를 본 뒤의 결정입니다.
   - 어느 길이든 도구 상수(`MIN_SAME_PAIRS`)가 바뀌면 다시 판정 커밋이 바뀌고, 1의 단일 T8 문제가 같이 생깁니다.
3. 4단계 멈춤 칸(`spec:201`)에 판정 불가가 들어가는지(M-3). 문면 해석은 control-expert 몫입니다.
4. (선택) P8-5 9쌍을 "라운드 수가 다름"과 "값이 다름"으로 나눌지. 원자료 `impl_p85_a1\p85.jsonl`의 `probe_stiffness_record` 길이를 팔별로 세어 건수만 내야 하므로, 메인의 블라인드 목록 조정이 필요합니다. 판정 분류에는 필요 없어 멈추지 않았습니다.
5. (선택) B-1 (a)를 완전히 지우려면 `impl_p80_a1\ed7_probe_a2.jsonl`에서 (job + setting) 키가 114개 모두 서로 다른지 건수만 세야 합니다. 값과 해시는 출력하지 않는 방식입니다. 블라인드 조정이 필요합니다. 길 (가)로 다시 판정하면 그 판정 출력이 이 확인을 대신합니다.

## 위임 필요
- **python-expert**(T8⁗를 택하면, ed8-judge3 위 새 커밋, C8 불변)
  1. `jp3_ed8_gate_judge.py:242-275`: p80 전용 키를 만듭니다(job에서 `mask`·`t4h_dir`만 빼고 setting 유지, `_part`·`_r79_plan`의 처리는 생산자 `run_v5.job_key`와 맞춤). `row_identity`는 팔 짝 관문용으로 그대로 둡니다.
  2. `:261-269`: run·reference 문제 목록을 나누고, reference 쪽은 setting_defect로 둡니다(M-1).
  3. 시험 두 가지
     - 생산자 꼴: 같은 case를 6개 setting × 15 + 2 × 12로 둔 114줄에서 pass, setting 하나만 빠지면 missing 실패.
     - 실제 고정 기준 파일을 자기 자신과 대조해 pass·jobs 114(기준 sha 단언, 파일이 없으면 skip이 아니라 실패. 또는 메인 checkout 자료로 `worktree_tests.py`).
- **control-expert**: 확인 필요 1(나)·2·3의 문면 해석, 정오가 필요한지와 그 문장.
- **stats-design-expert**: 확인 필요 2(나)를 택하면 그 평가.
- **tools/verif 후보**(python-expert): "기준 자기 대조" 검사
  - 입력: 판정 도구의 비교 함수 또는 키 경로 설정, 기준 jsonl, 규칙 줄 수.
  - 출력: 서로 다른 조인 키 수 대 줄 수, 중복 키 분포.
  - 종료 코드: 다르면 1.
  - 기준이 블라인드가 아닌 관문에서 실행 전에 돌립니다.

## 메인 세션 권고
- 확인 필요 1·2의 사용자 결정 뒤, T8⁗이면 python-expert → verif 재감사 → 4단계 8개 판정을 새 출력 폴더(`judge_<T8⁗ 앞 8자>`)에 다시 돌립니다. 판정 도구 실행은 메인이 합니다.

## 검사하지 못한 것
- 판정 대상 원자료(`impl_*_a1\`, `l1ref_a1\`): 블라인드. 그래서 p80 run 줄의 (job + setting) 유일성, P8-5 9쌍의 세부 분류, 출력 jsonl sha 재측정은 하지 못했습니다.
- `run_stage4_gates_t8ppp.ps1`는 이번에 다시 읽지 않았습니다(앞 감사 대상).
- p88·p815·p816·t8·cases·l1ref의 판정 내용은 보지 않았습니다(정체성과 상태만).

## 실행한 검증
- python-dev `-X utf8 -I -B`(`MKL_THREADING_LAYER=TBB`)
  - `depcheck.ps1`: STAMP
  - `source_guard snapshot`/`verify --strict-additions`
  - 즉석 스크립트 `ref_struct.py`(기준 구조), `ident.py`(8개 정체성, `.done` sha 재측정, p80 중복 다중집합, 기준 키별 첫 setting·해시 종류 수)
- dynamics-dev `-X utf8 -I -B`(cwd는 scratchpad, `PYTHONDONTWRITEBYTECODE=1`, `NUMBA_CACHE_DIR`은 scratchpad)
  - `selfref.py`: 잠긴 gate를 import해 `judge_p80(기준, 기준)`을 진단으로 재현하고, 키에 setting을 남긴 경우를 대조했습니다. 판정에는 쓰지 않았습니다.
  - 뒤에 ed8-judge3 `status --porcelain --ignored`는 빈 출력, HEAD 2263b246.
- git(Bash, 조회만): `log` 파일 이력과 `log -L`. `RUNTIME_JOB_KEYS`는 T8 ecf6c142에서 들어온 뒤 바뀌지 않았습니다.
- 읽은 파일
  - p80.json·p85.json 전체
  - `impl_p80.done`·`impl_p85.done`
  - `_identity_checks\impl_p80_a1.md`·`impl_p85_a1.md`
  - 명세 337~446행과 191~212행(나머지는 Grep)
  - `jp3_ed8_gate_judge.py` 전체
  - `ed7_probe.py` 20~259행
  - `test_ed8_gate_judge.py` 1~160행
  - `prejudge_report.md` 전체
  - `control_rev3_handback_notes.md` 전체
  - `.claude\blind_paths.json`
- 검색 범위(모두 단일 파일이거나 블라인드를 품지 않은 폴더)
  - Grep 명세 1개, `verif_t8ppp_prejudge.md`, `verif_t8p.md`, `verif_preseal_s8r.md`
  - Grep 폴더 `ed8_design`(`*.md`), `ed8_design\audit_prerun`(`*.md`), `ed8-judge3\05_tests`(`*.py`), `ed8-judge3\04_scripts\04_hydraulic\coupled`(`ed7_probe*.py`), `jp3_ed8_rules.py`
- 공개: 처음 PowerShell `Test-Path` 묶음 명령 하나가 blind_guard에 막혔습니다(`impl_p80.done` 등 단일 경로 목록, 변수 대입 판정). 그 뒤 블라인드 아닌 경로만 다시 지정했고, `.done`은 Read로 읽었습니다.
- 만든 뒤 지운 파일: scratchpad `verif-p80p85\`(스크립트 3개, `guard.json`, numba 폴더). 폴더째 지웠고, 지운 뒤 `Test-Path` False를 확인했습니다.
- 메모리: `agent-memory\verif-protocol-auditor\audit_pitfalls.md`에 "공용 줄 키 함수가 줄별 기준 관문을 접음, 실행 전 기준 자기 대조" 1항을 Edit로 더했고, `MEMORY.md` 색인 줄도 고쳤습니다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v8_rules.md 35f9eba8…, jp3_remedy_spec_v8_rules.md.sha256 e19aaa48…, ed7_probe_a2.jsonl d60306db…, jp3_ed8_gate_judge.py 17fac227…, p80.json 1077f3ab…, p85.json 8db37778…, p88.json 39c7909c…, p815.json 990b985a…, p816.json b14d770b…, t8.json eb0c4aef…, l1ref.json 20815752…, cases.json 54999935…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
