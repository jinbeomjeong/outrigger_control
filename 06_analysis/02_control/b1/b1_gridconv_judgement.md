# B1 격자 수렴 시험 판정서 — J2 패드 B 단일 패드 0.01 대 0.005 m (`B1-GRIDCONV`)

- 작성: control-expert, 2026-11-10
- 규칙: 원판 `b1_gridconv_plan.md`(봉인 sha256 `0e909bf1186a4cc90e40353d25244ee4a76a04cdabe48235e7051f9a111e9b24`) + 덧붙임 `b1_gridconv_plan_rev1.md`(봉인 sha256 `3f354eb7c122584c7e65e66bb2eeaf33e27cfa9b445521a9802bdf8962d1da9e`)
- 성격: 수치 모형(SCM 격자) 수렴 판정이다. 제어기 판정이 아니다.

## 1. 판정

| 항목 | 값 |
|---|---|
| **판정** | **`PASS`** (G-1·G-2·G-3 모두 문턱 안) |
| 묶음 상태 | `COMPLETE`(4행 모두 `VALID`) |
| 두 경로 | 경로 A `PASS` / 경로 B `PASS`. 대조 127항목, 불일치 0, 최대 절대차 0.0 |
| 사전 예측 | `예측 확인`(E-1~E-8 모두) |
| G-5 | 문턱 0.05 안(`G5_FLAG` 없음) |
| 결과 처리(원판 6절) | B1 크리프 근거 규칙 2.1절의 패드 격자 0.01 m 확정 근거로 쓴다. D-c 보정 $z/f$를 격자 무관 양으로 쓴다 |

## 2. 관문 지표

$k$ = 1, 2는 유지 끝 $t$ = 11.0, 21.0 s다. 침하 + = 깊어짐이다.

| 코드 | 문턱 | 값 | 결과 |
|---|---|---|---|
| G-1 법칙 일치 $n\lvert z^{node} - z_{ref}\rvert / z^{node}$ | ≤ 0.005 (8개) | 최대 3.09×10⁻⁶ (GC-3 유지 2) | 통과 |
| G-2 보정 수렴 $\lvert z/f(0.01) - z/f(0.005)\rvert$ | ≤ 1 mm (4개) | 최대 1.11×10⁻⁴ mm (RL 유지 2) | 통과 |
| G-3 증분 비율 $\lvert \Delta z/z_2(0.01) - \Delta z/z_2(0.005)\rvert$ | ≤ 0.002 (2개) | RL 1.04×10⁻⁶, FL 3.46×10⁻⁷ | 통과 |
| G-5 정규화 계단 응답 최대 차 | ≤ 0.05 (기록) | RL 0.00459, FL 0.00209 | 기록(플래그 없음) |

### 2.1 행별 값 (경로 A = 경로 B)

| 행 | 다리·격자 | $N_h$ | $b_{hull}$ [m] | $f$ | $z_1$ / $z_2$ [mm] | $z_1/f$ / $z_2/f$ [mm] | $\Delta z/z_2$ | G-1 유지 1 / 2 |
|---|---|---|---|---|---|---|---|---|
| GC-1 | RL 0.01 | 601 | 0.125456 | 1.036454 | 118.931 / 136.178 | 114.748 / 131.388 | 0.126646 | 1.77×10⁻⁶ / 5.87×10⁻⁷ |
| GC-2 | RL 0.005 | 2421 | 0.130980 | 1.015599 | 116.538 / 133.438 | 114.748 / 131.388 | 0.126647 | 1.78×10⁻⁶ / 2.20×10⁻⁶ |
| GC-3 | FL 0.01 | 1073 | 0.171437 | 0.990770 | 85.999 / 95.060 | 86.800 / 95.945 | 0.095315 | 5.23×10⁻⁷ / 3.09×10⁻⁶ |
| GC-4 | FL 0.005 | 4285 | 0.171564 | 0.999084 | 86.721 / 95.857 | 86.800 / 95.945 | 0.095315 | 2.71×10⁻⁶ / 2.98×10⁻⁶ |

