"""New remaining-only body/admission/provenance checks, entirely offline."""
import ast,copy,json,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
from experiments.p010 import cue_remaining as c,cue_remaining_binding as b
from experiments.p010.common import read,dump,manifest,sha
from tests.test_p010_cue_benchmark_group import Store,toy_roster,ENGINE
from scripts.audit_p010_cue_remaining import keys
from scripts.score_p010_cue_remaining import execute


class Remaining(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        inputs=root/'inputs';out=root/'out';out.mkdir();store=Store();claim={'new':True}
        parent=dict(claim={'old':True},terminal={'status':'failed','error':'original path'},cell={'reserved':True})
        store.values.update({c.PARENT+'/claim':parent['claim'],c.PARENT+'/terminal':parent['terminal'],c.PARENT+'/'+c.RUN+'/cell':parent['cell'],c.KEY+'/claim':claim})
        terminal={'status':'completed','synthetic':True};tkey='student/t72_s17_n400_k1/terminal';store.values[tkey]=terminal
        binding=dict(remote_path='/evidence/p010-20261019/students/t72_s17_n400_k1/merged',files={},
            parent=dict(terminal_key=tkey,terminal=terminal,original_merged_files={}),new_training_updates=0,new_checkpoint_loads=0,new_merge_operations=0)
        dump(inputs/(c.RUN+'.json'),toy_roster(c.RUN,2500))
        spec=dict(input_files=manifest(inputs),failed_parent=parent,corrected_model_binding=binding,observed_batch_seconds=[20.4121413230896,18.06444720200011])
        calls=[];invalid=[False]
        class LLM:
            def __init__(self,**kw):self.llm_engine=types.SimpleNamespace(vllm_config={});calls.append(('model',kw))
            def generate(self,prompts,params,use_tqdm):
                calls.append(('generate',len(prompts)))
                result=[types.SimpleNamespace(prompt_token_ids=p['prompt_token_ids'],outputs=[types.SimpleNamespace(token_ids=[2,151643],text='synthetic',finish_reason='stop',stop_reason=151643)]) for p in prompts]
                return result[:-1] if invalid[0] else result
        torch=types.SimpleNamespace(cuda=types.SimpleNamespace(device_count=lambda:1,get_device_name=lambda _: 'H100',get_device_properties=lambda _:types.SimpleNamespace(total_memory=80*1024**3)))
        modules={'vllm':types.SimpleNamespace(LLM=LLM,SamplingParams=lambda **kw:kw),'torch':torch}
        return inputs,out,store,claim,spec,calls,invalid,modules

    def run_body(self,f):
        inputs,out,store,claim,spec,calls,invalid,modules=f
        with patch.dict(sys.modules,modules),patch('experiments.p010.cue_benchmark_group.verify'),patch.object(c.time,'time',return_value=1),patch('experiments.learning_regime_p009.high_throughput_v1.actual_engine',return_value=ENGINE):
            return c.generate(inputs,out,spec,claim,0,1200,'12.16',store,types.SimpleNamespace(commit=lambda:None))

    def test_actual_new_body_generates_only2500_and_keeps_failed_parent(self):
        f=self.fixture();before=copy.deepcopy({k:v for k,v in f[2].values.items() if k.startswith(c.PARENT)})
        result=self.run_body(f)
        self.assertEqual(result['new_outputs'],2500);self.assertEqual(sum(x[1] for x in f[5] if x[0]=='generate'),2500)
        self.assertEqual(sum('/batch_done/' in k for k in f[2].values),10)
        self.assertEqual({k:v for k,v in f[2].values.items() if k.startswith(c.PARENT)},before)
        self.assertEqual(read(f[1]/'BEFORE_MODEL_FORECAST.json')['budget']['prior_reserved_usd'],'12.16')

    def test_original_unconfirmed_batch_permanently_blocks_before_model(self):
        f=self.fixture();f[2].values[c.PARENT+'/'+c.RUN+'/batch/00000']={'old_unconfirmed':True}
        with self.assertRaises(ValueError):self.run_body(f)
        self.assertEqual(f[5],[])

    def test_new_consumed_batch_cannot_generate_again(self):
        f=self.fixture();f[2].values[c.KEY+'/batch/00000']={'prior':True}
        with self.assertRaises(RuntimeError):self.run_body(f)
        self.assertFalse(any(x[0]=='generate' for x in f[5]))

    def test_malformed_return_is_saved_without_ack(self):
        f=self.fixture();f[6][0]=True
        with self.assertRaises(ValueError):self.run_body(f)
        self.assertEqual(len(read(f[1]/'raw/00000.json')),255)
        self.assertNotIn(c.KEY+'/batch_done/00000',f[2].values)

    def test_singular_model_path_rejected_before_model(self):
        f=self.fixture();f[4]['corrected_model_binding']['remote_path']='/evidence/p010-20261019/student/t72_s17_n400_k1/merged'
        with self.assertRaises(ValueError):self.run_body(f)
        self.assertEqual(f[5],[])

    def test_complete_old_times_and_elapsed_control_narrow_window(self):
        good=c.forecast(0,0,[],[20.4121413230896,18.06444720200011],'12.16')
        self.assertLess(good['total_seconds'],1170)
        with self.assertRaises(TimeoutError):c.forecast(300,0,[],[20.4121413230896],'12.16')
        with self.assertRaises(TimeoutError):c.forecast(0,1,[200],[20],'12.16')
        with self.assertRaises(ValueError):c.forecast(0,0,[],[20],'14.43')

    def test_owner_code_pass_does_not_replace_explicit_exception(self):
        with self.assertRaises(ValueError):b.owner_review({}, {'approved':False}, {}, 'not-opened')

    def test_exact_same_I_reservation_accounting_and_unknown_slots(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);paths=[];states={}
            for i,(category,n) in enumerate([('G','44'),('T','108.33'),('I','14.43')]):
                p=root/str(i);dump(p/'INTENT.json',dict(budget=dict(category=category,new_reserved_usd=n)));dump(p/'SUBMITTED.json',dict(app_id=str(i)))
                paths.append(p/'INTENT.json');states[str(i)]='stopped'
            with patch.object(b,'validate_I_settlement',return_value={'charged_usd':'0.99'}):
                raw,effective,slots,proof=b.effective_totals(root,paths,[],states,{},[])
                self.assertEqual(str(raw['I']),'14.43');self.assertEqual(str(effective['I']),'12.16');self.assertEqual(slots,0)
                states['1']='unknown';self.assertEqual(b.effective_totals(root,paths,[],states,{},[])[2],1)

    def test_new_records_keep_original_failed_boundaries_and_null_batches(self):
        s=dict(original_model_bindings={x:{'parent':{'terminal_key':x+'/terminal'}} for x in ('s1_n400_math',c.RUN)})
        allkeys=keys(s);self.assertEqual(len(allkeys),48);self.assertEqual(len(allkeys),len(set(allkeys)))
        self.assertIn(c.PARENT+'/terminal',allkeys);self.assertIn(c.PARENT+'/'+c.RUN+'/batch/00000',allkeys)

    def test_full_scoring_rejects_fake_completed_parent(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);dump(p/'COMPLETED.json',dict(passed=True,original_parent_status='completed'))
            sp=p/'spec.json';dump(sp,{})
            with self.assertRaises(ValueError):execute(types.SimpleNamespace(oracle=str(p),spec=str(sp)))

    def test_actual_entry_checks_owner_and_real_settlement_before_spawn(self):
        text=Path('experiments/p010/modal_cue_remaining.py').read_text();tree=ast.parse(text)
        source=ast.get_source_segment(text,next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='main'))
        for prior in ('owner_review(', 'effective_totals(', 'check_parent(', "store.put(KEY+'/dispatch'"):
            self.assertLess(source.index(prior),source.index('worker.spawn('))
        self.assertNotIn('store.delete',source)


if __name__=='__main__':unittest.main(verbosity=2)
