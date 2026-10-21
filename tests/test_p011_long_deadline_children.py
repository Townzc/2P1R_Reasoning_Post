import unittest
from experiments.p011.long_path import terminate_owned_descendants
class OwnedChildren(unittest.TestCase):
 def test_descendants_only_leaf_first(self):
  tree={10:[11,12],11:[13],12:[],13:[]};k=[]
  result=terminate_owned_descendants(10,lambda p:tree[p],k.append)
  self.assertEqual(result,[13,11,12]);self.assertEqual(k,result);self.assertNotIn(10,k)
 def test_gone_child_preserved_as_observed_not_retry(self):
  seen=[]
  def kill(p):seen.append(p);raise ProcessLookupError()
  self.assertEqual(terminate_owned_descendants(1,lambda p:[2] if p==1 else [],kill),[2]);self.assertEqual(seen,[2])
if __name__=='__main__':unittest.main()