- $N_h$·$b_{hull}$는 두 유지 끝에서 같았다(하중 증분으로 접촉 절점이 바뀌지 않았다).
- $z = $ `sinkage_geometric_m`(G-2~G-5), $z^{node}$ = `sinkage_mean_contact_m`(G-1). 두 값의 차는 행마다 ≤ 2×10⁻⁸ m다.
- 연속 Bekker $z_{cont}$(YAML $b_{poly}$, 기록된 $F$)는 RL 114.747 / 131.388 mm, FL 86.800 / 95.944 mm다. $z/f$는 두 격자 모두 이 값과 0.001 mm 안에서 같다(control-expert 확인 계산, `python -c` 한 줄, dynamics-dev).
- 실행 전 위상 0 오프셋 절점 조사(`evidence/gridconv_scan/phase_band.txt`, `gc_pred.json`)와 비교했다. $N_h$는 601 / 2421 / 1073 / 4285로 같다. $f$는 예측 1.0365 / 1.0156 / 0.9907 / 0.9991, 실측 1.03645 / 1.01560 / 0.99077 / 0.99908이다.

### 2.2 원시값 (G-4)과 사전 예측

| # | 양 | 예측 | 관측 | 확인 조건 | 결과 |
|---|---|---|---|---|---|
| E-1 | G-1 최대 | ≤ 0.1 % | 3.09×10⁻⁴ % | — | 안 |
| E-2 | G-2 최대 | ≤ 0.3 mm | 1.11×10⁻⁴ mm | — | 안 |
| E-3 | G-3 최대 | ≤ 0.0005 | 1.04×10⁻⁶ | — | 안 |
| E-4 | G-5 최대 | ≤ 0.02 | 0.00459 | — | 안 |
| E-5 | RL $z_2(0.01) - z_2(0.005)$ | +2.7 mm | **+2.740 mm** | ±0.5 mm | 확인 |
| E-6 | RL $\Delta z$ 차 | +0.35 mm | **+0.347 mm** | ±0.5 mm | 확인 |
| E-7 | FL $z_2$ 차 | −0.80 mm | **−0.798 mm** | ±0.5 mm | 확인 |
| E-8 | FL $\Delta z$ 차 | −0.08 mm | **−0.076 mm** | ±0.5 mm | 확인 |

- $z_1$ 차(기록): RL +2.393 mm, FL −0.722 mm.

## 3. 두 경로와 대조

| 경로 | 담당 | 도구 | 출력 |
|---|---|---|---|
| A | control-expert | `06_analysis/02_control/b1/gridconv_judge.py` sha256 `4a5c42460116a68e1c2c02f66b77d38b407aa9089d8906771d047774b694d248`, blob `91d8d80c93b2e4db6bd247460aca9a76428238d3`(rev1 표와 같음, 결과 전 고정) | `b1_gridconv_metrics_A.json` sha256 `1a9e93b84b497832e452d4aeb286df087da291c2dac147543593f27007d8071c` |
| B | terramechanics-expert | `evidence/gridconv_pathB/gridconv_path_b.py` sha256 `14350b883b8f1773422cbec90f7d393cd9ef89030478fee987b23ffdfaa74946`(경로 A를 import하지 않음, numpy·json만) | `b1_gridconv_metrics_B.json` sha256 `f165d62bbf4834c67e47ea1907963b4090ab8b4fde72903e320fe0ff9203726a` |
| 대조 | terramechanics-expert | `evidence/gridconv_pathB/compare_ab.py` sha256 `d825f5a7919b123b405dd0e22a0079fa001b8ea72e5dd43f2fcaf13524343b63` | `compare_ab.txt` sha256 `31bc92f45719d33dc8c56ddaa39cc9b276acd6f5777c7952f10d00daf56a7485`: `{"n_items": 127, "n_bad": 0, "max_abs_diff": 0.0}` |

- 대조 항목: 묶음 상태, 판정, 행 상태, 행마다 xy0, 유지 끝별 $N_h$·$F$·$z^{node}$·$z$·$b_{hull}$·$z_{ref}$·G-1·$f$·$z/f$, $\Delta z$, $\Delta z/z_2$, 짝 지표, E-1~E-8. 원판 7절 허용(이산 완전 일치, 실수 ≤ 1×10⁻⁹)을 만족한다.
- 시간 순서: 경로 A는 결과 전에 sha를 고정했다(rev1, 커밋 `01dd321`). 경로 B는 자기 계산을 끝낸 뒤에 경로 A 출력을 읽었다(메인 세션 기록). 원판 7절은 경로 A 다음에 경로 B 순서였다. B가 A와 독립으로 계산됐다는 조건은 지켰다.
- 재현: control-expert가 같은 경로 A 도구(sha 동일)로 결과 폴더를 다시 읽었다. 위치 필드(`yaml`, `batch`)를 뺀 모든 키가 저장 `metrics_A.json`과 같았다(차 0개). 두 실행의 YAML sha는 `4f85d2d2…` 하나다.

