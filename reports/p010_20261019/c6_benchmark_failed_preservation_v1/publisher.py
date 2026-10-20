"""Publish preserved C6 failure and one bounded remaining-cell proposal. No scoring."""
import ast
import hashlib
import json
import re
import shutil
import tarfile
from decimal import Decimal
from pathlib import Path
from experiments.p010.common import read, dump, sha, manifest, utc
from experiments.p010.settlement_d1 import gross, settle

r=Path('.local/p010_20261019/r1');p=Path('reports/p010_20261019')
failed=r/'cue_benchmark_failure_preservation_r1';receipt=r/'cue_benchmark_runs/benchmark_group_r1'
out=p/'c6_benchmark_failed_preservation_v1';candidate=p/'c6_remaining_owner_proposal_v1'
assert not out.exists() and not candidate.exists()
done=read(failed/'COMPLETED.json');original=read(failed/'MANIFEST.json')
assert done['provider_stopped'] and done['owned_count']==0 and done['total_saved_raw_rows']==18871
assert done['manifest_sha256']==sha(failed/'MANIFEST.json') and not (failed/'FAILED.json').exists()
assert done['cells']['t72_n400_math']['saved_raw_rows']==0 and done['cells']['t72_n400_math']['confirmed_batch_acks']==0
proof=r/'model_metadata_1120_r1/C6_PATH_PROOF.json';pathproof=read(proof)
assert pathproof['all_original_file_sizes_match'] and not pathproof['weights_read_or_downloaded']
helper=ast.parse((r/'publish_e9_completed_once.py').read_text())
ns=dict(hashlib=hashlib,tarfile=tarfile,sha=sha)
node=next(x for x in helper.body if isinstance(x,ast.FunctionDef) and x.name=='archive')
exec(compile(ast.Module(body=[node],type_ignores=[]),'<existing pure archive/readback>','exec'),ns)
# The failed outer traceback contains a local SDK path. Preserve it privately and
# publish an explicit projection alongside an archive omitting exactly that file.
safe_files={n:failed/'evidence'/n for n in original if n!='FAILURE.json'}
for name,f in safe_files.items():
    assert f.stat().st_size==original[name]['bytes'] and sha(f)==original[name]['sha256']
    assert '/Users/' not in f.read_text() and '/var/folders/' not in f.read_text(),name
def redact(value):
    if isinstance(value,dict):return {k:redact(v) for k,v in value.items()}
    if isinstance(value,list):return [redact(v) for v in value]
    if isinstance(value,str):
        value=re.sub(r'/Users/[^\s"\n]+', '<private-local-path>', value)
        return re.sub(r'/var/folders/[^\s"\n]+', '<private-local-path>', value)
    return value
projected=redact(read(failed/'evidence/FAILURE.json'))
assert '/Users/' not in json.dumps(projected) and '/var/folders/' not in json.dumps(projected)
provider=read(failed/'PROVIDER_PRIVATE.json');life=provider['original_info'][0]['lifecycle']
assert life['state'].lower()=='stopped' and provider['owned']==[]
# Same-I D1 candidate: original completed search only, not the failed benchmark.
app='ap-xPLmKYrPYx6fHKAGOaKU3T';searchprovider=read(r/'cue_search_export_r1/PROVIDER_PRIVATE.json')
slife=searchprovider['original_info'][0]['lifecycle'];assert searchprovider['app_id']==app and not searchprovider['owned']
projection=dict(app_id=app,state=slife['state'],created_at=slife['created_at'],stopped_at=slife['stopped_at'],owned_count=0)
hour=r/'g_settlement_hourly_coverage_r1/report.json';hourly=read(hour)
history={};basis={}
for f in sorted(r.rglob('report.json')):
    try:rows=read(f)
    except (ValueError,OSError):continue
    if isinstance(rows,list) and any(isinstance(x,dict) and x.get('object_id')==app and 'cost' in x for x in rows):
        selected=[x for x in rows if x.get('object_id')==app]
        history[str(f)]=selected;basis[str(f)]=dict(bytes=f.stat().st_size,sha256=sha(f))
