# 판 5 정오 1 실행 전 감사(verif-protocol-auditor, 2026-11-22) — hand-back 원문

## 감사 요약(판 5 정오 1, 실행 전)
**차단이 3건이라 이대로는 커밋할 수 없습니다.** 셋 다 정오 문장을 고치거나 시험 키를 바꾸면 됩니다.

- 대상:
  - `jp3_remedy_spec_v5_erratum1.md`(sha `fd6361d5`)
  - 경로 2 정오 `jp3_rev6_p2_handoff_ed5_e1.md`(sha `6906c1f0`)
  - 재검토 `ed5_design/control_review_impl_8a3c48c7.md`(sha `9ccffa30`)
  - `ed5_design/x4/`
- 원판 참조는 맞습니다. 원판 `fe6f5844`(`jp3_remedy_spec_v5.md.sha256`와 같음), 봉인 발췌 `3ce9ecd8`(파일 실측과 같음).
- 판정: 차단 3 / 경고 6.
- 본 결과: 판정 값은 보지 않았습니다. Grep은 `j9_runs` 밖에서만 했고, `j9_runs`는 최상위 폴더 이름만 봤습니다. 사례 원본 `h8_noise_VB.json`에서는 키 문자열만 Grep했습니다.

## 차단

**E-1 [T·I] 단위 시험과 탐침이 12b 판정 집합 b1의 키를 이미 돌렸습니다**
- 근거:
  - worktree `05_tests/unit/test_x10_rod_fault.py`:
    - 64행 `RUN_KEY = "cand=current#L2|s30|ref|0|rigid|B|0,0"`
    - 616행 `TRW_KEY = "cand=current#L2|s30|ref|3|rigid|B|0,3.2"`
    - 617~618행 docstring "probe run of this commit: carry start 373, witness 388"
    - 661~669행: 이 키들로 VBJ·VBJ0·VBK0(τ_R, τ_C)·VBK(무장 안 함)·VBK/VBK0(TRw)를 하네스로 실제 실행합니다.
  - 두 사례 모두 12b 사례 원본의 L2 사례입니다(`h8_noise_VB.json`에 `L2|s0..s4|ref|0|rigid|B|0,0`와 `…|ref|3|rigid|B|0,3.2`가 있음).
  - `s30`은 b1입니다(`test_jp3_12b_tools.py` 76·94행: b1 = seed_index 30 = 키 `s30`).
  - 원판 6.3.1의 seed 충돌 스캔 범위는 `06_analysis/`의 json·jsonl뿐입니다. 시험 키와 pytest 임시 출력은 잡지 못합니다.
- 실패 시나리오: 판정 집합 b1의 짝 일부(VBK0 쪽 궤적, 래치, 목격 위치)를 실행 전에 구현자가 이미 보았습니다. 이 상태로 "결과 전 정오", "판정 집합 밖 seed" 원칙을 쓰면 사실과 맞지 않습니다. c 건식 확인이 seed 90·91을 쓰는 이유와도 어긋납니다.
- 제안(정오에 넣기):
  - "단위 시험·탐침이 b1 seed(`s30`) 키를 돌렸다(시험 출력은 pytest 임시 폴더, 판정 값으로 쓰지 않음). 그러므로 6.3.1 충돌 규칙을 적용해 b1~b4를 모두 +10(seed_index 40~43)으로 옮긴다."
  - "선정 도구 스캔에 `05_tests`의 키 문자열과 탐침 기록을 더한다. 이후 시험·탐침 키는 판정 집합 밖 seed(예: `s9x`)만 쓴다."
  - 대안은 시험 키만 `s9x`로 바꾸고 노출 사실을 공개하는 것입니다. 다만 이미 돌린 b1 짝이 남으므로 +10 이동을 권합니다.
  - 담당: control(문장), python-expert(시험 키와 스캔 범위).

**E-2 [R·E] P5-2 "사례 재생 A~F에서 J-P3 판정 키 0"이 A·C(와 B)의 이어받은 기대와 충돌합니다**
- 근거:
  - 판 4a 5.3 표(`jp3_remedy_spec.md` 394~397행):
    - A(rev 4): 저장 h10 줄과 같아야 하고, 그 기대에 VB 위반 2, LS2 3, LS3 4가 들어 있습니다.
    - C(VBG4, rev 4, 반례 ⑥): "위반이 없거나 간격이 범위 밖이면 멈춤", 즉 위반이 있어야 합니다.
    - B는 LS3에서 허용 초과가 생길 수 있고 기록 전용입니다.
  - P5-2 집계 도구 `jp3_p5_fixed_values.py` 46·91~95행은 모든 줄의 판정 키를 더합니다(`judged_key_total`).
  - 정오 1절은 X11만 빼고 같은 꼴의 충돌을 남깁니다. A·C에는 rev 6 수(R5-8~R5-10)도 정의되지 않습니다. 재검토 W-1이 D에 대해 지적한 것과 같은 꼴입니다.
