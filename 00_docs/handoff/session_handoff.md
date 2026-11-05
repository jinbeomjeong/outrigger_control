# 세션 인계

새 세션은 이 문서와 아래 파일로 상태를 파악한다. 이전 대화 맥락은 없다. **아직 아무것도 실행하지 말고, 먼저 상태 확인 결과와 다음 단계 계획을 보고한 뒤 사용자 확인을 받는다.**

- 갱신: 2026-11-05 10:30, v4 범위 문장 반영 뒤 중간 커밋 직전(커밋할 때마다 이 파일을 덮어쓴다. 옛 판은 git 이력).
- 직전 커밋: **9af92b7**(S8 T-2·F-5 확정, C4G2·K1 Chrono 증거; 푸시 완료). 결정 경과 원본은 `decision_log.md` 4절 끝.

## 현재 위치

- S9 완료, 최종 제어기(R8 C2 + L1gs + DSb75 + SGS any_loc + R4c30) 프리셋 적용. 논문 `09_paper/v4/` 42쪽(본문 40쪽), 투고 차단 항목 없음, 저자·소속·사사·투고처 입력 대기(커밋 안 함).
- **유압 연성(펌프 유량 포화):** 10행 중 9행 판정 변화 없음, 토양 S8 크롤러 조항 T-2·F-5 확정, D-5 기본 켬 전환 안 함, v4는 한계 문장, v5에 기록. η_v 0.90·0.925도 실패, 0.95는 제한 0.
- **유압 구현 검토(`06_analysis/03_hydraulic/coupled/pressure_review/`):** 압력 결합·피크 추가 불필요, 큰 빈틈은 M1(체크 열림 지연)·M2(수축 뒤 해제 로드 압력 힘). v5 범위는 유량 포화 + 밸브 지연 + M2, M1은 M1b 결과 뒤 결정. M1 하네스의 G4 값(`m1/`)은 Hopsan 대조(`m1_hopsan/`)에서 규칙 세 개가 달라 **판단 근거로 쓰지 않는다.**
- **제어기 후보 인수:** C4G2·K1, 기본 꺼짐, 코드 `worktree-agent-a7f0f4f0aceadde2c`(`74032be` 제어기, `ce21ffa` 재생기). 인수 자료 `touch_phase/acceptance/`. C4G2 권고 채택(`g8|29` 안전 정지는 알려진 한계로 수용, `acceptance/g8_safe_stop/`), K1 사전 기준 2건 미충족(기록). 채택은 K1 토양 결과와 함께 사용자가 정한다.
- **v4 점검(11-05):** 수치 646칸 불일치 0(표 3·4·5·6·8·9·24, 2·3절 모델 검증 수치 대부분은 미대조). 범위 문장 반영: 저하중 놓침은 F_min 미달 구간 19개(실행 10건), 무작위 기록 44/604(근거 `06_analysis/02_control/paper/ml_jc/`, 명세 434절). 체크 밸브 열림 지연 한계 문장, 2.2절 예외 목록 추가. Word 렌더 확인은 안 함.

## 진행 중

