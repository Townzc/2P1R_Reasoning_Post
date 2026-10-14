"""New orchestration fixtures; no old scorer suite or real-output pass is rerun."""
import os
import time
import unittest
from unittest.mock import patch

from experiments.learning_regime_p009 import math_scoring_pool as pool


def fake_worker(conn):
    conn.send({'ready': True, 'versions': pool.VERSIONS})
    try:
        while True:
            task = conn.recv()
            if task is None:
                return
            key, gold, answer = task
            if gold == 'hang':
                time.sleep(5)
            if gold == 'die':
                os._exit(9)
            if gold == 'slow':
                time.sleep(.05)
            result = {'status': 'compared', 'equivalent': gold == answer}
            if gold == 'fallback':
                result = {'status': 'parse_failure', 'equivalent': None}
            if gold == 'valid_false':
                result = {'status': 'compared', 'equivalent': False}
            conn.send({'pair_id': key, 'result': result})
    except (EOFError, BrokenPipeError):
        pass


def wrong_environment(conn):
    conn.send({'ready': False, 'versions': {}})
    conn.close()


def row(i, gold='1', answer='1', stop='native_eos'):
    return {'id': str(i), 'gold': gold, 'answer_segment': '\\boxed{' + answer + '}',
            'stop_reason': stop}


class PoolTests(unittest.TestCase):
    def test_exact_pairs_reused_across_calls_without_losing_rows(self):
        with patch.object(pool, '_worker_main', fake_worker), pool.SymbolicPool() as p:
            a = p.score_rows([row(1), row(2), row(3, answer=' 1 ')])
            b = p.score_rows([row(4)])
            self.assertEqual(a['new_symbolic_attempts'], 1)
            self.assertEqual(len(a['rows']), 3)
            self.assertEqual(b['new_symbolic_attempts'], 0)
            self.assertEqual(b['rows_in_session'], 4)
            self.assertEqual(a['rows'][0]['pair_id'], b['rows'][0]['pair_id'])

    def test_stop_rule_per_row_and_no_workers_for_caps_or_unboxed(self):
        with pool.SymbolicPool() as p:
            rows = [row(1, stop='length_cap'), row(2)]
            rows[1]['answer_segment'] = 'unboxed 1'
            result = p.score_rows(rows)
            self.assertEqual(result['new_symbolic_attempts'], 0)
            self.assertEqual(result['startup_observations'], [])
            self.assertFalse(any(r['score']['correct'] for r in result['rows']))

    def test_timeout_is_cached_not_retried_and_next_unique_pair_runs(self):
        with patch.object(pool, '_worker_main', fake_worker), patch.object(pool, 'TASK_SECONDS', .2):
            with pool.SymbolicPool() as p:
                a = p.score_rows([row(1, gold='hang'), row(2, gold='hang'), row(3)])
                b = p.score_rows([row(4, gold='hang'), row(5, gold='2', answer='2')])
                self.assertEqual(a['new_symbolic_attempts'], 2)
                self.assertEqual(b['new_symbolic_attempts'], 1)
                self.assertEqual(a['rows'][0]['score']['status'], 'outer_timeout')
                self.assertEqual(b['rows'][0]['symbolic_attempt'], a['rows'][0]['symbolic_attempt'])
                self.assertTrue(b['rows'][1]['score']['correct'])

    def test_worker_eof_kept_and_order_preserved(self):
        with patch.object(pool, '_worker_main', fake_worker), pool.SymbolicPool() as p:
            result = p.score_rows([row(1, gold='slow'), row(2, gold='die'), row(3)])
            self.assertEqual([r['id'] for r in result['rows']], ['1', '2', '3'])
            self.assertEqual(result['rows'][1]['score']['status'], 'tool_error')
            self.assertEqual(result['new_symbolic_attempts'], 3)

    def test_bad_environment_is_technical_abort(self):
        with patch.object(pool, '_worker_main', wrong_environment), pool.SymbolicPool() as p:
            with self.assertRaises(RuntimeError):
                p.score_rows([row(1)])
            self.assertTrue(p.closed)
            self.assertEqual(len(p.attempts), 0)

    def test_valid_false_not_overridden_and_fallback_eligibility_retained(self):
        with patch.object(pool, '_worker_main', fake_worker), pool.SymbolicPool() as p:
            result = p.score_rows([row(1, 'valid_false', 'valid_false'),
                                   row(2, 'fallback', 'fallback'), row(3, 'fallback', 'other')])
            scores = [r['score'] for r in result['rows']]
            self.assertFalse(scores[0]['correct'])
            self.assertFalse(scores[0]['fallback_used'])
            self.assertTrue(scores[1]['teacher_label_eligible'])
            self.assertFalse(scores[2]['teacher_label_eligible'])

    def test_unknown_and_duplicate_identity_fail_before_work(self):
        with pool.SymbolicPool() as p:
            with self.assertRaises(ValueError):
                p.score_rows([row(1), row(1)])
            with self.assertRaises(ValueError):
                p.score_rows([row(2, stop='unknown')])
            with self.assertRaises(ValueError):
                p.score_rows([row(3, gold='')])
            self.assertEqual(p.startups, [])

    def test_real_persistent_symbolic_workers_and_dependency_versions(self):
        with pool.SymbolicPool() as p:
            result = p.score_rows([row(1, r'\frac{1}{2}', '0.5'),
                                   row(2, '2', '3'), row(3, 'x+1', '1+x')])
            self.assertEqual([r['score']['correct'] for r in result['rows']], [True, False, True])
            self.assertLessEqual(len(result['startup_observations']), 2)
            self.assertTrue(all(r['versions'] == pool.VERSIONS for r in result['startup_observations']))
        self.assertTrue(p.closed)
        self.assertEqual(p.workers, [])


if __name__ == '__main__':
    unittest.main()
