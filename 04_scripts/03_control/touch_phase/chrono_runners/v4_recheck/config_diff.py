"""Compare stored controller configs (Oct 24 batches) with the configs current code builds for the 14 recheck cases.

No simulation runs. Output: config_diff.json next to this file, plus a short print.
Usage: python -I -B -X utf8 config_diff.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MAIN = Path(r"C:\workspace\outrigger_control")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(MAIN / "03_src"))
sys.path.insert(0, str(MAIN / "04_scripts" / "02_chrono"))

S8 = MAIN / "07_results" / "S8"
SRC = {"N_G4_Fs0_pressure": "rest_20261024_233615", "N_G4_Fs4_pressure": "rest_20261024_233615", "N_G4_Fs8_pressure": "rest_20261024_233615",
       "N_SS_Fs0_pressure": "rest_20261024_233615", "N_SS_Fs4_pressure": "rest_20261024_233615", "N_SS_Fs8_pressure": "rest_20261024_233615",
       "K0V_top_fdown3.5_Fs0": "p1r_20261024_222013", "K24_top_fdown3.5_Fs2": "rest_20261024_233615", "K8_top_fdown3.5_Fs8": "p1r_20261024_222013",
       "E_SS_Fs0": "p1r_20261024_222013", "E_SS_Fs8": "p1r_20261024_222013", "E_RE1bF_Fs0": "p1r_20261024_222013",
       "E_RE1bP_Fs0": "p1r_20261024_222013", "E_RE1bP_Fs8": "p1r_20261024_222013"}
TOKEN = re.compile(r"([A-Za-z_][A-Za-z_0-9]*)=")


def flatten(text: str) -> dict[str, str]:
    """Flatten a dataclass repr into dotted-name -> scalar text (best effort; bracket aware)."""
    out: dict[str, str] = {}

    def walk(s: str, prefix: str) -> None:
        depth, i, n = 0, 0, len(s)
        key, start = None, 0
        while i < n:
            ch = s[i]
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch in "'\"":
                q = ch
                i += 1
                while i < n and s[i] != q:
                    i += 1
            elif depth == 0 and ch == "=" and key is None:
                key = s[start:i].strip()
                start = i + 1
            elif depth == 0 and ch == "," and s[i + 1:i + 2] == " ":
                if key is not None:
                    store(key, s[start:i], prefix)
                key, start = None, i + 2
                i += 1
            i += 1
        if key is not None:
            store(key, s[start:], prefix)

    def store(key: str, value: str, prefix: str) -> None:
        value = value.strip()
        m = re.match(r"^[A-Za-z_][A-Za-z_0-9.]*\((.*)\)$", value, re.S)
        if m and TOKEN.search(m.group(1)):
            walk(m.group(1), f"{prefix}{key}.")
        else:
            out[f"{prefix}{key}"] = value

    m = re.match(r"^[A-Za-z_][A-Za-z_0-9.]*\((.*)\)$", text, re.S)
    walk(m.group(1) if m else text, "")
    return out


def main() -> None:
    import run_S8C as s8

    table = s8.case_table()
    report = {}
    for cid, batch in SRC.items():
        case = table[cid]
        old = json.loads((S8 / batch / cid / "result.json").read_text(encoding="utf-8"))["settings"]
        old_text = old["controller_config"]
        params, params_ctrl, _over = s8.l2b_params(case)
        _c2, cfg, settle, ratio = s8._controller(case, params_ctrl, params)
        new_text = str(cfg)
        a, b = flatten(old_text), flatten(new_text)
        changed = {k: [a[k], b[k]] for k in a.keys() & b.keys() if a[k] != b[k]}
        report[cid] = {"old_len": len(old_text), "new_len": len(new_text), "old_truncated": old_text.endswith("...") or len(old_text) <= 4001,
                       "contact_old": old.get("contact"), "contact_new": str(cfg.contact), "added": {k: b[k] for k in sorted(b.keys() - a.keys())},
                       "removed": {k: a[k] for k in sorted(a.keys() - b.keys())}, "changed": dict(sorted(changed.items())),
                       "touch_new": {k: getattr(cfg.r8, k) for k in ("touch_free_air_min_travel_m", "touch_free_air_cap_excess_N", "touch_hold_dip_samples", "touch_seen_samples")},
                       "h4": str(cfg.reanchor.enable), "soil_stop": getattr(cfg.r8, "soil_stop", None), "ratio": ratio}
    (HERE / "config_diff.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    for cid, r in report.items():
        print(cid, "old_len", r["old_len"], "new_len", r["new_len"], "trunc", r["old_truncated"], "contact", r["contact_old"], r["contact_new"], "h4", r["h4"],
              "added", len(r["added"]), "removed", len(r["removed"]), "changed", len(r["changed"]))
    r = report["N_G4_Fs8_pressure"]
    print("touch_new", r["touch_new"])
    print("CHANGED", json.dumps(r["changed"], indent=0)[:5000])
    print("ADDED", list(r["added"])[:200])
    print("REMOVED", list(r["removed"])[:60])


if __name__ == "__main__":
    main()
