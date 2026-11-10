<!-- verif-protocol-auditor 리포트 원문(2026-11-10, 판정 후 재집계). 대상: B1-GRIDCONV GC-1~4 판정서 af2f89c. 메인 세션이 편집 없이 저장. -->

**차단 1건(호출자 규칙 "판정서 수치가 결과와 다르면 차단"을 적용), 실행 전 수정 0건, 기록 3건.**

판정 숫자(행 상태, G-1~G-5, E-1~E-8, 최종 `PASS`)는 원본 result.json에서 독립 스크립트로 다시 센 값과 모두 같습니다. 증거 사본 sha도 원본과 같습니다. 차단 1건은 판정서 40행의 부수 문장 하나가 실제 값과 다른 것입니다. 판정 결과에는 영향이 없고, 문장 하나를 고치면 풀립니다.

## 감사 요약
- 대상: B1-GRIDCONV GC-1~4 판정서. 브랜치 `b1-gc-judgement`, 커밋 af2f89c. 시점은 판정 후이고, 사용자 결정대로 재집계 중심입니다.
- 기준 문서
  - 원판 `b1_gridconv_plan.md`: sha 0e909bf1, LF, BOM 없음
  - rev1 `b1_gridconv_plan_rev1.md`: sha 3f354eb7, LF
  - 판정서 `b1_gridconv_judgement.md`: sha c0a847b2
- 판정: 차단 1 / 실행 전 수정 0 / 기록 3. 수치 판정 `PASS`는 재현됩니다. 판정서 40행 한 문장을 고치면 확정할 수 있습니다.

## 발견 사항 (심각도순)

**[차단][C] 판정서 40행 "$z/f$는 두 격자 모두 이 값과 0.001 mm 안에서 같다"가 결과와 맞지 않습니다**
- 근거: `C:\workspace\outrigger_control\.claude\worktrees\b1-gc-judgement\06_analysis\02_control\b1\b1_gridconv_judgement.md:40`
- 재계산: $z_{cont}$는 행마다 기록된 `Fz_scm_N`과 YAML $b_{poly}$로 구했습니다. $z/f - z_{cont}$ [mm]는 다음과 같습니다.

  | 행 | 유지 1 | 유지 2 |
  |---|---|---|
  | GC-1 | +0.00101 | +0.00038 |
  | GC-2 | +0.00102 | +0.00144 |
  | GC-3 | +0.00021 | +0.00148 |
  | GC-4 | +0.00117 | +0.00142 |

  - 8개 중 6개가 0.001 mm를 넘고, 최대는 0.00148 mm입니다(GC-3 유지 2).
  - 같은 행에 적힌 $z_{cont}$ 값(RL 114.747 / 131.388, FL 86.800 / 95.944)은 GC-1·GC-3의 F 기준으로는 맞습니다. GC-2 유지 2는 131.387, GC-4 유지 1은 86.799입니다.
  - 차이의 크기는 G-1 잔차(nε ≈ 3×10⁻⁶ → z 상대 1.5×10⁻⁵)와 들어맞습니다. 계산 오류가 아니라 문장의 허용폭을 잘못 적은 것입니다.
- 판정 영향: 없습니다. 이 양은 계획서 지표(G-1~G-5, E-1~E-8)가 아니고, control-expert의 확인 계산입니다. G-2(4.04×10⁻⁵ ~ 1.11×10⁻⁴ mm)와 `PASS`는 그대로입니다.
- 권장 조치(control-expert): 40행을 "0.0015 mm 안"(또는 "≤ 1.5×10⁻³ mm, G-1 잔차 수준")으로 고칩니다. 행마다 F가 달라 $z_{cont}$가 행마다 조금씩 다르다는 점도 적습니다. 판정 등급은 바꾸지 않습니다.

**[기록][I] 실행 전 감사 3번 처리 문구 "시작·끝 HEAD와 추적 파일 변경 0을 기록"은 일부만 맞습니다**
- 근거
  - `evidence/gridconv_run/gc_run_lane.ps1:24`와 `:30`이 기록하는 것은 `head_start`·`head_end`·`tracked_dirty_start`뿐입니다. 끝 시점의 추적 파일 변경은 기록하지 않습니다.
  - batch.json 4행 모두 `tracked_dirty_start: ""`이고, `head_start`와 `head_end`는 같습니다(dc2029be…).
