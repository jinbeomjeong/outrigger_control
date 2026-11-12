# B1 크리프 근거 `V5-B1-CREEP` — 실행 전 기록 (prelaunch)

- 작성: python-expert(경로 1 쪽 칸), 2026-11-12. 기준 checkout `C:\workspace\outrigger_control`, master `bd64cc405990101ca8f3398ba2b9db9edcfc01b4`, 추적 변경 0.
- 틀: `b1_creep_prelaunch_draft.md`(같은 폴더). 이 파일은 **추적 밖**이다(커밋은 메인 세션 판단).
- 아직 채우지 않은 칸은 중괄호 없는 대문자 이름으로 남겼다(`RUN_HEAD` 같은 꼴). 메인 세션이 실행 직전·직후에 채운다. 경로 2 칸은 비워 두었다(경로 2 작성자·메인 세션 몫).
- 판정 값은 적지 않았다. B1 Chrono 본 실행 결과는 아직 없다.

## 1. 규칙

| 항목 | 값 |
|---|---|
| 원판 | `06_analysis/02_control/b1/b1_creep_rules.md`, sha256 `6b99702ce26d6da28fbfe6473b622c7e51419241916cbc101f795828f498774e`(LF, CRLF 0), `.sha256` 같은 폴더, 봉인 커밋 `1ad3e5d` |
| rev1 | `06_analysis/02_control/b1/b1_creep_rules_rev1.md`, sha256 `9f72af5babc36a9164a79163a0c3fa8707a0b8dc71aa3bfe978ebdf33d0905cf`(LF, CRLF 0), `.sha256` 같은 폴더, 봉인 커밋 `417ce28` |
| 격자 시험 전제 | 계획 `0e909bf1…`, rev1 `3f354eb7…`, 판정 `a483ac48…` `PASS`(원판 첫머리 그대로) |
| 경로 1 도구의 규칙 대조 | `b1_creep_metrics.py` `check_rules_files`가 실행 때마다 두 판 sha를 대조한다(다르면 종료 2). 2026-11-12 rev1 상수 계산에서 둘 다 `match` |

## 2. 파라미터 (원판 1.1)

| 이름 | 값 |
|---|---|
| `CTRL_TAG_VB` / `CTRL_TAG_V0` | `final_C4G2_P3_LAS_K1` / `final_C4G2_LAS_K1` |
| `CTRL_PRESET` | `C2Config().with_10hz_d1()` 그대로, 래퍼 없음 |
| `P7_REF` | `06_analysis/03_hydraulic/coupled/v5/soil_defer/s2d_SC.jsonl` sha256 `70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa`, 줄 선택 `s2d.candidate == "P0"`, 키 `d1.key` |
| `HULL_DLL_SHA` | `cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15` = `03_src/outrigger_sim/native/chrono_hull/bin/chrono_hull_hook.dll` 원시 바이트 sha(2026-11-12 측정, 일치) |
| `START_LIMIT` | `record_only` |
| `HEAD_M`(실행 커밋) | `bd64cc405990101ca8f3398ba2b9db9edcfc01b4`(메인 세션 채움, 시작 직전 git rev-parse HEAD) |
| 하네스 커밋 | `7246c19a1aec6cfe9a6ba3b2f571a789fcf38912`(하네스 identity 시작·끝 같음). `HEAD_M`과 다르면 I-9 이유를 적는다: `git diff 7246c19 RUN_HEAD -- 03_src 04_scripts` 결과(하네스 경로 파일 변경 여부) 03_src·04_scripts 차이 없음(git diff --stat 7246c19 bd64cc4 = 06_analysis/02_control/b1/ 아래 10파일만, 실행 전 감사 기록; 메인 세션 채움) |
| 풀 | 배치표 `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\b1\schedule_main.json` sha256 `3d3b0117737ffd4bf0304a547d54b40ea4357bf842e42021f2c4357774114f94`, 6행 P, 4병렬. 행별 마스크: 배치표에 행별 마스크 없음, 행이 스스로 P코어에 고정, 예약 b1-chrono-main 0x0000FFFF(r-20261112125158-622c2d)(배치표에서 메인 세션이 옮김) |

## 3. 도구·코드 sha (master `bd64cc4`, 2026-11-12 측정)

