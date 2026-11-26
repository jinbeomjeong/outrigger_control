# S8-R 개정 3 재감사 (verif-protocol-auditor, 2026-11-26)

## 감사 요약
- **본 결과**: 판정 대상 결과(census·G′)는 아직 없다. 본 것은 입력 설정과 설계 입력뿐이다.
  - 판 7 `j9_main.jsonl`·`sens_keys_ed7.json`·`confirm_g1_grid171.json`·D 키 blob: `job.case`와 twin 필드 이름(입력 설정)만 셌다.
  - `python_0c2_events/event_names_0c2.json` 앞 60줄: 입력 sha와 코드 사실이다.
  - `spec_drafts/…rev2a.md`의 P8-14 줄 앞부분.
- **대상**: `jp3_remedy_spec_v8_rules.md` 개정 3, sha256 `f55080447afb1e4e33b79bf8a3883399c81a5418b4d38642d9119c4690fddcfe`. 감사 시작과 끝에 sha가 같았고, 메인이 Q8-21을 고친 뒤의 판이다(mtime 17:45:26). 대조 메모는 `audit_preseal/control_rev3_handback_notes.md`다.
- **판정**: **차단 0 / 실행 전 수정 4 / 기록 4**. 지난 감사의 B-1, M-1~M-9, R-1~R-4는 모두 해소됐다. 실행 전 수정 4건은 문면 몇 줄이라 봉인 전에 고치기를 권한다. 다만 고치지 않아도 결론이 틀어지는 경로는 찾지 못했다.
- **봉인 조건**: 0c′ 종료 0, 그리고 근거 표 SUMS 기입 뒤 바뀐 칸만 확인하는 것(아래 권고).

## 지난 항목 해소 대조
| 항목 | 개정 3 위치 | 판단 |
|---|---|---|
| B-1 `fast` 결측 | 6.3 `:259~265`, F8-20 `:108`, 0c′ `:193`, Y8-6 `:436` | **해소.** E 후보는 입력 사건(twin `event`, 없으면 사례 기본값)으로 정하고 `fast`는 읽지 않는다. 결측 규칙은 `reapproach_starts`에만 걸린다. 독립 확인은 아래 0c′ 절 |
| M-1 VBM/LSM 대응 | `:215` | 해소. j9_main sha `c89ec827ce541a53127a0115b8e1185b35e50df9cea2612d4a74b40cc618c122`를 재계산해 일치 |
| M-2 P8-16 | `:374`, 머리말 `:39` | 해소. 단일 원천 `89efe66f…`(일치), 계획 파일 4개 모두 `99e506534669f477…`(재계산 4/4 일치), 완결성 27/27·27/27, 결측 = 실패, 두 시점 |
| M-3 n_min·해당 없음 순서 | 7.3 `:289~297`, 7.4 `:303~305` | 해소(새로 생긴 사소한 순서 문제는 아래 N-3) |
| M-4 census 키 sha | `:219`, 11.3 `:353`, P8-10 `:368`, 14절 | 해소 |
| M-5 D 키 커밋 경로 | `:217` | 해소(잠금 유지 문장 있음) |
| M-6 SUMS | `:37`·`:42` | 해소. `python_0c_keys` SUMS `d212f2d5…`·`layer_keys_0c.json` `8fc9731b…`는 재계산해 일치. `python_p1_p3/SHA256SUMS`가 생김(17:18:36). 근거 표의 나머지 폴더 SUMS sha는 아직 빈칸(메인 기입 예정) |
| M-7 상태 줄·메모·자리 이름 | `:3`, 끝 메모 제거, `:181` | 해소(placeholder 전체 실행 unfilled 0) |
| M-8 O8 | `:68~71` | 해소. O8-9~O8-12가 transcript 사실과 지난 보고 공개 1~9와 맞음 |
| M-9 0건 관문 | P8-5·P8-8·P8-15 `:362`·`:365`·`:373` | 해소. P8-5 기준 변경은 아래 N-1 |
| R-1 문구 명확화 | 13절 18 `:394` | 해소 |
| R-2 main.jsonl 전체 sha | `:221` | 해소 |
| R-3 C-D 칸 | `:231`·`:252` | 해소 |
| R-4 k_N 재계산 | `:309` | 해소 |
- 이어받는 sha는 재확인했고 모두 그대로다: v7 `10902ffd…`, 정오 1 `74c49bda…`, 판정서 `994102b7…`(채운 값 `:19`).

