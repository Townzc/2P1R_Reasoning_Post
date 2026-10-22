import ast
from pathlib import Path
from unittest.mock import patch
import unittest
from experiments.p011 import ext3b_math_score_process as process
class ScoreChildLocator(unittest.TestCase):
 def test_owned_worker_import_and_source_snapshot_use_exact_scoped_driver(self):
  self.assertEqual(process.MODULE,'experiments.p011.ext3b_math_score_process')
  self.assertEqual(process.SOURCES,('experiments/p011/ext3b_math_score_process.py','experiments/p011/ext3b_math_scoring.py'))
  tree=ast.parse(Path(process.SOURCES[0]).read_text());worker=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='owned_worker')
  imports=[n.module for n in ast.walk(worker) if isinstance(n,ast.ImportFrom)]
  self.assertEqual(imports,['experiments.p011.ext3b_math_scoring'])
  self.assertNotIn('long_d2_scope',Path(process.SOURCES[0]).read_text())
  with patch('experiments.p011.ext3b_math_scoring.checked_rows',side_effect=RuntimeError('new_scope_validated_before_fence')):
   with self.assertRaisesRegex(RuntimeError,'new_scope_validated_before_fence'):
    process.supervise_once('/unreachable-never-created',[{}]*500,{'fixture':True},1)
if __name__=='__main__':unittest.main()
