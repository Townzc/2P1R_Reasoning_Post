"""CPU filesystem tests for the fixed E013 duplicate cleanup boundary."""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from analyses import e015_storage as storage


class DuplicatePreservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.addCleanup(self.temp.cleanup)
        self.stack.enter_context(patch.object(Path, "cwd", return_value=self.root))
        self.stack.enter_context(patch.object(storage, "_check_open_fds", return_value="fixture_idle"))
        self.candidate = self.root / storage.CANDIDATE
        self.candidate.mkdir(parents=True)
        self.snapshot = self.root / "original_base"
        self.snapshot.mkdir()
        (self.snapshot / "weights").write_bytes(b"original immutable base")
        self.ledger = self.root / "ledger.json"
        self.ledger.write_bytes(b'{"jobs": []}\n')
        self.ledger_sha = hashlib.sha256(self.ledger.read_bytes()).hexdigest()
        self.files = {}
        for name in sorted(storage.EXPECTED_FILES):
            raw = ("fixture bytes for " + name).encode()
            (self.candidate / name).write_bytes(raw)
            self.files[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        self.manifest = self.root / storage.MANIFEST
        self.manifest.write_text(json.dumps({"files": self.files}))
        self.manifest_sha = hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        self.receipt_path = self.root / storage.PRESERVATION
        self.receipt_path.parent.mkdir(parents=True)
        self.receipt = {"checkpoint": {
            "run_id": storage.RUN_ID, "manifest_path": storage.MANIFEST.as_posix(),
            "manifest_sha256": self.manifest_sha, "file_count": len(self.files),
            "total_bytes": sum(x["bytes"] for x in self.files.values()),
            "exact_inventory_verified": True, "all_files_regular_not_symlinks": True,
            "all_checkpoint_files_independently_backed_up_and_verified": True,
            "files": [{"file": name, **item} for name, item in self.files.items()]},
            "ledger": {"sha256": self.ledger_sha}}
        self.save_receipt()
        self.stack.enter_context(patch.object(storage, "EXPECTED_MANIFEST_SHA256", self.manifest_sha))
        self.stack.enter_context(patch.object(storage, "EXPECTED_LEDGER_SHA256", self.ledger_sha))

    def save_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt))

    def run_cleanup(self, execute=False, snapshot=None, ledger=None):
        return storage.reclaim_duplicate(snapshot or self.snapshot, ledger or self.ledger, execute=execute)

    def assert_rejected_without_deletion(self, **kwargs):
        before = {p.name for p in self.candidate.iterdir()}
        with patch.object(storage.os, "unlink", wraps=os.unlink) as unlink:
            with self.assertRaises((ValueError, OSError)):
                self.run_cleanup(execute=True, **kwargs)
            unlink.assert_not_called()
        self.assertEqual({p.name for p in self.candidate.iterdir()}, before)

    def test_default_preview_checks_all_files_without_deletion(self):
        result = self.run_cleanup()
        self.assertEqual(result["state"], "verified_preview")
        self.assertTrue(result["candidate_hashes_verified_this_call"])
        self.assertEqual(result["removed_files"], [])
        self.assertEqual(len(list(self.candidate.iterdir())), 12)

    def test_execute_removes_only_allowlisted_directory_and_keeps_records(self):
        record = self.candidate.parent / "metrics.json"
        record.write_bytes(b"retained raw record")
        sibling = self.candidate.parent / "another_checkpoint"
        sibling.mkdir()
        (sibling / "weights").write_bytes(b"retain")
        result = self.run_cleanup(execute=True)
        self.assertEqual(result["state"], "verified_duplicate_removed")
        self.assertFalse(self.candidate.exists())
        self.assertTrue(self.manifest.exists())
        self.assertEqual(record.read_bytes(), b"retained raw record")
        self.assertTrue((sibling / "weights").exists())
        self.assertTrue((self.snapshot / "weights").exists())
        self.assertEqual(hashlib.sha256(self.ledger.read_bytes()).hexdigest(), self.ledger_sha)
        self.assertEqual({x["file"] for x in result["removed_files"]}, storage.EXPECTED_FILES)
        self.assertEqual(result["removed_logical_bytes"], sum(x["bytes"] for x in self.files.values()))
        self.assertIn("free_after_bytes", result)

    def test_last_file_hash_tampering_rejects_before_first_unlink(self):
        path = self.candidate / sorted(storage.EXPECTED_FILES)[-1]
        path.write_bytes(b"!" * path.stat().st_size)
        self.assert_rejected_without_deletion()

    def test_extra_entry_rejects(self):
        (self.candidate / "unexpected.txt").write_bytes(b"unique state")
        self.assert_rejected_without_deletion()

    def test_symlink_entry_rejects(self):
        path = self.candidate / sorted(storage.EXPECTED_FILES)[0]
        saved = path.read_bytes()
        path.unlink()
        outside = self.root / "outside"
        outside.write_bytes(saved)
        path.symlink_to(outside)
        self.assert_rejected_without_deletion()

    def test_symlink_ancestor_rejects(self):
        parent = self.candidate.parent
        moved = parent.with_name("saved_run")
        parent.rename(moved)
        parent.symlink_to(moved, target_is_directory=True)
        self.assert_rejected_without_deletion()

    def test_hardlink_entry_rejects(self):
        path = self.candidate / sorted(storage.EXPECTED_FILES)[0]
        os.link(path, self.root / "second_link")
        self.assert_rejected_without_deletion()

    def test_snapshot_overlap_rejects(self):
        self.assert_rejected_without_deletion(snapshot=self.candidate)

    def test_ledger_overlap_rejects(self):
        path = self.candidate / sorted(storage.EXPECTED_FILES)[0]
        self.assert_rejected_without_deletion(ledger=path)

    def test_receipt_hash_mismatch_rejects(self):
        self.receipt["checkpoint"]["files"][-1]["sha256"] = "0" * 64
        self.save_receipt()
        self.assert_rejected_without_deletion()

    def test_unproven_backup_rejects(self):
        self.receipt["checkpoint"]["all_checkpoint_files_independently_backed_up_and_verified"] = False
        self.save_receipt()
        self.assert_rejected_without_deletion()

    def test_stale_ledger_rejects(self):
        self.ledger.write_bytes(b"different current ledger")
        self.assert_rejected_without_deletion()

    def test_permission_denied_fd_inspection_rejects(self):
        with patch.object(storage, "_check_open_fds", side_effect=ValueError("permission denied")):
            self.assert_rejected_without_deletion()

    def test_absent_directory_returns_state_without_deletion(self):
        for path in self.candidate.iterdir():
            path.unlink()
        self.candidate.rmdir()
        with patch.object(storage.os, "unlink", wraps=os.unlink) as unlink:
            result = self.run_cleanup()
            unlink.assert_not_called()
        self.assertEqual(result["state"], "already_absent")
        self.assertFalse(result["candidate_hashes_verified_this_call"])
        self.assertTrue(self.manifest.exists())