## 발견 사항 (심각도순)

### [실행 전 수정][R] N-1. P8-5 줄 선택 기준("두 팔의 `twist_stiffness_scale`이 모든 라운드에서 같은 줄")은 조건부로만 충분 조건이다
- **현재 코드(ed8-impl 7fc83456)가 받치는 부분**
  - PSW가 명령에 닿는 길은 `state.twist_stiffness_scale` 하나다. 이 값은 `_twist_gain_scale`(`c2.py:7721~7727`)과 `_twist_gain_stiffness_N_m`(`:7729~7734`)을 거쳐 비틀림·가드 이득으로 간다.
  - 이 값은 `_update_twist_stiffness_scale`(`:9892~9925`)에서만 쓰인다.
  - `twist_stiffness_raw_ratio`·`twist_stiffness_leg_count`는 기록에만 쓰인다(`:5008`·`:5010`·`:9953`).
  - 경고 `WARN_PROBE_STIFFNESS_OUT_OF_RANGE`는 `_add_event`(`:9502~9505`)로 목록에 붙고 로그만 남긴다. 제어기가 사건 목록을 읽는 곳은 `:6138`·`:7079`·`:7096` 셋이고, 모두 다른 이름의 중복 방지다.
  - 따라서 현재 코드에서는 "스케일 열이 같으면 명령이 같다"가 성립한다.
- **충분 조건이 되려면 남는 전제**: PSW 구현(Y8-1, 아직 없음)이 판 8 스케일 경로 밖에서 아무것도 바꾸지 않아야 한다. 구체적으로 `ProbeResult`의 기존 필드(`incremental_stiffness_N_m`, mid 관련 값)를 덮어쓰지 않아야 한다. 이 필드들은 접지 판정, 탐침 중점, 마찰 보정에 쓰인다(`:9897~9898` docstring).
- **실패 시나리오**: Y8-1이 mid 읽기를 `ProbeResult`에 덮어쓰는 식으로 구현되면, 스케일이 같은 줄에서도 명령이 달라진다. 반대로 명령은 같은데 다른 길의 차이가 숨는 경우도 생긴다. 그러면 P8-5가 원인을 잘못 가린다.
- **권장**
  - control-expert(문면): P8-5에 "PSW 구현은 새 필드(`scale_stiffness_N_m` 등)와 `_update_twist_stiffness_scale`만 바꾼다"를 전제로 적는다. 같음의 정의도 적는다: 두 팔의 라운드 수가 같고, 라운드별 스케일이 비트로 같다(None 포함). 기록 키가 없으면 판정 불가다.
  - python-expert(시험): PSW 켬·끔에서 `ProbeResult` 기존 필드가 비트로 같다는 시험을 넣는다. 새 필드를 읽는 곳이 `_update_twist_stiffness_scale`뿐이라는 것은 정적 시험으로 확인한다.

### [실행 전 수정][R] N-2. 1단계 P8-16의 "다르면 구현을 고쳐 다시 돈다"가 일반 규칙과 부딪친다
- **근거**
  - `:195`(1단계 "판정(관문)", "다르면 구현을 고쳐 다시 돈다")와 `:348`이 있다.
  - 바로 아래 일반 규칙 `:205`는 "판정 실패는 멈추고 묻는다. 재실행하지 않는다"이다.
  - 또 4단계 실패 뒤 C8을 바꾸면 "2단계부터"(`:198`·`:349`)다. 그러나 구현을 고치면 1단계 P8-16 사전 실행도 다시 해야 한다.
- **권장**
  - `:205`에 "1단계 P8-16 사전 실행은 구현 관문이라 예외(기준은 바꾸지 않음)"를 적는다.
  - C8 교체 때 시작 단계를 "1단계(P8-16 사전 실행)부터"로 고친다(control-expert).

