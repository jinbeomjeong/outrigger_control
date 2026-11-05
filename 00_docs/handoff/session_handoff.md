# 세션 인계

새 세션은 이 문서와 아래 파일로 상태를 파악한다. 이전 대화 맥락은 없다. **아직 아무것도 실행하지 말고, 먼저 상태 확인 결과와 다음 단계 계획을 보고한 뒤 사용자 확인을 받는다.**

- 갱신: 2026-11-05 15:30, C4G2 단독 인수 합격 뒤 중간 커밋 직전(커밋할 때마다 이 파일을 덮어쓴다. 옛 판은 git 이력).
- 직전 커밋: **1a9b4e6**(M1b·M1c, S8 끔 맞춤 판정; 푸시 완료). 결정 경과 원본은 `decision_log.md` 4절 끝.

## 현재 위치

- S9 완료. 논문 `09_paper/v4/` 43쪽(본문 40쪽), 최종 정합 점검 투고 차단 없음, 현 제어기(R8 C2 + L1gs + DSb75 + SGS any_loc + R4c30) 값으로 투고. 저자·소속·사사·투고처 입력과 Word 확인 대기(사용자, 커밋 안 함). 수치 646 + 163칸 불일치 0(표 6·24 일부와 4.8.1 패드 B 분리 값은 명세 인용·산술로만 확인).
- **제어기 후보 결론(사용자 11-05): C4G2 채택, K1 탈락.** C4G2 단독 인수 하네스 `touch_phase/acceptance/c4g2_only/judgement_report.md`: `criteria.md` 전 묶음 충족, L2 8/855 CP 1.682 %. 격자 768행은 끔과 해시가 같아 C4G2를 시험하지 못한다. 힘 이득 근거는 Chrono(비평면 5건 `chrono/g8c3/g8c3_judgement.md` +11.2~+13.4 kN). 알려진 한계: `g8|29`(운용 조건 밖, 하네스 유연 크롤러 + F_s 4에서만), 강체 FL F_s 0 FS24·RE1bF 실패 유지(현행과 같음). K1 근거 `chrono/k1soil/k1soil_judgement.md`, `sweep/sweep_judgement.md`. 코드 `worktree-agent-a7f0f4f0aceadde2c`(`74032be`, 켜기 `touch_twist_hold=True`, `ce21ffa` 재생기).
- **유압 연성:** 유량 포화 10행 중 9행 판정 변화 없음, S8 조항 T-2·F-5 확정, 유량과 정지 위상 미분리로 닫음(`judgement_chrono/s8off169_report.md`). 체크 밸브 열림 지연은 M1c(`pressure_review/m1c/`, 단위 기준 미달 상태의 참고 값): R12 ×1은 어느 회로든 F_min 아래, 정상 행 F_min 미달 0, 재충전 없는 환기에서 READY 지연·복귀 실패. 옛 M1·M1b 값은 쓰지 않는다. **모델 수정은 제조사 답까지 멈춘다.** G4는 급침하(2 s), 느린 침하는 SS(미시험).
- SCM 꼬리 진동(FL F_s 8 켬 행 2 Hz)은 격자 노드 스위칭 수치 현상. 감쇠 추정·실기 예측 근거로 쓰지 않는다.

## 진행 중

