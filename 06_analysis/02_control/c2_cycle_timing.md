# C2 한 주기 계산 시간 (R7 실측, R8 추정) — E코어 기준

2026-10-22. 스크립트 `04_scripts/03_control/c2_cycle_timing.py`, 결과 `c2_cycle_timing.json`(`runs.ecore27`, `runs.ecore27_high`).
근거: `00_docs/04_control/s6_control_spec.md` 개정 26 99.5절(U-R8-2, d = 0 조건).

## 방법

- `record`: R7 `C2Controller.update`(03_src, import만)를 축소 6자유도 플랜트(`run_control_comparison.py`)와 폐루프로 돌려 주기마다 입력·명령을 저장했다(`c2_cycle_timing_inputs.npz`, git 제외 — `record`로 다시 만든다).
  - 사례 3개, 9,450주기: 앞내림 3.5° 상단 검증 모드(REANCHOR 포함, 4,099), 평지(2,166), 평지 READY 뒤 RR 11.5 mm 침하 → 재레벨링(3,185).
  - 단계: CHECK, TOUCH, LEVEL, REANCHOR, DONE, PROBE, READY.
- `measure`: 저장 입력을 새 제어기로 재생해 `update`를 주기마다 `perf_counter_ns`로 쟀다. 재생 명령은 기록과 **비트 단위로 같음**을 매 주기 확인했다(폐루프 상태 흐름 그대로).
  - 반복: 사례마다 워밍업 1회 + 측정 5회(주기 표본 47,250개). GC 켬/끔을 각각 쟀다.
- R8은 코드에 없어 하네스(`run_c2_r8_10hz_check.py`) 로직을 같은 numpy 부품으로 흉내 내 R7 `update` 뒤에 붙였다(상한 추정).
  - IMU 추가 9표본: `AttitudeEstimator` + 2단 τ 0.8 s + 완료 필터.
  - 매 주기 모든 규칙 실행: R-1 예측 정지, R-2 접지 창, 연속 표본 확인(3/2/2/1), 끝 감속, 증분 제한. 실제로는 R-1은 REANCHOR 이동 중에만, R-2는 TOUCH에서만 돈다.
- 배치: 논리 CPU 27(E코어, Gracemont) 1개 고정, EcoQoS 해제, BLAS 1스레드. 우선순위는 보통(normal)과 높음(high) 두 가지다.
  - Chrono-dev(Python 3.12.15, numpy 2.5.4), i7-14700.
  - 측정 중 P코어는 Chrono 배치 B2가 쓰고 있었다.

## 결과 (E코어 27, 단위 µs)

우선순위 높음(high, OS 선점 잡음 제거), GC 켬:

| 단계 | R7 update 중앙값 | p95 | p99 | 최대 | R8 전체(update+IMU 9+추가) 중앙값 | p95 | p99 | 최대 |
|---|---|---|---|---|---|---|---|---|
| CHECK | 472 | 562 | 603 | 1,201 | 1,205 | 1,296 | 1,375 | 2,153 |
| TOUCH | 396 | 504 | 537 | 1,228 | 1,124 | 1,260 | 1,348 | 3,105 |
| LEVEL | 902 | 992 | 1,064 | 1,414 | 1,637 | 1,746 | 1,868 | 2,780 |
| REANCHOR | 782 | 840 | 885 | 1,234 | 1,519 | 1,605 | 1,689 | 2,412 |
| DONE | 888 | 931 | 951 | 957 | 1,634 | 1,690 | 1,719 | 1,728 |
| PROBE | 768 | 829 | 993 | 2,519 | 1,500 | 1,607 | 1,797 | 4,274 |
| READY | 850 | 925 | 1,029 | 2,916 | 1,583 | 1,702 | 1,863 | 2,374 |
| 전체 | 769 | 937 | 1,015 | 2,916 | 1,502 | 1,688 | 1,801 | 4,274 |

R8 구성 요소(높음, GC 켬):

| 구성 요소 | 중앙값 | p99 | 최대 | 반복 5회 중 최솟값의 최대(계산 고유 최악) |
|---|---|---|---|---|
| R7 update | 769 | 1,015 | 2,916 | 2,317 (PROBE) |
| IMU 추가 9표본 | 650 | 751 | 3,318 | 810 |
| R8 추가 규칙 | 79 | 97 | 357 | 92 |
| 임계 경로(IMU 필터를 100 Hz 콜백으로 뺀 경우) | 853 | 1,093 | 3,051 | 2,373 |
| R8 전체 | 1,502 | 1,801 | 4,274 | 3,029 |

**100 ms 예산 대비**(E코어, 높음): 중앙값 1.5 %, p99 1.8 %, 최대 4.3 %, 계산 고유 최악 3.0 %. 임계 경로만 보면 최대 3.1 %다.

우선순위 보통(normal)에서는 꼬리가 OS 선점으로 길어졌다. R8 전체 47,250주기 중 5 ms 초과 42~90개, 10 ms 초과 28~54개, 50 ms 초과 0~5개였다. 최대는 43.7 ms(GC 켬)와 **89.5 ms**(GC 끔)다.
- 같은 주기를 다시 재면 사라지므로(반복 최솟값의 최대 3.0 ms, 높음과 같음) 계산이 아니라 스케줄링 때문이다.
- 높음 우선순위로 바꾸자 5 ms 초과가 0개로 사라졌다.

