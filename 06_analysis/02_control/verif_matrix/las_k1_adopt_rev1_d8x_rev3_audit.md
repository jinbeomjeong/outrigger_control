<!-- verif-protocol-auditor 리포트 원문(2026-11-10). 대상: adopt rev1 전환 후 재감사 + D8x rev3 봉인 점검, 브랜치 worktree-agent-a9a55327c173a8e3e 커밋 589ff43. 메인 세션이 편집 없이 저장. 결정은 맨 끝 "메인 세션 덧붙임" 절에만 쓴다. -->

# K1 adopt rev1 `[시점] 전환 후` 재감사 + D8x rev3 봉인 점검 (verif-protocol-auditor, 2026-11-10)

## 감사 요약
- 대상: 브랜치 `worktree-agent-a9a55327c173a8e3e`, 커밋 `589ff43`(2026-11-10T11:36:37+09:00). 구성은 `b53d890` + d8x-rules 병합 `1899d5c` + 개정판 2개. `git diff --stat b53d890 589ff43`로 보면 11파일이 바뀌었고, 모두 규칙·봉인 파일과 `.gitattributes` 1줄이다. 코드 변경은 없다.
- 기준 문서(seal_check에서 raw 일치)

| 묶음 | 판 | 봉인 시각 | sha 앞 8자리 |
|---|---|---|---|
| las_k1_rules_adopt | 원판 | 2026-11-09 22:05:43 | 864836d8 |
| las_k1_rules_adopt | rev1 | 2026-11-10 11:36:17 | 730dbb3d |
| las_k1_rules_adopt2 | 원판 | 2026-11-09 23:03:15 | fb3a5696 |
| las_k1_rem_judgement.md | 판정서 | 커밋 15777d1 09:12:34 | 4c509d15 |
| las_k1_switch_post_audit.md | main checkout, 미추적 | mtime 11:25:35 | 2c02dc9e |
| d8x_rules | 원판 | 2026-11-10 02:19:14 | a377b9bb |
| d8x_rules | rev1 | 02:53:21 | ad16f452 |
| d8x_rules | rev2 | 03:10:48 | 5f3fa620 |
| d8x_rules | rev3 | 11:36:17 | 2318fb5c |
| 경로 2 `d8x_recount.py` | 사본 | mtime 09:13:45 | 46010967 |
| `test_d8x_recount.py` | 사본 | — | 906f899c |

- **판정: 차단 0 / 실행 전 수정 3 / 기록 9**
  - adopt rev1: 규칙 범위 안이다. 기준·문턱·등급은 바뀌지 않았고, 결과 뒤 개정이라는 공개도 충분하다. 확정해도 된다.
  - D8x rev3: 봉인·LF·`-text`·시간 순서에 문제가 없다. 경계·관문 순서·기대 수·W 자격도 바뀌지 않았다. 다만 실행 전 수정 1건(F-1, 채택 구성 행이 관문 밖에 있음)은 **R-a·R-c 결과가 하나라도 나오기 전에** 사용자 결정과 덧붙임판으로 닫아야 한다. 결과가 나온 뒤에 고치면 결과 뒤 개정이 된다.

## 발견 사항 (심각도순)

### [실행 전 수정][R·E] F-1. D8x: 전환 뒤 채택 제어기(K1 켬)의 하네스 행이 관문 G1 밖에 있다. 그 행이 실패해도 등급은 최대 "조건부 통과"까지만 내려간다
- 근거
  - 원판 `d8x_rules.md:277` G1: "판정 대상(K1 짝 제외 R-a 910, R-c 192)이 모두 `pass`. K1 짝 행도 J1~J11은 판정함". `:409` 미달 = "판정 대상 행 하나라도 `fail`".
  - rev3 `d8x_rules_rev3.md:40-43`: 판정 대상 910·192를 **K1 명시적 끔**으로 돌린다. 채택 구성(K1 켬)은 R-a-K1 192·R-c-K1 96뿐이다. `:48`이 이를 "원판 구조 그대로"라고 적는다.
  - 경로 2(고정): `d8x_recount.py:1467-1474`는 묶음 `fail`을 `parts["off"]`로만 정한다. `:1479` `k1_rows_fail`은 기록뿐이다. `:1403` W 선정은 `select_w(ra.get("off"), rc.get("off"))`이고, `:1433` FLAG (i)·(ii)도 off 팔만 본다.
  - 경로 1(`d8x-impl` 35df06c): `d8x_judge.py:582-589`도 K1 켬 행의 실패를 `k1_rows_failed` 목록으로만 남긴다.
  - 원판 `:127` "`with_10hz_d1()`를 덮어쓰지 않고 그대로 쓴다. 실행 시점의 기본 프리셋이다(Q6)". 전환 뒤 이 문구를 글자대로 읽으면 판정 대상 팔이 K1 켬이어야 한다. rev3 `:54`는 "원판의 K1 끔 팔은 봉인 시점 프리셋을 뜻했다"는 다른 읽기를 택했다. 이 충돌(Q6 "실행 시점")은 rev3에 언급되지 않았다.
