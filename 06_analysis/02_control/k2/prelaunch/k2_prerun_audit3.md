<!-- verif-protocol-auditor 리포트 원문(2026-11-10, 실행 전 세 번째 감사). 대상: K-2 _TCL V-2~V-7, master 38a804f, k2-run 6a44ff8. 메인 세션이 편집 없이 저장. -->

**차단 1건, 실행 전 수정 3건, 확인 필요 3건** (기록 7건)

## 감사 요약
- **대상과 시점**: K-2 `_TCL` V-2~V-7, 실행 전 세 번째 감사입니다. master는 `38a804f`이고, 실행 checkout k2-run은 `6a44ff8`(locked, 추적 변경 0, `runs` 폴더 없음, 결과 0건)입니다.
- **기준 문서**: 7판 모두 raw 해시가 `.sha256` 첫 토큰과 같습니다. 모두 LF이고 BOM이 없으며 `-text`입니다.
  - 원판 a3658197, rev1 5ba081c6, rev2 b3f1b41f, rev3 8bcdb0ed, rev4 82160ff5, rev5 73b87758, **rev6 21268203**, 명세 502b0bb7
  - criteria.md: blob 86aa6242 @6a44ff8
- **도구 blob**: HEAD와 작업 사본이 모두 아래 값입니다.
  - 경로 1 `c285b8c9`
  - 경로 2 1.5 `e1e16a9c`
  - 평탄화기 `b3851190`
- **판정**: 차단 1 / 실행 전 수정 3 / 확인 필요 3 / 기록 7.
  - 실행 자체는 규칙대로 준비돼 있습니다. 명령, 배치 파일 18개, 입력, 봉인, 고정값 60개가 모두 실측과 같습니다.
  - **다만 차단 1(경로 2 작성자가 경로 1 코드를 직접 읽음)은 시작 전에 사용자 결정이 필요합니다.** 경로 2는 결과가 나온 뒤에는 새로 쓸 수 없습니다(원판 8절). 그래서 "경로 2를 무효로 본다"는 선택지는 시작하는 순간 사라집니다.

## 재감사 항목 처리 상태

| # | 항목 | 상태 | 근거 |
|---|---|---|---|
| 수정 1 | 두 경로 V-5 판정 종류·적용 팔 5건 | **닫힘**(다섯 건 모두) | 아래 대조표 1~5행. 새로 남은 작은 차이는 기록 a·b와 실행 전 수정 2 |
| 수정 2 | 참고용 옛 평탄화 단계 | **닫힘** | rev6 4절이 확인 목록을 62개에서 60개로 줄이고 이어 돌리기 규칙을 정했습니다(`rev6.md:42-51`). `k2_commands.json`에서 identity_sidecar가 있는 단계는 63개입니다. 여기서 V-7 자리 표시 1개와 `v5_flatten_off`·`_tcl` 2개를 빼면 60개입니다. 다만 같은 절에 새로 넣은 `flat_main` 재생성 단계는 기대값이 정해지지 않았습니다 → 실행 전 수정 1 |
| 수정 3 | G-S 근거 | **대부분 닫힘** | `gs_evidence/gs.out` d397b00f, `gs_chrono.out` 2fc2bfee(실행 전 기록 값과 같음). `test_k2_hashes` 4/4 통과, skip 0. dynamics-dev의 fail 1건(`test_open_fraction`)은 `ModuleNotFoundError: pychrono`(`gs.out:114-165`)이고, Chrono-dev에서는 66건 모두 통과했습니다. **T-K2-7 "기존 단위 시험 전부 통과"의 근거는 없습니다** → 실행 전 수정 3 |
| 확인 필요 1 | 발견 1 처리 | **닫힘** | 사용자 결정 (a). rev6 1절, 경로 1·2 새 blob |
| 확인 필요 2 | 발견 2 처리 | **닫힘** | (b)를 골랐고 rev6 4절에 반영됐습니다 |
| 확인 필요 3 | 경로 2 작성자가 경로 1 코드를 읽었는지 | **열림, 그리고 사실로 확인됨** → 차단 1 | transcript 근거는 아래 |

## 발견 사항 (심각도순)

