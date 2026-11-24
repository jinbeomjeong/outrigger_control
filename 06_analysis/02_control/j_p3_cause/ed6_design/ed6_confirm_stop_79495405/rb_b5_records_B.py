"""Record-only B runs (j9_main 388, sens 184): per line the setting, row key, final phase,
t_ready_back / t_ready, rod fallbacks with reason, and from the T4h the longest A(i) blind-band
dwell (locked leg, 0 < |u| <= u_hold) inside any LEVEL segment and the last LEVEL length.
Writes CSV and prints summaries per file and setting, plus the R12 top-FR-Fs0 VBL lines."""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

B = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
         r"\records_after_stop\B_a1")
U_HOLD = 2.09243016e-4
PERIOD = 0.1
REASON = re.compile(r"INFO_ROD_PRESSURE_FAULT_REASON:(\w+):(\w+)")


def segments(phase):
    out, start = [], 0
    for i in range(1, len(phase) + 1):
        if i == len(phase) or phase[i] != phase[start]:
            out.append((str(phase[start]), start, i - 1))
            start = i
    return out


def band_stats(path):
    with np.load(path, allow_pickle=False) as d:
        t, ph, u, lk = d["t_s"], d["phase"], d["command_m_s"], d["locked"]
    segs = [s for s in segments(ph) if s[0] == "level"]
    longest = 0
    for _, i0, i1 in segs:
        band = lk[i0:i1 + 1] & (np.abs(u[i0:i1 + 1]) > 1e-12) & (np.abs(u[i0:i1 + 1]) <= U_HOLD)
        for leg in range(4):
            run = 0
            for flag in band[:, leg]:
                run = run + 1 if flag else 0
                longest = max(longest, run)
    last = segs[-1] if segs else None
    return round(longest * PERIOD, 1), (round(float(t[last[2]] - t[last[1]]), 1) if last else None)


def tag(job):
    twin = job.get("twin") or {}
    if twin:
        return f"{job['case']} {twin.get('level')}-{twin.get('leg')}-Fs{twin.get('fs_kN')} o{job.get('offset_s')}"
    return f"{job['case']} o{job.get('offset_s')} e{job.get('eps')}"


def main(out_csv: Path) -> None:
    rows = []
    for name in ("j9_main", "sens"):
        for text in (B / f"{name}.jsonl").read_text(encoding="utf-8").splitlines():
            if not text.strip():
                continue
            row = json.loads(text)
            job = row["job"]
            ev = row.get("event_output") or {}
            events = row.get("events") or []
            reasons = sorted({f"{m.group(1)}:{m.group(2)}" for e in events
                              for m in [REASON.search(str(e[1]))] if m})
            longest, last_level = band_stats(B / f"{name}_t4h" / row["t4h_file"])
            values = row.get("values") or {}
            rows.append({"file": name, "setting": job["setting"], "key": tag(job),
                         "final": ev.get("final_phase") or row.get("final_phase"),
                         "t_back": ev.get("t_ready_back_s"), "t_ready": values.get("t_ready"),
                         "fallback": ";".join(reasons), "band_longest_s": longest,
                         "last_level_s": last_level})
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = defaultdict(lambda: [0, 0, 0, 0])
    for r in rows:
        s = summary[(r["file"], r["setting"])]
        s[0] += 1
        s[1] += r["band_longest_s"] >= 5.0
        s[2] += r["band_longest_s"] >= 15.0
        s[3] += bool(r["fallback"])
    print("(file, setting): lines, band>=5 s, band>=15 s, fallback lines")
    for k, v in sorted(summary.items()):
        print(" ", k, v)
    print("fallback lines:")
    for r in rows:
        if r["fallback"]:
            print("  ", r["file"], r["setting"], r["key"], r["fallback"], "final", r["final"], "t_back", r["t_back"])
    print("band >= 15 s lines:")
    for r in rows:
        if r["band_longest_s"] >= 15.0:
            print("  ", r["file"], r["setting"], r["key"], "band", r["band_longest_s"], "last_level", r["last_level_s"],
                  "final", r["final"], "t_back", r["t_back"], "t_ready", r["t_ready"])
    print("R12 top-*-Fs0 in j9_main:")
    for r in rows:
        if r["file"] == "j9_main" and "top-" in r["key"] and "Fs0.0" in r["key"] and r["key"].startswith("R12"):
            print("  ", r["setting"], r["key"], "t_back", r["t_back"], "final", r["final"], "band", r["band_longest_s"])


if __name__ == "__main__":
    main(Path(sys.argv[1]))
