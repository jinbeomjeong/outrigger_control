# 세션 인계

새 세션은 이 문서와 아래 파일로 상태를 파악한다. 이전 대화 맥락은 없다. **아직 아무것도 실행하지 말고, 먼저 상태 확인 결과와 다음 단계 계획을 보고한 뒤 사용자 확인을 받는다.**

- 갱신: 2026-11-04 밤, v4 재확인·C4G1 중간 커밋 직전(커밋할 때마다 이 파일을 덮어쓴다. 옛 판은 git 이력).
- 마지막 커밋: **dfa1c17**(10행 판정, S8 미확정; 푸시 완료). 결정 경과 원본은 `decision_log.md` 4절 끝.

## 현재 위치

- S9 완료, 최종 제어기(R8 C2 + L1gs + DSb75 + SGS any_loc + R4c30) 프리셋 적용, 논문 `09_paper/v4/` 41쪽 스냅숏.
- 지금은 **유압 연성(펌프 유량 포화) 기여도 평가의 Chrono 재판정 단계**다. 봉인 기준 `00_docs/02_hydraulic/hydraulic_coupling_criteria.md`(SHA-256 `1d743eab…0fd0de`, LF 기준), 판정 `06_analysis/03_hydraulic/coupled/verdict/judgement_chrono/final10_report.md`.
- 10행(η_v 0.85) 중 9행 판정 변화 없음. **토양 S8만 미확정**: 조항 "정지 뒤 크롤러 하중 ≤ 정지 때 + 0.01 W"가 켬 실패(5.15 → 10.43 kN, 한계 8.95), 끔 통과(7.79 → 9.56 kN). T-2·F-5 후보, D-5 기본 켬 전환 보류. 물리 판정: 재접촉이 아니라 계속 접촉, 기준 표본은 약 1.75 Hz 진동 상승 구간이라 불안정, 안전 문제 근거 없음, 유량 효과 근거도 위상 증명도 없음.

## 진행 중

