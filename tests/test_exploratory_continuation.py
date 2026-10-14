"""New continuation failure boundaries; no cloud/model or old experiment rerun."""
import ast,copy,json,tempfile,unittest
from pathlib import Path
from experiments.sft_allocation_midpoint.common import dump,digest,manifest,read
from experiments.sft_exploratory_20261014.continuation_prefix import inspect_prefix,PARENT
from experiments.sft_exploratory_20261014.continuation_binding import claim_parent_suffix,marker,parent_records,validate_release,validate_spec,SCOPE


class Store(dict):
    def put(self,key,value,skip_if_exists=False):
        if key in self and skip_if_exists:return False
        self[key]=value;return True


def binding_fixture():
    from experiments.sft_exploratory_20261014.continuation_prefix import COUNTS
    configs={k+'_remaining_r1':dict(run_id=k+'_remaining_r1',logical_run=k,offset=n,max_seconds=4800,
                  updates=0,targets=0,input_sha256='x') for k,n in COUNTS.items()}
    plan=dict(campaign_id='exploratory-continuation-20261014-r1',total_cap_cents=2016,
              stage_caps_cents=dict(suffix=2016),slots={k:dict(stage='suffix',reserved_cents=672) for k in configs})
    proofs={k:dict(passed=True,binding=dict(offset=n,original_claim={'id':k},original_terminal={'status':'failed'})) for k,n in COUNTS.items()}
    spec=dict(plan=plan,configs=configs,source_files={'file':'hash'},total_spending_cap_cents=3000,exploratory=True,preregistered=False,
              original_admission=dict(input_manifest_sha256='x'),prefix_proofs=proofs,new_training_updates=0,
              repeat_generation_allowed=False,budget=dict(original_stopped_cost_allowance_cents=700,other_cost_allowance_cents=284,
              original_lifetime_resource_bound_cents=640,original_delayed_meter_cents_ceiling=544))
    return spec,configs['base_4shot_remaining_r1']


