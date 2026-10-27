# 세션 인계

새 세션은 이 문서와 아래 파일로 상태를 파악한다. 이전 대화 맥락은 없다. **아직 아무것도 실행하지 말고, 먼저 상태 확인 결과와 다음 단계 계획을 보고한 뒤 사용자 확인을 받는다.**

- 갱신: 2026-10-27 (커밋할 때마다 이 파일을 덮어쓴다. 옛 판은 git 이력).
- 마지막 커밋: 이 파일을 담은 커밋(`git log -1`, **"착지 충격·대각 로킹 = 정상 물리" 전파: control 개정 64~66, D1″ LOC 조건·임시 질량, FAULT_REGROUND(G4) 구현·Chrono 확인, dynamics 개정 55**). 그 전: 255981c(무결성 정리), 3eb1220(P-S8-22 V-5 ③′ 통과·V-1~V-5 종결, 개정 63, 재생 도구 D-1~D-4, C-S8-67), 7b4de6f(S9 완료·V-3~V-5 개정 62), 0941c0c(P-S8-22 merge), 3368317(cad C-1/C-2, worktree 브랜치), e9a6ea4(S9 P3b 판정), 6791c36(사용자: paper-reviewer 추가), 27c785e(개정 61 보충 3)
- 세션 기록: 일반 Windows 터미널에서 `claude`를 직접 실행한다(2026-10-26 결정).

## 현재 위치

- S8 완료(U-S8-58). **S9 완료(6/6, 2026-10-27, 합계 65/67)**: P1·P2·P2′·P3a·P3b 판정, 착수 전 점검 1~6(4 단독 비용 측정 포함) 모두 닫힘. 근거: `00_docs/00_roadmap.md` 1·4·6절.
- **P-S8-22(R-5 대체 다리 기울기) V-1~V-5 종결**: master merge 0941c0c, V-3 통과, V-4 실행, V-5 ①②④ 통과·③ 판정 불가 → U-S8-67 = (나) 양성 시험 ③′(C-S8-67) **통과**. 명세 `s6_control_spec.md` 개정 62(316~317.1절)·**개정 63(318~319절)**.
- worktree `.claude/worktrees/agent-a42ab63c487597861`과 병합된 브랜치 3개(`worktree-agent-a42ab63c487597861`·`-a21e7da9d589ffc9b`·`-ac4ca09081d79438a`)는 **정리 완료**(2026-10-27, 사용자 확인; 브랜치는 `git branch -d`). 저장소 브랜치는 master 하나.

- **다리 부상·대각 커버리지 감사**(2026-10-27, control): R8 C2에서 네 다리 모두 Chrono 판정을 거친 것은 "READY 뒤 침하·낙하"뿐. 공백 G1(레벨링 중 사건)·G2(R8 PS-7a)·G3(앞 다리 사건 + 로드 고장)·G5~G8은 미착수(아래 다음 단계). G4(헤드 고장 + 뜬 다리)는 이번 커밋에서 닫음.

## 이번 커밋에서 바뀐 것

- **전제 전파 감사**("착지 충격·대각 로킹은 정상 물리", control): 관측된 경로(D1″·로드 계단·RT·판정기)는 반영돼 있었고, 구조적 공백 4건을 찾음. 사용자 결정 U-S8-68~72(decision_log 5절):
  - U-S8-68 G4 = (가) 헤드 고장 때 뜬 다리만 재접지 → 잠금 → FAULT(**FAULT_REGROUND**). U-S8-69 첫 READY 전 D1″ 임시 질량 = YAML 명목. U-S8-70 D1″ 적용 조건 = LOC 확정 + 크롤러 재접촉 의심 보류. U-S8-71 범위(감사 (b) 1~4·6·7 지금, 5 밸브 불감대·8 착지 피크·9 유연 마스트는 U-R8-9·D2 때). U-S8-72 G4-4 = 0.5 s 이동 평균 최소 ≥ F_min + 순간 최소 > 0.
  - 명세 `s6_control_spec.md` **개정 64**(320~327, 기록 스캔·앨리어싱·비틀림 일 분해·설계), **65**(328~335, C-S8-68 1차 Chrono에서 재접지 0.1 s 중단 → 중단 2(자세) 삭제·접촉 네 다리 + 멈춤 10표본·단서 (d)·틈 축척 정정·헤드 고장 뒤 D1 계단 정지), **66**(336~340, c68b 판정, U-S8-72 확정, G4 닫음).
