"""Immutable records, phase-specific physical budgets, and path/source checks."""
from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import uuid

PHASE = "supervision_controls_v1"
NEW_ARMS = ("random", "position_difficulty")
OLD_ARMS = ("SFT", "DFT", "TrimSFT", "QDW_v0")
SAMPLE_SEED = 2026092902


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if read(path) != value:
            raise ValueError("Existing immutable record differs: " + str(path))
        return
    tmp = path.with_name(path.name + ".pending_" + uuid.uuid4().hex)
    with tmp.open("x") as f:
        json.dump(value, f, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        f.write("\n"); f.flush(); os.fsync(f.fileno())
    # The caller holds the phase/analysis lock; never overwrite a prior record.
    if path.exists():
        raise FileExistsError(path)
    os.rename(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def independent_output(output, prior):
    output, prior = Path(output).resolve(), Path(prior).resolve()
    if output == prior or output in prior.parents or prior in output.parents:
        raise ValueError("New output must be disjoint from the historical phase")
    return output, prior


def source_check(commit, inventory_sha256=None):
    root = Path(__file__).resolve().parents[2]
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("Full published source SHA required")
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()
    names = ["experiments/public_math_pilot_v1", "experiments/supervision_controls_v1"]
    if not (root/".git").exists():
        inventory = root/"SOURCE_INVENTORY.json"
        if not inventory_sha256 or sha(inventory) != inventory_sha256:
            raise ValueError("Archive requires independently supplied inventory SHA")
        record = read(inventory)
        actual = {p.relative_to(root).as_posix():sha(p) for name in names
                  for p in (root/name).rglob("*.py") if "__pycache__" not in p.parts}
        if record["commit"] != commit or record["python_source_sha256"] != actual:
            raise ValueError("Archive source identity differs")
        for rel, expected in record["configuration_sha256"].items():
            path = (root/rel).resolve()
            if root not in path.parents or sha(path) != expected:
                raise ValueError("Archive configuration identity differs")
        return record
    if git("rev-parse", "HEAD") != commit:
        raise ValueError("Source checkout HEAD differs")
    if git("status", "--porcelain", "--", *names):
        raise ValueError("Execution source or frozen inputs are uncommitted")
    files = git("ls-files", "--", *names).splitlines()
    return dict(commit=commit, files_sha256={p:sha(root/p) for p in files
                    if p.endswith((".py", ".json", ".md")) and "/release_v1/" not in p})


class Ledger:
    """New phase allowance; this does not replace any historical receipt ledger."""
    caps = {"optimizer_update": 256, "generation": 4096}

    def __init__(self, path):
        self.path = Path(path)

    def events(self):
        return [json.loads(x) for x in self.path.read_text().splitlines()] if self.path.exists() else []

    def reserve(self, kind, logical_ids):
        if kind not in self.caps or not logical_ids or len(set(logical_ids)) != len(logical_ids):
            raise ValueError("Invalid physical reservation")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            events = [json.loads(x) for x in f if x.strip()]
            if any(e["phase"] != PHASE for e in events):
                raise ValueError("This file belongs to another phase")
            previous = [e["logical_id"] for e in events if e["kind"] == kind]
            if set(previous) & set(logical_ids):
                raise RuntimeError("Reserved work cannot be silently repeated")
            if len(previous) + len(logical_ids) > self.caps[kind]:
                raise RuntimeError("Physical phase cap exhausted")
            f.seek(0, 2)
            for i, logical_id in enumerate(logical_ids, len(previous)+1):
                f.write(json.dumps(dict(phase=PHASE, kind=kind, logical_id=logical_id,
                                       ordinal=i, time_utc=datetime.now(timezone.utc).isoformat())) + "\n")
            f.flush(); os.fsync(f.fileno())
