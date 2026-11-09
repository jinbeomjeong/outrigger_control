# S-2 토양 모드 시작 유예(S2D) 판정서

- 작성: control-expert, 2026-11-09
- 상태: **판정 후 감사 반영판**. 새 봉인·코드 수정·재실행은 없다.
  - 감사(verif-protocol-auditor, 판정 후): 차단 0, 기록 7. 감사의 수치 재집계도 모두 일치했다.
  - 이 판은 감사가 요구한 기록 항목(앞 판들이 판정서에 적으라고 한 항목, 표기 정정, 등급 근거)을 넣었다. 판정과 결과 파일은 바뀌지 않았다.
- **최종 판정: S 판정 `미달`, S2D 기각.**
  - 근거: S-D가 SH-8로 멈췄다. 이때 SC-2 2짝, SC-S 4짝, 합 5짝이 위반이었다.
  - A 판정(P5r4S), A-P0, Chrono S-Ch는 하지 않는다(rev5 RS5-1). 그래서 A는 `not_run`이다.
- **한계 기록**
  - LAS-b 경계 키 `D1|H-S-A|G1+J1@FL|T|flat|K1|VB|e0`: 현 제어기(LAS-b b0)와 A안 후보 P5r4가 이 키에서 C-S 1짝 미달이다. 이를 개정하지 않고 알려진 한계로 둔다.
  - P0 J2 fdown 행정 예산 여유가 0.2~13.3 mm다(5절).
- 판정 도구 상태 문자열과 이 판정의 대응
  - 판정 도구 `judge_S.json`의 `status`는 `stop`이고 S는 `stop`(SH-8)이다. 이 판정서는 rev5 RS5-1에 따라 이를 **`미달`로 확정**한다.
  - 도구의 A `incomplete`는 rev5에 따라 `not_run`이다.
  - 도구의 asks `SH-6 Q-S2 missed: ask before A-S`는 A-S를 하지 않으므로 묻지 않고 공개로 닫는다(6절).
- 등급 근거
  - **미달**: rev5 RS5-1에 근거한다. S-D는 SH-8로 멈춰 216키를 실행하지 않았다. 그래서 원판 6절만으로는 `stop`이다. 이것을 `미달`로 확정하는 것은 rev5의 결정(위반이 이미 났고 기준은 위반 0을 요구함)에 기댄다.
  - **A `not_run`**: 원판 3절 순서(S 판정 → (통과 시) A-S)에 근거한다. S가 통과하지 않았으므로 A-S로 가지 않는다. rev5 RS5-1도 A-S·A-P0·S-Ch를 하지 않는다고 정했다.
  - **SH-6 asks**: 원판 6절 SH-6은 "다음 단계(A-S, S-Ch) 전에 멈추고 묻는다"이다. A-S·S-Ch를 하지 않으므로 물을 다음 단계가 없다. 그래서 공개(6절)로 닫는다.

## 0. 규칙·정체성·파일

### 0.1 규칙

| 파일 | sha256 | 시점 |
|---|---|---|
| 원판 `s2_soil_defer_rules.md` | `838bd27761b74fdbe6cd5148929d7af0489f63568c2efcebebd57869b4b2ab20` | 결과 전 |
| rev1 | `bc95453d7caf1d32408451e6d192cd3467407470202f9ae45999e372058807bd` | 결과 전 |
| rev2 | `3768a892b6d34fabc93841d82cf36fbac111f34a8193e1c0ea6046b9ff4a2a04` | 부분 결과 요약을 본 뒤(SC 기준 값은 안 봄), RS2-0 공개 |
| rev3 | `81bb429dec0ca48de7b188a438b8278d9bb5d0354f18d5874ba3c5c2092b34e8` | 부분 결과 요약을 본 뒤(SC 기준 값은 안 봄), RS3-0 공개 |
| rev4 | `5eb3f2f3802a087f983b9ce65113becfbcf7c5dffa6540ea34aad1bcaa2967d4` | 결과 전(13:59 rev3 실행분은 보지 않고 버림) |
| **rev5** | `0bed95a457e7b8b9c1eb12011b9e873155c455d25307c844a29636ea7b5ab137` | **사후 판**(S-D 106줄을 본 뒤). 바꾼 것은 정보용 실행 범위뿐이다 |

- 이어받은 A안 규칙: `las_rev_targeted_rules.md` `bb235f27…`·rev1 `672bc8f8…`, `las_revA_targeted_rules.md` `b09d004b…`·rev1 `c0251802…`·rev2 `9f478b7f…`·rev3 `98082a36…`
- 줄 기록
  - S-D 106줄의 규칙 sha256 기록은 원판~rev4와 A안 6개다.
  - S-D-info 19줄의 기록은 원판~**rev5**와 A안 6개다.
  - 묶음마다 한 벌이다.
- **rev5 시각 표기 오류(공개)**
  - rev5 본문 11행은 사용자 결정을 "2026-11-09 15시 30분대"로 적었다. 실제 사용자 결정은 rev5 봉인(15:25:26)과 봉인 커밋 `c93541b`(15:26:20 +0900) **전**이다.
  - 메인 세션 기록으로는 결정 직후 rev5 작성을 요청했다.
  - 봉인된 본문은 고치지 않는다. 시간 순서(결정 → rev5 봉인 → S-D-info 실행)는 바뀌지 않는다.

### 0.2 실행 정체성

| 묶음 | 줄 | `git_head` | dirty | 코드 diff | 스레드 | 마스크·워커 |
|---|---|---|---|---|---|---|
| S-0 | 9 | `d073326` | 없음 | `e3b0c442…`(빈) | MKL·OMP·OpenBLAS·Numba 1, `MKL_THREADING_LAYER=TBB` | 러너1 `0FFF5555`, 20 워커 |
| S-C | 456 | `d073326` | 없음 | 빈 | 같음 | 러너1 `0FFF5555`, 20 워커 |
| S-D | 106 | `d073326` | 없음 | 빈 | 같음 | 러너1 `0FFF5555`, 20 워커(15:04:24 시작, `wall_s` 504, exit 1 = SH-8) |
| S-D-info | 19 | `4545942`(rev5 병합) | 없음 | 빈 | 같음 | 메인 세션 실행. 로그(`SDinfo.log`)에 마스크 기록이 없다. 하네스는 스레드 1로 고정돼 있고, 마스크는 정체성 항목이 아니다 |

- 도구 sha256(줄 기록)
  - `c2.py`는 두 커밋 모두 `18f52a6035c8…`로 같다. rev5 RS5-2.3의 제어기 동일성이 성립한다.
  - 줄에 기록된 제어기·플랜트·하네스 경로 파일 9개가 S-D와 S-D-info에서 같다: `c2.py` `18f52a60…`, `fb_targeted.py` `27a8a5c7…`, `las_targeted.py` `e1e14a5f…`, `las_phase_diag.py` `65311a8f…`, `las_rev_targeted.py` `d6e09521…`, `las_rev_judge.py` `5e1de65f…`, `las_revA_targeted.py` `03b3008b…`, `las_revA_judge.py` `9771e416…`, `las_revA_diag.py` `e185fca3…`
  - 바뀐 것은 실행·판정 도구 두 개뿐이다(아래 표).
  - 플랜트 동일성 근거: `git diff --stat d073326 4545942`. 바뀐 파일은 다섯 개뿐이고 `03_src` 변경은 0이다.
    - `s2_defer_judge.py`, `s2_defer_targeted.py`(S2D 도구 두 개)
    - `test_s2_defer.py`(시험)
    - `s2_soil_defer_rules_rev5.md`·`.sha256`

