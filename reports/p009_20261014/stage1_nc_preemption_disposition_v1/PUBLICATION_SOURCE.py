"""Static complete-n400/failed-n3200 evidence publication; no scoring/analysis/model."""
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import gzip,hashlib,json,shutil
import sys
sys.path.insert(0,'.')
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,manifest
from scripts.publish_p009_nc_complete import bound
from scripts.publish_p009_stage0_result import archive_original
R=Path('.local/p009_20261014/r1');N=R/'stage1_nc_r1';F=N/'failed_nc3200_preservation_r1'
OUT=Path('reports/p009_20261014/stage1_nc_preemption_disposition_v1')
SPEC=Path('reports/p009_20261014/stage1_nc_runtime_preflight_v1/ADMISSION.json')
def projected_provider(value, path):
 return dict(state='stopped',owned_container_count=0,app_ids=value['app_ids'],
  read_utc=value.get('read_utc',value.get('utc')),original_private_file_sha256=sha(path),
  projection='Only original app IDs and lifecycle state/times; actor and unrelated workspace fields omitted.',
  apps=[dict(app_id=x['app_id'],lifecycle={k:v for k,v in x['lifecycle'].items() if k in ('state','created_at','stopped_at')}) for x in value['original_app_info']])
def project_intent(value):
 v=json.loads(json.dumps(value));removed={}
 for key,item in v['release'].items():
  if isinstance(item,dict) and 'local_report_path' in item:
   removed[key+'.local_report_path']=digest(item.pop('local_report_path'))
 if 'source_snapshot' in v['release'].get('budget',{}):
  removed['budget.source_snapshot']=digest(v['release']['budget'].pop('source_snapshot'))
 return v,removed

