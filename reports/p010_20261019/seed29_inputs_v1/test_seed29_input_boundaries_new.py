import copy,unittest
from scripts.prepare_p010_seed29_inputs import check_inventory,CELLS
class Checks(unittest.TestCase):
 def setUp(self):
  self.rows=[{'problem_id':str(i),'path_id':str(i)+'/a'} for i in range(2)]
  self.encoded=[dict(x,n_processed=3,n_supervised=2,input_ids=[3,4,151643],labels=[-100,4,151643]) for x in self.rows]
 def test_exact_four_cells(self):
  self.assertEqual(set(CELLS),{'t15_s29_n400_k1','t15_s29_n3200_k1','t72_s29_n400_k1','t72_s29_n3200_k1'})
  self.assertTrue(all(x['seed']==29 and x['K']==1 for x in CELLS.values()))
 def test_unchanged_seed17_order(self):
  self.assertTrue(check_inventory(self.rows,self.encoded,2))
  with self.assertRaises(ValueError):check_inventory(self.rows,list(reversed(self.encoded)),2)
 def test_unsupported_not_truncated(self):
  e=copy.deepcopy(self.encoded);e[0]['n_processed']=2049
  with self.assertRaises(ValueError):check_inventory(self.rows,e,2)
 def test_no_drop_or_eos_substitution(self):
  with self.assertRaises(ValueError):check_inventory(self.rows[:-1],self.encoded,2)
  e=copy.deepcopy(self.encoded);e[0]['labels'][-1]=100257
  with self.assertRaises(ValueError):check_inventory(self.rows,e,2)
if __name__=='__main__':unittest.main()
