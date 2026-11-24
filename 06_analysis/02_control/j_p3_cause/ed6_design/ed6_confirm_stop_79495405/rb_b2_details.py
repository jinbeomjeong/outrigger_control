"""Details: j9main VB failing pair items, and the J-P3 sections of j9main / sens / grid (judged
rows, breaches, H-7 lines with their keys and codes)."""
import json
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
            r"\records_after_stop")


def walk(value, path=""):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, value


def main():
    j9 = json.loads((ROOT / "B_a1/j9main_judge.json").read_text(encoding="utf-8"))
    print("== j9main vb_fail_items")
    print(json.dumps(j9.get("vb_fail_items"), ensure_ascii=False)[:3000])
    for name, rel in (("j9main", "B_a1/j9main_judge.json"), ("sens", "B_a1/sens_judge.json"),
                      ("grid", "A_a1/grid_judge.json")):
        data = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        jp3 = data.get("J-P3")
        print(f"== {name} J-P3 top keys:", sorted(jp3) if isinstance(jp3, dict) else type(jp3))
        text = json.dumps(jp3, ensure_ascii=False)
        print(text[:2500])
        hits = [(p, v) for p, v in walk(jp3) if isinstance(v, str) and ("H-7" in v or "breach" in v.lower())]
        print("H-7 / breach strings:", hits[:20])


if __name__ == "__main__":
    main()
