"""baseline_check.py: SHA256SUMS lists and run identity of a baseline folder."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import pytest
from conftest import git, git_or_skip, sha256_of, tree_hashes

TOOL = "baseline_check.py"
REPO = "저장소 repo"
BASELINE = "06_analysis/기준선 baseline"
REAL_REPO = Path(r"C:\workspace\outrigger_control")
REAL_SUMS = "06_analysis/02_control/j_p3_cause/baseline_221456d/SHA256SUMS"
REAL_SEAL_COMMIT = "f67745f"  # sealed the list; its 18 npz files were left out by *.npz
HEAD_A = "a" * 40
HEAD_B = "b" * 40


def _in_repo(write_file, relative: str, text: str) -> Path:
    return write_file(f"{REPO}/{relative}", text)


def _write_baseline(
    write_file, *, newline: str = "\n", extra: dict[str, str] | None = None
) -> Path:
    files = {"t4h/a.npz": "npz-a", "t4h/b.npz": "npz-b", "cd.jsonl": '{"k": 1}\n'}
    lines = []
    for name, text in files.items():
        path = _in_repo(write_file, f"{BASELINE}/{name}", text)
        lines.append(f"{sha256_of(path)}  {name}")
    for name, text in (extra or {}).items():
        _in_repo(write_file, f"{BASELINE}/{name}", text)
    return _in_repo(write_file, f"{BASELINE}/SHA256SUMS", newline.join(lines) + newline)


def _sums(run_cli, repo: Path, *extra: str):
    return run_cli(
        TOOL,
        "sums",
        "--repo",
        repo,
        f"{BASELINE}/SHA256SUMS",
        *extra,
        "--format",
        "json",
    )


# --- sums ---------------------------------------------------------------------


def test_clean_list_without_git_passes_and_reads_only(run_cli, write_file, tmp_path):
    _write_baseline(write_file)
    before = tree_hashes(tmp_path)

    result = _sums(run_cli, tmp_path / REPO, "--no-git")

    assert result.exit_code == 0, result.stdout
    assert result.summary["entries"] == 3
    assert result.summary["status"] == "ok"
    assert tree_hashes(tmp_path) == before


def test_crlf_list_is_parsed_and_reported(run_cli, write_file, tmp_path):
    _write_baseline(write_file, newline="\r\n")

    result = _sums(run_cli, tmp_path / REPO, "--no-git")

    assert result.summary["categories"] == {"sums_crlf": 1}
    assert result.summary["missing"] == 0  # "\r" was removed before the names were read
    assert result.summary["crlf_lines"] == 3


def test_hash_mismatch_missing_and_line_end_only_difference(
    run_cli, write_file, tmp_path
):
    _write_baseline(write_file)
    folder = tmp_path / REPO / BASELINE
    (folder / "t4h" / "a.npz").write_bytes(b"changed")
    (folder / "t4h" / "b.npz").unlink()
    lf_text = "line\n"
    note = folder / "note.md"
    note.write_bytes(lf_text.replace("\n", "\r\n").encode("utf-8"))
    lf_digest = sha256_of(_in_repo(write_file, "lf_copy.md", lf_text))
    sums = folder / "SHA256SUMS"
    sums.write_bytes(sums.read_bytes() + f"{lf_digest}  note.md\n".encode())

    result = _sums(run_cli, tmp_path / REPO, "--no-git")

    report = result.report()
    statuses = {item["name"]: item["status"] for item in report["lists"][0]["results"]}
    assert statuses == {
        "t4h/a.npz": "mismatch",
        "t4h/b.npz": "missing",
        "cd.jsonl": "ok",
        "note.md": "mismatch",
    }
    messages = [
        item["message"]
        for item in report["findings"]
        if item["category"] == "sums_hash_mismatch"
    ]
    assert any("줄바꿈만 다름" in message for message in messages)
    assert result.summary["categories"]["sums_file_missing"] == 1
    assert result.exit_code == 1


def test_unlisted_files_and_allow_extra(run_cli, write_file, tmp_path):
    _write_baseline(
        write_file, extra={"compare.md": "# 비교\n", "_runners/run.py": "pass\n"}
    )

    plain = _sums(run_cli, tmp_path / REPO, "--no-git")
    allowed = _sums(
        run_cli,
        tmp_path / REPO,
        "--no-git",
        "--allow-extra",
        "*.md",
        "--allow-extra",
        "_runners/*",
    )

    assert sorted(plain.report()["lists"][0]["unlisted"]) == [
        "_runners/run.py",
        "compare.md",
    ]
    assert plain.summary["categories"]["sums_unlisted"] == 2
    assert allowed.summary["unlisted"] == 0
    assert allowed.exit_code == 0


def test_duplicate_malformed_bsd_and_empty(run_cli, write_file, tmp_path):
    folder_relative = f"{BASELINE}/other"
    data = _in_repo(write_file, f"{folder_relative}/x.json", "{}")
    digest = sha256_of(data)
    text = f"{digest}  x.json\n{digest} *x.json\nnot a hash line\nSHA256 (x.json) = {digest}\n"
    _in_repo(write_file, f"{folder_relative}/SHA256SUMS", text)
    _in_repo(write_file, f"{BASELINE}/empty/SHA256SUMS", "# nothing\n")

    result = run_cli(
        TOOL,
        "sums",
        "--repo",
        tmp_path / REPO,
        f"{folder_relative}/SHA256SUMS",
        f"{BASELINE}/empty/SHA256SUMS",
        "--no-git",
        "--format",
        "json",
    )

    categories = result.summary["categories"]
    assert categories["sums_duplicate"] == 2  # the star and the BSD line repeat x.json
    assert categories["sums_malformed_line"] == 1
    assert categories["sums_empty"] == 1
    assert result.report()["lists"][0]["ok"] == 3


def test_ignored_untracked_entries_and_rev(run_cli, write_file, tmp_path):
    git_or_skip()
    _write_baseline(write_file)
    _in_repo(write_file, ".gitignore", "*.npz\n")
    repo = tmp_path / REPO
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "seal")
    git(repo, "add", "-f", f"{BASELINE}/t4h/a.npz", f"{BASELINE}/t4h/b.npz")
    git(repo, "commit", "-q", "-m", "force-add")

    now = _sums(run_cli, repo)
    at_seal = _sums(run_cli, repo, "--rev", "HEAD~1")

    assert now.summary["categories"] == {"cited_ignored_tracked": 2}
    assert now.exit_code == 0
    assert at_seal.summary["cited_ignored"] == 2
    assert at_seal.summary["categories"] == {"cited_ignored": 2}
    assert at_seal.exit_code == 1


def test_untracked_entry_without_ignore_rule(run_cli, write_file, tmp_path):
    git_or_skip()
    _write_baseline(write_file)
    repo = tmp_path / REPO
    git(repo, "init", "-q")
    git(repo, "add", f"{BASELINE}/SHA256SUMS", f"{BASELINE}/cd.jsonl")
    git(repo, "commit", "-q", "-m", "partial")

    result = _sums(run_cli, repo)

    assert result.summary["categories"] == {"cited_untracked": 2}


def test_sums_input_errors(run_cli, write_file, tmp_path):
    _write_baseline(write_file)
    repo = tmp_path / REPO

    assert run_cli(TOOL, "sums", "--repo", repo, "nothing/*/SHA256SUMS").exit_code == 2
    assert (
        run_cli(
            TOOL,
            "sums",
            "--repo",
            repo,
            f"{BASELINE}/SHA256SUMS",
            "--rev",
            "HEAD",
            "--no-git",
        ).exit_code
        == 2
    )
    out_inside = repo / BASELINE / "r.md"
    assert (
        run_cli(
            TOOL,
            "sums",
            "--repo",
            repo,
            f"{BASELINE}/SHA256SUMS",
            "--no-git",
            "--out",
            out_inside,
        ).exit_code
        == 2
    )


def _write_repo_relative_list(write_file) -> None:
    """A list whose names are relative to the repository root, not its own folder."""
    _write_baseline(write_file)
    folder = Path(BASELINE)
    sums = write_file(f"{REPO}/{BASELINE}/SHA256SUMS", "")
    lines = []
    for name in ("t4h/a.npz", "t4h/b.npz", "cd.jsonl"):
        digest = sha256_of(sums.parent / name)
        lines.append(f"{digest}  {(folder / name).as_posix()}")
    sums.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def test_default_base_is_sums_dir_and_hint_names_repo_root(
    run_cli, write_file, tmp_path
):
    _write_repo_relative_list(write_file)
    repo = tmp_path / REPO
    before = tree_hashes(tmp_path)

    default = _sums(run_cli, repo, "--no-git")
    at_root = _sums(run_cli, repo, "--no-git", "--base", "repo-root")

    assert default.summary["base"] == "sums-dir"
    assert default.summary["missing"] == 3 and default.exit_code == 1
    hint = default.report()["lists"][0]["base_hint"]
    assert hint["base"] == "repo-root" and hint["present"] == 3 and hint["hash_ok"] == 3
    assert hint["folder"] == str(repo.resolve())
    hint_findings = [
        item
        for item in default.report()["findings"]
        if item["category"] == "sums_base_hint"
    ]
    assert len(hint_findings) == 1 and hint_findings[0]["severity"] == "info"
    assert "--base repo-root" in hint_findings[0]["message"]
    assert at_root.exit_code == 0, at_root.stdout
    assert at_root.summary["base"] == "repo-root" and at_root.summary["missing"] == 0
    assert at_root.report()["lists"][0]["base_hint"] is None
    assert tree_hashes(tmp_path) == before


def test_repo_root_list_reports_unlisted_neighbours_as_info(run_cli, write_file, tmp_path):
    """Re-audit N-6 (2026-11-21): a repo-root list does not name its own folder's files."""
    _write_repo_relative_list(write_file)
    _in_repo(write_file, f"{BASELINE}/run_steps/step1.ps1", "# runner\n")
    repo = tmp_path / REPO

    at_root = _sums(run_cli, repo, "--no-git", "--base", "repo-root")
    allowed = _sums(
        run_cli, repo, "--no-git", "--base", "repo-root", "--allow-extra", "run_steps/*"
    )

    assert at_root.exit_code == 0, at_root.stdout
    assert at_root.report()["lists"][0]["unlisted"] == ["run_steps/step1.ps1"]
    unlisted = [
        item
        for item in at_root.report()["findings"]
        if item["category"] == "sums_unlisted"
    ]
    assert [item["severity"] for item in unlisted] == ["info"]
    assert "repo-root" in unlisted[0]["message"]
    assert allowed.summary["unlisted"] == 0


