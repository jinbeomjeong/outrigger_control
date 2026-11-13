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
P2_V5J_SHA = "5772624cb28e414ceeb38af3eb6d386a2e0a78857db8a5ea9a5d3cd2ec5f7d8b"
P2_CORE_SHA = "bebed9f1663ce17a0ea24c72de67080b335109dfb83d735971fe68cff4ed9d31"

EXIT = {"pass": 0, "fail": 1, "undecidable": 1, "stop": 2}

# rev3 (sealed 2026-11-13 03:13:21 +09:00, master 9ce2fdc). p2_4368.check_seals covers the original,
# rev1 and rev2; rev3 is checked here the same way (raw sha only, LF, no BOM, .sha256 record; R2-9 last line).
_VMR = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_"
LATER_RULES = (   # sealed addenda checked here (raw sha, LF, no BOM, .sha256 record)
    (_VMR + "rev3.md", "dad8dfa68da7a988971f4d687706465289ec7dd95d09079c92215c64e5eae557", _VMR + "rev3.sha256"),
    (_VMR + "rev4.md", "7ea87a30b08a00263c597d42d3450dc56f68952e8d3205604cb2c5bab5dce14b", _VMR + "rev4.sha256"),
    (_VMR + "rev5.md", "452a8436c547e4da8d78205556cbb37633842d42cb98c18849cb883d827b3aca", _VMR + "rev5.sha256"),
    (_VMR + "rev6.md", "809e563971ea451aba7c9d0787c660bdcab1c495af39c513c8f158e09b4fe6c9", _VMR + "rev6.sha256"),
    (_VMR + "rev7.md", "e81f7d31779b0d69a140c9d90aa4684f3c9299e84aec6af06b13d48d58631502", _VMR + "rev7.sha256"),
    (_VMR + "rev8.md", "3ecafaaf33d84bb6f34a8cef5401771832a4999e4930f3644caff56eed640e56", _VMR + "rev8.sha256"),
)
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


def check_rev3(repo):
    """rev3 ~ rev8 (the name is kept for the tests); ``ok`` = all sealed addenda match (rev8 R8-4:
    file sha = code seal sha = ``.sha256`` record, else S-1)."""
    items = [_check_one(repo, *r) for r in LATER_RULES]
    return {"items": items, "ok": all(i["ok"] for i in items)}


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
            "used": ["p2_v5j.judge_pair", "p2_v5j.j_values", "p2_v5j.jp3", "p2_v5j.nrev_max_by_row",
                     "p2_v5j.pair_key", "p2_v5j.row_key", "p2_v5j.rod_reading_from_t4h", "p2_v5j.tag_of",
                     "p2_v5j.is_event", "core.check_seals", "core.load_is_extend_start", "core.Findings",
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
        seals = core.check_seals(repo)
        rev3 = check_rev3(repo)
        if not seals["ok"] or not rev3["ok"]:
            report, status = {"seals": seals, "rev3": rev3, "imports": imp, "stop_codes": ["S-1"]}, "stop"
        elif not imp["ok"] and not getattr(args, "allow_import_sha", False):
            report, status = {"imports": imp, "stop_codes": ["P2-SHA"]}, "stop"
        else:
            body, status = cmds[args.cmd](args, repo, v5j, core)
            report = {"seals": {"ok": True, "rev3": rev3, "eol_only": seals.get("eol_only", []),
                                "eol_only_detail": {k: v for k, v in seals["appendix_a"].items()
                                                    if v.get("eol_only")}},
                      "imports": imp, **body}
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


def finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def read_json_or_jsonl(path, core):
    p = str(path)
    if p.endswith(".jsonl"):
        return core.read_jsonl(p)
    return json.loads(Path(p).read_text("utf-8"))
