"""PREPARED: publish one actual all-host N2 proposal, never create acceptance."""
from pathlib import Path
import datetime,json,shutil
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,manifest
from experiments.sft_allocation_p008.student_t8_binding import expected_mapping,ORIGINAL
r=Path(__file__).resolve().parent;out=Path('reports/p008_20261013/t8_actual_timing_proposal_v1')
if out.exists():raise ValueError('Immutable numerical proposal already exists')
proposal_path=r/'T8_TIMING_PROPOSAL_REPLACEMENTS.json';proposal=read(proposal_path)
spec=read('reports/p008_20261013/student_admission_v1/ADMISSION.json')
source=read('reports/p008_20261013/student_t8_runtime_preflight_v1/SOURCE_BUNDLE.json')
assert proposal['N2_closed'] is False and proposal['runtime_admission'] is False
assert proposal['spec_sha256']==digest(spec) and proposal['logical_to_physical']==expected_mapping(spec)
assert proposal['failed_host_dropped'] is False and proposal['new_model_calls']==0
measurements={};proofs={}
for logical,item in expected_mapping(spec).items():
    queue=r/'student_completion_r1' if item['campaign']==ORIGINAL else r/'student_lr_replacements_r1'
    physical=item['run_id'];root=queue/'exports'/physical/'evidence';close=queue/'closeouts'/physical
    p=proposal['provenance'][logical]
    assert sha(root/'LOCAL_ORACLE_AUDIT.json')==p['oracle_sha256'] and read(root/'LOCAL_ORACLE_AUDIT.json')['passed'] is True
    assert sha(root/'intent.json')==p['intent_sha256'] and sha(close/'provider.json')==p['provider_sha256']
    sent=read(root/'intent.json');terminal=p['terminal'];assert terminal['status']=='completed'
    provider=read(close/'provider.json');assert not provider['owned_containers'] and all(x['state']=='stopped' for x in provider['apps'])
    claim=read(close/'ledger.json')['midpoint/'+sent['plan']['campaign_id']+'/claim/'+physical]
    assert terminal['claim_sha256']==digest(claim)
    timing_start=min(sent['started_epoch'],claim['claimed_epoch'])
    assert timing_start==p['timing_start_epoch'] and claim==p['claim']
    wall=terminal['finished_epoch']-timing_start
    proofs[logical]=dict(physical=item,terminal=terminal,started_epoch=sent['started_epoch'],timing_start_epoch=timing_start,claim=claim,source_files=sent['release']['source_files'])
    if logical=='base':measurements[logical]=dict(worker_seconds_through_terminal=wall);continue
    assert sha(close/'TIMING_READ_METADATA.json')==p['timing_metadata_sha256']
    assert sha(root/'block_journal_metrics.json')==p['block_metrics_sha256']
    metadata=read(close/'TIMING_READ_METADATA.json')['files'];done=[read(root/'completed'/f'update_{i:04d}.json') for i in range(1,257)]
    metrics=read(root/'block_journal_metrics.json')
    measurements[logical]=dict(worker_seconds_through_terminal=wall,
        completed_update_mtimes=[metadata[f'completed/update_{i:04d}.json']['mtime'] for i in range(1,257)],
        optimizer_seconds=[x['seconds'] for x in done],processed_tokens=[x['processed_tokens'] for x in done],
        first_eval_intent_mtime=metadata['intents/endpoint1319_batch_0000.json']['mtime'],
        block_boundary_seconds=metrics['block_boundary_seconds'],local_step_write_seconds=metrics['local_step_write_seconds'])
for n,h in source.items():assert sha(n)==h
out.mkdir()
shutil.copyfile(proposal_path,out/'PROPOSAL.json');shutil.copyfile(r/'T1_TIMING_ROSTER.json',out/'ORIGINAL_T1_ROSTER.json')
dump(out/'MEASUREMENTS.json',measurements);dump(out/'ORIGINAL_TIMING_IDENTITIES.json',proofs);dump(out/'TARGET_T8_SOURCE_BUNDLE.json',source)
shutil.copyfile(r/'prepare_t8_timing_proposal_replacements.py',out/'PREPARATION_SOURCE.py')
shutil.copyfile(__file__,out/'PUBLICATION_SOURCE.py')
shutil.copyfile('experiments/sft_allocation_p008/timing_gate.py',out/'timing_gate.py')
dump(out/'BINDING.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),proposal_digest=digest(proposal),
    proposal_file_sha256=sha(proposal_path),spec_sha256=digest(spec),target_source_files=source,
    all_logical_T1_hosts=10,base_hosts=1,original_failed_attempts_retained=2,
    engineering_criterion_passed=proposal['engineering_criterion_passed'],N2_closed=False,runtime_admission=False,external_review='pending'))
(out/'REVIEW_REQUEST.md').write_text('''# Actual all-host T8 numerical N2 review

This request binds the exact original eight T8 configs and current34-source
T8 entry to the actual complete ten T1 hosts plus base. Both failed original
zero-update calls remain recorded and mapped to their authorized replacements.
No slow host, failed history or scientific dose was dropped; scores are unused.

Independently recompute all frozen C1/C2 v2 components and their maxima from
MEASUREMENTS and original published completed-update/timing evidence. Confirm
all eight 20%-margin predictions fit9530 seconds within original9560 worker caps.
Compare actual logical-to-physical provenance, failed setup walls, unchanged
common plan and exact target source/spec. If the criterion fails, report failure;
this producer never writes ACCEPTED and does not itself authorize any T8 call.

Historical hosts and processed-token scaling are proxies, not upper bounds or
guarantees. Checkpoint/setup gap is deliberately counted both inside F and K.
Original T1 metadata comes from Volume timestamps, not normalized tar mtimes.
The owner extended the finite student deadline, not these per-worker caps.
Please state exact accepted runs/source/spec/proposal digest if numerical N2
passes. Code-only PASS and the preliminary timing proposal are insufficient.
''')
dump(out/'MANIFEST.json',manifest(out));print(str(out))