원시 = 작업 파일 바이트, LF = CRLF→LF 정규화 값, blob = git 색인.

| 파일 | 원시 sha256 | LF sha256 | blob |
|---|---|---|---|
| 경로 1 `06_analysis/02_control/b1/b1_creep_metrics.py` | a9518c65aeb791ce55e83a8d94bbb063fe0b8b5046d0ef5c4b030efa924853dd | 같음 | 229e2251b06dffc3d31dd9a73cc23512fa7f697e |
| I-17 `06_analysis/02_control/b1/b1_preset_dump_diff.py` | 2acb3755acaf1a19e1e86f7c1536cba354278c95a71a73408009b20c1c705108 | 같음 | de16953e871f75f375ef74f20f263c57002a18d8 |
| 경로 2 `06_analysis/02_control/b1/path2/b1_path2.py` | f4f8be830eb241ee0c15a8858d7b023171af51e165707d9d853889f09cebfe7e | 같음 | 022fae7d2b6978b3b320f0ad42fd24b776cb6706 |
| 경로 2 keymap `06_analysis/02_control/b1/path2/b1_keymap.json` | 19021bc63635f57b65941a5bd9dda0ecdea64a9d9caf151751c1489a5f03501b | 같음 | 43c6fedb62dadbcadf497a5477aa0b25dcf45d28 |
| 하네스 러너 `04_scripts/03_control/b1/b1_harness.py` | 565b2317be385c3ece3203104d13ab3d4079652ca1fe4bf2fe548cb85765276d | a8f144ce77d1716fae91df15d7df691bb88ac6eb3513a76297ae69478467290e | c23ead2f834eabfe27daa2ddf1fc6c427063b184 |
| 하네스 기록 `04_scripts/03_control/b1/b1_record.py` | 9344e00f781bcb9765507bdd3577d91aa1363723e7b1c3acd6a90b9cd6ae8c4c | 6f1eec29a33a09b35b984ca8459fc1f18fe8c8f758ea8e514bcdf0006ac73ad6 | 0df384dd5b8b23c765ddebae099919e5bff86032 |
| cad 기록 `03_src/outrigger_sim/chrono/b1_grid_record.py` | 198cf3bb5ffcaf959ddcca41fa730fc8d7e6c3d7ff770f97f338ba79752142a3 | eb2f030e304aababe0cbdaf0c5ae8f52b226d75532f1364ad734821a1729e95e | 4217ab72a2dcbeb565ce4f0a6095f4935152d2ef |
| 행 모듈 `04_scripts/02_chrono/b1_creep_chrono_rows.py` | 5a243a1ab91c8a4e4c9389d34c04d3fa44e4a8374be2b2967f33abd379b4631d | 4e1b214a76f754c3e0431340108c970aa0623b0a0b1f6c1816f7c66c0580370e | 09904098cecc5d2e0bf02b028542e9024a53757b |
| `04_scripts/02_chrono/run_S9.py` | 9a0575aad80cd46e9c20489bcd4d100f37c98e12ed1d1758eba5a926b024c752 | 1341b9078d9f9e273cb07401a1e6c153f4a08567e618b638d4276e84bd967363 | ae2fd8cc03f7654dc0cdecd984515ce581a15427 |
| `04_scripts/02_chrono/s9_batch.py` | 34b21a788ac3660c45482bf8e7f6afca448b69477b1095b4f638e9d511767ca4 | 0f209d4c6cbe58db9d5b7180ccca7c03dcbe7fba07474660e2b8c4f1a206397b | 787027d62a6b681d40a3d0a5cd6354e637879dcd |
| `03_src/outrigger_sim/control/c2.py` | f58ee42b0f10ea42ceac5768e6ed373a38ee5e14440d9fc831536700b45ba6b1 | b323bf8a26691c3e857acccdd674e7945199289409e7cd57493c9b5c2632b6fd | 18c718767090cf68ce1d80d504ec2684af426fc1 |
| `03_src/outrigger_sim/chrono/hull_hook.py` | afef13ec8f75d42d95ddaf3342273c2ec476ae35450c665055f40100a5e3bdc3 | aae8495824089e7932ec5f677f85d313ecc81a23db21e4747aedfb472be65ece | 1c3eb1e3ad725951161d3dcf599adbe02112cea2 |
| YAML `02_params/rexome33.yaml`(I-8) | ef2880f98aa6a20df18edd515fd227e886aa5c384f4ef235bc85d4cec38987ce | 같음 | 7db55937c80e96e8a3db1b1fa0d725be0829c76f |
| DLL `03_src/outrigger_sim/native/chrono_hull/bin/chrono_hull_hook.dll`(git 제외) | cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15 | (이진 파일, 원시 값만 씀) | — |

