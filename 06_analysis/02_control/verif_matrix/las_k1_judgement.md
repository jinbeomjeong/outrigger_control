# LAS-b 경계 키 재개정 K1 판정서 (Y 묶음)

- 작성: control-expert, 2026-11-09
- 상태: **판정 후 감사 반영판.** 판정 후 감사(verif-protocol-auditor) 결과는 차단 0, 기록 6이고, 감사의 재집계도 모두 일치했다. 이 판은 기록 항목에 따라 문구만 고쳤다. 판정 등급과 결과 파일은 그대로다.
- **최종 판정: `통과`**(판정 도구 `status` `pass`, 종료 코드 0). 묶음별로 Y-0·Y-P·Y-S·Y-T 모두 `통과`다. `stop`·`미달`·`incomplete`는 없다.
- 두 경로 재집계 결과는 같다(8절). 비교한 236짝에서 수치 최대 차는 0.0이고, 불리언 불일치는 0이다.
- S-Ch(Chrono SCM 패치 1키)는 아직 돌리지 않았다. 순서는 9절에 적었다. K1 채택(프리셋 기본 켬)은 S-Ch 판정 뒤 사용자가 정한다(원판 9절).
- 규약: 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1, C2 음되먹임($u$ = 행정 속도 명령). 행정은 모터 행정 [m]이고 표에서는 mm로 적는다. 힘은 실린더 순 힘 [N]이다. 시각은 $\mathrm{round}(t/T_s)$ 정수 주기로 비교한다(원판 5.0.2).

## 0. 규칙·정체성·파일

### 0.1 규칙

| 파일 | sha256 | 봉인 시각 | 봉인 커밋(커밋 시각) | 차 |
|---|---|---|---|---|
| 원판 `las_k1_rules.md` | `2742c9760ad55a87eccbf73e84025aafe0171a3555e1f54ab19fab24d888e4a0` | 2026-11-09 16:24:49 +09:00 | `ea524f0`(16:25:47 +09:00) | +58 s |
| rev1 `las_k1_rules_rev1.md`(**결과 전**, K1 줄 0) | `eeee4ab9661babff50117b8ff579aa41e27a98d083f1fc13f46fb5c733e0b4d3` | 2026-11-09 17:13:20 +09:00 | `62fb8d7`(17:13:52 +09:00) | +32 s |

- 두 파일을 지금 다시 계산한 sha256이 위 값과 같다. 원시 바이트와 LF 정규화 값도 같다(`-text`, 경로 2).
- 이어받은 A안 규칙 6개(줄마다 기록되어 있고, 값은 `las_revA2_judgement.md` 0절과 같다)
  - `las_rev_targeted_rules` `bb235f27…`, 그 rev1 `672bc8f8…`
  - `las_revA_targeted_rules` `b09d004b…`, rev1 `c0251802…`, rev2 `9f478b7f…`, rev3 `98082a36…`
- 시간 순서(커밋 시각, +09:00)

| 시각 | 사건 |
|---|---|
| 16:24:49 / 16:25:47 | 원판 봉인 / 커밋 `ea524f0` |
| 16:50:32 | `a3a6580` CAD·S1~S3 그림 다시 렌더, 다리 신장 기구학 갱신(K1과 무관) |
| 16:53:46 | K1 코드·도구 `123e6da`(원판 봉인 **뒤**) |
| 16:54:33 | K1 구현 병합 `9405be9` |
| 17:02:53 | `86403d5` `leg_extension_loads.json` 재생성, 문서 행정·속도 값 표시(K1과 무관) |
| 17:13:20 / 17:13:52 | rev1 봉인 / 커밋 `62fb8d7` |
| 17:21:12 | `7c1bd09` S1/S2a/S2b 검증 재생성, S2a dt 연구 수정(K1과 무관) |
| 17:22:24 / 17:22:56 | 판정기·하네스 rev1 반영 `2268fa4` / 병합 `dec17d5` |
| 17:29:55 | S1/S2a/S2b 기록 재생성 병합 2건. K1 경로 밖 코드 변경(`run_S2a.py` +176/−43줄(변경 219줄), K1 하네스는 import하지 않음) |
| 17:35:00 | decision_log K1 결정 커밋 `c7123b5`(= 실행 HEAD, rev1 R1-4) |
| 17:35:31 ~ 18:38:14 | Y-0 → Y-P → Y-S → Y-T 실행(러너 로그) |
| 그 뒤 | 판정(이 문서) |

- 실행 중(17:35:31~18:38:14) master 커밋은 없다(rev1 R1-4). `git log` 마지막 커밋이 17:35:00 `c7123b5`다.

### 0.2 실행 정체성 (줄 563개 전체, 오류 줄 제외 562줄 집계)

| 항목 | 값 |
|---|---|
| `git_head` | `c7123b56f083629df4eb2e4bdd01b1b204adb484` 하나 |
| `git_dirty` / `dirty_files` | 거짓 / 빈 목록 하나 |
| `code_diff_sha256` | `e3b0c442…b855`(빈 해시) 하나 |
| 도구 sha256 집합 | 한 종류(13개 파일). `c2.py` `a75d2780…`, `k1_targeted.py` `0d2f8a8e…`, `k1_judge.py` `db361da6…`, `las_rev_judge.py` `5e1de65f…`, 그 밖 S2D 0.2절 9개 + `s2_defer_targeted.py` `d493c7ba…`. 지금 작업 트리 파일의 sha256과 같다 |
| 규칙 sha256 기록 | 8개 필드(위 0.1의 원판·rev1 + A안 6개) 한 종류 |
| 스레드 | MKL·OMP·OpenBLAS·Numba = 1, `MKL_THREADING_LAYER=TBB` 한 종류 |
| `controller_tag` | `final_C4G2_LAS`(V0) / `final_C4G2_P3_LAS`(VB) 두 값뿐 |
| 러너 마스크 | `0FFF5500`(기록, 정체성 항목 아님), 워커 16, env dynamics-dev |
| `k1.identity` = `rev.identity` | 562/562 참 |

