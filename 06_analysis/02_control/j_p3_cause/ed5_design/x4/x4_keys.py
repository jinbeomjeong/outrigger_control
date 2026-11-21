"""X-4 helper: per-family dry r79 keys (addendum 4a-8 3 rule) and their key-file sha256.

Reads only key strings (``key``, ``level``) of the case source and the Dg-3 file, and scans
key strings under 06_analysis (j9_runs excluded, 4a-6 G-1). No result value is read.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis")
NOISE = ROOT / "03_hydraulic/coupled/v5/resume_k1/h8_noise_VB.json"
DG3 = ROOT / "03_hydraulic/coupled/v5/resume_k1/h6_dg3_v4on.json"
EXCLUDED = "02_control/j_p3_cause/j9_runs/"
PATTERN = re.compile(rb'"key"\s*:\s*"((?:cand=[^"#]*#)?L\d+[A-Za-z]*\|s(\d+)\|[^"]*)"')
FAMILIES = ("g6", "g8", "ref")


def plain(key):
    return key.split("#", 1)[1] if "#" in key else key


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


noise = json.loads(NOISE.read_text(encoding="utf-8"))
dg3 = json.loads(DG3.read_text(encoding="utf-8"))
dg3_rows = dg3["results"] if isinstance(dg3, dict) else dg3
dg3_keys = {plain(r["key"]) for r in dg3_rows}
print("noise sha", sha(NOISE), "dg3 sha", sha(DG3), "dg3 keys", len(dg3_keys))

scan, files, excluded = set(), 0, 0
for p in sorted(ROOT.rglob("*")):
    if p.suffix not in (".json", ".jsonl") or not p.is_file():
        continue
    rel = p.relative_to(ROOT).as_posix()
    if rel.startswith(EXCLUDED):
        excluded += 1
        continue
    files += 1
    for key, _ in PATTERN.findall(p.read_bytes()):
        scan.add(plain(key.decode("utf-8")))
print("scan files", files, "excluded files", excluded, "keys", len(scan))

out = {}
for fam in FAMILIES:
    base = next(plain(r["key"]) for r in noise["results"]
                if r.get("level") == "L2" and plain(r["key"]).split("|")[2] == fam
                and plain(r["key"]) not in dg3_keys)
    tokens = base.split("|")
    seed = 25
    while True:
        gen = "|".join([tokens[0], f"s{seed}", *tokens[2:]])
        if gen not in scan:
            break
        seed += 1
    data = (gen + "\r\n").encode("utf-8")
    out[fam] = {"base": base, "generated": gen, "seed": seed,
                "key_file_sha256": hashlib.sha256(data).hexdigest()}
print(json.dumps(out, indent=1, ensure_ascii=False))
g6_fixed = "1a79e02fc33ae8844d0cd5672e9e5e745215c354e58e9a8095376939c4335e74"
print("g6 matches fixed:", out["g6"]["key_file_sha256"] == g6_fixed)
sys.exit(0)
