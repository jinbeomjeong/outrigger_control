"""Collapse j9j11_scan.json into one table (per file x setting) as TSV."""
import json
import sys

COLS = ["lines", "j9_judged", "j9_fail", "j11_block", "j11_fallback_line", "j11_missing_on_fallback_leg",
        "j11_fail", "any_leg_n_late_pos"]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    rep = json.load(open(src, encoding="utf-8"))
    rows = ["file\tsha8\tsetting\t" + "\t".join(COLS) + "\treasons"]
    tot = {c: 0 for c in COLS}
    for path, r in rep.items():
        short = path.split("j9_runs\\")[-1] if "j9_runs" in path else path.split("coupled\\")[-1]
        for s, k in r["by_setting"].items():
            reasons = ";".join(f"{a[len('j11_block_reason_'):]}={b}" for a, b in k.items()
                               if a.startswith("j11_block_reason_"))
            rows.append(f"{short}\t{r['sha256'][:8]}\t{s}\t" + "\t".join(str(k.get(c, 0)) for c in COLS)
                        + f"\t{reasons}")
            if s != "V0" and k.get("j9_judged", 0):
                for c in COLS:
                    tot[c] += k.get(c, 0)
    rows.append("TOTAL(non-V0 with J9 input)\t-\t-\t" + "\t".join(str(tot[c]) for c in COLS) + "\t")
    open(dst, "w", encoding="utf-8").write("\n".join(rows) + "\n")
    print(json.dumps({"status": "ok"}))


if __name__ == "__main__":
    main()
