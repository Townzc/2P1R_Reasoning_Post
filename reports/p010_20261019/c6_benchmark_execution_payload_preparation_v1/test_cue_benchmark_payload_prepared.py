import importlib.util,unittest
from pathlib import Path
p=Path('.local/p010_20261019/r1/cue_benchmark_payload_prepared.py')
s=importlib.util.spec_from_file_location('payload',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tokenizer:
 def decode(self,ids,**kwargs):return ''.join({1:'\\boxed{',2:'7}',3:'x',151643:'<|endoftext|>'}.get(t,'?') for t in ids)

def make(task='math'):
 cap=1024 if task=='math' else 512
 row=dict(candidate_id='cue/greedy/'+task+'/0',problem_id=task+'/0',source_row_sha256='a'*64,
  input_ids=[10,1],original_input_ids=[10],cue_token_ids=[1],sampling=dict(max_tokens=cap))
 item=dict(candidate_id=row['candidate_id'],problem_id=row['problem_id'],source_row_sha256=row['source_row_sha256'],
  prompt_token_ids=row['input_ids'],sampling=row['sampling'],output_count=1,backend_text='7}',
  token_ids=[2,151643],finish_reason='stop',stop_reason=151643)
 return row,item
class Payload(unittest.TestCase):
 def test_forced_prefix_is_part_of_answer(self):
  r,i=make();v,u=m.decode(r,i,Tokenizer(),{1,2,3,10,151643},(151643,))
  self.assertIn('\\boxed{7}',v['answer_segment']);self.assertFalse(u)
 def test_both_exact_cap_native_eos_boundaries(self):
  for task,cap in [('math',1024),('gsm',512)]:
   r,i=make(task);i.update(token_ids=[3]*(cap-1)+[151643],finish_reason='length',stop_reason=None)
   v,u=m.decode(r,i,Tokenizer(),{1,2,3,10,151643},(151643,));self.assertEqual(v['stop_reason'],'native_eos')
 def test_short_missing_eos_rejected(self):
  r,i=make();i['token_ids']=[2]
  with self.assertRaises(ValueError):m.decode(r,i,Tokenizer(),{1,2,3,10,151643},(151643,))
 def test_no_silent_prompt_or_parameter_change(self):
  r,i=make();i['prompt_token_ids']=[10]
  with self.assertRaises(ValueError):m.decode(r,i,Tokenizer(),{1,2,3,10,151643},(151643,))
 def test_padding_ids_only_in_retained_full_cap(self):
  r,i=make();i.update(token_ids=[151900]*1024,finish_reason='length',stop_reason=None)
  v,u=m.decode(r,i,Tokenizer(),{1,2,3,10,151643},(151643,));self.assertEqual(u,[151900]);self.assertEqual(v['stop_reason'],'length_cap')
  i['token_ids']=[151900,151643];i.update(finish_reason='stop',stop_reason=151643)
  with self.assertRaises(ValueError):m.decode(r,i,Tokenizer(),{1,2,3,10,151643},(151643,))
 def test_exact_named_record_roster_no_global_scan(self):
  keys=m.record_keys('base_gsm',11871);self.assertEqual(len(keys),96);self.assertEqual(len(keys),len(set(keys)))
  with self.assertRaises(ValueError):m.record_keys('s1_n400_math',0)
if __name__=='__main__':unittest.main()
