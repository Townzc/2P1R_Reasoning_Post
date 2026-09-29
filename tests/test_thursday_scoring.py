from pathlib import Path
import tempfile
import unittest
from experiments.thursday_probe.arithmetic_eval import score,GenerationBudget

class ScoringTests(unittest.TestCase):
    def event(self,text,reason='native_eos'):
        return {'answer_segment':text,'stop_reason':reason}
    def test_new_valid_program_and_cap(self):
        r={'task':'construct','numbers':[2,3,4,5],'target':14}
        t='Answer: (2+3)+(4+5)'
        self.assertTrue(score(r,self.event(t))['correct'])
        self.assertFalse(score(r,self.event(t,'length_cap'))['correct'])
        self.assertFalse(score(r,self.event('Answer: 14'))['correct'])
        self.assertFalse(score(r,self.event(t+'\n'+t))['parsed'])
    def test_exact_signed_fraction_and_code_rejection(self):
        r={'task':'compute','answer':'-3/2'}
        self.assertTrue(score(r,self.event('Answer: -3/2'))['correct'])
        self.assertFalse(score(r,self.event('Answer: __import__("os")'))['parsed'])
    def test_irreversible_generation_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            b=GenerationBudget(Path(d)/'budget.json',cap=3,initial_used=0)
            b.reserve('one',2)
            with self.assertRaises(ValueError):b.reserve('one',1)
            with self.assertRaises(ValueError):b.reserve('two',2)
            b.reserve('two',1)

if __name__=='__main__':unittest.main()