def test_repo_root_base_on_a_folder_relative_list_hints_sums_dir(
    run_cli, write_file, tmp_path
):
    _write_baseline(write_file)

    result = _sums(run_cli, tmp_path / REPO, "--no-git", "--base", "repo-root")

    assert result.summary["missing"] == 3
    hint = result.report()["lists"][0]["base_hint"]
    assert hint["base"] == "sums-dir" and hint["present"] == 3


def test_hint_says_files_are_really_missing(run_cli, write_file, tmp_path):
    _write_baseline(write_file)
    folder = tmp_path / REPO / BASELINE
    for name in ("t4h/a.npz", "t4h/b.npz", "cd.jsonl"):
        (folder / name).unlink()

    result = _sums(run_cli, tmp_path / REPO, "--no-git")
    partly = _write_baseline(write_file)  # restore all three, then drop one
    (partly.parent / "cd.jsonl").unlink()
    one_missing = _sums(run_cli, tmp_path / REPO, "--no-git")

    hint = result.report()["lists"][0]["base_hint"]
    assert hint["present"] == 0
    message = next(
        item["message"]
        for item in result.report()["findings"]
        if item["category"] == "sums_base_hint"
    )
    assert "기준 문제가 아니라" in message
    # Only an all-missing list gets a hint.
    assert one_missing.report()["lists"][0]["base_hint"] is None
    assert "sums_base_hint" not in one_missing.summary["categories"]


