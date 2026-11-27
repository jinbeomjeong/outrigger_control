# 판 8 T8″ 해석 결정문: NB-1(5단계 A/A의 V0 처리 줄 J11) (control-expert, 2026-11-27)

- **상태**: 해석 결정이다. 봉인 명세 S8-R(sha256 `35f9eba8…`)은 고치지 않았다. 판정서와 T8″(python-expert) 구현에 쓴다.
- **근거**
  - 재감사 `audit_prerun/verif_t8p.md`(sha256 앞 16자 `C30367865973ACDD`)의 NB-1과 확인 필요 3
  - 앞 결정문 `control_t8p_decisions.md`
  - 사용자 결정(2026-11-27)
    - T8″로 고친 뒤 재감사 차단 0을 받고 4단계로 간다(실행 분리 없음).
    - M′-2: waiver 수가 정수가 아니면 setting_defect, 결측만 기록 실패 (1)이다.
- **코드 기준**: T8′ `2bf16b31`(worktree `ed8-judge2`, 읽기만 함, 작업 뒤 `status --porcelain --ignored`가 비어 있음)
  - `judge_stage1_r5.py`는 같은 worktree의 `06_analysis/03_hydraulic/coupled/v5/paper_runs/scripts/`에 있다.

## 요청 밖 추가(먼저 밝힘)
| # | 내용 | 이유 |
|---|---|---|
| N-A | 앞 결정문 1.3의 `V0_ABSENT_KEYS`에 `lock_window_alignment`를 더한다(10번째). 5단계 V0 줄에 이 키가 있으면 정체성 문제(setting_defect)다 | 이 결정의 전제(V0 플랜트에는 잠금 창 기록이 없다)를 판정 도구가 직접 확인하게 한다. 감사 M′-4 "5단계 V0 줄에서 없음"과 같은 방향이다 |
| N-B | A/A 쌍에서 처리(후보)와 기준(조건)의 `group`이 다르면 SettingDefect를 낸다(방어용) | `aa_item_fail`은 처리 metric의 `row`·`phase`만 기준 값으로 바꾼다(jp3_ed8_judge.py:812). `_full_items`는 `groups[row["group"]]`로 찾으므로(jp3_j9main_judge.py:268), group이 다르면 KeyError가 나서 종료 3이 된다. 봉인 키에서는 1017/1017 같으므로 도달하지 않는다(아래 2.4) |
| N-C | stats에 넘길 질문에 (나) 형상 슬롯의 A/A 후보 섞임을 더한다 | 판정 정의는 바꾸지 않는다. A/A 바닥 구성에 대한 관찰이다(4절 Q-3) |

## 0. 요약
| # | 질문 | 결정 | 구분 | 실패 시 |
|---|---|---|---|---|
| 1 | 7.4 "C-J (i) 항목 전부"와 V0 처리 줄의 J11 입력 부재 | **(나′) J11의 범위는 줄 자신의 설정으로 정한다.** A/A 후보는 V0이므로 J11은 436.8 rev16 R16-6 2·RD-10의 기록 설정 규칙대로 "입력 없음"(기록)이다. A/A 실패에도 판정 불가에도 넣지 않는다. 표 라벨 `VB`와 나머지 항목(J1~J10, SA-4, R15)은 그대로 둔다 | 해석(7.4·10절) | – |
| 2 | 다른 항목 전수 | J1~J11·SA-4·R15를 확인했다. **J11만 V0에서 판정 불가가 나고, J9는 V0에서 구조적으로 실패할 수 없다**(M2 기록 없음). 그 밖의 항목은 판정 가능하다. 비구조적 판정 불가 경로는 J7(사건 목록 200 절단)뿐이다(저장 쌍 0/63) | 기록·공개 | – |
| 3 | S8 SA-4가 G′ 슬롯에서 생기는지 | **생기지 않는다.** G′ 339슬롯의 조건 V0 줄과 A/A 후보는 모두 R12 사건 행이고, SA-4는 S8 행에서만 계산된다(jp3_ed6_judge.py:267). R15 악화도 R15 행만 대상이다 | – | – |
| 4 | 비대칭 공개와 stats 질문 | A/A 바닥에는 J9·J11 기여가 없지만 G′ VBN은 둘 다 센다. 그래서 $x_{AA}$는 낮게 치우치고 $k_N$은 작아지는 쪽(엄해지는 쪽)이다. 공개 문장 초안은 5절, stats 질문 Q-1~Q-4는 4절 | 기록·공개 | – |
| 5 | 구현 | `unit_item_verdicts(..., own_setting_items=...)`, `aa_item_fail`의 J11 재평가, N-A·N-B, **스텁 없는** 시험 | – | 새 상태: setting_defect(N-A, N-B) |

