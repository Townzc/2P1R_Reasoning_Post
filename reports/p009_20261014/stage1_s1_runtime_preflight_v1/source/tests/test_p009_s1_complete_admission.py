"""New full S1 boundary checks, with real RunGuard and fully mocked model bodies.

Future runtime/NC/futility reports below are SYNTHETIC IN MEMORY ONLY. No test
writes an acceptance, creates a cloud app, scores a real answer or loads state.
"""
import ast
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from experiments.sft_allocation_midpoint.common import read, digest
from experiments.sft_allocation_midpoint.guard import RunGuard, GuardError
from experiments.learning_regime_p009 import stage1_s1_funded_binding as b

PRIVATE = Path('.local/p009_20261014/r1')
PUBLIC = Path('reports/p009_20261014/stage1_s1_runtime_preflight_v1')


class Store(dict):
    def put(self, key, value, skip_if_exists=False):
        if skip_if_exists and key in self:
            return False
        self[key] = copy.deepcopy(value)
        return True


def fixture():
    if (PUBLIC/'ADMISSION.json').exists():
        spec, plan = read(PUBLIC/'ADMISSION.json'), read(PUBLIC/'PLAN.json')
        originals = read(PUBLIC/'REVIEW_FIXTURE_INPUTS.json')
    else:
        candidate = PRIVATE/'stage1_s1_runtime_candidate_r1'
        spec, plan = read(candidate/'ADMISSION_DRAFT.json'), read(candidate/'PLAN.json')
        originals = {key:read(PRIVATE/name) for key,name in {
            'G0_review':'P1_COMPLETE_A2_ACCEPTED.json',
            'input_review':'STAGE1_S1_INPUTS_ACCEPTED.json',
            'core_review':'STAGE1_SCIENTIFIC_CORE_CODE_ACCEPTED.json',
            'internal_only_review':'P0_INTERNAL_ONLY_AMENDMENT_ACCEPTED.json',
            'budget_owner_decision':'stage1_s1_r1/OWNER_BUDGET_PROXY_DECISION.json',
        }.items()}
    review = dict(scope=b.SCOPE, decision='PASS', target_commit='a'*40,
        report_commit='b'*40, report_sha256='c'*64, source_files=spec['source_files'],
        spec_sha256=digest(spec), timing_sha256=digest(spec['timing']),
        budget_proxy_comment_sha256=spec['budget_proxy_comment_sha256'],
        NC_packet_manifest_sha256=spec['NC_packet_manifest_sha256'],
        input_basis_file_sha256=b.INPUT_BASIS, input_archive_file_sha256=b.INPUT_ARCHIVE,
        all_21_training_hosts_included=True, all_MATH_base_endpoint_batches_included=True,
        uncalibrated_timing_proxy_scope_accepted=True, training_process_exit_before_vllm=True,
        local_scoring_worst_pair_scenario_accepted=True, registered_NC_and_futility_gates_retained=True,
        prior_stage1_reserved_cents=2620, new_reserved_cents=3930, first_paid_measurement_exceptions=0)
    nc = dict(scope=b.NC_SCOPE, decision='PASS', target_commit=spec['NC_packet_target_commit'],
        report_commit='d'*40, report_sha256='e'*64,
        manifest_file_sha256=spec['NC_packet_manifest_sha256'],
        registered_decision_file_sha256=spec['NC_decision_file_sha256'],
        paired_NC_gate_passed=True, stop_all_positive_regimes=False,
        complete_logical_cells=2, failed_parent_retained=True)
    release = dict(originals, source_files=spec['source_files'], input_readback=spec['inputs'],
        runtime_review=review, review_target='a'*40, NC_A4_review=nc,
        budget=dict(stage1_prior_reserved_cents=2620, new_reserved_cents=3930,
            stage1_cap_cents=7000, experiment_cap_cents=15000, project_prior_upper_cents=26610),
        dispatch_app_id='ap-synthetic-in-memory-only', execution_commit='f'*40)
    return spec, plan, release


