import ast
import copy
import json
import unittest
from pathlib import Path
from tests.test_p008_lineage_student import fixture as lineage_fixture
from tests.test_p008_student_concurrency import fixture as quota_fixture
from experiments.sft_allocation_midpoint.common import digest
from experiments.sft_allocation_p008.completion_queue import (
    make_plan, validate_plan, transfer_record, assert_original_absent,
    require_handoff, ORIGINAL_CAMPAIGN, TRANSFER_KEY, LEDGER_LIFETIME_SECONDS)
from experiments.sft_allocation_p008.completion_student_binding import validate_student_binding

PACKET = Path('reports/p008_20261013/student_completion_queue_v1')


def records():
    return (json.loads((PACKET/'ORIGINAL_PLAN.json').read_text()),
            json.loads((PACKET/'OWNER_COMPLETION.json').read_text()))


def fixture():
    _, cfg, release, spec = lineage_fixture()
    original, owner = records()
    plan = make_plan(original, owner, original['created_epoch'] + 100)
    spec.update(original_plan=original, plan_sha256=digest(plan), branch=[8, False, 2],
                student_completion_owner_sha256=digest(owner))
    qs, qg = quota_fixture()
    spec.update(qs)
    release['gates'].update(qg, student_completion_owner=owner,
                            student_slot_transfer=transfer_record(plan, original, owner))
    spec['config_sha256'][cfg['run_id']] = digest(cfg)
    rehash(release, spec)
    return plan, cfg, release, spec


def rehash(release, spec):
    release['spec_sha256'] = digest(spec)
    release['gates']['runtime_review']['spec_sha256'] = digest(spec)


class CompletionQueueTests(unittest.TestCase):
    def test_exact_original_reservations_only(self):
        original, owner = records(); plan = make_plan(original, owner, original['created_epoch'])
        self.assertEqual(len(plan['slots']), 20)
        self.assertEqual(plan['total_cap_cents'], 19460)
        self.assertNotIn('pool_d2', plan['slots'])
        self.assertEqual(plan['slots'], {r: original['slots'][r] for r in plan['slots']})
        self.assertEqual(transfer_record(plan, original, owner)['additional_budget_cents'], 0)

    def test_original_not_mutated_or_relabelled(self):
        original, owner = records(); before=copy.deepcopy(original)
        plan=make_plan(original, owner, original['created_epoch'])
        self.assertEqual(original, before)
        self.assertNotEqual(plan['campaign_id'], original['campaign_id'])

    def test_six_day_envelope_is_below_dict_retention(self):
        self.assertLess(LEDGER_LIFETIME_SECONDS, 7*24*3600)

    def test_new_deadline_not_authority_for_new_slot(self):
        original, owner = records(); plan=make_plan(original, owner, original['created_epoch'])
        plan['slots']['extra']=dict(stage='main',reserved_cents=1)
        with self.assertRaises(ValueError):validate_plan(plan,original,owner)

    def test_cannot_extend_original_teacher_or_spending(self):
        for key in ('deadline_epoch','total_cap_cents'):
            original, owner=records();original[key]+=1
            with self.assertRaises(ValueError):make_plan(original,owner,original['created_epoch'])

    def test_relay_or_different_concurrency_cannot_replace_owner(self):
        for key,value in [('authority','Reviewer relay'),('maximum_student_H100_workers',10),
                          ('stage_cap_usd',251),('d2_continuation_deadline_unchanged',False)]:
            original,owner=records();owner[key]=value
            with self.assertRaises(ValueError):make_plan(original,owner,original['created_epoch'])

    def test_any_legacy_claim_intent_terminal_or_unit_blocks_transfer(self):
        run='d1_b1_p0_breadth_t1';prefix='midpoint/'+ORIGINAL_CAMPAIGN+'/'
        for suffix in ['claim/'+run,'intent/'+run,'terminal/'+run,run+'/unit/update_0001',
                       'audit/done/pool_d1','attempt/'+run+'/old']:
            with self.assertRaises(ValueError):assert_original_absent({prefix+suffix:{}})

    def test_original_teacher_history_is_retained_and_allowed(self):
        prefix='midpoint/'+ORIGINAL_CAMPAIGN+'/'
        assert_original_absent({prefix+'terminal/pool_d2':{'status':'failed'},prefix+'pool_d1/unit/first':{}})

    def test_actual_exact_handoff_and_original_absence_required(self):
        original,owner=records();plan=make_plan(original,owner,original['created_epoch'])
        expected=transfer_record(plan,original,owner)
        db={TRANSFER_KEY:expected}
        self.assertEqual(require_handoff(db,plan,original,owner,'base'),expected)
        db['midpoint/'+ORIGINAL_CAMPAIGN+'/claim/base']={}
        with self.assertRaises(ValueError):require_handoff(db,plan,original,owner,'base')

    def test_missing_handoff_cannot_start(self):
        original,owner=records();plan=make_plan(original,owner,original['created_epoch'])
        with self.assertRaises(ValueError):require_handoff({},plan,original,owner,'base')

    def test_true_lineage_joint_review_and_quota_still_required(self):
        self.assertTrue(validate_student_binding(*fixture()))
        for name in ('joint_plan_gate','runtime_review','student_quota'):
            a=fixture();a[2]['gates'][name]={}
            with self.assertRaises((ValueError,KeyError)):validate_student_binding(*a)

    def test_rehashed_scope_or_dose_change_rejected(self):
        for key in ('updates','targets','seed'):
            a=fixture();a[1][key]+=1;a[3]['config_sha256'][a[1]['run_id']]=digest(a[1]);rehash(a[2],a[3])
            with self.assertRaises(ValueError):validate_student_binding(*a)

    def test_changed_authority_even_rehashed_rejected(self):
        a=fixture();a[2]['gates']['student_completion_owner']['stage_cap_usd']=500
        a[3]['student_completion_owner_sha256']=digest(a[2]['gates']['student_completion_owner']);rehash(a[2],a[3])
        with self.assertRaises(ValueError):validate_student_binding(*a)

    def test_rehashed_pool_failure_is_not_completed(self):
        a=fixture();a[3]['pool_lineages']['2']['parent']['terminal']['status']='completed';rehash(a[2],a[3])
        with self.assertRaises(ValueError):validate_student_binding(*a)

    def test_oracle_raw_dose_state_body_unchanged(self):
        def fn(path):return next(n for n in ast.parse(Path(path).read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='audit')
        self.assertEqual(ast.dump(fn('scripts/audit_p008_student_lineage.py')),ast.dump(fn('scripts/audit_p008_student_completion.py')))

    def test_worker_science_and_caps_unchanged(self):
        calls=[]
        for name in ('modal_students_eight','modal_students_completion'):
            tree=ast.parse(Path('experiments/sft_allocation_p008/'+name+'.py').read_text())
            calls.append([ast.dump(n) for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                          and n.func.id in ('execute','BlockTrainingJournal','GPURecorder')])
        self.assertEqual(*calls)
        text=Path('experiments/sft_allocation_p008/modal_students_completion.py').read_text()
        self.assertIn("stop=min(start+config['max_seconds'],plan['deadline_epoch']-30)",text)
        self.assertIn('retries=0,max_containers=8,min_containers=0',text)
        self.assertEqual(text.count('require_handoff(claims,'),2)


if __name__=='__main__':unittest.main()
