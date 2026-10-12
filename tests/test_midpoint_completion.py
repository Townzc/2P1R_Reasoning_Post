import copy
import tempfile
import unittest
from unittest.mock import patch
from contextlib import ExitStack
from pathlib import Path
from experiments.sft_allocation_midpoint.common import dump,digest,manifest
from experiments.sft_allocation_midpoint.completion import inspect_parent,validate_completion,continue_main

class CompletionTests(unittest.TestCase):
    def files(self,p):
        for i in range(1,129):
            row={'step':i,'supervised_tokens':2,'processed_tokens':3}
            dump(p/'intents'/f'update_{i:04d}.json',row)
            dump(p/'completed'/f'update_{i:04d}.json',{**row,'cumulative_targets':2*i,'cumulative_processed':3*i})
        for step,n in [(64,80),(128,48)]:
            for i in range(0,n,8):
                unit=f'observed80_step{step}_batch_{i:04d}.json'
                dump(p/'intents'/unit,{'count':8});dump(p/'completed'/unit,{'count':8})
        dump(p/'intents/observed80_step128_batch_0048.json',{'count':8})
        ck={'supervised_tokens':256,'processed_tokens':384}
        dump(p/'checkpoint_0128/manifest.json',ck)
        return ck
    def finish(self,p):
        m=manifest(p);dump(p/'failure_manifest.json',m);return digest(m)
    def test_exactly_committed_prefix_and_one_unknown_diagnostic_are_admissible(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);ck=self.files(p);h=self.finish(p)
            i,d=inspect_parent(p,h,ck)
            self.assertEqual(set(i)-set(d),{'observed80_step128_batch_0048'})
            self.assertEqual(sum(x.get('count',0) for x in d.values()),128)
    def test_unknown_training_update_is_never_replayed(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);ck=self.files(p);dump(p/'intents/update_0129.json',{'step':129});h=self.finish(p)
            with self.assertRaisesRegex(ValueError,'ambiguous'):inspect_parent(p,h,ck)
    def test_completed_or_ambiguous_future_eval_cannot_be_regenerated(self):
        for name in ['observed80_step128_batch_0056','endpoint431_batch_0000']:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as t:
                p=Path(t);ck=self.files(p);dump(p/'intents'/(name+'.json'),{'count':8});h=self.finish(p)
                with self.assertRaises(ValueError):inspect_parent(p,h,ck)
    def test_dose_mismatch_and_modified_parent_fail_closed(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);ck=self.files(p);h=self.finish(p)
            with self.assertRaises(ValueError):inspect_parent(p,h,{**ck,'supervised_tokens':257})
            (p/'completed/update_0128.json').write_text('{}')
            with self.assertRaises(ValueError):inspect_parent(p,h,ck)
    def setup_binding(self):
        queue=[{'run_id':'breadth_17_resume','kind':'continue_main','arm':'breadth','seed':17},
               {'run_id':'mixed_17','kind':'main','arm':'mixed','seed':17},
               {'run_id':'mixed_23','kind':'main','arm':'mixed','seed':23}]
        base={'kind':'base','run_id':'base'};audit={'kind':'audit'}
        plan={'campaign_id':'child','deadline_epoch':999,'slots':{n:{} for n in ['breadth_17_resume','mixed_17','mixed_23','base','audit','controller']}}
        terminal={'status':'failed'}
        binding={'schema':'remaining_work_v1','campaign':'child','parent_campaign':'parent','deadline_epoch':999,
                 'old_app_stopped':True,'old_containers':0,'configs_sha256':digest([queue,base,audit]),'plan_sha256':digest(plan),
                 'parent_terminals':{'controller':terminal,'breadth_17':terminal}}
        store={f'midpoint/parent/terminal/{n}':terminal for n in ['controller','breadth_17']}
        return store,plan,binding,queue,base,audit
    def test_only_unattempted_slots_and_bound_failed_parent_are_admitted(self):
        args=self.setup_binding();before=copy.deepcopy(args[0]);validate_completion(*args)
        self.assertEqual(args[0],before)
        for key in ['claim/mixed_17','intent/base','dispatch/mixed_23/intent']:
            args=self.setup_binding();args[0]['midpoint/parent/'+key]={}
            with self.subTest(key=key),self.assertRaises(ValueError):validate_completion(*args)
    def test_changed_budget_deadline_or_queue_not_silently_admitted(self):
        for kind in ('deadline','live','queue','terminal'):
            args=self.setup_binding()
            if kind=='deadline':args[1]['deadline_epoch']+=1
            if kind=='live':args[2]['old_containers']=1
            if kind=='queue':args[3][1]['seed']=99
            if kind=='terminal':args[0]['midpoint/parent/terminal/controller']={'status':'completed'}
            with self.subTest(kind=kind),self.assertRaises(ValueError):validate_completion(*args)

    def test_continuation_restores_before_work_and_skips_ambiguous_eight(self):
        import torch,types
        from experiments.sft_allocation_midpoint import checkpoint as ck
        model=torch.nn.Linear(2,2);opt=torch.optim.AdamW(model.parameters())
        model(torch.ones(1,2)).sum().backward();opt.step()
        schedule=[[0]]*256;rates=[.001]*256
        state=ck.snapshot(model,opt,{'original':True},128,262077,400000,rates,schedule)
        observations=[{'problem_id':str(i)} for i in range(80)]
        recipe={'arm':'breadth','seed':17,'identity':state['identity'],'lrs':rates,'budget':{'same':True}}
        env={'versions':{'torch':'test'},'cuda':'test','deterministic_algorithms':True,'gpu':'GPU'}
        events=[]
        def evaluate(model,tok,rows,out,name,journal):
            events.append((name,[r['problem_id'] for r in rows]))
            return {'question_correct':{r['problem_id']:True for r in rows},'n':len(rows)}
        def training(model,tok,opt,encoded,schedule,rates,out,journal,identity,**kw):
            self.assertEqual(kw['start'],128);self.assertEqual(kw['targets'],262077)
            self.assertEqual(kw['save_steps'],{160,192,224,256})
            self.assertTrue(ck.same(ck.snapshot(model,opt,identity,128,262077,400000,rates,schedule),state))
            kw['callback'](256,model)
            return [{'seconds':1}],524288,800000
        def rows(path):
            path=Path(path)
            if path.name=='observed80.jsonl':return observations
            if path.name=='endpoint431.jsonl':return [{'problem_id':'endpoint'}]
            if path.name.endswith('_scored.jsonl'):
                start=int(path.name.split('_')[1]);return [{'problem_id':str(i),'task_score':{'task_answer_correct':True}} for i in range(start,start+8)]
            return []
        with tempfile.TemporaryDirectory() as t,ExitStack() as stack:
            p=Path(t);parent=p/'parent';out=p/'child';out.mkdir();assets=p/'assets'
            dump(parent/'recipe.json',recipe);dump(parent/'environment.json',env)
            dump(parent/'observed80_step64/summary.json',{'n':80})
            dump(assets/'inputs/breadth_seed17.json',{'updates':schedule})
            ck.save(parent,state)
            stack.enter_context(patch('experiments.sft_allocation_midpoint.completion.inspect_parent',return_value=({}, {f'update_{i:04d}':{'seconds':1} for i in range(1,129)})))
            target='experiments.sft_allocation_midpoint.runtime.'
            fresh=torch.nn.Linear(2,2);freshopt=torch.optim.AdamW(fresh.parameters())
            for name,value in [('new_model',lambda *a:(fresh,None)),('optimizer_for',lambda *a:freshopt),('encode',lambda *a:[]),
                               ('budget_report',lambda *a:recipe['budget']),('read_jsonl',rows),('evaluate',evaluate),('train',training),('nll',lambda *a:{})]:
                stack.enter_context(patch(target+name,side_effect=value))
            recovery={'failure_manifest_digest':'x','checkpoint_manifest':{}}
            result=continue_main(assets,parent,out,types.SimpleNamespace(check=lambda:None),{'recovery':recovery,'lrs':rates},env)
            self.assertEqual(events[0],('observed80_step128_remaining',[str(i) for i in range(56,80)]))
            self.assertEqual(result['new_committed_updates'],128)
            self.assertEqual(result['curve']['128']['unknown_n'],8)
            self.assertEqual([k for k,v in result['curve']['128']['question_correct'].items() if v is None],[str(i) for i in range(48,56)])

if __name__=='__main__':unittest.main()