- **코드(python P-S8-23·24·25)**: `03_src/outrigger_sim/control/c2.py`(`C2Phase.FAULT_REGROUND`, LOC 기준 `is_crawler_lifted`), `two_pressure.py`(`imu_mass_before_ready`, 재접촉 감시, `suspend_step_rule`), 새 `fault_reground.py`. R8 프리셋(`with_10hz_d1()`)에서만 켬, 클래스 기본은 옛 동작. 시험 `test_c2_fault_reground.py`·`test_two_pressure_rev64.py` 등, unit 2587 통과. 축소 하네스(rigid 135·soil 72·sensor 72·beta 16·r8d1) 명령 해시 불변. T8(축소 G4 하네스 24) control 후보와 24/24 일치.
- **판정기·실행기(cad C-S8-68·70·71)**: `verify/s8_control.py` G4-1~8·G4-E 행, 행 종류 `not_applicable`(주입 실행 일반 행), F2 고장 다리 제외; `run_S8C.py` 헤드 고장 주입 `HeadFaultInjection`, 집합 `mlj_c68` 6사례, 전달 판독 `<case>/head_fault_delivered.npz`. 시험 `test_s8_c_s8_68.py`, 107사례 정의 해시 불변.
- **Chrono**: 1차 `07_results/S8/g4h_c68_20261027_125253`(설계 결함 확인), 재실행 `g4h_c68b_20261027_135040`(rc 0 ×6) → 재판정 `06_analysis/02_control/s8/rev65/verify_S8C_c68b_c71.json` 387행 실패 0. FS24 4사례 RL 재접지 1/1(3.4~6.0 s, 6.8~14.7 mm).
- **분석 스크립트·결과(control)**: `04_scripts/03_control/s8/r64_*.py`·`r65_c68b_decay.py`, `06_analysis/02_control/s8/rev64/`(`r64_alias.json` 7.5 MB 포함, 사용자 결정 커밋)·`rev65/`. 기록 재생 1,366건 판정 차 0(옛 피클은 LOC 복원 필수).
- **dynamics 개정 55(5.39)**: F_s 0 잠김 2 Hz roll–sway 로킹 ζ ≈ 0.009는 모델 감쇠 항 그대로(독립 모델 일치), 보수 쪽 하한, YAML 불변. 실측 보강(U-R8-9 ⑤ 타격 시험 두 진폭) 채택(사용자 2026-10-27) → CLAUDE.md U-R8-9 줄.
- CLAUDE.md U-R8-9: ④ 본문, ⑤(압력·IMU·자이로 시각 ≤ 5 ms, IMU 필터 군지연, heave 진동수 기록), 잠김 로킹 감쇠 타격 시험.

## 255981c에서 바뀐 것

- 무결성 점검(2026-10-27, master 3eb1220 기준 Medium 6·Low 5) 정리만 했다. 판정·기준값 변화 없음.
  - 문서: 로드맵 6절 1·6번(현재 상태·최근 커밋), 3절 표 S9 ✅, 2절 "현행 개정 54", "미푸시" 문구(로드맵·decision_log), `chrono_build_plan.md` 머리말 S0~S9 완료·S9 제목 ✅, README(S9 실행기, `run_S9.py level --approved`, 명세 개정 63), 명세 머리말 "P3 판정은 개정 60에서 끝났다", CLAUDE.md 기준값 표 날짜, 이 문서(worktree 정리 완료, 시험 함수 수 11 + 3).
  - 코드(python): `04_scripts/02_chrono/s9_merge/soil_restore_check.py` `PLAN` 경로를 main 기준으로(worktree 전제로 `IndexError`), S9 스크립트 5개 docstring "project root", `06_analysis/01_chrono/19_S9/` 요약 JSON 6개에 `folder_note`(삭제된 worktree 경로 → main `07_results/S9/` 같은 이름 폴더; 기존 값 불변).

