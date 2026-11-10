# K-2 규칙 덧붙임 rev7 (결과 전, 2026-11-10)

- 작성: control-expert(경로 2 작성자), 2026-11-10. 봉인 정보는 같은 폴더의 `k2_touch_creep_rules_rev7.sha256`.
- 원판(`a3658197…7263`), rev1(`5ba081c6…4776`), rev2(`b3f1b41f…94ea`), rev3(`8bcdb0ed…6e61`), rev4(`82160ff5…00c5`), rev5(`73b87758…eccc`), rev6(`21268203e0b55218f88fc2458fe21467871ae3b1bb7ab9cc760b3fbd5ff7ea0e`)는 고치지 않는다. 아래만 덧붙인다. 서로 다르면 rev7 > rev6 > … > 원판 순으로 맞다.
- 시점: V-1~V-7 결과 0건.
  - 계기는 실행 전 세 번째 감사(`prelaunch/k2_prerun_audit3.md`)다. 결과는 차단 1, 실행 전 수정 3, 확인 필요 3, 기록 7.
  - 사용자 결정(2026-11-10)은 세 가지다.
    1. 사실을 공개하고 경로 2는 그대로 쓴다.
    2. SH-6 J2 결측은 경로 1을 rev6 문구대로 고친다.
    3. `flat_main` 단계의 기대값을 rev7에 봉인한다.
- **판정 항목과 문턱은 바꾸지 않는다.**

## 1. rev6 5절 정정: 경로 독립성 공개 (사실 그대로)

rev6 5절의 "메인 세션은 경로 1의 정의 요약(코드가 아님)을 경로 2 작성자에게 전달해 정렬했다"는 사실보다 약하게 적혀 있었다. 다음으로 바로잡는다. 모두 결과 0건인 시점에 일어난 일이다.

- **메인 세션의 정의 요약 전달**: 메인 세션은 경로 1의 정의를 요약한 글(코드가 아님)을 경로 2 작성자(control-expert)에게 보냈다. rev5 작성 때 7개 정렬 항목, rev6 작성 때 재감사 발견 등이다.
- **경로 2 작성자가 경로 1 코드를 직접 읽었다**(원판 8절 "경로 1의 출력과 코드는 읽지 않는다" 위반). 세 번째 감사가 transcript에서 확인한 행위는 다음과 같다(KST).
  - 17:37:23~17:37:36 — `04_scripts/03_control/k2/k2_judge.py`에서 다음을 했다. 목적은 manifest 형식을 맞추는 것이었다.
    - `add_argument`·manifest 키 grep
    - `Read` offset 1110 limit 100(CLI)
    - `sed -n 560,600p`(manifest 부분 읽기)
    - `Read` offset 884 limit 20(V-5 판정 함수)
  - 17:50:06 — `grep -n "series" k2_judge.py`를 했고, 곧바로 17:50:13에 `k2_recount.py`를 고쳤다(시계열 폴더 규칙).
  - 17:51:09 — `grep -n "dhat" k2_judge.py`(V-6 D̂ 키 위치 확인).
  - 19:37:58~19:38:02 — `git show 5f22957:04_scripts/03_control/k2/k2_judge.py`를 대상으로 다음을 했다. 30초 뒤(19:38:32)에 rev5를 썼다.
    - kind·`V5_KINDS`·`pass_to_fail` grep
    - `sed -n 1270,1300p`(`_relative`)
    - `V5_RELATIVE_GATES -A6`
  - 이 밖에 경로 2 작성자는 경로 1 코드의 줄 번호와 동작을 인용한 감사 원문 세 편(`k2_prerun_audit.md`, `k2_prerun_reaudit.md`, `k2_prerun_audit3.md`)을 읽었다.
- **경로 1 작성자**(python-expert)도 경로 2 코드를 일부 참조했다. docstring이 경로 2 내부를 가리키고, `false_latches`가 경로 2의 `false_latch`와 거의 같다(재감사 기록 d, rev6 5절).

## 2. 원판 8절 위반의 처리

- **사용자 결정: 경로 2(`k2_recount.py` 1.5, blob `e1e16a9c…`)를 그대로 쓴다.** 경로 2를 새 작성자가 다시 쓰지 않는다. G-F의 두 경로 대조는 원판 8절 기준을 그대로 적용한다.
- 판정서에는 다음을 공개한다: "두 경로가 서로의 코드·정의를 보고 맞춘 부분은 공통 실수가 두 경로에 함께 들어갔을 수 있다." 해당 부분은 다음과 같다.
  - V-5 결과 종류(rev6 1절: 실패/판정 불가 분류, 공통 항목, K-2 증거, 짝 없는 키, 건수)
  - SH 결측 처리(rev6 2절, rev5 4절의 SH-6 J2)
  - kind·relative gate(D8·잡음의 통과→실패를 기록으로 둠, rev5 4절)
  - manifest 형식(`points`/`points_file`, V-5 칸, 시계열 폴더 `<stem>_series`)과 V-6 D̂ 키 위치(`k2_row.json` `k2` 블록)
  - G8 c2 확인(rev5 2절)과 L1 공중 거짓 래치 계산
