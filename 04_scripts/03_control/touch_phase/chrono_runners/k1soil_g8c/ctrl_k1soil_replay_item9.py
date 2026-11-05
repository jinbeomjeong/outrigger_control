"""Item-9 replay of the K1 soil event rows with contact_replay of commit ce21ffa, no simulation.

S9 folders hold neither pads.npz nor controller_events.json. An adapter folder in the scratchpad gets copies of record, r8_series and
result.json, the events in repr form, and pads.npz built from step_series (1 ms F_cyl, also used as interval minimum; pad normal = SCM normal).
No probe_history exists, so the seal band stays at its initial value; that only touches samples after the first PROBE, the event comes before it.
engine=None gives the raw reading (delta_i = 0, L2b-NSC rule does not apply to SCM runs).
Reproduction: WatchMode.CONTROLLER events against the recorded events. Scores: CONTINUOUS, replay_item9. Writes replay_item9.json.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np

WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\agent-a7f0f4f0aceadde2c")
sys.path.insert(0, str(WT / "03_src"))

from outrigger_sim.contact_episode import MachineConstants, build_episode  # noqa: E402
from outrigger_sim.control import c2 as c2mod  # noqa: E402
from outrigger_sim.control import contact_replay as cr  # noqa: E402
from outrigger_sim.control.c2 import C2Geometry  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.verify.s8_control import replay_item9  # noqa: E402

BATCH = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_k1soil_G1_20261105")
HERE = Path(__file__).resolve().parent
AD = HERE / "adapter"
TAGS = ("FLFs0", "FLFs8", "RRFs0")
KEEP = ("leg_reapproach_start", "leg_reapproach_contact", "leg_reapproach_deferred", "WARN_LEG_REAPPROACH_NO_CONTACT")


def adapt(name: str) -> Path:
    src, dst = BATCH / name, AD / name
    (dst / "record").mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / "record" / "record.npz", dst / "record" / "record.npz")
    shutil.copy2(src / "r8_series.npz", dst / "r8_series.npz")
    shutil.copy2(src / "result.json", dst / "result.json")
    res = json.loads((src / "result.json").read_text(encoding="utf-8"))
    (dst / "controller_events.json").write_text(json.dumps([f"C2Event(t_s={float(e['t_s'])!r}, name={str(e['name'])!r}" for e in res["events"]]), encoding="utf-8")
    z = np.load(src / "step_series.npz")
    np.savez(dst / "pads.npz", t=np.asarray(z["t_s"]), F_cyl=np.asarray(z["F_cyl_N"]), F_cyl_min_interval=np.asarray(z["F_cyl_N"]), N_raw=np.asarray(z["scm_pad_normal_N"]), N=np.asarray(z["scm_pad_normal_N"]))
    return dst


def rec_events(res, t_from):
    return [(round(float(e["t_s"]) - t_from, 3), str(e["name"])) for e in res["events"] if str(e["name"]).split(":")[0] in KEEP]


def main():
    params = load_params(level="top")
    machine = MachineConstants.from_geometry(C2Geometry.from_params(params))
    out = {"code": {"contact_replay_sha256": hashlib.sha256(Path(cr.__file__).read_bytes()).hexdigest(), "c2_sha256": hashlib.sha256(Path(c2mod.__file__).read_bytes()).hexdigest(), "contact_replay": cr.__file__, "commit": "ce21ffa"}, "rows": {}}
    print(out["code"])
    for tag in TAGS:
        for s in ("RE1bF_off", "RE1bF_on"):
            name = f"S9EV_G1_{tag}_{s}"
            d = adapt(name)
            res = json.loads((d / "result.json").read_text(encoding="utf-8"))
            t0 = float(res["t_loop_start_s"])
            tev = float(res["soil_event"]["driver"]["t_ev_s"])
            lo = res["p3b_ext"].get("t_crawler_departure_rel_s")
            ep = build_episode(d, machine)
            row = {"retrigger_samples": res["c2_lifted_reapproach"]["retrigger_samples"]}
            reps = cr.replay_both(ep, watch=cr.WatchMode.CONTROLLER)
            recorded = rec_events(res, tev)
            for judge in (cr.Judge.COMBINED, cr.Judge.PRESSURE):
                evs = [(round(float(e.t_s) - tev, 3), f"{str(e.kind)}:{('FL', 'FR', 'RL', 'RR')[e.leg]}") for e in reps[judge].events if str(e.kind).split(":")[0] in KEEP]
                rec_cmp = [(t, ":".join(n.split(":")[:2])) for t, n in recorded]
                only_rec = [x for x in rec_cmp if x not in evs]
                only_rep = [x for x in evs if x not in rec_cmp]
                row[f"controller_watch_{judge.value}"] = {"n_replay": len(evs), "n_recorded": len(rec_cmp), "only_recorded": only_rec, "only_replay": only_rep, "starts_replay": [e for e in evs if "start" in e[1]]}
            r9 = replay_item9(d, params, lo, t0, False, engine=None)
            row["status"] = r9["status"]
            row["reading"] = r9["reading"]
            for j in ("J_C", "J_P"):
                v = r9[j]
                ev = [e for e in v["events"] if e["kind"].startswith("leg_reapproach_start")]
                missed = [e for e in v["episodes"] if e.get("first_decision_s") is None]
                row[j] = {"score": {k: v["score"].get(k) for k in ("M1_missed", "M1p_late", "M2_false_action_flags", "M2_per_watched_hour", "M4_max_N", "M1_missed_upper_95")}, "n_episodes": len(v["episodes"]), "missed": missed,
                          "starts_loop_s": [[round(e["t_s"], 2), e["leg"]] for e in ev][:30], "episodes_after_event": [e for e in v["episodes"] if e["t_on_s"] >= tev - t0 - 1e-6][:30]}
            out["rows"][name] = row
            print(name, json.dumps({k: (row[k] if k.startswith("controller") else None) for k in row if k.startswith("controller")}, default=str)[:900])
            print("   J_C", row["J_C"]["score"], "missed", row["J_C"]["missed"], "| J_P", row["J_P"]["score"], "missed", row["J_P"]["missed"], "n_ep", row["J_C"]["n_episodes"], row["J_P"]["n_episodes"])
            shutil.rmtree(d)
    (HERE / "replay_item9.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
