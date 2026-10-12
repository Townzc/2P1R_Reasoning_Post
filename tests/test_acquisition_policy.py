import unittest
from experiments.sft_allocation_acquisition.policy_contract import Policy


def finish(p, batch, values):
    proposal = p.propose()
    p.begin(batch, proposal)
    p.complete(batch, [dict(**r, usable=x) for r, x in zip(proposal['items'], values)])


class PolicyTests(unittest.TestCase):
    def test_breadth_retires_success_but_keeps_failed_parent(self):
        p = Policy([str(i) for i in range(40)], 1)
        finish(p, 'a', [True]+[False]*15)
        q = p.propose()
        self.assertEqual(q['new_problem_ids'], ['16'])
        self.assertEqual(q['items'][0], dict(problem_id='1', attempt=2))
        self.assertEqual(q['items'][-1], dict(problem_id='16', attempt=1))

    def test_depth_waits_for_four_usable_answers(self):
        p = Policy(['a'], 4)
        for i in range(3): finish(p, str(i), [True])
        self.assertEqual(p.active, ['a'])
        finish(p, '3', [True])
        self.assertEqual(p.active, [])
        self.assertEqual(p.summary()['attempted_candidates'], 4)

    def test_failures_and_unknowns_are_capped_and_never_dropped(self):
        p = Policy(['a'], 4)
        for i in range(8): finish(p, str(i), [None if i == 3 else False])
        self.assertEqual(p.active, [])
        self.assertEqual(p.summary()['unknown'], 1)
        self.assertEqual(p.summary()['zero_usable_parents'], 1)
        self.assertEqual(p.summary()['attempted_candidates'], 8)
        self.assertEqual(p.propose()['items'], [])

    def test_pending_or_lost_return_never_allows_replay(self):
        p = Policy(['a'], 1)
        p.begin('a', p.propose())
        with self.assertRaises(ValueError): p.propose()
        with self.assertRaises(ValueError): p.complete('a', [])
        self.assertTrue(p.summary()['unresolved_batch'])

    def test_wallet_limited_purchase_preserves_frozen_order(self):
        p = Policy([str(i) for i in range(50)], 1)
        q = p.propose(3)
        p.begin('a', q)
        p.complete('a', [dict(**r, usable=True) for r in q['items']])
        self.assertEqual(p.propose(2)['new_problem_ids'], ['3', '4'])
        self.assertEqual(p.summary()['acquired_problems'], 3)

    def test_no_duplicate_pool_or_changed_roster(self):
        with self.assertRaises(ValueError): Policy(['a', 'a'], 1)
        p = Policy(['a', 'b'], 1)
        q = p.propose()
        q['items'].reverse()
        with self.assertRaises(ValueError): p.begin('a', q)


if __name__ == '__main__': unittest.main()
