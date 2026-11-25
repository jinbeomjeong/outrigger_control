## 판 7 고정 표 계산(P7-9) 결과 — 봉인 구성 팔 a2, probe 6bfb2560

고정 표를 계산했습니다. **고정 표만으로는 6.2 규칙도, 6.3 규칙도 실패로 정해지지 않습니다.** 40단위 가운데 실패는 VBMslow S7 하나뿐이고, D 24줄은 V0 대비 실패·J-P3a 침범·FAULT가 모두 0건입니다. 해석과 권고는 넣지 않았습니다.

### 결과

**6.2 감도 본 단위 40개** (판정 4설정 × `probe_seen` 10키)
- 통과 39, 실패 1, 결측 0.
- 실패 단위: **VBMslow `S7_e0.001`**. 실패 항목은 `J3 fail: t_ready 77.1 -> 102.9`입니다.
  - 같은 단위의 J7 `WARN_PROBE_STIFFNESS_OUT_OF_RANGE`는 강성 경고 예외로 기록 처리했습니다.
- 강성 경고 예외가 적용된 단위는 7개입니다: VBMc005·VBMc04의 R12 top-FL-Fs8, VBMslow의 S7·R12 o0.0·top-FL-Fs8·bottom-FL-Fs4·top-FR-Fs4.
- 읽기 (1)로 기록 처리된 J1 관문은 0건입니다. `WARN_PROBE_RETRACT_NOT_OPENED`도 0건입니다.
- R15 나빠짐(정오 3 3-1): 4설정 모두 "구분됨"이지만 E > 0(+5855~5865 N)이라 나빠짐이 아닙니다.
- 군집 규칙만으로 계산한 결과:
  - 위상 2개 이상이 실패한 (설정, 행)은 없습니다.
  - 단독 실패는 1개(VBMslow S7)로, k = 4 이하입니다.
  - 판정: **실패로 정해지지 않음**. 결측이 0이라 결측을 어느 쪽으로 읽어도 같습니다.

**6.3 D 24줄** (D 12키 × {VBM, VBMslow})
- VBM 12줄은 모두 V0 기회 줄이고, V0 대비 실패는 0입니다(d = 0).
- VBMslow 12줄(기록)도 모두 통과입니다.
- ③ rev 7 조건 읽기는 24줄 모두 15이고, 그중 침범 0입니다. 줄 전체 jp3a 침범도 0입니다.
- FAULT 0줄, 24줄 모두 final `ready`입니다.
- V0 대비 새 WARN 이름은 강성 경고만 나왔습니다. 6줄에 있고, 판 6 6.3 읽기대로 기록만 했습니다.
- 판정: **실패로 정해지지 않음**.

**최소 힘(두 가지 원값, 기록만)**
- 모든 다리 값(`after_liftoff.min_kN`): D 24줄 중 16줄이 음수입니다. 그 최소 다리는 사건 다리(`event_output.pair[0]`)가 6줄, 대각 짝 다리가 10줄입니다.
- 사건 다리를 뺀 값: 다리별 이륙 뒤 최소 참 힘은 기록에 없습니다. 그래서 **사건 뒤 값**인 `event_output.min_F_after_event_kN`에서 사건 다리를 뺀 최솟값으로 적었습니다(아래 확인 필요 1).
  - 이 값은 D 12줄과 R15 8단위에서 음수입니다(−0.72~−1.05 kN).
  - head-only S1·S4·S5·S7 줄은 사건이 없어 해당 없음입니다.

### 대조
- 채택 도구 결과(`adoption_b46bdf8f.json`, 고정 해석, a2)와 맞습니다. 그 도구도 이 40단위 범위의 실패가 Mslow S7 하나였습니다.
- 40단위를 `VB` 라벨로 다시 계산해 봤고(채택 도구 방식, J11을 멈춤으로 봄), 판정 차이는 0건이었습니다.
- D 줄 `commands_sha256`은 명세 7절의 cmd 앞 8자와 맞습니다(예: `db0b1b38`, `92a0a01a`).
- 24 + 40줄의 정체성 검사(`ed7_condition3_adoption.line_problems`: 태그, 구성 요소, 조건 3, 옵션, blind 기록)와 실행 정체성(6bfb2560, clean)에서 문제는 0건입니다.

