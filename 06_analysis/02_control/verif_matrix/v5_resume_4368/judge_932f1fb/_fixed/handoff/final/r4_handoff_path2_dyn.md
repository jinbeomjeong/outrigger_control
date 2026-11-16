# 436.8 R4 하네스 지시문 정의 (경로 2-dyn)
rules rev25 sha256: c0b778fd3f53996a2caed37e373975afea591b3c798784843cb9e7eeaac6f233
R4 common block sha256: e451f067db9787c9a8a45b7fc2f3e711970a914b29bc089b37bd94414d259800 (lines between the two markers, LF, markers excluded; 두 경로 같은 바이트, 사용자 결정 114~122)
rule: 아래 블록·몫·뽑은 규칙 글머리만 쓴다. 목록에 없는 앞 판 절이 필요하면 멈추고 묻는다.

## R4 공통 블록
<!-- R4 공통 블록 시작 -->
- **[R4 정의] RD-0 블록의 지위**(결정 114 머리; 결정 113; rev25:197 꼴): 이 블록은 436.8 하네스 R4 재판정의 읽기를 정한다. 봉인 규칙(원판~rev25)은 고치지 않는다. 규칙 문장과 다르게 읽는 곳은 글머리 끝에 "(공개)"로 적었고 판정서 한계 절에 그대로 싣는다. 두 경로는 같은 바이트의 이 블록을 받고, 각 경로 판정서의 "읽은 것" 목록에 지시문에 적힌 이 블록의 sha256을 적는다. 각 경로는 자기 방법으로 구현한다. 이 블록의 뜻과 다른 구현이 있거나, 이 블록과 경로별 지시문이 어긋나면 그 묶음은 판정 전에 멈추고 묻는다. 이 블록에는 어느 경로의 도구 구조 이름(함수·상수·파일·출력 폴더)도 넣지 않았다. 기록 파일·키·행·사건 이름은 판정 정의이므로 넣었다.
- **[R4 정의] RD-1 기준 커밋, 메인 적용, 판정 checkout**(결정 114의 1; 4·5는 결정 115의 1; 6은 결정 117의 4; 7은 감사 권고 8; rev25:176; rev16:299~327 R16-12; rev17:56~57; 공개)
  1. 하네스 도구 브랜치(경로마다 하나)와 R4 통합 브랜치는 R3f `8a0c8432d23c9db0916bf6f9cb9139466bd32551`에서 가른다. R4는 R4 통합 브랜치에서 두 도구 브랜치를 `--no-ff`로 병합한 마지막 병합 커밋이다. R4 조건(rev16 R16-12)의 Chrono 판정 도구·허용 목록 기준점은 R3f..R4다(rev25:176).
  2. R4 조건(모두 참이어야 판정한다. 거짓이면 판정하지 않고 멈춘다, 원판 8.2 S-11): `git diff --name-only b9f5707..R4 -- 03_src 02_params`가 비어 있다. R3f..R4의 모든 변경 파일이 두 경로의 R4 허용 목록 파일과 판정서·감사 기록·`00_docs/decision_log.md`·`00_docs/00_roadmap.md`·`00_docs/handoff/session_handoff.md` 안에 있다. 규칙 파일과 `.gitattributes`는 R3f 아래에 이미 있으므로 R3f..R4에서 바뀌면 허용 목록 밖이다. Chrono 판정 도구(두 경로)와 Chrono 행 정의·manifest는 R3f..R4 diff 0이다. `b9f5707..R4 -- 04_scripts`의 파일 목록 조건(rev16:319, rev18:39)은 규칙 그대로다. R4를 만든 뒤 두 경로 허용 목록 파일의 `git show R4:<파일>` LF 바이트 sha256 표(R4 blob 표)를 판정서 부록에 싣고, 판정 전 감사가 감사한 브랜치 끝 blob과 대조한다. R4 blob과 다른 도구로 낸 출력은 쓰지 않는다.
  3. 메인 적용은 `git merge --no-ff`로 한다. 그 병합 커밋을 M4라 부른다. 봉인 문장 rev16:314("`git merge --ff-only`로 R4에 맞춘다")와 다른 절차다. R3f 뒤 master에 판정서·Chrono 판정 도구 판 문자열 커밋이 있어 R3f에서 가른 R4로는 ff가 성립하지 않기 때문이다(결정 114의 1, 공개).
  4. 판정 전 확인(하나라도 거짓이면 판정하지 않고 S-11로 멈춘다): 두 경로 R4 허용 목록 파일마다 `git show M4:<파일>`과 `git show R4:<파일>`의 LF 바이트 sha256이 같다. `git diff --name-only b9f5707..M4 -- 03_src 02_params`가 비어 있다(결정 114의 1의 구체화, 공개).
  5. 판정 도구는 M4 checkout에서 돈다. 판정 실행 스크립트는 시작 때 `git rev-parse HEAD`가 M4 전체 해시인지 확인하고 아니면 S-12로 멈춘다(rev25 R25-3 "실행 스크립트" (1) 꼴, 공개). 하네스 실행의 기대 실행 커밋 `git_at_start`는 R2 `b9f5707d7f3f7a26230b25f4edbc1fec587ca612`다(rev16:40, rev16:314).
  6. M4 적용 뒤 마지막 판정 실행(두 경로의 재판정, H-11·H-12, C-9~C-11 기록, J_P 판독, 두 경로 대조)이 끝날 때까지 master 커밋은 0이다. 그동안 판정서 초안과 감사 기록은 추적 밖(scratchpad)에 두고, 판정서 커밋 때 함께 넣는다. rev16:313은 이 기간에 판정서·감사 기록 커밋을 허용했지만, 5의 HEAD 확인과 부딪히지 않도록 더 좁게 읽는다(결정 117의 4, 공개).
  7. 하네스 도구 브랜치와 R4 통합 브랜치에서는 `00_docs/`(결정 기록·로드맵·인계 문서)와 판정서·감사 기록을 고치지 않는다. 2의 허용 목록이 이 문서들을 허용하더라도, 메인과 병합할 때 충돌과 손 해결을 피하려는 것이다(감사 권고 8, 공개).
- **[R4 정의] RD-2 봉인 확인 목록**(rev16:333~334 R16-13; rev17:56; rev18~rev25의 R4 글머리; rev25:176): R4 하네스 판정 도구가 확인하는 봉인 목록은 원판과 rev1~rev25의 26판이다. 두 경로가 같은 26판을 확인한다. 실행할 때마다 각 판의 원시 바이트 sha256(LF, BOM 없음)이 아래 값과 같고 같은 폴더 `.sha256` 파일 첫 토큰과도 같아야 한다(rev2 R2-9). 다르거나 파일이 없으면 원판 8.2 S-1로 모든 묶음을 멈춘다. 파일 위치는 `06_analysis/02_control/verif_matrix/`다.

| 판 | 파일 | sha256 |
|---|---|---|
| 원판 | `v5_resume_4368_rules.md` | `9019b405b7a196f28a756e7ca91f443f6241a58bd8e1eee0361483066cb19524` |
| rev1 | `v5_resume_4368_rules_rev1.md` | `d9094fda104e25ac7eb7aea44d7c34d8215a839fc3771aa50b224d43082f02c7` |
| rev2 | `v5_resume_4368_rules_rev2.md` | `497e4614d6780c3201027b3946e3c21da05e2fefe9a3609436bc35ea664c3199` |
| rev3 | `v5_resume_4368_rules_rev3.md` | `dad8dfa68da7a988971f4d687706465289ec7dd95d09079c92215c64e5eae557` |
| rev4 | `v5_resume_4368_rules_rev4.md` | `7ea87a30b08a00263c597d42d3450dc56f68952e8d3205604cb2c5bab5dce14b` |
| rev5 | `v5_resume_4368_rules_rev5.md` | `452a8436c547e4da8d78205556cbb37633842d42cb98c18849cb883d827b3aca` |
| rev6 | `v5_resume_4368_rules_rev6.md` | `809e563971ea451aba7c9d0787c660bdcab1c495af39c513c8f158e09b4fe6c9` |
| rev7 | `v5_resume_4368_rules_rev7.md` | `e81f7d31779b0d69a140c9d90aa4684f3c9299e84aec6af06b13d48d58631502` |
| rev8 | `v5_resume_4368_rules_rev8.md` | `3ecafaaf33d84bb6f34a8cef5401771832a4999e4930f3644caff56eed640e56` |
| rev9 | `v5_resume_4368_rules_rev9.md` | `4cf7843ce469df511d7b99c7236f0b245afae9fb4ba5ad903e1c2da823a59a6d` |
| rev10 | `v5_resume_4368_rules_rev10.md` | `62a0bd8dd6644f78bf37d052e884061d8c14e1cc96e2babc72a6ac0618f12c29` |
| rev11 | `v5_resume_4368_rules_rev11.md` | `9bac452470faf74f921aa7474b3dabad781dac1ba6c3493aff998e69e430617f` |
| rev12 | `v5_resume_4368_rules_rev12.md` | `78f1f99b1bb27473d6e3317c58af195cc3b477829ca1439f390aeeaf32565140` |
| rev13 | `v5_resume_4368_rules_rev13.md` | `383bffc1f2d920dbba5b5a8c0871786a43e983d83e2d5c1e477718257f70973b` |
| rev14 | `v5_resume_4368_rules_rev14.md` | `baedeab499133214804167dede4c4674f9edba4e67bd711dd6418a561f60ac3f` |
| rev15 | `v5_resume_4368_rules_rev15.md` | `0162561c3866412f06ef3be0b3a62434e4a9ba5a37c9003be4df2f373af545ef` |
| rev16 | `v5_resume_4368_rules_rev16.md` | `b38991943a565a020488d1046dd6e0b5c71276cf925715fa5ba844d8819d0683` |
| rev17 | `v5_resume_4368_rules_rev17.md` | `9400660e2f228c3bdfaf26b1eb36cf08a753e7ebc49fbcdedc4a8ab4e0b92422` |
| rev18 | `v5_resume_4368_rules_rev18.md` | `3693a69c3f04eb6c5b26556ec5997d081e38f8f6fa6a581aee66ba512d122a9e` |
| rev19 | `v5_resume_4368_rules_rev19.md` | `7f87b8bb091d23c1bdcd2bf356b732a77bea12c4cfc4853d0ea58f7d239c92b2` |
| rev20 | `v5_resume_4368_rules_rev20.md` | `615a8fbd82f4ef93f1ca76b3fb4d5c24a2e602e63a997c7c56119fcc73fb5531` |
| rev21 | `v5_resume_4368_rules_rev21.md` | `ecd709495f203eae1769ae42e67b5ae5bf2fb457146b558c12e46d636ed03f9a` |
| rev22 | `v5_resume_4368_rules_rev22.md` | `a48a81f9a71091aab40f643d48ae65ba559a5c0c629e02ef3145745a095f9328` |
| rev23 | `v5_resume_4368_rules_rev23.md` | `fa72e1726f87f686093e36f2f3f489d5b135df6392de6aae7fe91b8739b56f97` |
| rev24 | `v5_resume_4368_rules_rev24.md` | `f475cf77bc610802aa36026394cbe8dbae74745c8889ac203b53a6430e1e1e15` |
| rev25 | `v5_resume_4368_rules_rev25.md` | `c0b778fd3f53996a2caed37e373975afea591b3c798784843cb9e7eeaac6f233` |

  - 이 봉인 목록 확인은 각 판의 바이트만 본다. 넘겨받은 글머리 밖의 절을 읽는 범위는 경로별 지시문이 정한다.
- **[R4 정의] RD-3 R4 도구로 하는 일과 하지 않는 일**(rev16:38~41 R16-1; rev16:314~315 R16-12 7·8; rev16:271~274 R16-11a; 원판:298~312 9.1; 사용자 결정 110 (1))
  1. 하는 일: 하네스 묶음 H-1~H-10의 재판정(묶음 H-7은 기록 묶음, 원판 9.1 "집계 1회"), H-11 관문(두 경로), H-12 기록(경로 1, rev16 R16-10 1 (f)), C-9~C-11 기록(두 경로), 원판 7.3 J_P 재사용 판독(두 경로, RD-11). 묶음 H-0은 재판정 대상이 아니다(rev16:39 "H-1~H-10").
  2. 하지 않는 일: 시뮬레이션 재실행(rev16:40), Chrono 행(C-1~C-8)의 판정과 재판정(rev16:315). J_P 판독은 저장 Chrono 기록을 읽지만 Chrono 행 판정이 아니다. 판독 결과로 J_P 재실행이 필요해지면 RD-11 9대로 멈춘다.
  3. 첫 하네스 두 경로 판정 출력(rev16 R16-1 1)은 기록으로만 둔다. 두 경로 모두 그 출력을 입력이나 비교 기준으로 쓰지 않고 열지 않는다.
