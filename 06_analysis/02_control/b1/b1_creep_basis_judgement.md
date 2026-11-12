# B1 크리프 근거 판정서 (`V5-B1-CREEP`)

- 작성: control-expert, 2026-11-12. **시점: 판정 후, 판정서 커밋 전.** 등급은 두 경로 출력이 이미 낸 값을 옮겼다. 이 판정서는 등급을 새로 정하지 않고 문턱을 바꾸지 않는다.
- 성격: B1 설계 입력을 정하는 **등급 판정**이다(원판 첫머리). 제어기 합격·불합격 판정이 아니다. P3 행·SGS 분류는 기록만 한다.
- 규칙
  - 원판 `06_analysis/02_control/b1/b1_creep_rules.md`, sha256 `6b99702ce26d6da28fbfe6473b622c7e51419241916cbc101f795828f498774e`, 봉인 `b1_creep_rules.sha256`(파일 sha256 `a269959a…`, 봉인 2026-11-12 09:26:11 +09:00, 커밋 `1ad3e5d`)
  - rev1 `b1_creep_rules_rev1.md`, sha256 `9f72af5babc36a9164a79163a0c3fa8707a0b8dc71aa3bfe978ebdf33d0905cf`, 봉인 `b1_creep_rules_rev1.sha256`(파일 sha256 `07026005…`, 봉인 11:59:43, 커밋 `417ce28`). rev1은 하네스 결과를 본 뒤, B1 Chrono 결과 전에 썼다(rev1 0절 공개).
  - 전제: 격자 시험 계획 `b1_gridconv_plan.md` `0e909bf1…`, rev1 `3f354eb7…`, 판정 `b1_gridconv_judgement.md` `a483ac48…` `PASS`(원판 첫머리 그대로).
- 입력(이 판정서를 쓸 때 다시 해시함)

| 파일 | sha256 |
|---|---|
| 경로 1 출력 `b1_metrics_path1.json` | `6ad863abd3933e7f9353197bcd1af811188559722e76d69210dd80d47c336ee5` |
| 경로 2 출력 `b1_metrics_path2.json` | `5c3185c4930ec6f9f4a1a013a12266cb7680299071ead8120c623b9165949e35` |
| K-R 대응표 `b1_kr_map.md` / 결정 `b1_kr_map_decisions.md` | `d0f30e15…` / `1c00dc75…` |
| K-R 결과 `b1_kr_result.md` / `.json` | `3dafa009…` / `eaa8d833…` |
| K-R 감사 원문 + 결정 `b1_kr_audit.md` | `d84c7be1…` |
| prelaunch `b1_creep_prelaunch.md`(11절 postrun 포함) | `4e8627ed…` |
| 실행 전 감사 `b1_creep_prerun_audit.md` / 도구 수정 재감사 `b1_creep_fix_reaudit.md` | `7e22898a…` / `778162fb…` |
| 하네스 `06_analysis/03_hydraulic/coupled/v5/b1/b1_H.jsonl`(원시 바이트) | `a7099db61b58198c9e9b7975b02c5641a8bbe04b695eec6ae9f0abcf174fc2f7` |
| 정체성 입력 `07_results/S9/batch_V5-B1-CREEP_20261112_125134/B1_identity.json` | `2a4a46624d05466bfa6ff1123bc2af1c4869ef7aba234d827f3261a2523c10b5` |
| 상수 경로 1 `b1_harness_constants_rev1.json` / 경로 2 `b1_constants_path2_rev1_run.json` | `3d35a1d8…` / `3b5e775b…` |

- 판정서 파일 이름: 원판 11절대로 `06_analysis/02_control/b1/b1_creep_basis_judgement.md`다. 처음에는 메인 세션 지시의 잘못된 이름 `b1_creep_judgement.md`(sha256 5a959fb0…)로 썼고, 메인 세션이 이 줄만 고쳐 규칙 이름으로 옮겼고, 그 뒤 끝에 부록(판정 뒤 사용자 결정)을 더했으며, 판정 후 감사의 기록 4건(속도 범위 하한, 시각, 이 줄, 6절 형식 차이)과 npz 공개 줄을 메인 세션이 고쳤다.
- 규약: 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1, C2 음되먹임($u$ = 행정 속도 명령 [m/s]). 행정은 판독 행정(제어기가 보는 모터 행정), 가드 $s_{guard}$ = 682.8 mm. 침하 $z$는 패드 기하 침하(+ = 깊어짐). 도구 값은 m이고 이 문서는 mm로 적는다(소수 셋째 자리 반올림). 시각은 정수 주기 $n$ = round($t$/0.1)이고 절대 시각이다.

## 안전 기록 (`SAFETY_NOTE`)

- **`SAFETY_NOTE` 없음.** 6행 모두 `FAULT_STROKE_END` 0건, 다리 부상(T-8) 0건, 크롤러 재착지(T-9) 0건이다. 경로 1 `safety_notes` = `{}`, 경로 2 `safety_notes` = `{}`, 행별 `m.safety`도 비었다(K-85·K-86, 두 경로 모두 사건이 없어 같다).
- 기록(안전 기록 조건 아님): C3의 판독 행정 최대 FL 683.475 mm가 가드 682.8 mm를 0.675 mm 넘었다($g$ = −0.675 mm). 그 주기 $n$ = 610(61.0 s)은 `probe` 단계(59.7 s 시작, 69.8 s에 `level`)였고, C3에는 `WARN_LIFT_STROKE_LIMITED`·`FAULT_LIFT_STROKE_LIMIT` 사건이 없다(result.json `phases`·`events`). 행정 끝 FAULT 문턱 693.8 mm에는 닿지 않았다. C3는 D-e 대상 행이 아니다.

## 1. 결론

### 1.1 묶음·행 상태

- 묶음 상태: **`COMPLETE`**(두 경로 같음: 경로 1 `bundle` + `blocked` [] , 경로 2 `bundle`). 6행 모두 `VALID`이다.
- `INVALID` 행 없음. 그래서 적을 원인도 없다(V-2). `MISSING`·`MISSING_START`·`NO_LOC` 없음. 재실행 없음(`rerun_of` 없음, `attempt1/` 없음).
- 러너 로그(E-5·I-12): 최종 `<case>.log`에 `Traceback` 0행 → `runner_log` `errors_total` = `errors_left` = 0. `tools/verif/log_errors.py`는 종료 0, `errors N` 줄 없음(7로그). 첫 시도 오류는 없다.
- 하네스 짝(V-4·E-1): 경로 1 `harness_refused` [], 경로 2 `harness_invalid` {}. H-P VB e0 짝 5개가 모두 있다. H-SH0 그림자 짝 4개 모두 `same`(경로 1 `shadow_pairs.all_same` 참, 경로 2 `shadow_hash_ok` 참).

### 1.2 등급 8개

| 등급 | 결과 | 규칙 문장이 정한 뜻(원판 3.3) | 이번 값(두 경로 같음) | 계산 행(행 수) |
|---|---|---|---|---|
| D-a 크리프 허용 | **ZA-2** | 원시·보정 가운데 하나라도 $Z - Z_{hn} > 3$ mm. B1 하네스 스윕의 침하 항을 Chrono 쪽으로 보정한다 | $Z_{ch}$ 13.337, $Z^{corr}_{ch}$ 11.481, $Z_{hn}$ 7.168 mm. 원시 ZA-2, 보정 ZA-2 | C1~C5(5). 보정값은 C5만(1) |
| D-b 과도 초과 | **OS-MAX** | $O$ > 5 mm. B1은 "예상 최대 행정"을 쓰고 허용값 $O$를 더한다 | $O$ = 23.197 mm(C3 Chrono FL $\delta^{os}$) | C1~C3(3). C4·C5는 READY 없음으로 뺌 |
| D-c 하네스 대응 | **H-OPT** | 보정 $\Delta^{corr}_r$ > 3 mm인 행 ≥ 1. 방향별 최대 $\Delta^{corr}$를 더하고 그 방향은 B1 채택 전에 Chrono 확인 행을 둔다 | 보정 분류 C1 −, C2 +, C3 +(대체 범위), C4 미확정, C5 0. 원시도 H-OPT | C1~C5(5) |
| D-d 예측자 | **PRED-FAIL** | 최소 $E_q$ > 10 mm. B1 설계 전에 새 예측 형식을 재등록한다(개정판). 후보 밖 형식은 쓰지 않는다 | $E$: P-A 27.390, P-B 28.667, P-D 27.390, P-G 30.862, P-C 48.522 mm. $q^\ast$ = P-A(P-D와 동점, 순서) | C1~C5(5), T-14 제외 0 |
| D-e B1 필요성 | **B1-OPEN** | `NEED-RECHECK` 조건(C1·C2·C4 모두 $\tilde g \ge$ 20 mm이고 SGS 0)이 아님. B1(경사 틈 여유 $m$ 축소)은 열린 과제로 남는다 | $\tilde g$: C1 0.110, C2 0.334, C4 −7.095 mm. C4 SGS | C1·C2·C4(3) |
| D-f fup 범위 | **FUP-OUT** | C5 SGS이고 H-M0 C5 두 짝($m$ = 0) 모두 SGS. B1 범위(0~30 mm)로 풀 수 없다. 운용 권고 문제로 분리해 사용자에게 묻는다(Q6) | C5 SGS RL 50.2 s, H-M0 C5 VB·V0 e0 둘 다 SGS | C5 + H-M0 짝 2 |
| D-g ×1.1 감도 | **W-NA** | C6가 VALID가 아니거나 D-d가 `PRED-FAIL`이면 W-NA | C6 VALID, D-d PRED-FAIL → W-NA | C6(1, 경로 1 목록. 경로 2는 목록 없음, 4.3) |
| D-h 기준 정합 | **K-SAME** | `P7_REF` 해당 키 대 H-P 20실행 명령 해시가 모두 같음 | same 20 / diff 0 / na 0 | H-P 20 |

- 계산 행이 0개인 등급은 없다(E-6 없음).

### 1.3 B1 크리프 근거 판정이 말하는 것