def main():
 if OUT.exists():raise ValueError('Immutable/partial packet exists; never whole publisher retry')
 spec=read(SPEC)
 if digest(spec)!='748a7ab00a4fa9cd0b7efd126750f96e323837e672532c89bf42c65bc88f9db4':raise ValueError('Original exact NC spec changed')
 for n,h in spec['source_files'].items():
  if sha(n)!=h:raise ValueError('Original runtime changed')
 good=bound(N,'nc_s17_n400',spec);o=good['oracle'];proof=read(F/'PRESERVED.json');fm=read(F/'evidence/failure_manifest.json')
 prefix=read(F/'LOCAL_PREFIX_AUDIT.json')
 if prefix['passed_saved_record_structure'] is not True or prefix['full_training_complete'] is not False:raise ValueError('Original failed prefix structure must be preserved without claiming completed training')
 if (o['schema']!='p009_stage1_NC_full_oracle_v1' or o['technical_unknown']!=0
     or proof['passed'] is not True or proof['parent_stays_failed'] is not True
     or proof['run_id']!='nc_s17_n3200' or proof['unknown_transfer_files']!=0
     or proof['saved_checkpoint_or_weight_files'] or proof['output_raw_files']
     or proof['original_terminal']['status']!='failed' or digest(fm)!=proof['original_terminal']['evidence_sha256']):
  raise ValueError('Exact complete original n400 and failed n3200 preservation required')
 if read(F/'LIST_BEFORE.json')!=read(F/'LIST_AFTER.json') or read(F/'RECORDS_BEFORE.json')!=read(F/'RECORDS_AFTER.json'):
  raise ValueError('Failed original evidence changed')
 oldledger=read(F/'ledger.json');pre='midpoint/'+spec['campaign']+'/'
 if oldledger[pre+'terminal/nc_s17_n3200']!=proof['original_terminal'] or oldledger[pre+'terminal/nc_s17_n400']!=good['envelope']['receipt']:
  raise ValueError('Original full ledger does not bind both terminal outcomes')
 now=datetime.now(timezone.utc);copied=read(F/'COPIED.json')
 for k,v in fm.items():
  if copied[k]!=v:raise ValueError('Failed manifest/transfer digest differs')
 projected_good,removed_good=project_intent(good['intent'])
 projected_failed,removed_failed=project_intent(read(F/'evidence/intent.json'))
 providers=[projected_provider(good['provider'],good['close']/'provider.json'),
            projected_provider(read(F/'PROVIDER.json'),F/'PROVIDER.json')]
 localroot=str(Path.cwd());failure=read(F/'evidence/failure.json');failure_projection=dict(failure)
 failure_projection['traceback']=failure_projection['traceback'].replace(localroot,'<WORKSPACE>')
 log=(F/'original_cli.log').read_text();lines=log.splitlines()
 excerpts=[dict(line=i+1,text=line.replace(localroot,'<WORKSPACE>')) for i,line in enumerate(lines)
           if any(s in line for s in ('Container terminated due to preemption','run is already terminal','KeyboardInterrupt','"update": 880','"update": 896'))]
 OUT.mkdir();dump(OUT/'PUBLICATION_INTENT.json',dict(utc=now.isoformat(),source_sha256=sha(__file__),
  new_model_calls=0,new_scoring=0,paired_analysis_performed=False,original_complete_pair_publisher_executed=False))
 for name,ev,files,omit in [('nc_s17_n400',good['ev'],good['envelope']['artifact_manifest'],
       {'intent.json','compact_evidence.tar.gz','compact_manifest.json','bundle_receipt.json'}),
       ('nc_s17_n3200_failed',F/'evidence',fm,{'intent.json','failure.json'})]:
  dest=OUT/name;dest.mkdir();selected={n:v for n,v in files.items() if n not in omit and not n.endswith('.pt')}
  archive_original(ev,dest/'ORIGINAL_PUBLIC_MEMBERS.tar.gz',selected)
  dump(dest/'PROJECTION.json',dict(files=selected,omitted={n:v for n,v in files.items() if n not in selected},
    original_manifest_digest=digest(files),archive_sha256=sha(dest/'ORIGINAL_PUBLIC_MEMBERS.tar.gz'),
    private_originals_preserved=True,original_intent_file_sha256=sha(ev/'intent.json')))
 dump(OUT/'nc_s17_n400/ORIGINAL_ENVELOPE.json',good['envelope'])
 dest=OUT/'nc_s17_n400/LOCAL_ORACLE_AUDIT.json.gz'
 with (good['ev']/'LOCAL_ORACLE_AUDIT.json').open('rb') as f,dest.open('xb') as out:
  with gzip.GzipFile(fileobj=out,mode='wb',mtime=0) as z:shutil.copyfileobj(f,z)
 with gzip.open(dest,'rb') as f:
  if hashlib.sha256(f.read()).hexdigest()!=sha(good['ev']/'LOCAL_ORACLE_AUDIT.json'):raise ValueError('Original oracle readback differs')
 dump(OUT/'nc_s17_n400/INTENT_PROJECTION.json',projected_good)
 dump(OUT/'nc_s17_n3200_failed/INTENT_PROJECTION.json',projected_failed)
 dump(OUT/'nc_s17_n3200_failed/FAILURE_PROJECTION.json',dict(value=failure_projection,
  original_sha256=sha(F/'evidence/failure.json'),projection='Only local workspace prefix replaced by <WORKSPACE>; original private bytes retained.'))
 for n in ['PRESERVED.json','LIST_BEFORE.json','LIST_AFTER.json','RECORDS_BEFORE.json','RECORDS_AFTER.json','READ_ERRORS.json','COPIED.json','LOCAL_PREFIX_AUDIT.json']:
  shutil.copyfile(F/n,OUT/'nc_s17_n3200_failed'/n)
 shutil.copyfile(F/'evidence/failure_manifest.json',OUT/'nc_s17_n3200_failed/ORIGINAL_FAILURE_MANIFEST.json')
 dump(OUT/'nc_s17_n3200_failed/CLI_EVENT_EXCERPTS.json',dict(original_private_log_sha256=sha(F/'original_cli.log'),
  original_log_lines=len(lines),projection='Selected original preemption/guard/update lines; local prefix redacted only.',excerpts=excerpts))
 dump(OUT/'PROVIDERS.json',providers);shutil.copyfile(F/'ledger.json',OUT/'ORIGINAL_FULL_LEDGER.json')
 for run in ['nc_s17_n400','nc_s17_n3200']:
  shutil.copyfile(N/'runs'/run/'submitted.json',OUT/(run+'_ORIGINAL_SUBMITTED.json'))
 dump(OUT/'SOURCE_BINDING.json',dict(runtime_source_files=spec['source_files'],spec_sha256=digest(spec),
  runtime_target='22b02e313ef38581fb715a8273131f0be3b98c35',execution_commit=good['intent']['release']['execution_commit'],
  preserver_source_sha256=sha(R/'preserve_nc3200_preemption_once.py'),publisher_source_sha256=sha(__file__),
  reused_complete_n400_binding_sha256=sha('scripts/publish_p009_nc_complete.py'),
  reused_archive_helper_sha256=sha('scripts/publish_p009_stage0_result.py'),
  n400_oracle_original_file_sha256=sha(good['ev']/'LOCAL_ORACLE_AUDIT.json'),
  intent_removed_fields={'nc400':removed_good,'nc3200':removed_failed},
  original_clis={'nc_s17_n400':26666,'nc_s17_n3200':3874},actual_full_result_external_review='PENDING'))
 summary=dict(utc=now.isoformat(),nc400=dict(correct=o['correct'],total=1319,logical_stops=o['logical_stops'],
  updates=1024,targets=2097148,state_sha256=o['state_sha256'],technical_unknown=0,local_full_oracle_passed=True),
  nc3200=dict(status='failed',continuous_saved_updates=proof['continuous_saved_updates'],
   last_saved_block=proof['last_saved_block'],saved_checkpoint_count=0,saved_endpoint_outputs=0,
   failure_manifest_sha256=sha(F/'evidence/failure_manifest.json'),failure_manifest_digest=digest(fm),
   parent_stays_failed=True,full_state_oracle_performed=False),
  paired_NC_gate='UNAVAILABLE_TECHNICAL_FAILURE',scientific_NC_stop_decision=None,S1_admitted=False,
  original_reserved_cents=1310,reservation_is_actual_expense=False,active_GPU_CPU_workers=0,
  all_original_providers_stopped=True,operator_resubmission=False,platform_same_input_restart_guard_rejected=True,
  no_new_training_or_generation=True,no_missing_to_zero=True)
 dump(OUT/'SUMMARY.json',summary)
 proposal=dict(status='PROPOSAL_ONLY_OWNER_EXCEPTION_REQUIRED',old_failed_physical='nc_s17_n3200',
  proposed_physical='nc_s17_n3200_replacement_r1',independent_new_call_count=1,
  start_from_original_base=True,resume_from_896_updates=False,seed=17,n=3200,updates=1024,targets=2097148,
  original_inputs_plan_lr_unchanged=True,endpoint_questions=1319,greedy=True,max_new_tokens=512,
  proposed_worker_seconds=4500,proposed_platform_seconds=4560,proposed_startup_seconds=600,
  proposed_complete_window_seconds=5200,proposed_reserved_cents=655,automatic_retry=False,
  keep_failed_parent_and_all_costs=True,do_not_repeat_nc400=True,old_claim_or_fence_reused=False,
  exact_replacement_source_input_numeric_review_required=True,actual_runtime_not_prepared=True,
  current_stage1_cap_cents=5000,prior_stage1_reserved_cents=1310,
  proposed_stage1_reserved_cents=1965,remaining_after_proposal_cents=3035,
  later_six_S1_slots_still_require_full_budget_numeric_admission=True,
  no_reservation_release=True,no_new_call_authorized_by_this_document=True)
 dump(OUT/'REPLACEMENT_PROPOSAL.json',proposal)
 (OUT/'README.md').write_text('''# NC400 complete; NC3200 failed after platform preemption

NC400 completed once and passed the complete local raw/state/dose oracle:
954/1319 correct,56 logical caps counted incorrect,0 technical unknown;
1024 updates/2097148 targets. Its original fullstate hash is public, but this
is not a claim that an external reviewer loaded the private binary. Actual
independent outcome review is pending.

NC3200's original CLI records platform preemption during training. Its896
continuous saved update records and56 completed block acknowledgements are
preserved as metadata, with no saved model/optimizer/RNG checkpoint and no
endpoint output. All2024 files/3527435 bytes were read back against the original
failed manifest, before/after listing and original failed terminal/claim/fences.
The platform subsequently tried the same input; RunGuard rejected it before a
new claim or training. No operator model retry occurred. Both original apps
are STOPPED and own zero containers. The failed parent remains failed.

The registered NC paired decision cannot be computed. Missing NC3200 is neither
zero accuracy nor a passed/failed scientific gap. S1 remains unadmitted. The
reviewed complete-pair publisher and registered paired analysis were not run.
No checkpoint exists from which to resume the896 steps. A replacement would
start from the original base and repeat the full1024-step scientific recipe as
one distinct physical run, retaining all failed-work costs and lineage.

REPLACEMENT_PROPOSAL is a concrete option for an owner exception to the original
one-call/no-retry rule: one original-recipe NC3200 replacement,4500-second hard
worker cap and$6.55 maximum new reservation, no retry, no NC400 regeneration.
It fits the current Stage1 cap as a single proposed slot; later all-six S1
admission still needs exact actual timing, source and whole-stage budgeting.
There is no new runtime or call in this packet. Owner authorization and exact
Claude source/input/numeric review are still required before such a call.

Public archives preserve original bytes except explicitly omitted private
intents, packaging/state binaries and the separate failed traceback projection.
Original manifests/hashes and private files remain preserved. Provider actors
are omitted by an explicit projection. Log excerpts preserve the original
preemption/guard messages, with the local workspace prefix redacted. No score,
model, training, raw decode, symbolic verifier or old oracle was rerun here.
The original scalar full result is copied without a paired statistic or CI.

Modal documents automatic same-input restarts after preemption independently
of user application retries; GPU Functions do not support its nonpreemptible
option. This explains the observed platform attempt, not a promise about any
future host: [Modal preemption documentation](https://modal.com/docs/guide/preemption).
''')
 shutil.copyfile(R/'audit_nc3200_saved_prefix_once.py',OUT/'PREFIX_AUDIT_SOURCE.py');shutil.copyfile(__file__,OUT/'PUBLICATION_SOURCE.py');shutil.copyfile(R/'preserve_nc3200_preemption_once.py',OUT/'PRESERVATION_SOURCE.py')
 dump(OUT/'MANIFEST.json',manifest(OUT));print(json.dumps(dict(packet=str(OUT),members=len(read(OUT/'MANIFEST.json')),new_calls=0,new_scores=0)))
if __name__=='__main__':main()