## 3eb1220에서 바뀐 것

- **C-S8-67(cad)**: `run_S8C.py`에 사건 `G4RRF`(로드 고장 다리 RR)·사례 `MLJ_K0V_fdown3.5_G4RRF_Fs0/Fs8`·집합 `mlj_c67`(`mlj`는 `MLJ_EXTRA_EVENTS`로 6건 유지), 시험 `05_tests/unit/test_s8_c_s8_67.py`(기존 99사례 정의 해시 불변). 실행 `07_results/S8/v5_c67_20261027_032104` rc 0 ×2. cad 추출은 `06_analysis/02_control/s9/v5/cad_c67/`에 보존.
- **V-5 ③′(control, 개정 63)**: 통과. RR R-5 t_G4 + 0.7 / + 0.6 s(짝 + 0.9 / + 0.7), INFO:RR 14 / 8, 같은 실행 재생 낙관 −4.00 / −3.05 kN·놓친 발동 0, 판정 행 통과(최소 21.33 / 22.03 kN, 끝 자세 0.0345 / 0.0464°). 판정 스크립트 `04_scripts/03_control/s8/v5_c67_judge.py`, 결과 `06_analysis/02_control/s9/v5/v5_c67_judgement.json`·`verify_S8C_c67.json`.
- **재생 도구 D-1~D-4(python)**: `r5_fallback_replay.py`·`contact_replay.py`(C-1 meta 키 허용, C-2 `pads_seal_fields` 참값, S8·S7 엔진 읽기, `nominal_gap` 기록 same_run 관문). 출력 변경: 엔진 표기 L1→L1R·L2b→L2b_NSC, S8 기록 공식 `judgement_passed` None→값, 새 키 `gate`·`same_run_gate`·`level_gate.role`. 시험 함수 14개 추가(`test_r5_fallback_replay.py` 11 + `test_s8_c_s8_67.py` 3; 매개변수화로 수집 +24건), unit 2483 통과·7 건너뜀.
- 문서: 명세 개정 63(316.6·317 갱신), decision_log, 로드맵, 색인.

## 직전 커밋(7b4de6f)에서 바뀐 것

- **S9 단독 비용 측정**(사용자 결정 계획 A, 2026-10-26 23:06~10-27 00:29): `04_scripts/02_chrono/solver_benchmark/step_cost_S9.py`, 결과 `06_analysis/01_chrono/01_cost/S9_P3b_solo_step_cost.json`(원자료 `07_results/S9/cost_solo_20261026_230636`). P코어 4스레드 단독 전 하중 G1 2.64·S1 2.66·J1 4.55·J2 4.62 ms/스텝, 4병렬 경합 대비 약 2배 빠름. `--duration` 단축 궤적은 P3b와 0~40 s 비트 동일. dynamics 개정 53 보완(5.37.10 점검 4 닫힘), 로드맵 S9 6/6, `chrono_build_plan.md`.
- **P-S8-22 merge(0941c0c)**: worktree 커밋 d7638e9..88d483c + cad C-1/C-2(3368317: `outrigger_sim.chrono.fallback_ratio`, `run_rows`, 실행기 `fallback_ratio` 기록, 환경 변수 `OUTRIGGER_L1_FALLBACK_RATIO_SOURCE` 거부·`--allow-env-override`, `m3_run --fallback-ratio-source`, `probed_leg` 기록). merge 뒤 unit 2459 통과·7 건너뜀, chrono not slow 285 통과.
- **V-3**: 강체 135·토양 72·센서 72·β 16·r8d1 8 명령 해시 비트 동일, INFO_R5_FALLBACK_SLOPE 0회(`06_analysis/02_control/s9/v3/v3_judgement.json`).
- **V-4**(`07_results/S9/v4_20261027_010707`): ① L1·L2b PS2, ② MLJ_K0V G4RF Fs0·Fs8 rc 0·INFO 7/22/14/6회, ④ rpB plant_meta·column_nominal 명령 SHA = 기준선 e072f15c…. ③ ML88_ep0: 원 ML 스냅숏이 옛 YAML(params_sha256 불일치)이라 사용자 결정 (가)로 ML88 base 재생성(`07_results/S8/ml88_rebase_20261027_012458`) 뒤 재생 rc 0, 그러나 로드 대체 미발생(INFO 0). **원 ML 배치 branch.pkl은 YAML 재생성(8616be9) 뒤 복원 불가 — 재생하려면 base부터 다시.**
- **V-5(control, 명세 개정 62 316절)**: ①②④ 통과, ③ 판정 불가, 사양 미달 0. 재생 도구 결함 D-1~D-4(316.6, 우회로 판정). 303 V-2에 "S7 L2b는 F_s = 0이라 `F_cyl_no_friction`으로 재생" 명시, 304.1을 구현 기록으로. 결과 `06_analysis/02_control/s9/v5/`.
- 문서: 명세 개정 62, decision_log(S9 단독 비용, P-S8-22 merge·V-5·U-S8-67), 로드맵, CLAUDE.md(미정 사항 "S9 뒤 계속 감시"; 정확도 행 0.119°는 앞 커밋), 색인 재생성.

