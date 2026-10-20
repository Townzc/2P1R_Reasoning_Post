"""New consumer tests only; temporary synthetic data, no old tests or raw reads."""
import argparse
import copy
import json
from pathlib import Path
import random
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts import prepare_p011_ot3_4032_inputs as c


class NewConsumer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.dispositions = cls.root/'synthetic_dispositions.jsonl'
        cls.hashes = [c.rules.identity(f'Question {i}') for i in range(53107)]
        with cls.dispositions.open('x') as f:
            for i,h in enumerate(cls.hashes):
                f.write(json.dumps({'parent_sha256':h, 'candidate_position':i+1,
                    'row_count':16,'eligible':i<4038,
                    'flags':{'incomplete':i>=4038,'decontamination_hit':False,
                             'any_overlength':False}})+'\n')
        cls.report={'counts':{'eligible':4038,'examined_candidate_parents':53107},
                    'unexamined_candidates':0,'stopped_at_target':False}
        cls.keys=[f'Question {i}' for i in range(4038)]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @staticmethod
    def rows(key):
        return [{'question':key,'path_id':key+':'+str(i),'response':str(i)}
                for i in range(16)]

    def test_confirmed_exhausted_order_is_preserved(self):
        self.assertEqual(c.confirmed_order(self.dispositions,self.report),self.hashes[:4038])

    def test_nonexhausted_or_disagreed_outcome_rejected(self):
        changed=copy.deepcopy(self.report);changed['unexamined_candidates']=1
        with self.assertRaisesRegex(ValueError,'outcome differs'):
            c.confirmed_order(self.dispositions,changed)

    def test_duplicate_disposition_is_rejected(self):
        p=self.root/'duplicate.jsonl'
        row={'parent_sha256':'a'*64,'candidate_position':1,'row_count':16,
             'eligible':False,'flags':{}}
        p.write_text(json.dumps(row)+'\n'+json.dumps({**row,'candidate_position':2})+'\n')
        with self.assertRaisesRegex(ValueError,'sequential'):
            c.confirmed_order(p,self.report)

    def test_confirmed_flag_conflict_is_rejected(self):
        p=self.root/'conflict.jsonl'
        p.write_text(json.dumps({'parent_sha256':'b'*64,'candidate_position':1,
            'row_count':16,'eligible':True,'flags':{'incomplete':True}})+'\n')
        with self.assertRaisesRegex(ValueError,'conflicts'):
            c.confirmed_order(p,self.report)

    def test_readonly_key_resolution_uses_saved_order(self):
        p=self.root/'small.sqlite'
        db=sqlite3.connect(p);db.execute('CREATE TABLE rows(dataset TEXT,parent TEXT)')
        db.executemany('INSERT INTO rows VALUES (?,?)',[('ot3',k) for k in reversed(self.keys)])
        db.commit();db.close()
        db=sqlite3.connect(p.as_uri()+'?mode=ro&immutable=1',uri=True)
        self.addCleanup(db.close)
        self.assertEqual(c.restore_keys(db,self.hashes[:4038]),self.keys)
        with self.assertRaises(sqlite3.OperationalError):db.execute('DELETE FROM rows')
        missing=self.hashes[:4037]+[c.rules.identity('missing')]
        with self.assertRaisesRegex(ValueError,'missing'):
            c.restore_keys(db,missing)

    def test_nested_grid_equal_diagonal_and_original_response_seed(self):
        cells,unused=c.select_cells(self.keys,self.rows)
        self.assertEqual(unused,self.keys[4032:])
        for cell,(p,k) in c.GRID.items():
            self.assertEqual(len(cells[cell]),p*k)
            self.assertEqual({r['question'] for r in cells[cell]},set(self.keys[:p]))
        for child,parent in [('A1','A2'),('A2','A3'),('A3','A4'),('A4','A5'),
                             ('A1','A6'),('A6','A7'),('A3','A8')]:
            self.assertLessEqual({r['path_id'] for r in cells[child]},
                                 {r['path_id'] for r in cells[parent]})
        self.assertEqual([len(cells[x]) for x in ('A5','A7','A8')],[4032]*3)
        first=self.rows(self.keys[0]);random.Random(c.rules.identity(self.keys[0]+'p011')[:16]).shuffle(first)
        self.assertEqual(cells['A5'][:16],first)
        self.assertTrue(all(r['question'] not in unused for rows in cells.values() for r in rows))

    def test_missing_or_foreign_answer_never_substituted(self):
        with self.assertRaisesRegex(ValueError,'Original16'):
            c.select_cells(self.keys,lambda k:self.rows(k)[:15])
        def wrong(k):
            rows=self.rows(k);rows[3]['question']='Foreign question';return rows
        with self.assertRaisesRegex(ValueError,'Foreign'):
            c.select_cells(self.keys,wrong)

    def test_permanent_attempt_or_output_blocks_before_encoding(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);fence=root/'ATTEMPT';out=root/'output'
            with patch.object(c.argparse.ArgumentParser,'parse_args',return_value=argparse.Namespace()), \
                 patch.object(c.old,'check_cutoff'),patch.object(c,'admit',return_value=({}, {}, {})), \
                 patch.object(c,'ATTEMPT',fence),patch.object(c,'OUTPUT',out), \
                 patch.object(c.old,'encode_and_plan') as encode:
                fence.write_text('{}')
                with self.assertRaisesRegex(ValueError,'already attempted'):c.main()
                fence.unlink();out.mkdir()
                with self.assertRaisesRegex(ValueError,'already attempted'):c.main()
                encode.assert_not_called()


