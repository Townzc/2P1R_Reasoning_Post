"""New proof-boundary fixtures only; no model, original oracle or remote calls."""
import copy
import tempfile
import unittest
from pathlib import Path

from experiments.sft_allocation_midpoint.common import dump, digest, sha
from experiments.sft_allocation_p008.audit_replacement_binding import FAILED_STUDENTS, CHILD_RUN
from experiments.sft_allocation_p008.audit_t8_cap_records import CAP_SPEC
from scripts.audit_p008_final_cpu import check_proof, check_journal, check_provider, CONTAINERS


def t8_fixture():
    files = {n: dict(bytes=13, sha256='a' * 64) for n in CONTAINERS}
    files.update({'checkpoint_1024/state.pt': dict(bytes=21, sha256='b' * 64),
                  'checkpoint_2048/state.pt': dict(bytes=22, sha256='c' * 64)})
    oracle = dict(state_sha256='c' * 64, forensic_checkpoints={'1024': {'sha256': 'b' * 64}})
    label = dict(campaign='p008-students-completion-20261013-r1',
                 run_id='d1_b8_p0_breadth_t8',
                 config=dict(role='main', updates=2048, training_multiple=8),
                 envelope={'artifact_manifest': files}, local_oracle=oracle,
                 t8_operational_evidence={'fixture': 'exact archived original intent'})
    proof = dict(passed=True, new_model_calls=0, campaign=label['campaign'], run_id=label['run_id'],
                 role='main', files_verified=len(files), original_artifact_digest=digest(files),
                 local_oracle_sha256=digest(oracle), checkpoint_sha256={'1024': 'b' * 64, '2048': 'c' * 64},
                 copied_bytes=sum(r['bytes'] for r in files.values()),
                 timings=dict(copy_and_sha={n: {'bytes': r['bytes'], 'seconds': .1} for n, r in files.items()},
                              complete_state_validation_seconds={'1024': .2, '2048': .3},
                              unpack_and_all_file_sha_seconds=.4, total_seconds=1.1),
                 raw_rescoring_scope='Existing independent local oracle bound, not repeated in this integrity audit',
                 effective_worker_seconds=9600, original_config_seconds=9560,
                 original_reserved_cents=1253, supplement_reserved_cents=5, total_reserved_cents=1258,
                 original_N2_passed=False, post_hoc_engineering_deviation=True,
                 cap_spec_sha256=CAP_SPEC,
                 operational_evidence_sha256=digest(label['t8_operational_evidence']))
    return label, proof


