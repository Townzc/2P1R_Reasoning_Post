"""Prepared P011 full3300 endpoint scoring; unchanged frozen P1 scalar/pool.

Requires the complete new outer input/source/runtime admission and raw oracle.
No actual production scoring has run. No per-first100 extra audit is introduced.
"""
from pathlib import Path
import time
import math

from experiments.p010.common import read, sha
from experiments.p011.long_evaluation import BENCHMARK_COUNTS
from experiments.learning_regime_p009.math_scoring_journal import (
    create, digest, file_sha, validate_rows, pairs_for, audit_samples,
)
from experiments.learning_regime_p009.math_scoring_pool import pair_digest
from experiments.learning_regime_p009.stage1_s1_scoring import DurableEndpointPool, preserve_pairs

LOCAL_SECONDS = 33000
SCENARIO_SECONDS = 1.2*(3300*8+300)


def groups(rows):
    return {key:[i for i,r in enumerate(rows) if r['id'].split(':')[0]+'_'+r['id'].split(':')[2]==key]
            for key in ('math500_sample','math500_greedy','aime24_sample','aime25_sample','amc23_sample')}


def checked_rows(rows):
    validate_rows(rows)
    expected={f'{b}:{i:04d}:{mode}:{seed}'
        for b,n in BENCHMARK_COUNTS.items() for i in range(n)
        for mode,seeds in ([('sample',range(4)),('greedy',[0])] if b=='math500' else [('sample',range(8))])
        for seed in seeds}
    if len(rows)!=3300 or {r['id'] for r in rows}!=expected:
        raise ValueError('Exactly all3300 original long endpoints required')
    for row in rows:
        if row['stop_reason'] not in ('native_eos','length_cap','invalid_special_token'):
            raise ValueError('Only original native long generation stops permitted')
        for name in ('request_sha256','raw_text_sha256','region_sha256'):
            value=row.get(name)
            if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError('Exact original request/full-text/think-region binding required')
        if type(row.get('last_think_boundary_present')) is not bool:
            raise ValueError('Original think-boundary presence must be disclosed')


def checked_summary(rows, results):
    checked_rows(rows)
    if ([x['id'] for x in results] != [x['id'] for x in rows]
            or any(type(x['score'].get('correct')) is not bool for x in results)):
        raise ValueError('All3300 ordered Boolean results required; unknown is not zero')
    endpoints={}
    for label,indices in groups(rows).items():
        table={}
        for i in indices:
            b,question,mode,seed=rows[i]['id'].split(':')
            table.setdefault(b+':'+question,{})[int(seed)]=results[i]['score']['correct']
        table={q:[values[s] for s in sorted(values)] for q,values in sorted(table.items())}
        correct=sum(sum(v) for v in table.values())
        endpoints[label]=dict(correct=correct,total=len(indices),question_correct=table,
            mean_pass_at_one=correct/len(indices),descriptive_only=not label.startswith('math500_'))
    return dict(endpoints=endpoints,outputs=3300,primary_mean_pass_at_one=endpoints['math500_sample']['mean_pass_at_one'],
        greedy_accuracy=endpoints['math500_greedy']['mean_pass_at_one'],bootstrap_performed=False,
        independent_smoke_selection_performed=False)