- 실행 전 감사 수정 (a) 반영(2026-11-12 12:56, Chrono 첫 행 끝나기 전): 경로 1 `b1_creep_metrics.py`는 브랜치 `b1-path1-fix` 커밋 `1ac4849e19f7005ad9ddf413556b08f1c6f68fe5`(부모 bd64cc4)의 원시 = LF sha256 `6b6e04acfd0cfb77e53b35981984bd4a9e4ccad2b4ce5446b6e5e7c018dda9d9`(blob `f7c9431a`)로 바꿔 고정한다. 위 표의 `a9518c65`는 실행 전 감사 대상 판이다. 바뀐 것: D-h 키 `line["d1_key"]` 그대로(하네스만으로 K-SAME 20/20, 고치기 전 K-NA 20/20), V-1 끝 phase를 `phases` 마지막 항목에서 읽음. 시험 `test_b1_creep_metrics.py` `120ef7f6…`. postrun 뒤 병합.
- 실행 전 감사 수정 (b)(c) 반영(2026-11-12 13:00 커밋, Chrono 첫 행 끝나기 전): 경로 2 `b1_path2.py`는 브랜치 `b1-path2-fix` 커밋 `24a108e`(부모 bd64cc4)의 원시 = LF sha256 `7a9d258fa3182506a82fbdca74c15a1b8a37bd7858cf413f959fe0f4f52183db`(blob `32522171`)로 바꿔 고정한다. selftest `6815d960…`, README `ae982a17…`, keymap 변경 없음(`19021bc6`). 바뀐 것: `--identity` 필수 입력(행 ok 거짓 → INVALID), I-11 C6 상부체 질량 기준, 원판 6절 pad_nodes 일치(다르면 그 행 격자 전부 무효), E-5 rc + Traceback(있으면 BLOCKED_E5), D-b SGS 행 제외, 규칙·rev1·P7_REF sha 대조. 실행 명령에 `--identity <배치 폴더>\B1_identity.json`을 더한다. postrun 뒤 병합.
- 실행 직전에 같은 표를 RUN_HEAD checkout에서 다시 재서, 다르면 실행하지 않는다: 3절 14파일 원시·LF sha 다시 잼, 14/14 같음(2026-11-12 12:49, 메인 세션 scratchpad\main\b1_recheck.py rc 0).

## 4. 하네스 32실행 (원판 2.2, I-9, E-1)

| 항목 | 값 |
|---|---|
| 명령 | dynamics-dev `python.exe -I -B 04_scripts\03_control\b1\b1_harness.py --workers 8 --mask 0x00FF0000`, env `OUTRIGGER_LOC_SHADOW=1` |
| 출력 | `06_analysis/03_hydraulic/coupled/v5/b1/b1_H.jsonl` + `npz/` |
| jsonl sha256 | `a7099db61b58198c9e9b7975b02c5641a8bbe04b695eec6ae9f0abcf174fc2f7`(원시 바이트) |
| jsonl sha 대조 기준 | **파일을 직접 해시한 원시 바이트 값**이다. identity 파일 `b1_H.jsonl.identity.json`(sha256 `08d1cf0321068e687326dec7debb276b41fd8c237654540d56bf984940874c88`)에는 출력 jsonl의 sha 필드가 없다(러너 identity 형식이 checkout·도구·env만 적는다). 그래서 rev1 4절 3번의 "identity 파일의 값 확인"을 직접 해시로 대신했다(공개) |
| identity | 시작·끝 HEAD `7246c19a1aec6cfe9a6ba3b2f571a789fcf38912`, 둘 다 깨끗함, errors 0, exit 0 |
| 줄 | 32(H-P 20, H-W 4, H-M0 4, H-SH0 4), 오류 줄 0, E-1 거부 0 |
| 정체성 점검(python-expert, 2026-11-12, 값 출력 없음) | 태그 1.1 값 일치 32/32, 규칙 sha 6b99702c 32/32, H-M0 `B1MarginZeroC2Controller`·`margin_m` 0·`enable` 참 4/4, H-M0 margin 사건 이름은 `INFO_LOC_CLEARANCE_MARGIN`뿐(R4c30 0), 그림자 켬·끔 표시와 기록 일치, H-W 플랜트 질량 배율 1.1, R-10 연속 Bekker 32/32, npz sha 32/32, R-C1 6키 + `stroke_read_m`·`sink_m` 32/32. 문제 0건 |
| 그림자 짝(H-SH0) | C1·C2·C4·C5 모두 `same`(all same) → M-12 하네스 그림자 기록 사용 가능 |
| 명령 불변 확인(구현 때) | J1 flat 프로브에서 수정 전 HEAD 트리 = 기록 훅만 = 기록 훅 + 그림자 = 명령 해시 `6850d2a2…` |