- 후보 필드 집계(`sub_bundle` / `las_candidate` / `k1_candidate` / `k1.enabled`)

| 하위 | las | k1 | enabled | 줄 |
|---|---|---|---|---|
| Y-0a | P0 | K1off | 거짓 | 5 |
| Y-0b | P5r4 | K1off | 거짓 | 30 |
| Y-0c | P0 | K1off | 거짓 | 30 |
| Y-0d | P0 | K1off | 거짓 | 40 |
| Y-Pa | P0 | K1on | 참 | 165 |
| Y-Pb | P0 | K1on | 참 | 40 |
| Y-Sa | P0 | K1on | 참 | 30 |
| Y-Sb | P5r4 | K1on | 참 | 30 |
| Y-T | P5r4 | K1on | 참 | 192 |

- 실행 뒤 작업 트리: `04_scripts/02_chrono/render_S2_gifs.py`와 `run_S2a.py`가 수정 상태다. 실행 종료(18:38:14) 뒤의 변경이고, 실행과 무관하다.

### 0.3 결과 파일 (로컬 전용, `*.jsonl`은 git exclude)

| 파일 | 줄 | 바이트 | sha256 |
|---|---|---|---|
| `v5/las/k1/k1_Y0.jsonl` | 105 | 6,629,376 | `6ea12a8ed964832ec5abcca50f3943c7b4ea67ccd14520f8ef8eedbffcb00196` |
| `v5/las/k1/k1_YP.jsonl` | 206(오류 1 + 재실행 1 포함) | 3,880,711 | `0d985d5624f0fbb0219ca50d1c839b7db639011d6c2ab14fa9d84cfd197fc2c3` |
| `v5/las/k1/k1_YS.jsonl` | 60 | 5,865,933 | `a31153a64ed9cbdf7410082e8dbda81b79e6d607c0a238d510ac34c0c9333ac6` |
| `v5/las/k1/k1_YT.jsonl` | 192 | 26,276,501 | `84799f5c2628c3e38f2af28130abb3c57f000011adb1f2b2b1bad30e4533a335` |
| `v5/las/k1/judge_K1.json`(공식 판정 JSON, 이번에 만듦) | — | 116,184 | `b890a6112d15ca2f90c8e362d46b529f8903166cfdb4617a06e4344e5e6568dc` |

- `judge_K1.json`도 `.git/info/exclude`에 넣었다(로컬 전용). `judge_S.json`과 같은 관례다.
- 공식 판정 명령: `conda run -n dynamics-dev python -I 04_scripts\04_hydraulic\coupled\k1_judge.py --json-out 06_analysis\03_hydraulic\coupled\v5\las\k1\judge_K1.json`(`MKL_THREADING_LAYER=TBB`)
  - 종료 코드 0
  - 끝줄: `{"status": "pass", "bundles": {"Y-0": "pass", "Y-P": "pass", "Y-S": "pass", "Y-T": "pass"}, "reruns": {"Y-0": 0, "Y-P": 1, "Y-S": 0, "Y-T": 0}, "p3_baseline_false": 17, "c2_definition": "las_rev_judge.pair_violations (A rev1 R1-1)", "input_problems": 0}`
  - 러너가 마지막 묶음 뒤에 낸 `judge_after_Y-T.json`과 바이트 수가 같다(116,184).
- 기준 파일 sha256(경로 2에서 다시 계산, 모두 봉인 값과 같음)
  - S-C `s2d_SC.jsonl` `70e91ec1…08aa`
  - `revA_RS.jsonl` `7c407b6e…875d`
  - `revA_RP0.jsonl` `9be02caf…7300`
  - `revA_RT.jsonl` `c72f7e08…fd54`
  - L 줄: `las_T1` `3dee4f6b…`, `las_T2` `2fe6a54a…`, `fb_F3` `76be00cf…0bcf`, `fb_F4` `7e5716e6…`

## 1. 묶음별 판정

| 묶음 | 줄(기대) | 판정 도구 | 판정서 어휘 | 핵심 |
|---|---|---|---|---|
| Y-0 | 105(105) | `pass` | **통과** | 105/105 해시 = 저장값, 그림자 `would_block` 집합 = Q-0b |
| Y-P | 206(205, 재실행 1 포함) | `pass` | **통과** | 바뀐 키 = 부록 A 변경 예측 5키 정확히, 205짝 위반 0 |
| Y-S | 60(60) | `pass` | **통과** | Y-Sa 바뀐 키 1, Y-Sb 바뀐 키 2(예측 그대로). Y-Sb/Y-Sa 30짝과 C_SA 1짝 위반 0 |
| Y-T | 192(192) | `pass` | **통과** | 192/192 해시 같음, `decisions` 빈 줄 192 |

### 1.1 기준별 (K·H·C)