class ProofBoundaries(unittest.TestCase):
    def setUp(self):
        self.label, self.proof = t8_fixture()

    def test_complete_forensic_and_terminal_identity_pass(self):
        check_proof(self.label['run_id'], self.label, self.proof)

    def test_missing_or_substituted_state_is_rejected(self):
        for change in ('drop1024', 'swap2048'):
            with self.subTest(change=change):
                p = copy.deepcopy(self.proof)
                if change == 'drop1024':
                    del p['checkpoint_sha256']['1024']
                else:
                    p['checkpoint_sha256']['2048'] = 'd' * 64
                with self.assertRaises(ValueError):
                    check_proof(self.label['run_id'], self.label, p)

    def test_changed_oracle_binding_is_rejected(self):
        self.proof['local_oracle_sha256'] = 'e' * 64
        with self.assertRaises(ValueError):
            check_proof(self.label['run_id'], self.label, self.proof)

    def test_original_failure_cannot_be_retroactively_passed(self):
        self.proof['original_N2_passed'] = True
        with self.assertRaises(ValueError):
            check_proof(self.label['run_id'], self.label, self.proof)

    def test_supplement_cannot_be_omitted(self):
        self.proof['supplement_reserved_cents'] = 0
        with self.assertRaises(ValueError):
            check_proof(self.label['run_id'], self.label, self.proof)

    def test_nonfinite_or_underreported_copy_is_rejected(self):
        for key, value in (('seconds', float('nan')), ('bytes', 0)):
            with self.subTest(key=key):
                p = copy.deepcopy(self.proof)
                p['timings']['copy_and_sha']['checkpoint_1024/state.pt'][key] = value
                with self.assertRaises(ValueError):
                    check_proof(self.label['run_id'], self.label, p)

    def test_failed_student_remains_zero_update_failed(self):
        name = sorted(FAILED_STUDENTS)[0]
        files = {n: dict(bytes=17, sha256='a' * 64) for n in CONTAINERS}
        label = dict(campaign='original', run_id=name, terminal={'evidence_sha256': 'f' * 64},
                     preserved_manifest={'failure_manifest.json': {}}, archive_files=files)
        proof = dict(passed=True, new_model_calls=0, campaign='original', run_id=name,
                     original_status='failed', original_artifact_digest='f' * 64, files_verified=1,
                     raw_rescoring=False, attempted_updates=0, endpoint_outputs=0,
                     timings={n: {'bytes': 17, 'seconds': .1} for n in files})
        check_proof(name, label, proof)
        for field, value in (('original_status', 'completed'), ('attempted_updates', 1), ('endpoint_outputs', 1)):
            p = dict(proof, **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                check_proof(name, label, p)

    def test_child_binds_existing_merged_oracle_without_new_scoring(self):
        files = {n: dict(bytes=17, sha256='a' * 64) for n in CONTAINERS}
        label = dict(campaign='child', run_id=CHILD_RUN, config={'role': 'pool_continuation'},
                     envelope={'artifact_manifest': files}, local_oracle={'merged': 'existing'})
        proof = dict(passed=True, new_model_calls=0, campaign='child', run_id=CHILD_RUN,
                     role='pool_continuation', files_verified=3, original_artifact_digest=digest(files),
                     local_oracle_sha256=digest(label['local_oracle']), raw_rescoring=False,
                     timings={n: {'bytes': 17, 'seconds': .1} for n in files})
        check_proof(CHILD_RUN, label, proof)
        proof['raw_rescoring'] = True
        with self.assertRaises(ValueError):
            check_proof(CHILD_RUN, label, proof)

    def journal(self, root):
        name, label, proof = self.label['run_id'], self.label, self.proof
        terminal = {'status': 'completed'}
        item = dict(campaign=label['campaign'], run_id=name, terminal=terminal)
        binding = dict(plan={'campaign_id': 'cpu'}, labels={name: item})
        unit = dict(label_sha256=digest(label), campaign=item['campaign'],
                    source_run_id=name, original_terminal=terminal)
        dump(root / 'intents' / (name + '.json'), unit)
        dump(root / 'proofs' / (name + '.json'), proof)
        done = dict(proof_sha256=sha(root / 'proofs' / (name + '.json')), label_sha256=digest(label))
        dump(root / 'completed' / (name + '.json'), done)
        ledger = {'midpoint/cpu/audit/unit/' + name: unit, 'midpoint/cpu/audit/done/' + name: done}
        return binding, {name: label}, {'labels': {name: proof}}, ledger

    def test_complete_journal_matches_remote_immutable_ack(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            check_journal(root, *self.journal(root))

    def test_missing_remote_completion_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            binding, labels, result, ledger = self.journal(root)
            del ledger['midpoint/cpu/audit/done/' + self.label['run_id']]
            with self.assertRaises(ValueError):
                check_journal(root, binding, labels, result, ledger)

    def test_extra_unknown_unit_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            binding, labels, result, ledger = self.journal(root)
            ledger['midpoint/cpu/audit/unit/unknown'] = {}
            with self.assertRaises(ValueError):
                check_journal(root, binding, labels, result, ledger)

    def test_proof_byte_change_is_rejected_even_if_parsed_json_equal(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            binding, labels, result, ledger = self.journal(root)
            p = root / 'proofs' / (self.label['run_id'] + '.json')
            p.write_text(p.read_text() + '\n')
            with self.assertRaises(ValueError):
                check_journal(root, binding, labels, result, ledger)


class ProviderBoundaries(unittest.TestCase):
    def setUp(self):
        self.provider = dict(apps=[dict(app_id='ap-original', lifecycle=dict(state='stopped', stopped_at='saved-time'))],
                             owned_containers=[], other_containers=[])

    def test_original_stopped_app_is_accepted(self):
        check_provider(self.provider, 'ap-original', 'Original invocation https://modal.com/apps/ap-original')

    def test_unrelated_stopped_app_cannot_stand_in(self):
        with self.assertRaises(ValueError):
            check_provider(self.provider, 'ap-original', 'Original invocation ap-different')

    def test_unmatched_container_in_global_snapshot_is_rejected(self):
        self.provider['other_containers'] = [{'app_id': 'ap-original'}]
        with self.assertRaises(ValueError):
            check_provider(self.provider, 'ap-original', 'Original invocation ap-original')


if __name__ == '__main__':
    unittest.main()

