"""Once-only C6 local continuation using every original confirmed key/batch."""
import importlib.metadata
import multiprocessing
import time
from pathlib import Path
from experiments.p010.common import read,dump,digest,sha,utc
from experiments.p010.cue_answer_key import extracted_tail
from experiments.p010.cue_answer_key_nonfinite import answer_key
from experiments.p010.cue_key_process import OriginalAnswerKeys,PAIR_SECONDS,STARTUP_SECONDS
from experiments.learning_regime_p009.math_scoring import VERSIONS

FAILED_KEY='a61f5577ba33fb9115887fa48110a389b3a5954b5c770ee241a7204dae31b122'
EXPECTED_ERROR='Nonfinite parser numeric output is not a valid entropy key'


def confirmed_prior(prior):
    prior=Path(prior);cache={};failed=[]
    for folder in sorted((prior/'grouping/answer_keys/pairs').iterdir()):
        intent=read(folder/'INTENT.json');key=folder.name
        if key!=digest(dict(extracted_answer=intent['extracted_answer'])) or intent['pair_id']!=key:
            raise ValueError('Original pair identity differs')
        complete=folder/'COMPLETED.json';failure=folder/'FAILED_RESULT.json'
        if complete.exists():
            value=read(complete)
            if failure.exists() or (folder/'FAILED.json').exists() or value['status']!='confirmed' or value['pair_id']!=key:
                raise ValueError('Ambiguous original confirmed pair')
            cache[key]={k:value[k] for k in ('answer_key','status','pair_id')}
        else:
            value=read(failure);error=read(folder/'FAILED.json')
            if (key!=FAILED_KEY or intent['extracted_answer']!='\\infty' or value!=dict(key=key,status='technical_failure',error_type='ValueError',error=EXPECTED_ERROR)
                    or error['automatic_retry'] is not False):
                raise ValueError('Only the specifically approved infinity failure may be completed')
            failed.append(key)
    if len(cache)!=731 or failed!=[FAILED_KEY]:
        raise ValueError('Exact731 confirmed and one failed original keys required')
    return cache


def worker(connection):
    try:
        versions={n:importlib.metadata.version(n) for n in VERSIONS}
        if versions!=VERSIONS:
            connection.send(dict(ready=False,versions=versions));return
        from math_verify import parse
        connection.send(dict(ready=True,versions=versions))
        while True:
            item=connection.recv()
            if item is None:return
            key,text=item
            try:
                value=answer_key(text,lambda source:parse(source,parsing_timeout=2,raise_on_error=True))
                connection.send(dict(key=key,status='confirmed',answer_key=value))
            except Exception as exc:
                connection.send(dict(key=key,status='technical_failure',error_type=type(exc).__name__,error=str(exc)));return
    finally:connection.close()


class ResumedKeys(OriginalAnswerKeys):
    def __init__(self,out,deadline_epoch,confirmed):
        self.out=Path(out);self.out.mkdir(parents=True,exist_ok=False)
        self.deadline=deadline_epoch;self.cache=dict(confirmed);self.count=0
        self.ctx=multiprocessing.get_context('spawn');self.parent,child=self.ctx.Pipe()
        self.proc=self.ctx.Process(target=worker,args=(child,),daemon=False)
        dump(self.out/'INTENT.json',dict(utc=utc(),pair_seconds=PAIR_SECONDS,startup_seconds=STARTUP_SECONDS,
            deadline_epoch=deadline_epoch,inherited_confirmed_keys=len(confirmed),failed_key_allowed_once=FAILED_KEY,
            gold_used=False,correctness_used=False,automatic_retry=False))
        self.proc.start();child.close()
        try:
            if not self.parent.poll(min(STARTUP_SECONDS,max(0,self.deadline-time.time()))):raise TimeoutError('Parser startup deadline')
            ready=self.parent.recv();dump(self.out/'STARTUP.json',ready)
            if ready!=dict(ready=True,versions=VERSIONS):raise ValueError('Frozen parser versions differ')
        except BaseException:self.close(kill=True);raise


def resume_rows(decoded,prior,out,deadline,*,pool_factory=ResumedKeys,prior_loader=confirmed_prior):
    if len(decoded)!=10080 or len({r['candidate_id'] for r in decoded})!=10080:
        raise ValueError('Complete original development roster required')
    prior=Path(prior);out=Path(out);confirmed=prior_loader(prior);rows=[];observations=[];inherited={}
    batches=sorted((prior/'grouping/confirmed_batches').glob('*.json'))
    if [f.name for f in batches]!=[f'{i:05d}.json' for i in range(0,3700,100)]:raise ValueError('Exact37 original confirmed batches required')
    for f in batches:
        part=read(f);first=int(f.stem)
        if len(part)!=100:raise ValueError('Partial original batch')
        for saved,original in zip(part,decoded[first:first+100]):
            if any(saved[k]!=original[k] for k in ('candidate_id','problem_id','candidate','rollout')):raise ValueError('Original row order differs')
            if saved['stop_reason']!=original['stop']['stop_reason']:raise ValueError('Original logical stop differs')
            extracted=extracted_tail(original['stop']['answer_segment'])
            if extracted is None:
                if saved['answer_key'] is not None or saved['status']!='missing_extraction' or saved['pair_id'] is not None:raise ValueError('Original missing extraction differs')
            else:
                key=digest(dict(extracted_answer=extracted));value=confirmed[key]
                if any(saved[k]!=value[k] for k in ('answer_key','status','pair_id')):raise ValueError('Original cached key differs')
            rows.append(saved);observations.append({k:saved[k] for k in ('candidate','problem_id','rollout','answer_key')})
        inherited[f.name]=dict(sha256=sha(f),rows=len(part))
    out.mkdir(parents=True,exist_ok=False);dump(out/'INHERITED_CONFIRMED.json',dict(batches=inherited,keys=confirmed,original_rows=3700))
    pool=pool_factory(out/'answer_keys',deadline,confirmed)
    try:
        for first in range(3700,len(decoded),100):
            batch=[]
            for row in decoded[first:first+100]:
                value=pool.one(row['stop']['answer_segment'])
                saved=dict(candidate_id=row['candidate_id'],problem_id=row['problem_id'],candidate=row['candidate'],rollout=row['rollout'],stop_reason=row['stop']['stop_reason'],**value)
                batch.append(saved);observations.append({k:saved[k] for k in ('candidate','problem_id','rollout','answer_key')})
            dump(out/'confirmed_batches'/f'{first:05d}.json',batch);rows.extend(batch)
        pool.close();dump(out/'ROWS.json',rows);dump(out/'OBSERVATIONS.json',observations)
        dump(out/'COMPLETED.json',dict(utc=utc(),rows=len(rows),inherited_confirmed_keys=731,inherited_confirmed_rows=3700,
            new_parser_attempts=pool.count,original_failed_key_new_attempts=1 if FAILED_KEY in pool.cache else 0,
            repeated_confirmed_parser_attempts=0,technical_unknown=0,gold_used=False,correctness_used=False))
        return observations
    except BaseException as exc:
        pool.close(kill=True);dump(out/'FAILED.json',dict(utc=utc(),type=type(exc).__name__,error=str(exc),partial_valid_parts_preserved=True,automatic_retry=False));raise
