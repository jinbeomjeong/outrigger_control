# 판 5 봉인 직전 감사(verif-protocol-auditor, 2026-11-21) — hand-back 원문

## 감사 요약
- 본 결과: Grep 범위를 잘못 잡아 `j9_runs/78fd5d2d/dg3_a1/dg3_VBH.json`의 줄 몇 개가 화면에 나왔습니다. 설정 필드 `fallback_min_band_N` 값이고 판정 값은 아닙니다. 같은 실수로 `j9_runs/78fd5d2d/dg3_a1/step_record.json`의 판정 도구 argv 줄도 이름만 나왔습니다. judge 폴더와 판정 값은 열지 않았습니다.
- 대상: 436.9 J-P3 판 5 원고 `jp3_remedy_spec_v5.md`(봉인 전), 경로 2 발췌 `jp3_rev6_p2_handoff_ed5.md`(6dea0de7), 초안 `jp3_remedy_spec_v5_draft.md`(d4cbce84), `ed5_design/`, worktree `z4369-ed5`의 X-10 커밋 `5b216b4f`.
- 시점: 실행 전(봉인 직전). 기준 문서는 판 4a `jp3_remedy_spec.md`(8be9de22)와 덧붙임 4a-1~4a-8·정오입니다.
- 원고 sha: 감사 중에 메인이 6.3.3을 고쳐 f964a8ec에서 **0ec2ebd3**으로 바뀌었습니다. 아래 판단은 고친 원고를 다시 읽은 결과입니다(88·232~259·392·404행).
- 판정: **차단 7 / 경고 16 / 정보 9**. 이대로 봉인하면 판정 문장과 판정 집합이 두 가지로 읽히거나, 봉인 문서 안에 서로 다른 정의가 남습니다. 차단 7건을 고친 뒤 봉인할 것을 권합니다.

## 차단 — 봉인 전에 반드시 고칠 것

**B1 [R·E] 판정 문장 (1)의 다리 추출 규칙이 실제 사건 형식과 맞지 않아 새 FAULT를 놓칠 수 있습니다**
- 근거:
  - 원고 286행: "다리는 사건 이름의 끝 토큰이 FL·FR·RL·RR이면 그것이고, 아니면 '–'다". 같은 문장이 발췌 123행에도 있습니다.
  - 실제 사건 형식(worktree `03_src/outrigger_sim/control/c2.py`):
    - 1722~1727행: `FAULT_LIFT_STROKE_LIMIT:<legs>`, `FAULT_STROKE_END:<legs>`, `FAULT_LIFT_STROKE_LIMIT:soil:<legs>`
    - 3824~3826행 `_leg_names`: 다리 목록을 `"FL,RR"`처럼 쉼표로 잇습니다.
    - 8292행: `f"{LIFT_GUARD_FAULT_EVENT}:{legs}"`
  - 원고 10절 3항이 이 점을 아직 미해결로 둡니다.
- 실패 시나리오:
  - 두 다리 사건은 끝 토큰이 `FL,RR`이라 다리가 '–'가 됩니다. "이름"을 `:` 앞 부분으로 읽으면, VBK의 `FAULT_LIFT_STROKE_LIMIT:FR,RL`과 VBK0의 `FAULT_LIFT_STROKE_LIMIT:FL`이 같은 (이름, –)로 합쳐집니다. 새 다리의 FAULT를 놓쳐 거짓 통과가 납니다.
  - "이름"을 문자열 전체로 읽으면 다리 규칙이 아무 일도 하지 않습니다.
  - 어느 쪽인지 원고가 정하지 않았으므로 두 경로가 갈릴 수 있습니다.
- 제안 문장(6.3.7 (1)과 발췌 2.7 (1)을 같이 고침): "사건 문자열을 ':'로 나눈다. 첫 토큰이 이름이다. 나머지 토큰을 ','로 나눈 원소 가운데 FL·FR·RL·RR인 것이 다리 집합이고, 비면 {'–'}다. 사건마다 (이름, 다리) 쌍을 다리 수만큼 만든다. VBK 쌍 가운데 같은 짝 VBK0의 쌍 집합에 없는 것이 있으면 실패다. 대상은 결과 줄 사건 목록에서 이름이 `FAULT`로 시작하는 것이다."
- 출처 필드(`warn_fault` 또는 events)도 함께 정합니다(W13). 담당은 control(문장), python-expert(사건 형식 시험)입니다.

