# 세션 인계

새 세션은 이 문서와 아래 파일로 상태를 파악한다. 이전 대화 맥락은 없다. **아직 아무것도 실행하지 말고, 먼저 상태 확인 결과와 다음 단계 계획을 보고한 뒤 사용자 확인을 받는다.**

- 갱신: 2026-11-06, v5 유압 구현 병합(f91c37b, fast-forward)과 v5 인수 기준 봉인(본·rev1·rev2) 커밋(커밋할 때마다 이 파일을 덮어쓴다. 옛 판은 git 이력).
- 직전 코드 커밋: **f91c37b**(v5 구현 35커밋 병합). 결정 경과 원본은 `decision_log.md` 4절 끝.

## 현재 위치

- 최종 제어기는 `final_C4G2`(명세 433절, 프리셋 기본 켬). 논문 v4 값은 전환 전 제어기(`final_SGS_R4`)다.
- **병합 뒤 Chrono 판정(`06_analysis/02_control/touch_phase/chrono/final_c4g2/final_judgement.md`):** 대표 7행 중 5행 통과(P3-2 FLAG 3, P3-4 FLAG 1), 2행 사전 분류대로 SA-4 안전 정지, 강체 16/16 통과, v4 값보다 나빠진 행 0, 투고 차단 없음. C4G2 이득은 대각·비평면 시작 7행 +8.69~+11.37 kN, 그 밖은 ≤ +0.41 kN, 연약 ±0.23 kN. 이번 행에 SCM 사건 행이 없어 G1 RL 약점의 새 근거는 없다.
- **논문 v4(`09_paper/v4/`, 커밋 안 함):** 44쪽(본문 41쪽), 빌드 오류·경고 0, MANIFEST 84항목 불일치 0, 정합 점검 차단 없음, 범위 문구 수정 끝(CHANGES 22절), `09_paper` 루트를 v4에 맞춤(수정 전 `09_paper/history/20261106_pre_v4_scope_sync/`). **투고처 미정**(사용자). 정해지면 저자·소속·이메일·사사 입력(`main.tex`, `draft/00_front_abstract.md`, `draft/05_conclusion.md`), Word 확인, 재빌드. LaTeX 원본 제출이면 주석의 scratchpad 경로 제거. 정합 점검에서 보지 않은 것: 4절 표 전체 칸 재대조, 그림 내부 글자, Word 표 숫자, 서지 DOI.

## 진행 중: v5 유압 구현 (v4와 병행, 사용자 결정 11-06)

**현재(11-06)**: 구현 병합 완료(B-2 OFF 23행 황금값 일치, B-7 5,615 통과·실패 0, 병합 전 확인 실행 overlap·item8·r67 VB 통과, 정합 점검 차단 0). 기준 `06_analysis/03_hydraulic/coupled/v5/v5_criteria.md`(봉인) + `v5_criteria_rev1.md`(M2-6 2.43 ± 0.25 kN, C-1~10) + `v5_criteria_rev2.md`(M2 잘림은 첫 이륙 뒤만, 잡음 기준 쌍 = master 끔 V0 1,527, n_late·T4h 정의 보충). **다음**: compute-scheduler-expert 배치로 1단계 1,320건 + 잡음 V0 1,527 + Chrono B-4·B-5·LC/M2 비용 probe 동시 시작(사용자 사전 승인, 메모리 `v5-merge-stage1-authorization-20261106`). 잡음 VB 묶음(2단계)은 r79 러너에 이륙 시각 연결(M2 잘림 pre/post) 뒤. 격자 768도 출처가 다르면 V0 768 전체. 병합 전 확인 산출물 `v5/pre_merge_check/`.

명세 `00_docs/02_hydraulic/v5_hydraulic_impl_spec.md`(개정 2 + 11-06 보충). 범위는 유량 포화(기본 끔 유지, D-5 전환 안 함) + 밸브 지연 + M2 + M1c(기본 끔, VN·BL, 식 변경 없이 이식) + 오버랩·닫힘 항 LC(제어기 잠금 창 동반).

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
