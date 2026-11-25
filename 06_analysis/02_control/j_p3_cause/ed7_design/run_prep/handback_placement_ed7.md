의존성 점검: STAMP(이 세션 11-23 점검이 유효해서 생략). psutil·numpy·nvidia-ml-py 모두 OK.

**상태**: P 5% / E 5% / 가용 메모리 18,359 MB (예비 4,096 MB 제외 시 14,263 MB). 스왑은 1.3 GB 쓰는 중이고 문제는 없음. GPU는 1%, VRAM 110/12,282 MiB이고 데스크톱 프로세스(dwm·explorer 등)만 쓰며 P8, 스로틀 없음(gpu_idle). 고정 테넌트는 없음. `reserve.py prune` 결과는 removed 0, kept 0이고, 다른 세션의 유효 예약은 없음. 러너도 돌고 있지 않음. 속도표는 이 배치에서 쓰지 않았음(판정 실행이라 CPU-s ÷ 실측 처리량으로 계산).

**1. 마스크·worker 결정**

공통값은 `-MaskHex 0x0FFFFFFF`(논리 0–27, P+E 전부), `-Workers 20`입니다. 6단계 모두 같게 줍니다.

- **근거 (ed5·ed6 실측 처리량, cpu-s/s)**
  - 0x0FFFFFFF × 20 workers에서 j9main은 16.4~16.5, sens는 16.6, t8은 16.6, probe는 18.7, confirm은 17.7~19.3입니다.
  - P 8 worker만 쓴 ed5 t8은 7.5(4,413 cpu-s ÷ 585 s)입니다.
  - P+E 20 worker가 P만 쓸 때보다 약 2.2배 빠릅니다.
  - 그래서 P 단독은 쓰지 않습니다.
- **20으로 둔 이유**
  - P 물리 8 + E 12 = 20이라 물리 코어를 한 worker씩 채웁니다.
  - 더 늘리면 P SMT 형제에 얹힙니다. SMT 형제는 해시형 부하 기준으로 이득이 없었습니다(1.00, 2026-10-30 실측).
  - ed6와 같은 worker 수라 시간 예상이 그대로 맞습니다. 24 worker는 측정이 없어서 쓰지 않았습니다.
  - RSS는 W+2 = 22 프로세스에 0.34 GB씩이라 최대 약 5.5 GB입니다. 가용 14.2 GB 안입니다.
- **history에서 가져오지 못한 값**
  - `estimate_wall.py`는 이 task_type의 기록이 없어 `weak`로 18.2 cpu-s/s(wall 2,800~3,300 s)를 냈습니다.
  - 이 값은 쓰지 않고, 위 같은 계열 실측(16.4~16.6)을 썼습니다.

| 단계 | -MaskHex | -Workers | 비고 |
|---|---|---|---|
| impl_t8 | 0x0FFFFFFF | 20 | 44줄이라 worker당 약 2줄, 꼬리 짧음 |
| impl_cases | 0x0FFFFFFF | 20 | 실제 min(10,20) = 10 worker, 12 프로세스 |
| impl_probe | 0x0FFFFFFF | 20 | 114줄, worker당 약 5.7줄이라 꼬리 여유 필요 |
| confirm | 0x0FFFFFFF | 20 | G1 171줄 20 worker. D 24줄은 min(24,20) = 20 worker라 2라운드(마지막 4줄이 꼬리), 약 +200 s `추정` |
| j9main | 0x0FFFFFFF | 20 | |
| sens | 0x0FFFFFFF | 20 | |

단계 안에서 P와 E가 섞이므로 기록에는 `--core mixed --mask 0x0FFFFFFF`를 줍니다.

**4. 단계별 예상 wall (순차, 겹침 없음)**