| 도구 | S-D(`d073326`) | S-D-info(`4545942`) |
|---|---|---|
| `s2_defer_targeted.py` | `989364333f00…` | `d493c7ba6a92…` |
| `s2_defer_judge.py` | `62790027efe3…` | `c9dea77b0a5f…` |

- 판정 도구 실행(`4545942`, dynamics-dev, `MKL_THREADING_LAYER=TBB`)
  - 명령: `python -I -B 04_scripts/04_hydraulic/coupled/s2_defer_judge.py judge --info --json-out 06_analysis/03_hydraulic/coupled/v5/soil_defer/judge_S.json`
  - exit 1(S stop, 정상)
  - 기록: `seal_problems` 0, `identity_across_bundles` 0, info `identity_problems` 0

### 0.3 결과 파일 (로컬 전용, git exclude)

- jsonl 세 개는 git exclude이고 `.gitattributes` `-text` 대상이다. `judge_S.json`은 exclude라 커밋하지 않으며 `-text` 대상이 아니다.
- 줄의 이름표: S-D·S-D-info 줄의 `s2d.label` "P0"는 LAS 후보 이름(LAS-b b0)이다. S2D 후보 여부는 `s2d.candidate`(S-D·S-D-info는 `S2D`, S-C는 `P0`)로 본다. 둘을 혼동하지 않는다.

| 파일 | 줄 | sha256 |
|---|---|---|
| `v5/soil_defer/s2d_SC.jsonl` | 456 | `70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa` |
| `v5/soil_defer/s2d_SD.jsonl` | 106 | `16ca4e4f0a30cfff5e5da8445b2d9ddb31299dc43510b80f8cad5d47dd5a5787`(rev5 봉인 때와 같다. S-D-info 실행 뒤 `stored_files_after unchanged`) |
| `v5/soil_defer/s2d_SD_info.jsonl` | 19 | `9edde04b6e1fd5e28bddccc7dba4c7acff8c103f6460d84b6c26afe46838fb5d` |
| `v5/soil_defer/judge_S.json` | — | `d10d6f18dde3e37b1a6697aa608e12125f143bf6de3d68db67cd8b6fc236f0d0` |
| `history_pre_rev2/s2d_SC.jsonl`(SH-10 기준) | 456 | `ae0bda1f2e257b506663fec16c63c3cd0f5c8be7fad1b00126e4763c9e177d9d` |

## 1. 단계별 결과

| 단계 | 결과 |
|---|---|
| S-0 | 9/9 해시 일치(R-0 6, diagA P0·P5·P5r4 3), 오류 0 → pass |
| S-C | 456줄·456키, 오류 0. 토양 모드 301줄, 그림자 진입 68줄(평탄 진입 0, 기록 없음 0) |
| S-C 경합 조사(원판 7절) | 그룹별 `same_period`(래치 해제와 LOC가 같은 주기) / `within_n_d`(1~$N_d$주기 안): H-S-0 0/12, H-S-A 9/1, H-S-C-g 0/4, 나머지 그룹(H-S-1, H-S-C, H-S-A-J2, H-R-A-J2, H-R-A-S1) 0/0. 그림자 유예 진입 68(그룹별은 6절 표) |
| SH-9 | 19/19 같음 → pass |
| SH-10 | 456/456 같음(pre-rev2 S-C 기준) → pass |
| S-D | 341키(토양 301 + 무작위 40) 가운데 106줄째(15:12)에서 **SH-8 멈춤**. 러너 보고: runs 106, skipped 216, 오류 0 |
| S 판정 | **미달**(SC-2 거짓, SC-S 거짓) |
| S-D-info | 19/19, 오류 0, missing·extra 0, K 문제 0 → `complete`(정보용) |
| A-S, A-P0, S-Ch | 하지 않음(rev5) |

## 2. S 판정 (S-D 106줄, 짝 기준 S-C P0)

### 2.1 기준별

| 기준 | 결과 | 내용 |
|---|---|---|
| **SC-2** | **거짓** | 2짝(2.2 표) |
| SC-F | 참 | 위반 0 |
| **SC-S** | **거짓** | 4짝: Δ`stroke_max` +1.383 / +1.384 / +1.393 / +12.288 mm |
| SC-R | 참 | 해시 바뀐 49짝, READY 모집단 34. Δt 중앙 0.0 s, 최대 +0.2 s, 예외 0 |
| SC-T | 참 | 만료 38짝 모두 (a)~(d) 충족. 토양 모드 시작 지연 최대 0.5 s(규칙 상한) |
| K | 참 | K-S1~K-S6 위반 0(rev3 K-S6 포함). K-S3′ 2는 49/49 전부 대조(부분 0, 대신 0) |
| 참고 | — | 유예가 `loc`로 끝나 토양 모드를 피한 짝 11(SC-2 적용, 위반 0, 키는 2.1.1). Q-S3 참 |

#### 2.1.1 원판 5.1·7절과 rev1이 적으라고 한 항목

- **`loc`로 끝나 토양 모드를 피한 11짝**(`S.loc_avoided`, SC-2 위반 0)
  - J1 M fup-rec 4: `D1|H-S-0|J1|M|fup-rec|K1|V0|e0`, `…|V0|e0.002`, `…|VB|e0`, `…|VB|e0.002`
  - J1 T fup-rec 4: `D1|H-S-0|J1|T|fup-rec|K1|V0|e0`, `…|V0|e0.002`, `…|VB|e0`, `…|VB|e0.002`
  - J1 T roll-rec 3: `D1|H-S-0|J1|T|roll-rec|K1|V0|e0.002`, `…|VB|e0`, `…|VB|e0.002`
- **만료 38짝**: 키·사유·지연·(a)~(d)는 부록 A(`S.sc_t` 그대로)에 있다. 38짝 모두 (a)~(d) 통과다.
- **rev1 RS1-1 #3 공개**: 같은 주기에 만료 사유가 여럿이면 이름을 periods → stroke → window → rise 순서로 붙인다. 이 순서는 원판 1.2의 나열 순서(periods, stroke, rise, window)와 다르다. 이름표일 뿐이고 동작은 같다.
  - 이번 결과에서 사유는 periods·rise·loc뿐이다. 그래서 window와 rise의 순서 차이가 이름을 바꾼 짝은 없다.
