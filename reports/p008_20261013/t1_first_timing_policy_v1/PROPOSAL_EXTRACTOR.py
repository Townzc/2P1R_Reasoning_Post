"""PREPARED ONLY. Extract no endpoint scores; no GPU calls or automatic acceptance."""
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
from experiments.sft_allocation_p008.timing_gate import estimate
r=Path(__file__).resolve().parent;prep=r/'student_preparation_r1';inputs=prep/'inputs'
spec=read('reports/p008_20261013/student_admission_v1/ADMISSION.json');source=read('reports/p008_20261013/student_admission_v1/SOURCE_BUNDLE.json')
for n,h in source.items():assert sha(n)==h
small=[k for k,c in spec['configs'].items() if c.get('training_multiple')==1];large=[k for k,c in spec['configs'].items() if c.get('training_multiple')==8]
assert len(small)==10 and len(large)==8
samples={};provenance={};basewall=None
for run in small+['base']:
 cfg=spec['configs'][run];root=r/'exports'/run/'evidence';close=r/'closeouts'/run
 oracle=read(root/'LOCAL_ORACLE_AUDIT.json');assert oracle['passed'] and oracle['run_id']==run
 sent=read(root/'intent.json');assert sent['config']==cfg and sent['release']['source_files']==source
 # Read only the completed terminal/identity from the envelope. No accuracy field is used.
 terminal=read(close/'ledger.json')['midpoint/'+sent['plan']['campaign_id']+'/terminal/'+run]
 assert terminal['status']=='completed' and oracle['artifact_digest']==terminal['evidence_sha256']
 provider=read(close/'provider.json');assert not provider['owned_containers'] and all(x['state']=='stopped' for x in provider['apps'])
 wall=terminal['finished_epoch']-sent['started_epoch']
 provenance[run]=dict(oracle_sha256=sha(root/'LOCAL_ORACLE_AUDIT.json'),terminal=terminal,intent_sha256=sha(root/'intent.json'),provider_sha256=sha(close/'provider.json'))
 if run=='base':basewall=wall;continue
 metadata=read(close/'TIMING_READ_METADATA.json')['files'];records=[read(root/'completed'/f'update_{i:04d}.json') for i in range(1,257)]
 metrics=read(root/'block_journal_metrics.json')
 samples[run]=dict(worker_seconds_through_terminal=wall,
  completed_update_mtimes=[metadata[f'completed/update_{i:04d}.json']['mtime'] for i in range(1,257)],
  optimizer_seconds=[x['seconds'] for x in records],processed_tokens=[x['processed_tokens'] for x in records],
  first_eval_intent_mtime=metadata['intents/endpoint1319_batch_0000.json']['mtime'],
  block_boundary_seconds=metrics['block_boundary_seconds'],local_step_write_seconds=metrics['local_step_write_seconds'])
 provenance[run].update(timing_metadata_sha256=sha(close/'TIMING_READ_METADATA.json'),block_metrics_sha256=sha(root/'block_journal_metrics.json'))
candidates={}
for run in large:
 cfg=spec['configs'][run];plan=read(inputs/cfg['plan_file']);rows=[__import__('json').loads(x) for x in (inputs/cfg['rows_file']).read_text().splitlines()]
 P=sum(rows[i]['source']['n_processed'] for batch in plan['updates'] for i in batch)
 candidates[run]=dict(processed_tokens=P,updates=cfg['updates'],max_seconds=cfg['max_seconds'])
result=estimate(samples,basewall,candidates,expected_t1=small,expected_t8=large)
result.update(provenance=provenance,source_files=source,spec_sha256=digest(spec),common_plan_gate_sha256=spec['common_plan_gate_sha256'],worker_caps={run:spec['configs'][run]['max_seconds'] for run in large},new_model_calls=0)
# Explicitly different from T8_TIMING_ACCEPTED; no code writes acceptance.
dump(r/'T8_TIMING_PROPOSAL.json',result)
print('Prepared outcome-blind numerical proposal; real fixed-scope review required')
