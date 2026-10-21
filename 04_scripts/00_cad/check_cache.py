"""Write and check the CAD cache manifest ``01_cad/cache_manifest.json``.

The manifest records, for every cache folder under ``01_cad/``:

* the STEP source (size, modification time, sha256),
* the generator scripts (path, sha256, git blob hash, last git commit if any),
* the package versions at manifest time (pythonocc-core, OCCT, numpy, ...),
* every cache file (relative path, size, sha256, generator).

``--check`` (default) compares the current state with the manifest:

* STEP size or modification time changed -> the caches may be stale (error);
  with ``--full`` the STEP sha256 is recomputed and decides.
* cache file missing -> error; size (and with ``--full`` sha256) changed ->
  error; unregistered new file -> warning.
* generator script changed since the manifest -> warning.

``brep_cache.py`` calls :func:`warn_if_stale` (stat only) when it first loads.

Usage:
    python -I 04_scripts/00_cad/check_cache.py [--check] [--full] [--strict]
    python -I 04_scripts/00_cad/check_cache.py --write [--cache 06_brep ...]
"""

import argparse
import fnmatch
import hashlib
import json
import platform
import subprocess
import sys
import time
import warnings
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cad_common import CACHE_MANIFEST_JSON, CAD_DIR, PROJECT_ROOT, STEP_PATH

SCRIPT_DIR = Path(__file__).resolve().parent
MANIFEST_SCHEMA = 1
IGNORED_PATTERNS = ("*.log",)
WARN_LIMIT = 5

# Cache folder -> description and (file glob, generator script) rules; the
# first matching rule names the generator of a file (paths relative to the
# folder, POSIX separators).
CACHE_RULES: dict[str, dict] = {
    "00_step": {
        "description": "STEP header and product list (text scan of the STEP file)",
        "rules": [("*", "step_text_index.py")],
    },
    "01_parts": {
        "description": "Part table, classification, summary, mass audit, layout figures",
        "rules": [
            ("parts.csv", "extract_parts.py"),
            ("parts_classified.csv", "analyze_parts.py"),
            ("cad_summary.json", "analyze_parts.py"),
            ("layout_views.png", "analyze_parts.py"),
            ("layout_views_rendered.png", "render_layout_views.py"),
            ("imu_c1_*.png", "render_imu_c1.py"),
            ("*", "analyze_origin_mass_imu.py"),
        ],
    },
    "02_legs": {
        "description": "Jack cylinder B-rep (world placed), face table, extension figures, "
        "rod lateral check",
        "rules": [
            ("legs/*.brep", "inspect_legs.py"),
            ("leg_faces.csv", "inspect_legs.py"),
            ("leg_rod_lateral_check.*", "leg_rod_lateral_check.py"),
            ("*", "render_leg_extension.py"),
        ],
    },
    "03_auger": {
        "description": "Auger three-level values, part table and figures",
        "rules": [
            ("auger_levels/auger_descent.gif", "render_auger_descent.py"),
            ("*", "analyze_auger_levels.py"),
        ],
    },
    "04_mast": {
        "description": "Mast B-rep (world placed), faces, hinge review (reference only)",
        "rules": [
            ("mast/*", "inspect_mast.py"),
            ("mast_faces.csv", "inspect_mast.py"),
            ("*", "analyze_mast.py"),
        ],
    },
    "05_meshes": {
        "description": "Render mesh archive of all parts (world placed), mast sweep files",
        "rules": [
            ("render_mesh.npz", "analyze_mast.py"),
            ("contact_sweep_records.csv", "analyze_mast.py"),
            ("*", "export_meshes.py"),
        ],
    },
    "06_brep": {
        "description": "Prototype B-rep cache + instance placements of all parts",
        "rules": [
            ("verification.json", "verify_brep_cache.py"),
            ("format_conversion.json", "convert_brep_cache.py"),
            ("derived/crawler/parts/*", "derive_crawler_parts.py"),
            ("derived/crawler/crawler_contact_part*", "derive_crawler_parts.py"),
            ("derived/crawler/*", "derive_crawler_cache.py"),
            ("*", "build_brep_cache.py"),
        ],
    },
    "07_faces": {
        "description": "Face index of all parts: prototype faces + instance faces (world/body)",
        "rules": [("*", "build_face_index.py")],
    },
}


@dataclass
class Problem:
    """One finding of :func:`check`."""

    level: str  # "error" or "warning"
    cache: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level}] {self.cache}: {self.message}"


class StaleCacheError(RuntimeError):
    """Raised by :func:`check` with ``strict=True`` when errors are found."""


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _iso(timestamp: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(timestamp))