- 실패 시나리오
  - V-1에서 어떤 점의 K1 켬·끔 명령 해시가 다르고(`K1_DEPENDENT`), 그 점의 K1 켬 행이 J1 등에서 `fail`이라고 하자. 끔 팔은 통과하므로 G1은 통과한다.
  - 등급은 FLAG (iii) 때문에 `조건부 통과`가 된다. 채택 제어기의 실패가 `미달`로 나오지 않는다.
  - 채택 제어기의 강건 변형(td_robust 448, td_kt 126, 중·하단 144)은 K1 켬으로 한 번도 돌지 않는다. 이 변형들은 V-1(td_main 짝)의 불변성에만 기대고 있다.
  - rev3 6절의 예상대로 강체 지면에서 관문이 작동하지 않으면(`K1_INVARIANT`) 두 팔의 J 결과가 같으므로 결론은 맞다. 잠재 결함이다.
- 권장 조치(확인 필요 1 → 판정 에이전트 control-expert가 rev4를 결과 전에 봉인. 경로 2는 고정이라 처리 문구만 추가)
  - (a) K1 켬 팔 행의 `fail`도 G1 실패로 본다(채택 구성 = 판정 대상). 또는
  - (b) `K1_DEPENDENT` 점에 K1 켬 `fail`이 하나라도 있으면 `조건부 통과`가 아니라 B-V 정지(사용자 질문)로 둔다.
  - 어느 쪽이든 경로 2는 바뀌지 않는다. 판정서가 `k1_rows_fail`(경로 2 `:1479`)과 `k1_rows_failed`(경로 1)를 읽어 손으로 적용하는 문구가 필요하다.

### [실행 전 수정][S] F-2. adopt rev1이 sha로 인용한 감사 원문이 이 브랜치에서 `-text`로 보호되지 않는다
- 근거
  - `las_k1_rules_adopt_rev1.md:8,70,72`가 감사 원문 raw sha `2c02dc9e…`를 근거로 인용한다. rev3 `:18`도 같다.
  - 파일은 main checkout에서 미추적이다. CRLF 255줄 / 255줄이고 BOM은 없다.
  - main checkout의 `.gitattributes`에는 **커밋하지 않은 변경**(` M`)으로 `:37 06_analysis/02_control/verif_matrix/las_k1_switch_post_audit.md -text`가 있다. 그래서 main에서는 `text: unset`이다.
  - 이 브랜치(589ff43)에서 `git check-attr text -- …/las_k1_switch_post_audit.md`를 보면 `unspecified`다. 브랜치의 `.gitattributes` 변경은 `d8x_rules* -text` 1줄뿐이다.
  - `core.autocrlf=true`이다.
- 실패 시나리오
  - 589ff43을 master에 병합할 때 `.gitattributes`가 다시 충돌하거나, main 작업 트리의 미커밋 변경 때문에 병합이 거부될 수 있다.
  - 감사 원문을 보호 줄 없이 커밋하면 인덱스는 LF가 된다. LF 체크아웃(다른 PC, autocrlf false·input)에서는 raw sha가 `2c02dc9e`와 달라진다.
- 권장 조치(메인 세션): 병합할 때 `.gitattributes`에 보호 줄을 커밋으로 넣는다. 그다음 감사 원문을 바이트를 바꾸지 않고 커밋하고, `git ls-files --eol`(i/crlf)과 sha를 대조한다.

