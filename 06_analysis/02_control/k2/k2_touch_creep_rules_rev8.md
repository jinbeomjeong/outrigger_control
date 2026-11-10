# K-2 규칙 덧붙임 rev8 (결과 전, 2026-11-10)

- 작성: control-expert, 2026-11-10. 경로 2의 J 항목을 다시 쓴 새 작성자다. 이 작성자는 경로 1 코드를 연 적이 없다(1절 끝). 봉인 정보는 같은 폴더의 `k2_touch_creep_rules_rev8.sha256`.
- 원판(`a3658197…7263`), rev1(`5ba081c6…4776`), rev2(`b3f1b41f…94ea`), rev3(`8bcdb0ed…6e61`), rev4(`82160ff5…00c5`), rev5(`73b87758…eccc`), rev6(`21268203…ea0e`), rev7(`52d7dba9a058dd80555270b82452e145475822dbda6cf6e7542366a558e79840`)은 고치지 않는다. 아래만 덧붙인다. 서로 다르면 rev8 > rev7 > … > 원판 순으로 맞다.
- 시점: V-1~V-7 결과 0건.
  - 계기는 실행 전 네 번째 감사다. 경로 2의 이전 작성자가 경로 1의 행 판정 함수(D8x 경로 1 `d8x_judge.py`의 J1~J11·E-8 정의표)를 읽은 뒤 경로 2 첫 판을 썼다는 것이 확인됐다.
  - 사용자 결정(2026-11-10)
    1. 경로 2의 J 항목만 `d8x_recount` 기반으로 새 작성자가 다시 쓴다.
    2. 그 밖의 읽기는 공개하고 경로 2를 그대로 쓴다(rev7 2절과 같은 결정).
- **판정 항목·문턱·등급 규칙은 바꾸지 않는다.**

## 1. 독립성 공개 보완 (rev7 1절에 덧붙임, 사실 그대로)

rev7 1절의 목록은 세 번째 감사가 검색한 범위(`k2_judge.py`)에서 찾은 것만 옮겼다. 그래서 다른 경로 1 파일의 읽기가 빠져 있었다. 메인 세션이 경로 2 이전 작성자의 transcript(`subagents/agent-af7124b8517fd4c3a.jsonl`)의 tool_use를 경로 1 모듈 이름 전체로 다시 검색했다(KST 2026-11-10). 결과는 아래와 같다. 모두 결과 0건 시점의 일이다.

| 시각 | 행위 |
|---|---|
| 15:48:50 | `git ls-files \| grep d8x_recount\|d8x_judge\|d8x_record` |
| 15:49:17 | `d8x_judge.py`에 grep(def row_items/judge_row/J7/STROKE/WARN_PROBE/REJ_/J1_window/t_crawler_off 등) |
| 15:49:22 | Read `d8x_judge.py` 115~204행(J1~J11·E-8 정의표, `judge_metrics`). 4분 뒤 15:53:36에 경로 2 첫 판 Write |
| 17:37:07 | `sed -n 1,80p k2_record.py` + 키 grep |
| 17:37:23·26·32·35, 17:50:06, 17:51:09 | `k2_judge.py` grep·Read(rev7 1절에 이미 있음) |
| 17:45:10 | `acc_judge.py` `sed -n 1,50p` + `def`·`add_argument` grep |
| 18:10:58 | `git show c77ecf5:…/k2_v5_flatten.py \| sed -n 1,70p` |
| 18:11:16 | `k2_commands.json` grep(경로 1 커밋 c77ecf5 관련 git 조회 포함) |
| 18:49:21 | `acc_judge.py` `sed -n 79,110p` + regression·118·clip_ grep |
| 19:12:59 | Read `acc_judge.py` 42~276행 |
| 19:37:58·19:38:02 | `git show 5f22957:k2_judge.py` grep·sed 1270~1300(rev7 1절에 이미 있음), `git show 6a44ff8:run_with_identity.py` grep |
| 20:50:30 | `sed -n 85,100p run_with_identity.py` |
| 그 밖 | blob 해시 계산(`git rev-parse`·`hash-object`)과 기록 파일 sed 편집에 경로 1 이름이 나오는 것(내용 읽기 아님) |