def _git(*arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = result.stdout.strip()
    return output if result.returncode == 0 and output else None


def _distribution_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _conda_package_version(prefix: str) -> str | None:
    """Version of a conda package from ``conda-meta`` (pythonocc/occt have no dist-info)."""
    meta_dir = Path(sys.prefix) / "conda-meta"
    for path in sorted(meta_dir.glob(f"{prefix}-[0-9]*.json")):
        return json.loads(path.read_text(encoding="utf-8"))["version"]
    return None


def environment_versions() -> dict:
    """Interpreter and package versions relevant to the CAD caches."""
    try:
        import OCC

        pythonocc = OCC.VERSION
    except ImportError:
        pythonocc = None
    return {
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "pythonocc_core": pythonocc,
        "occt": _conda_package_version("occt"),
        "numpy": _distribution_version("numpy"),
        "trimesh": _distribution_version("trimesh"),
        "pandas": _distribution_version("pandas"),
    }


def _generator_record(script_name: str) -> dict:
    path = SCRIPT_DIR / script_name
    relative = path.relative_to(PROJECT_ROOT).as_posix()
    if not path.exists():
        return {"script": relative, "exists": False}
    return {
        "script": relative,
        "exists": True,
        "sha256": sha256_file(path),
        "git_blob": _git("hash-object", relative),
        "git_last_commit": _git("log", "-1", "--format=%H", "--", relative),
        "git_tracked": _git("ls-files", "--error-unmatch", relative) is not None,
    }


def _generator_for(relative: str, rules: list[tuple[str, str]]) -> str:
    for pattern, script in rules:
        if fnmatch.fnmatch(relative, pattern):
            return script
    return ""


def _cache_files(folder: Path) -> list[Path]:
    return sorted(
        path
        for path in folder.rglob("*")
        if path.is_file() and not any(fnmatch.fnmatch(path.name, p) for p in IGNORED_PATTERNS)
    )


def _git_ignored(paths_from_root: list[str]) -> set[str]:
    """Subset of the given project-relative paths that git ignores (one git call)."""
    if not paths_from_root:
        return set()
    try:
        # NUL-separated bytes: text mode on Windows would turn "\n" into "\r\n",
        # which git then treats as part of the path.
        result = subprocess.run(
            ["git", "check-ignore", "-z", "--stdin"],
            cwd=PROJECT_ROOT,
            input="\0".join(paths_from_root).encode("utf-8") + b"\0",
            capture_output=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    return {item for item in result.stdout.decode("utf-8").split("\0") if item}


def _step_record(with_hash: bool = True) -> dict:
    stat = STEP_PATH.stat()
    record = {
        "path": STEP_PATH.name,
        "size_bytes": stat.st_size,
        "mtime": _iso(stat.st_mtime),
        "mtime_ns": stat.st_mtime_ns,
    }
    if with_hash:
        record["sha256"] = sha256_file(STEP_PATH)
    return record


# --------------------------------------------------------------------------
# Manifest writing
# --------------------------------------------------------------------------
def _cache_entry(name: str) -> dict:
    spec = CACHE_RULES[name]
    folder = CAD_DIR / name
    files = []
    for path in _cache_files(folder):
        relative = path.relative_to(folder).as_posix()
        files.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "generator": _generator_for(relative, spec["rules"]),
            }
        )
    scripts = sorted({script for _, script in spec["rules"]})
    newest = max((path.stat().st_mtime for path in _cache_files(folder)), default=None)
    ignored = _git_ignored([f"01_cad/{name}/{item['path']}" for item in files])
    for item in files:
        item["git_ignored"] = f"01_cad/{name}/{item['path']}" in ignored
    return {
        "description": spec["description"],
        "folder": f"01_cad/{name}",
        "derived_from_step": True,
        "newest_file_mtime": _iso(newest) if newest else None,
        "generators": [_generator_record(script) for script in scripts],
        "file_count": len(files),
        "total_bytes": sum(item["bytes"] for item in files),
        "git_ignored_file_count": len(ignored),
        "files": files,
    }


def write_manifest(names: list[str] | None = None) -> dict:
    """Create or update the manifest; ``names`` limits which cache entries refresh.

    The STEP record and environment are always refreshed.
    """
    manifest = (
        json.loads(CACHE_MANIFEST_JSON.read_text(encoding="utf-8"))
        if CACHE_MANIFEST_JSON.exists()
        else {"caches": {}}
    )
    selected = names or [name for name in CACHE_RULES if (CAD_DIR / name).is_dir()]
    caches = manifest.get("caches", {})
    for name in selected:
        if not (CAD_DIR / name).is_dir():
            raise FileNotFoundError(CAD_DIR / name)
        caches[name] = _cache_entry(name)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "updated_at": _iso(time.time()),
        "updated_by": _generator_record(Path(__file__).name),
        "environment": environment_versions(),
        "step": _step_record(with_hash=True),
        "caches": dict(sorted(caches.items())),
    }
    CACHE_MANIFEST_JSON.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return manifest