**[차단][I·T] 1. 경로 2 작성자(control-expert)가 경로 1 코드를 직접 읽었습니다. 그런데 봉인된 rev6 5절은 "메인 세션이 정의 요약(코드가 아님)을 전달"이라고만 적었습니다.**
- **근거**: transcript `C:\Users\jinbeom\.claude\projects\C--workspace-outrigger-control\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\subagents\agent-af7124b8517fd4c3a.jsonl`의 첫 지시문은 "너(control-expert)"이고, 이 agent가 경로 2 1.1~1.5와 rev1~rev6을 썼습니다. 그 안의 tool_use 기록은 다음과 같습니다.
  - 2026-11-10 17:37:23~17:37:36 KST
    - `k2_judge.py`를 grep(add_argument, manifest)
    - `Read k2_judge.py offset 1110 limit 100`
    - `sed -n 560,600p k2_judge.py`
    - `Read offset 884 limit 20`
  - 17:50:06 `grep -n "series" k2_judge.py`, 곧바로 17:50:13 `k2_recount.py` Edit. 17:51:09에는 `grep -n "dhat" k2_judge.py`
  - 19:37:58~19:38:02 KST: `git show 5f22957:04_scripts/03_control/k2/k2_judge.py`에 대해
    - grep(kind, V5_KINDS, pass_to_fail)
    - `sed -n 1270,1300p`
    - `V5_RELATIVE_GATES -A6`
    - 30초 뒤(19:38:32)에 rev5를 Write했습니다.
  - 이 agent는 재감사 원문(경로 1 코드 줄 번호와 동작을 인용함)도 여러 번 읽었습니다.
- **규칙**: 원판 8절은 "경로 1의 출력과 코드는 읽지 않는다"(`k2_touch_creep_rules.md:352`)입니다. rev6 5절은 "메인 세션은 경로 1의 **정의 요약**(코드가 아님)을 경로 2 작성자에게 전달해 …"(`rev6.md:55`)입니다. 사용자 결정은 "경로 독립성은 사실대로 공개"입니다.
- **결과 순서**: 모두 결과 전이므로 결과에 맞춘 것은 아닙니다(`runs` 없음).
- **차단으로 둔 이유**
  - 원판 8절 위반을 어떻게 다룰지는 규칙에 없습니다.
  - 엄격하게 읽으면 "8절을 지키지 않은 경로 2는 G-F의 경로 2가 아니다", 곧 G-F가 판정 불가입니다.
  - 그 경우 대안은 새 독립 경로 2뿐인데, 8절상 결과가 나오기 전에만 쓸 수 있습니다. 시작한 뒤에 이 해석을 고르면 등급이 판정 불가로 굳습니다.
  - 봉인된 공개 문구가 사실보다 약하게 적혀 있어서, 이대로 판정서에 옮기면 독립성 근거가 틀린 채로 남습니다.
- **풀어 주는 최소 조치**(시작 전에)
  - (가) 사용자 결정(AskUserQuestion): "직접 읽음을 공개하고 경로 2를 그대로 쓴다"와 "다른 작성자가 독립 경로 2를 새로 쓴다" 중 하나를 고릅니다.
  - (나) 가를 고르면 실행 전 기록(`prelaunch/README.md` 7.2, `k2_prelaunch_v*.json` `independence_disclosure`)을 위 시각과 행위로 고칩니다. rev6 5절이 봉인돼 있으므로, 고친 공개 문구는 결과 전 rev7로 봉인하는 것을 권합니다.
  - (다) 판정서에 "공통 실수가 두 경로에 함께 들어갔을 가능성"을 적습니다. 특히 V-5 결과 종류, SH 결측, kind·relative gate처럼 경로 2가 경로 1 코드를 보고 맞춘 부분입니다.
- 담당: 메인 세션(사용자 질문, 기록 수정), control-expert 또는 다른 에이전트(rev7·새 경로 2를 고를 때).

