## 추가 작업: 436.9 j9_main J-P3(③ revision 6) 경로 2 판정 (dynamics-expert, 2026-11-23)

### 판정
**pass (종료 0)**
- 판정 행 200, breach 합 a/b/c = 0/0/0.
- judged_key_missing 0, setting_defect 0, record_defect 0, B2 위반 0, 리비전 결함 0.
- per-read 배열(`jp3_*`)은 판정 행 T4h 200개에 모두 있다. 그래서 판정 불가 사유가 없다.

| 설정 | 줄 | 판정 행 | 기록 행 | 헤드 전용 선언 줄 | breach a / b / c | judged_key_missing | B2 위반 | 리비전 결함 |
|---|---|---|---|---|---|---|---|---|
| VBJ | 100 | 40 | 0 | 60 | 0 / 0 / 0 | 0 | 0 | 0 |
| LSJ1 | 72 | 40 | 0 | 32 | 0 / 0 / 0 | 0 | 0 | 0 |
| LSJ2 | 72 | 40 | 0 | 32 | 0 / 0 / 0 | 0 | 0 | 0 |
| LSJ3 | 72 | 40 | 0 | 32 | 0 / 0 / 0 | 0 | 0 | 0 |
| LSJ4 | 72 | 40 | 0 | 32 | 0 / 0 / 0 | 0 | 0 | 0 |
| 합 | 388 | **200** | 0 | **188** | **0 / 0 / 0** | 0 | 0 | 0 |

### 판정 근거

**판정 행**
- 하네스 배치(jsonl) 줄은 `level`이 없다. 그래서 4a-7 4.3 3번에 따라 등급은 ideal이고, 판정 행 등급(normal 이하)에 든다.
- 판정 행은 이벤트 경로 줄 200개다(R12 160, R14 10, R15 10, R16 20). 설정마다 40개씩이다.

**헤드 전용 선언**
- 4a-7 e1 3: 388줄 모두 T4h meta `head_only_declared`로 판별했다.
- 개정 9 사례 표(R1~R11·S1~S5·S7·S8 = 선언)와 어긋나는 줄은 0이다.
- 선언 줄 188개는 ③ record가 없고 ① = ② = 0이다.

**B2 증거**
- 4a-8 8.1 / e1 8: 판정 행 200개 모두 ① = 1·② > 0이다. 하네스 줄은 r79 키가 아니므로 k = 1이다.

**리비전**
- 판정 행 200개 모두 태그 `final_C4G2_P3W_LAS_K1`(→ 6, 가정은 아래 1)이고 `extend_bound_check.rule_revision` = 6이다.
- 선언 줄 188개도 태그가 같고 ③ record가 없다.
- 줄 수준 `run_extend_start_revision` 키는 388줄 모두에 없다. 판정에는 쓰지 않고 기록만 했다(아래 2).

**그 밖의 결함 검사**
- 코드표, 분류 대 명령 표(±1e-12 m/s), 판정 읽기 NaN, used 대 ext/model 열 일치(e2 1), J-P3c used ≥ ext − 1 Pa 모두 위반이 없다.
- 시험 전용 설정 줄과 stretch_mismatch 줄도 0이다.

**정체성(기록만)**
- `spec_edition` fe6f5844, `carry_end_rule` inherit_when_gate_shut, `retract_start_rule` with_tracker.

**참고(판정에 쓰지 않음)**
- 줄에 기록된 jp3 키 9개가 경로 2 재계산과 판정 행 200/200에서 같다.

### 수행한 작업
- **입력 대조**: `SHA256SUMS_j9main` 389파일 모두 일치(경로는 `j9main\` 기준), 누락·여분 0. `j9_main.jsonl` sha256 `883a2538f61d2a6a6c577c9a327601fc04da076b212db9bcccad22694817c001`.
- **도구**: `z4378-p2ed5` 커밋 **`65e0678d`**(이전 dde4499d 위). master 병합·push는 하지 않았다.
  - `jp3_rev6_judge_p2.py`에 `judge-jsonl` 하위 명령을 추가했다.
  - rev 5 경로 2 행 판정(`jp3_rev5_judge_p2.judge_row`)에 기대 리비전·태그 대응·정체성 검사 여부 인자를 더했다. 기본값은 rev 5 그대로라 rev 5 동작은 바뀌지 않는다.
  - 시험 1개를 추가해 경로 2 시험 3파일 109 passed, ruff 통과.
- **실행**: dynamics-dev `python.exe -I -B`(PATH Library\bin, MKL_THREADING_LAYER=TBB). T4h 폴더는 jsonl 옆 `j9_main_t4h`다(4a-7 4.8).
- **결과**: `C:\Users\jinbeom\.claude\p2_inputs\ed5_606f8713\p2_out\`

  | 파일 | sha256 |
  |---|---|
  | `jp3_rev6_j9main_p2.json` | `572f2f391d08243e800f704962af5c82295e0eac4143fbc9f05d2d6069922445` |
  | `jp3_rev6_j9main_p2.console.txt` | `c5ddbd95e4f4ef925cacde544bbd7f286a3707ceb67594d40f1a194ea437a90d` |
  | `run_commands.txt` (j9_main 절을 덧붙임: 명령, 커밋, 도구 sha, 입력 대조) | `657c7766639a483a26426ea37cc381ee73c750653b4f554981830ca4437083f4` |
  | `SHA256SUMS_p2_out` | 7개 파일로 다시 만듦 |

  - 앞 작업 결과의 sha는 그대로다: `tjr12b_p2.json` `926823d8…e235`, `jp3_rev6_VBJ_VBJ0_p2.json` `afe5ffae…b86b`. 이 둘은 dde4499d에서 만들었다. 65e0678d의 변경은 T-JR-12b 경로를 지나지 않는다.

### 공개
- 이번에 새로 연 것은 중립 입력 `j9main\`과 그 SHA 목록뿐이다.
- 경로 1 코드·출력·판정서·금지 폴더는 열지 않았다. 줄 안의 실행 쪽 경로 문자열도 따라가지 않았다.

### 확인 필요
1. **rev 6 태그 base**: 앞 보고와 같이 `final_C4G2_P3W` → 6은 가정이다(넘김에 대응 없음).
2. **`run_extend_start_revision`**: 넘김 6 2.7 (4)는 이 키를 VBK 줄 문장에만 적었다. j9_main 하네스 줄에는 이 키가 없다(388/388). 이 키를 j9_main 줄에도 요구하면 388줄 모두 setting_defect가 된다. 그래서 지금은 기록만 한다.
3. **판정 행 기대 수**: 넘김에 j9_main 판정 행 수가 정해져 있지 않다. 기대 수 검사 없이 200을 보고한다.
4. **재잠김 1 bar(P4-3a / T-JR-15)**: 요청 범위 밖이라 돌리지 않았다. 필요하면 같은 도구에 relock 옵션을 붙여 돌릴 수 있다.

사용한 스킬: 없음
