"""No cloud activity: numerical acceptance fixtures exist only in memory."""
import ast
import copy
import json
import tempfile
import unittest
from pathlib import Path
from tests.test_p008_completion_queue import fixture as base_fixture
from experiments.sft_allocation_midpoint.common import digest, read
from experiments.sft_allocation_p008.student_t8_binding import (
    ORIGINAL, REPLACEMENTS, FAILED, expected_mapping, validate_student_binding,
    require_timing_terminals, pending_across_queues)
from experiments.sft_allocation_p008.student_concurrency import require_capacity


def fixture():
    plan, _, release, spec = base_fixture()
    actual = read('reports/p008_20261013/student_admission_v1/ADMISSION.json')
    spec['configs'] = copy.deepcopy(actual['configs'])
    spec['config_sha256'] = {n: digest(c) for n, c in spec['configs'].items()}
    large = sorted(n for n, c in spec['configs'].items() if c.get('training_multiple') == 8)
    cfg = copy.deepcopy(spec['configs'][large[0]])
    gates = release['gates']
    gates['upload']['input_sha256'] = cfg['input_sha256']
    gates['draw_review']['input_sha256'] = cfg['input_sha256']
    release['spec_sha256'] = gates['runtime_review']['spec_sha256'] = digest(spec)
    mapping = expected_mapping(spec)
    provenance = {n: dict(physical_run_id=x['run_id'],
                         terminal=dict(run_id=x['run_id'],status='completed'),
                         oracle_sha256='1'*64,intent_sha256='2'*64,provider_sha256='3'*64)
                  for n,x in mapping.items()}
    records = [dict(campaign=x['campaign'],run_id=x['run_id'],terminal=provenance[n]['terminal'])
               for n,x in mapping.items()]
    failed = {}
    for n in FAILED:
        term = dict(run_id=n,status='failed')
        records.append(dict(campaign=ORIGINAL,run_id=n,terminal=term))
        failed[n] = dict(status='failed',terminal=term,training_updates_attempted=0,
                         training_updates_completed=0,supervised_targets=0,
                         endpoint_outputs=0,unresolved_scientific_units=0)
    proposal = dict(N2_closed=False,runtime_admission=False,engineering_criterion_passed=True,
                    failed_host_dropped=False,new_model_calls=0,spec_sha256=digest(spec),
                    common_plan_gate_sha256=spec['common_plan_gate_sha256'],
                    logical_to_physical=mapping,provenance=provenance,
                    failed_attempts_retained=failed,components={n:{} for n in mapping if n!='base'},
                    predictions={n:dict(with_margin_seconds=9000,allowed_seconds=9530,
                                         engineering_criterion_passed=True) for n in large},
                    policy=dict(schema='p008_t1_first_timing_gate_v2'))
    gates.update(t8_timing_proposal=proposal,t1_terminal_records=records,
                 t8_numeric_review=dict(verdict='PASS',scope='t8-numeric',review_commit='0'*40,
                    review_report_sha256='0'*64,source_files=release['source_files'],
                    spec_sha256=digest(spec),passed=True,N2_closed=True,accepted_runs=large,
                    worker_caps={n:9560 for n in large},proposal_digest=digest(proposal),
                    common_plan_gate_sha256=spec['common_plan_gate_sha256']))
    return [plan,cfg,release,spec]


def rebind_proposal(a):
    g=a[2]['gates'];g['t8_numeric_review']['proposal_digest']=digest(g['t8_timing_proposal'])


