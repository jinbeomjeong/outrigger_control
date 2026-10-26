# S9 P3b control judgement scripts (spec rev. 60, 306~315)

`s6_control_spec.md` 개정 60(306~315절) S9 P3b 제어 판정에 쓴 후처리 스크립트다. 2026-10-26 세션 scratchpad `ctrl-run\`에서 옮겼다. 옮긴 뒤 다시 돌려 기존 산출물과 비트 단위로 같음을 확인했다.

- 실행 env: dynamics-dev. 저장소 루트에서 `conda run -n dynamics-dev python -I <파일> [인자]`.
- 경로는 파일 위치 기준이다(`ROOT = Path(__file__).resolve().parents[4]`). 인자를 생략하면 아래 기본 경로를 쓴다.
- 원자료 `07_results/`는 git 밖이다.

| 순서 | 스크립트 | 근거 절 | 입력(기본) | 출력 |
|---|---|---|---|---|
| 1 | `p3b_collect.py [<batch> [<out>]]` | 306·307(S-1 재구성)·309·310 | `07_results/S9/batch_P3b_20261026_122444/` | `06_analysis/02_control/s9/p3b/p3b_collect.json` |
| 2 | `p3b_loc_detail.py [<batch> [<out>]]` | 308.2·310 | 같은 배치(1의 `reconstruct_s1`을 import) | `06_analysis/02_control/s9/p3b/p3b_loc_detail.json` |
| 3 | `p3b_recheck.py [<batch> [<collect>]]` | 307(경로 2: P3-1·P3-3·P3-4) | 배치 + 1의 출력 | 표준 출력 |
| 4 | `p3b_probe_att.py [<collect> [<batch>]]` | 311(탐침 침하 → 자세 변화) | 1의 출력 + 배치 + `02_params/rexome33.yaml` | 표준 출력 |
| 5 | `p310_events.py [<batch>]` | 307(P3-10) | `07_results/S9/batch_P3-10_20261026_122444/` | 표준 출력 |
| 6 | `re1c_check.py [<events.json> ...]` | 307(RE1c R-1~R-4) | `07_results/S8/p3b_N_RE1c_Fs{0,8}_combined_*/N_RE1c_*/controller_events.json` | 표준 출력 |
| 7 | `p3b_table.py [<collect>]` | 306·315(표) | 1의 출력 | 표준 출력 |

- 3·4·7은 1의 출력을 읽는다. 5·6은 독립이다.
- `p3b_probe_att.py`의 패드 평면 위치는 YAML에 해당 키가 없어 근사값(x +2.0 / −2.7 m, y ±1.324 / ±1.168 m, **가정**)을 쓴다. 이때 "pad keys"와 "using fallback xy" 두 줄을 먼저 출력한다.
- `re1c_check.py`는 `result.json`이 아니라 `controller_events.json`을 읽어야 사건이 나온다(`result.json`에는 사건 목록이 없다).
