"""Strict offline analysis of decision-supervision continuations.

All mathematical scoring and stop handling retain the frozen E037 contracts.
Literal reference mismatch is not semantic failure; missing evidence stays NA.
Six states share bootstrap draws at the number-group and skeleton-family levels.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import json
import math
from pathlib import Path
import re

import numpy as np
from experiments.post_e037_goal_training import analyze as previous
from experiments.post_e036_goal_probe.scoring import score
from experiments.thursday_probe.common import digest, dump, jsonl, verify_manifest
from scripts.audit_family_matching import verified_tokenizer
from src.sft_data import encode_row, prefix, read_jsonl, sha256_file
from analyses.completion_contract import first_stop
from experiments.thursday_probe_v2.partial_audit import audit_batch_journal
from src.trace_audit import audit_trace

STATES = ('E038', 'E039', 'S-U', 'S-D', 'P-U', 'P-D')
ARMS = STATES[2:]
N_BOOTSTRAP = 10000
BOOTSTRAP_SEED = 2026091714
ROOT = Path('experiments/post_e039_decision_supervision')
RELEASE = ROOT/'release_v1'
RUN = Path('runs/post_e039_decision_supervision_v1')
OUTPUT = Path('reports/post_e039_decision_supervision')
PARENT_SHA = {
    'E038': '92da3a11e65e0de78012b6ab38d117554faa929f700dd95ed3f2df3c611fc5ae',
    'E039': 'a97f622c76c5817f8f283aa2f0034e19d438e8dd0bbb91026d443f3ba2f23bba',
}
DATA_KEYS = {
    'eval_F': ('eval', 'F'), 'eval_H': ('eval', 'H'),
    'train_F': ('train_all', 'F'), 'train_F64': ('endpoint64', 'F'),
    'midpoint_F': ('midpoint', 'F'), 'train_H': ('train32', 'H'),
    'midpoint_H': ('midpoint', 'H'),
}
UNCERTAINTY = (
    'Paired number-group bootstrap, 10000 draws, seed 2026091714, with all six states '
    'resampled jointly; skeleton-family clustering is a sensitivity analysis. Targets '
    'and samples remain nested. Intervals exclude training-seed, parent-seed and data-assignment '
    'uncertainty. The two recipes are not two seeds. Exploratory intervals are not '
    'multiplicity-adjusted; a zero-containing interval is not evidence of equivalence, '
    'and an empirical [0,0] interval is not proof of population zero.')
CONTRASTS = {
    'delta_S': {'S-D': 1., 'S-U': -1.},
    'delta_P': {'P-D': 1., 'P-U': -1.},
    'equal_recipe_mean': {'S-D': .5, 'S-U': -.5, 'P-D': .5, 'P-U': -.5},
    'recipe_heterogeneity_delta_P_minus_delta_S': {'P-D': 1., 'P-U': -1., 'S-D': -1., 'S-U': 1.},
    'S_U_minus_parent': {'S-U': 1., 'E038': -1.},
    'S_D_minus_parent': {'S-D': 1., 'E038': -1.},
    'P_U_minus_parent': {'P-U': 1., 'E039': -1.},
    'P_D_minus_parent': {'P-D': 1., 'E039': -1.},
    'parent_P_minus_S_exploratory': {'E039': 1., 'E038': -1.},
}


def _indices(records, rows, samples):
    """Support both paired evaluation and true one-prompt F training items."""
    by_id = {r['problem_id']: r for r in rows}
    if len(by_id) != len(rows) or not rows:
        raise ValueError('Empty or duplicate frozen problem identity')
    group_rows, families = defaultdict(list), {}
    for row in rows:
        g = row['group_id']; family = row.get('skeleton_family_id')
        if not family:
            raise ValueError('Missing frozen family identity')
        if g in families and families[g] != family:
            raise ValueError('Inconsistent family within group')
        families[g] = family; group_rows[g].append(row)
    wanted = {(r['problem_id'], s) for r in rows for s in range(samples)}
    indexed = {}
    for record in records:
        key = record['problem_id'], record['sample_index']
        if type(key[1]) is not int or key not in wanted:
            raise ValueError('Unregistered problem/sample identity')
        if key in indexed:
            raise ValueError('Duplicate generated problem/sample identity')
        indexed[key] = record
    if set(indexed) != wanted:
        raise ValueError('Complete-view metric requires every frozen problem/sample')
    return indexed, group_rows, families


def _paired_rows(rows):
    previous._data_index(rows)
    return True


def _group_values(records, rows, samples, metric):
    indexed, groups, families = _indices(records, rows, samples)
    if metric in ('both_targets_correct', 'pass_at_4'):
        _paired_rows(rows)
    values = {}
    for g, items in groups.items():
        flags = [[indexed[r['problem_id'], s]['score']['correct'] is True
                  for s in range(samples)] for r in items]
        if metric == 'both_targets_correct':
            if samples != 1: raise ValueError('Primary J_H is greedy only')
            values[g] = float(all(f[0] for f in flags))
        elif metric == 'pass_at_4':
            if samples != 4: raise ValueError('pass@4 requires four samples')
            values[g] = sum(any(f) for f in flags)/len(items)
        else:
            values[g] = sum(indexed[r['problem_id'], s]['score'].get(metric) is True
                            for r in items for s in range(samples))/(len(items)*samples)
    return values, families


def _joint_arrays(values, families, state_order, contrasts):
    ids = sorted(families)
    if not ids or any(set(values[state]) != set(ids) for state in state_order):
        raise ValueError('Joint inference requires identical complete groups in every state')
    array = np.asarray([[values[s][g] for s in state_order] for g in ids], dtype=float)
    if not np.isfinite(array).all(): raise ValueError('Nonfinite group measurement')
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.integers(0, len(ids), (N_BOOTSTRAP, len(ids)))
    group_draws = array[draws].mean(axis=1)
    buckets = defaultdict(list)
    for i, g in enumerate(ids): buckets[families[g]].append(i)
    family_draws = None
    if len(buckets) > 1:
        keys = sorted(buckets)
        totals = np.asarray([array[buckets[k]].sum(axis=0) for k in keys])
        sizes = np.asarray([len(buckets[k]) for k in keys])
        draws = rng.integers(0, len(keys), (N_BOOTSTRAP, len(keys)))
        family_draws = totals[draws].sum(axis=1)/sizes[draws].sum(axis=1)[:, None]
    def estimate(coeff):
        weights = np.asarray([coeff.get(s, 0.) for s in state_order])
        return dict(mean=float(array.mean(axis=0) @ weights),
            group_ci=np.quantile(group_draws @ weights, [.025,.975]).tolist(),
            family_ci=(np.quantile(family_draws @ weights,[.025,.975]).tolist()
                       if family_draws is not None else None),
            groups=len(ids), families=len(buckets))
    return dict(states={s: estimate({s:1.}) for s in state_order},
        contrasts={k: dict(coefficients=v, **estimate(v)) for k,v in contrasts.items()},
        group_rows=[dict(group_id=g, family=families[g], values={s:values[s][g] for s in state_order}) for g in ids],
        bootstrap_replicates=N_BOOTSTRAP, bootstrap_seed=BOOTSTRAP_SEED,
        joint_state_order=list(state_order), uncertainty_scope=UNCERTAINTY)


def joint_six_state_contrasts(values, families):
    if set(values) != set(STATES):
        raise ValueError('Main inference requires all six registered states; missing is not zero')
    return _joint_arrays(values, families, STATES, CONTRASTS)


def group_interval(values, families):
    if not values:
        return dict(mean=None, group_ci=None, family_ci=None, groups=0, families=0)
    return _joint_arrays({'view':values}, {g:families[g] for g in values}, ('view',), {})['states']['view']


def view_metrics(records, rows, samples):
    indexed, groups, families = _indices(records, rows, samples)
    result = dict(groups=len(groups), questions=len(rows), generations=len(records),
                  samples_per_question=samples)
    for field in ('correct','parsed','completed','free_correct','uses_input_multiset',
                  'reaches_target','scaffold_followed','operator_correct'):
        counts=Counter('NA' if r['score'].get(field) is None else str(bool(r['score'][field])).lower() for r in records)
        values,_=_group_values(records,rows,samples,field)
        result[field]=dict(counts=dict(counts), numerator=counts['true'],denominator=len(records),
            raw_fraction=counts['true']/len(records), **group_interval(values,families))
        if counts['NA']==len(records):
            result[field].update(numerator=None,raw_fraction=None,mean=None,group_ci=None,family_ci=None)
    is_paired=all(len(rs)==2 and {r['target_index'] for r in rs}=={0,1} for rs in groups.values())
    if is_paired:
        _paired_rows(rows)
        if samples==1:
            vals,_=_group_values(records,rows,samples,'both_targets_correct')
            result['both_targets_correct']=dict(numerator=int(sum(vals.values())),denominator=len(groups),**group_interval(vals,families))
        if samples==4:
            vals,_=_group_values(records,rows,samples,'pass_at_4')
            result['pass_at_4']=dict(numerator=round(2*sum(vals.values())),denominator=len(rows),**group_interval(vals,families))
    result.update(stop_reasons=dict(Counter(r['stop']['stop_reason'] for r in records)),
        failures=dict(Counter(r['score']['failure'] for r in records)),
        resource_target_categories=dict(Counter(r['score']['resource_target_category'] for r in records)),
        intermediate_arithmetic=dict(Counter(r['score']['intermediate_arithmetic_status'] for r in records)),
        retained_length_quantiles=dict(zip(('min','p25','p50','p75','p95','max'),
            np.quantile([len(r['generated_ids']) for r in records],[0,.25,.5,.75,.95,1]).tolist())))
    if rows[0]['interface']=='H':
        by_id={r['problem_id']:r for r in rows}
        result['interface_error_categories']=dict(Counter(previous.hole_error_category(r,by_id[r['problem_id']]) for r in records))
    return result


def training_metrics(records, rows, samples, state):
    result=view_metrics(records,rows,samples)
    result['scope']='Fixed training-instance diagnostic; not held-out generalization and never a checkpoint-selection gate.'
    if rows[0]['interface']=='F':
        result['training_pool']='Actual shared F replay prompts, deduplicated by exact prompt token sequence.'
        result['H_to_F_transfer']=False
    else:
        indexed,_,_=_indices(records,rows,samples)
        single=state in ('E038','S-U','S-D')
        result['target_exposure']={}
        for label,is_anchor in (('anchor',True),('countergoal',False)):
            subset=[r for r in rows if r['is_anchor'] is is_anchor]
            total=len(subset)*samples
            correct=sum(indexed[r['problem_id'],s]['score']['correct'] for r in subset for s in range(samples))
            result['target_exposure'][label]=dict(numerator=correct,denominator=total,
                H_target_supervised=(is_anchor or not single),fraction=correct/total if total else None)
        result['training_pool']='Stratified H training groups. Single countergoals were not supervised; paired countergoals were supervised.'
    return result


def literal_divergence(generated_ids, reference_ids):
    """Longest exact shared prefix among frozen references; never a correctness score."""
    if not reference_ids:
        return dict(status='unknown',reason='no_frozen_reference',token_index=None)
    matches=[]
    for ref in reference_ids:
        index=0
        while index<min(len(generated_ids),len(ref)) and generated_ids[index]==ref[index]: index+=1
        matches.append(index)
    chosen=max(range(len(matches)),key=lambda i:(matches[i],-i)); index=matches[chosen]; ref=reference_ids[chosen]
    equal=index==len(generated_ids)==len(ref)
    return dict(status='identical_reference' if equal else 'literal_difference',
        token_index=None if equal else index,reference_index=chosen,reference_count=len(reference_ids),
        generated_token=generated_ids[index] if index<len(generated_ids) else None,
        reference_token=ref[index] if index<len(ref) else None,
        interpretation='Text/token alignment only; a different legal F program remains correct.')


def semantic_divergence(row, record):
    """Report certifiable claims, without inventing the first hidden decision.

