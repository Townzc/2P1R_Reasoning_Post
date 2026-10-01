"""Authored CPU fixtures only; no model or benchmark program execution."""
import argparse
import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

from experiments.q2_supervision_migration import screen_plan as sp
from experiments.q2_supervision_migration import screen_runtime as sr
from experiments.q2_supervision_migration import screen_scoring as sc
from experiments.q2_supervision_migration import analyze_screen as an
from experiments.q2_supervision_migration.contracts import (
    ContractError, SuiteVerdict, identity_hash, reserve_batch, record_sample, seal_batch,
    reward_from_verdicts)
from experiments.q2_supervision_migration.gpu_profile import durable_json, sha256, ProfileError


def split_fixture():
    return {'train_ids':[f'Mbpp/{i}' for i in range(250)],
            'eval_ids':[f'Mbpp/{i}' for i in range(1000,1128)]}


class PlanTests(unittest.TestCase):
    def test_exact_dose_full_coverage_and_paired_schedules(self):
        plan=sp.make_plan(split_fixture())
        self.assertEqual(plan['dose']['optimizer_updates'],640)
        self.assertEqual(plan['dose']['training_completions'],10240)
        self.assertEqual(plan['dose']['evaluation_completions'],6144)
        self.assertEqual(plan['dose']['final_checkpoints'],5)
        for stage,schedule in plan['schedules'].items():
            tasks=[t for batch in schedule for t in batch]
            self.assertEqual(set(tasks),set(plan['train_ids']))
            self.assertFalse(set(tasks)&set(plan['eval_ids']))
            self.assertEqual(len(tasks),2048)
            self.assertTrue(all(len(set(b))==2 and b[:8]==[b[0]]*8 and b[8:]==[b[8]]*8 for b in schedule))
        p={x['name']:x for x in plan['training_phases']}
        self.assertEqual(p['W_prefix']['schedule'],p['C_prefix']['schedule'])
        self.assertEqual({p[s]['trainer_seed'] for s in ['W_future','C_future','R_future']},{1})
        self.assertNotEqual(plan['schedules']['prefix'],plan['schedules']['future'])

    def test_eval_leakage_and_adaptive_dose_rejected(self):
        split=split_fixture();split['eval_ids'][0]=split['train_ids'][0]
        with self.assertRaises(ContractError):sp.make_plan(split)
        plan=sp.make_plan(split_fixture());plan['training_phases'][0]['updates']=129
        with self.assertRaises(ContractError):sp.validate_plan(plan,split_fixture())

    def test_sampler_reuses_exact_generation_batch_for_four_microsteps(self):
        ids=['Mbpp/a','Mbpp/b','Mbpp/c','Mbpp/d']
        schedule=[['Mbpp/c']*8+['Mbpp/a']*8,['Mbpp/d']*8+['Mbpp/b']*8]
        indices=sp.sampler_indices(ids,schedule)
        batches=[indices[i:i+16] for i in range(0,len(indices),16)]
        self.assertEqual(batches,[[2]*8+[0]*8]*4+[[3]*8+[1]*8]*4)
        with self.assertRaises(ContractError):sp.sampler_indices(ids,[['not-a-task']*16])

    def test_evaluation_seed_excludes_arm_identity(self):
        self.assertEqual(sp.eval_seed('Mbpp/1'),sp.eval_seed('Mbpp/1'))
        self.assertNotEqual(sp.eval_seed('Mbpp/1'),sp.eval_seed('Mbpp/2'))
        self.assertTrue(0<=sp.eval_seed('Mbpp/1')<2**31)

    def test_repaired_plan_preserves_scientific_dose_and_old_plan(self):
        old=sp.make_plan(split_fixture());new=sp.make_plan(split_fixture(),first_failure=True)
        self.assertEqual(old['dose'],new['dose'])
        self.assertEqual(old['schedules'],new['schedules'])
        self.assertNotEqual(old['run_id'],new['run_id'])
        self.assertEqual(new['limits']['worker_seconds'],10800)
        sp.validate_plan(old,split_fixture());sp.validate_plan(new,split_fixture())
        new['scoring_policy']='invented'
        with self.assertRaises(ContractError):sp.validate_plan(new,split_fixture())


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.p={'base_input':[[1]],'plus_input':[[2]],'entry_point':'fixture','atol':0}
        self.gt={'base':[1],'plus':[2],'base_time':[0.01],'plus_time':[0.01]}

    def test_weak_and_union_reward_differ_only_on_dual_verdicts(self):
        check=mock.Mock(side_effect=[('pass',[True]),('fail',[False])])
        pair=sc.score_pair(self.p,self.gt,'authored fixture only',check)
        b,e=(SuiteVerdict(**pair[k]) for k in ['base','extra'])
        self.assertEqual(reward_from_verdicts(b,e,'base'),1)
        self.assertEqual(reward_from_verdicts(b,e,'union'),0)
        self.assertEqual(check.call_count,2)

    def test_empty_extra_is_vacuous_pass_without_executing_it(self):
        self.p['plus_input']=[];self.gt['plus']=[];self.gt['plus_time']=[]
        check=mock.Mock(return_value=('pass',[True]))
        pair=sc.score_pair(self.p,self.gt,'authored fixture only',check)
        self.assertEqual(pair['extra']['status'],'pass');check.assert_called_once()
        self.assertTrue(json.loads(pair['extra']['detail'])['vacuous_empty_extra'])

    def test_infrastructure_and_incomplete_pass_never_become_zero(self):
        for error in [RuntimeError('fixture executor failure'),('pass',[])]:
            check=mock.Mock(side_effect=error) if isinstance(error,Exception) else mock.Mock(return_value=error)
            pair=sc.score_pair(self.p,self.gt,'authored fixture only',check)
            self.assertEqual(pair['base']['status'],'scorer_error')
            with self.assertRaises(ContractError):reward_from_verdicts(*(SuiteVerdict(**pair[k]) for k in ['base','extra']),'base')

    def test_bad_reference_metadata_is_not_candidate_failure(self):
        self.gt['plus_time']=[];check=mock.Mock(return_value=('pass',[True]))
        pair=sc.score_pair(self.p,self.gt,'authored fixture only',check)
        self.assertEqual(pair['extra']['status'],'scorer_error');check.assert_called_once()

    def test_first_failure_can_be_partial_but_pass_cannot(self):
        self.p['plus_input']=[[2],[3]];self.gt['plus']=[2,3];self.gt['plus_time']=[.01,.01]
        check=mock.Mock(side_effect=[('fail',[False]),('fail',[False])])
        pair=sc.score_pair(self.p,self.gt,'authored',check,fast_check=True)
        self.assertEqual(reward_from_verdicts(*(SuiteVerdict(**pair[k]) for k in ['base','extra']),'union'),0)
        self.assertTrue(all(c.kwargs['fast_check'] for c in check.call_args_list))
        for result in [('pass',[True]),('timeout',[False])]:
            pair=sc.score_pair(self.p,self.gt,'authored',mock.Mock(side_effect=[('pass',[True]),result]),fast_check=True)
            with self.assertRaises(ContractError):reward_from_verdicts(*(SuiteVerdict(**pair[k]) for k in ['base','extra']),'union')

    def test_timeout_recovery_needs_explicit_candidate_attribution(self):
        target='experiments.q2_supervision_migration.initialization_guard.diagnose_initialization_timeout'
        for confirmed,expected in [(True,'fail'),(False,'timeout')]:
            with mock.patch(target,return_value={'confirmed_candidate_initialization_failure':confirmed,'confirmed_candidate_initialization_timeout':False,'observed':[]}) as guard:
                check=mock.Mock(side_effect=[('timeout',[]),('fail',[False])])
                pair=sc.score_pair(self.p,self.gt,'authored',check,fast_check=True,recover_initialization=True)
                self.assertEqual(pair['base']['status'],expected)
                self.assertEqual(json.loads(pair['base']['detail'])['initialization_timeout_diagnosis']['original_status'],'timeout')
                guard.assert_called_once()

    def test_suite_repair_requires_completed_observed_verdict(self):
        target='experiments.q2_supervision_migration.initialization_guard.diagnose_initialization_timeout'
        for verdict,observed,expected in [('pass',[True],'pass'),('fail',[False],'fail'),(None,[True],'timeout')]:
            with mock.patch(target,return_value={'verified_suite_verdict':verdict,'observed':observed,'confirmed_candidate_initialization_failure':False}):
                pair=sc.score_pair(self.p,self.gt,'authored',mock.Mock(side_effect=[('timeout',[]),('fail',[False])]),fast_check=True,recover_suite_watchdog=True)
                self.assertEqual(pair['base']['status'],expected)
        with mock.patch(target,return_value={'verified_suite_verdict':'pass','observed':[],'confirmed_candidate_initialization_failure':False}):
            pair=sc.score_pair(self.p,self.gt,'authored',mock.Mock(side_effect=[('timeout',[]),('fail',[False])]),fast_check=True,recover_suite_watchdog=True)
            self.assertEqual(pair['base']['status'],'scorer_error')

    def test_known_verdicts_are_never_reexecuted_by_timeout_repair(self):
        target='experiments.q2_supervision_migration.initialization_guard.diagnose_initialization_timeout'
        with mock.patch(target) as guard:
            pair=sc.score_pair(self.p,self.gt,'authored',mock.Mock(side_effect=[('pass',[True]),('fail',[False])]),fast_check=True,recover_initialization=True,recover_suite_watchdog=True)
            self.assertEqual([pair[k]['status'] for k in ['base','extra']],['pass','fail'])
            guard.assert_not_called()


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.plan=sp.make_plan(split_fixture());self.p=self.root/'W_prefix';self.p.mkdir()
        self.identity='a'*64;self.config='b'*64
        durable_json(self.p/'input_receipt.json',{'source_identity':self.identity,'config_identity':self.config})
        self.tasks=self.plan['schedules']['prefix'][0]
        self.batch=reserve_batch(self.p/'batches',run_id=self.plan['run_id'],phase_id='W_prefix',batch_index=0,
            tasks=self.tasks,config_sha256=self.config,policy_sha256=identity_hash({'source':self.identity,'phase':'W_prefix','committed_updates':0}))
        for i in range(16):
            record_sample(self.batch,sample_index=i,completion_text=f'authored {i}',completion_token_ids=[i],
                base=SuiteVerdict('pass'),extra=SuiteVerdict('fail' if i%2 else 'pass'),finish_reason='authored')
        seal_batch(self.batch)
        durable_json(self.batch.directory/'raw_generations.json',{'texts':[f'authored {i}' for i in range(16)],
            'completion_ids':[[i] for i in range(16)],'task_id':self.tasks})
        durable_json(self.batch.directory/'generation_return.json',{'decoded_text':[f'authored {i}' for i in range(16)],
            'completion_ids':[[i] for i in range(16)],'prompt_ids':[[100+i] for i in range(16)]})
        durable_json(self.batch.directory/'generation_complete.json',{'global_step':0,'last_loaded_step':0})
        durable_json(self.p/'pre_update_0001.json',{'step':1,'all_finite':True,'gradient_tensors':1})
        durable_json(self.p/'update_0001.json',{'committed_update':1})

    def test_actual_partial_counts_without_scientific_claim(self):
        result,samples=an.inspect_phase(self.root,self.plan,'W_prefix')
        self.assertFalse(result['finished']);self.assertEqual(result['committed_updates'],1)
        self.assertEqual(result['signed_samples'],16);self.assertEqual(result['base_pass_extra_fail'],8)
        self.assertEqual(result['group_types']['base:all_pass'],2)
        self.assertEqual(result['group_types']['union:mixed'],2)

    def test_mutated_raw_output_rejected(self):
        path=self.batch.directory/'raw_generations.json';raw=json.loads(path.read_text());raw['texts'][0]='changed'
        path.write_text(json.dumps(raw))
        with self.assertRaises(ContractError):an.inspect_phase(self.root,self.plan,'W_prefix')

    def test_mutated_original_backend_return_rejected(self):
        path=self.batch.directory/'generation_return.json';raw=json.loads(path.read_text());raw['completion_ids'][0]=[999]
        path.write_text(json.dumps(raw))
        with self.assertRaises(ContractError):an.inspect_phase(self.root,self.plan,'W_prefix')

    def test_returned_but_unscored_dose_is_not_lost(self):
        for path in self.batch.directory.glob('sample_*.jsonl'):path.unlink()
        for name in ['batch.jsonl','raw_generations.json','generation_complete.json']:(self.batch.directory/name).unlink()
        (self.p/'pre_update_0001.json').unlink();(self.p/'update_0001.json').unlink()
        result,_=an.inspect_phase(self.root,self.plan,'W_prefix')
        self.assertEqual(result['saved_backend_completions'],16)
        self.assertEqual(result['saved_raw_completions'],0)
        self.assertEqual(result['signed_samples'],0)
        self.assertEqual(result['committed_updates'],0)

    def test_pre_step_without_post_step_remains_ambiguous(self):
        (self.p/'update_0001.json').unlink()
        result,_=an.inspect_phase(self.root,self.plan,'W_prefix')
        self.assertEqual(result['committed_updates'],0)
        self.assertEqual(result['optimizer_steps_with_uncertain_commit'],[1])

    def test_unbacked_update_and_fake_completion_rejected(self):
        durable_json(self.p/'update_0002.json',{'committed_update':2})
        with self.assertRaises(ContractError):an.inspect_phase(self.root,self.plan,'W_prefix')

    def test_phase_receipt_cannot_hide_missing_dose(self):
        durable_json(self.p/'phase_complete.json',{'plan_sha256':identity_hash(self.plan),'committed_updates':128,'training_completions':2048})
        with self.assertRaises(ContractError):an.inspect_phase(self.root,self.plan,'W_prefix')

    def test_eval_unknown_missing_and_wrong_roster_rejected(self):
        samples=[{'task_id':'Mbpp/1000','base':{'status':'pass'},'extra':{'status':'pass'}} for _ in range(8)]
        maps=an.score_maps(samples,['Mbpp/1000']);self.assertEqual(maps['union']['Mbpp/1000'],1)
        with self.assertRaises(ContractError):an.score_maps(samples[:-1],['Mbpp/1000'])
        with self.assertRaises(ContractError):an.score_maps(samples,['Mbpp/1001'])
        samples[0]['extra']['status']='timeout'
        with self.assertRaises(ContractError):an.score_maps(samples,['Mbpp/1000'])

    def test_paired_interval_and_generic_extra_training_control(self):
        ci=an.paired_question_interval({'a':.25,'b':.5},{'a':.5,'b':.75},resamples=100)
        self.assertEqual(ci['difference_pp'],-25)
        self.assertEqual(ci['conditional_question_bootstrap_95pp'],[-25,-25])
        contrasts={k:{'difference_pp':v} for k,v in [('W_future_minus_R_future',-5),('W_future_minus_C_future',-4),('C_future_minus_R_future',-1)]}
        self.assertTrue(an.descriptive_decision(contrasts)['candidate_pattern'])
        contrasts['C_future_minus_R_future']['difference_pp']=-4
        self.assertFalse(an.descriptive_decision(contrasts)['candidate_pattern'])
        self.assertFalse(an.descriptive_decision(contrasts)['scientific_confirmation'])


