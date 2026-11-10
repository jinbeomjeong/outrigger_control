# B1 격자 수렴 시험 계획서 rev1 — 덧붙임판 (`B1-GRIDCONV`)

- 작성: control-expert, 2026-11-10
- **결과 전 개정**: GC-1~GC-4는 하나도 실행하지 않았고, 어떤 결과도 보지 않았다.
- 원판: `b1_gridconv_plan.md`(봉인 sha256 `0e909bf1186a4cc90e40353d25244ee4a76a04cdabe48235e7051f9a111e9b24`). 원판은 바꾸지 않는다. 이 판은 아래 C-1·C-2만 원판에 덧붙이거나 갈음한다. 나머지는 모두 원판 그대로다(G-3 단독 실패 = `HOLD` 포함, 사용자 확인 2026-11-10).
- 계기: cad-expert가 GC-1~GC-4 실행 명령을 준비하다가 두 문제를 찾았다(2026-11-10).

## C-1 V-2 패드 xy 오프셋 확인 (원판 3.3 V-2 갈음)

- 원판 문구: "패드 시작 위치 인자 없음(오프셋 0), `settle_end.x_mm`·`y_mm`의 절대값 ≤ 1e-3 mm(P1: 0 ~ 1e-18 mm)"
- 문제
  - `settle_end`는 유지가 끝난 뒤($t$ = 21 s)의 위치라 **시작** 오프셋이 아니다.
  - 하중 계단 행(`load_steps.levels[*]`)에는 패드 xy가 기록되지 않는다. 그래서 그 행으로는 시작 오프셋을 확인할 수 없다.
- 갈음 문구: 패드 시작 위치 인자 없음(오프셋 0). 그리고 `series.npz`의 첫 기록 표본 share 몸체 `x[0]`·`y[0]`의 절대값이 각각 ≤ 1×10⁻⁹ m여야 한다.
  - 근거: `run_S9.py` single-pad의 `series.npz` `x`·`y`는 `share.GetPos()`다(`run_S9.py` 2764-2768). `--joint fixed`라서 패드가 share 몸체에 묶여 있어 위치가 같이 움직인다.
  - `series.npz`가 없거나 `x`·`y`를 읽을 수 없으면 V-2 실패(`INVALID`)다.
  - `settle_end.x_mm`·`y_mm`는 기록만 한다(관문 아님).
- cad-expert 지표 스크립트(`04_scripts/02_chrono/b1_grid_conv/grid_conv_judge.py`, 브랜치 `b1-gridconv-prep`)와 같은 정의다. 경로 A는 그 코드를 보지 않고 이 문구로 따로 구현했다.

## C-2 hull hook DLL (원판 3.1 덧붙임, 3.3 V-2 덧붙임)

- 문제: DLL `03_src/outrigger_sim/native/chrono_hull/bin/chrono_hull_hook.dll`은 git 제외 파일이다. 새 checkout(`HEAD_G`)에는 없고, 없으면 hull hook이 경고 뒤 off로 폴백한다. 그러면 V-2의 hull `fast`에서 걸린다.
- 3.1 덧붙임(실행 전 단계)
  1. 검증된 DLL `C:\workspace\outrigger_control\03_src\outrigger_sim\native\chrono_hull\bin\chrono_hull_hook.dll`을 `HEAD_G` checkout의 같은 상대 경로에 복사한다.
  2. 복사본 SHA-256이 `cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15`(`hull_hook.VALIDATED_DLL_SHA256`)인지 확인한다. prelaunch 기록에 원본·복사본 sha를 적는다.
  3. `OUTRIGGER_HULL_HOOK`는 원판대로 설정하지 않는다(기본 fast). `OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED`도 설정하지 않는다.
- V-2 덧붙임: result.json `hull_hook.dll_sha256`이 위 값이고 `hull_hook.dll_sha_validated`가 참이어야 한다. 아니면 `INVALID`다.
- 이 복사는 추적 파일을 바꾸지 않는다. "깨끗한 checkout" 조건은 추적 파일 변경 0으로 본다(git 제외 DLL은 셈에 넣지 않는다).

## 경로 A 도구 (rev1 반영, 결과 전 고정)

| 파일 | sha256 | git blob id |
|---|---|---|
| `06_analysis/02_control/b1/gridconv_judge.py` | `4a5c42460116a68e1c2c02f66b77d38b407aa9089d8906771d047774b694d248` | `91d8d80c93b2e4db6bd247460aca9a76428238d3` |
| `06_analysis/02_control/b1/gridconv_judge_selftest.py` | `ec3126cd2f8389625990fb23119c66e807abddfc77b235861947e1797efde7c5` | `848e45e8e730296536d2beba985a1c1c4396f067` |

- 앞 판(커밋 `1377719`, sha `e17da053…`)은 C-1·C-2 전 정의라 쓰지 않는다.
- 합성 자체 시험 8경우가 모두 기대대로 나왔다(마지막 줄 `{"status": "ok"}`).
  - `PASS`, `REJECT`(G-1), `HOLD`(G-3)
  - `UNDETERMINED`: 행 없음, `--grid` 틀림, share xy0 2×10⁻⁹ m, `series.npz` 없음, 검증 안 된 DLL sha
- 경로 B(terramechanics)는 원판 7절 그대로 실행 뒤에 맡긴다. 경로 B도 C-1·C-2 정의를 따른다.

## 순서 (원판 7절에 덧붙임)

- 봉인(원판) → rev1 봉인 → 경로 A sha 고정(이 판 표) → `HEAD_G` 병합 → DLL 복사·sha 확인(C-2) → 배치표 → 실행 → 경로 A → 경로 B → 대조 → 판정서