**B2 [R·E] VBK·VBK0 줄에 J-P3 판정이 걸리는지 정하지 않았습니다**
- 근거:
  - 6.1(194행): "J-P3: 0 건수, 판정 행 normal 등급 이하… rev 6은 비교값만 바꾼다".
  - A7(156행)과 9절(464행)은 "P4 끔 행은 J-P3 기록만"이라고만 적습니다.
  - 6.3 어디에도 VBK(rev 6, P4 켬, L2 normal) 줄의 J-P3 판정 여부가 없습니다.
  - X-10 커밋은 `JP3_LINE_SETTINGS`에 VBK0만 넣었고(`jp3_tjr_judge.py`), VBK는 TODO입니다(`run_v5.py`).
- 실패 시나리오: R5-9 감압 상계의 건전성이 시험되는 곳은 대체가 많은 VBK 줄입니다. 경로 1이 J-P3를 판정하고 경로 2는 기록으로 읽거나 그 반대가 되면 판정이 갈립니다. 둘 다 빼면 rev 6의 건전성 판정이 빈 채로 통과합니다.
- 제안 문장(6.3.7 끝에 추가): "VBK 줄의 J-P3(6.1)는 판정한다(판정 행 = VBK 기회 짝과 VBK0 READY 미도달 짝의 VBK 줄, 판정 행 0 = 판정 불가). VBK0 줄은 ③ 끔이라 J-P3 줄이 아니다." 기록으로 둘 생각이면 그 문장을 대신 넣습니다. 발췌 2.7에도 같은 문장을 넣습니다.

**B3 [E] '미래치'가 짝 하나의 제외인지 관문 전체의 판정 불가인지, 그리고 분류 우선순위가 정해지지 않았습니다**
- 근거:
  - 221행: "래치되지 않은 짝은 `setting_defect`(판정 불가)다".
  - 309~310행(6.3.9): 기회 분류 건수에 '미래치'를 다른 범주와 나란히 셉니다.
  - 266행(6.3.4): `setting_defect`는 "판정 불가로 두고 멈춘다".
  - 구현 `rod_fault_plan.py` 383~399행 `latch_record`는 첫 고장 읽기 **이후 아무 때나** 나온 사유 사건을 래치로 기록합니다. 사유도 D1로 한정하지 않습니다(`reads_after_first`, `reason`만 남김).
- 실패 시나리오: 트리거 전에 자연 대체가 있던 다리는 이미 대체 상태라 D1 래치 사건이 다시 나오지 않을 수 있습니다[추정]. 그러면 '트리거 전 대체' 짝이 '미래치'로도 분류됩니다. '미래치 = 멈춤'으로 읽으면 관문 전체가 판정 불가가 됩니다. 반대로 늦은 래치나 다른 사유를 '래치됨'으로 세면 기회 짝이 늘어납니다.
- 제안 문장(6.3.2): "래치 = 첫 고장 읽기와 같은 읽기에서 사유 D1 사건. 늦은 래치·다른 사유·없음은 미래치다. 미래치 짝이 하나라도 있으면 setting_defect로 판정 불가, 멈춤이다(단, 트리거 전 대체 짝은 먼저 '트리거 전 대체'로 분류하고 미래치로 세지 않는다). 분류 순서는 트리거 없음 → 트리거 전 대체 → 미래치 → VBK0 READY 미도달 → 기회다." 6.3.9의 범주 목록과 발췌 2.9도 이 순서로 맞춥니다.

**B4 [R] τ_C 정의를 고친 뒤 같은 원고 안에 옛 정의가 두 곳 남았고, 7.2 (ii)가 구현·규칙과 어긋납니다**
- 근거:
  - 242행(고친 뒤): "CHECK를 떠난 갱신(T4h phase 열의 첫 non-CHECK 행)은 10.1 s다… k0은 그다음 읽기 10.2 s다".
  - 88행 F9: "첫 non-CHECK **읽기**는 모두 10.1 s다".
  - 404행(7.2 고장 주입): "T0′는 **첫 non-CHECK 읽기**다".
  - 구현은 242행과 같습니다. `rod_fault_plan.py` 19~23·29~31행, `r79_sensor_screen.py` 492~501행에서 T4h `phase` 행 k는 갱신 k 뒤의 단계, 즉 읽기 k+1에 작용하는 단계입니다.
  - 392행 (ii): "무장하지 않는 계획(**빈 계획** 또는 실행 끝 뒤 시각)". 그런데 408행은 "계획 없는 VBK·VBK0은 거부"이고, 구현 `load_plan`(246~249행)도 빈 계획을 거부합니다("an empty plan is refused", 시험 `test_x10_rod_fault.py` 106·444·720행). 시험 (ii)는 `t:1000000` 계획을 씁니다(522행).
