"""Authored byte/string fixtures only: no model or benchmark execution."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest

from experiments.q2_supervision_migration.contracts import (
    ContractError, CollisionError, IncompleteScoring, ReplayRefused,
    SuiteVerdict, VerdictStatus, build_fresh_fork_manifest, identity_hash,
    read_records, record_sample, reserve_batch, reserve_fork,
    reward_from_verdicts, seal_batch, verify_fork_sources,
)


class Q2ContractsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.good = SuiteVerdict(VerdictStatus.PASS)
        self.bad = SuiteVerdict(VerdictStatus.FAIL, "candidate assertion failed")

    def reserve(self, **changes):
        args = dict(run_id="authored", phase_id="W-reset", batch_index=0,
                    tasks=["fixture-a", "fixture-a"], policy_sha256="a" * 64,
                    config_sha256="b" * 64)
        args.update(changes)
        return reserve_batch(self.root / "batches", **args)

    def sample(self, batch, index=0, **changes):
        args = dict(sample_index=index, completion_text="answer\n",
                    completion_token_ids=[1, 2], base=self.good, extra=self.bad,
                    finish_reason="eos")
        args.update(changes)
        return record_sample(batch, **args)

    def manifest(self, **changes):
        policy = self.root / "weights"
        tokenizer = self.root / "tokenizer"
        if not policy.exists():
            policy.write_bytes(b"tiny authored weights fixture")
            tokenizer.write_bytes(b"tiny authored tokenizer fixture")
        args = dict(run_id="authored", phase_id="W-reset",
                    policy_files={"model": policy},
                    tokenizer_files={"tokenizer": tokenizer},
                    phase_config={"learning_rate": 0.0001, "reward": "union"},
                    phase_seed=7, prompt_schedule_sha256="c" * 64)
        args.update(changes)
        return build_fresh_fork_manifest(**args)

    def test_reward_truth_table_and_no_error_short_circuit(self):
        for b in (self.good, self.bad):
            for e in (self.good, self.bad):
                self.assertEqual(reward_from_verdicts(b, e, "base"), int(b == self.good))
                self.assertEqual(reward_from_verdicts(b, e, "extra"), int(e == self.good))
                self.assertEqual(reward_from_verdicts(b, e, "union"),
                                 int(b == self.good and e == self.good))
        for status in ("scorer_error", "timeout", "missing"):
            for mode in ("base", "extra", "union"):
                with self.subTest(status=status, mode=mode):
                    with self.assertRaises(IncompleteScoring):
                        reward_from_verdicts(self.bad, SuiteVerdict(status), mode)
                    with self.assertRaises(IncompleteScoring):
                        reward_from_verdicts(SuiteVerdict(status), self.bad, mode)
        with self.assertRaises(ContractError):
            reward_from_verdicts(self.good, self.good, "gold")

    def test_full_text_tokens_unicode_and_failure_evidence_survive(self):
        batch = self.reserve()
        text = "\n\r\t'quoted'\\\x00雪" + "x" * 10000 + "\nfinal suffix\n"
        record = self.sample(batch, completion_text=text,
                             completion_token_ids=list(range(400)),
                             extra=SuiteVerdict("timeout", "unknown timeout owner"))
        self.sample(batch, 1)
        rows = read_records(seal_batch(batch))
        self.assertEqual(rows[1], record)
        self.assertEqual(rows[1]["completion_text"], text)
        self.assertEqual(rows[1]["completion_token_ids"], list(range(400)))
        self.assertEqual(rows[1]["extra"]["status"], "timeout")
        self.assertNotEqual(rows[1]["sample_id"], rows[2]["sample_id"])

    def test_batch_reservation_replay_and_changed_contract_refused(self):
        self.reserve()
        with self.assertRaises(ReplayRefused):
            self.reserve()
        with self.assertRaises(CollisionError):
            self.reserve(policy_sha256="d" * 64)

    def test_partial_directory_remains_ambiguous(self):
        key = dict(run_id="authored", phase_id="W-reset", batch_index=0)
        directory = self.root / "batches" / identity_hash(key)
        directory.mkdir(parents=True)
        with self.assertRaises(CollisionError):
            self.reserve()
        self.assertTrue(directory.exists())

    def test_concurrent_reservation_has_only_one_owner(self):
        def attempt(_):
            try:
                return self.reserve()
            except ContractError:
                return None
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(attempt, range(4)))
        self.assertEqual(sum(result is not None for result in results), 1)

    def test_duplicate_sample_overwrite_and_reseal_refused(self):
        batch = self.reserve()
        self.sample(batch)
        with self.assertRaises(ReplayRefused):
            self.sample(batch)
        with self.assertRaises(CollisionError):
            self.sample(batch, completion_text="different")
        with self.assertRaises(ContractError):
            seal_batch(batch)
        self.sample(batch, 1)
        original = seal_batch(batch).read_bytes()
        with self.assertRaises(ReplayRefused):
            seal_batch(batch)
        with self.assertRaises(ReplayRefused):
            self.sample(batch, 1)
        self.assertEqual((batch.directory / "batch.jsonl").read_bytes(), original)

    def test_tampering_partial_jsonl_and_foreign_sample_detected(self):
        batch = self.reserve()
        self.sample(batch)
        path = batch.directory / "sample_00000000.jsonl"
        path.chmod(0o600)
        path.write_bytes(path.read_bytes().replace(b"answer", b"tamper"))
        with self.assertRaises(ContractError):
            read_records(path)
        path.write_bytes(b'{"unfinished":')
        with self.assertRaises(ContractError):
            read_records(path)
        other = self.reserve(batch_index=1)
        row = self.sample(other)
        path.write_text(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        with self.assertRaises(ContractError):
            seal_batch(batch)

    def test_bad_ids_and_token_types_refused(self):
        for args in (dict(batch_index=True), dict(tasks=[]), dict(tasks="bad"),
                     dict(policy_sha256="../escape")):
            with self.subTest(args=args):
                with self.assertRaises(ContractError):
                    self.reserve(**args)
        batch = self.reserve()
        for args in (dict(sample_index=2), dict(completion_token_ids=[True]),
                     dict(completion_token_ids=[-1])):
            with self.subTest(args=args):
                with self.assertRaises(ContractError):
                    self.sample(batch, **args)

    def test_fork_hashes_real_bytes_is_path_independent_and_refuses_replay(self):
        manifest = self.manifest()
        copy = self.root / "elsewhere"
        copy.write_bytes((self.root / "weights").read_bytes())
        same = self.manifest(policy_files={"model": copy})
        self.assertEqual(manifest, same)
        reserve_fork(self.root / "forks", manifest)
        with self.assertRaises(ReplayRefused):
            reserve_fork(self.root / "forks", same)
        with self.assertRaises(CollisionError):
            reserve_fork(self.root / "forks", self.manifest(phase_seed=8))
        verify_fork_sources(manifest, policy_files={"model": copy},
                            tokenizer_files={"tokenizer": self.root / "tokenizer"})
        copy.write_bytes(b"different weights")
        with self.assertRaises(ContractError):
            verify_fork_sources(manifest, policy_files={"model": copy},
                                tokenizer_files={"tokenizer": self.root / "tokenizer"})

    def test_manifest_detaches_config_and_rejects_nonfinite_identity(self):
        config = {"nested": {"lr": 1}}
        manifest = self.manifest(phase_config=config)
        config["nested"]["lr"] = 9
        self.assertEqual(manifest["phase_config"]["nested"]["lr"], 1)
        with self.assertRaises(ContractError):
            self.manifest(phase_config={"lr": float("nan")})
        with self.assertRaises(ContractError):
            self.manifest(policy_files={})
        with self.assertRaises(ContractError):
            self.manifest(phase_config={1: "ambiguous JSON key"})
        manifest["phase_seed"] = 9
        with self.assertRaises(ContractError):
            reserve_fork(self.root / "forks", manifest)

    def test_valid_hash_does_not_authorize_old_optimizer_resume(self):
        manifest = self.manifest()
        manifest["optimizer"] = "retained"
        body = {k: v for k, v in manifest.items() if k != "record_sha256"}
        manifest["record_sha256"] = identity_hash(body)
        with self.assertRaises(ContractError):
            reserve_fork(self.root / "forks", manifest)


if __name__ == "__main__":
    unittest.main()