B1은 LOC 주기에 다리별 최대 판독 행정을 예측해 E3c10 경사 틈 여유 $m$을 [0, 30] mm 안에서 줄이는 규칙이다(원판 0.1). 이번 판정은 그 예측식의 플랜트 항(LOC 뒤 침하 $\Delta z^{post}$, 과도 초과 $\delta^{os}$)과 하네스 보정 여부를 J2 경사(Chrono SCM, 명목 세트)에서 정했다. 결과가 말하는 것은 다음과 같다. 모두 SCM 명목 세트 안의 결론이고 실토양 결론이 아니다(원판 14.1).

1. **LOC 뒤 침하는 하네스보다 크다(ZA-2).** 예산 다리의 Chrono $\Delta z^{post}$ 최대 13.337 mm(C2 FL)는 같은 다리 하네스 최대 7.168 mm보다 6.169 mm 크다. 격자 기록이 유효한 C5만 쓴 보정값 11.481 mm도 4.313 mm 크다. 그래서 B1 하네스 스윕의 침하 항은 Chrono 쪽으로 보정해야 한다. 설계용 $Z_{\,B1} = \max(Z_{ch}, Z^{corr}_{ch}, Z_{hn}) + Z_{soil}$ = 13.337 mm + $Z_{soil}$이다($Z_{soil}$은 가정, 2.2).
2. **과도 초과가 크다(OS-MAX).** READY 행(C1~C3)의 예산 다리 $\delta^{os}$는 19.901~23.197 mm다. B1은 "예상 최종 행정"이 아니라 "예상 최대 행정"을 써야 하고 $O$ = 23.197 mm를 더한다.
3. **하네스는 fdown에서 낙관적이다(H-OPT).** Chrono 판독 최대가 하네스 VB e0보다 C2 +8.614 mm(보정), C3 +7.825~+15.042 mm(대체 범위) 높다. diag(C4)는 부호 미확정, fup(C5)는 ±3 mm 안이다.
4. **등록한 예측 형식으로는 최대 행정을 10 mm 안에 맞히지 못한다(PRED-FAIL).** 다섯 후보 모두 최소 $E_q$ 27.390 mm다. 이 최대는 SGS 행 C4(판독 최대는 하한)에서 나왔다. READY 행 C1~C3만 보아도 최소 오차는 13.661 mm(P-A·P-B·P-D, C3)로 10 mm를 넘는다. READY 행의 P-A 오차는 +6.100, +10.450, +13.661 mm로 모두 예측 부족이다. rev1 7절의 알려진 한계(예산 다리 FL·RL의 $\hat W$가 음수라 P-B·P-D가 P-A와 같아짐)가 Chrono에서도 나타났다(C1 FL −1,005 N, C3 FL −1,555 N, C5 RL −841 N. C2 FL +228 N은 P-B에 0.189 mm만 더함).
5. **B1은 열린 과제로 남는다(B1-OPEN).** 현행 $m$ = 30 mm에서 C1·C2의 가드 여유는 2.624 / 3.871 mm이고 C4는 SGS로 멈췄다. 20 mm 재확인 조건과 거리가 멀다.
6. **fup(앞들림 경사)는 B1 범위로 풀 수 없다(FUP-OUT).** C5 Chrono와 $m$ = 0 하네스 두 짝이 모두 SGS다. 틈 여유를 0까지 줄여도 행정 예산이 모자란다. 운용 권고 문제(Q6)다.
7. ×1.1 감도(D-g)는 예측 형식이 없어 등급을 낼 수 없었다(W-NA). 기준 정합(D-h)은 K-SAME이라 원판 0.2의 하네스 여유를 B1 근거에서 뺄 키는 없다.

요약: **크리프 근거 가운데 침하 항(ZA-2, Chrono 쪽 보정)과 과도 항(OS-MAX, 최대 행정 + 23.2 mm)은 정해졌다. 그러나 예측 형식이 없어(PRED-FAIL) 지금 등록된 꼴로는 B1을 설계할 수 없다. fup는 B1 밖이다.**

### 1.4 후속 과제

규칙이 정한 다음 단계(원판 3.3 효과 칸 그대로)

| 등급 | 규칙이 정한 다음 단계 |
|---|---|
| D-d PRED-FAIL | B1 설계 전에 새 예측 형식을 재등록한다(개정판). 후보 밖 형식은 쓰지 않는다. rev1 U-R1-4 (a)도 "`PRED-FAIL` 때 재등록"으로 정했다 |
| D-f FUP-OUT | 운용 권고 문제로 분리해 사용자에게 묻는다(Q6, 1.5) |
| D-e B1-OPEN | `NEED-RECHECK`가 아니므로 D-e에 따른 Q6 재질문은 생기지 않는다. B1 필요성은 열린 채 남는다 |
| D-c H-OPT | 방향별 최대 $\Delta^{corr}$를 더하고, 그 방향(fdown)은 B1 채택 전에 Chrono 확인 행을 둔다 |
| D-a ZA-2 | B1 하네스 스윕의 침하 항을 Chrono 쪽으로 보정한다. B1 설계 문서는 $Z_{soil}$ Z1·Z2를 감도로 쓴다 |
| D-b OS-MAX | B1은 예상 최대 행정을 쓰고 $O$를 더한다 |
| D-g W-NA | 등급 없음. 질량(하중) 항 필요 여부는 새 예측 형식이 정해진 뒤에 다시 본다(아래 제안) |

**제안**(판정 밖, 결정은 사용자)

- 제안 1(D-d 재등록 범위): 새 예측 형식 개정판은 **결과를 본 뒤의 개정**이므로 첫머리에 그 사실을 적어야 한다. 이번 값에서 보이는 빈 곳은 세 가지다. (가) READY 행의 예측 부족 +6~+14 mm는 과도 초과(19.9~23.2 mm)와 LOC 뒤 침하(9.9~13.3 mm) 가운데 P-A 꼴이 담지 않는 몫이다. (나) SGS 행은 판독 최대가 하한이라 $e$ < 0(예측 > 실제)이 그대로 $E_q$를 정한다(C4 −27.390 mm). 하한 행을 어떻게 셀지(예: "예측이 가드 이상이면 일치" 같은 한쪽 판정)를 결과 전 문장으로 정하지 않으면 같은 일이 되풀이된다. (다) LOC 뒤 침하가 하중 재분배로 설명되지 않는 다리(rev1 7절)가 예산 다리다. 개정판 초안은 control-expert, 플랜트 기구 확인(점성 지연·레벨링 중 동하중)은 dynamics-expert·terramechanics-expert에 맡기기를 제안한다.
- 제안 2(B1 진행 여부): PRED-FAIL과 FUP-OUT이 함께 나왔으므로, B1을 계속할지(새 형식 재등록 → 같은 Chrono 6행 재판정) 아니면 J2 경사 운용 권고(시작 조건 축소)로 먼저 닫을지를 사용자가 정하기를 제안한다. 앞쪽이면 새 형식은 이번 Chrono 결과를 본 뒤의 것이므로 **새 Chrono 행(다른 경사·오거 단계)으로 검증**해야 독립 근거가 된다.
- 제안 3(C3 probe 단계 가드 초과, 안전 기록 첫머리): 행정 예산 가드가 `probe` 단계에서 동작하지 않는 것이 설계 의도인지 control-expert(명세)·python-expert(코드 줄)로 확인한다. 이번 등급에는 영향이 없다(C3는 D-e 행이 아님).
- 제안 4(K-77): 다음 개정 때 "적합 다리 0개로 비가 NA면 κ 비선형 표시도 NA" 문장을 넣는다(사용자 결정 2026-11-12, 4.3).

### 1.5 사용자 질문 (D-e·D-f에 따른 것, 원판 11절)

- D-f `FUP-OUT` → **Q6 질문 필요**: "J2 연약 지면 fup(앞들림, pitch −2.8°, 오거 상단) 경사는 B1 범위(틈 여유 0~30 mm)로 풀 수 없다. J2 경사 운용 권고(시작 조건 축소 등)로 분리해 정할지?" 메인 세션이 AskUserQuestion으로 묻는다.
- 질문에 붙일 문장(TR-4, 원판 3.3 D-e): "SCM 명목 세트 안의 여유이고 실토양 여유가 아니다. $k_{eq}$ −4 %이면 침하가 +22~30 mm 늘어난다."
- D-e `B1-OPEN` → D-e에 따른 질문은 없다(질문 조건은 `NEED-RECHECK`).

### 1.6 G-S 건조 실행 공개 (원판 2.3, 판정서 1절에 적을 것)

| 항목 | 내용 |
|---|---|
| 시각 | 2026-11-12T11:25:55 ~ 11:34:08 +09:00(`progress.log`), 본 실행 시작 12:51:34보다 앞섬(I-16) |
| 명령 | `s9_batch.py run V5-B1-CREEP-GS`(Chrono-dev `python.exe -I -X utf8 -u … run_S9.py level …`), C1 꼴 `B1_J2_B_bottom_Fs4_VB_fdown`·C6 꼴 `B1_J2_B_bottom_Fs4_m1p1_VB_fdown`, `--duration 10`, P 2병렬. argv는 본 행과 `--duration`만 다르다(`batch.json`) |
| 결과 | 2/2 rc 0(벽시계 492 / 488 s), `gs-check` ok(메인 세션 확인) |
| 출력 범위 | rc, `expect_controller.ok`, 태그 문자열, `hull_hook`, `num_threads_chrono`, 5.1 격자 기록·M-4h·M-12 입력 필드의 키 이름 존재. 힘·행정·침하·시각 값은 보지 않았다 |
| 하네스 꼴 | H-P VB e0·H-M0 꼴은 하네스 32실행의 같은 꼴 줄로 필드를 확인했다(prelaunch 4·7절) |
| 커밋 | G-S와 하네스는 `7246c19`, 본 실행은 `bd64cc4`. 차이는 `06_analysis/02_control/b1/` 아래 10파일뿐이고 `03_src`·`04_scripts`는 0이다(실행 전 감사). 그래서 G-S를 다시 하지 않았다 |
| 규칙과 다른 점 | 폴더 `07_results/S9/batch_V5-B1-CREEP-GS_20261112_112555`에 result.json·npz 전체가 남아 있다. 원판 2.3은 "끝나면 키 목록만 남긴다"이다. 사용자 결정(2026-11-12, 실행 전 감사 확인 3)으로 남겨 두고 공개한다 |
| 순서 | G-S(11:25:55~11:34:08)는 rev1 봉인(11:59:43)·상수 커밋(12:08)보다 먼저 돌았다. 원판 3.0 순서("K 상수 고정 → G-S")와 다르다. G-S 출력은 상수와 무관하다(실행 전 감사 기록) |