- 실패 시나리오: 봉인 문서 안에서 같은 단어 '첫 non-CHECK 읽기'가 10.1 s와 10.2 s 두 뜻이 됩니다. 단위 시험 판정과 경로 2가 어느 쪽을 따를지 갈립니다.
- 제안 문장:
  - 88행: "첫 non-CHECK **갱신**(T4h phase 행)은 모두 10.1 s다(작용 단계 기준 k0은 10.2 s)".
  - 404행: "T0′는 CHECK를 떠난 갱신 다음 읽기(작용 단계가 처음 CHECK가 아닌 읽기)다".
  - 392행: "무장하지 않는 계획(실행 끝 뒤 시각 `t:` 앵커; 빈 계획은 거부된다)".

**B5 [T] 10절 '봉인 전 확인' 1~3항이 미해결인 채 봉인 대상에 들어 있습니다**
- 근거(472~476행):
  - 1항: TRw 정의가 통계·유압 쪽과 같은 뜻인지
  - 2항: 새 FAULT 집합(control이 정함, "확인을 권한다")
  - 3항: 다리 토큰 규칙(B1)
- 참고: 설계 문서 `vbk_gate_definition_6_2a.md` 86행은 "VBK0 READY 미도달 짝도 새 FAULT 판정(사용자 결정)"을 적었습니다. 그러나 '트리거 없음·트리거 전 대체 짝의 새 FAULT는 기록'이라는 부분은 control의 결정이고, 사용자 결정 기록이 없습니다.
- 실패 시나리오: 봉인 뒤 이 항목의 답이 달라지면, 결과 전에 고정했어야 할 정의를 덧붙임으로 바꾸게 됩니다.
- 조치:
  - 세 항목을 해결합니다(1: stats·hydraulics 확인 기록, 2: 사용자 확인 또는 "control 결정"으로 명시, 3: B1 문장).
  - 10절을 "확인 결과" 표로 바꿉니다. 근거 경로와 sha를 적습니다.
  - 초안에 16절 메인 기록을 더합니다. 지금 초안에는 TRw·k_min·커버리지 키·τ_C 수정 결정의 기록이 없고 12절 번호도 빠졌습니다.

**B6 [I·T] 목격 보충(TRw) 블록의 seed와 계획이 결과 전에 정해지지 않습니다**
- 근거:
  - 278행: "같은 167사례와 **다음 미사용 seed**". 블록 32 추가 여부에 따라 32인지 33인지 달라집니다.
  - 297·299행 A/A: "seed 30 대 seed 31"로 숫자를 박았습니다. 214행의 +10 규칙이 적용되면 40·41이 됩니다.
  - 214행 +10 규칙은 "+10 뒤에도 충돌"할 때를 정하지 않았습니다.
  - X-11(356행) 목록에 TRw 블록의 계획·seed 생성이 없습니다. 구현에도 TRw 앵커가 없습니다(`AnchorKind` 89~93행).
- 실패 시나리오: 보충 블록의 seed가 VBK0 출력을 본 뒤 정해지는 구조가 됩니다. 두 경로나 재현자가 서로 다른 seed를 쓸 수 있습니다.
- 제안 문장(6.3.1):
  - "블록 b1 = seed_index 30, b2 = 31, N 보충 블록 b3 = 32, 목격 보충 블록 b4 = 33(b3 사용 여부와 무관하게 고정). 충돌이 있으면 넷 모두 +10을 충돌이 없어질 때까지 되풀이하고 반복 수를 기록한다."
  - "A/A는 b1 대 b2다."
  - "X-11은 b3·b4 계획 파일과 sha를 실행 전에 만든다."

