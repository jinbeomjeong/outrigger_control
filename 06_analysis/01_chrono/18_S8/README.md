# 18_S8 — S8 최종 판정 파일 (2026-10-25)

S8(실 마찰·카운터 밸런스·제어 ③·접지 판정 ML) 마감(커밋 dd29aae) 뒤 판정 파일을 모은 폴더다. 사용자 결정(2026-10-25) **"최종 판정만 git"**에 따라 이 폴더에는 배치별 최종 판정 파일과 요약만 둔다. 중간 개정 판정과 재판정 verify 전체는 git에서 빠지는 `07_results/S8/archive/`로 옮겼다(3절). 원본 배치(npz, `result.json`, 에피소드)는 `07_results/S8/<배치>/`에 그대로 있다.

- 하위 폴더 이름은 `<배치>/<묶음>/`이다. 파일 이름은 원본 그대로다.
- 5 MB를 넘는 파일은 요약 `*_summary.json`으로 대신했다. 요약에는 `meta` 전체, `meta.summary`, 실패 행 전체, FLAG 행, 종류별 행 수가 들어 있다. 원본 경로는 요약 파일의 `summary_of`와 아래 표에 있다.
- `_manifest.json`의 항목마다 `location`이 있다: `git`(이 폴더 안, `dest`가 이 폴더 기준 경로), `archive`(`archive_path`가 프로젝트 루트 기준 경로, `archive_sha256`, 대부분 `archive_size_bytes`; ml768 rev52·pre55 두 항목은 크기를 아래 3절 표에서 본다), `none`(복사하지 않은 중복, `duplicate_of`·`same_rows_as`가 같은 내용 파일). 요약 항목의 원본이 archive에 있으면 `original_archive_path`·`original_archive_sha256`이 붙는다. 복사·이동한 모든 파일은 SHA-256으로 원본과 같음을 확인했다(불일치 0).
- 대표 PNG는 없다. S8 배치는 그림을 만들지 않았다.
- 판정 명령의 `python`은 Chrono-dev 인터프리터다(`C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I -X utf8 -u`, 프로젝트 루트에서 실행). 판정은 Chrono를 다시 돌리지 않고 저장된 기록만 읽는다.
- 판정 개정은 각 파일 `meta.judge_revision`의 머리다. "spec rev. N"은 `00_docs/04_control/s6_control_spec.md` 개정 N이다. V15는 `00_docs/01_dynamics/dynamics_model.md` 5.26(개정 39 기준값)과 5.29.7·5.29.11(개정 42·43 판정)이다.
- 이 폴더: 32파일(이 README·`_manifest.json` 포함), 약 7.9 MB.

## 1. 배치 최종 판정 파일 (git, `07_results/S8/` 복사)

