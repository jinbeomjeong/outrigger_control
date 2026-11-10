<!-- verif-protocol-auditor 리포트 원문(2026-11-10). 대상: D8x rev5 봉인 점검. 브랜치 worktree-agent-a9a55327c173a8e3e, 커밋 22521ec. 메인 세션이 편집 없이 저장. 결정은 맨 끝 "메인 세션 덧붙임" 절에만 쓴다. -->

# D8x rev5 봉인 점검 감사 (verif-protocol-auditor, 2026-11-10)

## 감사 요약
- **시점과 축**: 개정판 봉인 점검이다(R-a·R-c 결과 전). 호출문 시점이 세 표준 시점 밖이라 `실행 전` 비중으로 봤다(S·T·R·E 중심, I는 E-6d 키만).
- **대상**: 브랜치 `worktree-agent-a9a55327c173a8e3e`, HEAD `22521ec`(부모 `f708bee`, 2026-11-10T12:11:11+09:00), worktree `C:\workspace\outrigger_control\.claude\worktrees\agent-a9a55327c173a8e3e`. 감사 시작과 끝에 HEAD는 그대로였고 status도 깨끗했다.
- **기준 문서**: raw sha256 앞 8자리다. 모두 `.sha256` 첫 토큰과 raw로 일치하고, 모두 i/lf·w/lf·`-text`, CRLF 0, BOM 없음이다.
  - 원판 a377b9bb, rev1 ad16f452, rev2 5f3fa620, rev3 2318fb5c, rev4 5233c517
  - **rev5 63437019**(봉인 12:11:11, `.sha256` 파일 자체 sha a3a3137f)
  - 앞 점검 원문 `C:\workspace\outrigger_control\06_analysis\02_control\d8x\d8x_rev4_seal_audit.md`: 986add3a, LF, CR 0, BOM 없음, mtime 12:08:39(봉인 전), main checkout에서 미추적
  - 경로 2 사본 `C:\workspace\outrigger_control\.local_archive\session_9d4aec18_20261110\d8x_path2\d8x_recount.py`: 46010967
- **판정: 차단 0 / 실행 전 수정 4 / 기록 5**
  - A-1·A-2·A-3·A-6은 내용상 맞게 닫혔다.
  - A-3의 "보류 → 판정서 안 씀"은 빈 집합 통과나 조용한 통과를 만들지 않는다(B-3).
  - A-2·A-3 말고 기준·문턱·기대 수가 바뀐 곳은 없다. 5절 E-6d 키 보충만 엄격한 쪽으로 더해졌고, 머리말의 "바뀐 것" 목록에는 빠져 있다(C-2).
  - 결과 전에 닫을 것이 넷 있다. 첫째, 한쪽 경로만 고쳐지면서 원판 8절 "관문 결과·V-2 분류 일치"와 충돌한다. 둘째, 경로 1의 봉인 목록에 rev5가 없다. 셋째, rev5 5절의 실행 전 기록 키를 아무 코드도 쓰지 않는다. 넷째, 경로 1 `report`의 기본값 `[]`가 3.1-3 "키 없음 = 판정 불가"를 무력화한다.
  - 넷 모두 규칙 덧붙임(rev6)이나 구현 수정, 실행 전 기록으로 닫을 수 있다. 결과에 영향을 주는 변경은 없었다.

## 발견 사항 (심각도순)

### [실행 전 수정][R·E] B-1. 경로 1은 G1·V-2를 두 팔로 세게 고쳐졌고 경로 2는 끔 팔만 센다. 원판 8절의 "관문 결과·V-2 분류가 같아야"를 글자대로 적용하면, K1 켬 팔에만 fail이나 LAS 작동이 있는 경우 G3가 `판정 불가`가 된다. rev5는 비교 기준을 "경로 1 ↔ 경로 2 + 손 적용"으로 정하지 않았다
- **근거**
  - 원판 `d8x_rules.md:346`: "묶음별 수(E-1), 행별 `pass`/`fail`/불가, **관문 결과**, W·V 선정, **V-1·V-2 분류가 모두 같아야** 한다." `:348`: "하나라도 다르면 G3는 판정 불가다."
  - 경로 1(통합 브랜치 `worktree-agent-ac6cd65fc4ec57212` HEAD `b311169`, 12:15:26, rev5 봉인 뒤 커밋)
    - `04_scripts/03_control/d8x/d8x_judge.py:642-657` `_bundle_result`: `_status_of([parts["off"]["summary"], parts["on"]["summary"]])`, docstring "a ``fail`` in the K1-on arm fails the bundle"
    - `:1159-1161` report G1 = `_gate_of([gate_rows_off, gate_rows_on, …])`
    - `:1028-1048` `_las_activity`: "over both K1 arms (… rev4 check A-2 (b))"
  - 경로 2(46010967, 고치지 않음)
    - `:1467-1474` 묶음 status는 off 팔 fail만 본다. `:1530-1538` G1도 같다.
    - `:1306-1318` V-2는 `ra_off`·`rc_off`만 센다.
  - rev5 `d8x_rules_rev5.md:68`(2.1-4): "경로 1을 고쳐 켬 팔을 센다면 그 출력이 1~3의 손 적용 결과와 같은지 확인하고 적는다". `:77`(3.1-4)은 켬 팔 fail **수**만 대조한다. rev4 `:64`도 같다. 어느 판도 원판 8 `:346`의 "관문 결과·V-2 분류" 비교를 손 적용 뒤 값으로 한다고 적지 않았다.