**B7 [I] 커밋 전 정리가 필요합니다: 인용 파일 41개가 git에 없고 h8 사례 원본은 sha 앞자리만 인용됩니다**
- 근거:
  - `baseline_check sums` 네 목록: 해시 불일치 0, 없음 0. 대신 `cited_untracked`가 hyd 12, stats 15, stats_b 9, control_c 3건입니다.
  - `ref_check`: 원고·초안·발췌·`ed5_design` 모두 `ref_untracked`입니다. `git check-ignore`는 어느 것도 무시하지 않습니다(rc 1).
  - 210행 사례 원본 `h8_noise_VB.json`(sha `2219ab97…`)의 경로 `06_analysis/03_hydraulic/coupled/v5/resume_k1/h8_noise_VB.json`(42.8 MB)는 git 추적 밖입니다. 무시 규칙에도 걸리지 않습니다. 고정은 `prelaunch_j9/FIXED_INPUTS.SHA256SUMS` 한 줄뿐입니다.
- 조치:
  - 봉인 커밋에 원고, `.sha256`, 발췌, 초안, `ed5_design/**` 전체를 넣습니다. 커밋 직전에 `git status --ignored`를 확인합니다.
  - 210행을 "`06_analysis/03_hydraulic/coupled/v5/resume_k1/h8_noise_VB.json`, sha256 `2219ab9782b22fbe07e6c1f90e8b49c6b3703b0575b5d7cfb7d72b4f067bec43`(추적 밖, `prelaunch_j9/FIXED_INPUTS.SHA256SUMS`로 고정)"으로 고칩니다.
  - 차단으로 둔 이유: 이 상태로 커밋하면 봉인 근거가 다른 checkout에 없습니다.

## 경고 (실행 전 수정)

**W1 [I·R] 배열 이름과 행 기준을 적어야 합니다**
- 원고는 판독 `stroke_m`을 씁니다(236·250·276행). T4h 배열 이름은 `motor_stroke_m`입니다(`verdict_runs.py` 354~357행. `phase`·`command_m_s`도 같은 곳). `r79_sensor_screen` TruthLog의 `stroke_m`은 플랜트 참값(`plant.sref`, 440행)입니다.
- 제안: 6.3.3·6.3.6과 발췌 2.3·2.6에 "판독 `stroke_m` = T4h `motor_stroke_m`. T4h `phase` 행 k = 갱신 k 뒤 단계(읽기 k+1에 작용)"를 넣습니다.
- 6.6 X-2의 key_presence 목록에 넣을 것:
  - T4h 배열: `motor_stroke_m`, `command_m_s`, `phase`, `rod_fault_applied`
  - 줄 키: `rod_fault.*`

**W2 [I] 짝 동일성에 고장 계획 동일성이 빠졌습니다**
- 6.3.4에 "(다) 두 팔의 `rod_fault.plan_sha256`·`fault_id`·`leg`·`anchor`·`delay_reads`가 같다"를 넣습니다.
- 관문 계획은 `delay_reads` = 0으로 고정합니다(구현 333행에서 첫 고장 읽기에 더해지므로, 0이 아니면 "k+1부터"가 깨짐).

**W3 [E] 6.2 "판정 조건도 멈춤 조건도 아니다"(201행)가 다른 조항과 충돌합니다**
- 같은 줄에 P5-1(182행, 단계 (6) 포함 T8 멈춤)과 VBJ 줄 J-P3(6.1)가 걸립니다.
- 제안: "13.9절 지표와 지배 읽기 감소율은 판정·멈춤 조건이 아니다. 같은 줄의 P5-1과 VBJ 줄 J-P3(6.1)는 그대로 적용한다. VBH 줄은 A7에 따라 J-P3 기록이다."

**W4 [I] rev 6 태그 이름이 정해지지 않았습니다(이 프로젝트에서 따로 볼 것)**
- 근거:
  - 174행 "새 이름은 python-expert가 정하고".
  - 판별은 `v5_options.extend_start_revision_of_tag`가 base 태그를 `EXTEND_START_REVISION_OF_BASE_TAG`에서 찾는 방식입니다(`v5_options.py` 659~665행). 지금은 4·5만 있습니다.
- 제안(4.6): "rev 6 base 태그는 구현 커밋에서 정하고 실행 전 감사 기록에 고정한다. base→revision 대응에 6을 넣고, 접미사 없음·`_LAS`·`_K1`·`_LAS_K1` 네 꼴이 6으로 판별되며 4·5로 읽히지 않는 시험을 7.2에 넣는다. 판정 도구는 VBK 줄의 태그와 revision 기록 키가 6인지 본다."