**[실행 전 수정][I·R] 1. rev6 4절이 확인 목록에 넣은 `flat_main` 재생성 단계의 명령과 기대값이 정해지지 않았습니다.**
- 근거
  - rev6 4: "판정 전 `flat_main` 재생성 단계는 확인 목록에 넣는다. 래퍼로 돌려 sidecar를 남긴다"(`rev6.md:51`).
  - 확인 목록의 봉인 조건은 rev2 6.1입니다. 시작·끝 HEAD = `6a44ff8`, clean, `MKL_THREADING_LAYER=TBB`와 `*_NUM_THREADS=1`, affinity = 배치표 값입니다. "하나라도 어기면 G-F 판정 불가"입니다(`rev2.md:86-91`).
  - README 9.1의 명령 블록(`README.md:204-210`)은 래퍼 없이 `conda run … k2_v5_flatten.py`만 적혀 있습니다. 평탄화기 b3851190은 main checkout에만 있어서 HEAD가 `6a44ff8`일 수 없습니다.
  - 래퍼는 `--git-dir`를 주지 않으면 cwd의 git을 기록합니다(`run_with_identity.py:131-137`).
  - 배치표에는 이 단계의 마스크가 없고, sidecar 이름도 정해지지 않았습니다. 옛 `flatten.launch.json`을 덮어쓸 수 있습니다.
- 실패 시나리오: rev2 6.1을 글자 그대로 적용하면 G-F가 구조상 판정 불가입니다(HEAD ≠ 6a44ff8, NUM_THREADS 미설정). 반대로 결과를 본 뒤에 기대값을 정하면 사후 해석이 됩니다.
- 권장 조치(메인 세션, 시작 전): 실행 전 기록(README 9.1과 prelaunch)에 다음을 적어 커밋합니다.
  - 래퍼를 포함한 정확한 명령: sidecar 경로(예 `runs/v5/<arm>/flat_main.launch.json`), `--git-dir`, env, 마스크
  - 이 단계의 기대값: HEAD = 판정 커밋(평탄화기 blob b3851190), 추적 clean, env, 마스크
  - 이 단계에는 rev2 6.1의 `6a44ff8` 조건 대신 위 값을 쓴다는 문장. 규칙 해석이 걸리므로 rev7에 함께 넣으면 가장 깔끔합니다.

**[실행 전 수정][R] 2. SH-6 결측의 단위가 두 경로에서 다릅니다. V-2·V-3·V-4와 V-6 모두 해당합니다.**
- 근거
  - rev6 2: "SH-6: K-2 행의 J1이 없으면 결측이다. J2는 H4 구간이 있는 행에서만 본다"(`rev6.md:34`).
  - 경로 1은 H4 행의 J2가 없을 때도 `missing["SH-6"]`를 셉니다(`k2_judge.py:540-544`, `items = ("J1_N","J2_N") if row.get("has_h4")`). 이 값은 FLAG로 나갑니다(`_sh_missing_flags`). V-6도 같은 함수를 씁니다(`k2_judge.py:1574`).
  - 경로 2는 J1이 없을 때만 결측으로 셉니다. 하네스는 `k2_recount.py:708-713`, V-6은 `:1597-1603`입니다.
- 실패 시나리오: H4가 돈 K-2 행에서 J2가 None이면 경로 1은 SH-6 FLAG를 내고 경로 2는 내지 않습니다. 원판 8절은 "SH FLAG 여부 같음"을 요구하므로 G-F는 판정 불가입니다. 그 행은 J2 결측(E-9)으로 이미 row fail이므로, 원래 등급은 **미달**이어야 하는데 **판정 불가**로 바뀝니다.
- 영향 범위: 거짓 통과는 없고, 이미 실패하는 행에서만 생깁니다. 다만 두 비통과 등급(미달 ↔ 판정 불가) 사이에서 등급이 바뀝니다.
- 권장 조치(시작 전): 경로 1 `_sh_row_flags`에서 J2 결측은 SH-6 결측으로 세지 않습니다(python-expert). rev6 문구 쪽이 경로 2와 맞습니다. 그 뒤 실행 전 기록에 새 blob을 고정합니다. 받아들이기로 한다면 판정서에 미리 공개합니다.

**[실행 전 수정][I] 3. G-S의 T-K2-7 "기존 단위 시험 전부 통과" 근거가 없습니다.**
- 근거
  - 원판 7절 G-S는 "구현 시험 9.2 통과"를 요구하고, 9.2에는 T-K2-7이 들어 있습니다(`k2_touch_creep_rules.md:336,379`).
  - `gs_evidence`의 두 명령은 K-2 시험 파일 6개와 3개만 돌렸습니다(prelaunch `gs_evidence.runs[].command`).
  - transcript 검색에서도 전체 단위 시험을 돌린 기록을 찾지 못했습니다.
  - 147·152건은 판정 도구 시험입니다. 152건은 기록에도 없습니다. 기록에는 "147, 6d11d13"만 있습니다.
