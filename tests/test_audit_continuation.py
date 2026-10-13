import copy
from pathlib import Path
import tempfile
import unittest

from experiments.sft_allocation_midpoint.common import dump, sha, manifest, digest
from experiments.sft_allocation_acquisition.audit_continuation import expected_roster, validate_partition, verify_carried


class ContinuationProofTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.spec = dict(campaign_id='original', inputs_manifest=dict(acquisition_audits={
            cell: dict(campaign='procurement-recovery' if cell == 'breadth_p4' else 'procurement')
            for cell in ('breadth_p0', 'depth_p0', 'breadth_p4', 'depth_p4')}))
        self.roster = expected_roster(self.spec)
        label = 'breadth_p0_s17'
        folder = self.root / 'original' / label
        folder.mkdir(parents=True)
        dump(folder / 'result.json', dict(status='completed', correct=963))
        checkpoint = folder / 'checkpoint_0256'
        checkpoint.mkdir()
        (checkpoint / 'state.pt').write_bytes(b'opaque-parent-verified-state')
        cm = dict(sha256=sha(checkpoint / 'state.pt'), bytes=(checkpoint / 'state.pt').stat().st_size)
        dump(checkpoint / 'manifest.json', cm)
        files = manifest(folder)
        dump(folder / 'artifact_manifest.json', files)
        self.terminal = dict(status='completed', evidence_sha256=digest(files))
        self.record = dict(source_campaign='original', files_verified=len(files), manifest_digest=digest(files),
                           terminal=self.terminal, checkpoints={'checkpoint_0256': cm}, result=dict(status='completed', correct=963))
        self.parent = self.root / 'original' / 'audit'
        dump(self.parent / 'intent.json', dict(source='pinned-original-audit'))
        dump(self.parent / (label + '.json'), self.record)
        p = self.parent / (label + '.json')
        self.binding = dict(roster=self.roster, carried={label: dict(bytes=p.stat().st_size, sha256=sha(p))},
                            remaining=sorted(set(self.roster) - {label}), max_seconds=3300, parallel_readers=2,
                            original_deadline_epoch=10000,
                            plan=dict(deadline_epoch=10000, slots={'audit_remaining': dict(reserved_cents=300)}),
                            parent=dict(campaign='original', run='audit', provider=dict(state='stopped'), containers=[],
                                        terminal_status='interrupted', intent_file_sha256=sha(self.parent / 'intent.json')))

    def getter(self, campaign, run):
        self.assertEqual((campaign, run), ('original', 'breadth_p0_s17'))
        return self.terminal

    def test_valid_saved_parent_proof_is_carried(self):
        self.assertEqual(verify_carried(self.root, self.binding, self.spec, self.getter), {'breadth_p0_s17': self.record})

    def test_completed_or_active_parent_is_rejected(self):
        for key, value in [('terminal_status', 'completed'), ('containers', [{}]), ('provider', dict(state='ephemeral'))]:
            b = copy.deepcopy(self.binding); b['parent'][key] = value
            with self.assertRaises(ValueError): validate_partition(b, self.spec)

    def test_cannot_drop_duplicate_or_replay_a_label(self):
        for remaining in [self.binding['remaining'][1:], self.binding['remaining'] + ['breadth_p0_s17'],
                          self.binding['remaining'] + self.binding['remaining'][:1]]:
            b = copy.deepcopy(self.binding); b['remaining'] = remaining
            with self.assertRaises(ValueError): validate_partition(b, self.spec)

    def test_original_failed_procurement_mapping_cannot_replace_recovery(self):
        b = copy.deepcopy(self.binding); b['roster']['breadth_p4']['campaign'] = 'procurement'
        with self.assertRaises(ValueError): validate_partition(b, self.spec)

    def test_cannot_extend_deadline_or_add_slots(self):
        b = copy.deepcopy(self.binding); b['plan']['deadline_epoch'] += 1
        with self.assertRaises(ValueError): validate_partition(b, self.spec)
        b = copy.deepcopy(self.binding); b['plan']['slots']['extra'] = dict(reserved_cents=300)
        with self.assertRaises(ValueError): validate_partition(b, self.spec)

    def test_rehashed_missing_checkpoint_proof_is_rejected(self):
        p = self.parent / 'breadth_p0_s17.json'
        record = copy.deepcopy(self.record); record['checkpoints'] = {}
        p.write_text(__import__('json').dumps(record))
        b = copy.deepcopy(self.binding); b['carried']['breadth_p0_s17'] = dict(bytes=p.stat().st_size, sha256=sha(p))
        with self.assertRaises(ValueError): verify_carried(self.root, b, self.spec, self.getter)

    def test_changed_parent_bytes_are_rejected(self):
        with (self.parent / 'breadth_p0_s17.json').open('a') as f: f.write(' ')
        with self.assertRaises(ValueError): verify_carried(self.root, self.binding, self.spec, self.getter)

    def test_foreign_source_terminal_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_carried(self.root, self.binding, self.spec, lambda *_: dict(status='completed', evidence_sha256='0' * 64))


if __name__ == '__main__':
    unittest.main()
