# 세션 인계

새 세션은 이 문서와 아래 파일로 상태를 파악한다. 이전 대화 맥락은 없다. **아직 아무것도 실행하지 말고, 먼저 상태 확인 결과와 다음 단계 계획을 보고한 뒤 사용자 확인을 받는다.**

- 갱신: 2026-10-28 커밋 직전 (커밋할 때마다 이 파일을 덮어쓴다. 옛 판은 git 이력).
- 마지막 커밋: 이 파일을 담은 커밋(`git log -1`, **명세 개정 74: P-S8-30 = P30fz(LOC 전 느린 들어 올림 + 재접근 ×4) 구현·인수, 재현 시험 분리, V-3·r8d1 기준 갱신**). 그 전: 3131552(개정 72·73, G6 하네스·P-S8-29·꼬리 여유·G6 Chrono 기능), 34c806d(개정 69~71, G8·P-S8-28), 7862ef6(개정 67·68, P-S8-26·27, S9 J1 인수), e8ef7df(FAULT_REGROUND G4, 개정 64~66), 255981c(무결성 정리), 3eb1220(P-S8-22 종결, 개정 63), 7b4de6f(S9 완료), 0941c0c(P-S8-22 merge)
- 세션 기록: 일반 Windows 터미널에서 `claude`를 직접 실행한다(2026-10-26 결정).

## 이번 커밋에서 바뀐 것 (3131552 이후)

1. **개정 74(384~388)**: P-S8-30 후보 비교(control `r74_p30_screen.py` 변형 P30f·n·fn·f25·fz, `r74_compare.py`, `r74_judge.py`) → **P30fz 채택**(사용자 결정 2026-10-28). python 구현 `c2.py` `PreLocLiftPauseSettings`(R8 프리셋만), 사건 `INFO_LIFT_PAUSED`, 시험 `test_c2_p30.py` 38. 하네스 해시 G6 116·G8 516 = `rev74/r74_p30_expected_hashes_P30fz.json`. G6 116/116 합격, G8 판정 변화 0.
2. V-3 rigid 8·soil 4·r8d1 imu 변화(모두 늦춤 1회, 판정 불변, control `r75_v3_diff.py` → `rev75/r75_v3_diff.json`) → `07_results/S9/v3/` 기준 갱신(옛 기준 `history/*_pre_p30.json`, git 제외 폴더). P-R8-13 재현 시험은 P-S8-30 끔 프리셋(`04_scripts/03_control/r8d1/v34_drop.py preset_p30off`)으로 분리, 전체 프리셋은 새 시험 `test_full_preset_drop_stays_within_u57`. S9 P3b Chrono 재실행 불필요(사용자 승인).
3. 문서: 명세 개정 74(383 제목 갱신), decision_log, 로드맵 6절 1번, CLAUDE.md 제어기 행(P-S8-30, 개정 30~74)·커버리지 공백 줄, 색인.

## 다음 할 일 (권장 순서)

1. **G6 Chrono**(사용자 확인 뒤): `python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run G6 --parallel 4`(약 4.1 h; G6-0a 열린 루프 대조가 약 30분에 끝나면 `04_scripts/02_chrono/s9_g6_patch_compare.py <G6-0a 폴더>`부터 — 실패하면 나머지 해석 중단), long-running-task-monitor 15분 점검, cpu-scheduler 배치. 판정 기록에 `INFO_LIFT_PAUSED` 시각·LOC − 이탈 추가(cad, 실행 전), G6 판정 행을 S9 판정기에 넣을지(cad 제안)·C-4 허용값(dynamics) 확정.
2. dynamics_model.md 5.40(G6 첫 접촉 판단) 반영(dynamics 초안은 이번 세션 리포트에만 있음 — 다시 맡겨 문서화).
3. **G3(앞 다리 사건 + 그 다리 로드 고장)**: 축소 하네스에 로드 판독 고장 주입, 약 72실행.
4. 선택: C-S8-76 C5(L2b G5 A형 0.5 s 평균). 나중: 크롤러 재접촉 합성(322.2), U-S8-57·DONE 꼬리 감시.

## 3131552에서 바뀐 것