- 지금 상태: gc-run worktree에서 `git status --porcelain --untracked-files=no`를 실행하면 비어 있습니다. 결과에 영향은 없습니다.
- 권장 조치: 판정서 75·99행을 "추적 파일 변경 0(시작 시 기록, 끝은 HEAD만)"으로 적습니다.

**[기록][R] 실행 전 감사의 `확인 필요` 2건은 판정서 5절 처리표에 없습니다**
- 근거: `b1_gridconv_prerun_audit.md:100-101`. 판정서 5절은 발견 11건만 처리했습니다.
- 실제 상태
  - 1건(INVALID 행 재실행 문구 충돌): 4행이 모두 VALID라서 해당 없습니다.
  - 2건(경로 B가 판정까지 내는지): metrics_B가 G-2·G-3·판정·E-1~8까지 내서 대조 127항목에 들어갔습니다. 실제로는 해결된 상태입니다.
- 권장 조치: 5절에 두 줄을 더합니다(판정 불변).

**[기록][I] metrics A의 `yaml_sha256` 4f85d2d2는 CRLF 작업 트리 기준입니다**
- 근거: gc-run worktree의 `02_params/rexome33.yaml`은 `i/lf w/crlf attr/`(-text 없음)입니다. main checkout 파일 sha는 ef2880f9이고(실행 전 감사 141행에 인용), 두 쪽의 git blob은 7db55937로 같습니다.
- 영향: 내용은 같습니다. 판정서 68행의 "YAML sha 하나"는 사실이지만, 다른 checkout에서 다시 재면 sha가 달라집니다. 생성 YAML이라 이번 판정 대상의 봉인은 아닙니다.

## 재집계 표 (원본 result.json·series.npz·batch.json에서 독립 계산)

| 항목 | 판정서 값 | 재집계 값 | 차이 | 판단 |
|---|---|---|---|---|
| 묶음 | COMPLETE(4 VALID) | COMPLETE, 4행 VALID(V-1·V-2(argv 토큰 일치 포함)·C-1 xy0 = 0·C-2 DLL·V-3) | 0 | 일치 |
| N_h | 601 / 2421 / 1073 / 4285 | 같음(두 유지 끝 같음) | 0 | 일치 |
| b_hull [m] | 0.125456 / 0.130980 / 0.171437 / 0.171564 | 같음 | 0 | 일치 |
| f | 1.036454 / 1.015599 / 0.990770 / 0.999084 | 같음 | 0 | 일치 |
| z1/z2 [mm] | 118.931/136.178, 116.538/133.438, 85.999/95.060, 86.721/95.857 | 같음 | 0 | 일치 |
| z/f [mm] | 114.748/131.388(RL), 86.800/95.945(FL) | 같음 | 0 | 일치 |
| Δz/z2 | 0.126646 / 0.126647 / 0.095315 / 0.095315 | 0.1266456 / 0.1266466 / 0.0953152 / 0.0953149 | 반올림 | 일치 |
| G-1 행별 | 1.77e-6/5.87e-7, 1.78e-6/2.20e-6, 5.23e-7/3.09e-6, 2.71e-6/2.98e-6 | 같음 | 0 | 일치 |
| G-1 최대 | 3.09×10⁻⁶(GC-3 유지 2) | 3.0949×10⁻⁶(GC-3 유지 2), 8개 | 0 | 통과 |
| G-2 최대 | 1.11×10⁻⁴ mm(RL 유지 2) | 1.1054×10⁻⁴ mm. RL 4.04e-5 / 1.11e-4, FL 1.08e-5 / 4.86e-5, 4개 | 0 | 통과 |
| G-3 | RL 1.04e-6, FL 3.46e-7 | 1.0419e-6, 3.4575e-7 | 0 | 통과 |
| G-5 | RL 0.00459, FL 0.00209 | 0.004590, 0.002085(공통 표본 101개, 11.0~21.0 s) | 0 | 플래그 없음 |
| E-1~E-4 | 모두 안 | 모두 안 | — | 일치 |
| E-5 | +2.740 mm | +2.7400 mm(예측 대비 +0.040) | 0 | 확인 |
| E-6 | +0.347 mm | +0.3469 mm | 0 | 확인 |
| E-7 | −0.798 mm | −0.7977 mm | 0 | 확인 |
| E-8 | −0.076 mm | −0.0760 mm | 0 | 확인 |
| z1 차 | RL +2.393, FL −0.722 mm | +2.3931, −0.7217 mm | 0 | 일치 |
| node − geo | ≤ 2×10⁻⁸ m | 최대 1.79×10⁻⁸ m | — | 일치 |
| settle_end xy | 0 ~ 5.3×10⁻¹⁹ mm | 최대 5.31×10⁻¹⁹ mm | — | 일치 |
| 최종 판정 | PASS | PASS(G-1·G-2·G-3 count 8/4/2, 모두 문턱 안) | — | 일치 |
| z/f ↔ z_cont | "0.001 mm 안" | 최대 0.00148 mm | 초과 | **차단(문구)** |
| 행별 시각·소요 | 237 / 679 / 359 / 1,008 s, wall_s 231.1 / 676.9 / 357.6 / 1,003.6 | batch.json 시각과 result `wall_s`로 같음 | 반올림 | 일치 |

