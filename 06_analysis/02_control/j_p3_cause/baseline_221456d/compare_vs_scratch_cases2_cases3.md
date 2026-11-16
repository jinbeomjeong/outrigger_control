# 221456d baseline vs earlier scratch runs

| setting | run | sha equal | J-P3 keys equal | differing keys |
|---|---|---|---|---|
| LS4 | cases2 | True | True | - |
| VB | cases2 | True | True | - |
| LS3 | cases2 | True | True | - |
| LS2 | cases2 | True | True | - |
| LS1 | cases2 | True | True | - |
| LSH3 | cases2 | True | False | jp3c_fill_reads, jp3c_fill_breach_reads |
| VBH | cases2 | True | False | jp3c_fill_reads, jp3c_fill_breach_reads |
| LSH1 | cases2 | True | False | jp3c_fill_reads, jp3c_fill_breach_reads |
| LSH4 | cases2 | True | False | jp3c_fill_reads, jp3c_fill_breach_reads |
| LSH2 | cases2 | True | False | jp3c_fill_reads, jp3c_fill_breach_reads |
| LSJ1 | cases2 | True | False | jp3c_fill_reads, jp3c_fill_breach_reads |
| LSJ1 | cases3 | True | True | - |
| LSJ4 | cases2 | True | False | jp3c_fill_reads, jp3c_fill_breach_reads |
| LSJ4 | cases3 | True | True | - |
| LSJ3 | cases2 | True | False | jp3c_fill_reads, jp3c_fill_breach_reads |
| LSJ3 | cases3 | True | True | - |
| VBJ | cases2 | True | False | jp3c_fill_reads, jp3c_fill_breach_reads |
| VBJ | cases3 | True | True | - |
| LSJ2 | cases2 | True | False | jp3c_fill_reads, jp3c_fill_breach_reads |
| LSJ2 | cases3 | True | True | - |
| VBG4 | cases2 | True | True | - |
| VBG4 | cases3 | True | True | - |
| VBG5 | cases2 | True | False | jp3c_fill_reads, jp3c_fill_breach_reads |
| VBG5 | cases3 | True | True | - |

## min gap (bar) per leg: baseline | earlier

| setting | run | key | baseline | earlier |
|---|---|---|---|---|
| LSH3 | cases2 | jp3c_min_gap_bar | [44.9396, 44.9388, 56.4167, 55.8939] | [43.5208, 42.9344, 35.7886, 33.2274] |
| VBH | cases2 | jp3c_min_gap_bar | [44.9467, 44.9027, 56.4236, 55.8768] | [43.5318, 42.9054, 35.8049, 33.2406] |
| LSH1 | cases2 | jp3c_min_gap_bar | [45.0898, 44.734, 56.7181, 55.9804] | [43.6629, 42.7423, 35.7924, 33.2312] |
| LSH4 | cases2 | jp3c_min_gap_bar | [44.9563, 44.8728, 56.4247, 55.865] | [43.536, 42.9006, 35.8147, 33.2485] |
| LSH2 | cases2 | jp3c_min_gap_bar | [44.9225, 44.8894, 56.1872, 55.6733] | [43.5038, 42.8638, 35.8436, 33.2693] |
| LSJ1 | cases2 | jp3c_min_gap_bar | [28.1947, 24.2331, 29.618, 26.8707] | [20.8065, 18.5559, 20.4883, 17.505] |
| LSJ4 | cases2 | jp3c_min_gap_bar | [28.7181, 23.8132, 29.5134, 26.6982] | [21.3237, 18.5424, 20.3675, 17.2899] |
| LSJ3 | cases2 | jp3c_min_gap_bar | [28.5208, 23.6192, 29.4449, 26.8826] | [21.0578, 18.3688, 20.2606, 17.618] |
| VBJ | cases2 | jp3c_min_gap_bar | [28.9594, 23.6869, 17.9759, 26.8827] | [22.1427, 18.4438, 17.2296, 17.8302] |
| LSJ2 | cases2 | jp3c_min_gap_bar | [28.9268, 23.6159, 17.9535, 26.82] | [21.9699, 18.4275, 17.1802, 17.7123] |
| VBG5 | cases2 | jp3c_min_gap_bar | [45.3005, 32.0324, 34.0713, 35.4023] | [26.3462, 21.3247, 26.1246, 22.9525] |

## baseline J-P3 keys

| setting | sha | breach_reads | jp3a_breach_reads | jp3b_breach_reads | jp3b_breach_over_tol_reads | jp3c_breach_reads | jp3c_fill_reads | jp3c_fill_breach_reads | lock_ext_breach_over_tol_reads | ret_breach_reads |
|---|---|---|---|---|---|---|---|---|---|---|
| LS4 | 651a51ce7e3e | [0, 0, 0, 0] | None | None | None | None | None | None | None | None |
| VB | 295d0e7c9310 | [0, 0, 0, 2] | None | None | None | None | None | None | None | None |
| LS3 | 53ae7c735918 | [0, 0, 0, 4] | None | None | None | None | None | None | None | None |
| LS2 | 875ad53bccc3 | [0, 0, 0, 3] | None | None | None | None | None | None | None | None |
| LS1 | bd50065cc09d | [0, 0, 0, 0] | None | None | None | None | None | None | None | None |
| LSH3 | 53ae7c735918 | [0, 0, 0, 3] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [15, 24, 39, 32] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] |
| VBH | 295d0e7c9310 | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [15, 24, 39, 32] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] |
| LSH1 | bd50065cc09d | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [15, 24, 39, 32] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] |
| LSH4 | 651a51ce7e3e | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [15, 24, 39, 32] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] |
| LSH2 | 875ad53bccc3 | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [15, 24, 39, 32] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] |
| LSJ1 | 15afaa17ebcf | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [4, 7, 22, 24] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] |
| LSJ4 | 3672c7222519 | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [15, 7, 23, 24] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] |
| LSJ3 | 983ad2785c86 | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [8, 7, 23, 24] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] |
| VBJ | b3b4fb65002a | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [6, 4, 33, 22] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] |
| LSJ2 | 75c37ff55c01 | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [8, 4, 34, 22] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] |
| VBG4 | e3869a3be2f8 | [1, 0, 0, 1] | None | None | None | None | None | None | None | None |
| VBG5 | e3869a3be2f8 | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] | [6, 5, 23, 24] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] |
| LSJ4 fresh_stretch | 3672c7222519 | [0, 0, 0, 0] | [0, 0, 0, 0] | [1, 0, 0, 0] | [1, 0, 0, 0] | [0, 0, 0, 0] | [15, 7, 23, 24] | [0, 0, 0, 0] | [0, 0, 0, 0] | [0, 0, 0, 0] |

fresh_stretch LSJ4: sha 3672c7222519, jp3b_breach_over_tol_reads [1, 0, 0, 0], jp3b_min_gap_bar [-10.6743, 7.99999, 8, 8], jp3b_min_gap_t_s [49.0, 34.8, 60.9, 27.5]