def score_once(root, rows, binding, local_seconds, *, pool_factory=DurableEndpointPool):
    checked_rows(rows)
    if not isinstance(binding, dict) or not binding or type(local_seconds) is not int or not 1 <= local_seconds <= LOCAL_SECONDS:
        raise ValueError('Explicit original source/input binding and local window required')
    root = Path(root); root.mkdir(parents=True, exist_ok=False); started = time.monotonic()
    create(root/'INTENT.json', dict(binding=binding, ordered_rows_sha256=digest(rows),
        row_count=3300, local_seconds=local_seconds, no_automatic_retry=True,
        outer_owned_process_cap_required=True))
    create(root/'ROWS.json', rows)
    pool = None; all_scored = []
    try:
        pool = pool_factory(root, started+local_seconds)
        for offset in range(0, 3300, 100):
            if time.monotonic()-started >= local_seconds:
                raise TimeoutError('Original local window expired')
            part = rows[offset:offset+100]; folder = root/'chunks'/f'{offset//100:05d}'
            new = {key:list(pair) for key,pair in pairs_for(part).items() if pair not in pool.cache}
            create(folder/'INTENT.json', dict(start=offset, end=offset+100,
                row_ids=[r['id'] for r in part], rows_sha256=digest(part),
                new_pair_intents=new, cached_pairs_before=len(pool.cache)))
            tick = time.monotonic()
            try:
                value = pool.score_rows(part); preserve_pairs(root, pool)
                if ([r['id'] for r in value['rows']] != [r['id'] for r in part]
                        or any(type(r['score'].get('correct')) is not bool for r in value['rows'])):
                    raise ValueError('Incomplete or reordered scoring output')
                create(folder/'RESULT.json', value)
                create(folder/'COMPLETED.json', dict(intent_sha256=file_sha(folder/'INTENT.json'),
                    result_sha256=file_sha(folder/'RESULT.json'), confirmed_rows=100, technical_unknown=0))
                create(folder/'TIMING.json', dict(elapsed_through_completed_seconds=time.monotonic()-tick,
                                                timing_write_excluded=True))
                all_scored.extend(value['rows'])
            except BaseException as exc:
                preserve_pairs(root, pool)
                confirmed = {pair_digest(pair) for pair in pool.cache}
                create(folder/'FAILED.json', dict(type=type(exc).__name__, error=str(exc),
                    unconfirmed_pair_intents=sorted(set(new)-confirmed), automatic_retry=False))
                raise
        pool.close()
        if time.monotonic()-started >= local_seconds:
            raise TimeoutError('Scoring closeout must fit original local cap')
        summary = checked_summary(rows, all_scored)
        samples = audit_samples(rows, all_scored)
        create(root/'ALL_SCORED_ROWS.json', all_scored); create(root/'AUDIT_SAMPLES.json', samples)
        # Per-endpoint audit samples remain descriptive and never change labels.
        for label,indices in groups(rows).items():
            create(root/'audit_by_evaluation'/(label+'.json'),
                audit_samples([rows[i] for i in indices],[all_scored[i] for i in indices]))
        result = dict(**summary, row_count=3300, unique_symbolic_pairs=len(pool.cache),
            technical_unknown=0, scored_rows_sha256=file_sha(root/'ALL_SCORED_ROWS.json'),
            samples_sha256=file_sha(root/'AUDIT_SAMPLES.json'),
            elapsed_before_final_proof_seconds=time.monotonic()-started,
            unchanged_primary_labels=True, independent_adjudication_complete=False,
            independent_A3_pending=True, new_model_calls=0)
        create(root/'COMPLETED.json', result)
        return result
    except BaseException as exc:
        create(root/'FAILED.json', dict(type=type(exc).__name__, error=str(exc),
            confirmed_chunk_rows=len(all_scored), partial_evidence_preserved=True, automatic_retry=False))
        raise
    finally:
        if pool is not None:
            pool.close()


