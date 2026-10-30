# 세션 인계

새 세션은 이 문서와 아래 파일로 상태를 파악한다. 이전 대화 맥락은 없다. **아직 아무것도 실행하지 말고, 먼저 상태 확인 결과와 다음 단계 계획을 보고한 뒤 사용자 확인을 받는다.**

- 갱신: 2026-10-31 07시 30분경, 최종 제어기 Chrono·재집계 판정 커밋 직전 (커밋할 때마다 이 파일을 덮어쓴다. 옛 판은 git 이력).
- 마지막 커밋: **1e1372c**(R8 프리셋 최종 제어기 전환, B1 통과, RV2/RV3 판정; 푸시 완료). 그 전: 72d1722(최종 제어기 확정: SGS any_loc + R4c30 채택, P37t·ZIC 기각, FINAL-REP 계획), 05708b2(명세 개정 85·86), 9917955, 38fb395, 3434912, 7e4a0db, 1cd4618. 더 앞은 `git log`.
- 세션 기록: 일반 Windows 터미널에서 `claude`를 직접 실행한다(2026-10-26 결정).

## 현재 위치

- S9 완료(6/6). 지금은 **S9 뒤 제어 개선 단계의 마무리 + 논문 v4**다(로드맵 1·6절, 명세 `00_docs/04_control/s6_control_spec.md` 425~432절).
- **최종 제어기**: R8 C2 + L1gs(P-S8-33) + DSb75(P-S8-35) + SGS any_loc(P-S8-36, 논문 R8) + R4c30(논문 R9). R8 프리셋 `with_10hz_d1()` 기본값으로 켜져 있다(명세 429.11).
- 인수 B1 = B2(해시 1,720/1,720) 통과.

## 이번 커밋에서 바뀐 것 (1e1372c 이후, 2026-10-30 밤~10-31 아침)

1. **Chrono 최종 제어기 대표 사례 전부 통과**(`07_results/S9/`는 로컬 전용, 판정 값은 `06_analysis/02_control/s9/rev85/evidence/`):
   - FINAL-REP 7건, FINAL-R-REP 16행(명세 432.5.x·432.6.2).
   - FINAL6 J2 B RR 패임 150 mm: READY 84.4 s, 판독 행정 675.1 mm(가드 여유 7.7 mm), SGS 0(명세 426.9.D.2, `final6_sgRRd150_judge.json`). R9 행정 비용 약 +40 mm, 통과 패임 한계 약 194 → 158 mm(추정).
   - FINAL-REP-X J2 B ×1.1 180 s: 첫 READY 98.9 s, 끝 자세 0.032°(120 s판 P3-4 판정 불가 해소, 명세 432.5.4).
   - X6-rb2 J1 B roll −2.64°: 통과, 판독 행정 679.87 mm(가드 여유 2.93 mm, 명세 430.3.3).
2. **재집계**:
   - r79: G1 기반 G6 288건을 `R72_PATH=per_leg`로 재실행·병합(`s8/rev79/fin_r79_merged*.json`), Q-E 합격 11/855 = 1.29 %(CP 2.12 %), 명세 429.11.2.
   - B5 wide 879건(`s9/rev84/fin2_b5_wide_official.json`)·main 16사례(`fin_b5_main.json`): C2 관문 통과 206 + 안전 종료 72, 크롤러 하중 완료 0(ABL 130·60, IND 183·13), 명세 425.5.
3. **사용자 결정(2026-10-31)**: IMU 선정 조건 ≤ 0.118°(U-S9P-16 개정), H-6 판독 행정 +23 mm(연약 J1·J2·S1만), 경사 틈 −15 mm(명세 432.4.7), 좌우 ≤ 2.64° 확정(430.3.4), roll_pos 2.64° Chrono 1건 추가, B5 main 재실행·4.11절 한계 문장.
4. **E1 근거 자료**(`rep_evidence.py` schema 3, `rev85/harness_chrono_pairs.json`): 판독 행정끼리 비교로 고침(섞인 비교 결함 수정), 기존 54짝 49/54, 최종 짝 7/9, 가드 절단 표시, P3-2 FLAG 처리.
5. **러너 결함 수정**: 환경 변수 복원이 빈 문자열을 남겨 `R72_PATH=""`가 상속되던 문제(`make_runner`·`r72_g6_screen`·`r51`·`b5_baseline_compare` 빈 값 처리, `WeakPatchMissingError`).
6. 문서: 명세 311·425.5·426.9.D·429.11·430.3·432.4~432.5, decision_log 2절, IMU 검토 문서 10.6, CLAUDE.md 기준값(0.118°, 좌우 권고), 로드맵 6절, 이 문서. `10_rpi_migration/`(라즈베리파이 이식 검토·블록 다이어그램·구성 요소 표).

