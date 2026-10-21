"""New finite C2 scoring fixtures only, with synthetic frozen pair observations."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from experiments.p011 import c2_scoring as s,c2_score_process as p
from tests.test_p011_long_scoring import FakePool


def rows():
    result=[]
    for i in range(68):
        for a in (1,3,4):
            cid=f'fixture{i:03d}::attempt{a:02d}'
            result.append({'id':'p011_c2_t08/'+cid,'candidate_id':cid,'problem_id':f'fixture{i:03d}',
                'attempt':a,'gold':'2','answer_segment':'\\boxed{2}','stop_reason':'native_eos',
                'original_gold_row_sha256':'a'*64,'raw_record_sha256':'b'*64,'decoded_record_sha256':'c'*64})
    return result[:203]


class C2Scores(unittest.TestCase):
    def test_dynamic203_rows_three_chunks_tail3_and_saved_boolean_replay(self):
        with TemporaryDirectory() as root:
            path=Path(root)/'score';rr=rows();FakePool.calls=0
            done=s.score_once(path,rr,{'fixture':'C2only'},30,pool_factory=FakePool)
            self.assertEqual(done['row_count'],203);self.assertEqual(FakePool.calls,3)
            self.assertEqual(json.loads((path/'chunks/00002/COMPLETED.json').read_text())['confirmed_rows'],3)
            proof=s.verify_saved_scores(path,rr,{'fixture':'C2only'},30)
            self.assertEqual(proof['new_symbolic_comparisons'],0);self.assertEqual(FakePool.calls,3)
            with self.assertRaises(FileExistsError):s.score_once(path,rr,{'fixture':'C2only'},30,pool_factory=FakePool)

    def test_gapped_original_attempts_allowed_fifth_or_B_identity_rejected(self):
        rr=rows();s.checked_rows(rr)
        rr[0]['attempt']=5
        with self.assertRaises(ValueError):s.checked_rows(rr)
        rr=rows();rr[0]['id']='p011_b_t10/'+rr[0]['candidate_id']
        with self.assertRaises(ValueError):s.checked_rows(rr)

    def test_unknown_boolean_does_not_become_failed_answer(self):
        rr=rows();result=FakePool().score_rows(rr)['rows'];result[-1]['score']['correct']=None
        with self.assertRaisesRegex(ValueError,'unknown'):s.checked_summary(rr,result)

    def test_tampered_tail_count_cannot_pass_complete_journal(self):
        with TemporaryDirectory() as root:
            path=Path(root)/'score';rr=rows();s.score_once(path,rr,{'fixture':'tail'},30,pool_factory=FakePool)
            f=path/'chunks/00002/COMPLETED.json';v=json.loads(f.read_text());v['confirmed_rows']=100;f.write_text(json.dumps(v))
            with self.assertRaisesRegex(ValueError,'chunk proof'):s.verify_saved_scores(path,rr,{'fixture':'tail'},30)

    def test_second_chunk_failure_retains_first_without_zero_or_replay(self):
        class Broken(FakePool):
            def score_rows(self,rr):
                if self.cache:raise RuntimeError('synthetic nextchunk failure')
                return super().score_rows(rr)
        with TemporaryDirectory() as root:
            path=Path(root)/'score';rr=rows()
            with self.assertRaises(RuntimeError):s.score_once(path,rr,{'fixture':'partial'},30,pool_factory=Broken)
            self.assertTrue((path/'chunks/00000/COMPLETED.json').exists())
            self.assertTrue((path/'FAILED.json').exists());self.assertFalse((path/'COMPLETED.json').exists())
            with self.assertRaises(FileExistsError):s.score_once(path,rr,{'fixture':'partial'},30,pool_factory=Broken)

    def test_supervisor_range_and_original_cleanup_do_not_admit_empty_or_extra_rows(self):
        self.assertEqual(p.MODULE,'experiments.p011.c2_score_process')
        with TemporaryDirectory() as root:
            path=Path(root)/'control'
            for rr,seconds in (([],30),([{}]*2801,30),(rows(),28001)):
                with self.assertRaises(ValueError):p.supervise_once(path,rr,{'fixture':'limit'},seconds)
                self.assertFalse(path.exists())


if __name__=='__main__':unittest.main()
