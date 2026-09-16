from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments.thursday_probe.arithmetic_eval import score
from experiments.thursday_probe_v2 import resume_analyze as analyzer
from experiments.thursday_probe_v2.config import DATA, RELEASE
from experiments.thursday_probe_v2.resume_diagnostics import RESUME_RELEASE
from experiments.thursday_probe_v2.resumable_generation import _descriptor, _digest
from src.sft_data import read_jsonl, sha256_file


def write(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record))


def rows_file(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r)+'\n' for r in rows))


def prediction(pid, sample, correct, category='target', task='construct'):
    return dict(problem_id=pid, sample_index=sample, category=category, task=task,
                generated_ids=[1, 0], score=dict(correct=correct, parsed=True,
                completed=True, failure='none' if correct else 'wrong_answer_or_resources'),
                stop={'stop_reason': 'native_eos'}, independent_trace_status='unverifiable',
                reference_program_class='unknown')


class CoreAnalysisTests(unittest.TestCase):
    def fixture(self):
        problems = [dict(problem_id='q'+str(i), paths={'B': {'structure_id': 'family'+str(i)}})
                    for i in range(2)]
        completed = {}
        values = {'C-S': False, 'C-P': True, 'B-S': False, 'B-P': False}
        for state, correct in values.items():
            for view, samples in (('discovery_sampled', 4), ('discovery_greedy', 1)):
                completed[state+'_'+view] = [prediction(p['problem_id'], s, correct)
                    for p in problems for s in range(samples)]
        return problems, completed

    def test_paired_interaction_sign_and_exact_constant_interval(self):
        problems, completed = self.fixture()
        result = analyzer.core_results(completed, problems, {'full': ['q0', 'q1']})
        for row in result['results']:
            self.assertEqual(row['contrasts']['delta_C']['mean'], 1)
            self.assertEqual(row['contrasts']['delta_B']['mean'], 0)
            self.assertEqual(row['contrasts']['interaction']['mean'], -1)
            self.assertEqual(row['contrasts']['interaction']['question_ci'], [-1, -1])
            self.assertEqual(row['contrasts']['interaction']['cluster_ci'], [-1, -1])
        self.assertEqual(result['seed'], 2026091604)

    def test_missing_cell_is_na_and_duplicate_sample_shape_rejected(self):
        problems, completed = self.fixture()
        del completed['B-P_discovery_sampled']
        result = analyzer.core_results(completed, problems, {'full': ['q0', 'q1']})
        self.assertIsNone(result['results'][0]['contrasts'])
        self.assertIsNone(result['results'][0]['cells']['B-P']['estimate'])
        self.assertEqual(result['results'][2]['status'], 'complete')
        completed['C-P_discovery_sampled'].pop()
        with self.assertRaisesRegex(ValueError, 'exact complete'):
            analyzer.core_results(completed, problems, {'full': ['q0', 'q1']})

    def test_probe_D_and_denominators_use_questions_not_independent_draws(self):
        completed = {}
        for state in ('C0', 'C', 'B'):
            completed[state+'_probes'] = [prediction(category+str(i), sample,
                state == 'B' and category == 'target', category=category, task='compute')
                for category in ('atomic', 'target', 'control') for i in range(2) for sample in range(4)]
        result = analyzer.probe_results(completed)
        self.assertEqual(result['manipulation_contrast']['D'], 1)
        self.assertEqual(result['manipulation_contrast']['D_stratified_paired_question_ci'], [1, 1])
        for row in result['table']:
            self.assertEqual(row['metrics']['questions'], 2)
            self.assertEqual(row['metrics']['generations'], 8)
            self.assertEqual(row['metrics']['samples_per_question'], 4)

    def test_parsing_is_not_teacher_free_resource_verified_correctness(self):
        row = dict(problem_id='q', task='construct', numbers=[8, 25, 19, 21], target=42)
        text = ('Step 1: 25 - 19 = 6.\nStep 2: 8 * 6 = 48.\n'
                'Step 3: 48 - 21 = 27.\nAnswer: (8 * (25 - 19)) - 21')
        stop = dict(answer_segment=text, stop_reason='native_eos')
        record = dict(problem_id='q', sample_index=0, forced_prefix='', generated_ids=[1, 0],
                      stop=stop, score=score(row, stop))
        event = dict(name='C-S_train_diagnostic', state='C-S', view='train_diagnostic')
        result = analyzer.construction_errors([record], [row], event)[0]
        self.assertTrue(result['parsed'])
        self.assertTrue(result['uses_input_multiset'])
        self.assertTrue(result['intermediate_arithmetic_consistent'])
        self.assertFalse(result['teacher_free_resource_verified_correct'])
        self.assertFalse(result['primary_correct'])