class T8Tests(unittest.TestCase):
    def test_exact_full_roster_and_review(self):
        self.assertTrue(validate_student_binding(*fixture()))

    def test_source_pass_alone_never_admits(self):
        for key in ('N2_closed','passed'):
            a=fixture();a[2]['gates']['t8_numeric_review'][key]=False
            with self.assertRaises(ValueError):validate_student_binding(*a)

    def test_different_numerical_scope_source_spec_proposal_rejected(self):
        for key,value in [('scope','main-runtime'),('source_files',{}),('spec_sha256','9'*64),('proposal_digest','9'*64)]:
            a=fixture();a[2]['gates']['t8_numeric_review'][key]=value
            with self.assertRaises(ValueError):validate_student_binding(*a)

    def test_cannot_remove_slow_failed_or_completed_host_even_if_rehashed(self):
        for key in ('components','provenance','failed_attempts_retained'):
            a=fixture();d=a[2]['gates']['t8_timing_proposal'][key];d.pop(next(iter(d)));rebind_proposal(a)
            with self.assertRaises(ValueError):validate_student_binding(*a)

    def test_margin_failure_nan_and_wrong_cap_rejected(self):
        for key,value in [('with_margin_seconds',9531),('with_margin_seconds',float('nan')),
                          ('allowed_seconds',9560),('engineering_criterion_passed',False)]:
            a=fixture();p=a[2]['gates']['t8_timing_proposal'];p['predictions'][a[1]['run_id']][key]=value
            # Non-finite numbers are already rejected by canonical JSON hashing.
            with self.assertRaises(ValueError):
                rebind_proposal(a)
                validate_student_binding(*a)

    def test_old_failure_not_relabelled_or_given_science(self):
        for key,value in [('status','completed'),('unresolved_scientific_units',1),('training_updates_attempted',1)]:
            a=fixture();a[2]['gates']['t8_timing_proposal']['failed_attempts_retained'][FAILED[0]][key]=value;rebind_proposal(a)
            with self.assertRaises(ValueError):validate_student_binding(*a)

    def test_duplicate_missing_or_changed_terminal_rejected(self):
        for mode in ('duplicate','missing','changed'):
            a=fixture();rows=a[2]['gates']['t1_terminal_records']
            if mode=='duplicate':rows.append(rows[0])
            elif mode=='missing':rows.pop()
            else:rows[-1]['terminal']={**rows[-1]['terminal'],'status':'completed'}
            with self.assertRaises(ValueError):validate_student_binding(*a)

    def test_real_worker_rechecks_all_dependencies_without_writes(self):
        a=fixture();g=a[2]['gates'];db={'midpoint/'+x['campaign']+'/terminal/'+x['run_id']:x['terminal'] for x in g['t1_terminal_records']}
        before=copy.deepcopy(db);self.assertTrue(require_timing_terminals(db,g));self.assertEqual(db,before)
        db.pop(next(iter(db)))
        with self.assertRaises(ValueError):require_timing_terminals(db,g)

    def test_both_queue_pending_and_unmatched_containers_consume_capacity(self):
        with tempfile.TemporaryDirectory() as tmp:
            queues=[]
            for k,camp in enumerate((ORIGINAL,REPLACEMENTS)):
                root=Path(tmp)/str(k);root.mkdir();plan=dict(campaign_id=camp)
                (root/'plan.json').write_text(json.dumps(plan));d=root/'runs'/'r';d.mkdir(parents=True)
                (d/'dispatch_intent.json').write_text(json.dumps(dict(run_id='r',plan=plan,provider_app_id='ap-'+str(k))))
                queues.append((root,camp))
            pending=pending_across_queues(queues,{})
            self.assertEqual(len(pending),2)
            containers=[dict(container_id='ta-'+str(i),app_id='unmatched-'+str(i)) for i in range(6)]
            with self.assertRaises(ValueError):require_capacity(pending,containers)
            self.assertEqual(require_capacity(pending,containers[:5]),7)

    def test_new_entry_caps_and_lock_precede_spawn(self):
        src=Path('experiments/sft_allocation_p008/modal_students_t8.py').read_text();tree=ast.parse(src)
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='student_work')
        args={k.arg:ast.literal_eval(k.value) for k in fn.decorator_list[0].keywords if k.arg in ('timeout','startup_timeout','retries','max_containers')}
        self.assertEqual(args,dict(timeout=9620,startup_timeout=600,retries=0,max_containers=8))
        work=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='work')
        segment=ast.get_source_segment(src,work)
        self.assertLess(segment.index('start=time.time()'),segment.index('sys.path.insert'))
        self.assertIn('start+9560',segment)
        self.assertIn('with dispatch_lock(root):',src)
        self.assertLess(src.index('pending_across_queues(('),src.index('call=fn.spawn'))
        self.assertLess(src.index('read_stopped_apps(cli,dependency_apps'),src.index('call=fn.spawn'))

    def test_scientific_execute_function_remains_identical(self):
        # Wrapper calls the original frozen scientific function; no second model implementation.
        src=Path('experiments/sft_allocation_p008/modal_students_t8.py').read_text()
        self.assertIn('from experiments.sft_allocation_p008.frozen_lr_block_student_runtime import run as execute',src)
        self.assertIn('result=execute(assets,inputs,out,journal,identity)',src)


if __name__=='__main__':unittest.main()
