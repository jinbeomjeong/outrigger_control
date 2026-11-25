# 436.9 J-P3 보완 설계 명세 판 7 정오 1 — 실행 커밋 8a2a52ce의 run steps가 메운 빈 곳(2026-11-25)

- 대상: 봉인 명세 `jp3_remedy_spec_v7.md`(개정 6, 봉인 커밋 master `e241638d`), sha256 `10902ffdb763aa092588b1be0dd13f55874826b489f9aa9f1351dd7f48c1da45`(`jp3_remedy_spec_v7.md.sha256`과 같음). 봉인본은 고치지 않는다. 이 정오가 봉인본과 다르면 이 정오가 우선한다.
- 계기: 실행 커밋 C = `8a2a52ce2c07d2af11a6212a2932d2061261f156`(브랜치 `ed7-impl`, 부모 b46bdf8f, python-expert)의 run steps 13단계가 명세에 문장으로 없던 곳을 스스로 메웠다(보고 `ed7_design/postseal/handback_run_commit_C.md`, sha256 `9cabb1c29e3fed7c3aa8002df6de166e462a6fc7c63be3bb282207874dc071ce`, 확인 필요 1~4). 이 정오는 그것을 하나씩 "맞다" 또는 "고친다"로 정한다(사용자 결정 2026-11-25: 12b 계획 시점·스캔 범위는 control 판단 + 정오로 고정).
- 시점: 실행 커밋 C를 만든 뒤, 실행 전이다. 판 7 실행 단계 결과는 아무도 보지 않았다(실행이 아직 없다).
- 작성: control-expert. 연 것은 다음뿐이다(모두 경로 지정).
  - C 보고 `ed7_design/postseal/handback_run_commit_C.md`
  - C worktree의 `prelaunch_j9/run_steps_ed7/step10a_plan_ed7.ps1`(전체), `common_ed7.ps1`(Grep과 100~139행), `git show 8a2a52ce:…/run_steps/common.ps1`(Grep: 고정 입력 표 76~158행)
  - 판 6 명세 `jp3_remedy_spec_v6.md` 6.4(580~595행), 판 6 정오 1(전체), 판 6 정오 2(Grep과 158~171행)
  - `prelaunch_j9/ed5_inputs/x11/c92_keys.txt`·`c93_keys.txt`의 sha256과 git 추적 여부(내용은 열지 않음)
  - 판 6 `prelaunch_j9/ed6_inputs/x11/selection.json`은 열지 않았다(블라인드 파일 이름이 들어 있음, 2-4). 판 6 명세의 그 파일 문장만 썼다.
  - 블라인드 경로(`j9_runs/606f8713/cdry_a1/VBK_c92*`·`VBK_c93*`·`cdry_a1/logs/`, 메인과 worktree 사본 모두)는 열지 않았고 Grep·Glob 범위에도 넣지 않았다. `j_p3_cause`·`j9_runs`·worktree 루트를 대상으로 한 검색은 하지 않았다.
- **경로 2 넘김**(재감사 N-B1, 사용자 결정 Q-1 2026-11-25): 경로 2 넘김에 **1-13(결정 14, 12a·12b 한정)과 1-20 정하는 것 1~2를 [정의] 문장으로 더한다.** 두 경로가 같은 정의로 판정한다. 넘길 문장은 끝의 「경로 2에 넘길 정의 문장」에 묶었다. 그 밖의 항목은 경로 1 실행 절차와 판정 도구(T·T′) 요구이고, 경로 2 넘김을 바꾸지 않는다.
- **덧붙임(1-6~1-15, 2026-11-25)**: 판정 도구 커밋 T = `c91065b7236fac16b8649be571e6379807609317`(브랜치 `ed7-judge`, 부모 C, worktree `.claude/worktrees/ed7-judge` lock; 보고 `ed7_design/postseal/handback_judge_commit_T.md`, sha256 `769a60898638931fc35c6a47d805ff19b21d7f37aaa55312529c611faca97a94`, 근거 폴더 `ed7_design/judge_commit_c91065b7/` `SHA256SUMS` `adb82c9c…`)의 「확인 필요」 1~8을 판단하고(1-6~1-13), C의 P7-4 결과(1-14)와 블라인드 절차 공개(1-15)를 기록한다. 이때 더 연 것: T 보고, 판 6 명세 P6-2(389·408행)·정오 2 2-1(31~98행, 202행)·판 6 판정서(59·102·233행)의 경로 지정 Grep, `ed7_design/suite_8a2a52ce/run/suite_judgement.json`의 sha.
- **실행 전 감사 반영(2026-11-25)**: 감사 원문 `ed7_design/postseal/audit_prerun_T_erratum1_20261125.md`(sha256 `8c9800c9982104f83f1b9ce154b10054d5feaa80691db2769692d75cda9b0b75`; 차단 3 B-1~B-3, 실행 전 수정 6 M-1~M-6, 기록 14). P7-11은 통과하지 못했고, T를 고친 판정 도구 커밋 **T′**을 만들어 P7-11과 감사를 다시 받는다. 이 정오의 T 요구는 T′에 대한 것이다.
  - **T′ = `60ebb4a412c0b9eb20323efa536a35a0caa8c30b`**(브랜치 `ed7-judge`, 부모 T `c91065b7`, 계보 C `8a2a52ce` → T → T′; worktree `.claude/worktrees/ed7-judge` lock). 보고 `ed7_design/postseal/handback_T_prime_60ebb4a4.md`(sha256 `a607aef7c54c25d8cba85a0db3623c15a71623861c6ba5557580cd63a2de6498`), 근거 폴더 `ed7_design/judge_commit_60ebb4a4/`(`SHA256SUMS` sha256 `36f223e7a1ea22dc01c0de466a981e30b82b23f1935ce4ec9b81327abb40e0c9`). T 대비 바뀐 파일은 `jp3_ed7_judge.py`·`jp3_tjr_judge_ed7.py`·`jp3_12b_judge_ed7.py`·`test_ed7_judge.py` 넷이다(`git diff --stat c91065b7 60ebb4a4`). 아래 파일:행은 모두 T′ 트리(`04_scripts/04_hydraulic/coupled/`)의 행이다.
  - 사용자 결정(2026-11-25, 그대로 적음)
    13. 감도 J-P3 판정 집합 = 판정 4설정 줄(키 파일 기대 104), 기록 6설정 J-P3는 기록(B-1).
    14. 12a·12b J-P3에 ③ rev 7 조건 읽기를 더하되, 조건 읽기 0이면 그 조건 항목만 '해당 없음(기록)'이고 rev 6 J-P3 판정은 그대로(12a·12b에 한함; 다른 하위 명령은 0이면 판정 불가 유지) — 1-13 문면 고침(B-2).
    15. probe-repro 재현 불일치(P7-3 114줄·P7-9 64행) = setting_defect(M-1).
    16. 정오 1-7 33줄(판 6 A~D·X11) C 재실행은 **기록(관문 아님)**, 본 실행 전에 C worktree·`j9_runs\8a2a52ce` 밖 경로로, 실행 단계와 겹치지 않게; 다르면 사용자에게 알리고 판단(M-2).
  - 반영한 곳: 1-1 근거 (4)(R-8), 1-2 조건 1(M-3), 1-5(R-3), 1-6(R-7), 1-7(M-2, 결정 16), 1-8·1-9(B-3, T′), 1-13(B-2, 결정 14), 새 1-16(B-1, 결정 13), 1-17(M-1, 결정 15), 1-18(M-5), 1-19(M-6·R-12), 끝의 「판정서에 옮길 것」(M-4).
- **덧붙임(T′ 채움·r79 사건 시각, 2026-11-25)**: T′ sha와 구현 위치(1-8·1-9·1-13·1-14·1-16·1-17)를 채우고, T′ 보고 4절 확인 필요 1(B-1의 260)과 2(r79 사건 시각)를 판단했다(1-16 사실 정정, 새 1-20, 사용자 결정: control-expert 검토). 이때 더 연 것(모두 경로 지정): T′ 보고, T′ worktree의 `jp3_ed7_judge.py`(325~600행, 1000~1060행, 1260~1620행), `jp3_tjr_judge_ed7.py`·`jp3_12b_judge_ed7.py`(전체), `jp3_rev7_condition.py`(1~300행), `j_p3_inputs.py`(50~90행과 Grep), `run_v5.py`(825~854행), `verdict_runs.py`(540~600행과 Grep), `04_scripts/03_control/s8/r79_sensor_screen.py`(1~130행, 905~985행, 1183~1222행과 Grep), `rod_fault_plan.py`(1~120행, 525~570행), `las_t3_dg3.py`(Grep), 실행 경로 모듈 목록 json(Grep), 봉인 명세(Grep과 490~529·645~674·760~789행). 판 7 실행 출력은 아직 없고 열지 않았다. 공개: `04_scripts/03_control` 아래 `t_event_s` Grep이 옛 touch_phase c4g2 러너 JSON(판 7과 무관한 저장 결과) 몇 줄의 값을 화면에 냈다. 판 7·블라인드 경로의 값은 아니다(O7-16).
- **재감사 반영(2026-11-25)**: 재감사 원문 `ed7_design/postseal/audit_prerun_Tprime_erratum1_20261125.md`(sha256 `a56baf38cfb1ec41430cbbc49cd479b51d861528bb8149a39f870dbe22d6c59d`; 차단 1 N-B1, 실행 전 수정 M-a~M-c, 기록 R-1~R-14). **T′ 코드는 P7-11을 통과했고 도구 변경은 없다.** 정오 문면만 고쳤다. 사용자 결정 Q-1: 결정 14(12a·12b 한정)와 1-20 1~2를 경로 2 넘김에도 [정의] 문장으로 더한다. 사용자 결정(M-c): 실행 1단계 전에 r79 VBM·VBM0 각 1키와 t8 1쌍을 건식 확인한다(기록, 1-19). 확인 감사 원문 `ed7_design/postseal/audit_confirm_erratum1_e5e73119_20261125.md`(sha256 `02baa26c3b63f2877ef51722833259f2392a4e705d7d93bb0a7b7690853cac0c`; 대상 e5e73119, 차단 0, 기록 R-a~R-d)를 반영했다: 1-9 첫 줄(R-c), 1-13 T′ 요구 끝 문장(R-a), 1-16 사실 정정 끝 문장(R-b), 「판정서에 옮길 것」 15번 O7-19(R-d), 「경로 2에 넘길 정의 문장」의 `handoff_leak --shared` 줄.
  - 반영한 곳: 머리말 경로 2 넘김(N-B1), 1-9 구현 위치 첫 문단과 조건 2(M-a, R-3), 1-14 P7-11 기록(R-8), 1-18 경로(R-13), 1-19 건식 확인(M-c), 1-20 판단 3(N-B1), 정오 요약 표 1-13·1-20 행(N-B1, 봉인본 1019행 단서), 1-9 조건 3의 범위·12a 결측 상태(R-4·R-3), 1-20 정하는 것 4, 「판정서에 옮길 것」 6·11·14번(M-a, R-2, R-3·R-4)과 새 15·16·17번(M-b, N-B1, M-c), 머리말 덧붙임 구조(T′ 채움 덧붙임이 앞 감사 반영의 사용자 결정 목록 안에 끼어 있던 것을 그 목록 뒤로 옮김), 새 절 「경로 2에 넘길 정의 문장」(N-B1).
  - 이때 더 연 것: 재감사 원문(전체), 봉인 명세 1012~1026행(11절). 판 7 실행 출력은 없다.