1. **C4G2 단독 Chrono 1건** `S9EV_G1_FLFs0_RE1bF_d003_C4G2`: 14:31 시작, 러너 PID 168096, P 0x55, 예상 16시쯤. 로그 `scratchpad\cad_k1soil\logs\runner_d003.log`, 결과 `07_results\S9\batch_k1soil_G1_20261105\`, 추출 `scratchpad\cad_k1soil\extract_d003.py`. 끝나면 control-expert 판정. 세션 cron `ae169c13`이 점검한다(새 세션으로 이어지지 않음).

scratchpad: `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad`.

## 사전 결정(사용자)

- **병합(메모리 `c4g2-merge-authorization-20261105`):** 위 Chrono에서 F_min 아래가 확인되지 않으면 master 병합(C2 반환 명령 절단 `a1212bd2…`, 패드 틈 `ae9039e6…`, C4G2, 침하율 창 1.0 s + `window_short` FLAG), 기본 켬, `FINAL_CONTROLLER` 키, 명세 433절, CLAUDE.md 기준값까지 integrity-checker 통과 뒤 자동 진행하고 사후 보고한다. F_min 아래면 멈추고 묻는다. 프리셋 전환 뒤 인수 묶음 해시 재현 필요.
- 병합 뒤 최종 대표 묶음 + S7 Chrono(시작 전 시간 안내). v5는 그 뒤 구현부터(유량 포화·밸브 지연·M2·M1c 기본 끔, 재충전 없는 환기·차단 2종, E2·E4 제외, 인수 행은 decision_log). READY 한계 연약 100 s 유지.
- 제조사 질문지 1차 28건·2차 37건은 발송 시점 미정(사용자가 직접 검토 뒤). 답이 늦으면 v5는 가정 범위로 쓴다. M1c 기본 켬, G4·불감대 대응, 불감대 분리는 답 뒤.
- 앵커 도약·과상승 조사는 채택·병합 뒤. 포스터·GIF는 사용자 지시 때. 저자·소속·사사·투고처는 사용자 입력(`main.tex`, `draft/00_front_abstract.md`, `draft/05_conclusion.md` 뒤 Word 재빌드). LaTeX 원본 제출이 정해지면 주석의 scratchpad 경로 제거.

## 미병합 브랜치

`worktree-agent-a1212bd2c33c92475`(C2 반환 명령 절단), `worktree-agent-ae9039e69988d5282`(패드 틈 옵션), `worktree-agent-a7f0f4f0aceadde2c`(C4G2, K1 코드도 있으나 켜지 않음). 구동 스크립트 사본 `04_scripts/03_control/touch_phase/{acceptance,chrono_runners}`(이번 C4G2 단독·K1 토양 러너 포함)는 scratchpad 경로 의존(기록용).

## 정리

compute-scheduler-expert 기록 모드(하네스·S8·S7·K1 토양·비평면 실측), `r8d1_td.py:24` 경로, `candidates.py:21` 주석·`_limited_increment`, `extract_g8c.py` L2b FR 필드(`s_motor` 대 가드 좌표).

## 논문·포스터 (커밋 안 함)

- `09_paper/`는 커밋하지 않는다(`.git/info/exclude`). GIF·MP4·시계열 CSV도 커밋하지 않는다. 근거 스크립트 사본은 `04_scripts/05_paper/v4_evidence/`, `06_analysis/02_control/paper/ml_jc/`.
- 논문 작성·교정·빌드는 paper-writing-expert, 리뷰는 paper-reviewer, 데이터 그림은 graph-expert(메인 세션 직접 수정 금지).

## 주의

- 에이전트 지시문에 매번: 셸 heredoc·`python -` 금지, Write로 쓴 파일을 `python -I`로 실행, Bash `find /` 금지, 커밋 메시지는 `git commit -F <파일>`.
- Python·pytest·긴 명령은 **PowerShell 도구**로 실행한다(Bash 도구 자식 Suspended 멈춤 회피).
- 모든 서브 프로세스는 **compute-scheduler-expert 배치**를 받은 뒤 띄운다(비용 측정만 단독).
- 15분 이상 작업은 long-running-task-monitor 주기 점검.
- 주요 작업 중간마다 커밋한다. **커밋 전 integrity-checker를 먼저** 돌리고, 이상 없을 때만 커밋·푸시한다. 커밋마다 이 문서를 갱신해 같은 커밋에 넣는다. `git add -A`와 `touch_phase/` 통째 추가 금지(partial, 0바이트 `*_C4.jsonl` 포함).
- 장시간 배치는 WMI로 세션과 분리하고 창마다 제목·안내 문구를 붙인다(`pwsh`는 `(Get-Process -Id $PID).Path` 실경로로). Suspended 프로세스는 ResumeThread 자동 조치 뒤 사후 보고, 시뮬레이션·실행기는 자동 종료 금지.
- S단계 본 판정 실행 전에는 사용자에게 알리고 확인받는다. 사용자 결정 사항은 그때마다 메시지 박스(AskUserQuestion)로 묻는다.
- Windows Update는 11-09까지 일시 중지(사용자 설정).
- 알려진 경미 항목: `04_scripts/04_hydraulic/coupled/test_harness_flow.py:40` `=[` 공백(스타일, 미수정), `ml_jc/ml_jc_miss2.py`·`ml_jc_final.py`·`ml_jc_pads.py`의 scratchpad 경로 상수(README에 적음).