def test_no_hint_without_a_repo_root(run_cli, write_file, tmp_path):
    _write_repo_relative_list(write_file)
    list_path = tmp_path / REPO / BASELINE / "SHA256SUMS"

    result = run_cli(TOOL, "sums", list_path, "--no-git", "--format", "json")
    refused = run_cli(TOOL, "sums", list_path, "--no-git", "--base", "repo-root")

    assert result.report()["lists"][0]["base_hint"] is None  # no --repo, no git
    assert refused.exit_code == 2
    assert "--base repo-root needs --repo" in refused.summary["error"]


def test_repo_root_from_git_work_tree(run_cli, write_file, tmp_path):
    git_or_skip()
    _write_repo_relative_list(write_file)
    repo = tmp_path / REPO
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "seal")
    list_path = repo / BASELINE / "SHA256SUMS"

    result = run_cli(TOOL, "sums", list_path, "--base", "repo-root", "--format", "json")

    assert result.exit_code == 0, result.stdout
    assert result.report()["lists"][0]["entry_base"] == str(repo.resolve())


def test_real_baseline_at_seal_commit(run_cli):
    """Read-only smoke on the project baseline: f67745f sealed it without its npz."""
    if not (REAL_REPO / REAL_SUMS).is_file():
        pytest.skip("project baseline not available")
    git_or_skip()
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(REAL_REPO),
            "cat-file",
            "-e",
            f"{REAL_SEAL_COMMIT}^{{commit}}",
        ],
        capture_output=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip("seal commit not in this clone")

    result = run_cli(
        TOOL, "sums", "--repo", REAL_REPO, REAL_SUMS, "--rev", REAL_SEAL_COMMIT
    )

    assert result.summary["cited_ignored"] == 18
    assert result.summary["mismatch"] == 0
    assert result.summary["crlf_lines"] > 0