class ProcessDescriptorInspectionTests(unittest.TestCase):
    def test_matching_descriptor_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "checkpoint"
            candidate.mkdir()
            weight = candidate / "weight"
            weight.write_bytes(b"weights")
            proc = root / "proc"
            descriptors = proc / "123" / "fd"
            descriptors.mkdir(parents=True)
            (descriptors / "7").symlink_to(weight)
            identities = {weight.name: storage._identity(weight.stat())}
            with patch.object(storage, "PROC_ROOT", proc), patch.object(storage.sys, "platform", "linux"):
                with self.assertRaisesRegex(ValueError, "open process descriptor"):
                    storage._check_open_fds(candidate, identities)

    def test_unrelated_descriptor_is_not_treated_as_checkpoint_use(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "checkpoint"
            candidate.mkdir()
            weight = candidate / "weight"
            weight.write_bytes(b"weights")
            other = root / "log"
            other.write_bytes(b"unrelated")
            proc = root / "proc"
            descriptors = proc / "123" / "fd"
            descriptors.mkdir(parents=True)
            (descriptors / "7").symlink_to(other)
            identities = {weight.name: storage._identity(weight.stat())}
            with patch.object(storage, "PROC_ROOT", proc), patch.object(storage.sys, "platform", "linux"):
                self.assertEqual(storage._check_open_fds(candidate, identities),
                                 "no_matching_open_fds_observed")

    def test_denied_process_inventory_is_not_treated_as_idle(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory)
            proc = Mock()
            proc.is_dir.return_value = True
            proc.iterdir.side_effect = PermissionError("denied")
            with patch.object(storage, "PROC_ROOT", proc), patch.object(storage.sys, "platform", "linux"):
                with self.assertRaisesRegex(ValueError, "permission denied"):
                    storage._check_open_fds(candidate, {})


if __name__ == "__main__":
    unittest.main()
