"""sha256 of the files erratum 2 cites (bytes are hashed, never printed)."""
import hashlib
import json
from pathlib import Path

V = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix")
F = V / "v5_resume_4368"
files = [V / "v5_resume_4368_rules_rev26.md", V / "v5_resume_4368_rules_rev26.sha256",
         V / "v5_resume_4368_rules_rev26_erratum1.md", V / "v5_resume_4368_rules_rev26_erratum1.sha256",
         F / "rev26_run" / "audit_4prime.md", F / "rev26_run" / "t26_identity.json",
         F / "rev26_run" / "run_judgement_path2_rev26.ps1",
         F / "rev26_fixed" / "excl_fields_r5.py", F / "rev26_fixed" / "rev26_excluded_fields_r5.json"]
out = {str(p.relative_to(V)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
out["rev26_fixed_file_count"] = len([p for p in (F / "rev26_fixed").iterdir() if p.is_file()])
out["rev26_fixed_dirs"] = [p.name for p in (F / "rev26_fixed").iterdir() if p.is_dir()]
out["rev26_e2_fixed"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((F / "rev26_e2_fixed").iterdir())}
print(json.dumps(out, indent=1))