# --- identity -----------------------------------------------------------------


def _identity(
    head: str | None,
    is_clean: bool | None,
    porcelain: str = "",
    time: str = "2026-11-16 23:10:45 +0900",
) -> dict:
    block: dict[str, object] = {"status_porcelain": porcelain}
    if head is not None:
        block["head"] = head
    if is_clean is not None:
        block["is_clean"] = is_clean
    return {
        "start": [{"time": time, "git": block}],
        "end": [{"time": time, "git": block}],
    }


def _write_identity(write_file, name: str, document: dict) -> Path:
    return _in_repo(
        write_file, f"{BASELINE}/{name}", json.dumps(document, ensure_ascii=False)
    )


def _identity_run(run_cli, tmp_path, *extra: str):
    return run_cli(
        TOOL,
        "identity",
        "--repo",
        tmp_path / REPO,
        BASELINE,
        *extra,
        "--no-git",
        "--format",
        "json",
    )


def test_identity_clean_and_matching(run_cli, write_file, tmp_path):
    _write_identity(write_file, "cd.identity.json", _identity(HEAD_A, True))
    _write_identity(write_file, "j9.identity.json", _identity(HEAD_A, True))

    result = _identity_run(run_cli, tmp_path, "--expect-commit", HEAD_A[:7])

    assert result.exit_code == 0, result.stdout
    assert result.summary["git_blocks"] == 4
    assert result.report()["blocks"][0]["json_path"] == "$.start[0].git"


def test_identity_head_mismatch_dirty_and_unknown(run_cli, write_file, tmp_path):
    _write_identity(write_file, "a.identity.json", _identity(HEAD_B, True))
    _write_identity(
        write_file,
        "b.identity.json",
        _identity(HEAD_A, False, " M 03_src/c2.py\n?? x.py"),
    )
    _write_identity(write_file, "c.identity.json", _identity(HEAD_A, None))
    _write_identity(write_file, "d.identity.json", _identity(HEAD_A, True, " M y.py"))

    result = _identity_run(run_cli, tmp_path, "--expect-commit", HEAD_A)

    categories = result.summary["categories"]
    assert categories["baseline_head_mismatch"] == 2
    assert categories["baseline_dirty"] == 2
    assert categories["baseline_clean_unknown"] == 2
    assert categories["baseline_clean_inconsistent"] == 2
    dirty = next(
        item
        for item in result.report()["findings"]
        if item["category"] == "baseline_dirty"
    )
    assert "03_src/c2.py" in dirty["message"]
    assert result.exit_code == 1


def test_identity_block_without_head(run_cli, write_file, tmp_path):
    _write_identity(write_file, "a.identity.json", _identity(None, True))

    result = _identity_run(run_cli, tmp_path, "--expect-commit", HEAD_A)

    assert result.summary["categories"] == {"baseline_head_missing": 2}