### [실행 전 수정][R] N-3. 7.3·7.4의 E 합침 시점 순서
- **근거**
  - 7.3 2(`:291`)는 n_E < 16일 때 "A/A 기회·실패도 합친다"고 적었다. 그런데 A/A 점검은 그 뒤 4번이다.
  - 7.4(`:305`)의 "n_AA,E = 0이면 E를 N에 합친다"는 4번 안에서 일어난다. 그 뒤 N층 CP95 점검과 n_AA,N = 0 점검을 합친 값으로 다시 하는지 적혀 있지 않다.
- **권장**: 4번 안의 순서를 적는다. "E A/A 점검(실패 ≥ 2 멈춤 / n_AA,E = 0 → 합침) → 합친 값으로 N CP95와 n_AA,N 점검"(control-expert, Y8-6 T8 구현과 시험).
- 합치면 n_N은 늘기만 하므로 3번(n_N < 200)을 다시 볼 필요는 없다.

### [실행 전 수정][S] N-4. 봉인 직전 메인 기입 칸과 실행 전 초안 사본
- **근거**
  - 근거 표 `:22`는 "폴더 SHA256SUMS sha는 봉인 직전에 메인이 이 표에 기입"이라고 적었다. 그런데 지금은 여러 폴더 칸이 비어 있다: `dynamics_d1_d3`·`hydraulics_h1_h2`·`stats_s1`·`python_p1_p3`·`dynamics_u832_o00`·`control_k1_window`·`control_early_handover`·`stats_s8r`·`python_q8_checks`·`control_level_deadlock`.
  - 그러므로 이 감사가 본 sha `f5508044…`는 봉인본이 아니다.
  - 새로 찾은 `ed8_design/spec_drafts/` 폴더에 초안 판별 사본이 있다(rev0 15:27, rev1 15:36, rev2a 16:25:29, rev2b 16:28:45, rev2c 16:59:14 = 지난 감사 sha `5fdc0d7c`).
    - rev2a의 P8-14 줄은 실행 전 문구다("키는 `control_level_deadlock/report.md` 6절" 포함). P8-14 원자료 첫 mtime 16:34:53보다 앞선다.
    - 이 폴더는 SUMS가 없고 근거 표에도 없다.
- **권장(메인)**
  - SUMS 칸을 기입한 뒤 바뀐 줄이 그 칸들뿐인지 diff로 확인한다(git 밖이면 `fc.exe` 또는 줄 대조). 확인 뒤 `.sha256`을 만든다.
  - `spec_drafts/`에 SHA256SUMS를 만들고 근거 표에 한 줄 더한다. 그러면 13절 18의 "실행 전 고정"을 transcript뿐 아니라 파일로도 받친다(mtime은 사본 시각이라 [추정] 근거). 이 줄을 더하면 그것도 봉인 전 문면 변경이다.

### [기록] R-5. seed 20261127 계산 근거 — 맞음
- 7.2 `:284`의 규칙대로 계산했다. 봉인일 20261126은 판 7 G1 seed와 충돌한다(v7 `:723`). 그래서 +1 → 20261127이다.
- 20261127이 쓰인 곳은 없다. 다음을 파일 경로를 하나씩 지정해 찾았고 모두 0건이다.
  - `jp3_remedy_spec_v5.md`, v5 정오 1~8, v6, v6 정오 1, v7, v7 정오 1, ed5·ed7 판정서
  - `ed6_design/`·`ed7_design/`·`ed8_design/`의 md·py·json·txt
- v8 자신에만 5곳 있다(`:83`·`:283`·`:284`·`:396`·`:436`).
- 봉인이 11-28 이후로 넘어가면 개정이 필요하다는 문장(`:284`)도 맞다.

### [기록] R-6. 0c′ 독립 구조 확인 — 사건 이름은 1043줄 모두 정해진다
값은 출력하지 않았다. `job.case`와 twin 필드 이름만 셌다.