- 영향: 시작 관문 조건이고 등급에는 영향이 없습니다. 실행 경로(03_src·02_params·04_scripts 실행 코드)는 6a44ff8 뒤로 바뀌지 않았습니다.
- 권장 조치(메인 세션): 둘 중 하나입니다.
  - k2-run에서 `05_tests/unit` 전체를 E코어로 돌리고 결과를 `gs_evidence`에 넣습니다(env별 skip 원인 포함).
  - 이미 있는 실행 근거가 있으면 그것을 기록합니다.

**[기록]**
- **(a) 끔 팔·기록용 부분의 오류 행 범위가 다릅니다.**
  - 경로 1의 `error_rows`는 flattener 출처 파일 전체에서 셉니다. 여기에는 토양 `head`, r79 L3L4, 원 실행 파일이 들어 있고, 두 팔 모두에서 판정 불가로 칩니다(`k2_v5_flatten.py:182-195,498-503`, `k2_judge.py:1134-1136`).
  - 경로 2는 K-2 팔의 판정 대상만 봅니다(`_v5_d8` 1113, `_v5_ps7`, `_v5_g8`, `_v5_regression`).
  - rev6 1 표의 "두 팔 모두"는 rc에만 붙어 있습니다.
  - 생기면 경로 1이 판정 불가이므로 등급은 같습니다. 다시 돌리면 풀립니다.
- **(b) 잡음 L2의 팔 간 키 대조가 경로 2에 없습니다.** 경로 1은 짝 없는 키를 판정 불가로 칩니다(kind `noise_cp`). 경로 2 `_v5_noise`는 건수만 봅니다(`k2_recount.py:1150-1201`). 생기면 경로 1이 판정 불가이므로 등급은 같습니다.
- **(c) V-3 AUG_crc2의 처리가 다릅니다.**
  - 경로 1은 crc2의 E-1 건수 문제(`more`)까지 버립니다(`k2_judge.py:942-946`). 원판 E-1 3,822에는 crc2가 들어 있습니다.
  - 경로 2는 crc2 키 목록 sha(E-5, rev6 3에 따르면 기록)를 전역 판정 불가로 올립니다(`k2_recount.py:921-924`).
  - 키 파일이 공통이라 실제로 일어날 가능성은 낮습니다.
- **(d) SH-1 입력원이 다릅니다.** 경로 1 하네스는 드라이버 기록값 `k2.SH1_lift_chunks_after_latch`(`k2_judge.py:481`)를, 경로 2는 시계열 재계산값(`k2_recount.py:272-275`)을 씁니다. rev6 2는 "시계열 재계산 값"이라고 적었습니다. 경로 2 V-6 `sh1.values()`에 None이 섞이면 TypeError가 납니다(재계산값은 dict만이라 실제로는 생기지 않습니다).
- **(e) G-F 대조 단위가 정해지지 않았습니다.** 경로 2는 공통 항목을 `common` 한 덩어리로, 경로 1은 묶음마다 냅니다. 원판 8절의 "V-5 묶음별 실패 수" 대조표 형식(어느 필드를 맞대는지)을 결과 전에 README에 적어 두기를 권합니다. G-D가 판정 불가일 때만 갈리므로 등급 영향은 없습니다.
- **(f) 이어 돌리기 규칙(rev6 4)은 argv만 말합니다.** 확인 목록은 env(`*_NUM_THREADS=1`)와 마스크도 봅니다. `k2_commands_filled.json`의 env와 mask를 그대로 쓰십시오.
- **(g) 그 밖**
  - rev6 `.sha256` 머리의 "sealed 20:11"과 커밋 20:10:49가 11초 차이입니다(분 반올림으로 보이며 영향 없음).
  - `gate_scan.py --no-git`은 여전히 종료 2입니다.
  - 판정 도구 시험 "152건 @38a804f"는 실행 전 기록에 없습니다.

## 규칙↔도구 대조표 (재감사 불일치 행 재대조)

