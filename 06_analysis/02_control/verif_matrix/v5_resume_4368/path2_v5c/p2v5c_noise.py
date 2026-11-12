"""436.8 path 2: v5-criteria recount of the noise bundles H-6 (dg3 v4_on) and H-8 (noise VB / V0, seedext).

**Partial tool.** The per-run noise verdict of v5 10 is the r79 sensor judge's ``pass`` (S-1~S-6, spec
405~407.2 with 419.8 / 423.1; rev6 9 names ``r79_sensor_judge.py judge ... --s4-late-loc``). That judge is a
path-1 tool for this author and the S-1~S-6 rule sentences were not re-derived here, so every per-run
noise verdict is ``undecidable`` and the L2 Clopper-Pearson grade / L1 gate / L3 record are not produced
(README Q-N1). What this tool recounts from the record fields and the rule sentences:

  rev3 #1~#3: level counts L1 167 / L2 835 / L3 501 (1,503), V0 and VB key sets equal      -> ``levels``
  rev8 #6 / 436.8 5.1 H-6, RV1-3.2: the 135 dg3 keys (L2 1 + L3 134) replace the VB noise lines;
      H-6 vs H-8 VB ``commands_sha256`` same / different (record)                          -> ``cmd_noise``
  rev6 9 / H-15: seedext 2 keys x 25 seeds per setting; seeds 0~4 hash = noise line (stop)  -> ``seedext``
  v5 10 / rev3 / 423.1: S1 front patch runs excluded from the L2 fail rate; CP limit table for the
      resulting n (two paths, ``beta.ppf`` and the ``binom.cdf`` root)                       -> ``cp_table``
  rev8 3.2 / rev9 3.2 J-P3 on VB runs (two-pressure screen: rod reading assumed)            -> ``p2_v5j.jp3``
  rev2 2.1 J9 (post-lift M2 clip) and the H-7 window rule (n_late_fallback) on every run   -> ``run_checks``
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p2v5c_common as cm  # noqa: E402

TOOL_NAME = "p2v5c_noise.py"
TOOL_VERSION = "1"
LEVEL_COUNTS = {"L1": 167, "L2": 835, "L3": 501}      # rev3 #1
H6_COUNTS = {"L2": 1, "L3": 134}                      # rev8 #6
SEEDEXT_KEYS, SEEDEXT_SEEDS, SEEDEXT_CHECK = 2, 25, 5  # rev6 9 (seeds 0~4 checked)
M2_LAW = "flow_limited_r5"
S1_FRONT = ("S1@FL", "S1@FR")                          # 423.1 / v5 10 "S1 전방 제외"
HASH_PATHS = ("commands_sha256", "r79.commands_sha256", "resume_k1.commands_sha256")


def load(path):
    d = json.loads(Path(path).read_text("utf-8"))
    return d, {r.get("key"): r for r in d.get("results") or []}


def h(rec, core):
    v, _ = core.first_path(rec, HASH_PATHS)
    return None if v is core.MISSING else v


def levels(recs):
    out = {}
    for r in recs.values():
        out[r.get("level")] = out.get(r.get("level"), 0) + 1
    return out


def s1_front(rec):
    return any(s in str(rec.get("inner", "")) for s in S1_FRONT)


def run_checks(name, recs, core, v5j, is_p3, vb, fnd):
    jp = {}
    for k, r in recs.items():
        where = f"{name}|{k}"
        if vb:
            res, why = v5j.jp3(r, is_p3, True)
            jp[res] = jp.get(res, 0) + 1
            if res == "not_applicable_tag":
                fnd.undec(where, "J-P3 not applied (tag not ③ on)")
            elif res == "H-7":
                fnd.stop("H-7", where, f"J-P3 {why}")
            elif res == "setting_defect":
                fnd.stop("J-P3-defect", where, why)
        hr = r.get("hydraulics_record") or {}
        post = hr.get("m2_clipped_steps_post_lift")
        law = (r.get("hydraulic_options") or {}).get("m2_law")
        if vb:
            if law != M2_LAW:
                fnd.undec(where, f"m2_law {law!r} (rev6 #9)")
            if isinstance(post, list) and sum(post) > 0:
                fnd.stop("H-9", where, f"m2_clipped_steps_post_lift {post}")
        elif law is not None:
            fnd.undec(where, f"V0 run with m2_law {law!r}")
        nlf = core.dig(r, "lock_window_alignment.n_late_fallback", None)
        if isinstance(nlf, int) and nlf > 0:
            fnd.stop("H-7", where, f"n_late_fallback {nlf}")
    return jp


def cp_table(n_list):
    return {str(n): {"max_fail_at_3pct": cm.cp_max_fail(n),
                     "upper_at_max_beta": cm.cp_upper_beta(cm.cp_max_fail(n), n),
                     "upper_at_max_root": cm.cp_upper_root(cm.cp_max_fail(n), n)} for n in n_list}


def seedext(name, se, noise, core, fnd):
    keys = sorted(se)
    seeds = {}
    for r in se.values():
        seeds.setdefault(r.get("inner"), set()).add(r.get("seed_index"))
    ok_shape = len(seeds) == SEEDEXT_KEYS and all(v == set(range(SEEDEXT_SEEDS)) for v in seeds.values())
    if not ok_shape or len(keys) != SEEDEXT_KEYS * SEEDEXT_SEEDS:
        fnd.stop("S-15", name, f"seedext shape {({k: len(v) for k, v in seeds.items()})}")
    chk = []
    for k, r in se.items():
        if isinstance(r.get("seed_index"), int) and r["seed_index"] < SEEDEXT_CHECK:
            n = noise.get(k)
            ha, hb = h(r, core), (None if n is None else h(n, core))
            same = n is not None and ha is not None and ha == hb
            chk.append({"key": k, "noise_found": n is not None, "same_hash": same,
                        "hash_missing": ha is None or hb is None})
            if n is None:
                fnd.stop("S-15", f"{name}|{k}", "seed 0~4 key has no noise line")
            elif ha is None or hb is None:
                fnd.undec(f"{name}|{k}", "commands hash not in the record (9.3)")
            elif not same:
                fnd.stop("H-15", f"{name}|{k}", "seed 0~4 hash differs from the noise line (rev6 9)")
    return {"runs": len(keys), "inners": {k: len(v) for k, v in seeds.items()}, "seed0_4_checked": len(chk),
            "seed0_4_same": sum(1 for c in chk if c["same_hash"]), "detail": chk}


def cmd_noise(args, repo, v5j, core):
    is_p3, mod = core.load_is_extend_start(repo)
    fnd = core.Findings()
    d_vb, vb = load(args.noise_vb)
    d_v0, v0 = load(args.noise_v0)
    d_h6, h6 = load(args.h6)
    lv_vb, lv_v0, lv_h6 = levels(vb), levels(v0), levels(h6)
    if lv_vb != LEVEL_COUNTS or lv_v0 != LEVEL_COUNTS:
        fnd.stop("S-15", "noise", f"levels VB {lv_vb} V0 {lv_v0} != {LEVEL_COUNTS}")
    if set(vb) != set(v0):
        fnd.stop("S-15", "noise", f"VB / V0 key sets differ ({len(set(vb) ^ set(v0))})")
    if lv_h6 != H6_COUNTS:
        fnd.stop("S-15", "H-6", f"levels {lv_h6} != {H6_COUNTS}")
    if not set(h6) <= set(vb):
        fnd.stop("S-15", "H-6", f"{len(set(h6) - set(vb))} dg3 keys not in the noise VB keys")
    sub = [{"key": k, "same_hash": h(r, core) is not None and h(r, core) == h(vb.get(k, {}), core),
            "hash_missing": h(r, core) is None or h(vb.get(k, {}), core) is None}
           for k, r in h6.items()]
    jp = {"noise_VB": run_checks("noise_VB", vb, core, v5j, is_p3, True, fnd),
          "H-6": run_checks("H-6", h6, core, v5j, is_p3, True, fnd)}
    run_checks("noise_V0", v0, core, v5j, is_p3, False, fnd)
    se = {}
    if args.seedext_vb:
        _, sv = load(args.seedext_vb)
        jp["seedext_VB"] = run_checks("seedext_VB", sv, core, v5j, is_p3, True, fnd)
        se["VB"] = seedext("seedext_VB", sv, vb, core, fnd)
    if args.seedext_v0:
        _, s0 = load(args.seedext_v0)
        run_checks("seedext_V0", s0, core, v5j, is_p3, False, fnd)
        se["V0"] = seedext("seedext_V0", s0, v0, core, fnd)
    n_l2 = sum(1 for r in vb.values() if r.get("level") == "L2" and not s1_front(r))
    n_l3 = sum(1 for r in vb.values() if r.get("level") == "L3" and not s1_front(r))
    fnd.undec("per-run noise verdict", "r79 S-1~S-6 verdict not recomputed by this path-2 author (README Q-N1)")
    body = {"inputs": {k: [p, cm.sha256_file(p)] for k, p in (("noise_vb", args.noise_vb),
                                                              ("noise_v0", args.noise_v0), ("h6", args.h6),
                                                              ("seedext_vb", args.seedext_vb),
                                                              ("seedext_v0", args.seedext_v0)) if p},
            "v5_options": mod,
            "levels": {"VB": lv_vb, "V0": lv_v0, "H-6": lv_h6},
            "H-6_substitution": {"keys": len(sub), "same_hash_as_H8_VB": sum(1 for s in sub if s["same_hash"]),
                                 "hash_missing": sum(1 for s in sub if s["hash_missing"]),
                                 "different": [s["key"] for s in sub
                                               if not s["same_hash"] and not s["hash_missing"]]},
            "S1_front_excluded": {"L2_n_judged": n_l2, "L3_n_record": n_l3},
            "cp_limits": cp_table(sorted({n_l2, n_l3, 835, 501})),
            "J-P3": jp, "seedext": se,
            "noise_grade": "not produced (per-run verdict undecidable)", **fnd.as_dict()}
    st = fnd.status()
    lab = {"pass": "통과", "fail": "미달", "undecidable": "판정 불가", "stop": "멈춤"}[st]
    body["grades_436_8"] = {"H-6": lab, "H-8": lab}
    body["stop_codes"] = fnd.as_dict()["stop_codes"]
    return body, st


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    cm.add_common_args(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("noise")
    n.add_argument("--noise-vb", required=True, help="resume_k1/h8_noise_VB.json")
    n.add_argument("--noise-v0", required=True, help="resume_k1/h8_noise_V0.json")
    n.add_argument("--h6", required=True, help="resume_k1/h6_dg3_v4on.json")
    n.add_argument("--seedext-vb", default=None, help="resume_k1/h8_seedext_VB.json")
    n.add_argument("--seedext-v0", default=None, help="resume_k1/h8_seedext_V0.json")
    return ap


def main(argv=None):
    return cm.run_main(TOOL_NAME, TOOL_VERSION, Path(__file__), argv, build_parser, {"noise": cmd_noise})


if __name__ == "__main__":
    sys.exit(main())
