# FB 표적·채택 규칙 덧붙임 판 rev1 (실행 전 변경·해석 확정)

- 작성: control-expert, 2026-11-08. 원판 `fb_targeted_rules.md`(sha256 `e517b0d08bc46100bb20ec3824de5066cdb8890715f03f3e9a1299437e5dcb89`)와 설계서 사본 `fb_design.md`(sha256 `2b95fefb84b20ff370d9c121519d9015b5b885e8708c64208e09b8e9cdb5bbe1`)는 고치지 않는다.
- **실행 결과를 보기 전에 정한 것이다.** 이 판을 쓸 때 F-0~F-6 실행 줄은 0줄이다(`06_analysis/03_hydraulic/coupled/v5/fb/` 폴더 없음). 그래서 이 판의 변경은 원판 7절의 "결과를 본 뒤의 변경"이 아니다.
- 이 판을 쓰기 전에 본 것은 원판 봉인 전에 이미 본 것(원판 머리말: 진단 32건, 오프라인 그림자 551기록)뿐이다. 그 밖에 새로 본 것은 FB와 무관한 저장 기준선 두 가지다.
  - `v5/main.jsonl`의 R2·R2ra ε0 V0·VB 줄 4개(사건 이름만)
  - `v5/las/las_T1.jsonl`·`las_T2.jsonl` b0 act 줄의 `d1.verdict` 집계(192/192 pass)
- 기준 코드: master `1987495`(`fb_targeted.py`·`fb_judge.py` 병합)
- 우선순위: 이 판에 적은 항목은 원판보다 우선한다. 적지 않은 것은 모두 원판 그대로다.

## 1. 변경: F-4 verdict 사례 `R2` → `R2ra` (사용자 결정 2026-11-08)

| 항목 | 원판 | rev1 |
|---|---|---|
| F-4 verdict 사례 1번 | `R2`(fdown, REANCHOR) | **`R2ra`**(fdown, REANCHOR 켬) |
| 작업 정의 | `run_v5._phase_jobs("R2")[0]` = `{case: R2, eps: 0}`, 결정 없음 → `verdict_cases` 기본 `reanchor_off` | `run_v5._phase_jobs("R2ra")[0]` = `{case: R2, decision: reanchor_on, eps: 0}` |
| 설정 | V0·VB(η 기본) | 같음 |
| 키(`fb_targeted.fb_key`) | `R2\|<setting>\|etadef\|e0` | `R2\|<setting>\|etadef\|e0\|reanchor_on` |
| F-4 실행 수 | 28 | **28**(그대로: D-1 4키 + verdict 5사례 × 2설정 = 14작업 × L·LF) |

- 이유: 원판 괄호 "(fdown, REANCHOR)"는 REANCHOR 경로를 시험한다는 뜻이다. 그런데 결정 없는 `R2`는 REANCHOR를 건너뛴다. 저장 `v5/main.jsonl`(FB·LAS-b 없음, ε0) 사건 이름이 그것을 보여 준다.
  - `R2` V0·VB: `reanchor_skipped` 1
  - `R2ra` V0·VB: `reanchor_started` 1, `reanchor_completed` 1
- 그래서 원판의 뜻대로 그 경로를 실제로 시험하려면 `R2ra`를 돌려야 한다.
- 원판대로의 `R2`(reanchor_off)는 돌리지 않는다. 결과를 보기 전의 변경이므로 원판 7절의 "원판 기준·덧붙임 판 기준 둘 다 적기"는 이 항목에 적용하지 않는다. 판정서에는 이 변경을 적는다.
- 설계서 1.2절 "REANCHOR, SGS 네 다리 낮춤 — 없음(수계산, 환형 17.4 L/min)"이 이 행에서 처음 실행으로 확인된다. 다만 기준(C-2·C-4·C-9)은 바꾸지 않는다.

## 2. 해석 확정 (원판 문구의 애매한 곳, 판정 도구 `fb_judge.py`의 읽기를 검토해 유지)

아래는 원판 문구를 바꾸지 않는다. 두 가지 읽기가 가능한 곳을 한쪽으로 못 박는 것이다. 판정의 두 경로(python-expert 도구, control-expert 재집계, 원판 8절)는 모두 이 읽기를 쓴다.