| 단계 | 배치 | 예상 wall | 근거 |
|---|---|---|---|
| impl_scope | 없음(git diff) | 30 s | 시뮬레이션 없음 |
| l1ref | C 고정 P 0x000F/00F0/0F00/F000 ×4w | ~4,000 s | ed6 같은 키·마스크 실측 3,800 / 3,989 / 2,543 / 2,705 s, 가장 긴 줄이 결정. ed7 러너가 이 4개를 동시에 돌리므로 최장 약 4,000 s |
| impl_t8 | P+E 20w | ~270 s | ed6 260 s(20w, 0x0FFFFFFF) |
| impl_cases | P+E 10w | ~115 s | ed6 113 s |
| impl_probe | P+E 20w | ~900 s | 사전 봉인 재현 876 s. 꼬리 때문에 900~1,000 s로 `추정` |
| confirm | P+E 20w | 1,300~1,900 s | ed6 confirm_a 1,302 s, grid 1,607 s. D는 2라운드라 상한에 가까움 |
| j9main | P+E 20w | ~3,100 s | ed6 3,083 s, ed5 2,967 s |
| sens | P+E 20w | ~3,650 s (범위 2,900~4,600) | ed6의 184줄 1,448 s(131 cpu-s/줄)를 460줄로 환산(60,300 cpu-s ÷ 16.5). 줄 구성이 달라 ±25 % `추정` |
| dg3 | C 고정 P 0x00FF/0xFF00 ×4w | ~2,250 s | ed5 2,236 / 2,205 s |
| 12b_plan | 1프로세스 | 300~1,800 s | 측정 없음 `추정`. 입력 파일을 통째로 메모리에 읽음 |
| 12b_vbkm0 base | C 고정 0x000F/0x00F0 ×4w | ~3,600 s | ed5 3,550 / 3,555 s |

합계는 약 20,500 s(5.7 h)이고 범위는 19,500~21,600 s입니다. 요약의 19,500~21,600 s와 일치합니다. 판정·SUMS 대기는 빠져 있습니다. T' 판정 뒤의 12b_vbkm0_b4(약 3,600 s)와 12b_vbkm(약 3,800 s)은 이 합계에 넣지 않았습니다.

**고정 마스크 단계에서 E 코어가 노는 것(기록만)**
- l1ref: 4개 마스크가 P 0–15를 다 쓰고 E 12는 놉니다. 그나마 4 worker가 논리 4개(코어 2개)에 묶여 ed6처럼 ed5의 1.7배 걸립니다.
- dg3: P 16개를 다 쓰고 E는 놉니다.
- 12b_vbkm0 base: P 0–7만 쓰고 P 8–15와 E 전부가 놉니다.
- 이 세 단계는 합쳐서 약 9,850 s(약 2.7 h)로 전체의 약 48 %입니다.

**3. reserve 명령 (30분 넘는 단계)**

전역 규칙은 러너가 `make_runner.py --reserve-owner ... --reserve-ttl-min ...`로 자기 PID에 예약하는 방식입니다. 그 방식을 쓰면 아래는 필요 없습니다. 단계별로 수동 예약하려면 `<PID>` 자리에 그 단계를 돌리는 pwsh 러너 PID를 넣습니다. 이 명령은 실행하지 않고 드리는 것입니다.

