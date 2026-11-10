"""Write las_targeted_rules_rev5_r0k_keys.json (R-0K key list of rev5) from stored files only.

Usage: python -I -B make_r0k_keys.py <data_root> <out_json>
  data_root: checkout that holds v5/d1.jsonl (read only); the rev3 key list is read there too.
"""
import hashlib
import json
import sys
from pathlib import Path

D1_SHA = "9039b36a1a9c4ba5ed63528bb7384773018d4c7377dccbf76b18fbcfda86707f"
REV3_KEYS_SHA = "3602438d047b6a35829bda013921972411d10b0906153eba8bdc9760e7888553"
LIST_SHA = "9399c4922828973fe5129c6c5964dc2cf6c53137a8858d1f92e69f9c85452e3c"
R4 = "INFO_LOC_FLAT_SOIL_MARGIN"
PATCH_GROUPS = ("H-S-A", "H-S-A-J2")
UNIFORM_GROUPS = ("H-S-0", "H-S-1")
# las_k1_rules.md appendix A rows 41..45: S-C (b0) hashes that Y-Pa (b0 + gate) changed.
YPA_SC_HASH = {
    "D1|H-S-A-J2|G1+J2@FL|T|flat|K1|V0|e0": "4761352bd10a9a548e19bb75866c8ea6f24708365062e9e58c8ad3355ca53a24",
    "D1|H-S-A-J2|G1+J2@FL|T|flat|K1|V0|e0.002": "39278322f8775f25bf6c4e2c2f3f2ca8c4c9146f8f3b0e18365d3c8cbdc1d538",
    "D1|H-S-A-J2|G1+J2@FL|T|flat|K1|VB|e0": "84e60b8d062a472df8271a80e839af923b824a512030a67c64ab082d35b2a7eb",
    "D1|H-S-A-J2|G1+J2@FL|T|flat|K1|VB|e0.002": "66c5e1b0f1341b8c70a579d9e72e6dfa754fcd638c73e8fad87364179a1ee81b",
    "D1|H-S-A|G1+J1@FL|B|flat|K1|V0|e0.002": "ea32519dd82181468228be5c44a6e55bfb4a29e9f7fc801903f8de4e71d170fc",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    vm = root / "06_analysis" / "02_control" / "verif_matrix"
    keys_path = vm / "las_targeted_rules_rev3_keys.json"
    d1_path = root / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "d1.jsonl"
    assert sha(keys_path) == REV3_KEYS_SHA, "rev3 key list sha256"
    assert sha(d1_path) == D1_SHA, "d1.jsonl sha256"
    keys = json.loads(keys_path.read_text(encoding="utf-8"))
    lines = [json.loads(t) for t in d1_path.read_text(encoding="utf-8").splitlines() if t.strip()]
    by_key = {f"{l['job']['d1']['key']}|{l['job']['setting']}|e{float(l['job']['eps']):g}": l
              for l in lines}
    member = {}
    for bundle in ("T-3a", "T-3c"):
        for entry in keys[bundle]:
            member.setdefault(entry["key"], []).append(bundle)
    for key in keys["R-0"]["d1"]:
        member.setdefault(key, []).append("R-0")

    def r4_count(key):
        return int((by_key[key].get("event_names") or {}).get(R4, 0))

    selected = sorted({k for k in member if r4_count(k) > 0} | set(keys["R-0"]["d1"]))
    text = "".join(k + "\n" for k in selected)
    list_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert len(selected) == 45 and list_sha == LIST_SHA, (len(selected), list_sha)
    entries = []
    for key in selected:
        line = by_key[key]
        group = key.split("|")[1]
        n = r4_count(key)
        if n > 0 and group in UNIFORM_GROUPS:
            cls = "uniform_r4"
        elif n > 0 and group in PATCH_GROUPS:
            cls = "patch_r4"
        elif n == 0 and "R-0" in member[key]:
            cls = "r0_no_r4"
        else:
            raise ValueError(f"unclassified {key}")
        sc = YPA_SC_HASH.get(key)
        entries.append({
            "key": key, "group": group, "setting": line["job"]["setting"],
            "eps": float(line["job"]["eps"]), "bundles": sorted(member[key]), "class": cls,
            "stored_commands_sha256": line["commands_sha256"],
            "stored_controller_tag": line.get("controller_tag"),
            "stored_verdict": (line.get("d1") or {}).get("verdict"),
            "stored_r4c30_count": n,
            "predicted_would_block": cls == "patch_r4",
            "ypa_sc_b0_commands_sha256": sc,
            "ypa_sc_b0_equals_stored": None if sc is None else sc == line["commands_sha256"],
        })
    counts = {c: sum(1 for e in entries if e["class"] == c)
              for c in ("uniform_r4", "patch_r4", "r0_no_r4")}
    doc = {
        "schema": "las_targeted_rules_rev5_r0k_keys/1",
        "rules": "las_targeted_rules_rev5.md 2, 3",
        "selection": ("T-3a, T-3c and R-0 D-1 keys of las_targeted_rules_rev3_keys.json whose "
                      "v5/d1.jsonl line has event_names['INFO_LOC_FLAT_SOIL_MARGIN'] > 0, "
                      "union the five R-0 D-1 keys"),
        "d1_baseline": {"path": "06_analysis/03_hydraulic/coupled/v5/d1.jsonl", "sha256": D1_SHA},
        "rev3_keys": {"path": "06_analysis/02_control/verif_matrix/las_targeted_rules_rev3_keys.json",
                      "sha256": REV3_KEYS_SHA},
        "list_sha256": {"definition": "sha256 of the sorted keys, each followed by LF, UTF-8",
                        "value": list_sha},
        "count": len(entries), "class_counts": counts,
        "bundle_counts": {b: sum(1 for e in entries if b in e["bundles"])
                          for b in ("R-0", "T-3a", "T-3c")},
        "run_condition": {"las": "off", "order_gate": "on",
                          "tags": {"V0": "final_C4G2_K1", "VB": "final_C4G2_P3_K1"}},
        "R-0K": entries,
    }
    with out.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"count": len(entries), "class_counts": counts,
                      "bundle_counts": doc["bundle_counts"], "list_sha256": list_sha,
                      "ypa_equal": {k: e["ypa_sc_b0_equals_stored"] for e in entries
                                    for k in [e["key"]] if e["ypa_sc_b0_commands_sha256"]},
                      "file_sha256": sha(out)}, indent=1))


if __name__ == "__main__":
    main()