settled=settle(app,'3.26',projection,hourly,[gross(rows,app) for rows in history.values()])
assert settled['charged_usd']=='0.99' and settled['released_usd']=='2.27'
effective=Decimal('14.43')-Decimal('3.26')+Decimal(settled['charged_usd'])
assert effective+Decimal('2.52')<=15
out.mkdir(exist_ok=False)
for source,name in [(failed/'COMPLETED.json','PRESERVATION_COMPLETED.json'),(failed/'MANIFEST.json','ORIGINAL_ALL_325_MANIFEST.json'),(failed/'LEDGER.json','ORIGINAL_NAMED_LEDGER.json'),(receipt/'INTENT.json','ORIGINAL_LOCAL_INTENT.json'),(receipt/'SUBMITTED.json','ORIGINAL_SUBMITTED.json'),(receipt/'ERROR.json','ORIGINAL_CALLBACK_ERROR.json'),(proof,'MODEL_PATH_DIAGNOSIS.json')]:
    assert '/Users/' not in source.read_text() and '/var/folders/' not in source.read_text()
    shutil.copyfile(source,out/name)
dump(out/'ORIGINAL_EVIDENCE_ARCHIVE.json',ns['archive'](out/'original_saved_evidence.tar.gz',safe_files))
dump(out/'FAILURE_TRACEBACK_PROJECTED.json',projected)
dump(out/'PROVIDER.json',dict(app_id=provider['app_id'],lifecycle={k:life[k] for k in ('state','created_at','stopped_at')},owned_count=0,read_utc=provider['utc'],original_private_sha256=sha(failed/'PROVIDER_PRIVATE.json')))
dump(out/'PROJECTION.json',dict(original_file_count=325,original_bytes=done['bytes'],archive_original_members=324,
    excluded_original_files={'FAILURE.json':original['FAILURE.json']},traceback_projection='Only private host paths redacted; original bytes retained privately',
    provider_projection='Actor identity omitted; original full provider SHA retained',original_ledger_projection=False,full_raw_oracle=False,scores_computed=False))
(out/'README.md').write_text('# C6 original benchmark failure: preserved, STOPPED0\n\n'
    'The fourth cell failed before generation because its frozen model binding used `student/` instead of the original `students/` directory. '
    'Original base MATH4,500 + base GSM11,871 + S1n400 MATH2,500 =18,871 raw outputs and75 batch acknowledgments are preserved. '
    'T72n400 has zero raw outputs and zero batch acknowledgments. The original group remains failed; its claim, four cell markers and8.65USD reservation remain intact.\n\n'
    'The bounded read-only preservation saved325 files /222,808,495 bytes with stable before/after inventories and ledger boundaries. '
    'The archive contains324 byte-identical files. The one outer failure traceback is separately projected only to remove private local paths; its original hash is retained. '
    'This is structural preservation, not complete token decoding or scoring. Correct-path inventory matches every original merged-file size and one small tokenizer-file SHA; future exact worker must verify all weight hashes. No weights were downloaded, remerged or retrained.\n')
shutil.copyfile(__file__,out/'publisher.py');dump(out/'MANIFEST.json',manifest(out))
candidate.mkdir(exist_ok=False)
dump(candidate/'I_SEARCH_D1_PROPOSAL.json',dict(utc=utc(),scope='same-I original completed C6 search D1 candidate',
    item=settled,original_prior_I_reserved_usd='14.43',proposed_prior_I_charged_usd=str(effective),
    new_remaining_cell_reserve_usd='2.52',proposed_after_remaining_usd=str(effective+Decimal('2.52')),
    failed_benchmark_full_reserve_usd='8.65',E9_baseline_full_reserve_usd='2.52',
    original_claims_modified=False,actual_release_applied=False,category_transfer=False,
    no_backend_finality_watermark=True,exact_runtime_numeric_A2_required=True))
dump(candidate/'SEARCH_PROVIDER_PROJECTION.json',dict(**projection,original_private_sha256=sha(r/'cue_search_export_r1/PROVIDER_PRIVATE.json')))
dump(candidate/'SEARCH_HOURLY_ROWS.json',[x for x in hourly if x.get('object_id')==app])
dump(candidate/'SEARCH_HISTORICAL_ROWS.json',history);dump(candidate/'SOURCE_BASIS.json',basis)
dump(candidate/'PROPOSAL.json',dict(utc=utc(),request_id='p010-C6-only-unattempted-T72-cell-owner-exception-r1',
    new_physical_calls=1,new_outputs=2500,reused_saved_outputs=18871,old_outputs_regenerated=0,
    run='t72_n400_math',original_cue=[1249],original_input_and_seeds_unchanged=True,
    new_training_updates=0,new_checkpoint_loads=0,new_merge_operations=0,
    worker_seconds=1200,platform_seconds=1260,startup_seconds=600,full_dispatch_window_seconds=1900,
    reserve_usd='2.52',I_cap_usd='15',caps_usd=dict(G=50,T=150,I=15,C=25),overall_cap_usd=240,protected_usd=43,
    original_failure_manifest_sha256=sha(failed/'MANIFEST.json'),public_failure_manifest_sha256=sha(out/'MANIFEST.json'),
    correct_path_proof_sha256=sha(proof),owner_delegation_file_sha256=sha(r/'OWNER_P010_OVERNIGHT_DELEGATION.json'),
    original_parent_remains_failed=True,new_permanent_marker_required=True,automatic_retry=False,
    exact_code_and_numeric_A2_still_required=True,approval_received=False,actual_reserve_release=0))
