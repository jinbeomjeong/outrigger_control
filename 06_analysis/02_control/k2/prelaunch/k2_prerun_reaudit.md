<!-- verif-protocol-auditor 리포트 원문(2026-11-10, 실행 전 재감사). 대상: K-2 _TCL V-2~V-7, master 6d11d13, k2-run 6a44ff8. 메인 세션이 편집 없이 저장. -->

**차단 0건, 실행 전 수정 3건, 확인 필요 3건** (기록 9건)

## 감사 요약
- **대상**: K-2 `_TCL` V-2~V-7 본 실행 전 재감사입니다. 첫 감사 원문은 `06_analysis/02_control/k2/prelaunch/k2_prerun_audit.md`입니다.
- **기준 문서**: 6판 모두 raw 해시가 `.sha256` 첫 토큰과 같고, LF, BOM 없음, `-text`입니다.
  - 원판 a3658197
  - rev1 5ba081c6
  - rev2 b3f1b41f
  - rev3 8bcdb0ed
  - rev4 82160ff5
  - rev5 73b87758
  - dyn 명세 502b0bb7
  - criteria.md: blob 86aa6242 @6a44ff8, LF a7363e16, k2-run 사본 a392730f
- **상태**: master 6d11d13, 실행 checkout k2-run은 6a44ff8(locked)입니다. 추적 파일 변경 0, 결과 0건입니다(`k2-run\06_analysis\02_control\k2\runs` 없음, `07_results` 아래 k2 폴더 없음).
- **판정**: 차단 0 / 실행 전 수정 3 / 확인 필요 3 / 기록 9.
  - 실행 자체(명령·마스크·입력·봉인·고정값)는 규칙대로 준비돼 있습니다. **실행을 시작해도 결론이 틀어지는 경로는 찾지 못했습니다.**
  - 실행 전 수정 1·2는 V-5가 실패할 때만 드러나는 두 경로 간 차이와 절차 위험입니다. 어느 쪽도 거짓 통과를 만들지 않고, G-F 판정 불가 쪽으로 보수적으로 끝납니다.
  - 다만 경로 2는 결과 뒤에 고칠 수 없습니다(규칙 8). 고치려면 **시작 전에** 고쳐야 합니다(확인 필요 1·2).

## 첫 감사 항목 처리 상태

