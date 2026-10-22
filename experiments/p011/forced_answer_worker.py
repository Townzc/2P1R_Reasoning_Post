"""One isolated cell per subprocess; literal token continuation, no training."""
import argparse
from pathlib import Path
import time
from experiments.p011.owner_0205_common import create, digest, read, sha, utc
from experiments.p011.forced_answer import SUFFIX, forced_sampling

STORE = 'p011-forced-answer-20261022-v1'
REMOTE = '/evidence/p011-20261022-forced-answer-v1'


def snapshot(store, volume, cell, out, status, files):
    for p in sorted(out.rglob('*')):
        name=str(p.relative_to(out))
        if p.is_file() and name not in files:
            files[name]={'bytes':p.stat().st_size,'sha256':sha(p)}
    volume.commit()
    store.put('cell/'+cell, {'cell':cell,'status':status,'files':files,'observed_utc':utc()})
    return files


def run(cell, deadline):
    import modal
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from experiments.p011.long_execution import engine_settings
    volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    store=modal.Dict.from_name(STORE,create_if_missing=False)
    inputs=Path(REMOTE)/'inputs';manifest=read(inputs/'INPUT_MANIFEST.json');cfg=manifest['cells'][cell]
    request_path=inputs/cell/'REQUESTS.json'
    if sha(request_path)!=cfg['request_file_sha256']:raise ValueError('Reviewed new forced requests changed')
    requests=read(request_path)
    if [r['id'] for r in requests]!=cfg['ids']:raise ValueError('Forced subset/order differs')
    out=Path(REMOTE)/'results'/cell;out.mkdir(parents=True,exist_ok=False)
    create(out/'INTENT.json',{'cell':cell,'started_utc':utc(),'deadline_epoch':deadline,
        'model_path':cfg['model_path'],'model_files':cfg['model_files'],'requests_sha256':cfg['request_file_sha256'],
        'suffix_ids_sha256':manifest['suffix_sha256'],'greedy_max_new_tokens':64,'automatic_retry':False})
    files={};snapshot(store,volume,cell,out,'started',files)
    try:
        if not requests:
            create(out/'COMPLETED.json',{'cell':cell,'completed_utc':utc(),'rows':0,
                'original_primary_results_changed':False,'model_loaded':False})
            snapshot(store,volume,cell,out,'completed',files)
            return
        for name,want in cfg['model_files'].items():
            p=Path(cfg['model_path'])/name
            if p.stat().st_size!=want['bytes'] or sha(p)!=want['sha256']:
                raise ValueError('Same-checkpoint model-byte binding differs')
        tok=AutoTokenizer.from_pretrained(cfg['model_path'],local_files_only=True)
        if tok.encode(SUFFIX,add_special_tokens=False)!=manifest['suffix_ids']:
            raise ValueError('Pinned student suffix token IDs differ in model tokenizer')
        llm=LLM(model=cfg['model_path'],tokenizer=cfg['model_path'],**engine_settings(cfg['required_context']))
        params=forced_sampling(cfg['eos_token_ids'])
        create(out/'ENGINE_AND_SAMPLING.json',{'engine_settings':engine_settings(cfg['required_context']),'sampling':params})
        for offset in range(0,len(requests),128):
            if time.time()>=deadline:raise TimeoutError('Authorized shared worker hard timer reached')
            part=requests[offset:offset+128]
            create(out/'intents'/f'{offset:05d}.json',{'row_ids':[r['id'] for r in part],'requests_sha256':digest(part)})
            snapshot(store,volume,cell,out,'running',files)
            returned=llm.generate([{'prompt_token_ids':r['prompt_token_ids']} for r in part],SamplingParams(**params),use_tqdm=False)
            raw=[]
            for i,obj in enumerate(returned):
                row=part[i] if i<len(part) else None
                raw.append({'id':row['id'] if row else None,'request_sha256':digest(row) if row else None,
                    'prompt_token_ids':list(obj.prompt_token_ids),'sampling':params,
                    'answers':[{'token_ids':list(a.token_ids),'backend_text':a.text,'finish_reason':a.finish_reason,'stop_reason':a.stop_reason} for a in obj.outputs]})
            # Preserve raw backend output before shape checks; no automatic retry.
            create(out/'raw'/f'{offset:05d}.json',raw);snapshot(store,volume,cell,out,'running',files)
            if len(raw)!=len(part) or any(r['id']!=q['id'] or r['prompt_token_ids']!=q['prompt_token_ids'] or len(r['answers'])!=1 for r,q in zip(raw,part)):
                raise ValueError('Forced backend response shape differs')
            create(out/'completed'/f'{offset:05d}.json',{'rows':len(raw),'raw_sha256':files[f'raw/{offset:05d}.json']['sha256']})
            snapshot(store,volume,cell,out,'running',files)
        create(out/'COMPLETED.json',{'cell':cell,'completed_utc':utc(),'rows':len(requests),'original_primary_results_changed':False})
        snapshot(store,volume,cell,out,'completed',files)
    except BaseException as exc:
        create(out/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False})
        snapshot(store,volume,cell,out,'failed',files)
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cell',required=True);p.add_argument('--deadline',type=float,required=True)
    a=p.parse_args();run(a.cell,a.deadline)
