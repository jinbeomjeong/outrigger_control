"""Shared part of the 436.8 path-2 v5-criteria recount for H-6, H-8, H-9 and H-10 (``path2_v5c``).

Author: terramechanics-expert (path 2, user decision 2026-11-13). Path-1 tools and outputs were not
opened (436.8 rules 9.2). This module does not copy the path-2 common module; it imports it by path:

* ``p2_v5j.py`` (dynamics-expert, path 2, commit bf52c89, sha256 559bd34f...) for the v5 J items
  (``judge_pair``, ``j_values``, ``jp3``, ``nrev_max_by_row``, ``pair_key``, ``row_key``,
  ``rod_reading_from_t4h``, ``tag_of``) - main-session decision 2026-11-13: one J-item definition
  inside path 2.
* ``p2_4368.py`` through ``p2_v5j.core`` (seal check S-1 / R2-9, thresholds 7.6, K-10 ``same_value``,
  ``Findings``, ``load_is_extend_start``).

rev8 (3ecafaaf...): ``jp3_tag_scope`` - J-P3 applies to extend-start (3) rows only, decided by the row
tag (R8-2, rev3 R3-C8, original 4.1); a VB / LS line whose tag is not 3 on has J-P3 not applicable
(not counted as missing) and is an S-2 stop (tag differs from the 3-on tag of the setting).

rev9 (4cf7843c...): seal check (R9-8: file sha = code seal = ``.sha256`` record, else S-1). R9-1
(``expect_controller.ok``), R9-2 / R9-3 / R9-5 / R9-6 (``law_locked``) and R9-4 (LS reading by manifest and
``batch.json`` ``v5_setting``) are Chrono-row items; this folder reads harness lines only, where the LS
setting is the structured ``job.setting`` field (never a case-name token). R9-7 tag naming is not
computed here: 3 on is decided by ``p2_v5j.tag_of`` + ``is_extend_start_tag`` (``final_C4G2_K1`` = not 3).

rev10 (62a0bd8d...): seal check only (R10-3). R10-1 / R10-2 (input boundaries of the R9-4 LS reading of
Chrono rows: full batch name, manifest / ``batch.json`` row counts, manifest file) do not apply to the
harness lines read here.

rev11 (9bac4524...): seal check (R11-7). R11-2 (T4h lookup) is applied in ``p2v5c_stage1`` (the only tool
here that reads T4h) through the imported ``p2_v5j.t4h_places`` / ``rod_reading_lookup``. R11-1 (4.2
record-check expectations), R11-3 (meaning of ``commands_sha256``), R11-4 (open-loop commit identity),
R11-5 / R11-6 (G-S) do not apply to the harness lines read here.

rev12 (78f1f99b...): seal check (R12-6). R12-1 (Q-R12-1 = A): the R11-2 search applies to every J-P3 rod
reading here (stage1 H-10 lines, noise noise_VB / H-6 / seedext_VB runs, grid VB runs): a recorded
``t4h_file`` found 0 or 2+ times = S-2 and that J-P3 is not judged; only a line without the key uses the
configuration (``jp3_rod_input``). R12-3: ``noise --git-at-start`` is required. R12-2 / R12-4 / R12-5
(Chrono rows) do not apply.

R4 (436.8 R4 common block sha256 e451f067..., supplement 1 / 2; 2-terra author, a new agent run without the
earlier authors' context, from the R4 handoff for path 2-terra only): RD-2 seal list = original + rev1~rev25
(26 sheets): ``p2_4368.check_seals(r4=True)`` and ``check_rev3`` (rev3~rev25) are both run and their union must be
exactly ``RD2_SEALS`` (``rd2_union``), else S-1. RD-1 5: ``--expect-head`` (required) = ``git rev-parse HEAD``
(``p2_4368.head_check``), else S-12 and nothing is judged. RD-7 / RD-8 / RD-9 / RD-10 helpers: ``RdCounter``,
``jp3_rows`` / ``j11_rows`` (RD-7 3 columns), ``rd7_sort`` (RD-7 3 order), ``jp3_apply`` (an undecidable J-P3 stays
undecidable), ``read_jsonl_numbered`` (``line N``). RD-13: ``RD13_ITEMS`` / ``rd13_lists`` (item lists and sha256).
Supplement 4-3: ``plate_check`` (plate from the discrimination field or a one-plate file, tag compared with the
plate's expected tag; field / tag missing = S-11, other tag = S-2).

Both files are located with ``--p2-dir`` (default: ``../path2`` next to this folder, else the
dynamics-expert worktree). Their sha256 values are checked against ``P2_V5J_SHA`` / ``P2_CORE_SHA``;
a difference is a stop (exit 2, code ``P2-SHA``) because the J-item definition would have moved.

Exit codes (same contract as ``p2_4368.py``): 0 nothing failed / stopped / undecidable; 1 a fail or an
undecidable item; 2 a stop (H-*, S-*, P-*) or a rules / import sha mismatch; 3 tool error. The last
stdout line is a JSON summary (ASCII) with ``tool_sha256`` and ``out_sha256``.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import importlib.util
import json
import math
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_DEFAULT = HERE.parents[4]
P2_FALLBACK = Path(r"C:\workspace\outrigger_control\.claude\worktrees\agent-a2e81c57365f0d7bb"
                   r"\06_analysis\02_control\verif_matrix\v5_resume_4368\path2")
# rev3 versions (R3-C1~C8 in p2_v5j, rev3 seal + R3-F4 in p2_4368), files of 2026-11-13 03:16 / 03:18;
# before: p2_v5j 559bd34f... (bf52c89), p2_4368 1294dc4e...
# rev4 versions (dynamics-expert commits 6b4ebcc / dc54d25: rev4 seal, R4-C5 case_floor_deg in J3);
# rev3 versions were p2_v5j ceb75ee9..., p2_4368 cf0b643c...
# rev5 / rev6 versions (dynamics-expert commits 7b1e2e8 / d49068e; M-3: LS J11 n_late > 0 -> L-e);
# rev4 versions were p2_v5j a1675151..., p2_4368 71b87060...
# rev8 version of p2_4368 (dynamics-expert commit fd9bb68: rev8 seal, R8-2 / R8-3 Chrono rows, R8-1b
# dotted key); before: d49068e dc631509..., rev7 69b563f e033ca4b... (p2_v5j unchanged since d49068e)
# rev9 version of p2_4368 (dynamics-expert commit b0d6382: rev9 seal, R9-1..R9-6 Chrono rows, R9-4 LS by
# manifest); before: rev8 fd9bb68 bebed9f1... (p2_v5j still 5772624c...)
# rev10 version of p2_4368 (dynamics-expert commit a9594dc: rev10 seal, R10-1 / R10-2 Chrono LS input);
# before: rev9 b0d6382 7d764a80... (p2_v5j still 5772624c...)
# rev11 versions (dynamics-expert commits 582fa93 / 3eba3c5: rev11 seal, R11-2 T4h convention folders in
# p2_v5j, R11-1 / R11-4 elsewhere); before: rev10 a9594dc p2_4368 6e297ea3..., p2_v5j 5772624c...
# rev12 version of p2_4368 (dynamics-expert commit 6d41462: rev12 seal, R12-2..R12-5 Chrono rows);
# before: rev11 582fa93 a8c625bf... (p2_v5j still e5d769b9...)
# p2_v5j after user decision 24 (dynamics-expert commit e6971e5: rod_reading_lookup returns
# bad_t4h_file for a t4h_file key with None / non-string / empty value); before: e5d769b9...
# p2_4368 after user decision 19 (dynamics-expert commit c969b57: grid run tag from its job record,
# harness --gs); before: rev12 6d41462 a948d9a1...
# p2_4368 after the b9f5707 Chrono judgement (dynamics-expert branch z4372-p2chrono: C-7a / C-7b open loop,
# V0 open loop without v5_hydraulics block normal, no O-C5 main-row block on probes; decisions 19 and
# 2026-11-14); the functions used here are unchanged; before: c969b57 424e12f9...
# R4 versions (2-dyn author, branch z4373-p2harness commits 361e559 / da1e00e: RD-2 26 seals in
# check_seals, RD-1 5 head_check, RD-8 breach_reads_format / breach_reads_input, RD-10 j11_item, jp3 tag
# argument); before: p2_v5j 69d0e747..., p2_4368 0ccc5186...
# R4 supplement 3 versions (2-dyn commit 2aa0a40: p2_4368.bundle_key numeric bundle sort (3-5),
# p2_v5j.j11_item(setting_required=True) for grid runs (3-6)); before: p2_v5j 4a036b00..., p2_4368 92f6e0d4...
# R4 supplement 4 version of p2_4368 (2-dyn commit 8824499, user decisions 127 / 128); p2_v5j unchanged (b815771d...);
# before: p2_4368 dd3f266e... (2aa0a40)
# p2_4368 after 2-dyn commit 6139bb2 (user decision 129: grid run tag from results[i].controller_tag only);
# p2_v5j unchanged; before: p2_4368 76d561cc... (8824499)
P2_V5J_SHA = "b815771dcaee69f5b474a7a6328f7699631d4c69309a973314a0ba3eaf06ecb8"
P2_CORE_SHA = "51a0e7ccca2a6cbd3abfdf0c09d27fb03eac6985c31954e0b526c075ceba12e6"

EXIT = {"pass": 0, "fail": 1, "undecidable": 1, "stop": 2}

# rev3 (sealed 2026-11-13 03:13:21 +09:00, master 9ce2fdc). p2_4368.check_seals covers the original,
# rev1 and rev2; rev3 is checked here the same way (raw sha only, LF, no BOM, .sha256 record; R2-9 last line).
_VMR = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules"
# R4 common block RD-2 (sha256 e451f067...): the R4 harness tools check the original + rev1~rev25 (26 sheets);
# every sheet: raw sha (LF, no BOM) = this value = first token of the same-folder .sha256, else S-1 (all bundles).
RD2_SEALS = tuple((_VMR + ("" if n == 0 else f"_rev{n}") + ".md", sha, _VMR + ("" if n == 0 else f"_rev{n}") + ".sha256")
                  for n, sha in (
    (0, "9019b405b7a196f28a756e7ca91f443f6241a58bd8e1eee0361483066cb19524"),
    (1, "d9094fda104e25ac7eb7aea44d7c34d8215a839fc3771aa50b224d43082f02c7"),
    (2, "497e4614d6780c3201027b3946e3c21da05e2fefe9a3609436bc35ea664c3199"),
    (3, "dad8dfa68da7a988971f4d687706465289ec7dd95d09079c92215c64e5eae557"),
    (4, "7ea87a30b08a00263c597d42d3450dc56f68952e8d3205604cb2c5bab5dce14b"),
    (5, "452a8436c547e4da8d78205556cbb37633842d42cb98c18849cb883d827b3aca"),
    (6, "809e563971ea451aba7c9d0787c660bdcab1c495af39c513c8f158e09b4fe6c9"),
    (7, "e81f7d31779b0d69a140c9d90aa4684f3c9299e84aec6af06b13d48d58631502"),
    (8, "3ecafaaf33d84bb6f34a8cef5401771832a4999e4930f3644caff56eed640e56"),
    (9, "4cf7843ce469df511d7b99c7236f0b245afae9fb4ba5ad903e1c2da823a59a6d"),
    (10, "62a0bd8dd6644f78bf37d052e884061d8c14e1cc96e2babc72a6ac0618f12c29"),
    (11, "9bac452470faf74f921aa7474b3dabad781dac1ba6c3493aff998e69e430617f"),
    (12, "78f1f99b1bb27473d6e3317c58af195cc3b477829ca1439f390aeeaf32565140"),
    (13, "383bffc1f2d920dbba5b5a8c0871786a43e983d83e2d5c1e477718257f70973b"),
    (14, "baedeab499133214804167dede4c4674f9edba4e67bd711dd6418a561f60ac3f"),
    (15, "0162561c3866412f06ef3be0b3a62434e4a9ba5a37c9003be4df2f373af545ef"),
    (16, "b38991943a565a020488d1046dd6e0b5c71276cf925715fa5ba844d8819d0683"),
    (17, "9400660e2f228c3bdfaf26b1eb36cf08a753e7ebc49fbcdedc4a8ab4e0b92422"),
    (18, "3693a69c3f04eb6c5b26556ec5997d081e38f8f6fa6a581aee66ba512d122a9e"),
    (19, "7f87b8bb091d23c1bdcd2bf356b732a77bea12c4cfc4853d0ea58f7d239c92b2"),
    (20, "615a8fbd82f4ef93f1ca76b3fb4d5c24a2e602e63a997c7c56119fcc73fb5531"),
    (21, "ecd709495f203eae1769ae42e67b5ae5bf2fb457146b558c12e46d636ed03f9a"),
    (22, "a48a81f9a71091aab40f643d48ae65ba559a5c0c629e02ef3145745a095f9328"),
    (23, "fa72e1726f87f686093e36f2f3f489d5b135df6392de6aae7fe91b8739b56f97"),
    (24, "f475cf77bc610802aa36026394cbe8dbae74745c8889ac203b53a6430e1e1e15"),
    (25, "c0b778fd3f53996a2caed37e373975afea591b3c798784843cb9e7eeaac6f233"),
))
# sealed addenda checked here (raw sha, LF, no BOM, .sha256 record): rev3 ~ rev25. The original, rev1 and rev2
# are checked by the imported ``p2_4368.check_seals`` (which also checks rev3 ~ rev25, RD-2); the union of the
# two lists must be exactly RD2_SEALS (``rd2_union``), else S-1.
LATER_RULES = RD2_SEALS[3:]
REV3_REL, REV3_SHA = LATER_RULES[0][0], LATER_RULES[0][1]


def _check_one(repo, rel, want, seal_rel):
    p, sp = Path(repo) / rel, Path(repo) / seal_rel
    got = sha256_file(p) if p.is_file() else None
    words = sp.read_text("utf-8").split() if sp.is_file() else []
    seal = words[0].lower() if words else None
    raw = p.read_bytes() if p.is_file() else b""
    ok = got == want and seal == want and not raw.startswith(b"\xef\xbb\xbf") and b"\r\n" not in raw
    return {"path": rel, "sha256": got, "want": want, "seal_file_sha": seal, "ok": ok}


def jp3_tag_scope(fnd, where, res, setting_name):
    """rev8 R8-2 on a line of a 3-on setting (VB, LS). ``res`` is the ``p2_v5j.jp3`` result. A non-3 tag
    (or no tag) means J-P3 not applicable - not a missing item - and the line runs another controller
    than its setting: S-2 (original 4.1 / 8.2). Returns True when the S-2 was raised."""
    if res != "not_applicable_tag":
        return False
    fnd.stop("S-2", where, f"R8-2: {setting_name} line tag not 3 on (J-P3 not applicable, tag != setting)")
    return True


def jp3_rod_input(fnd, where, rec, dirs, v5j, config_rod, log):
    """rev12 R12-1 (Q-R12-1 = A) with rev11 R11-2 3: rod-reading input of J-P3 for one line / run.

    No ``t4h_file`` key -> ``(config_rod, True)`` (rev3 R3-C8 configuration). A recorded ``t4h_file`` must be
    found exactly once in ``dirs`` (the R11-2 search folders); 0 or 2+ files, or a None / non-string /
    empty value (``bad_t4h_file``, user decision 24, decided in ``p2_v5j.rod_reading_lookup``) -> S-2 on
    ``fnd`` and ``(None, False)``: that J-P3 is not judged and no configuration reading
    stands in. Found -> ``(reading, True)``; a found file without ``rod_pressure_Pa`` gives ``config_rod``
    (as ``p2_v5j`` does with reading None). ``log`` counts the lookup status."""
    if "t4h_file" not in rec:
        log["no_t4h_file"] = log.get("no_t4h_file", 0) + 1
        return config_rod, True
    dirs = list(dirs or [])
    rod, st, hits = v5j.rod_reading_lookup(rec, dirs)   # one definition inside path 2 (decision 24)
    log[st] = log.get(st, 0) + 1
    if st != "ok":
        fnd.stop("S-2", where, f"R12-1 / R11-2: T4h {rec.get('t4h_file')!r} {st} in {[str(d) for d in dirs]} {hits}")
        return None, False
    return (config_rod if rod is None else rod), True


def strip_jp3(items, f):
    """Drop the J-P3 result and its findings from a ``p2_v5j.judge_pair`` result when R12-1 stopped the
    line's J-P3 (the configuration reading judge_pair fell back to must not stand in)."""
    items["J-P3"] = {"result": "t4h_unresolved", "why": "R12-1: recorded T4h not found exactly once (S-2)"}
    f.stops = [s for s in f.stops if s["code"] != "J-P3-defect" and not str(s["why"]).startswith("J-P3")]
    f.undecidable = [u for u in f.undecidable if not str(u["why"]).startswith("J-P3")]