- **rev1 RS1-3·RS1-7 공개**
  - 실제 유예 진입 가운데 $\lvert\Delta R\rvert$ < 1 N인 진입은 S-D 49건 중 0건, S-D-info 19건 중 0건이다. 키 없음.
  - 진입의 "감소 중"($R_k<R_{k-1}$)과 만료의 "상승 증가"($R_k\ge R_{k-1}$)는 엄격한 비교이고 **허용치가 없다**.
- **rev1 RS1-5 공개**: SC-T (c)(G6-1·G6-3·G6-7)가 해당 없는 짝은 102짝이고, 그 가운데 만료 짝이 38이다(`S.sc_t_c_not_applicable`). 이 짝들의 같은 위험은 SC-2(`d1.items` 전체의 새 실패)로 잡힌다.

### 2.2 SH-8 다섯 짝과 기제

| 키 | 기준 | 유예(시작, 사유, 주기) | P0 → S2D | 기제 |
|---|---|---|---|---|
| `D1\|H-S-0\|J1\|B\|roll-rec\|K1\|V0\|e0` | SC-S | 25.8 s, periods, 5 | 행정 +1.393 mm, READY 56.9 → 57.0 s | 거짓 LOC 26.4 s(실제 이륙 27.2 s) → `INFO_LOC_REVOKED` → 26.9 s 토양 모드 재시작 → 최종 LOC 27.7 s(P0 27.5) |
| `…\|V0\|e0.002` | SC-S | 25.9, periods, 5 | +1.384 mm | 같은 사슬 |
| `…\|VB\|e0` | SC-S | 27.6, periods, 5 | +1.383 mm | 같은 사슬 |
| `D1\|H-S-0\|J2\|B\|roll-rec\|K1\|V0\|e0.002` | SC-2 | 25.7, periods, 5 | 끝 단계 ready → level, Δ −0.31 mm, READY +0.2 s | READY 뒤 크리프로 pitch가 재레벨 문턱 0.07°(`c2.py` `relevel_attitude_rad`)를 넘었다(마지막 5 s 최대 0.0702°, P0 0.0692°). 67.1 s에 재레벨을 시작했고 끝 자세는 0.027°다 |
| `D1\|H-S-0\|J2\|M\|fdown-rec\|K1\|V0\|e0` | SC-2 + SC-S | 26.7, periods, 5 | +12.288 mm, ready → fault | 새 `FAULT_LIFT_STROKE_LIMIT:soil:FL`·`WARN_LIFT_STROKE_LIMITED` |

- 다섯째 짝의 사슬
  1. LOC 31.6 s가 취소됐다.
  2. 32.9 s에 토양 모드가 재시작되면서 S-4 기준 행정이 412 → 492.5 mm로 다시 잡혔다.
  3. 최종 LOC는 33.8 s다(P0 31.5 s).
  4. 38.4 s에 SGS 행정 가드 첫 주기에서 안전 정지했다.
  5. P0 여유는 12.96 mm였다.
- 다섯째 짝의 새 실패 항목: P3-1, P3-5, READY, SL-1, fault_ready
- 넷째 짝(J2 B roll-rec e0.002)은 정의상 SC-2 위반으로 남긴다. 다만 0.001° 차이로 문턱을 넘은 칼날 사례이고, 같은 키 e0의 S2D는 0.0700°로 넘지 않았다.
- 공통 기제(control-expert 원인 분석, jsonl 읽기 전용)
  - 유예 중에는 토양 모드 밀어 올림 하한(0.25 $v_{max}$ = 5.2 mm/s)이 없다. 그래서 가장 느린 다리 명령이 0~2.3 mm/s가 된다(`s2d.trace.defer_rows`).
  - 그 결과 `rise` 만료가 가려진다.
    - S-D 49짝 중 26짝은 P0 궤적 그림자가 2~3주기 `rise`로 끝났는데, 실제 S2D는 `periods`로 끝났다.
    - S-D 실제 끝 사유: periods 34, loc 11, rise 4
    - 68짝 전체: 그림자 rise·실제 periods 44짝, 실제 끝 사유 periods 52 · loc 12 · rise 4
  - 유예가 LOC 시각을 흔들고, L1gs 취소 → 재래치 → 토양 모드 재시작 사슬이 LOC 기준 클리어런스 목표를 옮긴다.
  - SC-S +1.4 mm 세 짝은 모두 취소 사슬이 있었다. 취소가 없는 쌍둥이(`J1|B|roll-rec|VB|e0.002`)는 LOC +0.2 s에 +0.25 mm였다.
  - 1.4 mm는 유예 중 쓴 행정이 아니다. 유예는 모두 행정 6 mm 조건 전에 끝났다.
- 기제 분석의 한계: jsonl에는 주기별 행정·Ŵ 기록이 없다. 그래서 취소가 일어난 이유(Ŵ 과소 추정 가설)와 1.4 mm의 분해는 이벤트 시각·기준 행정·하중 추적으로 추론했다.

### 2.3 진입 특징의 겹침 (설계 근본 한계)

| 키 | $R$ [kN] | $\bar L/W_{ref}$ | 결과 |
|---|---|---|---|
| 경계 키(diagA P5r4, 유예 값 근거) | 4.01 | 1.037 | LOC까지 3주기 |
| `J1\|B\|roll-rec`(SH-8) | 3.11 | 1.016 | 실제 이륙까지 1.4 s, 거짓 LOC |
| `J2\|M\|fdown-rec`(SH-8) | 7.82 | 0.909 | 크롤러가 하중 약 9 %를 받는 중 |

- 진입 특징($R$, $\bar L/W$)으로는 경계 키와 진짜 토양 키를 가를 수 없다. $k_d$나 0.85 문턱을 바꿔도 J1 키가 경계 키보다 안쪽에 있다.

## 3. 정보용 S-D-info 19키 (rev5 RS5-2, S 판정 불변)

- 선택: 19키, 목록 sha256 `56a7981738326e6ef37943e90277a220e70771f7683c045b0c6eb995a1102ca7`(rev5와 같다)
  - list·file 문제 0, 오류 0, missing·extra 0, 결정 불가 0
- K: K-S3′·K-S4·K-S5 위반 0. K-S3′ 2는 19/19 전부 대조했다.
- 해시: 19/19 모두 바뀌었다(유예 19).
  - 끝 사유: periods 18, loc 1(`H-S-A G1+J1@FL B flat V0 e0.002`, 1주기)
- 결과(악화 = SC-2·SC-F·SC-S 위반 짝, 개선 = P0가 READY가 아니었는데 S2D가 READY)

- 표는 `info.pairs` 그대로다(전체 19키). 시각은 s, Δ = S2D − P0. `H-S-0|J2|T|fdown-rec|VB|e0`는 P0·S2D 모두 `harness_settle_check_fail`(같은 실패)이고, `H-S-A|G1+J1@FL|B|flat|V0|e0.002`는 유예가 `loc`로 끝나 토양 모드를 피했다. `H-S-C-g|J1|M|fdown-rec|…|V0|e0`의 개선은 P0 `E-5_end_ready_att` 실패(끝 단계 level) 해소다.