## 2. 등급별 계산 행과 핵심 수치

수치는 두 경로가 같다(K-R 일치, 길이 최대 차 3.9×10⁻¹⁶ m). 키 이름은 경로 1 `rows.<C>.metrics.` / 경로 2 `rows.<C>.m.` 기준이다.

### 2.1 행 요약 (예산 다리 $b^\ast$)

| 행 | 사례 | $b$ / $b^\ast$ | $n_{L,1}$ / $n_L$ / 취소 | $n_R$ | $n_{\max}$ | SGS 주기(다리) | $s(t_L)$ | $s_{\max}$ | $g$ |
|---|---|---|---|---|---|---|---|---|---|
| C1 | `B1_J2_B_bottom_Fs4_VB_fdown` | FL / FL | 461 / 461 / 0 | 1161 | 747 | 없음 | 599.169 | 680.176 | 2.624 |
| C2 | `B1_J2_B_middle_Fs4_VB_fdown` | FL / FL | 465 / 465 / 0 | 1357 | 733 | 없음 | 583.916 | 678.929 | 3.871 |
| C3 | `B1_J2_B_top_Fs4_VB_fdown` | FL / FL | 460 / 460 / 0 | 1162 | 610 | 없음 | 573.207 | 683.475 | −0.675 |
| C4 | `B1_J2_B_bottom_Fs4_VB_diag` | FR / FR | 432 / 481 / 2 | 없음 | 596 | 505(FR) | 645.021 | 681.197 | 1.603 |
| C5 | `B1_J2_B_top_Fs4_VB_fup` | RL / RL | 464 / 464 / 0 | 없음 | 897 | 502(RL) | 607.615 | 681.297 | 1.503 |
| C6 | `B1_J2_B_bottom_Fs4_m1p1_VB_fdown` | FL / **FR** | 488 / 488 / 0 | 없음 | 596 | 520(FL, FR) | 640.215 | 682.522 | 0.278 |

- 단위: 행정·$g$ mm, 주기 $n$(× 0.1 s = 절대 시각). 키: `M-1.n_L1`·`n_L`·`loc_revokes`·`n_R`·`n_max`, `M-2.n_sgs`·`s_L`·`s_max`·`b_star`·`g_m` / `n_L1`·`n_L`·`loc_revoked`·`n_R`·`n_max`·`n_sgs`·`s_L`·`s_max`·`b_star`·`g`.
- C6은 계획 예산 다리 FL과 실제 $b^\ast$ FR가 다르다(FR 682.522 > FL 682.221 mm). 등급에는 $b^\ast$를 쓴다(원판 2.1).
- SGS 행(C4·C5·C6)은 SGS(`FAULT_LIFT_STROKE_LIMIT:soil`, 같은 주기 `WARN_LIFT_STROKE_LIMITED`) 뒤에도 판독 최대가 나왔다($n_{\max} > n_{sgs}$: C4 596 > 505, C5 897 > 502, C6 596 > 520). 두 경로 모두 기록된 판독 최대를 그대로 $s_{\max}$로 썼다(K-13 일치). 해석 메모는 2.5.
- E3c10은 6행 모두 첫 LOC 주기에 `INFO_LOC_CLEARANCE_MARGIN:80`이고 $m_L$ = 0.030 m(출처 E3c10)다. R4c30 사건 0, `..._SKIPPED:order` 0. T-14 대조 6행 모두 일치(차 0).
- 첫 READY $t_R$: C1 116.1 s, C2 135.7 s, C3 116.2 s(C3는 118.8 s에 다시 `level`, 149.0 s에 두 번째 READY). C4·C5·C6는 READY 없음(SGS 안전 정지).

### 2.2 D-a 크리프 허용 → ZA-2

| 행 | $\Delta z^{post}_{b^\ast}$ 원시 | 보정 | 보정 `NA` 사유 | 하네스 VB e0 / V0 e0($b^\ast$ 다리) | $z(t_{\max}) - z(t_L)$(기록) |
|---|---|---|---|---|---|
| C1 | 11.918 | NA | $t_e$(n 1161) 격자 기록 무효($r_\sigma$ 0.00996 > 0.005) | 1.188 / 0.854 | 3.514 |
| C2 | **13.337** | NA | $t_e$(n 1357) 기록 무효($r_\sigma$ 0.01010) | 5.531 / 5.681 | 6.448 |
| C3 | 9.883 | NA | $t_e$(n 1162) 기록 무효($r_\sigma$ 0.00823) | 5.700 / 5.233 | 3.767 |
| C4 | −0.019 | NA | $t_L$(n 481) 기록 무효($r_\sigma$ 0.0209) | 0.000 / 0.160 | −0.019 |
| C5 | 11.346 | **11.481** | — | 6.973 / **7.168** | 11.346 |

- $Z_{ch}$ = 13.337 mm(C2), $Z^{corr}_{ch}$ = 11.481 mm(C5 하나), $Z_{hn}$ = 7.168 mm(H-P C5 V0 e0 RL, 하네스 10실행 가운데 최대). 키: `grades.D-a.Z_ch`·`Z_corr`·`Z_hn` / 같은 이름.
- T-1: 원시 13.337 − 7.168 − 3 = +3.169 mm > $\varepsilon_{th}$ → ZA-2. 보정 11.481 − 7.168 − 3 = +1.313 mm > $\varepsilon_{th}$ → ZA-2. 최종 ZA-2(보수 쪽). 두 등급이 같으므로 "격자 위상 의존" 표시는 없다.
- 표시: 경로 1 "격자 기록 없음: C1, C2, C3, C4", 경로 2 `flags` [] + `corr_na_rows` [C1, C2, C3, C4](같은 사실, 4.4).
- C-5 (나) "격자 몫 포함 보정"은 원시만 ZA-2이고 보정이 ZA-1일 때다. 이번에는 둘 다 ZA-2라 해당 없다. 그래서 D-a 하네스 보정량은 경로 1 null이 규칙 문장과 맞다(K-93, 4.2).
- C-5 (다) 기록 $z_{b^\ast}(t_e)(f(t_e) - f(t_L))$: C5 RL +0.011 mm만 값이 있다(C1~C4는 기록 무효로 NA). 참고 $z(t_{\max})(f(t_{\max}) - f(t_L))$(경로 1만, U-09): C1 +0.420, C2 −0.762, C5 +0.011 mm, C3·C4 NA.
- 3.4 D-d 칸 "$E_q$와 $Z_{ch} - Z^{corr}_{ch}$를 나란히": $Z_{ch} - Z^{corr}_{ch}$ = 1.856 mm(서로 다른 행 C2·C5의 값끼리의 차), $E_{q^\ast}$ = 27.390 mm(2.5).
- 효과: $Z_{\,B1} = \max(13.337, 11.481, 7.168) + Z_{soil}$ = 13.337 mm + $Z_{soil}$(경로 1 `Z_B1_before_soil_m`). $Z_{soil}$ 후보(가정, TR-8): Z0 0 mm, Z1 2 mm, Z2 $0.1\,z_{b^\ast}(t_R)$ = 10.054 mm(경로 1 `Z_soil_candidates`, U-12 한 경로), Zf 현장 평판 유지 시험값(없음).

### 2.3 D-b 과도 초과 → OS-MAX

| 행 | Chrono $\delta^{os}_{b^\ast}$ | 하네스 H-P VB e0 $\delta^{os}$($b^\ast$ 다리) | 행 최대 |
|---|---|---|---|
| C1 | 19.901 | NA(하네스 짝 SGS, $n_{sgs}$ 407) | 19.901 |
| C2 | 21.383 | 2.366 | 21.383 |
| C3 | **23.197** | 4.064 | 23.197 |
| C4 | NA(READY 없음, 뺌) | — | — |
| C5 | NA(READY 없음, 뺌) | — | — |

- $O$ = 23.197 mm(`grades.D-b.O_m` / `O`). T-2: 23.197 − 5 = 18.197 mm > $\varepsilon_{th}$ → OS-MAX. 계산 행 C1~C3(3), 뺀 행 C4·C5(경로 1 `dropped_no_ready`, 경로 2 `na_rows`).
- 하네스 $\delta^{os}$ 열은 경로 1 하네스 기록(`P1.harness`, U-10 한 경로)이다. 경로 2는 이 값을 내지 않아 K-R 감사가 O의 하네스 성분을 재도출하지 못했다(감사 "검사하지 못한 것"). $O$는 Chrono C3 값이 정한다.
- 참고 $t_{\max} - t_L$: C1 28.6, C2 26.8, C3 15.0, C4 11.5, C5 43.3, C6 10.8 s.

### 2.4 D-c 하네스 대응 → H-OPT

| 행 | 방향 | Chrono $s_{\max}$ | 하네스 VB e0 $s_{\max}$ | 원시 $\Delta_r$(분류) | $\delta^{grid}_r$($t_{\max}$) | 보정 $\Delta^{corr}_r$(분류) | $\delta z_{1n}$ |
|---|---|---|---|---|---|---|---|
| C1 | fdown | 680.176 | 682.411 | −2.235 (0) | +1.782 | −4.017 (−) | 0.421 |
| C2 | fdown | 678.929 | 669.470 | +9.460 (+) | +0.845 | +8.614 (+) | 0.430 |
| C3 | fdown | 683.475 | 671.154 | +12.321 (+) | 대체 범위 | [+7.825, +15.042] (+, 대체 범위) | 0.441 |
| C4 | diag | 681.197 | 682.428 | −1.231 (0) | 대체 범위 | [−6.541, +1.981] (미확정, 대체 범위) | 0.521 |
| C5 | fup | 681.297 | 680.449 | +0.847 (0) | −1.612 | +2.459 (0) | 1.037 |

