import types,unicodedata,unittest
from experiments.p011.long_evaluation import request_roster,BENCHMARK_COUNTS
from experiments.p011.long_execution import validate_endpoint
from experiments.sft_allocation_midpoint.common import digest
class Tokenizer:
 def __init__(self):self.backend_tokenizer=types.SimpleNamespace(normalizer=types.SimpleNamespace(normalize_str=lambda x:unicodedata.normalize('NFC',x)))
 def apply_chat_template(self,messages,**k):return '<user>'+messages[0]['content']+'</user><assistant>'
 def __call__(self,text,**k):return {'input_ids':list(map(ord,unicodedata.normalize('NFC',text)))}
 def decode(self,ids,**k):return ''.join(map(chr,ids))
class NativePrompt(unittest.TestCase):
 def test_native_NFC_only_goldfree_roster_preserves_raw_digest(self):
  rows=[{'benchmark':b,'source_row':i,'problem':'a\u0304','answer':'1'} for b,n in BENCHMARK_COUNTS.items() for i in range(n)]
  requests=request_roster(rows,Tokenizer());self.assertEqual(len(requests),3300)
  self.assertTrue(all(r['native_NFC_changed'] for r in requests));self.assertNotEqual(requests[0]['prompt_text_sha256'],requests[0]['raw_prompt_text_sha256'])
  gpu=[{**{k:v for k,v in r.items() if k!='gold'},'request_sha256':digest(r)} for r in requests]
  validate_endpoint(gpu,max(r['required_context'] for r in requests));self.assertNotIn('gold',gpu[0])
 def test_nonNFC_normalizer_blocked_before_roster(self):
  tok=Tokenizer();tok.backend_tokenizer.normalizer.normalize_str=lambda x:x.strip()+' altered'
  rows=[{'benchmark':b,'source_row':i,'problem':'a','answer':'1'} for b,n in BENCHMARK_COUNTS.items() for i in range(n)]
  with self.assertRaises(ValueError):request_roster(rows,tok)
if __name__=='__main__':unittest.main()
