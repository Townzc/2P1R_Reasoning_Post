"""New child proof tests; fake tokens only, no original outputs or state loads."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from experiments.p010.common import read, dump, digest
from experiments.p010.e4_endpoint_contract import sampling, forecast
from experiments.p010.e4_endpoint_evidence import decode, record_keys, verify_endpoint
from analyses.completion_contract import completion_score


class Tokenizer:
    all_special_ids = [100257, 100278]
    def get_vocab(self): return {'answer': 1, 'eos': 100257, 'special': 100278}
    def decode(self, ids, **kwargs): return '#### 1' if ids else ''


def raw(row):
    return dict(problem_id=row['problem_id'],candidate_id=None,source_row_sha256=None,
        prompt_token_ids=row['input_ids'],sampling=sampling(),output_count=1,
        backend_text='#### 1',token_ids=[1,100257],finish_reason='stop',stop_reason=100257)


def fixture(root):
    rows=[dict(problem_id=f'gsm8k/test/{i:05d}',input_ids=[2,i+10]) for i in range(1319)]
    wrapper=dict(n=1319,max_context=2048,max_new_tokens=512,eos_token_id=100257,prompts=rows)
    engine=dict(max_model_len=2048,enforce_eager=False,dtype='torch.bfloat16',max_num_seqs=256,
        max_num_batched_tokens=8192,enable_chunked_prefill=True,enable_prefix_caching=False,
        gpu_memory_utilization=.8,compilation_level=3,cudagraph_mode='FULL_AND_PIECEWISE',
        cudagraph_capture_sizes=[1,2,4,8,16,32,64,128,256])
    run='e4_s17_n400';ledger={};times=[1.]*6
    dump(root/'ENGINE.json',engine)
    dump(root/'RESULT.json',dict(run=run,raw_endpoint_count=1319,new_training_updates=0,
        original_training_updates=1024,original_targets=2097148,
        original_failed_parent_remains_failed=True,eval_batch_seconds=times))
    dump(root/'BEFORE_MODEL_FORECAST.json',forecast(0,0,[],'26.20'))
    for index,offset in enumerate(range(0,1319,256)):
        part=rows[offset:offset+256];unit=f'{offset:04d}';batch=[raw(r) for r in part]
        intent=dict(rows=part,sampling=[sampling() for _ in part],epoch=index+100)
        ack=dict(count=len(part),seconds=1.,raw_sha256=digest(batch))
        for folder,value in [('raw',batch),('eval_intents',intent),('eval_acks',ack),
                             ('eval_forecasts',forecast(index,index,times[:index],'26.20'))]:
            dump(root/folder/(unit+'.json'),value)
        ledger['e4_endpoint_only/'+run+'/eval/'+unit]=intent
        ledger['e4_endpoint_only/'+run+'/eval_done/'+unit]=ack
    return wrapper,ledger,{r['problem_id']:{'answer':'1'} for r in rows}


class ChildProof(unittest.TestCase):
    def test_complete_original_roster_six_batches_and_one_hash_each(self):
        import experiments.p010.e4_endpoint_evidence as module
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);wrapper,ledger,gold=fixture(root)
            with patch.object(module,'sha',wraps=module.sha) as hashes:
                value=verify_endpoint(root,wrapper,ledger,'e4_s17_n400','26.20',Tokenizer(),gold,100352,root/'proof')
            self.assertEqual(value['correct'],1319);self.assertEqual(value['total'],1319)
            self.assertEqual(value['repeated_training_state_loads'],0)
            self.assertEqual(hashes.call_count,6)
            self.assertEqual(len(list((root/'proof/confirmed_batches').glob('*.json'))),6)

    def test_missing_final_partial_batch_rejected_before_decoding(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);wrapper,ledger,gold=fixture(root);(root/'raw/1280.json').unlink()
            with self.assertRaisesRegex(ValueError,'Missing/extra'):
                verify_endpoint(root,wrapper,ledger,'e4_s17_n400','26.20',Tokenizer(),gold,100352,root/'proof')

    def test_tampered_forecast_rejected_and_prior_confirmed_batch_retained(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);wrapper,ledger,gold=fixture(root)
            p=root/'eval_forecasts/0256.json';v=read(p);v['maximum_seconds']=0;p.unlink();dump(p,v)
            with self.assertRaisesRegex(ValueError,'binding differs'):
                verify_endpoint(root,wrapper,ledger,'e4_s17_n400','26.20',Tokenizer(),gold,100352,root/'proof')
            self.assertTrue((root/'proof/confirmed_batches/0000.json').exists())
            self.assertFalse((root/'proof/confirmed_batches/0256.json').exists())

    def test_native_eos_at_cap_preserves_backend_and_true_cap_is_wrong(self):
        row=dict(problem_id='q',input_ids=[2]);item=raw(row)
        item.update(token_ids=[1]*511+[100257],finish_reason='length',stop_reason=None)
        before=deepcopy(item);args=(Tokenizer(),{1,100257,100278},[100257,100278],100352)
        event=decode(row,item,*args);self.assertEqual(item,before)
        self.assertTrue(completion_score({'answer':'1'},event)['task_answer_correct'])
        item['token_ids']=[1]*512;event=decode(row,item,*args)
        self.assertEqual(event['stop_reason'],'length_cap')
        self.assertFalse(completion_score({'answer':'1'},event)['task_answer_correct'])

    def test_unknown_token_is_not_silently_zero_or_fake_eos(self):
        row=dict(problem_id='q',input_ids=[2]);item=raw(row);item['token_ids']=[100300,100257]
        with self.assertRaisesRegex(ValueError,'Unknown token'):
            decode(row,item,Tokenizer(),{1,100257,100278},[100257,100278],100352)

    def test_foreign_prompt_or_interior_eos_or_short_length_rejected(self):
        row=dict(problem_id='q',input_ids=[2]);items=[]
        x=raw(row);x['prompt_token_ids']=[3];items.append(x)
        x=raw(row);x['token_ids']=[100257,1];items.append(x)
        x=raw(row);x.update(token_ids=[1],finish_reason='length',stop_reason=None);items.append(x)
        for item in items:
            with self.assertRaises(ValueError):
                decode(row,item,Tokenizer(),{1,100257,100278},[100257,100278],100352)

    def test_ledger_roster_keeps_both_failed_parent_and_completed_child(self):
        keys=record_keys('e4_s17_n3200');self.assertEqual(len(keys),29);self.assertEqual(len(set(keys)),29)
        self.assertIn('e4/e4_s17_n3200/terminal',keys)
        self.assertIn('e4_endpoint_only/e4_s17_n3200/eval_done/1280',keys)
        with self.assertRaises(ValueError):record_keys('new_arm')


if __name__=='__main__':unittest.main()
