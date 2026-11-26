"""b01: facts for the edition 7 judgement draft from the stored judge reports (status,
status_basis, counts, identity) and run-step records. Read only; prints JSON summaries.
Inputs are given as explicit paths (no recursive scans of parent folders)."""
import hashlib
import json
import os

R = r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\8a2a52ce"
J = R + r"\judge_60ebb4a4"
REPORTS = {"l1ref": r"l1ref_a1\l1ref.json", "t8": r"t8_a1\t8.json", "cases": r"cases_a1\cases.json",
           "probe-repro": r"probe-repro_a1\probe-repro.json", "confirm": r"confirm_a1\confirm.json",
           "j9main": r"j9main_a1\j9main.json", "sens": r"sens_a1\sens.json"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def small(o, depth=0):
    """Scalars and short lists of the top two levels (no line lists)."""
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            if isinstance(v, (int, float, str, bool)) or v is None:
                out[k] = v if not isinstance(v, str) else v[:160]
            elif isinstance(v, list):
                out[k] = v if len(json.dumps(v)) < 400 else f"list[{len(v)}]"
            elif isinstance(v, dict) and depth < 1:
                out[k] = small(v, depth + 1)
            elif isinstance(v, dict):
                out[k] = f"dict[{len(v)}]"
        return out
    return o


for name, rel in REPORTS.items():
    p = os.path.join(J, rel)
    d = json.load(open(p, encoding="utf-8"))
    print("=====", name, "sha256", sha(p))
    keep = {k: d[k] for k in ("status", "status_basis", "code_identity") if k in d}
    print(json.dumps(keep, ensure_ascii=False))
    rest = {k: v for k, v in d.items() if k not in ("inputs", "lines", "units", "rows") and k not in keep}
    s = json.dumps(small(rest), ensure_ascii=False)
    print(s[:3500])
print("===== judge SHA256SUMS", sha(os.path.join(J, "SHA256SUMS")))
print(open(os.path.join(J, "SHA256SUMS"), encoding="utf-8").read())
for step in ("l1ref", "impl_scope", "impl_t8", "impl_cases", "impl_probe", "confirm", "j9main", "sens"):
    p = os.path.join(R, step + ".done")
    d = json.load(open(p, encoding="utf-8"))
    print("done", step, sha(p)[:8], json.dumps({k: d.get(k) for k in ("exit_code", "commit", "folder", "started", "finished", "start", "end")}, ensure_ascii=False)[:400])
print("main_checks", sorted(os.listdir(os.path.join(R, "main_checks"))))
