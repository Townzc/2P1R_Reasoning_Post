from copy import deepcopy
import itertools
import unittest

from src.relation_transport import (compose, inverse, make_world, views, render_prompt,
                                    render_certificate, allocation_schedule, PERMS)
from src.relation_verifier import parse_prompt, solve, simple_paths, check_certificate, orbit_key


class RelationTransportTest(unittest.TestCase):
    def test_all_permutations_and_independent_direction_checks(self):
        for p in PERMS:
            self.assertEqual(compose(p, inverse(p)), tuple(range(5)))
            for x in range(5):
                q = {'source': 100, 'target': 101, 'state': x,
                     'edges': [{'id': 200, 'u': 100, 'v': 101, 'table': p}]}
                prompt = render_prompt(q)
                self.assertEqual(solve(parse_prompt(prompt)), [p[x]])
                self.assertTrue(check_certificate(prompt, render_certificate(q, [200]))['valid'])
                q['source'], q['target'], q['state'] = 101, 100, p[x]
                self.assertEqual(solve(parse_prompt(render_prompt(q))), [x])
                self.assertTrue(check_certificate(render_prompt(q), render_certificate(q, [200]))['valid'])

    def test_no_overwrite_or_dataset_needed_for_fixture_determinism(self):
        a = make_world(70001, 0, split='fixture')
        self.assertEqual(a, make_world(70001, 0, split='fixture'))
        self.assertNotEqual(a['question'], make_world(70001, 1, split='fixture')['question'])

    def test_support_views_and_removed_evidence(self):
        for i in range(12):
            w = make_world(70002, i, split='fixture')
            for name, (q, answer) in views(w).items():
                prompt = render_prompt(q); parsed = parse_prompt(prompt)
                self.assertEqual(solve(parsed), [answer])
                paths = simple_paths(parsed)
                self.assertEqual(len(paths), 1 if name == 'useful_delete' else 4)
                self.assertEqual({len(p) for p in paths}, {4})
                if name in ('source_change', 'target_change'):
                    self.assertNotEqual(answer, w['answer'])
                if name == 'useful_delete':
                    checked = [check_certificate(prompt, r) for r in w['responses']]
                    self.assertEqual(sum(r['valid'] for r in checked), 1)
                    self.assertEqual(sum(r['reason']=='absent_edge' for r in checked), 3)

    def test_strict_proof_rejects_wrong_steps_endpoints_and_extra_text(self):
        w = make_world(70003, 0, split='fixture'); good = w['responses'][0]
        self.assertTrue(check_certificate(w['prompt'], good)['valid'])
        self.assertFalse(check_certificate(w['prompt'], good+'\nExtra')['valid'])
        self.assertFalse(check_certificate(w['prompt'], '\n'.join(good.splitlines()[1:]))['valid'])
        wrong = good.rsplit(' ', 1)[0] + ' ' + str((w['answer']+1)%5)
        self.assertFalse(check_certificate(w['prompt'], wrong)['valid'])
        state_wrong = good.splitlines(); state_wrong[0] = state_wrong[0][:-1]+str((int(state_wrong[0][-1])+1)%5)
        self.assertFalse(check_certificate(w['prompt'], '\n'.join(state_wrong))['valid'])

    def test_solver_disconnected_and_inconsistent_negatives(self):
        w = make_world(70004, 0, split='fixture'); q = deepcopy(w['question'])
        remove = {p[1] for p in w['task_paths']}
        q['edges'] = [e for e in q['edges'] if e['id'] not in remove]
        self.assertEqual(solve(parse_prompt(render_prompt(q))), [])
        q = deepcopy(w['question'])
        e = next(e for e in q['edges'] if e['id'] == w['task_paths'][0][-1])
        e['table'] = [(x+1)%5 for x in e['table']]
        self.assertGreater(len(solve(parse_prompt(render_prompt(q)))), 1)
        self.assertFalse(check_certificate(render_prompt(q), w['responses'][1])['valid'])
        e['table'] = [0]*5
        with self.assertRaises(ValueError): parse_prompt(render_prompt(q))

    def test_orbits_global_labels_inverse_notation_and_counterfactuals(self):
        w = make_world(70005, 0, split='fixture'); base = orbit_key(parse_prompt(w['prompt']))
        for name, (q, _) in views(w).items():
            if 'delete' not in name:
                self.assertEqual(base, orbit_key(parse_prompt(render_prompt(q))))
        q = deepcopy(w['question']); g = (2, 4, 1, 0, 3)
        for e in q['edges']:
            e['u'], e['v'] = 233-e['u'], 233-e['v']
            e['id'] = 431-e['id']
            tab = [0]*5
            for a,b in enumerate(e['table']): tab[g[a]]=g[b]
            e['table'] = tuple(tab)
            e['u'], e['v'] = e['v'], e['u']
            e['table'] = tuple(e['table'].index(a) for a in range(5))
        q['source'], q['target'], q['state'] = 233-q['source'], 233-q['target'], g[q['state']]
        q['edges'].reverse()
        self.assertEqual(base, orbit_key(parse_prompt(render_prompt(q))))
        self.assertEqual(solve(parse_prompt(render_prompt(q))), [g[w['answer']]])
        different = make_world(70005, 1, split='fixture')
        self.assertNotEqual(base['canonical_hex'], orbit_key(parse_prompt(different['prompt']))['canonical_hex'])

    def test_complete_latin_schedule(self):
        ids = [f'q{i}' for i in range(12)]
        s = allocation_schedule(ids, 70006, cycles=2)
        seen = {w: [[], []] for w in ids}
        for u in s['updates']:
            self.assertEqual(sorted(u['multi']), list(range(4)))
            self.assertEqual(sorted(u['repeat']), list(range(4)))
            for w,m,r in zip(u['world_ids'],u['multi'],u['repeat']):
                seen[w][0].append(m); seen[w][1].append(r)
        for multi,repeat in seen.values():
            self.assertEqual(sorted(multi), [0,0,1,1,2,2,3,3])
            self.assertEqual(len(set(repeat)),1)
        with self.assertRaises(ValueError): allocation_schedule(ids[:-1], 1)


if __name__ == '__main__': unittest.main()
