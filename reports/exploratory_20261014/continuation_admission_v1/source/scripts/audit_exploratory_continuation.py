"""Full merged endpoint oracle: original independently verified prefix plus new raw suffix."""
import argparse,datetime,json
from collections import Counter
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
from experiments.sft_exploratory_20261014.continuation_prefix import inspect_prefix
from experiments.sft_exploratory_20261014.continuation_binding import validate_release,parent_records,marker
from experiments.sft_exploratory_20261014.cached_audit import audit_batch
from src.sft_data import read_jsonl


def audit(a):
    from transformers import AutoTokenizer
    root,inputs,parent=Path(a.export_dir),Path(a.inputs),Path(a.parent_preservation)
    spec=read(a.admission);sent=read(root/'intent.json');cfg=sent['config'];run=cfg['run_id'];logical=cfg['logical_run']
    if read(root/'admission.json')!=spec:raise ValueError('Exact admission differs')
    validate_release(spec,sent['plan'],cfg,sent['release'])
    if a.campaign!=sent['plan']['campaign_id']:raise ValueError('Foreign campaign')
    base='midpoint/'+a.campaign+'/';db=read(a.ledger);env=read(a.receipt);receipt=env['receipt']
    if receipt!=db[base+'terminal/'+run] or receipt['status']!='completed':raise ValueError('Real completed terminal required')
    claim,bound=db[base+'claim/'+run],db[base+'intent/'+run]
    if (claim['intent_sha256']!=digest(bound) or claim['plan_sha256']!=digest(sent['plan']) or
            receipt['claim_sha256']!=digest(claim) or bound['config_sha256']!=digest(cfg) or
            bound['source_sha256']!=digest(sent['release']['source_files']) or
            bound['data_sha256']!=cfg['input_sha256']):raise ValueError('Original claim binding differs')
    for key,value in parent_records(spec,cfg).items():
        if db[key]!=value:raise ValueError('Failed parent changed')
    key,value=marker(spec,cfg)
    if db[key]!=value or read(root/'PARENT_SUFFIX_CLAIM.json')!=dict(key=key,value=value):raise ValueError('Suffix lineage differs')
    files=read(root/'artifact_manifest.json')
    if files!=env['artifact_manifest'] or digest(files)!=receipt['evidence_sha256']:raise ValueError('Actual evidence manifest differs')
    verify(root,files)
    if sha(inputs/'manifest.json')!=cfg['input_sha256']:raise ValueError('Input release changed')
    verify(inputs,read(inputs/'manifest.json')['files'])
    if logical=='instruct_0shot':
        model=read(root/'official_model_readback.json');lock=read(inputs/'instruct_model_lock.json')
        if (model['lock']!=lock or model['reused'] is not True or
                model['download']['bytes']!=lock['weight']['size'] or
                model['download']['sha256']!=lock['weight']['sha256']):
            raise ValueError('Pinned reused Instruct model differs')
    binding,predictions=inspect_prefix(parent,inputs,spec['parent_ledger'],logical,spec['original_admission'])
    if binding!=spec['prefix_proofs'][logical]['binding']:raise ValueError('Previously decoded prefix bytes changed')
    # The 496 original raw outputs were independently decoded before admission;
    # this is hash-bound reuse, not a claim that parent acknowledgements exist.
    tok=AutoTokenizer.from_pretrained(a.tokenizer,local_files_only=True)
    rows=read_jsonl(inputs/'gsm8k_test1319.jsonl');prompts=read(inputs/(logical+'_prompts.json'))
    eos=[151645,151643] if logical=='instruct_0shot' else [tok.eos_token_id]
    recipe=read(root/'recipe.json')
    if (recipe['original_config']!=spec['original_admission']['configs'][logical] or
            recipe['prefix_binding']!=binding or recipe['training'] is not False or
            recipe['new_training_updates']!=0 or recipe['eos_ids']!=eos or
            recipe['parser']!='marked_answer_v1' or recipe['greedy'] is not True):
        raise ValueError('Frozen scientific recipe differs')
    expected=set();raw_names=set();scored_names=set()
    for start in range(cfg['offset'],1319,16):
        unit=f'endpoint1319_batch_{start:04d}';expected.add(unit)
        rawname=f'batch_{start:04d}_raw.json';scoredname=f'batch_{start:04d}_scored.jsonl'
        raw_names.add(rawname);scored_names.add(scoredname)
        raw=read(root/'endpoint1319'/rawname);records=read_jsonl(root/'endpoint1319'/scoredname)
        audit_batch(raw,records,rows[start:start+16],prompts[start:start+16],tok,eos)
        intent=dict(problem_ids=[r['problem_id'] for r in rows[start:start+16]],count=len(records),
                    config=dict(max_new_tokens=512,max_length=2048,eval_batch_size=16))
        done=dict(count=len(records),raw_sha256=sha(root/'endpoint1319'/rawname),scored_sha256=sha(root/'endpoint1319'/scoredname))
        if (read(root/'intents'/(unit+'.json'))!=intent or db[base+run+'/unit/'+unit]!=intent or
                read(root/'completed'/(unit+'.json'))!=done or db[base+run+'/done/'+unit]!=done):
            raise ValueError('New exact once-only batch acknowledgement differs')
        predictions.extend(records)
    if ({p.stem for p in (root/'intents').glob('*.json')}!=expected or
            {p.stem for p in (root/'completed').glob('*.json')}!=expected or
            {k.removeprefix(base+run+'/unit/') for k in db if k.startswith(base+run+'/unit/')}!=expected or
            {p.name for p in (root/'endpoint1319').glob('*_raw.json')}!=raw_names or
            {p.name for p in (root/'endpoint1319').glob('*_scored.jsonl')}!=scored_names):
        raise ValueError('Repeated prefix, hidden training, or omitted suffix')
    if [r['problem_id'] for r in predictions]!=[r['problem_id'] for r in rows]:raise ValueError('Full merged roster differs')
    summary=dict(n=len(predictions),correct=sum(r['task_score']['task_answer_correct'] for r in predictions),
        parsed=sum(r['task_score']['marked']['status']=='parsed' for r in predictions),
        stop_reasons=dict(Counter(r['stop']['stop_reason'] for r in predictions)),
        generated_tokens=sum(r['generated_tokens'] for r in predictions),
        padded_tokens=sum(r['batch_generated_steps'] for r in predictions),
        question_correct={r['problem_id']:r['task_score']['task_answer_correct'] for r in predictions})
    result=read(root/'result.json')
    if (result!=env['result'] or result['endpoint']!=summary or read(root/'endpoint1319/summary.json')!=summary or
            result['new_training_updates']!=0 or result['new_training_targets']!=0 or
            result['saved_prefix_rows']!=cfg['offset'] or result['newly_generated_rows']!=1319-cfg['offset']):
        raise ValueError('Actual full result/dose differs')
    if logical=='wrong_teacher_t1':
        restored=read(root/'CHECKPOINT_RESTORED.json')
        if (restored['passed'] is not True or restored['original_manifest']!=spec['checkpoint_verified']['manifest'] or
                restored['new_training_updates']!=0 or restored['adapter_exact'] is not True or
                restored['optimizer_exact'] is not True or restored['rng_restored'] is not True or
                restored['original_identity']!=read(parent/'recipe.json')['identity'] or
                result['original_training_updates']!=256 or result['original_training_targets']!=524287):
            raise ValueError('Exact original checkpoint restoration/dose differs')
    return dict(passed=True,run_id=run,logical_run=logical,endpoint=summary,new_training_updates=0,
         independently_verified_saved_prefix_rows=cfg['offset'],new_raw_rows=1319-cfg['offset'],
         original_unacknowledged_rows_preserved=16,duplicate_generation=0,technical_unknown=0,
         failed_parent_retained=True,checkpoint_state_reloaded_locally=False,
         source_sha256=digest(sent['release']['source_files']),spec_sha256=digest(spec),
         receipt_file_sha256=sha(a.receipt),ledger_file_sha256=sha(a.ledger),
         finished_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('campaign','export-dir','inputs','tokenizer','receipt','ledger','admission','parent-preservation','out'):
        p.add_argument('--'+key,required=True)
    a=p.parse_args();result=audit(a);dump(a.out,result);print(json.dumps(result))
