# LAS-b T-3 도구의 K1 전환 대응: 실행 조건·기준선·개정 필요 판단 (설계 메모)

- 작성: control-expert, 2026-11-10. **설계 판단만 했고 시뮬레이션은 돌리지 않았다.** 저장 파일 읽기 스크립트 3개만 돌렸다(아래 0.2).
- 대상 도구(master `c6ac251` 병합본, 이 worktree HEAD `ba6671c`): `04_scripts/04_hydraulic/coupled/las_t3.py`, `las_t3_dg3.py`, `las_t3_judge.py`, `las_h7.py`
- 관련 봉인 규칙: `las_targeted_rules_rev3.md`(+`_rev3_keys.json`), `rev4.md`, `rev4a.md`~`rev4c.md`, decision_log 551~609행. K1 전환은 명세 437, 근거는 `las_k1_rules_adopt2.md`·`las_k1_rem_judgement.md`·`las_k1_rules_adopt_rev1.md`
- 이 메모는 봉인 문서가 아니다. 결정이 나면 아래 3절 골자로 개정판을 써서 봉인한다.

## 0. 규약과 근거

### 0.1 이름과 규약

| 기호·이름 | 뜻 |
|---|---|
| LAS-b b0 | 이륙 접근 감속(명세 436). 지금 R8 프리셋에서 켜져 있다 |
| 관문(K1) | R4c30 평탄 시작 순서 관문 `slope_clearance_margin.flat_soil_margin_order_gate`(명세 437). 프리셋은 켬, 클래스 기본은 꺼짐. 하네스 키 안의 `K1`(크롤러 강성 ×1)과는 **다르다** |
| R4c30 | 평지 토양 LOC의 틈 목표 +30 mm(사건 `INFO_LOC_FLAT_SOIL_MARGIN`) |
| `would_block` | 관문이 R4c30을 막은 결정. `controller_meta.slope_clearance_margin.order_gate.decisions[*].would_block`(관문 꺼짐에서도 그림자로 남는다) |
| 저장 기준 | `v5/d1.jsonl`(sha256 `9039b36a…707f`, 868줄): LAS-b 끔, 관문 꺼짐, 태그 V0 없음 / VB `final_C4G2_P3`. dg3는 키 목록의 저장 T4h 해시 |
| 작동 | 그 줄의 제어기 사건에 `INFO_LIFTOFF_SLOW`(시작 사건)가 하나 이상 있다(rev3 3절) |

- C2는 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1, 음되먹임이고, 명령 $u$는 다리 행정 속도 [m/s]다(+ = 신장). 이 메모는 명령 해시(`commands_sha256`)와 판정 항목만 다룬다. 루프 이득·여유는 바뀌지 않는다.

### 0.2 이 메모에 쓴 계산(읽기 전용, scratchpad `t3k1\`)

| 스크립트 | 읽은 것 | 결과 |
|---|---|---|
| `keys_peek.py` | `las_targeted_rules_rev3_keys.json` | T-3a 228 = H-S-0 216 + H-S-1 12. T-3c 76 = H-S-A 72 + H-S-A-J2 4. T-3b 4 = dg3 G1 2키 × {off, v4_on}. R-0 = D-1 5 + dg3 2 |
| `r0k_set.py` | 위 + main checkout의 `v5/d1.jsonl` `event_names` | T-3 D-1 키 가운데 저장 줄에 `INFO_LOC_FLAT_SOIL_MARGIN`가 있는 키는 **41개**(T-3a 39, T-3c 5. R-0 S1 키가 T-3a에도 있어 단순 합계는 42). 여기에 R-0 D-1 5키를 합친 집합이 **45키**다(T-3a 39 + T-3c 6). 목록 sha256(LF 연결, 끝 LF) `9399c4922828973fe5129c6c5964dc2cf6c53137a8858d1f92e69f9c85452e3c` |
| `r0k_cost.py` | `d1.jsonl` `wall_s` | 45키의 저장 벽시계 합 7,323 s(약 2.0 CPU·h, 최대 283.5 s). T-3 D-1 304키는 45,828 s |

