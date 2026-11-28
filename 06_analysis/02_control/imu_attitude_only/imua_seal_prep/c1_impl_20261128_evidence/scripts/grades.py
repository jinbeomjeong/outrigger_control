"""IMU grade, seed and sensor model of the run_S8C p1r / v5rec cases (C-5 L2b rows and the G-d candidate)."""
import sys
from pathlib import Path

WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\v5-imua")
sys.path.insert(0, str(WT / "04_scripts" / "02_chrono"))
sys.path.insert(0, str(WT / "03_src"))
import run_S8C  # noqa: E402

tab = run_S8C.case_table()
for cid in ("K0V_top_fup3.5_Fs0", "K0_top_fup3.2_Fs0", "K0V_top_roll5.5_Fs0", "K0_top_fdown3.2_Fs0",
            "K0V_top_fdown3.5_Fs0", "E_G4_Fs8", "K0_top_rpBop_Fs0", "E_RE1bF_Fs0", "E_RE1bF_Fs8",
            "K8_top_rpB_Fs8", "S_top_fdown3.5_wika_Fs8", "K8_top_fdown3.5_Fs8", "E_G4_Fs4",
            "E_G4_Fs4_ph0.05", "G1R_FS24_FL_top_o050_Fs0", "K0_top_roll4.4_Fs0", "K0V_top_flat_Fs0"):
    c = tab[cid]
    sc = c.base.scenario
    print(cid, "grade", sc.grade, "seed", sc.seed, "sensor_model", c.base.sensor_model, "level", sc.level,
          "dur", c.duration_s, "tau_v", c.base.tau_v_s, "offset", c.base.command_offset_s)
