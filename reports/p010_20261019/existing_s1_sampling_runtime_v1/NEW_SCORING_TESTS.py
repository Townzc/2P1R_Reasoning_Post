"""New four-pass-only scoring checks, no real symbolic or model execution."""
from pathlib import Path
from copy import deepcopy
import tempfile
import unittest
from experiments.p010 import existing_samples_scoring as scoring
from tests.test_p010_student_scoring import FakePool, rows as five_rows


def rows():
    return five_rows()[500:]


class FourSampleScoringChecks(unittest.TestCase):
    def test_complete_new_sample_mean_excludes_all_old_greedy_rows(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'job'; source=rows(); binding={'synthetic_new_samples_only':True}
            value=scoring.score_once(p,source,binding,60,pool_factory=FakePool)
            proof=scoring.verify_saved_scores(p,source,binding,60)
            expected=sum(sum(i%(seed+3)==0 for i in range(499)) for seed in range(4))
            self.assertEqual(value['sampled_correct'],expected)
            self.assertEqual(value['sampled_outputs'],2000)
            self.assertEqual(set(value['endpoints']),{'sample0','sample1','sample2','sample3'})
            self.assertNotIn('greedy_accuracy',value)
            self.assertEqual(proof['unique_symbolic_pairs'],2)
            self.assertEqual(proof['new_symbolic_comparisons'],0)
            self.assertEqual(len(list((p/'chunks').iterdir())),20)

    def test_old_greedy_or_missing_fourth_pass_is_rejected(self):
        for value in (five_rows()[:2000],rows()[:-1],rows()[500:]+rows()[:500]):
            with self.assertRaises(ValueError): scoring.checked_rows(value)

    def test_partial_second_chunk_retained_and_same_job_cannot_retry(self):
        class Broken(FakePool):
            def score_rows(self,value):
                if self.ids: raise RuntimeError('synthetic sample-only interruption')
                return super().score_rows(value)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'job'
            with self.assertRaisesRegex(RuntimeError,'sample-only interruption'):
                scoring.score_once(p,rows(),{'synthetic':True},60,pool_factory=Broken)
            self.assertEqual(scoring.read(p/'FAILED.json')['confirmed_chunk_rows'],100)
            self.assertTrue((p/'chunks/00000/COMPLETED.json').exists())
            self.assertFalse((p/'COMPLETED.json').exists())
            with self.assertRaises(FileExistsError):
                scoring.score_once(p,rows(),{'synthetic':True},60,pool_factory=FakePool)

    def test_same_question_must_be_present_in_every_new_sample_pass(self):
        source=deepcopy(rows()); source[1000]['problem_id']='invented'
        source[1000]['id']='sample2::invented'
        with self.assertRaises(ValueError): scoring.checked_rows(source)


if __name__=='__main__': unittest.main()