| 단계 | 사건 행 | 사건 이름이 정해지는 방식 |
|---|---|---|
| C-J (j9_main) | R12 160 / R14 10 / R15 10 / R16 20 = 200 | R12 twin 140줄은 필드가 `{level, leg, fs_kN}`뿐이라 `event`가 없다 → 사례 기본값 G4. 나머지는 twin이 없어 기본값(`verdict_cases.py:153~171`, R14·R15·R16 RE1bF) |
| C-S | R12 180 / R14 20 / R15 20 / R16 40 = 260 | C-J와 같다 |
| C-D | 12 job | twin `event` 명시(FS24 4, G4 4, RE1bF 4) |
| C-G | 171 | twin `event` 명시 |
- R13(사례 기본 사건 SS, `r67.EVENTS`에 없음)은 census에 0줄이다.
- `r67_g1_screen.py:96~98·120~121`로 확인한 빠르기: G4 5.75 mm/s(빠르지 않음), RE1bF 600 mm/s, FS24 80 mm/s. FS24·G4 → N과 F8-20 문장이 코드와 맞는다. G′ (나)의 25 mm/0.05 s·30 mm/0.04 s는 RE1bF 변형이라 E 후보다.
- 이 확인으로 C-J E 후보는 R14·R15·R16 40줄, C-S는 80줄로 좁혀진다는 것이 드러난다. 13절 9에 적힌 대로 census 판정에는 영향이 없다(모든 칸 0).

### [기록] R-7. ref_check 누락 11건 — 지난 감사와 같은 분류, 새 결함 없음
- 상대 경로 기준 오탐 3: `:25`, `:40`×2. 세 폴더 모두 실제로 있다.
- 다른 브랜치·worktree 코드 3: `ed8_probe.py`·`lock_start_b.py`·`ed7_probe.py`.
- blob 경로 1: `:217`(커밋:경로 형식이라 도구가 풀지 못한다. sha는 일치).
- 생성 예정 3: `census_keys_ed8.json`·`heldout_g_ed8.json`·`ho_k_selection.json`.
- 정정 공개 문장의 옛 경로 1: `:395`.

### [기록] R-8. 0c′ 진행 상태
- `ed8_design/python_0c2_events/`에 `event_names_0c2.py`(17:48:50)와 `event_names_0c2.json`(17:48:58)만 있다. 보고·SUMS는 아직 없다.
- json 앞부분의 입력 sha 6개는 모두 match다. `default_event_in_EVENTS` R13 false는 위 R-6과 같은 뜻이다.

## 0c′를 봉인 조건으로 둘지 — 권고: **둔다**
- 6.3 `:265`가 "사건 이름을 정할 수 없는 사건 행 = `setting_defect`"로 정했고, 4절 `:193`이 "봉인 전에 정한다"고 적었다. 문면이 이미 봉인 전 확인을 전제로 한다.
- 비용이 작다. 이 감사의 독립 확인(R-6)과 python 결과가 같은지 대조할 수 있다.
- 봉인 조건으로 적을 것
  - 0c′ 종료 0이고, 단계별 "사건 행 / 이름 정해짐 / 정할 수 없음 0"이 R-6 표의 수와 같다(C-J 200, C-S 260, C-D 12, C-G 171).
  - `python_0c2_events/` SUMS가 있고 근거 표에 오른다.
  - 어긋나면 봉인을 멈추고 6.3을 다시 본다.
- 4절 0행(`:194`) 멈춤 칸에 "0c′ 미완료·불일치"를 더하기를 권한다(N-4와 함께 봉인 전 문면 변경).

## 확인 필요
- 없음. Q8-21은 메인이 사용자 결정으로 닫았고(`:424`), 7.4 `:305`와 맞다.

## 위임 필요
- control-expert: N-1·N-2·N-3 문면. 필요하면 N-4의 근거 표 한 줄과 0행 멈춤 칸.
- python-expert: N-1 시험(`ProbeResult` 기존 필드 불변, 새 필드를 읽는 곳 정적 확인). N-3 순서를 T8에 반영. 0c′ 보고와 SUMS.

## 메인 세션 권고
- 0c′ 보고를 받으면 R-6 표와 수를 대조한다.
- `spec_drafts/` SUMS를 만든다.
- 근거 표 SUMS 칸을 기입하고, diff로 그 칸만 바뀌었는지 본다.
- 그 뒤 `.sha256`을 만들고 `seal_check`를 돌린다.
- `audit_preseal/` SUMS는 이 보고를 저장한 뒤 마지막에 쓴다.

