"""One explicitly evidenced infrastructure continuation from a committed state.

This is not an automatic retry controller. It never allocates a model, replays
training, downloads checkpoint binaries, or relabels a scientific/cap failure.
"""
import argparse
import re
import json
from pathlib import Path
import subprocess
import time
from experiments.p011.ext4b_runtime_contract import SPEC,LOCAL,REMOTE,STORE,review,JOBS
from experiments.p011.ext4b_path import ACTUAL
from experiments.p011.c1_outer import closed_provider
from experiments.p011.owner_0205_common import create,read,sha,digest,utc


def classify_evidence(kind,text,quote):
    if not quote or quote not in text:raise ValueError('Verbatim observed infrastructure evidence required')
    if re.search(r'exit(?:ed)?(?:\s+with)?(?:\s+code)?\s*[:=]?\s*124|hard.?timer|nonfinite|NaN|out of memory|CUDA.*assert',text,re.I):
        raise ValueError('Hard-cap/scientific/resource failure cannot use infrastructure resume')
    patterns={'provider_preemption':r'preempt|evict','network':r'connection (?:reset|lost)|network|unavailable|disconnect',
              'container_crash':r'container.*(?:crash|lost|terminated)|worker.*(?:crash|lost)'}
    if kind not in patterns or not re.search(patterns[kind],quote,re.I):raise ValueError('Unproven infrastructure classification')
    return True


def main():
    p=argparse.ArgumentParser();p.add_argument('--job',choices=JOBS,required=True);p.add_argument('--source-review',required=True);p.add_argument('--actual-review',required=True)
    p.add_argument('--failure-class',required=True);p.add_argument('--evidence-file',required=True);p.add_argument('--evidence-quote',required=True);a=p.parse_args()
    review(SPEC,a.source_review,a.actual_review);evidence=Path(a.evidence_file);text=evidence.read_text()
    classify_evidence(a.failure_class,text,a.evidence_quote)
    name=a.job+'_attempt1';dispatch=LOCAL/'dispatch'/name;intent=read(dispatch/'INTENT.json');error=read(dispatch/'RETURN_ERROR.json');sub=read(dispatch/'SUBMITTED.json')
    if (dispatch/'RESULT.json').exists() or (LOCAL/'dispatch'/(a.job+'_attempt2')).exists():raise ValueError('Successful parent or second resume forbidden')
    out=LOCAL/'resume_authorization'/a.job;out.mkdir(parents=True,exist_ok=False);create(out/'ATTEMPT.json',{'utc':utc(),'failure_class':a.failure_class,'no_model_or_binary_download':True})
    try:
        import modal
        cli='.local/midpoint_20261011/venv/bin/modal'
        info=json.loads(subprocess.check_output([cli,'app','info',sub['app_id'],'--json'],text=True,timeout=60));containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True,timeout=60));observed=time.time()
        stopped=closed_provider(sub['app_id'],info,containers,observed);create(out/'PROVIDER_RAW.json',{'app':info,'containers':containers});create(out/'PROVIDER_STOPPED0.json',stopped)
        store=modal.Dict.from_name(STORE,create_if_missing=False);claim=store.get(name+'/claim');terminal=store.get(name+'/terminal')
        if store.get(name+'/dispatch')!=intent or store.get(a.job+'/single_resume_fence') is not None or not claim or (terminal or {}).get('status')=='completed':raise ValueError('Exact failed parent with no consumed resume required')
        if terminal and terminal.get('type') in ('TimeoutError','ValueError','AssertionError'):raise ValueError('Known hard-window/scientific validation failure is not infrastructure')
        volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False);remote=REMOTE+'/runs/'+name
        inventory=list(volume.iterdir(remote.removeprefix('/evidence'),recursive=True));names={x.path.removeprefix(remote.removeprefix('/evidence').lstrip('/')+'/'):x for x in inventory}
        # Normalize the volume API's leading slash without assuming a missing file.
        names={x.path.lstrip('/').removeprefix(remote.removeprefix('/evidence').lstrip('/')+'/'):x for x in inventory}
        create(out/'REMOTE_INVENTORY.json',[{'path':x.path,'size':x.size,'type':str(x.type)} for x in inventory])
        fetched={}
        def get(n):
            if n not in fetched:
                raw=b''.join(volume.read_file((remote+'/'+n).removeprefix('/evidence')));dest=out/'metadata'/n;dest.parent.mkdir(parents=True,exist_ok=True)
                with dest.open('xb') as f:f.write(raw)
                fetched[n]=json.loads(raw)
            return fetched[n]
        if get('IDENTITY.json')!=intent['identity'] or get('CLAIM.json')!=claim:raise ValueError('Original claimed identity differs')
        timing=get('TIMING_POLICY.json');candidates=[]
        for n in names:
            if re.fullmatch(r'checkpoint_\d+/manifest.json',n):
                m=get(n);step=m.get('step',0)
                if (m.get('identity_sha256')==digest(intent['identity']) and m.get('file')=='state.pt'
                        and 0<step<=intent['job_spec']['U'] and (step%500==0 or step==intent['job_spec']['U'])):
                    state=names.get(str(Path(n).parent/'state.pt'))
                    if state is not None and state.size==m['bytes']:candidates.append((step,n,m))
        if not candidates:raise ValueError('No committed checkpoint: restarting from zero is not a resume')
        step,n,record=max(candidates)
        training_complete=all(n in names for n in ['TRAINING_PROCESS_RESULT.json','TRAINING_EXIT.json','MODEL_EXPORT.json','completed/terminal_model_export.json'])
        if training_complete and step!=intent['job_spec']['U']:raise ValueError('Terminal state inconsistency')
        for batch in range(7):
            ack=f'completed/eval_{batch:04d}.json';cycle=f'endpoint_cycles/eval_{batch:04d}.json'
            if ack in names and cycle not in names:raise ValueError('Completed generation without cycle evidence is retained, not repeated')
        failure={'infrastructure_failure_confirmed':True,'classification':a.failure_class,'raw_evidence_path':str(evidence),
            'raw_evidence_sha256':sha(evidence),'verbatim_observed_evidence':a.evidence_quote,'provider_STOPPED_owned_zero':True,
            'stopped_observed_epoch':observed,'scientific_or_hard_cap_failure':False,'original_error':error,'original_remote_terminal':terminal}
        value={'parent_intent':intent,'parent_claim':claim,'identity':intent['identity'],'checkpoint':remote+'/'+str(Path(n).parent),
            'checkpoint_record':record,'parent_output':remote,'original_timing':timing,'failure':failure,'training_terminal_complete':training_complete,
            'maximum_resumes':1,'checkpoint_binary_downloaded':False,'uncheckpointed_failed_attempt_tail_retained':True,
            'replay_from_checkpoint_may_repeat_uncheckpointed_tail':True,'new_fresh_budget_still_required':True}
        create(out/'RESUME.json',value);create(out/'COMPLETED.json',{'utc':utc(),'resume_sha256':sha(out/'RESUME.json'),'checkpoint_step':step,'not_GPU_authorization_without_fresh_budget':True});print(out/'RESUME.json')
    except BaseException as exc:create(out/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False});raise


if __name__=='__main__':main()
