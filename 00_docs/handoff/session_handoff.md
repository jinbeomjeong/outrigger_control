# 세션 인계

새 세션은 이 문서와 아래 파일로 상태를 파악한다. 이전 대화 맥락은 없다. **아직 아무것도 실행하지 말고, 먼저 상태 확인 결과와 다음 단계 계획을 보고한 뒤 사용자 확인을 받는다.**

- 갱신: 2026-10-30 21시경, 이정표 커밋 직전 (커밋할 때마다 이 파일을 덮어쓴다. 옛 판은 git 이력).
- 마지막 커밋: **05708b2**(명세 개정 85·86: 426 하네스 공백 연구, P-S8-36 후보, RV1·RV2 묶음). 이번 이정표 커밋(최종 제어기 확정, SGS·R4c30 03_src)은 곧 한다. 그 전: 9917955(개정 76~84 요약 행, B5 표시 이름), 38fb395(Chrono D424R 판정, B5 기준선 비교, 에이전트 설계 반영), 3434912(P-S8-35 DSb75, D424 판정, R2DS 인수), 7e4a0db(Q-D P-S8-33 L1gs 채택·L2 폐기, Q-C 후보 없음, R2 인수), 1cd4618(최종 Chrono S9SL·G6P·연구 ③, r79 확정, Q-A~Q-G). 더 앞은 `git log`와 이 파일의 git 이력.
- 세션 기록: 일반 Windows 터미널에서 `claude`를 직접 실행한다(2026-10-26 결정).

## 현재 위치

- S9 완료(6/6, 합계 65/67, 2026-10-27). 지금은 **S9 뒤 제어 개선 단계**다(로드맵 1절, 명세 `00_docs/04_control/s6_control_spec.md` 427~432절).
- **최종 제어기 확정(명세 429.11)**: R8 C2 + L1gs(P-S8-33) + DSb75(P-S8-35) + SGS any_loc(P-S8-36 P36sa) + R4c30(P-S8-31 평지 토양 틈 여유 30 mm). P37t·ZIC는 기각했다(429.9·429.10).
- 인수 회귀 B(래퍼 B1 → 프리셋 전환 → 구현 B2) 중 B1이 돌고 있다. 그 뒤 재집계 C와 Chrono FINAL-REP·FINAL-R-REP다.

## 이번 커밋에서 바뀐 것 (05708b2 이후, 2026-10-30 오후~저녁)

1. **SGS(any_loc) 03_src 구현, 인수 통과**(명세 427.12.3·427.12.5.1): 구현 = 래퍼 P36sa 해시 1,220/1,220 + H9 36/36, scope `soil_sign` = P36s 1,220/1,220, 끈 상태 = R2DS 4/4. `c2.py` `LiftStrokeGuardSettings.soil_stop`·`soil_stop_scope`, 사건 `FAULT_LIFT_STROKE_LIMIT:soil:<legs>`, 분류 `stroke_limited_stop`(안전 종료).
2. **R4c30 03_src 구현**(명세 429.9): `SlopeClearanceMarginSettings.flat_soil_margin_m`(클래스 기본 0.0), 사건 `INFO_LOC_FLAT_SOIL_MARGIN:<mm>`. 단건 해시 일치, 단위 시험 5,203 통과.
3. **P37t·ZIC 기각**(명세 429.9·429.10): 03_src에 넣지 않고 래퍼 토큰(`P37t`, `P38z`)만 기록용으로 남겼다.
4. **프리셋 기본값은 아직 꺼짐**이다. 전환 순서는 명세 429.11(B1 → 프리셋 전환 → B2)이다. 전환 값: `lift_stroke_guard.soil_stop=True`, `soil_stop_scope="any_loc"`, `slope_clearance_margin.flat_soil_margin_m=0.03`.
5. **새 도구**
   - `04_scripts/03_control/s9/stable_ready_compare.py`: 안정 READY 기준 비교(429.8 판정 규칙 정정).
   - `04_scripts/03_control/s9/rep_evidence.py`: 대표 시나리오 근거 자료(432.4).
   - `04_scripts/03_control/s9/p38_p3b_recon.py`: P3b 24건 1 kHz 자세 재구성(431.2, `rev85/p38_p3b_recon.json`).
   - `04_scripts/03_control/s9/s9_settle_rejudge.py`: `rebuild_row_verdict` 판정 순서 수정. R2DS 연구 ① 177의 통과 / 행정 제한 통과가 98/39에서 94/43으로 바뀌었다(427.12.1, 원본 `rev83/history/R2DS_slope_rejudged_pre_classify_order_20261030.json`).
   - H9 suite(`s9_slope_fix_candidates.py run --suite h9`, 명세 430.2).
   - `b5_baseline_compare.py` ABL 스위치에 SGS·R4 끔 추가(429.11).
   - `04_scripts/03_control/s9/final_ctrl_offline.py`: (a) 재사용 동치 재생(432.4 E3), **진행 중**.
