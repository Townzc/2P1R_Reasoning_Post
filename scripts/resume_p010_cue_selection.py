"""Unattempted exact local infinity repair; requires delegate approval and A2."""
import argparse,datetime,os,threading,time
from pathlib import Path
from experiments.p010.common import read,dump,sha,verify,utc
from experiments.p010.cue_key_resume import resume_rows
from experiments.p010.cue_selection import select
from experiments.p010.cue_key_process import LOCAL_SECONDS
from scripts.audit_p010_cue_search import expire_owned_parser


def execute(root,owner_file,review_file):
    r=Path(root);packet=Path('reports/p010_20261019/c6_nonfinite_resume_preflight_v1')
    spec=read(packet/'SPEC.json');owner=read(owner_file);review=read(review_file)
    scope='p010-C6-nonfinite-local-selection-resume-A2'
    if (owner['decision']!='APPROVE_ONE_LOCAL_NONFINITE_CONTINUATION' or owner['scope']!=scope
            or owner['original_failure_manifest_sha256']!=spec['original_failure_manifest_sha256']
            or not owner['confirmed_keys_reused_without_reparse'] or not owner['no_new_model_outputs']
            or sha(owner['local_decision_file'])!=owner['decision_source_sha256']
            or review['scope']!=scope or review['decision'] not in ('PASS','PASS-WITH-NOTES')
            or sha(review['local_report_file'])!=review['report_sha256']
            or review['spec_sha256']!=sha(packet/'SPEC.json') or review['source_files']!=spec['source_files']
            or review['owner_decision_source_sha256']!=owner['decision_source_sha256']):
        raise ValueError('Actual scoped delegated decision and independent exact audit required')
    for name,value in spec['source_files'].items():
        if sha(name)!=value:raise ValueError('Exact new source changed: '+name)
    prior=r/'cue_selection_r1';oracle=r/'cue_search_oracle_r1';proposal=r/'cue_search_export_r1/evidence/PROPOSAL.json';dev=r/'cue_inputs_r1/DEV_PROMPTS.json'
    if sha(packet/'ORIGINAL_FAILURE_FILES.json')!=spec['original_failure_manifest_sha256']:
        raise ValueError('Original failure file roster changed')
    verify(prior,read(packet/'ORIGINAL_FAILURE_FILES.json'))
    if (sha(oracle/'COMPLETED.json')!=spec['original_oracle_sha256']
            or sha(oracle/'DECODED_ROWS.json')!=spec['original_decoded_rows_sha256']
            or sha(proposal)!=spec['original_proposal_sha256'] or sha(dev)!=spec['original_dev_sha256']):
        raise ValueError('Original full raw/proposal/dev evidence changed')
    cutoff=datetime.datetime(2026,10,21,19,tzinfo=datetime.timezone.utc).timestamp()
    cap=min(LOCAL_SECONDS,int(cutoff-time.time()-30));scenario=1.2*(6380*8+300)
    if cap<scenario:raise TimeoutError('Original bounded local completion window unavailable')
    out=r/'cue_selection_nonfinite_r1';out.mkdir(parents=True,exist_ok=False)
    started=time.time();dump(out/'INTENT.json',dict(utc=utc(),spec_sha256=sha(packet/'SPEC.json'),owner_decision_source_sha256=owner['decision_source_sha256'],review_report_sha256=review['report_sha256'],local_cap_seconds=cap,scenario_seconds=scenario,not_expected_or_guaranteed_runtime=True,new_model_calls=0,automatic_retry=False))
    timer=threading.Timer(cap+5,expire_owned_parser);timer.daemon=True;timer.start()
    try:
        observations=resume_rows(read(oracle/'DECODED_ROWS.json'),prior,out/'grouping',started+cap)
        result=select([[]]+[x['token_ids'] for x in read(proposal)['candidates']],[x['problem_id'] for x in read(dev)],observations)
        dump(out/'SELECTION.json',result)
        done=dict(utc=utc(),passed=True,selection_sha256=sha(out/'SELECTION.json'),original_oracle_sha256=sha(oracle/'COMPLETED.json'),spec_sha256=sha(packet/'SPEC.json'),selected_token_ids=result['selected_token_ids'],selected_candidate=result['selected_candidate'],elapsed_seconds=time.time()-started,gold_used=False,correctness_used=False,test_data_used=False,technical_unknown=0,independent_A3_pending=True)
        dump(out/'COMPLETED.json',done);return done
    except BaseException as exc:
        dump(out/'FAILED.json',dict(utc=utc(),type=type(exc).__name__,error=str(exc),partial_valid_parts_preserved=True,automatic_retry=False));raise
    finally:timer.cancel()

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('root','owner-decision','review'):p.add_argument('--'+name,required=True)
    a=p.parse_args();print(execute(a.root,a.owner_decision,a.review))