| # | 항목 | 상태 | 근거 |
|---|---|---|---|
| 차단 1 | V-5 절대 항목 | **닫힘** | rev2 1절 표(`rev2.md:14-23`). 경로 1 `v5_absolute`·`_absolute_d8`(`k2_judge.py:1109-1210`). 경로 2는 원 출력을 직접 읽습니다(`k2_recount.py:987-1376`, 평탄 파일 미사용, manifest `v5_raw`). 판정 종류(실패/불가) 차이는 새 발견 1 |
| 차단 2 | V-6 SH-1~6 | **닫힘** | rev2 3절. 경로 1 `chrono_sh`(`k2_judge.py:1534-1574`), 경로 2 `v6_shadow`(`k2_recount.py:1452-1520`). SH-2는 팔마다 4값, SH-5 = CAP + L1 거짓 래치, SH-6의 J2는 H4 행만(rev5 4)이고, 결측은 FLAG로 셉니다. 두 경로가 같습니다 |
| 수정 3 | E-5·I-9 | **닫힘** | rev2 4절·rev3. 값·키 집합·cn 배수·열림 비율이 두 경로에서 같습니다(`k2_judge.py:803-914`, `k2_recount.py:425-493`). V-6 L1 켬 0.10 / L2b 끔 None도 두 경로 같습니다(`k2_judge.py:1505-1519`, `k2_recount.py:483-493`) |
| 수정 4 | V-5 K-2 켬 증거 | **닫힘** | rev2 1절·rev5 1~2. provenance 14단계 + d8 meta, G8 행 필드, 사건 4파일을 두 경로가 모두 봅니다. 결과 등급 차이는 새 발견 1 |
| 수정 5 | 실행 전 기록 누락 | **부분 열림** | 키 목록 sha(v2 1bc5076d, v4 f243dc30, V-5 7묶음), V-6 시작 상태(L1R 4파일 sha, L2b in_run_settle과 blob), criteria sha는 기록되고 실측과 같습니다. **G-S 근거(9.2, I-4 축소, I-5, I-8) 기록은 여전히 없습니다** → 새 실행 전 수정 3 |
| 수정 6 | 러너 순서 | **닫힘(절차)** | README 8절, rev2 5절, `k2_prelaunch_v5.json` `launch_order`. 러너는 바뀌지 않았으므로(sha 일치) 메인 세션이 이 순서로 띄워야 합니다 |
| 수정 7 | 경로 1 봉인 대조 | **닫힘** | `SEALED_RULES` 원판~rev5 + 명세(`k2_judge.py:62-69,170-182`). 경로 2는 `--rules-dir`를 줄 때만 대조합니다(인자는 여전히 선택). README 9절 명령(`README.md:165`)에 들어 있습니다 |
| 수정 8 | 경로 1 SH 결측 | **닫힘** | `_sh_row_flags`·`sh_flags`가 결측 수를 세고 FLAG로 냅니다(`k2_judge.py:528-603`) |
| 수정 9 | 판정 후 정체성 목록 | **닫힘** | rev2 6절 1~6 |
| 기록 a | 25 / 49 | 닫힘 | `k2_prelaunch_v5.json:148`, README 3절, expect note |
| 기록 b | criteria sha | 닫힘 | rev2 1절, prelaunch `criteria_md`(실측 일치) |
| 기록 c | I-4 저장 행 sha 재확인 | 판정 후 감사로 넘김 | rev2 6.6. 지금 main의 `ra_off` 100985bf, `ra_on` e3c8c95f는 실측과 같습니다 |
| 기록 d | H_impl = M | 닫힘 | rev2 7절 |
| 기록 e | V-7 Job 메모리 | 열림 `[추정]` | 바뀐 것 없음 |
| 기록 f | `gate_scan --no-git` | 열림 | 지금도 종료 2 `unrecognized arguments: --no-git` |
| 확인 필요 1 | 회귀 118 ↔ 93/49 | 닫힘 | rev2 2절, rev4 1 (c) |
| 확인 필요 2 | V-6 E코어 | 사용자 결정으로 기록됨 | rev2 5절(결정 자체는 확인할 수 없음) |
| 확인 필요 3 | 이상적 센서 1단계 | 닫힘 | 96781b6(17:48:56)이 6a44ff8의 조상입니다(`merge-base --is-ancestor` 0) |
| 확인 필요 4 | L2b 시작 상태 | 닫힘 | rev2 7절. `run_S7C.py` b2b4458b, `run_S8C.py` cec2c696가 6a44ff8 인덱스와 같습니다. `CRAWLER_SETTLE_S = 3.0`(`run_S7C.py:93`), `check_settle`(`run_S8C.py:1385`) |

## 발견 사항 (심각도순)

**[실행 전 수정][R·E] 1. 경로 1·2가 V-5 몇 항목에서 판정 종류나 적용 팔이 다름 (rev5 정렬 뒤에도 남음)**
- 근거(항목별)
  - **K-2 증거 위반**
    - rev2: "하나라도 어기면 그 묶음은 판정 불가다"(`rev2.md:25`).
    - 경로 1은 판정 불가로 처리합니다(`k2_judge.py:1361-1363,1423-1424`).
    - 경로 2는 `_Tally.bad`로 넣어 G-D **fail**로 처리합니다(`k2_recount.py:1312-1349,1360-1362`).
  - **짝 없는 키**
    - rev2 표에서는 "끔 팔 대비" 칸의 기준입니다("짝 없는 키 0", `rev2.md:17-18,21`).
    - 경로 1은 판정 불가(`k2_judge.py:1364-1365`), 경로 2는 fail(`k2_recount.py:1005-1006,1037-1038`)입니다.
  - **격자 768건 확인(E-1)**
    - 경로 1은 manifest `count` 768로 두 팔을 셉니다(`k2_judge.py:1419-1422`, `k2_manifest.json:106`).
    - 경로 2 `_v5_grid`에는 건수 검사가 없습니다(`k2_recount.py:987-1008`). `recount_v5_raw`도 expect의 V-5 건수를 읽지 않습니다(`:1353-1376`). 두 팔이 같이 행을 잃어도 경로 2는 통과합니다.
  - **끔 팔 sidecar rc**
    - rev5 3: "실행 단계 36개와 r79 판정 단계 4개에 적용"(`rev5.md:30`). 즉 두 팔 모두입니다.
    - 경로 2는 두 팔을 다 봅니다(`k2_recount.py:1278-1290`).
    - 경로 1은 끔 팔을 `off_record`로 기록만 하고 판정에는 넣지 않습니다(`k2_judge.py:1355-1360`).
  - **회귀 verdict 결측**
    - 경로 2는 결측으로 세어 fail입니다(`k2_recount.py:1185-1187`).
    - 경로 1은 평탄화기에서 `bool(is_good(None))` = False가 되어 결측으로 세지 않습니다(`k2_v5_flatten.py:237`).
