# 세션 인계

새 세션은 이 문서와 아래 파일로 상태를 파악한다. 이전 대화 맥락은 없다. **아직 아무것도 실행하지 말고, 먼저 상태 확인 결과와 다음 단계 계획을 보고한 뒤 사용자 확인을 받는다.**

- 갱신: 2026-11-05 01:40, S8 확정 커밋 직전(커밋할 때마다 이 파일을 덮어쓴다. 옛 판은 git 이력).
- 마지막 커밋: **4d0f378**(v4 재확인, TOUCH 후보; 푸시 완료). 결정 경과 원본은 `decision_log.md` 4절 끝.

## 현재 위치

- S9 완료, 최종 제어기(R8 C2 + L1gs + DSb75 + SGS any_loc + R4c30) 프리셋 적용, 논문 `09_paper/v4/` 41쪽(최종 제어기 재확인 값 반영, 커밋 안 함).
- **유압 연성(펌프 유량 포화) 재판정 끝.** 봉인 기준 `00_docs/02_hydraulic/hydraulic_coupling_criteria.md`(SHA-256 `1d743eab…0fd0de`), 판정 `06_analysis/03_hydraulic/coupled/verdict/judgement_chrono/final10_report.md`, `s8off_report.md`, `s8on_report.md`. 10행 중 9행 판정 변화 없음. **토양 S8 크롤러 조항 T-2·F-5 확정**(끔 3/3 통과, 켬 3/3 실패, η_v 0.85, 보상기 공칭, 밸브 지연 없음). D-5 기본 켬 전환 안 함, v5에 한계로 기록. 14행 미재판정.
- **제어기 후보 인수 단계.** C4G2(비틀림 보정 1회 + 출발 벡터 램프)·K1(재발동 2 s 창 안 2표본). 기본 꺼짐, 코드 `worktree-agent-a7f0f4f0aceadde2c`(`74032be` 제어기, `ce21ffa` 재생기). 잠정: C4G2 후보 유지(이득은 강체 쪽만, 토양 S7 이득 없음), K1 조건부(R16 RL 27.2~27.6 kN, J_C 놓침 0 확정; C-S8-41 "새 FLAG 0" 글자대로 미충족, 부상 +0.04~+0.25 s, 강체 격자 통과→실패 1행 1.821 s). 판단 자료 `06_analysis/02_control/touch_phase/chrono/`.

## 진행 중