- 이 부분에서 두 경로가 일치해도, 그것은 서로 독립된 확인으로 세지 않는다. 판정서는 이 부분을 "정렬된 정의의 일치"로 표기한다.

## 3. `flat_main` 재생성 단계의 기대값 (rev6 4절 보완, rev2 6절 1의 `6a44ff8` 조건 대신)

- 이 단계는 결과가 나온 뒤 판정 전에, **판정 커밋의 main checkout**에서 돈다. 그래서 rev2 6절 1의 "시작·끝 HEAD = `6a44ff8`" 대신 아래 값을 기대값으로 쓴다.

| 항목 | 기대값 |
|---|---|
| sidecar | `<k2-run>\06_analysis\02_control\k2\runs\v5\<arm>\flat_main.launch.json`(팔마다 1개). 옛 `flatten.launch.json`과 다른 이름이다 |
| git(`--git-dir`) | main checkout `C:\workspace\outrigger_control` |
| 시작·끝 HEAD | 판정 커밋(실행 전 기록에 적은 커밋). 그 커밋의 `04_scripts/03_control/k2/k2_v5_flatten.py` blob = `b385119095b97568a4c8f82f685e3c920ee50d2b`. rev7 뒤 평탄화기가 바뀌면 실행 전 기록에 적은 최종 blob |
| 시작·끝 clean | `git status --porcelain --untracked-files=no`가 빈 문자열(`is_clean` 참) |
| env | `MKL_THREADING_LAYER=TBB`, `MKL_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `NUMBA_NUM_THREADS=1`. 그 밖은 `k2_commands.json` 하네스 env(`CONDA_PREFIX`·`PATH` = dynamics-dev, `PYTHONDONTWRITEBYTECODE=1`)와 같다 |
| 마스크 | E코어 `0x0FFF0000`. 래퍼를 띄우는 셸을 먼저 고정한다 |
| rc | 0 |

- **명령**(팔마다, cwd = main checkout. `<main>` = `C:\workspace\outrigger_control`, `<run>` = `C:\workspace\outrigger_control\.claude\worktrees\k2-run`):

```
C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B <main>\04_scripts\03_control\k2\run_with_identity.py
    <run>\06_analysis\02_control\k2\runs\v5\<arm>\flat_main.launch.json --git-dir <main> --
    C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B <main>\04_scripts\03_control\k2\k2_v5_flatten.py
    --arm-dir <run>\06_analysis\02_control\k2\runs\v5\<arm> --out-dir <run>\06_analysis\02_control\k2\runs\v5\<arm>\flat_main
    --checkout <run>
```

- 이 sidecar 2개는 판정 후 정체성 확인에서 rev2 6절 1의 60개와 함께 본다. 경로 1의 입력 검사에는 넣지 않는다(메인 세션 결정).

## 4. 이어 돌리기 규칙 보완 (rev6 4절, 감사 기록 f)

- P_post가 참고용 평탄화 단계에서 멈춰 남은 tcl r79 판정 단계를 이어 돌릴 때는 `k2_commands_filled.json`에 적힌 그 단계의 값을 **모두 그대로** 쓴다: argv, cwd, **env**, **마스크**(P코어 `0xFFFF`).
- 이어 돌린 단계의 sidecar는 rev2 6절 1의 기대값(HEAD `6a44ff8`, clean, env, 마스크)으로 본다.

## 5. G-F 대조 단위 (원판 8절, 감사 기록 e)

두 경로가 맞대는 필드를 결과 전에 정한다. 이름이 다른 내부 항목은 맞대지 않는다.

| 대상 | 맞대는 값 |
|---|---|
| 관문 | G-A, G-B, G-C, G-D, G-E 각각의 값(`pass`/`fail`/`not_judgeable`)과 등급 |
| V-2·V-3(판정 팔 6개)·V-4·V-6 행 | 행별 `pass`/`fail`/판정 불가, 실패 항목 이름 집합(J1~J11, V6_false_latch, V6_cap) |
| 같은 묶음의 SH | SH-1~SH-6 각각의 FLAG 여부(결측 FLAG 포함), 지표별 결측 수 |
| V-5 공통 | 두 경로 모두 "공통 항목 판정 불가 있음/없음" 한 값으로 맞댄다. 경로 1은 묶음별 결과를 OR로 합친다 |
| V-5 묶음(격자·토양·D8·잡음 L2·회귀·PS-7·G8) | ① 묶음 종류(`pass`/`fail`/`not_judgeable`), ② K-2 팔 행 수와 끔 팔 행 수, ③ 끔 팔 대비 통과→실패 행 수(D8·잡음은 기록이므로 맞대지 않는다), ④ 잡음 L2는 실패 수 k와 CP 상계 두 값(상대차 ≤ 1e-9), ⑤ 회귀는 판정 키 sha·기록 키 sha의 일치 여부 |
| 수치 | 같은 원 데이터에서 낸 수치는 상대차 ≤ 1e-9(0이면 절대차 ≤ 1e-9). 원판 8절 그대로 |

- 하나라도 다르면 G-F는 판정 불가다(원판 8절).
- 위 2절의 "정렬된 정의" 부분이 일치하면, 판정서에 그 사실을 함께 적는다.
