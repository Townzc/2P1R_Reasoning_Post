"""PREPARED: all-host timing proposal with immutable failed/replacement lineage.

No scores are used. Requires all ten completed T1 logical members plus base,
keeps the two original failed attempts separately, and never writes ACCEPTED.
"""
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
from experiments.sft_allocation_p008.student_replacement_binding import LOGICAL,MAPPING,validate_binding
from experiments.sft_allocation_p008.timing_gate import estimate
r=Path(__file__).resolve().parent;prep=r/'student_preparation_r1';inputs=prep/'inputs'
spec=read('reports/p008_20261013/student_admission_v1/ADMISSION.json')
oldsource=read('reports/p008_20261013/student_admission_v1/SOURCE_BUNDLE.json')
source=read('reports/p008_20261013/student_frozen_lr_amendment_v1/SOURCE_BUNDLE.json')
replacement_spec=read('reports/p008_20261013/student_lr_replacement_admission_v1/ADMISSION.json')
replacement_source=read('reports/p008_20261013/student_lr_replacement_admission_v1/SOURCE_BUNDLE.json')
for bundle in (oldsource,source,replacement_source):
 for n,h in bundle.items():assert sha(n)==h
roster=read(r/'T1_TIMING_ROSTER.json')
assert roster['frozen_before_first_T1_dispatch'] is True
assert roster['spec_sha256']==digest(spec) and roster['source_files']==oldsource
assert roster['common_plan_gate_sha256']==spec['common_plan_gate_sha256']
assert sorted(roster['accepted_draws'])==[1,2]
for draw in (1,2):assert sha(r/f'G1_D{draw}_ACCEPTED.json')==roster['G1_acceptance_sha256'][str(draw)]
small=sorted(n for n,c in spec['configs'].items() if c.get('training_multiple')==1)
large=sorted(n for n,c in spec['configs'].items() if c.get('training_multiple')==8)
assert small==sorted(roster['T1_runs']) and large==sorted(roster['T8_runs']) and len(small)==10 and len(large)==8
replroot=r/'student_lr_replacements_r1';review=read(replroot/'RUNTIME_ACCEPTED.json')
assert review['source_files']==replacement_source and review['spec_sha256']==digest(replacement_spec)
assert sha(replroot/'REVIEW_REPORT.md')==review['review_report_sha256']
failed_path=r/'student_completion_r1/lr_preflight_failures_r1/RECONCILED.json'
assert sha(failed_path)==replacement_spec['zero_update_reconciliation_sha256']
failed=read(failed_path);assert failed['passed'] is True and set(failed['runs'])==set(LOGICAL)
samples={};provenance={};physical_mapping={};basewall=None
for logical in small+['base']:
    replacement=logical in LOGICAL
    physical=next(n for n,v in MAPPING.items() if v==logical) if replacement else logical
    queue=replroot if replacement else r/'student_completion_r1'
    root=queue/'exports'/physical/'evidence';close=queue/'closeouts'/physical
    oracle=read(root/'LOCAL_ORACLE_AUDIT.json')
    assert oracle['passed'] is True and oracle['run_id']==physical
    sent=read(root/'intent.json');cfg=sent['config'];science=spec['configs'][logical]
    if replacement:
        assert validate_binding(sent['plan'],cfg,sent['release'],replacement_spec)==science
        assert oracle['logical_run_id']==logical and oracle['parent_status']=='failed'
        assert oracle['outcome_blind_zero_update_replacement'] is True
        assert sent['release']['source_files']==replacement_source
    else:
        assert cfg==science and sent['release']['source_files']==(oldsource if logical=='base' else source)
    ledger=read(close/'ledger.json');prefix='midpoint/'+sent['plan']['campaign_id']+'/'
    terminal=ledger[prefix+'terminal/'+physical];claim=ledger[prefix+'claim/'+physical]
    assert terminal['claim_sha256']==digest(claim)
    assert terminal['status']=='completed' and oracle['artifact_digest']==terminal['evidence_sha256']
    assert oracle['updates_verified']==science['updates'] and oracle['targets_verified']==science['targets'] and oracle['outputs_rescored']==1319
    provider=read(close/'provider.json');assert not provider['owned_containers'] and all(x['state']=='stopped' for x in provider['apps'])
    timing_start=min(sent['started_epoch'],claim['claimed_epoch'])
    wall=terminal['finished_epoch']-timing_start
    assert 0 < wall and timing_start <= claim['claimed_epoch'] <= terminal['finished_epoch']
    physical_mapping[logical]=dict(campaign=sent['plan']['campaign_id'],run_id=physical)
    provenance[logical]=dict(oracle_sha256=sha(root/'LOCAL_ORACLE_AUDIT.json'),terminal=terminal,
        intent_sha256=sha(root/'intent.json'),provider_sha256=sha(close/'provider.json'),
        source_files=sent['release']['source_files'],physical_run_id=physical,
        timing_start_epoch=timing_start,claim=claim,
        timing_origin='min(original saved worker start, immutable claim) through terminal finish; includes packing')
    if logical=='base':basewall=wall;continue
    metadata=read(close/'TIMING_READ_METADATA.json')['files']
    records=[read(root/'completed'/f'update_{i:04d}.json') for i in range(1,257)]
    metrics=read(root/'block_journal_metrics.json')
    samples[logical]=dict(worker_seconds_through_terminal=wall,
        completed_update_mtimes=[metadata[f'completed/update_{i:04d}.json']['mtime'] for i in range(1,257)],
        optimizer_seconds=[x['seconds'] for x in records],processed_tokens=[x['processed_tokens'] for x in records],
        first_eval_intent_mtime=metadata['intents/endpoint1319_batch_0000.json']['mtime'],
        block_boundary_seconds=metrics['block_boundary_seconds'],local_step_write_seconds=metrics['local_step_write_seconds'])
    provenance[logical].update(timing_metadata_sha256=sha(close/'TIMING_READ_METADATA.json'),block_metrics_sha256=sha(root/'block_journal_metrics.json'))
candidates={}
for run in large:
    cfg=spec['configs'][run];plan=read(inputs/cfg['plan_file'])
    rows=[__import__('json').loads(x) for x in (inputs/cfg['rows_file']).read_text().split('\n') if x.strip()]
    P=sum(rows[i]['source']['n_processed'] for batch in plan['updates'] for i in batch)
    candidates[run]=dict(processed_tokens=P,updates=cfg['updates'],max_seconds=cfg['max_seconds'])
result=estimate(samples,basewall,candidates,expected_t1=small,expected_t8=large)
result.update(timing_roster_sha256=sha(r/'T1_TIMING_ROSTER.json'),provenance=provenance,
    logical_to_physical=physical_mapping,failed_attempts_retained=failed['runs'],
    failed_attempt_proof_sha256=sha(failed_path),replacement_review_sha256=sha(replroot/'RUNTIME_ACCEPTED.json'),
    source_files=source,spec_sha256=digest(spec),common_plan_gate_sha256=spec['common_plan_gate_sha256'],
    worker_caps={run:spec['configs'][run]['max_seconds'] for run in large},new_model_calls=0,
    failed_host_dropped=False,timing_policy='All completed logical members with all physical failed attempts retained; component-wise maxima across all10completed T1, base overhead max; separate numerical review required')
dump(r/'T8_TIMING_PROPOSAL_REPLACEMENTS.json',result)
print('Prepared actual all-host proposal only; N2 acceptance not written')