**W5 [E] P5-3 "전부 통과"가 skip을 통과로 셀 수 있습니다**
- 비트 동일 시험 (i)은 `X10_BASE_ROOT`가 없으면 skip합니다(`test_x10_rod_fault.py` 69·595행). 하네스 시험은 `importorskip("numba")`입니다(519·727·739행).
- 제안: "skip·xfail은 미통과로 센다. junit을 남기고 `junit_skips.py --critical`로 확인한다."

**W6 [T] A/A 전에 VBK가 이미 실행되어 로그로 결과가 새어 나올 수 있습니다**
- 8절 4.(6).1(429행)은 "VBK0·VBK 실행 → A/A"입니다. 판정 도구가 VBK 파일을 열지 않아도, 러너 로그·`errors N`·FAULT 경고 줄은 메인·감시 에이전트가 볼 수 있습니다.
- 제안: "VBK0 블록을 먼저 돌려 A/A·N 보충·목격 보충을 결정한 뒤 VBK를 돌린다". 그렇게 하지 않으려면 "VBK 러너 로그는 블라인드 경로"로 정합니다.

**W7 [T] 공개 문구가 실제 쓴 자료보다 좁습니다**
- 51행 '본 결과'에 빠진 것:
  - stats·stats_b가 읽은 `h8_noise_VB/V0`, `h8_seedext_VB/V0`, `h6_dg3_v4on`, `h7_dg3_off`
  - hyd `h1b_retention`이 읽은 `dg3_VBH.json` 결과 줄
  - `m1`이 읽은 `dg3_VBJ0.json`
- 63행 O-3 "수치는 저장 L2 seed 간 분산과 시뮬레이션에서만 냈다"는 사실과 다릅니다. k 기대치는 저장 VBJ0 T4h의 목격 존재율에 기댑니다.
- 제안: "수치는 저장 L2 seed 간 분산, 저장 VBJ0 T4h의 트리거·목격 존재율(판정 값 아님), 시뮬레이션에서 냈다".

**W8 [T] 6.3.3·6.3.6의 수정된 수치에 해시된 출처가 없습니다**
- 원고의 TRw 존재율(256행), k 기대치·P(k<45)·TRw 한 블록 기대(277행)는 `ed5_design` SUMS 어느 파일에도 없습니다.
- 설계 문서는 옛 정의의 다른 수치를 씁니다(`vbk_gate_definition_6_2a.md` 107·114행, `hyd/m1_trigger_cover.py`는 기준 s[k−1]이고 u_n 조건이 없음).
- `control_c/` 두 스크립트는 print만 하고 출력을 남기지 않습니다.
- 조치: 수정 정의로 계산한 스크립트와 출력을 `ed5_design/<폴더>/SHA256SUMS`에 넣고 원고 표에 sha를 더합니다(stats·control).

**W9 [R] X-10이 봉인보다 먼저 구현·커밋되었습니다**
- 8절 1(419행)은 "봉인 → 구현"입니다. X-10은 `5b216b4f`(2026-11-21 23:16)로 봉인 전에 커밋되었습니다. 결과는 없으므로 오염은 아닙니다.
- 조치: 초안 16절에 사실대로 적고, 봉인 뒤 X-10을 봉인 문장과 다시 대조합니다(이 보고서의 R 표가 1차 대조).

**W10 [S] 판정 도구 blob 변경의 영향(메인 질문 답)**
- 판 4a 봉인 근거 `prelaunch_j9/FIXED_INPUTS*.SHA256SUMS`에는 `.py` 판정 도구가 없습니다. 들어 있는 것은 규칙·데이터·run_steps ps1뿐이라 `jp3_tjr_judge.py`·`j_p3_inputs.py` 변경은 그 목록에 영향을 주지 않습니다.
- `common.ps1`은 다릅니다. X-10이 바꿔 `840544bb…`가 `6394154f…`가 되었습니다. 이 파일은 `FIXED_INPUTS_78fd5d2d`·`_d3c6c57e` 55행에 고정되어 있습니다. 병합 뒤 작업 트리로 옛 목록을 검사하면 그 줄이 불일치합니다. 판 5에는 `FIXED_INPUTS_<판 5 실행 커밋>`을 새로 만들고, 4a 기록은 `git show <커밋>:경로`로 검사한다고 6.6이나 8절에 적습니다.
- `j_p3_inputs.py`는 Dg-3·L1 러너의 정적 import 폐포에 있습니다(`j4a_remedy_d3c6c57e/import_closure_78fd5d2d_d3c6c57e.json` 215·442행). 그래서 4a-8 6.1의 "고친 커밋 예외"는 쓸 수 없습니다. 판 5 8절은 전체 재실행이므로 실제 문제는 아닙니다.

