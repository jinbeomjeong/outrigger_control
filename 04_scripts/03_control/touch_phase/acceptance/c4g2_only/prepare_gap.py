"""Steps for the rows of the not-rerun bundles whose K1 activity the stored records cannot show: clip_harness 13, clip_p0 17, soil_A 16 jobs (80 runs, also covers clip_A J2). Same commands as the acceptance runner with ACC_COMBO=c4g2. Writes steps_gap.json, nothing runs. Also the repeat-reapproach metric summary of the two regression files."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ACC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance")
OUT = ACC / "c4g2_only"
src = {s["id"]: s for s in json.loads((HERE.parent / "c4g2k1" / "steps_E1.json").read_text(encoding="utf-8"))}
for sub in ("regression", "soil"):
    (OUT / sub).mkdir(parents=True, exist_ok=True)
steps = []
for sid in ("reg1", "reg2", "soil_A"):
    s = json.loads(json.dumps(src[sid]))
    cmd = s["cmd"].replace(str(ACC / "regression"), str(OUT / "regression")).replace(str(ACC / "soil"), str(OUT / "soil")).replace("0x00FF0000", "0x07FF5500").replace("--workers 8", "--workers 15")
    if cmd.endswith(" 8"):
        cmd = cmd[:-2] + " 15"
    s["cmd"] = cmd
    s["env"]["ACC_COMBO"] = "c4g2"
    s["env"]["OUTRIGGER_ACC"] = "c4g2only"
    s["env"]["ACC_PROVENANCE"] = str(OUT / "provenance" / f"gap_{sid}.json")
    s["id"] = f"gap_{sid}"
    steps.append(s)
    print(s["id"], cmd[-170:], {k: v for k, v in s["env"].items() if k.startswith(("R426", "S9", "R72"))})
(HERE / "steps_gap.json").write_text(json.dumps(steps, indent=1), encoding="utf-8")
for f in ("clip_harness", "clip_p0"):
    rec = json.loads((ACC / f"regression/{f}.json").read_text(encoding="utf-8"))["records"]
    print(f, "repeat_reapproach_events", [r["metrics"].get("repeat_reapproach_events") for r in rec], "wall sum", round(sum(r["wall_s"] for r in rec)))
