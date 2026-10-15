"""Owner-authorized36-hour local P1 successor; no model calls or changed scorer."""
import argparse
from datetime import datetime,timezone
import importlib.metadata
import json
import math
import multiprocessing
import os
from pathlib import Path
import threading
import time

from experiments.sft_allocation_midpoint.common import sha
from experiments.learning_regime_p009.p1_input_binding_extended import (
    bind_complete_generations,DATASET_ORDER,SOURCE_PATHS,GENERATION_SPEC_SHA,GENERATION_TARGET,OWNER_WINDOW_AMENDMENT_SHA256)
from experiments.learning_regime_p009.math_scoring import VERSIONS
from experiments.learning_regime_p009.math_scoring_journal import (
    JournaledPool,read,create,digest,first100_forecast,audit_samples)

SCOPE='p009-math-p1-extended-local-window-and-first100'
FIRST_WALL_SECONDS=1200
MAXIMUM_TOTAL_SCENARIO_SECONDS=129600


def accepted(path):
    review=read(path)
    if (review.get('scope')!=SCOPE or review.get('decision') not in ('PASS','PASS-WITH-NOTES')
            or len(review.get('report_commit',''))!=40
            or sha(review['local_report_path'])!=review['report_sha256']
            or review.get('conditional_first100_authorized') is not True
            or review.get('first100_wall_seconds')!=FIRST_WALL_SECONDS
            or review.get('maximum_total_wall_seconds')!=MAXIMUM_TOTAL_SCENARIO_SECONDS
            or review.get('local_window_amendment_sha256')!=OWNER_WINDOW_AMENDMENT_SHA256
            or review.get('generation_spec_sha256')!=GENERATION_SPEC_SHA
            or review.get('generation_target_commit')!=GENERATION_TARGET
            or set(review.get('source_files',{}))!=set(SOURCE_PATHS)):
        raise ValueError('True exact driver/input-contract review must permit first100')
    for name,h in review['source_files'].items():
        if sha(name)!=h:raise ValueError('Reviewed P1 code changed')
    if review['source_files'].get(__file__.removeprefix(str(Path.cwd())+'/'))!=sha(__file__):
        raise ValueError('Actual driver must be covered by the exact review')
    return review


def freeze(args):
    root=Path(args.root);review=accepted(args.code_review)
    if root.exists():raise ValueError('Actual P1 input release already exists; no rebuild')
    value=bind_complete_generations(args.generation_root,args.inputs,args.generation_admission)
    binding=dict(driver_review={k:v for k,v in review.items() if k!='local_report_path'},
        source_files=review['source_files'],generation_proof=value['generation_proof'],
        generation_spec_sha256=value['generation_spec_sha256'],
        generation_runtime_review_sha256=value['generation_runtime_review_sha256'],
        gold_files=value['original_gold_files'],
        unsupported_gold_sha256=digest(value['unsupported_gold']),counts=value['counts'],
        dataset_order=list(DATASET_ORDER),first100_wall_seconds=FIRST_WALL_SECONDS,
        maximum_total_wall_seconds=MAXIMUM_TOTAL_SCENARIO_SECONDS,
        local_window_amendment_sha256=OWNER_WINDOW_AMENDMENT_SHA256)
    create(root/'ROWS.json',value['rows']);create(root/'UNSUPPORTED_GOLD.json',value['unsupported_gold'])
    create(root/'INPUT_BINDING.json',binding)
    create(root/'INPUT_SUMMARY.json',{k:v for k,v in value.items() if k not in ('rows','unsupported_gold')})
    create(root/'FROZEN.json',dict(rows_sha256=sha(root/'ROWS.json'),binding_sha256=sha(root/'INPUT_BINDING.json'),
        exclusions_sha256=sha(root/'UNSUPPORTED_GOLD.json'),utc=datetime.now(timezone.utc).isoformat(),
        actual_symbolic_attempts=0))


def hard_timer(seconds):
    def stop():
        for child in multiprocessing.active_children():
            try:child.kill();child.join(timeout=2)
            except (ProcessLookupError,AssertionError):pass
        os._exit(124)
    timer=threading.Timer(seconds,stop);timer.daemon=True;timer.start();return timer


