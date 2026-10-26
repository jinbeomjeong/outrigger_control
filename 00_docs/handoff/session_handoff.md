# 세션 인계

새 세션은 이 문서와 아래 파일로 상태를 파악한다. 이전 대화 맥락은 없다. **아직 아무것도 실행하지 말고, 먼저 상태 확인 결과와 다음 단계 계획을 보고한 뒤 사용자 확인을 받는다.**

- 갱신: 2026-10-26 (커밋할 때마다 이 파일을 덮어쓴다. 옛 판은 git 이력).
- 마지막 커밋: 이 파일을 담은 커밋(`git log -1`, **S9 P3b 실행기 정리 + YAML 묶음 8단계 문서**). 그 전: 88d8d9b(S9 merge), 25caf20(명세 개정 61·P3a 판정 기록), 762b4f3(C2 merge), b8f5b1d(R3 완료), 8616be9(YAML 묶음 1~6단계)
- 세션 기록: 일반 Windows 터미널에서 `claude`를 직접 실행한다(2026-10-26 결정). 이번 세션(f556fe97…)은 transcript가 정상 저장됐다.

## 현재 위치

- S8 완료(U-S8-58). **S9 본 판정 중**: P1·P2·P2′·P3a 끝(dynamics 개정 50·51·52). **P3b 실행 승인됨(U-S9P-6 (가)), 실행기 준비 끝, 센서·C2 구성 확정 대기.** 근거: `00_docs/00_roadmap.md` 1절·6절 1항.
- YAML 재생성 묶음: 1~6단계·R0~R3·**8단계 문서 끝**(2026-10-26, 명세 `00_docs/00_cad/yaml_regen_bundle_2026-10-25.md` 7.1·8절). 묶음 탓 차이 0.
- worktree 두 개(C2·S9)는 지웠다(브랜치는 남김). 원자료는 메인 `07_results/S9/`(P1~P3a, 30개 폴더)와 `07_results/S9_merge/`(C2 worktree에 있던 1.1 GB)로 옮겼다.

## 이번 커밋에서 바뀐 것

- `run_S9.py level`: 가드는 `config.soil.enable` 검사(`--allow-current-c2`로만 우회). 결과에 `c2_setup`·`c2_soil`·`c2_lifted_reapproach` 기록. 새 인자 `--fs-kN`(플랜트 실 마찰 재정의), `--case`·`--out-root`, `--imu-grade`(기본 `ideal`, 옛 기본 `"G2"`는 없는 이름이었다). 계산 비용(wall, µs/step) 기록. `--threads 4` 기본.
- 요약 키(공통 함수): `mask_track_utilisation`(정착 법선 5 % 미만 NaN), `crawler_departure`(P3a-2 규칙), `creep_stop`(0.2 s 후향 침하 속도 < 0.1 mm/s), `pre_liftoff_min_force`. P3a 요약에도 적용 → P3a-10 `track_utilisation_max_lift`는 이제 마스크 값(옛 값은 `_unmasked`).
- 기록: 1 ms `step_series.npz`(사례당 약 22 MB), 10 Hz 287절 키, `p3b` 블록(P3-1~6·8·9; **P3-7은 control이 계열로 산출**), W-61-1~4 감시(`w61_watch`, 기록·경고만).
- P3b 묶음 26건(`s9_batch.py`): RE1c 양성 2건(`run_S8C.py` L2b-NSC 강체 바닥, `with_10hz_d1()`, 재접근 10 s 한계, 사용자 결정 2026-10-26) 먼저, 그다음 SCM 24건. `s9_batch`가 S8C 사례 로그를 검사해 실패를 rc 4로 잡는다(`s8c_case_check`). `run_S8C.py`에 `--tag`.
- 시험(커밋 직전 재실행): unit 2301 통과·7 건너뜀·0 실패, chrono(not slow) 285 통과.
- 문서: CLAUDE.md M-1·패드 줄, 묶음 명세 머리말·5.1·5.2·7·7.1·8절, 로드맵 1·4·6절(S9 4/6, 합계 63/67), `chrono_build_plan.md` S9 체크, rev48 초안 상태, `dynamics_model.md` 5.30.5·5.30.8, `cad_cylinder_vs_drawing.md` 6절.

