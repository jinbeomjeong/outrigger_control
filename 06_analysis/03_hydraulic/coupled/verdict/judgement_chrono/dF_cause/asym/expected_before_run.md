Written before the R12 flow-off phase run (2026-11-04).
Case E_G4_Fs4_ph0.05, flow limit off, no pad gap, preset controller, main-tree code.

Stored [kN]: off phase 0 RR 11.14 (event + 1.52 s); on phase 0 RR 12.42; on phase 0.05 RR 10.92.
Expected: r8_series equal to the stored off run until the first control sample after the event (event 49.55 s after
the settle, abs 52.55 s, first difference at abs 52.60 s). Flow limit did not act near the event in the on runs, so the
off phase 0.05 RR minimum is expected near the on phase 0.05 value, about 10.9 kN, not derived more exactly.
J_C and J_P M1 missed 0, like the three stored rows.
