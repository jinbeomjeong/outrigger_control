# v5 재개 검증 436.8 판정서 — Chrono 부분 (제어기 `final_C4G2_LAS_K1`)

- **상태: 커밋 판(정본).** 판정 후 감사·재감사 2회(차단 0)와 integrity 점검을 거쳐 사용자 결정 96·111대로 커밋한다. 정본 위치는 `06_analysis/02_control/verif_matrix/v5_resume_4368_judgement.md`(원판 13절)다. 종합 문장(0.2절)은 사용자에게 먼저 보였고, 사용자가 끝 문장까지 그대로 쓰기로 했다(사용자 결정 109, 2026-11-16).
- **범위**: Chrono 묶음 C-1~C-8(O-C5 probe 포함)과 그 두 경로 판정. 하네스 묶음 H-0~H-10(R4)은 판정 전이므로 이 판정서의 하네스 절은 비워 두고 "하네스 R4 판정 뒤"로 적는다. **v5 종합 판정은 하네스 R4 판정 뒤 확정한다.** (갱신 2026-11-16: 하네스 판정은 `v5_resume_4368_harness_judgement.md`에 있고, v5 종합 판정은 `판정 불가`다 — 하네스 판정서 0.1·0.2절)
- 작성: control-expert, 2026-11-16. 판정 대상 출력: R3f `8a0c8432d23c9db0916bf6f9cb9139466bd32551`의 두 경로 출력(`06_analysis/02_control/verif_matrix/v5_resume_4368/judge_8a0c843/chrono_path1/`, `…/chrono_path2/`). 실행(시뮬레이션) 커밋 R2 `b9f5707d7f3f7a26230b25f4edbc1fec587ca612`.
- 수치는 모두 위 두 출력 폴더와 감사 리포트(`r3f_kr_cross_path.md` sha256 `1980bd4f74ae56077ff7da727cc8820d08aeaf157d7552695b1ecc31a81b22b0`, `r3f_postrun_audit.md` `9df13449b2678329ce953c614f025fb3be481dc0488d02fc24fc7a427a9a1af0`, `r3f_prejudge_audit.md` `a64952156e16055188141967c691263bc07371045cfc4747cc5b7eb6d0b8b11c`)에서 옮겼다. 출처를 찾지 못한 값은 `확인 필요`로 적었다(12절 목록).
- 규약: 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1, C2 음되먹임(다리 행정 속도 명령 [m/s], + = 신장). 힘은 실린더 순 힘 [N](표는 kN 병기), 압력 bar 게이지, 행정 mm, 각 °. $F_{min}$ = 9,414.589 N(YAML `control.F_min_cylinder_N`).

| 기호 | 뜻 | 단위 |
|---|---|---|
| $F_{min}$ | 다리당 최소 실린더 순 힘 문턱 9,414.589 | N |
| $F^{\mathrm{a}}_{min}$ | 크롤러 이탈 $t_D$ 뒤 기록 끝까지 다리별 1 ms 참 $F_{cyl}$ 최소 | N |
| $F^{\mathrm{t}}_{min}$ | 이륙 과도 구간 $[t_D, t_D + 8\,\mathrm{s})$ 다리별 1 ms 참 $F_{cyl}$ 최소 | N |
| $m$ | O-C5 행 네 다리 $F^{\mathrm{a}}_{min}$의 최소(원판 7.4) | N |
| $R_c$ | 운용 사용률 $\lvert\phi_c\rvert/4.4° + \lvert\theta_c\rvert/3.2°$ (CHECK 끝 크롤러 자세) | – |
| $k$ | O-C5 바닥 축척(바닥 = $k\cdot(2.3351°, 1.5017°)$) | – |
| `git_at_start` | 묶음 실행을 시작한 커밋 | – |

## 0. 판정 요약

### 0.1 묶음별 상태 (원판 8.1, 두 경로, 사용자 결정 107·108 적용 뒤)

| 묶음 | 경로 1 | 경로 2 | 확정(두 경로 같음) | 비고 |
|---|---|---|---|---|
| C-1 (J-3) | 통과(판정 6, 기록 4) | 통과(6 / 기록 완료 4) | **통과** | R3d와 같음 |
| C-2 (J-4) | 미달: 통과 2 / 안전 종료 2 / 미달 1 | 미달(S-01·02 `allowed_stop`, c-slow E-5 미달) | **미달** | PS-c c-slow 행 E-5 |
| C-3 (J-5) | 통과 2 | 통과 2 | **통과** | |
| C-4 (J-14, 기록) | 기록 완료 4/4 | 기록 완료 4/4 | **기록 완료** | 운용 시작 조건 밖($R_c$ 1.076 / 1.035) |
| C-5 (J-15) | 미달 26 / 9 → 결정 107 (3) 뒤 28 / 7 | CD-7 멈춤(판정 불가) → 결정 107 (2) 뒤 행 등급 28 / 7 | **미달 28 통과 / 7 미달** | P3b_J2 t180 계열 7행 |
| C-6·C-7 (기록) | 기록 완료 3 | 기록 완료 3 | **기록 완료** | |
| C-8 (O-C5, 기록) | 기록 완료 2 | 기록 완료 2 | **기록 완료** | C-8a S-9는 사용자 결정 60 (A)·88로 처리(L-5) |
| J_P 재사용(V5-JP-{VB,V0} 12행, L2b) | 재사용 참(R4) | 재사용 참(R4) | **재사용**(저장 판정 그대로, 하네스 판정서 4.14절) | 사용자 결정 110 (1). R4 하네스 판정과 함께 판독했다. 12행 모두 7.3 조건 참, 멈춤 표지 없음 |

- **Chrono 판정 묶음(C-1·C-2·C-3·C-5)의 최악: 미달.** J_P 재사용 12행은 R4에서 재사용 참으로 판독했고, 저장 판정(`v5_paper_runs_judgement.md` 2절)에는 묶음 등급 낱말이 없어 이 최악값은 바뀌지 않는다(하네스 판정서 4.14절).
- 하네스 묶음(H-0~H-12, C-9~C-11): `v5_resume_4368_harness_judgement.md` 0.2절. 최악 `판정 불가`(H-3 S-13, H-4 등급 키 부재; 436.9(rev26)에서 두 경로 도구를 보완한 뒤 재판정), 미달 H-9(격자)·H-10(J-P3), C-9~C-11 기록 불완전.
- **v5 종합 판정: 판정 불가**(사용자 결정 139, 원판 8.1의 순서 `판정 불가` > `미달` > `통과`). 판정 불가를 빼고 보아도 Chrono와 하네스 모두 미달 묶음이 있으므로 종합은 `통과`가 될 수 없다. 종합 문장은 `v5_resume_4368_harness_judgement.md` 0.1절이다.

### 0.2 종합 문장 (사용자 결정 109로 확정, 끝 문장 포함)

> 436.8 v5 재개 검증의 Chrono 판정 묶음은 실행 커밋 R2 `b9f5707`에서 돈 실행을 판정 도구 커밋 R3f `8a0c843`로 두 경로가 따로 판정했고, 사용자 결정 107·108을 적용한 뒤 두 경로의 묶음 등급과 행 등급이 모두 같다. C-1 통과, C-2 미달(PS-c c-slow 행 E-5: 탐침 소성 침하로 재레벨이 두 번 일어나 분기 끝이 READY가 아님), C-3 통과, C-5 미달(35행 중 28 통과·7 미달; 미달 7행은 모두 균일 J2 토양 t180 계열이고 7행 모두 P3-7, 그중 4행은 P3-6도 미달)이며, 기록 묶음 C-4·C-6·C-7·C-8은 기록 완료다. C-8a(운용 시작 조건 안 $R_c$ 0.952, 크롤러 강성 ×3·VB)에서 후방 좌측 실린더 힘이 크롤러 이탈 직후 5,869.6 N($F_{min}$ − 3,545 N, 0.158 s)까지 내려간 것은 사용자 결정 88에 따라 운용 범위 안의 제어기 한계로 L-5에 공개하고 설계 보완은 LAS-c 별건으로 넘긴다. 따라서 Chrono 판정 묶음의 최악은 미달이다. v5 종합 판정은 하네스 묶음(H-0~H-10) R4 판정 뒤 원판 8.1의 최악값으로 확정하며, Chrono가 미달이므로 종합 판정은 통과가 될 수 없다.

- **하네스 R4 판정 뒤(사용자 결정 139, 2026-11-16)**: 위 끝 문장의 "하네스 묶음 R4 판정 뒤 원판 8.1의 최악값으로 확정"에 따라 v5 종합 판정은 `판정 불가`로 확정됐다. Chrono 부분의 위 문장은 사용자 결정 109로 확정한 그대로 두고, 하네스와 합친 종합 문장은 `v5_resume_4368_harness_judgement.md` 0.1절에 둔다.
- 이 문장은 원판 8.1 "O-C5 멈춤이 걸리면 종합 문장은 사용자 결정 뒤에 쓴다"와 rev25 CD-11 마지막 글머리("등급 항목이 한 경로에만 … 있으면 … 판정서 종합 문장을 쓰기 전에 멈추고 묻는다")에 따라, 사용자 결정 88(C-8a S-9)과 108(CD-11 한쪽 등급 항목 123건) 뒤에 썼고, 사용자 결정 109(2026-11-16)로 끝 문장까지 그대로 확정했다.

### 0.3 멈춤과 사용자 결정 (원판 13절 2항)

| 멈춤·질문 | 조건 | 처리 | 사용자 결정 |
|---|---|---|---|
| C-8a S-9(원판 7.4·8.2) | $m$ = 5,869.617 N < $F_{min}$, $R_c$ 0.952 ≤ 1 | 멈춤 목록 밖, L-5 알려진 한계. R3d와 두 경로 모두 같은 $m$·최소 다리(CD-8 R3d 대조 참) | 60 (A), 88 |
| C-5 S-13(R3d) | R3d 두 경로 C-5 등급이 갈림(경로 1 판정 불가, 경로 2 통과) | rev24 공통 블록 → R3e(폐기) → rev25 → R3f 재판정 | 89, 90, 91, 92, 95, 98~101 |
| J-P3 위반의 H-7 멈춤(R3f 판정 전 감사 Q1) | 경로 2 도구는 미달 표지만 남김 | 판정서는 멈춤으로 읽음. **위반 0행**(두 경로) | 102 |
| R3f 허용 목록 밖 범주 안 키 4곳(판정 후 감사 Q1) | R24-3 재판정 2 | 허용(공개, 7.6절) | 107 (1) |
| 경로 2 C-5 CD-7 빈 사유 11행(H-9) | CD-7 | 도구 수정 없이 사유 문구를 판정서에 적고 행 등급 28 / 7 미달 | 107 (2) |
| C-5 S9SL 2행 등급 갈림 | 427.9 분기 범위 | 경로 2 읽기(427.9 안전 종료) 채택 | 107 (3) |
| CD-11 한쪽 등급 항목 123건(누락 점검 4 거짓) | rev25 CD-11 마지막 글머리 | 등급 영향 없는 표기 차이로 공개, 도구 수정 없음, rev26 후보 | 108 (1)·(2) |

### 0.4 사용자 결정 (원문 요지)

| # | 날짜 | 요지 | 반영 |
|---|---|---|---|
| 60 | 2026-11-15 | ① C-8a S-9는 (A) L-5 알려진 한계로 공개, 원인 진단은 436.9, 등급 불변. ② C-2는 rev18 + R3b 도구 보완으로 재판정 | rev18 R18-5, 4.7절 |
| 65 | 2026-11-15 | `allowed_stop`(427.9 안전 종료)을 묶음 등급의 통과 쪽으로 센다(결과 본 뒤 정한 정의, rev19 R19-1). 경로 2 출력의 공개 문구 그대로 | 4.2·4.5절 |
| 86 | 2026-11-15 | 경로 2 기록 K-10 '다름' 5건(`tool_gate.head`, `argv[3]` 출력 경로, `created`)은 일치 처리, 실행 정체성 키를 K-10 제외 키로 명시(rev24 CD-10) | 7.6절 |
| 88 | 2026-11-15 | C-8a S-9(RL 5,869.6 N, $R_c$ 0.952)는 '운용 범위 안 제어기 한계'로 L-5에 기록하고, 설계(이탈~`is_lifted` 사이 가벼운 다리 보호 공백)는 LAS-c 별건. 개입 실행 2행은 436.8 판정 뒤 별건. C-2 E-5는 탐침 소성 침하로 재레벨이 두 번 일어난 것으로 제어기 오동작이 아니다. C-4 P3-5 표본 0은 rigid_base라 구조적으로 해당 없음. 이 둘은 436.9 입력 | 4.2·4.4·4.7·10·11절 |
| 89 | 2026-11-15 | (1) C-5 S-13은 rev24 뒤 두 경로 재판정 (2) C-5 항목 범위 R18-2(P3 포함) (3) C-8 기록 상태는 R18-5대로 기록 완료 (4) 작은 불일치 공개와 정리 | rev24 |
| 90 | 2026-11-15 | (1) CD-5 READY 없음 (2) 공통 정의를 C-1~C-5에 적용 (3) C-4는 다른 결측이 없으면 기록 완료(결정 88이 R18-6보다 앞섬) (4) 경로 2의 원 판정기 직접 실행 허용과 독립성 공개 | rev24·rev25 |
| 91 | 2026-11-15 | L-5 틀 문장 수정을 rev24 R24-5에 넣는다(dynamics-expert 판정, A5 확인, `L5_proposal_report.md` sha256 `74f74e0d0ee95a9e4b94a049c8ff6ab5f1c8b2f507c5b7e01b8174fe62f6556b`) | 10절 L-5 |
| 92 | 2026-11-15 | (1) C-5 사건 행은 6행(`E_RE1bF_` 4 + `G1R_FS24_` 2), `E_G4_` 7행은 비사건 규칙 (2) L-5 (다) 문장을 (가) 새 문장 뒤로 | CD-3, 10절 |
| 95 | 2026-11-16 | 공통 블록과 경로별 몫이 어긋나면 공통 블록이 앞선다. "`event_t_s`만으로는 사건 행이 아니다". R4 하네스 지시문 때 판정 정의 출처 표 점검 | rev25 |
| 98 | 2026-11-16 | Q1 C-5 SCM 행 P3-6 판정(한계 421.1 표), Q2 C1 D8 사건 시각 절단, Q3 CD-11 대응 규약, Q4 CD-8 기록 값 | rev25 |
| 99 | 2026-11-16 | CD-9 C-4 기록 값에 D8·G6을 넣지 않고 rev24 그대로, C-4의 D8·G6은 436.9로 | rev25, 10절 |
| 100 | 2026-11-16 | (1) rigid_base P3-5 해당 없음을 C-4·O-C5 전체로 (2) READY 없는 C-3 행의 G6-4·G6-5 해당 없음 | rev25, 10절 |
| 101 | 2026-11-16 | C-1~C-3의 J-P3는 두 경로 모두 등급 항목 | rev25 |
| 102 | 2026-11-16 | J-P3 위반 시 H-7 멈춤 유지. 경로 2 도구는 미달 표지만 남기지만 판정서는 멈춤으로 읽는다. 위반은 0건 | 0.3·7.5절 |
| 107 | 2026-11-16 | (1) 범주 안 키 누락 4곳 허용 (2) 경로 2 C-5 CD-7 멈춤은 도구를 고치지 않고 처리: "H-9: M2 끔이라 해당 없음, CD-1 목록 밖 기록 항목"을 적고 행 등급으로 미달 28/7, 이 처리를 공개 (3) S9SL 2행은 토양 가드 정지 행으로 보고 427.9 분기 적용(경로 2 읽기). 결정 90의 "S9SL 미달"은 427.9 분기를 모르고 쓴 추정이었다는 점을 공개 | 4.5·7절 |
| 108 | 2026-11-16 | (1) CD-11 한쪽 등급 항목 123건(K1~K4)은 등급 영향 없는 표기 차이로 공개, 도구는 고치지 않고 경로 1 목록 분류는 rev26 후보 (2) S9SL CD-11 표는 경로 2의 427.9 목록을 정본으로. J11 표기 차이 35건, C-4 목록 경로 1 없음, C-2 S 행 P3-6 잠복 차이는 공개만 하고 rev26/436.9 후보 | 7.4절, 11절 |
| 109 | 2026-11-16 | 판정서 종합 문장(0.2절)을 끝 문장('Chrono가 미달이므로 종합 판정은 통과가 될 수 없다')까지 그대로 쓴다 | 0.2절 |
| 110 | 2026-11-16 | 판정 후 감사 Q1~Q6, 모두 감사 권고안: (1) J_P Chrono 12행 재사용 판독은 R4 하네스 판정과 함께 하고 이 판정서에는 "R4와 함께 판독, 미포함"으로 적는다 (2) 대체된 앞 단계(R3·R3b·R3c·R3d)의 기록 의무는 "R3f로 대체됨"을 공개하고 목록과 출력 위치(sha)만 싣는다 (3) R2 Chrono 본 실행 전 감사 리포트와 경로 1 최초 R3 보고의 "읽은 것"은 앞 세션 transcript에서 찾아 인용하고, 없으면 "원문 미보유"로 공개한다 (4) 사전 예측 P-7·P-11·P-11b는 출력 키가 없으면 "확인 못함"으로 공개하고 R4 때 다시 본다. R19-10·R20-3·R21-6의 "한계 절에 그대로" 문장은 10.2절에 원문을 직접 싣는다 | 0.1·3.1·5.2·6·7.1·9·10.2절 |
| 111 | 2026-11-16 | 커밋 대상 출력은 재감사 권고안 그대로: 판정서와 `judge_8a0c843`·`judge_0220671`·`judge_f9bc3c7`을 커밋하고 `.gitattributes` `-text`를 먼저 건다. G-S, 대체 단계 출력, R4 몫은 추적 밖으로 보존한다 | 9.2절 |
| 34 | 2026-11-13 | 본 실행 뒤 판정서 커밋까지 자동(판정 후 감사 차단 0·integrity 뒤). R2 실행 전 감사: 차단 1(Chrono 러너 `--only-file` 경로) 고침, 판정 전 키 경로 확인 단계 넣기, `probe_not_judgement` 공개 | 9·10.3절 |
| 41 | 2026-11-14 | Chrono 판정 도구 결함은 worktree에서 고치고 하네스 뒤 병합(R3). C-7b `v5_hydraulics` 부재 = 정상(V0 해당 없음, 공개). C-4 끔 팔 `liftoff_approach_slow` 결측 = R7-4 허용 결측. C-2·C-8 본 행은 R2·P 8–15에서 실행 | 4.6·10.3절 |
| 62 | 2026-11-15 | rev18 봉인 뒤 원 경로 2 작성자 에이전트를 맥락 소실로 부를 수 없어 새 작성자로 바꾸고 공개(경로 1 비공개, rev18 R18-3 정의 문장과 경로 2 README만 넘김, rev 개정 없음) | 7.1·10.3절 |
| 70 | 2026-11-15 | R21-2 [사실]의 "5a rocking 9행(C-2 2, C-5 7)"은 진단 JSON 기준 8행(C-5 6)이다 → 판정서 한계 절에서 정정 공개(봉인본 수정 안 함). rev21 인계 파일 `e9744fac`은 R21-1 안의 결과 문장 1개를 메인 세션이 지운 판이다(공개 대상) | 7.1·10.3절 |
| 83 | 2026-11-15 | R3d 판정 전 감사 차단 2 처리: 경로 2 README 메모 줄 지우고 R3d 다시. 경로 1 스크립트의 옛 R3 compare 단계 삭제는 변경 3으로 인정. 판정서 공개 2건: 경로 1 작성자의 봉인 뒤 R3c 이름 열람, S10 본문·rev22 `.sha256` 설명의 경로 1 구조가 경로 2 브랜치에서 보인 것 | 3.1·10.3절 |
| 84 | 2026-11-15 | R3d 재생성 `0220671`. 덩어리 분류 문장(판정서에 실음): 경로 2 `4a80c5a..3d0c05f`의 README `@@ -4,2 +4 @@`은 해시 줄 + 결정 83에 따른 rev22 메모 줄 되돌림, `f9bc3c7` 기준 순변화 0줄로 S-11 아님 | 3.1절 |
| 93 | 2026-11-16 | rev24 재감사 뒤: 메인 세션이 결정 92 질문 때 "E_G4 값은 아직 보지 않았다"고 했으나 작성자는 감사 리포트로 13행 이동 압력 범위 136.4~189.1 bar와 G1R 두 행 값을 봤다 → 사용자에게 정정 고지, 사건 행 6행 유지 + 공개 문장을 사실대로 | 10.3절 |
- 결정 34·41·62·70·83·84·93은 메인 세션 결정 기록(`memory\gs-4368-decisions-20261113.md` 48·55·76·84·97·98·107행)에서 요지를 옮겼다(읽기 전용).
- 공개(결정 107 (3)): **결정 90 기록 때 메인 세션이 옮긴 "S9SL 2행은 FAULT0·P3-6으로 미달" 문구는 427.9 안전 종료 분기를 모르고 쓴 추정이었다.** R3f 판정에서는 경로 2 읽기(427.9-1~5 모두 참, `allowed_stop`)를 따른다.

## 1. 규칙·기준 파일과 sha256 (원판 13절 1항)

### 1.1 규칙 원판과 덧붙임 판 (26판, 이 판정서 작성 때 다시 잼, 원시 바이트 = `.sha256` 첫 토큰)

| 판 | sha256(파일, 원시 바이트) | `.sha256` 첫 토큰 일치 | 봉인 시각(`.sha256` 기록) |
|---|---|---|---|
| 원판 | `9019b405b7a196f28a756e7ca91f443f6241a58bd8e1eee0361483066cb19524` | 일치 | 2026-11-13 00:46:07 +09:00 |
| rev1 | `d9094fda104e25ac7eb7aea44d7c34d8215a839fc3771aa50b224d43082f02c7` | 일치 | 2026-11-13 01:49:34 +09:00 |
| rev2 | `497e4614d6780c3201027b3946e3c21da05e2fefe9a3609436bc35ea664c3199` | 일치 | 2026-11-13 02:30:11 +09:00 |
| rev3 | `dad8dfa68da7a988971f4d687706465289ec7dd95d09079c92215c64e5eae557` | 일치 | 2026-11-13 03:13:21 +09:00 |
| rev4 | `7ea87a30b08a00263c597d42d3450dc56f68952e8d3205604cb2c5bab5dce14b` | 일치 | 2026-11-13 03:47:45 +09:00 |
| rev5 | `452a8436c547e4da8d78205556cbb37633842d42cb98c18849cb883d827b3aca` | 일치 | 2026-11-13 07:32:14 +09:00 |
| rev6 | `809e563971ea451aba7c9d0787c660bdcab1c495af39c513c8f158e09b4fe6c9` | 일치 | 2026-11-13 07:49:42 +09:00 |
| rev7 | `e81f7d31779b0d69a140c9d90aa4684f3c9299e84aec6af06b13d48d58631502` | 일치 | 2026-11-13 09:56:53 +09:00 |
| rev8 | `3ecafaaf33d84bb6f34a8cef5401771832a4999e4930f3644caff56eed640e56` | 일치 | 2026-11-13 10:47:09 +09:00 |
| rev9 | `4cf7843ce469df511d7b99c7236f0b245afae9fb4ba5ad903e1c2da823a59a6d` | 일치 | 2026-11-13 11:51:57 +09:00 |
| rev10 | `62a0bd8dd6644f78bf37d052e884061d8c14e1cc96e2babc72a6ac0618f12c29` | 일치 | 2026-11-13 12:29:18 +09:00 |
| rev11 | `9bac452470faf74f921aa7474b3dabad781dac1ba6c3493aff998e69e430617f` | 일치 | 2026-11-13 13:57:36 +09:00 |
| rev12 | `78f1f99b1bb27473d6e3317c58af195cc3b477829ca1439f390aeeaf32565140` | 일치 | 2026-11-13 14:58:03 +09:00 |
| rev13 | `383bffc1f2d920dbba5b5a8c0871786a43e983d83e2d5c1e477718257f70973b` | 일치 | 2026-11-13 18:03:52 +09:00 |
| rev14 | `baedeab499133214804167dede4c4674f9edba4e67bd711dd6418a561f60ac3f` | 일치 | 2026-11-13 19:46:05 +09:00 |
| rev15 | `0162561c3866412f06ef3be0b3a62434e4a9ba5a37c9003be4df2f373af545ef` | 일치 | 2026-11-15 00:08:30 +09:00 |
| rev16 | `b38991943a565a020488d1046dd6e0b5c71276cf925715fa5ba844d8819d0683` | 일치 | 2026-11-15 09:58:22 +09:00 |
| rev17 | `9400660e2f228c3bdfaf26b1eb36cf08a753e7ebc49fbcdedc4a8ab4e0b92422` | 일치 | 2026-11-15 10:51:35 +09:00 |
| rev18 | `3693a69c3f04eb6c5b26556ec5997d081e38f8f6fa6a581aee66ba512d122a9e` | 일치 | 2026-11-15 14:28:43 +09:00 |
| rev19 | `7f87b8bb091d23c1bdcd2bf356b732a77bea12c4cfc4853d0ea58f7d239c92b2` | 일치 | 2026-11-15 15:25:13 +09:00 |
| rev20 | `615a8fbd82f4ef93f1ca76b3fb4d5c24a2e602e63a997c7c56119fcc73fb5531` | 일치 | 2026-11-15 15:54:50 +09:00 |
| rev21 | `ecd709495f203eae1769ae42e67b5ae5bf2fb457146b558c12e46d636ed03f9a` | 일치 | 2026-11-15 16:41:22 +09:00 |
| rev22 | `a48a81f9a71091aab40f643d48ae65ba559a5c0c629e02ef3145745a095f9328` | 일치 | 2026-11-15 18:24:06 +09:00 |
| rev23 | `fa72e1726f87f686093e36f2f3f489d5b135df6392de6aae7fe91b8739b56f97` | 일치 | 2026-11-15 20:27:59 +09:00 |
| rev24 | `f475cf77bc610802aa36026394cbe8dbae74745c8889ac203b53a6430e1e1e15` | 일치 | 2026-11-15 22:51:49 +09:00 |
| rev25 | `c0b778fd3f53996a2caed37e373975afea591b3c798784843cb9e7eeaac6f233` | 일치 | 2026-11-16 01:09:01 +09:00 |

- 봉인 후보 초안(같은 폴더 `<판>_seal_candidate_draft.md`, 봉인본과 머리 1·3·5(·9)행만 다름)의 sha256:
  - 원판 초안 `8dce4e3a838f902c425fe75952eeb6a39051a010db46c720ca6cd3b1b5c3d905`
  - rev1 초안 `187b6c2ddbd125cbb56bf56cb8960af94328b15d98dbc37e761cda047636d4cf`
  - rev2 초안 `3fbb990ac1a3ee9fc5b828e1e0976a05d63ded4fde3d08673a8f37a7e8d6cad4`
  - rev3 초안 `2919e3bbead6cbc2731405fd370ab8e803c9132f3715b951f898669fb73809dd`
  - rev4 초안 `be8feeaabeb182801db5c52bb63843ab40bd3904bd030acc9809aef7673b432f`
  - rev5 초안 `9881e0e6038b524048ef8fdb65ff512b8f9a1052ebde38dbab508791444d178e`
  - rev6 초안 `e9341fdc58b1cce9a220fe8094ebb9cbc806018ef8462c8c0d413c3547274299`
  - rev7 초안 `8539ee311aacd80c1e169c4f899ec6d1b62055b3d5bbb4d21863286e94bb0649`
  - rev8 초안 `8dcd2cb3ea591d42e1ab386a4888eb6529628efe744a6eef292c372c72ec60d1`
  - rev9 초안 `f7025830cbe5cf3904cfd1840387dbc83234d6270ebaf36c52ee45ccdaeaa6fd`
  - rev10 초안 `5739ac6694ed5044920e8831d6d964274b6d732efabaa57681c93d74f72e2d5d`
  - rev11 초안 `ccdf42b2ffb92190d87aaa9c045e73fc4b209bc5f303fe2d656d057512fafe2b`
  - rev12 초안 `45dcf2f959b72636215453a41783aed3896b57799c310e51a69867d3de384af0`
  - rev13 초안 `5f0658de35c126dfc027ea01fd887f2249b7f69ce6aede729cab8236e506fc57`
  - rev14 초안 `d46ca3fd56b5afcbb0783b0e06524710aed599152cb15faa72bdb49c53e90242`
  - rev15 초안 `1107aa2415f4f5d988109d8c259c34bdee391563dc4ee4d211d70d5e77ba393f`
  - rev16 초안 `292b1420e9e32e31e2cac4e58a06941d54a1277959d0be4dc4d9c6b70a3f3913`
  - rev17 초안 `121e72581fdbf608c153faf57c409946d52a7cbf0474d53fddb6e08df2e0b442`
  - rev18 초안 `1488d87546331d1d0b283f0ee0c94eec5c88ee0372c6fe4e565dee22bb9eef98`
  - rev19 초안 `631bd2ff4b9063ec37bd6db60786010402161f64450d3e98e52e4e34ea4226c8`
  - rev20 초안 `ceca2c2596f8172c69863c1fd83b592ccf69f49ccd45113995d740b311952283`
  - rev21 초안 `39cb349f46cc96e948eec4d887b86fa81025bcac1629684e4d318c3571c598e5`
  - rev22 초안 `787de1cd2ba1fcb0682cf4e738faf29a9f1925ee56d5e33b778cdbfe01a0d057`
  - rev23 초안 `dde11cdb640d27948bd10f6012f2ed182fbc99e52c8cf6d91a0f578f85f26ea8`
  - rev24 초안 `75fca3cc8de490bdd5e43ad74ebb2e850fd3984a3a1d8a3da0399a06aae78cd7`
  - rev25 초안 `c1f28d6230245ec81ac7dec134e407d4e25d9276c957924939adc2dee66c2dd0`


- 26판 모두 원시 바이트 sha256이 `.sha256` 첫 토큰과 같다. 그래서 rev2 R2-9·rev3 R3-F4의 "CRLF 변환만 다름" 처리(원시 다름·LF 정규화 같음)에 해당하는 판은 **0개**다.
- 경로 1 도구 봉인 목록(`RULES_SEALS`)과 경로 2 `p2_rules.SEALED`의 436.8 규칙 항목은 24개(원판, rev1~12, rev15~25)로 이름·sha가 같다(R3f 판정 전 감사 3절, 독립 비교). rev13·rev14는 R13-7·R14-7·R15-7에 따라 Chrono 도구 봉인 목록에서 의도적으로 뺐다(`seal_check` `code_pin_missing` 2건, 결함 아님).
- R3f 두 경로 실행의 봉인 확인: 경로 1 `seals_rows_judge`·`seals_bundle_grade` 종료 0(묶음 출력 `seals.ok` 참, `missing` 빈 목록), 경로 2 `01_p2_chrono_seal` 종료 0(`ok` 참)·`06_p2_4368_seal` 종료 0.

### 1.2 원판 부록 A 기준 파일 (34개)

- 이 판정서 작성 때 원판 부록 A의 34개 파일(v5 기준 원판~개정 12b 15, `d1_selection_rules` 2, `u3_u6_rerun_rules` 3, `u9_targeted_rules_rev1` 1, `las_targeted_rules` 원판~rev5 9, `las_k1_rules_adopt2`·`adopt_rev1` 2, `las_p5r4_k1_judgement.md` `5e9fb33b7419d624d8dc305ad93121be090802cc5c85ea29fbc823e019fc9e2f`, `v5_resume_4368_plan_draft.md` `141e4958f39b7c7470bb4c66003877f2af0c14c93300a705eb60988e2a04033d`)을 다시 쟀다: **원시 바이트 34/34 일치**, LF 정규화로만 같은 파일 0, 불일치 0.
- 34개 표(원판 부록 A의 sha256과 이 판정서의 재측정):

| 파일 | sha256(원판 부록 A) | 이 판정서 작성 때 다시 잰 원시 바이트 |
|---|---|---|
| `06_analysis/03_hydraulic/coupled/v5/v5_criteria.md` | `06ed0384fb942cfdf9ab481878ffd5f19d5faab4e6163aa986dcdda5156e080e` | 일치 |
| `06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev1.md` | `cbfac2b2de571500fbf5410dd5456bfa82d4a05cf25f21c76feb25fab1308fab` | 일치 |
| `06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev2.md` | `e120474b8ebd721e6edc4fec8eef811ce810006b8c489e38cecbb7ae5caeed77` | 일치 |
| `06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev3.md` | `7084da25c6129681086efc4fbc5afb315d7b4d424cbed123746ec32b4ea61ec2` | 일치 |
| `06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev4.md` | `642e96f9cfd20a9c2a016ed128a6ce7d584718e5728d6008640f8703a5acbd72` | 일치 |
| `06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev5.md` | `945f714660cd3ec7e749151bcd81b1f9da35b6001d7fd9c7e2cfeee21fcd320b` | 일치 |
| `06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev6.md` | `fd5117031ef460cf4c6aa74807b2e73de984b014abb89a952b593499841da39c` | 일치 |
| `06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev7.md` | `9ccde7a5a4128317ed832dd2f92cd2368280f18cefa6827f1b1731c6d4e9aab3` | 일치 |
| `06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev8.md` | `c6ec89f71c1d8de4c06000568c2e5978fd7f9fe58a53defea728f2f4886bb25f` | 일치 |
| `06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev9.md` | `3c50dda50ca6dca60177f26d91d86c009eeb4f9321f5ffd0c98ddc27cf62e981` | 일치 |
| `06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev10.md` | `bd65db24f68a6d4c3a8346447a0cbfdd89e97cd07f4b295237127c304174e182` | 일치 |
| `06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev11.md` | `ca6b5c95d8f544ff8ec5db2e1ec193d2b200df74c2e9c7decdb56b61757e2ecb` | 일치 |
| `06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev12.md` | `e02d63cc1290383ee85d9a1f3a20c6348224b60999cccaf8d587cf610c5f5eb2` | 일치 |
| `06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev12a.md` | `e171141dce180fbb48493b9b95503ff3577d16f17cc54061ce3ad6e9efd51458` | 일치 |
| `06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev12b.md` | `0d17f87e9532d558efcab9fa89648e2790ece9c7568a802fbaa4c7631824e75d` | 일치 |
| `06_analysis/02_control/verif_matrix/d1_selection_rules.md` | `51dea528e57fa0c4378cda110addb73da20339535e16189452af2d06b60736e9` | 일치 |
| `06_analysis/02_control/verif_matrix/d1_selection_rules_rev1.md` | `eb730bddae35e76bc2569503605dea714b066fa42de7bc7b98efdde3edb3e868` | 일치 |
| `06_analysis/02_control/verif_matrix/u3_u6_rerun_rules.md` | `8de318825764114ad14afcec362c87c1e01a2ad47195b8491b1c96056e1960b3` | 일치 |
| `06_analysis/02_control/verif_matrix/u3_u6_rerun_rules_rev1.md` | `2c5e69213b29fc930c478306676efc72b515d67af08634adab3eba2d05f5f15d` | 일치 |
| `06_analysis/02_control/verif_matrix/u3_u6_rerun_rules_rev2.md` | `be1584a4448d68a30c4fe9ec613d3d7b3cb0b47169c2f5eff72e9a9ca0776880` | 일치 |
| `06_analysis/02_control/verif_matrix/u9_targeted_rules_rev1.md` | `644005b706ba46cebba11b975ded474226cc4eab5030ee18e9f91dacd2d14587` | 일치 |
| `06_analysis/02_control/verif_matrix/las_targeted_rules.md` | `00b48fd834d81b9d499015f2d44380623e9fbcb2f1515913a8fd0589503eaf40` | 일치 |
| `06_analysis/02_control/verif_matrix/las_targeted_rules_rev1.md` | `0d5f59f8e4a09448b93e0cde42adb7d23c2f99f6b365809876efaa6212d27625` | 일치 |
| `06_analysis/02_control/verif_matrix/las_targeted_rules_rev2.md` | `6be736cb98cea34e4a606606b4009668bbc1470c8a7db23b6a119ef033c97960` | 일치 |
| `06_analysis/02_control/verif_matrix/las_targeted_rules_rev3.md` | `956f65c74e36eb8fe921dc6399b0d5f2f04099b7852380362351f658c9791cd1` | 일치 |
| `06_analysis/02_control/verif_matrix/las_targeted_rules_rev4.md` | `05fbde22009c10b74ddf0df071452a99631bb319c2f482df83be59adfad1de6d` | 일치 |
| `06_analysis/02_control/verif_matrix/las_targeted_rules_rev4a.md` | `3cbbfb5d8afda9075bf9631accf1b8bee4c1ee02edafa34a7869091175a73b15` | 일치 |
| `06_analysis/02_control/verif_matrix/las_targeted_rules_rev4b.md` | `add921e4978ef16abcc22dfc88dc25e51a770dc98d2d540526f48cf6ea7a6f3f` | 일치 |
| `06_analysis/02_control/verif_matrix/las_targeted_rules_rev4c.md` | `7e45993f667382f56aeb1b72bb5e7023ecfe3048a3723ac050cefc3b2a721417` | 일치 |
| `06_analysis/02_control/verif_matrix/las_targeted_rules_rev5.md` | `879d0e4d715b2e9f4e51257863fc259ccfe48105ca019299547d58dca24949b2` | 일치 |
| `06_analysis/02_control/verif_matrix/las_k1_rules_adopt2.md` | `fb3a5696f24385e81acc9c564500b5e5a0547db45a5335272e7d18400f1e68e8` | 일치 |
| `06_analysis/02_control/verif_matrix/las_k1_rules_adopt_rev1.md` | `730dbb3d30dffca6d652953c22b62563141beeee6af6f045d6b2cb59f60deb65` | 일치 |
| `06_analysis/02_control/verif_matrix/las_p5r4_k1_judgement.md` | `5e9fb33b7419d624d8dc305ad93121be090802cc5c85ea29fbc823e019fc9e2f` | 일치 |
| `06_analysis/02_control/verif_matrix/v5_resume_4368_plan_draft.md` | `141e4958f39b7c7470bb4c66003877f2af0c14c93300a705eb60988e2a04033d` | 일치 |

- 원판 1.2 "읽은 것"에 적힌 `las_p5r4_k1_judgement.md`, `las_k1_rem_judgement.md`, 명세 `00_docs/04_control/s6_control_spec.md` 436·437절, CLAUDE.md 기준값 표는 규칙 작성 때의 근거다. 경로 2 출력의 `seal.recorded`에는 명세 `s6_control_spec.md` sha256 `1924ae89a02752761f7b1e494304843f5c99d29c59d3989f7671ee258143be16`이 기록돼 있다.

### 1.3 rev25 공통 블록

- rev25 봉인본 35~146행의 두 표지 줄 사이 블록 sha256 = **`0e082b9c3b3ce3ff384a5cbf5d62da41bf766c423411d5eb3395217c79630b5d`**, `- **[공통 정의]` 줄 11개(K-R 감사자가 봉인본에서 다시 뽑아 잼). 두 경로 작성자 모두 넘김 문장에서 같은 값을 확인했다고 보고했다(7.1절 "읽은 것").

## 2. 커밋과 실행 정체성 (원판 13절 1·3항, 6절)

### 2.1 `git_at_start`와 커밋 계보

| 이름 | 커밋 | 뜻 |
|---|---|---|
| R2 (`git_at_start`, Chrono 전 묶음) | `b9f5707d7f3f7a26230b25f4edbc1fec587ca612` (2026-11-13 19:46:17 +09:00) | 모든 Chrono 실행의 `batch.json` `git_at_start`. 두 경로 판정 도구도 `--git-at-start` = R2(rev24 R24-3 재판정 1) |
| R3c | `f9bc3c775d09d0588adb388dec96614fd95f2929` | 러너 판정 출력·t45 재생 출력(재사용) |
| R3d | `02206710fe9ea77088d466f8a486afd5e130bceb` | 앞 판정 도구(대조 기준 출력) |
| S12 / S13 | `b75d8743ecb94f6beee2dc5ac1815a1552d97a20`(rev24) / `f381053628c4462d96914687c6e5ea209fd12de1`(rev25) | 봉인 파일 커밋(`z4373-s4`) |
| 경로 1 도구 커밋 | `086866a3d61322bba8a685dbcb457a20b4bd12ea`(rev24) → `f2cfe79`(S13 병합) → `3a61d4d3af225f738fa5f8ef1902fde0580a820d`(rev25) → **`c3f4cadf3ed1572c0d5b375b9b9fea76f0c34980`**(판정 전 감사 실행 전 수정 2) | `z4377-p1chrono` |
| 경로 2 도구 커밋 | `24481ad72ec2988972c0b293a12a8d54cd940810`(rev24) → `d32137f`(S13 병합) → **`0f2fd4e7bb4697d505f4d5b8a51ee656d5f5b9ac`**(rev25) | `z4377-p2chrono` |
| R3f (판정 도구 커밋) | **`8a0c8432d23c9db0916bf6f9cb9139466bd32551`** (2026-11-16 01:59:28 +09:00) | `z4373-r3f`: R3d에서 `f777e09`(p1 병합) → `8a0c843`(p2 병합), `--no-ff` |

- **판정 전 감사는 `1fadc06`에서 진행됐다.** R3f 판정 전 감사(`r3f_prejudge_audit.md`)의 대상은 통합 worktree HEAD `1fadc06fd7b5026d8076f903f6a099668fef9dfd`(경로 1 도구 `3a61d4d`, 경로 2 도구 `0f2fd4e`)였다. 감사가 "실행 전 수정 2"(경로 1이 PS-c 사건 행 `stroke_le_684.8mm`를 공통 ID 표 밖 등급 항목으로 둠, 대조표 g)를 냈고, python-expert가 경로 1 도구 브랜치에 **`c3f4cad` "436.8 R3f path 1: PS-c stroke item listed as a record under E-5 (CD-11, pre-judgement audit)"**(2026-11-16 01:58:32 +09:00)를 더했다. 그래서 통합 브랜치를 다시 만들어 R3f가 `8a0c843`이 됐다. `1fadc06`은 브랜치 `z4373-r3f-discarded-1fadc06`에 남아 있고 판정에 쓰지 않았다. 경로 2 실행 전 수정 1(K-10 비교기의 `created` 제외)은 저장소 밖 비교기(`k10_compare_r3f.py`)에서 고쳤으므로 경로 2 도구 커밋은 `0f2fd4e` 그대로다. `c3f4cad`는 CD-11 목록 분류 열만 바꾼 것으로 rev25 R25-2 [경로 1] 1 "CD-11 분류 열·조항 ID 열" 범위 안이다(판정 전 감사 권고).
- **`c3f4cad` 뒤 판정 전 재감사는 하지 않았다.** 대신 다음 세 가지를 했다(메인 세션 전달, 2026-11-16).
  - (a) 메인 세션이 `git diff --stat 1fadc06 8a0c843`으로 바뀐 것이 경로 1 3파일, +27 −5뿐임을 확인했다(이 판정서 작성자가 다시 본 `git diff --stat 3a61d4d c3f4cad`도 같은 3파일 +27 −5: `chrono_bundle_grade_4368.py`, `chrono_rows_judge_4368_README.md`, `test_chrono_bundle_grade_4368.py`).
  - (b) integrity-checker가 R3f `8a0c843` 전체 24파일을 점검했다. 결과 High 0, Low 3: ① 경로 1 README 191행 sha 표 출처 설명에 `c3f4cad`가 빠짐 ② `TOOL_VERSION`이 v7 그대로 ③ 경로 1 README 시험 개수의 '옛 값' 기준이 줄마다 다름. 세 건 모두 등급·판정 값에 영향이 없는 표기다(rev26 또는 다음 도구 커밋 후보).
  - (c) 이 수정은 판정 전 감사가 직접 요구한 것이다(실행 전 수정 2, 대조표 g, 권장 조치 "CD-11 목록에서 이 항목을 `E-5`의 기록으로 둔다").
- R3f 조건(rev25 R25-3): `git diff --name-only 0220671..8a0c843 -- 03_src 02_params` 빈 출력. 전체 diff 24파일 = (가) rev24·rev25 규칙 6 + `.gitattributes`(`-text` 6줄 추가, 지운 줄 0), (나) 경로 1 다섯 파일, (다) `path2_chrono/` 12파일(rev24 때 바뀐 `p2_b_c1.py` 포함; 판정 전 감사의 "11파일"은 `d32137f..0f2fd4e` 기준 셈), (라) 없음. `--is-ancestor`: 경로 1 도구 커밋은 `0220671`·`086866a`의 후손, 경로 2 도구 커밋은 `0220671`·`24481ad`의 후손(판정 전 감사 2절, `c3f4cad`는 `3a61d4d`의 자식). 원 판정기 코드(`03_src`, `run_S8C.py`, `run_S6C.py`)는 `b9f5707..8a0c843` diff 0(경로 2 로그 7행).
- 원판 A-5·rev8 R8-4~rev15 R15-1의 `git_at_start` 규칙: Chrono 실행의 `git_at_start`는 R2 하나이고(묶음마다 `batch.json`, `commit_identity_R11_4` 모든 행 `match`), R2 뒤 커밋은 R3·R3b·R3c·R3d·R3f 판정 도구 커밋(각 판의 허용 목록 안)뿐이다. 판정서·감사 기록 커밋은 이 판정서 커밋에서 처음 생긴다(R8-4 (라), R15-2 (바): `00_docs/decision_log.md`·`00_docs/00_roadmap.md`·`00_docs/handoff/session_handoff.md` 포함 가능). 열린 루프 행의 `result.json` `code_state`와 `git_at_start`의 같음(R12-4)은 `commit_identity_R11_4` `match`(C-6·C-7 3행)로 본다.
- G-S 도구 커밋과 `git_at_start`(rev7 R7-7·rev8 R8-4·rev14 R14-4): Chrono G-S는 R2 `b9f5707`에서 돌렸고(`gs_chrono_b9f5707\`, `gs_psc_b9f5707\`), 모든 묶음의 `git_at_start`도 R2이다. 그래서 `git diff --stat Y..GIT_AT_START`(Y = R2)는 대상이 없는 빈 diff다. 판정서·감사 기록만 더한 커밋은 아직 없다(이 판정서 커밋이 처음).

### 2.2 Chrono 묶음별 실행 기간·러너 로그 (원판 13절 1항)

| 묶음 | 배치 폴더(`07_results/S9/` 또는 `07_results/S8/`) | 실행 기간(러너 로그) | 러너 로그 |
|---|---|---|---|
| O-C5 probe | `batch_V5-RESUME-K1-OC5PROBE_20261113_215123` | 2026-11-13 21:51:22 시작, wall 315 s | `v5_resume_4368/run_b9f5707/logs/run_chronoA/a1_oc5probe.log` |
| C-6·C-7 | `batch_V5-RESUME-K1-C6C7_20261113_215638` | 21:56:37 시작, wall 1,954 s | `run_chronoA/a2_c6c7.log` |
| C-4 | `batch_V5-RESUME-K1-C4_20261113_222912` | 22:29:11 시작, wall 9,389 s | `run_chronoA/a3_c4.log` |
| C-3 | `batch_V5-RESUME-K1-C3_20261114_010541` | 2026-11-14 01:05:40 시작, wall 8,325 s | `run_chronoA/a4_c3.log` |
| C-5 SCM A | `batch_V5-RESUME-K1-C5_20261114_032426` | 03:24:25 시작, wall 27,897 s | `run_chronoA/a5_c5_soilA.log` |
| C-1 | `batch_V5-RESUME-K1-C1_20261114_110925`(+ S8 `v5s3_VB_D1C2_*_20261114_11*`) | 11:09:24 시작, wall 1,675 s | `run_chronoR/r1_c1.log` |
| C-5 L2b | `batch_V5-RESUME-K1-C5_20261114_113720`(+ S8 `v5s3_*_20261114_1*`) | 11:37:20 시작, wall 5,538 s | `run_chronoR/r2_c5_rigid.log` |
| C-5 SCM B | `batch_V5-RESUME-K1-C5_20261114_131025` | 13:10:25 시작, wall 24,043 s | `run_chronoB/b1_c5_soilB.log` |
| C-8 본 행 | `batch_V5-RESUME-K1-OC5_20261114_210626` | 21:06:25 시작, wall 4,748 s | `run_b9f5707/c2_oc5/logs_oc5/c8_oc5_main.log` |
| C-2 (4행) | `batch_V5-RESUME-K1-C2_20261114_222633`(+ S8 `v5s3_VB_D1C2_*_rollm4.4_Fs4_20261115_00*`) | 22:26:32 시작, wall 9,604 s | `c2_oc5/logs_c2_4/c2_main4.log` |
| C-2 PS-c (2행) | `batch_V5-RESUME-K1-C2_20261114_230123` | 23:01:22 시작, wall 18,047 s, 마스크 0xFF | `c2_oc5/logs_c2_psc/c2_psc2.log` |

- 러너 로그 폴더: `06_analysis/02_control/verif_matrix/v5_resume_4368/run_b9f5707/logs/`(`run_chronoA`·`run_chronoB`·`run_chronoR`)와 `run_b9f5707/c2_oc5/`. 모든 단계 `exit=0`(러너 `.out.log`의 `[end] … exit=0`, `[done] all steps complete`). `tools/verif/log_errors.py`를 이 폴더에 돌린 결과 파일은 이 판정서 작성 때 찾지 못했다 → `확인 필요`(9절).
- 위 S8(L2b) 배치 폴더의 정확한 목록은 경로 2 로그 18~49행(원 판정기 32회의 대상 폴더 이름)에 있다.

### 2.3 R3f 판정 실행의 정체성

| 항목 | 경로 1 | 경로 2 |
|---|---|---|
| 실행 시각 | 2026-11-16 02:02:59(R3c·R3d 전 대조) ~ 02:03:55(전후 대조 끝) | 02:02:59 ~ 02:07:11 |
| 배치 | P 논리 0-7(마스크 0xFF), 래퍼 `scratchpad\sched3\drive_p1.ps1`, 실측 `sched3\r3f_p1.sample.json` | P 논리 8-15(마스크 0xFF00), 래퍼 `sched3\drive_p2.ps1`, 실측 `sched3\r3f_p2.sample.json` |
| checkout | R3f `8a0c843`(실행 스크립트의 HEAD 확인: 다르면 S-12, 종료 2) | 로그 3행 "R3f HEAD 8a0c8432… (expected 8a0c8432…)" |
| 실행 스크립트 sha256 | `run_path1_r3f.ps1` `faf01f0e2451550685957e1b41b61551889534094b0b368a13d84877fc8bbbfc` | `run_path2_r3f.ps1` `61cf51b2f62e624375290176efe88c1b0b8212f8c39cf5625c78c3991929a182` |
| 감사한 초안과의 차 | 초안 `882578fe06cc0ebd73b14ba5169d84d850e0a6458a1927e5bd9f48961dee64bc`에서 자리값 2줄(`$R3fShort` = `8a0c843`, `$R3fFull` = 전체 해시)만 다름 | 초안 `2ea5556f454a2bd10c024ed982dfc1aa9472e75bcb0610efa7e4a6facdec7574`에서 자리값 2줄만 다름 |
| R3d·R3e 판과의 diff(초안 기준, 작성자 보고) | R3d 판 대비 +53 −21, R3e 판 대비 +32 −15 | R3e 판(`a99bcbea`) 대비 83줄, R3d 판(`5573b964`) 대비 188줄 |
| 허용 변경(rev25 R25-3 실행 스크립트) | 출력 폴더, 재사용 입력(R3c), R3c·R3d 전후 대조, HEAD 확인(S-12, 종료 2), C-1~C-3 등급 차이 자동 멈춤(종료 3), 전후 대조 실패 종료 4 | HEAD 확인(종료 2), `Get-GradeDiff`(종료 4), 전후 대조 실패 종료 5, 비교기 교체 |
| 비교기 | `compare_r3d.py` `0e8fad4a063437011eda2dcd7ffc646c8b565b0dcc3be8ee9ed804e2006eb53b`(R3e 판 대비 +7 −5, `compare_r3c.py` 대비 +114 −45) | `k10_compare_r3f.py` `cc92c5479ef69e63dc7222e0b42914100e00f4877ba1d61ad924e834b67291dd`(판정 전 감사가 본 초안 `f47a597f…`에서 `RUN_TIME_KEYS = {"created"}`만 바뀐 판, 사용자 결정 104의 실행 전 수정 1; R3e 판 `p2r3e\k10_compare_r3e.py` 대비 +34 −10줄(메인 세션 전달값). 판정 전 감사 초안 파일은 같은 경로에서 덮어써져 남아 있지 않아 이 작성자가 줄 diff를 다시 뜨지 못했다) |
| 허용 차이 키 목록 | `allowed_keys_path1.md` `e015509e9d191859a979c03e9e52584f30a8764594601c470d70c29525eaef8c` | `C:\workspace\_resume_4368_20261115\p2r3f_8a0c843\allowed_keys_path2.md` `7cbff3976086d212afcbe8c9e58b112603993d979b7948f9840a77cec5dbf395`(초안 `04ffc656…`에 사용자 결정 102 4절 추가) |
| 판정 도구 sha256 | `chrono_bundle_grade_4368.py` `git show 8a0c843:` blob `dd776429cb1e50f166030b6494a2f60af1d001cb8821ff48ded90adaa0982ae1`(`c3f4cad` 반영 판; `3a61d4d` 판 `4b1b0983…`), `chrono_rows_judge_4368.py` blob `dca1b3ab757b117c626ecc17148ae4fc2f1b5eb58cb5f1e2c5f9fa2c578bde15`. `-text`가 없어 작업 트리(CRLF)가 아니라 blob으로 적는다 | 공통 `e6fcc72aeb0b3354b4620af9d84e9b0300f2c0afe28fa3a684a9ee737c9f4e95`, 묶음별 C-1 `d3f927d7…`, C-2 `179666f7…`, C-3 `0a6e98c7…`, C-4 `79f12956…`, C-5 `757899909e03997c048ffb3d1a0848d24d8329048cb8145af5810d27d9982649`, C-6C7 `e18c42b4…`, C-8 `77e848ef…`; `p2_4368.py` `9e2673d5e50614346cfc86458ddc4f8afadea03250b98cb1fd224309f803c03d` |
| 시험 | 판정 전 감사 재현 510 통과 | 실행 중 `02_test_p2_synthetic` 413 실패 0. 작성자 보고 412와의 차 1은 SKIP 1건이다: 메인 checkout에는 `T45.REG_BATCH` 폴더가 있어 출처 확인 시험 1개가 더 돈다(R3d 감사 `audit-r3d\r3d_k10_record_audit.md` 4절에서 같은 원인 확인) |
| 출력 sha | 실행 스크립트가 `SHA256SUMS`를 쓰지 않아 K-R 감사자가 64개를 고정(부록 A) | `outputs.sha256` `d576ddf8350692ce84dc58018630e788f6082b62b61fe92b0a763201cfa0396c`, 121항목 모두 일치(K-R) |
| 실행 로그 | 단계별 `*.stdout.txt`, `exit_codes.json` `3f04ef86…` | `run_path2_r3f.log` sha256 `a2daa35cd3370a50834caa8bfaf45fed587b4c0cebeb8978dc42fcab620aa019`(**`outputs.sha256` 목록 밖**) |

- **R3c·R3d 전후 대조**(rev24 R24-3·rev25 R25-3 쓰기 금지와 전후 대조): 경로 1 `r3c_check_before/after` 120/120 같음(R3c `SHA256SUMS.txt` `12f1f5b4e437f7f552410fc52089cd287df323d437c3adbbdb11a5b18cb8d10c`), `r3d_check_before/after` 57/57 같음(R3d `SHA256SUMS.txt` `3a1b8a7a69540927bb5be00ec014b9a860bcbe1c19fd97c22af85b1606f41346`), 두 출력 파일 sha 전후 같음(부록 A). 경로 2 R3c `outputs.sha256`(`bd49fb6b7a95cfa9b9322e9578d678c7fa3637454c624317668469a0b6b6409f`)·R3d `outputs.sha256`(`096346c740c171bc10660dd8745587f99794ca39f4d036a15b996fa7775860bb`) 전후 "all entries match", R3d 실행 로그(목록 밖) sha256 전후 `ecf4b0f6f3f7bb7fff0a4522b9a0b592c48602100487d715759a1324756000c4`.
- **R3f 경로 1 view 단계 입력(rev18:62)**: `run_path1_r3f.ps1` 43·44행이 `$View` = `judge_576eb87\chrono_path1\chrono_view\`(R3 단계에서 만든 view. 폴더 실제 파일 43개 = `make_view.py` 1 + `view_map.json` 1 + 배치 하위 폴더 3개 안의 사본 41개(`batch.json` 등 json))를 정하고, 109행 `view_check`와 163~167행(`k1_class_view`·`record_check_view` 입력 목록의 C-1·C-2·C-5 L2b 배치)이 이를 읽는다. R3f 출력 `view_check.json`(`f26e1afa…`): `make_view_sha256` `adb01782ef7c89d88e8542b24b483b7a2cc3321f863e9d2321d21266685b8816`, `view_map_sha256` `1b2c500fa16630f3548a7d41acaf11c561a73d0680dcc7ef60930d8a06e36f59`, 41항목·82파일 대조(82 = `view_map.json` 41항목 × 원본(`07_results\S9\…`)과 사본(`chrono_view\…`) 두 쪽; `view_check.py` 38~40행이 항목마다 `sha256_source`·`sha256_copy`를 각각 세어 잼. 폴더 파일 수 43과 세는 대상이 다르다), `problems` 빈 목록, `reusable` 참. `make_view.py`는 git 추적 밖이고(rev18:62 "판정서 커밋 때 함께 고정") 이 sha로 고정한다. **R3f 판정 입력이므로 지우지 않는다.**
- **경로 2 원 판정기 직접 실행(CD-2 (1)~(3))**: 대상 S8 폴더 32개(C-1 6, C-2 2, C-5 24), 32회 모두 `exit=0`(로그 18~49행, 02:03:44~02:05:47), 출력은 자기 폴더 `chrono_path2\s8c\`(파일 32개). 원 판정기 코드 diff vs `b9f5707`: 없음, checkout `8a0c843`. 판정기 파일 sha256: `03_src/outrigger_sim/verify/s8_control.py` `3aa15db72e952bd7c6333776e6b2152e2729fc2ebb699794f492bb4cdb09bb09`, `s6_control.py` `d0c413308e273e21707a1359c9b78631825c0e1998ab7f3e5de4739ae0346f34`, `s6_bundle_c.py` `1d8f7dabf877e73a5cd6da64d2853f7be11ae4a7cfc9e3114e3a2d5354fa1410`, `04_scripts/02_chrono/run_S8C.py` `1e5d9fa20d7be634c107d12b1148cf0f5fffca74cc5f2d17901346b774067bb3`, `run_S6C.py` `7359bdd585b013b7df6bb7e43b54589bf7786fc697a6b68d039abb25b3134914`(`cd2_judge_provenance` 블록과 같음). 이 다섯 값은 작업 트리 원시 바이트(`core.autocrlf` = true라 CRLF) 기준이다. 경로 1 도구 sha는 git blob(LF) 기준이라 기준이 다르다(예: `s6_control.py` LF·HEAD blob은 `27c0c9db…`, 판정 후 감사 기록 5). 경로 1은 원 판정기를 다시 돌리지 않고 R3c 러너 판정 출력(`judge_f9bc3c7\chrono_path1\runner_judge\`)을 sha 대조 뒤 재사용했다.
- **하위 단계 종료 코드**: 경로 1 `oc5_C-8a` 1(C-8a S-9, CD-8로 처리), `k1_class_view`·`record_check_view` 1(열린 루프 3행 R18-2a 해당 없음, view sha `k1_classification_7_2_view.json` `3d174e10…`·`record_check_chrono_view.json` `058993f3…`가 R3d와 같음), `compare_r3d` 1(허용 목록 밖 범주 안 키와 C-5 상한 잘림, 7.6절), 나머지 0. 경로 2 `04_p2_chrono_judge_C2` 1(묶음 미달), `C5` 1(CD-7 멈춤), `07_p2_4368_chrono` 2(`stop_codes` S-9, R3d와 같음), K-10 단계 `different`(허용 목록 대조 대상), 나머지 0. 경로 2 로그 끝 줄: "C-1..C-3 grade change vs R3d: 0"(02:07:11). `grade_change_C1_C3.txt`는 차이가 0건이라 생기지 않았다(파이프 입력 0개, 판정 후 감사 2절).

### 2.4 6절 정체성 표 (SCM 행, 경로 2 `identity` 관문과 `placement_record`, 경로 1 `record_check` view)

| 묶음 | SCM 행 | `num_threads_chrono` | start env `OMP_WAIT_POLICY` | `pool` / `planned_pool` | `placement` affinity 마스크 일치·`power_throttling_off_ok` | 훅 | identity 관문 |
|---|---|---|---|---|---|---|---|
| C-2 | 3(S-01, S-02, PS-c c-slow) + 기준 행 1 | 4 (3행) | PASSIVE (3행) | pcore / pcore | 참·참 (3행) | fast, `fallback` 없음 | pass 3 (+ L2b 2행 pass). PS-c 기준 행에는 경로 2 `identity` 관문 없음(K-R 기록 8) |
| C-3 | 2 | 4 | PASSIVE | pcore / pcore | 참·참 | fast | pass 2 |
| C-4 | 4 | 4 | PASSIVE | pcore / pcore | 참·참 | fast | pass 4 |
| C-5 | 11 | 4 | PASSIVE | pcore / pcore | 참·참 (마스크 `0x0000FF00`) | fast | pass 11 (L2b 24행은 경로 2 `identity` 없음) |
| C-8 | 2 | 4 | PASSIVE | pcore / pcore | 참·참 | fast | pass 2 |
| C-6·C-7 | 3(열린 루프) | – | – | – | – | – | 해당 없음(R18-2a) |

- 경로 1 `record_check_chrono_view`(4.2 기록 확인): Chrono 64행 중 문제 행 3(열린 루프 C-6·C-7 3행, `expect_controller` 없음, rev18 R18-2a 해당 없음), `stop_S11` 거짓, 하네스 줄 0(하네스는 R4). 64행 = C-1 10 + C-2 6 + C-3 2 + C-4 4 + C-5 35 + C-6·C-7 3 + C-8 2 + O-C5 probe 2.
- 4.2 기록 확인 결과(원판 13절 3항, Chrono): 어긋난 행 0(열린 루프 3행 해당 없음 제외). `c2_setup.k1_order_gate` = `preset`·`k1_order_gate_effective` 참·`flat_soil_margin_order_gate` 참(경로 2 `identity` 관문 필드, SCM 22행). C-4 끔 팔 2행은 `--las-off --k1-order-gate on`(K1 분류 "LAS 없음"), rev15 R15-4에 따라 끔 팔 `liftoff_approach_slow` 결측은 허용 결측이다.
- `MIXED_HULL_MODE` 0, `fallback_reason` 0(경로 2 identity 관문, 판정 전 감사).
- 태그 대조(원판 13절 3항, rev7 R7-1a·rev9 R9-1): 경로 2 `p2h_chrono.json` `R9-1_expect_controller` 대조 행 61, 어긋난 행(S-2) 0. 경로 1 `record_check_chrono_view` `expect_controller_failed_R9_1` 3행은 열린 루프 3행(해당 없음).
- dirty 기록(rev12): 경로 2 묶음 출력 C-1~C-8의 `dirty_record` 62행 모두 거짓(참 0행).
- 행마다 폴더를 찾은 방법(rev7 R7-5·rev12 R12-5, 경로 2 `p2h_chrono.json` `R7-5_row_folders`): `case_log` 36행(C-1 10, C-2 L2b 2, C-5 L2b 24), 그 밖 `batch_folder`(C-2 SCM 4, C-3 2, C-4 4, C-5 SCM 11, C-6·C-7 3, C-8 2), `case_log_relocated`·`time_window` 0행.
- `affinity_mask_ok`가 거짓인 행: 0(rev7 R7-6). C-2 L2b 2행은 `placement` 마스크가 기록되지 않았다(None, L2b 행이라 원판 6절의 SCM 요건 밖).
- 하네스 줄의 정체성 표는 하네스 R4 판정 뒤.

## 3. 결과를 본 뒤 개정의 역사 (Chrono)

| 차례 | 커밋·판 | 무엇 | 본 것과 결정 |
|---|---|---|---|
| R3c | 판정 도구 `f9bc3c7` | 경로 1 C-1~C-3 등급, C-5는 t45 입력 거부(종료 2)로 멈춤 | 결정 74~77 |
| rev22 | 봉인 2026-11-15 18:24:06, S10 `570a9c1` | t45 행 짝짓기, 도구 보완 커밋 R3d | R22-0(부록 D) |
| rev23 | 봉인 20:27:59, S11 `f40935a` | 러너 행·`s8_metrics`를 판정 행 `dir` 안쪽 이름으로 찾기 | 결정 80·81, R23-0 |
| R3d | `0220671` (21:16:01) | 두 경로 재판정 21:24~21:26. C-5 S-13(경로 1 판정 불가 / 경로 2 통과) | K-R `r3d_kr_cross_path.md`, 결정 86·88·89 |
| rev24 | 봉인 22:51:49, S12 `b75d874` | 공통 판정 정의 CD-1~CD-11, L-5 틀 문장 교체 | 결정 86·88~92, R24-0 |
| R3e | `4b81591`(통합 `z4373-r3e`, 푸시 안 함) | 판정 전 감사가 공통 블록 문장 모호·구현 결함을 찾음 → **폐기**(판정 실행 안 함) | 결정 95·98 |
| rev25 | 봉인 2026-11-16 01:09:01, S13 `f381053` | 공통 블록 교체(P3-6 판정과 한계, C1 사건 시각 절단, CD-11 대응 규약, C-8 기록 값) | 결정 95·98~101, R25-0 |
| R3f | 판정 전 감사 대상 `1fadc06` → 실행 전 수정 2로 `c3f4cad` 추가 → **`8a0c843`** | 두 경로 판정 02:02:59~02:07:11. 판정 후 감사(Q1·Q2), K-R(차단 1) | 결정 102·107·108 |

- rev15~rev25의 "결과 본 뒤 개정" 본 자료 목록과 공개 절은 부록 D에 원문 그대로 실었다(R15-0, R16-0, R17-0, R18-0, R19-0·R19-10, R20-0·R20-3, R21-0·R21-6, R22-0·R22-5, R23-0·R23-5, R24-0·R24-5, R25-0·R25-5). 이 판정서의 정의 가운데 R15-3~R25-3은 "결과 본 뒤 정한 정의(읽기)"다.
- R3c·R3d·R3e 출력과 감사는 판정 등급·사전 예측 대조·한계 문장의 근거로 쓰지 않는다(rev14 R14-2·rev16 R16-0·rev18 R18-4의 "S-13 경과" 처리와 같은 꼴). R3d 출력은 R3f 대조 기준(허용 차이 키 대조, CD-8 R3d $m$ 대조)으로만 쓴다.


### 3.1 대체된 앞 단계의 기록 의무 (사용자 결정 110 (2))

- R3·R3b·R3c·R3d 판정 도구 단계의 출력과 기록 의무(R3·R3b·R3c blob 표 rev15:67·rev18:34·56·rev21:63·71, R3 출력 기록 rev18:87, R3d 덩어리 표 rev22:58·rev23:90·91, V0 L2b t_b 대응값 rev21:29, R3b·R3c·R3d 실행 스크립트·비교기 diff 등)는 **R3f로 대체되어 판정 근거가 아니다.** 사용자 결정 110 (2)에 따라 그 사실을 공개하고 목록과 출력 위치(sha)만 싣는다.

| 단계 | 판정 도구 커밋 | 출력 폴더(`06_analysis/02_control/verif_matrix/v5_resume_4368/`) | 출력 sha 목록 파일 sha256(줄 수) |
|---|---|---|---|
| R3 | `576eb87`(브랜치 `z4373-r3v2`의 병합 커밋; `z4373-r3`은 `99ad4dc`) | `judge_576eb87\chrono_path1\` / `chrono_path2\` / `chrono_path2c\`. **단, `chrono_path1\chrono_view\`는 대체된 출력이지만 R3f 경로 1 view 단계의 입력이다(2.3절, `make_view.py` `adb01782…`·view map `1b2c500f…`, 41항목·82파일 대조, 폴더 실제 파일 43개)** | 경로 1 `SHA256SUMS.txt` `6590e656e12a5b63072aa414dac12931b443858958dd541c1630ad0c2d014d30`(43) / 경로 2 `outputs.sha256` `29fc641b969caeb790c4b2932962a3c706fc3d24d9305400694b6b669233dbad`(16) / `chrono_path2c` 목록 파일 없음(11파일) |
| R3b | `062e051` | `judge_062e051\chrono_path1\` / `chrono_path2\` | `SHA256SUMS.txt` `ea096bb89a936c043f89e52802732f124a9ffea560b5e963addff6baab4b3105`(53) / `outputs.sha256` `a95250bd48018242017a4284df9ac50f66bd7680f3c07ad21a310ba9d7713a03`(8) |
| R3c | `f9bc3c7` | `judge_f9bc3c7\chrono_path1\` / `chrono_path2\` | `SHA256SUMS.txt` `12f1f5b4e437f7f552410fc52089cd287df323d437c3adbbdb11a5b18cb8d10c`(120) / `outputs.sha256` `bd49fb6b7a95cfa9b9322e9578d678c7fa3637454c624317668469a0b6b6409f`(36) |
| R3d | `0220671` | `judge_0220671\chrono_path1\` / `chrono_path2\` | `SHA256SUMS.txt` `3a1b8a7a69540927bb5be00ec014b9a860bcbe1c19fd97c22af85b1606f41346`(57) / `outputs.sha256` `096346c740c171bc10660dd8745587f99794ca39f4d036a15b996fa7775860bb`(57), R3d 경로 2 로그 `ecf4b0f6…` |
| (참고) R2 첫 판정 | `b9f5707` | `judge_b9f5707\chrono_path1\`(56파일) / `chrono_path2\`(14) / `chrono_path2c\`(10) | 목록 파일 없음 |

- R3c 경로 1 러너 판정 출력(`judge_f9bc3c7\chrono_path1\runner_judge\`)과 두 경로 t45 재생 출력은 R3f에서 sha 대조 뒤 재사용한 입력이다(2.3절).
- R3d 덩어리 분류 문장(사용자 결정 84, "판정서에 실음"): 경로 2 `4a80c5a..3d0c05f`의 README `@@ -4,2 +4 @@`은 해시 줄 + 결정 83에 따른 rev22 메모 줄 되돌림으로 `f9bc3c7` 기준 순변화 0줄이며 S-11이 아니다. 결정 83: 경로 1 R3d 실행 스크립트에서 옛 R3 compare 단계를 지운 것은 허용 변경 3으로 인정했다.

## 4. 묶음별 판정과 기록

### 4.1 C-1 (D-1 고정 강체, 10행) — **통과**

| 행 | ID | 엔진 | 역할 | 경로 1 | 경로 2 | t_lift 차 [s] (경로 1 / 경로 2) |
|---|---|---|---|---|---|---|
| `D1C2_middle_fdown3.2_Fs4` | C2-01 | L2b VB | 판정 | 통과 | 통과 | 0.1 / 0.1 |
| `D1C2_middle_fup3.2_Fs4` | C2-02 | L2b | 판정 | 통과 | 통과 | 0.1 / 0.1 |
| `D1C2_middle_rpBop_Fs4` | C2-04 | L2b | 판정 | 통과 | 통과 | 0.0 / 0.0 |
| `D1C2_bottom_fdown3.2_Fs4` | C2-05 | L2b | 판정 | 통과 | 통과 | 0.0 / 0.0 |
| `D1C2_bottom_fup3.2_Fs4` | C2-06 | L2b | 판정 | 통과 | 통과 | 0.1 / 0.1 |
| `D1C2_bottom_rpBop_Fs4` | C2-08 | L2b | 판정 | 통과 | 통과 | 0.0 / 0.0 |
| `D1C1_top_flat_crx3` | C1-09 | L1-R V0 Kc×3 | 기록 | 기록(러너 항목 통과) | 기록 완료 | – |
| `D1C1_top_rpBop_crx3` | C1-10 | L1-R | 기록 | 기록 | 기록 완료 | – |
| `D1C1_bottom_flat_crx3` | C1-11 | L1-R | 기록 | 기록 | 기록 완료 | – |
| `D1C1_bottom_rpBop_crx3` | C1-12 | L1-R | 기록 | 기록 | 기록 완료 | – |

- 행 수 10/10(S-15 아님), `commit_identity_R11_4` 10행 `match`, CD-7 빈 사유 0, 경로 1 `stops` 0.
- t_lift 차 확인(rev19 R19-5, CD-2 표 마지막 앞 줄): 최대 0.0999999999998 s ≤ 0.1 s + 10⁻⁹ s, 멈춤 0. 차가 0.1 s인 행은 1 ms 기준 t_lift를 다음 10 Hz 제어 주기 표본으로 올린 값과 러너 이륙 시각이 한 주기 다른 경우다(두 경로 같은 값).
- 러너 미판정(rev19 R19-4, 경로 1): 4행(L1-R 4행, 항목 `K8 shadow (B) - true floor` 4건). L1-R 행은 기록 행이라 등급 셈 밖이다.
- R23-1 대응 기록: `rows` 10 = L2b·L1-R 행 수, `name_differs` 빈 목록.
- J-P3: ③ 켬 L2b 6행 pass, L1-R V0 4행 해당 없음(③ 끔). 위반 0.
- **C1-09~C1-12 D8 t_lift: "10 Hz 구간 대체"**(rev6 R6-B1): L1-R 4행은 1 ms 크롤러 법선이 없어 t_lift를 10 Hz 구간 대체로 얻었다(경로 2 `D8_F_after_liftoff.t_lift_basis` = `bracket_10Hz` 4행; L2b 6행은 `1ms_sus`).
- N1(정의 차이, 등급 영향 없음): fdown 2행 D8 최소 — CD-2 C1 줄 재계산값 51,365 / 51,792 N(REANCHOR 밖)은 두 경로 같고, 경로 2 자체 기록 항목 `D8_F_after_liftoff`(REANCHOR 포함) 29,739 / 30,114 N은 기록이다.

### 4.2 C-2 (D-1 선별 행 + PS-c, 6행) — **미달**

| 행 | ID | 엔진 | 경로 1 | 경로 2 | 근거 |
|---|---|---|---|---|---|
| `D1S_J1_B_middle_Fs4_r0_pm2p8` | S-01 | SCM | 안전 종료(`allowed_stop`) | 통과(`allowed_stop`, 결정 65) | 427.9-1~5 모두 참 |
| `D1S_J1_B_bottom_Fs4_r0_pm2p8` | S-02 | SCM | 안전 종료 | 통과(`allowed_stop`) | 같음 |
| `D1C2_middle_rollm4.4_Fs4` | C2-03 | L2b | 통과 | 통과 | t_lift 차 0.0 / 0.0 s |
| `D1C2_bottom_rollm4.4_Fs4` | C2-07 | L2b | 통과 | 통과 | t_lift 차 0.1 / 0.1 s |
| `D1PSC_J1_B_top_Fs4_spFLJ1_base` | PSC-base-FL | SCM | 기록 행 | 기록 완료 | 기록 행(CD-11 예외) |
| `D1PSC_J1_B_top_Fs4_FL_cslow` | PSC-c-slow-FL | SCM | **미달(E-5)** | **미달(E-5)** | 아래 |

- 묶음 문구: 통과 2 / 안전 종료 2 / 미달 1(경로 1 `row_phrase`; 경로 2는 S 행을 통과 쪽으로 세어 "통과 2 / 안전 종료 2"를 공개 문구로 적음). 등급 `미달`.
- **S-01·S-02의 남은 두 값(rev18 R18-4, 행마다)**: 다리 부상 표본(레벨 시작부터) [0, 0, 0, 0] / [0, 0, 0, 0], 이동 중 압력 최대 89.409 / 89.221 bar(≤ 180 bar), 포화 행 [0, 0, 0, 0](경로 2 `safe_stop_427_9`). 경로 1은 같은 조건을 참거짓으로 냈다(`5_moving_pressure` 참, `3_no_lift_after_level` 참). 두 행 모두 READY가 없어 P3-1·P3-4·P3-5는 CD-5 해당 없음(경로 2 `indeterminate` 표기), P3-6·FAULT0은 427.9 분기 행이라 기록이다.
- **PS-c c-slow E 항목**(명세 426.3): E-1 pass(사건 뒤 부상 표본 0), E-2 해당 없음(빠른 사건 전용), E-3 pass(사건 뒤 네 다리 1 ms 최소 114,848 / 112,266 / 67,732 / 67,131 N), E-4 pass(창 안 최대 89.73 bar, 창 밖 이동 최대 91.18 bar), **E-5 fail**, E-6 pass(창 안팎 재접촉 0, 끝 크롤러 하중 0, 끝 틈 61.9 mm), E-7 pass(+20 J 초과 비틀림 일 묶음 0). E-5 내용(경로 2 재계산): 분기 끝 마지막 `c2_phase` = `probe`(READY 아님), 끝 1 s 평균 |roll|·|pitch| = 0.0316° / 0.0064°(≤ 0.2°), 분기 안 FAULT 주기 0, 실행 최대 행정 512.63 mm(≤ 684.8 mm), 분기 끝 사유 `max_after`. 즉 E-5 실패 원인은 분기 끝이 READY가 아닌 것이다.
- N3(수치 차이, 등급 영향 없음): E-5 최대 행정 경로 1 517.33 mm(러너 `soil_event.judgement` 재집계) / 경로 2 512.63 mm(재계산). 둘 다 ≤ 684.8 mm. 어느 행정 좌표인지는 R3d부터 python-expert 원인 확인이 남아 있다(`확인 필요`).
- PS-c `stroke_le_684.8mm`: R3f에서 경로 1이 CD-11 목록상 E-5의 기록으로 옮겼다(`c3f4cad`, 2.1절). 값 517.33 mm, pass.
- **436.9 입력(사용자 결정 88, rev24 R24-5)**: "C-2 PS-c c-slow 행의 E-5 실패는 탐침 소성 침하로 재레벨이 두 번 일어난 것이고 제어기 오동작이 아니다." C-2 E-5의 등급(`미달`)은 바뀌지 않는다. 진단 근거: control-expert 진단 보고 `scratchpad\diag-4368\diag_report_control_expert.md`(sha256 `8c40dc0ea8e8cd9a383eb59ef13d6d7394c9d5ac4e8d5d0a71c490ee568c3930`) 진단 2(스크립트 `psc_phases.py`·`psc_probe.py`·`psc_probe_legs.py`·`harness_cslow.py`). 요지: E-5는 사건 + 60 s(143.2 s)의 끝 상태가 READY인지를 보는데 그 시각 상태가 `probe`였다. 95.8 s에 편차가 재레벨 문턱 0.07°를 넘어 LEVEL(121.8 s DONE), 1차 탐침(121.9~132.2 s)이 균일 J1에 소성 침하(FR +2.8, RL +1.7, RR +5.6 mm)를 남겨 편차가 0.027°→0.0701°로 올라 132.3 s에 LEVEL로 복귀, 141.6 s DONE → 2차 탐침 141.7~153.6 s → READY 153.6 s(사건 + 70.4 s). 제어기 오동작이 아니라 연약 지면 탐침의 소성 침하가 재레벨을 한 번 더 부르는 알려진 계열(U-S9P-16)이 60 s 상한과 만난 것이다(확신도 높음). 하네스는 이 재레벨을 재현하지 않는다(하네스 c-slow 22줄 READY 복귀 32.0~56.0 s).
- t_lift 차 최대 0.0999999999998 s, 러너 미판정 0, R23-1 `rows` 2 = L2b 행 수, `name_differs` 빈 목록, `commit_identity_R11_4` 6행 `match`.

### 4.3 C-3 (D-1 고정 토양 S-03·S-04) — **통과**

| 행 | ID | 경로 1 | 경로 2 |
|---|---|---|---|
| `D1S_G1_B_middle_Fs4_spJ1FL` | S-03 | 통과 | 통과 |
| `D1S_G1_B_bottom_Fs4_spJ1FL` | S-04 | 통과 | 통과 |

- 등급 항목(행마다 10개, 두 경로 일치, 판정 다름 0): G6 대응표 여덟 ID와 `P3-7`, `J-P3`. 427.9 분기 행 없음(`safe_stop_427_9.rows` 빈 목록). READY 없는 C-3 행 없음(rev25 R25-5 G6 공개 문장의 "지금 R3d 자료에는 READY가 없는 C-3 행이 없다"는 R3f에서도 같다).
- **G6 갈음 대응(rev25 CD-8 9, CD-11 G6 대응표; 공통 ID로 다시 적음)**: G6-1 → `P3-1`, G6-2 → `P3-2`, G6-3 → `P3-3`, G6-4 → `P3-4`, G6-5 → `P3-5`, G6-6 → `G6-6`, G6-7 → `P3-8`, 따로 `READY_le_120s`. 경로 1은 공통 ID(`P3-*` + `G6-6` + `READY_le_120s`, 조항 `CD-11 G6 대응표`)로, 경로 2는 `G6` 블록에 원 관문 이름(`G6-1`~`G6-7`)과 같은 공통 ID로 적었고 값이 같다.
- C-3의 `P3-6`·`P3-9`·`FAULT0`은 기록(CD-4 P3-6 역할, CD-11). 경로 1 묶음 출력에서 C-3 P3-6 기록 항목이 421.1 한계 필드(`limit_s`, `runner_limit_s`, `limit_matches_runner` 등)를 새로 얻은 것은 허용 목록 밖 범주 안 차이로 결정 107 (1)로 허용했다(7.6절).
- P-7(C-3 저장 행과 명령 비트 같음, 기록)은 이 판정서에서 확인하지 못했다(`확인 필요`, 6절). (갱신 2026-11-16: 하네스 판정서 6절 — 판정서 작성자가 원 기록에서 계산, 두 행 비트 같음, 맞음(기록))

### 4.4 C-4 (LAS Chrono 확인, 기록 4행) — **기록 완료**

| 행 | Kc | LAS | $R_c$ | 이탈 $t_D$ [s] | 다리별 $F^{\mathrm{a}}_{min}$ [kN] FL / FR / RL / RR | 최소(다리, 시각) | P3-3 | 기록 상태 |
|---|---|---|---|---|---|---|---|---|
| `R4368C4_rigidJ1FR_B_top_Fs4_r2p3351_p1p5017_Kc1_VB_lason` | ×1 | 켬 | 1.0764 | 35.229 | 122.32 / 88.09 / **10.81** / 72.59 | RL 10,813.8 N @35.939 s | pass | 기록 완료 |
| `…_Kc1_VB_lasoff` | ×1 | 끔 | 1.0764 | 35.094 | 122.24 / 87.70 / **7.65** / 72.49 | RL 7,653.2 N @35.279 s | fail | 기록 완료 |
| `…_Kc3_VB_lason` | ×3 | 켬 | 1.0354 | 34.868 | 122.17 / 85.85 / **8.64** / 72.73 | RL 8,637.1 N @35.581 s | fail | 기록 완료 |
| `…_Kc3_VB_lasoff` | ×3 | 끔 | 1.0354 | 34.598 | 122.03 / 84.43 / **4.20** / 72.42 | RL 4,199.4 N @34.760 s | fail | 기록 완료 |

- 네 행 모두 실행 $R_c$ > 1(운용 시작 조건 밖)이다. 원판 7.4에 따라 $F_{min}$ 하회(`P3-3_within` 거짓, 3행)는 L-5 알려진 한계이고 묶음을 멈추지 않으며 등급에 넣지 않는다.
- **C-4 켬 팔의 같은 하회(원판 14절 끝 글머리)**: Kc3 켬 팔 RL 8,637.1 N($F_{min}$ − 777.5 N)을 L-5 근거로 함께 적는다. Kc1 켬 팔 RL 10,813.8 N은 $F_{min}$ 위다. C-4 행의 $F < F_{min}$ 시간은 C-4 기록 값(CD-9)에 없어 이 판정서에 적지 못했다(`확인 필요`).
- P3 값(두 경로 같음): P3-1·P3-2·P3-4·P3-6~P3-9·FAULT0 pass, P3-5 `해당 없음(rigid_base)`(사용자 결정 88·100), P3-3은 위 표.
- **436.9 입력(사용자 결정 88)**: "C-4 P3-5 표본 0은 강체 바닥(rigid_base)이라 구조적으로 해당 없음이다." 진단: 같은 보고 진단 3(스크립트 `c4_rut.py`). 요지: 틈 기준점은 정착 때 SCM 침하가 0보다 큰 크롤러 블록 바닥점이고(`scm_model.py` 1510~1544행), rigid_base 행은 `rut_reference.n_points` = 0이라 `rut_clearance_m`이 1,600행 모두 None이다. P3-5의 행정 부분은 통과(최대 658.4 mm). 같은 구조: O-C5 C-8a·C-8b, P5r4 A1~A6.
- C-4 기록 값에는 D8·G6을 넣지 않는다(사용자 결정 99, 10절 공개 문장). C-4 CD-11 목록은 경로 2에만 있다(경로 1 `bundle_C4.json`에 `item_list_CD_11` 없음; 결정 108 (2) 공개만, rev26 후보).
- K1 분류: 켬 팔 2행 "LAS-b 작동"(LAS 시작 34.8 s / 34.2 s, `decisions` 0), 끔 팔 2행 "LAS 없음"(5절).

### 4.5 C-5 (3단계 Chrono, 35행: L2b 24 + SCM 11) — **미달(28 통과 / 7 미달)**

**미달 7행(두 경로 같은 행·같은 실패 항목)**

| 행 | 설정 | P3-7 | P3-6 | P3-2 | P3-1 |
|---|---|---|---|---|---|
| `P3b_J2_B_top_Fs4_m1p1_t180` | VB | fail | fail | FLAG | – |
| `P3b_J2_B_top_Fs4_m1p1_t180_v0v` | V0v | fail | fail | FLAG | – |
| `…_t180_seed20261026` | S6SEED | fail | – | FLAG | – |
| `…_t180_seed20261026_flow` | S6SEED | fail | – | FLAG | FLAG |
| `…_t180_seed20261027` | S6SEED | fail | fail | FLAG | FLAG |
| `…_t180_seed20261028` | S6SEED | fail | – | FLAG | FLAG |
| `…_t180_seed20261029` | S6SEED | fail | fail | – | – |

- 표의 FLAG는 두 경로 출력의 판정 `flag`다(등급 셈에서 실패가 아님). K-R 감사 1절 표는 P3-1·P3-2를 "실패 항목" 칸에 함께 적고 P3-2만 FLAG로 주석했다. 두 경로 출력은 P3-1도 `flag`이므로 이 판정서는 출력대로 적는다(`확인 필요`: 감사 표 문구와의 차이).
- 미달 7행은 모두 균일 J2 토양 t180 계열이다. P3-6 한계는 rev25 CD-4(명세 421.1 표)로 정했고, 두 경로 모두 원 판정기 P3b `limit_s`와 같다(경로 1 81행 점검 불일치 0, 7.1절).
- **통과 28행**: L2b 24행 전부, SCM `P3b_J1_B_top_Fs4`·`P3b_J1_B_top_Fs4_v0v`, 그리고 S9SL 2행(결정 107 (3)으로 427.9 안전 종료 → 통과 쪽).
- **S9SL 2행(`S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0`, `…_v0v`)**: 경로 2는 첫 `FAULT*`가 토양 가드라 427.9 안전 종료 분기 행으로 보았다(427.9-1~5 모두 pass, `allowed_stop`; P3 항목은 기록). 경로 1은 427.9 분기를 S-01~S-04에만 적용해 P3 항목(P3-1·P3-6·FAULT0 fail)으로 `미달`을 냈다. **사용자 결정 107 (3)으로 경로 2 읽기를 채택한다**(근거: rev19 R19-1 분류 글머리 "정지 사유가 토양 가드인 행", rev25 CD-4 "427.9 안전 종료 분기 행은 그 분기 규칙대로"). 경로 1의 `미달` 판정은 정의 차이로 공개한다(7.5절 107-(3) 줄).
- **경로 2 C-5 CD-7 멈춤(사용자 결정 107 (2) 공개)**: 경로 2 C-5 묶음 출력은 11행의 `H-9` 항목(판정 `na`, `m2_on` 거짓, 사유 빈칸)이 CD-7 빈 사유라 `판정 불가`(stops 1)로 멈췄다. 대상 11행: SCM 8(`P3b_J2_…_t180_seed20261026`·`…27`·`…28`·`…29`·`…26_flow`·`…_t180_v0v`, `P3b_J1_B_top_Fs4_v0v`, `S9SL_…_p0_v0v`), L2b V0 3(`E_G4_Fs4_V0`, `E_G4_Fs4_ph0.05_V0`, `G1R_FS24_FL_top_o050_Fs0_V0`). 도구는 고치지 않고, 이 판정서에 사유를 적는다: **"H-9: M2 끔이라 해당 없음, CD-1 목록 밖 기록 항목"**(`v5_hydraulics.hydraulic_options.m2_law` 거짓). 그 위에서 경로 2 C-5 묶음 등급은 행 등급대로 **28 통과 / 7 미달 → 미달**이다(판정 후 감사의 재계산과 같음). 이 처리는 판정 뒤 정한 처리이므로 10절 한계에 공개한다. 경로 1 C-5 묶음 출력에는 H-9(M2) 항목이 없다.
- **VB↔V0 여섯 쌍(v5 기준 개정 12 2.1·2.2)**: 경로 1 `vb_v0_pairs_S15` 확인. `P3b_J2_…_t180`(VB 미달)↔`_v0v`(미달): VB 고유 실패 없음. S9SL 짝은 결정 107 (3) 뒤 둘 다 안전 종료. 나머지 짝(E_G4_Fs4, E_G4_Fs4_ph0.05, G1R_FS24, P3b_J1)은 둘 다 통과. "VB 고유 실패"는 없다(K-R 1절).
- **T4·T5(CD-6)**: 대상 18행 모두 pass(경로 1 `t4_t5_phrase` "일치 (등급 부분: ML 216 없음, Chrono 18행)"), 비대상 17행은 해당 없음(대상 행 아님). T4-0 관문 18행 pass(두 경로). R22-1 짝짓기: `t45_pairing_R22_1` 18쌍, 검사 1~4 모두 참, 목록 sha256 `05ca47a4699346839c2e9d159c1f3076c70b9f38a9b975961bb7cd7bdcfd34be`, R3c 실행 스크립트 `$T45Cases`(`run_path1_r3c.ps1` `8d65d4b1cee8340bc08a5e3858c066339aabbc43b5f3ffbe205650e6b9af84bc`)와 18개 목록 같음(`equal` 참, 대소문자 무시 목록도 같음), R3c `judge_C5.json`(`c1ba9382…d76a`) 목록 = R3f 목록.
- **R23-1 대응 기록**: `rows` 24 = L2b 행 수, `name_differs` 9행 = R23-1 예상 영향 9행(`E_G4_Fs4_V0`, `E_G4_Fs4_ph0.05_V0`, `G1R_FS24_FL_top_o050_Fs0_V0`, `E_G4_Fs8_LS1`, `E_G4_Fs8_LS4`, `E_RE1bF_Fs8_LS1`, `E_RE1bF_Fs8_LS4`, `K0V_top_fup3.5_Fs0_LS1`, `K0V_top_fup3.5_Fs0_LS4`), `ok` 참. C-1 `rows` 10, C-2 2, C-3 0, `name_differs` 빈 목록.
- 러너 미판정(경로 1, rev19 R19-4): 6행(`E_RE1bF_Fs0`, `E_RE1bF_Fs8`, `E_RE1bF_Fs8_LS1`, `E_RE1bF_Fs8_LS4`, `K8_top_fdown3.5_Fs8`, `K8_top_rpB_Fs8`), 항목 `3 lift-off RR time / ratio (report)` 4건, `I3 J_C: M4 max <= sensor share` 2건. 목록에 없는 `kind` 0.
- J-P3: ③ 켬 24행 pass, ③ 끔 11행 해당 없음. 위반 0(사용자 결정 102 해당 없음).
- J11: 35행 모두 실제 대체 다리 $n_{late}$ > 0 없음(두 경로). 표기 차이 35건(경로 1 `pass` / 경로 2 `record`)은 결정 108 (2)로 공개만 한다.
- K1 분류: C-5 35행 모두 "미작동"(LAS-b 시작 없음, `decisions` 막힘 0). 균일 연약 지면 계열 K1 막힘 0(S-6 해당 없음).
- 사건 행(CD-3, 결정 92의 1): 바닥 사건 `E_RE1bF_Fs0`·`E_RE1bF_Fs8`·`E_RE1bF_Fs8_LS1`·`E_RE1bF_Fs8_LS4`, 빠른 침하 `G1R_FS24_FL_top_o050_Fs0`·`…_V0`, 6행. `E_G4_` 7행은 비사건 규칙. 창 끝 표는 7.3절.

### 4.6 C-6·C-7 (G1 열린 루프 3행, 기록) — **기록 완료**

| 행 | 묶음 | 이륙(폐루프 시작 뒤) [s] | 속도비(유량 제한) | 이륙 전 최소 $F_a$ FL / FR / RL / RR [kN] | 끝 Δroll / Δpitch [°] | 끝 행정 FL~RR [mm] | 유량 제한 | P3a-1~5 | 명세 11047 FLAG |
|---|---|---|---|---|---|---|---|---|---|
| `P3a_G1_B_VB_prop` | C-6 | 18.921 | 0.89474(네 다리, 0.93 아래 27.0 s) | 13.21 / 13.30 / 13.23 / 13.36 | −0.0076 / −0.0290 | 517.52~518.48 | 27.77 s(네 다리 동시) | 모두 참 | 없음 |
| `P3a_G1_B_VB_FB` | C-7a | 19.332 | 1.0(제한 없음) | 13.20 / 13.29 / 13.28 / 13.23 | −0.0082 / −0.0281 | 578.14~579.18 | 0 s | 모두 참 | 없음 |
| `P3a_G1_B_V0_FB` | C-7b | 19.276 | – (V0) | 13.25 / 13.21 / 13.36 / 13.31 | −0.0083 / −0.0280 | 579.16~580.21 | – | 모두 참 | 없음 |

- 값은 경로 2 `p2h_openloop.json`(`openloop_compare.py` `analyse`, 스크립트 sha256 `a91a8fe1905d0dee383437ff4f65253a501289a9fb1b75e40687f5cbc70328c0`)에서 옮겼고, 경로 1 `bundle_C6C7.json` P3a 판정(`P3a-1_within`~`P3a-5_within` 참, `abort` 거짓, 11047 FLAG 거짓, 따로 적을 것 없음)과 맞다. K-R 감사: C-6·C-7 행 값 18개 일치.
- 묶음 칸의 C-6·C-7a·C-7b는 **행 생성기가 쓴 `criteria_id` 값**이다(rev4:82; 경로 2 `p2_C6C7.json`·경로 1 `bundle_C6C7.json` `criteria_id` = `C-6`·`C-7a`·`C-7b`).
- C-7a 유량: $Q_{sum}$ 최대 = 51.17 L/min × (1 − 0.0200) = 50.15 L/min(`max_sum_Q_over_supply_minus_1` = −0.020002에서 계산).
- P3a-1(힘 한계) 실패·실행 오류: 없음(원판 7.5).
- C-7b(V0) 행에 `v5_hydraulics` 블록이 없는 것은 정상이다(V0라 해당 없음, 사용자 결정 41 공개).
- D12(공개, rev24 R24-5): C-6·C-7 P3a를 두 경로가 같은 저장값에서 읽었다(독립 아님).

### 4.7 C-8 O-C5 (기록 2행) — **기록 완료**

**5.4 바닥 각 결정 절차 기록(원판 13절 8항)**

| 행 | 첫 축척 $k_1$ | probe 수 | probe `PROBE_DURATION` | probe $R_c$ | 정한 $k$ | 바닥 (roll, pitch) | 본 행 $R_c$ | probe ↔ 본 행 |
|---|---|---|---|---|---|---|---|---|
| C-8a `OC5_mixed_rigid_J1FR_Kc3_VB_top` | 0.9179 (= 0.95 / 1.035) | 1(`OC5P_Kc3_VB_n1_k0p9179`) | 7 s | 0.9523695802182304 | 0.9179 | 2.1434°, 1.3784° | 0.9523695802182304 | 비트 같음 |
| C-8b `OC5_mixed_rigid_J1FR_Kc1_V0_top` | 0.8829 (= 0.95 / 1.076) | 1(`OC5P_Kc1_V0_n1_k0p8829`) | 7 s | 0.9568086623414596 | 0.8829 | 2.0617°, 1.3259° | 0.9568086623414596 | 비트 같음 |

- 두 행 모두 첫 probe에서 $|R_c(k_1) - 0.95| \le 0.02$라 $k = k_1$이다. 두 배 재실행 없음, 절차 멈춤(S-10) 없음. probe는 `batch_V5-RESUME-K1-OC5PROBE_20261113_215123`, CHECK 끝 8.1 s(probe `phases`). 출처: `oc5_state.json`, 경로 2 `p2h_oc5k_C-8a.json`·`…C-8b.json`(`n_probes_counted` 1, `R_c_recorded` = `R_c_path2`). 목표 0.95, 허용 0.02, 최대 3건은 절차 값(가정)이다.

**7.4 기록 항목(CD-8 1~9, 두 경로 같음)**

| 항목 | C-8a (×3·VB) | C-8b (×1·V0) |
|---|---|---|
| $t_D$ [s] | 34.546 | 33.991 |
| $F^{\mathrm{a}}_{min}$ FL / FR / RL / RR [N] | 122,313.1 / 82,974.1 / **5,869.6** / 72,774.8 | 121,958.6 / 88,312.95 / **11,951.2** / 74,601.3 |
| 그 시각 [s] | 76.255 / 35.553 / **35.286** / 71.816 | 76.140 / 34.638 / **34.504** / 76.565 |
| $F^{\mathrm{t}}_{min}$ FL / FR / RL / RR [N] | 136,324.7 / 82,974.1 / 5,869.6 / 95,240.4 | 136,889.5 / 88,312.95 / 11,951.2 / 95,195.2 |
| 그 시각 [s] | 42.541 / 35.553 / 35.286 / 42.545 | 41.990 / 34.638 / 34.504 / 41.990 |
| $m$, 최소 다리, $m - F_{min}$ | **5,869.617 N, RL, −3,544.97 N** | **11,951.206 N, RL, +2,536.62 N** |
| $F<F_{min}$ 시간 (RL) | **0.158 s** | 0 |
| $F<F_{min}+2$ kN 시간 (RL) | **0.212 s** | 0 |
| `P3-3_within` | 거짓 | 참 |
| LAS-b 시작 / 끝 [s], 끝 사유 | 34.4 / 34.9, `sum` | 33.3 / 34.2, `sum` |
| K1 `decisions` | 빈 목록 | 빈 목록 |
| 실행 $R_c$, 크롤러 자세 (roll, pitch) | 0.95237, (2.1519°, 1.4826°) | 0.95681, (2.0856°, 1.5450°) |
| 바닥 각, 크롤러 강성 배수 | (2.1434°, 1.3784°), 3.0 | (2.0617°, 1.3259°), 1.0 |
| P3-1~P3-9 | P3-3 fail, P3-5 `해당 없음(rigid_base)`, 나머지 pass | P3-5 `해당 없음(rigid_base)`, 나머지 pass |
| D8 ① t_lift | 34.547 s | 33.992 s |
| D8 ② 이탈 뒤 최소 | 5,869.6 N, RL, 35.286 s | 11,951.2 N, RL, 34.504 s |
| D8 ③ 끝 자세 + 장착 | 0.03976° | 0.03814° |
| D8 ④ 패드 부상 표본 | 0 ([0, 0, 0, 0]) | 0 ([0, 0, 0, 0]) |
| G6 값 | G6-6 pass, `READY_le_120s` pass, G6-1~G6-5·G6-7은 P3 값으로 갈음 | 같음 |

- **원판 7.4 처리**: C-8a는 $m < F_{min}$ → S-9. 사용자 결정 60 (A)·88로 처리했다(멈춤 목록 밖, L-5 알려진 한계, 운용 범위 안 제어기 한계). CD-8 조건 "$m$과 최소 다리가 그 경로의 R3d 출력과 K-10으로 같을 때만": 경로 2 `CD-8_S9.r3d_equal` 참(R3d $m$ 5,869.61684783503 N, RL), 경로 1 비교기에서 `m_N`·`min_leg`가 허용 키 밖이고 차이 없음. C-8b는 $F_{min} \le m$, $m \ge F_{min} + 2000$ N → 기록.
- **C-8a 진단(R3d 뒤, 판정 불변)**: control-expert 진단 보고 `scratchpad\diag-4368\diag_report_control_expert.md`(sha256 `8c40dc0e…`) 진단 1. 요지: A3·A5와 같은 계열(LAS-b 끝 계단 + RL을 0에 고정한 명령 + FR 연약 패치 포화)에, LAS-b가 이탈 0.146 s 전에야 시작해 거의 최고 속도로 이탈한 것과 모멘트 진동 몫 증가가 더해졌다. 원시 시계열에서 다시 계산한 RL 최소 5,869.6 N과 $F_{min}$ 아래 158 ms가 두 경로 출력과 같았다(세 번째 독립 읽기). 기전의 정량 분해는 dynamics-expert 판정(`dyn-4368\L5_proposal_report.md`, 같은 폴더 `mode_*.json` 등)을 따른다(10.1절 L-5).
- "다리는 접지를 유지했다"(rev18 R18-5): C-8a 네 다리 $F^{\mathrm{a}}_{min}$이 모두 양수(최소 RL 5,869.6 N)이고 D8 ④ 패드 부상 표본 0, P3-1(재접촉 0 포함) pass다.
- **CD-8 8 크롤러 법선 계열(공개)**: D8 ① t_lift는 두 경로 모두 `step_series.npz` `scm_crawler_normal_N`(P3-3 이탈 판정 $t_D$와 같은 계열)으로 정했다. **이 계열이 강체 바닥(rigid_base) 쪽 크롤러 하중을 담는지는 두 경로 모두 확인하지 못했다(미확인).** D8 ① t_lift(34.547 / 33.992 s)는 $t_D$(34.546 / 33.991 s)보다 1 ms 뒤로, 같은 계열에서 정의만 다른 값이다.
- N5(정의 차이, 기록): 8 s 창 RR $F^{\mathrm{t}}_{min}$ — CD-8 값 [t_D, t_D + 8 s) = 95,240.43 N(두 경로 같음), 경로 2 옛 기록 `Fmin_time_8s`는 닫힌 구간 [t_D, t_D + 8]이라 95,239.19 N @ t_D + 8.
- 경로 1 `oc5_C-8a` 종료 1(`class` `stop_S9`)과 경로 2 `07_p2_4368_chrono` 종료 2(`stop_codes` S-9)는 이 S-9 기록이며 R3d와 같다.

## 5. K1 분류(7.2)와 J_P 재사용(7.3)

### 5.1 7.2 분류 표 (Chrono, 경로 1 `k1_classification_7_2_view.json`, 64 실행)

| 묶음 | 미작동 | LAS-b 작동 | K1 막힘 | 둘 다 | LAS 없음(C-4 끔 팔) | 판정 불가 |
|---|---|---|---|---|---|---|
| C-1 | 10 | 0 | 0 | 0 | – | 0 |
| C-2 | 6 | 0 | 0 | 0 | – | 0 |
| C-3 | 2 | 0 | 0 | 0 | – | 0 |
| C-4 | 0 | 2(켬 팔) | 0 | 0 | 2 | 0 |
| C-5 | 35 | 0 | 0 | 0 | – | 0 |
| C-6·C-7 | – | – | – | – | – | 3(열린 루프, R18-2a 해당 없음) |
| C-8 | 0 | 2 | 0 | 0 | – | 0 |
| O-C5 probe | 2 | 0 | 0 | 0 | – | 0 |
| 계 | 55 | 4 | 0 | 0 | 2 | 3 |

- 묶음별 칸은 view의 비미작동 9행 목록(C-4 4, C-6·C-7 3, C-8 2)과 총계(미작동 55)에서 셌다. 미작동 55 = C-1 10 + C-2 6 + C-3 2 + C-5 35 + probe 2.
- K1 막힘 계열 목록: **없음**(`decisions` 막힘 0, `applied` ∧ `would_block` 0, `_SKIPPED:order` 사건 0). 균일 연약 지면 계열 K1 막힘(S-6) 없음.
- 미작동 줄 해시 비교: Chrono에는 비트 예측 앵커가 없다(`anchors` 0, `hash_checked` 0). P-1·P-2 앵커는 하네스 H-1 몫이다(하네스 R4 판정 뒤).
- 경로 2의 7.2 분류(`K1_class` 관문)는 C-1~C-5 행에서 실패(`indeterminate`) 0이다(관문 결과, 7.5절).

### 5.2 7.3 J_P 재사용

- **J_P Chrono 12행(`V5-JP-{VB,V0}`): R4와 함께 판독, 이 판정서에는 미포함**(사용자 결정 110 (1)). 판독 도구는 `resume4368_judge.py jp-reuse`(12행)이고 그 출력은 아직 없다. 판독이 거짓이거나 판독 불가이면 묶음 `JP`를 `git_at_start` R2에서 재실행해 판정한다(원판 5.2·7.3, rev14 R14-3). 0.1절 표에 이 줄을 두었다.

## 6. 사전 예측 대조 (원판 10절)

| # | 대상 | 예측 | 결과 | 맞음/틀림 |
|---|---|---|---|---|
| P-1 | H-1 강체 412줄 | K1 막힘 0, 명령 해시 앵커 | 하네스 판정서 6절(앵커 408/408 같음) | 맞음 |
| P-2 | H-1 토양 456줄 | H-SH 앵커 해시 | 하네스 판정서 6절(456/456 같음) | 맞음 |
| P-3~P-6 | 하네스 | – | 하네스 판정서 6절(P-3·P-4 맞음, P-5·P-6 확인 못함) | – |
| P-7 | C-3 | 저장과 명령 비트 같음(기록) | 하네스 판정서 6절: 판정서 작성자가 원 기록에서 계산(사용자 결정 113·114의 9). 두 행 `controller_commands.npz` 비트 같음(배치는 R2 P코어, 저장 E코어). K1 분류는 미작동(예측 전제와 같음) | 맞음(기록) |
| P-8 | C-5 토양 균일 행 | K1 막힘 0 | 막힘 0 | 맞음 |
| P-9 | C-4 | 켬 팔 Kc1 약 10.81 kN, Kc3 약 8.64 kN(< $F_{min}$), $R_c$ 1.076 / 1.035, 켬 ≥ 끔 | 10.814 / 8.637 kN, $R_c$ 1.0764 / 1.0354, 켬 ≥ 끔(10.81 ≥ 7.65, 8.64 ≥ 4.20) | 맞음 |
| P-10 | C-6 | 속도비 0.8947 ± 0.001, 이륙 18.91 ± 0.15 s, 끝 \|Δpitch\| ≤ 0.1°, 다리 사이 행정 차 ≤ 2 mm, 후방 최소 $F_a$ 11.0~13.6 kN, FLAG 없음, P3a 통과 | 0.89474, 18.921 s, 0.029°, 0.96 mm, RL 13.23·RR 13.36 kN, FLAG 없음, 통과 | 맞음 |
| P-11 | C-7a | 유량 제한 0행, $Q_{sum}$ ≤ 50.2 L/min, 속도비 0.8769, 이륙 19.29 ± 0.15 s | 제한 0 s, 50.15 L/min, 이륙 19.332 s. 속도비 $r_v$는 하네스 판정서 6절(0.876909 / 0.876909 / 0.876906 / 0.876906, 결정 113·114의 9) | 맞음 |
| P-11b | C-7b | 속도비 0.8769, 이륙 19.29 ± 0.15 s(C-7a보다 0~0.1 s 이름), 후방 최소 C-7a ± 0.5 kN, 끝 자세 ± 0.02°, P3a 통과 | 이륙 19.276 s(C-7a보다 0.056 s 이름), 후방 RL +0.08·RR +0.09 kN, 끝 자세 차 ≤ 0.0002°, 통과. 속도비 $r_v$는 하네스 판정서 6절(C-7a와 차 < 10⁻⁹) | 맞음 |
| P-13 | C-8a | $R_c$ 0.93~0.97, RL 최소 > A3 8.64 kN, 최소 다리 RL | 0.9524, **5.87 kN**, RL | $R_c$·다리 맞음, **최소 크기 틀림** |
| P-13b | C-8b | $R_c$ 0.93~0.97, RL 최소 > A5 8.51 kN, 최소 다리 RL | 0.9568, 11.95 kN, RL | 맞음 |
| P-14 | C-8 probe ↔ 본 행 | $R_c$ 비트 같음 | 두 행 모두 비트 같음 | 맞음 |
| P-15 | 전체 | 새 FAULT·실행 오류 0, `errors 0`, `MIXED_HULL_MODE` 0 | 러너 단계 모두 `exit=0`, `MIXED_HULL_MODE` 0. C-5 S9SL 2행과 C-2 S-01·02는 토양 가드 FAULT(427.9 안전 종료)로 끝났다. 이 FAULT는 427.9 안전 종료 분기의 예정된 정지라 새 FAULT로 세지 않는다(이 작성자의 읽기). `log_errors.py`는 Chrono 러너 로그 16개에서 `errors N` 줄이 없어 빈 통과였고(판정 후 감사 기록 3), 실제 근거는 `.done exit=0` 11단계다(9절). `FAULT_STROKE_END` 행 0(10.2절 RV1-10 표) | 맞음(읽기 공개) |

- P-1·P-2(판정 전 확인 항목)는 하네스 몫이라 결과는 하네스 판정서 6절이다(두 항목 맞음).
- P-13 빗나감은 rev18 R18-5 L-5 문구와 같다(10절 L-5).

## 7. 두 경로 (원판 9절, 13절 7항)

### 7.1 경로별 작성자와 읽은 것

**경로 1** — 작성자: python-expert(경로 1 도구 `chrono_rows_judge_4368.py`·`chrono_bundle_grade_4368.py`, 브랜치 `z4377-p1chrono`). 실행 스크립트 실행: 메인 세션.

- 공통 블록 sha256 **`0e082b9c3b3ce3ff384a5cbf5d62da41bf766c423411d5eb3395217c79630b5d`**(rev25 넘김 문장에서 확인, 넘김 파일 `214e09e1…`만 읽음; 경로 1 R3f 보고 "읽은 것").
- R3f(rev25) 작업: `04_scripts/02_chrono/run_S9.py` 2379–2393, 3760–3809, 5676–5774행(P3b P3-3·P3-4·P3-6·P3-7). S9 실행 파일은 키와 참거짓만. R3d 출력은 이번에 쓰지 않음. 경로 2와 봉인 `.md`의 다른 절은 열지 않음.
- **81행 P3-6 한계 일치 점검(공개)**: S9 배치 SCM 81행에 다시 구현한 421.1 P3-6 한계를 돌려 러너 P3b `limit_s`와 대조했다. 출력은 참거짓뿐이고 불일치 0이다.
- R3e(rev24) 작업: 원 판정기 소스 `03_src/outrigger_sim/verify/s6_control.py` 139–189, 795–984, 1360–1420, 2010–2110행, `03_src/outrigger_sim/verify/s8_control.py` 5666–5815행(행 판정 도구가 `settle_lift_split`·`THREE_POINT_ROCKING_PERIOD_S`를 그곳에서 import; `03_src`는 R2와 HEAD 사이 diff 0). 경로 1 도구 `resume4368_judge.py` 1100–1133행(oc5 키 출처). R3d·R3c 출력은 이름·키·상태만. 봉인 rev24 `.md`(`.sha256` 첫 토큰만)와 경로 2는 열지 않음. C-5 사건 행 판별 확인 때 행 판정을 scratch로 돌려 상태만 출력.
- R3d(rev22·rev23) 작업: 정의 넘김 `rev22_definitions_handoff_path1.md`(sha `68bebde2…`), rev22·rev23 봉인본은 `.sha256` 첫 토큰만, R3c 출력(읽기만) `judge_f9bc3c7\chrono_path1\SHA256SUMS.txt`·`run_path1_r3c.ps1`·`runner_judge\C5_E_G4_Fs8_LS1.verify_S8C.json`의 러너 행 이름과 `s8_metrics` 키, R3c 러너 출력 이름 점검(이름과 참거짓만). 경로 2 코드·출력, 넘김 문서의 다른 절은 열지 않음.
- 앞 단계(R3·R3b·R3c)의 경로 1 보고는 **앞 세션 보고이고, 이 판정서 작성 때 원문 파일을 갖고 있지 않다**(scratchpad의 `p1_r3d_report.md`는 rev22 R3d 도구 보고). 이 작성자가 앞 세션 transcript(`~/.claude/projects/C--workspace-outrigger-control/6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1.jsonl`)에서 경로 1 보고의 "읽은 파일" 절을 찾아 옮긴 것은 아래와 같다(읽기 전용 추출, 보고 본문 그대로). **R3(최초 경로 1 Chrono 판정, `judge_576eb87`) 보고의 "읽은 것"은 앞 세션 transcript 두 개(`6f3ebc4d-…jsonl`, `9d4aec18-3b7f-4f45-ae19-6d57127a6418.jsonl`)에서도 찾지 못했다 → 원문 미보유로 공개한다(사용자 결정 110 (3)).** 같은 transcript의 R2 전 경로 1 도구 보고 둘(16117행 G-S 결함 수정 `e237e97`, 16181행 manifest 조건 표 `870d8fa`)은 "경로 2 폴더(`path2*`)는 열지 않았습니다"라고 적었다.
  - R3b(transcript 26510행, 2026-11-15 05:57 UTC, "436.8 R3b 경로 1 Chrono 판정 도구 보완"; 경로 2 도구·출력 `path2*/`, `judge_*\chrono_path2*\`는 열지 않음): **규칙** `v5_resume_4368_rules_rev18.md`(전문), 원판 5.2~9.3(126~325행), rev6 R6-A·R6-B4·B8, rev1 RV1-7, rev2 R2-5·R2-6, rev15·rev16·rev18의 grep 줄, rev4·rev3의 C-5 grep 줄, `.sha256`(rev16~18), `d1_selection_rules.md` 5~11절, `d1_selection_rules_rev1.md`, `v5_criteria_rev12/12a/12b.md`, `v5_criteria_rev6.md` 4절(+grep), rev7 grep, 명세 `s6_control_spec.md` 17246~17300·17680~17696·315~322행. **코드** `chrono_rows_judge_4368.py`(대부분), README, `resume4368_judge.py`(oc5·fmin-time·COMMANDS·상수), `chrono_t45_replay.py`(머리말·824~1035), `s9_soil_event_screen.py` 525~612, `run_S6C.py`·`run_S8C.py` main·judge 부분, `verify/s8_control.py` 실패·hold 계수 부분, `s6_bundle_c.py` grep, 시험 `test_chrono_rows_judge_4368.py` 1~120·509~555, `test_resume4368_rev1.py` fmin-time 시험. **데이터(읽기 전용)** `judge_576eb87\chrono_path1\`의 `run_path1.ps1`·`judge_C2.json` 구조, `judge_b9f5707\chrono_path1\`의 `runner_judge\` 목록과 C1 행 2개·`runner_judge_C1_summary.json` 일부, `07_results\S9\` 배치 10개의 `batch.json`(행·역할), `result.json` 구조(S-02, PS-c cslow, C-6), `chrono_rows_manifest.json`.
  - rev19 정렬(transcript 26827행, `z4374-p1chrono`): 정의 `scratchpad\p2handoff\rev19_definitions_handoff.md`(sha `ff5e61b8…` 확인), rev19 봉인본은 `.sha256` 첫 토큰만. 원 규칙이 인용하는 도구 `run_S9.py`(`soil_event_stop_s`, `judge_chrono_soil_event`, `SOIL_EVENT_*` 상수), `s9_soil_event_screen.py` `_pressure_rows`, `verify/s6_control.py`(`_force_metrics`, R/D8 행), `verify/s6_bundle_c.py`(D8 행), `verify/s8_control.py`(실패·hold 계수, `liftoff` 쓰는 곳), 앞 작업의 `chrono_rows_judge_4368.py`. 데이터: `judge_b9f5707` runner_judge의 C-1 S8C·S6C 각 1개 `metrics`·`s8_metrics` 키, S-02 `result.json`의 `s9_rows`·`events` 꼴. 경로 2 코드·출력은 열지 않음.
  - R3c(transcript 27540행, 2026-11-15 07:57 UTC, `z4375-p1chrono`, rev21 R21-1~R21-3): 정의 `rev21_definitions_handoff.md`(sha `e9744fac…` 확인; **이 인계 파일은 R21-1 안의 결과 문장 1개를 메인 세션이 손으로 지운 판이다**, 사용자 결정 70 공개), rev21 봉인본은 `.sha256` 첫 토큰만, 다른 절·dynamics-expert 진단 파일·경로 2 코드·출력은 열지 않음. 코드: 그 브랜치의 `chrono_rows_judge_4368.py`(`judge_rigid`, `bracket_10hz_lift`, V0 구간 대체 부분), `chrono_bundle_grade_4368.py`(`t_lift_difference`, `rigid_row`), 시험 두 파일.
  - 같은 transcript의 경로 2 앞 단계 보고: R3b 중단 보고(27613행)와 R3c 판정 보고(28091행, HEAD `f9bc3c7`, P코어 0xFF00)는 경로 1 도구·출력(`chrono_rows_judge_4368.py`·`chrono_bundle_grade_4368.py`·`resume4368_judge.py`·`judge_*\chrono_path1\`)을 열지 않았다고 적었다.

**경로 2** — 작성자: 경로 1 도구를 만들거나 고친 적 없는 별도 작성자(원판 9.2 요건). **작성자 교체 공개(사용자 결정 62)**: rev18 봉인(S6 `59c933b`) 뒤 R3b 단계에서 처음 경로 2 작성자 에이전트를 맥락 소실로 부를 수 없어 새 작성자로 바꿨다. 새 작성자에게는 경로 1 내용을 주지 않았고 rev18 R18-3 정의 문장과 경로 2 README만 넘겼으며, 규칙 개정은 없었다. 그 뒤 R3b~R3f의 경로 2는 이 작성자가 맡았다. 아래 "원 경로 2 작성자"·"경로 2 작성자"는 교체 뒤의 작성자를 가리킨다. 브랜치 `z4377-p2chrono`, 도구 디렉터리 `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/`.

- 공통 블록 sha256 **`0e082b9c3b3ce3ff384a5cbf5d62da41bf766c423411d5eb3395217c79630b5d`**(넘기는 문장 147줄, sha `db596ee3…` 확인; rev25 봉인 `c0b778fd…` 원문 sha와 `.sha256` 첫 토큰 같음 확인).
- R3f(rev25) 작업: 명세 `s6_control_spec.md` 421.1(16310~16325행), 422.6(16531~16552행); v5 기준 개정 9 45~67행, 개정 8 59~72행; 원 G6 판정기 `04_scripts/03_control/s8/r76_g6_chrono_judge.py` 4~9, 16, 341~348행. 실제 기록 열람(값 출력 없음): C-2~C-5·C-8 SCM 행 `result.json` `args`의 키 이름과 문자열 값(`soil`, `pad_variant`, `soil_patch`, `rigid_base`, `mass_scale`이 숫자라는 것), L2b 행 하나의 `record.npz` 키 이름, R3d 경로 2 출력 키 경로(시각 키·출력 폴더 문자열 위치 찾기), CD-3 판별의 L2b 32행 클래스와 `event_t_s` 수치 여부(참거짓). 앞 판 경로 1 코드, rev25 `.md`·`_seal_candidate_draft.md`, S13 커밋 본문은 열지 않음.
- **SCM 23행 P3-7 시각 일치 참거짓 열람(공개, rev25 R25-0)**: R3e 작업 때 P3-7 재구성 정의를 고르려고 실제 SCM 23행(C-2·C-3·C-4·C-5·C-8)의 `record.npz`·`c2_soil` meta에 재구성을 돌렸고, 출력한 것은 "t_P·t_LOC가 meta와 1e-6 s 안에서 같은지"의 참거짓뿐이다. P3-7 상승값과 판정은 보지 않았다. R3f 작업에서는 이 점검을 다시 돌리지 않았다.
- R3e(rev24) 작업: 인계 파일 전체(90줄, sha `c8fc6071…`); 명세 7148~7161, 11012~11056, 11085~11101, 11879~11895, 16857~16886행과 grep 줄(3, 77, 79, 10908, 10936~10940, 11092, 11100, 11210~11247, 11823, 11952~11985); 원판 238~327행(+ 머리말 grep); v5 기준 개정 6 66~81행, 개정 12 전체(88줄); 원 판정기 소스 `s8_control.py` 400~419, 530~608, 915~937, 1589~1599, 1695~1762, 2258~2279, 5360~5551, 7523~7562행(+ grep), `s6_control.py` 140~189, 215~249, 585~609, 840~984, 1360~1389, 2020~2099행, `run_S8C.py` 150~175(import), 4264~4463행, `s6_bundle_c.py`·`s7_control.py` grep 줄; 실행 기록 `result.json`·`record.npz`·`step_series.npz` 키 이름과 모양, OC5 `batch.json` argv 옵션 이름; R3d 출력은 이름·키·행 폴더 경로만, 실행 설정(`settings.event`·`level`·`s8`, `args` 문자열, LW `mode`)은 이름과 문자열만. 경로 1 코드·출력, rev24 `.md`·초안, S12 커밋 본문은 열지 않음.
- R3d(rev23) 작업: rev23 `.md` 원문 sha256과 `.sha256` 첫 토큰(`fa72e172…`) 계산만, 본문 열지 않음. 경로 1 코드·출력, S11 커밋 본문, 초안은 열지 않음.
- 원 판정기 직접 실행(CD-2): 7.1절 위 2.3절 표와 같은 32회, 판정기 파일 sha는 2.3절.
- **읽은 입력 파일 이름과 sha256(rev3 R3-G2, rev3:415)**: 경로 2 묶음 출력의 행마다 `rows[].input_files_sha256`(예: SCM 행 `result.json`·`step_series.npz`·`r8_series.npz`·`record/record.npz`, L2b 행 `pads.npz`·`record.npz`, L1-R 행 `record.npz`)에 이름과 sha256이 있다(`p2_C{1,2,3,4,5,6C7,8}.json`, `outputs.sha256`으로 고정).
- 원판 9.2 "경로 1 코드를 본 사실": 두 경로 작성자 보고 모두 "열지 않음"이다. 경로 2 작성자가 경로 1 코드·출력을 본 사실은 없다(판정 불가 사유 없음).

### 7.2 출력 sha256

- 경로 1: `judge_8a0c843\chrono_path1\` 64파일(부록 A, K-R 감사자가 고정; 실행 스크립트가 `SHA256SUMS`를 만들지 않음). 주요: `bundle_C1.json` `30c0da5c…`, `bundle_C2.json` `0dd4129b…`, `bundle_C3.json` `b10bb25d…`, `bundle_C4.json` `6610eb13…`, `bundle_C5.json` `8dca4678…`, `bundle_C6C7.json` `66e5bf3c…`, `bundle_OC5.json` `d8a7b066…`, `judge_C5.json` `d952f075…`.
- 경로 2: `judge_8a0c843\chrono_path2\outputs.sha256`(`d576ddf8350692ce84dc58018630e788f6082b62b61fe92b0a763201cfa0396c`, 121항목, K-R 대조 모두 일치). 주요: `p2_C1.json` `52769dbc…`, `p2_C2.json` `a3794370…`, `p2_C3.json` `12c6fac3…`, `p2_C4.json` `5def3fdd…`, `p2_C5.json` `e8462c305933fb22f3984232e52750049f7434a01ebf5d9bebd3410ddb348bd8`, `p2_C6C7.json` `5027ee60…`, `p2_C8.json` `eb0b8c53…`, `p2h_chrono.json` `ad0b9a7c…`, `p2h_oc5k_C-8a.json` `805ad500…`, `p2h_oc5k_C-8b.json` `51d2ae5f…`, `p2h_openloop.json` `87dc0254…`, `e7_path2.json` `79a85e2d…`, `gs_load.json` `390e884a…`. **`run_path2_r3f.log`(`a2daa35cd3370a50834caa8bfaf45fed587b4c0cebeb8978dc42fcab620aa019`)는 `outputs.sha256` 목록 밖이다.**

### 7.3 K-10 대조 (원판 9.2, rev25 CD-10; K-R 감사 2절)

**(가) CD-11 등급 항목(공통 ID 기준)**

| 묶음 | 일치 | 판정 다름 | 한 경로에만 있음 | 조항 ID 다름 |
|---|---|---|---|---|
| C-1 | 120 | 0 | 52(경로 1에만: L1-R 기록 4행 × 13) | 0 |
| C-2 | 55 | 0 | 9(경로 1에만: PS-c 기준 행) | 0 |
| C-3 | 20 | 0 | 0 | 0 |
| C-5 | 783 | 35(J11 경로 1 `pass` / 경로 2 `record`, 35행) | 62(T4·T5 해당 없음 34 경로 2에만, S9SL P3 18 경로 1 대 427.9 10 경로 2) | 0 |
| 계 | 978 | 35 | 123 | 0 |

- 이 판정서 작성자가 두 경로 CD-11 목록에서 다시 센 값도 같다(일치 978, 판정 다름 35, 경로 1에만 79, 경로 2에만 44, 조항 ID 다름 0; 7.4절).

**(나) CD-2 원 판정기 항목(L2b 32행)**: 항목 판정 일치 779, 표기만 다름 1,287(기록 종류에서 경로 1 `null`, 경로 2 `record`·`runner_unjudged`), 수치 1,854 일치·불일치 0, t_lift 차 확인 32행 × 3값 96 일치(최대 차 0.1 s). (감사자 첫 스크립트의 `D8 no pad lift-off` 11건 불일치는 감사자 스크립트의 키 선택 오류였고, 실제 값은 경로 1 0개, 경로 2 다리별 [0, 0, 0, 0]으로 같다.)

**(다) 행 값**

| 묶음 | 일치 | 불일치 | 양쪽 NA | 비고 |
|---|---|---|---|---|
| C-1 | 22 | 2 | 0 | N1(경로 2 자체 기록 항목과 비교한 것) |
| C-2 | 37 | 0 | 4 | |
| C-3 | 22 | 0 | 0 | |
| C-4 | 44 | 0 | 0 | |
| C-5 | 144 | 21 | 4 | 21건은 키를 잘못 맞춘 것(경로 2 C-5 `t_lift` 기록 항목은 rev6 5의 첫 ≤0 표본; CD-2 t_lift(a) = t_lift,sus는 두 경로 같음) |
| C-6·C-7 | 18 | 0 | 0 | |
| C-8 | 64 + 표기만 다름 4 | 0 | 0 | P3-6·P3-9 경로 1 `pass` / 경로 2 `record` |

- 등급이 같고 수치가 허용 밖인 곳: 없음(위 불일치는 정의·키 대응 차이로 원인이 밝혀짐, 7.5절).

**t_lift 차 확인(CD-2 표, 행마다; 두 경로 같은 값)**

| 묶음 | 행: 차 [s] |
|---|---|
| C-1 | `D1C2_middle_rpBop_Fs4` 0.0, `D1C2_middle_fup3.2_Fs4` 0.1, `D1C2_middle_fdown3.2_Fs4` 0.1, `D1C2_bottom_fup3.2_Fs4` 0.1, `D1C2_bottom_fdown3.2_Fs4` 0.0, `D1C2_bottom_rpBop_Fs4` 0.0 |
| C-2 | `D1C2_middle_rollm4.4_Fs4` 0.0, `D1C2_bottom_rollm4.4_Fs4` 0.1 |
| C-5 | `E_G4_Fs4_V0` 0.0, `E_RE1bF_Fs8_LS1` 0.0, `E_RE1bF_Fs8_LS4` 0.0, `E_RE1bF_Fs8` 0.0, `E_RE1bF_Fs0` 0.0, `G1R_FS24_FL_top_o050_Fs0` 0.0, `E_G4_Fs4` 0.1, `E_G4_Fs4_ph0.05` 0.1, `E_G4_Fs8` 0.0, `E_G4_Fs8_LS1` 0.0, `K8_top_fdown3.5_Fs8` 0.0, `E_G4_Fs8_LS4` 0.0, `S_top_fdown3.5_wika_Fs8` 0.0, `G1R_FS24_FL_top_o050_Fs0_V0` 0.0, `K0V_top_fdown3.5_Fs0` 0.1, `K0_top_fdown3.2_Fs0` 0.1, `K0V_top_fup3.5_Fs0_LS1` 0.1, `K8_top_rpB_Fs8` 0.1, `K0_top_fup3.2_Fs0` 0.1, `K0V_top_fup3.5_Fs0` 0.0, `K0V_top_roll5.5_Fs0` 0.1, `K0V_top_fup3.5_Fs0_LS4` 0.0, `K0_top_rpBop_Fs0` 0.0, `E_G4_Fs4_ph0.05_V0` 0.0 |

- **t_lift 기준(`t_lift_basis`, rev15 R15-3·CD-2 (a))**: L2b 32행 가운데 V0 3행(`E_G4_Fs4_V0`, `E_G4_Fs4_ph0.05_V0`, `G1R_FS24_FL_top_o050_Fs0_V0`)은 1 ms 크롤러 법선이 없어 10 Hz 구간 대체(`bracket_10Hz`)로 t_lift = 27.4 s(단계 절대)를 얻었고, 나머지 29행은 1 ms t_lift,sus(`1ms_sus`)다(경로 2 `CD-2.t_lift.basis`; 경로 1 t_lift 값과 96값 일치). 이 V0 행의 t_lift 정의는 "결과 본 뒤 정한 읽기"다(rev15 R15-3, 사용자 결정 (c)). 판정 후 감사의 "R3f에서 V0 L2b 행은 `1ms_sus`라 해당 행 없음" [추정]은 출력과 다르다.
- 0.1로 적은 값은 0.09999999999976694 s 등 10⁻¹² s 아래 반올림 표기이고 모두 ≤ 0.1 s + 10⁻⁹ s이다. 경로 1 키 `t_lift_check_R19_5.difference_s`, 경로 2 키 `CD-2.t_lift_check.diff_s`. 멈춤 0.

**사건 창 끝 차 확인(CD-3 "적는다", C-5 사건 6행)**

| 행 | 분류 | 경로 1 창 [실행 상대 s] 시작 → 끝, 원 판정기 기록과의 차 | 경로 2 창 [단계 절대 s] 시작 → 끝, 차 | 방법 |
|---|---|---|---|---|
| `E_RE1bF_Fs8_LS1` | 바닥 | 49.700 → 51.796, 0.0 | 52.700 → 54.796, 0.0 | 두 경로 계산 |
| `E_RE1bF_Fs8_LS4` | 바닥 | 49.600 → 51.694, 0.0 | 52.600 → 54.694, 0.0 | 두 경로 계산 |
| `E_RE1bF_Fs8` | 바닥 | 49.800 → 51.894, 0.0 | 52.800 → 54.894, 0.0 | 두 경로 계산 |
| `E_RE1bF_Fs0` | 바닥 | 50.300 → 52.478, 0.0 | 53.300 → 55.478, 0.0 | 두 경로 계산 |
| `G1R_FS24_FL_top_o050_Fs0` | 빠른 침하 | 50.350 → 53.009, 0.0 | 53.350 → 56.009, 차 없음 | 경로 2는 원 판정기 기록 창을 읽음(CD-3 "읽는다") |
| `G1R_FS24_FL_top_o050_Fs0_V0` | 빠른 침하 | 47.850 → 50.541, 0.0 | 50.850 → 53.541, 차 없음 | 같음 |

- 두 경로의 시각 기준은 3.0 s 다르다(경로 1 실행 상대, 경로 2 단계 절대; 경로 1 `t0_s` = 3.0 s). 기준을 맞추면 6행 창 끝 절대 시각이 두 경로 같다(K-R 2절 (라)). 차 > 0.1 s 또는 그 차로 판정이 바뀐 행 0(경로 1 `verdicts_changed` 빈 목록, 경로 2 `judge_window_changes_verdict` 거짓).

### 7.3a rev6 R6-A 공개 수 (경로 1 집계의 러너 값 대 새 판 값)

| 의무 | 결과 | 출처 |
|---|---|---|
| rev6:55 행마다 러너 값과 새 판 값이 다른 행 수(D 번호) | 겹쳐 쓴(`overrides` 있는) 행: C-1 10, C-2 2, C-5 24, C-3·C-4·C-8 0. 러너 값과 재계산 값(값 또는 판정)이 다른 행: **D-31 / D-39**(C1 D8 재계산) C-1 6·C-2 2·C-5 24, **R19-5**(D-29 t_lift, `pads.npz` `N` ≤ 0 1 ms 표본, rev3 Q-14) C-1 2·C-5 9, **D-32 CD-3 W 안**(사건 행 이동 압력) C-5 6. 판정이 바뀐 행은 없다(C-1~C-3 등급 R3d와 같음, C-5 등급 항목 두 경로 일치) | 경로 1 `bundle_C{1,2,5}.json` `rows[].overrides[]`(`rule`, `runner`, `recomputed`, `applied`) |
| rev6:56 t_D 재정의(R6-B4)로 러너 `p3b.departure`와 다른 행 수 | **0행**: SCM C-2 4·C-3 2·C-4 4·C-5 11·C-8 2, 최대 차 0.0 s | 경로 1 `judge_C{2,3,4,5}.json`·`judge_OC5.json` `t_D_vs_runner_R6_B4` |
| rev6:76 S8-A2가 적용된 표본 수(부상 표본 수), 행마다 | L2b 32행 모두 **0**(C-1 6, C-2 2, C-5 24). L1-R 4행은 `null`(L1-R은 `pads.npz` S8-A2 대상 아님) | 경로 1 `judge_C{1,2,5}.json` `rows[].items.C1_R40.s8a2_airborne_samples_in_window` |
| rev6:85 LOC 취소가 있었던 행 수와, 최종 LOC + 1 s로 계산했다면 377 강등 결과가 달라졌는지 | LOC 취소 **6행**(C-5 P3b_J2 t180 계열: `t180` 59.9 s, `_v0v` 56.6 s, `seed20261026` 56.6 s, `_flow` 57.1 s, `seed20261027` 56.0 s, `seed20261028` 55.8 s; 각 1회, 두 경로 같음). C-2·C-3·C-4·C-8 0행. 이 6행의 P3-8(377 대상)은 첫 확정 LOC 기준(`loc_for_377` = `first`)으로 모두 pass다. **"최종 LOC + 1 s로 계산했다면"의 대안 판정은 출력에 없다**: 두 경로 도구 모두 rev6 83~84행 정의(377은 첫 확정 LOC, 424.8.1 최종 LOC 규칙은 377에 적용하지 않음)대로 첫 LOC만 계산하고 대안 값을 내지 않는다. 대안 계산은 이 판정서에서 하지 않았다 | 경로 1 `judge_C5.json` `loc_timeline.revokes_s`·`P3-8_D-34_D-35.loc_for_377`, 경로 2 `p2_C5.json` `P3-2.revokes_s`·`late_loc_revoked.n_revoke` |
### 7.4 CD-11 항목 목록 대응표 (rev25 CD-11, 누락 점검 4)

- 조건: 두 목록 모두 비어 있지 않음(C-1·C-2·C-3·C-5), 행 수 = 묶음 행 수(10 / 6 / 2 / 35), 판정 행마다 등급 항목 ≥ 1(해당 없음 제외, 기록 행 예외), 조항 ID 다른 등급 항목 0, **한 경로에만 있는 등급 항목 123(C-1 52, C-2 9, C-5 62) → 누락 점검 4 거짓**. 경로 1 `item_list_CD_11.ok` 참·`empty_rows` 빈 목록, 경로 2 `cd11_item_list.problems` 빈 목록.
- **사용자 결정 108 (1)·(2)**: 123건(K1~K4)은 등급 영향 없는 표기 차이로 공개하고 도구는 고치지 않는다. S9SL 표는 경로 2의 427.9 목록을 정본으로 삼는다. 묶음 등급·행 등급에는 영향이 없다.

| # | 내역 | 수 | 원인 | 등급 영향 | 처리 |
|---|---|---|---|---|---|
| K1 | C-1 L1-R 기록 4행: 경로 1이 러너 항목 13개(`run`, `2 attitude…`, `3 F_min (1 ms)`, `4 …`, `5a…`, `7a~7c`, `C-R5…`, `72.1…`, `5.24.2…`, J-P3(null))를 `등급 항목`으로 분류, 경로 2는 기록 행이라 등급 항목 없음 | 52 | 경로 1 분류가 CD-11 "기록 행은 목록에 기록 항목으로 싣고"와 다름. 이 4행은 적용 범위 글머리상 블록 밖("앞 판 그대로") | 없음(두 경로 기록 완료) | 공개, rev26 후보 |
| K2 | C-2 PS-c 기준 행(기록 행): 경로 1이 P3-1~5·P3-7·P3-8·FAULT0·J-P3을 `등급 항목`으로 분류 | 9 | K1과 같음 | 없음 | 공개, rev26 후보 |
| K3 | C-5 비대상 17행의 T4·T5: 경로 2는 `해당 없음(대상 행 아님)` 등급 항목, 경로 1 목록에는 없음 | 34 | 경로 1 목록이 CD-6 "그 밖의 C-5 행에는 T4·T5를 해당 없음으로 적는다"를 싣지 않음 | 없음 | 공개, rev26 후보 |
| K4 | C-5 S9SL 2행: 경로 1 P3 9개, 경로 2 427.9-1~5 | 18 + 10 | 427.9 분기 범위 정의 차이 | 결정 107 (3)으로 해소 | 경로 2 427.9 목록이 정본(결정 108 (2)) |
| (참고) K5 | C-5 J11 판정 표기: 경로 1 `pass`, 경로 2 `record`(35행), 공통 ID·조항 ID(`CD-1 ①`) 같음 | 35 | 경로 2는 J11을 R9-6대로 실제 대체 다리 $n_{late}$만 보는 기록 판정으로 적음 | 없음(둘 다 실패 아님) | 공개만, rev26/436.9 후보(결정 108 (2)) |

- **방법 표(rev24 R24-2·rev25 R25-2 "판정서에 방법 표(CD-11)")**: 부록 C의 "방법 표"(묶음 × 경로 × 방법별 등급 항목 수)와 항목별 칸의 `[경로 1 방법 / 경로 2 방법]`. 경로 1의 "원 판정기 실행"은 R3c 러너 판정 출력을 sha 대조 뒤 재사용한 것이고(이번에 다시 돌리지 않음), 경로 2의 "원 판정기 실행"은 R3f에서 32회 직접 실행한 것이다(CD-2 (1)~(3), 2.3절).(CD-11 "등급이 같아도 표로 싣는다"). 대응 판단은 공통 항목 ID와 조항 ID로 했고, 판정 구간·설명 열은 대응 판단에 쓰지 않았다.
- C-4: 경로 2는 C-4 CD-11 목록을 냈고 경로 1에는 없다. CD-11 첫 문장("C-1~C-5 판정 묶음")과 적용 범위 글머리("C-4 기록 행에도")가 엇갈린다(결정 108 (2) 공개만, rev26 후보).

### 7.5 두 경로 정의가 다른 곳 (원판 9.2 마지막 글머리, K-R 5절·판정 전 감사 1절)

| # | 항목 | 경로 1 | 경로 2 | 영향 | 처리 |
|---|---|---|---|---|---|
| a | J-P3 위반의 H-7 | 미달 + 멈춤 | 미달만(README "H-7 표지, 멈춤 없음") | 이번 위반 0행이라 없음 | 결정 102(멈춤 유지)로 판정서는 멈춤으로 읽음, 공개 |
| b | C-3 G6 펼침 | 목록에만 여덟 ID로 펼침, 등급은 `gates` | 관문마다 등급 항목 | 없음(C-3 등급 항목 20개 일치) | 기록 |
| c | 관문 `identity`·`K1_class` | view 단계에서 봄(목록 판정 null) | 도구 안에서 판정 | 관문이라 등급 밖, 두 경로 실패 0 | 7.7절에 행별 관문 결과 |
| d | C-2 S 행(427.9 분기 아닌 경우) P3-6 역할 | 기록 | 판정 120 s | 지금 S-01·02는 427.9 분기라 잠복 | rev26 후보(결정 108 (2)) |
| e | P3-6 한계 출처 | 421.1 + 러너 `limit_s` 대조 | 421.1 재계산(`soil_patch` 목록까지) | 없음(C-5 SCM `P3-6.limit_s` 일치) | 기록 |
| f | CD-8 D8 ③④, a·t | 러너 $t_D$, 목표 0 가정 | 자기 $t_D$, att − target | 없음(C-8 값 모두 같음) | 크롤러 법선 계열 미확인을 4.7절에 기재 |
| g | PS-c `stroke_le_684.8mm` | R3f에서 기록 분류로 바뀜(`c3f4cad`) | E-5 안 | 없음 | 해소, 기록 |
| h | 등급 항목 ≥ 1 셈 | null 제외 | na·record 제외 | 같음 | 기록 |
| i | `event_t_s` null | 없음으로 읽음 | 같음 | 없음 | 기록 |
| j | J-P3 로드 판독 도달 | `has_rod_sensor` | `meas.rod_pressure` 유한값 | 잠복, J-P3 판정 전 행 일치 | 기록 |
| 107-(1) | 허용 키 목록 밖 네 곳 | OC5PROBE `ready_reached`, C-3 P3-6 기록 키, OC5 출력 경로 | `gs_load` 항목 수 키 | 없음 | 허용(결정 107 (1)), 7.6절 |
| 107-(2) | C-5 H-9 사유 빈칸 | 항목 없음 | CD-7 멈춤 → 결정으로 행 등급 미달 | 묶음 상태 | "H-9: M2 끔이라 해당 없음, CD-1 목록 밖 기록 항목" 공개 |
| 107-(3) | C-5 S9SL 토양 가드 정지 | P3 항목으로 판정 → 미달(FAULT0·P3-1·P3-6) | 427.9 분기 → 안전 종료 | 2행 등급 | 경로 2 읽기 채택(rev19 R19-1, CD-4). 경로 1 판정은 정의 차이로 공개. 결정 90의 "S9SL 미달"은 427.9 분기를 모르고 쓴 추정이었음을 공개 |
| K1·K2 | 기록 행의 CD-11 분류 | 러너·P3 항목을 `등급 항목`으로 | 기록 행에 등급 항목 없음 | 없음 | 결정 108 (1) |
| K3 | C-5 비대상 행 T4·T5 해당 없음 | 목록에 없음 | 등급 항목 해당 없음 | 없음 | 결정 108 (1) |
| K5 | C-5 J11 표기 | `pass` | `record` | 없음 | 결정 108 (2) 공개만 |
| N1 | C-1 fdown 2행 D8 최소 | CD-2 C1 줄 51,365 / 51,792 N(REANCHOR 밖) | 같은 값 + 자체 기록 `D8_F_after_liftoff` 29,739 / 30,114 N(REANCHOR 포함) | 없음 | 기록 |
| N3 | C-2 c-slow E-5 행정 | 517.33 mm(러너 `soil_event`) | 512.63 mm(재계산) | 없음(둘 다 ≤ 684.8, E-5 fail은 분기 끝 READY 아님) | R3d와 같음, python-expert 원인 확인 미완 |
| N5 | C-8 8 s 창 RR | CD-8 $F^{\mathrm{t}}$ [t_D, t_D+8) = 95,240.43 N | CD-8 값 같음, 옛 `Fmin_time_8s` 닫힌 구간 95,239.19 N | 없음 | 기록 |
| R3d N2·N4 | 끝 자세 / S 행 P3-4 | – | – | R3f에서 CD-2 "원 판정기 셈 그대로"와 CD-5 READY 없음 해당 없음으로 해소 | 해소 |

- **rev24 R24-5 "정의를 맞춘 것과 공개만 하는 것" 표**(사용자 결정 89의 4)는 부록 D(R24-5 원문)에 그대로 실었다. 그 표의 "C-1~C-3 J-P3를 경로 2 묶음 출력에 두지 않음 | 공개만" 줄은 **rev25 사용자 결정 101로 맞춤(두 경로 모두 ③ 켬 태그 행의 등급 항목)**이다(R3f에서 두 경로 C-1 6행·C-2 6행·C-3 2행 J-P3 pass).
- 경로 1 `moving_pressure_D-32.rule` 문자열에 "rules rev24 CD-3" 판 표기가 남아 있다. 정의는 rev25와 같다(기록).

### 7.6 R3d 대비 허용 차이 (rev24 R24-3 재판정 2·3, rev25 R25-3; 판정 후 감사 1절)

- C-1~C-3 묶음·행 등급: 두 경로 모두 R3d와 같다(경로 1 `grade_differences` 빈 목록, 경로 2 로그 "C-1..C-3 grade change vs R3d: 0").
- 범주 밖 차이(iii): 없음.
- **실행 전 허용 키 목록에서 빠진 범주 안 키(ii) 네 곳 — 사용자 결정 107 (1)로 허용**

| 경로 | 파일 | 키 | 범주(rev25 R25-3) | 근거 |
|---|---|---|---|---|
| 1 | `judge_OC5PROBE.json` | `rows.#.items.ready_D-27_D-28.ready_reached`(2행, R3f에만) | CD-5 READY 없음 | rev25 행 판정 도구 `ready_items`가 READY 없는 행에 더함 |
| 1 | `bundle_C3.json` | `rows.#.record_items.#.{limit_matches_runner, limit_row, limit_s, runner_limit_s, value, source}`(2행 × 6) | CD-4 P3-6 역할·한계 | C-3 P3-6 기록 항목이 421.1 한계 필드를 얻음 |
| 1 | `bundle_OC5.json` | `rows.#.oc5_file`, `rows.#.fmin-time_file`(2행) | CD-10 실행 출력 위치 | R3f 출력 폴더 경로 |
| 2 | `gs_load.json` | `rows[#].absent_inputs`(21), `n_items`(10), `n_judged_keys`(10), `r7_4_absent_where_required`(5, None → []) | rev24·rev25 항목 정의 변경의 결과 | G-S 행은 판정 대상 아님(원판 11.2) |

- 경로 1 C-5 비교는 상한 200건으로 잘렸고(`truncated`) 경로 2 C-5도 207 > 200으로 잘렸다. C-5는 묶음 전체가 허용 범주라 판정 영향은 없다.
- C-4는 경로 1에서 새 출력(`new_in_r3e` C4 참)이라 대조하지 않았다(R24-3 재판정 3). C-4·C-8 기록 상태는 R3d의 경로 2 `기록 불완전`에서 R3f 두 경로 `기록 완료`로 같아졌다(R3d D10·D14 해소).

### 7.7 관문 결과 (CD-11 관문, 대응 대조 밖; 행별)

| 관문 | 경로 1 | 경로 2 |
|---|---|---|
| `identity` | view 단계 `record_check_chrono_view.json`(64행, 문제 3 = 열린 루프 R18-2a 해당 없음), 목록 판정 null | SCM 22행 + C-1·C-2 L2b 8행 pass, 실패 0. C-5 L2b 24행·C-2 PS-c 기준 행에는 관문 없음 |
| `K1_class` | view 단계 `k1_classification_7_2_view.json`(5.1절), 목록 판정 null | C-1~C-5 행 `indeterminate` 0 |
| `R9-1` (expect_controller) | 실패 0(열린 루프 3행 해당 없음) | pass, 같음 |
| `R11-4` (커밋 정체성) | 모든 묶음 `commit_identity_R11_4` `match` | pass, 같음 |
| `T4-0` | C-5 대상 18행 pass | 18행 pass + 비대상 17행 해당 없음 |
| 행 수 검사 | C-1 10, C-2 6, C-3 2, C-4 4, C-5 35, C-6·C-7 3, C-8 2 모두 일치 | 같음 |
| t_lift 차 확인 | 32행 ≤ 0.1 s(7.3절) | 같음 |
| 사건 창 끝 차 확인 | 6행 0.0 | 바닥 4행 0.0, 빠른 침하 2행 차 없음(창 읽음) |
| C-8 R3d $m$ 대조 | 비교기에서 `m_N`·`min_leg` 차이 없음 | `CD-8_S9.r3d_equal` 참 |

- 관문 실패 0 → 관문 멈춤 없음.

### 7.8 독립성과 원 판정기 공유 (공개)

- rev24 R24-5와 rev25 R25-5의 독립성 공개 문장은 10.2절에 그대로 실었다. 요지: 경로 2는 L2b 원 판정기 항목 값("원 판정기 셈 그대로" 항목)을 같은 원 판정기를 따로 실행해 얻었으므로 두 경로는 그 값의 계산 함수에 함께 기댄다. 경로 1은 빠른 침하 W와 $T_3$에 원 판정기 함수·상수를 쓴다. C-3 G6 대응은 두 경로가 같은 원 G6 판정기 정의에 기댄다.
- D12: C-6·C-7 P3a는 두 경로가 같은 저장값에서 읽었다(독립 아님).

## 8. 덩어리 표 (rev25 R25-3)

### 8.1 경로 1: `git diff -U0 0220671 8a0c843` (경로 1 다섯 파일)

경로 1 도구 커밋 `c3f4cad`(R3f에 병합된 `z4377-p1chrono` 커밋). `--is-ancestor 0220671 c3f4cad`·`--is-ancestor 086866a c3f4cad` 참(`c3f4cad`의 부모 `3a61d4d`에 대해 판정 전 감사가 확인, `c3f4cad`는 그 자식). 분류는 경로 1 R3f 보고의 표(`0220671` 기준; `086866a..HEAD`가 건드리지 않은 덩어리는 rev24)에 `c3f4cad` 줄을 더한 것이다. 덩어리 머리 전체 목록은 부록 B.

| 파일 | 덩어리(감싸는 이름) | 분류 |
|---|---|---|
| `chrono_bundle_grade_4368.py` | 모듈 docstring(`-26 +26,20`) | rev24 + rev25 정의 |
| 〃 | docstring 기록 묶음·CLI·종료 코드(`-40`, `-55`, `-59,3`) | rev24 정의 |
| 〃 | `TOOL_VERSION`(v7)·`RULES_TEXT` | rev24 + rev25 정의 |
| 〃 | `EXPECTED_ROWS`/`BUNDLE_CRITERIA`(C-4), `RECORD_BUNDLES` | rev24 정의 |
| 〃 | CD-2 상수, `RIGID_OVERRIDES`, `CD3_ITEM_IDS` 삭제, `CD11_RULE` | rev24 + rev25 정의 |
| 〃 | `runner_items`(`case_star` 표시), `_runner_reason` | rev24 정의 + rev24 범위 안 결함 수정(case `*`) + rev25 정의 |
| 〃 | `recomputed_verdict`, `is_event_row`, `_override_applies`, `apply_rigid_overrides`, `_override`, `apply_d8_overrides`, `RigidResult.reason`, `rigid_row`, `event_window_stop`, `runner_part_reason`, `has_first_ready`, `checked_item`, `word_item`, `not_applicable_item` | rev24 정의 |
| 〃 | `p3_items`(`args`, `p36_graded`), `P36_*`, `p36_limit`, `p36_item`, `_p35_item` | rev24 + rev25 정의(CD-4 P3-6, CD-5 P3-6) |
| 〃 | `_p31_item`, `_p32_item`, `_p39_item`, `_fault_item`, `soil_event_items` | rev24 정의 |
| 〃 | `grade_row`, CD-7 보조 함수, CD-11 절(`cd2_clause`, `list_entry`, `_runner_entries`, `_t45_entries`, `_g6_entries`, `_sgs_entries`, `_item_entries`, `_gate_entries`, `row_item_list`, `graded_count`, `item_list`) | rev24 + rev25 정의(CD-11 분류, 조항 ID, G6 표, `[case *]`) |
| 〃 | `_scm_items`(P3-6 역할, P3-9 기록) | rev25 정의 |
| 〃 | `_g6_items`, `_row_grade`, `_graded_bundle`, `build_parser` | rev24 정의 |
| 〃 | `oc5_row`, `c8_record_values`, `_leg_minima`, `scm_force_minima`, `_close_lists`, `scm_d8_values`, `g6_record_values`, `is_rigid_base`, `c4_row` | rev24 + rev25 정의(CD-8 1/7/8/9) |
| 〃 | `cd7_cd11_stops`, `record_reason_check`(C-4 CD-7), `p36_limit_stops` | rev24 정의 + **rev24 범위 안 결함 수정**(C-4 빈 사유 멈춤) + rev25 정의 |
| 〃 | `_record_bundle`(C-4 사유 검사와 멈춤) | rev24 정의 + **rev24 범위 안 결함 수정** |
| 〃 | **`c3f4cad`**(`git diff -U0 3a61d4d c3f4cad`): `-1666,0 +1667,4`(`ITEM_CLAUSES` 다음), `-1685,0 +1690,3`·`-1687,2 +1694`(`_item_entries`) — PS-c `stroke_le_684.8mm`를 CD-11 목록에서 E-5의 기록으로 분류. README `-175`·`-195`·`-198`(설명·sha·시험 개수), 시험 `-1710,0 +1711,16`(`test_cd7_c4_empty_reason_stops` 뒤 새 시험). 3파일 +27 −5 | rev25 정의(R25-2 [경로 1] 1 "CD-11 분류 열·조항 ID 열"; R3f 판정 전 감사 실행 전 수정 2) |
| `chrono_rows_judge_4368.py`(판 문자열 그대로) | docstring CD-3/CD-5, CLI | rev24 정의 |
| 〃 | 봉인 docstring 줄, `RULES_SEALS` rev24·rev25 항목, `RULES_DESCRIPTION` | rev24 + rev25 봉인 목록 |
| 〃 | CD-3 상수와 함수 | rev24 정의 |
| 〃 | `ready_items`(READY 없는 P3-6 기록) | rev24 + rev25 정의 |
| 〃 | `judge_scm` 문구, `g6_grade`/`_g6_ready_missing`, `judge_rigid`, `cmd_judge`, `build_parser` | rev24 정의 |
| `chrono_rows_judge_4368_README.md` | rev25 해시(`-99`), §7a(`-120,0 +121,9`), 봉인·제목 줄, C-4 CD-7 줄(결함 수정)과 rev25 표 줄, sha 표·시험 개수 | rev24 + rev25(+ 결함 수정 설명) |
| `test_chrono_bundle_grade_4368.py` | `write_scm_series`(`roll_pitch_deg`)·C-8 fixture, R23 비교 시험, rev24 시험 + rev25 시험(`-1378,0 +1456,336`) | rev24 + rev25 정의 시험 |
| `test_chrono_rows_judge_4368.py` | 봉인 기대값, READY 시험(rev25), `-822,0`(rev24) | rev24 + rev25 |

- 경로 1 `0220671..8a0c843`의 나머지 파일은 (가) 규칙 6파일과 `.gitattributes`(S12·S13 병합으로 들어옴, (가)로 분류)다.
- `c3f4cad`의 덩어리는 위 표 줄에 `3a61d4d..c3f4cad` 기준으로 따로 적었고, 부록 B의 `086866a..c3f4cad` 목록에도 함께 들어 있다.

### 8.2 경로 2: `git diff -U0 0220671 8a0c843 -- …/path2_chrono/`

경로 2 도구 커밋 `0f2fd4e`(R3f에 병합된 `z4377-p2chrono` 커밋). `--is-ancestor 0220671 0f2fd4e`·`--is-ancestor 24481ad 0f2fd4e` 참(판정 전 감사 2절). 분류는 경로 2 R3f 보고의 표.

| 파일 | 덩어리(감싸는 이름) | 분류 |
|---|---|---|
| `README.md` | `-4 +4`(규칙 해시 줄), `-59 +59,3`(도구 sha 표), `-125,0 +128,11`(CD-1~CD-11 구현 위치, 정의마다 한 줄) | rev24·rev25 봉인 목록, 도구 sha·시험 개수, rev24 + rev25 정의 |
| `p2_b_c1.py` | docstring, import, `judge_row` | rev24 정의(CD-2) |
| `p2_b_c2.py` | docstring, import, `judge_row` L2b | rev24 정의 |
| 〃 | `judge_row` S 행(`-48,0 +53,4`) | rev24 정의(P3-7, CD-5) + rev25 정의(`set_p3_6`) |
| 〃 | `_psc_base`(`-64,0 +73,3`) | rev24 + rev25 정의(P3-6 기록) |
| `p2_b_c3.py` | docstring, import; `judge_row`(`-19,0 +24,5`) | rev24 + rev25 정의(G6 대응표, P3-6 기록, `g6_split`) |
| `p2_b_c4.py` | docstring, import; `judge_row`(`-33,2 +37,8`) | rev24 정의(CD-9) + rev25 정의(P3-6, `g6_split`) |
| `p2_b_c5.py` | docstring, import, 상수; `judge_row`·`_add_p3`(`-45 +57,26`); `engine_counts`·`bundle_status` | rev24 정의(CD-1·2·4·6, 행 수, CD-6 문구) + rev25 정의(P3-6 판정, `cd1_role`) |
| `p2_b_c8.py` | docstring, import; `judge_row`·`_add_record_values`·`_c8a_s9`(`-49,0 +66,30`) | rev24 정의(CD-8) + rev25 정의(P3-6·G6 분리·옛 D8 기록 뺌) |
| `p2_cd.py` | 새 파일(`-0,0 +1,1402`) | rev24 정의: `cd2_items`, `cd3_items`, `event_window`, `t_lift_a`, `p3_7` 재구성, CD-5·6·7, CD-8·9 기본. rev25 정의: `recalc_c1` 사건 시각 절단, `p3_6_limit`·`set_p3_6`, `g6_split`, `apply_rev25_row`(관문, J-P3), `item_list`·`clause_id`·`_cd2_entries`·`_safe_stop_entries`, `_table_line`, `c8_values`·`scm_d8_values`, 구간 문자열. rev24 범위 안 결함 수정: (가) `judge_rows_of` case `*` 행 포함·`common_id` 접미 ` [case *]`, (나) `p3_7` 문턱 0.01 × mass_scale × W_ref·`_mass_scale` |
| `p2_chrono.py` | import·`COMMON_FILES`·상수, `augment_items`, `judge`·`finish_rev24`·`main` | rev24 정의 |
| 〃 | `judge`(`-381,0 +394,2`) | rev25 정의(`apply_rev25_row`) |
| `p2_kinds.py` | `jp3_item`, `JP3_NA_OFF`, `rod_reading_present` | rev25 정의(CD-1 J-P3) |
| `p2_rules.py` | `SEALED`, `RAW_ONLY`, `seal_check` | 봉인 목록 rev24 + rev25 |
| `test_p2_synthetic.py` | `write_rod_record`, `t_scm` J-P3; `t_seal`; `t_cli`; rev24 시험·`t_rev25`·`main` | rev25 정의 시험, 봉인 목록 시험, rev24 시험 + rev25 |

- rev24 범위 안 결함 수정 (다)(K-10 실행 정체성 키)는 저장소 밖 비교기 `k10_compare_r3f.py`에 있다(2.3절).

### 8.3 경로 1 rev25 몫: `git diff -U0 086866a c3f4cad -- 04_scripts/02_chrono 05_tests/unit`

- 5파일(`chrono_bundle_grade_4368.py` 45덩어리, `chrono_rows_judge_4368.py` 7, README 9, `test_chrono_bundle_grade_4368.py` 13, `test_chrono_rows_judge_4368.py` 6). 경로 지정 없는 `086866a..c3f4cad` 전체에는 S13 병합으로 들어온 rev25 규칙 3파일과 `.gitattributes`(`-text` 3줄)가 더 있고 (가)로 분류한다. 덩어리 머리 목록은 부록 B. 분류는 8.1절 표의 rev25 정의·결함 수정 줄과 같다.

### 8.4 경로 2 rev25 몫: `git diff -U0 24481ad 0f2fd4e -- …/path2_chrono/`

- 11파일(README 3, `p2_b_c2.py` 2, `p2_b_c3.py` 2, `p2_b_c4.py` 1, `p2_b_c5.py` 4, `p2_b_c8.py` 4, `p2_cd.py` 46, `p2_chrono.py` 1, `p2_kinds.py` 5, `p2_rules.py` 4, `test_p2_synthetic.py` 12). 경로 지정 없는 전체에는 S13 병합 (가) 파일이 더 있다. 덩어리 머리 목록은 부록 B. 분류는 8.2절 표의 rev25 정의·결함 수정 줄과 같다.
- 판정 전 감사 2절: `0220671..R3f` 덩어리 분류가 rev24 정의 / rev25 정의 / rev24 범위 안 결함 수정으로 나뉘고 허용 범위 밖 덩어리 0(대상 `1fadc06`). `c3f4cad` 한 커밋은 그 뒤 추가이고 범위 안이다(2.1절).

## 9. 관문 (원판 11절, 13절 10항)

| 관문 | 결과 | 근거 |
|---|---|---|
| 11.1 옵션 × 단계 겹침 표 | Chrono 묶음은 실행 전 감사에서 대조(하네스와 함께) | 실행 전 감사 리포트 경로·sha는 `확인 필요`(R2 실행 전 감사) |
| 11.2 G-S 건조 실행 | Chrono G-S 출력 `v5_resume_4368/gs_chrono_b9f5707/`(R2, 배치 폴더 `07_results/S9/batch_V5-RESUME-K1-GS_20261113_182641`·`…_194755`), PS-c G-S `gs_psc_b9f5707/`(배치 밖, rev15 R15-6). 경로 2 `gs_load` 단계 종료 0(행 12, 오류 0). **"G-S 행 등급은 판정하지 않음"**(rev11 R11-5) | 파일별 sha256은 9.1절 표 |
| 11.3 러너 로그 | Chrono 러너 단계 모두 `exit=0`(2.2절). `tools/verif/log_errors.py`를 Chrono 러너 로그 6폴더(`run_chronoA/B/R`, `c2_oc5\logs_c2_4`·`logs_c2_psc`·`logs_oc5`) 16개에 돌린 결과(판정 후 감사 `scratchpad\audit-judgement-4368\judgement_postaudit.md` 기록 3): 종료 0이지만 16개 모두 `no_errors_line`, 즉 `errors N` 줄이 없는 **빈 통과**다. 실제 근거는 `.done exit=0` 11단계(wall 315 / 1,954 / 9,389 / 8,325 / 27,897 / 24,043 / 1,675 / 5,538 / 9,604 / 18,047 / 4,748 s, 2.2절 표와 같음)다 | `run_b9f5707/logs/`, `run_b9f5707/c2_oc5/` |
| 11.4 자리표시 | R3f 판정 전 감사 `placeholder_scan`(`p1r3f\*.md`, `p2r3f\*.md`) 0건. 이 판정서의 14절 채울 칸은 10절에서 값으로 바꿨다 | 판정서 커밋 전 감사에서 다시 본다 |
| 실행 전 감사(A-10) | R3f 판정 전 감사 `r3f_prejudge_audit.md` sha256 `a64952156e16055188141967c691263bc07371045cfc4747cc5b7eb6d0b8b11c`(차단 0, 대상 `1fadc06`). 판정 후 감사 `r3f_postrun_audit.md` `9df13449…`(차단 0). K-R `r3f_kr_cross_path.md` `1980bd4f…`(차단 1 → 결정 108). rev25 넘기기 전 감사 `rev25_prehandoff_audit.md` `59feeb79933eea5e66a263e8958007c7b49cc8e23a3167fcb05327a717d7889f`, R3e 판정 전 감사 `r3e_prejudge_audit.md` `09af41108025012e6f9b614025aa2c533086df56ee752921c2bdcb0bdb43e268` | 모두 scratchpad `audit-r3f\`·`audit-rev25\`·`audit-r3e\`. R2 Chrono 본 실행 전 감사 리포트는 파일로 남아 있지 않아 앞 세션 transcript(`6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1.jsonl`)의 감사 보고를 줄 번호로 인용한다(사용자 결정 110 (3), 원문 파일 미보유): 20974행(본 묶음 H-1~H-10·Chrono C-1~C-8·probe 시작 전, R2 `b9f5707`, rev14 `baedeab4` 기준, "차단 1 / 실행 전 수정 3 / 기록 6", 차단은 Chrono 러너 세 개의 경로 오류 → 고친 뒤 실행, 사용자 결정 34), 23282행(C-8a·C-8b O-C5 본 행과 C-2 6행, R2·P 8–15, "차단 1 / 실행 전 수정 1 / 기록 9", 차단은 C-2 PS-c 2행의 rev5 R5-B4 순서 → PS-c 2행을 따로 뒤에 실행). 그 앞 20422행은 rev13 기준 H-0 뒤 감사(차단 0)다 |

- 하네스 G-S(`gs_harness_*`)와 H-0 관문은 하네스 R4 판정 뒤. (갱신 2026-11-16: 하네스 판정서 2.1절(G-S `gs_harness_b9f5707`, 새 묶음 G-S 면제와 대체 점검)·4.1절(H-0 통과)·부록 B)


### 9.1 G-S 파일 sha256 (rev11 R11-6, 원판 13절 10항; 이 판정서 작성 때 잼)

| 폴더 | 파일 | sha256 | 바이트 |
|---|---|---|---|
| `gs_chrono_b9f5707` | `batch_stdout.log` | `b0084564c0a0971215f585b8416b3f0713be5c66f65c343fd376172380679f16` | 233 |
| `gs_chrono_b9f5707` | `compare_vs_182641.json` | `7c15ada4600ecba9fbe549a84b05e8e004babe7415f7c97c8ac80f365c841392` | 12362 |
| `gs_chrono_b9f5707` | `gs_check.txt` | `7308853d7cbf6309a58a76a1b623b47cb2aa4fa786cd67424677e44d8dfd4983` | 12694 |
| `gs_chrono_b9f5707` | `judge_out.json` | `1caaeefb1c4c023d52c7f38a708a9734b102453134531c95529e3d5f294f03b9` | 73857 |
| `gs_chrono_b9f5707` | `judge_stdout.txt` | `8bf55229a8e1613d5ba1990cf5c75b384f86b3d6e53eb52a29d9e30db677adf8` | 1626 |
| `gs_chrono_b9f5707` | `p2c_gs_load.json` | `bec566d2a15d48566e0c299e82628c51bfdbcb8d878c4abee8c07049507a19ef` | 37047 |
| `gs_chrono_b9f5707` | `p2h_chrono_gs.json` | `57b9913555720c3d0a1905d14127a01ea88aae74e47648d2d0d8b78804695c1b` | 42121 |
| `gs_chrono_b9f5707` | `p2h_seal.json` | `fe7e14795265f633fcffdcdef56882e5816a18b213354ae3afef4dd73539cc4e` | 10759 |
| `gs_chrono_b9f5707` | `row_summary.json` | `faa0607559cf55903148de7d8c010f13568c25d0cf32101db87863e89dc62ce1` | 8045 |
| `gs_chrono_b9f5707` | `seals.txt` | `827859e0eb28cf331ff720c7b9d3466e060116a931894ade1f36667dd902f47e` | 3761 |
| `gs_psc_b9f5707` | `gs_identity_start.json` | `f270b3d932355dc2cbc28d669169c41c328f64a35294ce60f47158c8aa438ee3` | 407 |
| `gs_psc_b9f5707` | `gs_psc_check.json` | `7f4a80965c8dd027af3545a61400e13a45c12e27d2442a8609f65078ef740b11` | 2969 |
| `gs_psc_b9f5707` | `run_gs_psc.out.log` | `124a4938221022a702b7c72ab78651e275edc65f6303a5c1320e74ed94ebbf90` | 4983 |
| `gs_psc_b9f5707` | `run_gs_psc.ps1` | `06d29023c993bf9a904668146dbaf0928d670cc06b2ee7141ae6810ec0ae258e` | 9823 |
| `gs_psc_b9f5707` | `steps_GS_PSC.json` | `4fb04fb3376ba5e968e0960a22bcb9500a27545a1d041e920b88e6c233d78f76` | 2446 |
| `gs_psc_b9f5707` | `logs/gs_psc_check.done` | `78ee0f2e065383cb3b39d8c3a841b9afddae50b40b89f0ebdd2c8a9229de1989` | 37 |
| `gs_psc_b9f5707` | `logs/gs_psc_check.log` | `40ff424bd1bc0dd9c3d901e0919520afa376df329d1dab940caee36225fc0512` | 312 |
| `gs_psc_b9f5707` | `logs/gs_psc_identity.done` | `0c325712f7be4c3cd375d8f84cf0fadba02d60c82e1d1c16d806dcd1b15f77e6` | 37 |
| `gs_psc_b9f5707` | `logs/gs_psc_identity.log` | `1931697a2e5e411973ad44850c1da6516461cdb032b5a0c8a349a329acaf4adf` | 491 |
| `gs_psc_b9f5707` | `logs/gs_psc_run.done` | `495151d4b2d658eca2d14c92a64a7cd24320d0f7b89d746b848f04e2723a6cdc` | 40 |
| `gs_psc_b9f5707` | `logs/gs_psc_run.log` | `316f1e8a2a23f63fad0b8df9c89c0de6915b75e0146405d77c824caf84c06d3f` | 3951 |
| `gs_psc_b9f5707` | `out/GS_PSC_D1PSC_J1_B_top_Fs4_FL_cslow_d130/completion_series.npz` | `57d0b1f1050c0a62d422f03a18eccad4be4df6e6ed7d1daead96e949ac18cc70` | 315848 |
| `gs_psc_b9f5707` | `out/GS_PSC_D1PSC_J1_B_top_Fs4_FL_cslow_d130/controller_commands.npz` | `365395b4aaca41ae113d42f83dcbc1fbe69f17a2a569046ef5c59596ab483573` | 52516 |
| `gs_psc_b9f5707` | `out/GS_PSC_D1PSC_J1_B_top_Fs4_FL_cslow_d130/flow_series.npz` | `ba5ece9a50a7df58fb05048b2ed9fa4126fd6f654d67942029c3017882eb3e03` | 11566889 |
| `gs_psc_b9f5707` | `out/GS_PSC_D1PSC_J1_B_top_Fs4_FL_cslow_d130/r8_series.npz` | `dcb3179c35ce03485311c723137dc69ce763cd14da0edff01b4e6c6fee7a3c41` | 44802 |
| `gs_psc_b9f5707` | `out/GS_PSC_D1PSC_J1_B_top_Fs4_FL_cslow_d130/result.json` | `7df36856f3555c5c47f770a0c3a9e98add3ab77a8ac6b2b30c823e753a90b741` | 6058919 |
| `gs_psc_b9f5707` | `out/GS_PSC_D1PSC_J1_B_top_Fs4_FL_cslow_d130/soil_event_series.npz` | `7b8b6b0830f46a9f3007589ab465d467b24c525f22fef3cb8b35ff3715243494` | 13275120 |
| `gs_psc_b9f5707` | `out/GS_PSC_D1PSC_J1_B_top_Fs4_FL_cslow_d130/step_series.npz` | `8f5cd1b48ad7e398d1905a84996bb517d3c0b5498e49c9f2f040ab42892663c5` | 31723420 |
| `gs_psc_b9f5707` | `out/GS_PSC_D1PSC_J1_B_top_Fs4_FL_cslow_d130/record/meta.json` | `c3ee953afbd86095e0ffd98d1303f5a2f6a5df8fe00c03ba8961233e3a791ca7` | 50899 |
| `gs_psc_b9f5707` | `out/GS_PSC_D1PSC_J1_B_top_Fs4_FL_cslow_d130/record/record.npz` | `6ebdbc978b35ff1ef555f35bf154dce10ad8e682274461fe18204ec7f7352745` | 916418 |
| `gs_psc_b9f5707` | `tools/gs_identity.py` | `1f424d00be45244095174138e42657fed7cf8d9163c7bd952e66654d787588b1` | 1962 |
| `gs_psc_b9f5707` | `tools/gs_psc_check.py` | `9255f5d1025de45c57de9f74e75f75d4ff27506619bb499a6d4a32d4a452edeb` | 7597 |

- 합계 32파일. `gs_chrono_b9f5707\` 10파일: Chrono G-S 배치 `batch_V5-RESUME-K1-GS_20261113_182641`·`…_194755`의 판정 도구 키 경로 확인 출력(값 판정 아님). `gs_psc_b9f5707\` 22파일: PS-c G-S(배치 밖 실행, rev15 R15-6).
- **`gs_psc_check` 결과(rev15 R15-6)**: `gs_psc_check.json`(`7f4a8096…`) `ok` 참, `failures` 빈 목록, 1 ms 행 55,301, `events_form_ok`·`s9_rows_form_ok`·`phases_form_ok` 참, R4-D 열(`r4d_columns` 12)·사건 키 있음, 사건 시각 − 첫 READY 5.0 s. 두 정체성 파일: `gs_identity_start.json` `f270b3d932355dc2cbc28d669169c41c328f64a35294ce60f47158c8aa438ee3`, 그 행 `result.json`(`code_state` 기록) `7df36856f3555c5c47f770a0c3a9e98add3ab77a8ac6b2b30c823e753a90b741`.


### 9.2 커밋 대상 출력 (판정 후 재감사 권고안, **사용자 결정 111로 확정**, 2026-11-16)

- 커밋한다(`.gitattributes`에 `-text` 줄을 먼저 넣는다; 세 폴더에 CRLF 파일이 131·64·78개 있음): 판정서 `06_analysis/02_control/verif_matrix/v5_resume_4368_judgement.md`, `v5_resume_4368/judge_8a0c843/**`(R3f 판정 출력, 187파일), `judge_0220671/**`(R3d, R3f K-10·CD-8 대조 기준·전후 대조 대상, 117파일), `judge_f9bc3c7/**`(R3c, R3f가 sha 대조 뒤 다시 쓴 러너 판정·t45 재생 출력, 158파일).
- 추적하지 않고 보존한다(지우지 않음, sha는 이 판정서가 고정): `gs_chrono_b9f5707`·`gs_harness_b9f5707`(rev11:90, rev13:120, rev14:85), `gs_psc_b9f5707`(9.1절 22파일 sha), 대체 단계 `judge_062e051`·`judge_576eb87`·`judge_b9f5707`(3.1절 목록 파일 sha; `judge_576eb87\chrono_path1\chrono_view\`는 R3f 입력, 2.3절), 하네스 R4 몫 `h0_judge_b9f5707`·`run_b9f5707`(이 판정서는 러너 로그 경로만 인용).

## 10. 한계 (원판 14절 L-1~L-5와 덧붙임 판의 한계 절 문장)

### 10.1 원판 14절 한계 문장 (채울 칸을 값으로 바꾼 것)

**L-1 비틀림 이득과 θ 채널 $M_s$** (원본 `06_analysis/02_control/k2b/twist_gain_margin.md` 5절)

> 하네스는 잠긴 다리의 로드측 강성이 없어 비틀림 루프 이득이 실기보다 최대 1/1.3배 작다. 실기 이득에서도 비틀림 채널은 $M_s \le 1.25$, GM ≥ 6.0, PM ≥ 73.7°이다. 다만 오거 상단·β 1.6 GPa·마스트 대리 조합 한 점에서 자세 θ 채널 $M_s$가 1.53(기준 1.5)으로, 이 점은 비틀림 이득과 무관한 상계 대리값이며 L1-R Chrono 대표 행이 판정한다.

- 이 436.8에서 L1-R Chrono 대표 행은 C-1 C1-09~C1-12(기록 4행, 두 경로 기록 완료, 러너 항목 통과)다.

**L-2 LOC 앵커 단일 표본 기울기** (원본 `06_analysis/02_control/k2/judgement/loc_anchor_review.md` 4절, `06_analysis/02_control/k2/loc_shadow/hsh_report.md` 0절)

> 크롤러 이탈 확인(LOC) 때의 틈 추정 기준은 이탈 순간 한 주기(0.1 s)의 원시 기울기를 자세로 쓴다. 그래서 단단한 바닥의 이탈 과도에서는 틈 추정이 ±(10~20) mm 흔들리고, 균일 연약 지면 Chrono에서는 −5.5~+2.7 mm다. 중심 1 s 평균을 쓴 그림자 추정과 비교하면 D-1 토양 계열 하네스 456줄에서 차이가 −18.1~+0.53 mm였고, 판정 여유 안쪽에 든 줄은 없었다. 그 밖 묶음은 미측정이다. 추정기 수정은 v5 뒤 과제로 둔다.

**L-3 하네스 $k_{lock}$ 미포함** (원본 `06_analysis/02_control/k2/judgement/k2_dyn_sensitivity.md` 덧붙임 A)

> 하네스 축소 모델에는 잠긴 다리의 로드측 기름 기둥 강성 $k_{lock}$이 없어, 늦게 닿는 대각 쌍이 먼저 래치된 쌍의 하중을 가져가는 비틀림 결합(M2)에서 뒷다리 하중 손실을 약 25 % 작게 본다(β 1.0 GPa에서 −5.2 대 −7.0 kN/mm). 그래서 하네스의 TOUCH·이탈 판정은 이 기구에 대해 비보수 쪽이고, 잠김 상태 판정에 대한 영향은 방향이 정해지지 않았다. v5 하네스 결과는 이 모델 그대로 판정했으며, $k_{lock}$을 포함한 Chrono L1-R 대표 행이 교차 확인을 맡는다.

**L-4 유량 분배 법칙** (원본 `v5/v5_paper_runs_judgement.md` 1.6절, 사용자 결정 11-10 Q-2·11-11 Q6)

> 폐루프 판정(VB)은 우선 분배 법칙을 기준으로 했고, 비례 분배는 열린 루프(J1·G1)에서만 확인했다. G1 열린 루프 VB 비례 분배 행(C-6)은 속도비 0.89474(네 다리, 유량 제한 27.77 s), 폐루프 시작 뒤 이륙 18.921 s, 이륙 전 네 다리 최소 실린더 힘 13.21~13.36 kN(명세 11047 FLAG 없음), 끝 Δroll −0.0076°·Δpitch −0.0290°, 끝 행정 517.5~518.5 mm, P3a-1~5 모두 통과였다.

**L-5 운용 시작 조건 밖의 이탈 뒤 비틀림 하회** (원본 `las_p5r4_k1_judgement.md` 8.2절·"D-2 진단 요약"·10절 D-2, 사용자 결정 2026-11-12; rev24 R24-5 (가)·(나)·(다)로 바꾼 문장, 사용자 결정 88·91·92)

> 혼합 지형(강체 바닥 + 전방 우측 패드 아래 연약 패치) Chrono에서 채택 제어기는 크롤러 이탈 뒤 0.5~0.7 s에 대각 반대 다리(후방 좌측)의 실린더 힘이 $F_{min}$ 아래로 내려갔다(크롤러 강성 ×3·VB 8.64 kN 195 ms, ×1·V0 8.51 kN 67 ms). 골의 깊이(이탈 전 약 40 kN에서 한 주기 평균 11.4 kN(×3·VB), 14.1 kN(×1·V0)까지)는 준정적 하중 재분배다. 이탈 감속(LAS-b)이 끝난 다음 주기의 비틀림 계단과 연약 패치 침하가 기름 기둥 강성을 거쳐 옮겨진 것이다. 이 준정적 성분은 두 행 모두 $F_{min}$ 위에 있었다. $F_{min}$ 아래로 내려간 몫(×3·VB 약 2.8 kN, ×1·V0 약 5.6 kN, 그중 4 Hz 위 약 1.2 kN)은 크롤러 이탈 직후 상부체의 1차 좌우 흔들림–롤 모드(1.5~1.8 Hz, 좌우 다리 역위상) 진동이다. 모델 상부체는 강체라 준정적 비틀림 몫은 보수 쪽이고 β에 민감하다. 진동 몫은 크롤러 강성(×1~×3)·이동 중 다리 감쇠·패드 횡 강성 같은 실측 전 가정치에 좌우된다. ×1·V0 행도 같은 모드다(1.5~1.7 Hz, 이탈 감속은 이탈 0.71 s 전에 시작, 이탈 때 전방 우측 6.5 mm/s). 준정적 성분 14.1 kN은 $F_{min}$보다 4.7 kN 위였고, 67 ms 하회는 진동 몫 약 5.6 kN 때문이다. 이 행들은 실행 시작 자세 비 $R_c$ 1.035~1.076으로 운용 시작 조건($R_c \le 1$) 밖이다. 운용 시작 조건 안($R_c$ 0.952, 바닥 2.1434°·1.3784°)의 혼합 지형(강체 + J1@FR, VB, 크롤러 강성 ×3)에서, 크롤러 이탈 직후 35.286 s에 RL 실제 실린더 힘이 최소 5,869.6 N($F_{min}$ 9,414.6 N 대비 −3,545 N)까지 내려갔다. $F<F_{min}$ 시간은 0.158 s, $F<F_{min}$ + 2 kN 시간은 0.212 s다. 다리는 접지를 유지했다. 사전 예측 P-13(RL 최소가 P5r4 A3의 8.64 kN보다 높다)은 빗나갔다. 바닥을 줄였는데 최소가 낮아진 비단조는 시점 민감성으로 설명된다. 이 행의 준정적 성분(한 주기 평균 13.6 kN)은 $F_{min}$ 위에 있었다. 하회는 크롤러 이탈 직후 1차 좌우 흔들림–롤 모드(약 1.8 Hz) 진동이 약 7.7 kN을 더 뺀 것이다. 이탈 감속이 이탈 0.15 s 전에야 시작되어(A행·C-8b는 0.43~0.71 s 전) 전방 우측이 최고 속도에 가깝게(19.3 mm/s) 이탈했다. 크롤러 하중 해제와 감속·재가속이 모드 한 주기 안에 겹쳤고, 진동 에너지는 비교 행의 3~10배였다. 둘 중 어느 쪽이 주로 진동을 일으켰는지는 기존 결과로 가르지 못했고 436.9에서 다룬다. 같은 지형의 C-4 4행($R_c$ > 1)도 RL 이탈 직후 하강(4.20~10.81 kN)을 보였다. 이 하한은 운용 범위 안의 제어기 한계로 본다(크롤러 이탈부터 그 다리의 `is_lifted` 판정까지 가벼운 다리를 보호하는 동작이 없는 구간). 설계 보완은 LAS-c 별건으로 넘기고, 개입 실행 2행은 436.8 판정 뒤 별건이다. 짝 C-8b(V0, 크롤러 강성 ×1)의 RL 최소는 11,951.2 N($F_{min}$ + 2.54 kN)이다. 이탈 감속 끝 처리의 재설계는 v5 뒤 과제로 둔다.

- **조립 방법**(판정 후 감사가 규칙대로 조립한 기대 문장과 정규화 일치를 확인, 감사 기록 2): 원판 440행 틀 문장에서 (가) "주성분은 … 옮겨졌다."를 rev24 R24-5 (가) 새 문장으로 바꾸고 (다) 문장을 그 뒤에 덧붙였으며, "모델 상부체는 강체라 이 값은 보수 쪽이고, … 민감하다."를 지웠다. 원판 7.4 멈춤(S-9)이 걸려 "L-5 전체를 사용자 결정 뒤 다시 쓴다"(원판 14절)에 따라, 두 채울 칸(O-C5 VB·V0 문장) 자리에는 사용자 결정 60 (A)로 정한 rev18 R18-5 L-5 문구를 rev24 R24-5 (나)로 고친 것(첫 원문 자리에 (나) 새 문장, 둘째 원문 자리에 사용자 결정 88 문장)을 넣었다. 채울 칸 자리에 R18-5 문구를 넣은 것은 원판 14절과 R18-5 "판정서에 그대로"의 읽기이고, 규칙이 위치를 직접 정하지 않은 유일한 곳이다.
- 숫자 대조(R3f): $m$ 5,869.61684783503 N RL @35.286 s, $F<F_{min}$ 0.158 s·+2 kN 0.212 s(두 경로 같음, 상대 차 R3d 3.3e-11), $R_c$ 0.9523695802182304, 바닥 2.1434°·1.3784°, C-4 RL 4.20~10.81 kN, C-8b 11,951.205749 N(여유 +2,536.6 N). 준정적·진동 분해 값(11.4 / 14.1 / 13.6 kN, 2.8 / 5.6 / 7.7 kN, 1.5~1.8 Hz)은 dynamics-expert 보고 `L5_proposal_report.md`(sha256 `74f74e0d0ee95a9e4b94a049c8ff6ab5f1c8b2f507c5b7e01b8174fe62f6556b`) 4절이 출처이고 두 경로 대조 대상이 아니다(rev24 R24-5). 확신도: ×3·VB 몫 높음(모멘트 닫힘 2.5 %, 모델 1.755 Hz 대 기록 1.759 Hz), ×1·V0 몫 중상(닫힘 33 %, heave 10 % 섞임), 늦은 LAS 시작·최고 속도 이탈과의 연관 중간(5행 중 늦은 행 1개), 가진원 배분 낮음.
- **L-5 근거 표(원판 13절 9항, 시작 조건 밖 행과 $F_{min}$ 하회)**: C-4 4행($R_c$ 1.0764 / 1.0354)의 RL 최소 10,813.8 / 7,653.2 / 8,637.1 / 4,199.4 N(Kc1 켬 / Kc1 끔 / Kc3 켬 / Kc3 끔). **C-4 켬 팔의 같은 하회**: Kc3 켬 8,637.1 N($F_{min}$ − 777.5 N, 35.581 s). 시작 조건 밖인 그 밖 Chrono 행: 없음(경로 2 `p2h_chrono.json` `outside_start_condition_rows` = C-4 4행뿐; O-C5 두 행은 $R_c$ ≤ 1). C-4 행의 $F<F_{min}$ 시간은 CD-9 기록 값에 없고 규칙이 요구하지 않는다.
- rev18 R18-5 93행 "원인 진단은 436.9로 넘긴다"는 rev24로 다음처럼 읽는다: 기전(준정적 성분과 1차 모드 진동 몫)은 사용자 결정 88·91로 정했고, 436.9로 넘기는 것은 가진원 배분(크롤러 하중 해제 대 감속·재가속)과 사용자 결정 88의 두 사실뿐이다.

### 10.2 덧붙임 판의 한계 절 문장 (그대로)

**rev1 RV1-10 i(행정 좌표 명시, `stroke_input_review.md` Q3)**: "제어기 행정 입력 `stroke_m` = 기름 부피 좌표(L1 모터 위치 = L2b `s_ref`, 하네스 `plant.sref`), `stroke_corrected_m` = 피스톤, 두 좌표의 용도 구분은 `c2.py` R1 설계 결정이다."

**rev1 RV1-10 j(행정 끝 한정, `end_stop_cushion_model_review.md` Q2)**: "플랜트에는 피스톤 끝 정지와 신장 끝 쿠션이 없다(쿠션은 판독 678~694.8 mm)."
- 노출 집계(Chrono 행, 기록, 경로 1 집계 1회에 해당하는 이 작성자의 읽기 전용 집계; 등급·멈춤에 쓰지 않음): 입력은 경로 2 묶음 출력의 행 폴더, 각 행 10 Hz 제어 기록 `record.npz`의 `s_ref`(= `stroke_m`)와 `meas.stroke_corrected`(피스톤 판독) 최대값, `result.json`의 `FAULT_STROKE_END` 사건(사건 이름 또는 0보다 큰 사건 수). 비교 허용 10⁻⁹ m. 하네스 줄 집계는 하네스 R4 판정 뒤.

| 묶음 | 행 | s_ref(`stroke_m`) 최대 ≥ 678 mm | ≥ 684.8 mm | 피스톤(`meas.stroke_corrected`) ≥ 678 mm | ≥ 684.8 mm | 기록 없음 행 | `FAULT_STROKE_END` 행 | 묶음 최대 s_ref / 피스톤 [mm] |
|---|---|---|---|---|---|---|---|---|
| C-1 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 644.27 / 638.22 |
| C-2 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 683.03 / 677.55 |
| C-3 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 442.98 / 438.80 |
| C-4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 664.72 / 658.87 |
| C-5 | 35 | 2 | 0 | 0 | 0 | 0 | 0 | 680.99 / 674.67 |
| C-6C7 | 3 | 0 | 0 | 0 | 0 | 3 (P3a_G1_B_V0_FB, P3a_G1_B_VB_FB, P3a_G1_B_VB_prop) | 0 | 기록 없음 / 기록 없음 |
| C-8 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 646.94 / 641.25 |

- C-6·C-7 열린 루프 3행은 제어기가 없어 `record.npz`가 없다(두 좌표 "기록 없음", 3행). 모터 행정 끝값은 4.6절 표(517.5~580.2 mm, `p2h_openloop.json` `s_motor_end_mm`)에 있다.
- 10 Hz 기록 기준이라 1 ms 최대보다 작을 수 있다. 684.8 mm 이상인 행은 두 좌표 모두 0행, `FAULT_STROKE_END`가 있는 행은 0행이다.

**rev3 R3-G1(Chrono 경로 2 재집계)**: "원판 9.1은 C-1~C-5의 경로 2를 시계열에서 다시 계산하는 것으로 정했다. 그러나 C-5의 T4-0·T4·T5·J11 창·J-P3·D2와 PS-c의 E-1~E-4·E-6·E-7은 두 압력 감시기나 사건 판정 논리를 재생해야 값이 나온다. 그래서 이 항목들의 두 경로는 '재계산'에서 '재집계'로 낮아졌다(사용자 결정 2026-11-13). 경로 2는 `result.json`의 항목별 결과에 등급 규칙을 따로 적용해 행 등급만 다시 만들었다. 항목 값 자체는 경로 1과 같은 기록에 기대므로 독립 재계산이 아니다. 해당 항목 목록과 수는 판정서 표 TABLE_REAGG에 있다."
**rev4 R4-A2(rev3 R3-G1·R3-E3 문장에 더함)**: "T4-0·T4·T5, PS-c E-7, 잡음 S-1~S-6과 L1 게이트의 항목 값은 원 규칙이 지정한 같은 판정 도구를 경로 2가 따로 실행해 얻었다. 그래서 두 경로는 같은 계산 함수에 기댄다. 경로 2의 독립성은 도구 실행과 등급 재집계에 있고, 항목 값 계산에는 없다."
- 이 판정서의 사실 주석: 이 문장의 잡음 S-1~S-6과 L1 게이트는 하네스(H-6·H-8) 몫이다. Chrono에서는 T4-0·T4·T5(R3c t45 재생 출력 재사용)와 PS-c E-7(경로 2 도구 실행 `layer` "tool-run (rev4 R4-A2 c)")이 해당한다.
- TABLE_REAGG(Chrono, R3f 경로 2 출력): C-1·C-2·C-3·C-4·C-5·C-8 모두 `reaggregated_items.count` 0(빈 표). R3f 경로 2는 이 항목들을 재계산(`recalculated_judged_items` C-1 48, C-2 27, C-3 20, C-4 4, C-5 213, C-8 14), t45 재생 출력(R3c 재사용), 도구 실행(E-7, rev4 R4-A2 c)으로 냈다. 하네스(H-6·H-8) 한계 공개(rev3 R3-E3)는 하네스 R4 판정 뒤.

**rev6 R6-B9(패드 부상 정의, rev6:131)**: SGS 조건 3 "부상 없음"은 패드 법선 접촉력 진값이 있는 Chrono(SCM `step_series.npz` `scm_pad_normal_N`, L2b `pads.npz` `N`)에서는 rev3 Q-14 정의(패드 법선 ≤ 0인 1 ms 표본 = 부상)로, 진값이 없는 하네스에서는 "참 F_cyl + 로드 무게가 0에 닿지 않음" 근사로 판정한다. 두 엔진의 정의가 다르다.

**rev19 R19-1(이동 중 압력 표본, rev19:28)**: Chrono에는 1 ms 작용 명령 기록이 없으므로 하네스 꼴(1 ms, |valve| > 10⁻⁶ m/s)을 Chrono에 쓰지 않았다. Chrono 427.9 조건 5와 이동 압력은 10 Hz 제어 주기 행(`record.npz` `u_applied`와 같은 행의 F_cyl)으로 판정했다.

**rev18 R18-3**: "R3b 두 경로 보완 항목은 메인 세션과 도메인 검토가 R3 두 경로 출력을 본 뒤 정했다. 보완의 구현과 재판정 값은 경로마다 따로 만들었다. 보완 항목의 선택은 두 경로 출력에서 독립이 아니다."

**rev19 R19-10**: "rev19 정의는 메인 세션과 도메인 검토가 R3b 두 경로의 구현 질문과 해석을 본 뒤 원 규칙 문장과 원 판정 도구에서 정했다. 두 경로는 같은 정의 문장만 받았고, 구현과 값은 경로마다 따로 만들었다. 정의할 곳의 선택은 두 경로에서 독립이 아니다."

**rev20 R20-3**: "rev19 R19-7 조건 (1)은 모듈 수준 상수 정의를 빠뜨려 문장 그대로 대조하면 거짓이었다. rev20 R20-1이 그 이름을 읽는 함수가 모두 기록 전용임을 조건으로 고쳤다. 이 개정은 경로 2의 대조 결과를 본 뒤 했다."

**rev21 R21-6**: "rev21은 R3b 경로 1 재판정이 C-1 L2b 6행에서 R19-5로 멈추고, dynamics-expert가 원인을 rev6 D-29 정의의 퇴화(L2b 스텝 끝 NSC 접촉력에서 첫 ≤ 0 표본이 LEVEL 첫 표본; C-1 L2b 6행: D-29가 LEVEL 시작과 0~1 ms, 그 시각 크롤러 30~75 kN; C-2·C-5 L2b 1 ms 23행: LEVEL 전 1 s 0 비율 55~77 %, D-29 시각 크롤러 30~126 kN)로 진단한 뒤 정했다. rev6 D-29가 빌린 정의는 원래 M2 잘림 스텝의 pre/post 분류용이었다. rev3 R3-G5의 조작 정의(명세 309행 '법선력 합이 0이 된 첫 시각' → 5절 첫 ≤ 0)를 같은 기준 문서(v5 기준 rev6 5절) 안의 t_lift,sus로 바꿨다. 새 정의 t_lift,sus는 결과를 본 뒤 정했고, 명세 3절의 '0'을 0.01 W와 '끝까지 이어짐'으로 읽는다."
- **R21-2 [사실]의 정정(사용자 결정 70, 봉인본은 고치지 않음)**: rev21 R21-2 [사실]의 "5a rocking 9행(C-2 2, C-5 7)"은 진단 JSON 기준 **8행(C-5 6)**이다.
**rev22 R22-5**: "rev22는 R3c 경로 1 판정에서 C-1~C-3 묶음 등급이 나오고 C-5 묶음 등급이 t45 입력 거부로 멈춘 뒤 정했다. 바뀐 것은 경로 1 집계 도구가 t45 재생 출력의 행을 판정 행에 짝짓는 방법(이름 → 입력 폴더 순서와 `dir` 경로·안쪽 이름 대조)과 두 경로 Chrono 판정 도구의 봉인 목록 정의(rev22 추가)뿐이고, T4·T5 판정 로직·문턱·키와 다른 묶음의 규칙은 바뀌지 않았다. 두 경로는 R3d 도구로 C-1~C-8 판정을 다시 내어 R3c 출력과 대조했고, 러너 출력과 t45 재생 출력은 sha256 대조 뒤 재사용했다. 작성 중 t45 재생 출력의 요약 블록을 열람한 사실은 R22-0에 적었다."

**rev23 R23-5**: "rev23은 R3d 통합 전, 경로 1 작성자가 R3c 러너 판정 출력의 행 이름과 `s8_metrics` 키(실행 폴더 안쪽 이름)가 경로 1 집계 도구의 조회 키(판정 행 이름)와 어긋남을 보고한 뒤 정했다. 바뀐 것은 경로 1 집계 도구가 러너 판정 출력의 행과 `s8_metrics`를 판정 행 `dir`의 안쪽 이름으로 찾는 것과 그 대응 기록(대응 대조의 S-11 포함), 두 경로 Chrono 판정 도구 봉인 목록의 rev23 추가뿐이고, 러너 판정 출력, R19-4·R19-5 판정 로직·문턱·키, R22-1 짝짓기, 다른 묶음의 규칙은 바뀌지 않았다. 영향 행은 판정 행 이름과 안쪽 이름이 다른 C-5 9행(LS1·LS4 6행, V0 3행)이고, C-1~C-3 묶음 등급이 바뀌지 않는지는 R3c 출력과의 K-10 대조로 확인한다(결과는 판정서 K-10 표). 작성 중 본 자료는 이름과 키뿐이며 판정 값은 보지 않았다(R23-0)."
- R3d K-10 결과: R3c 대비 C-1~C-3 묶음 등급 같음(rev24 R24-0이 인용한 R3d 결과). R3f에서도 같다(7.6절).

**rev24 R24-5 (원 판정기 직접 실행의 한계)**: "L2b 행의 원 판정기 항목(CD-2 표에서 '원 판정기 셈 그대로'인 항목) 값은 원 규칙의 같은 판정기를 경로 2가 따로 실행해 얻었다. 그래서 두 경로는 그 항목 값의 계산 함수에 함께 기댄다. 경로 2의 독립성은 판정기 실행, 재계산 항목, 셈과 등급 재집계에 있고, '그대로' 항목의 값 계산에는 없다. 재계산 항목(사건 행 판별과 창 등)의 정의를 원 판정기 소스에서 읽어 구현했다면 그 항목도 원 판정기와 같은 정의에 기댄다. 경로 2가 연 원 판정기 소스는 경로 2 판정서의 읽은 것 목록에 있다."

**rev24 R24-5 (rev24 개정)**: "rev24는 R3d 두 경로 Chrono 재판정에서 C-5 묶음 등급이 갈린(경로 1 판정 불가, 경로 2 통과) 뒤 정했다. 원인은 C-5 판정 항목 범위의 정의(rev18 R18-2)가 한 경로에만 넘어간 것과 한 경로의 사건 행 이동 압력 창 미구현이었다. rev24는 두 경로에 같은 문장으로 넘기는 공통 판정 정의(CD-1~CD-11)로 C-5 항목 범위, 원 판정기 항목 덮어쓰기 표, 사건 행 판별과 창, READY 없음 처리, T4·T5 대상 행, 사유 문구, C-4·C-8 기록 상태와 기록 값, K-10 실행 정체성 키, 항목 목록을 정했고, 두 경로는 R3e 도구로 C-1~C-8을 다시 판정했다. 숫자 문턱과 등급 순서는 바뀌지 않았다. 정의를 고른 것은 두 경로 출력과 감사 결과(등급·값 포함), 경로 1 도구의 덮어쓰기 목록을 본 뒤이므로, 정의의 선택은 두 경로 출력에서 독립이 아니다. 구현과 재판정 값은 경로마다 따로 만들었다."
- 이 판정서의 사실 주석: R3e 판정은 실행하지 않았고(폐기), C-1~C-8 재판정은 rev25 뒤 R3f 도구로 했다(3절).

**rev24 R24-5 (사건 행 판별)**: "rev24의 C-5 사건 행 판별(바닥 사건 4행, 빠른 침하 2행)은 R3d 출력과 감사 결과를 본 뒤 정했다. 근거는 명세 220.6 ①·U-S8-43(침하 속도가 $v_{max}$를 넘는 침하만 바닥 사건으로 보고, G4 5.75 mm/s는 사건 없는 규칙)과 J-5('비사건 사례의 항목 4는 바꾸지 않는다'), 그리고 원 판정기의 같은 갈래다. R3d에서 한 경로가 `event_t_s`가 있는 13행을 사건 행으로 본 것은 규칙 문장에 없는 구현 기준이었다. 이 판별로 `E_G4_` 7행의 이동 압력은 창 없는 ≤ 180 bar 규칙으로 판정된다. 판별은 행별 압력 값으로 정하지 않았다. 작성자는 감사 리포트로 13행 전체의 이동 압력 범위(136.4~189.1 bar)와 G1R_FS24 두 행 값을 읽었고, `E_G4_` 행별 값은 보지 않았다. 판별의 근거는 명세 220.6 ①, J-5, 원 판정기 갈래이고, 판정 결과가 미달이어도 판별은 바꾸지 않는다."

**rev24 R24-5 (436.9 입력, 사용자 결정 88)**: "C-2 PS-c c-slow 행의 E-5 실패는 탐침 소성 침하로 재레벨이 두 번 일어난 것이고 제어기 오동작이 아니다." "C-4 P3-5 표본 0은 강체 바닥(rigid_base)이라 구조적으로 해당 없음이다."

**rev25 R25-5 (결과를 본 뒤 정한 정의)**: "rev25는 R3e 판정 출력을 보기 전, R3e 판정 전 감사가 두 경로 구현과 rev24 공통 블록을 대조한 뒤 정했다. 바뀐 것은 C-5 SCM 행 P3-6을 판정 항목으로 하고 한계를 명세 421.1 표(경사 120 s / 평지·패드 B·후방 두 패드 J1·J2·S1 100 s / 그 밖 평지 90 s)로 적은 것, C1 D8 재계산에 원 판정기와 같은 사건 시각 절단을 넣은 것, CD-11 대응 규약(등급 항목·관문·기록)과 조항 ID 대응, C-8 기록 값 목록(다리별 두 계열 시각, O-C5 SCM 행의 D8·G6), 공통 블록 sha 기록 의무다. rev24 범위 안의 구현 결함 네 건(원 판정기 묶음 항목 셈, P3-7 문턱의 질량 배율, K-10 실행 정체성 키, C-4 빈 사유 멈춤)은 새 정의가 아니라 rev24 문장대로 고친 것이다. 숫자 문턱과 등급 순서는 바뀌지 않았다. 이 작성자는 rev24 때 R3d 두 경로 출력의 등급·값을 보았으므로, P3-6을 판정 항목으로 둔 결정(사용자 결정 98의 1)이 C-5 등급을 미달 쪽으로 움직일 수 있음을 알고 이 정의를 적었다. 결정의 근거는 사용자 결정 90의 1(CD-5 'P3-6 READY 도달 미달'), 명세 15948행('Chrono P3-6(100 s)은 판정 행 그대로'), 원 판정기 P3b 블록의 판정이다. 명세 421.1 첫 문장('P3-6은 기록 행이고 판정 수치는 가정이다')과 다른 점은 이 결정으로 정했다."
- 이 판정서의 사실 주석: R3f C-5 미달 7행 가운데 4행은 P3-6도 미달이다. 7행 모두 P3-7 미달이므로 P3-6 판정 여부와 관계없이 C-5 묶음 등급은 미달이다.

**rev25 R25-5 (독립성)**: "경로 1은 빠른 침하 W와 T_3에 원 판정기의 함수와 상수를 읽어 쓴다. 그래서 그 재계산 값은 원 판정기 정의에 기댄다. 경로 2는 P3-7 재구성 정의를 고르려고 실제 SCM 23행 기록에서 시각 재현의 참·거짓만 보았고, P3-7 값과 판정은 보지 않았다. P3-6 한계는 두 경로 모두 원 판정기 P3b 블록과 같은 정의를 쓴다. C-3 G6 대응과 READY 없음 처리는 두 경로가 같은 원 G6 판정기(`r76_g6_chrono_judge.py`) 정의에 기댄다. 원 G6 판정기는 C-3의 P3-7을 기록으로 두지만, 이 판은 d1 선정 규칙 11절('P3 + G6-1~G6-7')과 앞서 두 경로가 쓰던 구현을 근거로 C-3 P3-7을 등급 항목으로 둔다."

**rev25 R25-5 (G6 대응과 원 G6 판정기의 차이)**: "C-3 G6 행의 관문은 원 G6 판정기(`r76_g6_chrono_judge.py`)의 대응(G6-1~G6-5 = P3-1~P3-5, G6-6 = FAULT 없음·READY 도달, G6-7 = P3-8, 따로 READY ≤ 120 s)대로 펼쳤다. READY가 없는 C-3 행에서 원 G6 판정기는 G6-4·G6-5·G6-6·READY ≤ 120 s를 판정 불가로 실패로 세고 G6-1을 이탈 확인부터 끝까지의 크롤러 힘 0으로 대신한다. 이 판은 G6-4·G6-5를 CD-5대로 해당 없음으로, G6-1을 CD-5 P3-1 줄대로 두고, 행 등급은 G6-6·READY ≤ 120 s 미달로 정한다. READY ≤ 120 s 비교에는 원판 7.6의 허용 10⁻⁹ s를 쓴다. 지금 R3d 자료에는 READY가 없는 C-3 행이 없다."

**rev25 R25-5 (O-C5 rigid_base P3-5)**: "사용자 결정 88의 'rigid_base 행 P3-5는 구조적으로 해당 없음'을 rigid_base 행 전체(C-4와 O-C5 두 행)로 넓혔다. C-8 기록 상태는 사용자 결정 89대로 기록 완료 판단을 따른다."

**rev25 R25-5 (C-4 기록 값과 원판 5.2의 차이)**: "C-4 기록 값(CD-9)에는 D8·G6 값을 넣지 않고 rev24 정의를 그대로 둔다. 원판 5.2 C-4 행의 '기록, D8·G6'과 다르다. C-4 행의 D8·G6 기록은 436.9로 넘긴다."

**rev25 R25-5 (9.2)**: 이 판은 R3e 판정 출력 없이, 두 경로 구현 보고와 판정 전 감사(두 경로의 코드 위치와 구조를 담음)를 본 뒤 정했다(R25-0). 공통 블록으로 두 경로에 보완 항목이 넘어가므로 결함 사실의 전달은 이 공개로 다룬다(rev18 R18-3, 사용자 결정 61 선례). 이 판의 정의를 쓰려고 경로 2 코드를 열지 않았다.

- rev15~rev21의 한계·공개 문장(R16-15a 하네스 로드 판독 모형은 하네스 몫, R19-10, R20-3, R21-6 등)은 부록 D에 원문을 실었다. 그 가운데 하네스 묶음에 관한 문장은 하네스 R4 판정서 절에서 다시 적는다.

### 10.3 판정 뒤 정한 처리의 공개 (사용자 결정 102·107·108)

- **결정 107 (2)**: 경로 2 C-5 묶음 출력의 CD-7 멈춤(H-9 빈 사유 11행)은 판정 뒤 도구를 고치지 않고, 판정서에 사유 "H-9: M2 끔이라 해당 없음, CD-1 목록 밖 기록 항목"을 적어 처리했다. 경로 2 C-5 등급은 행 등급으로 셈한 미달(28 / 7)이다. 판정 후 감사는 원인을 경로 2 도구의 표시 결함(CD-1 닫힌 목록 밖 기록 항목에도 CD-7이 걸린다는 점이 문장에 명시되지 않음)으로 분류했고, 합성 시험에 M2 끔 행의 H-9 사유 검사가 없어 판정 전 감사에서 놓쳤다.
- **결정 107 (3)**: C-5 S9SL 2행은 토양 가드 정지 행으로 보고 427.9 분기를 적용했다(경로 2 읽기). 경로 1의 미달(P3-1·P3-6·FAULT0)은 정의 차이로 공개한다. **결정 90 때의 "S9SL 미달" 문구는 427.9 분기를 모르고 쓴 추정이었다.**
- **결정 107 (1)**: 실행 전 허용 키 목록에 키를 적지 않은 범주 안 차이 네 곳(7.6절)을 허용했다.
- **결정 108**: CD-11 한쪽 등급 항목 123건과 J11 표기 차이 35건, C-4 목록 경로 1 없음, C-2 S 행 P3-6 잠복 차이는 공개만 하고 도구는 고치지 않았다(rev26/436.9 후보).
- **결정 102**: J-P3 위반은 멈춤으로 읽는다. R3f 두 경로 모두 위반 0행이라 실제 멈춤은 없었다.
- **결정 93(사실 정정)**: 사용자 결정 92(C-5 사건 행 6행)를 물을 때 메인 세션은 "E_G4 행 값은 아직 보지 않았다"고 했으나, rev24 작성자는 감사 리포트로 사건 후보 13행 전체의 이동 압력 범위 136.4~189.1 bar와 G1R_FS24 두 행 값을 읽었다. 메인 세션이 사용자에게 정정해 알렸고, 사용자는 사건 행 6행을 유지하고 공개 문장을 사실대로 쓰기로 했다(10.2절 R24-5 사건 행 판별 문장).
- **결정 62(경로 2 작성자 교체)**: R3b 단계에서 원 경로 2 작성자를 맥락 소실로 부를 수 없어 새 작성자로 바꿨다(7.1절). 새 작성자는 경로 1 내용을 받지 않았고 rev18 R18-3 정의 문장과 경로 2 README만 받았다.
- **결정 70(인계 파일 손 편집)**: rev21 경로 1 인계 파일 `rev21_definitions_handoff.md`(`e9744fac…`)는 R21-1 안의 결과 문장 1개를 메인 세션이 지운 판이다. R21-2 [사실] 9행 → 8행 정정은 10.2절.
- **결정 83(R3d 공개 2건)**: ① 경로 1 작성자가 rev22 봉인 뒤 R3c 러너 판정 출력의 이름을 열람했다(rev23 R23-0에도 적힘: `runner_judge\C5_E_G4_Fs8_LS1.verify_S8C.json`의 러너 행 이름과 `s8_metrics` 키). ② S10 커밋 본문과 rev22 `.sha256` 설명 줄의 경로 1 구조(키·함수 이름)가 경로 2 브랜치에서 보였다(S10이 두 도구 브랜치에 병합되어서). 경로 2 작성자가 S10 본문·rev22 `.sha256` 설명 줄을 실제로 읽었는지는 이 판정서 자료로 확인하지 않았다(rev23 단계 경로 2 보고는 "경로 1 코드·출력, S11 커밋 본문, 초안은 열지 않음"이라고 적었다).
- **결정 41**: C-7b `v5_hydraulics` 부재는 정상(V0 해당 없음, 4.6절). C-4 끔 팔 `liftoff_approach_slow` 결측은 R7-4 허용 결측(2.4절).
- **결정 34(`probe_not_judgement` 공개)**: 메모리 결정 기록 34번 줄 원문은 "R2 실행 전 감사: … probe_not_judgement 공개"이다. `judge_b9f5707\chrono_path2\probe_not_judgement\`(5파일: `make_probe.py`, `p2_4368_probe.py` 133,640 B, `run_probe.ps1`, `p2h_chrono.json`, `p2h_seal.json`)는 R2 첫 판정 단계에서 추적되는 경로 2 도구(`p2_4368.py`)를 고치지 않고, `make_probe.py`가 두 수정(① `criteria_id` C-7a/C-7b 열린 루프 행 인식, rev4:82 ② O-C5 본 행 블록을 OC5PROBE 행에 적용하지 않음, 원판 5.4)을 넣어 만든 scratch 사본 `p2_4368_probe.py`로 Chrono 판정(C1·C3·C4·C5×3·C6C7·OC5PROBE 배치)을 시험 실행한 출력이다(`run_probe.ps1` 1행 "Path-2 Chrono judgement (main mode) of the 436.8 main bundles at R2 (b9f5707)"). **판정 근거가 아니다.** 이 사본 실행은 결정 41의 "경로 2 멈춤(C-7a·b 열린 루프 미인식, probe에 O-C5 본 행 적용)"과 이어지며, 결정 41("도구 결함은 worktree에서 고치고 하네스 뒤 병합(R3)")에 따라 두 결함은 R3 판정 도구 쪽에서 고치기로 했다. 그 수정이 R3 커밋의 어느 덩어리인지는 이 판정서에서 대조하지 않았다.

## 11. 436.9 입력과 rev26 후보

| # | 내용 | 출처 |
|---|---|---|
| 436.9-1 | C-2 PS-c c-slow E-5 실패: 탐침 소성 침하로 재레벨 두 번, 제어기 오동작 아님(등급 미달 유지) | 사용자 결정 88, rev24 R24-5 |
| 436.9-2 | C-4 P3-5 표본 0: rigid_base라 구조적으로 해당 없음 | 같음 |
| 436.9-3 | C-8a 가진원 배분(크롤러 하중 해제 대 감속·재가속), L-5 | rev24 R24-5 |
| 436.9-4 | C-4 행의 D8·G6 기록 | 사용자 결정 99 |
| LAS-c 별건 | 이탈~`is_lifted` 사이 가벼운 다리 보호 공백의 설계, 개입 실행 2행 | 사용자 결정 88 |
| rev26 후보 1 | 경로 1 CD-11 목록의 기록 행 분류(K1·K2)와 비대상 행 T4·T5 해당 없음(K3) | 사용자 결정 108 (1) |
| rev26 후보 2 | J11 판정 표기 통일(K5), C-4 CD-11 목록 요구 범위, C-2 S 행(427.9 분기 아님) P3-6 역할(정의 차이 d) | 사용자 결정 108 (2) |
| rev26 후보 3 | 427.9 분기 적용 범위 문장(S-01~S-04 대 토양 가드 정지 행 전체)과 CD-7의 CD-1 목록 밖 기록 항목 적용 | 결정 107 (2)·(3) |
| 원인 확인 | N3 E-5 행정 좌표(517.33 대 512.63 mm) | python-expert, R3d부터 미완 |
| 도구 후보 | `kr_cd11`(두 경로 CD-11 목록 대응 도구) | K-R 위임 필요(python-expert) |

## 12. 확인 필요

- 닫힌 것: 결정 날짜, R3f 배치, `c3f4cad` 뒤 재감사 없음과 대신 한 확인, 시험 413 대 412, 비교기 판, 진단 원문, 경로 1 R3b·rev19·R3c "읽은 것"(앞 메인 답), K-R 표 P3-1 기재(판정 후 감사: 두 경로 모두 `flag`, K-R 표기 오류), 실행 $R_c$ 표와 C-4 $F<F_{min}$ 시간(감사: `outside_start_condition_rows` = C-4 4행, 시간은 규칙에 없음), L-5 조립(감사 기록 2), J_P 처리(결정 110 (1)), 대체된 앞 단계 기록(결정 110 (2), 3.1절), R2 실행 전 감사·경로 1 R3 "읽은 것"(결정 110 (3), 9·7.1절), P-7·P-11·P-11b(결정 110 (4); 하네스 판정서 6절에서 결정 113·114의 9로 계산, 맞음), RV1-10·G-S sha·`log_errors`(10.2·9절), rev6 R6-A 공개 수(7.3a절, 대안 377 계산은 출력에 없음), rev4 R4-A2 한계 문장(10.2절), 결정 34 설명 정정(10.3절), R3 view 입력 고정(2.3·3.1절), 커밋 대상 출력 목록(사용자 결정 111, 9.2절).
- 남은 것:

1. N3 행정 좌표(517.33 대 512.63 mm): 원판 9.2대로 공개하고 python-expert 원인 확인으로 넘긴 상태(커밋 가능, 판정 후 감사 분류).
2. integrity-checker Low 3건(경로 1 README 191행 sha 표 출처에 `c3f4cad` 없음, `TOOL_VERSION` v7 그대로, README 시험 개수 '옛 값' 기준 불일치)의 처리 시점(rev26 또는 다음 도구 커밋).
3. rev6:85 둘째 구절("그 행에서 최종 LOC + 1 s로 계산했다면 강등 결과가 달라졌는지"): LOC 취소 6행의 대안 377 판정은 두 경로 출력에 없다(7.3a절). 이 판정서에서 계산하지 않았다.
4. 부록 E에서 "확인 필요"로 남은 항목(머리말 집계; 재감사 기록 4: 대부분 하네스 몫·대체·이미 반영, 커밋을 막지 않음).

## 부록 A. 경로 1 출력 파일 sha256 (64개, `judge_8a0c843\chrono_path1\`, K-R 감사자 고정, `r3f_kr_cross_path.md` 부록 A 그대로)

```
e015509e9d191859a979c03e9e52584f30a8764594601c470d70c29525eaef8c allowed_keys_path1.md
30c0da5c54ea0c84febbdb2a82a8f3db3c75a9137103e5f7f846a9db75e106c4 bundle_C1.json
e04a0e5d9b9f1b73321d5ac6f8fa85b847bc6bea70b3c20c32687bbf9a0e17f8 bundle_C1.stdout.txt
0dd4129b6982724469376d67117128b3d8f5f77ed7615a6e90ae40f0fab72693 bundle_C2.json
ff82c82a125fc967c1109f8b37f9b53102d30de2812b271d58f4cc505e0c572e bundle_C2.stdout.txt
b10bb25ddf64433f65f684d6c953ccae94643c9ee0f50c54e75a31dcd4d53314 bundle_C3.json
b61ac3df8a22a6f1c61987ed28446c6997d2e3fc2bc6648c4de0213f0e77d924 bundle_C3.stdout.txt
6610eb137afee5b68aa8242148b51c3ef8a05ab69a8f3b834a751e27bbd5d78b bundle_C4.json
433e92cf0c01cd15d62c647bc30f18264f7e2d3d3e9919bec7475a95acac8f96 bundle_C4.stdout.txt
8dca46782e130aa2b373bf033d12f6b0d24de55448c4679a00ca4f7d2304bd30 bundle_C5.json
637c6c3fe65d679e57107058ecd4ffc5798059fec5e2c8067204b389af2adde6 bundle_C5.stdout.txt
66e5bf3cb0e4edcb32313c5a64d06176ef8e4bb600bac3914c917d561f48bff5 bundle_C6C7.json
30b9946cc8fe03949fe6eac864083a6f6e5090aba936995a9170cc6fc7675629 bundle_C6C7.stdout.txt
d8a7b0668b82b264d36cac65b57b9c0f85b08e8c20005faf4dc158ab4fc54df5 bundle_OC5.json
b5d3e6d64237c97a5544d54fa878fb52cd07a4c27974987c88ccad58d12ac423 bundle_OC5.stdout.txt
5496eff433005a30e44f35501b9c2eb86eeee3fbd07f3b50fc71b04a37a2ccf0 bundle_summary.py
a9d526d1d2e9ff5716a5d32935e71a09e09ea669f83420a3fd007191b8c1ab26 compare_r3d.json
0e8fad4a063437011eda2dcd7ffc646c8b565b0dcc3be8ee9ed804e2006eb53b compare_r3d.py
ad3480afd868635ed060a7007c779de1a3e79e5c858acc28180063bb23a582c4 compare_r3d.stdout.txt
3f04ef86574c59562f8865f64b995e86821cc88ebee79518fe2ea088fc1d908e exit_codes.json
abc60a18315bf54834fd3168b0671269fb166666c1797c1bda12120798c758dd fmin_C-8a.json
c579ba149651f3fd3df484c10d470b3ef1e7997f714221fbe877a26c29a721be fmin_C-8a.stdout.txt
0b15c5e2f8ccf35ade4a2d12f582aeea0090a0ab3bb1bfd881ac33498fa691f1 fmin_C-8b.json
220ef4c71d0e2597b2669caa8fefe44f4b24821bc9337011c5ceec3c2184aec5 fmin_C-8b.stdout.txt
ffd6638697b8bf9a29bf6485419e8de9e795bdf67e47e2165d00cf47e74ecfdd judge_C1.json
08677d26cb58d6415fd09405432e03d1e7f6ce8258edc8b91443884e2f37b1c5 judge_C1.stdout.txt
5d0feed8f81d921d23da9e3401f852709df61bfddc47848b95ee974d24efa6d6 judge_C2.json
9102a4752beb7cfa7016d11766222366818efcd789afb9c89becc6884c677bc6 judge_C2.stdout.txt
26d0aa6ccff1ccbea139accc914250ea5f6b42c9fe67f2e006826804deb65bbc judge_C3.json
b1baaa07a214a9e60571ec2f1e4a8a9028ea0eb98695206b93510777fb547acf judge_C3.stdout.txt
92e34cd1d51bce338e4527c8412cee00ec403ce77ff62cc673434bda45e92f1d judge_C4.json
084b758f22748a5ce3381b5868d2151c75aefa04d23cba05ddddfdc6e1d7158f judge_C4.stdout.txt
d952f07563ebaac34dc4a1ac40f3ac3d786b5149317c755ff7d00f94d62b6ce5 judge_C5.json
00111636c0e0eeb6229547338156818589163acdf947f0b7a30d5319b0e90de2 judge_C5.stdout.txt
4aa7e3d52a61df0ce9af5d2279617bda887b29ed8916034fb95a7cf9127fc2c7 judge_C6C7.json
0f3555bcd9ed91be48d3da11f2aea3a76e5b4d4171d85f1df2059636453cf9d2 judge_C6C7.stdout.txt
0ce2dc13bbcb43229fcc3ea413db602121378f05560c53efaf2e8886449e51a3 judge_OC5.json
7becba6174acde511338b3923f506cb8d7ef20e62d110011450a2a093999a614 judge_OC5.stdout.txt
0665d4d125f43bc9f6f0b9b8bba4bf8de702f3a1be096f0a2dee2df606be06f4 judge_OC5PROBE.json
73d93b94b72a15fc574c534bb48a8a97b67ac79eac81c4e83e6d80d9f8a9e4f4 judge_OC5PROBE.stdout.txt
9b69c3590842deb293dc440ec812f1e4751dfa3db46f40a8e75042a920db9ac7 k1_class_view.stdout.txt
3d174e1083d811e414fb050c042f5f5492c4ce082b54eb3619a701ed31cfa876 k1_classification_7_2_view.json
17329569ece3d1d81150e3c1e425756b6ecd9d455d698cfcb0631f8a203f0fa3 oc5_C-8a.json
8b3899c9d18e360d6d928b9de47273ce5009685b5602d1abc4140c02a34a811d oc5_C-8a.stdout.txt
ca05f8dae559ab1fea2855e202a21fb33db54d0fab289977ec5311dc371854de oc5_C-8b.json
64f72ab1c255396958efae4ba5164e5d43e5e28782f6f366b1626187a539069c oc5_C-8b.stdout.txt
cfd9750606984c54992af0eb8d905002178f341d43a526929c078930b176319b r3c_check_after.json
5824f3bed1f6418b7390a82124d24de0878089a017e8702c3d72e02b6ed293c8 r3c_check_after.stdout.txt
cfd9750606984c54992af0eb8d905002178f341d43a526929c078930b176319b r3c_check_before.json
5824f3bed1f6418b7390a82124d24de0878089a017e8702c3d72e02b6ed293c8 r3c_check_before.stdout.txt
974100701a1d349a67914aae4ffa6f97390c740e38ce594300469e50f9447762 r3d_check_after.json
a0ab8e4c0da84b18e346ff48150137fc55baf75b93e715c68a2d8984c0991849 r3d_check_after.stdout.txt
974100701a1d349a67914aae4ffa6f97390c740e38ce594300469e50f9447762 r3d_check_before.json
a0ab8e4c0da84b18e346ff48150137fc55baf75b93e715c68a2d8984c0991849 r3d_check_before.stdout.txt
058993f34778e69516d68c76d967f269f3e01fe0f4ba57495ae558d4f06d0256 record_check_chrono_view.json
ac6a5c7e8908a967e3d21efeae98a7ba605468f3553796f36c22bacc9698d9bd record_check_view.stdout.txt
faf01f0e2451550685957e1b41b61551889534094b0b368a13d84877fc8bbbfc run_path1_r3f.ps1
7e8eb0906bf85cf314afe0eb7e67a5ed718431d8ffe2b3b3103770e6cf4de563 seals_bundle_grade.stdout.txt
7e8eb0906bf85cf314afe0eb7e67a5ed718431d8ffe2b3b3103770e6cf4de563 seals_rows_judge.stdout.txt
b7165b01fd70153f6caafee26114869e67ed4fa8a75c484e4f61d0df9660cf4d sums_check.py
5005079a944e5a143ed9652f4dad300f03d4569480c5c62c4c89b7a337c50a29 td_basis.py
f26e1afa7be01b099384d4f77307eff5121e9982a8114a33b04b0fdb6311c404 view_check.json
73bb02c27bdf30f85d5d9bf997565c0ed954270e9c4b046dc7d23223a22c307a view_check.py
da402eae942b67bd649e7f40568d664ab0ca519450b64976e5503d393246c5af view_check.stdout.txt
```

## 부록 B. 덩어리 머리 목록 (`git diff -U0`, 감싸는 이름은 git 문맥 표시 앞 50자)

- 만든 명령(읽기 전용): `git diff --name-only`, `git diff --shortstat`, `git diff -U0 <a> <b> -- <파일>`의 `@@` 줄.

### 0220671..8a0c843 files=24 stat:
24 files changed, 5177 insertions(+), 151 deletions(-)
- `.gitattributes` (1 hunks): `-138,0 +139,6`
- `04_scripts/02_chrono/chrono_bundle_grade_4368.py` (67 hunks): `-26 +26,20` it runs no simulation and no other judge:; `-40 +59,4` it runs no simulation and no other judge:; `-55 +77,3` CLI (Chrono-dev or python-dev, no simulation)::; `-59,3 +83,3` Exit codes: 0 done without a stop; 1 a stop (S-15,; `-87,2 +111,3` InputError = rows_judge.InputError; `-92 +117,6` RULES_TEXT = ("rules rev18 R18-2 (bundle grades of; `-97,4 +127,5` RULES_TEXT = ("rules rev18 R18-2 (bundle grades of; `-103 +134` GRADED_BUNDLES = ("C-1", "C-2", "C-3", "C-5"); `-126,0 +158,7` D1-PSC base = the event's timing base); ``judge ..; `-128,3 +166,5` RIGID_OVERRIDES = (; `-132,2 +172,15` RIGID_OVERRIDES = (; `-382,4 +435,10` def runner_items(doc: dict[str, Any], inner: str |; `-388,0 +448,10` def runner_items(doc: dict[str, Any], inner: str |; `-451,3 +520,4` def runner_t_lift_items(items: list[dict[str, Any]; `-456 +526` def recomputed_verdict(judge_key: str, runner_name; `-459,2 +529,4` def recomputed_verdict(judge_key: str, runner_name; `-462,2 +534,2` def recomputed_verdict(judge_key: str, runner_name; `-465 +537,4` def recomputed_verdict(judge_key: str, runner_name; `-468,2 +543,16` def recomputed_verdict(judge_key: str, runner_name; `-474 +563,2` def apply_rigid_overrides(items: list[dict[str, An; `-475,0 +566` def apply_rigid_overrides(items: list[dict[str, An; `-477,2 +568,2` def apply_rigid_overrides(items: list[dict[str, An; `-480,2 +571,3` def apply_rigid_overrides(items: list[dict[str, An; `-488 +580,2` def _override(runner_item: dict[str, Any], verdict; `-495,2 +588,6` def _override(runner_item: dict[str, Any], verdict; `-531 +628` def apply_d8_overrides(items: list[dict[str, Any]]; `-535,0 +633` def apply_d8_overrides(items: list[dict[str, Any]]; `-540,0 +639,2` def apply_d8_overrides(items: list[dict[str, Any]]; `-608,0 +709,2` class RigidResult:; `-683,0 +786` def rigid_row(row: RowInput, bundle: str, runner_d; `-714,0 +818,3` def rigid_row(row: RowInput, bundle: str, runner_d; `-715,0 +822,2` def rigid_row(row: RowInput, bundle: str, runner_d; `-718,0 +827,26` def rigid_row(row: RowInput, bundle: str, runner_d; `-731 +865,39` def _check_runner_batch(doc: dict[str, Any], row: ; `-733 +905,8` def p3_items(p3b: dict[str, Any], judged_items: di; `-738,0 +918` def p3_items(p3b: dict[str, Any], judged_items: di; `-740 +920` def p3_items(p3b: dict[str, Any], judged_items: di; `-742,8 +922,10` def p3_items(p3b: dict[str, Any], judged_items: di; `-751 +933` def p3_items(p3b: dict[str, Any], judged_items: di; `-754,0 +937,60` def p3_items(p3b: dict[str, Any], judged_items: di; `-759 +1001,4` def _verdict_word(word: Any) -> str:; `-762 +1007,11` def _p31_item(checks: dict[str, Any], recontact: d; `-763,0 +1019` def _p31_item(checks: dict[str, Any], recontact: d; `-769 +1025` def _p31_item(checks: dict[str, Any], recontact: d; `-775,0 +1032` def _p32_item(checks: dict[str, Any], p32: dict[st; `-781,0 +1039` def _p32_item(checks: dict[str, Any], p32: dict[st; `-783 +1041` def _p32_item(checks: dict[str, Any], p32: dict[st; `-789 +1047,2` def _p39_item(checks: dict[str, Any]) -> dict[str,; `-793 +1052` def _p39_item(checks: dict[str, Any]) -> dict[str,; `-794,0 +1054` def _fault_verdict(p38: dict[str, Any]) -> str:; `-796,2 +1056,3` def _fault_verdict(p38: dict[str, Any]) -> str:; `-924,2 +1185,2` def soil_event_items(result: dict[str, Any]) -> li; `-1169,0 +1431,2` def grade_row(row: RowInput, bundle: str, runner_d; `-1198,0 +1462,201` def grade_row(row: RowInput, bundle: str, runner_d; `-1201,0 +1666,103` def grade_row(row: RowInput, bundle: str, runner_d; `-1222 +1789,2` def _scm_items(row: RowInput, bundle: str, judged_; `-1227 +1795,2` def _scm_items(row: RowInput, bundle: str, judged_; `-1242 +1811,3` def _scm_items(row: RowInput, bundle: str, judged_; `-1256,0 +1828,6` def _g6_items(row: RowInput, p3: list[dict[str, An; `-1268 +1845` def _row_grade(row: RowInput, items: list[dict[str; `-1492,0 +2070,2` def oc5_row(row: RowInput, oc5: dict[str, tuple[di; `-1494,0 +2074,205` def oc5_row(row: RowInput, oc5: dict[str, tuple[di; `-1608,0 +2393,2` def _graded_bundle(doc: dict[str, Any], bundle: st; `-1613,0 +2400,2` def _graded_bundle(doc: dict[str, Any], bundle: st; `-1617,0 +2406,43` def _graded_bundle(doc: dict[str, Any], bundle: st; `-1636,0 +2468,4` def _record_bundle(doc: dict[str, Any], bundle: st; `-1672 +2507,3` def build_parser() -> argparse.ArgumentParser:
- `04_scripts/02_chrono/chrono_rows_judge_4368.py` (19 hunks): `-24,0 +25,6` rules rev6 R6-A D-26 .. D-39):; `-32 +38` rules rev6 R6-A D-26 .. D-39):; `-58 +64,2` CLI (Chrono-dev, no simulation)::; `-124,0 +132,4` RULES_SEALS = {; `-126,3 +137,3` RULES_SEALS = {; `-130 +141,2` RULES_DESCRIPTION = ("v5_resume_4368_rules.md + re; `-132 +144,2` RULES_DESCRIPTION = ("v5_resume_4368_rules.md + re; `-164,0 +178,24` MOVING_EPS_M_S = 1e-9; `-649,0 +687,216` def moving_pressure(rec: dict[str, np.ndarray] | N; `-734 +987,3` def ready_items(phases: list[tuple[float, str]], t; `-739,3 +994,8` def ready_items(phases: list[tuple[float, str]], t; `-835,2 +1095,2` def judge_scm(row: dict[str, Any], rid: str | None; `-871,0 +1132` def g6_grade(p3b, t, cn, f_after, rc, p32, p38, re; `-878 +1139` def g6_grade(p3b, t, cn, f_after, rc, p32, p38, re; `-883,2 +1144,20` def g6_grade(p3b, t, cn, f_after, rc, p32, p38, re; `-1005 +1284,3` def sustained_lift_10hz(row: dict[str, Any]) -> di; `-1009,2 +1290,5` def judge_rigid(row: dict[str, Any], params: dict[; `-1852 +2136,2` def cmd_judge(args) -> tuple[int, dict[str, Any]]:; `-1934,0 +2220,3` def build_parser() -> argparse.ArgumentParser:
- `04_scripts/02_chrono/chrono_rows_judge_4368_README.md` (14 hunks): `-99 +99` python -I -X utf8 04_scripts/02_chrono/chrono_rows; `-120,0 +121,9` python -I -X utf8 04_scripts/02_chrono/chrono_rows; `-123 +132` python -I -X utf8 04_scripts/02_chrono/chrono_rows; `-125 +134` python -I -X utf8 04_scripts/02_chrono/chrono_rows; `-127 +136` python -I -X utf8 04_scripts/02_chrono/chrono_rows; `-137 +146,2` python -I -B -X utf8 04_scripts/02_chrono/chrono_b; `-141 +151` python -I -B -X utf8 04_scripts/02_chrono/chrono_b; `-145 +155` python -I -B -X utf8 04_scripts/02_chrono/chrono_b; `-148 +158` python -I -B -X utf8 04_scripts/02_chrono/chrono_b; `-150 +160,3` python -I -B -X utf8 04_scripts/02_chrono/chrono_b; `-161 +173,3` python -I -B -X utf8 04_scripts/02_chrono/chrono_b; `-177 +191` python -I -B -X utf8 04_scripts/02_chrono/chrono_b; `-181,2 +195,2` python -I -B -X utf8 04_scripts/02_chrono/chrono_b; `-184 +198` python -I -B -X utf8 04_scripts/02_chrono/chrono_b
- `05_tests/unit/test_chrono_bundle_grade_4368.py` (19 hunks): `-80,0 +81,2` def write_scm_series(folder: Path, *, lift_after_l; `-82 +84` def write_scm_series(folder: Path, *, lift_after_l; `-183,0 +186,5` def write_cases_script(mod, tmp_path: Path, cases:; `-188,2 +195` def runner_pass_rows() -> list[dict[str, Any]]:; `-613,2 +619,11` def test_openloop_record_complete_and_incomplete(m; `-617 +632` def oc5_files(tmp_path: Path, b: Bundle, case: str; `-622 +637,2` def oc5_files(tmp_path: Path, b: Bundle, case: str; `-627 +643,11` def oc5_files(tmp_path: Path, b: Bundle, case: str; `-629,2 +655,9` def test_c8_record_with_s9_handling(mod, tmp_path); `-633 +666` def test_c8_record_with_s9_handling(mod, tmp_path); `-637,0 +671,19` def test_c8_record_with_s9_handling(mod, tmp_path); `-641,3 +693` def test_c8_s9_on_v0_stops_and_missing_fmin(mod, t; `-646 +696` def test_c8_s9_on_v0_stops_and_missing_fmin(mod, t; `-648,0 +699,2` def test_c8_s9_on_v0_stops_and_missing_fmin(mod, t; `-668,0 +721,6` def test_seals_command(mod, capsys):; `-1221 +1279,2` def test_r23_same_names_keep_the_rev22_output(mod,; `-1228,3 +1287,7` def test_r23_same_names_keep_the_rev22_output(mod,; `-1233,0 +1297,14` def test_r23_same_names_keep_the_rev22_output(mod,; `-1378,0 +1456,352` def test_r23_checks_not_applied_are_null(mod, tmp_
- `05_tests/unit/test_chrono_rows_judge_4368.py` (5 hunks): `-606,0 +607,2` REV16_18_SHA256 = {; `-608 +610` REV16_18_SHA256 = {; `-613 +615` def test_rev16_to_rev18_in_the_seal_list(mod):; `-616 +618` def test_rev16_to_rev18_in_the_seal_list(mod):; `-822,0 +825,183` def test_gs_batch_082117_execution_path(mod, tmp_p
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/README.md` (3 hunks): `-4 +4`; `-59 +59,3` $d = "<repo>\06_analysis\02_control\verif_matrix\v; `-125,0 +128,11` $d = "<repo>\06_analysis\02_control\verif_matrix\v
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_b_c1.py` (3 hunks): `-2,2 +2,4`; `-4,0 +7`; `-22,0 +26` def judge_row(row, case, kind, params):
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_b_c2.py` (5 hunks): `-10,0 +11,2`; `-11,0 +14`; `-44,0 +48` def judge_row(row, case, kind, params):; `-48,0 +53,4` def judge_row(row, case, kind, params):; `-64,0 +73,3` def _psc_base(row, params):
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_b_c3.py` (3 hunks): `-5,0 +6,3` as for H-S-A (d1 11; see README 확인 필요 Q-C3).; `-6,0 +10` as for H-S-A (d1 11; see README 확인 필요 Q-C3).; `-19,0 +24,5` def judge_row(row, case, kind, params):
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_b_c4.py` (3 hunks): `-5,0 +6,3` recorded crawler attitude, F<F_min times in [t_D, ; `-6,0 +10` recorded crawler attitude, F<F_min times in [t_D, ; `-33,2 +37,8` def judge_row(row, case, kind, params):
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_b_c5.py` (9 hunks): `-6,0 +7,6` passed -> `일치`(등급 `부분`).; `-10,0 +17` from pathlib import Path; `-11,0 +19` import p2_kinds as K; `-41,0 +50,4` V0_SUFFIXES = ("_V0", "_v0v"); `-45 +57,26` def judge_row(row, case, kind, params):; `-73,0 +111,10` def pair_check(rows, manifest_cases) -> dict:; `-76 +123,2` def bundle_status(rows):; `-78 +126,2` def bundle_status(rows):; `-80 +129` def bundle_status(rows):
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_b_c8.py` (4 hunks): `-4,0 +5,7` and [t_D, end] (R2-5), R_c from the recorded crawl; `-5,0 +13` and [t_D, end] (R2-5), R_c from the recorded crawl; `-46,0 +55,8` def judge_row(row, case, kind, params):; `-49,0 +66,30` def judge_row(row, case, kind, params):
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_cd.py` (1 hunks): `-0,0 +1,1402`
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_chrono.py` (9 hunks): `-27,0 +28` sys.path.insert(0, str(HERE))  # -I drops the scri; `-34 +35,4` BUNDLE_MODULES = {"C-1": "p2_b_c1", "C-2": "p2_b_c; `-324,0 +329,5` def augment_items(bundle: str, row, items: dict, k; `-360,0 +370,3` def judge(args) -> int:; `-381,0 +394,2` def judge(args) -> int:; `-397,0 +412` def judge(args) -> int:; `-400,0 +416,2` def judge(args) -> int:; `-411,0 +429,29` def judge(args) -> int:; `-669,0 +716,3` def main(argv=None) -> int:
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_kinds.py` (5 hunks): `-370 +370,4` def jp3_item(row):; `-404 +407,2` def jp3_item(row):; `-414,0 +419,8` def jp3_item(row):; `-434 +446` def jp3_item(row):; `-437,0 +450,16` def jp3_item(row):
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_rules.py` (4 hunks): `-71 +71,7` SEALED = [; `-140,0 +147,2` RAW_ONLY = {  # rev2 R2-9 last-but-one bullet: sea; `-155 +163` def seal_check(repo: Path) -> dict:; `-157 +165` def seal_check(repo: Path) -> dict:
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/test_p2_synthetic.py` (9 hunks): `-189,0 +190,8` def _set_npz(path: Path, **arrays):; `-751,0 +760` def t_scm(tmp):; `-753,2 +762,2` def t_scm(tmp):; `-1111 +1120` def t_seal(tmp, rules_repo=None):; `-1123,3 +1132,3` def t_seal(tmp, rules_repo=None):; `-1221,2 +1230,6` def t_cli(tmp):; `-1234,0 +1248,13` def t_cli(tmp):; `-1984,0 +2011,600` def t_pairs():; `-2010,0 +2637,2` def main():
- `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev24.md` (1 hunks): `-0,0 +1,241`
- `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev24.sha256` (1 hunks): `-0,0 +1`
- `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev24_seal_candidate_draft.md` (1 hunks): `-0,0 +1,241`
- `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev25.md` (1 hunks): `-0,0 +1,263`
- `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev25.sha256` (1 hunks): `-0,0 +1`
- `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev25_seal_candidate_draft.md` (1 hunks): `-0,0 +1,263`

### 086866a..c3f4cad files=9 stat:
9 files changed, 1151 insertions(+), 101 deletions(-)
- `.gitattributes` (1 hunks): `-141,0 +142,3`
- `04_scripts/02_chrono/chrono_bundle_grade_4368.py` (45 hunks): `-37,0 +38,8` it runs no simulation and no other judge:; `-103 +111` InputError = rows_judge.InputError; `-105 +113` TOOL_VERSION = ("chrono_bundle_grade_4368 v6 (pyth; `-111 +119,4` RULES_TEXT = ("rules rev18 R18-2 (bundle grades of; `-166,2 +176,0` D8_OVERRIDE_ITEMS = ("D8 min true cylinder force >; `-175,3 +184,3` CD7_RULE = ("rules rev24 CD-7: every not-judgeable; `-429,0 +439,2` def runner_items(doc: dict[str, Any], inner: str |; `-891 +902,2` def p3_items(p3b: dict[str, Any], judged_items: di; `-895,2 +907,5` def p3_items(p3b: dict[str, Any], judged_items: di; `-913,3 +928` def p3_items(p3b: dict[str, Any], judged_items: di; `-923,0 +937,52` def p3_items(p3b: dict[str, Any], judged_items: di; `-1468,0 +1534` METHOD_RUNNER, METHOD_RECOMPUTED = "원 판정기 실행", "재계; `-1470 +1536` RECOMPUTED_SOURCES = ("recomputed", "rev19", "chro; `-1473 +1539` ITEM_INTERVALS = {; `-1479,0 +1546,24` ITEM_INTERVALS = {; `-1493,0 +1584,11` def _interval(entry: dict[str, Any], method: str, ; `-1495,2 +1596,3` def list_entry(entry: dict[str, Any], event_row: b; `-1500,3 +1602,7` def list_entry(entry: dict[str, Any], event_row: b; `-1505,0 +1612,14` def list_entry(entry: dict[str, Any], event_row: b; `-1507 +1627,5` def _t45_entries(entry: dict[str, Any], event_row:; `-1509,4 +1633,19` def _t45_entries(entry: dict[str, Any], event_row:; `-1515,5 +1654,22` def _t45_entries(entry: dict[str, Any], event_row:; `-1521 +1677,2` def row_item_list(row: dict[str, Any], event_row: ; `-1523 +1680` def row_item_list(row: dict[str, Any], event_row: ; `-1524,0 +1682,11` def row_item_list(row: dict[str, Any], event_row: ; `-1526 +1694` def row_item_list(row: dict[str, Any], event_row: ; `-1530,3 +1698,53` def row_item_list(row: dict[str, Any], event_row: ; `-1536 +1754` def item_list(inputs: list[RowInput], rows: list[d; `-1538 +1756` def item_list(inputs: list[RowInput], rows: list[d; `-1540 +1758,3` def item_list(inputs: list[RowInput], rows: list[d; `-1542,0 +1763,3` def item_list(inputs: list[RowInput], rows: list[d; `-1566 +1789,2` def _scm_items(row: RowInput, bundle: str, judged_; `-1571 +1795,2` def _scm_items(row: RowInput, bundle: str, judged_; `-1586 +1811,3` def _scm_items(row: RowInput, bundle: str, judged_; `-1860,3 +2087,5` P3_RECORD_ITEMS = tuple(f"P3-{n}" for n in range(1; `-1895,2 +2124,3` def c8_record_values(row: RowInput, oc5_doc: dict[; `-1901 +2131,2` def c8_record_values(row: RowInput, oc5_doc: dict[; `-1903 +2134,7` def c8_record_values(row: RowInput, oc5_doc: dict[; `-1906 +2143,2` def c8_record_values(row: RowInput, oc5_doc: dict[; `-1908 +2145,0` def c8_record_values(row: RowInput, oc5_doc: dict[; `-1910 +2147,87` def c8_record_values(row: RowInput, oc5_doc: dict[; `-1930 +2253,2` def c4_row(row: RowInput) -> dict[str, Any]:; `-2069,2 +2393,2` def _graded_bundle(doc: dict[str, Any], bundle: st; `-2087,0 +2412,23` def reason_check(rows: list[dict[str, Any]]) -> di; `-2122,0 +2470,2` def _record_bundle(doc: dict[str, Any], bundle: st
- `04_scripts/02_chrono/chrono_rows_judge_4368.py` (7 hunks): `-38 +38` rules rev6 R6-A D-26 .. D-39):; `-133,0 +134,2` RULES_SEALS = {; `-135,3 +137,3` RULES_SEALS = {; `-139 +141,2` RULES_DESCRIPTION = ("v5_resume_4368_rules.md + re; `-142 +145` RULES_DESCRIPTION = ("v5_resume_4368_rules.md + re; `-984,2 +987,3` def ready_items(phases: list[tuple[float, str]], t; `-994,2 +998,3` def ready_items(phases: list[tuple[float, str]], t
- `04_scripts/02_chrono/chrono_rows_judge_4368_README.md` (9 hunks): `-99 +99` python -I -X utf8 04_scripts/02_chrono/chrono_rows; `-127 +127` python -I -X utf8 04_scripts/02_chrono/chrono_rows; `-132 +132` python -I -X utf8 04_scripts/02_chrono/chrono_rows; `-134 +134` python -I -X utf8 04_scripts/02_chrono/chrono_rows; `-136 +136` python -I -X utf8 04_scripts/02_chrono/chrono_rows; `-174 +174,2` python -I -B -X utf8 04_scripts/02_chrono/chrono_b; `-190 +191` python -I -B -X utf8 04_scripts/02_chrono/chrono_b; `-194,2 +195,2` python -I -B -X utf8 04_scripts/02_chrono/chrono_b; `-197 +198` python -I -B -X utf8 04_scripts/02_chrono/chrono_b
- `05_tests/unit/test_chrono_bundle_grade_4368.py` (13 hunks): `-80,0 +81,2` def write_scm_series(folder: Path, *, lift_after_l; `-82 +84` def write_scm_series(folder: Path, *, lift_after_l; `-642,3 +644,7` def oc5_result(**checks: Any) -> dict[str, Any]:; `-649,3 +655,4` def c8_bundle(tmp_path: Path) -> Bundle:; `-668,0 +676,16` def test_c8_record_with_s9_handling(mod, tmp_path); `-700,0 +724,3` def test_seals_command(mod, capsys):; `-1253 +1279,2` def test_r23_same_names_keep_the_rev22_output(mod,; `-1260 +1287,2` def test_r23_same_names_keep_the_rev22_output(mod,; `-1261,0 +1290,4` def test_r23_same_names_keep_the_rev22_output(mod,; `-1516,4 +1548,5` def test_cd5_p3_items_without_ready(mod):; `-1526,0 +1560,3` def test_cd5_p3_items_without_ready(mod):; `-1561 +1597,2` def test_cd11_item_list(mod, tmp_path):; `-1567,6 +1604,131` def test_cd11_item_list(mod, tmp_path):
- `05_tests/unit/test_chrono_rows_judge_4368.py` (6 hunks): `-607,0 +608` REV16_18_SHA256 = {; `-609 +610` REV16_18_SHA256 = {; `-614 +615` def test_rev16_to_rev18_in_the_seal_list(mod):; `-617 +618` def test_rev16_to_rev18_in_the_seal_list(mod):; `-988,0 +990,2` def test_cd5_ready_items_without_ready(mod):; `-990,2 +993,2` def test_cd5_ready_items_without_ready(mod):
- `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev25.md` (1 hunks): `-0,0 +1,263`
- `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev25.sha256` (1 hunks): `-0,0 +1`
- `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev25_seal_candidate_draft.md` (1 hunks): `-0,0 +1,263`

### 24481ad..0f2fd4e files=15 stat:
15 files changed, 1173 insertions(+), 109 deletions(-)
- `.gitattributes` (1 hunks): `-141,0 +142,3`
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/README.md` (3 hunks): `-4 +4`; `-59 +59,2` $d = "<repo>\06_analysis\02_control\verif_matrix\v; `-127,11 +128,11` $d = "<repo>\06_analysis\02_control\verif_matrix\v
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_b_c2.py` (2 hunks): `-52,0 +53` def judge_row(row, case, kind, params):; `-71,0 +73` def _psc_base(row, params):
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_b_c3.py` (2 hunks): `-6,0 +7,2` rev24 (common block scope sentence): CD-4 adds P3-; `-21,0 +24,2` def judge_row(row, case, kind, params):
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_b_c4.py` (1 hunks): `-36,0 +37,2` def judge_row(row, case, kind, params):
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_b_c5.py` (4 hunks): `-10,0 +11,2` K1_class stay as records whose stops still stop th; `-58 +60,2` def judge_row(row, case, kind, params):; `-69,4 +72,3` def _add_p3(items, graded, notes, row, params):; `-75,0 +78` def _add_p3(items, graded, notes, row, params):
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_b_c8.py` (4 hunks): `-9,0 +10,2` equal this path's R3d C-8 output (`--r3d-c8`), els; `-65,3 +67,3` def _add_record_values(items, row, params):; `-69,0 +72,2` def _add_record_values(items, row, params):; `-72,3 +75,0` def _add_record_values(items, row, params):
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_cd.py` (46 hunks): `-1 +1,2`; `-4 +5,3` Sources opened for this module (the 판정서 "읽은 것" lis; `-90,2 +93,2` P37_RISE_MIN_N = 4000.0                     # 284 ; `-110,2 +113,4` C5_ROWS_SCM = 11; `-114,0 +120,14` COMMON_ID = {"J11_window": "J11", "J-P3": "J-P3", ; `-165,0 +185,4` def judge_doc_for(row):; `-166,0 +190,2` def judge_rows_of(doc, row) -> list:; `-168 +193,2` def judge_rows_of(doc, row) -> list:; `-203,0 +230` def _event_abs(row):; `-205 +232,3` def _event_abs(row):; `-210,3 +239,4` def recalc_c1(row, params, tl) -> dict:; `-221,0 +252,6` def recalc_c1(row, params, tl) -> dict:; `-229,4 +264,0` def recalc_c1(row, params, tl) -> dict:; `-260,0 +293` def recalc_d8_lift(row, tl) -> dict:; `-400,0 +434` def cd3_items(row, params, ev, win) -> dict:; `-404,0 +439` def cd3_items(row, params, ev, win) -> dict:; `-413,0 +449` def cd3_items(row, params, ev, win) -> dict:; `-415,0 +452` def cd3_items(row, params, ev, win) -> dict:; `-420,0 +458` def cd3_items(row, params, ev, win) -> dict:; `-424,0 +463` def cd3_items(row, params, ev, win) -> dict:; `-480 +519` def cd2_items(row, params) -> dict:; `-570,0 +610` def _entry(row, params, j, tl, ev, cd3, stops) -> ; `-573 +613,2` def _entry(row, params, j, tl, ev, cd3, stops) -> ; `-577,0 +619` def _entry(row, params, j, tl, ev, cd3, stops) -> ; `-605,0 +648,7` def _entry(row, params, j, tl, ev, cd3, stops) -> ; `-721 +770,2` def p3_7(row, params, judged=True) -> dict:; `-757 +807,2` def p3_7(row, params, judged=True) -> dict:; `-760 +811,2` def p3_7(row, params, judged=True) -> dict:; `-785,0 +838,6` def p3_7(row, params, judged=True) -> dict:; `-858,0 +917,143` def scm_grade_guard(items, keys) -> dict | None:; `-927,6 +1128,66` def _first_stop(r):; `-936,3 +1197,5` def item_list(bundle: str, rows, record_bundle=Fal; `-939,0 +1203` def item_list(bundle: str, rows, record_bundle=Fal; `-941 +1205,2` def item_list(bundle: str, rows, record_bundle=Fal; `-943,0 +1209` def item_list(bundle: str, rows, record_bundle=Fal; `-945,15 +1211,20` def item_list(bundle: str, rows, record_bundle=Fal; `-961,5 +1232,4` def item_list(bundle: str, rows, record_bundle=Fal; `-967 +1237` def item_list(bundle: str, rows, record_bundle=Fal; `-969 +1239` def item_list(bundle: str, rows, record_bundle=Fal; `-975 +1245` def item_list(bundle: str, rows, record_bundle=Fal; `-986 +1256,4` def c8_values(row, items, params) -> dict:; `-991 +1264,4` def c8_values(row, items, params) -> dict:; `-1012 +1288` def c8_values(row, items, params) -> dict:; `-1014 +1290,2` def c8_values(row, items, params) -> dict:; `-1017,6 +1294,17` def c8_values(row, items, params) -> dict:; `-1025,0 +1314,2` def _per_leg_min(row, series, t0):
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_chrono.py` (1 hunks): `-393,0 +394,2` def judge(args) -> int:
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_kinds.py` (5 hunks): `-370 +370,4` def jp3_item(row):; `-404 +407,2` def jp3_item(row):; `-414,0 +419,8` def jp3_item(row):; `-434 +446` def jp3_item(row):; `-437,0 +450,16` def jp3_item(row):
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_rules.py` (4 hunks): `-74 +74,4` SEALED = [; `-144,0 +148` RAW_ONLY = {  # rev2 R2-9 last-but-one bullet: sea; `-159 +163` def seal_check(repo: Path) -> dict:; `-161 +165` def seal_check(repo: Path) -> dict:
- `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/test_p2_synthetic.py` (12 hunks): `-189,0 +190,8` def _set_npz(path: Path, **arrays):; `-751,0 +760` def t_scm(tmp):; `-753,2 +762,2` def t_scm(tmp):; `-1111 +1120` def t_seal(tmp, rules_repo=None):; `-1123,3 +1132,3` def t_seal(tmp, rules_repo=None):; `-1223,2 +1232,4` def t_cli(tmp):; `-2050 +2061` def write_judge_doc(s8c: Path, folder: Path, rows,; `-2330,3 +2341,4` def t_rev24(tmp):; `-2348,0 +2361,2` def t_rev24(tmp):; `-2350,4 +2364,6` def t_rev24(tmp):; `-2414,0 +2431,180` def t_rev24(tmp):; `-2441,0 +2638` def main():
- `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev25.md` (1 hunks): `-0,0 +1,263`
- `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev25.sha256` (1 hunks): `-0,0 +1`
- `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev25_seal_candidate_draft.md` (1 hunks): `-0,0 +1,263`


## 부록 C. CD-11 등급 항목 대응표 (두 경로 목록, 공통 항목 ID 기준, 이 판정서 작성자가 다시 셈)

- 입력: 경로 1 `bundle_C{1,2,3,5}.json` `item_list_CD_11`, 경로 2 `p2_C{1,2,3,5}.json` `bundle_result.cd11_item_list`. 등급 항목(분류 `등급 항목`)만, 판정은 원문 표기. '판정 같음'은 null·`na`·`해당 없음…`을 같은 것으로 본다.

**C-1** (경로 1 행 10, 경로 2 행 10)

| 행 | 공통 ID 일치(판정 같음) | 판정 다름 | 경로 1에만 | 경로 2에만 | 조항 ID 다름 |
|---|---|---|---|---|---|
| `D1C2_middle_rpBop_Fs4` | 18 | 0 | 0 | 0 | 0 |
| `D1C2_middle_fup3.2_Fs4` | 18 | 0 | 0 | 0 | 0 |
| `D1C2_middle_fdown3.2_Fs4` | 24 | 0 | 0 | 0 | 0 |
| `D1C2_bottom_fup3.2_Fs4` | 18 | 0 | 0 | 0 | 0 |
| `D1C2_bottom_fdown3.2_Fs4` | 24 | 0 | 0 | 0 | 0 |
| `D1C2_bottom_rpBop_Fs4` | 18 | 0 | 0 | 0 | 0 |
| `D1C1_top_flat_crx3` | 0 | 0 | 13 | 0 | 0 |
| `D1C1_top_rpBop_crx3` | 0 | 0 | 13 | 0 | 0 |
| `D1C1_bottom_flat_crx3` | 0 | 0 | 13 | 0 | 0 |
| `D1C1_bottom_rpBop_crx3` | 0 | 0 | 13 | 0 | 0 |

**C-2** (경로 1 행 6, 경로 2 행 6)

| 행 | 공통 ID 일치(판정 같음) | 판정 다름 | 경로 1에만 | 경로 2에만 | 조항 ID 다름 |
|---|---|---|---|---|---|
| `D1S_J1_B_bottom_Fs4_r0_pm2p8` | 6 | 0 | 0 | 0 | 0 |
| `D1S_J1_B_middle_Fs4_r0_pm2p8` | 6 | 0 | 0 | 0 | 0 |
| `D1C2_middle_rollm4.4_Fs4` | 18 | 0 | 0 | 0 | 0 |
| `D1C2_bottom_rollm4.4_Fs4` | 18 | 0 | 0 | 0 | 0 |
| `D1PSC_J1_B_top_Fs4_spFLJ1_base` | 0 | 0 | 9 | 0 | 0 |
| `D1PSC_J1_B_top_Fs4_FL_cslow` | 7 | 0 | 0 | 0 | 0 |

**C-3** (경로 1 행 2, 경로 2 행 2)

| 행 | 공통 ID 일치(판정 같음) | 판정 다름 | 경로 1에만 | 경로 2에만 | 조항 ID 다름 |
|---|---|---|---|---|---|
| `D1S_G1_B_bottom_Fs4_spJ1FL` | 10 | 0 | 0 | 0 | 0 |
| `D1S_G1_B_middle_Fs4_spJ1FL` | 10 | 0 | 0 | 0 | 0 |

**C-5** (경로 1 행 35, 경로 2 행 35)

| 행 | 공통 ID 일치(판정 같음) | 판정 다름 | 경로 1에만 | 경로 2에만 | 조항 ID 다름 |
|---|---|---|---|---|---|
| `P3b_J2_B_top_Fs4_m1p1_t180_seed20261026` | 10 | 1 | 0 | 2 | 0 |
| `P3b_J2_B_top_Fs4_m1p1_t180_seed20261028` | 10 | 1 | 0 | 2 | 0 |
| `P3b_J2_B_top_Fs4_m1p1_t180_seed20261026_flow` | 10 | 1 | 0 | 2 | 0 |
| `P3b_J2_B_top_Fs4_m1p1_t180` | 10 | 1 | 0 | 2 | 0 |
| `P3b_J1_B_top_Fs4_v0v` | 10 | 1 | 0 | 2 | 0 |
| `S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0_v0v` | 1 | 1 | 9 | 7 | 0 |
| `E_G4_Fs4_V0` | 29 | 1 | 0 | 2 | 0 |
| `E_RE1bF_Fs8_LS1` | 34 | 1 | 0 | 0 | 0 |
| `E_RE1bF_Fs8_LS4` | 34 | 1 | 0 | 0 | 0 |
| `E_RE1bF_Fs8` | 34 | 1 | 0 | 0 | 0 |
| `E_RE1bF_Fs0` | 35 | 1 | 0 | 0 | 0 |
| `G1R_FS24_FL_top_o050_Fs0` | 29 | 1 | 0 | 2 | 0 |
| `E_G4_Fs4` | 29 | 1 | 0 | 2 | 0 |
| `E_G4_Fs4_ph0.05` | 29 | 1 | 0 | 2 | 0 |
| `E_G4_Fs8` | 31 | 1 | 0 | 0 | 0 |
| `E_G4_Fs8_LS1` | 31 | 1 | 0 | 0 | 0 |
| `K8_top_fdown3.5_Fs8` | 33 | 1 | 0 | 0 | 0 |
| `E_G4_Fs8_LS4` | 31 | 1 | 0 | 0 | 0 |
| `S_top_fdown3.5_wika_Fs8` | 29 | 1 | 0 | 0 | 0 |
| `G1R_FS24_FL_top_o050_Fs0_V0` | 29 | 1 | 0 | 2 | 0 |
| `K0V_top_fdown3.5_Fs0` | 29 | 1 | 0 | 0 | 0 |
| `K0_top_fdown3.2_Fs0` | 27 | 1 | 0 | 0 | 0 |
| `K0V_top_fup3.5_Fs0_LS1` | 25 | 1 | 0 | 0 | 0 |
| `K8_top_rpB_Fs8` | 27 | 1 | 0 | 0 | 0 |
| `K0_top_fup3.2_Fs0` | 21 | 1 | 0 | 0 | 0 |
| `K0V_top_fup3.5_Fs0` | 25 | 1 | 0 | 0 | 0 |
| `K0V_top_roll5.5_Fs0` | 25 | 1 | 0 | 0 | 0 |
| `K0V_top_fup3.5_Fs0_LS4` | 25 | 1 | 0 | 0 | 0 |
| `K0_top_rpBop_Fs0` | 21 | 1 | 0 | 0 | 0 |
| `E_G4_Fs4_ph0.05_V0` | 29 | 1 | 0 | 2 | 0 |
| `P3b_J2_B_top_Fs4_m1p1_t180_seed20261027` | 10 | 1 | 0 | 2 | 0 |
| `P3b_J2_B_top_Fs4_m1p1_t180_seed20261029` | 10 | 1 | 0 | 2 | 0 |
| `P3b_J1_B_top_Fs4` | 10 | 1 | 0 | 2 | 0 |
| `S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0` | 1 | 1 | 9 | 7 | 0 |
| `P3b_J2_B_top_Fs4_m1p1_t180_v0v` | 10 | 1 | 0 | 2 | 0 |

합계: 일치 978, 판정 다름 35, 경로 1에만 79, 경로 2에만 44, 조항 ID 다름 0

### 방법 표(CD-11 방법 열; 등급 항목 수, 묶음 × 경로 × 방법)

| 묶음 | 경로 | 방법 | 등급 항목 수 |
|---|---|---|---|
| C1 | 경로 1 | 원 판정기 실행 | 134 |
| C1 | 경로 1 | 재계산 | 38 |
| C1 | 경로 2 | 원 판정기 실행 | 94 |
| C1 | 경로 2 | 재계산 | 26 |
| C2 | 경로 1 | 원 판정기 실행 | 38 |
| C2 | 경로 1 | 재계산 | 26 |
| C2 | 경로 2 | 원 판정기 실행 | 28 |
| C2 | 경로 2 | 재계산 | 27 |
| C3 | 경로 1 | 원 판정기 실행 | 2 |
| C3 | 경로 1 | 재계산 | 18 |
| C3 | 경로 2 | 재계산 | 20 |
| C5 | 경로 1 | 원 판정기 실행 | 588 |
| C5 | 경로 1 | 재계산 | 248 |
| C5 | 경로 2 | 원 판정기 실행 | 614 |
| C5 | 경로 2 | 재계산 | 248 |

### 항목별(경로 1 판정 / 경로 2 판정 [경로 1 방법 / 경로 2 방법], `—` = 그 경로 목록에 등급 항목으로 없음)

- C1 `D1C2_middle_rpBop_Fs4`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]
- C1 `D1C2_middle_fup3.2_Fs4`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]
- C1 `D1C2_middle_fdown3.2_Fs4`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; R attitude change during REANCHOR: pass/pass [원 판정기 실행/원 판정기 실행]; R H4 mechanism one-sided T_READY / mu(P_stop + m_rod g): pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; D8 no pad lift-off: pass/pass [재계산/재계산]; D8 attitude last 5 s + mount <= 0.2 deg: pass/pass [원 판정기 실행/원 판정기 실행]; REANCHOR min >= F_min + 7 kN: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; C2 REANCHOR min >= F_min + 7 kN: pass/pass [원 판정기 실행/원 판정기 실행]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]
- C1 `D1C2_bottom_fup3.2_Fs4`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]
- C1 `D1C2_bottom_fdown3.2_Fs4`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; R attitude change during REANCHOR: pass/pass [원 판정기 실행/원 판정기 실행]; R H4 mechanism one-sided T_READY / mu(P_stop + m_rod g): pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; D8 no pad lift-off: pass/pass [재계산/재계산]; D8 attitude last 5 s + mount <= 0.2 deg: pass/pass [원 판정기 실행/원 판정기 실행]; REANCHOR min >= F_min + 7 kN: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; C2 REANCHOR min >= F_min + 7 kN: pass/pass [원 판정기 실행/원 판정기 실행]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]
- C1 `D1C2_bottom_rpBop_Fs4`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]
- C1 `D1C1_top_flat_crx3`: run: pass/— [원 판정기 실행/—]; 2 attitude +-0.2 (+mount): pass/— [원 판정기 실행/—]; 3 F_min (1 ms): pass/— [원 판정기 실행/—]; 4 saturation steps: pass/— [재계산/—]; 4 max moving pressure: pass/— [재계산/—]; 5a rocking amplitude: pass/— [원 판정기 실행/—]; 7a probe attitude change: pass/— [원 판정기 실행/—]; 7b verdict = truth: pass/— [원 판정기 실행/—]; 7c load estimate error: pass/— [원 판정기 실행/—]; 72.1 (6) no false pressure diagnosis: pass/— [원 판정기 실행/—]; C-R5 CHECK attitude error <= 0.017 deg: pass/— [원 판정기 실행/—]; 5.24.2 unexpected warnings: pass/— [원 판정기 실행/—]; J-P3: None/— [재계산/—]
- C1 `D1C1_top_rpBop_crx3`: run: pass/— [원 판정기 실행/—]; 2 attitude +-0.2 (+mount): pass/— [원 판정기 실행/—]; 3 F_min (1 ms): pass/— [원 판정기 실행/—]; 4 saturation steps: pass/— [재계산/—]; 4 max moving pressure: pass/— [재계산/—]; 5a rocking amplitude: pass/— [원 판정기 실행/—]; 7a probe attitude change: pass/— [원 판정기 실행/—]; 7b verdict = truth: pass/— [원 판정기 실행/—]; 7c load estimate error: pass/— [원 판정기 실행/—]; 72.1 (6) no false pressure diagnosis: pass/— [원 판정기 실행/—]; C-R5 CHECK attitude error <= 0.017 deg: pass/— [원 판정기 실행/—]; 5.24.2 unexpected warnings: pass/— [원 판정기 실행/—]; J-P3: None/— [재계산/—]
- C1 `D1C1_bottom_flat_crx3`: run: pass/— [원 판정기 실행/—]; 2 attitude +-0.2 (+mount): pass/— [원 판정기 실행/—]; 3 F_min (1 ms): pass/— [원 판정기 실행/—]; 4 saturation steps: pass/— [재계산/—]; 4 max moving pressure: pass/— [재계산/—]; 5a rocking amplitude: pass/— [원 판정기 실행/—]; 7a probe attitude change: pass/— [원 판정기 실행/—]; 7b verdict = truth: pass/— [원 판정기 실행/—]; 7c load estimate error: pass/— [원 판정기 실행/—]; 72.1 (6) no false pressure diagnosis: pass/— [원 판정기 실행/—]; C-R5 CHECK attitude error <= 0.017 deg: pass/— [원 판정기 실행/—]; 5.24.2 unexpected warnings: pass/— [원 판정기 실행/—]; J-P3: None/— [재계산/—]
- C1 `D1C1_bottom_rpBop_crx3`: run: pass/— [원 판정기 실행/—]; 2 attitude +-0.2 (+mount): pass/— [원 판정기 실행/—]; 3 F_min (1 ms): pass/— [원 판정기 실행/—]; 4 saturation steps: pass/— [재계산/—]; 4 max moving pressure: pass/— [재계산/—]; 5a rocking amplitude: pass/— [원 판정기 실행/—]; 7a probe attitude change: pass/— [원 판정기 실행/—]; 7b verdict = truth: pass/— [원 판정기 실행/—]; 7c load estimate error: pass/— [원 판정기 실행/—]; 72.1 (6) no false pressure diagnosis: pass/— [원 판정기 실행/—]; C-R5 CHECK attitude error <= 0.017 deg: pass/— [원 판정기 실행/—]; 5.24.2 unexpected warnings: pass/— [원 판정기 실행/—]; J-P3: None/— [재계산/—]
- C2 `D1S_J1_B_bottom_Fs4_r0_pm2p8`: 427.9-1: pass/pass [재계산/재계산]; 427.9-2: pass/pass [재계산/재계산]; 427.9-3: pass/pass [재계산/재계산]; 427.9-4: pass/pass [재계산/재계산]; 427.9-5: pass/pass [재계산/재계산]; J-P3: pass/pass [재계산/재계산]
- C2 `D1S_J1_B_middle_Fs4_r0_pm2p8`: 427.9-1: pass/pass [재계산/재계산]; 427.9-2: pass/pass [재계산/재계산]; 427.9-3: pass/pass [재계산/재계산]; 427.9-4: pass/pass [재계산/재계산]; 427.9-5: pass/pass [재계산/재계산]; J-P3: pass/pass [재계산/재계산]
- C2 `D1C2_middle_rollm4.4_Fs4`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]
- C2 `D1C2_bottom_rollm4.4_Fs4`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]
- C2 `D1PSC_J1_B_top_Fs4_spFLJ1_base`: P3-1: pass/— [원 판정기 실행/—]; P3-2: pass/— [재계산/—]; P3-3: pass/— [재계산/—]; P3-4: pass/— [원 판정기 실행/—]; P3-5: pass/— [원 판정기 실행/—]; P3-7: pass/— [원 판정기 실행/—]; P3-8: pass/— [재계산/—]; FAULT0: pass/— [재계산/—]; J-P3: pass/— [재계산/—]
- C2 `D1PSC_J1_B_top_Fs4_FL_cslow`: E-1: pass/pass [원 판정기 실행/재계산]; E-3: pass/pass [원 판정기 실행/재계산]; E-4: pass/pass [원 판정기 실행/재계산]; E-5: fail/fail [원 판정기 실행/재계산]; E-6: pass/pass [원 판정기 실행/재계산]; E-7: pass/pass [원 판정기 실행/재계산]; J-P3: pass/pass [재계산/재계산]
- C3 `D1S_G1_B_bottom_Fs4_spJ1FL`: P3-1: pass/pass [재계산/재계산]; P3-2: pass/pass [재계산/재계산]; P3-3: pass/pass [재계산/재계산]; P3-4: pass/pass [재계산/재계산]; P3-5: pass/pass [재계산/재계산]; G6-6: pass/pass [재계산/재계산]; P3-8: pass/pass [재계산/재계산]; READY_le_120s: pass/pass [재계산/재계산]; P3-7: pass/pass [원 판정기 실행/재계산]; J-P3: pass/pass [재계산/재계산]
- C3 `D1S_G1_B_middle_Fs4_spJ1FL`: P3-1: pass/pass [재계산/재계산]; P3-2: pass/pass [재계산/재계산]; P3-3: pass/pass [재계산/재계산]; P3-4: pass/pass [재계산/재계산]; P3-5: pass/pass [재계산/재계산]; G6-6: pass/pass [재계산/재계산]; P3-8: pass/pass [재계산/재계산]; READY_le_120s: pass/pass [재계산/재계산]; P3-7: pass/pass [원 판정기 실행/재계산]; J-P3: pass/pass [재계산/재계산]
- C5 `P3b_J2_B_top_Fs4_m1p1_t180_seed20261026`: P3-1: pass/pass [원 판정기 실행/재계산]; P3-2: flag/flag [재계산/재계산]; P3-3: pass/pass [재계산/재계산]; P3-4: pass/pass [원 판정기 실행/재계산]; P3-5: pass/pass [원 판정기 실행/재계산]; P3-6: pass/pass [재계산/재계산]; P3-7: fail/fail [원 판정기 실행/재계산]; P3-8: pass/pass [재계산/재계산]; FAULT0: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; J-P3: None/na [재계산/재계산]; T4: —/na [—/원 판정기 실행]; T5: —/na [—/원 판정기 실행]
- C5 `P3b_J2_B_top_Fs4_m1p1_t180_seed20261028`: P3-1: flag/flag [원 판정기 실행/재계산]; P3-2: flag/flag [재계산/재계산]; P3-3: pass/pass [재계산/재계산]; P3-4: pass/pass [원 판정기 실행/재계산]; P3-5: pass/pass [원 판정기 실행/재계산]; P3-6: pass/pass [재계산/재계산]; P3-7: fail/fail [원 판정기 실행/재계산]; P3-8: pass/pass [재계산/재계산]; FAULT0: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; J-P3: None/na [재계산/재계산]; T4: —/na [—/원 판정기 실행]; T5: —/na [—/원 판정기 실행]
- C5 `P3b_J2_B_top_Fs4_m1p1_t180_seed20261026_flow`: P3-1: flag/flag [원 판정기 실행/재계산]; P3-2: flag/flag [재계산/재계산]; P3-3: pass/pass [재계산/재계산]; P3-4: pass/pass [원 판정기 실행/재계산]; P3-5: pass/pass [원 판정기 실행/재계산]; P3-6: pass/pass [재계산/재계산]; P3-7: fail/fail [원 판정기 실행/재계산]; P3-8: pass/pass [재계산/재계산]; FAULT0: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; J-P3: None/na [재계산/재계산]; T4: —/na [—/원 판정기 실행]; T5: —/na [—/원 판정기 실행]
- C5 `P3b_J2_B_top_Fs4_m1p1_t180`: P3-1: pass/pass [원 판정기 실행/재계산]; P3-2: flag/flag [재계산/재계산]; P3-3: pass/pass [재계산/재계산]; P3-4: pass/pass [원 판정기 실행/재계산]; P3-5: pass/pass [원 판정기 실행/재계산]; P3-6: fail/fail [재계산/재계산]; P3-7: fail/fail [원 판정기 실행/재계산]; P3-8: pass/pass [재계산/재계산]; FAULT0: pass/pass [재계산/재계산]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: —/na [—/원 판정기 실행]; T5: —/na [—/원 판정기 실행]
- C5 `P3b_J1_B_top_Fs4_v0v`: P3-1: pass/pass [원 판정기 실행/재계산]; P3-2: pass/pass [재계산/재계산]; P3-3: pass/pass [재계산/재계산]; P3-4: pass/pass [원 판정기 실행/재계산]; P3-5: pass/pass [원 판정기 실행/재계산]; P3-6: pass/pass [재계산/재계산]; P3-7: pass/pass [원 판정기 실행/재계산]; P3-8: pass/pass [재계산/재계산]; FAULT0: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; J-P3: None/na [재계산/재계산]; T4: —/na [—/원 판정기 실행]; T5: —/na [—/원 판정기 실행]
- C5 `S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0_v0v`: P3-1: fail/— [원 판정기 실행/—]; P3-2: pass/— [재계산/—]; P3-3: pass/— [재계산/—]; P3-4: None/— [원 판정기 실행/—]; P3-5: None/— [원 판정기 실행/—]; P3-6: fail/— [재계산/—]; P3-7: pass/— [원 판정기 실행/—]; P3-8: pass/— [재계산/—]; FAULT0: fail/— [재계산/—]; J11: pass/record [재계산/재계산]; J-P3: None/na [재계산/재계산]; 427.9-1: —/pass [—/재계산]; 427.9-2: —/pass [—/재계산]; 427.9-3: —/pass [—/재계산]; 427.9-4: —/pass [—/재계산]; 427.9-5: —/pass [—/재계산]; T4: —/na [—/원 판정기 실행]; T5: —/na [—/원 판정기 실행]
- C5 `E_G4_Fs4_V0`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 6 min after settlement: pass/pass [원 판정기 실행/원 판정기 실행]; 6 re-READY <= 40 s: pass/pass [원 판정기 실행/원 판정기 실행]; 6 final >= F_min + 5 kN: pass/pass [원 판정기 실행/원 판정기 실행]; 6 attitude <= 0.2 deg (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; R-5 justified firing (floor event): pass/pass [원 판정기 실행/원 판정기 실행]; G4 item 6 (1) min after settlement >= F_min: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; I1 J_C: M1 = 0, M1' = 0 (fast events), F2 = 0 [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I2 J_C: no actual control action in event-free windows [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I3 J_C: M4 max <= sensor share [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 U-S8-9: E-group G4 C8 min >= F_min and re-READY <= 40 s [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-36 twist-mode work recurrence: clusters of 0.5 s bins > +20 J after event + 1.5 s (forced window masked) <= 1 (spec rev. 54 248.3, ASSUMPTION) - judged (RT variant runs) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; J11: pass/record [재계산/재계산]; J-P3: None/na [재계산/재계산]; T4: —/na [—/원 판정기 실행]; T5: —/na [—/원 판정기 실행]
- C5 `E_RE1bF_Fs8_LS1`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min before the event: pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min after the re-READY: pass/pass [원 판정기 실행/원 판정기 실행]; 3 lift-off other legs in the event transient: pass/pass [원 판정기 실행/원 판정기 실행]; 3 lift-off other legs after the transient: pass/pass [원 판정기 실행/원 판정기 실행]; 3 lift-off RR after the re-READY: pass/pass [원 판정기 실행/원 판정기 실행]; RE1b re-READY <= 60 s: pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure outside the event transient: pass/pass [재계산/재계산]; 4 max pressure in the event transient: pass/pass [재계산/재계산]; 5a rocking amplitude after the re-READY: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; R-5 justified firing (floor event): pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F7 first re-approach after the RE1b event <= 0.3 s: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; I1 J_C: M1 = 0, M1' = 0 (fast events), F2 = 0 [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I2 J_C: no actual control action in event-free windows [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I3 J_C: M4 max <= sensor share [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I4 classification vs control rev. 41 expected table (211.2): pass/pass [원 판정기 실행/원 판정기 실행]; I4 summary (gate: every compared case matches) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-36 twist-mode work recurrence: clusters of 0.5 s bins > +20 J after event + 1.5 s (forced window masked) <= 1 (spec rev. 54 248.3, ASSUMPTION) - judged (RT variant runs) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `E_RE1bF_Fs8_LS4`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min before the event: pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min after the re-READY: pass/pass [원 판정기 실행/원 판정기 실행]; 3 lift-off other legs in the event transient: pass/pass [원 판정기 실행/원 판정기 실행]; 3 lift-off other legs after the transient: pass/pass [원 판정기 실행/원 판정기 실행]; 3 lift-off RR after the re-READY: pass/pass [원 판정기 실행/원 판정기 실행]; RE1b re-READY <= 60 s: pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure outside the event transient: pass/pass [재계산/재계산]; 4 max pressure in the event transient: pass/pass [재계산/재계산]; 5a rocking amplitude after the re-READY: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; R-5 justified firing (floor event): pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F7 first re-approach after the RE1b event <= 0.3 s: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; I1 J_C: M1 = 0, M1' = 0 (fast events), F2 = 0 [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I2 J_C: no actual control action in event-free windows [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I3 J_C: M4 max <= sensor share [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I4 classification vs control rev. 41 expected table (211.2): pass/pass [원 판정기 실행/원 판정기 실행]; I4 summary (gate: every compared case matches) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-36 twist-mode work recurrence: clusters of 0.5 s bins > +20 J after event + 1.5 s (forced window masked) <= 1 (spec rev. 54 248.3, ASSUMPTION) - judged (RT variant runs) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `E_RE1bF_Fs8`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min before the event: pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min after the re-READY: pass/pass [원 판정기 실행/원 판정기 실행]; 3 lift-off other legs in the event transient: pass/pass [원 판정기 실행/원 판정기 실행]; 3 lift-off other legs after the transient: pass/pass [원 판정기 실행/원 판정기 실행]; 3 lift-off RR after the re-READY: pass/pass [원 판정기 실행/원 판정기 실행]; RE1b re-READY <= 60 s: pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure outside the event transient: pass/pass [재계산/재계산]; 4 max pressure in the event transient: pass/pass [재계산/재계산]; 5a rocking amplitude after the re-READY: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; R-5 justified firing (floor event): pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F7 first re-approach after the RE1b event <= 0.3 s: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; I1 J_C: M1 = 0, M1' = 0 (fast events), F2 = 0 [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I2 J_C: no actual control action in event-free windows [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I3 J_C: M4 max <= sensor share [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I4 classification vs control rev. 41 expected table (211.2): pass/pass [원 판정기 실행/원 판정기 실행]; I4 summary (gate: every compared case matches) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-36 twist-mode work recurrence: clusters of 0.5 s bins > +20 J after event + 1.5 s (forced window masked) <= 1 (spec rev. 54 248.3, ASSUMPTION) - judged (RT variant runs) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `E_RE1bF_Fs0`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min before the event: pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min after the re-READY: pass/pass [원 판정기 실행/원 판정기 실행]; 3 lift-off other legs in the event transient: pass/pass [원 판정기 실행/원 판정기 실행]; 3 lift-off other legs after the transient: pass/pass [원 판정기 실행/원 판정기 실행]; 3 lift-off RR after the re-READY: pass/pass [원 판정기 실행/원 판정기 실행]; RE1b re-READY <= 60 s: pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure outside the event transient: pass/pass [재계산/재계산]; 4 max pressure in the event transient: pass/pass [재계산/재계산]; 5a rocking amplitude after the re-READY: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 7c load estimate error: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; R-5 justified firing (floor event): pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F7 first re-approach after the RE1b event <= 0.3 s: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; I1 J_C: M1 = 0, M1' = 0 (fast events), F2 = 0 [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I2 J_C: no actual control action in event-free windows [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I3 J_C: M4 max <= sensor share [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I4 classification vs control rev. 41 expected table (211.2): pass/pass [원 판정기 실행/원 판정기 실행]; I4 summary (gate: every compared case matches) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-36 twist-mode work recurrence: clusters of 0.5 s bins > +20 J after event + 1.5 s (forced window masked) <= 1 (spec rev. 54 248.3, ASSUMPTION) - judged (RT variant runs) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `G1R_FS24_FL_top_o050_Fs0`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min before the event: pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min after the re-READY: pass/pass [원 판정기 실행/원 판정기 실행]; RE1b re-READY <= 60 s: pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure outside the event transient: pass/pass [재계산/재계산]; 4 max pressure in the event transient: pass/pass [재계산/재계산]; 5a rocking amplitude after the re-READY: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 7c load estimate error: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-72 U-S8-32 adjacent legs U57: lift sum <= 0.5 s, gap <= 2 mm in the physical window, 0 outside: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-72 U-S8-32 event legs (settled + diagonal): cumulative lift <= 1.8 s, last re-contact <= event + 3 s (U-S8-37; column <= 2.5 s nominal damping, display), FAULT 0 (ASSUMPTION): pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-72 U58: head F/A_p in the window <= 350 bar, outside extension samples <= 180 bar (slow event: whole-run any-state peak <= 350): pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-72 F_min U-S8-74: 0.5 s moving mean >= F_min and no pad lift after the window end (fast); 1 ms min >= F_min (slow): pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-72 end: READY and last 1 s mean true |roll|, |pitch| <= 0.2 deg: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-72 recurrence ban (248.3): twist-work clusters of 0.5 s bins > +20 J after event + 1.5 s <= 1: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-36 twist-mode work recurrence: clusters of 0.5 s bins > +20 J after event + 1.5 s (forced window masked) <= 1 (spec rev. 54 248.3, ASSUMPTION) - judged (RT variant runs) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: —/na [—/원 판정기 실행]; T5: —/na [—/원 판정기 실행]
- C5 `E_G4_Fs4`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 6 min after settlement: pass/pass [원 판정기 실행/원 판정기 실행]; 6 re-READY <= 40 s: pass/pass [원 판정기 실행/원 판정기 실행]; 6 final >= F_min + 5 kN: pass/pass [원 판정기 실행/원 판정기 실행]; 6 attitude <= 0.2 deg (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; R-5 justified firing (floor event): pass/pass [원 판정기 실행/원 판정기 실행]; G4 item 6 (1) min after settlement >= F_min: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; I1 J_C: M1 = 0, M1' = 0 (fast events), F2 = 0 [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I2 J_C: no actual control action in event-free windows [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I3 J_C: M4 max <= sensor share [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 U-S8-9: E-group G4 C8 min >= F_min and re-READY <= 40 s [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-36 twist-mode work recurrence: clusters of 0.5 s bins > +20 J after event + 1.5 s (forced window masked) <= 1 (spec rev. 54 248.3, ASSUMPTION) - judged (RT variant runs) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: —/na [—/원 판정기 실행]; T5: —/na [—/원 판정기 실행]
- C5 `E_G4_Fs4_ph0.05`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 6 min after settlement: pass/pass [원 판정기 실행/원 판정기 실행]; 6 re-READY <= 40 s: pass/pass [원 판정기 실행/원 판정기 실행]; 6 final >= F_min + 5 kN: pass/pass [원 판정기 실행/원 판정기 실행]; 6 attitude <= 0.2 deg (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; R-5 justified firing (floor event): pass/pass [원 판정기 실행/원 판정기 실행]; G4 item 6 (1) min after settlement >= F_min: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; I1 J_C: M1 = 0, M1' = 0 (fast events), F2 = 0 [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I2 J_C: no actual control action in event-free windows [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I3 J_C: M4 max <= sensor share [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 U-S8-9: E-group G4 C8 min >= F_min and re-READY <= 40 s [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-36 twist-mode work recurrence: clusters of 0.5 s bins > +20 J after event + 1.5 s (forced window masked) <= 1 (spec rev. 54 248.3, ASSUMPTION) - judged (RT variant runs) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: —/na [—/원 판정기 실행]; T5: —/na [—/원 판정기 실행]
- C5 `E_G4_Fs8`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 6 min after settlement: pass/pass [원 판정기 실행/원 판정기 실행]; 6 re-READY <= 40 s: pass/pass [원 판정기 실행/원 판정기 실행]; 6 final >= F_min + 5 kN: pass/pass [원 판정기 실행/원 판정기 실행]; 6 attitude <= 0.2 deg (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; R-5 justified firing (floor event): pass/pass [원 판정기 실행/원 판정기 실행]; G4 item 6 (1) min after settlement >= F_min: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; I1 J_C: M1 = 0, M1' = 0 (fast events), F2 = 0 [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I2 J_C: no actual control action in event-free windows [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I3 J_C: M4 max <= sensor share [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 U-S8-9: E-group G4 C8 min >= F_min and re-READY <= 40 s [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-36 twist-mode work recurrence: clusters of 0.5 s bins > +20 J after event + 1.5 s (forced window masked) <= 1 (spec rev. 54 248.3, ASSUMPTION) - judged (RT variant runs) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `E_G4_Fs8_LS1`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 6 min after settlement: pass/pass [원 판정기 실행/원 판정기 실행]; 6 re-READY <= 40 s: pass/pass [원 판정기 실행/원 판정기 실행]; 6 final >= F_min + 5 kN: pass/pass [원 판정기 실행/원 판정기 실행]; 6 attitude <= 0.2 deg (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; R-5 justified firing (floor event): pass/pass [원 판정기 실행/원 판정기 실행]; G4 item 6 (1) min after settlement >= F_min: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; I1 J_C: M1 = 0, M1' = 0 (fast events), F2 = 0 [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I2 J_C: no actual control action in event-free windows [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I3 J_C: M4 max <= sensor share [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 U-S8-9: E-group G4 C8 min >= F_min and re-READY <= 40 s [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-36 twist-mode work recurrence: clusters of 0.5 s bins > +20 J after event + 1.5 s (forced window masked) <= 1 (spec rev. 54 248.3, ASSUMPTION) - judged (RT variant runs) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `K8_top_fdown3.5_Fs8`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 7c zero-calibration deduction legs: warning event: pass/pass [원 판정기 실행/원 판정기 실행]; R/D8 min force >= F_min + 5 kN: pass/pass [원 판정기 실행/원 판정기 실행]; R/D8 no pad lift-off: pass/pass [원 판정기 실행/원 판정기 실행]; R attitude change during REANCHOR: pass/pass [원 판정기 실행/원 판정기 실행]; R H4 mechanism one-sided T_READY / mu(P_stop + m_rod g): pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; D8 no pad lift-off: pass/pass [재계산/재계산]; D8 attitude last 5 s + mount <= 0.2 deg: pass/pass [원 판정기 실행/원 판정기 실행]; REANCHOR min >= F_min + 7 kN: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; C2 REANCHOR min >= F_min + 7 kN: pass/pass [원 판정기 실행/원 판정기 실행]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; I1 J_C: M1 = 0, M1' = 0 (fast events), F2 = 0 [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I2 J_C: no actual control action in event-free windows [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I4 classification vs control rev. 41 expected table (211.2): pass/pass [원 판정기 실행/원 판정기 실행]; I4 summary (gate: every compared case matches) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `E_G4_Fs8_LS4`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 6 min after settlement: pass/pass [원 판정기 실행/원 판정기 실행]; 6 re-READY <= 40 s: pass/pass [원 판정기 실행/원 판정기 실행]; 6 final >= F_min + 5 kN: pass/pass [원 판정기 실행/원 판정기 실행]; 6 attitude <= 0.2 deg (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; R-5 justified firing (floor event): pass/pass [원 판정기 실행/원 판정기 실행]; G4 item 6 (1) min after settlement >= F_min: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; I1 J_C: M1 = 0, M1' = 0 (fast events), F2 = 0 [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I2 J_C: no actual control action in event-free windows [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I3 J_C: M4 max <= sensor share [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 U-S8-9: E-group G4 C8 min >= F_min and re-READY <= 40 s [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-36 twist-mode work recurrence: clusters of 0.5 s bins > +20 J after event + 1.5 s (forced window masked) <= 1 (spec rev. 54 248.3, ASSUMPTION) - judged (RT variant runs) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `S_top_fdown3.5_wika_Fs8`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; R/D8 min force >= F_min + 5 kN: pass/pass [원 판정기 실행/원 판정기 실행]; R/D8 no pad lift-off: pass/pass [원 판정기 실행/원 판정기 실행]; R attitude change during REANCHOR: pass/pass [원 판정기 실행/원 판정기 실행]; R H4 mechanism one-sided T_READY / mu(P_stop + m_rod g): pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; D8 no pad lift-off: pass/pass [재계산/재계산]; D8 attitude last 5 s + mount <= 0.2 deg: pass/pass [원 판정기 실행/원 판정기 실행]; REANCHOR min >= F_min + 7 kN: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; C2 REANCHOR min >= F_min + 7 kN: pass/pass [원 판정기 실행/원 판정기 실행]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F1 reading law per leg: |mean r| <= 0.1 kN, std r / sigma_F in [0.85, 1.15] (R45-1 ②, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `G1R_FS24_FL_top_o050_Fs0_V0`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min before the event: pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min after the re-READY: pass/pass [원 판정기 실행/원 판정기 실행]; RE1b re-READY <= 60 s: pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure outside the event transient: pass/pass [재계산/재계산]; 4 max pressure in the event transient: pass/pass [재계산/재계산]; 5a rocking amplitude after the re-READY: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 7c load estimate error: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-72 U-S8-32 adjacent legs U57: lift sum <= 0.5 s, gap <= 2 mm in the physical window, 0 outside: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-72 U-S8-32 event legs (settled + diagonal): cumulative lift <= 1.8 s, last re-contact <= event + 3 s (U-S8-37; column <= 2.5 s nominal damping, display), FAULT 0 (ASSUMPTION): pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-72 U58: head F/A_p in the window <= 350 bar, outside extension samples <= 180 bar (slow event: whole-run any-state peak <= 350): pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-72 F_min U-S8-74: 0.5 s moving mean >= F_min and no pad lift after the window end (fast); 1 ms min >= F_min (slow): pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-72 end: READY and last 1 s mean true |roll|, |pitch| <= 0.2 deg: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-72 recurrence ban (248.3): twist-work clusters of 0.5 s bins > +20 J after event + 1.5 s <= 1: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-36 twist-mode work recurrence: clusters of 0.5 s bins > +20 J after event + 1.5 s (forced window masked) <= 1 (spec rev. 54 248.3, ASSUMPTION) - judged (RT variant runs) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; J11: pass/record [재계산/재계산]; J-P3: None/na [재계산/재계산]; T4: —/na [—/원 판정기 실행]; T5: —/na [—/원 판정기 실행]
- C5 `K0V_top_fdown3.5_Fs0`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 7c load estimate error: pass/pass [원 판정기 실행/원 판정기 실행]; R/D8 min force >= F_min + 5 kN: pass/pass [원 판정기 실행/원 판정기 실행]; R/D8 no pad lift-off: pass/pass [원 판정기 실행/원 판정기 실행]; R attitude change during REANCHOR: pass/pass [원 판정기 실행/원 판정기 실행]; R H4 mechanism one-sided T_READY / mu(P_stop + m_rod g): pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; D8 no pad lift-off: pass/pass [재계산/재계산]; D8 attitude last 5 s + mount <= 0.2 deg: pass/pass [원 판정기 실행/원 판정기 실행]; REANCHOR min >= F_min + 7 kN: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; C2 REANCHOR min >= F_min + 7 kN: pass/pass [원 판정기 실행/원 판정기 실행]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `K0_top_fdown3.2_Fs0`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 7c load estimate error: pass/pass [원 판정기 실행/원 판정기 실행]; R attitude change during REANCHOR: pass/pass [원 판정기 실행/원 판정기 실행]; R H4 mechanism one-sided T_READY / mu(P_stop + m_rod g): pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; D8 no pad lift-off: pass/pass [재계산/재계산]; D8 attitude last 5 s + mount <= 0.2 deg: pass/pass [원 판정기 실행/원 판정기 실행]; REANCHOR min >= F_min + 7 kN: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; C2 REANCHOR min >= F_min + 7 kN: pass/pass [원 판정기 실행/원 판정기 실행]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `K0V_top_fup3.5_Fs0_LS1`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 7c load estimate error: pass/pass [원 판정기 실행/원 판정기 실행]; R/D8 min force >= F_min + 5 kN: pass/pass [원 판정기 실행/원 판정기 실행]; R/D8 no pad lift-off: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; D8 no pad lift-off: pass/pass [재계산/재계산]; D8 attitude last 5 s + mount <= 0.2 deg: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `K8_top_rpB_Fs8`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 7c zero-calibration deduction legs: warning event: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; D8 no pad lift-off: pass/pass [재계산/재계산]; D8 attitude last 5 s + mount <= 0.2 deg: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; I1 J_C: M1 = 0, M1' = 0 (fast events), F2 = 0 [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I2 J_C: no actual control action in event-free windows [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I4 classification vs control rev. 41 expected table (211.2): pass/pass [원 판정기 실행/원 판정기 실행]; I4 summary (gate: every compared case matches) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `K0_top_fup3.2_Fs0`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 7c load estimate error: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `K0V_top_fup3.5_Fs0`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 7c load estimate error: pass/pass [원 판정기 실행/원 판정기 실행]; R/D8 min force >= F_min + 5 kN: pass/pass [원 판정기 실행/원 판정기 실행]; R/D8 no pad lift-off: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; D8 no pad lift-off: pass/pass [재계산/재계산]; D8 attitude last 5 s + mount <= 0.2 deg: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `K0V_top_roll5.5_Fs0`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 7c load estimate error: pass/pass [원 판정기 실행/원 판정기 실행]; R/D8 min force >= F_min + 5 kN: pass/pass [원 판정기 실행/원 판정기 실행]; R/D8 no pad lift-off: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; D8 no pad lift-off: pass/pass [재계산/재계산]; D8 attitude last 5 s + mount <= 0.2 deg: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `K0V_top_fup3.5_Fs0_LS4`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 7c load estimate error: pass/pass [원 판정기 실행/원 판정기 실행]; R/D8 min force >= F_min + 5 kN: pass/pass [원 판정기 실행/원 판정기 실행]; R/D8 no pad lift-off: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; D8 no pad lift-off: pass/pass [재계산/재계산]; D8 attitude last 5 s + mount <= 0.2 deg: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `K0_top_rpBop_Fs0`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 7c load estimate error: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: pass/pass [재계산/원 판정기 실행]; T5: pass/pass [재계산/원 판정기 실행]
- C5 `E_G4_Fs4_ph0.05_V0`: run: pass/pass [원 판정기 실행/원 판정기 실행]; 2 attitude +-0.2 (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 3 F_min (1 ms): pass/pass [원 판정기 실행/원 판정기 실행]; 4 saturation steps: pass/pass [재계산/재계산]; 4 max moving pressure: pass/pass [재계산/재계산]; 5a rocking amplitude: pass/pass [원 판정기 실행/원 판정기 실행]; 6 min after settlement: pass/pass [원 판정기 실행/원 판정기 실행]; 6 re-READY <= 40 s: pass/pass [원 판정기 실행/원 판정기 실행]; 6 final >= F_min + 5 kN: pass/pass [원 판정기 실행/원 판정기 실행]; 6 attitude <= 0.2 deg (+mount): pass/pass [원 판정기 실행/원 판정기 실행]; 7a probe attitude change: pass/pass [원 판정기 실행/원 판정기 실행]; 7b verdict = truth: pass/pass [원 판정기 실행/원 판정기 실행]; 72.1 (6) no false pressure diagnosis: pass/pass [원 판정기 실행/원 판정기 실행]; R-5 justified firing (floor event): pass/pass [원 판정기 실행/원 판정기 실행]; G4 item 6 (1) min after settlement >= F_min: pass/pass [원 판정기 실행/원 판정기 실행]; 5.24.2 unexpected warnings: pass/pass [원 판정기 실행/원 판정기 실행]; C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN: pass/pass [재계산/재계산]; F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18): pass/pass [원 판정기 실행/원 판정기 실행]; F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share (after lift-off): pass/pass [원 판정기 실행/원 판정기 실행]; F3 F_band >= F_s after the first probe: pass/pass [원 판정기 실행/원 판정기 실행]; F8 no false re-level in event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; I1 J_C: M1 = 0, M1' = 0 (fast events), F2 = 0 [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I2 J_C: no actual control action in event-free windows [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; I3 J_C: M4 max <= sensor share [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact): pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 U-S8-9: E-group G4 C8 min >= F_min and re-READY <= 40 s [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY: pass/pass [원 판정기 실행/원 판정기 실행]; C-S8-36 twist-mode work recurrence: clusters of 0.5 s bins > +20 J after event + 1.5 s (forced window masked) <= 1 (spec rev. 54 248.3, ASSUMPTION) - judged (RT variant runs) [case *]: pass/pass [원 판정기 실행/원 판정기 실행]; J11: pass/record [재계산/재계산]; J-P3: None/na [재계산/재계산]; T4: —/na [—/원 판정기 실행]; T5: —/na [—/원 판정기 실행]
- C5 `P3b_J2_B_top_Fs4_m1p1_t180_seed20261027`: P3-1: flag/flag [원 판정기 실행/재계산]; P3-2: flag/flag [재계산/재계산]; P3-3: pass/pass [재계산/재계산]; P3-4: pass/pass [원 판정기 실행/재계산]; P3-5: pass/pass [원 판정기 실행/재계산]; P3-6: fail/fail [재계산/재계산]; P3-7: fail/fail [원 판정기 실행/재계산]; P3-8: pass/pass [재계산/재계산]; FAULT0: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; J-P3: None/na [재계산/재계산]; T4: —/na [—/원 판정기 실행]; T5: —/na [—/원 판정기 실행]
- C5 `P3b_J2_B_top_Fs4_m1p1_t180_seed20261029`: P3-1: pass/pass [원 판정기 실행/재계산]; P3-2: pass/pass [재계산/재계산]; P3-3: pass/pass [재계산/재계산]; P3-4: pass/pass [원 판정기 실행/재계산]; P3-5: pass/pass [원 판정기 실행/재계산]; P3-6: fail/fail [재계산/재계산]; P3-7: fail/fail [원 판정기 실행/재계산]; P3-8: pass/pass [재계산/재계산]; FAULT0: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; J-P3: None/na [재계산/재계산]; T4: —/na [—/원 판정기 실행]; T5: —/na [—/원 판정기 실행]
- C5 `P3b_J1_B_top_Fs4`: P3-1: pass/pass [원 판정기 실행/재계산]; P3-2: pass/pass [재계산/재계산]; P3-3: pass/pass [재계산/재계산]; P3-4: pass/pass [원 판정기 실행/재계산]; P3-5: pass/pass [원 판정기 실행/재계산]; P3-6: pass/pass [재계산/재계산]; P3-7: pass/pass [원 판정기 실행/재계산]; P3-8: pass/pass [재계산/재계산]; FAULT0: pass/pass [재계산/재계산]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; T4: —/na [—/원 판정기 실행]; T5: —/na [—/원 판정기 실행]
- C5 `S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0`: P3-1: fail/— [원 판정기 실행/—]; P3-2: pass/— [재계산/—]; P3-3: pass/— [재계산/—]; P3-4: None/— [원 판정기 실행/—]; P3-5: None/— [원 판정기 실행/—]; P3-6: fail/— [재계산/—]; P3-7: pass/— [원 판정기 실행/—]; P3-8: pass/— [재계산/—]; FAULT0: fail/— [재계산/—]; J-P3: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; 427.9-1: —/pass [—/재계산]; 427.9-2: —/pass [—/재계산]; 427.9-3: —/pass [—/재계산]; 427.9-4: —/pass [—/재계산]; 427.9-5: —/pass [—/재계산]; T4: —/na [—/원 판정기 실행]; T5: —/na [—/원 판정기 실행]
- C5 `P3b_J2_B_top_Fs4_m1p1_t180_v0v`: P3-1: pass/pass [원 판정기 실행/재계산]; P3-2: flag/flag [재계산/재계산]; P3-3: pass/pass [재계산/재계산]; P3-4: pass/pass [원 판정기 실행/재계산]; P3-5: pass/pass [원 판정기 실행/재계산]; P3-6: fail/fail [재계산/재계산]; P3-7: fail/fail [원 판정기 실행/재계산]; P3-8: pass/pass [재계산/재계산]; FAULT0: pass/pass [재계산/재계산]; J11: pass/record [재계산/재계산]; J-P3: None/na [재계산/재계산]; T4: —/na [—/원 판정기 실행]; T5: —/na [—/원 판정기 실행]


## 부록 F. 실행 스크립트·비교기 diff (rev24 R24-3·rev25 R25-3 "sha256과 R3d 판·R3e 판과의 diff")

- 만든 명령(읽기 전용): `git -c core.autocrlf=false diff --no-index -U2 <앞 판> <R3f 실행본>`. 줄 끝 CR은 diff 전에 비교에서 빼지 않았다(파일 그대로). 중괄호 대문자 자리표시 오탐을 피하려고 diff 본문의 `{`·`}`를 `｛`·`｝`(전각)로 바꿨다.

### 경로 1 실행 스크립트, R3d 판 → R3f

- 앞 판 `C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\judge_0220671\chrono_path1\run_path1_r3d.ps1` sha256 `2b68109d5bbac56f1fffbc0447b7e2737a3562315ff394aa71116f69ff6996ff`
- R3f `C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\judge_8a0c843\chrono_path1\run_path1_r3f.ps1` sha256 `faf01f0e2451550685957e1b41b61551889534094b0b368a13d84877fc8bbbfc`
- 1 file changed, 53 insertions(+), 21 deletions(-)

```diff
diff --git "a/C:\\workspace\\outrigger_control\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\judge_0220671\\chrono_path1\\run_path1_r3d.ps1" "b/C:\\workspace\\outrigger_control\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\judge_8a0c843\\chrono_path1\\run_path1_r3f.ps1"
index ec00bd1..eb27c35 100644
--- "a/C:\\workspace\\outrigger_control\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\judge_0220671\\chrono_path1\\run_path1_r3d.ps1"
+++ "b/C:\\workspace\\outrigger_control\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\judge_8a0c843\\chrono_path1\\run_path1_r3f.ps1"
@@ -1,12 +1,18 @@
 #Requires -Version 7.2
-# 436.8 R3d Chrono judgement, path 1 (python-expert, 2026-11-15; DRAFT, not run). Copy of run_path1_r3c.ps1
-# (judge_f9bc3c7) with the three changes rev22 R22-3 allows: (1) the output folder is judge_<R3d short hash>;
-# (2) the reused inputs (runner_judge\, t45_C5.json, R3c judge_C5.json / bundle outputs for the comparison) are read
-# from the R3c folder after a check against its SHA256SUMS.txt, and nothing is written there (the runner / t45 stages
-# refuse to run); (3) the t45 pairing arguments (rev22 R22-1), the row-judge re-run and the comparison stages.
+# 436.8 R3f Chrono judgement, path 1 (python-expert, 2026-11-16; DRAFT, not run). Copy of the unrun R3e draft
+# run_path1_r3e.ps1, itself a copy of run_path1_r3d.ps1 (judge_0220671), with the changes rules rev24 R24-3 and
+# rev25 R25-3 allow: (1) the output folder is judge_<R3f short hash>; (2) the reused inputs stay in the R3c folder
+# (runner_judge\, t45_C5.json, R3c judge_C5.json, run_path1_r3c.ps1); (3) R3c and R3d before / after checks (each
+# SHA256SUMS.txt file sha256 and every entry; nothing is written there; a failure ends the script with exit 4);
+# (4) the new steps the rev24 tools need (R24-2): --runner-judge-dir for the row judge (CD-3 window end difference),
+# the C-4 record bundle (CD-9) and --rows-judge for C-8 (CD-8 values); (5) the K-10 comparison against R3d with the
+# CD-10 / CD-7 keys left out and the pre-registered allowed keys (compare_r3d.py, allowed_keys_path1.md);
+# (6, rev25 R25-3) the run checkout check: `git rev-parse HEAD` must be the full R3f hash, else S-12 and exit 2;
+# (7, rev25 R25-3) a C-1 / C-2 / C-3 bundle or row grade unlike R3d ends the compare stage with exit 3.
 # Run commit R2 = b9f5707 (every --git-at-start). Path 2 outputs are not read. A stop (R19-5 t_lift, R21-1, R22-1,
-# K-10 difference) ends the sequence: run stage by stage and stop on the first one.
-# Before the first run: set $R3dShort, copy view_check.py, td_basis.py, bundle_summary.py, compare_r3c.py and
-# sums_check.py into the R3d folder.
+# R23-1, CD-3 window end, CD-4 P3-6 limit, CD-7, CD-11, K-10 difference) ends the sequence: run stage by stage and
+# stop on the first one.
+# Before the first run: set $R3fShort / $R3fFull, copy view_check.py, td_basis.py, bundle_summary.py and
+# sums_check.py from the R3d folder and compare_r3d.py / allowed_keys_path1.md into the R3f folder.
 # Run:  pwsh -NoProfile -File <this file> -Stage <name>|all
 param([string]$Stage = 'all')
@@ -22,8 +28,17 @@ $Py = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'
 $R2 = 'b9f5707d7f3f7a26230b25f4edbc1fec587ca612'
 $V = Join-Path $Root '06_analysis\02_control\verif_matrix\v5_resume_4368'
-$R3dShort = '0220671'   # change (1): the R3d merge commit short hash, filled in by the main session
-if ($R3dShort -like '<*') ｛ throw 'set $R3dShort to the R3d short hash first' ｝
-$J = Join-Path $V "judge_$R3dShort\chrono_path1"
+$R3fShort = '8a0c843'   # change (1): the R3f merge commit short hash, filled in by the main session
+$R3fFull = '8a0c8432d23c9db0916bf6f9cb9139466bd32551'     # change (6): the R3f merge commit full hash
+if ($R3fShort -like '<*' -or $R3fFull -like '<*') ｛ Write-Output 'set $R3fShort and $R3fFull first'; exit 2 ｝
+$Head = (& git -C $Root rev-parse HEAD).Trim()
+if ($Head -ne $R3fFull -or -not $R3fFull.StartsWith($R3fShort)) ｛   # change (6): rev25 R25-3 checkout check
+    Write-Output "S-12: checkout HEAD $Head is not R3f $R3fFull (rules rev25 R25-3)"
+    exit 2
+｝
+$J = Join-Path $V "judge_$R3fShort\chrono_path1"
 $R3cJ = Join-Path $V 'judge_f9bc3c7\chrono_path1'   # change (2): R3c folder, read only
+$R3dJ = Join-Path $V 'judge_0220671\chrono_path1'   # change (3): R3d folder, read only (comparison basis)
+$SumsSha = @｛ $R3cJ = '12f1f5b4e437f7f552410fc52089cd287df323d437c3adbbdb11a5b18cb8d10c'
+              $R3dJ = '3a1b8a7a69540927bb5be00ec014b9a860bcbe1c19fd97c22af85b1606f41346' ｝   # rev24 R24-3
 $R3J = Join-Path $V 'judge_576eb87\chrono_path1'
 $View = Join-Path $R3J 'chrono_view'
@@ -76,7 +91,16 @@ function Grade-Bundle([string]$Bundle, [string]$Key, [string[]]$Extra) ｛
 ｝
 
-# change (2) / (3): every R3c SHA256SUMS.txt entry before the run (and again in r3c_check_after)
+# change (3): the R3c and R3d SHA256SUMS.txt files (sha256 of the file, then every entry) before the run and again
+# in the *_check_after stage; a difference is S-11 and ends the script with exit 4 (rev25 R25-3: an exit code, not
+# only the log)
+function Check-Sums([string]$Folder, [string]$Id) ｛
+    $sums = (Get-FileHash -Algorithm SHA256 (Join-Path $Folder 'SHA256SUMS.txt')).Hash.ToLower()
+    if ($sums -ne $SumsSha[$Folder]) ｛ Write-Output "S-11: $Folder SHA256SUMS.txt sha256 $sums (rev24 R24-3)"; exit 4 ｝
+    Invoke-Step $Id @('-I', '-B', (Join-Path $J 'sums_check.py'), $Folder, (Join-Path $J "$Id.json"))
+    if ($Codes[$Id] -ne 0) ｛ Write-Output "S-11: $Id found a changed or missing file (rev24 R24-3)"; exit 4 ｝
+｝
 if ($Stage -in 'all', 'r3c_check_before') ｛
-    Invoke-Step 'r3c_check_before' @('-I', '-B', (Join-Path $J 'sums_check.py'), $R3cJ, (Join-Path $J 'r3c_check_before.json'))
+    Check-Sums $R3cJ 'r3c_check_before'
+    Check-Sums $R3dJ 'r3d_check_before'
 ｝
 if ($Stage -in 'all', 'seals_view') ｛
@@ -85,8 +109,8 @@ if ($Stage -in 'all', 'seals_view') ｛
     Invoke-Step 'view_check' @('-I', '-B', (Join-Path $J 'view_check.py'), $View, (Join-Path $J 'view_check.json'))
 ｝
-if ($Stage -in 'all', 'rows_judge') ｛   # change (3): the row-judge re-run with the R3d tool (R22-3 1)
+if ($Stage -in 'all', 'rows_judge') ｛   # the row-judge re-run with the R3f tool; change (4): CD-3 window record
     foreach ($name in $Batches.Keys) ｛
         $arguments = @('-I', '-B', '-X', 'utf8', $Judge, 'judge', '--git-at-start', $R2,
-                       '--out', (Join-Path $J "judge_$name.json"))
+                       '--out', (Join-Path $J "judge_$name.json"), '--runner-judge-dir', $RJ)
         foreach ($b in $Batches[$name]) ｛ $arguments += @('--batch', (Batch $b)) ｝
         Invoke-Step "judge_$name" $arguments
@@ -105,7 +129,4 @@ if ($Stage -in 'all', 'grade_C2C3') ｛
     Grade-Bundle 'C-3' 'C3' @('--rows-judge', (Join-Path $J 'judge_C3.json'), '--runner-judge-dir', $RJ)
 ｝
-if ($Stage -in 'all', 'compare') ｛   # change (3): judge C-1 .. C-8 and bundles C-1 .. C-3 against R3c (K-10)
-    Invoke-Step 'compare_r3c' @('-I', '-B', (Join-Path $J 'compare_r3c.py'), $R3cJ, $J, (Join-Path $J 'compare_r3c.json'))
-｝
 if ($Stage -eq 't45') ｛   # change (2): reused, never re-run
     throw "t45 is reused from $T45Out (rev22 R22-3), not re-run"
@@ -126,5 +147,15 @@ if ($Stage -in 'all', 'records') ｛
     ｝
     Grade-Bundle 'C-8' 'OC5' @('--oc5', (Join-Path $J 'oc5_C-8a.json'), '--oc5', (Join-Path $J 'oc5_C-8b.json'),
-        '--fmin-time', (Join-Path $J 'fmin_C-8a.json'), '--fmin-time', (Join-Path $J 'fmin_C-8b.json'))
+        '--fmin-time', (Join-Path $J 'fmin_C-8a.json'), '--fmin-time', (Join-Path $J 'fmin_C-8b.json'),
+        '--rows-judge', (Join-Path $J 'judge_OC5.json'))   # change (4): CD-8 P3 record values
+    Grade-Bundle 'C-4' 'C4' @('--rows-judge', (Join-Path $J 'judge_C4.json'))   # change (4): CD-9 record bundle
+｝
+if ($Stage -in 'all', 'compare') ｛   # change (5): judge C-1 .. C-8 and every R3d bundle output against R3d (K-10)
+    Invoke-Step 'compare_r3d' @('-I', '-B', (Join-Path $J 'compare_r3d.py'), $R3dJ, $J, (Join-Path $J 'compare_r3d.json'))
+    # change (7), rev25 R25-3: C-1 .. C-3 bundle / row grade differences taken apart; any -> exit 3 at this stage
+    $cmp = Get-Content (Join-Path $J 'compare_r3d.json') -Raw | ConvertFrom-Json -AsHashtable
+    $grades = foreach ($b in 'C1', 'C2', 'C3') ｛ foreach ($g in $cmp['bundle'][$b]['grade_differences']) ｛ "$｛b｝: $g" ｝ ｝
+    $grades | Set-Content -Path (Join-Path $J 'grade_differences_C1_C3.txt') -Encoding utf8
+    if (@($grades).Count -gt 0) ｛ Write-Output "C-1 .. C-3 grade differences: $(@($grades).Count) (stop and ask)"; exit 3 ｝
 ｝
 if ($Stage -in 'all', 'k1view') ｛
@@ -142,6 +173,7 @@ if ($Stage -in 'all', 'k1view') ｛
         @('--out', (Join-Path $J 'record_check_chrono_view.json')))
 ｝
-if ($Stage -in 'all', 'r3c_check_after') ｛   # change (3): the R3c folder unchanged after the run
-    Invoke-Step 'r3c_check_after' @('-I', '-B', (Join-Path $J 'sums_check.py'), $R3cJ, (Join-Path $J 'r3c_check_after.json'))
+if ($Stage -in 'all', 'r3c_check_after') ｛   # change (3): the R3c and R3d folders unchanged after the run
+    Check-Sums $R3cJ 'r3c_check_after'
+    Check-Sums $R3dJ 'r3d_check_after'
 ｝
 Write-Output "stage $Stage done"
```

### 경로 1 실행 스크립트, R3e 판(실행 안 함) → R3f

- 앞 판 `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\7ea6ef9d-fc13-4bf1-8179-0167f32d78a7\scratchpad\p1r3e\run_path1_r3e.ps1` sha256 `0cf38f5ec2e4dca66d53e861fe02322f6dbf75e3872cdfe5c6debf6cec27f41f`
- R3f `C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\judge_8a0c843\chrono_path1\run_path1_r3f.ps1` sha256 `faf01f0e2451550685957e1b41b61551889534094b0b368a13d84877fc8bbbfc`
- 1 file changed, 32 insertions(+), 15 deletions(-)

```diff
diff --git "a/C:\\Users\\jinbeom\\AppData\\Local\\Temp\\claude\\63917d480778c1ba\\7ea6ef9d-fc13-4bf1-8179-0167f32d78a7\\scratchpad\\p1r3e\\run_path1_r3e.ps1" "b/C:\\workspace\\outrigger_control\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\judge_8a0c843\\chrono_path1\\run_path1_r3f.ps1"
index b629783..eb27c35 100644
--- "a/C:\\Users\\jinbeom\\AppData\\Local\\Temp\\claude\\63917d480778c1ba\\7ea6ef9d-fc13-4bf1-8179-0167f32d78a7\\scratchpad\\p1r3e\\run_path1_r3e.ps1"
+++ "b/C:\\workspace\\outrigger_control\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\judge_8a0c843\\chrono_path1\\run_path1_r3f.ps1"
@@ -1,14 +1,18 @@
 #Requires -Version 7.2
-# 436.8 R3e Chrono judgement, path 1 (python-expert, 2026-11-15; DRAFT, not run). Copy of run_path1_r3d.ps1
-# (judge_0220671) with the changes rules rev24 R24-3 allows: (1) the output folder is judge_<R3e short hash>;
-# (2) the reused inputs stay in the R3c folder (runner_judge\, t45_C5.json, R3c judge_C5.json, run_path1_r3c.ps1);
-# (3) R3c and R3d before / after checks (each SHA256SUMS.txt file sha256 and every entry; nothing is written there);
+# 436.8 R3f Chrono judgement, path 1 (python-expert, 2026-11-16; DRAFT, not run). Copy of the unrun R3e draft
+# run_path1_r3e.ps1, itself a copy of run_path1_r3d.ps1 (judge_0220671), with the changes rules rev24 R24-3 and
+# rev25 R25-3 allow: (1) the output folder is judge_<R3f short hash>; (2) the reused inputs stay in the R3c folder
+# (runner_judge\, t45_C5.json, R3c judge_C5.json, run_path1_r3c.ps1); (3) R3c and R3d before / after checks (each
+# SHA256SUMS.txt file sha256 and every entry; nothing is written there; a failure ends the script with exit 4);
 # (4) the new steps the rev24 tools need (R24-2): --runner-judge-dir for the row judge (CD-3 window end difference),
-# the C-4 record bundle (CD-9) and --rows-judge for C-8 (CD-8 P3 values); (5) the K-10 comparison against R3d with
-# the CD-10 / CD-7 keys left out and the pre-registered allowed keys (compare_r3d.py, allowed_keys_path1.md).
+# the C-4 record bundle (CD-9) and --rows-judge for C-8 (CD-8 values); (5) the K-10 comparison against R3d with the
+# CD-10 / CD-7 keys left out and the pre-registered allowed keys (compare_r3d.py, allowed_keys_path1.md);
+# (6, rev25 R25-3) the run checkout check: `git rev-parse HEAD` must be the full R3f hash, else S-12 and exit 2;
+# (7, rev25 R25-3) a C-1 / C-2 / C-3 bundle or row grade unlike R3d ends the compare stage with exit 3.
 # Run commit R2 = b9f5707 (every --git-at-start). Path 2 outputs are not read. A stop (R19-5 t_lift, R21-1, R22-1,
-# R23-1, CD-3 window end, CD-7, CD-11, K-10 difference) ends the sequence: run stage by stage, stop on the first one.
-# Before the first run: set $R3eShort, copy view_check.py, td_basis.py, bundle_summary.py and sums_check.py from the
-# R3d folder and compare_r3d.py / allowed_keys_path1.md into the R3e folder.
+# R23-1, CD-3 window end, CD-4 P3-6 limit, CD-7, CD-11, K-10 difference) ends the sequence: run stage by stage and
+# stop on the first one.
+# Before the first run: set $R3fShort / $R3fFull, copy view_check.py, td_basis.py, bundle_summary.py and
+# sums_check.py from the R3d folder and compare_r3d.py / allowed_keys_path1.md into the R3f folder.
 # Run:  pwsh -NoProfile -File <this file> -Stage <name>|all
 param([string]$Stage = 'all')
@@ -24,7 +28,13 @@ $Py = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'
 $R2 = 'b9f5707d7f3f7a26230b25f4edbc1fec587ca612'
 $V = Join-Path $Root '06_analysis\02_control\verif_matrix\v5_resume_4368'
-$R3eShort = '<R3E_SHORT>'   # change (1): the R3e merge commit short hash, filled in by the main session
-if ($R3eShort -like '<*') ｛ throw 'set $R3eShort to the R3e short hash first' ｝
-$J = Join-Path $V "judge_$R3eShort\chrono_path1"
+$R3fShort = '8a0c843'   # change (1): the R3f merge commit short hash, filled in by the main session
+$R3fFull = '8a0c8432d23c9db0916bf6f9cb9139466bd32551'     # change (6): the R3f merge commit full hash
+if ($R3fShort -like '<*' -or $R3fFull -like '<*') ｛ Write-Output 'set $R3fShort and $R3fFull first'; exit 2 ｝
+$Head = (& git -C $Root rev-parse HEAD).Trim()
+if ($Head -ne $R3fFull -or -not $R3fFull.StartsWith($R3fShort)) ｛   # change (6): rev25 R25-3 checkout check
+    Write-Output "S-12: checkout HEAD $Head is not R3f $R3fFull (rules rev25 R25-3)"
+    exit 2
+｝
+$J = Join-Path $V "judge_$R3fShort\chrono_path1"
 $R3cJ = Join-Path $V 'judge_f9bc3c7\chrono_path1'   # change (2): R3c folder, read only
 $R3dJ = Join-Path $V 'judge_0220671\chrono_path1'   # change (3): R3d folder, read only (comparison basis)
@@ -82,9 +92,11 @@ function Grade-Bundle([string]$Bundle, [string]$Key, [string[]]$Extra) ｛
 
 # change (3): the R3c and R3d SHA256SUMS.txt files (sha256 of the file, then every entry) before the run and again
-# in the *_check_after stage; a difference is S-11
+# in the *_check_after stage; a difference is S-11 and ends the script with exit 4 (rev25 R25-3: an exit code, not
+# only the log)
 function Check-Sums([string]$Folder, [string]$Id) ｛
     $sums = (Get-FileHash -Algorithm SHA256 (Join-Path $Folder 'SHA256SUMS.txt')).Hash.ToLower()
-    if ($sums -ne $SumsSha[$Folder]) ｛ throw "S-11: $Folder SHA256SUMS.txt sha256 $sums (rev24 R24-3)" ｝
+    if ($sums -ne $SumsSha[$Folder]) ｛ Write-Output "S-11: $Folder SHA256SUMS.txt sha256 $sums (rev24 R24-3)"; exit 4 ｝
     Invoke-Step $Id @('-I', '-B', (Join-Path $J 'sums_check.py'), $Folder, (Join-Path $J "$Id.json"))
+    if ($Codes[$Id] -ne 0) ｛ Write-Output "S-11: $Id found a changed or missing file (rev24 R24-3)"; exit 4 ｝
 ｝
 if ($Stage -in 'all', 'r3c_check_before') ｛
@@ -97,5 +109,5 @@ if ($Stage -in 'all', 'seals_view') ｛
     Invoke-Step 'view_check' @('-I', '-B', (Join-Path $J 'view_check.py'), $View, (Join-Path $J 'view_check.json'))
 ｝
-if ($Stage -in 'all', 'rows_judge') ｛   # the row-judge re-run with the R3e tool; change (4): CD-3 window record
+if ($Stage -in 'all', 'rows_judge') ｛   # the row-judge re-run with the R3f tool; change (4): CD-3 window record
     foreach ($name in $Batches.Keys) ｛
         $arguments = @('-I', '-B', '-X', 'utf8', $Judge, 'judge', '--git-at-start', $R2,
@@ -141,4 +153,9 @@ if ($Stage -in 'all', 'records') ｛
 if ($Stage -in 'all', 'compare') ｛   # change (5): judge C-1 .. C-8 and every R3d bundle output against R3d (K-10)
     Invoke-Step 'compare_r3d' @('-I', '-B', (Join-Path $J 'compare_r3d.py'), $R3dJ, $J, (Join-Path $J 'compare_r3d.json'))
+    # change (7), rev25 R25-3: C-1 .. C-3 bundle / row grade differences taken apart; any -> exit 3 at this stage
+    $cmp = Get-Content (Join-Path $J 'compare_r3d.json') -Raw | ConvertFrom-Json -AsHashtable
+    $grades = foreach ($b in 'C1', 'C2', 'C3') ｛ foreach ($g in $cmp['bundle'][$b]['grade_differences']) ｛ "$｛b｝: $g" ｝ ｝
+    $grades | Set-Content -Path (Join-Path $J 'grade_differences_C1_C3.txt') -Encoding utf8
+    if (@($grades).Count -gt 0) ｛ Write-Output "C-1 .. C-3 grade differences: $(@($grades).Count) (stop and ask)"; exit 3 ｝
 ｝
 if ($Stage -in 'all', 'k1view') ｛
```

### 경로 1 비교기, R3d 판 `compare_r3c.py`(고친 사본) → R3f `compare_r3d.py`

- 앞 판 `C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\judge_0220671\chrono_path1\compare_r3c.py` sha256 `c19aa68b73d9333a0c3af4ff0fdb943c4c501354b21f3a7f5ea8e13749fe9cab`
- R3f `C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\judge_8a0c843\chrono_path1\compare_r3d.py` sha256 `0e8fad4a063437011eda2dcd7ffc646c8b565b0dcc3be8ee9ed804e2006eb53b`
- 1 file changed, 114 insertions(+), 45 deletions(-)

```diff
diff --git "a/C:\\workspace\\outrigger_control\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\judge_0220671\\chrono_path1\\compare_r3c.py" "b/C:\\workspace\\outrigger_control\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\judge_8a0c843\\chrono_path1\\compare_r3d.py"
index ab1c10c..62d8448 100644
--- "a/C:\\workspace\\outrigger_control\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\judge_0220671\\chrono_path1\\compare_r3c.py"
+++ "b/C:\\workspace\\outrigger_control\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\judge_8a0c843\\chrono_path1\\compare_r3d.py"
@@ -1,18 +1,24 @@
-"""R3c vs R3d comparison of the path 1 Chrono outputs (rules rev22 R22-3, original 9.2 K-10;
-python-expert 2026-11-15, draft for run_path1_r3d.ps1).
-
-* ``judge_<B>.json`` (chrono_rows_judge, C-1 .. C-8): K-10 form without ``tool``, ``rules``,
-  ``seals`` and the ``disclosure`` block (R22-3 keys of path 1).
-* ``bundle_<B>.json`` (chrono_bundle_grade, C-1 .. C-3): K-10 form without ``tool``, ``rules``,
-  ``seals``, the pairing record ``t45_pairing_R22_1``, the name record ``runner_name_map_R23_1``
-  (rev23 R23-3) and ``inputs.rows_judge.path`` / ``inputs.rows_judge.sha256``;
-  ``inputs.rows_judge_tool`` and ``inputs.runner_judge_dir`` stay.
+"""R3d vs R3f comparison of the path 1 Chrono outputs (rules rev24 R24-3 re-judgement 2 as kept by
+rev25 R25-3, original 9.2 K-10; python-expert 2026-11-16, draft for run_path1_r3f.ps1; the R3e
+draft with the rev25 categories added; "R3e" below means the run being compared, now R3f).
+
+* Left out (as before): ``tool``, ``rules``, ``seals``, ``disclosure`` (judge), the pairing record
+  ``t45_pairing_R22_1``, the name record ``runner_name_map_R23_1`` and ``inputs.rows_judge.path``
+  / ``.sha256`` (bundle).
+* Left out (rules rev24 CD-10 run identity, CD-7 reason text): the keys of :data:`REASON_KEYS` at
+  any depth and the ``reasons_CD_7`` block. Run identity of path 1 = ``inputs.rows_judge.path``
+  (output folder) and ``disclosure`` (checkout); neither output records a run time.
+* A remaining difference is allowed when its key path is under a pattern of :data:`ALLOWED` (the
+  pre-registered key list ``allowed_keys_path1.md``); any other difference fails.
+* Always fails, allowed or not: a different C-1 / C-2 / C-3 bundle grade (``bundle_grade.grade``,
+  ``status``, ``grade_without_stop``) or row grade (``rows[].grade``).
+* An R3d output missing in R3e is S-15; ``bundle_C4.json`` is new in R3e (listed, not compared).
 K-10: grades, booleans, lists, counts and classes equal; numbers within 1e-9 * max(1, |a|, |b|).
-A bundle output missing on either side is S-15 (R22-3 1).
 
-Usage: python -I -B compare_r3c.py <R3c folder> <R3d folder> <out.json>
-Exit codes: 0 all equal, 1 a difference or a missing output.
+Usage: python -I -B compare_r3d.py <R3d folder> <R3e folder> <out.json>
+Exit codes: 0 no failing difference, 1 a failing difference or a missing output.
 """
 
+import fnmatch
 import hashlib
 import json
@@ -22,11 +28,42 @@ from pathlib import Path
 
 JUDGE_BUNDLES = ("C1", "C2", "C3", "C4", "C5", "C6C7", "OC5PROBE", "OC5")
-GRADE_BUNDLES = ("C1", "C2", "C3")
+GRADE_BUNDLES = ("C1", "C2", "C3", "C5", "C6C7", "OC5")
+"""Bundle outputs R3d wrote (all compared)."""
+NEW_BUNDLES = ("C4",)
+"""Bundle outputs new in R3e (rules rev24 CD-9): listed, not compared (R24-3 re-judgement 3)."""
+GRADE_GUARDED = ("C1", "C2", "C3")
 JUDGE_IGNORED = ｛("tool",), ("rules",), ("seals",), ("disclosure",)｝
 BUNDLE_IGNORED = ｛("tool",), ("rules",), ("seals",), ("t45_pairing_R22_1",),
-                  ("runner_name_map_R23_1",),
+                  ("runner_name_map_R23_1",), ("reasons_CD_7",),
                   ("inputs", "rows_judge", "path"), ("inputs", "rows_judge", "sha256")｝
+REASON_KEYS = ("reason", "override_reason", "grade_reason", "record_reason",
+               "reason_not_judgeable", "gate_reasons_CD_5", "condition_note")
+"""Rules rev24 CD-7 reason text keys (CD-10: left out of K-10 at any depth)."""
+ALLOWED = ｛
+    # CD-3 event rows (C-5 whole bundle) and the event test record of every L2b row
+    "judge_C5.json": ["rows.#.items.moving_pressure_D-32*", "rows.#.items.ready_D-27_D-28.*"],
+    "judge_C1.json": ["rows.#.items.moving_pressure_D-32.event_test_CD_3*"],
+    "judge_C2.json": ["rows.#.items.moving_pressure_D-32.event_test_CD_3*",
+                      "rows.#.items.ready_D-27_D-28.P3-6",
+                      "rows.#.items.ready_D-27_D-28.ready_reached"],
+    # C-5 whole bundle (rules rev24 R24-3 re-judgement 2)
+    "bundle_C5.json": ["*"],
+    # CD-2 re-computed item values, CD-5 READY missing items, CD-11 item list (C-1 .. C-3)
+    "bundle_C1.json": ["item_list_CD_11*", "rows.#.overrides.#*", "rows.#.runner_items.#*"],
+    # rev25 R25-3: CD-4 P3-6 role / limit and CD-11 P3-9 record move items between items and
+    # record_items (C-2 PS-c base row, 427.9 rows); CD-5 P3-6 lines of the recorded rows
+    "bundle_C2.json": ["item_list_CD_11*", "rows.#.overrides.#*", "rows.#.runner_items.#*",
+                       "rows.#.items", "rows.#.items.#*", "rows.#.record_items",
+                       "rows.#.record_items.#*"],
+    "bundle_C3.json": ["item_list_CD_11*"],
+    # CD-8 C-8 record values, record status and the new rows-judge input
+    "bundle_OC5.json": ["rows.#.record_values_CD_8*", "rows.#.complete", "rows.#.missing_inputs*",
+                        "rows.#.inputs_sha256*", "record_status", "inputs.rows_judge",
+                        "inputs.rows_judge_tool"],
+｝
+"""Pre-registered allowed difference keys (``allowed_keys_path1.md``); ``#`` = any list index,
+fnmatch patterns on the dotted path."""
 REL_TOL = 1e-9
-MAX_LISTED = 60
+MAX_LISTED = 200
 
 
@@ -39,23 +76,27 @@ def is_number(value) -> bool:
 
 
-def compare(a, b, path: tuple, ignored: set, out: list[str]) -> None:
-    """K-10: append the dotted paths where ``a`` and ``b`` differ (``ignored`` key paths out)."""
-    if len(out) >= MAX_LISTED or path in ignored:
+def dotted(path: tuple) -> str:
+    return ".".join("#" if isinstance(p, int) else str(p) for p in path) or "(top)"
+
+
+def compare(a, b, path: tuple, ignored: set, out: list[tuple[str, str]]) -> None:
+    """K-10: append (pattern path, text) where ``a`` and ``b`` differ (ignored keys out)."""
+    if len(out) >= MAX_LISTED or path in ignored or (path and path[-1] in REASON_KEYS):
         return
-    name = ".".join(str(p) for p in path) or "(top)"
+    name = dotted(path)
     if is_number(a) and is_number(b):
         if math.isfinite(a) and math.isfinite(b):
             if abs(a - b) > REL_TOL * max(1.0, abs(a), abs(b)):
-                out.append(f"｛name｝: ｛a｝ != ｛b｝")
+                out.append((name, f"｛a｝ != ｛b｝"))
         elif a != b:
-            out.append(f"｛name｝: ｛a｝ != ｛b｝")
+            out.append((name, f"｛a｝ != ｛b｝"))
         return
     if isinstance(a, dict) and isinstance(b, dict):
         for key in sorted(set(a) | set(b)):
             sub = (*path, key)
-            if sub in ignored:
+            if sub in ignored or key in REASON_KEYS:
                 continue
             if key not in a or key not in b:
-                out.append(f"｛name｝.｛key｝: present only in ｛'R3c' if key in a else 'R3d'｝")
+                out.append((dotted(sub), f"present only in ｛'R3d' if key in a else 'R3e'｝"))
                 continue
             compare(a[key], b[key], sub, ignored, out)
@@ -63,5 +104,5 @@ def compare(a, b, path: tuple, ignored: set, out: list[str]) -> None:
     if isinstance(a, list) and isinstance(b, list):
         if len(a) != len(b):
-            out.append(f"｛name｝: list length ｛len(a)｝ != ｛len(b)｝")
+            out.append((name, f"list length ｛len(a)｝ != ｛len(b)｝"))
             return
         for index, (x, y) in enumerate(zip(a, b, strict=True)):
@@ -69,35 +110,63 @@ def compare(a, b, path: tuple, ignored: set, out: list[str]) -> None:
         return
     if a != b:
-        out.append(f"｛name｝: ｛str(a)[:80]!r｝ != ｛str(b)[:80]!r｝")
+        out.append((name, f"｛str(a)[:60]!r｝ != ｛str(b)[:60]!r｝"))
+
+
+def is_allowed(name: str, patterns: list[str]) -> bool:
+    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)
+
+
+def grade_differences(old: dict, new: dict) -> list[str]:
+    """C-1 .. C-3 bundle and row grades that differ (a stop whatever the allowed list says)."""
+    found = []
+    for key in ("grade", "status", "grade_without_stop"):
+        if (old.get("bundle_grade") or ｛｝).get(key) != (new.get("bundle_grade") or ｛｝).get(key):
+            found.append(f"bundle_grade.｛key｝")
+    old_rows = ｛r.get("case"): r.get("grade") for r in old.get("rows") or []｝
+    new_rows = ｛r.get("case"): r.get("grade") for r in new.get("rows") or []｝
+    found += [f"rows[｛case｝].grade" for case in sorted(set(old_rows) | set(new_rows))
+              if old_rows.get(case) != new_rows.get(case)]
+    return found
 
 
-def compare_files(old: Path, new: Path, ignored: set) -> dict:
+def compare_files(old: Path, new: Path, ignored: set, *, guarded: bool) -> dict:
     if not old.is_file() or not new.is_file():
-        return ｛"present": ｛"R3c": old.is_file(), "R3d": new.is_file()｝, "k10_equal": False,
-                "stop": "S-15: output missing on one side (rev22 R22-3 1)"｝
-    diffs: list[str] = []
-    compare(json.loads(old.read_text(encoding="utf-8")),
-            json.loads(new.read_text(encoding="utf-8")), (), ignored, diffs)
-    return ｛"r3c_sha256": sha256(old), "r3d_sha256": sha256(new), "k10_equal": not diffs,
-            "differences": diffs｝
+        return ｛"present": ｛"R3d": old.is_file(), "R3e": new.is_file()｝, "ok": False,
+                "stop": "S-15: output missing on one side (rev24 R24-3 re-judgement 3)"｝
+    a = json.loads(old.read_text(encoding="utf-8"))
+    b = json.loads(new.read_text(encoding="utf-8"))
+    diffs: list[tuple[str, str]] = []
+    compare(a, b, (), ignored, diffs)
+    patterns = ALLOWED.get(new.name, [])
+    allowed = [｛"key": k, "diff": t｝ for k, t in diffs if is_allowed(k, patterns)]
+    failing = [｛"key": k, "diff": t｝ for k, t in diffs if not is_allowed(k, patterns)]
+    grades = grade_differences(a, b) if guarded else []
+    return ｛"r3d_sha256": sha256(old), "r3e_sha256": sha256(new),
+            "allowed_differences": allowed, "failing_differences": failing,
+            "grade_differences": grades, "truncated": len(diffs) >= MAX_LISTED,
+            "ok": not failing and not grades and len(diffs) < MAX_LISTED｝
 
 
 def main() -> int:
-    r3c, r3d, out_path = map(Path, sys.argv[1:4])
-    report = ｛"rule": "rev22 R22-3, original 9.2 K-10 (rel 1e-9)",
+    r3d, r3e, out_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
+    report = ｛"rules": "rev24 R24-3 re-judgement 2 / 3, original 9.2 K-10, CD-10, CD-7",
               "judge_ignored": sorted(".".join(p) for p in JUDGE_IGNORED),
               "bundle_ignored": sorted(".".join(p) for p in BUNDLE_IGNORED),
-              "judge": ｛b: compare_files(r3c / f"judge_｛b｝.json", r3d / f"judge_｛b｝.json",
-                                         JUDGE_IGNORED) for b in JUDGE_BUNDLES｝,
-              "bundle": ｛b: compare_files(r3c / f"bundle_｛b｝.json", r3d / f"bundle_｛b｝.json",
-                                          BUNDLE_IGNORED) for b in GRADE_BUNDLES｝｝
-    equal = all(v["k10_equal"] for part in ("judge", "bundle") for v in report[part].values())
-    report["all_equal"] = equal
+              "reason_keys": list(REASON_KEYS), "allowed": ALLOWED,
+              "judge": ｛b: compare_files(r3d / f"judge_｛b｝.json", r3e / f"judge_｛b｝.json",
+                                         JUDGE_IGNORED, guarded=False) for b in JUDGE_BUNDLES｝,
+              "bundle": ｛b: compare_files(r3d / f"bundle_｛b｝.json", r3e / f"bundle_｛b｝.json",
+                                          BUNDLE_IGNORED, guarded=b in GRADE_GUARDED)
+                         for b in GRADE_BUNDLES｝,
+              "new_in_r3e": ｛b: (r3e / f"bundle_｛b｝.json").is_file() for b in NEW_BUNDLES｝｝
+    ok = all(v["ok"] for part in ("judge", "bundle") for v in report[part].values())
+    report["all_ok"] = ok
     out_path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                         encoding="utf-8", newline="\n")
-    print(json.dumps(｛"all_equal": equal,
-                      "judge": ｛k: v["k10_equal"] for k, v in report["judge"].items()｝,
-                      "bundle": ｛k: v["k10_equal"] for k, v in report["bundle"].items()｝｝))
-    return 0 if equal else 1
+    print(json.dumps(｛"all_ok": ok,
+                      "judge": ｛k: v["ok"] for k, v in report["judge"].items()｝,
+                      "bundle": ｛k: v["ok"] for k, v in report["bundle"].items()｝,
+                      "new_in_r3e": report["new_in_r3e"]｝))
+    return 0 if ok else 1
 
 
```

### 경로 1 비교기, R3e 판 → R3f

- 앞 판 `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\7ea6ef9d-fc13-4bf1-8179-0167f32d78a7\scratchpad\p1r3e\compare_r3d.py` sha256 `6ebe4750186a4affd08412f52b184cf33666a19d9627151afab2b1217f30b34e`
- R3f `C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\judge_8a0c843\chrono_path1\compare_r3d.py` sha256 `0e8fad4a063437011eda2dcd7ffc646c8b565b0dcc3be8ee9ed804e2006eb53b`
- 1 file changed, 7 insertions(+), 5 deletions(-)

```diff
diff --git "a/C:\\Users\\jinbeom\\AppData\\Local\\Temp\\claude\\63917d480778c1ba\\7ea6ef9d-fc13-4bf1-8179-0167f32d78a7\\scratchpad\\p1r3e\\compare_r3d.py" "b/C:\\workspace\\outrigger_control\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\judge_8a0c843\\chrono_path1\\compare_r3d.py"
index 6592155..62d8448 100644
--- "a/C:\\Users\\jinbeom\\AppData\\Local\\Temp\\claude\\63917d480778c1ba\\7ea6ef9d-fc13-4bf1-8179-0167f32d78a7\\scratchpad\\p1r3e\\compare_r3d.py"
+++ "b/C:\\workspace\\outrigger_control\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\judge_8a0c843\\chrono_path1\\compare_r3d.py"
@@ -1,4 +1,5 @@
-"""R3d vs R3e comparison of the path 1 Chrono outputs (rules rev24 R24-3 re-judgement 2, original
-9.2 K-10; python-expert 2026-11-15, draft for run_path1_r3e.ps1; derived from compare_r3c.py).
+"""R3d vs R3f comparison of the path 1 Chrono outputs (rules rev24 R24-3 re-judgement 2 as kept by
+rev25 R25-3, original 9.2 K-10; python-expert 2026-11-16, draft for run_path1_r3f.ps1; the R3e
+draft with the rev25 categories added; "R3e" below means the run being compared, now R3f).
 
 * Left out (as before): ``tool``, ``rules``, ``seals``, ``disclosure`` (judge), the pairing record
@@ -50,8 +51,9 @@ ALLOWED = ｛
     # CD-2 re-computed item values, CD-5 READY missing items, CD-11 item list (C-1 .. C-3)
     "bundle_C1.json": ["item_list_CD_11*", "rows.#.overrides.#*", "rows.#.runner_items.#*"],
+    # rev25 R25-3: CD-4 P3-6 role / limit and CD-11 P3-9 record move items between items and
+    # record_items (C-2 PS-c base row, 427.9 rows); CD-5 P3-6 lines of the recorded rows
     "bundle_C2.json": ["item_list_CD_11*", "rows.#.overrides.#*", "rows.#.runner_items.#*",
-                       "rows.#.record_items.#.verdict_recorded", "rows.#.record_items.#.value",
-                       "rows.#.record_items.#.status", "rows.#.record_items.#.source",
-                       "rows.#.record_items.#.crawler_zero_after_ready"],
+                       "rows.#.items", "rows.#.items.#*", "rows.#.record_items",
+                       "rows.#.record_items.#*"],
     "bundle_C3.json": ["item_list_CD_11*"],
     # CD-8 C-8 record values, record status and the new rows-judge input
```

### 경로 2 실행 스크립트, R3d 판 → R3f

- 앞 판 `C:\workspace\_resume_4368_20261115\p2r3d_0220671\run_path2_r3d.ps1` sha256 `5573b96407fa14165e72bb3b0f014418706bc9e816afa814efb0f3acc81971b8`
- R3f `C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\judge_8a0c843\chrono_path2\run_path2_r3f.ps1` sha256 `61cf51b2f62e624375290176efe88c1b0b8212f8c39cf5625c78c3991929a182`
- 1 file changed, 147 insertions(+), 41 deletions(-)

```diff
diff --git "a/C:\\workspace\\_resume_4368_20261115\\p2r3d_0220671\\run_path2_r3d.ps1" "b/C:\\workspace\\outrigger_control\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\judge_8a0c843\\chrono_path2\\run_path2_r3f.ps1"
index dd8d53c..14c79c3 100644
--- "a/C:\\workspace\\_resume_4368_20261115\\p2r3d_0220671\\run_path2_r3d.ps1"
+++ "b/C:\\workspace\\outrigger_control\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\judge_8a0c843\\chrono_path2\\run_path2_r3f.ps1"
@@ -1,21 +1,33 @@
-# DRAFT - NOT RUN. Path-2 Chrono re-judgement of the 436.8 bundles with the R3d tool (rev22 R22-3 3, 4).
-# Replace 0220671 with the 7-digit R3d merge commit and 02206710fe9ea77088d466f8a486afd5e130bceb with its full hash before running; the
-# script stops if either placeholder is left. git_at_start = R2 b9f5707 (as R3c).
-# Outputs go to a NEW folder judge_0220671\chrono_path2 ; the R3c folder judge_f9bc3c7\chrono_path2 is only read.
-# Steps: 0 R3c outputs.sha256 check (file sha and every entry, S-11) -> 1 seal -> 2 synthetic self test -> 3 E-7
-# tool run (new folder) -> 4 judge C-1..C-8 with the R3c t45 replay output (not rebuilt, R22-3 2) -> 5 G-S load
-# -> 6..8 p2_4368 seal / chrono / oc5k / openloop -> 9 R3c outputs.sha256 check again (S-11) -> 10 K-10 per bundle
-# (k10_compare_r3d.py, R22-3 4; missing side = S-15) -> 11 outputs.sha256 of the new folder.
+# DRAFT - NOT RUN. Path-2 Chrono re-judgement of the 436.8 bundles with the R3f tool (rev25 R25-3; R3e not run).
+# Replace <R3F_SHORT> with the 7-digit R3f merge commit and <R3F_FULL> with its full hash before running; the
+# script stops if either placeholder is left. git_at_start = R2 b9f5707 (as R3c / R3d).
+# Outputs go to a NEW folder judge_<R3F_SHORT>\chrono_path2 ; the R3c (judge_f9bc3c7) and R3d (judge_0220671) path 2
+# folders are only read.
+# Exit codes (rev25 R25-3 "실행 스크립트"): 2 = stopped before judging (placeholders, S-12 checkout is not R3f,
+# S-11 list or judge-code check, S-15 folder count); 4 = C-1 / C-2 / C-3 bundle or row grade differs from R3d
+# (stops at that step); 5 = the R3c / R3d lists differ after the run; 0 = otherwise.
+# Steps: 0 R3c and R3d outputs.sha256 checks (file sha and every entry, S-11) + R3d run log sha -> 0b CD-2 (1)
+# original judge code = b9f5707 (S-11) -> 1 seal -> 2 synthetic self test -> 3 E-7 tool run (new folder)
+# -> 3b original judge (run_S8C.py judge) on the S8 folders of the C-1 / C-2 / C-5 L2b rows into the new folder
+# (CD-2 (1)-(3)) -> 4 judge C-1..C-8 (C-1 / C-2 / C-5 with --s8c-dir, C-8 with --r3d-c8; R3c t45 replay output read,
+# not rebuilt) -> 5 G-S load -> 6..8 p2_4368 seal / chrono / oc5k / openloop -> 9 R3c and R3d outputs.sha256
+# checks again (S-11) -> 10 K-10 per bundle vs R3d (k10_compare_r3f.py: CD-10 run identity keys, output-path elements
+# of argument lists and CD-7 reason keys excluded; missing side = S-15) -> 10b C-1..C-3 grade change check (exit 4)
+# -> 11 outputs.sha256 of the new folder -> exit 5 if the after-run list check failed.
 $ErrorActionPreference = 'Continue'
-$R3D_SHORT = '0220671'
-$R3D_FULL = '02206710fe9ea77088d466f8a486afd5e130bceb'
-if ($R3D_SHORT -like '<*' -or $R3D_FULL -like '<*') ｛ Write-Error 'placeholders not replaced'; exit 2 ｝
+$R3F_SHORT = '8a0c843'
+$R3F_FULL = '8a0c8432d23c9db0916bf6f9cb9139466bd32551'
+if ($R3F_SHORT -like '<*' -or $R3F_FULL -like '<*') ｛ Write-Error 'placeholders not replaced'; exit 2 ｝
 $repo = 'C:\workspace\outrigger_control'
 $R2 = 'b9f5707d7f3f7a26230b25f4edbc1fec587ca612'
 $vm = "$repo\06_analysis\02_control\verif_matrix\v5_resume_4368"
 $R3C = "$vm\judge_f9bc3c7\chrono_path2"
-$R3C_LIST_SHA = 'bd49fb6b7a95cfa9b9322e9578d678c7fa3637454c624317668469a0b6b6409f'   # rev22 R22-3 2
-$OUT = "$vm\judge_$R3D_SHORT\chrono_path2"
+$R3C_LIST_SHA = 'bd49fb6b7a95cfa9b9322e9578d678c7fa3637454c624317668469a0b6b6409f'   # rev22 R22-3 2 / rev24 R24-3
+$R3D = "$vm\judge_0220671\chrono_path2"
+$R3D_LIST_SHA = '096346c740c171bc10660dd8745587f99794ca39f4d036a15b996fa7775860bb'   # rev24 R24-3 (57 lines)
+$R3D_LIST_LINES = 57
+$OUT = "$vm\judge_$R3F_SHORT\chrono_path2"
 $LOGS = "$OUT\logs"
+$S8C = "$OUT\s8c"                                   # CD-2 (2): the path 2 original-judge outputs
 $pc = "$vm\path2_chrono"
 $t = "$vm\path2\p2_4368.py"
@@ -23,18 +35,22 @@ $s9 = "$repo\07_results\S9"
 $s8 = "$repo\07_results\S8"
 $man = "$vm\chrono_rows_manifest.json"
-$k10 = 'C:\workspace\_resume_4368_20261115\p2r3d\k10_compare_r3d.py'
+$k10 = Join-Path $PSScriptRoot 'k10_compare_r3f.py'
 # Synthetic self-test scratch (about 1.5 GB); removed after step 2 so outputs.sha256 does not cover it.
 $tmp = "$OUT\synth_tmp"
 $conda = 'C:\ProgramData\miniforge3\Scripts\conda.exe'
 $py = @('run', '-n', 'dynamics-dev', 'python', '-I', '-B')
-$log = "$OUT\run_path2_r3d.log"
-if ($OUT -eq $R3C) ｛ Write-Error 'output folder must not be the R3c folder'; exit 2 ｝
+$chrono_py = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'   # original judge env (run_S8C.py)
+$JUDGE_CODE = @('03_src', '04_scripts/02_chrono/run_S8C.py', '04_scripts/02_chrono/run_S6C.py')   # CD-2 (1)
+$log = "$OUT\run_path2_r3f.log"
+if ($OUT -eq $R3C -or $OUT -eq $R3D) ｛ Write-Error 'output folder must not be the R3c / R3d folder'; exit 2 ｝
 if (Test-Path $OUT) ｛ Write-Error "output folder exists: $OUT"; exit 2 ｝
 if (-not $PSCommandPath) ｛ Write-Error 'run this as a script file (pwsh -File), not pasted'; exit 2 ｝
-New-Item -ItemType Directory -Force $OUT, $LOGS | Out-Null
+New-Item -ItemType Directory -Force $OUT, $LOGS, $S8C | Out-Null
 # Keep the exact script that ran next to its outputs (hashed in step 11).
-Copy-Item -LiteralPath $PSCommandPath "$OUT\run_path2_r3d.ps1"
+Copy-Item -LiteralPath $PSCommandPath "$OUT\run_path2_r3f.ps1"
 "script $PSCommandPath sha256 $((Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath).Hash.ToLower())" |
   Tee-Object -FilePath $log -Append | Out-Host
+"k10 comparator $k10 sha256 $((Get-FileHash -Algorithm SHA256 -LiteralPath $k10).Hash.ToLower())" |
+  Tee-Object -FilePath $log -Append | Out-Host
 if (Test-Path $tmp) ｛ Remove-Item -Recurse -Force $tmp ｝
 New-Item -ItemType Directory -Force $tmp | Out-Null
@@ -49,4 +65,6 @@ $BUNDLES = [ordered]@｛
   'C-8'   = @('batch_V5-RESUME-K1-OC5_20261114_210626')
 ｝
+$CD2_BUNDLES = @('C-1', 'C-2', 'C-5')
+$CD2_L2B_ROWS = 32                                  # C-1 6 + C-2 2 + C-5 24 L2b rows (R3d outputs)
 $probe = 'batch_V5-RESUME-K1-OC5PROBE_20261113_215123'
 $gs = 'batch_V5-RESUME-K1-GS_20261113_194755'
@@ -64,32 +82,96 @@ function Run($name, [string[]]$a) ｛
 ｝
 
-function Check-R3C($label) ｛
-  # rev22 R22-3 2 / 3: the R3c list file sha and every entry; any difference = S-11 (stop)
-  $lp = "$R3C\outputs.sha256"
+function Run-Judge($name, [string[]]$a) ｛
+  # CD-2: the original judge in its own env (Chrono-dev), cwd = repo; same logging as Run
+  Push-Location $repo
+  try ｛ $out = & $chrono_py -I -B @a 2>&1; $rc = $LASTEXITCODE ｝ finally ｛ Pop-Location ｝
+  $safe = $name -replace '[^A-Za-z0-9_.-]', '_'
+  $out | Set-Content -Encoding utf8NoBOM "$LOGS\$safe.txt"
+  $last = ($out | Select-Object -Last 1)
+  "[$((Get-Date).ToString('s'))] $name exit=$rc :: $last" | Tee-Object -FilePath $log -Append | Out-Host
+  return $rc
+｝
+
+function Check-List($label, $dir, $want, $lines) ｛
+  # rev24 R24-3: the R3c / R3d list file sha and every entry; any difference = S-11 (stop)
+  $lp = "$dir\outputs.sha256"
   $bad = @()
   if (-not (Test-Path $lp)) ｛ $bad += 'outputs.sha256 missing' ｝
-  elseif ((Get-FileHash -Algorithm SHA256 $lp).Hash.ToLower() -ne $R3C_LIST_SHA) ｛ $bad += 'outputs.sha256 file sha differs' ｝
+  elseif ((Get-FileHash -Algorithm SHA256 $lp).Hash.ToLower() -ne $want) ｛ $bad += 'outputs.sha256 file sha differs' ｝
   else ｛
-    foreach ($ln in Get-Content $lp) ｛
-      if (-not $ln.Trim()) ｛ continue ｝
+    $entries = @(Get-Content $lp | Where-Object ｛ $_.Trim() ｝)
+    if ($lines -and $entries.Count -ne $lines) ｛ $bad += "entries $($entries.Count) != $lines" ｝
+    foreach ($ln in $entries) ｛
       $parts = $ln -split '  ', 2
-      $f = Join-Path $R3C $parts[1]
+      $f = Join-Path $dir $parts[1]
       if (-not (Test-Path $f)) ｛ $bad += "missing $($parts[1])" ｝
       elseif ((Get-FileHash -Algorithm SHA256 $f).Hash.ToLower() -ne $parts[0]) ｛ $bad += "differs $($parts[1])" ｝
     ｝
   ｝
-  "[$((Get-Date).ToString('s'))] R3c outputs.sha256 check ($label): $(if ($bad) ｛ 'S-11 ' + ($bad -join '; ') ｝ else ｛ 'all entries match' ｝)" |
+  "[$((Get-Date).ToString('s'))] $label outputs.sha256 check: $(if ($bad) ｛ 'S-11 ' + ($bad -join '; ') ｝ else ｛ 'all entries match' ｝)" |
     Tee-Object -FilePath $log -Append | Out-Host
   return ($bad.Count -eq 0)
 ｝
 
-"R3d HEAD $(git -C $repo rev-parse HEAD) (expected $R3D_FULL)" | Tee-Object -FilePath $log -Append
-if ((git -C $repo rev-parse HEAD).Trim() -ne $R3D_FULL) ｛ 'S-12: checkout is not R3d' | Tee-Object -FilePath $log -Append; exit 2 ｝
-if (-not (Check-R3C 'before')) ｛ exit 2 ｝
+function Check-Reused($when) ｛
+  $okc = Check-List "R3c ($when)" $R3C $R3C_LIST_SHA 0
+  $okd = Check-List "R3d ($when)" $R3D $R3D_LIST_SHA $R3D_LIST_LINES
+  $rl = "$R3D\run_path2_r3d.log"
+  "[$((Get-Date).ToString('s'))] R3d run log (outside the list) sha256 ($when): $(if (Test-Path $rl) ｛ (Get-FileHash -Algorithm SHA256 $rl).Hash.ToLower() ｝ else ｛ 'missing' ｝)" |
+    Tee-Object -FilePath $log -Append | Out-Host
+  return ($okc -and $okd)
+｝
+
+function Get-GradeDiff($before, $after) ｛
+  # rev25 R25-3 실행 스크립트 (2): C-1 / C-2 / C-3 bundle status and row status differences (one string each)
+  $out = @()
+  foreach ($k in @('C-1', 'C-2', 'C-3')) ｛
+    $n = $k -replace '-', ''
+    $pd, $pf = "$before\p2_$n.json", "$after\p2_$n.json"
+    if (-not (Test-Path $pd) -or -not (Test-Path $pf)) ｛ $out += "$｛k｝: bundle output missing"; continue ｝
+    $d0 = Get-Content -Raw $pd | ConvertFrom-Json
+    $d1 = Get-Content -Raw $pf | ConvertFrom-Json
+    if ($d0.bundle_result.status -ne $d1.bundle_result.status) ｛
+      $out += "$｛k｝: bundle $($d0.bundle_result.status) -> $($d1.bundle_result.status)"
+    ｝
+    $r0 = @｛｝; foreach ($r in $d0.rows) ｛ $r0[$r.case] = $r.status ｝
+    $r1 = @｛｝; foreach ($r in $d1.rows) ｛ $r1[$r.case] = $r.status ｝
+    foreach ($c in (@($r0.Keys) + @($r1.Keys) | Select-Object -Unique)) ｛
+      if ($r0[$c] -ne $r1[$c]) ｛ $out += "$｛k｝ $｛c｝: $($r0[$c]) -> $($r1[$c])" ｝
+    ｝
+  ｝
+  return $out   # unrolled: the caller collects with @(...) (0 elements when nothing differs)
+｝
+
+# rev25 R25-3 실행 스크립트 (1): the checkout must be R3f (full hash), else S-12
+"R3f HEAD $(git -C $repo rev-parse HEAD) (expected $R3F_FULL)" | Tee-Object -FilePath $log -Append
+if ((git -C $repo rev-parse HEAD).Trim() -ne $R3F_FULL) ｛ 'S-12: checkout is not R3f' | Tee-Object -FilePath $log -Append; exit 2 ｝
+if (-not (Check-Reused 'before')) ｛ exit 2 ｝
+
+# 0b. CD-2 (1): the original judge code of this checkout = R2 b9f5707 (diff 0, working tree), else S-11; commit and
+# judge file sha256 recorded (the bundle outputs carry the same record, `cd2_judge_provenance`).
+$jdiff = @(git -C $repo diff --name-only $R2 -- @JUDGE_CODE)
+"[$((Get-Date).ToString('s'))] CD-2 (1) judge code diff vs $R2 : $(if ($jdiff.Count) ｛ 'S-11 ' + ($jdiff -join ', ') ｝ else ｛ 'none' ｝); checkout $(git -C $repo rev-parse HEAD)" |
+  Tee-Object -FilePath $log -Append | Out-Host
+if ($jdiff.Count) ｛ exit 2 ｝
+foreach ($f in @('03_src/outrigger_sim/verify/s8_control.py', '03_src/outrigger_sim/verify/s6_control.py',
+                 '03_src/outrigger_sim/verify/s6_bundle_c.py', '04_scripts/02_chrono/run_S8C.py', '04_scripts/02_chrono/run_S6C.py')) ｛
+  "  judge file $f sha256 $((Get-FileHash -Algorithm SHA256 (Join-Path $repo $f)).Hash.ToLower())" | Tee-Object -FilePath $log -Append | Out-Host
+｝
+# The S8 folders of the L2b rows (read from the R3d outputs, checked by the list above): one judge run per folder.
+$s8dirs = @()
+foreach ($k in $CD2_BUNDLES) ｛
+  $n = $k -replace '-', ''
+  $doc = Get-Content -Raw "$R3D\p2_$n.json" | ConvertFrom-Json
+  $s8dirs += @($doc.rows | Where-Object ｛ $_.engine -eq 'l2b' ｝ | ForEach-Object ｛ Split-Path -Parent $_.folder ｝)
+｝
+$s8dirs = @($s8dirs | Select-Object -Unique)
+"[$((Get-Date).ToString('s'))] CD-2 L2b S8 folders: $($s8dirs.Count) (expected $CD2_L2B_ROWS)" | Tee-Object -FilePath $log -Append | Out-Host
+if ($s8dirs.Count -ne $CD2_L2B_ROWS) ｛ 'S-15: L2b S8 folder count differs' | Tee-Object -FilePath $log -Append; exit 2 ｝
 
 $p = [Diagnostics.Process]::GetCurrentProcess(); $old = $p.ProcessorAffinity
 try ｛
   $p.ProcessorAffinity = [IntPtr]0xFF00
-  # 1. seal (path2_chrono, rev16..rev23)
+  # 1. seal (path2_chrono, rev16..rev25)
   Run '01_p2_chrono_seal' @("$pc\p2_chrono.py", 'seal') | Out-Null
   # 2. synthetic self test (script, not pytest)
@@ -98,7 +180,13 @@ try ｛
   "[$((Get-Date).ToString('s'))] removed synthetic scratch $tmp (result in logs\02_test_p2_synthetic.txt)" |
     Tee-Object -FilePath $log -Append | Out-Host
-  # 3. E-7 tool run on the C-2 PS-c event row (new folder; compared with the R3c e7 output in step 10 as a record)
+  # 3. E-7 tool run on the C-2 PS-c event row (new folder; compared with the R3d e7 output in step 10 as a record)
   Run '03_p2_e7' @("$pc\p2_e7.py", $repo, $OUT, '--git-at-start', $R2, $psc) | Out-Null
-  # 4. judge per bundle; C-5 uses the R3c t45 replay output read-only (rev22 R22-3 2: not rebuilt)
+  # 3b. CD-2 (2): original judge (verify_S8C) per S8 folder into this run's folder only; its summary is not a grade (CD-2 (3))
+  foreach ($d in $s8dirs) ｛
+    $leaf = Split-Path -Leaf $d
+    New-Item -ItemType Directory -Force "$S8C\$leaf" | Out-Null
+    Run-Judge "03b_verify_S8C_$leaf" @("$repo\04_scripts\02_chrono\run_S8C.py", 'judge', '--batch', $d, '--out', "$S8C\$leaf\verify_S8C.json") | Out-Null
+  ｝
+  # 4. judge per bundle; C-5 uses the R3c t45 replay output read-only (rev24 R24-3 / rev25 R25-3 reuse: not rebuilt)
   foreach ($k in $BUNDLES.Keys) ｛
     $n = $k -replace '-', ''
@@ -108,4 +196,6 @@ try ｛
     if ($k -eq 'C-2') ｛ $a += @('--aux', "e7=$OUT\e7_path2.json") ｝
     if ($k -eq 'C-5') ｛ $a += @('--aux', "t45=$R3C\t45\t45_path2.json") ｝
+    if ($CD2_BUNDLES -contains $k) ｛ $a += @('--s8c-dir', $S8C) ｝
+    if ($k -eq 'C-8') ｛ $a += @('--r3d-c8', "$R3D\p2_C8.json") ｝
     Run "04_p2_chrono_judge_$n" $a | Out-Null
   ｝
@@ -126,25 +216,41 @@ try ｛
 ｝ finally ｛ $p.ProcessorAffinity = $old ｝
 
-# 9. R3c outputs.sha256 again (after the re-judgement), S-11 on any difference
-$after = Check-R3C 'after'
+# 9. R3c and R3d outputs.sha256 again (after the re-judgement), S-11 on any difference
+$after = Check-Reused 'after'
 
-# 10. K-10 per bundle (rev22 R22-3 4): p2_C*.json must exist on both sides (else S-15); p2h_* and e7 as records
+# 10. K-10 per bundle vs R3d (rev24 R24-3 / rev25 R25-3 재판정 2 / 3): p2_C*.json must exist on both sides (else
+# S-15); p2h_* and e7 as records. The comparator drops the output-path elements of argument lists (rev25 (다),
+# --out-dir of both runs). Differences are then sorted against the pre-written allowed key list (판정서).
 $cmp = "$OUT\k10"
 New-Item -ItemType Directory -Force $cmp | Out-Null
+$outdirs = @('--out-dir', $R3D, '--out-dir', $OUT)
 $k10rc = @｛｝
 foreach ($k in $BUNDLES.Keys) ｛
   $n = $k -replace '-', ''
-  $k10rc[$k] = Run "10_k10_$n" @($k10, "$R3C\p2_$n.json", "$OUT\p2_$n.json", '--out', "$cmp\k10_p2_$n.json")
+  $k10rc[$k] = Run "10_k10_$n" (@($k10, "$R3D\p2_$n.json", "$OUT\p2_$n.json", '--out', "$cmp\k10_p2_$n.json") + $outdirs)
 ｝
 foreach ($f in @('e7_path2.json', 'gs_load.json', 'p2h_chrono.json', 'p2h_oc5k_C-8a.json', 'p2h_oc5k_C-8b.json', 'p2h_openloop.json')) ｛
-  Run "10_k10_record_$($f -replace '\.json$', '')" @($k10, "$R3C\$f", "$OUT\$f", '--out', "$cmp\k10_record_$f") | Out-Null
+  Run "10_k10_record_$($f -replace '\.json$', '')" (@($k10, "$R3D\$f", "$OUT\$f", '--out', "$cmp\k10_record_$f") + $outdirs) | Out-Null
 ｝
-$summary = foreach ($k in $BUNDLES.Keys) ｛ "$k=" + @｛0 = 'equal'; 1 = 'different (stop and ask)'; 2 = 'missing S-15'｝[[int]$k10rc[$k]] ｝
-"[$((Get-Date).ToString('s'))] K-10 per bundle: $($summary -join ', '); R3c list after: $(if ($after) ｛ 'match' ｝ else ｛ 'S-11' ｝)" |
+$summary = foreach ($k in $BUNDLES.Keys) ｛ "$k=" + @｛0 = 'equal'; 1 = 'different (sort against the allowed key list)'; 2 = 'missing S-15'｝[[int]$k10rc[$k]] ｝
+"[$((Get-Date).ToString('s'))] K-10 per bundle vs R3d: $($summary -join ', '); R3c / R3d lists after: $(if ($after) ｛ 'match' ｝ else ｛ 'S-11' ｝)" |
   Tee-Object -FilePath $log -Append
 
-# 11. sha256 of every output of the new folder
-Get-ChildItem -Recurse -File $OUT | Where-Object ｛ $_.Name -notin @('run_path2_r3d.log', 'outputs.sha256') ｝ |
+# 10b. rev25 R25-3 실행 스크립트 (2): C-1 / C-2 / C-3 bundle grade and row grades vs R3d; any difference -> exit 4 here
+$gradeDiff = @(Get-GradeDiff $R3D $OUT)
+$gradeDiff | Set-Content -Encoding utf8NoBOM "$cmp\grade_change_C1_C3.txt"
+"[$((Get-Date).ToString('s'))] C-1..C-3 grade change vs R3d: $($gradeDiff.Count)" | Tee-Object -FilePath $log -Append | Out-Host
+if ($gradeDiff.Count) ｛
+  'stop: C-1 / C-2 / C-3 bundle or row grade differs from R3d (rev25 R25-3 재판정): ask before judging' |
+    Tee-Object -FilePath $log -Append | Out-Host
+  exit 4
+｝
+
+# 11. sha256 of every output of the new folder (the original-judge outputs under s8c\ included, CD-2 / R24-2 2)
+Get-ChildItem -Recurse -File $OUT | Where-Object ｛ $_.Name -notin @('run_path2_r3f.log', 'outputs.sha256') ｝ |
   ForEach-Object ｛ "$((Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLower())  $($_.FullName.Substring($OUT.Length + 1))" ｝ |
   Set-Content -Encoding utf8NoBOM "$OUT\outputs.sha256"
 Get-Content "$OUT\outputs.sha256"
+# rev25 R25-3 실행 스크립트: a failed after-run list check is reported by the exit code, not only in the log
+if (-not $after) ｛ 'S-11: R3c / R3d outputs.sha256 differ after the run' | Tee-Object -FilePath $log -Append | Out-Host; exit 5 ｝
+exit 0
```

### 경로 2 실행 스크립트, R3e 판(실행 안 함) → R3f

- 앞 판 `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\7ea6ef9d-fc13-4bf1-8179-0167f32d78a7\scratchpad\p2r3e\run_path2_r3e.ps1` sha256 `a99bcbea9c1b7c88aadf9493b71181a352038f62665633bbc60b4c41dd607b12`
- R3f `C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\judge_8a0c843\chrono_path2\run_path2_r3f.ps1` sha256 `61cf51b2f62e624375290176efe88c1b0b8212f8c39cf5625c78c3991929a182`
- 1 file changed, 62 insertions(+), 21 deletions(-)

```diff
diff --git "a/C:\\Users\\jinbeom\\AppData\\Local\\Temp\\claude\\63917d480778c1ba\\7ea6ef9d-fc13-4bf1-8179-0167f32d78a7\\scratchpad\\p2r3e\\run_path2_r3e.ps1" "b/C:\\workspace\\outrigger_control\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\judge_8a0c843\\chrono_path2\\run_path2_r3f.ps1"
index 408b036..14c79c3 100644
--- "a/C:\\Users\\jinbeom\\AppData\\Local\\Temp\\claude\\63917d480778c1ba\\7ea6ef9d-fc13-4bf1-8179-0167f32d78a7\\scratchpad\\p2r3e\\run_path2_r3e.ps1"
+++ "b/C:\\workspace\\outrigger_control\\06_analysis\\02_control\\verif_matrix\\v5_resume_4368\\judge_8a0c843\\chrono_path2\\run_path2_r3f.ps1"
@@ -1,7 +1,10 @@
-# DRAFT - NOT RUN. Path-2 Chrono re-judgement of the 436.8 bundles with the R3e tool (rev24 R24-3).
-# Replace <R3E_SHORT> with the 7-digit R3e merge commit and <R3E_FULL> with its full hash before running; the
+# DRAFT - NOT RUN. Path-2 Chrono re-judgement of the 436.8 bundles with the R3f tool (rev25 R25-3; R3e not run).
+# Replace <R3F_SHORT> with the 7-digit R3f merge commit and <R3F_FULL> with its full hash before running; the
 # script stops if either placeholder is left. git_at_start = R2 b9f5707 (as R3c / R3d).
-# Outputs go to a NEW folder judge_<R3E_SHORT>\chrono_path2 ; the R3c (judge_f9bc3c7) and R3d (judge_0220671) path 2
+# Outputs go to a NEW folder judge_<R3F_SHORT>\chrono_path2 ; the R3c (judge_f9bc3c7) and R3d (judge_0220671) path 2
 # folders are only read.
+# Exit codes (rev25 R25-3 "실행 스크립트"): 2 = stopped before judging (placeholders, S-12 checkout is not R3f,
+# S-11 list or judge-code check, S-15 folder count); 4 = C-1 / C-2 / C-3 bundle or row grade differs from R3d
+# (stops at that step); 5 = the R3c / R3d lists differ after the run; 0 = otherwise.
 # Steps: 0 R3c and R3d outputs.sha256 checks (file sha and every entry, S-11) + R3d run log sha -> 0b CD-2 (1)
 # original judge code = b9f5707 (S-11) -> 1 seal -> 2 synthetic self test -> 3 E-7 tool run (new folder)
@@ -9,10 +12,11 @@
 # (CD-2 (1)-(3)) -> 4 judge C-1..C-8 (C-1 / C-2 / C-5 with --s8c-dir, C-8 with --r3d-c8; R3c t45 replay output read,
 # not rebuilt) -> 5 G-S load -> 6..8 p2_4368 seal / chrono / oc5k / openloop -> 9 R3c and R3d outputs.sha256
-# checks again (S-11) -> 10 K-10 per bundle vs R3d (k10_compare_r3e.py: CD-10 run identity keys and CD-7 reason
-# keys excluded; missing side = S-15) -> 11 outputs.sha256 of the new folder.
+# checks again (S-11) -> 10 K-10 per bundle vs R3d (k10_compare_r3f.py: CD-10 run identity keys, output-path elements
+# of argument lists and CD-7 reason keys excluded; missing side = S-15) -> 10b C-1..C-3 grade change check (exit 4)
+# -> 11 outputs.sha256 of the new folder -> exit 5 if the after-run list check failed.
 $ErrorActionPreference = 'Continue'
-$R3E_SHORT = '<R3E_SHORT>'
-$R3E_FULL = '<R3E_FULL>'
-if ($R3E_SHORT -like '<*' -or $R3E_FULL -like '<*') ｛ Write-Error 'placeholders not replaced'; exit 2 ｝
+$R3F_SHORT = '8a0c843'
+$R3F_FULL = '8a0c8432d23c9db0916bf6f9cb9139466bd32551'
+if ($R3F_SHORT -like '<*' -or $R3F_FULL -like '<*') ｛ Write-Error 'placeholders not replaced'; exit 2 ｝
 $repo = 'C:\workspace\outrigger_control'
 $R2 = 'b9f5707d7f3f7a26230b25f4edbc1fec587ca612'
@@ -23,5 +27,5 @@ $R3D = "$vm\judge_0220671\chrono_path2"
 $R3D_LIST_SHA = '096346c740c171bc10660dd8745587f99794ca39f4d036a15b996fa7775860bb'   # rev24 R24-3 (57 lines)
 $R3D_LIST_LINES = 57
-$OUT = "$vm\judge_$R3E_SHORT\chrono_path2"
+$OUT = "$vm\judge_$R3F_SHORT\chrono_path2"
 $LOGS = "$OUT\logs"
 $S8C = "$OUT\s8c"                                   # CD-2 (2): the path 2 original-judge outputs
@@ -31,5 +35,5 @@ $s9 = "$repo\07_results\S9"
 $s8 = "$repo\07_results\S8"
 $man = "$vm\chrono_rows_manifest.json"
-$k10 = Join-Path $PSScriptRoot 'k10_compare_r3e.py'
+$k10 = Join-Path $PSScriptRoot 'k10_compare_r3f.py'
 # Synthetic self-test scratch (about 1.5 GB); removed after step 2 so outputs.sha256 does not cover it.
 $tmp = "$OUT\synth_tmp"
@@ -38,5 +42,5 @@ $py = @('run', '-n', 'dynamics-dev', 'python', '-I', '-B')
 $chrono_py = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'   # original judge env (run_S8C.py)
 $JUDGE_CODE = @('03_src', '04_scripts/02_chrono/run_S8C.py', '04_scripts/02_chrono/run_S6C.py')   # CD-2 (1)
-$log = "$OUT\run_path2_r3e.log"
+$log = "$OUT\run_path2_r3f.log"
 if ($OUT -eq $R3C -or $OUT -eq $R3D) ｛ Write-Error 'output folder must not be the R3c / R3d folder'; exit 2 ｝
 if (Test-Path $OUT) ｛ Write-Error "output folder exists: $OUT"; exit 2 ｝
@@ -44,5 +48,5 @@ if (-not $PSCommandPath) ｛ Write-Error 'run this as a script file (pwsh -File),
 New-Item -ItemType Directory -Force $OUT, $LOGS, $S8C | Out-Null
 # Keep the exact script that ran next to its outputs (hashed in step 11).
-Copy-Item -LiteralPath $PSCommandPath "$OUT\run_path2_r3e.ps1"
+Copy-Item -LiteralPath $PSCommandPath "$OUT\run_path2_r3f.ps1"
 "script $PSCommandPath sha256 $((Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath).Hash.ToLower())" |
   Tee-Object -FilePath $log -Append | Out-Host
@@ -119,6 +123,28 @@ function Check-Reused($when) ｛
 ｝
 
-"R3e HEAD $(git -C $repo rev-parse HEAD) (expected $R3E_FULL)" | Tee-Object -FilePath $log -Append
-if ((git -C $repo rev-parse HEAD).Trim() -ne $R3E_FULL) ｛ 'S-12: checkout is not R3e' | Tee-Object -FilePath $log -Append; exit 2 ｝
+function Get-GradeDiff($before, $after) ｛
+  # rev25 R25-3 실행 스크립트 (2): C-1 / C-2 / C-3 bundle status and row status differences (one string each)
+  $out = @()
+  foreach ($k in @('C-1', 'C-2', 'C-3')) ｛
+    $n = $k -replace '-', ''
+    $pd, $pf = "$before\p2_$n.json", "$after\p2_$n.json"
+    if (-not (Test-Path $pd) -or -not (Test-Path $pf)) ｛ $out += "$｛k｝: bundle output missing"; continue ｝
+    $d0 = Get-Content -Raw $pd | ConvertFrom-Json
+    $d1 = Get-Content -Raw $pf | ConvertFrom-Json
+    if ($d0.bundle_result.status -ne $d1.bundle_result.status) ｛
+      $out += "$｛k｝: bundle $($d0.bundle_result.status) -> $($d1.bundle_result.status)"
+    ｝
+    $r0 = @｛｝; foreach ($r in $d0.rows) ｛ $r0[$r.case] = $r.status ｝
+    $r1 = @｛｝; foreach ($r in $d1.rows) ｛ $r1[$r.case] = $r.status ｝
+    foreach ($c in (@($r0.Keys) + @($r1.Keys) | Select-Object -Unique)) ｛
+      if ($r0[$c] -ne $r1[$c]) ｛ $out += "$｛k｝ $｛c｝: $($r0[$c]) -> $($r1[$c])" ｝
+    ｝
+  ｝
+  return $out   # unrolled: the caller collects with @(...) (0 elements when nothing differs)
+｝
+
+# rev25 R25-3 실행 스크립트 (1): the checkout must be R3f (full hash), else S-12
+"R3f HEAD $(git -C $repo rev-parse HEAD) (expected $R3F_FULL)" | Tee-Object -FilePath $log -Append
+if ((git -C $repo rev-parse HEAD).Trim() -ne $R3F_FULL) ｛ 'S-12: checkout is not R3f' | Tee-Object -FilePath $log -Append; exit 2 ｝
 if (-not (Check-Reused 'before')) ｛ exit 2 ｝
 
@@ -147,5 +173,5 @@ $p = [Diagnostics.Process]::GetCurrentProcess(); $old = $p.ProcessorAffinity
 try ｛
   $p.ProcessorAffinity = [IntPtr]0xFF00
-  # 1. seal (path2_chrono, rev16..rev24)
+  # 1. seal (path2_chrono, rev16..rev25)
   Run '01_p2_chrono_seal' @("$pc\p2_chrono.py", 'seal') | Out-Null
   # 2. synthetic self test (script, not pytest)
@@ -162,5 +188,5 @@ try ｛
     Run-Judge "03b_verify_S8C_$leaf" @("$repo\04_scripts\02_chrono\run_S8C.py", 'judge', '--batch', $d, '--out', "$S8C\$leaf\verify_S8C.json") | Out-Null
   ｝
-  # 4. judge per bundle; C-5 uses the R3c t45 replay output read-only (rev24 R24-3 reuse: not rebuilt)
+  # 4. judge per bundle; C-5 uses the R3c t45 replay output read-only (rev24 R24-3 / rev25 R25-3 reuse: not rebuilt)
   foreach ($k in $BUNDLES.Keys) ｛
     $n = $k -replace '-', ''
@@ -193,15 +219,17 @@ try ｛
 $after = Check-Reused 'after'
 
-# 10. K-10 per bundle vs R3d (rev24 R24-3 재판정 2 / 3): p2_C*.json must exist on both sides (else S-15); p2h_* and
-# e7 as records. Differences are then sorted against the pre-written allowed key list (판정서, not this script).
+# 10. K-10 per bundle vs R3d (rev24 R24-3 / rev25 R25-3 재판정 2 / 3): p2_C*.json must exist on both sides (else
+# S-15); p2h_* and e7 as records. The comparator drops the output-path elements of argument lists (rev25 (다),
+# --out-dir of both runs). Differences are then sorted against the pre-written allowed key list (판정서).
 $cmp = "$OUT\k10"
 New-Item -ItemType Directory -Force $cmp | Out-Null
+$outdirs = @('--out-dir', $R3D, '--out-dir', $OUT)
 $k10rc = @｛｝
 foreach ($k in $BUNDLES.Keys) ｛
   $n = $k -replace '-', ''
-  $k10rc[$k] = Run "10_k10_$n" @($k10, "$R3D\p2_$n.json", "$OUT\p2_$n.json", '--out', "$cmp\k10_p2_$n.json")
+  $k10rc[$k] = Run "10_k10_$n" (@($k10, "$R3D\p2_$n.json", "$OUT\p2_$n.json", '--out', "$cmp\k10_p2_$n.json") + $outdirs)
 ｝
 foreach ($f in @('e7_path2.json', 'gs_load.json', 'p2h_chrono.json', 'p2h_oc5k_C-8a.json', 'p2h_oc5k_C-8b.json', 'p2h_openloop.json')) ｛
-  Run "10_k10_record_$($f -replace '\.json$', '')" @($k10, "$R3D\$f", "$OUT\$f", '--out', "$cmp\k10_record_$f") | Out-Null
+  Run "10_k10_record_$($f -replace '\.json$', '')" (@($k10, "$R3D\$f", "$OUT\$f", '--out', "$cmp\k10_record_$f") + $outdirs) | Out-Null
 ｝
 $summary = foreach ($k in $BUNDLES.Keys) ｛ "$k=" + @｛0 = 'equal'; 1 = 'different (sort against the allowed key list)'; 2 = 'missing S-15'｝[[int]$k10rc[$k]] ｝
@@ -209,7 +237,20 @@ $summary = foreach ($k in $BUNDLES.Keys) ｛ "$k=" + @｛0 = 'equal'; 1 = 'different
   Tee-Object -FilePath $log -Append
 
+# 10b. rev25 R25-3 실행 스크립트 (2): C-1 / C-2 / C-3 bundle grade and row grades vs R3d; any difference -> exit 4 here
+$gradeDiff = @(Get-GradeDiff $R3D $OUT)
+$gradeDiff | Set-Content -Encoding utf8NoBOM "$cmp\grade_change_C1_C3.txt"
+"[$((Get-Date).ToString('s'))] C-1..C-3 grade change vs R3d: $($gradeDiff.Count)" | Tee-Object -FilePath $log -Append | Out-Host
+if ($gradeDiff.Count) ｛
+  'stop: C-1 / C-2 / C-3 bundle or row grade differs from R3d (rev25 R25-3 재판정): ask before judging' |
+    Tee-Object -FilePath $log -Append | Out-Host
+  exit 4
+｝
+
 # 11. sha256 of every output of the new folder (the original-judge outputs under s8c\ included, CD-2 / R24-2 2)
-Get-ChildItem -Recurse -File $OUT | Where-Object ｛ $_.Name -notin @('run_path2_r3e.log', 'outputs.sha256') ｝ |
+Get-ChildItem -Recurse -File $OUT | Where-Object ｛ $_.Name -notin @('run_path2_r3f.log', 'outputs.sha256') ｝ |
   ForEach-Object ｛ "$((Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLower())  $($_.FullName.Substring($OUT.Length + 1))" ｝ |
   Set-Content -Encoding utf8NoBOM "$OUT\outputs.sha256"
 Get-Content "$OUT\outputs.sha256"
+# rev25 R25-3 실행 스크립트: a failed after-run list check is reported by the exit code, not only in the log
+if (-not $after) ｛ 'S-11: R3c / R3d outputs.sha256 differ after the run' | Tee-Object -FilePath $log -Append | Out-Host; exit 5 ｝
+exit 0
```

### 경로 2 비교기, R3d 판 → R3f

- 앞 판 `C:\workspace\_resume_4368_20261115\p2r3d\k10_compare_r3d.py` sha256 `840c476742ea58eed6c57adf966f1313180e04d26f6f371b46d9a558e6935fa0`
- R3f `C:\workspace\_resume_4368_20261115\p2r3f_8a0c843\k10_compare_r3f.py` sha256 `cc92c5479ef69e63dc7222e0b42914100e00f4877ba1d61ad924e834b67291dd`
- 1 file changed, 43 insertions(+), 8 deletions(-)

```diff
diff --git "a/C:\\workspace\\_resume_4368_20261115\\p2r3d\\k10_compare_r3d.py" "b/C:\\workspace\\_resume_4368_20261115\\p2r3f_8a0c843\\k10_compare_r3f.py"
index 5f649e9..76c3cd9 100644
--- "a/C:\\workspace\\_resume_4368_20261115\\p2r3d\\k10_compare_r3d.py"
+++ "b/C:\\workspace\\_resume_4368_20261115\\p2r3f_8a0c843\\k10_compare_r3f.py"
@@ -1,8 +1,20 @@
-"""DRAFT (not run). rev22 R22-3 K-10 comparison of one path 2 bundle output: R3c (judge_f9bc3c7) vs R3d.
+"""DRAFT (not run). rev25 R25-3 K-10 comparison of one path 2 bundle output: R3d (judge_0220671) vs R3f.
+(Copy of the R3e comparator `k10_compare_r3e.py`; only the excluded keys / elements and this docstring changed.
+The output keys `r3c` / `r3d` keep their names and mean "before" (R3d) / "after" (R3f).)
 
 Usage (dynamics-dev or python-dev, -I):
-  python -I k10_compare_r3d.py <R3c json> <R3d json> --out <compare json>
+  python -I k10_compare_r3f.py <R3d json> <R3f json> --out <compare json> [--out-dir <R3d out> --out-dir <R3f out>]
 
-Excluded before the comparison (R22-3 "K-10 비교에서 빼는 것"):
+rev25 R25-2 2 (다) (a rev24 CD-10 defect fix): run-time keys and the output-path elements of argument lists.
+  - Run-time keys of the tool run: `created` (top level of every `p2h_*.json`, `path2/p2_4368.py:2565`, the
+    wall-clock time of that tool run; it differed in the R3d K-10 too). Checked in the output code of path 2
+    (`path2/p2_4368.py`, `path2_chrono/p2_*.py`): the other datetime uses (`p2_4368.py:1247` `window`,
+    `p2_chrono.py` row windows) are built from the batch records, not from the tool-run clock, and are kept.
+    Time-like names that are judgement values or input records (`P3-2.time_ok`, `H-9.clip_times_complete`,
+    `law_locked.time_key`, `las_started`, the Chrono run's `wall_s`) are compared.
+  - Output-path elements: list elements that are strings containing a `--out-dir` folder (the R3d and the R3f
+    output folders), e.g. the `--out` value inside `p2h_*.json` `argv`, are dropped; the rest of the list stays.
+
+Excluded before the comparison (R22-3 "K-10 비교에서 빼는 것", kept):
   - seal block: key `seal`
   - tool version / rule description strings: keys `tool`, `clause`, `clause_t_lift`, `layer`, `rule`, `note`,
@@ -11,4 +23,9 @@ Excluded before the comparison (R22-3 "K-10 비교에서 빼는 것"):
   - input file path / sha256 blocks: `input_files_sha256`, `manifest`, `batch`, `folder`, `t45_report`,
     `e7_tool_output`, `params` is kept (YAML numbers are judgement inputs, compared)
+Added by rev24 CD-10 (run identity keys of path 2 outputs: checkout commit of the tool run; the tool-run time key is
+`created`, added by rev25 (다) above; output locations are the `t45_report` / `e7_tool_output` keys above):
+  - `checkout_commit` (bundle `cd2_judge_provenance`), `head` (`e7_path2.json` `tool_gate`)
+Added by rev24 CD-10 last sentence (CD-7 reason keys): `cd7_reason`, `cd7_row_reason`, `cd7_change_reason`,
+  `cd7_empty_reasons`
 Compared: grades, booleans, lists, counts, classes exactly; numbers |a - b| <= 1e-9 max(1, |a|, |b|) (rules 9.2).
 Exit 0 = equal, 1 = differences (listed), 2 = a file missing (S-15) or unreadable.
@@ -24,12 +41,26 @@ from pathlib import Path
 EXCLUDE = ｛"seal", "tool", "clause", "clause_t_lift", "layer", "rule", "note", "disclosure", "limit_disclosure",
            "tool_sha256", "tool_files_sha256", "out_sha256", "input_files_sha256", "manifest", "batch", "folder",
-           "t45_report", "e7_tool_output"｝
+           "t45_report", "e7_tool_output",
+           # rev24 CD-10: run identity (checkout commit of the tool run)
+           "checkout_commit", "head",
+           # rev24 CD-10 last sentence: CD-7 reason keys
+           "cd7_reason", "cd7_row_reason", "cd7_change_reason", "cd7_empty_reasons"｝
+RUN_TIME_KEYS = frozenset(｛"created"｝)   # rev25 (다): tool-run time (p2h_*.json, path2/p2_4368.py:2565)
+OUT_DIRS: list = []           # rev25 (다): normalised output folders (set from --out-dir)
+
+
+def _norm(s: str) -> str:
+    return s.replace("/", "\\").rstrip("\\").lower()
+
+
+def _is_out_path(v) -> bool:
+    return isinstance(v, str) and any(d and d in _norm(v) for d in OUT_DIRS)
 
 
 def strip(o):
     if isinstance(o, dict):
-        return ｛k: strip(v) for k, v in o.items() if k not in EXCLUDE｝
+        return ｛k: strip(v) for k, v in o.items() if k not in EXCLUDE and k not in RUN_TIME_KEYS｝
     if isinstance(o, list):
-        return [strip(v) for v in o]
+        return [strip(v) for v in o if not _is_out_path(v)]   # drop only the output-path elements
     return o
 
@@ -72,6 +103,10 @@ def main(argv=None) -> int:
     ap.add_argument("r3d")
     ap.add_argument("--out", required=True)
+    ap.add_argument("--out-dir", action="append", default=[],
+                    help="output folder of a compared run (repeatable); list elements containing it are dropped")
     a = ap.parse_args(argv)
-    res = ｛"r3c": a.r3c, "r3d": a.r3d, "excluded_keys": sorted(EXCLUDE)｝
+    OUT_DIRS[:] = [_norm(d) for d in a.out_dir]
+    res = ｛"r3c": a.r3c, "r3d": a.r3d, "excluded_keys": sorted(EXCLUDE | RUN_TIME_KEYS),
+           "dropped_list_elements_containing": list(a.out_dir)｝
     try:
         if not Path(a.r3c).is_file() or not Path(a.r3d).is_file():
@@ -88,5 +123,5 @@ def main(argv=None) -> int:
         code = 2
     Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
-    print(json.dumps(｛"tool": "k10_compare_r3d.py", "status": res["status"], "out": a.out｝))
+    print(json.dumps(｛"tool": "k10_compare_r3f.py", "status": res["status"], "out": a.out｝))
     return code
 
```

### 경로 2 비교기, R3e 판 → R3f

- 앞 판 `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\7ea6ef9d-fc13-4bf1-8179-0167f32d78a7\scratchpad\p2r3e\k10_compare_r3e.py` sha256 `28e85e45ad33dd16f94248a94fb800531ea5516b088bffed5eaee7a9fa0acc08`
- R3f `C:\workspace\_resume_4368_20261115\p2r3f_8a0c843\k10_compare_r3f.py` sha256 `cc92c5479ef69e63dc7222e0b42914100e00f4877ba1d61ad924e834b67291dd`
- 1 file changed, 34 insertions(+), 10 deletions(-)

```diff
diff --git "a/C:\\Users\\jinbeom\\AppData\\Local\\Temp\\claude\\63917d480778c1ba\\7ea6ef9d-fc13-4bf1-8179-0167f32d78a7\\scratchpad\\p2r3e\\k10_compare_r3e.py" "b/C:\\workspace\\_resume_4368_20261115\\p2r3f_8a0c843\\k10_compare_r3f.py"
index 97bcc7e..76c3cd9 100644
--- "a/C:\\Users\\jinbeom\\AppData\\Local\\Temp\\claude\\63917d480778c1ba\\7ea6ef9d-fc13-4bf1-8179-0167f32d78a7\\scratchpad\\p2r3e\\k10_compare_r3e.py"
+++ "b/C:\\workspace\\_resume_4368_20261115\\p2r3f_8a0c843\\k10_compare_r3f.py"
@@ -1,8 +1,18 @@
-"""DRAFT (not run). rev24 R24-3 K-10 comparison of one path 2 bundle output: R3d (judge_0220671) vs R3e.
-(Copy of the R3d comparator `k10_compare_r3d.py`; only the excluded keys and this docstring changed.
-The output keys `r3c` / `r3d` keep their names and mean "before" (R3d) / "after" (R3e).)
+"""DRAFT (not run). rev25 R25-3 K-10 comparison of one path 2 bundle output: R3d (judge_0220671) vs R3f.
+(Copy of the R3e comparator `k10_compare_r3e.py`; only the excluded keys / elements and this docstring changed.
+The output keys `r3c` / `r3d` keep their names and mean "before" (R3d) / "after" (R3f).)
 
 Usage (dynamics-dev or python-dev, -I):
-  python -I k10_compare_r3e.py <R3d json> <R3e json> --out <compare json>
+  python -I k10_compare_r3f.py <R3d json> <R3f json> --out <compare json> [--out-dir <R3d out> --out-dir <R3f out>]
+
+rev25 R25-2 2 (다) (a rev24 CD-10 defect fix): run-time keys and the output-path elements of argument lists.
+  - Run-time keys of the tool run: `created` (top level of every `p2h_*.json`, `path2/p2_4368.py:2565`, the
+    wall-clock time of that tool run; it differed in the R3d K-10 too). Checked in the output code of path 2
+    (`path2/p2_4368.py`, `path2_chrono/p2_*.py`): the other datetime uses (`p2_4368.py:1247` `window`,
+    `p2_chrono.py` row windows) are built from the batch records, not from the tool-run clock, and are kept.
+    Time-like names that are judgement values or input records (`P3-2.time_ok`, `H-9.clip_times_complete`,
+    `law_locked.time_key`, `las_started`, the Chrono run's `wall_s`) are compared.
+  - Output-path elements: list elements that are strings containing a `--out-dir` folder (the R3d and the R3f
+    output folders), e.g. the `--out` value inside `p2h_*.json` `argv`, are dropped; the rest of the list stays.
 
 Excluded before the comparison (R22-3 "K-10 비교에서 빼는 것", kept):
@@ -13,6 +23,6 @@ Excluded before the comparison (R22-3 "K-10 비교에서 빼는 것", kept):
   - input file path / sha256 blocks: `input_files_sha256`, `manifest`, `batch`, `folder`, `t45_report`,
     `e7_tool_output`, `params` is kept (YAML numbers are judgement inputs, compared)
-Added by rev24 CD-10 (run identity keys of path 2 outputs: checkout commit of the tool run; path 2 outputs carry no
-tool-run time, and their output locations are the `t45_report` / `e7_tool_output` keys above):
+Added by rev24 CD-10 (run identity keys of path 2 outputs: checkout commit of the tool run; the tool-run time key is
+`created`, added by rev25 (다) above; output locations are the `t45_report` / `e7_tool_output` keys above):
   - `checkout_commit` (bundle `cd2_judge_provenance`), `head` (`e7_path2.json` `tool_gate`)
 Added by rev24 CD-10 last sentence (CD-7 reason keys): `cd7_reason`, `cd7_row_reason`, `cd7_change_reason`,
@@ -36,11 +46,21 @@ EXCLUDE = ｛"seal", "tool", "clause", "clause_t_lift", "layer", "rule", "note", "
            # rev24 CD-10 last sentence: CD-7 reason keys
            "cd7_reason", "cd7_row_reason", "cd7_change_reason", "cd7_empty_reasons"｝
+RUN_TIME_KEYS = frozenset(｛"created"｝)   # rev25 (다): tool-run time (p2h_*.json, path2/p2_4368.py:2565)
+OUT_DIRS: list = []           # rev25 (다): normalised output folders (set from --out-dir)
+
+
+def _norm(s: str) -> str:
+    return s.replace("/", "\\").rstrip("\\").lower()
+
+
+def _is_out_path(v) -> bool:
+    return isinstance(v, str) and any(d and d in _norm(v) for d in OUT_DIRS)
 
 
 def strip(o):
     if isinstance(o, dict):
-        return ｛k: strip(v) for k, v in o.items() if k not in EXCLUDE｝
+        return ｛k: strip(v) for k, v in o.items() if k not in EXCLUDE and k not in RUN_TIME_KEYS｝
     if isinstance(o, list):
-        return [strip(v) for v in o]
+        return [strip(v) for v in o if not _is_out_path(v)]   # drop only the output-path elements
     return o
 
@@ -83,6 +103,10 @@ def main(argv=None) -> int:
     ap.add_argument("r3d")
     ap.add_argument("--out", required=True)
+    ap.add_argument("--out-dir", action="append", default=[],
+                    help="output folder of a compared run (repeatable); list elements containing it are dropped")
     a = ap.parse_args(argv)
-    res = ｛"r3c": a.r3c, "r3d": a.r3d, "excluded_keys": sorted(EXCLUDE)｝
+    OUT_DIRS[:] = [_norm(d) for d in a.out_dir]
+    res = ｛"r3c": a.r3c, "r3d": a.r3d, "excluded_keys": sorted(EXCLUDE | RUN_TIME_KEYS),
+           "dropped_list_elements_containing": list(a.out_dir)｝
     try:
         if not Path(a.r3c).is_file() or not Path(a.r3d).is_file():
@@ -99,5 +123,5 @@ def main(argv=None) -> int:
         code = 2
     Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
-    print(json.dumps(｛"tool": "k10_compare_r3d.py", "status": res["status"], "out": a.out｝))
+    print(json.dumps(｛"tool": "k10_compare_r3f.py", "status": res["status"], "out": a.out｝))
     return code
 
```

## 부록 D. 결과 본 뒤 개정의 본 자료 목록과 공개 절 (봉인본 원문 그대로)

- 각 절은 봉인본에서 그 절 제목 줄부터 다음 `## ` 제목 앞까지를 그대로 옮겼다(제목 수준만 `####`로 낮춤). 판정서 정의는 이 원문이 정한다.

#### R15-0. 결과 본 뒤 개정의 공개 (본 자료 목록) — `v5_resume_4368_rules_rev15.md` 12~29행

- 이 판은 R2 본 실행 결과 일부가 나온 뒤에 쓴다. 문턱·등급·멈춤 조건의 뜻은 바꾸지 않는다. 바꾸는 것은 판정 도구와 판정 입력, 그리고 원 규칙이 정하지 않은 세 곳의 읽기(R15-3·R15-4)뿐이다.
- **이 판을 쓰기 전에 사람·도구가 본 것**(메인 세션 전달, 2026-11-14):
  1. 실행 상태: 하네스 73단계 모두 exit 0(23:31). Chrono C-1·C-3·C-4·C-5(3폴더)·C-6/7·OC5PROBE·OC5 본 행 rc 0. C-2 4행(22:26~)과 PS-c 2행(23:01~)은 진행 중이다.
  2. PS-c G-S 1행의 확인 결과: `gs_psc_check` ok, R4-D 열과 사건 키 있음, 1 ms 55,301행(R15-6).
  3. H-2 C-2 선정: 두 경로가 같은 6행을 골랐다(사용자 결정 (h)).
  4. Chrono 판정 중 판정자가 본 것:
     - V0 L2b 행에 1 ms `crawler_normal_N`이 없고, 경로 1 `e998fd5`가 그 행의 10 Hz 구간 값을 `reference_not_used`로 남겼다(판정자는 그 값을 보았다).
     - C-7b 행에 `v5_hydraulics` 블록이 없다.
     - C-4 끔 팔에 `controller_meta.liftoff_approach_slow`가 없다.
     - 경로 1이 V0 L2b 행을 L1-R로 읽었다.
     - 경로 2가 C-7a·b를 열린 루프로 읽지 않았고, probe에 O-C5 본 행 블록을 적용했다.
     - `p2_t45` 회귀 행 폴더를 정확히 고정하지 않았다.
  5. 판정 등급·멈춤 여부·P-1·P-2 대조 결과는 이 판을 쓰는 데 쓰지 않았다. 이 작성자는 결과 파일과 판정 출력의 내용을 열지 않았다. 도구 커밋은 이름·줄 수·커밋 메시지와 `v5_resume_4368_chrono_rows.py` diff만 보았다.
- 사후 개정이므로 판정서에는 이 목록을 그대로 싣는다. D-29 V0 L2b(R15-3)처럼 값을 본 뒤 정한 읽기는 그 사실을 판정 결과 옆에 적는다.
- 이 작성자는 경로 2 작성자가 아니다(rev2 R2-0).

#### R16-0. 결과 본 뒤 개정의 공개 (본 자료 목록) — `v5_resume_4368_rules_rev16.md` 13~35행

- 이 판은 하네스 본 묶음의 두 경로 판정 출력과 Chrono 결과 일부가 나온 뒤에 쓴다. 문턱·등급·멈춤 조건의 뜻은 바꾸지 않는다.
- **이 판을 쓰기 전에 사람·도구가 본 것**(2026-11-15)
  1. 메인 세션이 두 경로 출력을 요약한 것: S-6 67줄, G-5 집합(경로 1의 5키, 경로 2 A의 2키, B의 3키), H-7 J-P3 5줄, J11 6줄(경로 2) / 153줄 판정 불가(경로 1), u3 G-6 3줄, H-8 seedext, 경로 2의 S-5 앵커 질문, 경로 1의 S-2 1,553줄·S-3 242줄, G-3 기록 없음.
  2. 이 작성자(control-expert, 도메인 검토)가 직접 연 것(읽기 전용, 2026-11-15)
     - 두 경로 판정 출력: 경로 1 `k1_class.json`, `u3_judge.json`, `h8_noise_judge.json`, `record_check.json`, `chrono_path1/k1_classification_7_2.json`(Chrono 행 51개의 7.2 분류), 경로 2 `p2h_harness.json`, `p2h_harness_b.json`, `p2h_u3.json`, `p2h_u3_b.json`.
     - 원 데이터: `resume_k1/` 아래 `h8_noise_{V0,VB}.json`, `h8_seedext_VB.json`, `h6_dg3_v4on.json`, `h9_stage1.jsonl`, `h10_reuse_rerun.jsonl`(와 그 T4h npz), `h9_grid/*.json`, `v5_rerun/las_k1/` 아래 u3·u6 결과, 저장 기준선 `v5/noise_v0`, `noise_vb`, `noise_vb_m2r4`, `dg3/dg3_v4_on.json`, `seedext/r79_VB_seedext.json`.
     - 저장 Chrono: `07_results/S9/batch_JOURNAL-AUGER_20261031_165543`, `batch_P3b_20261026_122444`, `batch_k1soil_G1_20261105`, `batch_G6P_20261029_144418`, `batch_V5-RESUME-K1-C3/C4/C5_*`의 `batch.json`·`result.json`.
     - 코드(읽기만): `two_pressure.py` 2185~2216행, `b5_baseline_compare.py` 347~366행, `p2_u3.py` 1~209행, `r69_g8_screen.py` 85·223행, `s9_soil_slope.py` 44~52·720~740행, `run_b9f5707/run_harness.ps1` 26~47행(단계 argv·Env).
  3. 이 작성자가 그 자료에서 확인한 사실(아래 각 절 [사실] 글머리의 근거)
     - S-6 67줄은 모두 G1 균일이고 결정 67건이 모두 dP = −5주기다.
     - 저장 Chrono G1 행은 모두 `soil_mode_t_s` = null이다: G1 균일 6행(패드 B 3, A 3)과, 배치가 다른 G1 일색 10행(`batch_k1soil_G1_20261105`, `--soil-patch FL:G1`, 60 s, `batch.json` 없음).
     - G-5 차이의 원인: 경로 2가 settle_v2의 축별 목록을 스칼라로 읽었고, r72 377·U-S9-G6c 강등을 빠뜨렸다.
     - 경로 2 S-5(1,844/86/86)는 "같음 + 저장 해시 없음"의 합이다. 저장 파일에는 `base.commands_sha256`만 있다. VB 3줄 차이는 dg3 대체 키이고, `dg3_v4_on`과는 비트가 같다.
     - J11 기록 필드는 `n_late_fallback`이다(`n_late` 없음, 153/153). 경로 2의 6줄은 모두 V5·V7이다.
     - J-P3 5줄은 2개 시나리오다(R12 bottom FL Fs4와 격자 `r69_bottom|…|FL|G4|0.0`은 숫자가 같음).
  4. 메인 세션이 전달한 확인 결과(2026-11-15): python-expert의 G-3 argv·키·비교 필드, G-6 T4h 경로와 값 출처 조사, cad-expert의 Chrono 행 argv·격자·실행 방식·정체성 점검·실행 준비(칸 마스크, 정체성 도구, 출력 폴더), verif-protocol-auditor의 봉인 전 감사. 모두 코드·저장 행 argv·규칙 본문만 보았고 판정 등급은 쓰지 않았다(메인 세션 전달).
  5. **hydraulics-expert 원인 분석**(2026-11-15, 결과를 본 뒤의 분석): J-P3 2개 시나리오와 G-6 g8 3키의 원인이다. 근거 자료는 `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\hyd-4368`(스크립트·출력·npz 83개 파일)다. 메인 세션이 요약을 전달했다. 이 작성자는 요약만 보았고, 그 폴더의 파일은 열지 않았다. 요약 내용은 R16-15 2와 R16-15a에 적었다.
  6. 이 결함 목록(R16-5~R16-9)은 **메인 세션과 도메인 검토(control-expert)가 두 경로의 출력을 모두 보고 정리한 것**이다. 두 경로 작성자 자신이 상대 출력을 보고 고친 것이 아니다(원판 9.2 "상대 출력을 본 뒤에는 어느 경로도 고치지 않는다"). 경로 2 작성자에게는 R16-10 3 표의 [정의] 글머리만 준다.
- 사후 개정이므로 판정서에는 이 목록을 그대로 싣는다. 값을 본 뒤 정한 읽기(R16-3~R16-9)는 판정 결과 옆에 "결과 본 뒤 정한 읽기"로 적는다.
- 이 작성자는 경로 2 작성자가 아니다(rev2 R2-0).

#### R17-0. 결과 본 뒤 개정의 공개 (본 자료 목록) — `v5_resume_4368_rules_rev17.md` 12~19행

- 이 작성자가 본 것(2026-11-15, 메인 세션 전달과 읽기 전용 확인)
  1. 메인 세션 전달: H-11 10실행 모두 exit 0(env_guard·identity 포함). H-12 래퍼 `u3_g8_VB_t4h.json` exit 0(53 s), staging T4h 3개, `gate first`로 첫 키 `slope_edge_top_4.0_FR_raised_20.0_proj.npz`(sha256 `c3e577dc…`)를 `t4h\`로 옮김, `t4h_replay --check-recorded` exit 0(`runs` 1, `J-P3` pass, settings 같음, RuntimeError 없음), `gate rest` exit 1(`recorded_lower_max_abs_N` = 9.094947017729282e-13 N). 나머지 두 파일(`edgeMr FL`, `rpB FR`)은 staging에 남음. Chrono 8행은 pre 모두 ok, 실행 중. 같은 첫 파일 확인 출력 `<OUT>\H-12\t4h_first_check.json`의 필드(그대로): `runs_over` = 1, 행 `over_0p6kN` = 1, `over_0p6kN_by_leg` = {FR: 1}, `max_excess_N` = 1110.48 N, `provisional_pass` = False, `unlocked_tail_over_0p6kN_by_leg` = {RL: 1}, `max_excess_vs_window_min_N` = 7702.5 N, `judged_samples_by_leg` = FL 157, FR 320, RL 168, RR 154. **공개: 메인 세션과 이 판의 작성자는 이 H-7 관련 값을 본 상태에서 이 판을 쓰고 봉인한다.** 이 판이 바꾸는 것은 도구 일관성 관문(재생 하한 = 기록 하한)의 허용 오차뿐이고, H-7 판정 문턱(0.6 kN)과는 무관하다.
  2. 이 작성자가 연 것(읽기만): `<OUT>\_tools\harness\h12_t4h_gate.py`(sha256 `821fb9df298703f6c3d66bbda521125fd8b1b0dced6b019cda48b1f35e5e44f2`) 1~175행, `steps_h12.json`, `run_h12.ps1`의 대기·`SkipDone` 부분(22·118~174행), `h11_h12_check.py`의 머리말과 해시 비교 부분, rev16 봉인본.
  3. 확인한 사실: `h12_t4h_gate.py` 82행이 `row.get("recorded_lower_max_abs_N") != 0.0`으로 정확한 0을 요구한다. `h11_h12_check.py`는 이 값을 쓰지 않는다. rev16 봉인본에서 이 조건이 나오는 곳은 R16-9 4 (다) 한 곳(봉인본 173행)이다.
- 판정 결과(J-P3, H-7 등)의 값은 이 판을 정하는 데 쓰지 않았다. 판정서에는 이 목록과 "결과 본 뒤 정한 허용 오차"를 그대로 적는다.

#### R18-0. 결과 본 뒤 개정의 공개 (본 자료 목록) — `v5_resume_4368_rules_rev18.md` 12~18행

- 이 작성자(control-expert, 도메인 검토)가 본 것(읽기 전용, 2026-11-15): `judge_576eb87/chrono_path1/`의 `judge_C*.json`(행별 `grade`·`grade_note`·재계산 항목), `oc5_C-8a.json`·`oc5_C-8b.json`, `run_path1.ps1`; `judge_576eb87/chrono_path2c/p2_C1~C8.json`(묶음·행 상태, C-4·C-8 항목), `chrono_path2/p2h_oc5k_C-8a.json`·`p2h_openloop.json`; C-2 S-01·02 행 `result.json`(`controller_meta.lift_stroke_guard`, `p3b`, `p3b_ext`); 규칙 원판 5.2·7.4, rev6 R6-B8, `d1_selection_rules.md` 6·11절, 명세 427.9.
- 이 작성자가 확인한 사실: 경로 1 R3 도구는 등급을 G6 행(S-03·04)에만 붙이고 그 밖은 "D8 row grade is the bundle judge's"로 비워 둔다. 경로 2는 C-1 통과·C-3 통과·C-5 통과·C-2 판정 불가·C-4 기록 불완전·C-6·C-7 기록 완료·C-8 S-9를 냈다. C-2 S-01·02는 SGS 정지(RL, 52.9 / 52.0 s, `FAULT_STROKE_END` 0, 이탈 뒤 최소 71.2~71.6 kN)다. C-8a·C-4의 RL 값은 R18-5·아래 표다.
- 메인 세션 전달: 사용자 결정 60, 메인 checkout이 R3에 있다는 사실.
- 판정서에는 이 목록을 그대로 싣는다. 이 판의 정의는 위 값을 본 뒤 정했으므로 "결과 본 뒤 정한 정의"로 적는다.

#### R18-5. C-8a S-9의 처리와 L-5 문구 (사용자 결정 60의 1) — `v5_resume_4368_rules_rev18.md` 91~103행

- **[정의]** C-8a(O-C5 VB, Kc3) S-9는 (A)로 처리한다: L-5 알려진 한계로 공개하고, 원인 진단은 436.9로 넘긴다. C-8은 기록 묶음이라 등급은 바뀌지 않는다(원판 7.4·8.1).
- **[정의] L-5 문구**(판정서에 그대로): "운용 시작 조건 안(R_c 0.952, 바닥 2.1434°·1.3784°)의 혼합 지형(강체 + J1@FR, VB, 크롤러 강성 ×3)에서, 크롤러 이탈 직후 35.286 s에 RL 실제 실린더 힘이 최소 5,869.6 N(F_min 9,414.6 N 대비 −3,545 N)까지 내려갔다. F<F_min 시간은 0.158 s, F<F_min + 2 kN 시간은 0.212 s다. 다리는 접지를 유지했다. 사전 예측 P-13(RL 최소가 P5r4 A3의 8.64 kN보다 높다)은 빗나갔다. 바닥을 줄였는데 최소가 낮아진 비단조라 시점 민감성이 의심된다. 같은 지형의 C-4 4행(R_c > 1)도 RL 이탈 직후 하강(4.20~10.81 kN)을 보였다. 원인 진단(1 ms 다리별 하중, LAS-b 끝 시각과의 관계, 크롤러 강성 의존)은 436.9에서 한다. 짝 C-8b(V0, 크롤러 강성 ×1)의 RL 최소는 11,951.2 N(F_min + 2.54 kN)이다."
- **[정의] 시간 값의 확정**: 문구의 F<F_min 0.158 s와 F<F_min + 2 kN 0.212 s는 경로 2 값이다. 경로 1 `fmin-time`(R3b 판, R18-2)과 K-10으로 대조한 뒤 확정한다. 값이 다르면 원판 9.2대로 기록하고, 문구에는 대조한 값을 적거나(수치만 허용 밖이면) 멈추고 묻는다(분류가 다르면).
- **[참고] 근거 출력과 키**
  - m·다리·시각: 경로 1 `judge_576eb87\chrono_path1\oc5_C-8a.json` `values.F_min_after_N`(RL = 5,869.61684783503 N)·`values.t_min_after_s`, `m_N`·`min_leg`·`margin_N`; 경로 2 `chrono_path2c\p2_C8.json` `rows[case = OC5_mixed_rigid_J1FR_Kc3_VB_top].items.m_7_4.per_leg.min_N`
  - 시간: 경로 2 같은 행 `items.Fmin_time_full.t_below_Fmin_s`·`t_below_Fmin_plus2k_s`(RL 0.158 / 0.212 s)
  - "접지 유지": 위 `F_min_after_N`의 네 다리 값이 모두 양수(최소 RL 5,869.6 N)이고, 같은 행 `result.json` `p3b`의 부상·재접촉 기록이 0이다(판정서에서 키와 함께 다시 적는다).
  - C-4 범위 4.20~10.81 kN: 경로 2 `p2_C4.json` `rows[].items.P3-3.min_N`(RL), 경로 1은 각 행 `result.json` `p3b.P3-3_leg_force.F_min_after_N`(RL)
  - R_c 0.952: 두 경로 `R_c_operating`·`items.R_c.R_c`(0.9523695802182304)
- 결정 필요: **아니오**(사용자 결정 60의 1).

#### R19-0. 결과 본 뒤 개정의 공개 (본 자료 목록) — `v5_resume_4368_rules_rev19.md` 12~17행

- 이 작성자(control-expert)가 본 것(읽기 전용, 2026-11-15): 경로 2 `path2_chrono/README.md` 6절 질문 표(T-1~T-7), 경로 1 `04_scripts/02_chrono/chrono_rows_judge_4368_README.md` 9절(러너 행 분기 표, C-5 짝, 러너 t_lift 항목), `chrono_bundle_grade_4368.py`(`30ef4b1`), `judge_b9f5707/chrono_path1/runner_judge/`의 러너 판정 출력 10개(`meta.failed`·`meta.hold`와 행 셈의 대조만), R3 판정 출력(rev18 R18-0 목록 그대로).
- 원 규칙 근거로 읽은 것: 명세 `s6_control_spec.md` 426.3(17246행 부근)·427.9(17680~17699행), `04_scripts/03_control/s9/soil_guard_stop_rule.py` 머리 문서(1~23행), `s9_soil_slope.py` `classify`(976~979행), `s9_soil_event_screen.py` `_pressure_rows`(481~497행)·E 항목 표(550~557행), `04_scripts/03_control/s8/r67_g1_screen.py` `judge_event`(309~373행), `04_scripts/02_chrono/run_S9.py` 1185~1195행·`soil_event_stop_s`·`judge_chrono_soil_event`(1374~1446행), `03_src/outrigger_sim/verify/s8_control.py` `_row`(407행)·CB 집계(3115~3126행)·`meta`(5477~5482행)·`judge_summary`(7523행), `verify/s6_control.py` 1196~1209·1261~1271·1991~2000·2096~2099·2318~2338행, `d1_selection_rules.md` 7·11절, rev3 R3-G10(Q-13·Q-14), rev6 R6-A(D-26~D-39)·R6-B4·R6-B5·R6-B8·R6-B9, `git diff f46b5ab 59c933b -- 04_scripts/03_control/s8/r67_g1_screen.py`.
- 판정서에는 이 목록을 그대로 싣는다. 이 판의 정의는 위 질문·해석을 본 뒤 정했으므로 "결과 본 뒤 정한 정의"로 적는다. 정의는 원 규칙 문장과 원 판정 도구에서 정했고, 어느 경로의 값으로 정하지 않았다.

#### R19-10. 9.2 예외와 바꾸지 않는 것의 공개 — `v5_resume_4368_rules_rev19.md` 101~127행

- **[사실]** 원판 9.2는 "상대 출력을 본 뒤에는 어느 경로도 고치지 않는다"이다. 이 판의 정의는 두 경로의 R3b 구현 질문·해석(R19-0)을 본 뒤 정했다. 판정서 한계 절에 그대로 적는다: "rev19 정의는 메인 세션과 도메인 검토가 R3b 두 경로의 구현 질문과 해석을 본 뒤 원 규칙 문장과 원 판정 도구에서 정했다. 두 경로는 같은 정의 문장만 받았고, 구현과 값은 경로마다 따로 만들었다. 정의할 곳의 선택은 두 경로에서 독립이 아니다."
- **[사실]** 숫자 문턱, 등급과 우선순위, 멈춤 조건의 뜻은 바뀌지 않는다. R19-5의 "멈추고 묻는다"는 rev18 R18-4와 같은 꼴의 판정 전 멈춤이고 원판 8.2의 새 멈춤 조건이 아니다.

##### 결정 표

| 항목 | 정의 | 결정 필요 |
|---|---|---|
| R19-1 안전 종료 | 427.9 조건 1~5만, P3·G6 기록 목록, 조건 3 창 LEVEL 시작~끝(Q-14), 조건 4 t_D~끝, 조건 5 D-32 10 Hz 실행 전체(포화 = 신장 ≥ 210 bar), 결측 판정 불가, `allowed_stop`은 통과 쪽·문구는 `통과 n / 안전 종료 m`(d1 11절 173행, R6-B8, 결과 본 뒤 정한 정의) | 결정됨: 사용자 결정 63의 1, 65 |
| R19-2 PS-c 기준·C1-09~12 | 기록 행, E 항목 없음은 결측 아님, 실패 보고·보류는 기록 불완전 | 결정됨: 사용자 결정 63의 2 |
| R19-3 E 창 | 어댑터 가지 창(−0.5 s ~ `soil_event_stop_s`), "실행 끝" = 가지 끝, E-4 창 밖 = 사건 뒤·W 뒤~가지 끝, E-5 = 가지 끝 READY·자세·FAULT 0·행정 | 결정됨: 사용자 결정 63의 3·4 |
| R19-4 passed None | 러너 셈 그대로(False = 미달, hold = 판정 불가), 판정 종류 None = 러너 미판정 기록, 셈 대조 S-11, 판정 종류 True 0개 행 = 판정 불가 | 결정됨: 사용자 결정 64 |
| R19-5 t_lift | D8 세 항목만 D-29 재계산, 나머지 넷은 러너 값 + t_lift 차 > 0.1 s(10 Hz 격자끼리)면 멈추고 묻기, D-29 t_lift 없음 = D8 세 항목 판정 불가, 차 계산 불가 = 멈추고 묻기 | 결정됨: 사용자 결정 63의 5 |
| R19-6 VB↔V0 | 여섯 쌍 정확히, 다르면 S-15 | 아니오 |
| R19-7 E-7 함수 단위 | 기록 전용 함수 안 덩어리만 + E-7 경로 함수 바이트 같음, 아니면 S-11 | 결정됨: 사용자 결정 63의 6 |
| R19-8 순서·허용 목록 | S7(부모 S6) → 두 도구 브랜치가 S7 병합 뒤 구현 → `z4373-r3b`(S7에서, `--no-ff`) → 메인 ff-only, 허용 (가) rev16~rev19, 봉인 목록 Chrono rev16~19·하네스 rev13~19 | 결정됨: 사용자 결정 63의 8 |
| R19-9 넘길 문장 | 두 경로 같은 문장, "다른 절은 열지 않는다" | 결정됨: 사용자 결정 63의 7 |

##### 결과 본 뒤 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-15 | 65 | 사용자 결정 65(2026-11-15, rev19 봉인 전 감사 권고 4): S-01~04의 `allowed_stop`은 묶음 등급에서 통과 쪽으로 세고, 묶음 문구는 `통과 n / 안전 종료 m`으로 따로 적는다. 판정서에는 결과 본 뒤 정한 정의로 공개한다 | R19-1 |
| 2026-11-15 | 64 | 사용자 결정 64(2026-11-15, rev19 봉인 전 감사 권고 1): 러너 행 등급은 러너 판정기 자신의 셈을 따르고(판정 종류 `passed` None = 러너 미판정 기록), 묶음별 러너 미판정 항목 수와 이름을 판정서에 공개한다 | R19-4 |
| 2026-11-15 | 63 | 사용자 결정 63(2026-11-15): R3b 두 도구 브랜치의 구현 질문을 원 규칙으로 정의하는 rev19를 쓰고 봉인한 뒤(S7, S6 위) 두 도구 브랜치가 S7을 병합해 정의를 맞춘다. 경로 2 하네스 도구의 `P2_CORE_SHA`는 R4에서 맞춘다 | R19-1~R19-10 |

#### R20-0. 결과 본 뒤 개정의 공개 (본 자료 목록) — `v5_resume_4368_rules_rev20.md` 12~16행

- 이 작성자(control-expert)가 본 것(읽기 전용, 2026-11-15): 메인 세션이 전한 경로 2 `5dcc8d4`의 R19-7 대조 사실((1) 거짓, (2) 참)과 질문 T-9, `git diff f46b5ab b9f5707 -- 04_scripts/03_control/s8/r67_g1_screen.py`, `git show b9f5707:04_scripts/03_control/s8/r67_g1_screen.py`의 `RESUME_K1_KEY` 정의·읽는 줄(616·622·645행)과 함수 머리(608·626·636·652·669행), 원판 4.2·6·7.2·8.2(S-3·S-5·S-6) 머리 문장, S7의 rev19 R19-7 본문.
- 판정서에는 이 목록을 그대로 싣고, 이 판의 정의를 "결과 본 뒤 정한 정의"로 적는다.

#### R20-3. 사실 오류와 9.2 예외의 공개 — `v5_resume_4368_rules_rev20.md` 33~37행

- **[사실]** rev19 봉인 전 control-expert 보고(초안 `20c68016` 보고)의 "[확인한 사실] `f46b5ab..59c933b`에서 `r67_g1_screen.py`의 바뀐 줄은 모두 기록 전용 함수 안에 있다"는 함수 밖 상수 `RESUME_K1_KEY`와 그 docstring을 놓친 사실 오류다. rev19 본문 R19-7에는 이 문장이 [정의] 조건 (1)으로만 들어갔고, 그 조건은 문장 그대로는 거짓이 된다. 판정서 한계 절에 그대로 적는다: "rev19 R19-7 조건 (1)은 모듈 수준 상수 정의를 빠뜨려 문장 그대로 대조하면 거짓이었다. rev20 R20-1이 그 이름을 읽는 함수가 모두 기록 전용임을 조건으로 고쳤다. 이 개정은 경로 2의 대조 결과를 본 뒤 했다."
- **[사실]** 9.2: 이 판의 정의는 경로 2의 대조 결과와 질문을 본 뒤 정했다. 두 경로는 같은 정의 문장만 받는다. 정의할 곳의 선택은 두 경로에서 독립이 아니다.

#### R21-0. 결과 본 뒤 개정의 공개 (본 자료 목록) — `v5_resume_4368_rules_rev21.md` 12~16행

- 이 작성자(control-expert)가 본 것(읽기 전용, 2026-11-15): 메인 세션이 전한 R3b 경로 1 멈춤 사실(C-1 L2b 6행, 러너 t_lift가 D-29 t_lift보다 0.4~0.5 s 늦음), dynamics-expert 진단 `…\scratchpad\dyn-run\tlift\tlift_diag.json`·`tlift_c2c5.json`(행별 `t_D29`·`t_runner`·`t_lift_sus`·LEVEL 시각·LEVEL 전 1 s의 0 비율·D-29 시각의 크롤러 힘·러너 값 네 항목의 두 창 값), `judge_062e051/chrono_path1/` 파일 목록, v5 기준 rev6 5절(146~159행), rev3 R3-G5, rev6 D-29·D-39, rev15 R15-3, rev19 R19-5.
- 판정서에는 이 목록을 그대로 싣고, 이 판의 정의를 "결과 본 뒤 정한 정의"로 적는다.

#### R21-6. 공개 — `v5_resume_4368_rules_rev21.md` 81~103행

- **[사실]** 판정서 한계 절에 그대로 적는다: "rev21은 R3b 경로 1 재판정이 C-1 L2b 6행에서 R19-5로 멈추고, dynamics-expert가 원인을 rev6 D-29 정의의 퇴화(L2b 스텝 끝 NSC 접촉력에서 첫 ≤ 0 표본이 LEVEL 첫 표본; C-1 L2b 6행: D-29가 LEVEL 시작과 0~1 ms, 그 시각 크롤러 30~75 kN; C-2·C-5 L2b 1 ms 23행: LEVEL 전 1 s 0 비율 55~77 %, D-29 시각 크롤러 30~126 kN)로 진단한 뒤 정했다. rev6 D-29가 빌린 정의는 원래 M2 잘림 스텝의 pre/post 분류용이었다. rev3 R3-G5의 조작 정의(명세 309행 '법선력 합이 0이 된 첫 시각' → 5절 첫 ≤ 0)를 같은 기준 문서(v5 기준 rev6 5절) 안의 t_lift,sus로 바꿨다. 새 정의 t_lift,sus는 결과를 본 뒤 정했고, 명세 3절의 '0'을 0.01 W와 '끝까지 이어짐'으로 읽는다."
- **[사실]** 9.2: 이 판의 정의는 경로 1 출력과 그 진단을 본 뒤 정했다. 두 경로는 같은 정의 문장만 받는다. 정의할 곳의 선택은 두 경로에서 독립이 아니다. 경로 2는 이 변경의 계기(경로 1 멈춤)를 정의 문장 밖으로는 받지 않는다.

##### 결정 표

| 항목 | 정의 | 결정 필요 |
|---|---|---|
| R21-1 D-29 교체 | 1 ms 행 = t_lift,sus(≤ 0.01 W 끝까지, 단계 조건 그대로, `1ms_sus`), D8 세 항목·D-39 재계산, V0 L2b = R15-3 그대로(10 Hz sus 대응값 기록), D-30·t_D·M2 분류 불변 | 결정됨: 사용자 결정 68의 1, 69(V0 L2b R15-3 유지) |
| R21-2 R19-5 기준 | 맞춘 값 = 새 t_lift의 10 Hz 올림(V0는 t_b), 문턱·네 항목 그대로 | 결정됨: 사용자 결정 68의 2 |
| R21-3 R3c | S9(부모 S8, `z4373-s4`) → `z4375-p1chrono`·`z4375-p2chrono`(R3b에서, S9 병합 뒤 구현) → `z4373-r3c`(R3b에서, `--no-ff`) → 메인 ff-only·푸시; 03_src·02_params·러너·manifest·`resume4368_judge.py` diff 0, 허용 (가)~(라); R4 브랜치는 R3c에서, R4 기준점 R3c..R4; 봉인 목록 Chrono rev16~21·하네스 rev13~21 | 결정됨: 사용자 결정 68의 4, 69(브랜치) |
| R21-4 재판정 | 경로 1 judge·bundle 전부 R3c 재실행 + D-29 밖 K-10 대조, 러너·view·fmin-time·oc5 출력 재사용, 경로 2 R3b 출력은 기록, R3c 출력으로 판정 | 결정됨: 사용자 결정 68의 5 |
| R21-5 넘길 문장 | R21-1~R21-4 [정의] 글머리 + 인용 원 절 | 결정됨: 사용자 결정 68의 6 |
| R21-6 공개 | 결과 본 뒤 개정, 퇴화 수치, 원 용도, 9.2 | 결정됨: 사용자 결정 68의 3 |

##### 결과 본 뒤 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-15 | 69 | 사용자 결정 69(2026-11-15, rev21 초안 보고의 판단 1·2): ① V0 L2b 행은 R15-3을 그대로 쓰고 10 Hz t_lift,sus 대응값을 기록하며 정의 차이를 공개한다. ② 새 도구 브랜치 `z4375-p1chrono`·`z4375-p2chrono`를 R3b에서 가르고 `z4373-r3c`로 통합한다 | R21-1, R21-3 |
| 2026-11-15 | 68 | 사용자 결정 68(2026-11-15): D-29 t_lift를 v5 기준 rev6 5절 t_lift,sus로 바꾸고 R19-5를 그 값으로 비교하는 rev21을 S8 위 S9로 봉인한 뒤, R3b 위에서 도구를 보완(R3c)하고 다시 판정한다 | R21-1~R21-6 |

#### R22-0. 결과 본 뒤 개정의 공개 (본 자료 목록) — `v5_resume_4368_rules_rev22.md` 12~17행

- 이 작성자(control-expert)가 본 것(읽기 전용, 2026-11-15): 메인 세션이 전한 멈춤 사실(위 계기), `judge_f9bc3c7/chrono_path1/`의 파일 목록, `run_path1_r3c.ps1`(19·22·57~60·89·95~103·105·117행), `t45_C5.json`(sha256 `aa19ebcf3fed31842ae76f554efc82ab7c22c0b48dbfff3b8b7e67f366ad477f`)의 키 구성과 `case` 값, `judge_C5.json`(sha256 `c1ba93823eee39c47b099042193ad54e29ae513bb7cbda3ae52a8437b27ad76a`)의 `case`·`dir` 짝, R3c `chrono_bundle_grade_4368.py`(74·76·134~141·864~878·1297행), `chrono_rows_judge_4368.py`(93~94·124행), `chrono_t45_replay.py`(876~885·1020~1032행), 메인 세션이 전한 `judge_f9bc3c7/chrono_path2/outputs.sha256`의 파일 sha256.
- **열람 공개**: 이 작성자는 첫 초안을 쓸 때 `t45_C5.json`의 머리(앞 1,500바이트)를 출력해 `summary` 블록 전체(T4·T5 초과 수, J-P3·rev7 요약, settings_equal·t4_0 통과 수 등)를 한 번 보았다. 봉인 전 감사자도 같은 블록을 한 번 의도치 않게 열람했다. 이 블록은 C-5 T4_T5 항목의 판정과 같은 값을 담는다. 두 경우 모두 그 값은 이 판의 정의에 쓰지 않았고 이 판에 적지 않는다. R22-1 짝짓기의 정의는 t45 값에 기대지 않는다(행 순서·경로·이름만 쓴다). C-1~C-3 묶음 등급 값과 경로 2 R3c 판정 결과는 이 판을 쓰는 데 쓰지 않았다.
- 판정서에는 이 목록을 그대로 싣고, 이 판의 정의를 "결과 본 뒤 정한 정의"로 적는다.

#### R22-5. 공개 — `v5_resume_4368_rules_rev22.md` 87~110행

- **[사실]** 판정서 한계 절에 그대로 적는다: "rev22는 R3c 경로 1 판정에서 C-1~C-3 묶음 등급이 나오고 C-5 묶음 등급이 t45 입력 거부로 멈춘 뒤 정했다. 바뀐 것은 경로 1 집계 도구가 t45 재생 출력의 행을 판정 행에 짝짓는 방법(이름 → 입력 폴더 순서와 `dir` 경로·안쪽 이름 대조)과 두 경로 Chrono 판정 도구의 봉인 목록 정의(rev22 추가)뿐이고, T4·T5 판정 로직·문턱·키와 다른 묶음의 규칙은 바뀌지 않았다. 두 경로는 R3d 도구로 C-1~C-8 판정을 다시 내어 R3c 출력과 대조했고, 러너 출력과 t45 재생 출력은 sha256 대조 뒤 재사용했다. 작성 중 t45 재생 출력의 요약 블록을 열람한 사실은 R22-0에 적었다."
- **[사실]** 9.2: 이 판은 경로 1 출력을 본 뒤 정했다. 경로 2 도구에서 바뀌는 것은 봉인 목록 정의뿐이다. 이 판의 정의는 경로 2 R3c 판정 결과를 보지 않고 정했다.

##### 결정 표

| 항목 | 정의 | 결정 필요 |
|---|---|---|
| R22-1 t45 짝짓기 | 입력 폴더 순서 + `dir` 전체 경로 = 입력 폴더 경로 + 안쪽 이름, 근거 사슬(`T45_CASES` = `$T45Cases`, 목록 재생성, 대소문자, 빈 `dir`), 행 수 S-15, 그 밖 S-11, 판정 로직 불변, 시험 | 결정됨: 사용자 결정 74의 2, 75의 2 |
| R22-2 R3d | S10(부모 S9, `z4373-s4`) → `z4376-p1chrono`·`z4376-p2chrono`(R3c에서, S10 병합 뒤) → `z4373-r3d`(p1 → p2 `--no-ff`) → 감사 → 메인 ff-only·푸시; 봉인 목록 두 경로 rev16~22(경로 1 정의는 행 판정 도구), 봉인 목록 변경 범위 일반형, 허용 (가)~(라), 덩어리 표 두 경로; R4는 R3d에서, 하네스 rev13~22 | 결정됨: 사용자 결정 74의 3·5, 75의 1, 77 |
| R22-3 재사용·재판정 | 빼는 것(공통 일반형, 경로 1 키 이름에 `disclosure`, 키 대응표); C-5 목록 원천 R3c = R3d; 경로 1: 러너·runner_judge·t45 출력 SHA256SUMS 대조 재사용, C-1~C-8 행 판정·묶음 등급 R3d 재실행과 K-10 대조, 실행 스크립트 허용 변경 셋, R3c 폴더 쓰기 금지·전후 대조; 경로 2: R3c 끝까지, t45 출력 `outputs.sha256` 대조 재사용, C-1~C-8 R3d 재판정(새 폴더, R3c 폴더 쓰기 금지, `outputs.sha256` 전후 대조)과 K-10 대조, 묶음 출력 없으면 S-15 | 결정됨: 사용자 결정 74의 4, 75의 1, 76, 77 |
| R22-4 넘길 문장 | 경로 1: R22-1~R22-3 [정의](경로 2 글머리 뺌), 경로 2: 순서 3·봉인 목록·변경 범위·(다)·빼는 것(일반형)·경로 2 재사용 [정의]만, 경로 1 구조·키 이름 없음, 자기 도구 디렉터리 말고 파일·줄 위치 없음 | 결정됨: 사용자 결정 74의 7, 75의 3 |
| R22-5 공개 | 결과 본 뒤 개정, 바뀐 것은 짝짓기와 봉인 목록 정의뿐, 요약 블록 열람 | 결정됨: 사용자 결정 74의 6 |

##### 결과 본 뒤 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-15 | 77 | 사용자 결정 77(2026-11-15, rev22 봉인 전 감사 차단 1): 경로 1 봉인 목록 정의는 행 판정 도구에 있으므로 그 정의와 시험 기대값만 rev16~22로 바꾸고, 경로 1도 R3d 도구로 C-1~C-8 행 판정을 다시 돌려 봉인 블록 밖을 R3c와 K-10으로 대조한다. 러너·runner_judge·t45 출력은 SHA256SUMS 대조 뒤 재사용한다. 두 경로 봉인 목록은 같고 예외는 없다. 경로 2 재판정 범위도 C-1~C-8 전체다 | R22-2, R22-3 |
| 2026-11-15 | 76 | 사용자 결정 76(2026-11-15): 경로 2 출력 처리는 R3c 판정을 끝까지 돌리고, R3d 뒤 t45 재생 출력을 sha 대조 뒤 재사용하며, R3d 경로 2 도구로 판정만 다시 돌려 봉인·도구 sha 블록 밖을 R3c 출력과 K-10으로 대조한다(다르면 멈추고 묻는다) | R22-3 |
| 2026-11-15 | 75 | 사용자 결정 75(2026-11-15, rev22 초안 보고의 확인 필요 2건): ① 경로 2도 봉인 목록에 rev22를 넣는다(`z4376-p2chrono`, R18-1 2 예외 없음), 경로 2 출력 재사용 규칙은 결정 76으로 정했다. ② t45 짝짓기 대조는 판정 행 `dir` 전체 경로 = t45 입력 폴더 경로 + 안쪽 이름 일치, 바깥 폴더 표지 대조는 쓰지 않는다. ③ 경로 2 넘길 문장은 봉인 목록과 재사용 정의 | R22-1~R22-4 |
| 2026-11-15 | 74 | 사용자 결정 74(2026-11-15): R3c C-5 묶음 등급의 t45 입력 거부를 경로 1 집계 도구의 t45 행 짝짓기 보완(R3d)으로 풀고, R3c 출력은 sha 대조 뒤 재사용해 `grade_C5`부터 잇는 rev22를 S9 위 S10으로 봉인한다(재사용·재판정 범위는 결정 76·77이 고쳐 씀) | R22-1~R22-5 |

#### R23-0. 결과 본 뒤 개정의 공개 (본 자료 목록) — `v5_resume_4368_rules_rev23.md` 12~27행

- 이 작성자(control-expert)가 본 것(읽기 전용, 2026-11-15)
  - 메인 세션 지시문(사용자 결정 80, 경로 1 작성자 보고의 요지)과 경로 1 작성자 보고 전문(R3d 경로 1 도구 커밋 보고: 결함 설명, diff 통계, 도구 sha256, 시험 개수, 덩어리 표, 실행 스크립트 초안 설명. 판정 값은 담지 않는다).
  - rev22 봉인본과 `.sha256`, rev22 봉인 후보 초안 1~12행.
  - 경로 1 도구 `7cd7031`의 `chrono_bundle_grade_4368.py` 300~389·525~669·1090~1129·1355~1424·1493~1552행과 `case` 문자열 Grep 결과.
  - R3c `judge_f9bc3c7/chrono_path1/`: 파일 목록, `runner_judge/` 파일 목록, `run_path1_r3c.ps1`의 Grep 줄(22·59·60·83·84·89·92·93·102·108행).
  - 같은 폴더 러너 판정 파일 36개(C1 10, C2 2, C5 24)에서 이름만 뽑는 스크립트로 본 것: 최상위 키 이름, 행 `case` 이름 집합, `s8_metrics` 키 이름, `meta` 키 이름, `meta.batch`의 끝 두 경로 이름. 값·항목 판정·등급은 출력하지 않았다.
  - `judge_C1.json`~`judge_C5.json`·`judge_C6C7.json`의 행 수, `dir` 없는 행 수, `case` ≠ `dir` 안쪽 이름인 행, 여러 행이 함께 가진 안쪽 이름, 대소문자 무시로 같은 `case` 이름, `judge_C5.json`의 `case` → `dir` 끝 두 이름.
  - 브랜치 기록: `z4373-s4`·`z4376-p1chrono`·`z4376-p2chrono`의 커밋 제목·해시, 경로 1 도구 커밋의 파일 통계. 경로 2 코드·출력은 열지 않았다.
  - 봉인 전 감사 리포트(`rev23_preseal_audit.md`, 이름·키·sha·줄 번호와 고칠 문안만 담고 판정 값은 담지 않는다).
- 봉인 전 감사자(verif-protocol-auditor)가 본 것(읽기 전용, 감사 리포트의 목록 그대로): R3c `judge_f9bc3c7/chrono_path1/`의 파일 목록; `runner_judge/` 36파일의 최상위 키 이름, `*`가 아닌 행 `case` 이름 집합, `*` 행 유무, `s8_metrics` 키 이름, `meta.batch` 끝 이름과 판정 행 바깥 폴더 이름의 일치 여부; `judge_C1.json`~`judge_C5.json`·`judge_C6C7.json`·`judge_OC5*.json`의 행 수, `dir` 없는 행 수, `case` → `dir` 안쪽 이름 차이 목록, `judge_C5.json`에서 같은 안쪽 이름을 가진 행 무리의 바깥 폴더 이름이 서로 다른지 여부; `SHA256SUMS.txt` 120항목 가운데 러너 판정 json 36개와 `judge_C1.json`·`judge_C2.json`·`judge_C5.json`의 sha256 대조; 경로 1 작성자 보고에서 판정어 Grep 6줄(시험·ruff 통과 문구뿐, 행·묶음 판정 값 없음); 경로 2 도구는 봉인 목록 위치만. 감사자는 이름·키·sha만 출력했고 판정 값은 보지 않았다(리포트 "우연히 본 값: 없음").
- 경로 1 작성자는 보고대로 R3c `runner_judge/C5_E_G4_Fs8_LS1.verify_S8C.json`의 러너 행 이름과 `s8_metrics` 키를 보았다.
- 이 판을 쓰는 데 C-1~C-3 묶음 등급 값, 행 판정 값, 러너 항목 판정, `liftoff_s` 값, 경로 2 판정 결과는 쓰지 않았고 보지 않았다.
- 판정서에는 이 목록을 그대로 싣고, R23-1을 "결과 본 뒤 정한 정의"로 적는다.

#### R23-5. 공개 — `v5_resume_4368_rules_rev23.md` 113~134행

- **[사실]** 판정서 한계 절에 그대로 적는다: "rev23은 R3d 통합 전, 경로 1 작성자가 R3c 러너 판정 출력의 행 이름과 `s8_metrics` 키(실행 폴더 안쪽 이름)가 경로 1 집계 도구의 조회 키(판정 행 이름)와 어긋남을 보고한 뒤 정했다. 바뀐 것은 경로 1 집계 도구가 러너 판정 출력의 행과 `s8_metrics`를 판정 행 `dir`의 안쪽 이름으로 찾는 것과 그 대응 기록(대응 대조의 S-11 포함), 두 경로 Chrono 판정 도구 봉인 목록의 rev23 추가뿐이고, 러너 판정 출력, R19-4·R19-5 판정 로직·문턱·키, R22-1 짝짓기, 다른 묶음의 규칙은 바뀌지 않았다. 영향 행은 판정 행 이름과 안쪽 이름이 다른 C-5 9행(LS1·LS4 6행, V0 3행)이고, C-1~C-3 묶음 등급이 바뀌지 않는지는 R3c 출력과의 K-10 대조로 확인한다(결과는 판정서 K-10 표). 작성 중 본 자료는 이름과 키뿐이며 판정 값은 보지 않았다(R23-0)."
- **[사실]** 9.2: 이 판은 경로 1 출력의 이름과 키를 본 뒤 정했다. 경로 2 도구에서 바뀌는 것은 봉인 목록 정의뿐이다. 이 판의 정의는 경로 2 코드와 판정 결과를 보지 않고 정했다.

##### 결정 표

| 항목 | 정의 | 결정 필요 |
|---|---|---|
| R23-1 러너 출력 찾기 | 파일은 판정 행 이름으로(그대로), `meta.batch` 대조 그대로, 파일 안 행·`s8_metrics`는 `dir` 안쪽 이름(완전 일치), 빈 `dir`·같은 `dir`·다른 이름 행·다른 키 S-11(행 판정 출력에 행이 없으면 기존 결측, 적용 안 한 대조는 null), 안쪽 이름 행 없음·키 없음은 기존 결측·계산 불가, 대응 기록 `runner_name_map_R23_1`, 행 출력 키 불변, 예상 영향 9행, 맵 행 수 = L2b·L1-R 행 수(R3c 참고 기준 C-1 10, C-2 2, C-3 0, C-5 24)와 C-1~C-3 `name_differs` 빈 목록, 시험 | 결정됨: 사용자 결정 80, 81(영향 행 9행, 대조 1~4) |
| R23-2 R3d | S11(부모 S10, `z4373-s4`) → 두 도구 브랜치에 S11 병합 뒤 추가 커밋 → `z4373-r3d`(p1 → p2 `--no-ff`) → 감사·integrity → 메인 ff-only·푸시; 봉인 목록 두 경로 rev16~23, 하네스 rev13~23; 허용 (가) rev22·rev23 파일과 `-text` 6줄, (나) R23-1 범위 추가(전달 자료 구조·종료 코드 단락 포함), (다)·(라) 그대로; 덩어리 표에 판 구분과 추가 커밋 표, 추가 커밋 표는 도구 경로로 거르고 S11 병합 파일 덩어리는 (가)로 분류 | 결정됨: 사용자 결정 80 |
| R23-3 재사용·재판정 | 경로 1 빼는 키에 `runner_name_map_R23_1`; 재사용·재판정 R22-3 그대로, C-1~C-3 K-10 대조가 R23-1 무영향 확인, C-5는 대응 기록 9행 확인, 묶음마다 맵 행 수 확인; `disclosure` 값 변화는 빼는 키 안; 실행 스크립트 추가 변경 없음; 경로 2는 봉인 목록만; 실행 쪽 판정 출력을 찾지 못한 행(원인을 가릴 수 없는 입력 결측 포함)은 두 경로 공통으로 멈추고 묻기 | 결정됨: 사용자 결정 80, 81(C-5 9행) |
| R23-4 넘길 문장 | 경로 1: R23-1 전체와 경로 1 글머리, 경로 2: 순서 3·봉인 목록·변경 범위·(다)·경로 2 덩어리 표만(경로 1 구조·키 이름·파일 위치 없음), rev23 sha는 값으로 주고 rev23 `.md`·초안·S11 커밋 본문은 열지 않음 | 결정됨: 사용자 결정 80 |
| R23-5 공개 | 결과 본 뒤 개정, 바뀐 것은 조회 키·대응 기록과 봉인 목록뿐, 이름·키만 열람 | 결정됨: 사용자 결정 80 |

##### 결과 본 뒤 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-15 | 81 | 사용자 결정 81(2026-11-15, rev23 초안 확인 필요 2건, 둘 다 권고안): ① 영향 행 범위는 C-5 9행 모두(LS1·LS4 6행과 V0 3행)이고, 판정 행 `dir` 안쪽 이름으로 찾는 방식 하나로 덮는다. ② R23-1 대조 1~4(빈 `dir`, 같은 `dir`, 파일 안 다른 `case`, `s8_metrics` 다른 키)의 S-11을 넣는다. 둘 다 찾기가 맞는지 확인하는 장치로 결정 80 범위 안이다 | R23-1, R23-3 |
| 2026-11-15 | 80 | 사용자 결정 80(2026-11-15): R3d 전에 짧은 rev23을 둔다. 허용 변경은 경로 1 집계 도구가 러너 출력 행·`s8_metrics`를 판정 행 `dir`의 안쪽 이름으로 찾는 것과 그 대응 기록뿐이고, 두 경로 봉인 목록에 rev23을 더한다. 봉인 S11은 S10 위(`z4373-s4`), 도구 수정은 같은 도구 브랜치(`z4376-p1chrono`·`z4376-p2chrono`)에 추가 커밋, 그 뒤 `z4373-r3d` 통합 → 판정 전 감사·integrity → master ff·푸시 → 두 경로 R3d 재판정. 결과 본 뒤 개정이라 stats-design-expert 검토는 하지 않고 R23-0·R23-5에 공개한다 | R23-0~R23-5 |

#### R24-0. 결과 본 뒤 개정의 공개 (본 자료 목록) — `v5_resume_4368_rules_rev24.md` 12~30행

- 이 작성자(control-expert)가 이 판을 쓰며 본 것(읽기 전용, 2026-11-15)
  - 메인 세션 지시문: 사용자 결정 86·88·89·90·91·92의 원문, rev23 봉인 사실(S11, sha), R3d 재판정 출력 위치와 두 sha 목록 파일의 짧은 해시, 감사가 권고한 도구 변경 목록, 진단 요지(결정 88 안).
  - 판정 후 감사 리포트 셋 전문: `r3d_kr_cross_path.md`(두 경로 K-R), `r3d_k10_record_audit.md`(경로 2 기록 K-10), `r3d_prejudge_reaudit.md`(판정 전 재감사). 이 rev24 초안의 봉인 전 감사 리포트 `rev24_preseal_audit.md` 전문.
  - **판정 값 열람 공개**: 위 리포트에서 두 경로의 묶음 등급(C-1 통과, C-2 미달, C-3 통과, C-5 경로 1 `판정 불가`(통과 13 / 미달 7 / 판정 불가 15)·경로 2 `통과`(35), C-6·C-7 기록 완료, C-8 경로 1 `기록 완료`·경로 2 `기록 불완전`, C-4 경로 2 `기록 불완전`), 행 등급이 갈린 행 이름(판정 불가 15행, 미달 7행), 그 원인 항목(P3-6·P3-7 실패, P3-1·P3-2 FLAG, 사건 행 이동 압력 판정 불가), 러너 이동 압력 값 범위(100.4~148.3 bar, 사건 창 없이 다시 센 값 136.4~189.1 bar, G1R_FS24 두 행 185.6·189.1 bar), C-8a m(5,869.6 N, RL, R_c 0.952)과 시간 값, C-8b m, N1~N6 수치(D8 최소 힘 51.4 / 29.7 kN 등), C-2 PS-c E-5 행정 값, K1 분류 수를 읽었다. 이 값들은 정의에 쓰지 않았다. 다만 어느 정의를 맞출지 고른 것은 이 값을 본 뒤다.
  - **경로 2 구조 열람 공개**: 위 리포트로 경로 2 출력 파일·키 이름(`p2_C*.json`, `p2h_*.json`, `e7_path2.json`, `D8_F_after_liftoff`, `D8_end_attitude`, `D8_pressure`, `leg_lift_after_departure`, `items.P3-2.*`, `items.T4`·`T5`, `items.m_7_4`, `Fmin_time_8s`, `stored_p3a_checks`, `tool_gate.head`, `argv`, `created`)와 코드 위치 요지(`p2_core.py:997-1042`의 D8 문턱·보류 처리, `p2_e7.py:113`, `path2/p2_4368.py:2564-2565`, 비교기 `k10_compare_r3d.py`의 이름 기준 제외), 경로 1 키 대응표를 보았다. 경로 2 코드·출력 파일 자체는 열지 않았다.
  - 규칙 원문: 원판 245·247~250·288~294·320·436~442행, rev18 1~125행, rev19 R19-1·R19-4·R19-5(58~73행)·R19-6, rev6 R6-A 표 34~53행, rev4 R4-A2 51~80행, rev3 Q-13·Q-14·R3-G5·R3-G6 줄, rev22·rev23 봉인본, v5 기준 개정 12 60~78행.
  - 명세 `s6_control_spec.md` 318~322행(검증 항목 2~6), 2360~2382행(U55~U61, 59.1 J-0~J-7), P3b 표 11024~11032행과 결과 표 11791~11801행.
  - `03_src/outrigger_sim/verify/s6_control.py` 151~170·799~1000행(사건 과도 창·빠른 침하 함수, 읽기만).
  - 경로 1 도구(메인 checkout R3d): `chrono_bundle_grade_4368.py` 120~201·440~549행(덮어쓰기 목록과 함수), `chrono_rows_judge_4368.py` 628~648행(이동 압력 함수, Grep). CD-2 덮어쓰기 표는 rev19 R19-5와 이 덮어쓰기 목록을 본 뒤 정했다.
  - R3c `judge_f9bc3c7/chrono_path1/`: 러너 판정 파일의 항목 이름·종류(묶음별, 그리고 C-5 사건 13행 행별), 각 파일의 창 관련 키 이름; `judge_C5.json`의 사건 13행 `dir`을 따라 연 `result.json`의 사건 설정(`settings.event`, `settings.level`, 사건 명세의 종류·다리·깊이·램프, `event_t_s` 있음 여부). 값·판정은 출력하지 않았다(이름만 뽑는 스크립트 `runner_items.py`·`event_items.py`·`event_config.py`).
  - R3c·R3d 두 경로 sha 목록 파일 넷의 파일 sha256.
  - dynamics-expert 보고 `L5_proposal_report.md`(sha256 앞 `74f74e0d`) 전문: A3·A5·OC5a의 RL 최소 분해 값, 모드 진동수, LAS 시각, L-5 문장안.
  - 진단 폴더 `diag-4368\`의 파일과 R3d 재판정 출력 파일은 열지 않았다.
- 이 작성자는 rev23 작성 때 본 자료(rev23 R23-0)도 가지고 있다.
- **봉인 전 감사자(verif-protocol-auditor)가 본 것**(감사 리포트 목록 그대로): `r3d_kr_cross_path.md` 전문(등급·값 포함)과 `r3d_k10_record_audit.md` Grep 줄, 작성자 스크립트로 뽑은 R3c 러너 판정 항목 이름·종류, R3c·R3d sha 목록 네 파일의 sha와 줄 수, `runner_judges.py`(경로 1 실행 보조) 앞 60줄, 규칙 원판 200~329행, rev4 48~80행, rev18 40~111행, rev19 58~87행, 명세 2355~2386행. 경로 2 코드·출력은 열지 않았다. 봉인 전 재감사(대상 `a5fc3df6…`)에서 더 본 것: 작성자 스크립트 `runner_items.py`·`event_items.py`·`event_config.py`의 출력(러너 판정 항목 이름·종류, 사건 13행의 행별 항목 이름, 창 관련 키 이름, `settings.event`·`level`·`event.spec`의 kind·leg·depth·ramp·`event_t_s` 있음 여부), `s6_control.py` 834~983행과 Grep, `L5_proposal_report.md` 4절과 1절 Grep 줄(분해 값), rev15 Grep, 원판 434~443행. 판정 값·등급은 보지 않았다.
- 판정서에는 이 목록을 그대로 싣고, R24-1~R24-3의 정의를 "결과 본 뒤 정한 정의"로 적는다. R24-1 "판정 확인용" 글머리의 수치는 출처(감사 리포트)와 함께 싣는다.

#### R24-5. 공개 — `v5_resume_4368_rules_rev24.md` 158~223행

- **[정의] 정의를 맞춘 것과 공개만 하는 것**(사용자 결정 89의 4)

| 감사 항목 | 처리 | 근거 |
|---|---|---|
| D1·D3 C-5 항목 범위(경로 1 미달 7행의 P3-6·P3-7) | 맞춤: CD-1·CD-2·CD-4 | 결정 89의 2 |
| D2 사건 행 이동 압력 창(경로 1 판정 불가 13행) | 맞춤: CD-2 표·CD-3(사건 행은 `E_RE1bF_` 4행과 `G1R_FS24_` 2행, `E_G4_` 7행은 비사건 규칙) | 결정 89의 4, 감사 차단 2 |
| S9SL 2행(사유 없는 판정 불가), N4·D9(S-01·02 P3-4) | 맞춤: CD-5·CD-7 | 결정 89의 4, 90의 1 |
| D4 T4·T5 대상 행 18 대 24 | 맞춤: CD-6 | 결정 89의 4 |
| D5(N1) 이탈 뒤 최소 힘 문턱·창, D7 부상 창 | 맞춤: CD-2 표(`C1 D8 min true rod force`·`D8 no pad lift-off` 재계산, `R/D8` 두 항목 그대로) | 원 판정기 항목 원문, rev3 R3-G6·Q-14, rev19 R19-5 |
| D10(N6) C-8 기록 상태 | 맞춤: CD-8(기록 값 목록) | 결정 89의 3 |
| D14 C-4 경로 1 출력 없음 | 맞춤: CD-9(경로 1 출력 추가, 기록 값 목록) | 결정 89의 4, 결정 88, 90의 3 |
| 경로 2 기록 K-10 다름 5건 | 맞춤: CD-10(다음 재판정부터 키로 뺌), R3d 판정은 결정 86대로 일치 처리 | 결정 86 |
| 경로 1 묶음 출력 판정 불가 사유 없음(57곳) | 맞춤: CD-7 | 감사 실행 전 수정 |
| D6(N2) 끝 자세 + 장착 계산 차(≤ 2.8e-6°) | 공개만(CD-2 표에서 끝 자세는 원 판정기 셈 그대로), python-expert 원인 확인 | 원판 320행 |
| D8(N3) PS-c E-5 행정 517.33 / 512.63 mm(재집계 대 재계산, 행정 좌표 미확인) | 공개만, python-expert 원인 확인 | 원판 320행 |
| D11(N5) C-8 8 s 창 최소(기록 항목) | 공개만, python-expert 원인 확인 | 원판 320행 |
| D12 C-6·C-7 P3a를 두 경로가 같은 저장값에서 읽음(독립 아님) | 공개만 | 원판 9.1의 경로 2 방법 |
| D13 열린 루프 3행의 7.2·4.2 표기 | 공개만 | rev18 R18-2a |
| D15 표기(`stroke_limited_stop` = `allowed_stop`, 기록 `pass` = `record`) | 공개만 | rev3 N-1 |
| C-1~C-3 J-P3를 경로 2 묶음 출력에 두지 않음 | 공개만(적용 수는 기록에 있음) | 감사 1.3 |
| D8 패드 부상 Q-14(경로 1만 계산했던 항목) | 맞춤: CD-2 표 | 감사 1.3 |

- **[사실] 원 판정기 직접 실행의 한계**(사용자 결정 90의 4, rev4 R4-A2 한계 공개 문장의 꼴): 경로 2가 원 판정기를 직접 실행하면 판정서 한계 절에 그대로 적는다: "L2b 행의 원 판정기 항목(CD-2 표에서 '원 판정기 셈 그대로'인 항목) 값은 원 규칙의 같은 판정기를 경로 2가 따로 실행해 얻었다. 그래서 두 경로는 그 항목 값의 계산 함수에 함께 기댄다. 경로 2의 독립성은 판정기 실행, 재계산 항목, 셈과 등급 재집계에 있고, '그대로' 항목의 값 계산에는 없다. 재계산 항목(사건 행 판별과 창 등)의 정의를 원 판정기 소스에서 읽어 구현했다면 그 항목도 원 판정기와 같은 정의에 기댄다. 경로 2가 연 원 판정기 소스는 경로 2 판정서의 읽은 것 목록에 있다." 공통 블록의 인용 출처 글머리가 두 경로 모두에 원 판정기 소스를 열었을 때 판정서 읽은 것 목록에 적게 한다.
- **[정의] L-5 틀 문장 교체**(사용자 결정 91, dynamics-expert 판정 `L5_proposal_report.md` 4절, A5 확인). 판정서의 L-5는 아래 새 문장으로 쓴다. 수치는 1 ms 참값(`step_series.npz` `F_cyl_N`, RL)에서 냈다. 준정적 = 한 주기 중심 평균, 진동 = 원값 − 그것이고, 0.8 Hz 저역·1~4 Hz 대역 분해와 0.6 kN 안에서 일치한다.
  1. (가) 원판 440행 L-5 틀 문장.
     - 바꿀 원문: "주성분은 동적 과도가 아니라 준정적 4점 비틀림이다. 이탈 감속(LAS-b)이 끝난 다음 주기에 명령이 원래 속도로 돌아가며 생긴 비틀림 계단과 연약 패치 침하가, 이탈 뒤 네 다리 기름 기둥 강성(명령 비틀림 1 mm당 후방 좌측 하중 약 −6.5 kN)을 거쳐 하중으로 옮겨졌다." 그리고 같은 단락 뒤쪽의 "모델 상부체는 강체라 비틀림 강성을 크게 보므로 이 값은 보수 쪽이고, 유압유 체적 탄성 계수 β에 민감하다."(새 문장에 들어갔으므로 지운다). 그 사이의 "이 행들은 실행 시작 자세 비 $R_c$ 1.035~1.076으로 운용 시작 조건($R_c \le 1$) 밖이다."는 그대로 둔다.
     - 새 문장: "골의 깊이(이탈 전 약 40 kN에서 한 주기 평균 11.4 kN(×3·VB), 14.1 kN(×1·V0)까지)는 준정적 하중 재분배다. 이탈 감속(LAS-b)이 끝난 다음 주기의 비틀림 계단과 연약 패치 침하가 기름 기둥 강성을 거쳐 옮겨진 것이다. 이 준정적 성분은 두 행 모두 $F_{min}$ 위에 있었다. $F_{min}$ 아래로 내려간 몫(×3·VB 약 2.8 kN, ×1·V0 약 5.6 kN, 그중 4 Hz 위 약 1.2 kN)은 크롤러 이탈 직후 상부체의 1차 좌우 흔들림–롤 모드(1.5~1.8 Hz, 좌우 다리 역위상) 진동이다. 모델 상부체는 강체라 준정적 비틀림 몫은 보수 쪽이고 β에 민감하다. 진동 몫은 크롤러 강성(×1~×3)·이동 중 다리 감쇠·패드 횡 강성 같은 실측 전 가정치에 좌우된다."
     - 확신도: ×3·VB 몫은 높음(모멘트 닫힘 2.5 %, 모델 1.755 Hz 대 기록 1.759 Hz). ×1·V0 몫은 중상(닫힘 33 %, heave 10 % 섞임). 준정적 깊이의 원인을 비틀림으로 본 것은 D-2 진단을 그대로 따른 것이고 다시 검증하지 않았다.
  2. (나) rev18 R18-5 94행 L-5 문구(OC5a).
     - 바꿀 원문: "바닥을 줄였는데 최소가 낮아진 비단조라 시점 민감성이 의심된다."와 "원인 진단(1 ms 다리별 하중, LAS-b 끝 시각과의 관계, 크롤러 강성 의존)은 436.9에서 한다." 두 문장. 그 사이의 "같은 지형의 C-4 4행(R_c > 1)도 RL 이탈 직후 하강(4.20~10.81 kN)을 보였다."와 나머지 문장은 그대로 둔다.
     - 새 문장(첫 원문 자리에 넣고, 둘째 원문은 지운다): "바닥을 줄였는데 최소가 낮아진 비단조는 시점 민감성으로 설명된다. 이 행의 준정적 성분(한 주기 평균 13.6 kN)은 $F_{min}$ 위에 있었다. 하회는 크롤러 이탈 직후 1차 좌우 흔들림–롤 모드(약 1.8 Hz) 진동이 약 7.7 kN을 더 뺀 것이다. 이탈 감속이 이탈 0.15 s 전에야 시작되어(A행·C-8b는 0.43~0.71 s 전) 전방 우측이 최고 속도에 가깝게(19.3 mm/s) 이탈했다. 크롤러 하중 해제와 감속·재가속이 모드 한 주기 안에 겹쳤고, 진동 에너지는 비교 행의 3~10배였다. 둘 중 어느 쪽이 주로 진동을 일으켰는지는 기존 결과로 가르지 못했고 436.9에서 다룬다."
     - 이어서 둘째 원문 자리에 사용자 결정 88 문장을 넣는다: "이 하한은 운용 범위 안의 제어기 한계로 본다(크롤러 이탈부터 그 다리의 `is_lifted` 판정까지 가벼운 다리를 보호하는 동작이 없는 구간). 설계 보완은 LAS-c 별건으로 넘기고, 개입 실행 2행은 436.8 판정 뒤 별건이다."
     - 확신도: 모드와 동적 몫은 높음. 늦은 LAS 시작·최고 속도 이탈과의 연관은 중간(5행 중 늦은 행 1개). 가진원 배분은 낮음.
     - 시간 값(F<F_min 0.158 s, F<F_min + 2 kN 0.212 s)은 R3d 두 경로 값이 같음을 감사가 확인했다(상대 차 3.3e-11).
  3. (다) 원판 440행 첫 문장(괄호 "(크롤러 강성 ×3·VB 8.64 kN 195 ms, ×1·V0 8.51 kN 67 ms)"가 있는 문장)은 그대로 두고, 다음 문장을 (가)의 새 문장 바로 뒤(그 끝 문장 "진동 몫은 … 좌우된다." 다음)에 덧붙인다(사용자 결정 92의 2, 모드를 설명한 뒤에 오도록): "×1·V0 행도 같은 모드다(1.5~1.7 Hz, 이탈 감속은 이탈 0.71 s 전에 시작, 이탈 때 전방 우측 6.5 mm/s). 준정적 성분 14.1 kN은 $F_{min}$보다 4.7 kN 위였고, 67 ms 하회는 진동 몫 약 5.6 kN 때문이다." 확신도: 중상.
  - rev18 R18-5 [정의] 93행의 "원인 진단은 436.9로 넘긴다"는 이 판으로 다음처럼 읽는다: 기전(준정적 성분과 1차 모드 진동 몫)은 사용자 결정 88·91로 정했고, 436.9로 넘기는 것은 가진원 배분(크롤러 하중 해제 대 감속·재가속)과 사용자 결정 88의 두 사실뿐이다.
  - 이 문장들은 판정서 문구의 정의이고 판정 항목이 아니므로 공통 블록에 넣지 않는다. 두 경로 판정 출력의 값(m, 시간 값)은 CD-8대로 K-10으로 대조하고, 위 분해 값은 dynamics-expert 보고를 출처로 적는다(두 경로 대조 대상 아님).
- **[정의] 436.9 입력으로 넘기는 사실**(사용자 결정 88): "C-2 PS-c c-slow 행의 E-5 실패는 탐침 소성 침하로 재레벨이 두 번 일어난 것이고 제어기 오동작이 아니다." "C-4 P3-5 표본 0은 강체 바닥(rigid_base)이라 구조적으로 해당 없음이다." 두 문장을 판정서 한계 절과 436.9 입력 목록에 적는다. C-2 E-5의 등급(`미달`)은 바뀌지 않는다.
- **[사실]** 판정서 한계 절에 그대로 적는다: "rev24는 R3d 두 경로 Chrono 재판정에서 C-5 묶음 등급이 갈린(경로 1 판정 불가, 경로 2 통과) 뒤 정했다. 원인은 C-5 판정 항목 범위의 정의(rev18 R18-2)가 한 경로에만 넘어간 것과 한 경로의 사건 행 이동 압력 창 미구현이었다. rev24는 두 경로에 같은 문장으로 넘기는 공통 판정 정의(CD-1~CD-11)로 C-5 항목 범위, 원 판정기 항목 덮어쓰기 표, 사건 행 판별과 창, READY 없음 처리, T4·T5 대상 행, 사유 문구, C-4·C-8 기록 상태와 기록 값, K-10 실행 정체성 키, 항목 목록을 정했고, 두 경로는 R3e 도구로 C-1~C-8을 다시 판정했다. 숫자 문턱과 등급 순서는 바뀌지 않았다. 정의를 고른 것은 두 경로 출력과 감사 결과(등급·값 포함), 경로 1 도구의 덮어쓰기 목록을 본 뒤이므로, 정의의 선택은 두 경로 출력에서 독립이 아니다. 구현과 재판정 값은 경로마다 따로 만들었다."
- **[사실]** 사건 행 판별(사용자 결정 92의 1). 판정서 한계 절에 그대로 적는다: "rev24의 C-5 사건 행 판별(바닥 사건 4행, 빠른 침하 2행)은 R3d 출력과 감사 결과를 본 뒤 정했다. 근거는 명세 220.6 ①·U-S8-43(침하 속도가 $v_{max}$를 넘는 침하만 바닥 사건으로 보고, G4 5.75 mm/s는 사건 없는 규칙)과 J-5('비사건 사례의 항목 4는 바꾸지 않는다'), 그리고 원 판정기의 같은 갈래다. R3d에서 한 경로가 `event_t_s`가 있는 13행을 사건 행으로 본 것은 규칙 문장에 없는 구현 기준이었다. 이 판별로 `E_G4_` 7행의 이동 압력은 창 없는 ≤ 180 bar 규칙으로 판정된다. 판별은 행별 압력 값으로 정하지 않았다. 작성자는 감사 리포트로 13행 전체의 이동 압력 범위(136.4~189.1 bar)와 G1R_FS24 두 행 값을 읽었고, `E_G4_` 행별 값은 보지 않았다. 판별의 근거는 명세 220.6 ①, J-5, 원 판정기 갈래이고, 판정 결과가 미달이어도 판별은 바꾸지 않는다." 이 문장은 판정서 공개 문장이고 두 경로 지시문에는 넣지 않는다(R24-4).
- **[사실]** 9.2: 이 판은 두 경로 출력의 등급·값, 두 경로의 출력 구조(감사 리포트로 본 키·파일 이름), 경로 1 도구의 일부를 본 뒤 정했다(R24-0). 공통 블록으로 경로 2에 C-5 항목 범위·덮어쓰기 표·사건 행 창 등 보완 항목이 넘어가므로, 결함 사실의 전달은 이 공개로 다룬다(rev18 R18-3, 사용자 결정 61 선례). 이 판의 정의는 경로 2 코드를 보지 않고 정했다.
- 결정 필요: **아니오**(사용자 결정 86·88·89·90·91·92).

##### 결정 표

| 항목 | 정의 | 결정 필요 |
|---|---|---|
| R24-1 공통 정의 | 공통 블록 표지; CD-1 C-5 항목 범위(T4·T5·J11·J-P3·D2·잠금 창 + L2b 원 판정기 항목 + P3 열 항목), CD-2 원 판정기 셈과 닫힌 덮어쓰기 표(D8 셋 재계산, 이동 압력 넷 재계산, U58·R/D8·끝 자세 그대로, t_lift 차 확인 넷), 안 c 조건 (1)~(3), CD-3 비사건 규칙·사건 행 판별(6행)·W 식(바닥·빠른 침하)·로드측 판정 없음·창 차 확인, CD-4 P3 열 개와 빈 등급 행, CD-5 READY 없음 닫힌 표, CD-6 T4·T5 18행, CD-7 사유 문구, CD-8 C-8 기록 값 목록·R3d m 대조, CD-9 C-4 기록 값 목록, CD-10 실행 정체성 키, CD-11 공통 항목 ID·행 수 조건; 적용 범위(L1-R 4행 밖), 인용 출처 | 결정됨: 사용자 결정 86·88·89·90, 92의 1(사건 행 6행) |
| R24-2 도구 보완 | 경로 1: 행 판정(사건 판별·창, 문구, READY 없음, 봉인 목록), 집계(덮어쓰기 표, READY 없음, 사유, C-8·C-4 기록 값, C-4 출력, 항목 목록), 그대로 R22-1·R23-1·R19-4·R19-5; 경로 2: path2_chrono 아래 CD-1~CD-11, 안 c 조건, README 범위 닫음, 봉인 목록 | 결정됨: 사용자 결정 89, 86, 90의 4 |
| R24-3 R3e | S12(부모 S11) → `z4377-p1chrono`·`z4377-p2chrono`(R3d에서, S12 병합 뒤) → `z4373-r3e`(p1 → p2 `--no-ff`) → 감사·integrity → 메인 ff-only·푸시; 봉인 목록 rev16~24, 하네스 rev13~24, R4는 R3e에서; 허용 (가)~(라), 덩어리 표 두 경로(is-ancestor, S12 파일은 (가)); 재사용 R3c 목록 대조, R3c·R3d 쓰기 금지·전후 대조; C-1~C-8 재판정, 실행 전 범주별 허용 차이 키 목록, R3d와 K-10, C-1~C-3 등급 바뀌면 멈춤, K-R 감사 | 결정됨: 사용자 결정 89의 1, 86 |
| R24-4 넘길 문장 | 표지 사이 블록 같은 바이트, 경로별 몫, 넘기지 않는 것, 누락 점검 4가지(봉인본 블록 sha 3자 대조, 원판~rev24 정의 출처 표, 판정서 읽은 것, 항목 목록 행 수·빈 목록·대응), 점검별 시점 | 결정됨: 사용자 결정 89의 2·3 |
| R24-5 공개 | 맞춤 10종 / 공개만 7종 표, 안 c 한계 문장, L-5 틀 문장 교체 (가)·(나)·(다)와 결정 88 문장, R18-5 93행 읽기, 436.9 입력 두 사실, 한계 절 문장, 9.2 | 결정됨: 사용자 결정 86·88·89의 4·90·91, 92(사건 행 판별 공개 문장, (다) 위치) |

##### 결과 본 뒤 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-15 | 92 | 사용자 결정 92(2026-11-15, 둘째 초안 확인 필요 2건): (1) C-5 사건 행은 6행이다(`E_RE1bF_` 4행 + `G1R_FS24_` 2행). `E_G4_` 7행은 비사건 규칙(창 없는 ≤ 180 bar)으로 판정한다(근거: 명세 220.6 ①·U-S8-43, J-5, 원 판정기 갈래). (2) L-5 (다) 문장을 (가) 새 문장 뒤로 옮긴다(뜻은 그대로). 공개 문장 사실 정정(사용자 확인): 판별은 행별 압력 값으로 정하지 않았고, 작성자가 감사 리포트로 13행 전체 범위와 G1R_FS24 두 행 값을 읽은 사실을 적는다 | CD-3, R24-2 [경로 1] 1, R24-5 |
| 2026-11-15 | 91 | 사용자 결정 91(2026-11-15): L-5 틀 문장 수정을 rev24 R24-5에 넣는다. 근거는 dynamics-expert 판정(A5 확인 포함, `L5_proposal_report.md` sha256 앞 `74f74e0d`): 약 1.8 Hz는 1차 sway–roll 로킹 모드이고, OC5a 준정적 RL은 13.6 kN으로 F_min보다 크며 F_min을 밑돈 158 ms는 전부 동적 몫 −7.7 kN 때문이다. A3는 골 깊이의 대부분이 준정적이지만 F_min을 넘은 몫 약 2.8 kN은 같은 모드다. 늦은 LAS(−0.146 s)와 v_max 이탈의 연관은 중간 정도다. A5(×1·V0)도 같은 모드다(준정적 14.1 kN, 진동 몫 약 5.6 kN). 문장은 보고 4절 (가)·(나)·(다)를 그대로 쓴다 | R24-5 |
| 2026-11-15 | 90 | 사용자 결정 90(2026-11-15, rev24 초안 확인 필요 4건, 모두 권고안): (1) CD-5 READY 없음: READY에 기대는 항목은 해당 없음, READY 도달 항목은 미달, 입력 결측은 판정 불가로 둔다. (2) 공통 정의 CD-2·4·5·7·11을 C-1~C-5 모두에 쓴다. (3) C-4는 다른 결측이 없으면 기록 완료이고, 결정 88이 R18-6보다 앞선다. (4) 경로 2가 원 러너 판정기를 직접 실행하는 것(안 c)을 허용하고, 독립성이 줄어든 점은 공개한다 | R24-1, R24-2, R24-5 |
| 2026-11-15 | 89 | 사용자 결정 89(2026-11-15, R3d K-R 감사의 확인 필요): (1) C-5 S-13은 rev24 개정 뒤 두 경로를 다시 판정한다. (2) C-5 판정 항목 범위는 R18-2(P3 포함)로 두 경로가 같게 두고, 경로 2에 R18-2 52행의 뜻을 넘기는 방법은 rev24가 정한다. (3) C-8 기록 상태는 R18-5대로 '기록 완료'이고 경로 2에도 R18-5의 뜻을 넘긴다. (4) 작은 불일치(N1~N5 정의 차이, 사유 문구 없이 판정 불가가 된 S9SL 2행, T4·T5 대상 행 수 18 대 24, C-4 경로 1 출력 없음, C-6·C-7 P3a 비독립)는 공개하고 rev24에서 정리한다. 정의를 맞출 것과 공개만 할 것은 rev24가 나눈다. N1~N5 원인 확인은 python-expert 몫이다 | R24-1~R24-5 |
| 2026-11-15 | 88 | 사용자 결정 88(2026-11-15): C-8a S-9(RL 5,869.6 N, R_c 0.952)는 '운용 범위 안 제어기 한계'로 L-5에 기록하고, 설계(이탈~`is_lifted` 사이 가벼운 다리 보호 공백)는 LAS-c 별건으로 넘긴다. 기전 확신도는 dynamics-expert 판정이 오면 판정서에서 보완한다. 개입 실행 2행은 436.8 판정 뒤 별건이다. C-2 E-5는 탐침 소성 침하로 재레벨이 두 번 일어난 것으로 제어기 오동작이 아니다. C-4 P3-5 표본 0은 rigid_base라 구조적으로 해당 없음이다. 이 둘은 436.9 입력이다 | CD-8, CD-9, R24-5 |
| 2026-11-15 | 86 | 사용자 결정 86(2026-11-15): 경로 2 기록 K-10 '다름' 5건(`tool_gate.head`, `argv[3]` 출력 경로, `created`)은 일치로 처리한다. 다음 개정에서 이 실행 정체성 키를 K-10 제외 키로 명시한다 | CD-10, R24-3 |

#### R25-0. 개정의 공개 (본 자료 목록) — `v5_resume_4368_rules_rev25.md` 12~30행

- 이 작성자(control-expert)가 이 판을 쓰며 새로 본 것(읽기 전용, 2026-11-16)
  - 메인 세션 지시문: 사용자 결정 98(Q1~Q4 모두 감사 권고안)·95·99의 원문, rev24 봉인 사실(S12 `b75d874`, sha `f475cf77`), 함께 정리할 것(실행 전 수정 1~7), 순서·이름(S13, 기존 도구 브랜치, `z4373-r3f`, R3e 폐기).
  - R3e 판정 전 감사 리포트 `r3e_prejudge_audit.md` 전문(338행). 판정 값·등급은 담지 않는다. 담긴 것은 두 경로 코드 위치(파일:줄), 원 판정기 줄 위치, 실행 설정 이름·문자열(`settings.event`, `args.mass_scale` 1.1 행 수 등), R3c 러너 출력 항목 이름·종류 집계(case `*` 행의 judged 항목 수), R3d K-10 차이 키 이름, 실행 스크립트·비교기 sha와 동작이다.
  - 두 경로 구현 보고: 경로 1 보고 `p1_r3e_report.md`(머리 1~12행, 145~194행, Grep 줄), 경로 2 보고 `p2_r3e_report.md`(Grep 줄, 168~176행). 두 보고 모두 판정 값은 담지 않는다. 이로써 이 작성자는 두 경로의 구현 구조(함수·파일 이름, 경로 1의 C1 D8 절단, 경로 2의 P3-6 기록 처리와 P3-7 재구성 방식)를 보았다.
  - 명세 `s6_control_spec.md` 16300~16324행(421 P3-6 READY 한계 표), 15946~15950행(Chrono P3-6 판정 행), P3b 표 11024~11032행.
  - `04_scripts/02_chrono/run_S9.py` 3760~3800행(`p36_ready_limit`)과 5758~5770행(`P3-6_ready` 블록), `P3-6` Grep 줄.
  - `03_src/outrigger_sim/verify/s8_control.py` 1700~1722행(C1 사건 시각 절단과 REANCHOR 제외).
  - 원판 133~136행(5.2 C-4·C-5·C-6·C-7 행), 236~252행(7.4), `d1_selection_rules.md`의 G6 Grep 줄.
  - rev24 봉인본 `.sha256` 줄, 메인·도구 브랜치의 커밋 해시.
  - 봉인 전 재감사 리포트 `rev25_preseal_reaudit.md`의 Grep 줄과 원판 40~50행(1절 기호 표), rev8 R8-2(76~90행). 재감사가 밝힌 대로, 앞 봉인 전 감사 권고 2의 예시 문구("a = 판정 힘, t = 1 ms 순간")는 원판 기호 표와 맞지 않았고 이 작성자가 그것을 CD-8 1에 옮겼다. 이 판은 CD-8 1을 원판 1절 기호 표와 원 판정기 `run_S9.py` 5687~5703행 정의(재감사 리포트 인용; a·t 모두 같은 1 ms 참 F_cyl 계열)로 바로잡았다.
  - 봉인 전 감사 리포트 `rev25_preseal_audit.md` 전문과, 그 지적을 고치려고 연 원 G6 판정기 `04_scripts/03_control/s8/r76_g6_chrono_judge.py` 1~60·320~365행(G6 관문 정의와 READY 없는 실행 처리).
- 이 작성자는 rev24 작성 때 R3d 두 경로 출력의 등급·값과 감사 결과를 보았다(rev24 R24-0). 그래서 Q1(P3-6)이 C-5 등급에 미치는 방향(R3d 경로 1 C-5 미달 7행의 원인 항목에 P3-6이 있었음)을 알고 이 판을 썼다. R3e 판정 출력은 없고 보지 않았다.
- **경로 2 작성자의 기록 열람 공개**(경로 2 보고 8절 그대로): P3-7 재구성 정의를 고르려고 실제 SCM 23행(C-2·C-3·C-4·C-5·C-8)의 기록(`record.npz`, `c2_soil` meta)에 재구성을 돌렸고, 출력한 것은 "t_P·t_LOC가 meta와 1e-6 s 안에서 같은지"의 참·거짓뿐이다. P3-7 상승값과 판정은 보지 않았다. R3d 출력은 이름·키·행 폴더 경로만, 실행 설정은 이름과 문자열만 읽었다.
- **판정 전 감사자가 본 것**(감사 리포트 "실행한 검증" 그대로): rev24 전문, 원판 7.4(238~252), 두 작성자 보고 전문, 앞 감사 `rev24_prehandoff_audit.md` 전문, 경로 1 두 도구의 R3e diff와 해당 함수, 경로 2 `p2_cd.py` 전문과 나머지 파일 diff·`p2_kinds.py`·`p2_core.py` 일부, 실행 초안 6개 전문과 R3d 실행 스크립트 diff, 원 판정기 `s6_control.py`·`s8_control.py`·`run_S8C.py`·`run_S9.py` 해당 줄, 명세 P3-6·P3-7 줄, v5 기준 개정 12 70행, 이름·종류·설정만 출력한 독립 스크립트 9개의 출력. 판정 값·등급은 보지 않았다.
- **봉인 전 감사자가 본 것**(대상 초안 `7bd44387…`, 감사 리포트 권고 7 목록 그대로): 초안 전문, rev24 봉인본(블록 대조), 원판 9.2, `run_S9.py` 3760~3800·5755~5772행, 명세 16296~16326·15944~15950·17470~17478행, `s8_control.py` 1698~1722행, `r76_g6_chrono_judge.py` G6 줄(4~9, 46, 56, 341~348), 경로 1 `chrono_rows_judge_4368.py` 1102~1126행, 경로 2 `p2_kinds.py` G6 Grep 줄, rev19 R19-2 38행, R3d 경로 2 출력의 행 폴더를 따라간 `result.json` `args` 설정 문자열(`rigid_base`, `soil`, `soil_patch`, `pad_variant`, 바닥 각, `mass_scale`)과 npz 키 이름. 판정 값·등급은 보지 않았다. 2차 재감사자가 본 것(대상 `411aab50…`, 리포트 `rev25_preseal_reaudit2.md`의 목록 그대로): 초안 diff 전체와 바뀐 줄, rev8 74~92행, 원판 4.1, `03_src/outrigger_sim/control/extend_start_bound.py` 646~720행, 경로 1 `chrono_rows_judge_4368.py` 1027~1081행, O-C5 행 `step_series.npz` 키 이름. 판정 값·등급은 보지 않았다. 이 작성자는 그 리포트와 `extend_start_bound.py` 646~720행(J-P3 실행 경우 표의 원 정의)을 읽었다.
- 판정서에는 이 목록을 그대로 싣는다. 이 판의 정의는 R3e 판정 출력을 보기 전에 정했지만, R3d 출력을 본 뒤의 연속 개정이므로 "결과 본 뒤 정한 정의"로 적는다.

#### R25-5. 공개 — `v5_resume_4368_rules_rev25.md` 209~245행

- **[사실] 결과를 본 뒤 정한 정의의 공개**: 판정서 한계 절에 그대로 적는다: "rev25는 R3e 판정 출력을 보기 전, R3e 판정 전 감사가 두 경로 구현과 rev24 공통 블록을 대조한 뒤 정했다. 바뀐 것은 C-5 SCM 행 P3-6을 판정 항목으로 하고 한계를 명세 421.1 표(경사 120 s / 평지·패드 B·후방 두 패드 J1·J2·S1 100 s / 그 밖 평지 90 s)로 적은 것, C1 D8 재계산에 원 판정기와 같은 사건 시각 절단을 넣은 것, CD-11 대응 규약(등급 항목·관문·기록)과 조항 ID 대응, C-8 기록 값 목록(다리별 두 계열 시각, O-C5 SCM 행의 D8·G6), 공통 블록 sha 기록 의무다. rev24 범위 안의 구현 결함 네 건(원 판정기 묶음 항목 셈, P3-7 문턱의 질량 배율, K-10 실행 정체성 키, C-4 빈 사유 멈춤)은 새 정의가 아니라 rev24 문장대로 고친 것이다. 숫자 문턱과 등급 순서는 바뀌지 않았다. 이 작성자는 rev24 때 R3d 두 경로 출력의 등급·값을 보았으므로, P3-6을 판정 항목으로 둔 결정(사용자 결정 98의 1)이 C-5 등급을 미달 쪽으로 움직일 수 있음을 알고 이 정의를 적었다. 결정의 근거는 사용자 결정 90의 1(CD-5 'P3-6 READY 도달 미달'), 명세 15948행('Chrono P3-6(100 s)은 판정 행 그대로'), 원 판정기 P3b 블록의 판정이다. 명세 421.1 첫 문장('P3-6은 기록 행이고 판정 수치는 가정이다')과 다른 점은 이 결정으로 정했다."
- **[사실] 독립성 공개**(rev24 R24-5 원 판정기 직접 실행 한계 문장에 더한다): "경로 1은 빠른 침하 W와 T_3에 원 판정기의 함수와 상수를 읽어 쓴다. 그래서 그 재계산 값은 원 판정기 정의에 기댄다. 경로 2는 P3-7 재구성 정의를 고르려고 실제 SCM 23행 기록에서 시각 재현의 참·거짓만 보았고, P3-7 값과 판정은 보지 않았다. P3-6 한계는 두 경로 모두 원 판정기 P3b 블록과 같은 정의를 쓴다. C-3 G6 대응과 READY 없음 처리는 두 경로가 같은 원 G6 판정기(`r76_g6_chrono_judge.py`) 정의에 기댄다. 원 G6 판정기는 C-3의 P3-7을 기록으로 두지만, 이 판은 d1 선정 규칙 11절('P3 + G6-1~G6-7')과 앞서 두 경로가 쓰던 구현을 근거로 C-3 P3-7을 등급 항목으로 둔다."
- **[사실] G6 대응과 원 G6 판정기의 차이**(사용자 결정 100의 2): 판정서 한계 절에 그대로 적는다: "C-3 G6 행의 관문은 원 G6 판정기(`r76_g6_chrono_judge.py`)의 대응(G6-1~G6-5 = P3-1~P3-5, G6-6 = FAULT 없음·READY 도달, G6-7 = P3-8, 따로 READY ≤ 120 s)대로 펼쳤다. READY가 없는 C-3 행에서 원 G6 판정기는 G6-4·G6-5·G6-6·READY ≤ 120 s를 판정 불가로 실패로 세고 G6-1을 이탈 확인부터 끝까지의 크롤러 힘 0으로 대신한다. 이 판은 G6-4·G6-5를 CD-5대로 해당 없음으로, G6-1을 CD-5 P3-1 줄대로 두고, 행 등급은 G6-6·READY ≤ 120 s 미달로 정한다. READY ≤ 120 s 비교에는 원판 7.6의 허용 10⁻⁹ s를 쓴다. 지금 R3d 자료에는 READY가 없는 C-3 행이 없다."
- **[사실] O-C5 rigid_base P3-5**(사용자 결정 100의 1): 판정서 한계 절에 그대로 적는다: "사용자 결정 88의 'rigid_base 행 P3-5는 구조적으로 해당 없음'을 rigid_base 행 전체(C-4와 O-C5 두 행)로 넓혔다. C-8 기록 상태는 사용자 결정 89대로 기록 완료 판단을 따른다."
- **[사실] rev24 R24-5 표를 실을 때**(사용자 결정 101): 판정서가 rev24 R24-5의 "정의를 맞춘 것과 공개만 하는 것" 표를 실을 때, "C-1~C-3 J-P3를 경로 2 묶음 출력에 두지 않음 | 공개만" 줄에는 "rev25 사용자 결정 101로 맞춤(두 경로 모두 ③ 켬 태그 행의 등급 항목)"을 함께 적는다.
- **[사실] C-4 기록 값과 원판 5.2의 차이**(사용자 결정 99): 판정서 한계 절에 그대로 적는다: "C-4 기록 값(CD-9)에는 D8·G6 값을 넣지 않고 rev24 정의를 그대로 둔다. 원판 5.2 C-4 행의 '기록, D8·G6'과 다르다. C-4 행의 D8·G6 기록은 436.9로 넘긴다."
- **[사실]** 9.2: 이 판은 R3e 판정 출력 없이, 두 경로 구현 보고와 판정 전 감사(두 경로의 코드 위치와 구조를 담음)를 본 뒤 정했다(R25-0). 공통 블록으로 두 경로에 보완 항목이 넘어가므로 결함 사실의 전달은 이 공개로 다룬다(rev18 R18-3, 사용자 결정 61 선례). 이 판의 정의를 쓰려고 경로 2 코드를 열지 않았다.
- 결정 필요: **아니오**(사용자 결정 98).

##### 결정 표

| 항목 | 정의 | 결정 필요 |
|---|---|---|
| R25-1 공통 블록 | rev24 블록을 통째로 대신; CD-2 C1 사건 시각 절단(모든 `event_t_s` 수치 행, 사건 판별 불변); CD-3 `event_t_s`만으로 사건 행 아님; CD-4 P3-7 문턱 W_plant 표기, P3-6 판정(C-5)·한계 421.1·역할; CD-5 P3-6 두 갈래·G6 `READY_le_120s`; CD-6 T4-0 관문; CD-7 C-4 포함; CD-8 기록 값 1~9(a·t 정의, 다리별 두 계열 시각, O-C5 rigid_base P3-5 해당 없음, SCM D8 ①~④, G6 값은 G6 대응표); CD-10 출력 경로 원소; CD-11 대응 규약 표(등급 항목·관문·기록, 기록 행 예외, `[case *]` 접미, G6 대응표와 READY 없음 처리, 조항 ID 표); 인용 출처에 원 G6 판정기·d1 11절과 블록 sha 기록 의무; R24-2 [경로 1] 괄호 읽기 | 결정됨: 사용자 결정 98(Q1~Q4), 95(공통 블록 우선, 괄호 읽기), 99(CD-9 rev24 그대로), 100(rigid_base P3-5를 O-C5에, C-3 G6-4·G6-5 READY 없음 해당 없음), 101(C-1~C-3 J-P3 등급 항목), 86·88~92 |
| R25-2 도구 보완 | 경로 1: P3-6 역할, P3-9 기록, G6 펼침, CD-8 값, CD-11 열, 결함 수정(C-4 빈 사유 멈춤), 봉인 목록; 경로 2: C1 절단, P3-6, CD-11 열·구간, CD-8 값, 결함 수정(case `*`, P3-7 W_plant, CD-10 키), README 범위 닫음, 봉인 목록 | 결정됨: 사용자 결정 98 |
| R25-3 R3f | R3e 폐기; S13(부모 S12) → 기존 도구 브랜치에 S13 병합 뒤 추가 커밋 → `z4373-r3f`(R3d에서, p1 → p2 `--no-ff`) → 감사·integrity → ff·푸시; 봉인 목록 rev16~25, 하네스 rev13~25, R4는 R3f에서; 허용 (가)~(라)(rev24·rev25, 결함 수정 포함); 덩어리 표(is-ancestor 0220671과 rev24 도구 커밋); 재사용·쓰기 금지·전후 대조 rev24 그대로; 허용 차이 범주 추가; 실행 스크립트 HEAD 확인·등급 변화 자동 멈춤 | 결정됨: 사용자 결정 98 |
| R25-4 넘길 문장 | rev25 표지 블록과 sha 값, 경로별 몫(경로 2에 경로 1 이름 없음), 누락 점검 4가지(블록 sha 4자 대조) | 결정됨: 사용자 결정 89의 2·3, 98의 3 |
| R25-5 공개 | 결과 본 뒤 정한 정의(P3-6 결정의 근거와 방향), 독립성 공개 추가, G6 대응과 원 G6 판정기의 차이, O-C5 rigid_base P3-5, C-4 기록 값과 원판 5.2의 차이, 9.2 | 결정됨: 사용자 결정 98·99·100 |

##### 결과 본 뒤 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-16 | 101 | 사용자 결정 101(2026-11-16, rev25 봉인 전 재감사 차단 3): C-1~C-3의 J-P3는 두 경로 모두 등급 항목으로 둔다. 경로 2는 적용 행(③ 켬 태그 행)에 J-P3를 더한다. 근거는 rev8 R8-2 "③ 켬 행 전부"이고 R3c·R3d 경로 1 판정과 같다. rev24 R24-5에서 "공개만"이던 것이 "맞춤"이 된다 | R25-1 CD-1 J-P3 적용 행·rev24와 다른 곳, R25-2 [경로 2] 1, R25-3 재판정 |
| 2026-11-16 | 100 | 사용자 결정 100(2026-11-16, rev25 봉인 전 감사의 확인 필요 2건): (1) 사용자 결정 88의 "rigid_base P3-5는 구조적으로 해당 없음"을 rigid_base 행 전체(C-4, O-C5)로 넓혀 쓴다. C-8은 사용자 결정 89대로 기록 완료로 둔다. CD-8의 "해당 없음은 CD-5 것만 값으로 본다"를 이 결정에 맞게 고치고, "rev24와 다른 곳"에 적는다. (2) READY가 없는 C-3 행의 G6-4·G6-5는 CD-5대로 해당 없음이고, 행 등급은 G6-6 미달로 정해진다. 원 G6 판정기와 다른 점은 R25-5에 공개한다 | R25-1 CD-8·CD-11 G6 대응표·rev24와 다른 곳, R25-2, R25-5 |
| 2026-11-16 | 99 | 사용자 결정 99(2026-11-16, rev25 초안 확인 필요 1건): CD-9 C-4 기록 값에는 D8·G6을 넣지 않고 rev24 그대로 둔다. 원판 5.2와 다른 점은 R25-5에 공개하고, C-4의 D8·G6 기록은 436.9로 넘긴다 | R25-1 CD-9(변경 없음), R25-5 |
| 2026-11-16 | 98 | 사용자 결정 98(2026-11-16, R3e 판정 전 감사 Q1~Q4, 모두 감사 권고안): Q1 C-5 SCM 행 P3-6은 판정이고 한계는 명세 P3-6 정의(421.1 표)에서 찾아 공통 블록에 적으며, C-5의 "READY ≤ 120 s"도 같은 근거로 닫는다. Q2 CD-2 C1 D8 재계산에 원 판정기대로 사건 시각 절단(t < `event_t_s`, 수치일 때)을 넣고, `event_t_s`가 있는 비사건 행도 잘리며 결정 92와 부딪히지 않게 쓴다. Q3 CD-11 대응 규약 표를 공통 블록에 넣는다(관문 identity·K1_class·R9-1·R11-4와 T4-0은 관문, D2·P3-9는 기록, C-3 G6은 공통 ID로 펼침, 대응은 조항 ID로 판단). Q4 CD-8 기록 값을 원판 7.4에 맞춰 닫는다("그 시각"과 O-C5 SCM 행의 D8·G6) | R25-1, R25-2, R25-5 |
| 2026-11-16 | 95 | 사용자 결정 95(2026-11-16, rev24 넘기기 전 감사 뒤): 공통 블록과 경로별 몫이 어긋나면 공통 블록이 앞선다. rev24 R24-2 [경로 1] 1의 "`event_t_s` 유무로 사건 행을 정하지 않는다"는 "`event_t_s`만으로는 사건 행이 아니다"로 읽는다. R4 하네스 지시문 때 판정 정의 출처 표 점검을 따로 한다 | R25-1 괄호 읽기·공통 블록 우선, R25-3 R4 |
| 2026-11-15 | 92 | 사용자 결정 92(2026-11-15): (1) C-5 사건 행은 6행(`E_RE1bF_` 4행 + `G1R_FS24_` 2행)이고 `E_G4_` 7행은 비사건 규칙으로 판정한다. (2) L-5 (다) 문장을 (가) 새 문장 뒤로 옮긴다. 공개 문장 사실 정정(사용자 확인) | rev24, R25-1 CD-3·괄호 읽기 |
| 2026-11-15 | 91 | 사용자 결정 91(2026-11-15): L-5 틀 문장 수정을 rev24 R24-5에 넣는다(dynamics-expert 판정, A5 확인) | rev24 |
| 2026-11-15 | 90 | 사용자 결정 90(2026-11-15): (1) CD-5 READY 없음, (2) 공통 정의를 C-1~C-5에 적용, (3) C-4는 다른 결측이 없으면 기록 완료(결정 88이 R18-6보다 앞섬), (4) 경로 2의 원 판정기 직접 실행 허용과 독립성 공개 | rev24, R25-1 |
| 2026-11-15 | 89 | 사용자 결정 89(2026-11-15): (1) C-5 S-13은 rev24 뒤 두 경로 재판정, (2) C-5 항목 범위 R18-2(P3 포함), (3) C-8 기록 상태는 R18-5대로 기록 완료, (4) 작은 불일치 공개와 정리 | rev24, R25-1 |
| 2026-11-15 | 88 | 사용자 결정 88(2026-11-15): C-8a S-9는 운용 범위 안 제어기 한계로 L-5에 기록, 설계 보완은 LAS-c 별건, C-2 E-5와 C-4 P3-5는 436.9 입력 | rev24, R25-1 CD-8·CD-9 |
| 2026-11-15 | 86 | 사용자 결정 86(2026-11-15): 경로 2 기록 K-10 다름 5건(`tool_gate.head`, `argv[3]`, `created`)은 일치 처리, 다음 개정에서 실행 정체성 키를 K-10 제외 키로 명시 | rev24 CD-10, R25-2 [경로 2] 2 (다) |

## 부록 E. 규칙의 판정서 기록 의무 대조표 (도구 추출 강한 항목, 봉인본 26판)

- 추출: `tools/verif/judgement_checklist.py --rules <원판·rev1~rev25 봉인본 26개> --judgement <빈 판정서>`의 강한 절 항목(모두). 의무 원문 칸은 규칙 문장을 그대로 옮겼다. **이 표가 의무 문장을 옮겨 적으므로 점검 도구의 토큰 대조는 이 표에서도 found가 된다. 실제 반영 여부는 '처리' 칸이 정한다.**
- 처리 칸 집계: 본문 반영 116, R3f로 대체됨 21, 해당 없음 4, 확인 필요 24, 하네스 R4 몫 66 (합 231).
- 분류는 이 판정서 작성자의 판단이다(규칙 판·문장의 열쇠말로 먼저 나누고, 손으로 본문 절을 지정). 판정 후 감사(`judgement_postaudit.md` 기록 6)가 표본에서 찾은 오분류(D478, D420·D422·D438, D622·D706, D621·D623·D707·D711, D168, D227, D010·D012·D013·D366·D628·D700, D076·D161·D162·D164·D167, D497·D555·D557·D587)와 재감사(`judgement_reaudit.md` 기록 1, 두 번째 재감사)가 찾은 D214·D281·D077·D082·D495·D118·D196·D199·D200을 이 판에서 고쳤다. 감사는 231항목을 전수로 보지 않았으므로 표본 밖 오분류가 남아 있을 수 있다. 부록 F는 물리적으로 부록 D 앞에 둔다.

| ID | 판:줄 | 의무 원문 | 처리 |
|---|---|---|---|
| D007 | 원판:32 | 규칙·판정서: 부록 A의 봉인 문서 전부(sha256을 `.sha256` 기록과 대조, 모두 일치), `las_p5r4_k1_judgement.md`, `las_k1_rem_judgement.md`, 명세 `00_docs/04_control/s6_control_spec.md` 436·437절, CLAUDE.md 기준값 표. | 본문 1.2절 |
| D010 | 원판:182 | probe와 본 행의 $k$, 바닥 각, $R_c$, probe 개수는 모두 판정서에 적는다. | 본문 4.7절 |
| D011 | 원판:245 | 판정서 종합 문장과 L-5는 결정 뒤에 쓴다 | 본문 0.3·4.7·10.1절(S-9는 결정 60 (A)·88 뒤 L-5 작성) |
| D012 | 원판:254 | 다만 P3a-1(힘 한계) 실패나 실행 오류는 판정서에 따로 적는다. | 본문 4.6절 |
| D013 | 원판:317 | 경로 2 작성자는 판정서에 읽은 것 목록을 적는다(1.2절과 같은 꼴). | 본문 7.1절 |
| D016 | 원판:406 | 판정서 `06_analysis/02_control/verif_matrix/v5_resume_4368_judgement.md`에 다음을 모두 적는다. | 이 판정서(정본 경로는 머리말) |
| D017 | 원판:408 | 이 문서와 부록 A의 sha256, `git_at_start`, 묶음별 실행 기간·러너 로그 경로. | 본문 1·2절 |
| D018 | 원판:409 | 묶음별 상태(8.1), v5 종합 판정, 멈춤이 있었으면 그 조건·사용자 결정. | 본문 0절 |
| D019 | 원판:410 | 4.2 기록 확인 결과(행 수·어긋난 수), 6절 정체성 표(SCM 행 `num_threads_chrono`·`start_env`·`pool`·`planned_pool`·`placement`·훅). | 본문 2.4절(Chrono). 하네스 줄은 R4 뒤 |
| D020 | 원판:411 | 7.2 분류 표(묶음 × 분류 줄 수), K1 막힘 계열 목록, 미작동 줄 해시 비교 결과. | 본문 5.1절(Chrono). 하네스 줄은 R4 뒤 |
| D021 | 원판:412 | 7.3 J_P 판독 결과와 재사용 여부. | 확인 필요(5.2절) |
| D022 | 원판:413 | 10절 사전 예측 대조(맞음·틀림, P-1·P-2 결과 먼저). | 본문 6절(Chrono). P-1·P-2는 하네스 R4 뒤 |
| D023 | 원판:414 | 9절 두 경로: 경로별 작성자·읽은 것, 출력 sha256, K-10 대조 결과, 정의가 다른 곳 표. | 본문 7절 |
| D024 | 원판:415 | O-C5: 5.4 절차 기록(행마다 probe 수, $k$, 바닥 각, $R_c$), 7.4 기록 항목, 멈춤 여부. | 본문 4.7절 |
| D025 | 원판:416 | 시작 조건 밖 행 목록과 그 행들의 $F_{min}$ 하회(L-5 근거). | 본문 10.1절 L-5 근거 표 |
| D026 | 원판:417 | 11절 관문 결과(G-S 목록 sha, `log_errors.py` 출력 경로, `placeholder_scan.py` 결과), 실행 전 감사 리포트 경로·sha. | 본문 9절(일부 확인 필요) |
| D027 | 원판:418 | 14절 한계 문장 L-1~L-5(채울 칸을 값으로 바꾼 것). | 본문 10.1절 |
| D028 | 원판:443 | C-4 켬 팔에서 같은 하회가 다시 나오면 그 값도 L-5 근거로 판정서에 함께 적는다. | 본문 4.4·10.1절 |
| D036 | rev1:81 | 판정서에 저장 `t_a`와 새 `t_a`, 새 기준 실행의 `commands_sha256`을 함께 적는다(기록). | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D037 | rev1:146 | **행정 좌표 명시(판정서 기록 항목)**: 판정서에 다음 한 줄을 적는다. | 본문 10.2절(RV1-10 i·j) |
| D038 | rev1:148 | **행정 끝 한정과 노출 집계(판정서 기록 항목)**: 판정서 한계 절에 "플랜트에는 피스톤 끝 정지와 신장 끝 쿠션이 없다(쿠션은 판독 678~694.8 mm)."를 한정으로 적는다. | 본문 10.2절(RV1-10 i·j) |
| D039 | rev1:187 | 행정 좌표 명시(판정서 기록, `stroke_input_review.md` Q3) | 본문 10.2절(RV1-10 i·j) |
| D040 | rev1:188 | 행정 끝 한정과 노출 집계(판정서 기록, `end_stop_cushion_model_review.md` Q2) | 본문 10.2절(RV1-10 i·j) |
| D049 | rev2:99 | 판정서·L-5에는 경로 1 값을 적고 경로 2 값을 함께 적는다. | 본문 4.7·10.1절(두 경로 값 같음) |
| D050 | rev2:101 | 판정서 종합 문장과 L-5는 결정 뒤에 쓴다. | 본문 0.3·10.1절 |
| D051 | rev2:126 | 통과한 경우 판정서에 파일 이름, raw sha256, LF 정규화 sha256, 그리고 "CRLF 변환만 다름"을 적는다(공개). | 본문 1.1절(해당 판 0) |
| D067 | rev3:52 | 판정서에 묶음마다 다음을 적는다(공개): | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D068 | rev3:58 | 판정서 한계 절에 그 사실을 적는다. | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D070 | rev3:108 | 경로 2는 그 줄을 찾은 식별 필드 이름을 판정서에 적는다. | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D071 | rev3:124 | 판정서에 다음을 적는다: | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D072 | rev3:140 | 개수를 판정서에 적는다. | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D073 | rev3:167 | 공개: 판정서에 시작 틈 패드가 있는 연구 D 줄 수와, 표 목표로 계산했을 때 `ok`가 달라지는 줄 수를 기록으로 적는다. | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D074 | rev3:241 | 없으면 위 구성 정의로 읽는다는 사실을 판정서에 적는다. | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D075 | rev3:268 | 실행 전 감사(verif-protocol-auditor, 원판 A-10)와 경로 1 도구의 기록으로 확인하고, 판정서에 그 기록 경로를 적는다. | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D076 | rev3:287 | 8작업이 모두 같으면 저장 V0 격자를 짝으로 쓴다(V0 태그는 판정서에 "저장(옛 V0 제어기), 표본 해시 같음"으로 적는다). | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D077 | rev3:320 | 판정서에 묶음마다 재계산 항목 수, 재집계만 한 항목의 이름과 수, 불일치 수를 적는다. | 본문 10.2절(TABLE_REAGG·재계산 항목 수) |
| D078 | rev3:320 | 재집계 항목은 R3-G1의 C-5 항목과 같은 판정서 표 TABLE_REAGG에 함께 넣는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D079 | rev3:321 | **한계 공개(판정서 한계 절에 그대로 적는다)**: "원판 9.1은 H-6·H-8의 판정을 두 경로로 하도록 정했다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D080 | rev3:325 | 원판 9.1의 H-6·H-8 경로 2가 관문 값에서 재집계로 낮아지며, 아래 한계 공개 문장으로 판정서에 밝힌다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D081 | rev3:387 | raw sha256이 다르고 LF 정규화 sha256이 기록과 같으면 통과로 보고, 판정서에 파일 이름·두 sha256·"CRLF 변환만 다름"을 적는다. | 본문 1.1절(해당 판 0) |
| D082 | rev3:402 | 판정서에 묶음마다 재계산 항목 수, 재집계만 한 항목의 이름과 수, 불일치 수를 적는다. | 본문 10.2절(TABLE_REAGG·재계산 항목 수) |
| D084 | rev3:403 | **한계 공개(판정서 한계 절에 그대로 적는다)**: "원판 9.1은 C-1~C-5의 경로 2를 시계열에서 다시 계산하는 것으로 정했다. | 본문 10.2절 |
| D085 | rev3:409 | 원판 9.1의 Chrono 경로 2 문구("재계산")가 감시기 항목에서 "재집계"로 낮아지며, 위 한계 공개 문장으로 판정서에 밝힌다. | 본문 10.2절 |
| D086 | rev3:415 | 경로 2는 읽은 파일 이름과 sha256을 판정서의 "읽은 것" 목록에 적는다. | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D116 | rev4:70 | `GIT_AT_START`는 판정서에 적을 채울 칸이다. | 본문 2.1·2.3절 |
| D117 | rev4:70 | 판정서에 도구 파일 sha256을 적는다. | 본문 2.1·2.3절 |
| D118 | rev4:74 | **한계 공개(판정서 한계 절에 그대로 적는다. | 본문 10.2절(rev4 R4-A2 원문) |
| D120 | rev4:82 | 판정서에 행 생성기가 쓴 값을 적는다. | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D122 | rev4:193 | 필드가 이 꼴이 아니면 G-S에서 대응을 확인하고 판정서에 적는다. | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D131 | rev5:34 | 같은 묶음의 기존 도구와의 차이를 판정서에 공개한다: `git diff --no-index <기존> <새 판>`의 요약(줄 수)과 R5-A3 목록의 해당 항목. | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D132 | rev5:36 | 최종 이름과 sha256은 판정서에 적는다. | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D133 | rev5:53 | 436.8에서 돌려 그 결과를 판정서 기록 칸에 적되, H-3·H-4 등급은 새 판(`u3_judge_4368.py` 등)으로 낸다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D134 | rev5:54 | 두 결과가 다른 줄 수를 판정서에 적는다. | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D160 | rev5:87 | 판정서는 위 표를 그대로 옮기고, 묶음마다 새 판과 기존 도구의 결과가 다른 줄 수를 항목 번호와 함께 적는다. | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D161 | rev5:129 | 그 줄 목록과 S-4 하위 값은 판정서에 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D162 | rev5:152 | 다른 강등(424.11.2·424.8.1 `late_loc_revoked`·419.8 늦은 LOC)이 하네스 판정 값 안에서 이미 반영된 경우에는 그 사실과 근거 필드를 판정서에 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D164 | rev5:154 | 판정서에 "436.8부터 새 판이 377을 적용"이라고 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D165 | rev5:159 | 이 값의 근거(사례 정의의 바닥 각)를 dynamics-expert가 확인하고 판정서에 적는다. | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D166 | rev5:166 | dynamics-expert가 그 근사가 부상 판정(≤ 0)에 충분한지 확인하고 판정서에 적는다. | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D167 | rev5:167 | 확인 전에는 F-4 값으로 SA-4를 판정하되, 판정서에 "근사 정의, dynamics 확인 대기"를 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D168 | rev5:183 | 판정서에 그 모듈의 `git diff --stat f46b5ab..GIT_AT_START`와 "기록 전용 변경" 여부를 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D196 | rev6:55 | 판정서는 행마다 러너 값과 새 판 값이 다른 행 수를 D 번호와 함께 적는다. | 본문 7.3a절 |
| D198 | rev6:66 | 판정서에 "10 Hz 구간 대체"를 적는다. | 본문 4.1절 |
| D199 | rev6:76 | 판정서에 S8-A2가 적용된 표본 수(부상 표본 수)를 행마다 적는다. | 본문 7.3a절 |
| D200 | rev6:85 | 판정서에 LOC 취소가 있었던 행 수와, 그 행에서 최종 LOC + 1 s로 계산했다면 강등 결과가 달라졌는지를 기록한다. | 본문 7.3a절(둘째 구절의 대안 계산은 출력에 없음, 12절) |
| D203 | rev6:131 | 두 엔진의 정의가 다르다는 것을 판정서 한계 절에 적는다. | 본문 10.2절 |
| D214 | rev7:31 | 대조한 줄 수와 어긋난 줄 수를 판정서 13절 3항에 적는다. | 본문 2.4절(태그 대조 61/0) |
| D217 | rev7:83 | 판정서에 LOC 취소가 있었던 g6 경로 줄 수를 적는다. | 확인 필요(앞 단계 Chrono 기록, 이 판정서에 값 미기재) |
| D222 | rev7:128 | v1과의 차이는 입력(행 폴더) 선택과 열린 루프 행 제외뿐이다. 판정 정의(D-26~D-39)는 바뀌지 않는다. 판정서에 v2의 sha256과 행마다 폴더를 찾은 방법(`case_log`, `case_log_relocated`, `time_window`)을 적는다(R5-A1 요건 3). | 본문 2.4절 |
| D224 | rev7:136 | `affinity_mask_ok`가 거짓인 행은 원판 6절의 "실행 중 affinity 변경 기록"과 같이 판정서에 적는다. | 본문 2.4절(해당 행 0) |
| D225 | rev7:150 | 도구 커밋 sha와 G-S 배치(하네스 출력 경로, Chrono 배치 폴더)는 판정서에 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D226 | rev7:151 | `git_at_start`는 도구 커밋이거나, 그 위에 판정서·감사 기록만 더한 커밋이다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D227 | rev7:151 | `git diff --stat <도구 커밋>..GIT_AT_START`로 확인하고 판정서에 적는다. | 본문 2.1절(G-S 도구 커밋 = R2 = `git_at_start`, 빈 diff 명시) |
| D229 | rev7:179 | `git_at_start` = 도구 커밋(+ 판정서·감사 기록만) | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D240 | rev8:63 | 대조 방법(T4h meta / 재계산), 대조한 수, 어긋난 수, 재계산 불가 수를 묶음마다 판정서 13절 3항에 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D241 | rev8:125 | Y의 sha와 G-S 배치(하네스 출력 경로, Chrono 배치 폴더)는 판정서에 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D242 | rev8:126 | `git_at_start`는 Y이거나, Y 위에 판정서·감사 기록만 더한 커밋이다. | 본문 2.1절(rev14 R14-3·R14-4로 Y = R2 = `git_at_start`라 `git diff --stat` 대상 없음; 출력 기록은 확인 필요) |
| D243 | rev8:126 | `git diff --stat Y..GIT_AT_START`로 확인하고 판정서에 적는다. | 본문 2.1절(Y = R2라 빈 diff 명시) |
| D244 | rev8:140 | rev8 봉인 → 도구 커밋 Y(`7527fc3`·`4a8a092` 흡수, 경로 1 재계산·T4h 대조·SCM J11 읽기·봉인 확인, 경로 2 봉인 확인·SCM J11 읽기·`P2_CORE_SHA`) → Y에서 G-S 전체, `git_at_start` = Y(+ 판정서·감사 기록만) | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D256 | rev9:73 | 그 행에서 실제 대체 다리 $n_{late}$ > 0이 나오면 H-7·L-e 어느 쪽이든 멈춤이므로 멈추고, 판정서에는 "LS 판별 불가"로 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D257 | rev9:114 | **최종 Y에서 이 판 봉인 뒤 G-S 전체를 다시 돌린 것을 원판 11.2 충족으로 본다.** `git_at_start`는 최종 Y이거나, 그 위에 판정서·감사 기록만 더한 커밋이다(rev8 R8-4의 확인 방법 그대로). | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D258 | rev9:129 | rev9 봉인 → Y에 경로 1·2 수정·rev9 봉인 확인 추가 → 최종 Y에서 G-S 전체, `git_at_start` = 최종 Y(+ 판정서·감사 기록만) | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D267 | rev10:50 | `판정 불가`가 된 행의 처리는 rev9 R9-4 그대로다: 그 행에서 실제 대체 다리 $n_{late}$ > 0이 나오면 H-7·L-e 어느 쪽이든 멈춤이므로 멈추고, 판정서에 "LS 판별 불가"와 그 경우(위 표의 행)를 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D268 | rev10:72 | **최종 Y에서 이 판 봉인 뒤 G-S 전체를 다시 돌린 것을 원판 11.2 충족으로 본다.** `git_at_start`는 최종 Y이거나, 그 위에 판정서·감사 기록만 더한 커밋이다(rev8 R8-4의 확인 방법 그대로). | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D269 | rev10:82 | rev10 봉인 → 최종 Y에 두 경로 수정 + rev10 봉인 확인 → 최종 Y에서 G-S 전체, `git_at_start` = 최종 Y(+ 판정서·감사 기록만) | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D278 | rev11:62 | 판정서에 H-6·H-7 같은 키의 해시 같음 수를 적는다(rev1 RV1-3.2의 H-6↔H-8 같음 기록과 같은 꼴, 멈춤 아님). | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D279 | rev11:72 | 비교 기준은 판정서에 적은 `git_at_start`(최종 Y 커밋 또는 그 위에 판정서·감사 기록만 더한 커밋, R11-7)다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D280 | rev11:81 | 판정서에는 "G-S 행 등급은 판정하지 않음"과 그 등급 수만 적는다. | 본문 9절(G-S 행 등급은 판정하지 않음) |
| D281 | rev11:90 | 판정서 13절 10항에 파일마다 sha256과 배치 폴더 이름을 적는다. | 본문 9.1절(G-S 파일 sha) |
| D282 | rev11:104 | **최종 Y에서 이 판 봉인 뒤 G-S 전체를 다시 돌린 것을 원판 11.2 충족으로 본다.** `git_at_start`는 최종 Y이거나, 그 위에 판정서·감사 기록만 더한 커밋이다(rev8 R8-4의 확인 방법 그대로). | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D287 | rev12:47 | 판정서에는 dirty 기록 행 수와 경로를 적는다. | 본문 2.4절 |
| D288 | rev12:60 | 판정서에 그 값과 `git_at_start`의 같음 여부를 적는다. | 본문 2.1절 |
| D289 | rev12:74 | 판정서에 행마다 폴더를 찾은 방법(`case_log`, `case_log_relocated`, `time_window`)을 적는다(rev7 R7-5). | 본문 2.4절 |
| D290 | rev12:86 | **최종 Y에서 이 판 봉인 뒤 G-S 전체를 다시 돌린 것을 원판 11.2 충족으로 본다.** `git_at_start`는 최종 Y이거나, 그 위에 판정서·감사 기록만 더한 커밋이다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D297 | rev13:20 | 이 판이 봉인(sha256 확정)되기 전에 H-0 출력의 내용을 연 사람이 있으면, 판정서에 누가 무엇을 언제 열었는지 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D299 | rev13:102 | (라) rev8 R8-4의 판정서·감사 기록 | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D300 | rev13:118 | 출력은 untracked `gs_harness_<R>/`·`gs_chrono_<R>/`에 두고, sha는 판정서에 적는다(rev11 R11-6). | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D301 | rev13:121 | "R에서 이 판 봉인 뒤 G-S 전체를 다시 돌린 것을 원판 11.2 충족으로 본다." 본 묶음의 `git_at_start`는 R이거나, R 위에 판정서·감사 기록만 더한 커밋이다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D302 | rev13:121 | 판정서·감사 기록만 더한 커밋은 본 묶음이 끝난 뒤에만 만든다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D303 | rev13:123 | **R11-4(S-12 커밋 정체성)와의 관계**: 대조 기준은 "판정서에 적은 `git_at_start`"이고 묶음마다 따로 적는다(R13-6). | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D305 | rev13:141 | 판정서에는 H-0 사이드카마다 `start`·`end` 기록 수와 두 경로의 K-0 결과를 원판 9.2 "두 경로 정의가 다른 곳" 표로 공개한다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D306 | rev13:143 | 판정서(원판 13절 1항)에 적을 것: | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D330 | rev14:49 | 옮기기 전과 뒤의 파일 목록과 sha256을 판정서에 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D331 | rev14:49 | 판정서에는 S-13 경과로 적고, 판정 등급·사전 예측 대조·한계 문장의 근거로 쓰지 않는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D332 | rev14:74 | (바) rev8 R8-4의 판정서·감사 기록, `00_docs/decision_log.md`·`00_docs/00_roadmap.md`·`00_docs/handoff/session_handoff.md`의 문서 갱신(rev13 R13-4 3 (라)·(마)와 같음) | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D333 | rev14:76 | 조건 대조에는 blob sha256만 쓰고, 작업 복사본 sha256은 판정서에 참고로 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D334 | rev14:85 | 출력은 untracked `gs_harness_<R2>/`·`gs_chrono_<R2>/`에 두고 sha는 판정서에 적는다(rev11 R11-6). | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D335 | rev14:88 | "R2에서 이 판 봉인 뒤 G-S 전체를 다시 돌린 것을 원판 11.2 충족으로 본다." 모든 묶음의 `git_at_start`는 R2이고, 판정서·감사 기록만 더한 커밋은 모든 묶음이 끝난 뒤에만 만든다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D341 | rev14:106 | R2의 러너는 이 키를 기록한다(R14-1, `controller.meta()`의 값). 그래서 재실행 H-0 줄에서는 두 읽기가 같은 사실(실행한 제어기의 R4c30 `enable`)을 본다. 판정서에는 위 표를 원판 9.2 "두 경로 정의가 다른 곳" 표로 싣고, 줄마다 두 읽기의 결과 수(어긋난 줄 수)를 함께 적는다. 등급이 갈리면 원판 S-13이다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D347 | rev14:115 | 판정서에는 사이드카 수, 대조한 기록 수, 어긋난 수를 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D349 | rev14:121 | 판정서에 준 값과 명령 줄을 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D364 | rev15:27 | 사후 개정이므로 판정서에는 이 목록을 그대로 싣는다. D-29 V0 L2b(R15-3)처럼 값을 본 뒤 정한 읽기는 그 사실을 판정 결과 옆에 적는다. | 부록 D(원문) |
| D366 | rev15:34 | 판정서에는 실행 커밋 R2와 판정 도구 커밋 R3을 따로 적는다. | 본문 2.1절 |
| D367 | rev15:36 | R2 뒤의 커밋은 R15-2의 R3 조건을 지키는 R3(와 그 안의 브랜치 커밋)만 허용하고, R3 뒤 판정이 끝날 때까지는 판정서·감사 기록만 더한다. | 본문 2.1절 |
| D369 | rev15:59 | (바) rev8 R8-4의 판정서·감사 기록, `00_docs/decision_log.md`·`00_docs/00_roadmap.md`·`00_docs/handoff/session_handoff.md` | 본문 2.1절 |
| D370 | rev15:67 | R3를 만든 뒤 `git show R3:<파일>`의 LF 바이트 sha256 표(이하 R3 blob 표)를 판정서 부록에 싣는다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D371 | rev15:82 | 판정서에는 행마다 쓴 파일·키를 적는다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D373 | rev15:85 | 판정서에는 그 행들의 t_lift와 `t_lift_basis`, 그리고 "결과 본 뒤 정한 읽기"를 함께 적는다. | 본문 7.3절(V0 3행 `bracket_10Hz`) |
| D375 | rev15:91 | **C-4 끔 팔 `liftoff_approach_slow` 결측 = 허용 결측**: C-4 끔 팔(`--las-off`, `r4368.arm` = `"off"`)에서 `controller_meta.liftoff_approach_slow`의 블록 전체나 하위 키가 없는 것은 rev7 R7-4의 허용 결측(끔 팔은 `liftoff_approach_slow.*` 결측 허용)이고, rev1 RV1-10 b("끔 팔은 블록이 없거나 `enable` 거짓")와 같다. 7.2 분류는 RV1-10 b대로 "LAS 없음"이다. 판정서에는 허용 결측으로 기록한다. 켬 팔에서 같은 키가 없으면 rev7 R7-4대로 `result_missing`이다. | 본문 2.4절 |
| D377 | rev15:102 | 그래서 대조는 blob 기준으로 하고, 작업 복사본 sha256은 판정서에 참고로만 적는다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D383 | rev15:112 | 확인 결과(`gs_psc_check` ok, R4-D 열·사건 키 있음, 1 ms 55,301행)와 두 정체성 파일의 sha256을 판정서에 적는다. | 본문 9.1절 |
| D386 | rev15:132 | 본 자료 목록을 판정서에 싣는다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D407 | rev16:33 | 사후 개정이므로 판정서에는 이 목록을 그대로 싣는다. 값을 본 뒤 정한 읽기(R16-3~R16-9)는 판정 결과 옆에 "결과 본 뒤 정한 읽기"로 적는다. | 부록 D(원문) |
| D409 | rev16:39 | S-13 경과로 판정서에 싣고, 등급·사전 예측 대조·한계 문장의 근거로 쓰지 않는다(rev14 R14-2와 같은 처리). | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D411 | rev16:91 | 판정서에는 묶음별 같음·다름·없음 수를 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D414 | rev16:92 | 판정서에 그렇게 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D415 | rev16:119 | 키 파일과 그 sha256을 판정서에 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D416 | rev16:157 | 래퍼 파일은 추적 경로 밖 `<OUT>\_tools\harness\`에 두고, sha256은 실행 전 감사에서 고정해 판정서에 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D418 | rev16:174 | 판정서에는 이 차례와 staging·공식 폴더의 파일 목록·sha256을 적는다(공개). | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D420 | rev16:204 | 판정서 한계 절에 그대로 적는다: "경로 2 작성자의 rev16 파일 접근은 기술적으로 막지 않았다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D422 | rev16:221 | 이 판의 결함 목록이 두 경로 출력을 본 뒤에 정리된 것이라는 사실(R16-0 6)은 판정서 한계 절에 그대로 적는다: "R4 두 경로 도구의 수정 항목은 메인 세션과 도메인 검토가 첫 두 경로 출력을 대조해 정리했다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D423 | rev16:260 | C-10도 같은 앞 패드 S1이라 F_min 위아래는 물리 예측이 아니고, 판정서에도 그렇게 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D424 | rev16:273 | H-12와 C-9~C-11은 **436.8 판정서 안의 별도 확인(기록 묶음)**이다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D425 | rev16:274 | S-6(C-9), G-5(C-10), G-6(H-12)의 멈춤 질문에 대한 답의 근거로 판정서에 싣는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D426 | rev16:287 | 정체성 도구 `x16_identity.py`의 sha256은 실행 전 감사에서 고정하고 판정서에 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D428 | rev16:304 | 판정서에 그렇게 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D429 | rev16:313 | (위 조건은 ff 전 조건이다.) ff 뒤: **C-1~C-8 판정, C-5 경로 2 재판정, R3 G-S 읽기는 R4 적용 전에 R3 도구로 끝낸다.** 이 문장이 rev15 R15-1 3의 둘째 문장(R2 뒤 허용 커밋과 R3 뒤 커밋 제한)을 대신한다: R2 뒤 메인의 커밋은 R3와 R4(와 그 안의 브랜치 커밋)만 허용하고, R3 적용 뒤 R4 적용 전, R4 적용 뒤 판정이 끝날 때까지는 판정서·감사 기록만 더한다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D430 | rev16:326 | (마) rev8 R8-4의 판정서·감사 기록, `00_docs/decision_log.md`·`00_docs/00_roadmap.md`·`00_docs/handoff/session_handoff.md` | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D431 | rev16:327 | R4 blob 표: R4를 만든 뒤 (다)·(라) 파일의 `git show R4:<파일>` LF 바이트 sha256 표를 판정서 부록에 싣는다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 (갱신 2026-11-16: R4 blob 표는 하네스 판정서 부록 E) |
| D432 | rev16:350 | 판정서에는 폴더 전체 경로와 정체성 파일·도구의 sha256을 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D433 | rev16:374 | 이 귀결은 결과를 본 뒤의 결정으로 판정서에 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D436 | rev16:379 | 대가(행정 −29.45~−31.88 mm, 끝 rut 틈 −29.37~−30.86 mm, 최소 43.7 mm)는 판정서에 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D438 | rev16:387 | **판정서 한계 절에 그대로 적을 문장**: "VB/LS 하네스에서 제어기의 로드 판독은 M2 참값이 아니라 잠김 법칙 값이다. 그래서 다음이 생긴다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D442 | rev16:392 | G-6(R16-9 H-12)은 래퍼 T4h로 공식 확인하는 방식을 그대로 둔다(사용자 결정 51). 이 분석은 원인 근거로만 쓴다. H-12 판정서에는 "D3 오탐의 원인은 R16-15a"를 함께 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D445 | rev16:401 | 436.8 판정서에는 "개선은 436.9에서 다룬다"는 한 줄만 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D460 | rev17:18 | 판정 결과(J-P3, H-7 등)의 값은 이 판을 정하는 데 쓰지 않았다. 판정서에는 이 목록과 "결과 본 뒤 정한 허용 오차"를 그대로 적는다. | 이 Chrono 판정서 범위 밖(하네스 R4·별도 확인 묶음) — 하네스 판정서에서 채움 |
| D461 | rev17:34 | 실행 전 감사가 이 값을 고정하고 판정서에 적는다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D462 | rev17:34 | 새 판과 옛 판의 diff를 판정서에 싣는다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D463 | rev17:37 | 그래서 금지 env 증명은 첫 러너의 env_guard 기록으로 대신하고, 그 사실을 판정서에 적는다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D469 | rev18:17 | 판정서에는 이 목록을 그대로 싣는다. 이 판의 정의는 위 값을 본 뒤 정했으므로 "결과 본 뒤 정한 정의"로 적는다. | 부록 D(원문) |
| D470 | rev18:33 | (라) rev8 R8-4의 판정서·감사 기록, `00_docs/decision_log.md`·`00_docs/00_roadmap.md`·`00_docs/handoff/session_handoff.md` | 본문 2.1절 |
| D471 | rev18:34 | R3b blob 표: (나)·(다) 파일의 `git show R3b:<파일>` LF 바이트 sha256 표를 판정서 부록에 싣고, 판정 전 감사가 감사한 브랜치 끝 blob과 대조한다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D472 | rev18:56 | 이 도구들은 R3에서 돌려도 되고, 판정서에 R3·R3b blob이 같음을 보인다(rev15 R15-2 꼴). | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D473 | rev18:58 | 다른 곳은 판정서에 표로 싣고 python-expert에 원인 확인을 넘긴다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D478 | rev18:78 | 판정서 한계 절에 그대로 적는다: "R3b 두 경로 보완 항목은 메인 세션과 도메인 검토가 R3 두 경로 출력을 본 뒤 정했다. | 본문 10.2절(rev18 R18-3 원문) |
| D480 | rev18:87 | R3 출력은 기록으로 둔다(S-13 경과처럼 판정서에 싣되 등급의 근거로 쓰지 않는다). | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D481 | rev18:88 | **[정의] C-2 S-01·02의 남은 두 값**: 다리 부상 0과 이동 중 압력 ≤ 180 bar는 두 경로가 값으로 내고, 판정서에 행마다 적는다. | 본문 4.2절 |
| D483 | rev18:99 | "접지 유지": 위 `F_min_after_N`의 네 다리 값이 모두 양수(최소 RL 5,869.6 N)이고, 같은 행 `result.json` `p3b`의 부상·재접촉 기록이 0이다(판정서에서 키와 함께 다시 적는다). | 본문 4.7절 |
| D494 | rev19:16 | 판정서에는 이 목록을 그대로 싣는다. 이 판의 정의는 위 질문·해석을 본 뒤 정했으므로 "결과 본 뒤 정한 정의"로 적는다. 정의는 원 규칙 문장과 원 판정 도구에서 정했고, 어느 경로의 값으로 정하지 않았다. | 부록 D(원문) |
| D495 | rev19:28 | 이 차이는 판정서 한계 절에 적는다. | 본문 10.2절 |
| D497 | rev19:47 | 끝 사유가 `run_end`면 어댑터대로 그 기록으로 판정하고, 사유를 판정서에 적는다. | 해당 없음(조건 불성립)(PS-c c-slow 분기 끝 사유가 `run_end`가 아니라 `max_after`, 4.2절) |
| D498 | rev19:55 | 묶음마다 `러너 미판정` 항목 수와 행을 판정서에 싣는다. | 본문 4.1·4.5절 |
| D499 | rev19:56 | 목록에 없는 `kind`는 러너도 세지 않으므로 `러너 미판정`으로 적고, 판정서에 따로 표로 싣는다. | 본문 4.5절(목록 밖 `kind` 0) |
| D501 | rev19:68 | 행마다 러너 t_lift와 D-29 t_lift의 차를 적고, 차가 한 제어 주기(0.1 s)를 넘는 행이 있으면 판정서에 적고 그 묶음은 판정 전에 멈추고 묻는다(rev18 R18-4와 같은 꼴). | 본문 7.3절 |
| D502 | rev19:81 | 덩어리 표(덩어리 머리, 감싸는 함수)를 판정서에 싣는다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D503 | rev19:103 | **[사실]** 원판 9.2는 "상대 출력을 본 뒤에는 어느 경로도 고치지 않는다"이다. 이 판의 정의는 두 경로의 R3b 구현 질문·해석(R19-0)을 본 뒤 정했다. 판정서 한계 절에 그대로 적는다: "rev19 정의는 메인 세션과 도메인 검토가 R3b 두 경로의 구현 질문과 해석을 본 뒤 원 규칙 문장과 원 판정 도구에서 정했다. 두 경로는 같은 정의 문장만 받았고, 구현과 값은 경로마다 따로 만들었다. 정의할 곳의 선택은 두 경로에서 독립이 아니다." | 본문 10.2절·부록 D(원문) |
| D519 | rev20:15 | 판정서에는 이 목록을 그대로 싣고, 이 판의 정의를 "결과 본 뒤 정한 정의"로 적는다. | 부록 D(원문) |
| D520 | rev20:35 | **[사실]** rev19 봉인 전 control-expert 보고(초안 `20c68016` 보고)의 "[확인한 사실] `f46b5ab..59c933b`에서 `r67_g1_screen.py`의 바뀐 줄은 모두 기록 전용 함수 안에 있다"는 함수 밖 상수 `RESUME_K1_KEY`와 그 docstring을 놓친 사실 오류다. rev19 본문 R19-7에는 이 문장이 [정의] 조건 (1)으로만 들어갔고, 그 조건은 문장 그대로는 거짓이 된다. 판정서 한계 절에 그대로 적는다: "rev19 R19-7 조건 (1)은 모듈 수준 상수 정의를 빠뜨려 문장 그대로 대조하면 거짓이었다. rev20 R20-1이 그 이름을 읽는 함수가 모두 기록 전용임을 조건으로 고쳤다. 이 개정은 경로 2의 대조 결과를 본 뒤 했다." | 본문 10.2절·부록 D(원문) |
| D528 | rev21:15 | 판정서에는 이 목록을 그대로 싣고, 이 판의 정의를 "결과 본 뒤 정한 정의"로 적는다. | 부록 D(원문) |
| D530 | rev21:29 | t_b와 다르면 판정서에 적는다(등급은 R15-3 값으로 낸다). | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D531 | rev21:62 | (라) rev8 R8-4의 판정서·감사 기록, `00_docs/decision_log.md`·`00_docs/00_roadmap.md`·`00_docs/handoff/session_handoff.md` | 본문 2.1절 |
| D532 | rev21:63 | R3c blob 표: (나)·(다) 파일의 `git show R3c:<파일>` LF 바이트 sha256 표를 판정서 부록에 싣는다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D533 | rev21:70 | 다르면 판정서에 표로 싣고 그 묶음은 판정 전에 멈추고 묻는다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D534 | rev21:71 | 판정서에 R3b·R3c blob이 같음을 보인다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D535 | rev21:83 | **[사실]** 판정서 한계 절에 그대로 적는다: "rev21은 R3b 경로 1 재판정이 C-1 L2b 6행에서 R19-5로 멈추고, dynamics-expert가 원인을 rev6 D-29 정의의 퇴화(L2b 스텝 끝 NSC 접촉력에서 첫 ≤ 0 표본이 LEVEL 첫 표본; C-1 L2b 6행: D-29가 LEVEL 시작과 0~1 ms, 그 시각 크롤러 30~75 kN; C-2·C-5 L2b 1 ms 23행: LEVEL 전 1 s 0 비율 55~77 %, D-29 시각 크롤러 30~126 kN)로 진단한 뒤 정했다. rev6 D-29가 빌린 정의는 원래 M2 잘림 스텝의 pre/post 분류용이었다. rev3 R3-G5의 조작 정의(명세 309행 '법선력 합이 0이 된 첫 시각' → 5절 첫 ≤ 0)를 같은 기준 문서(v5 기준 rev6 5절) 안의 t_lift,sus로 바꿨다. 새 정의 t_lift,sus는 결과를 본 뒤 정했고, 명세 3절의 '0'을 0.01 W와 '끝까지 이어짐'으로 읽는다." | 본문 10.2절·부록 D(원문) |
| D548 | rev22:16 | 판정서에는 이 목록을 그대로 싣고, 이 판의 정의를 "결과 본 뒤 정한 정의"로 적는다. | 부록 D(원문) |
| D549 | rev22:22 | R3c 실행 스크립트의 `$T45Cases`(18개)와 같은 목록이어야 하고, 판정서에 두 목록이 같음을 보인다. | 본문 2.3절 |
| D550 | rev22:56 | (라) rev8 R8-4의 판정서·감사 기록, `00_docs/decision_log.md`·`00_docs/00_roadmap.md`·`00_docs/handoff/session_handoff.md` | 본문 2.1절 |
| D551 | rev22:58 | 두 경로 모두 바뀐 파일마다 `git diff -U0 f9bc3c7 R3d -- <파일>`의 덩어리 표(덩어리 머리, 감싸는 함수 또는 정의 이름, 위 허용 범위의 어느 것인지)를 판정서에 싣는다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D553 | rev22:63 | 같은 뜻의 키는 각 경로가 판정서에 키 대응표로 밝힌다. | 본문 7.4절·부록 C |
| D555 | rev22:69 | 대조가 다르면 판정서에 표로 싣고 그 묶음은 판정 전에 멈추고 묻는다. | 해당 없음(조건 불성립)(R3c 전후 대조 일치, 2.3절) |
| D556 | rev22:70 | **[정의] 경로 1 실행 스크립트**: R3c 실행 스크립트를 R3d 출력 폴더에 `run_path1_r3d.ps1`로 복사해 쓰고, 그 sha256과 R3c 판과의 diff를 판정서에 싣는다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D557 | rev22:79 | 다르면 판정서에 표로 싣고 그 묶음은 판정 전에 멈추고 묻는다. | 해당 없음(조건 불성립)(R3c 전후 대조 일치, 2.3절) |
| D558 | rev22:89 | **[사실]** 판정서 한계 절에 그대로 적는다: "rev22는 R3c 경로 1 판정에서 C-1~C-3 묶음 등급이 나오고 C-5 묶음 등급이 t45 입력 거부로 멈춘 뒤 정했다. 바뀐 것은 경로 1 집계 도구가 t45 재생 출력의 행을 판정 행에 짝짓는 방법(이름 → 입력 폴더 순서와 `dir` 경로·안쪽 이름 대조)과 두 경로 Chrono 판정 도구의 봉인 목록 정의(rev22 추가)뿐이고, T4·T5 판정 로직·문턱·키와 다른 묶음의 규칙은 바뀌지 않았다. 두 경로는 R3d 도구로 C-1~C-8 판정을 다시 내어 R3c 출력과 대조했고, 러너 출력과 t45 재생 출력은 sha256 대조 뒤 재사용했다. 작성 중 t45 재생 출력의 요약 블록을 열람한 사실은 R22-0에 적었다." | 본문 10.2절·부록 D(원문) |
| D581 | rev23:26 | 판정서에는 이 목록을 그대로 싣고, R23-1을 "결과 본 뒤 정한 정의"로 적는다. | 부록 D(원문) |
| D582 | rev23:53 | 판정서에 R3d C-5 대응 기록의 `name_differs` 행 목록이 이 9행과 같음을 보인다. | 본문 4.5절 |
| D583 | rev23:54 | 판정서에 묶음마다 대응 기록 `rows` 수 = 그 묶음의 L2b·L1-R 행 수이고 C-1~C-3의 `name_differs` 행 목록이 비어 있음을 보인다. | 본문 4.5절 |
| D584 | rev23:90 | **[정의] 덩어리 표, 경로 1**: R22-2대로 바뀐 파일마다 `git diff -U0 f9bc3c7 R3d -- <파일>`의 덩어리 표를 판정서에 싣고, 덩어리마다 어느 판의 허용 범위(rev22 R22-1·R22-2 또는 rev23 R23-1·R23-2)인지 적는다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D585 | rev23:91 | **[정의] 덩어리 표, 경로 2**: R22-2대로 바뀐 파일마다 `git diff -U0 f9bc3c7 R3d -- <파일>`의 덩어리 표를 판정서에 싣고, `git diff -U0 4a80c5a <경로 2 도구 커밋> -- 06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/`의 덩어리 표도 함께 싣는다. | R3f로 대체됨(사용자 결정 110 (2)) — 3.1절에 목록·출력 위치 |
| D586 | rev23:100 | 판정서에 R22-1 짝짓기 기록과 R23-1 대응 기록(`name_differs` 행 목록 = R23-1 예상 영향의 9행, 묶음마다 `rows` 수 = L2b·L1-R 행 수, C-1~C-3의 `name_differs` 빈 목록)을 싣는다. | 본문 4.5절 |
| D587 | rev23:103 | 그 행과 사유를 판정서 표에 싣고 그 묶음은 판정 전에 멈추고 묻는다(고치려면 새 개정). | 해당 없음(조건 불성립)(판정 후 감사 기록 6: 조건 불성립) |
| D588 | rev23:115 | **[사실]** 판정서 한계 절에 그대로 적는다: "rev23은 R3d 통합 전, 경로 1 작성자가 R3c 러너 판정 출력의 행 이름과 `s8_metrics` 키(실행 폴더 안쪽 이름)가 경로 1 집계 도구의 조회 키(판정 행 이름)와 어긋남을 보고한 뒤 정했다. 바뀐 것은 경로 1 집계 도구가 러너 판정 출력의 행과 `s8_metrics`를 판정 행 `dir`의 안쪽 이름으로 찾는 것과 그 대응 기록(대응 대조의 S-11 포함), 두 경로 Chrono 판정 도구 봉인 목록의 rev23 추가뿐이고, 러너 판정 출력, R19-4·R19-5 판정 로직·문턱·키, R22-1 짝짓기, 다른 묶음의 규칙은 바뀌지 않았다. 영향 행은 판정 행 이름과 안쪽 이름이 다른 C-5 9행(LS1·LS4 6행, V0 3행)이고, C-1~C-3 묶음 등급이 바뀌지 않는지는 R3c 출력과의 K-10 대조로 확인한다(결과는 판정서 K-10 표). 작성 중 본 자료는 이름과 키뿐이며 판정 값은 보지 않았다(R23-0)." | 본문 10.2절·부록 D(원문) |
| D613 | rev24:29 | 판정서에는 이 목록을 그대로 싣고, R24-1~R24-3의 정의를 "결과 본 뒤 정한 정의"로 적는다. R24-1 "판정 확인용" 글머리의 수치는 출처(감사 리포트)와 함께 싣는다. | 부록 D(원문) |
| D614 | rev24:36 | 각 경로는 자기 방법으로 구현하고, 이 글머리의 뜻과 다른 구현이 있으면 판정서에 적고 그 묶음은 판정 전에 멈추고 묻는다. | 본문(해당 절) — 확인 필요 |
| D615 | rev24:59 | 직접 실행할 때는 (1) 원 판정기 코드(`03_src`, `run_S8C.py`·`run_S6C.py`)가 R2 `b9f5707`과 실행 커밋 사이에서 diff 0이어야 하고(아니면 S-11), 실행 커밋과 판정기 파일 sha256을 판정서에 적는다. | 본문 2.3절 |
| D617 | rev24:88 | 각 경로는 자기 출력에서 이 범주에 드는 키 이름과 생산 위치를 실행 전에 판정서 키 대응표 초안에 적는다(R24-3 재판정 2). | 본문 7.4절·부록 C |
| D619 | rev24:91 | 원 판정기 소스를 열었으면 판정서 "읽은 것" 목록에 연 파일과 줄 범위를 적는다. | 본문 7.1절 |
| D621 | rev24:104 | 판정서에 sha와 R3d 판과의 diff를 싣는다. | 본문 2.3절·부록 F(diff 본문) |
| D622 | rev24:108 | 판정서에 방법 표(CD-11)를 싣는다. | 본문 7.4절·부록 C 방법 표 |
| D623 | rev24:109 | 저장소 밖 실행 스크립트·비교기는 판정서에 sha와 R3d 판과의 diff를 싣는다. | 본문 2.3절·부록 F(diff 본문) |
| D625 | rev24:129 | (라) rev8 R8-4의 판정서·감사 기록, `00_docs/decision_log.md`·`00_docs/00_roadmap.md`·`00_docs/handoff/session_handoff.md` | 본문 2.1절 |
| D626 | rev24:131 | **[정의] 덩어리 표, 경로 1**: 바뀐 파일마다 `git diff -U0 0220671 R3e -- <파일>`의 덩어리 표(덩어리 머리, 감싸는 함수 또는 정의 이름, 위 허용 범위의 어느 것인지)를 판정서에 싣는다. | 본문 8절·부록 B |
| D627 | rev24:132 | **[정의] 덩어리 표, 경로 2**: 바뀐 파일마다 `git diff -U0 0220671 R3e -- <파일>`의 덩어리 표를 판정서에 싣는다. | 본문 8절·부록 B |
| D628 | rev24:136 | R3d 경로 2 실행 로그는 목록 밖이므로 판정서에 그 sha256을 따로 적는다. | 본문 2.3절 |
| D629 | rev24:139 | **허용 차이 키 목록**: 각 경로는 실행 전에 판정서 키 대응표 초안에 자기 출력 키를 다음 범주별로 적는다: CD-10 실행 정체성 키, CD-7 사유 문구 키, 그리고 이 판이 정한 차이 범주(C-5 묶음 전체; CD-2 표의 재계산 항목 값; CD-3 사건 행 항목; CD-4로 더한 P3 항목; CD-5 READY 없음 항목; CD-6 대상 밖 행의 T4·T5; CD-8 C-8 기록 값·기록 상태·멈춤 목록; CD-9 C-4 기록 출력; CD-11 항목 목록; 표시 문구 정정). | 본문 7.4절·부록 C |
| D630 | rev24:142 | **[정의] 실행 스크립트**: 각 경로는 자기 R3d 실행 스크립트를 R3e 출력 폴더에 복사해 쓰고, sha256과 R3d 판과의 diff를 판정서에 싣는다. | 본문 2.3절 |
| D649 | rev24:182 | **[사실] 원 판정기 직접 실행의 한계**(사용자 결정 90의 4, rev4 R4-A2 한계 공개 문장의 꼴): 경로 2가 원 판정기를 직접 실행하면 판정서 한계 절에 그대로 적는다: "L2b 행의 원 판정기 항목(CD-2 표에서 '원 판정기 셈 그대로'인 항목) 값은 원 규칙의 같은 판정기를 경로 2가 따로 실행해 얻었다. 그래서 두 경로는 그 항목 값의 계산 함수에 함께 기댄다. 경로 2의 독립성은 판정기 실행, 재계산 항목, 셈과 등급 재집계에 있고, '그대로' 항목의 값 계산에는 없다. 재계산 항목(사건 행 판별과 창 등)의 정의를 원 판정기 소스에서 읽어 구현했다면 그 항목도 원 판정기와 같은 정의에 기댄다. 경로 2가 연 원 판정기 소스는 경로 2 판정서의 읽은 것 목록에 있다." 공통 블록의 인용 출처 글머리가 두 경로 모두에 원 판정기 소스를 열었을 때 판정서 읽은 것 목록에 적게 한다. | 본문 10.2절·부록 D(원문) |
| D650 | rev24:183 | **[정의] L-5 틀 문장 교체**(사용자 결정 91, dynamics-expert 판정 `L5_proposal_report.md` 4절, A5 확인). 판정서의 L-5는 아래 새 문장으로 쓴다. 수치는 1 ms 참값(`step_series.npz` `F_cyl_N`, RL)에서 냈다. 준정적 = 한 주기 중심 평균, 진동 = 원값 − 그것이고, 0.8 Hz 저역·1~4 Hz 대역 분해와 0.6 kN 안에서 일치한다. | 본문 10.1절 |
| D664 | rev24:197 | **[정의] 436.9 입력으로 넘기는 사실**(사용자 결정 88): "C-2 PS-c c-slow 행의 E-5 실패는 탐침 소성 침하로 재레벨이 두 번 일어난 것이고 제어기 오동작이 아니다." "C-4 P3-5 표본 0은 강체 바닥(rigid_base)이라 구조적으로 해당 없음이다." 두 문장을 판정서 한계 절과 436.9 입력 목록에 적는다. C-2 E-5의 등급(`미달`)은 바뀌지 않는다. | 본문 11절·10.2절 |
| D665 | rev24:198 | **[사실]** 판정서 한계 절에 그대로 적는다: "rev24는 R3d 두 경로 Chrono 재판정에서 C-5 묶음 등급이 갈린(경로 1 판정 불가, 경로 2 통과) 뒤 정했다. 원인은 C-5 판정 항목 범위의 정의(rev18 R18-2)가 한 경로에만 넘어간 것과 한 경로의 사건 행 이동 압력 창 미구현이었다. rev24는 두 경로에 같은 문장으로 넘기는 공통 판정 정의(CD-1~CD-11)로 C-5 항목 범위, 원 판정기 항목 덮어쓰기 표, 사건 행 판별과 창, READY 없음 처리, T4·T5 대상 행, 사유 문구, C-4·C-8 기록 상태와 기록 값, K-10 실행 정체성 키, 항목 목록을 정했고, 두 경로는 R3e 도구로 C-1~C-8을 다시 판정했다. 숫자 문턱과 등급 순서는 바뀌지 않았다. 정의를 고른 것은 두 경로 출력과 감사 결과(등급·값 포함), 경로 1 도구의 덮어쓰기 목록을 본 뒤이므로, 정의의 선택은 두 경로 출력에서 독립이 아니다. 구현과 재판정 값은 경로마다 따로 만들었다." | 본문 10.2절·부록 D(원문) |
| D666 | rev24:199 | **[사실]** 사건 행 판별(사용자 결정 92의 1). 판정서 한계 절에 그대로 적는다: "rev24의 C-5 사건 행 판별(바닥 사건 4행, 빠른 침하 2행)은 R3d 출력과 감사 결과를 본 뒤 정했다. 근거는 명세 220.6 ①·U-S8-43(침하 속도가 $v_{max}$를 넘는 침하만 바닥 사건으로 보고, G4 5.75 mm/s는 사건 없는 규칙)과 J-5('비사건 사례의 항목 4는 바꾸지 않는다'), 그리고 원 판정기의 같은 갈래다. R3d에서 한 경로가 `event_t_s`가 있는 13행을 사건 행으로 본 것은 규칙 문장에 없는 구현 기준이었다. 이 판별로 `E_G4_` 7행의 이동 압력은 창 없는 ≤ 180 bar 규칙으로 판정된다. 판별은 행별 압력 값으로 정하지 않았다. 작성자는 감사 리포트로 13행 전체의 이동 압력 범위(136.4~189.1 bar)와 G1R_FS24 두 행 값을 읽었고, `E_G4_` 행별 값은 보지 않았다. 판별의 근거는 명세 220.6 ①, J-5, 원 판정기 갈래이고, 판정 결과가 미달이어도 판별은 바꾸지 않는다." 이 문장은 판정서 공개 문장이고 두 경로 지시문에는 넣지 않는다(R24-4). | 본문 10.2절·부록 D(원문) |
| D696 | rev25:29 | 판정서에는 이 목록을 그대로 싣는다. 이 판의 정의는 R3e 판정 출력을 보기 전에 정했지만, R3d 출력을 본 뒤의 연속 개정이므로 "결과 본 뒤 정한 정의"로 적는다. | 부록 D(원문) |
| D697 | rev25:36 | 각 경로는 자기 방법으로 구현하고, 이 글머리의 뜻과 다른 구현이 있으면 판정서에 적고 그 묶음은 판정 전에 멈추고 묻는다. | 본문(해당 절) — 확인 필요 |
| D698 | rev25:61 | 직접 실행할 때는 (1) 원 판정기 코드(`03_src`, `run_S8C.py`·`run_S6C.py`)가 R2 `b9f5707`과 실행 커밋 사이에서 diff 0이어야 하고(아니면 S-11), 실행 커밋과 판정기 파일 sha256을 판정서에 적는다. | 본문 2.3절 |
| D700 | rev25:98 | 크롤러 법선 계열이 강체 바닥 쪽 크롤러 하중을 담는지는 판정서에 적는다. | 본문 4.7절 |
| D701 | rev25:102 | 각 경로는 자기 출력에서 이 범주에 드는 키 이름과 생산 위치를 실행 전에 판정서 키 대응표 초안에 적는다. | 본문 7.4절·부록 C |
| D703 | rev25:145 | 원 판정기 소스를 열었으면 판정서 "읽은 것" 목록에 연 파일과 줄 범위를 적는다. | 본문 7.1절 |
| D704 | rev25:145 | 각 경로 판정서 "읽은 것" 목록에는 넘겨받은 이 공통 블록의 sha256(지시문에 값으로 적힘)을 적는다. | 본문 7.1절 |
| D706 | rev25:163 | 판정서에 방법 표(CD-11)와 P3-7 재구성 관문 점검의 공개(R25-0)를 싣는다. | 본문 7.4절·부록 C 방법 표 |
| D707 | rev25:164 | 저장소 밖 실행 스크립트·비교기는 판정서에 sha와 R3d 판과의 diff를 싣는다. | 본문 2.3절·부록 F(diff 본문) |
| D708 | rev25:185 | (라) rev8 R8-4의 판정서·감사 기록, `00_docs/decision_log.md`·`00_docs/00_roadmap.md`·`00_docs/handoff/session_handoff.md` | 본문 2.1절 |
| D709 | rev25:187 | **[정의] 덩어리 표, 경로 1**: 바뀐 파일마다 `git diff -U0 0220671 R3f -- <파일>`의 덩어리 표(덩어리 머리, 감싸는 함수 또는 정의 이름, 위 허용 범위의 어느 것인지: rev24 정의 / rev25 정의 / rev24 범위 안 결함 수정)를 판정서에 싣는다. | 본문 8절·부록 B |
| D710 | rev25:188 | **[정의] 덩어리 표, 경로 2**: 바뀐 파일마다 `git diff -U0 0220671 R3f -- <파일>`의 덩어리 표를 판정서에 싣는다(허용 범위의 어느 것인지 같은 꼴로). | 본문 8절·부록 B |
| D711 | rev25:192 | **[정의] 실행 스크립트**: 각 경로는 자기 R3e 실행 스크립트(실행하지 않은 판)를 R3f 출력 폴더에 복사해 쓰고, sha256과 R3d 판·R3e 판과의 diff를 판정서에 싣는다. | 본문 2.3절·부록 F(diff 본문) |
| D712 | rev25:206 | **[정의] 판정 후 감사의 손 대조 의무**(판정서 점검 도구가 뽑지 못하는 줄): 판정 후 감사 지시문에 다음을 넣고 손으로 대조한다. | 본문(해당 절) — 확인 필요 |
| D713 | rev25:206 | CD-11 "판정서에서 두 목록을 공통 항목 ID로 맞춘다 … 등급이 같아도 표로 싣는다", 누락 점검 3(판정서 "읽은 것"의 블록 sha), CD-2 표 t_lift 차 확인 줄의 "차를 적는다", CD-3의 창 끝 차 "적는다", CD-8 9의 G6 값 갈음 대응과 CD-11 G6 대응표 ID "적는다", 그리고 rev24에서 그대로인 의무(rev24 R24-0 목록, R24-5 공개 문장, L-5 문장). | 본문 7.1절 |
| D714 | rev25:211 | **[사실] 결과를 본 뒤 정한 정의의 공개**: 판정서 한계 절에 그대로 적는다: "rev25는 R3e 판정 출력을 보기 전, R3e 판정 전 감사가 두 경로 구현과 rev24 공통 블록을 대조한 뒤 정했다. 바뀐 것은 C-5 SCM 행 P3-6을 판정 항목으로 하고 한계를 명세 421.1 표(경사 120 s / 평지·패드 B·후방 두 패드 J1·J2·S1 100 s / 그 밖 평지 90 s)로 적은 것, C1 D8 재계산에 원 판정기와 같은 사건 시각 절단을 넣은 것, CD-11 대응 규약(등급 항목·관문·기록)과 조항 ID 대응, C-8 기록 값 목록(다리별 두 계열 시각, O-C5 SCM 행의 D8·G6), 공통 블록 sha 기록 의무다. rev24 범위 안의 구현 결함 네 건(원 판정기 묶음 항목 셈, P3-7 문턱의 질량 배율, K-10 실행 정체성 키, C-4 빈 사유 멈춤)은 새 정의가 아니라 rev24 문장대로 고친 것이다. 숫자 문턱과 등급 순서는 바뀌지 않았다. 이 작성자는 rev24 때 R3d 두 경로 출력의 등급·값을 보았으므로, P3-6을 판정 항목으로 둔 결정(사용자 결정 98의 1)이 C-5 등급을 미달 쪽으로 움직일 수 있음을 알고 이 정의를 적었다. 결정의 근거는 사용자 결정 90의 1(CD-5 'P3-6 READY 도달 미달'), 명세 15948행('Chrono P3-6(100 s)은 판정 행 그대로'), 원 판정기 P3b 블록의 판정이다. 명세 421.1 첫 문장('P3-6은 기록 행이고 판정 수치는 가정이다')과 다른 점은 이 결정으로 정했다." | 본문 10.2절·부록 D(원문) |
| D716 | rev25:213 | **[사실] G6 대응과 원 G6 판정기의 차이**(사용자 결정 100의 2): 판정서 한계 절에 그대로 적는다: "C-3 G6 행의 관문은 원 G6 판정기(`r76_g6_chrono_judge.py`)의 대응(G6-1~G6-5 = P3-1~P3-5, G6-6 = FAULT 없음·READY 도달, G6-7 = P3-8, 따로 READY ≤ 120 s)대로 펼쳤다. READY가 없는 C-3 행에서 원 G6 판정기는 G6-4·G6-5·G6-6·READY ≤ 120 s를 판정 불가로 실패로 세고 G6-1을 이탈 확인부터 끝까지의 크롤러 힘 0으로 대신한다. 이 판은 G6-4·G6-5를 CD-5대로 해당 없음으로, G6-1을 CD-5 P3-1 줄대로 두고, 행 등급은 G6-6·READY ≤ 120 s 미달로 정한다. READY ≤ 120 s 비교에는 원판 7.6의 허용 10⁻⁹ s를 쓴다. 지금 R3d 자료에는 READY가 없는 C-3 행이 없다." | 본문 10.2절·부록 D(원문) |
| D717 | rev25:214 | **[사실] O-C5 rigid_base P3-5**(사용자 결정 100의 1): 판정서 한계 절에 그대로 적는다: "사용자 결정 88의 'rigid_base 행 P3-5는 구조적으로 해당 없음'을 rigid_base 행 전체(C-4와 O-C5 두 행)로 넓혔다. C-8 기록 상태는 사용자 결정 89대로 기록 완료 판단을 따른다." | 본문 10.2절·부록 D(원문) |
| D718 | rev25:215 | **[사실] rev24 R24-5 표를 실을 때**(사용자 결정 101): 판정서가 rev24 R24-5의 "정의를 맞춘 것과 공개만 하는 것" 표를 실을 때, "C-1~C-3 J-P3를 경로 2 묶음 출력에 두지 않음 \| 공개만" 줄에는 "rev25 사용자 결정 101로 맞춤(두 경로 모두 ③ 켬 태그 행의 등급 항목)"을 함께 적는다. | 본문 10.2절·부록 D(원문) |
| D719 | rev25:216 | **[사실] C-4 기록 값과 원판 5.2의 차이**(사용자 결정 99): 판정서 한계 절에 그대로 적는다: "C-4 기록 값(CD-9)에는 D8·G6 값을 넣지 않고 rev24 정의를 그대로 둔다. 원판 5.2 C-4 행의 '기록, D8·G6'과 다르다. C-4 행의 D8·G6 기록은 436.9로 넘긴다." | 본문 10.2절·부록 D(원문) |
