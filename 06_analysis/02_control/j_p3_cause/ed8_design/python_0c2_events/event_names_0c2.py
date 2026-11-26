"""Edition 8 S8-R step 0c': can every census event row name its event and its event leg?

Read only and value blind. Spec 6.3: the event name of a unit is the ``event`` of its job twin,
else the case default (``verdict_cases.py`` CASES); the event leg is the twin ``leg``, else the
case default. The unit job is

- C-J: the ``job`` of the edition 7 ``j9_main.jsonl`` line (settings VBM / LSM<n>)
- C-S: the ``job`` of the ``sens_keys_ed7.json`` line (settings VBM<key>)
- C-D: the ``job`` of the ``d_grid_keys12.json`` entry (key file side; 12 keys, census 24)
- C-G: the ``job`` of the ``confirm_g1_grid171.json`` line (key file side)

For every event row the script counts where the name and the leg come from (twin / default /
undetermined) and whether the name is a key of ``r67_g1_screen.EVENTS`` and the leg one of
``r67_g1_screen.LEGS``. The case defaults, the ``EventTwin`` field names, ``EVENTS`` and ``LEGS``
are read from the source with ``ast`` (no project import, no code execution).

As a cross-check (counts only) the resolved name and leg are compared with the V0 pair record
where it stores them: top-level ``event`` / ``leg`` of the main.jsonl V0 line or the grid run
(absent keys are counted as absent). No event name, leg, E candidate, layer or start time is
written: the output holds row counts, key-name sets and sha256 digests only.

Usage: python -I -B event_names_0c2.py <repo root> <out json>
Exit codes: 0 every event row has a name in EVENTS and a leg in LEGS and every input sha matches,
1 an undetermined name or leg, a name outside EVENTS, a twin key outside EventTwin, a pairing
gap or a sha difference, 2 input error, 3 internal error.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
import traceback
from collections import Counter
from pathlib import Path

MAIN_JSONL = "06_analysis/03_hydraulic/coupled/v5/main.jsonl"
MAIN_SHA = "9ad749907c34c9e9efb77579a8ab6e3b1f86cdc32d36162c0029005ca545b29e"
J9_MAIN = (
    "06_analysis/02_control/j_p3_cause/j9_runs/8a2a52ce/j9main_a1/j9_main.jsonl",
    "c89ec827ce541a53127a0115b8e1185b35e50df9cea2612d4a74b40cc618c122",
)
SENS_KEYS = (
    "06_analysis/02_control/j_p3_cause/ed7_design/keys_seal_b46bdf8f/sens_keys_ed7.json",
    "be930b75a375877d07fc84fa98a9f8b0ee463f5b592319cfd6869fcc62a05b1b",
)
G1_KEYS = (
    "06_analysis/02_control/j_p3_cause/ed7_design/keys_seal_b46bdf8f/confirm_g1_grid171.json",
    "684054abb1ad05d8f82141f58eafdfa3c096edae1c05c9a4b9e8ae9ffe5b5dec",
)
GRID192_KEYS = (
    "06_analysis/02_control/j_p3_cause/ed6_design/keys/confirm_b_grid192.json",
    "4e80e69bd2233b994853ae3f60ed0749f2c39c7dbb6390bc012b016efa5cf85b",
)
D_KEYS_REV = "3ecf61f1"
D_KEYS_PATH = "06_analysis/02_control/j_p3_cause/prelaunch_j9/run_records_ed6/d_grid_keys12.json"
D_KEYS_SHA = "a995abff9d73816f58a0e3d67a59f18b3e60fb006fe48d824012b79b57d87981"
VERDICT_CASES = "04_scripts/04_hydraulic/coupled/verdict_cases.py"
R67_SCREEN = "04_scripts/03_control/s8/r67_g1_screen.py"

DECIDED_R13 = "R13"
"""``run_v5._case_of`` always decides R13 = ss_fs4, which gives ``SS_FS4_TWIN``."""
IGNORED_JOB_FIELDS = ("setting", "mask", "t4h_dir")
EXPECTED_ROWS = {"C-J": 388, "C-S": 460, "C-D": 12, "C-G": 171}
SOURCE_TWIN = "twin"
SOURCE_DEFAULT = "default"
SOURCE_NONE = "undetermined"


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def plain_job_key(job: dict) -> str:
    """Job identity without the setting and the runtime-only fields (spec 5.1 C-J pairing)."""
    return json.dumps({k: v for k, v in job.items() if k not in IGNORED_JOB_FIELDS},
                      sort_keys=True)


# --- source facts read with ast ---


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return node.func.id
    return None


def _event_twin_name_and_leg(call: ast.Call, field_names: list[str]) -> tuple[str | None, ...]:
    """Literal ``event`` and ``leg`` of an ``EventTwin(...)`` call (positional or keyword)."""
    wanted = ("event", "leg")
    values: dict[str, object] = {}
    for name, arg in zip(field_names, call.args, strict=False):  # trailing fields may default
        if name in wanted:
            values[name] = ast.literal_eval(arg)
    for keyword in call.keywords:
        if keyword.arg in wanted:
            values[keyword.arg] = ast.literal_eval(keyword.value)
    return values.get("event"), values.get("leg")


def _dataclass_fields(tree: ast.Module, class_name: str) -> list[str]:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return [item.target.id for item in node.body
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)]
    raise ValueError(f"class {class_name} not found")


class CaseDefaults:
    """Per case: twin kind and the default event name / leg, read from verdict_cases.py."""

    def __init__(self, source: str) -> None:
        tree = ast.parse(source)
        self.event_twin_fields = _dataclass_fields(tree, "EventTwin")
        self.kind: dict[str, str] = {}
        self.default: dict[str, tuple[str | None, str | None]] = {}
        decided_r13 = self._decided_r13_twin(tree)
        for node in ast.walk(tree):
            if _call_name(node) != "VerdictCase" or not node.args:
                continue
            if not isinstance(node.args[0], ast.Constant):
                continue  # resolve_case() rebuilds a case from variables; CASES uses literals
            case_id = ast.literal_eval(node.args[0])
            twin_node = node.args[2] if len(node.args) > 2 else None
            for keyword in node.keywords:
                if keyword.arg == "twin":
                    twin_node = keyword.value
            self._add_case(case_id, twin_node)
        if self.kind.get(DECIDED_R13) == "none" and decided_r13 is not None:
            self.kind[DECIDED_R13] = "event"
            self.default[DECIDED_R13] = decided_r13

    def _decided_r13_twin(self, tree: ast.Module) -> tuple[str | None, str | None] | None:
        for node in tree.body:
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == "SS_FS4_TWIN"
                    and _call_name(node.value) == "EventTwin"):
                return _event_twin_name_and_leg(node.value, self.event_twin_fields)
        return None

    def _add_case(self, case_id: str, twin_node: ast.AST | None) -> None:
        name = _call_name(twin_node) if twin_node is not None else None
        if name == "EventTwin":
            self.kind[case_id] = "event"
            self.default[case_id] = _event_twin_name_and_leg(twin_node, self.event_twin_fields)
        elif isinstance(twin_node, ast.Constant) and twin_node.value is None:
            self.kind[case_id] = "none"
        else:
            self.kind[case_id] = "steady"  # SteadyTwin(...) or a helper returning one


def read_r67_names(source: str) -> tuple[set[str], set[str]]:
    """Keys of ``EVENTS`` and members of ``LEGS`` in r67_g1_screen.py (names only)."""
    events: set[str] | None = None
    legs: set[str] | None = None
    for node in ast.parse(source).body:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            continue
        target = node.targets[0].id
        if target == "EVENTS" and isinstance(node.value, ast.Dict):
            events = {ast.literal_eval(key) for key in node.value.keys}
        elif target == "LEGS":
            legs = set(ast.literal_eval(node.value))
    if events is None or legs is None:
        raise ValueError("EVENTS or LEGS not found in r67_g1_screen.py")
    return events, legs


# --- per-row resolution ---


class Resolver:
    """Resolves the event name and leg of a unit job and counts the outcome (no values out)."""

    def __init__(self, defaults: CaseDefaults, events: set[str], legs: set[str]) -> None:
        self.defaults = defaults
        self.events = events
        self.legs = legs

    def is_event_job(self, job: dict, counts: Counter) -> bool:
        kind = self.defaults.kind.get(job.get("case"))
        if kind is None:
            counts["case_unknown_rows"] += 1
            return False
        return kind == "event"

    def resolve(self, job: dict, counts: Counter) -> tuple[str | None, str | None]:
        twin = job.get("twin")
        if twin is not None and not isinstance(twin, dict):
            counts["twin_not_a_dict"] += 1
            twin = None
        twin = twin or {}
        counts[f"twin_key_set:{','.join(sorted(twin)) or '(no twin)'}"] += 1
        unknown_keys = set(twin) - set(self.defaults.event_twin_fields)
        if unknown_keys:
            counts["twin_keys_outside_EventTwin_rows"] += 1
        default_event, default_leg = self.defaults.default.get(job["case"], (None, None))
        event = self._pick(twin.get("event"), default_event, "event", counts)
        leg = self._pick(twin.get("leg"), default_leg, "leg", counts)
        if event is not None and event not in self.events:
            counts["event_not_in_EVENTS"] += 1
        if leg is not None and leg not in self.legs:
            counts["leg_not_in_LEGS"] += 1
        return event, leg

    @staticmethod
    def _pick(twin_value: object, default_value: str | None, label: str,
              counts: Counter) -> str | None:
        if isinstance(twin_value, str) and twin_value:
            counts[f"{label}_from:{SOURCE_TWIN}"] += 1
            return twin_value
        if twin_value is not None:
            counts[f"{label}_twin_value_not_text"] += 1
        if isinstance(default_value, str) and default_value:
            counts[f"{label}_from:{SOURCE_DEFAULT}"] += 1
            return default_value
        counts[f"{label}_from:{SOURCE_NONE}"] += 1
        return None


def compare_with_record(record: dict, event: str | None, leg: str | None, counts: Counter) -> None:
    """Equal / differs / absent counts against a V0 pair record (main line or grid run)."""
    for key, value in (("event", event), ("leg", leg)):
        if key not in record:
            counts[f"pair_record_{key}:absent"] += 1
        elif value is None:
            counts[f"pair_record_{key}:row_undetermined"] += 1
        else:
            counts[f"pair_record_{key}:{'equal' if record[key] == value else 'differs'}"] += 1
    if "event_names" in record:
        # main.jsonl lines carry a dict here whose meaning is not the floor event; only its
        # type is recorded, it is not used as a cross-check
        counts[f"pair_record_event_names_type:{type(record['event_names']).__name__}"] += 1


# --- V0 pair stores (as in 0c) ---


class MainV0:
    """V0 lines of the stored main.jsonl, indexed by plain job key."""

    def __init__(self, data: bytes) -> None:
        self.lines_by_key: dict[str, list[dict]] = {}
        for raw in data.decode("utf-8").splitlines():
            if not raw.strip():
                continue
            line = json.loads(raw)
            job = line.get("job") or {}
            if job.get("setting") == "V0":
                self.lines_by_key.setdefault(plain_job_key(job), []).append(line)

    def find(self, job: dict) -> dict | None:
        matches = self.lines_by_key.get(plain_job_key(job), [])
        if len(matches) != 1 or "error" in matches[0]:
            return None
        return matches[0]


class GridStore:
    """Stored V0 grid files (``results[*].runs[*]``), loaded once each."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: dict[str, dict] = {}

    def find(self, pair: dict) -> dict | None:
        name = pair.get("file")
        if not isinstance(name, str):
            return None
        if name not in self.files:
            self.files[name] = json.loads((self.root / name).read_bytes())
        stored_results = self.files[name].get("results", [])
        results = [r for r in stored_results if r.get("key") == pair.get("key")]
        if len(results) != 1:
            return None
        try:
            run_index = int(pair.get("run_id"))  # spec 5.1: G1 stores run_id as text
        except (TypeError, ValueError):
            return None
        runs = results[0].get("runs", [])
        if not 0 <= run_index < len(runs):
            return None
        run = runs[run_index]
        if run.get("commands_sha256") != pair.get("v0_commands_sha256"):
            return None
        return run