---

## 1. 7.4와 J11: 해석 결정

### 1.1 명세 문면
- 7.4(spec:303): "5단계에서 V0($o''$)를 돌려 V0($o''$)를 처리, V0($o$)를 기준으로 **C-J (i) 항목 전부로 판정**한다."
- C-J (i)(spec:232): "VBN 대 V0 J1~J11(판 6 6.2 읽기 (1)~(3), J7 판 7 6.1 새 비교, …)".
- 10절(spec:346): "계산되지 않은 판정 항목(조기 반환, 판정 행 0, **키·필드 결측**)은 판정 불가(0으로 읽지 않음)."
- 이 두 문장을 글자대로 함께 적용하면 V0 A/A 쌍은 모두 J11 판정 불가가 된다. 그러면 5단계 판정이 언제나 불가하다(감사 NB-1 실측 30/30, 아래 2.2 실측 63/63). 즉 봉인 문면 안에서 7.4는 쓸 수 없는 규칙이 된다. 그래서 해석이 필요하다.

### 1.2 J11이 무엇이고 누가 만드는가(코드)
| 사실 | 위치 |
|---|---|
| J11 = 잠금 창 대체 판독 다리의 `n_late_fallback_by_leg` > 0. 입력은 줄의 `lock_window_alignment` 블록이다 | judge_stage1_4368.py:311-329, judge4368_common.py:578-615 |
| **멈춤 설정은 `VB`·`LS1~4`뿐**이다. "every other setting's J11 is a record"(rev16 R16-6 2). 기록 설정에서 블록이 없으면 "입력 없음"(RD-10)이고, 멈춤 설정에서 블록이 없으면 판정 불가다 | judge4368_common.py:559-567, 594-598 |
| 블록은 플랜트에 `lock_events`가 있을 때만 쓰인다(v5 잠금 창 플랜트 옵션) | verdict_runs.py:218-221 |
| V0 = `options_of("V0")[1]` None이라 v5 플랜트 옵션이 없다 | run_v5.py:123, 887-909 |
| VBN은 `lock_window_follows_plant` = 참이다(실측, `options_of("VBN")`) | run_v5 옵션 |
| 지금 A/A는 후보 V0 줄을 표 라벨 `VB`로 metric에 넣는다. 그래서 J11 범위가 멈춤 설정이 된다 | jp3_ed8_judge.py:811 (`ed7.metric_of(..., TREATMENT_LABEL)`), :105 |
| census·G′에서 VBN이 J11 멈춤 범위에 드는 것도 이 라벨 대응(VBN→VB) 때문이다. 판 8 처리 줄의 J11은 원래 뜻대로 멈춤 항목이다 | jp3_ed8_judge.py `CJ_LABEL`, `TREATMENT_LABEL` |

### 1.3 후보 비교
| 후보 | 내용 | 판단 |
|---|---|---|
| (가) J11 A/A 해당 없음(기록) | 판정 불가 J11 항목을 A/A에서만 기록으로 바꾼다 | 효과는 (나′)와 같다. 다만 근거가 "A/A라서 뺀다"는 새 규칙이 되고, 무엇을 뺄지(사유 문자열 일치)가 깨지기 쉽다 |
| (나) 처리 라벨 전체를 기록 설정 라벨(예: `V0AA`)로 | 라벨 하나로 J11이 "입력 없음"이 된다 | 효과 범위가 넓다. R15 악화는 `path1.JUDGED_SETTING`(= `VB`)에 묶여 있다(jp3_j9main_judge.py:582). 라벨에 묶인 다른 경로가 생기면 VBN 판정 경로와 달라진다. 실측(2.2)에서는 J11을 뺀 실패 항목 집합이 두 라벨에서 63/63 같았다 |
| **(나′) 채택**: 표 라벨은 `VB` 그대로, **J11만 줄 자신의 설정(V0)으로 평가** | `assess_j11(lwa, "V0")` → V0은 기록 설정이므로 블록이 없으면 "입력 없음"(기록) | 436.8 rev16 R16-6 2·RD-10이 이미 정한 규칙(J11 범위는 설정이 정한다)을 그대로 쓴다. 새 예외를 만들지 않는다. 나머지 항목은 VBN 판정과 같은 경로·라벨을 지킨다 |