## 1-1. 12b 계획의 시점과 스캔 범위 — **맞다(구현 그대로)**
- 구현: `step10a_plan_ed7.ps1`(10번째 단계)이 dg3(9번째, T-JR-12a 줄 실행) 뒤, 12b VBKM0 b1·b2(11번째) 앞에서 `jp3_12b_plan.py --edition 7`을 돌린다.
  - `--scan-root` = 메인 checkout `06_analysis` 전체(블라인드 접두는 도구가 순회 전에 이름으로 뺀다, Y7-7)
  - `--scan-extra` = 실행 worktree의 `05_tests`와 메인 checkout의 `05_tests`
  - `--scan-keys-file` = `prelaunch_j9/ed5_inputs/x11/c92_keys.txt`·`c93_keys.txt`(판 5 블라인드 c 건식 줄의 키 목록, 판 6과 같음)
  - `--scan-required` = `j9_runs/79495405`(판 6 실행 출력, 기록 B·C·D는 그 아래 `records_after_stop`), `j9_runs/6bfb2560`(probe), `j9_runs/b46bdf8f`(봉인 전 재현), `j9_runs/8a2a52ce`(이 실행)
  - `--scan-exclude`는 쓰지 않는다
- 판단 근거
  1. **목적**: 12b 블록 seed(50~53, 충돌이면 네 블록 +10 반복)가 만드는 r79 키가 이미 돌았던(결과를 볼 수 있었던) 어떤 줄의 키와도 겹치지 않게 하는 것이다(판 6 6.4 충돌 규칙, 판 5 원판). 그래서 스캔은 **12b 줄이 하나라도 생기기 전**에, 그때까지 생긴 r79 출력을 빠짐없이 덮어야 한다.
  2. **봉인 문면**: 판 7 6.4는 "넓힐 범위는 판 6 실행 출력, 기록 B·C·D, 판 7 출력(probe 포함)"이라고 정했다. 판 7 실행 출력(l1ref·dg3 등)은 실행 전에는 없으므로, 실행 전(prelaunch)에 계획하면 이 문면을 만족할 수 없다. dg3 뒤·12b 앞이 판 7 출력을 덮는 가장 늦은 때이고, 12b 출력보다는 앞이다.
  3. **판 6과의 차이**: 판 6은 실행 전(prelaunch)에 계획했다(`prelaunch_j9/ed6_inputs/x11/selection.json`). 판 6 6.4의 충돌 규칙도 "이 판의 실행 출력 폴더"를 범위에 넣었다. 판 7은 그 범위를 실제 출력이 있는 때에 훑는다. 목적과 규칙은 같고 시점만 늦다.
  4. **결과 의존 없음**(감사 R-8로 정리): seed는 키의 **존재 여부**만으로 정해진다(+10 반복 수). 도구는 앞 단계의 판정 값·지표를 읽지 않는다. 그래서 앞 단계 결과를 누가 언제 보았든 seed는 같은 값이 나온다. dg3 뒤에 계획해도 결과를 본 뒤의 선택이 생기지 않는다.
  5. **범위의 포함 관계**: `--scan-root` 06_analysis 전체가 판 6 범위(판 4a 덧붙임 4a-4 1절의 범위, 판 5 실행 출력, 이 판의 실행 출력)를 덮는다. `--scan-required` 네 루트는 그 안에 있고, 비어 있으면 도구가 멈춘다(종료 2). 그래서 필수 루트가 빠진 채 스캔이 끝나는 일이 없다. 블라인드 폴더의 키는 블라인드 파일을 열지 않고 c92·c93 키 목록으로 덮는다(판 6과 같음).
- **run steps 변경: 없다.** 구현이 위 판단과 같으므로 C를 다시 커밋하지 않는다. 그래서 P7-4 suite를 다시 돌릴 필요도 없다.
  - 만약 시점을 실행 전으로 옮기는 쪽으로 정했다면 `step10a`의 선행 단계와 순서가 바뀌어 C를 다시 커밋해야 했고, 그러면 P7-10·P7-4 전체를 새 C에서 다시 해야 했다(봉인본 5.1 「실행 커밋이 다시 바뀌면」). 이 정오는 그 길을 택하지 않는다.
- 기록: `selection.json`의 sha는 10번째 단계 `.done`의 `selection_sha256`으로 남고, 11~13번째 단계와 T의 12b 판정이 그 값을 대조한다(1-3).
- 순서 제약(봉인본 4절 5a에서 따름): 12b 결정(`decide`)은 T의 판정 도구다. 그래서 12번째(b4)·13번째(VBKM) 단계는 T와 그 감사 뒤에만 돈다. 1~11번째 단계는 T 전에도 돌 수 있다.

## 1-2. 고정 입력 목록(FIXED_INPUTS) 대신 단계별 sha 단언 — **맞다(조건 셋, 판 6 정오 2 2-3과 동등)**
- 구현: `jp3_fixed_inputs_list.py`에 `--edition 7`이 없고, C 범위(P7-10)상 더할 수 없다. 그래서 각 단계가 시작에서 입력 sha를 직접 단언한다.
  - `common_ed7.ps1` 111~127행: 봉인 명세(`10902ffd…`), G1 키(`684054ab…`), 감도 키(`be930b75…`), 12b L1 키(`9f815533…`), 12a L1 키(`eea8ed0d…`)
  - `common.ps1`(C 판) 76~158행 `Assert-FixedInputs`: V0 `main.jsonl`(`MAIN_JSONL_SHA256`), 12a 키 `h6_dg3_v4on.json`(`H6_SHA256`), 12b 사례 `h8_noise_VB.json`(`NOISE_VB_SHA256`) 등 판 6 고정 입력 전부. 실행 커밋의 `jp3_fixed_inputs.py` 값과도 대조한다.
  - 단계마다 시작·끝에 HEAD·`is_clean`·`03_src` tree id(`0cffdbdf…`)를 기록하고 다르면 멈춘다(종료 3).
- 판 6 정오 2 2-3과의 대조
  - 2-3은 코드·run steps를 고정 목록에서 빼는 대신 실행 커밋 sha와 단계별 정체성 단언으로 고정하는 것을 인정했다(조건 1·2·4). C도 같다.
  - 2-3 조건 3은 "고정 목록에는 데이터 입력을 빠짐없이 넣는다"이다. 판 7은 목록 파일 대신 단계별 단언으로 하므로, **아래 표가 판 7 데이터 입력 목록이다.** 이 표의 모든 항목이 실행 단계나 T에서 sha로 단언되면 동등하다.

| 입력 | sha256 | 단언하는 곳 |
|---|---|---|
| 봉인 명세 `jp3_remedy_spec_v7.md` | `10902ffdb763aa092588b1be0dd13f55874826b489f9aa9f1351dd7f48c1da45` | 모든 실행 단계(`common_ed7.ps1`), T |
| G1 키 `ed7_design/keys_seal_b46bdf8f/confirm_g1_grid171.json` | `684054abb1ad05d8f82141f58eafdfa3c096edae1c05c9a4b9e8ae9ffe5b5dec` | 실행 단계, `run_v5.ED7_KEY_FILE_SHA256` |
| 감도 키 `…/sens_keys_ed7.json` | `be930b75a375877d07fc84fa98a9f8b0ee463f5b592319cfd6869fcc62a05b1b` | 실행 단계, `run_v5.ED7_KEY_FILE_SHA256` |
| 12b L1 키 `prelaunch_j9/ed5_inputs/l1_keys_12b.txt` | `9f815533c0deb44925134465fe90e0f508c1819ae2c4c34bf4f3b651b6a63ca5` | 실행 단계 |
| 12a L1 키 `prelaunch_j9/l1_keys_d3c6c57e.json` | `eea8ed0d5f3aa79ecb5cf1cb892fa82f7d4bac780f8b3b17dbd069200765c6af` | 실행 단계 |
| D 키 `d_grid_keys12.json`(3ecf61f1 blob) | `a995abff9d73816f58a0e3d67a59f18b3e60fb006fe48d824012b79b57d87981` | `ed7_probe.D_KEY_FILE_SHA256`(코드 상수, C 고정) |
| V0 `main.jsonl`, `h6_dg3_v4on.json`, `h8_noise_VB.json` 등 판 6 고정 입력 | `common.ps1` `$FixedInputs` 값 | 실행 단계 `Assert-FixedInputs` |
| **12b 스캔 키 목록 `prelaunch_j9/ed5_inputs/x11/c92_keys.txt`** | `fa5385126b24baff0b46d12985a63b8c6f1fc9b7ba9fd6f797f873d88fb61ef6` | **조건 1(아래)** |
| **12b 스캔 키 목록 `…/x11/c93_keys.txt`** | `e5d1d52e0778140a53b3913e0f1cfed25643820167a264a8e8faca5123b91827` | **조건 1(아래)** |
| 12b 선정 `j9_runs/8a2a52ce/12b_plan_a<N>/x11/selection.json` | 10번째 단계 `.done`의 `selection_sha256` | 11~13번째 단계, T(조건 2) |
| L1 기준 실행 4개 `j9_runs/8a2a52ce/l1ref_a<N>/L1_VBM0·L1_VBM·L1a_VBM0·L1a_VBM.json` | 2번째 단계 기록 | T(조건 2) |
| P7-9 고정 표 `ed7_design/fixed_table_b46bdf8f/fixed_table_a2.json` | `f7754a693c75da218a0ccc0eeb42c598cd4843034f874b70e47a709eaf4554d8` | T(조건 2) |
| probe 출력 `j9_runs/6bfb2560/ed7_probe_a1/ed7_probe.jsonl` | `1107b309…`(`6bfb2560_LOCAL_ONLY.SHA256SUMS`) | T(조건 2) |
| D V0 짝 `ed6_design/keys/confirm_b_grid192.json` | `4e80e69bd2233b994853ae3f60ed0749f2c39c7dbb6390bc012b016efa5cf85b` | T(조건 2) |

