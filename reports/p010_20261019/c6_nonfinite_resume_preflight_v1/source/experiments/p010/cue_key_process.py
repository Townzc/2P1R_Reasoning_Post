"""Bounded, gold-free answer grouping; technical failures never become missing."""
import importlib.metadata
import multiprocessing
import time
from pathlib import Path
from experiments.p010.common import dump, digest, utc
from experiments.p010.cue_answer_key import answer_key, extracted_tail
from experiments.learning_regime_p009.math_scoring import VERSIONS

PAIR_SECONDS = 8
STARTUP_SECONDS = 30
LOCAL_SECONDS = 108000


def worker(connection):
    try:
        actual = {name:importlib.metadata.version(name) for name in VERSIONS}
        if actual != VERSIONS:
            connection.send(dict(ready=False, versions=actual))
            return
        from math_verify import parse
        connection.send(dict(ready=True, versions=actual))
        while True:
            item = connection.recv()
            if item is None:
                return
            key, text = item
            try:
                value = answer_key(text, lambda source:parse(source, parsing_timeout=2, raise_on_error=True))
                connection.send(dict(key=key, status='confirmed', answer_key=value))
            except Exception as exc:
                connection.send(dict(key=key, status='technical_failure',
                    error_type=type(exc).__name__, error=str(exc)))
                return
    finally:
        connection.close()


class OriginalAnswerKeys:
    def __init__(self, out, deadline_epoch):
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=False)
        self.deadline = deadline_epoch
        self.cache = {}
        self.count = 0
        self.ctx = multiprocessing.get_context('spawn')
        self.parent, child = self.ctx.Pipe()
        self.proc = self.ctx.Process(target=worker, args=(child,), daemon=False)
        dump(self.out/'INTENT.json', dict(utc=utc(), pair_seconds=PAIR_SECONDS,
            startup_seconds=STARTUP_SECONDS, deadline_epoch=deadline_epoch,
            gold_used=False, correctness_used=False, automatic_retry=False))
        self.proc.start()
        child.close()
        try:
            if not self.parent.poll(min(STARTUP_SECONDS,max(0,self.deadline-time.time()))):
                raise TimeoutError('Original answer-key process startup deadline')
            ready = self.parent.recv()
            dump(self.out/'STARTUP.json',ready)
            if ready != dict(ready=True,versions=VERSIONS):
                raise ValueError('Pinned answer-key parser environment differs')
        except BaseException:
            self.close(kill=True)
            raise

    def one(self, text):
        if time.time() >= self.deadline-5:
            raise TimeoutError('Original local selection deadline')
        extracted = extracted_tail(text)
        if extracted is None:
            return dict(answer_key=None,status='missing_extraction',pair_id=None,cached=False)
        key = digest(dict(extracted_answer=extracted))
        if key in self.cache:
            return dict(**self.cache[key],cached=True)
        out = self.out/'pairs'/key
        out.mkdir(parents=True,exist_ok=False)
        dump(out/'INTENT.json',dict(pair_id=key,extracted_answer=extracted,utc=utc()))
        tick = time.monotonic()
        self.count += 1
        try:
            # Preserve the original completion. Rewrapping a truncated nested
            # answer before extraction could change the author's80-char rule.
            # Neither the question nor gold enters this subprocess.
            self.parent.send((key,text))
            if not self.parent.poll(min(PAIR_SECONDS,max(0,self.deadline-time.time()-5))):
                raise TimeoutError('Original unique answer-key outer timeout')
            result = self.parent.recv()
            if result.get('key') != key or result.get('status') != 'confirmed':
                dump(out/'FAILED_RESULT.json',result)
                raise RuntimeError('Technical answer-key failure; cue selection unavailable')
            value = dict(answer_key=result['answer_key'],status='confirmed',pair_id=key)
            dump(out/'COMPLETED.json',dict(**value,seconds=time.monotonic()-tick,utc=utc()))
            self.cache[key] = value
            return dict(**value,cached=False)
        except BaseException as exc:
            dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),
                seconds=time.monotonic()-tick,utc=utc(),automatic_retry=False))
            self.close(kill=True)
            raise

    def close(self, *, kill=False):
        if not self.proc.is_alive():
            self.proc.join(timeout=1)
            self.parent.close()
            if not kill and self.proc.exitcode != 0:
                raise RuntimeError('Original parser process exit was not successful')
            return
        if kill:
            self.proc.kill()
        else:
            self.parent.send(None)
        self.proc.join(timeout=3)
        if self.proc.is_alive():
            self.proc.kill()
            self.proc.join(timeout=2)
            if not kill:
                raise RuntimeError('Original parser process did not exit')
        self.parent.close()
        if not kill and self.proc.exitcode != 0:
            raise RuntimeError('Original parser process exit was not successful')


def group_rows(decoded, out, deadline_epoch):
    """Exactly the already audited10080 development responses, each kept once."""
    if (len(decoded) != 10080 or len({r['candidate_id'] for r in decoded}) != 10080
            or any(set(r)-{'candidate_id','problem_id','candidate','rollout','cue_token_ids',
                'stop','raw_record_sha256','raw_file','raw_file_sha256'} for r in decoded)):
        raise ValueError('Only full gold-free decoded development responses')
    out = Path(out)
    out.mkdir(parents=True,exist_ok=False)
    rows, observations = [], []
    pool = OriginalAnswerKeys(out/'answer_keys',deadline_epoch)
    try:
        for first in range(0,len(decoded),100):
            batch = []
            for row in decoded[first:first+100]:
                # Search missingness is absence of an extractable answer, not
                # primary task correctness. A capped output can have a key;
                # its cap is retained and primary evaluation still marks caps wrong.
                value = pool.one(row['stop']['answer_segment'])
                result = dict(candidate_id=row['candidate_id'],problem_id=row['problem_id'],
                    candidate=row['candidate'],rollout=row['rollout'],
                    stop_reason=row['stop']['stop_reason'],**value)
                batch.append(result)
                observations.append({k:result[k] for k in ('candidate','problem_id','rollout','answer_key')})
            dump(out/'confirmed_batches'/f'{first:05d}.json',batch)
            rows.extend(batch)
        pool.close()
        dump(out/'ROWS.json',rows)
        dump(out/'OBSERVATIONS.json',observations)
        dump(out/'COMPLETED.json',dict(utc=utc(),rows=len(rows),unique_parser_attempts=pool.count,
            cached_rows=sum(r['cached'] for r in rows),gold_used=False,correctness_used=False,
            parser_versions=VERSIONS,technical_unknown=0))
        return observations
    except BaseException as exc:
        pool.close(kill=True)
        dump(out/'FAILED.json',dict(utc=utc(),type=type(exc).__name__,error=str(exc),
            partial_valid_parts_preserved=True,automatic_retry=False,selection_allowed=False))
        raise
