import unittest
import json
from pathlib import Path
import tempfile
import numpy as np
from analysis.p012_registered import bootstrap_delta, differences, digest, outcomes, ranks, read_endpoint, spearman, two_seed_contrast


class RegisteredAnalysisTests(unittest.TestCase):
    def test_wrong_seed_or_sampling_is_rejected_before_loading_outcomes(self):
        with tempfile.TemporaryDirectory(dir='.') as directory:
            path = Path(directory).resolve().relative_to(Path.cwd())/'generation.json'
            for seed, n in [(17,1),(29,8)]:
                path.write_text(json.dumps({'config':{'protocol':'omi2','n':n,'temperature':0,'seed':seed,'template_family':'qwen','task':'math'}}))
                spec = {'generation_manifest':{'path':str(path),'sha256':digest(path)}}
                with self.assertRaisesRegex(ValueError,'Endpoint protocol'):
                    read_endpoint(spec,5000,29,'qwen','math')

    def test_pairing_uses_ids_and_not_file_order(self):
        high = {'b': False, 'a': True}; low = {'a': False, 'b': True}
        np.testing.assert_array_equal(differences(high, low), [1, -1])

    def test_rejects_missing_duplicate_unknown_and_nonboolean_labels(self):
        valid = {'id': 'a', 'draw': 0, 'correct': True}
        for rows, ids in [([valid], ['a','b']), ([valid,valid], ['a']),
                          ([dict(valid, needs_judge=True)], ['a']),
                          ([dict(valid, correct=1)], ['a']),
                          ([dict(valid, draw=1)], ['a'])]:
            with self.assertRaises(ValueError): outcomes(rows, ids)

    def test_identical_and_uniformly_superior_models_have_exact_intervals(self):
        for value, expected in [(0, 0), (1, 100), (-1, -100)]:
            r = bootstrap_delta([value] * 4)
            self.assertEqual((r['delta_pp'], r['lower95_pp'], r['upper95_pp']), (expected,)*3)

    def test_question_bootstrap_matches_independent_small_oracle(self):
        delta = np.array([1.,-1.,0.,0.]); rng = np.random.Generator(np.random.PCG64(20261111))
        oracle = delta[rng.integers(0,4,size=(10000,4))].mean(axis=1)*100
        r = bootstrap_delta(delta)
        np.testing.assert_array_equal([r['lower95_pp'],r['upper95_pp']], np.quantile(oracle,[.025,.975]))
        self.assertEqual(r, bootstrap_delta(delta))

    def test_two_seeds_are_coupled_by_question_not_doubled_sample_size(self):
        high = {'17':{'a':True,'b':False},'29':{'b':True,'a':False}}
        low = {'17':{'b':True,'a':False},'29':{'a':True,'b':False}}
        r = two_seed_contrast(high,low)
        self.assertEqual(r['seed_mean']['n_questions'],2)
        self.assertEqual((r['seed_mean']['lower95_pp'],r['seed_mean']['upper95_pp']),(0,0))
        self.assertFalse(r['same_nonzero_direction'])

    def test_tied_ranks_constant_input_and_negative_capability_direction(self):
        np.testing.assert_array_equal(ranks([3,1,1,2]),[4,1.5,1.5,3])
        self.assertAlmostEqual(spearman([1,2,3],[3,2,1]),-1)
        self.assertIsNone(spearman([1,1,1],[1,2,3]))
        self.assertAlmostEqual(spearman([-3,-2,-1],[1,2,3]),1)


if __name__ == '__main__': unittest.main()