### 1.4 결정 문장([해석], 판정서에 옮김)
> 7.4 "C-J (i) 항목 전부"는 **V0 처리 줄에 정의된 항목 전부**로 읽는다.
>
> J11(잠금 창 대체 판독의 늦은 표본)은 그 입력 블록 `lock_window_alignment`를 v5 잠금 창 플랜트 옵션이 있는 실행만 만든다(verdict_runs.py:218-221). J11의 멈춤 범위는 436.8 rev16 R16-6 2와 RD-10대로 줄 자신의 설정이 정한다(judge4368_common.py:559-598).
>
> A/A 후보 줄의 설정은 V0(옵션 없음, 기록 설정)이다. 그래서 J11은 "입력 없음"(기록)이고, A/A 실패에도 판정 불가에도 넣지 않는다. 표 라벨 `VB`는 J1~J10·SA-4·R15 비교 경로를 VBN 판정과 같게 하려는 표기일 뿐이며, J11의 설정 범위를 바꾸지 않는다.
>
> 10절 "키·필드 결측 = 판정 불가"는 그 줄의 설정이 만들어야 하는 키가 빠진 경우에 적용한다. 설정이 정의상 만들지 않는 키에는 적용하지 않는다. 그 전제(V0 줄에 블록 없음)는 5단계 정체성 검사로 확인한다(N-A).

- **적용 범위**: 5단계 A/A(`aa_item_fail`)뿐이다.
  - census·G′ 8단계의 VBN 줄은 J11을 지금처럼 멈춤 항목으로 판정한다(바뀌지 않음).
  - 조건 V0의 기준 통과(`is_base_pass`, `own_item_failures`)도 바뀌지 않는다. 감사 실측에서 bool 30/30이었다.

---

## 2. C-J (i) 항목 전수 확인(V0 처리 줄)

### 2.1 항목별 입력과 V0에서의 상태(코드 + 저장 V0 실측, 값은 출력하지 않음)
실측 대상은 저장 `main.jsonl` V0 100줄(사건 40·정상 60, 판 5~7에서 본 행, O8-1)과 판 8 생산자 줄(41e107e9 P8-16 사전 실행 L2_impl run_v5 줄 23, 키 존재만)이다. "판정됨"은 계산이 된 경우이고, 통과와 실패를 합친 수다.

