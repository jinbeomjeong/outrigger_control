# 세션 인계

새 세션은 이 문서와 아래 파일로 상태를 파악한다. 이전 대화 맥락은 없다. **아직 아무것도 실행하지 말고, 먼저 상태 확인 결과와 다음 단계 계획을 보고한 뒤 사용자 확인을 받는다.**

- 갱신: 2026-11-07 아침, v5 1·2단계 r4 재판정 통과(M2 개정 4 `flow_limited_r4`, 기준 개정 5). 3단계(Chrono 25건, D-3) 사용자 결정 대기(커밋할 때마다 이 파일을 덮어쓴다. 옛 판은 git 이력).
- 직전 코드 커밋: **f8c08cc**(M2 개정 4 `flow_limited_r4`, M2-14/14b/14c). 결정 경과 원본은 `decision_log.md` 4절 끝.

## 현재 위치

- 최종 제어기는 `final_C4G2`(명세 433절, 프리셋 기본 켬). 논문 v4 값은 전환 전 제어기(`final_SGS_R4`)다.
- **병합 뒤 Chrono 판정(`06_analysis/02_control/touch_phase/chrono/final_c4g2/final_judgement.md`):** 대표 7행 중 5행 통과(P3-2 FLAG 3, P3-4 FLAG 1), 2행 사전 분류대로 SA-4 안전 정지, 강체 16/16 통과, v4 값보다 나빠진 행 0, 투고 차단 없음. C4G2 이득은 대각·비평면 시작 7행 +8.69~+11.37 kN, 그 밖은 ≤ +0.41 kN, 연약 ±0.23 kN. 이번 행에 SCM 사건 행이 없어 G1 RL 약점의 새 근거는 없다.
- **논문 v4(`09_paper/v4/`, 커밋 안 함):** 44쪽(본문 41쪽), 빌드 오류·경고 0, MANIFEST 84항목 불일치 0, 정합 점검 차단 없음, 범위 문구 수정 끝(CHANGES 22절), `09_paper` 루트를 v4에 맞춤(수정 전 `09_paper/history/20261106_pre_v4_scope_sync/`). **투고처 미정**(사용자). 정해지면 저자·소속·이메일·사사 입력(`main.tex`, `draft/00_front_abstract.md`, `draft/05_conclusion.md`), Word 확인, 재빌드. LaTeX 원본 제출이면 주석의 scratchpad 경로 제거. 정합 점검에서 보지 않은 것: 4절 표 전체 칸 재대조, 그림 내부 글자, Word 표 숫자, 서지 DOI.

## 진행 중: v5 유압 구현 (v4와 병행, 사용자 결정 11-06)

**현재(11-07 아침)**: **1·2단계 통과(r4)**. 2단계 H-10(격자 통과→실패 5행)의 주원인은 M2 r3의 이중 계산(기본 L1-R 해제 킥 1.06 mm에 M2가 같은 몫을 더함)이었고, FS24 F_s 0 READY 계열의 위상 산포는 V0 기준선 약점. 사용자 결정(11-07): P-1 물리 수정 채택(`flow_limited_r4`, ec5eaf8·a8feb1d·1686d56·f8c08cc) + 그 계열 H-10은 위상 분포 규칙. 기준 개정 5 봉인 01:27:42(`945f7146…`, 결과를 본 뒤 바꾼 두 가지를 밝힘). 재실행 01:30~05:06(위상 32 + 격자 768 + 1단계 1,030 + 잡음 1,503). 판정: 위상 분포 FR 3→1·FL 9→11, 격자 VB 실패 87(V0 100)·통과→실패 3행 모두 계열 𝓕·계열 밖 0, 잡음 L2 5/835(CP 1.255 %)·L3 10/501 기록, J8 G4 26~30·R15 44~48, 대체 경로 잠정. r3 결과는 `*_m2r3*`·`m2r3_archive_manifest.json`. **다음**: 3단계 전 사용자 결정 D-3(Chrono 행·시점, 토양 밸브 켬 기준 행, W-6 T4·T5 기록, 권고 기록 행 계열 𝓕 FL δ 0.05/0.075와 잡음 `g8|22`·`g6|56`), L2b는 r4로, 새 규칙은 실행 전 개정 6. 명세 본문의 M2 서술은 개정 4 반영 전(머리 주의 문단). 큰 결과(`main*.jsonl`, `noise_v0/`, `noise_vb*/`)는 로컬 보관.