| 기준 | 결과 | 비고 |
|---|---|---|
| K-0 | 참 | 0.2절. 묶음 안·사이 정체성 한 종류, 규칙 기록에 원판·rev1 있음 |
| K-1 | 참 | `k1.enabled` = `k1_candidate` 562/562. R4c30을 평가한 LOC마다 `decisions` 항목이 있다 |
| K-2 | 참 | K1off 105줄에서 `applied` = `r4_due_without_gate`, `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED` 0건 |
| K-3 | 참 | K1on 457줄에서 `applied` = `r4_due_without_gate` ∧ ¬`would_block` |
| K-4 | 참 | `would_block_any` 거짓인 K1on 줄은 모두 K1off 기준 해시와 같다(위반 0) |
| H-1 | 참 | Y-0 105/105 같음(Y-0a 5 SC, Y-0b 30 RS, Y-0c 30 L 줄(F-3 16, F-4 14, RP0 대체 0), Y-0d 40 SC) |
| H-2 | 참 | Y-Pa 바뀐 키 5개, 목록 sha256 `4cdc9bfe…5da6` = 부록 A. Y-Pb 40/40 같음 |
| H-3 | 참 | Y-Sa 대 Y-0c 바뀐 키 1개(`7a7caafd…2d76`), Y-Sb 대 Y-0b 바뀐 키 2개(`56177ba0…c8a5`) |
| H-4 | 참 | Y-T 192/192 같음 |
| C-2형 | 위반 0 | Y-Pa 바뀐 5짝, Y-Sb/Y-Sa 30짝, C_SA 1짝. 경로 2는 Y-P 해시가 같은 200짝에도 적용했고 위반 0이다 |
| P3(rev1 R1-1) | 위반 0 | 236짝 전부. 해당 없음과 기준 거짓은 3절 |
| C-S | 위반 0 | 최대 증가 +0.316 mm(`D1\|H-S-A\|G1+J1@FR\|T\|diag-psa-soil\|K1\|VB\|e0`, Y-Sb/Y-Sa) ≤ 1 mm |
| C-F | 위반 0 | 규칙 4.3의 판정 범위 36짝(해시가 바뀐 Y-P 5, Y-S 30, C_SA 1)에서 센 값이다. 기준 ≥ 10,414.589 N인 짝의 후보 최소는 19,881.6 N(`H-R-A-J2`, Y-Sb)이다. 기준이 문턱 아래라 해당 없는 짝은 1개다: `D1\|H-R-A-S1\|rigid+S1@FL\|T\|flat\|K1\|VB\|e0`(5,745.3 N, 해시 같음). 참고로 236짝 전체에서는 후보 최소가 11,460.1 N(Y-Pa `H-R-A-S1` V0 e0, 해시 같음)이고, 기준이 이미 문턱 아래인 짝은 4개(그중 Y-Pa 3개, 해시 같음)다 |

### 1.2 H 해시 예측 대조

| 하위 | 짝 기준 | 같음 / 전체 | 바뀐 키 | 예측 |
|---|---|---|---|---|
| Y-0a·b·c·d | S-C / RS / L / S-C | 105 / 105 | 없음 | 없음 |
| Y-Pa | S-C | 160 / 165 | `D1\|H-S-A-J2\|G1+J2@FL\|T\|flat\|K1\|V0\|e0`, `…\|V0\|e0.002`, `…\|VB\|e0`, `…\|VB\|e0.002`, `D1\|H-S-A\|G1+J1@FL\|B\|flat\|K1\|V0\|e0.002` | 같은 5키 |
| Y-Pb | S-C | 40 / 40 | 없음 | 없음 |
| Y-Sa | Y-0c | 29 / 30 | `D1\|H-S-A-J2\|G1+J2@FL\|T\|flat\|K1\|VB\|e0` | 같은 1키 |
| Y-Sb | Y-0b | 28 / 30 | `D1\|H-S-A-J2\|G1+J2@FL\|T\|flat\|K1\|VB\|e0`, `D1\|H-S-A\|G1+J1@FL\|T\|flat\|K1\|VB\|e0` | 같은 2키 |
| Y-T | `revA_RT` | 192 / 192 | 없음 | 없음 |

- 주의: Y-Sb/Y-Sa **판정 짝**(4.3)에서 해시가 다른 짝은 5개다(`H-R-A-J2`, `H-R-A-stop`, 경계 키, J2 패치 키, `H-S-A|G1+J1@FR|diag-psa-soil`). 이 차이는 LAS-b 후보(P5r4 대 P0)에서 온다. H-3는 같은 LAS 후보끼리 K1 효과만 보는 것(Y-Sb 대 Y-0b, Y-Sa 대 Y-0c)이라 두 수는 다르다.

## 2. 핵심 키

### 2.1 경계 키 `D1|H-S-A|G1+J1@FL|T|flat|K1|VB|e0` — C-S **통과**

| 줄 | LAS / K1 | 토양 모드 | $n_P$ / $n_S$ / dP [주기] | R4c30 | LOC [s] | 최대 행정 [mm] | $F_{judged,min}$ [kN] | READY [s] | verdict |
|---|---|---|---|---|---|---|---|---|---|
| Y-0c | P0 / 끔 | 없음 | — (decisions 없음, $t_P$ 22.9 s) | 없음 | 23.5 | 438.764 | 42.793 | 60.3 | pass |
| Y-0b | P5r4 / 끔 | 23.8 s | 231 / 238 / **−7** | **적용**(그림자 `would_block` 참) | 24.1 | 468.863 | 40.684 | 59.7 | pass |
| Y-Sa | P0 / 켬 | 없음 | — | 없음 | 23.5 | 438.764 | 42.793 | 60.3 | pass |
| **Y-Sb** | P5r4 / 켬 | 23.8 s | 231 / 238 / −7 | **막힘**(`INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED`) | 24.1 | **438.647** | 40.684 | 61.1 | pass |

