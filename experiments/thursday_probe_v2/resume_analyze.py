"""Offline token replay and complete/partial reporting for the post-E030 queue.

Uses the original scorer and paired bootstrap. This module never loads model
weights, generates samples, changes original results, or fills missing cells.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import json
import hashlib
import math
from pathlib import Path

import numpy as np

from experiments.thursday_probe.common import SEEDS, dump, jsonl, verify_manifest
from experiments.thursday_probe_v2.analyze import (
    N_BOOTSTRAP, audit_records, paired_interval, per_question)
from experiments.thursday_probe_v2.config import DATA, RELEASE, STATES, evaluation_queue
from experiments.thursday_probe_v2.partial_audit import audit_batch_journal, incomplete_file, measurement
from experiments.thursday_probe_v2.queue import load_inputs
from experiments.thursday_probe_v2.resume_diagnostics import (
    RESUME_RELEASE, construction_error_breakdown, load_generation_rows)
from experiments.thursday_probe_v2.resumable_generation import _descriptor, _digest, _protocol
from scripts.audit_family_matching import verified_tokenizer
from src.sft_data import read_jsonl, sha256_file
from src.trace_audit import audit_trace

RUN = Path('runs/thursday_arithmetic_resume_r1')
HISTORICAL = Path('runs/thursday_arithmetic_v2_r2')
OUTPUT = Path('reports/thursday_resume_analysis_r1')
CHILDREN = ('C-S', 'C-P', 'B-S', 'B-P')


def core_results(completed, problems, groups):
    """Four-cell contrasts require all four complete, matching evaluation sets."""
    by_id = {p['problem_id']: p for p in problems}
    result = []
    for group, members in groups.items():
        ids = sorted(members)
        clusters = [by_id[pid]['paths']['B']['structure_id'] for pid in ids]
        for view, metric in (('discovery_sampled', 'pass_at_1'),
                             ('discovery_sampled', 'pass_at_4'),
                             ('discovery_greedy', 'pass_at_1')):
            values, cells = {}, {}
            for state in CHILDREN:
                name = state+'_'+view
                if name not in completed:
                    cells[state] = dict(status='not_measured_complete_view', estimate=None)
                    continue
                qs = per_question(completed[name])
                expected_n = 4 if view == 'discovery_sampled' else 1
                if set(qs) != set(by_id) or any(q['n'] != expected_n for q in qs.values()):
                    raise ValueError('Core comparison requires the exact complete frozen question/sample set')
                values[state] = np.asarray([qs[pid][metric] for pid in ids], dtype=float)
                cells[state] = dict(status='measured', **paired_interval(values[state], clusters))
            contrasts = None
            if len(values) == 4:
                dc = values['C-P']-values['C-S']; db = values['B-P']-values['B-S']
                contrasts = {name: paired_interval(vector, clusters) for name, vector in
                             (('delta_C', dc), ('delta_B', db), ('interaction', db-dc))}
            result.append(dict(subgroup=group, questions=len(ids), view=view, metric=metric,
                               status='complete' if contrasts is not None else 'incomplete_cells',
                               cells=cells, contrasts=contrasts))
    return dict(results=result, bootstrap_replicates=N_BOOTSTRAP, seed=SEEDS['bootstrap'],
                cluster_definition='Frozen reference-B canonical structure ID',
                uncertainty_scope='Paired question/template resampling only; excludes training, '
                                  'prep and assignment seed uncertainty. Missing cells are not zero. '
                                  'Nonsignificance is not equivalence.')


def _measure(records):
    if not records:
        return None
    result = measurement(records)
    result['correct_generations'] = sum(bool(r['score']['correct']) for r in records)
    result['independent_questions'] = result['questions']
    result['parsed_generations'] = sum(bool(r['score']['parsed']) for r in records)
    result['completed_generations'] = sum(bool(r['score']['completed']) for r in records)
    result['retained_length_quantiles'] = dict(zip(('min', 'p25', 'p50', 'p75', 'p95', 'max'),
        np.quantile([len(r['generated_ids']) for r in records], [0, .25, .5, .75, .95, 1]).tolist()))
    result['resource_rule_status'] = dict(Counter(
        'NA' if r.get('supplemental_resource_rule_satisfied') is None else
        'satisfied' if r['supplemental_resource_rule_satisfied'] else 'violated' for r in records))
    result['resource_rule_definition'] = ('Construction: exact final-expression input multiset; '
        'compute: connected resource derivation from the supplied expression inputs. Unknown is NA.')
    result['task_types'] = dict(Counter(r['task'] for r in records))
    return result


def _add_resource_evidence(records, rows):
    by_id = {r['problem_id']: r for r in rows}
    for record in records:
        row = by_id[record['problem_id']]
        text = record['forced_prefix']+record['stop']['answer_segment']
        if row['task'] == 'construct':
            resource = construction_error_breakdown(row, text)['uses_input_multiset']
        else:
            lines = text.splitlines(); answers = [i for i, line in enumerate(lines)
                                                  if line.strip().startswith('Answer:')]
            resource = None
            if len(answers) == 1:
                lines[answers[0]] = 'Answer: '+row['expression']
                trace = audit_trace('\n'.join(lines), row['numbers'], Fraction(row['answer']))
                resource = {'verified': True, 'inconsistent': False}.get(trace['resource_derivation_status'])
        record['supplemental_resource_rule_satisfied'] = resource
    return records


def probe_results(completed):
    table, by = [], {}
    for state in ('C0', 'C', 'B'):
        for category in ('atomic', 'target', 'control'):
            name = state+'_probes'
            rows = [r for r in completed.get(name, []) if r['category'] == category]
            metric = _measure(rows)
            table.append(dict(state=state, category=category,
                              status='measured' if metric else 'not_measured_complete_view', metrics=metric))
            if metric:
                by[state, category] = per_question(rows)
    contrast = None
    if all((s, c) in by for s in ('C', 'B') for c in ('target', 'control')):
        rng = np.random.default_rng(SEEDS['bootstrap']); draws = {}; differences = {}
        for category in ('target', 'control'):
            c, b = by['C', category], by['B', category]
            if set(c) != set(b):
                raise ValueError('Parent probe question identities differ')
            ids = sorted(c)
            diff = np.array([b[pid]['pass_at_1']-c[pid]['pass_at_1'] for pid in ids])
            differences[category] = paired_interval(diff, [category]*len(ids))
            draws[category] = diff[rng.integers(0, len(diff), (N_BOOTSTRAP, len(diff)))].mean(axis=1)
        contrast = dict(delta_target=differences['target'], delta_control=differences['control'],
                        D=differences['target']['mean']-differences['control']['mean'],
                        D_stratified_paired_question_ci=np.quantile(
                            draws['target']-draws['control'], [.025, .975]).tolist(),
                        descriptive_only=True, score_used_as_run_gate=False,
                        limitation='Four draws per question are not independent questions; '
                                   'one template per compute category prevents a template-population interval.')
    return dict(table=table, manipulation_contrast=contrast)


def sentinel_results(completed, sentinel_rows):
    ids = {r['problem_id'] for r in sentinel_rows}; table = []; paired = {}
    for state in ('C0',)+STATES:
        name = state+('_probes' if state in ('C0', 'C', 'B') else '_sentinel')
        rows = [r for r in completed.get(name, []) if r['problem_id'] in ids and r['sample_index'] < 2]
        for category in ('atomic', 'target', 'control'):
            subset = [r for r in rows if r['category'] == category]
            metric = _measure(subset)
            parent = None if state == 'C0' else 'C0' if state in ('C', 'B') else state[0]
            change = None
            if metric:
                qs = per_question(subset); paired[state, category] = qs
                if parent and (parent, category) in paired:
                    before = paired[parent, category]
                    if set(before) != set(qs):
                        raise ValueError('Sentinel parent/child question identities differ')
                    change = paired_interval([qs[p]['pass_at_1']-before[p]['pass_at_1']
                                              for p in sorted(qs)], [category]*len(qs))
            table.append(dict(state=state, category=category, metrics=metric,
                              status='measured' if metric else 'not_measured_complete_view',
                              comparison_parent=parent, change_from_parent=change,
                              source='first_two_parent_probe_samples' if state in ('C0', 'C', 'B')
                              else 'registered_endpoint_sentinel'))
    return table


def midpoint_results(completed, midpoint_rows):
    ids = {r['problem_id'] for r in midpoint_rows}; result = []
    for child in CHILDREN:
        for step, state, view in (('parent', child[0], 'discovery_greedy'),
                                  (128, child, 'midpoint'), (256, child, 'discovery_greedy')):
            name = state+'_'+view
            rows = [r for r in completed.get(name, []) if r['problem_id'] in ids]
            metric = _measure(rows)
            result.append(dict(child=child, step=step, source_evaluation=name,
                               status='measured' if metric else 'not_measured_complete_view', metrics=metric))
    return result


def diagnostic_results(completed, rows):
    selection_path = RESUME_RELEASE/'selection.json'
    selection = json.loads(selection_path.read_text())
    groups = {'full': {r['problem_id'] for r in rows}}
    for field in ('diagnostic_anchor_family', 'diagnostic_target_label'):
        for label in sorted({r[field] for r in rows}):
            groups[label] = {r['problem_id'] for r in rows if r[field] == label}
    table = []
    for state in CHILDREN:
        rs = completed.get(state+'_train_diagnostic', [])
        for group, ids in groups.items():
            metric = _measure([r for r in rs if r['problem_id'] in ids])
            table.append(dict(state=state, subgroup=group, registered_questions=len(ids),
                              status='measured' if metric else 'not_measured_complete_view', metrics=metric))
    scope = dict(selection_sha256=sha256_file(selection_path),
                 population_questions=selection['population_questions'],
                 selected_questions=selection['selected_questions'],
                 strata=[{key: stratum[key] for key in
                          ('anchor_family', 'target_label', 'support', 'final_selected_count')}
                         for stratum in selection['strata']],
                 target_label_basis=selection['target_label_basis'],
                 weighting='Unweighted selected-question diagnostic. Equal stratum allocation '
                           'oversamples target-degenerate questions: 8/16 selected versus 54/256 '
                           'in the training population; no population reweighting is applied.')
    return dict(table=table, sampling_scope=scope, interpretation='Any legal correct construction is accepted. These fixed '
                '16 training questions do not estimate whole-training accuracy, literal memorization, '
                'unseen generalization, or an exact train-discovery generalization gap.')


def construction_errors(records, rows, event):
    by_id = {r['problem_id']: r for r in rows}; output = []
    for record in records:
        row = by_id[record['problem_id']]
        if row['task'] != 'construct':
            continue
        result = construction_error_breakdown(row,
            record['forced_prefix']+record['stop']['answer_segment'],
            stop_reason=record['stop']['stop_reason'], output_tokens=len(record['generated_ids']))
        valid_construction = result['resource_target_category'] == 'both_satisfied' and result['completed']
        if bool(valid_construction) != bool(record['score']['correct']):
            raise ValueError('Supplemental resource/target decomposition changed the primary correctness')
        output.append(dict(evaluation=event['name'], state=event['state'], view=event['view'],
                           problem_id=record['problem_id'], sample_index=record['sample_index'],
                           primary_correct=record['score']['correct'],
                           teacher_free_resource_verified_correct=bool(valid_construction), **result))
    return output


def _audit_resume_commits(path, rows, event, summary, tokenizer, ledger, *, allow_stale_views=False):
    """Bind compatible JSONL to immutable batches, reservations, and RNG chain."""
    folder = path.with_suffix('.resume'); manifest_path = folder/'manifest.json'
    manifest = json.loads(manifest_path.read_text()); descriptor = manifest['descriptor']
    protocol, _ = _protocol(event, tokenizer)
    expected = _descriptor(rows, event, descriptor['identity'], protocol)
    if descriptor != expected or descriptor['identity']['model_hash'] != summary['adapter']['sha256']:
        raise ValueError('Resume descriptor/model/protocol differs from registered evaluation')
    split_path = (RESUME_RELEASE/'train_diagnostic.jsonl' if event['view'] == 'train_diagnostic' else
                  (RELEASE if event['view'] in ('sentinel', 'midpoint') else DATA)/
                  (('discovery_problems' if event['view'].startswith('discovery_') else event['view'])+'.jsonl'))
    if descriptor['identity']['split_hash'] != sha256_file(split_path):
        raise ValueError('Resume split identity changed')
    budget = {r['name']: r['reserved'] for r in ledger['events']}
    evaluation_hash = _digest(descriptor); before = manifest['initial_rng']
    raw_files = sorted((folder/'batches').glob('*.raw.json')); records = []; raws = []; request_keys = []
    for index, raw_path in enumerate(raw_files):
        if raw_path.name != f'{index:06d}.raw.json':
            raise ValueError('Committed raw batches are not contiguous')
        requests = descriptor['request_ids'][index*8:(index+1)*8]
        key = 'eval_batch_'+_digest(requests)
        identity = dict(evaluation_hash=evaluation_hash, batch_index=index,
                        request_key=key, request_ids=requests, generations=len(requests))
        raw = json.loads(raw_path.read_text()); stem = folder/'batches'/f'{index:06d}'
        intent = json.loads(Path(str(stem)+'.intent.json').read_text())
        reserved = json.loads(Path(str(stem)+'.reserved.json').read_text())
        if (not requests or raw['identity'] != identity or reserved != identity or
                intent['identity'] != identity or raw['rng_before'] != before or
                intent['rng_before'] != before or budget.get(key) != len(requests)):
            raise ValueError('Raw identity, reservation or RNG continuity mismatch')
        before = raw['rng_after']; raws.append(raw['raw']); request_keys.append(key)
        scored_path = Path(str(stem)+'.scored.json')
        if scored_path.exists():
            scored = json.loads(scored_path.read_text())
            if (scored['identity'] != identity or scored['raw_sha256'] != sha256_file(raw_path) or
                    scored['records_sha256'] != _digest(scored['records']) or len(records) != index*8):
                raise ValueError('Immutable scored batch changed or has a gap')
            records.extend(scored['records'])
    published = read_jsonl(path)
    raw_view = path.with_suffix('.raw_batches.jsonl')
    published_raw = read_jsonl(raw_view) if raw_view.exists() else []
    if allow_stale_views:
        # Each derived file is independently replaced. A crash may leave either
        # view, or the event summary, at an earlier exact committed prefix.
        if (len(published) > len(records) or published != records[:len(published)] or
                len(published_raw) > len(raws) or published_raw != raws[:len(published_raw)]):
            raise ValueError('Partial derived view is not an exact immutable prefix')
        count = summary['completed_records']
        if type(count) is not int or not 0 <= count <= len(records) or count % 8:
            raise ValueError('Partial summary count is not a committed batch prefix')
        prefix_bytes = ''.join(json.dumps(r, sort_keys=True, allow_nan=False)+'\n'
                               for r in records[:count]).encode()
        if hashlib.sha256(prefix_bytes).hexdigest() != summary['predictions_sha256']:
            raise ValueError('Partial summary SHA is not its immutable scored prefix')
    elif records != published or not raw_view.exists() or raws != published_raw:
        raise ValueError('Derived prediction/journal view differs from immutable commits')
    return dict(manifest_sha256=sha256_file(manifest_path), raw_batches=len(raws),
                raw_generated_records=sum(len(r['problem_ids']) for r in raws),
                scored_records=len(records), committed_request_keys=request_keys,
                published_scored_records=len(published), published_raw_batches=len(published_raw),
                derived_views_stale=published != records or published_raw != raws,
                summary_stale=summary.get('predictions_sha256') != sha256_file(path),
                status='immutable_batches_rng_and_reservations_verified')


def _prefix_journal(path, records, rows, event, tokenizer, *, committed_raw=False):
    """Audit scored prefix batches; unscored raw commits are inventoried separately."""
    expected = [(r['problem_id'], sample) for r in rows for sample in range(event['samples'])]
    if [(r['problem_id'], r['sample_index']) for r in records] != expected[:len(records)]:
        raise ValueError('Partial predictions are not an exact frozen prefix')
    batches = ([json.loads(p.read_text())['raw'] for p in
                sorted((path.with_suffix('.resume')/'batches').glob('*.raw.json'))]
               if committed_raw else read_jsonl(path.with_suffix('.raw_batches.jsonl')))
    if len(records) % 8 or len(batches)*8 < len(records):
        raise ValueError('Partial scored records do not end at a fixed batch boundary')
    for index in range(len(records)//8):
        part = records[index*8:(index+1)*8]; raw = batches[index]
        prompts = [r['prompt_ids'] for r in part]; width = max(map(len, prompts))
        inputs = [[tokenizer.eos_token_id]*(width-len(p))+p for p in prompts]
        wanted = dict(batch_index=index, start_index=index*8, padded_prompt_width=width,
                      problem_ids=[r['problem_id'] for r in part], sample_indices=[r['sample_index'] for r in part],
                      forced_prefixes=[r['forced_prefix'] for r in part], prompt_ids=prompts, input_ids=inputs,
                      attention_mask=[[0]*(width-len(p))+[1]*len(p) for p in prompts],
                      output_ids=[p+r['batch_output_ids'] for p, r in zip(inputs, part)],
                      stop_events=[r['stop'] for r in part])
        if any(raw.get(k) != v for k, v in wanted.items()) or any(
                r['batch_index'] != index or r['batch_seconds'] != raw['batch_seconds'] for r in part):
            raise ValueError('Partial raw/scored batch correspondence changed')
    return dict(status='scored_prefix_verified', scored_records=len(records),
                raw_batches=len(batches), scored_batches=len(records)//8)


def timing_profiles(path, records, rows, event):
    by_id = {r['problem_id']: r for r in rows}; groups = defaultdict(list)
    journal = path.with_suffix('.raw_batches.jsonl')
    if journal.exists():
        batches = read_jsonl(journal)
    else:
        grouped = defaultdict(list)
        for r in records:
            grouped[r['batch_index']].append(r)
        batches = [dict(batch_index=i, problem_ids=[r['problem_id'] for r in rs],
                        batch_seconds=rs[0]['batch_seconds'],
                        retained_generated_tokens=sum(len(r['generated_ids']) for r in rs),
                        generated_tokens_with_padding=sum(len(r['batch_output_ids']) for r in rs),
                        input_nonpadding_tokens=sum(len(r['prompt_ids']) for r in rs))
                   for i, rs in sorted(grouped.items())]
    for raw in batches:
        tasks = sorted({by_id[p]['task'] for p in raw['problem_ids']})
        timing_path = path.with_suffix('.resume')/'batches'/f"{raw['batch_index']:06d}.timing.json"
        timing = json.loads(timing_path.read_text()) if timing_path.exists() else {}
        width = raw.get('padded_prompt_width', 0)
        retained = raw.get('retained_generated_tokens')
        if retained is None and 'stop_events' in raw:
            retained = sum(r['retained_tokens'] for r in raw['stop_events'])
        generated = raw.get('generated_tokens_with_padding')
        if generated is None and 'output_ids' in raw:
            generated = sum(len(ids)-width for ids in raw['output_ids'])
        groups['+'.join(tasks)].append(dict(raw=raw, timing=timing, retained=retained, generated=generated))
    output = []
    for task, batches in groups.items():
        seconds = sum(b['raw']['batch_seconds'] for b in batches)
        def partial_sum(field):
            values = [b['timing'].get(field) for b in batches]
            return dict(known_seconds=sum(v for v in values if v is not None),
                        measured_batches=sum(v is not None for v in values), total_batches=len(values))
        output.append(dict(evaluation=event['name'], state=event['state'], task=task,
                           decoding='sampled' if event['sampling'] else 'greedy', batches=len(batches),
                           generated_records=sum(len(b['raw']['problem_ids']) for b in batches),
                           generation_seconds_including_prefill=seconds,
                           prefill_seconds=None, decode_only_seconds=None,
                           generated_tokens_with_padding=sum(b['generated'] or 0 for b in batches),
                           retained_generated_tokens=sum(b['retained'] or 0 for b in batches),
                           input_nonpadding_tokens=sum(b['raw'].get('input_nonpadding_tokens',
                               sum(map(len, b['raw'].get('prompt_ids', [])))) for b in batches),
                           cpu_scoring=partial_sum('cpu_score_seconds'),
                           raw_save=partial_sum('raw_save_seconds'), score_save=partial_sum('score_save_seconds'),
                           note='Batch counts, generated records and tokens are distinct. Unmeasured timing '
                                'components remain NA; generation already includes prefill.'))
    return output


def _reference_nll(run):
    output = []
    for state in CHILDREN:
        for family in ('A', 'B'):
            path = run/(state+'_train_reference_'+family+'.json')
            row = dict(state=state, family=family, status='not_measured', metrics=None,
                       reference_rows_sha256=sha256_file(RESUME_RELEASE/('reference_'+family+'.jsonl')),
                       artifact_sha256=None, additional_autoregressive_generations=0,
                       separately_measured_runtime_seconds=None)
            if path.exists():
                metric = json.loads(path.read_text())
                if (metric['reference_count'] != 16 or metric['supervised_tokens'] <= 0 or
                        not math.isclose(metric['nll'], metric['response_loss_sum']/metric['supervised_tokens'],
                                         rel_tol=1e-10, abs_tol=1e-12)):
                    raise ValueError('Training diagnostic NLL has an invalid denominator or normalization')
                forward_seconds = metric.get('forward_seconds')
                if forward_seconds is not None and (
                        type(forward_seconds) not in (int, float) or
                        not math.isfinite(forward_seconds) or forward_seconds < 0):
                    raise ValueError('Training diagnostic NLL forward_seconds must be finite and nonnegative')
                row.update(status='measured', metrics=metric, artifact_sha256=sha256_file(path),
                           separately_measured_runtime_seconds=forward_seconds)
            output.append(row)
    return dict(results=output, reference_definition=dict(
                family_namespace='A/B denotes reference program families, not prep states C/B.',
                rendering_id=0,
                aggregation='Response-token-weighted NLL over 16 references per family; '
                            'not a mean of question-level NLLs.',
                anchor_mapping='Surface trains the assigned anchor family only: each reference-family '
                               'aggregate contains eight anchor and eight non-anchor questions. '
                               'Paths trains both program families, but reference rendering 0 can differ '
                               'from the trained rendering. The aggregates do not isolate seen text, '
                               'unseen paths, or anchor-specific NLL.'),
                note='Teacher-forced forward measurements have zero autoregressive '
                'generations but nonzero runtime included in the rental/process ledger. '
                'Recorded forward_seconds is reported as separately measured runtime; '
                'absent timing remains NA, never an assumed zero. This time is already included '
                'in process/rental charges and must not be added to them again.')


def training_timing(run, registrations):
    output = []
    for registration in registrations:
        folder = run/registration['run_id']/'segments'
        for receipt_path in sorted(folder.glob('*.receipt.json')):
            receipt = json.loads(receipt_path.read_text())
            journal_path = receipt_path.with_name(receipt_path.name.replace('.receipt.json', '.jsonl'))
            inventory, rows = incomplete_file(journal_path) if journal_path.exists() else ({}, [])
            step_seconds = sum(r['seconds'] for r in rows)
            if step_seconds > receipt['process_seconds']+1e-6:
                raise ValueError('Training step timing exceeds its segment wall duration')
            output.append(dict(state=registration['state'], run_id=registration['run_id'],
                               receipt=receipt_path.name, receipt_sha256=sha256_file(receipt_path),
                               segment_status=receipt['status'], segment_wall_seconds=receipt['process_seconds'],
                               logged_update_seconds=step_seconds,
                               combined_non_update_seconds=receipt['process_seconds']-step_seconds,
                               timing_definition='Residual includes initialization/load, checkpoint/recovery '
                               'serialization, hashing, readback, synchronization and bookkeeping. '
                               'It does not isolate disk write or synchronization time.',
                               committed_step=receipt['committed_step'],
                               physically_finished_updates=receipt['physically_finished_updates'],
                               journal_inventory=inventory))
    return output


def analyze(tokenizer_dir, run_dir=RUN, historical_dir=HISTORICAL, output=OUTPUT):
    run, historical, output = Path(run_dir), Path(historical_dir), Path(output)
    if output.exists():
        raise FileExistsError('Never overwrite an offline analysis release')
    inputs, registrations, _, _, doses = load_inputs(); verify_manifest(RESUME_RELEASE)
    inputs['train_diagnostic'] = load_generation_rows()
    tokenizer, tokenizer_identity = verified_tokenizer(Path(tokenizer_dir))
    hist_manifest = json.loads((historical/'run_manifest_final.json').read_text())
    run_manifest = json.loads((run/'run_manifest_final.json').read_text())
    if run_manifest['status'] == 'running':
        raise ValueError('Analyze an exported completed/paused/fault snapshot, not a live changing worker')
    for manifest in (hist_manifest, run_manifest):
        if manifest['release_manifest_sha256'] != sha256_file(RELEASE/'manifest.json'):
            raise ValueError('Execution and frozen analysis release differ')
    if run_manifest['diagnostic_manifest_sha256'] != sha256_file(RESUME_RELEASE/'manifest.json'):
        raise ValueError('Diagnostic selection differs from the executed release')
    ledger = json.loads((run/'generation_ledger.json').read_text())
    hist_ledger = json.loads((historical/'generation_ledger.json').read_text())
    if (hist_ledger['used'] != 592 or hist_ledger.get('fault_generations') != 16 or
            ledger['historical_consumed'] != 592 or ledger['cap'] != 4864 or not 592 <= ledger['used'] <= 4864 or
            any(type(e['reserved']) is not int or e['reserved'] <= 0 for e in ledger['events']) or
            ledger['used'] != 592+sum(e['reserved'] for e in ledger['events']) or ledger['used'] > 4864 or
            len({e['name'] for e in ledger['events']}) != len(ledger['events'])):
        raise ValueError('Historical/new generation accounting was reset or changed')
    events = evaluation_queue()+json.loads((RESUME_RELEASE/'evaluation_queue.json').read_text())
    hist_summaries = {e['name']: e for e in hist_manifest['evaluations']}
    terminal_summaries = {e['name']: e for e in run_manifest.get('evaluations', [])}
    completed, coverage, perq, errors, timing, commits = {}, [], [], [], [], {}
    bindings = {str(p): sha256_file(p) for p in (
        historical/'run_manifest_final.json', historical/'generation_ledger.json',
        run/'run_manifest_final.json', run/'generation_ledger.json', RELEASE/'manifest.json',
        RESUME_RELEASE/'manifest.json')}
    new_raw = 0; completed_new = 0; historical_unique = 0; partial_scored = 0
    for event in events:
        name = event['name']; legacy = event['state'] in ('C0', 'calibration')
        folder = historical if legacy else run
        path = folder/(name+'.jsonl'); summary_path = folder/(name+'.summary.json')
        summary = hist_summaries.get(name) if legacy else (
            json.loads(summary_path.read_text()) if summary_path.exists() else None)
        key = 'discovery_problems' if event['view'].startswith('discovery_') else event['view']
        rows = inputs[key]
        cov = dict(evaluation=name, state=event['state'], view=event['view'], expected_records=event['generations'],
                   expected_questions=event['questions'], expected_samples_per_question=event['samples'],
                   status='not_run', scored_records=0, primary_metrics=None, historical_reuse=legacy)
        if not path.exists():
            if summary and summary['status'] == 'completed':
                raise ValueError('Completed evaluation is missing predictions: '+name)
            durable = sorted((path.with_suffix('.resume')/'batches').glob('*.raw.json')) if not legacy else []
            if durable:
                cov.update(status='partial_raw_only', durable_raw_batches=len(durable),
                    limitation='Durable raw output exists without a published scored view; no primary measurement is reported.')
            coverage.append(cov); continue
        inventory, raw_records = incomplete_file(path)
        cov.update(file_inventory=inventory, scored_records=len(raw_records), status='partial')
        bindings[str(path)] = sha256_file(path)
        if summary is None:
            cov['limitation'] = 'Predictions have no committed summary; no primary measurement is reported.'
            coverage.append(cov); partial_scored += len(raw_records); continue
        allow_stale = not legacy and run_manifest['status'] != 'completed' and summary['status'] != 'completed'
        cov['stale_summary'] = sha256_file(path) != summary['predictions_sha256']
        if cov['stale_summary'] and not allow_stale:
            raise ValueError('Prediction SHA differs from its committed summary: '+name)
        if summary_path.exists():
            bindings[str(summary_path)] = sha256_file(summary_path)
        if any(summary[k] != event[k] for k in ('state', 'view', 'questions', 'samples', 'sampling', 'generations')):
            raise ValueError('Evaluation registration changed: '+name)
        if not legacy and run_manifest['status'] == 'completed':
            terminal = terminal_summaries.get(name)
            if not terminal or any(terminal[k] != summary[k] for k in ('status', 'predictions_sha256', 'adapter')):
                raise ValueError('Completed terminal manifest and evaluation summary disagree: '+name)
        if inventory['invalid_json_lines']:
            if summary['status'] == 'completed':
                raise ValueError('Completed evaluation contains torn/invalid JSON')
            cov['limitation'] = 'Torn partial stream, excluded from scored measurements.'
            coverage.append(cov); partial_scored += len(raw_records); continue
        records = _add_resource_evidence(audit_records(path, rows, tokenizer), rows)
        expected = [(r['problem_id'], s) for r in rows for s in range(event['samples'])]
        if [(r['problem_id'], r['sample_index']) for r in records] != expected[:len(records)]:
            raise ValueError('Wrong question/sample order or excess predictions: '+name)
        if not legacy:
            commits[name] = _audit_resume_commits(path, rows, event, summary, tokenizer, ledger,
                                                 allow_stale_views=allow_stale)
            cov.update(immutable_scored_records=commits[name]['scored_records'],
                       durable_raw_records=commits[name]['raw_generated_records'],
                       derived_views_stale=commits[name]['derived_views_stale'])
            new_raw += commits[name]['raw_generated_records']
        complete = summary['status'] == 'completed'
        if complete:
            if len(records) != event['generations']:
                raise ValueError('A completed view is missing registered outputs: '+name)
            audit_batch_journal(path, records, rows, event, tokenizer,
                                allow_missing=legacy and bool(summary.get('reused_from')))
            completed[name] = records; cov.update(status='completed', primary_metrics=_measure(records))
            if legacy:
                historical_unique += len(records)
            else:
                completed_new += len(records)
            perq.extend(dict(evaluation=name, state=event['state'], view=event['view'],
                             problem_id=pid, **metric) for pid, metric in per_question(records).items())
        else:
            _prefix_journal(path, records, rows, event, tokenizer, committed_raw=allow_stale)
            partial_scored += len(records)
            cov['limitation'] = 'Audited prefix only; excluded from full-view primary scores and contrasts.'
        coverage.append(cov)
        errors.extend(dict(complete_evaluation=complete, **r) for r in construction_errors(records, rows, event))
        timing.extend(timing_profiles(path, records, rows, event))
    if historical_unique != 576:
        raise ValueError('The four historical completed evaluations must contribute exactly576 unique results')
    extra_attempts = ledger['used']-592
    # A process can commit raw output immediately before failing, without a
    # scored view or summary. Inventory it without labeling it a lost output.
    raw_inventory = []
    for path in sorted(run.glob('*.resume/batches/*.raw.json')):
        bundle = json.loads(path.read_text())
        raw_inventory.append(dict(path=str(path.relative_to(run)), sha256=sha256_file(path),
                                  records=len(bundle['raw']['problem_ids'])))
    inventoried_raw = sum(r['records'] for r in raw_inventory)
    if new_raw > inventoried_raw or inventoried_raw > extra_attempts:
        raise ValueError('Durable new output count exceeds charged generation attempts')
    all_complete = all(c['status'] == 'completed' for c in coverage)
    if run_manifest['status'] == 'completed' and (not all_complete or completed_new != 4192):
        raise ValueError('Completed phase manifest disagrees with evaluation coverage')
    data_audit = json.loads((RELEASE/'DATA_AUDIT_v2.json').read_text())
    core = core_results(completed, inputs['discovery_problems'],
                        data_audit['reference_subgroups']['discovery']['groups'])
    probes = probe_results(completed)
    error_summary = []
    for cov in coverage:
        rs = [r for r in errors if r['evaluation'] == cov['evaluation']]
        if rs:
            error_summary.append(dict(evaluation=cov['evaluation'], status=cov['status'], records=len(rs),
                primary_correct=sum(r['primary_correct'] for r in rs),
                teacher_free_resource_verified_correct=sum(r['teacher_free_resource_verified_correct'] for r in rs),
                resource_target_categories=dict(Counter(r['resource_target_category'] for r in rs)),
                intermediate_arithmetic=dict(Counter(r['intermediate_arithmetic_status'] for r in rs)),
                note='Correct means completed, exact target and exact input multiset under the original scorer; '
                     'parsing alone is never resource-verified task correctness. Local arithmetic is independent of target success.'))
    training = []
    for registration in registrations:
        if registration['state'] == 'calibration':
            continue
        final = run/registration['run_id']/'run_manifest_final.json'
        segment = final.with_name('segment_progress.json')
        pointer = final.parent/'recovery/latest.json'
        record = json.loads(final.read_text()) if final.exists() else None
        cursor = (json.loads(pointer.read_text())['step'] if pointer.exists() else
                  json.loads(segment.read_text())['step'] if segment.exists() else 0)
        if not 0 <= cursor <= registration['updates']:
            raise ValueError('Committed training cursor exceeds its registration')
        if record and record['status'] == 'completed':
            history_path = final.with_name('train_history.jsonl'); history = read_jsonl(history_path)
            expected_dose = doses[registration['data']]
            if (any(record[k] != registration[k] for k in registration) or record['budget'] != expected_dose or
                    record['data_sha256'] != sha256_file(DATA/(registration['data']+'.jsonl')) or
                    [r['step'] for r in history] != list(range(1, registration['updates']+1)) or
                    sum(r['supervised_tokens'] for r in history) != expected_dose['supervised_response_tokens'] or
                    sum(r['processed_tokens'] for r in history) != expected_dose['processed_nonpadding_tokens']):
                raise ValueError('Completed training history differs from frozen dose')
            bindings[str(final)] = sha256_file(final); bindings[str(history_path)] = sha256_file(history_path)
            cursor = registration['updates']
        started = cursor > 0 or final.with_name('run_manifest.json').exists()
        training.append(dict(**registration, status=record['status'] if record else 'partial' if started else 'not_run',
                             completed_updates=cursor, final_record=record))
    summary = dict(status='all_registered_outputs_verified' if all_complete else 'partial_coverage_verified',
        run_manifest_status=run_manifest['status'], completed_evaluations=sum(c['status']=='completed' for c in coverage),
        expected_evaluations=len(events), generation_accounting=dict(
            historical_unique_completed=576, historical_actual_attempts=592, historical_fault_attempts=16,
            historical_saved_fault_records=12, historical_unrecoverable_fault_records=4,
            new_completed_view_records=completed_new, new_durable_raw_records=inventoried_raw,
            new_raw_records_with_full_commit_audit=new_raw,
            partial_scored_records=partial_scored, new_charged_attempts=extra_attempts,
            new_charged_without_durable_raw=extra_attempts-inventoried_raw,
            cumulative_attempts=ledger['used'], unique_completed_results=historical_unique+completed_new,
            planned_core_unique=4704, planned_diagnostic_unique=64, planned_total_unique=4768,
            planned_cumulative_attempts=4784, unchanged_cap=4864),
        tokenizer=tokenizer_identity, inputs_sha256=bindings, training=training,
        immutable_batch_audits=commits, durable_raw_inventory=raw_inventory, reserved_test_contents_read=False,
        primary_scorer_changed=False, model_calls=0,
        limitations=['All invalid and incomplete generated answers remain in their completed-view denominators.',
                     'Incomplete evaluation prefixes are inventoried but do not provide full-view estimates.',
                     'Sixteen selected training questions are a small diagnostic, not a generalization estimate.',
                     'Fine-structure and prep-token residuals remain; no pure mechanism claim is identified.',
                     'Power/rental costs are read from separate ledgers, never inferred from generation time.'])
    artifacts = {'summary.json': summary, 'coverage.json': coverage, 'core_2x2.json': core,
                 'parent_probes.json': probes, 'sentinel.json': sentinel_results(completed, inputs['sentinel']),
                 'midpoint.json': midpoint_results(completed, inputs['midpoint']),
                 'training_diagnostic.json': diagnostic_results(completed, inputs['train_diagnostic']),
                 'reference_nll.json': _reference_nll(run), 'construction_errors.json': error_summary,
                 'timing_profiles.json': timing, 'training_timing.json': training_timing(run, registrations)}
    output.mkdir(parents=True, exist_ok=False)
    for name, artifact in artifacts.items():
        dump(output/name, artifact)
    jsonl(output/'per_question.jsonl', perq); jsonl(output/'construction_error_records.jsonl', errors)
    lines = ['# Post-E030 arithmetic continuation: offline analysis', '',
             'Status: **'+summary['status']+'**. All reported primary metrics use the original strict scorer.', '',
             f"Completed views: {summary['completed_evaluations']}/{len(events)}. "
             f"Unique completed results: {historical_unique+completed_new}/4768; "
             f"charged attempts: {ledger['used']}/4864 (includes the original16 fault attempts).", '',
             'The original576 completed outputs are reused once. Missing cells and incomplete views remain unmeasured.', '',
             '| Discovery measure | C-S | C-P | B-S | B-P | Interaction |',
             '|---|---:|---:|---:|---:|---:|']
    def fmt(value):
        return 'NA' if value is None else f'{value:.4f}'
    for row in core['results']:
        if row['subgroup'] != 'full':
            continue
        estimates = [fmt(row['cells'][s].get('mean')) for s in CHILDREN]
        interaction = row['contrasts']['interaction']['mean'] if row['contrasts'] else None
        lines.append('| '+row['view']+'/'+row['metric']+' | '+' | '.join(estimates)+' | '+fmt(interaction)+' |')
    lines += ['', 'Question-paired and reference-template bootstrap intervals are in `core_2x2.json`; '
              'they do not include training-seed uncertainty. Nonsignificance does not establish equivalence.', '',
              'Parent probe pass@1 and pass@4, the descriptive target-minus-control contrast, matched sentinel '
              'changes, midpoint trajectories, and the fixed16 training diagnostic are reported separately. '
              'Compute probes are not construction accuracy.', '',
              'The training diagnostic selects four questions from each anchor-family x target-label stratum '
              '(population supports 25, 103, 29, 99). Target-degenerate questions are 8/16 of the diagnostic '
              'versus 54/256 of the training population. Scores are unweighted diagnostic summaries, '
              'not whole-training accuracy estimates.', '',
              'Construction errors distinguish exact number resources, exact target satisfaction, and explicit '
              'intermediate equations. NA remains unknown. An expression reaching the wrong target may still '
              'have correct intermediate arithmetic. Parsing alone is not verified task correctness.', '',
              'A/B reference NLL is teacher-forced and response-token weighted; A/B names the reference '
              'program family, not the prep state. Each Surface reference-family aggregate mixes eight '
              'anchor and eight non-anchor questions. Paths sees both program families, but its trained '
              'rendering can differ from reference rendering 0. These aggregates cannot identify literal '
              'memorization or unseen-path performance. Missing measurements remain NA. Recorded forward '
              'runtime appears in `reference_nll.json`; absent timing remains NA. Forward runtime is '
              'already included in process/rental charges and adds no autoregressive generations.', '',
              'Batch counts, generated records, retained tokens, padded generated tokens, generation time '
              '(including prefill), CPU scoring, and persistence timing remain distinct in `timing_profiles.json`. '
              'No separate prefill/decode timing was measured.', '']
    (output/'REPORT.md').write_text('\n'.join(lines))
    dump(output/'manifest.json', dict(source_files_sha256={str(p): sha256_file(p) for p in (
        Path('experiments/thursday_probe_v2/resume_analyze.py'), Path('experiments/thursday_probe_v2/analyze.py'),
        Path('experiments/thursday_probe/arithmetic_eval.py'),
        Path('experiments/thursday_probe_v2/resume_diagnostics.py'),
        Path('experiments/thursday_probe_v2/partial_audit.py'),
        Path('experiments/thursday_probe_v2/resumable_generation.py'),
        Path('src/trace_audit.py'), Path('src/countdown_smoke.py'), Path('src/evaluation.py'))},
        input_bindings_sha256=bindings,
        files_sha256={p.name: sha256_file(p) for p in sorted(output.iterdir())}))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer-dir', required=True)
    parser.add_argument('--run-dir', type=Path, default=RUN)
    parser.add_argument('--historical-dir', type=Path, default=HISTORICAL)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = analyze(args.tokenizer_dir, args.run_dir, args.historical_dir, args.output)
    print(json.dumps(dict(status=result['status'], accounting=result['generation_accounting']), indent=2))
