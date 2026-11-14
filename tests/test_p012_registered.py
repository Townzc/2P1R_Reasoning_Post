import unittest
import json
from pathlib import Path
import tempfile
import numpy as np
from analysis.p012_registered import DATA_SHA, MODELS, bootstrap_delta, differences, digest, outcomes, ranks, read_endpoint, spearman, two_seed_contrast


class RegisteredAnalysisTests(unittest.TestCase):
    def test_wrong_sampling_is_rejected_before_loading_outcomes(self):
        with tempfile.TemporaryDirectory(dir='.') as directory:
            path = Path(directory).resolve().relative_to(Path.cwd())/'generation.json'
            for n, max_tokens in [(8,4096),(1,2048)]:
                path.write_text(json.dumps({'config':{'protocol':'omi2','n':n,'temperature':0,'max_tokens':max_tokens}}))
                spec = {'generation_manifest':{'path':str(path),'sha256':digest(path)}}
                with self.assertRaisesRegex(ValueError,'Endpoint protocol'):
                    read_endpoint(spec,5000,29,'qwen','math','base','P')

    def endpoint_fixture(self, directory, cell='P', initialization='base', seed=17):
        root = Path(directory).resolve().relative_to(Path.cwd())
        def write(name, value, jsonl=False):
            path = root/name
            path.write_text((''.join(json.dumps(x)+'\n' for x in value) if jsonl else json.dumps(value)))
            return {'path':str(path),'sha256':digest(path)}
        model = MODELS['qwen_'+initialization]
        training = {'run_id':'synthetic_training','cell':cell,'model':{'repo':model,'revision':'f'*40},
                    'config':{'seed':seed,'data_seed':seed,'dataset':'math_'+cell.lower()},
                    'dataset':{'name':'math_'+cell.lower(),'sha256':DATA_SHA['math'][cell]},
                    'dose':{'expected_updates':128 if cell=='L' else 1024}}
        spec = {'training_manifest':write('training.json',training), 'checkpoint_manifest':write('checkpoint.json',[]),
                'inputs':write('inputs.jsonl',[{'id':'a','problem':'synthetic'}],True),
                'raw':write('raw.jsonl',[{'id':'a','draw':0,'text':'synthetic'}],True),
                'labels':write('labels.jsonl',[{'id':'a','draw':0,'correct':True}],True)}
        generation = {'config':{'protocol':'omi2','n':1,'temperature':0,'max_tokens':4096,'seed':999,
                      'template_family':'qwen','task':'math','model':'/p012/training/synthetic_training/checkpoint',
                      'revision':'f'*40,'training_run_id':'synthetic_training',
                      'checkpoint_manifest_sha256':spec['checkpoint_manifest']['sha256']},
                      'input_sha256':spec['inputs']['sha256'],
                      'checkpoint_verification':{'training_run_id':'synthetic_training',
                      'training_manifest_sha256':spec['training_manifest']['sha256'],
                      'checkpoint_manifest_sha256':spec['checkpoint_manifest']['sha256'],'initialization_repo':model}}
        spec['generation_manifest'] = write('generation.json',generation)
        spec['termination'] = write('termination.json',{'raw_sha256':spec['raw']['sha256'],
                    'labels_sha256':spec['labels']['sha256'],
                    'all':{'responses':1,'correct':1,'accuracy':1.,'length_cap_rate':0.}})
        return spec

    def test_swapped_cell_labels_raise(self):
        with tempfile.TemporaryDirectory(dir='.') as directory:
            spec = self.endpoint_fixture(directory,cell='P')
            with self.assertRaisesRegex(ValueError,'Training cell'):
                read_endpoint(spec,1,17,'qwen','math','base','L')

    def test_swapped_base_and_instruct_raise(self):
        with tempfile.TemporaryDirectory(dir='.') as directory:
            spec = self.endpoint_fixture(directory,initialization='base')
            with self.assertRaisesRegex(ValueError,'initialization'):
                read_endpoint(spec,1,17,'qwen','math','instruct','P')

    def test_swapped_training_seeds_raise(self):
        with tempfile.TemporaryDirectory(dir='.') as directory:
            spec = self.endpoint_fixture(directory,seed=17)
            with self.assertRaisesRegex(ValueError,'seed'):
                read_endpoint(spec,1,29,'qwen','math','base','P')

    def test_sampling_seed_does_not_replace_training_identity(self):
        with tempfile.TemporaryDirectory(dir='.') as directory:
            spec = self.endpoint_fixture(directory,seed=17)
            self.assertEqual(read_endpoint(spec,1,17,'qwen','math','base','P')['outcomes'],{'a':True})

    def test_checkpoint_and_termination_cross_wiring_raise(self):
        for field in ['generation_manifest','termination']:
            with tempfile.TemporaryDirectory(dir='.') as directory:
                spec = self.endpoint_fixture(directory)
                path = Path(spec[field]['path']);value=json.loads(path.read_text())
                if field=='generation_manifest':value['checkpoint_verification']['training_manifest_sha256']='0'*64
                else:value['raw_sha256']='0'*64
                path.write_text(json.dumps(value));spec[field]['sha256']=digest(path)
                with self.assertRaisesRegex(ValueError,'bound|Termination'):
                    read_endpoint(spec,1,17,'qwen','math','base','P')

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
        self.assertFalse(r['noticeable'])

    def test_noticeable_uses_frozen_joint_mean_rule(self):
        low={s:{str(i):False for i in range(100)} for s in ['17','29']}
        high={'17':{str(i):i<2 for i in range(100)},'29':{str(i):i<8 for i in range(100)}}
        r=two_seed_contrast(high,low)
        self.assertTrue(r['noticeable'])
        self.assertFalse(r['by_seed']['17']['abs_delta_at_least_3pp'])
        self.assertEqual(r['seed_mean']['delta_pp'],5.)

    def test_tied_ranks_constant_input_and_negative_capability_direction(self):
        np.testing.assert_array_equal(ranks([3,1,1,2]),[4,1.5,1.5,3])
        self.assertAlmostEqual(spearman([1,2,3],[3,2,1]),-1)
        self.assertIsNone(spearman([1,1,1],[1,2,3]))
        self.assertAlmostEqual(spearman([-3,-2,-1],[1,2,3]),1)


if __name__ == '__main__': unittest.main()