## 남은 단계 (P3b 시작 전)

0. **(끝남, 이번 커밋)** 센서·C2 구성 확정과 실행기 반영. 사용자 결정 U-S9P-9~12(decision_log 5절): 압력·행정 WIKA 정상 + 영점 교정, IMU ideal + 0.04° 기록만, **실행 길이 120 s 고정**(끝내기 규칙 아님). 명세 개정 61 보완 2(284.1·305.2절). 실행기 새 기본: `--pressure-grade normal --imu-grade ideal --seed 20261026 --duration 120`, P3-4 창 `p34_judgement_window`, `reapproach_limit_records`, RE1c 요약 `re1c_summary`. 건별 예상 G1·S1 5800 s, J1·J2 11500 s, 26건 직렬 합 208,561 s(약 57.9 h; 4병렬 약 15~16 h, 경합 측정 외삽). FAULT/IDLE 조기 정지는 넣지 않았다. 새 `level` 경로는 단위 시험뿐이고 실제 실행은 스모크가 처음이다. 시험 unit 2307 통과·7 건너뜀, chrono 285 통과.
1. (아래는 결정 전 기록) **센서·C2 구성 확정**: control-expert 권고가 나왔다(2026-10-26) — IMU `ideal`, 압력·행정 WIKA 정상 등급 + CHECK 영점 교정(U71), 시드 20261026 공통, C2 `with_10hz_d1()` 그대로, 90 s 고정 대신 끝내기 규칙(마지막 READY 15 s + 양방향 크리프 정지 5 s, 상한 150 s), P3-4 창 = [max(양방향 크리프 정지, 마지막 READY), 끝] ≥ 5 s, RE1c 합격 R-1~R-5, SCM에서 재접근 시간 한계 발동은 FLAG. 실행기 반영 D-1~D-5(cad-expert). **사용자 확인 3건 대기**: 압력 센서 정상 등급 전환, 이상 IMU 잔차 0.04° 예산 대응값을 기록/판정 중 무엇으로, 끝내기 규칙·상한 150 s. 명세 284.1절 문안 초안은 control 리포트에 있다(반영 시 명세 개정에 넣는다).
2. **스모크 1건 + 단독 비용 측정**(다른 계산과 겹치지 않게, 계획은 cpu-scheduler-expert): P코어 1건, E코어 1건 실행 시간, 건당 최대 메모리, 4·2스레드 비교 → cpu-scheduler-expert가 26건 + P3-10 배치 결정, P3b 시간 재추정. 스모크 확인: 영점 교정 `sensors.zero_calibration.all_calibrated`, `pressure_error_terms`·시드, `record/record.npz` 10 Hz 판독·`controller_commands.npz`, `checks`의 P3-4·재접근 한계 키, C2 soil 블록, µs/step·RSS.
2a. **P3-10**: L1 강체 2사례(평지·rpB, 상단) 토양 대응 켬/끔 SHA 비교(P3b 묶음 밖, 개정 60 판정 전). 같은 쌍은 M-3(089bfd5, 명세 285절)에서 이미 동일 확인됐지만 그 뒤 C2 merge·개정 59~61이 있어 현 코드로 다시 확인한다: `s9_batch.py run P3-10 --parallel 2`(4건, `m3_run.py` 재사용, 건별 600 s 가정) → `s9_batch_summary.py P3-10 <폴더>`.
3. (끝남) 명세 284·284.1·285·301·305.2절, decision_log U-S9P-9~12.

## P3b (승인됨)