- 등급(T-3): 보정 "+"인 행 C2·C3 → H-OPT. 원시 등급도 H-OPT(C2·C3 "+"). 키: `grades.D-c.per_row.<C>.raw_m`·`corr_low_m`·`corr_high_m`·`corr_class`·`raw_class` / `detail.<C>.delta_raw`·`corr_lo`·`corr_hi`, `signs`, `raw_signs`.
- C3·C4는 $t_{\max}$ 격자 기록이 무효($r_\sigma$ C3 0.00812, C4 0.0217 > 0.005)라 대체 범위(0.4 표 0.01 m 위상 범위, 패드 종류별)를 썼다. C4는 구간이 −3 mm와 +3 mm를 모두 걸쳐 "격자 위상 의존(부호 미확정): C4"이고 세지 않았다.
- "절점 계단 수준" 행 없음($\lvert\Delta^{corr}_r\rvert \le \delta z_{1n}$인 행 없음).
- 효과: 방향별 최대 $\Delta^{corr}$는 fdown C2 +8.614 mm(기록값) / C3 대체 범위 상단 +15.042 mm, diag 미확정, fup +2.459 mm(0 분류). fdown 방향은 B1 채택 전에 Chrono 확인 행을 둔다.
- 짝 산포(기록, `pair_differences.<C>.harness_s_max_spread`, VB·V0 × e0·e0.002): C1 681.977~682.421, C2 669.470~682.609, C3 670.829~671.598, C4 682.428~682.766, C5 680.051~680.449 mm.

### 2.5 D-d 예측자 → PRED-FAIL

| 행 | P-A | P-B | P-D | P-G | P-C | 하한(SGS) |
|---|---|---|---|---|---|---|
| C1 | +6.100 | +6.100 | +6.100 | +6.989 | −13.755 | 아니오 |
| C2 | +10.450 | +10.261 | +10.450 | +11.328 | −9.593 | 아니오 |
| C3 | +13.661 | +13.661 | +13.661 | +14.644 | −6.193 | 아니오 |
| C4 | **−27.390** | −28.667 | −27.390 | +21.220 | −48.522 | 예 |
| C5 | −18.264 | −18.264 | −18.264 | **−30.862** | −38.119 | 예 |
| $E_q$ | **27.390** | 28.667 | 27.390 | 30.862 | 48.522 | |
| $E_{\text{P-A*}}$(M-12, 경로 1만) | 27.390 | | | | | |

- $e = s_{\max} - \hat s$ [mm], + = 예측 부족. 키: `metrics.M-6.errors.<q>[b*]` / `pred.e.<q>`, `grades.D-d.E_q` / `E`.
- T-4: 최소 $E$ = 27.390 mm(P-A, P-D 동점 → 순서상 $q^\ast$ = P-A). 27.390 − 10 = 17.390 mm > $\varepsilon_{th}$ → PRED-FAIL. T-14 어긋난 행 없음(제외 0, Q-5 (a) 행 집합 C1~C5).
- 7.4 SGS 하한: C4·C5의 $e$(P-A) < 0이라 그대로 썼다. P-G의 C4 $e$ = +21.220 mm ≥ 0은 하한으로 썼다. **등급이 `PRED-q`가 아니라 `PRED-FAIL`이므로 7.4의 "하한 포함" 문구를 붙일 조건(`PRED-q`)은 생기지 않았다.** 표시는 두 경로가 다르다: 경로 1 `flags` "하한 포함"(SGS 행 C4·C5 포함), 경로 2 `lower_bound_included` false(4.4).
- 7.5 M-12(경로 1만, X-02·X-03): $E_{\text{P-A*}}$ = 27.390 mm = $E_{\text{P-A}}$. Chrono 6행 재구성 기록(행마다 1건)의 앵커 경로는 모두 ①, $\max\lvert d\rvert$ = 0.048 mm(C5), C6 0.030 mm, 나머지 0. T-13 "앵커 단일 표본 의존" 표시 없음(차 0).
- 예측 입력(K-39~K-45 일치): $\hat c(t_L)$ C1 6.855, C2 5.817, C3 5.267, C4 8.787, C5 5.152, C6 7.007 mm. P-G 모서리 $k^\ast$: C1~C3 RR, C4 RL, C5 FR, C6 RR(경로 1 색인 0/1/2 ↔ 경로 2 이름, 대응표 0절).
- P-A 한계 기록(7.2, 등급에 안 씀): 관측 $h$의 네 다리 평균·폭($t_{\max}$) C1 73.088 / 4.948, C2 75.366 / 5.389, C3 81.393 / 6.187, C4 29.017 / 28.767, C5 53.272 / 16.860 mm. $\varepsilon$ = C1 +0.969, C2 −0.259, C3 +1.239 mm(READY 없는 행은 NA). $Z_{k^\ast}$는 경로 1만 냈다(4.5).
- 해석 메모(판정서 작성자 확인 계산, 등급 불변): SGS 행의 $s_{\max}$를 "가드 도달 값"으로 읽어 0.6828 m로 두어도 C4 $e$(P-A) = −25.787 mm, C5 −16.761 mm이고 C1~C3만으로도 13.661 mm라 PRED-FAIL은 같다. 같은 읽기로 D-c의 C4 원시 +0.372 mm(0), C5 원시 +2.351 mm(0)·보정 +3.963 mm(+)가 되지만 C2·C3 때문에 H-OPT는 같고, D-e는 C4 SGS라 B1-OPEN이 같다.

### 2.6 D-e B1 필요성 → B1-OPEN

| 행 | $g$ | SGS | $g^{corr} = g + \delta^{grid}$ | $\tilde g$ | 출처 | $g^{corr}$ 위상 범위(경로 1만, U-12) | T-5 |
|---|---|---|---|---|---|---|---|
| C1 | 2.624 | 아니오 | 4.406 | 0.110 | 격자 기록 | [0.025, 6.919] | 미충족 |
| C2 | 3.871 | 아니오 | 4.716 | 0.334 | 격자 기록 | [1.220, 8.253] | 미충족 |
| C4 | 1.603 | 예(505, FR) | NA | −7.095 | 기록 무효 → $g - z(t_{\max})(f_{\max} - f_{\min})$ | [−1.609, 6.912] | 미충족 |

- 키: `grades.D-e.per_row.<C>.g_m`·`g_corr_m`·`g_tilde_m`·`sgs` / `rows.<C>.g`·`g_corr`·`g_tilde`·`sgs`.
- 세 행 모두 $\tilde g - 20 < -\varepsilon_{th}$이고 C4는 SGS → B1-OPEN.
- 해석(TR-4, 원판 3.3 D-e): "SCM 명목 세트 안의 여유이고 실토양 여유가 아니다. $k_{eq}$ −4 %이면 침하가 +22~30 mm 늘어난다." 경로 1 `note`에도 같은 앞 문장이 있다.

### 2.7 D-f fup 범위 → FUP-OUT

| 대상 | 결과 | 근거 |
|---|---|---|
| C5 Chrono | SGS, `FAULT_LIFT_STROKE_LIMIT:soil:RL` 50.2 s($n$ 502), $g$ 1.503 mm | result.json `events` |
| H-M0 C5 VB e0($m$ = 0) | SGS($n_{sgs}$ 420), E3c10 `INFO_LOC_CLEARANCE_MARGIN:50`, R4c30 0 | 경로 1 `grades.D-f.pairs`, 하네스 기록 |
| H-M0 C5 V0 e0($m$ = 0) | SGS($n_{sgs}$ 404), E3c10 50, R4c30 0 | 같음 |

- 짝 2개가 모두 남았다(R4c30 사건 0, V-4 유효) → "짝 1개" 경우 아님. 경로 1 `rows` [C5, H-M0|C5|VB|e0, H-M0|C5|V0|e0], 경로 2 `pairs` 2.
- 3.4 D-f 칸 "C5의 $g$와 $\delta^{grid}$": $g$ = 1.503 mm, RL $\delta^{grid}(t_{\max})$ = −1.612 mm(격자 기록 유효, $f$ 0.98736), 합 $g + \delta^{grid}$ = −0.109 mm.

### 2.8 D-g ×1.1 감도 → W-NA

- C6는 VALID이지만 D-d가 PRED-FAIL이라 W-NA다. $e$(C6, $q^\ast$)·$E_{q^\ast}$·비 |e(C6)| / $E_{q^\ast}$는 두 경로 모두 NA로 냈다(등급 수치 NA). 그래서 비가 1.61 근처인지("오차가 침하와 같이 커짐" 표시)는 판단하지 않았다.
- 기록(행 값): C6 $b^\ast$ FR의 $e$ = P-A −22.290, P-B −22.290, P-D −22.290, P-G +21.486, P-C −42.145 mm(SGS 행, 하한).
- 3.4 D-g 칸 "C6의 $\delta^{grid}$": FR $t_{\max}$($n$ 596) 기록 유효, $f$ 0.99069, $\delta^{grid}$ = −1.125 mm. C-5 (다) 기록 $z(t_e)(f(t_e) - f(t_L))$ = +1.105 mm.
- C6 R1-4 합 비 1.1017(×1.1 행이라 [1.00, 1.08] 표시 대상 아님, 표시 없음). I-11: 플랜트 질량 배율 1.1, 제어기 질량은 YAML 명목(경로 1 직접 확인 $W_{ref}$/YAML 질량 = 9.80665, 경로 2 같은 키로 확인).

### 2.9 D-h 기준 정합 → K-SAME

- `P7_REF` `s2d_SC.jsonl`(sha256 `70e91ec1…`, 경로 2 `p7_ref_sha256` 같음)의 P0 줄 `d1.key` 대 H-P 20실행 `commands_sha256`: same 20, diff 0, na 0. 실행별 상태 20/20 `K-SAME`(K-109 일치). `diff_keys` [].

### 2.10 7.3 상수 (rev1, 하네스만, Chrono 결과 전 고정)

| 상수 | 전방 330(FL·FR) | 후방 250(RL·RR) | 적합 / 제외 다리 | 최대를 정한 실행·다리 |
|---|---|---|---|---|
| $\kappa_z$ [m/N] | 8.269×10⁻⁷ | 2.530×10⁻⁵ | 전방 13/27, 후방 8/32 | 전방 H-P C5 V0 e0 FR, 후방 H-P C3 VB e0 RL |
| $C_{type}$ [m/N⁵] | 8.249×10⁻²⁸ | 1.691×10⁻²⁵ | 전방 4/36, 후방 8/32 | 전방 H-P C5 V0 e0 FR, 후방 H-P C3 VB e0 RL |
| $\delta_{allow}$ [m] | 0.019855(두 종류 공통, H-P $b^\ast$ $\delta^{os}$ 최대) | | | |
| κ 비 | 8,224(κ 비선형) | 2.20(κ 비선형) | | |