- 실패 시나리오: 위 항목 가운데 하나가 실제로 일어나면 G-D가 경로 1 `not_judgeable`, 경로 2 `fail`로 갈립니다. 그러면 규칙 8에 따라 G-F가 판정 불가입니다.
  - 등급은 어느 쪽이든 판정 불가(가장 엄한 쪽)라 거짓 통과는 없습니다.
  - 그러나 규칙 8은 고정 뒤 경로 2를 고치면 판정 불가라고 합니다. 그래서 결과 뒤에 이 차이를 풀 길이 없고, 미달이어야 할 경우가 판정 불가로 굳습니다.
- 권장 조치(둘 중 하나, 확인 필요 1)
  - (a) 시작 전에 고칩니다. 담당은 python-expert(경로 1)와 control-expert(경로 2)입니다. 다음을 rev6 봉인과 새 blob 실행 전 기록으로 맞춥니다.
    - 경로 2: K-2 증거와 짝 없는 키를 rev2대로 분류하고, 격자 768 건수를 확인
    - 경로 1: 끔 팔 rc를 판정에 넣고, 회귀 verdict 결측을 셈
  - (b) 그대로 시작하고, 판정서에 "이 다섯 항목은 G-F에서 판정 불가로 끝난다"를 미리 적습니다.

**[실행 전 수정][I·T] 2. P_post의 참고용 옛 평탄화기 단계가 "sidecar 62개 rc = 0" 조항 안에 있고, 필요한 단계보다 먼저 돎 `[추정]`**
- 근거
  - **단계 순서와 멈춤**
    - P_post 순서는 `v5_judge_r79_L1L2_off` → `v5_judge_clip_r79_L1L2_off` → **`v5_flatten_off`(k2-run 옛 평탄화기 a83abd80)** → `v5_judge_*_tcl` 2개 → `v5_flatten_tcl`입니다(`sched/steps_P_post.json`).
    - 러너는 실패하면 그 뒤 단계를 시작하지 않습니다(`k2run_P_post.ps1:164-165` "later steps NOT started").
  - **규칙상 효과**
    - rev2 6.1: sidecar 62개 rc = 0, 하나라도 어기면 G-F 판정 불가(`rev2.md:86-88`). rev5 3: "판정 후 정체성 확인은 sidecar 62개 전부를 그대로 본다"(`rev5.md:32`). 62에는 평탄화 단계 2개가 들어 있습니다.
  - **옛 평탄화기가 죽는 지점**
    - 옛 `d8_row_pass`는 `run["min_true_cyl_force_kN"] < GUARD_KN`, `run["ss_true_att_deg_maxabs"] > …`를 감싸지 않습니다(blob a83abd80 153-159행). 값이 None인 D8 행이 있으면 TypeError로 종료 3이 납니다.
    - 새 평탄화기는 바로 이 경우를 `except (KeyError, TypeError)`로 받습니다(`k2_v5_flatten.py:263-269`).
- 실패 시나리오: K-2 팔 D8 행 하나가 READY에 못 가 `ss_true_att_deg_maxabs`가 None이 됩니다(그런 행이 생기는지는 확인 못 함, `[추정]`).
  - `v5_flatten_off`이나 `_tcl`이 종료 3으로 끝나고 러너가 멈춥니다. off에서 죽으면 tcl 쪽 r79 판정 단계 2개(두 경로의 입력)가 돌지 않습니다.
  - 손으로 이어 돌려도 rev2 6.1 때문에 G-F는 판정 불가입니다. 원래는 D8 절대 항목 실패(미달)여야 할 결과가 판정 불가로 바뀝니다.
- 권장 조치(확인 필요 2)
  - (a) P_post에서 두 평탄화 단계를 빼고 새 배치 기록을 남깁니다(compute-scheduler-expert, 러너 sha 갱신).
  - (b) rev6에 "참고용 평탄화 단계 2개의 rc는 rev2 6.1에서 뺀다. 실패하면 남은 tcl 판정 단계를 같은 래퍼 argv로 이어 돌린다"를 적고 봉인합니다(control-expert).
  - (c) 위험을 받아들이고 판정서에 공개합니다.