- 실행: `python.exe -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run P3b --parallel <N>`(P 전용) 또는 P/E 두 풀 `--parallel-p <N> --parallel-e <M> --e-cases <사례...> --order lpt`, cpu-scheduler-expert 배치는 `--schedule plan.json`(키 `e_cases`·`order`·`order_cases`·`parallel_p`·`parallel_e`). 사례 프로세스 배치는 환경 변수 `OUTRIGGER_PLACEMENT`(`pcore`/`ecore`), RE1c·P3-10 행은 P코어 고정이라 E 풀 불가. → `s9_batch_summary.py P3b 07_results/S9/batch_P3b_<stamp>`. RE1c 결과는 `07_results/S8/p3b_N_RE1c_*`.
- 24건: G1 10(A·B × 오거 3 × F_s 4 kN + 상단 F_s 0·8 kN × A·B) → J1 10(같은 구성, 패드 1 cm) → J2·S1 각 A·B 상단 4 kN 4. 격자 G1·S1 패드 2 cm, J1·J2 1 cm, 크롤러 4 cm, 감쇠기 정착 8 s, 루프 120 s 고정(U-S9P-12). 건별 예상 G1·S1 5800 s, J1·J2 11500 s(개정 52 상한 스텝 비용 × 1.28×10⁶ 스텝). 센서·C2 구성은 명세 284.1절.
- 판정: **주 판정은 정상상태 끝 자세 ±0.2°**(크리프 정지 뒤 창) + control 284절 P3-1~10. J1·J2 보완 4개 항(U-S9P-7). 0.03° 기준들은 기록. 탐침 한도 0.1°(E7)는 별개.
- 30분 넘으므로 long-running-task-monitor 주기 점검(약 15분 cron).
- 끝나면 control·dynamics 판정 → 명세 개정 60(306절~), J1·J2 해석 보완 P3-3·5·7·8/9 포함.

## 논문 초안 (커밋 안 함)

- `09_paper/`(LaTeX `latex/build.ps1`, MiKTeX xelatex→bibtex→xelatex×2, PDF·docx 변환본, 원고 `draft/*.md`, 그림 `figures/`, 참고문헌 `refs/`)는 **커밋하지 않는다**(사용자 2026-10-26, `.git/info/exclude`). 본문 약 9.2쪽(사용자가 분량 유지 결정). P3b 판정 뒤 4.4절·그림 7(`figures/scripts/fig7_p3b.py`)·초록·결론 TBD를 채운다.
- 논문 점검에서 나온 원본 문서 쪽 정정(P3b 판정 때 dynamics 개정 53에서): `dynamics_model.md` 5.37.1 P3a-7 Δroll/Δpitch가 `s9_P3a_summary.json` `d_roll_pitch_end_deg`와 다름(J1 A −0.003 대 −0.011 등) — 정본 결정. D2 Δt 비교 정의(끝 침하 0.0049 %, 자세 7.1×10⁻⁶°로 재계산됨) 정리.
- 원고 리뷰는 프로젝트 에이전트 `paper-reviewer`(`.claude/agents/paper-reviewer.md`, opus·effort medium, 읽기 전용, 결과는 응답으로만)에 맡긴다(2026-10-26). 새 세션부터 인식된다. 첫 시험은 "`draft/00_front_abstract.md` 초록만 리뷰".

## P3b 뒤

