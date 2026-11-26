# 교차 검증 비교 (ctrl_verify compare)

- A: `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\control_k1_window\loops\py_r3.6_sigma1.5.json` (source: python-grid (ctrl_verify margins))
- B: `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\control_k1_window\loops\jl_r3.6_sigma1.5.json` (source: julia ControlSystemsBase dense grid)
- 판정: **불일치 (mismatch)** (비교 6개)

| 양 | 등급 | 지표 | 차이 | 원소별 최대 상대차 | 일치 ≤ | 허용 ≤ | 판정 | 비고 |
|---|---|---|---|---|---|---|---|---|
| gm | margin | rel_norm | 1e-10 | - | 1e-06 | 0.001 | 일치 (match) |  |
| pm_deg | margin | rel_norm | 9.36e-11 | - | 1e-06 | 0.001 | 일치 (match) |  |
| wgc | margin | rel_norm | 2.68e-10 | - | 1e-06 | 0.001 | 일치 (match) |  |
| wpc | margin | rel_norm | 6.62e-11 | - | 1e-06 | 0.001 | 일치 (match) |  |
| ms | margin | rel_norm | 6.36e-11 | - | 1e-06 | 0.001 | 일치 (match) |  |
| cl_poles | algebraic | rel_norm | inf | - | 1e-09 | 1e-06 | 불일치 (mismatch) | set sizes differ: 4 vs 3 |

B에만 있는 양(비교 안 함): dm_s

## 판정 기준

지표: rel_norm = ‖a-b‖/max(‖a‖,‖b‖)(Frobenius, 복소 집합은 헝가리안 짝짓기 뒤), abs_max = max|a-b|(sim 등급).

| 등급 | 일치 ≤ | 허용 ≤ |
|---|---|---|
| algebraic | 1e-09 | 1e-06 |
| margin | 1e-06 | 0.001 |
| mu | 0.0001 | 0.001 |
| sim | 1e-06 | 0.001 |
| residual | 1e-10 | 1e-08 |
