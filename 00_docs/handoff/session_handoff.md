# 세션 인계

새 세션은 이 문서와 아래 파일로 상태를 파악한다. 이전 대화 맥락은 없다. **아직 아무것도 실행하지 말고, 먼저 상태 확인 결과와 다음 단계 계획을 보고한 뒤 사용자 확인을 받는다.**

- 갱신: 2026-11-01, Q-F 재결정·MCV A/B 대응·개정 61 문서 정리·journal auger Chrono 커밋 직전 (커밋할 때마다 이 파일을 덮어쓴다. 옛 판은 git 이력).
- 마지막 커밋: **5bfb970**(좌우 경계 Chrono X6-rp2 실패·X6-rp3 통과, 방향별 권고; 푸시 완료). 그 전: 840bc31, 1e1372c, 72d1722. 더 앞은 `git log`.

## 5bfb970 이후 바뀐 것 (2026-10-31 낮 ~ 11-01)

1. **Q-F 재결정(사용자 결정 2026-10-31, 명세 429.11.3)**: 센서 오차 L3·L4를 최종 제어기로 재실행(`04_scripts/03_control/s8/r79_L3L4_final.py`, `s8/rev79/fin_r79_L3L4_final{,_judgement}.json`, 1,002실행). conservative 13/501(CP 4.09 %), old_worst 81/501(CP 19.12 %) 모두 3 % 초과 → 압력 센서 요구는 **normal 등급 수준**(온도 보상 또는 사용 온도 영점 교정). CLAUDE.md 센서 행 갱신.
2. **MCV A/B ↔ 헤드/로드 대응(11-01, `hydraulic_circuit.md` 8절)**: 회로도 판독상 FL·RL은 MCV A = 헤드, **FR·RR은 MCV A = 로드**. 시뮬레이션 영향 없음(다리별 속도 명령). 실기 통합 때 밸브 명령 부호·압력 센서 태그를 다리별로 정해야 함(실물 배관 미확인). 코드 4개(`rod_chamber.py`, `sensors/hydraulic.py`, `sensors/rod_side.py`, `04_scripts/04_hydraulic/extend_tail_check.py`)는 docstring만, 회로도 PNG 갱신(옛 판 `00_docs/02_hydraulic/history/`).
3. **개정 61 문서 정리(11-01)**: `dynamics_model.md`·index 기준값 표를 현재 YAML에 맞춤(옛 값 병기, 계산·실행 없음), `rod_side_pressure.md`·`control_candidates_comparison.md` 옛 값 표시. CLAUDE.md 크롤러 접촉 행(L2b 강체 NSC 명확화).
4. **논문용 journal auger Chrono(cad 10-31)**: `run_S8C.py` 그룹 JA / 세트 jaug(K24_top_flat_Fs4의 오거 중·하단 2건), `s9_batch.py` JOURNAL-AUGER, 결과 `s9/rev85/evidence/journal_auger*`, 판정 `journal_auger_rigid_judge.py`, 시험 `test_s9_journal_auger.py`. 기존 시험 4개는 새 그룹 제외만.
5. **U-PAD-7(사용자 결정 10-31)**: 논문에서 패드 사양 변수 삭제, 결과는 패드 B 그대로(재실행 없음). 논문은 v4.2(캡션 형식)→v4.3(유압–다물체 결합 그림 4, 2.2·2.4절 기호 $F_a$/$F_{cyl}$)→v4.4(패드 변수 삭제, 패드 B만 재집계, 리뷰 반영) `09_paper/v4.4/`(커밋 안 함).
6. GIF 렌더(`render_case_gifs.py`, `gif_lists/`). 산출 GIF·MP4(`06_analysis/01_chrono/1[89]_S*/gifs/`, 약 72 MB)와 r79 L3L4 중간 산출물(`.partial.jsonl`, `.log`, `.log.err`)은 **커밋하지 않음**(사용자 결정 11-01).
7. 전역(저장소 밖): 새 전역 에이전트 **graph-expert**(데이터 차트, `~/.claude/agents/graph-expert.md`, 도구 `~/.claude/tools/graph`, python-dev에 plotly·kaleido·colorspacious·cmcrameri·colorcet·adjustText 설치). 데이터 차트는 graph-expert, 논문 반영은 paper-writing-expert.