## 검사하지 못한 것
- PSW 구현이 아직 없어 N-1의 충분성은 7fc83456 코드와 명세 3.3 문장으로만 판단했다.
- 0c′ 최종 보고는 아직 나오지 않았다.
- 메인이 SUMS 칸을 기입한 뒤의 최종 봉인본 sha는 보지 못했다.

## 실행한 검증
- **인터프리터**: python-dev `-I -B`(`MKL_THREADING_LAYER=TBB`). 프로젝트 모듈은 import하지 않았다.
- **placeholder_scan**(`--allow` S8C 11개)
  - `--pattern-set both --skip-inline-code`: 종료 0(unfilled 0, skipped 50).
  - 전체: 종료 0(unfilled 0, allowed 15).
- **ref_check**: `--no-git --exclude …/j9_runs/606f8713/cdry_a1 --exclude …/prelaunch_j9/ed6_inputs/x11 --exclude .claude`, 종료 1. missing 11은 R-7로 분류했고, untracked 1은 O8-12 문장 속 `prelaunch_j9/ed6_inputs/`다.
- **해시 재계산**(`Get-FileHash`): j9_main, 계획 파일 4개, `python_0c_keys/SHA256SUMS`·`layer_keys_0c.json`, `p814_selection.json`, `spec_drafts/…rev2c.md`(= `5fdc0d7c`).
- **seed 검색**: 파일 경로를 하나씩 지정해 `Select-String`. `ed6_design`·`ed7_design`·`ed8_design`은 Grep(glob md·py·json·txt, 파일 목록 모드).
- **코드 읽기**(ed8-impl worktree, 파일과 하위 폴더 지정)
  - `c2.py` 7715~7748·9502~9526·9890~9929·6130~6140
  - `03_src/outrigger_sim/control` Grep 2회(glob `*.py`)
  - `c2.py` Grep 2회
  - `r67_g1_screen.py` Grep 1회
- **즉석 스크립트**: `cases.py`와 `-c` 한 줄 셋. scratchpad `verif-ed8-preseal-r3\`는 보고 전에 지웠다(Test-Path False).
- **원본 불변**: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v8_rules.md f5508044…, control_rev3_handback_notes.md 7c4e3d77…, 디렉터리 목록 동일, ~$ 임시 파일 없음) · 경고: 형제 항목 수정 시각만 변경 1건(ed8_design). 이 경고는 감사 중 python-expert가 `python_0c2_events/`를 쓴 탓이다.
- **사용한 스킬**: 없음

## 공개(행위 그대로)
1. 블라인드를 품은 상위 폴더(`j_p3_cause`, `j9_runs`, `prelaunch_j9`, `ed5_design`, 저장소·worktree 루트)는 Grep·Glob·목록의 path로 쓰지 않았다. Bash 파이프도 쓰지 않았다.
2. `ref_check`가 블라인드 파일의 부모 폴더 `prelaunch_j9/ed6_inputs/`를 stat했다. 이 폴더는 명세 O8-12 문장이 가리키고, 제외 인자는 `x11`이라 부모는 빠지지 않았다. 출력은 "작업 트리에만 있음" 한 줄이고, 폴더 안 목록은 없다.
3. 판 7 `j9_runs/8a2a52ce/j9main_a1/j9_main.jsonl`(블라인드 아님)을 파일 경로로 지정해 `job.case`와 twin 필드 이름만 셌다.
4. `ed8_design` 아래 하위 폴더 목록은 비재귀로 봤다: `ed8_design` 자체, `audit_preseal`, `python_0c2_events`, `spec_drafts`, `python_p1_p3`.
5. 진행 중인 `python_0c2_events/event_names_0c2.json` 앞 60줄을 읽었다(입력 sha·코드 사실).
6. 쓰기는 scratchpad 하위 폴더뿐이고 보고 전에 지웠다. 프로젝트 파일과 감사자 메모리는 이번에 쓰지 않았다.