**[실행 전 수정][I] 3. G-S 조건인 "구현 시험 9.2, I-4 축소·I-5·I-8 통과"의 근거 기록이 아직 없음 (첫 감사 수정 5의 마지막 항목)**
- 근거
  - `k2_prelaunch_v2~v7.json`과 README에 시험 명령·건수·skip 수가 없습니다(`pytest|T-K2|I-5|I-8` Grep: notes의 가정 문장만 나옴).
  - "147개 통과(Chrono-dev, master)"를 보여 주는 파일은 찾지 못했습니다. scratchpad `cad-k2\pytest.log`(18:08)는 "35 passed"뿐이고 대상 시험이 무엇인지 알 수 없습니다.
  - 6a44ff8..6d11d13 사이에 실행 경로(03_src, 02_params, 04_scripts 실행 코드)는 바뀌지 않았습니다. 바뀐 것은 `04_scripts/03_control/k2` 판정 도구 3개와 `05_tests` 4개뿐입니다. 그래서 근거가 유효할 가능성은 큽니다.
- 권장 조치(메인 세션): 시작 전에 다음 기록 한 줄을 실행 전 기록 브랜치에 남기십시오.
  - 시험 명령
  - 인터프리터
  - checkout(6a44ff8인지 master인지)
  - pass / skip 수
  - `test_k2_hashes.py`(T-K2-1, T-K2-2, I-8 G0·R-c)의 skip 0 여부

**[기록]**
- **(a) rev2 1의 공통 항목 결과가 criteria.md와 다릅니다.** criteria.md는 "하나라도 어기면 그 묶음은 판정하지 않고 다시 돌린다"(`criteria.md:9`, 판정 불가에 해당)인데, rev2는 "그 묶음 실패"(`rev2.md:14,16`)로 정했습니다. 결과 전이고 더 엄한 쪽이라 허용 범위입니다. 다만 rev2가 "criteria.md 문구 그대로"라고 쓴 것과는 맞지 않으니 판정서에 적으십시오.
- **(b) 하네스 묶음(V-2·V-3·V-4)의 SH 결측 처리가 다릅니다.** 경로 1은 결측을 세고 FLAG로 냅니다(`k2_judge.py:572,590`). 경로 2 `shadow`는 None을 조용히 뺍니다(`k2_recount.py:660-691`). rev2 3의 결측 규칙은 V-6만 다룹니다. 값이 빠지는 행은 대개 J 항목도 실패하므로 영향은 작고, 달라도 G-F 판정 불가 쪽입니다.
- **(c) 기록 팔 AUG_crc2의 E-5 위반을 다르게 셉니다.** 경로 1은 모든 팔에서 problems로 넣습니다(`k2_judge.py:938`). 경로 2는 판정 팔만 problems로 올리고, 기록 팔은 행 판정 불가로만 둡니다(`k2_recount.py:890-894`).
- **(d) 경로 1이 경로 2 코드를 참조했습니다.** 경로 1 docstring이 경로 2 내부를 가리키고(`k2_judge.py:1473`, `k2_record.py:191`), `false_latches`는 경로 2 `false_latch`와 거의 같은 코드입니다(`k2_judge.py:1488-1502`, `k2_recount.py:286-298`). 규칙 8은 경로 2만 제한하므로 위반은 아닙니다. 다만 같은 실수가 두 경로에 함께 들어갈 수 있습니다.
- **(e) 경로 2의 중간 blob이 기록에 없습니다.** 1.3(78a3d2c7, 7578198)은 쓰이지 않았지만, prelaunch `path2`에는 경로 1처럼 `previous_blob_not_used` 칸이 없습니다.
- **(f) V-5 키 목록 sha를 실행 뒤 대조하는 경로가 없습니다.** 격자·토양·D8·잡음·PS-7·G8 sha는 실행 전 기록에 고정돼 있지만, 두 경로는 회귀만 대조합니다. 판정 후 감사에서 두 팔 키 목록을 이 sha와 대조하겠습니다.
- **(g) provenance와 K-2 증거 경로는 실제 K-2 출력으로 시험된 적이 없습니다.** rev4 2가 "점검하지 못했다"고 적었습니다. 형식이 어긋나면 보수적으로(판정 불가·실패) 끝납니다.
- **(h) 줄바꿈 보호**: `07_results` 출력(V-6 `k2_row.json` 등)은 여전히 `text: unspecified`입니다. 반면 `runs/**`(flat_main 포함)와 prelaunch 신규 파일은 `-text`, i/lf·w/lf입니다.
- **(i) 러너 env는 띄우는 셸을 물려받습니다**(`k2run_E_V6_*.ps1`은 단계 env만 바꿈). 지금 사용자·시스템·현재 셸에 `OUTRIGGER_*`·`ACC_*`는 없습니다(rev2 6.3 전제).