| 항목 | 읽는 metric 입력(코드) | V0 사건 줄 | 판 8 생산자 줄 | A/A 63쌍(사건 22·정상 41), 표 라벨 VB | V0에서 구조적? |
|---|---|---|---|---|---|
| J1 | 사건: `event_output.gates`, 정상: `harness_class`(judge_stage1_4368.py:216-243) | 있음 40/40 | 있음 | 판정됨 63 | 아님 |
| J2 | 정상 `F_after`, 강체 사건 `F_after_W_min_kN`, 그 밖 사건 `F_after_event`(246-266) | 있음 | 있음 | 판정됨 63 | 아님 |
| J3 | 사건 행은 항목 없음. 정상 강체 기록 행은 `case_floor`(없으면 **기록** "FLAG limit 미정")(269-290) | `case_floor` None 100/100 | 있음 | 판정됨 63 | 사건 행(G′ 전부)에는 적용되지 않는다. 정상 행에서도 기록·flag만 내고 fail은 없다 |
| J4 | `final_phase`, `t_first_ready_s`(judge_stage1_r5.py:126-130) | 있음 | 있음 | 판정됨 63 | 아님 |
| J5 | 사건 `t_ready_back_s`(r5:99-102) | 있음 | 있음 | 판정됨 63 | 아님 |
| J6 | 사건 `att_end_deg`, 정상 `max_abs_last_5s_deg`(r5:103-105, 120-123) | 있음 | 있음 | 판정됨 63 | 아님 |
| J7(판 7) | `events_full`·`bad_436`, 절단 시 판정 불가(jp3_ed7_rules.py:104-122) | 있음, 절단 0 | 있음 | 판정됨 63 | 아님. **비구조적 판정 불가 경로**(사건 목록 200 절단)가 있으나 저장 쌍에서는 0/63 |
| J8 | `command_stats.n_rev`(r5:134-135) | 있음 | 있음 | 판정됨 63 | 아님 |
| **J9** | `hydraulics_record.m2_clipped_steps_post_lift`(r5:61, 136-137). None이면 항목을 만들지 않는다 | **None 100/100** | 있음 23/23 | 항목 없음 63 | **예**: V0은 `hydraulics_record` None(verdict_runs.py:875-877)이므로 J9가 **실패할 수 없다** |
| J10 | 사건 `pressure.moving_outside_max_bar`, 정상 `pressure.max_moving_bar`(r5:106-107, 124-125) | 있음 | 있음 | 판정됨 63 | 아님 |
| **J11** | `lock_window_alignment`(위 1.2) | **None 100/100** | 있음 23/23 | **판정 불가 63/63**(사유 RD-10 "block missing") | **예**: (나′)로 "입력 없음"(기록) |
| SA-4 | S8 행만, `values.sa4` 등(jp3_ed6_judge.py:258-276) | 사건 행은 해당 없음 | – | 정상 41쌍 중 판정 불가 3(저장 S8 쌍, 옛 줄에 `sa4` 기록 없음) | G′에는 S8 행이 없다(3절). C8 V0 줄은 `values.sa4`를 늘 쓴다(verdict_runs.py:241) |
| R15 악화 | R15 행만, 라벨 `VB` 고정(jp3_j9main_judge.py:573-596) | – | – | 판정됨 | G′에는 R15 행이 없다 |
| J-P3 | 표에서 뺀다(jp3_j9main_judge.py:238-247, 272) | – | – | – | A/A 대상 아님. G′ 7.6에서 VBN 줄 단위로 따로 판정한다 |

- **표 라벨 비교**: 같은 63쌍에서 J11을 뺀 실패 항목 집합이 `VB` 라벨과 기록 설정 라벨(`V0AA`)에서 63/63 같았다. 집합 자체는 출력하지 않았다. 그러므로 (나′)의 효과는 J11에 한정된다.
- **결론**
  - V0 처리 줄에서 **구조적으로 입력이 없는 항목은 J9와 J11 둘**이다. 둘 다 v5 유압 플랜트 옵션의 산물이다(M2 이륙 뒤 클립, 잠금 창 대체 판독).
  - J11은 판정 불가로, J9는 "실패할 수 없음"으로 나타난다. J9는 NB-1을 만들지 않지만 비대칭(4절)에는 들어간다.
  - 그 밖의 항목은 판정 가능하다. 비구조적 판정 불가 경로는 J7 사건 목록 절단뿐이다(아래 2.3).

### 2.2 실측 명령과 출력 종류
- `aa_item_kinds.py`(dynamics-dev, T8′ 코드 import, 스텁 없음)
  - 저장 V0 줄을 같은 (row, group) 안에서 인접 위상끼리 짝지어 63쌍을 만들었다.
  - 각 쌍을 실제 `_full_items`·`replace_j7`·`apply_reading_1`·`s8_items`·`r15_worsening` 경로에 넣었다.
  - 출력은 항목별 상태 종류(판정됨 / 판정 불가 / 기록 "입력 없음")의 수, 판정 불가 사유, 두 라벨에서 실패 항목 집합이 같은지(예/아니오 수)뿐이다.
  - 결과
    - J11 판정 불가 63/63(사건 22, 정상 41), 사유 "lock_window_alignment block missing or not an object (RD-10)"
    - SA-4 판정 불가 3(정상 S8 쌍)
    - 그 밖의 항목은 모두 판정됨
    - 사건 목록 절단 0
- `structural_inputs.py`: 2.1 표의 입력 존재 수(None / 있음 / 키 없음)와 G′ 키 구조(3절)를 출력했다. 값은 출력하지 않았다.