| 항목 | rev6 | 경로 1 (c285b8c9) | 경로 2 (e1e16a9c) | 판단 |
|---|---|---|---|---|
| K-2 증거 위반 | 판정 불가(`rev6.md:15`) | 판정 불가(`_not_judgeable_reasons`, 1392-1404) | `NJ_ITEMS`의 k2_evidence·events:*·combo·k2·tcl·tag·g8_*(990-999) → 판정 불가 | **일치** |
| 짝 없는 키 | 판정 불가(`:16`) | `unpaired` → 판정 불가(kind ≠ absolute) | `unmatched` → 판정 불가(격자·토양·D8·회귀·PS-7·G8) | **일치**(잡음만 기록 b) |
| 격자 768 두 팔 | 판정 불가(`:17`) | `rows` 두 팔(`V5_EXPECTED_ROWS`, `V5_NOT_JUDGEABLE_ITEMS`) | `count` n_tcl·n_off(1068-1071) | **일치** |
| 끔 팔 sidecar rc | 두 팔, 36 + 4(`:14`) | `absolute["off"]`의 rc → 판정 불가 | 두 팔 20개씩, flatten 제외 | **일치**(단계 집합 20/팔 같음) |
| 회귀 verdict 결측 | 실패(`:20`) | `regression_verdict` 결측 → 실패(1156-1159, flatten `verdict_missing`) | `miss("verdict")` → 실패(1260-1261) | **일치** |
| 결측의 종류 | 항목 종류를 따름(`:19`) | `_Items` 결측 → 그 항목 이름의 종류 | `miss` → `bad` → `_is_nj_item` | 일치 |
| G-D 우선순위 | 판정 불가 > 실패 | `problems` 먼저(1459-1460) | `nj` 먼저(1461) | 일치 |
| 하네스 SH 결측 | rev6 2 | 짝 단위 SH-2, SH-5 결측 없음 | 짝 단위, 결측 → FLAG | 일치. **SH-6의 J2는 불일치(실행 전 수정 2)** |
| AUG_crc2 | E-5·I-9 기록만 | arm_problems 기록. E-1도 버림 | E-5 기록. 키 sha는 전역 | 기록 c |
| 봉인 rev6 | – | `RULES_REV6_SHA256`(62행) | `REV6_SHA256`(101행), `--rules-dir`일 때 | 일치(seal_check const 2/2) |

## T·S 확인
- **커밋 순서**(git `%cI`): 결과는 0건입니다(`k2-run\…\k2\runs` 없음, k2-run untracked 0).
  - rev6 봉인 d5e878a 20:10:49
  - 경로 2 1.5 12e116a 20:15:14
  - 경로 1 728ace5 20:16:10
  - 기록 7b7d67f·fa69233
  - 병합 38a804f 20:20:48
- **판정 항목·문턱**: 바뀐 것이 없습니다. rev6에는 새 수치가 없고, 건수는 E-1·rev2 2의 값 그대로입니다. SH-2 중앙값을 "두 값이 모두 있는 짝"으로 정한 것은 원판 5.2의 "짝짓는다"와 E-11 범위 안의 결측 처리입니다.
- **공통 항목 "실패 → 판정 불가"는 criteria.md 원문으로 돌아간 것입니다.**
  - criteria.md 9행은 "오류 행 0, `main_tree_modules` 0, 기록된 `c2_sha256`이 체크아웃과 같고 조합 설정이 맞을 것. **하나라도 어기면 그 묶음은 판정하지 않고 다시 돌린다**"입니다. 원판 3.4는 그 파일을 "글자 그대로" 쓰라고 합니다(`k2_touch_creep_rules.md:162`). 그러므로 rev2의 "실패"가 원문에서 벗어난 것이었고, rev6이 되돌렸습니다. 건수가 다를 때의 판정 불가도 원판 E-1 그대로입니다.
  - **원문으로 돌아간 것이 아닌 부분이 하나 있습니다. 짝 없는 키를 판정 불가로 둔 것입니다.** criteria.md에는 이 항목이 없고, rev2에서는 "끔 팔 대비" 칸, 곧 G-D 실패였습니다. 이것은 결과 종류를 새로 정한 것입니다. 그래도 결과 전이고, 판정 불가는 미달보다 높은 순위라 통과로 가는 길은 생기지 않습니다. 허용 범위입니다.
  - 효과 차이는 하나입니다. K-2 코드 때문에 생긴 오류 행도 "미달"이 아니라 "판정 불가 → 다시 돌림"이 됩니다. 결정적 코드라면 다시 돌려도 같으므로 거짓 통과는 없습니다. 판정서에는 원인(실행 결함인지 K-2 결함인지)을 구분해 적으십시오.

