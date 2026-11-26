# 436.8 rev26 4′ 점검 (판정 전) — verif-protocol-auditor, 2026-11-26

## 감사 요약
- 본 결과: 436.8 저장 결과와 원 출력(`judge_932f1fb\` 아래 `_fixed` 밖)은 열지 않았다. 본 값은 세 가지뿐이다: 합성 고정물 출력의 값, `t26_identity.json`의 sha·구조, 규칙·보고 문서.
- 대상: T26 `335004a7ad9f5f988e7543dd98d45bf2b96e4294`, worktree `C:\workspace\outrigger_control\.claude\worktrees\rev26-t26`(locked)
- 시점: 판정 전(rev26 4′)
- 기준 문서
  - rev26 `f6591836`(봉인 c77b1dcf, `.sha256` `e74aeca9`)
  - 정오 1 `5e3bf3e6`(`.sha256` `27f98bae`, 미추적)
  - 부록 A 스크립트 `excl_fields_r5.py` `bee9eee7`
  - 부록 B `9e1831f5`는 sha만 쟀다.
- 판정: **차단 1 / 실행 전 수정 4 / 기록 13. 5단계 진행 불가.**
  - 정체성 필드 덮음 점검(rev26:156~162)에서 부록 A 규칙으로 지워지지 않는 run 의존 필드가 나왔다.
  - rev26:162에 따라 멈추고 사용자 결정을 받아야 한다.
  - 변형 3과 원 출력 쪽 도구 sha 잎 점검은 감사자 권한 밖이라 하지 못했다.

## 발견 사항 (심각도순)

### [차단][I·R] B-1 `harness_path2/p2v5c_merge.json :: parts[].sha256`은 실행마다 달라지고 부록 A 규칙에 걸리지 않는다. (d)가 반드시 불일치한다
- **근거(코드)**
  - `path2_v5c/p2v5c_stage1.py:716`(T26)과 932f1fb:712는 같은 줄이다: `rec = {"path": p, "sha256": cm.sha256_file(p), "tool": t, ...}`
  - `p`는 같은 실행이 쓴 `p2v5c_noise/stage1/grid.json`이다(실행본 `run_judgement_path2_rev26.ps1:392~394`).
  - 이 파트 파일에는 매번 달라지는 값이 들어 있다: `created`, argv 출력 경로, `tool_sha256`·`common_sha256`(T26이 p2v5c_*를 바꿈), `head_check.head`(T26), `seals`의 rev26 칸. 그래서 파일 raw sha는 원 출력과 반드시 다르다.
- **근거(규칙)**
  - `excl_fields_r5.py:193~217` `classify`에서 키 `sha256`은 SEAL·TOOL·F·TIME 이름이 아니다.
  - `imports` 바로 아래의 `*_sha256`도 아니다.
  - 값은 커밋 토큰·출력 토큰·시각이 없는 64자리 16진이다.
  - 그래서 비교 대상이다. 부록 A 규칙 표의 "(비교) 입력 경로·sha 블록"(rev26:245)과도 맞는다.
- **근거(실행)**: 합성 고정물로 실행본 꼴 두 번 실행했다(A: 토큰 `judge_rev26_335004a`, B: `judge_rev26_9999999`, 다른 시각).
  - 각 쪽에 `excl_fields_r5` 규칙(Rules·classify import)으로 자기 I·S·F를 지우고 NT·NM을 정규화했다.
  - 48/48 파일 가운데 불일치는 이 파일의 `parts/[0..2]/sha256` 3잎뿐이었다.
  - 파트 파일 자체는 정규화 뒤 A=B였다.
- **판정 기준(rev26:160)**: "세 출력 사이에서 달라지는 필드가 모두 … 사라지거나 (g)·(h) 대상이어야 한다." 이 기준에 어긋난다.
- **실패 시나리오**
  - 5단계를 그대로 하면 데이터와 무관하게 (d)가 불일치한다.
  - rev26 낱말은 "판정 불가(rev26 기대 효과 불일치)"가 되고 1회 실행을 소모한다(5절 실패 처리 3행).
- **권장 조치**: rev26:162대로 멈추고 사용자 결정을 받는다. 선택지는 아래와 같다.
  - (i) 정오 2와 부록 A r6으로 `p2v5c_merge.json :: parts[].sha256`을 I(같은 실행의 출력 digest)로 정한다.
    - 파트 세 파일은 (d)에서 각자 비교되므로 잃는 비교는 없다.
    - r6 원 출력 적용 목록은 원 출력 구조를 읽어야 하므로 공개가 필요하다.
    - `rev26_fixed/**`에는 파일을 더할 수 없다(정오 1 E1-4, rev26:67 "master와 바이트 같음"). 새 폴더에 둔다.
  - (ii) 이 3잎을 (d)의 알려진 불일치로 사전 선언한다. 이것도 규칙 변경이다.
  - 담당: 사용자 결정 → control-expert(정오·부록) → 봉인 → 4′ 정체성 점검 다시 실행(이 감사자)

### [실행 전 수정][I] W-1 정체성 필드 덮음 점검의 변형 3을 하지 않았고, 합성 범위가 부분이다
- **변형 3 미실시**
  - rev26:159의 "다른 worktree + 빈 커밋"을 하지 않았다.
  - 감사자는 worktree와 커밋을 만들 수 없다(읽기 전용).
- **합성 범위**
  - 경로 1은 실행본이 쓰는 json 약 55개 가운데 35개를 만들었다.
  - 만들지 못한 것: `family_table`, `k1_class`, `r4_lists`, `anchor_map`, `u3_judge_k1`, `u3_judge`, `u9_judge`, `h8_noise_judge`, `h6_judge`, `h6_r79_judge`, `x16_records`, `import_check`, `overlap_steps`, `log_errors_run_harness`, `keyset_h7`, `keyset_grid_*` 4개, `stage1_judge`
  - 경로 2는 14개 가운데 13개를 만들었다(`d1.json` 없음, 합성 h1 꼴 KeyError).
  - 만든 파일도 상당수는 멈춤 출력(rc 2)이라, 멈춤 뒤의 필드는 지나가지 않았다.
- **못 만든 출력의 정적 검토([추정])**
  - 같은 실행 출력의 sha를 적는 곳을 찾아 읽었다.
  - `h6_judge_4368.py:288`(`inputs.judge.sha256` ← `h6_r79_judge.json`): r79 판정 출력에 경로·시각이 없다(`r79_sensor_judge.py:540~545, 817~819`). 같을 것으로 본다.
  - `resume4368_judge.py:1162, 3607`(family_table sha): 표에 루트·시각이 없다(`resume_k1_family.py:289~296, 337~348`). 같을 것으로 본다.
  - `resume4368_judge.py:4518`(h12 replay sha), `p2v5c_noise.py:139`(r79 출력 sha): 시각·경로 키를 찾지 못했다.
  - 이 넷은 B-1과 달리 같은 sha가 날 것으로 보지만, 실행으로 확인하지 못했다.
- **권장 조치**
  - 메인이 T26에서 두 번째 worktree를 만들고 `git commit --allow-empty`를 한 뒤, 이 감사자를 SendMessage로 이어 불러 변형 3을 돌린다.
  - 그때 h11처럼 합성 입력을 보강해 빠진 단계도 돌린다.
  - B-1 해소 뒤 4′ 정체성 점검을 다시 할 때 함께 한다.

### [실행 전 수정][C] W-2 도구 sha 잎 점검(rev26:155): 원 출력 쪽을 하지 않았다
- **미실시 이유**: 이 점검은 원 출력(`judge_932f1fb/harness_path*`)과 부록 B가 필요하다. 지시문상 열 수 없다.
- **한 범위(새 출력 쪽 대응 점검)**
  - 합성 출력에서 비교 대상 잎(I·S·F 제외 뒤)의 64자리 16진을 대조했다.
  - 대조 집합은 T26·932f1fb의 바뀐 파일 37개와 허용 목록 29개의 raw·LF·CRLF sha 134개다.
  - 같은 값은 경로 1 `head_check.json :: blobs[].M4·R4`(14파일 × 2)뿐이었다. 이것은 (g) 대상이고 (d) 범위 밖이다(`excl_fields_r5.py:80`).
- **권장 조치**
  - 메인이 값 비출력 개수 점검을 승인한다.
  - 방법: 원 출력에 부록 B를 적용해 I·S·F를 지우고, 남은 잎의 64자리 16진과 `git show 932f1fb:<허용 목록 29>`의 raw·LF·CRLF sha가 같은 건수와 경로만 낸다.
  - 실행 주체: 이 감사자 또는 다른 감사자
  - 5단계 전에 해야 한다.

### [실행 전 수정][I] W-3 메인 checkout 추적 트리가 더럽고, 기록 파일이 커밋되지 않았다
- **추적 트리**
  - `git status --porcelain --untracked-files=no` 결과: ` M .claude/agents/paper-reviewer.md`, ` M .gitattributes`, ` M 00_docs/decision_log.md`
  - 경로 1 `Assert-CleanTree 'start'`(`run_judgement_path1_rev26.ps1:73~79`)가 시작에서 throw한다.
- **E1-5 `.gitattributes`**
  - 세 줄은 작업 트리에만 있고 HEAD `2715230e`에는 없다.
  - `rev26_run/**`·정오 파일은 미추적이다. `check-attr`는 지금 작업 트리 기준으로 `unset`이다.
- **동시 작업**: 같은 세션에 다른 구현 에이전트(ed8 등)가 있다. 5단계 중에 메인 추적 트리를 바꾸면 끝 관문(`:197`)이 설정 결함을 낸다.
- **권장 조치**: 아래 "5단계 전 메인 할 일" 순서를 따른다.

### [실행 전 수정][I] W-4 `t26_identity.json`의 rev26:109 필수 칸이 비어 있다
- `input_basis_crosscheck`가 null이다. rev26:109 "2절 '입력 기준' 표와 두 경로 구현 기록의 대조 결과"에 해당한다.
- 이 감사의 대조 결과(아래 기록 R-5 표)로 채우고 sha를 새로 고정한다.
- `wt_status_before/after`는 5단계 때 채울 칸이다(설계대로).

### [기록] R-1 RD-1 4 대체 조건 1~3: 모두 충족(직접 재계산)
- **조건 1**
  - `git diff --name-status 932f1fb..T26`는 37개(A·M)다.
  - 허용 집합 밖은 0이다: 경로 1 허용 목록 14(M4 실행본 30~43행), `path2/`·`path2_v5c/`, rev26 `.md`·`.sha256`, `rev26_fixed/**` 14, `.gitattributes`.
  - 규칙 파일 16개는 메인 HEAD와 바이트가 같다. `rev26_fixed` 파일 집합도 같다(14/14).
  - `.gitattributes` diff는 `+` 6줄이고 rev26 7절 6줄과 순서까지 같다(`-` 0줄).
- **조건 2**
  - `git diff --name-only b9f5707..T26 -- 03_src 02_params`는 0건이다(rc 0).
  - T26 추적 파일 수는 03_src 141, 02_params 18이다(0개 폴더가 아니다).
- **조건 3**: 허용 목록 29개 가운데 바뀌지 않은 10개는 LF sha가 같다. 바뀐 19개는 blob이 실제로 다르다.

### [기록] R-2 실행본: diff·ps1_lint·`$AllowListPath2`·모드 인자 모두 정오 1 3절과 같다
- **diff(difflib 줄 대조)**
  - 경로 1 대 M4: 교체 13·14·21·26·27·46·109·116·153·154·155이고 삽입·삭제 0, 207/207줄이다.
  - 경로 1 대 retry1: 교체 13·14·21·26·27·46·109·116이고 153~155는 같다.
  - 경로 2 대 M4: 24~26의 3줄이 4줄(`$WT` 1줄 증가)로, 그리고 35, 38, 39, 57~59, 61~63, 66~71, 327, 332, 336, 340, 349, 362, 369, 379, 384, 430이 교체됐다.
  - 이 집합은 2절 경로 2 1~7과 같다.
- **ps1_lint**: 두 파일 모두 종료 0(error·warning·info 0, AST 파서)이다.
- **`$AllowListPath2`**
  - 키 15개의 순서가 M4와 같다.
  - 값 15개는 `git cat-file blob T26:<파일>` raw sha와 모두 같다.
  - M4 표 값 15개는 932f1fb raw와 같다.
  - 개수 관문 "15 expected"는 경로 2 실행본 207행에 그대로 있다.
  - `path2/test_rev26_p2.py`는 표에 없다. T26 blob은 `3e8166b2…ca2877`이고 identity·정오와 같다. 바뀐 파일 37개 안에 있다.
- **토큰 수(대소문자 무시)**
  - `tag-mode`·`imua`·`pytest`: 두 실행본 모두 0
  - `data-root`: 경로 1 1(family_table), 경로 2 9
  - `las-k1-dir`: 경로 1 1
- **rev26:152**: 경로 1 입력 인자는 모두 cwd 상대이고 `/` 구분자다. 절대 경로는 도구(`$Judge`·`$Co`·log_errors)와 인터프리터뿐이다.

### [기록] R-3 `.gitattributes`·줄바꿈(B-4)과 줄바꿈 잎: 충족
- worktree 대상 4개 파일
  - `check-attr text`는 모두 `unset`이다.
  - `ls-files --eol`은 모두 `i/lf w/lf attr/-text`다.
  - raw sha는 T26 blob과 같다(`f6591836`·`e74aeca9`·`bee9eee7`·`9e1831f5`).
- `rev26_fixed/**` 14개의 `check-attr`는 모두 `unset`이다.
- `core.autocrlf=true`이고 출처는 system gitconfig다.
- `v5_options.py` worktree raw는 `d2b903a2…`이고 `git show 932f1fb:` CRLF 꼴과 같다. LF blob은 `a88ad603`이다.
- 5단계 출력 폴더 `judge_rev26_335004a/**`: `check-attr` unset, ignore 아님, 아직 없음

### [기록] R-4 (g)·(h)의 데이터 무관 필드는 합성 실행에서 이미 기대값이다
- 합성 실행은 실제 worktree·git을 쓰므로, 데이터와 무관한 필드는 5단계 값과 같다.
- **경로 1 `head_check.json`**
  - `head` = `expected_head` = T26
  - `markers` = [], `src_params_changed` = [], `diff_exit` = 0, `exit_code` = 0
  - `blobs` 14개는 모두 `same`
- **경로 2 `harness.json`**
  - `head_check` = {expect T26, head T26, ok true, why null}
  - `v5_options.sha256` = `d2b903a2…`, `loaded` = true
- **봉인 칸**
  - 경로 1: `rules_seal`이 있는 출력에는 모두 rev26 칸이 있다. `rules_seal`이 없는 h2_select·h6_L1_reference·h12_t4h_replay·sidecars에는 칸이 없다.
  - 경로 2: `seals`가 있는 11개 출력의 rev26 칸은 sha 셋이 모두 `f6591836`이고 ok다. u3·v5j_u9는 성공 출력에 `seals`가 없다(구현 기록대로).

### [기록] R-5 입력 기준(B-5): T26 코드와 두 구현 기록이 2절과 맞는다(identity `input_basis_crosscheck` 채움용)
| 경로 | 결과 입력을 도구 저장소(WT) 기준으로 푸는 곳 | 실행본이 덮는가 | 근거 |
|---|---|---|---|
| 1 | `h11 --las-k1-dir` 기본 ROOT/LAS_K1_DIR | 예(`:116`, cwd 상대) | `resume4368_judge.py:5352` |
| 1 | `resume_k1_family.py --data-root` 기본 ROOT | 예(`:109` `'.'`) | `resume_k1_family.py:364~368` |
| 1 | `--root` 기본 ROOT(r4-inputs·jp-reuse·r4-lists·grid-h10) | 예(`'.'`) | `:5338~5345` |
| 1 | head-check·import-check·appendix-a의 `--root`=WT | W(git·코드·규칙) | `:5313·5320·5375` |
| 1 | `u3_judge_k1 DEFAULT_U3_DIR/V4_DIR` | 예(`--u3-dir`·`--v4-dir`) | `u3_judge_k1.py:73~75` |
| 1 | `d1_select DEFAULT_RULES`, `s9_settle_rejudge` 기준선, r79 판정기, paper_runs | W | `d1_select.py:39` 등 |
| 2 | D 함수 14 → `--data-root`, W 함수 9 → `repo` | 9개 호출에 `--data-root $Repo` | `p2_4368.py:619~624`, 실행본 9줄 |

- 경로 1의 `ROOT /` 사용처는 모두 03_src·04_scripts·02_params(W)였다(`resume4368_judge.py:195, 1702, 3287, 4742, 4762`).
- `resume_k1_family._argv_as_root`(`:96~104`)가 넘기는 ROOT는 `r72_g6_screen.py:80~81, 614`에서 코드 경로로만 쓰인다(W).
- `import-check`의 `module_index(root=WT)`(`:2957~2971`)는 03_src·04_scripts·05_tests/unit의 `.py`를 훑는다(rglob, 비추적·무시 포함).
  - 지금 메인과 WT 모두 이 폴더에 비추적·무시 `.py`가 0개다.
  - T26 diff에서 바뀐 import 줄은 시험 파일 3줄뿐이다. 원 출력과 같은 closure일 것으로 본다[추정].
- 4′ :153 추적 입력 확인
  - T26 추적 수가 0이 아닌 경로의 `git diff --name-only 932f1fb..HEAD`는 모두 0건이다: s9 516(rev84 18, rev85 281), `touch_phase/.../c4g2_only/grid` 6, `v5/grid_vb` 4, `v5/p3_hash.jsonl`, `v5/las/shadow_jp_b0.jsonl`.
  - `_fixed`의 sidecar·manifest·compare 사본은 T26에 없다(ls-tree 0). 932f1fb 뒤 메인에 추가된 파일이라 diff 확인 대신 sha로 확인했다: `0962f639`, `fa0b72bf`, `8ff3d32b`, log_errors `3b9a8eac`.
  - `resume_k1`·`las_k1`·`v5/dg3` 등은 git 밖(무시·미추적)이다.
  - s9의 비추적 46개(journal_v0 11-22, rev84/b5_oos·rev86 11-02)는 도구가 이름으로 읽는 파일이 아니다(`u3_judge_k1.py:423, 536`, `u3_judge_4368.py:322`).
- 합성 실행에서 NM 문자열에 WT 루트가 남은 곳: 0
  - 합성 h11 출력에 `las_k1` 문자열 0(4′ :161)
  - 경로 1 출력의 `--data-root`·`--las-k1-dir` 0
  - 경로 2 출력 8개는 argv에 `--data-root` 쌍이 남지만 `PAIR_FLAGS` I로 빠진다. A/B 차이 0

### [기록] R-6 두 경로 독립·작성자 조건: 충족
- **방법**: transcript `agent-a2b9da219fd50a504`(경로 1, 154호출)와 `agent-ac916be4796ce6acb`(경로 2, 232호출)의 도구 입력·결과에서 상대 경로 토큰과 436.8 결과 토큰을 찾았다.
- **경로 1 작성자**
  - 경로 2 코드·출력·worktree·실행본을 연 호출은 0이다.
  - 상대 경로 이름이 보인 곳은 셋이다.
    - `git branch --list 'rev26*'` 결과의 `rev26-p2` 이름(공개 3)
    - 자기 `coupled/*.py` Grep 결과 속 문자열 `path2`
    - 규칙 문서
- **경로 2 작성자**
  - 경로 1 코드를 연 호출은 0이다.
  - 경로 1 이름이 보인 곳은 셋이다.
    - 자기 `p2_*.py`의 주석
    - worktree `.gitattributes` 출력의 경로 1 파일 이름 줄(호출 [18])
    - 자기 diff 출력의 주석
- 두 작성자 모두 `judge_932f1fb` 결과 json(`_fixed` 밖), 판정서, 판정 후 감사를 연 호출이 0이다. 부록 B는 `git checkout master --` 복사와 sha만 했다.
- 둘 다 11-26에 새로 띄운 인스턴스다(rev26 3절 "새 인스턴스").
- `transcript_scope.py`(4개 에이전트)의 블라인드 노출은 0이다. 오류 3건은 이름 패턴 `git ls-files`다.
  - 경로 1: `'*u3_u6_rerun_rules*'`, `'*v5paper_imua_rules*'`(공개 3)
  - 준비 작성자: `'*compare_r4*'`(공개)
  - 패턴이 블라인드 이름과 맞지 않아 노출은 없다.
  - 그 밖은 Bash 파이프 18건으로 하우스 규칙 위반이고, 판정 영향은 없다.

### [기록] R-7 436.8 저장 결과에 판정 도구가 돈 기록: 0(봉인 2026-11-22T15:45Z 뒤 ~ 4′)
- **셸 기록**: 두 세션(0d95027e, bd7ff3b9)과 9c514956 subagents, 196개 transcript를 훑었다.
  - 대상: 판정 도구 이름(경로 1·2·compare_r4·resume_k1_family·t4h_replay·chrono_rows_judge)과 436.8 저장 경로 토큰이 함께 든 실행 명령
  - 결과: 봉인 뒤에는 실행본 초안 삭제, ps1_lint, handback_save, 이 감사의 source_guard뿐이다. 도구 실행은 0이다.
- **공개된 두 시험은 "436.8 저장 결과에 판정 도구가 돈 것"에 해당하지 않는다.**
  - 경로 1 G-S 배치 3건: `batch_V5-RESUME-K1-GS_20261113_*`는 R2 `b9f5707` 저장 결과(rev26:138의 정의)가 아니다(11-13 건조 실행). 도구 `chrono_rows_judge_4368`은 5단계 실행본에 없다. 출력은 pytest tmp에만 썼다.
  - 경로 2 `s9/rev85` 키 파일: 추적된 v4 연구 키 입력(D 자리)이다. 판정 출력을 만든 것이 아니라 키 목록을 읽었다. 932f1fb판 `study_keys`였고 출력은 tmp뿐이다.
  - 다만 rev26:126 "어느 묶음이든"을 넓게 읽을 여지가 있다. 6단계 횟수 집계와 판정서에 "범위 밖 실행 2건"으로 따로 공개하기를 권한다.
- **참고**
  - 봉인 뒤 여러 에이전트가 pytest를 실행했다.
  - 436.9 시험(`test_jp3_addendum_4a4/4a5`, `test_jp3_ed5_*`)은 `resume_k1` 저장 파일을 입력으로 읽지만 436.9 도구다.
  - 6단계에서 "판정 도구" 범위를 문장으로 고정하기를 권한다.

### [기록] R-8 확인 필요 (가): record-check ABL 한쪽 S-3은 (e) "두 경로 모두 S-2"를 실행본 꼴에서 충족한다
- **판단 근거**
  - 경로 1 실행본에서 `r4_inputs`는 `-Always` 관문이고 rc≠0이면 throw한다("nothing judged", `run_judgement_path1_rev26.ps1:90~91`).
  - R26-3이 실패한 u6 줄은 r4-inputs에서 S-2(종료 1)를 낸다(`resume4368_judge.py:3784~3793` → `u6_line_check`).
  - 그래서 경로 1은 `record_check`(`:111`)에 닿기 전에 멈춘다. 판정 출력에 S-3이 함께 실릴 수 없다.
  - 경로 2는 S-2만 낸다(`p2_4368.py:642~656`).
- **남는 경우(5단계에서 드러남)**
  - `abl_line`은 최상위 `controller_tag`를 먼저 읽는다(경로 1 보고 5절 1).
  - v5 쌍은 맞고 최상위 태그만 다른 줄이 있으면 r4-inputs는 통과하고 record-check만 S-3을 낸다. 그러면 두 경로 표지가 갈려 S-13이 된다.
  - 경로 2 6절 5와 같은 부류다. rev26 "436.8 입력의 쌍은 넷뿐(감사 실측)"이 최상위 태그까지 말하지는 않는다.
- **해석**: "S-2만"으로 읽을지는 확인 필요에 남긴다. 436.8 데이터 영향은 위 경우에만 생긴다.

### [기록] R-9 확인 필요 (나)와 경로 2 6절 4·5·6: 구현 기록·정의로만 판단
- **(나) imua "더 받아들임"**: 436.8 영향 없음
  - 실행본 `tag-mode`가 0건이다.
  - 4368 모드에서 `tag_matches`는 정확 일치만 통과시킨다(`p2_4368.py:632~639`).
  - TA(A형) 전에 두 경로 해석을 맞춰야 한다. 경로 1은 `_IMUA`만 받는다.
- **6절 4(IND_LAS 파일 줄 controller)**
  - 실제 줄이 (IND, IND_LAS)이면 위험이 (e)에 그치지 않는다.
  - 경로 1은 r4-inputs 관문에서 S-2로 전체가 멈춘다(판정 출력 없음, 1회로 셈). 경로 2는 242줄이 S-2인 채 계속 돈다.
  - 생산자 코드(`v5_rerun.py` b9f5707:60~63 `INDUSTRY_NAMES`, :379 `controller_tag`)로 보면 IND_LAS 이름으로 돌았을 개연성이 높다[추정]. 실데이터 확인은 5단계에서 드러남.
- **6절 5(u6 태그 읽기 경로가 v5로 바뀜)**: 최상위 태그와 v5 태그가 다른 줄이 있으면 (d) `harness.json bundles.H-4.tags`가 불일치한다(R-8과 같은 부류). 5단계에서 드러남.
- **6절 6(U-3 counts suite 열쇠 null)**: `u3.json`은 (a)(b) 대상이고 (d) 범위 밖이다. `Assert-U3Counts`는 합만 본다. (a)·(d) 위험은 없다.

### [기록] R-10 python-dev `conda list --export` 비결정성: 권고
- rev26:109는 export sha를 **기록**하라고만 정한다. 관문이나 전후 대조를 정하지 않는다. 그러니 원 export 파일과 sha(`d5d66884`)를 그대로 두고 비결정성(중복 dist-info 4개)을 판정서에 공개하면 문면을 충족한다(가능성 나).
- 전후 대조가 필요하면 `stable_inventory` sha(`b32b783e…`)를 쓴다. 이것은 기록을 더하는 일이라 정오가 필요 없다. 다만 "export sha로 대조한다"는 관문을 새로 두려면 정오가 필요하다.
- 5단계의 python-dev 단계(log_errors, sidecars 사본, x16_records)는 중복 패키지 넷(protobuf·soupsieve·platformdirs·onnxruntime)을 import하지 않는다.
  - Grep 결과: `verif_matrix/scripts`·`log_errors.py`에서 0건
  - sidecars는 json·sys·pathlib만 import한다.
  - 그래서 판정 영향은 없다.
- dist-info 중복 정리는 환경 변경이라 사용자 결정 사항이다(5단계 뒤 권장).

### [기록] R-11 정오 1 3절의 "rev26_run 파일 `i/lf w/lf attr/-text`" 기대는 conda export 두 파일과 맞지 않는다
- `conda_list_export_{dynamics-dev,python-dev}.txt`는 CRLF(각 580·380개, stdout 원 바이트)다. 커밋하면 `i/crlf w/crlf attr/-text`가 된다.
- raw sha는 보존된다. 판정서에 "LF가 아니라 원 바이트 보존"으로 적는다.

### [기록] R-12 실행본 자리표시
- `placeholder_scan --pattern-set both` 13건은 모두 설명문이다. 위치: 실행본 주석(경로 1 `:4·:8`, 경로 2 `:3·:6·:55·:107`, M4에서 물려받음)과 identity 설명 문자열.
- 주석의 "judge_<M4 short>/harness_path1/"은 실제 `judge_rev26_<T26>`와 다른 낡은 문구다. 실행에는 영향이 없다.

### [기록] R-13 동일성 보조 확인
- `seal_check` rev26·정오 1: 종료 0
- `worktree_locks`: 종료 0(lock 사유의 커밋 접두 = HEAD)
- worktree `status --porcelain --ignored`는 합성 실행 전후 모두 0줄이었다(-B, PYTHONDONTWRITEBYTECODE).
- `t26_identity.json`의 실행본·외부 도구·규칙 파일·v5_options sha 값은 이 감사의 재계산값과 모두 같다.

## 4′ 점검표
| 4′ 항목(rev26 :143~162 + 정오 1 3절) | 결과 |
|---|---|
| RD-1 4 대체 1~3, `rev26_run/t26_identity.json`과 고정 파일 sha | 충족(R-1, R-13). identity의 `input_basis_crosscheck` 비어 있음(W-4) |
| 두 경로 독립, 작성자 조건 | 충족(R-6) |
| 436.8 저장 결과에 판정 도구 실행 0 | 충족(R-7). 공개 시험 2건은 비해당(범위 밖 공개 권고) |
| 실행본 diff·ps1_lint·`$AllowListPath2`·`--tag-mode` 0 | 충족(R-2) |
| `.gitattributes`·줄바꿈(B-4), 기록 보호(E1-5) | T26 쪽 충족(R-3). master E1-5 미커밋(W-3) |
| 입력 기준(B-5), :152 cwd 상대, :153 추적 입력 | 충족(R-5) |
| 줄바꿈 잎(v5_options) | 충족 |
| 도구 sha 잎 | 새 출력 쪽(합성)만 함. 원 출력 쪽 미실시(W-2) |
| 정체성 필드 덮음(변형 1·2) | **불충족(B-1)**. 변형 3 미실시(W-1) |

## 확인 필요
1. B-1 처리: 부록 A r6(정오 2)인가, 사전 선언인가. 사용자 결정(rev26:162)
2. (가) (e) "두 경로 모두 S-2"를 "S-2가 나옴"으로 읽는가, "S-2만"으로 읽는가. 실행본 꼴에서는 S-3이 판정 출력에 닿지 않는다(R-8).
3. rev26:126 "어느 묶음이든"이 G-S 건조 실행 배치까지 포함하는가. 이 감사는 :138 정의에 따라 비해당으로 봤다.

## 위임 필요
- control-expert: B-1 정오 2와 부록 A r6(새 폴더, 원 출력 적용 목록 r6 생성 시 공개 문장 포함). 사용자 결정 뒤
- python-expert, `tools/verif` 후보 `rerun_identity`
  - 기능: 실행본 꼴 합성 이중 실행 + 부록 A 규범 스크립트 정규화 diff
  - 입력: 합성 루트 두 개, 규범 스크립트 경로, 토큰·창, 체크아웃 루트
  - 출력: 파일 집합 차이, 잎 경로 차이, NM의 WT 루트 잔존, 도구 sha 잎
  - 종료 코드: 0 차이 없음 / 1 차이 / 2 입력 오류
  - 이번에 즉석 스크립트 4개로 했고, 변형 3에서 다시 필요하다.

## 메인 세션 권고 (5단계 전 메인 할 일, 순서대로)
1. B-1 사용자 결정 → (r6이면) control-expert 정오 2·부록 r6 → 봉인
2. 변형 3 준비: `git -C C:\workspace\outrigger_control worktree add .claude\worktrees\rev26-t26x -b rev26-t26x 335004a7` 다음 `git -C …\rev26-t26x commit --allow-empty -m "4' variant 3"`. 이어서 이 감사자를 SendMessage로 불러 변형 1~3 재실행(합성 입력 보강 포함)과 W-2 원 출력 쪽 개수 점검(승인 문구 필요: "judge_932f1fb 원 출력에 값 비출력 개수 스크립트 허용")을 맡긴다. 끝나면 `rev26-t26x`는 지운다.
3. 메인 추적 트리 정리: `.claude/agents/paper-reviewer.md`, `00_docs/decision_log.md`의 수정 처리(커밋 여부는 메인 결정)
4. 커밋 순서(작업 트리 `.gitattributes`가 이미 E1-5 줄을 가지므로 되돌리지 않는다)
   - 커밋 ①: master `.gitattributes`(E1-5 세 줄)
   - 커밋 ② 또는 같은 커밋: 정오 1 `.md`·`.sha256`과 `rev26_run/**`(t26_identity, 실행본 두 개, conda export 두 개, prep 보고 두 개, handback, `superseded/`)
   - 커밋 뒤 `git ls-files --eol -- <rev26_run 파일·정오>`를 확인한다. `attr/-text`, LF 파일은 `i/lf w/lf`, conda export 두 파일은 `i/crlf w/crlf`(R-11)이어야 한다.
   - raw sha가 `t26_identity.json` 값과 같은지 확인한다.
   - 이 감사 핸드백 저장(`audit_4prime.md`)은 `rev26_run` 커밋 전에 하고 함께 넣는다. 4′를 다시 하면 새 파일로 둔다.
5. `t26_identity.json`의 `input_basis_crosscheck`를 R-5로 채운다(W-4). python-dev 칸에 R-10 공개 문장을 넣고 sha를 다시 고정한다. 4′ 재감사 때 새 sha를 넘긴다.
6. 5단계 직전
   - `git -C <WT> status --porcelain`(규칙 명령)이 0줄인지 보고, 명령·시각·출력을 `wt_status_before`에 적는다. 보조로 `--ignored`도 적기를 권한다.
   - 메인 `git status --porcelain --untracked-files=no`가 0줄이어야 한다.
   - 다른 에이전트의 메인 쓰기 작업(ed8 등)을 멈추거나 끝낸다.
   - 경로 1은 메인 cwd에서, 경로 2는 자체 `Set-Location`으로 돌린다. 이어서 `compare_r4.py`를 돌린다.
   - 끝난 직후 `wt_status_after`를 적는다.

## 검사하지 못한 것
- 정체성 점검 변형 3(W-1)과 합성 미산출 출력 20여 개의 실행 확인(정적 검토만, [추정])
- 원 출력 쪽 도구 sha 잎 점검(W-2)
- 데이터 무관 출력(key_map·item_list·reagg_items·appendix_a·seal·rd13_items)의 T26 대 932f1fb 내용 차이를 932f1fb 코드로 실행해 대조하지 않았다. diff hunk(`resume4368_judge.py` 157~5455, `p2_x16` RD13 문구 불변)로는 이 상수들이 바뀌지 않았다[추정].
- (e)(f)(h) 단위 시험 재실행(작성자 보고 714·353 통과를 인용만 함)
- 실데이터에 기대는 항목(IND_LAS 줄 controller, 최상위·v5 태그 일치, u6 쌍이 넷뿐인지): 5단계에서 드러남

## 실행한 검증
- 의존성: 이 세션 스탬프 있음(STAMP)
- 인터프리터
  - 집계·해시·비교: python-dev `-I -B`(MKL_THREADING_LAYER=TBB)
  - 합성 실행
    - 경로 1: dynamics-dev `python.exe -I -B`(cwd = 합성 메인), x16·log_errors·sidecars는 python-dev
    - 경로 2: `conda run -n dynamics-dev python -I -B`(cwd = WT, `--data-root` = 합성 메인)
- 즉석 스크립트(scratchpad `verif-rev26-4p\`, 보고 전 폴더째 삭제)
  - `static_check.py`(RD-1 4, .gitattributes, eol, 허용 목록, sha)
  - `build_synth.py`(경로 1 시험 `_build_inputs` 재사용), `extra_synth.py`, `h11_synth.py`
  - `run_synth.py`(실행본 꼴 경로 1 52단계, 경로 2 14단계, 토큰 2개 × 2회), `compare_synth.py`(excl_fields_r5 Rules·classify import, 부록 A 정규화 diff·도구 sha 잎·NM WT 루트)
  - `peek_*.py`(합성 출력만), `runner_diff.py`, `tracked_inputs.py`, `scan_tx*.py`·`scan_all.py`(transcript), `show_diff.py`, `dup_mods.py`(import 실패, 결과는 Grep으로 대신)
- 도구: `ps1_lint`(0), `placeholder_scan --pattern-set both`(1, 설명문 13), `worktree_locks`(0), `seal_check --no-git`(0), `transcript_scope`(1, R-6)
- git 조회: diff, ls-tree, cat-file, check-attr, check-ignore, ls-files --eol, status(메인·WT, --ignored), grep, log, worktree list, config
- `__pycache__` 잔존: rev26_fixed·WT 05_tests 모두 없음. WT `status --porcelain --ignored` 0줄(전후)
- 메모리: `audit_pitfalls.md`에 "rerun diff-0 identity checks" 한 항목을 더하고 `MEMORY.md` 색인에 짧은 문구를 더했다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha v5_resume_4368_rules_rev26.md f6591836…, v5_resume_4368_rules_rev26.sha256 e74aeca9…, v5_resume_4368_rules_rev26_erratum1.md 5e3bf3e6…, v5_resume_4368_rules_rev26_erratum1.sha256 27f98bae…, excl_fields_r5.py bee9eee7…, rev26_excluded_fields_r5.json 9e1831f5…, t26_identity.json b96dce6e…, run_judgement_path1_rev26.ps1 3516ea5e…, run_judgement_path2_rev26.ps1 a6f0b90c…, conda_list_export_dynamics-dev.txt 6cca76b4…, conda_list_export_python-dev.txt d5d66884…, prep_report.md 550df7dc…, prep_report_e1.md adef0926…, run_judgement_path1_M4.ps1 868fa7b7…, run_judgement_path1_M4_retry1.ps1 c93cfc5c…, run_judgement_path2_M4.ps1 9690f2de…, path1_report.md 0c6ac5db…, path2_report.md 9235af60…, .gitattributes e40680a1…, 디렉터리 목록 동일, ~$ 임시 파일 없음) · 경고: 형제 항목 수정 시각만 변경 1건(.git)
- 사용한 스킬: 없음

## 공개 (행위 그대로)
- **연 문서(Read)**
  - rev26 전체, 정오 1 전체
  - `path1_report.md`·`path2_report.md`·`prep_report.md`·`prep_report_e1.md` 전체
  - 두 5단계 실행본 전체
  - `excl_fields_r5.py` 전체, `excl_check.py` 1~40행
  - `t26_identity.json`: 구조와 값을 스크립트로 출력. 실행 기록 sha·파일 목록이다.
- **M4 실행본**: 세 파일을 스크립트로 줄 대조와 정규식 추출만 했다. 경로 1 M4 30~43행, 경로 2 M4 `$AllowListPath2`.
- **읽은 T26 worktree 코드 구간**
  - `resume4368_judge.py` 2957~3044, 5235~5434
  - `judge4368_common.py` 700~799
  - `resume_k1_family.py` 85~124, 320~390
  - `h6_judge_4368.py` 240~309, `h8_noise_judge_4368.py` 453~524
  - `r79_sensor_judge.py` 523~552, 770~824
  - `p2_4368.py` 615~664, `p2_x16.py` 640~679, `p2v5c_stage1.py` 705~774
  - `test_rev26_p2.py` 1~170, 266~505, `test_resume4368_supplement4.py` 1~135, 270~399
  - Grep 결과 줄: WT `verif_matrix/scripts`, `coupled`, `path2`, `03_control/s8/r72_g6_screen.py`·`r79_sensor_judge.py`
  - git diff hunk: `resume4368_judge.py` 3500~3700
- **메인 checkout 검색**
  - Grep: `05_tests/unit` `test_*.py`(경로 패턴 줄)
  - `git status`: `s9`·`03_src`·`04_scripts`·`05_tests/unit`(이름과 mtime)
  - `.claude/blind_paths.json`
- **검색 범위 이탈 1건**: Grep path로 WT `…\verif_matrix\v5_resume_4368` 폴더를 1회 썼다. glob `path2*/*.py`였고 결과는 0건이라 아무것도 나오지 않았다. 블라인드의 상위 폴더는 아니다.
- **합성 실행에서 메인 `_fixed` 사본 두 개를 썼다(원 출력 아님)**
  - 매니페스트 사본(`p2_manifest_draft.json`, sha `fa0b72bf`): 바이트를 합성 출력 폴더로 복사했고 경로 2 harness가 읽었다.
  - sidecar 사본: 합성 `resume_k1`에 실행했다.
- **transcript**: 두 작성자, 준비·정오 에이전트, 두 세션의 도구 입력을 훑었다. 결과 본문은 토큰 유무만 봤다.
- **열지 않은 것**
  - 블라인드 경로(worktree 사본 포함)
  - `judge_932f1fb\` 아래 `_fixed` 밖
  - `v5_resume_4368_harness_judgement.md`, 판정 후 감사 문서
  - 부록 B 내용(source_guard sha만)
- **판정 도구 실행**: T26 판정 도구를 합성 고정물(scratchpad)에만 돌렸다. 경로 1 52단계×2, 경로 2 14단계×2, h11×2다. 436.8 저장 결과에는 0회다.
- **종료한 프로세스**: 없음. 띄운 subprocess는 모두 스스로 끝났다(시간 초과 0).
- **지운 것**: scratchpad `verif-rev26-4p\` 전체(합성 트리·출력·스크립트·guard state)
