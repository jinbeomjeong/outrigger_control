# LAS-b phase diagnosis D-b: judge aid (diag_Db.jsonl)

- verdict: **phase** (anchors pass: True, errors 0, exclusion problems 0)

## Anchors (plan 1.3)

| anchor | source | expected | got | pass |
|---|---|---|---|---|
| `A-1 VB` | las_T1.jsonl b0 act (L) | eec974b66af2 | eec974b66af2 | True |
| `A-1 V0` | las_T1.jsonl b0 act (L) | 52547a6e145e | 52547a6e145e | True |
| `A-2 VB` | fb_F2.jsonl LF | c72e663e16cf | c72e663e16cf | True |
| `A-2 V0` | fb_F2.jsonl LF | c190903359aa | c190903359aa | True |

## Points (plan 2)

| key | c | j | s | F_RL kN | TOUCH end s | lift s | start +k | rho | rho_prev | active | end | false before start | LEVEL budget | gate ok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V0 | 0.94 | 0 | 0.940000 | 9.004 | 21.20 | 22.286 | 8 | 0.3001 | 0.2412 | 5 | sum | S7_light | 0 | True |
| V0 | 0.94 | 1 | 0.938476 | 10.771 | 21.10 | 22.362 | 6 | 0.2503 | 0.2328 | 8 | sum | S7p_rise | 0 | True |
| V0 | 0.94 | 2 | 0.936956 | 9.022 | 21.20 | 22.296 | 8 | 0.2975 | 0.2388 | 5 | sum | S7_light | 0 | True |
| V0 | 0.94 | 3 | 0.935442 | 10.650 | 21.10 | 22.372 | 6 | 0.2491 | 0.2315 | 8 | sum | S7p_rise | 0 | True |
| V0 | 0.94 | 4 | 0.933932 | 8.994 | 21.30 | 22.387 | 8 | 0.2998 | 0.2410 | 5 | sum | S7_light | 0 | True |
| V0 | 1 | 0 | 1.000000 | 10.740 | 20.10 | 21.364 | 6 | 0.2497 | 0.2323 | 8 | sum | S7p_rise | 0 | True |
| V0 | 1 | 1 | 0.998275 | 9.031 | 20.30 | 21.385 | 8 | 0.3008 | 0.2419 | 5 | sum | S7_light | 0 | True |
| V0 | 1 | 2 | 0.996556 | 10.764 | 20.20 | 21.657 | 5 | 0.2327 | 0.2326 | 11 | sum | S7_sum,S7p_rise | 0 | True |
| V0 | 1 | 3 | 0.994843 | 9.037 | 20.30 | 21.386 | 8 | 0.3006 | 0.2416 | 5 | sum | S7_light | 0 | True |
| V0 | 1 | 4 | 0.993136 | 10.728 | 20.20 | 21.466 | 6 | 0.2499 | 0.2324 | 8 | sum | S7p_rise | 0 | True |
| V0 | nom | 0 | 0.876842 | 9.048 | 22.30 | 23.403 | 8 | 0.2867 | 0.2230 | 5 | sum | S7_light | 0 | True |
| V0 | nom | 1 | 0.875516 | 8.684 | 22.30 | 23.366 | 8 | 0.2930 | 0.2315 | 5 | sum | S7_light | 0 | True |
| V0 | nom | 2 | 0.874193 | 9.056 | 22.30 | 23.420 | 8 | 0.2817 | 0.2188 | 5 | sum | S7_light | 0 | True |
| V0 | nom | 3 | 0.872874 | 11.418 | 22.20 | 23.510 | 6 | 0.2439 | 0.2274 | 9 | sum | S7_sum,S7p_rise | 0 | True |
| V0 | nom | 4 | 0.871560 | 9.040 | 22.40 | 23.503 | 8 | 0.2867 | 0.2229 | 5 | sum | S7_light | 0 | True |
| VB | 0.94 | 0 | 0.940000 | 11.301 | 21.80 | 23.062 | 6 | 0.2497 | 0.2323 | 9 | sum | S7p_rise | 0 | True |
| VB | 0.94 | 1 | 0.938476 | 11.302 | 21.80 | 23.063 | 6 | 0.2495 | 0.2321 | 9 | sum | S7p_rise | 0 | True |
| VB | 0.94 | 2 | 0.936956 | 11.303 | 21.80 | 23.064 | 6 | 0.2494 | 0.2320 | 9 | sum | S7p_rise | 0 | True |
| VB | 0.94 | 3 | 0.935442 | 11.301 | 21.80 | 23.064 | 6 | 0.2493 | 0.2319 | 9 | sum | S7p_rise | 0 | True |
| VB | 0.94 | 4 | 0.933932 | 11.303 | 21.80 | 23.065 | 6 | 0.2491 | 0.2317 | 9 | sum | S7p_rise | 0 | True |
| VB | 1 | 0 | 1.000000 | 11.570 | 21.80 | 23.073 | 6 | 0.2007 | 0.1635 | 9 | sum | S7p_rise | 0 | True |
| VB | 1 | 1 | 0.998275 | 11.574 | 21.80 | 23.074 | 6 | 0.2006 | 0.1633 | 9 | sum | S7p_rise | 0 | True |
| VB | 1 | 2 | 0.996556 | 11.583 | 21.80 | 23.074 | 6 | 0.2005 | 0.1632 | 9 | sum | S7p_rise | 0 | True |
| VB | 1 | 3 | 0.994843 | 11.587 | 21.80 | 23.074 | 6 | 0.2004 | 0.1631 | 9 | sum | S7p_rise | 0 | True |
| VB | 1 | 4 | 0.993136 | 11.594 | 21.80 | 23.075 | 6 | 0.2003 | 0.1630 | 9 | sum | S7p_rise | 0 | True |
| VB | nom | 0 | 0.876842 | 8.758 | 22.30 | 23.420 | 8 | 0.2814 | 0.2206 | 5 | sum | S7_light | 0 | True |
| VB | nom | 1 | 0.875516 | 8.600 | 22.30 | 23.388 | 8 | 0.2871 | 0.2262 | 5 | sum | S7_light | 0 | True |
| VB | nom | 2 | 0.874193 | 11.494 | 22.30 | 23.673 | 6 | 0.2222 | 0.2105 | 9 | sum | S7p_rise | 0 | True |
| VB | nom | 3 | 0.872874 | 11.314 | 22.20 | 23.516 | 6 | 0.2386 | 0.2240 | 9 | sum | S7_sum,S7p_rise | 0 | True |
| VB | nom | 4 | 0.871560 | 8.734 | 22.40 | 23.520 | 8 | 0.2813 | 0.2206 | 5 | sum | S7_light | 0 | True |