- 판정 짝 Y-Sb − Y-Sa: 최대 행정 **−0.116 mm**(−0.00011632527759158906 m) ≤ +1 mm → **C-S 통과**. revA2(P5r4 대 L)의 +30.10 mm 미달이 K1로 풀렸다.
- K1 효과(Y-Sb − Y-0b, 같은 P5r4): −30.216 mm다. R4c30 +30 mm가 빠진 만큼이다.
- 그 밖: C-2형 위반 0, P3 항목 없음(해당 없음), $F_{judged,min}$ −2.109 kN(40.684 kN ≥ 10.415 kN), READY Δt +0.8 s(+8주기, 기록만).
- Y-0c와 Y-Sa는 해시가 같다(`fae9b390…`). P0 경계 키는 토양 모드가 없어 R4c30 평가 자체가 없고, K1이 닿지 않는다.

### 2.2 패치 키 틈 목표 변화 (80 → 50 mm, 사용자 결정 2)

- K1이 막은 LOC에서는 R4c30(평지 토양 LOC 틈 목표 +30 mm)이 적용되지 않는다. 그래서 틈 목표가 80 mm에서 기본 50 mm로 돌아간다.
- 관측: 기준 줄은 `INFO_LOC_FLAT_SOIL_MARGIN` 1건, 후보 줄은 `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED` 1건이다(정확한 이름으로 셈).
- 결과 줄에는 틈 목표 값 필드가 없다. 그래서 50 mm는 최대 행정 감소와 R4c30 미적용 기록에서 간접으로 확인한 값이다.

| 키 (Y-Pa, P0+K1 대 S-C P0) | dP [주기] | 최대 행정 기준 → 후보 [mm] | Δ [mm] | $F_{judged,min}$ [kN] | READY 기준 → 후보 [s] | verdict / final |
|---|---|---|---|---|---|---|
| `D1\|H-S-A-J2\|G1+J2@FL\|T\|flat\|K1\|V0\|e0` | −5 | 503.657 → 473.693 | −29.964 | 27.766(같음) | 79.5 → 79.4 | pass / ready 유지 |
| `D1\|H-S-A-J2\|G1+J2@FL\|T\|flat\|K1\|V0\|e0.002` | −8 | 503.614 → 473.649 | −29.965 | 27.517(같음) | 80.2 → 80.1 | pass / ready 유지 |
| `D1\|H-S-A-J2\|G1+J2@FL\|T\|flat\|K1\|VB\|e0` | −8 | 503.687 → 473.677 | −30.009 | 28.868(같음) | 82.0 → 81.8 | pass / ready 유지 |
| `D1\|H-S-A-J2\|G1+J2@FL\|T\|flat\|K1\|VB\|e0.002` | −4 | 503.720 → 473.707 | −30.013 | 29.789(같음) | 81.3 → 81.1 | pass / ready 유지 |
| `D1\|H-S-A\|G1+J1@FL\|B\|flat\|K1\|V0\|e0.002` | −5 | 469.049 → 439.024 | −30.024 | 46.327(같음) | 60.4 → 60.2 | pass / ready 유지 |

- 5키 모두 $F_{judged,min}$이 비트 단위로 같다. 판정 최소 힘이 LOC 전에 정해지고, K1은 LOC 뒤 틈 목표만 바꾸기 때문이다(원판 0.1 "LOC 전 명령은 비트 단위로 같다"와 맞음).
- `d1.items` 8항목(G6-1~G6-7, READY)은 기준·후보 모두 참이다. FAULT·WARN 이름 집합도 같다. 마지막 키는 양쪽 모두 `WARN_PROBE_STIFFNESS_OUT_OF_RANGE`이고, 새로 생긴 것이 아니다.

### 2.3 C_SA 짝 (rev1 R1-3: Y-Sa 대 Y-0c, 해시가 바뀐 Y-Sa 키만)

| 키 | Y-0c → Y-Sa 최대 행정 [mm] | Δ [mm] | $F_{judged,min}$ [kN] | READY [s] | C-2형 | P3 | C-S | C-F |
|---|---|---|---|---|---|---|---|---|
| `D1\|H-S-A-J2\|G1+J2@FL\|T\|flat\|K1\|VB\|e0` | 503.687 → 473.677 | −30.009 | 28.868 → 28.868 | 82.0 → 81.8(−2주기) | 0 | 해당 없음(항목 없음) | 통과 | 통과 |

- dP −8(n_P 232, n_S 240)이다. Y-Pa의 같은 키와 같은 값이다(같은 줄 설정).

## 3. P3 (rev1 R1-1)

- 위반: 0(236짝).
- 해당 없음(양쪽 모두 `P3-1*`·`P3-5*` 항목 없음): Y-Pa 129, Y-Pb 16, Y-Sb/Y-Sa 20, C_SA 1. 두 경로 같다.
- **`p3_baseline_false` 17건**(기준 거짓 → 판정 제외 목록, 두 경로 같음)