## 840bc31 이후 바뀐 것 (2026-10-31 07~11시)

1. **좌우 경계 Chrono 2건**: X6-rp2(J1 B roll_pos +2.64°)는 P3-5만 실패(첫 READY 뒤 틈 24.84 mm < 25 mm; LOC 때 틈 추정 17.2 mm 과대 + 높은 쪽 패드 46~47 mm 침하, 명세 430.3.5). 사용자 결정으로 **좌우 권고 방향별**: 왼쪽(roll 음) ≤ 2.64°, 오른쪽(roll 양) ≤ 2.2°(430.3.6). X6-rp3(+2.2°) 통과(틈 32.6 mm, 가드 여유 70.4 mm, 430.3.7).
2. **E1**(`rep_evidence.py` FINAL_RUNS 12, 대체 1 → 최종 11짝, 일치 8/11, 모두 하네스 낙관), H-6 문구에 경사 틈 −15 mm. **E5** 최종 하네스 기준 재생성(경사 패드 A→B 22/67, 평지 0/36). 그림 7용 하네스 8건 재실행(`evidence/figD_harness_pads.json`, 해시 일치).
3. **논문 종합 리뷰 도메인 답**(명세 432.4.8): 최종 프리셋에서 가드 완화 DONE 경로 미도달, 연구 ① 연약 통과 56 중 경계 17, B5 남은 실패 7 = 크롤러 이탈 전 SGS 정지(425.5 정정), G1 B E3 동치 유지(하네스 p0 정착 훅 편향).
4. 문서: 명세 425.5·430.3.5~7·432.4.5~8·432.5.3, decision_log, CLAUDE.md 좌우 권고 행, 로드맵 6절, 이 문서.
- 세션 기록: 일반 Windows 터미널에서 `claude`를 직접 실행한다(2026-10-26 결정).

## 현재 위치

- S9 완료(6/6). 지금은 **S9 뒤 제어 개선 단계의 마무리 + 논문 v4**다(로드맵 1·6절, 명세 `00_docs/04_control/s6_control_spec.md` 425~432절).
- **최종 제어기**: R8 C2 + L1gs(P-S8-33) + DSb75(P-S8-35) + SGS any_loc(P-S8-36, 논문 R8) + R4c30(논문 R9). R8 프리셋 `with_10hz_d1()` 기본값으로 켜져 있다(명세 429.11).
- 인수 B1 = B2(해시 1,720/1,720) 통과.

## 840bc31에서 바뀐 것 (1e1372c 이후, 2026-10-30 밤~10-31 아침)

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

- 없음(실행 중인 계산 없음). 러너·플래그는 `scratchpad\sched\day2\`(세션 임시, 저장소 밖).

## 다음 할 일

1. 논문: v4.4 완료(리뷰 "경미한 수정 뒤 게재 가능" 지적 반영, 최종 정합 감사 통과). 남은 것: 포스터 초록 docx의 패드 비교 문장 점검, `dynamics_model.md` 4.3·`l2b_actuator.py` docstring의 옛 로드 모드 값(71 Hz → 78~450 Hz 계산값) 갱신, 하네스 `rigid+J2@FL` 2건 실 마찰 방향 확인(선택, 몇 분).
2. 미완(사용자 입력 필요): 저자·소속·사사 자리표시, 미확인 서지 항목(`09_paper/refs/references.md`).
2b. graph-expert 도구 개선(선택): fig_lint가 범주형 축에도 단위를 요구해 "지반 [-]" 같은 라벨이 생김.
3. 포스터(초록 docx + pptx v3).
5. GIF(논문 완료 뒤, 시나리오별, 기존 `render_case_gifs.py` 화면 구성).
6. 나중: compute-scheduler-expert 기록 모드(끝난 작업 실측), dynamics-dev hypothesis 설치(dry-run 먼저).

## 대기 사용자 결정

- **지금은 없다.** (오늘 결정: IMU ≤ 0.118°, H-6 범위 J1·J2·S1, 좌우 방향별 2.64°/2.2°, B5 main 재실행·4.11 한계 문장, 그림 7 하네스 재실행, 이전 판 블록 부록 이동 안 함.)

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
