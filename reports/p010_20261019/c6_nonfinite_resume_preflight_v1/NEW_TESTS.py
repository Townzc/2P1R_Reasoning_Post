import unittest,tempfile
from pathlib import Path
from experiments.p010.common import dump,read,digest
from experiments.p010.cue_answer_key_nonfinite import answer_key
from experiments.p010.cue_key_resume import resume_rows,FAILED_KEY

class KeyTests(unittest.TestCase):
 def test_signed_infinities_are_distinct_observed_symbols(self):
  self.assertEqual(answer_key(r'\boxed{\infty}',lambda _: [float('inf'),r'\infty']),'symbolic:+infinity')
  self.assertEqual(answer_key(r'\boxed{-\infty}',lambda _: [float('-inf'),r'-\infty']),'symbolic:-infinity')
 def test_nan_remains_failure(self):
  with self.assertRaises(ValueError):answer_key(r'\boxed{x}',lambda _: [float('nan'),'NaN'])
 def test_finite_zero_and_rounding_unchanged(self):
  self.assertEqual(answer_key(r'\boxed{x}',lambda _: [-0.,'0']),'number:0.0')
  self.assertEqual(answer_key(r'\boxed{x}',lambda _: [1.1234567,'x']),'number:1.123457')
 def test_parser_exceptions_not_missing(self):
  def parse(_):raise RuntimeError('tool')
  with self.assertRaises(RuntimeError):answer_key(r'\boxed{x}',parse)
 def test_text_and_missing_unchanged(self):
  self.assertEqual(answer_key(r'\boxed{x}',lambda _: [object(),'x']),'text:x')
  self.assertIsNone(answer_key('none',lambda _: self.fail('must not parse')))

def fixture(root):
 decoded=[];key=digest(dict(extracted_answer='1'));cache={key:dict(answer_key='number:1.0',status='confirmed',pair_id=key)}
 for i in range(10080):decoded.append(dict(candidate_id=str(i),problem_id='p'+str(i%30),candidate=i//480,rollout=i%16,stop=dict(answer_segment=r'\boxed{1}',stop_reason='native_eos')))
 for first in range(0,3700,100):
  batch=[dict(**{k:row[k] for k in ('candidate_id','problem_id','candidate','rollout')},stop_reason='native_eos',**cache[key],cached=True) for row in decoded[first:first+100]]
  dump(root/'grouping/confirmed_batches'/f'{first:05d}.json',batch)
 decoded[3700]['stop']['answer_segment']=r'\boxed{\infty}'
 return decoded,cache

class FakePool:
 instances=[]
 def __init__(self,out,deadline,confirmed):self.cache=dict(confirmed);self.count=0;self.calls=0;self.closed=False;self.instances.append(self)
 def one(self,text):
  self.calls+=1;answer=r'\infty' if 'infty' in text else '1';key=digest(dict(extracted_answer=answer))
  if key in self.cache:return dict(**self.cache[key],cached=True)
  self.count+=1;v=dict(answer_key='symbolic:+infinity',status='confirmed',pair_id=key);self.cache[key]=v;return dict(**v,cached=False)
 def close(self,kill=False):self.closed=True

class ResumeTests(unittest.TestCase):
 def test_confirmed_batches_and_keys_reused_only_suffix_newkey_parsed(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);rows,cache=fixture(p/'prior');v=resume_rows(rows,p/'prior',p/'out',10**12,pool_factory=FakePool,prior_loader=lambda _:cache)
   pool=FakePool.instances[-1];self.assertEqual(pool.calls,6380);self.assertEqual(pool.count,1);self.assertEqual(len(v),10080);self.assertTrue(pool.closed)
   self.assertEqual(read(p/'out/grouping.json') if (p/'out/grouping.json').exists() else read(p/'out/COMPLETED.json')['repeated_confirmed_parser_attempts'],0)
 def test_incomplete_old_batches_rejected_before_new_output(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);rows,cache=fixture(p/'prior');(p/'prior/grouping/confirmed_batches/00000.json').unlink()
   with self.assertRaises(ValueError):resume_rows(rows,p/'prior',p/'out',10**12,pool_factory=FakePool,prior_loader=lambda _:cache)
   self.assertFalse((p/'out').exists())
 def test_new_failure_preserves_partial_and_no_retry(self):
  class Broken(FakePool):
   def one(self,text):raise TimeoutError('new attempt')
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);rows,cache=fixture(p/'prior')
   with self.assertRaises(TimeoutError):resume_rows(rows,p/'prior',p/'out',10**12,pool_factory=Broken,prior_loader=lambda _:cache)
   self.assertFalse(read(p/'out/FAILED.json')['automatic_retry']);self.assertTrue((p/'out/INHERITED_CONFIRMED.json').exists())

if __name__=='__main__':unittest.main()