1. **인수 하네스**(00:19 시작, 재개 가능): E1 `scratchpad\c4g2k1\runner_E1.ps1`(E 16~23, 8워커, D8 → 끔 → 강성 → L3, L4 생략), E2 `runner_E2.ps1`(E 24~27, 4워커, 잡음 L1·L2 1,026건, 약 02:50). 합격 기준 `06_analysis/02_control/touch_phase/acceptance/criteria.md`(잡음 L2 855건 중 실패 ≤ 17, 현행 11). 체크아웃 `scratchpad\cad_c4g2\wt\`(74032be). 판정 `conda run -n dynamics-dev python -I -B scratchpad\c4g2k1\acc_judge.py`. 토양 60행 합격 완료.
2. `grid_r67_main`은 폴더 누락으로 실패했다. E1 뒤 같은 러너를 다시 띄우면 이 스텝만 돈다(`--skip-done`, 폴더는 만들었다).

미병합 브랜치: `worktree-agent-a1212bd2c33c92475`(C2 반환 명령 절단), `worktree-agent-ae9039e69988d5282`(패드 틈 옵션, asym 보고서, 원자료 제외), `worktree-agent-a7f0f4f0aceadde2c`(C4G2·K1, 위 두 코드 커밋 포함). 구동 스크립트 사본 `04_scripts/03_control/touch_phase/{acceptance,chrono_runners}`(scratchpad 경로 의존, 기록용).

## 사전 결정(사용자)

- K1 토양 Chrono: G1 3행(FL F_s 0, FL F_s 8, RR F_s 0) 켬·끔 짝 + 기준 3건(`touch_phase/chrono/next_soil_rows.md`). `grid_r67_main` 재실행 뒤 K1 통과→실패 전체를 보고 시작.
- 잡음 기준 미달이면 원인 분석·후보 안까지만 하고 재설계는 질문. C4G2·K1 채택은 각각 사용자가 결정. 밤사이 자동은 판정·기록·커밋까지이고 master 병합·기본 켬·긴 새 실행은 질문.
- D-5 비교는 전환 조건이 생길 때 C4G2·K1 결정·병합 뒤 최종 제어기로 1회. 현재는 전환 안 함.
- 저자·소속·사사, 투고처는 사용자가 직접 입력. 메인 세션이 채우지 않는다.

## 남은 단계

1. 인수 판정 → K1 토양 Chrono → C4G2·K1 채택 질문.
2. 병합(C2 절단, 패드 틈, 채택 코드, `FINAL_CONTROLLER` 키, 명세 433절), 짧은 Chrono·최종 대표 묶음, 하네스 재실행, CLAUDE.md 기준값 갱신.
3. v4 투고 준비(사용자 입력 뒤, docx Word 확인), 제조사 질문지(Q-M1·M2·M4·M5·M9, 체적 효율), v5 계획(S8 한계, 겹침 사례, S-4 FLAG, 항목 8 지표, 위상 민감 표시, R15 부상 표현). 포스터·GIF는 사용자 지시 때.

## 대기 사용자 결정

- 다음 결정은 C4G2·K1 채택과 K1 토양 Chrono 시작(격자 결과 뒤). v4와 F-5는 투고 유지 + 한계 문장 한 줄 강화로 정해졌다(`decision_log.md`, paper-writing-expert 반영 중).
- 사용자 방침(11-04): 범위 축소는 나중에 정하고 조사 중 나온 문제는 하나씩 푼다. 지금 작업은 시뮬레이션끼리·논문 숫자의 정합이고 실기 정합이 아니다(실측 없음). 크롤러 제하 강성 실측이 C4G2 수치를 정한다(U-R8-9).

## 논문·포스터 (커밋 안 함)

- `09_paper/`는 커밋하지 않는다(`.git/info/exclude`). GIF·MP4도 커밋하지 않는다. 유압 연성은 v5에서 다룬다.
- 논문 작성·교정·빌드는 paper-writing-expert, 리뷰는 paper-reviewer, 데이터 그림은 graph-expert(메인 세션 직접 수정 금지).

## 주의

- 에이전트 지시문에 매번: 셸 heredoc·`python -` 금지, Write로 쓴 파일을 `python -I`로 실행, Bash `find /` 금지, 커밋 메시지는 `git commit -F <파일>`.
- Python·pytest·긴 명령은 **PowerShell 도구**로 실행한다(Bash 도구 자식 Suspended 멈춤 회피).
- 모든 서브 프로세스는 **compute-scheduler-expert 배치**를 받은 뒤 띄운다(비용 측정만 단독).
- 15분 이상 작업은 long-running-task-monitor 주기 점검. 세션 cron은 새 세션으로 이어지지 않는다.
- 주요 작업 중간마다 커밋한다. **커밋 전 integrity-checker를 먼저** 돌리고, 이상 없을 때만 커밋·푸시한다. 커밋마다 이 문서를 갱신해 같은 커밋에 넣는다. `git add -A`와 `touch_phase/` 통째 추가 금지(진행 중 `acceptance/`, 0바이트 `*_C4.jsonl` 포함).
- 장시간 배치는 WMI로 세션과 분리하고 창마다 제목·안내 문구를 붙인다(`pwsh`는 `(Get-Process -Id $PID).Path` 실경로로, WindowsApps 별칭은 WMI에서 실패). Suspended 프로세스는 ResumeThread 자동 조치 뒤 사후 보고, 시뮬레이션·실행기는 자동 종료 금지.
- S단계 본 판정 실행 전에는 사용자에게 알리고 확인받는다. 사용자 결정 사항은 그때마다 메시지 박스(AskUserQuestion)로 묻는다.
- Windows Update는 11-09까지 일시 중지(사용자 설정).
- 알려진 경미 항목: `04_scripts/04_hydraulic/coupled/test_harness_flow.py:40` `=[` 공백(스타일, 미수정), `04_scripts/03_control/r8d1/r8d1_td.py:24` 메인 트리 경로 하드코딩(인수는 가드로 막음, python-expert 수정 대상).
