"""D8x regression helper: hashes of every existing Chrono row definition (cad 2026-11-10).

``d8x_rules.md`` 9.3: the D8x rows are added without changing the definition, meta or argv of any
earlier row. :func:`current_hashes` hashes

* ``s6c``: every ``run_S6C.case_table()`` case: ``to_meta()`` (JSON, sorted keys) and ``repr``;
* ``s8c``: every ``run_S8C.case_table()`` case: ``to_meta()`` and ``repr``;
* ``s6c_sets`` / ``s8c_sets``: the case ids of every case set (order kept);
* ``floors``: ``s6_stage2.FLOORS`` after importing both runners (name -> (roll, pitch) deg);
* ``s9_rows``: every ``s9_batch.batches()`` row: its ``argv`` and the row (JSON) without the
  keys read from stored results (:data:`STORED_RESULT_ROW_KEYS`), with the interpreter path and
  the repository root replaced by placeholders (worktree independent).

The D8x rows / sets / floors themselves (:data:`D8X_PREFIX`, ``d8x_*`` sets, the floors of
``s6_stage2.D8X_FLOORS``) are left out, so the same function gives the baseline before the change
(``05_tests/data/d8x_existing_case_hashes.json``) and the check after it.

The hashes cover row definitions only (case meta / repr, set ids, floors, S9 argv); no C2 preset
value enters them, so the K1 switch (R4c30 order gate on in ``with_10hz_d1``, 2026-11-10) leaves
the baseline valid (checked: the diff is empty on the K1-switched master b53d890 with D8x
merged). A preset switch shows up in the run-time tags, not here. The ``s9_rows`` section was
regenerated once (2026-11-10) only to drop :data:`STORED_RESULT_ROW_KEYS`; every other section
and the row set are the 2026-11-10 D8x baseline as committed in 4014710.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CHRONO = ROOT / "04_scripts" / "02_chrono"
BASELINE = ROOT / "05_tests" / "data" / "d8x_existing_case_hashes.json"
D8X_PREFIX = "D8X_"
D8X_SETS = ("d8x_w1", "d8x_w2")
STORED_RESULT_ROW_KEYS = ("est_s", "stored_result", "stored_wall_s", "note")
"""``s9_batch`` row keys filled from the stored results in ``07_results/`` (git-ignored): a
checkout with the results (main tree) and one without (worktree) give different values, so they
are left out of the row hash. The definition is the argv and the other keys."""


def _sha(obj: Any) -> str:
    text = obj if isinstance(obj, str) else json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                                       default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _norm(obj: Any) -> Any:
    """Replace the interpreter / repository paths (rows of another checkout hash the same)."""
    text = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    for path, tag in ((sys.executable, "<PY>"), (str(ROOT), "<ROOT>")):
        text = text.replace(json.dumps(path)[1:-1], tag)
    return text


def _imports():
    for p in (str(ROOT / "03_src"), str(CHRONO)):
        if p not in sys.path:
            sys.path.insert(0, p)
    import run_S6C as s6c  # noqa: PLC0415
    import run_S8C as s8c  # noqa: PLC0415
    import s6_stage2 as st  # noqa: PLC0415
    import s9_batch as sb  # noqa: PLC0415

    return s6c, s8c, st, sb


def current_hashes() -> dict[str, dict[str, str]]:
    s6c, s8c, st, sb = _imports()
    d8x_floors = set(getattr(st, "D8X_FLOORS", {}))
    out: dict[str, dict[str, str]] = {"s6c": {}, "s8c": {}, "s6c_sets": {}, "s8c_sets": {},
                                      "floors": {}, "s9_rows": {}}
    for cid, c in s6c.case_table().items():
        if cid.startswith(D8X_PREFIX):
            continue
        out["s6c"][cid] = _sha({"meta": _sha(c.to_meta()), "repr": _sha(repr(c))})
    for cid, c in s8c.case_table().items():
        if cid.startswith(D8X_PREFIX):
            continue
        out["s8c"][cid] = _sha({"meta": _sha(c.to_meta()), "repr": _sha(repr(c))})
    for name, make in s6c.CASE_SETS.items():
        if name in D8X_SETS:
            continue
        out["s6c_sets"][name] = _sha([c.case_id for c in make()])
    for name in s8c.SET_NAMES:
        if name in D8X_SETS:
            continue
        out["s8c_sets"][name] = _sha([c.case_id for c in s8c.case_set(name)])
    for name, value in st.FLOORS.items():
        if name in d8x_floors:
            continue
        out["floors"][name] = _sha([float(v) for v in value])
    for batch, rows in sb.batches().items():
        for i, row in enumerate(rows):
            key = f"{batch}#{i}:{row.get('case')}"
            definition = {k: v for k, v in row.items() if k not in STORED_RESULT_ROW_KEYS}
            out["s9_rows"][key] = _sha({"argv": _sha(_norm(row.get("argv"))),
                                        "row": _sha(_norm(definition))})
    return out


def diff(base: dict[str, dict[str, str]], now: dict[str, dict[str, str]]) -> dict[str, Any]:
    """Keys missing / changed / added per section (added rows are allowed only for D8x)."""
    res: dict[str, Any] = {}
    for sec in base:
        b, n = base[sec], now.get(sec, {})
        res[sec] = {"missing": sorted(set(b) - set(n)),
                    "changed": sorted(k for k in set(b) & set(n) if b[k] != n[k]),
                    "added": sorted(set(n) - set(b))}
    return res