## 다음 단계

A. ✅ (이번 커밋) G4 FAULT_REGROUND 닫음(명세 개정 64~66, U-S8-68~72). 남은 감사 후속(U-S8-71 범위): **S9 재접촉 합성 사례**(명세 322.2 확인, control), 커버리지 공백 G1(레벨링 중 사건, 네 다리)·G2(R8 PS-7a·FL 미러·PS-7b·c)·G3(앞 다리 사건 + 그 다리 로드 고장)·G5(앞 다리 빠른 침하 × 높은 F_s)·G6(SCM 한 패드 연약부)·G7(RL·FL 전용 사례)·G8(비평면 시작) — control 감사 권고는 축소 스크린 약 200건 → Chrono 보강 배치(L2b 11 + L1-R 4~6, 약 45~60분). 뒤로 미룬 것: 밸브 불감대 잠김 판정(U-R8-9 ③④ 뒤), 착지 피크 물리 판정(hydraulics), 유연 마스트(D2 때).
0. ✅ (3eb1220) 아래 1·2 끝: C-S8-67 실행(`07_results/S8/v5_c67_20261027_032104`, rc 0 ×2) → control V-5 ③′ 통과(명세 개정 63 318~319절, `06_analysis/02_control/s9/v5/v5_c67_judgement.json`, 판정 스크립트 `04_scripts/03_control/s8/v5_c67_judge.py`): RR R-5 t_G4+0.7/+0.6 s(짝 +0.9/+0.7), INFO:RR 14/8, 낙관 −4.00/−3.05 kN, 놓친 발동 0 → **P-S8-22 V-1~V-5 종결**. 재생 도구 D-1~D-4 해결(python, 시험 함수 14개 추가, unit 2483 통과). 3(worktree·브랜치 정리)도 끝났다.
1. ✅ **C-S8-67(cad, 명세 317.1)**: `run_S8C.py`에 `G4RRF` 사건(로드 고장 다리 RR, 나머지 G4RF와 같음)·집합 `mlj_c67` 정의 → `run_S8C.py run --only MLJ_K0V_fdown3.5_G4RRF_Fs0 MLJ_K0V_fdown3.5_G4RRF_Fs8 --tag v5_c67 --approved --workers p7`(사용자 결정 U-S8-67 (나)로 승인, P코어, 동시 2 이하, 건당 약 6~7분). 기존 mlj·mlj_c29 해시 불변 확인. → control V-5 ③′ 판정(317.1 기준 4개).
2. ✅ **python D-1~D-4**(`03_src/outrigger_sim/control/r5_fallback_replay.py`, `contact_replay.py`): C-1 meta 키 TypeError, C-2 `pads_seal_fields` 미사용, S8 엔진 None, `nominal_gap` 기록 관문. 고친 뒤 V-4 기록 4건이 우회 없이 `judgement_passed` True.
3. ✅ worktree·브랜치 정리(2026-10-27). 이어진 무결성 점검 정리 커밋: 로드맵 6절·README S9 실행기·`chrono_build_plan.md` 머리말·`soil_restore_check.py` 경로(main 기준)·S9 스크립트 docstring "project root"·19_S9 요약 JSON 6개 `folder_note`.
4. hydraulics H-61-1 후속, 실기 κ_hi 상태식 P-S8-22b는 U-R8-9 ④ 확인 뒤.
5. R8 C2 PS-7a 판정(S9 뒤), U-S8-57·DONE 꼬리 감시, IMU 선정에 0.119° 반영, `run_S9.py` `P3B_US_PER_STEP_UPPER` 갱신 검토(경합 상한 G1·S1 4500 µs가 P3b 4병렬 실측 128 s 평균 G1 5.10·S1 4.98 ms/스텝보다 작다; J1·J2 9000 µs는 실측 8.69·8.48 이상), 재레벨 문턱 문서 불일치(control 311절 0.07° vs dynamics 5.38.4 0.03°) 정리.

