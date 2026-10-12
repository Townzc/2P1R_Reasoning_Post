"""Safety checks for immutable C017 reconstruction and full-row schedule reuse."""
import unittest

from scripts.prepare_midpoint_inventory import restore_parents, sha_bytes, validate_schedule, expected_selected_pairs


class MidpointInventoryTests(unittest.TestCase):
    def fixture(self):
        c = dict(id='gsm8k/train/00001', dataset='gsm8k', original_split='train',
                 source_locator='train.jsonl:2', subject=None, level=None, stratum='gsm8k',
                 problem='Two plus three?', reference='2+3=5\n#### 5', answer='5')
        p = {k:v for k,v in c.items() if k not in ('problem','reference','answer')}
        p.update(partition='audit_draw', rank=1, group_id='group-a', exclusions=[])
        for k in ('problem','reference','answer'):
            p[k+'_sha256'] = sha_bytes(c[k].encode())
        p['normalized_problem_sha256'] = sha_bytes(c['problem'].encode())
        return c,p

    def test_restores_content_and_preserves_frozen_missing_metadata(self):
        c,p=self.fixture()
        restored=restore_parents([p],[c])
        self.assertEqual(restored[0]['rank'],1)
        self.assertEqual(restored[0]['partition'],'audit_draw')
        self.assertEqual(restored[0]['problem'],c['problem'])
        self.assertNotIn('problem_sha256',restored[0])

    def test_changed_answer_rejected(self):
        c,p=self.fixture();c['answer']='6'
        with self.assertRaisesRegex(ValueError,'content checksum'):
            restore_parents([p],[c])

    def test_changed_original_split_rejected(self):
        c,p=self.fixture();c['original_split']='test'
        with self.assertRaisesRegex(ValueError,'source metadata'):
            restore_parents([p],[c])

    def test_missing_or_duplicate_parent_rejected(self):
        c,p=self.fixture()
        for records in ([],[c,c]):
            with self.assertRaisesRegex(ValueError,'identity inventory'):
                restore_parents([p],records)

    def test_selection_keeps_acquired_shortfalls_without_backfill(self):
        acquired=[{'id':'a'}, {'id':'missing'}, {'id':'b'}]
        decisions=[dict(problem_id='a',reason='accepted',candidate_index=1),
                   dict(problem_id='a',reason='duplicate_normalized_text',candidate_index=2),
                   dict(problem_id='a',reason='accepted',candidate_index=3),
                   dict(problem_id='b',reason='accepted',candidate_index=1),
                   dict(problem_id='outside',reason='accepted',candidate_index=1)]
        selected=expected_selected_pairs(acquired,decisions,2)
        self.assertEqual([(d['problem_id'],d['candidate_index']) for d in selected],
                         [('a',1),('a',3),('b',1)])
        self.assertEqual(len(acquired),3)

    def schedule_fixture(self):
        rows=[dict(n_supervised=3,n_processed=5),dict(n_supervised=7,n_processed=9)]
        saved=dict(updates=[[0,1],[0]],row_exposures={'0':2,'1':1},
                   summary=dict(optimizer_updates=2,supervised_response_tokens=13,
                                processed_nonpadding_tokens=19))
        return rows,saved

    def test_whole_response_schedule_exact_dose(self):
        rows,saved=self.schedule_fixture()
        result=validate_schedule(rows,saved)
        self.assertTrue(result['full_responses_only'])
        self.assertEqual(result['supervised_response_tokens'],13)
        self.assertEqual(result['row_exposure_range'],[1,2])

    def test_partial_row_or_out_of_bounds_index_rejected(self):
        for index in (0.5,True,2,-1,{'row':0,'tokens':1}):
            rows,saved=self.schedule_fixture();saved['updates'][1]=[index]
            with self.assertRaisesRegex(ValueError,'full-row'):
                validate_schedule(rows,saved)

    def test_missing_selected_pair_rejected(self):
        rows,saved=self.schedule_fixture();saved['updates']=[[0],[0]]
        with self.assertRaisesRegex(ValueError,'never exposed'):
            validate_schedule(rows,saved)

    def test_wrong_token_budget_or_exposure_rejected(self):
        rows,saved=self.schedule_fixture();saved['summary']['supervised_response_tokens']=12
        with self.assertRaisesRegex(ValueError,'dose mismatch'):
            validate_schedule(rows,saved)
        rows,saved=self.schedule_fixture();saved['row_exposures']['0']=1
        with self.assertRaisesRegex(ValueError,'exposure mismatch'):
            validate_schedule(rows,saved)


if __name__ == '__main__':
    unittest.main()
