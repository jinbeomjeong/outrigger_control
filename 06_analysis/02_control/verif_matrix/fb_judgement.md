# FB 표적 판정서 (초안, fb_judge.py 생성)

- 규칙: `fb_targeted_rules.md`(sha256 `e517b0d08bc4…`) + 덧붙임 판 `fb_targeted_rules_rev1.md`(sha256 `0163b6c3f065…`) + `fb_targeted_rules_rev2.md`(sha256 `12ed20ea215f…`) + `fb_targeted_rules_rev3.md`(sha256 `99cea69a8719…`), 후보 LF 대 L
- H-1 봉인 확인(판정 시작 때 `fb_targeted.sealed_check` 통과)
  - `fb_targeted_rules.md` 실측 sha256 `e517b0d08bc46100bb20ec3824de5066cdb8890715f03f3e9a1299437e5dcb89`
  - `fb_targeted_rules_rev1.md` 실측 sha256 `0163b6c3f065bd18320c6857c605186112f411ff7c20e02f403bf82a26ba9d63`
  - `fb_targeted_rules_rev2.md` 실측 sha256 `12ed20ea215fab24b475bc0b05b36fa01afe50aa4ad300b5af1ede441bcaaba0`
  - `fb_targeted_rules_rev3.md` 실측 sha256 `99cea69a8719ef738b81c96ae311762a36e73ffecf5884345d6a0ecbd6b9c356`
  - `fb_design.md` 실측 sha256 `2b95fefb84b20ff370d9c121519d9015b5b885e8708c64208e09b8e9cdb5bbe1`
- 실행 줄: `C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\fb` F-0 4/4, F-1 92/92, F-2 192/192, F-3 32/32, F-4 28/28, F-5 12/12
- F-2의 L: 저장 `v5/las/las_T1.jsonl`·`las_T2.jsonl` b0 act 줄
- 두 경로 판정(python-expert 도구, control-expert 재집계)이 같아야 확정이다(규칙 8절).

## 사전 관찰(rev3 R3-3)

> **사전 관찰(공개)**: rev2 봉인(2026-11-08 19:00:42) 전에 scratch에서 F-0 4줄(L·LF-off × K1 VB e0·K3 V0 e0, 커밋 `5468c67`, `scratchpad\fbfix\f0\fb_F0.jsonl`)을 돌렸다. S-1·C-7 결과(해시 `aff9b0f10ac5`·`fc2ca22f2850`, 저장 b0 act와 같음)를 rev2 작성 전에 봤다. rev2 머리말의 "실행 줄 0줄"은 저장소 기준이었고, 이 4줄을 빠뜨렸다. 이 줄들은 예산 꺼짐 경로라 LF 결과는 포함하지 않는다. S-1 기준 해시는 저장 값에서 정해졌다. 판정에는 저장소 `v5/fb/fb_F0.jsonl`(rev3 도구로 다시 돈 줄)만 쓴다.

> **사전 관찰(공개, rev3 봉인 뒤)**: rev3 봉인(19:31:35) 뒤 rev3 도구 확인으로 scratch에서 F-0 4줄을 다시 돌렸다(`scratchpad\fbfix\f0_rev3\fb_F0.jsonl`, 커밋 `b6a8a82`, 19:42, L·LF-off만이라 LF 결과는 없다). 해시는 rev2 R2-1 표와 같았다. 판정에는 쓰지 않는다.

## LAS-b 구현

> **LAS-b 구현(원판 3.1 대체, rev2 R2-1)**
> ① 이 판정의 모든 새 실행(F-0 L·LF-off, F-1·F-3·F-4의 L·LF, F-2 LF, F-5 OL-L·OL-LF)은 LAS-b를 03_src 프리셋 구현(`C2Config.with_10hz_d1().liftoff_approach_slow`, P-S8-39, 병합 `bacb2d2`, 이후 `334d544` 포함)으로 돌렸다. 원판 3.1의 `las_targeted.install` b0 래퍼는 설치하지 않았다. 실행 코드는 각 줄 `fb.identity`의 커밋 `2ee35c99d1d3`과 도구 sha256이다. 새 L 줄의 제어기 태그는 `final_C4G2_P3_LAS`(VB)·`final_C4G2_LAS`(V0)다. 저장 F-2 L 줄의 태그는 `final_C4G2_P3`·`final_C4G2`(래퍼)다. 짝은 키로만 맞추고 태그로 거르지 않았다.
> ② 이 대체는 원판 3.1에 따른 것이다. 원판 7절의 사후 변경 공개 대상이 아니다. 대체 전에 S-1을 확인했다. F-0 두 키의 03_src L 해시는 K1 VB `aff9b0f1…`와 K3 V0 `fc2ca22f…`였고, 둘 다 저장 b0 act 해시와 같았다. C-7(LF-off = L 2/2)은 통과했다.
> ③ F-2의 L은 원판 3.2대로 저장 `v5/las/las_T1.jsonl`·`las_T2.jsonl`의 b0 act 줄이다. 이 줄은 03_src에 LAS-b가 들어가기 전의 코드에 b0 래퍼를 얹어 만든 것이다. 줄에는 커밋 필드가 없다. 파일 시각 15:28·15:51과 git 기록으로 보면 `655844a`(15:09) 뒤, `11d28c6`(17:37) 앞이다. 따라서 F-2의 LF − L 짝에는 FB의 효과와 함께 "03_src LAS-b ↔ 래퍼 b0" 구현 차이가 들어갈 수 있다. 이 차이가 0이라는 근거는 다음과 같다. 첫째, 비트 시험 B-1~B-3(`11d28c6`)이다. B-2는 T-1 8키 = 래퍼, B-3은 T-2 작동 12키 = 래퍼, 미작동 10키 = 기준이다. 둘째, `334d544` 뒤 재확인 3키(K3 V0 e0, K3 VB e0, K1 VB e0)다. 셋째, 위 ②의 S-1이다. 그래서 F-2 192키 가운데 해시로 같음을 직접 보인 것은 T-1 8키와 T-2 22키, 합 30키다. 나머지 162키는 구현 동등성 가정이다(한계).

## 판정: **미달**

