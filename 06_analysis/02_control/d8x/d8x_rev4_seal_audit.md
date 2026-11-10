<!-- verif-protocol-auditor 리포트 원문(2026-11-10). 대상: D8x rev4 봉인 점검, 브랜치 worktree-agent-a9a55327c173a8e3e 커밋 f708bee. 메인 세션이 편집 없이 저장. 결정은 맨 끝 "메인 세션 덧붙임" 절에만 쓴다. -->

# D8x rev4 봉인 점검 감사 (verif-protocol-auditor, 2026-11-10)

## 감사 요약
- 시점: 개정판 봉인 점검이다. 대상은 D8x rev4이고, R-a·R-c 결과가 나오기 전이다. 이 감사의 축 비중은 `실행 전`에 맞췄다(S·T·R·E 중심).
- 대상: 브랜치 `worktree-agent-a9a55327c173a8e3e`, HEAD `f708bee`(부모 `589ff43`, 2026-11-10T11:56:39+09:00), worktree `C:\workspace\outrigger_control\.claude\worktrees\agent-a9a55327c173a8e3e`. 감사 중 git status는 깨끗했고 HEAD도 바뀌지 않았다.
- 기준 문서(raw sha256 앞 8자리, 모두 `.sha256` 첫 토큰과 raw 일치)
  - 원판 `d8x_rules.md` a377b9bb
  - rev1 ad16f452 / rev2 5f3fa620 / rev3 2318fb5c
  - **rev4 `d8x_rules_rev4.md` 5233c517**: 봉인 11:56:17. 같은 폴더의 `.sha256` 파일 자체 sha는 fc118b10
  - 앞선 재감사 원문 `C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\las_k1_adopt_rev1_d8x_rev3_audit.md` aeb481ea: main checkout, 미추적, mtime 11:53:57(봉인 전), LF 229줄, CRLF 0, BOM 없음
  - 경로 2 사본 `C:\workspace\outrigger_control\.local_archive\session_9d4aec18_20261110\d8x_path2\d8x_recount.py` 46010967…d9d1, 시험 906f899c
- **판정: 차단 0 / 실행 전 수정 4 / 기록 4**
  - F-1·F-3·F-8·F-9는 내용상 맞게 닫혔다. F-1 처리는 원판·rev1~rev3과 모순이 없고 기준을 엄격한 쪽으로만 바꿨다. F-1 말고 기준·경계·문턱·기대 수가 바뀐 곳은 없다.
  - 다만 결과 전에 닫아야 할 것이 넷 있다.
    1. rev4 "공개"의 "결과 0건" 문구가 사실과 다르다(A-1). rev3 봉인과 rev4 봉인 사이에 새 점 폐루프 탐침 3건이 있다.
    2. 넓어진 "판정 대상"이 V-2와 어떤 관계인지 정해지지 않았다(A-2).
    3. 손 적용 절차의 우선순위와 None 처리가 빠져 있다(A-3).
    4. rev4가 sha로 인용한 감사 원문에 `-text` 보호가 없다(A-4, F-2 재발).
  - 위 넷을 공개·덧붙임·커밋으로 처리하면 실행 전 감사로 넘어갈 수 있다. 결과에 영향을 주는 규칙 변경은 없었다.

## 발견 사항 (심각도순)