- **실패 시나리오**: K1 켬 팔 R-a에 fail 1행이 있고 끔 팔은 전부 pass인 경우다.
  - 경로 1 G1은 fail이고 경로 2 G1은 pass다.
  - 원판 `:346`을 글자대로 읽으면 G3 불일치 → `판정 불가`(B-ID, "원인을 고친 뒤 다시 집계")다. rev4·rev5가 뜻한 `미달`(B-G1)이 나오지 않는다.
  - 판정자가 "원인 = 경로 2가 끔 팔만 셈"으로 보고 결과를 본 뒤 경로 2를 고치면, 봉인 뒤 도구 변경이 된다.
  - V-2도 같다. 켬 팔에만 `INFO_LIFTOFF_SLOW`가 있으면 경로 1은 `LAS_DEPENDENT`, 경로 2는 `LAS_INACTIVE`가 된다.
  - 조용한 통과는 아니다. 등급이 틀린 쪽(판정 불가)으로 가고 사후 도구 수정을 부를 수 있다.
- **권장 조치**(control-expert, 결과 전 덧붙임 rev6): "원판 8 두 경로 일치에서 G1 관문 결과와 V-2 분류는 경로 1 출력 ↔ (경로 2 출력 + rev4 1.4·rev5 2.1·3.1 손 적용 결과)로 비교한다. 켬 팔 행별 verdict와 켬 팔 LAS 수는 행 단위로 대조한다"를 적는다. 경로 2는 고치지 않는다.

### [실행 전 수정][S] B-2. 경로 1의 봉인 목록과 G0 rev3 실행 기록에 rev5가 없다
- **근거**
  - 통합 브랜치 `d8x_spec.py:39-50` `RULES_FILES`는 rev4까지이고, `:54`는 `LATEST_RULES_REV = "rev4"`다.
  - `s6_stage2.py:113`에 `D8X_RULES_REV4_SHA256`이 있다(rev5 상수 없음).
  - 커밋 메시지(`…\scratchpad\d8xfix\msg5.txt`): "seals to rev4".
  - 아래 B-5의 G0 rev3 탐침 `meta.rules_seals`도 원판~rev4만 담고 있다.
  - rev5 파일은 통합 브랜치에 아직 없다(규칙 브랜치 미병합).
- **실패 시나리오**: 이대로 $H_{impl}$를 정해 실행하면 경로 1 `seals_ok()`·prelaunch `rules`·Chrono `d8x_rules_meta`가 rev5를 대조하지 않는다. rev5가 바뀌거나 빠져도 G-S 봉인 관문이 통과한다. 경로 2 `RULES_SHA256`은 원판~rev2뿐이고 rev4 2-1이 판정서 손 확인을 요구하므로, rev5도 손 확인 목록에 들어가야 한다.
- **권장 조치**
  - python-expert·cad-expert: 규칙 브랜치를 통합 브랜치에 병합한 뒤 `RULES_FILES`·`LATEST_RULES_REV`·`D8X_RULES_REV5_SHA256`에 rev5 `63437019eaee2340fbbfc45efdcf78bfc5ba314f83085d55f19e323c6f5ffabe`를 더한다. 시험도 함께 고친다.
  - control-expert: 판정서 "두 경로 범위 차이"(rev4 2-1)에 rev5를 더한다.