class ArtifactAuditTests(unittest.TestCase):
    def test_reference_nll_preserves_measured_runtime_and_unknown_timing(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            metric = dict(reference_count=16, supervised_tokens=160,
                          response_loss_sum=40.0, nll=0.25)
            write(run/'C-S_train_reference_A.json', dict(metric, forward_seconds=1.75))
            write(run/'C-S_train_reference_B.json', metric)
            result = analyzer._reference_nll(run)
            by = {(r['state'], r['family']): r for r in result['results']}
            measured = by['C-S', 'A']
            self.assertEqual(measured['separately_measured_runtime_seconds'], 1.75)
            self.assertEqual(measured['metrics']['nll'], 0.25)
            self.assertEqual(measured['additional_autoregressive_generations'], 0)
            self.assertEqual(measured['artifact_sha256'], sha256_file(run/'C-S_train_reference_A.json'))
            self.assertEqual(by['C-S', 'B']['status'], 'measured')
            self.assertIsNone(by['C-S', 'B']['separately_measured_runtime_seconds'])
            self.assertEqual(by['B-P', 'B']['status'], 'not_measured')
            self.assertIsNone(by['B-P', 'B']['metrics'])
            self.assertIsNone(by['B-P', 'B']['separately_measured_runtime_seconds'])

    def test_reference_nll_rejects_invalid_timing_without_changing_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            metric = dict(reference_count=16, supervised_tokens=160,
                          response_loss_sum=40.0, nll=0.25)
            path = run/'C-S_train_reference_A.json'
            for invalid in (-1, float('inf'), float('nan'), True, '1.75'):
                with self.subTest(forward_seconds=invalid):
                    write(path, dict(metric, forward_seconds=invalid))
                    with self.assertRaisesRegex(ValueError, 'forward_seconds'):
                        analyzer._reference_nll(run)
            write(path, dict(metric, nll=0.5, forward_seconds=1.75))
            with self.assertRaisesRegex(ValueError, 'normalization'):
                analyzer._reference_nll(run)

    def test_partial_summary_and_derived_views_may_lag_exact_immutable_prefixes(self):
        # Use already-published real token records, with fixture-only commit IDs;
        # no generation/tokenizer model call is needed for this crash boundary.
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)/'run'; run.mkdir(); historical = analyzer.HISTORICAL
            inputs, _, _, _, _ = analyzer.load_inputs(); rows = inputs['probes']
            event = next(e for e in analyzer.evaluation_queue() if e['name'] == 'C_probes')
            records = read_jsonl(historical/'C0_probes.jsonl')[:16]
            raw_batches = read_jsonl(historical/'C0_probes.raw_batches.jsonl')[:2]
            protocol = {'fixture_protocol': True}
            descriptor = _descriptor(rows, event, {'model_hash': 'a'*64,
                'split_hash': sha256_file(DATA/'probes.jsonl')}, protocol)
            path = run/'C_probes.jsonl'; folder = path.with_suffix('.resume')
            write(folder/'manifest.json', dict(descriptor=descriptor, initial_rng={'state': 0}))
            events = []
            for index, raw in enumerate(raw_batches):
                requests = descriptor['request_ids'][index*8:(index+1)*8]
                key = 'eval_batch_'+_digest(requests)
                identity = dict(evaluation_hash=_digest(descriptor), batch_index=index,
                    request_key=key, request_ids=requests, generations=8)
                stem = folder/'batches'/f'{index:06d}'; raw_path = Path(str(stem)+'.raw.json')
                before = {'state': index}
                write(raw_path, dict(identity=identity, rng_before=before, rng_after={'state': index+1}, raw=raw))
                write(Path(str(stem)+'.intent.json'), dict(identity=identity, rng_before=before))
                write(Path(str(stem)+'.reserved.json'), identity)
                part = records[index*8:(index+1)*8]
                write(Path(str(stem)+'.scored.json'), dict(identity=identity, raw_sha256=sha256_file(raw_path),
                    records_sha256=_digest(part), records=part))
                events.append(dict(name=key, reserved=8))
            # Crash after predictions advanced, before derived raw view and
            # per-event summary advanced: all three are valid different prefixes.
            rows_file(path, records); rows_file(path.with_suffix('.raw_batches.jsonl'), raw_batches[:1])
            prefix_bytes = ''.join(json.dumps(r, sort_keys=True, allow_nan=False)+'\n' for r in records[:8]).encode()
            summary = dict(**event, status='partial', completed_records=8,
                adapter={'sha256': 'a'*64}, predictions_sha256=hashlib.sha256(prefix_bytes).hexdigest())
            write(run/'C_probes.summary.json', summary)
            # Another request can have durable raw but no prediction file at all.
            raw_only = run/'B_discovery_sampled.resume/batches/000000.raw.json'
            write(raw_only, {'raw': {'problem_ids': ['unscored_fixture']*8}})
            events.append(dict(name='unscored_fixture_reservation', reserved=8))
            write(run/'run_manifest_final.json', dict(status='partial_resource_pause',
                release_manifest_sha256=sha256_file(RELEASE/'manifest.json'),
                diagnostic_manifest_sha256=sha256_file(RESUME_RELEASE/'manifest.json')))
            write(run/'generation_ledger.json', dict(used=616, historical_consumed=592, cap=4864, events=events))
            def audit_fixture(path, rows, tokenizer):
                return [dict(r, independent_trace_status='unverifiable', reference_program_class='unknown')
                        for r in read_jsonl(path)]
            with patch.object(analyzer, 'verified_tokenizer', return_value=(SimpleNamespace(eos_token_id=151643), {})),\
                 patch.object(analyzer, '_protocol', return_value=(protocol, {})),\
                 patch.object(analyzer, 'audit_records', side_effect=audit_fixture),\
                 patch.object(analyzer, 'audit_batch_journal'):
                output = Path(directory)/'partial_report'
                result = analyzer.analyze('unused', run, output=output)
                self.assertEqual(result['status'], 'partial_coverage_verified')
                self.assertEqual(result['generation_accounting']['partial_scored_records'], 16)
                self.assertEqual(result['generation_accounting']['new_completed_view_records'], 0)
                self.assertEqual(result['generation_accounting']['new_durable_raw_records'], 24)
                coverage = {r['evaluation']: r for r in json.loads((output/'coverage.json').read_text())}
                self.assertTrue(coverage['C_probes']['stale_summary'])
                self.assertTrue(coverage['C_probes']['derived_views_stale'])
                self.assertIsNone(coverage['C_probes']['primary_metrics'])
                self.assertEqual(coverage['B_discovery_sampled']['status'], 'partial_raw_only')
                self.assertTrue(all(r['contrasts'] is None for r in json.loads((output/'core_2x2.json').read_text())['results']))
                # A complete summary receives no relaxation, even in a partial run.
                write(run/'C_probes.summary.json', dict(summary, status='completed'))
                with self.assertRaisesRegex(ValueError, 'Prediction SHA differs'):
                    analyzer.analyze('unused', run, output=Path(directory)/'must_not_complete')
                # Neither an unrelated partial SHA nor changed prefix content is
                # an acceptable explanation for lagging mutable views.
                write(run/'C_probes.summary.json', dict(summary, predictions_sha256='0'*64))
                with self.assertRaisesRegex(ValueError, 'Partial summary SHA'):
                    analyzer.analyze('unused', run, output=Path(directory)/'must_not_accept_bad_sha')
                write(run/'C_probes.summary.json', summary)
                changed = [dict(r) for r in records]; changed[0]['batch_seconds'] += 1
                rows_file(path, changed)
                with self.assertRaisesRegex(ValueError, 'exact immutable prefix'):
                    analyzer.analyze('unused', run, output=Path(directory)/'must_not_accept_changed_prefix')

    def test_raw_commit_chain_binds_rng_reservation_and_scored_view(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'C_probes.jsonl'; folder = path.with_suffix('.resume')
            event = dict(name='C_probes', state='C', view='probes', questions=8,
                         samples=1, sampling=False, generations=8)
            rows = [dict(problem_id='p'+str(i), task='compute') for i in range(8)]
            protocol = {'fixed': True}
            descriptor = _descriptor(rows, event, {'model_hash': 'a'*64,
                'split_hash': sha256_file(DATA/'probes.jsonl')}, protocol)
            requests = descriptor['request_ids']; key = 'eval_batch_'+_digest(requests)
            identity = dict(evaluation_hash=_digest(descriptor), batch_index=0,
                            request_key=key, request_ids=requests, generations=8)
            raw = dict(problem_ids=[r['problem_id'] for r in rows])
            stem = folder/'batches/000000'; raw_path = Path(str(stem)+'.raw.json')
            write(folder/'manifest.json', dict(descriptor=descriptor, initial_rng={'state': 1}))
            write(raw_path, dict(identity=identity, rng_before={'state': 1}, rng_after={'state': 2}, raw=raw))
            write(Path(str(stem)+'.intent.json'), dict(identity=identity, rng_before={'state': 1}))
            write(Path(str(stem)+'.reserved.json'), identity)
            records = [{'problem_id': r['problem_id']} for r in rows]
            write(Path(str(stem)+'.scored.json'), dict(identity=identity, raw_sha256=sha256_file(raw_path),
                  records_sha256=_digest(records), records=records))
            rows_file(path, records); rows_file(path.with_suffix('.raw_batches.jsonl'), [raw])
            ledger = dict(events=[dict(name=key, reserved=8)])
            summary = {'adapter': {'sha256': 'a'*64}}
            with patch.object(analyzer, '_protocol', return_value=(protocol, {})):
                result = analyzer._audit_resume_commits(path, rows, event, summary, None, ledger)
                self.assertEqual(result['raw_generated_records'], 8)
                ledger['events'][0]['reserved'] = 7
                with self.assertRaisesRegex(ValueError, 'RNG continuity'):
                    analyzer._audit_resume_commits(path, rows, event, summary, None, ledger)

    def test_timing_counts_batches_once_and_leaves_unknown_fields_na(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'C_probes.jsonl'
            rows = [dict(problem_id='q', task='compute')]
            raw = dict(batch_index=0, problem_ids=['q']*4, batch_seconds=2.0,
                       padded_prompt_width=2, prompt_ids=[[1, 1]]*4,
                       output_ids=[[1, 1, 3, 0]]*4, stop_events=[{'retained_tokens': 2}]*4)
            rows_file(path.with_suffix('.raw_batches.jsonl'), [raw])
            event = dict(name='C_probes', state='C', sampling=True)
            result = analyzer.timing_profiles(path, [], rows, event)[0]
            self.assertEqual((result['batches'], result['generated_records']), (1, 4))
            self.assertEqual(result['generation_seconds_including_prefill'], 2.0)
            self.assertEqual(result['generated_tokens_with_padding'], 8)
            self.assertIsNone(result['prefill_seconds'])
            self.assertEqual(result['cpu_scoring']['measured_batches'], 0)

    def test_training_residual_is_combined_overhead_not_claimed_disk_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); receipt = root/'run/segments/segment_fixture.receipt.json'
            write(receipt, dict(status='completed', process_seconds=10, committed_step=2,
                                physically_finished_updates=2))
            rows_file(receipt.with_name('segment_fixture.jsonl'), [{'seconds': 2}, {'seconds': 3}])
            result = analyzer.training_timing(root, [{'state': 'C', 'run_id': 'run'}])[0]
            self.assertEqual(result['combined_non_update_seconds'], 5)
            self.assertIn('does not isolate', result['timing_definition'])

    def test_partial_release_preserves576_history_and_does_not_fill_new_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)/'run'; output = Path(directory)/'report'
            write(run/'run_manifest_final.json', dict(status='partial_resource_pause',
                release_manifest_sha256=sha256_file(RELEASE/'manifest.json'),
                diagnostic_manifest_sha256=sha256_file(RESUME_RELEASE/'manifest.json')))
            write(run/'generation_ledger.json', dict(used=592, historical_consumed=592, cap=4864, events=[]))
            # A recovery can commit before the logical segment result is saved.
            write(run/'thu_v2_e031_r1/recovery/latest.json', {'step': 16})
            def audit_fixture(path, rows, tokenizer):
                return [dict(r, independent_trace_status='unverifiable', reference_program_class='unknown')
                        for r in read_jsonl(path)]
            with patch.object(analyzer, 'verified_tokenizer', return_value=(SimpleNamespace(eos_token_id=0), {})),\
                 patch.object(analyzer, 'audit_records', side_effect=audit_fixture),\
                 patch.object(analyzer, 'audit_batch_journal'):
                result = analyzer.analyze('unused', run, output=output)
            self.assertEqual(result['status'], 'partial_coverage_verified')
            self.assertEqual(result['generation_accounting']['historical_unique_completed'], 576)
            self.assertEqual(result['generation_accounting']['cumulative_attempts'], 592)
            self.assertEqual(result['generation_accounting']['new_completed_view_records'], 0)
            self.assertEqual(result['training'][0]['status'], 'partial')
            self.assertEqual(result['training'][0]['completed_updates'], 16)
            core = json.loads((output/'core_2x2.json').read_text())
            self.assertTrue(all(row['contrasts'] is None for row in core['results']))
            reference = json.loads((output/'reference_nll.json').read_text())
            self.assertTrue(all(row['metrics'] is None for row in reference['results']))
            self.assertIn('NA', (output/'REPORT.md').read_text())
            with self.assertRaises(FileExistsError):
                analyzer.analyze('unused', run, output=output)


if __name__ == '__main__':
    unittest.main()