### [실행 전 수정][T] A-1. rev4 "공개"의 "R-a·R-c 결과 0건, 새 점의 폐루프 결과를 하나도 보지 않았다"가 사실과 다르다. rev3 봉인 뒤·rev4 봉인 전에 판정 대상 키의 탐침 결과 3건이 있다
- 근거
  - `d8x_rules_rev4.md:19`: "**R-a·R-c·Chrono D8x 결과와 G0 rev3 결과(`d8x_g0_rev3.json`)는 여전히 0건이다.** 새 점의 폐루프·정적 결과를 하나도 보지 않았다".
  - main 세션 scratchpad `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\d8xfix\`에 다음이 있다.
    - `ra_probe_off.json`(mtime 11:39:53)과 `ra_probe_off.log`
      - 행 `main|C2_tv0.1|top|rigid|pitch+`(새 점 pitch+ 3.7°, td_main 상단 rigid, K1 끔 팔, 태그 `final_C4G2_LAS`, `k1_order_gate` False)
      - `min_true_cyl_force_kN` 61.0, `t_ready_s` 43.4, `commands_sha256` cab74a24…
      - meta: HEAD `20e8722`(통합 브랜치), `is_clean: false`(편집 중 11파일), `d8x.limit` 1
    - `rc_probe_off.json`(11:39:42)과 `rc_probe_on.json`(11:42:25)
      - H-R-X `D1|H-R-X|rigid|T|fdown3.7|K1`, VB, ε 0의 끔·켬 팔
      - 두 팔 모두 `J1_N` 53,835.95, `t_ready_s` 57.5. 태그는 각각 `final_C4G2_P3_LAS` / `final_C4G2_P3_LAS_K1`
    - 만든 스크립트 `rc_probe.py`(11:37:23)의 docstring: "Pipeline probe (not a judged run)".
  - `timeline.py --rules rev3 rev4 --results <탐침 3>` 결과
    - rev3(11:36:17)는 탐침보다 앞선다. 그래서 rev3의 "0건"은 참이었다.
    - rev4(11:56:17)는 세 탐침 모두보다 뒤다(`rule_after_results` 3건). 결과 시각 근거는 mtime뿐이지만, 로그의 경과 시간 124 s·157.7 s와 맞는다.
  - 저장소 전체(main·모든 worktree)와 `%TEMP%\claude` 전체에서 `ra_*.json`·`hrx_*.jsonl`·`D8X_*`·`d8x_g0_rev3*`·`d8x_prelaunch*`·`d8x_expect*`·`d8x_selection*`·`d8x_judgement*`를 찾았다. 나온 것은 위 `ra_probe_off.json` 하나다(나머지 두 탐침은 이름이 `rc_probe_*`라 패턴 밖이며, 폴더 목록에서 찾았다). 정식 R-a·R-c·Chrono·G0 rev3 산출물은 0건이다.
- 영향 판단
  - rev4가 바꾼 것은 판정 범위뿐이다(K1 켬 팔 fail → G1 실패). 명령·실행은 바꾸지 않았다. 그리고 엄격한 쪽 변경이다.
  - 본 값(R-c 한 행이 K1 끔·켬에서 J1 같음, R-a pitch+ 61 kN)은 선택지 (a)를 고르는 데 유리하게 작용할 수 없다. (a)는 (b)보다 항상 같거나 엄격하다.
  - rev4 `:82`가 "통합 브랜치 병합 전 커밋에서 돌린 R-a·R-c·G0 결과는 판정에 쓰지 않는다"로 이 탐침의 사용은 막는다.
  - 따라서 결론을 틀리게 할 위험은 낮다. 그러나 봉인 문서의 공개 문구가 사실과 다르므로 차단 바로 아래인 실행 전 수정으로 둔다.
  - [추정] 사용자 결정(감사 원문 덧붙임, mtime 11:53:57)이 탐침 뒤에 기록됐다. 결정자나 rev4 작성자가 탐침 값을 봤는지는 확인하지 못했다.
- 실패 시나리오: 판정서가 rev4 `:19`를 인용해 "봉인 전 결과 0건"이라고 적는다. 뒤에 다른 감사가 탐침 파일을 찾으면 공개 누락이 되고, 판정 확정이 늦어진다.
- 권장 조치(control-expert와 메인 세션)
  - D8x 실행 전에 공개 기록을 남긴다. rev5(공개 전용 덧붙임) 또는 실행 전 기록(prelaunch)과 판정서의 "봉인 전 본 자료" 절에 적는다.
  - 적을 것: 탐침 3건의 경로·시각·키·값·실행 커밋(`20e8722`, dirty), "판정에 쓰지 않음(rev4 3)", "rev4 변경은 명령 무관·엄격한 쪽".
  - 탐침 파일은 지우지 말고 보존한다(공개 근거). 위치는 `.local_archive` 등으로 옮겨 sha를 적는다.

### [실행 전 수정][R·E] A-2. "판정 대상"을 K1 켬 팔까지 넓혔지만 원판 V-2(같은 용어)를 어떻게 읽을지 정하지 않았다. 두 경로는 모두 끔 팔만 센다
- 근거
  - 원판 `d8x_rules.md:334` V-2: "R-a·R-c **판정 대상 행**의 `INFO_LIFTOFF_SLOW` 수를 점·단계별로 센다. 0인 점은 `LAS_INACTIVE`". `:335` V-2b: 작동한 점은 `LAS_DEPENDENT` → FLAG (iii), Chrono 재실행.
  - rev4 `:39` 판정 대상 = R-a 1,102 전부 + R-c 288 전부. rev4 `:26`(0절 표)은 원판 10 미달 문구에만 이 뜻을 적용한다고 적었다. `:54`는 "FLAG (iii): V-1 `K1_DEPENDENT`, V-2 `LAS_DEPENDENT` 그대로"라고만 적었다. V-2의 "판정 대상 행" 범위는 말하지 않았다.
  - 경로 2 `d8x_recount.py:1306-1316`: 주석 "V-2: judged rows only (K1 pairs excluded)"이고 `ra_off`·`rc_off`만 센다.
  - 경로 1(통합 worktree `agent-ac6cd65fc4ec57212`의 편집 중 `d8x_judge.py:956-966` `_las_activity(ra_off, rc_off)`)도 끔 팔만 센다.
  - V-3(`:336`, "판정 대상 행이 모두 `pass`이면 추가 Chrono는 없다")은 넓은 뜻으로 읽어도 G1과 같은 결론이다. 문제 없다.
- 실패 시나리오
  - `K1_DEPENDENT`인 점에서 K1 켬 행에만 `INFO_LIFTOFF_SLOW`가 생기는 경우를 생각한다. 넓은 뜻으로 읽으면 `LAS_DEPENDENT` → FLAG (iii) → `조건부 통과`이고 Chrono 재실행 대상이 생긴다. 두 도구는 `LAS_INACTIVE` → `통과`를 낸다.
  - 이때 두 경로는 서로 같아서 8절 불일치로 잡히지 않는다. 규칙 해석과만 어긋난다.
  - 강체 지면에서는 관문이 작동하지 않을 것으로 예상한다(rev3 6). 잠재 결함이다.
- 권장 조치(확인 필요 1 → control-expert가 결과 전 덧붙임으로 확정)
  - (a) V-2 범위는 그대로 끔 팔로 둔다(도구와 같음). K1 켬 팔의 LAS 작동은 기록한다. 또는
  - (b) K1 켬 팔도 센다. 이 경우 판정서가 손으로 적용하는 문구를 1.4처럼 둔다(두 도구는 고치지 않음 / 경로 1만 고침).

### [실행 전 수정][E·R] A-3. 1.4 손 적용 절차가 판정 불가와 어떤 순서로 적용되는지, 경로 2 값이 `None`일 때 어떻게 읽는지 정하지 않았다
- 근거
  - rev4 `:62` "둘 중 하나라도 0이 아니면 **G1 실패**로 적고, 그 뒤 관문(G2a…)과 등급은 **도구 출력과 관계없이** `미달`(B-G1)로 둔다".
  - rev4 `:41` "K1 켬 팔 행의 `판정 불가`는 원판·rev3대로 묶음을 판정 불가로 만든다(바뀌지 않음)".
  - 원판 `:410` 판정 불가 = 빈 집합 방지·정체성(I-*)·두 경로 일치 실패. 경로 2 `grade()`(`:1552-1573`)의 순서는 unjudgeable > fail > pending > flags다.
  - 경로 2 `_bundle`(`:1454-1480`)
    - 묶음 수준 문제(E-1 수 불일치, 3.2 태그 히스토그램)가 있어도 행별 `fail`은 그대로 세어 `k1_rows_fail`에 들어간다(`:1479`, `count_rows` `:1176-1190`).
    - `--ra-k1`/`--rc-k1`을 주지 않으면 `k1_rows_fail`은 `None`이다(`(out["parts"].get("on") or {}).get("fail")`). 이때 묶음 `status`는 `pending`이다(`:1475-1476`).
  - 경로 1 `_bundle_result`(35df06c `d8x_judge.py:578-590`)는 켬 팔이 판정 불가이거나 수가 다르면 `EXIT_NOT_JUDGEABLE`을 낸다. 켬 팔 fail은 `k1_rows_failed` 목록으로만 남는다.
- 실패 시나리오
  - 판정 불가 덮어쓰기: K1 켬 팔 파일에 정체성·수 문제가 있어 도구가 `판정 불가`를 냈는데, 그 파일 안에 `fail` 행이 하나라도 있는 경우다. `:62`를 글자대로 적용하면 등급이 `미달`이 된다. 정체성이 깨진 행으로 등급을 내는 셈이고, 원판 10·B-ID(원인 수정 뒤 재실행)와 어긋난다.
  - `None` 읽기: 켬 팔 파일이 빠졌을 때 `k1_rows_fail = None`을 "0이 아님"으로 읽으면 G1 실패가 된다. 옳은 처리는 `보류`·판정 불가다. 조용한 통과는 아니다.
  - `:63`(둘 다 0이면 도구 G1 그대로)은 도구가 켬 팔 누락 때 pending이나 판정 불가를 내므로 빈 집합 통과는 생기지 않는다. 이 부분은 확인했다.
- 권장 조치(control-expert 덧붙임 문구, 결과 전)
  - "도구 G1이 `판정 불가`·`보류`이면 손 적용보다 그것이 우선한다. K1 켬 fail 수는 기록한다."
  - "`k1_rows_fail`이 `None`이거나 `k1_rows_failed` 키가 없으면 판정 불가(입력 누락)로 둔다."
  - 판정서 표에 두 경로의 켬 팔 `expected/actual/pass/fail/unjudgeable`를 함께 적게 한다.

### [실행 전 수정][S] A-4. rev4가 sha로 인용한 재감사 원문이 이 브랜치에서 `-text`로 보호되지 않는다(앞 감사 F-2와 같은 문제가 다시 생김)
- 근거
  - rev4 `:9`가 `las_k1_adopt_rev1_d8x_rev3_audit.md`의 raw sha `aeb481ea…`를 계기 근거로 인용한다. seal_check `--quoted`는 이 파일 raw로 풀었다.
  - 파일은 LF 229줄, CRLF 0이다. `core.autocrlf=true`다.
  - 이 브랜치(f708bee)의 `git check-attr text`: 이 파일과 `las_k1_switch_post_audit.md` 모두 `unspecified`다. f708bee의 `.gitattributes` 변경은 d8x 두 줄뿐이다.
  - main checkout의 `.gitattributes`에는 **미커밋** 두 줄이 있다(`git diff`: `+…/las_k1_switch_post_audit.md -text`, `+…/las_k1_adopt_rev1_d8x_rev3_audit.md -text`).
- 실패 시나리오
  - 보호 없이 커밋한 뒤 이 PC에서 새로 checkout(worktree)하면 autocrlf가 CRLF로 바꾼다. 그러면 raw sha가 aeb481ea와 달라진다. 파일이 지금 LF라서 다른 PC보다 이 PC에서 먼저 깨진다.
  - 또 main 작업 트리의 `.gitattributes`가 수정된 상태라서, f708bee(같은 파일 끝부분 변경)를 병합할 때 병합이 거부되거나 충돌한다.
- 권장 조치(메인 세션, 결과 전): 통합·병합 커밋에 두 감사 원문의 `-text` 줄을 넣는다. 그다음 원문을 바이트 그대로 커밋하고 `git ls-files --eol`(i/lf, attr/-text)과 sha aeb481ea·2c02dc9e를 대조한다.

### [기록][R] A-5. F-1 처리는 원문과 맞다. 원판·rev1~rev3과 모순이 없고, 그 밖의 기준은 바뀌지 않았다
- G1 대체: rev4 `:39`는 R-a 1,102 = 910 + 192, R-c 288 = 192 + 96이다. 원판 `:166-190`의 기대 수와 같다. 원판 `:277`의 "K1 짝 제외" 판정 대상을 전부로 넓혔다. 사용자 결정 (a)(감사 원문 `:227`)와 같다.
- 미달 문구: 원판 `:409` 문구는 유지하고 뜻만 1.1로 읽는다(`:42`). 엄격한 쪽 변경이다.
- W 선정: 원판 5.1 `:287-288`에 "K1 짝 제외"가 글자로 있다. rev4 `:52`는 그것을 다시 적었을 뿐이다. 경로 2 `:1403` `select_w(ra.get("off"), rc.get("off"))`와 같다.
- FLAG (i)·(ii): 원판 `:408`은 팔 범위를 글자로 정하지 않았다("…작은 행"). rev4 `:53`은 끔 팔 + Chrono로 정하고, K1 켬 팔의 얇은 여유는 기록으로만 남긴다. 경로 2 `flags(ra_off, rc_off, chrono, g0)`(`:1352-1373`)와 같다. rev4는 이것을 "바뀌지 않음"이라고 불렀지만, 정확히는 도구 해석을 결과 전에 명문화한 것이다. 등급을 덜 엄격하게 만드는 쪽이 아니므로 허용된다.
- Q6 관계(`:46-48`): 원판 `:127`과 rev3 `:54`의 읽기 차이를 공개했다. 남는 공백(채택 구성 강건 변형 718행이 K1 켬으로 돌지 않음)도 공개했고 V-1/B-V로 처리하게 했다. 앞 감사 F-1의 시나리오와 같다.
- 바뀌지 않은 것: rev4 `:11`의 목록(J1~J11, 문턱, 관문 순서, 기대 수, 점 좌표, 마름모 5.7/3.7/3.6, G0-4 범위·W 자격, d45 1.01, 태그·E-6, G0 재계산, 7절, 등급 정의)을 본문 전체와 대조했다. 본문 1~4절에 이 항목을 바꾸는 문장은 없다. f708bee는 rev1~rev3 파일을 건드리지 않았다(`git show --stat`: `.gitattributes` +2, rev4 두 파일).
- F-8(`:66-72`): 앞 감사 F-8의 세 가지(RULES_SHA256 `:61-65`에 rev3·rev4 없음, `--g0-base` 없을 때 출처 점검 없음, `--expect` sha 손 계산)가 의무 문구로 모두 들어갔다. rev3 3.3 Chrono `k1_order_gate` 비대칭과 함께 적게 했다.
- 경로 2 인용 줄 번호(`1403`, `1433`, `1467-1474`, `1479`, `61-65`)는 사본 46010967에서 확인했다. 맞다.

### [기록][T·I] A-6. F-9 처리: 통합 브랜치를 공개했고 $H_{impl}$를 "통합 브랜치 병합 뒤의 master HEAD"로 다시 정의했다. 원판 2.2의 실행 위치가 엄격해진다. "감사에서 지정"이라는 문구는 고칠 필요가 있다
- rev4 `:76-82`의 공개 내용(`064a498` 11:28:19, `20e8722` 11:28:25, 미커밋 편집 11파일, 결과 0건 — A-1 참조)은 실제와 같다. 통합 worktree HEAD는 20e8722이고 `git status`에 ` M` 12파일이 보인다(재감사 기준 11파일 + `05_tests/data/d8x_existing_case_hashes.json`).
- 원판 `:134`는 "$H_{impl}$ = `d8x-impl` HEAD"였다. rev4는 이를 master HEAD로 바꾼다. 이제 $H_{impl}$와 $M$이 같을 수 있고, 그러면 I-2·I-2b는 사실상 같은 커밋 비교가 된다. 엄격한 쪽 변경이라 허용된다.
- 다만 `:81` "그 커밋 id는 D8x 실행 전 감사에서 지정"은 고친다. 감사자는 지정하지 않는다. 메인 세션이 지정하고 실행 전 감사가 확인한다고 적는 것이 맞다(확인 필요 3).

### [기록][S] A-7. F-3 처리는 맞다. 이미 커밋된 G0 파일 두 개는 `-text`가 붙은 뒤 작업 사본이 "수정됨"으로 보일 수 있다
- f708bee `.gitattributes:39-40`에 `06_analysis/02_control/d8x/** -text`와 `06_analysis/00_dynamics/d8x_g0*.json -text`가 있다. 이 브랜치에서 `git check-attr text`로 본 결과는 다음과 같다.
  - `text: unset`: `d8x_expect_k1.json`, `d8x_points.json`, `ra/ra_x.json`, `rc/hrx_x.jsonl`, `d8x_prelaunch.json`, `d8x_judgement.md`, `sub/deep/x.npz`, `00_dynamics/d8x_g0.json`, `d8x_g0_rev1.json`, `d8x_g0_rev3.json`
  - 규칙 10파일은 seal_check 기준 모두 i/lf, w/lf, `-text`다.
- 통합 worktree에서 `d8x_g0.json`·`d8x_g0_rev1.json`은 `i/lf w/crlf attr/`(보호 없음)이다. G0 worktree 사본의 CR 수는 6,742·7,132다.
  - 병합 뒤 `-text`가 걸리면 기존 CRLF 작업 사본이 인덱스와 달라져 `git status`에 수정됨으로 보일 수 있다. 그러면 원판 I-1의 `status --porcelain` 빈 목록 조건이 실행 시작 때 깨진다.
  - 그런 상태로 다시 커밋하면 blob이 바뀐다. rev1이 인용한 blob `26e90fd0…`는 커밋 3da8daa 기준이라 깨지지 않는다.
- 권장: 병합 뒤 해당 checkout에서 `git status`를 확인한다. 수정됨이면 그 파일을 다시 checkout해서 LF로 맞춘다(메인 세션, 결과 전).
- `d8x_points.json`은 통합 브랜치에서 이미 `i/crlf -text`다. 문제 없다.

### [기록][R] A-8. 구현 시험 전체 실행에서 1건이 실패한 기록이 있다(G-S 관련, rev4 범위 밖)
- `…\scratchpad\d8xfix\unit_full.txt`(11:55:41) 끝: `FAILED 05_tests/unit/test_hydraulics_flow_limit_run.py::test_coupled_batch_rows_and_resume`, "1 failed, 6234 passed, 135 skipped".
- 원판 `:275` G-S 조건 "구현 시험 통과(9.3)". D8x 실행 전 감사에서 이 실패의 원인과 처리를 확인해야 한다. 어느 worktree에서 돌린 것인지는 이 파일만으로 확정하지 못했다([추정] 통합 worktree).

## 규칙↔도구 대조표 (rev4 변경분)

| 규칙 | rev4 | 경로 2(46010967) | 경로 1(35df06c / 통합 편집본) | 결과 |
|---|---|---|---|---|
| G1 판정 대상 원판 `:277` | 전부(`:39`) | `status` = off 팔 fail(`:1467-1474`), `k1_rows_fail` 기록(`:1479`) | `_status_of([off])` + `k1_rows_failed`(`:578-590` / `:584-596`) | 두 도구 모두 F-1을 반영하지 않음 → 판정서 손 적용(`:60-64`). 순서·None은 A-3 |
| 미달 `:409` | 뜻 재정의(`:42`) | `grade` unjudgeable > fail | 같음 | 손 적용이 판정 불가를 덮을 수 있음(A-3) |
| W 5.1 `:287-288` | 바뀌지 않음(`:52`) | `select_w(off, off)` `:1403` | — | 같음 |
| FLAG (i)(ii) `:408` | 끔 팔 + Chrono(`:53`) | `flags(ra_off, rc_off, chrono)` `:1433` | — | 같음(명문화) |
| V-2 `:334` "판정 대상 행" | 언급 없음 | off만(`:1306-1316`) | off만(`:956-966`) | 미확정(A-2) |
| V-1 `:332-333` | 바뀌지 않음 | 짝 288 비교(`:1256-1297`) | 짝 비교(`:940-953`) | 같음 |
| 8 경로 2 범위 | 의무 문구 3개(`:68-72`) | `RULES_SHA256` `:61-65`, `_load_expect` `:1444-1451` | — | 같음 |
| 2.2 $H_{impl}$ `:134` | 통합 병합 뒤 master HEAD(`:81`) | — | — | 엄격 쪽. 지정 주체 문구(A-6) |
| `.gitattributes` | 두 줄(`:86-89`) | — | — | 반영됨(A-7). 감사 원문 줄 빠짐(A-4) |

## 확인 필요
1. (A-2, control-expert 또는 사용자) V-2의 "판정 대상 행"을 rev4의 넓은 뜻(K1 켬 팔 포함)으로 읽을지, 끔 팔로 둘지 결과 전에 덧붙임으로 정한다. 넓은 뜻이면 손 적용 문구가 필요하다.
2. (A-3, control-expert) 손 적용과 도구의 `판정 불가`·`보류` 사이의 우선순위, 그리고 `k1_rows_fail = None`·`k1_rows_failed` 키가 없을 때의 처리를 정한다.
3. (A-6, 메인 세션) $H_{impl}$를 지정하는 주체는 메인 세션이고, 실행 전 감사는 확인만 한다는 뜻인지 확인한다.
4. (A-1, 사용자) 탐침 3건(R-a pitch+ 1행, R-c fdown3.7 VB 끔·켬 2행)을 rev5 공개로 남길지, 실행 전 기록과 판정서 공개 절로 충분하다고 볼지 정한다.

## 위임 필요
- **control-expert**(판정 에이전트): A-1 공개 문구, A-2·A-3 덧붙임(rev5)을 R-a·R-c 결과 전에 봉인하고 다시 감사받는다. 경로 2는 고치지 않는다.
- **python-expert**(선택): 경로 1 `d8x_judge.py`에서 G1에 K1 켬 팔을 넣는다(rev4 `:64`가 허용). 넣는다면 다음도 함께 한다.
  - `k1_rows_failed` 누락 시 종료 2
  - 판정 불가 우선
  - V-2 범위(확인 필요 1의 결정대로)
  - 시험: 켬 팔 fail 1 + 끔 팔 pass → G1 fail, 켬 팔 파일 누락 → 판정 불가, 켬 팔 수 불일치 + fail → 판정 불가
- **메인 세션**
  - A-4: 감사 원문 두 개의 `-text` 줄을 병합 커밋에 넣고 원문을 바이트 그대로 커밋한다.
  - A-7: 병합 뒤 G0 파일 작업 사본의 status를 확인한다.
  - A-8: 시험 실패 원인을 확인한다.
  - A-1: 탐침 파일을 보존하고 sha를 기록한다.

## 메인 세션 권고
- D8x 실행 전 감사(통합 브랜치를 master에 병합한 뒤)에서 볼 것
  - $H_{impl}$ 커밋 id
  - `prelaunch`의 `expected_tags`가 rev3 1절과 같은지
  - `d8x_expect_k1.json` 내용과 sha(rev4 2-3)
  - 끔 팔 `k1_order_gate` False 기록
  - G0 rev3 실행 커밋의 닫힘 blob
  - `git status` 깨끗함(A-7)
  - 구현 시험 전부 통과(A-8)
- 이 감사는 실행을 하지 않았다. 건조 실행(`prelaunch` 등)도 하지 않았다.

## 검사하지 못한 것
- 통합 worktree의 편집 중 경로 1 코드: `_bundle_result`와 `_las_activity`만 읽었다. 테스트와 나머지 편집은 범위 밖이다.
- 탐침 결과를 rev4 작성자나 결정자가 봤는지(transcript 대조)는 확인하지 않았다([추정]).
- `unit_full.txt`의 실행 위치와 실패 원인은 확인하지 않았다.
- `gate_scan.py`는 돌리지 않았다. rev4는 도구를 바꾸지 않았고, 경로 2의 관련 경로(`_bundle`, `count_rows`, `grade`, `invariance`, `flags`)는 직접 읽었다.
- 감사 원문 aeb481ea가 커밋된 뒤의 `ls-files --eol`은 확인하지 못했다. 아직 미추적이다.

## 실행한 검증
- 인터프리터: `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`MKL_THREADING_LAYER=TBB`, 필요하면 `-X utf8`). Python은 모두 PowerShell 도구로 실행했다. 프로젝트 모듈은 import하지 않았다.
- `depcheck.ps1` → STAMP(numpy 2.5.3, pyyaml 6.0.3, git OK)
- `source_guard.py snapshot/verify`(입력 14개: 원판~rev4와 `.sha256` 10개, `.gitattributes`, 재감사 원문, 경로 2 사본 2개)
- `seal_check.py --repo <wt> "06_analysis/02_control/d8x/d8x_rules*.md" --quoted <rev4> --hash-files <재감사 원문> <경로 2 사본>`
  - 5판 모두 raw 일치, `-text`, i/lf·w/lf, CRLF 0, BOM 없음
  - `quoted_unresolved` 2건은 브랜치 이름 `ac6cd65fc4ec57212` 오탐이다
- `timeline.py --rules rev3 rev4 --results <탐침 3> --no-git` → rev3는 탐침보다 앞, rev4는 뒤(`rule_after_results` 3, mtime 근거)
- 직접 해시 `Get-FileHash`(입력 14개, G0 파일 2개)
- 바이트 CR 계수: 재감사 원문, G0 파일 2개
- 한 줄 python: 탐침 R-a 행 필드 조회
- git 조회: `log`, `show --stat`, `show <c>:<path>`, `diff -- .gitattributes`(main), `check-attr`, `ls-files --eol`(통합 worktree), `ls-tree`, `rev-parse`, `worktree list`, `status`, `config --get core.autocrlf`
- 파일 검색: 저장소 전체와 `%TEMP%\claude`에서 D8x 결과 파일 이름 패턴(Get-ChildItem)
- 만든 뒤 지운 것: scratchpad `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\rev4_audit\`(guard.json, seal.md)를 폴더째 지웠다. 남은 부산물은 없다.
- 메모리 `audit_pitfalls.md`에 일반 함정 2줄을 더하고 `MEMORY.md` 색인을 갱신했다.
  - 넓힌 "판정 대상"이 같은 용어를 쓰는 다른 절에 미치는 범위, 손 적용 우선순위와 None
  - 봉인 사이의 구현 탐침
- 최종 판정 직전 확인: rev4·감사 원문·경로 2는 source_guard verify로 불변을 확인했다. 감사 대상 worktree HEAD는 f708bee 그대로이고 status는 깨끗하다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha d8x_rules.md a377b9bb…, d8x_rules.sha256 66837eee…, d8x_rules_rev1.md ad16f452…, d8x_rules_rev1.sha256 7aebedc5…, d8x_rules_rev2.md 5f3fa620…, d8x_rules_rev2.sha256 52a42789…, d8x_rules_rev3.md 2318fb5c…, d8x_rules_rev3.sha256 4b6ea235…, d8x_rules_rev4.md 5233c517…, d8x_rules_rev4.sha256 fc118b10…, .gitattributes 8ad6ec28…, las_k1_adopt_rev1_d8x_rev3_audit.md aeb481ea…, d8x_recount.py 46010967…, test_d8x_recount.py 906f899c…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음

---

## 메인 세션 덧붙임 (2026-11-10)

- A-4: 감사 원문 두 개와 `-text` 줄은 이 감사 도중 master c731f4b로 커밋됐다(`i/lf w/lf attr/-text`, sha 2c02dc9e·aeb481ea 유지). 규칙 브랜치 병합 때 `.gitattributes`를 합친다.
- A-8: 실패 1건은 worktree에 git 제외 폴더 `07_results`가 없어서 생긴 것으로 구현 에이전트가 보고했다(junction 연결 뒤 통과). 실행 전 감사에서 main checkout 기준으로 다시 확인한다.
- 사용자 결정(2026-11-10): A-1 rev5에 탐침 3건 공개(파일은 `.local_archive/session_6f3ebc4d_20261110/d8x_probes/`에 sha와 보존), A-2 (b) V-2도 K1 켬 팔을 센다(판정서 손 적용, 경로 1은 고쳐도 됨), A-3 문구는 control-expert에 맡김(rev5 초안 확인), A-6 "$H_{impl}$는 메인 세션이 지정하고 실행 전 감사가 확인".
