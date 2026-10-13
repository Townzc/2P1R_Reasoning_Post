"""Offline negative admission tests; synthetic review exists only in memory."""
import ast
import copy
import json
import unittest
from pathlib import Path

from experiments.sft_allocation_midpoint.common import digest, read, sha
from experiments.sft_allocation_p008.student_replacement_binding import (
    LOGICAL, MAPPING, PARENT_CAMPAIGN, make_plan, physical_config,
    validate_binding, require_parent_records)
from experiments.sft_allocation_p008.completion_queue import TRANSFER_KEY
from experiments.sft_allocation_p008.student_concurrency import require_capacity

PACKET=Path('reports/p008_20261013/student_lr_replacement_admission_v1')
ENTRY=Path('experiments/sft_allocation_p008/modal_student_replacements.py')


def fixture():
    spec=read(PACKET/'ADMISSION.json');plan=read(PACKET/'PLAN.json')
    cfg=copy.deepcopy(spec['configs'][next(iter(MAPPING))])
    sources=read(PACKET/'SOURCE_BUNDLE.json')
    # Never persisted as a gate or runtime acceptance; tests cannot dispatch.
    review=dict(verdict='PASS',scope='student-lr-replacement-runtime',
                review_commit='0'*40,review_report_sha256='0'*64,
                source_files=sources,spec_sha256=digest(spec))
    release=dict(source_files=sources,spec_sha256=digest(spec),gates=dict(
        owner=spec['owner'],input_readback=spec['input_readback'],
        zero_update_reconciliation_sha256=spec['zero_update_reconciliation_sha256'],
        runtime_review=review))
    return [plan,cfg,release,spec]


def rehash(a):
    a[2]['spec_sha256']=a[2]['gates']['runtime_review']['spec_sha256']=digest(a[3])


def parent_store(spec):
    result={}
    for n,p in spec['parents'].items():
        for kind,field in [('claim','claim'),('intent','binding'),('terminal','terminal')]:
            result['midpoint/'+PARENT_CAMPAIGN+'/'+kind+'/'+n]=copy.deepcopy(p[field])
        gate=spec['original_releases'][n]['gates']
        result[TRANSFER_KEY]=gate['student_slot_transfer']
        for x in gate['required_terminals']:
            result['midpoint/'+x['campaign']+'/terminal/'+x['run_id']]=x['terminal']
    return result


