"""NO_REAL_MODEL orchestration and immutable budget checks."""
import hashlib
import json
import os
from contextlib import ExitStack, contextmanager
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from experiments.post_e039_decision_supervision import launcher, queue
from experiments.thursday_probe.common import dump

class Budgets(unittest.TestCase):
    def test_counts_and_roles(self):
        events=queue.evaluation_queue()
        self.assertEqual(len(events),38);self.assertEqual(sum(e['generations'] for e in events),4736)
        self.assertEqual(sum(e['generations'] for e in events if e['view']=='stage_a'),640)
        self.assertEqual(sum(e['generations'] for e in events if e['view']=='midpoint'),128)
    def test_independent_caps_and_duplicate_refusal(self):
        with tempfile.TemporaryDirectory() as t:
            g=launcher.GenerationBudget(Path(t)/'g.json');f=launcher.ForwardBudget(Path(t)/'f.json')
            g.reserve('g',5000);f.reserve('f',16384)
            for budget in (g,f):
                with self.assertRaises(ValueError):budget.reserve('another',1)
                with self.assertRaises(ValueError):budget.reserve('g' if budget is g else 'f',1)
            self.assertEqual(g.used,5000);self.assertEqual(f.used,16384)
    def test_budget_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'f.json';b=launcher.ForwardBudget(p);b.reserve('one',2)
            r=json.loads(p.read_text());r['used']=0;p.write_text(json.dumps(r))
            with self.assertRaises(ValueError):b.record()
    def test_whole_rental_limit_includes_setup(self):
        with tempfile.TemporaryDirectory() as t:
            start=launcher.epoch('2026-09-17T05:56:00+00:00')
            with patch.object(launcher.time,'time',return_value=start+1000):
                budget=launcher.RentalBudget(Path(t)/'r.json','2026-09-17T05:56:00+00:00',7.98)
                r=budget.remaining();self.assertEqual(r['remaining_hard_seconds'],13400)
                self.assertEqual(r['worker_deadline_epoch'],start+14400-600)
                self.assertAlmostEqual(r['rental_cost_proxy_cny'],1000*7.98/3600)

class Model:
    training=False
    adapter=None
    def cuda(self):return self
    def train(self,mode=True):self.training=mode;return self
    def eval(self):return self.train(False)


