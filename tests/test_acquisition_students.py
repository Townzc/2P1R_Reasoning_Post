import copy
import unittest

from experiments.sft_allocation_acquisition.student_contract import training_rows, exact_plans


def parent(pid):
    return dict(id=pid, group_id='group-'+pid, problem='Find 1+1.', answer='2')


def candidate(pid, attempt, usable=True):
    return dict(problem_id=pid, candidate_id=f'{pid}::attempt{attempt:02d}',
        attempt=attempt, usable=usable, text='1+1=2. \\boxed{2}',
        score=dict(clean_correct=usable), usable_duplicate_of=None,
        stop=dict(eos=True, truncated=False))


class CharacterTokenizer:
    eos_token_id = 99999

    def __call__(self, text, **kwargs):
        result = dict(input_ids=[ord(x) for x in text])
        if kwargs.get('return_offsets_mapping'):
            result['offset_mapping'] = [(i, i+1) for i in range(len(text))]
        return result


class StudentContractTests(unittest.TestCase):
    def test_all_usable_rows_and_exact_text_preserved(self):
        records = [candidate('a', 1, False), candidate('b', 1), candidate('a', 2), candidate('a', 3)]
        records[-1]['text'] = 'Different full explanation. \\boxed{2}'
        result = training_rows([parent('a'), parent('b')], ['a', 'b'], records)
        self.assertEqual([r['path_id'] for r in result], ['a::attempt02', 'a::attempt03', 'b::attempt01'])
        self.assertEqual(result[1]['response'], records[-1]['text'])

    def test_unknown_and_duplicate_physical_rows_reject(self):
        r = candidate('a', 1)
        for records in ([r, r], [{**r, 'usable': None}], [candidate('a', 2)]):
            with self.assertRaises(ValueError):
                training_rows([parent('a')], ['a'], records)

    def test_invalid_accepted_and_empty_pool_reject(self):
        r = candidate('a', 1)
        invalid = copy.deepcopy(r); invalid['stop']['truncated'] = True
        for records in ([invalid], [candidate('a', 1, False)]):
            with self.assertRaises(ValueError):
                training_rows([parent('a')], ['a'], records)

    def test_exact_complete_answer_targets_and_balanced_exposures(self):
        records = [candidate(str(i), 1) for i in range(32)]
        for i, record in enumerate(records):
            record['text'] += '.' * i
        parents = [parent(str(i)) for i in range(32)]
        rows = training_rows(parents, [p['id'] for p in parents], records)
        plans = exact_plans(rows, CharacterTokenizer())
        self.assertEqual(set(plans), {'17', '23'})
        for plan in plans.values():
            self.assertEqual(plan['budget']['supervised_response_tokens'], 524288)
            self.assertEqual(len(plan['updates']), 256)
        self.assertEqual(len(rows), 32)


if __name__ == '__main__':
    unittest.main()