A wrong completed final expression is certified only at the final answer. A
false displayed equality is independent evidence. Unsupported earlier language
prevents labeling the first *true* semantic error; F dead-end prefixes remain
unknown because no full-prefix enumerator is invoked in this analysis.
"""
    text=record['stop']['answer_segment']
    trace=audit_trace(text,row['numbers'],Fraction(row['target']))
    evidence=[]
    for eq in trace['equations']:
        if eq['status']=='inconsistent':
            evidence.append(dict(line=eq['line'],kind='false_or_undefined_local_equation',text=eq['text']))
    s=record['score']; answers=list(re.finditer(r'(?m)^\s*Answer:\s*([^\n]+)',text))
    if s['parsed'] and not s['answer_correct_ignoring_stop'] and answers:
        match=answers[-1]
        evidence.append(dict(line=text[:match.start()].count('\n')+1,
            kind='strict_final_expression_violation',text=match.group(0)))
    evidence.sort(key=lambda e:e['line'])
    earliest=evidence[0] if evidence else None
    # Even locally true preceding statements may alter the input program or
    # resource derivation. No claim that the first certified line is first cause.
    return dict(first_certified_error=earliest,certified_errors=evidence,
        first_semantic_error=dict(status='unknown',line=None,
            reason='Earliest semantic commitment is not certified by literal matching or local-equation checks.'),
        F_prefix_dead_end=dict(status='unknown' if row['interface']=='F' else 'not_applicable',
            reason='No exhaustive prefix completion certificate; reference mismatch is insufficient.'),
        final_strict_correct=s['correct'],final_value_correct_ignoring_stop=s['answer_correct_ignoring_stop'],
        local_equations_status=trace['local_equations_status'],unknown_lines=trace['unknown_lines'],
        conclusion=('valid_alternative_F_is_accepted' if row['interface']=='F' and s['correct'] else
                    'certified_error_evidence' if earliest else 'unknown_or_no_certified_error'))


def generated_first_decision(row, text, references):
    """Certify H's first operation only on an exact valid earlier reference prefix.

    A formatting/path change before that point is unknown, not a semantic error.
    F has no single required reference path and is never assigned this H label.
    """
    if row['interface']!='H':
        return dict(status='not_applicable',reason='F permits arbitrary valid constructions')
    from .decision_spans import render_with_provenance
    from src.countdown_smoke import safe_parse
    candidates=[]
    for style in (0,1):
        response,atoms=render_with_provenance(safe_parse(row['expression']),style,tuple(row['hole_path']))
        if response not in references: continue
        dependent=[atom for atom in atoms if atom['depends_on_hole']]
        if not dependent or dependent[0]['kind']!='program_operator':
            raise ValueError('Reference first semantic decision is not the frozen operation')
        atom=dependent[0];start,end=atom['response_char_span']
        if text[:start]!=response[:start] or len(text)<end: continue
        actual=text[start:end]
        if actual not in ('+','-','*','/'):
            continue
        candidates.append(dict(status='same_valid_reference_prefix',rendering_id=style,
            response_char_span=[start,end],selected_operator=actual,
            correct_operator=row['correct_operator'],correct=actual==row['correct_operator'],
            prior_semantic_commitments_match_reference=True))
    if len(candidates)>1 and len({c['selected_operator'] for c in candidates})>1:
        raise ValueError('Ambiguous first-decision alignment')
    return candidates[0] if candidates else dict(status='unknown',
        reason='No exact valid reference prefix through the first decision; literal divergence alone is not semantic error.')


def per_problem(event, rows, records, tokenizer):
    by_id={r['problem_id']:r for r in rows}
    result=[]
    for record in records:
        row=by_id[record['problem_id']]
        refs=row.get('reference_responses',[])
        if isinstance(refs,dict):
            recipe='single' if event['state'] in ('E038','S-U','S-D') else 'paired'
            refs=refs.get(recipe,[])
        encoded_refs=[encode_row(dict(row,response=ref),tokenizer,1024) for ref in refs]
        ref_ids=[r['input_ids'][r['n_prompt']:] for r in encoded_refs]
        semantic=semantic_divergence(row,record)
        decision=generated_first_decision(row,record['stop']['answer_segment'],refs)
        if decision.get('status')=='same_valid_reference_prefix' and decision['correct'] is False:
            semantic['first_semantic_error']=dict(status='certified_wrong_first_H_decision',
                response_char_span=decision['response_char_span'],
                reason='Earlier emitted text exactly matches a valid reference with no earlier hole-dependent commitment.')
        result.append(dict(evaluation=event['name'],state=event['state'],view=event['view'],
            interface=row['interface'],data_key=event['data_key'],checkpoint_step=event['checkpoint_step'],
            problem_id=row['problem_id'],group_id=row['group_id'],target_index=row['target_index'],
            sample_index=record['sample_index'],numbers=row['numbers'],target=row['target'],
            template=row.get('template'),is_anchor=row.get('is_anchor'),score=record['score'],
            stop=record['stop'],generated_ids=record['generated_ids'],
            first_literal_divergence=literal_divergence(record['generated_ids'],ref_ids),
            generated_first_decision=decision,semantic_diagnosis=semantic))
    return result


def audit_commits(path, rows, event, tokenizer, ledger, release):
    """Bind a complete publication to immutable raw/score commits and reservations."""
    from experiments.post_e039_decision_supervision.generation import _descriptor, _digest, _protocol
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


def audit_predictions(path, rows, event, tokenizer, *, both_targets=True):
    """E037 replay contract, also usable on one physical target substream."""
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
    wanted = [(row['problem_id'], s) for row in rows for s in range(event['samples'])]
    if [(r['problem_id'], r['sample_index']) for r in records] != wanted:
        raise ValueError('Published output is not the complete frozen row/sample order')
    if both_targets:
        previous._record_index(records, rows, event['samples'])
    return records, audit_batch_journal(path, records, rows, event, tokenizer)


def audit_completed_view(path, rows, event, summary, tokenizer, ledger, release, expected_model):
    from .generation import _digest, SEED, target_seed
    if (summary['status'] != 'completed' or summary['completed_records'] != len(rows)*event['samples'] or
            summary['predictions_sha256'] != sha256_file(path) or
            summary['adapter']['sha256'] != expected_model):
        raise ValueError('Completed view count/hash/model identity differs: '+path.name)
    if not event['sampling']:
        saved_event = json.loads((path.with_suffix('.resume')/'manifest.json').read_text())['descriptor']['event']
        if any(saved_event.get(k) != v for k, v in event.items()):
            raise ValueError('Saved event differs from frozen queue')
        records, journal = audit_predictions(path, rows, saved_event, tokenizer, both_targets=False)
        commit = audit_commits(path, rows, saved_event, tokenizer, ledger, release)
        if commit['model_hash'] != expected_model:
            raise ValueError('Generation descriptor model differs from checkpoint')
        return records, dict(journal=journal, immutable_commits=commit)
    folder = path.with_suffix('.targets')
    binding = json.loads((folder/'manifest.json').read_text())
    saved_event = binding['event']
    if (any(saved_event.get(k) != v for k, v in event.items()) or
            binding != json.loads(path.with_suffix('.generation.json').read_text()) or
            binding['rows_sha256'] != _digest(rows) or binding['model_hash'] != expected_model or
            binding['split_hash'] != sha256_file(release/'manifest.json') or
            binding['base_seed'] != SEED or binding['mode'] != 'independent_target_substreams' or
            binding['target_seeds'] != {str(i): target_seed(i) for i in (0, 1)}):
        raise ValueError('Logical target-substream manifest differs')
    streams = summary['substreams']
    if [s['target_index'] for s in streams] != [0, 1]:
        raise ValueError('Missing, duplicated or reordered target streams')
    merged, audits = {}, []
    for index, stream in enumerate(streams):
        subset = [r for r in rows if r['target_index'] == index]
        subpath = folder/f't{index}.jsonl'
        subsummary_path = subpath.with_suffix('.summary.json')
        sm = json.loads(subsummary_path.read_text())
        subevent = dict(saved_event, name=saved_event['name']+f'_t{index}', questions=len(subset),
            generations=len(subset)*4, expected_records=len(subset)*4,
            evaluation_seed=target_seed(index), target_index=index)
        if (stream['seed'] != target_seed(index) or stream['status'] != 'completed' or
                stream['path'] != str(subpath.relative_to(path.parent)) or
                stream['summary_path'] != str(subsummary_path.relative_to(path.parent)) or
                stream['completed_records'] != len(subset)*4 or
                stream['predictions_sha256'] != sha256_file(subpath) or
                stream['manifest_sha256'] != sha256_file(subpath.with_suffix('.resume')/'manifest.json') or
                any(sm.get(k) != v for k, v in subevent.items()) or
                any(sm.get(k) != v for k, v in stream.items()) or
                sm['adapter_sha256'] != expected_model):
            raise ValueError('Target-substream summary binding differs')
        rs, journal = audit_predictions(subpath, subset, subevent, tokenizer, both_targets=False)
        commit = audit_commits(subpath, subset, subevent, tokenizer, ledger, release)
        if commit['model_hash'] != expected_model:
            raise ValueError('Target-substream model differs')
        for record in rs:
            merged[record['problem_id'], record['sample_index']] = record
        audits.append(dict(target_index=index, seed=target_seed(index), journal=journal, immutable_commits=commit))
    records = read_jsonl(path)
    if records != [merged[row['problem_id'], s] for row in rows for s in range(4)]:
        raise ValueError('Logical sampled publication differs from independently verified target streams')
    previous._record_index(records, rows, 4)
    return records, dict(mode='independent_target_substreams', substreams=audits,
                         logical_manifest_sha256=sha256_file(folder/'manifest.json'))



def analyze_generations(completed, rows_by_key, events):
    """Missing views are NA; only complete immutable views enter estimates."""
    views=[]
    for event in events:
        rows=rows_by_key[event['data_key']]; records=completed.get(event['name'])
        metrics=None
        if records is not None:
            metrics=(view_metrics(records,rows,event['samples']) if event['data_key'].startswith('eval_') else
                     training_metrics(records,rows,event['samples'],event['state']))
        views.append(dict(**event,status='measured' if metrics is not None else 'not_measured_complete_view',metrics=metrics))
    contrasts=[]
    for interface,decoding,samples,metric,role in (
        ('H','greedy',1,'both_targets_correct','primary_J_H'),
        ('F','sampled',4,'correct','secondary_F_sampled_pass_at_1'),
        ('F','greedy',1,'correct','supporting_F_greedy'),
        ('F','sampled',4,'pass_at_4','supporting_F_pass_at_4'),
        ('H','greedy',1,'correct','supporting_H_per_target'),
        ('H','greedy',1,'scaffold_followed','supporting_H_scaffold')):
        chosen=[e for e in events if e['data_key']=='eval_'+interface and e['decoding']==decoding]
        if len(chosen)!=6 or {e['state'] for e in chosen}!=set(STATES):
            raise ValueError('Frozen queue must register all six fresh-pool states')
        missing=[e['name'] for e in chosen if e['name'] not in completed]
        result=None
        if not missing:
            values={}; families=None
            for event in chosen:
                values[event['state']],f=_group_values(completed[event['name']],rows_by_key[event['data_key']],samples,metric)
                if families is not None and families!=f: raise ValueError('Six-state group/family registration differs')
                families=f
            result=joint_six_state_contrasts(values,families)
        contrasts.append(dict(role=role,interface=interface,decoding=decoding,metric=metric,
            status='measured' if result else 'not_measured_all_six_complete_views',missing_views=missing,result=result))
    return dict(views=views,contrasts=contrasts,uncertainty_scope=UNCERTAINTY,
        midpoint_scope='Fixed step64 dynamics only; formal endpoint step128; no selection by outcomes.',
        old_recipe_result='Previous E038/E039 paired-minus-single negative/uncertain primary results are unchanged. '
            'Current primary treatment is decision-weighted minus ordinary-CE continuation within each recipe.')


def _fraction(metric):
    return 'NA' if metric is None or metric.get('numerator') is None else f"{metric['numerator']}/{metric['denominator']}"


def _stage_a_report(views, problems, diagnostics):
    stage=[v for v in views if v['state'] in STATES[:2] and not v['data_key'].startswith('eval_')]
    lines=['# Stage A: actual training fit and first-decision evidence','',
        'Actual F replay prompts are deduplicated by exact training prompt tokens. This is separate from '
        'H-to-F transfer and fresh-instance evaluation. H anchors/countergoals retain their supervision labels. '
        'No metric is a training or checkpoint-selection gate.','',
        '| State | Pool | Strict correct / all outputs | Anchor | Countergoal |',
        '|---|---|---:|---:|---:|']
    for v in stage:
        m=v['metrics']; exp=m.get('target_exposure',{}) if m else {}
        lines.append(f"| {v['state']} | {v['data_key']} | {_fraction(m['correct']) if m else 'NA'} | {_fraction(exp.get('anchor'))} | {_fraction(exp.get('countergoal'))} |")
    stage_names={v['name'] for v in stage}
    measured=[p for p in problems if p['evaluation'] in stage_names]
    lines+=['',f"Stored Stage A outputs analyzed: {len(measured)}. First literal token differences: "
            f"{sum(p['first_literal_divergence']['status']=='literal_difference' for p in measured)}. "
            f"Outputs with certified error evidence: {sum(p['semantic_diagnosis']['first_certified_error'] is not None for p in measured)}.",'',
        'A different valid F expression is accepted. Literal mismatch does not locate a semantic mistake. '
        'False displayed equalities and strict final violations are recorded as certified evidence; unsupported '
        'earlier reasoning leaves the first true semantic error unknown. No F prefix is called a dead end '
        'without an exhaustive completion certificate. PER_PROBLEM.jsonl retains these distinctions.','',
        'Reference span diagnostics use unweighted likelihood, regardless of training objective. Whole-response '
        'NLL does not identify the decisive token loss; H source reference sets differ across recipes. '
        'Missing or unavailable span/alignment evidence is NA, never fabricated from generation accuracy.','',
        f"Forward diagnostic views registered: {len(diagnostics['views'])}. Details and raw source bindings are in DECISION_DIAGNOSTICS.json.", '',
        '| State | Reference pool | Records | Full NLL | First decision NLL | Other response NLL |',
        '|---|---|---:|---:|---:|---:|']
    for item in diagnostics['views']:
        if item['state'] not in STATES[:2] or item.get('kind') not in ('reference_H','reference_F','train_H'):
            continue
        parts=item.get('partitions',{}) if item['status']=='completed' else {}
        cells=[]
        for key in ('full','decision_mask','rest'):
            value=parts.get(key,{}).get('mean_nll')
            cells.append('NA' if value is None else f'{value:.6f}')
        lines.append('| '+' | '.join([item['state'],item['kind'],str(item.get('completed_records',0))]+cells)+' |')
    lines+=['','reference_H/F are each arm’s actual training references. train_H is the separate fixed '
        'style0 diagnostic reference; its single countergoals are unsupervised and are not included in '
        'training NLL. F has no decision weighting mask. Prefix-matched emitted H decisions: '
        f"{sum(p['generated_first_decision']['status']=='same_valid_reference_prefix' for p in measured)}; "
        'all other H trajectory decision alignments remain unknown.','']
    return '\n'.join(lines)


def _results_report(summary,tables):
    lines=['# Decision-supervision continuation results','',f"Status: **{summary['status']}**. Offline analysis made no model calls.",'',
        'The primary treatment is D minus U within S and P. The equal-recipe mean is descriptive across two '
        'recipes, not two training seeds. Parent comparisons include extra optimization. Previous E038/E039 '
        'paired-versus-single conclusions remain unchanged.','',
        '| Outcome | Contrast | Difference [95% group interval] | Family sensitivity |',
        '|---|---|---:|---:|']
    for item in tables['contrasts']:
        if item['role'] not in ('primary_J_H','secondary_F_sampled_pass_at_1'): continue
        for name in ('delta_S','delta_P','equal_recipe_mean'):
            x=item['result']['contrasts'][name] if item['result'] else None
            value=(f"{x['mean']:+.4f} [{x['group_ci'][0]:+.4f}, {x['group_ci'][1]:+.4f}]" if x else 'NA')
            family=(f"[{x['family_ci'][0]:+.4f}, {x['family_ci'][1]:+.4f}]" if x and x['family_ci'] else 'NA')
            lines.append(f"| {item['role']} | {name} | {value} | {family} |")
    lines+=['','| State | Pool | Interface | Decoding | Strict correct / outputs | Both goals / groups | Pass@4 targets |',
            '|---|---|---|---|---:|---:|---:|']
    for v in tables['views']:
        if not v['data_key'].startswith('eval_'): continue
        m=v['metrics']
        lines.append('| '+' | '.join([v['state'],v['data_key'],v['interface'],v['decoding'],
            _fraction(m.get('correct')) if m else 'NA',_fraction(m.get('both_targets_correct')) if m else 'NA',
            _fraction(m.get('pass_at_4')) if m else 'NA'])+' |')
    lines+=['',UNCERTAINTY,'',
        'Invalid, unparsed and capped outputs remain in every measured denominator. Unrun or incomplete views '
        'are not zeros and do not enter complete-grid contrasts. H requires the ordered scaffold, resources, '
        'target and completed output; F accepts any legal correct construction.','',
        'Training/midpoint diagnostics appear separately in TRAINING_DIAGNOSTICS.json and STAGE_A_TRAIN_FIT.md. '
        'Midpoint step64 never selects the formal step128 endpoint. Weighted and ordinary training objectives '
        'differ; only unweighted fixed-reference NLL is comparable as a diagnostic. Weight-mass preservation '
        'does not preserve gradient norm or effective optimization direction.','',
        'These fresh number instances are exploratory, not automatically structural OOD or an external '
        'confirmation set. Conditional operator diagnostics do not establish free construction or a hidden '
        'mechanism. No further training is selected or authorized by this report.','']
    return '\n'.join(lines)


def checkpoint_models(run, manifest, release):
    registration=json.loads((ROOT/'registration.json').read_text())['entries']
    if {e['state'] for e in registration}!=set(ARMS):
        raise ValueError('All four registered continuation arms required')
    models={(state,256):digest for state,digest in PARENT_SHA.items()}
    if any(manifest['parents'][state]['parameter_digest']['sha256']!=value for state,value in PARENT_SHA.items()):
        raise ValueError('Frozen E038/E039 parent identity differs')
    training=[]; protocols={}
    for entry in registration:
        state=entry['state']; directory=run/entry['run_id']; parent=PARENT_SHA[entry['parent']]
        initial_path=directory/'training_identity.json'
        initial=json.loads(initial_path.read_text()) if initial_path.exists() else None
        if initial:
            protocol=initial['protocol']; protocols[state]=protocol
            if (initial['initial_adapter']['sha256']!=parent or protocol['total_updates']!=128 or
                protocol['training_seed']!=17 or protocol['objective']!=entry['objective'] or
                protocol['decision_multiplier']!=(5. if entry['objective']=='D' else 1.) or
                protocol['denominator']!='raw_supervised_tokens' or protocol['F_weights']!=1.):
                raise ValueError('Continuation identity/objective differs from registration')
        for step in (64,128):
            path=directory/f'checkpoint_{step}'/'checkpoint_identity.json'
            if path.exists():
                cp=json.loads(path.read_text()); models[state,step]=cp['parameter_digest']['sha256']
        path=directory/'run_manifest_final.json'
        final=json.loads(path.read_text()) if path.exists() else None
        if final:
            if (final['status']!='completed' or final['completed_updates']!=128 or final['state']!=state or
                final['parent_adapter']['sha256']!=parent or final['final_adapter']['sha256']!=models.get((state,128)) or
                final['identity']['data_sha256']!=sha256_file(release/(entry['data']+'.jsonl')) or
                final.get('objective')!=entry['objective'] or
                final.get('optimizer_reset') is not True or final.get('scheduler_reset') is not True or initial is None):
                raise ValueError('Final endpoint/parent/data/objective differs from registration')
            history=read_jsonl(directory/'train_history.jsonl')
            if len(history)!=128 or [r['step'] for r in history]!=list(range(1,129)):
                raise ValueError('Final training history is incomplete or noncontiguous')
        training.append(dict(state=state,status='completed' if final else 'not_completed',
            final_manifest=final,training_identity=initial,
            interpretation='Objective loss differs between U and D; only ordinary unweighted reference NLL is comparable.'))
    for a,b in (('S-U','S-D'),('P-U','P-D')):
        if a in protocols and b in protocols:
            for field in ('schedule_sha256','lr_vector_sha256','encoded_rows_sha256','decision_masks_sha256'):
                if protocols[a][field]!=protocols[b][field]:
                    raise ValueError('Within-parent U/D order/LR/data/masks differ: '+field)
    return models,training


def _safe_public_binding(path, root):
    """Private export roots become stable relative artifact names, never user paths."""
    return str(path.relative_to(root))


def analyze(run=RUN, release=RELEASE, output=OUTPUT, *, tokenizer_dir):
    from .data import load_rows
    from .queue import evaluation_queue
    run,release,output=Path(run),Path(release),Path(output)
    if output.exists(): raise FileExistsError('Never overwrite a completed or partial analysis')
    verify_manifest(release)
    rows_by_key={key:load_rows(interface,release,pool=pool) for key,(pool,interface) in DATA_KEYS.items()}
    for interface in ('F','H'):
        if len(previous._data_index(rows_by_key['eval_'+interface])[2])!=48:
            raise ValueError('Fresh evaluation requires 48 frozen paired groups')
    events=evaluation_queue()
    for event in events:
        rows=rows_by_key[event['data_key']]
        if event['questions']!=len(rows) or event['generations']!=len(rows)*event['samples']:
            raise ValueError('Frozen event shape differs from analysis input')
    tokenizer,tokenizer_identity=verified_tokenizer(Path(tokenizer_dir))
    manifest_path=next((run/p for p in ('run_manifest_final.json','progress.json','run_manifest.json') if (run/p).exists()),None)
    if manifest_path is None: raise FileNotFoundError('No execution manifest')
    manifest=json.loads(manifest_path.read_text());ledger=json.loads((run/'generation_ledger.json').read_text())
    release_hash=sha256_file(release/'manifest.json')
    if manifest['release_manifest_sha256']!=release_hash: raise ValueError('Run/release identity differs')
    if (ledger['cap']!=5000 or len({e['name'] for e in ledger['events']})!=len(ledger['events']) or
        any(type(e['reserved']) is not int or e['reserved']<=0 for e in ledger['events']) or
        sum(e['reserved'] for e in ledger['events'])!=ledger['used'] or not 0<=ledger['used']<=5000):
        raise ValueError('New-phase generation ledger is inconsistent')
    models,training=checkpoint_models(run,manifest,release)
    completed={};coverage=[];audits={};problems=[]
    for event in events:
        path=run/(event['name']+'.jsonl');summary_path=path.with_suffix('.summary.json')
        summary=json.loads(summary_path.read_text()) if summary_path.exists() else None
        item=dict(evaluation=event['name'],expected_records=event['generations'],**previous._inventory_partial(path))
        if summary and summary.get('status')=='completed':
            if any(summary.get(k)!=v for k,v in event.items()):
                raise ValueError('Completed summary differs from frozen queue')
            expected=models.get((event['state'],event['checkpoint_step']))
            if expected is None: raise ValueError('Completed view lacks verified checkpoint identity')
            rows=rows_by_key[event['data_key']]
            records,audit=audit_completed_view(path,rows,event,summary,tokenizer,ledger,release,expected)
            completed[event['name']]=records;audits[event['name']]=audit
            problems.extend(per_problem(event,rows,records,tokenizer))
            item.update(status='complete_independently_verified',completed_records=len(records))
        coverage.append(item)
    tables=analyze_generations(completed,rows_by_key,events)
    diagnostics,diagnostics_complete=audit_diagnostics(run,release,models,tokenizer)
    complete=(len(completed)==len(events) and all(r['status']=='completed' for r in training) and diagnostics_complete)
    if manifest.get('status')=='completed' and not complete:
        raise ValueError('Completed phase is missing independently verified units')
    summary=dict(status='all_registered_outputs_verified' if complete else 'partial_coverage_verified',
        completed_generation_views=len(completed),registered_generation_views=len(events),
        completed_unique_generations=sum(map(len,completed.values())),registered_generations=sum(e['generations'] for e in events),
        charged_generation_reservations=ledger['used'],generation_cap=ledger['cap'],
        completed_training_runs=sum(r['status']=='completed' for r in training),planned_training_runs=4,
        completed_training_updates=sum(128 for r in training if r['status']=='completed'),planned_training_updates=512,
        analysis_model_calls=0,tokenizer=tokenizer_identity,generation_audits=audits,
        diagnostics_complete=diagnostics_complete,historical_phase_budgets_used_for_new_generation=False,
        uncertainty_scope=UNCERTAINTY,
        verification_scope='Frozen scorer and exact prompt/token/stop replay, immutable raw/score/request/RNG bindings, '
            'scientific checkpoint identities and stored forward arithmetic. No model logits replay.')
    output.mkdir(parents=True,exist_ok=False)
    dump(output/'SUMMARY.json',summary);dump(output/'COVERAGE.json',coverage)
    dump(output/'BEHAVIOR_RESULTS.json',dict(views=[v for v in tables['views'] if v['data_key'].startswith('eval_')],
        contrasts=tables['contrasts'],uncertainty_scope=UNCERTAINTY))
    dump(output/'TRAINING_DIAGNOSTICS.json',dict(views=[v for v in tables['views'] if not v['data_key'].startswith('eval_')],
        training=training,midpoint_scope=tables['midpoint_scope']))
    dump(output/'DECISION_DIAGNOSTICS.json',diagnostics)
    jsonl(output/'PER_PROBLEM.jsonl',problems)
    jsonl(output/'ERRORS.jsonl',[dict(p,error_inventory_scope='Strict failures or independently certified trace evidence; original score unchanged.')
        for p in problems if not p['score']['correct'] or p['semantic_diagnosis']['first_certified_error'] is not None or
        p['semantic_diagnosis']['first_semantic_error']['status']=='certified_wrong_first_H_decision'])
    (output/'STAGE_A_TRAIN_FIT.md').write_text(_stage_a_report(tables['views'],problems,diagnostics))
    (output/'RESULTS.md').write_text(_results_report(summary,tables))
    bindings={_safe_public_binding(p,run):sha256_file(p) for p in sorted(run.rglob('*'))
        if p.is_file() and not p.is_symlink() and p.suffix in ('.json','.jsonl')}
    sources=[Path(__file__),ROOT/'data.py',ROOT/'generation.py',ROOT/'decision_spans.py',ROOT/'diagnostics.py',
        Path('experiments/post_e037_goal_training/analyze.py'),Path('experiments/post_e036_goal_probe/scoring.py'),
        Path('src/trace_audit.py'),Path('analyses/completion_contract.py')]
    dump(output/'manifest.json',dict(input_root='run_artifacts',input_files_sha256=bindings,
        release_manifest_sha256=release_hash,registration_sha256=sha256_file(ROOT/'registration.json'),
        source_files_sha256={str(p.relative_to(Path.cwd()) if p.is_absolute() else p):sha256_file(p) for p in sources},
        files_sha256={p.name:sha256_file(p) for p in sorted(output.iterdir())}))
    return summary


def validate_decomposition(record,row,span,tokenizer):
    """Recompute stored reference partitions and causal masks without logits calls."""
    from .decision_spans import validate_mask
    enc=encode_row(row,tokenizer,1024);validate_mask(enc,span)
    positions=[i for i,label in enumerate(enc['labels']) if i>0 and label!=-100]
    expected=dict(source_row_sha256=digest(row),encoded_row_sha256=digest(enc),span_sha256=digest(span),
        input_ids=enc['input_ids'],prompt_ids=enc['input_ids'][:enc['n_prompt']],
        response_ids=[enc['input_ids'][i] for i in positions],response_token_positions=positions,
        causal_logit_positions=[i-1 for i in positions])
    if any(record.get(k)!=v for k,v in expected.items()):
        raise ValueError('Reference row/span/token/causal identity differs')
    values=record['response_log_probabilities']
    if len(values)!=len(positions) or any(type(v) not in (int,float) or not math.isfinite(v) or v>1e-6 for v in values):
        raise ValueError('Invalid response token log probabilities')
    names=('decision_mask','program_operator_mask','input_copy_mask','computed_numeric_mask')
    masks={k:[span[k][i] for i in positions] for k in names}
    if record['response_masks']!=masks or record['full_token_masks']!={k:span[k] for k in names}:
        raise ValueError('Reference decomposition masks differ from frozen annotation')
    masks=dict(masks,full=[True]*len(values),rest=[not v for v in masks['decision_mask']])
    if set(record['partitions'])!=set(masks): raise ValueError('Missing reference partition')
    for name,mask in masks.items():
        selected=[-v for v,m in zip(values,mask) if m]; part=record['partitions'][name]
        if (part['tokens']!=len(selected) or not math.isclose(part['nll_sum'],sum(selected),rel_tol=1e-10,abs_tol=1e-9) or
            (part['mean_nll'] is not None if not selected else
             part['mean_nll'] is None or not math.isclose(part['mean_nll'],sum(selected)/len(selected),rel_tol=1e-10,abs_tol=1e-9))):
            raise ValueError('Unweighted reference partition arithmetic differs')
    chosen=[i for i in positions if span['decision_mask'][i]]
    if record['decision_token_indices']!=chosen or len(record['decision_token_statistics'])!=len(chosen):
        raise ValueError('Reference decision statistics differ from annotated span')
    lookup=dict(zip(positions,values))
    for i,stats in zip(chosen,record['decision_token_statistics']):
        if (stats['token_id']!=enc['input_ids'][i] or not math.isclose(stats['log_probability'],lookup[i],abs_tol=1e-6) or
            not math.isclose(stats['probability'],math.exp(lookup[i]),rel_tol=1e-6,abs_tol=1e-8) or
            stats['strictly_higher_tokens']<0 or stats['equal_logit_tokens']<1 or not stats['argmax_tokens']):
            raise ValueError('Saved decision-token probabilities/ranks are inconsistent')
    if record['forward_calls']!=1 or record['input_tokens']!=len(enc['input_ids']) or record['seconds']<0:
        raise ValueError('Reference forward accounting differs')
    return dict(partitions=record['partitions'],decision_tokens=len(chosen),
        decision_response_positions=[i-enc['n_prompt'] for i in chosen],
        decision_token_statistics=record['decision_token_statistics'],
        rank_verification='Arithmetic and identities checked; vocabulary ranks rely on recorded forward evidence, not a model replay.')


def validate_candidates(record,row):
    from .diagnostics import candidate_context
    expected=candidate_context(row)
    if (record['context_ids']!=expected['context_ids'] or record['correct_operator']!=expected['correct_operator'] or
        record['source_row_sha256']!=digest(row)):
        raise ValueError('Candidate context/source identity differs')
    emitted={r['operator']:r for r in record['candidates']}
    if len(emitted)!=4 or set(emitted)!=set('+-*/'): raise ValueError('Four exact candidates required')
    ids=expected['candidates']
    if any(a!=b and ids[a]==ids[b][:len(ids[a])] for a in ids for b in ids):
        raise ValueError('Candidate sequences are not prefix-free')
    for operator,item in emitted.items():
        ps=item['token_log_probabilities']
        if (item['token_ids']!=ids[operator] or len(ps)!=len(ids[operator]) or
            any(not math.isfinite(v) or v>1e-6 for v in ps) or
            not math.isclose(sum(ps),item['log_probability'],rel_tol=1e-10,abs_tol=1e-9)):
            raise ValueError('Candidate sequence/log-probability sum differs')
    adapted=dict(record,candidate_ids=ids)
    parsed=previous._operator_context(adapted)
    calls=1 if all(len(v)==1 for v in ids.values()) else 4
    tokens=len(expected['context_ids']) if calls==1 else sum(len(expected['context_ids'])+len(v)-1 for v in ids.values())
    if record['forward_calls']!=calls or record['sequence_equivalents']!=calls or record['input_tokens']!=tokens:
        raise ValueError('Candidate sequence-equivalent accounting differs')
    return adapted,parsed


def audit_alignment_vectors(observation):
    """Reconstruct saved IEEE754 vectors; exact ties use first-index argmax."""
    vectors={}
    for kind in ('raw','effective'):
        bits=observation[kind+'_logits_fp32_bits']
        if not bits or any(type(v) is not int or not -(2**31)<=v<2**31 for v in bits):
            raise ValueError('Invalid lossless logit encoding')
        vector=np.asarray(bits,dtype=np.int32).view(np.float32)
        if np.isnan(vector).any() or not np.isfinite(vector).any(): raise ValueError('Nonfinite saved logits')
        argmax=int(vector.argmax());ties=np.flatnonzero(vector==vector.max()).tolist()
        if observation[kind+'_argmax']!=argmax or observation[kind+'_argmax_tokens']!=ties:
            raise ValueError('Stored argmax/tie report differs from lossless logits')
        vectors[kind]=vector
    if len(vectors['raw'])!=len(vectors['effective']): raise ValueError('Raw/effective vocabulary differs')
    if observation['raw_effective_exact_equal']!=bool(np.array_equal(vectors['raw'],vectors['effective'])):
        raise ValueError('Raw/effective equality report differs')
    matched=observation['generated_token']==observation['effective_argmax']
    expected_status='aligned' if matched else 'genuine_effective_argmax_mismatch'
    if observation['status']!=expected_status: raise ValueError('Alignment status conceals an effective-argmax mismatch')
    return matched


def audit_alignment(path,event,rows,case_rows,case_spans,tokenizer,expected_model,release_hash):
    from .diagnostics import make_alignment_cases
    artifact=json.loads(path.read_text());cases=make_alignment_cases(case_rows,case_spans,tokenizer)
    if (artifact['cases']!=cases or artifact['cases_sha256']!=digest(cases) or
        artifact['identity']['model_hash']!=expected_model or artifact['identity']['split_hash']!=release_hash or
        artifact['extra_forward_calls']!=0 or artifact['extra_generations']!=0):
        raise ValueError('Alignment cases/model/release identity differs')
    folder=path.with_suffix('.observations');files=sorted(folder.glob('*.json'))
    if artifact['batch_files_sha256']!={p.name:sha256_file(p) for p in files}:
        raise ValueError('Alignment observation file hashes differ')
    rawpath=path.parent.parent/(event['name']+'.raw_batches.jsonl')
    raw_batches=read_jsonl(rawpath) if rawpath.exists() else []
    raw={digest(dict(input_ids=r['input_ids'],attention_mask=r['attention_mask'],output_ids=r['output_ids'])):r for r in raw_batches}
    summary_path=path.parent.parent/(event['name']+'.summary.json')
    generation_completed=(summary_path.exists() and json.loads(summary_path.read_text()).get('status')=='completed')
    by_case={c['source_row_sha256']:c for c in cases};observed=set();committed_observed=set()
    mismatches=0;observation_count=0;uncommitted=[]
    for file in files:
        batch=json.loads(file.read_text());binding=batch['identity']
        if binding['identity']!=artifact['identity'] or binding['cases_sha256']!=digest(cases):
            raise ValueError('Alignment batch binding differs')
        key=digest(dict(input_ids=binding['prompt_batch_ids'],attention_mask=binding['attention_mask'],output_ids=batch['output_ids']))
        committed=key in raw
        if not committed:
            if generation_completed:
                raise ValueError('Completed generation alignment lacks matching durable raw batch')
            uncommitted.append(dict(file=file.name,sha256=sha256_file(file),
                reason='Observation persisted before generation raw commit; not counted as verified committed coverage.'))
        if batch['extra_forward_calls'] or batch['extra_generations'] or batch['model_training']:
            raise ValueError('Alignment was not passive eval-mode observation')
        width=len(binding['prompt_batch_ids'][0]);checks={}
        for check in batch['selection_checks']:
            index,step=check['batch_row'],check['step'];case=by_case[check['source_row_sha256']]
            prompt=[t for t,m in zip(binding['prompt_batch_ids'][index],binding['attention_mask'][index]) if m]
            if prompt!=case['prompt_ids'] or check['generated_token']!=batch['output_ids'][index][width+step]:
                raise ValueError('Alignment selection/prompt/output binding differs')
            if (index,step) in checks: raise ValueError('Duplicate alignment selection step')
            checks[index,step]=check;observed.add(check['source_row_sha256'])
            if committed:committed_observed.add(check['source_row_sha256'])
            mismatches+=int(check['generated_token']!=check['effective_argmax'])
        for observation in batch['observations']:
            index,step=observation['batch_row'],observation['step'];check=checks[index,step]
            case=by_case[check['source_row_sha256']];reference=case['reference_response_ids']
            generated=batch['output_ids'][index][width:]
            first_difference=next((i for i,t in enumerate(generated) if i>=len(reference) or t!=reference[i]),None)
            if (observation['source_row_sha256']!=check['source_row_sha256'] or
                observation['generated_token']!=check['generated_token'] or
                observation['prefix_ids']!=batch['output_ids'][index][:width+step] or
                observation['generated_prefix_ids']!=generated[:step] or
                observation['reference_token']!=(reference[step] if step<len(reference) else None) or
                observation['reference_prefix_matches']!=(generated[:step]==reference[:step]) or
                observation['first_literal_deviation']!=(step==first_difference) or
                observation['is_reference_decision_position']!=(step in case['decision_response_positions'])):
                raise ValueError('Alignment detailed prefix differs from actual generated prefix')
            audit_alignment_vectors(observation);observation_count+=1
        emitted_mismatches=[c for c in batch['selection_checks'] if c['generated_token']!=c['effective_argmax']]
        if batch['genuine_mismatches']!=emitted_mismatches:
            raise ValueError('Alignment mismatch inventory differs')
        if committed:
            case_prompts={tuple(c['prompt_ids']) for c in cases}
            expected_checks=set()
            for index,(ids,mask) in enumerate(zip(binding['prompt_batch_ids'],binding['attention_mask'])):
                if tuple(t for t,m in zip(ids,mask) if m) in case_prompts:
                    expected_checks.update((index,step) for step in range(raw[key]['stop_events'][index]['retained_tokens']))
            if set(checks)!=expected_checks:
                raise ValueError('Alignment selection checks omit active generated tokens or include post-stop padding')
    missing=sorted(set(by_case)-observed)
    if artifact['missing_cases']!=missing or artifact['observed_cases']!=sorted(observed) or artifact['genuine_mismatches']!=mismatches:
        raise ValueError('Alignment aggregate coverage/count differs')
    committed_missing=sorted(set(by_case)-committed_observed)
    return dict(path=str(path.name),status='hard_failure' if mismatches else 'incomplete' if committed_missing or uncommitted else 'passed',
        registered_cases=len(cases),observed_cases=len(observed),missing_cases=missing,
        committed_observed_cases=len(committed_observed),committed_missing_cases=committed_missing,
        uncommitted_observation_batches=uncommitted,
        genuine_mismatches=mismatches,lossless_vector_observations=observation_count,
        extra_forward_calls=0,extra_generations=0,
        verification='Generation-batch/prefix/output binding and saved lossless raw/effective vector argmax replay; no model replay.')


def _operator_summary(records,rows):
    _,registered,families=previous._data_index(rows)
    indexed={(r['group_id'],r['target_index']):previous._operator_context(r) for r in records}
    if len(indexed)!=len(records) or set(indexed)!=set(registered):
        raise ValueError('Candidate view does not cover every registered target exactly once')
    values={name:{} for name in ('D_goal','margin','correct_unique_argmax','both_unique_argmax','raw_mass','correct_raw_probability')}
    marginals={op:dict(true_labels=0,unique_argmax=0,argmax_including_ties=0) for op in '+-*/'}
    for context in indexed.values():
        marginals[context['correct_operator']]['true_labels']+=1
        for op in context['argmax_operators']:marginals[op]['argmax_including_ties']+=1
        if len(context['argmax_operators'])==1:marginals[context['argmax_operators'][0]]['unique_argmax']+=1
    for g in families:
        a,b=indexed[g,0],indexed[g,1];o0,o1=a['correct_operator'],b['correct_operator']
        la,lb=a['candidate_log_probabilities'],b['candidate_log_probabilities']
        values['D_goal'][g]=(lb[o1]-lb[o0])-(la[o1]-la[o0])
        values['margin'][g]=sum(c['candidate_log_probabilities'][c['correct_operator']]-
            max(v for op,v in c['candidate_log_probabilities'].items() if op!=c['correct_operator']) for c in (a,b))/2
        values['correct_unique_argmax'][g]=(a['correct_unique_argmax']+b['correct_unique_argmax'])/2
        values['both_unique_argmax'][g]=float(a['correct_unique_argmax'] and b['correct_unique_argmax'])
        values['raw_mass'][g]=(a['candidate_probability_mass']+b['candidate_probability_mass'])/2
        values['correct_raw_probability'][g]=(a['correct_raw_probability']+b['correct_raw_probability'])/2
    return dict(contexts=len(records),groups=len(families),operator_marginals=marginals,
        correct_unique_argmax=dict(numerator=sum(c['correct_unique_argmax'] for c in indexed.values()),denominator=len(records)),
        both_unique_argmax=dict(numerator=int(sum(values['both_unique_argmax'].values())),denominator=len(families)),
        ties=sum(len(c['argmax_operators'])>1 for c in indexed.values()),
        metrics={k:group_interval(v,families) for k,v in values.items()},group_values=values,
        contexts_results=list(indexed.values()),
        interpretation='First decision under supplied valid reference prefix. Raw full-vocabulary mass and four-candidate normalization remain separate; these are not free-generation success.')


def _audit_forward_view(path,rows,spans,identity,ledger,tokenizer):
    from .diagnostics import candidate_context
    candidate=spans is None
    diagnostic='first_decision_candidates' if candidate else 'unweighted_reference_decomposition'
    identity=dict(identity,diagnostic=diagnostic)
    bound_rows=rows if candidate else [dict(row=r,span=s) for r,s in zip(rows,spans)]
    descriptor=dict(identity=identity,rows_sha256=digest(bound_rows),diagnostic=diagnostic,
                    source_sha256=sha256_file(ROOT/'diagnostics.py'))
    folder=path.with_suffix('.resume');manifest_path=folder/'manifest.json'
    if json.loads(manifest_path.read_text())!=descriptor:
        raise ValueError('Forward descriptor differs')
    published=json.loads(path.read_text()) if path.exists() else None
    files=sorted(p for p in folder.glob('*.json') if len(p.stem)==6 and p.stem.isdigit())
    if [p.name for p in files]!=[f'{i:06d}.json' for i in range(len(files))]:
        raise ValueError('Noncontiguous durable forward rows')
    records=[json.loads(p.read_text()) for p in files]
    if len(records)>len(rows):raise ValueError('Extra forward rows')
    if published:
        if (published['identity']!=identity or published['manifest_sha256']!=sha256_file(manifest_path) or
            published['expected_records']!=len(rows) or published['completed_records']!=len(published['records']) or
            published['records']!=records[:len(published['records'])]):
            raise ValueError('Forward publication is not the exact durable prefix')
        if published['status']=='completed' and len(published['records'])!=len(rows):
            raise ValueError('Completed forward view missing records')
        for key in ('forward_calls','sequence_equivalents','input_tokens','seconds'):
            measured=sum(r['forward_calls' if key=='sequence_equivalents' else key] for r in published['records'])
            if not math.isclose(published[key],measured,rel_tol=1e-10,abs_tol=1e-9):
                raise ValueError('Published forward aggregate accounting differs')
    artifact=dict(status='completed' if published and published['status']=='completed' else 'partial',
        records=records,completed_records=len(records),manifest_sha256=sha256_file(manifest_path),
        **{key:sum(r['forward_calls' if key=='sequence_equivalents' else key] for r in records)
           for key in ('forward_calls','sequence_equivalents','input_tokens','seconds')})
    reservations={e['name']:e['reserved'] for e in ledger['events']};adapted=[];decomposed=[]
    for index,record in enumerate(artifact['records']):
        path_row=folder/f'{index:06d}.json';intent=path_row.with_suffix('.intent.json')
        binding=dict(descriptor_sha256=digest(descriptor),index=index,row_sha256=digest(bound_rows[index]))
        key='diagnostic_'+digest(binding)
        n=(1 if all(len(v)==1 for v in candidate_context(rows[index])['candidates'].values()) else 4) if candidate else 1
        if (record!=json.loads(path_row.read_text()) or record['identity']!=binding or record['request_key']!=key or
            reservations.get(key)!=n or json.loads(intent.read_text())!=dict(identity=binding,request_key=key,sequence_equivalents=n)):
            raise ValueError('Immutable forward/intent/reservation binding differs')
        if candidate:
            item,_=validate_candidates(record,rows[index]);adapted.append(item)
        else:decomposed.append(validate_decomposition(record,rows[index],spans[index],tokenizer))
    pending_intents=[]
    for intent in sorted(folder.glob('*.intent.json')):
        index=int(intent.name.split('.')[0])
        if not 0<=index<len(rows):raise ValueError('Unregistered forward intent')
        binding=dict(descriptor_sha256=digest(descriptor),index=index,row_sha256=digest(bound_rows[index]))
        key='diagnostic_'+digest(binding)
        n=(1 if all(len(v)==1 for v in candidate_context(rows[index])['candidates'].values()) else 4) if candidate else 1
        if json.loads(intent.read_text())!=dict(identity=binding,request_key=key,sequence_equivalents=n):
            raise ValueError('Forward intent binding differs')
        if index>=len(records):
            pending_intents.append(dict(index=index,request_key=key,reserved_sequence_equivalents=reservations.get(key,0),
                status='intent_without_result_do_not_replay'))
    if artifact['status']=='completed' and pending_intents:
        raise ValueError('Completed forward view has unresolved intents')
    summary=dict(status=artifact['status'],completed_records=artifact['completed_records'],expected_records=len(rows),
        published_records=published['completed_records'] if published else 0,
        aggregate_publication='current' if published and len(published['records'])==len(records) else 'stale_prefix' if published else 'missing',
        pending_intents=pending_intents,
        manifest_sha256=artifact['manifest_sha256'],forward_calls=artifact['forward_calls'],
        sequence_equivalents=artifact['sequence_equivalents'],input_tokens=artifact['input_tokens'],seconds=artifact['seconds'])
    if not candidate:
        partitions={}
        for name in ('full','decision_mask','rest','program_operator_mask','input_copy_mask','computed_numeric_mask'):
            count=sum(r['partitions'][name]['tokens'] for r in decomposed)
            total=sum(r['partitions'][name]['nll_sum'] for r in decomposed)
            partitions[name]=dict(tokens=count,nll_sum=total,mean_nll=total/count if count else None)
        summary.update(partitions=partitions,decision_span_lengths=dict(Counter(str(r['decision_tokens']) for r in decomposed)),
            decision_details=[dict(problem_id=row['problem_id'],source_row_sha256=digest(row),**r) for row,r in zip(rows,decomposed)],
            interpretation='Nonweighted reference likelihood; descriptive partial totals are not a complete-pool estimate until status completed.')
    return summary,adapted


def audit_diagnostics(run,release,models,tokenizer):
    from .data import load_inputs
    from .decision_spans import annotate
    from .queue import evaluation_queue
    inputs=load_inputs(release);release_hash=sha256_file(release/'manifest.json')
    other={key:[annotate(row,tokenizer) for row in inputs[key]] for key in ('eval_H','train_H','midpoint_H','midpoint_F')}
    forward_path=run/'forward_ledger.json'
    ledger=json.loads(forward_path.read_text()) if forward_path.exists() else dict(cap=16384,used=0,events=[])
    if (ledger['cap']!=16384 or len({e['name'] for e in ledger['events']})!=len(ledger['events']) or
        any(type(e['reserved']) is not int or e['reserved']<=0 for e in ledger['events']) or
        ledger['used']!=sum(e['reserved'] for e in ledger['events']) or not 0<=ledger['used']<=16384):
        raise ValueError('Forward sequence-equivalent ledger differs')
    views=[];operator_views={}
    for state in STATES:
        recipe='single' if state in ('E038','S-U','S-D') else 'paired'
        specs=[('reference_H',inputs[recipe][:512],inputs['spans'][recipe][:512]),
               ('reference_F',inputs[recipe][512:],inputs['spans'][recipe][512:])]
        for pool in (('train_H','eval_H') if state in STATES[:2] else ('eval_H',)):
            rows=inputs[pool];spans=other[pool]
            contexts=[dict(problem_id=row['problem_id'],group_id=row['group_id'],target_index=row['target_index'],
                context_ids=span['prefix_input_ids'],candidates=span['candidates'],correct_operator=span['correct_operator'])
                for row,span in zip(rows,spans)]
            specs += [(pool,rows,spans),(pool+'_candidates',contexts,None)]
        for kind,rows,spans in specs:
            path=run/'diagnostics'/state/(kind+'.json')
            if not path.exists() and not (path.with_suffix('.resume')/'manifest.json').exists():
                views.append(dict(state=state,kind=kind,status='not_measured',metrics=None));continue
            expected=models.get((state,256 if state in STATES[:2] else 128))
            if expected is None:raise ValueError('Forward artifact lacks verified endpoint identity')
            identity=dict(state=state,adapter_sha256=expected,release_manifest_sha256=release_hash,rows_sha256=digest(rows))
            summary,adapted=_audit_forward_view(path,rows,spans,identity,ledger,tokenizer)
            if spans is None and summary['status']=='completed':
                pool=kind.removesuffix('_candidates')
                summary['operator_metrics']=_operator_summary(adapted,inputs[pool])
                if pool=='eval_H':operator_views[state]=summary['operator_metrics']
            scope=('Actual arm-specific training references; no unsupervised countergoals included.' if kind.startswith('reference_') else
                   'Fixed H training-group diagnostic with style0 reference; E038 countergoals are unsupervised, separate from training NLL.' if kind.startswith('train_H') else
                   'Fresh exploratory H evaluation references; same fixed references across all six states.')
            views.append(dict(state=state,kind=kind,scope=scope,**summary))
    if len(views)!=28:raise ValueError('Exactly 28 reference/candidate diagnostic views required')
    alignment=[];events={e['name']:e for e in evaluation_queue()}
    for state in STATES[:2]:
        for interface in 'FH':
            name=f'{state}_stage_a_{interface}_greedy';path=run/'alignment'/(name+'.json');pool='midpoint_'+interface
            result=(audit_alignment(path,events[name],inputs['train_'+interface],inputs[pool],other[pool],tokenizer,
                                    PARENT_SHA[state],release_hash) if path.exists() else dict(status='not_measured'))
            alignment.append(dict(state=state,interface=interface,**result))
    contrasts={}
    if set(operator_views)==set(STATES):
        families=previous._data_index(inputs['eval_H'])[2]
        for metric in ('D_goal','margin','correct_unique_argmax','both_unique_argmax','raw_mass','correct_raw_probability'):
            contrasts[metric]=joint_six_state_contrasts({s:operator_views[s]['group_values'][metric] for s in STATES},families)
    complete=all(v['status']=='completed' for v in views) and all(v['status']=='passed' for v in alignment)
    return dict(views=views,alignment=alignment,operator_contrasts=contrasts,
        forward_accounting=dict(charged_sequence_equivalents=ledger['used'],cap=ledger['cap'],
            verified_saved_forward_calls=sum(v.get('forward_calls',0) for v in views),
            scope='Each actual sequence forward is charged once; candidate scores and new generations are separate.'),
        same_prefix_hard_consistency_passed=all(v['status']=='passed' for v in alignment),
        uncertainty_scope=UNCERTAINTY),complete


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,default=RUN);parser.add_argument('--release',type=Path,default=RELEASE)
    parser.add_argument('--output',type=Path,default=OUTPUT);parser.add_argument('--tokenizer-dir',required=True)
    args=parser.parse_args()
    result=analyze(args.run_dir,args.release,args.output,tokenizer_dir=args.tokenizer_dir)
    print(json.dumps({k:result[k] for k in ('status','completed_generation_views','completed_unique_generations')}))