- $W_{fit}$ = 1,000 N(가정, U-R1-2 (c)). 감도 600·2,000 N은 기록만(2,000 N에서 후방 κ·C와 전방 C의 적합 다리 0개 → NA). 두 경로 상수 상대차 최대 2.0×10⁻¹⁴, 적합 다리 목록 같음(K-70~K-79).

### 2.11 R1-4 기록 (Chrono 6행, 등급에 안 씀)

| 행 | $n_L$ | $\sum F(n_L)/\sum W^{static}$ | $\hat W_{b^\ast}$ [N] | "재분배 가정 이탈" |
|---|---|---|---|---|
| C1 | 461 | 1.0359 | −1,005 | 없음 |
| C2 | 465 | 1.0332 | +228 | 없음 |
| C3 | 460 | 1.0374 | −1,555 | 없음 |
| C4 | 481 | 1.0362 | +1,545 | 없음 |
| C5 | 464 | 1.0354 | −841 | 없음 |
| C6 | 488 | 1.1017 | −4,258 | 없음 |

- $n_L$에서 네 다리 모두 신장 중이다(판독 행정 속도 3.1~21.3 mm/s, 최소는 C3 RL, 6행 모두 > 0; 판정 후 감사 정정).

## 3. 원판 "판정서에 적을 것" 대조

| # | 규칙 위치 | 요구 | 이 판정서 |
|---|---|---|---|
| 1 | 2.3 | 판정서 1절에 G-S 시각·명령·출력 범위 | 1.6 |
| 2 | 3.1 V-2 | `INVALID` 원인 | 1.1(`INVALID` 행 없음) |
| 3 | 3.2 | 각 등급의 계산 행 ID 목록과 행 수, 0개 등급 `NA` | 1.2 표·2절 |
| 4 | 3.3 D-a | 원시·보정·최종 등급, "격자 위상 의존"·"격자 기록 없음" 표시, C-5 (다) 기록, $z(t_{\max}) - z(t_L)$ 기록 | 2.2 |
| 5 | 3.3 D-c | 원시·보정 등급, 대체 범위·부호 미확정·절점 계단 표시, 행별 $\delta z_{1n}$ | 2.4 |
| 6 | 3.3 D-d·7.5 | $E_q$ 옆에 M-12의 $E_{\text{P-A*}}$, $\max\lvert d\rvert$, T-13 표시 | 2.5 |
| 7 | 3.3 D-e | $g^{corr} = g + \delta^{grid}$와 위상 범위로 정한 $g$ 범위 병기, TR-4 문장 | 2.6 |
| 8 | 3.3 D-g | 비 |e(C6)| / $E_{q^\ast}$, 1.61 근처면 "오차가 침하와 같이 커짐" | 2.8(비 NA) |
| 9 | 3.3 안전 기록 | `FAULT_STROKE_END`, T-8, T-9가 있으면 `SAFETY_NOTE`로 첫머리에 | 첫머리 "안전 기록"(없음) |
| 10 | 3.4 D-d | $E_q$와 $Z_{ch} - Z^{corr}_{ch}$를 나란히 | 2.2·2.5 |
| 11 | 3.4 D-f | C5의 $g$와 $\delta^{grid}$ | 2.7 |
| 12 | 3.4 D-g | C6의 $\delta^{grid}$ | 2.8 |
| 13 | 4.1 I-6 | 실행 중 affinity 변경 | 5절(기록된 변경 없음) |
| 14 | 4.1 I-12 | 러너 로그 `errors N` 비영이면 `errors_left` = 0일 때만 진행, 첫 시도 오류 | 1.1(`errors N` 줄 없음, `errors_left` 0, 첫 시도 오류 없음) |
| 15 | 4.3 | 재실행이면 `rerun_of` | 1.1(재실행 없음) |
| 16 | 7.4 | `PRED-q`가 하한 포함 값으로 나오면 "하한 포함" | 2.5(PRED-FAIL이라 조건 없음, 두 경로 표시 공개) |
| 17 | 11 | 등급표, 행 상태, 예측 대조, `SAFETY_NOTE`, 건조 실행 공개, D-e·D-f에 따른 사용자 질문 | 1.2·1.1·3.1·첫머리·1.6·1.5 |
| 18 | 10.1 판정 후 | C(K-R), E(등급별 행 수), I(V-2 결과), T(경로 2 출력 sha가 경로 1 실행보다 앞섬) | 4.1·1.2·1.1·4.6 |

### 3.1 방향 예측 대조 (원판 8절, 기록, 등급에 안 씀)

| # | 예측 | 결과 | 맞음 |
|---|---|---|---|
| P-1 | C1~C3 FL $\Delta z^{post}$ 0~15 mm, 뒤 패드보다 작음. C5 RL 15~60 mm, ×1.0 다섯 행 중 최대 | FL 11.918 / 13.337 / 9.883 mm, 뒤 패드 30.3~47.8 mm. C5 RL 11.346 mm(15 미만, 최대는 C2 FL 13.337) | 앞 부분 맞음, C5 부분 틀림 |
| P-2 | READY → 끝 추가 침하 ≤ 5 mm(재레벨 없으면 ≤ 0.5), $t_{creep}$ ≤ 마지막 READY + 30 s | $b^\ast$ $z(t_{end}) - z(t_R)$: C1 +0.034, C2 +0.034, C3 +1.100 mm(C3는 READY 뒤 재레벨). $t_{creep}$ 117.7 / 137.0 / 150.0 s ≤ 마지막 READY 116.1 / 135.7 / 149.0 s + 30 s. C4~C6 READY 없음 | 맞음(READY 행) |
| P-3 | 원시 $\Delta_r$ ∈ [−8, +3] mm, 0 또는 음이 더 많음 | −2.235, +9.460, +12.321, −1.231, +0.847. 분류 0 3, + 2 | 범위 틀림(C2·C3), 다수 쪽은 맞음 |
| P-4 | $\delta^{os}$ fdown·fup 5~30 mm, diag 3~15 mm | fdown 19.901 / 21.383 / 23.197 mm. fup(C5)·diag(C4) NA(SGS) | fdown 맞음, 나머지 판단 불가 |
| P-5 | C1 SGS 또는 $g$ < 10 mm, `FAULT_STROKE_END` 0, 다리 부상 0 | C1 $g$ 2.624 mm, 둘 다 0 | 맞음 |
| P-6 | C5 SGS(RL), Chrono 가드 시각 ≤ 하네스 VB e0 가드 시각 | C5 SGS RL 50.2 s. 하네스 H-P C5 VB e0 SGS 38.7 s(절대 시각). 마지막 LOC 기준으로는 Chrono +3.8 s, 하네스 +4.0 s | SGS 맞음, 시각(절대) 틀림 |
| P-7 | `P7_REF`에 키가 있으면 K-SAME, Chrono E3c10 LOC의 `order_gate.decisions` 0 | K-SAME 20/20. `order_gate_decisions` C4 2(LOC 취소 2회 행, LOC별 구분은 출력에 없음), 나머지 0 | K-SAME 맞음, C4 틀림 |
| P-8 | P-A $e$ > 0 모든 VALID 행, $E_{\text{P-C}}$ ≤ 10 mm | C1~C3 > 0, C4·C5·C6 < 0. $E_{\text{P-C}}$ 48.522 mm | 틀림 |
| P-9 | C6: C1보다 $g$ 작거나 SGS가 이름, `W-EXT` 예상 | C6 SGS 52.0 s(C1 SGS 없음), $g$ 0.278 < 2.624 mm. D-g는 W-NA | 앞 부분 맞음, W-EXT는 판단 불가 |
| P-10 | 모든 LOC 앵커 경로 ② 0건, $\lvert d\rvert$ ≤ 5.5 mm, $d$ > 0은 ≤ +2.7 mm | Chrono 재구성 기록 6건(경로 1, 행마다 마지막 LOC 1건. C4는 LOC 3회 가운데 기록 1건) 모두 ①, 최대 0.048 mm. 하네스 38 LOC 모두 ①, 최대 0 | 맞음(기록된 LOC) |
| P-11 | ×1.0 C1~C5 R4c30 0, `..._SKIPPED:order` 0, $m_L$ 0.03 또는 0 | 모두 0, $m_L$ 0.03 | 맞음 |
| P-12 | H-M0 4실행 E3c10 50 mm 또는 사건 없음, R4c30 0 | 4/4 `INFO_LOC_CLEARANCE_MARGIN:50`, R4c30 0 | 맞음 |
| P-13 | G-S 첫 시도에서 모든 필드 검사를 통과하지 못할 수 있음 | 2/2 rc 0, `gs-check` ok | 통과(예측한 실패는 없었음) |
| P-14 | ×1.0 $z(t_R) - z(t_{\max})$ ≥ 0이고 예산 다리 ≤ 6 mm | C1 8.405, C2 6.889, C3 6.116 mm(≥ 0, 6 mm 초과). C4·C5 NA | ≥ 0 맞음, ≤ 6 mm 틀림 |
| P-15 | $t_L \to t_{\max}$ 예산 다리 $\lvert\Delta f\rvert$ ≤ 0.03 | 두 시각 모두 유효 기록인 행: C1 0.0047, C2 0.0083, C5 0.0001(C6 0.0092). C3($t_{\max}$ 무효)·C4(둘 다 무효)는 판단 불가 | 맞음(유효 행) |
| P-16 | C5 RL의 P-B 오차가 C1~C4 예산 다리보다 큼 | $\lvert e\rvert$ C5 18.264 < C4 28.667 mm | 틀림 |
| P-17 | `t_final_s`가 나온 행에서 그 뒤 예산 다리 하중 변화 ≤ 0.5 kN | 두 경로 출력에 이 양이 없다 | 계산하지 않음 |

- P-6 시각은 원판 규약대로 절대 시각으로 비교했다. 하네스와 Chrono는 LOC 시각 자체가 다르다(C5 LOC 하네스 34.7 s, Chrono 46.4 s).

## 4. 공개 항목

### 4.1 K-R 결과 (원판 9절, `b1_kr_audit.md`)

