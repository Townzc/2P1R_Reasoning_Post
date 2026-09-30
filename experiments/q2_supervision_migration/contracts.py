"""CPU-only evidence contracts; no model loader, scorer, or automatic resume.

Files are exclusive-create, content-hashed JSONL. A reserved but unfinished batch
is ambiguous work, not permission to replay it. Hashes detect modification; they
are not OS-enforced WORM storage or proof that declared model/scorer versions ran.
"""

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Mapping, Sequence


class ContractError(ValueError):
    pass


class ReplayRefused(ContractError):
    pass


class CollisionError(ContractError):
    pass


class IncompleteScoring(ContractError):
    pass


class VerdictStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SCORER_ERROR = "scorer_error"
    TIMEOUT = "timeout"
    MISSING = "missing"


@dataclass(frozen=True)
class SuiteVerdict:
    status: VerdictStatus
    detail: str = ""

    def __post_init__(self):
        object.__setattr__(self, "status", VerdictStatus(self.status))
        if not isinstance(self.detail, str):
            raise ContractError("verdict detail must be text")


def reward_from_verdicts(base: SuiteVerdict, extra: SuiteVerdict, mode: str) -> int:
    """Require both verdicts, even for base reward: dual scoring is mandatory.

    TIMEOUT means unresolved attribution and stops training. A scorer may emit
    FAIL for a confirmed candidate violation of the frozen test resource limit,
    but must explicitly classify that outcome, not convert infrastructure errors.
    """
    if mode not in {"base", "extra", "union"}:
        raise ContractError("unknown reward mode")
    for verdict in (base, extra):
        if not isinstance(verdict, SuiteVerdict):
            raise ContractError("expected SuiteVerdict")
        if verdict.status not in {VerdictStatus.PASS, VerdictStatus.FAIL}:
            raise IncompleteScoring(f"unresolved score: {verdict.status.value}")
    b, e = base.status == VerdictStatus.PASS, extra.status == VerdictStatus.PASS
    return int(b if mode == "base" else e if mode == "extra" else b and e)


