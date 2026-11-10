# D8x J3(패드 부상) 원인 진단 — 판정 아님

- 날짜: 2026-11-10. **진단이다.** 이 폴더의 결과는 봉인 규칙(`d8x_rules*.md`)의 판정에 쓰지 않는다(결과 파일 `meta.diagnostic = true`).
- 대상: `d8x_judgement.md`(main checkout, 미추적) 8절의 G1 실패 74행. 모두 J3(TOUCH 끝 뒤 1 ms 청크의 최소 패드 법선력 ≤ 0 N)만 실패했고, 저장 결과에는 어느 패드가 떴는지가 없었다.
- 도구: `04_scripts/03_control/touch_phase/acceptance/d8x_diag.py`(새 파일, `acc_d8.py`는 바꾸지 않음). `acc_d8.run_one`을 그대로 부르고, 같은 프로세스에 읽기 전용 기록기 두 개(`FlexPlant.step` 뒤 1 ms 청크마다, `HarnessAdapter.update` 뒤 제어 주기마다)를 단다. K1 팔·점 파일·태그·관문 설치는 D8x 경로(`d8x_record.install_k1_order_gate`, 프리셋 그대로)와 같다.
- 재현: 다시 돌린 5행 모두 `commands_sha256`, J3 수·최솟값, `t_touch`·`t_lift`·`t_ready`, 사건 목록이 저장 행(`ra/ra_off.json`)과 **같다**(`rerun/rerun_summary.json`의 `stored_compare`). 시험 `05_tests/unit/test_d8x_diag.py`(기록기 유무로 같은 행, 저장 해시와 같음).

## 1. 실행 정체성

| 항목 | 값 |
|---|---|
| 코드 | 이 worktree, HEAD `ba6671c`(저장 R-a 실행과 같은 커밋), 추적 파일 변경 없음(`identity_start.git.is_clean`, 새 파일 `d8x_diag.py`는 실행 때 미추적). 커밋한 `d8x_diag.py`는 실행본과 import 묶음·`zip(strict=True)`·줄바꿈만 다르다(ruff 정리). 시험은 커밋본으로 저장 해시를 다시 확인했다 |
| 인터프리터 | `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B`(직접 호출, 저장 실행과 같음) |
| 스레드 | `MKL_THREADING_LAYER=TBB`, `MKL/OMP/NUMBA/OPENBLAS_NUM_THREADS=1` |
| 풀 | P코어 마스크 `0xFFFF`, (a) worker 5, (b) worker 8 |
| K1 | off(`k1_order_gate` false), 태그 `final_C4G2_LAS` |

## 2. (a) 패드 부상 기구

### 2.1 고른 행과 이유

| id | 저장 결과 | 고른 이유 |
|---|---|---|
| `main\|C2_tv0.1\|top\|upper\|pitch+` | fail, J3 131 | `pitch+`(3.7 꼭짓점, 실패 20/44) 상단의 td_main 행. K1 켬 팔에서도 같은 id가 fail(판정서 6.3). 같은 점 td_main 중 부상 청크가 가장 많다 |
| `main\|C2_tv0.1\|top\|rigid\|r+p+0.5` | fail, J3 14 | `r+p+0.5`(실패 17/44) 상단 td_main, 강체 마스트(가장 단순한 조건). K1 켬 팔에서도 fail |
| `main\|C2_tv0.1\|top\|upper\|d45-+` | fail, J3 232 | `d45-+`·`d45++` 중 td_main에서 실패한 유일한 행. K1 켬 팔에서도 fail |
| `main\|C2_tv0.1\|top\|rigid\|pitch+` | pass(최소 16.0 kN) | 첫 번째 행과 같은 점·상단, 마스트만 강체. 탐침 키라 판정서 67에서 통과 확인 |
| `main\|C2_tv0.1\|top\|rigid\|d45-+` | pass(최소 8.7 kN) | 세 번째 행과 같은 점, 마스트만 강체 |

### 2.2 결과

시각은 시뮬레이션 시각 [s], 힘은 패드 법선력(로드 축력 = $F_{cyl} + W_{rod}$, J3와 같은 값).