def verify_saved_scores(root, rows, binding, local_seconds):
    """Reconstruct saved Boolean summaries; never rerun symbolic comparison."""
    from experiments.learning_regime_p009.math_scoring import last_box, decide
    root = Path(root); checked_rows(rows); intent = read(root/'INTENT.json')
    if (intent['binding'] != binding or intent['ordered_rows_sha256'] != digest(rows)
            or intent['local_seconds'] != local_seconds or read(root/'ROWS.json') != rows
            or intent['row_count'] != 3300 or intent['no_automatic_retry'] is not True
            or intent['outer_owned_process_cap_required'] is not True
            or (root/'FAILED.json').exists()):
        raise ValueError('Original scoring input or incomplete job differs')
    pairs = {}
    for path in sorted((root/'pairs').glob('*.json')):
        record = read(path); pair = tuple(record['pair']); obs = record['observation']
        if path.stem != pair_digest(pair) or path.stem != obs['pair_id'] or pair in pairs:
            raise ValueError('Saved symbolic pair identity differs')
        symbolic = obs['symbolic']
        if (type(obs['attempt_index']) is not int or not math.isfinite(obs['elapsed_seconds'])
                or obs['elapsed_seconds'] < 0 or not (
                    (symbolic['status'] == 'compared' and type(symbolic['equivalent']) is bool)
                    or (symbolic['status'] in ('parse_failure', 'symbolic_timeout', 'tool_error', 'outer_timeout')
                        and symbolic['equivalent'] is None))):
            raise ValueError('Invalid original pair verdict or observed time')
        pairs[pair] = obs
    if set(pairs) != set(pairs_for(rows).values()):
        raise ValueError('Missing or extra confirmed symbolic pair')
    observed = sorted(pairs.values(), key=lambda x: x['attempt_index'])
    if [x['attempt_index'] for x in observed] != list(range(len(observed))):
        raise ValueError('Duplicate/missing original symbolic attempts')
    folders = sorted((root/'chunks').glob('*')); all_rows = []; seen = set()
    if [p.name for p in folders] != [f'{i:05d}' for i in range(33)]:
        raise ValueError('All33 original complete chunks required')
    for index, folder in enumerate(folders):
        part = rows[index*100:(index+1)*100]; start = read(folder/'INTENT.json')
        done = read(folder/'COMPLETED.json'); value = read(folder/'RESULT.json')
        new = {k:list(p) for k,p in pairs_for(part).items() if p not in seen}
        if ((folder/'FAILED.json').exists() or start['rows_sha256'] != digest(part)
                or start['row_ids'] != [r['id'] for r in part]
                or start['start'] != index*100 or start['end'] != (index+1)*100
                or start['new_pair_intents'] != new or start['cached_pairs_before'] != len(seen)
                or done['intent_sha256'] != file_sha(folder/'INTENT.json')
                or done['result_sha256'] != file_sha(folder/'RESULT.json')
                or done['confirmed_rows'] != 100 or done['technical_unknown'] != 0
                or [r['id'] for r in value['rows']] != [r['id'] for r in part]):
            raise ValueError('Original confirmed chunk proof differs')
        for row, actual in zip(part, value['rows']):
            extracted = last_box(row['answer_segment']); pair = (row['gold'], extracted['answer'])
            has_pair = row['stop_reason'] in ('native_eos', 'new_problem_boundary') and bool(extracted['answer'])
            observation = pairs[pair] if has_pair else None
            expected = decide(row['gold'], extracted, observation['symbolic'] if observation else {},
                              stop_reason=row['stop_reason'])
            if (actual['score'] != expected or actual['symbolic_attempt'] != observation
                    or actual['pair_id'] != (pair_digest(pair) if has_pair else None)):
                raise ValueError('Saved frozen decision or pair provenance differs')
        timing = read(folder/'TIMING.json')
        if not math.isfinite(timing['elapsed_through_completed_seconds']) or timing['elapsed_through_completed_seconds'] < 0:
            raise ValueError('Original chunk timing invalid')
        seen.update(pairs_for(part).values()); all_rows.extend(value['rows'])
    saved = read(root/'COMPLETED.json'); summary = checked_summary(rows, all_rows)
    if (read(root/'AUDIT_SAMPLES.json') != audit_samples(rows, all_rows)
            or saved['technical_unknown'] != 0 or saved['row_count'] != 3300
            or saved['independent_adjudication_complete'] is not False
            or saved['independent_A3_pending'] is not True
            or saved['unchanged_primary_labels'] is not True
            or not 0 <= saved['elapsed_before_final_proof_seconds'] < local_seconds):
        raise ValueError('Saved fixed samples, original labels or local window differs')
    for label,indices in groups(rows).items():
        if read(root/'audit_by_evaluation'/(label+'.json')) != audit_samples(
                [rows[i] for i in indices],[all_rows[i] for i in indices]):
            raise ValueError('Per-endpoint fixed sample differs')
    if (read(root/'ALL_SCORED_ROWS.json') != all_rows
            or saved['scored_rows_sha256'] != file_sha(root/'ALL_SCORED_ROWS.json')
            or saved['samples_sha256'] != file_sha(root/'AUDIT_SAMPLES.json')
            or saved['unique_symbolic_pairs'] != len(pairs)
            or any(saved.get(k) != v for k,v in summary.items())):
        raise ValueError('Original complete score summary differs')
    return dict(passed=True, **summary, unique_symbolic_pairs=len(pairs), new_symbolic_comparisons=0)
