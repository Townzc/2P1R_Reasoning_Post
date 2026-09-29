"""Offline, group-paired analysis for the frozen post-E036 F/H/C diagnostic.

No weights or model forwards are used. Missing interfaces remain unmeasured;
four samples and the two counterfactual targets are nested within a number
group, never counted as independent groups. Raw operator likelihoods are not
replaced by probabilities normalized within the four-candidate set.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path

import numpy as np

from analyses.completion_contract import first_stop
from experiments.post_e036_goal_probe.scoring import OPERATORS, score
from experiments.thursday_probe.common import dump, jsonl, verify_manifest
from experiments.thursday_probe_v2.partial_audit import audit_batch_journal, incomplete_file
from scripts.audit_family_matching import verified_tokenizer
from src.sft_data import prefix, read_jsonl, sha256_file

STATES = ('C-S', 'C-P', 'B-S', 'B-P')
INTERFACES = ('F', 'H', 'C')
N_BOOTSTRAP = 10000
BOOTSTRAP_SEED = 2026091704
RELEASE = Path('experiments/post_e036_goal_probe/release_v1')
RUN = Path('runs/post_e036_goal_probe_v1')
OUTPUT = Path('reports/post_e036_goal_probe/analysis_v1')


def group_interval(values, families):
    """Equal-group mean; paired group and size-weighted family cluster bootstrap."""
    ids = sorted(values)
    if not ids:
        return dict(mean=None, groups=0, families=0, group_ci=None, family_ci=None)
    array = np.asarray([values[g] for g in ids], dtype=float)
    if not np.isfinite(array).all():
        raise ValueError('Nonfinite group measurements')
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.integers(0, len(ids), (N_BOOTSTRAP, len(ids)))
    buckets = defaultdict(list)
    for index, group in enumerate(ids):
        buckets[families[group]].append(index)
    family_ci = None
    if len(buckets) > 1:
        keys = sorted(buckets)
        totals = np.array([array[buckets[k]].sum() for k in keys])
        sizes = np.array([len(buckets[k]) for k in keys])
        clusters = rng.integers(0, len(keys), (N_BOOTSTRAP, len(keys)))
        family_ci = np.quantile(totals[clusters].sum(axis=1)/sizes[clusters].sum(axis=1),
                                [.025, .975]).tolist()
    return dict(mean=float(array.mean()), groups=len(ids), families=len(buckets),
                group_ci=np.quantile(array[draws].mean(axis=1), [.025, .975]).tolist(),
                family_ci=family_ci)


def _rate(values, numerator, denominator, families):
    return dict(numerator=int(numerator), denominator=int(denominator),
                raw_fraction=numerator/denominator if denominator else None,
                **group_interval(values, families))


def _data_index(rows):
    by_id = {row['problem_id']: row for row in rows}
    index = {(row['group_id'], row['target_index']): row for row in rows}
    families = {row['group_id']: row['skeleton_family_id'] for row in rows}
    if len(by_id) != len(rows) or len(index) != len(rows):
        raise ValueError('Duplicate registered problem/group-target identity')
    if set(index) != {(g, t) for g in families for t in (0, 1)}:
        raise ValueError('Every registered group needs both targets')
    for group, family in families.items():
        a, b = index[group, 0], index[group, 1]
        if (a['skeleton_family_id'] != family or b['skeleton_family_id'] != family or
                a['numbers'] != b['numbers'] or a['target'] == b['target'] or
                a['template'] != b['template'] or
                a.get('correct_operator', a.get('expected_operator')) ==
                b.get('correct_operator', b.get('expected_operator'))):
            raise ValueError('Counterfactual group registration differs')
    return by_id, index, families


def _record_index(records, rows, samples):
    by_id, _, families = _data_index(rows)
    indexed = {}
    for record in records:
        row = by_id[record['problem_id']]
        sample = record['sample_index']
        if type(sample) is not int or not 0 <= sample < samples:
            raise ValueError('Unexpected sample index')
        key = row['group_id'], row['target_index'], sample
        if key in indexed:
            raise ValueError('Duplicate generated group/target/sample')
        indexed[key] = record
    if set(indexed) != {(g, t, s) for g in families for t in (0, 1) for s in range(samples)}:
        raise ValueError('Complete-view metric requires every frozen group/target/sample')
    return indexed, families


def view_metrics(records, rows, samples):
    indexed, families = _record_index(records, rows, samples)
    groups = sorted(families); interface = rows[0]['interface']
    denominator = len(records)
    result = dict(groups=len(groups), targets=2*len(groups), generations=denominator,
                  samples_per_target=samples)
    for field in ('correct', 'parsed', 'completed', 'free_correct', 'uses_input_multiset',
                  'reaches_target', 'scaffold_followed', 'operator_correct',
                  'unconstrained_correct_off_template'):
        counts = Counter('NA' if r['score'].get(field) is None else
                         'true' if r['score'][field] else 'false' for r in records)
        if counts['NA'] == denominator:
            result[field] = dict(counts=dict(counts), numerator=None, denominator=denominator,
                                 raw_fraction=None, mean=None, group_ci=None, family_ci=None)
        else:
            values = {g: sum(indexed[g, t, s]['score'].get(field) is True
                             for t in (0, 1) for s in range(samples))/(2*samples) for g in groups}
            result[field] = dict(counts=dict(counts),
                                 **_rate(values, counts['true'], denominator, families))
    if samples == 4:
        solved = {g: sum(any(indexed[g, t, s]['score']['correct'] for s in range(samples))
                         for t in (0, 1))/2 for g in groups}
        result['pass_at_4'] = _rate(solved, round(sum(solved.values())*2), len(groups)*2, families)
    pairs, switches, same, assessable = {}, {}, {}, {}
    for group in groups:
        pair_flags, switch_flags, same_flags, available_flags = [], [], [], []
        for sample in range(samples):
            a, b = (indexed[group, target, sample]['score'] for target in (0, 1))
            both = bool(a['correct'] and b['correct'])
            pair_flags.append(both)
            switch_flags.append(bool(both and a.get('operator_correct') and b.get('operator_correct')
                                     and a.get('selected_operator') != b.get('selected_operator')))
            available = a.get('ordered_expression') is not None and b.get('ordered_expression') is not None
            available_flags.append(available)
            same_flags.append(bool(available and a['ordered_expression'] == b['ordered_expression'] and not both))
        pairs[group] = sum(pair_flags)/samples
        switches[group] = sum(switch_flags)/samples
        same[group] = sum(same_flags)/samples
        assessable[group] = sum(available_flags)/samples
    pair_denominator = len(groups)*samples
    result['both_targets_correct'] = _rate(pairs, round(sum(pairs.values())*samples), pair_denominator, families)
    if interface == 'H':
        result['correct_operator_switch'] = _rate(switches, round(sum(switches.values())*samples),
                                                  pair_denominator, families)
    if interface in ('F', 'H'):
        result['same_ordered_expression_failure'] = _rate(same, round(sum(same.values())*samples),
                                                          pair_denominator, families)
        result['same_ordered_expression_failure']['assessable_pairs'] = round(sum(assessable.values())*samples)
        result['same_ordered_expression_failure']['definition'] = (
            'Both answers have the same ordered AST, ignoring spaces/outer parentheses. '
            'Non-parsed pairs are unassessable, not evidence of a successful target switch.')
    result.update(stop_reasons=dict(Counter(r['stop']['stop_reason'] for r in records)),
                  failures=dict(Counter(r['score']['failure'] for r in records)),
                  resource_target_categories=dict(Counter(r['score']['resource_target_category'] for r in records)),
                  intermediate_arithmetic=dict(Counter(r['score']['intermediate_arithmetic_status'] for r in records)),
                  retained_length_quantiles=dict(zip(('min', 'p25', 'p50', 'p75', 'p95', 'max'),
                      np.quantile([len(r['generated_ids']) for r in records], [0, .25, .5, .75, .95, 1]).tolist())),
                  pairing_note='Sample index pairs independent requests; bootstrap unit is the number group.')
    return result


def rescue_loss(free_records, hole_records, free_rows, hole_rows, samples):
    f, families = _record_index(free_records, free_rows, samples)
    h, other_families = _record_index(hole_records, hole_rows, samples)
    if set(f) != set(h) or families != other_families:
        raise ValueError('F/H groups or family identities differ')
    _, free_index, _ = _data_index(free_rows)
    _, hole_index, _ = _data_index(hole_rows)
    if any((free_index[key]['numbers'], free_index[key]['target']) !=
           (hole_index[key]['numbers'], hole_index[key]['target']) for key in free_index):
        raise ValueError('F/H numbers or targets differ')
    rescued, lost = {}, {}
    for group in families:
        pairs = [(f[group, t, s]['score']['correct'], h[group, t, s]['score']['correct'])
                 for t in (0, 1) for s in range(samples)]
        rescued[group] = sum(not a and b for a, b in pairs)/(2*samples)
        lost[group] = sum(a and not b for a, b in pairs)/(2*samples)
    nr, nl = round(sum(rescued.values())*2*samples), round(sum(lost.values())*2*samples)
    return dict(rescued_F_wrong_H_correct=_rate(rescued, nr, len(f), families),
                lost_F_correct_H_wrong=_rate(lost, nl, len(f), families),
                H_minus_F=_rate({g: rescued[g]-lost[g] for g in families}, nr-nl, len(f), families),
                interpretation='Giving a template changes task difficulty and interface as well as search freedom; '
                               'this paired difference does not isolate an internal search/routing mechanism.')


def analyze_generations(completed, rows_by_interface):
    tables, comparisons = [], []
    for state in STATES:
        for decoding, samples in (('greedy', 1), ('sampled', 4)):
            for interface in (INTERFACES if samples == 1 else ('F', 'H')):
                name = f'{state}_{interface}_{decoding}'
                metric = view_metrics(completed[name], rows_by_interface[interface], samples) if name in completed else None
                tables.append(dict(evaluation=name, state=state, interface=interface, decoding=decoding,
                                   status='measured' if metric else 'not_measured_complete_view', metrics=metric))
            fn, hn = f'{state}_F_{decoding}', f'{state}_H_{decoding}'
            metric = rescue_loss(completed[fn], completed[hn], rows_by_interface['F'],
                                 rows_by_interface['H'], samples) if fn in completed and hn in completed else None
            comparisons.append(dict(state=state, decoding=decoding,
                                    status='measured' if metric else 'not_measured_paired_views', metrics=metric))
    return dict(views=tables, free_hole_comparisons=comparisons, bootstrap_replicates=N_BOOTSTRAP,
                bootstrap_seed=BOOTSTRAP_SEED, uncertainty_scope='Paired number-group and skeleton-family '
                'resampling only; excludes training-seed uncertainty. Empirical boundary intervals do not '
                'establish perfect ability or equivalence. Four sample pairs are not four independent groups.')


def _operator_context(record):
    """Check emitted full-vocabulary likelihoods without rerunning a forward."""
    candidates = record['candidates']
    by = {c['operator']: c for c in candidates}
    if len(candidates) != 4 or set(by) != set(OPERATORS):
        raise ValueError('Operator candidates must contain each registered operator once')
    logp = {op: by[op]['log_probability'] for op in OPERATORS}
    if any(type(v) not in (int, float) or not math.isfinite(v) or v > 1e-7 for v in logp.values()):
        raise ValueError('Operator log probabilities must be finite and nonpositive')
    top = max(logp.values())
    log_mass = top+math.log(sum(math.exp(v-top) for v in logp.values()))
    mass = math.exp(log_mass)
    if mass > 1+1e-6:
        raise ValueError('Disjoint candidate sequence probability mass exceeds one')
    if not math.isclose(record['candidate_probability_mass'], mass, rel_tol=1e-6, abs_tol=1e-12):
        raise ValueError('Candidate total probability mass differs from raw log probabilities')
    for op, candidate in by.items():
        for field, expected in (('probability', math.exp(logp[op])),
                                ('normalized_probability', math.exp(logp[op]-log_mass))):
            if not math.isclose(candidate[field], expected, rel_tol=1e-6, abs_tol=1e-12):
                raise ValueError('Candidate probability normalization differs')
    ids = record['candidate_ids']
    if set(ids) != set(OPERATORS) or any(not ids[op] or any(type(t) is not int or t < 0 for t in ids[op]) for op in OPERATORS):
        raise ValueError('Invalid candidate token IDs')
    if any(a != b and ids[a] == ids[b][:len(ids[a])] for a in OPERATORS for b in OPERATORS):
        raise ValueError('Candidate sequences are not prefix-free/disjoint')
    correct = record['correct_operator']
    if correct not in by:
        raise ValueError('Unregistered correct operator')
    winners = [op for op in OPERATORS if logp[op] == top]
    return dict(group_id=record['group_id'], target_index=record['target_index'],
                correct_operator=correct, candidate_log_probabilities=logp,
                candidate_probability_mass=mass, candidate_log_probability_mass=log_mass,
                correct_raw_probability=math.exp(logp[correct]),
                correct_candidate_normalized_probability=math.exp(logp[correct]-log_mass),
                correct_unique_argmax=winners == [correct], correct_in_argmax=correct in winners,
                argmax_operators=winners, candidate_count=4)


def operator_metrics(records, rows):
    _, registered, families = _data_index(rows)
    checked, unavailable = {}, []
    seen = set()
    for record in records:
        key = record['group_id'], record['target_index']
        if key in seen or key not in registered:
            raise ValueError('Duplicate or unregistered operator context')
        seen.add(key)
        expected = registered[key].get('correct_operator', registered[key].get('expected_operator'))
        if record.get('status') in ('unavailable', 'not_available'):
            if not record.get('reason'):
                raise ValueError('Unavailable operator context requires a reason')
            unavailable.append(dict(group_id=key[0], target_index=key[1], reason=record['reason']))
            continue
        if record['correct_operator'] != expected:
            raise ValueError('Operator context correct-label mismatch')
        checked[key] = _operator_context(record)
    per_group, d_values, switched, ranked = [], {}, {}, {}
    for group in sorted(families):
        if (group, 0) not in checked or (group, 1) not in checked:
            per_group.append(dict(group_id=group, status='not_measured_both_contexts', D_goal=None))
            continue
        a, b = checked[group, 0], checked[group, 1]
        o0, o1 = a['correct_operator'], b['correct_operator']
        la, lb = a['candidate_log_probabilities'], b['candidate_log_probabilities']
        d = (lb[o1]-lb[o0])-(la[o1]-la[o0])
        d_values[group] = d
        switched[group] = int(a['correct_unique_argmax'] and b['correct_unique_argmax'])
        ranked[group] = (int(a['correct_unique_argmax'])+int(b['correct_unique_argmax']))/2
        per_group.append(dict(group_id=group, status='measured', D_goal=d,
                              both_targets_correct_unique_argmax=bool(switched[group])))
    contexts = [checked[k] for k in sorted(checked)]
    paired_probability_means = {}
    for field in ('candidate_probability_mass', 'correct_raw_probability',
                  'correct_candidate_normalized_probability'):
        values = {g: (checked[g, 0][field]+checked[g, 1][field])/2 for g in d_values}
        paired_probability_means[field] = dict(**group_interval(values, families),
            numerator=sum(values.values())*2, denominator=len(values)*2)
    return dict(registered_contexts=len(registered), available_contexts=len(checked),
                recorded_contexts=len(seen), missing_contexts=len(registered)-len(seen),
                unavailable_contexts=unavailable, context_results=contexts, per_group=per_group,
                D_goal=dict(**group_interval(d_values, families), numerator=sum(d_values.values()),
                            denominator=len(d_values), units='natural-log-odds difference'),
                both_targets_correct_unique_argmax=_rate(switched, sum(switched.values()), len(switched), families),
                correct_unique_argmax_on_paired_groups=_rate(ranked, round(sum(ranked.values())*2), len(ranked)*2, families),
                paired_context_probability_means=paired_probability_means,
                available_context_ranking_counts=dict(denominator=len(contexts),
                    correct_unique_argmax=sum(c['correct_unique_argmax'] for c in contexts),
                    correct_in_argmax=sum(c['correct_in_argmax'] for c in contexts),
                    ties=sum(len(c['argmax_operators']) > 1 for c in contexts)),
                raw_candidate_probability_mass=dict(numerator=sum(c['candidate_probability_mass'] for c in contexts),
                    denominator=len(contexts), mean=(sum(c['candidate_probability_mass'] for c in contexts)/len(contexts)
                                                    if contexts else None)),
                interpretation='Raw log probabilities condition on the supplied prefix. Candidate-normalized '
                'probabilities are conditional on the four-candidate set, not full-vocabulary probabilities. '
                'D_goal uses raw log probabilities; positive D_goal alone is not full-path correctness. '
                'Missing contexts are NA; estimates explicitly use available complete target pairs.')


def audit_predictions(path, rows, event, tokenizer):
    by_id = {row['problem_id']: row for row in rows}
    records = read_jsonl(path)
    decode = lambda ids: tokenizer.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    vocab, specials = len(tokenizer), set(tokenizer.all_special_ids)
    for record in records:
        row = by_id[record['problem_id']]
        ids = record['batch_output_ids']
        stop = first_stop(ids, decode, tokenizer.eos_token_id, 512, specials | {t for t in ids if t >= vocab})
        if (record['forced_prefix'] != '' or stop != record['stop'] or
                record['generated_ids'] != ids[:stop['retained_tokens']] or
                any(t != tokenizer.eos_token_id for t in ids[stop['retained_tokens']:]) or
                record['prompt_ids'] != tokenizer.encode(prefix(row['prompt']), add_special_tokens=False) or
                record['score'] != score(row, stop) or
                any(record.get(k) != row[k] for k in ('task', 'interface', 'group_id', 'target_index'))):
            raise ValueError('Independent prompt/token/stop/scorer replay differs: '+path.name)
    _record_index(records, rows, event['samples'])
    journal = audit_batch_journal(path, records, rows, event, tokenizer)
    return records, journal


def audit_commits(path, rows, event, tokenizer, ledger, release):
    """Bind a complete publication to immutable raw/score commits and reservations."""
    from experiments.post_e036_goal_probe.generation import _descriptor, _digest, _protocol
    folder = path.with_suffix('.resume')
    manifest_path = folder/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    descriptor = manifest['descriptor']
    protocol, _ = _protocol(event, tokenizer)
    if descriptor != _descriptor(rows, event, descriptor['identity'], protocol):
        raise ValueError('Generation descriptor differs from the frozen protocol/rows')
    if descriptor['identity']['split_hash'] != sha256_file(release/'manifest.json'):
        raise ValueError('Generation split-manifest SHA differs from the frozen release')
    reservations = {r['name']: r['reserved'] for r in ledger['events']}
    before, records, raws, keys = manifest['initial_rng'], [], [], []
    files = sorted((folder/'batches').glob('*.raw.json'))
    for index, raw_path in enumerate(files):
        if raw_path.name != f'{index:06d}.raw.json':
            raise ValueError('Noncontiguous immutable batch stream')
        requests = descriptor['request_ids'][index*8:(index+1)*8]
        key = 'eval_batch_'+_digest(requests)
        identity = dict(evaluation_hash=_digest(descriptor), batch_index=index,
                        request_key=key, request_ids=requests, generations=len(requests))
        stem = folder/'batches'/f'{index:06d}'
        raw = json.loads(raw_path.read_text())
        intent = json.loads(Path(str(stem)+'.intent.json').read_text())
        reserved = json.loads(Path(str(stem)+'.reserved.json').read_text())
        scored = json.loads(Path(str(stem)+'.scored.json').read_text())
        if (not requests or raw['identity'] != identity or intent['identity'] != identity or
                reserved != identity or raw['rng_before'] != before or intent['rng_before'] != before or
                reservations.get(key) != len(requests) or scored['identity'] != identity or
                scored['raw_sha256'] != sha256_file(raw_path) or
                scored['records_sha256'] != _digest(scored['records'])):
            raise ValueError('Immutable batch/RNG/reservation/score binding differs')
        before = raw['rng_after']; records.extend(scored['records']); raws.append(raw['raw']); keys.append(key)
    if records != read_jsonl(path) or raws != read_jsonl(path.with_suffix('.raw_batches.jsonl')):
        raise ValueError('Published stream differs from immutable batches')
    return dict(status='verified', manifest_sha256=sha256_file(manifest_path),
                batches=len(raws), records=len(records), request_keys=keys,
                model_hash=descriptor['identity']['model_hash'])


def _operator_bindings(artifact, contexts, tokenizer, *, directory=None, model_hash=None, release_hash=None):
    from experiments.post_e036_goal_probe.generation import _digest
    registered = {(r['group_id'], r['target_index']): r for r in contexts}
    if len(artifact['records']) > len(contexts):
        raise ValueError('Too many operator contexts')
    for index, record in enumerate(artifact['records']):
        frozen = registered[record['group_id'], record['target_index']]
        if frozen != contexts[index]:
            raise ValueError('Operator records are not the frozen context prefix')
        if directory is not None:
            path = directory/f'{index:06d}.json'
            identity = dict(request_hash=_digest(frozen), model_hash=model_hash,
                            release_manifest_sha256=release_hash)
            if record != json.loads(path.read_text()) or record['identity'] != identity:
                raise ValueError('Operator immutable record/identity differs from aggregate')
        if record.get('status') in ('unavailable', 'not_available'):
            if frozen['available']:
                # A runtime failure may be unavailable, but must explicitly
                # preserve its reason rather than silently drop the context.
                if not record.get('reason'):
                    raise ValueError('Runtime unavailable context has no reason')
            continue
        if record.get('status') != 'available':
            raise ValueError('Operator context has an unknown status')
        if not frozen['available']:
            raise ValueError('Unavailable frozen token context was reported as measured')
        if (record['context_ids'] != frozen['context_ids'] or
                record['candidate_ids'] != frozen['candidates'] or
                record['correct_operator'] != frozen['correct_operator']):
            raise ValueError('Operator token context/candidate identity differs')
        for operator in OPERATORS:
            full = tokenizer.encode(frozen['candidate_texts'][operator], add_special_tokens=False)
            if full != record['context_ids']+record['candidate_ids'][operator]:
                raise ValueError('Operator full-encoding prefix/span replay differs')
        single = all(len(v) == 1 for v in record['candidate_ids'].values())
        calls = 1 if single else 4
        tokens = len(record['context_ids']) if single else sum(
            len(record['context_ids'])+len(v)-1 for v in record['candidate_ids'].values())
        if (record['forward_calls'] != calls or record['input_tokens'] != tokens or
                record['candidate_tokens'] != sum(map(len, record['candidate_ids'].values())) or
                not math.isfinite(record['seconds']) or record['seconds'] < 0):
            raise ValueError('Operator recorded forward/token/time accounting differs')
        if directory is not None and json.loads((directory/f'{index:06d}.intent.json').read_text()) != identity:
            raise ValueError('Operator forward intent identity differs')
    rows = artifact['records']
    available = sum(r['status'] == 'available' for r in rows)
    for field, expected in (
            ('recorded_contexts', len(rows)), ('forward_contexts', available),
            ('unavailable_contexts', len(rows)-available), ('candidate_scores', 4*available),
            ('forward_calls', sum(r['forward_calls'] for r in rows)),
            ('input_tokens', sum(r['input_tokens'] for r in rows))):
        if artifact[field] != expected:
            raise ValueError('Operator aggregate accounting differs: '+field)
    if not math.isclose(artifact['seconds'], sum(r['seconds'] for r in rows), rel_tol=1e-10, abs_tol=1e-9):
        raise ValueError('Operator aggregate forward time differs')


def analyze(run=RUN, release=RELEASE, output=OUTPUT, *, tokenizer_dir):
    from experiments.post_e036_goal_probe.data import load_operator_rows, load_rows
    run, release, output = Path(run), Path(release), Path(output)
    if output.exists():
        raise FileExistsError('Never overwrite a completed or partial analysis')
    verify_manifest(release)
    rows = {interface: load_rows(interface, release) for interface in INTERFACES}
    for interface in INTERFACES:
        _data_index(rows[interface])
    contexts = load_operator_rows(release)
    tokenizer, tokenizer_identity = verified_tokenizer(Path(tokenizer_dir))
    manifest_path, ledger_path = run/'run_manifest_final.json', run/'generation_ledger.json'
    manifest, ledger = json.loads(manifest_path.read_text()), json.loads(ledger_path.read_text())
    endpoint_path = Path('experiments/post_e036_goal_probe/endpoint_identities.json')
    endpoints = json.loads(endpoint_path.read_text())
    if manifest['release_manifest_sha256'] != sha256_file(release/'manifest.json'):
        raise ValueError('Run release-manifest identity differs')
    reservations = ledger['events']
    if (len({e['name'] for e in reservations}) != len(reservations) or
            any(type(e['reserved']) is not int or e['reserved'] <= 0 for e in reservations) or
            sum(e['reserved'] for e in reservations) != ledger['used'] or
            ledger['cap'] != 2304 or not 0 <= ledger['used'] <= ledger['cap']):
        raise ValueError('New-generation ledger is inconsistent or was mixed with the old budget')
    bindings = {str(p): sha256_file(p) for p in (manifest_path, ledger_path, release/'manifest.json', endpoint_path)}
    completed, coverage, audits, model_hashes = {}, [], {}, {}
    for state in STATES:
        for decoding, samples in (('greedy', 1), ('sampled', 4)):
            for interface in (INTERFACES if samples == 1 else ('F', 'H')):
                name = f'{state}_{interface}_{decoding}'
                path, summary_path = run/(name+'.jsonl'), run/(name+'.summary.json')
                row = dict(evaluation=name, state=state, interface=interface, decoding=decoding,
                           expected_records=len(rows[interface])*samples, status='not_run')
                summary = json.loads(summary_path.read_text()) if summary_path.exists() else None
                if summary_path.exists():
                    bindings[str(summary_path)] = sha256_file(summary_path)
                if not summary or summary['status'] != 'completed':
                    if path.exists():
                        inventory, visible = incomplete_file(path)
                        row.update(status='incomplete_not_in_metrics', inventory=inventory,
                                   published_records=len(visible))
                        bindings[str(path)] = sha256_file(path)
                    raw = sorted(path.with_suffix('.resume').glob('batches/*.raw.json'))
                    if raw:
                        row.update(status='incomplete_not_in_metrics', durable_raw_batches=len(raw),
                            durable_raw_records=sum(len(json.loads(p.read_text())['raw']['problem_ids']) for p in raw))
                    coverage.append(row)
                    continue
                if (not path.exists() or summary['predictions_sha256'] != sha256_file(path) or
                        summary['completed_records'] != row['expected_records']):
                    raise ValueError('Completed summary prediction SHA or count differs: '+name)
                # Use the exact registered event saved in the immutable descriptor;
                # extra metadata keys remain covered by that hash.
                event = json.loads((path.with_suffix('.resume')/'manifest.json').read_text())['descriptor']['event']
                if (event['name'] != name or event['state'] != state or event['interface'] != interface or
                        event['samples'] != samples or event['sampling'] != (samples == 4) or
                        event['questions'] != len(rows[interface]) or event['generations'] != row['expected_records']):
                    raise ValueError('Completed event differs from fixed F/H/C queue')
                records, journal = audit_predictions(path, rows[interface], event, tokenizer)
                commit = audit_commits(path, rows[interface], event, tokenizer, ledger, release)
                expected_model = endpoints[state]['parameter_digest']['sha256']
                if (commit['model_hash'] != expected_model or
                        summary['adapter']['sha256'] != expected_model):
                    raise ValueError('Generation endpoint differs from frozen E033-E036 identity')
                if state in model_hashes and model_hashes[state] != commit['model_hash']:
                    raise ValueError('A frozen endpoint identity changed between views')
                model_hashes[state] = commit['model_hash']
                completed[name] = records
                audits[name] = dict(journal=journal, immutable_commits=commit)
                bindings[str(path)] = sha256_file(path)
                bindings[str(path.with_suffix('.raw_batches.jsonl'))] = sha256_file(path.with_suffix('.raw_batches.jsonl'))
                row.update(status='complete_independently_verified', completed_records=len(records))
                coverage.append(row)
    metrics = analyze_generations(completed, rows)
    operator_results = []
    for state in STATES:
        path = run/'operator_scores'/(state+'.json')
        artifact = json.loads(path.read_text()) if path.exists() else None
        if artifact:
            if artifact.get('release_manifest_sha256') != sha256_file(release/'manifest.json'):
                raise ValueError('Operator artifact release binding differs')
            expected_model = endpoints[state]['parameter_digest']['sha256']
            if artifact['state'] != state or artifact['model_hash'] != expected_model:
                raise ValueError('Operator endpoint differs from frozen E033-E036 identity')
            _operator_bindings(artifact, contexts, tokenizer, directory=run/'operator_scores'/state,
                               model_hash=expected_model, release_hash=sha256_file(release/'manifest.json'))
            bindings[str(path)] = sha256_file(path)
        measured = operator_metrics(artifact['records'] if artifact else [], rows['H'])
        operator_results.append(dict(state=state, status='recorded' if artifact else 'not_measured',
                                     metrics=measured,
                                     forward_metadata={k: v for k, v in artifact.items() if k != 'records'} if artifact else None))
    expected = sum(c['expected_records'] for c in coverage)
    complete_count = sum(len(rs) for rs in completed.values())
    all_operators_recorded = all(r['metrics']['recorded_contexts'] == len(contexts) for r in operator_results)
    complete = len(completed) == len(coverage) and all_operators_recorded
    if manifest['status'] == 'completed' and not complete:
        raise ValueError('Completed run is missing a registered generation view or operator context')
    summary = dict(status='all_registered_outputs_verified' if complete else 'partial_coverage_verified',
        completed_generation_views=len(completed), registered_generation_views=len(coverage),
        completed_unique_generations=complete_count, registered_generations=expected,
        charged_generation_reservations=ledger['used'], generation_cap=ledger['cap'],
        old_generation_ledger_modified=False, training_runs=0, analysis_model_calls=0,
        tokenizer=tokenizer_identity, generation_audits=audits, model_hashes=model_hashes,
        verification_scope='Independent prompt/token/stop/strict score replay, immutable request/RNG/hash '
        'bindings and emitted operator probability arithmetic. No CUDA generation or model forward is replayed.')
    output.mkdir(parents=True, exist_ok=False)
    dump(output/'SUMMARY.json', summary)
    dump(output/'COVERAGE.json', coverage)
    dump(output/'FREE_HOLE_COMPUTE_RESULTS.json', metrics)
    dump(output/'PAIRED_GOAL_SWITCH.json', dict(
        views=[dict(evaluation=r['evaluation'], status=r['status'], metrics=(
            {key: value for key, value in r['metrics'].items() if key in (
                'both_targets_correct', 'correct_operator_switch', 'same_ordered_expression_failure')}
            if r['metrics'] else None)) for r in metrics['views']],
        free_hole_comparisons=metrics['free_hole_comparisons']))
    dump(output/'OPERATOR_TARGET_SENSITIVITY.json', dict(results=operator_results,
        bootstrap_replicates=N_BOOTSTRAP, bootstrap_seed=BOOTSTRAP_SEED,
        uncertainty_scope=metrics['uncertainty_scope']))
    jsonl(output/'SCORED_OUTPUTS.jsonl', [dict(evaluation=name, **record)
        for name, records in completed.items() for record in records])
    errors = ['# Diagnostic error inventory', '',
        'Every failed generated answer remains in its measured denominator. '
        'This inventory does not select examples for a new run.', '',
        '| Evaluation | Failure | Count |', '|---|---|---:|']
    for row in metrics['views']:
        if row['metrics']:
            errors.extend('| '+row['evaluation']+' | '+failure+' | '+str(count)+' |'
                          for failure, count in sorted(row['metrics']['failures'].items()) if failure != 'none')
    errors += ['', 'Full per-output parsed/resource/target/template and local-arithmetic fields are in '
               '`SCORED_OUTPUTS.jsonl`; NA is not a verified arithmetic error.', '']
    (output/'ERROR_CASES.md').write_text('\n'.join(errors))
    (output/'REPORT.md').write_text(_report(summary, metrics, operator_results))
    dump(output/'manifest.json', dict(input_files_sha256=bindings,
        source_files_sha256={str(p): sha256_file(p) for p in (
            Path('experiments/post_e036_goal_probe/analyze.py'), Path('experiments/post_e036_goal_probe/scoring.py'),
            Path('experiments/post_e036_goal_probe/generation.py'), Path('src/evaluation.py'),
            Path('src/trace_audit.py'), Path('analyses/completion_contract.py'))},
        files_sha256={p.name: sha256_file(p) for p in sorted(output.iterdir())}))
    return summary


def _report(summary, metrics, operators):
    lines = ['# Frozen-endpoint goal-switch diagnostic', '',
             'Status: **'+summary['status']+'**. No training was performed.', '',
             '| State | Interface | Decoding | Strict correct / outputs | Both targets correct / pairs |',
             '|---|---|---|---:|---:|']
    for row in metrics['views']:
        m = row['metrics']
        cells = ([f"{m[k]['numerator']}/{m[k]['denominator']}" for k in ('correct', 'both_targets_correct')]
                 if m else ['NA', 'NA'])
        lines.append('| '+' | '.join([row['state'], row['interface'], row['decoding']]+cells)+' |')
    lines += ['', 'Two targets and four stochastic samples are nested within each number group. '
        'Intervals resample groups and skeleton families, not individual outputs or training seeds. '
        'Missing views remain NA; invalid and truncated outputs stay in measured denominators.', '',
        'F accepts any legal correct construction. H additionally requires the exact ordered template '
        'and its unique correct operator. C measures expression evaluation only. Template rescue changes '
        'difficulty and interface as well as search freedom; it does not identify an internal mechanism.', '',
        'Operator scores are conditional on a supplied valid prefix. Raw full-vocabulary log probabilities, '
        'candidate total probability mass, and within-candidate normalized probabilities remain distinct. '
        'Correct ranking or positive D_goal alone does not establish free-generation competence.', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=RUN)
    parser.add_argument('--release', type=Path, default=RELEASE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--tokenizer-dir', required=True)
    args = parser.parse_args()
    result = analyze(args.run_dir, args.release, args.output, tokenizer_dir=args.tokenizer_dir)
    print(json.dumps({k: result[k] for k in ('status', 'completed_generation_views', 'completed_unique_generations')}))