| 키 | 유예 시작 [s] | 끝 사유 | 주기 | Δ행정 [mm] | READY Δt [s] | 최종 LOC Δt [s] | P0 → S2D 단계 | LOC 취소 P0/S2D | SC-2 | SC-S | 개선/악화 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `D1\|H-S-0\|J2\|B\|fdown-rec\|K1\|VB\|e0` | 28.5 | periods | 5 | -13.399 | — | -2.0 | fault → ready | 1/0 | 0건 | — | 개선 |
| `D1\|H-S-0\|J2\|B\|roll-rec\|K1\|VB\|e0` | 27.4 | periods | 5 | -0.320 | 0.2 | 0.1 | probe → probe | 0/0 | 0건 | — | — |
| `D1\|H-S-0\|J2\|B\|roll-rec\|K1\|VB\|e0.002` | 27.4 | periods | 5 | -0.319 | 0.2 | 0.1 | probe → probe | 0/0 | 0건 | — | — |
| `D1\|H-S-0\|J2\|M\|fdown-rec\|K1\|VB\|e0` | 28.6 | periods | 5 | 13.265 | — | 2.2 | ready → fault | 0/1 | 9건 | 위반 | 악화 |
| `D1\|H-S-0\|J2\|M\|fdown-rec\|K1\|VB\|e0.002` | 28.8 | periods | 5 | 0.089 | — | 0.1 | fault → fault | 1/1 | 0건 | — | — |
| `D1\|H-S-0\|J2\|T\|fdown-rec\|K1\|VB\|e0` | 28.7 | periods | 5 | -0.949 | -0.3 | 0.1 | ready → ready | 0/0 | 0건 | — | — |
| `D1\|H-S-A\|G1+J1@FL\|B\|flat\|K1\|V0\|e0.002` | 21.7 | loc | 1 | -30.024 | -0.2 | 0.0 | ready → ready | 0/0 | 0건 | — | — |
| `D1\|H-S-C-g\|J1\|B\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|V0\|e0` | 26.9 | periods | 5 | -1.712 | 0.2 | 0.5 | ready → ready | 0/0 | 0건 | — | — |
| `D1\|H-S-C-g\|J1\|B\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|V0\|e0.002` | 27.0 | periods | 5 | -1.432 | 0.2 | 0.5 | ready → ready | 0/0 | 0건 | — | — |
| `D1\|H-S-C-g\|J1\|B\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|VB\|e0` | 28.6 | periods | 5 | -0.423 | 0.2 | 0.5 | ready → ready | 0/0 | 0건 | — | — |
| `D1\|H-S-C-g\|J1\|B\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|VB\|e0.002` | 28.6 | periods | 5 | -1.196 | 0.2 | 0.4 | ready → ready | 0/0 | 0건 | — | — |
| `D1\|H-S-C-g\|J1\|M\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|V0\|e0` | 26.9 | periods | 5 | -2.018 | 0.2 | 0.4 | level → ready | 0/0 | 0건 | — | 개선 |
| `D1\|H-S-C-g\|J1\|M\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|V0\|e0.002` | 27.0 | periods | 5 | -1.228 | 0.0 | 0.4 | ready → ready | 0/0 | 0건 | — | — |
| `D1\|H-S-C-g\|J1\|M\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|VB\|e0` | 28.6 | periods | 5 | -0.697 | 0.2 | 0.4 | ready → ready | 0/0 | 0건 | — | — |
| `D1\|H-S-C-g\|J1\|M\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|VB\|e0.002` | 28.6 | periods | 5 | -0.721 | 0.3 | 0.5 | ready → ready | 0/0 | 0건 | — | — |
| `D1\|H-S-C-g\|J1\|T\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|V0\|e0` | 26.7 | periods | 5 | -0.945 | 0.2 | 0.5 | ready → ready | 0/0 | 0건 | — | — |
| `D1\|H-S-C-g\|J1\|T\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|V0\|e0.002` | 27.2 | periods | 5 | -0.635 | -0.3 | 0.5 | ready → ready | 0/1 | 0건 | — | — |
| `D1\|H-S-C-g\|J1\|T\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|VB\|e0` | 28.9 | periods | 5 | -0.700 | -0.4 | 0.5 | ready → ready | 0/1 | 0건 | — | — |
| `D1\|H-S-C-g\|J1\|T\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|VB\|e0.002` | 28.8 | periods | 5 | -1.249 | 0.3 | 0.4 | ready → ready | 0/0 | 0건 | — | — |

- 악화 1짝 `J2|M|fdown-rec|VB|e0`은 S-D의 FAULT 짝(`V0|e0`)과 쌍둥이다.
  - 원인 분석 보고에서 높은 가능성으로 예측했던 대로 같은 사슬이 반복됐다: 취소 → 최종 LOC +2.2 s → 행정 가드.
- H-S-C-g 12키는 모두 Δ −2.0 ~ −0.4 mm이고 SC-2 위반 0이다.
- 정보용이므로 SH-8은 적용하지 않았다. S 판정은 바뀌지 않는다.

## 4. J2 fdown 계열 FAULT (S-D 106줄 + S-D-info, `FAULT_LIFT_STROKE_LIMIT`)

| 키 | 출처 | FAULT | P0 → S2D 단계 | Δ행정 [mm] | P0 여유 [mm] |
|---|---|---|---|---|---|
| `J2\|B\|fdown-rec\|V0\|e0` | S-D | **lost** | fault → ready | −13.129 | 0.82 |
| `J2\|B\|fdown-rec\|V0\|e0.002` | S-D | both | fault → fault | +0.012 | 0.75 |
| `J2\|B\|fdown-rec\|VB\|e0.002` | S-D | both | fault → fault | +0.143 | 0.38 |
| `J2\|M\|fdown-rec\|V0\|e0` | S-D | **new** | ready → fault | +12.288 | 12.96 |
| `J2\|B\|fdown-rec\|VB\|e0` | info | **lost** | fault → ready | −13.399 | 0.39 |
| `J2\|M\|fdown-rec\|VB\|e0` | info | **new** | ready → fault | +13.265 | 13.33 |
| `J2\|M\|fdown-rec\|VB\|e0.002` | info | both | fault → fault | +0.089 | 0.19 |
| `J2\|T\|fdown-rec\|VB\|e0` | info | none | ready → ready | −0.949 | 11.65 |

- 집계: lost 2 / both 3 / new 2 / none 1. 판정 도구와 경로 2가 같다.
- **FAULT는 반복됐다.** 다만 양방향이다. S2D가 만든 FAULT 2와 없앤 FAULT 2가 같은 수다.
- P0 여유가 1 mm 안쪽인 키는 P0 자체가 FAULT다(both·lost). 여유 12~13 mm인 키에서 S2D가 FAULT를 새로 만든다.
- 해석: S2D의 일관된 효과가 아니다. LOC 시각 교란에 대한 **P0 행정 예산 경계의 민감도**다(5절).

## 5. 한계 항목: P0 J2 fdown 행정 예산 여유 0.2~13.3 mm

