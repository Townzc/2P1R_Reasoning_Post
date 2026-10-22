"""New synthetic checks only; no original data/model/tokenizer/scoring jobs."""
import copy
from decimal import Decimal
import unittest
from experiments.p011.forced_answer import (forced_request, original_digest, digest, joined_labels,
    question_vectors, expected_math_ids, checked_budget, loop_heuristic, forced_sampling, decode_continuation)
from scripts.count_p011_ot3_math_pool import normalized_question, dispersion, prefix_mass
from experiments.learning_regime_p009.math_scoring import decide, last_box


class FakeTokenizer:
    all_special_ids=[9,10]
    def get_vocab(self):return {'x':1,'y':2,'eos':9,'special':10}
    def decode(self,ids,**kwargs):return ''.join({1:'4',2:'}',9:'<eos>',10:'<special>'}[i] for i in ids)


class ProtocolChecks(unittest.TestCase):
    def fixture(self):
        raw={'id':'math500:0000:sample:0','request_sha256':'a'*64,'prompt_token_ids':[3,4],
             'answers':[{'token_ids':[1]*16384,'finish_reason':'length'}]}
        decoded={'id':raw['id'],'raw_record_sha256':original_digest(raw),'backend_finish_reason':'length',
                 'stop_reason':'length_cap','unmapped_model_token_ids':[]}
        return raw,decoded

    def test_exact_original_tokens_suffix_no_reencoding(self):
        raw,decoded=self.fixture();value=forced_request(raw,decoded,[7,8])
        self.assertEqual(value['prompt_token_ids'],[3,4]+[1]*16384+[7,8])
        self.assertEqual(value['original_generated_tokens'],16384)

    def test_natural_or_non16384_never_dispatched(self):
        raw,decoded=self.fixture();raw['answers'][0]['finish_reason']='stop';decoded['raw_record_sha256']=original_digest(raw)
        with self.assertRaises(ValueError):forced_request(raw,decoded,[7])
        raw,decoded=self.fixture();raw['answers'][0]['token_ids'].pop();decoded['raw_record_sha256']=original_digest(raw)
        with self.assertRaises(ValueError):forced_request(raw,decoded,[7])

    def test_raw_digest_mismatch_rejected(self):
        raw,decoded=self.fixture();raw['prompt_token_ids'].append(5)
        with self.assertRaises(ValueError):forced_request(raw,decoded,[7])

    def test_join_preserves_all_natural_booleans_and_missing_is_not_zero(self):
        old={k:True for k in expected_math_ids()};key='math500:0000:sample:0';old[key]=False
        joined=joined_labels(old,{key:True},{key})
        self.assertTrue(all(joined.values()));self.assertFalse(old[key])
        with self.assertRaises(ValueError):joined_labels(old,{}, {key})
        with self.assertRaises(ValueError):joined_labels(old,{key:None},{key})

    def test_greedy_vectors_are_same_single_saved_bit(self):
        labels={k:True for k in expected_math_ids()};labels['math500:0000:greedy:0']=False
        self.assertEqual(question_vectors(labels,'greedy')['math500:0000'],[False]*4)
        self.assertEqual(question_vectors(labels,'sample')['math500:0000'],[True]*4)

    def budget(self):
        return {'hourly_rate_usd':'4.39520','new_epoch_observed_tagged_cost_usd':'100.02287004',
            'prior_unattributed_cost_allowance_usd':'20.02','observed_epoch':1000,
            'active_or_pending_or_unknown_model_slots':0,'new_task_reserve_usd':'12','all_prior_attempts_terminal':True}

    def test_budget_costs_startup_and_platform_grace_under_twelve(self):
        result=checked_budget(self.budget(),1001)
        self.assertLessEqual(Decimal(result['compute_upper_usd'])+Decimal(result['new_noncompute_allowance_usd']),12)
        self.assertLessEqual(result['worker_hard_seconds'],10800)
        self.assertEqual(result['startup_seconds']+result['platform_grace_seconds'],660)

    def test_stale_over_cap_or_eight_slots_rejected(self):
        for field,value in [('observed_epoch',-4000),('new_epoch_observed_tagged_cost_usd','130'),('active_or_pending_or_unknown_model_slots',8)]:
            b=self.budget();b[field]=value
            with self.assertRaises(ValueError):checked_budget(b,1001)

    def continuation(self,ids,finish='stop'):
        req={'id':'math500:0000:greedy:0','prompt_token_ids':[1]*16390}
        item={'id':req['id'],'request_sha256':digest(req),'prompt_token_ids':req['prompt_token_ids'],
            'sampling':forced_sampling([9]),'answers':[{'token_ids':ids,'backend_text':'4}',
            'finish_reason':finish,'stop_reason':9 if finish=='stop' else None}]}
        return req,item

    def test_native_decode_only_new64_text_box_prefix(self):
        req,item=self.continuation([1,2,9]);out=decode_continuation(req,item,[9],FakeTokenizer(),11)
        self.assertEqual(out['answer_segment'],'\\boxed{4}');self.assertEqual(out['stop_reason'],'native_eos')

    def test_partial_or_nonterminal_eos_rejected(self):
        for ids,finish in [([1,2],'length'),([1,9,2],'stop')]:
            req,item=self.continuation(ids,finish)
            with self.assertRaises(ValueError):decode_continuation(req,item,[9],FakeTokenizer(),11)

    def test_64cap_keeps_original_scalar_rejection(self):
        req,item=self.continuation([1]*62+[1,2],'length');out=decode_continuation(req,item,[9],FakeTokenizer(),11)
        self.assertEqual(out['stop_reason'],'length_cap')
        self.assertFalse(decide('4',last_box('\\boxed{4}'),{},stop_reason=out['stop_reason'])['correct'])

    def test_special_and_unknown_are_not_fake_eos(self):
        req,item=self.continuation([1,10],'stop');out=decode_continuation(req,item,[9],FakeTokenizer(),11)
        self.assertEqual(out['stop_reason'],'invalid_special_token')
        req,item=self.continuation([3,9],'stop')
        with self.assertRaises(ValueError):decode_continuation(req,item,[9],FakeTokenizer(),11)

    def test_loop_is_descriptive_and_empty_not_loop(self):
        self.assertTrue(loop_heuristic('a'*7000)['loop']);self.assertFalse(loop_heuristic('')['loop'])

    def test_census_normalization_and_population_dispersion(self):
        self.assertEqual(normalized_question(' A\tB\n'),'ab')
        ratio,cv=dispersion([1,3]);self.assertEqual(ratio,3);self.assertEqual(cv,.5)
        self.assertEqual(dispersion([0,0]),(None,None))

    def test_census_insufficient_pool_is_null_not_zero(self):
        value=prefix_mass({'a':10,'b':20},sizes=(2,3))
        self.assertEqual(value['2']['one_pass_supervised_tokens_including_EOS'],30)
        self.assertIsNone(value['3']['one_pass_supervised_tokens_including_EOS'])


if __name__=='__main__':unittest.main()
