import json
from pathlib import Path
import tempfile
import unittest
from experiments.sft_allocation_acquisition.student_runtime import preflight_inputs,CELLS
from experiments.sft_allocation_acquisition.student_contract import training_rows,exact_plans
from experiments.sft_allocation_midpoint.common import dump,manifest
from tests.test_acquisition_students import CharacterTokenizer,parent,candidate

class AllCellPreflightTests(unittest.TestCase):
    def build(self,root):
        tok=CharacterTokenizer()
        for cell in CELLS:
            parents=[parent(str(i)) for i in range(32)]
            records=[candidate(str(i),1) for i in range(32)]
            for i,row in enumerate(records):row['text']+='.'*i
            rows=training_rows(parents,[p['id'] for p in parents],records)
            plans=exact_plans(rows,tok)
            (root/f'{cell}_train.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            for seed,plan in plans.items():dump(root/f'{cell}_seed{seed}.json',plan)
        dump(root/'manifest.json',dict(files=manifest(root)))
        return tok

    def test_all_eight_exact_budgets_verified_without_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);tok=self.build(root)
            result=preflight_inputs(root,tok,{})
            self.assertEqual(len(result),8)
            self.assertTrue(all(r['budget']['supervised_response_tokens']==524288 for r in result.values()))

    def test_bad_future_cell_prevents_preflight_even_if_first_cell_is_good(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);tok=self.build(root)
            p=root/'depth_p4_seed23.json';r=json.loads(p.read_text());r['updates'][0].append(0);p.write_text(json.dumps(r))
            # Rehashing the corpus cannot excuse unequal training targets.
            files=manifest(root);files.pop('manifest.json')
            (root/'manifest.json').write_text(json.dumps(dict(files=files)))
            with self.assertRaises(ValueError):preflight_inputs(root,tok,{})

if __name__=='__main__':unittest.main()