- 실패 시나리오: 단계 (4)에서 A·C 때문에 P5-2 멈춤 조건(판정 키 > 0)이 반드시 걸립니다. 그렇지 않으면 결과를 본 뒤에 A·C를 빼는 해석을 하게 됩니다.
- 제안 문장(정오 1절에 더하기): "P5-2의 판정 키 0과 rev 6 수의 고정은 rev 6 줄(B의 VBH·LSH1~4, D의 VBG6, E의 VBJ·LSJ1~4, F의 B·E 갈래)에만 건다. P4 끔 줄(B·D)은 A7에 따라 J-P3 기록이고, 판 4a 5.3의 사례별 합격 조건으로 판정한다. A·C(rev 4)는 판 4a 5.3 기대 그대로이며 P5-2 대상이 아니다." D의 처리(A7 대 5.3 합격 조건)는 control이 확정합니다.

**E-3 [R] 경로 2 정오 1.4의 재잠김 lookback 정의에서 항 하나가 빠졌습니다**
- 근거:
  - 경로 2 정오 18행: "수축 이동 주기에서는 $\max(13+p_h/3$ 수축 모델$,\ \hat p+\delta_m)$"으로 두 항뿐입니다.
  - 이어받는 R5-7 정의(`jp3_remedy_spec.md` 219행)는 $M^{ret}=\max(13+p_h/3,\ p_{ret,i},\ \hat p_i+\delta_m)$로 세 항입니다.
  - 정오 3절(42행) "R5-7 값 $\max(\text{수축 모델},\ \hat p+\delta_m)$"도 같은 꼴로 읽힐 수 있습니다. 판 4a 94행의 "수축 모델" = $13+p_h/3$입니다.
- 실패 시나리오: 경로 2가 $p_{ret,i}$ 없이 $M^{lb}$를 만들면 상계가 낮아져 경로 1과 J-P3 분류가 갈립니다. 경로 2 정오는 "이 정오가 우선"이라 이 식이 그대로 적용됩니다.
- 제안: 두 문서 모두 "수축 이동 주기의 이동 시작값은 R5-7 값 $\max(13+p_h/3,\ p_{ret,i},\ \hat p+\delta_m)$(판 4a 2.10절)"로 바꾸고, handoff_leak을 다시 돌립니다.

## 경고
1. **정오 6절(주입 없는 짝 = 트리거 없음): 새 빈 통과는 없습니다.** 주입이 없는 짝은 기회에서 빠지고, 줄어든 N_opp는 301 하한이 막습니다. 다만 판단에 쓰는 기록을 명시하기를 권합니다: `rod_fault.applied_periods` > 0이고 `first_applied_t_s`가 null이 아닐 때만 주입 있음. 구현 `jp3_12b_judge.py` 347~352행이 이미 이렇게 합니다.
2. **정오 7절 PHASE_FAULT: 빈 통과는 없습니다.**
   - `fault`·`fault_reground`는 `C2Phase` 값과 같습니다(`c2.py` 461~462행). 구현도 같은 집합을 씁니다(`jp3_12b_judge.py` 98·100행).
   - `phase` 배열이 없으면 6.6 존재 관문에서 판정 불가가 됩니다.
   - 정보: `IDLE`(CHECK 거부)은 FAULT가 아니어서 대상이 아니라는 점을 한 줄로 적어 둘 수 있습니다.
3. **X11 기대가 두 곳에 있습니다.** 1절은 X11 명령 해시가 기준선 LSJ4 `3672c722…`와 같고, 동시에 78fd5d2d X11 줄과도 같아야 한다고 적습니다. 두 값이 같다는 근거(4a P4-5 고정값)를 인용하거나, 하나만 기준으로 두십시오.
4. **9.2 (다)의 T4h 배열 이름과 12b 판정 도구의 목록이 다릅니다.**
   - 9.2 (다)에는 `jp3_r59_end_guard_substeps`가 있는데, 12b 판정 도구의 rev 6 배열 목록(`jp3_12b_judge.py` 106행)에는 이 이름이 없습니다.
   - 커버리지 키 `jp3_r58_witness_carries`(줄)와 배열 `jp3_r58_witness`(T4h)는 이름이 다릅니다.
   - 건식 출력에 `key_presence --npz-dir … --array`를 돌려 네 이름이 모두 나오는지 실행 전 감사에서 확인합니다.