### 2.3 남는 비구조적 판정 불가(바꾸지 않음, 공개)
- J7 사건 목록 200 절단이나 조건 V0의 기준 항목 부재로 A/A 쌍 하나가 판정 불가이면, 지금 코드는 5단계 전체를 not_judgeable로 만든다(`slot_inputs` → `aa_item_fail` 예외).
- 이는 10절 "계산되지 않은 항목 = 판정 불가"와 4절 "멈추고 묻는다"의 문면대로다. 저장 쌍에서는 0/63이었다.
- 이 결정은 그 동작을 바꾸지 않는다. stats 질문 Q-4로 넘긴다.

---

## 3. S8 SA-4(와 R15)가 G′ 슬롯에서 생기는가: 생기지 않음
- 봉인 키 `heldout_g_ed8.json`(sha `a18b5818…`) 실측
  - 조건 V0 줄의 행: R12 339/339
  - 원천: (가) a_phase 171, (나) b_shape 48, (다) c_fs 120
  - twin 사건: FS24 95, G4 112, RE1bF 132
  - A/A 첫 세 후보 1017개: 행이 같은 것 1017/1017
- SA-4는 `row == "S8"`일 때만 계산되고(jp3_ed6_judge.py:267), R15 악화는 R15 행만 대상이다(jp3_j9main_judge.py:582-585). 둘 다 5단계에서 도달하지 않는다.
- 판정 도구에 별도 처리를 두지 않는다. 키 파일이 sha로 고정돼 있으므로, S8·R15 행이 나타날 수 있는 경로는 없다.

### 2.4(N-B 근거) A/A 쌍의 group
- 첫 세 후보의 group이 조건과 같은 수: a_phase 513/513, b_shape 144/144, c_fs 360/360.
- 다른 필드
  - a_phase·c_fs는 `offset_s`만 다르다.
  - **b_shape는 144개 가운데 80개에서 `depth_m`·`ramp_s`(사건 형상)가 다르다**(형상만 7, 형상과 위상 73). 나머지 64는 위상만 다르다. 이것은 stats 질문 Q-3으로 넘긴다.

---

## 4. 비대칭과 stats-design-expert에 넘길 질문

### 4.1 비대칭(방향)
| | A/A 바닥(5단계, V0 대 V0) | G′ 처리(8단계, VBN 대 V0) |
|---|---|---|
| J9 | 실패할 수 없음(입력 구조 없음) | 셈(`m2_law` 있음, 생산자 줄 23/23에 입력 있음) |
| J11 | 기록 "입력 없음"((나′)) | 셈(멈춤 설정, `lock_window_follows_plant` 참) |
| 나머지 J1~J8, J10, J7 판 7 | 같은 경로 | 같은 경로 |

- **방향**: A/A는 J9·J11에 따른 위상 감도 실패를 잴 수 없다. 그래서 $x_{AA}$는 VBN의 참 귀무 실패율보다 낮게 치우치고, Jeffreys 사후 예측 $k_N$(7.5)은 작아진다. 이것은 **판정이 엄해지는 쪽**(거짓 실패 증가)이다. 7.4 공개 "A/A는 처리 팔 귀무 바닥의 하한이다"와 같은 방향이다.
- **반대 방향의 요인**(Q-3): (나) 형상 슬롯의 A/A 후보 80/144에서 사건 형상이 다르다. 그런 짝은 위상 섭동보다 큰 입력 차이이므로 $x_{AA}$를 높이는 쪽일 수 있다.

### 4.2 stats-design-expert 질문
- 메인이 지시문에 결과 수치를 옮기지 않는다.
- 쓰면 안 되는 자료: 판 8 출력 전부, 블라인드 경로.

| # | 질문 |
|---|---|
| Q-1 | A/A 바닥에서 J9·J11이 빠지는 것이 $k_N$(7.5)과 N층 CP95·$n_{AA}$ 멈춤(7.4)에 주는 영향의 크기를 공개 표(MDE80, 거짓 실패율)에 덧붙일 문장으로 정량화해 달라. 근거 후보는 판 5~7 저장 VB 계열 처리 줄에서 J9·J11 **단독** 실패가 위상에 따라 나는 빈도다(이미 본 행, O8-1). 판정 규칙($k$ 산식)은 바꾸지 않는다 |
| Q-2 | 판정서에 "J9·J11 단독 실패 단위 수"를 G′ 기록 칸으로 따로 둘지(판정 불변, 기록 추가)에 대한 통계적 권고 |
| Q-3 | (나) 형상 슬롯의 A/A 후보 80/144가 형상이 다른 짝이라는 점이 $x_{AA}$에 주는 방향(높임)과, Q-1의 낮춤과 함께 볼 때의 공개 문장. 봉인 규칙(같은 슬롯 후보)은 바꾸지 않는다 |
| Q-4 | 비구조적 A/A 판정 불가(J7 절단 등, 저장 0/63)가 생기면 지금은 5단계 전체가 판정 불가(멈추고 묻기)다. "그 슬롯 A/A 기회 없음(기록)"으로 두는 읽기와 비교한 통계적 영향. 규칙 해석은 control·사용자 결정 사항이고, stats는 영향만 본다 |

