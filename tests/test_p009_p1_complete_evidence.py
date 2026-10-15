"""Synthetic saved-proof tests only: no math-verify, model, cloud or real rows."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts import p009_p1_complete_evidence as evidence


class SavedJournalFixture(unittest.TestCase):
    def setUp(self):
        Path('.local').mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir='.local')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.rows = [dict(id=f'row{i}', dataset='math_procurement', gold='2',
                         answer_segment='synthetic', stop_reason='native_eos') for i in range(102)]
        self.binding = {'synthetic':True}
        self.basis = dict(ordered_rows_sha256=evidence.digest(self.rows), row_count=102,
                          binding=self.binding)
        evidence.create(self.root/'journal/BASIS.json', self.basis)
        self.timing = dict(basis_sha256=evidence.digest(self.basis), local_report_path='PRIVATE/report.md')
        self.pairs = []
        self.scored = []
        for index, answer in enumerate(('2', '3')):
            pair = ['2', answer]
            key = hashlib.sha256(json.dumps(pair, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
            obs = dict(pair_id=key, attempt_index=index, elapsed_seconds=.01,
                       symbolic=dict(status='compared', equivalent=index == 0))
            record = dict(pair=pair, observation=obs)
            self.pairs.append(record)
            evidence.create(self.root/'journal/pairs'/f'{key}.json', record)
        for index, original in enumerate(self.rows):
            pair = self.pairs[int(index == 101)]
            obs = pair['observation']
            self.scored.append(dict(id=original['id'], pair_id=obs['pair_id'], symbolic_attempt=obs,
                score=dict(correct=index != 101, parsed=True, fallback_used=False,
                    teacher_label_eligible=True, reasoning_validated=False, status='compared',
                    extracted_answer=pair['pair'][1], symbolic=obs['symbolic'])))
        for i, (start, end) in enumerate(((0, 100), (100, 102))):
            folder = self.root/'journal/chunks'/f'{i:05d}'
            record = self.pairs[i]
            key = record['observation']['pair_id']
            intent = dict(start=start, end=end, rows_sha256=evidence.digest(self.rows[start:end]),
                row_ids=[r['id'] for r in self.rows[start:end]], automatic_retry=False,
                timing_review=None if i == 0 else self.timing,
                new_pair_intents={key:record['pair']})
            result = dict(rows=self.scored[start:end], new_symbolic_attempts=1,
                          unique_pairs_in_session=i+1, rows_in_session=end)
            evidence.create(folder/'INTENT.json', intent)
            evidence.create(folder/'RESULT.json', result)
            evidence.create(folder/'COMPLETED.json', dict(intent_sha256=evidence.file_sha(folder/'INTENT.json'),
                result_sha256=evidence.file_sha(folder/'RESULT.json'), confirmed_rows=end-start, technical_unknown=0))
            evidence.create(folder/'TIMING.json', dict(elapsed_through_completed_proof_seconds=.1,
                                                    final_timing_record_write_excluded=True))
        evidence.create(self.root/'ALL_SCORED_ROWS.json', self.scored)

    def check(self):
        return evidence.verify_journal(self.root, self.rows, self.binding, self.timing)

    def rewrite(self, rel, value):
        (self.root/rel).write_bytes(evidence.canonical(value)+b'\n')

    def test_complete_saved_chain_with_cache_hit(self):
        rows, pairs, chunks = self.check()
        self.assertEqual((len(rows), len(pairs), chunks), (102, 2, 2))

    def test_partial_chunk_is_not_complete(self):
        (self.root/'journal/chunks/00001/COMPLETED.json').unlink()
        with self.assertRaises(ValueError): self.check()

    def test_failed_chunk_cannot_hide_behind_completed(self):
        evidence.create(self.root/'journal/chunks/00001/FAILED.json', {'unconfirmed':True})
        with self.assertRaises(ValueError): self.check()

    def test_original_prefix_input_change_rejected(self):
        self.rows[0]['gold'] = 'changed'
        with self.assertRaises(ValueError): self.check()

    def test_duplicate_symbolic_attempt_index_rejected(self):
        p = copy.deepcopy(self.pairs[1]); p['observation']['attempt_index'] = 0
        self.rewrite('journal/pairs/'+p['observation']['pair_id']+'.json', p)
        with self.assertRaises(ValueError): self.check()

    def test_integer_label_is_not_boolean(self):
        rel = 'journal/chunks/00001/'
        result = evidence.read(self.root/(rel+'RESULT.json'))
        result['rows'][1]['score']['correct'] = 0
        self.rewrite(rel+'RESULT.json', result)
        proof = evidence.read(self.root/(rel+'COMPLETED.json'))
        proof['result_sha256'] = evidence.file_sha(self.root/(rel+'RESULT.json'))
        self.rewrite(rel+'COMPLETED.json', proof)
        with self.assertRaises(ValueError): self.check()

    def test_saved_final_rows_must_equal_all_chunks(self):
        self.rewrite('ALL_SCORED_ROWS.json', self.scored[:-1])
        with self.assertRaises(ValueError): self.check()

    def test_numeric_review_change_rejected(self):
        changed = dict(self.timing, local_report_path='another.md')
        with self.assertRaises(ValueError):
            evidence.verify_journal(self.root, self.rows, self.binding, changed)

    def test_projection_removes_only_host_locator_without_mutating_original(self):
        intent = dict(timing_review=dict(self.timing, report_sha256='a'*64), start=100)
        original = copy.deepcopy(intent)
        result = evidence.project_intent(intent, self.timing)
        self.assertEqual(intent, original)
        self.assertEqual(result, dict(timing_review=dict(basis_sha256=self.timing['basis_sha256'],
                                                       report_sha256='a'*64), start=100))
        with self.assertRaises(ValueError):
            evidence.project_intent(intent, dict(local_report_path='different.md'))


if __name__ == '__main__':
    unittest.main()
