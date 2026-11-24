# 격자 J-P3 H-7 원인 분리 — 기록용 Part D 분석(판 6 판정에 쓰지 않음, 2026-11-24)

- 작성: control-expert. **판 6 멈춤 뒤의 기록용 반사실이다. 판 6 판정에 쓰지 않는다.**
- 이것은 J-P3 판정이 아니라 팔 사이의 비교다. 판정 도구는 돌리지 않았다.
- 값은 각 줄의 ③ 기록(`hydraulics_record.extend_bound_check`, 실행 안에서 경로 1 정의로 계산된 값)과 T4h 배열(`jp3_class`, `jp3_used_bound_Pa`, `rod_pressure_Pa`, `phase`, `lsb_*`)에서 읽었다.
- 입력
  - `j9_runs/79495405/records_after_stop/D_a1/grid_cause.jsonl`(sha256 `c6a702748d0924b51e923217df1e1f8b1a5a22714592711de934deb5d101d32c`)과 `grid_cause_t4h/`
  - 실행: python-expert, ed6-records 3ecf61f1, 2026-11-24 15:43~15:48, 종료 0
  - 재현 확인 `reproduction_compare.json`: 봉인 팔 12줄이 기존 격자 줄(`confirm_b.jsonl`, sha256 `26d5032c…`)과 명령 해시 12/12 같다.
  - 선택 키: `prelaunch_j9/run_records_ed6/d_grid_keys12.json`(a995abff…)
    - 격자 timing level breach 44줄 가운데 사건 FS24·G4·RE1bF 각 4줄을 골랐다.
    - 첫 breach 다리가 FR·RL·RR 순으로 돌도록 골랐다.
  - 팔(플랜트는 VBL)
    - `P6-J-a1a2b3` = 봉인 구성
    - `P6-J-a1b3` = A(ii) 끔
    - `P6-J-none` = 판 6 구성 요소 모두 끔. VBJ 제어기와 같고, ③ rev 6는 켜져 있다.
- 열지 않은 것: 경로 2 결과 `ed6_p2_79495405/`, 블라인드 경로 `j9_runs/606f8713/cdry_a1/VBK_c92*`·`VBK_c93*`·`cdry_a1/logs/`
- 스크립트와 출력(같은 폴더, python-dev `python.exe -I -B`)
  - `h7_h1_compare.py` → `h7_h1_compare.txt`, `h7_h1_min_gap.csv`
    - 다리마다 사건 뒤 탐침 `carry_ext` 읽기 가운데 gap이 가장 작은 읽기를 뽑는다.
    - 그 다리의 사건 이후 A(ii) 켬 읽기 수와 lsb 명령 변경 읽기 수를 함께 낸다.
  - `h7_h2_breach_reads.py` → `h7_h2_breach_reads.txt`
    - T4h 재계산과 ③ 기록 breach 수를 대조한다.

## 0. 결론
- **원인은 ③ rev 6의 잠김 신장 운반 상계다. 판 6 구성 요소의 원인이 아니다.**
  - 판 6 구성 요소를 모두 끈 팔(none, 판 5 VBJ 제어기 + VBL 플랜트)에서도 12줄 가운데 11줄이 breach다.
  - A(ii)만 끈 팔에서도 11줄이 breach다. 봉인 구성은 12줄이다.
  - breach 다리·시각·크기는 세 팔이 거의 같다.
- A(ii)의 몫은 작다. 봉인 구성에만 있는 breach는 18읽기 가운데 2읽기다.
  - 1줄은 bottom-RL-Fs4-o0.025-G4의 RR(gap −6.86 bar). A(ii)가 그 다리 명령을 3읽기 바꿨다.
  - 1다리는 bottom-FL-Fs2-o0.075-FS24의 FR(gap −0.42 bar; A(ii) 끔에서는 +0.56 bar).
- 판 6 구성 요소가 없는 VBJ 제어기(none 팔)에서도 VBL 플랜트의 같은 행이 breach다. 그래서 이 breach는 판 6에서 생긴 것이 아니다. 이 조건의 행을 판정에 넣지 않았기 때문에 그동안 보이지 않았던 것이다.
  - 근거(`records_B_analysis.md` 5절): 판정 행에서는 breach가 0이었다.
    - 판 5 VBK 334행, 판 5 j9_main 200행
    - 판 6 j9_main 388행, 확인 (가) 216단위(J-P3 판정 56행)
  - 이 조건은 "LEVEL 중 사건 뒤 첫 탐침의 잠김 신장 운반"이다.
  - 판 5 플랜트(VBJ)에서 같은 행이 breach인지는 이 자료로 확인하지 않았다. Part D 플랜트는 VBL이다.

