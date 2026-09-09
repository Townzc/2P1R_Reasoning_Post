"""Synthetic unit fixtures only; no learned model or experiment output."""
import copy
import itertools
import json
import math
from pathlib import Path
import unittest

from src.relation_transport import make_world, render_prompt, allocation_schedule
from src.relation_verifier import orbit_key, STEP
from src.relation_diagnostics import CONFIG, derive_rows, prepare
from src.relation_diagnostic_verifier import (required_route, check_diagnostic,
    score, summarize, token_fields, teacher_forced_metrics, FIELDS)
from src.sft_data import encode_row, budget_report
from scripts.verify_relation_diagnostics import audit_payload


class CharacterTokenizer:
    eos_token_id = 2
    def __call__(self, text, **kwargs):
        return {'input_ids': [ord(c)+3 for c in text],
                'offset_mapping': [(i, i+1) for i in range(len(text))]}


def fixture_worlds():
    worlds = [make_world(seed, i, split='unit_fixture')
              for seed, count in ((9901,32),(9981,16)) for i in range(count)]
    for w in worlds: w['audit'] = {'orbit': orbit_key(w['question'])}
    return worlds


class DiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = {**json.loads(CONFIG.read_text()), 'max_length': 10000}
        cls.worlds = fixture_worlds(); cls.tokenizer = CharacterTokenizer()
        cls.rows, cls.schedules, cls.assignment, cls.budgets = prepare(cls.worlds, cls.cfg, cls.tokenizer)
        cls.legacy_train = [{'problem_id': w['world_id'], 'prompt': w['prompt'], 'path_id': str(i), 'response': text}
                           for w in cls.worlds[:32] for i, text in enumerate(w['responses'])]
        ids = [w['world_id'] for w in cls.worlds[:32]]
        positions = {(r['problem_id'], int(r['path_id'])): i for i,r in enumerate(cls.legacy_train)}
        cls.legacy_schedule = [[positions[(wid,r)] for wid,r in zip(u['world_ids'],u['multi'])]
                              for u in allocation_schedule(ids,81401,8)['updates']]
        cls.legacy_budget = json.loads(json.dumps(budget_report(
            [encode_row(r,cls.tokenizer,10000) for r in cls.legacy_train],cls.legacy_schedule,2)))

    def audit(self, rows=None, schedules=None, budgets=None, assignment=None):
        return audit_payload(self.rows if rows is None else rows,
            self.schedules if schedules is None else schedules,
            self.budgets if budgets is None else budgets,
            self.assignment if assignment is None else assignment,
            self.worlds,self.legacy_train,self.legacy_schedule,self.legacy_budget,self.cfg,self.tokenizer)

    def test_independent_reconstruction_and_original_dose(self):
        report = self.audit()
        self.assertTrue(report['verified']); self.assertEqual(report['derived_rows'],288)
        self.assertEqual(report['checks']['valid_references'],288)
        self.assertEqual(report['checks']['source_state_counterfactuals'],288)
        self.assertEqual(report['single_step_forward_rows'],192)
        self.assertEqual(report,json.loads(json.dumps(report)))
        for arm in self.cfg['arms']:
            self.assertEqual(self.budgets[arm]['presentations'],1024)
            self.assertEqual(set(self.budgets[arm]['parent_exposures'].values()),{32})

    def test_wrong_route_is_distinct_from_wrong_math(self):
        full = next(r for r in self.rows if r['arm']=='fixed_reference')
        given = next(r for r in self.rows if r['arm']=='given_route')
        w = self.worlds[0]; other = w['responses'][(full['selected_route']+1)%4]
        self.assertTrue(score(full,other,True,False)['complete_correct'])
        self.assertFalse(score(full,other,True,False)['reference_exact'])
        self.assertEqual(score(given,other,True,False)['certificate']['reason'],'wrong_required_route')
        self.assertEqual(len(required_route(given['prompt'])),4)

    def test_malformed_absent_or_disconnected_hint_rejected(self):
        given = next(r for r in self.rows if r['arm']=='given_route')
        route = required_route(given['prompt']); e,u,v = route[0]
        for altered in (given['prompt'].replace(f'R E {e}', 'R E 999',1),
                        given['prompt'].replace(f'R E {e} : N {u} > N {v}',f'R E {e} : N {v} > N {u}',1),
                        self.worlds[0]['prompt']):
            self.assertFalse(check_diagnostic(altered,given['response'],'given_route')['valid'])

    def test_eos_truncation_and_answer_only_cannot_pass(self):
        r = self.rows[0]
        self.assertFalse(score(r,r['response'],False,False)['complete_correct'])
        self.assertFalse(score(r,r['response'],True,True)['complete_correct'])
        result = score(r,f"Answer : {r['answer']}",True,False)
        self.assertTrue(result['answer_correct']); self.assertFalse(result['complete_correct'])
        self.assertTrue(score(r,' \n'+r['response']+'\t ',True,False)['complete_correct'])

    def test_truncation_does_not_hide_local_lookup_errors(self):
        r = self.rows[0]; line = r['response'].splitlines()[0]
        match = STEP.fullmatch(line); a,b = match.span(5)
        bad = line[:a]+str((int(match.group(5))+1)%5)+line[b:]
        result = score(r,bad,False,True)
        self.assertEqual(result['certificate']['reason'],'missing_final')
        self.assertEqual(result['local_steps']['grounded_lines'],1)
        self.assertEqual(result['local_steps']['locally_correct_lines'],0)

    def test_parent_denominator_rejects_missing_subproblems(self):
        rows = [r for r in self.rows if r['arm']=='single_step' and r['split']=='train']
        scores = [score(r,r['response'],True,False) for r in rows]
        self.assertEqual(summarize(rows,scores)['all_correct_parents'],32)
        scores[0] = score(rows[0],rows[0]['response'],False,True)
        self.assertEqual(summarize(rows,scores)['all_correct_parents'],31)
        with self.assertRaises(ValueError): summarize(rows[:-1],scores[:-1])

    def test_row_loss_mask_and_split_tampering_rejected(self):
        variants = []
        for field,value in (('split','train'),('answer',9),('selected_route',9)):
            rows = copy.deepcopy(self.rows); rows[-1][field] = value; variants.append(rows)
        rows = copy.deepcopy(self.rows); rows[0]['token_fields']['after_state'][0] = 0; variants.append(rows)
        variants.extend((self.rows[:-1], self.rows+[self.rows[0]]))
        for rows in variants:
            with self.assertRaises(ValueError): self.audit(rows=rows)

    def test_schedule_and_budget_tampering_rejected(self):
        schedule = copy.deepcopy(self.schedules); schedule['fixed_reference'][0].reverse()
        with self.assertRaises(ValueError): self.audit(schedules=schedule)
        budget = copy.deepcopy(self.budgets); budget['single_step']['presentations'] += 1
        with self.assertRaises(ValueError): self.audit(budgets=budget)
        assignment = dict(self.assignment); assignment[self.worlds[0]['world_id']] = 9
        with self.assertRaises(ValueError): self.audit(assignment=assignment)

    def test_semantic_metrics_expose_dilution_and_mask_prompt(self):
        r = self.rows[0]; enc = encode_row(r,self.tokenizer,10000); fields = r['token_fields']
        losses = [None]*len(enc['input_ids']); correct = [None]*len(losses)
        for positions in fields.values():
            for i in positions: losses[i] = 0.0; correct[i] = True
        for i in fields['after_state']: losses[i] = math.log(5); correct[i] = False
        metric = teacher_forced_metrics(enc,fields,losses,correct)
        self.assertLess(metric['all_response']['nll'],.2)
        self.assertAlmostEqual(metric['by_field']['after_state']['nll'],math.log(5))
        self.assertEqual(metric['by_field']['after_state']['accuracy'],0)
        self.assertEqual(metric['by_field']['eos']['tokens'],1)
        self.assertEqual(sum(x['tokens'] for x in metric['by_field'].values()),enc['n_supervised'])
        losses[0] = 0
        with self.assertRaises(ValueError): teacher_forced_metrics(enc,fields,losses,correct)

    def test_nonfinite_duplicate_or_unshifted_statistics_rejected(self):
        r = self.rows[0]; enc = encode_row(r,self.tokenizer,10000); fields = r['token_fields']
        losses = [0.0 if i and x!=-100 else None for i,x in enumerate(enc['labels'])]
        correct = [True if x is not None else None for x in losses]
        losses[fields['after_state'][0]] = float('nan')
        with self.assertRaises(ValueError): teacher_forced_metrics(enc,fields,losses,correct)
        losses[fields['after_state'][0]] = .1
        wrong = copy.deepcopy(fields); wrong['other_response'].append(fields['after_state'][0])
        with self.assertRaises(ValueError): teacher_forced_metrics(enc,wrong,losses,correct)
        with self.assertRaises(ValueError): teacher_forced_metrics(enc,fields,losses[1:],correct[1:])

    def test_real_pinned_tokenizer_field_spans_on_synthetic_world(self):
        from scripts.audit_family_matching import verified_tokenizer
        cache = Path('.local/hf-cache/hub/models--Qwen--Qwen2.5-1.5B/snapshots/8faed761d45a263340a0528343f099c05c9a4323')
        if not cache.exists(): self.skipTest('Pinned local tokenizer required before release')
        tokenizer,_ = verified_tokenizer(cache)
        for arm in self.cfg['arms']:
            row = next(r for r in self.rows if r['arm']==arm)
            enc = encode_row(row,tokenizer,1536); fields = token_fields(row,tokenizer,enc)
            expected = 1 if arm=='single_step' else 4
            self.assertEqual(len(fields['after_state']),expected)
            self.assertEqual(len(fields['final_state']),1)
            self.assertEqual(sum(map(len,fields.values())),enc['n_supervised'])
            for name in FIELDS[:6]:
                for pos in fields[name]:
                    self.assertTrue(tokenizer.decode([enc['input_ids'][pos]]).isdigit())


class ExhaustivePrimitiveTests(unittest.TestCase):
    def test_all_120_permutations_five_states_both_directions(self):
        count = 0
        for table in itertools.permutations(range(5)):
            for x in range(5):
                for reverse in (False,True):
                    u,v = (101,100) if reverse else (100,101)
                    y = table.index(x) if reverse else table[x]
                    q = {'source':u,'target':v,'state':x,
                         'edges':[{'id':200,'u':100,'v':101,'table':list(table)}]}
                    prompt = render_prompt(q)
                    response = f'E 200 : N {u} = {x} > N {v} = {y}\nAnswer : {y}'
                    self.assertTrue(check_diagnostic(prompt,response,'single_step')['valid'])
                    wrong = f'E 200 : N {u} = {x} > N {v} = {(y+1)%5}\nAnswer : {(y+1)%5}'
                    self.assertFalse(check_diagnostic(prompt,wrong,'single_step')['valid'])
                    count += 1
        self.assertEqual(count,1200)


if __name__ == '__main__': unittest.main()
