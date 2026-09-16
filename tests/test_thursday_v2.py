import copy
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

import torch
from transformers import Qwen2Config,Qwen2ForCausalLM

from experiments.thursday_probe.common import epoch_schedule,verify_manifest
from experiments.thursday_probe.lora import attach,parameter_digest,save_adapter
from experiments.thursday_probe_v2.config import DATA,RELEASE,TRAINING,LIMITS,evaluation_queue,learning_rates,continue_after_measurement
from experiments.thursday_probe_v2.prepare import identity_labels,calibration_rows,validate_reference
from experiments.thursday_probe_v2.queue import dry_run
from experiments.thursday_probe_v2.runtime import GenerationBudget,generation_contract
from experiments.thursday_probe_v2.training import new_optimizer,save_recovery,load_recovery,restore_adapter,train
from src.countdown_smoke import safe_parse
from src.relation_experiment import accumulate_gradients
from src.sft_data import read_jsonl
from experiments.thursday_probe_v2.analyze import paired_interval,per_question


class ProtocolTests(unittest.TestCase):
    def test_local_identity_and_directed_edges(self):
        for expression, present, degenerate in (
            ('(9-3)*7',True,False),('(9*7)-3',False,False),
            ('(4-3)*7',True,True),('(4-4)*7',True,True),
            ('(4-0)*7',True,True),('(8-3)*1',True,True),
            ('(8-3)*0',True,True),('(8-3)*(5-4)',True,True)):
            labels=identity_labels(safe_parse(expression))
            self.assertEqual(labels['target_present'],present)
            self.assertEqual(labels['identity_at_target'],degenerate)
            self.assertEqual(labels['target_nondegenerate'],present and not degenerate)
        # Identity elsewhere does not make a target dependency degenerate.
        r=identity_labels(safe_parse('((9-3)*7)+(5-5)'))
        self.assertTrue(r['identity_anywhere']);self.assertTrue(r['target_nondegenerate'])

    def test_split_sentinel_and_unchanged_releases(self):
        verify_manifest(DATA);verify_manifest(RELEASE)
        original=read_jsonl(DATA/'calibration.jsonl')
        release=read_jsonl(RELEASE/'calibration.jsonl')
        self.assertEqual(calibration_rows(original),release)
        self.assertEqual({r['problem_id'] for r in original},{r['problem_id'] for r in release})
        fit={r['problem_id'] for r in release if r['calibration_split']=='fit'}
        check={r['problem_id'] for r in release if r['calibration_split']=='check'}
        self.assertEqual((len(fit),len(check),len(fit&check)),(32,16,0))
        for r in release:validate_reference(r)
        probe_ids={r['problem_id'] for r in read_jsonl(DATA/'probes.jsonl')}
        sentinel=read_jsonl(RELEASE/'sentinel.jsonl')
        self.assertEqual(len({r['problem_id'] for r in sentinel}),48)
        self.assertTrue({r['problem_id'] for r in sentinel}<=probe_ids)
        for c in ('atomic','target','control'):
            self.assertEqual(sum(r['category']==c for r in sentinel),16)

    def test_complete_queue_no_outcome_selection(self):
        d=dry_run();self.assertEqual(d['updates'],1120);self.assertEqual(d['generations'],4704)
        self.assertEqual([r['experiment_id'] for r in d['training_runs']], [f'E{i:03d}' for i in range(30,37)])
        self.assertEqual(len(TRAINING),7)
        for kwargs in (dict(retention=0,probe_p=1,paths_gain=-1,nll_improved=False),dict(accuracy=0)):
            self.assertTrue(continue_after_measurement(hard_errors=[],resource_available=True,**kwargs))
        self.assertFalse(continue_after_measurement(hard_errors=['wrong_label'],resource_available=True))
        self.assertFalse(continue_after_measurement(hard_errors=[],resource_available=False))
        for n in (32,256):
            lr=learning_rates(n)
            self.assertEqual(max(lr),5e-5);self.assertEqual(lr[-1],1e-5)
        self.assertEqual(sum(e['generations'] for e in evaluation_queue())-96,4608)

    def test_generation_reservation_is_not_historical_or_resettable(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'budget.json';b=GenerationBudget(p,10)
            self.assertEqual(b.used,0);b.reserve('C-probes',4)
            with self.assertRaises(ValueError):b.reserve('C-probes',4)
            with self.assertRaises(ValueError):b.reserve('B-probes',7)
            with self.assertRaises(FileExistsError):GenerationBudget(p,10)
            self.assertEqual(json.loads(p.read_text())['used'],4)

    def test_question_paired_intervals_and_finite_pass4(self):
        # Identical paired outputs must have exactly zero contrast uncertainty.
        stat=paired_interval([0,0,0,0],['a','a','b','b'])
        self.assertEqual(stat['question_ci'],[0,0]);self.assertEqual(stat['cluster_ci'],[0,0])
        self.assertIsNone(paired_interval([0,1],['same','same'])['cluster_ci'])
        rs=[dict(problem_id='q',sample_index=i,score=dict(correct=(i==0),parsed=True,completed=True,failure='none'),
                 stop={'stop_reason':'native_eos'},independent_trace_status='verified',reference_program_class='unknown') for i in range(4)]
        result=per_question(rs)['q'];self.assertEqual(result['pass_at_1'],.25);self.assertEqual(result['pass_at_4'],1.)
        self.assertNotIn('pass_at_8',result)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(17);torch.set_num_threads(1)
        self.config=Qwen2Config(vocab_size=64,hidden_size=32,intermediate_size=64,
            num_hidden_layers=1,num_attention_heads=4,num_key_value_heads=2,max_position_embeddings=64,attention_dropout=0)
        self.model=attach(Qwen2ForCausalLM(self.config))
        self.rows=[dict(input_ids=[1,2,3,4,5],labels=[-100,-100,3,4,5],n_supervised=3,n_processed=5)]

    def step(self,model,opt):
        opt.zero_grad(set_to_none=True);accumulate_gradients(model,self.rows,0,1,'cpu')
        torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad],1.);opt.step()

    def test_recovery_exact_continuation_and_parent_reset(self):
        opt=new_optimizer(self.model,5e-5);self.step(self.model,opt)
        base=parameter_digest(self.model)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);save_recovery(self.model,opt,p/'recovery',1,'fixed','cpu')
            save_adapter(self.model,p/'parent')
            sibling=copy.deepcopy(self.model);sibling_opt=new_optimizer(sibling,5e-5)
            self.assertFalse(sibling_opt.state)
            restore_adapter(sibling,p/'parent')
            self.assertEqual(parameter_digest(sibling,True),parameter_digest(self.model,True))
            with self.assertRaises(ValueError):load_recovery(sibling,sibling_opt,p/'recovery','different','cpu')
            self.assertEqual(load_recovery(sibling,sibling_opt,p/'recovery','fixed','cpu'),1)
            self.assertTrue(sibling_opt.state)
            self.step(self.model,opt);self.step(sibling,sibling_opt)
            self.assertEqual(parameter_digest(self.model,True),parameter_digest(sibling,True))
            self.assertEqual(base,parameter_digest(self.model))
            save_recovery(self.model,opt,p/'recovery',2,'fixed','cpu')
            self.assertEqual(len(list((p/'recovery').glob('*.pt'))),1)
            # Scientific parent remains immutable despite rolling recovery pruning.
            restore_adapter(sibling,p/'parent');self.assertNotEqual(parameter_digest(sibling,True),parameter_digest(self.model,True))

    def test_training_writes_recoverable_state_and_frozen_dose(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);before=parameter_digest(self.model)
            h,ck=train(self.model,self.rows,[[0]]*2,learning_rates(2),SimpleNamespace(pad_token_id=0),p,
                identity={'fixture':True},checkpoint_steps={2},device='cpu')
            self.assertEqual(len(h),2);self.assertEqual(sum(r['supervised_tokens'] for r in h),6)
            self.assertEqual(before,parameter_digest(self.model));self.assertEqual(set(ck),{'0','2'})
            self.assertEqual(json.loads((p/'recovery/latest.json').read_text())['step'],2)


if __name__=='__main__':unittest.main()