| # | 항목 | 결과 | 요약 |
|---|---|---|---|
| C-1 | eta 0.85 포화 제거 | 만족 | VB eta 0.85 LF 134줄, 최대 0.0 s, 초과 0 |
| C-2 | 판정 | 위반 | 짝 268, 위반 3, 사건 절단 짝 0 |
| C-3 | 계열 최소 힘 | 위반 | 8/8키, 최소 8.758 kN |
| C-4 | READY | 위반 | 같은 사건 집합 170짝, 중앙값 1.0 s, 최대 8.0 s, 집합이 다른 짝 96 |
| C-5 | eta 0.80 | 만족 | 14/14줄, 위반 0 |
| C-6 | eta 0.70 | 만족 | 4/4줄, 위반 0 |
| C-7 | 스위치 | 만족 | 일치 |
| C-8 | 행정 | 만족 | D-1 짝 212, 최대 증가 0.893 mm |
| C-9 | 거짓 검출 | 만족 | V0·VB eta 0.85 LF 250줄, 깎기 0 |
| C-10 | 열린 루프 상당 | 만족 | VB 3/3, 위반 0 |

## 실행 정체성

| 묶음 | 줄 | 커밋 |
|---|---|---|
| F-0 | 4 | `2ee35c99d1d3` |
| F-1 | 92 | `2ee35c99d1d3` |
| F-2 | 192 | `2ee35c99d1d3` |
| F-3 | 32 | `2ee35c99d1d3` |
| F-4 | 28 | `2ee35c99d1d3` |
| F-5 | 12 | `2ee35c99d1d3` |

- 묶음 사이 커밋 같음

- F-0: 줄 4, 커밋 ['2ee35c99d1d3cb950cf85b15d53cdf559b07625a'], 도구 해시 묶음 1, dirty 줄 0, 정체성 없는 줄 0, R3-1 이전 도구 줄 0
- F-1: 줄 92, 커밋 ['2ee35c99d1d3cb950cf85b15d53cdf559b07625a'], 도구 해시 묶음 1, dirty 줄 92, 정체성 없는 줄 0, R3-1 이전 도구 줄 0
- F-2: 줄 192, 커밋 ['2ee35c99d1d3cb950cf85b15d53cdf559b07625a'], 도구 해시 묶음 1, dirty 줄 192, 정체성 없는 줄 0, R3-1 이전 도구 줄 0
- F-3: 줄 32, 커밋 ['2ee35c99d1d3cb950cf85b15d53cdf559b07625a'], 도구 해시 묶음 1, dirty 줄 32, 정체성 없는 줄 0, R3-1 이전 도구 줄 0
- F-4: 줄 28, 커밋 ['2ee35c99d1d3cb950cf85b15d53cdf559b07625a'], 도구 해시 묶음 1, dirty 줄 28, 정체성 없는 줄 0, R3-1 이전 도구 줄 0
- F-5: 줄 12, 커밋 ['2ee35c99d1d3cb950cf85b15d53cdf559b07625a'], 도구 해시 묶음 1, dirty 줄 12, 정체성 없는 줄 0, R3-1 이전 도구 줄 0
- F-2 L = 저장 `las_T1`·`las_T2` b0 act 줄 192개(예외: 이 도구의 실행이 아니어서 커밋 검사에서 뺌, LAS-b 래퍼 시기 줄)

### 반환 명령 절단 스위치

- `clip_returned_command`는 R8 프리셋 기본 켬(`c2.py:2496`, 클래스 기본 꺼짐)이다. 실행 줄에는 이 값이 없고 `controller_tag`만 있다. 그래서 줄의 `controller_tag`가 기대 태그(C4G2 포함)인지로 절단 켬 가정을 확인한다.
- 기대 태그 줄 360, 그 밖 0(절단 켬 가정의 근거)
- 묶음별 커밋·도구 해시 하나씩

## 멈춤 조건

- H-2 (F-0 C-7): 통과
- S-1 (rev2 R2-1, H-2와 같이 처리): 통과
-   S-1 D1|H-R-A|rigid+J1@FR|T|diag-op|K1|VB|e0: L aff9b0f10ac5 저장 b0 aff9b0f10ac5
-   S-1 D1|H-R-A|rigid+J1@FR|T|diag-op|K3|V0|e0: L fc2ca22f2850 저장 b0 fc2ca22f2850
- H-3: 오류 줄 없음
- H-4 F-1: C-2 위반 짝 0(문장 0)
- H-4 F-2: C-2 위반 짝 2(문장 2)
- H-4 F-3: C-2 위반 짝 1(문장 1)
- H-4 F-4: C-2 위반 짝 0(문장 0)

## 예산 축척 s(rev2 R2-3, rev3 R3-1 정정, 기록)

- R3-1 정정: 예산 유량은 반환 명령 기준 Q(c(u))(c = ±v_max 절단, `clip_returned_command` 켬)이고, 축척 s* = max{s ≤ 1 : Q(c(s u)) ≤ Q_b}를 절단 전 벡터에 곱한다. 모든 |u_i| ≤ v_max이거나 절단이 꺼진 주기는 원판 식 그대로다.
- 명령이 바뀐 실행(예산 작용 + 절단 다리 주기가 있는 LF·OL-LF 줄): 31
- 명령이 바뀐 실행 수는 R3-5 정의 기준(예산 작용 + 절단 다리 주기)이며, rev3:41의 둘째 경우(옛 식은 작용하고 새 식은 작용하지 않는 주기)는 줄에 기록이 없어 세지 않았다.
- s = s_eff = Q(c(s* u))/Q(c(u)), s_vec = s*. s_nom = Q_nom/Q(4 v_max): 실행 계산값 0.8768421(차 +2.1e-06), rev2 표기 0.876840(규칙 1.1의 57.1902 L/min 기준; YAML로는 57.1900 L/min). 하한 = 0.5 s_nom, 결함 후보 판정은 실행 계산값 기준, 허용 1e-06

### 1. LF·OL-LF 실행의 단계별 최소 s_eff(묶음별)