- 펼친 단위 2,751개: 일치 2,629, 양쪽 NA 120(모두 구조적), 불일치 1(K-77), 대응 없음 1(K-107).
- 항목 K-01~K-109: 일치 102, 불일치 1(K-77), 대응 없음 1(K-107), 다른 항목을 가리키기만 함 4(K-84→K-53, K-87→K-01, K-88→K-08, K-89→K-69), 제외 1(K-93).
- 실수 최대 차: m 3.9×10⁻¹⁶, N 4.4×10⁻¹¹, 상대(무차원·m/N) 2.0×10⁻¹⁴, $r_\sigma$ 4.9×10⁻¹⁷, rad·m/s·s 0. 허용값은 결정 덧붙임 3(N 1×10⁻⁶, rad 1×10⁻¹², 무차원·m/N 상대 1×10⁻⁹, $r_\sigma$ 1×10⁻¹², m/s 1×10⁻⁹, s 1×10⁻⁹, 길이 1×10⁻⁹ m는 규칙 9절)이다.
- `UNDETERMINED`가 되는 등급: 없다(K-77이 들어가는 등급이 없다).
- 공허 일치: K-85·K-86(T-8·T-9)은 두 경로 모두 사건이 없어 같다. K-16·K-17은 READY 행에서 양쪽 NA다.
- 감사가 다시 보지 못한 것: K-03 종료 코드(prelaunch 10.2·10.3 기록 근거), D-b O의 하네스 성분, D-e $\tilde g$의 $f_{\max}$ 대체항(행별 $\tilde g$ 일치와 문턱 비교만 확인).

### 4.2 K-R 제외 (사용자 결정 2026-11-12, 결과 전)

| 기호 | 내용 | 기록한 경로 |
|---|---|---|
| X-01 | M-4 LOC 뒤 최대 침하율 | 두 경로가 정의가 다름(경로 1 10 Hz $n > n_L$, 경로 2 1 ms 계열 $t_L$ 포함). 판정서에 쓰지 않음 |
| X-02 | Chrono M-12 전부 | 경로 1(R-G4 재구성). 경로 2는 NA |
| X-03 | $E_{\text{P-A*}}$·$e$(P-A*)·T-13 "앵커 단일 표본 의존" | 경로 1 |
| X-04 | T-13 문턱 행 | X-03에 따름 |
| U-01~U-12 | 경로 2 출력에 대응 키가 없는 기록 12묶음: t_dep, M-4h, M-6 $b^\ast$·$b$ 밖 두 다리, P-G 보조 값, M-7, M-8 나머지, M-9, M-10 $s_L$·$s_R$·$\delta^{os}$·$g$ 짝 차, M-11 일부, 하네스 실행별 M-1~M-11, D-f 짝 이름 목록, D-a $Z_{soil}$·$Z_{\,B1}$ 바탕값·D-e $g^{corr}$ 범위·D-d 하한 표시 | 경로 1 |
| K-93 | D-a 하네스 보정량 | 경로 1 null, 경로 2 0.006169 m(= $Z_{ch} - Z_{hn}$). 원시·보정이 모두 ZA-2라 규칙 (나) 조건이 성립하지 않으므로 경로 1이 규칙 문장과 맞다. D-a 등급·계산 행은 계속 대조(일치) |

- 이 판정서의 2절 값 가운데 위 항목에서 온 것은 "경로 1만"으로 표시했다(2.2 $Z_{soil}$, 2.3 하네스 $\delta^{os}$, 2.5 M-12·$Z_{k^\ast}$, 2.6 $g^{corr}$ 범위, 3.1 일부).

### 4.3 K-77·K-107 처리 (사용자 결정 2026-11-12, 판정서 전)

- **K-77**(불일치): $W_{fit}$ 2,000 N 감도에서 후방 적합 다리 0개 → 두 경로 모두 κ 비 NA. 표시는 경로 1 `kappa_nonlinear` null, 경로 2 false. 규칙에 "비가 NA일 때 표시" 문장이 없는 정의 해석 차이다. 이 감도는 등급에 쓰지 않으므로(rev1 R1-3 감도 기록 문장) **개정 없이 정의 차이로 공개**한다. 원판 9절 끝 문장("원인이 정의 해석 차이면 개정판으로 정의를 고친 뒤 두 경로를 다시 돌린다")은 등급에 쓰이는 항목에만 적용했다. 다음 개정 때 "비가 NA면 κ 비선형 표시도 NA" 문장을 넣을 후보로 기록한다.
- **K-107**(대응 없음): D-g 계산 행은 경로 1 `rows` ["C6"](1), 경로 2는 행 목록을 내지 않는다. 대응표 규약은 W-NA가 아닌 경우만 정했다. **대응 없음으로 공개**하고 D-g 등급 W-NA는 유지한다(두 경로 등급 같음, 입력 D-d 등급 K-100과 C6 상태 K-01 일치).

### 4.4 정의 차이 (등급 불변)

| 항목 | 경로 1 | 경로 2 | 이번 영향 |
|---|---|---|---|
| D-d 하한 표시 | SGS 행이 계산 행에 있으면 "하한 포함" | $q^\ast$의 SGS 행 $e$ ≥ 0일 때만 `lower_bound_included` 참 | 없음. $E_{\text{P-A}}$ 27.390 mm는 SGS 행 C4에서 나왔고, C1~C3만으로도 13.661 mm > 10 mm |
| E-5 | identity `runner_log`(prelaunch 10.1: 최종 `<case>.log` Traceback 행 수로 채움) | rc + `<case>.log` Traceback | 없음. 두 경로 모두 차단 없음(Traceback 0) |
| $b^\ast$ 동점 | $\varepsilon_{th}$ 안의 첫 다리 | 정확한 argmax | 없음. 6행 모두 $b^\ast$ 같음 |
| pad_nodes 일치 | 8필드 완전 일치 | 원판 6절 5필드 상대 1×10⁻¹² | 없음. 6행 모두 두 기준으로 일치(경로 1 51,200 비교 차 0, 경로 2 1,600/1,800주기 불일치 0) |
| D-a 하네스 보정량(K-93) | (원시 ZA-2, 보정 ZA-1)일 때만 | 최종 ZA-2이면 항상 | 4.2 |
| κ 비선형 NA 표시(K-77) | null | false | 4.3 |
| D-a·D-c 표시 문자열 | "격자 기록 없음: C1~C4" / "격자 위상 의존(부호 미확정): C4", "대체 범위" | `flags` [] + `corr_na_rows` / "grid phase dependent (sign undetermined): C4", 행별 `substitute` | 같은 사실(K-98 일치) |
| 1 ms 계열 끝 조회 | None | 마지막 표본으로 자름 | 이번 값에서 차이 없음(K-R 일치) |
| V-1 FAULT 끝 판별 | `phases` 마지막 항목 | `FAULT_` 접두 사건 | 없음. SGS 3행 모두 `phases` 끝 `fault`이고 사건도 있음 |

### 4.5 한 경로만 낸 기록

- $Z_{k^\ast}$(원판 7.2 P-A 한계 기록): 경로 2 `h_rec.Z_k_star`는 초기값 null을 채우지 않는다. 경로 1만 `p_a_limit.Z_k_star_e_m`·`Z_k_star_max_m`을 낸다: C1 27.872 / 3.952, C2 30.355 / 8.262, C3 37.612 / 12.967, C4 11.157 / 11.157, C5 1.299 / 1.299, C6 38.009 / 38.009 mm($t_e$ / $t_{\max}$). 같은 블록의 나머지 102단위는 최대 차 2.8×10⁻¹⁷ m로 일치했다(K-R 감사 발견 3). 9절 K-R 목록(7.2는 $m_L$만)에 없는 항목이다.
- 4.2 U-01~U-12와 X-01~X-04 항목, 4.4 표시 문자열.

### 4.6 절차 사실

- **G-S 폴더 유지**: 1.6.
- **G-S가 상수 고정 전에 실행됨**: G-S 11:25:55~11:34:08, 하네스 11:25:56~11:30:17(동시), rev1 봉인 11:59:43, 두 경로 sha 재고정 12:05, 상수 커밋 12:08, prelaunch 12:13(실행 전 감사 기록 [T]). 원판 3.0 순서와 다르다.
- **실행 중 도구 수정과 sha 재고정**(Chrono 본 배치 시작 12:51:34 뒤, 첫 결과 파일 15:10:50 전, 사용자 결정 "Chrono 6행 지금 시작, 도구 수정은 worktree에서 병행")
  - 경로 1: 12:55(커밋 시각 12:55:15, 판정 후 감사 정정)에 브랜치 `b1-path1-fix` 커밋 `1ac4849`로 `b1_creep_metrics.py` sha256 `6b6e04acfd0cfb77e53b35981984bd4a9e4ccad2b4ce5446b6e5e7c018dda9d9`(원래 감사 대상 `a9518c65…`). 바뀐 것: D-h 키 `line["d1_key"]` 그대로, V-1 끝 단계를 `phases` 마지막에서 읽음.
  - 경로 2: 13:00 커밋 `24a108e`로 `b1_path2.py` sha256 `7a9d258fa3182506a82fbdca74c15a1b8a37bd7858cf413f959fe0f4f52183db`(원래 `f4f8be83…`). 바뀐 것: `--identity` 필수(I-11 포함), 원판 6절 pad_nodes 일치, E-5 rc + Traceback, D-b SGS 행 제외, 규칙·rev1·`P7_REF` sha 대조.
  - 재감사 `b1_creep_fix_reaudit.md`(Chrono 실행 중·결과 전, 본 배치 미열람): 차단 0. 남은 prelaunch 문장 수정 2건(10.1 E-5 정의, 10.2 `--identity`)은 결과 전에 고쳤다.