## 1. 팔별 결과(`h7_h1_compare.txt`)
| 묶음 | 봉인 a1a2b3 | A(ii) 끔 a1b3 | 모두 끔 none |
|---|---|---|---|
| breach 줄(12줄 중) | **12** | 11 | 11 |
| J-P3a breach 읽기 합 | 18 | 16 | 16 |
| J-P3b·J-P3c breach | 0 | 0 | 0 |

- 12줄 가운데 11줄은 세 팔 모두 breach다. 대부분 같은 다리·같은 시각(±0.1~1.0 s)이다. 봉인 구성에만 있는 것은 bottom-RL-Fs4-o0.025-G4 1줄이다.
- breach 읽기는 모두 탐침 단계의 `carry_ext`(잠긴 다리의 탐침 신장 운반)다.
  - 확인(`h7_h2_breach_reads.txt`): T4h에서 `carry_ext`이면서 로드 판독 > 사용 상계인 읽기를 셌다.
    - 팔별 18 / 16 / 16으로 ③ 기록 `jp3a_breach_reads`와 다리마다 같다(불일치 0).
    - 50읽기 모두 탐침 단계다.
  - 로드 판독이 사용 상계를 0.01~22.4 bar 넘는다(gap = 상계 − 판독이 음수).
  - 예: top-RR-Fs0-o0.0-FS24의 FR. 봉인 −11.37, A(ii) 끔 −9.51 bar다.
- A(ii) 끔·모두 끔 팔에서는 그 다리의 A(ii) 활동이 0이다. 그래도 breach가 남는다.
- none과 a1b3는 12줄 모두 같은 breach 다리·시각이다. 이 행들(LEVEL 중 사건)에서는 A(i)·B3가 breach에 영향을 주지 않는다.

## 2. 판단과 함의
- J-P3 H-7(기록용 격자 44줄·감도 3줄)은 **③ rev 6 상계 정의가 덮지 못한 조건**이다.
  - 조건: 사건이 LEVEL 중에 나고, 사건 뒤 첫 탐침이 잠긴 다리를 신장 운반으로 출발시킨다.
  - 이때 breach 읽기의 로드 판독(16.95~47.05 bar)이 ③의 운반 상계(13.61~29.86 bar)보다 높다(세 팔 50읽기).
- 판 6 판정은 바뀌지 않는다. 확인 (가) J-P3 56행은 통과, 판 6 전체는 불합격 그대로다.
- 판 5의 J-P3 통과 판정도 봉인 규칙대로 그대로다. 다만 판 5·판 6 모두 이 조건의 행을 판정 집합에 갖지 않았다. **③ rev 6의 J-P3 통과가 이 조건까지 덮는다고 말할 수 없다.** 이것을 공개한다.
- 상계가 왜 낮은지(어느 상계 원천인지, 갇힘 압력의 물리)는 이 분석 범위 밖이다.
  - `jp3_model_bound_source`·`jp3_model_bound_inherited` 배열과 탐침 직전 수축·잠김 이력으로 hydraulics-expert가 판정할 일이다.
  - `위임 필요(hydraulics-expert)`: 입력은 이 폴더의 `h7_h1_min_gap.csv`, `D_a1/grid_cause_t4h/`, 격자 T4h다.

## 3. 판 7 입력
- J-P3 H-7은 판 6 구성 요소 설계 문제가 아니다. **③(rev 6) 상계의 적용 범위 문제**다.
- 판 7에서 정할 것
  - (가) ③ 상계를 이 조건까지 넓힌다(③ rev 7). 이 경우 hydraulics 판정 뒤 control이 규칙을 쓴다.
  - (나) 이 조건의 행을 판 7 J-P3 판정 집합에 넣는다. 격자 timing level 행이 그 후보다.
  - 사용자 결정이 필요하다.
- A(ii)의 작은 몫(2/18 읽기)은 A(ii) 보완을 설계할 때 함께 본다.