| # | 원판 위치 | 확정한 읽기 | 근거 |
|---|---|---|---|
| I-1 | 4절 C-2 (a) "L pass → LF fail 0" | `d1.verdict`가 L `pass` → LF `fail`인 짝만 위반으로 센다. LF `allowed_stop`은 `fail`이 아니다. L `allowed_stop` → LF `fail`도 (a) 위반이 아니다(L이 `pass`가 아님). 그 밖의 판정 변화(pass→allowed_stop, allowed_stop→fail 등)는 모두 판정서에 참고 목록으로 적는다. 실패 항목의 P3-2·G6-2 새 실패(L 실패 항목에 없고 LF 실패 항목에 있는 이름)는 L 판정과 무관하게 모든 D-1 짝에서 센다 | `d1_runs`의 판정 등급은 `pass`·`allowed_stop`·`fail` 세 가지다. 원판은 `fail`이라고 썼다. `allowed_stop`은 토양 가드 안전 정지(`stroke_limited_stop`, 행이 허용할 때)다. 그래서 L pass → LF allowed_stop은 LF에 새 `FAULT_LIFT_STROKE_LIMIT`가 생긴다는 뜻이고, (c) 새 FAULT로 잡힌다. F-2의 L(저장 b0 act 192줄)은 모두 `pass`다. 그래서 allowed_stop → fail은 F-3·F-4에서만 생길 수 있다 |
| I-2 | 4절 머리말, C-2 (c)·C-4 "사건 이름" | 사건 이름은 `event_names`의 키다(`run_m1.event_names`: 사건 문자열의 첫 `:` 앞). 새 사건은 LF 키 집합에서 L 키 집합을 뺀 것 중 접두사 `FAULT` 또는 `WARN`으로 시작하는 이름이다. 접미사(`:soil` 등)만 다른 사건은 같은 이름이다 | 원판 "사건 이름(접두사 FAULT·WARN)"과 같다. LAS-b 판정(`las_judge` C3)과 v5 기록의 기존 관례도 같다 |
| I-3 | 4절 C-6 "첫 TOUCH 주기 뒤 1.0 s 안" | 지연 = (첫 `INFO_FLOW_BUDGET_CUT`의 시각, 규칙 U·A97 어느 것이든) − (update 끝 단계가 처음 TOUCH인 주기의 시각 $t_j$)이다. 지연이 [0, 1.0] s(허용 1e-9 s)면 만족이다. 깎기 사건이 없으면 위반이다 | 시각은 둘 다 `measurements.t_s`(같은 시계)다. $t_j$는 TOUCH 첫 명령을 낸 주기의 시작이다. "그 주기 끝"($t_j$ + 0.1 s)을 기준으로 하는 읽기보다 0.1 s 엄격하다(보수 쪽). TOUCH 전에는 이동 명령이 없어($\hat m\ge0.3v_{max}$ 불성립) 음의 지연은 생기지 않는다. 봉인 전 진단(η 0.70)은 CHECK 1.0 s, 깎기 1.7 s로 지연이 약 0.7 s였다. 두 읽기 모두 그 값을 같은 쪽으로 판정한다 |
| I-4 | 4절 C-10 "창 자세 변화의 크기" | 크기 = $\sqrt{\Delta\phi^2+\Delta\theta^2}$ [deg]다. $\Delta$는 8 s 창의 끝 − 시작(플랜트 진값 roll·pitch)이다. 같은 키 V0 OL-L의 같은 크기와 비교한다. 축별 $\Delta\phi$·$\Delta\theta$도 판정서에 적는다(판정에는 쓰지 않음) | "크기"는 벡터 크기다. 설계서 3.1절의 진단 값(축별 끝 − 시작, 진단 래퍼 `budget_run.py`)과 같은 정의다. 그래서 C-10의 문턱(V0 + 0.05°)이 정해진 근거와 맞는다. 방향이 V0와 다른지는 축별 기록으로 본다 |
| I-5 | 1.2절 조건 3 $\lvert a_k-a_{k-1}\rvert$ | 첫 주기의 $a_{-1}$ = 0이다 | 원판 $x_0$ = 0(밸브 정지)과 같은 가정이다. 첫 주기는 CHECK의 0 명령이라 결과에 영향이 없다 |
| I-6 | 4절 C-4 "사건 이름 집합이 L과 같은 짝" | 집합은 `event_names`의 모든 키다(INFO 포함, I-2). 그래서 LF에만 `INFO_FLOW_BUDGET_CUT`가 있는 짝(η 0.80·0.70처럼 검출이 선 실행)은 READY 판정에서 빠지고 목록으로 보고된다 | 원판 문구 그대로다. 검출이 선 실행은 C-5·C-6이 판정한다. C-4는 정상 공급(V0, VB η 0.85)에서 예산의 비용을 본다. 판정서는 빠진 짝 수를 묶음별로 적는다 |
| I-7 | 4절 C-1·C-9 "VB(η 0.85)" | 설정 VB이고 작업의 `eta_v`가 없거나(기본 0.85) 0.85인 것 | U-9 작업은 η 0.85를 명시하고, D-1 작업은 기본값을 쓴다 |
| I-8 | 1.2절 조건 1 $\hat m_{i,k}\ge0.3\,v_{max}$ | 부호 있는 비교다. 수축 다리(REANCHOR, SGS 네 다리 낮춤)는 평가 다리가 아니다 | 원판 문구 그대로다. 수축은 환형 면적이라 예산에도 닿지 않는다(설계서 1.2절) |

## 3. 멈춤 조건 H-1 덧붙임

- 원판 H-1에 다음을 더한다. 이 파일(`fb_targeted_rules_rev1.md`)이나 `fb_targeted_rules_rev1.sha256`이 없거나, 이 파일의 sha256이 `.sha256` 파일의 값과 다르면 실행하지 않는다.
- 원판의 H-1 대조(원판 sha256 `e517b0d0…`, `fb_design.md` 존재)는 그대로 둔다.

## 4. 판정서에 적을 것

- 규칙: 원판 sha256과 rev1 sha256 둘 다
- F-4가 `R2ra`(reanchor_on)로 돌았다는 것과 그 이유(1절)
- 2절 I-1~I-8 읽기. 특히 C-2 참고 목록(판정 변화 전부), C-4에서 빠진 짝 목록과 묶음별 수