| # | 짝 | 키 | 항목 | 후보 verdict / final | FAULT·WARN(기준·후보 같음) |
|---|---|---|---|---|---|
| 1·2 | Y-Pb/S-C | `D1\|H-S-0\|J2\|B\|fdown-rec\|K1\|V0\|e0.002` | P3-1, P3-5 | allowed_stop / fault | `FAULT_LIFT_STROKE_LIMIT`, `WARN_LIFT_STROKE_LIMITED` |
| 3·4 | Y-Pb/S-C | `D1\|H-S-0\|J2\|B\|fup-rec\|K1\|V0\|e0` | P3-1, P3-5 | allowed_stop / fault | 같음 |
| 5·6 | Y-Pb/S-C | `D1\|H-S-0\|J2\|B\|fup-rec\|K1\|V0\|e0.002` | P3-1, P3-5 | allowed_stop / fault | 같음 |
| 7·8 | Y-Pb/S-C | `D1\|H-S-0\|J2\|M\|fup-rec\|K1\|VB\|e0` | P3-1, P3-5 | allowed_stop / fault | 같음 |
| 9 | Y-Pb/S-C | `D1\|H-S-0\|J2\|M\|roll+rec\|K1\|V0\|e0` | P3-1 | fail / ready | 없음 |
| 10 | Y-Pb/S-C | `D1\|H-S-0\|J2\|M\|roll+rec\|K1\|V0\|e0.002` | P3-1 | fail / ready | 없음 |
| 11·12 | Y-Pb/S-C | `D1\|H-S-0\|J2\|T\|diag-rec\|K1\|VB\|e0.002` | P3-1, P3-5 | allowed_stop / fault | `FAULT_LIFT_STROKE_LIMIT`, `WARN_LIFT_STROKE_LIMITED` |
| 13·14 | Y-Pb/S-C | `D1\|H-S-0\|J2\|T\|fup-rec\|K1\|V0\|e0` | P3-1, P3-5 | allowed_stop / fault | 같음 |
| 15 | Y-Pb/S-C | `D1\|H-S-0\|J2\|T\|roll+rec\|K1\|VB\|e0` | P3-1 | fail / ready | 없음 |
| 16·17 | Y-Sb/Y-Sa | `D1\|H-S-0\|J2\|T\|diag-rec\|K1\|VB\|e0` | P3-1, P3-5 | allowed_stop / fault | `FAULT_LIFT_STROKE_LIMIT`, `WARN_LIFT_STROKE_LIMITED` |

- 17건 모두 해시가 같은 짝이다. 그래서 후보와 기준의 결과가 같다.
- 이 키들은 저장 S-C·revA2에서 이미 기준 거짓이었다. SGS 의도 정지(`allowed_stop`, `FAULT_LIFT_STROKE_LIMIT`)가 7키이고, `fail`/ready인 J2 `roll+rec`가 3키다. 두 무리 모두 저장 S-C 줄과 해시·verdict가 같다.
- **예상과 다른 점(공개)**: rev1 R1-1은 "예상: Y-S 짝 `diag-rec` 2건, 그 밖에 R-S의 SGS 정지 키가 있으면 같이"라고만 적었다. 실제로는 Y-Pb(S-C 비R4 표본 40키)에서 15건이 더 나왔다.
  - R1-1의 적용 범위("4.3의 모든 짝")에 Y-Pb가 들어 있으므로, 정의대로 세면 이 15건이 맞다.
  - 예상 문구가 Y-Pb를 빠뜨렸을 뿐이고, 판정에는 영향이 없다.

## 4. 그림자 기록과 dP 분포 (체크리스트 7, Q-0b·Q-0c)

| 하위 | `would_block` 참 키 | Q-0b 예측 | `decisions` 항목 | R4 due / applied | `INFO_LOC_FLAT_SOIL_MARGIN` / `_SKIPPED`(정확한 이름) |
|---|---|---|---|---|---|
| Y-0a | 부록 A 변경 예측 5키 | 5/5 | 5 | 5 / 5 | 5 / 0 |
| Y-0b | 경계 키(dP −7), J2 패치 VB e0(dP −15) | 2키 | 12 | 11 / 11 | 11 / 0 |
| Y-0c | J2 패치 VB e0(dP −8) | 1키 | 11 | 10 / 10 | 10 / 0 |
| Y-0d | 없음 | 0 | 11(R4 due 0) | 0 / 0 | 0 / 0 |
| Y-Pa | 5키 | — | 165 | 165 / 160 | 160 / 5 |
| Y-Pb | 없음 | — | 11(R4 due 0) | 0 / 0 | 0 / 0 |
| Y-Sa | J2 패치 VB e0 | — | 11 | 10 / 9 | 9 / 1 |
| Y-Sb | 경계 키, J2 패치 VB e0 | — | 12 | 11 / 9 | 9 / 2 |
| Y-T | 없음 | — | 0(192줄 모두 빈 목록) | 0 / 0 | 0 / 0 |

- Q-0b: 네 하위 모두 예측 집합과 같다(두 경로 같음). SK-3은 걸리지 않았다.
- dP 분포
  - Y-Pa 165줄: −8 ~ +96주기. ≤ 0인 줄은 정확히 변경 예측 5키(−8 ~ −4)다.
  - Y-0b·Y-0c(R-S)의 R4 평가 줄
    - 진짜 연약 지면 18줄(H-S-0 J1·J2 평지, H-S-1, H-S-C, H-R-A-S1, 두 하위 합): +31 ~ +96주기
    - 패치 키: −15 / −8 / −7
  - Y-0d·Y-Pb의 `decisions` 11항목은 모두 R4 due 거짓이다(경사 여유 쪽 LOC, dP −5 ~ +13). `D1|H-S-0|J2|T|diag-rec|K1|VB|e0`도 R4 due 거짓이다(dP +13).