1. **개정 72(375~379)**: 하네스 행정 관문 = 실행 중 최대(재판정 불변). **꼬리 생략 검사 여유**(python, `LockTailSettings.end_overshoot_margin_m` R8 0.0005; 인수 해시 불변). **G6 하네스**(control `r72_g6_screen.py`: 패드별 토양 `SoilPadsPerLeg`, 강체 기반 `MixedRigidPads` — 사용자 결정으로 강체 기반 추가) G1 기반 64 + 강체 기반 52: 자세 116/116 ≤ 0.042°, 후방 연약 J1·J2 32건 READY 미도달(비틀림 완료 조건; dynamics 가설대로 비틀림 강성 약 1/60 저하 × 루프 이득), S1 LOC 전 재접근 → P3-8 FLAG 강등(사용자 결정). **P-S8-29 = V2b**(사용자 결정 2026-10-28) python 구현(`TwistCompletionRelaxSettings`, `INFO_TWIST_UNSETTLED`, 시험 `test_c2_p29.py` 22 + unit 2747) → 해시 G6 116 = 후보, G8 516·V-3·r8d1 불변. 결과 `06_analysis/02_control/s8/rev72/`·`rev73/`.
2. **개정 73(380~383)**: (C) 강체 + S1 전방 대각 부상 판정 정의 U-S9-G6c (가)(이탈 뒤 엄격, LOC 전 하중 소실 FLAG). P-S8-30 후보 탐색 12 → Af3B4 (C) 8/8이지만 나머지 108 중 20 회귀(LOC 지연) → 인수 미달, python 구현 되돌림(`c2.py` = P-S8-29 상태 확인). 결과 `rev74/`(기대 해시 파일은 `_provisional`, 인수에 쓰지 않음).
3. **G6 Chrono 기능(cad, 실행 전)**: `scm_model.py` `soil_patch`(연약 패드만 세 번째 SCMTerrain, 앵커 부싱 연약 세트·패드별 마찰 `ground_bushing.PadBushingSpec.friction`), `run_S9.py` `--soil-patch`·`--soil-patch-grid`·G6 사례(G6-0a 열린 루프 대조 G1@RR, G6-0b 선택, J1@RR 160 s, J1@FL 200 s, G1@RR 120 s, `duration_s`)·`p3b_ext`(완료 막힘 사유·D 시계열 `completion_series.npz`, 사건 수, t_P·c_min, 처녀 가지 구간 `virgin_branch`), `s9_batch.py` G6·G6_opt, 비교기 `s9_g6_patch_compare.py`. soil_patch 없으면 비트 동일, 기존 정의 불변. 시험 `test_s9_g6_soil_patch.py`·`test_s9_g6_patch_compare.py`·`05_tests/chrono/test_scm_soil_patch.py`. dynamics 판단: 연약 세트 J1 유지(첫 접촉 튐은 TOUCH 첫 약 0.2 s만, `dynamics_model.md` 5.40 개정 초안은 아직 문서에 안 넣음).
4. 문서: 명세 개정 72·73, decision_log, 로드맵 6절 1번, CLAUDE.md 제어기 행(P-S8-29·꼬리 여유, 개정 30~73)·커버리지 공백 줄, 색인.

### 3131552 당시 다음 할 일 (기록)

1. **P-S8-30 수정 후보 비교**(control): P30-f(정지 대신 0.15 $v_{max}$ 느린 들어 올림)·P30-n(문턱 2.0/2.5 $F_{min}$)·P30-fn을 `r74_p30_screen.py`에 넣고 (C) 8 + 회귀 20 + ref 20 비교(약 7분) → 통과 후보로 G6 116·G8 516 전체 회귀(약 30분, 메인 세션 배치) → python 구현(383절 갱신 명세, Af3B4 참조 구현 특성은 python 리포트 기록) → 인수.
2. **G6 Chrono**(사용자 확인 뒤): `s9_batch.py run G6 --parallel 4`(약 4.1 h, G6-0a 끝나면 `s9_g6_patch_compare.py`부터), long-running-task-monitor 15분 점검. P-S8-30 확정 뒤 최종 제어기로. G6 판정 행을 S9 판정기에 넣을지(cad 제안)·C-4 허용값(dynamics) 확정.
3. dynamics_model.md 5.40(G6 첫 접촉 판단) 개정을 문서에 반영(dynamics 초안 있음).
4. **G3(앞 다리 사건 + 그 다리 로드 고장)**: 축소 하네스에 로드 판독 고장 주입, 약 72실행.
5. 선택: C-S8-76 C5(L2b G5 A형 0.5 s 평균). 나중: 크롤러 재접촉 합성(322.2), U-S8-57·DONE 꼬리 감시.