---

## 5. 판정서 공개 문장(초안)
> **5단계 A/A 항목 범위(해석, control-expert 2026-11-27, 감사 NB-1)**: 7.4 "C-J (i) 항목 전부"는 V0 처리 줄에 정의된 항목 전부로 읽었다.
>
> J11(잠금 창 대체 판독)과 J9(M2 이륙 뒤 클립)은 v5 유압 플랜트 옵션이 있는 실행에만 입력이 생긴다. V0(옵션 없음)에서는 정의되지 않는다.
> - J11은 436.8 rev16 R16-6 2·RD-10대로 줄 자신의 설정(V0 = 기록 설정)으로 범위를 정해 "입력 없음"(기록)으로 두었다.
> - J9는 입력이 없어 실패할 수 없다.
>
> G′ 처리(VBN)는 두 항목을 센다. 따라서 A/A 바닥 $x_{AA}$에는 J9·J11의 위상 감도가 들어 있지 않고, $k_N$은 그만큼 작게(판정이 엄하게) 정해진다. 이는 7.4 공개("A/A는 귀무 바닥의 하한")와 같은 방향이다. 크기는 stats 검토(Q-1)에 따른다.
>
> (나) 형상 슬롯의 A/A 후보 일부(첫 세 후보 144 중 80)는 사건 형상이 다른 짝이다(반대 방향, Q-3).
>
> 이 해석의 전제(5단계 V0 줄에 `lock_window_alignment` 없음)는 정체성 검사로 확인했다. 실측은 저장 V0 100줄에서 없음 100/100, 판 8 생산자 23줄에서 있음 23/23이다.

---

## 6. 구현 명세(python-expert, T8″ = ed8-judge2 위 새 커밋, C8 불변)
1. **`unit_item_verdicts(treatment, references, *, own_setting_items: Mapping[str, str] | None = None)`**(jp3_ed8_judge.py)
   - `None`이면 지금과 같다. census·G′는 바꾸지 않는다.
   - `{"J11": "V0"}`을 주면 표의 J11 항목(`item["item"] == "J11"`)을 모두 빼고, 처리 metric마다 `path1.j11_items({**metric, "setting": own_setting})`로 다시 만든다.
     - 다시 만든 항목 가운데 `stop`은 실패로, `not_judgeable`은 판정 불가로 기존 목록에 넣는다.
     - `record`는 반환값의 새 키 `own_setting_records`(단위별 `[{"item", "state", "detail"}]`)에 넣는다.
   - 실패·판정 불가 목록의 다른 항목은 그대로다.
2. **`aa_item_fail(base_row, candidate_row, folders)`**
   - **전제 확인**: `candidate_row["job"]["setting"] == "V0"`이고 `candidate_row.get("hydraulic_options") is None`이다. 아니면 `SettingDefect`.
   - **N-B**: `treatment["group"] != reference["group"]`이면 `SettingDefect("A/A pair groups differ")`. row·phase를 바꾸기 전에 비교한다.
   - `unit_item_verdicts([treatment], [reference], own_setting_items={"J11": "V0"})`를 부른다. 판정 불가 항목이 남으면 지금처럼 `NotJudgeable`이다.
   - 반환을 bool에서 `{"fail": bool, "own_setting_records": [...]}`로 바꾸거나, bool은 유지하고 기록을 별도로 돌려준다(구현자 선택). `slot_inputs` 후보 기록에 `aa_j11_state`(기대 "입력 없음")를 넣는다.