### [실행 전 수정][S·T] F-3. D8x 판정서가 sha로 인용할 새 산출물에 `-text` 보호가 없다
- 근거: rev3 `:96`은 `d8x_expect_k1.json`의 sha256을 판정서에 적으라고 한다. `:107`은 `06_analysis/00_dynamics/d8x_g0_rev3.json`을 출력으로 둔다. 원판 `:370,377`의 `d8x/rc/hrx_*.jsonl`·`d8x/ra/ra_*.json`도 같다. 589ff43에서 `git check-attr text`를 보면 다섯 경로 모두 `unspecified`다. `.gitattributes:38`은 `d8x_rules*`만 덮는다.
- 실패 시나리오: 결과를 커밋하거나 다른 checkout에서 판정서의 인용 sha가 맞지 않는다(봉인 판정의 근거 파일).
- 권장 조치(메인 세션, D8x 실행 전 감사 전): `06_analysis/02_control/d8x/** -text`, `06_analysis/00_dynamics/d8x_g0*.json -text`를 결과 전에 커밋한다.

### [기록][R] F-4. adopt rev1이 감사 R-1·R-4·R-6·R-8·R-9·W-2를 처리한 방식은 원문과 맞고, 원판 기준·문턱을 바꾸지 않았다
- R-1: rev1 `:45-51`. G-7 "새 실행 없음"은 그대로 두고 근거만 바꿨다.
  - 원판 `las_k1_rules_adopt.md:342`의 근거는 S-Ch gateon 1행이었다. rev1의 근거는 REM R7·R8 + F2다.
  - 인용 값은 원본에서 다시 확인했다.
    - R7·R8 result.json: `expect_controller` `final_C4G2_P3_LAS`, `k1_order_gate` `on`, 관문 설정 True.
    - decision: R7 (dP 99, due True, applied True). R8 (198, True, True), (0, False, False).
    - npz sha(직접 해시): R1·R7 `ebf86d1d40af464e…`, R4·R8 `97aace614a534a6a…`로 짝끼리 같다.
    - REM 판정서 `:8-11, :96-97, :137-140, :264`와도 같다.
  - S-Ch는 기록으로 남겼다(`:51`).
  - 근거 교체 결정은 REM 판정서 `:426`(13절 #3)에 **전환 구현 전에** 이미 있었다(커밋 15777d1 09:12:34 < b0979d1 10:50:42). 봉인만 뒤에 왔다.
- R-4: rev1 `:62-66`.
  - `run_S8C.py:1389` `LAS_OFF_PRESET`(`…flat_soil_margin_order_gate=False`) 인용이 실제 코드와 같다.
  - 원판 9.1이 `--las-off`를 정하지 않았으므로 보충으로 볼 수 있다.
- R-6: rev1 `:80-84`. 완료 시각 10:51:14, 커밋보다 32 s 뒤, 소스 마지막 mtime 09:59:09. 감사 원문 `:114-121`과 같다. 앞으로 지킬 규칙(증거 파일 마지막 쓰기 뒤에 커밋)도 더했다.
- R-8: rev1 `:74-78`.
  - 원판 G-2의 합격 조건 "기존 단위 시험의 명령·메타 해시가 같다"를 G-1 통과로 충족했다고 읽었다. 같은 조건이다.
  - `test_c2_k1.py:84-86`이 클래스 기본 False·프리셋 True를 단정한다.
  - `C2Config()` 해시 시험 파일(`test_c2_returned_clip.py` 등)이 있다.
- R-9: rev1 `:86-90`. 원판 `:341`의 의무 문구("재실행 필요 시 새 태그로")를 넣었고, 첨부는 9.6 단계로 미뤘다.
- 원판 6.2 등급 표, 9.1~9.3·9.5는 손대지 않았다(rev1 `:92-96`).

### [기록][R] F-5. W-2 대체(rev1 2.2): 감사가 만든 표를 9.2 산출물로 갈음했다. 원문은 그대로지만, 9.2의 "전부 git grep" 요건과 9.5의 독립 점검은 약해졌다
- 근거
  - 감사 원문 본문을 감사자 SubagentHandback 원문(transcript `agent-aef914eb47679ec85.jsonl`)과 비교했다. 빈 줄을 빼고 줄 단위로 보면 214줄 대 214줄, 차이 0이다. 원문 그대로 저장됐다.
  - 원판 `las_k1_rules_adopt.md:316`은 "태그 소비자 전부를 `git grep`으로 나열"을 요구한다. 589ff43에서 태그 패턴을 `git grep`한 결과 22파일(시험 제외)이 나왔다. 감사 표에 없는 파일은 두 개다.
    - `las_rev_targeted.py:33-34`: 옛 태그가 아니면 묶음을 멈춘다. 크게 실패한다.
    - `b5_baseline_compare.py`: 이름 상수이고 태그 소비자가 아니다. R-7에서만 다뤘다.
  - 9.5("감사가 그 표를 본다")는 감사가 자기 표를 다시 보는 구조가 됐다.
- 영향: 빠진 곳이 조용한 실패가 아니어서 결론은 그대로다.
- 권장: 9.6 문서나 다음 단계 실행 전 감사에서 `las_rev_targeted`를 "크게 실패" 행으로 덧붙인다(메인 세션).

### [기록][R] F-6. adopt rev1 2.1의 사용 제한은 규칙을 넓히지 않는 보수 쪽 제한이라 허용된다. 다만 강제하는 장치가 없고, V0 행의 "기대 태그 `final_C4G2_K1`"은 run_S9로 표현할 수 없다
- 근거
  - rev1 `:66`. `run_S9.py:6355` `--expect-controller`의 `choices=tuple(CONTROLLER_EXPECTATIONS)`이다(`:1548-1556`, 7개 키). `final_C4G2_K1`·`final_C4G2_P3_K1`은 없다. 이 태그를 넘기면 argparse가 종료 2로 끝낸다(크게 실패).
  - 사용 제한은 코드가 막지 않는다. rev1 `:96`이 W-1·W-3 처리를 다음 단계의 실행 전 조건으로 넘겼다.
- 권장: 다음 단계(LAS-b P5r4+K1) 규칙과 그 실행 전 감사에서 다음을 점검 항목으로 둔다(판정 에이전트·메인 세션).
  - 이 조합 행이 있는가.
  - 있다면 기대 태그를 무엇으로 점검하는가: 판정 도구 쪽인지, run_S9 choices 추가(python-expert)인지.

### [기록][R] F-7. adopt rev1이 감사 원문 끝의 세 번째 사용자 결정(무결성 Medium `las_targeted._turn_preset_las_off` 관문도 끔)을 다루지 않는다
- 근거
  - 감사 원문 `:255`. rev1의 "사용자 결정"(`:26-28`)에는 R-1·W-1만 있다.
  - 589ff43 `04_scripts/04_hydraulic/coupled/las_targeted.py:481-495`는 아직 `liftoff_approach_slow=False`만 되돌린다.
- 판정에는 영향이 없다(adopt 규칙 범위 밖, 구현 미완).
- 권장: W-1과 함께 다음 단계 실행 전 조건 목록에 넣는다(python-expert 구현, 메인 세션 추적).

### [기록][R·C] F-8. D8x 경로 2의 비대칭은 rev3이 공개한 것(Chrono `k1_order_gate` 미점검) 말고도 세 가지가 더 있다
- 근거(경로 2 사본, sha `46010967` 확인)
  1. 규칙 봉인 대조 `RULES_SHA256`(`:61-65`)에 원판·rev1·rev2만 있다. `--rules-dir`(`check_rules_dir`, `:414-424`)는 **rev3의 sha를 보지 않는다**.
  2. `judge_g0`(`:432-501`)는 `--g0-base`가 없으면 출처 점검을 하지 않는다. 출처 점검이란 재사용 0 / 재계산 60, `meta.rules_rev`, 실행 커밋 닫힘 blob이다. rev3 `:97`이 `--g0-base`를 주지 말라고 정했으므로, rev3 4절의 G0 출처 요건은 경로 1만 본다.
  3. `--expect` 파일은 `source` 경로만 기록된다(`:1447`). 파일 sha는 경로 2가 내지 않는다. rev3 `:96`의 "결과 전 작성 + sha 판정서 기재"는 손으로 해야 한다.
- 그 밖에 rev3 3.3의 코드 읽기를 확인했다.
  - `DEFAULT_EXPECT` `:165-171`.
  - `FORBIDDEN_TAGS` `:172`.
  - `_load_expect`는 최상위 키를 통째로 바꾼다(`:1444-1451`).
  - 하네스 `k1_order_gate is (k1 == "on")`(`:704`, `:842`).
  - Chrono는 태그·LAS-b만 본다(`:1053-1056`).
  - `--g0-base`의 차이는 판정 불가로 들어간다(`:493-495`).
  - 모두 rev3 서술과 같다.
- 권장: 판정서 "두 경로 범위 차이" 절에 위 세 가지를 적는다(control-expert). 경로 2는 고치지 않는다.

### [기록][T] F-9. D8x rev3 봉인 전에 통합 브랜치가 있었고 그 구현 편집이 이미 시작돼 있었다. 결과는 0건이다
- 근거
  - `worktree-agent-ac6cd65fc4ec57212`의 `064a498`(11:28:19)은 d8x-impl을 K1 전환 위에 병합한 커밋이다. `20e8722`(11:28:25)는 G0 rev1(e37f42c)을 병합했다.
  - 그 worktree의 미커밋 편집 11파일(`d8x_record.py` 11:30:58 ~ `d8x_spec.py` 11:35:52)은 rev3 봉인(11:36:17)보다 앞선다.
  - rev3 `:103` "G0 단계 코드는 master·`d8x-impl` 어디에도 병합돼 있지 않다"는 글자로는 참이다. 하지만 이 통합 브랜치는 언급하지 않는다.
  - R-a·R-c·Chrono 결과(`ra_*`, `hrx_*`, `D8X_*`, `d8x_g0_rev3.json`, `d8x_prelaunch*`, `d8x_expect*`)는 main 06·07, 모든 worktree의 d8x·00_dynamics 폴더, 오늘 날짜 scratchpad 전체에서 0건이었다. 그래서 rev3 `:20` "결과 0건"은 성립한다.
  - rev3 `:102` blob을 확인했다(`git rev-parse <c>:03_src/outrigger_sim/control/target.py`).
    - e37f42c·3da8daa·b53d890·589ff43: `a786935…`
    - 35df06c: `f4d490e…`
    - `d8x_g0_rev1.json:31,186`에 target.py가 닫힘 목록으로 들어 있다. 재사용 조건이 깨졌다는 판단은 맞다.
  - 재계산 60은 기존 재사용 33 + 27보다 엄격한 쪽이다. G0 rev1 값을 본 뒤에 정했지만, 결과를 골라 쓴 것이 아니다.
- 권장: D8x 실행 전 감사 때 통합 브랜치 HEAD를 $H_{impl}$로 쓰는지 밝히고, 판정서 시간 순서 절에 적는다(메인 세션).

## 규칙↔도구 대조표

### adopt rev1

| 원판·감사 | rev1 처리 | 결과 |
|---|---|---|
| 9.4 G-7 `adopt.md:342` | 대체 `rev1:45-52`. REM R7·R8·F2. 값은 result.json·npz에서 다시 확인 | 같음. 기준 불변 |
| 9.6 인용 `adopt.md:355` "판정 `las_k1_rules_adopt.md`"(제안 문구) | 대체 `rev1:54-58`. REM 13 #3·#5와 같음 | 허용(문서 제안 문구) |
| 9.1 + 감사 R-4 | 보충 `rev1:62-66`. `run_S8C.py:1389` 같음 | 같음. 사용 제한은 강제 장치 없음(F-6) |
| 9.2 표 + W-2 | 감사 원문 표로 갈음 `rev1:68-72` | 원문 그대로 확인. 전수성은 F-5 |
| 9.4 G-2 + R-8 | `rev1:74-78` | 같은 조건으로 읽음 |
| 9.4 G-5 + R-6 | `rev1:80-84` | 같음 |
| 9.4 G-6 + R-9 | `rev1:86-90` | 같음. 첨부는 9.6 |
| 6.2 등급, 9.3, 9.5 | 그대로 `rev1:92-96` | 같음 |

### D8x rev3

| 원판·rev 절 | rev3 | 결과 |
|---|---|---|
| 기대 수 `d8x_rules.md:166-190` | 910 + 192 / 192 + 96 / 19 / 60 (`rev3:38-45`) | 같음 |
| 관문 순서 `:271-282` | 바꾸지 않음(`:10`, `:111`) | 같음. 판정 대상 팔의 뜻은 F-1 |
| 마름모·W 자격·G0-4 범위(rev1·rev2 3) | `:10`, `:108` | 같음 |
| 2.1 "덮어쓰지 않음" | K1 한 키만 명시 설치(`:52-58`). 같은 값은 멱등, 다른 값은 오류 | 허용. 지금 impl `d8x_record.py:108-116`은 끔 = 설치 없음 → rev3 5가 고치라고 지시 |
| E-6 `:324`, rev2 4 | E-6a~f(`:62-73`). 필터는 완전 일치 | 같음(`is_order_gate_tag`는 `endswith("_K1")`이지만 E-6a 완전 일치가 먼저라 무해) |
| 8 경로 2 | 고치지 않음, `--expect`, `--g0-base` 없음(`:79-97`) | 코드와 같음. 비대칭 F-8 |
| rev1 3 G0 재사용 | 전체 재계산(`:99-111`) | 조건이 깨졌음을 blob으로 확인 |

## 확인 필요
1. (F-1, 사용자 또는 control-expert) 전환 뒤 D8x의 "판정 대상" 팔을 어떻게 볼지 정한다.
   - 원판 Q6 "실행 시점의 기본 프리셋"으로 읽으면 K1 켬 팔이 채택 구성이다. 이 팔의 `fail`을 G1 실패로 볼지, 아니면 `K1_DEPENDENT` + K1 켬 `fail`을 B-V 정지로 둘지 정한다.
   - R-a·R-c 결과가 나오기 전에 rev4로 봉인해야 한다.
2. (F-6) "LAS-b 단일 변수 짝"(`--las-off --k1-order-gate on`)을 다음 단계 실험 설계에 쓸지 정한다. 쓴다면 run_S9 `--expect-controller` choices에 `_K1` 조합 태그를 더할지(W-1 수정과 함께) 정한다.

## 위임 필요
- **control-expert(판정 에이전트)**
  - F-1 rev4: 결과 전에 봉인하고 다시 감사받는다.
  - F-8: 판정서의 두 경로 범위 차이 문구를 쓴다.
- **python-expert**
  - W-1(사용자 결정 (a))과 F-7 `las_targeted._turn_preset_las_off`의 관문 끔을 다음 단계 실행 전에 처리한다.
  - rev3 5절 구현 위치를 처리한다. 특히 `d8x_record.py:108-116` "K1 off installs nothing"은 전환 뒤 끔 팔을 켬으로 만든다. 통합 worktree에서 이미 편집 중이다.
  - F-6에서 필요하면 run_S9 choices를 고친다.
- **메인 세션**
  - F-2: 병합 때 `.gitattributes`에 감사 원문 `-text` 줄을 커밋하고, 감사 원문을 바이트 그대로 커밋한다.
  - F-3: `d8x/** -text`, `00_dynamics/d8x_g0*.json -text`를 결과 전에 커밋한다.
  - F-5: `las_rev_targeted`를 소비자 표에 덧붙인다.
  - F-9: $H_{impl}$를 지정한다.

## 메인 세션 권고
- D8x 실행 전 감사(구현 병합 뒤)에서 볼 것:
  - `d8x_judge.py prelaunch`의 `expected_tags`가 rev3 1절 표와 같은지
  - 끔 팔 행 기록 `k1_order_gate` False
  - `d8x_expect_k1.json`의 내용과 sha
  - G0 rev3의 실행 커밋 닫힘 blob
- 이 감사는 결과를 쓰는 실행을 하지 않았다. `prelaunch`·`check-sources` 같은 건조 실행도 하지 않았다.

## 검사하지 못한 것
- D8x 구현(통합 worktree `agent-ac6cd65fc4ec57212`의 편집 중 파일)은 범위 밖이다. 구현 병합 뒤 실행 전 감사에서 본다.
- 경로 1 `d8x_judge.py`는 35df06c 판의 해당 줄(`:197-208, :555, :582-589, :632-634`)만 읽었다. 통합 브랜치의 새 판은 보지 않았다.
- 감사 원문이 커밋된 뒤의 `ls-files --eol`은 확인하지 못했다. 아직 미추적이다.
- `las_rev_targeted`·`b5_baseline_compare` 밖의 태그 소비자는 패턴 `final_C4G2|_LAS"|"_LAS|ABL_LAS|endswith("_LAS|EXTEND_START_TAGS|P3_CONTROLLER_TAGS|LAS_CONTROLLER`로만 찾았다. 문자열을 조립하는 소비자는 빠질 수 있다.

## 실행한 검증
- 인터프리터: `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`MKL_THREADING_LAYER=TBB`, 필요하면 `-X utf8`). Python은 모두 PowerShell 도구로 실행했고, 프로젝트 모듈은 import하지 않았다.
- 실행한 도구
  - `depcheck.ps1` → STAMP
  - `source_guard.py snapshot/verify`(입력 17개)
  - `seal_check.py --repo <wt> "…/las_k1_rules_adopt*.md" "…/d8x_rules*.md" --quoted <rev1> --hash-files <REM 판정서> <adopt2> <감사 원문>`
    - 7판 raw 일치, `-text`·i/lf·w/lf·CRLF 0·BOM 없음
    - `quoted_unresolved` 2건은 npz 해시다. 원본 npz를 직접 해시해 확인했다.
  - `seal_check.py --repo <wt> "…/d8x_rules*.md" --quoted <rev3> --hash-files <경로 2 사본 2개>`
    - 4판 raw 일치
    - `quoted_unresolved` 5건은 브랜치 이름 오탐 1, 첫 실행에서 풀린 판정서·감사 sha 2, git blob id 2다. blob은 `git rev-parse`로 확인했다.
  - `timeline.py --rules adopt 원판·rev1·adopt2 --results R7·R8 result.json` → rev1은 결과 뒤 개정이고 그렇게 공개함(`rev_after_results_declared`). 결과 시각 근거는 mtime뿐이다([추정]).
- git 조회: `log`, `diff --stat`, `show`, `rev-parse <c>:<path>`, `branch --contains`, `merge-base --is-ancestor`, `worktree list`, `check-attr`, `status`, `grep`
- 직접 해시: `Get-FileHash`(REM `controller_commands.npz` 7개, 경로 2 사본 2개)
- 한 줄 python: R7·R8 result.json의 태그·인자·관문·decisions 조회
- 즉석 스크립트
  - `hb_diff.py`: 감사 원문 ↔ SubagentHandback 원문 비교. 차이 0.
  - scratchpad `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\rev_audit\`(guard.json, seal 보고서 2개, hb_diff.py 포함)는 보고 전에 폴더째 지웠다. 남은 부산물은 없다.
- 감사 대상 worktree는 `git status` 깨끗, HEAD 589ff43 그대로다.
- 메모리 `audit_pitfalls.md`에 일반 함정 3줄(전환 뒤 채택 팔이 관문 밖에 남음, 경로 2의 다른 비대칭, main checkout에만 있는 `-text` 줄)을 더하고 `MEMORY.md` 색인을 갱신했다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha las_k1_rules_adopt.md 864836d8…, las_k1_rules_adopt.sha256 fddf01a3…, las_k1_rules_adopt_rev1.md 730dbb3d…, las_k1_rules_adopt_rev1.sha256 35f49811…, las_k1_rules_adopt2.md fb3a5696…, las_k1_rem_judgement.md 4c509d15…, las_k1_switch_post_audit.md 2c02dc9e…, d8x_rules.md a377b9bb…, d8x_rules.sha256 66837eee…, d8x_rules_rev1.md ad16f452…, d8x_rules_rev1.sha256 7aebedc5…, d8x_rules_rev2.md 5f3fa620…, d8x_rules_rev2.sha256 52a42789…, d8x_rules_rev3.md 2318fb5c…, d8x_rules_rev3.sha256 4b6ea235…, .gitattributes 1274ba85…, d8x_recount.py 46010967…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음

---

## 메인 세션 덧붙임 (2026-11-10)

- (결정 기록 자리. 아래에 사용자 결정을 덧붙인다.)
- 사용자 결정(2026-11-10 12시경)
  - F-1: (a) K1 켬 팔 행(R-a-K1 192, R-c-K1 96)의 `fail`도 G1 실패로 본다. D8x rev4를 R-a·R-c 결과 전에 봉인하고 재감사한다.
  - F-6: run_S9 `--expect-controller`에 `final_C4G2_K1`·`final_C4G2_P3_K1`(LAS 꺼짐 + 관문 켬)을 코드로 지원하되, 지금 실험 설계에는 쓰지 않는다.
  - F-2·F-3: 메인 세션이 `-text` 줄을 결과 전에 커밋한다.
