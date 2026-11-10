# D8x 검증 범위 확장 판정 규칙 — 덧붙임판 6 (rev6, 두 경로 비교 기준판)

- 작성: control-expert, 2026-11-10. 봉인 sha는 같은 폴더 `d8x_rules_rev6.sha256`에 있다.
- 바탕 문서(모두 고치지 않는다)
  - 원판 `d8x_rules.md` `a377b9bb028385bb7d7d97312a71816ba0ca758e2cb193e25b2d092fff064da8`(28d5aab)
  - rev1 `ad16f452fb4dce7395a059c73d7caf213f1a9a69f18af8d230bf03f4518e80d4`(9e2b9e2)
  - rev2 `5f3fa620fe704834a9b6c0a65824b29b75e2a527ea8e97a17abb5e07987a8c27`(f1e8ac5)
  - rev3 `2318fb5cf75b64b525c515566776ed1ec6cbb10743621edc04c092d6774c7301`(589ff43)
  - rev4 `5233c517e6c0d17b0e26e902673e0d6990532ed1c54c82ae0801e688d50702a5`(f708bee)
  - rev5 `63437019eaee2340fbbfc45efdcf78bfc5ba314f83085d55f19e323c6f5ffabe`(22521ec)
- 계기: verif-protocol-auditor rev5 봉인 점검 원문 `06_analysis/02_control/d8x/d8x_rev5_seal_audit.md`(main checkout, 이 판을 쓸 때 git 미커밋, 끝에 메인 세션 덧붙임 포함, sha256 `abd2f6d08977f6fd95cf8b61a6751afee4e339b75cbb093a598e64d69eeb7429`). 차단 0, 실행 전 수정 B-1·B-2·B-3a·B-4.
- 사용자 결정(2026-11-10, 위 원문 덧붙임): **권고대로.** B-1은 이 판에 "원판 8 일치 비교 = 경로 1 ↔ (경로 2 + 손 적용)"으로 적는다. B-2·B-3a(실행 전 기록 키 구현 + 다섯 키 각각 읽기)·B-4는 경로 1 코드로 고친다. 이 판 공개 절에 봉인 뒤 G0 rev3 탐침을 넣는다. C-2 정정과 B-3 경계 문구는 control-expert가 정한다.
- **바뀐 것**: 원판 8의 G1·V-2 비교 기준(1절), V-2 손 집계의 결측 경계(2절), 경로 1 출력의 뜻(3절, B-3a·B-4 구현 전제), 판정서 범위 차이 문구(4절), rev5 머리말·5절 정정(5절). **그 밖의 기준(J1~J11, 문턱, 관문 순서, 기대 수, 점 좌표, 마름모 5.7 / 3.7 / 3.6, G0-4 범위·W 자격, d45 1.01, 태그·E-6, G0 재계산, rev4 G1 정의, rev5 V-2 범위와 3.1 순서, W 선정·FLAG (i)·(ii), 7절 승계, 등급 정의)은 바꾸지 않는다.**
- 규약·기호·$F_{D8}$ = 14,414.589 N은 원판과 같다. K1 = LAS-b K1(R4c30 순서 관문).

## 공개: 봉인 시점에 본 것과 없는 것

| 구분 | 내용 |
|---|---|
| 본 것 | rev5 공개 목록, rev5 봉인 점검 원문 전체, 탐침 보존 폴더 목록과 `SHA256SUMS_add.txt`, 통합 브랜치 커밋 제목 `8c9e8b1`(12:09:18)·`b311169`(12:15:26) |
| 봉인 뒤 탐침(rev5 봉인 12:11:11 뒤) | 아래 표. **판정에 쓰지 않는다** |
| 없는 것 | 정식 R-a·R-c·Chrono·G0 rev3 산출물 0건(봉인 점검 B-5 탐색 결과와 같음) |

**G0 rev3 탐침(B-5)과 같은 탐침 부산물(B-6)**