- F-1 level: 실행 33, s_eff 최소 0.740862 · 중앙 0.876931 · 최대 0.895948; 작용 주기 최소 29.000000 · 중앙 33.000000 · 최대 51.000000
- F-1 touch: 실행 46, s_eff 최소 0.714736 · 중앙 0.876842 · 최대 0.876842; 작용 주기 최소 165.000000 · 중앙 165.000000 · 최대 207.000000
- F-2 level: 실행 48, s_eff 최소 0.908737 · 중앙 0.915477 · 최대 0.927080; 작용 주기 최소 4.000000 · 중앙 9.000000 · 최대 13.000000
- F-2 touch: 실행 192, s_eff 최소 0.876842 · 중앙 0.876842 · 최대 0.876842; 작용 주기 최소 165.000000 · 중앙 165.000000 · 최대 165.000000
- F-3 level: 실행 13, s_eff 최소 0.885746 · 중앙 0.910486 · 최대 0.973680; 작용 주기 최소 4.000000 · 중앙 17.000000 · 최대 31.000000
- F-3 touch: 실행 16, s_eff 최소 0.876842 · 중앙 0.876842 · 최대 0.876842; 작용 주기 최소 165.000000 · 중앙 165.000000 · 최대 165.000000
- F-4 level: 실행 10, s_eff 최소 0.885746 · 중앙 0.909908 · 최대 0.910799; 작용 주기 최소 11.000000 · 중앙 12.000000 · 최대 31.000000
- F-4 touch: 실행 14, s_eff 최소 0.876842 · 중앙 0.876842 · 최대 0.876842; 작용 주기 최소 165.000000 · 중앙 165.000000 · 최대 165.000000
- F-5 level: 실행 6, s_eff 최소 0.876842 · 중앙 0.876842 · 최대 0.876842; 작용 주기 최소 77.000000 · 중앙 77.000000 · 최대 77.000000
- F-5 touch: 실행 6, s_eff 최소 0.876842 · 중앙 0.876842 · 최대 0.876842; 작용 주기 최소 165.000000 · 중앙 165.000000 · 최대 165.000000

#### s_vec(참고)

- F-1 level: 실행 33, s_vec 최소 0.740862 · 중앙 0.837095 · 최대 0.877163; 작용 주기 최소 29.000000 · 중앙 33.000000 · 최대 51.000000
- F-1 touch: 실행 46, s_vec 최소 0.714736 · 중앙 0.876842 · 최대 0.876842; 작용 주기 최소 165.000000 · 중앙 165.000000 · 최대 207.000000
- F-2 level: 실행 48, s_vec 최소 0.908737 · 중앙 0.915477 · 최대 0.927080; 작용 주기 최소 4.000000 · 중앙 9.000000 · 최대 13.000000
- F-2 touch: 실행 192, s_vec 최소 0.876842 · 중앙 0.876842 · 최대 0.876842; 작용 주기 최소 165.000000 · 중앙 165.000000 · 최대 165.000000
- F-3 level: 실행 13, s_vec 최소 0.865154 · 중앙 0.910486 · 최대 0.973680; 작용 주기 최소 4.000000 · 중앙 17.000000 · 최대 31.000000
- F-3 touch: 실행 16, s_vec 최소 0.876842 · 중앙 0.876842 · 최대 0.876842; 작용 주기 최소 165.000000 · 중앙 165.000000 · 최대 165.000000
- F-4 level: 실행 10, s_vec 최소 0.885650 · 중앙 0.909908 · 최대 0.910799; 작용 주기 최소 11.000000 · 중앙 12.000000 · 최대 31.000000
- F-4 touch: 실행 14, s_vec 최소 0.876842 · 중앙 0.876842 · 최대 0.876842; 작용 주기 최소 165.000000 · 중앙 165.000000 · 최대 165.000000
- F-5 level: 실행 6, s_vec 최소 0.876842 · 중앙 0.876842 · 최대 0.876842; 작용 주기 최소 77.000000 · 중앙 77.000000 · 최대 77.000000
- F-5 touch: 실행 6, s_vec 최소 0.876842 · 중앙 0.876842 · 최대 0.876842; 작용 주기 최소 165.000000 · 중앙 165.000000 · 최대 165.000000

### 2. 검출로 예산을 깎은 실행

- F-1 S2|VB|eta0.8|e0: 깎기 2(A97@1.9s, A97@2.1s), 최종 Q_b 46.72 L/min, 최소 s_eff 0.8168420874636056, 최소 s_vec 0.791410
- F-1 S2|VB|eta0.8|e0.002: 깎기 2(A97@1.9s, A97@2.1s), 최종 Q_b 46.62 L/min, 최소 s_eff 0.8152084032615882, 최소 s_vec 0.788494
- F-1 S2|VB|eta0.8|e0.003: 깎기 2(A97@1.9s, A97@2.1s), 최종 Q_b 46.58 L/min, 최소 s_eff 0.8143915611605742, 최소 s_vec 0.788229
- F-1 S2|VB|eta0.8|e0.001: 깎기 2(A97@1.9s, A97@2.1s), 최종 Q_b 46.67 L/min, 최소 s_eff 0.8160252453626003, 최소 s_vec 0.788630
- F-1 S3|VB|eta0.8|e0: 깎기 2(A97@1.9s, A97@2.1s), 최종 Q_b 46.72 L/min, 최소 s_eff 0.8168420874636056, 최소 s_vec 0.816842
- F-1 S3|VB|eta0.8|e0.002: 깎기 2(A97@1.9s, A97@2.1s), 최종 Q_b 46.62 L/min, 최소 s_eff 0.8152084032615882, 최소 s_vec 0.815208
- F-1 R3|VB|eta0.8|e0: 깎기 2(A97@1.9s, A97@2.1s), 최종 Q_b 46.72 L/min, 최소 s_eff 0.8168420874636056, 최소 s_vec 0.816842
- F-1 R3|VB|eta0.8|e0.001: 깎기 2(A97@1.9s, A97@2.1s), 최종 Q_b 46.67 L/min, 최소 s_eff 0.8160252453626003, 최소 s_vec 0.816025
- F-1 R3|VB|eta0.8|e0.002: 깎기 2(A97@1.9s, A97@2.1s), 최종 Q_b 46.62 L/min, 최소 s_eff 0.8152084032615882, 최소 s_vec 0.815208
- F-1 R3|VB|eta0.8|e0.003: 깎기 2(A97@1.9s, A97@2.1s), 최종 Q_b 46.58 L/min, 최소 s_eff 0.8143915611605742, 최소 s_vec 0.814392
- F-1 S5|VB|eta0.8|e0: 깎기 2(A97@1.9s, A97@2.1s), 최종 Q_b 46.72 L/min, 최소 s_eff 0.8168420874636056, 최소 s_vec 0.792853
- F-1 S5|VB|eta0.8|e0.001: 깎기 2(A97@1.9s, A97@2.1s), 최종 Q_b 46.67 L/min, 최소 s_eff 0.8160252453626003, 최소 s_vec 0.792617
- F-1 S5|VB|eta0.8|e0.002: 깎기 2(A97@1.9s, A97@2.1s), 최종 Q_b 46.62 L/min, 최소 s_eff 0.8152084032615882, 최소 s_vec 0.792342
- F-1 S5|VB|eta0.8|e0.003: 깎기 2(A97@1.9s, A97@2.1s), 최종 Q_b 46.58 L/min, 최소 s_eff 0.8143915611605742, 최소 s_vec 0.792164
- F-1 S2|VB|eta0.7|e0: 깎기 4(U@1.7s, A97@1.7s, U@1.9s, A97@1.9s), 최종 Q_b 40.88 L/min, 최소 s_eff 0.7147360987521185, 최소 s_vec 0.714736
- F-1 R3|VB|eta0.7|e0: 깎기 4(U@1.7s, A97@1.7s, U@1.9s, A97@1.9s), 최종 Q_b 40.88 L/min, 최소 s_eff 0.7147360987521185, 최소 s_vec 0.714736
- F-1 S3|VB|eta0.7|e0: 깎기 4(U@1.7s, A97@1.7s, U@1.9s, A97@1.9s), 최종 Q_b 40.88 L/min, 최소 s_eff 0.7147360987521185, 최소 s_vec 0.714736
- F-1 S5|VB|eta0.7|e0: 깎기 4(U@1.7s, A97@1.7s, U@1.9s, A97@1.9s), 최종 Q_b 40.88 L/min, 최소 s_eff 0.7147360987521185, 최소 s_vec 0.714736

