"""sha256 of the files erratum 3 cites (bytes hashed, never printed)."""
import hashlib
import json
import subprocess
from pathlib import Path

V = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix")
F = V / "v5_resume_4368"
files = [V / "v5_resume_4368_rules_rev26_erratum2.md", V / "v5_resume_4368_rules_rev26_erratum2.sha256",
         F / "rev26_run" / "t26_identity.json", F / "rev26_run" / "audit_4prime_r2.md",
         F / "rev26_run" / "run_judgement_path1_rev26.ps1", F / "rev26_run" / "run_judgement_path2_rev26.ps1",
         F / "rev26_impl" / "path2_fix1_report.md", F / "rev26_impl" / "path2_report.md"]
out = {str(p.relative_to(V)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
out["rev26_stage5_names"] = sorted(p.name for p in (F / "rev26_stage5").iterdir())
out["rev26_run2_exists"] = (F / "rev26_run2").exists()
out["judge_rev26_74c2784_exists"] = (F / "judge_rev26_74c2784").exists()
r = subprocess.run(["git", "-C", r"C:\workspace\outrigger_control", "log", "-1", "--format=%H %s", "6c42df04"],
                   capture_output=True, text=True, timeout=60)
out["prep_commit"] = r.stdout.strip()
r = subprocess.run(["git", "-C", r"C:\workspace\outrigger_control", "check-attr", "text", "--",
                    "06_analysis/02_control/verif_matrix/v5_resume_4368/judge_rev26_74c2784/harness_path2/x.json",
                    "06_analysis/02_control/verif_matrix/v5_resume_4368/rev26_stage5/stage5_record.json",
                    "06_analysis/02_control/verif_matrix/v5_resume_4368/rev26_run2/x.ps1",
                    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26_erratum3.md"],
                   capture_output=True, text=True, timeout=60)
out["check_attr"] = r.stdout.strip().splitlines()
print(json.dumps(out, indent=1))