## 진행 중

- **Chrono X6-rp2**(J1 B 상단 roll_pos k 0.6 = +2.64°, 행 `S9SL_X6rb_J1_B_top_Fs4_r2p64_p0`, 07:06 시작, P 단독, 예상 종료 08:20~09:55, 예약 owner `main-X6rp2`). 하네스 틈 30.9 mm라 Chrono 틈이 P3-5 하한 25 mm 아래일 수 있다(추정). 결과로 roll_pos 범위를 확정한다(명세 432.4.7).
- 러너·플래그: `scratchpad\sched\day2\`(세션 임시, 저장소 밖).

## 다음 할 일

1. X6-rp2 판정(control) → 실패면 roll_pos 범위·틈 보완 안건을 사용자에게 묻는다 → 논문·CLAUDE.md 좌우 권고 문구 확정.
2. 논문 남은 TBD: E1-final(요약 문장), E5-final, 그림 6·7 최종 판, 경사 틈 −15 mm 반영, 표 12 X6-rb2 행, 표 23 중복 오타.
3. 리뷰·빌드(paper-reviewer opus/high → 반영 → integrity-checker 원고↔결과 수치 → 빌드·docx·latexdiff·v4 스냅숏).
4. 포스터(초록 docx + pptx v3).
5. GIF(논문 완료 뒤, 시나리오별, 기존 `render_case_gifs.py` 화면 구성).
6. 나중: compute-scheduler-expert 기록 모드(끝난 작업 실측), dynamics-dev hypothesis 설치(dry-run 먼저).

## 대기 사용자 결정

- **지금은 없다.** X6-rp2 결과에 따라 roll_pos 범위 결정이 생길 수 있다.

## 논문·포스터 (커밋 안 함)

- `09_paper/`는 **커밋하지 않는다**(`.git/info/exclude`). GIF·MP4도 커밋하지 않는다.
- 논문 결과는 최종 제어기 기준이다. Chrono는 대표 시나리오 최소안(명세 432)이고, 이전 판 Chrono는 부록 이력표·대조 통계로 둔다.
- 논문 작성·교정·빌드는 paper-writing-expert, 리뷰는 paper-reviewer에 맡긴다(메인 세션 직접 수정 금지). 수정 전 보관본은 `09_paper/history/`.

## 주의

- 에이전트 지시문에 매번: 셸 heredoc·`python -` 금지, Write로 쓴 파일을 `python -I`로 실행, Bash `find /` 금지(고아 find.exe가 CPU를 먹은 일이 있음), 커밋 메시지는 `git commit -F <파일>`.
- Python·pytest·긴 명령은 **PowerShell 도구**로 실행한다(Bash 도구 자식 Suspended 멈춤 회피).
- 모든 서브 프로세스는 **compute-scheduler-expert 배치**를 받은 뒤 띄운다(단건 포함, 비용 측정만 단독). 러너 env에 `R72_PATH`가 빈 값으로 남지 않게 한다.
- 모니터링(long-running-task-monitor, 15분 이상 작업)을 할 때 **예상 종료 시각과 근거**를 받는다.
- 주요 작업 중간마다 커밋한다. **커밋 전 integrity-checker를 먼저** 돌리고, 이상 없을 때만 커밋·푸시한다. 커밋마다 이 문서를 갱신해 같은 커밋에 넣는다.
- **09_paper·GIF·MP4는 커밋하지 않는다.**
- 장시간 배치는 WMI로 세션과 분리하고 창마다 제목·안내 문구를 붙인다. Suspended 프로세스는 ResumeThread로 자동 조치 뒤 사후 보고, 시뮬레이션·실행기는 자동 종료 금지.
- S단계 본 판정 실행 전에는 사용자에게 알리고 확인받는다.
- 작업이 끝나면 사용자에게 Microsoft Store 자동 업데이트 다시 켜기를 알린다(Windows Update 일시 중지 11-01 13:06 만료).