## 5. 상수 (원판 7.3 + rev1 4절)

| 항목 | 값 |
|---|---|
| 경로 1 상수 파일 | `06_analysis/02_control/b1/b1_harness_constants_rev1.json`, sha256 `3d35a1d81a7c4c4a2e4a40d9c2e3c498753dc0e674fe41491e57007ec52f5ffe`, blob `95c114c86890824fb01b1edc5337b5d3436a415b`(master `bd64cc4`) |
| 계산 명령 | python-dev `python.exe -I -B 06_analysis\02_control\b1\b1_creep_metrics.py constants --harness C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\b1\b1_H.jsonl --out 06_analysis\02_control\b1\b1_harness_constants_rev1.json`(도구 sha a9518c65, 입력 jsonl a7099db6) |
| 경로 2 상수 파일 | sha256 `3b5e775b…`(전체 값 `3b5e775b3542f8f1efeb8033f894c4f765944358db73f389d3bb8996b454665c`(메인 세션 채움), 경로 `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\b1p2-3b7d1e\b1_constants_path2_rev1.json`(경로 2 작성자 scratch, 메인 세션 채움) — 경로 2 쪽 칸, 이 작성자는 열지 않음) |
| 두 경로 대조(rev1 4절 5번) | 메인 세션 확인: 상대 차 ≤ 2e-14, 적합 다리 목록 일치 |
| 옛 상수 파일 | `b1_harness_constants.json`(sha256 `0dd09ad0…`, 원판 Ŵ 정의) — rev1로 대체, 판정에 쓰지 않음(보관) |

## 6. I-17 (원판 1.2 CR-1)

| 항목 | 값 |
|---|---|
| 명령 | python-dev `python.exe -I -B 06_analysis\02_control\b1\b1_preset_dump_diff.py run --repo C:\workspace\outrigger_control --python C:\ProgramData\miniforge3\envs\python-dev\python.exe --out <scratch>\b1_i17_diff.json` |
| 결과(2026-11-12, HEAD `bd64cc4` 대 `e67dae84e75a3adffdcaf979a237e580d3393d81`) | `i17_ok` true, 위반 0, 공통 필드 409(모두 같음), 새 필드 6(`touch_creep_latch.*`, 모두 클래스 기본값), 지워진 필드 0. 출력 sha256 `190341e78d1488d6705b7916c833cdd5b6ea384976e52521c591dd41f7cf95bb`(scratch, 보관 안 함) |
| RUN_HEAD에서 다시 | RUN_HEAD가 `bd64cc4`와 다르면 같은 명령을 다시 돌려 적는다: 불필요(RUN_HEAD = bd64cc4) |

## 7. G-S 건조 실행 (원판 2.3, I-16)

| 항목 | 값 |
|---|---|
| Chrono 배치 | `07_results/S9/batch_V5-B1-CREEP-GS_20261112_112555`: C1 꼴 `B1_J2_B_bottom_Fs4_VB_fdown`, C6 꼴 `B1_J2_B_bottom_Fs4_m1p1_VB_fdown`, `--duration 10`, 2/2 rc 0(`batch.json`), gs-check ok(메인 세션 확인) |
| 하네스 | H-P VB e0·H-M0 꼴은 하네스 32실행의 같은 꼴 줄로 필드를 확인했다(4절 점검) |
| 시각 | 2026-11-12T11:25:55(배치 `progress.log` 첫 줄, 메인 세션이 옮김) < 2026-11-12T12:51:34+09:00(러너 status.txt) |