# --- stages ---


def count_event_row(resolver: Resolver, job: dict, record: dict | None, counts: Counter) -> None:
    counts["event_rows"] += 1
    event, leg = resolver.resolve(job, counts)
    if record is None:
        counts["pair_record_not_found"] += 1
        return
    compare_with_record(record, event, leg, counts)


def check_c_j(data: bytes, main_v0: MainV0, resolver: Resolver) -> dict:
    counts: Counter = Counter()
    rows = 0
    for raw in data.decode("utf-8").splitlines():
        if not raw.strip():
            continue
        rows += 1
        job = json.loads(raw)["job"]
        if not resolver.is_event_job(job, counts):
            counts["steady_rows"] += 1
            continue
        count_event_row(resolver, job, main_v0.find(job), counts)
    return {"rows": rows, "unit_job": "j9_main.jsonl line job", "counts": counts}


def check_c_s(data: bytes, main_v0: MainV0, resolver: Resolver) -> dict:
    counts: Counter = Counter()
    lines = json.loads(data)["lines"]
    for line in lines:
        job = line["job"]
        pair_job = line["v0_pair"]["job"]
        is_event = resolver.is_event_job(job, counts)
        if is_event != resolver.is_event_job(pair_job, Counter()):
            counts["unit_and_pair_event_kind_differ"] += 1
        if not is_event:
            counts["steady_rows"] += 1
            continue
        same_twin = job.get("twin") == pair_job.get("twin") and job["case"] == pair_job["case"]
        counts[f"unit_twin_equals_v0_pair_twin:{same_twin}"] += 1
        count_event_row(resolver, job, main_v0.find(pair_job), counts)
    return {"rows": len(lines), "unit_job": "sens_keys_ed7.json line job", "counts": counts}