- 대상: S-C 그림자 진입 68키 각각의 P0 여유 = 682.8 mm(SGS 행정 가드) − P0 `d1.stroke_max_m`
  - 판정 도구 68키와 경로 2 68키는 키 집합이 같고, 최대 차는 0.0이다.
- 전체 범위: 0.03 ~ 213.75 mm
- J2 fdown 8키: 0.19, 0.38, 0.39, 0.75, 0.82, 11.65, 12.96, 13.33 mm
  - 이 가운데 P0 자체가 SGS로 멈추는 키가 5개다(4절 both 3 + lost 2의 P0 쪽).
- H-S-C-g J1 fdown 12키: 10.09 ~ 13.56 mm
- 68키 전체 값은 부록 C(`info.P0_margin.rows` 그대로)에 있다.
- **기록**
  - 현 제어기(LAS-b P0)는 J2(연약)·앞내림 회수 키에서 행정 예산이 0.2~13.3 mm만 남는다. LOC 시각이 0.1~2 s만 교란돼도 SGS 안전 정지 쪽으로 넘어간다.
  - SGS(P-S8-36)는 의도된 안전 정지(`allowed_stop`)라 안전 문제는 아니다. 그러나 READY 도달 여부가 LOC 시각에 칼날처럼 민감하다는 것은 S2D와 무관한 P0의 한계다.
  - 이 한계에 대응할지(행정 예산을 고려한 LOC·클리어런스 설계 등)는 별도 결정이다. 이 판정서는 기록만 한다.

## 6. 사전 예측 대조

| # | 예측 | 결과 |
|---|---|---|
| Q-S1 | 경계 키 P5r4S 유예 3주기 뒤 LOC, C-S 통과 | **평가 안 함**(A-S를 하지 않음) |
| **Q-S2** | S-C 그림자 진입 토양 모드 키 ≤ 그룹별 20 % | **어긋남**(아래 표) |
| Q-S3 | 만료 키의 토양 모드 시작 지연 ≤ 0.5 s | 참(38/38, 최대 0.5 s) |
| Q-S4 | A-S R-S 해시 바뀜 ≤ 4키 | 평가 안 함 |

| 그룹 | 그림자 진입 / 토양 모드 | 비율 |
|---|---|---|
| H-S-0 | 55 / 140(J1 39/68 = 57 %, J2 16/72 = 22 %) | 39.3 % |
| H-S-C-g | 12 / 20 | 60 % |
| H-S-A | 1 / 1 | 100 % |
| H-S-C, H-S-1, H-S-A-J2, H-R-A-S1 | 0 / 140 | 0 % |
| H-R-A-J2 | 0 / 0 | — |
| **전체** | **68 / 301** | **22.6 %**(> 20 %) |

- 봉인 전 가정이 틀렸다. 원판 0절과 4.2절은 "진짜 연약 지면에서는 래치 해제 때 크롤러가 아직 하중을 받아 $\bar L<0.85W$이거나 $R$이 크다"고 봤다. 원판 0절은 이것이 기록으로 확인하지 못한 가정이라고 이미 공개했다.
- 도구의 asks(SH-6, A-S 전 묻기)는 A-S를 하지 않으므로 묻지 않고 이 공개로 닫는다.

## 7. 공개 항목 (rev5 RS5-3 전부)

1. **개선 짝**
   - S-D의 `D1|H-S-0|J2|B|fdown-rec|K1|V0|e0`: P0 FAULT(행정 가드) → S2D READY, Δ −13.1 mm
   - S-D-info에서도 개선 2짝이 나왔다: `J2|B|fdown-rec|VB|e0` −13.4 mm, `H-S-C-g|J1|M|fdown-rec|V0|e0` P0 LEVEL → READY
   - 같은 정의(P0가 READY가 아닌데 S2D가 READY)로 S-D 106줄을 세면 개선은 3짝이다: 위 J2 B fdown V0 e0, `J1|M|fdown-rec|V0|e0`, `J1|M|fdown-rec|V0|e0.002`(둘 다 P0 level → S2D ready)
   - SC는 악화만 세므로 이것들은 판정에 들어가지 않는다. 효과가 양방향이라는 근거로 적는다.
2. **P0 J2 fdown 행정 예산 여유 0.2~13.3 mm**: 5절 한계 항목
3. **Q-S2 깨짐**: 22.6 % > 20 %(6절)
4. **원인 분석 요지**: 2.2·2.3절
   - 원판 1.3절은 "더 넓히면 진짜 토양에서 토양 모드 지연이 커진다"만 위험으로 봤다. 실제 위험은 유예의 구동 변화(하한 제거)가 LOC 사슬을 바꾸는 쪽이었다.
5. **감사 기록 7건**(아래 표)

| # | 감사 | 기록 |
|---|---|---|
| 1 | rev4 실행 전 | RS4-2의 "주기 기록이 없는 줄"은 코드에서는 원판 K-S3로 멈춘다(규칙보다 엄격한 쪽). 이번 S-D 106줄과 S-D-info 19줄에서 이 경로로 멈춘 줄은 0이다(K-S3′ 2 전부 대조 49/49, 19/19) |
| 2 | rev4 실행 전 | pre-rev4로 옮긴 S-C 줄은 0줄이다 |
| 3 | rev4 실행 전 | K-S6(A) 건수: A-S를 돌리지 않으므로 해당 없음 |
| 4 | S-D-info 실행 전 | 테스트 파일이 dirty 허용 목록에 있다. 하네스가 import하지 않는다 |
| 5 | S-D-info 실행 전 | resume을 쓰지 않았다(새 파일 한 번 실행) |
| 6 | S-D-info 실행 전 | `--keys`·`--limit`을 쓰지 않았다. 목록은 도구가 다시 계산해 sha256을 대조했다 |
| 7 | S-D-info 실행 전 | P0_margin 건수 68을 눈으로 확인했다(판정 도구 68 = 경로 2 68) |

- 추가 공개
  - S-D 러너 보고는 runs 106, skipped 216이었다. 341 − 106 − 216 = 19키는 멈춤 때 결과 줄이 없다. 그 19키가 S-D-info 대상과 같은지는 이 판정서에서 대조하지 않았다. S-D-info 대상은 rev5 정의(그림자 진입)로 다시 계산했다.
  - 돌리지 않은 216키는 원판 K-S1(24키)·K-S2(192키)에 따라 해시가 P0와 같아야 하는 키다. 실행으로 확인하지는 않았다.
  - S-D 106줄 가운데 그림자 없는 57줄의 K-S1·K-S2 위반은 0이다.