**이전 경과(11-06)**: **1단계 통과**(`v5/stage1_judgement.md` R절). 첫 판정은 J8 리밋 사이클로 멈춤 → 원인은 M2의 즉시 이동(유량 무관) → M2 개정 3(유량 제한 `flow_limited_r3`, 사용자 결정) → M2 켠 1,030건 재실행(옛 행은 `*_m2r2*`, `m2r2_archive_manifest.json`) → 통과. B-7 5,629 통과·실패 0. 기준: `v5_criteria.md`(봉인) + rev1(M2-6 2.43 ± 0.25, C-1~10) + rev2(M2 잘림 이륙 뒤만, 잡음 기준 쌍 = master 끔 V0, n_late·T4h 정의) + rev3(잡음 1,503건, L2 문턱 16) + rev4(M2 개정 3 사실·M2-1~13·재실행 범위). 잡음 V0 1,503 완료(`v5/noise_v0/`, 커밋 안 함). Chrono B-4·B-5 비트 동일, 비용 probe 6건은 동시 실행으로 오염된 참고값. **진행**: 2단계 실행 종료 19:46(오류 0, cea162f 기준, r79·r67 러너 이륙 시각·n_late 연결 7a2898f·cea162f). 격자 V0 표본 8작업 해시 일치 → V0 768 생략. 잡음 L1 게이트 통과, L2 9/835(CP 1.873 %, 허용 16) 통과, L3 12/501 기록(V0 12/501), 대체 L3 133건 잠정. 격자는 VB 실패 61(V0 100), 통과→실패 5행(실행 3건, 모두 강체 상단 F_s 0 READY FS24, 관문 Fmin_after_W만, FAULT 0). 사용자 결정(11-06): H-10은 조건부 수용이 아니라 멈추고 원인 분리 중(control-expert: M2·LC·유량·τ_v·F_s·촘촘한 위상, 기준·코드 변경 없음). 3단계(Chrono 25건, D-3) 보류. 판정서 `v5/stage2_judgement.md`. **다음**: H-10 원인 분리 결과 확인 → 대응 결정 → 3단계 D-3. 큰 결과 파일(`main*.jsonl`, `noise_v0/`, `noise_vb/`)은 로컬 보관(`.git/info/exclude`).

명세 `00_docs/02_hydraulic/v5_hydraulic_impl_spec.md`(개정 3). 유압 그림 `00_docs/02_hydraulic/figures/`(1 범위, 2 목적, 3 블록, 4 ISO 1219 회로도; 명세 `hydraulic_model_figspec.md`). 범위는 유량 포화(기본 끔 유지, D-5 전환 안 함) + 밸브 지연 + M2 + M1c(기본 끔, VN·BL, 식 변경 없이 이식) + 오버랩·닫힘 항 LC(제어기 잠금 창 동반).

- 결정: D-1 LC 넣음(권고와 다름, 제어기 변경 동반), D-2 M1c $p_r$ 그대로·한계 기록, D-3 Chrono는 하네스 판정 뒤, D-4 M2 양방향, D-5 기준 구성 $\eta_v$ 0.85, D-6 BL + LC 거부.
- 조합: 모두 끔 = `final_C4G2` 비트 동일 대상, 플랜트만 = 비교용, 제어기만 = 금지, 둘 다 = v5 기준 구성(VB).
- 순서: control-expert Q-1~Q-6 답·기준 초안(`06_analysis/03_hydraulic/coupled/v5/v5_criteria_draft.md`, 진행 중) → 미룬 판정 항목 8개 사용자 결정 → python-expert 커밋 13개(커밋 7만 Q-1 답 필요, 커밋 12·13은 커밋 7 뒤에 끝남; 첫 커밋에서 scratchpad `hyd_review/{common,four_leg,m2_check}.py`를 저장소로 옮김) → 기준 봉인 → compute-scheduler-expert 배치 → 하네스 약 1,200건 → Chrono 행 결정.
- 그 뒤: G1 RL 약점 대응 설계, 앵커 도약·과상승 조사, 논문 v5.
- 제조사 답 뒤: M1c 기본 켬, G4·불감대 대응, BL + LC 재검토. 질문지 1차 28건·2차 37건은 발송 시점 미정(사용자가 직접). 포스터·GIF 보류.

scratchpad: `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad`.

## 미병합 브랜치

코드는 모두 master에 병합됨. 남은 것은 `worktree-agent-ae9039e69988d5282`의 코드 뒤 커밋 `02efc57`(R16 asym 보고서·원자료, master에 없는 파일 21개)뿐이다.

## 정리

compute-scheduler-expert 기록 모드(하네스·S8·K1 토양·비평면·대표·강체 실측, `batch.json`), worktree `.claude/worktrees/merge-c4g2`·scratchpad `cad_finalC4/wt` 제거(`git -c core.longpaths=true worktree remove --force`), `r8d1_td.py:24` 경로, `candidates.py:21` 주석·`_limited_increment`, `extract_g8c.py` L2b FR 필드(`s_motor` 대 가드 좌표), 명세 433.7(`final_judgement.md` 7절)·434.9(`phase_judgement.md`) 제안 반영 여부.

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
