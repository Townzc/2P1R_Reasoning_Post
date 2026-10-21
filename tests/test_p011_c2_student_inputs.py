"""New fake-data tests for the C2 old-encoding reuse constructor only."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from experiments.p010.common import digest
from experiments.p011.c2_student_inputs import original_catalog,encoding_key,construct,checked_encoding


def encoded(row):
    token=20 if row['response']=='left' else 21
    return {'input_ids':[10,token,151643],'labels':[-100,token,151643],
        'n_prompt':1,'n_supervised':2,'n_processed':3,'problem_id':row['problem_id'],
        'path_id':row['path_id'],'response_hash':hashlib.sha256(row['response'].encode()).hexdigest()}


def fixture():
    rows={run:[{'problem_id':f'p{i}','path_id':f'p{i}::attempt01','prompt':f'q{i}',
        'response':'left' if run=='C2a' else 'right','teacher':'t15' if run=='C2a' else 't72',
        'temperature':.8,'attempt':1,'saved_record_sha256':'a'*64,'unverified_fallback':False}
        for i in range(400)] for run in ('C2a','C2b')}
    selection={'complete':True,'S1_overlap':9,'selected':[{'problem_id':f'p{i}',
        't15':f'p{i}::attempt01','t72':f'p{i}::attempt01'} for i in range(400)]}
    pairs=[(run,chosen,[encoded(r) for r in chosen]) for run,chosen in rows.items()]
    catalog,sources=original_catalog(pairs)
    binding={'complete_original_and_new_saved_verdicts':True,'selection_sha256':digest(selection),
        'original_encoded_pair_files':{'fixed/rows.json':'b'*64,'fixed/encoded.json':'c'*64}}
    return rows,selection,catalog,sources,binding


class NewC2StudentInputs(unittest.TestCase):
    def test_raw_response_hash_blocks_changed_answer(self):
        row=fixture()[0]['C2a'][0];item=encoded(row);row={**row,'response':'changed'}
        with self.assertRaises(ValueError):checked_encoding(row,item)

    def test_conflicting_old_encoding_blocks_overwrite(self):
        row=fixture()[0]['C2a'][0];a=encoded(row);b=copy.deepcopy(a)
        b['input_ids'][1]=22;b['labels'][1]=22
        with self.assertRaises(ValueError):original_catalog([('a',[row],[a]),('b',[row],[b])])

    def test_teacher_metadata_does_not_force_second_encoding(self):
        row=fixture()[0]['C2a'][0]
        self.assertEqual(encoding_key(row),encoding_key({**row,'teacher':'t72'}))

    def run_fake(self,out,values,encoder):
        rows,selection,catalog,sources,binding=values
        tokenizer=type('T',(),{'eos_token_id':151643})()
        with patch('experiments.p011.c2_student_inputs.checked_recipe',lambda *args: {}):
            return construct(out,rows,selection,catalog,sources,tokenizer,binding,lambda:None,
                encoder=encoder,planner=lambda *args:{'new_plan_fixture':True})

    def test_all_old_encodings_never_call_encoder(self):
        values=fixture()
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'new';self.run_fake(out,values,lambda *args:self.fail('old encoding repeated'))
            done=json.loads((out/'COMPLETED.json').read_text())
            self.assertEqual((done['first_new_encodings'],done['reused_original_encodings']),(0,800))
            self.assertEqual(json.loads((out/'C2b/encoded.json').read_text())[0],encoded(values[0]['C2b'][0]))

    def test_only_unseen_selected_answer_encoded_once(self):
        values=fixture();row=values[0]['C2a'][7];key=encoding_key(row)
        del values[2][key];del values[3][key];calls=[]
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'new';self.run_fake(out,values,lambda r,*args:(calls.append(r['path_id']) or encoded(r)))
            self.assertEqual(calls,[row['path_id']])
            done=json.loads((out/'COMPLETED.json').read_text());self.assertEqual(done['first_new_encodings'],1)

    def test_existing_output_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):self.run_fake(Path(td),fixture(),lambda *args:self.fail())

    def test_incomplete_common_set_blocks_before_mkdir(self):
        values=fixture();values[0]['C2a'].pop()
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'new'
            with self.assertRaises(ValueError):self.run_fake(out,values,lambda *args:self.fail())
            self.assertFalse(out.exists())

    def test_new_encoder_failure_preserves_confirmed_prefix(self):
        values=fixture();key=encoding_key(values[0]['C2a'][7]);del values[2][key];del values[3][key]
        def fail(*args):raise RuntimeError('new answer failure')
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'new'
            with self.assertRaises(RuntimeError):self.run_fake(out,values,fail)
            failed=json.loads((out/'FAILED.json').read_text())
            self.assertEqual(failed['confirmed_unique_encodings'],7)
            self.assertFalse(failed['automatic_retry']);self.assertFalse((out/'COMPLETED.json').exists())

if __name__=='__main__':unittest.main()