- **worktree 실행·병합은 판정 뒤**: 두 경로는 각자 고정 sha worktree에서 실행했다(경로 2 `.claude/worktrees/b1-path2-fix` `24a108e`, 경로 1 `.claude/worktrees/agent-a54833748c3f6b37d` `1ac4849`). prelaunch 10.2는 "경로 2 실행 전에 `b1-path2-fix`를 병합"이라고 적었지만, 실제로는 병합하지 않고 worktree에서 실행했고 병합은 판정 뒤 커밋 때로 미뤘다(prelaunch 11절 postrun). 이 판정서를 쓸 때 master HEAD는 `bd64cc4`이고 두 worktree 파일 sha는 위 값과 같다(다시 해시함).
- **경로 2 상수 출력 파일 이름 변경**: 실행 때 `--constants-out`을 `b1_constants_path2_rev1_run.json`으로 바꿨다(scratch 판 `b1_constants_path2_rev1.json`과 섞이지 않게). 두 파일 sha256이 `3b5e775b…`로 같다.
- **K-R 대응표·결정 시각**: 대응표 13:10:31(mtime), 결정 덧붙임 `b1_kr_map_decisions.md` 13:59:33(파일 안 표기 "13:59+09:00"). 호출문의 "13:2x"와 다르다. 둘 다 첫 result.json(C4, 15:10:50)보다 앞선다.
- **시간 근거는 mtime**: 해당 산출물이 모두 git 추적 밖(`??`)이고 출력 안에 시각 필드가 없다. 순서: 배치 시작 12:51:34 → 대응표 13:10:31 → 결정 13:59:33 → 첫 result.json 15:10:50 → 배치 끝 17:15:50 → 경로 2 실행 17:27:18~17:27:24(상수 17:27:22, 출력 17:27:24) → 경로 1 실행 17:27:38~17:27:41(출력 17:27:41). `timeline.py`는 대응표 쪽 시각을 날짜만 써서(`seal_time_missing` 2건) mtime 비교를 근거로 삼았다. [추정] 수준이다.
- **판정 후 감사 T**: 경로 2 출력(17:27:24)이 경로 1 실행 시작(17:27:38)보다 앞선다(prelaunch 10.2·10.3, mtime).
- 종료 코드: 경로 2 종료 0·묶음 COMPLETE, 경로 1 종료 0·묶음 COMPLETE(prelaunch 10.2·10.3 메인 세션 기록).

### 4.7 독립성 공개

- 경로 2 작성자는 control-expert이고, 경로 1(python-expert) 코드·출력을 보지 않았다. 실행 전 감사가 경로 2 작성자 transcript `agent-ac0313cdb25a6845c.jsonl`의 도구 호출을 검색했다: 경로 1 파일(`b1_creep_metrics.py`, `b1_harness_constants*.json`, 경로 1 worktree)을 Read·Grep한 기록 0건. rev1은 2·4·5절(30~87행, 97~115행)만 읽었고, 0·1·7절의 경로 1 상수 요약은 읽지 않았다.
- **메인 세션이 경로 2에 알린 것**(실행 전 감사 [T·독립성] 기록 그대로 공개)
  - [추정] 02:40Z handback의 "알려 주신 Q-1 Ŵ 문제"라는 말로 보아, 경로 2가 상수를 계산하기 전에 메인 세션이 $\hat W$ 문제(경로 1 결과 요약에서 나온 사실)를 알렸을 수 있다. 같은 사실은 rev1 0절(경로 1 상수 결과 요약을 보고 개정)에 공개돼 있다.
  - 02:18Z에 메인 세션이 경로 2 코드의 색인 방식을 짚어 고치게 했다(스키마 사실 전달).
- 경로 1 작성자 transcript `agent-a54833748c3f6b37d.jsonl`에서 경로 2 파일은 prelaunch 해시 표를 Write할 때만 나왔다(내용 Read 없음).
- K-R 대응표는 경로 2 작성자에게 넘기지 않은 문서다(대응표 머리). 경로 1 명령은 경로 2 출력을 입력으로 받지 않는다(prelaunch 10.3).
- 이 판정서 작성자(control-expert)는 두 경로가 모두 실행된 뒤 두 출력과 K-R 결과를 읽었다. 등급·수치는 출력에서 옮겼고, 판정서 작성자 확인 계산은 2.5 해석 메모(가드 값 읽기)와 차·합 산술(2.2 $Z_{ch} - Z^{corr}_{ch}$, 2.7 $g + \delta^{grid}$)뿐이다.

### 4.8 실행 전 감사·재감사 기록 항목과 처리

| 감사 | 항목 | 처리 |
|---|---|---|
| 실행 전 [실행 전 수정][R] | 경로 1 D-h 키 꼴(항상 K-NA) | 경로 1 `1ac4849`로 고침, 결과 전(4.6) |
| 실행 전 [실행 전 수정][R] | 경로 2 정체성·pad_nodes·E-5 누락 | 경로 2 `24a108e`로 고침(사용자 결정 확인 2), 결과 전 |
| 실행 전 [실행 전 수정][R] | 경로 2 D-b가 SGS 행 하네스 $\delta^{os}$를 넣음 | 경로 2에서 뺌, 결과 전 |
| 실행 전 [실행 전 수정][R·E] | K-R 대조 도구·대응표 없음 | 대응표 `d0f30e15…`(13:10), 제외 X-01~X-04(사용자 결정 확인 1), 대조는 감사 즉석 스크립트(`tools/verif` 후보 `kr_compare`) |
| 실행 전 [기록][I] | 하네스·G-S 커밋 `7246c19` ≠ 실행 `bd64cc4` | 차이는 `06_analysis/02_control/b1/` 10파일뿐(1.6, 5절) |
| 실행 전 [기록][T] | 처리 순서 3.0과 실제 순서 다름 | 4.6 |
| 실행 전 [기록][S] | 하네스 출력 폴더 `06_analysis/03_hydraulic/coupled/v5/b1/`에 `-text` 보호 없음(`b1_H.jsonl` CRLF 32줄, 원시 sha 인용) | 미처리. 커밋 전에 `.gitattributes`에 `06_analysis/03_hydraulic/coupled/v5/b1/** -text`를 넣어야 인용 sha가 유지된다(6절) |
| 실행 전 [기록][E] | E-5·I-12 로그 관문이 사실상 빔 | prelaunch 10.1을 Traceback 정의로 고침(재감사 수정 1) |
| 실행 전 [기록][I] | I-8 출처 필드 이름(`params_file` 없음) | postrun이 `meta.pad_variant.pad_variants_params_file_sha256` = YAML `ef2880f9…` 6/6로 확인 |
| 실행 전 [기록][E] | 경로 1 V-1 FAULT 판별 미사용 | 경로 1 `1ac4849`에서 `phases` 마지막으로 바꿈. SGS 3행 모두 VALID(4.4) |
| 실행 전 [기록][R] | 작은 정의 차이 (1)~(5) | 4.4. (4) D-h 순위는 20/20 같아 섞일 일이 없었음. (5) 경로 2 sha 대조는 `24a108e`에서 넣음 |
| 실행 전 [기록][T·독립성] | transcript 검색, 메인 세션 전달 2건 | 4.7 |
| 실행 전 [기록][I] | G-S 폴더 전체 출력 남음 | 1.6(사용자 결정 확인 3) |
| 재감사 [실행 전 수정] | E-5 정의, prelaunch 10.2 `--identity`, U-01~U-12 | 앞 둘 결과 전 prelaunch 수정, U-01~U-12는 결정 덧붙임 1 |
| 재감사 [기록] | K-93·K-108·D-d 하한·D-c 계산 행·D-f READY 판별, pad_nodes 필드 수, I-11 None 통과, V-1 FAULT 판별, $Z_{k^\ast}$ null | 4.2·4.4·4.5. I-11: C6 result.json에 두 경로가 읽는 키가 모두 있어 두 경로 모두 확인했다 |

## 5. 정체성·실행 조건

| 항목 | 값 | 근거 |
|---|---|---|
| 실행 HEAD(`HEAD_M`) | `bd64cc405990101ca8f3398ba2b9db9edcfc01b4`, 시작·끝 같음, 추적 변경 0(I-1·I-10) | 러너 status.txt, `batch.json` `code_at_launch.git` 6/6 `clean` |
| 하네스 커밋 | `7246c19a1aec6cfe9a6ba3b2f571a789fcf38912`(시작·끝 같음, 깨끗함). `bd64cc4`와 `03_src`·`04_scripts` 차이 0 | prelaunch 2·4절 |
| 태그 | Chrono 6행 `--expect-controller final_C4G2_P3_LAS_K1`, `controller_check` 참 6/6, `expect_controller.name` 같음(I-3). 하네스 VB `final_C4G2_P3_LAS_K1` / V0 `final_C4G2_LAS_K1` 32/32(I-9) | `batch.json`, result.json `c2_setup`, prelaunch 4절 |
| 프리셋 | `C2Config().with_10hz_d1()` 그대로, 래퍼 없음. I-17 `bd64cc4` 대 `e67dae8`: 공통 409필드 같음, 새 6필드(`touch_creep_latch.*`) 클래스 기본값, 위반 0 | prelaunch 6절 |
| 스레드 | `--threads 4`, `num_threads_chrono` 4 6/6(I-4) | result.json |
| OMP | `OMP_WAIT_POLICY=PASSIVE` 6/6(I-5) | `batch.json` `omp_wait_policy`, result.json `placement` |
| 풀 | P코어 6/6(`pool` = `planned_pool` = `pcore`), 4병렬, 배치표 sha256 `3d3b0117…`(I-6). 예약 b1-chrono-main 마스크 0x0000FFFF. result.json `placement` affinity 논리 CPU 0~15, `power_throttling_off_ok` 참. 실행 중 affinity 변경 기록 없음 | `batch.json`, prelaunch 2절, result.json |
| 볼록 껍질 훅 | requested = effective = `fast` 6/6, 출처 `default`, `fallback_reason` 없음, `MIXED_HULL_MODE` 없음(`mixed_hull_mode` false), DLL sha256 `cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15`(I-7, 이 판정서를 쓸 때 DLL 파일 다시 해시해 같음) | result.json `hull_hook`, `batch.json` |
| 셸 env | `OUTRIGGER_HULL_HOOK`·`_ALLOW_UNVALIDATED`·`_DLL`·`OUTRIGGER_LOC_SHADOW` 제거(I-14), 인터프리터 Chrono-dev `python.exe -I -X utf8 -u`, 러너 pwsh WMI 분리 실행 | prelaunch 8·9절 |
| YAML(I-8) | `02_params/rexome33.yaml` sha256 `ef2880f9…` 6/6 | postrun |
| argv(I-2·I-15) | 6/6이 실행 전 감사 기대 `argv_level_sha256`와 같음(C1 `af7d176e`, C2 `80c074e4`, C3 `1dfd69db`, C4 `4f3506e1`, C5 `8e0c4c8f`, C6 `c6f2ee1b`), rc 6/6 0 | postrun, `batch.json` |
| 공통 조건 | `--soil J2 --pad-variant dwg_rear250 --fs-kN 4 --grid 0.01 --crawler-grid 0.04 --settle-dashpot zrp --threads 4 --pressure-grade normal --imu-grade ideal --seed 20261026 --start-limit record_only --b1-grid-record full` + `v5_vb_argv()` 옵션. C6만 `--mass-scale 1.1 --duration 180` | `batch.json` `cases[].argv` |
| 격자 기록 | `full`(실행 전체 10 Hz), 켬·끔 `step_series.npz` 비트 동일, 벽시계 비 0.996·0.993(T-10 통과) | prelaunch 8절 |
| 정체성 입력 | `B1_identity.json` sha256 `2a4a4662…`(6행 ok 참, `runner_log` 0/0) | postrun |

