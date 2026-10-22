"""New extension boundaries only. No old production or successful tests rerun."""
import ast
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from experiments.p011.ext4b_runtime_contract import cost_window,admit_attempt,JOBS
from experiments.p011.ext4b_path import budget_check
from experiments.p011.ext4b_encoded import EncodedRows
from experiments.p011.ext4b_training import validate_resume_metadata,ResumableJournal
from experiments.p011.ext4b_execution import evaluate_with_prefix
from experiments.sft_allocation_midpoint.common import digest,dump,read
from scripts.prepare_p011_ext4b_infra_resume import classify_evidence

class NewExt4BRuntimeBoundaries(unittest.TestCase):
    def test_hard_money_window_includes_parent_and_each_startup(self):
        fresh=cost_window('4.90720');resumed=cost_window('4.90720','12.50')
        self.assertLess(resumed['worker_seconds'],fresh['worker_seconds']);self.assertLessEqual(Decimal(resumed['cumulative_cell_upper_usd']),45)
        for args in [('0',),('NaN',),('4.9','40'),('4.9','-1'),('4.9','0','0')]:
            with self.assertRaises(ValueError):cost_window(*args)
        b={'observed_epoch':1000,'pair_cap_usd':'90','per_cell_cap_usd':'45','requested_job':JOBS[0],'requested_attempt':1,'slots_after_requested':2,'hourly_rate_usd':'4.90720','prior_job_compute_upper_usd':'0','retained_noncompute_usd':'5','other_cell_retained_upper_usd':'45','check':fresh,'pair_total_upper_usd':str(Decimal(fresh['cumulative_cell_upper_usd'])+45)}
        self.assertEqual(budget_check(b,JOBS[0],1,1001),fresh)
        for patch in [{'slots_after_requested':9},{'slots_after_requested':-1},{'observed_epoch':-3000},{'other_cell_retained_upper_usd':'0'},{'pair_total_upper_usd':'70'}]:
            with self.assertRaises(ValueError):budget_check({**b,**patch},JOBS[0],1,1001)

    def test_lazy_encoded_view_is_exact_canonical_json_and_row_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'rows.jsonl';rows=[{'path_id':str(i),'parent_sha256':str(i),'n_supervised':1,'n_processed':2,'input_ids':[1,151645],'labels':[-100,151645]} for i in range(3024)]
            file.write_text(''.join(json.dumps(x)+'\n' for x in rows));meta=[{k:r[k] for k in ('path_id','parent_sha256','n_supervised','n_processed')} for r in rows]
            lazy=EncodedRows(file,meta,3024);self.assertEqual(digest(lazy),digest(rows));self.assertEqual(lazy[-1]['input_ids'],rows[-1]['input_ids'])
            self.assertEqual(lazy[0].loaded,None);meta[0]['n_supervised']=9
            with self.assertRaises(ValueError):lazy[0]['input_ids']

    def test_exact_toy_adam_rng_checkpoint_restore_and_wrong_cursor_rejected(self):
        import torch,numpy as np,random
        from experiments.sft_allocation_midpoint import checkpoint
        torch.manual_seed(17);np.random.seed(17);random.seed(17)
        model=torch.nn.Linear(2,1);optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=0,foreach=False)
        x=torch.ones((1,2));model(x).sum().backward();optimizer.step();optimizer.zero_grad(set_to_none=True)
        identity={'job':'toy'};plan={'optimizer_updates':500,'updates':[[0]]*500};rates=[.001]*500
        for s in optimizer.state.values():s['step'].fill_(500)
        state=checkpoint.snapshot(model,optimizer,identity,500,1000,1500,rates,plan['updates']);state.update(schema='p011_ext4b_resume_state_v1',adaptation_mode='full');record={k:state[k] for k in ('step','supervised_tokens','processed_tokens')};record['identity_sha256']=digest(identity)
        validate_resume_metadata(state,record,identity,plan,rates)
        expected=(random.random(),np.random.rand(),torch.rand(3));clone=torch.nn.Linear(2,1);other=torch.optim.AdamW(clone.parameters(),lr=.001,weight_decay=0,foreach=False);checkpoint.restore(clone,other,state)
        actual=(random.random(),np.random.rand(),torch.rand(3));self.assertEqual(expected[:2],actual[:2]);self.assertTrue(torch.equal(expected[2],actual[2]));self.assertTrue(checkpoint.same(checkpoint.cpu(optimizer.state_dict()),checkpoint.cpu(other.state_dict())))
        for a,b in zip(model.parameters(),clone.parameters()):self.assertTrue(torch.equal(a,b))
        wrong=deepcopy(state);wrong['cursor']=499
        with self.assertRaises(ValueError):validate_resume_metadata(wrong,record,identity,plan,rates)
        wrong=deepcopy(state);next(iter(wrong['optimizer']['state'].values()))['step'].fill_(499)
        with self.assertRaises(ValueError):validate_resume_metadata(wrong,record,identity,plan,rates)

    def test_one_resume_requires_genuine_infra_not_cap_or_science(self):
        self.assertTrue(classify_evidence('provider_preemption','provider preempted container','preempted'))
        for text in ('exit code 124; preempted','nonfinite gradient; preempted','CUDA device assert; preempted'):
            with self.assertRaises(ValueError):classify_evidence('provider_preemption',text,'preempted')
        with self.assertRaises(ValueError):classify_evidence('network','unrelated RuntimeError','RuntimeError')
        with self.assertRaises(ValueError):admit_attempt(JOBS[0],3,{},'checkpoint',{})
        with self.assertRaises(ValueError):admit_attempt(JOBS[0],2,None,None,None)

    def test_acknowledged_endpoint_without_cycle_fails_before_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent=Path(tmp)/'parent';out=Path(tmp)/'out';out.mkdir();dump(parent/'completed/eval_0000.json',{'count':1})
            class Engine:
                def generate(self,*a,**k):raise AssertionError('Must not regenerate completed endpoint')
            import unittest.mock
            with unittest.mock.patch('experiments.p011.ext4b_execution.sampling',return_value={}):
                with self.assertRaisesRegex(ValueError,'never regenerate'):
                    evaluate_with_prefix(Engine(),dict,[{'id':'x'}],[151645],out,'new',None,lambda:None,lambda:None,lambda *a:{},{'parent_output':str(parent)})

    def test_original_training_update_math_ast_unchanged(self):
        def body(path,name):
            root=ast.parse(Path(path).read_text());fn=next(n for n in root.body if isinstance(n,ast.FunctionDef) and n.name==name)
            loop=next(n for n in fn.body if isinstance(n,ast.For) and ast.unparse(n.target)=='(step, indices)')
            start=next(i for i,n in enumerate(loop.body) if isinstance(n,ast.Expr) and ast.unparse(n).startswith('model.train('))
            end=next(i for i,n in enumerate(loop.body) if isinstance(n,ast.Expr) and ast.unparse(n).startswith('journal.finish_update('))
            return ast.dump(ast.Module(body=loop.body[start:end+1],type_ignores=[]),include_attributes=False)
        self.assertEqual(body('experiments/p011/long_lr_r2_training.py','train_terminal'),body('experiments/p011/ext4b_training.py','train_with_checkpoints'))

    def test_module_entry_and_new_wall_watchdog_are_source_bound(self):
        module=Path('experiments/p011/modal_ext4b.py').read_text();entry=Path('scripts/run_p011_ext4b_once.py').read_text()
        self.assertIn("if __name__ == 'modal_ext4b'",module);self.assertIn("'run','-m','experiments.p011.modal_ext4b'",entry)
        self.assertIn("check['worker_seconds']+check['startup_seconds']+60",entry);self.assertIn("'stop',app,'--yes'",entry)

if __name__=='__main__':unittest.main()