**W11 [E] A/A의 결측·반올림 규칙**
- "두 줄이 다 있는 167쌍"이 167보다 적을 때를 정합니다(167쌍이 모두 있지 않으면 판정 불가로 멈춤).
- 30 s 비교도 (2)처럼 1×10⁻⁶ s로 반올림합니다.

**W12 [R] s_ref 첨자가 4.1과 6.3.3·6.3.6에서 다르게 읽힙니다**
- 4.1(119행)은 "운반 직전 읽기"이고, 6.3.3·6.3.6(250·276행)은 "트리거 읽기 k(=시작 읽기)"입니다. 옛 측정 `m1`은 s[k−1]을 썼습니다.
- 제안(4.1): "s_ref = 운반의 첫 출력 명령을 낸 갱신 k의 읽기 판독(그 명령은 읽기 k+1부터 작용)".
- 6.3.6의 "래치 뒤"가 래치 읽기를 포함하는지도 적습니다.

**W13 [R] FAULT 사건의 출처 필드와 접두사가 6.3.7에 없습니다**
- 설계 문서 51행은 `warn_fault`, 접두사 `FAULT`였습니다. B1 문장에 함께 넣습니다.

**W14 [R] 발췌와 원고의 뜻이 다른 곳**
- 발췌 1.5(58행)의 T8은 "대체가 없는 행"이라는 한쪽 조건입니다. 원고 P5-1은 "양쪽 실행 모두 대체 없음 + VBJ0·VB 행은 무조건"입니다. 원고 쪽으로 맞춥니다.
- 발췌 2.9(142행)의 "다리별 목록"은 원고 6.3.9에 없습니다. [바꿈] 표지도 없습니다.
- 발췌 2.3에 W1의 phase 행 기준이 없습니다. 경로 2가 τ_C를 10.1 s로 읽을 수 있습니다.
- 발췌 2.7 (1)은 B1, 2.2는 B3 문장으로 같이 고칩니다.
- 발췌 3행의 "봉인 sha256: 메인이 봉인 뒤 덧붙임"은 커밋 전에 채우고, 발췌 자신의 sha도 봉인 기록에 남깁니다.

**W15 [I] 가드가 문자열 접두사 하나로 판별합니다(python-expert)**
- 가드는 `startswith("VBK")`(`r79_sensor_screen.py` 1050·1061행)이고, 목록은 `run_v5.ROD_FAULT_SETTINGS = ("VBK0",)`입니다. 같은 사실의 출처가 둘입니다.
- `setting in ROD_FAULT_SETTINGS`(VBK 등록 뒤 포함)로 판별하거나, 접두사 판별과 목록이 같은지 보는 시험을 둡니다.

**W16 [R] 남은 X-10 구현과 원고 목록의 차이(구현 중이라 목록만)**
- TRw 앵커가 없습니다(`AnchorKind`에 3종 + `t`).
- 커버리지 세 키(`jp3_r58_witness_carries`, `jp3_r59_substeps`, `jp3_r510_candidates`)가 없습니다(rev 6 미구현).
- VBK 설정이 등록되지 않았습니다(`run_v5.py` TODO).
- 7.2 (라)·(마) TRw 이어받기 시험이 없습니다.
- `latch_record`가 D1과 즉시 래치를 강제하지 않습니다(B3).

## 정보