@pytest.mark.parametrize("head", ["", "   ", HEAD_A[:12], "z" * 40])
def test_identity_empty_or_short_head_is_refused(run_cli, write_file, tmp_path, head):
    """2026-11-21 (436.9 addendum 4a-5 4): ``d8x_record.git_state`` writes head ``""`` and
    ``is_clean: true`` when git fails; ``""`` used to match every ``--expect-commit``."""
    _write_identity(write_file, "a.identity.json", _identity(head, True))

    result = _identity_run(run_cli, tmp_path, "--expect-commit", HEAD_A)

    assert result.summary["categories"] == {"baseline_head_invalid": 2}
    assert result.exit_code == 1
    assert _identity_run(run_cli, tmp_path).exit_code == 1  # without --expect-commit too


def test_identity_git_failure_mark_is_refused(run_cli, write_file, tmp_path):
    document = _identity(HEAD_A, True)
    document["start"][0]["git"]["error"] = "git rc 128 / 128"  # start and end share it
    _write_identity(write_file, "a.identity.json", document)

    result = _identity_run(run_cli, tmp_path, "--expect-commit", HEAD_A)

    assert result.summary["categories"] == {"identity_git_error": 2}
    assert result.exit_code == 1


def test_bom_list_is_info(run_cli, write_file, tmp_path):
    sums = _write_baseline(write_file)
    sums.write_bytes(b"\xef\xbb\xbf" + sums.read_bytes())

    result = _sums(run_cli, tmp_path / REPO, "--no-git")

    assert result.summary["categories"] == {"sums_bom": 1}
    assert result.summary["missing"] == 0
    assert result.exit_code == 0


def test_identity_without_expectation_needs_one_head(run_cli, write_file, tmp_path):
    _write_identity(write_file, "a.identity.json", _identity(HEAD_A, True))
    _write_identity(write_file, "b.identity.json", _identity(HEAD_B, True))
    _write_identity(write_file, "c.identity.json", {"note": "no git block"})

    result = _identity_run(run_cli, tmp_path)

    assert result.summary["categories"]["baseline_head_mixed"] == 1
    assert result.summary["categories"]["identity_git_absent"] == 1


def test_identity_input_errors(run_cli, write_file, tmp_path):
    _in_repo(write_file, f"{BASELINE}/readme.md", "# 없음\n")

    assert _identity_run(run_cli, tmp_path).exit_code == 2  # no identity files
    _write_identity(write_file, "a.identity.json", _identity(HEAD_A, True))
    assert _identity_run(run_cli, tmp_path, "--expect-commit", "xyz").exit_code == 2
    _in_repo(write_file, f"{BASELINE}/broken.identity.json", "{not json")
    assert _identity_run(run_cli, tmp_path).exit_code == 2


def test_identity_mtime_after_commit(run_cli, write_file, tmp_path):
    git_or_skip()
    repo = tmp_path / REPO
    edited = _in_repo(write_file, "03_src/c2.py", "x = 1\n")
    later = _in_repo(write_file, "03_src/later.py", "y = 1\n")
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "baseline commit")
    commit_line = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%H %ct"],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    ).stdout.split()
    commit, commit_s = commit_line[0], int(commit_line[1])
    edited.write_bytes(b"x = 2\n")
    os.utime(edited, (commit_s + 60, commit_s + 60))  # after the commit, before the run
    os.utime(later, (commit_s + 600, commit_s + 600))  # after the run started
    run_time = _local_text(commit_s + 120)
    _write_identity(
        write_file, "cd.identity.json", _identity(commit, True, time=run_time)
    )

    result = run_cli(
        TOOL,
        "identity",
        "--repo",
        repo,
        BASELINE,
        "--expect-commit",
        commit,
        "--mtime",
        "--format",
        "json",
    )

    findings = {item["category"]: item for item in result.report()["findings"]}
    assert set(findings) == {"mtime_after_commit_before_run", "mtime_after_commit"}
    assert "03_src/c2.py" in findings["mtime_after_commit_before_run"]["message"]
    assert (
        "지금 내용도 커밋과 다르다"
        in findings["mtime_after_commit_before_run"]["message"]
    )
    assert "03_src/later.py" in findings["mtime_after_commit"]["message"]


def _local_text(epoch_s: int) -> str:
    moment = datetime.fromtimestamp(epoch_s).astimezone()
    return moment.strftime("%Y-%m-%d %H:%M:%S %z")
