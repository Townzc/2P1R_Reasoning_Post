"""Small synthetic producer/verifier integration and adversarial completeness tests.

The verifier imports no production matcher. These fixtures alone call production
to build a candidate receipt, then independently audit or deliberately corrupt it.
No real C013 inventory/search is run by this test module.
"""
import base64
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import verify_compact_join as verify
from src.path_family_matching_compact import compact_supported_key_join
from tests.test_path_family_matching import FAMILIES, SI, row, simple_block, simple_problem, brute_keys


class CompactVerifierTest(unittest.TestCase):
    def fixture(self, rows=None):
        rows = simple_block(si=tuple('abcde'), sn=tuple('vwxyz')) if rows is None else rows
        keys = []
        result = compact_supported_key_join(rows, on_key=keys.append, clock=lambda: 0.0)
        catalog, groups = result.pop('catalog'), result.pop('support_groups')
        return rows, catalog, result, groups, keys

    def stream(self, keys):
        raw = b''.join(f'[{a},{b},{c}]\n'.encode() for a, b, c in keys)
        return io.BytesIO(gzip.compress(raw, mtime=0)), hashlib.sha256(raw).hexdigest()

    def checked(self, fixture):
        rows, catalog, join, groups, keys = fixture
        stream, _ = self.stream(keys)
        return verify.verify_records(rows, catalog, join, groups, stream)

    def test_full_small_grid_matches_independent_brute_force(self):
        for rows in (simple_block(), simple_block(si=tuple('abcde'), sn=tuple('vwxyz')),
                     simple_block(si=tuple('abcd'), sn=tuple('bcde')),
                     simple_block() + simple_problem('p0', 30) + simple_problem('p0', 10)[:-1]):
            fixture = self.fixture(rows)
            result, _ = self.checked(fixture)
            self.assertTrue(result['audit_complete'])
            self.assertEqual(result['valid_key_count'], len(brute_keys(rows)))
            self.assertEqual(result['counters']['independent_pruned_pairs'] +
                             result['counters']['independent_exact_pairs'], result['total_candidate_pairs'])

    def test_hall_class_collision_and_cross_length_negative_keys_are_checked(self):
        collision = [row(f'p{p}', 20, f, s, s) for p in range(4) for f in FAMILIES for s in SI]
        for rows in (collision, [{**r, 'n_supervised': r['n_supervised'] +
                                (100 if r['family'] == FAMILIES[1] else 0)} for r in simple_block()]):
            result, _ = self.checked(self.fixture(rows))
            self.assertEqual(result['total_candidate_pairs'], 1)
            self.assertEqual(result['counters']['independent_exact_pairs'], 1)
            self.assertEqual(result['valid_key_count'], 0)

    def test_full_pruned_cartesian_domain_is_accounted(self):
        rows = [row(f'p{p}', 20, FAMILIES[0], s, s) for p in range(4) for s in 'abcde']
        rows += [row(f'p{p}', 20, FAMILIES[1], s, s) for p in range(4, 8) for s in 'uvwxy']
        result, _ = self.checked(self.fixture(rows))
        self.assertEqual(result['counters']['independent_pruned_pairs'], 25)
        self.assertEqual(result['counters']['independent_exact_pairs'], 0)

    def test_missing_positive_rehashed_and_recounted_still_fails_complete_grid(self):
        rows, catalog, join, groups, keys = self.fixture()
        keys.pop()
        join['key_stream_sha256'] = self.stream(keys)[1]
        join['valid_key_count'] -= 1
        join['counters']['valid_key_count'] -= 1
        groups[0]['valid_key_count'] -= 1
        with self.assertRaisesRegex(verify.AuditFailure, 'omitted or altered valid key'):
            self.checked((rows, catalog, join, groups, keys))

    def test_duplicate_compact_key_is_not_an_extra_valid_key(self):
        fixture = self.fixture()
        fixture[4].append(fixture[4][0])
        fixture[2]['key_stream_sha256'] = self.stream(fixture[4])[1]
        with self.assertRaisesRegex(verify.AuditFailure, 'Duplicate compact'):
            self.checked(fixture)

    def test_nonminimum_length_or_dropped_support_rejected(self):
        for mutation in ('length', 'support'):
            fixture = self.fixture(simple_block() + simple_problem('p4', 24))
            if mutation == 'length':
                fixture[1]['length_signatures'][0][0][1] += 1
            else:
                fixture[1]['length_signatures'][0].pop()
            with self.assertRaisesRegex(verify.AuditFailure, 'wrong exact support or nonminimum'):
                self.checked(fixture)

    def test_independent_tuple_domain_cannot_be_narrowed(self):
        fixture = self.fixture()
        fixture[1]['identity_tuples'].pop()
        with self.assertRaisesRegex(verify.AuditFailure, 'complete tuple domain differs'):
            self.checked(fixture)

    def test_wrong_ref_and_eight_class_requirement(self):
        for mutation in ('ref', 'class'):
            fixture = self.fixture()
            slots = fixture[3][0]['representative_key']['witnesses']['p0']['slots']
            if mutation == 'ref':
                slots[0]['record_ref'] = '0'*64
                message = 'Unresolved record_ref'
            else:
                slots[0]['ac_class'] = slots[1]['ac_class']
                message = 'eight distinct'
            with self.assertRaisesRegex(verify.AuditFailure, message):
                self.checked(fixture)

    def test_wrong_group_count_or_nonminimum_key_rejected(self):
        for mutation in ('count', 'key'):
            fixture = self.fixture()
            field = 'valid_key_count' if mutation == 'count' else 'representative_tuple_ids'
            fixture[3][0][field] = 1 if mutation == 'count' else [1, 0]
            with self.assertRaisesRegex(verify.AuditFailure, 'multiplicity|lexicographic'):
                self.checked(fixture)

    def test_nonfunctional_ac_structure_and_incomplete_producer_fail_closed(self):
        fixture = self.fixture()
        fixture[0][0]['ac_class'] = fixture[0][1]['ac_class']
        with self.assertRaisesRegex(verify.AuditFailure, 'maps to multiple structures'):
            self.checked(fixture)
        fixture = self.fixture()
        fixture[2]['complete'] = False
        with self.assertRaisesRegex(verify.AuditFailure, 'incomplete compact join'):
            self.checked(fixture)

    def test_deadline_is_not_a_successful_partial_verification(self):
        rows, catalog, join, groups, keys = self.fixture()
        calls = [0]
        def deadline():
            calls[0] += 1
            if calls[0] == 12:
                raise verify.AuditDeadline('synthetic cap', {'calls': calls[0]})
        with self.assertRaises(verify.AuditDeadline):
            verify.verify_records(rows, catalog, join, groups, self.stream(keys)[0], check=deadline)

    def packing(self, groups, index, selected=True):
        pids = groups[0]['problem_ids'][:4] if selected else []
        rep = groups[0]['representative_key']
        blocks, assignments = [], []
        if selected:
            expanded = dict(rep, problem_ids=pids, witnesses={})
            for pid in pids:
                witness = rep['witnesses'][pid]
                slots = [{**{k: v for k, v in s.items() if k != 'record_ref'},
                          'record': index['lookup'][s['record_ref']]} for s in witness['slots']]
                expanded['witnesses'][pid] = dict(witness, slots=slots)
            blocks = [{'group_id': 0, 'problem_ids': pids, 'representative': expanded}]
            assignments = [{'group_id': 0, 'problem_ids': pids, 'block_count': 1, 'representative': rep}]
        return {'input_join_complete': True, 'blocks': blocks, 'used_problem_ids': pids,
                'primal_block_count': int(selected), 'group_assignments': assignments,
                'input_group_count': len(groups), 'input_problem_count': 4, 'elementary_upper_bound': 1,
                'integer_upper_bound': 1, 'dual_upper_bound': 1.0,
                'solver_status': 0 if selected else 1, 'is_optimal': selected,
                'absolute_gap_blocks': 0 if selected else 1}

    def test_integer_packing_and_component_certificate(self):
        fixture = self.fixture(simple_block())
        _, index = self.checked(fixture)
        for selected in (True, False):
            result = verify.verify_packing(self.packing(fixture[3], index, selected), fixture[3], index)
            self.assertEqual(result['component_upper_bound'], 1)
            self.assertEqual(result['optimality_independently_certified'], selected)
        packing = self.packing(fixture[3], index)
        packing['blocks'].append(copy.deepcopy(packing['blocks'][0]))
        with self.assertRaisesRegex(verify.AuditFailure, 'repeats a problem'):
            verify.verify_packing(packing, fixture[3], index)

    def test_packing_record_and_solver_bound_tamper(self):
        fixture = self.fixture(simple_block())
        _, index = self.checked(fixture)
        for mutation in ('record', 'bound', 'fractional'):
            packing = self.packing(fixture[3], index)
            if mutation == 'record':
                packing['blocks'][0]['representative']['witnesses']['p0']['slots'][0]['record'] = {}
                message = 'expanded witness'
            elif mutation == 'bound':
                packing['dual_upper_bound'] = .5
                message = 'dual bound inconsistent'
            else:
                packing['group_assignments'][0]['block_count'] = 1.0
                message = 'sum x = 4y'
            with self.assertRaisesRegex(verify.AuditFailure, message):
                verify.verify_packing(packing, fixture[3], index)

    def test_public_archive_fallback_is_byte_exact_without_materialization(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = b'{"synthetic": [1,2,3]}\n'
            encoded = base64.encodebytes(gzip.compress(raw, mtime=0))
            (root/'catalog.json.gz.b64').write_bytes(encoded)
            original = verify.receipt(raw)
            encoded_receipt = verify.receipt(encoded)
            archive = gzip.compress(b'[0,0,0]\n', mtime=0)
            parts = []
            for i, part in enumerate((archive[:10], archive[10:])):
                name = f'part{i}.b64'
                e = base64.encodebytes(part)
                (root/name).write_bytes(e)
                parts.append({'file': name, 'encoded_sha256': verify.receipt(e)['sha256'], 'encoded_bytes': len(e)})
            storage = {'format': 'gzip-base64-original-bytes-v1', 'files': {'catalog.json': {
                'archive_file': 'catalog.json.gz.b64', 'original_sha256': original['sha256'],
                'original_bytes': original['bytes'], 'encoded_sha256': encoded_receipt['sha256'],
                'encoded_bytes': encoded_receipt['bytes']}}, 'compact_key_archive': {
                    'original_sha256': verify.receipt(archive)['sha256'], 'original_bytes': len(archive), 'parts_in_order': parts}}
            (root/'storage.json').write_text(json.dumps(storage))
            summary = {'output_sha256': {'catalog.json': original['sha256']}, 'private_key_archive': verify.receipt(archive)}
            hashes = {}
            artifacts, parsed_storage = verify.public_artifacts(root, summary, hashes)
            self.assertEqual(artifacts['catalog.json'], json.loads(raw))
            restored = verify.key_input(root, root/'missing.gz', summary, parsed_storage, hashes)
            self.assertEqual(restored.getvalue(), archive)
            self.assertFalse((root/'catalog.json').exists())
            self.assertFalse((root/'missing.gz').exists())
            (root/'part0.b64').write_bytes(b'changed')
            with self.assertRaisesRegex(verify.AuditFailure, 'Encoded archive hash/size'):
                verify.key_input(root, None, summary, parsed_storage, {})

    def test_cli_deadline_receipt_is_incomplete_and_nonzero(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)/'audit.json'
            argv = ['verify', '--report', temporary, '--inventory', 'unused', '--out', str(out)]
            with patch('sys.argv', argv), patch.object(verify, 'audit', side_effect=verify.AuditDeadline('cap', {'stage': 'grid'})):
                with self.assertRaises(SystemExit) as caught:
                    verify.main()
            self.assertEqual(caught.exception.code, 1)
            result = json.loads(out.read_text())
            self.assertEqual(result['status'], 'incomplete')
            self.assertFalse(result['audit_complete'])


if __name__ == '__main__':
    unittest.main()
