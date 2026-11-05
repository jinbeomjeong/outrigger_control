# 논문 v4 저하중 놓침 근거(분모 19, ML 기록 재생)

- 작성: control-expert, 2026-11-05. 판정과 수치 설명은 `00_docs/04_control/s6_control_spec.md` 434절이 원본이다.
- 원고가 이 경로를 `src`로 가리킨다. 폴더 이름을 바꾸지 않는다.
- 새 시뮬레이션은 없다. 모두 저장 기록을 읽어 다시 판정하거나 집계했다.

## 파일

| 파일 | 뜻 | 입력 | scratchpad 경로 의존 |
|---|---|---|---|
| `ml_jc_replay.py` | ML 평가 기록에서 J_C·J_P를 재생해 미달 구간을 모두 나열한다. 인자는 소스 트리와 출력 JSON이다. E 코어 `0x00FF0000`, 워커 4개 | `07_results/S8/ml_main_20261025_090131/{ml_dataset,ml_dataset_mlj,ml_dataset_en,verify_S8ML.json}`, 각 사례의 `pads.npz` | 없음 |
| `ml_jc_head.json` | 위 재생 결과, 현재 코드 | 위 | 해당 없음 |
| `ml_jc_pin.json` | 위 재생 결과, 당시 코드. `ml_jc_head.json`과 바이트까지 같다 | 위 | 해당 없음 |
| `ml_jc_miss2.py` | J_C가 놓친 44구간의 1 ms 값, 사건 다리, 띠, 끝 단계를 만든다 | `ml_jc_head.json`, 각 사례의 `result.json`·`pads.npz` | **있음**: 파일 앞쪽 상수 `S`, 입출력 폴더 |
| `ml_jc_missed_detail.json` | 위 결과(44구간) | 위 | 해당 없음 |
| `ml_jc_final.py` | 조건별 집계, 부분집합 확인, 묶음별 조건 범위 | `ml_jc_head.json`, `ml_jc_missed_detail.json`, 각 사례의 `result.json` | **있음**: 파일 앞쪽 상수 `S`, 입력 폴더 |
| `ml_jc_final.out.txt` | 위 표준 출력 | | 해당 없음 |
| `chrono_level_miss.py` | C-S8-71·72·74 판정 파일에서 J_C 놓침과 표본 시각 힘을 뽑는다. `pads.npz` 시계 오프셋 3 s를 보정한다 | `06_analysis/02_control/s8/rev65/verify_S8C_c68b_c71.json`, `rev68/verify_S8C_{c72,c74}_u75.json`, 해당 배치의 `result.json`·`record/record.npz`·`pads.npz` | 없음 |
| `chrono_level_miss.out.txt` | 위 표준 출력 | | 해당 없음 |
| `item9_list.py` / `.out.txt` | 항목 9 사례별 구간 수와 놓침(분모 19 재집계) | `06_analysis/02_control/s8/s8_rest_rev46_item9.json` | 없음 |
| `item9_rows.py` / `.out.txt` | p1r·rest·CB 2개·v4 재확인 판정 파일의 항목 9 행 | 각 `verify_*.json` | 없음 |
| `ep_table.py` / `.out.txt` | 19구간의 다리·시각·부상 표시 표, 최종 재실행의 같은 구간 | p1r·rest `verify_S8C.json`, `verify_final_v4recheck_20261104_202815.json`, `verify_final_E_RE1bF_Fs8_20261031_000914.json` | 없음 |

- 주의: `chrono_level_miss.out.txt`의 `G4H` 행은 헤드 센서 고장 주입 사례다(434.6).
- `ml_jc_final.py` 끝의 Chrono 블록은 찾는 경로에 판정 파일이 없어 아무것도 내지 않는다. Chrono 값은 `chrono_level_miss.out.txt`를 쓴다.
- 표본 수 집계(1표본 67개 중 42, 2표본 이상 537개 중 2)는 `ml_jc_head.json`의 `scope == "scored"` 행에서 `samples`와 `JC_first_decision_s`로 다시 셀 수 있다. 묶음은 train, validation, test, OOD-1, OOD-2, MLJ다. `EN` 묶음은 넣지 않는다.

## 코드 판

| 판 | 내용 | 확인 |
|---|---|---|
| 당시 코드(`ml_jc_pin.json`) | `dd29aae` 트리에 `9636556`의 `control/c2.py`·`control/contact_replay.py`를 덮음 | SHA-256 앞자리 `8120b8d4`(c2), `2082cc01`(contact_replay). `s8_ml_main_report_v2.json` 기록과 같다 |
| 현재 코드(`ml_jc_head.json`) | 커밋 `9af92b7`의 `03_src`(실행 때 `03_src` 변경 없음) | |

## 재생 명령

저장소 루트에서 실행한다. `<W>`는 임의의 작업 폴더다.

당시 코드 트리 만들기(Bash 도구, 짧은 git 명령):
```bash
mkdir -p <W>/pin && git archive dd29aae 03_src 02_params | tar -x -C <W>/pin
git show 9636556:03_src/outrigger_sim/control/c2.py > <W>/pin/03_src/outrigger_sim/control/c2.py
git show 9636556:03_src/outrigger_sim/control/contact_replay.py > <W>/pin/03_src/outrigger_sim/control/contact_replay.py
```

재생(PowerShell 도구, 한 번에 약 44 s, 2026-11-05 측정):
```powershell
$D = '06_analysis\02_control\paper\ml_jc'
& C:\ProgramData\miniforge3\Scripts\conda.exe run --no-capture-output -n dynamics-dev python -I "$D\ml_jc_replay.py" C:\workspace\outrigger_control\03_src <W>\ml_jc_head.json
& C:\ProgramData\miniforge3\Scripts\conda.exe run --no-capture-output -n dynamics-dev python -I "$D\ml_jc_replay.py" <W>\pin\03_src <W>\ml_jc_pin.json
```

집계(같은 호출 방식):
- `ml_jc_miss2.py`, `ml_jc_final.py`는 실행 전에 파일 안의 `S`를 입력 JSON이 있는 폴더로 바꾼다.
- `chrono_level_miss.py`, `item9_list.py`, `item9_rows.py`, `ep_table.py`는 인자 없이 그대로 돈다.

## 재현 해시(SHA-256 앞 16자리)

복사본과 scratchpad 원본이 모두 일치함을 확인했다.

| 파일 | 해시 |
|---|---|
| `ml_jc_replay.py` | `8F82AFEA50287B82` |
| `ml_jc_miss2.py` | `2A204D7E369AEB8A` |
| `ml_jc_final.py` | `38DF83B7218CEA97` |
| `chrono_level_miss.py` | `C8F39A461907CC18` |
| `ml_jc_head.json` | `4463F646D58993DB` |
| `ml_jc_pin.json` | `4463F646D58993DB` |
| `ml_jc_missed_detail.json` | `41039FA780743D82` |
| `item9_list.py` | `4F73B3C41FC6BCD5` |
| `item9_rows.py` | `C20FD782067758F7` |
| `ep_table.py` | `2624C4F891E12A46` |
| `item9_list.out.txt` | `505DBE3CFBAF0179` |
| `item9_rows.out.txt` | `3F0A01D2BF3A7FB4` |
| `ep_table.out.txt` | `E72C42ACEA8AA048` |
| `ml_jc_final.out.txt` | `1A4B853D03FFDFD2` |
| `chrono_level_miss.out.txt` | `1CEACE9C815C96DE` |