- 보존 위치: `C:\workspace\outrigger_control\.local_archive\session_6f3ebc4d_20261110\d8x_probes\`. 목록 `SHA256SUMS.txt`(sha256 `0e239c7a3bc3b901c7bdb35945d23f37aa7ab4e566001e13252f7c90d86ca047`, rev5 1.2의 5파일)와 `SHA256SUMS_add.txt`(sha256 `35889499829b530de1d1186aa63c1ea438f2aa036f1527d37dce8b131987f62b`, 아래 5파일).

| 파일 | sha256 | 내용 |
|---|---|---|
| `g0_rev3_probe.json` | `26cb3faa3b1f6f018933d05366d8562a7d85aaabd823507f2ef492bb87ad4958` | G0 rev3 전체 재계산 탐침(원래 mtime 12:15:48). meta `rules_rev` rev3, `run_commit` `b311169`(통합 브랜치 `worktree-agent-ac6cd65fc4ec57212`), `clean` true, reuse 0 / recompute 60. `meta.rules_seals`는 원판~rev4 |
| `g0_rev3_probe_judge.json` | `226e7b2bffb96500dab0bacc0010f3f8512ffbdbc66c351bc2bc139d7d96ea34` | 경로 1 판정 탐침(12:15:51), `gate_G0` = `pass` |
| `rc_probe_off.log` | `a1156da208b35091990b1732af177a80d427cf0817668b3bee4a9cde22104809` | rev5 1.2 R-c 끔 탐침 로그 |
| `rc_probe_on.log` | `37d7af8bf2c2f7578006bcb3fc471c3602aa44bbe031987b2f38bd76a49bb0ff` | rev5 1.2 R-c 켬 탐침 로그 |
| `ra_probe_off.json.partial.jsonl` | `8580f71069bd88e1a5ebf18cab3b184e3cd69cdf514aebbbc1539741e93f3fea` | rev5 1.2 R-a 탐침 부분 파일 |

- G0 탐침은 master 병합 전 커밋(`b311169`)의 결과이므로 rev4 3에 따라 **판정에 쓰지 않는다.** 정식 G0 rev3(`d8x_g0_rev3.json`)는 $H_{impl}$(rev4 3, rev5 4)에서 새로 돌고, 그 실행 기록은 rev6까지의 봉인을 담아야 한다(4절).
- 메인 세션이 이 값(G0 60/60 `pass`)을 실행 전에 봤다. 실행 전 기록과 판정서 "봉인 뒤·실행 전 본 자료" 절에도 이 표를 옮긴다.
- 영향: 이 판의 변경(1~5절)은 비교 방법·결측 처리·문구이고 명령·실행·문턱과 무관하다. G0 탐침 값이 이 판의 선택에 쓰이지 않았다.

## 1. B-1: 원판 8 두 경로 일치의 비교 기준 (원판 8 보충)

- 원판 8 "묶음별 수(E-1), 행별 `pass`/`fail`/불가, 관문 결과, W·V 선정, V-1·V-2 분류가 모두 같아야 한다"에서 **G1 관문 결과와 V-2 분류는 다음 둘을 비교한다.**
  - 경로 1 출력(통합 브랜치 `b311169`부터 G1·V-2를 두 팔로 센다)
  - **경로 2 출력 + 손 적용 결과**(rev4 1.4 F-1, rev5 2.1 V-2, rev5 3.1 순서). 경로 2는 고치지 않는다(`46010967…d9d1`, 끔 팔만 셈).
- 행 단위 대조(의무)
  1. K1 켬 팔 행별 verdict(`pass`/`fail`/불가): 경로 1 켬 팔 행 ↔ 경로 2 `report["ra"|"rc"]["on"]["rows"][*]["verdict"]`를 키로 이어 모두 같아야 한다.
  2. K1 켬 팔 LAS 수: (묶음, 점, 단계)별로 경로 1 ↔ 경로 2 켬 팔 행 `record.las_events` 합(2절 결측 경계 적용)이 모두 같아야 한다.
  3. 끔 팔은 원판 8 그대로 도구 출력끼리 비교한다.
- 키 대응(판정서에 표로 적는다)

| 경로 1 | 경로 2 | 비고 |
|---|---|---|
| `ra\|<point>\|<level>` | `["R-a", <point>, <level>, n]` | `<point>`는 rev1 1.2 (A) 점 태그 |
| `rc\|<slope_name>\|<level>` | `["R-c", <floor>, <level>, n]` | 경로 2 R-c 키의 첫 원소가 바닥 이름(= 경로 1 `slope_name`) |

- 하나라도 다르면 원판 8대로 G3는 판정 불가다. 다만 그 차이가 "경로 2가 켬 팔을 세지 않음" 자체라면 그것은 손 적용으로 메운 것이므로 차이가 아니다. 손 적용 뒤에도 남는 차이만 불일치다. 결과를 본 뒤 경로 2를 고치지 않는다.

## 2. B-3 경계: V-2 켬 팔 손 집계의 결측 (rev5 2.1-1·3.1-7 정리)

rev5 2.1-1 "필드가 없으면 원 결과 파일에서 손으로 센다"와 3.1-7 "결측(켬 팔 행 기록 없음) = 판정 불가"를 다음으로 정리한다.

| 상황 | 처리 |
|---|---|
| (i) 켬 팔 행이 도구 출력에 있고 `las_events`(경로 2 `record`) 또는 사건 목록(경로 1)이 있다 | 그 값을 쓴다 |
| (ii) 행은 있으나 도구 출력에 그 필드가 없다 | 원 결과 파일(R-a 런 레코드의 사건 이름 목록, R-c 줄의 `d1` 사건 이름 목록)에서 `INFO_LIFTOFF_SLOW` 접두사를 손으로 센다. 센 출처(파일·키)를 판정서에 적는다 |
| (iii) 행은 있고 verdict가 `pass`인데 원 결과에도 사건 목록이 없다(키 없음) | **그 행의 V-2 집계는 판정 불가**다(정체성 기록 결측). 사건 목록이 빈 목록 `[]`이면 0으로 센다(키 있음 = 기록 있음) |
| (iv) 행이 없거나(E-1 수 부족), 드라이버 오류·`d8x` 블록 없음 행 | 그 행은 이미 묶음을 판정 불가(E-1)나 `fail`(E-2)로 만든다. rev5 3.1-1 순서대로 G1이 먼저 막고, V-2 집계는 기록만 한다 |
| (v) 행 verdict가 `fail`·불가이고 사건 목록이 없다 | (iv)와 같다. G1이 먼저 막으므로 V-2는 기록 |

- 정리하면 3.1-7의 "켬 팔 행 기록 없음"은 (iii)·(iv)를 뜻하고, 2.1-1의 "필드 없음"은 (ii)를 뜻한다. 같은 처리를 끔 팔 손 확인에도 쓴다(도구 출력이 있으면 도구 값이 먼저다).
- 이유: (iii)을 0으로 세면 기록이 빠진 행이 `LAS_INACTIVE`로 들어가 조용한 통과가 된다. 판정 불가가 엄격한 쪽이다.

## 3. B-3a·B-4: 경로 1 출력의 뜻 (구현 전제)

- **B-3a(구현으로 채움)**: rev5 5절의 E-6d 다섯 키는 그대로다. python-expert가 다음을 구현하는 것을 전제로 한다.
  - `d8x_judge.py` `_chrono_prelaunch`가 `d8x_prelaunch_C.json`의 `rows[<case>]`마다 `k1_order_gate`(기대 태그가 `_K1`이면 True)를 기록한다.
  - `judge-chrono`가 다섯 키(`d8x.k1_order_gate`, `d8x.controller_meta_order_gate`, `d8x.k1_order_gate_matches_meta`, `controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate`, prelaunch `rows[<case>].k1_order_gate`)를 **각각** 읽는다. 처음 찾은 값 하나로 대신하지 않는다. 하나라도 없으면 그 행은 판정 불가이고, 키가 없는 입력이면 종료 2다.
  - 이 구현이 $H_{impl}$에 없으면 Chrono 행은 rev5 5절을 글자대로 적용해 판정 불가다(규칙을 도구에 맞춰 낮추지 않는다).
- **B-4**: rev5 3.1-3의 "경로 1 출력"은 **`judge-ra`·`judge-rc` 출력 파일과 `report` 출력 모두**를 뜻한다. python-expert가 `cmd_report`의 `.get("k1_rows_failed", [])` 기본값을 없애, 키가 없으면 `None`을 내고 종료 2가 되게 고친다는 전제다. 판정서는 두 출력 모두에서 키 존재와 값을 확인하고, 둘 중 어디에서든 키가 없으면 그 묶음은 판정 불가다.

## 4. B-2: 판정서 "두 경로 범위 차이" 문구 (rev4 2-1 대체)

- rev4 2의 1번 문구를 다음으로 바꾼다: **경로 2 `RULES_SHA256`(62~65행)은 원판·rev1·rev2만 대조한다. rev3·rev4·rev5·rev6의 봉인 일치는 경로 2가 보지 않으므로, 판정서 작성자가 각 `.sha256` 파일과 직접 해시로 손 확인하고 값을 적는다.**
- 경로 1 봉인 목록(`d8x_spec.RULES_FILES`, `LATEST_RULES_REV`, `s6_stage2` 규칙 sha 상수)에 rev5(`63437019…fabe`)와 rev6(이 판의 `.sha256` 값)이 들어가는 것은 구현으로 한다(python-expert·cad-expert). 정식 G0 rev3·R-a·R-c·Chrono 실행 기록의 규칙 봉인 목록도 rev6까지 담아야 한다. 담지 않은 실행 기록은 원판 G-S 봉인 관문에서 판정 불가다.
- rev4 2의 2·3번(G0 출처 점검, `--expect` 파일 sha)과 rev3 3.3(Chrono `k1_order_gate` 미점검)은 그대로 적는다.

## 5. C-2: rev5 정정

- rev5 머리말 "바뀐 판정은 A-2(2절) 하나와 … 3절뿐이다"에 **5절(E-6d 키 보충: 키 셋 추가, 키 없음 = 판정 불가)**을 더한다. 5절은 결과 전이고 엄격한 쪽이다.
- rev5 5절 "브랜치 `d8x-gate-meta` 4e8eb9b, 병합 전"은 **"master 병합 전(통합 브랜치 `worktree-agent-ac6cd65fc4ec57212`에는 `8c9e8b1`, 12:09:18로 병합)"**으로 읽는다.
- rev5 공개 절의 "커밋 제목(4e8eb9b)"은 **"커밋 본문(4e8eb9b)"**으로 읽는다. 5절의 키 이름은 커밋 본문에서 왔다.
