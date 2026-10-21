"""New tiny/synthetic long closeout checks; no prior tests or scientific inputs."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from experiments.p011 import long_evidence as e
from experiments.p011.long_evaluation import BENCHMARK_COUNTS, sampling
from experiments.sft_allocation_midpoint.common import dump,read,sha,digest


class Tokenizer:
    all_special_ids=[151643,151644,151645]
    def get_vocab(self):return {'text':20,'prompt':10,'other':11,'eos':151645,'start':151644}
    def decode(self,ids,**kw):return ''.join('analysis</think>\\boxed{2}' if i==20 else '?' for i in ids)


class LongEvidenceChecks(unittest.TestCase):
    @staticmethod
    def tiny_config():
        return dict(architectures=['Qwen2ForCausalLM'],model_type='qwen2',tie_word_embeddings=True,
            hidden_size=16,intermediate_size=24,num_attention_heads=4,num_key_value_heads=2,
            num_hidden_layers=1,vocab_size=32)

    def state(self,arm='S-L15'):
        import torch
        cfg=self.tiny_config();shapes=e.expected_shapes(cfg,arm);names=list(shapes)
        tensors={n:torch.zeros(s,dtype=torch.float32) for n,s in shapes.items()}
        optimizer=dict(state={i:dict(step=torch.tensor(2.),exp_avg=torch.zeros_like(tensors[n]),
            exp_avg_sq=torch.zeros_like(tensors[n])) for i,n in enumerate(names)},
            param_groups=[dict(params=list(range(len(names))),lr=1e-5,betas=(.9,.999),eps=1e-8,
                weight_decay=0.,foreach=False,amsgrad=False,maximize=False)])
        plan=dict(optimizer_updates=2,supervised_tokens=4,updates=[[0],[0]])
        encoded=[dict(n_supervised=2,n_processed=3)];rates=[1e-4,1e-5];identity={'synthetic':True}
        state=dict(schema='p011_complete_training_state_v1',identity=identity,step=2,cursor=2,
            schedule=plan['updates'],lrs=rates,supervised_tokens=4,processed_tokens=6,
            adaptation_mode=e.ARMS[arm]['mode'],
            parameter_payload_meaning='all_trainable_parameters; full model for full arm, adapters for LoRA',
            trainable_names=names,adapter=tensors,optimizer=optimizer,
            rng=dict(python=(3,tuple(range(625)),None),numpy=['MT19937',[0]*624,0,0,0.],
                torch=torch.zeros(4,dtype=torch.uint8),cuda=[torch.zeros(4,dtype=torch.uint8)]))
        return state,identity,encoded,plan,rates,arm,cfg

    def test_shapes_match_real_tiny_qwen_and_peft_parameter_names(self):
        import torch
        from transformers import Qwen2Config,Qwen2ForCausalLM
        from peft import LoraConfig,get_peft_model,TaskType
        cfg=self.tiny_config()
        with torch.device('meta'):
            model=Qwen2ForCausalLM(Qwen2Config(**cfg))
            full={n:tuple(p.shape) for n,p in model.named_parameters() if p.requires_grad}
            self.assertEqual(e.expected_shapes(cfg,'S-F15'),full)
            model=get_peft_model(model,LoraConfig(r=64,lora_alpha=128,lora_dropout=0.,bias='none',
                target_modules=e.TARGETS,task_type=TaskType.CAUSAL_LM))
            adapter={n:tuple(p.shape) for n,p in model.named_parameters() if p.requires_grad}
            self.assertEqual(e.expected_shapes(cfg,'S-L15'),adapter)
        # Shape metadata only: no weights loaded, forward, optimizer or GPU.

    def test_full_and_lora_states_have_complete_dose_optimizer_rng(self):
        for arm in ('S-L15','S-F15','S-L3'):
            args=self.state(arm);proof=e.check_state(*args)
            self.assertEqual((proof['targets'],proof['processed'],proof['updates']),(4,6,2))

    def test_missing_parameter_even_with_self_consistent_saved_names_rejected(self):
        args=list(self.state());s=args[0];name=s['trainable_names'].pop();del s['adapter'][name]
        with self.assertRaisesRegex(ValueError,'coverage'):e.check_state(*args)

    def test_nonfinite_moment_wrong_step_and_rng_each_rejected(self):
        for mutation in ('nan','step','rng'):
            args=list(self.state());s=args[0]
            if mutation=='nan':s['optimizer']['state'][0]['exp_avg'].flatten()[0]=float('nan')
            elif mutation=='step':s['optimizer']['state'][0]['step'].fill_(1)
            else:s['rng']['cuda']=[]
            with self.assertRaises(ValueError):e.check_state(*args)

    def test_state_file_mmap_load_has_original_manifest_and_no_restore(self):
        import torch
        args=self.state();state,identity,encoded,plan,rates,arm,cfg=args
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as tmp:
            path=Path(tmp)/'checkpoint_0002';path.mkdir();torch.save(state,path/'state.pt')
            record=dict(schema=state['schema'],file='state.pt',bytes=(path/'state.pt').stat().st_size,
                sha256=sha(path/'state.pt'),identity_sha256=digest(identity),step=2,
                supervised_tokens=4,processed_tokens=6)
            dump(path/'manifest.json',record)
            result=e.load_state_once(tmp,identity,encoded,plan,rates,arm,cfg)
            self.assertEqual(result['record'],record)

    def request(self):
        return dict(id='math500:0000:sample:0',problem_id='math500:0000',benchmark='math500',
            source_row=0,mode='sample',seed=0,prompt_token_ids=[10,11],prompt_text_sha256=digest('native'),
            required_context=16386,gold='2')

    def record(self,r,ids=None,finish='stop'):
        return dict(id=r['id'],request_sha256=digest(r),prompt_token_ids=r['prompt_token_ids'],
            sampling=sampling(r,[151645]),answers=[dict(token_ids=[20,151645] if ids is None else ids,
                backend_text='synthetic backend output',finish_reason=finish,stop_reason=None)])

    def test_native_cap_special_and_full_think_region_are_distinguished(self):
        r=self.request();tok=Tokenizer()
        cases=[([20,151645],'stop','native_eos'),([20]*16384,'length','length_cap'),
               ([20,151644,20],'stop','invalid_special_token')]
        for ids,finish,want in cases:
            v=e.decode_record(r,self.record(r,ids,finish),[151645],tok,151936)
            self.assertEqual(v['stop_reason'],want)
        v=e.decode_record(r,self.record(r),[151645],tok,151936)
        scored=e.scoring_rows([r],{r['id']:v})
        self.assertEqual(scored[0]['answer_segment'],'\\boxed{2}')
        self.assertTrue(scored[0]['last_think_boundary_present'])

    def test_incomplete_foreign_and_post_eos_outputs_never_become_zero(self):
        r=self.request()
        for kind in ('partial','foreign','post_eos'):
            item=self.record(r)
            if kind=='partial':item['answers'][0]['token_ids']=[20]
            elif kind=='foreign':item['request_sha256']='0'*64
            else:item['answers'][0]['token_ids']=[151645,20]
            with self.assertRaises(ValueError):e.decode_record(r,item,[151645],Tokenizer(),151936)

    def test_unmapped_tokens_only_preserved_for_complete_length_cap(self):
        r=self.request();item=self.record(r,[90000]*16384,'length')
        v=e.decode_record(r,item,[151645],Tokenizer(),151936)
        self.assertEqual(v['unmapped_model_token_ids'],[90000])
        with self.assertRaises(ValueError):
            e.decode_record(r,self.record(r,[90000,151645]),[151645],Tokenizer(),151936)

    def fixture(self,root):
        requests=[]
        for b,n in BENCHMARK_COUNTS.items():
            for i in range(n):
                modes=[('sample',s) for s in range(4 if b=='math500' else 8)]
                if b=='math500':modes.append(('greedy',0))
                for mode,seed in modes:
                    requests.append({**self.request(),'id':f'{b}:{i:04d}:{mode}:{seed}',
                        'problem_id':f'{b}:{i:04d}','benchmark':b,'source_row':i,'mode':mode,'seed':seed})
        policy=dict(category='A',worker_start_epoch=1000.,worker_hard_seconds=5500.,
            result_deadline_epoch=10000.,full_result_seconds=7000.,measurement_exceptions=0,
            projection_multiplier=1.2,uncalibrated_future_seconds=300,
            training_unit_seconds=[],endpoint_batch_seconds=[1.],hourly_rate_usd='4.01',
            startup_allowance_seconds=600,platform_timeout_seconds=5560,reserved_usd='8',prior_reserved_usd='0')
        key='long/synthetic';ledger={key+'/claim':{'fake':True},key+'/terminal':{'fake':True}}
        for index,first in enumerate(range(0,len(requests),32)):
            unit=f'eval_{index:04d}';part=requests[first:first+32]
            gpu=[{**{k:v for k,v in r.items() if k!='gold'},'request_sha256':digest(r)} for r in part]
            intent=dict(requests=gpu,sampling=[sampling(r,[151645]) for r in part])
            dump(root/'intents'/(unit+'.json'),intent)
            raw=[self.record(r) for r in part];dump(root/'raw'/(unit+'.json'),raw)
            ack=dict(count=len(part),raw_file_sha256=sha(root/'raw'/(unit+'.json')),
                     request_ids=[r['id'] for r in part],seconds=1.)
            dump(root/'completed'/(unit+'.json'),ack)
            ledger[key+'/unit/'+unit]=intent;ledger[key+'/done/'+unit]=ack
            dump(root/'forecasts'/(unit+'.json'),e.forecast(policy,0,104-index,[],[1.]*index,1001.+index))
        dump(root/'RESULT.json',dict(raw_endpoint_count=3300,unique_questions=600,endpoint_batch_seconds=[1.]*104))
        dump(root/'PRE_ENGINE_FORECAST.json',e.forecast(policy,0,104,[],[],1001.))
        dump(root/'ENGINE.json',dict(requested=e.engine_settings(16386),actual=dict(max_model_len=16386,
            enforce_eager=False,dtype='torch.bfloat16',max_num_seqs=32,max_num_batched_tokens=8192,
            enable_chunked_prefill=True,enable_prefix_caching=False,gpu_memory_utilization=.8,
            compilation_level=3,cudagraph_mode='FULL_AND_PIECEWISE',cudagraph_capture_sizes=[1,2,4,8,16,32])))
        dump(root/'LINUX_CONSTRUCTORS.json',dict(count=3300,before_vllm_model_allocation=True,
            all_native_prompt_texts_verified=True))
        return requests,policy,key,ledger

    def test_all3300_payload_and_exact_named_journal_with_no_symbolic_calls(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as tmp:
            root=Path(tmp);requests,p,key,ledger=self.fixture(root)
            a,d=e.verify_journals(root,key,'baseline',0,ledger)
            result=e.verify_endpoint(root,requests,16386,[151645],Tokenizer(),{'vocab_size':151936},a,d,p,[])
            self.assertEqual(result['logical_stops'],{'native_eos':3300})
            self.assertEqual(len(result['scoring_rows']),3300)
            self.assertFalse(result['symbolic_scoring_performed'])

    def test_mutated_cloud_ack_and_missing_unit_rejected_before_decode(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as tmp:
            root=Path(tmp);_,_,key,ledger=self.fixture(root)
            changed=copy.deepcopy(ledger);changed[key+'/done/eval_0000']['count']=0
            with self.assertRaisesRegex(ValueError,'acknowledgments'):e.verify_journals(root,key,'baseline',0,changed)
            del ledger[key+'/unit/eval_0103']
            with self.assertRaisesRegex(ValueError,'named-key'):e.verify_journals(root,key,'baseline',0,ledger)

    def test_forecast_tampering_and_baseline_training_unit_rejected(self):
        p=dict(category='A',worker_start_epoch=1000.,worker_hard_seconds=5500.,
            result_deadline_epoch=10000.,full_result_seconds=7000.,measurement_exceptions=0,
            projection_multiplier=1.2,uncalibrated_future_seconds=300,training_unit_seconds=[],
            endpoint_batch_seconds=[1.],hourly_rate_usd='4.01',startup_allowance_seconds=600,
            platform_timeout_seconds=5560,reserved_usd='8',prior_reserved_usd='0')
        f=e.forecast(p,0,104,[],[],1001.);f['endpoint_batch_max_seconds']=0
        with self.assertRaisesRegex(ValueError,'forecast'):e.replay_forecast(f,p,0,104,[],[])
        with self.assertRaisesRegex(ValueError,'Baseline'):e.expected_units('baseline',2)


if __name__=='__main__':unittest.main()