- 조건
  1. **c92·c93 키 목록**: C는 두 파일의 존재만 보고 sha는 단언하지 않는다(`common_ed7.ps1` 121~122행, sha `$null`). 두 파일은 git 추적(커밋 c2357844)이다. **10번째 단계(10a, `step10a_plan_ed7.ps1`) 바로 전에** 메인이 두 파일의 sha256이 위 값과 같고, 작업본이 HEAD의 git blob과 같음을 확인해 기록한다. 명령은 `git diff --quiet HEAD -- <두 경로>`(종료 0), 또는 `git hash-object <경로>`와 `git rev-parse HEAD:<경로>`가 같음이다(감사 M-3: index가 아니라 HEAD와 비교한다. 감사 시점 값은 blob `f9332882…`·`d323c25d…`였으나 실행 직전 값을 대신하지 않는다). 다르면 10번째 단계를 돌리지 않는다. 이 확인을 run steps에 넣으려면 C를 다시 커밋해야 하므로, 실행 절차 확인으로 대신한다.
  2. **T가 단언할 입력**: 실행 단계가 만든 출력(L1 기준 4개, `selection.json`, 12b VBKM0 b1·b2)과 판정에만 쓰는 입력(고정 표, probe jsonl, D V0 짝, V0 `main.jsonl`)은 T의 판정 도구가 sha로 단언한다. 실행 단계 출력은 그 단계 `.done`·`step_record.json`의 값과 대조한다. 다르면 `setting_defect`다(봉인본 6.1 상태 순서).
  3. 판정서는 이 표와 C sha, run steps 경로(C 안의 경로)를 인용한다. 판 6 방식(고정 목록 파일)과의 차이를 공개한다.

## 1-3. 12b 결정 파일 형식 — **T 요구로 고정**
- run steps(12·13번째 단계)는 T의 `decide` 출력 JSON을 읽는다. 파일 sha를 인자(`-DecisionSha256`)로 받아 대조하고, 다르면 종료 2로 멈춘다. P7-11 때문에 T는 run steps를 바꿀 수 없으므로, T의 `decide` 출력은 아래 형식이어야 한다.
  - `status`: `"needs_b4"` 또는 `"decided"`. 그 밖의 값(판정 불가, b3 필요, 멈춤 등)이면 run steps는 12·13번째 단계를 돌리지 않는다(종료 2). b3은 판 6 정오 8 2.5대로 $N_{opp}<0.9N$이면 돌리지 않고 판정 불가로 멈춘다.
  - `blocks`: 다음에 돌릴 VBKM 블록의 목록, `{"b1", "b2", "b4"}`의 부분집합. `needs_b4`이면 b4(VBKM0 b4)를 먼저 돌리고, `decided`이면 그 목록의 VBKM 블록을 돈다.
  - 기록 필드(판정에는 쓰지 않음): 입력 sha(VBKM0 b1·b2 출력, `selection.json`, 봉인 명세), P-pred seed `numpy.random.default_rng(20261125)`, $n_{par}$·$n_{rep}$, $k_{allow}$, 코드 정체성(HEAD·`is_clean`).
- T의 단위 시험: 위 두 상태와 그 밖의 상태(멈춤), `blocks`가 부분집합이 아닐 때의 거부, run steps가 읽는 필드 이름이 같음.
- 이 형식은 판정 규칙을 바꾸지 않는다. $k_{allow}$ 결정은 봉인본 6.4(판 6 절차, P-pred)를 그대로 따른다.

## 1-4. 블라인드 이름 노출 공개(O7-14) — **기록**
- python-expert가 C 작업 중 판 6 12b 계획 명령을 알아내려고 판 6 `prelaunch_j9/ed6_inputs/x11/selection.json`의 `inputs` 블록을 통째로 출력했다. 그 블록의 `scan_excluded_files`에 블라인드 경로(`j9_runs/606f8713/cdry_a1/VBK_c92*`·`VBK_c93*`·`cdry_a1/logs/`) 아래 **파일 이름 14개**가 들어 있어 화면에 노출됐다. 파일 내용·값은 노출되지 않았고, 블라인드 경로 자체는 Read·Grep·Glob하지 않았다(C 보고 「공개」).
- 판 6 `selection.json`은 판 5·6 도구(`excluded_files`)가 제외 파일 경로를 기록하는 방식이라 **그 파일 자체가 블라인드 파일 이름을 담고 있다.** 그래서 이 파일은 블라인드 이름 목록과 같이 다룬다(열지 않거나, 필드를 골라 읽는다).
- 판 7 12b 도구(`jp3_12b_plan.py --edition 7`)는 블라인드 접두를 순회 전에 이름으로 빼고, 출력에는 적용한 접두 수(`blind_prefixes_applied`)만 남긴다(봉인본 Y7-7, b46bdf8f 확인). 판 7 `selection.json`에는 블라인드 이름이 들어가지 않는다.
- 판정서 공개 문장(판 7 판정서에 옮김): "판 7 실행 커밋 작업 중 판 6 12b 선정 파일의 `scan_excluded_files` 출력으로 블라인드 폴더 아래 파일 이름 14개가 노출됐다(내용·값 없음). 판 6 선정 파일은 설계상 블라인드 파일 이름을 담는다. 판 7 12b 도구는 이름을 쓰지 않는다."
- 공개 번호: 봉인본 머리말 오염 보고 O7-1~O7-13 다음 **O7-14**로 둔다.

## 1-5. 실행 worktree와 판정 worktree — **사용자 결정(2026-11-25) 기록**
- 사정: 단계마다 끝에 `baseline_check identity --mtime`을 돈다. `git worktree add`로 C를 새로 받으면 C가 바꾼 18개 파일의 수정 시각이 커밋 시각보다 늦어 경고(종료 1)가 나고 단계가 멈춘다(과거 사례 78fd5d2d·876d8a49). ed7-impl은 18개 모두 커밋 시각보다 앞이다(`ed7_design/run_commit_8a2a52ce/mtime_vs_commit.json`).
- 결정
  - **실행 worktree = `.claude/worktrees/ed7-impl`**(HEAD = C, 깨끗한 트리). 실행 동안과 판정이 끝날 때까지 `git worktree lock`을 건다. 이 worktree에서 커밋하지 않는다.
  - **판정 worktree = 새 `.claude/worktrees/ed7-judge`**(C에서 분기한 브랜치). T는 여기서 커밋한다. T worktree는 실행 단계를 돌리지 않으므로 수정 시각 경고와 무관하다. T의 시험·판정 기록에는 HEAD·`is_clean`을 남긴다(봉인본 5.2).
- 실행 경로 모듈 목록 파일(봉인본 5.2): T가 C 트리(`git archive`)에서 만들었다. `05_tests/data/ed7_run_path_modules_8a2a52ce.json`, sha256 **`e9c852e41a4691d1ef2ed1f6fa4b581aeded018d8293405910bae4f0ae927901`**(T 안 blob `a3491352…`, 근거 사본과 같음; 감사 R-3). 155파일: 진입(`run_v5`·`ed7_probe`·`las_t3_dg3`·`jp3_run_identity`·`jp3_12b_plan`·`jp3_ed6_suite`)의 정적 import 닫힘 중 `03_src` 밖 Python 파일 **138개**(목록 json `closure_python_files_outside_03_src`; T 보고의 "137개"는 문면 차이), `run_steps_ed7` 전체, dot-source되는 `run_steps/common.ps1`·`record_helper.ps1`. T′도 이 목록(같은 sha)으로 P7-11을 받는다.

## 1-6. j9_main의 LS 대 VB 표(L-a)의 J7 — **맞다**(T 확인 필요 1)
- T는 6.1 J7 새 비교((이름, 다리, 사유) 집합 차, 주기 차는 기록)를 V0 대비 표뿐 아니라 LS 대 VB 표(L-a: LSM 대 같은 행·위상의 VBM 줄)에도 썼다.
- 판단: 맞다. 6.1의 J7 새 비교는 "같은 대체가 주기만 달라 실패로 세어지는" 도구 결함(F7-13)을 고친 것이다. 이 결함은 비교 짝이 무엇이든 같다. LS 표에만 판 6 비교를 남기면 같은 거짓 실패가 LS 쪽에서만 남는다. 판 6 정오 1 1-5(읽기 (1)을 LS 대 VB 표에도 쓴다, 기준 짝 = 같은 행·위상의 VB 줄)와 같은 논리다.
- 문면(감사 R-7로 정리): 6.1 J7 새 비교는 판 7에서 J7 집합 비교를 하는 모든 곳(j9_main V0 대비 표와 LS 대 VB 표, 감도, probe 재현 단위 판정)에 쓴다. 기준 짝은 각 표의 정의대로다(LS 표는 같은 행·위상의 VBM 줄). 확인 단계(G1·D 줄)는 봉인본 6.3과 고정 표의 D 판정대로 V0 대비 `event_output.pass`와 Q7-C4의 retract WARN만 보고 J7 집합 비교를 하지 않는다. T의 confirm이 이와 같다.
- 공개: 이 범위는 판 7 결과 전에 T 구현을 보고 정했다.

## 1-7. P7-2 사례 재생 범위 — **고친다(봉인 문면 "A~F·X11"을 판 6과 같이 E·F 10줄로 좁힌다). run steps 변경 없음**(T 확인 필요 2)
- 봉인 문면: P7-2 "사례 재생 A~F·X11에서 J-P3 판정 키 0(③ rev 7, VBM)". C run steps는 사례 E·F × {VBM, LSM1~4} = 10줄(`ed7_cases`)만 돈다. T `cases`는 그 10줄을 판정한다.
- 판 6의 실제 범위: 판 6 봉인 P6-2도 같은 문면("사례 재생 A~F·X11")이었다(판 6 명세 389·408행). 판 6 정오 2 2-1 (iii)이 실행 범위를 정했다.
  - 판 6 구성 요소를 켠 판이 정의된 사례는 E·F뿐이다: E = R12 bottom-FL-Fs4 o0.0 × {VBL, LSL1~4} 5줄, F = `j9_case_f` FR 행 × {VBL, LSL1~4} 5줄. **P6-2 판정은 이 10줄이었다**(정오 2 2-1 (iii) 80~98행, 202행; 판 6 판정서 59·102행 "P6-2(사례 J-P3 키 0) 통과").
  - 사례 A~D·X11은 판 6 구성 요소를 켠 판이 없다. C·D는 시험 전용 플랜트(VBG4·VBG6), X11은 ③ 판정의 반례 팔이다. 판 6은 이 줄들의 판 5 판정(사례 A~F J-P3 판정 키 0, X11 반례 검출)을 **명령 불변으로 이어받았다**(정오 2 2-1 (i)-2 "P5-1형 불변" 33줄 실행, 606f8713과 명령 해시 같음).