3. **stage5 report**
   - `aa_item_scope`를 둔다
     - `{"items": "C-J (i) J1..J11", "own_setting_items": {"J11": "V0"}, "structural_no_input": ["J9", "J11"], "basis": "control_nb1_decision.md 1.4"}`
   - 결정된 A/A 쌍의 `aa_j11_state` 분포 수를 둔다(기대: 모두 "입력 없음").
4. **N-A**: `V0_ABSENT_KEYS`에 `"lock_window_alignment"`를 더한다(10개). 정체성 문제 → setting_defect다(앞 결정문 1.4의 상태 순서 그대로).
5. 상수 `AA_OWN_SETTING_ITEMS = {"J11": "V0"}` 한 곳에 둔다. 시험이 이 상수를 쓴다.
6. M′-1, M′-2(사용자 결정: 비정수 waiver = setting_defect, 결측만 기록 실패 (1)), R′-4는 감사 지시대로 함께 처리한다.

### 6.1 시험(스텁 없음)
`ed7.metric_of`, `ed8.is_base_pass`, `ed8.aa_item_fail`, `unit_item_verdicts`, `identity_defects`는 바꾸지 않는다. 바꿔도 되는 것은 파일 위치(tmp 폴더)와 격자 저장소 입력(`GridStore`가 tmp의 작은 격자 파일을 읽게 하는 것)뿐이다.

| # | 시험 | 기대 |
|---|---|---|
| T-1 | **생산자 꼴 V0 사건 줄 두 개**(같은 R12 twin, `offset_s`만 다름; `lock_window_alignment` 없음, `t4h_file` 없음, `hydraulic_options`·`hydraulics_record` None, `controller_tag` `final_C4G2_LAS_K1`). 키 집합은 `run_v5.run_one` 반환(run_v5.py:948-963)과 `judge_stage1_r5.metrics`·`judge_stage1_4368.metrics`가 읽는 키 전부(judge_stage1_r5.py:48-82, judge_stage1_4368.py:163-186)를 갖춘다. 이 둘로 `aa_item_fail` | 예외 없음. `aa_j11_state` = "입력 없음". 실패 여부는 bool |
| T-2 | T-1 줄로 1356줄짜리 5단계 출력 셋을 봉인 키의 job으로 합성하고 `judge_stage5`를 끝까지 돈다 | 상태가 `frozen` 또는 규칙의 stop이다. **not_judgeable이 아니다**. `aa_item_scope`가 있다 |
| T-3 | T-1에 `lock_window_alignment: {}` 추가 | `v0_identity_problems`에 문제 → 5단계 setting_defect, $k$ 동결 없음 |
| T-4 | T-1 후보의 twin `fs_kN`을 바꿔 group을 다르게 | `SettingDefect`(종료 2, 종료 3 아님) |
| T-5 | T-1 후보의 `events`를 200개로 채움(J7 절단) | `NotJudgeable`(비구조적 경로는 그대로) |
| T-6 | 회귀: VBN 처리 줄(블록 있음, 대체 다리 `n_late` > 0)을 `judge_heldout` 경로의 `unit_item_verdicts`로 | J11 `stop` → 실패. `own_setting_items`는 쓰이지 않는다 |
| T-7 | 회귀: VBN 줄(블록 없음) census 경로 | J11 판정 불가(바뀌지 않음) |
| T-8(선택, 실제 꼴) | 메인 checkout 저장 `main.jsonl`(sha 9ad74990 고정)의 같은 (row, group) V0 사건 쌍 22개로 `aa_item_fail` | 22/22 예외 없음(값은 단언하지 않고 출력하지 않음). 파일이 없으면 skip이 아니라 실패로 한다(`OUTRIGGER_RECORDS_ROOT=main`) |

- 전체 시험에서 새 실패 0, 새 skip 0이어야 하고, P8-11(`test_ed8_run_path`)을 다시 돈다.
- 감사 메인 권고 3(C8 V0 한 줄 스모크)은 이 결정의 전제(`lock_window_alignment` 없음, `hydraulics_record` None, 태그)를 C8 생산자로 직접 확인하는 일이다. T8″ 재감사 전에 하기를 권한다.