6. **Chrono 묶음 정의**(`run_S9.py`·`s9_batch.py`, cad): RV3~RV6, FINAL1~6, FINAL-R, FINAL-REP(7건, 432.6.1), FINAL-R-REP(16행, 432.6.2). 프리셋 점검 기대 이름은 `final_SGS_R4`다(`run_S9.CONTROLLER_EXPECTATIONS`, 429.11).
7. **결과**: `06_analysis/02_control/s9/rev83/`~`rev85/`.
   - H9 판정(`rev85/h9_roll_fine{,_cmp}.json`, 명세 430.3.1): 패드 B 좌우 경계는 \|φ_c\| ≤ 2.86°($R_c$ 0.65)이고 roll_neg가 지배 방향이다. Chrono X6-rb로 확인할 예정이다.
   - SGS 회귀 `rev85/p36s_A_*`, `p36sa_A_*`, 조합 stage 1 `p37c_*`, stage 2 `p37s2_*`.
8. 문서: 명세 427.9~432절, decision_log 5절, CLAUDE.md 기준값 표 제어기 칸(최종 구성), 로드맵 1·4·5·6절, 이 문서.

## 진행 중 (scratchpad 러너, 예약 등록)

- **B1**: 20:35 시작, 21:15~21:35 끝날 예정. 래퍼 최종 조합 `P36sa+R4c30`(명세 429.11, 래퍼 1,220 + 연구 A 80 + r67 384 + H9 36).
- **RV2** E 1건이 돌고 있다.
- 대기 러너
  - B2: 플래그 `final_src_ready`가 서면 시작한다.
  - FINAL-REP 러너 2개와 재집계 C: 플래그 `final_adopted`가 서면 시작한다.
- 플래그는 `scratchpad\sched\day2\setflag.ps1`(세션 임시 파일, 저장소 밖)로 세운다.

## 다음 할 일 (로드맵 6절과 같은 순서)

1. 인수 B1 결과 확인
2. R8 프리셋 기본값 전환(python, 한 커밋) → `final_src_ready` 플래그
3. 인수 B2: finB1 = finB2 명령 해시 id별 1,720 일치, 단건 끔 = R2DS 4/4, unit 전체 통과 → `final_adopted` 플래그
4. Chrono FINAL-REP 7건 + FINAL-R-REP 16행 + 재집계 C(r79 전체, B5 wide, x426 C·D, 정착 v2; 명세 429.11 C 범위)
5. 논문 4절 갱신(명세 432.7, paper-writing-expert `[모드]`·원본 수정 허락)
6. 리뷰·빌드(paper-reviewer → 반영 → integrity-checker 원고↔결과 수치 → 빌드)
7. 포스터
8. GIF(MP4 포함, 논문 뒤로 미룸 — 사용자 결정)

## 대기 사용자 결정

- **지금은 없다.**
- 이전 "아침에 물을 항목"(7e4a0db 당시)은 모두 정리됐다.
  - 논문 리뷰 (B): B1~B5 반영, B6(부록 이동)은 하지 않음(38fb395 당시 결정).
  - IMU 영점 허용 0.119°: 유지.
  - 문헌 보강: 29편 추가.
  - J1 패드 B $R_c$ ≤ 0.875 권고: 앞내림·대각에만 쓴다. 좌우는 경계 세분 연구(명세 430)로 대체했고, Chrono X6-rb로 확정한다.
  - `.claude/settings.json`: 로컬(`settings.local.json`)로 옮김.
- FINAL-REP 1단계에서 432.3 기대값 미달, 430.3·430.4 미달, R4 때문에 생긴 새 실패가 나오면 확장 전에 원인을 분석하고 사용자에게 묻는다(명세 432.3).

## 논문·포스터 (커밋 안 함)

- `09_paper/`는 **커밋하지 않는다**(`.git/info/exclude`). GIF·MP4도 커밋하지 않는다.
- 논문 결과는 최종 제어기 기준이다(사용자 결정, 명세 431). Chrono는 대표 시나리오 최소안(명세 432)이고, 이전 판 Chrono는 2.6.3절과 부록 이력표·대조 통계로 둔다.
- 논문 작성·교정·빌드는 paper-writing-expert, 리뷰는 paper-reviewer에 맡긴다(메인 세션 직접 수정 금지).

## 주의

- 에이전트 지시문에 매번: 셸 heredoc·`python -`·`sed -i` 금지, Write로 쓴 파일을 `python -I`로 실행, 커밋 메시지는 `git commit -F <파일>`.
- Python·pytest·긴 명령은 **PowerShell 도구**로 실행한다(Bash 도구 자식 Suspended 멈춤 회피).
- 모든 서브 프로세스는 **compute-scheduler-expert 배치**를 받은 뒤 띄운다(단건 포함, 비용 측정만 단독).
- 모니터링(long-running-task-monitor, 15분 이상 작업)을 할 때 **예상 종료 시각**을 받는다.
- 주요 작업 중간마다 커밋한다. **커밋 전 integrity-checker를 먼저** 돌리고, 이상 없을 때만 커밋·푸시한다. 커밋마다 이 문서를 갱신해 같은 커밋에 넣는다.
- **09_paper·GIF·MP4는 커밋하지 않는다.**
- 장시간 배치는 WMI로 세션과 분리하고 창마다 제목·안내 문구를 붙인다. Suspended 프로세스는 ResumeThread로 자동 조치 뒤 사후 보고, 시뮬레이션·실행기는 자동 종료 금지.
- S단계 본 판정 실행 전에는 사용자에게 알리고 확인받는다.
- 작업이 끝나면 사용자에게 Microsoft Store 자동 업데이트 다시 켜기를 알린다(Windows Update 일시 중지 11-01 13:06 만료).