| 파일(이 폴더 기준) | 크기 | 출처 배치 | 판정 개정 | 행 / 실패 | 판정 명령 |
|---|---|---|---|---|---|
| `v15_20261025_132215/v15_summary.json` | 88,806 B | `v15_20261025_132215`(V15 본 배치, 로드측 법칙, $L$ 0/2/4/8 kN + 0.05 mm/s 관성 확인 2) | 판정기 `verify.s8_v15`, dynamics 개정 42 5.29.7(A-1~A-4, L-1~L-2) → 개정 43 5.29.11 통과 | 143 / 0 | `python 04_scripts/02_chrono/run_S8V15.py rejudge --batch 07_results/S8/v15_20261025_132215` 다음 `... judge --batch 07_results/S8/v15_20261025_132215` |
| `v15_20261025_142154/v15_summary.json` | 18,061 B | `v15_20261025_142154`(헤드만 변형 $L$ 4, 2사례) | 개정 43 5.29.11 | 29 / 0 | `python 04_scripts/02_chrono/run_S8V15.py rejudge --batch 07_results/S8/v15_20261025_142154` 다음 `judge` |
| `cb_20261025_013946/verify_S8C.json` | 381,957 B | `cb_20261025_013946`(카운터 밸런스 6사례, CB 216.8 재실행) | spec rev. 46 | 307 / 0 | `python 04_scripts/02_chrono/run_S8C.py judge --batch 07_results/S8/cb_20261025_013946 --ref-batch 07_results/S8/p1r_20261024_222013 --lookup-batch 07_results/S8/p1r_20261024_222013` |
| `p1r_20261024_222013/verify_S8C.json` | 2,095,956 B | `p1r_20261024_222013`(제어 ③ 우선순위 1 + N_D8 rpB, 37사례) | spec rev. 46(on 45·44·43) | 1,735 / 0 | `python 04_scripts/02_chrono/run_S8C.py judge --batch 07_results/S8/p1r_20261024_222013 --ref-batch 07_results/S8/p1_20261024_204911 --lookup-batch 07_results/S8/p1_20261024_204911 07_results/S8/rest_20261024_233615` |
| `rest_20261024_233615/verify_S8C.json` | 2,504,682 B | `rest_20261024_233615`(p2 + p3, 49사례) | spec rev. 46 | 1,997 / 0 | `python 04_scripts/02_chrono/run_S8C.py judge --batch 07_results/S8/rest_20261024_233615 --ref-batch 07_results/S8/p1r_20261024_222013 --lookup-batch 07_results/S8/p1r_20261024_222013` |
| `mlj_20261025_080212/verify_S8C.json` | 454,642 B | `mlj_20261025_080212`(MLJ 판정 사례 6: FS24·SS9P·K0V G4RF × $F_s$ 0/8) | spec rev. 46 | 290 / 6 | `python 04_scripts/02_chrono/run_S8C.py judge --batch 07_results/S8/mlj_20261025_080212`. 같은 6사례는 `ml_main_20261025_090131/judged/`로 옮겨 rev. 50 이후 다시 판정했다(2절 `mlj`, 실패 0) |
| `ml_main_20261025_090131/verify_S8ML_summary.json` | 요약 11,798 B(원본 6,036,117 B) | `ml_main_20261025_090131`(ML 본 768: 기준 96 × 에피소드 8) | spec rev. 51 225 | 540 / 3 | `python 04_scripts/02_chrono/run_S8C.py judge --batch 07_results/S8/ml_main_20261025_090131`. **원본**: `07_results/S8/ml_main_20261025_090131/verify_S8ML.json`. 실패 3 = ML78_ep0·ep3 U-S8-32 행(명세 222.3) |
| `c36_20261025_155317/A_rt/verify_S8ML.json` | 788,074 B | `c36_20261025_155317`, 묶음 A(RT + F1, 55 에피소드) | spec rev. 54 248.3 / 249 / 251(C-S8-40) | 135 / 0 | `python 04_scripts/02_chrono/run_S8C.py judge --batch 07_results/S8/c36_20261025_155317/A_rt --ref-batch 07_results/S8/ml_main_20261025_090131` |
| `c36_20261025_155317/B_f1only/verify_S8ML.json` | 52,268 B | 같은 배치, 묶음 B(F1만, 2 에피소드) | spec rev. 54 | 27 / 2 | `... judge --batch 07_results/S8/c36_20261025_155317/B_f1only --ref-batch 07_results/S8/ml_main_20261025_090131`. 해석은 명세 개정 54 |
| `c36_20261025_155317/C_gate/verify_S8C.json` | 220,776 B | 같은 배치, 묶음 C(RE1bF·RE1bP $F_s$ 0) | spec rev. 54 | 129 / 0 | `... judge --batch 07_results/S8/c36_20261025_155317/C_gate --ref-batch 07_results/S8/p1r_20261024_222013 --lookup-batch 07_results/S8/p1r_20261024_222013 07_results/S8/rest_20261024_233615` |
| `c36_20261025_155317/D_fs24/verify_S8C.json` | 315,179 B | 같은 배치, 묶음 D(MLJ_FS24 $F_s$ 0/8) | spec rev. 54 | 123 / 0 | `... judge --batch 07_results/S8/c36_20261025_155317/D_fs24 --lookup-batch 07_results/S8/p1r_20261024_222013` |
| `c37_20261025_180821/E_drain/verify_S8ML.json` | 285,316 B | `c37_20261025_180821`, 묶음 E(P-S8-21 로드 배수 유지 + RT + F1, 17 에피소드) | spec rev. 55 267 / 269.3 for rev. 56(C-S8-42) | 62 / 0 | `python 04_scripts/02_chrono/run_S8C.py judge --batch 07_results/S8/c37_20261025_180821/E_drain --ref-batch 07_results/S8/ml_main_20261025_090131` |
| `c37_20261025_180821/C_gate/verify_S8C.json` | 223,819 B | 같은 배치, 회귀 C | 같음 | 130 / 0 | `... judge --batch 07_results/S8/c37_20261025_180821/C_gate --ref-batch 07_results/S8/p1r_20261024_222013 --lookup-batch 07_results/S8/p1r_20261024_222013 07_results/S8/rest_20261024_233615` |
| `c37_20261025_180821/D_fs24/verify_S8C.json` | 321,955 B | 같은 배치, 회귀 D | 같음 | 124 / 0(FLAG 1: MLJ_FS24_Fs0 지연 다리 최소) | `... judge --batch 07_results/S8/c37_20261025_180821/D_fs24 --lookup-batch 07_results/S8/p1r_20261024_222013 --deferred-ref 07_results/S8/mlj_20261025_080212` |