- 판 7 판단
  - 판 7 3.6 설정 표에도 A~D·X11의 판 7 판(VBM 계열)은 정의돼 있지 않다. 판 7 구성 요소와 P1 보완을 켠 판이 있는 사례는 E·F뿐이다. 그래서 **P7-2의 판정 범위는 E·F × {VBM, LSM1~4} 10줄이다.** C run steps와 T `cases`가 맞다.
  - 사례 A~D·X11은 옛 설정(판 7 구성 요소·P1 보완 끔)이고, 판 7 P7-0(기존 설정의 명령 = 판 6 실행 커밋)의 대상이다. 그 판정은 판 6이 이어받은 판 5 판정을 그대로 이어받는다.
  - 판 6과 다른 점(공개): 판 6은 A~D·X11 줄을 실행 커밋에서 다시 돌려(P5-1형 33줄) 명령 해시가 같음을 확인했다. 판 7의 P7-0은 봉인본 4절 5대로 단위 시험(`test_ed7_harness.py`의 판 6 설정 7줄)으로 판정하고, A~D·X11 줄 자체는 다시 돌리지 않는다. 근거는 판 7 코드 변경이 판 7 구성 요소·설정에서만 켜지고(`A_ib`, `probe_d6_settings`, `p1_patch`), 옛 P1 플랜트에는 기록 키 `stale_seed_release`만 더해진다는 것이다(봉인본 3.3, P7-0).
- **run steps 변경: 없다.** C 재커밋·P7-4 재실행·T 재분기가 필요 없다.
- **P5-1형 33줄 재실행(사용자 결정 16, 감사 M-2): 기록이고 관문이 아니다.**
  - 대상: 판 6 P5-1형 33줄(판 5 `j9_cases` 15, `j9_case_f` 15, 사례 C·D 2, X11 1). C 코드로 run steps 밖에서 한 번 돌리고, `commands_sha256`을 판 6 실행 출력 `j9_runs/79495405/impl_p51_a<N>/`의 같은 줄과 대조한다. 코드 변경은 없다.
  - 시점: **판 7 본 실행(실행 단계 1~13) 전**에 돌린다. 실행 단계와 겹치지 않게 한다.
  - 출력 경로: **C worktree 밖이자 `j9_runs/8a2a52ce` 밖**이다(예: 형제 폴더 `j9_runs/p51_record_8a2a52ce/`, 메인 checkout 쪽. 정확한 경로는 메인이 정해 판정서에 적는다). C worktree에 미추적 파일을 만들지 않아야 단계별 정체성(`is_clean`) 검사와 겹치지 않는다.
  - 결과 처리: 다르면 **사용자에게 알리고 판단을 받는다.** 이 기록은 판정 상태와 실행 단계를 자동으로 막지 않는다. 같으면 판정서에 기록으로 적는다.

## 1-8. ③ 끔 설정의 태그 — **맞다(조건)**(T 확인 필요 3)
- T는 VBM0·VBKM0 줄의 태그를 `final_C4G2_LAS_K1_LSB`로 기대한다(C 코드의 `with_switch_tags` 읽기). 판 7 ③ 끔 실데이터로는 아직 확인되지 않았다.
- 판단: 맞다. 태그는 실행 경로 코드(C)가 정하는 정체성이고, T가 같은 함수로 기대값을 만든다. 첫 실측은 T8(4절 5)의 VBM0 줄이다.
- 조건: T8 판정 report에 VBM0 줄의 실제 태그를 기록한다. 기대와 다르면 `setting_defect`로 멈추는 것이 맞는 동작이다(통과로 넘기지 않는다). 그때는 판정 전에 원인을 보고 정오로 정한다.
- **구현 위치(감사 B-3, T′)**: T(c91065b7)의 `judge_t8`은 정체성을 대조하지 않았다. T′의 `t8` 하위 명령이 VBM·VBM0 양쪽 줄에 6.1 정체성 대조(`identity_defects`, ③ 켬 VBM 줄은 ③ 기록이 있어야 함, 감사 R-10)를 하고 VBM0 줄의 실제 태그를 report에 기록한다.
  - T′ `60ebb4a4`, `jp3_ed7_judge.py` `judge_t8` 1268~1317행: 1305~1306행이 오류 없는 모든 줄에 `identity_defects`(437~446행, 기대값 = 그 줄 설정의 `setting_identity`)를 돌려 결함이 있으면 `setting_defects`에 넣고, 1313~1316행이 설정별 실제 태그(`controller_tags`)와 기대 태그(`expected_tags`: VBM `ED7_TAG`, VBM0 `ED7_P3_OFF_TAG`)를 report에 남긴다.
  - 대조 내용은 `ed7_identity_problems` 393~434행이다: 태그 404~405행, `hydraulic_options` 전체 406~408행, `lsb_components` 412~415행, `lsb_settings`·`probe_d6_settings` 416~418행, ③ 끔 줄의 ③ 기록 없음 420~423행, ③ 켬 줄의 ③ 기록 없음(head-only 선언 없을 때, R-10) 424~425행, `rule_revision` 7·`spec_edition`·기본 규칙 정체성 428~433행.

## 1-9. r79 줄(12a·12b)의 정체성 출처 — **맞다(조건)**(T 확인 필요 4)
- T는 r79 줄의 `hydraulic_options`에서 `p1_patch`만 대조하고, `lsb_components`·`lsb_settings`·`probe_d6_settings`는 T4h meta에서 읽는다. 판 7 r79 실출력으로는 아직 확인되지 않았다(첫 실측은 1단계 전 건식 확인(1-19), 판정 실측은 l1ref).
- 판단: 맞다. 6.1 정체성은 항목을 정할 뿐 출처를 정하지 않는다.
- 조건
  1. 6.1 정체성 항목(`rule_revision` 7, 태그 기저, `lsb_components`, `lsb_settings`, `probe_d6_settings`, `p1_patch`, ③ 켬 줄의 `spec_edition` `10902ffd`)을 r79 줄마다 어느 출처에서든 **전부** 대조한다.
  2. 출처에 그 항목이 없으면 `setting_defect`다. 빈 값을 통과로 읽지 않는다. 단, 12a는 T4h 폴더나 그 줄의 T4h meta가 통째로 없으면 `not_judgeable`로 둔다(`jp3_tjr_judge_ed7.py` 67~69·75~77행; 실패가 상태 순서상 늘 앞선다, 재감사 R-3). meta는 있는데 항목이 없으면 `setting_defect`다.
  3. l1ref(2번째 단계) 판정 때 출처별로 읽은 값을 report에 기록한다.
- **구현 위치(감사 B-3, T′)**: T(c91065b7)에는 L1 기준 4개(`L1_VBM0`·`L1_VBM`·`L1a_VBM0`·`L1a_VBM`)의 정체성 대조가 없었고, `r79_identity_view`는 출처별 값을 남기지 않았다. T′은 L1 기준 4개의 6.1 정체성을 대조하고 출처(줄·T4h meta)별 값을 report에 남긴다. 위치는 12a(`dg3-judge`)·12b(`grade-judge`)가 L1을 읽는 곳이거나 따로 둔 l1ref 하위 명령이다. 12a·12b 줄은 같은 6.1 대조만 한다(출처별 값 기록은 l1ref만, 아래 「조건 3의 범위」; 재감사 M-a).
  - **L1 기준 4개(T′ `60ebb4a4`, 새 하위 명령 `l1ref`)**: `jp3_ed7_judge.py` `judge_l1ref` 1549~1582행(`L1_RUNS` 1516행 = `L1_VBM0`·`L1_VBM`·`L1a_VBM0`·`L1a_VBM`, 각 run 옆 `<stem>_t4h` 폴더의 meta를 `t4h_meta` 1520~1529행으로 읽음). 줄마다 `r79_line_identity` 1532~1546행이 조건 1·2를 한다: 6.1 항목(`lsb_components`·`lsb_settings`·`probe_d6_settings`·`controller_tag`·`hydraulic_options`)이 줄과 meta 둘 다에 없으면 문제(1540~1542행), 나머지 대조는 `ed7_identity_problems`(1543행, `whole_options=False` = `p1_patch`만), ③ 켬 줄의 `run_extend_start_revision` 7(1544~1545행). 문제가 하나라도 있으면 `setting_defect`(1572·1579행). 조건 3은 `identity_source_values` 371~390행이 항목(`IDENTITY_SOURCE_FIELDS` 350~352행)·출처(`row`·`meta`)별 값 digest·개수·대표값을 `identity_sources`(1577행)로 남긴다. `l1ref`는 run steps에 없으므로 판정 단계에서 메인이 `--runs`(l1ref 단계 폴더의 json 4개)와 `--step-done <l1ref .done>`을 주고 돈다(`STEP_COMMANDS` 1586행, T′ 보고 4절 4).
  - **12a 줄(T′)**: `jp3_tjr_judge_ed7.py` `bundle_problems` 57~82행이 VBM(③ 켬)·VBM0(③ 끔) 양쪽 줄마다 `r79_identity_view`(줄에 없는 항목을 T4h meta에서 채움, `jp3_ed7_judge.py` 335~347행)로 6.1 대조를 하고 문제를 `setting_defects`에 넣는다(79~81행). `--new-t4h`·`--base-t4h` 폴더가 없거나 그 줄의 T4h meta가 없으면 `not_judgeable`이다(67~69·75~77행).
  - **12b 줄(T′)**: `jp3_12b_judge_ed7.py` `line_identity_problems` 80~89행(같은 `r79_identity_view` + `ed7_identity_problems`), VBKM0는 `decide`에서 `_vbkm0_identity_problems` 92~94행 → 문제가 있으면 `setting_defect`로 멈춤(137~140행), VBKM은 `judge`의 `revision_problems` 218~231행(태그·`run_extend_start_revision` 7 + 같은 대조).
  - **조건 3의 범위를 12a·12b에서 거둔다(control 판단, 결과 전)**: T′의 12a·12b는 정체성을 전부 대조하고 문제 목록을 남기지만, 출처별 값(`identity_sources`)은 l1ref에서만 남긴다(`identity_source_values` 호출은 1577행 하나뿐). 이 정오는 12a·12b의 출처별 값 기록 요구를 **거두고 l1ref 기록으로 대신한다.** 근거: (1) 1-9 조건 3의 원문은 l1ref 판정 때의 기록이고, 12a·12b 문장은 감사 반영 때 이 정오가 덧붙인 기록 요구다(판정 항목 아님). (2) 12a(dg3: `las_t3_dg3.py` → `r79_L3L4_final.py` → `r79_sensor_screen.run_job`)·12b(같은 `run_job` + 로드 고장 계획)·l1ref 줄은 모두 같은 생산 경로(`r79_sensor_screen.py` `run_job` 908~972행의 줄 키, `write_t4h` 1183~1222행의 meta)에서 나온다. 출처 배치(어느 항목이 줄에, 어느 항목이 meta에 있는가)는 생산 코드가 정하므로 l1ref report가 그 배치를 보인다. (3) 12a·12b에서 출처에 항목이 없으면 대조에서 문제로 잡힌다(빈 값을 통과로 읽지 않음). 이것을 위해 T″을 만들지 않는다. 재감사(R-4)가 이 축소를 기록 요구의 축소로 보고 차단 아님·T″ 불요로 확인했다.
  - 12a의 T4h 폴더·meta 통째 결측은 `setting_defect`가 아니라 `not_judgeable`이다(조건 2의 단서). 둘 다 통과가 아니고, 재감사(R-3)가 통과 여부·실패 은폐에 영향이 없음을 확인했다.