### 3. 구현 결함 후보(rev3 R3-1 정의)

- 없음

### 절단 다리 주기가 있는 실행(R3-1, 결함 후보 아님, `INFO_DIFF_SINK_*` 함께)

- F-1 LF S2|VB|eta0.85|e0: 절단 주기 {'level': 11}, s_vec 0.837918, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S2|VB|eta0.85|e0.001: 절단 주기 {'level': 11}, s_vec 0.836708, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S2|VB|eta0.85|e0.002: 절단 주기 {'level': 12}, s_vec 0.832263, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S2|VB|eta0.85|e0.003: 절단 주기 {'level': 11}, s_vec 0.837961, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S2|VB|eta0.8|e0: 절단 주기 {'level': 11}, s_vec 0.791410, s_eff 0.8168420874636056, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S2|VB|eta0.8|e0.002: 절단 주기 {'level': 12}, s_vec 0.788494, s_eff 0.8152084032615882, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S2|VB|eta0.8|e0.003: 절단 주기 {'level': 12}, s_vec 0.788229, s_eff 0.8143915611605742, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S2|VB|eta0.8|e0.001: 절단 주기 {'level': 13}, s_vec 0.788630, s_eff 0.8160252453626003, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S5|VB|eta0.85|e0: 절단 주기 {'level': 13}, s_vec 0.855279, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S5|VB|eta0.8|e0: 절단 주기 {'level': 18}, s_vec 0.792853, s_eff 0.8168420874636056, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S5|VB|eta0.85|e0.001: 절단 주기 {'level': 10}, s_vec 0.855324, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S5|VB|eta0.8|e0.001: 절단 주기 {'level': 18}, s_vec 0.792617, s_eff 0.8160252453626003, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S5|VB|eta0.85|e0.002: 절단 주기 {'level': 10}, s_vec 0.854416, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S5|VB|eta0.8|e0.002: 절단 주기 {'level': 18}, s_vec 0.792342, s_eff 0.8152084032615882, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S5|VB|eta0.85|e0.003: 절단 주기 {'level': 13}, s_vec 0.855293, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S5|VB|eta0.8|e0.003: 절단 주기 {'level': 18}, s_vec 0.792164, s_eff 0.8143915611605742, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S2|VB|eta0.7|e0: 절단 주기 {'level': 2}, s_vec 0.714736, s_eff 0.7147360987521185, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S2|V0|etadef|e0: 절단 주기 {'level': 11}, s_vec 0.838340, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S2|V0|etadef|e0.001: 절단 주기 {'level': 11}, s_vec 0.837095, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S2|V0|etadef|e0.002: 절단 주기 {'level': 12}, s_vec 0.832670, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S2|V0|etadef|e0.003: 절단 주기 {'level': 11}, s_vec 0.838386, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S5|VB|eta0.7|e0: 절단 주기 {'level': 24}, s_vec 0.714736, s_eff 0.7147360987521185, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S5|V0|etadef|e0: 절단 주기 {'level': 13}, s_vec 0.855447, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S5|V0|etadef|e0.001: 절단 주기 {'level': 10}, s_vec 0.855502, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S5|V0|etadef|e0.002: 절단 주기 {'level': 10}, s_vec 0.854584, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-1 LF S5|V0|etadef|e0.003: 절단 주기 {'level': 13}, s_vec 0.855460, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-3 LF D1|H-S-0|J1|T|flat|K1|VB|e0: 절단 주기 {'level': 10}, s_vec 0.876842, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-3 LF D1|H-S-0|J2|T|flat|K1|VB|e0: 절단 주기 {'level': 11}, s_vec 0.865154, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-3 LF D1|H-S-0|J1|T|flat|K1|V0|e0: 절단 주기 {'level': 10}, s_vec 0.876842, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-4 LF D1|H-S-C|J1|T|flat|K1|c-mid@FL|VB|e0: 절단 주기 {'level': 10}, s_vec 0.876842, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']
- F-4 LF D1|H-S-C|J1|T|flat|K1|c-mid@RL|VB|e0: 절단 주기 {'level': 10}, s_vec 0.876842, s_eff 0.8768421006980677, 사건 ['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE']

### 4. LEVEL s_eff와 선형 여유 표 범위 [0.438420, 1]

- LEVEL 최소 s_eff 0.740862(79실행): 선형 여유 표 범위 안, LEVEL 절단 주기가 있어 표 대조에서 뺀 실행 31(기록만)

## 항목별 상세

### C-1 eta 0.85 포화 제거
- (상세 없음)

### C-2 판정
- F-2 D1|H-R-A|rigid+J1@FR|T|diag-op|K3|VB|e0.002: (a) pass -> fail ['D8_F_after_liftoff', 'G6-3_Fmin']
- F-2 D1|H-R-A|rigid+J1@FR|T|diag-op|K3|V0|e0.002: (a) pass -> fail ['D8_F_after_liftoff', 'G6-3_Fmin']
- F-3 D1|H-R-A-S1|rigid+S1@FL|T|flat|K1|VB|e0: (a) new G6-2_loc failure

### C-3 계열 최소 힘
- D1|H-R-A|rigid+J1@FR|T|diag-op|K3|VB|e0.002: 8.758 kN
- D1|H-R-A|rigid+J1@FR|T|diag-op|K3|V0|e0.002: 9.048 kN