## 실행 전 기록 고정값 ↔ 실측
즉석 대조 60항목이 모두 일치했고 불일치는 0입니다.
- inputs 5
- criteria 3값
- k2-run c2.py
- L1R 시작 상태 4, L2b blob 2
- fix_blobs 5 @6a44ff8
- 배치 파일 18
- ra_off·ra_on
- 회귀 키 파일
- 점 파일 2
- gs 로그 2
- 경로 1·2·평탄화기 blob(HEAD와 작업 사본)
- 규칙 7판과 명세

`k2_prelaunch_v2~v7`의 공통 칸은 `pool`(묶음별 값)만 다르고 나머지는 모두 같습니다.

## 확인 필요
1. **차단 1**: 경로 2 작성자가 경로 1 코드를 직접 읽은 것을 (가) 공개하고 받아들일지, (나) 독립 경로 2를 새로 쓸지 정해 주십시오. (나)는 시작 전에만 가능합니다.
2. **실행 전 수정 2**: SH-6 J2 결측 차이를 경로 1에서 고칠지, 이대로 두고 판정서에 공개할지 정해 주십시오(미달 ↔ 판정 불가에만 영향).
3. **실행 전 수정 1**: `flat_main` sidecar의 기대값(HEAD, 마스크, env)을 무엇으로 할지, 그리고 rev7에 넣을지 기록에만 둘지 정해 주십시오.

## 위임 필요
- **python-expert**(확인 필요 2에서 고치기로 하면): `k2_judge.py:540-544` `_sh_row_flags`에서 J2 결측을 SH-6 결측으로 세지 않게 합니다(J2가 숫자일 때만 근접 판정). 선택으로 crc2의 E-1을 `problems`에 남깁니다(942-946). 그 뒤 새 blob을 실행 전 기록에 넣습니다.
- **control-expert 또는 다른 에이전트**(확인 필요 1·3): rev7에 독립성 공개 정정과 `flat_main` 단계 기대값을 넣고 봉인합니다(결과 전). 새 경로 2를 고르면 원판 8절대로 경로 1 코드를 보지 않는 작성자가 씁니다.
- **python-expert (tools/verif)**: `gate_scan.py --no-git`이 아직 종료 2입니다.

## 메인 세션 권고
- 시작 전: 확인 필요 1을 사용자에게 묻습니다. 실행 전 수정 1·3의 기록을 커밋합니다. 경로 1을 고치면 새 blob을 고정합니다.
- 판정이 끝날 때까지 `04_scripts/03_control/k2/` 판정 도구를 바꾸는 병합은 하지 않습니다. 열려 있는 `k2-v7k1-dhat`, `k2-chrono-runner` 브랜치는 병합 전에 `git diff --stat`으로 확인하십시오.
- 순서는 README 8절대로입니다. 셸에는 `OUTRIGGER_*`·`ACC_*`가 없어야 합니다.
- P_post를 이어 돌릴 때는 argv와 함께 env와 마스크도 그대로 씁니다.

## 검사하지 못한 것
- 전체 단위 시험(T-K2-7)과 판정 도구 selftest(1.5·c285b8c9)는 재실행하지 않았습니다.
- 경로 1 작성자(python-expert) transcript에서 경로 2 코드를 어디까지 참조했는지 전수 확인하지 않았습니다(rev6 5가 이미 공개).
- 메인 세션이 control-expert에게 넘긴 "정의 요약" 메시지 원문은 대조하지 않았습니다.
- V-7 Job 메모리. C축(결과 0건).