- 경로 2는 `decisions`의 $t_P$·$t_S$에서 $n_P$, $n_S$, dP, `would_block`, `applied`를 다시 계산했다. 562줄 모두 기록값과 같고, R4 사건 수 = `applied` 수, `_SKIPPED` 사건 수 = K1on `would_block` 수다(불일치 0).

## 5. 사전 예측 대조 (원판 5절 전부)

| # | 예측 | 관측 | 맞음 |
|---|---|---|---|
| Q-0a | 105/105 해시 같음 | 105/105 | 참 |
| Q-0b | 그림자 `would_block`: Y-0a 5/5, Y-0b 2키, Y-0c 1키, Y-0d 0 | 같음(4절) | 참 |
| Q-0c | 진짜 연약 지면 R4 평가 행 dP ≥ +20 | 18줄, 최소 +31 | 참 |
| Q-P1 | 바뀐 키 = 부록 A 5키 | 같음 | 참 |
| Q-P2 | 5키 최대 행정 25~35 mm 감소, C-S 위반 0 | 29.964 / 29.965 / 30.009 / 30.013 / 30.024 mm 감소, C-S 위반 0 | 참 |
| Q-P3 | 5키 C-2형·P3·새 FAULT·WARN 0 | 5/5 위반 0(P3는 항목 없음 = 해당 없음) | 참 |
| Q-P4 | READY Δt ≤ 0, ≥ −5 s | −0.1, −0.1, −0.2, −0.2, −0.2 s | 참 |
| **Q-S1** | 경계 키 Y-Sb − Y-Sa Δ ∈ [−1, +1] mm, 중앙 +0.1 mm, C-S 통과 | **−0.116 mm**, C-S 통과 | 참(범위 안. 중앙값 +0.1과는 부호가 반대이고 0.22 mm 차이) |
| Q-S2 | J2 패치 VB e0 두 쪽 모두 R4c30 막힘, Δ ∈ [−1, +1] mm | 두 쪽 막힘(dP −8 / −15), Δ **+0.034 mm** | 참 |
| Q-S3 | 나머지 18 D-1 짝 + verdict 사례 10짝이 revA2와 같은 결과(C-2형·C-F·C-S 통과) | 28/28 통과 | 참 |
| Q-S4 | Y-S `통과` | `통과` | 참(판정 도구 예측 표는 이 행을 `null`로 남김. 묶음 판정으로 채움) |
| Q-T1 | 192/192 같음, `decisions` 빈 줄 192 | 192 / 192 | 참 |
| Q-C1~Q-C4 | S-Ch | 아직 실행 안 함 | 판정 안 함(9절) |

- Q-S1 근거식("revA2 +30.10 − R4 30 = +0.10 mm")은 Y-Sa가 P0 경로라는 점을 반영하지 못했다. 실제 Δ는 P5r4와 P0의 R4 없는 경로 차(−0.116 mm)다. 범위 예측은 맞았다.

## 6. 재실행 1건 공개 (SK-2, rev1 R1-5 항목 1)

| 항목 | 값 |
|---|---|
| 키 | Y-Pa `D1\|H-S-1\|S1\|M\|flat\|K1\|V0\|e0.002`(러너 진행 100/205) |
| 1회차 | 오류 줄. `install: TimeoutExpired(['git', '-C', 'C:\\workspace\\outrigger_control', 'rev-parse', 'HEAD'], 60)`, `rev.attempt` 1 |
| 2회차 | 같은 정체성으로 자동 재실행(러너 105/205번째 출력), `rev.attempt` 2, `rev.resumed` 거짓, 결과 pass, 해시 `7bdc61c8c3f1…` = S-C 저장값(Y-Pa 160 같음에 포함), dP +94(R4 적용) |
| 원인(추정) | 설치 단계의 `git rev-parse` 자식 프로세스가 60 s 안에 끝나지 않았다. 생성 직후 Suspended로 남는 git 프로세스 문제(알려진 문제)로 추정한다. 확인하지 않았다 |
| `--resume` | 쓰지 않았다(묶음 안 자동 재실행). 남은 오류 0 → `incomplete` 아님 |
| 기록 위치 | 러너 로그 `scratchpad\k1\logs\Y-P.log`, 판정 JSON `bundles.Y-P.reruns` |

- 두 경로 모두 재실행 키 1건, 오류 줄 1건을 셌다. 1회차 오류 줄은 판정에 쓰지 않았지만 파일에서 지우지도 않았다(206줄 = 205 + 1).

## 7. 공개 체크리스트

### 7.1 원판 8절 11항

