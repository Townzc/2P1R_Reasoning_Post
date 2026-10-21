"""New cross-component state/journal/forecast tests; no old fixture replay."""
import copy
from pathlib import Path
import tempfile
import unittest

from experiments.p011 import long_evidence as e
from experiments.p011.long_training import learning_rates, validate_plan
from experiments.sft_allocation_midpoint.common import dump,digest,sha,read
from tests.test_p011_long_evidence import LongEvidenceChecks


class LongStateChain(unittest.TestCase):
    def test_architecture_order_matches_real_tiny_model_and_rejects_swap(self):
        import torch
        from transformers import Qwen2Config,Qwen2ForCausalLM
        from peft import LoraConfig,get_peft_model,TaskType
        helper=LongEvidenceChecks();cfg=helper.tiny_config()
        with torch.device('meta'):
            model=Qwen2ForCausalLM(Qwen2Config(**cfg))
            self.assertEqual(list(e.expected_shapes(cfg,'S-F15')),[n for n,p in model.named_parameters()])
            model=get_peft_model(model,LoraConfig(r=64,lora_alpha=128,lora_dropout=0.,bias='none',
                target_modules=e.TARGETS,task_type=TaskType.CAUSAL_LM))
            self.assertEqual(list(e.expected_shapes(cfg,'S-L15')),[n for n,p in model.named_parameters() if p.requires_grad])
        args=list(helper.state());names=args[0]['trainable_names'];names[0],names[1]=names[1],names[0]
        with self.assertRaisesRegex(ValueError,'coverage'):e.check_state(*args)

    def test_full_training_chain_and_changed_join_rejected_without_second_state_load(self):
        import torch
        state,identity,_,_,_,arm,cfg=LongEvidenceChecks().state()
        ids=[10]+[20]*16000+[151645]+[11]
        encoded=[dict(path_id='synthetic',input_ids=ids,labels=[-100]+ids[1:-1]+[-100],
            assistant_start=1,assistant_end=16002,n_supervised=16001,n_processed=16003,
            eos_token_id=151645,template_final_newline_supervised=False)]
        plan=dict(supervised_tokens=64004,optimizer_updates=2,seed=17,length_bucket_width=None,
            presentation_order='shuffled_full_passes_then_extras',row_path_ids=['synthetic'],
            updates=[[0,0],[0,0]],q=4,exposures=[4])
        rates=learning_rates(2,arm);proof=validate_plan(encoded,plan,rates,arm)
        state.update(schedule=plan['updates'],lrs=rates,supervised_tokens=64004,processed_tokens=64012)
        state['optimizer']['param_groups'][0]['lr']=rates[-1]
        policy=dict(category='A',worker_start_epoch=1000.,worker_hard_seconds=5500.,
            result_deadline_epoch=10000.,full_result_seconds=7000.,measurement_exceptions=0,
            projection_multiplier=1.2,uncalibrated_future_seconds=300,training_unit_seconds=[1.],
            endpoint_batch_seconds=[1.],hourly_rate_usd='4.01',startup_allowance_seconds=600,
            platform_timeout_seconds=5560,reserved_usd='8',prior_reserved_usd='0')
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as tmp:
            root=Path(tmp);cp=root/'checkpoint_0002';cp.mkdir();torch.save(state,cp/'state.pt')
            record=dict(schema=state['schema'],file='state.pt',bytes=(cp/'state.pt').stat().st_size,
                sha256=sha(cp/'state.pt'),identity_sha256=digest(identity),step=2,
                supervised_tokens=64004,processed_tokens=64012);dump(cp/'manifest.json',record)
            attempts={};done={}
            for step in (1,2):
                name=f'update_{step:05d}';intent=dict(step=step,indices=[0,0],lr=rates[step-1],
                    supervised_tokens=32002,processed_tokens=32006)
                attempts[name]=intent;done[name]={**intent,'cumulative_supervised':32002*step,
                    'cumulative_processed':32006*step,'seconds':1.,'loss':.4,'gradient_norm':.7,
                    'max_allocated_bytes':1000}
                dump(root/'forecasts'/(name+'.json'),e.forecast(policy,3-step,104,[1.]*(step-1),[],1000.+step))
            exported=dict(relative_path='model_for_vllm',files={'model.safetensors':{'bytes':1,'sha256':'a'*64}},
                final_state=record,mode='lora',evaluation_performed=False,optimizer_updates_after_terminal_state=0)
            dump(root/'MODEL_EXPORT.json',exported)
            trained={**proof,'actual_supervised_tokens':64004,'actual_processed_tokens':64012,
                     'terminal_state':record,'model_export_sha256':digest(exported)}
            dump(root/'TRAINING_PROCESS_RESULT.json',dict(result=trained,update_seconds=[1.,1.],pid=123))
            dump(root/'RESULT.json',dict(training=trained,training_update_seconds=[1.,1.]))
            dump(root/'TRAINING_EXIT.json',dict(pid=123,exitcode=0,joined_before_vllm=True,
                model_export_file_sha256=sha(root/'MODEL_EXPORT.json')))
            attempts.update(terminal_state=proof,terminal_model_export=dict(mode='lora',final_state=record))
            done.update(terminal_state=record,terminal_model_export={'proof_sha256':digest(exported)})
            actual=e.verify_training(root,encoded,plan,rates,arm,cfg,identity,attempts,done,policy)
            self.assertEqual((actual['updates'],actual['targets'],actual['processed']),(2,64004,64012))
            # Deliberately do not invoke verify_training/state-load a second time.
            # Validate the failure branch with a stubbed cached state proof only.
            from unittest.mock import patch
            (root/'TRAINING_EXIT.json').write_text('{"pid":123,"exitcode":1,"joined_before_vllm":true}')
            with patch.object(e,'load_state_once',return_value=actual):
                with self.assertRaisesRegex(ValueError,'chain'):
                    e.verify_training(root,encoded,plan,rates,arm,cfg,identity,attempts,done,policy)


if __name__=='__main__':unittest.main()
