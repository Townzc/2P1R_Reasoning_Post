"""Only new R1/R2/R3 fixtures. No real corpus, scorer, model or production call."""
import io
import json
from pathlib import Path
import random
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from experiments.p011 import data_contract as rules
from scripts import prepare_p011_long_inputs as builder


def database(teachers, n, answers=1):
    db = sqlite3.connect(':memory:')
    db.execute('CREATE TABLE rows(dataset,parent,source_file,row_index,question,response,metadata)')
    for teacher in teachers:
        for i in range(n):
            for j in range(answers):
                metadata = {'difficulty': i % 3, 'turn_info': [{'source': 'same'}, {}]}
                db.execute('INSERT INTO rows VALUES(?,?,?,?,?,?,?)',
                           (teacher, f'p{i:04}', 'fixture', i * answers + j,
                            f'p{i:04}', '\\boxed{1}', json.dumps(metadata)))
    return db


class RevisionR2(unittest.TestCase):
    def test_complete_epochs_precede_shuffled_exact_extras(self):
        rows = [{'path_id': str(i), 'n_supervised': 1000 + i, 'n_processed': 1200 + 500 * i}
                for i in range(80)]
        dose = 3 * sum(r['n_supervised'] for r in rows) + sum(r['n_supervised'] for r in rows[:35])
        result = rules.whole_schedule(rows, dose)
        stream = sum(result['updates'], [])
        for epoch in range(3):
            expected = list(range(80))
            random.Random(f'17:pass:{epoch}').shuffle(expected)
            self.assertEqual(stream[epoch * 80:(epoch + 1) * 80], expected)
        extra = rules.exact_subset([r['n_supervised'] for r in rows], dose % sum(
            r['n_supervised'] for r in rows), 17)
        random.Random('17:extras').shuffle(extra)
        self.assertEqual(stream[240:], extra)
        self.assertIsNone(result['length_bucket_width'])
        self.assertEqual(sum(rows[i]['n_supervised'] for i in stream), dose)

    def test_inventory_parent_order_is_not_shuffled_again(self):
        keys = [f'p{i:04}' for i in range(4096)]
        random.Random(61).shuffle(keys)
        selected, rows = rules.ot3_order(keys, lambda key: list(range(16)))
        self.assertEqual(selected, keys)
        self.assertEqual(len(rows), 4096)
        with self.assertRaises(ValueError):
            rules.ot3_order(keys + [keys[0]], lambda key: list(range(16)))

    def test_ot3_prefix_stops_at_target_and_counts_wrong_cardinality_globally(self):
        db = database(['ot3'], 8, 16)
        db.execute('INSERT INTO rows VALUES(?,?,?,?,?,?,?)', ('ot3', 'wrong', 'x', 0, 'wrong', 'a', '{}'))
        order = [f'p{i:04}' for i in range(8)]
        random.Random(20261020).shuffle(order)
        # One excluded candidate, then three accepted; remaining answers unseen.
        db.execute('UPDATE rows SET response=? WHERE parent=?', ('incomplete', order[0]))
        with tempfile.TemporaryDirectory() as tmp, patch.object(builder, 'OT3_TARGET', 3), \
                patch.object(rules, 'bounded_length', return_value=5) as length:
            selected, report = builder.ot3_inventory(db, None, rules.Decontamination(['unrelated']),
                                                     Path(tmp), io.StringIO())
            self.assertEqual(selected, order[1:4])
            self.assertEqual(length.call_count, 3 * 16)
            self.assertEqual(report['counts']['full_pool_wrong_cardinality'], 1)
            self.assertEqual(report['counts']['examined_candidate_parents'], 4)
            self.assertEqual(report['unexamined_candidates'], 4)
            self.assertEqual(len((Path(tmp) / 'PARENT_DISPOSITIONS.jsonl').read_text().splitlines()), 4)
        db.close()

    def test_insufficient_ot3_is_retained_without_replacement(self):
        db = database(['ot3'], 2, 16)
        with tempfile.TemporaryDirectory() as tmp, patch.object(builder, 'OT3_TARGET', 3), \
                patch.object(rules, 'bounded_length', return_value=5):
            with self.assertRaises(ValueError):
                builder.ot3_inventory(db, None, rules.Decontamination(['unrelated']),
                                      Path(tmp), io.StringIO())
            proof = json.loads((Path(tmp) / 'INSUFFICIENT_OT3_PARENTS.json').read_text())
            self.assertEqual(proof['counts']['eligible'], 2)
            self.assertTrue(proof['requires_owner_disposition'])
        db.close()

    def test_d_prefix_and_full_common_source_metadata(self):
        db = database(['am_thinking', 'am_qwen3'], 7)
        db.execute('UPDATE rows SET metadata=? WHERE dataset=? AND parent=?',
                   (json.dumps({'turn_info': [{'source': 'different'}, {}]}), 'am_qwen3', 'p0006'))
        order = [f'p{i:04}' for i in range(7)]
        random.Random(20261021).shuffle(order)
        with tempfile.TemporaryDirectory() as tmp, patch.object(builder, 'D_TARGET', 3), \
                patch.object(rules, 'bounded_length', return_value=5) as length:
            cells, report = builder.d_inventory(db, None, rules.Decontamination(['unrelated']),
                                               Path(tmp), io.StringIO())
            self.assertEqual([x['question'] for x in cells['D1']], order[:3])
            self.assertEqual([x['question'] for x in cells['D2']], order[:3])
            self.assertEqual(length.call_count, 6)
            self.assertEqual(report['source_agreement']['different_source_sets'], 1)
            self.assertEqual(report['source_agreement']['common_parents'], 7)
            self.assertEqual(report['unexamined_candidates'], 4)
        db.close()

    def test_d_bad_selected_duplicate_does_not_swap_to_good(self):
        db = database(['am_thinking', 'am_qwen3'], 4, 2)
        order = [f'p{i:04}' for i in range(4)]
        random.Random(20261021).shuffle(order)
        key = order[0]
        chosen = rules.choose_d_row(key, 'am_thinking', builder.grouped_rows(db, 'am_thinking', key))
        db.execute('UPDATE rows SET response=? WHERE dataset=? AND row_index=?',
                   ('incomplete', 'am_thinking', chosen['source_row']))
        with tempfile.TemporaryDirectory() as tmp, patch.object(builder, 'D_TARGET', 2), \
                patch.object(rules, 'bounded_length', return_value=5):
            cells, report = builder.d_inventory(db, None, rules.Decontamination(['unrelated']),
                                               Path(tmp), io.StringIO())
            self.assertEqual([x['question'] for x in cells['D1']], order[1:3])
            self.assertEqual(report['counts']['excluded'], 1)
        db.close()

    def test_maximum_once_dose_not_just_A7(self):
        cells = {'A7': [{'path_id': 'a', 'question': 'q', 'response': 'a'}],
                 'A5': [{'path_id': 'b', 'question': 'q', 'response': 'b'}]}
        def encode(tok, q, a, path):
            return {'path_id': path, 'n_supervised': 5 if path == 'a' else 10,
                    'n_processed': 20, 'input_ids': [], 'labels': []}
        with tempfile.TemporaryDirectory() as tmp, patch.object(rules, 'encode_complete', side_effect=encode):
            failures = builder.encode_and_plan(cells, None, Path(tmp), 'ot3')
            dose = json.loads((Path(tmp) / 'FROZEN_DOSE.json').read_text())
            self.assertEqual(failures, {})
            self.assertEqual(dose['B'], 10)
            self.assertEqual(json.loads((Path(tmp) / 'A7_PLAN.json').read_text())['q'], 2)

    def test_revised_CR_requires_bound_owner_amendment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, obj in [('lock', {'plan_sha256': rules.PLAN_SHA256}),
                              ('report', {'synthetic': True}), ('proposal', {'synthetic': True})]:
                builder.dump(root / name, obj)
            owner = {'scope': 'p011-long-data-R1-R3-owner-amendment',
                     'authority': 'direct_human_reply_in_current_chat',
                     'original_plan_sha256': rules.PLAN_SHA256,
                     'proposal_sha256': builder.sha(root / 'proposal'),
                     'B_rule': 'maximum_once_pass_tokens_across_original_A_cells',
                     'sampling_rule': 'shuffle_candidates_then_check_until_original_target_reached',
                     'required_real_re_review': True, 'budget_changed': False}
            builder.dump(root / 'owner', owner)
            review = {'scope': builder.REVIEW_SCOPE, 'decision': 'PASS',
                      'source_files': {p: builder.sha(p) for p in builder.SOURCE_FILES},
                      'plan_sha256': rules.PLAN_SHA256, 'source_lock_sha256': builder.sha(root / 'lock'),
                      'local_report_path': str(root / 'report'), 'report_sha256': builder.sha(root / 'report'),
                      'operational_details_accepted': True, 'owner_amendment_sha256': builder.sha(root / 'owner'),
                      'proposal_sha256': builder.sha(root / 'proposal')}
            builder.dump(root / 'review', review)
            with self.assertRaises(ValueError):
                builder.admit_code(root / 'review', root / 'lock')
            builder.admit_code(root / 'review', root / 'lock', root / 'owner', root / 'proposal')
            (root / 'proposal').write_text('changed')
            with self.assertRaises(ValueError):
                builder.admit_code(root / 'review', root / 'lock', root / 'owner', root / 'proposal')


if __name__ == '__main__':
    unittest.main()