| # | 항목 | 내용 |
|---|---|---|
| 1 | 규칙 sha256·봉인 시각·커밋 시각 대조 | 0.1절. 원판 +58 s, rev1 +32 s. 둘 다 봉인 뒤 커밋이고, K1 코드 커밋(16:53:46)은 원판 봉인 뒤, 실행(17:35:31)은 rev1 커밋 뒤다 |
| 2 | 봉인 전에 본 데이터 / 봉인 뒤 판정 전에 본 것 | 7.3절 |
| 3 | 정체성·후보 필드 집계 | 0.2절(한 종류씩, 후보 9행 집계) |
| 4 | resume, `--keys`·`--limit`, 목록 sha256 | `--resume` 미사용. 묶음 안 자동 재실행 1건(6절). 러너 명령에 `--keys`·`--limit` 없음(러너 로그 `Y-*: N runs`가 전체 건수). 결과 줄 키로 다시 계산한 목록 sha256이 9개 하위 모두 부록 값과 같다(A 165 `dc1e65d4…`, A5 5 `4cdc9bfe…`, B 40 `ef6c010d…`, C 30 `19c78b49…`, D 192 `4160bddf…`) |
| 5 | 본 뒤 버린 줄 | 없음 |
| 6 | 짝 없는 키·목록 밖 키·중복 줄 | 0 / 0 / 0. 기준 해시가 없는 키도 0이다 |
| 7 | 그림자 `would_block`·Q-0b·dP 분포 | 4절 |
| 8 | 사전 예측 대조표 | 5절 |
| 9 | 해당 없음 건수 | 3절(P3 해당 없음 129 / 16 / 20 / 1). C-F 기준 문턱 아래 1짝(판정 범위 36짝 기준, 1.1절). verdict 사례 10짝은 `d1`이 없어 C-S·C-F를 해당 없음(`NO_STROKE_FORCE`)으로 처리했다(10건). READY Δt None 짝: Y-Sb `H-R-A-stop`(양쪽 READY 없음, 정지 사례 키), `D1\|H-S-0\|J2\|T\|diag-rec\|K1\|VB\|e0`(양쪽 fault) |
| 10 | 두 경로 재집계 | 8절. 수치 최대 차 0.0(허용 1e-9) |
| 11 | 멈춤 | 없음. SK-1~SK-5가 하나도 걸리지 않았고, 사용자 결정·정보용 줄도 없다 |

### 7.2 rev1 R1-5 공개 항목

| # | 항목 | 내용 |
|---|---|---|
| 1 | SK-2 재실행 기록 | 6절. 하네스가 `rev.attempt`·`rev.resumed`를 남겼고, 판정기가 묶음별 재실행 키를 냈다(Y-P 1). 손으로 적을 필요는 없었다 |
| 2 | 경로 2 정확한 이름 일치 | `event_names`의 키를 `:`에서 잘라 이름만 같으면 셌다. 부분 문자열은 쓰지 않았다. `INFO_LOC_FLAT_SOIL_MARGIN`과 `_SKIPPED`를 따로 셌고(4절), 각각 `applied`·`would_block` 수와 줄마다 맞았다 |
| 3 | 실행 전 감사 결과 | verif-protocol-auditor 실행 전 감사: **차단 1**(R1-0: 원판 P3 절대값 읽기 → `D1\|H-S-0\|J2\|T\|diag-rec\|K1\|VB\|e0`가 해시와 무관하게 미달) / **실행 전 수정 1**(R1-2: C-2형 = A rev1 R1-1 `pair_violations` 승계) / **확인 필요 3**(R1-1 P3 범위, R1-3 C_SA 짝, R1-4 dirty 허용 목록) / **기록**(R1-5 항목 1·2, R1-4 실행 중 커밋 금지). 모두 rev1에 반영된 뒤 실행했다. 커밋 금지는 지켰다(0.1절). 실행 전 감사 기록(아래 7.2.1)도 옮겼다 |
| 4 | `P3_baseline_false` 목록·건수, C_SA 결과 | 3절(17건), 2.3절(위반 0) |
| 5 | rev1 sha256과 봉인·커밋 시각 | `eeee4ab9…`, 17:13:20 → `62fb8d7` 17:13:52(0.1절) |

#### 7.2.1 실행 전 감사 기록 (재감사 보고)

- **P3 None·None 미분류**: 기준과 후보가 모두 None인 경우는 분류하지 않는다. 실제 발생은 0건이다. P3 항목의 (기준, 후보) 값 쌍은 (참, 참) 123, (거짓, 거짓) 17뿐이다.
- 구현자의 해석 두 가지(원문). 재감사가 둘 다 rev1 원문과 맞다고 확인했다.
  - (a) 기준이 None이고 후보에 그 항목이 없으면 위반이 아니다. R1-1 원문이 "기준 없음 → 후보 **거짓**이면 위반"이므로 글자 그대로 일치한다.
  - (b) Y-P에서 해시가 같은 짝에도 P3를 적용한다. R1-1 "적용 범위: 해시와 관계없이 4.3의 모든 짝"에 따른 것이다.
    - 해시가 같은 Y-P 짝은 P3만 보고, C-2형·C-S·C-F는 보지 않는다.
    - 해시가 같은 Y-Sa 키에는 C_SA 짝을 맺지 않는다(R1-3).

### 7.3 봉인 전에 본 데이터와 봉인 뒤 판정 전에 본 것

- **원판 봉인 전**(원판 0.2절 그대로)
  - S-C `s2d_SC.jsonl` 456줄: $t_S$·$t_P$·$t_{LOC}$·`r4c30`·최대 행정 등. **K1 문턱(dP > 0)은 이 분포를 본 뒤 정했다.**
  - S-D 106줄과 S-D-info 19줄
  - `diagA.jsonl` 3줄
  - `revA_RS`·`revA_RP0`·`revA_RT`의 키·해시·R4 사건 유무
  - 판정서 3종, 명세 426.9·428·429.9
  - 따라서 **Y-P는 기구 확인일 뿐이다.** 표본 밖 근거는 Y-S의 P5r4 줄(경계 키 제외), Y-T, S-Ch다.
