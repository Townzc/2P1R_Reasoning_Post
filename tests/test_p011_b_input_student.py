"""New B consumer/identity fixtures only; no original production inputs/weights."""
import ast
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from experiments.p011 import b_input_path as b, b_student_training as t
from experiments.p011.short_generation import b_selection
from experiments.p010.common import dump, sha, digest, read


def fixture(failed=1):
    ids=[f'q{i:03d}' for i in range(400)]
    pack={'ordered400':ids,'source':{pid:{'problem':'question '+pid} for pid in ids}}
    records={}
    for i,pid in enumerate(ids):
        for a in range(1,17):
            cid=f'{pid}::attempt{a:02d}';ok=i>=failed and a>1
            records[cid]={'candidate_id':cid,'problem_id':pid,'attempt':a,
                'answer_text':f'answer{a}', 'stop':{'stop_reason':'native_eos'},
                'score':{'score':{'box_extracted':True,'parsed':True,'correct':ok}},'usable':ok}
    return pack,records,b_selection(ids,records)


def authority(root):
    owner=Path(b.OWNER_PATH);(root/owner).parent.mkdir(parents=True)
    (root/owner).write_bytes(owner.read_bytes())
    report=root/'synthetic_report.txt';report.write_text('synthetic only, never actual acceptance')
    binding={'source_files':{b.OWNER_PATH:b.OWNER_SHA}}
    review={'scope':'p011-B-generation-student-complete-path-CR','decision':'PASS',
        'source_files':binding['source_files'],'owner_B16_sha256':b.OWNER_SHA,
        'input_preparation_authorized':True,'target_commit':'a'*40,
        'local_report_path':str(report),'report_sha256':sha(report)}
    return binding,review


def fake_encode(row, tok, maxlen):
    return {'problem_id':row['problem_id'],'path_id':row['path_id'],
            'input_ids':[1,2,151643],'labels':[-100,2,151643]}