- `events` 목록은 잘려 있다(INFO가 빠짐). 그래서 R4c30 적용 여부는 `event_names` 개수로 본다. 구현 때 같은 정의를 쓴다.
- dg3 4기록의 저장 결과 JSON에서는 R4c30 흔적이 보이지 않았다. 하지만 사건 목록은 T4h 메타 `events`에 있으므로 구현 때 그것으로 다시 확인한다(4.2 #1의 시험 T1-c).

## 1. 결정안

### 1.1 T-3 실행 조건 = 관문 켬(채택 제어기). 관문 끔은 쓰지 않는다

| 선택지 | 내용 | 판단 |
|---|---|---|
| **A. 관문 켬(추천)** | 지금 프리셋 그대로(LAS-b b0 + 관문 켬)로 돈다. 태그는 `final_C4G2_LAS_K1` / `final_C4G2_P3_LAS_K1` | 사용자 결정("판정 묶음은 새 `_K1` 태그로 재실행")과 명세 437.4("그 밖 저장 결과를 다시 돌릴 때는 새 태그로")에 맞는다. T-3의 결론은 재개 검증(436.8)의 전제인데, 재개 검증은 채택 제어기로 한다. 그래서 T-3도 같은 제어기여야 쓸모가 있다 |
| B. 관문 끔 | `pre_k1_preset_runner.py`로 돌리고 rev3 태그(`_LAS`)를 그대로 쓴다 | 도구 변경은 가장 작다. 하지만 결과가 채택되지 않은 제어기의 것이 된다. rev3 2.2·H-T3-0의 "래퍼 없음"에도 걸려 어차피 개정이 필요하다. **기각** |

### 1.2 기준선: R-0은 관문 끔으로 고정하고, 관문 켬 LAS-b 끔 짝 R-0K를 더한다

관문을 켜면 T-3 줄과 저장 기준(LAS-b 끔·관문 꺼짐) 사이에 변수가 둘 바뀐다. K-5(미작동 해시 = 기준)와 K-6(작동 줄의 판정 비교)이 LAS-b 단일 변수 비교가 되려면, 기준을 **LAS-b 끔 + 관문 켬** 팔로 맞춰야 한다(명세 437.4 "LAS-b 단일 변수 짝의 꺼짐 팔" = 태그 `final_C4G2_K1` / `final_C4G2_P3_K1`).

**전제 G(관문의 동일성 논증).** 관문은 R4c30 적용 여부만 바꾸고(437.1), 그 밖에는 명령을 바꾸지 않는다. 그러므로 같은 키의 관문 켬 실행과 꺼짐 실행은 첫 `would_block` 결정 전까지 비트 단위로 같다. 그 결정은 꺼짐 실행에서 R4c30을 적용한 LOC다. 여기서 두 가지가 따라 나온다.

- (G-a) 저장 줄에 R4c30이 없는 키는 LAS-b 끔 + 관문 켬 실행이 저장 해시와 같다.
- (G-b) 어떤 줄이든 `would_block_any`가 거짓이면 관문 꺼짐 실행과 같다. `las_k1_judgement.md` K-4에 이미 쓴 규칙과 같은 것이다.

| 묶음 | 조건 | 키 | 역할 |
|---|---|---|---|
| **R-0**(그대로) | LAS-b 끔 + **관문 끔**(`pre_las_preset_runner.py`. 이 러너는 이미 두 스위치를 모두 끈다) | D-1 5 + dg3 2 = 7 | 실행 커밋에서 저장 기준이 비트 단위로 재현되는지 본다(도구·환경 정체성). 저장 기준 자체가 관문 꺼짐이므로 관문을 켜면 재현이 아니게 된다. **python-expert 목록 6번(R-0 기준 해시)은 바꾸지 않는다** |
| **R-0K**(새로) | LAS-b 끔 + **관문 켬**. 태그 V0 `final_C4G2_K1`, VB `final_C4G2_P3_K1` | D-1 45(0.2. 저장 R4c30 41키 ∪ R-0 D-1 5키) | 관문 켬 기준선. R-0 5키 가운데 R4c30이 없는 4키는 (G-a)의 구조 확인이 된다. dg3는 넣지 않는다(G1 균일, 저장 R4c30 없음. 구현 때 T4h로 확인) |
| **T-3K**(T-3a·b·c) | 프리셋 그대로(LAS-b b0 + 관문 켬) | 228 + 4 + 76 = 308(키 목록 그대로) | rev3 K-4~K-7을 기준선 $B(k)$로 판정한다 |

- **기준선** $B(k)$: $k$ ∈ R-0K이면 R-0K 줄(해시와 `d1` 판정 블록 전체), 아니면 저장 기준(키 목록 = `d1.jsonl`, dg3는 저장 T4h 해시). 근거는 (G-a)다.
- 실행 순서: R-0 → R-0K → T-3K. 앞 묶음이 통과해야 다음 묶음을 시작한다(rev3 H-T3-1과 같은 방식).
- 비용은 약 2.0 CPU·h가 늘어난다(저장 벽시계 기준, 0.2). rev3의 13.1 CPU·h가 약 15.1 CPU·h가 된다.
- K-4(G1 균일 72 + T-3b 4의 "G1 해시 불변")는 G1 키가 R-0K에 하나도 없으므로 저장 해시와 글자 그대로 비교한다. 사용자 기준을 문구 변경 없이 그대로 시험한다.

### 1.3 봉인 규칙 개정이 필요하다

필요하다. 다음 항목이 봉인 문구와 어긋나기 때문이다.

| 봉인 문구 | 어긋나는 점 |
|---|---|
| rev3 2.1 실행 목록(R-0 7 + T-3 308) | R-0K 묶음과 새 키 목록이 생긴다 |
| rev3 2.2 실행 조건, H-T3-0 | 프리셋 조건이 "LAS-b b0"뿐이다. 관문 상태, R-0K의 프리셋 패치 허용이 없다 |
| rev3 3절 K-2·K-3 태그 | `_LAS` 고정(K-3), R-0 태그. `_K1`이면 H-T3-3이 된다 |
| rev3 K-5·K-6 기준값 = 키 목록 값 | $B(k)$로 대체한다 |
| rev4a 4 #2 dg3 설정 비교 | 관문 키 `slope_clearance_margin.flat_soil_margin_order_gate`의 처리가 정해져 있지 않다 |
| rev3 K-0, `T3_REQUIRED_SEALS` 9개 | 새 개정판과 R-0K 키 목록 봉인이 더해진다 |

- 사용자 결정("봉인 판정 도구를 새 태그에 쓰려면 개정판")과도 맞는다.
- 절차: control-expert가 **개정판 `las_targeted_rules_rev5.md` + `las_targeted_rules_rev5_r0k_keys.json`** 을 결과 전에 써서 봉인한다 → python-expert가 구현한다 → **verif-protocol-auditor `[시점] 실행 전` 감사(차단 0)** → 배치표(compute-scheduler-expert)와 함께 실행 승인을 받는다.
- 판정 기준(K-6a~e의 문턱, 사용자 채택 기준)은 바꾸지 않는다. 바뀌는 것은 실행 조건, 태그, 기준선 출처, 묶음 하나다.
- 결과 전 개정이다. T-3 본 실행은 아직 없다. 저장된 것은 연기 1행뿐이다(decision_log 591).

## 2. 확인 필요(사용자 결정)

| # | 질문 | 선택지 | 추천 |
|---|---|---|---|
| Q1 | T-3 실행 조건 | (a) 관문 켬(채택 제어기, `_LAS_K1`) / (b) 관문 끔(`pre_k1_preset_runner.py`, `_LAS`) | **(a)**. 1.1 |
| Q2 | 관문 켬일 때 기준선 | (a) R-0 고정 + R-0K 45키 추가(+2.0 CPU·h) / (b) R-0K 없이 저장 기준을 쓰고 `would_block` 줄을 K-5·K-6에서 "해당 없음"으로 뺀다 / (c) T-3 308키 전부의 LAS-b 끔·관문 켬 짝을 돌린다(+12.7 CPU·h) | **(a)**. (b)는 관문이 실제로 작용하는 패치 키(T-3c. T-3c를 넣은 이유가 G1 바탕 G6-2 시험이다)를 판정에서 뺀다. (c)는 (G-a)로 같은 결과가 미리 정해진 줄을 다시 돈다 |
| Q3 | R-0K에서 균일 연약 지면 키(H-S-0 J1·J2, H-S-1 S1, 36키)가 `would_block`일 때 | (a) 멈추고 묻는다 / (b) 기록만 한다 | **(a)**. K1 채택 근거(REM)는 "균일 연약 지면에서 K1은 동작을 바꾸지 않는다"였다. 하네스에서 이것이 깨지면 437.5 F2형 한계가 관측된 것이므로 T-3보다 먼저 볼 일이다 |
| Q4 | 개정판 이름 | `rev5` / `rev4d` | **`rev5`**. rev4a~c는 정정판이고, 이번은 실행 조건과 묶음이 바뀐다 |

## 3. 개정판 `las_targeted_rules_rev5.md` 골자(봉인할 때 문구로 쓴다)

1. **바뀌는 항목.** rev3 2.1·2.2·3절 K-0·K-2·K-3·K-5·K-6(기준값 출처)·4절 H-T3-0·H-T3-1, rev4a 4 #2. 그 밖(K-4 문구, K-6a~e 문턱, K-7, H-T3-2~H-T3-6, rev4~rev4c의 J-형식·G6-2_loc·None 규칙)은 그대로 둔다.
2. **실행 조건.**

   | 묶음 | LAS-b | 관문 | 기대 태그 V0 / VB | dg3 off / v4_on |
   |---|---|---|---|---|
   | R-0 | 끔 | 끔 | 없음 / `final_C4G2_P3` | 없음 / `final_C4G2_P3`(rev3 그대로) |
   | R-0K | 끔 | 켬 | `final_C4G2_K1` / `final_C4G2_P3_K1` | – |
   | T-3K | b0 | 켬 | `final_C4G2_LAS_K1` / `final_C4G2_P3_LAS_K1` | `final_C4G2_LAS_K1` / `final_C4G2_P3_LAS_K1` |

   - `_LAS`만 있고 `_K1`이 없는 태그, `_FB`가 붙은 태그는 H-T3-3이다.
   - 프리셋 패치 허용: R-0은 `pre_las_preset_runner`의 `with_10hz_d1`만, R-0K는 새 모듈 `las_t3_presets`의 `with_10hz_d1`만, T-3K는 패치 없음.
3. **R-0K 키 목록.** 선택 규칙: 「T-3a·T-3c·R-0 D-1 키 가운데 `d1.jsonl` 줄의 `event_names["INFO_LOC_FLAT_SOIL_MARGIN"]` > 0」 ∪ R-0 D-1 5키. 45키이고 목록 sha256은 `9399c492…2e3c`다(0.2). 파일에는 키마다 저장 해시, R4c30 개수, 예측 `would_block`을 적는다.
4. **K-2K(R-0K).**
   - (i) 태그·LAS-b 끔·관문 켬·미작동.
   - (ii) `would_block_any` 거짓인 줄은 해시가 저장 해시와 같다((G-b). 위반하면 구현 결함으로 보고 H-T3-1K 멈춤).
   - (iii) R-0의 R4c30 없는 4키는 `would_block_any`가 거짓이다((G-a). 위반하면 H-T3-1K).
   - (iv) 균일 연약 지면 36키 가운데 `would_block`이 있으면 멈추고 묻는다(Q3).
   - **예측(기준 아님).** `would_block` 참 집합은 패치 5키 = `H-S-A-J2|G1+J2@FL|T|flat|K1|{V0,VB}|e{0,0.002}` 4키 + `H-S-A|G1+J1@FL|B|flat|K1|V0|e0.002`. 근거는 S-C(b0) 위 Y-Pa에서 해시가 바뀐 5키(`las_k1_rules.md` 부록 A 41~45, dP −4~−8)와 같다는 점이다. 이 5키가 S-C에서 LAS-b 미작동이었다면 LAS-b 끔에서도 dP가 같다.
5. **기준선** $B(k)$(1.2). 키 목록 값과 `d1.jsonl`의 대조(rev4a 1의 `key-list` 검사)는 그대로 둔다. R-0K 줄의 `d1` 블록은 같은 형식이므로 G6-2는 `G6-2_loc`로 읽는다(rev4a 1).
6. **K-5.** 작동하지 않은 T-3K 줄의 해시 = $B(k)$. 추가로, R-0K 밖 키의 미작동 T-3K 줄에서 `would_block_any`가 참이면 K-5 실패로 본다((G-a)와 모순이므로 구현 결함, H-T3-5).
7. **K-6.** 작동한 T-3K 줄을 $B(k)$와 비교한다(K-6a~e 문턱 불변). 작동 줄에서 관문이 막은 결정은 LAS-b가 LOC 시각을 옮겨 생긴 결과이므로 LAS-b 효과로 판정한다(단일 변수).
8. **K-7(기록)에 열 추가.** `would_block_any`, `applied`, 첫 결정 dP [주기], R-0K/저장 기준과 결정이 다른지.
9. **dg3(rev4a 4 #2 대체).** 설정 비교에서는 정확한 키 `slope_clearance_margin.flat_soil_margin_order_gate` 하나만 뺀다. 대신 그 값을 묶음 조건(R-0 False, T-3K True)과 따로 대조한다. 접두 `slope_clearance_margin` 전체를 빼지 않는다(R4c30 설정이 비교에서 빠지면 안 된다). 실행 전에 dg3 4기록의 저장 T4h `events`에 `INFO_LOC_FLAT_SOIL_MARGIN`이 0개인지 확인한다. 0개가 아니면 H-T3-0이다(R-0K dg3 설계가 없으므로).
10. **K-0 봉인.** 원판, rev1~rev4, rev4a~rev4c, rev3 키 목록, **rev5, rev5 R-0K 키 목록**, 모두 11개.
11. **출력.** 새 폴더 `v5/las/t3_k1/`(`las_T3_R0.jsonl`, `las_T3_R0K.jsonl`, `las_T3.jsonl`, `las_T3.md`, `las_T3_judge.json`, `t3_dg3_t4h/`). 기존 `v5/las/`의 연기 산출물과 섞지 않는다.
12. **사전 위험.** 437.5 F2(첫 R4 LOC를 막으면 끝까지 R4c30 없음)는 T-3K 작동 줄에서 생길 수 있다. 생기면 K-6e(행정 증가 ≤ 1 mm)는 통과 쪽이다. 하지만 P3-5(끝 크롤러 틈 ≥ 25 mm)가 거짓이 될 수 있고, 그것은 K-6b로 잡힌다.

## 4. python-expert 구현 명세(6곳 + 시험)

공통 사항
- 지금 rev3/rev4c 동작은 모드 `rules="rev4c"`로 남긴다(기존 시험 176건이 그대로 돌아야 한다). 새 기본 모드는 `rules="rev5"`다. 봉인된 옛 판정 도구(`u3_judge`, `fb_judge`, `las_rev_judge`, `las_k1_*_judge` 등)는 건드리지 않는다.
- 태그 문자열은 리터럴로 두되, `v5_options`의 `LAS_K1_CONTROLLER_TAG`·`EXTEND_START_LAS_K1_CONTROLLER_TAG`·`with_order_gate_tag(None)`·`with_order_gate_tag(EXTEND_START_CONTROLLER_TAG)`와 같은지 시험으로 고정한다.
- 이 명세는 rev5 봉인 뒤에 구현한다. rev5 sha256은 `lt.SEALS`(`las_targeted.py`)에 등록한다.

| # | 위치 | 변경 | 시험 |
|---|---|---|---|
| 1 | `las_t3.py:219` `preset_problems()` | 매개변수 `gate_expected: bool`을 받는다. `config.slope_clearance_margin.flat_soil_margin_order_gate`가 기대와 다르면 문제로 낸다. `slope_clearance_margin.enable` True이고 `flat_soil_margin_m` 0.03인지도 본다(R4c30이 없는 관문은 의미가 없다). 실행 전 검사(`preflight`)는 T-3K 조건(b0 + 관문 True)으로 부른다. `controller_problems(controller, las, gate)`도 같은 세 값을 줄마다 본다(R-0: 끔/끔, R-0K: 끔/켬, T-3K: b0/켬). `las_record`에 `k1` 블록을 더한다. 내용은 `controller.meta()["slope_clearance_margin"]["order_gate"]`의 `enabled`, `decisions`(원문), 파생 `would_block_any`·`applied_any`·`first_dP`다 | T1-a: 프리셋 그대로이면 문제 0, `with_10hz_d1(flat_soil_margin_order_gate=False)`이면 문제 1. T1-b: 세 묶음 × 관문 두 값의 `controller_problems` 표(6조합, 매개변수 시험). T1-c: dg3 4기록 저장 T4h `events`의 R4c30 개수가 0인지 보는 검사 함수와, 합성 T4h로 그 검사가 실패하는 경우. T1-d: `k1` 블록이 관문 꺼짐 실행에서도 그림자 결정을 담는지(짧은 하네스 1키, 기존 연기 크기) |
| 2 | `las_t3.py:195` `wrapper_problems()` | 이름만 허용하던 방식을 `allowed: dict[str, str]`(메서드 이름 → 허용 모듈 이름)로 바꾼다. 묶음별 값은 R-0 `{"with_10hz_d1": "pre_las_preset_runner"}`, R-0K `{"with_10hz_d1": "las_t3_presets"}`, T-3K `{}`다. 새 파일 `04_scripts/04_hydraulic/coupled/las_t3_presets.py`에는 `install_las_off_gate_on()` 하나만 둔다. 이 함수는 `with_10hz_d1`을 `liftoff_approach_slow=False` 기본값으로만 감싸고, 관문은 프리셋 값(True)을 그대로 쓴다. 호출자가 키워드를 주면 그 값을 따르는 점은 `pre_las_preset_runner`와 같다. `TOOL_FILES`에 이 파일을 더한다. `build_jobs`는 묶음 R-0K의 `t3["las"]`를 `off`, `t3["gate"]`를 `on`으로 둔다(R-0은 off/off, T-3K는 on/on) | T2-a: 다른 모듈의 `with_10hz_d1`(예: `pre_k1_preset_runner`)이 R-0K에서 거부되는지. T2-b: `las_t3_presets` 설치 뒤 프리셋이 LAS-b False·관문 True인지. T2-c: R-0K 1키(`D1\|H-S-0\|G1\|T\|flat\|K1\|V0\|e0`)의 해시가 저장 `f805759d…`와 같은지(연기. 저장 벽시계 기준 짧은 키) |
| 3 | `las_t3_dg3.py:106` `main()` | 환경 변수 `LAS_T3_DG3_K1`(`on`/`off`, 필수)을 더한다. 시작할 때 `T-3 Dg-3 condition: LAS-b …, K1 gate … (preset …), ③ …`를 출력하고, 프리셋 관문 값이 변수와 다르면 `SystemExit`한다. R-0은 `off`(`pre_las_preset_runner`가 두 스위치를 모두 끈다), T-3K는 `on`이다. `final.RECORDED_SETTINGS`에 `slope_clearance_margin.flat_soil_margin_order_gate`를 더한다. `las_t3.run_dg3_job`은 묶음 조건에서 이 변수를 넘긴다 | T3-a: 변수 없음·잘못된 값이면 종료 코드 ≠ 0. T3-b: 변수 `on`인데 `pre_las_preset_runner`가 설치된 경우(관문 False)에 멈추는지. T3-c: 기록된 `controller_settings`에 관문 키가 있는지 |
| 4 | `las_t3_judge.py:41-43` 상수 | `TAG_V0_K1 = "final_C4G2_K1"`, `TAG_P3_K1 = "final_C4G2_P3_K1"`, `TAG_V0_LAS_K1 = "final_C4G2_LAS_K1"`, `TAG_P3_LAS_K1 = "final_C4G2_P3_LAS_K1"`를 더한다. 옛 상수는 `rev4c` 모드용으로 남긴다. `DG3_IGNORED_SETTING_PREFIXES`는 그대로 두고, 정확한 키 무시 집합 `DG3_IGNORED_SETTING_KEYS = ("slope_clearance_margin.flat_soil_margin_order_gate",)`를 따로 두어 3절 9번 대조를 한다 | T4-a: 네 상수가 `v5_options` 값과 같다. T4-b: 접두 무시가 관문 키 말고 다른 `slope_clearance_margin.*` 키를 숨기지 않는다(합성 기록에서 `flat_soil_margin_m`을 바꾸면 H-T3-3) |
| 5 | `las_t3_judge.py:104-112` `expected_tag()` | 서명을 `expected_tag(entry, line, las_on, gate_on)`으로 바꾸고, 3절 2번 표대로 돌려준다. `_LAS`이면서 `_K1`이 없는 태그는 rev5에서 H-T3-3이다. 판정기에 R-0K 단계를 더한다. 입력은 `las_T3_R0K.jsonl`이고, K-1(키 집합 = rev5 키 목록, 45), K-2K (i)~(iv), 정체성 K-0(세 파일 헤더가 같음)을 본다. $B(k)$ 사전을 만들어 K-5·K-6 기준으로 쓰고, K-7 열을 더한다 | T5-a: 묶음 3 × V0/VB/dg3 폴더의 기대 태그 표(매개변수 시험, 8칸 + `_LAS`만인 거부 1칸 + `_FB` 거부 1칸). T5-b: 합성 줄. R-0K 밖 키의 미작동 T-3K 줄에 `would_block_any` 참 → K-5 실패. R-0K 안 키의 미작동 줄 해시 = R-0K 해시 → 통과, 저장 해시와 같지만 R-0K와 다르면 → 실패. T5-c: R-0K 균일 키에 `would_block` → Q3 멈춤 코드. T5-d: 작동 줄의 K-6 기준이 R-0K 블록에서 오는지(`G6-2_loc`, READY, 행정) |
| 6 | R-0 기준 해시(`folder == "v4_on"` dg3 포함, LAS-b 끔) | **바꾸지 않는다**(1.2). 대신 R-0K 키 목록 생성기 `04_scripts/04_hydraulic/coupled/las_t3_r0k_keys.py`를 만든다. 입력은 `d1.jsonl`·rev3 키 목록이고 sha256을 대조한다. 3절 3번 규칙으로 `las_targeted_rules_rev5_r0k_keys.json`을 쓴다(이미 있으면 거부). 목록 sha256이 `9399c492…2e3c`, 45키여야 한다 | T6-a: 생성기 결과가 45키이고 sha256이 위 값과 같다. T6-b: R-0 7키의 기준 해시가 바뀌지 않았다(rev4c 모드와 rev5 모드의 R-0 기준 사전이 같음) |

- 실행 순서와 종료 코드: `las_t3.py run`은 R-0 → R-0K → T-3K 순서로 돈다. `--only R-0`·`--only R-0K`를 지원한다. 종료 코드 0/1/2는 rev3와 같고, K-2K (ii)(iii) 실패는 2(H-T3-1K), Q3 멈춤도 2다.
- 회귀: 기존 `test_las_t3.py`·`test_las_h7.py`를 `rules="rev4c"` 모드로 그대로 통과시킨다. 전체 단위 시험(6,492건 기준)에서 실패가 0이어야 한다. 무거운 연기는 T2-c 1키만 한다(P코어 D8x 하네스와 겹치지 않게 E코어 1워커로).

## 5. 핸드오프

- control-expert: Q1~Q4 결정 뒤 rev5 본문과 R-0K 키 목록 형식을 써서 봉인한다(결과 전).
- python-expert: 4절 구현(rev5 봉인 뒤).
- verif-protocol-auditor: `[시점] 실행 전` 감사. 주의할 점은 태그 집합의 `_K1` 처리, 래퍼 허용 모듈, R-0K 키 목록 봉인, $B(k)$ 출처, `.gitattributes -text` 보호다.
- compute-scheduler-expert: 배치표. R-0 7 + R-0K 45 + T-3K 308이고 약 15.1 CPU·h, 스레드 1이다.

## 6. rev5 봉인 뒤 바뀐 구현 명세(2026-11-10, 사용자 결정 Q1~Q4 = 추천안)

rev5(`las_targeted_rules_rev5.md` `879d0e4d…49b2`, R-0K 키 목록 `53b134a1…d764`, 봉인 2026-11-10 13:24:55 +09:00)가 4절보다 우선한다. 4절과 다른 점은 아래와 같다.

- 봉인 등록: `lt.SEALS`에 `rev5`와 `rev5_r0k_keys` 두 항목을 넣고, 둘 다 같은 `las_targeted_rules_rev5.sha256`(두 줄, rev3 방식)을 쓴다. `T3_REQUIRED_SEALS`는 11개가 된다.
- 6번: 생성기를 새로 만들지 않는다. 봉인 파일을 읽어 쓴다. 시험 T6-a는 봉인 파일과, `scripts/make_las_rev5_r0k_keys.py`(`54e6eff2…be24`) 규칙으로 `d1.jsonl`에서 다시 계산한 키 집합·`class`가 같은지 본다(45키, 목록 sha256 `9399c492…2e3c`).
- 분류: Q3 멈춤은 JSON `class == "uniform_r4"` 36키에만 건다. `r0_no_r4` 4키(R-0의 균일 키 2개 포함)는 K-2K (iii)으로 H-T3-1K다.
- 멈춤 이름과 종료 코드: K-2K (i) 실패는 H-T3-3(2), (ii)·(iii) 실패는 **H-T3-1K(종료 코드 1)**, (iv) 실패는 **H-T3-1Q(종료 코드 2)**. 4절 공통의 "K-2K (ii)(iii) → 2"는 1로 바꾼다. 멈춤 순서는 rev5 4절.
- K-5 추가 검사는 R-0K 밖 키의 미작동 D-1 줄에만 건다(dg3는 저장 R4c30 0 확인으로 대신).
- 출력 폴더: `06_analysis/03_hydraulic/coupled/v5/las/t3_k1/`.