1. 머리말 sha 표 25개(판 4a, 덧붙임·정오 15개, 설계 문서 5개, SUMS 4개)는 모두 raw 바이트 해시와 같습니다. CRLF 0, BOM 0입니다. 덧붙임 `.sha256` 첫 토큰도 모두 같습니다.
2. 4a-1에는 `.sha256` 파일이 없습니다. 고정은 `FIXED_INPUTS.SHA256SUMS` 3행입니다.
3. 줄바꿈 보호: `.gitattributes`의 `06_analysis/02_control/j_p3_cause/** -text`가 새 `jp3_remedy_spec_v5.md(.sha256)`, 발췌, 초안, `ed5_design/**`에 모두 걸립니다(`check-attr` text: unset). worktree도 같습니다. `core.autocrlf=true`지만 보호됩니다.
4. `baseline_check sums` 네 목록: 항목 11·14·8·2개 모두 해시 일치입니다. hyd 폴더의 두 검토 md는 목록 밖이지만 원고 표가 따로 고정합니다(`sums_unlisted` 2).
5. `gate_scan` `rod_fault_plan.py`는 발견 0이고, `ps1_lint` worktree `common.ps1`도 0입니다.
6. 메인이 전한 구현 다섯 점은 원고와 맞습니다(k0 = CHECK 탈출 갱신 다음 읽기, 첫 고장 읽기 전 모든 갱신의 명령 sha, `delay_reads`, VBK0 추가, VBK 접두사). 판정 도구 대상 목록은 튜플 포함 비교라 단일 문자열 비교가 아닙니다. 접두사 판별은 W15입니다.
7. τ_R 구현(`_scan_retract_start` 362~372행)은 period_log 행 단계(갱신 뒤 단계)를 씁니다. 존재율 근거 `c2_triggers_b.py`의 T4h phase(같은 기준)와 맞습니다.
8. `ref_check`의 `ref_missing` 4건 가운데 3건은 이름만 적은 참조입니다(`x10_and_stats_b_summary.md`·`vbk_gate_definition_6_2a.md`는 `ed5_design/`에 있음, `rod_fault_plan.py`는 worktree에만 있음). `h8_noise_VB.json`은 B7입니다. 원고에 전체 경로를 적기를 권합니다.
9. 6.3.10의 ĉ ≥ 0.5일 때 (가)·(나) 선택은 c 건식 결과(판정 집합 밖 seed)를 본 뒤 정합니다. 판정서에 그 순서를 공개합니다.

## 규칙↔도구 대조표(X-10, `5b216b4f`)

| 원고 | 구현 | 판단 |
|---|---|---|
| 6.3.2 −100 bar STUCK, DROPOUT NaN (219·228) | `FaultKind`, `value_Pa` (82~86·121~126) | 같음 |
| 6.3.2 위치: 오차 모형·포화 뒤 (220) | `after_period`, `deliver` 뒤 `apply` (`r79_sensor_screen.py` 468~480) | 같음 |
| 6.3.2 첫 고장 읽기에서 D1 래치, 아니면 setting_defect (221) | `latch_record`가 이후 아무 때 + 사유 기록 (383~399) | 판정 도구에서 강제 필요(B3) |
| τ_C k0 = 작용 단계 첫 non-CHECK 읽기 (241~242) | `PHASE_EXIT_CHECK` (344~348) | 같음(10.2 s) |
| τ_R k, k+1 주입 (244~245) | `_scan_retract_start` (362~372) | 같음 |
| TRw 앵커 (248~257) | 없음 | 미구현 |
| (나) 첫 고장 읽기 전 모든 갱신 명령 sha (264) | `commands_sha256(log, read)` (374~377) | 같음 |
| 트리거 전 대체 (265) | `pre_trigger_fallback_events` (378~380) | 같음 |
| `rod_fault_sum_offset_N` (226) | `sum_offset_record` (401~412) | 같음 |
| 7.2 (ii) 빈 계획 (392) | 빈 계획 거부 (246~249) | 원고 수정(B4) |
| 계획 없는 VBK·VBK0 거부 (408) | 가드 종료 2 | 같음 |
| 계획 동일성 | `plan_sha256` 기록 | 원고 조항 없음(W2) |

## 확인 필요
1. VBK 줄의 J-P3를 판정으로 둘지 기록으로 둘지(B2) — 사용자 또는 control.
2. 트리거 없음·트리거 전 대체 짝의 새 FAULT를 기록으로만 둘지(10절 2항) — 사용자 결정 기록이 없습니다.
3. 미래치를 관문 전체 판정 불가로 둘지 짝 제외로 둘지(B3).

## 위임 필요
- control-expert: B1~B6, W1~W4, W6·W7·W11~W14 원고·발췌·초안 문장.
- stats-design-expert와 control: W8(수정 정의로 계산한 존재율·k 기대치 스크립트와 출력을 SUMS에 넣기).
- python-expert:
  - W15 가드 판별
  - W16 남은 구현
  - B1 사건 형식 시험(`NAME:FL,RR`, `NAME:soil:FR`)
  - B3 래치 판정
  - W4 rev 6 태그 대응과 시험
  - W5 junit 기록

