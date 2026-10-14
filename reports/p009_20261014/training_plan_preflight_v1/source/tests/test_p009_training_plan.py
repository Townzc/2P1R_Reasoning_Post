import copy
import math
import unittest

from experiments.learning_regime_p009.training_plan import (
    TARGETS, checked_rows, frozen_lrs, make_plan, validate_lrs, validate_plan,
)


def row(index, length):
    ids = [11, 12, 13] + [17] * (length - 1) + [99]
    return dict(problem_id=f'fixture/{index}', path_id=f'fixture/{index}/answer',
                response_hash=f'fixturehash{index}', input_ids=ids,
                labels=[-100] * 3 + ids[3:], n_prompt=3,
                n_supervised=length, n_processed=len(ids))


class TrainingPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [row(i, i + 32) for i in range(33)]
        cls.plan17 = make_plan(cls.rows, 17, 99)

    def test_exact_dose_and_all_rows_exposed(self):
        b = validate_plan(self.rows, self.plan17, 17, 99)
        self.assertEqual(b['supervised_response_tokens'], TARGETS)
        self.assertEqual(b['optimizer_updates'], 1024)
        self.assertGreaterEqual(min(self.plan17['row_exposures']), 1)
        self.assertLessEqual(max(self.plan17['row_exposures']) - min(self.plan17['row_exposures']), 1)

    def test_seed29_changes_schedule_not_dose(self):
        p = make_plan(self.rows, 29, 99)
        self.assertNotEqual(p['updates'], self.plan17['updates'])
        self.assertEqual(p['supervised_targets'], TARGETS)

    def test_q_zero_is_rejected(self):
        template = row(0, 2000)
        many = [dict(template, problem_id=f'p{i}', path_id=f'a{i}') for i in range(1049)]
        with self.assertRaisesRegex(ValueError, 'no q=0'):
            make_plan(many, 17, 99)

    def test_infeasible_remainder_has_no_target_relaxation(self):
        with self.assertRaisesRegex(ValueError, 'remainder'):
            make_plan([row(0, 3)], 17, 99)

    def test_one_ulp_lr_change_rejected(self):
        rates = frozen_lrs()
        self.assertEqual(rates[63], 1e-4)
        self.assertEqual(rates[-1], 1e-5)
        rates[100] = math.nextafter(rates[100], math.inf)
        with self.assertRaisesRegex(ValueError, 'LR bytes'):
            validate_lrs(rates)

    def test_labels_eos_duplicates_and_context_rejected(self):
        for changed in ('mask', 'eos', 'duplicate', 'context'):
            data = copy.deepcopy(self.rows)
            if changed == 'mask':
                data[0]['labels'][0] = 11
            elif changed == 'eos':
                data[0]['input_ids'][5] = 99
            elif changed == 'duplicate':
                data[1]['problem_id'] = data[0]['problem_id']
            else:
                data[0] = row(0, 2046)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                checked_rows(data, 99)

    def test_dose_seed_and_missing_update_rejected(self):
        with self.assertRaises(ValueError):
            make_plan(self.rows, 31, 99)
        for changed in ('dose', 'update'):
            p = copy.deepcopy(self.plan17)
            if changed == 'dose':
                p['supervised_targets'] -= 1
            else:
                p['updates'].pop()
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                validate_plan(self.rows, p, 17, 99)

    def test_non_integer_metadata_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[0]['n_supervised'] = float(rows[0]['n_supervised'])
        with self.assertRaises(ValueError):
            checked_rows(rows, 99)
        p = copy.deepcopy(self.plan17)
        p['q'] = float(p['q'])
        with self.assertRaises(ValueError):
            validate_plan(self.rows, p, 17, 99)


if __name__ == '__main__':
    unittest.main()