def check_grid_stage(entries: list[dict], pairs: list[dict | None], store: GridStore,
                     resolver: Resolver) -> Counter:
    counts: Counter = Counter()
    for entry, pair in zip(entries, pairs, strict=True):
        job = entry["job"]
        if not resolver.is_event_job(job, counts):
            counts["steady_rows"] += 1
            continue
        record = store.find(pair) if pair is not None else None
        count_event_row(resolver, job, record, counts)
    return counts


def check_c_d(d_data: bytes, grid192_data: bytes, store: GridStore, resolver: Resolver) -> dict:
    grid_by_job: dict[str, list[dict]] = {}
    for line in json.loads(grid192_data)["lines"]:
        grid_by_job.setdefault(plain_job_key(line["job"]), []).append(line)
    entries = json.loads(d_data)["jobs"]
    pairs: list[dict | None] = []
    for entry in entries:
        found = grid_by_job.get(plain_job_key(entry["job"]), [])
        pairs.append(found[0]["v0_pair"] if len(found) == 1 else None)
    counts = check_grid_stage(entries, pairs, store, resolver)
    counts["grid192_pair_found"] = sum(pair is not None for pair in pairs)
    return {"rows": len(entries), "census_rows": 2 * len(entries),
            "census_rows_note": "12 D keys x {VBN, VBNslow}; both settings share one unit job",
            "unit_job": "d_grid_keys12.json jobs[*].job (key file side)", "counts": counts}