- **rev1 봉인 전**: 실행 전 감사 보고(위 7.2-3)와, 원판 0.2절에 이미 공개한 저장 줄(S-C, F-3 L, `revA_RS`)뿐이다. K1 결과 줄은 0줄이었다.
- **rev1 봉인 뒤 ~ 판정 전**
  - 러너 진행 로그 `Y-0.log`~`Y-T.log`(줄마다 결과 등급, 해시 앞 12자, `decisions` (dP, would_block))
  - 묶음마다 러너가 돌린 판정기 출력 `judge_after_Y-0`~`Y-T.json/log`
  - 메인 세션이 받은 최종 출력 요약
  - 이것들은 규칙이 정한 판정 절차의 출력이다. 이를 보고 바꾼 규칙·기준·문턱은 없다.

## 8. 두 경로 재집계

| 경로 | 방법 | 결과 |
|---|---|---|
| 1 | 판정 도구 `k1_judge.py`(sha256 `db361da6…`) → `judge_K1.json` | `pass` |
| 2 | control-expert 독립 집계 `recount_k1.py`. `k1_judge`·`las_rev_judge`·프로젝트 모듈을 import하지 않고, jsonl과 저장 기준 파일만 읽는다. C-2형·P3·C-S·C-F를 따로 구현했다 | 아래 표 |

| 항목 | 경로 1 | 경로 2 |
|---|---|---|
| 하위별 바뀐 키 집합(9개) | 1.2절 | 9/9 같음(목록 sha256 같음) |
| 그림자 `would_block` 집합(Y-0 4개) | 4절 | 4/4 같음 |
| 짝 수 | 236(165 + 40 + 30 + 1) | 236, 한쪽에만 있는 짝 0 |
| 짝별 `changed`·`fail`·C-2형 유무·P3·`cs_fail`·`cf_fail`·P3 해당 없음 | — | 불일치 0 |
| 행정 증가·$F$ 기준·$F$ 후보·READY Δt | — | 최대 절대 차 **0.0** |
| P3 해당 없음 | 129 / 16 / 20 / 1 | 같음 |
| `p3_baseline_false` | 17 | 17(같은 목록) |
| 재실행·오류 | Y-P 1 / 1 | 1 / 1 |
| K-1~K-4 재계산 | 통과 | 위반 0 |

- 경로 2는 판정 도구보다 범위가 넓다. Y-P 해시가 같은 200짝에도 C-2형·C-S·C-F를 적용했고, 위반은 0이다.
- 경로 2 파일(control-expert scratchpad `k1_judge\`)
  - `recount_k1.py` → `recount.json`
  - `show_recount.py`, `p3bf_rows.py`, `dump_judge.py`
  - 실행은 모두 `conda run -n dynamics-dev python -I`다.

## 9. 다음 단계: S-Ch (원판 3.5, 아직 실행 안 함)

- 대상: G1 바닥 + J2 패치@FL, 평지, 오거 상단. P0 대 P0+K1 **2행**(P5r4 아님).
- 순서(원판 3.5). Y 판정이 `통과`이므로 S-Ch로 갈 수 있다.
  1. **cad-expert 행 정의**: SCM 세트, 패드, `--threads`, `OMP_WAIT_POLICY`, P/E 풀, 시드, 볼록 껍질 훅 모드, 예상 실행 시간. (판정서 커밋 시점: 행 정의 코드 `las_k1_chrono_rows.py`·`run_S9.py --k1-order-gate`는 f805aba/f25b043에 들어 있고, `las_k1_sch_plan.md`는 봉인 전)
  2. control-expert가 행 정의와 원판 5.5 예측(Q-C1~Q-C4, 방향은 바꾸지 않음)을 묶어 **`las_k1_sch_plan.md` 봉인**
  3. **verif-protocol-auditor 실행 전 감사**(차단 0이어야 함)
  4. **실행**(compute-scheduler-expert 배치표, SCM 실행 규칙)
  5. 판정
- 이번 결과에서 S-Ch 예측에 쓸 사실(봉인할 때 공개할 것)
  - 하네스 J2 패치 키 dP는 −4 ~ −8(P0)이다(Y-Pa, Y-0c).
  - P0+K1의 최대 행정 감소는 29.96~30.01 mm다.
  - LOC 전 명령은 같다($F_{judged,min}$이 비트 단위로 같음).
- K1 채택(프리셋 기본 켬)과 LAS-b P5r4 후보의 처리는 S-Ch 판정 뒤 사용자가 정한다(원판 9절).
  - 참고: K1이 켜지면 revA2에서 P5r4를 미달시킨 경계 키 C-S(+30.10 mm)가 −0.116 mm로 풀린다(2.1절).

## 10. 한계

- 모든 근거는 하네스다. 표본 밖 근거는 Y-S(P5r4, 경계 키 제외)와 Y-T뿐이다. 잡음 등급, Chrono, 436.8 재개 묶음은 보지 않았다.
- 패치 키의 틈 목표 50 mm는 최대 행정 감소(≈30 mm)와 R4c30 미적용 기록으로 간접 확인한 값이다. 결과 줄에 목표값 필드가 없다.
- 재실행 원인(Suspended git)은 추정이다. 1회차는 설치 단계에서 끝나 플랜트 실행에 들어가지 않았다. 2회차 해시가 저장값과 같아 결과에는 영향이 없다.
- `p3_baseline_false` 17건은 기준 자체가 이미 거짓인 키(SGS 정지·J2 roll+rec)다. K1이 그 키들을 고치지도, 나쁘게 하지도 않았다는 뜻일 뿐이다.
