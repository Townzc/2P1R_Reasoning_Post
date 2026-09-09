import hashlib
import gzip
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import scripts.audit_legal_support as legal_support
from scripts.audit_legal_support import (allocate_distinct_classes, audit_problem,
                                         create_output, identity_operations, json_bytes,
                                         ordered_programs, run_audit)
from src.countdown_smoke import canonical, safe_parse


class LegalSupportTests(unittest.TestCase):
    def test_exact_ordered_program_count_and_input_resources(self):
        trees = list(ordered_programs([1, 2, 3, 20]))
        self.assertEqual(len(trees), 24 * 5 * 64)
        self.assertEqual(len(set(trees)), len(trees))
        def leaves(tree):
            return [tree[1]] if tree[0] == 'n' else leaves(tree[1]) + leaves(tree[2])
        self.assertTrue(all(sorted(leaves(tree)) == [1, 2, 3, 20] for tree in trees))
        with self.assertRaises(ValueError):
            list(ordered_programs([1, 1, 3, 20]))

    def test_ac_reassociation_can_change_identity_label(self):
        a = safe_parse('((1 - 3) + 2) + 20')
        b = safe_parse('(1 - 3) + (2 + 20)')
        self.assertEqual(canonical(a), canonical(b))
        self.assertTrue(identity_operations(a)[1])
        self.assertFalse(identity_operations(b)[1])
        self.assertEqual(identity_operations(a)[1][0]['node_address'], 'root')

    def test_overlap_cannot_be_double_counted_in_two_plus_two(self):
        self.assertIsNone(allocate_distinct_classes({'a', 'b'}, {'a', 'b'}, 2))
        self.assertIsNone(allocate_distinct_classes({'a', 'b'}, {'b', 'c'}, 2))
        result = allocate_distinct_classes({'a', 'b'}, {'a', 'b', 'c', 'd'}, 2)
        self.assertIsNotNone(result)
        self.assertEqual(set(result['identity_present']), {'a', 'b'})
        self.assertEqual(set(result['identity_absent']), {'c', 'd'})

    def test_matching_agrees_with_exhaustive_small_set_assignment(self):
        universe = tuple('abcde')
        subsets = [set(x) for n in range(6) for x in itertools.combinations(universe, n)]
        for a in subsets:
            for b in subsets:
                expected = any(not set(x) & set(y) for x in itertools.combinations(a, 2)
                               for y in itertools.combinations(b, 2))
                result = allocate_distinct_classes(a, b, 2)
                self.assertEqual(result is not None, expected, (a, b))
                if result:
                    self.assertEqual(len(set(result['identity_present'] + result['identity_absent'])), 4)

    def test_four_per_family_does_not_imply_eight_distinct_classes(self):
        a = set('abcd')
        b = set('bcde')
        self.assertGreaterEqual(len(a), 4)
        self.assertGreaterEqual(len(b), 4)
        self.assertIsNone(allocate_distinct_classes(a, b, 4))
        self.assertIsNotNone(allocate_distinct_classes(set('abcd'), set('efgh'), 4))

    def test_one_toy_census_recovers_ordered_references_and_mixed_ac(self):
        texts = ['((1 - 3) + 2) + 20', '(1 - 3) + (2 + 20)']
        problem = {'problem_id': 'toy_identity_reassociation', 'numbers': [1, 2, 3, 20],
                   'target': 20, 'stored_paths': [
                       {'expression': t, 'path_id': canonical(safe_parse(t))} for t in texts]}
        summary, solutions = audit_problem(problem, retain_solutions=True)
        self.assertEqual(summary['ordered_candidates_examined'], 7680)
        self.assertGreater(summary['undefined_division_programs'], 0)
        self.assertTrue(summary['all_stored_ordered_references_recovered'])
        self.assertEqual(summary['stored_ordered_solution_matches'], 2)
        self.assertEqual(summary['stored_reference_family_counts'], {'identity_present': 1, 'identity_absent': 1})
        self.assertEqual(summary['defined_programs'], summary['wrong_target_programs'] + summary['legal_ordered_solutions'])
        self.assertEqual(summary['ordered_candidates_examined'], summary['undefined_division_programs'] + summary['defined_programs'])
        self.assertGreater(summary['mixed_ac_class_count'], 0)
        target_class = canonical(safe_parse(texts[0]))
        family_labels = {s['identity_family'] for s in solutions if s['ac_class'] == target_class}
        self.assertEqual(family_labels, {'identity_present', 'identity_absent'})
        digest = hashlib.sha256(b''.join(json_bytes(s) for s in solutions)).hexdigest()
        self.assertEqual(digest, summary['complete_solution_feature_stream_sha256'])
        self.assertEqual(len(solutions), summary['legal_ordered_solutions'])
        for witness_key, k in [('two_plus_two_witness', 2), ('four_plus_four_witness', 4)]:
            witness = summary[witness_key]
            if witness:
                rows = witness['ordered_solution_witnesses']
                self.assertEqual(len({r['ac_class'] for r in rows}), 2*k)
                self.assertEqual(sum(r['identity_family'] == 'identity_present' for r in rows), k)

    def test_existing_outputs_and_out_of_bound_resources_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'report'
            create_output(out)
            (out / 'keep.txt').write_text('original')
            with self.assertRaises(FileExistsError):
                create_output(out)
            self.assertEqual((out / 'keep.txt').read_text(), 'original')
            for kwargs in ({'workers': 3}, {'max_seconds': 601}, {'max_seconds': 0}):
                with self.assertRaises(ValueError):
                    run_audit(Path(directory), Path(directory)/'unused', **kwargs)
            self.assertFalse((Path(directory)/'unused').exists())

    def test_input_failure_is_retained_without_any_pool_or_enumeration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = run_audit(root/'missing_repository', root/'report', workers=1, max_seconds=1)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['completed']['completed_problems'], 0)
            saved = json.loads((root/'report/summary.json').read_text())
            self.assertEqual(saved['status'], 'failed')
            self.assertEqual(saved['requested_problems'], 256)
            self.assertNotIn(str(root), (root/'report/summary.json').read_text())

    def test_timeout_terminates_workers_and_retains_partial_status(self):
        # Exercise the controller without reading or enumerating real training data.
        context = mock.Mock()
        pool = context.Pool.return_value
        pool.apply_async.return_value.get.side_effect = legal_support.multiprocessing.TimeoutError()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(legal_support, 'sha256_file', return_value='mock_digest'), \
                 mock.patch.object(legal_support, 'load_training_problems', return_value=[{'problem_id': 'toy'}]), \
                 mock.patch.object(legal_support.subprocess, 'check_output', return_value='mock_commit\n'), \
                 mock.patch.object(legal_support.multiprocessing, 'get_context', return_value=context):
                result = run_audit(root, root/'report', max_seconds=1)
            self.assertEqual(result['status'], 'timed_out')
            self.assertEqual(result['pending_problem_ids'], ['toy'])
            self.assertEqual(result['completed']['completed_problems'], 0)
            pool.terminate.assert_called_once()
            pool.join.assert_called_once()
            self.assertEqual(json.loads((root/'report/summary.json').read_text())['status'], 'timed_out')

    def test_parent_archive_order_and_uncompressed_hash(self):
        # Controller-only fake results test archive plumbing, not mathematical support.
        def record(pid):
            return {'problem_id': pid, 'mixed_ac_class_count': 0,
                    'ordered_candidates_examined': 7680, 'undefined_division_programs': 0,
                    'wrong_target_programs': 7679, 'legal_ordered_solutions': 1,
                    'ordered_two_plus_two_supported': False, 'ordered_four_plus_four_supported': False,
                    'distinct_ac_two_plus_two_supported': False,
                    'each_family_has_four_ac_classes_allowing_overlap': False,
                    'distinct_ac_four_plus_four_supported': False,
                    'all_stored_ordered_references_recovered': True}
        features = [{'problem_id': 'a', 'test_feature': 1}, {'problem_id': 'b', 'test_feature': 2}]
        context = mock.Mock()
        pool = context.Pool.return_value
        jobs = [mock.Mock(), mock.Mock()]
        for i, pid in enumerate(('a', 'b')):
            jobs[i].get.return_value = (record(pid), [features[i]])
        pool.apply_async.side_effect = jobs
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root/'private/solutions.jsonl.gz'
            with mock.patch.object(legal_support, 'SOURCES', ()), \
                 mock.patch.object(legal_support, 'load_training_problems', return_value=[{'problem_id': 'a'}, {'problem_id': 'b'}]), \
                 mock.patch.object(legal_support.subprocess, 'check_output', return_value='mock_commit\n'), \
                 mock.patch.object(legal_support.multiprocessing, 'get_context', return_value=context), \
                 mock.patch('builtins.print'):
                result = run_audit(root, root/'report', max_seconds=10, solutions_out=archive)
            with gzip.open(archive, 'rb') as stream:
                raw = stream.read()
            self.assertEqual(raw, b''.join(json_bytes(x) for x in features))
            self.assertEqual(result['solution_archive_uncompressed_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(result['solution_archive_gzip_sha256'], hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertEqual(result['solution_archive_records'], 2)
            self.assertEqual(result['status'], 'completed')
            self.assertNotIn(str(root), (root/'report/summary.json').read_text())

    def test_existing_private_archive_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root/'existing.jsonl.gz'
            archive.write_bytes(b'preserve')
            with self.assertRaises(FileExistsError):
                run_audit(root, root/'new-report', solutions_out=archive)
            self.assertEqual(archive.read_bytes(), b'preserve')
            self.assertFalse((root/'new-report').exists())


if __name__ == '__main__':
    unittest.main()
