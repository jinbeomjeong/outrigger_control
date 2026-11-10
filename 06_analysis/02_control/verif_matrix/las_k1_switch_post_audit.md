<!-- verif-protocol-auditor [시점] 전환 후 리포트 원문(2026-11-10, 대상 b0979d1). 메인 세션이 편집 없이 저장. 결정은 맨 끝 "메인 세션 덧붙임" 절에만 쓴다. -->

# K1 채택 전환 `[시점] 전환 후` 감사 보고 (verif-protocol-auditor, 2026-11-10)

## 감사 요약
- 의존성 점검: 모두 있음(numpy 2.5.3, pyyaml 6.0.3, git).
- 대상: 브랜치 `worktree-agent-a48e2e723452f1db0`, 커밋 `b0979d1`(기준 `15777d1`). worktree `C:\workspace\outrigger_control\.claude\worktrees\agent-a48e2e723452f1db0`에서 읽었다. 시점은 전환 후다. 바뀐 파일은 26개다(`git diff --stat 15777d1 b0979d1`).
- 기준 문서(봉인 일치는 seal_check로 확인):
  - `las_k1_rules_adopt.md` `864836d8`(9.1~9.5)
  - `las_k1_rules_adopt2.md` `fb3a5696`
  - `las_k1_rules.md` `2742c976`, rev1 `eeee4ab9`
  - `las_k1_rem_judgement.md` `4c509d15`(R7·R8 행, 알려진 한계 F2)
  - 증거 폴더 `C:\workspace\outrigger_control\.local_archive\session_9d4aec18_20261110\k1sw\`
- **판정: 차단 0 / 실행 전 수정 3 / 기록 11.** 병합해도 된다. 실행 전 수정 3건은 다음 단계(LAS-b P5r4+K1 재판정 규칙)의 본 실행 전에 처리해야 한다.
- 명세와 다르게 처리한 5곳의 판정(자세한 근거는 아래 발견 사항):

| # | 내용 | 판정 | 조용한 실패 | 두 번 적용 |
|---|---|---|---|---|
| ① | `--k1-order-gate` 기본 SUPPRESS, 기록은 늘 남김 | 허용 | 없음(단 `check-sources`는 제어기 동일성을 증명하지 못함, 기록 R-3) | 없음(`on`·`K1on` 멱등이 시험으로 고정됨) |
| ② | `--las-off`가 관문도 끔 | 허용 | 조합 `--las-off --k1-order-gate on`에서 ③ 태그가 집합 밖으로 나감(실행 전 수정 W-1) | 없음 |
| ③ | 옛 태그 전부 관문 False 점검 | 허용(명세보다 엄격하고 크게 실패함) | 없음 | — |
| ④ | G-5를 G-5a·G-5b로 대체 | 허용(명세 예시는 실행할 수 없음). 판별력이 얇다(기록 R-5) | — | — |
| ⑤ | ABL이 프리셋 관문 플래그 유지 | 허용(명세 9.2 표와 같음). R4가 꺼져 있어 관문이 작동하지 않는다(코드로 확인). 이를 고정하는 시험은 없다(기록 R-7) | 없음 | 없음 |

- 클래스 기본값은 꺼짐 그대로다: `c2.py:2203` `flat_soil_margin_order_gate: bool = False`. 프리셋 키워드만 `c2.py:2632`에서 `True`이고 `c2.py:2797`로 넘어간다.

## 발견 사항 (심각도순)

### [실행 전 수정][E·I] W-1. 접미사를 조합하면 `EXTEND_START_TAGS`에 없는 ③ 태그가 생기고, J-P3가 조용히 빠진다
- 근거
  - `v5_options.py:411-415`: `with_order_gate_tag`는 `_LAS`가 없어도 `_K1`을 붙인다.
  - `v5_options.py:432-440`: `with_switch_tags`는 LAS가 꺼지고 관문이 켜진 구성에 `final_C4G2_P3` → `final_C4G2_P3_K1`을 만든다.
  - `v5_options.py:46`: `EXTEND_START_TAGS`는 `(final_C4G2_P3, final_C4G2_P3_LAS, final_C4G2_P3_LAS_K1)` 셋뿐이다.
  - 이 집합을 쓰는 곳:
    - `v5_rerun.py:423` `if tag not in EXTEND_START_TAGS: return J_P3_NOT_APPLICABLE`
    - `j_p3_inputs.py:41`(`is_p3_expected`)
    - `chrono_t45_replay.py:833`(`is_p3_expected(run_controller_tag(...), None)`, setting 대체 없음)
    - `u3_reuse.py:235`
  - 이 조합에 닿는 경로:
    - `run_S9 level --las-off --k1-order-gate on` + v5 옵션. 이 조합은 `test_las_k1_chrono_rows.py::test_las_off_and_gate_compose`가 명시적으로 시험한다. 이때 `run_S9.py:5877`이 `final_C4G2_P3_K1`을 기록한다.
    - 하네스에서 `pre_las_preset_runner.py` + 토큰 `K1on`.
  - 이 두 태그는 `run_S9.CONTROLLER_EXPECTATIONS`에도 없다(`run_S9.py:1548-1556`).
- 실패 시나리오: "LAS-b 꺼짐 + K1 켬" 짝(LAS 단일 변수 짝을 K1 프리셋에서 만들 때 필요하다)을 VB로 돌린다. 그러면 그 행의 J-P3가 `not_applicable`이 되거나 `p3_expected` 거짓이 된다. 판정 집합에서 빠지고 오류도 나지 않는다. 명세 436.9.5 D-1·D-2와 같은 종류의 결함이다.
- 지금 영향: 저장 결과와 등록된 행 가운데 이 조합은 없다. 지금 결과는 맞다.
- 권장 조치(위임 필요: python-expert) — 둘 중 하나:
  - (a) ③ 판정을 태그 집합이 아니라 기준 태그로 한다. `_K1`·`_LAS`를 벗긴 기준 태그가 `final_C4G2_P3`인지 보는 `is_extend_start_tag(tag)`를 만들고 위 네 곳에 쓴다.
  - (b) `with_switch_tags`가 `_LAS` 없는 `_K1`을 만들지 않게 막는다(LAS 꺼짐 + 관문 켬이면 `ValueError`, 또는 run_S9에서 `--las-off --k1-order-gate on`이면 종료 2).
  - 어느 쪽이든 조합 4가지(LAS on/off × gate on/off) × ③ on/off를 매개변수 시험으로 고정한다.

### [실행 전 수정][R] W-2. 9.2가 요구한 "태그 소비자 전부 + 큰/조용한 실패 분류" 산출물이 없다
- 근거
  - `las_k1_rules_adopt.md:316` "태그 소비자 전부를 `git grep`으로 나열한다 … 큰 실패(즉시 오류)와 조용한 실패(선택 집합이 빔)로 나눈다".
  - `:346` 9.5는 감사가 그 표를 본다고 적는다.
  - 증거 폴더 `k1sw\`(파일 목록 확인)와 커밋 메시지(`commit_msg.txt`)에 그 표가 없다. 커밋 메시지에는 "Sealed judge tag constants unchanged" 한 줄만 있다.
- 실패 시나리오: 업데이트하지 않은 소비자가 다음 단계에서 쓰일 때, 크게 실패할지 조용히 빌지를 판단할 근거가 문서에 없다. W-1이 그 예다.
- 감사가 대신 만든 분류는 아래 "태그 소비자 표"에 있다. 판정서나 9.6 문서에 이 표(또는 구현 에이전트가 만든 표)를 붙인다(메인 세션, 필요하면 python-expert).

### [실행 전 수정][R·I] W-3. 다음 단계 재실행 행 생성기가 아직 `_LAS` 태그를 기대값으로 쓴다
- 근거
  - `d1_chrono_rows.py:101,160,164`(`sb.V5_P3_LAS_CONTROLLER`)
  - `v5_stage3_las_rows.py:108`
  - `las_chrono_rows.py:144`, `las_k1_chrono_rows.py:50`, `las_k1_rem_chrono_rows.py:43`
  - `s9_batch.py:377-378`의 새 상수 `V5_*_LAS_K1_CONTROLLER`는 정의만 있고 어디서도 쓰지 않는다(Grep 결과).
  - `u3_judge.py:70,72`·`u3_reuse.py:122`(`SETTING_TAGS_LAS`), `fb_judge.py:116`, `las_rev_judge.py:858-860`, `p3_hash_check.py:47`·`p3_chrono_check.py:72`도 그대로다.
- 실패 시나리오: 모두 **크게** 실패한다(조용히 비지 않는다). 예:
  - run_S9 `--expect-controller final_C4G2_P3_LAS`는 모델을 만들기 전에 종료한다(`run_S9.py:5857-5863`).
  - u3 G-2는 problems로 실패한다(`u3_judge.py:532-542`).
  - `las_rev_judge`는 "not in" 문제를 낸다(`:868-870`).
  - 다만 새 프리셋으로 재실행 묶음(D1 Chrono, stage3 LAS, U-3/U-6)을 띄우면 즉시 멈추거나 관문이 실패한다.
- 권장 조치: 다음 규칙(LAS-b P5r4+K1 재판정)에 쓸 묶음마다 "새 `_K1` 태그로 재실행"인지 "`pre_k1_preset_runner.py`로 재현"인지 정하고, 행 생성기에 반영한다(python-expert). 봉인된 판정 도구(`fb_judge`, `las_rev_judge`, `u3_judge` 등)의 상수는 고치지 않는다는 9.2 원칙을 지킨다. 그 판정을 새 태그 결과에 써야 하면 개정판이 필요하다(판정 에이전트).

### [기록][R] R-1. G-7 근거를 S-Ch 1행에서 REM R7·R8로 바꾼 것은 봉인 규칙에 적혀 있지 않다
- 근거
  - `las_k1_rules_adopt.md:342` G-7 = "S-Ch gateon 1행".
  - `las_k1_rules_adopt2.md:21,44`는 "adopt 9절 전환 절차를 그대로 쓴다"라고 해서 G-7을 바꾸지 않았다.
  - 대체는 호출 지시문의 메인 세션 결정이다.
- REM 근거 자체는 정체성을 갖췄다: `las_k1_rem_judgement.md:54-57`(threads 4, `OMP_WAIT_POLICY=PASSIVE`, 10행 `pcore`, 짝 같은 풀), `:9`, `:11`(F2 알려진 한계).
- 권장: decision_log와 9.6 문서에 "G-7 근거 = REM R7·R8(adopt2 판정), 메인 세션 결정 2026-11-10"을 적는다(메인 세션).

### [기록][I·R] R-2. 전환 뒤에는 gate-on 진단 행(S-Ch gateon, REM R7·R8·F1·F2)을 어떤 키워드 러너로도 재현할 수 없다
- 근거
  - `run_S9.py:1552-1553`: `final_C4G2_P3_LAS`는 관문 False를 점검한다.
  - `run_S9.py:3910-3915`: `--k1-order-gate on`이 관문을 True로 만든 뒤 기대값을 점검한다(`:5857`).
  - 이 결과는 시험으로 고정됐다: `test_las_k1_rem_chrono_rows.py` `GATE_ON_KEYS`, `check-sources` 종료 1. `test_las_k1_chrono_rows.py::test_argv_check_ok_and_check_sources`.
  - `pre_k1_preset_runner.py:6-8` docstring은 "reproduces the LAS-b results before the switch (tags `final_C4G2_LAS` / `final_C4G2_P3_LAS` …)"라고 적는다. 관문 꺼짐 행에만 맞는 말이다.
- 9.2 문구 "전환 전 재현 러너로만 돌린다"도 gate-on 행에는 맞지 않는다. 크게 실패하므로 결론이 틀릴 위험은 없다.
- 권장: 러너 docstring과 9.6 문서에 "gate-on 진단 행의 재현 = 그 결과의 `git_at_start` checkout만"을 적는다(python-expert 문구, 메인 세션 문서).

### [기록][I] R-3. ① SUPPRESS의 "args 비교 보존"은 제어기가 같다는 증명이 아니다
- 근거
  - `run_S9.py:1920` `SOURCE_ARGS_IGNORE`에 `expect_controller`·`las_off`가 들어 있다.
  - `source_args_check`(`:1925-1953`)는 args만 비교한다. 그래서 전환 전 저장 결과(속성 없음 = 관문 꺼짐)와 전환 뒤 행(속성 없음 = 관문 켬)이 `check-sources ok`로 나온다.
  - 실행 때 막는 것은 `--expect-controller` 옛 태그의 크게 실패다(③). `--expect-controller`가 없는 행(FINAL-R S8C/S6C, `s9_batch.py:941`)은 새 프리셋으로 돈다. 다만 이들은 강체 지면이라 토양 LOC가 없어 R4·관문이 작동하지 않는다고 본다([추정], `c2.py:8768-8772`의 R4 조건 "soil mode used").
  - `--resume`의 HEAD 변경은 경고만 낸다(`s9_batch.py:1343-1363`). 이 동작은 전환 전부터 있었다.
- 좋은 점: `c2_setup.k1_order_gate`(요청)·`k1_order_gate_effective`가 모든 실행에 남는다(`run_S9.py:3916-3917`). 명시 요청은 만든 제어기에서 다시 확인한다(`:5939-5943`).
- 참고: `effective`는 `level_c2_config_of_args` 시점의 config 값이다. 최종 제어기 값은 `controller_meta.slope_clearance_margin.settings`가 원본이다.

### [기록][E] R-4. ② `--las-off`의 뜻이 "LAS-b와 K1 둘 다 꺼짐"으로 바뀌었다
- 근거: `run_S9.py:3774,3788`, `run_S8C.py:1389-1406`. 명세 9.1~9.3에는 `--las-off`에 대한 언급이 없다.
- 옛 태그(`final_C4G2`·`_P3`)를 재현하려면 ③ 때문에 관문 꺼짐이 꼭 필요하다. 그래서 이 처리는 맞다.
- 다만 "LAS-b 실행의 LAS-off 짝"을 K1 프리셋에서 만들면 두 변수가 함께 바뀐다. 단일 변수 짝은 `--las-off --k1-order-gate on`이어야 하는데, 이 조합이 W-1에 걸린다.
- 문서(9.6)에 이 뜻의 변화를 적는다.

### [기록][C·R] R-5. G-3~G-5 재집계: 건수·해시는 모두 맞지만, 관문이 실제로 결과를 바꾼 줄이 적다
- 독립 재집계(아래 재집계 표). 저장 원본(main checkout `06_analysis/03_hydraulic/coupled/v5/las/k1/k1_Y*.jsonl`, `v5/d1.jsonl`, `v5/las/revA2/revA_RP0.jsonl`)과 키로 이었다.
- 관문이 실제로 막은 줄(`k1.would_block_any`)
  - G-3: 457줄 중 8줄. 이 8줄이 "래퍼 토큰 K1 = 프리셋 구현"의 실질 근거다.
  - G-4: 70줄 중 1줄.
  - G-5a·G-5b: 그림자 근거가 없다(g6.txt shadow 0). 러너가 관문을 껐다는 근거는 각 줄의 `preset_gate: false` 필드(작업자 프로세스에서 `C2Config().with_10hz_d1()`로 다시 잼, `replay_k1.py:94`)뿐이다.
- `pre_k1_preset_runner.py`를 직접 시험하는 단위 시험은 없다(Grep: `05_tests` 안에 참조 없음). `pre_c4g2`·`pre_switch` 러너는 기존 subprocess 해시 시험에서 쓰지만, 그 시험에 관문이 작동하는 장면이 있는지는 확인하지 못했다([추정]).
- G-3 `gate` 필드는 실행 뒤 따로 만든 제어기 값이다(`replay_k1.py:89-91`). 실행한 제어기의 값이 아니다.
- 권장: `pre_k1_preset_runner` import 뒤 `with_10hz_d1().slope_clearance_margin.flat_soil_margin_order_gate is False`를 단정하는 subprocess 단위 시험을 더한다. 기존 세 러너에도 같은 단정을 더한다(python-expert).

### [기록][T] R-6. 커밋 메시지가 G-5 재현을 주장한 시각이 G-5a 2부가 끝나기 전이다
- 근거
  - 커밋 `b0979d1` 시각 2026-11-10T10:50:42+09:00(`git log`).
  - `g5a_part2.jsonl`·`.log`는 10:34:16 생성, 10:51:14 마지막 쓰기(149줄). `commit_msg.txt` 마지막 쓰기 10:50:42.
  - 커밋 메시지: "G-3 / G-4 / G-5 replays reproduce the stored command hashes".
- 결과는 149/149 SAME이라 결론은 그대로다. 코드도 같다: 바뀐 파일의 마지막 mtime 09:59:09는 G-5a 2부 시작보다 앞이다.
- G-5a는 1부 40줄(중단) + 2부 149줄(`REPLAY_DONE` 이어 돌리기)로 나뉘었다. 합 189줄, 키 189개가 모두 다르고, 선택이 `r4+20`과 같은 것을 확인했다.
- 판정서·decision_log에 G-5 완료 시각(10:51:14)을 적는다(메인 세션).

### [기록][E] R-7. ⑤ ABL에서 명령이 바뀌지 않는다는 것은 코드상 참이지만 시험으로 고정되지 않았다
- 근거
  - `b5_baseline_compare.py:361-364`: `flat_soil_margin_m=0.0`에 관문 플래그를 그대로 넘긴다.
  - `c2.py:8768-8769`: `flat_soil_margin_m <= 0`이면 R4 미대상이다. `:8784-8792`: 관문 판단은 R4 대상일 때만 한다. `:8815-8816`: decision도 남기지 않는다.
  - 메타는 바뀐다(`settings.flat_soil_margin_order_gate` True, `order_gate.enabled` True, `c2.py:8858,8868`). 태그는 `ABL_LAS_K1`이다(`test_v5_switch_tags.py:105`).
  - `test_b5*.py`에 `order_gate`·`ABL_LAS_K1` 참조가 없다.
- 권장: ABL 구성의 관문 on/off 명령 해시가 같음을 단정하는 시험을 더한다(python-expert).

### [기록][R] R-8. G-2(클래스 기본 해시)는 따로 보고되지 않았다. 구조상 성립한다
- 근거: `c2.py` diff는 docstring, `with_10hz_d1` 키워드 추가(`:2632`), 넘김(`:2797`)뿐이다. 클래스 기본값(`:2203`)은 그대로다. `test_c2_k1.py`는 `C2Config()`의 관문이 False임을 단정한다. G-1이 기존 클래스 기본 해시 시험을 포함해 통과했다(6298 통과·실패 0).
- 판정서 G 표에 "G-2: 별도 실행 없음, diff상 C2Config() 무변경 + G-1"로 적는다.

### [기록][R] R-9. G-6 영향 표에 9.4가 요구한 문구와 첨부가 아직 없다
- 근거: `las_k1_rules_adopt.md:341` "근거 없는 집합은 '재실행 필요 시 새 태그로'라고 적는다", "판정서에 붙인다".
  - `k1sw\g6.txt`에는 숫자만 있다. 하네스 30개 묶음 중 그림자 근거가 있는 것은 `las/k1/k1_Y*.jsonl` 넷뿐이고, K1off에서 바뀔 행은 `k1_Y0` 8행이다. Chrono는 `V5-LAS-K1-CHRONO` 1행만 해당한다.
  - 나머지 집합은 그림자 근거가 없다.
- 9.6 문서 단계에서 그 문구와 함께 붙인다(메인 세션).

### [기록][S] R-10. 줄바꿈 보호
- 규칙 4판과 `.sha256` 4개는 모두 `-text`, i/lf·w/lf, CRLF 0, BOM 없음이다(seal_check). `.gitattributes:31`(`las_k1_rules*`), `:36`(`las_k1_rem_judgement.md`), `:27`(`verif_matrix/scripts/*`).
- `las_k1_adopt_judgement.md`·`las_k1_judgement.md`·`las_k1_sch_judgement.md`는 보호되지 않고(`attr/` 빈칸) 작업 트리가 CRLF다(`core.autocrlf=true`). 다만 그 해시(raw `744bf87e`, LF `3b98dbd0`)를 인용한 곳은 `06_analysis`·`00_docs`·`04_scripts`에 없다(`git grep` 결과 없음). 지금은 봉인과 무관하다.
- 이 커밋의 새 파일(`pre_k1_preset_runner.py`, `test_v5_switch_tags.py`)은 해시로 인용되지 않아 보호가 필요 없다. 기존 세 러너도 보호하지 않는 관례와 같다.
- 판정서 해시를 나중 규칙이 인용하게 되면 그때 `-text`를 더한다.

### [기록][I] R-11. 재생 경로는 그 기록 자신의 설정으로 관문을 다시 만든다. 하네스 T4h만 태그 기준이다
- `chrono_t45_replay.py:907-917`: 기록의 `controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate`를 먼저 보고, 다음으로 태그와 `expect_controller`의 `_K1`을 본다. S-Ch·REM gateon 결과(옛 태그 + 관문 켬)도 켬으로 재생한다. 맞는 처리다.
- `t4h_replay.py:117-120`은 태그의 `_K1`만 본다. 그래서 래퍼 토큰 `K1on`으로 돈 하네스 줄(태그 `_LAS`)은 꺼짐으로 재생된다. 다만 이 재생은 두 압력 모니터만 다시 돌리므로 관문이 결과에 영향을 주지 않는다([추정]: 모니터가 `slope_clearance_margin`을 읽지 않는다는 것은 코드를 따라가 확인하지 않았다).

## 규칙↔도구 대조표

| 규칙 원문 | 구현 | 결과 |
|---|---|---|
| 9.1 `with_10hz_d1(…, flat_soil_margin_order_gate=True)`, 설정으로 넘김 (`adopt.md:298`) | `c2.py:2632`, `:2797` | 같음 |
| 9.1 클래스 기본 False 유지 (`:299`) | `c2.py:2203`, `test_c2_k1.py` | 같음 |
| 9.1 run_S9 기본 `preset`, `off`/`on` 명시만 덮음, 요청·effective 기록 (`:300`) | `run_S9.py:3792-3823`, `:3910-3917`, `:6363-6369`(SUPPRESS) | 뜻은 같음(①) |
| 9.1 하네스 토큰 없음 = 프리셋, `K1`과 프리셋이 겹칠 때 멱등을 시험으로 고정 (`:301`) | `test_k1.py:554-567`, `test_las_k1_chrono_rows.py::test_on_keeps_the_preset_bits_and_records_it` | 같음 |
| 9.2 태그 3종 (`:305-309`) | `v5_options.py:38-45`, `run_S9.py:1522-1529`, `s9_batch.py:377-378` | 같음 |
| 9.2 `ORDER_GATE_TAG_SUFFIX`, `controller_tag`가 관문 켬일 때 붙임 (`:311`) | `v5_options.py:38`, `:442-452` | 같음. 조합 밖 태그가 생기는 문제는 W-1 |
| 9.2 `EXTEND_START_TAGS`에 `_P3_LAS_K1` 추가 (`:312`) | `v5_options.py:46-48` | 같음 |
| 9.2 `is_liftoff_slow_tag`·`with_liftoff_slow_tag` 조용한 실패 수정 (`:314-315`) | `v5_options.py:399-424`, `test_v5_switch_tags.py:45-73` | 같음 |
| 9.2 태그 소비자 표(큰/조용한 실패) (`:316-322`) | 산출물 없음 | **W-2** |
| 9.2 봉인 판정 도구 상수는 고치지 않음 (`:323`) | `las_k1_sch_judge.py:144`, `las_k1_rem_judge.py:92-93`, `las_k1_adopt_judge.py:78` 모두 diff 밖 | 같음 |
| 9.2 새 태그 = 관문 True, 옛 `_LAS` = False (`:324`) | `run_S9.py:1543-1556`(옛 태그 5개 모두 False, ③) | 같음, 명세보다 엄격 |
| 9.3 `pre_k1_preset_runner.py` 같은 꼴(스레드 env 선설정, import 때 패치) (`:328`) | 새 파일 `:31-35`, `:44-63` | 같음. docstring 과장은 R-2 |
| 9.3 기존 세 러너도 관문 False (`:329`) | 세 러너 diff | 같음 |
| 9.4 G-1~G-7 (`:334-342`) | 증거 폴더 | 아래 재집계 표. G-2 R-8, G-5 ④, G-6 R-9, G-7 R-1 |
| 9.5 `-text` (`:346`) | seal_check | 규칙·봉인 보호됨(R-10) |

## 태그 소비자 표 (감사가 만든 분류, W-2 대체 근거)

| 소비자 (path:line) | 비교 방식 | 새 태그 `_LAS_K1`일 때 | 분류 |
|---|---|---|---|
| `v5_options.is_liftoff_slow_tag` `:418-424` | 접미사 분리 | 참 | 고침 |
| `v5_options.with_liftoff_slow_tag` `:399-408` | 접미사 분리 | `_LAS` 두 번 안 붙음 | 고침 |
| `EXTEND_START_TAGS` `:46` → `j_p3_inputs:41`, `v5_rerun:423`, `u3_reuse:235`, `chrono_t45_replay:833` | 집합 | `_P3_LAS_K1` 포함 | 고침. 단 `_P3_K1`은 조용한 실패(W-1) |
| `run_S9.CONTROLLER_EXPECTATIONS` `:1548-1556` | dict | 새 두 태그 있음 | 고침 |
| `run_S9.CONTROLLER_ABSENT_OR_OFF` `:1568-1569` | dict | 새 두 태그 있음 | 고침 |
| `t4h_replay:117-120`, `chrono_t45_replay:907-917` | `endswith("_K1")` + 메타 | 관문 재구성 | 고침(R-11) |
| `v5_rerun.controller_tag:386`, `verdict_runs:208-217,593,602`, `run_S8C:1560`, `run_S9:5877`, `r79_sensor_screen:1012` | `with_switch_tags`(config) | `_LAS_K1` | 고침 |
| `run_S8C:1539-1540`, `run_v5:286`, `v5_rerun:532` | config 없이 `controller_tag(options)` | 전환 전 태그. 뒤에서 덮어쓰거나 정의용 | 전환 전부터 같은 설계(T4h는 `verdict_runs`가 덮음, `test_v5_setting_records.py:235` 확인) |
| `d1_chrono_rows:101,160,164`, `v5_stage3_las_rows:108`, `las_chrono_rows:75,144`, `las_k1_chrono_rows:50`, `las_k1_rem_chrono_rows:43` | `--expect-controller` 옛 태그 | 실행 시 종료 | 크게 실패(W-3) |
| `u3_judge:70,72`, `u3_reuse:122` | `==` | problems / Q-6 | 크게 실패(W-3) |
| `fb_judge:116,826-832` | `==` | others에 나열 | 크게 실패(봉인 도구) |
| `las_rev_judge:858-872` | `in`/`==` | "not in" 문제 | 크게 실패(봉인 도구) |
| `p3_hash_check:47,161`, `p3_chrono_check:72,205` | `==` `final_C4G2_P3` | 실패 | LAS 전환 때부터 크게 실패(변화 없음) |
| `las_k1_sch_judge:144,893`, `las_k1_rem_judge:92-93`, `las_k1_adopt_judge:78`, `k1rem_twopath/recount_rem.py:46-47` | `==` | 옛 결과 전용 | 봉인 도구. 고치지 않는 것이 맞음 |

## 재집계 표

| 항목 | 구현 보고 | 재집계 | 차이 | 판단 |
|---|---|---|---|---|
| G-1 단위 | 6298 통과·실패 0 | `g1b_sum.txt`: passed 6298, skipped 8. 12샤드 모두 종료 0(`g1b_driver.log`). 실행 시작(약 10:34)은 마지막 소스 수정(09:59:09)보다 뒤 | 0 | 일치 |
| G-1 coupled | 437 | `coupled.log` 437 passed, 4 skipped | 0 | 일치 |
| G-3 건수·해시 | 457/457 | 457줄. 하위 묶음 Y-Pa 165·Y-Pb 40·Y-Sa 30·Y-Sb 30·Y-T 192(규칙 `:338`과 같음). 모두 K1on, 저장 원본과 키로 이은 해시 같음 457, error 0, `preset_gate` True 457, 태그 `_LAS_K1` 210 / `_P3_LAS_K1` 247 | 0 | 일치. 관문이 막은 줄 8(R-5) |
| G-4 건수·해시 | 70/70 | 70줄(Y-0c 30 + Y-0d 40, 규칙 `:339`). 모두 K1off, 해시 같음 70, `preset_gate` False 70, 태그 `_LAS` 25 / `_P3_LAS` 45 | 0 | 일치. 관문이 막은 줄 1 |
| G-5a | 189/189 | `d1.jsonl` 868줄 중 R4 적용 169 + 비R4 앞 20 = 189 = 선택 집합. 저장 해시와 원본 같음 189, 재생 같음 189, `preset_gate` False 189 | 0 | 일치(1부 40 + 2부 149, R-6) |
| G-5b | 21/21 | `revA_RP0.jsonl` 149줄 중 R4 적용 1 + 비R4 20 = 21 = 선택 집합. 같음 21, `preset_gate` False 21 | 0 | 일치 |
| 봉인 | — | 규칙 4판 raw 일치(seal_check findings 0) | — | 일치 |

## 확인 필요
1. W-1의 고침 방향: (a) 기준 태그로 ③을 판단 / (b) `_LAS` 없는 `_K1` 조합을 막음. 어느 쪽이 의도인지 정한다(사용자 또는 control-expert). "LAS-b 꺼짐 + K1 켬" 짝이 앞으로 쓸 실험 설계인지에 따라 다르다.
2. G-7 근거 대체(R-1)를 개정판으로 봉인할지, decision_log 기재로 충분한지(메인 세션).
3. 다음 규칙(LAS-b P5r4+K1)에서 쓸 묶음마다 "새 태그 재실행" 또는 "pre_k1 재현"을 정한다(W-3, 판정 에이전트).

## 위임 필요
- **python-expert**
  - W-1: `v5_options.py:411-452`(조합 밖 태그). `v5_rerun.py:423`, `j_p3_inputs.py:41`, `chrono_t45_replay.py:833`, `u3_reuse.py:235`의 ③ 판단을 기준 태그 기반으로 바꾸거나 조합을 금지한다. 4×2 조합 매개변수 시험을 더한다.
  - W-3: 다음 단계에 쓸 행 생성기에 `s9_batch.V5_*_LAS_K1_CONTROLLER`를 연결한다(결정 뒤).
  - R-2: `pre_k1_preset_runner.py:6-8` docstring을 "관문 꺼짐 `_LAS` 결과만, gate-on 진단 행은 `git_at_start` checkout"으로 고친다.
  - R-5: 네 러너가 관문 False를 만든다는 subprocess 단위 시험을 더한다.
  - R-7: ABL 관문 on/off 명령 해시가 같다는 시험을 더한다.
- **메인 세션**: W-2 표 첨부, R-1·R-6·R-8·R-9의 판정서·decision_log 기재, 9.6 문서에 R-4(`--las-off` 뜻) 기재.
- tools/verif 후보(python-expert): "저장 원본과 키로 이어 재생 jsonl의 선택 규칙(`r4+N`)·해시·판별 줄 수(would_block)를 세는 검사". 입력은 재생 jsonl + 원본 jsonl + 키 함수 + 선택 규칙이고, 출력은 선택 일치·해시 일치·판별 줄 수이며, 종료 1은 불일치다. 이번에 즉석 스크립트 2개로 했다.

## 메인 세션 권고
- W-1을 고친 뒤 `pytest 05_tests/unit/test_v5_switch_tags.py 05_tests/unit/test_v5_rerun.py 05_tests/unit/test_las_k1_chrono_rows.py`와 coupled 시험을 다시 돌린다(PowerShell 도구).
- 다음 단계 본 실행 전에 그 묶음의 `s9_batch check-sources`(결과를 쓰지 않음)를 돌리고, 행마다 `--expect-controller` 태그가 `_K1`인지 본다.

## 검사하지 못한 것
- G-1 단위 시험을 다시 실행하지 않았다(시뮬레이션·하네스 본 실행 금지). 증거 파일로만 확인했다.
- `t4h_replay`가 쓰는 두 압력 모니터가 `slope_clearance_margin`을 읽지 않는지 코드를 끝까지 따라가지 않았다(R-11 [추정]).
- 강체 지면(S8C/S6C FINAL-R) 행에서 R4·관문이 작동하지 않는다는 것은 R4 조건 코드로만 판단했다(R-3 [추정]).
- 구현 에이전트의 증거 입력 사본(`…\9d4aec18…\scratchpad\k1sw\stored\`)은 이미 지워져 해시를 대조하지 못했다. 대신 재생 기록의 `stored_hash`가 main checkout 원본과 모두 같음을 키로 이어 확인했다(G-3 457, G-4 70, G-5a 189, G-5b 21).
- `pre_c4g2`·`pre_switch` 러너를 쓰는 subprocess 해시 시험에 관문이 작동하는 장면이 있는지 확인하지 않았다.
- 프로젝트 모듈을 import하는 동적 확인(W-1 태그 생성)은 하지 않았다. 지시문에 프로젝트 env가 없어서 코드 읽기로 확정했다(`v5_options.py:411-415`, `:432-440`, `:46`).

## 실행한 검증
- 인터프리터: `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`MKL_THREADING_LAYER=TBB`, 필요하면 `-X utf8`). 모두 PowerShell 도구로 실행했다. 프로젝트 모듈은 import하지 않았다.
- `depcheck.ps1`(CHECKED)
- `source_guard.py snapshot/verify`(입력 11개)
- `seal_check.py las_k1_rules.md las_k1_rules_adopt.md las_k1_rules_adopt2.md`(findings 0)
- `gate_scan.py v5_options.py pre_k1_preset_runner.py`(findings 0)
- `record_check.py recount`를 시도했으나 `--no-git` 인자 오류(종료 2, 감사자 사용 오류)로 쓰지 못하고 즉석 스크립트로 대신했다.
- git 조회: `git diff --stat/diff 15777d1 b0979d1`, `git log`, `git check-attr text`, `git ls-files --eol`, `git config core.autocrlf`, `git grep`
- `Get-FileHash`(판정서·원본 jsonl)
- 즉석 스크립트(scratchpad `k1_post_audit\`에 쓰고 실행 뒤 폴더째 지움)
  - `disc.py`: G-3·G-4와 저장 K1 원본을 키로 잇고, 후보·would_block·해시를 셈
  - `g5join.py`: G-5a·G-5b와 `d1.jsonl`·`revA_RP0.jsonl`을 잇고, `r4+20` 선택 일치·해시를 셈
- 지운 파일: `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\k1_post_audit\`(guard.json, disc.py, g5join.py 포함 전체). 남은 부산물 없음. worktree `git status` 깨끗함, HEAD `b0979d1`.
- 최종 판정 전에 근거 줄(`v5_options.py:46,411,415,432`)을 Grep으로 다시 확인했다. 감사 중 바뀐 파일은 없다(source_guard).
- 메모리: `C:\Users\jinbeom\.claude\agent-memory\verif-protocol-auditor\audit_pitfalls.md`에 일반 함정 3줄(조합 접미사 태그가 집합 밖으로 나감, 옛 태그가 새 플래그를 꺼짐으로 고정, 재생이 끝나기 전의 커밋 주장)을 더하고 `MEMORY.md` 색인을 갱신했다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha las_k1_rules_adopt.md 864836d8…, las_k1_rules_adopt.sha256 fddf01a3…, las_k1_rules_adopt2.md fb3a5696…, las_k1_rules_adopt2.sha256 eb9c1417…, las_k1_rem_judgement.md 4c509d15…, las_k1_rules.md 2742c976…, las_k1_rules.sha256 7811ccf3…, .gitattributes dabe2202…, c2.py 4febaf35…, v5_options.py cd122b8c…, run_S9.py 64372ca5…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음

---

## 메인 세션 덧붙임 (2026-11-10)

- 병합: 차단 0이므로 master에 병합(b53d890).
- 사용자 결정
  - W-1: (a) 기준 태그로 ③ 판단. 조합 4×2 매개변수 시험으로 고정.
  - R-1(G-7 근거): adopt 개정판(addendum)을 봉인하고 감사를 다시 받는다.
  - 무결성 Medium(`las_targeted._turn_preset_las_off`): 관문도 함께 끈다(gate=False 되돌림), 해시 재현 시험으로 확인.