### 산출물
폴더: `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\fixed_table_b46bdf8f\`
- `fixed_table_a2.json` (sha256 `f7754a693c75da218a0ccc0eeb42c598cd4843034f874b70e47a709eaf4554d8`)
- `fixed_table_a2.csv` (sha256 `89190eec369bb5b99892c300b85dc776f22f446d6e3f13be1f1510169b465caf`)
- `manifest.json`: 입력 sha 8개, 명령, worktree b46bdf8f clean, 출력 sha.
- `fixed_table.py`: 계산 스크립트. worktree 모듈은 import만 했습니다.
- `fixed_table_rule_check.py` / `.txt`: 규칙 함수의 실패·통과·미정 분기 10개를 합성 입력으로 확인했고, 모두 ok입니다.
- `SHA256SUMS` (sha256 `195e8855bba243218c88450b3a1284de007b9813a80f86674ff6f58741f659c1`, 6항목, baseline_check write-sums)

입력과 sha:
- 고정해서 단언한 것:
  - 명세 `ebb79469…`
  - probe jsonl `1107b309…`
  - probe 키 `189dbb13…`
  - V0 main.jsonl `9ad74990…`
  - `confirm_b_grid192.json` `4e80e69b…`
- 기록만 한 것:
  - `sens_keys_ed7.json`(tool_6bfb2560) `3b622bbd…`
  - `condition_ad7a716e.json` `9bd2dba8…`
  - identity `16116fa2…`
- `jp3_rev7_condition.py`는 ad7a716e와 b46bdf8f 사이에 바뀌지 않았습니다(git diff로 확인).

### 적용한 읽기(공개용 사실)
- **40단위 판정**: 판 6 `jp3_ed6_judge.judge_sens` 꼴을 따랐습니다.
  - `_full_items` 위에 J7을 `j7_items_ed7`로 바꾸고, 읽기 (1), 읽기 (3)(S8 줄 없음), 강성 경고 예외(`is_j7_stiffness_exempt`)를 적용했습니다.
  - R15 나빠짐이면 두 R15 단위가 모두 실패입니다.
  - `fail`/`stop` 항목이 있으면 실패, `not_judgeable` 항목이 있거나 V0 짝이 없으면 결측입니다.
  - 설정 라벨은 실제 이름(VBMslow 등)을 썼습니다. 그래서 J11은 기록으로 들어갑니다.
- **D 줄 V0 짝**: 판 6 records D의 키 파일 입력인 `confirm_b_grid192.json`의 `v0_pair`를 썼습니다. 저장 V0 격자 run은 `grid_v0_run`으로 읽어 해시를 대조했습니다.
  - 기회 줄은 `event_output.pass`가 참이 아니면 실패입니다.
  - Q7-C4대로 V0에 없던 `WARN_PROBE_RETRACT_NOT_OPENED`가 있어도 실패로 둡니다. 실제로는 0건이었습니다.

### 확인 필요
1. **사건 다리 제외 최소 힘의 기준**
   - 실행 기록에는 다리별 이륙 뒤 최소 참 힘이 없습니다. T4h `true_force_*`는 meta상 limiter oil force입니다. 모든 다리 최솟값으로 비교해 보니 `after_liftoff.min_kN`과 대부분 맞지 않았습니다.
   - 그래서 사건 다리 제외 값은 "사건 뒤" 기준(`min_F_after_event_kN`)입니다. 7절 열을 어떤 정의로 쓸지는 control-expert와 메인 세션이 정할 일입니다.
2. **문면이 비어 있는 해석 세 가지** — 셋 다 이번 결과에는 영향이 없지만, 봉인 문면에 적을지 판단이 필요합니다.
   - (a) 감도 단위의 설정 라벨: 실제 이름이면 J11이 기록, `VB`면 J11이 멈춤. 두 방식의 차이는 0건이었습니다.
   - (b) R15 나빠짐이면 두 위상을 모두 실패로 셈. 이번에는 나빠짐이 없었습니다.
   - (c) D J-P3a 관문을 조건 읽기 기준으로 볼지(P7-8 문면), 줄 전체 jp3a로 볼지. 둘 다 0이었습니다.

### 남은 일
- 채택 도구의 "팔 3·4가 모두 만족할 때" 규칙 맞추기(명세 4.2, Y7-5)는 지시대로 하지 않았습니다. 봉인 뒤 도구 커밋으로 넘깁니다.
- 7절 a2 114행 가운데 고정 표 범위 밖 50행(VBM main 15, VBL 15, 감도 플랜트의 비감도 키 20)의 "V0 대비" 열은 P7-9 범위 밖이라 계산하지 않았습니다.

### 실행한 검증
- ruff(E,F,W,B,SIM,PTH,UP,RET): 통과. codespell: 오타 없음.
- scratchpad에 건식 실행을 두 번 했고, 최종 출력 json·csv 해시와 같습니다.
- 규칙 분기 합성 확인 10/10.
- worktree ed7-impl는 HEAD b46bdf8f, tracked 변경 없음입니다. 안의 `__pycache__`는 11-24 17:56 것으로 이번 작업 전부터 있었습니다. 실행은 모두 `-I -B`로 했습니다.
- 블라인드 경로(`606f8713/cdry_a1/...`)와 worktree 루트, `06_analysis` 전체는 검색하지 않았습니다. Glob은 `ed7_probe_a1`·`ed7_design` 폴더만 지정해서 썼습니다.
- scratchpad `python-ed7fixed\`는 지웠습니다.

사용한 스킬: 없음
