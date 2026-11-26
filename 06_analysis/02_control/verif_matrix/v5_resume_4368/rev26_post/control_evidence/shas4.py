"""sha256 of the files the rev26 judgement addendum cites (bytes hashed only)."""
import hashlib
import json
from pathlib import Path

V = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix")
F = V / "v5_resume_4368"
rel = ["v5_resume_4368_rules_rev26_erratum3.md", "v5_resume_4368_rules_rev26_erratum3.sha256",
       "v5_resume_4368_rules_rev26_erratum1.sha256", "v5_resume_4368_rules_rev26.sha256",
       "v5_resume_4368_harness_judgement.md",
       "v5_resume_4368/rev26_post/audit_post_run2.md", "v5_resume_4368/rev26_run2/audit_4prime_run2.md",
       "v5_resume_4368/rev26_run2/t26b_identity.json", "v5_resume_4368/rev26_run2/run_judgement_path1_rev26b.ps1",
       "v5_resume_4368/rev26_run2/run_judgement_path2_rev26b.ps1", "v5_resume_4368/rev26_run2/run1_main_seen_output.md",
       "v5_resume_4368/rev26_run2/prep_report_run2.md",
       "v5_resume_4368/rev26_stage5/stage5_record.json", "v5_resume_4368/rev26_stage5/stage5_driver.log",
       "v5_resume_4368/rev26_stage5/compare_r4_rev26.json",
       "v5_resume_4368/rev26_stage5_run2/stage5_record.json", "v5_resume_4368/rev26_stage5_run2/stage5_driver.log",
       "v5_resume_4368/rev26_stage5_run2/compare_r4_rev26b.json",
       "v5_resume_4368/judge_rev26_74c2784/harness_path1/sha256_manifest.txt",
       "v5_resume_4368/judge_rev26_74c2784/harness_path2/sha256_manifest.txt",
       "v5_resume_4368/judge_rev26_74c2784/harness_path1/u3_judge.json",
       "v5_resume_4368/judge_rev26_74c2784/harness_path2/u3.json",
       "v5_resume_4368/judge_rev26_74c2784/harness_path1/ind_las.json",
       "v5_resume_4368/rev26_run/t26_identity.json", "v5_resume_4368/rev26_impl/path1_report.md",
       "v5_resume_4368/rev26_impl/path2_report.md", "v5_resume_4368/rev26_impl/path2_fix1_report.md",
       "v5_resume_4368/rev26_run/audit_4prime.md", "v5_resume_4368/rev26_run/audit_4prime_r2.md",
       "v5_resume_4368/judge_932f1fb/_fixed/compare/compare_r4_result.json"]
out = {r: hashlib.sha256((V / r).read_bytes()).hexdigest() for r in rel}
for d in (Path(r"C:\Users\jinbeom\.claude\runners\outrigger-rev26-stage5\run_stage5.ps1"),
          Path(r"C:\Users\jinbeom\.claude\runners\outrigger-rev26-stage5-run2\run_stage5_run2.ps1")):
    out[str(d)] = hashlib.sha256(d.read_bytes()).hexdigest() if d.exists() else None
c = json.loads((F / "rev26_stage5_run2" / "compare_r4_rev26b.json").read_text("utf-8"))
out["compare_top_keys"] = list(c)[:20]
out["compare_summary"] = {k: c.get(k) for k in ("exit_code", "equal", "differ", "missing")}
il = json.loads((F / "judge_rev26_74c2784" / "harness_path1" / "ind_las.json").read_text("utf-8"))
out["ind_las"] = {k: il.get(k) for k in ("state", "status", "markers", "record_state", "adapter_defect",
                                         "gate_unreadable")}
print(json.dumps(out, indent=1, ensure_ascii=False))