def score(args,first):
    root=Path(args.root);review=accepted(args.code_review);frozen=read(root/'FROZEN.json')
    for key,name in [('rows_sha256','ROWS.json'),('binding_sha256','INPUT_BINDING.json'),
                     ('exclusions_sha256','UNSUPPORTED_GOLD.json')]:
        if frozen[key]!=sha(root/name):raise ValueError('Frozen original P1 input changed')
    rows=read(root/'ROWS.json');binding=read(root/'INPUT_BINDING.json')
    if binding['source_files']!=review['source_files']:raise ValueError('Original P1 source set changed')
    if {n:importlib.metadata.version(n) for n in VERSIONS}!=VERSIONS:
        raise ValueError('Pinned real scorer environment required')
    timing=None;wall=FIRST_WALL_SECONDS
    if not first:
        timing=read(args.timing_review);proposal=read(root/'FIRST100_PROPOSAL.json')
        if (timing.get('scope')!='p009-math-p1-first100-throughput'
                or timing.get('decision') not in ('PASS','PASS-WITH-NOTES')
                or len(timing.get('report_commit',''))!=40
                or sha(timing['local_report_path'])!=timing['report_sha256']
                or timing.get('proposal_sha256')!=sha(root/'FIRST100_PROPOSAL.json')
                or timing.get('local_window_amendment_sha256')!=OWNER_WINDOW_AMENDMENT_SHA256
                or timing.get('driver_source_files')!=review['source_files']
                or type(timing.get('approved_total_wall_seconds')) is not int
                or not proposal['serial_time_scenario_seconds']<=timing['approved_total_wall_seconds']
                    <=MAXIMUM_TOTAL_SCENARIO_SECONDS):
            raise ValueError('True exact measured first100 numerical review required')
        elapsed=read(root/'FIRST100_COMPLETED.json')['total_command_seconds']
        if not math.isfinite(elapsed) or elapsed<0:raise ValueError('Invalid original command timing')
        wall=timing['approved_total_wall_seconds']-elapsed
        if wall<=0:raise ValueError('No reviewed remaining local window')
    intent=root/('FIRST100_STARTED.json' if first else 'REMAINDER_STARTED.json')
    create(intent,dict(utc=datetime.now(timezone.utc).isoformat(),wall_seconds=wall,
        rows_sha256=frozen['rows_sha256'],no_retry=True,model_calls=0))
    start=time.monotonic();timer=hard_timer(wall)
    try:
        with JournaledPool(root/'journal',rows,binding) as journal:
            if first:
                if journal.position!=0:raise ValueError('First100 already attempted; no replay')
                result=journal.score_next(min(100,len(rows)))
                proposal=first100_forecast(journal.basis,result,
                    read(root/'journal/chunks/00000/TIMING.json'),rows)
                proposal.update(basis_sha256=digest(journal.basis),
                    first100_result_sha256=sha(root/'journal/chunks/00000/RESULT.json'),
                    driver_source_files=review['source_files'],
                    original_unsupported_gold_rows=len(read(root/'UNSUPPORTED_GOLD.json')),
                    maximum_future_local_wall_seconds=MAXIMUM_TOTAL_SCENARIO_SECONDS,
                    local_window_amendment_sha256=OWNER_WINDOW_AMENDMENT_SHA256)
                create(root/'FIRST100_PROPOSAL.json',proposal)
            else:
                if journal.position!=min(100,len(rows)):
                    raise ValueError('Only the original fully committed first100 may precede this one remainder')
                while journal.position<len(rows):
                    if time.monotonic()-start>=wall-10:raise TimeoutError('Reviewed local remaining window exhausted')
                    journal.score_next(min(100,len(rows)-journal.position),timing_review=timing)
                results=[row for _,_,result in journal.completed for row in result['rows']]
                samples={}
                for name in DATASET_ORDER:
                    selected=[r for r in rows if r['dataset']==name]
                    ids={r['id'] for r in selected}
                    samples[name]=audit_samples(selected,[x for x in results if x['id'] in ids])
                    excluded=[x for x in read(root/'UNSUPPORTED_GOLD.json') if x['dataset']==name]
                    samples[name]['structurally_unsupported_gold_rows']=len(excluded)
                    samples[name]['unsupported_gold_exclusions']=excluded
                create(root/'ALL_SCORED_ROWS.json',results);create(root/'FIXED_AUDIT_SAMPLES.json',samples)
                create(root/'ALL_ROWS_SCORED.json',dict(rows=len(results),technical_unknown=0,
                    independent_adjudication_complete=False,eligibility_admitted=False,G0_admitted=False,
                    primary_labels_changed=False,raw_decode_repeated=False,model_calls=0))
        create(root/('FIRST100_COMPLETED.json' if first else 'REMAINDER_COMPLETED.json'),
            dict(total_command_seconds=time.monotonic()-start,utc=datetime.now(timezone.utc).isoformat(),
                 evidence_writes_included_except_this_record=True,model_calls=0))
    except BaseException as exc:
        create(root/('FIRST100_FAILURE.json' if first else 'REMAINDER_FAILURE.json'),
            dict(type=type(exc).__name__,error=str(exc),no_retry=True,partial_evidence_preserved=True))
        raise
    finally:timer.cancel()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','first100','remaining'])
    p.add_argument('--root',required=True);p.add_argument('--code-review',required=True)
    for n in ('generation-root','inputs','generation-admission','timing-review'):p.add_argument('--'+n)
    a=p.parse_args()
    if a.action=='freeze' and any(not getattr(a,n) for n in ('generation_root','inputs','generation_admission')):
        p.error('freeze requires complete generation root, original inputs and exact generation admission')
    if a.action=='remaining' and not a.timing_review:p.error('remaining requires real first100 timing review')
    freeze(a) if a.action=='freeze' else score(a,a.action=='first100')