def t4h_input_error(perr):
    """rev11 R11-2 2: input error of the T4h search places -> S-11, exit 2, the bundles are not judged."""
    return {"R11-2_t4h_places": {"input_error": perr}, "not_judged": True, "stop_codes": ["S-11"]}, "stop"


def check_rev3(repo):
    """rev3 ~ rev25 (the name is kept for the tests); ``ok`` = all sealed addenda match (rev8 R8-4 .. rev12 R12-6,
    R4 RD-2: file sha = code seal sha = ``.sha256`` record, LF, no BOM, else S-1)."""
    items = [_check_one(repo, *r) for r in LATER_RULES]
    return {"items": items, "ok": all(i["ok"] for i in items)}


def rd2_union(core_seals):
    """R4 RD-2: the union of the sheets checked by ``p2_4368.check_seals`` (its ``rules`` block: path -> want)
    and by ``check_rev3`` here must be exactly the 26 sheets of RD2_SEALS with the same sha256 (and no sheet
    checked with another value). ``ok`` False = S-1 (the seal list of this run is not the RD-2 list)."""
    want = {rel: sha for rel, sha, _s in RD2_SEALS}
    seen = {}
    for rel, item in (core_seals.get("rules") or {}).items():
        seen.setdefault(rel, set()).add(item.get("want"))
    for rel, sha, _s in LATER_RULES:
        seen.setdefault(rel, set()).add(sha)
    wrong = sorted(rel for rel, shas in seen.items() if rel not in want or shas != {want[rel]})
    missing = sorted(set(want) - set(seen))
    return {"sheets": len(seen), "want_sheets": len(want), "missing": missing, "wrong": wrong,
            "ok": not missing and not wrong and len(seen) == len(want) == 26}