1. **K1 토양 Chrono(9행):** 러너 PID 140876, 08:20 시작, 약 8~16 h, 기준 3건 끝, 사건 6건. 로그 `scratchpad\cad_k1soil\logs\runner.log`, 결과 `07_results\S9\batch_k1soil_G1_20261105\`, 슬롯 2→4, 예약 `scm-K1soil`. 끝나면 값 추출, 항목 9는 `ce21ffa`로 재판정, control-expert 판정, C4G2·K1 채택 질문.
2. **S8 끔 맞춤 2건:** 08:08 시작, 러너 131596·137816, Chrono 133444·139708, 결과 `07_results\S9\batch_s8off169_*`. 끝나면 control-expert가 조항·정지 주기 해석(F-5 기록 유지, 16.9 s가 안 나오면 그대로 적음).
3. **M1b R12·G4 재실행:** control-expert, E 코어, 결과 `pressure_review\m1b\`. 코드 `04_scripts/03_control/m1_check/`와 `pressure_review/m1b/`는 작업 중이라 이번 커밋에 넣지 않고 **다음 커밋에 넣는다**(`pressure_review/m1/` 결과의 코드도 그때 들어간다). 결과로 v5에 M1을 넣을지 질문.

scratchpad 경로: `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad`. 세션 cron은 새 세션으로 이어지지 않는다.

## 사전 결정(사용자)

- K1 토양 뒤 Chrono 3건(edge RL g230 C4G2, rpB RL g230 끔·켬). 앵커 단일 표본 도약·과상승은 별도 과제(기록만).
- 제어기 설계는 M1 때문에 지금 바꾸지 않는다. 제조사 질문지는 1차 28건·2차 37건, 발송은 사용자가 직접 검토 뒤.
- C4G2·K1 채택, master 병합, 기본 켬, 긴 새 실행은 질문. D-5 비교는 전환 조건이 생길 때 C4G2·K1 결정·병합 뒤 1회.
- 저자·소속·사사, 투고처는 사용자가 직접 입력(`main.tex`, `draft/00_front_abstract.md` 뒤 Word 재빌드). LaTeX 원본 제출이 정해지면 주석의 scratchpad 경로 제거.

## 남은 단계

1. K1 토양·S8 끔·M1b 결과 → C4G2·K1 채택과 v5 M1 질문.
2. 병합(C2 절단, 패드 틈, 채택 코드, `FINAL_CONTROLLER` 키, 명세 433절), 짧은 Chrono·최종 대표 묶음(S7 포함), 하네스 재실행, CLAUDE.md 기준값 갱신.
3. v4 투고(사용자 입력, Word 확인), v5 계획(유량 포화·밸브 지연·M2, S8 한계와 정지 주기 겹침, R15 부상 표현, 겹침 사례, S-4 FLAG, 항목 8 지표, 위상 민감 표시). M2 구현은 python-expert. 포스터·GIF는 사용자 지시 때.
4. 정리: compute-scheduler-expert 기록 모드(하네스·S8·S7 실측, `cad_c4g1\runner_S7_logs\c4g1_S7.sample.json`), `r8d1_td.py:24` 경로, `candidates.py:21` 주석·`_limited_increment`.

## 미병합 브랜치

`worktree-agent-a1212bd2c33c92475`(C2 반환 명령 절단), `worktree-agent-ae9039e69988d5282`(패드 틈 옵션, asym 보고서), `worktree-agent-a7f0f4f0aceadde2c`(C4G2·K1). 구동 스크립트 사본 `04_scripts/03_control/touch_phase/{acceptance,chrono_runners}`는 scratchpad 경로 의존(기록용).

## 논문·포스터 (커밋 안 함)

- `09_paper/`는 커밋하지 않는다(`.git/info/exclude`). GIF·MP4·시계열 CSV도 커밋하지 않는다. 근거 스크립트 사본은 `04_scripts/05_paper/v4_evidence/`. 유압 연성은 v5에서 다룬다.
- 논문 작성·교정·빌드는 paper-writing-expert, 리뷰는 paper-reviewer, 데이터 그림은 graph-expert(메인 세션 직접 수정 금지).

## 주의

- 에이전트 지시문에 매번: 셸 heredoc·`python -` 금지, Write로 쓴 파일을 `python -I`로 실행, Bash `find /` 금지, 커밋 메시지는 `git commit -F <파일>`.
- Python·pytest·긴 명령은 **PowerShell 도구**로 실행한다(Bash 도구 자식 Suspended 멈춤 회피).
- 모든 서브 프로세스는 **compute-scheduler-expert 배치**를 받은 뒤 띄운다(비용 측정만 단독).
- 15분 이상 작업은 long-running-task-monitor 주기 점검.
- 주요 작업 중간마다 커밋한다. **커밋 전 integrity-checker를 먼저** 돌리고, 이상 없을 때만 커밋·푸시한다. 커밋마다 이 문서를 갱신해 같은 커밋에 넣는다. `git add -A`와 `touch_phase/` 통째 추가 금지(0바이트 `*_C4.jsonl` 포함).
- 장시간 배치는 WMI로 세션과 분리하고 창마다 제목·안내 문구를 붙인다(`pwsh`는 `(Get-Process -Id $PID).Path` 실경로로, WindowsApps 별칭은 WMI에서 실패). Suspended 프로세스는 ResumeThread 자동 조치 뒤 사후 보고, 시뮬레이션·실행기는 자동 종료 금지.
- S단계 본 판정 실행 전에는 사용자에게 알리고 확인받는다. 사용자 결정 사항은 그때마다 메시지 박스(AskUserQuestion)로 묻는다.
- Windows Update는 11-09까지 일시 중지(사용자 설정).
- 알려진 경미 항목: `04_scripts/04_hydraulic/coupled/test_harness_flow.py:40` `=[` 공백(스타일, 미수정), `ml_jc/ml_jc_miss2.py`·`ml_jc_final.py`의 scratchpad 경로 상수(README에 적음).
