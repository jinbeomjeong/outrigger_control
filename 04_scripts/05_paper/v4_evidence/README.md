# 논문 v4 근거 스크립트 보존본

`09_paper/v4`의 원고 주석(`draft/*.md`의 `<!-- src -->`와 `FIGURE_REQUEST` 블록, `latex/sections/*.tex`의 `%`)이 가리키는 집계·확인 스크립트 중 에이전트 scratchpad에만 있던 것을 복사했다. `09_paper/`는 커밋하지 않고(`.git/info/exclude`) scratchpad는 임시 폴더라서, 원고 수치의 집계 근거가 사라지지 않게 둔다.

- 복사일: 2026-11-05. 내용은 원본과 바이트까지 같다(복사 때 대조). 원본은 지우지 않았다.
- **기록용이다.** 복사 뒤 다시 실행해 결과를 확인하지 않았다. 원고 주석은 고치지 않았으므로 주석의 `scratchpad ...` 경로를 아래 표로 찾아 읽는다.
- **경로 의존**: 표의 스크립트 중 scratchpad 경로에 의존하는 것은 없다. 입력을 읽는 스크립트는 프로젝트 절대경로 `C:\workspace\outrigger_control\...`를 코드에 적어 두었으므로 다른 위치에서 재실행하려면 그 경로를 고쳐야 한다. 입력 결과 파일이 그 뒤 바뀌었다면 값이 원고와 다를 수 있다.
- 폴더 구조는 원본 scratchpad 하위 폴더 이름을 그대로 쓴다. `pwe_final`의 `agg1~7.py`는 원본 폴더에 같이 있던 원고 편집 스크립트와 구분해 집계 스크립트만 옮겼다. `fa_fmin_check`·`settle_b`는 주석이 폴더 전체를 가리키므로 그 안의 `.py`를 모두 옮겼다.

## 원본 위치

| 표기 | 원본 scratchpad |
|---|---|
| A | `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\a73a016d-417c-4696-97f8-8d5bc4937486\scratchpad` |
| B | `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\88c41358-354a-4920-a8e2-5dba519bb75b\scratchpad` |

원본 경로 = 표기 위치 + 복사 위치(이 폴더 기준 상대 경로).

## 대응표

절·표 번호는 2026-11-05 빌드(`09_paper/latex/main.aux`) 기준이다. 표·그림은 주석이 그 표·그림 환경 안이나 바로 뒤에 있을 때만 적었고, 나머지는 절만 적었다. `draft`의 줄 번호는 `09_paper/v4/draft/` 기준이다.

