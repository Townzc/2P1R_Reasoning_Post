"""Offline boundary fixtures only; no P011 production corpus is constructed."""
from collections import Counter
import itertools
from pathlib import Path
import random
import sqlite3
import tempfile
import unittest

from experiments.p011 import data_contract as c
from scripts.prepare_p011_long_inputs import grouped_rows


class DataRules(unittest.TestCase):
    def test_parent_normalization_preserves_internal_whitespace(self):
        self.assertEqual(c.parent_key('  Ａ + １  '), 'A + 1')
        self.assertNotEqual(c.parent_key('a  b'), c.parent_key('a b'))

    def test_tail_is_last_think_close_and_literal_final2000(self):
        self.assertFalse(c.complete('\\boxed{bad}</think>no box'))
        self.assertTrue(c.complete('reason</think>answer \\boxed{4}'))
        self.assertFalse(c.complete('\\boxed{4}' + 'x' * 2001))
        self.assertTrue(c.complete('x' * 2200 + '\\boxed{4}'))

    def test_two_turn_schema_no_silent_flattening(self):
        row = {'conversations': [{'from': 'human', 'value': 'q'},
                                 {'from': 'gpt', 'value': 'a'}]}
        self.assertEqual(c.conversation_pair(row), ('q', 'a'))
        row['conversations'].append({'from': 'human', 'value': 'followup'})
        with self.assertRaises(ValueError):
            c.conversation_pair(row)

    def test_13_words_and_short_exact_overlap(self):
        source = ' '.join(f'w{i}' for i in range(14))
        rule = c.Decontamination([source, 'short exact'])
        self.assertTrue(rule.hit('prefix ' + ' '.join(f'w{i}' for i in range(13))))
        self.assertFalse(rule.hit(' '.join(f'w{i}' for i in range(12))))
        self.assertTrue(rule.hit(' short exact '))

    def test_nested_parent_and_response_orders(self):
        keys = [f'p{i:04}' for i in range(4100)]
        order, rows = c.ot3_order(keys, lambda key: [f'{key}:{i}' for i in range(16)])
        actual = {name: [r for key in order[:p] for r in rows[key][:k]]
                  for name, (p, k) in c.CELLS.items()}
        for name, (p, k) in c.CELLS.items():
            self.assertEqual(len(actual[name]), p * k)
        self.assertTrue(set(actual['A1']) < set(actual['A5']))
        self.assertTrue(set(actual['A6']) < set(actual['A7']))
        self.assertTrue(set(actual['A6']) < set(actual['A8']))
        with self.assertRaises(ValueError):
            c.ot3_order(keys[:4000], lambda key: list(range(16)))

    def test_d_selection_is_one_original_row_before_filtering(self):
        rows = [{'id': i, 'response': 'unboxed' if i % 2 else '\\boxed{1}'}
                for i in range(9)]
        chosen = c.choose_d_row('p', 'am_qwen3', rows)
        self.assertIn(chosen, rows)
        self.assertEqual(chosen, c.choose_d_row('p', 'am_qwen3', rows))

    def test_cross_source_parents_preserve_every_row(self):
        db = sqlite3.connect(':memory:')
        db.execute('CREATE TABLE rows(dataset,parent,source_file,row_index,question,response,metadata)')
        for source, n in [('a', 10), ('b', 6)]:
            for i in range(n):
                db.execute('INSERT INTO rows VALUES(?,?,?,?,?,?,?)',
                           ('ot3', 'q', source, i, 'q', f'a{i}', '{}'))
        found = grouped_rows(db, 'ot3', 'q')
        self.assertEqual(len(found), 16)
        self.assertEqual(found[10]['source_file'], 'b')
        db.close()

    def test_exact_subset_matches_small_exhaustive_feasibility(self):
        lengths = [3, 5, 7, 11, 13, 17]
        reachable = {sum(x) for n in range(7) for x in itertools.combinations(lengths, n)}
        for target in range(sum(lengths) + 1):
            if target in reachable:
                indices = c.exact_subset(lengths, target, 17)
                self.assertEqual(len(indices), len(set(indices)))
                self.assertEqual(sum(lengths[i] for i in indices), target)
            else:
                with self.assertRaises(ValueError):
                    c.exact_subset(lengths, target, 17)

    def test_checkpointed_subset_crosses_multiple_blocks(self):
        lengths = [1000 + i for i in range(170)]
        target = sum(lengths) - sum(lengths[:9])
        ids = c.exact_subset(lengths, target, 17)
        self.assertEqual(sum(lengths[i] for i in ids), target)
        self.assertEqual(len(ids), len(set(ids)))

    def test_schedule_exact_dose_balanced_positive_exposure(self):
        rows = [{'path_id': str(i), 'n_supervised': 1000 + i, 'n_processed': 1200 + i}
                for i in range(80)]
        dose = 2 * sum(x['n_supervised'] for x in rows) + sum(x['n_supervised'] for x in rows[:40])
        plan = c.whole_schedule(rows, dose)
        counts = Counter(i for b in plan['updates'] for i in b)
        self.assertEqual(sum(rows[i]['n_supervised'] * n for i, n in counts.items()), dose)
        self.assertEqual(set(counts.values()), {2, 3})
        self.assertEqual(len(plan['updates']), (dose + 63999) // 64000)
        self.assertTrue(all(plan['updates']))

    def test_schedule_never_raises_frozen_dose_or_uses_zero_exposure(self):
        rows = [{'path_id': str(i), 'n_supervised': x, 'n_processed': x + 3}
                for i, x in enumerate([10, 14])]
        for budget in (23, 25):
            with self.assertRaises(ValueError):
                c.whole_schedule(rows, budget)

    def test_pinned_native_tokenizer_supervises_only_assistant_and_eos(self):
        from transformers import AutoTokenizer
        folder = Path('.local/exploratory_20261014/r1/inputs/instruct_model')
        tok = AutoTokenizer.from_pretrained(folder, local_files_only=True,
                                            trust_remote_code=False, use_fast=True)
        for response in ('<think>work</think>\\boxed{2}', '\nanswer \\boxed{４}', '结果：\\boxed{四}'):
            out = c.encode_complete(tok, 'What is 1+1?', response, 'fixture')
            labels = out['labels']
            self.assertEqual(labels[:out['assistant_start']], [-100] * out['assistant_start'])
            self.assertEqual(out['n_supervised'], sum(x != -100 for x in labels))
            self.assertEqual(labels[out['assistant_end'] - 1], 151645)
            self.assertEqual(labels[-1], -100)
            self.assertEqual(c.bounded_length(tok, 'What is 1+1?', response), len(out['input_ids']))


if __name__ == '__main__':
    unittest.main()
