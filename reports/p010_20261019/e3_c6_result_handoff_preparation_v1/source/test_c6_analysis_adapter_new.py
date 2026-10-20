"""New C6 GSM-sample and complete-table boundary fixtures; no real outcomes."""
import ast
import importlib.util
import unittest
from pathlib import Path

ROOT = Path('.local/p010_20261019/r1')


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load('c6_analysis_adapter', ROOT/'analyze_c6_complete_once.py')
paired = load('c6_new_cardinality', ROOT/'c6_paired_questions_prepared.py')


class NewC6Boundaries(unittest.TestCase):
    def fixture(self):
        ids = [f'synthetic/{i:04d}' for i in range(1319)]
        rows = [dict(problem_id=pid) for pid in ids]
        tables = {label:{pid:False for pid in ids} for label in adapter.LABELS}
        for i in range(3):
            tables[f'cue/sample{i}'][ids[0]] = True
        tables['cue/greedy'][ids[0]] = True
        return ids, rows, tables

    def test_gsm_four_samples_averaged_per_question(self):
        ids, rows, tables = self.fixture()
        order, vectors, cells = adapter.cell_vectors(tables, rows, 'base_gsm')
        self.assertEqual(order, ids)
        self.assertEqual(vectors['sampled_mean_pass_at_1']['base_gsm/cue']['question_values'][:2], [.75, 0])
        self.assertEqual(cells[1]['sampled_correct'], 3)
        self.assertEqual(cells[1]['sampled_outputs'], 5276)

    def test_missing_original_sample_rejected(self):
        _, rows, tables = self.fixture()
        del tables['cue/sample3']
        with self.assertRaises(ValueError):
            adapter.cell_vectors(tables, rows, 'base_gsm')

    def test_numeric_label_not_boolean_rejected(self):
        ids, rows, tables = self.fixture()
        tables['no_cue/sample0'][ids[0]] = 1
        with self.assertRaises(ValueError):
            adapter.cell_vectors(tables, rows, 'base_gsm')

    def test_changed_question_identity_rejected(self):
        ids, rows, tables = self.fixture()
        del tables['cue/greedy'][ids[0]]
        tables['cue/greedy']['synthetic/unmatched'] = False
        with self.assertRaises(ValueError):
            adapter.cell_vectors(tables, rows, 'base_gsm')

    def test_new_1319_checker_accepts_four_not_three(self):
        ids, rows, tables = self.fixture()
        _, vectors, _ = adapter.cell_vectors(tables, rows, 'base_gsm')
        vector = vectors['sampled_mean_pass_at_1']['base_gsm/cue']
        self.assertEqual(paired.checked_vector(vector, ids, vector['metric']).shape, (1319,))
        with self.assertRaises(ValueError):
            paired.checked_vector(dict(vector, samples_per_question=3), ids, vector['metric'])

    def test_paired_estimator_ast_exact_original(self):
        def method(file):
            tree = ast.parse(Path(file).read_text())
            return ast.dump(next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name=='paired_summary'),
                            include_attributes=False)
        self.assertEqual(method('analyses/p010_paired_questions.py'),
                         method(ROOT/'c6_paired_questions_prepared.py'))


if __name__ == '__main__':
    unittest.main()
