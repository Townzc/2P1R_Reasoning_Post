import hashlib
import json
import random
import unittest
from unittest import mock

from src.path_family_matching import FAMILIES, find_supported_keys
from src.path_family_matching_complete import record_reference
import src.path_family_matching_compact as compact
from src.path_family_matching_compact import compact_key_bytes, compact_supported_key_join
from tests.test_path_family_matching import SI, SN, row, simple_block, simple_problem


def decode(result, line):
    catalog = result['catalog']
    si = tuple(catalog['structure_ids'][i] for i in catalog['identity_tuples'][line[0]])
    sn = tuple(catalog['structure_ids'][i] for i in catalog['nonidentity_tuples'][line[1]])
    support = {catalog['problem_ids'][pi]: length for pi, length in catalog['length_signatures'][line[2]]}
    return (si, sn), support


class CompactJoinTests(unittest.TestCase):
    def compare(self, records):
        naive = find_supported_keys(records, max_key_pair_checks=1_000_000,
                                    max_structure_nodes=1_000_000, clock=lambda: 0.0)
        self.assertTrue(naive['complete'])
        stream = []
        result = compact_supported_key_join(records, on_key=stream.append, clock=lambda: 0.0)
        self.assertTrue(result['complete'])
        self.assertTrue(result['ac_to_structure_functionality_verified'])
        actual = dict(decode(result, key) for key in stream)
        expected = {(tuple(key['identity_structures']), tuple(key['nonidentity_structures'])):
                    {pid: witness['n_supervised'] for pid, witness in key['witnesses'].items()}
                    for key in naive['keys']}
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), len(stream))
        self.assertEqual(result['valid_key_count'], len(stream))
        self.assertEqual(result['represented_pairs'], result['total_candidate_pairs'])
        self.assertEqual(result['pruned_pairs'] + result['exact_pairs'], result['total_candidate_pairs'])
        self.assertEqual(result['exact_pairs'], naive['counters']['raw_key_pairs_support_at_least_four'])
        self.assertEqual(result['total_candidate_pairs'], naive['counters']['key_pair_checks'])
        self.assertEqual(result['key_stream_sha256'],
                         hashlib.sha256(b''.join(compact_key_bytes(key) for key in stream)).hexdigest())
        refs = {record_reference(record): record for record in records}
        for group in result['support_groups']:
            key = group['representative_key']
            si, sn = tuple(key['identity_structures']), tuple(key['nonidentity_structures'])
            candidates = [signature for signature, support in actual.items() if sorted(support) == group['problem_ids']]
            self.assertEqual((si, sn), min(candidates))
            self.assertEqual(group['valid_key_count'], len(candidates))
            for pid, witness in key['witnesses'].items():
                self.assertEqual(len({s['ac_class'] for s in witness['slots']}), 8)
                for slot in witness['slots']:
                    record = refs[slot['record_ref']]
                    self.assertEqual(record['problem_id'], pid)
                    self.assertEqual(record['n_supervised'], witness['n_supervised'])
        return result, stream

    def test_variable_common_lengths_and_reference_catalog(self):
        records = simple_block() + simple_problem('p0', 30) + simple_problem('p0', 10)[:-1]
        result, stream = self.compare(records)
        self.assertEqual(decode(result, stream[0])[1], {f'p{p}': 20 + p for p in range(4)})
        self.assertEqual(len(stream[0]), 3)
        self.assertTrue(all(type(value) is int for value in stream[0]))

    def test_same_class_in_both_families_cannot_fill_two_shared_structure_slots(self):
        records = [row(f'p{p}', 20, family, structure, structure)
                   for p in range(4) for family in FAMILIES for structure in SI]
        result, stream = self.compare(records)
        self.assertEqual(stream, [])
        records += [row(f'p{p}', 20, FAMILIES[1], structure, 'alt:' + structure)
                    for p in range(4) for structure in SI]
        result, stream = self.compare(records)
        self.assertEqual(len(stream), 1)

    def test_cross_length_false_support_is_excluded(self):
        records = simple_block()
        for record in records:
            if record['family'] == FAMILIES[1]:
                record['n_supervised'] += 100
        result, stream = self.compare(records)
        self.assertEqual(result['exact_pairs'], 1)
        self.assertEqual(stream, [])

    def test_one_problem_with_four_lengths_is_not_four_problems(self):
        result, stream = self.compare([r for length in range(20, 24) for r in simple_problem('p0', length)])
        self.assertEqual(result['total_candidate_pairs'], 0)

    def test_disjoint_mask_group_product_counts_all_pruned_pairs(self):
        records = [row(f'p{p}', 20, FAMILIES[0], structure, structure)
                   for p in range(4) for structure in 'abcde']
        records += [row(f'p{p}', 20, FAMILIES[1], structure, structure)
                    for p in range(4, 8) for structure in 'uvwxy']
        result, _ = self.compare(records)
        self.assertEqual(result['pruned_pairs'], 25)
        self.assertEqual(result['exact_pairs'], 0)

    def test_full_small_grids_with_overlap_match_naive(self):
        for seed in range(10):
            rng = random.Random(seed)
            records = simple_block(si=tuple('abcd'), sn=tuple('bcde'))
            for p in range(6):
                for length in (20, 21):
                    for family in FAMILIES:
                        for structure in 'abcde':
                            if rng.random() < .6:
                                records.append(row(f'p{p}', length, family, structure, f'{family}:{structure}'))
                                if rng.random() < .5:
                                    records.append(row(f'p{p}', length, family, structure, f'shared:{structure}'))
            self.compare(records)

    def test_exact_support_groups_keep_counts_and_lex_minimum(self):
        records = simple_block(si=tuple('abcde'), sn=tuple('vwxyz')) + simple_problem('p4', 31)
        result, stream = self.compare(records)
        self.assertEqual(len(stream), 25)
        self.assertEqual(result['support_group_count'], 2)
        self.assertEqual(sorted(g['valid_key_count'] for g in result['support_groups']), [1, 24])

    def test_input_order_does_not_change_ids_hashes_or_representatives(self):
        records = simple_block(si=tuple('abcde'))
        records += [{**records[0], 'response': 'z'}, {**records[0], 'response': 'a'}]
        shuffled = list(records)
        random.Random(919).shuffle(shuffled)
        a, stream_a = self.compare(records)
        b, stream_b = self.compare(shuffled)
        self.assertEqual(a, b)
        self.assertEqual(stream_a, stream_b)

    def test_nonfunctional_ac_structure_relation_fails_closed(self):
        records = simple_block()
        records[0]['ac_class'] = records[1]['ac_class']
        with self.assertRaisesRegex(ValueError, 'multiple structures'):
            compact_supported_key_join(records)

    def test_deadline_after_output_preserves_committed_pair_once(self):
        now, stream = [0.0], []
        def write(key):
            stream.append(key)
            now[0] = 600.0
        result = compact_supported_key_join(simple_block(si=tuple('abcde')), on_key=write, clock=lambda: now[0])
        self.assertFalse(result['complete'])
        self.assertEqual(result['valid_key_count'], 1)
        self.assertEqual(result['exact_pairs'], 1)
        self.assertEqual(result['represented_pairs'], 1)
        self.assertEqual(result['unrepresented_pairs'], 4)
        self.assertFalse(result['representatives_complete'])
        self.assertIsNone(result['support_groups'][0]['representative_key'])
        self.assertEqual(result['key_stream_sha256'], hashlib.sha256(compact_key_bytes(stream[0])).hexdigest())

    def test_representative_crosscheck_failure_is_not_complete(self):
        with mock.patch.object(compact, '_slot_assignment', return_value=None):
            with self.assertRaisesRegex(ValueError, 'contradicts'):
                compact_supported_key_join(simple_block(), clock=lambda: 0.0)

    def test_deadline_during_initial_index_has_no_claimed_grid(self):
        times = iter([0.0, 600.0, 600.0])
        result = compact_supported_key_join(simple_block(), clock=lambda: next(times))
        self.assertFalse(result['complete'])
        self.assertEqual(result['stop_stage'], 'indexing')
        self.assertIsNone(result['total_candidate_pairs'])

    def test_encoding_validation_empty_inventory_and_callback_error(self):
        self.assertEqual(compact_key_bytes([1, 2, 30]), b'[1,2,30]\n')
        self.assertEqual(json.loads(compact_key_bytes([1, 2, 30])), [1, 2, 30])
        for values in ([1, 2], [1, True, 3], [1, -2, 3]):
            with self.assertRaises(ValueError):
                compact_key_bytes(values)
        self.compare([])
        def fail(key):
            raise OSError('synthetic callback failure')
        with self.assertRaises(OSError):
            compact_supported_key_join(simple_block(), on_key=fail, clock=lambda: 0.0)
        for seconds in (0, -1, True, float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                compact_supported_key_join([], max_seconds=seconds)


if __name__ == '__main__':
    unittest.main()
