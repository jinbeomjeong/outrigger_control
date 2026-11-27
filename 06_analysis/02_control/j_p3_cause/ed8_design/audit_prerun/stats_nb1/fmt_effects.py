"""Format nb1_effects.json into readable TSV blocks (percent, 2 decimals)."""
import json
import sys


def pct(v):
    return f"{100 * v:.2f}"


def main():
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    L = ["# checks", json.dumps(d["checks"]), "# q_anchor", json.dumps(d["q_anchor"])]
    L.append("# Q1 n_N n_AA p0 q_name q% stop% ff% dff% pow% dpow%")
    for r in d["q1"]:
        L.append("\t".join([str(r["n_N"]), str(r["n_AA"]), str(r["p0_AA"]), r["q_name"], pct(r["q"]),
                            pct(r["p_stop"]), pct(r["false_fail"]), pct(r["d_false_fail"]),
                            pct(r["power_+2pp"]), pct(r["d_power"])]))
    L.append("# Q3 n_N n_AA p0 m_s p_s E_x stop% dstop% ff% dff% pow% dpow% E_k")
    for r in d["q3"]:
        L.append("\t".join([str(r["n_N"]), str(r["n_AA"]), str(r["p0"]), str(r["m_s"]), str(r["p_s"]),
                            f"{r['E_x_AA']:.2f}", pct(r["p_stop"]), pct(r["d_p_stop"]), pct(r["false_fail"]),
                            pct(r["d_false_fail"]), pct(r["power_+2pp"]), pct(r["d_power"]),
                            f"{r['E_k_given_go']:.2f}"]))
    L.append("# Q1Q3 p0 q% p_s stop% ff% dff% pow% dpow%")
    for r in d["q1q3"]:
        L.append("\t".join([str(r["p0"]), pct(r["q"]), str(r["p_s"]), pct(r["p_stop"]), pct(r["false_fail"]),
                            pct(r["d_false_fail"]), pct(r["power_+2pp"]), pct(r["d_power"])]))
    L.append("# Q4")
    L.append(json.dumps(d["q4"], indent=0))
    open(sys.argv[2], "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(json.dumps({"status": "ok"}))


if __name__ == "__main__":
    main()