1. **S8 유량 끔 위상 변형 2건**(18:51 시작, 건당 9,200~14,876 s, 예상 21:25~23:00): `07_results/S9/batch_s8off_eps1e-3_20261104`, `batch_s8off_eps2e-3_20261104`. 러너·래퍼 `scratchpad\cad_s8_off\`(세션 임시, `run_s8_eps.py`, `S9Engine.apply_command` 런타임 교체, 첫 접촉까지 속도 (1 − ε)배). ε = 0은 저장 끔과 t = 12 s까지 비트 동일. 샘플러는 부모 `job_exec.py`에 붙었다(자식 합산 여부 미확인).
2. **C4G1 토양 S7**(21:25 시작, 약 2.6~4 h): 고정 체크아웃 15176d1(`scratchpad\cad_c4g1\wt\`), 러너 `scratchpad\cad_c4g1\runner_S7.ps1`, 출력 `07_results/S8/c4g1_S7_20261104/`. 값 추출 `scratchpad\cad_c4g1\metrics.py s7 <폴더>`.
3. **C4G1 강체 4건 판정과 G2 두 가지 판단**(control-expert, `06_analysis/02_control/touch_phase/chrono/`).
4. **v4 교정**(paper-writing-expert, docx 표 셀 앞 숫자 소실 수정, 재READY 조건 표기, 결론 표시; 09_paper, 커밋 안 함).

코드: `182f8d9`(K1·G2·보정 종료, 기본 꺼짐), `15176d1`(C4G1), 모두 브랜치 `worktree-agent-a7f0f4f0aceadde2c`.
미병합 브랜치: `worktree-agent-a1212bd2c33c92475`(C2 반환 명령 절단), `worktree-agent-ae9039e69988d5282`(패드 틈 옵션, asym 보고서, 원자료 제외), `worktree-agent-a7f0f4f0aceadde2c`(C4G1·K1, 위 두 코드 커밋을 합친 위에 얹음).

## 사전 결정(결과 전, 사용자 2026-11-04)

- S8 끔 2건 중 하나라도 조항 실패 → 포화 귀속이 깨져 뒤집힘으로 세지 않고 조항 한계로 기록.
- 둘 다 통과 → 같은 래퍼로 켬 위상 변형 2건 추가(건당 2.6~4.1 h).
- C2 절단 병합, 짧은 Chrono, 절단 재실행 하네스 118행(34 + 79 + x426 5행), D-5 비교(이와 별개로 하네스 24행 + 강체·토양 짧은 Chrono)는 TOUCH 결정 뒤 시작. C4G1은 구현 → 하네스 회귀 → Chrono → 채택 재판단 순서이고, 채택 판단 전까지 긴 실행은 시작하지 않는다. Chrono: 강체 4건(R9 mirror2 2위상, R9 대칭, R4) 끝, S7 진행, K1 뒤 R16 2위상·R12·R16 C4G1 단독·R15. v4는 S8 확정 뒤 현행 제어기로 투고하고 C4G1·K1·유압 연성은 v5.
- 항목 9 `sampling_only` 일화는 F-2 놓침 집계에서 빼고 기록 행으로.

## 남은 단계

1. S8 판정 확정, 10행 결론과 기여도 문구.
2. C4G1 하네스 회귀, Chrono 대표(R9 mirror2 2위상·대칭, R4, R16 mirror2 2위상, R12, 토양 1행), 채택 판단.
3. 병합(C2 절단, 패드 틈, `FINAL_CONTROLLER` 키, 명세 433절), 짧은 Chrono, 하네스 재실행, D-5(10행 실패 없고 해시가 맞을 때만 자동), CLAUDE.md 기준값 갱신.
4. 재판정 뒤: v4 투고 준비(저자·소속·사사, 투고처, docx Word 확인), 제조사 질문지(Q-M1·M2·M4·M5·M9, 체적 효율), v5 계획(겹침 사례, S-4 FLAG, 항목 8 지표, 위상 민감 표시, 축소 모델 δF 사용 범위). 포스터·GIF는 사용자 지시 때.

## 대기 사용자 결정

- 다음 결정은 G2 Δu 정의·종료 래치(control-expert 판단 뒤), S8 끔 결과, C4G1·K1 채택에서 나온다. v4 투고 전에 저자·소속·사사, 투고처를 사용자에게 받는다.
- 사용자 방침(11-04): 범위 축소는 나중에 정하고, 조사 중 나온 문제는 하나씩 푼다. 지금 작업은 시뮬레이션끼리·논문 숫자의 정합이고 실기 정합이 아니다(실측 없음).

## 논문·포스터 (커밋 안 함)

- `09_paper/`는 커밋하지 않는다(`.git/info/exclude`). GIF·MP4도 커밋하지 않는다. 유압 연성은 v5에서 다룬다.
- 논문 작성·교정·빌드는 paper-writing-expert, 리뷰는 paper-reviewer(메인 세션 직접 수정 금지).

## 주의

- 에이전트 지시문에 매번: 셸 heredoc·`python -` 금지, Write로 쓴 파일을 `python -I`로 실행, Bash `find /` 금지, 커밋 메시지는 `git commit -F <파일>`.
- Python·pytest·긴 명령은 **PowerShell 도구**로 실행한다(Bash 도구 자식 Suspended 멈춤 회피).
- 모든 서브 프로세스는 **compute-scheduler-expert 배치**를 받은 뒤 띄운다(비용 측정만 단독).
- 15분 이상 작업은 long-running-task-monitor 주기 점검. 예상 종료 시각과 근거를 받는다. 세션 cron은 새 세션으로 이어지지 않는다.
- 주요 작업 중간마다 커밋한다. **커밋 전 integrity-checker를 먼저** 돌리고, 이상 없을 때만 커밋·푸시한다. 커밋마다 이 문서를 갱신해 같은 커밋에 넣는다.
- 장시간 배치는 WMI로 세션과 분리하고 창마다 제목·안내 문구를 붙인다(`pwsh`는 `(Get-Process -Id $PID).Path` 실경로로, WindowsApps 별칭은 WMI에서 실패). Suspended 프로세스는 ResumeThread 자동 조치 뒤 사후 보고, 시뮬레이션·실행기는 자동 종료 금지.
- S단계 본 판정 실행 전에는 사용자에게 알리고 확인받는다.
- Windows Update는 11-09까지 일시 중지(사용자 설정). 11-04 18:22부터 `TiWorker`가 돌았으나 재부팅 대기 표시는 없었다.
- 사용자 결정 사항은 그때마다 메시지 박스(AskUserQuestion)로 묻는다.
- 알려진 경미 항목: `04_scripts/04_hydraulic/coupled/test_harness_flow.py:40` `=[` 공백(스타일, 미수정).
