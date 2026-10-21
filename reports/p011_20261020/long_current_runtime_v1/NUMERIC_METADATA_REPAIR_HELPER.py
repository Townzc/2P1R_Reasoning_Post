from pathlib import Path
from datetime import datetime,timezone
import json,math,hashlib
R=Path('.local/p011_20261020/r1');OUT=R/'LONG_FORMAL_ACTUAL_NUMERIC_PROJECTION.json';assert not OUT.exists()
def rd(p):return json.loads(Path(p).read_text())
def stream_rows(p):
 decoder=json.JSONDecoder();buffer='';started=False;ended=False
 with Path(p).open() as f:
  while not ended:
   part=f.read(1<<20);buffer+=part
   if not started:
    buffer=buffer.lstrip();assert buffer.startswith('[');buffer=buffer[1:];started=True
   while True:
    buffer=buffer.lstrip()
    if buffer.startswith(','):buffer=buffer[1:].lstrip()
    if buffer.startswith(']'):ended=True;buffer=buffer[1:];break
    try:v,index=decoder.raw_decode(buffer)
    except json.JSONDecodeError:break
    yield v;buffer=buffer[index:]
   if not part and not ended:raise ValueError('Truncated original encoded JSON')
  assert not buffer.strip() and not f.read().strip()
assert 'ENCODED.jsonl' in rd(R/'ot3_inputs_nfc_r1/MANIFEST.json')['files']
rowmeta={}
with (R/'ot3_inputs_nfc_r1/ENCODED.jsonl').open() as f:
 for line in f:
  x=json.loads(line);rowmeta[x['path_id']]={'n_processed':x['n_processed'],'n_supervised':x['n_supervised']}
assert len(rowmeta)==10080
with (R/'LONG_NUMERIC_ROW_COUNTS_METADATA.json').open('x') as f:json.dump(rowmeta,f)
source_manifest=rd(R/'long_inputs_numeric_gold_r1/MANIFEST.json');profiles={}
for cell in [f'A{i}' for i in range(1,9)]+['D1','D2']:
 d=R/'long_inputs_numeric_gold_r1'/cell;plan=rd(d/'plan.json')
 if cell.startswith('D'):
  meta={x['path_id']:{'n_processed':x['n_processed'],'n_supervised':x['n_supervised']} for x in stream_rows(d/'encoded.json')}
 else:meta=rowmeta
 ordered=[meta[name] for name in plan['row_path_ids']]
 units=[{'sequences':len(u),'processed_tokens':sum(ordered[i]['n_processed'] for i in u),'supervised_tokens':sum(ordered[i]['n_supervised'] for i in u)} for u in plan['updates']]
 profiles[cell]=dict(U=plan['optimizer_updates'],B=plan['supervised_tokens'],max_processed_tokens=max(u['processed_tokens'] for u in units),max_sequences=max(u['sequences'] for u in units),min_sequences=min(u['sequences'] for u in units),original_update_profile=units,source_plan_binding=source_manifest[cell+'/plan.json'],source_encoded_binding=source_manifest[cell+'/encoded.json'],processed_ratio_to_original_preflight_update=max(u['processed_tokens'] for u in units)/(65346/2),new_tokenizer_calls=0,new_plan_construction=False)
with (R/'LONG_NUMERIC_UPDATE_PROFILES_METADATA.json').open('x') as f:json.dump(profiles,f)
packet=Path('reports/p011_20261020/long_preflight_measured_evidence_v1');measured=rd(packet/'MEASURED_SUMMARY.json');arms={}
for x in measured['arms']:
 result=x['original_result'];maxunit=max(result['training_update_seconds']);batch=result['endpoint_batch_seconds'][0]
 residual=x['finished_epoch']-x['worker_start_epoch']-sum(result['training_update_seconds'])-sum(result['endpoint_batch_seconds'])
 arms[x['arm']]=dict(original_whole_update_seconds=result['training_update_seconds'],max_whole_update_seconds=maxunit,original_whole32_endpoint_seconds=batch,linear512_request_proxy_seconds=batch*16,original_nonunit_wall_residual_seconds=residual,uncalibrated_future_seconds=max(600,math.ceil(residual+300)),formal512_throughput_measured=False,model_memory_peak_measured=False,full_local_oracle_completed=x['full_state_oracle_completed'])
projection=dict(created_utc=datetime.now(timezone.utc).isoformat(),source_master_encoded_binding=rd(R/'ot3_inputs_nfc_r1/MANIFEST.json')['files']['ENCODED.jsonl'],profiles=profiles,arms=arms,formula={'training':'max observed whole-cycle seconds * max original processed tokens per formal update /32673; retain all original update observations scaled identically','endpoint':'observed whole32-request cycle *16 for full512, including all seven batches; empirical scenario, not an upper bound','future':'max(600,ceil(original worker walltime minus disjoint complete update and endpoint cycles +300)); no paid new calibration','projection_multiplier':1.2},limitations=['Whole-sequence count and length distribution differ; linear processed-token scaling does not bound per-sequence launch overhead.','Formal512 request throughput is unmeasured; trained32 samples are not a baseline or a formal trained-model distribution.','Use worst measured same-size endpoint for the untrained baseline; no claim baseline directly measured.','GPU peak bytes absent. Completed near16k/actualH100 and pinned maxseq/config are evidence, not a future OOM guarantee.','Fullparameter local state oracle pending pre-entry disposition.','These are new numerical projections of saved actual metadata, no old scoring/statistical effect analysis repeated.'],new_model_calls=0,new_encodings=0,new_scores=0,actual_runtime_admitted=False)
with OUT.open('x') as f:json.dump(projection,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps({'profiles':{k:{n:v[n] for n in ('U','B','max_processed_tokens','max_sequences','processed_ratio_to_original_preflight_update')} for k,v in profiles.items()},'arms':arms}))
