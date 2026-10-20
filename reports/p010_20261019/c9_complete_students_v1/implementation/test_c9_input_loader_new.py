import json,tempfile,unittest
from pathlib import Path
from scripts.analyze_p010_completed_students import checked_table,load
from experiments.p010.common import sha
class NewLoaderChecks(unittest.TestCase):
 def test_question_order(self):
  self.assertEqual(checked_table({'b':True,'a':False},['a','b'],1),[False,True])
 def test_no_missing_zero_imputation_or_numeric_labels(self):
  for table,ids,count in [({'a':True},['a','b'],1),({'a':1},['a'],1),({'a':False},['a','a'],0),({'a':True},['a'],0)]:
   with self.assertRaises(ValueError):checked_table(table,ids,count)
 def test_immutable_bytes_bound(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'outcome.json';p.write_text('{"correct":1}\n')
   m={'bytes':p.stat().st_size,'sha256':sha(p)};(p.parent/'MANIFEST.json').write_text(json.dumps({p.name:m}))
   binding={};self.assertEqual(load(p,binding),{'correct':1});self.assertEqual(binding[str(p)],m)
   p.write_text('{"correct":2}\n')
   with self.assertRaises(ValueError):load(p,{})
if __name__=='__main__':unittest.main()