(candidate/'README.md').write_text('# C6 remaining-cell exception proposal — not admitted\n\n'
    'Request one explicit reasoned overnight Claude owner decision for only the2,500 unattempted T72n400 responses. '
    'Reuse all18,871 saved earlier responses without generation. Use the original merged model at its verified plural `students/` path, with all original file hashes; no training/checkpoint reload/remerge. '
    'The original failed group, cell marker and8.65 reservation remain unchanged. A new physical identity and permanent marker must prevent another call. '
    'Same cue1249, questions, seeds, greedy/four sample passes and original cap;1200 worker/1260 platform/600 startup/full1900,2.52USD reserve, no automatic retry.\n\n'
    'D1 same-I search-only candidate: completed search3.26 reservation → max saved gross0.82151854×1.2 rounded up0.99, releasing2.27; I14.43−3.26+0.99+2.52=14.68≤15. '
    'Returned complete hourly buckets cover the original STOPPED/owned0 lifecycle; this is delayed metering plus buffer, not invoice finality. '
    'No release, transfer, budget increase, admission or new call has occurred. Full exact runtime/combined raw oracle/scoring A2 must independently pass before dispatch. '
    'The original18871 rows have not yet been decoded or scored; future complete verification must preserve their real failed-parent provenance.\n')
dump(candidate/'MANIFEST.json',manifest(candidate))
request=p/'C6_UNATTEMPTED_T72_OWNER_REQUEST.md'
request.write_text('# Owner exception requested: only the unattempted C6 T72 cell\n\n'
    'Request ID `p010-C6-only-unattempted-T72-cell-owner-exception-r1`. Under the saved direct overnight delegation, please state an explicit approve/reject decision and reason. '
    'The one original group failed at a singular/plural path binding, after18,871 saved outputs. Only the remaining2,500 are proposed; original outputs, failed claim and costs stay preserved. '
    'See `c6_benchmark_failed_preservation_v1` and `c6_remaining_owner_proposal_v1` at this fixed commit. '
    'The proposed same-I D1 search settlement yields14.68≤15 including the new2.52, with all category/240/protected43 caps unchanged. '
    'This decision does not waive independent exact source/input/runtime/numeric A2. Full code candidate follows; no models are active or automatically retried.\n')
idx=read('reports/p007_audit/INDEX.json');assert not any(x.get('request_id')=='p010-C6-only-unattempted-T72-cell-owner-exception-r1' for x in idx['review_requests'])
idx['review_requests'].append(dict(request_id='p010-C6-only-unattempted-T72-cell-owner-exception-r1',scope='p010-C6-only-unattempted-T72-cell-owner-exception',status='pending_explicit_Claude_owner_decision_and_future_exact_A2',packet=str(candidate),failure_packet=str(out),request=str(request),proposal_sha256=sha(candidate/'PROPOSAL.json')))
idx['as_of_utc']=utc();idx['p010']['C6_benchmark_status']='FAILED_STOPPED0_preserved18871_only2500_unattempted_owner_exception_pending';idx['p010']['active_scientific_calls']=0
dump('reports/p007_audit/INDEX.json',idx)
b=read(r/'CLI_SESSIONS.json');b['observed_utc']=utc();b['C6_benchmark_original_call'].update(status='EXIT1_CONSUMED_FAILED_PRESERVED_STOPPED0',phase='failed_parent_no_retry',exit_code=1,consumed=True,failed_preservation_cli=28694,failed_preservation_DONE=True,metadata_cli=48673,metadata_DONE=True);dump(r/'CLI_SESSIONS.json',b)
dump(r/'C6_FAILURE_PROPOSAL_PUBLISHED_ONCE.json',dict(utc=utc(),failure_packet=str(out),proposal_packet=str(candidate),failed_manifest_sha256=sha(out/'MANIFEST.json'),proposal_manifest_sha256=sha(candidate/'MANIFEST.json'),new_models=0,actual_settlement_release=0))
print(json.dumps(dict(failure_members=len(read(out/'MANIFEST.json')),proposal_members=len(read(candidate/'MANIFEST.json')),archive_bytes=(out/'original_saved_evidence.tar.gz').stat().st_size,I_after_proposal='14.68',new_models=0)))
