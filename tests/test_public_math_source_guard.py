import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from experiments.public_math_pilot_v1.source_guard import verify_inventory, bound_preflight_arguments


class SourceGuardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "experiments/public_math_pilot_v1"
        self.source.mkdir(parents=True)
        for name in ("source_guard.py", "preflight.py", "nested/vendor.py"):
            path = self.source / name; path.parent.mkdir(exist_ok=True)
            path.write_text("# frozen CPU fixture\n")
        self.inputs = self.root / "inputs.json"; self.inputs.write_text('{"rows": []}\n')
        self.commit = "a" * 40
        self.inventory = self.root / "inventory.json"
        self.freeze()

    def freeze(self):
        data = dict(schema=1, source_commit=self.commit,
            source_files_sha256={p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in self.source.rglob("*.py") if "__pycache__" not in p.parts},
            inputs_sha256=hashlib.sha256(self.inputs.read_bytes()).hexdigest())
        self.inventory.write_text(json.dumps(data, sort_keys=True))
        self.inventory_sha = hashlib.sha256(self.inventory.read_bytes()).hexdigest()

    def verify(self):
        return verify_inventory(self.inventory, self.inputs, expected_source_commit=self.commit,
            expected_inventory_sha256=self.inventory_sha, repo_root=self.root)

    def test_archive_without_git_is_verified(self):
        result = self.verify()
        self.assertEqual(result["python_source_files"], 3)
        self.assertFalse(result["git_checkout_additionally_checked"])
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_source_input_or_inventory_changed_are_rejected(self):
        (self.source / "preflight.py").write_text("changed\n")
        with self.assertRaisesRegex(ValueError, "Python source SHA"):
            self.verify()
        self.freeze(); self.inputs.write_text("changed input")
        with self.assertRaisesRegex(ValueError, "input SHA"):
            self.verify()
        self.freeze(); self.inventory.write_text(self.inventory.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "inventory SHA"):
            self.verify()

    def test_extra_or_missing_python_is_rejected_but_cache_ignored(self):
        cache = self.source / "__pycache__"; cache.mkdir()
        (cache / "not_source.py").write_text("ignored cache")
        self.verify()
        extra = self.source / "extra.py"; extra.write_text("unexpected")
        with self.assertRaisesRegex(ValueError, "extra"):
            self.verify()
        extra.unlink(); (self.source / "nested/vendor.py").unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            self.verify()

    def test_symlink_source_and_symlink_directory_rejected(self):
        outside = self.root / "outside.py"; outside.write_text("# frozen CPU fixture\n")
        path = self.source / "preflight.py"; path.unlink(); path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "Symlinked"):
            self.verify()
        path.unlink(); path.write_text("# frozen CPU fixture\n")
        (self.source / "link").symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symlinked"):
            self.verify()

    def test_duplicate_inventory_keys_and_wrong_commit_rejected(self):
        data = self.inventory.read_text()
        self.inventory.write_text(data[:-1] + ',"schema":1}')
        self.inventory_sha = hashlib.sha256(self.inventory.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.verify()
        self.freeze(); self.commit = "b" * 40
        with self.assertRaisesRegex(ValueError, "commit"):
            self.verify()

    def test_git_checkout_has_additional_head_and_clean_checks(self):
        def git(*args):
            return subprocess.check_output(["git", "-C", str(self.root), *args], text=True,
                stderr=subprocess.DEVNULL).strip()
        git("init", "-q"); git("add", "experiments")
        git("-c", "user.name=CPU Test", "-c", "user.email=cpu@example.invalid", "commit", "-qm", "fixture")
        self.commit = git("rev-parse", "HEAD"); self.freeze()
        self.assertTrue(self.verify()["git_checkout_additionally_checked"])
        (self.source / "preflight.py").write_text("changed\n"); self.freeze()
        with self.assertRaisesRegex(ValueError, "untracked or changed"):
            self.verify()

    def test_execution_identity_is_bound_and_input_is_absolute(self):
        args = bound_preflight_arguments(["--", "--inputs", str(self.inputs), "--source-commit", self.commit,
                                          "--output", "out"], inputs_path=self.inputs, source_commit=self.commit)
        self.assertEqual(args[1], str(self.inputs.resolve()))
        self.assertEqual(args[-2:], ["--output", "out"])
        for bad in (["--inputs", str(self.inputs), "--source-commit", "b" * 40],
                    ["--inputs", str(self.root / "other.json"), "--source-commit", self.commit],
                    ["--inputs", str(self.inputs), "--inputs", str(self.inputs), "--source-commit", self.commit]):
            with self.assertRaises(ValueError):
                bound_preflight_arguments(bad, inputs_path=self.inputs, source_commit=self.commit)


if __name__ == "__main__":
    unittest.main()