# ----------------------------------------------------------------- R4 harness layer (RD-7, RD-8, RD-9, RD-10, RD-13)
LEGS = ("FL", "FR", "RL", "RR")
RD7_BUNDLES = ("H-6", "H-8", "H-9", "H-10")      # bundles of this folder's RD-7 J-P3 / J11 lists (2-terra share)
MIN_GAP_BAR_KEY, FIRST_BREACH_KEY = "min_gap_bar", "first_breach_t_s"   # supplement 3-3 (decision 126)


def read_jsonl_numbered(path):
    """The lines of a jsonl file in the order of ``p2_4368.read_jsonl`` (blank lines skipped) with their physical
    line numbers (RD-7 3: ``line N``, from 1, blank lines counted). Returns (lines, numbers)."""
    lines, nums = [], []
    with open(path, encoding="utf-8") as f:
        for n, raw in enumerate(f, start=1):
            s = raw.strip()
            if s:
                lines.append(json.loads(s))
                nums.append(n)
    return lines, nums


def rel_file(path, repo):
    """RD-7 3 result file: relative to the repository root with '/' (absolute posix path outside the repo)."""
    try:
        return Path(path).resolve().relative_to(Path(repo).resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def _int_elem(seq, i):
    if isinstance(seq, list) and len(seq) == 4:
        x = seq[i]
        if isinstance(x, int) and not isinstance(x, bool):
            return x
    return None


def _num_elem(seq, i):
    """Element i of a 4-list copied as recorded when it is a finite JSON number (no rounding), else None."""
    if isinstance(seq, list) and len(seq) == 4:
        x = seq[i]
        if finite(x):
            return x
    return None


def jp3_rows(bundle, rfile, pos, rec, key, setting, core):
    """RD-7 1 / 3 J-P3 violation rows of one line / run whose J-P3 result is ``H-7`` (``breach_reads`` valid by
    RD-8, sum >= 1): one row per leg with ``breach_reads`` >= 1. Columns: bundle, result file, position, leg, key,
    setting, reads (that leg's ``breach_reads``), minimum gap [bar] and first breach time [s]: supplement 3-3
    (user decision 126) - the leg element of the record's ``min_gap_bar`` / ``first_breach_t_s`` copied without
    any computation or rounding; missing, not a number or not finite = None (JSON null)."""
    ebc, _p = core.first_path(rec, ("hydraulics_record.extend_bound_check", "v5.hydraulics_record.extend_bound_check"))
    ebc = ebc if isinstance(ebc, dict) else {}
    br = ebc.get("breach_reads")
    out = []
    for i, leg in enumerate(LEGS):
        n = _int_elem(br, i)
        if n is None or n < 1:
            continue
        out.append({"bundle": bundle, "file": rfile, "position": pos, "leg": leg, "key": key, "setting": setting,
                    "breach_reads": n, "min_gap_bar": _num_elem(ebc.get(MIN_GAP_BAR_KEY), i),
                    "first_breach_t_s": _num_elem(ebc.get(FIRST_BREACH_KEY), i)})
    return out


def j11_rows(bundle, rfile, pos, item, key, setting):
    """RD-7 1 / 3 J11 rows from a ``p2_v5j.j11_item`` result (stop setting, actual fallback leg n_late > 0):
    bundle, result file, position, leg, key, setting, ``n_late_fallback_by_leg`` of that leg, marker."""
    return [{"bundle": bundle, "file": rfile, "position": pos, "leg": r["leg"], "key": key, "setting": setting,
             "n_late_fallback_by_leg": r["n_late_fallback_by_leg"], "marker": r["marker"]}
            for r in (item.get("list") or []) if item.get("result") == "stop"]


def position_sort_key(pos):
    """RD-7 3 order of positions: the numbers of ``line N`` / ``results[i]`` / ``results[i].runs[j]`` in order."""
    import re  # noqa: PLC0415
    return tuple(int(x) for x in re.findall(r"\d+", str(pos)))


def rd7_sort(rows, bundle_key):
    """RD-7 3 order: bundle (``bundle_key`` = ``p2_4368.bundle_key``, number of ``H-n``, supplement 3-5) -> result
    file (string order) -> position (numbers) -> leg (FL, FR, RL, RR) -> k."""
    return sorted(rows, key=lambda r: (bundle_key(r["bundle"]), r["file"], position_sort_key(r["position"]),
                                       LEGS.index(r["leg"]) if r.get("leg") in LEGS else 9, r.get("k", 0)))


class RdCounter:
    """Per-bundle RD-8 / RD-9 / RD-10 counts and RD-7 rows of one tool run (``bundle_key``: ``p2_4368.bundle_key``)."""

    def __init__(self, bundle_key):
        self.bundle_key = bundle_key
        self.jp3, self.j11 = [], []
        self.p3 = {}            # RD-9: 3-on lines / runs by the row tag (original 4.1)
        self.lines = {}         # lines / runs scanned per bundle
        self.rd8 = {}           # RD-8 J-P3 undecidable: input format defect / RD-7 3 top-level mismatch
        self.rd10 = {}          # RD-10 J11 result counts (undecidable on stop settings, input_missing on records)

    def _b(self, d, b):
        return d.setdefault(b, {})

    def line(self, bundle, p3):
        self.lines[bundle] = self.lines.get(bundle, 0) + 1
        self.p3[bundle] = self.p3.get(bundle, 0) + bool(p3)

    def jp3_result(self, bundle, res, why):
        if res == "undecidable" and isinstance(why, str):
            kind = "format" if why.startswith("RD-8") else ("top_level_mismatch" if why.startswith("RD-7 3") else
                                                           "other")
            d = self._b(self.rd8, bundle)
            d[kind] = d.get(kind, 0) + 1

    def j11_result(self, bundle, item):
        d = self._b(self.rd10, bundle)
        d[item["result"]] = d.get(item["result"], 0) + 1

    def as_dict(self, bundles):
        bk = self.bundle_key
        out = {"RD-7": {"J-P3": {b: rd7_sort([r for r in self.jp3 if r["bundle"] == b], bk) for b in bundles},
                        "J11": {b: rd7_sort([r for r in self.j11 if r["bundle"] == b], bk) for b in bundles}},
               "RD-9": {b: {"p3_on": self.p3.get(b, 0), "scanned": self.lines.get(b, 0)} for b in bundles},
               "RD-8": {b: {"format": self.rd8.get(b, {}).get("format", 0),
                            "top_level_mismatch": self.rd8.get(b, {}).get("top_level_mismatch", 0)} for b in bundles},
               "RD-10": {b: {"undecidable": self.rd10.get(b, {}).get("undecidable", 0),
                             "input_missing": self.rd10.get(b, {}).get("input_missing", 0),
                             "results": dict(sorted(self.rd10.get(b, {}).items()))} for b in bundles}}
        out["markers"] = {b: rd7_markers([r for r in self.jp3 if r["bundle"] == b],
                                         [r for r in self.j11 if r["bundle"] == b]) for b in bundles}
        return out


def rd7_markers(jp3_list, j11_list):
    """RD-7 1 stop markers of one bundle: J-P3 violation -> "멈춤 H-7"; J11 -> "멈춤 H-7" (VB) / "L-e" (LS)."""
    m = {"멈춤 H-7"} if jp3_list else set()
    m |= {("멈춤 H-7" if r["marker"] == "H-7" else r["marker"]) for r in j11_list}
    return sorted(m)


P3_TAG, NOP3_TAG = "final_C4G2_P3_LAS_K1", "final_C4G2_LAS_K1"   # original 4.1 expected tags (436.8)
LS_PLATES = ("LS1", "LS2", "LS3", "LS4")


def plate_of_setting(s):
    """Supplement 4-3: plate of a run_v5 ``job.setting`` / family ``setting`` value: ``VB`` = 3 on (VB), ``LS1``~``LS4``
    = 3 on (LS), any other value = 3 none; missing / null / empty = None (S-11)."""
    if not isinstance(s, str) or not s:
        return None
    return "VB" if s == "VB" else ("LS" if s in LS_PLATES else "none")


def plate_check(fnd, where, setting, tag, fixed_plate=None, field="job.setting"):
    """Supplement 4-3: the plate comes from the discrimination field (or ``fixed_plate`` for a one-plate file), never
    from the tag; the tag is compared with the plate's expected tag. Field missing = S-11, tag missing = S-11, tag
    different = S-2. Returns the plate (None when the field is missing)."""
    plate = fixed_plate if fixed_plate is not None else plate_of_setting(setting)
    if plate is None:
        fnd.stop("S-11", where, f"supplement 4-3: discrimination field {field} missing")
        return None
    want = P3_TAG if plate in ("VB", "LS") else NOP3_TAG
    if not isinstance(tag, str) or not tag:
        fnd.stop("S-11", where, "supplement 4-3: tag missing")
    elif tag != want:
        fnd.stop("S-2", where, f"supplement 4-3: tag {tag} != {want} of plate {plate}")
    return plate


def jp3_apply(fnd, where, res, why, setting_name=None):
    """Findings of one J-P3 result outside ``judge_pair`` (noise / grid / stage1 scan): ``undecidable`` (RD-8 input
    format, RD-7 3 top-level mismatch, no rod basis) stays undecidable (never a pass), ``H-7`` stop, setting defect
    stop; a 3-on setting whose row tag is not 3 on -> R8-2 S-2."""
    if setting_name is not None and jp3_tag_scope(fnd, where, res, setting_name):
        return
    if res == "undecidable":
        fnd.undec(where, f"J-P3: {why}")
    elif res == "H-7":
        fnd.stop("H-7", where, f"J-P3 {why}")
    elif res == "setting_defect":
        fnd.stop("J-P3-defect", where, why)


def canon_sha(obj):
    """sha256 of the canonical JSON (sorted keys, ',' ':' separators, UTF-8) of a list / dict (RD-13 list sha)."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                          .encode("utf-8")).hexdigest()


# RD-13 item lists (R4 common block RD-13; columns item / basis / kind). Basis: handed-over clauses by "sheet:
# clause" (436.8 original / revN, rev16:line, R4 RDn, supplement 2-n); earlier rules not handed over are quoted
# from this folder's code comments / README as implemented ("v5 기준 ..." = v5_criteria.md + revision N,
# "spec ..." = s6_control_spec.md). Kind: 등급 항목 / 기록 / 관문 (a stop marker = 관문).
_COMMON_ITEMS = (
    ("봉인 확인 26판(S-1)", "R4 RD-2", "관문"),
    ("판정 checkout HEAD = M4(S-12)", "R4 RD-1 5", "관문"),
    ("import 고정 sha(P2-SHA)", "rev19:93 (P2-49), 지시문 2-terra 재고정 순서", "관문"),
)
_JP3 = (("J-P3 ext_moving breach_reads(멈춤 H-7, 위반 목록)",
         "rev3 R3-C8, rev4:54, rev8 R8-2, R4 RD-7 1·3, 보충 3-3·3-5", "관문"),
        ("J-P3 입력 형식(판정 불가 수)", "R4 RD-8", "관문"),
        ("J-P3 태그 범위(③ 켬 설정의 ③ 아닌 태그 = S-2)", "rev8 R8-2, 원판 4.1", "관문"),
        ("J-P3 T4h 찾기(0개·2개 이상 = S-2)", "rev12 R12-1 (C-14), rev11 R11-2 (C-23a~c)", "관문"),
        ("③ 켬 줄 수(0 = S-8)", "R4 RD-9, 원판 8.2 S-8, 보충 3-1", "관문"))
_J11 = (("J11 실제 대체 다리 n_late > 0(멈춤 H-7 / L-e, 목록)",
         "rev16:102~103 (P2-13·P2-14), rev3 R3-C7, R4 RD-7 1, 보충 3-5", "관문"),
        ("J11 블록 결측(판정 불가 수·입력 없음 수)", "R4 RD-10", "기록"))
RD13_ITEMS = {
    "H-6": _COMMON_ITEMS + _JP3 + _J11 + (
        ("줄 등급 S-1~S-6(r79 판정기 항목 행 재집계)", "v5 기준 10, rev4 R4-A2 안 c, rev3 R3-E3", "등급 항목"),
        ("S-4 시간 조항 419.8(늦은 LOC, 첫 DONE)", "v5 기준 13.2, spec 419.8, rev7 R7-2", "등급 항목"),
        ("같은 사례 L1에 없던 FAULT 이름", "rev4 R4-B6", "등급 항목"),
        ("J9 m2_clipped_steps_post_lift > 0(멈춤 H-9)", "v5 기준 개정 2 2.1, 개정 6", "관문"),
        ("m2_law 키(flow_limited_r5)", "v5 기준 개정 6 #9", "등급 항목"),
        ("줄 수 L2 1 + L3 134(S-15)", "v5 기준 개정 8 #6, rev1 RV1-3.2 (C-01)", "관문"),
        ("L3 실패 수", "rev4 R4-B6", "기록"),
        ("H-8 VB 같은 키 commands_sha256 같음", "rev1 RV1-3.2 (C-01), rev16 R16-5 (P2-12)", "기록")),
    "H-8": _COMMON_ITEMS + _JP3 + _J11 + (
        ("줄 등급 S-1~S-6(r79 판정기 항목 행 재집계)", "v5 기준 10, rev4 R4-A2 안 c, rev3 R3-E3", "등급 항목"),
        ("S-4 시간 조항 419.8(늦은 LOC, 첫 DONE)", "v5 기준 13.2, spec 419.8, rev7 R7-2", "등급 항목"),
        ("L1 관문 네 개수(경로 2 = 판정기, 다르면 S-13; 위반 = 멈춤 H-10)", "v5 기준 10, rev4 R4-B3", "관문"),
        ("L2 Clopper-Pearson ≤ 3 %(멈춤 H-10)", "v5 기준 10, v5 기준 개정 3", "관문"),
        ("L3 기록", "v5 기준 10", "기록"),
        ("seedext 시드 0~4 해시 = 잡음 L2(멈춤 H-15)", "v5 기준 개정 6 9", "관문"),
        ("seedext k/25·CP·Fisher 문구", "v5 기준 개정 6 9", "기록"),
        ("dg3 대체 135키 = H-6 줄로 판정(h8_noise_VB만, H-8 J-P3·J11 목록에서 뺌, 뺀 수 기록)",
         "rev1 RV1-3.2 (C-01), 보충 2-1, 보충 3-1·3-2", "관문"),
        ("J9 m2_clipped_steps_post_lift > 0(멈춤 H-9)", "v5 기준 개정 2 2.1, 개정 6", "관문"),
        ("m2_law 키(flow_limited_r5)", "v5 기준 개정 6 #9", "등급 항목"),
        ("수준별 줄 수 L1 167·L2 835·L3 501, VB/V0 키 집합(S-15)", "v5 기준 개정 3 #1, rev1 RV1-12 (C-16)", "관문")),
    "H-9": _COMMON_ITEMS + _JP3 + _J11 + (
        ("J1~J8·J10 V0 짝 대비(L1 등급, 그 밖 설정 기록)", "v5 기준 3·8", "기록"),
        ("J9 m2_clipped_steps_post_lift > 0(멈춤 H-9)", "v5 기준 개정 2 2.1", "관문"),
        ("VB × L1 표(VB 실패 = 멈춤)", "v5 기준 8", "관문"),
        ("L1 리밋 사이클 J8(멈춤 H-4)", "v5 기준 4·11", "관문"),
        ("P-6(L1·L2 해시 같음)·P-7(L1 ≠ V0)", "v5 기준 2", "관문"),
        ("S8 F-5 조항(흐름 끔 설정 = 멈춤 H-5)", "v5 기준 6", "관문"),
        ("pressure_only unit_status", "v5 기준 13.4", "기록"),
        ("m2_law 키(flow_limited_r5)", "v5 기준 개정 6 #9", "등급 항목"),
        ("줄 수 main 812·pressure_only 96(S-15)", "원판 5.1, rev1 RV1-12 (C-16)", "관문"),
        ("격자 행 통과 = 기록 pass(gates 논리곱과 대조), 통과→실패 (가) 목록·N_raw",
         "v5 기준 3 J1·10, rev3 R3-C3, 보충 5-2·5-3", "관문"),
        ("격자 FAULT 수·행 목록(fault_events 빈 목록 아님, 등급은 판정서)", "v5 기준 10, 보충 5-2·5-4·6-4", "기록"),
        ("격자 V0 짝 출처: 표본 8작업 같음 = 저장 V0, 다름 = h9_grid_v0, 짝 결측·해시 결측 = 판정 불가(다름보다 앞섬); "
         "짝 = (stem, 키, 사건, 위상 ±1e-9 s) 정확히 1개; V0 태그는 h9_grid_v0일 때만 대조",
         "rev3 R3-E1, rev4 R4-B4, 보충 5-1·6-1·6-2", "기록"),
        ("격자 판정 불가 행 목록(짝 0·2개 이상, V0에만 있음, pass·gates 꼴, fault_events 꼴, 등급은 판정서)",
         "원판 9.3, 보충 5-1·5-2·5-4·6-4", "기록"),
        ("격자 기록: 실패→통과·실패→실패 수", "v5 기준 10, 보충 5-3", "기록"),
        ("격자 목록 표기: 파일 = 저장소 상대 경로, 정렬 경로·키·사건·위상, 관문 이름 정렬, (다) 거짓 관문 전부",
         "R4 RD-7 3, 보충 6-1", "기록"),
        ("계열 𝓕 R-1~R-4(h9_family_F.jsonl 64줄, 짝 (key, offset_s), 늘 냄)",
         "v5 기준 개정 5 5.2, rev3 R3-E2, rev4 R4-B5, 보충 4-5", "기록"),
        ("계열 𝓕 행 표 (나)와 적용 조건(참·거짓·undecidable, V0는 5-1 짝)", "보충 4-5, 보충 5-3, 보충 6-3", "기록"),
        ("v5 H-10 격자 항: 조건 거짓 = N_raw, 참·R 통과 = N_F((다) B안: V0·VB 두 관문 뺀 논리곱), "
         "참·R 실패·판정 불가 = 멈춤 H-10, 조건 판정 불가 = 쓰는 수 없음(표지 없음)",
         "v5 기준 개정 5 5.1·5.2·11, rev3 R3-E2, 보충 4-5·5-3·5-4·6-3·6-4, 사용자 결정 129", "관문"),
        ("계열 𝓕 판정 입력 꼴 64칸·판 판별(setting)·태그 대조(S-15·S-11·S-2)", "rev4 R4-B5, 보충 4-3·4-5", "관문"),
        ("h9_stage1 판(③ 없음)·태그 대조(S-11·S-2)", "원판 4.1, 보충 4-2·4-3", "관문"),
        ("입력 파일 있음: V0 저장 격자 4·h9_family_F.jsonl(S-15)", "보충 4-2·4-4", "관문"),
        ("격자 run 태그 = results[i].controller_tag만(없음 S-11, 다름 S-2)", "rev8 R8-1, 보충 4-3·5-1, 사용자 결정 129",
         "관문"),
        ("격자 run J11 설정 = results[i].v5_setting만(없으면 J11 판정 불가)", "보충 2-2, 보충 3-6", "관문"),
        ("격자 run 수 192 × 4(S-15)", "rev1 RV1-3.2·RV1-12 (C-01·C-16)", "관문")),
    "H-10": _COMMON_ITEMS + _JP3 + _J11 + (
        ("J1~J8·J10 V0 짝 대비(VB 실패 = 멈춤 H-2)", "v5 기준 3·11", "관문"),
        ("J9 m2_clipped_steps_post_lift > 0(멈춤 H-9)", "v5 기준 개정 2 2.1", "관문"),
        ("VB 리밋 사이클 J8(멈춤 H-4)", "v5 기준 4·11", "관문"),
        ("R12 V0 사건 통과 수(멈춤 H-3)", "v5 기준 11", "관문"),
        ("LS L-a~L-e(멈춤 H-6, L-d 기록)", "v5 기준 8", "관문"),
        ("S7 분류·FL 가드 주기(멈춤 H-8)", "v5 기준 11, rev3 Q-S7", "관문"),
        ("S8 F-5 조항과 SA-4 나머지(멈춤 H-5, VB 실패 = H-2)", "v5 기준 6, rev3 R3-E5, rev4 R4-B1, rev6 R6-C1", "관문"),
        ("item8 순서(VB 뒤집힘 = 멈춤 H-11)", "v5 기준 13.1", "관문"),
        ("overlap FLAG_overlap", "v5 기준 13.3", "기록"),
        ("U-9 VB 줄 수(J-P3·J11 목록 대상, 등급은 p2_v5j u9)", "rev1 RV1-2, 보충 3-4", "기록"),
        ("줄마다 판 판별(job.setting)·태그 대조(S-11·S-2), 판별 수 기록", "원판 4.1, 보충 4-2·4-3", "관문"),
        ("m2_law 키(flow_limited_r5)", "v5 기준 개정 6 #9", "등급 항목"),
        ("줄 수 440(S-15)", "rev1 RV1-2·RV1-12 (C-16)", "관문")),
}


def rd13_lists():
    """RD-13 item lists of this folder's bundles with the sha256 of each list (canonical JSON)."""
    out = {}
    for b, items in RD13_ITEMS.items():
        rows = [{"항목": a, "근거 조항": c, "구분": k} for a, c, k in items]
        out[b] = {"items": rows, "sha256": canon_sha(rows)}
    return out


def git_commits_since(repo, base, head, rel):
    """Commits touching ``rel`` in base..head (read-only git log); None if git fails."""
    import subprocess  # noqa: PLC0415
    try:
        out = subprocess.run(["git", "-C", str(repo), "log", "--format=%H", f"{base}..{head}", "--", rel],
                             capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return [x for x in out.stdout.split() if x]


def git_diff_stat(repo, base, head, rel):
    """``git diff --stat base..head -- rel`` text (read-only); None if git fails."""
    import subprocess  # noqa: PLC0415
    try:
        out = subprocess.run(["git", "-C", str(repo), "diff", "--stat", f"{base}..{head}", "--", rel],
                             capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def git_head(repo):
    import subprocess  # noqa: PLC0415
    try:
        out = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                             timeout=60, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_p2_dir(arg=None):
    for cand in ([Path(arg)] if arg else []) + [HERE.parent / "path2", P2_FALLBACK]:
        if (cand / "p2_v5j.py").is_file() and (cand / "p2_4368.py").is_file():
            return cand
    raise FileNotFoundError("p2_v5j.py / p2_4368.py not found (give --p2-dir)")


def load_v5j(p2_dir):
    """Import ``p2_v5j.py`` by path (it loads ``p2_4368.py`` as ``core`` itself)."""
    spec = importlib.util.spec_from_file_location("p2_v5j_imported", p2_dir / "p2_v5j.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def import_record(p2_dir):
    v5j_sha = sha256_file(p2_dir / "p2_v5j.py")
    core_sha = sha256_file(p2_dir / "p2_4368.py")
    return {"p2_dir": str(p2_dir), "p2_v5j_sha256": v5j_sha, "p2_4368_sha256": core_sha,
            "ok": v5j_sha == P2_V5J_SHA and core_sha == P2_CORE_SHA,
            "used": ["p2_v5j.judge_pair", "p2_v5j.j_values", "p2_v5j.jp3", "p2_v5j.j11_item", "p2_v5j.apply_j11",
                     "p2_v5j.nrev_max_by_row",
                     "p2_v5j.pair_key", "p2_v5j.row_key", "p2_v5j.t4h_places", "p2_v5j.rod_reading_lookup",
                     "p2_v5j.tag_of", "p2_v5j.breach_reads_input", "p2_v5j.t4h_convention_dirs",
                     "p2_v5j.is_event", "core.check_seals", "core.head_check", "core.bundle_key",
                     "core.load_is_extend_start",
                     "core.Findings", "core.first_path", "core.APPENDIX_B",
                     "core.t_ge/t_lt/t_gt", "core.num", "core.dig", "core.read_jsonl", "core.F_MIN_N"]}


# ----------------------------------------------------------------- Clopper-Pearson (v5 10, rev3)
def cp_upper_beta(k, n, conf=0.95):
    """One-sided CP upper bound, path a: ``beta.ppf(conf, k+1, n-k)``."""
    from scipy.stats import beta  # noqa: PLC0415
    if k >= n:
        return 1.0
    return float(beta.ppf(conf, k + 1, n - k))


def cp_upper_root(k, n, conf=0.95):
    """One-sided CP upper bound, path b: root of ``binom.cdf(k, n, p) = 1 - conf``."""
    from scipy.optimize import brentq  # noqa: PLC0415
    from scipy.stats import binom  # noqa: PLC0415
    if k >= n:
        return 1.0
    return float(brentq(lambda p: binom.cdf(k, n, p) - (1.0 - conf), 1e-12, 1 - 1e-12, xtol=1e-14))


def cp_max_fail(n, limit=0.03, conf=0.95):
    """Largest k with CP upper <= limit (v5 rev3 table: n 835 -> 16, n 501 -> 8)."""
    k = -1
    while k + 1 <= n and cp_upper_beta(k + 1, n, conf) <= limit + 1e-12:
        k += 1
    return k


# ----------------------------------------------------------------- runner
def run_main(tool_name, version, tool_file, argv, build_parser, cmds):
    ap = build_parser()
    args = ap.parse_args(argv)
    repo = Path(args.repo) if args.repo else REPO_DEFAULT
    tool_sha = sha256_file(tool_file)
    common_sha = sha256_file(Path(__file__))
    summary = {"tool": tool_name, "version": version, "tool_sha256": tool_sha,
               "common_sha256": common_sha, "cmd": args.cmd}
    try:
        p2_dir = find_p2_dir(getattr(args, "p2_dir", None))
        imp = import_record(p2_dir)
        v5j = load_v5j(p2_dir)
        core = v5j.core
        seals = core.check_seals(repo, appendix=True, r4=True)   # R4 RD-2: original + rev1~rev25
        rev3 = check_rev3(repo)
        union = rd2_union(seals)
        head = core.head_check(repo, getattr(args, "expect_head", None))   # R4 RD-1 5
        if not seals["ok"] or not rev3["ok"] or not union["ok"]:
            report, status = {"seals": seals, "rev3": rev3, "rd2_union": union, "imports": imp,
                              "head_check": head, "stop_codes": ["S-1"]}, "stop"
        elif not imp["ok"] and not getattr(args, "allow_import_sha", False):
            report, status = {"imports": imp, "head_check": head, "stop_codes": ["P2-SHA"]}, "stop"
        elif not head["ok"]:
            report, status = {"imports": imp, "head_check": head, "not_judged": True, "stop_codes": ["S-12"]}, "stop"
        else:
            body, status = cmds[args.cmd](args, repo, v5j, core)
            report = {"seals": {"ok": True, "rev3": rev3, "rd2_union": union, "eol_only": seals.get("eol_only", []),
                                "eol_only_detail": {k: v for k, v in seals["appendix_a"].items()
                                                    if v.get("eol_only")}},
                      "imports": imp, "head_check": head, **body}
        report.update(tool=tool_name, version=version, tool_sha256=tool_sha, common_sha256=common_sha,
                      cmd=args.cmd, argv=sys.argv[1:] if argv is None else list(argv),
                      created=_dt.datetime.now().astimezone().isoformat(timespec="seconds"), status=status)
        text = json.dumps(report, indent=1, ensure_ascii=False, default=str)
        out_sha = None
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(text + "\n", encoding="utf-8", newline="\n")
            out_sha = sha256_file(args.out)
        code = EXIT[status]
        summary.update(status=status, exit=code, out=args.out, out_sha256=out_sha,
                       stop_codes=report.get("stop_codes", []))
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        code = 3
        summary.update(status="tool_error", exit=3, error=repr(exc)[:300], out_sha256=None)
    print(json.dumps(summary, ensure_ascii=True))
    return code


def add_common_args(ap):
    ap.add_argument("--repo", default=None, help="repository root (default: 5 levels above this file)")
    ap.add_argument("--out", default=None, help="output JSON path")
    ap.add_argument("--p2-dir", default=None, help="folder with p2_v5j.py / p2_4368.py")
    ap.add_argument("--allow-import-sha", action="store_true",
                    help="run although the imported path-2 files differ from the pinned sha (recorded)")
    ap.add_argument("--expect-head", required=True,
                    help="R4 RD-1 5: full 40-hex M4 commit; must equal git rev-parse HEAD of --repo (else S-12, "
                         "nothing judged)")


def finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def read_json_or_jsonl(path, core):
    p = str(path)
    if p.endswith(".jsonl"):
        return core.read_jsonl(p)
    return json.loads(Path(p).read_text("utf-8"))
