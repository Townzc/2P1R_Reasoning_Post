import copy
import json
import math
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np

from experiments.post_e039_decision_supervision import analyze as a
from experiments.post_e036_goal_probe.scoring import score
from tests.test_post_e037_analysis import fixture
from src.sft_data import read_jsonl, sha256_file


class DecisionAnalysisTests(unittest.TestCase):
    def test_joint_recipe_mean_uses_paired_draws_and_is_not_two_seeds(self):
        families={'g0':'f0','g1':'f0','g2':'f1','g3':'f2'}
        values={s:{g:0. for g in families} for s in a.STATES}
        values['S-D']={'g0':1.,'g1':1.,'g2':0.,'g3':0.}
        values['P-U']=dict(values['S-D'])
        result=a.joint_six_state_contrasts(values,families)
        self.assertEqual(a.BOOTSTRAP_SEED,2026091714)
        self.assertEqual(result['bootstrap_replicates'],10000)
        self.assertEqual(result['contrasts']['delta_S']['mean'],.5)
        self.assertEqual(result['contrasts']['delta_P']['mean'],-.5)
        pooled=result['contrasts']['equal_recipe_mean']
        self.assertEqual(pooled['mean'],0.)
        self.assertEqual(pooled['group_ci'],[0.,0.])
        self.assertEqual(pooled['family_ci'],[0.,0.])
        self.assertEqual(result['joint_state_order'],list(a.STATES))
        reordered={s:dict(reversed(list(values[s].items()))) for s in reversed(a.STATES)}
        self.assertEqual(result,a.joint_six_state_contrasts(reordered,dict(reversed(list(families.items())))))
        with self.assertRaisesRegex(ValueError,'all six'):
            a.joint_six_state_contrasts({s:values[s] for s in a.STATES[1:]},families)

    def test_actual_F_one_prompt_per_question_retains_all_invalids(self):
        rows,records=fixture('F')
        rows=rows[::2]; records=records[::2]
        stop=dict(answer_segment='unfinished',stop_reason='length_cap')
        records[0]=dict(records[0],stop=stop,score=score(rows[0],stop))
        before=copy.deepcopy(records)
        result=a.training_metrics(records,rows,1,'E038')
        self.assertEqual(result['correct']['numerator'],3)
        self.assertEqual(result['correct']['denominator'],4)
        self.assertNotIn('both_targets_correct',result)
        self.assertFalse(result['H_to_F_transfer'])
        self.assertEqual(records,before)
        with self.assertRaisesRegex(ValueError,'every frozen'):
            a.view_metrics(records[:-1],rows,1)
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            a.view_metrics(records+records[:1],rows,1)

    def test_pair_success_differs_from_per_target_and_samples_nested(self):
        rows,records=fixture('H',successes={(g,0,0) for g in range(4)})
        result=a.view_metrics(records,rows,1)
        self.assertEqual(result['correct']['numerator'],4)
        self.assertEqual(result['both_targets_correct']['numerator'],0)
        rows,records=fixture('F',samples=4,successes={(g,0,0) for g in range(4)})
        result=a.view_metrics(records,rows,4)
        self.assertEqual(result['correct']['denominator'],32)
        self.assertEqual(result['correct']['groups'],4)
        self.assertEqual(result['pass_at_4']['numerator'],4)
        self.assertEqual(result['pass_at_4']['denominator'],8)

    def test_supervised_countergoal_distinguished_from_anchor(self):
        rows,records=fixture('H')
        s=a.training_metrics(records,rows,1,'S-D')
        p=a.training_metrics(records,rows,1,'P-U')
        self.assertFalse(s['target_exposure']['countergoal']['H_target_supervised'])
        self.assertTrue(p['target_exposure']['countergoal']['H_target_supervised'])
        self.assertTrue(s['target_exposure']['anchor']['H_target_supervised'])

    def test_literal_mismatch_is_not_error_for_alternative_valid_F(self):
        rows,_=fixture('F'); row=rows[0]
        stop=dict(answer_segment='Answer: (3 * (12 - 5)) - 2',stop_reason='native_eos')
        record=dict(stop=stop,score=score(row,stop))
        self.assertTrue(record['score']['correct'])
        result=a.semantic_divergence(row,record)
        self.assertEqual(result['conclusion'],'valid_alternative_F_is_accepted')
        self.assertIsNone(result['first_certified_error'])
        self.assertEqual(result['F_prefix_dead_end']['status'],'unknown')
        mismatch=a.literal_divergence([1,2,8,0],[[1,2,3,0],[1,9,0]])
        self.assertEqual(mismatch['token_index'],2)
        self.assertEqual(mismatch['reference_index'],0)
        self.assertEqual(a.literal_divergence([1,0],[[1,0]])['status'],'identical_reference')
        self.assertEqual(a.literal_divergence([1,0],[])['status'],'unknown')

    def test_false_equation_and_wrong_target_separated_from_first_semantic_cause(self):
        rows,_=fixture('F'); row=rows[0]
        stop=dict(answer_segment='Step 1: 12 - 5 = 6.\nAnswer: (12 - 5) * 3 - 2',stop_reason='native_eos')
        record=dict(stop=stop,score=score(row,stop))
        result=a.semantic_divergence(row,record)
        self.assertTrue(record['score']['correct'])  # frozen score is final-expression based
        self.assertEqual(result['first_certified_error']['kind'],'false_or_undefined_local_equation')
        self.assertEqual(result['first_semantic_error']['status'],'unknown')
        self.assertEqual(result['local_equations_status'],'inconsistent')
        stop=dict(answer_segment='Step 1: 12 + 5 = 17.\nAnswer: (12 + 5) * 3 - 2',stop_reason='native_eos')
        result=a.semantic_divergence(row,dict(stop=stop,score=score(row,stop)))
        self.assertEqual(result['local_equations_status'],'consistent')
        self.assertEqual(result['first_certified_error']['kind'],'strict_final_expression_violation')
        self.assertEqual(result['first_semantic_error']['status'],'unknown')

    def test_partial_six_state_grid_does_not_fabricate_zero(self):
        rows_by_key={k:fixture(i,4 if False else 1)[0] for k,i in [('eval_F','F'),('eval_H','H')]}
        events=[]
        for s in a.STATES:
            for i,dec,n in [('H','greedy',1),('F','greedy',1),('F','sampled',4)]:
                events.append(dict(name=f'{s}_{i}_{dec}',state=s,interface=i,decoding=dec,samples=n,
                    data_key='eval_'+i,view='eval',checkpoint_step=256 if s in a.STATES[:2] else 128))
        result=a.analyze_generations({},rows_by_key,events)
        self.assertEqual(len(result['views']),18)
        self.assertTrue(all(v['metrics'] is None for v in result['views']))
        self.assertTrue(all(v['result'] is None for v in result['contrasts']))
        self.assertTrue(all(len(v['missing_views'])==6 for v in result['contrasts']))

    def test_generated_first_H_decision_only_with_valid_same_prefix(self):
        from experiments.post_e039_decision_supervision.decision_spans import annotate
        from tests.test_decision_spans import CharacterTokenizer
        rows=read_jsonl('experiments/post_e037_goal_training/release_v1/single.jsonl')
        for row in (rows[0],next(r for r in rows[:512] if r['hole_path'])):
            span=annotate(row,CharacterTokenizer());start,end=span['response_char_span']
            other=next(op for op in '+-*/' if op!=row['correct_operator'])
            changed=row['response'][:start]+other+row['response'][end:]
            result=a.generated_first_decision(row,changed,[row['response']])
            self.assertEqual(result['status'],'same_valid_reference_prefix')
            self.assertFalse(result['correct'])
            self.assertEqual(a.generated_first_decision(row,'Different. '+changed,[row['response']])['status'],'unknown')

    def test_lossless_alignment_argmax_ties_and_real_mismatch(self):
        vector=np.array([1.,4.,4.,3.],dtype=np.float32)
        bits=vector.view(np.int32).tolist()
        record=dict(raw_logits_fp32_bits=bits,effective_logits_fp32_bits=bits,
            raw_argmax=1,effective_argmax=1,raw_argmax_tokens=[1,2],effective_argmax_tokens=[1,2],
            raw_effective_exact_equal=True,generated_token=1,status='aligned')
        self.assertTrue(a.audit_alignment_vectors(record))
        changed=dict(record,generated_token=2,status='genuine_effective_argmax_mismatch')
        self.assertFalse(a.audit_alignment_vectors(changed))  # tie uses first index
        changed=dict(record,effective_argmax_tokens=[1])
        with self.assertRaisesRegex(ValueError,'argmax/tie'):
            a.audit_alignment_vectors(changed)

    def test_alignment_observation_before_raw_commit_is_partial_not_false_pass(self):
        from experiments.post_e039_decision_supervision import diagnostics as d
        from experiments.post_e039_decision_supervision.decision_spans import annotate
        from tests.test_decision_spans import CharacterTokenizer
        row=read_jsonl('experiments/post_e037_goal_training/release_v1/single.jsonl')[0]
        tok=CharacterTokenizer();span=annotate(row,tok);cases=d.make_alignment_cases([row],[span],tok)
        case=cases[0];prompt=case['prompt_ids'];output=prompt+[0]
        identity=dict(model_hash='a'*64,split_hash='b'*64)
        bits=np.array([1.,0.],dtype=np.float32).view(np.int32).tolist()
        check=dict(batch_row=0,step=0,effective_argmax=0,generated_token=0,source_row_sha256=case['source_row_sha256'])
        observation=dict(**check,prefix_ids=prompt,generated_prefix_ids=[],raw_logits_fp32_bits=bits,
            effective_logits_fp32_bits=bits,raw_argmax=0,raw_argmax_tokens=[0],effective_argmax_tokens=[0],
            raw_effective_exact_equal=True,status='aligned',reference_token=case['reference_response_ids'][0],
            reference_prefix_matches=True,first_literal_deviation=True,is_reference_decision_position=False)
        batch=dict(identity=dict(identity=identity,cases_sha256=a.digest(cases),prompt_batch_ids=[prompt],attention_mask=[[1]*len(prompt)]),
            output_ids=[output],selection_checks=[check],observations=[observation],genuine_mismatches=[],
            extra_forward_calls=0,extra_generations=0,model_training=False)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'alignment'/'E038_stage_a_H_greedy.json'
            folder=path.with_suffix('.observations');folder.mkdir(parents=True)
            file=folder/'batch.json';file.write_text(json.dumps(batch))
            artifact=dict(identity=identity,cases=cases,cases_sha256=a.digest(cases),
                batch_files_sha256={file.name:sha256_file(file)},observed_cases=[case['source_row_sha256']],
                missing_cases=[],genuine_mismatches=0,extra_forward_calls=0,extra_generations=0)
            path.write_text(json.dumps(artifact));event=dict(name='E038_stage_a_H_greedy')
            result=a.audit_alignment(path,event,[row],[row],[span],tok,'a'*64,'b'*64)
            self.assertEqual(result['status'],'incomplete')
            self.assertEqual(result['committed_observed_cases'],0)
            self.assertEqual(len(result['uncommitted_observation_batches']),1)
            raw=dict(input_ids=[prompt],attention_mask=[[1]*len(prompt)],output_ids=[output],stop_events=[dict(retained_tokens=1)])
            (root/(event['name']+'.raw_batches.jsonl')).write_text(json.dumps(raw)+'\n')
            self.assertEqual(a.audit_alignment(path,event,[row],[row],[span],tok,'a'*64,'b'*64)['status'],'passed')
            (root/(event['name']+'.raw_batches.jsonl')).unlink()
            (root/(event['name']+'.summary.json')).write_text(json.dumps(dict(status='completed')))
            with self.assertRaisesRegex(ValueError,'Completed generation alignment'):
                a.audit_alignment(path,event,[row],[row],[span],tok,'a'*64,'b'*64)

    def test_durable_reference_forward_replay_causal_partition_and_intent(self):
        import torch
        from experiments.post_e039_decision_supervision import diagnostics as d
        from experiments.post_e039_decision_supervision.decision_spans import annotate
        from experiments.post_e039_decision_supervision.launcher import ForwardBudget
        from tests.test_decision_spans import CharacterTokenizer
        class Tok(CharacterTokenizer): eos_token_id=127
        class Model:
            training=False
            def eval(self):self.training=False
            def train(self,value=True):self.training=value
        tokenizer=Tok();row=read_jsonl('experiments/post_e037_goal_training/release_v1/single.jsonl')[0]
        span=annotate(row,tokenizer)
        def forward(model,ids,device):
            logits=torch.linspace(-1,1,128).reshape(1,1,128).expand(1,len(ids),128)
            return logits,dict(forward_calls=1,input_tokens=len(ids),seconds=.1,logits_dtype='torch.float32',use_cache=False)
        with tempfile.TemporaryDirectory() as tmp,patch.object(d,'_forward',side_effect=forward):
            root=Path(tmp);path=root/'reference.json';budget=ForwardBudget(root/'ledger.json')
            identity=dict(state='E038',adapter_sha256='a'*64,release_manifest_sha256='b'*64,rows_sha256=a.digest([row]))
            result=d.run_decomposition(Model(),tokenizer,[row],[span],path,identity=identity,
                forward_budget=budget,deadline=time.time()+300,device='cpu')
            summary,_=a._audit_forward_view(path,[row],[span],identity,budget.record(),tokenizer)
            self.assertEqual(summary['status'],'completed')
            self.assertEqual(summary['partitions']['decision_mask']['tokens'],1)
            self.assertAlmostEqual(summary['partitions']['full']['nll_sum'],
                summary['partitions']['decision_mask']['nll_sum']+summary['partitions']['rest']['nll_sum'])
            saved=path.read_bytes();path.unlink()
            partial,_=a._audit_forward_view(path,[row],[span],identity,budget.record(),tokenizer)
            self.assertEqual(partial['status'],'partial')
            self.assertEqual(partial['completed_records'],1)
            self.assertEqual(partial['aggregate_publication'],'missing')
            self.assertEqual(partial['published_records'],0)
            path.write_bytes(saved)
            record=copy.deepcopy(result['records'][0]);record['causal_logit_positions'][0]+=1
            with self.assertRaisesRegex(ValueError,'causal identity'):
                a.validate_decomposition(record,row,span,tokenizer)
            record=copy.deepcopy(result['records'][0]);record['partitions']['full']['nll_sum']+=.1
            with self.assertRaisesRegex(ValueError,'partition arithmetic'):
                a.validate_decomposition(record,row,span,tokenizer)
            intent=path.with_suffix('.resume')/'000000.intent.json';value=json.loads(intent.read_text())
            value['sequence_equivalents']=4;intent.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,'Immutable forward'):
                a._audit_forward_view(path,[row],[span],identity,budget.record(),tokenizer)

    def test_new_generation_seed_and_single_prompt_replay(self):
        from experiments.post_e039_decision_supervision import generation as gen
        from tests.test_goal_probe_runtime import RuntimeTests
        from tests.test_thursday_v2_resumable_generation import Model,Tokenizer,Budget
        self.assertEqual(gen.SEED,2026091713)
        for samples in (1,4):
            rows,_=fixture('F',samples)
            if samples==1:rows=rows[::2]  # actual-F training shape
            for row in rows:row['prompt']='Use the numbers.'
            event=dict(name='E038_test_F',state='E038',interface='F',decoding='sampled' if samples==4 else 'greedy',
                samples=samples,sampling=samples==4,view='eval' if samples==4 else 'stage_a',
                questions=len(rows),generations=len(rows)*samples,evaluation_seed=2026091713)
            with tempfile.TemporaryDirectory() as tmp,RuntimeTests().cpu():
                root=Path(tmp);release=root/'release';release.mkdir();(release/'manifest.json').write_text('{}')
                path=root/'E038_test_F.jsonl';budget=Budget(root/'ledger.json')
                identity=dict(model_hash='a'*64,split_hash=sha256_file(release/'manifest.json'),batch_time_reserve_seconds=120.)
                result=gen.run_event(Model(),Tokenizer(),rows,path,event,identity,99,budget,1e20)
                summary=dict(status='completed',completed_records=len(result['records']),predictions_sha256=sha256_file(path),
                    adapter={'sha256':'a'*64},substreams=result.get('substreams',[]))
                checked,_=a.audit_completed_view(path,rows,event,summary,Tokenizer(),budget.record(),release,'a'*64)
                self.assertEqual(len(checked),len(rows)*samples)
                # Public rehashing cannot hide disagreement with durable scored commits.
                checked[0]['score']['correct']=not checked[0]['score']['correct']
                path.write_text(''.join(json.dumps(r)+'\n' for r in checked));summary['predictions_sha256']=sha256_file(path)
                with self.assertRaises(ValueError):
                    a.audit_completed_view(path,rows,event,summary,Tokenizer(),budget.record(),release,'a'*64)


if __name__=='__main__':
    unittest.main()