## 1-10. 1-2 조건 2 "`.done` 값과 대조"의 뜻 — **고친다(문면 정정 + 실행 절차 하나)**(T 확인 필요 5)
- 사실: 실행 단계의 `.done`에는 출력 파일 sha가 없다(`selection_sha256`만 있다). T는 단계 기록(exit 0, commit = C, 끝 정체성 head = C·clean)과 출력 파일의 단계 폴더 소속을 단언하고, 출력 sha는 판정 report에 기록한다.
- 판단: 1-2 조건 2의 "그 단계 `.done`·`step_record.json`의 값과 대조"는 **"단계 기록(exit 0, commit = C, 끝 정체성 C·clean)과 폴더 소속을 단언하고, `selection.json`은 `selection_sha256`과 대조하고, 그 밖의 출력 sha는 판정 report에 기록한다"**로 고친다. T 구현과 같다.
- 빈 곳: 단계가 끝난 뒤 판정 전까지 출력 파일이 바뀌어도 위 단언으로는 드러나지 않는다.
- 막는 절차(T·run steps 변경 없음): 메인이 각 실행 단계의 `.done` 직후 그 단계 폴더에 `SHA256SUMS`(`tools/verif/baseline_check.py write-sums --recursive`)를 만든다. T 판정을 돌리기 직전에 `baseline_check.py sums`로 불일치 0을 확인하고 기록한다. 불일치가 있으면 그 단계 판정을 돌리지 않는다. 판정 report의 출력 sha와 이 SUMS가 같아야 한다(판정 후 감사가 대조).

## 1-11. j9_main J-P3 기대 판정 행 수 200 — **맞다**(T 확인 필요 6)
- T는 j9_main J-P3(판 6 판정 집합) 기대 행 수를 판 6과 같이 200으로 둔다.
- 판단: 맞다. `ed7_j9_main` 388줄은 판 6 `ed6_j9_main`의 job 배치에서 설정 이름만 VBL·LSL1~4 → VBM·LSM1~4로 바꾼 것이다. head-only 선언은 사례 경로로 정해지므로 판 6과 같다(판 6: 설정마다 40, R12 160·R14 10·R15 10·R16 20, head-only 188). 봉인본 6.2의 "키 목록 단계에서 다시 센다"를 이 배치에서 세면 200이다.
- 조건: 판정 때 실제 판정 행 수가 200이 아니면 `setting_defect`다. ③ rev 7 조건 행 수는 이와 별도로 판정 때 T4h로 센다(봉인본 6.2 R-5).

## 1-12. 12b `decide`의 `--spec` — **맞다**(T 확인 필요 7)
- 봉인 명세는 C·T 트리에 없다(master e241638d). T는 `decide`에 `--spec <메인 checkout 명세>`를 받고, 없거나 sha가 `10902ffd…`가 아니면 `setting_defect`다.
- 판단: 맞다. 봉인 명세는 1-2 표의 데이터 입력이고 sha로 단언된다. 실행 단계도 같은 경로·sha를 단언한다.

## 1-13. ③ rev 7 조건 읽기 0의 범위 — **고친다(사용자 결정 14, 감사 B-2)**(T 확인 필요 8)
- T는 한 하위 명령에서 ③ rev 7 조건 읽기가 0이면 그 조건의 J-P3 항목을 판정 불가로 두고, 상태 순서(실패 > `setting_defect` > 판정 불가 > 통과)대로 그 하위 명령의 상태가 판정 불가가 된다(다른 항목이 실패면 실패). 그러나 T는 12a(`jp3_tjr_judge_ed7.py`)·12b(`jp3_12b_judge_ed7.py`)에서 조건 읽기를 계산하지 않았다(감사 B-2).
- 판단
  - **j9_main·감도·확인 단계(G1·D)·cases**: T 그대로 맞다. 조건 읽기가 0이면 그 조건의 J-P3 항목은 판정 불가이고, 상태 순서대로 그 하위 명령이 판정 불가가 된다. 봉인본 6.1·6.5와 "판정 행 0 = 판정 불가(통과 아님)"를 함께 읽은 결과다.
  - **12a(T-JR-12a)·12b(T-JR-12b)**: J-P3 판정에 ③ rev 7 조건 읽기를 더한다(T′). 조건 읽기가 0이면 **그 조건 항목만 '해당 없음(기록)'**이고, rev 6 판정 집합의 J-P3 판정은 그대로 한다(판정 행 0이면 판정 불가, 침범이면 실패). 이 예외는 12a·12b에만 쓴다.
  - 근거: 12a는 J-P3 판정 행이 하나(판 6 정오 1 1-3 5, 판 7도 같은 꼴)이고, 12b는 r79 사례 키 위의 판정이라 "사건 뒤 첫 PROBE 단계의 `locked_ext` → `moving_ext` 전환"이 구조적으로 없을 수 있다. 이때 조건 항목 하나 때문에 rev 6 판정이 끝난 하위 명령 전체를 판정 불가로 두면, 판 7이 고치려는 기전과 무관한 빈 집합이 합격을 막는다. 반대로 조건 읽기가 있으면 그 침범은 판정한다(빈 집합이 통과로 넘어가지는 않는다: 조건 행이 있는 경우는 판정, 없는 경우는 해당 없음으로 기록에 남는다).
  - 결과 전 결정이다. 판 7 실행 결과는 아직 없다.
- T′ 요구: 12a t12 판 7 쪽과 12b 판정 줄에 `condition_judgement`를 넣는다. r79 T4h에 조건 판정 배열(`jp3_t_s`, `jp3_class`, `jp3_plant_state`, `jp3_p_tr_Pa`, `jp3_used_bound_Pa` 등 `T4H_ARRAYS`)이 있는지는 첫 l1ref·dg3 출력에서 `key_presence.py --npz-dir … --array …`로 확인한다(감사 권고 10). 배열이 없으면 `setting_defect`다(빈 값을 '해당 없음'으로 읽지 않는다). `no_event` 줄 수(`rev7_condition.summary.no_event_lines`)와 `rev7_condition_records`(조건 읽기 0의 '해당 없음' 기록)를 report에 남긴다(T′ 552~573행과 같음; 확인 감사 R-a).
- **구현 위치(T′ `60ebb4a4`)**
  - 공통: `jp3_ed7_judge.py` `r79_condition_entry` 528~549행(T4h 파일이나 `T4H_ARRAYS` 결측 → `setting_defect` 539~543행, 조건 도구 `jp3_rev7_condition.line_condition`의 결측이 `t_event_s` 하나뿐이면 상태 `no_event`·조건 읽기 0 546~548행), `r79_condition_judgement` 552~559행(요약에 `no_event_lines`), `r79_condition_basis` 562~573행(침범 → 실패, 결측 → `setting_defect`, 조건 읽기 0 → 판정 불가가 아니라 기록 "해당 없음"), `is_judged_grade` 576~582행(판정 등급 ideal·normal 줄만).
  - 12a: `jp3_tjr_judge_ed7.py` `condition_lines` 100~110행, `add_condition` 113~125행(`t12 --bundle VBM`에서만, 133~134행).
  - 12b: `jp3_12b_judge_ed7.py` `judged_condition_lines` 173~185행(6.3.7 (4) 판정 범주 쌍의 VBKM 줄 중 판정 등급), `_with_condition` 188~204행.
  - j9_main·감도·확인·cases는 `condition_basis` 512~521행(조건 읽기 0 → 판정 불가)을 그대로 쓴다.
- **12a·12b에서 조건 항목이 늘 '해당 없음'이 되는 사실과 그 처리는 1-20이 정한다.**
- 공개: 12a·12b의 조건 읽기 0 처리는 다른 하위 명령과 다르다(결정 14). 봉인본 6.1·6.5 문면("0이면 판정 불가")을 12a·12b에 한해 좁힌 것이다.

## 1-14. P7-4 단위 시험 전부(실행 커밋 C) — **기록: 통과**
- `full_suite_ed7.ps1 -Side run`을 C(8a2a52ce)에서 돌렸다. 판정 `ed7_design/suite_8a2a52ce/run/suite_judgement.json`(sha256 `1e020f0545847cb2cd6318c87ff7592a0afa4b56f9296b3dad1b46f24eadc07e`; 폴더 `SHA256SUMS` `ae9839ca423a462d4a5651270faf19aa8331398178973f75a6603f8dfdfb5f59`): **status pass**. 시험 8695개(통과 8678, 실패 2, 건너뜀 15), 새 실패·핵심 미통과·새 건너뜀 0, 4199 s. 실패 2·건너뜀 15는 기준 목록(`571f42a1…`, base 79495405)에 있는 것이다.
- P7-0·P7-6은 봉인본 4절 5대로 이 P7-4로 판정한다(통과).
- T(c91065b7)의 시험 범위(P7-11): 84개 파일, 2650 통과, 실패·오류·건너뜀·xfail 0, 기준 목록 대조 pass(T 보고 3절). 그러나 실행 전 감사에서 차단 3(B-1~B-3)이 나와 **T는 P7-11을 통과하지 못했다.** T′(`60ebb4a412c0b9eb20323efa536a35a0caa8c30b`)에서 P7-11 시험 범위와 감사를 다시 한다.
- T′ 보고(2절)에 따른 T′의 P7-11 기록: C 대비 변경 경로 9개(모두 `04_scripts/`·`05_tests/`), 실행 경로 목록 155파일 중 변경 0, `03_src` tree = C. T′ 시험 범위 84파일 **2658 통과**, 실패·오류·건너뜀·xfail 0, 기준 목록 `571f42a1…` 대조 pass, 시작·끝 HEAD `60ebb4a4`·`is_clean` True(근거 `judge_commit_60ebb4a4/`). `suite_T/suite_record.json`의 `worktree_tests_exit`는 1이고, 원인은 **경고 8**(`data_literal_not_rebased` 7, `rebase_never_used` 1; `worktree_tests.md` 101~112행)뿐이며 **시험 실패 0**이다(pytest 0, `junit_skips` 2658/2658, skip·xfail 0; 재감사 R-8). 재감사가 T′의 P7-11 통과를 확인했다(재감사 원문 「감사 요약」).
- 실행 전 감사가 같은 실측으로 P7-10(C 범위)과 P7-4(C suite)를 통과로 확인했다(감사 「실측 결과」).

