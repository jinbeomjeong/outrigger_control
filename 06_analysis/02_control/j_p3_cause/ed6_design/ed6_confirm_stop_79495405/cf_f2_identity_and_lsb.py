"""(a) The counterfactual arm `none` against the edition 5 VBJ j9_main lines (J plant) and the
sealed arm `a1a2b3` against the confirmation (가) lines (c04 / v05 / v15): command hash equal?
(b) Per counterfactual line the lsb record summary: B3 episodes (start, end reason, travel) and
A(i) trigger counts per leg, when the line carries `lsb_record`."""
import json
from pathlib import Path

CAUSE = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause")
CF = CAUSE / "j9_runs/79495405/records_after_stop/C_a2/counterfactual.jsonl"
ED5 = CAUSE / "j9_runs/606f8713/j9main_a1/j9_main.jsonl"
CONFIRM_A = CAUSE / "j9_runs/79495405/confirm_a1/confirm_a.jsonl"
PLANT_SETTING = {"c04": "VBLc04", "v05": "VBLv05", "v15": "VBLv15"}


def key_of(job):
    twin = job.get("twin") or {}
    return (job.get("case"), twin.get("level"), twin.get("leg"), twin.get("fs_kN"),
            job.get("offset_s"))


def load(path):
    return [json.loads(t) for t in path.read_text(encoding="utf-8").splitlines() if t.strip()]


def main():
    cf = load(CF)
    ed5 = {key_of(r["job"]): r for r in load(ED5) if r["job"].get("setting") == "VBJ"}
    conf = {(r["job"]["setting"], key_of(r["job"])): r for r in load(CONFIRM_A)}
    print("== (a) hash identity")
    for r in cf:
        setting = r["job"]["setting"]
        _, plant, arm = setting.split("-")
        k = key_of(r["job"])
        if arm == "none" and plant == "J":
            ref = ed5.get(k)
            print("none/J vs ed5 VBJ", k, ref is not None and ref["commands_sha256"] == r["commands_sha256"])
        if arm == "a1a2b3" and plant in PLANT_SETTING:
            ref = conf.get((PLANT_SETTING[plant], k))
            print(f"a1a2b3/{plant} vs confirm_a", k,
                  ref is not None and ref["commands_sha256"] == r["commands_sha256"])
    print("== (b) lsb record")
    for r in cf:
        rec = r.get("lsb_record")
        setting = r["job"]["setting"]
        if not rec:
            print(setting, key_of(r["job"])[2], key_of(r["job"])[4], "no lsb_record")
            continue
        eps = rec.get("b3_episodes") or []
        short = [(round(e.get("start_t_s", e.get("t_start_s", -1)), 1), e.get("end_reason"),
                  e.get("leg")) for e in eps]
        a1 = rec.get("a1_triggers") or rec.get("a_i_triggers") or {}
        print(setting, key_of(r["job"])[2], key_of(r["job"])[4], "b3", short, "a1", a1,
              "keys", sorted(rec)[:12])


if __name__ == "__main__":
    main()
