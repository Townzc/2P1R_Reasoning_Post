"""New local-only IO/schema fixtures. No production invocation or real CR acceptance."""
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts import prepare_p011_long_inputs as builder


class DataIO(unittest.TestCase):
    def test_pinned_file_rejects_changed_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'raw.jsonl'
            p.write_text('[]\n')
            item = {'local_path': str(p), 'bytes': p.stat().st_size,
                    'sha256': builder.sha(p)}
            self.assertEqual(builder.checked_file(item), p)
            p.write_text('{}\n')
            with self.assertRaises(ValueError):
                builder.checked_file(item)

    def test_ingestion_preserves_source_rows_and_reports_author_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'math.jsonl'
            rows = []
            for category, score in [('math', 1), ('code', 1), ('math', 0.5)]:
                rows.append({'system': 'unused source system', 'conversations': [
                    {'from': 'human', 'value': 'question', 'info': {'category': category}},
                    {'from': 'assistant', 'value': '\\boxed{2}', 'info': {'verify_score': score}}]})
            p.write_text(''.join(json.dumps(x) + '\n' for x in rows))
            db = sqlite3.connect(':memory:')
            db.execute('CREATE TABLE rows(dataset,parent,source_file,row_index,question,response,metadata)')
            spec = {'files': [{'source_file': 'math.jsonl', 'local_path': str(p),
                              'sha256': builder.sha(p), 'bytes': p.stat().st_size}]}
            stats = builder.ingest(db, 'am_thinking', spec, io.StringIO())
            self.assertEqual(stats, {'raw_rows': 3, 'math_rows': 2, 'non_math_rows': 1,
                                    'author_verification_missing_or_below_0_9': 1})
            self.assertEqual([r['source_row'] for r in builder.grouped_rows(
                db, 'am_thinking', 'question')], [0, 2])
            db.close()

    def test_create_only_writer_does_not_replace_partial_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'record.json'
            builder.dump(p, {'first': True})
            with self.assertRaises(FileExistsError):
                builder.dump(p, {'second': True})
            self.assertEqual(json.loads(p.read_text()), {'first': True})

    def test_incorrect_review_scope_rejected_before_output_creation(self):
        from experiments.p011.data_contract import PLAN_SHA256
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            lock = base / 'lock.json'
            review = base / 'synthetic_review.json'
            builder.dump(lock, {'plan_sha256': PLAN_SHA256})
            builder.dump(review, {'scope': 'wrong'})
            with self.assertRaises(ValueError):
                builder.admit_code(review, lock)
            self.assertEqual(sorted(p.name for p in base.iterdir()), ['lock.json', 'synthetic_review.json'])


if __name__ == '__main__':
    unittest.main()
