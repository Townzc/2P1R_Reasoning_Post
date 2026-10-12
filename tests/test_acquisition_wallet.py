import unittest
from experiments.sft_allocation_acquisition.wallet import Wallet, cost_ns, NS_PER_HOUR


class WalletTests(unittest.TestCase):
    def test_fractional_clock_cost_rounds_up(self):
        self.assertEqual(cost_ns(1, 1), 1)
        self.assertEqual(cost_ns(NS_PER_HOUR + 1, 1), 2)

    def test_problem_purchase_and_idle_are_both_charged(self):
        w = Wallet(100, 10, 20, 0)
        a = w.admit('a', ['p'], NS_PER_HOUR, NS_PER_HOUR)
        self.assertEqual(a['previously_spent_nanodollars'], 10)
        self.assertEqual(w.settle('a', 2*NS_PER_HOUR)['cumulative_spent_nanodollars'], 40)
        self.assertEqual(w.spent(3*NS_PER_HOUR), 50)

    def test_rejected_action_does_not_buy_problems(self):
        w = Wallet(30, 10, 25, 0)
        self.assertIsNone(w.admit('a', ['p'], 0, NS_PER_HOUR))
        self.assertEqual(w.acquired, set())
        self.assertEqual(w.attempted_batches, set())

    def test_equality_is_admitted_without_overspending(self):
        w = Wallet(30, 10, 20, 0)
        self.assertIsNotNone(w.admit('a', ['p'], 0, NS_PER_HOUR))
        self.assertEqual(w.settle('a', NS_PER_HOUR)['remaining_nanodollars'], 0)

    def test_ambiguous_batch_cannot_be_replayed_or_replaced(self):
        w = Wallet(100, 10, 0, 0)
        w.admit('a', ['p'], 0, NS_PER_HOUR)
        with self.assertRaises(ValueError): w.admit('b', [], 0, NS_PER_HOUR)
        with self.assertRaises(ValueError): w.settle('b', 1)
        self.assertEqual(w.pending['batch_id'], 'a')

    def test_overrun_preserves_unresolved_intent(self):
        w = Wallet(10, 10, 0, 0)
        w.admit('a', ['p'], 0, NS_PER_HOUR)
        with self.assertRaises(ValueError): w.settle('a', NS_PER_HOUR + 1)
        self.assertIsNotNone(w.pending)
        self.assertEqual(w.spent(NS_PER_HOUR + 1), 11)

    def test_completed_batch_and_problem_cannot_be_charged_twice(self):
        w = Wallet(100, 10, 20, 0)
        w.admit('a', ['p'], 0, NS_PER_HOUR)
        w.settle('a', 1)
        with self.assertRaises(ValueError): w.admit('a', [], 1, NS_PER_HOUR)
        with self.assertRaises(ValueError): w.admit('b', ['p'], 1, NS_PER_HOUR)

    def test_backward_clock_and_noninteger_money_fail(self):
        w = Wallet(100, 10, 0, 5)
        with self.assertRaises(ValueError): w.spent(4)
        with self.assertRaises(ValueError): Wallet(100.0, 10, 0, 5)
        with self.assertRaises(ValueError): Wallet(True, 10, 0, 5)


if __name__ == '__main__': unittest.main()