## 규칙↔도구 대조표 (재감사 범위)

| 항목 | 규칙 | 경로 1 | 경로 2 | 판단 |
|---|---|---|---|---|
| V-5 입력 | 경로 2는 원 출력(rev2:12) | flat_main(manifest v5) | `v5_raw` 폴더 직접 | 일치 |
| 공통 rc | 36 + 4(rev5:30) | K-2 팔만 판정 | 두 팔 | **불일치(발견 1)** |
| 공통 c2_sha256 | f58ee42b, G8은 sidecar HEAD·clean + checkout(rev5 2) | `g8_c2_ok`(1097-1106) | 1291-1299, 1271-1277 | 일치 |
| 오류 행 | 값이 비지 않은 `error`(rev4 a) | `has_error`(flatten 175-194) | `_err`(930-932). 격자·토양은 results 단위만 | 일치(runs 단위 오류는 경로 2가 짝 없음으로 잡음) |
| 격자 | fault 0, p2f 0, 짝 없음 0, 768 | 있음 | 768 없음 | **불일치(발견 1)** |
| 토양 | 60, G1·J2 pass, fault 0 | 있음 | 있음 | 일치 |
| D8 | 576, fails·fault·14.41·0.2·READY ≤ 100, 끔 대비 기록 | 있음, 기록(1027-1028) | 있음, 기록 | 일치 |
| 잡음 L2 | 855, CP 두 계산, unmatched·errors·false_loc 0, SGS 키(rev4 b) | 있음 | 있음 | 일치 |
| 회귀 | 93 / 49 sha, errors 0, unmatched 기록(rev4 c) | 있음 | 있음 | 일치(결측 처리만 다름) |
| PS-7 / G8 | 20 / 83, p2f·ready 상실·새 FAULT | 있음 | 있음 | 일치 |
| K-2 증거 | 위반 = 판정 불가(rev2:25), 사건 4파일(rev5 2) | 판정 불가 | fail | **불일치(발견 1)** |
| V-6 SH-1~6 | rev2 3, rev5 4(J2는 H4 행만) | 1534-1574 | 1452-1520 | 일치(결측 수 세는 단위만 다름, FLAG 여부는 같음) |
| V-3 E-5 | rev3 상수, 키 집합, cn 배수, 열림 비율 | 803-914 | 425-480 | 일치 |
| V-6 E-5·I-9 | L1 켬 0.10 + 열림 비율 4, L2b 끔·None | 1505-1519 | 483-493 | 일치 |
| 봉인 | 원판~rev5 + 명세 | 상수 대조 | `--rules-dir` 줄 때 | 일치(README 9에 인자 있음) |

## T·S 확인 (rev2~rev5)
- **봉인 시각**(커밋): rev2 19:17:25, rev3 19:20:09, rev4 19:27:37, rev5 19:38:49. 이어서 경로 2 1.3 19:27:38, 1.4 19:40:52, 경로 1 b41d2587 19:48:33, 병합 19:51입니다.
- **결과 0건**: 결과 폴더가 없고, k2-run과 관련 worktree 4곳의 untracked는 0입니다. 18:00 이후 scratchpad에서 K-2 실행 산출물을 찾지 못했습니다(배치표 사본과 figspec 작업뿐).
- **판정 항목·문턱**: 바뀐 것이 없습니다.
  - J1~J11, SH 문턱(+3 s, −3 kN, +2 kN), 14.41 kN, 0.2°, 100 s, CP 3 %는 원판·criteria와 같습니다.
  - rev3은 대조 기준을 YAML 계산값으로 바꾸기만 했습니다.
  - rev4 (b)·(c)는 rev2가 넓혀 놓은 것을 criteria 문구로 되돌립니다. 근거는 저장 인수 출력의 형식 점검이고, K-2 결과는 아닙니다.
  - rev5는 출처와 확인 방법만 정합니다.
