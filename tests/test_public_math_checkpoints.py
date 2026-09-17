"""Tiny CPU checks of full-state commit, recovery and deletion boundaries."""
import copy
import json
from pathlib import Path
import random
from types import SimpleNamespace

import numpy as np
import tempfile
import unittest
from unittest.mock import patch
import torch

from experiments.public_math_pilot_v1 import checkpoints as cp


def store(tmp_path, **kwargs):
    return cp.CheckpointStore(tmp_path / "control", [tmp_path / "a", tmp_path / "b"],
        phase="public_math_pilot_v1", arm="SFT", config_hash="a" * 64,
        reserve_bytes=kwargs.pop("reserve_bytes", 0), **kwargs)


def states():
    return {"weight": torch.tensor([[1., 2.], [3., 4.]])}, {
        "state": {0: {"step": torch.tensor(1.), "exp_avg": torch.ones(2, 2), "exp_avg_sq": torch.ones(2, 2)}},
        "param_groups": [{"params": [0], "lr": 0.001}]}


def save(s, step, *, scientific=False, terminal=False):
    model, optimizer = states()
    return s.save(model, optimizer, step=step, token_step=step * 32,
        scheduler_state={"last_epoch": step, "actual_lr_vector": [0.1, 0.05]},
        rng_state=cp.capture_rng(), metadata={"rows_sha256": "b" * 64},
        scientific=scientific, terminal=terminal)


