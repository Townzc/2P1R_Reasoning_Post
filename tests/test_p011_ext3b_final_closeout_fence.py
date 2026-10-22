import ast
from pathlib import Path
import unittest
class FinalCloseoutFence(unittest.TestCase):
 def test_both_resume_authorization_and_dispatch_refuse_started_final_collection(self):
  for name in ['scripts/prepare_p011_ext4b_infra_resume.py','experiments/p011/ext4b_path.py']:
   tree=ast.parse(Path(name).read_text())
   guards=[n for n in ast.walk(tree) if isinstance(n,ast.If) and "'collect'" in ast.unparse(n.test) and '.exists()' in ast.unparse(n.test)]
   self.assertTrue(guards,name);self.assertTrue(any(isinstance(k,ast.Raise) for g in guards for k in g.body),name)
if __name__=='__main__':unittest.main()
