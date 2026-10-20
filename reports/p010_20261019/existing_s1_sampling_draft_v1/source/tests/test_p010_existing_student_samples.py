"""New sample-only recipe and adapter restoration checks, no original state."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import torch
from experiments.p010.common import dump,manifest,digest,sha
from experiments.p010.existing_student_samples import rows_checked,sampling,forecast,parent_checked
from experiments.p010.existing_student_restore import copy_adapter,restore_once


class SampleCases(unittest.TestCase):
    def test_only_four_new_complete_sample_passes(self):
        endpoint=[dict(problem_id=f'synthetic/{i}',input_ids=[12,13]) for i in range(500)]
        rows=rows_checked(endpoint)
        self.assertEqual(len(rows),2000)
        self.assertEqual(len({r['candidate_id'] for r in rows}),2000)
        self.assertEqual([r['sampling_seed'] for r in rows[::500]],list(range(4)))
        self.assertTrue(all(sampling(r['sampling_seed'])['temperature']==.6 for r in rows))
        self.assertTrue(all(sampling(r['sampling_seed'])['max_tokens']==1024 for r in rows))

    def test_no_gold_partial_or_truncated_prompts(self):
        endpoint=[dict(problem_id=str(i),input_ids=[12]) for i in range(500)]
        endpoint[0]['solution']='forbidden'
        with self.assertRaises(ValueError):rows_checked(endpoint)
        endpoint[0].pop('solution');endpoint[0]['input_ids']=[12]*1025
        with self.assertRaises(ValueError):rows_checked(endpoint)
        with self.assertRaises(ValueError):rows_checked(endpoint[:499])

    def test_actual_intervals_all_retained_and_budget_not_released(self):
        f=forecast(10,1,[12.],[11.55,10.7],'31.24')
        self.assertEqual(f['maximum_seconds'],12.)
        self.assertEqual(f['actual_completed_seconds'],[12.])
        self.assertEqual(f['budget']['prior_reserved_usd'],'31.24')
        with self.assertRaises(TimeoutError):forecast(500,1,[12.],[11.55],'31.24')
        with self.assertRaises(ValueError):forecast(0,0,[],[11.55],'149')

    def test_parent_rejects_nonfinal_or_wrong_model(self):
        checkpoint=dict(step=1024,supervised_tokens=2097148,schema='complete_lora_v1',sha256='synthetic')
        merge=dict(checkpoint=checkpoint,merge_dtype='float32',saved_dtype='bfloat16',
            final_checkpoint_only=True,optimizer_updates_after_terminal_save=0,merged_files={})
        oracle=dict(passed=True,run_id='s1_s17_n400',updates_verified=1024,targets_verified=2097148,state_sha256='synthetic')
        accepted=dict(decision='PASS',first_pair_run_ids=['s1_s17_n400','s1_s17_n3200'],report_sha256='synthetic-report')
        result=parent_checked('s1_s17_n400',checkpoint,merge,oracle,accepted)
        self.assertEqual(result['new_training_updates'],0)
        self.assertTrue(result['original_greedy_reused'])
        with self.assertRaises(ValueError):parent_checked('unknown',checkpoint,merge,oracle,accepted)
        oracle['updates_verified']=896
        with self.assertRaises(ValueError):parent_checked('s1_s17_n400',checkpoint,merge,oracle,accepted)


class AdapterCases(unittest.TestCase):
    def test_exact_cpu_parameter_copy_without_optimizer_or_rng_restore(self):
        model=torch.nn.Linear(2,1,bias=False)
        value=torch.tensor([[1.25,-2.5]],dtype=torch.float32)
        state=dict(trainable_names=['weight'],adapter={'weight':value})
        with patch('torch.optim.AdamW',side_effect=AssertionError('optimizer forbidden')):
            self.assertEqual(copy_adapter(model,state),1)
        self.assertTrue(torch.equal(model.weight.detach(),value))

    def test_wrong_shape_dtype_and_nonfinite_are_rejected(self):
        model=torch.nn.Linear(2,1,bias=False)
        for value in [torch.zeros(1,3),torch.zeros(1,2,dtype=torch.float64),torch.tensor([[float('nan'),0.]])]:
            with self.assertRaises(ValueError):copy_adapter(model,dict(trainable_names=['weight'],adapter={'weight':value}))

    def test_actual_restore_body_reconstructs_original_bytes_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);checkpoint=root/'checkpoint';checkpoint.mkdir()
            (checkpoint/'state.pt').write_bytes(b'synthetic saved state')
            identity={'run':'synthetic'}
            m=dict(step=1024,supervised_tokens=2097148,identity_sha256=digest(identity),sha256=sha(checkpoint/'state.pt'))
            dump(checkpoint/'manifest.json',m)
            original=root/'old';original.mkdir();(original/'model.safetensors').write_bytes(b'synthetic merged bytes');(original/'tokenizer.json').write_bytes(b'synthetic tokenizer')
            expected=dict(checkpoint=m,merged_files=manifest(original))
            model=torch.nn.Linear(2,1,bias=False)
            model.merge_and_unload=lambda **kw:model
            model.save_pretrained=lambda path,**kw:(Path(path)/'model.safetensors').write_bytes(b'synthetic merged bytes')
            tokenizer=type('Tokenizer',(),{'eos_token_id':151643,'save_pretrained':lambda self,path:(Path(path)/'tokenizer.json').write_bytes(b'synthetic tokenizer')})()
            state=dict(step=1024,supervised_tokens=2097148,identity=identity,trainable_names=['weight'],adapter={'weight':torch.tensor([[1.,2.]])})
            with patch('experiments.sft_allocation_midpoint.checkpoint.load',return_value=state) as load, \
                 patch('experiments.sft_allocation_midpoint.runtime.new_model',return_value=(model,tokenizer)), \
                 patch('experiments.learning_regime_p009.stage1_training_core.training_environment',return_value={'synthetic':True}), \
                 patch('experiments.sft_allocation_midpoint.runtime.train',side_effect=AssertionError('training forbidden')), \
                 patch('experiments.sft_allocation_midpoint.checkpoint.restore_rng',side_effect=AssertionError('RNG restore forbidden')):
                result=restore_once('synthetic/base',checkpoint,expected,root/'restore',root/'merged')
                self.assertEqual(load.call_count,1)
                self.assertTrue(result['original_greedy_model_bytes_reproduced'])
                self.assertEqual(result['new_training_updates'],0)
                with self.assertRaises(FileExistsError):restore_once('synthetic/base',checkpoint,expected,root/'restore',root/'merged')
                self.assertEqual(load.call_count,1)


if __name__=='__main__':unittest.main()