- **[R4 정의] RD-4 이름 구분**(감사 권고 "이름 겹침"; 결정 122의 3; 원판:119·121; rev16:102; rev25:38; 원판:213; rev21:35): 지시문·출력·판정서에서 다음을 구분해 적는다. "묶음 H-n"은 원판 5.1 표의 하네스 묶음이다(묶음 H-7 = dg3 끔 기록 묶음, 묶음 H-9 = 1단계 main·pressure_only·격자). "멈춤 H-7"은 v5 기준의 멈춤(J-P3 위반, J11 실제 대체 다리 n_late > 0의 VB 쪽, H-12 잠긴 표본 초과)이다. "H-7′"은 las 규칙의 작동 행 규칙이다. "v5 항목 H-9"(M2 pre/post 잘림 분류)는 436.8 판정 항목이 아니다. "멈춤 S-6"은 원판 8.2의 멈춤(원판 7.2 균일 연약 지면 계열의 K1 막힘)이고, "r79 관문 S-1~S-6"은 묶음 H-8 잡음 판정(r79 판정기)의 관문이다. RD-7의 S-6 목록은 멈춤 S-6이다(결정 122의 3). 출력의 키·사유 문구에서도 묶음 이름과 멈춤 이름, 멈춤 S-6과 r79 관문 S-6이 섞이지 않게 한다.
- **[R4 정의] RD-5 K-10 대조와 실행 정체성 키**(결정 114의 5; rev25:102 CD-10; 원판:314~321 9.2; rev16:293): 원판 9.2의 K-10 꼴 대조(등급·참거짓·목록·개수·분류는 완전 일치, 수치는 |a − b| ≤ 10⁻⁹ max(1, |a|, |b|))는 하네스 묶음 H-1~H-10 재판정, H-11 관문, C-9~C-11 기록 항목(rev16:293), RD-11 J_P 판독에 모두 쓴다. 이 대조에서 다음 키를 뺀다: 실행 정체성 키(판정 도구가 돈 checkout 커밋, 실행 시각, 그 실행의 출력 위치; 출력 경로 인자는 인자 목록 전체가 아니라 그 원소만), 앞 판의 빼는 범주(봉인 블록, 도구 판·규칙 설명 문자열, 도구 sha·공개 블록, 입력 파일 경로·sha256 블록), 자유 문장 사유 키. 각 경로는 자기 출력에서 이 범주에 드는 키 이름과 그 키를 만드는 곳을 실행 전에 판정서 키 대응표 초안에 적는다. 제외 키를 결과를 본 뒤 더하지 않는다. C-9~C-11 기록 항목이 이 대조로 맞지 않으면 그 행은 `기록 불완전`이다(rev16:293). rev25 CD-10의 적용 범위(rev25:144)는 Chrono 묶음이었고, 이를 하네스 묶음·C-9~C-11 기록·J_P 판독에 넓히고 자유 문장 사유 키를 빼는 것은 결정 114의 5에 따른 읽기다(공개).
- **[R4 정의] RD-6 출력 확정과 독립성**(원판:314~318 9.2; rev16:41 R16-1 3; rev16:203~204): 각 경로는 자기 출력 파일을 모두 확정하고 sha256을 기록한 뒤에만 상대 출력과 대조한다. 상대 출력을 본 뒤에는 어느 경로도 도구·출력을 고치지 않는다(고쳐야 하면 새 봉인 개정). 각 경로는 상대 경로의 코드·출력·출력 폴더·보고를 열지 않고, 판정서에 읽은 것 목록을 적는다. 재판정에서 두 경로 등급이 다시 갈리면 원판 S-13대로 그 묶음은 `판정 불가`이고 멈추고 묻는다.
- **[R4 정의] RD-7 도구가 내는 멈춤 표지와 등급 확정의 경계**(결정 114의 6·7·8·10; 3은 결정 118의 1·119의 1·3·120의 1·121; J11 적용 묶음은 결정 119의 1; J-P3·S-6 목록 대상 묶음은 결정 122의 1·2; rev16:107~110 R16-7; rev16:366~382 R16-15; rev17:43~49 R17-2a; 원판:276~294 8.2; 공개)
  1. 도구는 다음을 멈춤 표지와 목록으로 낸다. 등급(`미달` 등)으로 바꾸지 않고, 사용자 결정의 답을 도구 안에 넣지 않는다. 각 목록의 열과 표기는 3을 따른다.
     - J-P3 위반(③ 켬 줄·run의 ext_moving `breach_reads` 네 다리 합 ≥ 1): 표지 "멈춤 H-7"과 위반 목록. 한 줄은 (줄·run, 다리) 하나이고 그 다리의 `breach_reads` 값이 1 이상인 것만 싣는다. 대상은 묶음 H-6, H-8, H-9(main·pressure_only의 ③ 켬 줄과 격자 768 run), H-10의 R2 결과 줄·run이다. 묶음 H-1·H-3·H-4의 J-P3는 이 목록에 넣지 않고, 기록 상태 판정과 RD-8 표지(H-3·H-4는 앞 판 관문 G-4도)로만 다룬다(결정 122의 2). 열: 묶음, 결과 파일, 위치, 다리, 키, 설정, 판독 수(그 다리의 `breach_reads`), 최소 간격 [bar], 첫 위반 시각 [s](rev16:109의 열). 묶음 H-9 격자 768 run에도 run마다 같은 꼴로 낸다. family run(`h9_family_F_VB.json`·`h9_family_F_V0.json`의 runs)은 RD-7 목록 전부(J-P3·J11·S-6)와 RD-9 ③ 줄 수에 넣지 않는다. family run은 family 판정 R-1~R-4에만 쓰고, 그 입력과 셈은 앞 판 그대로다(rev4 R4-B5, FS24 64줄). 격자 J-P3 목록은 `h9_grid/grid_*.json`의 768 run이다(rev16:109)(결정 120의 1, 121).
     - J11 멈춤 적용 설정(VB, LS1~LS4, item8(VB), overlap(VB))의 실제 대체 다리 n_late > 0(rev16:102~103): 표지(VB 쪽 "멈춤 H-7", LS는 L-e)와 목록. 적용 묶음은 J11을 판정해 온 묶음 H-6·H-8·H-9·H-10뿐이다. 묶음 H-1·H-3·H-4는 J11을 판정하지 않는다(앞 판 도구 그대로, 결정 119의 1). 한 줄은 (줄, 다리) 하나다. 열: 묶음, 결과 파일, 위치, 다리, 키, 설정, `n_late_fallback_by_leg`의 그 다리 값, 표지(`H-7` / `L-e`).
     - 멈춤 S-6(원판 8.2; 원판 7.2 균일 연약 지면 계열의 K1 막힘): 목록. 대상은 묶음 H-1, H-3, H-4, H-5, H-6, H-7, H-8, H-9, H-10의 R2 결과 파일(RD-7 3) 줄·run이다. family run, H-11·H-12 출력, C-9~C-11 기록은 넣지 않는다(결정 122의 1). 한 줄은 막힌 결정 항목(`would_block` 참 ∧ `r4_due_without_gate` 참인 `decisions` 항목) 하나다. 열: 묶음, 결과 파일, 위치, 결정 번호 k(그 기록의 `resume_k1.slope_clearance_margin.order_gate.decisions` 목록 안에서 0부터 센 번호), 키, 설정, 계열, 그 항목의 `t_loc_s` [s], `n_P`, `n_S`, `dP` [주기].
     - G-5(u3 원판 5.1 VB 고유 실패): 목록. 대상은 묶음 H-3(U-3)의 u3 결과 파일이다. 한 줄은 VB 고유 실패인 u3 기록 하나다. 열: 묶음, 결과 파일, 위치, 키.
     - G-6(u3 rev1 #5, g8 VB 실행의 `WARN_ROD_PRESSURE_FALLBACK`): 목록. 대상은 묶음 H-3의 `v5_rerun/las_k1/u3_g8_VB.json`이다. 한 줄은 그 사건이 있는 g8 VB 기록 하나다. 열: 묶음, 결과 파일, 위치, 키.
     - G-3(H-11) 거짓: 표지와 거짓인 짝 목록. 대상은 H-11의 8쌍(rev16:132~142)이다. 열: 스크립트 이름(파일 이름만, 예 `s9_slope_fix_candidates.py`), 키, 비교 필드, 옵션 없는 출력의 해시, 비교 대상의 해시, 각 쪽 줄 수. 이때 H-3·H-4는 판정하지 않고 멈춘다(rev16:142).
  2. 두 경로의 위 목록·집합은 RD-5대로 완전 일치해야 한다. 다르면 그 묶음은 S-13이다. 두 경로의 G-3 참거짓이 다르면 H-3·H-4는 판정하지 않고 멈추고 묻는다.
  3. 목록 표기(결정 118의 1, 감사 권고 4, 재감사 차단)
     - 줄 식별과 두 경로 대조 단위: (묶음, 결과 파일, 위치[, 다리])이고, S-6은 (묶음, 결과 파일, 위치, k)다. 키·설정·계열과 값 열은 같은 줄에서 함께 맞춰야 하는 값이며(수치는 RD-5 허용), 줄 식별에는 쓰지 않는다. 같은 키가 설정·쌍·오프셋이 다른 여러 줄에 나와도 줄은 위치로 가린다.
     - 결과 파일: 원판 4.3과 rev1 RV1-3.3이 정한 최종 출력 파일이고, 저장소 루트 기준 상대 경로(`/` 구분)로 적는다. 이어쓰기 중간 파일 `*.partial.jsonl`과 정체성 파일 `*.identity.json`은 결과로 읽지 않는다.
     - 위치: jsonl은 `line N`(N = 그 파일의 물리 줄 번호, 1부터, 빈 줄도 센다), JSON은 `results[i]`·`records[i]`·`results[i].runs[j]`처럼 0부터 센 목록 경로다.
     - 키·설정 필드(파일 꼴별, 그 줄·항목 기준):
       - `h1_d1.jsonl`: 키 `job.d1.key`, 설정 `job.setting`.
       - `h5_u9_v0.jsonl`, `h9_stage1.jsonl`, `h10_reuse_rerun.jsonl`: 키 `job.case`, 설정 `job.setting`.
       - `h6_dg3_v4on.json`, `h7_dg3_off.json`, `h8_noise_VB.json`, `h8_noise_V0.json`, `h8_seedext_VB.json`, `h8_seedext_V0.json`, `h9_family_F_VB.json`, `h9_family_F_V0.json`, `h9_grid/grid_*.json`: 키 `results[i].key`, 설정 `results[i].v5_setting`. 격자·family의 `results[i].runs[j]`는 위 `results[i]`의 키·설정을 쓴다. family run을 RD-7 목록에 넣는 일은 없다(RD-7 1). 판정서 공개 표에서 family run을 가리킬 때만 결과 파일과 위치를 `h9_family_F_VB.json`·`h9_family_F_V0.json`의 `results[i].runs[j]`로 적는다(결정 119의 3, 120의 1, 121). family 판정 R-1~R-4의 입력은 이 문장의 범위 밖이다.
       - `v5_rerun/las_k1/u3_*.json`: 항목(`results[i]` 또는 `records[i]`)의 `key`, 없으면 문자열인 `id`가 키이고, 설정은 항목의 `v5.v5_setting`이다.
       - `v5_rerun/las_k1/u6_*.json`: 항목(`records[i]`)의 `case`가 키이고, 설정은 항목의 `v5.v5_setting`이다.
       - 위에 없는 꼴이거나 필드가 없으면 그 값은 `null`이다.
     - 입력 필드: J-P3는 그 줄·run의 `hydraulics_record.extend_bound_check`(u3·u6 항목은 `v5.hydraulics_record.extend_bound_check`), J11은 `lock_window_alignment`(J11 적용 묶음 H-6·H-8·H-9·H-10의 줄·run), S-6은 `resume_k1.slope_clearance_margin.order_gate.decisions`(u3·u6 항목은 `v5.` 아래)다. 같은 항목에 최상위 `extend_bound_check`가 함께 있으면 두 `breach_reads`가 같은지 보고, 다르면 그 줄의 J-P3는 `판정 불가`다(공개).
     - 값 표기: 계열 이름은 이 글머리의 글자 그대로 `균일 연약` / `패치·처방 침하` / `강체`다(가운뎃점은 U+00B7). 다리는 `FL`·`FR`·`RL`·`RR`이다. 정수 값(판독 수, n_late, `n_P`, `n_S`, `dP`, k, N)은 JSON 정수로 적는다. 실수 값(`t_loc_s`, 시각 [s])은 기록의 JSON 수를 그대로 옮기고 반올림하거나 문자열로 바꾸지 않는다. 최소 간격 [bar]는 기록 Pa ÷ 10⁵의 계산값이다. 없는 원소는 `null`이다.
     - 정렬: 묶음 → 결과 파일(문자열 순) → 위치(N 또는 목록 번호를 앞에서부터 수 순) → 다리(`FL`, `FR`, `RL`, `RR` 순) → k(수 순).
  4. 표지를 등급으로 읽는 일(결정 51·102·3과 사용자 질문)은 판정서가 한다. 도구는 판정서의 읽기를 미리 하지 않는다. rev16:374의 "`미달` 확정"을 도구 등급으로 넣지 않고 판정서에서 읽는 것은 결정 114의 6에 따른 읽기다(공개).
- **[R4 정의] RD-8 J-P3 입력 형식**(결정 114 "E축 보강"; 결정 117의 1; 결정 118의 3; rev3 R3-C8; rev4 R4-A2 J-P3 글머리; rev8 R8-2; rev16:109; 원판:323~325 9.3): J-P3를 판정하는 모든 하네스 줄과 run에서 `hydraulics_record.extend_bound_check.breach_reads`는 정수 4개의 목록(다리 순서 FL, FR, RL, RR, 각 값 ≥ 0)이어야 한다. 길이가 4가 아니거나(빈 목록 포함) 정수가 아닌 원소가 있으면 그 줄·run의 J-P3는 `판정 불가`(입력 형식 결함)이고, 합 0으로 통과시키지 않는다. 묶음마다 이 판정 불가 수를 적는다. J-P3를 실행기가 기록한 상태로 판정하는 묶음 H-1·H-3·H-4는 그 묶음 판정 도구를 R4에서 고칠 수 없으므로, 같은 경로의 R4 도구가 이 세 묶음의 실행 기록에서 `breach_reads`를 읽어 길이가 틀린 줄 수를 묶음마다 따로 낸다(RD-9 꼴). 기록에 `breach_reads`가 있는 줄만 센다(입력 필드는 RD-7 3). 수가 0이면 기록 상태로 낸 판정을 그대로 두고, 1 이상이면 그 줄의 J-P3는 `판정 불가`다(결정 117의 1). 이 수가 1 이상이면 그 도구는 그 묶음에 관문 표지 `J-P3 입력 형식(RD-8)`을 낸다. 두 경로가 같은 표지 이름을 쓴다. 판정서는 이 표지가 있는 묶음을 원판 9.3대로 `판정 불가`로 올린다(결정 118의 3). 같은 도구는 이 세 묶음의 VB 줄 가운데 기록된 J-P3 상태(`h1_d1.jsonl` 줄의 `d1.j_p3`, u3·u6 항목의 `v5.j_p3`)가 `pass`인데 RD-7 3의 J-P3 입력 필드에 `breach_reads`가 없는 줄 수도 함께 내고, 0이 아니면 같은 표지를 낸다(빈 통과 막기, 재감사 덧붙임, 공개). 그 밖의 J-P3 정의(로드 판독 유무, 헤드 전용 선언, T4h 찾기, 설정 결함 멈춤)는 앞 판 그대로다.
- **[R4 정의] RD-9 ③ 켬 줄 수**(결정 114 "E축 보강"; 원판:209 개정 11 #4; 원판:287 S-8; 원판 4.1): 각 경로는 묶음마다 ③ 켬 줄·run 수(원판 4.1 태그 판별)를 출력에 싣는다. family run은 이 수에 넣지 않는다(RD-7 1, 결정 121). 묶음 정의에 VB(③ 켬) 줄이 들어 있는 판정 묶음 H-1, H-3, H-4, H-6, H-8, H-9, H-10에서 이 수가 0이면 그 묶음은 판정하지 않고 멈춘다(S-8). 이 수는 그 묶음의 줄 태그를 읽는 같은 경로의 다른 도구가 내도 된다(그 묶음의 판정 도구를 R4에서 고칠 수 없을 때).
- **[R4 정의] RD-10 J11 기록 블록 결측**(결정 114 "E축 보강"; 결정 119의 1; rev3 R3-C7; rev16:102~103 R16-6; 원판 9.3; 공개): 적용 묶음은 J11을 판정해 온 묶음 H-6·H-8·H-9·H-10뿐이다. 묶음 H-1·H-3·H-4는 J11을 판정하지 않는다(앞 판 도구 그대로, 결정 119의 1). J11 멈춤 적용 설정(VB, LS1~LS4, item8(VB), overlap(VB))의 하네스 줄에서 `lock_window_alignment` 블록이 없거나 객체가 아니면, 그 줄의 J11은 실제 대체 다리 n_late > 0 멈춤 조건을 확인할 수 없으므로 `판정 불가`다. 블록이 있고 `fallback_legs`의 다리가 있는데 `n_late_fallback_by_leg`의 그 다리 값이 없거나 None이면 앞 판 그대로 `판정 불가`다(rev16:102). J11 기록 설정(V0~V8·L1·L2, pressure_only)의 블록 결측은 기록 "입력 없음"으로 센다. 묶음마다 판정 불가 수와 입력 없음 수를 적는다. rev3 R3-C7은 대체 다리가 있는 줄의 None만 정했고, 블록 자체가 없는 멈춤 적용 줄을 판정 불가로 읽는 것은 결정 114에 따른 읽기다(공개).
- **[R4 정의] RD-11 J_P 재사용 판독(원판 7.3)**(결정 114의 4; 원판:231~236 7.3; 원판:139 5.2 재사용 행; 원판:312 9.1; 공개): 원판 7.3 조건 1·2를 두 경로가 아래 같은 정의로 판독한다. 이 정의는 앞서 두 경로 판독 정의가 다르던 네 곳(사건 이름의 콜론 접미, 사건 기록의 원소 꼴, 그림자 줄 중복, 행 집합)을 맞춘 것이다. 이 블록 작성자는 J_P 판독 출력을 보지 않았다.
  1. **입력**: 저장 J_P 배치 두 개 `07_results/S9/batch_V5-JP-VB_20261108_115631`, `07_results/S9/batch_V5-JP-V0_20261108_131212`의 `batch.json`과 각 행 폴더의 `controller_events.json`, 그리고 그림자 기록 `06_analysis/03_hydraulic/coupled/v5/las/shadow_jp_b0.jsonl`.
  2. **행 집합**: 두 배치 `batch.json`의 `cases` 전부다(배치 순서 VB, V0; 각 배치 안은 `cases` 순서). 행 수 기대값은 12로 고정하고 실행 인자로 바꾸지 않는다. 행 수가 12가 아니면 판독을 내지 않고 원판 8.2 S-15로 멈춘다(입력 문제이고 판독 결과가 아니므로 "재사용 거짓"으로 두지 않는다, 결정 115의 4). 근거: 원판 5.2 재사용 행이 J_P 12행을 저장 배치 `V5-JP-{VB,V0}`로 정하므로, 행을 사람이 고른 폴더가 아니라 배치 기록에서 얻는 쪽이 원판 뜻에 가깝다.
  3. **행 폴더와 run id**: case 기록에서 `s8c_check.result_json`, `s6c_check.result_json`, `result_json`의 순서로 처음 실제 파일을 가리키는 경로를 쓴다. 경로 문자열에 `07_results/`가 있고 그대로는 파일이 없으면 저장소 루트 아래 `07_results/` 뒷부분으로 찾는다. 셋 모두 없으면 `<배치 폴더>/<case>/result.json`이다. 이것도 없으면 그 행은 "사건 기록 판독 불가"다(7). 행 폴더는 그 `result.json`이 있는 폴더이고, run id는 `<행 폴더의 부모 폴더 이름>/<행 폴더 이름>`이다.
  4. **사건 기록 꼴**: `<행 폴더>/controller_events.json`은 JSON 목록이고, 모든 원소가 문자열이며 앞뒤 공백을 뺀 문자열 전체가 `C2Event(t_s=<수>, name=<파이썬 문자열 표기>)` 꼴이어야 한다. 사건 이름은 그 문자열 표기의 값이다. 파일이 없거나, 목록이 아니거나, 한 원소라도 이 꼴이 아니면(사전(dict) 원소 포함) 그 행은 "사건 기록 판독 불가"다(7). 근거: 사건 기록을 쓰는 코드는 사건마다 `C2Event`의 문자열 표기를 목록으로 쓴다. 원판 7.3 3이 말하는 "코드로 확인한 형식"은 이 꼴 하나다.
  5. **사건 이름 비교**: 사건 이름을 첫 `:` 앞(기본 이름)과 뒤로 나눈다(`:`가 없으면 이름 전체가 기본 이름). R4c30 적용 수 = 기본 이름이 `INFO_LOC_FLAT_SOIL_MARGIN`과 글자 그대로 같은 사건 수다(접미 `:<mm>` 유무와 무관). `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order`는 기본 이름이 다르므로 세지 않는다. 토양 모드 시작 수 = 기본 이름이 `soil_mode_start`인 사건 수다. 근거: 원판 7.3 2는 R4c30 적용 사건을 접미 없는 이름 `INFO_LOC_FLAT_SOIL_MARGIN`으로 부르고, 제어기는 이 사건을 `INFO_LOC_FLAT_SOIL_MARGIN:<mm>`으로 쓴다. 기본 이름 비교는 접미 유무와 상관없이 적용 사건을 모두 세므로 "적용이 한 번도 없음"이라는 원판 뜻에 가장 가깝다.
  6. **그림자 줄**: 그림자 기록의 각 줄(JSON 객체 하나)에서 최상위 `job.chrono_run` 값의 역슬래시를 `/`로 바꾼 것을 그 줄의 run id로 쓴다. 행마다 같은 run id의 그림자 줄 수 n을 센다. 조건 1(LAS-b 그림자 미작동) = (n = 1) ∧ 그 줄의 `status` = `"silent"` ∧ `first_fire_t_s` = null이다. n = 0이거나 n ≥ 2이면 그 행은 "그림자 판독 불가"(사유 "그림자 줄 수 n")이고, 판독을 내지 않고 멈추고 묻는다. 이 경우를 조건 1 거짓이나 "재사용 거짓"으로 두지 않는다(입력 문제와 판독 결과를 섞지 않는다, 결정 115의 4). 근거: 원판 7.3 1은 행마다 그림자 판독 하나를 전제한다. 같은 run의 줄이 없거나 여럿이면 어느 줄이 그 행의 판독인지 규칙이 정하지 않으므로 파일 순서에 기대지 않는다.
  7. **판정**: 입력 문제 세 가지(2의 행 수 ≠ 12, 3·4의 사건 기록 판독 불가, 6의 그림자 판독 불가)는 판독 결과가 아니다. 하나라도 있으면 도구는 멈춤 표지(S-15, 사건 기록 판독 불가, 그림자 판독 불가)와 해당 행·사유를 내고 재사용 참거짓을 내지 않는다. "재사용 거짓"으로 두지 않는다(결정 115의 4, 결정 116). 원판 7.3 끝 문장("판독 불가이면 재실행")과 다르게 읽는 것이다(공개). 입력 문제가 없을 때만 판독한다: 조건 2(K1 무영향) = R4c30 적용 수 = 0 ∧ 토양 모드 시작 수 = 0. 재사용 = 모든 행의 조건 1 ∧ 모든 행의 조건 2.
  8. **출력 항목**: 행마다 배치 이름, case, run id, 사건 기록 판독 불가 여부와 사유, 사건 수, R4c30 적용 수, 토양 모드 시작 수, 그림자 줄 수, 그림자 판독 불가 여부, 조건 1, 조건 2. 묶음에 행 수, 멈춤 표지(S-15, 사건 기록 판독 불가, 그림자 판독 불가)와 재사용 참거짓(멈춤 표지가 있으면 내지 않음). 두 경로는 이 항목을 RD-5대로 대조한다.
  9. **처리**: 7의 멈춤 표지(S-15, 사건 기록 판독 불가, 그림자 판독 불가)가 한 경로에라도 있으면 J_P 판독을 쓰지 않고 멈추고 묻는다. 두 경로의 재사용 참거짓이나 행별 항목이 다르면 J_P를 재사용으로 쓰지 않고 멈추고 묻는다. 두 경로가 모두 재사용 거짓이면, 원판 7.3 끝 문장(묶음 `JP` 재실행 판정)이 rev16:315("R4 뒤 Chrono 판정은 하지 않는다 … 새 봉인 개정")와 부딪히므로 멈추고 새 봉인 개정 여부를 묻는다. 두 경로가 모두 재사용 참일 때만 저장 판정을 재사용 표시로 쓴다.
- **[R4 정의] RD-12 C-9~C-11 기록의 정체성과 순서**(rev16:278~294 R16-11b; rev16:269~275 R16-11a; 결정 114의 10): C-9~C-11 기록은 두 경로가 R16-11b 2의 행 폴더 파일을 따로 읽어 R16-11의 기록 항목과 R16-11b 1의 정체성으로 낸다. 기록 묶음이므로 원판 8.1 등급을 만들지 않는다. 두 경로는 C-9~C-11 기록을 묶음 H-3·H-8의 등급 확정보다 먼저 확정해 낸다(S-6·G-5 질문의 근거 자료, 결정 114의 10).
- **[R4 정의] RD-13 묶음별 항목 목록**(결정 115의 5; rev25:103 CD-11 꼴; 원판:314~321 9.2; 공개): 두 경로는 판정·기록하는 묶음(H-1~H-12, C-9~C-11, J_P 판독)마다 항목 목록을 낸다. 열은 항목(그 경로의 항목 이름), 근거 조항(판:절 또는 판:행, 예: `원판 7.2`, `rev16:102`, `u3 원판 5.1`), 구분(`등급 항목` / `기록` / `관문`)이다. 멈춤 표지(RD-7)를 내는 항목은 구분 `관문`으로 적는다. 근거 조항은 넘겨받은 글머리에 있으면 그 판:절을 적고, 넘겨받지 않은 앞 판 정의는 도구가 구현한 그대로 두며 근거 조항을 도구의 주석·README 인용에서 옮겨 적는다. 근거 조항을 채우려고 넘겨받지 않은 앞 판 절을 새로 열지 않는다(결정 117의 2). 목록은 출력 파일과 함께 확정하고 sha256을 기록한다(RD-6). 한 경로에만 있는 항목이 있어도 멈추지 않는다. 두 목록은 판정서 대조(K-R)에서 근거 조항으로 맞춘 표로 싣고 공개한다. 묶음 등급이 두 경로에서 갈리면 앞 판 그대로 S-13이다(RD-6).
<!-- R4 공통 블록 끝 -->

## 이 경로 몫
### 2.3 2-dyn 몫 (지시문 글머리 초안)

- **받는 것**(이 파일 안에 모두 있다)
  1. R4 읽기 블록(이 파일 위, sha256은 이 파일 머리 줄).
  2. 이 몫.
  3. 뽑은 규칙 글머리(이 파일 아래, 글머리마다 `<!-- 행 ID 파일:첫 행 -->` 표지): 원판 전문(C-00), 앞 판 글머리 C-01~C-24(rev1·rev2·rev3·rev4·rev6·rev8·rev9·rev11·rev12·rev13에서 고른 것), rev16 이후 글머리 P2-01~P2-50(rev16 R16-10 3 표의 [정의] 글머리와, 사용자 결정 114가 더한 R4 조건·허용 목록 (라)·봉인 목록 글머리). 다른 경로의 이름이 있던 여섯 곳은 이름을 지운 문장으로 바뀌어 있다.
- **열어도 되는 것**(이 목록 밖은 열지 않는다)
  1. 이 파일.
  2. 원 규칙 문서(원판 부록 A, 읽기만): `06_analysis/03_hydraulic/coupled/v5/` 아래 `v5_criteria.md`와 개정 1~12b; `06_analysis/02_control/verif_matrix/` 아래 `d1_selection_rules.md`·`d1_selection_rules_rev1.md`, `u3_u6_rerun_rules.md`·`u3_u6_rerun_rules_rev1.md`·`u3_u6_rerun_rules_rev2.md`, `u9_targeted_rules_rev1.md`, `las_targeted_rules.md`·`las_targeted_rules_rev1.md`~`las_targeted_rules_rev5.md`.
  3. 명세 `00_docs/04_control/s6_control_spec.md`(읽기만).
  4. 원 데이터(읽기만): `06_analysis/03_hydraulic/coupled/v5/` 아래 R2 실행 기록 `resume_k1/`과 저장 기준선·키 원본·앵커 파일(뽑은 글머리 C-01·C-02·P2-11·P2-12가 가리키는 파일), `06_analysis/02_control/v5_rerun/las_k1/`, `<OUT>` = `C:\workspace\outrigger_control\07_results\S9\R4368X_b9f5707_20261115_013947\`의 `H-11\`·`H-12\`·`C-9\`·`C-10\`·`C-11\`, J_P 저장 배치 `07_results/S9/batch_V5-JP-VB_20261108_115631`·`07_results/S9/batch_V5-JP-V0_20261108_131212`와 그 행 폴더, 그림자 기록 `06_analysis/03_hydraulic/coupled/v5/las/shadow_jp_b0.jsonl`, 그리고 P2-17(R16-8 옵션 없음)이 가리키는 `06_analysis/02_control/verif_matrix/v5_resume_4368/run_b9f5707/run_harness.ps1`의 26~47행(그 줄만).
  5. 코드(읽기만): 자기 경로 2 폴더 `06_analysis/02_control/verif_matrix/v5_resume_4368/path2/`·`06_analysis/02_control/verif_matrix/v5_resume_4368/path2_v5c/`의 파일, `03_src/` 아래 파일(기록 키와 사건 이름의 뜻 확인용), 원 규칙이 값의 원본으로 지정한 원 판정기 `04_scripts/03_control/s8/r79_sensor_judge.py`(잡음 S-1~S-6·L1 관문, v5 기준 10절)와 `04_scripts/03_control/s8/r72_judge.py`(G6 판정 분기, C-09 R6-C3). 원 판정기를 열었으면 연 파일과 줄 범위를 판정서 읽은 것 목록에 적는다.
  6. 규칙 파일 원판~rev25: 봉인 sha 확인 때 바이트만 읽는다. 위 "받는 것" 3의 뽑은 글머리 밖의 절은 열지 않는다(기술적으로는 막지 않았고, 판정서 읽은 것 목록으로 확인한다).
  7. 자기 출력 폴더.
- **열지 않는 것**(원판 9.2; 사용자 결정 117의 3)
  1. 원판 9.1 경로 1 칸에 적힌 도구와 그것이 import하는 판: `las_judge`(H-7′ 모듈), `run_v5.py`(`d1` 판정 블록이 있는 파일 전체), `d1_select.py`, `u3_judge`(개정판을 포함해 이 이름으로 시작하는 모든 파일), H-5·H-6·H-8·H-9·H-10 경로 1 칸의 "각 판정 도구", 7.2 경로 1 칸의 "판정 도구", 7.3 경로 1 칸의 "python-expert 판독 도구".
  2. `06_analysis/02_control/verif_matrix/v5_resume_4368/` 아래 자기 폴더(`path2/`·`path2_v5c/`)와 자기 출력 폴더 밖의 모든 폴더(앞 판정 출력 포함). 예외는 "열어도 되는 것" 4의 `run_harness.ps1` 26~47행뿐이다.
  3. "열어도 되는 것" 5의 목록 밖 코드 파일.
  - "열어도 되는 것" 5에 파일 이름으로 적힌 원 판정기는 위 1의 지칭("각 판정 도구" 등)과 겹쳐도 열 수 있다. 이름으로 적은 허용이 지칭보다 앞선다.
  - 뽑은 글머리 C-02(rev1 RV1-5)가 인용하는 `run_v5.job_key` 대응은 지금 도구가 구현한 그대로 둔다. 이 대응을 고쳐야 하면 `run_v5.py`를 열지 말고 멈추고 묻는다.
  - 다른 경로의 코드나 출력을 본 사실이 있으면 그대로 적는다(원판 9.2: 그 묶음의 두 경로 판정은 `판정 불가`).
  - 자기 폴더 README와 코드 주석에는 앞 작성자가 "보지 않은 것"으로 적은 다른 경로의 파일 이름이 있다. 이름만 있고 내용은 없다. 그 파일은 열지 않는다.
- **고칠 수 있는 파일**(R4 허용 목록 (라)의 `path2/` 몫, rev16:325): `README.md`, `p2_4368.py`, `p2_u3.py`, `p2_v5j.py`, `test_p2_4368.py`, `test_p2_u3.py`, `test_p2_v5j.py`, 새 `p2_x16.py`·`test_p2_x16.py`. `p2_d1.py`·`p2_t3k.py`·`path2_chrono/`·`path2_v5c/`는 고치지 않는다(고치면 S-11). `00_docs/`와 판정서·감사 기록도 고치지 않는다(RD-1 7).
- **브랜치와 순서**: 브랜치 `z4373-p2harness`(R3f `8a0c843`에서 가름) 하나를 terramechanics-expert 작성자(`path2_v5c/` 담당)와 함께 쓴다. 이 작성자(2-dyn)가 먼저 `path2/` 변경을 모두 커밋하고, 마지막 커밋 해시를 메인 세션에 알린다. 그 뒤 `path2_v5c/` 작성자가 그 커밋 위에서 `p2v5c_common.py`의 `P2_CORE_SHA`·`P2_V5J_SHA`를 이 작성자의 최종 `p2_4368.py`·`p2_v5j.py` sha256으로 다시 고정한다. 그 뒤 이 작성자가 두 파일을 다시 고치면 메인 세션에 알린다(재고정을 다시 한다). master에는 커밋하지 않는다(RD-1 6).
- **할 일**
  - R16-10 2 (a)·(b)·(c)(U-3·U-6 판정), (d)(S-5 키 원본 대조 기록), (e)(J11, RD-10 포함. J11은 묶음 H-6·H-8·H-9·H-10에만 적용하고 H-1·H-3·H-4에는 판정하지 않는다. 이 작성자는 J 판정 함수에 구현하고, J11 목록은 `path2_v5c/` 작성자가 낸다), (f)(봉인 목록 → RD-2 26판), (g)(C-9~C-11 기록, 새 파일), (h)(H-11 G-3).
  - RD-11 J_P 판독(행 집합·사건 꼴·기본 이름·그림자 줄 수, 출력 항목 8, 사유 문구). 지금 도구에서 바꿀 것: 행 수 ≠ 12를 메모가 아니라 S-15 멈춤 표지로, 그림자 줄 수 ≠ 1을 조건 1 거짓이 아니라 그림자 판독 불가 멈춤 표지로, 사건 기록 판독 불가(`result.json`·`controller_events.json` 없음, 문자열 아닌 원소, 꼴 불일치)를 재사용 거짓이 아니라 사건 기록 판독 불가 멈춤 표지로 낸다. 멈춤 표지가 있으면 재사용 참거짓을 내지 않는다.
  - RD-8 `breach_reads` 길이 4(J-P3 판정 함수에서). `path2_v5c/`가 이 함수를 불러 쓰므로 그 폴더 판정에도 들어간다. 묶음 H-1·H-3·H-4는 기록 상태로 J-P3를 판정한다(H-1 판정 도구 `p2_d1.py`는 허용 목록 밖). 그래서 하네스 줄을 읽는 하위 명령이 이 세 묶음 실행 기록의 `breach_reads`를 읽어 길이가 틀린 줄 수를 묶음마다 낸다. 0이면 기록 상태 판정을 그대로 두고, 1 이상이면 그 줄의 J-P3는 판정 불가다. 이 수가 1 이상이면 묶음 관문 표지 `J-P3 입력 형식(RD-8)`(이름 그대로)을 낸다. 같은 도구가 이 세 묶음 VB 줄 가운데 기록된 J-P3 상태(`h1_d1.jsonl` 줄의 `d1.j_p3`, u3·u6 항목의 `v5.j_p3`)가 `pass`인데 `breach_reads`가 없는 줄 수도 내고, 0이 아니면 같은 표지를 낸다.
  - RD-9 ③ 켬 줄 수: 묶음 H-1·H-3·H-4(H-1은 판정 도구가 허용 목록 밖이므로 줄 태그를 읽는 하네스 하위 명령에서 센다).
  - RD-7 멈춤 표지와 목록(열과 표기는 RD-7 3): G-5 목록, G-6 목록, G-3 거짓 짝 목록, 멈춤 S-6 목록. 경로 2의 멈춤 S-6 목록은 이 작성자가 묶음 H-1·H-3~H-10(H-5 포함; H-6·H-8·H-9·H-10 포함)의 R2 결과 줄·run 전부에 대해 하나로 낸다. family run, H-11·H-12 출력, C-9~C-11 기록은 넣지 않는다. J-P3 위반 목록과 J11 목록은 이 작성자가 내지 않는다(`path2_v5c/` 작성자가 묶음 H-6·H-8·H-9·H-10에 대해 낸다). 묶음 H-1·H-3·H-4의 J-P3는 J-P3 위반 목록에 넣지 않고 기록 상태 판정과 RD-8 표지(H-3·H-4는 G-4도)로만 다룬다.
  - RD-5 키 대응표 초안, RD-13 묶음별 항목 목록(자기 도구가 내는 묶음; 넘겨받지 않은 앞 판 정의의 근거 조항은 도구 주석·README 인용에서 옮긴다), RD-1 5 HEAD 확인.
  - Chrono 하위 명령은 돌리지 않는다(RD-3 2).
- **출력**: `06_analysis/02_control/verif_matrix/v5_resume_4368/judge_<M4 짧은 해시>/harness_path2/`.
- **앞 판이 더 필요할 때**: 이 파일에 없는 앞 판 절이 필요하면 멈추고 묻는다. 메인 세션이 이름을 지운 사본으로 넘긴다.


## 뽑은 규칙 글머리 (원문, 이름 지운 곳은 표시)
<!-- C-00 v5_resume_4368_rules.md:1 -->
# v5 재개 검증 436.8 판정 규칙 (제어기 `final_C4G2_LAS_K1`, 봉인)

- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_seal_candidate_draft.md`와 1·3·5행만 다르다.
- 작성: control-expert, 2026-11-13. 기준 master `3d41083`(작성 시점 HEAD). 입력 초안 `v5_resume_4368_plan_draft.md`(sha256 `141e4958f39b7c74…`, 이 폴더).
- **시점: 436.8의 어떤 실행 결과도 없을 때(봉인 2026-11-13 00:46:07 +09:00, 봉인 커밋 3d41083).** 436.8 묶음(0단계 T-3K 포함)은 한 줄도 돌지 않았다. 이 규칙을 쓰려고 읽은 것은 1절에 모두 적었다.
- 이 문서 하나가 다음 셋을 겸한다(판이 따로 없다): (가) v5 기준 개정 13(`v5_criteria.md` 계열, 2절 이하 "개정 13 몫"), (나) `u3_u6_rerun_rules` rev3(4.2절·7.1절 H-3·H-4 행, "rev3 몫"), (다) O-C5 기록 행 규칙(5.4절·7.4절). 앞 판들은 고치지 않는다. 이 문서와 앞 판이 다르면 이 문서가 맞고, 이 문서가 말하지 않는 것은 앞 판 그대로다.

## 0. 목적과 판의 성격

1. v5 확정 제어기 `final_C4G2_LAS_K1`(VB `final_C4G2_P3_LAS_K1`, ABL `ABL_LAS_K1`)로 v5 검증 묶음 전체를 **한 커밋에서 한 번만** 다시 돌려 v5 판정을 낸다(사용자 결정 2026-11-10 "436.8은 확정 제어기로 한 번만").
2. LAS-b 전환(명세 436)과 K1 전환(명세 437) 뒤 그림자·재사용으로 덮지 못한 묶음을 모두 채운다.
3. 논문 2.8용 G1 열린 루프 새 행 3개(VB 비례 1, 속도 낮춤 VB·V0 2), 운용 시작 조건 안 확인 기록 행 O-C5 **2개**(A3 조건 VB + V0 짝, 사용자 결정 2026-11-12 R-3)를 더한다.
4. **숫자 문턱을 새로 만들지 않는다.** 새로 넣는 것은 규칙 문장(태그·옵션·K1 분류·재사용·시작 조건 밖 처리·O-C5 멈춤·두 경로)뿐이다. 7.6절에 이 문서가 쓰는 숫자 전부를 적었다.
5. LAS-c 재설계(`06_analysis/02_control/las_redesign/las_redesign_v1_draft.md`)는 v5 뒤 과제이고 436.8 범위 밖이다. 436.8에는 LAS-c 후보·진단 probe·표본 밖 판정 행(O-H*, O-C1~O-C4)을 넣지 않는다(사용자 결정 2026-11-12 E-4).

## 1. 봉인 전에 본 것 (공개)

### 1.1 이미 알려진 결과 (과적합 공개)

| 원본 | 알려진 값 | 이 규칙에서 쓴 곳 |
|---|---|---|
| `las_p5r4_k1_judgement.md`(sha256 `5e9fb33b7419d624…`) 5.1·8.2·9·10절 | P0+K1 Chrono A1/A3/A5(혼합 지형 강체 + J1@FR, 바닥 (2.3351°, 1.5017°), `record_only`): RL 이탈 뒤 최소 10.814 / **8.637** / **8.509** kN, $F<F_{min}$ 시간 A3 195 ms, A5 67 ms. 실행 SL-2 $R_c$ A1·A5 1.076, A3 1.035(`operating_rule_rejects` 참). A행 wall_s 3,885~4,413 s(P 4병렬) | 5.4절 O-C5 정의·첫 축척, 7.4절, 10절 P-9·P-13, 12절 비용 |
| `06_analysis/02_control/b1/prelaunch/batch.json`(B1 본 배치, 커밋 `bd64cc4`) | SCM 6행 wall_s 6,649~8,898 s(P 4병렬, `--threads 4`, 훅 fast) | 12절 단가만(힘·행정 값은 읽지 않음) |
| `07_results/S9/batch_V5-STAGE3_20261107_184341/batch.json` | L2b 23행 wall_s 862~1,869 s, 합 28,412.8 s(P) | 12절 단가만 |
| `07_results/S9/batch_V5-STAGE3_20261107_184239/batch.json` | SCM 11행 wall_s 10,900~19,178 s(P/E 혼합, 볼록 껍질 훅 채택 전), 합 168,603 s | 12절 민감도 상한만 |
| 초안 `v5_resume_4368_plan_draft.md` 0절 머리 표 | 저장 기준선(LAS-b 전환 전·K1 관문 꺼짐)의 줄 수·`soil_mode_started`·`INFO_LOC_FLAT_SOIL_MARGIN` 개수·wall_s(판정 값은 아님) | 5.1·5.5절, 10절 P-1~P-8 |

- 436.8 행과 같은 정의의 결과로 이미 있는 것은 P5r4 A1·A3(C-4 켬 팔과 같을 수 있음, 5.2절)뿐이다. 그 값은 10절 P-9에 예측으로 적고, 판정은 436.8 커밋에서 다시 돈 결과로만 한다(사용자 결정 R-2).

### 1.2 이 규칙을 쓰려고 읽은 것

- 규칙·판정서: 부록 A의 봉인 문서 전부(sha256을 `.sha256` 기록과 대조, 모두 일치), `las_p5r4_k1_judgement.md`, `las_k1_rem_judgement.md`, 명세 `00_docs/04_control/s6_control_spec.md` 436·437절, CLAUDE.md 기준값 표.
- 코드(정의 확인만, 실행 안 함): `03_src/outrigger_sim/hydraulics/v5_options.py`(`is_extend_start_tag`, `switch_base_tag`, `EXTEND_START_TAGS`), `04_scripts/02_chrono/s9_batch.py`(`V5_LAS_K1_CONTROLLER` = `final_C4G2_LAS_K1`, `V5_P3_LAS_K1_CONTROLLER` = `final_C4G2_P3_LAS_K1`), `run_S9.py`(`--las-off`·`--k1-order-gate {preset,off,on}`·`--start-limit`·`--floor-roll`·`--floor-pitch`·`--crawler-kn-scale {1,3}`, `SCM_THREADS_FIXED` = 4, `start_condition_record`의 $R_c$ 식), `las_chrono_rows.py`(`V5-LAS-CHRONO` 4행 정의), `las_p5r4_k1_chrono_rows.py`(A1~A6 정의).
- 해시 앵커 커밋 `c6bb55b` 이후 `03_src`·`02_params` 변경: `03_src/outrigger_sim/chrono/b1_grid_record.py` 추가 1건(Chrono 전용, `--b1-grid-record`를 줄 때만 동작). 하네스 경로 변경 없음(`git diff --stat c6bb55b..3d41083`). 실행 커밋에서 다시 확인한다(3절 A-5).

## 2. 규약과 기호

- 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1, C2 음되먹임($u$ = 다리 행정 속도 명령 [m/s], + = 신장). 정수 주기 $n = \mathrm{round}(t/T_s)$로 시각을 비교한다.
- 다리 순서 FL, FR, RL, RR(0~3). 힘은 실린더 순 힘 [N](표는 kN). 압력은 bar 게이지. 행정은 모터 행정 [m](표는 mm).
- "Kc1"·"Kc3"은 크롤러 접촉 강성 ×1·×3이다. K1 R4c30 순서 관문(이하 "K1 관문")과 하네스 키 토큰 `K1`(크롤러 ×1)과 다르다.

| 기호 | 정의 | 단위 |
|---|---|---|
| $F_{min}$ | YAML `control.F_min_cylinder_N` = 9,414.589 | N |
| $F^{\mathrm{a}}_{min}$ | Chrono `p3b.P3-3_leg_force.F_min_after_N`(이탈 뒤 1 ms 참 $F_{cyl}$ 다리별 최소) | N |
| $F^{\mathrm{t}}_{min}$ | Chrono `p3b.P3-3_leg_force.F_min_transient_N` | N |
| $R_c$ | SL-2 운용 사용률 $\lvert\phi_c\rvert/4.4° + \lvert\theta_c\rvert/3.2°$, $(\phi_c, \theta_c)$ = CHECK 끝 크롤러 IMU 자세(result.json `p3b_ext.start_condition.R_c_operating`) | – |
| $k$ | O-C5 바닥 축척. 바닥 $(\phi_g, \theta_g) = k\cdot(2.3351°, 1.5017°)$ | – |
| `git_at_start` | 묶음 실행을 시작한 커밋 | – |

## 3. 전제·실행 전 조건 (하나라도 거짓이면 그 묶음을 시작하지 않는다)

| # | 조건 | 확인 방법 |
|---|---|---|
| A-1 | v5 제어기 = `final_C4G2_LAS_K1`. P5r4(`미달`, P0 유지)·K-2·K-2b·B1 결과는 제어기를 바꾸지 않았다 | `k2/judgement/k2_judgement.md`, `las_p5r4_k1_judgement.md` 10절 |
| A-2 | 이 문서가 봉인됐다(`.sha256`과 파일 sha256 같음, LF·BOM 없음, `.gitattributes -text`) | `tools/verif/seal_check.py` 종료 0 |
| A-3 | 0단계 T-3K(`las_targeted_rules_rev5.md`, 360건)가 판정까지 끝났다. T-3K가 `통과`가 아니면 본 묶음을 시작하지 않고 묻는다 | T-3K 판정서 |
| A-4 | 행 생성기·판정 도구가 `_LAS_K1` 태그를 기대한다(감사 W-3 해소): `d1_chrono_rows.py`, `v5_stage3_las_rows.py`, `las_chrono_rows.py`, `las_k1_chrono_rows.py`, `las_k1_rem_chrono_rows.py`, 개정판 `u3_judge`. 봉인 도구 `u3_judge`의 상수는 고치지 않는다 | 16절 위임 결과 + G-S(11.2) |
| A-5 | 모든 묶음이 같은 `git_at_start`. 실행 중 master 커밋·병합 금지(전용 worktree 예외, 그때도 `git_at_start`는 하나). `git_at_start`에서 `03_src`·`02_params`·하네스 경로가 `c6bb55b`와 다르면(1.2의 Chrono 전용 1건 제외) 10절 P-1·P-2 비트 예측의 앵커를 실행 전에 다시 정하는 개정을 봉인한다 | `git diff --stat c6bb55b..GIT_AT_START -- 03_src 02_params` |
| A-6 | 볼록 껍질 훅 DLL SHA-256이 검증 빌드 `cec997d7…`. 새 worktree에는 DLL을 복사했다 | `hull_hook` 기록 |
| A-7 | fdown3.5 L1R 스냅숏 재생성(cad-expert, RMS < 0.01 °/s)이 끝났고, 그 스냅숏을 시작 상태로 쓰는 436.8 행 목록을 cad-expert가 냈다. 그 행은 저장 행과 "조건 다름, 해시 비교 없음"으로 적는다 | cad-expert 보고 |
| A-8 | 재발 방지 4항: 옵션 × 단계 겹침 표(11.1), G-S 건조 실행(11.2), 러너 로그 `errors 0`(11.3), 자리표시 점검(11.4) | 11절 |
| A-9 | 출력은 4.3절의 새 이름으로만 쓴다. 저장 기준선과 `_LAS` 전용으로 예정됐던 이름(`v5/d1_las.jsonl`, `v5_rerun/las/`)은 쓰지 않는다 | 실행 전 감사 |
| A-10 | 묶음마다 verif-protocol-auditor `[시점] 실행 전` 감사 차단 0 | 감사 리포트 |

## 4. 제어기 태그와 옵션 (래퍼·프리셋 이중 적용 금지)

### 4.1 기대 태그와 ③ 판별

| 행 종류 | 기대 태그(`controller_tag`, Chrono `--expect-controller` 같은 값) |
|---|---|
| V0·V0v·S6SEED·V3·그 밖 ③ 없는 설정 | `final_C4G2_LAS_K1` |
| VB·LS1~LS4(③ 켬) | `final_C4G2_P3_LAS_K1` |
| ABL | `ABL_LAS_K1`(명령은 `ABL_LAS`와 같음, 437.3) |
| IND / IND_LAS(기록 열) | `IND` / `IND_LAS`(`_K1` 없음, 437.3) |
| C-4 끔 팔 2행만 | V0 `final_C4G2_K1` / VB `final_C4G2_P3_K1`(`--las-off --k1-order-gate on`) |
| 열린 루프 C-6·C-7 | 제어기 없음(`controller_options.applied` = false). 태그 검사 대상 아님 |

- **③ 켬 판별**은 `v5_options.is_extend_start_tag(tag)`(기준 태그 `switch_base_tag(tag)` = `final_C4G2_P3`)로만 한다. 집합 `EXTEND_START_TAGS`, 태그 문자열 접미사 비교, 정규식은 판정·선택에 쓰지 않는다. 접미사 조합(`_LAS`, `_K1`, `_LAS_K1`, `_TCL`)이 무엇이든 기준 태그가 같으면 같은 ③ 판별이다.
- 한 판정 묶음 안의 실행은 모두 위 표의 같은 판이다(개정 11 #6). 섞이면 멈춘다(8.2 S-2).
- 개정 11 #5의 감시기 설정 재구성에 "태그에 `_K1` 접미사(`v5_options`의 순서 관문 접미사 분해 함수가 참)면 관문 켬"을 더한다.

### 4.2 금지 옵션·env (한 번이라도 있으면 그 행은 무효, 8.2 S-3)

| 대상 | 금지 |
|---|---|
| 모든 하네스 줄 | 후보 토큰·래퍼(`K1on`, `LASoff`, `TCL`, `P5r4` 등 `C2Config.with_10hz_d1()` 기본값을 다시 적용하거나 바꾸는 키 토큰), `OUTRIGGER_LOC_SHADOW` env(사용자 결정 Q5 (a)) |
| 모든 Chrono 행(C-4 끔 팔 제외) | `--k1-order-gate`(값 무관), `--las-off`, `--las-candidate`, `--k1-forced-block`, `--k2`, `--no-controller-check`, `pre_*_preset_runner.py` 경유, `OUTRIGGER_LOC_SHADOW` |
| C-4 끔 팔 2행 | 위에서 `--las-off`와 `--k1-order-gate on` 두 개만 허용(437.4의 LAS-b 단일 변수 짝). 그 밖은 같음 |
| 모든 SCM 행 | `OUTRIGGER_HULL_HOOK` 설정(미설정 = fast가 기본), `OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED`, `--allow-mixed-hull` |

- 기록 확인(전 행, 실행 직후·판정 전): `c2_setup.k1_order_gate` = `preset`(C-4 끔 팔은 `on`), `c2_setup.k1_order_gate_effective` = true, `controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate` = true, `liftoff_approach_slow.settings` 9값이 프리셋 값(C-4 끔 팔은 꺼짐, `c2_setup.las_off` = true). 하네스 줄은 같은 의미의 줄 필드. 하나라도 다르면 8.2 S-3.

### 4.3 출력 이름 (고정)

| 묶음 | 출력 |
|---|---|
| 하네스 H-1·H-5·H-6·H-7·H-8·H-9·H-10 | `06_analysis/03_hydraulic/coupled/v5/resume_k1/` 아래 `h1_d1.jsonl`, `h5_u9_v0.jsonl`, `h6_dg3_v4on.jsonl`, `h7_dg3_off.jsonl`, `h8_noise.jsonl`, `h9_stage1.jsonl`, `h10_reuse_rerun.jsonl`(각 `.identity.json` 동반) |
| H-2 | `resume_k1/h2_d1_select.json` |
| H-3·H-4 | `06_analysis/02_control/v5_rerun/las_k1/` 아래 `u3_*.json`, `u6_*.json`(파일 구성은 `u3_u6_rerun_rules` 원판~rev2의 꼴, 폴더만 바꿈) |
| H-0 T-3K | `las_targeted_rules_rev5.md` 2.6절 그대로 |
| Chrono | `07_results/S9/batch_V5-RESUME-K1-<묶음 ID>_<stamp>`(묶음 ID: `C1`, `C2`, `C3`, `C4`, `C5`, `C6C7`, `OC5PROBE`, `OC5`, J_P 재실행이 생기면 `JP`) |

- python-expert가 다른 이름이 필요하면 봉인 전에 이 표를 고친다. 봉인 뒤에는 바꾸지 않는다.

## 5. 묶음과 행

### 5.1 하네스 묶음 (dynamics-dev, 하네스 축소 모델)

| # | 묶음 | 행 수 | 정의 | 판정 규칙 |
|---|---|---|---|---|
| H-0 | T-3K(0단계, 봉인 rev5) | 360(R-0 7 + R-0K 45 + T-3K 308) | rev5 그대로. 다른 묶음보다 먼저, 판정 뒤 본 묶음 시작(Q3 (a)) | `las_targeted_rules` 원판~rev5 |
| H-1 (J-1) | D-1 하네스 전부 | 868(V0 434 + VB 434) | 키·플랜트·시드는 저장 `v5/d1.jsonl`과 같다. 태그만 다르다 | `d1_selection_rules{,_rev1}` 판정 항목 + v5 기준 + H-7′ |
| H-2 (J-2) | D-1 선별 | 1(계산) | H-1 출력이 입력(G-1~G-5 그대로) | `d1_selection_rules{,_rev1}` |
| H-3 (J-7) | U-3 V0·VB | 2,228(slope V0 110 포함, D-1 재사용 12는 H-1 출력에서 Q-1~Q-5로) | 옛 태그 `u3_slope_V0.json`은 판정하지 않는다(해시 기록만) | `u3_u6_rerun_rules` 원판~rev2 + 이 문서 rev3 몫 |
| H-4 (J-8) | U-6 VB(C2·ABL·IND) + 기록 열 IND_LAS | 726 + 242(기록) | ABL은 `ABL_LAS_K1` | 같음 |
| H-5 (J-9) | U-9 V0 | 14 | 같음 | `u9_targeted_rules_rev1` + 7.1 태그 읽기 |
| H-6 (J-10) | dg3 v4_on(2단계 잡음 L3 VB 대체) | 135 전부(Q1 (a)) | 그림자 작동 38키·미작동 97키 모두 재실행 | v5 개정 8 2절 #6 |
| H-7 (J-11) | dg3 off(③ 끔 비교) | 135 전부(Q4 (a)) | 기록 행 | 기록 |
| H-8 (J-12) | 2단계 잡음 VB·V0, seedext | 3,106(VB 1,503·V0 1,503·seedext 100) | 원 명령, 새 이름. dg3가 대체한 L3 134·L2 1의 처리는 원 규칙 그대로 | r79·v5 기준 |
| H-9 (J-13) | 1단계 main V0~V8·L1·L2, pressure_only V0·V4·V5, 격자 VB | 812 + 96 + 768 | 원 명령, 새 이름 | v5 기준 |
| H-10 | 재사용 예정이던 하네스: main VB·LS1~LS4, U-9 VB, p3_hash VB, item8(VB 6 + V0 6), overlap(VB 4 + V0 4 + V3 4) | 388 + 28 + 22 + 12 + 12 = 462 | 재사용하지 않고 재실행(Q1 (a)) | v5 기준(재사용 표시 없이 새 결과로 판정) |

- 본 묶음 합계 9,800행(H-1 868 + H-3 2,228 + H-4 968 + H-5 14 + H-6·H-7 270 + H-8 3,106 + H-9 1,676 + H-10 462) + 0단계 360. 묶음별 실제 줄 수는 python-expert가 `steps_h2.json`에서 세고, 이 표와 다르면 실행하지 않고 멈춘다(8.2 S-15). 차이의 원인이 원 규칙의 줄 정의(예: dg3 대체분)이면 봉인 전에 이 표를 고친다.

### 5.2 Chrono 묶음 (Chrono-dev)

| # | 묶음 | 행 | 엔진 | 정의 | 판정 규칙 |
|---|---|---|---|---|---|
| C-1 (J-3) | D-1 고정 강체 | 10(L2b VB 6: C2-01·02·04·05·06·08, L1-R V0 Kc×3 4: C1-09~12) | L2b NSC / L1-R | 미실행 행. 태그만 `_LAS_K1` | D-1 선별 규칙 11절 |
| C-2 (J-4) | D-1 선별 행 + PS-c | 4(L2b C2-03·07, SCM S-01·02) + 기준선 실패 시 칸당 +1(최대 8) + PS-c 0~2(SCM) = 4~10 | L2b / SCM | H-2 출력으로 정한다 | 같음 |
| C-3 (J-5) | D-1 고정 토양 S-03·S-04(`D1S_G1_B_{middle,bottom}_Fs4_spJ1FL` 두 행) | 2 | SCM | 재실행이 판정, 저장(옛 VB 태그) 결과는 기준선 기록(명세 436.9.7) | 같음 |
| C-4 (J-14) | LAS Chrono 확인 `V5-LAS-CHRONO`(혼합 지형 강체 + J1@FR, 바닥 (2.3351°, 1.5017°), `record_only`, 160 s, VB) | 4 = Kc1·Kc3 × LAS 켬·끔 | SCM 혼합 | 켬 팔 = 현행 프리셋(P0+K1), 태그 `final_C4G2_P3_LAS_K1`. 끔 팔 = `--las-off --k1-order-gate on`, 태그 `final_C4G2_P3_K1`. 켬 팔이 P5r4 A1(Kc1)·A3(Kc3)와 같은 정의이면(cad-expert가 `option_diff`로 확인, 차이 허용은 `--las-candidate P0` 한 개) 436.8 커밋에서 다시 돌리고 A1·A3과의 명령 비트 비교는 기록만 한다(R-2 (a)) | 기록(하네스 T-1 짝과 나란히), D8·G6. 7.4 시작 조건 밖 처리 |
| C-5 (J-15) | 3단계 Chrono(`V5-STAGE3-LAS` 정의를 `_LAS_K1`로) | 논리 37, **실행 35** = L2b 24(강체 23 + 짝 P-1) + SCM 11. 짝 P-2·P-3은 S6SEED `…_seed20261026`·`…_seed20261026_flow`와 정체성 5항목이 같아 빼고, 판정에서는 그 두 행을 P-2·P-3으로도 읽는다(12c 대기분을 이 문서가 확정) | L2b / SCM | 개정 12 2.1 행 그대로, 태그만 4.1 | 개정 12·12a·12b + 이 문서 |
| C-6 | G1 열린 루프 VB 비례 `P3a_G1_B_VB_prop` | 1 | SCM(L2b 다리, 제어기 없음) | 5.3절 | 기록(7.5) |
| C-7 | G1 열린 루프 속도 낮춤 VB `P3a_G1_B_VB_FB` + V0 `P3a_G1_B_V0_FB` | 2 | 같음 | 5.3절 | 기록(7.5) |
| C-8a | **O-C5 VB**: A3 조건(Kc3, VB)을 운용 시작 조건 안으로 | 1 + $R_c$ probe 1~3 | SCM 혼합 | 5.4절 | 기록 행 + 멈춤(7.4) |
| C-8b | **O-C5 V0 짝**: A5 조건(Kc1, V0)을 운용 시작 조건 안으로(사용자 결정 R-3, 확인 필요 질문 Q-A) | 1 + $R_c$ probe 1~3 | SCM 혼합 | 5.4절 | 기록 행 + 멈춤(7.4) |
| 재사용 | J_P Chrono 12(`V5-JP-{VB,V0}`) | 0(조건 실패 시 12) | L2b | 7.3 조건이 참이면 저장 판정 그대로(재사용 표시). 거짓이면 저장 argv 그대로·태그만 4.1로 묶음 `JP`에서 재실행해 판정한다(멈추지 않음) | 저장 판정 / 재실행 판정 |
| 재사용 | 열린 루프 `V5-OPENLOOP-{VB,V0,VB-PROP,FB}`, `V5-OPENLOOP-R`·`RFU` | 0 | – | 제어기 없음 | 그대로 |

- Chrono 합계: **60~66행**(C-1 10 + C-2 4~10 + C-3 2 + C-4 4 + C-5 35 + C-6·C-7 3 + C-8 2) + $R_c$ probe 2~6건(행마다 최대 3, CHECK까지) + J_P 조건 실패 시 12.
- 엔진별: L2b·L1-R 36~38행(C-1 10, C-2 2~4, C-5 24), SCM 24~28행(C-2 2~6, C-3 2, C-4 4, C-5 11, C-6·C-7 3, C-8 2).
- 행 이름의 최종 문자열(`case`)은 cad-expert가 정하고 `batch.json`에 `criteria_id`로 이 표의 # 값을 남긴다.

### 5.3 G1 열린 루프 새 행 (C-6·C-7)

| 항목 | C-6 VB 비례 | C-7a 속도 낮춤 VB | C-7b 속도 낮춤 V0 |
|---|---|---|---|
| 바탕 행 | `batch_V5-OPENLOOP-VB_20261108_112044\P3a_G1_B_VB`(VB: η_v 0.85, 51.17 L/min, 우선 분배, τ_v 0.1 s, M2 `flow_limited_r5`) | 같음 | `batch_V5-OPENLOOP-V0_20261108_123517\P3a_G1_B_V0` |
| 바꾸는 인자 | `--flow-law proportional`만 | `--lift-s 31.93 --lift-speed-fraction 0.87684`만 | 같은 두 인자만 |
| `check-sources` | `ok_expected_diff`, 차이 = VB 인자 + `flow_law` | 차이 = VB 인자 + 두 인자 | 차이 = 두 인자 |
| 짝(기록) | 저장 G1 v4·V0·VB(우선) | 저장 G1 v4·V0·VB, C-6, C-7b | C-7a |
| 값 계산 | `paper_runs/scripts/openloop_compare.py`의 `analyse` 정의(속도비 창 8.5 s < t ≤ 실행 끝) | 같음 + 유량 제한 0행 확인 | 같음(V0라 유량 항목 해당 없음, 속도비는 10~20 s $\dot s_{motor}$) |

### 5.4 O-C5 기록 행 (C-8a·C-8b)과 바닥 각 결정 절차

| 항목 | C-8a(VB) | C-8b(V0 짝) |
|---|---|---|
| 행 이름 | `OC5_mixed_rigid_J1FR_Kc3_VB_top` | `OC5_mixed_rigid_J1FR_Kc1_V0_top` |
| 바탕 | P5r4 A3 행 정의(`las_p5r4_k1_chrono_rows` → `las_chrono_rows.level_argv`: 강체 + J1@FR `--rigid-base FR --soil J1 --grid 0.01`, `--crawler-kn-scale 3`, VB `s9_batch.v5_vb_argv()`, 패드 B, 오거 상단, $F_s$ 4 kN, 압력 normal·IMU ideal·시드 20261026, 160 s) | P5r4 A5 행 정의(같은 지형, Kc1 = 크롤러 인자 없음, V0 = v5 인자 없음) |
| 제어기 | 현행 프리셋, 태그 `final_C4G2_P3_LAS_K1` | 현행 프리셋, 태그 `final_C4G2_LAS_K1` |
| 바탕과 다른 인자 | `--floor-roll`·`--floor-pitch`(바닥 축척 $k$)와 `--las-candidate P0` 없음, 이 둘뿐 | 같음 |
| 시작 제한 | `--start-limit record_only`(A행과 같음). $R_c$는 판정 대상 여부를 정하는 값으로만 쓴다 | 같음 |
| 첫 축척 | $k_1 = 0.95 / 1.035 = 0.9179$ | $k_1 = 0.95 / 1.076 = 0.8829$ |
| 비교 짝(기록) | P5r4 A3(같은 Kc·플랜트, 바닥만 다름) | P5r4 A5(같은 Kc·플랜트, 바닥만 다름) |
| C-8a↔C-8b | 크롤러 강성과 플랜트 두 변수가 다르다. 둘의 차는 단일 변수 효과로 읽지 않는다(기록만) | |

**바닥 각 결정 절차(행마다 따로, 본 행 결과 전)**

1. **probe 정의**: 본 행 argv에서 `--duration`만 `PROBE_DURATION`으로 바꾼 실행이다. `PROBE_DURATION` = 같은 바탕 행(A3 또는 A5)의 저장 `phases`에서 CHECK 끝 시각(폐루프 시작 기준) + 2 s를 올림한 정수 초. cad-expert가 시각만 읽어 정하고 `batch.json` 행 `note`에 적는다. 같은 커밋·스레드·풀·훅·start env.
2. probe에서 읽는 것은 `p3b_ext.start_condition`의 `crawler_attitude_deg`·`R_c_operating`, 바닥 인자, `phases`뿐이다. probe 판독 도구는 이것만 출력한다. 힘·행정·판정 블록은 읽지 않고, 판정서에도 쓰지 않는다.
3. probe 결과에 `R_c_operating`이 없으면(CHECK가 끝나지 않음) `PROBE_DURATION`을 두 배로 한 번 다시 돈다. 이 재실행은 probe 개수에 세지 않는다. 그래도 없으면 그 행의 절차를 멈추고 묻는다.
4. $|R_c(k_1) - 0.95| \le 0.02$이면 $k = k_1$.
5. 아니면 $k_2 = k_1 \cdot 0.95 / R_c(k_1)$로 둘째 probe. $|R_c(k_2) - 0.95| \le 0.02$이면 $k = k_2$.
6. 아니면 할선 $k_3 = k_1 + (0.95 - R_c(k_1))(k_2 - k_1)/(R_c(k_2) - R_c(k_1))$로 셋째 probe. $|R_c(k_3) - 0.95| \le 0.02$이면 $k = k_3$.
7. 멈춤: 셋째 probe 뒤에도 허용 밖, $R_c(k_2) = R_c(k_1)$(할선 정의 불가), 계산한 $k \notin (0, 1]$ 중 하나면 그 행의 본 실행을 하지 않고 멈춘 뒤 묻는다(다른 묶음은 계속). **probe는 행마다 최대 3건**이다.
8. 바닥 인자 값: $\phi_g = \mathrm{round}(k \cdot 2.3351, 4)$°, $\theta_g = \mathrm{round}(k \cdot 1.5017, 4)$°. $k$는 소수 넷째 자리로 적는다. 실제 argv 문자열이 원본이다.
9. 본 행은 정한 $k$로 처음부터 끝까지 돈다. 본 행의 실행 $R_c$를 다시 기록하고 정한 probe의 $R_c$와 비교한다(같은 argv 앞부분이므로 같다고 예측, 10절 P-14). 다르면 기록하고 python-expert에 원인 확인을 넘긴다(멈추지 않음).
   - 본 행 $R_c \le 1$: O-C5로 읽는다(7.4).
   - 본 행 $R_c > 1$: O-C5로 읽지 않는다. 대체 행을 넣지 않고, 기록하고 묻는다.
10. probe와 본 행의 $k$, 바닥 각, $R_c$, probe 개수는 모두 판정서에 적는다. 목표 0.95, 허용 0.02, 최대 3건은 **절차 값(가정)**이고 판정 문턱이 아니다(사용자 결정 R-1).

### 5.5 재사용

- 재사용은 **J_P Chrono 12**와 **제어기 없는 열린 루프**뿐이다(Q1 (a)). 하네스는 재사용하지 않는다. 재실행 결과와 저장 해시가 같으면 "미작동 확인"으로 적는다(개정 11 2절 문구).

## 6. 실행 정체성 기록 (줄·행마다, 판정 전 확인)

| 항목 | 하네스 | Chrono SCM(`run_S9.py level`, 열린 루프·probe 포함) | Chrono L2b(`run_S8C.py`) / L1-R |
|---|---|---|---|
| 프리셋 | `C2Config.with_10hz_d1()` 기본값(LAS-b 켬, K1 관문 켬, ③는 VB·LS만). 4.2 금지 토큰 없음 | 같음, `--k1-order-gate` 없음(= `preset`) | 같음 |
| 태그 | 4.1 표. `controller_tag` 필드 | `--expect-controller` = 4.1 값, `expect_controller.ok` 참 | 같음 |
| 커밋 | 줄마다 `git_at_start`(+ dirty 여부). 묶음 안에서 하나 | `batch.json` `git_at_start`, result.json 커밋 | 같음 |
| 스레드 | 작업자마다 `MKL_NUM_THREADS`·`OMP_NUM_THREADS`·`OPENBLAS_NUM_THREADS`·`NUMBA_NUM_THREADS` = 1, `MKL_THREADING_LAYER` = TBB, spawn. 기록만(결과가 스레드와 무관) | `--threads 4`, result.json `num_threads_chrono` = 4. 다르면 8.2 S-4 | 저장 argv와 같은 값 |
| start env | – | 행 키 `start_env`에 `OMP_WAIT_POLICY=PASSIVE`, result.json에 같은 값 기록. 없거나 다르면 8.2 S-4 | – |
| 풀 | 기록(P·E 혼합 가능) | `pool` = `planned_pool` = `pcore`, result.json `placement`(affinity 마스크·논리 CPU 목록), `power_throttling_off_ok` 참, 실행 중 affinity 변경 기록. E로 돈 행은 저장 행과 해시 비교를 하지 않고 "조건 다름"으로 적는다(개정 12 2.2). `pool` ≠ `planned_pool`이면 기록하고 그 행의 해시 비교만 뺀다 | `pcore` |
| 볼록 껍질 훅 | – | `hull_hook_requested`·`hull_hook_effective` 전 행 fast, `fallback_reason` 없음, batch `MIXED_HULL_MODE` 없음. 하나라도 어긋나면 8.2 S-4 | – |
| 센서 | 각 묶음 원 정의(압력 normal 등급, IMU 원 정의, 시드 원 값) | 같음 | 같음 |
| 예약 | 30분 넘는 묶음은 `reserve.py add`(러너면 `--reserve-owner`) | 같음 | 같음 |
| 시작 제한 | – | C-4·C-8·probe `--start-limit record_only` | – |

## 7. 판정 기준

### 7.1 원본 기준 (바꾸지 않는다)

| 묶음 | 기준 원본(봉인, 부록 A) | 이 문서가 더하는 것 |
|---|---|---|
| 전부 | `v5_criteria.md` + 개정 1~12b | 태그를 4.1로(개정 11 #1·#2·#5, 개정 12 #2). 개정 11 #4 "③ 켬 실행 전부, 대상 0이면 판정하지 않고 멈춘다"의 ③ 켬은 4.1 판별. #6 "한 판정 묶음은 같은 제어기 판". #7 `INFO_LIFTOFF_SLOW*`는 기록 항목 |
| H-1·H-2·C-1·C-2 | `d1_selection_rules.md` + rev1 | 입력 이름만 4.3(`h1_d1.jsonl`). rev1에 태그 문자열이 없으므로 규칙 문장은 그대로 |
| H-3·H-4 (rev3 몫) | `u3_u6_rerun_rules.md` + rev1 + rev2 | G-2 태그: V0 `final_C4G2_LAS_K1`, VB C2 `final_C4G2_P3_LAS_K1`, ABL `ABL_LAS_K1`, IND `IND`, IND_LAS `IND_LAS`. D-1 재사용 입력 `d1_las.jsonl` → `resume_k1/h1_d1.jsonl`. 출력 폴더 `v5_rerun/las/` → `v5_rerun/las_k1/`. 판정 도구는 봉인 도구 `u3_judge`가 아니라 개정판 도구(16절)이고, 개정판은 태그 상수와 입출력 경로만 다르다(그 밖 코드 차 0을 `git diff`로 보인다) |
| H-5 | `u9_targeted_rules_rev1.md` | 태그 읽기 `final_C4G2` → `final_C4G2_LAS_K1`, `final_C4G2_P3` → `final_C4G2_P3_LAS_K1` |
| 작동 행 | `las_targeted_rules` 원판~rev4c(H-7′), rev5(T-3K) | H-7′의 "작동 행"을 7.2 분류의 LAS-b 작동·K1 막힘·둘 다로 넓힌다 |
| C-5 | 개정 12 2.2(짝은 재실행끼리만, 재실행↔저장은 기록, 해시 비교는 같은 `--threads`·둘 다 P), 12a(OMP 기록 + 플랜트 선행 검사), 12b(핵심·보조 배열) | 실행 35행(5.2) |
| C-6·C-7 | 명세 11047(열린 루프 이륙 전 최소 $F_a$ < $F_{min}$이면 FLAG), `run_S9.py` `p3a.checks` P3a-1~5 | 7.5 |

### 7.2 K1 작동 분류 (줄·행마다, 관문 켬 실행)

| 분류 | 조건(`controller_meta`) | 처리 |
|---|---|---|
| 미작동 | `liftoff_approach_slow.start_s` = None **이고** `slope_clearance_margin.order_gate.decisions`의 모든 항목이 `would_block` 거짓 | 명령 해시가 10절 비트 예측(P-1·P-2) 앵커 또는 저장 행 해시와 같아야 한다(해당 앵커가 있는 줄만). 다르면 멈춘다(8.2 S-5) |
| LAS-b 작동 | `start_s` ≠ None, K1 막힘 없음 | H-7′ 적용 |
| K1 막힘 | 어떤 `decisions` 항목이 `would_block` 참 ∧ `r4_due_without_gate` 참, LAS-b 작동 없음 | H-7′ 적용(C2·C3·C4′·C5′·P3-2 유지, None은 실패). 사건 `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order` 수 = `decisions` 막힘 수(다르면 8.2 S-5) |
| K1 막힘 — 균일 연약 지면 계열 | K1 막힘 ∧ 계열이 H-S-0·H-S-1, U-3·잡음의 균일 J1·J2·S1 바탕(패치·처방 침하 없음), Chrono 균일 SCM 행 | **멈추고 묻는다**(8.2 S-6). 근거: REM R1~R8 첫 R4 LOC dP +99~+206주기, 437.5 F2 |
| 둘 다 | LAS-b 작동 ∧ K1 막힘 | H-7′ 적용, 원인 칸에 둘 다 |

- 패치·처방 침하 계열(H-S-A, H-S-A-J2, H-R-A-J2, H-R-A-S1, H-S-C, H-S-C-g, G6 계열)의 K1 막힘은 의도된 동작(437.1)이다. 기록하고 H-7′만 적용한다.
- 관문 켬 실행이므로 각 `decisions` 항목에서 `applied`와 `would_block`이 함께 참이면 안 된다. 함께 참인 항목이 있으면 8.2 S-5.
- 분류에 쓰는 키가 없으면 그 줄은 `판정 불가`(None은 실패가 아니라 결측, 9.3).

### 7.3 J_P 재사용 조건 (모두 참이어야 재사용)

1. LAS-b 그림자 미작동(`shadow_jp_b0.jsonl`, 개정 11 2절).
2. K1 무영향: 저장 결과의 사건 기록에 `INFO_LOC_FLAT_SOIL_MARGIN`(R4c30 적용)이 0개이고 토양 모드 시작이 없다. 관문은 R4c30을 막기만 하므로 R4c30이 한 번도 적용되지 않은 실행은 관문 켬에서도 명령이 비트 단위로 같다(437.1).
3. 2의 판독은 python-expert가 사건 기록 형식(`controller_events.json`)을 코드로 확인한 판독 도구로 낸다. 문자열 검색은 근거로 쓰지 않는다(초안 단계 문자열 검색에서 `"INFO_` 자체가 검색되지 않았다).
- 하나라도 거짓이거나 판독 불가이면 J_P 12행을 묶음 `JP`로 재실행해 판정한다(5.2).

### 7.4 운용 시작 조건 밖 행과 O-C5

- **운용 시작 조건 밖 행**: 실행 $R_c$ > 1인 Chrono 행(예상: C-4 4행)의 $F_{min}$ 하회(`P3-3_within` 거짓)는 L-5 알려진 한계로 적는다. 묶음을 멈추지 않고 판정 등급에 넣지 않는다. 그 밖 판정 항목은 원 규칙대로 판정한다.
- **O-C5(C-8a·C-8b)는 기록 행이다.** 판정 등급(`통과`·`미달`)을 만들지 않는다. 본 행 $R_c \le 1$일 때 $m$ = 네 다리 $F^{\mathrm{a}}_{min}$의 최소로 다음을 적용한다.

| 조건 | 처리 |
|---|---|
| $m < F_{min}$ (= 9,414.589 N) | **멈춤**(8.2 S-9): 판정서에 적기 전에 사용자에게 다시 묻는다. 다른 묶음은 멈추지 않는다. 판정서 종합 문장과 L-5는 결정 뒤에 쓴다 |
| $F_{min} \le m < F_{min} + 2000$ N | 기록, L-5에 여유 값 $m - F_{min}$을 함께 적는다 |
| $m \ge F_{min} + 2000$ N | 기록 |

- 기록 항목(두 행 같음): 다리별 $F^{\mathrm{a}}_{min}$·$F^{\mathrm{t}}_{min}$과 그 시각, $F<F_{min}$ 시간, $F<F_{min}+2$ kN 시간(P5r4 판정서 8.2 표와 같은 정의, 1 ms 참 $F_{cyl}$), `P3-3_within`, LAS-b 시작·끝 주기와 끝 사유, K1 `decisions`, 실행 $R_c$·크롤러 자세·바닥 각·$k$, P3-1~P3-9·D8·G6 값.
- C-8a와 C-8b가 둘 다 멈춤에 걸리면 한 번에 묻는다.

### 7.5 열린 루프 (C-6·C-7)

- 기록이다. P3a-1~5 결과와 명세 11047 FLAG 여부를 적고, 논문 표 7·그림 5의 값 원본으로 쓴다. 실패·FLAG는 멈춤 사유가 아니다. 다만 P3a-1(힘 한계) 실패나 실행 오류는 판정서에 따로 적는다.

### 7.6 이 문서가 쓰는 숫자 (전부)

| 숫자 | 쓰는 곳 | 성격 |
|---|---|---|
| $F_{min}$ = 9,414.589 N | 7.4 | 기존 문턱(YAML) |
| $F_{min}$ + 2000 N = 11,414.589 N | 7.4 | 기존 문턱(G-2′와 같은 값) |
| $R_c$ ≤ 1 | 7.4, 5.4-9 | 기존 운용 시작 조건(CLAUDE.md, SL-2) |
| 0.95, 0.02, 최대 3건, +2 s, ×2 | 5.4 | 절차 값(가정, 판정 문턱 아님) |
| 1.035, 1.076 | 5.4 첫 축척 | 알려진 값(1.1절) |
| `--threads` 4 | 6 | 기존 실행 정체성 |
| 원 규칙의 문턱 | 7.1 | 바꾸지 않음(원문 그대로) |

- 문턱 비교: "$v \ge X$"는 $v \ge X - 10^{-9}$(그 단위)일 때 참, "$v < X$"는 $v < X - 10^{-9}$일 때 참, "$v > X$"는 $v > X + 10^{-9}$일 때 참, "$\lvert v - c\rvert \le e$"는 $\lvert v - c\rvert \le e + 10^{-9}$일 때 참이다. 이 비교 허용은 9.2의 두 경로 값 대조 허용과 다른 것이다.

## 8. 상태·멈춤

### 8.1 묶음별 상태 (앞의 것이 이긴다)

`판정 불가` > `미달` > `통과`. 기록 묶음(H-7, IND_LAS, C-4 기록 항목, C-6·C-7, C-8)은 등급 없이 `기록 완료` / `기록 불완전`. v5 종합 판정은 판정 묶음 상태의 최악이다. O-C5 멈춤이 걸리면 종합 문장은 사용자 결정 뒤에 쓴다.

### 8.2 멈춤 (그 묶음의 실행·판정을 멈추고 묻는다. 적힌 경우 말고는 다른 묶음은 계속)

| # | 조건 |
|---|---|
| S-1 | 이 문서·부록 A 문서의 sha256이 기록과 다르다(전 묶음 멈춤) |
| S-2 | 4.1 태그와 다르거나 한 묶음 안에 두 판이 섞였다 |
| S-3 | 4.2 금지 옵션·env가 있거나 4.2 기록 확인이 어긋났다(이중 적용 의심) |
| S-4 | SCM 정체성: `num_threads_chrono` ≠ 4, `OMP_WAIT_POLICY=PASSIVE` 없음, 훅이 fast가 아니거나 `fallback_reason` 있음, `MIXED_HULL_MODE` |
| S-5 | 7.2 미작동 줄의 해시 변화, `_SKIPPED:order` 수 ≠ 막힘 수, `applied` ∧ `would_block` |
| S-6 | 균일 연약 지면 계열의 K1 막힘(7.2) |
| S-7 | 비트 예측 P-1·P-2가 어긋났다(판정 전 멈춤, 원인을 본다) |
| S-8 | ③ 켬 대상 0(개정 11 #4), G-4·G-6 빈 선택(`u3_u6` 원판) |
| S-9 | O-C5 본 행 $R_c \le 1$에서 $m < F_{min}$(7.4). 그 행만 멈춤 |
| S-10 | O-C5 절차 멈춤(5.4-3·7), 본 행 $R_c > 1$(5.4-9). 그 행만 멈춤 |
| S-11 | 러너 로그 `errors` ≠ 0, 자리표시 남음, G-S 실패(11절) |
| S-12 | 한 묶음 안 커밋이 둘 이상이거나 실행 중 master 커밋·병합 |
| S-13 | 두 경로 등급이 다르다(9.2) — 그 묶음 `판정 불가` |
| S-14 | T-3K가 `통과`가 아니다(본 묶음 시작 전, 전 묶음 멈춤) |
| S-15 | 묶음 줄·행 수가 5.1·5.2 표와 다르다 |

## 9. 두 경로 판정

### 9.1 경로 표

| 묶음 | 두 경로 | 경로 1 | 경로 2(독립) |
|---|---|---|---|
| H-0 T-3K | 필요(rev3~5) | `las_judge`/H-7′ 모듈 | jsonl 재집계 |
| H-1·H-2 | 필요 | `run_v5.py d1` 판정 블록 + `d1_select.py` | jsonl 직접 재집계·재선별 |
| H-3·H-4 | 필요 | 개정판 `u3_judge` | 재집계 |
| H-5·H-6·H-8·H-9·H-10 | 필요 | 각 판정 도구 | 재집계 |
| H-7, IND_LAS | 불필요(기록) | 집계 1회 | – |
| 7.2 K1 분류 | 필요 | 판정 도구 | `decisions`·사건 수 재집계 |
| C-1~C-5 | 필요 | 행 판정기(`result.json` 판정 블록) | `series.npz`·`r8_series` 재계산 |
| C-6·C-7 | 필요(논문 표 7 값) | `result.json` `p3a` | `openloop_compare.py` `analyse`(`series.npz`) |
| C-8a·C-8b | 필요(7.4 멈춤과 L-5 값) | `result.json` 판정 블록(`P3-3_within`, $F^{\mathrm{a}}_{min}$, $R_c$) | 1 ms 참 $F_{cyl}$ 다리별 최소·시간을 `series.npz`에서 재계산, $R_c$는 기록된 크롤러 자세에서 2절 식으로 재계산 |
| $R_c$ probe | 불필요(절차 값) | 1회 | – |
| 7.3 J_P 재사용 판독 | 필요 | python-expert 판독 도구 | `controller_events.json` 직접 재집계 |

### 9.2 독립성과 대조

- **경로 2 작성자 요건**: 경로 2는 경로 1 도구를 만들거나 고친 사람(에이전트 실행)이 아닌 작성자가 쓴다. 경로 2 작성자에게는 이 문서, 부록 A 원 규칙, 원 데이터(jsonl·`result.json`·`series.npz`·`controller_commands.npz`·`controller_events.json`·`batch.json`)만 준다. 경로 1의 코드·출력·중간 파일·로그는 주지 않는다. 정의를 맞출 때는 이 문서와 원 규칙의 정의 문장만 쓴다.
- 경로 2 작성자는 판정서에 읽은 것 목록을 적는다(1.2절과 같은 꼴). 경로 1 코드를 본 사실이 있으면 그대로 적고, 그 묶음의 두 경로 판정은 `판정 불가`로 둔다.
- 순서: 두 경로 출력 파일을 모두 확정(sha256 기록)한 뒤 대조한다. 상대 출력을 본 뒤에는 어느 경로도 고치지 않는다. 고쳐야 하면 새 봉인 개정을 거친다.
- **대조(K-10 꼴)**: 등급·참거짓·목록·개수·분류는 완전 일치. 수치 값은 같은 단위에서 $\lvert a - b\rvert \le 10^{-9}\max(1, \lvert a\rvert, \lvert b\rvert)$(힘 N, 시간 s, 행정 m, $R_c$ 무차원)이면 일치. 판정서가 도구 밖에서 확정한다.
- 등급이 다르면 그 묶음은 `판정 불가`(8.2 S-13), 두 출력을 그대로 적고 묻는다. 등급은 같고 수치만 허용 밖이면 기록하고 python-expert에 원인 확인을 넘긴다(공개).
- 두 경로 정의가 다른 곳은 판정서에 표로 공개한다(P5r4 판정서 6.3 꼴).

### 9.3 결측

- 판정에 쓰는 키가 없거나 None인 항목은 원 규칙이 None을 실패로 정한 곳(H-7′ 등)만 실패이고, 그 밖은 `판정 불가`다. 결측 개수를 묶음마다 적는다.

## 10. 사전 예측 (P-1·P-2만 판정 전 확인 항목, 나머지는 판정 기준 아님)

| # | 대상 | 예측 | 근거 |
|---|---|---|---|
| P-1 | H-1 강체 412줄(H-R-0 264, H-R-A 144, H-R-A-stop 4) | K1 `decisions` 막힘 0. 명령 해시: T-1·T-2에서 돈 192키는 `las_T1.jsonl`·`las_T2.jsonl` b0 해시, H-R-0 나머지 216줄은 저장 `d1.jsonl` 해시. H-R-A-stop 4줄은 예측하지 않는다 | 저장 412줄 토양 모드 0·R4c30 0, 437.1, `k1_YT.jsonl` 192/192 |
| P-2 | H-1 토양 456줄(S-C) | 명령 해시가 H-SH 앵커와 같다: `k1_YP.jsonl`(`0d985d56…`) 165줄 + `soil_defer/s2d_SC.jsonl`(`70e91ec1…`) 291줄 | `k2/loc_shadow/hsh_report.md` 0·4.1절(`c6bb55b`에서 456/456) |
| P-3 | H-1 K1 막힘 | 패치·처방 침하 계열에만, 균일 계열(H-S-0·H-S-1) 0 | 437.1 |
| P-4 | H-2 | 옛 G-3 정지 행 `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K1` ε 0이 풀린다 | `las_judgement.md` 8.2 |
| P-5 | H-3·H-4·H-8·H-9 | 강체 바탕 K1 막힘 0. LAS-b 작동은 강체 + J1 패치·잡음 L3 G6 계열에 몰린다 | `las_judgement.md` 5절 |
| P-6 | H-10 main VB·LS 388 | R4c30 없는 322줄은 저장 해시와 같다. R4c30 있는 66줄은 강체 바탕이면 같고 패치 바탕이면 막힘이 생길 수 있다 | 초안 3.6절 |
| P-7 | C-3 | K1 무영향, LAS-b 미작동 → 같은 `--threads`·P면 저장과 명령 비트 같음(기록) | `v5_paper_runs_judgement.md` 7.4 |
| P-8 | C-5 토양 균일 행 | K1 막힘 0 | 437.2 |
| P-9 | C-4 | 켬 팔: P5r4 A1·A3와 같은 크기(Kc1 VB RL 약 10.81 kN, Kc3 VB 약 8.64 kN < $F_{min}$), $R_c$ 1.076 / 1.035(L-5, 멈춤 없음). 끔 팔과는 방향만(켬 ≥ 끔) | P5r4 판정서 5.1·8.2 |
| P-10 | C-6 | 속도비 0.8947 ± 0.001, 이륙 18.91 ± 0.15 s, 끝 \|Δpitch\| ≤ 0.1°, 다리 사이 행정 차 ≤ 2 mm, 이륙 전 후방 최소 $F_a$ 11.0~13.6 kN(FLAG 없음), P3a-1~5 통과 | `v5_paper_runs_judgement.md` 1.2·1.6절 |
| P-11 | C-7a | 유량 제한 0행, $Q_{sum}$ 최대 ≤ 50.2 L/min, 속도비 0.8769, 이륙 19.29 ± 0.15 s, 그 밖 C-6과 같은 크기 | 같은 문서 1.7절 |
| P-11b | C-7b | 속도비 0.8769, 이륙 19.29 ± 0.15 s(C-7a보다 0~0.1 s 이름), 후방 최소 C-7a와 ±0.5 kN 안, 끝 자세 ±0.02°, P3a-1~5 통과 | 같은 문서 1.7절 V0_FB |
| P-13 | C-8a | 본 행 $R_c$ 0.93~0.97. RL 최소는 A3의 8.64 kN보다 높다. **크기와 $F_{min}$ 위아래, LAS-b 시작 여부는 예측하지 않는다.** 최소 다리 RL | P5r4 판정서 8.2 |
| P-13b | C-8b | 본 행 $R_c$ 0.93~0.97. RL 최소는 A5의 8.51 kN보다 높다. 크기·$F_{min}$ 위아래·LAS-b 시작 여부는 예측하지 않는다. 최소 다리 RL | 같음 |
| P-14 | C-8 probe ↔ 본 행 | 정한 probe의 $R_c$와 본 행 $R_c$가 비트 같다(argv가 `--duration`만 다름) | 결정론 실행(P5r4 판정서 8.4) |
| P-15 | 전체 | 새 FAULT·실행 오류 0, `errors 0`, `MIXED_HULL_MODE` 0 | 재발 방지 4항 |

## 11. 순서와 관문

1. 0단계 H-0 T-3K → 판정(S-14).
2. 하네스 H-1 → H-2 → C-2 행 확정. H-3~H-10은 H-1과 병행 가능(H-3은 H-1 출력의 D-1 재사용 12를 쓰므로 H-1 뒤에 판정).
3. Chrono C-1·C-3·C-4·C-5·C-6·C-7과 O-C5 probe는 H-0 판정 뒤 바로 시작할 수 있다. C-2는 H-2 뒤. C-8 본 행은 그 행의 $k$가 정해진 뒤.
4. 묶음마다 아래 관문을 통과해야 시작·판정한다.

### 11.1 옵션 × 단계 겹침 표

python-expert가 묶음마다 "행 종류 × (프리셋·래퍼·argv·env)" 표를 만들어 4.2 금지와 4.1 태그가 맞는지 보인다. 실행 전 감사가 대조한다.

### 11.2 G-S 건조 실행

묶음마다 옵션 팔 × 단계 1행(하네스는 1줄, Chrono는 `--duration`만 짧게)을 같은 커밋에서 돌려, 판정 도구가 읽는 키 경로(4.2 기록 확인 키, 7.2 분류 키, 7.4 기록 키, 6절 정체성 키)가 **실제로 있음**을 확인한다. 값은 출력하지 않는다. G-S 결과는 판정하지 않는다. O-C5는 probe가 G-S를 겸하지 않는다(probe는 시작 조건 키만 읽음). C-8 G-S는 $k$ = 1(A행 바닥)로 `--duration`만 짧게 돈다.

### 11.3 러너 로그

`tools/verif/log_errors.py <러너 로그 폴더>` 종료 0(단계별 `errors 0`, `.done exit=0`)을 실행 중 점검과 판정 전에 확인한다.

### 11.4 자리표시

`tools/verif/placeholder_scan.py <prelaunch>/*.json` 종료 0. 판정서의 채울 칸(14절 `OC5A_SENTENCE`·`OC5B_SENTENCE`·`G1_VB_PROP_SENTENCE` 등, 중괄호 없는 대문자 이름)은 판정서 커밋 전에 모두 값으로 바꾼다. 남으면 S-11.

## 12. 비용 (가정, 사용자 결정 R-3 반영 재계산)

### 12.1 단가

| 엔진·행 종류 | 단가 [s/행] | 근거(1.1절) |
|---|---|---|
| SCM 균일·패치 토양(C-2 SCM, C-3, C-5 SCM) | 6,649~8,898 | B1 본 배치 6행 실측, P 4병렬, `--threads 4`, 훅 fast(사용자 지시 "B1 배치 4병렬 행당 6,600~8,900 s") |
| C-3 상한만 | 12,600 | 명세 436.9.7 어림(B1 상한보다 큼) |
| SCM 혼합 지형(C-4, C-8) | 3,885~4,413 | P5r4 A행 실측, P 4병렬 |
| L2b | 862~1,869 | 3단계 L2b 23행 실측, P |
| L1-R | 600 | 가정(측정 없음) |
| G1 열린 루프 | C-6 1,581, C-7a 1,754, C-7b 1,748 | 저장 G1 VB 1,581·V0 1,576 s × 39.93/36 |
| $R_c$ probe | 900~1,800 | 가정(CHECK까지, 미측정) |

### 12.2 묶음별 (CPU·s 합, 4병렬 실측 단가)

| 묶음 | 행(초안) | 행(이 문서) | 비용 [ks](이 문서) | 초안 비용 [ks] |
|---|---|---|---|---|
| C-1 | 10 | 10 | 7.6~13.6 | 약 7 |
| C-2 | 4~10 | 4~10 | 15.0~60.9(최소 L2b 2 + SCM 2, 최대 L2b 4 + SCM 6) | 19~46 |
| C-3 | 2 | 2 | 13.3~25.2 | 약 25 |
| C-4 | 4 | 4 | 15.5~17.7 | 약 17 |
| C-5 | 35 | 35 | 102.4~128.2(L2b 24: 29.3~30.3, SCM 11: 73.1~97.9) | 186~210 |
| C-6·C-7 | 3 | 3 | 5.1 | 5.1 |
| C-8 O-C5 | 1 + probe 2~3 | **2 + probe 2~6** | 9.6~19.6(본 행 7.8~8.8 + probe 1.8~10.8) | 6~10 |
| **Chrono 합** | 59~65 + probe 2~3 | **60~66 + probe 2~6** | **168.5~270.3** | 265~320 |
| (J_P 재사용 실패 시) | – | +12 | +10.3~22.4 | – |
| 하네스(H-0~H-10) | 360 + 9,800 | 360 + 9,800 | 약 740(변화 없음) | 약 740 |

- **R-3(V0 짝)로 늘어난 것**: Chrono 행 +1(C-8b), probe 최대 +3, 비용 +4.8~9.8 ks(본 행 3.9~4.4 + probe 0.9~5.4).
- C-5가 초안보다 작은 이유: 초안은 개정 12의 옛 어림(훅 채택 전, P/E 혼합)을 썼다. 저장 3단계 SCM 11행 실측 합은 168.6 ks(훅 채택 전, P/E 혼합)이고, 이를 상한 민감도로 두면 Chrono 합 상한은 약 311 ks다.
- 벽시계(어림): SCM·혼합·probe는 P에서 4병렬(16 논리 CPU) — CPU·s 합 129.9~218.9 ks → **9.0~15.2 h**. probe는 행마다 직렬 최대 3건(최대 약 1.5 h)이 C-8 본 행 앞에 온다. L2b·L1-R(38.6~51.4 ks)은 compute-scheduler-expert 배치(E에 두면 E/P 약 2.4~2.5배). 하네스 약 740 ks는 28 작업자에서 약 7.5 h(D-1 실측 비율). 전체 **약 1~2일**. 배치표·동시 개수·예약은 compute-scheduler-expert가 정한다.

## 13. 판정서에 적을 것

판정서 `06_analysis/02_control/verif_matrix/v5_resume_4368_judgement.md`에 다음을 모두 적는다.

1. 이 문서와 부록 A의 sha256, `git_at_start`, 묶음별 실행 기간·러너 로그 경로.
2. 묶음별 상태(8.1), v5 종합 판정, 멈춤이 있었으면 그 조건·사용자 결정.
3. 4.2 기록 확인 결과(행 수·어긋난 수), 6절 정체성 표(SCM 행 `num_threads_chrono`·`start_env`·`pool`·`planned_pool`·`placement`·훅).
4. 7.2 분류 표(묶음 × 분류 줄 수), K1 막힘 계열 목록, 미작동 줄 해시 비교 결과.
5. 7.3 J_P 판독 결과와 재사용 여부.
6. 10절 사전 예측 대조(맞음·틀림, P-1·P-2 결과 먼저).
7. 9절 두 경로: 경로별 작성자·읽은 것, 출력 sha256, K-10 대조 결과, 정의가 다른 곳 표.
8. O-C5: 5.4 절차 기록(행마다 probe 수, $k$, 바닥 각, $R_c$), 7.4 기록 항목, 멈춤 여부.
9. 시작 조건 밖 행 목록과 그 행들의 $F_{min}$ 하회(L-5 근거).
10. 11절 관문 결과(G-S 목록 sha, `log_errors.py` 출력 경로, `placeholder_scan.py` 결과), 실행 전 감사 리포트 경로·sha.
11. 14절 한계 문장 L-1~L-5(채울 칸을 값으로 바꾼 것).

## 14. 한계 문장 (판정서 한계 절에 그대로, 논문은 문체만 맞춤)

**L-1 비틀림 이득과 θ 채널 $M_s$** (원본 `06_analysis/02_control/k2b/twist_gain_margin.md` 5절)

> 하네스는 잠긴 다리의 로드측 강성이 없어 비틀림 루프 이득이 실기보다 최대 1/1.3배 작다. 실기 이득에서도 비틀림 채널은 $M_s \le 1.25$, GM ≥ 6.0, PM ≥ 73.7°이다. 다만 오거 상단·β 1.6 GPa·마스트 대리 조합 한 점에서 자세 θ 채널 $M_s$가 1.53(기준 1.5)으로, 이 점은 비틀림 이득과 무관한 상계 대리값이며 L1-R Chrono 대표 행이 판정한다.

**L-2 LOC 앵커 단일 표본 기울기** (원본 `06_analysis/02_control/k2/judgement/loc_anchor_review.md` 4절, `06_analysis/02_control/k2/loc_shadow/hsh_report.md` 0절)

> 크롤러 이탈 확인(LOC) 때의 틈 추정 기준은 이탈 순간 한 주기(0.1 s)의 원시 기울기를 자세로 쓴다. 그래서 단단한 바닥의 이탈 과도에서는 틈 추정이 ±(10~20) mm 흔들리고, 균일 연약 지면 Chrono에서는 −5.5~+2.7 mm다. 중심 1 s 평균을 쓴 그림자 추정과 비교하면 D-1 토양 계열 하네스 456줄에서 차이가 −18.1~+0.53 mm였고, 판정 여유 안쪽에 든 줄은 없었다. 그 밖 묶음은 미측정이다. 추정기 수정은 v5 뒤 과제로 둔다.

**L-3 하네스 $k_{lock}$ 미포함** (원본 `06_analysis/02_control/k2/judgement/k2_dyn_sensitivity.md` 덧붙임 A)

> 하네스 축소 모델에는 잠긴 다리의 로드측 기름 기둥 강성 $k_{lock}$이 없어, 늦게 닿는 대각 쌍이 먼저 래치된 쌍의 하중을 가져가는 비틀림 결합(M2)에서 뒷다리 하중 손실을 약 25 % 작게 본다(β 1.0 GPa에서 −5.2 대 −7.0 kN/mm). 그래서 하네스의 TOUCH·이탈 판정은 이 기구에 대해 비보수 쪽이고, 잠김 상태 판정에 대한 영향은 방향이 정해지지 않았다. v5 하네스 결과는 이 모델 그대로 판정했으며, $k_{lock}$을 포함한 Chrono L1-R 대표 행이 교차 확인을 맡는다.

**L-4 유량 분배 법칙** (원본 `v5/v5_paper_runs_judgement.md` 1.6절, 사용자 결정 11-10 Q-2·11-11 Q6)

> 폐루프 판정(VB)은 우선 분배 법칙을 기준으로 했고, 비례 분배는 열린 루프(J1·G1)에서만 확인했다. G1_VB_PROP_SENTENCE

**L-5 운용 시작 조건 밖의 이탈 뒤 비틀림 하회** (원본 `las_p5r4_k1_judgement.md` 8.2절·"D-2 진단 요약"·10절 D-2, 사용자 결정 2026-11-12)

> 혼합 지형(강체 바닥 + 전방 우측 패드 아래 연약 패치) Chrono에서 채택 제어기는 크롤러 이탈 뒤 0.5~0.7 s에 대각 반대 다리(후방 좌측)의 실린더 힘이 $F_{min}$ 아래로 내려갔다(크롤러 강성 ×3·VB 8.64 kN 195 ms, ×1·V0 8.51 kN 67 ms). 주성분은 동적 과도가 아니라 준정적 4점 비틀림이다. 이탈 감속(LAS-b)이 끝난 다음 주기에 명령이 원래 속도로 돌아가며 생긴 비틀림 계단과 연약 패치 침하가, 이탈 뒤 네 다리 기름 기둥 강성(명령 비틀림 1 mm당 후방 좌측 하중 약 −6.5 kN)을 거쳐 하중으로 옮겨졌다. 이 행들은 실행 시작 자세 비 $R_c$ 1.035~1.076으로 운용 시작 조건($R_c \le 1$) 밖이다. 모델 상부체는 강체라 비틀림 강성을 크게 보므로 이 값은 보수 쪽이고, 유압유 체적 탄성 계수 β에 민감하다. OC5A_SENTENCE OC5B_SENTENCE 이탈 감속 끝 처리의 재설계는 v5 뒤 과제로 둔다.

- 채울 칸: `G1_VB_PROP_SENTENCE` = C-6 결과 한 문장(값만, 해석 없음). `OC5A_SENTENCE` = "운용 시작 조건 안($R_c$ = 값)으로 옮긴 같은 조건(크롤러 강성 ×3·VB)에서 후방 좌측 최소 힘은 값 kN이었다." 꼴, `OC5B_SENTENCE` = 같은 꼴(×1·V0). 7.4 멈춤에 걸리면 L-5 전체를 사용자 결정 뒤 다시 쓴다. C-8 본 행 $R_c > 1$이면 그 행의 칸은 "운용 시작 조건 안으로 옮기지 못했다($R_c$ = 값)."로 쓴다.
- C-4 켬 팔에서 같은 하회가 다시 나오면 그 값도 L-5 근거로 판정서에 함께 적는다.

## 15. 결과 전 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-11 | Q1 | (a) 하네스 재사용분 전부 재실행(H-10 462 + dg3 v4_on 135), Chrono J_P 12만 7.3 조건으로 재사용 | 5.1, 5.2, 7.3 |
| 2026-11-11 | Q2 | (b) G1 속도 낮춤 VB + V0 2행 | 5.3 |
| 2026-11-11 | Q3 | (a) T-3K는 0단계로 먼저, 판정 뒤 본 묶음 | 11, S-14 |
| 2026-11-11 | Q4 | (a) dg3 off 135 전부 | 5.1 H-7 |
| 2026-11-11 | Q5 | (a) LOC 앵커 그림자 훅을 걸지 않음 | 4.2, L-2 |
| 2026-11-11 | Q6 | 넷째 한계 문장 = L-4 | 14 |
| 2026-11-12 | E-1 | P5r4 `미달` 확정, P0 유지 | A-1 |
| 2026-11-12 | E-2 | O-C5 기록 행, 범위 안 하회면 다시 묻는 멈춤 | 5.4, 7.4, S-9 |
| 2026-11-12 | E-3 | 한계 문장 L-5 | 14 |
| 2026-11-12 | E-4 | LAS-c는 범위 밖 | 0-5 |
| 2026-11-12 | R-1 | 바닥 각 절차 허용 ±0.02, probe 최대 3건 | 5.4 |
| 2026-11-12 | R-2 | C-4는 `_LAS_K1`로 다시 돌린다(P5r4 결과 재사용 안 함) | 5.2 C-4 |
| 2026-11-12 | R-3 | **V0 짝을 둔다**(초안 추천 '없음'과 다름) | 5.2 C-8b, 5.4, 7.4, 12 |

## 16. 구현 목록 (위임, 봉인 전 정의·봉인 뒤 실행 전 감사)

| 대상 | 일 |
|---|---|
| python-expert | A-4 행 생성기 5개 기대 태그 `_LAS_K1`, 개정판 `u3_judge`(태그 상수·경로만), 4.3 출력 이름, `steps_h2.json` 갱신과 줄 수(5.1), 7.2 분류 판정 모듈, 7.3 J_P 사건 판독 도구, 4.2 기록 확인 검사, 11.1 겹침 표, 11.2 G-S(하네스), 경로 1 판정 도구 |
| cad-expert | C-1~C-5 행 정의 태그 갱신 확인, C-4 끔 팔 `--las-off --k1-order-gate on`, C-4 켬 팔 ↔ P5r4 A1·A3 `option_diff`, C-6·C-7 3행(`check-sources`), C-8a·C-8b 행 정의(바닥 인자만 다름), $R_c$ probe 실행기·판독기(5.4-1~3, 시작 조건 키만 출력), `PROBE_DURATION` 결정, A-7 스냅숏 사용 행 확인, 행별 est_s, Chrono G-S |
| control-expert 아닌 경로 2 작성자 | 9.2 요건의 경로 2(묶음별). 작성자 배정은 메인 세션 |
| compute-scheduler-expert | 배치표(SCM P 4병렬, L2b·하네스 배치, probe 직렬), 예약 |
| verif-protocol-auditor | 묶음마다 `[시점] 실행 전`, 판정서 커밋 전 |

## 17. 가정

| 가정 | 값 | 근거 |
|---|---|---|
| 하네스 R4c30 사건 판독(초안 단계) | 줄 문자열에 `INFO_LOC_FLAT_SOIL_MARGIN`이 있으면 R4c30 적용 | 저장 기록이 K1 전이라 `_SKIPPED`가 없다 |
| G1 속도 낮춤 인자 | J1과 같은 `--lift-s 31.93 --lift-speed-fraction 0.87684` | 같은 펌프·실린더·명령 행정 |
| O-C5 절차 | 목표 0.95, 허용 0.02, probe 최대 3건, 첫 축척은 $R_c$가 바닥 각에 비례한다는 가정 | 사용자 결정 R-1 |
| C-8b 바탕 | A5 조건(Kc1, V0) | 초안 R-3 (b) 문구, 확인 필요 질문 Q-A |
| 비용 단가 | 12.1 표 | 실측 + 가정(L1-R, probe) |
| T-3K 결과 | 통과로 가정하고 계획 | 미실행 |

## 부록 A. 기준 파일 (봉인 때 다시 계산해 대조, sha256 전체, 2026-11-13 `3d41083` 작업 트리, `.sha256` 기록과 모두 일치)

| 파일 | sha256 |
|---|---|
| `06_analysis/03_hydraulic/coupled/v5/v5_criteria.md` | `06ed0384fb942cfdf9ab481878ffd5f19d5faab4e6163aa986dcdda5156e080e` |
| `…/v5_criteria_rev1.md` | `cbfac2b2de571500fbf5410dd5456bfa82d4a05cf25f21c76feb25fab1308fab` |
| `…/v5_criteria_rev2.md` | `e120474b8ebd721e6edc4fec8eef811ce810006b8c489e38cecbb7ae5caeed77` |
| `…/v5_criteria_rev3.md` | `7084da25c6129681086efc4fbc5afb315d7b4d424cbed123746ec32b4ea61ec2` |
| `…/v5_criteria_rev4.md` | `642e96f9cfd20a9c2a016ed128a6ce7d584718e5728d6008640f8703a5acbd72` |
| `…/v5_criteria_rev5.md` | `945f714660cd3ec7e749151bcd81b1f9da35b6001d7fd9c7e2cfeee21fcd320b` |
| `…/v5_criteria_rev6.md` | `fd5117031ef460cf4c6aa74807b2e73de984b014abb89a952b593499841da39c` |
| `…/v5_criteria_rev7.md` | `9ccde7a5a4128317ed832dd2f92cd2368280f18cefa6827f1b1731c6d4e9aab3` |
| `…/v5_criteria_rev8.md` | `c6ec89f71c1d8de4c06000568c2e5978fd7f9fe58a53defea728f2f4886bb25f` |
| `…/v5_criteria_rev9.md` | `3c50dda50ca6dca60177f26d91d86c009eeb4f9321f5ffd0c98ddc27cf62e981` |
| `…/v5_criteria_rev10.md` | `bd65db24f68a6d4c3a8346447a0cbfdd89e97cd07f4b295237127c304174e182` |
| `…/v5_criteria_rev11.md` | `ca6b5c95d8f544ff8ec5db2e1ec193d2b200df74c2e9c7decdb56b61757e2ecb` |
| `…/v5_criteria_rev12.md` | `e02d63cc1290383ee85d9a1f3a20c6348224b60999cccaf8d587cf610c5f5eb2` |
| `…/v5_criteria_rev12a.md` | `e171141dce180fbb48493b9b95503ff3577d16f17cc54061ce3ad6e9efd51458` |
| `…/v5_criteria_rev12b.md` | `0d17f87e9532d558efcab9fa89648e2790ece9c7568a802fbaa4c7631824e75d` |
| `06_analysis/02_control/verif_matrix/d1_selection_rules.md` | `51dea528e57fa0c4378cda110addb73da20339535e16189452af2d06b60736e9` |
| `…/d1_selection_rules_rev1.md` | `eb730bddae35e76bc2569503605dea714b066fa42de7bc7b98efdde3edb3e868` |
| `…/u3_u6_rerun_rules.md` | `8de318825764114ad14afcec362c87c1e01a2ad47195b8491b1c96056e1960b3` |
| `…/u3_u6_rerun_rules_rev1.md` | `2c5e69213b29fc930c478306676efc72b515d67af08634adab3eba2d05f5f15d` |
| `…/u3_u6_rerun_rules_rev2.md` | `be1584a4448d68a30c4fe9ec613d3d7b3cb0b47169c2f5eff72e9a9ca0776880` |
| `…/u9_targeted_rules_rev1.md` | `644005b706ba46cebba11b975ded474226cc4eab5030ee18e9f91dacd2d14587` |
| `…/las_targeted_rules.md` | `00b48fd834d81b9d499015f2d44380623e9fbcb2f1515913a8fd0589503eaf40` |
| `…/las_targeted_rules_rev1.md` | `0d5f59f8e4a09448b93e0cde42adb7d23c2f99f6b365809876efaa6212d27625` |
| `…/las_targeted_rules_rev2.md` | `6be736cb98cea34e4a606606b4009668bbc1470c8a7db23b6a119ef033c97960` |
| `…/las_targeted_rules_rev3.md` | `956f65c74e36eb8fe921dc6399b0d5f2f04099b7852380362351f658c9791cd1` |
| `…/las_targeted_rules_rev4.md` | `05fbde22009c10b74ddf0df071452a99631bb319c2f482df83be59adfad1de6d` |
| `…/las_targeted_rules_rev4a.md` | `3cbbfb5d8afda9075bf9631accf1b8bee4c1ee02edafa34a7869091175a73b15` |
| `…/las_targeted_rules_rev4b.md` | `add921e4978ef16abcc22dfc88dc25e51a770dc98d2d540526f48cf6ea7a6f3f` |
| `…/las_targeted_rules_rev4c.md` | `7e45993f667382f56aeb1b72bb5e7023ecfe3048a3723ac050cefc3b2a721417` |
| `…/las_targeted_rules_rev5.md` | `879d0e4d715b2e9f4e51257863fc259ccfe48105ca019299547d58dca24949b2` |
| `…/las_k1_rules_adopt2.md` | `fb3a5696f24385e81acc9c564500b5e5a0547db45a5335272e7d18400f1e68e8` |
| `…/las_k1_rules_adopt_rev1.md` | `730dbb3d30dffca6d652953c22b62563141beeee6af6f045d6b2cb59f60deb65` |
| `…/las_p5r4_k1_judgement.md`(봉인 아님, 1.1 근거) | `5e9fb33b7419d624d8dc305ad93121be090802cc5c85ea29fbc823e019fc9e2f` |
| `…/v5_resume_4368_plan_draft.md`(봉인 아님, 입력 초안) | `141e4958f39b7c7470bb4c66003877f2af0c14c93300a705eb60988e2a04033d` |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 파일 이름: `v5_resume_4368_rules_seal_candidate_draft.md` → `v5_resume_4368_rules.md`(같은 폴더). 초안 파일은 지우지 않고 그대로 둔다.
2. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 (제어기 `final_C4G2_LAS_K1`, 봉인)`
3. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_seal_candidate_draft.md`와 1·3·5행만 다르다.`
4. 5행("시점")을 다음으로 바꾼다:
   `- **시점: 436.8의 어떤 실행 결과도 없을 때(봉인 SEAL_TIME, 봉인 커밋 SEAL_COMMIT).** 436.8 묶음(0단계 T-3K 포함)은 한 줄도 돌지 않았다. 이 규칙을 쓰려고 읽은 것은 1절에 모두 적었다.`
   - `SEAL_TIME`(예: 2026-11-13 10:00:00 +09:00)과 `SEAL_COMMIT`(봉인 파일을 넣는 커밋의 앞 커밋, 7자리)은 메인 세션이 값으로 바꾼다. 이 두 이름 말고는 본문을 바꾸지 않는다.
5. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules.sha256`에 `<sha256>  v5_resume_4368_rules.md  sealed <SEAL_TIME 값> (436.8 v5 resume rules: v5 criteria rev13 + u3_u6 rev3 + O-C5 VB/V0 record rows; thresholds unchanged)` 한 줄로 쓴다.
6. `.gitattributes`에 `06_analysis/02_control/verif_matrix/v5_resume_4368_rules.md -text`와 `…/v5_resume_4368_rules.sha256 -text`를 더한다.
7. `tools/verif/seal_check.py`로 확인한 뒤 커밋한다. 봉인 뒤 이 문서를 고치지 않는다. 고칠 것이 생기면 `v5_resume_4368_rules_rev1.md`로 새로 봉인한다.


<!-- C-01 v5_resume_4368_rules_rev1.md:48 -->
### RV1-3.2 묶음별 정의

| # | 러너(저장소) | 조건 | 작업 키 원본(sha256 앞 16자리) | 수 |
|---|---|---|---|---|
| H-6 | `04_scripts/04_hydraulic/coupled/las_t3_dg3.py`(`r79_L3L4_final.py`를 그대로 부름) `run --levels L2,L3 --keys <135키>` | env `R79_V5_SETTING=VB`, `R72_PATH=per_leg`, `R79_T4H_DIR`(T4h 폴더), `LAS_T3_DG3_LAS=on`, `LAS_T3_DG3_K1=on`, `LAS_T3_DG3_P3=on` | `v5/dg3/dg3_v4_on.json`(`5f912ca0d25d6dfe`) | 135(L3 134 + L2 1) |
| H-7 | 같음 | 같음, 단 `LAS_T3_DG3_P3=off` | `v5/dg3/off/dg3_off.json`(`95b81f82d800ae3c`), 키 집합은 H-6과 같다 | 135 |
| H-8 잡음 VB·V0 | `04_scripts/03_control/s8/r79_L3L4_final.py run --levels L1,L2,L3`(키 지정 없음) | env `R79_V5_SETTING=VB` 또는 `V0`, `R72_PATH=per_leg` | `v5/noise_vb/r79_VB_L1L2L3.json`(`d3c9bba1abd3c1fb`), `v5/noise_v0/r79_V0_L1L2L3.json`(`af6a7ae51abe4b90`), 두 키 집합은 같다 | 1,503 × 2 |
| H-8 seedext | `r79_L3L4_final.py run --levels L2`에 저장 키 목록을 그대로 받는 저장소 옵션(python-expert 추가, 아래) | env `R79_V5_SETTING=VB` 또는 `V0`, `R72_PATH=per_leg` | `v5/seedext/r79_VB_seedext.json`(`6ddca3d5ce5dc628`), `…/r79_V0_seedext.json`(`f2c01d65238cac50`), 두 키 집합은 같다(2기본 키 × 시드 0~24) | 50 × 2 |
| H-9 격자 | 저장 V0 짝 provenance의 `script`와 같은 파일: `grid_r67_main`·`grid_r67_top` = `r67_g1_screen.py`, `grid_r69_bottom`·`grid_r69_top` = `r69_g5_screen.py` | env `R67_*`는 저장 `v5/grid_vb/<파일>.json` `meta`(`offsets_s`, `n_jobs`, `candidate` = current, `v5_setting` = VB)가 같아지도록 python-expert가 정한다 | `v5/grid_vb/grid_r67_main.json`(`8ef4237dc7658559`), `…_r67_top`(`498aa41199b2e4ed`), `…_r69_bottom`(`ee84750be278a2c2`), `…_r69_top`(`c132fd41f13b8033`) | `runs[]` 192 × 4 = 768 |

- **H-7의 ③ 끔**: `LAS_T3_DG3_P3=off`는 `run_v5.SETTINGS["VB"]`에서 `extend_start_tracked`만 뺀다(`las_t3_dg3.py` 66~71행, 봉인 rev3~rev5 T-3b가 같은 러너로 쓴 끔 팔). 프리셋 `with_10hz_d1()` 기본값은 건드리지 않는다. **원판 4.2의 금지 래퍼에 해당하지 않는 것으로 H-7에만 허용한다.** H-6·H-8·H-9·H-10에는 `LAS_T3_DG3_P3=off`를 쓰지 않는다. `LAS_T3_DG3_LAS=off`는 어느 묶음에도 쓰지 않는다.
- **H-7 기대 태그**: VB 플랜트지만 ③ 꺼짐이므로 `final_C4G2_LAS_K1`이다(원판 4.1 "그 밖 ③ 없는 설정"). `is_extend_start_tag`가 거짓이어야 하고, 실행된 프리셋의 `two_pressure.extend_start_rule`이 `tracked_bound`가 아니어야 한다. H-6은 `final_C4G2_P3_LAS_K1`, `tracked_bound`다.
- **seedext 키 옵션**: `r79_L3L4_final.py` `cmd_run`은 기본 시드 밖의 키를 거부한다(`keys not in the job list`). python-expert가 저장 키 목록 파일을 그대로 받는 옵션을 저장소에 넣는다. 그 옵션은 작업 목록만 바꾸고 작업마다 `run_one`을 그대로 부른다. 그 커밋은 `git_at_start` 이전이어야 한다(원판 A-5). G-S(11.2)에서 시드 ≥ 3인 키 1줄을 돌려 받아들여지는지 본다.
- **H-8의 dg3 대체**: 원판 5.1 H-8 "dg3가 대체한 L3 134·L2 1의 처리는 원 규칙 그대로"는 그대로다. 그 135키는 H-6 줄로 판정한다. 같은 키의 H-6 줄과 H-8 VB 줄의 `commands_sha256` 같음 여부를 기록한다(같다고 예측한다. 다르면 기록하고 python-expert에 원인 확인을 넘긴다. 멈춤 사유가 아니다).
- **H-8 seedext와 잡음의 겹침**: seedext 키 가운데 시드 0~4의 10키는 잡음 키와 같다. 파일이 달라 줄 수는 원판대로 센다(H-8 = 1,503 + 1,503 + 50 + 50 = 3,106).
- **H-9 격자의 줄 수**: 격자 파일의 S-15 대조값은 `runs[]` 수(파일마다 192, 합 768)다. 격자 줄의 태그 확인(원판 4.1·S-2)과 4.2 기록 확인은 각 run의 `resume_k1` 블록과 v5 기록 칸으로 한다. 태그 필드가 run에 없으면 G-S에서 멈추고 묻는다(S-11).

<!-- C-02 v5_resume_4368_rules_rev1.md:83 -->
## RV1-5. P-1·P-2 비트 앵커의 줄 대응 (질문 5)

- 앵커 줄과 H-1 줄은 **`run_v5.job_key(line["job"])`이 같은 것끼리** 짝짓는다(`job`에서 `mask`·`t4h_dir`만 뺀 전체 사전). `rev.key`·`d1.key` 같은 문자열 키는 대응에 쓰지 않는다. 2026-11-13 계산에서 여섯 앵커 파일의 모든 줄이 `d1_rows.jobs()`의 작업과 이 방식으로 맞았다.
- 앵커 줄 고르기(각 파일에서 `error` 키가 없는 줄만):

| 예측 | 앵커 파일(sha256) | 고르는 줄 | 키 수 |
|---|---|---|---|
| P-1 T-1 | `v5/las/las_T1.jsonl`(`3dee4f6b88e71654debd68b3ef5c5f1a9b01f1dba8fcd731d1355ec219d9a85b`) | `las.candidate` = `b0` | 8(H-R-A) |
| P-1 T-2 | `v5/las/las_T2.jsonl`(`2fe6a54aafdc0c3ffbf1991907ee4e1af85761e1bef2e25bef07dd52ab199efb`) | `las.candidate` = `b0` | 184(H-R-0 48 + H-R-A 136) |
| P-1 나머지 | `v5/d1.jsonl`(`9039b36a1a9c4ba5ed63528bb7384773018d4c7377dccbf76b18fbcfda86707f`) | 위 192키 밖의 H-R-0 줄 | 216 |
| P-2 Y-Pa | `v5/las/k1/k1_YP.jsonl`(`0d985d5624f0fbb0219ca50d1c839b7db639011d6c2ab14fa9d84cfd197fc2c3`) | `k1.sub_bundle` = `Y-Pa` ∧ `las.candidate` = `P0` | 165 |
| P-2 나머지 | `v5/soil_defer/s2d_SC.jsonl`(`70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa`) | Y-Pa 165키 밖의 줄 | 291 |

- 고른 앵커는 키마다 정확히 1줄이어야 한다. 0줄이나 2줄 이상이면 S-7이다. 2026-11-13 계산: 중복 0, T-1·T-2 겹침 0, 192키 ⊂ 강체 412, Y-Pa 165 ⊂ 토양 456, `s2d_SC.jsonl`이 토양 456을 모두 덮는다. H-R-A-stop 4줄은 원판대로 예측하지 않는다.
- 대조하는 값은 `commands_sha256`(64자리)뿐이다.

<!-- C-03 v5_resume_4368_rules_rev1.md:99 -->
## RV1-6. 7.2 계열 판정과 적용 범위 (질문 6, 덧붙임 발견 1건)

- **계열 표**: python-expert가 H-1·H-3·H-4·H-6~H-10의 모든 작업 키를 세 계열(강체 / 패치·처방 침하 / 균일 연약) 가운데 하나로 나눈 표를 실행 전에 만든다. 분류는 문자열 추측이 아니라 그 러너가 그 키로 만드는 지면 정의(바탕 토양, 패치 토양·다리, 처방 침하)에서 읽는다. 표의 sha256을 첫 본 실행 전에 기록하고 11.1 겹침 표와 함께 실행 전 감사가 본다.
- 원판 7.2 "균일 연약 지면 계열" = 계열 표의 균일 연약(바탕이 연약 토양이고 패치·처방 침하가 없음)이다.
- **표가 나누지 못한 키는 균일 연약으로 다룬다.** 그 키의 K1 막힘은 S-6(멈추고 묻는다)이다. "family unresolved"로 판정을 계속하지 않는다.
- 경로 2는 이 표를 쓰지 않고 원 규칙의 정의 문장과 키·지면 기록으로 따로 나눈다. 두 경로 분류가 다르면 그 줄은 원판 9.2대로 `판정 불가`(S-13)다.
- **덧붙임(발견)**: `resume_k1` 블록의 `applicable`이 거짓인 실행(C2 설정이 없는 IND·IND_LAS)은 K1 관문이 없으므로 원판 7.2 분류와 4.2 기록 확인의 대상이 아니다. 그 줄은 "해당 없음"으로 적고 원판 7.2 끝 문장(키 없음 = `판정 불가`)을 적용하지 않는다. ABL(`ABL_LAS_K1`)은 대상이다.

<!-- C-04 v5_resume_4368_rules_rev3.md:132 -->
### R3-B6. 정착 판정 v2 기록과 경로 2 재계산 (R3-B1 A안의 입력 문장)

- **적용 묶음**: 원 규칙 4절 52행의 정착 판정 v2 대상인 연구 ①(slope)·H6·H9·연구 B(x426b)·연구 D와, U-3이 재사용하는 D-1 정상 상태 줄이다.
  - P3b는 rev1(u3) 17행대로 `p3_lite_gates`로 판정하므로 v2 대상이 아니다.
  - 한 패드 연약부(g6)·연구 C는 r72 G6 판정, 비평면 시작(g8)은 g8 판정이므로 v2 대상이 아니다.
- **기록 위치**: 대상 묶음의 레코드(연구 D는 `results[]` 항목)는 최상위 `settle_v2`, D-1 재사용 줄은 `u3.settle_v2`다. 대상 묶음의 레코드에 이 블록이 없으면 그 줄의 정착 항목은 `판정 불가`(원판 9.3)다.
- **상태 `status`에 따른 처리**:
  - `checked`: 아래 재계산을 한다.
  - `no_table_check`: 정착 표에 그 사례 행이 없어 v2 대조 대상이 없다. 정착 항목은 "해당 없음"으로 적고 등급에 넣지 않는다. 표 행이 없는 사례가 v1에서도 정착 점검 대상이 아니었다는 것은 **가정**이다. 개수를 판정서에 적는다.
  - `error`: `판정 불가`다.
- **경로 2 재계산(`checked`)**: `inputs`만으로 명세 398.3절 v2 식을 다시 계산하고 `result`와 대조한다.
  1. 패드마다 pen_mean,i = pen_inst,i + (y_i Δφ − x_i Δθ)를 구한다. 입력은 `pen_inst_mm`, 패드 좌표 `pad_xy_m`, 자세 변화 `d_attitude_deg`(창 평균 − 순간)이다.
  2. 패드마다 |pen_mean,i + gap_target,i| ≤ 1 mm인지 본다(`gap_target_mm`).
  3. 자세 허용 = max(0.005°, `residual_deg` + 0.002°). `attitude_error_deg`가 이 허용 이하인지 본다.
  4. `ok` = 2와 3이 모두 참이다.
- 대조:
  - 1~4의 값과 참거짓이 `result`의 `pen_mean_mm`, `pen_plus_gap_mm`, `gap_ok`, `attitude_tol_deg`, `attitude_ok`, `ok`와 원판 9.2 K-10 꼴로 같아야 한다. 다르면 그 줄은 `판정 불가`(S-13)다.
  - 문턱 1 mm·0.005°·0.002°는 398.3의 값이다. 기록의 `tolerances`가 이 값과 다르면 그 묶음은 S-11로 멈춘다.
  - 경로 2는 입력 출처도 확인한다:
    - `table_sha256`이 `table`이 가리키는 정착 표 파일의 sha256과 같은지 본다.
    - `gap_target_source`가 표일 때는 `gap_target_mm`이 그 표의 `table_key` 행 값과 같은지 본다.
    - 다르면 `판정 불가`다.
- **`gate`에 따른 등급**:
  - `judged`: `ok` 거짓이면 그 줄의 정착 항목 실패(`settle_check_fail`)다.
  - `settle_check_fail`: 기록된 결론이다. 경로 2는 재계산한 `ok`로 같은 결론이 나오는지 본다.
  - `record_only`: 질량 배율 실행처럼 정착 점검이 기록만인 경우다(명세 422.2). 등급에 넣지 않는다.
- 결정 필요: **아니오**(Q-U1 = A의 문장화).

<!-- C-05 v5_resume_4368_rules_rev3.md:223 -->
### R3-C7. J11의 `n_late` 결측 (J 항목)

- **정의**:
  - 대체 다리가 없는 줄에서 `n_late`가 없거나 None이면 `not_computed`로 기록한다.
  - **대체 다리가 있는 줄**에서 `n_late`가 None이면 J11의 멈춤 조건(대체 다리 `n_late` > 0)을 확인할 수 없으므로 그 줄은 `판정 불가`다(원판 9.3).
- 근거: v5 기준 65행("대체 다리 n_late > 0은 멈춤. 그 밖은 기록").
- 결정 필요: **아니오**.

<!-- C-06 v5_resume_4368_rules_rev3.md:231 -->
### R3-C8. J-P3과 로드 판독 (J 항목)

- **정의**(E절 Q-S3·Q-G3을 받아 고쳐 씀): J-P3은 ③ 켬(`is_extend_start_tag`) 줄에만 적용하고, 개정 9 3.2 표(#1~#5)를 그대로 쓴다. 표의 두 입력은 다음으로 정한다.
  1. **로드 판독 유무**(개정 9 3.1): 그 줄의 T4h 기록에서 `rod_pressure_Pa`가 하나라도 유한값이면 "있음"이다.
     - T4h 기록이 없는 줄은 실행 구성으로 정한다. 구성이 두 압력 판독이면 "있음"이다(예: r67 축소 스크린, 명세 342.1 "헤드·로드 판독은 순 기름 힘에서 두 압력을 만듦").
     - T4h도 구성 근거도 없으면 그 줄의 J-P3은 `판정 불가`다.
  2. **헤드 전용 구성(선언)**(개정 9 3.1): 줄의 `head_only_declared`가 참이면 선언이 있다.
     - 필드가 없으면 개정 9 3.1의 구성 정의로 정한다: 하네스 steady 경로 사례(R1~R11, S1~S8, `s9_soil_slope` 경로)이거나 판독 설정이 `head`인 실행이면 선언이 있다.
     - 선언 값을 뒤집어 로드 판독 유무를 가정하지 않는다.
- 두 입력을 정하면 #1~#5를 그대로 적용한다. #2·#4·#5는 설정 결함이고, 그 묶음의 J-P3를 판정하지 않고 멈춘다(개정 9 3.2 묶음 문구).
- 436.8 줄에 `head_only_declared` 필드가 있는지 원판 11.2 G-S에서 확인한다. 없으면 위 구성 정의로 읽는다는 사실을 판정서에 적는다.
- 결정 필요: **아니오**.

<!-- C-07 v5_resume_4368_rules_rev4.md:155 -->
### R4-C2. 정착 v2 블록의 단위·허용·표 목표 (rev3 R3-B6)

- **정의**:
  - 단위: 398.3 식에서 Δφ·Δθ(`d_attitude_deg`)는 rad로 바꿔 쓴다. 패드 좌표(`pad_xy_m`)는 mm로 바꿔 관입(mm)과 같은 단위로 쓴다. 식은 pen_mean,i [mm] = pen_inst,i [mm] + (y_i [mm] · Δφ [rad] − x_i [mm] · Δθ [rad])다.
  - `tolerances` 대조: 기록의 세 값(gap 1.0 mm, attitude min 0.005°, residual margin 0.002°)이 398.3의 값과 원판 7.6 비교 허용(10⁻⁹, 그 단위) 안에서 같아야 한다. 하나라도 다르면 S-11이다.
  - 표 목표 대조: 정착 표 파일의 형식은 규칙에 정의돼 있지 않다. 그래서 rev3 R3-B6의 "표 행 값과 같은지"는 다음 두 확인으로 바꾼다.
    1. `table_sha256`이 `table` 파일의 sha256과 같다.
    2. 경로 1 구현자가 기록 전용 필드 `settle_v2.inputs.table_gap_target_mm`(그 사례의 표 목표, 시작 틈 패드도 표 값)을 더한다(R4-D 표). `gap_target_source` = 표인 패드는 `gap_target_mm` = `table_gap_target_mm`이어야 한다.
  - 연구 D 시작 틈 패드의 "표 목표로도 계산"(rev3 R3-B7 공개)은 `table_gap_target_mm`로 한다.
  - 표 파일을 경로 2가 직접 읽어 값을 대조했으면 그 결과를 기록으로 적는다(판정 조건은 아님).
- 결정 필요: **아니오**.

<!-- C-08 v5_resume_4368_rules_rev4.md:54 -->
- J-P3: `hydraulics_record.extend_bound_check`. `breach_reads`(ext_moving, 개정 8 68행: 작용 명령 > 0인 판독의 초과 수)의 네 다리 합 = 0이면 통과, ≥ 1이면 H-7이다. 키가 없거나 null이면 개정 9 3.2 표로 처리한다. 블록의 `rule`이 ext_moving 정의와 같은지 G-S에서 확인한다.

<!-- C-09 v5_resume_4368_rules_rev6.md:164 -->
### R6-C3. 377 판정 분기와 `P3-8_preloc_loss` (rev5 R5-D1)

- 사실: 기존 G6 판정 함수(`r72_judge.py`)의 G6-7 처리에는 분기가 셋이다.
  1. `preloc_flag_ok` 참 → `P3-8_demoted`(377)
  2. `preloc_flag_ok` 거짓 ∧ G6-3 참 ∧ FAULT 없음 → `P3-8_preloc_loss`
  3. `preloc_flag_ok` 없음 → `P3-8_unchecked`
- 2번은 사용자 결정 **U-S9-G6c (가)**(명세 381절, 2026-10-28)다: "LOC 전(크롤러 하중 ≥ 0.01 W) 대각 하중 소실은 FLAG(`P3-8_preloc_loss`)다. … 377절 강등은 그대로다."
- **정의**: rev5 R5-D1이 377만 적은 것은 빠뜨림이다. 하네스 D-1 새 판과 Chrono 새 판(D-34)은 **2번 분기도 넣는다**. `d1_selection_rules.md` 11절 H-R-A·H-S-A·S-03·04의 G6 판정은 기존 기준 그대로(D-5)이고, 기존 G6 판정 함수가 이 분기를 가진다.
  - 분기 1·2에 해당하면 G6-7은 FLAG이고 실패가 아니다. 그 항목을 `d1.demoted_items`에 넣는다. `rule`은 377 또는 `U-S9-G6c`, `flag`는 그 이름이다.
  - 분기 3(`preloc_flag_ok` 없음)은 원판 9.3 결측으로 `판정 불가`다. 기존 함수의 `P3-8_unchecked` 꼬리표(실패 유지)는 쓰지 않는다.
  - 경로 2는 R5-D1 4대로 `d1.g6_preloc`과 G6-3·FAULT 기록으로 두 분기를 다시 계산해 대조한다. Chrono는 1 ms 계열로 다시 계산한다(D-34).
- 결정 필요: **아니오**(봉인된 사용자 결정 U-S9-G6c의 적용).

<!-- C-10 v5_resume_4368_rules_rev8.md:25 -->
## R8-1. T4h 없는 실행의 태그 재계산 대조 (rev7 R7-1a 보충, 사용자 결정 10)

### R8-1a. 대상

- r79 계열(H-6·H-7·H-8) 결과 항목 가운데 `t4h_file` 키가 없는 것, 그리고 격자(H-9) job 기록(`results[]` 항목) 전부다.
- `t4h_file`이 있는 실행은 rev7 R7-1a(T4h meta 대조)로 한다. 기록이 가리키는 T4h 파일을 찾지 못하면 S-2이고, 재계산으로 대신하지 않는다(기록이 있다고 한 쪽이 없으므로 R7-1a의 "한쪽에만").

### R8-1b. 입력 필드 (기록 사실, 2026-11-13 저장 기록에서 확인)

| 입력 | r79 결과 항목 | 격자 job 기록 | 읽기 |
|---|---|---|---|
| ③ | `hydraulic_options.extend_start_tracked` | `results[].hydraulic_options.extend_start_tracked` | 키가 있고 참 = ③ 켬. 블록이 있는데 키가 없음 = ③ 끔(`HydraulicOptions` 기록은 ③ 켬일 때만 이 키를 남긴다, `v5_options.py` 168~172행, 읽을 때도 없음 = 끔, 218행). `hydraulic_options` 블록이 없으면 재계산 불가 |
| ③ 대조 | `controller_settings["two_pressure.extend_start_rule"]`(점 이름 키 하나) | 없음 | 키가 있으면 값 `tracked_bound` ⇔ ③ 켬이어야 한다. 다르면 S-2. 키가 없으면 이 대조는 하지 않는다(dg3 기록에만 있다) |
| C2 실행 | `resume_k1.applicable` | `results[].resume_k1.applicable` | 참이어야 한다. 거짓이거나 없으면 재계산 불가 |
| LAS-b | `resume_k1.liftoff_approach_slow.settings.enable` | `results[].resume_k1.liftoff_approach_slow.settings.enable` | bool. 없으면 재계산 불가 |
| K1 관문 | `resume_k1.slope_clearance_margin.settings.flat_soil_margin_order_gate` | `results[].resume_k1.slope_clearance_margin.settings.flat_soil_margin_order_gate` | bool. 없으면 재계산 불가 |
| 대조 대상 | 최상위 `controller_tag` | `results[].controller_tag` | 키가 없으면 "태그 없음" |

- 격자 job의 각 run(`results[].runs[]`)도 자기 `resume_k1` 블록을 가진다(rev1 RV1-3.2 "격자 줄의 태그 확인은 각 run의 `resume_k1` 블록"). 각 run의 LAS-b·K1 두 값은 그 job 기록의 두 값과 같아야 한다. 다르면 S-2다. run의 블록이 없으면 재계산 불가다.
- `controller_settings`의 그 밖 키(`lift_stroke_guard.*`, `slope_clearance_margin.enable` 등)는 태그를 정하지 않으므로 재계산에 쓰지 않는다.

### R8-1c. 재계산 규칙 (봉인된 태그 정의)

1. 바탕: ③ 켬이면 `final_C4G2_P3`(v5 기준 개정 8 3.1 "③ revision 4 … 태그 `final_C4G2_P3`"). ③ 끔이면 바탕 없음(러너 태그 `final_C4G2`, v5 기록은 키를 남기지 않음, 개정 8 3.1 "기준 `final_C4G2`").
2. LAS-b 켬이면 `_LAS`를 붙인다. 바탕이 없으면 `final_C4G2_LAS`다(개정 11 1절 #1 `final_C4G2_LAS` = `final_C4G2` + LAS-b, #2 `final_C4G2_P3_LAS`).
3. K1 관문 켬이면 `_LAS` 다음에 `_K1`을 붙인다(`las_k1_rules_adopt.md` 9.2: "LAS-b 접미사 `_LAS` 다음에 순서 관문 접미사 `_K1`을 붙인다", `final_C4G2_LAS_K1`·`final_C4G2_P3_LAS_K1`).
4. `_TCL`(K-2 TOUCH 크리프 래치)은 만들지 않는다. 위 기록에 TCL 켬을 나타내는 필드가 없고, TCL은 원판 4.2 금지 토큰이다. 기록 태그에 `_TCL`이 있으면 재계산 태그와 달라 S-2가 되고, 4.2 확인(S-3)도 따로 걸린다.
5. 셋 다 끔이고 ③도 끔이면 재계산 태그는 "태그 없음"이다.

- 436.8 행에서 나오는 값: ③ 켬 + LAS-b + K1 = `final_C4G2_P3_LAS_K1`(H-6, H-8 VB, 격자 VB), ③ 끔 + LAS-b + K1 = `final_C4G2_LAS_K1`(H-7, H-8 V0). 원판 4.1·rev1 RV1-3.2의 기대 태그와 같다.
- 이 규칙은 코드의 `v5_options.controller_tag(options, config)`(T4h meta와 `c4e0ed9` 뒤 최상위 태그를 만드는 함수)와 같은 결과를 낸다. 정의의 원본은 위 봉인 문장이다.

### R8-1d. 대조와 멈춤

- 재계산 태그와 최상위 `controller_tag`가 같으면(둘 다 "태그 없음"인 경우 포함) 일치다.
- 다르거나 한쪽에만 있으면 그 묶음은 원판 8.2 S-2로 멈춘다(사용자 결정 10).
- **재계산 불가**(R8-1b의 "재계산 불가" 경우)도 S-2로 멈춘다. G-S에서는 원판 11.2의 키 있음 실패(S-11)로도 센다.
  - 근거: 태그 확인(원판 4.1)은 등급 항목이 아니라 묶음을 시작·판정하기 위한 멈춤 조건이다. 그래서 원판 9.3의 `판정 불가`(등급 항목의 결측)로 넘기지 않는다. 재계산 불가는 "기록 태그는 있는데 설정 쪽 값이 없음"이므로 rev7 R7-1a와 사용자 결정 10의 "한쪽에만 있으면 S-2"에 해당한다. 필요한 키는 모두 원판 4.2 기록 확인 키(`resume_k1.*`)와 v5 기록 칸이라 정상 실행에서는 빠지지 않는다.
- 대조는 경로 1 도구가 한다(G-S·기록 확인, rev7 R7-1a와 같은 곳). 대조 방법(T4h meta / 재계산), 대조한 수, 어긋난 수, 재계산 불가 수를 묶음마다 판정서 13절 3항에 적는다. `not_compared`로 남는 실행은 없어야 한다.

### R8-1e. 확인 사실 (저장 기록에 이 규칙을 적용, 2026-11-13, 이 작성자 계산)

| 기록 | 대조 방법 | 기록 태그 | 재계산 | 결과 |
|---|---|---|---|---|
| `b1ddeae` G-S 격자 job 1개(run 6개, LAS-b·K1 값 job과 같음) | 재계산 | `final_C4G2_P3` | `final_C4G2_P3_LAS_K1` | 다름(R7-1b의 기록 결함) |
| `b1ddeae` G-S H-8 seedext 1개(`t4h_file` 없음) | 재계산 | `final_C4G2_P3` | `final_C4G2_P3_LAS_K1` | 다름(같은 결함) |
| `c4e0ed9` 재실행 격자 job 1개(run 6개 같음) | 재계산 | `final_C4G2_P3_LAS_K1` | 같음 | 일치 |
| `c4e0ed9` 재실행 seedext·H-6·H-7 각 1개 | (T4h 있음, R7-1a) 참고로 재계산도 함 | `final_C4G2_P3_LAS_K1` / `final_C4G2_P3_LAS_K1` / `final_C4G2_LAS_K1` | 같음 | 일치. H-6·H-7은 `controller_settings` `two_pressure.extend_start_rule`(`tracked_bound` / `constant`)도 ③과 맞음 |

- 결정 필요: **아니오**(사용자 결정 10. 재계산 불가 처리는 R7-1a 문장의 적용).

<!-- C-11 v5_resume_4368_rules_rev8.md:76 -->
## R8-2. J-P3 적용 범위와 ③ 판별 (경로 2 메모 P-3)

- **정의**: J-P3은 ③ 켬 행에만 적용한다(rev3 R3-C8 "J-P3은 ③ 켬(`is_extend_start_tag`) 줄에만 적용", v5 기준 개정 8 3.2 "VB·LS 모든 실행"). ③ 판별은 원판 4.1대로 그 행의 태그로만 한다. Chrono 행의 태그는 `--expect-controller` 값이고 `c2_setup.expect_controller`의 확인이 참이어야 한다(원판 6절, rev1 RV1-10 a).
  - 태그가 ③ 켬이 아닌 행(V0·V0v·S6SEED 등)의 J-P3은 **해당 없음**이다. `controller_meta.two_pressure.settings.extend_start_rule` 키가 없어도 결측으로 세지 않는다.
  - 태그가 ③ 켬인 행은 `controller_meta.two_pressure.settings.extend_start_rule` = `tracked_bound`여야 한다. 키가 없으면 그 행의 J-P3은 `판정 불가`(원판 9.3)다. 다른 값이면 태그와 실행 제어기가 달라 S-2다.
- **③ 요청 기록과의 대조**(경로 2 메모 P-3의 두 필드): 행 argv의 `--extend-start-tracked` 유무와, 있으면 `v5_hydraulics.hydraulic_options.extend_start_tracked`(키 없음 = 끔, R8-1b와 같은 기록 규칙)는 태그의 ③ 판별과 같아야 한다. 다르면 S-2다. `v5_hydraulics` 블록이 없는 행(2026-11-13 G-S에서 V0·S6SEED 행)은 argv만 대조한다.
- 열린 루프 C-6·C-7(제어기 없음, 원판 4.1 "태그 검사 대상 아님")은 이 절의 대상이 아니다.
- 메모와 같은 점·다른 점: 메모는 argv와 `hydraulic_options` 둘 다 끔이면 해당 없음이라고 했다. 이 판은 판별을 태그로 하고 두 필드를 대조에 쓴다. 정상 행에서 두 읽기는 같은 답을 낸다. 둘이 어긋나는 행은 이 판에서 S-2로 멈춘다. ③을 요청한 행에 키가 없으면 판정 불가라는 메모의 문장은 그대로 들어 있다.
- 결정 필요: **아니오**(R3-C8·원판 4.1·9.3의 적용).

<!-- C-12a v5_resume_4368_rules_rev11.md:25 -->
- **정의**: 원판 4.2의 기록 확인(관문 요청·적용, `flat_soil_margin_order_gate`, `liftoff_approach_slow.settings`)의 기대값은 **그 줄 종류(묶음·설정·팔)의 기대 스위치**다. 원판 4.2 본문의 "프리셋 값"은 그 줄 종류의 기대 스위치가 프리셋일 때의 값이다.

<!-- C-12b v5_resume_4368_rules_rev11.md:29 -->
| 줄 종류 | 판별 입력 | LAS-b | K1 관문 | 근거 |
|---|---|---|---|---|
| H-0 R-0 | `t3.bundle` = `R-0`, `t3.las` = `off`, `t3.gate` = `off` | 끔 | 끔 | `las_targeted_rules_rev5.md` 2.2 R-0 행, rev7 R7-1c |
| H-0 R-0K | `t3.bundle` = `R-0K`, `t3.las` = `off`, `t3.gate` = `on` | 끔 | 켬 | 같은 표 R-0K 행 |
| H-0 T-3K | `t3.bundle` ∈ {`T-3a`, `T-3b`, `T-3c`}, `t3.las` = `on`, `t3.gate` = `on` | 켬(b0) | 켬 | 같은 표 T-3K 행 |
| Chrono C-4 끔 팔 | 원판 4.2 그대로(`c2_setup.las_off` = true, `--k1-order-gate on`) | 끔 | 켬 | 원판 4.1·4.2 |
| 그 밖 하네스 줄·Chrono 행 | (위에 들지 않음) | 켬(프리셋) | 켬(프리셋) | 원판 4.2 |

<!-- C-12c v5_resume_4368_rules_rev11.md:35 -->
- 대조할 값:
  - LAS-b 켬: `liftoff_approach_slow.settings` 9값이 프리셋 값(원판 4.2 그대로). LAS-b 끔: `settings.enable` = false만 대조한다(원판 4.2 C-4 끔 팔의 "꺼짐"과 같은 뜻).
  - 관문 켬: `k1_order_gate_effective` = true, `slope_clearance_margin.settings.flat_soil_margin_order_gate` = true. 관문 끔: 둘 다 false.
  - 관문 요청(`k1_order_gate_request`, Chrono `c2_setup.k1_order_gate`): 원판 4.2대로 `preset`(C-4 끔 팔은 `on`). 단 R-0·R-0K 줄은 기록만 한다. 이 두 묶음은 요청 인자가 아니라 프리셋 패치(`pre_las_preset_runner`·`las_t3_presets`)로 스위치를 정하기 때문이다(`las_targeted_rules_rev5.md` 2.2 "프리셋 패치 허용" 칸).

<!-- C-12d v5_resume_4368_rules_rev11.md:39 -->
- 판별 입력의 일관성: H-0 줄에서 `t3.bundle`과 `t3.las`·`t3.gate`의 짝이 위 표와 다르거나 셋 가운데 하나라도 없으면, 기대값을 정할 수 없는 기록 결함이다. 본 실행은 원판 8.2 S-3, G-S는 S-11이다.

<!-- C-13 v5_resume_4368_rules_rev12.md:29 -->
- **규칙 문장에서 바로 나오는 것**:
  - rev3 R3-C8의 로드 판독 입력은 "**그 줄의** T4h 기록"이다. rev7 R7-1a의 대조도 "**같은 실행**"의 T4h meta다. 두 문장 모두 그 실행 자신의 T4h만 입력으로 인정한다. 다른 실행 폴더의 같은 이름 파일은 그 줄의 기록이 아니다(이름이 겹치는 것은 정상이다, rev11 R11-2 근거).
  - 그래서 **찾는 곳**(R11-2 정의 1·2: 러너 관례 폴더 `<결과 파일 stem>_t4h/`·결과 옆 `t4h/`, 관례 폴더가 없을 때만 지정 1개, 그 밖은 입력 오류)과 **같은 이름 파일이 2개 이상 잡히면 그 줄의 기록을 정할 수 없다**는 것은 T4h를 읽는 모든 판정(R7-1a 태그 대조, R3-C8 J-P3 로드 판독, 그 밖 T4h를 입력으로 쓰는 판정)에 같게 적용한다. 이것은 R3-C8·R7-1a의 "그 줄"·"같은 실행"에서 나온다.

<!-- C-14 v5_resume_4368_rules_rev12.md:32 -->
- **새 판단이 필요했던 것(Q-R12-1, 사용자 결정 2026-11-13 = A)**: J-P3 로드 판독에서 줄이 `t4h_file`을 기록했는데 관례 폴더에서 그 파일을 찾지 못하거나 2개 이상 잡힐 때의 처리.
  - R3-C8은 "T4h 기록이 없는 줄은 실행 구성으로 정한다"고 했다. 이 문장이 "`t4h_file` 키가 없는 줄"만 뜻하는지, "기록한 파일을 찾지 못한 줄"까지 뜻하는지 정해져 있지 않다.
  - **정의(A, 사용자 결정 2026-11-13, 권고와 같음)**: T4h를 읽는 모든 판정에 R11-2 정의 3을 같게 쓴다.
    1. 줄에 `t4h_file` 키가 없으면 R3-C8대로 실행 구성으로 정한다(J-P3 로드 판독). R7-1a 태그 대조는 rev8 R8-1(재계산)로 한다.
    2. 줄이 `t4h_file`을 기록했는데 찾는 곳에서 그 파일이 0개 또는 2개 이상이면 **S-2**로 그 묶음을 멈춘다. 기록이 가리키는 그 실행의 T4h를 정할 수 없으므로, 구성 규칙으로 대신하지 않는다(rev8 R8-1a "재계산으로 대신하지 않는다"와 같은 이유).
  - 근거: 같은 이름 파일이 섞이는 위험은 태그 대조와 로드 판독에 똑같이 있다. 기록이 있는데 못 찾는 것은 기록 결함이고, "기록 없음"과 다르다. R3-C8의 "T4h 기록이 없는 줄"은 `t4h_file` 키가 없는 줄로 읽는다.

<!-- C-15 v5_resume_4368_rules_rev13.md:75 -->
## R13-3. 앵커 결정: 유지

- **정의**: P-1·P-2 비트 예측의 앵커를 다시 정하지 않는다. 앵커 파일 5개와 그 sha256, 고르는 줄, `run_v5.job_key` 대응, 키 수, "키마다 정확히 1줄"은 rev1 RV1-5 그대로다. 원판 10절 P-1·P-2의 예측 내용과 원판 8.2 S-7(어긋나면 판정 전에 멈추고 원인을 본다)도 그대로다.
- 근거: R13-2의 변경은 모두 세 가지 가운데 하나다. H-1 명령 경로 밖이거나, 경로 안에서 기록 전용이거나, H-1이 주지 않는 선택 인자이고 그 기본값이 `c6bb55b`의 연산을 그대로 남긴다. 그래서 `c6bb55b`에서 세운 예측(P-2: `hsh_report.md` "`c6bb55b`에서 456/456", P-1: 저장 앵커)이 같은 근거로 R에서도 선다.
- 이 판이 원판 A-5가 요구한 "앵커를 다시 정하는 개정"이고, 판단 결과는 "다시 정하지 않음"이다. A-5의 이 조건은 이 판 봉인으로 충족된다. 다만 R13-4의 확인(R의 `03_src`·`02_params`·`04_scripts`가 `a861981`과 같음)이 참일 때만이다.
- P-1·P-2가 어긋나면(S-7) 원인 확인은 R13-2 표의 경로 안 항목(#3~#16)부터 본다. 이 판은 그 순서를 권할 뿐 판정을 바꾸지 않는다.
- 결정 필요: **아니오**(코드 diff에서 바로 나오는 판단, 사용자 결정 2026-11-13 "rev13으로 처리").

<!-- C-16 v5_resume_4368_rules_rev1.md:164 -->
## RV1-12. 바뀐 줄 수 (S-15 대조값)

| 묶음 | 원판 | 이 판 | 이유 |
|---|---|---|---|
| H-10 | 462 | **440** | RV1-2 |
| H-8 | 3,106(파일 1개) | 3,106(파일 4개: 1,503 + 1,503 + 50 + 50) | RV1-3 |
| H-9 | 1,676(파일 1개) | 1,676(`h9_stage1.jsonl` 908 + 격자 `runs[]` 768) | RV1-3 |
| H-6·H-7 | 각 135 | 각 135(키 집합은 저장 dg3와 같음) | RV1-3 |
| 본 묶음 합 | 9,800 | **9,778** | RV1-2 |
| overlap 기준 실행 | (저장 재사용) | 1건, 줄 수에 세지 않음 | RV1-4 |

<!-- C-17 v5_resume_4368_rules_rev2.md:21 -->
## R2-1. `would_block` 참 ∧ `r4_due_without_gate` 거짓 (항목 1)

- 정의: `las_k1_rules.md` 63행에 따라 `would_block` = `r4_due_without_gate` ∧ (n_P ≤ n_S 또는 t_P·t_S 없음)이다. 그러므로 `would_block`이 참이면 `r4_due_without_gate`도 참이어야 한다.
- `decisions` 항목 가운데 `would_block` 참 ∧ `r4_due_without_gate` 거짓인 것은 **기록 모순**이다. 원판 7.2의 어느 분류에도 넣지 않는다.
  - 그 줄·행은 `판정 불가`다.
  - 그 묶음은 원판 8.2 **S-5**로 멈추고 묻는다(`applied` ∧ `would_block`과 같은 기록 모순 처리).
- 두 경로 모두 이 문장으로 처리한다. "분류 밖 → 멈춤"과 "판정 불가"는 이 판에서 하나가 된다: 그 줄은 `판정 불가`, 그 묶음은 S-5.
- 같은 정의로, `applied` 참 ∧ `r4_due_without_gate` 거짓도 기록 모순으로 S-5다(R4c30은 due일 때만 적용된다).

<!-- C-18 v5_resume_4368_rules_rev2.md:30 -->
## R2-2. `liftoff_approach_slow.start_s`가 없을 때 (항목 2)

하네스 줄과 Chrono 행에 같이 적용한다. 대상 블록은 하네스 줄이 `resume_k1.liftoff_approach_slow`, Chrono 행이 `controller_meta.liftoff_approach_slow`다.

| 기록 상태 | 원판 7.2의 읽기 |
|---|---|
| 블록이 있고 `start_s` 키가 있으며 값이 None | LAS-b 시작 안 함 |
| 블록이 있고(`settings`가 있음) `start_s` 키가 없음 | **LAS-b 시작 안 함**(LAS-b 상태가 생기지 않은 실행의 기록. 결측으로 보지 않는다) |
| 블록이 있고 `start_s`가 수 | LAS-b 작동 |
| 블록 자체가 없음 | `판정 불가`(원판 9.3 결측) |
| C-4 끔 팔(`--las-off`) | 'LAS 없음'(rev1 RV1-10 b). 블록이 없어도 결측이 아니다 |
| `resume_k1.applicable` 거짓(IND·IND_LAS) | 해당 없음(rev1 RV1-6) |

- "LAS-b 시작 안 함"은 원판 7.2 미작동 조건의 앞 절(`start_s` = None)을 만족하는 것으로 읽는다. `end_s`·`end_reason`이 없는 것도 같은 읽기다.

<!-- C-19 v5_resume_4368_rules_rev2.md:104 -->
## R2-7. 격자(r67·r69) 줄의 지면 계열 (항목 7)

격자 결과의 키(`screen|<오거>|<F_s>|level|<다리>`)에는 지면 토큰이 없다. 계열은 다음 식별 필드로 정한다(rev1 RV1-6의 계열 표 규칙에 더한다).

| 조건 | 계열 |
|---|---|
| 파일 `meta.spec` = `rev. 67 (G1 / G2 / G7 reduced screen)` ∧ 그 run의 `event`가 `G4`·`RE1bF`·`FS24` 가운데 하나 | **패치·처방 침하**(강체 바닥 축소 하네스에 처방 바닥 사건, 명세 342.1·342.2) |
| `meta.spec`이 위와 다르거나 없음, 또는 `event`가 없거나 위 셋 밖 | 분류 안 됨 → 균일 연약으로 다룬다(그 run의 K1 막힘은 **S-6**, rev1 RV1-6) |

- 계열은 run 단위(`results[].runs[]`)로 정한다. 같은 `results[]` 항목의 run들은 키를 공유하지만 `event`가 다를 수 있다.
- 두 경로 모두 이 표만 쓴다. 키 문자열에서 지면을 추측하지 않는다.
- 2026-11-13 저장 VB 격자 4파일의 식별 필드(값 아님)는 모두 첫 줄 조건을 만족했다(`meta.spec` 같음, `event` 셋 각 64 run/파일).

<!-- C-20 v5_resume_4368_rules_rev3.md:362 -->
### R3-F1. 하네스 본 묶음 합계 (경로 1 질문: 합계 불일치)

- 사실: 원판 5.1 둘째 글머리의 괄호 안 항(H-1 868 + H-3 2,228 + H-4 968 + H-5 14 + H-6·H-7 270 + H-8 3,106 + H-9 1,676 + H-10 462)을 더하면 **9,592**인데, 원판은 합을 9,800으로 적었다. rev1 RV1-2·RV1-12의 9,778도 같은 덧셈 오류를 이어받았다. 바른 값은 9,592 − 22 = **9,570**이다. 묶음별 값은 원판·rev1 표 그대로 맞고, 합만 208 틀렸다.
- **정의**:
  - 하네스 본 묶음 합은 **9,570줄**(rev1 기준, H-10 440)이다. 원판 5.1의 9,800, rev1 RV1-2의 9,778, RV1-12 표의 "본 묶음 합" 칸은 이 값으로 읽는다. 원판 12.2 비용 표의 "360 + 9,800"도 "360 + 9,570"으로 읽는다(비용 값은 실측 단가에서 왔으므로 바꾸지 않는다).
  - **S-15(원판 8.2)의 대조값은 묶음별 줄 수뿐이다.** 합은 묶음별 값의 덧셈 기록이고 멈춤 대조에 쓰지 않는다. 묶음별 값은 원판 5.1 표와 rev1 RV1-12 표 그대로다.
- 결정 필요: **아니오**(산술 정정, 묶음 범위·문턱 불변).

<!-- C-21 v5_resume_4368_rules_rev3.md:370 -->
### R3-F2. G1 단독 바탕의 지면 계열 (경로 1 질문)

- 사실: 원판 7.2 "K1 막힘 — 균일 연약 지면 계열" 행의 조건 문장은 셋으로 나뉜다. "계열이 H-S-0·H-S-1"(D-1, G1 균일 포함), "U-3·잡음의 균일 J1·J2·S1 바탕(패치·처방 침하 없음)", "Chrono 균일 SCM 행"(토양 세트를 가리지 않음)이다. D-1·Chrono 부분은 G1 균일을 넣고, U-3·잡음 부분만 토양 이름을 셋으로 적었다.
- **정의**: 계열은 토양 세트 이름이 아니라 **지면 구조**로 정한다. 바탕 전체가 SCM 토양(G1·J1·J2·S1 어느 세트든)이고 패치·처방 침하가 없으면 균일 계열이다. G1 단독 바탕도 균일 계열이며, 그 K1 막힘은 S-6이다. rev1 RV1-6의 계열 표("바탕이 연약 토양이고 패치·처방 침하가 없음")의 "연약 토양"은 SCM 토양 세트 넷을 모두 뜻한다.
- 근거: 원판 7.2의 같은 행이 D-1에서 H-S-0(G1 균일 포함)을, Chrono에서 "균일 SCM 행"을 모두 균일 계열에 넣는다. U-3·잡음 문장의 "균일"과 "(패치·처방 침하 없음)"이 구조 조건이고, J1·J2·S1은 그 바탕들의 예시 목록으로 읽는다. 멈추고 묻는 쪽(S-6)이 보수 쪽이다. 잘못 넣으면 질문 한 번이 늘고, 잘못 빼면 균일 지면 막힘이 기록 없이 지나간다.
- 결정 필요: **아니오**(보수 쪽 읽기. 다르게 정하려면 사용자 결정이 필요하다).

<!-- C-22 v5_resume_4368_rules_rev9.md:98 -->
## R9-7. LAS-b 끔 + K1 켬 태그와 R8-1c 규칙 5 (rev8 R8-1c 고쳐 씀)

- rev8 R8-1c 규칙 3을 다음으로 고쳐 쓴다: K1 관문 켬이면 태그 끝에 `_K1`을 붙인다. LAS-b 켬이면 `_LAS` 다음이다. ③도 LAS-b도 끔이면 `final_C4G2_K1`이다(③ 켬 + LAS-b 끔이면 `final_C4G2_P3_K1`).
  - 근거: 원판 4.1 표의 C-4 끔 팔 태그(V0 `final_C4G2_K1`, VB `final_C4G2_P3_K1`), `las_targeted_rules_rev5.md` 2.2 R-0K 기대 태그(`final_C4G2_K1` / `final_C4G2_P3_K1`), `las_k1_rules_adopt.md` 9.2. 코드의 `with_order_gate_tag(None)`도 `final_C4G2_K1`을 낸다.
- rev8 R8-1c 규칙 5를 다음으로 고쳐 쓴다: **③·LAS-b·K1 관문 세 가지가 모두 끔**이면 재계산 태그는 "태그 없음"이다. `_TCL`은 규칙 4대로 만들지 않으므로 이 셋에 들지 않는다.
- 결정 필요: **아니오**(봉인된 태그 문장의 인용).

<!-- C-23a v5_resume_4368_rules_rev11.md:48 -->
  1. 한 결과 파일의 T4h는 그 결과 파일의 **러너 관례 폴더**에서만 찾는다. 관례 폴더는 둘이다: `<결과 파일 stem>_t4h/`(run_v5·r79 계열, rev1 RV1-3.3 이름 `h6_dg3_v4on_t4h/` 등), 결과 파일과 같은 폴더의 `t4h/`(`las_t3` 계열).

<!-- C-23b v5_resume_4368_rules_rev11.md:49 -->
  2. 관례 폴더가 하나도 없을 때만 다른 폴더를 **1개** 지정할 수 있다. 관례 폴더가 있는데 다른 폴더를 지정하거나, 2개 이상 지정하면 입력 오류다(도구 종료 2, 그 묶음 판정 안 함, 원판 8.2 S-11).

<!-- C-23c v5_resume_4368_rules_rev11.md:50 -->
  3. 찾는 곳 전체(관례 폴더 둘, 또는 지정 폴더 1개)에서 기록된 `t4h_file` 이름의 파일이 정확히 하나여야 한다. 둘 이상이면 S-2, 없으면 S-2(rev8 R8-1a)다.

<!-- C-24 v5_resume_4368_rules_rev1.md:65 -->
### RV1-3.3 출력 이름 (원판 4.3 표의 해당 칸을 바꾼다)

| 묶음 | 출력(`06_analysis/03_hydraulic/coupled/v5/resume_k1/` 아래) |
|---|---|
| H-6 | `h6_dg3_v4on.json`(+ `.partial.jsonl`), T4h `h6_dg3_v4on_t4h/` |
| H-7 | `h7_dg3_off.json`(+ `.partial.jsonl`), T4h `h7_dg3_off_t4h/` |
| H-8 | `h8_noise_VB.json`, `h8_noise_V0.json`, `h8_seedext_VB.json`, `h8_seedext_V0.json`(각 + `.partial.jsonl`) |
| H-9 | main·pressure_only는 원판대로 `h9_stage1.jsonl`. 격자는 `h9_grid/grid_r67_main.json`, `h9_grid/grid_r67_top.json`, `h9_grid/grid_r69_bottom.json`, `h9_grid/grid_r69_top.json` |

- 각 출력에 `.identity.json`이 동반한다(RV1-3.1).
- 이어쓰기는 러너의 `.partial.jsonl` 규칙대로이고, 저장 기준선 파일(`v5/dg3/`, `v5/noise_*`, `v5/seedext/`, `v5/grid_vb/`)에는 쓰지 않는다(원판 A-9).

<!-- P2-01 v5_resume_4368_rules_rev16.md:39 -->
  1. 하네스 묶음 H-1~H-10의 첫 두 경로 판정 출력(경로 1 출력과 경로 2의 A·B판)은 **기록으로만** 둔다. S-13 경과로 판정서에 싣고, 등급·사전 예측 대조·한계 문장의 근거로 쓰지 않는다(rev14 R14-2와 같은 처리).

<!-- P2-02 v5_resume_4368_rules_rev16.md:40 -->
  2. 시뮬레이션은 다시 돌리지 않는다. R2 실행 기록(`resume_k1/`, `v5_rerun/las_k1/`)을 그대로 두고 R4 도구(R16-12)로 두 경로를 다시 판정한다. `--git-at-start`에는 R2를 준다(rev15 R15-1 2).

<!-- P2-03 v5_resume_4368_rules_rev16.md:41 -->
  3. 재판정에서 등급이 다시 갈리면 원판 S-13 그대로 멈추고 묻는다.

<!-- P2-04 v5_resume_4368_rules_rev16.md:48 -->
| # | 묶음 | 줄·행 수 | 지위 | 정의 |
|---|---|---|---|---|
| H-11 | U-3·U-6 G-3 짝(V0 설정 = 옵션 없음) | 실행 10(비교 짝 8) | 관문(u3 원판 7절 G-3) | R16-8 |
| H-12 | u3 g8 G-6 3키의 T4h 기록 실행 | 3(대체 경로로 가면 대체 3, R16-9 6) | 기록(rev1 #5) | R16-9 |
| C-9 | S-6 확인: Chrono G1 균일 관문 켬/끔 짝 | 2 | 기록 | R16-11 1 |
| C-10 | G-5 확인: g6 강체 + S1 앞 패드, VB/V0 × FL·FR | 4 | 기록 | R16-11 2 |
| C-11 | seedext 확인: J2 균일 상단 F_s 0, VB/V0 | 2 | 기록 | R16-11 3 |

<!-- P2-05 v5_resume_4368_rules_rev16.md:54 -->
- **[정의]** S-15(원판 5.1·5.2)의 대조값에 위 다섯 줄을 더한다. 기존 묶음의 묶음별 값(rev3 R3-F1, 하네스 9,570줄)은 그대로다. S-15는 묶음별 값만 대조한다.

<!-- P2-06 v5_resume_4368_rules_rev16.md:55 -->
- **[정의]** 원판 8.1의 기록 묶음(H-7, IND_LAS, C-4 기록 항목, C-6·C-7, C-8)에 H-12, C-9, C-10, C-11을 더한다. 이 묶음들은 `기록 완료` / `기록 불완전`이다. H-11은 관문이므로 등급이 없다. H-11이 거짓이면 H-3·H-4를 판정하지 않고 멈춘다(u3 원판 7절).

<!-- P2-07 v5_resume_4368_rules_rev16.md:56 -->
- **[정의]** 원판 4.2의 `--k1-order-gate` 금지는 C-9 끔 팔에는 적용하지 않는다. 그 팔은 `--k1-order-gate off`가 정의다. 기대값은 R16-11 1이다. 다른 새 행에는 금지가 그대로다.

<!-- P2-08 v5_resume_4368_rules_rev16.md:57 -->
- **[정의] 원판 11.1·11.2의 적용**(사용자 결정 54의 4: G-S 면제 + 대체 점검)
  - 11.1 옵션 × 단계 겹침 표: 새 묶음 H-11·H-12·C-9~C-11의 행을 **넣는다**. python-expert(하네스)·cad-expert(Chrono)가 행 종류 × (프리셋·래퍼·argv·env) 칸을 채우고 실행 전 감사가 대조한다.
  - 11.2 G-S 건조 실행: 새 묶음은 **면제**한다. 대신 다음을 한다.
    - H-11: 각 스크립트의 인자 파싱 dry 점검. 실물은 `<OUT>\H-11\h11_key_selection.json`(6실행, 키 10, R16-8 표와 일치)이다.
    - H-12: 설치 점검 `<OUT>\H-12\h12_check_install.json`과 첫 T4h 파일의 `--check-recorded` 확인(R16-9 4)
    - C-9~C-11: 행마다 실행 전·뒤 정체성 점검(R16-11b 1, R16-14 3)
    - 11.1 표의 실물은 `<OUT>\_tools\harness\table_11_1.md`다.
  - 면제 사실과 대체 점검 결과는 판정서에 공개한다.

<!-- P2-09 v5_resume_4368_rules_rev16.md:69 -->
- **[정의]** ABL 줄의 원판 4.2 기대값은 프리셋 값이다. 다만 `liftoff_approach_slow.settings.require_soil_response`는 `False`다. 그 밖의 8값, K1 관문(`flat_soil_margin_order_gate` = true), `k1_order_gate_effective` = true는 프리셋 그대로다. `slope_clearance_margin.settings.flat_soil_margin_m` = 0은 ABL 정의값이다(명세 429.11, 같은 함수). 이 둘 밖의 값이 다르면 S-3이다.
  - 줄 종류 판별은 줄의 `controller` 필드(`ABL`)와 태그(`ABL_LAS_K1`)가 함께 맞을 때만 한다. 하나만 맞으면 판별 입력 결함이고 S-3이다(rev11 R11-1과 같은 꼴).
  - C2·IND·IND_LAS 줄은 앞 판 그대로다.

<!-- P2-10 v5_resume_4368_rules_rev16.md:77 -->
- **[정의]**(R8-1b ③ 칸의 보완): r79 결과 항목의 `v5_setting`이 `V0`이면 `hydraulic_options` 블록이 없는 것은 ③ 끔이다. V0은 "v5 플랜트 옵션 모두 끔"이다(u3 원판 1절 V0 행, v5 기준 8절). 그 밖의 재계산 입력(`resume_k1.applicable`, LAS-b `enable`, K1 관문)은 R8-1b 그대로 있어야 한다.
  - `v5_setting`이 없거나 V0가 아니면서 블록이 없으면 앞 판 그대로 재계산 불가이고 S-2다.
  - 재계산 태그는 R8-1c대로 정하고 최상위 태그와 같아야 한다. 다르면 S-2다.

<!-- P2-11 v5_resume_4368_rules_rev16.md:86 -->
  1. 원판 7.2 미작동 행의 "10절 비트 예측(P-1·P-2) 앵커 또는 저장 행 해시"에서 앵커는 rev1 RV1-5의 P-1·P-2 앵커 파일뿐이다(rev13 R13-3). rev1 RV1-3.2의 키 원본(`v5/dg3/dg3_v4_on.json`, `v5/noise_{v0,vb}/*`, `v5/seedext/*`)은 앵커가 아니다. 그래서 그 파일과 해시가 달라도 S-5가 아니다. rev13 R13-2 #19("H-8에는 P-1·P-2 앵커가 없다")와 같은 읽기다.

<!-- P2-12 v5_resume_4368_rules_rev16.md:87 -->
  2. 키 원본과의 대조는 **기록**("미작동 확인", 원판 5.5 문구)으로 두 경로가 함께 낸다.
     - 새 줄의 최상위 `commands_sha256`을 키 원본 같은 키 줄의 `base.commands_sha256`과 비교한다. 키 원본에는 최상위 `commands_sha256`이 없다.
     - H-8 VB 잡음에서 dg3가 대체한 키(L3 134 + L2 1, rev1 RV1-3.2)는 `v5/noise_vb` 대신 `v5/dg3/dg3_v4_on.json`과 비교한다. 그 키의 키 원본은 ③ 끔 실행이라서다.
     - 저장 줄에 해시 필드가 없으면 "저장 해시 없음"으로 센다.
     - 판정서에는 묶음별 같음·다름·없음 수를 적는다. 다름은 python-expert에 원인 확인을 넘긴다(공개, 멈춤 아님).

<!-- P2-13 v5_resume_4368_rules_rev16.md:102 -->
  1. rev3 R3-C7의 "n_late"는 하네스 줄에서 `lock_window_alignment.n_late_fallback_by_leg`(실제 대체 다리, `fallback_legs`의 다리)다. 실제 대체 다리 n_late > 0의 멈춤(H-7, LS는 L-e)은 이 값으로 본다. 대체 다리가 있는 줄에서 이 키가 없거나 None이면 앞 판 그대로 판정 불가다.

<!-- P2-14 v5_resume_4368_rules_rev16.md:103 -->
  2. J11 멈춤의 적용 설정은 VB, LS1~LS4, item8(VB), overlap(VB)이다. V0~V8·L1·L2와 pressure_only의 J11 값은 기록이다(v5 기준 8절, 1단계 판정서 2절 표).

<!-- P2-15 v5_resume_4368_rules_rev16.md:109 -->
- **[정의]** H-9 격자 VB 768 run 각각에 rev3 R3-C8·rev4 R4-A2·rev8 R8-2의 J-P3을 적용한다. 입력은 run의 `hydraulics_record.extend_bound_check`(`breach_reads`, ext_moving)다. 경로 1은 자기 하네스 도구에 격자 등급을 넣는다. 경로 2는 앞 판 그대로다. 두 경로 모두 run 단위 위반 목록(격자 파일, `results[]`·`runs[]` 위치, 다리, 판독 수, 최소 간격 [bar], 첫 위반 시각 [s])을 낸다.

<!-- P2-16 v5_resume_4368_rules_rev16.md:115 -->
- **[정의] 비교 대상**(u3 rev2 #11을 고쳐 씀, 사용자 결정 54의 1): G-3은 "V0 설정이 옵션 없음과 같다"는 검사다. rev2 #11의 비교 대상 "같은 커밋에서 옵션 없이 돌린 LAS 태그 출력"을 "**R2에서 `--v5-setting V0`으로 돈 출력**(H-3의 V0 출력, U-6은 R16-8 실행 표의 V0 팔)"으로 고쳐 쓴다. 옵션 없는 실행은 R2에서 새로 돈다.

<!-- P2-17 v5_resume_4368_rules_rev16.md:116 -->
- **[정의] 옵션 없음**: 기준은 H-3·H-4의 R2 실행 argv와 Env(`run_b9f5707/run_harness.ps1` 26~47행)다.
  - argv에서 `--v5-setting <설정>`, `--reuse-d1 <파일>`, `--ids-from <파일>`, `--pad <패드>`를 빼고 아래 표의 키 좁히기 인자로 대신한다. 출력 경로는 `<OUT>\H-11\` 아래로 바꾼다.
  - **작업자 수와 affinity**: 작업자 수와 affinity는 명령 해시에 영향이 없으므로 R2와 다를 수 있다(작업마다 spawn, 작업자당 1스레드). 해시 같음 관문(아래)이 이를 확인한다. 이번 값은 배치표에 따른다: 하네스 전체 `--workers 2`·`--affinity 0x0F000000`(E 24–27), r72는 위치 인자 `2`와 env `R72_AFFINITY=0x0F000000`(R2는 workers 8, 마스크 `0x00FF0000`).
  - `s9_soil_slope.py`만 2키 키 파일 `<OUT>\_tools\harness\h11_D_keys.json`(`H8|rigid|B|top|flat`, `H8|G1|B|top|flat|FL:g20`)을 `--ids-from <그 파일> --pad B`로 넘긴다. 이 두 인자는 키 선택이고 v5 플랜트 옵션이 아니다. 키 파일과 그 sha256을 판정서에 적는다.
  - 준비물(`<OUT>\_tools\harness\`)의 `h11_h12_check.py`는 기계 점검(파일·키 수·정체성 기록 유무)만 하는 도구다. G-3 관문 판정은 R4의 두 경로 도구가 한다.
  - **env**는 R2 `run_harness.ps1`의 해당 단계 Env에서 두 곳만 다르다: `R72_FILTER`를 더하고, `R72_AFFINITY`는 위 작업자·affinity 글머리대로 `0x00FF0000` → `0x0F000000`이다. R2 값: `u3_p3b_V0`·`u3_g8_V0`·`u3_D_V0` = `@{}`, `u3_C_V0` = `R72_SET=x426`, `R72_PATH=per_leg`, `S9_SETTLE_HOOK=p0`, `R72_AFFINITY=0x00FF0000`, `u6_main_VB` = `R72_PATH=per_leg`(b5 두 팔 모두). 실제 argv·env와 R2의 차이는 사이드카 `<OUT>\H-11\h11_argv_env_vs_R2.json`에 남긴다.
  - 인터프리터는 dynamics-dev `python.exe` 직접 호출이다(`run_harness.ps1`과 같다).

<!-- P2-18 v5_resume_4368_rules_rev16.md:123 -->
- **[정의] 키 좁히기와 비교 필드**

<!-- P2-19 v5_resume_4368_rules_rev16.md:127 -->
| 스크립트 | 키 좁히기 | 비교 필드 |
|---|---|---|
| `s9_slope_fix_candidates.py` | `--ids "<키1>;<키2>"`(`;` 구분) | `records[].hash`(16자리 hex, g8은 r69 `cmd_sha256`) |
| `r72_g6_screen.py` | env `R72_FILTER=g6\|G1+J1@FL\|top\|Fs8,g6r\|rigid+J1@FL\|top\|Fs8` | `results[].commands_sha256` |
| `s9_soil_slope.py --groups H8` | `--ids-from <OUT>\_tools\harness\h11_D_keys.json --pad B` | `results[].run.commands_sha256` |
| `b5_baseline_compare.py --cases A1-rigid,A1-J1 --controllers C2` | `--cases` | `records[].commands_sha256`(`controller` == `C2`) |

<!-- P2-20 v5_resume_4368_rules_rev16.md:132 -->
- **[정의] 실행 10건, 비교 짝 8쌍**

<!-- P2-21 v5_resume_4368_rules_rev16.md:136 -->
| 스크립트 | 키(묶음, id) | 새 실행 | 비교 대상 |
|---|---|---|---|
| `s9_slope_fix_candidates.py` | (p3b, `base\|G1\|B\|top\|Fs0`), (g8, `slope\|edge\|top\|4.0\|ref\|none\|0\|proj`) | 옵션 없음 2 | `las_k1/u3_p3b_V0.json`, `u3_g8_V0.json` 같은 id |
| `r72_g6_screen.py` | `g6\|G1+J1@FL\|top\|Fs8`, `g6r\|rigid+J1@FL\|top\|Fs8` | 옵션 없음 2 | `las_k1/u3_C_V0.json` 같은 key |
| `s9_soil_slope.py --groups H8` | `H8\|rigid\|B\|top\|flat`, `H8\|G1\|B\|top\|flat\|FL:g20` | 옵션 없음 2 | `las_k1/u3_D_V0.json` 같은 id |
| `b5_baseline_compare.py` | `A1-rigid`, `A1-J1`(main) | 옵션 없음 2 + `--v5-setting V0` 2 | 같은 키의 두 팔끼리 |

<!-- P2-22 v5_resume_4368_rules_rev16.md:141 -->
- **[정의] 수 검사**: 도구는 위 표의 8키를 열거한다. 키마다 옵션 없는 출력에 정확히 1줄, 비교 대상 출력에 정확히 1줄이 있어야 한다. 0줄이거나 2줄 이상(중복 줄)이면 그 짝은 거짓이다.

<!-- P2-23 v5_resume_4368_rules_rev16.md:142 -->
- **[정의] 관문**: 8쌍 모두 같은 필드의 해시가 같으면 G-3 참이다. 하나라도 다르거나 수 검사가 거짓이면 G-3 거짓이고, H-3·H-4를 판정하지 않고 멈춘다(u3 원판 7절). 판정은 두 경로가 따로 낸다(사용자 결정 54의 4).

<!-- P2-24 v5_resume_4368_rules_rev16.md:143 -->
- **[정의] 커밋 정체성**: 옵션 없는 출력에는 `v5` 블록과 커밋 기록이 없다(`file_meta` = `{}`). 그래서 실행마다 `04_scripts/04_hydraulic/coupled/resume_k1_identity.py <out> --moment start` / `--moment end`로 감싸고, 그 기록의 커밋이 R2이고 clean이어야 한다. 다르면 원판 8.2 S-12다.

<!-- P2-25 v5_resume_4368_rules_rev16.md:144 -->
- **[정의] 출력**: `<OUT>\H-11\`(R16-14 4). 부산물(`_compare.csv`·`_cases.csv`·`_kstar.csv`)도 함께 둔다.

<!-- P2-26 v5_resume_4368_rules_rev16.md:194 -->
2. **경로 2**(경로 2 작성자)
   - (a) settle_v2: `residual_deg`·`attitude_error_deg`는 축별 [roll, pitch] 목록이다. 명세 398.3을 축마다 적용하고, `attitude_tol_deg`(축별)와 `attitude_ok`를 `result`의 같은 이름 값과 K-10 꼴로 대조한다.
   - (b) r72 계열(g6, 연구 C)의 등급: 기록의 `verdict`·`pass`를 그대로 쓰지 않는다. `gates`, `preloc_flag_ok`, G6-3, FAULT 기록에 rev6 R6-C3의 세 분기를 적용한다: `preloc_flag_ok` 참이면 `P3-8_demoted`(377), `preloc_flag_ok` 거짓 ∧ G6-3 참 ∧ FAULT 없음이면 `P3-8_preloc_loss`(U-S9-G6c), `preloc_flag_ok` 없음이면 판정 불가. 그다음 424.11.2·419.8·U-S9-G6d를 적용한다(u3 원판 4절 "같은 판정 함수").
   - (c) u6 키 계열 분류: u6 키(예: `G|g6|G1+J1@FL|top|Fs0|C2`)는 안쪽 키의 지면 토큰으로 나눈다. `+<토양>@<다리>`는 패치 계열이고, 토양 토큰만 있으면 균일 계열이다. 안쪽 키에 지면 토큰이 없을 때만 미분류(rev1 RV1-6, 균일로 다룸)다.
   - (d) S-5·저장 해시: R16-5 [정의].
   - (e) J11: R16-6 [정의].
   - (f) 봉인 확인 목록에 rev13~rev16 추가(R16-13).
   - (g) C-9~C-11 기록 항목과 정체성(R16-11 행 이름 표·각 행의 기록 항목, R16-11b 1, R16-11b 2의 입력 파일 목록, R16-14 4의 출력 위치). 새 파일 `path2/p2_x16.py`.
   - (h) H-11 읽기(사용자 결정 54의 4): R16-8 [정의] 글머리(비교 대상, 키 좁히기·비교 필드 표, 실행·짝 표, 수 검사, 관문, 커밋 정체성, 출력)로 G-3 참거짓을 따로 낸다.

<!-- P2-27 v5_resume_4368_rules_rev16.md:203 -->
3. **경로 2에 넘기는 글머리**(원판 9.2, 사용자 결정 53·54의 1·55의 1). 아래 표의 글머리만 준다. 경로 2 지시문에는 "rev16의 다른 절·글머리는 열지 않는다"를 넣고, 경로 2 판정서의 9.2 읽은 것 목록으로 확인한다. 경로 1의 코드·출력과 이 작성자의 검토 메모는 주지 않는다.
   - 경로 2 작성자는 S4에서 갈라진 브랜치에서 일하므로 rev16 전문 파일에 기술적으로 접근할 수 있다(사용자 결정 55의 1). 접근을 막지 않고 위 지시와 읽은 것 목록 확인으로 막는다. 판정서 한계 절에 그대로 적는다: "경로 2 작성자의 rev16 파일 접근은 기술적으로 막지 않았다. 다른 절을 열지 않는다는 지시와 경로 2 판정서의 읽은 것 목록으로 확인했다."

<!-- P2-28 v5_resume_4368_rules_rev16.md:208 -->
| 절 | 넘기는 글머리 | 넘기지 않는 글머리 |
|---|---|---|
| R16-1 | [정의] 1~3 | – |
| R16-2 | 표, [정의] 넷(S-15, 기록 묶음, `--k1-order-gate` 예외, 11.1·11.2 적용) | – |
| R16-3 | [정의] | [사실] |
| R16-4 | [정의] | [사실], [참고] |
| R16-5 | [정의] 1·2 | [사실] 공개, [참고] |
| R16-6 | [정의] 1·2 | [사실], [참고] |
| R16-7 | [정의] | – |
| R16-8 | [정의] 전부(비교 대상, 옵션 없음, 키 좁히기·비교 필드 표, 실행·짝 표, 수 검사, 관문, 커밋 정체성, 출력) | [사실], [참고] 둘 |
| R16-10 | 2 (a)~(h)와 이 3 | 1(경로 1 목록) |
| R16-11 | 공통 조건 [정의], 행 이름 표, 1의 끔 팔 기대값(S-2 판 섞임 예외 포함), 1의 P-18 읽기 전제, 각 행의 "기록 항목" 글머리 | 각 행의 바탕 행·하네스 근거·사전 예측·읽기, 격자·시간 근거 |
| R16-11b | 1, 2 | – |
| R16-14 | 4(출력 위치) | 그 밖 |

<!-- P2-29 v5_resume_4368_rules_rev16.md:221 -->
   - 이 판의 결함 목록이 두 경로 출력을 본 뒤에 정리된 것이라는 사실(R16-0 6)은 판정서 한계 절에 그대로 적는다: "R4 두 경로 도구의 수정 항목은 메인 세션과 도메인 검토가 첫 두 경로 출력을 대조해 정리했다. 그래서 재판정의 두 경로는 수정 항목의 선택에서 독립이 아니다. 각 수정의 구현과 재판정 값은 경로마다 따로 만들었다."

<!-- P2-30 v5_resume_4368_rules_rev16.md:226 -->
- **[정의] 공통 조건**
  - 엔진은 SCM이다(`run_S9.py level`). 원판 6절 SCM 정체성(`--threads 4`, `OMP_WAIT_POLICY=PASSIVE`, P코어, 볼록 껍질 훅 fast, `MIXED_HULL_MODE` 없음)을 지키고, 직접 실행 행의 대체 키는 R16-11b 1이다. 어긋나면 S-4다.
  - 공통 꼬리: `--pad-variant dwg_rear250 --level top --settle-dashpot zrp --threads 4 --pressure-grade normal --seed 20261026`. 아래 표의 `T`가 이 꼬리다.
  - V0 = `--expect-controller final_C4G2_LAS_K1`(v5 인자 없음). VB = `--expect-controller final_C4G2_P3_LAS_K1` + VB 인자 `--flow-eta-v 0.85 --flow-dp-comp-bar 10 --flow-dp-unload-bar 20 --flow-width-bar 1 --flow-law priority --valve-tau-s 0.1 --rod-release-force --lock-overlap-ratio 0.02 --lock-closing-delay-s 0.05 --lock-window-follows-plant --extend-start-tracked`(= R2 `s9_batch.v5_vb_argv()`, C-5 VB 행과 같음).
  - 실행 방식: 직접 실행(`run_S9.py level … --case <행 이름> --out-root <OUT>\<묶음>\`). 정체성은 R16-11b 1, 배치는 R16-14 5다.
  - 모두 기록 행이다. 원판 8.1 등급을 만들지 않는다(R16-11a).

<!-- P2-31 v5_resume_4368_rules_rev16.md:232 -->
- **[정의] 행 이름과 argv(글자 그대로)**

<!-- P2-32 v5_resume_4368_rules_rev16.md:236 -->
| # | 행 이름(`--case`) | argv(`run_S9.py` 뒤, `T` = 공통 꼬리) |
|---|---|---|
| 1 | `R4368X_G1_B_top_Fs4_V0_gateon` | `level --soil G1 T --fs-kN 4 --grid 0.02 --crawler-grid 0.04 --duration 120 --imu-grade ideal --expect-controller final_C4G2_LAS_K1 --approved --case R4368X_G1_B_top_Fs4_V0_gateon` |
| 2 | `R4368X_G1_B_top_Fs4_V0_gateoff` | `level --soil G1 T --fs-kN 4 --grid 0.02 --crawler-grid 0.04 --duration 120 --imu-grade ideal --k1-order-gate off --expect-controller final_C4G2_LAS --approved --case R4368X_G1_B_top_Fs4_V0_gateoff` |
| 3 | `R4368X_rigidS1FL_B_top_Fs4_V0` | `level --soil S1 --rigid-base FL T --fs-kN 4 --grid 0.02 --duration 160 --imu-grade ideal --expect-controller final_C4G2_LAS_K1 --approved --note "model-limit stress case: S1 patch under a front pad on a rigid base, outside the Bekker validity range (436.8 rev16 C-10)" --case R4368X_rigidS1FL_B_top_Fs4_V0` |
| 4 | `R4368X_rigidS1FL_B_top_Fs4_VB` | 3과 같고 `--expect-controller final_C4G2_P3_LAS_K1` + VB 인자, `--case R4368X_rigidS1FL_B_top_Fs4_VB` |
| 5 | `R4368X_rigidS1FR_B_top_Fs4_V0` | 3과 같고 `--rigid-base FR`, `--case R4368X_rigidS1FR_B_top_Fs4_V0` |
| 6 | `R4368X_rigidS1FR_B_top_Fs4_VB` | 5와 같고 `--expect-controller final_C4G2_P3_LAS_K1` + VB 인자, `--case R4368X_rigidS1FR_B_top_Fs4_VB` |
| 7 | `R4368X_J2_B_top_Fs0_L2_V0` | `level --soil J2 T --fs-kN 0 --grid 0.01 --crawler-grid 0.04 --duration 120 --imu-grade normal_zeroed --expect-controller final_C4G2_LAS_K1 --approved --case R4368X_J2_B_top_Fs0_L2_V0` |
| 8 | `R4368X_J2_B_top_Fs0_L2_VB` | 7과 같고 `--expect-controller final_C4G2_P3_LAS_K1` + VB 인자, `--case R4368X_J2_B_top_Fs0_L2_VB` |

<!-- P2-33 v5_resume_4368_rules_rev16.md:245 -->
  - 묶음: C-9 = 1·2, C-10 = 3~6, C-11 = 7·8. 출력은 `<OUT>\C-9\`, `<OUT>\C-10\`, `<OUT>\C-11\`(R16-14 4).

<!-- P2-34 v5_resume_4368_rules_rev16.md:248 -->
1. **C-9 (S-6 확인, 사용자 결정 2)**: G1 균일, 관문 켬/끔 단일 변수 짝, V0

<!-- P2-35 v5_resume_4368_rules_rev16.md:249 -->
   - **[정의] 끔 팔 기대값**(C-4 끔 팔과 같은 꼴): 태그 `final_C4G2_LAS`, `c2_setup.k1_order_gate` = `off`, `c2_setup.k1_order_gate_effective` = false, `controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate` = false, `liftoff_approach_slow.settings` 9값은 프리셋(LAS-b 켬), `c2_setup.las_off` 없음 또는 거짓. 켬 팔은 원판 4.2 그대로다. 한 묶음 C-9 안에 `final_C4G2_LAS_K1`과 `final_C4G2_LAS` 두 판이 있는 것은 정의이므로 원판 8.2 S-2의 "한 묶음 안에 두 판이 섞였다"에 해당하지 않는다(이 묶음에 한한 예외).

<!-- P2-36 v5_resume_4368_rules_rev16.md:250 -->
   - **[정의] 기록 항목**: 두 팔의 `decisions`(dP 포함), 토양 모드 시작 시각, LOC 시각, 두 팔 `controller_commands.npz` sha256 같음 여부, 최대 행정 [mm], 끝 rut 틈 [mm], P3-1~P3-9, 첫 READY [s], rc, 마지막 표본 시각 [s].

<!-- P2-37 v5_resume_4368_rules_rev16.md:254 -->
   - **[정의] P-18 읽기의 전제**(빈 창 막기): 두 팔 모두 rc 0, 마지막 표본 시각 ≥ `--duration` − 0.1 s, 첫 READY 있음, 같은 `--threads`(4), 둘 다 pcore. 하나라도 거짓이면 P-18을 읽지 않고 묶음을 `기록 불완전`으로 둔다.

<!-- P2-38 v5_resume_4368_rules_rev16.md:256 -->
2. **C-10 (G-5 확인, 사용자 결정 3)**: g6 강체 바탕 + S1 앞 패드 패치, F_s 4, 상단, VB/V0 × FL·FR

<!-- P2-39 v5_resume_4368_rules_rev16.md:257 -->
   - **[정의] 기록 항목**: 다리별 F^a_min·F^t_min과 그 시각, F < F_min 시간, F < F_min + 2 kN 시간(원판 7.4 정의), G6-1~G6-7, P3-3, 끝 단계, 최대 행정, 패치 다리 침하 [mm], rc, 마지막 표본 시각 [s].

<!-- P2-40 v5_resume_4368_rules_rev16.md:263 -->
3. **C-11 (seedext 확인, 사용자 결정 6)**: J2 균일, 상단, F_s 0, VB/V0, 잡음 L2 상당

<!-- P2-41 v5_resume_4368_rules_rev16.md:264 -->
   - **[정의] 기록 항목**: 첫 LOC 시각, LOC 주기의 1 ms 크롤러 법선 최대 [N]과 그 값 / W, 0.01 W 위아래, LOC 취소 수, 첫 READY, rc, 마지막 표본 시각 [s].

<!-- P2-42 v5_resume_4368_rules_rev16.md:280 -->
1. **[정의] 정체성(rev15 R15-6 대체의 확장)**
   - rev11 R11-4 5항("`code_at_launch` 없음 = S-12")의 대체(rev15 R15-6, PS-c G-S 1행)를 C-9~C-11 8행으로 넓힌다.
   - 행마다 다음 기록이 있어야 한다. 하나라도 없거나 어긋나면 S-12(커밋)·S-4(SCM 정체성)다.
     - 시작 정체성 파일(gs_identity 꼴, 정체성 도구 `x16_identity.py`): HEAD = R2 `b9f5707d7f3f7a26230b25f4edbc1fec587ca612`, `git status --porcelain --untracked-files=no` 빈 출력, `env`(start env), 금지 env 다섯의 유무(`OUTRIGGER_LOC_SHADOW`, `OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED`, `OUTRIGGER_HULL_HOOK_DLL`, `OUTRIGGER_HULL_HOOK`, `MIXED_HULL_MODE`: 모두 없음), DLL sha256.
     - 끝 정체성 파일(같은 도구 `post`, 행 끝): 끝 HEAD, `git status --porcelain --untracked-files=no`, `git reflog` 5항목, 금지 env 다섯의 유무를 기록하고 시작 파일과 대조한다. HEAD가 시작과 같고, 시작 시각 뒤에 새 reflog 항목이 없어야 한다(있으면 도구 exit 1). 금지 env 다섯은 시작과 끝 양쪽에 기록한다.
     - `result.json`: `code_state.git_at_start` = R2, `num_threads_chrono` = 4, `placement` 마스크(= 그 행의 칸 마스크, R16-14 5)와 `placement.omp_wait_policy` = `PASSIVE`, `hull_hook.mode` = `"fast"`, `hull_hook.dll_sha_validated` = true, `hull_hook.dll_sha256` = `cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15`.
   - 원판 6절 SCM 칸의 대응: start env = 시작 정체성 파일 `env`, 풀 = `placement` 마스크, `OMP_WAIT_POLICY` = `placement.omp_wait_policy`, 훅 = 위 hull 세 값.
   - 정체성 도구 `x16_identity.py`의 sha256은 실행 전 감사에서 고정하고 판정서에 적는다. 다른 Chrono 행에는 R11-4 그대로다.

<!-- P2-43 v5_resume_4368_rules_rev16.md:288 -->
2. **[정의] 기록 항목을 내는 곳**
   - R16-12가 Chrono 판정 도구를 R3..R4 diff 0으로 두므로 C-9~C-11의 기록은 Chrono 판정 도구로 내지 않는다.
   - **경로 1**: 경로 1의 R4 하네스 도구가 각 행 폴더를 직접 읽는다(R16-11 기록 항목, 1의 정체성).
   - **경로 2**: `path2/p2_x16.py`가 따로 읽는다(원판 9.1 C-8 행 꼴).
   - 두 경로가 읽는 행 폴더 파일(`run_S9.py level` 행): `result.json`, `controller_commands.npz`, `step_series.npz`, `r8_series.npz`, `completion_series.npz`, `flow_series.npz`(VB 행만, `--flow-eta-v`가 있을 때), `record/record.npz`, `record/meta.json`, 그리고 1의 정체성 파일 둘. `completion_series.npz`는 모든 행에 필수다.
   - 기록 항목은 K-10 꼴로 대조한다. 맞지 않으면 그 행은 `기록 불완전`이고 python-expert에 원인 확인을 넘긴다(기록 묶음이라 S-13 아님).
   - 이 행들에는 R3 Chrono 도구의 S-12 판정을 쓰지 않는다. 1로 대신한다.

<!-- P2-44 v5_resume_4368_rules_rev16.md:350 -->
4. **[정의] 출력 위치**: `<OUT>` = `C:\workspace\outrigger_control\07_results\S9\R4368X_b9f5707_20261115_013947\`(git 무시 경로, `batch_` 접두 없음). 하위 폴더 `H-11\`, `H-12\`(대체 경로면 `H-12b\`), `C-9\`, `C-10\`, `C-11\`, 정체성 도구 `<OUT>\_tools\x16_identity.py`. 판정서에는 폴더 전체 경로와 정체성 파일·도구의 sha256을 적는다.

<!-- P2-45 v5_resume_4368_rules_rev16.md:318 -->
  - `git diff --name-only b9f5707..R4 -- 03_src 02_params`가 비어 있다.

<!-- P2-46 v5_resume_4368_rules_rev16.md:325 -->
    - (라) 경로 2: `06_analysis/02_control/verif_matrix/v5_resume_4368/path2/` 아래 `README.md`·`p2_4368.py`·`p2_u3.py`·`p2_v5j.py`·`test_p2_4368.py`·`test_p2_u3.py`·`test_p2_v5j.py`·`p2_x16.py`(새)·`test_p2_x16.py`(새), `path2_v5c/` 아래 `README.md`·`p2v5c_common.py`·`p2v5c_grid.py`·`p2v5c_noise.py`·`p2v5c_stage1.py`·`test_p2v5c.py`

<!-- P2-47 v5_resume_4368_rules_rev16.md:327 -->
  - R4 blob 표: R4를 만든 뒤 (다)·(라) 파일의 `git show R4:<파일>` LF 바이트 sha256 표를 판정서 부록에 싣는다. 판정 전 감사가 감사한 브랜치 끝 blob과 대조한다. R4 blob과 다른 도구로 낸 출력은 쓰지 않는다.

<!-- P2-48 v5_resume_4368_rules_rev17.md:56 -->
  3. 하네스 도구 봉인 목록(rev16 R16-13)에 rev17도 넣는다. 두 경로를 같게 한다. Chrono 판정 도구의 봉인 목록은 rev15까지 그대로이고(rev16 R16-13), rev16·rev17 확인은 `tools/verif/seal_check.py`로 한다.

<!-- P2-49 v5_resume_4368_rules_rev19.md:93 -->
- **[사실]** 경로 2 하네스 도구 `path2_v5c`의 `P2_CORE_SHA`는 R4에서 맞춘다(사용자 결정 63). R3b는 하네스 판정을 하지 않으므로 이 판정에 영향이 없다.

<!-- P2-50 v5_resume_4368_rules_rev25.md:176 -->
  - R4: 하네스 도구 브랜치(경로마다 하나)와 R4 통합 브랜치는 **R3f**에서 가르고, R4 조건의 Chrono 판정 도구·허용 목록 기준점은 **R3f..R4**다. 하네스 도구(R4)의 봉인 목록은 rev13~rev25다. R4 하네스 지시문을 넘기기 전에 판정 정의 출처 표 점검(R25-4 누락 점검 2 꼴)을 하네스 묶음에 대해 따로 한다(사용자 결정 95).