- **모순**: 원판·rev1과 모순되는 곳은 없습니다. 예외는 기록 (a)(공통 항목 결과 종류)뿐입니다.

## 실행 전 기록 고정값 ↔ 실측
`k2_prelaunch_v2~v7.json`을 모두 대조했고 **불일치 0**입니다. 대조 항목은 다음과 같습니다.
- 규칙 6판과 명세 sha
- 경로 2 1cde20d2, 경로 1 b41d2587, 평탄화기 654bc38c(main 인덱스·작업 사본 hash-object 일치)
- inputs 5개(manifest 807e3690, expect ecef70d2 포함)
- 배치 파일 18개
- 점 파일 2개
- `ra_off`·`ra_on`
- k2-run의 c2.py f58ee42b와 criteria 3값
- L1R 시작 상태 4파일
- L2b blob 2개
- k2-run HEAD
- `fix_blobs_c77ecf5` 5개 @6a44ff8

## 확인 필요
1. **발견 1의 처리.** (a) 시작 전에 두 경로를 맞추고 rev6 봉인과 새 blob을 실행 전 기록에 남길지, (b) 그대로 시작하고 해당 다섯 경우는 G-F 판정 불가로 받아들일지 정해 주십시오. (b)를 고르면 결과 뒤에는 고칠 수 없습니다.
2. **발견 2의 처리.** 참고용 옛 평탄화 단계를 (a) 러너에서 뺄지, (b) rev6에서 rev2 6.1의 예외로 둘지, (c) 위험을 공개만 할지 정해 주십시오.
3. **`[추정]` rev5의 "경로 1과 경로 2의 정의를 맞추는 과정"(`rev5.md:5`)**: 경로 2 작성자가 경로 1 코드(5f22957)를 읽었는지 파일만으로는 알 수 없습니다. 규칙 8은 "경로 1의 출력과 코드는 읽지 않는다"입니다. 결과 전이라 결과에 맞춘 것은 아닙니다. 판정서에 누가 무엇을 대조해 정렬했는지 적을지 정해 주십시오(transcript 확인은 메인 세션 몫).

## 위임 필요
- **python-expert**(확인 필요 1에서 (a)를 고르면): `k2_judge.py` 1355-1360에서 끔 팔 sidecar rc를 판정에 넣고(rev5 3), 회귀 verdict 결측을 세도록 평탄화기 `_flat_rows`의 verdict None을 결측으로 표시합니다.
- **control-expert**(같은 조건): `k2_recount.py`를 고칩니다.
  - `_v5_common`의 K-2 증거 위반을 판정 불가(problems)로 분리
  - `_p2f`의 짝 없는 키를 rev2대로 분류
  - `_v5_grid`에 768 건수 확인
  - rev6 작성과 봉인, 새 blob 고정
- **compute-scheduler-expert**(확인 필요 2에서 (a)를 고르면): P_post에서 `v5_flatten_off`·`_tcl`을 빼고 러너와 배치 기록 sha를 갱신합니다.
- **python-expert (tools/verif)**: `gate_scan.py`가 `--no-git`을 받도록 합니다(지금 종료 2, 공통 인자 계약 불일치).

## 메인 세션 권고
- 시작 전에 G-S 시험 기록을 남기십시오(발견 3).
- 러너는 `OUTRIGGER_*`·`ACC_*`가 없는 셸에서 띄우십시오.
- 순서는 README 8절대로입니다: E_pre 로그 확인 → E_V6 두 러너 → 프로세스와 배치 폴더 확인 → E_V7. P_main과 P_post는 따로 띄웁니다.
- 발견 2를 그대로 두고 P_post가 `v5_flatten_off`에서 멈추면, 남은 tcl r79 판정 단계 2개를 `k2_commands_filled.json`의 같은 래퍼 argv로 이어 돌리고 그 사실을 기록하십시오.

## 검사하지 못한 것
- G-S 시험 자체(재실행하지 않음)와 147개 통과 주장의 대상·skip 수.
- 옛 평탄화기가 실제 K-2 출력에서 죽는지 여부. D8 행에 None 값이 생기는지는 드라이버 코드에서 확정하지 못했습니다.
- 경로 1·2 selftest 재실행(README 9: 2026-11-10 통과 주장, 확인 안 함).
- 저장된 `k2_prerun_audit.md`가 첫 감사 handback 원문과 바이트까지 같은지(transcript 대조 안 함).
- 확인 필요 3의 transcript 확인.
- V-7 Job 메모리.
- C축 재집계(결과 0건).