class SyntheticAdmission(unittest.TestCase):
    """Fake reviewer evidence stays in TemporaryDirectory and never admits real work."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.original=self.root/'original';self.original.mkdir()
        self.args=argparse.Namespace()
        for name in ('original_code_review','source_lock','prior_owner_amendment','prior_proposal',
                     'owner_amendment','proposal','preservation','code_review'):
            p=self.root/(name+'.json');p.write_text('{}');setattr(self.args,name,str(p))
        self.source=self.root/'synthetic.py';self.source.write_text('# fixture only\n')
        self.report=self.root/'synthetic_report.md';self.report.write_text('SYNTHETIC ONLY\n')
        owner={'scope':'p011-OT3-252-1008-4032-owner-amendment',
            'authority':'direct_human_reply_in_current_chat','original_plan_sha256':c.rules.PLAN_SHA256,
            'proposal_sha256':c.old.sha(self.args.proposal),
            'prior_R1_R3_owner_sha256':c.old.sha(self.args.prior_owner_amendment),
            'original_failure_preservation_sha256':c.old.sha(self.args.preservation),
            'grid':c.GRID,'original_confirmed_eligible':4038,'selected_confirmed_prefix':4032,
            'confirmed_unused_tail':6,'B_rule':'maximum_once_pass_tokens_across_amended_eight_A_cells',
            'U_rule':'ceil_B_divided_by_64000'}
        owner.update({k:True for k in ('required_real_re_review','reuse_original_candidate_order',
                                      'original_failed_attempt_retained')})
        owner.update({k:False for k in ('refilter_allowed','new_generation_allowed','budget_changed',
                        'arms_seeds_LR_evaluation_smoke_rules_changed','B_C_D_counts_changed')})
        proof={'state':'EXIT1_CONSUMED','original_session':88890,'source':str(self.original),
               'automatic_retry_allowed':False}
        Path(self.args.preservation).write_text(json.dumps(proof))
        owner['original_failure_preservation_sha256']=c.old.sha(self.args.preservation)
        Path(self.args.owner_amendment).write_text(json.dumps(owner))
        self.review={'scope':c.SCOPE,'decision':'PASS-WITH-NOTES',
            'source_files':{str(self.source):c.old.sha(self.source)},'plan_sha256':c.rules.PLAN_SHA256,
            'source_lock_sha256':c.old.sha(self.args.source_lock),
            'owner_count_amendment_sha256':c.old.sha(self.args.owner_amendment),
            'owner_prior_R1_R3_sha256':c.old.sha(self.args.prior_owner_amendment),
            'proposal_sha256':c.old.sha(self.args.proposal),
            'original_failure_preservation_sha256':c.old.sha(self.args.preservation),
            'original_code_acceptance_sha256':c.old.sha(self.args.original_code_review),'grid':c.GRID,
            'local_report_path':str(self.report),'report_sha256':c.old.sha(self.report),'target_commit':'a'*40}
        self.review.update({k:True for k in ('confirmed_eligible_parents_reused_without_refiltering',
            'original_failed_attempt_retained','new_global_attempt_fence','first_full_encoding_only',
            'operational_details_accepted')})
        (self.original/'INTENT.json').write_text(json.dumps({'source_files':{'old':'fixed'},
            'review_sha256':self.review['original_code_acceptance_sha256'],
            'source_lock_sha256':self.review['source_lock_sha256']}))

    def call_admit(self):
        Path(self.args.code_review).write_text(json.dumps(self.review))
        with patch.object(c.old,'admit_code',return_value=({}, {'old':'fixed'})), \
             patch.object(c,'ORIGINAL',self.original),patch.object(c,'SOURCES',(str(self.source),)):
            return c.admit(self.args)

    def test_exact_synthetic_chain_and_original_phase_absence(self):
        self.assertEqual(self.call_admit()[1]['grid'],c.GRID)
        (self.original/'ENCODED.jsonl').write_text('partial')
        with self.assertRaisesRegex(ValueError,'already have happened'):self.call_admit()

    def test_old_review_or_unbound_source_cannot_admit(self):
        self.review['scope']=c.old.REVIEW_SCOPE
        with self.assertRaisesRegex(ValueError,'Real exact'):self.call_admit()
        self.review['scope']=c.SCOPE;self.source.write_text('# changed fixture\n')
        with self.assertRaisesRegex(ValueError,'Real exact'):self.call_admit()

    def test_missing_review_flag_and_unapproved_count_rejected(self):
        self.review['first_full_encoding_only']=False
        with self.assertRaisesRegex(ValueError,'Real exact'):self.call_admit()
        self.review['first_full_encoding_only']=True
        owner=json.loads(Path(self.args.owner_amendment).read_text());owner['selected_confirmed_prefix']=4096
        Path(self.args.owner_amendment).write_text(json.dumps(owner))
        with self.assertRaisesRegex(ValueError,'direct owner'):self.call_admit()


if __name__=='__main__':unittest.main()