- **본 뒤 버린 줄(rev2 RS2-5, rev3 RS3-0, rev4 RS4-0)**: 아래 줄들은 판정에 쓰지 않았다.
  - rev2 전 S-C 456줄(`history_pre_rev2/s2d_SC.jsonl`): **본 뒤 버림**. 요약을 봤다(RS2-0). 판정에는 쓰지 않았고, rev3 SH-10의 해시 비교 기준(456/456 같음)으로만 썼다.
  - rev2 전 S-D 28줄(28줄째 `D1|H-S-0|J1|B|roll+rec|K1|V0|e0`에서 SH-3(K-S5)로 멈춤): **본 뒤 버림**(RS2-0·RS2-5)
  - rev2 재실행 S-C 일부(13:40~13:42, 몇십 줄, `history_pre_rev3`): 메인 세션도 control-expert도 보지 않고 버림(RS3-0)
  - rev3 실행(13:59 시작)의 S-0과 S-C 일부(`history_pre_rev4`): 보지 않고 버림(RS4-0)

## 8. 두 경로 재집계

- 경로 1: 판정 도구 `judge_S.json`(위 sha256)
- 경로 2: control-expert 독립 집계
  - 스크립트: `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\s2d_rca\recount.py`
  - 판정기를 import하지 않고 jsonl만 읽는다. C-2는 verdict pass → 비pass, 새 fail_items, items True → False, 단계 ready → 비ready, 새 FAULT·WARN 이름으로 직접 정의했다. SC-S는 Δ > 1 mm, SC-F는 10,414.589 N 문턱이다.

| 항목 | 경로 1 | 경로 2 | 일치 |
|---|---|---|---|
| S-D 해시 바뀜 / 유예 | 49 / 49 | 49 / 49 | 예 |
| S C-2 위반 키 | 2키(위 표) | 같은 2키 | 예 |
| S SC-S 위반 키 | 4 | 4(같은 키) | 예 |
| S SC-F 위반 | 0 | 0 | 예 |
| SH-8 짝 | 5 | 5 | 예 |
| READY(바뀐 짝, 둘 다 ready) | 모집단 34, 중앙 0.0, 최대 0.2 | n 34, 중앙 0.0, 최대 0.2 | 예 |
| info 짝별 Δ행정·SC-2 유무·SC-S·SC-F·개선·끝 사유·READY Δt(19짝) | — | 불일치 0(허용 1e-9) | 예 |
| info 악화 / 개선 | 1 / 2 | 같은 키 | 예 |
| J2 fdown 집계 | lost 2 / both 3 / new 2 / none 1 | 같음 | 예 |
| P0 여유 | 68키 | 68키, 키 집합 같음, 최대 차 0.0 | 예 |
| Q-S2 | 68 / 301, H-S-0 39.3 %, H-S-C-g 60 %, H-S-A 100 % | 같음 | 예 |

- 결론: 기준별 참·거짓, 개수, 수치(1e-9)가 두 경로에서 같다. **판정 확정.**

## 9. 결론과 다음

- S2D는 기각한다(S 판정 미달). 원인은 문턱이 아니라 설계다.
  - 진입 특징이 겹친다(2.3절).
  - 유예가 밀어 올림 하한을 없애 `rise` 만료를 가린다(2.2절).
  - SC-S 1 mm가 LOC 1주기 양자화(약 0.7~1.3 mm)보다 작다는 점은 부차적이다. 결과를 본 뒤 SC-S를 바꿔도 SC-2 위반이 남는다.
- LAS-b 경계 키 `D1|H-S-A|G1+J1@FL|T|flat|K1|VB|e0`는 현 제어기의 알려진 한계로 기록한다. P0 J2 fdown 행정 예산 여유(5절)도 별도 한계로 기록한다.
- 다음 방향(경계 키 재개정, 행정 예산 대응, 재개 검증 436.8 재개 여부)은 사용자 결정이다. 이 판정서는 제안하지 않는다.

## 부록 A. 만료 38짝 (`judge_S.json` `S.sc_t`)

| # | 키 | 만료 시작 [s] | 사유 | 토양 모드 지연 [s] | (a) | (b) | (c) | (d) |
|---|---|---|---|---|---|---|---|---|
| 1 | `D1\|H-S-0\|J1\|B\|fdown-rec\|K1\|V0\|e0` | 26.9 | periods | 0.5 | True | True | n/a | True |
| 2 | `D1\|H-S-0\|J1\|B\|fdown-rec\|K1\|V0\|e0.002` | 27.0 | periods | 0.5 | True | True | n/a | True |
| 3 | `D1\|H-S-0\|J1\|B\|fdown-rec\|K1\|VB\|e0` | 28.6 | periods | 0.5 | True | True | n/a | True |
| 4 | `D1\|H-S-0\|J1\|B\|fdown-rec\|K1\|VB\|e0.002` | 28.6 | periods | 0.5 | True | True | n/a | True |
| 5 | `D1\|H-S-0\|J1\|B\|fup-rec\|K1\|V0\|e0` | 28.8 | periods | 0.5 | True | True | n/a | True |
| 6 | `D1\|H-S-0\|J1\|B\|fup-rec\|K1\|V0\|e0.002` | 28.9 | periods | 0.5 | True | True | n/a | True |
| 7 | `D1\|H-S-0\|J1\|B\|fup-rec\|K1\|VB\|e0` | 30.6 | periods | 0.5 | True | True | n/a | True |
| 8 | `D1\|H-S-0\|J1\|B\|fup-rec\|K1\|VB\|e0.002` | 30.6 | periods | 0.5 | True | True | n/a | True |
| 9 | `D1\|H-S-0\|J1\|B\|roll+rec\|K1\|V0\|e0` | 24.0 | periods | 0.5 | True | True | n/a | True |
| 10 | `D1\|H-S-0\|J1\|B\|roll+rec\|K1\|V0\|e0.002` | 24.1 | periods | 0.5 | True | True | n/a | True |
| 11 | `D1\|H-S-0\|J1\|B\|roll+rec\|K1\|VB\|e0` | 25.8 | periods | 0.5 | True | True | n/a | True |
| 12 | `D1\|H-S-0\|J1\|B\|roll+rec\|K1\|VB\|e0.002` | 25.7 | periods | 0.5 | True | True | n/a | True |
| 13 | `D1\|H-S-0\|J1\|B\|roll-rec\|K1\|V0\|e0` | 25.8 | periods | 0.5 | True | True | n/a | True |
| 14 | `D1\|H-S-0\|J1\|B\|roll-rec\|K1\|V0\|e0.002` | 25.9 | periods | 0.5 | True | True | n/a | True |
| 15 | `D1\|H-S-0\|J1\|B\|roll-rec\|K1\|VB\|e0` | 27.6 | periods | 0.5 | True | True | n/a | True |
| 16 | `D1\|H-S-0\|J1\|B\|roll-rec\|K1\|VB\|e0.002` | 27.5 | periods | 0.5 | True | True | n/a | True |
| 17 | `D1\|H-S-0\|J1\|M\|fdown-rec\|K1\|V0\|e0` | 26.9 | periods | 0.5 | True | True | n/a | True |
| 18 | `D1\|H-S-0\|J1\|M\|fdown-rec\|K1\|V0\|e0.002` | 27.0 | periods | 0.5 | True | True | n/a | True |
| 19 | `D1\|H-S-0\|J1\|M\|fdown-rec\|K1\|VB\|e0` | 28.6 | periods | 0.5 | True | True | n/a | True |
| 20 | `D1\|H-S-0\|J1\|M\|fdown-rec\|K1\|VB\|e0.002` | 28.6 | periods | 0.5 | True | True | n/a | True |
| 21 | `D1\|H-S-0\|J1\|M\|roll-rec\|K1\|V0\|e0` | 25.9 | periods | 0.5 | True | True | n/a | True |
| 22 | `D1\|H-S-0\|J1\|M\|roll-rec\|K1\|V0\|e0.002` | 25.9 | periods | 0.5 | True | True | n/a | True |
| 23 | `D1\|H-S-0\|J1\|M\|roll-rec\|K1\|VB\|e0` | 27.6 | periods | 0.5 | True | True | n/a | True |
| 24 | `D1\|H-S-0\|J1\|M\|roll-rec\|K1\|VB\|e0.002` | 27.6 | periods | 0.5 | True | True | n/a | True |
| 25 | `D1\|H-S-0\|J1\|T\|fdown-rec\|K1\|V0\|e0` | 26.7 | periods | 0.5 | True | True | n/a | True |
| 26 | `D1\|H-S-0\|J1\|T\|fdown-rec\|K1\|V0\|e0.002` | 27.2 | periods | 0.5 | True | True | n/a | True |
| 27 | `D1\|H-S-0\|J1\|T\|fdown-rec\|K1\|VB\|e0` | 28.9 | periods | 0.5 | True | True | n/a | True |
| 28 | `D1\|H-S-0\|J1\|T\|fdown-rec\|K1\|VB\|e0.002` | 28.8 | periods | 0.5 | True | True | n/a | True |
| 29 | `D1\|H-S-0\|J2\|B\|diag-rec\|K1\|V0\|e0` | 30.1 | rise | 0.2 | True | True | n/a | True |
| 30 | `D1\|H-S-0\|J2\|B\|diag-rec\|K1\|V0\|e0.002` | 30.2 | rise | 0.2 | True | True | n/a | True |
| 31 | `D1\|H-S-0\|J2\|B\|diag-rec\|K1\|VB\|e0` | 31.9 | rise | 0.2 | True | True | n/a | True |
| 32 | `D1\|H-S-0\|J2\|B\|diag-rec\|K1\|VB\|e0.002` | 31.9 | rise | 0.2 | True | True | n/a | True |
| 33 | `D1\|H-S-0\|J2\|B\|fdown-rec\|K1\|V0\|e0` | 26.9 | periods | 0.5 | True | True | n/a | True |
| 34 | `D1\|H-S-0\|J2\|B\|fdown-rec\|K1\|V0\|e0.002` | 26.8 | periods | 0.5 | True | True | n/a | True |
| 35 | `D1\|H-S-0\|J2\|B\|fdown-rec\|K1\|VB\|e0.002` | 28.5 | periods | 0.5 | True | True | n/a | True |
| 36 | `D1\|H-S-0\|J2\|B\|roll-rec\|K1\|V0\|e0` | 25.6 | periods | 0.5 | True | True | n/a | True |
| 37 | `D1\|H-S-0\|J2\|B\|roll-rec\|K1\|V0\|e0.002` | 25.7 | periods | 0.5 | True | True | n/a | True |
| 38 | `D1\|H-S-0\|J2\|M\|fdown-rec\|K1\|V0\|e0` | 26.7 | periods | 0.5 | True | True | n/a | True |

