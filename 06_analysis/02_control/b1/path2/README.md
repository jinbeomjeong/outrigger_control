# B1 경로 2 재집계 (`b1_path2.py`)

- 작성: control-expert(경로 2 작성자), 2026-11-12. 봉인 규칙 `../b1_creep_rules.md`(sha256 `6b99702ce26d6da28fbfe6473b622c7e51419241916cbc101f795828f498774e`)의 문장만 보고 썼다. 경로 1(python-expert) 코드·출력·브랜치와 cad-expert 구현 코드는 열지 않았다.
- 의존: numpy와 표준 라이브러리만. YAML은 필요한 세 절(`superstructure`, `legs`, `pad_shapes`)을 작은 블록 YAML 읽기로 읽는다. 크롤러 모서리는 `c2.py`의 `CRAWLER_XY_BOX_M` 줄을 글자로 읽는다(import 안 함).

## 실행

```powershell
cmd /c "start /b /wait /affinity 0FFF0000 C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B <checkout>\06_analysis\02_control\b1\path2\b1_path2.py --repo <checkout> --batch <07_results\S9\batch_V5-B1-CREEP_*> --harness-jsonl <v5\b1\b1_H.jsonl> --p7-ref <s2d_SC.jsonl> [--keymap keymap.json] --constants-out b1_constants_path2.json --out b1_metrics_path2.json"
```

- 종료 코드: 0 = 묶음 `COMPLETE`/`PARTIAL`(등급 냄), 1 = `UNDETERMINED`, 2 = 입력·사용 오류, 3 = 내부 오류. 마지막 줄은 JSON 요약(`out_sha256` 포함).
- 자체 시험: `b1_path2_selftest.py --repo <checkout> --work <빈 scratch 폴더>`(합성 입력만, 실제 결과를 읽지 않음).

## 입력 키

- 봉인 규칙 6절이 이름을 정한 것은 R-C1(`n`, `load_read_N`, `att_raw_rad`, `c_hat_m`, `c_hat_corner_m`, `c_target_m`)과 R-G1 필드 이름이다. 나머지 파일 키(이벤트 목록 위치, `result.json`의 p3b 경로, 1 ms 계열 이름, 하네스 줄 필드)는 규칙이 prelaunch 키 목록에 맡겼다.
- 그래서 읽는 키는 모두 `DEFAULT_KEYMAP`에 있고, prelaunch 키 목록이 나오면 `--keymap` JSON(데이터)으로 맞춘다. 코드는 바꾸지 않는다. keymap 파일의 sha256은 판정서에 적는다.

## 문장 해석 (경로 1과 대조할 때 볼 곳)

| # | 규칙 | 이 구현의 읽기 |
|---|---|---|
| A-1 | M-4 `searchsorted(t, τ − 1e-9)` | 문자 그대로 왼쪽 searchsorted 인덱스(그 시각 이상 첫 표본). 1 ms 격자에 τ 표본이 있으면 "같은 시각 표본"이다 |
| A-2 | V-2 실행 정체성 | 경로 2는 `result.json`으로 확인되는 I-3(태그·`expect_controller.ok`), I-4(스레드 4), I-7(훅 fast·DLL sha)만 본다. 나머지 I 항목은 prelaunch·감사 몫이다 |
| A-3 | `c_hat_corner_m` 모서리 순서 | `c2.py` `CRAWLER_CORNER_NAMES` 순서(RR, RL, FR, FL)를 기본으로 둔다. prelaunch 키 목록이 다르면 keymap `corner_order`로 맞춘다 |
| A-4 | Q-1 `PressureForces.nominal` | R-C1 `load_read_N`의 LOC 주기 값으로 읽는다(규칙 6절 "판독 하중"). 다르면 keymap으로 다른 키를 가리킨다 |
| A-5 | M-12 Chrono 재구성 | R-G4 `imu_*` 외에 LOC별 $t_P$·경로(①②③)·정착 자세·행정 평면 모서리 틈 $c_k(t)$가 있어야 계산한다(keymap `m12_*`). 없으면 `NA`(규칙 7.5 허용) |
| A-6 | 하네스 침하 | 하네스 npz의 10 Hz 패드 침하를 주기 값으로 쓴다(1 ms 계열 없음) |
| A-7 | `t_max` 같은 최대 | 최대와 1×10⁻⁹ m 안의 가장 작은 주기. 다리별 $t_{\max,i}$도 같은 규칙 |
| A-8 | D-b 하네스 값 | Q-2 (a): 짝 H-P VB e0 실행의, Chrono 행 $b^\ast$ 다리 $\delta^{os}$ |
| A-9 | D-f 짝 제외 | H-M0 C5 짝 가운데 R4c30 사건이 있거나 유효하지 않은(Q-6) 줄은 뺀다 |
