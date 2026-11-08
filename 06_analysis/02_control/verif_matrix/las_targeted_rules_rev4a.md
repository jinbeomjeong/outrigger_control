# LAS-b 표적·채택 규칙 덧붙임 판 4a (정정: G6-2 항목 이름, 기준 항목이 없는 행, 멈춤 귀속, dg3 off 재현, H-7′ 필드 대응)

작성: control-expert, 2026-11-08.

> **상태: 봉인(2026-11-08).** SHA-256과 봉인 시각은 같은 폴더 `las_targeted_rules_rev4a.sha256`에 있다. 이 파일은 더 고치지 않는다.
> - **고치는 판**: 원판(`00b48fd8…`), 판 1(`0d5f59f8…`), 판 2(`6be736cb…`), 판 3 `las_targeted_rules_rev3.md`(`956f65c74e36eb8fe921dc6399b0d5f2f04099b7852380362351f658c9791cd1`)와 키 목록(`3602438d047b6a35829bda013921972411d10b0906153eba8bdc9760e7888553`), 판 4 `las_targeted_rules_rev4.md`(`05fbde22009c10b74ddf0df071452a99631bb319c2f482df83be59adfad1de6d`). 여기 적지 않은 항목은 그대로다.
> - **결과를 보기 전의 정정이다.**
>   - T-3과 재개 검증의 LAS-b 실행 결과는 0줄이다.
>   - 본 것은 다음뿐이다.
>     - python-expert 구현 검토 질문 4건(worktree `agent-a3f0479104b4556fe`, 커밋 `12f9837`, 병합 전). 실행 결과는 들어 있지 않다.
>     - 그 worktree의 `las_h7.py`
>     - 저장 기준 기록의 필드 이름: `v5/d1.jsonl` 항목 이름, r79 `events`, `v5_rerun/u3_slope_V0.json` `records`, `paper_runs/d1_scm/d1s_judge.json`
> - 판정 문턱·대상 수(T-3 315건)·멈춤 처리의 뜻은 바꾸지 않는다.

## 1. G6-2 항목 이름 (판 3 K-6b, 판 3 2.1 표, 판 4 2절 C4′·3절 J-1)

- 저장 D-1 줄의 G6-2 항목 이름은 **`G6-2_loc`**다(`d1.items["G6-2_loc"]`). `v5/d1.jsonl` 868줄 어디에도 `G6-2` 키는 없다.
  - 원판 C4와 `las_judge.py`의 `G62_ITEM = "G6-2_loc"`도 이 이름이다.
  - 판 3·판 4에 "G6-2" 또는 `d1.items["G6-2"]`로 적은 곳은 모두 `G6-2_loc`로 읽는다.
- 판 3 키 목록 `las_targeted_rules_rev3_keys.json`의 항목별 `"G6-2"` 필드는 **무효**다.
  - 생성기가 `items.get("G6-2")`를 읽어 228 + 76건 전부 None이 되었다. 실제 `G6-2_loc`는 T-3c 76건 모두 참이다.
  - 판 3 2.1 표의 "G6-2 = 참 76/76"은 `G6-2_loc` 기준으로 맞는 문장이다.
  - 키 목록은 키 집합과 개수의 원본으로 계속 쓴다.
- **K-6 기준값의 원본은 `v5/d1.jsonl`**(sha256 `9039b36a1a9c4ba5ed63528bb7384773018d4c7377dccbf76b18fbcfda86707f`)이다. 판 3 K-6b의 "d1.items"가 바로 이것이다.
- 키 목록의 나머지 기준 필드(`verdict`, `fail_items`, `P3-2`, `t_ready_s`, `stroke_max_m`, `fault_names`, `commands_sha256`)는 판정 시작 때 `d1.jsonl` 값과 같은지 대조한다. 하나라도 다르면 H-T3-3(도구·입력 결함)으로 멈춘다.

## 2. 기준 행에 항목이 없을 때

- G6-2(`G6-2_loc`)나 P3-2 항목이 **기준 행에 없으면** 그 기준은 그 행에 해당하지 않는다. 판 3 K-6b와 판 4 C4′·P3-2 모두 같다.
  - 예: steady 행에는 G6-2가 없고, G6 행에는 P3-2가 없다.
  - 줄마다 "기준 항목 없음"으로 기록한다.
  - 판 4 2절 P3-2의 "기준에서 P3-2가 실패가 아닌데"는 **항목이 있고 실패가 아닌 경우**로 읽는다. 항목이 없는 경우는 여기에 들지 않는다.
- 기준 행에 항목이 있고 참(실패 아님)인데 새 값이 없으면(None) 위반이다. 판 3 K-6b의 "거짓이 되지 않는다"도 이 엄격한 뜻으로 읽는다. T-3 K-6과 H-7′는 같은 함수(`las_h7.h7_violations`)로 판정한다.

## 3. T-3 멈춤의 귀속 (판 3 K-4·K-5, H-T3-4·H-T3-5)

| 경우 | 멈춤 |
|---|---|
| G1 균일 행(T-3a G1 72, T-3b 4)에서 LAS-b가 **작동**했다 | H-T3-4(사용자 기준 "G1 해시 불변" 위반, 묻는다) |
| 어느 T-3 행이든 **미작동**인데 해시가 기준과 다르다(G1·dg3 포함) | H-T3-5(구현·재현 결함, python-expert 진단) |

판 3 K-4는 "작동 0"과 "해시 같음"을 함께 요구한다. 해시만 다른 경우는 K-5와 같은 원인 분류로 본다.

