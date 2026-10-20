"""Prepared durable S1 endpoint scoring, without CLI or admission authority.

The future complete driver must validate its exact runtime/source/input reviews,
the full endpoint payload, actual P1 A2/scorer identity and numerical local-time
admission before calling this helper. No old P1 job or first100 review is reused
as permission for a different roster. The accepted scalar/pool stay unchanged.
An existing job, including an interrupted one, cannot be run again here.
"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import math
import time

from experiments.learning_regime_p009.math_scoring_journal import (
    create, digest, file_sha, read, validate_rows, pairs_for, audit_samples,
)
from experiments.learning_regime_p009.math_scoring_pool import SymbolicPool, pair_digest


class DurableEndpointPool(SymbolicPool):
    """Persist each returned pair immediately, including original failures.

    The parent pool still owns the two processes and all eight-second deadlines.
    An abrupt loss between computation and this write is unconfirmed work, not
    permission to retry. Replacement processes only handle future distinct pairs.
    """

    def __init__(self, root, deadline):
        super().__init__()
        self.root = Path(root)
        self.deadline = deadline

    def _start(self):
        if time.monotonic() >= self.deadline:
            raise TimeoutError('Original local scoring window exhausted')
        return super()._start()

    def _finish(self, worker, result, *, retire=False):
        pair = worker['task'][1]
        super()._finish(worker, result, retire=retire)
        create(self.root/'pairs'/(pair_digest(pair)+'.json'),
               dict(pair=list(pair), observation=self.cache[pair]))
        if time.monotonic() >= self.deadline:
            raise TimeoutError('Original local scoring window exhausted after preserved pair')


def checked_endpoint_rows(rows):
    validate_rows(rows)
    if len(rows) != 500 or len({r.get('problem_id') for r in rows}) != 500:
        raise ValueError('The complete original500 endpoint is required')
    for row in rows:
        if (not isinstance(row.get('problem_id'), str) or not row['problem_id']
                or row['id'] != 'S1::'+row['problem_id']):
            raise ValueError('Exact original S1 endpoint identity is required')
        for key in ('original_gold_row_sha256', 'original_decoded_record_sha256'):
            value = row.get(key)
            if (not isinstance(value, str) or len(value) != 64
                    or any(c not in '0123456789abcdef' for c in value)):
                raise ValueError('Original gold and decoded source hashes are required')


def preserve_pairs(root, pool):
    for pair, observation in pool.cache.items():
        path = root/'pairs'/(pair_digest(pair)+'.json')
        value = dict(pair=list(pair), observation=observation)
        if path.exists():
            if read(path) != value:
                raise ValueError('A preserved original pair changed')
        else:
            create(path, value)


def score_endpoint_once(root, rows, binding, local_seconds, *, pool_factory=DurableEndpointPool):
    """One complete500-row job; caller must enforce the outer hard process cap.

    This is a payload operation, not an acceptance writer. The explicit binding
    is retained unchanged for the future outer verifier. No resume/retry path,
    prior-job rescore, model invocation, new parser or label adjustment exists.
    """
    checked_endpoint_rows(rows)
    if (not isinstance(binding, dict) or not binding
            or type(local_seconds) is not int or not 0 < local_seconds <= 129600):
        raise ValueError('Explicit future source/input binding and bounded local window required')
    digest(binding)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    create(root/'INTENT.json', dict(ordered_rows_sha256=digest(rows), row_count=500,
        binding=deepcopy(binding), local_seconds=local_seconds,
        utc=datetime.now(timezone.utc).isoformat(), automatic_retry=False,
        outer_hard_process_cap_required=True, payload_only=True))
    create(root/'ROWS.json', rows)
    pool = None; complete = []
    try:
        pool = pool_factory(root, started+local_seconds)
        for offset in range(0, 500, 100):
            if time.monotonic()-started >= local_seconds:
                raise TimeoutError('Original local scoring window exhausted before chunk')
            part = rows[offset:offset+100]
            folder = root/'chunks'/f'{offset//100:05d}'
            new = {key:list(pair) for key,pair in pairs_for(part).items() if pair not in pool.cache}
            create(folder/'INTENT.json', dict(start=offset, end=offset+100,
                row_ids=[r['id'] for r in part], rows_sha256=digest(part),
                new_pair_intents=new, cached_pairs_before=len(pool.cache)))
            chunk_started = time.monotonic()
            try:
                value = pool.score_rows(part)
                preserve_pairs(root, pool)
                if ([r['id'] for r in value['rows']] != [r['id'] for r in part]
                        or any(type(r['score'].get('correct')) is not bool for r in value['rows'])):
                    raise ValueError('Complete ordered Boolean endpoint result required')
                create(folder/'RESULT.json', value)
                create(folder/'COMPLETED.json', dict(intent_sha256=file_sha(folder/'INTENT.json'),
                    result_sha256=file_sha(folder/'RESULT.json'), confirmed_rows=100,
                    technical_unknown=0))
                create(folder/'TIMING.json', dict(
                    elapsed_through_completed_proof_seconds=time.monotonic()-chunk_started,
                    final_timing_record_write_excluded=True))
                complete.extend(value['rows'])
            except BaseException as exc:
                preserve_pairs(root, pool)
                confirmed = {pair_digest(pair) for pair in pool.cache}
                create(folder/'FAILED.json', dict(type=type(exc).__name__, error=str(exc),
                    unconfirmed_pair_intents=sorted(set(new)-confirmed),
                    original_chunk_not_confirmed=True, automatic_retry=False))
                raise
        pool.close()
        if time.monotonic()-started >= local_seconds:
            raise TimeoutError('Local closeout must fit the original window')
        observations = list(pool.cache.values())
        if any(not math.isfinite(x['elapsed_seconds']) or x['elapsed_seconds'] < 0
               for x in observations):
            raise ValueError('Original actual symbolic intervals must be finite')
        samples = audit_samples(rows, complete)
        scores = {row['problem_id']:out['score']['correct'] for row,out in zip(rows, complete)}
        create(root/'ALL_SCORED_ROWS.json', complete)
        create(root/'AUDIT_SAMPLES.json', samples)
        result = dict(row_count=500, correct=sum(scores.values()), question_correct=scores,
            unique_symbolic_pairs=len(pool.cache), technical_unknown=0,
            elapsed_before_final_proof_seconds=time.monotonic()-started,
            original_rows_sha256=file_sha(root/'ROWS.json'),
            scored_rows_sha256=file_sha(root/'ALL_SCORED_ROWS.json'),
            audit_samples_sha256=file_sha(root/'AUDIT_SAMPLES.json'),
            full_runtime_lineage_admission_checked=False, payload_only=True,
            external_outcome_review_pending=True, scientific_G1_admitted=False,
            original_parser_unchanged=True, automatic_retry=False, new_model_calls=0)
        create(root/'COMPLETED.json', result)
        return result
    except BaseException as exc:
        create(root/'FAILED.json', dict(type=type(exc).__name__, error=str(exc),
            confirmed_chunk_rows=len(complete), automatic_retry=False,
            partial_evidence_preserved=True, complete_endpoint=False))
        raise
    finally:
        if pool is not None:
            pool.close()