## 34c806d에서 바뀐 것

1. **정리(7862ef6 직후, 사용자 확인)**: worktree `agent-acc9eadf7f3760ab1`·브랜치 삭제(미커밋 파일 20개는 메인과 같거나 메인이 최신), 점검 폴더 `c72smoke_*`·`c75chk_*`·`bundleC_ps7r8_check_*` 삭제. 저장소 브랜치는 master 하나.
2. **진동 진폭 정의 정정(명세 359절)**: `r68_p27_screen.py`·`r68_c73_rocking.py`에 추세 제거 진폭 열 `half_pp_detrended_per_2s_kN` 추가(기존 키 불변, python). 개정 68 351.1·356.1 인용 정정, 결론 불변.
3. **개정 69(359~365)**: G8(비평면 시작) 400 + G5 잔여($F_s$ 2·4) 384 축소 스크린(9단위 P 8 + E 12, 20:20~20:33). 평지 336/336 합격, 경사 + 한 패드 둔덕에서 크롤러 틈 추정(네 패드 평면 맞춤, 오차 3h/4)이 뜬 크롤러를 모자라게 읽어 아래 다리 행정 끝 FAULT 26·대각 부상 13. G5 B형 0 → 닫음. U-S8-78 = (가)+(나), U-S8-79 = 재접지 뒤 FAULT(사용자 결정).
4. **개정 70(366~370)**: C-S8-76(cad) — `03_src/outrigger_sim/chrono/pad_block.py`(새), `chrono/model.py` `pad_blocks`, `rod_chamber_link.py`, `run_S6C.py`(경사 `edge`·스냅숏 `S6_crawler_top_edge.npz`·집합 `g8c76`·`g8c76_p28`·`g8c76_p28acc`·`judge-g8`·크롤러 구 틈 기록·FAULT 뒤 끝 규칙), `s6_stage2.py`, `verify/s6_control.py`(g8 행, 행정 관문 = 실행 중 최대값, P-S8-28 사건 열). Chrono C1·C2(L1-R $F_s$ 0, `07_results/S6/bundleC_g8c76_c76_L1R_20261027_211309`) 하네스와 ≤ 0.2 mm 일치 → 하네스 타당. P-S8-28 후보 9개 비교 → AG2c5 채택(평지 342 확인 뒤 사용자 결정).
5. **개정 71(371~374)**: P-S8-28 구현(python, `c2.py`·`fault_reground.py`, R8 프리셋만, 시험 `test_c2_p28.py` 24 + unit 2692 통과). 하네스 해시 경사 174/174·평지 342/342, Chrono 인수(`07_results/S6/bundleC_g8c76_p28acc_p28_L1R_20261027_222426`) 40행 실패 0. V-3·r8d1 기준(`07_results/S9/v3/`, git 제외) 갱신: 차이 39 + 4 = P-S8-27 수용분(`INFO_TOUCH_DIP_HELD` 실행과 완전 일치), 옛 기준 `history/*_pre_p27.json`. `run_S8C.py` 토양 복원 앵커 거부를 `SoilStateRestoreError`로 통일(cad, 시험 6건, unit 2698 통과).
6. 문서: 명세 개정 69~71, decision_log 4줄, 로드맵 6절 1·6번, CLAUDE.md 제어기 행(P-S8-28, 개정 30~71)·미정 사항 커버리지 공백(G3·G6만 남음), 색인. 커밋 전 무결성 점검 Medium 2·Low 6 모두 고침.
7. 분석: `04_scripts/03_control/s8/r69_*`(g8_screen·g5_screen·table·judge·g8_xcheck)·`r70_*`(p28_screen·judge·c76_harness), 결과 `06_analysis/02_control/s8/rev69/`·`rev70/`. 시험 `test_s6_c_s8_76.py`·`05_tests/chrono/test_pad_block.py`·`test_c2_p28.py`·`test_s8_soil_restore.py`.

