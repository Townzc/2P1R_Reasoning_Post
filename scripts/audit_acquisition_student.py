"""Local-only P007B full-state/dose and raw endpoint oracle, no model execution."""
import argparse
import datetime
from pathlib import Path
from collections import Counter
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
from experiments.sft_allocation_midpoint import checkpoint as ck
from scripts.audit_midpoint_local import verify_selected
from src.sft_data import read_jsonl,encode_row,budget_report,prefix
from analyses.e017_audit import audit_predictions

EVAL=dict(max_new_tokens=512,max_length=2048,eval_batch_size=16)

def audit(args):
    from transformers import AutoTokenizer
    root=Path(args.export_dir);inputs=Path(args.inputs);envelope=read(args.receipt);ledger=read(args.ledger)
    sent=read(root/'intent.json');cfg=sent['config'];run=cfg['run_id'];base='midpoint/'+args.campaign+'/'
    admission=read('reports/sft_allocation_midpoint_20261011/P007B_STUDENT_ADMISSION.json')
    assert digest(cfg)==admission['config_sha256'][run] and digest(sent['plan'])==admission['plan_sha256']
    assert sha(inputs/'manifest.json')==cfg['input_sha256'];verify(inputs,read(inputs/'manifest.json')['files'])
    receipt=envelope['receipt'];assert receipt==ledger[base+'terminal/'+run] and receipt['status']=='completed'
    claim=ledger[base+'claim/'+run];bound=ledger[base+'intent/'+run]
    assert claim['intent_sha256']==digest(bound) and claim['plan_sha256']==digest(sent['plan'])
    assert bound['config_sha256']==digest(cfg) and bound['source_sha256']==digest(sent['release']['source_files'])
    assert bound['data_sha256']==cfg['input_sha256'] and receipt['claim_sha256']==digest(claim)
    assert receipt['attempt_id']==claim['attempt_id'] and ledger[base+'attempt/'+run+'/'+claim['attempt_id']]==claim
    files=read(root/'artifact_manifest.json');assert files==envelope['artifact_manifest'] and digest(files)==receipt['evidence_sha256']
    transport=read(root/'LOCAL_VERIFICATION.json');assert transport['campaign']==args.campaign and transport['run']==run
    assert transport['full_checkpoint_steps']==[256];verify_selected(root,files,[256])
    result=read(root/'result.json');assert result==envelope['result'] and result['status']=='completed'
    tok=AutoTokenizer.from_pretrained(args.tokenizer,local_files_only=True)
    train_rows=read_jsonl(inputs/f"{cfg['cell']}_train.jsonl")
    encoded=[encode_row(r,tok,2048) for r in train_rows]
    plan=read(inputs/f"{cfg['cell']}_seed{cfg['seed']}.json");schedule=plan['updates']
    import json
    budget=budget_report(encoded,schedule,1)
    assert json.loads(json.dumps(budget))==plan['budget']==result['budget']
    assert budget['supervised_response_tokens']==524288 and budget['optimizer_updates']==256
    counts=Counter(i for batch in schedule for i in batch)
    assert set(counts)==set(range(len(train_rows))) and max(counts.values())-min(counts.values())<=1
    recipe=read(root/'recipe.json');assert recipe['identity']['config']==cfg and recipe['eval']==EVAL
    state=ck.load(root/'checkpoint_0256',recipe['identity'])
    assert state['step']==state['cursor']==result['committed_updates']==256
    assert state['supervised_tokens']==result['supervised_tokens']==524288
    assert state['schedule']==schedule and state['lrs']==recipe['lrs']==cfg['lrs']
    intents={p.stem:read(p) for p in (root/'intents').glob('*.json')}
    done={p.stem:read(p) for p in (root/'completed').glob('*.json')}
    assert set(intents)==set(done)
    for kind,local in (('unit',intents),('done',done)):
        key=base+run+'/'+kind+'/'
        assert {k[len(key):] for k in ledger if k.startswith(key)}==set(local)
        assert all(ledger[key+k]==v for k,v in local.items())
    expected=set();targets=processed=0
    for step,indices in enumerate(schedule,1):
        name=f'update_{step:04d}';expected.add(name)
        item=dict(step=step,indices=indices,lr=state['lrs'][step-1],
                  supervised_tokens=sum(encoded[i]['n_supervised'] for i in indices),
                  processed_tokens=sum(encoded[i]['n_processed'] for i in indices))
        assert intents[name]==item and all(done[name][k]==v for k,v in item.items())
        targets+=item['supervised_tokens'];processed+=item['processed_tokens']
        assert done[name]['cumulative_targets']==targets and done[name]['cumulative_processed']==processed
    assert targets==524288 and processed==state['processed_tokens']==result['processed_tokens']
    rows=read_jsonl(inputs/'gsm8k_test1319.jsonl');assert len(rows)==1319
    saved=[]
    for start in range(0,1319,16):
        part=rows[start:start+16];unit=f'endpoint1319_batch_{start:04d}';expected.add(unit)
        assert intents[unit]==dict(problem_ids=[r['problem_id'] for r in part],count=len(part),config=EVAL)
        rawfile=root/'endpoint1319'/f'batch_{start:04d}_raw.json';scored=root/'endpoint1319'/f'batch_{start:04d}_scored.jsonl'
        assert sha(rawfile)==done[unit]['raw_sha256'] and sha(scored)==done[unit]['scored_sha256']
        raw=read(rawfile);rescored=audit_predictions(scored,part,tok,EVAL)
        assert raw['problem_ids']==[r['problem_id'] for r in part]
        assert raw['input_ids']==[tok(prefix(r['prompt']),add_special_tokens=False)['input_ids'] for r in part]
        assert raw['batch_output_ids']==[r['batch_output_ids'] for r in rescored]
        assert raw['events']==[r['stop'] for r in rescored] and len(rescored)==done[unit]['count']
        saved.extend(rescored)
    assert set(done)==expected
    qc={r['problem_id']:r['task_score']['task_answer_correct'] for r in saved}
    assert len(qc)==1319 and all(type(v) is bool for v in qc.values())
    summary=read(root/'endpoint1319/summary.json')
    assert summary==result['endpoint'] and summary['question_correct']==qc and summary['correct']==sum(qc.values())
    assert result['physical_generated_outputs']==len(saved)==1319
    return dict(schema='p007b_independent_student_audit_v1',checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        campaign=args.campaign,run_id=run,cell=cfg['cell'],seed=cfg['seed'],updates_verified=256,
        supervised_tokens_verified=targets,outputs_independently_rescored=1319,correct=sum(qc.values()),
        artifact_digest=digest(files),state_sha256=sha(root/'checkpoint_0256/state.pt'),
        input_sha256=cfg['input_sha256'],new_model_calls=0,external_claude_review='pending')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('campaign','export-dir','inputs','tokenizer','receipt','ledger','out'):p.add_argument('--'+key,required=True)
    a=p.parse_args();result=audit(a);dump(a.out,result);print(__import__('json').dumps(result))