### [실행 전 수정][I·R] B-3a. rev5 5절의 E-6d 다섯 키 가운데 실행 전 기록 `rows[<case>].k1_order_gate`를 쓰는 코드가 없다. 경로 1 판정도 다섯 키 가운데 둘만 본다
- **근거**
  - rev5 `:102-108`: E-6d는 다섯 키를 "읽고 모두 참이어야 한다. 키가 없으면 그 행은 판정 불가"다.
  - 4e8eb9b(`run_S6C.py` diff)는 `d8x.k1_order_gate`, `d8x.controller_meta_order_gate`, `d8x.k1_order_gate_matches_meta`를 더했다. result.json 최상위 `controller_meta`는 `run_S6C.py:2335`, `run_S8C.py:2019`에 있다. 앞의 네 키는 존재한다.
  - **`d8x_prelaunch_C.json` `rows[<case>].k1_order_gate`는 없다.**
    - 경로 1 `_chrono_prelaunch`(`d8x_judge.py:424-433`)의 `rows`는 `spec.chrono_rows(...)`다.
    - `d8x_spec.py`에는 `k1_order_gate` 문자열이 없다(Grep 0건).
    - `04_scripts/02_chrono`에 `prelaunch` 문자열이 없다(Grep 0건).
  - 경로 1 판정 `d8x_judge.py:893-895`는 `k1_order_gate`와 `controller_meta_order_gate`만 본다. 뒤의 것은 `:746-748`에서 `result.controller_meta…flat_soil_margin_order_gate` → `result.d8x.controller_meta_order_gate` 순으로 처음 찾은 값 하나다. `k1_order_gate_matches_meta`와 prelaunch 행 키는 보지 않는다.
- **실패 시나리오**
  - rev5를 글자대로 적용하면 Chrono 19행 모두 "키 없음 → 판정 불가"다(G2a·G2b 판정 불가 → 등급 판정 불가).
  - 반대로 도구 출력만 옮기면 rev5 5절 가운데 셋을 보지 않은 채 E-6d 통과가 된다. 규칙과 도구가 어긋난다.
  - 값은 같은 `controller_meta`에서 나오므로 실제로 다른 판정이 날 가능성은 낮다. 키가 빠진 옛 결과가 통과하는 길은 남는다(예: d8x 블록에 `controller_meta_order_gate` 키가 없는 result.json).
- **권장 조치**(어느 쪽인지 control-expert가 정한다)
  - 규칙이 맞다면 python-expert가 세 가지를 고친다.
    - prelaunch C의 행마다 `k1_order_gate`(기대 태그의 `_K1`)를 기록한다.
    - judge-chrono가 다섯 키를 각각 읽는다. 키가 없으면 종료 2다.
    - 시험을 더한다.
  - 도구가 맞다면 control-expert가 rev6에서 5절을 "경로 1이 보는 키 + 판정서 손 확인 키"로 나눠 적는다.

### [실행 전 수정][E] B-4. 경로 1 `report`가 `k1_rows_failed`를 기본값 `[]`로 채운다. 그래서 rev5 3.1-3 "경로 1 출력에 `k1_rows_failed` 키가 없으면 판정 불가"를 report 출력에서는 확인할 수 없다
- **근거**
  - 통합 브랜치 `d8x_judge.py:1174-1175`: `"k1_rows_failed": {"R-a": ra.get("k1_rows_failed", []), "R-c": rc.get("k1_rows_failed", [])}`
  - rev5 `:76`: "경로 1 출력에 `k1_rows_failed` 키가 없으면 그 묶음은 `판정 불가` … 0으로 읽지 않고".
- **영향**: 같은 report의 G1은 `gate_rows_on`이 None이면 `_gate_of`(`:1179`, `s is None`)에서 판정 불가가 된다. 그래서 켬 팔이 통째로 빠지면 등급은 막힌다. 남는 경우는 judge-ra/rc 출력에 `gate_rows_on`은 있고 `k1_rows_failed`만 없는 경우(옛 출력이나 도구 결함)다. 이때 report는 켬 팔 fail 0을 낸다. 경로 2도 0이면 3.1-4 대조를 통과한다(조용한 0).
- **권장 조치**
  - python-expert: 기본값을 없앤다(키가 없으면 `None`을 내고 종료 2).
  - 또는 control-expert: rev6에 "3.1-3의 경로 1 출력은 `judge-ra`·`judge-rc` 출력 파일"이라고 적는다.

