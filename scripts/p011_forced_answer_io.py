"""New inputs only; once-only collection/native64 oracle/frozen scorer per cell."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import time
from experiments.p011.owner_0205_common import admit, create, digest, read, sha, utc
from experiments.p011.forced_answer import CELLS, decode_continuation
from experiments.p011.forced_answer_worker import REMOTE, STORE

SPEC='reports/p011_20261020/forced_answer_preflight_v1/SPEC.json'


def safe_name(name):
    p=Path(name)
    if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe new evidence member')
    return p


def upload(spec,out):
    import modal
    inputs=Path(spec['input_output']);complete=read(inputs/'COMPLETED.json')
    if sha(inputs/'INPUT_MANIFEST.json')!=complete['manifest_sha256']:raise ValueError('New input manifest differs')
    store=modal.Dict.from_name(STORE,create_if_missing=True)
    if not store.put('upload',{'utc':utc(),'manifest_sha256':complete['manifest_sha256']},skip_if_exists=True):
        raise ValueError('New input upload already attempted')
    volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    names=['INPUT_MANIFEST.json']+[c+'/REQUESTS.json' for c in CELLS]
    inventory={n:{'bytes':(inputs/n).stat().st_size,'sha256':sha(inputs/n)} for n in names}
    with volume.batch_upload(force=False) as batch:
        for name in names:batch.put_file(inputs/name,(REMOTE+'/inputs/'+name).removeprefix('/evidence'))
    for name,wanted in inventory.items():
        h=hashlib.sha256();size=0
        for block in volume.read_file((REMOTE+'/inputs/'+name).removeprefix('/evidence')):h.update(block);size+=len(block)
        if {'bytes':size,'sha256':h.hexdigest()}!=wanted:raise ValueError('New request transfer readback differs')
    create(out/'COMPLETED.json',{'utc':utc(),'input_manifest_sha256':complete['manifest_sha256'],
        'transferred_files':inventory,'original_weights_uploaded':0,'labels_or_gold_uploaded':False})


def collect(spec,out):
    import modal,json
    from experiments.p011.c1_outer import closed_provider
    dispatch=Path(spec['local_root'])/'dispatch';sub=read(dispatch/'SUBMITTED.json')
    if not ((dispatch/'RESULT.json').exists() or (dispatch/'RETURN_ERROR.json').exists()):
        raise ValueError('Original new attempt must be terminal before collecting')
    cli='.local/midpoint_20261011/venv/bin/modal'
    info=json.loads(subprocess.check_output([cli,'app','info',sub['app_id'],'--json'],text=True,timeout=45))
    containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True,timeout=45))
    provider=closed_provider(sub['app_id'],info,containers,time.time())
    create(out/'PROVIDER_RAW.json',{'app':info,'containers':containers});create(out/'PROVIDER_STOPPED0.json',provider)
    store=modal.Dict.from_name(STORE,create_if_missing=False)
    records={k:store.get(k) for k in ['dispatch','claim','terminal']+['cell/'+c for c in CELLS]}
    create(out/'NAMED_RECORDS.json',records)
    if records['dispatch']!=read(dispatch/'INTENT.json'):raise ValueError('New dispatch binding differs')
    volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    for cell in CELLS:
        record=records['cell/'+cell]
        if record is None:continue
        for name,wanted in record['files'].items():
            target=out/'cells'/cell/safe_name(name);target.parent.mkdir(parents=True,exist_ok=True)
            h=hashlib.sha256();size=0
            with target.open('xb') as stream:
                for b in volume.read_file((REMOTE+'/results/'+cell+'/'+name).removeprefix('/evidence')):
                    stream.write(b);h.update(b);size+=len(b)
            if {'bytes':size,'sha256':h.hexdigest()}!=wanted:raise ValueError('New committed cell evidence mismatch')
    create(out/'COMPLETED.json',{'utc':utc(),'cell_statuses':{c:(records['cell/'+c] or {}).get('status','not_started') for c in CELLS},
        'unlisted_or_uncommitted_files_not_claimed':True,'partial_cells_not_scored':True,'prior_evidence_recollected':False})


def audit(spec,out,cell):
    from transformers import AutoTokenizer
    root=Path(spec['local_root']);saved=root/'collect';read(saved/'COMPLETED.json')
    record=read(saved/'NAMED_RECORDS.json')['cell/'+cell]
    if not record or record['status']!='completed':raise ValueError('Only a complete new cell may be decoded/scored')
    cfg=read(Path(spec['input_output'])/'INPUT_MANIFEST.json')['cells'][cell]
    payload=saved/'cells'/cell;complete=read(payload/'COMPLETED.json')
    requests=read(Path(spec['input_output'])/cell/'REQUESTS.json')
    if complete['rows']!=len(requests) or sha(Path(spec['input_output'])/cell/'REQUESTS.json')!=cfg['request_file_sha256']:
        raise ValueError('Exact complete request roster required')
    labels=read(Path(spec['input_output'])/cell/'ORIGINAL_LABELS_AND_GOLD.json')
    if sha(Path(spec['input_output'])/cell/'ORIGINAL_LABELS_AND_GOLD.json')!=cfg['original_labels_file_sha256']:
        raise ValueError('Original local label/gold binding differs')
    tok=AutoTokenizer.from_pretrained(spec['student_tokenizer_path'],local_files_only=True)
    for name,want in spec['student_tokenizer_files'].items():
        if sha(Path(spec['student_tokenizer_path'])/name)!=want:raise ValueError('Pinned decoder changed')
    raw=[]
    for offset in range(0,len(requests),128):
        file=payload/'raw'/f'{offset:05d}.json';ack=read(payload/'completed'/f'{offset:05d}.json')
        part=read(file)
        if ack['rows']!=len(part) or sha(file)!=ack['raw_sha256']:raise ValueError('New batch completion binding differs')
        raw.extend(part)
    if len(raw)!=len(requests):raise ValueError('Full selected cell required')
    decoded=[];rows=[]
    for req,item in zip(requests,raw):
        value=decode_continuation(req,item,cfg['eos_token_ids'],tok,spec['model_vocab_size'])
        decoded.append(value);rows.append({'id':req['id'],'gold':labels['gold'][req['id']],
            'answer_segment':value['answer_segment'],'stop_reason':value['stop_reason'],
            'request_sha256':digest(req),'raw_text_sha256':digest(value['continuation_text']),
            'region_sha256':digest(value['answer_segment']),'last_think_boundary_present':False})
    create(out/'DECODED.json',decoded);create(out/'SCORING_ROWS.json',rows)
    create(out/'COMPLETE_PROOF.json',{'utc':utc(),'cell':cell,'new_continuations_decoded':len(rows),
        'original16384_token_streams_redecoded':0,'original_training_oracle_repeated':False,
        'scoring_rows_sha256':sha(out/'SCORING_ROWS.json'),'technical_unknown':0,'actual_A3_accepted':False})


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['upload','collect','audit','score']);p.add_argument('--review',required=True);p.add_argument('--cell',choices=CELLS)
    a=p.parse_args();spec=admit(SPEC,a.review,'p011-forced-answer-complete-path-CR')
    if a.mode in ('audit','score') and not a.cell:raise ValueError('Exact cell required')
    out=Path(spec['local_root'])/a.mode
    if a.cell:out=out/a.cell
    if a.mode=='score':
        from experiments.p011.forced_answer_score_process import supervise
        audit_dir=Path(spec['local_root'])/'audit'/a.cell;proof=read(audit_dir/'COMPLETE_PROOF.json')
        if sha(audit_dir/'SCORING_ROWS.json')!=proof['scoring_rows_sha256']:raise ValueError('New oracle rows changed')
        supervise(out,read(audit_dir/'SCORING_ROWS.json'),{'oracle_sha256':sha(audit_dir/'COMPLETE_PROOF.json'),
            'source_CR_sha256':sha(a.review),'spec_sha256':sha(SPEC)},7200)
        return
    out.mkdir(parents=True,exist_ok=False);create(out/'ATTEMPT.json',{'utc':utc(),'mode':a.mode,'cell':a.cell,'source_CR_sha256':sha(a.review),'automatic_retry':False})
    try:
        if a.mode=='upload':upload(spec,out)
        elif a.mode=='collect':collect(spec,out)
        else:audit(spec,out,a.cell)
    except BaseException as exc:
        create(out/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False});raise


if __name__=='__main__':main()
