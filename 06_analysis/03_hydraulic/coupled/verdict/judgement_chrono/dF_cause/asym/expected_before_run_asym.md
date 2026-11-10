Written before any asym run (2026-11-04).
Case A_bottom_rpB_Fs0, flow limit off, duration 40 s after settle (lift about 24.4 s).
Gap offsets (FL, FR, RL, RR) = left +2, right -2 mm + common delta. Contact stroke L-R = 4 mm for both pairs.
tau_contact = n.s_contact = (0.476 - 0.523) x 4 = -0.187 mm (n = 0.476, -0.476, -0.523, 0.523).
Approach 10.46 mm/s in the touch window (0.5 v_max), so L-R contact time difference 0.38 s, delta 0.35 mm = 33 ms of phase.
Slow approach after touch_seen: 0.25 v_max = 5.23 mm/s = 0.523 mm per 0.1 s period, so one period of one leg moves
tau by 0.25 mm (front) or 0.27 mm (rear). This is the harness step 0.25-0.3 mm.

Expected if the scatter exists in Chrono:
- D_te != 0 and differs by phase; tau_te at values tau_contact + k x 0.25-0.27 mm plus compression terms.
- Twist stiffness after lift 22 kN/mm (harness slope dD/dtau), leg force step about 0.52 x 22 x 0.25 = 3 kN.
- Symmetric gap at delta 0.35 mm: tau_te = 0 (|tau| < 0.001 mm), D_te about 0.
- Option off (ctrl_none): bits equal to the stored run up to 40 s.
- Chrono stored D_win 19.7 kN, F_RL_win 52.6 kN; harness interpolated at tau = 0: D about 18.5 kN, F_RL about 53.5 kN.