def futility(release):
    release['futility_target_commit'] = '1'*40
    release['futility_review'] = dict(scope=b.FUTILITY_SCOPE, target_commit='1'*40,
        report_commit='2'*40, report_sha256='3'*64, decision='PASS',
        NC_A4_report_sha256=release['NC_A4_review']['report_sha256'], S1_G0_report_sha256=b.G0_SHA,
        futility_stopped=False, remaining_S1_allowed=True, first_pair_run_ids=list(b.FIRST_PAIR),
        first_pair_app_ids=['ap-synthetic-400','ap-synthetic-3200'],
        required_terminal_records={'midpoint/'+b.CAMPAIGN+'/terminal/'+k:{'status':'completed'}
                                   for k in b.FIRST_PAIR})


class CompleteAdmission(unittest.TestCase):
    def setUp(self):
        self.s, self.p, self.r = fixture()

    def test_original_first_pair_passes_only_full_synthetic_binding(self):
        for run in b.FIRST_PAIR:
            cap = b.validate(self.s,self.p,run,self.r)
            self.assertEqual((cap['updates'],cap['targets'],cap['reserved_cents']), (1024,2097148,655))
        self.assertEqual(sum(x['reserved_cents'] for x in self.s['slots'].values())+2620,6550)

    def test_real_guard_exact_four_fields_and_permanent_replay_rejection(self):
        db = Store(); guard = RunGuard(db,self.p); now = self.p['created_epoch']+1
        guard.register(now_epoch=now); run = b.FIRST_PAIR[0]
        value = b.intent(self.s,run)
        self.assertEqual(set(value), {'run_id','config_sha256','source_sha256','data_sha256'})
        claim = guard.admit(value,attempt_id='actual_guard_test',now_epoch=now,max_runtime_seconds=4500)
        self.assertEqual(claim.run_id,run)
        with self.assertRaises(GuardError):
            guard.admit(value,attempt_id='replay',now_epoch=now,max_runtime_seconds=4500)

    def test_actual_nc_result_cannot_be_replaced_by_code_review(self):
        self.r['NC_A4_review'] = self.r['core_review']
        with self.assertRaisesRegex(ValueError,'Actual complete fixed scoped report'): b.validate(self.s,self.p,b.FIRST_PAIR[0],self.r)

    def test_failed_nc_or_rule_change_blocks_every_s1(self):
        self.r['NC_A4_review']['stop_all_positive_regimes'] = True
        with self.assertRaisesRegex(ValueError,'paired NC A4'): b.validate(self.s,self.p,b.FIRST_PAIR[0],self.r)

    def test_original_failed_reservations_cannot_be_silently_released(self):
        self.r['budget']['stage1_prior_reserved_cents'] = 1310
        with self.assertRaisesRegex(ValueError,'Current necessary project budget'): b.validate(self.s,self.p,b.FIRST_PAIR[0],self.r)

    def test_wrong_proxy_or_expired_decision_rejected(self):
        self.r['budget_owner_decision']['comment']['created_at'] = '2026-10-15T14:00:00Z'
        with self.assertRaisesRegex(ValueError,'Actual bounded proxy allocation'): b.validate(self.s,self.p,b.FIRST_PAIR[0],self.r)

    def test_later_four_require_actual_futility_then_reject_stop(self):
        run = 's1_s17_n100'
        with self.assertRaises(KeyError): b.validate(self.s,self.p,run,self.r)
        futility(self.r)
        for later in list(b.RUNS)[2:]: b.validate(self.s,self.p,later,self.r)
        self.r['futility_review']['futility_stopped'] = True
        with self.assertRaises(ValueError): b.validate(self.s,self.p,run,self.r)

    def test_original_dose_and_exact_source_cannot_change(self):
        self.s['configs'][b.FIRST_PAIR[0]]['targets'] -= 1
        with self.assertRaisesRegex(ValueError,'Frozen scientific dose changed'): b.validate(self.s,self.p,b.FIRST_PAIR[0],self.r)

    def test_permanent_fence_unknown_and_order_rejected(self):
        run = b.FIRST_PAIR[0]; b.require_unused({}, {}, run, self.p)
        with self.assertRaises(ValueError): b.require_unused({}, {b.logical_key(run):{}},run,self.p)
        with self.assertRaises(ValueError): b.require_unused({'midpoint/'+b.CAMPAIGN+'/unknown':{}},{},run,self.p)
        with self.assertRaises(ValueError): b.require_unused({}, {}, b.FIRST_PAIR[1], self.p)
        prior = {b.dispatch_key(run):{'provider_app_id':'ap-original'}}
        b.require_unused(prior, {}, b.FIRST_PAIR[1], self.p)
        prior['midpoint/'+b.CAMPAIGN+'/terminal/'+run] = {'status':'failed'}
        with self.assertRaises(ValueError): b.require_unused(prior, {}, b.FIRST_PAIR[1], self.p)