### 34c806d 당시 다음 할 일 (기록)

1. **G6(SCM 한 패드 연약부) 스크린**: s9 하네스 `SoilPads`를 다리별 토양 세트로 확장(control 설계: 한 패드 J1·J2·S1 / 나머지 G1·rigid × 다리 4 × 상·하단 × $F_s$ 0·4, 약 96실행). P-S8-28 앵커가 패드별 침하로 작동할 수 있으니 앵커·참 틈·끝 자세·$t_P$ 표본을 함께 본다(명세 374).
2. **G3(앞 다리 사건 + 그 다리 로드 고장)**: 축소 하네스에 로드 판독 고장 주입 추가, 사건 FL·FR × G4·RE1bF·FS24 × 고장 시각 3 × $F_s$ 0·8, 약 72실행.
3. control: `r70_judge.py` 하네스 집계 행정 관문을 실행 중 최대값으로(366 정정 반영).
4. 선택: C-S8-76 C5(L2b G5 A형 후보 0.5 s 평균 확인, 약 13분).
5. 나중: 크롤러 재접촉 합성 사례(322.2), U-S8-57·DONE 꼬리 감시(계속).

## 7862ef6에서 바뀐 것

1. **C-S8-75 C(S9 J1) 합격**(명세 358.8): `07_results/S9/batch_P3b_20261027_174330`(`P3b_J1_B_top_Fs0`·`Fs4`, rc 0 ×2, 19:39·19:41 끝, 벽시계 6,983 / 7,061 s). P3 판정 행 전부 통과(P3-4 0.0558° / 0.0423°, P3-3 68.06 / 68.17 kN), FLAG 0, CAPPED·DIP_HELD 0회, 10 Hz 지령이 10-26 배치와 비트 동일. A·B·C 합격 → P-S8-27 인수 완료. 판정 `04_scripts/03_control/s8/r68_c75c_j1_judge.py`, 결과 `06_analysis/02_control/s8/rev68/c75c_j1_judgement.json`·`c75c_j1_baseline_20261026.json`. CLAUDE.md 제어기 행 갱신(개정 30~68). 2차 무결성 점검 Medium 2·Low 5 모두 고침, python-expert 린트(쓰지 않는 import·변수 제거, 판정 출력 비트 동일).
2. **이전 미커밋 작업**: 명세 개정 67(341~347, G1·G2·G7 스크린, U-S8-73)·68(348~358: C-S8-72·73·74·75 판정, U-S8-74~77). 제어기 `c2.py` P-S8-26(`touch_free_air_cap_excess_N` (8000,8000,6666.4,6666.4), `INFO_TOUCH_FREE_AIR_CAPPED`)·P-S8-27(`touch_hold_dip_samples` 2, `INFO_TOUCH_DIP_HELD`, R8 프리셋만). 판정기 `verify/s8_control.py` G1 행·U-S8-74(0.5 s 평균 + 부상 없음)·U-S8-75 (나) 예외(F_s < 2 kN·상단·전방 빠른 사건, ≤ 0.1 s·≤ 0.5 mm), `s6_control.py` PS-7 판정, `s6_bundle_c.py` 사전 접지 스냅숏 허용. 실행기 `run_S8C.py`(집합 g1·c74·c75, `e6` 레이아웃, 메타 키), `run_S6C.py`(ps7r8, `--tag`, 메타 키), `s6_stage2.py`(사전 접지 스냅숏). 시험 `test_c_s8_72.py`·`test_s8_u74.py`·`test_s8_u75.py`·`test_c2_r8d1.py`·`test_s8_c_s8_68.py`(unit 약 2640 통과). 분석 `04_scripts/03_control/s8/r67_*`·`r68_*`, 결과 `06_analysis/02_control/s8/rev67/`·`rev68/`, 새 스냅숏 `07_results/states_L1R/S6_crawler_top_flat_FLpre.npz`. Chrono 결과 폴더: S8 `c72_20261027_155426`·`c74_20261027_164128`·`c75_4790e2b_…174330`·`c75_cb292e8_…174330`, S6 `bundleC_ps7r8_L1R_20261027_160512`·`bundleC_ps7r8_c73_L1R_20261027_161914`·`bundleC_ps7r8_c75_L1R_20261027_174330`, 점검용 `c72smoke_*`·`c75chk_*`·`bundleC_ps7r8_check_*`(커밋 전 정리 여부 확인). 1차 무결성 점검(18:10) Medium 3·Low 4는 색인 재생성 외 모두 고침.
3. **다음 단계 5번 묶음 정리**:
   - `00_docs/01_dynamics/dynamics_model.md` 5.38.4: 재레벨 계기를 "0.03° 데드밴드" → READY 재레벨 문턱 **0.07°**(`relevel_attitude_rad`, `c2.py:557`, control 311절)로 정정(정정 주석 포함).
   - `00_docs/05_sensors/imu_cabin_and_accuracy_review.md`: 머리말 보충 + **10.6절**(연약 지면 IMU 선정 ≤ 0.119°; 바뀐 센서는 ACS-080 △→× 하나, 최소 여유 TMM88D 0.047°).
   - `04_scripts/02_chrono/run_S9.py` `P3B_US_PER_STEP_UPPER` G1·S1 4500 → **5500 µs**(4병렬 실측 5.10·4.98, 사례 최대 5.3 ms), J1·J2 9000 유지(사용자 결정 2026-10-27 (가): B·상단 평균 기준, 사례 최대 11.2 ms는 덮지 않음), docstring 출처 갱신, `P3B_EST_S` G1·S1 5800 → 7000 s. `05_tests/unit/test_s9_p3b_records.py` 기대값 2줄(22 통과, python).
   - 로드맵 6절 1번에 위 셋 완료 표시(U-S8-57·DONE 꼬리 감시는 그대로 남김), decision_log에 J1·J2 9000 유지 결정 한 줄.
   - 전역 `~/.claude/settings.json`에 permissions allow(기본 도구·로컬 MCP 9개)·deny(force push·reset --hard·clean -f·루트 삭제·settings 자기 수정) 추가(사용자 2026-10-27, 저장소 밖). 클라우드 커넥터는 allow에 넣지 않음.
