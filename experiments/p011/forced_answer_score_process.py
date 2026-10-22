"""Once-only forced-continuation scoring with unchanged P1 scalar/two-process pool."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from experiments.p011.owner_0205_common import create, digest, read, sha, utc


def score_child(root):
    from experiments.learning_regime_p009.math_scoring_journal import validate_rows, pairs_for, audit_samples
    from experiments.learning_regime_p009.stage1_s1_scoring import DurableEndpointPool, preserve_pairs
    root=Path(root);intent=read(root/'INTENT.json');rows=read(root/'ROWS.json')
    if (os.getpid()!=os.getpgrp() or sha(root/'ROWS.json')!=intent['rows_sha256']
            or time.time()>=intent['deadline_epoch']):
        raise ValueError('Owned bounded scoring child with exact rows required')
    out=root/'payload';out.mkdir(exist_ok=False)
    create(out/'STARTED.json',{'utc':utc(),'rows':len(rows),'original_natural_rows_scored':0})
    if rows:validate_rows(rows)
    pool=None;scored=[]
    try:
        pool=DurableEndpointPool(out,time.monotonic()+intent['deadline_epoch']-time.time())
        for offset in range(0,len(rows),100):
            if time.time()>=intent['deadline_epoch']:raise TimeoutError('New score hard timer expired')
            part=rows[offset:offset+100];folder=out/'chunks'/f'{offset:05d}'
            create(folder/'INTENT.json',{'ids':[r['id'] for r in part],'rows_sha256':digest(part),
                'new_pair_intents':{k:list(p) for k,p in pairs_for(part).items() if p not in pool.cache}})
            value=pool.score_rows(part);preserve_pairs(out,pool)
            create(folder/'RESULT.json',value)
            if ([r['id'] for r in value['rows']]!=[r['id'] for r in part]
                    or any(type(r['score'].get('correct')) is not bool for r in value['rows'])):
                raise ValueError('Incomplete scoring is unknown, never zero')
            create(folder/'COMPLETED.json',{'rows':len(part),'result_sha256':sha(folder/'RESULT.json')})
            scored.extend(value['rows'])
        pool.close()
        create(out/'ALL_SCORED_ROWS.json',scored)
        if rows:create(out/'AUDIT_SAMPLES.json',audit_samples(rows,scored))
        create(out/'COMPLETED.json',{'utc':utc(),'rows':len(scored),'technical_unknown':0,
            'unique_symbolic_pairs':len(pool.cache),'old_rows_rescored':0,
            'scored_rows_sha256':sha(out/'ALL_SCORED_ROWS.json'),'actual_A3_accepted':False})
    except BaseException as exc:
        if pool is not None:preserve_pairs(out,pool)
        create(out/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),
            'confirmed_rows':len(scored),'automatic_retry':False});raise
    finally:
        if pool is not None:pool.close()


def supervise(root,rows,binding,seconds=7200):
    if type(seconds) is not int or not 0<seconds<=7200:raise ValueError('Score cap at most7200s')
    root=Path(root);root.mkdir(parents=True,exist_ok=False);started=time.time();proc=None
    create(root/'ROWS.json',rows);create(root/'BINDING.json',binding)
    create(root/'INTENT.json',{'started_epoch':started,'deadline_epoch':started+seconds,
        'rows_sha256':sha(root/'ROWS.json'),'binding_sha256':sha(root/'BINDING.json'),
        'automatic_retry':False,'original_labels_rescored':0})
    try:
        with (root/'worker.log').open('xb') as log:
            proc=subprocess.Popen([sys.executable,'-m','experiments.p011.forced_answer_score_process',
                '--owned-child',str(root.resolve())],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            create(root/'CHILD.json',{'pid':proc.pid,'pgid':proc.pid,'new_session':True})
            code=proc.wait(timeout=max(.001,started+seconds-time.time()))
        if code!=0 or time.time()>=started+seconds:raise RuntimeError('Scoring child failed or exceeded hard timer')
        # Close any resource-tracker remnant from this exact owned group only.
        try:os.killpg(proc.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        proof=read(root/'payload/COMPLETED.json')
        create(root/'COMPLETED.json',{'finished_utc':utc(),'proof':proof,
            'payload_proof_sha256':sha(root/'payload/COMPLETED.json'),'automatic_retry':False})
    except BaseException as exc:
        if proc is not None:
            try:os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            proc.wait(timeout=5)
        create(root/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False});raise


if __name__=='__main__':
    if len(sys.argv)!=3 or sys.argv[1]!='--owned-child':raise SystemExit('Owned child only')
    score_child(sys.argv[2])