- 빠졌던 파일: `d8x_judge.py`(J 정의), `k2_record.py`(K-2 행 기록 필드), `acc_judge.py`(V-5 회귀·사건 행), `k2_v5_flatten.py`(평탄화기), `run_with_identity.py`(래퍼), 그리고 `c77ecf5` 관련 git 조회.
- **1.6 J 항목 작성자의 범위**(이 판의 작성자)
  - 읽은 것: K-2 규칙 원판~rev7, `k2_dyn_spec.md` 머리말, D8x 규칙 원판 4.1절·6절 E 항목과 rev2 E-2 예외 줄(grep), `d8x_recount.py`와 그 시험 파일 이름, 경로 2 `k2_recount.py` 1.5와 그 시험, prelaunch의 `README.md`·`make_prelaunch.py`·`k2_fields.json`·`k2_prelaunch_v7.json`(path2 칸), `gs_evidence/`의 T-K2-7 재실행 로그 2개.
  - 열지 않은 것: 경로 1 파일 6개(`k2_judge.py`, `d8x_judge.py`, `k2_record.py`, `k2_v5_flatten.py`, `run_with_identity.py`, `acc_judge.py`)는 어느 커밋·blob도 열지 않았다. 감사 원문(`prelaunch/k2_prerun_audit*.md`, `k2_prerun_reaudit.md`, `d8x/*audit*`)과 경로 1 출력도 열지 않았다.
  - 한 번 있었던 일: 저장소 전체 `grep -rln "k2_recount"`(파일 이름만 출력)의 결과에 `k2_record.py`·`k2_v5_flatten.py`의 **파일 이름**이 나왔다. 그 파일의 줄은 출력되지 않았고 열지 않았다.
  - 1.5 코드는 경로 1을 읽은 작성자가 썼다. 1.6 작성자는 그 1.5 코드를 읽었다(경로 2 자신의 코드). 1.5에서 그대로 둔 부분은 2절의 "정렬된 정의"에 들어간다.

## 2. 조치

### 2.1 독립 확인으로 세는 것

- 경로 2 1.6(`k2_recount.py`)은 행 판정 항목을 `d8x_recount.py`(D8x 경로 2 1.0)의 함수로 계산한다. 원판 8절이 허용한 경로다. 새 작성자가 다시 썼다.
- G-F에서 아래 항목의 두 경로 일치는 **독립 확인**으로 센다.
  - J1~J11(V-2·V-3·V-4·V-6 행)
  - E-2·E-3
  - E-10(= D8x E-8, 이탈 뒤 구간 1 s)
  - J3 1 ms 재계산(원판 머리 표·5.1 J3·11절 E-8의 글로 다시 씀)

| K-2 규칙 | `d8x_recount` 함수 | 1.6 어댑터 |
|---|---|---|
| J1·J2·J3·J4·J5·J6(이동)·J7·J8·J9·J11, E-2·E-3 (5.1, 11절) | `harness_items`(내부 `num_item`·`list_item`·`classify_events`·`F_D8_N`·`J4_LIMIT_DEG`·`J5_LIMIT_S`·`J6_MOVING_BAR`·`J7_*`·`J9_ALLOWED`) | `_d8x_block`(필드 이름 변환), `_j_items`. 항목 이름 `J6_moving` → `J6`만 바꾼다(rev7 5절 대조 이름) |
| 사건 목록 해석 | `parse_events` | 그대로 호출 |
| J6 잠김 (D8x 4.1 "C, 필드가 있을 때") | `_chrono_j6_locked` | Chrono 행만. 필드가 없으면 적용 안 함 |
| J10 (Chrono) | `num_item` | 비교 `v == 0`은 D8x 4.1 J10 문턱 0이다. `d8x_recount._judge_chrono_row`는 verify json 형식을 읽어 이 행 형식에 부를 수 없어서, 그 함수와 같은 비교를 어댑터에 한 줄 둔다. 참/거짓 필드는 1/0으로 바꾼다(형식 변환) |
| J11 (하네스만) | `list_item` | Chrono 행에서는 뺀다(5.1 J11 "하네스") |
| E-10 = D8x E-8 | `e8_check` | 메시지 앞에 `E-10`을 붙인다 |
| J3 (1 ms, E-8) | – (D8x 경로 2는 행 필드를 읽음) | `j3_series_count`: TOUCH 끝(`t_touch`, 그 청크 포함) 뒤 네 패드 중 하나라도 법선력 ≤ 0 N인 1 ms 청크 수 |

- `d8x_recount.py`는 LF 내용 sha256 `46010967729e190ab572775db9dd59b083a3856558c3f07a239bf601bed9d9d1`(blob `d47c10e97662eb18c47c2a22f5f56990e6f4f115`, `dc2029b`)로 고정한다. 경로 2는 불러오기 전에 이 값을 대조하고, 다르면 종료 2(판정 불가)다.

### 2.2 정렬된 정의 (독립 확인 아님)

아래 부분은 두 경로가 일치해도 독립 확인으로 세지 않는다. 판정서에는 "정렬된 정의의 일치"로 적는다.