## GC·메모리·첫 호출

- GC: 1,000주기당 gen0 2.7회, gen1 0.24회, gen2 0회다. GC가 든 주기의 최대는 R7 1.2~1.6 ms, R8 2.2 ms로 GC 없는 주기의 꼬리 안이다. `gc.disable`은 최악값을 줄이지 못했다(높음: R8 최대 4.3 → 3.2 ms는 잡음 범위). 필요하면 초기화 뒤 `gc.freeze()` 정도면 된다.
- 주기당 할당 정점(tracemalloc): 중앙값 4~15 KB, 최대 29 KB(CHECK)다.
- 첫 호출: `import numpy` 약 195 ms, `outrigger_sim.control.c2` 약 155 ms, `load_params` 약 100 ms, 제어기 생성 1.7 ms, 첫 `update` 0.6 ms.
  - 첫 패스에서 처음 지나는 코드 경로는 1회만 느리다. CHECK 최대가 약 13 ms(두 우선순위 모두)라서, 기동 시 워밍업 패스로 없앨 수 있다.
- `Measurements` 객체 생성: 주기당 약 80 µs(IO → 객체 변환 몫, 위 표에는 들어 있지 않음).

## 병목 (cProfile, 앞내림 3.5° 사례, 주기당 µs — 프로파일러 오버헤드로 절대값은 약 1.4배 부풀려짐)

| 함수 | 누적 | 비고 |
|---|---|---|
| `c2.py` `update` | 1,085 | 전체 |
| `c2.py` `_update_support_shadow` | 520 | 지지면 그림자 계산이 update의 약 절반이다 |
| `c2.py` `_heights_above_others` | 353 | `np.median`·`np.delete` 반복 |
| `np.median` (5.4회/주기) | 268 | 길이 4 배열에 대한 범용 median 오버헤드 |
| `two_pressure.py` `read` / `_sensor_faults` | 202 / 89 | |
| `np.mean` (8.6회/주기) | 133 | |
| `_update_attitude_filters` | 129 | |
| `standstill.py` `_are_rates_quiet` | 114 | |

시간 대부분은 길이 4~수십짜리 작은 배열에 대한 numpy 호출 오버헤드다(`median`, `mean`, `delete`, `array`). 계산량 자체는 작다.

## 판단

- 계산은 d = 0의 걸림돌이 아니다. E코어 1개에서 R8 전체 최악 4.3 ms로 100 ms의 4.3 %다. 계산 고유 최악은 3.0 %다.
- 걸림돌은 OS 스케줄링 결정성이다. Windows 보통 우선순위에서는 드물게(약 1만 주기에 1회) 50~90 ms 지연이 나와, d = 0이면 그 주기 출력을 놓칠 수 있다. 대상 컴퓨터에서는 다음이 필요하다.
  - 높은(실시간) 우선순위와 전용 코어
  - 또는 PREEMPT_RT 리눅스
  - 주기 초과 감시(워치독, 놓친 주기는 이전 명령 유지 또는 정지)
- Python으로 충분하다. C/C++ 이식은 계산 시간 때문에는 필요 없다. cpp-expert 위임 명세는 만들지 않았다.
- 대상이 Python을 못 돌리는 마이컴이거나 하드 실시간 인증이 필요하면 그때 다시 정한다.
- 저사양 환산(추정, 미측정): 대략적인 단일 스레드 성능 비율로 보면, 계산 고유 최악 3.0 ms가 10배 느린 CPU에서도 30 ms(예산의 30 %)다.
  - P코어(Raptor Cove)는 E코어보다 약 1.5~1.8배 빠르다.
  - Atom x6000E·Cortex-A76(라즈베리 파이 5)급은 E코어의 약 1/2~1/3이다.
  - Cortex-A72(파이 4)급은 약 1/4~1/5이다.
  - 비율은 공개 벤치마크 경향에서 잡은 추정이고, 이 PC에서 잰 것은 E코어뿐이다. 대상 하드웨어가 정해지면 `measure`만 그 컴퓨터에서 돌리면 된다(numpy, PyYAML, `03_src`, npz).
- 측정 간 변동: 같은 E코어에서 실행마다 중앙값이 최대 약 25 % 달랐다(첫 시험 실행 R7 중앙값 605 µs, 본 실행 767 µs). 최악값 판정에는 영향이 없다.

## 한계

- R8은 흉내 낸 상한 추정이다. R8 구현 뒤 다시 재야 한다.
- 축소 플랜트 입력, 이상 센서다. 평지 침하 사례는 로드측 압력을 상수로 넣어 `WARN_ROD_PRESSURE_FALLBACK` 경로가 함께 돈다.
- P코어 측정은 B2가 끝난 뒤 한다.
  ```
  C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I 04_scripts/03_control/c2_cycle_timing.py measure --cpu 2 --label pcore2 --profile
  C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I 04_scripts/03_control/c2_cycle_timing.py measure --cpu 2 --label pcore2_high --priority high
  ```