도구·규칙 sha256

| 도구 | sha256 | 커밋·위치 |
|---|---|---|
| 경로 1 `b1_creep_metrics.py`(판정에 쓴 판) | `6b6e04acfd0cfb77e53b35981984bd4a9e4ccad2b4ce5446b6e5e7c018dda9d9` | `b1-path1-fix` `1ac4849`(worktree) |
| 경로 1 상수 계산에 쓴 판 | `a9518c65aeb791ce55e83a8d94bbb063fe0b8b5046d0ef5c4b030efa924853dd` | master `bd64cc4`. judge가 jsonl로 상수를 다시 계산해 파일과 대조(종료 0) |
| 경로 2 `path2/b1_path2.py` | `7a9d258fa3182506a82fbdca74c15a1b8a37bd7858cf413f959fe0f4f52183db` | `b1-path2-fix` `24a108e`(worktree) |
| 경로 2 keymap `path2/b1_keymap.json` | `19021bc6…` | 변경 없음 |
| I-17 `b1_preset_dump_diff.py` | `2acb3755…` | master |
| 행 모듈 `b1_creep_chrono_rows.py` | `5a243a1a…`(LF `4e1b214a…`) | master |
| cad 기록 `b1_grid_record.py` | `198cf3bb…` | master |
| 하네스 `b1_harness.py` / `b1_record.py` | `565b2317…` / `9344e00f…` | master |
| `c2.py` | `f58ee42b…`(`batch.json` `code_at_launch` 6/6 같음) | master |
| `run_S9.py` / `s9_batch.py` / `hull_hook.py` | `9a0575aa…` / `34b21a78…` / `afef13ec…` | master |
| 원판 / rev1 | `6b99702c…` / `9f72af5b…`(경로 1 `rules_files_check` 둘 다 `match`, 경로 2 `rules_sha256`·`rules_rev1_sha256` 같음) | 봉인 커밋 `1ad3e5d` / `417ce28` |

### 5.1 벽시계와 C3 (사실)

| 행 | 시작 → 끝 | 벽시계 [s] | `n_steps` | µs/스텝 | 끝 단계 | FAULT·SGS |
|---|---|---|---|---|---|---|
| C1 | 12:51:34 → 15:12:13 | 8,438 | 1,680,000 | 5,018 | ready | 없음 |
| C2 | 12:51:34 → 15:17:47 | 8,772 | 1,680,000 | 5,217 | ready | 없음 |
| C4 | 12:51:35 → 15:10:50 | 8,356 | 1,680,000 | 4,969 | fault | SGS 50.5 s |
| C5 | 12:51:35 → 15:19:53 | 8,898 | 1,680,000 | 5,292 | fault | SGS 50.2 s |
| C6 | 15:10:51 → 17:15:50 | 7,499 | 1,880,000 | 3,984 | fault | SGS 52.0 s |
| C3 | 15:12:13 → 17:03:02 | 6,649 | 1,680,000 | 3,955 | ready | 없음 |

- **C3가 짧은 이유는 일찍 끝나서가 아니다.** C3 result.json에는 FAULT·SGS·`WARN_LIFT_STROKE_LIMITED` 사건이 없고, 단계는 `ready`(149.0 s)로 끝났으며, `n_steps` 1,680,000으로 다른 160 s 행과 같은 시간을 다 적분했다($n_{end}$ 1680). 사건은 `INFO_LIFT_PAUSED:FR`(34.7 s) 1건, LOC 1회(46.0 s, 취소 0), 첫 READY 116.2 s 뒤 118.8 s 재레벨, 두 번째 READY 149.0 s다.
- 다른 점은 스텝당 비용이다: C3 3,955 µs/스텝, 같은 두 번째 물결의 C6 3,984 µs/스텝, 첫 물결 4행 4,969~5,292 µs/스텝. `progress.log`로 보면 C3·C6이 돈 시간의 대부분(15:19:53~)은 동시 실행이 2행이었고, 첫 물결은 4행이었다. [추정] 동시 실행 수가 줄어 스텝당 비용이 낮아진 것이 벽시계 차의 원인이다(스레드 수는 6행 모두 4로 같아 결과 비트 조건은 같다).

## 6. 가정과 남은 일

- 가정(원판·rev1에 있는 것 그대로, 이 판정서가 더한 것 없음): $Z_{soil}$ 후보(TR-8), $W_{fit}$ = 1,000 N, $n_a$ = 0.2, 문턱 3 / 5 / 10 / 20 / +5 mm, $\varepsilon_{th}$ = 1×10⁻⁹ m, M-11 유효성 범위 [0.95, 1.05]·법칙 잔차 0.005, 하네스 $f \equiv 1$(R-10, 하네스 32/32 연속 Bekker 확인), 압력 `normal`·IMU `ideal`.
- 커밋 전에 남은 일(메인 세션)
  - 판정 후 감사의 나머지(S·I, `tools/verif/judgement_checklist.py`)와 integrity-checker.
  - `.gitattributes`에 `06_analysis/03_hydraulic/coupled/v5/b1/** -text`(4.8).
  - 경로 1·2 worktree 브랜치(`b1-path1-fix` `1ac4849`, `b1-path2-fix` `24a108e`) 병합(4.6).
  - `B1_prelaunch` 사본을 `06_analysis/02_control/b1/prelaunch/`에 커밋할지(원판 11절).
- 원판 11절 결과물 형식 차이: prelaunch는 `B1_prelaunch.json`이 아니라 `06_analysis/02_control/b1/b1_creep_prelaunch.md`이고, 배치 폴더 정체성 입력은 `B1_identity.json`이다. 사본은 `06_analysis/02_control/b1/prelaunch/`에 `B1_identity.json`(sha 2a4a4662 유지)·`batch.json`·`progress.log`로 커밋한다. 상수 파일은 `b1_harness_constants_rev1.json`이다(옛 `b1_harness_constants.json` 0dd09ad0은 보관).
- 하네스 npz 32개는 `.gitignore`(*.npz)로 커밋하지 않는다(사용자 결정 2026-11-13). V-4 "npz sha = 줄 기록" 재검사는 이 PC에서만 된다.
  - Q6 질문(1.5).

### 6.1 기호

| 기호 | 정의 | 단위 |
|---|---|---|
| $b$, $b^\ast$ | 계획 예산 다리(원판 2.1 표), 판독 최대가 나온 실제 예산 다리 | — |
| $n_{L,1}$, $n_L$, $n_R$, $n_{\max}$, $n_{sgs}$ | 첫 LOC, 마지막 LOC, 첫 READY, 판독 최대 첫 주기, SGS 첫 주기(정수 주기, × 0.1 s) | — |
| $s(t_L)$, $s_{\max}$ | $t_L$의 판독 행정, 판독 행정 최대 | mm |
| $g$ | $s_{guard} - s_{b^\ast,\max}$, $s_{guard}$ = 682.8 mm | mm |
| $\Delta z^{post}$ | $z(t_e) - z(t_L)$, $t_e = \max(t_{\max}, t_R)$($t_R$ 없으면 $t_{\max}$) | mm |
| $Z_{ch}$, $Z^{corr}_{ch}$, $Z_{hn}$ | $\mathcal R$(C1~C5)의 $b^\ast$ $\Delta z^{post}$ 최대(원시, 격자 보정 $z/f$), 같은 다리 하네스 H-P VB·V0 e0 최대 | mm |
| $\delta^{os}$, $O$ | $s_{\max} - s(t_R)$, D-b 최대 | mm |
| $\Delta_r$, $\Delta^{corr}_r$ | Chrono − 하네스 VB e0 $s_{\max}$($b^\ast$), $\Delta_r - \delta^{grid}_r$ | mm |
| $f$, $\delta^{grid}$, $\delta z_{1n}$ | 격자 인자(원판 0.4), $z(1 - 1/f)$, 절점 하나 계단 $z\Delta^2/(nA)$ | —, mm, mm |
| $r_\sigma$ | 격자 기록 법칙 잔차(T-7 (ii), 문턱 0.005) | — |
| $e(q)$, $E_q$ | $s_{\max} - \hat s^{(q)}$(+ = 예측 부족), $\mathcal R$ 위 $\lvert e\rvert$ 최대 | mm |
| $g^{corr}$, $\tilde g$ | $g + \delta^{grid}$, $\min(g,\ g^{corr} - z(t_{\max})(1 - 1/f_{\max}))$(기록 무효면 $g - z(t_{\max})(f_{\max} - f_{\min})$) | mm |
| $\hat W_i$, $\hat E_i$ | rev1 R1-1 재분배 하중 추정 $r_i\sum_j F_j(n_L) - F_i(n_L)$, 끝 하중 추정 | N |
| $m_L$ | $c^\ast_{run}(t_L) - c^\ast$, $c^\ast$ = 50 mm | m |
| $\varepsilon_{th}$ | 문턱 비교 허용 1×10⁻⁹ m(값 대조 허용과 별개) | m |

## 부록. 판정 뒤 사용자 결정 (2026-11-13, 메인 세션 기록)

- Q6(D-f FUP-OUT): J2 fup(앞들림) 경사는 B1에서 빼고 운용 권고(시작 조건 축소 등)로 분리한다. 권고값은 뒤에 분석한다.
- B1 진행(제안 2): 새 예측 형식 재등록에 착수한다. 이 판정 결과를 본 뒤의 개정이므로 개정판 첫머리에 그 사실을 적고, 검증은 이번 6행과 다른 새 Chrono 행(다른 경사·오거 단계)으로 한다(제안 2 문장). 436.8은 계획대로 함께 진행한다.
- 제안 3(C3 probe 단계 가드 초과): 명세·코드 읽기 확인을 진행한다(Chrono 없음).
- 제안 4(K-77): 다음 개정 문장 후보로 둔다(4.3).