| id | 뜬 패드 | 0 N 구간(TOUCH 끝 기준) | 부상 시작 때 명령 [mm/s] FL FR RL RR | 크롤러 수직력 | 로킹(touch−2 s ~ 크롤러 이탈) | 뜬 다리 평균 하중(TOUCH~이탈) |
|---|---|---|---|---|---|---|
| pitch+ upper | RL, RR | 19.79~19.92(+0.19~+0.32 s) | 0 0 0 0(LEVEL 첫 명령은 19.80) | 263 kN, 접촉점 앞 8 / 뒤 2 | pitch 1.8 Hz, 각속도 진폭 0.71 °/s | 38 kN |
| r+p+0.5 rigid | RR | 19.782~19.795(+0.28 s) | 2.9 5.2 0 2.2(밸브 1.6 2.9 0 1.2) | 226 kN, 앞 8 / 뒤 3 | roll 2.5 Hz·pitch 3.0 Hz, 0.32·0.39 °/s | 34 kN |
| d45-+ upper | RL | 19.64~19.87(+0.14~+0.37 s) | 0 0 0 0 | 223 kN, 앞 8 / 뒤 3 | 1.9 Hz, pitch 0.37·roll 0.20 °/s | 27 kN |
| pitch+ rigid(통과) | – | 최소 16.0 kN(RR, +0.24 s) | – | 240 kN, 앞 8 / 뒤 2 | 2.5 Hz, pitch 0.37 °/s | 37 kN |
| d45-+ rigid(통과) | – | 최소 8.7 kN(RL, +0.28 s) | – | 203 kN, 앞 8 / 뒤 2 | 2.0~2.6 Hz, 0.43·0.51 °/s | 42 kN |

(로킹 주파수는 각속도 영점 교차로 셌다. 대략값이다.)

### 2.3 기구

1. **TOUCH 중에 이미 패드가 여러 번 0 N이 된다.** 다섯 행 모두(통과 두 행 포함) TOUCH 단계 안(17.5~19.5 s)에서 앞·뒤 패드가 번갈아 0 N까지 내려간다(예: pitch+ upper 후방 두 패드 19.02·19.31·19.46 s, d45-+ upper RL 19.17·19.41 s). J3 창(TOUCH 끝부터) 밖이라 기록되지 않았을 뿐이다.
2. **원인은 크롤러 위 상부체의 로킹(시소) 진동이다.** 크롤러가 아직 상부체 무게의 대부분(200~260 kN)을 받치고, 크롤러 접촉점은 앞쪽 8개 / 뒤쪽 2~4개라 크롤러 앞쪽이 받침점이 된다. 앞·뒤 패드 하중이 1.8~3 Hz로 반대 위상으로 흔들린다(후방 0 N일 때 전방 55~65 kN). TOUCH 명령은 다리별로 0 ↔ 5.23 ↔ 10.46 mm/s 계단(0.1 s 주기, 밸브 지연 0.1 s)이라 로킹을 계속 들뜨게 하는 것으로 보인다(**추정**, 가진원 분리 실험은 안 함).
3. **TOUCH 끝 판정은 로킹이 가라앉기 전에 내려지고, 그 직후의 골에서 J3가 걸린다.** 부상은 TOUCH 끝 뒤 0.14~0.37 s(경계 실험 68 fail에서는 0~0.28 s)에 시작하고 0.01~0.23 s 이어진다. 뜬 다리는 앞내림 바닥에서 오르막 쪽 **후방 다리**다(pitch+ → RL·RR 둘 다, d45-+·r-p+ → RL, r+p+·d45++ → RR; `r+p+0.25`는 RL·RR이 행마다 갈림). 경계 실험 fail 68행 중 2행(pitch+ rigid, 시드 12347)만 FL도 함께 떴다.
4. **LEVEL 들어 올림 명령이 직접 원인은 아니다.** pitch+·d45-+ 실패 행은 부상 시작 때 네 다리 명령이 모두 0이다(LEVEL 첫 주기 전이거나 정지). 경계 실험 fail 68행 중 47행도 부상 시작 때 명령이 0이다. r+p+0.5처럼 LEVEL 첫 명령 중인 행도 직전 TOUCH 중 골이 이미 2.6 kN이었다.
5. **`INFO_LIFT_PAUSED`(P30fz)는 부상을 막지 못한다.** 측정 하중이 떨어진 것을 10 Hz 표본으로 보고 반응하는데, 골의 폭(0.1~0.2 s)이 제어 주기(0.1 s) + 밸브 지연(0.1 s)과 비슷하다. 경계 실험 fail 68행 중 61행에서 작동했고, 그중 40행은 처음 작동한 시각이 부상 시작 **뒤**였다.
6. **통과·실패는 골의 위상과 진폭으로 갈린다.** 같은 점에서 마스트만 바꿔도 결과가 바뀐다. 유연 마스트 `upper`는 pitch 각속도 진폭이 강체의 약 2배(0.71 대 0.37 °/s)이고 골이 0까지 내려간다. 강체 마스트에서는 골이 9 → 15 → 16 → 27 kN으로 줄어든다. β·kt·잡음 시드로도 위상이 바뀐다(3절: 같은 id라도 5.5/3.5와 5.7/3.7에서 fail이 겹치는 행은 19행뿐).

