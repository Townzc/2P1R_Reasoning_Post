from contextlib import nullcontext
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import torch

from experiments.public_math_pilot_v1 import runtime_common as rc


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


if __name__=='__main__':unittest.main()
