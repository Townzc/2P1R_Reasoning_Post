import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_p011_c2_reuse_projection import NewC2Reuse
from experiments.p011 import c2_input_path as mod
from experiments.sft_allocation_midpoint.common import digest

class NewConsumerChecks(unittest.TestCase):
 def setup_files(self,root):
  values=dict(zip(('roster','source','requests','t72_index','t15_index','p1_rows','p1_scored'),NewC2Reuse().fixture()))
  for k,n in mod.FILES.items():
   p=root/n;p.parent.mkdir(parents=True,exist_ok=True);x=values[k]
   p.write_text(''.join(json.dumps(y)+'\n' for y in x) if n.endswith('.jsonl') else json.dumps(x))
  for n in mod.EVIDENCE:
   p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'provider_stopped':True}))
  (root/mod.EVIDENCE[2]).write_text(json.dumps({'source_order_sha256':digest(values['roster']['e1d_order']),'examined_prefix_count':401}))
  return {'window_size':2,'original_reuse_files':{},'original_acceptance_files':{}}
 def test_one_reuse_no_raw_decoder_and_gold_free_gpu(self):
  with tempfile.TemporaryDirectory() as t,patch.object(mod,'authority'),patch.object(mod.time,'time',return_value=1792600000):
   r=Path(t);b=self.setup_files(r);out=mod.prepare(r,b,{})
   pack=json.loads((out/'GPU_PACK.json').read_text());self.assertEqual(len(pack['plan']['new_requests']),6)
   self.assertEqual(pack['source'],{'p0':{'problem':'q'},'p1':{'problem':'q'}})
   with self.assertRaises(ValueError):mod.prepare(r,b,{})
 def test_partial_input_error_retains_fence(self):
  with tempfile.TemporaryDirectory() as t,patch.object(mod,'authority'),patch.object(mod.time,'time',return_value=1792600000):
   r=Path(t);b=self.setup_files(r);(r/mod.FILES['p1_scored']).write_text('[]')
   with self.assertRaises(ValueError):mod.prepare(r,b,{})
   self.assertTrue((r/mod.LOCAL/'C2_GENERATION_INPUT_ATTEMPT.json').exists());self.assertTrue((r/mod.LOCAL/'c2_generation_inputs_r1/FAILED.json').exists())
   with self.assertRaises(ValueError):mod.prepare(r,b,{})
 def test_saved_unclosed_provider_refused(self):
  with tempfile.TemporaryDirectory() as t,patch.object(mod,'authority'),patch.object(mod.time,'time',return_value=1792600000):
   r=Path(t);b=self.setup_files(r);(r/mod.EVIDENCE[0]).write_text('{"provider_stopped":false}')
   with self.assertRaises(ValueError):mod.prepare(r,b,{})
 def test_expired_before_fence(self):
  with tempfile.TemporaryDirectory() as t,patch.object(mod,'authority'),patch.object(mod.time,'time',return_value=mod.CUTOFF):
   r=Path(t);b=self.setup_files(r)
   with self.assertRaises(TimeoutError):mod.prepare(r,b,{})
   self.assertFalse((r/mod.LOCAL/'C2_GENERATION_INPUT_ATTEMPT.json').exists())
 def test_missing_old_t72_produces_blocked_metadata_no_gpu(self):
  with tempfile.TemporaryDirectory() as t,patch.object(mod,'authority'),patch.object(mod.time,'time',return_value=1792600000):
   r=Path(t);b=self.setup_files(r);p=r/mod.FILES['t72_index'];x=json.loads(p.read_text());x.pop('p0::attempt01');p.write_text(json.dumps(x));out=mod.prepare(r,b,{})
   self.assertFalse((out/'GPU_PACK.json').exists());self.assertEqual(json.loads((out/'COMPLETED.json').read_text())['initial_prefix']['blocked_missing_old_T72'],'p0')

if __name__=='__main__':unittest.main()