def check_c_g(data: bytes, store: GridStore, resolver: Resolver) -> dict:
    lines = json.loads(data)["lines"]
    counts = check_grid_stage(lines, [line["v0_pair"] for line in lines], store, resolver)
    return {"rows": len(lines), "unit_job": "confirm_g1_grid171.json line job (key file side)",
            "counts": counts}


# --- driver ---


def read_blob(root: Path, rev: str, rel: str) -> bytes:
    completed = subprocess.run(["git", "-C", str(root), "show", f"{rev}:{rel}"],
                               capture_output=True, check=True, timeout=60,
                               stdin=subprocess.DEVNULL)
    return completed.stdout


def stage_is_complete(stage: dict) -> bool:
    counts = stage["counts"]
    event_rows = counts.get("event_rows", 0)
    if event_rows == 0:
        return False  # an empty selection is not a pass
    resolved = (counts.get(f"event_from:{SOURCE_TWIN}", 0)
                + counts.get(f"event_from:{SOURCE_DEFAULT}", 0))
    legs = counts.get(f"leg_from:{SOURCE_TWIN}", 0) + counts.get(f"leg_from:{SOURCE_DEFAULT}", 0)
    return (resolved == event_rows and legs == event_rows
            and counts.get("event_not_in_EVENTS", 0) == 0
            and counts.get("leg_not_in_LEGS", 0) == 0
            and counts.get("twin_keys_outside_EventTwin_rows", 0) == 0
            and counts.get("case_unknown_rows", 0) == 0
            and counts.get("pair_record_not_found", 0) == 0)