- 판정 명령은 `run_S8C.py`·`run_S8V15.py` docstring과 c37 계획 출력(`c37_jobs` → `"judge"`)의 명령, 각 파일 `meta.ref_batch`·`meta.lookup_batches`·`meta.ref_twist_work`에서 다시 적었다. 실행 당시 셸 기록은 남아 있지 않다. c37 D의 `--deferred-ref`는 `meta`에 기록되지 않아 명령은 c37 계획 출력에서 가져왔다.
- 복사하지 않은 판정 파일: `ml_main_20261025_090131/judged/verify_S8C.json`(MLJ 6사례, rev. 50, 308 / 0)은 배치 루트가 아니라 뺐다. `cb_20261025_000840`, `p1_*`, `ml_pilot_*`, `smoke_check_*`는 이번 범위가 아니다.
- 중간 개정 판정(p1r rev. 43·44·45, rest rev. 45, V15 첫 판정 `v15_summary_v1.json`)은 3절 archive에 있다. 같은 파일의 원본은 각 배치 폴더 `07_results/S8/<배치>/`에도 그대로 있다.

## 2. 재판정 요약 (git, `rejudge/`)

Chrono 없이 같은 기록을 판정기 개정별로 다시 판정한 출력의 **요약과 입력 로그만** 여기 둔다. verify 전체는 3절 archive에 있다. 원래 위치는 세션 scratchpad `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\85e4a02e-5208-42d0-8012-d36d25080593\scratchpad\`이고 scratchpad는 세션이 끝나면 지워질 수 있다.

| 폴더 | 원래 위치(scratchpad 기준) | 판정기 | git에 남긴 것 | 명령(스크립트는 `04_scripts/02_chrono/s8_judge/`) |
|---|---|---|---|---|
| `rejudge/rev52/` | `rejudge\` | spec rev. 52 232 / 230(C-S8-37) | `summary_{p1r,rest,mlj,ml768}.json`(C-S8-37 비교 요약). 같은 실행의 `verify_S8C_{mlj,p1r,rest}_rev52.json`은 archive `rejudge/rev54/*_base52.json`과 행·지표가 같고 `meta.judge_revision` 문자열만 달라 보관하지 않았다(`_manifest.json`의 `same_rows_as`). ml768 rev52 원본은 archive에 있다 | `python rejudge_rev52.py <프로젝트 루트> <p1r\|rest\|mlj\|ml768> <출력>` |
| `rejudge/rev54/` | `cad-run\rejudge54\` | base52 = rev. 52, rev54 = spec rev. 54(C-S8-40) | `verify_S8ML_ml768_{base52,rev54}_summary.json` | `python rejudge_batches.py --src <rev. 52 또는 54 판정기 03_src> --tag base52\|rev54 --out <출력> ml768 mlj p1r rest`, 비교 `python compare54.py <출력>`, 요약 `python summ54.py <파일…>` |
| `rejudge/rev55/` | `cad-run\rejudge55\` (= `cad-run55\rj_pre55\`, 바이트 동일) | spec rev. 55(C-S8-41) | `verify_S8ML_ml768_rev55_summary.json` | `python rejudge_batches.py --src <rev. 55 판정기 03_src> --tag rev55 --out <출력>`, 비교 `python compare55.py --c36 07_results/S8/c36_20261025_155317 --rev54 <rev54 폴더> --rev55 <rev55 폴더>` |
| `rejudge/rev56/` | `cad-run55\rj_new56\` | spec rev. 55 267 / 269.3 for rev. 56(C-S8-42) | `verify_S8ML_ml768_new56_summary.json` | `python rejudge_batches.py --src 03_src --tag new56 --out <출력>`(HEAD dd29aae의 판정기가 rev. 56), 비교 `python compare56.py --pre <rev55 폴더> --pre-tag rev55 --new <rev56 폴더>` |
| `rejudge/rev56/inputs_logs/` | `cad-run55\log_*.txt`, `c55_avail_A17.json`, `ctrl-run55\c55_defer.json` | — | 재판정 실행 로그(pre55·new56 각 3개), control 비교 입력 2개(전부) | `python avail_vs_c55.py --src 03_src --c55 rejudge/rev56/inputs_logs/c55_avail_A17.json --verify <archive rev56>/verify_S8ML_A_new56.json`, `python defer_vs_c55.py --c55 rejudge/rev56/inputs_logs/c55_defer.json --new <archive rev56>` |

- 비교 스크립트의 `<rev54 폴더>` 등은 3절 archive 경로다. ml768 비교에는 `07_results/S8/archive/rejudge_ml768/rev5x/`의 원본이 필요하다(archive 18_S8_extra 폴더에는 ml768이 없다).
- rev. 52·54·55 판정기는 scratchpad 사본 트리(`stage_rev54`, `proj_new56` 등)로 돌렸고 그 트리는 남아 있지 않다. 개정별 커밋도 따로 없다(9636556 → dd29aae 사이). 그래서 rev. 52~55 출력은 지금 다시 만들 수 없고, archive 사본이 유일한 기록이다(git 밖이므로 `07_results` 백업에 의존한다). HEAD `03_src`의 판정기는 rev. 56 표지(`JUDGE_REVISION_REV56`)를 가지므로 rev. 56 출력은 다시 만들 수 있다(같은 바이트가 나오는지는 다시 돌려 확인하지 않았다).
- 2026-10-25 옮긴 뒤 사본으로 비교 스크립트를 다시 돌린 결과: `compare56.py` 기존 행 변경 0, 지연 다리 창 끝 변경 1건(A, C-S8-42의 의도된 창 정의 변경), `avail_vs_c55.py` 17 에피소드 차 0, `defer_vs_c55.py` 13개 중 2개 최소값 차(ML00_ep5 RR −0.717 / −1.079 kN, ML78_ep1 RR −0.709 / −0.974 kN, 창 끝은 같음). 이 결과가 scratchpad 원 실행 결과와 같은지는 원 출력이 남아 있지 않아 대조하지 못했다.

## 3. archive (git 제외, `07_results/S8/archive/`)

2026-10-25 이 폴더에서 `Move-Item`으로 옮기고(같은 상대 구조) 이동 뒤 SHA-256이 이동 전과 같음을 확인했다. ml768 원본은 scratchpad에서 `Copy-Item`으로 복사하고 원본·사본 SHA-256이 같음을 확인했다.

### 3.1 `07_results/S8/archive/18_S8_extra/` (이 폴더에서 옮김, 25파일, 37,356,350 B)

| 파일(`18_S8_extra/` 기준 = 옛 `18_S8/` 기준) | 크기 B | SHA-256 | 내용 |
|---|---|---|---|
| `p1r_20261024_222013/verify_S8C_rev43judge.json` | 1,409,096 | `e0fddd03332dc2a99f850be3a50b4fc24aa34c318e06c28da40485c9c3db8bcb` | p1r spec rev. 43 판정, 1,422 / 0 |
| `p1r_20261024_222013/verify_S8C_rev44judge.json` | 1,698,505 | `b80483cac15c90aae321057d5e33324298b98f49178faaa2708180c29942c7c0` | p1r spec rev. 44, 1,643 / 0 |
| `p1r_20261024_222013/verify_S8C_rev45judge.json` | 2,067,903 | `a1073ee190ac3f6374d4cf408b115b79cb921498c5dcb753c497ebf47b7e7d0c` | p1r spec rev. 45, 1,724 / 0 |
| `rest_20261024_233615/verify_S8C_rev45judge.json` | 2,472,475 | `f7fcf14ae7e12ff1b3ef331e4dcee431a8552c6d91583c501e2fc8ab5db80ac4` | rest spec rev. 45, 1,983 / 8(rev. 46에서 실패 0) |
| `v15_20261025_132215/v15_summary_v1.json` | 24,892 | `b0c7bdbf94b1f7ad98a9b0dbf7749a8be4192511cf094689ac0faf385b6c4c69` | V15 첫 판정(판정기 수정 전, 개정 39 5.26.9 지표), 실패 6 |
| `rejudge/rev54/verify_S8C_mlj_base52.json` | 628,027 | `bb5de2f71e8e3a027d586bbc2fcdb49a567085705ea9d761b63235f258a9da2b` | rev. 52 판정기 |
| `rejudge/rev54/verify_S8C_mlj_rev54.json` | 698,576 | `05ffc6096f1b07a3460660fde6e3bdb5f657ca273416b90ede1cc4cc7a0d6e89` | rev. 54 |
| `rejudge/rev54/verify_S8C_p1r_base52.json` | 2,485,706 | `99497011d81f449daebc8f485bc4f07542c873276ca64cdf3212154ab6497afa` | rev. 52 |
| `rejudge/rev54/verify_S8C_p1r_rev54.json` | 2,693,423 | `0f89c3f0d8444d8d68a1507b1eb98de3d3b2f9335589348e8ded6ee26a3868f7` | rev. 54 |
| `rejudge/rev54/verify_S8C_rest_base52.json` | 3,136,030 | `e1a8d3e45086a719c15f69cf43ebc1606bc5032fe8c837c61ee190028e168a29` | rev. 52 |
| `rejudge/rev54/verify_S8C_rest_rev54.json` | 3,466,519 | `df1d2435fefa323f5869c98dc239fd1f63934bddad4e9d34264d9610fbdb9915` | rev. 54 |
| `rejudge/rev55/verify_S8C_C_rev55.json` | 222,550 | `242fdca459d365ba39de1f88b188bb777e1ef578939fa71f86194f5247448a73` | rev. 55 |
| `rejudge/rev55/verify_S8C_D_rev55.json` | 318,751 | `096d0cfa31a6150c108a11b457e7c1bd98253f3dd0362fcc8767624b8d303997` | rev. 55 |
| `rejudge/rev55/verify_S8C_mlj_rev55.json` | 699,236 | `7a402c2fa1ea1662d293b6dad8f54799367f4d3e862a4c8477323e54da0212c9` | rev. 55 |
| `rejudge/rev55/verify_S8C_p1r_rev55.json` | 2,694,327 | `9081ed5e760a46a44f92d12510a52a10bf7f65ff9285d2c7c4d670965b2b4439` | rev. 55 |
| `rejudge/rev55/verify_S8C_rest_rev55.json` | 3,467,342 | `621ebbe8feb5863b184012913dc2ce3433e62dc39d64ea5b044084188483d647` | rev. 55 |
| `rejudge/rev55/verify_S8ML_A_rev55.json` | 805,917 | `9411db6e048eb4bff29793ea61e350c3742c28885031502d5599b45042037fab` | rev. 55 |
| `rejudge/rev55/verify_S8ML_B_rev55.json` | 53,800 | `2d3147e63f8b9cd613df742b410f3d51a6d5ef1fdee594c7ceb3718c8d0e951c` | rev. 55 |
| `rejudge/rev56/verify_S8C_C_new56.json` | 223,955 | `46139e93f6598bb91144de913e1900fbc0034767f283246e62fd67d4d01854e0` | rev. 56 |
| `rejudge/rev56/verify_S8C_D_new56.json` | 322,023 | `34b19dd5590a825bc226243002f066e8970106cd7e67bad804ae56bc4aebe59b` | rev. 56 |
| `rejudge/rev56/verify_S8C_mlj_new56.json` | 699,793 | `61b29fb27f7d9b105babf6376276c4f85cca4343e2b08fa3d86cfbe2b69a2476` | rev. 56 |
| `rejudge/rev56/verify_S8C_p1r_new56.json` | 2,694,884 | `c6acad66c7fddb2131e1ff2eb4d04c459ebb9e3e9a8f99023d1e8c8a001657f3` | rev. 56 |
| `rejudge/rev56/verify_S8C_rest_new56.json` | 3,467,899 | `630b390c2135e3d75dc417c5107ed8cfac0789760b55b75072838379684ee9de` | rev. 56 |
| `rejudge/rev56/verify_S8ML_A_new56.json` | 845,994 | `69d0d225169e9f9e637887a5e5990a0a8aef97295e7282bfe7bec71642cdf7d0` | rev. 56 |
| `rejudge/rev56/verify_S8ML_B_new56.json` | 58,727 | `cccbfc3f1f2d9c98d56aea3514008ef29b7d24ba97a15a89e047d2b331fd1b8c` | rev. 56 |

### 3.2 `07_results/S8/archive/rejudge_ml768/` (scratchpad에서 복사, 6파일, 45,824,105 B)

| 파일(`rejudge_ml768/` 기준) | scratchpad 원 위치 | 크기 B | SHA-256 | git 요약 |
|---|---|---|---|---|
| `rev52/verify_S8ML_ml768_rev52.json` | `rejudge\` | 7,149,629 | `78111406a1a6c57f8dca900ce2e1ca46d368777bbbab2a8881df8cb694c8c0a7` | `rejudge/rev52/summary_ml768.json`(비교 요약). 행·지표는 `rev54/..._base52.json`과 같다 |
| `rev54/verify_S8ML_ml768_base52.json` | `cad-run\rejudge54\` | 7,149,943 | `bbaee16bf19cb14d81d0de5b357f38f6a124d29e20b3b060068cff1a105c480c` | `rejudge/rev54/verify_S8ML_ml768_base52_summary.json` |
| `rev54/verify_S8ML_ml768_rev54.json` | `cad-run\rejudge54\` | 7,864,056 | `f567195db0f4e2ebd415304aef6ad2bc9968e09118369d06ca0a694e06850a86` | `rejudge/rev54/verify_S8ML_ml768_rev54_summary.json` |
| `rev55/verify_S8ML_ml768_rev55.json` | `cad-run\rejudge55\` | 7,886,640 | `b243896c0baee3819126f2ebdeb372326be328942609bcb75a7ae9b689719343` | `rejudge/rev55/verify_S8ML_ml768_rev55_summary.json` |
| `rev55/verify_S8ML_ml768_pre55.json` | `cad-run55\rj_pre55\` | 7,886,640 | 위와 같음(바이트 동일) | 같음 |
| `rev56/verify_S8ML_ml768_new56.json` | `cad-run55\rj_new56\` | 7,887,197 | `45880c758c736f3c6722da5d81d16349fcb8383a9b436f061135d318eff3e56d` | `rejudge/rev56/verify_S8ML_ml768_new56_summary.json` |
