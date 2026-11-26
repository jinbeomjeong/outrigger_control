"""d01: reproduction check of the d00 instrumented reruns against the stored edition 7 lines.

For every d00 line of arm a2 the stored line of the same job (j9main VBM / LSM4, sens VBMslow)
must have the same ``commands_sha256`` (the record-only patches change no command). For every
line: final phase, first READY time, warning / fault event names, the stored values of the same
key, and the A-arm differences.

Usage: conda run -n dynamics-dev python -I -B d01_repro_check.py <d00 scratch dir>
Output: d01_repro_check.json (this folder); stdout ASCII summary.
"""
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
J9 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\8a2a52ce")
STORED = {"M": (J9 / "j9main_a1" / "j9_main.jsonl", "VBM"),
          "LSM4": (J9 / "j9main_a1" / "j9_main.jsonl", "LSM4"),
          "Mslow": (J9 / "sens_a1" / "sens.jsonl", "VBMslow"),
          "Mh15": (J9 / "sens_a1" / "sens.jsonl", "VBMh15")}


def job_id(job: dict, setting: str) -> str:
    j = {k: v for k, v in job.items() if k not in ("mask", "t4h_dir")}
    j["setting"] = setting
    return json.dumps(j, sort_keys=True)


def summary(rec: dict) -> dict:
    v = rec.get("values", {})
    flat = {}
    for k, x in v.items():
        if isinstance(x, (int, float, str)) or x is None:
            flat[k] = x
    return {"commands_sha256": rec.get("commands_sha256"), "final_phase": rec.get("final_phase"),
            "t_event_s": rec.get("t_event_s"), "events": rec.get("events"),
            "event_names": rec.get("event_names"),
            "values_scalar": {k: flat[k] for k in sorted(flat) if any(
                s in k for s in ("ready", "done", "t_", "probe", "level"))}}


def main() -> int:
    scratch = Path(sys.argv[1])
    lines = [json.loads(s) for s in (scratch / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    wanted = {}
    for rec in lines:
        plant, arm = rec["job"]["setting"].split("-")[1:3]
        if plant in STORED:
            path, setting = STORED[plant]
            wanted.setdefault(path, {})[job_id(rec["job"], setting)] = None
    for path, ids in wanted.items():
        with path.open(encoding="utf-8") as f:
            for s in f:
                r = json.loads(s)
                key = job_id(r["job"], r["job"]["setting"])
                if key in ids:
                    ids[key] = r
    out = []
    for rec in lines:
        plant, arm = rec["job"]["setting"].split("-")[1:3]
        row = {"setting": rec["job"]["setting"], "job": {k: v for k, v in rec["job"].items()
                                                          if k not in ("mask", "t4h_dir")},
               "error": rec.get("error"), "d8": rec.get("d8"), "rerun": summary(rec)}
        if plant in STORED:
            path, setting = STORED[plant]
            stored = wanted[path].get(job_id(rec["job"], setting))
            row["stored_setting"] = setting
            row["stored"] = None if stored is None else summary(stored)
            if stored is not None:
                row["same_commands"] = stored.get("commands_sha256") == rec.get("commands_sha256")
        out.append(row)
    (OUT / "d01_repro_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for row in out:
        same = row.get("same_commands")
        ev = [e[1] for e in (row["rerun"]["events"] or [])]
        print(row["setting"], json.dumps(row["job"], sort_keys=True)[:90], "same_cmd=", same,
              "final=", row["rerun"]["final_phase"], "events=", ev[:4])
    return 0


if __name__ == "__main__":
    sys.exit(main())