## 부록 C. 그림자 진입 68키의 P0 행정 예산 여유 (`judge_S.json` `info.P0_margin.rows`)

여유 = 682.8 mm − P0 `d1.stroke_max_m`. 출처는 그 키를 S2D로 돌린 묶음이다.

| # | 키 | 출처 | P0 최대 행정 [mm] | 여유 [mm] |
|---|---|---|---|---|
| 1 | `D1\|H-S-0\|J1\|B\|fdown-rec\|K1\|V0\|e0` | S-D | 648.94 | 33.86 |
| 2 | `D1\|H-S-0\|J1\|B\|fdown-rec\|K1\|V0\|e0.002` | S-D | 649.19 | 33.61 |
| 3 | `D1\|H-S-0\|J1\|B\|fdown-rec\|K1\|VB\|e0` | S-D | 649.02 | 33.78 |
| 4 | `D1\|H-S-0\|J1\|B\|fdown-rec\|K1\|VB\|e0.002` | S-D | 649.74 | 33.06 |
| 5 | `D1\|H-S-0\|J1\|B\|fup-rec\|K1\|V0\|e0` | S-D | 682.60 | 0.20 |
| 6 | `D1\|H-S-0\|J1\|B\|fup-rec\|K1\|V0\|e0.002` | S-D | 682.65 | 0.15 |
| 7 | `D1\|H-S-0\|J1\|B\|fup-rec\|K1\|VB\|e0` | S-D | 682.51 | 0.29 |
| 8 | `D1\|H-S-0\|J1\|B\|fup-rec\|K1\|VB\|e0.002` | S-D | 682.52 | 0.28 |
| 9 | `D1\|H-S-0\|J1\|B\|roll+rec\|K1\|V0\|e0` | S-D | 584.67 | 98.13 |
| 10 | `D1\|H-S-0\|J1\|B\|roll+rec\|K1\|V0\|e0.002` | S-D | 586.36 | 96.44 |
| 11 | `D1\|H-S-0\|J1\|B\|roll+rec\|K1\|VB\|e0` | S-D | 586.40 | 96.40 |
| 12 | `D1\|H-S-0\|J1\|B\|roll+rec\|K1\|VB\|e0.002` | S-D | 586.60 | 96.20 |
| 13 | `D1\|H-S-0\|J1\|B\|roll-rec\|K1\|V0\|e0` | S-D | 607.93 | 74.87 |
| 14 | `D1\|H-S-0\|J1\|B\|roll-rec\|K1\|V0\|e0.002` | S-D | 607.67 | 75.13 |
| 15 | `D1\|H-S-0\|J1\|B\|roll-rec\|K1\|VB\|e0` | S-D | 607.69 | 75.11 |
| 16 | `D1\|H-S-0\|J1\|B\|roll-rec\|K1\|VB\|e0.002` | S-D | 607.93 | 74.87 |
| 17 | `D1\|H-S-0\|J1\|M\|fdown-rec\|K1\|V0\|e0` | S-D | 649.45 | 33.35 |
| 18 | `D1\|H-S-0\|J1\|M\|fdown-rec\|K1\|V0\|e0.002` | S-D | 648.43 | 34.37 |
| 19 | `D1\|H-S-0\|J1\|M\|fdown-rec\|K1\|VB\|e0` | S-D | 648.52 | 34.28 |
| 20 | `D1\|H-S-0\|J1\|M\|fdown-rec\|K1\|VB\|e0.002` | S-D | 648.63 | 34.17 |
| 21 | `D1\|H-S-0\|J1\|M\|fup-rec\|K1\|V0\|e0` | S-D | 682.39 | 0.41 |
| 22 | `D1\|H-S-0\|J1\|M\|fup-rec\|K1\|V0\|e0.002` | S-D | 682.41 | 0.39 |
| 23 | `D1\|H-S-0\|J1\|M\|fup-rec\|K1\|VB\|e0` | S-D | 682.41 | 0.39 |
| 24 | `D1\|H-S-0\|J1\|M\|fup-rec\|K1\|VB\|e0.002` | S-D | 682.46 | 0.34 |
| 25 | `D1\|H-S-0\|J1\|M\|roll-rec\|K1\|V0\|e0` | S-D | 612.68 | 70.12 |
| 26 | `D1\|H-S-0\|J1\|M\|roll-rec\|K1\|V0\|e0.002` | S-D | 612.66 | 70.14 |
| 27 | `D1\|H-S-0\|J1\|M\|roll-rec\|K1\|VB\|e0` | S-D | 612.71 | 70.09 |
| 28 | `D1\|H-S-0\|J1\|M\|roll-rec\|K1\|VB\|e0.002` | S-D | 612.62 | 70.18 |
| 29 | `D1\|H-S-0\|J1\|T\|fdown-rec\|K1\|V0\|e0` | S-D | 652.19 | 30.61 |
| 30 | `D1\|H-S-0\|J1\|T\|fdown-rec\|K1\|V0\|e0.002` | S-D | 650.07 | 32.73 |
| 31 | `D1\|H-S-0\|J1\|T\|fdown-rec\|K1\|VB\|e0` | S-D | 650.15 | 32.65 |
| 32 | `D1\|H-S-0\|J1\|T\|fdown-rec\|K1\|VB\|e0.002` | S-D | 650.27 | 32.53 |
| 33 | `D1\|H-S-0\|J1\|T\|fup-rec\|K1\|V0\|e0` | S-D | 681.77 | 1.03 |
| 34 | `D1\|H-S-0\|J1\|T\|fup-rec\|K1\|V0\|e0.002` | S-D | 681.98 | 0.82 |
| 35 | `D1\|H-S-0\|J1\|T\|fup-rec\|K1\|VB\|e0` | S-D | 682.00 | 0.80 |
| 36 | `D1\|H-S-0\|J1\|T\|fup-rec\|K1\|VB\|e0.002` | S-D | 682.10 | 0.70 |
| 37 | `D1\|H-S-0\|J1\|T\|roll-rec\|K1\|V0\|e0.002` | S-D | 662.37 | 20.43 |
| 38 | `D1\|H-S-0\|J1\|T\|roll-rec\|K1\|VB\|e0` | S-D | 662.40 | 20.40 |
| 39 | `D1\|H-S-0\|J1\|T\|roll-rec\|K1\|VB\|e0.002` | S-D | 662.52 | 20.28 |
| 40 | `D1\|H-S-0\|J2\|B\|diag-rec\|K1\|V0\|e0` | S-D | 682.77 | 0.03 |
| 41 | `D1\|H-S-0\|J2\|B\|diag-rec\|K1\|V0\|e0.002` | S-D | 682.66 | 0.14 |
| 42 | `D1\|H-S-0\|J2\|B\|diag-rec\|K1\|VB\|e0` | S-D | 682.43 | 0.37 |
| 43 | `D1\|H-S-0\|J2\|B\|diag-rec\|K1\|VB\|e0.002` | S-D | 682.51 | 0.29 |
| 44 | `D1\|H-S-0\|J2\|B\|fdown-rec\|K1\|V0\|e0` | S-D | 681.98 | 0.82 |
| 45 | `D1\|H-S-0\|J2\|B\|fdown-rec\|K1\|V0\|e0.002` | S-D | 682.05 | 0.75 |
| 46 | `D1\|H-S-0\|J2\|B\|fdown-rec\|K1\|VB\|e0` | S-D-info | 682.41 | 0.39 |
| 47 | `D1\|H-S-0\|J2\|B\|fdown-rec\|K1\|VB\|e0.002` | S-D | 682.42 | 0.38 |
| 48 | `D1\|H-S-0\|J2\|B\|roll-rec\|K1\|V0\|e0` | S-D | 644.24 | 38.56 |
| 49 | `D1\|H-S-0\|J2\|B\|roll-rec\|K1\|V0\|e0.002` | S-D | 644.29 | 38.51 |
| 50 | `D1\|H-S-0\|J2\|B\|roll-rec\|K1\|VB\|e0` | S-D-info | 644.29 | 38.51 |
| 51 | `D1\|H-S-0\|J2\|B\|roll-rec\|K1\|VB\|e0.002` | S-D-info | 644.32 | 38.48 |
| 52 | `D1\|H-S-0\|J2\|M\|fdown-rec\|K1\|V0\|e0` | S-D | 669.84 | 12.96 |
| 53 | `D1\|H-S-0\|J2\|M\|fdown-rec\|K1\|VB\|e0` | S-D-info | 669.47 | 13.33 |
| 54 | `D1\|H-S-0\|J2\|M\|fdown-rec\|K1\|VB\|e0.002` | S-D-info | 682.61 | 0.19 |
| 55 | `D1\|H-S-0\|J2\|T\|fdown-rec\|K1\|VB\|e0` | S-D-info | 671.15 | 11.65 |
| 56 | `D1\|H-S-A\|G1+J1@FL\|B\|flat\|K1\|V0\|e0.002` | S-D-info | 469.05 | 213.75 |
| 57 | `D1\|H-S-C-g\|J1\|B\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|V0\|e0` | S-D-info | 671.77 | 11.03 |
| 58 | `D1\|H-S-C-g\|J1\|B\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|V0\|e0.002` | S-D-info | 672.11 | 10.69 |
| 59 | `D1\|H-S-C-g\|J1\|B\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|VB\|e0` | S-D-info | 671.95 | 10.85 |
| 60 | `D1\|H-S-C-g\|J1\|B\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|VB\|e0.002` | S-D-info | 672.71 | 10.09 |
| 61 | `D1\|H-S-C-g\|J1\|M\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|V0\|e0` | S-D-info | 670.02 | 12.78 |
| 62 | `D1\|H-S-C-g\|J1\|M\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|V0\|e0.002` | S-D-info | 669.41 | 13.39 |
| 63 | `D1\|H-S-C-g\|J1\|M\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|VB\|e0` | S-D-info | 669.24 | 13.56 |
| 64 | `D1\|H-S-C-g\|J1\|M\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|VB\|e0.002` | S-D-info | 669.34 | 13.46 |
| 65 | `D1\|H-S-C-g\|J1\|T\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|V0\|e0` | S-D-info | 671.57 | 11.23 |
| 66 | `D1\|H-S-C-g\|J1\|T\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|V0\|e0.002` | S-D-info | 669.35 | 13.45 |
| 67 | `D1\|H-S-C-g\|J1\|T\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|VB\|e0` | S-D-info | 669.42 | 13.38 |
| 68 | `D1\|H-S-C-g\|J1\|T\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|VB\|e0.002` | S-D-info | 669.54 | 13.26 |
