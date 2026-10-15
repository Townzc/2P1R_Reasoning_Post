"""New53 helper adaptation checks only; no original analysis/model/provider work."""
import ast,copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import publish_p009_nc_guard_repair_pair as p
from scripts import p009_nc_guard_repair_observe as observer


class GuardRepairHelpers(unittest.TestCase):
    def test_new_observer_bound_to_53_and_no_remote_mutation(self):
        self.assertEqual(observer.ROOT.name,'stage1_nc_guard_repair_r1')
        t=ast.parse(Path(observer.__file__).read_text())
        calls={n.func.attr for n in ast.walk(t) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
        self.assertFalse(calls & {'put','spawn','generate','batch_upload','delete','commit'})
        self.assertIn('source_file_count=53',Path(observer.__file__).read_text())
    def test_nested_proxy_locator_projection_preserves_original_comment(self):
        original=dict(release=dict(owner_proxy_decision=dict(raw_comment_local_path='/Users/example/private/comment.json',
            comment=dict(body='【Owner 代理决定】 reason',id=123),comment_sha256='a'*64),
            original_replacement_release=dict(runtime_review=dict(local_report_path='/Users/example/report',decision='PASS'))))
        old=copy.deepcopy(original);got,removed=p.projection(original)
        self.assertEqual(original,old);self.assertEqual(len(removed),2)
        self.assertEqual(got['release']['owner_proxy_decision']['comment'],original['release']['owner_proxy_decision']['comment'])
        self.assertNotIn('/Users/',str(got))
    def test_new_preclaim_and_provider_projection_before_output_creation(self):
        t=ast.parse(Path(p.__file__).read_text());f=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='publish')
        mkdir=next(i for i,n in enumerate(f.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='mkdir')
        assigned={target.id for n in f.body[:mkdir] if isinstance(n,ast.Assign) for target in n.targets if isinstance(target,ast.Name)}
        self.assertTrue({'provider_projected','preclaim','proxy'}<=assigned)
    def test_original_lineage_and_sibling_checker_bodies_unchanged(self):
        def funcs(path):
            t=ast.parse(Path(path).read_text())
            return {n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,ast.FunctionDef)}
        old=funcs('scripts/publish_p009_nc_replacement_pair.py');new=funcs(p.__file__)
        for name in ('check_oracle','original_sibling','check_lineage'):self.assertEqual(old[name],new[name])
    def test_exactly_one_registered_decision_call_no_new_analysis(self):
        t=ast.parse(Path(p.__file__).read_text())
        self.assertEqual(sum(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='nc_result' for n in ast.walk(t)),1)
        self.assertNotIn('bootstrap', {n.func.id for n in ast.walk(t) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)})
        self.assertIn('reserved_cents=2620',Path(p.__file__).read_text())
        self.assertIn('preclaim_only_has_no_scientific_terminal=True',Path(p.__file__).read_text())
    def test_prior_repair_dispatch_record_remains_an_immutable_dependency(self):
        old_failure_key='midpoint/'+p.PARENT_CAMPAIGN+'/terminal/'+p.PARENT_RUN
        required={old_failure_key:dict(status='failed',evidence_sha256=p.PARENT_FAILURE_DIGEST),
            'old_preclaim_dispatch':dict(provider_app_id='old_failed_app')}
        spec=dict(required_records=required,required_stopped_app_ids=['old_failed_app'])
        sent=dict(spec=spec,run_id=p.RUN,plan={},release=dict(dispatch_app_id='new_app'))
        files={'checkpoint_1024/state.pt':dict(sha256='a'*64,bytes=1)};claim=dict(attempt_id='once',reserved_cents=655)
        term=dict(status='completed',run_id=p.RUN,claim_sha256=p.digest(claim),attempt_id='once',evidence_sha256=p.digest(files),actual_cost_cents=655)
        db={**copy.deepcopy(required),'midpoint/'+p.CAMPAIGN+'/claim/'+p.RUN:claim,'midpoint/'+p.CAMPAIGN+'/terminal/'+p.RUN:term,
            p.dispatch_key(p.RUN):{},p.logical_key(p.RUN):{}}
        db['old_preclaim_dispatch']['provider_app_id']='substituted'
        with patch.object(p,'validate'),patch.object(p,'marker',return_value={}):
            with self.assertRaises(ValueError):p.check_lineage(spec,sent,dict(receipt=term,artifact_manifest=files),{}, {},{},db,'receipt','ledger')
    def test_partial_new_publication_is_never_repeated(self):
        base=Path('.local/p009_20261014/r1');base.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as tmp:
            out=Path(tmp)/'partial';out.mkdir();(out/'PUBLICATION_INTENT.json').write_text('{}')
            with self.assertRaises(ValueError):p.publish('unused',out,'unused','unused')
            self.assertEqual((out/'PUBLICATION_INTENT.json').read_text(),'{}')


if __name__=='__main__':unittest.main()