def run(root: Path, out: Path) -> int:
    defaults = CaseDefaults((root / VERDICT_CASES).read_text(encoding="utf-8"))
    events, legs = read_r67_names((root / R67_SCREEN).read_text(encoding="utf-8"))
    resolver = Resolver(defaults, events, legs)
    inputs = {
        "main.jsonl": ((root / MAIN_JSONL).read_bytes(), MAIN_SHA),
        "j9_main.jsonl": ((root / J9_MAIN[0]).read_bytes(), J9_MAIN[1]),
        "sens_keys_ed7.json": ((root / SENS_KEYS[0]).read_bytes(), SENS_KEYS[1]),
        "d_grid_keys12.json (git blob)": (read_blob(root, D_KEYS_REV, D_KEYS_PATH), D_KEYS_SHA),
        "confirm_g1_grid171.json": ((root / G1_KEYS[0]).read_bytes(), G1_KEYS[1]),
        "confirm_b_grid192.json": ((root / GRID192_KEYS[0]).read_bytes(), GRID192_KEYS[1]),
    }
    shas = {name: {"sha256": sha256_of(data), "match": sha256_of(data) == expected}
            for name, (data, expected) in inputs.items()}
    main_v0 = MainV0(inputs["main.jsonl"][0])
    store = GridStore(root)
    stages = {
        "C-J": check_c_j(inputs["j9_main.jsonl"][0], main_v0, resolver),
        "C-S": check_c_s(inputs["sens_keys_ed7.json"][0], main_v0, resolver),
        "C-D": check_c_d(inputs["d_grid_keys12.json (git blob)"][0],
                         inputs["confirm_b_grid192.json"][0], store, resolver),
        "C-G": check_c_g(inputs["confirm_g1_grid171.json"][0], store, resolver),
    }
    for name, stage in stages.items():
        stage["rows_match_expected"] = stage["rows"] == EXPECTED_ROWS[name]
        stage["all_event_rows_resolved"] = stage_is_complete(stage)
        stage["counts"] = dict(sorted(stage["counts"].items()))
    source_facts = {
        "event_twin_fields": defaults.event_twin_fields,
        "event_cases": sorted(c for c, kind in defaults.kind.items() if kind == "event"),
        "cases_without_twin_before_decision": sorted(
            c for c, kind in defaults.kind.items() if kind == "none"),
        "events_key_count": len(events),
        "legs_count": len(legs),
        "default_event_in_EVENTS": {c: defaults.default[c][0] in events
                                    for c in sorted(defaults.default)},
        "source_sha256": {rel: sha256_of((root / rel).read_bytes())
                          for rel in (VERDICT_CASES, R67_SCREEN)},
    }
    result = {"inputs_sha256": shas, "source_facts": source_facts, "stages": stages}
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    shas_ok = all(entry["match"] for entry in shas.values())
    rows_ok = all(stage["rows_match_expected"] for stage in stages.values())
    resolved = all(stage["all_event_rows_resolved"] for stage in stages.values())
    status = "ok" if shas_ok and rows_ok and resolved else "findings"
    print(json.dumps({"status": status, "shas_ok": shas_ok, "rows_ok": rows_ok,
                      "all_event_rows_resolved": resolved, "out": str(out)}))
    return 0 if status == "ok" else 1


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"status": "input_error", "error": "usage: <repo root> <out json>"}))
        return 2
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    if out.exists():
        print(json.dumps({"status": "input_error", "error": f"refusing to overwrite {out}"}))
        return 2
    try:
        return run(root, out)
    except (OSError, subprocess.CalledProcessError) as error:
        print(json.dumps({"status": "input_error", "error": str(error)}))
        return 2
    except Exception:  # noqa: BLE001 - any other failure is a tool defect (exit 3)
        traceback.print_exc()
        print(json.dumps({"status": "internal_error"}))
        return 3


if __name__ == "__main__":
    sys.exit(main())
