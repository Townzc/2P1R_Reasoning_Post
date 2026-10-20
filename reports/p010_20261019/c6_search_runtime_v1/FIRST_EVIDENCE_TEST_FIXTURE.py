"""New C6 evidence/owned-parser cases; synthetic text only, no model or gold."""
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.p010.common import read, digest
from experiments.p010.cue_key_process import OriginalAnswerKeys, group_rows, worker
from experiments.p010.cue_search_contract import sampling
from experiments.p010.cue_search_evidence import decode, record_keys


class Tokens:
    def decode(self, ids, **kwargs):
        return ''.join({1:r'\boxed{',2:'2}',3:'x',4:'\nProblem:',5:'after',151643:''}[t] for t in ids)


def example(ids=None, cue=None):
    cue = [1] if cue is None else cue
    row = dict(candidate_id='synthetic/only', problem_id='synthetic/problem',
        source_row_sha256='synthetic-source', input_ids=[9]+cue, cue_token_ids=cue, rollout=0)
    raw = {k:row[k] for k in ('candidate_id','problem_id','source_row_sha256')}
    raw.update(prompt_token_ids=row['input_ids'],sampling=sampling(0),output_count=1,
        backend_text='original synthetic text',token_ids=[2,151643] if ids is None else ids,
        finish_reason='stop',stop_reason=151643)
    return row,raw


class RawCases(unittest.TestCase):
    def decoded(self,row,raw):
        return decode(row,raw,Tokens(),{1,2,3,4,5,151643},(151643,))

    def test_forced_cue_is_part_of_assistant_answer(self):
        row,raw=example()
        result=self.decoded(row,raw)
        self.assertEqual(result['answer_segment'],r'\boxed{2}')
        self.assertEqual(result['stop_reason'],'native_eos')

    def test_exact_cap_native_eos_does_not_become_length_cap(self):
        row,raw=example([3]*1023+[151643],cue=[])
        raw.update(finish_reason='length',stop_reason=None)
        self.assertEqual(self.decoded(row,raw)['stop_reason'],'native_eos')

    def test_real_cap_and_logical_boundary_are_preserved(self):
        row,raw=example([3]*1024,cue=[]);raw.update(finish_reason='length',stop_reason=None)
        self.assertEqual(self.decoded(row,raw)['stop_reason'],'length_cap')
        row,raw=example([2,4,5,151643])
        result=self.decoded(row,raw)
        self.assertEqual(result['stop_reason'],'new_problem_boundary')
        self.assertEqual(result['answer_segment'],r'\boxed{2}')

    def test_incomplete_or_foreign_stream_is_not_missing(self):
        row,raw=example([2]);raw.update(finish_reason='length',stop_reason=None)
        with self.assertRaises(ValueError):self.decoded(row,raw)
        row,raw=example([151643,2,151643])
        with self.assertRaises(ValueError):self.decoded(row,raw)
        row,raw=example();raw['source_row_sha256']='different'
        with self.assertRaises(ValueError):self.decoded(row,raw)
        row,raw=example([999,151643])
        with self.assertRaises(ValueError):self.decoded(row,raw)

    def test_exact_named_ledger_contains_all_batches(self):
        keys=record_keys()
        self.assertEqual(len(keys),82)
        self.assertEqual(len(set(keys)),82)
        self.assertIn('cue/search_r1/screen_done/09984',keys)


class ParserCases(unittest.TestCase):
    def test_real_pinned_process_cache_missing_and_successful_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'original'
            pool=OriginalAnswerKeys(out,time.time()+60)
            try:
                first=pool.one(r'Text. \boxed{\frac{1}{2}}')
                second=pool.one(r'Other text. \boxed{\frac{1}{2}}')
                missing=pool.one('No explicit final answer here.')
                self.assertEqual(first['answer_key'],'number:0.5')
                self.assertFalse(first['cached']);self.assertTrue(second['cached'])
                self.assertIsNone(missing['answer_key']);self.assertEqual(pool.count,1)
                self.assertEqual(len(list((out/'pairs').glob('*/COMPLETED.json'))),1)
            finally:pool.close()
            self.assertEqual(pool.proc.exitcode,0)
            with self.assertRaises(FileExistsError):OriginalAnswerKeys(out,time.time()+60)

    def test_worker_parser_exception_is_a_preserved_technical_failure(self):
        sent=[]
        conn=types.SimpleNamespace(send=sent.append,recv=lambda:('pair',r'\boxed{2}'),close=lambda:None)
        with patch('math_verify.parse',side_effect=RuntimeError('synthetic parser fault')):
            worker(conn)
        self.assertTrue(sent[0]['ready'])
        self.assertEqual(sent[1]['status'],'technical_failure')
        self.assertNotIn('answer_key',sent[1])

    def test_outer_timeout_is_not_retried_or_assigned_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            pool=object.__new__(OriginalAnswerKeys)
            pool.out=Path(directory);pool.deadline=time.time()+60;pool.cache={};pool.count=0
            pool.parent=types.SimpleNamespace(send=lambda x:None,poll=lambda x:False)
            pool.close=lambda **kw:None
            with self.assertRaises(TimeoutError):pool.one(r'\boxed{5}')
            self.assertEqual(pool.count,1)
            self.assertEqual(pool.cache,{})
            key=digest(dict(extracted_answer='5'))
            self.assertTrue((pool.out/'pairs'/key/'FAILED.json').exists())
            self.assertFalse((pool.out/'pairs'/key/'COMPLETED.json').exists())
            with self.assertRaises(FileExistsError):pool.one(r'\boxed{5}')
            self.assertEqual(pool.count,1)

    def test_actual_group_job_preserves_failure_and_blocks_selection(self):
        rows=[dict(candidate_id=str(i),problem_id='synthetic',candidate=0,rollout=0,
                   stop={'answer_segment':r'\boxed{1}','stop_reason':'native_eos'}) for i in range(10080)]
        fake=types.SimpleNamespace(one=lambda x:(_ for _ in ()).throw(RuntimeError('synthetic failure')),
                                   close=lambda **kw:None)
        with tempfile.TemporaryDirectory() as directory, patch(
                'experiments.p010.cue_key_process.OriginalAnswerKeys',return_value=fake):
            out=Path(directory)/'group'
            with self.assertRaises(RuntimeError):group_rows(rows,out,time.time()+60)
            self.assertFalse(read(out/'FAILED.json')['selection_allowed'])
            self.assertFalse((out/'COMPLETED.json').exists())
            self.assertFalse((out/'OBSERVATIONS.json').exists())

    def test_gold_or_partial_rows_rejected_before_parser_process(self):
        with patch('experiments.p010.cue_key_process.OriginalAnswerKeys') as spawn:
            with self.assertRaises(ValueError):group_rows([],Path('never-created'),time.time()+60)
            rows=[dict(candidate_id=str(i),solution='forbidden') for i in range(10080)]
            with self.assertRaises(ValueError):group_rows(rows,Path('never-created'),time.time()+60)
            spawn.assert_not_called()


if __name__=='__main__':unittest.main()
