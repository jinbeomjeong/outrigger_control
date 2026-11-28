"""Skip reasons of a junit xml (count per message)."""
import collections
import sys
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
c = collections.Counter()
for case in root.iter("testcase"):
    for s in case.findall("skipped"):
        c[(s.get("message") or "")[:150]] += 1
for msg, n in c.most_common():
    print(n, msg)
