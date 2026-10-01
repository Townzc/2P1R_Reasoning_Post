"""Authored in-memory scorer replies only; no program/model execution."""
import argparse
import json
from pathlib import Path
import tempfile
import time
import unittest

from experiments.q2_supervision_migration import screen_runtime as sr
from experiments.q2_supervision_migration.contracts import reserve_batch, read_records
from experiments.q2_supervision_migration.gpu_profile import ProfileError


def reply(base='pass', extra='pass'):
    return {'base': {'status': base, 'detail': 'authored base'},
            'extra': {'status': extra, 'detail': 'authored extra'}}


class FakeConnection:
    def __init__(self, replies, *, ready=True, recv_error=None):
        self.replies = list(replies)
        self.ready = ready
        self.recv_error = recv_error
        self.sent = []
        self.poll_calls = 0
        self.recv_calls = 0
        self.closed = False

    def send(self, value):
        if self.closed:
            raise AssertionError('request sent on a failed channel')
        self.sent.append(value)

    def poll(self, timeout):
        if self.closed:
            raise AssertionError('failed channel polled again')
        self.poll_calls += 1
        return self.ready

    def recv(self):
        if self.closed:
            raise AssertionError('failed channel consumed a late reply')
        self.recv_calls += 1
        if self.recv_error:
            raise self.recv_error
        return self.replies.pop(0)

    def close(self):
        self.closed = True


class BatchScoringTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.batch = reserve_batch(self.root / 'batches', run_id='authored', phase_id='R_future',
            batch_index=0, tasks=['authored/1', 'authored/2'],
            policy_sha256='a' * 64, config_sha256='b' * 64)
        self.args = argparse.Namespace(worker_deadline_epoch=time.time()+60)

    def score(self, conn, *, allow_unresolved=False):
        return sr.score_batch(self.args, self.batch, ['authored first', 'authored second'],
            [[1], [2]], ['authored/1', 'authored/2'], conn, 'union', ['eos', 'eos'],
            allow_unresolved=allow_unresolved)

    def samples(self):
        return read_records(self.batch.directory / 'batch.jsonl')[1:]

    def test_training_unknown_inspects_later_saved_samples_then_forbids_update(self):
        conn = FakeConnection([reply(extra='timeout'), reply()])
        with self.assertRaisesRegex(ProfileError, 'complete batch inspection'):
            self.score(conn)
        self.assertEqual(len(conn.sent), 2)
        self.assertEqual(conn.recv_calls, 2)
        self.assertFalse(conn.closed)
        first, second = self.samples()
        self.assertEqual(first['extra']['status'], 'timeout')
        self.assertEqual(second['base']['status'], 'pass')
        self.assertEqual(second['extra']['status'], 'pass')

    def test_unknown_evaluation_returns_none_without_dropping_later_sample(self):
        conn = FakeConnection([reply(extra='scorer_error'), reply()])
        self.assertEqual(self.score(conn, allow_unresolved=True), [None, 1.0])
        self.assertEqual(len(conn.sent), 2)
        self.assertEqual(self.samples()[0]['extra']['status'], 'scorer_error')

    def test_outer_timeout_closes_channel_without_sending_or_reading_later_work(self):
        conn = FakeConnection([reply(), reply()], ready=False)
        with self.assertRaises(TimeoutError):
            self.score(conn, allow_unresolved=True)
        self.assertEqual(len(conn.sent), 1)
        self.assertEqual(conn.poll_calls, 1)
        self.assertEqual(conn.recv_calls, 0)
        self.assertTrue(conn.closed)
        self.assertEqual(len(conn.replies), 2)  # Late response remains unread.
        first, second = self.samples()
        self.assertEqual(first['base']['status'], 'timeout')
        self.assertEqual(second['base']['status'], 'missing')
        self.assertEqual(second['extra']['status'], 'missing')

    def test_known_failure_is_used_once_without_retry(self):
        conn = FakeConnection([reply(base='fail'), reply()])
        self.assertEqual(self.score(conn), [0.0, 1.0])
        self.assertEqual(conn.recv_calls, 2)
        self.assertEqual(conn.sent, [('authored/1', 'authored first'),
                                     ('authored/2', 'authored second')])

    def test_request_and_unmodified_raw_reply_are_saved_and_bound_per_sample(self):
        values = [reply(extra='timeout'), reply(base='fail')]
        conn = FakeConnection(values)
        self.assertEqual(self.score(conn, allow_unresolved=True), [None, 0.0])
        request_ids = []
        for i in range(2):
            request = json.loads((self.batch.directory / f'scoring_request_{i:08d}.json').read_text())
            recorded = json.loads((self.batch.directory / f'scoring_reply_{i:08d}.json').read_text())
            self.assertEqual(request['intent_sha256'], self.batch.intent_sha256)
            self.assertEqual(request['sample_index'], i)
            self.assertEqual(recorded['request_id'], request['request_id'])
            self.assertEqual(recorded['raw_reply'], values[i])
            self.assertFalse(recorded['scorer_request_identity_echoed'])
            request_ids.append(request['request_id'])
        self.assertNotEqual(*request_ids)

    def test_malformed_reply_is_preserved_then_channel_is_closed(self):
        malformed = {'base': {'status': 'pass'}}
        conn = FakeConnection([malformed, reply()])
        with self.assertRaisesRegex(ProfileError, 'channel failed'):
            self.score(conn)
        self.assertTrue(conn.closed)
        self.assertEqual(conn.recv_calls, 1)
        recorded = json.loads((self.batch.directory / 'scoring_reply_00000000.json').read_text())
        self.assertEqual(recorded['raw_reply'], malformed)
        self.assertEqual(self.samples()[1]['extra']['status'], 'missing')

    def test_fatal_reply_is_journaled_before_receive_raises(self):
        conn = FakeConnection([{'fatal': 'authored process failure'}, reply()])
        with self.assertRaisesRegex(ProfileError, 'channel failed'):
            self.score(conn)
        recorded = json.loads((self.batch.directory / 'scoring_reply_00000000.json').read_text())
        self.assertEqual(recorded['raw_reply'], {'fatal': 'authored process failure'})
        self.assertEqual(conn.recv_calls, 1)
        self.assertEqual(len(conn.sent), 1)
        self.assertTrue(conn.closed)

    def test_keyboard_interrupt_remains_a_hard_stop(self):
        conn = FakeConnection([], recv_error=KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):
            self.score(conn)
        self.assertEqual(len(conn.sent), 1)
        self.assertEqual(conn.recv_calls, 1)
        self.assertTrue(conn.closed)
        self.assertEqual(self.samples()[1]['base']['status'], 'missing')

    def test_expired_deadline_sends_no_request(self):
        self.args.worker_deadline_epoch = time.time()-1
        conn = FakeConnection([reply(), reply()])
        with self.assertRaisesRegex(TimeoutError, 'deadline'):
            self.score(conn)
        self.assertEqual(conn.sent, [])
        self.assertEqual(conn.recv_calls, 0)
        self.assertTrue(conn.closed)
        self.assertEqual(len(self.samples()), 2)


if __name__ == '__main__':
    unittest.main()