class EvaluationUnknownTests(unittest.TestCase):
    def test_unknown_evaluation_is_retained_and_later_samples_still_scored(self):
        with tempfile.TemporaryDirectory() as d:
            batch=reserve_batch(Path(d)/'batches',run_id='fixture',phase_id='eval_R',batch_index=0,
                tasks=['Mbpp/1','Mbpp/2'],config_sha256='a'*64,policy_sha256='b'*64)
            args=argparse.Namespace(worker_deadline_epoch=time.time()+100)
            replies=[{'base':{'status':'pass'},'extra':{'status':'timeout'}},
                     {'base':{'status':'pass'},'extra':{'status':'pass'}}]
            with mock.patch.object(sr,'receive',side_effect=replies):
                scores=sr.score_batch(args,batch,['a','b'],[[1],[2]],['Mbpp/1','Mbpp/2'],mock.Mock(),'union',['eos']*2,allow_unresolved=True)
            self.assertEqual(scores,[None,1.0])
            rows=sr.read_records(batch.directory/'batch.jsonl')
            self.assertEqual(rows[1]['extra']['status'],'timeout')
            self.assertEqual(rows[2]['base']['status'],'pass')

    def test_training_still_rejects_unknown_reward(self):
        with tempfile.TemporaryDirectory() as d:
            batch=reserve_batch(Path(d)/'batches',run_id='fixture',phase_id='R_future',batch_index=0,
                tasks=['Mbpp/1','Mbpp/2'],config_sha256='a'*64,policy_sha256='b'*64)
            args=argparse.Namespace(worker_deadline_epoch=time.time()+100)
            with mock.patch.object(sr,'receive',return_value={'base':{'status':'pass'},'extra':{'status':'timeout'}}):
                with self.assertRaises(ProfileError):
                    sr.score_batch(args,batch,['a','b'],[[1],[2]],['Mbpp/1','Mbpp/2'],mock.Mock(),'union',['eos']*2)
            rows=sr.read_records(batch.directory/'batch.jsonl')
            self.assertEqual(rows[1]['extra']['status'],'timeout')
            self.assertEqual(rows[2]['base']['status'],'pass')
            self.assertEqual(rows[2]['extra']['status'],'timeout')