- P-S8-22(R-5 대체 다리 기울기, U-S8-60~62) 구현(python, 명세 304절) → V-1~V-5 → cad V-4 → hydraulics H-61-1(R_hi 확정).
- ✅(2026-10-26, P3b 실행 중 미리 함) dynamics `dynamics_model.md` 개정 54: 5.12.13 L1-R 잠김 강성 대표 범위(U-S8-63: 수준은 대표, 변화율 −Δp_r/Δp_h·G는 대표 못 함 → L1-R의 R-5·`lock_load_regain`은 실기 근거 아님), 5.30.10 rev48 YAML 묶음 초안 합침. **개정 53은 P3b 판정(5.37.10 착수 전 점검 1~6 종결 포함)용으로 비워 둠** — 넣을 때 머리말·개정표 순서를 맞춘다. hydraulics H-61-1은 5.12.13 표를 출발값으로 쓴다.
- 🔄 **P-S8-22는 worktree 구현, P3b 뒤 merge**: worktree `.claude/worktrees/agent-a42ab63c487597861`, 브랜치 `worktree-agent-a42ab63c487597861`, 커밋 d7638e9(①~⑤) + 88625da(O-1~O-3), cad C-1(L1 `plant_meta` 분기, `03_src/outrigger_sim/chrono/fallback_ratio.py`, run_S6C 등) 미커밋, python O-4(V-2 재생 관문·탐침 다리 출처·L̂_true)와 cad 후속(meta 키·환경 변수 거부·10 Hz `probed_leg` 기록) 진행 중. 메인 `03_src`·`04_scripts`를 바꾸면 대기 중 P3b 사례가 새 코드를 불러오므로 merge는 P3b 뒤. merge 뒤: V-3 축소 하네스 해시, V-4(명세 303 보강표: ① PS2 L1·L2b 125 s, ② MLJ_K0V G4RF Fs0/Fs8 같은 실행 재생, ③ ML88_ep0, ④ rpB 기준선 SHA), V-5 판정.
- ✅ H-61-1(hydraulics `s8_seal_friction_counterbalance.md` 14절, 스크립트 `04_scripts/04_hydraulic/h61/`, 결과 `06_analysis/03_hydraulic/s8/h61_*.json`) 채택 U-S8-64, U-R8-9 ④ 부가 U-S8-65, V-2·V-4 방식 U-S8-66(명세 개정 61 보완 3, 219.7·302.3·302.4·303·304.1·305.3). 실기 κ_hi 상태식 구현 P-S8-22b는 U-R8-9 ④ 확인 뒤.
- ✅ V-2 재생 도구(worktree `r5_fallback_replay.py`, python O-4·P-1·공식 판정 커밋 0b1a55e·349b908·c52fdc4·88d483c, 판정 필드 `judgement_passed`): 공식 판정 = R-5 감시 nominal_gap 행 중 헤드 하강 행(Δh ≥ 0) 낙관 ≤ L1 0.05 / L2b 1.2 kN + 302.2 성립 감시 행(하강·상승) 놓친 발동 0, level 규칙 행 놓친 발동은 FLAG만(명세 303 "V-2 통과 판정 집합", U-S8-66 보충 2). `current_dur125` 통과(−0.10 / −0.24 kN). 참 힘은 L2b `F_pressure`, L1-R `F_cyl`. V-4 ③ ML88_ep0 길이는 원 에피소드 길이·최소 60 s. P3b 사례는 재생하지 않고 W-61-3 사례만 merge 뒤 대상 재실행.
- S9 착수 전 점검 1·5·6 닫힘 확인(`dynamics_model.md` 5.32.7 표는 4~6 "미실행").
- R8 C2 PS-7a 판정(S9 뒤), U-S8-57·DONE 꼬리 감시.

## 작업 규칙 (이 프로젝트 메모리에 있음)

- **모든 커밋 직전 integrity-checker → 이상 없을 때만 커밋·`origin/master` 푸시(상시 승인).** 커밋마다 이 인계 문서를 갱신해 같은 커밋에 넣는다. Medium·Low 지적도 커밋 전에 고친다.
- 예상 15분 이상 작업은 long-running-task-monitor 주기 점검(약 15분 간격 cron). 프로세스 종료 등 조치는 사용자 승인 뒤.
- 에이전트 지시문에 매번: 셸 heredoc·`python -`·`sed -i` 금지, Write로 쓴 파일을 `python -I`로 실행, 커밋 메시지는 `git commit -F <파일>`.
- 계산은 컴퓨터 자원을 최대한 쓴다(사용자 2026-10-26). 독립 작업은 에이전트를 병렬로 띄운다. 비용 측정만 단독.
- 다중 계산 작업의 P/E 코어 배치·동시 실행 수는 **cpu-scheduler-expert**에 맡긴다(사용자 2026-10-26). 배치표·실행 명령을 받아 메인이 실행하고, 끝나면 `기록` 모드로 실측을 남긴다.
- S단계 본 판정 실행 전에는 사용자에게 알리고 확인받는다(P3b는 2026-10-26 승인됨).
