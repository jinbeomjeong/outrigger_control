"""Read the 79495405 command hashes of a few edition 6 jobs (P7-0 references)."""
import hashlib
import json
import sys
from pathlib import Path

run = Path(sys.argv[1])
wanted = {
    ("VBL", "R12", None, 0.0, None), ("VBL", "S5", 0.0, None, None),
    ("LSL1", "R12", None, 0.0, None), ("LSL4", "S5", 0.0, None, None),
    ("VBLc04", "S5", 0.0, None, None), ("VBLv15", "R12", None, 0.0, None),
    ("VBL0", "S5", 0.0, None, None), ("VBL0", "R12", None, 0.0, None),
}
files = {"j9_main": run / "records_after_stop/B_a1/j9_main.jsonl",
         "sens": run / "records_after_stop/B_a1/sens.jsonl"}
for folder in ("impl_t8_a1", "impl_cases_a1"):
    for path in sorted((run / folder).glob("*.jsonl")):
        files[f"{folder}/{path.name}"] = path
for label, path in files.items():
    data = path.read_bytes()
    print(label, path.name, hashlib.sha256(data).hexdigest())
    for text in data.decode("utf-8").splitlines():
        line = json.loads(text)
        job = line["job"]
        key = (job["setting"], job["case"], job.get("eps") if "offset_s" not in job else None,
               job.get("offset_s"), json.dumps(job.get("twin"), sort_keys=True) if job.get("twin") else None)
        if key in wanted and "error" not in line:
            print(" ", json.dumps({k: v for k, v in job.items() if k not in ("mask", "t4h_dir")}),
                  line["commands_sha256"], line.get("controller_tag"))