원인 후보(판단은 도메인 에이전트에 넘김, 모두 **추정**):
- (제어) TOUCH 단계 속도 명령의 계단 가진과, 로킹이 남아 있는데도 성립하는 TOUCH 끝 판정 → control-expert
- (모델) 크롤러 위 로킹 모드의 감쇠와 크롤러 접촉 모델(접촉점 수·강성)이 실기에 비해 타당한지 → dynamics-expert
- J3 창·문턱 완화는 결과에 맞춘 개정이므로 하지 않는다(판정서 289).

## 3. (b) 현 검증 범위 5.5° / 3.5° 경계 기준선

- 점: D8x R-a 16 태그를 대칭 마름모 반축 roll 5.5° / pitch 3.5°로 만든다(`d8x_diag.diamond_points`: 축 꼭짓점, `r±p±f` = (f·5.5, (1−f)·3.5), d45 = 5.5·3.5/9 = 2.1389°). 모두 $R_v$ = 1(반올림 범위). D8x 점 파일의 앞내림 d45(2.2627°, $R_v$ 1.0085)와 달리 d45도 마름모 위에 둔다.
- 단계: D8x와 같은 `acc_d8.d8x_cases`(td_main·td_robust·td_kt)의 **상단만**. 마스트 4종(rigid·stiff·upper·lower)이라 596행이다(지시문의 "약 500행"보다 많음). J3 정의는 같다(`d8x_record.run_metrics`).
- 결과 파일: `boundary_5p5_3p5_top_off.json`(전체, 커밋 안 함), `boundary_5p5_3p5_top_off_rows.csv`(행별 요약, 커밋), fail 행 시계열 `boundary_5p5_3p5_top_off_series/*.npz`(커밋 안 함).

| 항목 | 5.5° / 3.5°(이번, 진단) | D8x 5.7° / 3.7°·3.6°(저장 `ra_off.json`, 상단만) |
|---|---|---|
| 행 | 596(오류 0) | 596 |
| **J3 fail** | **68** | **68** |
| J3 외 실패 표지(`fails`·FAULT·WARN·READY 없음) | 0 | 0 |
| 점별 fail / 행 | pitch+ 16/44, r+p+0.25 17/44, d45++ 13/44, r-p+0.5 9/32, d45-+ 9/32, r+p+0.5 3/44, r+p+0.75 1/32, 그 밖 9점 0 | pitch+ 20/44, r+p+0.5 17/44, d45++ 8/44, d45-+ 9/32, r+p+0.25 7/44, r-p+0.5 4/32, r+p+0.75 2/32, roll- 1/44, 그 밖 8점 0 |
| 앞들림·순수 roll 점 | 0 | roll- 1, 그 밖 0 |
| 단계·마스트별 fail | main 6(rigid 3·upper 2·stiff 1), robust 46(rigid 22·upper 13·stiff 11), kt 16(rigid 8·stiff 8) | main 6, robust 52(upper 21·stiff 18·rigid 13), kt 10(stiff 8·rigid 2) |
| TOUCH 뒤 최소 패드 법선력 분위(0/5/25/50/75/100 %) [kN] | 0 / 0 / 9.2 / 19.3 / 26.4 / 51.1 | 0 / 0 / 9.8 / 19.3 / 26.0 / 51.6 |
| 최소 법선력 < 5 kN / < 10 kN 행 | 94 / 156 | 101 / 154 |
| fail 행 부상 청크 수 | 17~279(중앙 133) | 12~386 |
| `INFO_LIFT_PAUSED` 작동(fail 행) | 61/68 | 64/68 |
| 뜬 다리(fail 행) | RR 25, RL 27, RL+RR 14, FL+RL+RR 2(pitch+ rigid 시드 12347 두 행) | (기록 없음, 판정서 8.1 추정: 후방) |

같은 id(태그·단계·변형이 같고 바닥 각도만 다름) 596쌍 비교:

| | D8x fail | D8x pass |
|---|---|---|
| 5.5/3.5 fail | 19 | 49 |
| 5.5/3.5 pass | 49 | 479 |

최소 법선력 차이(5.5/3.5 − D8x) 분위 0/25/50/75/100 %: −17.4 / −0.4 / −0.1 / +0.9 / +19.1 kN.

