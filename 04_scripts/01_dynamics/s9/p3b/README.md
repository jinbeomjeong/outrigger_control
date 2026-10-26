# S9 P3b dynamics judgement scripts (dynamics_model.md rev. 53, 5.37.10 / 5.38)

`dynamics_model.md` 개정 53(5.37.10 Δt 확인 D1·D2, 5.38 P3b 동역학 판정)에 쓴 후처리 스크립트다. 2026-10-26 세션 scratchpad `dyn-run\`에서 옮겼다. 옮긴 뒤 다시 돌려 중간 JSON 3개와 표준 출력이 기존과 비트 단위로 같음을 확인했다. 최종 JSON은 출처 필드 2개(`scripts_sha256_12`, `scripts_location`)만 다르다.

- 실행 env: dynamics-dev. 저장소 루트에서 `conda run -n dynamics-dev python -I <파일> [인자]`.
- 경로는 파일 위치 기준이다(`ROOT = Path(__file__).resolve().parents[4]`). 원자료 `07_results/S9/`는 git 밖이다.
- 중간 JSON은 작업 폴더(`<work>`, 저장소 밖 임시 폴더 권장)에 쓰고, 4가 합쳐 최종 JSON을 쓴다.

| 순서 | 스크립트 | 근거 절 | 입력 | 출력 |
|---|---|---|---|---|
| 1 | `p3b_judge.py <work>/p3b_judge.json` | 5.37.10(점검 1, D1·D2), 5.37.1, 5.38.1 | `batch_P3b_20261026_122444`, `batch_DT_20261026_122444`, `batch_P3a_20261026_092653`, `19_S9/s9_P3b_summary.json`·`s9_P2prime_summary.json`·`s9_P3a_summary.json` | 중간 JSON |
| 2 | `p3b_judge2.py <work>/p3b_judge2.json` | 5.38.4~5.38.6 | `batch_P3b_20261026_122444`, `s9_P3b_summary.json` | 중간 JSON + 표준 출력 |
| 3 | `p3b_roll_ratio.py <work>/p3b_judge.json <work>/p3b_roll_ratio.json` | 5.37.3·5.38.3 | 1의 출력, `s9_P3b_summary.json`, 배치 `result.json` | 중간 JSON + 표준 출력 |
| 4 | `merge_out.py <work> [<out>]` | 5.37.10·5.38 | 1~3의 출력 | `06_analysis/01_chrono/19_S9/s9_P3b_dyn_judgement_rev53.json`(기본) |
| — | `d2_check.py` | 5.37.10 D2 | `batch_DT_.../DT_P3a_G1_B_dt5e-5`, `batch_P3a_.../P3a_G1_B` | 표준 출력(값은 `merge_out.py`의 `D2_END_POINT`에 손으로 옮겨 둠) |
| — | `probe_sink.py [<batch>]` | 5.38 | `batch_P3b_20261026_122444` | 표준 출력(탐침별 침하 변화·자세 변화) |

- 4를 기본 출력으로 돌리면 기존 `s9_P3b_dyn_judgement_rev53.json`을 덮어쓴다. 이때 `scripts_sha256_12`(이 폴더 스크립트, 줄바꿈 LF로 맞춘 SHA-256 앞 12자)와 `scripts_location`이 바뀌어 파일 SHA-256도 문서에 적힌 `0821a94e8f57`과 달라진다. 값 비교만 할 때는 `<out>`을 임시 경로로 준다.
- 1·2·3은 `s9_P3b_summary.json`(재판정 전, `generator` `s9_batch_summary.py`)의 키(`departure`, `creep_stop`, `P3-2_loc`, `P3-4_attitude` 등)를 읽는다. 요약을 다시 만들면서 키가 바뀌면 결과도 달라질 수 있다.