### C-4 READY
- F-1 S5|V0|etadef|e0.001: dt +7.9 s
- F-1 S5|V0|etadef|e0.002: dt +8.0 s
- 집합 다름으로 빠진 짝 F-1: 27
- 집합 다름으로 빠진 짝 F-2: 58
- 집합 다름으로 빠진 짝 F-3: 7
- 집합 다름으로 빠진 짝 F-4: 4
- 집합 다름(READY 판정 제외) F-1 S2|VB|eta0.85|e0: dt +3.5 s, 사건 차 +[] -['INFO_FLOOR_NONPLANAR']
- 집합 다름(READY 판정 제외) F-1 S2|VB|eta0.85|e0.001: dt +3.6 s, 사건 차 +[] -['INFO_FLOOR_NONPLANAR']
- 집합 다름(READY 판정 제외) F-1 S2|VB|eta0.85|e0.002: dt +3.5 s, 사건 차 +[] -['INFO_FLOOR_NONPLANAR']
- 집합 다름(READY 판정 제외) F-1 S2|VB|eta0.85|e0.003: dt +3.6 s, 사건 차 +[] -['INFO_FLOOR_NONPLANAR']
- 집합 다름(READY 판정 제외) F-1 S2|VB|eta0.8|e0: dt +3.9 s, 사건 차 +['INFO_FLOW_BUDGET_CUT', 'INFO_TOUCH_TWIST_HOLD'] -['INFO_FLOOR_NONPLANAR']
- 집합 다름(READY 판정 제외) F-1 S2|VB|eta0.8|e0.002: dt +3.9 s, 사건 차 +['INFO_FLOW_BUDGET_CUT'] -['INFO_FLOOR_NONPLANAR']
- 집합 다름(READY 판정 제외) F-1 S2|VB|eta0.8|e0.003: dt +3.8 s, 사건 차 +['INFO_FLOW_BUDGET_CUT'] -['INFO_FLOOR_NONPLANAR']
- 집합 다름(READY 판정 제외) F-1 S2|VB|eta0.8|e0.001: dt +3.8 s, 사건 차 +['INFO_FLOW_BUDGET_CUT'] -['INFO_FLOOR_NONPLANAR']
- 집합 다름(READY 판정 제외) F-1 S3|VB|eta0.8|e0: dt +3.8 s, 사건 차 +['INFO_FLOW_BUDGET_CUT'] -['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE', 'INFO_FLOOR_NONPLANAR']
- 집합 다름(READY 판정 제외) F-1 S3|VB|eta0.8|e0.002: dt +3.7 s, 사건 차 +['INFO_FLOW_BUDGET_CUT'] -['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE', 'INFO_FLOOR_NONPLANAR']
- 집합 다름(READY 판정 제외) F-1 R3|VB|eta0.8|e0: dt +0.5 s, 사건 차 +['INFO_FLOW_BUDGET_CUT'] -[]
- 집합 다름(READY 판정 제외) F-1 R3|VB|eta0.8|e0.001: dt +0.5 s, 사건 차 +['INFO_FLOW_BUDGET_CUT'] -[]
- 집합 다름(READY 판정 제외) F-1 R3|VB|eta0.8|e0.002: dt +0.6 s, 사건 차 +['INFO_FLOW_BUDGET_CUT'] -[]
- 집합 다름(READY 판정 제외) F-1 R3|VB|eta0.8|e0.003: dt +0.5 s, 사건 차 +['INFO_FLOW_BUDGET_CUT'] -[]
- 집합 다름(READY 판정 제외) F-1 S5|VB|eta0.85|e0: dt +1.3 s, 사건 차 +[] -['INFO_LOC_REVOKED']
- 집합 다름(READY 판정 제외) F-1 S5|VB|eta0.8|e0: dt -13.8 s, 사건 차 +['INFO_FLOW_BUDGET_CUT'] -['INFO_FLOOR_NONPLANAR', 'INFO_LOC_REVOKED']
- 집합 다름(READY 판정 제외) F-1 S5|VB|eta0.8|e0.001: dt -13.8 s, 사건 차 +['INFO_FLOW_BUDGET_CUT'] -['INFO_FLOOR_NONPLANAR', 'INFO_LOC_REVOKED']
- 집합 다름(READY 판정 제외) F-1 S5|VB|eta0.8|e0.002: dt -13.6 s, 사건 차 +['INFO_FLOW_BUDGET_CUT'] -['INFO_FLOOR_NONPLANAR', 'INFO_LOC_REVOKED', 'INFO_TOUCH_TWIST_HOLD']
- 집합 다름(READY 판정 제외) F-1 S5|VB|eta0.85|e0.003: dt +1.4 s, 사건 차 +[] -['INFO_LOC_REVOKED']
- 집합 다름(READY 판정 제외) F-1 S5|VB|eta0.8|e0.003: dt -13.5 s, 사건 차 +['INFO_FLOW_BUDGET_CUT'] -['INFO_FLOOR_NONPLANAR', 'INFO_LOC_REVOKED']
- 집합 다름(READY 판정 제외) F-1 S2|VB|eta0.7|e0: dt +1.5 s, 사건 차 +['INFO_FLOW_BUDGET_CUT'] -['INFO_FLOOR_NONPLANAR']
- 집합 다름(READY 판정 제외) F-1 R3|VB|eta0.7|e0: dt +0.4 s, 사건 차 +['INFO_FLOW_BUDGET_CUT'] -[]
- 집합 다름(READY 판정 제외) F-1 S3|VB|eta0.7|e0: dt +2.5 s, 사건 차 +['INFO_FLOW_BUDGET_CUT'] -['INFO_DIFF_SINK_HOLD', 'INFO_DIFF_SINK_RELEASE', 'INFO_FLOOR_NONPLANAR']
- 집합 다름(READY 판정 제외) F-1 S5|VB|eta0.7|e0: dt -11.9 s, 사건 차 +['INFO_FLOW_BUDGET_CUT'] -['INFO_FLOOR_NONPLANAR']
- 집합 다름(READY 판정 제외) F-1 R3|V0|etadef|e0.002: dt +2.1 s, 사건 차 +['INFO_TOUCH_TWIST_HOLD'] -[]
- 집합 다름(READY 판정 제외) F-1 S5|V0|etadef|e0: dt +3.1 s, 사건 차 +[] -['INFO_LOC_REVOKED']
- 집합 다름(READY 판정 제외) F-1 S5|V0|etadef|e0.003: dt +3.1 s, 사건 차 +[] -['INFO_LOC_REVOKED']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|diag-op|K3|VB|e0.002: dt +0.7 s, 사건 차 +['INFO_TOUCH_DIP_HELD'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|roll-op|K1|VB|e0: dt +0.3 s, 사건 차 +[] -['INFO_LIFT_PAUSED']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|roll+op|K1|VB|e0.002: dt +0.3 s, 사건 차 +[] -['INFO_LIFT_PAUSED']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|roll-op|K1|VB|e0.002: dt +0.4 s, 사건 차 +[] -['INFO_LIFT_PAUSED']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|diag-val|K3|VB|e0: dt +0.2 s, 사건 차 +[] -['INFO_TOUCH_DIP_HELD']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|roll+val|K1|VB|e0.002: dt +0.2 s, 사건 차 +[] -['INFO_LIFT_PAUSED', 'INFO_TOUCH_DIP_HELD']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|roll-val|K1|VB|e0.002: dt +0.1 s, 사건 차 +[] -['INFO_LIFT_PAUSED', 'INFO_TOUCH_DIP_HELD']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|T|flat|K1|VB|e0: dt +0.4 s, 사건 차 +['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|T|fdown-psa|K1|VB|e0: dt +0.8 s, 사건 차 +['INFO_TOUCH_TWIST_HOLD'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|T|fdown-psa|K1|VB|e0.002: dt +0.3 s, 사건 차 +[] -['INFO_TOUCH_TWIST_HOLD']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@RL|T|flat|K1|VB|e0.002: dt +3.2 s, 사건 차 +['INFO_TOUCH_TWIST_HOLD'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@RL|T|fup-psa|K1|VB|e0: dt -0.8 s, 사건 차 +[] -['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@RL|T|fup-psa|K1|VB|e0.002: dt +1.2 s, 사건 차 +['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|M|flat|K1|VB|e0: dt +1.2 s, 사건 차 +['INFO_TOUCH_TWIST_HOLD'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|M|flat|K3|VB|e0: dt +0.4 s, 사건 차 +['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|M|flat|K3|VB|e0.002: dt +0.5 s, 사건 차 +['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@RL|M|flat|K1|VB|e0: dt +3.6 s, 사건 차 +['INFO_TOUCH_TWIST_HOLD'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@RL|M|roll-op|K1|VB|e0: dt +0.9 s, 사건 차 +['INFO_TOUCH_TWIST_HOLD'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@RL|M|roll-op|K3|VB|e0: dt +0.8 s, 사건 차 +['INFO_TOUCH_TWIST_HOLD'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|B|flat|K1|VB|e0: dt -0.1 s, 사건 차 +['INFO_LIFT_PAUSED'] -['INFO_TOUCH_TWIST_HOLD']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|B|flat|K3|VB|e0: dt +0.6 s, 사건 차 +[] -['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|B|flat|K1|VB|e0.002: dt +0.1 s, 사건 차 +['INFO_LIFT_PAUSED', 'INFO_TOUCH_DIP_HELD'] -['INFO_TOUCH_TWIST_HOLD']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@RL|B|flat|K1|VB|e0: dt +0.2 s, 사건 차 +[] -['INFO_TOUCH_TWIST_HOLD']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@RL|B|flat|K1|VB|e0.002: dt +0.6 s, 사건 차 +['INFO_TOUCH_DIP_HELD'] -['INFO_TOUCH_TWIST_HOLD']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@RL|B|roll-op|K3|VB|e0: dt +1.1 s, 사건 차 +['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|roll+op|K1|V0|e0: dt +2.5 s, 사건 차 +['INFO_LIFT_PAUSED', 'INFO_TOUCH_DIP_HELD'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|roll-op|K1|V0|e0: dt +2.4 s, 사건 차 +['INFO_LIFT_PAUSED', 'INFO_TOUCH_DIP_HELD'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|diag-op|K1|V0|e0.002: dt +2.0 s, 사건 차 +[] -['INFO_TOUCH_TWIST_HOLD']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|diag-op|K3|V0|e0.002: dt +2.2 s, 사건 차 +['INFO_TOUCH_DIP_HELD'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|roll+val|K3|V0|e0: dt +2.1 s, 사건 차 +['INFO_LIFT_PAUSED'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|roll+val|K1|V0|e0.002: dt +1.9 s, 사건 차 +['INFO_LIFT_PAUSED'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|roll-val|K1|V0|e0: dt +2.2 s, 사건 차 +['INFO_TOUCH_TWIST_HOLD'] -['INFO_LIFT_PAUSED']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|roll+val|K3|V0|e0.002: dt +2.0 s, 사건 차 +[] -['INFO_LIFT_PAUSED']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|roll-val|K3|V0|e0: dt +2.1 s, 사건 차 +['INFO_LIFT_PAUSED'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|roll-val|K1|V0|e0.002: dt +1.9 s, 사건 차 +['INFO_LIFT_PAUSED'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-0|rigid|T|diag-val|K3|V0|e0: dt +2.2 s, 사건 차 +['INFO_TOUCH_DIP_HELD'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|T|flat|K1|V0|e0: dt +2.2 s, 사건 차 +['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|T|flat|K1|V0|e0.002: dt +2.1 s, 사건 차 +['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|T|flat|K3|V0|e0.002: dt +2.2 s, 사건 차 +['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|T|fdown-psa|K3|V0|e0: dt +2.5 s, 사건 차 +['INFO_TOUCH_DIP_HELD'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|T|fdown-psa|K1|V0|e0.002: dt +1.9 s, 사건 차 +[] -['INFO_TOUCH_TWIST_HOLD']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|T|fdown-psa|K3|V0|e0.002: dt +2.0 s, 사건 차 +[] -['INFO_TOUCH_DIP_HELD']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@RL|T|flat|K1|V0|e0.002: dt +1.9 s, 사건 차 +[] -['INFO_TOUCH_TWIST_HOLD']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@RL|T|fup-psa|K1|V0|e0.002: dt +3.2 s, 사건 차 +['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@RL|T|roll-op|K1|V0|e0: dt +2.5 s, 사건 차 +['INFO_TOUCH_DIP_HELD', 'INFO_TOUCH_TWIST_HOLD'] -['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|M|flat|K1|V0|e0: dt +2.3 s, 사건 차 +['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@RL|T|roll-op|K1|V0|e0.002: dt +1.7 s, 사건 차 +[] -['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|M|flat|K3|V0|e0: dt +2.1 s, 사건 차 +['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|M|flat|K1|V0|e0.002: dt +1.6 s, 사건 차 +['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END'] -['INFO_TOUCH_TWIST_HOLD']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|M|flat|K3|V0|e0.002: dt +2.1 s, 사건 차 +['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@RL|M|roll-op|K1|V0|e0.002: dt +2.2 s, 사건 차 +['INFO_TOUCH_TWIST_HOLD'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|B|flat|K1|V0|e0: dt +1.8 s, 사건 차 +[] -['INFO_TOUCH_TWIST_HOLD']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FR|M|diag-op|K1|V0|e0.002: dt +2.1 s, 사건 차 +['INFO_TOUCH_DIP_HELD'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|B|flat|K1|V0|e0.002: dt +2.1 s, 사건 차 +['INFO_TOUCH_DIP_HELD'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@FL|B|fdown-psa|K1|V0|e0: dt +2.0 s, 사건 차 +['INFO_TOUCH_DIP_HELD'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@RL|B|flat|K1|V0|e0: dt +2.4 s, 사건 차 +['INFO_TOUCH_TWIST_HOLD'] -[]
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@RL|B|flat|K1|V0|e0.002: dt +1.9 s, 사건 차 +['INFO_TOUCH_DIP_HELD'] -['INFO_TOUCH_TWIST_HOLD']
- 집합 다름(READY 판정 제외) F-2 D1|H-R-A|rigid+J1@RL|B|roll-op|K3|V0|e0: dt +2.2 s, 사건 차 +['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END'] -[]
- 집합 다름(READY 판정 제외) F-3 D1|H-S-0|J1|T|diag-rec|K1|VB|e0: dt +0.5 s, 사건 차 +['INFO_TOUCH_TWIST_HOLD'] -[]
- 집합 다름(READY 판정 제외) F-3 D1|H-S-0|J2|T|flat|K1|VB|e0: dt -0.3 s, 사건 차 +[] -['INFO_FLOOR_NONPLANAR']
- 집합 다름(READY 판정 제외) F-3 D1|H-S-1|S1|T|flat|K1|VB|e0: dt +0.1 s, 사건 차 +[] -['INFO_TOUCH_DIP_HELD']
- 집합 다름(READY 판정 제외) F-3 D1|H-S-A|G1+J1@FL|T|flat|K1|VB|e0: dt +2.4 s, 사건 차 +['INFO_LIFTOFF_SLOW', 'INFO_LIFTOFF_SLOW_END'] -[]
- 집합 다름(READY 판정 제외) F-3 D1|H-S-A|G1+J1@RL|T|flat|K1|VB|e0: dt +1.0 s, 사건 차 +[] -['INFO_TOUCH_TWIST_HOLD']
- 집합 다름(READY 판정 제외) F-3 D1|H-S-A|G1+J1@FR|T|diag-psa-soil|K1|VB|e0: dt +0.6 s, 사건 차 +[] -['INFO_TOUCH_TWIST_HOLD']
- 집합 다름(READY 판정 제외) F-3 D1|H-R-A-S1|rigid+S1@FL|T|flat|K1|VB|e0: dt -10.6 s, 사건 차 +[] -['INFO_TWIST_UNSETTLED']
- 집합 다름(READY 판정 제외) F-4 R14|VB|etadef|e0|o0: dt -1.0 s, 사건 차 +[] -['INFO_TOUCH_DIP_HELD']
- 집합 다름(READY 판정 제외) F-4 R15|VB|etadef|e0|o0.05: dt -0.3 s, 사건 차 +['INFO_TOUCH_TWIST_HOLD'] -[]
- 집합 다름(READY 판정 제외) F-4 R2|V0|etadef|e0|reanchor_on: dt +2.5 s, 사건 차 +['INFO_TOUCH_DIP_HELD'] -['INFO_TOUCH_TWIST_HOLD']
- 집합 다름(READY 판정 제외) F-4 R15|V0|etadef|e0|o0.05: dt +2.0 s, 사건 차 +['INFO_TOUCH_TWIST_HOLD'] -[]

### C-5 eta 0.80
- (상세 없음)

### C-6 eta 0.70
- S2|VB|eta0.7|e0: 첫 깎기 {'t_s': 1.7, 'rule': 'U', 'budget_L_min': 40.87575756464466, 'delivered_L_min': 42.139956252210986} 첫 TOUCH 0.9999999999999453 지연 0.7000000000000547
- R3|VB|eta0.7|e0: 첫 깎기 {'t_s': 1.7, 'rule': 'U', 'budget_L_min': 40.87575756464466, 'delivered_L_min': 42.139956252210986} 첫 TOUCH 0.9999999999999453 지연 0.7000000000000547
- S3|VB|eta0.7|e0: 첫 깎기 {'t_s': 1.7, 'rule': 'U', 'budget_L_min': 40.87575756464466, 'delivered_L_min': 42.139956252210986} 첫 TOUCH 0.9999999999999453 지연 0.7000000000000547
- S5|VB|eta0.7|e0: 첫 깎기 {'t_s': 1.7, 'rule': 'U', 'budget_L_min': 40.87575756464466, 'delivered_L_min': 42.139956252210986} 첫 TOUCH 0.9999999999999453 지연 0.7000000000000547

### C-7 스위치
- D1|H-R-A|rigid+J1@FR|T|diag-op|K1|VB|e0: L aff9b0f10ac5 LF-off aff9b0f10ac5
- D1|H-R-A|rigid+J1@FR|T|diag-op|K1|VB|e0: stored b0 aff9b0f10ac5
- D1|H-R-A|rigid+J1@FR|T|diag-op|K3|V0|e0: L fc2ca22f2850 LF-off fc2ca22f2850

### C-8 행정
- (상세 없음)

### C-9 거짓 검출
- (상세 없음)

### C-10 열린 루프 상당
- D1|H-R-0|rigid|T|flat|K1|VB|e0: 행정 차 0.004 mm, 자세 0.006 deg (roll -0.001, pitch +0.005), V0 OL-L 0.005675732770490637
- D1|H-S-0|J1|T|flat|K1|VB|e0: 행정 차 0.003 mm, 자세 0.497 deg (roll -0.391, pitch -0.307), V0 OL-L 0.5022374429466518
- D1|H-S-0|J2|T|flat|K1|VB|e0: 행정 차 0.000 mm, 자세 0.473 deg (roll -0.373, pitch -0.291), V0 OL-L 0.5004783632446358

## 이 판정 도구가 정한 해석

- C-2 (a): `d1.verdict` pass → fail만 센다(allowed_stop은 참고 목록). P3-2·G6-2 새 실패 = L이 실패하지 않은 이름이 `P3-2`·`G6-2`로 시작하는 LF 실패 항목
- 사건 이름 = `event_names` 키(`:` 앞). 새 사건 = LF에만 있는 FAULT·WARN 접두 이름
- VB(eta 0.85) = 설정 VB이고 `eta_v`가 없거나 0.85
- C-6: 첫 깎기 시각 − 첫 TOUCH 주기(그 주기 끝 단계가 TOUCH) 시각 ∈ [0, 1.0] s
- C-10 자세 변화 크기 = hypot(roll 변화, pitch 변화), 축별 값은 상세에 둔다
- 위 해석은 rev1 2절 I-1~I-8로 확정
- F-4 verdict 1번 = `R2ra`(reanchor_on), rev1 1절
- A97 단계 조건의 `touch_seen`은 주기 k+1 update 끝 값(rev2 R2-2)
- H-4는 C-2 위반 문장이 하나 이상 있는 짝을 1건으로 센다(rev3 R3-2)
- R3-1 이전 도구의 줄(정체성 `budget_rule` 또는 meta `min_scale_eff` 없음)은 판정에 쓰지 않는다(rev3 R3-4)

## 기록 항목 (control-expert 추가, 판정 후 감사 반영, 2026-11-08)

### 두 번째 경로(규칙 8절): control-expert 독립 재집계 = 일치

- 스크립트: `06_analysis/02_control/verif_matrix/scripts/fb_recount.py`(sha256 `e927c7ba632af5d268263120bfb17d4685665cedacb734b4e4277fd92de91d3d`)
  - `fb_judge`·`fb_targeted`를 import하지 않는다. 규칙 4절과 rev1~rev3 정의로 직접 센다.
- 출력: `scripts/fb_recount_out.json`(sha256 `e6c33ae95e7e6fbe2b6126dcd16b116e20526b92a913a34b6f40306de99f1e74`)
  - scratchpad에서 돌린 실행의 출력을 복사했다. 다시 돌리면 출력은 스크립트와 같은 폴더에 쓰인다.
- 입력 sha256

  | 파일 | sha256 |
  |---|---|
  | `fb_F0.jsonl` | `2a246f80…` |
  | `fb_F1.jsonl` | `086afb19…` |
  | `fb_F2.jsonl` | `f81097f6…` |
  | `fb_F3.jsonl` | `76be00cf…` |
  | `fb_F4.jsonl` | `7e5716e6…` |
  | `fb_F5.jsonl` | `bcac6007…` |
  | `las/las_T1.jsonl` | `3dee4f6b…` |
  | `las/las_T2.jsonl` | `2fe6a54a…` |

- 결과: C-1~C-10의 만족·위반, 값, 위반 키가 도구 판정과 모두 같다. 미달이 확정된다.

### 원판 1.1 기준으로도 미달

- C-2·C-3 위반 짝 둘(F-2 K3 VB e0.002, K3 V0 e0.002)의 LF는 다음과 같다.
  - `clipped_budget_periods` = {}
  - `INFO_DIFF_SINK_*` 사건 없음
  - 예산은 TOUCH에서만 작용(165주기)
- 그래서 rev3 R3-1 비트 규칙에 따라 이 두 줄의 명령은 원판 1.1 정의와 같다. 원판 기준으로 판정해도 C-2·C-3 위반은 그대로다.

### 사전 관찰 공개 (rev3 머리말 누락분)

- rev3 봉인(19:31:35) 전에 F-6 열린 루프 결과를 봤다.
  - 파일: `v5/paper_runs/openloop_fb_compare.json`(19:21)
  - 커밋: `9299364`(19:31:02)
  - 판정서: `v5/v5_paper_runs_judgement.md` 1.7절
- rev3 머리말의 "본 실행 결과는 scratch F-0 4줄뿐"에서 이 관찰이 빠졌다.
- F-6은 채택 기준이 아니다(원판 4절). rev3의 변경(R3-1 반환 명령 기준, R3-2 H-4 짝 단위)은 F-6 값과 관계없는 정의 정정이다.

### rev2 인용

- R2-3 선형 여유: $s\in[0.438420,1]$(7점 격자)에서 M_s ≤ 1.3810, α ≥ 0.6856이고 폐루프는 안정이다.
  - Python ↔ Julia는 허용 일치다.
  - 실행 기준은 아니다(기록).
  - 이번 LEVEL 최소 $s_{eff}$ 0.740862는 이 범위 안이다. 다만 절단 주기가 있는 31줄은 표 대조에서 뺐다(rev3 R3-1).
- R2-4 F-6 사전 정보: dynamics-expert `prop_dip_*.json`(FB 없음)으로 0.877배를 외삽하면 후방 골이 약 8.8 kN으로 F_min 아래다. 원판의 기대 문장("후방 골이 F_min 위로")과 반대를 시사한다는 정보를 F-6 실행 전에 봤다.

### rev1 R2ra 변경 이유

- 원판의 F-4 `R2`(결정 없음)는 REANCHOR를 건너뛴다(`reanchor_skipped`).
- 원판의 뜻인 REANCHOR 경로 시험을 하려면 `R2ra`(reanchor_on)를 돌려야 한다. 저장 `v5/main.jsonl`에서 `R2ra`는 `reanchor_started`·`reanchor_completed`가 있다.
- 이 변경은 결과를 보기 전에 했다.

### 판정 도구 수정 `f644137`(20:24, F-5 결과 뒤)

- 바뀐 곳은 기록 항목뿐이다: 단계별 절단 제외, 절단 스위치 태그 확인, 공개 문구.
- 변경 hunk는 `PRIOR_OBSERVATION_NOTE`, `scale_defects`, `level_range_report`, `identity_problems`, `scale_text`, `render`, `judge`(1행)에 있다.
- C-1~C-10 판정 함수는 바뀌지 않았다. 독립 재집계 일치가 이를 뒷받침한다.

### 저장 F-2 L 줄의 제어기 태그

- 192줄(`las_T1`·`las_T2` b0 act): VB 96줄 `final_C4G2_P3`, V0 96줄은 태그 null(필드 값 없음)이다.
- 판정서 위쪽 R2-1 ① 문구의 "저장 F-2 L 줄의 태그는 `final_C4G2_P3`·`final_C4G2`"는 V0 쪽이 실제로는 null이다. 짝은 키로만 맞췄으므로 판정에는 영향이 없다.
