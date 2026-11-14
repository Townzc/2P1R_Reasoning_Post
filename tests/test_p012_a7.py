import copy
import unittest
from analysis.p012_a7 import (
    A6_AUTHORITY, AUTHORITY, DATA_SHA, INPUT_SHA, MODELS, RUNNER_SHA,
    analyze, interval_fields, run_id, validate_generation, validate_training, validate_result_identity,
)
from analysis.p012_registered import two_seed_contrast


class A7BindingTests(unittest.TestCase):
    def training(self, model='9b', arm='short', seed=29):
        repo, rev, lr = MODELS[model]
        return {'run_id': run_id(model, arm, seed), 'model': repo, 'seed': seed, 'mode': 'train',
                'A7_arm': arm, 'cell': 'L', 'rank': 32, 'learning_rate': lr,
                'asset': {'repo': repo, 'revision': rev},
                'dataset': {'sha256': DATA_SHA['9b' if model == '9b_base' else model][arm]},
                'dose': {'parents': 512, 'distinct_rows': 512, 'paths_per_parent': 1,
                         'epochs': 2, 'presentations': 1024, 'effective_batch': 8, 'expected_updates': 128},
                'source_sha256': RUNNER_SHA,
                'prediction_commit': AUTHORITY if seed == 29 or arm == 'concise' else A6_AUTHORITY}

    def generation(self, train):
        names = ['train_loss.jsonl', 'ROW_ORDER.json', 'STATE.json', 'SAMPLER.json']
        hashes = {'training/'+n: str(i)*64 for i, n in enumerate(names, 1)}
        fields = ['train_loss_sha256', 'row_order_sha256', 'state_manifest_sha256', 'sampler_manifest_sha256']
        ev = {'mode': 'generate', 'model': train['model'], 'seed': train['seed'], 'source_sha256': RUNNER_SHA,
              'asset': train['asset'], 'sampler_path': 'tinker://fixture/sampler_weights/final',
              'evaluation': {'sha256': INPUT_SHA}, 'training_evidence': {
                  'run_id': train['run_id'], 'updates': 128,
                  **dict(zip(fields, hashes.values(), strict=True))}}
        gen = {'renderer': 'qwen3_5_disable_thinking', 'input_sha256': INPUT_SHA,
               'config': {'protocol': 'omi2', 'task': 'math', 'n': 1, 'temperature': 0,
                          'top_p': 1, 'max_tokens': 4096, 'max_model_len': 8192, 'seed': train['seed']}}
        sampler = {'path': ev['sampler_path']}
        return ev, gen, sampler, hashes

    def test_all_fifteen_fixed_slots_validate(self):
        for model in MODELS:
            for seed in ((17,) if model == '9b_base' else (17, 29)):
                for arm in ('short', 'long', 'concise'):
                    r = self.training(model, arm, seed)
                    validate_training(r, model, arm, seed)
                    validate_generation(r, *self.generation(r))

    def test_short_long_swaps_fail_even_though_both_have_cell_L(self):
        with self.assertRaisesRegex(ValueError, 'arm'):
            validate_training(self.training(arm='short'), '9b', 'long', 29)

    def test_base_instruct_swap_fails(self):
        with self.assertRaisesRegex(ValueError, 'model'):
            validate_training(self.training(seed=17), '9b_base', 'short', 17)

    def test_training_seed_swap_fails(self):
        with self.assertRaisesRegex(ValueError, 'seed'):
            validate_training(self.training(seed=17), '9b', 'short', 29)

    def test_same_model_cross_teacher_dataset_fails(self):
        r = self.training()
        r['dataset']['sha256'] = DATA_SHA['4b']['short']
        with self.assertRaisesRegex(ValueError, 'data'):
            validate_training(r, '9b', 'short', 29)

    def test_dose_revision_and_source_changes_fail(self):
        for change in ('dose', 'revision', 'source'):
            r = self.training()
            if change == 'dose': r['dose']['expected_updates'] = 1024
            elif change == 'revision': r['asset']['revision'] = '0'*40
            else: r['source_sha256'] = '0'*64
            with self.assertRaises(ValueError): validate_training(r, '9b', 'short', 29)

    def test_eval_must_bind_actual_state_and_sampler(self):
        for field in ('run_id', 'state_manifest_sha256', 'sampler_manifest_sha256'):
            r = self.training(); ev, gen, sampler, hashes = self.generation(r)
            ev['training_evidence'][field] = 'wrong'
            with self.assertRaises(ValueError): validate_generation(r, ev, gen, sampler, hashes)
        r = self.training(); ev, gen, sampler, hashes = self.generation(r)
        sampler['path'] = 'tinker://different/sampler_weights/final'
        with self.assertRaisesRegex(ValueError, 'Sampler'): validate_generation(r, ev, gen, sampler, hashes)

    def test_eval_seed_does_not_repair_wrong_training_identity(self):
        r = self.training(); ev, gen, sampler, hashes = self.generation(r)
        ev['seed'] = 17
        with self.assertRaisesRegex(ValueError, 'seed'): validate_generation(r, ev, gen, sampler, hashes)

    def test_non_greedy_or_different_context_fails(self):
        for key, value in [('n', 8), ('temperature', .7), ('max_tokens', 2048), ('max_model_len', 16384)]:
            r = self.training(); ev, gen, sampler, hashes = self.generation(r)
            gen['config'][key] = value
            with self.assertRaisesRegex(ValueError, 'protocol'): validate_generation(r, ev, gen, sampler, hashes)

    def test_joint_core_keeps_question_sample_size_and_excludes_hypothesis_flags(self):
        high = {'17': {'a': True, 'b': False}, '29': {'b': True, 'a': False}}
        low = {'17': {'b': True, 'a': False}, '29': {'a': True, 'b': False}}
        r = two_seed_contrast(high, low)
        mean = interval_fields(r['seed_mean'])
        self.assertEqual((mean['n_questions'], mean['lower95_pp'], mean['upper95_pp']), (2, 0, 0))
        self.assertNotIn('noticeable', mean)
        self.assertNotIn('abs_delta_at_least_3pp', mean)

    def test_real_execution_is_disabled_before_review(self):
        with self.assertRaisesRegex(ValueError, 'awaits Claude'):
            analyze({'accepted_analysis_review_commit': AUTHORITY})

    def test_legacy_and_new_result_schemas_bind_same_training_identity(self):
        for seed in (17, 29):
            r = self.training(seed=seed)
            result = {k: r[k] for k in ('model', 'seed', 'cell', 'dose')}
            result['arm'] = 'short'
            if seed == 17:
                result['dataset_sha256'] = r['dataset']['sha256']
            else:
                result.update(training_run_id=r['run_id'], training_request_sha256='f'*64,
                              dataset=r['dataset'])
            validate_result_identity(result, r, 'f'*64)
            wrong = copy.deepcopy(result); wrong['arm'] = 'long'
            with self.assertRaisesRegex(ValueError, 'identity'):
                validate_result_identity(wrong, r, 'f'*64)


if __name__ == '__main__':
    unittest.main()