5. **재검토에서 넘어온 항목 둘이 정오에 없습니다.**
   - 셀 배정 규칙(rank = `h8_noise_VB` L2 첫 등장 순서, 셀은 다리 우선)이 명세에 없고 `selection.json`에만 있습니다(재검토 54·60행).
   - hydraulics 위임(저하중·인장 영역의 $p^*_{ub}$ 건전성, 재검토 88행)이 정오 10절 "남은 일"에 없습니다.
   - 두 항목을 정오에 적거나 남은 일 목록에 넣으십시오.
6. **9절 공개 문구는 실제와 맞습니다.**
   - `x4_keys.py`는 두 파일을 통째로 파싱하지만(`json.loads`) 쓰는 것은 `key`·`level`뿐이고 출력도 키뿐입니다. "파일을 파싱했으나 `key`·`level`만 꺼냈다"로 적으면 더 정확합니다.

## 축별 확인 결과
- **(T) 판 5 실행 출력**: 단계 폴더 기준으로는 없습니다.
  - `j9_runs/` 최상위는 판 4a 커밋 넷(78fd5d2d·b51ed6e1·d3c6c57e·fa997f4c)뿐이고, worktree도 같습니다.
  - `06_analysis`에 `*p52*`·`*p54*` 파일이 없습니다.
  - scratchpad `python-ed5impl`에는 junit xml 6개만 있습니다.
  - 단, E-1의 시험·탐침 실행은 남습니다.
- **(I) 9.1 키 파일 sha**:
  - 세 값이 `x4_out.txt`와 같습니다. 키에 CRLF를 붙여 직접 다시 계산한 값도 같습니다(g6 `1a79e02f`, g8 `b7c7470a`, ref `95ce6f27`).
  - g6은 4a-4 정오 1의 고정값, `FIXED_INPUTS*.SHA256SUMS` 22행, `j4a_remedy_b06e409e/SHA256SUMS`와 같습니다.
  - `x4/SHA256SUMS` 두 항목은 파일 실측과 같습니다.
- **(E) 시험 전용 설정 규칙(X11 판정 밖, VBG6 setting_defect)**: 판 4a 4-7 4.9 구조(시험 전용 설정은 별도 폴더에서 사례 판정)를 넓힌 것이라 새 빈 판정을 만들지 않습니다. 남는 것은 E-2의 P5-2 대상 정의입니다.
- **(S) 줄바꿈과 추적**:
  - 정오, 경로 2 정오, 재검토, `x4/*`는 CRLF 0이고 BOM이 없습니다.
  - `j_p3_cause/** -text`가 걸립니다(`.sha256` 포함, `check-attr` unset).
  - 모두 추적 밖이고 무시 규칙에는 걸리지 않습니다. 커밋 때 함께 넣으면 됩니다. `.sha256`을 만들 준비는 되어 있습니다.

## 실행한 검증
- Bash: sha256 측정, git 조회(`status --ignored`, `check-attr`, `show --stat`, `ls-files -s`, `log`), CRLF·BOM 확인, `j9_runs` 최상위 목록, scratchpad 데이터 파일 목록.
- python-dev `-I -B -c`: 키 파일 sha 세 개를 다시 계산했습니다.
- `gate_scan.py`(worktree `jp3_12b_judge.py`): 발견 0.
- 읽은 것: 정오, 경로 2 정오, 재검토, `x4_keys.py`, 판 4a 2.10·5.3절, 4a-7 4.9, worktree의 `test_x10_rod_fault.py`·`jp3_case_replay.py`·`jp3_p5_fixed_values.py` 일부, `c2.py` C2Phase.
- 만든 파일은 없습니다. 메모리 `C:\Users\jinbeom\.claude\agent-memory\verif-protocol-auditor\audit_pitfalls.md`에 두 줄을 더했습니다(판정 집합 키를 쓴 시험·탐침, 범위만 고친 예측 행의 남은 충돌).
- source_guard는 쓰지 않았습니다(원본 쓰기 없음).
- 사용한 스킬: 없음

## 재감사(2026-11-22) 요지
- 차단 남지 않음. control의 네 결정(seed 40~43 시작값 고정, 하네스 시험 키 s95~s99, 05_tests 스캔은 12b 선정에만, c 건식 90·91) 모두 건전.
- 경고 1(충돌 = 생성 키와 정확히 같은 키) → 메인이 정오 0.2절에 문장 반영. 경고 2(ed5_design/probes/ 폴더에 탐침 키 기록)는 실행 전 감사 전까지. 경고 3(j9_runs 안 seed 40~43 확인)은 실행 커밋 선정 스캔에 맡김.
