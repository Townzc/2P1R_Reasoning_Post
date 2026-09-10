"""Preview or remove only the independently preserved E013 checkpoint duplicate.

The caller must verify published source, the original base, Linux/idle GPU and
the current process ledger before executing this helper. No model is loaded.
The caller also owns the unchanged 12 GiB post-cleanup launch gate.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys


RUN_ID = "gsm8k_overfit_e013_r1"
CANDIDATE = Path("runs") / RUN_ID / "checkpoint_final"
MANIFEST = CANDIDATE.parent / "checkpoint_manifest.json"
PRESERVATION = Path("reports/real_math_e015_local_preservation.json")
EXPECTED_MANIFEST_SHA256 = "b0afd4cf81a8c41a2268d5d797a3f832c8b530206f1fa3a6539a43ddf91fab6a"
EXPECTED_LEDGER_SHA256 = "8813caaa4a3661900f874033fac68b802b3e856bc9c449f28f1fff3983b4aae9"
PROC_ROOT = Path("/proc")
EXPECTED_FILES = frozenset({
    "added_tokens.json", "chat_template.jinja", "config.json",
    "generation_config.json", "merges.txt", "model-00001-of-00002.safetensors",
    "model-00002-of-00002.safetensors", "model.safetensors.index.json",
    "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json", "vocab.json",
})


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_nlink, info.st_mode)


def _checked_components(path, root, *, final_may_be_absent=False):
    """Reject symlinks in every repository-relative path component."""
    relative = path.relative_to(root)
    current = root
    for index, name in enumerate(relative.parts):
        current = current / name
        try:
            info = current.lstat()
        except FileNotFoundError:
            if final_may_be_absent and index == len(relative.parts) - 1:
                return False
            raise ValueError("Required preservation path is missing") from None
        _require(not stat.S_ISLNK(info.st_mode), "Symlink in preservation path")
        if index < len(relative.parts) - 1:
            _require(stat.S_ISDIR(info.st_mode), "Non-directory preservation ancestor")
    return True


def _overlaps(left, right):
    return left == right or left in right.parents or right in left.parents


def _read_regular(path):
    _require(stat.S_ISREG(path.lstat().st_mode), "Preservation record is not a regular file")
    with path.open("rb") as handle:
        return handle.read()


def _evidence(root, ledger):
    manifest_path, receipt_path = root / MANIFEST, root / PRESERVATION
    _checked_components(manifest_path, root)
    _checked_components(receipt_path, root)
    raw_manifest = _read_regular(manifest_path)
    _require(_digest(raw_manifest) == EXPECTED_MANIFEST_SHA256, "Published E013 manifest differs")
    manifest = json.loads(raw_manifest)
    files = manifest["files"]
    _require(set(files) == EXPECTED_FILES, "Checkpoint manifest inventory differs")
    for name, item in files.items():
        _require(set(item) == {"bytes", "sha256"} and type(item["bytes"]) is int
                 and item["bytes"] > 0 and isinstance(item["sha256"], str)
                 and len(item["sha256"]) == 64
                 and all(c in "0123456789abcdef" for c in item["sha256"]),
                 "Malformed checkpoint identity")
    receipt = json.loads(_read_regular(receipt_path))
    checkpoint = receipt["checkpoint"]
    _require(checkpoint["run_id"] == RUN_ID
             and checkpoint["manifest_path"] == MANIFEST.as_posix()
             and checkpoint["manifest_sha256"] == EXPECTED_MANIFEST_SHA256
             and checkpoint["file_count"] == len(EXPECTED_FILES)
             and checkpoint["total_bytes"] == sum(x["bytes"] for x in files.values()),
             "Local preservation receipt does not match checkpoint")
    for field in ("exact_inventory_verified", "all_files_regular_not_symlinks",
                  "all_checkpoint_files_independently_backed_up_and_verified"):
        _require(checkpoint.get(field) is True, "Independent local preservation is unproven")
    records = checkpoint["files"]
    _require(len(records) == len(EXPECTED_FILES)
             and all(set(item) == {"file", "bytes", "sha256"} for item in records),
             "Local preservation file inventory differs")
    preserved = {item["file"]: {"bytes": item["bytes"], "sha256": item["sha256"]}
                 for item in records}
    _require(preserved == files, "Local preservation file identities differ")
    raw_ledger = _read_regular(ledger)
    digest = _digest(raw_ledger)
    _require(digest == EXPECTED_LEDGER_SHA256 == receipt["ledger"]["sha256"],
             "Current ledger differs from independent preservation receipt")
    return files, digest, _digest(_read_regular(receipt_path))


def _check_open_fds(candidate, identities):
    """Reject known open descriptors; deny cleanup if Linux inspection is denied.

    This is an FD check, not a claim about mappings or all model activity.
    Process/GPU idleness is independently required by the launcher.
    """
    if sys.platform != "linux":
        return "not_linux_inspection_unavailable"
    proc = PROC_ROOT
    _require(proc.is_dir(), "Linux process descriptor inspection is unavailable")
    inodes = {(identity[0], identity[1]) for identity in identities.values()}
    info = candidate.stat()
    inodes.add((info.st_dev, info.st_ino))
    try:
        for process in proc.iterdir():
            if not process.name.isdigit():
                continue
            try:
                descriptors = list((process / "fd").iterdir())
            except FileNotFoundError:
                continue  # A process may exit during the inspection.
            for descriptor in descriptors:
                try:
                    info = descriptor.stat()
                except FileNotFoundError:
                    continue  # A descriptor may close during the inspection.
                _require((info.st_dev, info.st_ino) not in inodes,
                         "Checkpoint file/directory has an open process descriptor")
    except PermissionError as error:
        raise ValueError("Cannot establish descriptor state: permission denied") from error
    return "no_matching_open_fds_observed"


def reclaim_duplicate(snapshot, ledger, execute=False):
    """Default to preview. Execute only the fixed, fully verified duplicate.

    All hashes and a second complete metadata inventory are checked before the
    first unlink. Directory-relative unlinks cannot follow a swapped symlink.
    No disk threshold is weakened and no other cleanup candidate is searched.
    """
    _require(type(execute) is bool, "Execute must be an explicit boolean")
    root = Path.cwd().resolve(strict=True)
    candidate = root / CANDIDATE
    snapshot, ledger = Path(snapshot).resolve(strict=True), Path(ledger).resolve(strict=True)
    _require(snapshot.is_dir(), "Original snapshot is not a directory")
    _require(not _overlaps(candidate, snapshot) and not _overlaps(candidate, ledger),
             "Cleanup candidate overlaps original snapshot or ledger")
    present = _checked_components(candidate, root, final_may_be_absent=True)
    files, ledger_sha, receipt_sha = _evidence(root, ledger)
    before = shutil.disk_usage(candidate.parent).free
    report = {"candidate": CANDIDATE.as_posix(), "execute_requested": execute,
              "checkpoint_manifest_sha256": EXPECTED_MANIFEST_SHA256,
              "local_preservation_receipt_sha256": receipt_sha,
              "ledger_sha256": ledger_sha, "free_before_bytes": before,
              "removed_files": [], "removed_logical_bytes": 0,
              "model_execution_performed": False}
    if not present:
        return {**report, "state": "already_absent", "free_after_bytes": before,
                "candidate_hashes_verified_this_call": False}
    _require(stat.S_ISDIR(candidate.lstat().st_mode), "Cleanup candidate is not a directory")
    _require({p.name for p in candidate.iterdir()} == EXPECTED_FILES,
             "Cleanup candidate contains missing or additional entries")
    identities = {}
    for name in sorted(EXPECTED_FILES):
        path = candidate / name
        info = path.lstat()
        _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                 "Checkpoint entry is not a single-link regular file")
        _require(info.st_size == files[name]["bytes"], "Checkpoint file length differs")
        digest = hashlib.sha256()
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as handle:
            _require(_identity(os.fstat(handle.fileno())) == _identity(info),
                     "Checkpoint file changed before hashing")
            for block in iter(lambda: handle.read(8 * 1024**2), b""):
                digest.update(block)
            _require(_identity(os.fstat(handle.fileno())) == _identity(info),
                     "Checkpoint file changed during hashing")
        _require(digest.hexdigest() == files[name]["sha256"], "Checkpoint file SHA256 differs")
        identities[name] = _identity(info)
    fd_state = _check_open_fds(candidate, identities)
    report.update(candidate_hashes_verified_this_call=True,
                  candidate_file_count=len(files), open_fd_inspection=fd_state,
                  candidate_logical_bytes=sum(x["bytes"] for x in files.values()))
    if not execute:
        return {**report, "state": "verified_preview", "free_after_bytes": before}

    directory_info = candidate.lstat()
    parent_fd = os.open(candidate.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    directory_fd = None
    try:
        directory_fd = os.open(candidate.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                               dir_fd=parent_fd)
        _require(_identity(os.fstat(directory_fd)) == _identity(directory_info),
                 "Checkpoint directory changed before cleanup")
        _require(set(os.listdir(directory_fd)) == EXPECTED_FILES,
                 "Checkpoint inventory changed before cleanup")
        for name, identity in identities.items():
            _require(_identity(os.stat(name, dir_fd=directory_fd, follow_symlinks=False)) == identity,
                     "Checkpoint entry changed before cleanup")
        _require(_digest(_read_regular(ledger)) == ledger_sha,
                 "Ledger changed before cleanup")
        for name in sorted(EXPECTED_FILES):
            os.unlink(name, dir_fd=directory_fd)
            report["removed_files"].append({"file": name, **files[name]})
        os.rmdir(candidate.name, dir_fd=parent_fd)
    finally:
        if directory_fd is not None:
            os.close(directory_fd)
        os.close(parent_fd)
    return {**report, "state": "verified_duplicate_removed",
            "removed_logical_bytes": sum(x["bytes"] for x in files.values()),
            "free_after_bytes": shutil.disk_usage(candidate.parent).free}