4. **주요 판정 결과(개정 68)**: C-S8-72 실패 9 → U-S8-74 판정 4 → U-S8-75 (나) 예외 0(FLAG 2). C-S8-74(F_s 2·4) 1,008행 실패 0. C-S8-73 TOUCH FLAG 3 → 1. C-S8-75 A(PS-7) 합격(RR 추가 행정 8.9~15.7 mm, FLAG 0), B(경사 짝) 합격(313행 × 2 실패 0, 최소 힘 차 ≤ 0.37 kN).

## 현재 위치

- S8 완료(U-S8-58). **S9 완료(6/6, 2026-10-27, 합계 65/67)**: P1·P2·P2′·P3a·P3b 판정, 착수 전 점검 1~6(4 단독 비용 측정 포함) 모두 닫힘. 근거: `00_docs/00_roadmap.md` 1·4·6절.
- **P-S8-22(R-5 대체 다리 기울기) V-1~V-5 종결**: master merge 0941c0c, V-3 통과, V-4 실행, V-5 ①②④ 통과·③ 판정 불가 → U-S8-67 = (나) 양성 시험 ③′(C-S8-67) **통과**. 명세 `s6_control_spec.md` 개정 62(316~317.1절)·**개정 63(318~319절)**.
- worktree `.claude/worktrees/agent-a42ab63c487597861`과 병합된 브랜치 3개(`worktree-agent-a42ab63c487597861`·`-a21e7da9d589ffc9b`·`-ac4ca09081d79438a`)는 **정리 완료**(2026-10-27, 사용자 확인; 브랜치는 `git branch -d`). 저장소 브랜치는 master 하나.

- **다리 부상·대각 커버리지 감사**(2026-10-27, control): R8 C2에서 네 다리 모두 Chrono 판정을 거친 것은 "READY 뒤 침하·낙하"뿐. 닫힘: G4(e8ef7df), G1·G2·G7(7862ef6, 개정 67·68), G5·G8(이번 커밋, 개정 69~71). 남음: G3(앞 다리 사건 + 로드 고장)·G6(SCM 한 패드 연약부) — 위 "다음 할 일".

