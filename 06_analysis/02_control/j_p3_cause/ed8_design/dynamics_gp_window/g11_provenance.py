"""G' window shift, part 11: provenance.json (input / output sha256, column definitions).
Usage: python -I -B g11_provenance.py <out_folder>
"""
import hashlib
import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
R = Path(r"C:\workspace\outrigger_control")
U = R / r"06_analysis\02_control\j_p3_cause\ed8_design\dynamics_u832_o00"
G = R / r"06_analysis\02_control\touch_phase\acceptance\c4g2_only\grid"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


inputs = [R / r"02_params\rexome33.yaml", R / r"04_scripts\03_control\s8\r67_g1_screen.py",
          R / r"04_scripts\03_control\s8\r51_reapp_closed_loop.py",
          R / r"04_scripts\01_dynamics\run_mast_flex_c2_check.py", R / r"04_scripts\01_dynamics\s8_g4_rodside_check.py",
          R / r"03_src\outrigger_sim\control\c2.py", U / "u11_periods.csv", U / "u12_exit_window.csv",
          U / "u04_v0_detail.txt", U / "u11_rerun_analysis.txt", U / "report.md"]
inputs += [G / f for f in ("grid_r67_main.json", "grid_r67_top.json", "grid_r69_bottom.json", "grid_r69_top.json")]
inputs += sorted((U / "rerun_raw" / "logs").glob("R12_bottom-F*-ready_*_rows.npz"))
outputs = sorted(p for p in out.iterdir() if p.is_file() and p.name not in ("provenance.json", "SHA256SUMS"))
columns = {
    "g01_grid_E_rows.csv": {
        "diag_start_grid_s": "first re-approach start of the event leg's diagonal (FL<->RR, FR<->RL), stored value "
                             "(0.01 s rounded) snapped to the run's 0.1 s grid 0.1 k - phi; s after the event start",
        "E": "round(diag_start_grid_s, 3) <= 0.450 (spec 6.3 reading); g01_grid_E.py:58",
        "phi_s": "offset mod 0.1 s"},
    "g02_traces.csv": {
        "t_contact_s": "first 1 ms row after the event-leg lift with pad contact force > 0; s after the event",
        "t_reload_exit_s": "first row after re-contact with F_true >= F_exit = 14.4146 kN (F_true = contact - W_rod)",
        "t_hold_end_s": "last row before the re-lift with F_true >= F_exit",
        "t_relift_s": "first row after re-contact with contact <= 0",
        "v_impact_m_s": "gap closing speed over the last 5 ms before re-contact (m/s, > 0 = approaching)",
        "contact_s": "t_relift - t_contact"},
    "g03_reading_offset.csv": {
        "offset_kN": "F_true(sample) - L(sample); L = controller lower load estimate (u11_periods, cylinder force lower "
                     "- seal band); edge 'load' = before the force peak, 'unload' = after"},
    "g05_contact_shift.csv": {
        "t_gap5mm_s": "time the stored 30 mm pad clearance falls to 5 mm (= re-contact time of a 25 mm floor, pre-lift "
                      "difference not included); linear interpolation of 1 ms rows",
        "dt_contact_25_minus_30_s": "t_gap5mm_s - t_contact_30_s (negative = earlier)"},
    "g06_variants.csv": {
        "t_r_star": "controller-effective rising edge: first row after re-contact with F_true >= F_exit + 6.1 + 2.4 F_s kN "
                    "(g03 loading offset fit), reduced model",
        "t_h_star": "controller-effective falling edge: last row before re-lift with F_true >= F_exit - 6.6 + 0.5 F_s kN",
        "d_*": "value(shape) - value(30/0.05) at the same stem / case (s)",
        "case": "ens0..ens5 = calibrated ensemble (g04); valve_off / mu0.3 / mu1.0 / dt_half = sensitivities on ens0"},
    "g07_window_m.json": {
        "P_by_phase": "P(E | condition, phi): MC over families, cluster F_s, level offset N(0, SIG_L), F_s slope se, "
                      "shape shift pairs; E <=> s1 + 0.2 <= t_h* and round(s1 + 0.2, 3) <= 0.450, s1 = first 0.1 k - phi "
                      ">= t_r* (g07_window_m.py is_E)",
        "m_vs_model_base": "mean over the 8 phases of P(E | condition) / same for 'base' (model base 0.573 vs stats 0.586)"},
    "g09_nE.json": {"P_lt_16": "fraction of 20,000 replications with n_E < 16 under the f3 slot structure (reading I)"},
}
prov = {"created": "2026-11-26", "agent": "dynamics-expert", "env": "conda dynamics-dev (python -I -B, "
        "MKL_THREADING_LAYER=TBB)", "inputs": {str(p): sha(p) for p in inputs},
        "outputs": {p.name: sha(p) for p in outputs}, "columns": columns,
        "seeds": {"g07": 20261126, "g09": 8817},
        "held_out_note": "no harness / Chrono run; the held-out shapes and F_s values were evaluated only with the own "
                         "reduced model (g00) and the empirical window model (g07)"}
(out / "provenance.json").write_text(json.dumps(prov, indent=1), encoding="utf-8")
print(json.dumps({"status": "ok", "inputs": len(inputs), "outputs": len(outputs)}))
