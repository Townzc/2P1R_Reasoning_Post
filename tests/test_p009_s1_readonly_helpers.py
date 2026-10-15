"""New read-only helper tests only; synthetic files and mocked Modal reads.

No real model, tokenizer, raw oracle, symbolic scorer, original job or provider
is invoked. No future runtime/code acceptance is written to an actual root.
"""
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from experiments.sft_allocation_midpoint.common import dump, read, digest, sha, manifest
from scripts import p009_s1_observe as observation
from scripts import publish_p009_s1_results as publication


class S1ReadOnlyTests(unittest.TestCase):
    def test_boolean_table_rejects_unknown_and_missing(self):
        ids=[str(i) for i in range(500)]
        value=dict(passed=True,run_id='r',total=500,technical_unknown=0,
            updates_verified=1024,targets_verified=2097148,question_correct={i:False for i in ids},correct=0)
        self.assertEqual(publication.complete_boolean_table(value,ids,'r'),value['question_correct'])
        value['question_correct'][ids[0]]=None
        with self.assertRaisesRegex(ValueError,'Boolean'):publication.complete_boolean_table(value,ids,'r')
        value['question_correct'].pop(ids[0])
        with self.assertRaisesRegex(ValueError,'Boolean'):publication.complete_boolean_table(value,ids,'r')

    def test_projection_removes_only_declared_nested_locators(self):
        source=dict(a=[dict(local_report_path='/Users/private/report',keep=9)],
                    raw_comment_local_path='/Users/private/comment',label='real')
        output,removed=publication.projection(source)
        self.assertEqual(output,{'a':[{'keep':9}],'label':'real'})
        self.assertEqual(removed,{'a.0.local_report_path':digest('/Users/private/report'),
            'raw_comment_local_path':digest('/Users/private/comment')})
        self.assertIn('local_report_path',source['a'][0])

    def test_file_roster_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'source').write_text('original');(root/'link').symlink_to(root/'source')
            with self.assertRaisesRegex(ValueError,'Symlink'):publication.file_roster(root)

    def test_partial_publication_refuses_before_reads(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(publication,'source_review') as check:
            with self.assertRaisesRegex(ValueError,'Prior or partial'):
                publication.publish_run(Path(folder),Path(folder),'s1_s17_n400','unused')
            check.assert_not_called()

    def test_failed_score_refuses_before_lineage_or_analysis(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);run='s1_s17_n400'
            (root/'oracles'/run).mkdir(parents=True);dump(root/'scores'/run/'FAILED.json',{'original':True})
            with patch.object(publication,'validate') as validate:
                with self.assertRaisesRegex(ValueError,'Partial or failed'):publication.check_complete(root,run,{})
                validate.assert_not_called()

    def test_named_status_counts_only500_and_retains_read_errors(self):
        run='s1_s17_n400'
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);dump(root/'runs'/run/'dispatch_intent.json',{'provider_app_id':'ap-test'})
            dump(root/'runs'/run/'submitted.json',{'call_id':'fc-test'})
            volume=types.SimpleNamespace(iterdir=lambda *a,**k:[types.SimpleNamespace(path=x)
                for x in ['endpoint_00000.json','endpoint_00256.json']])
            modal=types.SimpleNamespace(Dict=types.SimpleNamespace(from_name=lambda *a,**k:{}),
                Volume=types.SimpleNamespace(from_name=lambda *a,**k:volume))
            def cli(args,**kw):
                return json.dumps([] if 'container' in args else {'lifecycle':{'state':'running'}})
            with patch.dict(sys.modules,{'modal':modal}),patch.object(observation,'ROOT',root),\
                patch.object(observation.subprocess,'check_output',side_effect=cli),patch('sys.stdout',new=io.StringIO()):
                observation.observe([run])
                value=read(next((root/'status').glob('*/STATUS.json')))
                self.assertEqual(value['runs'][run]['continuous_saved_endpoint_count_from_names'],500)
                self.assertFalse(value['partial_scores_computed'])
                volume.iterdir=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('rate limit'))
                observation.observe([run])
                latest=read(sorted((root/'status').glob('*/STATUS.json'))[-1])
                self.assertEqual(latest['runs'][run]['progress'],'unknown')
                self.assertIn('rate limit',latest['runs'][run]['read_error'])

    def test_startup_without_ack_does_not_create_verified_path(self):
        run='s1_s29_n400'
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);specpath=root/'spec.json';dump(specpath,{'source_files':{}})
            dump(root/'runs'/run/'dispatch_intent.json',{'plan':{},'release':{}})
            dump(root/'runs'/run/'submitted.json',{'call_id':'fc-test'})
            modal=types.SimpleNamespace(Dict=types.SimpleNamespace(from_name=lambda *a,**k:{}),
                Volume=types.SimpleNamespace(from_name=lambda *a,**k:object()))
            with patch.dict(sys.modules,{'modal':modal}),patch.object(observation,'ROOT',root),\
                patch.object(observation,'SPEC',specpath),patch.object(observation,'validate',return_value={'seed':29,'n':400}):
                with self.assertRaisesRegex(ValueError,'has not acknowledged'):observation.verify(run)
                self.assertFalse((root/'startup'/run).exists())

    def test_real_publication_archives_original_files_without_science(self):
        run='s1_s17_n400'
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'private';out=Path(folder)/'published';ev=root/'ev';scored=root/'scored';generated=root/'generated';close=root/'close'
            for d in (ev,scored,generated,close):d.mkdir(parents=True)
            dump(ev/'raw.json',{'original':[1,2,3]});dump(ev/'intent.json',{'private':'kept'})
            (ev/'state.pt').write_bytes(b'not a model; never deserialized')
            dump(generated/'COMPLETED.json',{'passed':True});dump(generated/'SCORING_ROWS.json',[{'id':'original'}])
            oracle=dict(correct=123,logical_stops={'length_cap':7},unique_symbolic_pairs=15,
                outer_timeout_over_half_percent=True,fallback_over_two_percent=False,state_sha256=sha(ev/'state.pt'))
            dump(scored/'LOCAL_ORACLE_AUDIT.json',oracle);dump(scored/'job/payload/AUDIT_SAMPLES.json',{'adjudication':None})
            (scored/'job/worker.log').write_text('/Users/private/log remains private')
            dump(close/'ledger.json',{'original_failed_parent':'failed'})
            item=dict(ev=ev,scored=scored,generated=generated,close=close,
                envelope={'artifact_manifest':manifest(ev)},projected_intent={'public':'retained'},removed={'x':'original-sha'},
                provider={'state':'stopped'},raw_proof={},oracle=oracle,
                sent={'release':{'execution_commit':'e'*40,'runtime_review':{'report_sha256':'r'*64},'NC_A4_review':{'report_sha256':'n'*64}}},
                original_app_id='ap-test')
            with patch.object(publication,'SPEC',generated/'COMPLETED.json'),\
                patch.object(publication,'source_review',return_value={'source_files':{}}),\
                patch.object(publication,'check_complete',return_value=item),\
                patch.object(publication,'read',wraps=publication.read) as actual_read:
                # Keep the actual archive/write path; only the already-tested outer
                # scientific lineage gate is mocked for this tiny byte fixture.
                dump(generated/'SPEC.json',{'source_files':{}})
                with patch.object(publication,'SPEC',generated/'SPEC.json'):
                    result=publication.publish_run(root,out,run,'mock-in-memory-review')
            self.assertEqual(result['correct'],123)
            self.assertEqual(read(out/'AUDIT_SAMPLES.json'),{'adjudication':None})
            self.assertTrue(read(out/'SUMMARY.json')['outer_timeout_over_half_percent'])
            self.assertEqual(read(out/'PROJECTION.json')['omitted_generation']['state.pt']['sha256'],sha(ev/'state.pt'))
            self.assertEqual(read(out/'LOCAL_ORACLE_AUDIT.json'),oracle)
            self.assertNotIn('/Users/',(out/'INTENT_PROJECTION.json').read_text())
            with self.assertRaisesRegex(ValueError,'Prior or partial'):
                publication.publish_run(root,out,run,'unused')

    def first_pair_fixture(self, folder, same_app=False):
        root=Path(folder)/'private';out=Path(folder)/'pair';packets=Path(folder)/'endpoints'
        root.mkdir();specpath=root/'spec.json';dump(specpath,{'source_files':{},'G0_report_sha256':'g'*64})
        report=root/'synthetic_report.txt';report.write_text('SYNTHETIC TEST ONLY')
        analysis=root/'synthetic_analysis.json';dump(analysis,dict(
            scope='p009-stage1-registered-analysis-and-stop-code',decision='PASS',
            target_commit='2c7d6b5ce7fe7d9c23ad59dc6e185493390f9a81',
            local_report_path=str(report),report_sha256=sha(report),source_files={}))
        ids=[f'math/{i}' for i in range(500)];items={}
        for at,run in enumerate(publication.FIRST_PAIR):
            oracle={'question_correct':{k:i<100+8*at for i,k in enumerate(ids)}}
            dump(packets/run/'LOCAL_ORACLE_AUDIT.json',oracle)
            dump(packets/run/'MANIFEST.json',manifest(packets/run))
            items[run]=dict(oracle=oracle,ids=ids,original_app_id='ap-test'+str(0 if same_app else at),
                envelope={'receipt':{'status':'completed','run_id':run}},
                sent={'release':{'NC_A4_review':{'report_sha256':'n'*64}}})
        ncids=[f'nc/{i}' for i in range(1319)];nc={k:False for k in ncids}
        return root,out,packets,specpath,analysis,items,(ncids,nc,nc)

    def test_first_pair_original_futility_rule_is_once_and_never_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            root,out,packets,specpath,analysis,items,nc=self.first_pair_fixture(folder)
            with patch.object(publication,'SPEC',specpath),patch.object(publication,'PUBLIC_RUNS',packets),\
                patch.object(publication,'source_review',return_value={}),\
                patch.object(publication,'check_complete',side_effect=lambda root,run,spec:items[run]),\
                patch.object(publication,'nc_metadata',return_value=nc):
                result=publication.publish_first_pair(root,out,'synthetic',analysis)
            self.assertEqual(result['decision'],'stop_registered_futility')
            self.assertTrue(result['actual_A4_pending'])
            self.assertFalse(read(out/'REVIEW_BINDING.json')['remaining_S1_runtime_admitted'])
            self.assertFalse((root/'FIRST_PAIR_FUTILITY_A4_ACCEPTED.json').exists())

    def test_first_pair_duplicate_app_blocks_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root,out,packets,specpath,analysis,items,nc=self.first_pair_fixture(folder,same_app=True)
            with patch.object(publication,'SPEC',specpath),patch.object(publication,'PUBLIC_RUNS',packets),\
                patch.object(publication,'source_review',return_value={}),\
                patch.object(publication,'check_complete',side_effect=lambda root,run,spec:items[run]):
                with self.assertRaisesRegex(ValueError,'distinct original'):
                    publication.publish_first_pair(root,out,'synthetic',analysis)
            self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