## 7. 판정·기록 구분과 상태(새 항목만)
| 항목 | 구분 | 상태 |
|---|---|---|
| A/A의 J11(V0 처리 줄) | 기록("입력 없음") | 상태를 바꾸지 않는다 |
| A/A의 J9 | 구조적으로 실패할 수 없음(공개) | – |
| V0 줄에 `lock_window_alignment` 있음(N-A) | 판정(정체성) | setting_defect, $k$ 동결 없음 |
| A/A 쌍 group 다름(N-B) | 입력 결함(봉인 키에서는 도달하지 않음) | setting_defect |
| 비구조적 A/A 판정 불가(J7 절단 등) | 판정 불가(그대로) | not_judgeable(멈추고 묻기) |

상태 순서는 10절을 따른다. 5단계 정체성 결함과 완결성 결함이 있으면 선택을 계산하지 않는다(앞 결정문 1.4).

## 8. 수행한 작업
- **읽기**: 재감사 `verif_t8p.md`(NB-1, M′-1~M′-4, R′, 확인 필요), 명세 7.4·10절(앞 작업에서 전체 읽음)
- **코드**(ed8-judge2, 파일 직접 지정)
  - `jp3_ed8_judge.py`(298-338, 795-915)
  - `judge4368_common.py`(262-308, 555-615)
  - `judge_stage1_4368.py`(160-460)
  - `jp3_j9main_judge.py`(226-273, 569-613)
  - `jp3_ed7_judge.py`(`replace_j7`·`metric_of`·`phase_of`)
  - `jp3_ed7_rules.py`(`j7_items_ed7`)
  - `jp3_ed6_judge.py`(`apply_reading_1`·`s8_items`·`missing_keys`·`fault_reasons`)
  - `06_analysis/03_hydraulic/coupled/v5/paper_runs/scripts/judge_stage1_r5.py`(20-141)
- **실행**: PowerShell, `conda run -n dynamics-dev python -I -B`, `PYTHONDONTWRITEBYTECODE=1`, `NUMBA_CACHE_DIR`=scratch(실행 뒤 지움). 스크립트는 `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\0d95027e-6012-4053-b99a-1e505935768c\scratchpad\control-ed8-nb1\`에 있다(근거 스크립트, 메인이 근거 폴더로 옮길 대상).

| 스크립트 | sha256 앞 16자 | 내용 |
|---|---|---|
| `aa_item_kinds.py` | `0F170436076EEFF4` | 저장 V0 63쌍의 항목별 상태 종류, 판정 불가 사유, 두 라벨에서 J11을 뺀 실패 집합이 같은지 |
| `structural_inputs.py` | `257251FF86E1FD9E` | 항목 입력의 존재 수(저장 V0·P8-16 L2_impl), VBN 옵션 스위치, G′ 키의 행·group·다른 필드 |

## 9. 공개(행위 그대로)
- **블라인드**: `j9_runs\606f8713\cdry_a1\…`, `prelaunch_j9\ed6_inputs\x11\selection.json`과 그 worktree 사본은 열지도 검색하지도 않았다. 상위 폴더(`j_p3_cause`, `j9_runs`, `prelaunch_j9`, `06_analysis`, worktree 루트)는 Grep·Glob 범위로 쓰지 않았다.
  - Glob은 한 번 썼다(`**/judge_stage1_r5.py`, path = `ed8-judge2\04_scripts`, 결과 없음).
  - Grep은 파일을 직접 지정했다.
  - `judge_stage1_r5.py`는 worktree의 `06_analysis\03_hydraulic\…\scripts\` 파일을 직접 지정해 읽었다.
- **읽은 자료와 출력 범위**
  - 저장 main.jsonl V0 줄(판 5~7에서 본 행): 항목 상태 종류와 입력 존재 수만 출력했다. 통과·실패는 합쳐 셌다.
  - 41e107e9 `p816.jsonl`: L2_impl run_v5 줄의 입력 키 존재만 셌다.
  - 봉인 G′ 키: 행·출처·group·다른 필드 이름만 셌다.
  - 판 8 결과는 없고 보지 않았다.
- **셸**: Bash는 쓰지 않았다. 프로세스를 종료하지 않았다. scratchpad는 `control-ed8-nb1\`만 썼고, 그 안 `numba`만 지웠다.
- **에이전트 메모리**: `baseline-identity-and-record-keys.md`에 한 단락을 더했다(기준선 줄을 처리 라벨로 판정할 때 옵션 전용 항목이 생기는 문제, group 확인).

사용한 스킬: 없음