## 메인 세션 권고
- 봉인 커밋 직전에 `git status --ignored -- 06_analysis/02_control/j_p3_cause`를 확인하고 `ed5_design/**`·원고·`.sha256`·발췌·초안을 함께 커밋합니다.
- 커밋 뒤 `seal_check.py --repo <저장소> 06_analysis/02_control/j_p3_cause/jp3_remedy_spec_v5.md --sums <각 SUMS> --rev <봉인 커밋> --check-tracked`와 `baseline_check sums --rev <봉인 커밋>`이 종료 0인지 봅니다. 지금은 커밋 전이라 돌릴 수 없어 돌리지 않았습니다.
- 원고를 고친 뒤 `handoff_leak.py`를 다시 돌립니다(발췌도 바뀌므로).

## 검사하지 못한 것
- `seal_check --sums --rev --check-tracked`: 봉인 커밋이 아직 없습니다.
- X-10 시험 실행(pytest·junit): 읽기 전용 원칙에 따라 돌리지 않았습니다. "65+793 통과"는 메인 전달 사실로만 둡니다.
- 원고 6.3.6 k 기대치의 재계산(출처 스크립트가 없음, W8).
- `hydraulics_review_ed5*.md`·`control_integration_ed5.md`·`x10_and_stats_b_summary.md` 본문 전체 대조. 원고 표의 sha 일치만 봤습니다.

## 실행한 검증
- 의존성 점검: STAMP(생략).
- python-dev(`-I -B`, `MKL_THREADING_LAYER=TBB`)로 돌린 것:
  - 즉석 스크립트 `hash_table.py`(머리말 sha 25개 raw·LF 대조, CRLF·BOM, `.sha256` 대조)
  - `baseline_check.py sums` ×4
  - `ref_check.py`(원고)
  - `gate_scan.py`(`rod_fault_plan.py`)
  - `ps1_lint.py`(worktree `common.ps1`)
  - `source_guard snapshot`·`verify`
- git 조회: `check-attr`, `status --ignored`, `check-ignore -v`, `ls-files --error-unmatch`·`--eol`, `worktree list`, `show 5b216b4f`, `log d3c6c57e`. `Get-FileHash`(`common.ps1` 두 판).
- 만든 뒤 지운 것: `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\bd7ff3b9-880c-4e9e-afd1-7024158f16f4\scratchpad\verif-ed5seal\`(`list_inputs.py`, `hash_table.py`, `guard.json`). 지운 뒤 없음을 확인했습니다.
- 메모리: `C:\Users\jinbeom\.claude\agent-memory\verif-protocol-auditor\audit_pitfalls.md`에 두 줄을 더했습니다(다리 토큰 규칙과 사건 형식, 설계 수치의 해시 출처).
- 감사 중 바뀐 파일:
  - 원고가 메인 수정으로 f964a8ec에서 0ec2ebd3으로 바뀌었습니다(6.3.3 τ_C 문장).
  - worktree의 X-10 변경이 감사 중에 `5b216b4f`로 커밋되었습니다.
  - 최종 판단은 다시 읽은 내용 기준입니다(88·232~259·392·404행 재확인).
- 원본 불변: 위반 — 원본 내용 변경 1건(jp3_remedy_spec_v5.md). 이 변경은 메인 세션이 감사 중에 고친 6.3.3이고, 감사 에이전트는 이 파일을 쓰지 않았습니다. 나머지 입력 77개와 폴더는 바뀌지 않았습니다(folder_status unchanged).
- 사용한 스킬: 없음

---

## 메인 기록(2026-11-21)
- 확인 필요 2(트리거 없음·트리거 전 대체 짝의 새 FAULT는 기록): 사용자가 메시지 박스에서 "그대로(Recommended)"로 확인했다(2026-11-21, 원고 저장 직후). 사용자 결정으로 기록한다.
- 확인 필요 1·3과 W6은 사용자에게 묻는다.
- 사용자 결정(2026-11-21, 메시지 박스): B2 VBK 줄 J-P3는 **판정함**. B3 미래치는 **하나라도 있으면 판정 불가·멈춤**(분류 순서: 트리거 없음 → 트리거 전 대체 → 미래치 → VBK0 READY 미도달 → 기회). W6 **VBK0 먼저, 그다음 VBK**.
