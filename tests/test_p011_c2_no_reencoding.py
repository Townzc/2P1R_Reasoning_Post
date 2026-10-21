"""Only two newly changed boundaries; no prior successful test is repeated."""
import ast,json,tempfile,unittest
from pathlib import Path
from experiments.p011.c2_input_path import read_physical_jsonl

class NewC2Boundaries(unittest.TestCase):
    def test_training_reuses_fixed_token_sequences_and_other_training_body_exact(self):
        def function(path):
            return next(n for n in ast.parse(Path(path).read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='train_and_merge')
        old=function('experiments/p011/b_student_training.py');new=function('experiments/p011/c2_student_training.py')
        source=ast.unparse(new)
        self.assertNotIn('rt.encode(',source);self.assertIn('checked_encoding(row, item)',source)
        # Remove only the old re-encode conditional and the new preserved-structure
        # check; every actual model/update/state/merge statement remains identical.
        old.body=[n for n in old.body if not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='actual_encoded' for t in n.targets)) and not (isinstance(n,ast.If) and 'actual_encoded' in ast.unparse(n.test))]
        new.body=[n for n in new.body if not (isinstance(n,ast.ImportFrom) and n.module=='experiments.p011.c2_student_inputs') and not (isinstance(n,ast.For) and 'checked_encoding' in ast.unparse(n))]
        self.assertEqual(ast.dump(old,include_attributes=False),ast.dump(new,include_attributes=False))

    def test_json_strings_keep_unicode_line_separators(self):
        value={'prompt':'part\u2028still one row\u2029end'}
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'fixture.jsonl';p.write_text(json.dumps(value,ensure_ascii=False)+'\n')
            self.assertEqual(read_physical_jsonl(p),[value])

if __name__=='__main__':unittest.main()