### [기록][E] B-3. A-3 "보류 → 판정서 안 씀"은 빈 집합 통과나 조용한 통과를 만들지 않는다(확인)
- 경로 2 `_bundle`(`:1454-1480`)에서 켬 팔 파일이 없을 때의 동작
  - `missing_parts`가 생기고 status는 `pending`, `k1_rows_fail`은 `None`이다.
  - 단 끔 팔에 fail이 있으면 `:1473`이 `:1475`보다 앞이라 status는 `fail`이다. 이 경우는 rev5 `:75`의 "최종 집계는 원판 3절 모든 입력이 들어간 실행에서만"이 따로 막는다.
- 켬 팔 파일이 비었거나 건수가 틀리면 `count_rows` `:1181-1185`가 E-1을 내고 unjudgeable이다. 켬 팔 행 정체성(E-6 `k1_order_gate`, `:704-705`)이 어긋나도 unjudgeable이다. 따라서 3.1-5 "같고 0이면 도구 G1 그대로"가 빈 켬 팔로 통과하는 길은 없다.
- `grade`(`:1552-1573`)의 순서는 unjudgeable > fail > pending > flags다. 3.1-6 문구와 같다.
- 3.1-1 판정 불가 우선은 감사 제안과 같다. 3.1-2 보류는 등급이 아니라 "판정서를 쓰지 않음"이라 통과로 갈 수 없다. 3.1-3과 3.1-2의 선후(최종 집계에서 경로 2 G1 `pending` + `None`)는 어느 쪽으로 읽어도 통과가 아니다.
- V-2 결측: 경로 2는 `record` 없는 행(드라이버 오류 행, `:668-670`·`:696-697`)을 `or 0`(`:1315`)으로 센다. 그런 행은 verdict가 `fail`이거나 unjudgeable이라 G1이 미달이나 판정 불가로 먼저 막힌다. 3.1-7 결측이 등급을 통과로 바꾸는 경로는 없다.
- 남는 문구 모순(기록): 2.1-1(`:65`)은 "필드가 없으면 원 결과 파일에서 손으로 센다"이고, 3.1-7(`:80`)은 "결측(켬 팔 행 기록 없음) = 판정 불가"다. "필드 없음"과 "행 기록 없음"을 구별해 읽으면 양립한다. 원 결과에도 사건 목록이 없을 때의 처리는 적혀 있지 않다(확인 필요 2).

