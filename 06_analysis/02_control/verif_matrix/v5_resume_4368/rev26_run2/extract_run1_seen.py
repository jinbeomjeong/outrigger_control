"""Extract, verbatim, the main-session tool calls (and their results) that displayed
rev26 stage-5 run-1 console/log content, between 14:19Z and 14:30Z on 2026-11-26."""
import json
import pathlib
import sys

tr = pathlib.Path(r"C:\Users\jinbeom\.claude\projects\C--workspace-outrigger-control\0d95027e-6012-4053-b99a-1e505935768c.jsonl")
out = pathlib.Path(sys.argv[1])
keys = ("rev26_stage5", "judge_rev26_335004a")
calls = {}
order = []
results = {}
for line in tr.open(encoding="utf-8"):
    try:
        o = json.loads(line)
    except ValueError:
        continue
    ts = o.get("timestamp", "")
    if not ("2026-11-26T14:19" <= ts <= "2026-11-26T14:30"):
        continue
    if o.get("isSidechain"):
        continue
    msg = o.get("message") or {}
    content = msg.get("content")
    if not isinstance(content, list):
        continue
    for c in content:
        if c.get("type") == "tool_use":
            s = json.dumps(c.get("input"), ensure_ascii=False)
            if any(k in s for k in keys):
                calls[c["id"]] = (ts, c.get("name"), c.get("input"))
                order.append(c["id"])
        elif c.get("type") == "tool_result" and c.get("tool_use_id"):
            r = c.get("content")
            if isinstance(r, list):
                r = "\n".join(x.get("text", "") for x in r if isinstance(x, dict))
            results[c["tool_use_id"]] = r
parts = []
for i, cid in enumerate(order, 1):
    ts, name, inp = calls[cid]
    parts.append(f"## 호출 {i} ({ts}, {name})\n\n입력:\n\n```\n{json.dumps(inp, ensure_ascii=False, indent=1)}\n```\n\n결과(그대로):\n\n```\n{results.get(cid, '(결과 없음)')}\n```\n")
out.write_text("\n".join(parts), encoding="utf-8", newline="\n")
print(len(order))