def ack(s, manifest):
    return s.mark_backup(manifest, {name: dict(sha256=r["sha256"], bytes=r["bytes"], verified_local=True)
                                  for name, r in manifest["files"].items()})


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.tmp_path = Path(temporary.name)
        case = self
        class MonkeyPatch:
            def setattr(self, obj, name, value):
                active = patch.object(obj, name, value)
                active.start()
                case.addCleanup(active.stop)
        self.monkeypatch = MonkeyPatch()

    def test_roundtrip_and_shared_model_identity(self):
        tmp_path = self.tmp_path
        monkeypatch = self.monkeypatch
        s = store(tmp_path)
        manifest = save(s, 16)
        loaded = s.load_latest()
        assert cp._same(loaded["model_state"], states()[0])
        assert cp._same(loaded["optimizer_state"], states()[1])
        assert loaded["step"] == 16 and loaded["token_step"] == 512
        assert loaded["scheduler_state"]["last_epoch"] == 16
        assert set(loaded["rng_state"]) == {"python", "numpy", "torch", "cuda"}
        assert len(list((tmp_path / "a").rglob("model.pt"))) + len(list((tmp_path / "b").rglob("model.pt"))) == 1
        assert str(tmp_path) not in json.dumps(manifest)
        assert s.latest_manifest() == manifest


    def test_exact_optimizer_scheduler_and_all_cpu_rng_resume(self):
        tmp_path = self.tmp_path
        monkeypatch = self.monkeypatch
        def setup():
            random.seed(31); np.random.seed(32); torch.manual_seed(33)
            model = torch.nn.Linear(3, 2)
            optimizer = torch.optim.AdamW(model.parameters(), lr=0.01, foreach=False)
            scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=1, gamma=0.9)
            return model, optimizer, scheduler

        def advance(model, optimizer, scheduler, count):
            for _ in range(count):
                optimizer.zero_grad(set_to_none=True)
                x = torch.randn(4, 3) + random.random() + float(np.random.random())
                model(x).square().mean().backward()
                optimizer.step(); scheduler.step()

        reference, reference_opt, reference_lr = setup()
        advance(reference, reference_opt, reference_lr, 4)
        expected_rng = cp.capture_rng()
        interrupted, opt, lr = setup()
        advance(interrupted, opt, lr, 2)
        s = store(tmp_path)
        s.save(interrupted.state_dict(), opt.state_dict(), step=2, token_step=64,
               scheduler_state=lr.state_dict(), rng_state=cp.capture_rng())
        # Recreate objects as in a fresh process; construction deliberately perturbs RNG.
        resumed = torch.nn.Linear(3, 2)
        opt2 = torch.optim.AdamW(resumed.parameters(), lr=99, foreach=False)
        lr2 = torch.optim.lr_scheduler.StepLR(opt2, step_size=8)
        loaded = s.load_latest()
        resumed.load_state_dict(loaded["model_state"], strict=True)
        opt2.load_state_dict(loaded["optimizer_state"])
        lr2.load_state_dict(loaded["scheduler_state"])
        cp.restore_rng(loaded["rng_state"])
        advance(resumed, opt2, lr2, 2)
        assert cp._same(reference.state_dict(), resumed.state_dict())
        assert cp._same(reference_opt.state_dict(), opt2.state_dict())
        assert cp._same(reference_lr.state_dict(), lr2.state_dict())
        assert cp._same(expected_rng, cp.capture_rng())


    def test_failure_before_pointer_preserves_old_recovery(self):
        tmp_path = self.tmp_path
        monkeypatch = self.monkeypatch
        s = store(tmp_path)
        first = save(s, 16)
        pointer = (s.control / "latest.json").read_bytes()
        def fail(_):
            raise RuntimeError("simulated power failure before pointer commit")
        monkeypatch.setattr(s, "_before_publish", fail)
        with self.assertRaisesRegex(RuntimeError, "power failure"):
            save(s, 32)
        assert (s.control / "latest.json").read_bytes() == pointer
        assert s.load_latest()["step"] == 16
        assert all(s._path(r).is_file() for r in first["files"].values())


    def test_verified_rolling_prunes_only_own_previous_components(self):
        tmp_path = self.tmp_path
        monkeypatch = self.monkeypatch
        s = store(tmp_path)
        first = save(s, 16)
        unrelated = tmp_path / "a" / "unrelated_scientific.pt"
        unrelated.write_bytes(b"keep me")
        second = save(s, 32)
        assert not any(s._path(r).exists() for r in first["files"].values())
        assert all(s._path(r).is_file() for r in second["files"].values())
        assert unrelated.read_bytes() == b"keep me"
        assert s._manifest(first) == first  # Compact hashes survive deletion.


    def test_scientific64_weights_retained_until_explicit_verified_prune(self):
        tmp_path = self.tmp_path
        monkeypatch = self.monkeypatch
        s = store(tmp_path)
        midpoint = save(s, 64, scientific=True)
        midpoint_ack = ack(s, midpoint)
        with self.assertRaisesRegex(ValueError, "current active"):
            s.prune_scientific_temp(midpoint, midpoint_ack, evaluation_complete=True)
        save(s, 80)
        assert s._path(midpoint["files"]["model"]).exists()
        with self.assertRaisesRegex(ValueError, "evaluated"):
            s.prune_scientific_temp(midpoint, midpoint_ack)
        assert s.prune_scientific_temp(midpoint, midpoint_ack, evaluation_complete=True) == ["model"]
        assert s._manifest(midpoint)["files"]["model"]["sha256"]


    def test_step128_can_supersede_evaluated64_without_network_ack(self):
        tmp_path = self.tmp_path
        monkeypatch = self.monkeypatch
        s = store(tmp_path)
        midpoint = save(s, 64, scientific=True)
        final = save(s, 128, scientific=True, terminal=True)
        assert s.prune_scientific_temp(midpoint, evaluation_complete=True) == ["model"]
        assert s._path(final["files"]["model"]).exists()


    def test_terminal_optimizer_requires_complete_local_ack_and_keeps_weights(self):
        tmp_path = self.tmp_path
        monkeypatch = self.monkeypatch
        s = store(tmp_path)
        final = save(s, 128, scientific=True, terminal=True)
        with self.assertRaisesRegex(ValueError, "ACK"):
            s.prune_terminal_optimizer(final, None)
        with self.assertRaisesRegex(ValueError, "Complete"):
            s.mark_backup(final, {"model": final["files"]["model"]})
        with self.assertRaisesRegex(ValueError, "receipt"):
            s.mark_backup(final, {name: dict(r, verified_local=False) for name, r in final["files"].items()})
        receipt = ack(s, final)
        assert s.prune_terminal_optimizer(final, receipt) == ["training"]
        assert s._path(final["files"]["model"]).is_file()
        assert not s._path(final["files"]["training"]).exists()
        assert s.prune_terminal_optimizer(final, receipt) == []
        with self.assertRaisesRegex(ValueError, "missing"):
            s.load_latest()
        with self.assertRaisesRegex(ValueError, "terminal"):
            save(s, 129)


    def test_identity_hash_and_rewind_are_rejected(self):
        tmp_path = self.tmp_path
        monkeypatch = self.monkeypatch
        s = store(tmp_path)
        save(s, 16)
        with self.assertRaisesRegex(ValueError, "overwrite"):
            save(s, 16)
        with self.assertRaisesRegex(ValueError, "identity"):
            cp.CheckpointStore(s.control, s.roots, phase="public_math_pilot_v1", arm="SFT", config_hash="c" * 64)
        with self.assertRaisesRegex(ValueError, "FP32"):
            s.save({"weight": torch.ones(2).bfloat16()}, {}, step=32, token_step=1024,
                   scheduler_state={}, rng_state=cp.capture_rng())


    def test_hash_tamper_prevents_restore_and_cleanup(self):
        tmp_path = self.tmp_path
        monkeypatch = self.monkeypatch
        s = store(tmp_path)
        first = save(s, 16)
        p = s._path(first["files"]["model"])
        p.write_bytes(p.read_bytes() + b"bad")
        with self.assertRaisesRegex(ValueError, "hash"):
            s.load_latest()
        with self.assertRaisesRegex(ValueError, "hash"):
            s._delete_files(first, ["model", "training"], reason="test")
        assert s._path(first["files"]["training"]).exists()


    def test_path_traversal_symlink_and_foreign_manifest_never_deleted(self):
        tmp_path = self.tmp_path
        monkeypatch = self.monkeypatch
        s = store(tmp_path)
        first = save(s, 16)
        foreign = tmp_path / "outside.pt"
        foreign.write_bytes(b"outside")
        record = dict(first["files"]["model"], path="../outside.pt")
        with self.assertRaisesRegex(ValueError, "outside"):
            s._path(record)
        changed = copy.deepcopy(first)
        changed["files"]["model"]["path"] = "../outside.pt"
        with self.assertRaisesRegex(ValueError, "manifest"):
            s._delete_files(changed, ["model"], reason="test")
        path = s._path(first["files"]["model"])
        path.unlink(); path.symlink_to(foreign)
        with self.assertRaisesRegex(ValueError, "Symlinked"):
            s._delete_files(first, ["model"], reason="test")
        assert foreign.read_bytes() == b"outside"


    def test_each_device_reserve_and_shared_device_aggregate(self):
        tmp_path = self.tmp_path
        monkeypatch = self.monkeypatch
        s = store(tmp_path, reserve_bytes=100)
        monkeypatch.setattr(cp.shutil, "disk_usage", lambda _: SimpleNamespace(free=1000))
        # Both temp dirs use one filesystem, so its free bytes cannot be counted twice.
        with self.assertRaisesRegex(OSError, "space"):
            s._placement([500, 500])
        assert len(s._placement([400, 400])) == 2
        with self.assertRaisesRegex(OSError, "space"):
            save(s, 16)
        assert s.latest_manifest() is None


    def test_unowned_directory_and_symlink_namespace_rejected(self):
        tmp_path = self.tmp_path
        monkeypatch = self.monkeypatch
        (tmp_path / "control").mkdir()
        (tmp_path / "control" / "old_scientific.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "unowned"):
            store(tmp_path)

    def test_two_filesystems_place_components_separately_when_needed(self):
        s = store(self.tmp_path, reserve_bytes=100)
        original_stat = Path.stat
        def fake_stat(path, *args, **kwargs):
            if path in s.roots:
                return SimpleNamespace(st_dev=s.roots.index(path) + 101)
            return original_stat(path, *args, **kwargs)
        with patch.object(Path, "stat", fake_stat), patch.object(cp.shutil, "disk_usage", lambda _: SimpleNamespace(free=1000)):
            placement = s._placement([800, 800])
            self.assertEqual(set(placement), {0, 1})
            with self.assertRaisesRegex(OSError, "space"):
                s._placement([901, 800])

    def test_engineering_discard_retains_receipt_without_full_backup(self):
        s = cp.CheckpointStore(self.tmp_path / "control", [self.tmp_path / "a", self.tmp_path / "b"],
            phase="public_math_pilot_v1_engineering", arm="SFT-smoke", config_hash="a" * 64, reserve_bytes=0)
        model, optimizer = states()
        manifest = s.save(model, optimizer, step=1, token_step=32, scheduler_state={}, rng_state=cp.capture_rng(),
                          metadata=dict(formal=False, discard_before_main=True))
        loaded = s.load_latest()
        receipt = dict(checkpoint=manifest, step=loaded["step"], token_step=loaded["token_step"], formal=False)
        with self.assertRaisesRegex(ValueError, "round-trip"):
            s.discard_engineering(manifest, roundtrip_receipt=receipt)
        receipt["roundtrip_verified"] = True
        self.assertEqual(s.discard_engineering(manifest, roundtrip_receipt=receipt), ["model", "training"])
        self.assertTrue(list(s.control.glob("engineering_discard_*.json")))
        self.assertTrue(s._manifest_path(manifest["checkpoint_id"]).is_file())
        self.assertEqual(s.discard_engineering(manifest, roundtrip_receipt=receipt), [])

    def test_engineering_discard_cannot_delete_formal_run(self):
        s = store(self.tmp_path)
        manifest = save(s, 16)
        with self.assertRaisesRegex(ValueError, "engineering"):
            s.discard_engineering(manifest, roundtrip_receipt={})
        self.assertTrue(all(s._path(record).exists() for record in manifest["files"].values()))


    def test_foreign_backup_ack_and_non64_scientific_prune_rejected(self):
        tmp_path = self.tmp_path
        monkeypatch = self.monkeypatch
        s = store(tmp_path)
        final = save(s, 128, scientific=True, terminal=True)
        receipt = ack(s, final)
        bad = copy.deepcopy(receipt)
        bad["identity"]["arm"] = "DFT"
        with self.assertRaisesRegex(ValueError, "ACK"):
            s.prune_terminal_optimizer(final, bad)
        with self.assertRaisesRegex(ValueError, "step64"):
            s.prune_scientific_temp(final, receipt, evaluation_complete=True)

if __name__ == "__main__":
    unittest.main()
