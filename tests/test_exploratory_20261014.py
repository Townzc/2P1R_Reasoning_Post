"""New selection, native-EOS, input and once-only authorization boundaries."""
import copy
import unittest
from experiments.sft_exploratory_20261014.contract import wrong_candidates, RUNS, validate_spec, make_plan
from experiments.sft_allocation_midpoint.guard import RunGuard, GuardError
from experiments.sft_allocation_midpoint.common import digest


def record(pid='b',attempt=1,**changes):
    r=dict(problem_id=pid,attempt=attempt,candidate_id=f'd1::{pid}::{attempt}',
        normalized_text_sha256=f'{pid}{attempt}',duplicate_of=None,
        score=dict(version='marked_answer_v1',status='parsed',answer_correct=False),
        stop=dict(eos=True,truncated=False,token_ids=[12,151645]))
    r.update(changes);return r


class Selection(unittest.TestCase):
    def select(self,records):return wrong_candidates({r['candidate_id']:r for r in records},['b','a'])
    def test_order(self):
        out,n=self.select([record('a'),record('b',2),record('b')])
        self.assertEqual([(r['problem_id'],r['attempt']) for r in out],[('b',1),('b',2),('a',1)])
    def test_excludes_capped_unparsed_correct(self):
        r=[record('b',i) for i in range(1,5)]
        r[0]['stop'].update(eos=False,truncated=True);r[1]['score']['status']='missing';r[2]['score']['answer_correct']=True
        self.assertEqual([x['attempt'] for x in self.select(r)[0]],[4])
    def test_duplicate_first_wrong_retained(self):
        first=record();second=record(attempt=2,normalized_text_sha256=first['normalized_text_sha256'],duplicate_of=first['candidate_id'])
        self.assertEqual(self.select([second,first])[0],[first])
    def test_duplicate_pointer_mutation_rejected(self):
        with self.assertRaises(ValueError):self.select([record(duplicate_of='fabricated')])
    def test_first429_and_shortfall(self):
        rows=[record('b',i) for i in range(1,501)];selected,n=self.select(rows)
        self.assertEqual((len(selected),n,selected[-1]['attempt']),(429,500,429))
        self.assertEqual(len(self.select(rows[:3])[0]),3)
    def test_foreign_parent(self):
        with self.assertRaises(ValueError):self.select([record('foreign')])


class Memory:
    def __init__(self):self.data={}
    def get(self,k,default=None):return self.data.get(k,default)
    def put(self,k,v,skip_if_exists=False):
        if skip_if_exists and k in self.data:return False
        self.data[k]=copy.deepcopy(v);return True


class Guards(unittest.TestCase):
    def test_three_single_use_slots(self):
        plan=dict(campaign_id='new-exploratory',created_epoch=100,deadline_epoch=10000,total_cap_cents=3000,
            stage_caps_cents={'new':3000},slots={r:dict(stage='new',reserved_cents=826) for r in RUNS})
        db=Memory();g=RunGuard(db,plan);g.register(now_epoch=101)
        intent=dict(run_id=RUNS[0],config_sha256='a'*64,source_sha256='b'*64,data_sha256='c'*64)
        g.admit(intent,attempt_id='once',now_epoch=102,max_runtime_seconds=6031)
        with self.assertRaises(GuardError):g.admit(intent,attempt_id='again',now_epoch=103,max_runtime_seconds=6031)
        with self.assertRaises(GuardError):g.admit({**intent,'run_id':'fourth'},attempt_id='new',now_epoch=103,max_runtime_seconds=6031)
    def test_exact_spec_cap(self):
        plan={'slots':{r:dict(reserved_cents=826) for r in RUNS}}
        configs={r:dict(run_id=r,max_seconds=6001) for r in RUNS}
        spec=dict(exploratory=True,preregistered=False,total_cap_cents=3000,plan=plan,configs=configs,source_files={})
        validate_spec(spec,plan,configs[RUNS[0]],{})
        changed=copy.deepcopy(spec);changed['configs'][RUNS[1]]['max_seconds']=6002
        with self.assertRaises(ValueError):validate_spec(changed,plan,configs[RUNS[0]],{})


class NativeStop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from transformers import AutoTokenizer
        cls.tok=AutoTokenizer.from_pretrained('.local/exploratory_20261014/r1/metadata',local_files_only=True)
    def test_both_official_eos(self):
        from experiments.sft_exploratory_20261014.runtime import reference_event
        text=self.tok('The answer is \\boxed{2}.',add_special_tokens=False)['input_ids']
        for eos in (151645,151643):
            e=reference_event(text+[eos],self.tok,[151645,151643]);self.assertEqual(e['stop_reason'],'native_eos')
    def test_length_cap_still_incorrect(self):
        from analyses.completion_contract import completion_score
        e=dict(stop_reason='length_cap',retained_tokens=512,actual_eos_at_stop=False,
            answer_segment='\\boxed{2}',boundary_offset=None,trigger_text=None)
        self.assertFalse(completion_score({'answer':'2'},e)['task_answer_correct'])
    def test_alternate_eos_is_not_a_base_eos(self):
        from experiments.sft_exploratory_20261014.runtime import reference_event
        e=reference_event([151645],self.tok,[151643])
        # Use a tokenizer with the base native EOS for a genuine base contract.
        old=self.tok.eos_token;self.tok.eos_token='<|endoftext|>'
        try:self.assertEqual(reference_event([151645],self.tok,[151643])['stop_reason'],'invalid_special_token')
        finally:self.tok.eos_token=old


if __name__=='__main__':unittest.main()
