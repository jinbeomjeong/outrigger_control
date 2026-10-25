# 세션 인계

새 세션은 이 문서와 아래 파일로 상태를 파악한다. 이전 대화 맥락은 없다. **아직 아무것도 실행하지 말고, 먼저 상태 확인 결과와 다음 단계 계획을 보고한 뒤 사용자 확인을 받는다.**

- 갱신: 2026-10-26 01:05 (커밋할 때마다 이 파일을 덮어쓴다. 옛 판은 git 이력)
- 마지막 커밋: 이 파일을 담은 커밋(`git log -1`, R1 완료·S9 결정 기록). 그 전 단계 커밋은 8616be9(YAML 묶음 1~6단계)

## 현재 위치

- S8 완료(U-S8-58). 지금은 **S9 착수 전 작업**이다. 근거: `00_docs/00_roadmap.md` 1절·6절 1항.
- 착수 전 작업 세 가지 중 C2 토양 대응 설계(control 개정 57, 커밋 3fc758b)와 SCM 패드 수평 구속(dynamics 개정 47, 커밋 004107c)은 끝났다. YAML 재생성 묶음(명세 `00_docs/00_cad/yaml_regen_bundle_2026-10-25.md`)은 1~6단계와 R0가 끝났다(커밋 8616be9).
- S9 사용자 결정 11건 확정(2026-10-26, 모두 권고안): U-S9L-1~5(`dynamics_model.md` 5.33.10), U-S9-C1~C6(`s6_control_spec.md` 286절). 기록은 `decision_log.md`.

## 진행 중 작업 (이 판 작성 시점)

| 작업 | 담당 | 위치 | 상태 확인 |
|---|---|---|---|
| ✅ 회귀 R1(스냅숏 37개) | cad-expert | 배치 `07_results/params_bundle_R1_20261026_001438/` | **완료(00:57)**: 36/37 비트 동일, RRpre(`states_L1R/S6_crawler_top_flat_RRpre`) 1건은 사용자 승인 예외(묶음과 무관한 10-22 이후 코드 변경 탓, 근거 `diag_rrpre_oldyaml/exception_RRpre.json`). 새 스냅숏 설치(`install.json`), 옛 보관본 `07_results/states/history/params_bundle_2026-10-25/`, chrono 시험 265 통과, 동등성 `06_analysis/01_chrono/00_conventions/params_bundle_2026-10-25_equivalence.json` |
| 회귀 R2(index 102사례 = 명세 96 + S4_energy 6) | cad-expert | 메인 트리, 배치 `07_results/params_bundle_R2_<시각>/` | `progress.log` END 줄 identical 값. 요약 판정 표는 스크래치로 다시 만들어 비교(덮어쓰지 않음). R2 도구는 R1 배치 `tools/` 재사용 |
| C2 토양 대응 구현 P-S9-1~10, `test_c2_soil.py`, 회귀 P-S9-9 | python-expert | worktree `.claude/worktrees/agent-a21e7da9d589ffc9b`, 브랜치 `worktree-agent-a21e7da9d589ffc9b` | 브랜치에 커밋 db3e9b4(00:56, "off by default"). 회귀 P-S9-9·R8 기본 켜기 완결 여부는 에이전트 리포트로 확인 |
| `GroundBushingCoulomb` 부착력 인자, S9 실행기 본체(`run_S9.py`, `scm_engine.py`, `scm_model.py`), 스모크 1건 | cad-expert | worktree `.claude/worktrees/agent-ac4ca09081d79438a`, 브랜치 `worktree-agent-ac4ca09081d79438a` | 아직 미커밋 변경(`git -C <wt> status`) |
| RRpre 원인 추적(10-22 이후 커밋 bisect, 코드 수정 없음, PS-7a 영향 목록) | python-expert | worktree `.claude/worktrees/agent-ad53ae05f03708a30`, 브랜치 `worktree-agent-ad53ae05f03708a30` | 결과는 리포트(파일 미커밋일 수 있음). 영향: `07_results/S6/stage2_L1R_20261022_120926/PS7*`는 현재 코드로 재현 안 됨 |

- 세션이 끊기면 백그라운드 에이전트는 사라진다. 디스크(로그·브랜치 커밋·worktree의 미커밋 변경)로 어디까지 됐는지 판단하고, 반쯤 쓴 파일이 없는지 먼저 본다.
- worktree 두 개는 **R3이 끝난 뒤** 메인에 합친다. 그 전에 메인의 `03_src`·`c2.py`를 고치면 R2·R3 비트 비교가 깨진다.

## 남은 단계

1. 회귀 R1 ✅ → R2(102사례, 약 30~40분, 진행 중) → R3(S7·S8 94사례, 약 1.4~1.6시간). 명세 7절. 비트 차이가 나면 멈추고 보고(원인 후보는 소비 코드, python-expert). 결과는 동등성 JSON의 `regressions.R2`·`R3`에 모은다. 명세 정정 거리: 5.1 표 states_L1R S6 소계 25 → 26(top 13 → 14), 7절 R2 96 → 102(S4_energy 6 누락).
2. 묶음 8단계 문서 갱신: decision_log 실행 완료 줄, CLAUDE.md M-1(YAML `sensors` 주석 서술), 로드맵, 명세 머리말(3행 "아직 바꾸지 않음"·5행 SHA·108행 표 SHA가 낡음), rev48 초안 3절 153행·4절 상태, `dynamics_model.md` 5.30.5·5.30.8, `cad_cylinder_vs_drawing.md` 6절. `l2_hydraulic_model_spec.md` 머리말은 이미 갱신됨.
3. 결정 반영 문서: `dynamics_model.md` 5.33.10과 `s6_control_spec.md` 286절의 "사용자 결정 필요"를 확정으로(각 담당 에이전트), 로드맵 S9 준비 항목.
4. RRpre 원인 추적 결과를 보고 PS-7a 계열 재실행 여부를 control·dynamics에 판정받는다.
5. worktree 구현 브랜치 두 개(C2 토양 대응, S9 실행기) 합치기 → 무결성 점검 → 커밋·푸시. C2 토양 대응을 R8 기본으로 켜면 기존 S6~S8 결과 해시가 바뀌는지 확인.
6. dynamics-expert 검토(`s6_control_spec.md` 287절): 축소 하네스 크롤러 근사·패드 R 결합, P3 이탈 뒤 탐침 침하(J1 A 전방 +7 mm) 물리 판정, 5.31.11 연결.
7. S9 계획을 사용자에게 보고하고 확인을 받은 뒤 본 판정 시작: 착수 전 점검 1~6, 패드/로드 분리, P1 단일 패드 비용·격자, V16, 제어 ④(P3a 4사례, P3b 12사례). 로드맵 4절 S9.

## 작업 규칙 (이 프로젝트 메모리에 있음)

- 긴 단계를 마칠 때마다 integrity-checker → 이상 없으면 단계 단위 커밋·`origin/master` 푸시(상시 승인). **커밋마다 이 인계 문서를 갱신해 같은 커밋에 넣는다.**
- 예상 15분 이상 작업은 long-running-task-monitor 주기 점검(약 12~15분 간격 cron). 프로세스 종료 등 조치는 사용자 승인 뒤.
- 에이전트 지시문에 매번: 셸 heredoc·`python -` 금지, Write로 쓴 파일을 `python -I`로 실행.
- 디스크 전체 `find /` 금지(옛 세션에서 40분 폭주). 세션이 멈추면 메모리 `suspended-git-stall`, `no-heredoc-python-stdin` 참고.
- S단계 본 판정 실행 전에는 사용자에게 알리고 확인받는다.