class ReplacementTests(unittest.TestCase):
    def test_both_real_logical_configs_and_frozen_inputs_retained(self):
        for physical,logical in MAPPING.items():
            a=fixture();a[1]=a[3]['configs'][physical]
            self.assertEqual(validate_binding(*a),a[3]['original_spec']['configs'][logical])

    def test_new_plan_two_independent_818_slots_only(self):
        a=fixture();self.assertEqual(a[0]['total_cap_cents'],1636)
        self.assertEqual(set(a[0]['slots']),set(MAPPING))
        self.assertNotEqual(a[0]['campaign_id'],PARENT_CAMPAIGN)
        self.assertEqual(sum(x['reserved_cents'] for x in a[0]['slots'].values()),1636)

    def test_cannot_relabel_original_failed_slot(self):
        a=fixture();a[1]['run_id']=LOGICAL[0]
        with self.assertRaises((ValueError,KeyError)):validate_binding(*a)

    def test_rehashed_scientific_change_rejected(self):
        for key in ('updates','targets','seed','max_seconds'):
            a=fixture();a[1][key]+=1;a[3]['configs'][a[1]['run_id']]=copy.deepcopy(a[1]);rehash(a)
            with self.assertRaises(ValueError):validate_binding(*a)

    def test_only_direct_exact_authority(self):
        for k,v in [('authority','Claude relay'),('stage_cap_cents',26605),
                    ('max_worker_seconds',6002),('automatic_retry',True),('replacement_call_count',3)]:
            a=fixture();a[3]['owner'][k]=v;rehash(a)
            with self.assertRaises(ValueError):validate_binding(*a)

    def test_extra_slot_rejected_even_if_rehashed(self):
        a=fixture();a[0]['slots']['extra']={'stage':'replacement','reserved_cents':1}
        a[3]['plan_sha256']=digest(a[0]);rehash(a)
        with self.assertRaises(ValueError):validate_binding(*a)

    def test_completed_or_unknown_parent_rejected(self):
        for change in ('terminal','unknown','attempted'):
            a=fixture();n=LOGICAL[0]
            if change=='terminal':a[3]['parents'][n]['terminal']['status']='completed'
            elif change=='unknown':a[3]['zero_update_reconciliation']['runs'][n]['unresolved_scientific_units']=1
            else:a[3]['zero_update_reconciliation']['runs'][n]['training_updates_attempted']=1
            rehash(a)
            with self.assertRaises(ValueError):validate_binding(*a)

    def test_parent_config_intent_canonical_digest_required(self):
        a=fixture();n=LOGICAL[0]
        a[3]['parents'][n]['binding']['config_sha256']=a[3]['canonical_config_digests'][n]['original_proposal_file_style_digest']
        rehash(a)
        with self.assertRaises(ValueError):validate_binding(*a)

    def test_parent_provider_identity_cannot_be_swapped(self):
        a=fixture();a[3]['parents'][LOGICAL[0]]['provider_app_id']='ap-foreign';rehash(a)
        with self.assertRaises(ValueError):validate_binding(*a)

    def test_review_scope_and_spec_must_match_new_entry(self):
        for k,v in [('scope','main-runtime'),('spec_sha256','f'*64),('source_files',{})]:
            a=fixture();a[2]['gates']['runtime_review'][k]=v
            with self.assertRaises(ValueError):validate_binding(*a)

    def test_missing_reused_readback_rejected(self):
        a=fixture();a[2]['gates']['input_readback']={}
        with self.assertRaises(ValueError):validate_binding(*a)

    def test_project_meter_plus_entire_stage_under450(self):
        a=fixture();b=a[3]['project_budget'];self.assertLessEqual(b['double_counted_meter_plus_full_stage_cents'],45000)
        b['workspace_summary']['metered_cost']='200';b['double_counted_meter_plus_full_stage_cents']=46604;rehash(a)
        with self.assertRaises(ValueError):validate_binding(*a)

    def test_original_dependencies_are_read_only_and_fresh(self):
        a=fixture();db=parent_store(a[3]);before=copy.deepcopy(db)
        self.assertTrue(require_parent_records(db,a[3]));self.assertEqual(db,before)
        del db['midpoint/'+PARENT_CAMPAIGN+'/terminal/'+LOGICAL[0]]
        with self.assertRaises(ValueError):require_parent_records(db,a[3])

    def test_new_pool_failure_cannot_be_hidden(self):
        a=fixture();db=parent_store(a[3]);key=next(k for k in db if '/terminal/pool_d2' in k)
        db[key]=dict(db[key],status='completed')
        with self.assertRaises(ValueError):require_parent_records(db,a[3])

    def test_shared_capacity_counts_original_and_replacement_queues(self):
        original=[dict(run_id=f'original/{i}',provider_app_id=f'ap-{i}') for i in range(7)]
        replacement=[dict(run_id='replacement/first',provider_app_id='ap-new')]
        with self.assertRaises(ValueError):require_capacity(original+replacement,[])
        with self.assertRaises(ValueError):require_capacity(original,[dict(app_id='unknown',container_id='ta-x')])
        self.assertEqual(require_capacity(original,[]),7)

    def test_cap_timer_precedes_model_imports(self):
        s=ENTRY.read_text();body=s[s.index('def work('):s.index('@app.function')]
        self.assertLess(body.index('timer.start()'),body.index('from experiments.'))
        self.assertIn('start+6001',body);self.assertIn('timeout=6061',s)
        self.assertIn('retries=0,max_containers=8,min_containers=0',s)

    def test_no_worker_upload_input_or_parent_writes(self):
        s=ENTRY.read_text();self.assertNotIn('batch_upload',s);self.assertNotIn('claims.put',s)
        self.assertIn("inputs=Path('/evidence')/PARENT_CAMPAIGN",s)
        self.assertIn('with dispatch_lock(shared):',s)
        self.assertIn('claims.keys()',s)

    def test_scientific_runtime_bytes_unchanged(self):
        old=read('reports/p008_20261013/student_frozen_lr_amendment_v1/SOURCE_BUNDLE.json')
        for name,h in old.items():self.assertEqual(sha(name),h,name)
        s=ENTRY.read_text();self.assertIn('from experiments.sft_allocation_p008.frozen_lr_block_student_runtime import run as execute',s)

    def test_all_new_source_files_bound(self):
        names=next(ast.literal_eval(n.value) for n in ast.parse(ENTRY.read_text()).body
            if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCES' for t in n.targets))
        self.assertEqual(len(names),34);self.assertEqual(set(names),set(read(PACKET/'SOURCE_BUNDLE.json')))
        for name,h in read(PACKET/'SOURCE_BUNDLE.json').items():self.assertEqual(sha(name),h)

    def test_oracle_keeps_physical_and_logical_lineage(self):
        s=Path('scripts/audit_p008_student_replacement.py').read_text()
        self.assertIn('require_parent_records(db,spec)',s)
        self.assertIn("recipe['identity']['physical_run_id']==run",s)
        self.assertIn('audit_predictions(sf,part,tok,EVAL)',s)
        self.assertIn('state=ck.load(state_path,recipe[',s)
        self.assertIn("outcome_blind_zero_update_replacement=True",s)


if __name__=='__main__':unittest.main()