def run_fake(tokenizer_dir, fail_alignment=False):
    from experiments.post_e039_decision_supervision import diagnostics
    registered=json.loads((queue.ROOT/'registration.json').read_text())['entries']
    run_ids={r['state']:r['run_id'] for r in registered}
    count={'segments':0,'new_generations':0,'new_forwards':0,'train_before_alignment':False}
    digest=lambda run,step:hashlib.sha256(f'NO_REAL_MODEL/{run}/{step}'.encode()).hexdigest()
    def pd(model,adapter_only=False):return dict(sha256=model.adapter if adapter_only else queue.BASE_SHA,parameters=0)
    def restore(model,path):
        r=json.loads((Path(path)/'checkpoint_identity.json').read_text());model.adapter=r['parameter_digest']['sha256'];return r
    def train(model,encoded,schedule,lrs,tokenizer,out,*,identity,objective,end_step,deadline):
        count['segments']+=1
        assert json.loads((Path(queue.OUT)/'progress.json').read_text())['stage_a_alignment_passed']
        history=[dict(step=s+1,seconds=.001,supervised_tokens=sum(encoded[i]['n_supervised'] for i in schedule[s]),processed_tokens=sum(encoded[i]['n_processed'] for i in schedule[s])) for s in range(end_step)]
        out=Path(out);(out/'recovery').mkdir(exist_ok=True);queue.atomic_json(out/'recovery/latest.json',dict(step=end_step))
        model.adapter=digest(out.name,end_step)
        for step in (64,128):
            if end_step>=step:
                d=out/f'checkpoint_{step}';d.mkdir(exist_ok=True);queue.atomic_json(d/'checkpoint_identity.json',dict(parameter_digest=dict(sha256=digest(out.name,step),parameters=0),files_sha256={}))
        return dict(step=end_step,cumulative_history=history)
    def generate(model,tokenizer,rows,path,event,identity,remaining,budget,deadline):
        expected=queue.PARENTS[event['state']][1] if event['state'] in queue.PARENTS else digest(run_ids[event['state']],event['checkpoint_step'])
        assert model.adapter==expected,'wrong checkpoint evaluated'
        path=Path(path)
        if not path.exists():budget.reserve('MOCK_'+event['name'],event['generations']);path.write_text('NO_REAL_MODEL\n');count['new_generations']+=event['generations']
        return dict(status='completed',completed_records=event['generations'],reason=None,batch_timings=[],substreams=[])
    def forward(model,rows,path,identity,budget):
        path=Path(path)
        if path.exists():return json.loads(path.read_text())
        budget.reserve('MOCK_'+identity['state']+'/'+path.stem,len(rows));count['new_forwards']+=len(rows)
        r=dict(status='completed',completed_records=len(rows),records=[],forward_calls=len(rows),input_tokens=0,seconds=0,NO_REAL_MODEL=True);dump(path,r);return r
    def decomposition(model,tokenizer,rows,spans,path,*,identity,forward_budget,deadline):return forward(model,rows,path,identity,forward_budget)
    def candidates(model,contexts,path,*,identity,forward_budget,deadline):return forward(model,contexts,path,identity,forward_budget)
    @contextmanager
    def observer(model,tokenizer,cases,path,*,identity):
        path=Path(path);path.parent.mkdir(exist_ok=True,parents=True)
        yield
        if not path.exists():dump(path,dict(status='failed' if fail_alignment else 'passed',genuine_mismatches=int(fail_alignment),NO_REAL_MODEL=True))
    with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
        root=Path(temp);out=root/'run';parents=root/'parents'
        for state,(run,sha) in queue.PARENTS.items():
            p=parents/run/'checkpoint_256';p.mkdir(parents=True);dump(p/'checkpoint_identity.json',dict(parameter_digest=dict(sha256=sha,parameters=0),files_sha256={}))
        stack.enter_context(patch.object(queue,'OUT',out))
        stack.enter_context(patch.dict(os.environ,{'DECISION_TRAINING_BOUNDED':launcher.RUN_ID,'DECISION_TRAINING_DEADLINE':str(time.time()+100000),'DECISION_TRAINING_PUBLISHED_COMMIT':'0'*40}))
        stack.enter_context(patch.object(launcher,'source',return_value=dict(source_commit='0'*40,source_files_sha256={})))
        stack.enter_context(patch('transformers.AutoModelForCausalLM.from_pretrained',return_value=Model()))
        stack.enter_context(patch.object(queue,'attach',side_effect=lambda m:m))
        stack.enter_context(patch.object(queue,'parameter_digest',side_effect=pd));stack.enter_context(patch.object(queue,'restore_adapter',side_effect=restore))
        stack.enter_context(patch.object(queue,'train_segment',side_effect=train));stack.enter_context(patch.object(queue,'run_event',side_effect=generate))
        stack.enter_context(patch.object(diagnostics,'run_decomposition',side_effect=decomposition));stack.enter_context(patch.object(diagnostics,'run_candidates',side_effect=candidates))
        stack.enter_context(patch.object(diagnostics,'observe_greedy_alignment',side_effect=observer));stack.enter_context(patch.object(diagnostics,'make_alignment_cases',return_value=[]))
        if fail_alignment:
            try:queue.worker(tokenizer_dir,parents)
            except ValueError as exc:assert 'consistency' in str(exc)
            else:raise AssertionError('Alignment failure did not stop before training')
            assert count['segments']==0;return count
        assert queue.worker(tokenizer_dir,parents)==0
        launcher._validate_completion(out,launcher.GenerationBudget(out/'generation_ledger.json'))
        assert count['new_generations']==4736 and count['new_forwards']==7552
        before=dict(count);assert queue.worker(tokenizer_dir,parents)==0
        assert count==before,'Completed durable work repeated on resume'
        return count

class WholeWorker(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('DECISION_TEST_TOKENIZER'),'Pinned local tokenizer required')
    def test_full_no_real_model_and_resume(self):run_fake(os.environ['DECISION_TEST_TOKENIZER'])
    @unittest.skipUnless(os.environ.get('DECISION_TEST_TOKENIZER'),'Pinned local tokenizer required')
    def test_real_consistency_failure_stops_before_training(self):run_fake(os.environ['DECISION_TEST_TOKENIZER'],True)

if __name__=='__main__':unittest.main()
