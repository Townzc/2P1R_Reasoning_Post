import copy
import unittest
from experiments.p010.common import read
from experiments.p010.training import checked_recipe


class RecipeChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p='.local/p010_20261019/r1/inputs/e4_n400_'
        cls.cfg=read(p+'config.json');cls.enc=read(p+'encoded.json');cls.plan=read(p+'plan.json')
    def test_actual_new_inputs_match_original_dose(self):
        r=checked_recipe(self.cfg,self.enc,self.plan)
        self.assertEqual(r['budget']['supervised_response_tokens'],2097148)
    def test_mutated_dose_seed_model_or_eos_rejected(self):
        for k,v in [('seed',29),('targets',2097147),('n',401),('eos_token_id',151643),('model',['wrong','revision'])]:
            cfg=copy.deepcopy(self.cfg);cfg[k]=v
            with self.assertRaises(ValueError):checked_recipe(cfg,self.enc,self.plan)
    def test_partial_answer_and_lr_cannot_pass(self):
        enc=copy.deepcopy(self.enc);enc[0]['input_ids']=enc[0]['input_ids'][:-1]
        with self.assertRaises(ValueError):checked_recipe(self.cfg,enc,self.plan)
        plan=copy.deepcopy(self.plan);plan['lrs'][0]*=2
        with self.assertRaises(ValueError):checked_recipe(self.cfg,self.enc,plan)

if __name__=='__main__':unittest.main()
