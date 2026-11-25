"""Print the key structure of the first rows of the ed7 probe jsonl (no values of big arrays)."""
import json
import sys

PATH = sys.argv[1]
N_ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 1


def describe(value, depth, max_depth, indent):
    pad = "  " * indent
    if isinstance(value, dict):
        print(f"{pad}dict({len(value)})")
        if depth >= max_depth:
            return
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                print(f"{pad}  {key}:")
                describe(item, depth + 1, max_depth, indent + 2)
            else:
                text = repr(item)
                print(f"{pad}  {key}: {text[:80]}")
    elif isinstance(value, list):
        head = repr(value[:3])[:120]
        print(f"{pad}list({len(value)}) {head}")
    else:
        print(f"{pad}{repr(value)[:80]}")


count = 0
with open(PATH, encoding="utf-8") as handle:
    for line in handle:
        row = json.loads(line)
        if count < N_ROWS:
            print(f"=== row {count} ({len(line)} chars)")
            describe(row, 0, 4, 0)
        count += 1
print("rows:", count)