## 1-15. 블라인드 절차 공개(O7-15) — **기록**
- T 작업 중 python-expert가 도구 보완을 시험하면서, 기존 실데이터 시험이 메인 checkout 전체를 대상으로 `git ls-files --others`를 5회 실행했다. 그 과정에서 git이 블라인드 폴더(`j9_runs/606f8713/cdry_a1/`)의 목록을 읽었다. 출력에 블라인드 경로의 이름·건수는 나오지 않았다. 그 시험에 블라인드 경로 `--exclude`를 더했다.
- 공개 번호: O7-15(1-4의 O7-14 다음). 판정서에 옮긴다.

## 1-16. 감도 J-P3 판정 집합 — **고친다(사용자 결정 13, 감사 B-1)**
- 사실(감사 B-1의 지적): T의 감도 J-P3(`jp3_ed7_judge.py` 886·888행, c91065b7)는 460줄 전체(기록 6설정 포함)를 J-P3 도구에 넘겨, 봉인 키 파일 `sens_keys_ed7.json`(be930b75)의 `expected_j_p3_judged_rows` **104**(판정 4설정 줄만, `ed7_key_lists.py` 152행)와 비교한다. 감사는 기록 6설정도 ③ 켬(`_P3X`)이라 판정 행이 260이 되어 결과와 무관하게 `setting_defect`가 난다고 보았다.
- **사실 정정(T′ 보고 4절 확인 필요 1, 코드로 확인)**: 판정 행 수는 260이 아니라 **이미 104였다.** J-P3 도구의 hold revision 판정(`j_p3_inputs.py` `_revision_5_judgement` 250~256행)이 판정 설정 표 `REV5_JUDGED_SETTINGS`(67~68행; 판 7 몫 `ED7_JUDGED_SETTINGS` 62~63행 = VBM·LSM1~4·VBKM·판정 4설정)의 줄만 `rev7` 판정에 넣고, 기록 6설정 줄은 `rev7_record_only`로 따로 둔다. `j_p3_inputs.py`는 C·T·T′에서 같다(`git diff --stat 8a2a52ce c91065b7 -- …/j_p3_inputs.py` 빈 출력, T→T′ 변경 파일 4개에 없음). 그래서 이 정오의 앞 문면 "260 ≠ 104로 `setting_defect`가 난다"는 틀렸다. 260은 판정 행 수가 아니라 감사가 460줄 배치에서 기록 설정 줄을 빼지 않고 센 수다. 재감사(확인 항목 4, R-1)의 답: T에서 기록 설정 J-P3 침범(H-7)은 감도 status에 **들어가지 않았다**(`jp3_basis` 468~469행의 `has_judged_breach`와 `j_p3_over_rows` 232~235행의 `status_by_revision`은 판정 몫 `rev5/6/7`만 본다). T에서 status에 들어갈 수 있었던 것은 기록 줄의 **줄 단위 결함 수 5종**(`rule_missing`·`test_only`·`l1_reference`·`revision_key_missing`·`revision_key_mismatch`; `j_p3_over_rows` 236~237행, `jp3_basis` 471~474행)뿐이다. T′은 기록 줄을 J-P3 status에 넣지 않는다. 다만 460줄 전체의 6.1 정체성 대조(`judge_sens` 933·947~948행)는 status에 남는다.
- 그래도 결정 13과 아래 T′ 요구는 유지한다. 판정 집합을 도구의 설정 표에 기대지 않고 키 파일 `judged` 줄로 명시해 고정하는 것이고, 판정 결과는 바뀌지 않는다.
- 결정: **감도 J-P3 판정 집합 = 판정 4설정(VBMslow·VBMfast·VBMc005·VBMc04) 줄**이다. 기대 판정 행 수는 키 파일의 104다. 기록 6설정 줄의 J-P3는 **기록**이고 판정 상태를 바꾸지 않는다(침범이 있으면 공개).
- ③ rev 7 조건 판정도 같은 판정 4설정 줄만 본다(T와 같음). 두 판정의 범위가 같아진다.
- T′ 요구: 감도 J-P3를 키 파일 `judged` 줄로 한정하고, 기록 설정 J-P3는 별도 기록으로 둔다. 460줄 배치 꼴(기록 설정 포함)의 합성 시험을 더한다(감사 지적: 기존 e2e 시험은 VBMslow 10줄만 써서 이 결함을 덮지 못했다).
- 구현 위치(T′ `60ebb4a4`): `jp3_ed7_judge.py` `_sens_jp3` 1006~1032행. 키 파일 줄의 `judged`가 참인 줄만 J-P3·③ 조건 판정(1012·1017~1018행), 나머지는 `J-P3_record_settings`·`rev7_condition_record_settings` 기록(1013·1024~1029행), `judged` 플래그가 그 줄 설정의 판정 4설정 소속(`rules.SENSITIVITY_JUDGED`)과 어긋나면 `setting_defect`(1014~1016·1021~1023행). 합성 시험은 `test_ed7_judge.py`(T′ 보고 2절: 460줄 배치에서 판정 행 104, 기록 설정 침범은 status에 들지 않음).
- 결과 전 결정이다.

## 1-17. probe 재현 불일치의 분류 — **고친다(사용자 결정 15, 감사 M-1)**
- 사실: T의 `probe-repro`(`jp3_ed7_judge.py` 1331·1364행)는 `commands_sha256` 차이를 판정 실패(`failures`)로 넣었다. 같은 도구의 감도·확인 단계는 재현 차이를 `setting_defect`로 둔다.
- 결정: **P7-3(a2 114줄 `commands_sha256` 재현)과 P7-9(고정 표 64행 재현)의 불일치는 모두 `setting_defect`다.** 봉인본 P7-9("재현 불일치(양방향)면 멈춤, `setting_defect`")와 6.1 「재현 불일치와 상태 순서」를 P7-3에도 그대로 쓴다. 재현 불일치는 판정 실패가 아니라 구현·도구 결함이고, 그 단계는 판정 불가(통과 아님)이며 다음 조치는 사용자에게 묻는다.
- T′ 요구: `probe-repro`의 해시 차이를 `setting_defect`로 옮기고, 그것을 고정하는 시험(`test_ed7_judge.py` 500행 꼴)을 고친다.
- 구현 위치(T′ `60ebb4a4`): `jp3_ed7_judge.py` `judge_probe_repro` 1448~1485행. P7-3 해시 차이(`_probe_hash_match` 1488~1512행의 `differences`)와 P7-9 고정 표 재현 차이(1465~1467·1471~1472행)를 모두 `setting_defects`에 넣고 `failures`는 비운다(1475~1478행).

## 1-18. 판정 출력 위치 — **고친다(감사 M-5)**
- T의 `code_identity`는 `git status --porcelain`(미추적 포함)으로 `is_clean`을 정한다. 판정 `--out`이 T′ worktree 안이면 그 뒤 report의 `is_clean`이 거짓이 된다. 판정 report를 단계 폴더 안에 쓰면 1-10의 단계 폴더 SUMS 대조에서 목록 밖 파일이 생긴다.
- 결정: **판정 `--out`은 T′ worktree 밖이자 실행 단계 폴더 밖**에 둔다(예: `j9_runs/8a2a52ce/judge_60ebb4a4/<하위 명령>/`). 실행 단계 폴더에는 판정 산출물을 쓰지 않는다.

## 1-19. 순서와 커밋 — **기록(감사 M-6·R-12)**
- T′과 그 재감사(P7-11)는 **판 7 실행 출력이 생기기 전에** 끝낸다(감사 M-6). 실행 출력이 있는 동안 판정 도구를 고치면 "결과가 있는 상태에서 도구를 고쳤다"는 문제가 생기기 때문이다. 부득이 함께 해야 하면 T′ 작성자 지시문에 `j9_runs/8a2a52ce` 전체를 블라인드 경로로 넣고 공개한다.
- 근거 폴더 `ed7_design/run_commit_8a2a52ce/`·`suite_8a2a52ce/`·`judge_commit_c91065b7/`·`postseal/`은 이 정오를 봉인할 때 함께 커밋한다. `postseal/`에는 봉인 때 `SHA256SUMS`를 만든다(감사 R-12). 커밋 전에 `git status --ignored`로 인용 파일이 ignore에 걸리지 않는지 본다. `judge_commit_60ebb4a4/`도 같은 때 함께 커밋한다(재감사 R-11).
- **실행 1단계 전 건식 확인(재감사 M-c, 사용자 결정 2026-11-25; 기록, 판정에 쓰지 않음)**: r79 VBM·VBM0 각 1키와 `ed7_t8` 1쌍을 C 코드로 건식 실행하고, 그 출력에 `key_presence.py`(줄 키·T4h 배열)와 T′ `l1ref`·`t8`(stand-in `.done`)을 돌려 정체성 문제가 0인지 본다. 출력과 판정 report는 **C worktree 밖이자 `j9_runs\8a2a52ce` 밖**에 둔다. 문제가 나오면 실행 1단계 전에 사용자에게 알린다(출력이 없는 상태에서 T″을 정할 수 있게).

## 1-20. r79 줄(12a·12b)의 사건 시각 — **정의하지 않는다(나). 12a·12b의 ③ rev 7 조건은 사건 시각 부재로 늘 '해당 없음(기록)'이다**(T′ 보고 4절 확인 필요 2, 사용자 결정: control-expert 검토)
- 사실(코드)
  1. **봉인 문면**: ③ rev 7 조건의 판정 집합은 "사건 시각 뒤 첫 PROBE 단계에서 `locked_ext` → `moving_ext` 전환을 가진 다리의 `carry_ext` 읽기"다(봉인본 3.5 500행, 6.1 658행). 조건이 겨냥하는 기전은 "LEVEL 중 사건 뒤 첫 탐침에서 잠긴 다리의 `carry_ext` 해제 읽기"의 묵은 수축 M2 시드다(3.5 496행). 사건 시각이 무엇인지는 따로 정의하지 않고, 조건 도구가 줄의 `t_event_s`를 쓴다(`jp3_rev7_condition.py` `line_condition` 219~225행, `first_probe_window` 111~123행). event 경로 줄에 사건 시각이 없으면 `setting_defect`다(봉인본 3.5 507행, 6.1 659행; 도구 220~224행).
  2. **`t_event_s`의 출처(j9 계열)**: `verdict_runs.py` 560~590행이 기준 실행의 READY·LOC·DONE 시각에서 분기해 플랜트 사건(`r67.EVENTS`의 다리 지면 사건)을 넣고 그 시각을 `t_event_s`로 적는다(566·590행). `run_v5.py` 847행이 그것을 줄에 옮긴다. 즉 사건 시각은 **하네스가 분기해 넣은 플랜트 사건의 시각**이다.
  3. **r79 줄에는 사건 시각 키가 없다**: r79 하네스는 G6(한 패드 연약 토양, 시작부터 있음), G8(한 패드 바닥 이동), ref(패드 형식·바닥 경사)다(`r79_sensor_screen.py` 4~7행). 줄을 만드는 `run_job` 908~972행과 T4h meta를 만드는 `write_t4h` 1183~1222행 어디에도 사건 시각 키가 없다(`04_scripts/03_control` 아래 `t_event_s` Grep: `r79_sensor_screen.py`·`r72_g6_screen.py`·`r69_g8_screen.py`·`r79_L3L4_final.py`·`rod_fault_plan.py` 0건; `las_t3_dg3.py`는 `r79_L3L4_final.py`를 그대로 부른다, 1~2행). r79 줄은 `head_only_declared` False(`r79_sensor_screen.py` `j_p3_run_record` 1306~1314행)라 4a-7 순서로는 event 경로 줄이다.
  4. **12b의 시각 후보**: VBKM 줄에는 로드 압력 센서 고장의 `rod_fault.first_applied_t_s`(`rod_fault_plan.py` `record` 530~554행, 544행; 줄 키 `r79_sensor_screen.py` 955~956행, T4h meta 1218행)가 있다. 고장은 센서 모델 뒤 한 다리의 로드 판독만 바꾼다(`rod_fault_plan.py` 3~4행). 12b 앵커는 τ_C(CHECK 나감)·τ_R(LEVEL 수축 시작)·TRw다(`GATE_ANCHORS` 111~113행).