class NewBInputsAndStudent(unittest.TestCase):
    def test_owner_exception_retains400_K1_but399_K4_without_silent_fill(self):
        pack,records,selection=fixture()
        one=b.selected_training_rows(pack,records,selection,1)
        four=b.selected_training_rows(pack,records,selection,4)
        self.assertEqual(len(one),400);self.assertEqual(len(four),399*4)
        self.assertTrue(one[0]['unverified_fallback'])
        self.assertNotIn('q000',{r['problem_id'] for r in four})
        self.assertEqual(four[0]['path_id'],'q001::attempt02')

    def test_over10pct_or_altered_selection_is_blocked_before_encoding(self):
        pack,records,selection=fixture(41)
        with self.assertRaisesRegex(ValueError,'10percent'):b.selected_training_rows(pack,records,selection,1)
        pack,records,selection=fixture();selection['selected_ids']['1'][0]='foreign'
        with self.assertRaisesRegex(ValueError,'selection'):b.selected_training_rows(pack,records,selection,1)

    def test_missing_full_source_authority_blocks_before_projection_fence(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as tmp:
            root=Path(tmp)
            with self.assertRaises(ValueError):b.generate_inputs(root,{'source_files':{}},{})
            self.assertFalse((root/b.LOCAL/'B_GENERATION_INPUT_ATTEMPT.json').exists())

    def test_generation_input_failure_retains_fence_and_partial_no_retry(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as tmp:
            root=Path(tmp);binding,review=authority(root);binding['original_input_files']={}
            for name in b.ORIGINAL_INPUTS.values():
                path=root/name;dump(path,{'synthetic':True});binding['original_input_files'][name]=sha(path)
            with patch.object(b,'original_inputs',side_effect=RuntimeError('synthetic projection failure')):
                with self.assertRaises(RuntimeError):b.generate_inputs(root,binding,review)
            self.assertTrue((root/b.LOCAL/'b_generation_inputs_r1/FAILED.json').exists())
            with self.assertRaisesRegex(ValueError,'already attempted'):b.generate_inputs(root,binding,review)

    def test_unique_new_encoding_reused_across_three_cells_and_replay_refused(self):
        pack,records,selection=fixture()
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as tmp:
            root=Path(tmp);binding,review=authority(root);proof=root/'new_full_proof.json';dump(proof,{'synthetic_complete':True})
            binding.update(complete_new_raw_and_score_proof=True,new_raw_outputs=6400,technical_unknown=0,
                records_sha256=digest(records),selection_sha256=digest(selection),
                actual_result_evidence_files={'new_full_proof.json':sha(proof)})
            tok=type('Tok',(),{'eos_token_id':151643})()
            with patch.object(b,'encode_row',side_effect=fake_encode) as encoder,patch.object(b,'make_plan',return_value={'synthetic_plan':True}):
                out=b.student_inputs(root,pack,records,selection,tok,binding,review)
            self.assertEqual(encoder.call_count,399*8+1)
            self.assertEqual(read(out/'B2/config.json')['P_cov'],399)
            self.assertEqual(read(out/'B1/config.json')['P_cov'],400)
            self.assertEqual(read(out/'B2/encoded.json')[0],read(out/'B3/encoded.json')[0])
            with self.assertRaisesRegex(ValueError,'already attempted'):
                b.student_inputs(root,pack,records,selection,tok,binding,review)

    def test_failed_new_encoding_never_erases_confirmed_prefix(self):
        pack,records,selection=fixture()
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as tmp:
            root=Path(tmp);binding,review=authority(root);proof=root/'proof.json';dump(proof,{})
            binding.update(complete_new_raw_and_score_proof=True,new_raw_outputs=6400,technical_unknown=0,
                records_sha256=digest(records),selection_sha256=digest(selection),
                actual_result_evidence_files={'proof.json':sha(proof)})
            calls=[]
            def broken(row,tok,cap):
                calls.append(row['path_id'])
                if len(calls)==2:raise ValueError('synthetic second-answer failure')
                return fake_encode(row,tok,cap)
            with patch.object(b,'encode_row',side_effect=broken):
                with self.assertRaisesRegex(ValueError,'second-answer'):
                    b.student_inputs(root,pack,records,selection,type('Tok',(),{'eos_token_id':151643})(),binding,review)
            out=root/b.LOCAL/'b_student_inputs_r1'
            self.assertEqual(read(out/'FAILED.json')['confirmed_unique_encodings'],1)
            self.assertTrue((out/'unique_encoded/00000.json').exists());self.assertFalse((out/'COMPLETED.json').exists())

    def test_B_recipe_accepts_explicit_covered_parent_exception_rejects_seed_and_foreign_cell(self):
        pack,records,selection=fixture();rows=b.selected_training_rows(pack,records,selection,4)
        encoded=[fake_encode(r,None,2048) for r in rows];plan={'fixture':True}
        config=b.student_config('B2',4,pack,selection,rows,encoded,plan)
        with patch.object(t,'validate_plan',return_value={'fixture':'exact dose check stub'}) as check:
            recipe=t.checked_recipe(config,encoded,plan);self.assertEqual(recipe['cell']['P_cov'],399)
            check.assert_called_once_with(encoded,plan,17,151643)
            for field,value in [('seed',29),('run_id','t15_s17_n400_k4'),('P_cov',400)]:
                bad=copy.deepcopy(config);bad[field]=value
                with self.assertRaises(ValueError):t.checked_recipe(bad,encoded,plan)

    def test_original_training_body_AST_unchanged_no_original_module_mutation(self):
        def body(path):
            tree=ast.parse(Path(path).read_text())
            return ast.dump(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='train_and_merge'),include_attributes=False)
        self.assertEqual(body('experiments/p010/student_training.py'),body('experiments/p011/b_student_training.py'))


if __name__=='__main__':unittest.main()
