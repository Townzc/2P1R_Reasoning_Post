from contextlib import nullcontext
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import torch

from experiments.public_math_pilot_v1 import runtime_common as rc
from experiments.public_math_pilot_v1 import runtime_train as rt
from experiments.public_math_pilot_v1.runtime_evaluate import evaluation_jobs


class Tokenizer:
    def decode(self, tokens, skip_special_tokens=False):
        return ''.join('<|im_end|>' if t==151645 else str(t)+' ' for t in tokens)


class Model:
    def __init__(self): self.calls=0
    def eval(self): pass
    def generate(self, input_ids, **kwargs):
        self.calls+=1
        sample=torch.randint(1,100,(len(input_ids),4))
        return torch.cat([input_ids,sample,torch.full((len(input_ids),1),151645)],dim=1)


class RuntimeTest(unittest.TestCase):
    def test_complete_evaluation_contract_has_no_extra_or_missing_draws(self):
        jobs=evaluation_jobs();self.assertEqual(len(jobs),53)
        self.assertEqual(len({j['name'] for j in jobs}),53)
        counts={'math500':500,'gsm8k':1319,'dev':512}
        self.assertEqual(sum(counts[j['dataset']] for j in jobs)+512,31203)
        for arm in ('Base',*rt.ARMS):
            math=[j for j in jobs if j['arm']==arm and j['dataset']=='math500']
            self.assertEqual([j['seed'] for j in math],list(range(2026091800,2026091808)))
            self.assertTrue(all(j['step']==(0 if arm=='Base' else 128) for j in math))
        self.assertEqual(sum(j['step']==64 for j in jobs),4)
        self.assertTrue(all(j['batch_size']==128 for j in jobs if j['dataset']=='gsm8k'))
        self.assertTrue(all(j['batch_size']==256 for j in jobs if j['dataset']=='math500'))

    def test_reservation_duplicate_and_cap_are_not_retries(self):
        with tempfile.TemporaryDirectory() as d:
            ledger=rc.PhysicalLedger(Path(d)/'ledger')
            ledger.reserve('annotation_forward',['a/full','a/blank'])
            with self.assertRaises(RuntimeError): ledger.reserve('annotation_forward',['a/full'])
            with self.assertRaises(ValueError): ledger.reserve('generation',['a','a'])
            with self.assertRaises(RuntimeError): ledger.reserve('nonformal_optimizer_update',[str(i) for i in range(9)])
            self.assertEqual(len((Path(d)/'ledger').read_text().splitlines()),2)

    def test_rng_roundtrip(self):
        torch.manual_seed(2026091800)
        state=rc.generation_rng(); a=torch.rand(20)
        rc.restore_generation_rng(state)
        self.assertTrue(torch.equal(a,torch.rand(20)))

    def test_mid_draw_resume_preserves_stream_and_no_duplicates(self):
        rows=[dict(id=str(i),prompt_ids=[10+i,2]) for i in range(33)]
        def batch(group): return dict(input_ids=torch.tensor([r['prompt_ids'] for r in group]))
        with tempfile.TemporaryDirectory() as d, \
            patch.object(rc,'generation_batch',batch), \
            patch.object(torch,'autocast',lambda *a,**k:nullcontext()), \
            patch.object(torch.cuda,'synchronize'), \
            patch.object(torch.cuda,'reset_peak_memory_stats'), \
            patch.object(torch.cuda,'max_memory_allocated',return_value=0):
            root=Path(d)
            def run(name,model):
                return rc.generate_rows(model,Tokenizer(),rows,root/name,
                    model_identity={'model_sha256':'a'*64},logical_name='MATH-draw0',
                    ledger=rc.PhysicalLedger(root/(name+'.ledger')),deadline=time.time()+3600,
                    batch_size=16,seed=2026091800)
            baseline=run('full',Model())
            partial=Model()
            with patch.object(rc,'require_time',side_effect=[None,TimeoutError('pause')]):
                with self.assertRaises(TimeoutError): run('resume',partial)
            self.assertEqual(partial.calls,1)
            continuation=Model(); resumed=run('resume',continuation)
            self.assertEqual(continuation.calls,2)
            self.assertEqual(resumed,baseline)
            complete=Model(); self.assertEqual(run('resume',complete),baseline)
            self.assertEqual(complete.calls,0)
            self.assertEqual(len((root/'resume.ledger').read_text().splitlines()),33)
            path=root/'resume'/'batch_00000.json'; bad=json.loads(path.read_text())
            bad['records'][0]['raw_text']='tampered';path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError): run('resume',Model())

    def test_unexplained_short_completion_is_error(self):
        with self.assertRaises(ValueError): rc.decode_tokens(Tokenizer(),[1,2])
        self.assertEqual(rc.decode_tokens(Tokenizer(),[1,151645,3])['generated_ids'],[1,151645])

    def test_existing_identity_is_immutable(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.json';rc.ensure_record(p,{'n':1});rc.ensure_record(p,{'n':1})
            with self.assertRaises(ValueError):rc.ensure_record(p,{'n':2})

    def test_training_interruption_restores_actual_model_optimizer_and_rng(self):
        class Tiny(torch.nn.Module):
            def __init__(self):
                super().__init__();self.embed=torch.nn.Embedding(4,5);self.drop=torch.nn.Dropout(.2)
                self.head=torch.nn.Linear(5,4)
            def forward(self,input_ids,use_cache=False):
                return SimpleNamespace(logits=self.head(self.drop(self.embed(input_ids))))
        rows=[dict(problem_id=str(i),response_ids=[1,2]) for i in range(4096)]
        batches=rt.frozen_batches(rows)
        self.assertEqual(len({x['problem_id'] for b in batches for x in b}),4096)
        contract=rt.training_contract({'model_sha256':'a'*64},batches,'b'*64,[.001]*127+[0.])
        masks={r['problem_id']:[False,False] for r in rows}
        def load(*a,**kw):
            torch.manual_seed(17);return Tiny().train()
        def batch(two,masks=None):
            ids=torch.tensor([[int(r['problem_id'])%4,1,2] for r in two])
            labels=torch.tensor([[-100,1,2]]*len(two))
            return {'input_ids':ids},labels,torch.zeros_like(labels,dtype=torch.bool)
        # Exercise the production loop and real SFT gradients, injecting only tiny
        # CPU model/collation/hardware seams. Checkpoint serialization stays real.
        with tempfile.TemporaryDirectory() as d,redirect_stdout(io.StringIO()), \
            patch.object(rt,'load_base',load),patch.object(rt,'training_batch',batch), \
            patch.object(torch,'autocast',lambda *a,**k:nullcontext()), \
            patch.object(torch.cuda,'synchronize'),patch.object(torch.cuda,'reset_peak_memory_stats'), \
            patch.object(torch.cuda,'max_memory_allocated',return_value=0), \
            patch.object(rt,'host_available_bytes',return_value=100*2**30):
            # Production loss receives attention_mask; no padding in this toy.
            original=rt.compute_loss
            def toy_batch(two,masks=None):
                inputs,labels,qmask=batch(two,masks)
                inputs['attention_mask']=torch.ones_like(inputs['input_ids'])
                return inputs,labels,qmask
            def forward(self,input_ids,attention_mask=None,use_cache=False):
                return SimpleNamespace(logits=self.head(self.drop(self.embed(input_ids))))
            with patch.object(rt,'training_batch',toy_batch),patch.object(Tiny,'forward',forward):
                def args(name):
                    return SimpleNamespace(output=str(Path(d)/name),volume_root=[str(Path(d)/'vol')],
                        base='tiny',source_commit='test',deadline_unix=time.time()+3600)
                first=args('full');rt.train_arm(first,contract,batches,masks,'SFT')
                one=rt.store_for(first.output,first.volume_root,contract,'SFT').load_latest()
                # Different owned volume for independent run of the same arm.
                resumed=args('resume');resumed.volume_root=[str(Path(d)/'vol2')]
                def pause_after37(*a,**kw):
                    return len(list((Path(resumed.output)/'training').glob('SFT/*/*.completed.json')))>=37
                with patch.object(rt,'stop_due',pause_after37):
                    self.assertEqual(rt.train_arm(resumed,contract,batches,masks,'SFT')['step'],37)
                rt.train_arm(resumed,contract,batches,masks,'SFT')
                store=rt.store_for(resumed.output,resumed.volume_root,contract,'SFT');two=store.load_latest()
                self.assertEqual(two['step'],128)
                from experiments.public_math_pilot_v1.checkpoints import _same
                self.assertTrue(_same(one['model_state'],two['model_state']))
                self.assertTrue(_same(one['optimizer_state'],two['optimizer_state']))
                self.assertTrue(_same(one['rng_state'],two['rng_state']))
                self.assertEqual([m['step'] for m in rt.manifests_for(store)],[128,96,64,37,32])
                corrupted=list(two['metadata']['history']);corrupted[0]=dict(corrupted[0],learning_rate=.02)
                with self.assertRaises(ValueError):rt.validate_history(corrupted,contract,'SFT',128)


if __name__=='__main__':unittest.main()