| 주석의 경로 | 복사 위치 | 원본 | 원고 위치 | 비고 | sha256 |
|---|---|---|---|---|---|
| `agg1.py`<br>`pwe_final/agg1~7.py` | `pwe_final/agg1.py` | B | 절 4·4.2·4.7·4.9; 표 20<br>draft 04_results.md:3, 04_results.md:100, 04_results.md:105, 04_results.md:121, 04_results.md:254, 04_results.md:275, 04_results.md:306 |  | `6d510dbbd95d154561ffa532ac6342d4d79d2a68d32557b393199357378973d1` |
| `agg2.py`<br>`pwe_final/agg1~7.py`<br>`pwe_final/agg2·3·5·6.py` | `pwe_final/agg2.py` | B | 절 2.6.3·4·4.2·4.3.1·4.3.2; 표 14<br>draft 02_6_conditions.md:91, 04_results.md:3, 04_results.md:100, 04_results.md:105, 04_results.md:119, 04_results.md:132, 04_results.md:155 |  | `4d1e81272c628c5e6bb4bea3c9ed025b38b5d3c2ab79018583ede323417ca60b` |
| `agg3.py`<br>`pwe_final/agg1~7.py`<br>`pwe_final/agg2·3·5·6.py`<br>`pwe_final/agg3.py` | `pwe_final/agg3.py` | B | 절 2.6.3·3.4·4·4.1·4.2·4.3.2·4.8.2; 표 13b<br>draft 02_6_conditions.md:91, 03_controller.md:83, 04_results.md:3, 04_results.md:51, 04_results.md:53, 04_results.md:83, 04_results.md:87, 04_results.md:96, 04_results.md:155, 04_results.md:302 |  | `951eb48e939a326a315481d81562d741ec8aecd6ca8a89219f8c0e4953a76eeb` |
| `agg4.py`<br>`pwe_final/agg1~7.py` | `pwe_final/agg4.py` | B | 절 4·4.3.1·4.7; 표 15<br>draft 04_results.md:3, 04_results.md:136, 04_results.md:149, 04_results.md:256 |  | `e09d81b480a5f86924be65d043d86fee72589a4643b2eeb7065862691f400eae` |
| `agg5.py`<br>`pwe_final/agg1~7.py`<br>`pwe_final/agg2·3·5·6.py` | `pwe_final/agg5.py` | B | 절 2.6.3·4·4.2·4.4·4.9<br>draft 02_6_conditions.md:91, 04_results.md:3, 04_results.md:121, 04_results.md:190, 04_results.md:306 |  | `6ccf6ca9ca9f0c378fececc43078d27951584355d605edee6fa7c8426f0dd54f` |
| `agg6`<br>`agg6.py`<br>`pwe_final/agg1~7.py`<br>`pwe_final/agg2·3·5·6.py`<br>`pwe_final/agg6.py` | `pwe_final/agg6.py` | B | 절 2.6.3·4·4.1·4.2·4.5; 표 18<br>draft 02_6_conditions.md:91, 04_results.md:3, 04_results.md:45, 04_results.md:51, 04_results.md:96, 04_results.md:225 |  | `a90a20ef9d1fdc6aef89b601fefbfb51e9544277dc668853db90db768a572f25` |
| `agg7.py`<br>`pwe_final/agg1~7.py` | `pwe_final/agg7.py` | B | 절 4·4.3.2·4.4·4.5·4.6·4.7·4.8.2; 표 17·표 18·표 20<br>draft 04_results.md:3, 04_results.md:155, 04_results.md:190, 04_results.md:204, 04_results.md:210, 04_results.md:225, 04_results.md:227, 04_results.md:233, 04_results.md:256, 04_results.md:275, 04_results.md:302 |  | `7bb65a9724e2ad2118390d110d97acefc9da3fa710aec8f096e11b96be9c7e11` |
| `agg_b.py`<br>`paper_v44/agg_b.py` | `paper_v44/agg_b.py` | A | 절 1·2.6.2·4·4.1·4.2·4.5·4.6·4.7·4.10; 표 6<br>draft 01_introduction.md:9, 02_6_conditions.md:81, 04_results.md:5, 04_results.md:53, 04_results.md:85, 04_results.md:100, 04_results.md:105, 04_results.md:121, 04_results.md:210, 04_results.md:233, 04_results.md:254, 04_results.md:331 | 실행하면 스크립트와 같은 폴더에 `agg_b_out.txt`를 쓴다(원본 출력은 복사하지 않음) | `90a9f1bcc4aeaa5cc882417ab8c06ea30c312fa748aa4ea10b495cf2c75379af` |
| `paper_v44/xc.py`<br>`xc.py` | `paper_v44/xc.py` | A | 절 2.6.2·4.3.2; 표 6<br>draft 02_6_conditions.md:81, 04_results.md:157 |  | `d3b47a8d8e336936d663f74e243f3d12f41b3962a3d8e13c8ddd444137440416` |
| `paper_v44/a1chk.py` | `paper_v44/a1chk.py` | A | 절 4.8.1; 표 22<br>draft 04_results.md:323 |  | `07392c37c03bb96e136799ccbca097bc10e645457eb2ea8f47efbac094105b19` |
| `hyd_basis/basis_calc.py`<br>`scratchpad/hyd_basis/basis_calc.py` | `hyd_basis/basis_calc.py` | A | 절 2.2<br>draft 02_modeling.md:62, 02_modeling.md:64 | 프로젝트 파일을 읽지 않는다. YAML·dynamics_model 값을 상수로 옮겨 적음(2026-10-31 기준) | `2cd7c00b9314689fa741fbe54ce888c9acf65a161d6e3294defabc9af5d10a09` |
| `dyn_basis/l2b_dt_limits.py`<br>`scratchpad/dyn_basis/l2b_dt_limits.py` | `dyn_basis/l2b_dt_limits.py` | A | 절 2.2<br>draft 02_modeling.md:68 | 프로젝트 파일을 읽지 않는다. YAML 값을 상수로 옮겨 적음(2026-10-31 기준) | `7995ca5d51aa8b60d9d3c111e54925cb3b4d5d40f4d7263f901acc452e069808` |
| `rev_v44/pairs_padB.py` | `rev_v44/pairs_padB.py` | A | 절 2.5.2·4<br>draft 02_modeling.md:145, 04_results.md:9 |  | `c60cb76e06a6d03f23f87b52a0bae5327355ece04963a29455b221977a2deee2` |
| `rev_v44/l1_padB.py` | `rev_v44/l1_padB.py` | A | 절 4.8.1<br>draft 04_results.md:283 | `04_scripts/03_control/s8/`의 판정 모듈을 경로로 불러온다 | `9c1d639cc3b1b38f86d3349ed9b8ab5a809d1f526ef1d765682f9e567174de49` |
| `pwe_figpack/pairs_check.py` | `pwe_figpack/pairs_check.py` | B | 절 4; 그림 13<br>draft 04_results.md:17 |  | `3660dad668189f8cdabcf91bf8cb3c0926c648ec8a45c5842de6e03a2e00d23d` |
| `r79_pad/padB_recount.py` | `r79_pad/padB_recount.py` | A | 절 2.5.3·4.8.1<br>draft 02_modeling.md:149, 04_results.md:283 | scipy 필요 | `2448e1b0f9c543b3f647a4c74c135bab7f2fb479ed03786ecf2b47355494ff88` |
| `scratchpad fa_fmin_check\` (폴더만 가리킴) | `fa_fmin_check/g6_min.py` | A | 절 2.1<br>draft 02_modeling.md:16 |  | `a2327ff5210a1a119bbb4105f7f8335b5b582e1b333be10c94f98988c116d7b7` |
| `scratchpad fa_fmin_check\` (폴더만 가리킴) | `fa_fmin_check/low_force_rows.py` | A | 절 2.1<br>draft 02_modeling.md:16 | 입력 파일 이름을 인자로 받는다 | `843cd2407d8162ac62d6c66d44e5a3090896bb92a207dfc97fb6e1712dd9cf53` |
| `scratchpad fa_fmin_check\` (폴더만 가리킴) | `fa_fmin_check/scan_mf.py` | A | 절 2.1<br>draft 02_modeling.md:16 |  | `554f08b9b7ad628b5f3976e8343aa17b971cdacc4c40566679f55c310ede63bf` |
| `scratchpad settle_b\` (폴더만 가리킴) | `settle_b/ab_identity.py` | A | 절 2.5.2<br>draft 02_modeling.md:126 |  | `b380611e91ead84b8fabc44eda9fde26ad9efe9b115a3cdd82f0d5d67a9154f2` |
| `scratchpad settle_b\` (폴더만 가리킴) | `settle_b/probe.py` | A | 절 2.5.2<br>draft 02_modeling.md:126 | 입력 파일 이름을 인자로 받는다(settle_b) | `ba822de5fdbe52f79dec1027f3a711de4ba6071c6c15527fc6a7632e8566779f` |
| `scratchpad settle_b\` (폴더만 가리킴) | `settle_b/probe2.py` | A | 절 2.5.2<br>draft 02_modeling.md:126 |  | `589c43a42b7ac161b0febc1b024e7f02b906a4adb28253a62fbd64544c043d42` |
| `scratchpad settle_b\` (폴더만 가리킴) | `settle_b/settle_split.py` | A | 절 2.5.2<br>draft 02_modeling.md:126 |  | `19581d3a243e99d1c559360ee8039bd092db09d119b63d53257670a955ac8d82` |

## 복사하지 않은 참조

스크립트가 아니어서 복사하지 않았다. 원본은 아래 위치에 그대로 있다.

| 주석의 경로 | 원본 | 원고 위치 |
|---|---|---|
| `paper_v44/agg_b.py`의 출력 `agg_b_out.txt` | `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\a73a016d-417c-4696-97f8-8d5bc4937486\scratchpad\paper_v44\agg_b_out.txt` | 04_results.md:5 |
| `scratchpad python-fig34b/fig4_conditions.md` | `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\88c41358-354a-4920-a8e2-5dba519bb75b\scratchpad\python-fig34b\fig4_conditions.md` | 03_controller.md:52 |

그림 스크립트(`09_paper/figures/scripts/`)와 변환 도구(`09_paper/latex/tools/`)는 scratchpad 전용이 아니라 `09_paper/` 안에 있으므로 여기에 두지 않았다. `09_paper/`가 커밋되지 않는다는 점은 같다.
