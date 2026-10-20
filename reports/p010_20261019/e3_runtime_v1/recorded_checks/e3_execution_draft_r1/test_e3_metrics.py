import importlib.util
from pathlib import Path
import random
import unittest
from copy import deepcopy

path = Path(__file__).with_name('e3_metrics.py')
spec = importlib.util.spec_from_file_location('new_e3_metrics', path)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def dynamic(a, b):
    previous = [0] * (len(b) + 1)
    for x in a:
        current = [0]
        for j, y in enumerate(b):
            current.append(previous[j]+1 if x == y else max(previous[j+1], current[-1]))
        previous = current
    return previous[-1]


def fixture():
    pids = ['q'+str(i) for i in range(200)]
    rows = []
    for label in ('t06', 't08', 't10'):
        for pid in pids:
            for attempt in range(1, 9):
                rows.append(dict(temperature_label=label, problem_id=pid, attempt=attempt,
                    candidate_id=f'{label}/{pid}/{attempt}', answer_text='x = 2',
                    physical_returned_tokens=10, gold_supported=True,
                    stop=dict(stop_reason='native_eos', retained_tokens=9),
                    score=dict(score=dict(correct=True, parsed=True, box_extracted=True))))
    return pids, rows


class Metrics(unittest.TestCase):
    def test_lcs_matches_independent_dynamic_program(self):
        rng = random.Random(4)
        for _ in range(500):
            a = [rng.randrange(5) for _ in range(rng.randrange(25))]
            b = [rng.randrange(5) for _ in range(rng.randrange(25))]
            self.assertEqual(m.lcs_length(a, b), dynamic(a, b))

    def test_rouge_empty_and_order(self):
        self.assertEqual(m.rouge_l('', ''), 1)
        self.assertEqual(m.rouge_l('', 'a'), 0)
        self.assertAlmostEqual(m.rouge_l('a b c', 'a c b'), 2/3)

    def test_lexical_equation_delimiters(self):
        self.assertEqual(m.equation_set(r'Use \(x = 2\) and $y+1$ then \[z = 3\]'), {'x=2', 'y+1', 'z=3'})

    def test_no_semantic_equivalence(self):
        self.assertNotEqual(m.equation_set(r'$x+x$'), m.equation_set(r'$2x$'))

    def test_all_eight_count_cost_even_duplicates(self):
        ids, rows = fixture(); got = m.summarize(rows, ids)
        for value in got['temperatures'].values():
            self.assertEqual(value['usable_unique'], 200)
            self.assertEqual(value['usable_unique_fraction'], 1/8)
            self.assertEqual(value['physical_tokens_per_usable_unique'], 80)
            self.assertEqual(value['similarities']['all']['pair_count'], 5600)
            self.assertEqual(value['similarities']['usable_unique']['pair_count'], 0)

    def test_caps_still_in_denominator_and_cost(self):
        ids, rows = fixture()
        for row in rows:
            if row['attempt'] == 1:
                row['stop']['stop_reason'] = 'length_cap'; row['score']['score']['correct'] = False
        got = m.summarize(rows, ids)['temperatures']['t06']
        self.assertEqual(got['complete_fraction'], 7/8)
        self.assertEqual(got['correct_fraction'], 7/8)
        self.assertEqual(got['physical_tokens'], 16000)
        self.assertEqual(got['usable_unique'], 200)

    def test_missing_attempt_rejected(self):
        ids, rows = fixture()
        with self.assertRaises(ValueError): m.summarize(rows[:-1], ids)

    def test_duplicate_attempt_rejected(self):
        ids, rows = fixture(); rows[-1] = deepcopy(rows[-2])
        with self.assertRaises(ValueError): m.summarize(rows, ids)

    def test_unknown_not_zero(self):
        ids, rows = fixture(); rows[0]['score']['score']['correct'] = None
        with self.assertRaises(ValueError): m.summarize(rows, ids)

    def test_empty_equation_union_disclosed(self):
        values = m.similarities([dict(attempt=1, answer_text='hello'),dict(attempt=2, answer_text='world')])
        self.assertEqual(values['empty_equation_unions'], 1)
        self.assertEqual(values['equation_jaccard_mean'], 1)
        self.assertEqual(values['rouge_L_mean'], 0)


if __name__ == '__main__': unittest.main()
