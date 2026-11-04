Written while the F_s 0 and 8 flow-off phase runs were starting, before any result of them (2026-11-04).

Rev. 44 gate D_g4 (`06_analysis/02_control/s8/s8_p1r_rev44_gate.json`), batch p1r_20261024_222013, older controller settings
(no soil_stop, no flat_soil_margin in its controller_config):
E_G4_Fs0 12.185846216270221, E_G4_Fs0_ph0.05 12.692230473759565, E_G4_Fs8 13.069607604402643, E_G4_Fs8_ph0.05 11.782433860451315 kN.

Observed before this run: the F_s 4 values of the same gate equal the final-controller values to the last digit
(E_G4_Fs4 11.143760085285908 = final_E_G4_Fs4_20261030_233941; E_G4_Fs4_ph0.05 11.834737392051006 = this session's flow-off run),
so the added soil rules do not act on this rigid row at F_s 4.
Expected: the new rows equal the gate values to the last digit, if the same holds at F_s 0 and 8. If not, report the first difference.
No final-controller phase-0 row of F_s 0 or 8 is stored; only p1 and p1r hold them.
