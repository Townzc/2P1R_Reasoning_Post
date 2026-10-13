"""New synthetic archive tests; never invoke old raw/model/oracle work."""
import copy
from pathlib import Path
import tempfile
import unittest
from experiments.sft_allocation_midpoint.common import dump, digest, manifest
from experiments.sft_allocation_p008.evidence_bundle import pack
from experiments.sft_allocation_p008.audit_continued_pool import (
    verify_failed_parent, verify_completed_child, CONTAINERS)
from experiments.sft_allocation_p008.pool_lineage import PARENT_CAMPAIGN, CHILD_CAMPAIGN, CHILD_RUN


class ContinuedIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def parent(self):
        src = self.root / 'parent'; src.mkdir()
        cfg = dict(run_id='pool_d2', role='pool')
        plan = dict(campaign_id=PARENT_CAMPAIGN)
        claim = dict(plan_sha256=digest(plan), intent_sha256='a' * 64)
        dump(src / 'intent.json', dict(config=cfg, plan=plan, release=dict(commit='1' * 40)))
        dump(src / 'failure.json', dict(error='TimeoutError'))
        original = manifest(src)
        terminal = dict(status='failed', evidence_sha256=digest(original), claim_sha256=digest(claim))
        dump(src / 'failure_manifest.json', original)
        preserved = manifest(src)
        pack(src)
        label = dict(campaign=PARENT_CAMPAIGN, run_id='pool_d2', config=cfg,
            claim=claim, terminal=terminal, preserved_manifest=preserved,
            archive_files={k:v for k,v in manifest(src).items() if k in CONTAINERS},
            reconciliation=dict(passed=True, parent_claim=claim, parent_terminal=terminal,
                parent_source_commit='1' * 40, physical_attempts=3992, physical_raw_unknown=0,
                all_raw_independently_redecoded=True, all_wallet_prefixes_replayed=True))
        return src, label

    def child(self):
        src = self.root / 'child'; src.mkdir()
        cfg = dict(run_id=CHILD_RUN, role='pool_continuation')
        plan = dict(campaign_id=CHILD_CAMPAIGN)
        claim = dict(plan_sha256=digest(plan), intent_sha256='b' * 64)
        result = dict(original_parent_status='failed', cumulative_parent_plus_child=True,
            physical_outputs=4008, child_physical_outputs=16, returned_tokens=1200000, wallets={'x': 1})
        dump(src / 'intent.json', dict(config=cfg, plan=plan))
        dump(src / 'result.json', result)
        pack(src); files = manifest(src); dump(src / 'artifact_manifest.json', files)
        terminal = dict(status='completed', evidence_sha256=digest(files), claim_sha256=digest(claim))
        oracle = dict(passed=True, manifest_digest=digest(files), child_terminal=terminal,
            parent_status='failed', child_status='completed', parent_physical_outputs=3992,
            parent_plus_child_redecoded=True, all_raw_redecoded=True, all_wallets_replayed=True,
            physical_outputs=4008, child_physical_outputs=16, returned_tokens=1200000, wallets={'x':1})
        label = dict(campaign=CHILD_CAMPAIGN, run_id=CHILD_RUN, config=cfg, claim=claim,
            envelope=dict(receipt=terminal, artifact_manifest=files, result=result), local_oracle=oracle)
        return src, label

    def test_failed_parent_stays_failed(self):
        src, label = self.parent()
        proof = verify_failed_parent(src, self.root/'out', label)
        self.assertEqual(proof['original_status'], 'failed')
        self.assertFalse(proof['raw_rescoring'])

    def test_parent_relabel_rejected(self):
        src, label = self.parent(); label = copy.deepcopy(label)
        label['terminal']['status'] = 'completed'
        with self.assertRaises(ValueError): verify_failed_parent(src, self.root/'out', label)

    def test_parent_extra_file_rehashed_archive_rejected(self):
        src, label = self.parent()
        for n in CONTAINERS: (src/n).unlink()
        dump(src/'injected.json', {'fake': True})
        label['preserved_manifest'] = manifest(src); pack(src)
        label['archive_files'] = {k:v for k,v in manifest(src).items() if k in CONTAINERS}
        with self.assertRaises(ValueError): verify_failed_parent(src, self.root/'out', label)

    def test_parent_unknown_rejected(self):
        src, label = self.parent(); label['reconciliation']['physical_raw_unknown'] = 1
        with self.assertRaises(ValueError): verify_failed_parent(src, self.root/'out', label)

    def test_parent_modified_original_rehashed_archive_rejected(self):
        src, label = self.parent()
        for n in CONTAINERS: (src/n).unlink()
        (src/'failure.json').unlink()  # Deliberate corruption of a synthetic fixture only.
        dump(src/'failure.json', {'error': 'different'})
        label['preserved_manifest'] = manifest(src); pack(src)
        label['archive_files'] = {k:v for k,v in manifest(src).items() if k in CONTAINERS}
        with self.assertRaises(ValueError): verify_failed_parent(src, self.root/'out', label)

    def test_child_complete_merged_oracle_bound(self):
        src, label = self.child()
        proof = verify_completed_child(src, self.root/'out', label)
        self.assertEqual(proof['role'], 'pool_continuation')
        self.assertEqual(proof['new_model_calls'], 0)

    def test_child_cumulative_as_new_rejected(self):
        src, label = self.child(); label['local_oracle']['child_physical_outputs'] = 4008
        with self.assertRaises(ValueError): verify_completed_child(src, self.root/'out', label)

    def test_child_parent_not_redecoded_rejected(self):
        src, label = self.child(); label['local_oracle']['parent_plus_child_redecoded'] = False
        with self.assertRaises(ValueError): verify_completed_child(src, self.root/'out', label)

    def test_child_changed_claim_rejected(self):
        src, label = self.child(); label['claim']['intent_sha256'] = 'c' * 64
        with self.assertRaises(ValueError): verify_completed_child(src, self.root/'out', label)

    def test_copy_deadline_callback_enforced(self):
        src, label = self.child()
        def stop(): raise TimeoutError('finite CPU limit')
        with self.assertRaises(TimeoutError): verify_completed_child(src, self.root/'out', label, stop)


if __name__ == '__main__': unittest.main()