## 실행한 검증
- 인터프리터: python-dev `-I -B`(`-X utf8`, `MKL_THREADING_LAYER=TBB`). 대상 프로젝트 import는 없습니다.
- verif 도구
  - `seal_check.py --repo . "06_analysis/02_control/k2/k2_touch_creep_rules*.md" --code 04_scripts/03_control/k2`: 6판 raw 일치, 고정 27개, 발견 0
  - `gate_scan.py`(judge, recount, flatten): warning 4. 모두 상위 건수 검사가 있거나 selftest·points_check라 오탐이고, 좋은 패턴 18입니다. `--no-git`은 종료 2입니다.
- 즉석 스크립트 `pin_check.py`(prelaunch v2~v7 고정값 ↔ 파일·git 대조)는 scratchpad `verif\`에 두었고, 실행 뒤 폴더째 지웠습니다.
- 조회 명령
  - git: log, status, worktree list, rev-parse, hash-object, ls-files -s/--eol, check-attr, diff --stat, merge-base --is-ancestor, show
  - PowerShell: Get-FileHash, 환경 변수 조회, 프로세스 목록
- 메모리 갱신: `C:\Users\jinbeom\.claude\agent-memory\verif-protocol-auditor\audit_pitfalls.md`에 2개 항목(두 경로의 판정 종류·적용 팔 차이, 전체 rc 조항 안의 참고용 옛 단계)을 더했고 `MEMORY.md` 색인을 갱신했습니다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha k2_dyn_spec.md 502b0bb7…, k2_prelaunch_notes.md ca3bf841…, k2_touch_creep_rules_rev1.md 5ba081c6…, k2_touch_creep_rules_rev2.md b3f1b41f…, k2_touch_creep_rules_rev3.md 8bcdb0ed…, k2_touch_creep_rules_rev4.md 82160ff5…, k2_touch_creep_rules_rev5.md 73b87758…, k2_touch_creep_rules.md a3658197…, k2_touch_creep_rules_rev1.sha256 fdf6d8ca…, k2_touch_creep_rules_rev2.sha256 2fd7dc24…, k2_touch_creep_rules_rev3.sha256 de03d989…, k2_touch_creep_rules_rev4.sha256 735815f4…, k2_touch_creep_rules_rev5.sha256 f3e5eb8e…, k2_touch_creep_rules.sha256 6a7d3b25…, k2_points_5p5_3p5.json a15cbe95…, k2_commands.json ce6e04a2…, k2_expect.json ecef70d2…, k2_fields.json 0c5aafc4…, k2_manifest.json 807e3690…, k2_prelaunch_v2.json 02c33731…, k2_prelaunch_v3.json 34fb7c6a…, k2_prelaunch_v4.json d8aaa3fd…, k2_prelaunch_v5.json e8b0e334…, k2_prelaunch_v6.json adbc7291…, k2_prelaunch_v7.json 45a3bb87…, k2_prerun_audit.md fe971e24…, k2_v3_keys.txt 506b93a4…, k2_v5_regression_keys.json f2970048…, make_prelaunch.py 1990fb0f…, README.md a87d9752…, regression_keys.py 31ee5cc9…, aff.json 68bb2fb1…, build_runners.py 7182fb37…, k2_commands_filled.json 402a1ef3…, k2_placement_20261110.json f349ce4e…, k2_sched_lanes.json 1b5fc744…, p_main_done_markers.txt ac277f80…, state.json 257a8ab2…, steps_E_pre.json b725bdfe…, steps_E_V6_off.json 1ec165c4…, steps_E_V6_tcl.json d04502cf…, steps_E_V7.json 0713920f…, steps_P_main.json 033496df…, steps_P_post.json 5dd80d49…, k2run_E_pre.ps1 5e8a85db…, k2run_E_V6_off.ps1 8c25c06e…, k2run_E_V6_tcl.ps1 cff4c587…, k2run_E_V7.ps1 e5c94ae7…, k2run_P_main.ps1 1c4c4c58…, k2run_P_post.ps1 434c109b…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 최종 판정 직전에 다시 확인했습니다: master 6d11d13, k2-run 6a44ff8, 추적 파일 변경 0, `runs` 없음, 경로 1·2 blob 그대로입니다. 감사 중 바뀐 파일은 없습니다.
- 사용한 스킬: 없음