- 대조
  - metrics_A: 행 80항목이 상대 1e-12 안에서 재집계와 같습니다. pairs·gates·predictions 값도 같습니다.
  - metrics_B: 행 상태 4 VALID, pairs·gates·E 값이 A와 비트 단위로 같습니다.
  - `compare_ab.txt` 끝줄은 `{"n_items": 127, "n_bad": 0, "max_abs_diff": 0.0}`로 판정서와 같습니다.
- 결과 sha
  - result.json 4개, series.npz 4개 모두 판정서 4절과 같습니다(efd5a827·c0ea54e1 / ae737f52·3f16de0b / 564997bf·2166c3f7 / bf822d36·e0f81c0a).
  - metrics_A·metrics_B의 `inputs`에 적힌 sha와도 같습니다.

## 증거 사본 sha (판정서 7절)
- 결과 폴더의 원본과 바이트가 같습니다: metrics_A 1a9e93b8, metrics_B f165d62b, batch.json 54083f97, prelaunch.json 5b13de68.
- 판정서 표의 sha와 같습니다: gc_placement_table dd493048, gc_run_lane 03d8ce9b, gc_lanes 346cd7b2, gc_finalize 3e22fa26, gridconv_path_b 14350b88, compare_ab.py d825f5a7, compare_ab.txt 31bc92f4. 다만 이 7개는 원본이 scratchpad에 있어 재측정은 사본 쪽만 했습니다.
- 모든 사본이 `attr/-text`입니다. compare_ab.txt·metrics_B·batch.json·prelaunch.json은 i/crlf w/crlf로 바이트 그대로 보존돼 있습니다.

## 판정서 서술의 사실 확인
- **A의 sha를 결과 전에 고정**: 사실입니다.
  - `gridconv_judge.py`의 마지막 변경은 01dd321(2026-11-10T16:50:48)이고, 결과 시작(prelaunch 17:46:40)보다 앞섭니다.
  - af2f89c 트리 blob과 작업 트리 `hash-object`는 91d8d80c로 rev1 표와 같습니다. 파일 sha는 4a5c4246으로 metrics_A의 `tool_sha256`과 같습니다.
  - 01dd321은 실행 HEAD dc2029b의 조상입니다.
- **B는 독립 계산 뒤 A를 읽음**: 코드로 확인되는 부분은 사실입니다.
  - `gridconv_path_b.py`는 hashlib·json·math·sys·pathlib·numpy만 import합니다. 입력은 batch 폴더·pad_variants.json·출력 경로뿐이고(`:16-26`, `:44-45`, `:72`) metrics_A를 읽지 않습니다.
  - 파일 mtime은 A 18:04:05, B 18:06:25입니다. "자기 계산을 끝낸 뒤 A를 읽었다"는 순서는 파일만으로는 증명할 수 없습니다(메인 세션 기록에 근거, 아래 검사하지 못한 것).