## 8. 실행 전 점검 표 (원판 4.1 I-1~I-17, 2.4, 6절)

| 코드 | 내용 | 상태 | 근거·채울 곳 |
|---|---|---|---|
| I-1 | 실행 커밋 = `HEAD_M`, checkout 깨끗함 | 실행 때 | RUN_HEAD, 빈 출력(러너 status.txt)(`git status --porcelain --untracked-files=no` 빈 출력) |
| I-2 | 6행 argv = 2.1 표 = 전개 argv, sha256 | 실행 때 | 행 모듈 `b1_creep_chrono_rows.py`(LF 4e1b214a…)가 전개한다. batch.json cases[].argv(level부터) sha = 실행 전 감사 기대값 6/6 일치(C1 af7d176e, C2 80c074e4, C3 1dfd69db, C4 4f3506e1, C5 8e0c4c8f, C6 c6f2ee1b; postrun 메인 세션) |
| I-3 | `--expect-controller final_C4G2_P3_LAS_K1`, `expect_controller.ok` 참, 클래스 `C2Controller` | 실행 뒤 | 경로 1이 result.json에서 직접 확인(`chrono_identity_checks`) |
| I-4 | `num_threads_chrono` = 4 | 실행 뒤 | 경로 1 직접 확인 |
| I-5 | 자식 env `OMP_WAIT_POLICY=PASSIVE` | 실행 뒤 | `batch.json`(배치가 넣음) |
| I-6 | 풀 = 배치표 행별 풀 | 실행 뒤 | 배치표 sha 3d3b0117…, `batch.json` `pool` |
| I-7 | hull hook fast, DLL sha = `HULL_DLL_SHA`, `MIXED_HULL_MODE` 없음 | DLL 확인함, result는 실행 뒤 | DLL 원시 sha cec997d7 일치(3절). 셸에서 `OUTRIGGER_HULL_HOOK*` 제거(9절) |
| I-8 | params 지문 = YAML sha | 실행 뒤 | YAML ef2880f9…(3절) |
| I-9 | 하네스 32실행 정체성 | **확인함** | 4절 |
| I-10 | 시작 직전·끝난 직후 HEAD·status 같음 | 실행 때 | bd64cc405990101ca8f3398ba2b9db9edcfc01b4, bd64cc405990101ca8f3398ba2b9db9edcfc01b4(러너 status.txt, 시작 전과 같음), 빈 출력(러너 status.txt) |
| I-11 | C6 제어기 질량 명목, 플랜트 ×1.1 | 실행 뒤 | 경로 1 직접 확인(W_ref / YAML 질량 = 9.80665, `args.mass_scale` 1.1) |
| I-12 | 러너 로그 `errors N`, `errors_left` | 실행 뒤 | `tools/verif/log_errors.py <배치 폴더>` 종료 0 → identity JSON `runner_log` |
| I-13 | 추적 파일에 `{이름}` 자리표시 없음 | 실행 전 | 이 파일의 자리표시는 중괄호 없이 썼다. `placeholder_scan.py --allow b1_creep_prelaunch_draft.md` 결과 placeholder_scan.py b1_creep_prelaunch.md 종료 0, unfilled 0(채운 뒤 다시 돌림) |
| I-14 | 지운 env·더한 env, 인터프리터 플래그 | 실행 때 | 9절 명령 그대로, Chrono-dev python.exe -I -X utf8 -u, 러너 pwsh(실제 경로) WMI 분리 실행, 셸에서 OUTRIGGER_HULL_HOOK·_ALLOW_UNVALIDATED·_DLL·OUTRIGGER_LOC_SHADOW 제거(env_before.txt 기록), 러너 06_analysis/03_hydraulic/coupled/v5/b1/run/ |
| I-15 | 실제 argv·rc를 `batch.json`에 | 실행 뒤 | `batch.json cases[].argv`·`rc` |
| I-16 | G-S 기록이 본 실행보다 앞섬 | 실행 때 | 7절 2026-11-12T11:25:55 < 2026-11-12T12:51:34+09:00(러너 status.txt) |
| I-17 | 프리셋 덤프 대 `e67dae8` | **확인함**(bd64cc4) | 6절 |
| 2.4 겹침 표 | 칸별 코드 줄 확인(cad-expert·python-expert) | 부분 | python-expert 칸: H-M0 `enable` 유지 + `margin_m` 0(하네스 meta로 확인), `OUTRIGGER_LOC_SHADOW`는 하네스만(H-SH0 해시 짝 same), 기록 훅 명령 불변(프로브 6850d2a2). 확인자·시각 python-expert 2026-11-12. cad 칸(`v5_vb_argv()`만 사용·`v5_vb_rows()` 미사용, `--start-limit record_only`, `--mass-scale 1.1`, 격자 기록 읽기 전용): cad-expert 칸별 확인 기록 없음. 대신 실행 전 감사 차단 0, I-2 전개 argv sha로 배치 prelaunch에서 대조(메인 세션 기록) |
| 6절 T-10 비용 | 격자 기록 켬/끔 벽시계 비 ≤ 1.05 | **확인함**(메인 세션 전달) | 비 0.993, 통과 |
| 6절 비트 동일 | 기록 켬·끔 `step_series.npz` 비트 동일 | **확인함**(메인 세션 전달) | 측정 폴더·명령 cad-expert 짝 실행 2회(커밋 d8fd457·a813066): 명령 `scratchpad\cad-b1\pair_run.ps1`(E 0x0FFF0000, OUTRIGGER_PLACEMENT=ecore, PASSIVE, C1 꼴 10 s, 끔 vs `--b1-grid-record full` 동시), 대조 `scratchpad\cad-b1\compare_pair.py`, 폴더 `scratchpad\cad-b1\pair\`·`pair2\`; step_series 5b8c63a3·record eeef5d2b·controller_commands 343bf6a2·r8_series a0f8f972 켬·끔 같음, 벽시계 비 0.996·0.993(메인 세션 채움)(cad-expert) |
| 실행 전 감사 | verif-protocol-auditor, 차단 0 | 실행 전 | 06_analysis/02_control/b1/b1_creep_prerun_audit.md, 7e22898aca20a1c0f4382df921aa7f461a32dc477e0de4b3993f8aace31b6606, 0 |

## 9. 본 Chrono 6행 명령 (원판 2.1, 1.3)

PowerShell, RUN_HEAD checkout 루트에서. P코어 4병렬은 배치표가 정한다.

```powershell
Remove-Item Env:OUTRIGGER_HULL_HOOK -ErrorAction SilentlyContinue
Remove-Item Env:OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED -ErrorAction SilentlyContinue
Remove-Item Env:OUTRIGGER_HULL_HOOK_DLL -ErrorAction SilentlyContinue
Remove-Item Env:OUTRIGGER_LOC_SHADOW -ErrorAction SilentlyContinue
# OMP_WAIT_POLICY=PASSIVE 는 s9_batch 가 자식 env 에 넣는다 (셸에서 따로 두지 않음)
git rev-parse HEAD                                   # -> bd64cc405990101ca8f3398ba2b9db9edcfc01b4
git status --porcelain --untracked-files=no          # -> 빈 출력(러너 status.txt) (빈 출력이어야 함)
C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I 04_scripts\02_chrono\s9_batch.py run V5-B1-CREEP --schedule C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\b1\schedule_main.json
git rev-parse HEAD                                   # -> bd64cc405990101ca8f3398ba2b9db9edcfc01b4(러너 status.txt, 시작 전과 같음)
git status --porcelain --untracked-files=no          # -> 빈 출력(러너 status.txt)
```

- 6행(12행 아님): C1~C6, P 4병렬. 출력 `07_results/S9/batch_V5-B1-CREEP_BATCH_STAMP/`.
- 인터프리터 경로·플래그는 실제 실행 명령대로 메인 세션이 Chrono-dev python.exe -I -X utf8 -u, 러너 pwsh(실제 경로) WMI 분리 실행, 셸에서 OUTRIGGER_HULL_HOOK·_ALLOW_UNVALIDATED·_DLL·OUTRIGGER_LOC_SHADOW 제거(env_before.txt 기록), 러너 06_analysis/03_hydraulic/coupled/v5/b1/run/에 적는다(`-I` 포함).

## 10. Chrono 뒤 재집계 (원판 9절: postrun → 경로 2 → 경로 1 → K-R)

### 10.1 `--identity` 입력 JSON 만들기 (경로 1 judge 입력)

배치 폴더에 `B1_identity.json`을 쓴다(추적 밖). 꼴:

```json
{
  "rows": {
    "C1": {"ok": true, "rc": 0, "reasons": []},
    "C2": {"ok": true, "rc": 0, "reasons": []},
    "C3": {"ok": true, "rc": 0, "reasons": []},
    "C4": {"ok": true, "rc": 0, "reasons": []},
    "C5": {"ok": true, "rc": 0, "reasons": []},
    "C6": {"ok": true, "rc": 0, "reasons": []}
  },
  "runner_log": {"errors_total": 0, "errors_left": 0}
}
```

- `rc`: `batch.json` `cases[].rc`(행 이름 = 원판 2.1 사례 이름). 빠지면 경로 1이 `batch.json`에서 다시 찾는다.
- `ok`: 그 행의 I-1, I-2, I-5, I-6, I-8, I-10, I-12, I-13, I-14, I-15, I-16, I-17이 모두 참이면 true(실행 전 감사·postrun 결과로 메인 세션이 정함). 하나라도 거짓이면 false로 두고 `reasons`에 코드를 적는다. I-3·I-4·I-7·I-11은 경로 1이 result.json에서 따로 확인한다.
- `runner_log`: E-5. 이 배치 로그에는 `errors N` 줄이 없으므로(실행 전 감사 기록) 경로 2와 같은 정의로 채운다: `errors_total` = `errors_left` = 최종 `<case>.log`에 `Traceback`이 있는 행 수, rc는 `batch.json`. `log_errors.py` 출력은 참고로 함께 적는다(재감사 2026-11-12 반영, 결과 전).
- 위 값은 꼴 예시다. 실제 값은 postrun에서 채운다.

### 10.2 경로 2 (먼저)

- 경로 2 실행 전에 브랜치 `b1-path2-fix`(24a108e)를 병합하고 main checkout `b1_path2.py` sha가 `7a9d258f…`인지 확인한다. K-R 대응표 `06_analysis/02_control/b1/b1_kr_map.md` sha256 `d0f30e15223785934f1435ac1900a6d1e3ca124256f6e4777d2a3545de6601c8`(verif-protocol-auditor, 2026-11-12T13:10, 결과 전, 본 배치 미열람). 결정 덧붙임 `b1_kr_map_decisions.md` sha256 `1c00dc7502f0f586e236bcfab320852858403e88103b25c562e689476263e186`(U-01~U-12·K-93 K-R 제외, 제안 허용값 채택). 도구 재감사 원문 `b1_creep_fix_reaudit.md`(차단 0).

- 명령, 출력 sha, 실행 시각: `cmd /c "start /b /wait /affinity 00FF0000 C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B C:\workspace\outrigger_control\06_analysis\02_control\b1\path2\b1_path2.py --repo C:\workspace\outrigger_control --batch <B1 배치> --harness-jsonl C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\b1\b1_H.jsonl --p7-ref C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\soil_defer\s2d_SC.jsonl --keymap C:\workspace\outrigger_control\06_analysis\02_control\b1\path2\b1_keymap.json --identity C:\workspace\outrigger_control\07_results\S9\batch_V5-B1-CREEP_20261112_125134\B1_identity.json --constants-out C:\workspace\outrigger_control\06_analysis\02_control\b1\b1_constants_path2_rev1.json --out C:\workspace\outrigger_control\06_analysis\02_control\b1\b1_metrics_path2.json"`(경로 2 작성자 제공, 메인 세션 채움), 5c3185c4930ec6f9f4a1a013a12266cb7680299071ead8120c623b9165949e35, 2026-11-12T17:27:18~17:27:24+09:00(worktree b1-path2-fix 24a108e에서 실행, --repo = 그 worktree, --keymap 그 worktree, --identity 배치 폴더, --constants-out 이름을 b1_constants_path2_rev1_run.json으로 바꿈(scratch 판과 섞이지 않게), 종료 0, 묶음 COMPLETE)(경로 2 README대로, 이 작성자는 열지 않음). 경로 2 출력 sha가 경로 1 실행보다 앞서야 한다(판정 후 감사 T).

### 10.3 경로 1 judge

python-dev, RUN_HEAD checkout 루트에서:

```powershell
C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B 06_analysis\02_control\b1\b1_creep_metrics.py judge `
  --chrono-batch 07_results\S9\batch_V5-B1-CREEP_BATCH_STAMP `
  --harness 06_analysis\03_hydraulic\coupled\v5\b1\b1_H.jsonl `
  --identity 07_results\S9\batch_V5-B1-CREEP_BATCH_STAMP\B1_identity.json `
  --constants 06_analysis\02_control\b1\b1_harness_constants_rev1.json `
  --p7-ref 06_analysis\03_hydraulic\coupled\v5\soil_defer\s2d_SC.jsonl `
  --out 06_analysis\02_control\b1\b1_metrics_path1.json
