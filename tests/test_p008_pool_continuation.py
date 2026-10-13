"""Synthetic CPU fixtures only: no tokenizer downloads, model or cloud calls."""
import ast
import copy
import inspect
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from test_p008_pool_prefix import fixture, wallets
from experiments.sft_allocation_p008 import pool_runtime as original
from experiments.sft_allocation_p008 import pool_continuation_runtime as child
from experiments.sft_allocation_p008.pool_continuation_prefix import load_prefix
from experiments.sft_allocation_midpoint.common import dump, read, sha, manifest, digest
from experiments.sft_allocation_acquisition.contract import REVISION


def make_prefix(root):
    c,e,s,r=fixture();ws=wallets();ids=list(ws[0].lengths);lengths=ws[0].lengths
    cfg=dict(draw=2,high_multiple=8,max_physical_attempts=16384,input_sha256='a'*64,
             max_seconds=7200,run_id='pool_d2_remaining',role='pool_continuation')
    old=dict(cfg,run_id='pool_d2',role='pool',max_seconds=10800)
    plan=dict(campaign_id='p008-main-20261013-r1')
    release=dict(commit='b'*40,source_files={'source.py':'c'*64})
    bound=dict(run_id='pool_d2',source_sha256=digest(release['source_files']),
               config_sha256=digest(old),data_sha256=old['input_sha256'])
    claim=dict(attempt_id='old',plan_sha256=digest(plan),intent_sha256=digest(bound))
    r.update(parent_claim=claim,parent_source_commit=release['commit'],parent_manifest_digest='d'*64)
    r['parent_terminal'].update(run_id='pool_d2',attempt_id='old',claim_sha256=digest(claim),evidence_sha256='d'*64)
    dump(root/'parent_intent.json',dict(config=old,plan=plan,release=release))
    dump(root/'parent_frozen_wallets.json',dict(draw=2,max_physical_attempts=16384,teacher_revision=REVISION,
         parent_order=ids,prompt_lengths=lengths,wallets=[w.name for w in ws]))
    for name,value,field in [('candidate_cache_reconstructed.json',c,'reconstructed_cache_sha256'),
                            ('wallet_events_reconstructed.json',e,'reconstructed_events_sha256'),
                            ('wallet_states_reconstructed.json',s,'reconstructed_states_sha256')]:
        dump(root/name,value);r[field]=sha(root/name)
    dump(root/'RECONCILIATION.json',r);dump(root/'manifest.json',dict(files=manifest(root)))
    cfg['prefix_manifest_sha256']=sha(root/'manifest.json')
    return cfg,ids,lengths


def altered(root,cfg,name,mutate):
    obj=read(root/name);mutate(obj);(root/name).unlink();dump(root/name,obj)
    (root/'manifest.json').unlink();dump(root/'manifest.json',dict(files=manifest(root)))
    cfg['prefix_manifest_sha256']=sha(root/'manifest.json')


class PrefixBindingTests(unittest.TestCase):
    def test_valid_exact_prefix_is_not_an_admission(self):
        with tempfile.TemporaryDirectory() as d:
            cfg,ids,lens=make_prefix(Path(d));state,lineage=load_prefix(d,cfg,wallets(),ids,lens)
            self.assertEqual(state['attempted'],16)
            self.assertEqual(lineage['original_parent_status'],'failed')
            self.assertFalse(lineage['continuation_authorized_by_this_check'])
    def reject(self,name,mutate):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cfg,ids,lens=make_prefix(root);altered(root,cfg,name,mutate)
            with self.assertRaises(ValueError):load_prefix(d,cfg,wallets(),ids,lens)
    def test_rehashed_parent_config_change_rejected(self):
        self.reject('parent_intent.json',lambda x:x['config'].update(max_physical_attempts=17000))
    def test_rehashed_parent_status_change_rejected(self):
        self.reject('RECONCILIATION.json',lambda x:x['parent_terminal'].update(status='completed'))
    def test_rehashed_parent_attempt_change_rejected(self):
        self.reject('RECONCILIATION.json',lambda x:x['parent_terminal'].update(attempt_id='other'))
    def test_rehashed_prompt_order_rejected(self):
        self.reject('parent_frozen_wallets.json',lambda x:x['parent_order'].reverse())
    def test_rehashed_teacher_revision_rejected(self):
        self.reject('parent_frozen_wallets.json',lambda x:x.update(teacher_revision='0'*40))
    def test_rehashed_cache_without_reconciliation_rejected(self):
        self.reject('candidate_cache_reconstructed.json',lambda x:x.pop(next(iter(x))))
    def test_manifest_identity_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            cfg,ids,lens=make_prefix(Path(d));cfg['prefix_manifest_sha256']='0'*64
            with self.assertRaises(ValueError):load_prefix(d,cfg,wallets(),ids,lens)


class Journal:
    def __init__(self):self.units={};self.dones={};self.commits=0
    def check(self):pass
    def begin(self,name,record):
        if name.endswith('_batch_0000') or name=='physical_batch_00000' or name in self.units:
            raise AssertionError('Existing work replayed')
        self.units[name]=copy.deepcopy(record)
    def end(self,name,record):
        if name not in self.units or name in self.dones:raise AssertionError('Bad completion')
        self.dones[name]=copy.deepcopy(record)
    def commit(self):self.commits+=1