class ActualWorkerBody(unittest.TestCase):
    def exercise(self, source_bad=False, model_failed=False):
        spec, plan, release = fixture(); run = b.FIRST_PAIR[0]
        tree = ast.parse(Path('experiments/learning_regime_p009/modal_stage1_s1.py').read_text())
        node = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='work')
        node.decorator_list=[]
        code = compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])), 'actual_S1_worker_body','exec')
        files, directories = {}, set()
        store = Store(spec['required_records'])
        for key in (b.dispatch_key(run),b.logical_key(run)): store[key]=b.marker(spec,run,release)
        class FakePath:
            def __init__(self,p): self.p=str(p)
            def __str__(self): return self.p
            def __truediv__(self,n): return FakePath(self.p+'/'+str(n))
            def mkdir(self,parents=False,exist_ok=False):
                if self.p in directories and not exist_ok: raise FileExistsError(self.p)
                directories.add(self.p)
            def exists(self): return self.p in directories
        def write(path,value):
            if str(path) in files: raise FileExistsError(str(path))
            files[str(path)]=copy.deepcopy(value)
        model=Mock(side_effect=RuntimeError('synthetic scientific failure') if model_failed else None,
            return_value=dict(updates=1024,targets=2097148,new_outputs=500))
        namespace=dict(Path=FakePath,modal=SimpleNamespace(Dict=SimpleNamespace(from_name=lambda *a,**k:store)),
            volume=Mock(),SPEC='in-memory-spec')
        exec(code,namespace); timer=Mock()
        def source(path): return '0'*64 if source_bad else spec['source_files'][str(path).removeprefix('/workspace/')]
        with patch('threading.Timer',return_value=timer),patch('experiments.sft_allocation_midpoint.common.read',return_value=spec),patch('experiments.sft_allocation_midpoint.common.dump',side_effect=write),patch('experiments.sft_allocation_midpoint.common.sha',side_effect=source),patch('experiments.sft_allocation_midpoint.common.manifest',return_value={'synthetic.json':{'bytes':1,'sha256':'1'*64}}),patch('experiments.sft_allocation_p008.evidence_bundle.pack'),patch('experiments.learning_regime_p009.stage1_s1_funded_runtime.execute',model):
            if source_bad or model_failed:
                with self.assertRaises((ValueError,RuntimeError)): namespace['work'](plan,run,release)
            else:
                result=namespace['work'](plan,run,release)
                self.assertEqual(result['receipt']['status'],'completed')
                self.assertAlmostEqual(model.call_args.args[-1]-model.call_args.args[-2],4500)
            timer.start.assert_called_once(); timer.cancel.assert_called_once()
        if source_bad:
            self.assertNotIn('midpoint/'+b.CAMPAIGN+'/claim/'+run,store); model.assert_not_called()
        else:
            model.assert_called_once()
            self.assertEqual(store['midpoint/'+b.CAMPAIGN+'/terminal/'+run]['status'],
                             'failed' if model_failed else 'completed')
        return store

    def test_actual_worker_success_with_real_guard(self): self.exercise()
    def test_actual_worker_changed_source_before_claim(self): self.exercise(source_bad=True)
    def test_actual_worker_scientific_failure_preserves_claim_and_terminal(self): self.exercise(model_failed=True)


if __name__ == '__main__': unittest.main()