def _canonical(value) -> bytes:
    def check_keys(item):
        if isinstance(item, dict):
            if any(not isinstance(k, str) for k in item):
                raise ContractError("JSON identity keys must be strings")
            for child in item.values():
                check_keys(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                check_keys(child)
    check_keys(value)
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ContractError("not canonical JSON") from exc


def identity_hash(value) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _hash(value: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ContractError("expected lowercase SHA-256")
    return value


def _text(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError("expected nonempty text identifier")
    return value


def _number(value: int) -> int:
    if type(value) is not int or value < 0:
        raise ContractError("expected nonnegative integer")
    return value


def _signed(body: dict) -> dict:
    return {**body, "record_sha256": identity_hash(body)}


def _verify(record: dict) -> dict:
    if not isinstance(record, dict) or "record_sha256" not in record:
        raise ContractError("missing record identity")
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    if _hash(record["record_sha256"]) != identity_hash(body):
        raise ContractError("record content changed")
    return record


def _write_once(path: Path, records: Sequence[dict]) -> None:
    data = b"".join(_canonical(_verify(r)) + b"\n" for r in records)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    except FileExistsError as exc:
        if not path.is_symlink() and path.is_file() and path.read_bytes() == data:
            raise ReplayRefused(f"already written: {path.name}") from exc
        raise CollisionError(f"existing or ambiguous record: {path.name}") from exc
    # On any write failure leave the file in place: never erase ambiguous work.
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def read_records(path: Path) -> list[dict]:
    path = Path(path)
    if path.is_symlink():
        raise ContractError("record must not be a symlink")
    raw = path.read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise ContractError("empty or incomplete JSONL")
    try:
        records = [_verify(json.loads(line)) for line in raw.splitlines()]
    except (ValueError, UnicodeError, TypeError) as exc:
        raise ContractError("invalid JSONL evidence") from exc
    if raw != b"".join(_canonical(r) + b"\n" for r in records):
        raise ContractError("noncanonical JSONL evidence")
    return records


@dataclass(frozen=True)
class BatchReservation:
    directory: Path
    intent_sha256: str

    def intent(self) -> dict:
        rows = read_records(self.directory / "intent.jsonl")
        if len(rows) != 1 or rows[0]["record_sha256"] != self.intent_sha256:
            raise ContractError("batch intent changed")
        return rows[0]


def reserve_batch(root: Path, *, run_id: str, phase_id: str, batch_index: int,
                  tasks: Sequence[str], policy_sha256: str,
                  config_sha256: str) -> BatchReservation:
    """tasks has one task ID per expected completion, including group repeats."""
    if isinstance(tasks, (str, bytes)) or not tasks:
        raise ContractError("nonempty task sequence required")
    key = {"run_id": _text(run_id), "phase_id": _text(phase_id),
           "batch_index": _number(batch_index)}
    body = {"kind": "batch_intent", "schema": 1, **key,
            "tasks": [_text(t) for t in tasks],
            "policy_sha256": _hash(policy_sha256),
            "config_sha256": _hash(config_sha256)}
    record = _signed(body)
    directory = Path(root) / identity_hash(key)
    directory.parent.mkdir(parents=True, exist_ok=True)
    try:
        directory.mkdir()
    except FileExistsError as exc:
        # Even an empty directory is a reservation: do not replay after a crash.
        old = directory / "intent.jsonl"
        if not directory.is_symlink() and old.is_file():
            try:
                if read_records(old) == [record]:
                    raise ReplayRefused("batch already reserved; reconcile it") from exc
            except ReplayRefused:
                raise
            except ContractError:
                pass
        raise CollisionError("batch identity exists or is ambiguous") from exc
    _write_once(directory / "intent.jsonl", [record])
    return BatchReservation(directory, record["record_sha256"])


def record_sample(batch: BatchReservation, *, sample_index: int,
                  completion_text: str, completion_token_ids: Sequence[int],
                  base: SuiteVerdict, extra: SuiteVerdict,
                  finish_reason: str) -> dict:
    """Preserve unmodified raw text and IDs, including unresolved score evidence."""
    intent = batch.intent()
    i = _number(sample_index)
    if i >= len(intent["tasks"]):
        raise ContractError("sample not in reserved batch")
    if (batch.directory / "batch.jsonl").exists():
        raise ReplayRefused("batch is already sealed")
    if not isinstance(completion_text, str):
        raise ContractError("raw completion text required")
    if isinstance(completion_token_ids, (str, bytes)):
        raise ContractError("token IDs must be an integer sequence")
    ids = [_number(token) for token in completion_token_ids]
    if not isinstance(base, SuiteVerdict) or not isinstance(extra, SuiteVerdict):
        raise ContractError("explicit dual verdicts required")
    record = _signed({"kind": "sample", "schema": 1,
                      "intent_sha256": batch.intent_sha256,
                      "sample_id": identity_hash({"intent": batch.intent_sha256,
                                                  "sample_index": i}),
                      "sample_index": i, "task_id": intent["tasks"][i],
                      "policy_sha256": intent["policy_sha256"],
                      "completion_text": completion_text,
                      "completion_token_ids": ids,
                      "finish_reason": _text(finish_reason),
                      "base": asdict(base), "extra": asdict(extra)})
    _write_once(batch.directory / f"sample_{i:08d}.jsonl", [record])
    return record


def seal_batch(batch: BatchReservation) -> Path:
    """Seal all samples, including failure receipts; does not authorize an update."""
    intent = batch.intent()
    samples = []
    for i, task in enumerate(intent["tasks"]):
        path = batch.directory / f"sample_{i:08d}.jsonl"
        if not path.is_file():
            raise ContractError(f"incomplete batch: missing sample {i}")
        rows = read_records(path)
        if len(rows) != 1:
            raise ContractError("one sample per sample file required")
        row = rows[0]
        if (row.get("intent_sha256") != batch.intent_sha256 or
                row.get("sample_index") != i or row.get("task_id") != task or
                row.get("policy_sha256") != intent["policy_sha256"] or
                row.get("sample_id") != identity_hash({"intent": batch.intent_sha256,
                                                        "sample_index": i})):
            raise ContractError("sample does not belong to batch")
        samples.append(row)
    expected = {f"sample_{i:08d}.jsonl" for i in range(len(samples))}
    if {p.name for p in batch.directory.glob("sample_*.jsonl")} != expected:
        raise ContractError("unexpected sample file")
    output = batch.directory / "batch.jsonl"
    _write_once(output, [intent, *samples])
    return output


def _artifact_hashes(artifacts: Mapping[str, Path]) -> dict:
    if not artifacts:
        raise ContractError("artifact set cannot be empty")
    result = {}
    for name, value in artifacts.items():
        _text(name)
        path = Path(value)
        if path.is_symlink() or not path.is_file():
            raise ContractError("artifact must be a regular file")
        before = path.stat()
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        after = path.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_ino, after.st_size, after.st_mtime_ns):
            raise ContractError("artifact changed during hashing")
        result[name] = {"sha256": digest.hexdigest(), "size_bytes": after.st_size}
    return result


def build_fresh_fork_manifest(*, run_id: str, phase_id: str,
                              policy_files: Mapping[str, Path],
                              tokenizer_files: Mapping[str, Path],
                              phase_config: dict, phase_seed: int,
                              prompt_schedule_sha256: str) -> dict:
    if not isinstance(phase_config, dict) or not phase_config:
        raise ContractError("explicit nonempty phase configuration required")
    # Roundtrip to detach the manifest from caller-owned mutable dictionaries.
    config = json.loads(_canonical(phase_config))
    return _signed({"kind": "fresh_weight_fork", "schema": 1,
                    "run_id": _text(run_id), "phase_id": _text(phase_id),
                    "policy_files": _artifact_hashes(policy_files),
                    "tokenizer_files": _artifact_hashes(tokenizer_files),
                    "phase_config": config, "phase_seed": _number(phase_seed),
                    "prompt_schedule_sha256": _hash(prompt_schedule_sha256),
                    "optimizer": "fresh", "scheduler": "fresh_phase",
                    "rng": "fresh_phase", "resume_old_state": False})


def verify_fork_sources(manifest: dict, *, policy_files: Mapping[str, Path],
                        tokenizer_files: Mapping[str, Path]) -> None:
    _validate_fresh_fork(manifest)
    if (manifest["policy_files"] != _artifact_hashes(policy_files) or
            manifest["tokenizer_files"] != _artifact_hashes(tokenizer_files)):
        raise ContractError("fork source identity mismatch")


def _validate_fresh_fork(manifest: dict) -> None:
    _verify(manifest)
    if (manifest.get("kind") != "fresh_weight_fork" or
            manifest.get("optimizer") != "fresh" or
            manifest.get("scheduler") != "fresh_phase" or
            manifest.get("rng") != "fresh_phase" or
            manifest.get("resume_old_state") is not False):
        raise ContractError("not a fresh-state fork")
    _text(manifest.get("run_id"))
    _text(manifest.get("phase_id"))
    _number(manifest.get("phase_seed"))
    _hash(manifest.get("prompt_schedule_sha256"))
    for name in ("phase_config", "policy_files", "tokenizer_files"):
        if not isinstance(manifest.get(name), dict) or not manifest[name]:
            raise ContractError(f"missing fork field: {name}")


def reserve_fork(root: Path, manifest: dict) -> Path:
    _validate_fresh_fork(manifest)
    key = {"run_id": _text(manifest["run_id"]),
           "phase_id": _text(manifest["phase_id"])}
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / (identity_hash(key) + ".jsonl")
    _write_once(path, [manifest])
    return path