## Measures (plan 3, rev1 1 .. 3)

| key | c | R_c | M_c | P_c | P2 | P3 evaluated | not started | predicting pairs | contradictions | P3 cell |
|---|---|---|---|---|---|---|---|---|---|---|
| VB | 1 | 0.017 | 11.578 | 0.024 | True | False | 0 | 10 | 0 | pass |
| VB | 0.94 | 0.002 | 11.302 | 0.002 | True | False | 0 | 10 | 0 | pass |
| VB | nom | 2.894 | 10.042 | 0.024 | True | True | 0 | 10 | 0 | pass |
| V0 | 1 | 1.733 | 9.893 | 0.012 | True | True | 0 | 10 | 0 | pass |
| V0 | 0.94 | 1.767 | 9.862 | 0.010 | True | True | 0 | 10 | 0 | pass |
| V0 | nom | 2.734 | 9.551 | 0.008 | True | True | 0 | 10 | 0 | pass |
- VB: M spread 1.537, max R_c 2.894, P4 True, direction -1, |M_1.0 - M_nom| 1.537, mixed part False, speed part False
- V0: M spread 0.342, max R_c 2.734, P4 True, direction -1, |M_1.0 - M_nom| 0.342, mixed part False, speed part False
- conditions: {'P1': True, 'P2': True, 'P3': 'pass', 'P4': True, 'phase': True, 'mixed': False, 'speed': False}