```

- 종료 0 = COMPLETE/PARTIAL, 1 = UNDETERMINED 또는 E-5 차단, 2 = 입력 오류(규칙 sha 불일치, 상수 파일이 jsonl에서 다시 계산한 값과 다름, 격자 간격 없음 포함), 3 = E-6. stdout 마지막 줄 JSON에 출력 sha가 있다.
- 경로 1 출력 sha, 실행 시각: 6ad863abd3933e7f9353197bcd1af811188559722e76d69210dd80d47c336ee5, 2026-11-12T17:27:38~17:27:41+09:00(worktree agent-a54833748c3f6b37d 1ac4849에서 절대 경로로 실행, 종료 0, 묶음 COMPLETE). 경로 2 출력 sha가 경로 1 실행보다 앞섬.

## 11. 끝난 뒤 채울 칸

2026-11-12T12:51:34+09:00(러너 status.txt), 2026-11-12T17:15:51+09:00(러너 status.txt, exit=0; progress.log finished 17:15:50 failed=False), 20261112_125134, bd64cc405990101ca8f3398ba2b9db9edcfc01b4(러너 status.txt, 시작 전과 같음), 빈 출력(러너 status.txt), 6/6 있음(`cases[].argv`·`rc`), 0, 0, 재실행 기록(`rerun_of`, `attempt1/` 경로) 재실행 없음.

## 11. postrun 기록 (메인 세션, 2026-11-12 17:30)

- 6행 rc 0(progress.log END 6줄, batch.json failed=False, mixed_hull_mode False). 벽시계 C4 8356 / C1 8438 / C2 8772 / C5 8898 / C3 6649 / C6 7499 s.
- I-1·I-10: 러너 status.txt HEAD bd64cc4 시작 = 끝, status 빈 출력 둘 다. 실행 중 master 커밋 0.
- I-2: 6/6 일치. I-5: omp_wait_policy PASSIVE 6/6. I-6: pool pcore 6/6, 배치표 sha 3d3b0117 같음. I-8: result.json `meta.pad_variant.pad_variants_params_file_sha256` = YAML ef2880f9 6/6(`meta.params_sha256`는 오거 단계별 파라미터 묶음 지문이라 단계마다 다름, 판정 대상 아님). I-15: batch.json argv·rc 6/6. hull_hook_effective mode fast 6/6.
- 필드 점검: `b1_creep_chrono_rows.py gs-check <배치>` 종료 0(존재·키·pad_nodes 일치 6/6, 값 출력 없음).
- E-5: 최종 `<case>.log` Traceback 0행 → runner_log errors_total = errors_left = 0. 참고 `log_errors.py` 종료 0, errors 줄 없음 7로그.
- 정체성 입력 `07_results/S9/batch_V5-B1-CREEP_20261112_125134/B1_identity.json` sha256 2a4a46624d05466bfa6ff1123bc2af1c4869ef7aba234d827f3261a2523c10b5(6행 ok 참). 만든 스크립트 scratchpad\main\b1_postrun.py.
- 판정 도구: 고정 sha 판을 각 worktree에서 실행한다(경로 2 `.claude/worktrees/b1-path2-fix` 24a108e, 경로 1 `.claude/worktrees/agent-a54833748c3f6b37d` 1ac4849). 병합은 판정 뒤 커밋 때.