```powershell
$py = 'C:\ProgramData\miniforge3\envs\python-dev\python.exe'
$tools = 'C:\Users\jinbeom\.claude\tools\cpu-scheduler'
# l1ref (예상 67분 -> TTL 120). 끝나면 release
& $py -I -B $tools\reserve.py add --owner ed7-l1ref --mask 0xFFFF --ram-mb 6144 --pid <PID> --ttl-min 120 --note "ed7 l1ref 4x4w P0-15, E idle"
# j9main (예상 52분 -> TTL 120)
& $py -I -B $tools\reserve.py add --owner ed7-j9main --mask 0x0FFFFFFF --ram-mb 7168 --pid <PID> --ttl-min 120 --note "ed7 j9main 20w P+E"
# sens (예상 61분, 최대 77분 -> TTL 150)
& $py -I -B $tools\reserve.py add --owner ed7-sens --mask 0x0FFFFFFF --ram-mb 7168 --pid <PID> --ttl-min 150 --note "ed7 sens 20w P+E"
# dg3 (예상 38분 -> TTL 90)
& $py -I -B $tools\reserve.py add --owner ed7-dg3 --mask 0xFFFF --ram-mb 4096 --pid <PID> --ttl-min 90 --note "ed7 dg3 VBM 0x00FF / VBM0 0xFF00"
# 12b_vbkm0 base (예상 60분 -> TTL 120). 마스크는 P 0-7만
& $py -I -B $tools\reserve.py add --owner ed7-12b-vbkm0 --mask 0x00FF --ram-mb 3584 --pid <PID> --ttl-min 120 --note "ed7 12b vbkm0 base b1 0x000F b2 0x00F0"
# 각 단계 끝에 (add가 출력한 id 사용)
& $py -I -B $tools\reserve.py release --id <ID>
```

- `wait_until.py --no-reservation-overlap`은 자기 부모 러너의 예약을 무시합니다.
- 12b_plan은 5~30분이라 예약하지 않았습니다.
- 12b_vbkm0 base 이후(b4, vbkm)도 30분을 넘기므로 같은 방식으로 예약하면 됩니다(마스크 0x000F, 0x0FFF 등). 이번 배치표에는 넣지 않았습니다.

**5. 기록**

위 "고정 마스크 단계에서 E 코어가 노는 것"과 같은 내용입니다. 바꿀 수 없어서 기록만 합니다.

**실행 명령**: 이번 요청은 `-MaskHex`·`-Workers` 값 결정이라서 `plan.py`의 `launch_ps1`은 만들지 않았습니다. 스텝 명령줄에 아래 값을 넣으면 됩니다.

`-MaskHex 0x0FFFFFFF -Workers 20`

기록 예시는 이렇습니다.

```powershell
& $py -I -B $tools\record.py --task-id ed7_j9main --task-type ed7_j9main --core mixed --mask 0x0FFFFFFF --from-sample <run>.sample.json --workers 20 --batch-id ed7_run
```

**사용자 조치 필요**: 없음.
**위임 필요**: 없음.

**메인 세션 권고**
- 총 약 5.7 h라 long-running-task-monitor를 15분 간격으로 부르고, 예약이 있으면 ID·마스크를 지시문에 넣습니다. 단계가 `.done` 대기로 이어지니 러너 로그의 `[end]`·`[stop]`·`[done]`을 먼저 grep합니다.
- 밤을 넘기므로 Windows Update 일시 중지 만료(12-21까지 확인됨), 예약 재부팅, Store 자동 업데이트(끔)를 시작 전에 확인합니다.
- 러너를 세션을 넘겨 쓸 거면 `C:\Users\jinbeom\.claude\runners\outrigger-ed7-run\` 아래에 둡니다.
- 판정 실행이라 단계 안 마스크·worker가 `0x0FFFFFFF`/20으로 기록에 남습니다. 봉인 규칙의 기록 항목과 일치하는지 실행 전 감사에서 확인합니다. 정체성 기록 변경 — 실행 전 감사 대상(steps의 `-MaskHex`·`-Workers`를 채우는 것).
- 0x0FFFFFFF에는 P SMT 형제도 들어 있습니다. 단계 안 마스크 혼합은 기록만 하면 된다고 하셔서 그대로 두었습니다.

**불확실한 판단(`추정`)**
- sens 시간(줄 구성이 달라 ±25 %).
- confirm D의 2라운드 꼬리.
- probe의 꼬리 여유.
- 12b_plan 시간(측정 없음).
- 이 PC에서 20 worker가 최적인지는 21~28 worker를 재 본 적이 없습니다.

**사용한 스킬**: 없음
