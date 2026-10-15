"""Tiny CPU tensors check complete1024-state rejection; never train a model."""
from copy import deepcopy
import unittest
import torch
from scripts.audit_p009_stage1_nc import check_state


class NCStateOracle(unittest.TestCase):
    def setUp(self):
        self.plan=dict(updates=[[0]]*1024,lrs=[1e-5]*1024);self.identity={'synthetic_fixture':True}
        self.state=dict(identity=self.identity,step=1024,cursor=1024,schedule=self.plan['updates'],lrs=self.plan['lrs'],supervised_tokens=2097148,processed_tokens=3000000,
            trainable_names=['model.lora_A.weight'],adapter={'model.lora_A.weight':torch.ones(2,2,dtype=torch.float32)},
            optimizer=dict(param_groups=[{'params':[0]}],state={0:dict(step=torch.tensor(1024.),exp_avg=torch.zeros(2,2),exp_avg_sq=torch.ones(2,2))}),
            rng=dict(python=(3,(1,2),None),numpy=['MT19937',[0]*624,0,0,0.],torch=torch.ones(32,dtype=torch.uint8),cuda=[torch.ones(32,dtype=torch.uint8)]))

    def test_complete_original_state_passes_without_loading_model(self):
        check_state(self.state,self.identity,self.plan,2097148,3000000)

    def test_missing_optimizer_or_incomplete_rng_is_rejected(self):
        s=deepcopy(self.state);s['optimizer']['state']={}
        with self.assertRaises(ValueError):check_state(s,self.identity,self.plan,2097148,3000000)
        s=deepcopy(self.state);s['rng']['cuda']=[]
        with self.assertRaises(ValueError):check_state(s,self.identity,self.plan,2097148,3000000)

    def test_nonfinite_moment_and_wrong_trajectory_are_rejected(self):
        s=deepcopy(self.state);s['optimizer']['state'][0]['exp_avg'][0,0]=float('nan')
        with self.assertRaises(ValueError):check_state(s,self.identity,self.plan,2097148,3000000)
        s=deepcopy(self.state);s['lrs']=s['lrs'][:-1]
        with self.assertRaises(ValueError):check_state(s,self.identity,self.plan,2097148,3000000)


if __name__=='__main__':unittest.main()