- 판단: **정의하지 않는다.**
  1. **g6 약한 다리**: 연약 패치는 시작부터 있는 토양 조건이라 시각이 없다. t = 0, LEVEL 시작, 첫 이륙(`t_lift_s`) 같은 대리 시각은 모두 봉인 문면에 없는 새 정의다. t = 0이면 "첫 PROBE"는 CHECK 공중 영점 교정 뒤의 첫 접지 탐침이 되어, 3.5가 말하는 "LEVEL 중 사건 뒤 첫 탐침"이 아닌 다른 읽기 집합을 판정하게 된다.
  2. **12b 로드 고장 주입 시각**: 시각은 정의돼 있지만 의미가 다르다. 조건의 기전은 **플랜트**의 묵은 수축 열림 시드이고, 판 7 판정 플랜트(VBKM 포함)는 P1 보완 (d)로 그 시드를 두지 않는다(3.5 498행). 로드 고장은 **판독**만 바꾸므로 그 시각 뒤 첫 탐침 읽기는 시드 기전이 아니라 고장 대응(D1 래치·대체 경로)을 섞는다. τ_C 앵커면 "첫 PROBE"는 첫 접지 탐침이라 1과 같은 문제가 있다. 이 읽기 집합의 사전 예측도 없다(3.5 510행의 예측은 j9 115읽기에서 나왔다; 「예측은 구현과 같은 모델 경로로」).
  3. **판정 집합 변경**: 사건 시각을 새로 정의하면 r79 줄에 조건 읽기가 생겨 ③ rev 7 판정 집합이 봉인 뒤에 바뀐다(대리 시각 뒤 첫 PROBE의 읽기가 새로 판정된다). 정의하지 않으면 판정 집합은 그대로이고, 바뀌는 것은 r79 줄의 '사건 없음' 처리뿐이다. 그 처리도 판정 정의이므로 경로 2 넘김에 [정의]로 더한다(재감사 N-B1, 결정 Q-1; 끝의 「경로 2에 넘길 정의 문장」).
  4. **덮는 범위**: 조건은 사건 시각이 있는 줄(j9_main, 감도 판정 4설정, 확인 단계 G1·D, cases E·F)에서 판정된다. P1 보완 (d)는 플랜트 코드라 하네스와 무관하게 같은 동작이므로, 12a·12b에서 조건을 빼도 시드 제거 확인이 빠지지는 않는다. 12a·12b의 rev 6 J-P3 판정은 그대로 한다(결정 14).
- 이 정오가 정하는 것
  1. 12a·12b(r79 줄)에서 `t_event_s`가 없는 것은 **구조적 부재**(하네스에 사건 시각 개념이 없음)다. 봉인본 3.5 507행·6.1 659행의 "event 경로 줄에 사건 시각이 없으면 `setting_defect`"를 r79 줄에는 쓰지 않고, **사건 없음 = 조건 읽기 0 = 그 조건 항목만 '해당 없음(기록)'**으로 읽는다(결정 14의 범위 안, 12a·12b에 한함). T′ `r79_condition_entry` 546~548행(결측이 `t_event_s` 하나뿐이면 `no_event`)이 이와 같다.
  2. T4h 조건 배열(`T4H_ARRAYS`)이나 T4h 파일이 없으면 여전히 `setting_defect`다(T′ 539~543행). r79 줄이 뜻밖에 `t_event_s`를 가지면 조건을 정상 계산한다(T′ 544행 → `line_condition`).
  3. **항등 지표 공개**: 이 조건 항목은 12a·12b에서 정의상 늘 '해당 없음'이고 침범이 나올 수 없다. 그래서 12a·12b에서는 **판정 지표가 아니라 구현 확인(T4h 조건 배열 존재, `no_event_lines` 수 = 판정 등급 줄 수)**이다. report의 `rev7_condition.summary.no_event_lines`와 판정 등급 줄 수가 다르면(사건 시각이 있는 r79 줄이 생겼다는 뜻) 판정서에 그 사실을 적는다.
  4. 도구 변경 없음, T″ 없음. 재감사(확인 항목 3)가 이 판단과 T′ 구현(528~549행, 546행)이 같음을 확인했다. 1·2는 경로 2 넘김에 [정의]로 더한다(결정 Q-1, 끝의 「경로 2에 넘길 정의 문장」).
- 결과 전 결정이다. 판 7 실행 출력은 없고 보지 않았다.

## 판정서에 옮길 것(감사 M-4, 이 정오의 공개 항목 전부)
1. 1-1: 12b 계획을 판 6(실행 전)과 달리 dg3 뒤·12b 앞에 했다. seed는 키 존재로만 정해진다.
2. 1-2 조건 3: 판 7은 고정 입력 목록 파일 대신 단계별 sha 단언과 1-2 표로 데이터 입력을 고정했다(판 6 방식과의 차이). 1-2 조건 1(c92·c93 sha와 HEAD blob 확인)의 실행 기록.
3. 1-4: O7-14(판 6 `selection.json` 출력으로 블라인드 파일 이름 14개 노출, 판 6 선정 파일이 블라인드 이름을 담음).
4. 1-6: J7 새 비교를 LS 대 VB 표에도 쓰는 범위를 T 구현을 보고 정했다.
5. 1-7: **봉인 문면 P7-2 "사례 재생 A~F·X11"을 봉인 뒤·결과 전에 E·F × {VBM, LSM1~4} 10줄로 좁혔다.** A~D·X11은 P7-0으로 이어받았고, 판 6과 달리 그 줄을 실행 단계에서 다시 돌리지 않았다. P5-1형 33줄 기록 재실행(결정 16)의 결과.
6. 1-8·1-9: T8 VBM0 실제 태그, L1 기준 4개의 출처별 정체성 값(l1ref report `runs.<stem>.identity_sources`). 12a·12b는 정체성 대조 결과(문제 목록)만 인용한다.
7. 1-10: 단계별 SUMS를 만들고 판정 직전에 대조한 기록.
8. 1-13: 12a·12b에 한해 ③ rev 7 조건 읽기 0을 '해당 없음(기록)'으로 둔다(결정 14, 봉인본 6.1·6.5 문면을 좁힘). 다른 하위 명령은 0이면 판정 불가다.
9. 1-14: C의 P7-4 통과, T가 P7-11을 통과하지 못해 T′을 만들었다는 사실.
10. 1-15: O7-15(실데이터 시험의 `git ls-files --others` 5회).
11. 1-16: 감도 J-P3 판정 집합을 판정 4설정으로 정했고(결정 13), 기록 6설정 J-P3는 기록이다. 기록 설정 J-P3 침범은 감도 report의 `J-P3_record_settings.rev7_record_only.runs_with_breach`에서 읽어 적는다(`J-P3_record_settings_judged_rows`는 구조적으로 늘 0이라 쓰지 않는다; 재감사 R-2). 감사 B-1의 "판정 행 260"은 실측과 달랐다(J-P3 도구가 이미 판정 설정 표로 104만 판정했다; 1-16 사실 정정).
12. 1-17: P7-3·P7-9 재현 불일치는 `setting_defect`(결정 15).
13. 1-20: **12a·12b의 ③ rev 7 조건은 r79 줄에 사건 시각이 없어(하네스에 사건 개념 없음) 늘 '해당 없음(기록)'이다.** 이 조건 항목은 12a·12b에서 판정 지표가 아니라 T4h 조건 배열 존재 확인이다. 사건 시각의 대리 정의(g6 시작, 12b 로드 고장 주입 시각)는 결과 전에 검토하고 쓰지 않았다. 봉인본 3.5·6.1의 "event 경로 줄에 사건 시각이 없으면 `setting_defect`"를 r79 줄에 한해 '사건 없음'으로 읽었다. report의 `no_event_lines`와 판정 등급 줄 수.
14. 1-9: 12a·12b 줄의 출처별 정체성 값 기록 요구를 거두고 l1ref 기록으로 대신했다(T′ 구현을 보고 정함, 결과 전; 재감사 R-4). 12a의 T4h 폴더·meta 통째 결측은 `not_judgeable`이다(재감사 R-3).
15. 블라인드 절차 공개(재감사 M-b)
    - **O7-16**: 정오 1 T′ 채움 때 control-expert의 `04_scripts/03_control` 아래 `t_event_s` Grep이 판 7과 무관한 옛 touch_phase c4g2 러너 JSON 몇 줄의 값을 화면에 냈다(머리말 덧붙임). 판 7·블라인드 경로의 값은 아니다.
    - **O7-17**: T′ 작업 중 python-expert가 판 6 `j9_runs/79495405/l1ref_a1/L1_VBL.json`을 경로 지정으로 읽고 줄·`base`·`r79` 키 이름, 하네스 종류 수, T4h 배열 이름을 출력했다. 값은 출력하지 않았다(T′ 보고 5절).
    - **O7-18**: T′·정오 1 재감사 중 verif-protocol-auditor의 `ref_check`가 비슷한 이름 후보로 `j9_runs/606f8713/cases_a1/logs/…` 아래 파일 이름 몇 개를 화면에 냈다. 블라인드 정의(`cdry_a1/VBK_c92*`·`VBK_c93*`·`cdry_a1/logs/`) 밖의 이름이다. 재감사는 그 밖에 판 6 `L1_VBL.json` 키 존재·건수, `L1_VBL_t4h\*.npz` 배열 이름, `l1ref_a1` 아래 npz 파일 이름 100개(568개 중), 판 6 `impl_t8.done`(명령·정체성·종료 코드)을 보았다(재감사 원문 「감사 요약」 본 결과).
    - **O7-19**: 정오 1 확인 감사(`audit_confirm_erratum1_e5e73119_20261125.md`) 중 verif-protocol-auditor가 블라인드를 품은 상위 폴더 `j_p3_cause`를 범위로 Grep을 1회 했다(glob `jp3_remedy_spec*.md`, 건수 모드). 출력은 최상위 명세·정오 8개 파일의 건수뿐이었다. ripgrep이 `j9_runs` 아래를 순회했을 수 있다(O7-13과 같은 종류).