## 4. dg3 off 폴더 재현 (T-3b, R-0)

- 저장 off 기록은 ③이 없던 코드(`d1ec93f`)에서 만들었다. 지금 HEAD의 VB 정의에는 ③가 들어 있다.
- off 기록을 다시 만들려고, off 폴더 작업에서만 프로세스 안에서 VB의 ③ 옵션을 빼는 방식(`las_t3_dg3.py`)을 **승인한다.** 조건은 다음과 같다.
  1. 작업마다 새 프로세스로 돈다(spawn, `maxtasksperchild=1`). off·v4_on 작업이 한 프로세스에 섞이지 않는다.
  2. 줄마다 실제 쓴 수압 옵션과 제어기 설정 전체를 기록한다. 이 값을 저장 기록의 `hydraulic_options`·`controller_settings`와 대조한다. LAS-b 블록과 실행 정체성 필드만 빼고 같아야 하며, 다르면 H-T3-3이다.
  3. ③ 규칙은 off 폴더가 `constant`, v4_on 폴더가 `tracked_bound`(저장 `preset_settings["two_pressure.extend_start_rule"]`와 같음)이어야 한다. 이것을 K-3에서 본다.
  4. R-0 dg3 off 기록(`…|48|ref|G1|top|Fs0`)이 LAS 끔에서 저장 해시와 같아야 T-3b를 시작한다(판 3 H-T3-1).
  5. 나머지 off 기록(`…|s2|ref|14|G1|B|0,0`)이 미작동인데 해시가 다르면 3절대로 H-T3-5다.

## 5. H-7′ 필드 대응 (판 4 3절; `las_h7.py` 확인 결과)

| 묶음 | 상태 | 확정 내용 |
|---|---|---|
| J-1 D-1 | **확정** | `d1.verdict`, `d1.fail_items`, `event_names`(개수 사전), `d1.items["G6-2_loc"]`, `d1.items["P3-2"]`(참 = 실패 아님), `d1.t_ready_s`, `d1.stroke_max_m` [m] |
| J-10·J-11·J-12 r72 | **확정** | 판정 = `base.pass`. 실패 항목 = `base.gates`의 거짓 문. 작동·FAULT = `events`(시각·이름 쌍). G6-2 = `base.gates["G6-2_loc"]`. P3-2 = `base.late_loc_reapproach.verdict`(`fail`만 실패). READY = `base.t_ready_s`. 행정 = `r79.max_true_stroke_mm`/1000. 조건: 새 줄과 기준 줄의 `events`가 잘리지 않은 전체 목록이어야 한다. 도구는 잘림 표시(개수 상한·`incomplete`)가 있으면 그 줄을 판정 불가로 두고 멈춘다 |
| J-9 U-9 V0, J-13 main·pressure_only | **확정(조건부)** | READY = `values.times.t_first_ready_s`. G6-2·P3-2·행정은 형식 없음. 판정·실패 항목은 `judged.verdict`·`judged.fail_items`인데, 이 값은 그 묶음의 봉인 판정기(J-9 `u9_targeted_rules_rev1`, J-13 `v5_criteria` 최신 개정)가 써야 한다. 줄에 판정기 이름·버전·해시를 남긴다. `judged`가 없으면 C2 "판정 없음" 위반이다(조용한 통과 금지) |
| J-3′ D-1 Chrono SCM | **대응 지정, 존재 확인 뒤 확정** | `d1s_judge.json` `cases.<id>`: 판정 = `verdict`, 실패 항목 = `gates`의 거짓 문 + `p3_checks`의 거짓·`fail`, G6-2 = `gates["G6-2_loc"]`, P3-2 = `p3_checks["P3-2_verdict"]`(`fail`만 실패), READY = `t_ready_rel_s`(양쪽 같은 정의라 차이만 쓴다), 행정 = 판정기의 최대 행정 필드(이름은 python-expert가 확인), 작동·FAULT = Chrono `controller_events.json`. python-expert가 기준·새 기록 양쪽에 이 필드가 실제로 있음을 보이면 확정이다. 없으면 control-expert에게 돌려보낸다 |
| J-7 U-3 slope V0 110 | **대응 지정, 존재 확인 뒤 확정** | `u3_slope_V0.json` `records[i]`: 판정 = `verdict`, 실패 항목 = `failed_rows`, P3-2 = `late_loc_reapproach.verdict`(`fail`만 실패), READY = `t_ready_s`, 행정 = `max_stroke_mm`/1000, G6-2 = 기록에 G6 문이 있으면 그 `G6-2_loc`, 없으면 형식 없음. FAULT = `warnings`의 `FAULT` 접두 이름이다. 단 `warnings`가 FAULT를 담지 않는 형식이면 C3을 형식 없음으로 둘 수 없으므로 control-expert에게 돌려보낸다. 기준 기록에는 사건 목록이 없으므로 작동 판정은 새 줄의 사건 목록으로만 한다 |
| J-5·J-6, J-13 grid_vb, J-15 | **초안 유지** | 실제 기준 파일에서 뽑은 필드 표를 python-expert가 내고, control-expert가 확인한 뒤 확정한다. 확인 전에는 판정 함수가 거부한다(지금 구현 그대로) |

- "형식 없음"은 이 표에 적힌 것만이다. 결과를 본 뒤 더하지 않는다.
- 첫 실행 묶음(J-3·J-4·J-7 신규·J-8·J-14)은 판 4 그대로 H-7′ 대상이 아니다.
