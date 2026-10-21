"""New fake-ledger cases only; no original jobs, provider, model or old tests."""
import ast
import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from experiments.p011 import failed_attempt_ledger as ledger, c1_admission
from experiments.p011.long_preflight import failed_ledger_path as current
from experiments.sft_allocation_midpoint.common import dump, read, sha, digest


def fixture(root):
    logical='B_generation_t10_400x16_r1';base=root/ledger.c1_outer.LOCAL/'dispatch'/logical
    base.mkdir(parents=True)
    intent={'logical_id':logical,'app_id':'ap-b','execution':'a'*40,
            'budget':{'category':'B','new_reserved_usd':'3.01'}}
    submitted={'logical_id':logical,'app_id':'ap-b','call_id':'fc-b'}
    failure={'logical_id':logical,'app_id':'ap-b','status':'failed','finished_epoch':10.,'automatic_retry_allowed':False}
    provider={'app_id':'ap-b','state':'stopped','owned_containers':0,'observed_epoch':11.}
    values={'intent':intent,'submitted':submitted,'failure':failure,'provider':provider,
        'preservation':{'stable_inventory':True,'scientific_completion':False},
        'named_dispatch':{'key':'b/generation/dispatch','value':intent},
        'named_terminal':{'key':'b/generation/terminal','value':failure},
        'named_claim':{'key':'b/generation/claim','value':{'logical_id':logical,'app_id':'ap-b',
            'execution':'a'*40,'dispatch_sha256':digest(intent)}}}
    files={}
    for name,value in values.items():
        path=Path('saved')/(name+'.json');dump(root/path,value);files[name]={'path':str(path),'sha256':sha(root/path)}
    dump(base/'INTENT.json',intent);dump(base/'SUBMITTED.json',submitted);dump(base/'PROVIDER_STOPPED0.json',provider)
    return {'failed_attempt_bindings':{logical:{'key':'b/generation','category':'B','reserved_usd':'3.01','files':files}}},base


class NewFailedLedgerTests(unittest.TestCase):
    def test_failed_is_retained_without_writing_success_or_repolling(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);spec,base=fixture(root)
            before={str(p):p.read_bytes() for p in root.rglob('*.json')}
            rows=ledger.ledger(root,spec)
            totals,slots=c1_admission.accounting(rows,[],{'ap-b':'stopped'})
            self.assertEqual((totals['B'],slots),('3.01',0))
            self.assertEqual(rows[0]['preserved_failed_terminal']['status'],'failed')
            self.assertEqual(before,{str(p):p.read_bytes() for p in root.rglob('*.json')})
            self.assertFalse((base/'RESULT.json').exists())

    def test_pending_unknown_and_unmatched_slots_still_count(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);spec,base=fixture(root)
            for name,submitted in [('pending',False),('unknown',True)]:
                p=base.parent/name;dump(p/'INTENT.json',{'logical_id':name,'app_id':'ap-'+name,'budget':{'category':'A','new_reserved_usd':'1.91'}})
                if submitted:dump(p/'SUBMITTED.json',{'logical_id':name,'app_id':'ap-'+name,'call_id':'fc-'+name})
            rows=ledger.ledger(root,spec);totals,slots=c1_admission.accounting(rows,[{'app_id':'ap-unmatched'}],{'ap-b':'stopped'})
            self.assertEqual(slots,3);self.assertEqual(totals['A'],'3.82');self.assertEqual(totals['B'],'3.01')

    def test_changed_bound_failure_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);spec,base=fixture(root);(root/'saved/failure.json').write_text(json.dumps({'status':'completed'}))
            with self.assertRaises(ValueError):ledger.ledger(root,spec)

    def test_false_result_or_missing_provider_cannot_release_failure(self):
        for change in ('result','missing'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as d:
                root=Path(d);spec,base=fixture(root)
                if change=='result':dump(base/'RESULT.json',{'status':'completed'})
                else:(base/'PROVIDER_STOPPED0.json').unlink()
                with self.assertRaises(ValueError):ledger.ledger(root,spec)

    def test_old_unknown_or_mismatched_provider_is_rejected(self):
        for key,value in [('observed_epoch',9.),('observed_epoch',float('nan')),('app_id','ap-other'),('owned_containers',1)]:
            with self.subTest(key=key,value=value),tempfile.TemporaryDirectory() as d:
                root=Path(d);spec,base=fixture(root);p=read(base/'PROVIDER_STOPPED0.json');p[key]=value;(base/'PROVIDER_STOPPED0.json').write_text(json.dumps(p))
                with self.assertRaises(ValueError):ledger.ledger(root,spec)

    def test_binding_missing_from_real_ledger_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);spec,base=fixture(root);spec['failed_attempt_bindings']['absent']=deepcopy(next(iter(spec['failed_attempt_bindings'].values())))
            with self.assertRaises(ValueError):ledger.ledger(root,spec)

    def test_remote_reads_only_three_exact_saved_fences(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);spec,base=fixture(root);values={}
            for name in ('dispatch','claim','terminal'):
                v=read(root/'saved'/('named_'+name+'.json'));values[v['key']]=v['value']
            class Store:
                def __init__(self):self.read=[]
                def get(self,key):self.read.append(key);return values.get(key)
            store=Store();ledger.remote_fences(root,spec,store)
            self.assertEqual(store.read,['b/generation/dispatch','b/generation/claim','b/generation/terminal'])
            values['b/generation/terminal']=None
            with self.assertRaises(ValueError):ledger.remote_fences(root,spec,Store())

    def test_completed_results_keep_original_success_identity_rules(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);spec,base=fixture(root);p=base.parent/'complete'
            dump(p/'INTENT.json',{'logical_id':'complete','budget':{'category':'C','new_reserved_usd':'2.64'}})
            dump(p/'SUBMITTED.json',{'logical_id':'complete','app_id':'ap-complete','call_id':'fc-complete'})
            dump(p/'PROVIDER_STOPPED0.json',{'app_id':'ap-complete','state':'stopped','owned_containers':0,'observed_epoch':20.})
            dump(p/'RESULT.json',{'app_id':'ap-complete','status':'completed','finished_epoch':19.})
            self.assertEqual(len(ledger.ledger(root,spec)),2)
            (p/'RESULT.json').write_text(json.dumps({'app_id':'ap-complete','status':'failed','finished_epoch':19.}))
            with self.assertRaises(ValueError):ledger.ledger(root,spec)

    def test_scientific_worker_budget_policy_and_wrapper_bodies_identical(self):
        def functions(file):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(Path(file).read_text()).body if isinstance(n,ast.FunctionDef)}
        old=functions('experiments/p011/long_preflight/path.py');new=functions('experiments/p011/long_preflight/failed_ledger_path.py')
        for name in set(old)-{'validate','reviewed','submit','published'}:self.assertEqual(old[name],new[name],name)
        for left,right in [('experiments/p011/long_preflight/modal_entry.py','experiments/p011/long_preflight/modal_failed_ledger_entry.py'),('scripts/p011_long_preflight_io.py','scripts/p011_long_preflight_failed_ledger_io.py')]:
            tree=ast.parse(Path(right).read_text())
            for n in ast.walk(tree):
                if isinstance(n,ast.alias) and n.name=='failed_ledger_path':n.name='path';n.asname=None if n.asname=='path' else n.asname
            self.assertEqual(ast.dump(ast.parse(Path(left).read_text()),include_attributes=False),ast.dump(tree,include_attributes=False))


if __name__=='__main__':unittest.main()