class ContinuationTests(unittest.TestCase):
    def test_atomic_parent_suffix_never_reacquired(self):
        spec,cfg=binding_fixture();store=Store(parent_records(spec,cfg))
        claim_parent_suffix(store,spec,cfg)
        with self.assertRaises(ValueError):claim_parent_suffix(store,spec,cfg)

    def test_parent_completed_or_changed_rejected(self):
        spec,cfg=binding_fixture();store=Store(parent_records(spec,cfg));key=list(store)[-1]
        store[key]={'status':'completed'}
        with self.assertRaises(ValueError):claim_parent_suffix(store,spec,cfg)

    def test_marker_exact_prefix_and_config(self):
        spec,cfg=binding_fixture();one=marker(spec,cfg);cfg=dict(cfg,offset=256)
        self.assertNotEqual(one[1],marker(spec,cfg)[1])

    def test_budget_includes_failed_originals(self):
        spec,cfg=binding_fixture();validate_spec(spec,spec['plan'],cfg,spec['source_files'])
        spec['budget']['other_cost_allowance_cents']+=1
        with self.assertRaises(ValueError):validate_spec(spec,spec['plan'],cfg,spec['source_files'])

    def test_parent_meter_over_allowance_refused(self):
        spec,cfg=binding_fixture();spec['budget']['original_delayed_meter_cents_ceiling']=701
        with self.assertRaises(ValueError):validate_spec(spec,spec['plan'],cfg,spec['source_files'])

    def test_no_training_or_offset_change(self):
        for key,value in [('updates',1),('targets',1),('offset',256),('max_seconds',6001)]:
            spec,cfg=binding_fixture();cfg[key]=value
            with self.assertRaises(ValueError):validate_spec(spec,spec['plan'],cfg,spec['source_files'])

    def test_old_proposal_acceptance_does_not_admit(self):
        spec,cfg=binding_fixture()
        with self.assertRaises(ValueError):validate_release(spec,spec['plan'],cfg,
          dict(source_files=spec['source_files'],acceptance=dict(scope='exploratory-vocabulary-cache-proposal-code')))

    def test_cached_audit_body_exact_original_ast(self):
        def node(path,name):return next(n for n in ast.parse(Path(path).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
        old=node('experiments/sft_exploratory_20261014/runtime.py','audit_batch')
        new=node('experiments/sft_exploratory_20261014/cached_audit.py','audit_batch')
        self.assertEqual(ast.dump(old,include_attributes=False),ast.dump(new,include_attributes=False))

    def test_child_never_calls_training_or_download(self):
        tree=ast.parse(Path('experiments/sft_exploratory_20261014/continuation_runtime.py').read_text())
        names=[n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        self.assertNotIn('train',names);self.assertNotIn('step',names);self.assertNotIn('save',names)
        self.assertNotIn('urlopen',names);self.assertIn('restore',names)

    def test_source_includes_every_new_dependency(self):
        tree=ast.parse(Path('experiments/sft_exploratory_20261014/modal_continuation.py').read_text())
        sources=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCES' for t in n.targets))
        self.assertEqual(len(sources),len(set(sources)))
        for name in ['continuation_prefix','cached_audit','continuation_binding','continuation_runtime','modal_continuation']:
            self.assertIn('experiments/sft_exploratory_20261014/'+name+'.py',sources)

    def test_checkpoint_restore_copies_exact_without_step(self):
        import torch
        from experiments.sft_allocation_midpoint import checkpoint as ck
        model=torch.nn.Linear(2,1);opt=torch.optim.AdamW(model.parameters())
        state=ck.snapshot(model,opt,{'fixture':True},256,524287,630774,[],[])
        with torch.no_grad():
            for p in model.parameters():p.add_(3)
        ck.restore(model,opt,state)
        self.assertTrue(all(torch.equal(p.detach().cpu(),state['adapter'][n]) for n,p in model.named_parameters()))
        self.assertTrue(ck.same(ck.cpu(opt.state_dict()),state['optimizer']))


class PrefixTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        r=Path(self.temp.name);self.root=r/'parent';self.inputs=r/'inputs';self.root.mkdir();self.inputs.mkdir()
        cfg=dict(input_sha256='i');self.spec=dict(configs={'base_4shot':cfg},plan={'p':1},source_files={'s':'h'})
        b='midpoint/'+PARENT+'/';self.base=b
        bound=dict(config_sha256=digest(cfg),data_sha256='i',source_sha256=digest(self.spec['source_files']))
        claim=dict(intent_sha256=digest(bound));self.db={b+'intent/base_4shot':bound,b+'claim/base_4shot':claim}
        dump(self.root/'intent.json',dict(config=cfg,plan=self.spec['plan'],release=dict(source_files=self.spec['source_files'])))
        dump(self.root/'admission.json',self.spec)
        rows=[dict(problem_id=str(i)) for i in range(1319)]
        (self.inputs/'gsm8k_test1319.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
        for start in range(0,272,16):
            unit=f'endpoint1319_batch_{start:04d}';ids=[r['problem_id'] for r in rows[start:start+16]]
            intent=dict(problem_ids=ids,count=16);dump(self.root/'intents'/(unit+'.json'),intent)
            self.db[b+'base_4shot/unit/'+unit]=intent
            raw=f'endpoint1319/batch_{start:04d}_raw.json';scored=f'endpoint1319/batch_{start:04d}_scored.jsonl'
            dump(self.root/raw,dict(problem_ids=ids,batch_output_ids=[[0]]*16))
            (self.root/scored).write_text(''.join(json.dumps(x)+'\n' for x in rows[start:start+16]))
            if start<256:
                from experiments.sft_allocation_midpoint.common import sha
                done=dict(count=16,raw_sha256=sha(self.root/raw),scored_sha256=sha(self.root/scored))
                dump(self.root/'completed'/(unit+'.json'),done);self.db[b+'base_4shot/done/'+unit]=done
        files=manifest(self.root);dump(self.root/'failure_manifest.json',files)
        self.db[b+'terminal/base_4shot']=dict(status='failed',claim_sha256=digest(claim),evidence_sha256=digest(files))

    def test_unacknowledged_saved_batch_is_reused(self):
        b,p=inspect_prefix(self.root,self.inputs,self.db,'base_4shot',self.spec)
        self.assertEqual(len(p),272);self.assertEqual(b['remaining'],1047)
        self.assertFalse(b['batches'][-1]['original_ack_present'])
        self.assertFalse((self.root/'completed/endpoint1319_batch_0256.json').exists())

    def test_attempt_without_saved_raw_refused(self):
        (self.root/'endpoint1319/batch_0256_raw.json').unlink()
        with self.assertRaises((ValueError,FileNotFoundError)):inspect_prefix(self.root,self.inputs,self.db,'base_4shot',self.spec)

    def test_extra_remote_attempt_refused(self):
        self.db[self.base+'base_4shot/unit/endpoint1319_batch_0272']={}
        with self.assertRaises(ValueError):inspect_prefix(self.root,self.inputs,self.db,'base_4shot',self.spec)

    def test_extra_saved_batch_refused(self):
        dump(self.root/'endpoint1319/batch_0272_raw.json',{})
        with self.assertRaises(ValueError):inspect_prefix(self.root,self.inputs,self.db,'base_4shot',self.spec)


if __name__=='__main__':unittest.main()