class Model:
    def __init__(self,journal):self.journal=journal;self.calls=[];self.bad_return=False
    def generate(self,prompts,params,use_tqdm):
        # Both physical and wallet reservations must already be committed.
        if not self.journal.commits or not self.journal.units:raise AssertionError('No committed intent')
        self.calls.append([x.seed for x in params]);out=[]
        for p in prompts:
            out.append(types.SimpleNamespace(prompt_token_ids=p['prompt_token_ids'],outputs=[
                types.SimpleNamespace(token_ids=[1000+len(self.calls)*32+len(out),151645],
                                      text='synthetic',finish_reason='stop',stop_reason=151645)]))
        return out[:-1] if self.bad_return else out


def loop_nodes(module):
    fn=next(x for x in ast.parse(inspect.getsource(module)).body if isinstance(x,ast.FunctionDef) and x.name=='run')
    start=next(i for i,x in enumerate(fn.body) if isinstance(x,ast.While))
    return fn.body[start:]


def simulate(out,state,ws,journal,model,cap=16384):
    body=ast.parse("attempted=initial['attempted']; batch_index=initial['batch_index']; returned_tokens=initial['returned_tokens']").body+loop_nodes(child)
    fn=ast.FunctionDef(name='execute_fixture',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),
                      body=body,decorator_list=[])
    tree=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]))
    ids=list(ws[0].lengths)
    env={**child.__dict__,**state,'initial':state,'wallets':ws,'draw':2,'config':dict(max_physical_attempts=cap),
         'out':out,'journal':journal,'model':model,'physical_token_bound':cap*1024,
         'prompts':dict.fromkeys(ids,[9]*10),'lengths':dict.fromkeys(ids,10),'lookup':dict.fromkeys(ids,{}),
         'SamplingParams':lambda **kw:types.SimpleNamespace(**kw),
         'tok':types.SimpleNamespace(decode=lambda ids,**kw:str(ids[0])),
         'assess':lambda p,text,stop,seen,accepted:dict(usable=True,normalized_text_sha256=text),
         'lineage':dict(parent_physical_attempts=state['attempted'],parent_returned_tokens=state['returned_tokens'],
                        parent_physical_batches=state['batch_index'])}
    exec(compile(tree,'synthetic_cpu_tail','exec'),env)
    with patch('builtins.print'):return env['execute_fixture']()


class LoopTests(unittest.TestCase):
    def test_scientific_loop_and_final_wallet_files_ast_unchanged(self):
        old=loop_nodes(original);new=loop_nodes(child)
        # Only the return is enriched with explicit cumulative/suffix provenance.
        self.assertEqual(ast.dump(ast.Module(body=old[:-1],type_ignores=[])),
                         ast.dump(ast.Module(body=new[:len(old)-1],type_ignores=[])))
    def prepare(self):
        from experiments.sft_allocation_p008.pool_prefix import restore
        ws=wallets();state=restore(ws,*fixture());journal=Journal();model=Model(journal)
        return ws,state,journal,model
    def test_suffix_only_preserves_parent_and_full_wallet_charges(self):
        ws,state,journal,model=self.prepare();before=copy.deepcopy(state['cache'])
        with tempfile.TemporaryDirectory() as d:
            result=simulate(Path(d),state,ws,journal,model)
            self.assertEqual(result['physical_outputs'],64)
            self.assertEqual(result['child_physical_outputs'],48)
            self.assertEqual(result['child_physical_batches'],3)
            self.assertEqual(len(model.calls),3)
            self.assertEqual({k:state['cache'][k] for k in before},before)
            self.assertTrue(all(x['attempt']>=2 for k,v in journal.units.items() if k.startswith('physical') for x in v['items']))
            self.assertEqual(result['original_parent_status'],'failed')
            for w in ws:self.assertIsNone(w.propose())
            # Parent+child events are retained even though only child units exist here.
            self.assertEqual(len(read(Path(d)/'d2_b8_p0_depth_events.json')),4)
            self.assertFalse((Path(d)/'physical_batch_00000_raw.json').exists())
    def test_parent_attempts_count_toward_cap(self):
        ws,state,journal,model=self.prepare()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError,'Physical cap'):simulate(Path(d),state,ws,journal,model,cap=16)
            self.assertEqual(model.calls,[])
            self.assertTrue((Path(d)/'supply_censored.json').exists())
    def test_missing_return_preserves_unfinished_intent_and_does_not_retry(self):
        ws,state,journal,model=self.prepare();model.bad_return=True
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'Missing physical return'):simulate(Path(d),state,ws,journal,model)
            self.assertEqual(len(model.calls),1)
            self.assertIn('physical_batch_00001',journal.units)
            self.assertNotIn('physical_batch_00001',journal.dones)
            self.assertTrue(any(w.pending is not None for w in ws))


if __name__=='__main__':unittest.main()