## e8ef7df에서 바뀐 것

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

## 다음 단계 (7862ef6까지의 기록, 현행은 위 "다음 할 일")

A. ✅ (e8ef7df) G4 FAULT_REGROUND 닫음(명세 개정 64~66, U-S8-68~72). ✅ (이번 커밋) G1·G2·G7 스크린·Chrono 보강(개정 67·68, C-S8-72~75, P-S8-26·27). 남은 감사 후속(U-S8-71 범위): G3·G5(중간 $F_s$)·G6·G8(조기 접지 포함), 크롤러 재접촉 합성 사례(322.2, 나중 — 자세 제어 우선). 아래는 e8ef7df 당시 목록: **S9 재접촉 합성 사례**(명세 322.2 확인, control), 커버리지 공백 G1(레벨링 중 사건, 네 다리)·G2(R8 PS-7a·FL 미러·PS-7b·c)·G3(앞 다리 사건 + 그 다리 로드 고장)·G5(앞 다리 빠른 침하 × 높은 F_s)·G6(SCM 한 패드 연약부)·G7(RL·FL 전용 사례)·G8(비평면 시작) — control 감사 권고는 축소 스크린 약 200건 → Chrono 보강 배치(L2b 11 + L1-R 4~6, 약 45~60분). 뒤로 미룬 것: 밸브 불감대 잠김 판정(U-R8-9 ③④ 뒤), 착지 피크 물리 판정(hydraulics), 유연 마스트(D2 때).
0. ✅ (3eb1220) 아래 1·2 끝: C-S8-67 실행(`07_results/S8/v5_c67_20261027_032104`, rc 0 ×2) → control V-5 ③′ 통과(명세 개정 63 318~319절, `06_analysis/02_control/s9/v5/v5_c67_judgement.json`, 판정 스크립트 `04_scripts/03_control/s8/v5_c67_judge.py`): RR R-5 t_G4+0.7/+0.6 s(짝 +0.9/+0.7), INFO:RR 14/8, 낙관 −4.00/−3.05 kN, 놓친 발동 0 → **P-S8-22 V-1~V-5 종결**. 재생 도구 D-1~D-4 해결(python, 시험 함수 14개 추가, unit 2483 통과). 3(worktree·브랜치 정리)도 끝났다.
1. ✅ **C-S8-67(cad, 명세 317.1)**: `run_S8C.py`에 `G4RRF` 사건(로드 고장 다리 RR, 나머지 G4RF와 같음)·집합 `mlj_c67` 정의 → `run_S8C.py run --only MLJ_K0V_fdown3.5_G4RRF_Fs0 MLJ_K0V_fdown3.5_G4RRF_Fs8 --tag v5_c67 --approved --workers p7`(사용자 결정 U-S8-67 (나)로 승인, P코어, 동시 2 이하, 건당 약 6~7분). 기존 mlj·mlj_c29 해시 불변 확인. → control V-5 ③′ 판정(317.1 기준 4개).
2. ✅ **python D-1~D-4**(`03_src/outrigger_sim/control/r5_fallback_replay.py`, `contact_replay.py`): C-1 meta 키 TypeError, C-2 `pads_seal_fields` 미사용, S8 엔진 None, `nominal_gap` 기록 관문. 고친 뒤 V-4 기록 4건이 우회 없이 `judgement_passed` True.
3. ✅ worktree·브랜치 정리(2026-10-27). 이어진 무결성 점검 정리 커밋: 로드맵 6절·README S9 실행기·`chrono_build_plan.md` 머리말·`soil_restore_check.py` 경로(main 기준)·S9 스크립트 docstring "project root"·19_S9 요약 JSON 6개 `folder_note`.
4. hydraulics H-61-1 후속, 실기 κ_hi 상태식 P-S8-22b는 U-R8-9 ④ 확인 뒤.
5. U-S8-57·DONE 꼬리 감시(남음). ✅ (이번 커밋) R8 C2 PS-7a 판정(C-S8-72·73·75 A), IMU 선정에 0.119° 반영(10.6절), `P3B_US_PER_STEP_UPPER` G1·S1 5500 µs(J1·J2 9000 유지), 재레벨 문턱 문서 정리(dynamics 5.38.4 → 0.07°).

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
