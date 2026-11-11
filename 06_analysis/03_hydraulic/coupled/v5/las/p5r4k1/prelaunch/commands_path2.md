# P5r4+K1 경로 2 판정 실행 명령 (control-expert 작성, 메인 세션 옮김 2026-11-11)

경로 2 작성자(control-expert)가 리포트로 준 명령을 메인 세션이 그대로 옮겼다. 경로 1 `commands.md`와 따로 둔다.

## 고정값 (master a916e04, rev3 반영 `0ec945b`)

| 파일 | git blob | sha256 (LF, `-text`) |
|---|---|---|
| `06_analysis/02_control/verif_matrix/p5k_path2/p5k_recount.py` | `1b85aacca3b74e01cf5223c7f45b8962edbcbba7` | `5c827f2f9b04e673b3f0622f419c20d356fe3be9bd4e26f379bd4d094b3f30bf` |
| `.../p5k_path2/p5k_chrono_recount.py` | `8888336ec58a736b9b637583d69636f98e897232` | `e3cb1c4addd1d7732fd847e57a246b1f141ad3dc7a0c74c1120cdcde9429f080` |
| `.../p5k_path2/test_p5k_recount.py` | `1f00d1eddabaff85189d7139e0b602d664eb2db3` | `34e75af45054c12bf619b2be01078d0350a3dea675e53c90843511fd26950dd7` |

규칙 blob: 원판 `c8688da4`, rev1 `7219a46d`, rev2 `2762b402`, rev3 sha256 `31ba01dff9defb4b7274b27b9df1a427c460fa9ccc5efd84f5a3145e0d3ef8f6`(재봉인 `0827c8f`; 첫 봉인 `5798dd32`은 쓰지 않음). `0ec945b`에서 경로 2 시험 53/53 통과(control-expert 확인). 이전 판(master 8f0150a, 시험 40) 값은 rev3 전 기록이다.

## 공통

- 인터프리터: `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B`(env 활성화 불필요). 셸 env `MKL_THREADING_LAYER=TBB`.
- cwd: `C:\workspace\outrigger_control`(인자는 모두 절대경로).
- 실행 직전: main checkout 두 도구 파일 `Get-FileHash`가 위 sha256과 같아야 함. 다르면 실행하지 않음(원판 10.2). 규칙 세 파일과 `.sha256`은 같은 폴더(K-0이 대조).
- 자리표시는 `{BATCH_CHRONO}` 하나(16.4). prelaunch는 실행 HEAD 커밋에서 git 추적을 해제하고 추적 밖에서 채운다(rev3 RV3-3).
- 출력 폴더 `06_analysis\02_control\verif_matrix\p5k_judge\`(메인 세션이 만듦).
- 종료 코드: 0 통과(잠정, `k10: null`), 1 미달·판정 불가, 2 stop, 3 도구 오류. 기대 0(사전 예측 P-14). 3이면 도구를 고치지 않고 멈추고 보고(고치면 독립성 공개 필요).
- E코어(선택): `cmd /c "start "p5k_path2" /b /wait /affinity 0FFF0000 <명령>"`.

## (1) 하네스 `p5k_recount.py`

시점: 하네스 Z-0~Z-X가 끝나고 16.3 `errors_left`·16.4 자리표시 관문 통과 뒤.

```
C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\p5k_path2\p5k_recount.py --run-dir C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\las\p5r4k1 --v5-dir C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5 --rules C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\las_p5r4_k1_rules.md --rules-rev1 C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\las_p5r4_k1_rules_rev1.md --rules-rev2 C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\las_p5r4_k1_rules_rev2.md --rules-rev3 C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\las_p5r4_k1_rules_rev3.md --gs-dir C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\las\p5r4k1\gs --out C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\p5k_judge\path2_harness.json
```

- 입력: `--run-dir` 아래 묶음마다 `p5k_<묶음>.jsonl` 정확히 하나(`p5k_Z-0`·`p5k_Z0`·`p5k_Z_0` 꼴). 다르면 `--bundle Z-0=<절대경로>`.
- 출력: `path2_harness.json`, stdout 끝 줄 JSON `{status, errors_total, errors_left, bundles, out}`.

## (2) Chrono `p5k_chrono_recount.py`

시점: Chrono 본 배치 `V5-LAS-P5R4-K1` 끝난 뒤(하네스 `통과` 때만 돈 배치, S-6).

```
C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\p5k_path2\p5k_chrono_recount.py --batch {BATCH_CHRONO} --rem-batch C:\workspace\outrigger_control\07_results\S9\batch_V5-LAS-K1-REM_20261109_235554 --rules C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\las_p5r4_k1_rules.md --rules-rev1 C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\las_p5r4_k1_rules_rev1.md --rules-rev2 C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\las_p5r4_k1_rules_rev2.md --rules-rev3 C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\las_p5r4_k1_rules_rev3.md --out C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\p5k_judge\path2_chrono.json
```

- `{BATCH_CHRONO}` = `C:\workspace\outrigger_control\07_results\S9\batch_V5-LAS-P5R4-K1_<시각>`(절대경로).
- `--rem-batch`는 BT-C 기준 REM R7·R8 npz 폴더(sha `ebf86d1d…`·`97aace61…` 도구가 대조).
- 출력: `path2_chrono.json`, 끝 줄 JSON `{status, errors_total, errors_left, out}`.
- G-S 배치(`--duration 10`)에는 쓰지 않음(K-7 stop). G-S 필드 점검은 `gs-check`.

## (3) 단위 시험(선택)

```
C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B -m pytest -q -p no:cacheprovider --basetemp <scratch 폴더> C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\p5k_path2\test_p5k_recount.py
```

기대 `53 passed`, 종료 0.