16. 경로 2 넘김: 1-13(결정 14, 12a·12b 한정)과 1-20 1~2를 봉인 뒤·결과 전에 경로 2 [정의]로 더했다(재감사 N-B1, 결정 Q-1). 봉인본 11절 1019행 "조건 행 0 = 판정 불가"는 12a·12b에서 1-13·1-20을 따른다.
17. 1-19: 실행 1단계 전 건식 확인(r79 VBM·VBM0 각 1키, t8 1쌍)의 기록(판정에 쓰지 않음; 재감사 M-c).

## 정오 요약
| # | 항목 | 판단 | 봉인본 자리 |
|---|---|---|---|
| 1-1 | 12b 계획 = dg3 뒤·12b 앞, 스캔 = 06_analysis 전체 + 05_tests 둘 + c92·c93 키 목록 + 필수 루트 넷(79495405, 6bfb2560, b46bdf8f, 8a2a52ce) | 맞다. **run steps 변경 없음(C 재커밋 없음, P7-4 재실행 없음).** 12·13번째 단계는 T와 감사 뒤 | 6.4, Y7-7, 4절 5a |
| 1-2 | FIXED_INPUTS 목록 대신 단계별 sha 단언 | 맞다(조건 셋: c92·c93 sha 실행 전 확인, T 입력 단언, 판정서 인용). 판 7 데이터 입력 목록 = 1-2 표 | 판 6 정오 2 2-3 이어받음 |
| 1-3 | 12b 결정 파일 = `status`(`needs_b4`/`decided`)·`blocks`(b1·b2·b4 부분집합), sha 대조 | T 요구로 고정 | 5.2, 6.4 |
| 1-4 | 블라인드 파일 이름 14개 노출, 판 6 `selection.json`이 블라인드 이름을 담음 | 기록, 공개 O7-14 | 머리말 오염 보고, 12절 |
| 1-5 | 실행 worktree = ed7-impl(lock), T = 새 ed7-judge(C에서 분기) | 사용자 결정 기록. 실행 경로 모듈 목록 `05_tests/data/ed7_run_path_modules_8a2a52ce.json`(sha256 `e9c852e4…`, 155파일, 03_src 밖 Python 138) | 5.1·5.2 |
| 1-6 | LS 대 VB 표의 J7 = 6.1 새 비교 | 맞다(J7 집합 비교를 하는 곳 전부; 확인 단계는 J7 집합 비교 없음) | 6.1, 6.2 |
| 1-7 | P7-2 범위 | **고친다: E·F × {VBM, LSM1~4} 10줄**(판 6 정오 2 2-1 (iii)과 같음). A~D·X11은 P7-0으로 이어받음. **run steps 변경 없음.** P5-1형 33줄 재실행은 기록(관문 아님, 본 실행 전, C worktree·`j9_runs/8a2a52ce` 밖, 다르면 사용자 판단; 결정 16) | 5절 P7-2 |
| 1-8 | ③ 끔 태그 `final_C4G2_LAS_K1_LSB` | 맞다(T′ `60ebb4a4` `judge_t8` 1268~1317행이 VBM·VBM0 정체성 대조와 VBM0 실제 태그 기록, 다르면 `setting_defect`) | 6.1 |
| 1-9 | r79 줄 정체성 출처(T4h meta) | 맞다(T′ `l1ref` 1549~1582행이 L1 기준 4개 대조와 출처별 기록, 12a `bundle_problems`·12b `line_identity_problems`는 대조만; 12a·12b 출처별 기록 요구는 거둠(재감사 R-4). 12a 폴더·meta 통째 결측은 `not_judgeable`(R-3)) | 6.1 |
| 1-10 | `.done` 대조의 뜻 | 고친다: 단계 기록·폴더 소속 단언 + `selection_sha256` 대조 + 출력 sha 기록, 메인이 단계 끝마다 폴더 SUMS를 만들고 판정 직전 확인 | 1-2 조건 2 |
| 1-11 | j9_main J-P3 기대 행 200 | 맞다(다르면 `setting_defect`) | 6.2 |
| 1-12 | decide `--spec`(sha `10902ffd`) | 맞다 | 6.4, 1-2 |
| 1-13 | 조건 읽기 0 | **고친다**: j9_main·감도·확인·cases는 판정 불가 유지, 12a·12b는 조건 읽기를 더하되 0이면 그 항목만 '해당 없음(기록)'이고 rev 6 J-P3 판정은 그대로(결정 14). 경로 2 넘김에 [정의]로 더함(결정 Q-1) | 6.1, 6.5, **11절 1019행 "조건 행 0 = 판정 불가"(12a·12b는 1-13·1-20)** |
| 1-14 | P7-4 on C | 기록: pass(8695, 새 실패·핵심 미통과·새 건너뜀 0). P7-0·P7-6 통과. T는 P7-11 미통과 → T′ | 4절 5, P7-11 |
| 1-15 | O7-15(실데이터 시험의 `git ls-files --others` 5회) | 기록, 공개 | 머리말 오염 보고, 12절 |
| 1-16 | 감도 J-P3 판정 집합 | **고친다**: 판정 4설정 줄(기대 104), 기록 6설정 J-P3는 기록(결정 13). 사실 정정: 감사의 260은 실측과 다르고 T도 판정 행은 104였다(`j_p3_inputs.py` 250~256행) | 6.2 |
| 1-17 | probe 재현 불일치 | **고친다**: P7-3·P7-9 모두 `setting_defect`(결정 15) | 5절 P7-3·P7-9, 6.1 |
| 1-18 | 판정 `--out` 위치 | **고친다**: T′ worktree 밖·실행 단계 폴더 밖 | 5.2, 1-10 |
| 1-19 | T′ 시점, 근거 폴더 커밋·SUMS, 1단계 전 건식 확인 | 기록: T′·재감사는 실행 전, 근거 폴더는 정오 봉인 때 커밋·`postseal` SUMS. 실행 1단계 전 r79 VBM·VBM0 각 1키·t8 1쌍 건식 확인(기록, C worktree·`j9_runs\8a2a52ce` 밖; M-c) | 4절 5a |
| 1-20 | r79 줄 사건 시각 | **정의하지 않는다(나)**: 12a·12b ③ rev 7 조건은 늘 '해당 없음(기록)', r79 줄의 `t_event_s` 부재는 구조적 '사건 없음'(3.5 507행·6.1 659행을 r79 줄에 한해 좁힘), 배열 결측은 `setting_defect`. 도구 변경·T″ 없음. 1~2는 경로 2 넘김에 [정의]로 더함(결정 Q-1) | 3.5, 6.1, 6.5, **11절 1019행(12a·12b는 1-13·1-20)** |

## 경로 2에 넘길 정의 문장(재감사 N-B1, 사용자 결정 Q-1 2026-11-25)
- 쓰임: 메인이 판 7 경로 2 넘김 문서에 아래 [정의] 두 문장을 **그대로** 옮긴다. 봉인본 11절 1019행의 판 7 J-P3 정의 문장(상계 식 rev 6 그대로, 판정 집합 추가(3.5), 조건 행 0 = 판정 불가, 판정 플랜트 VBM 계열)에 덧붙이는 단서다. 두 경로는 이 정의로 같은 판정을 한다.
- 이 문장에는 경로 1의 코드 이름·파일:행·출력을 넣지 않았다(봉인본 11절 1018행 "경로 1 이름·출력은 넣지 않는다"). 넘김 전에 메인이 `handoff_leak.py`로 상대 경로 이름 누설과 공통 블록 sha를 본다.
- 넘김 때 `handoff_leak --shared`에는 436.9 원판 `jp3_remedy_spec.md`를 포함한다(확인 감사 지적).

> **[정의 E7-P2-1] T-JR-12a·T-JR-12b의 ③ rev 7 조건 읽기 0.** T-JR-12a(VBM 대 VBM0)와 T-JR-12b(VBKM 대 VBKM0)의 J-P3에는 ③ rev 7 조건(사건 시각 뒤 첫 PROBE 단계에서 `locked_ext` → `moving_ext` 전환을 가진 다리의 `carry_ext` 읽기)을 더한다. 대상 줄은 T-JR-12a에서는 VBM 쪽 줄 가운데 J-P3 판정 센서 등급(ideal·normal) 줄, T-JR-12b에서는 판 5 6.3.7 (4)의 J-P3 판정 쌍(기회 쌍과 VBKM0 READY 없는 쌍)의 VBKM 줄 가운데 판정 센서 등급 줄이다(conservative·old_worst 줄은 대상이 아니다). 조건 읽기에 침범(사용 상계 − 플랜트 로드측 진값 < −1 Pa)이 있으면 실패다. 판정 줄 전체에서 조건 읽기가 0이면 **그 조건 항목만 '해당 없음(기록)'**이고 판정 상태를 바꾸지 않는다. rev 6 판정 집합의 J-P3 판정은 그대로 한다(그 판정 행 0 = 판정 불가, 침범 = 실패). 이 예외는 T-JR-12a·T-JR-12b에만 쓴다. 그 밖의 판정(j9_main, 감도, 확인 단계, 사례 재생)에서 조건 읽기 0은 판정 불가(통과 아님)다.

> **[정의 E7-P2-2] r79 줄의 사건 시각.** T-JR-12a·T-JR-12b의 줄(r79 하네스: 연약 패드·바닥 이동·패드 형식·경사 조건이 시작부터 있는 하네스이고, 하네스가 분기해 넣는 플랜트 사건이 없다)에는 사건 시각 `t_event_s`가 없다. 이 부재는 입력 결함이 아니라 **사건 없음**이다. 사건 없음 = 그 줄의 ③ rev 7 조건 읽기 0으로 읽고, [정의 E7-P2-1]의 '해당 없음(기록)'에 넣는다. 봉인본 3.5·6.1의 "event 경로 줄에 사건 시각이 없으면 `setting_defect`"는 이 줄들에 쓰지 않는다. 대리 사건 시각(시작 시각, LEVEL 시작, 이륙 시각, 로드 압력 센서 고장 주입 시각 등)은 만들지 않는다. 다만 그 줄의 T4h 조건 배열(`t_s`, `phase`, `jp3_t_s`, `jp3_class`, `jp3_plant_state`, `jp3_p_tr_Pa`, `jp3_used_bound_Pa`)이나 T4h 파일이 없으면 `setting_defect`다. 이 줄에 `t_event_s`가 있으면 조건을 [정의 E7-P2-1]대로 정상 계산한다.