읽기:
- **현 검증 범위 5.5° / 3.5° 경계도 같은 J3 정의로 상단 596행 중 68행이 실패한다.** 실패 수·최소 법선력 분포가 D8x 확장 범위와 사실상 같다. J3 실패는 범위 확장 때문이 아니라, 이전 검증이 재지 않은 TOUCH 끝 ~ 크롤러 이탈 구간의 로킹 과도(2절) 때문으로 보인다.
- 실패는 두 범위 모두 앞내림 쪽 점에만 있고, 뜬 패드는 후방이다(5.5/3.5의 2행만 FL 포함). 앞들림 쪽(pitch−, r±p−, d45±−)은 두 범위 모두 0이다.
- 같은 id끼리 fail이 겹치는 행은 19행뿐이다. 바닥 각이 조금만 달라도 골의 위상이 바뀌어 fail 행이 바뀐다(2.3의 6). 점 하나의 pass/fail보다 분포(최소 법선력 중앙 19 kN, 11 %가 0 N)로 보는 것이 맞다.
- 판정서 11절 선택지 2("검증 범위를 줄여 재판정")는 이 결과로 보면 J3 통과를 기대하기 어렵다(옛 범위 기준선이 같은 비율로 실패). **진단 결과이며 판정이 아니다.**

## 4. 한계

- 축소 하네스(`r8d1_td2`) 결과뿐이다. Chrono L1·L2b에서 같은 로킹·부상이 나는지는 확인하지 않았다.
- K1 끔 팔만 돌렸다. (b)는 상단만이다(D8x 실패가 모두 상단이라서). 중단·하단 5.5/3.5 기준선은 없다.
- 로킹 가진원(TOUCH 명령 계단)은 시계열에서 읽은 **추정**이다. 명령 계단을 없앤 대조 실행은 하지 않았다.
- 크롤러는 총 수직력과 접촉점별 접촉 여부만 기록된다(접촉점별 힘 없음). 로킹 주파수는 영점 교차로 센 대략값이다.
- (b)의 d45 점은 마름모 위(2.1389°)라 D8x 점 파일의 앞내림 d45(2.2627°, 마름모 밖 0.85 %)와 정의가 조금 다르다.
- `acc_d8._d8x_fields`는 모듈 목록을 `preset_controller_tag`보다 먼저 읽는다. 그래서 프로세스의 첫 실행만 `module_files_sha256`에 `outrigger_sim.hydraulics.v5_options`가 빠진다(기존 동작, 이번에 고치지 않음). 판정의 모듈 대조가 이 값을 쓰면 worker별 첫 행이 다른 digest를 가진다.

## 5. 다시 돌리기

```powershell
# dynamics-dev python.exe 직접 호출, MKL_THREADING_LAYER=TBB, *_NUM_THREADS=1, P코어 0xFFFF
python -I -B 04_scripts/03_control/touch_phase/acceptance/d8x_diag.py rerun --k1 off --workers 5 `
    --ids "main|C2_tv0.1|top|upper|pitch+,main|C2_tv0.1|top|rigid|r+p+0.5,main|C2_tv0.1|top|upper|d45-+,main|C2_tv0.1|top|rigid|pitch+,main|C2_tv0.1|top|rigid|d45-+" `
    --out-dir 06_analysis/02_control/d8x/diag/rerun `
    --stored C:\workspace\outrigger_control\06_analysis\02_control\d8x\ra\ra_off.json
python -I -B 04_scripts/03_control/touch_phase/acceptance/d8x_diag.py boundary --k1 off --workers 8 `
    --half-spans 5.5,3.5 --levels top --series fail `
    --out 06_analysis/02_control/d8x/diag/boundary_5p5_3p5_top_off.json
```

실측 시간: rerun 5행 48 s(worker 5), boundary 596행 923 s(worker 8).

npz 키: 1 ms 청크 `t_s`, `pad_normal_min_N`(J3 값), `pad_normal_last_N`, `stroke_m`, `motor_stroke_m`, `command_m_s`(밸브 앞), `valve_m_s`, `pad_contact`, `crawler_contact`, `crawler_point_xy_m`, `crawler_normal_N`, `crawler_clearance_m`, `att_rad`, `body_rate_rad_s`, 패드·크롤러 접선력, 청크 최대·최소 압력 힘. 제어 주기 `ctrl_t_s`, `ctrl_phase`, `ctrl_speed_m_s`, `ctrl_load_N`, `ctrl_stroke_m`, `ctrl_att_filtered_rad`. 사건 `event_t_s`, `event_name`, 그리고 `t_touch_s`, `t_lift_s`.