## 4. 실행 기록

| 항목 | 값 |
|---|---|
| 결과 폴더 | `C:\workspace\outrigger_control\07_results\S9\batch_B1-GRIDCONV_20261110_174640\`(git 밖) |
| 실행 checkout | worktree `.claude/worktrees/gc-run-dc2029b`, detached HEAD `dc2029be9512f40bf849e17fd3bdaa5c61a89a5e`. 행마다 시작·끝 HEAD 같음, 추적 파일 변경 0 |
| hull DLL | 복사본 sha256 = 원본 `cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15`(rev1 C-2). 행마다 `hull_hook` mode·requested `fast`, `dll_sha_validated` 참 |
| env | 설정 `OMP_WAIT_POLICY=PASSIVE`, `OUTRIGGER_PLACEMENT=ecore`. 제거 `OUTRIGGER_HULL_HOOK`, `OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED`, `OUTRIGGER_HULL_HOOK_DLL`, `OPENBLAS_NUM_THREADS`. 인터프리터 Chrono-dev `python.exe -I -X utf8 -u` |
| 배치 | E코어 3줄(줄 1 GC-4, 줄 2 GC-2, 줄 3 GC-3 → GC-1), `--threads 4`. 배치표 `gc_placement_table.md` sha256 `dd4930486897d8e186196a82dd6e6889411f395ca3a426ece780ea61acecabd5` |
| 시각 | 시작 2026-11-10 17:46:40(prelaunch), 마지막 행 끝 18:03:30 |
| 행별 | 아래 표 |

| 행 | rc | 시작 → 끝 | 걸린 시간 [s](batch.json) | result.json `wall_s` | result.json sha256 | series.npz sha256 |
|---|---|---|---|---|---|---|
| GC-1 | 0 | 17:52:42 → 17:56:39 | 237 | 231.1 | `efd5a827c40eabce67109a898cf31f9ca653d9de7057c1c070ed5e8c67a5dc71` | `c0ea54e137ea82cd193a3e323ff1d414849fa9882b552f5032764eb89fdf919f` |
| GC-2 | 0 | 17:46:43 → 17:58:01 | 679 | 676.9 | `ae737f52ff1b1068f21801e8891b1d68eb1d387944003ad9c77beaa27adc8950` | `3f16de0bdf31b91843fda8654b74277c371a9994af47650f8ca5c23580c5c07f` |
| GC-3 | 0 | 17:46:43 → 17:52:42 | 359 | 357.6 | `564997bf42a677d59dfca982666f89c509bd50ddf1fcf2fe5f6dada25e31e7cc` | `2166c3f7797a6b3ba3bc5d2aa0b0aa1c910674de7ad3d8774ff0347579a27f62` |
| GC-4 | 0 | 17:46:43 → 18:03:30 | 1,008 | 1,003.6 | `bf822d3698347b024fc90d295372f4e30251d9a5b1597a12fa249096fedb778d` | `e0f81c0a8305bc915d7288844abff717ad47f4d0ce2235f3d90ea4c6d3ac843e` |

- 실행 래퍼(메인 세션): `gc_run_lane.ps1` `03d8ce9b2f96564ec4c67c819bf2e6f1c353f47248d8e7bf345e56d0f0fc48fb`, `gc_lanes.ps1` `346cd7b24566a25b9bad4aaf34eaa0232be7634551613bdefc7b252f7ab1b8ec`, `gc_finalize.py` `3e22fa263ddd59c9571618e8961d8cf87fae7611161856964f27b67a2b8cc20b`. 이 래퍼가 `batch.json`(argv·rc·HEAD·env) `54083f97…e0579`와 `prelaunch.json` `5b13de68…cc712f4`를 썼다.

## 5. 실행 전 감사 처리

감사 원문은 `06_analysis/02_control/b1/b1_gridconv_prerun_audit.md`(verif-protocol-auditor, master `dc2029b`)다. 차단 2, 실행 전 수정 3, 기록 6건이었다.

| 감사 항목 | 처리 |
|---|---|
| [차단] 1. single-pad가 `batch.json`을 만들지 않아 rc·argv가 남지 않는다 | 실행 래퍼가 행마다 argv·rc·HEAD·env를 `batch.json`에 썼다. 경로 A는 `--rc` 없이 batch.json에서 읽었다(`argv_checked` 참) |
| [차단] 2. 인자 순서 | 래퍼가 원판 3.2 argv 예의 순서로 띄웠다. 경로 A V-2 argv 대조 4행 통과 |
| [수정] 3. 결과에 커밋 없음, main checkout | `dc2029b` 전용 worktree에서 돌렸다. 시작·끝 HEAD와 추적 파일 변경 0을 기록했다 |
| [수정] 4. 배치표 | compute-scheduler-expert 배치표(E 3줄)를 썼고, 경로와 sha를 prelaunch에 적었다 |
| [수정] 5. env 정리 | hull hook 관련 env 3개와 `OPENBLAS_NUM_THREADS`를 지우고 그 목록을 prelaunch에 적었다 |
| [기록] 6. 비정상 입력 예외 | 해당 없음(4행 모두 정상 입력) |
| [기록] 7. G-5 공통 표본 < 2이면 NA가 아님 | 해당 없음. 공통 표본은 짝마다 0.1 s 간격 [11, 21] s다 |
| [기록] 8. rev1 근거 행 번호 `run_S9.py 2764-2768` → `dc2029b`에서 2782-2786 | 정의는 그대로다(single-pad 코드 불변, 감사 확인). 행 번호만 다르다 |
| [기록] 9. 동시 실행이 비트를 바꾸지 않는다는 확인 없음 | 짝 비교는 같은 묶음 안이다. G-1 잔차가 3×10⁻⁶ 수준이라 판정 영향이 없다 |
| [기록] 10. 패드 시작 위치 인자가 parser에 없음 | 아래 6절 해석 2 |
| [기록] 11. 07_results는 git 밖 | 증거 사본을 `evidence/gridconv_run/`에 두었다(7절) |

## 6. 정의 해석 (경로 A·B 같게 처리)

| # | 원판·rev1 문구 | 이번 처리 | 판정 영향 |
|---|---|---|---|
| 1 | 3.2 argv 예는 `--out-root 07_results/S9/batch_B1-GRIDCONV_<stamp>`(상대 경로) | 실제 argv는 절대 경로 `C:\workspace\outrigger_control\07_results\S9\batch_B1-GRIDCONV_20261110_174640`이다. 경로 A는 `--out-root <batch>` 한 쌍으로 끝나는지만 본다. 같은 폴더를 가리키므로 같은 argv로 본다 | 없음 |
| 2 | 3.3 V-2 "패드 시작 위치 인자 없음" | single-pad parser에 그런 인자가 없어 구조적으로 충족된다. rev1 C-1의 `series.npz` 첫 share x·y = (0, 0)이 그것을 대신한다(4행 모두 0.0 m). `settle_end` xy는 기록만 한다(0 ~ 5.3×10⁻¹⁹ mm) | 없음 |
| 3 | G-5의 $z$ | `node_series` `sinkage_geometric_m`(0.1 s), 정규화 기준 $z_1$·$z_2$는 유지 끝 `sinkage_geometric_m` | 없음 |
| 4 | 1절 $b_{poly}$ 값 "0.1306 m / 0.1714 m" | 반올림하지 않은 원본 값을 썼다. 경로 A는 YAML `pad_shapes.dwg_rear250` `bekker_b_m`(0.130578967 / 0.171400364)을 읽었고, 경로 B는 같은 값의 사본 `02_params/pad_variants.json`을 읽었다 | 없음(G-2는 같은 $b_{poly}$로 두 격자를 나누는 비교) |

## 7. 증거 사본 (git 추적, `-text`)

| 파일 | sha256 | 원본 |
|---|---|---|
| `evidence/gridconv_run/b1_gridconv_metrics_A.json` | `1a9e93b84b497832e452d4aeb286df087da291c2dac147543593f27007d8071c` | 결과 폴더 |
| `evidence/gridconv_run/b1_gridconv_metrics_B.json` | `f165d62bbf4834c67e47ea1907963b4090ab8b4fde72903e320fe0ff9203726a` | 결과 폴더 |
| `evidence/gridconv_run/batch.json` | `54083f97328926856f38d905fc0f34e8bf157f2482fe82aa9f08ca1eeec0e579` | 결과 폴더 |
| `evidence/gridconv_run/prelaunch.json` | `5b13de68f86d2427be3e81952eb1fbbef98d5199a8a39a3dbb182be2ccc712f4` | 결과 폴더 |
| `evidence/gridconv_run/gc_placement_table.md` | `dd4930486897d8e186196a82dd6e6889411f395ca3a426ece780ea61acecabd5` | 메인 세션 scratchpad `gc_sched\` |
| `evidence/gridconv_run/gc_run_lane.ps1` | `03d8ce9b2f96564ec4c67c819bf2e6f1c353f47248d8e7bf345e56d0f0fc48fb` | 같음 |
| `evidence/gridconv_run/gc_lanes.ps1` | `346cd7b24566a25b9bad4aaf34eaa0232be7634551613bdefc7b252f7ab1b8ec` | 같음 |
| `evidence/gridconv_run/gc_finalize.py` | `3e22fa263ddd59c9571618e8961d8cf87fae7611161856964f27b67a2b8cc20b` | 같음 |
| `evidence/gridconv_pathB/gridconv_path_b.py` | `14350b883b8f1773422cbec90f7d393cd9ef89030478fee987b23ffdfaa74946` | terramechanics scratchpad `terra\gc\` |
| `evidence/gridconv_pathB/compare_ab.py` | `d825f5a7919b123b405dd0e22a0079fa001b8ea72e5dd43f2fcaf13524343b63` | 같음 |
| `evidence/gridconv_pathB/compare_ab.txt` | `31bc92f45719d33dc8c56ddaa39cc9b276acd6f5777c7952f10d00daf56a7485` | 같음 |

- 모든 사본의 sha는 원본과 같다(복사 뒤 다시 계산). `result.json`·`series.npz`는 크기 때문에 복사하지 않고 4절 sha만 적었다.

## 8. 범위와 한계

- 이 시험은 **위상 0 오프셋 한 점**이다(패드 중심 = SCM 평면 원점, 요 0). 다른 위상의 $f$는 실행 전 스캔(유도식, `evidence/gridconv_scan/phase_band.txt`)에 기댄다. 이번 결과는 그 스캔의 0 오프셋 값과 $N_h$가 같고 $f$가 0.03 % 안에서 맞아 스캔 방법을 뒷받침한다. 그러나 다른 위상을 Chrono로 확인하지는 않았다.
- 단일 패드, `--joint fixed`, 수평 하중 0, 지면 수평이다. 레벨링 행에서는 패드가 기울고 미끄러지므로 $N_h$·$b_{hull}$이 실행 중 바뀔 수 있다. 이 변화는 B1 규칙 M-11·5.1 기록(cad-expert)으로 행마다 보고, D-c는 그 기록으로 보정한다.
- 유지 끝(정적 값)의 판정이다. 램프 중 동적 응답은 G-5(기록)로만 봤고, 두 격자의 정규화 응답 차는 ≤ 0.005다.
- J2 세트, 패드 B 두 종류(후방 250, 전방 330), 하중 72.85~74.85 / 119.59~122.01 kN 범위의 결과다. 다른 토양과 패드 A에는 일반화하지 않는다.
- 수렴의 뜻: 원시 침하는 격자에 따라 RL에서 2.7 mm 다르다. 0.01 m를 확정하는 근거는 원시값의 수렴이 아니다. Chrono가 각 격자의 이산 Bekker 법칙($f$)을 정확히 따르고, $z/f$가 격자와 무관하다는 것이 근거다. 그래서 B1 D-c는 보정값 $\Delta^{corr}$로 등급을 낸다.

## 9. 후속

- B1 후보판 0.4절에 이 판정서 sha와 "GC PASS → 0.01 m 확정 근거"를 적는다(같은 커밋). B1 봉인은 P5r4 결정 뒤라는 기존 순서 그대로다.
- 판정 후 재집계 감사(verif-protocol-auditor)와 integrity 점검은 메인 세션이 한다.