## 논문·포스터 (커밋 안 함)

- `09_paper/`는 **커밋하지 않는다**(사용자 2026-10-26, `.git/info/exclude`). LaTeX `latex/build.ps1`(MiKTeX xelatex→bibtex→xelatex×2). 분량 제한은 잠정적으로 두지 않는다(사용자 2026-10-26 밤).
- 2026-10-27: 4.4절(표 7)·초록·결론 P3b 반영, 그림 7(`figures/fig7_p3b.png`) 렌더, `md2tex.py` 표 대응 갱신, 빌드 `latex/main.pdf` 11쪽. 원고 백업 `draft/history/`. 남은 점: 4.3·04_1 "표 3" 번호 중복, 결론 (2) 앞 문장을 "들어 올림 과정"으로 고친 것 확인.
- 포스터 `09_paper/poster/`: **v2만 수정**(사용자). v2 ⑧ P3b 상자를 24건 결과로(사용자 승인 문구), ⑦을 오른쪽 단으로 이동. 선택: 왼쪽 ⑧ 아래 15 mm 공백에 ④ 블록도 확대(230→240 mm). 생성 스크립트는 세션 scratchpad에 있었다(새 세션에서는 없음; 그림 스크립트는 `09_paper/poster/figures/scripts/`).
- 원고 리뷰는 프로젝트 에이전트 `paper-reviewer`(`.claude/agents/paper-reviewer.md`, opus·effort medium, 읽기 전용, 결과는 응답으로만)에 맡긴다(사용자 추가 6791c36). 첫 시험은 "`draft/00_front_abstract.md` 초록만 리뷰".

## 작업 규칙 (이 프로젝트 메모리에 있음)

- **모든 커밋 직전 integrity-checker → 이상 없을 때만 커밋·`origin/master` 푸시(상시 승인).** 커밋마다 이 인계 문서를 갱신해 같은 커밋에 넣는다. Medium·Low 지적도 커밋 전에 고친다.
- **모든 계산 작업은 cpu-scheduler-expert 배치표로 P·E 코어를 최대한 쓴다**(사용자 2026-10-27, 단건 포함). 비용 측정만 단독.
- 예상 15분 이상 작업은 **long-running-task-monitor**에 15분 주기 점검을 맡긴다(Suspended 검사 포함).
- **Suspended·응답 없는 프로세스는 추천 방법으로 자동 조치 뒤 사후 보고**(사용자 2026-10-26): Suspended는 ResumeThread, 일회성 고아만 단일 PID 종료, 시뮬레이션·실행기는 자동 종료 금지. Bash·Grep 도구 자식(git·grep·bash·ripgrep)이 Suspended로 멈추는 일이 반복돼 Python·검색·긴 명령은 PowerShell 도구로 한다(검색은 `Select-String`).
- 에이전트 지시문에 매번: 셸 heredoc·`python -`·`sed -i` 금지, Write로 쓴 파일을 `python -I`로 실행, 커밋 메시지는 `git commit -F <파일>`.
- S단계 본 판정 실행 전에는 사용자에게 알리고 확인받는다.