### [기록][T] B-5. rev5 봉인 뒤(12:11:11) 메인 세션 scratchpad에 G0 rev3 전체 재계산 탐침 두 파일이 생겼다. rev5 공개는 봉인 시점 기준으로 참이다. 실행 전 기록과 판정서에는 공개해야 한다
- **근거**: `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\d8xfix\`
  - `g0_rev3_probe.json`: 12:15:48, 186,090 B, sha256 `26cb3faa3b1f6f018933d05366d8562a7d85aaabd823507f2ef492bb87ad4958`. meta는 `rules_rev` rev3, `run_commit` `b311169…`(통합 브랜치), `clean` true, reuse 0 / recompute 60.
  - `g0_rev3_probe_judge.json`: 12:15:51, sha256 `226e7b2bffb96500dab0bacc0010f3f8512ffbdbc66c351bc2bc139d7d96ea34`. `gate_G0` = `pass`.
  - `timeline.py --rules rev4 rev5 --results <탐침 5개>`: G0 두 파일은 rev5보다 뒤("before" = 규칙이 먼저, mtime 근거 `[추정]`)이고, R-a·R-c 탐침 3건은 rev5보다 앞(`rule_after_results` 3, 공개됨)이다.
  - 저장소 전체(main·모든 worktree)에서 `ra_on.json`·`ra_off.json`·`hrx_*.jsonl`·`d8x_g0_rev3*.json`·`d8x_prelaunch*.json`·`d8x_expect_k1.json`·`d8x_selection.json`·`d8x_judgement*`를 찾았다. 0건이다.
  - `%TEMP%\claude`에서 11:36 뒤의 d8x·probe·hrx·ra_·rc_·g0_rev3 이름은 위 d8xfix 파일들뿐이다.
- **판단**: 공개 문구 "정식 … G0 rev3 산출물 0건"(`:24`)은 봉인 시점에 참이다. 이 G0 결과는 병합 전 커밋에서 나왔으므로 rev4 3(`rev4:82`)에 따라 판정에 쓰지 않는다. 다만 메인 세션이 이 값(G0 60/60 통과)을 실행 전에 봤으므로 실행 전 기록과 판정서 "봉인 뒤·실행 전 본 자료"에 적어야 한다. rev6을 쓴다면 그 공개 절에도 적어야 한다.
- **권장 조치**(메인 세션): 두 파일을 `.local_archive`로 옮겨 보존하고 sha를 적는다. 정식 G0 rev3는 $H_{impl}$에서 새로 돈다.

### [기록][T] B-6. A-1 처리는 맞다. 보존본은 원본과 바이트가 같다. 같은 탐침의 로그 두 개와 부분 파일 하나는 보존 목록에 없다
- 보존 폴더 `C:\workspace\outrigger_control\.local_archive\session_6f3ebc4d_20261110\d8x_probes\`
  - 다섯 파일의 실측 sha가 `SHA256SUMS.txt`와 rev5 `:39-43`과 같다. 원래 위치(d8xfix)의 같은 이름 파일과도 같다.
  - `SHA256SUMS.txt` 자체 sha는 0e239c7a다.
  - 보존본 mtime은 12:08:39(복사 시각)다. rev5 표의 시각(11:39:53·11:39:42·11:42:25)은 원본 mtime과 같다.
- rev5 1.2 표의 값은 파일과 같다.
  - R-a: `min_true_cyl_force_kN` 61.0, `t_ready_s` 43.4, `commands_sha256` `cab74a24…be23`, `k1_order_gate` False, 태그 `final_C4G2_LAS`, `d8x.limit` 1, HEAD `20e8722`, `is_clean` false
  - R-c 끔·켬: `J1_N` 53,835.95, `t_ready_s` 57.5, 태그·`k1_order_gate`가 표와 같다.
- 보존 목록에 없는 같은 탐침의 부산물: `rc_probe_off.log`(a1156da2…), `rc_probe_on.log`(37d7af8b…), `ra_probe_off.json.partial.jsonl`(8580f710…). 내용상 새 값은 아니지만 공개 근거를 완결하려면 함께 보존하는 것이 낫다.
- A-2 선택과 탐침의 관계: R-a 탐침의 `d8x.events`에 `INFO_LIFTOFF_SLOW`가 0건이고, R-c 탐침 두 파일에는 사건 목록이 없다. 그래서 켬 팔 LAS 작동을 보여준 탐침은 없다. (b)는 (a)보다 같거나 엄격하다. rev5 `:53`의 영향 판단은 맞다.

### [기록][R] C-1. A-2 (b)·A-6 처리는 결정과 같다
- A-2: rev5 `:57-58`은 판정 대상 = R-a 1,102(910 + 192), R-c 288(192 + 96)로 rev4 1.1(`rev4:39`)과 같다. "두 팔 중 어느 쪽이라도 > 0 → `LAS_DEPENDENT`"는 사용자 결정 (b)(감사 원문 `:204`)와 같다.
  - 키 (묶음, 점, 단계)와 접두사 `INFO_LIFTOFF_SLOW`는 경로 2 `:177`·`:1314`와 같다.
  - 경로 2 켬 팔 행 위치 `report["ra"]["on"]["rows"][*]["record"]["las_events"]`는 `:1408`·`:721`·`:863`에서 확인했다(정수 개수).
  - 인용 줄 번호 1306~1320, 1552~1575는 사본 46010967에서 맞다.
  - 경로 1의 키 형식은 `ra|<point>|<level>`·`rc|<slope_name>|<level>`(`:1036`·`:1040`)이고 경로 2는 `["R-a", point, level, n]`이다. 판정서 V-2 표에서 대응을 적어야 한다.
- A-6: rev5 `:98`이 rev4 `:81` 문구를 "메인 세션 지정, 실행 전 감사 확인"으로 바꿨다. $H_{impl}$ 정의는 rev4 그대로다. 지금 master HEAD는 `e67dae8`(12:16:55)이고 통합 브랜치(b311169)는 아직 미병합이다.

### [기록][R·T] C-2. rev5 머리말의 "바뀐 판정은 A-2와 3절뿐"에 5절(E-6d 키 보충, 키 없음 = 판정 불가)이 빠져 있다. 5절의 "4e8eb9b, 병합 전"은 통합 브랜치 기준으로는 사실이 아니다
- rev5 `:16` 목록과 본문 1~4절을 대조했다. J1~J11, 문턱, 관문 순서, 기대 수, 점 좌표, 마름모, G0-4, d45, 태그, G0 재계산, W, FLAG (i)·(ii), 7절, 등급 정의를 바꾸는 문장은 없다.
- 5절(`:100-108`)은 rev3 E-6d(`rev3:69`, 두 조건)에 키 셋(`d8x.controller_meta_order_gate`, `k1_order_gate_matches_meta`, prelaunch 행 키)과 "키 없음 = 판정 불가"를 더한다. 결과 전이고 엄격한 쪽이라 허용되지만, "바뀐 것" 목록에는 넣어야 한다.
- 4e8eb9b(12:06:52)는 rev5 봉인 전인 12:09:18에 통합 브랜치로 병합됐다(`8c9e8b1` "Merge d8x-gate-meta"). master에는 아직 없다. "병합 전"은 "master 병합 전"으로 읽어야 맞다.
- rev5 `:23`의 본 것 "커밋 제목(4e8eb9b)": 5절의 키 이름은 커밋 **본문**에 있다. 본 범위를 정확히 적는 편이 낫다(사소).
- 판정서나 rev6에서 정정 한 줄이면 된다.

### [기록][S] C-3. rev5가 sha로 인용한 앞 점검 원문 986add3a는 아직 어디에도 커밋되지 않았다. 규칙 브랜치의 `d8x/** -text`로는 보호된다
- main checkout에서 `git ls-files --eol`은 미추적이고 `check-attr text`는 `unspecified`다(master `.gitattributes`에 `d8x/**` 줄 없음). `git status`는 `?? 06_analysis/02_control/d8x/`다.
- 규칙 브랜치 22521ec에서 같은 경로의 `check-attr text`는 `unset`(`-text`)이다(f708bee `.gitattributes:39`).
- 파일은 LF이고 CR 0이다. `core.autocrlf=true`다.
- 권장(메인 세션): 규칙 브랜치를 master에 병합한 **뒤에** 바이트 그대로 커밋한다. 그 전에 master에서 커밋하면 보호가 없다(앞 점검 A-4와 같은 함정). 커밋 뒤 `ls-files --eol`(i/lf attr/-text)과 sha 986add3a를 대조한다.

## 규칙↔도구 대조표 (rev5 변경분)

| 규칙 | rev5 | 경로 2(46010967) | 경로 1(통합 b311169) | 결과 |
|---|---|---|---|---|
| V-2 범위 원판 `:334` | 두 팔(`:57-58`) | 끔 팔만(`:1306-1318`) | 두 팔(`:1028-1048`) | 판정서 손 적용(`:61-68`). 원판 8 일치 비교 기준 미정(B-1) |
| G1 손 적용 순서 | 3.1-1~6(`:74-79`) | unjudgeable > fail > pending(`:1471-1478`, `:1552-1573`) | 두 팔 `_status_of`(`:648`), report `_gate_of`(`:1159`) | 순서는 같다. 원판 8 비교 기준 미정(B-1) |
| 결측 3.1-3 | `None`·키 없음 = 판정 불가 | `k1_rows_fail` None(`:1479`) | report 기본값 `[]`(`:1174-1175`) | 경로 1 report에서 확인 불가(B-4) |
| 두 경로 수 3.1-4 | fail 수 대조 | `k1_rows_fail` | `len(k1_rows_failed)` | 같다 |
| E-6d 5절 | 키 다섯, 없음 = 판정 불가 | 보지 않음(rev3 3.3) | 둘만(`:893-895`, `:745-748`) | prelaunch 키를 쓰는 코드 없음(B-3a) |
| 봉인 | rev5 63437019 | `RULES_SHA256` 원판~rev2 | `RULES_FILES` ~rev4(`d8x_spec.py:39-54`) | rev5 미포함(B-2) |
| $H_{impl}$ | 메인 지정, 감사 확인(`:98`) | — | — | 결정과 같다 |

## 확인 필요
1. (B-1, control-expert) 원판 8 두 경로 일치에서 G1 관문 결과와 V-2 분류를 "경로 1 ↔ 경로 2 + 손 적용"으로 비교한다고 rev6에 적을지 정한다. 경로 1을 끔 팔 기준으로 되돌리는 방법도 있다. 다만 그러면 rev4 1.4·rev5 2.1-4의 "고쳐도 됨"과 이미 구현된 b311169를 되돌려야 한다.
2. (B-3 남는 모순, control-expert) 2.1-1 "필드가 없으면 원 결과에서 손으로 센다"와 3.1-7 "켬 팔 행 기록 없음 = 판정 불가"의 경계를 정한다. 원 결과에도 사건 목록이 없을 때의 처리도 정한다.
3. (B-3a, control-expert) rev5 5절의 prelaunch `rows[<case>].k1_order_gate`를 구현으로 채울지, 규칙에서 "판정서 손 확인 키"로 바꿀지 정한다.
4. (B-5, 메인 세션) 봉인 뒤 G0 rev3 탐침 공개를 실행 전 기록과 판정서로 충분하다고 볼지, rev6을 쓸 때 공개 절에 함께 넣을지 정한다.

## 위임 필요
- **control-expert**: B-1(비교 기준), B-3a 또는 B-4(규칙 쪽을 고르는 경우), C-2(바뀐 것 목록과 "병합 전" 정정). 결과 전 덧붙임 rev6으로 봉인하고 다시 감사받는다. 경로 2는 고치지 않는다.
- **python-expert**(경로 1, 통합 브랜치)
  - B-2: 규칙 브랜치를 병합한 뒤 `d8x_spec.RULES_FILES`·`LATEST_RULES_REV`·`s6_stage2.D8X_RULES_REV5_SHA256`(cad-expert와 협의)에 rev5 `63437019…fabe`를 더하고 시험을 고친다.
  - B-4: `cmd_report` `:1174-1175`의 `.get("k1_rows_failed", [])` 기본값을 없앤다(키가 없으면 종료 2). 시험: judge 출력에서 키를 지우면 종료 2.
  - B-3a(규칙 쪽이 정해지면)
    - `_chrono_prelaunch`(`:424-433`)가 행마다 `k1_order_gate`를 기록한다.
    - judge-chrono가 `d8x.k1_order_gate`, `d8x.controller_meta_order_gate`, `d8x.k1_order_gate_matches_meta`, `controller_meta…flat_soil_margin_order_gate`, prelaunch 행 키를 각각 읽는다(처음 찾은 값 하나로 대신하지 않음). 키가 없으면 판정 불가다.
- **메인 세션**
  - B-5: G0 탐침 두 파일을 보존하고 sha를 기록한다. 실행 전 기록에 공개한다.
  - B-6: 로그 두 개와 부분 파일 하나를 보존 폴더에 더할지 정한다.
  - C-3: 규칙 브랜치를 병합한 뒤 앞 점검 원문을 바이트 그대로 커밋한다.

## 메인 세션 권고
- D8x 실행 전 감사(통합 브랜치와 규칙 브랜치를 master에 병합한 뒤)에서 볼 것
  - $H_{impl}$ 커밋 id(메인 세션 지정)
  - `RULES_FILES`에 rev5(와 rev6) 포함
  - prelaunch C 행의 `k1_order_gate`
  - `report` 기본값 수정
  - 앞 점검 A-7·A-8 항목
- 이 감사는 실행하지 않았다. 건조 실행(prelaunch 등)도 하지 않았다.

## 검사하지 못한 것
- 경로 1 시험(`test_d8x_judge.py`, `test_d8x_chrono_rows.py`)의 내용과 통과 여부. 읽지 않았다.
- b311169의 나머지 변경(E-6a~f, judge-g0 rev3 출처 점검). B-1~B-4 관련 함수만 읽었다.
- 탐침 결과를 rev5 작성자나 결정자가 봤는지는 transcript로 대조하지 않았다. rev5 `:23`은 "본 것"에 탐침 다섯 파일을 적었다.
- G0 rev3 탐침의 행별 값. 메타와 `gate_G0`만 봤다.
- `gate_scan.py`는 돌리지 않았다. 관련 경로는 직접 읽었다.

## 실행한 검증
- 인터프리터: `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`MKL_THREADING_LAYER=TBB`, `-X utf8`). Python은 모두 PowerShell 도구로 실행했다. 프로젝트 모듈은 import하지 않았다.
- `depcheck.ps1` → STAMP(numpy 2.5.3, pyyaml 6.0.3, git OK)
- `source_guard.py snapshot/verify`, 입력 21개
  - 원판~rev5와 `.sha256` 12개
  - 탐침 보존본 6개
  - 경로 2 사본
  - 규칙 브랜치 `.gitattributes`
  - 앞 점검 원문
- `seal_check.py --repo <wt> "06_analysis/02_control/d8x/d8x_rules*.md" --quoted <rev5> --hash-files <앞 점검 원문> <탐침 보존본> <경로 2 사본>`
  - 6판 모두 raw 일치, `-text`, i/lf·w/lf, CRLF 0, BOM 없음
  - 인용 14개 가운데 11개가 풀렸다. 못 푼 3개는 오탐이다.
    - `cab74a24`는 파일 해시가 아니라 탐침 안의 `commands_sha256` 값이다. `cab74a241f775f67…8b15be23`로 직접 확인했다.
    - `ac6cd65fc4ec57212` 2건은 브랜치 이름이다.
- `timeline.py --rules rev4 rev5 --results <d8xfix 탐침 3 + G0 탐침 2> --no-git`: R-a·R-c 탐침은 rev4·rev5보다 앞이고, G0 탐침은 rev5보다 뒤다(mtime 근거).
- `Get-FileHash`: 보존본 6개, d8xfix 원본 전체, 경로 2 사본, 앞 점검 원문
- 바이트 CR·BOM 계수: 앞 점검 원문
- 한 줄 python: 탐침 R-a·G0 메타와 사건 조회, `commands_sha256` 확인
- git 조회: `log`, `show --stat`, `show 4e8eb9b`, `diff f708bee 22521ec -- .gitattributes`, `status`, `check-attr`, `ls-files --eol`, `worktree list`, `branch --contains`
- 파일 검색
  - 저장소 전체(main·worktree)에서 정식 D8x 산출물 이름(Get-ChildItem)
  - `%TEMP%\claude`에서 11:36 뒤의 D8x 관련 파일
- 읽은 코드
  - 경로 2 `:177`, `:660-728`, `:1176-1190`, `:1300-1324`, `:1395-1576`
  - 경로 1(b311169) `d8x_spec.py:1-60`, `d8x_judge.py:360-433`, `:640-657`, `:735-761`, `:875-905`, `:985-1052`, `:1140-1180`
  - 4e8eb9b diff
  - d8xfix `msg4.txt`·`msg5.txt`·`tables_probe.py`
- 만든 뒤 지운 것: scratchpad `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\rev5_audit\`(guard.json, seal.md)를 폴더째 지웠다. 남은 부산물은 없다.
- 메모리: `audit_pitfalls.md`에 일반 함정 한 줄을 더하고 `MEMORY.md` 색인을 갱신했다. 내용은 한쪽 경로만 고친 손 적용과 원판 두 경로 일치 조항의 충돌, 집계 기본값 `[]`, 봉인 뒤 탐침 재스캔이다.
- 최종 판정 직전 확인: source_guard verify로 입력 불변을 확인했다. 대상 HEAD는 22521ec 그대로이고 status는 깨끗하다. 통합 브랜치 HEAD는 b311169 그대로다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha d8x_rules_rev1.md ad16f452…, d8x_rules_rev1.sha256 7aebedc5…, d8x_rules_rev2.md 5f3fa620…, d8x_rules_rev2.sha256 52a42789…, d8x_rules_rev3.md 2318fb5c…, d8x_rules_rev3.sha256 4b6ea235…, d8x_rules_rev4.md 5233c517…, d8x_rules_rev4.sha256 fc118b10…, d8x_rules_rev5.md 63437019…, d8x_rules_rev5.sha256 a3a3137f…, d8x_rules.md a377b9bb…, d8x_rules.sha256 66837eee…, ra_probe_off.json 43da9a88…, ra_probe_off.log 6bf91694…, rc_probe_off.json 327ef5cc…, rc_probe_on.json 97fa70ad…, rc_probe.py 93a47b6f…, SHA256SUMS.txt 0e239c7a…, d8x_recount.py 46010967…, .gitattributes 8ad6ec28…, d8x_rev4_seal_audit.md 986add3a…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음

---

## 메인 세션 덧붙임 (2026-11-10)

- (결정 기록 자리)
- 사용자 결정(2026-11-10): 권고대로. B-1은 rev6에 "원판 8 일치 비교 = 경로 1 ↔ (경로 2 + 손 적용)"으로 적고, B-2·B-3a(실행 전 기록 키 구현 + 다섯 키 각각 읽기)·B-4는 경로 1 코드로 고친다. rev6 공개 절에 봉인 뒤 G0 rev3 탐침을 넣는다. B-5·B-6 탐침 파일 5개를 `.local_archive/session_6f3ebc4d_20261110/d8x_probes/`에 보존(SHA256SUMS_add.txt). C-2 정정과 B-3 경계 문구는 rev6에서 control-expert가 정한다.
