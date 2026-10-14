"""Create-only local P1 journal candidate; no model calls or eligibility admission.

The accepted scalar and two-process pool are unchanged. A partial chunk blocks
continuation; pending pairs are not retried or silently converted into zeroes.
"""
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time

from experiments.learning_regime_p009.math_scoring import decide, last_box
from experiments.learning_regime_p009.math_scoring_pool import SymbolicPool, pair_digest, STOPS

VERSION = 'p009_math_journal_candidate_v1'
SAMPLE_DOMAIN = 'p009-p1-fixed-audit-sample-v1'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def create(path, value):
    """A torn write stays visible and blocks reentry; never overwrite a record."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(canonical(value)+b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def validate_rows(rows):
    ids = set()
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get('id'), str)
                or not row['id'] or row['id'] in ids
                or not isinstance(row.get('gold'), str) or not row['gold'].strip()
                or not isinstance(row.get('answer_segment'), str)
                or row.get('stop_reason') not in STOPS):
            raise ValueError('Complete unique original rows and supported structural gold required')
        ids.add(row['id'])
    if not rows:
        raise ValueError('Empty P1 roster is not a pass')
    canonical(rows)


def pairs_for(rows):
    pairs = {}
    for row in rows:
        answer = last_box(row['answer_segment'])['answer']
        if row['stop_reason'] in ('native_eos', 'new_problem_boundary') and answer:
            pair = (row['gold'], answer)
            pairs[pair_digest(pair)] = pair
    return pairs


class JournaledPool:
    """Reuse only fully committed chunks; unknown or partial work blocks the job.

    A chunk intent reserves every prospective new pair before pool execution.
    On a caught error, known finished pairs are saved but the chunk stays failed.
    Abrupt loss may leave additional pairs unconfirmed; none may be retried.
    """

    def __init__(self, root, rows, binding, *, pool_factory=SymbolicPool):
        validate_rows(rows)
        if not isinstance(binding, dict) or not binding:
            raise ValueError('Exact future input/source binding required')
        canonical(binding)
        self.root = Path(root)
        self.rows = deepcopy(rows)
        self.basis = dict(version=VERSION, ordered_rows_sha256=digest(rows),
                          row_count=len(rows), binding=deepcopy(binding))
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = (self.root/'LOCK').open('a+b')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.lock.close()
            raise
        self.pool = pool_factory()
        self.closed = False
        self.completed = []
        self.position = 0
        try:
            basis = self.root/'BASIS.json'
            if basis.exists():
                if read(basis) != self.basis:
                    raise ValueError('Original ordered rows or binding changed')
            else:
                if any(p.name != 'LOCK' for p in self.root.iterdir()):
                    raise ValueError('Unbound prior/partial journal exists')
                create(basis, self.basis)
            self._restore_complete_only()
        except BaseException:
            self.close()
            raise

    def _restore_complete_only(self):
        chunks = sorted((self.root/'chunks').glob('*'))
        for i, folder in enumerate(chunks):
            if folder.name != f'{i:05d}' or (not (folder/'COMPLETED.json').is_file() or not (folder/'TIMING.json').is_file()):
                raise ValueError('Partial/unknown chunk blocks continuation; preserve and reconcile')
            intent = read(folder/'INTENT.json'); done = read(folder/'COMPLETED.json')
            result = read(folder/'RESULT.json')
            if (done['intent_sha256'] != file_sha(folder/'INTENT.json')
                    or done['result_sha256'] != file_sha(folder/'RESULT.json')
                    or intent['start'] != self.position
                    or intent['rows_sha256'] != digest(self.rows[intent['start']:intent['end']])
                    or [r['id'] for r in result['rows']] != intent['row_ids']):
                raise ValueError('Committed chunk binding differs')
            self.position = intent['end']
            self.completed.append((folder, intent, result))
        observations = []
        for path in sorted((self.root/'pairs').glob('*.json')):
            record = read(path); pair = tuple(record['pair']); obs = record['observation']
            if (len(pair) != 2 or path.stem != pair_digest(pair)
                    or obs['pair_id'] != path.stem or pair in self.pool.cache):
                raise ValueError('Pair cache identity differs')
            decide(pair[0], {'answer': pair[1]}, obs['symbolic'], stop_reason='native_eos')
            self.pool.cache[pair] = obs; observations.append(obs)
        observations.sort(key=lambda x: x['attempt_index'])
        if [x['attempt_index'] for x in observations] != list(range(len(observations))):
            raise ValueError('Missing or duplicate symbolic attempt')
        expected_pairs = pairs_for(self.rows[:self.position])
        if set(expected_pairs.values()) != set(self.pool.cache):
            raise ValueError('Pair cache is not exactly the committed original rows')
        for _, _, result in self.completed:
            for row in result['rows']:
                obs = row['symbolic_attempt']
                if obs is not None and obs not in observations:
                    raise ValueError('Row references an uncommitted symbolic result')
        self.pool.attempts = observations
        self.pool.row_ids = {r['id'] for r in self.rows[:self.position]}

    def _save_pairs(self):
        for pair, observation in self.pool.cache.items():
            path = self.root/'pairs'/(pair_digest(pair)+'.json')
            value = dict(pair=list(pair), observation=observation)
            if path.exists():
                if read(path) != value:
                    raise ValueError('Cached symbolic result changed')
            else:
                create(path, value)

    def score_next(self, count, *, timing_review=None):
        if self.closed or type(count) is not int or not 1 <= count <= 100:
            raise ValueError('Open session and bounded chunk required')
        if self.position >= len(self.rows):
            raise ValueError('Complete roster cannot be rescored')
        if self.position == 0:
            if count != min(100, len(self.rows)):
                raise ValueError('The first actual chunk must be the first100 original rows')
        else:
            first = self.completed[0][0]/'RESULT.json'
            review = timing_review or {}
            if (review.get('scope') != 'p009-math-p1-first100-throughput'
                    or review.get('decision') not in ('PASS', 'PASS-WITH-NOTES')
                    or review.get('basis_sha256') != digest(self.basis)
                    or review.get('first100_result_sha256') != file_sha(first)
                    or not isinstance(review.get('report_commit'), str)
                    or len(review['report_commit']) != 40
                    or file_sha(review['local_report_path']) != review['report_sha256']):
                raise ValueError('Real exact first100 throughput review required before the rest')
        end = min(self.position+count, len(self.rows))
        rows = self.rows[self.position:end]
        folder = self.root/'chunks'/f'{len(self.completed):05d}'
        folder.mkdir(parents=True, exist_ok=False)
        intended = pairs_for(rows)
        new_pairs = {key:list(pair) for key,pair in intended.items() if pair not in self.pool.cache}
        intent = dict(start=self.position, end=end, row_ids=[r['id'] for r in rows],
            rows_sha256=digest(rows), new_pair_intents=new_pairs,
            utc=datetime.now(timezone.utc).isoformat(), automatic_retry=False,
            timing_review=timing_review)
        create(folder/'INTENT.json', intent)
        started = time.monotonic()
        try:
            result = self.pool.score_rows(rows)
            if [r['id'] for r in result['rows']] != intent['row_ids']:
                raise ValueError('Pool returned different rows')
            self._save_pairs()
            create(folder/'RESULT.json', result)
            create(folder/'COMPLETED.json', dict(intent_sha256=file_sha(folder/'INTENT.json'),
                result_sha256=file_sha(folder/'RESULT.json'),
                confirmed_rows=len(rows), technical_unknown=0))
            create(folder/'TIMING.json', dict(
                elapsed_through_completed_proof_seconds=time.monotonic()-started,
                final_timing_record_write_excluded=True))
        except BaseException as exc:
            try:
                self._save_pairs()
                confirmed = {pair_digest(pair) for pair in self.pool.cache}
                create(folder/'FAILED.json', dict(type=type(exc).__name__, error=str(exc),
                    unconfirmed_pair_intents=sorted(set(new_pairs)-confirmed),
                    row_outcomes_unconfirmed=True, retry_authorized=False))
            finally:
                self.close()
            raise
        self.position = end
        self.completed.append((folder, intent, result))
        return result

    def close(self):
        if not self.closed:
            self.closed = True
            try:
                self.pool.close()
            finally:
                fcntl.flock(self.lock, fcntl.LOCK_UN)
                self.lock.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def first100_forecast(basis, first_result, timing_record, all_rows):
    """Conservative serial-time scenario; never count cache hits as new speed."""
    if basis['ordered_rows_sha256'] != digest(all_rows):
        raise ValueError('Original complete input roster required')
    n = min(100, len(all_rows))
    if [r['id'] for r in first_result['rows']] != [r['id'] for r in all_rows[:n]]:
        raise ValueError('First100 exact ordered result required')
    observations = {r['pair_id']:r['symbolic_attempt'] for r in first_result['rows']
                    if r['pair_id'] is not None}
    remaining = len(set(pairs_for(all_rows))-set(observations))
    durations = [r['elapsed_seconds'] for r in observations.values()]
    if remaining and not durations:
        raise ValueError('No new-pair timing; cannot extrapolate only cache/stop rows')
    times = durations+[timing_record['elapsed_through_completed_proof_seconds']]
    if any(not math.isfinite(t) or t < 0 for t in times):
        raise ValueError('Finite actual observations required')
    # No assumed two-worker speedup or favorable-host selection. Allowances are
    # explicitly uncalibrated; a later exact numerical review must admit runtime.
    elapsed = timing_record['elapsed_through_completed_proof_seconds']
    scenario = elapsed+1.2*((max(durations) if durations else 0)*remaining+300)
    return dict(first_rows=n, unique_observed_pairs=len(observations),
        remaining_distinct_pairs=remaining, maximum_pair_seconds=max(durations,default=None),
        startup_observations=first_result['startup_observations'],
        first_chunk_through_proof_seconds=elapsed, final_timing_record_write_excluded=True,
        serial_time_scenario_seconds=scenario,
        allowance_seconds=300, margin=1.2, calibrated_bound=False,
        runtime_admitted=False, cache_hits_are_not_new_pair_timing=True)


def audit_samples(original_rows, results):
    """Freeze samples for independent inspection; do not invent adjudications."""
    validate_rows(original_rows)
    if [r['id'] for r in results] != [r['id'] for r in original_rows]:
        raise ValueError('Complete ordered results required; no partial score selection')
    by_id = {r['id']:r for r in original_rows}
    def sample(rows, limit):
        return sorted(rows, key=lambda r:(digest([SAMPLE_DOMAIN,r['id']]),r['id']))[:limit]
    disagreements = [r for r in results if r['score'].get('string_symbolic_disagreement')]
    fallback = [r for r in results if r['score'].get('fallback_used')]
    boxed = sum(bool(last_box(r['answer_segment'])['answer']) for r in original_rows)
    pairs = {r['pair_id']:r['symbolic_attempt'] for r in results if r['pair_id'] is not None}
    outer = sum(x['symbolic']['status']=='outer_timeout' for x in pairs.values())
    high_fallback = bool(boxed and 100*len(fallback)>2*boxed)
    def project(rows):
        return [dict(original=by_id[r['id']], scored=r, adjudication=None) for r in rows]
    return dict(disagreement_count=len(disagreements),
        disagreement_sample=project(sample(disagreements,50)),
        boxed_rows=boxed, fallback_rows=len(fallback), fallback_over_two_percent=high_fallback,
        fallback_sample=project(sample(fallback,25)) if high_fallback else [],
        unique_pairs=len(pairs), outer_timeout_unique_pairs=outer,
        outer_timeout_over_half_percent=bool(pairs and 200*outer>len(pairs)),
        unbraced_boxed_rows=sum(bool(re.search(r'\\(?:boxed|fbox)(?!\s*\{)',r['answer_segment']))
                               for r in original_rows),
        structurally_unsupported_gold_rows=0, unsupported_gold_is_not_scored_zero=True,
        sample_domain=SAMPLE_DOMAIN, independent_adjudication_complete=False,
        eligibility_admitted=False, primary_labels_changed=False)
