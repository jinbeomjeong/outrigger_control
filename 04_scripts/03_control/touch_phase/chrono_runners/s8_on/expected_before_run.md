Written before any flow-on eps run (2026-11-04).

Stored flow-on row batch_COUPLED_eta085_20261104_142213 / S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0 (abs time, loop start 8.0 s):
limit acting 13.215 .. 29.4 s (delivered 18.72 mm/s, four legs, Q_sum 51.17 L/min = supply), TOUCH end 33.3, LOC 42.5, FAULT 50.3 s.
First contact (3 kN, 1 ms): FR 32.612, FL 32.631, RR 32.646, RL 32.685 s, delivered 10.462 mm/s there.
Travel from the gate at the first contact: front 344.67 mm, rear 339.50 mm.

Check 1, eps 0, gate 0, duration 7 s (to abs 15.0 s, 1.8 s into the limit): every raw signal equal to the stored run, including
flow_series rows; scaled steps counted over the limit too.
Check 2, eps 2e-3, gate 12.85, duration 7 s:
- step_series s_motor slope / flow_series v = 1 - eps = 0.998 in the limit window (18.72 mm/s -> 18.683 mm/s);
- stroke deficit at abs 15.0 s against the stored run = eps x stroke there, stroke about 39.2 mm, so about 0.078 mm;
- max scaled demand / supply <= 0.998 in the limit window; flow summary max_sum_Q_over_supply_minus_1 = 0.
Main runs: delay of the first contact = eps x travel / 10.462 mm/s.
eps 1.0e-3: deficit 0.345 / 0.340 mm, 33.0 / 32.5 ms, 0.33 of the period. eps 2.0e-3: 0.689 / 0.679 mm, 65.9 / 64.9 ms, 0.65 of the period.
Expected end points if no branch changes (weak basis): TOUCH end 33.3 or 33.4 s, LOC about 42.5 .. 42.7 s, FAULT about 50.3 .. 50.5 s.