class ParentTests(unittest.TestCase):
    def test_disk_gate_and_shared_deadline(self):
        with mock.patch.object(sr.shutil,'disk_usage',return_value=argparse.Namespace(free=2*1024**3)):
            with self.assertRaises(ProfileError):sr.disk_gate('.')
        with self.assertRaises(TimeoutError):sr.remaining(argparse.Namespace(worker_deadline_epoch=time.time()-1))

    def test_parent_stops_at_failure_without_retry_or_evaluation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);split=root/'split.json';split.write_text(json.dumps(split_fixture()))
            plan=root/'plan.json';plan.write_text(json.dumps(sp.make_plan(split_fixture())))
            argv=['--model-path',str(root/'model'),'--model-manifest',str(root/'manifest.json'),
                '--data-json',str(root/'data.jsonl'),'--data-sha256','a'*64,
                '--split-json',str(split),'--split-sha256',sha256(split),
                '--plan-json',str(plan),'--plan-sha256',sha256(plan),
                '--out',str(root/'run'),'--source-commit','b'*40,
                '--provider-deadline-epoch',str(time.time()+14000),'--execute-screen']
            with mock.patch.object(sr.platform,'system',return_value='Linux'), \
                 mock.patch.object(sr,'disk_gate',return_value={}), \
                 mock.patch.object(sr,'validate_environment',return_value={}), \
                 mock.patch.object(sr,'verify_model',return_value='a'*64), \
                 mock.patch.object(sr.subprocess,'check_output',return_value=''), \
                 mock.patch.object(sr,'launch_guarded',side_effect=[0,1]) as launch:
                self.assertEqual(sr.main(argv),1)
                self.assertEqual(launch.call_count,2)
                self.assertEqual([x.args[0][-1] for x in launch.call_args_list],['references','W_prefix'])
                self.assertLessEqual(launch.call_args_list[0].args[2],600)
                self.assertLessEqual(launch.call_args_list[1].args[2],2700)
                self.assertFalse((root/'run/C_prefix').exists())
                with self.assertRaises(FileExistsError):sr.main(argv)
                self.assertEqual(launch.call_count,2)

if __name__=='__main__':unittest.main()
