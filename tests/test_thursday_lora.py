import copy
import tempfile
import unittest
from pathlib import Path

import torch
from transformers import Qwen2Config, Qwen2ForCausalLM
from peft import PeftModel
from experiments.thursday_probe.lora import attach, parameter_digest, save_adapter
from src.relation_experiment import accumulate_gradients


class LoraTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(17); torch.set_num_threads(1)
        self.base=Qwen2ForCausalLM(Qwen2Config(vocab_size=64,hidden_size=32,intermediate_size=64,
             num_hidden_layers=2,num_attention_heads=4,num_key_value_heads=2,
             max_position_embeddings=128,attention_dropout=0))
        self.ids=torch.tensor([[1,2,3,4,5]])

    def test_zero_output_scope_and_reload(self):
        self.base.eval(); expected=self.base(self.ids).logits.detach()
        original=copy.deepcopy(self.base.state_dict())
        model=attach(self.base); model.eval()
        self.assertTrue(torch.equal(expected,model(self.ids).logits))
        before=parameter_digest(model)
        rows=[{'input_ids':[1,2,3,4,5],'labels':[-100,-100,3,4,5],'n_supervised':3}]
        opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=.01)
        accumulate_gradients(model,rows,0,1,'cpu'); opt.step()
        self.assertEqual(before,parameter_digest(model))
        self.assertFalse(torch.equal(expected,model(self.ids).logits))
        with tempfile.TemporaryDirectory() as d:
            save_adapter(model,Path(d)/'adapter')
            fresh=Qwen2ForCausalLM(self.base.config); fresh.load_state_dict(original)
            child=PeftModel.from_pretrained(fresh,Path(d)/'adapter',is_trainable=True)
            child.eval()
            self.assertTrue(torch.equal(model(self.ids).logits,child(self.ids).logits))
            self.assertEqual(parameter_digest(model,True),parameter_digest(child,True))
            self.assertFalse(torch.optim.AdamW([p for p in child.parameters() if p.requires_grad]).state)

    def test_accumulation_is_token_weighted(self):
        m=attach(self.base)
        rows=[{'input_ids':[1,2,3,4,5],'labels':[-100,-100,3,4,5],'n_supervised':3},
              {'input_ids':[1,6,7],'labels':[-100,6,7],'n_supervised':2}]
        n1=accumulate_gradients(m,rows,0,1,'cpu')
        grads={n:p.grad.clone() for n,p in m.named_parameters() if p.requires_grad}
        m.zero_grad(set_to_none=True); n2=accumulate_gradients(m,rows,0,2,'cpu')
        self.assertAlmostEqual(n1,n2,places=5)
        for n,p in m.named_parameters():
            if p.requires_grad:
                torch.testing.assert_close(grads[n],p.grad,rtol=1e-4,atol=1e-7)


if __name__=='__main__': unittest.main()