# --------------------------------------------------------------------------
# Checking
# --------------------------------------------------------------------------
def _check_step(step: dict, full_hash: bool) -> list[Problem]:
    if not STEP_PATH.exists():
        return [Problem("error", "step", f"STEP file missing: {STEP_PATH}")]
    current = _step_record(with_hash=False)
    if full_hash:
        if sha256_file(STEP_PATH) != step.get("sha256"):
            return [Problem("error", "step", "STEP sha256 differs from the manifest")]
        return []
    if current["size_bytes"] != step.get("size_bytes"):
        return [Problem("error", "step", "STEP size differs from the manifest")]
    if current["mtime_ns"] != step.get("mtime_ns"):
        return [
            Problem(
                "error",
                "step",
                "STEP modification time differs from the manifest "
                "(run check_cache.py --full to compare sha256)",
            )
        ]
    return []


def _check_cache(name: str, entry: dict, full_hash: bool) -> list[Problem]:
    problems: list[Problem] = []
    folder = CAD_DIR / name
    registered = {item["path"]: item for item in entry["files"]}
    for relative, item in registered.items():
        path = folder / relative
        if not path.exists():
            problems.append(Problem("error", name, f"missing file {relative}"))
        elif path.stat().st_size != item["bytes"]:
            problems.append(Problem("error", name, f"size changed: {relative}"))
        elif full_hash and sha256_file(path) != item["sha256"]:
            problems.append(Problem("error", name, f"sha256 changed: {relative}"))
    if folder.is_dir():
        extra = [
            path.relative_to(folder).as_posix()
            for path in _cache_files(folder)
            if path.relative_to(folder).as_posix() not in registered
        ]
        if extra:
            problems.append(
                Problem("warning", name, f"{len(extra)} unregistered file(s), e.g. {extra[0]}")
            )
    for generator in entry.get("generators", []):
        path = PROJECT_ROOT / generator["script"]
        if not path.exists():
            problems.append(Problem("warning", name, f"generator missing: {generator['script']}"))
        elif generator.get("sha256") and sha256_file(path) != generator["sha256"]:
            problems.append(
                Problem("warning", name, f"generator changed since manifest: {generator['script']}")
            )
    return problems


def check(
    names: list[str] | None = None, full_hash: bool = False, strict: bool = False
) -> list[Problem]:
    """Compare the STEP file and cache folders with the manifest.

    Args:
        names: Cache folders to check (default: all in the manifest).
        full_hash: Recompute sha256 of the STEP file and of every cache file
            (slower: about 1 s per 500 MB) instead of size/mtime only.
        strict: Raise :class:`StaleCacheError` if any error is found.

    Returns:
        The list of problems (empty if the caches match the manifest).
    """
    if not CACHE_MANIFEST_JSON.exists():
        problems = [Problem("error", "manifest", f"missing {CACHE_MANIFEST_JSON}")]
    else:
        manifest = json.loads(CACHE_MANIFEST_JSON.read_text(encoding="utf-8"))
        problems = _check_step(manifest["step"], full_hash)
        caches = manifest["caches"]
        for name in names or list(caches):
            if name not in caches:
                problems.append(Problem("error", name, "not registered in the manifest"))
                continue
            problems.extend(_check_cache(name, caches[name], full_hash))
    if strict and any(problem.level == "error" for problem in problems):
        raise StaleCacheError("\n".join(str(problem) for problem in problems))
    return problems


def warn_if_stale(names: list[str]) -> None:
    """Quick stat-only check; emits one ``UserWarning`` listing up to 5 problems."""
    problems = check(names, full_hash=False)
    if not problems:
        return
    shown = "\n".join(str(problem) for problem in problems[:WARN_LIMIT])
    more = len(problems) - WARN_LIMIT
    suffix = f"\n... and {more} more (run check_cache.py)" if more > 0 else ""
    warnings.warn(f"CAD cache differs from the manifest:\n{shown}{suffix}", stacklevel=3)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="compare with manifest (default)")
    action.add_argument("--write", action="store_true", help="create/update the manifest")
    parser.add_argument("--cache", nargs="*", choices=sorted(CACHE_RULES), help="cache folders")
    parser.add_argument("--full", action="store_true", help="recompute all sha256")
    parser.add_argument("--strict", action="store_true", help="exit 1 on any error")
    arguments = parser.parse_args()

    started_s = time.perf_counter()
    if arguments.write:
        manifest = write_manifest(arguments.cache)
        for name, entry in manifest["caches"].items():
            print(f"{name}: {entry['file_count']} files, {entry['total_bytes'] / 1e6:.1f} MB")
        print(f"wrote {CACHE_MANIFEST_JSON} in {time.perf_counter() - started_s:.1f} s")
        return
    problems = check(arguments.cache, full_hash=arguments.full)
    for problem in problems:
        print(problem)
    errors = sum(problem.level == "error" for problem in problems)
    print(
        f"{errors} error(s), {len(problems) - errors} warning(s) "
        f"in {time.perf_counter() - started_s:.1f} s"
    )
    if arguments.strict and errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
