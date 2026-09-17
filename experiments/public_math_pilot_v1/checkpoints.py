"""Full-parameter recovery with verified components and a small commit pointer.

Model bytes serve both inference and recovery. Components may live on separate
filesystems; only the control-directory pointer is atomically replaced. This
module never removes old experiments, unknown files, or unacknowledged terminal
states. The caller must hold the phase worker lock and save at update boundaries.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import re
import shutil
import uuid

SCHEMA = 1
GIB = 1024 ** 3
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z")
_SLOT = re.compile(r"slot_[0-9]{6}_[0-9a-f]{32}\Z")


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode()).hexdigest()


def _sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _fsync_dir(path):
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _json(path, value, *, replace=False):
    path = Path(path)
    if path.exists() and not replace:
        raise FileExistsError(path)
    pending = path.with_name(path.name + ".pending_" + uuid.uuid4().hex)
    with pending.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
    os.replace(pending, path)
    _fsync_dir(path.parent)


def _read(path):
    return json.loads(Path(path).read_text())


def _cpu_tree(value):
    import torch
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().contiguous()
    if isinstance(value, dict):
        return {k: _cpu_tree(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_cpu_tree(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_cpu_tree(v) for v in value)
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise TypeError(f"Unsupported recovery value: {type(value).__name__}")


def _same(left, right):
    import torch
    if isinstance(left, torch.Tensor):
        return (isinstance(right, torch.Tensor) and left.dtype == right.dtype
                and left.shape == right.shape and torch.equal(left, right))
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _tensor_bytes(value):
    import torch
    if isinstance(value, torch.Tensor):
        return value.numel() * value.element_size()
    if isinstance(value, dict):
        return sum(_tensor_bytes(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(map(_tensor_bytes, value))
    return 0


def capture_rng():
    """Weights-only-loadable complete RNG state; CUDA devices included if active."""
    import numpy as np
    import torch
    state = np.random.get_state()
    return dict(python=random.getstate(), numpy=dict(kind=state[0], keys=state[1].tolist(),
        position=state[2], has_gauss=state[3], cached_gaussian=state[4]),
        torch=torch.get_rng_state().clone(),
        cuda=[x.clone() for x in torch.cuda.get_rng_state_all()] if torch.cuda.is_initialized() else [])


def restore_rng(state):
    import numpy as np
    import torch
    if not isinstance(state, dict) or set(state) != {"python", "numpy", "torch", "cuda"}:
        raise ValueError("Complete Python/NumPy/Torch/CUDA RNG state required")
    if torch.cuda.is_initialized() and len(state["cuda"]) != torch.cuda.device_count():
        raise ValueError("Recovery CUDA RNG device count differs")
    random.setstate(state["python"])
    n = state["numpy"]
    np.random.set_state((n["kind"], np.asarray(n["keys"], dtype=np.uint32),
                        n["position"], n["has_gauss"], n["cached_gaussian"]))
    torch.set_rng_state(state["torch"])
    if state["cuda"]:
        if not torch.cuda.is_available() or len(state["cuda"]) != torch.cuda.device_count():
            raise ValueError("Recovery CUDA RNG device count differs")
        torch.cuda.set_rng_state_all(state["cuda"])


class CheckpointStore:
    """Owned per-arm components on one or two configured volume roots.

    ``save`` takes state_dicts, not model/optimizer objects. Restore those objects
    with their strict load_state_dict APIs, then call restore_rng immediately
    before the next update. ``metadata`` should bind history, LR and row identity.
    Component references contain volume indices and relative paths, no host paths.
    """
    def __init__(self, control_dir, volume_roots, *, phase, arm, config_hash,
                 reserve_bytes=2 * GIB):
        if not _NAME.fullmatch(phase) or not _NAME.fullmatch(arm):
            raise ValueError("Invalid phase/arm namespace")
        if not re.fullmatch(r"[0-9a-f]{64}", config_hash):
            raise ValueError("Full configuration SHA256 required")
        if type(reserve_bytes) is not int or reserve_bytes < 0:
            raise ValueError("Invalid per-filesystem reserve")
        roots = [Path(p).expanduser().resolve() for p in volume_roots]
        if not 1 <= len(roots) <= 2 or len(set(roots)) != len(roots):
            raise ValueError("Provide one or two distinct volume roots")
        self.control = Path(control_dir).expanduser().resolve()
        self.roots = roots
        self.reserve_bytes = reserve_bytes
        self.identity = dict(schema=SCHEMA, phase=phase, arm=arm, config_hash=config_hash)
        self.relative = Path(phase) / arm
        self.control.mkdir(parents=True, exist_ok=True)
        _fsync_dir(self.control.parent)
        self._own(self.control)
        for folder in ("commits", "acks", "deletions"):
            path = self.control / folder
            if path.is_symlink():
                raise ValueError("Symlinked control directory")
            path.mkdir(exist_ok=True)
        _fsync_dir(self.control)
        for root in self.roots:
            root.mkdir(parents=True, exist_ok=True)
            _fsync_dir(root.parent)
            self._mkdir_owned(root)

    def _own(self, directory):
        marker = directory / "checkpoint_owner.json"
        if marker.is_symlink():
            raise ValueError("Symlinked owner marker")
        if marker.exists():
            if _read(marker) != self.identity:
                raise ValueError("Checkpoint directory belongs to another identity")
        else:
            # Existing unknown contents are never adopted into the deletion scope.
            if any(directory.iterdir()):
                raise ValueError("Refusing to adopt a nonempty unowned directory")
            _json(marker, self.identity)

    def _mkdir_owned(self, root):
        phase = root / self.identity["phase"]
        if phase.is_symlink():
            raise ValueError("Symlinked phase namespace")
        phase.mkdir(exist_ok=True)
        _fsync_dir(root)
        folder = root / self.relative
        if folder.is_symlink():
            raise ValueError("Symlinked arm namespace")
        folder.mkdir(exist_ok=True)
        _fsync_dir(phase)
        self._own(folder)
        slots = folder / "slots"
        if slots.is_symlink():
            raise ValueError("Symlinked slots namespace")
        slots.mkdir(exist_ok=True)
        _fsync_dir(folder)

    @contextmanager
    def _lock(self):
        path = self.control / "writer.lock"
        if path.is_symlink():
            raise ValueError("Symlinked writer lock")
        with path.open("a+") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def _manifest_path(self, checkpoint_id):
        if not isinstance(checkpoint_id, str) or not _SLOT.fullmatch(checkpoint_id):
            raise ValueError("Invalid checkpoint identifier")
        if (self.control / "commits").is_symlink():
            raise ValueError("Symlinked commit directory")
        return self.control / "commits" / (checkpoint_id + ".json")

    def _manifest(self, manifest):
        if isinstance(manifest, str):
            manifest = _read(self._manifest_path(manifest))
        if not isinstance(manifest, dict) or manifest.get("identity") != self.identity:
            raise ValueError("Foreign checkpoint identity")
        path = self._manifest_path(manifest["checkpoint_id"])
        if path.is_symlink() or not path.is_file() or _read(path) != manifest:
            raise ValueError("Immutable committed manifest differs")
        return manifest

    def _path(self, record):
        volume = record["volume"]
        if type(volume) is not int or not 0 <= volume < len(self.roots):
            raise ValueError("Invalid component volume")
        rel = Path(record["path"])
        parts = rel.parts
        if (rel.is_absolute() or len(parts) != 5 or Path(*parts[:2]) != self.relative
                or parts[2] != "slots" or not _SLOT.fullmatch(parts[3])
                or parts[4] not in ("model.pt", "training.pt")):
            raise ValueError("Component lies outside owned checkpoint scope")
        root = self.roots[volume]
        path = root
        for part in parts:
            path /= part
            if path.is_symlink():
                raise ValueError("Symlinked checkpoint component path")
        owner = root / self.relative / "checkpoint_owner.json"
        if owner.is_symlink() or _read(owner) != self.identity:
            raise ValueError("Storage namespace identity changed")
        return path

    def _verify_file(self, record):
        path = self._path(record)
        if not path.is_file() or path.stat().st_size != record["bytes"] or _sha(path) != record["sha256"]:
            raise ValueError("Checkpoint component bytes/hash differ or are missing")
        return path

    def latest_manifest(self):
        pointer = self.control / "latest.json"
        if not pointer.exists():
            return None
        if pointer.is_symlink():
            raise ValueError("Symlinked latest pointer")
        record = _read(pointer)
        path = self._manifest_path(record["checkpoint_id"])
        if path.is_symlink() or _sha(path) != record["manifest_sha256"]:
            raise ValueError("Latest manifest hash differs")
        manifest = self._manifest(record["checkpoint_id"])
        if manifest["step"] != record["step"]:
            raise ValueError("Latest absolute step differs")
        return manifest

    def _placement(self, sizes):
        # Account by device, even when two configured roots share a filesystem.
        devices = [root.stat().st_dev for root in self.roots]
        free = {}
        for root, dev in zip(self.roots, devices):
            free[dev] = min(free.get(dev, float("inf")), shutil.disk_usage(root).free)
        options = []
        for assignment in itertools.product(range(len(self.roots)), repeat=len(sizes)):
            used = dict.fromkeys(free, 0)
            for volume, size in zip(assignment, sizes):
                used[devices[volume]] += size
            slack = {dev: free[dev] - used[dev] - self.reserve_bytes for dev in free}
            if min(slack.values()) >= 0:
                options.append((min(slack.values()), assignment))
        if not options:
            raise OSError("Insufficient per-filesystem space for atomic recovery plus reserve")
        return max(options, key=lambda item: item[0])[1]

    def _write_tensor_file(self, value, volume, checkpoint_id, name):
        import torch
        rel = self.relative / "slots" / checkpoint_id / name
        record = dict(volume=volume, path=rel.as_posix())
        path = self._path(record)
        path.parent.mkdir(exist_ok=True)
        _fsync_dir(path.parent.parent)
        pending = path.with_name(name + ".pending")
        cpu = _cpu_tree(value)
        with pending.open("xb") as stream:
            torch.save(cpu, stream)
            stream.flush(); os.fsync(stream.fileno())
        check = torch.load(pending, map_location="cpu", weights_only=True)
        if not _same(cpu, check):
            raise ValueError("Recovery serialization round-trip differs")
        del check, cpu
        os.replace(pending, path)
        _fsync_dir(path.parent)
        record.update(bytes=path.stat().st_size, sha256=_sha(path))
        return record

    def save(self, model_state, optimizer_state, *, step, token_step,
             scheduler_state, rng_state, metadata=None, scientific=False, terminal=False):
        import torch
        if type(step) is not int or not 0 <= step <= 999999 or type(token_step) is not int or token_step < 0:
            raise ValueError("Invalid absolute update/token counter")
        if (not isinstance(model_state, dict) or not model_state
                or any(not isinstance(k, str) or not isinstance(v, torch.Tensor) for k, v in model_state.items())
                or any(v.is_floating_point() and v.dtype != torch.float32 for v in model_state.values())):
            raise ValueError("Full FP32 model state required")
        if type(scientific) is not bool or type(terminal) is not bool or terminal and not scientific:
            raise ValueError("Terminal state must be a scientific checkpoint")
        if not isinstance(rng_state, dict) or set(rng_state) != {"python", "numpy", "torch", "cuda"}:
            raise ValueError("Complete Python/NumPy/Torch/CUDA RNG state required")
        metadata = {} if metadata is None else metadata
        _digest(metadata)  # Require a finite, JSON-safe public identity record.
        with self._lock():
            previous = self.latest_manifest()
            if previous and (previous["terminal"] or step <= previous["step"] or token_step < previous["token_step"]):
                raise ValueError("Cannot overwrite, rewind, or continue a terminal checkpoint")
            checkpoint_id = f"slot_{step:06d}_{uuid.uuid4().hex}"
            training = dict(identity=self.identity, checkpoint_id=checkpoint_id, step=step,
                token_step=token_step, optimizer_state=optimizer_state, scheduler_state=scheduler_state,
                rng_state=rng_state, metadata=metadata)
            # One percent plus 1 MiB allows serialization/container overhead.
            sizes = [int(_tensor_bytes(value) * 1.01) + 1024**2 for value in (model_state, training)]
            placement = self._placement(sizes)
            model_file = self._write_tensor_file(model_state, placement[0], checkpoint_id, "model.pt")
            training_file = self._write_tensor_file(training, placement[1], checkpoint_id, "training.pt")
            spec = {k: dict(shape=list(v.shape), dtype=str(v.dtype)) for k, v in model_state.items()}
            manifest = dict(identity=self.identity, checkpoint_id=checkpoint_id, step=step,
                token_step=token_step, scientific=scientific, terminal=terminal,
                files=dict(model=model_file, training=training_file), model_spec=spec,
                metadata=metadata, committed_at_utc=datetime.now(timezone.utc).isoformat())
            # Check actual remaining capacity before publishing. Failure retains old
            # recovery and the uncommitted files as evidence; it never prunes first.
            self._placement([0])
            path = self._manifest_path(checkpoint_id)
            _json(path, manifest)
            self._before_publish(manifest)
            _json(self.control / "latest.json", dict(checkpoint_id=checkpoint_id,
                step=step, manifest_sha256=_sha(path)), replace=True)
            if previous:
                names = ["training"] + ([] if previous["scientific"] else ["model"])
                self._delete_files(previous, names, reason="new_recovery_verified_and_committed")
            return manifest

    def _before_publish(self, manifest):
        """Fault-injection seam; no model work is performed here."""

    def load(self, manifest):
        import torch
        manifest = self._manifest(manifest)
        model = torch.load(self._verify_file(manifest["files"]["model"]), map_location="cpu", weights_only=True)
        training = torch.load(self._verify_file(manifest["files"]["training"]), map_location="cpu", weights_only=True)
        if (training["identity"] != self.identity or training["checkpoint_id"] != manifest["checkpoint_id"]
                or training["step"] != manifest["step"] or training["token_step"] != manifest["token_step"]
                or training["metadata"] != manifest["metadata"]):
            raise ValueError("Serialized recovery identity differs")
        spec = {k: dict(shape=list(v.shape), dtype=str(v.dtype)) for k, v in model.items()}
        if spec != manifest["model_spec"]:
            raise ValueError("Serialized full-model schema differs")
        return dict(model_state=model, **training)

    def load_latest(self):
        manifest = self.latest_manifest()
        return None if manifest is None else self.load(manifest)

    def mark_backup(self, manifest, files):
        """Record transport's independent LOCAL verification, never self-ACK.

        files has exactly model/training, each with sha256, bytes and the explicit
        boolean verified_local=True. The transport must hash actual local bytes.
        """
        manifest = self._manifest(manifest)
        if not isinstance(files, dict) or set(files) != {"model", "training"}:
            raise ValueError("Complete independent model and training backup required")
        for name, expected in manifest["files"].items():
            got = files[name]
            if (got.get("verified_local") is not True or got.get("sha256") != expected["sha256"]
                    or type(got.get("bytes")) is not int or got["bytes"] != expected["bytes"]):
                raise ValueError("Local backup receipt does not match component identity")
        ack = dict(identity=self.identity, checkpoint_id=manifest["checkpoint_id"],
            manifest_sha256=_sha(self._manifest_path(manifest["checkpoint_id"])),
            verified_at_utc=datetime.now(timezone.utc).isoformat(),
            files={name: {k: files[name][k] for k in ("sha256", "bytes", "verified_local")} for name in files})
        path = self.control / "acks" / (manifest["checkpoint_id"] + ".json")
        with self._lock():
            if path.exists():
                old = _read(path)
                if {k:v for k,v in old.items() if k != "verified_at_utc"} != {k:v for k,v in ack.items() if k != "verified_at_utc"}:
                    raise ValueError("Immutable backup ACK changed")
                return old
            _json(path, ack)
        return ack

    def _check_ack(self, manifest, ack):
        path = self.control / "acks" / (manifest["checkpoint_id"] + ".json")
        if (not isinstance(ack, dict) or not path.is_file() or path.is_symlink() or _read(path) != ack
                or ack.get("identity") != self.identity or ack.get("checkpoint_id") != manifest["checkpoint_id"]
                or ack.get("manifest_sha256") != _sha(self._manifest_path(manifest["checkpoint_id"]))):
            raise ValueError("Matching independently verified local ACK required")
        for name, record in manifest["files"].items():
            got = ack["files"][name]
            if got.get("verified_local") is not True or got["sha256"] != record["sha256"] or got["bytes"] != record["bytes"]:
                raise ValueError("ACK component hash/size differs")

    def _delete_files(self, manifest, names, *, reason):
        manifest = self._manifest(manifest)
        # Validate all targets before the first unlink. Never follow a caller path.
        targets = []
        for name in names:
            record = manifest["files"][name]
            path = self._path(record)
            if path.exists():
                self._verify_file(record)
                targets.append((name, path))
        if not targets:
            return []
        receipt = dict(identity=self.identity, checkpoint_id=manifest["checkpoint_id"],
            reason=reason, files={name: manifest["files"][name] for name, _ in targets},
            at_utc=datetime.now(timezone.utc).isoformat())
        path = self.control / "deletions" / (manifest["checkpoint_id"] + "_" + uuid.uuid4().hex + ".json")
        _json(path, receipt)
        for _, target in targets:
            target.unlink(); _fsync_dir(target.parent)
        return [name for name, _ in targets]

    def prune_terminal_optimizer(self, manifest, ack):
        with self._lock():
            manifest = self._manifest(manifest)
            if not manifest["terminal"] or not manifest["scientific"]:
                raise ValueError("Only a terminal scientific recovery can be exported then pruned")
            self._check_ack(manifest, ack)
            self._verify_file(manifest["files"]["model"])
            return self._delete_files(manifest, ["training"], reason="terminal_full_local_backup_verified")

    def discard_engineering(self, manifest, *, roundtrip_receipt):
        """Explicitly discard non-scientific smoke state after verified reload.

        No independent large-file backup is needed for a discarded engineering
        update. Its exact component hashes and compact round-trip receipt remain.
        The dedicated phase must end in ``_engineering``; formal states fail shut.
        """
        with self._lock():
            manifest = self._manifest(manifest)
            metadata = manifest["metadata"]
            if (not self.identity["phase"].endswith("_engineering") or manifest["scientific"]
                    or manifest["terminal"] or metadata.get("formal") is not False
                    or metadata.get("discard_before_main") is not True):
                raise ValueError("Only explicitly disposable engineering state may be discarded")
            if (not isinstance(roundtrip_receipt, dict) or roundtrip_receipt.get("checkpoint") != manifest
                    or roundtrip_receipt.get("formal") is not False
                    or roundtrip_receipt.get("step") != manifest["step"]
                    or roundtrip_receipt.get("token_step") != manifest["token_step"]
                    or roundtrip_receipt.get("roundtrip_verified") is not True):
                raise ValueError("Matching verified engineering round-trip receipt required")
            record = dict(identity=self.identity, checkpoint_id=manifest["checkpoint_id"],
                roundtrip_receipt=roundtrip_receipt, reason="nonformal_smoke_state_discarded_before_main")
            path = self.control / ("engineering_discard_" + manifest["checkpoint_id"] + ".json")
            if path.exists():
                if path.is_symlink() or _read(path) != record:
                    raise ValueError("Immutable engineering discard receipt changed")
            else:
                _json(path, record)
            return self._delete_files(manifest, ["model", "training"],
                                      reason="verified_engineering_roundtrip_not_scientific")

    def prune_scientific_temp(self, manifest, ack=None, *, evaluation_complete=False):
        with self._lock():
            manifest = self._manifest(manifest)
            if manifest["step"] != 64 or not manifest["scientific"] or manifest["terminal"] or evaluation_complete is not True:
                raise ValueError("Only evaluated nonterminal step64 is a temporary scientific checkpoint")
            latest = self.latest_manifest()
            if latest is None:
                raise ValueError("Missing latest recovery pointer; reconcile before temporary cleanup")
            if ack is not None:
                self._check_ack(manifest, ack)
            elif not latest or latest["step"] != 128 or not latest["terminal"]:
                raise ValueError("Step64 deletion needs full backup ACK or verified terminal step128")
            else:
                for record in latest["files"].values():
                    self._verify_file(record)
            if latest["checkpoint_id"] == manifest["checkpoint_id"]:
                raise ValueError("Never remove the current active recovery for a temporary checkpoint")
            return self._delete_files(manifest, ["model", "training"], reason="evaluated_step64_superseded_or_backed")