## 실행한 검증
- 인터프리터: python-dev `-I -B -X utf8`, `MKL_THREADING_LAYER=TBB`. 대상 프로젝트 import는 없습니다.
- verif 도구
  - `seal_check.py --repo . "06_analysis/02_control/k2/k2_touch_creep_rules*.md" --code 04_scripts/03_control/k2 --const k2_judge.py:RULES_REV6_SHA256 --const k2_recount.py:REV6_SHA256`: 7판 raw 일치, 고정 31개, const 2/2, 발견 0
  - `gate_scan.py`(judge, recount, flatten): warning 4. 재감사 때와 같고 모두 오탐입니다. `--no-git`은 종료 2입니다.
- 즉석 스크립트: scratchpad `verif\pin_check.py`로 실행 전 기록 60항목을 파일·git과 대조했습니다. 보고 전에 `verif\` 폴더째 지웠습니다.
- 조회
  - git: log, diff, status, worktree list, rev-parse, hash-object, ls-files --eol, check-attr
  - PowerShell: Get-FileHash, ConvertFrom-Json
  - transcript jsonl 조회: `agent-af7124b8517fd4c3a.jsonl` tool_use 추출
- 메모리 갱신: `audit_pitfalls.md`에 3개 항목(자기 작성 독립성 공개와 transcript 대조, 확인 목록에 넣은 단계의 기대값, 조건부 부값 결측)을 더했고 `MEMORY.md` 색인을 갱신했습니다.
- 최종 판정 직전에 다시 확인했습니다: master 38a804f, k2-run 6a44ff8, 추적 변경 0, `runs` 없음, 세 도구 blob 그대로, `rev6.md:55` 문구 그대로입니다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha k2_dyn_spec.md 502b0bb7…, k2_prelaunch_notes.md ca3bf841…, k2_touch_creep_rules_rev1.md 5ba081c6…, k2_touch_creep_rules_rev2.md b3f1b41f…, k2_touch_creep_rules_rev3.md 8bcdb0ed…, k2_touch_creep_rules_rev4.md 82160ff5…, k2_touch_creep_rules_rev5.md 73b87758…, k2_touch_creep_rules_rev6.md 21268203…, k2_touch_creep_rules.md a3658197…, k2_touch_creep_rules_rev1.sha256 fdf6d8ca…, k2_touch_creep_rules_rev2.sha256 2fd7dc24…, k2_touch_creep_rules_rev3.sha256 de03d989…, k2_touch_creep_rules_rev4.sha256 735815f4…, k2_touch_creep_rules_rev5.sha256 f3e5eb8e…, k2_touch_creep_rules_rev6.sha256 e31f6204…, k2_touch_creep_rules.sha256 6a7d3b25…, k2_points_5p5_3p5.json a15cbe95…, k2_commands.json ce6e04a2…, k2_expect.json ecef70d2…, k2_fields.json 0c5aafc4…, k2_manifest.json 807e3690…, k2_prelaunch_v2.json 3fccad4a…, k2_prelaunch_v3.json 0433ab9d…, k2_prelaunch_v4.json 6d0f68e6…, k2_prelaunch_v5.json 41408ae4…, k2_prelaunch_v6.json 41a81e11…, k2_prelaunch_v7.json f95b8ae9…, k2_prerun_audit.md fe971e24…, k2_prerun_reaudit.md bb2ba773…, k2_v3_keys.txt 506b93a4…, k2_v5_regression_keys.json f2970048…, make_prelaunch.py 7152ed04…, README.md d358481a…, regression_keys.py 31ee5cc9…, gs_chrono.out 2fc2bfee…, gs.out d397b00f…, aff.json 68bb2fb1…, build_runners.py 7182fb37…, k2_commands_filled.json 402a1ef3…, k2_placement_20261110.json f349ce4e…, k2_sched_lanes.json 1b5fc744…, p_main_done_markers.txt ac277f80…, state.json 257a8ab2…, steps_E_pre.json b725bdfe…, steps_E_V6_off.json 1ec165c4…, steps_E_V6_tcl.json d04502cf…, steps_E_V7.json 0713920f…, steps_P_main.json 033496df…, steps_P_post.json 5dd80d49…, k2run_E_pre.ps1 5e8a85db…, k2run_E_V6_off.ps1 8c25c06e…, k2run_E_V6_tcl.ps1 cff4c587…, k2run_E_V7.ps1 e5c94ae7…, k2run_P_main.ps1 1c4c4c58…, k2run_P_post.ps1 434c109b…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