- **SH-1·SH-2**: `k2_record.py` 필드 이름 확인(17:37:07) 뒤에 쓴 부분.
- **V-5 회귀·사건 행 처리**: `_event_rows`·`_reg_verdicts` 등 `acc_judge.py`를 읽은 뒤 쓴 부분(17:45:10, 18:49:21, 19:12:59).
- **평탄화기 입력 형식**(18:10:58).
- **rev7 2절에 이미 있는 항목**: V-5 결과 종류, SH 결측 처리, kind·relative gate, manifest 형식과 V-6 D̂ 키, G8 c2 확인과 L1 공중 거짓 래치 계산.
- **1.6이 1.5에서 그대로 둔 행 판정 둘레의 처리**
  - 필드 지도(`k2_fields.json`)의 키 이름
  - 키가 행에 없으면 판정 불가로 두는 규칙
  - 하네스 행 J3 필드와 1 ms 재계산이 다르면 판정 불가로 두는 규칙
  - 시계열이 없으면 J3를 빼고 판정 불가로 두는 규칙(E-8)
  - J10 필드가 없으면 판정 불가로 두는 규칙
  - E-4·E-6·E-7·E-5·I-9 확인
  - `values`(SH 입력) 구성. SH-6 J2는 H4 구간이 있을 때만 쓴다(rev5 4절).

### 2.3 1.5 → 1.6 동작 차이 (결과 전, 규칙 문구 범위 안)

판정 항목·문턱은 그대로다. 아래는 같은 규칙을 D8x 경로 2의 해석으로 계산해서 생긴 차이다. 저장 D8x R-a 1,102행에서 1.5와 1.6의 `judge_row`를 행마다 맞대 봤다(점 파일 E-7 포함). 행 결과·실패 항목·항목별 참거짓·판정 불가 목록의 차이는 0행이다.

| 항목 | 1.5 | 1.6 (= D8x 경로 2) |
|---|---|---|
| J2 적용 범위("H4가 돈 행", D8x 4.1) | `reanchor_intervals_s`가 비어 있지 않은 행 | 그 구간이 있거나 `reanchor_started` 사건이 있는 행 |
| J7 사건 | 이름 전체가 세 접두어로 시작 | 기본 이름(`:` 앞)이 `FAULT_STROKE_END`·`WARN_LIFT_STROKE_LIMITED`와 같거나 `FAULT_LIFT_STROKE_LIMIT`로 시작 |
| E-2 결측 | None만 결측 | 유한한 수가 아니면 결측(NaN 포함, E-9) |
| 문자열 사건 `C2Event(t_s=…, name='…')` | 문자열 전체를 이름으로 봄 | 정규식으로 이름을 꺼냄 |
| J1·J2 선 $F_{D8}$ | 9,414.589 + 5,000 N | YAML 값 9,414.58911 + 5,000 N(차 0.11 mN). SH-6 선은 1.5 그대로 |

## 3. 도구 고정 (I-3, 원판 8절)

- **경로 2**: `04_scripts/03_control/k2/k2_recount.py` **1.6**, blob `82299dd2d43fa8d39fa312a750b353f693f0c133`. 1.5 blob `e1e16a9c5864e5a724f976eb6dda8456f14ff0a7`은 어느 결과에도 쓰이지 않았다.
  - 결과 전 확인(2026-11-10, dynamics-dev, E코어 `0x0FFF0000`):
    - `selftest-d8x`(저장 D8x `ra_off.json` `100985bf…cb10`, `ra_on.json` `e3c8c95f…247a`, 점 파일로 E-7 포함) 통과. K1 끔 910행 중 fail 68, K1 켬 192행 중 fail 6이고, 실패 항목은 모두 J3뿐이며 판정 불가 0이다.
    - 같은 selftest 안의 대조: 1,102행의 실패 J 항목 집합이 `d8x_recount.judge_ra`의 결과와 모두 같다(차이 0).
    - `selftest-v5-stored`, `selftest-screen`, `points-check` 통과.
    - 단위 시험 `05_tests/unit/test_k2_recount.py` 41건, `d8x/path2/test_d8x_recount.py` 55건 통과.
- **J 항목 의존 도구**: `06_analysis/02_control/d8x/path2/d8x_recount.py` 1.0(2.1절 sha).
- **경로 1**: `k2_judge.py` blob `74d72d5e1747e11c8b89e0adb177e952d3b598a7`. 바뀌지 않는다.
- **봉인 대조**
  - 경로 2 1.6의 봉인 대조(`--rules-dir`)는 1.5와 같다. 대상은 원판, rev1~rev6, `k2_dyn_spec.md`다.
  - 경로 1·2 모두 rev7·rev8 상수가 없다.
  - rev7·rev8 봉인(`.sha256` 첫 토큰 = raw 바이트 sha256)은 판정 전·후 감사가 `seal_check`로 대조한다.