- **실행 전 감사 11건 처리**: 건수(차단 2, 수정 3, 기록 6)와 항목이 감사 원문과 맞습니다.
  - 1·2번: batch.json argv 4행이 계획서 3.2 순서와 같습니다(재집계에서 토큰 단위로 대조). rc는 0입니다.
  - 4·5번: prelaunch에 배치표 sha와 env 정리 목록이 있습니다.
  - 3번: 위 [기록] 참고(끝 시점 dirty 미기록).
  - 8·10·11번 처리도 원문과 맞습니다.

## 확인 필요
- 없습니다.

## 위임 필요
- control-expert: 판정서 40행의 허용폭 문구 수정(차단 해소). 75·99행과 5절에 기록 3건을 반영하는 것은 선택입니다.

## 메인 세션 권고
- 40행을 고친 판정서로 다시 커밋하기 전에, 판정서 sha가 바뀌면 B1 0.4절에 인용한 sha도 함께 갱신합니다.

## 검사하지 못한 것
- 경로 B가 A 출력을 읽기 전에 계산을 끝냈는지의 시각 순서. 파일 근거는 없고 mtime뿐입니다[추정].
- scratchpad에 있는 래퍼·경로 B 원본 파일과 증거 사본의 대조. 원본에 접근하지 않았고, 사본 sha를 판정서 표와만 대조했습니다.
- S·E·T축 전수 검사. 이번 범위는 재집계뿐입니다.

## 실행한 검증
- 인터프리터: python-dev `python.exe -I -B -X utf8`, `MKL_THREADING_LAYER=TBB`. PowerShell 셸의 affinity를 0xFFF0000(E코어 16~27)으로 두고 그 자식으로 실행했습니다.
- depcheck: STAMP(이번 세션에서 이미 점검함).
- 독립 재집계 `gc_recount.py`: 경로 A·B를 import하지 않고 계획서 1·3.3·4·5절 식을 다시 구현했습니다. 원본 결과 폴더와 gc-run worktree의 YAML(`pad_shapes.dwg_rear250`, 다각형 2A/P도 검산)을 읽고, metrics A/B와 대조했습니다.
- 보조 `gc_extra.py`: z/f ↔ z_cont, 증거 사본 sha, 원판·rev1 CRLF·BOM, `.sha256`, prelaunch를 확인했습니다.
- 위 두 스크립트와 `guard.json`은 scratchpad `verif\`에 만들었다가 폴더째 지웠습니다. 저장소에 생긴 파일과 `__pycache__`는 없습니다(`git status --short` 비어 있음).
- git 조회: `log`(judge·01dd321), `rev-parse af2f89c:<judge>`, `hash-object`, `merge-base --is-ancestor`, `ls-files --eol`(판정서·증거·YAML), gc-run worktree의 `status --porcelain`.
- Grep으로 `gridconv_path_b.py`의 import·입력을 확인하고, `gc_run_lane.ps1`의 dirty 기록 줄을 확인했습니다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha b1_gridconv_metrics_A.json 1a9e93b8…, b1_gridconv_metrics_B.json f165d62b…, batch.json 54083f97…, prelaunch.json 5b13de68…, result.json efd5a827…, series.npz c0ea54e1…, result.json ae737f52…, series.npz 3f16de0b…, result.json 564997bf…, series.npz 2166c3f7…, result.json bf822d36…, series.npz e0f81c0a…, GC1_J2_B_RL_1cm.json e8237aaf…, GC2_J2_B_RL_0p5cm.json a64c67fc…, GC3_J2_B_FL_1cm.json 2e59363e…, GC4_J2_B_FL_0p5cm.json 8765f79b…, b1_gridconv_judgement.md c0a847b2…, b1_gridconv_plan.md 0e909bf1…, b1_gridconv_plan_rev1.md 3f354eb7…, b1_gridconv_plan.sha256 2cc150c3…, b1_gridconv_plan_rev1.sha256 67069c63…, b1_gridconv_prerun_audit.md 46c6b9fe…, b1_gridconv_metrics_A.json 1a9e93b8…, b1_gridconv_metrics_B.json f165d62b…, batch.json 54083f97…, gc_finalize.py 3e22fa26…, gc_lanes.ps1 346cd7b2…, gc_placement_table.md dd493048…, gc_run_lane.ps1 03d8ce9b…, prelaunch.json 5b13de68…, compare_ab.py d825f5a7…, compare_ab.txt 31bc92f4…, gridconv_path_b.py 14350b88…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
