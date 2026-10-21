from pathlib import Path
from datetime import datetime,timezone
import json,tarfile,hashlib
R=Path('.local/p011_20261020/r1');P=Path('reports/p011_20261020');OUT=P/'long_preflight_measured_evidence_v1';assert not OUT.exists()
def h(b):return hashlib.sha256(b).hexdigest()
def rd(p):return json.loads(Path(p).read_text())
def put(p,b):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def dump(p,x):put(p,(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode())
OUT.mkdir();items=[];allprojection={}
for arm in ('S-L15','S-F15','S-L3'):
 job='preflight_'+arm+'_s17_r1';c=R/'long_preflight_io_r1/collect'/job;a=R/'long_preflight_io_r1/audit'/job;o=OUT/job
 result=rd(c/'ORIGINAL_RESULT.json');collected=rd(c/'COMPLETED.json');provider=rd(c/'PROVIDER_STOPPED0.json')
 assert result['status']=='completed' and provider['state']=='stopped' and provider['owned_containers']==0
 # The full original tar SHA was already confirmed by its unique collector.
 # This new publication copies only small declared metadata/raw members, never
 # loads/rechecks state.pt or any model weights and never repeats an oracle.
 copied={};excluded={}
 with tarfile.open(c/'evidence.tar','r:') as tar:
  members={m.name:m for m in tar.getmembers()}
  inventory=json.loads(tar.extractfile(members['EVIDENCE_MEMBERS.json']).read())
  for name,m in members.items():
   if not m.isfile():continue
   p=Path(name);allowed=(name!='ADMISSION.json' and not name.startswith('model_for_vllm/') and p.suffix!='.pt' and m.size<20_000_000)
   if allowed:
    b=tar.extractfile(m).read();put(o/'payload'/name,b);copied[name]=dict(bytes=len(b),sha256=h(b))
    if name in inventory:
     expected=inventory[name];assert expected['bytes']==len(b) and expected['sha256']==h(b)
   else:
    excluded[name]=dict(inventory.get(name,{}),reason='private_admission' if name=='ADMISSION.json' else 'private_binary_or_pinned_model_asset')
 for name in ('ORIGINAL_RESULT.json','PROVIDER_STOPPED0.json','COMPLETED.json'):
  put(o/'collection'/name,(c/name).read_bytes())
 put(o/'SUBMITTED.json',(R/'dispatch'/job/'SUBMITTED.json').read_bytes())
 # The full dispatch record carries private budget sources, so publish all
 # original named scientific records except that one, binding its original SHA.
 rawrecords=rd(c/'RECORDS.json');pub={k:v for k,v in rawrecords.items() if not k.endswith('/dispatch')}
 dump(o/'NAMED_RECORDS_NONPRIVATE_PROJECTION.json',pub)
 dispatch=c/'records/dispatch.json';dispatchproof=dict(bytes=dispatch.stat().st_size,sha256=h(dispatch.read_bytes()),public_value_omitted=True)
 actualproof=a/'COMPLETE_READONLY_PROOF.json';oracle=actualproof.exists()
 if oracle:put(o/'COMPLETE_READONLY_PROOF.json',actualproof.read_bytes())
 else:assert arm=='S-F15' and not a.exists()
 projection=dict(original_tar_sha256=collected['archive_sha256'],original_tar_bytes=(c/'evidence.tar').stat().st_size,
  original_tar_collected_and_SHA_confirmed_once=True,public_original_members=copied,omitted_original_members=excluded,
  original_private_dispatch=dispatchproof,full_state_oracle_completed=oracle,
  no_checkpoint_or_weight_read_in_this_publisher=True,no_source_test_or_old_oracle_repeated=True,
  reviewer_private_binary_access_not_implied=True,original_false_or_unknown_values_not_reinterpreted=True)
 dump(o/'PUBLIC_PRIVATE_PROJECTION.json',projection);allprojection[job]=projection
 timings={n:rd(o/'payload'/n) for n in ('MODEL_LOAD_TIMING.json','TRAINING_COMPLETE_CYCLES.json','TERMINAL_PHASE_TIMINGS.json','ENGINE_START_TIMING.json','ENDPOINT_COMPLETE_CYCLES.json','TRAINING_PARENT_INTERVAL.json')}
 items.append(dict(logical_id=job,arm=arm,app_id=result['app_id'],worker_start_epoch=result['worker_start_epoch'],finished_epoch=result['finished_epoch'],original_result=result['result'],timing_files=timings,full_state_oracle_completed=oracle,actual_provider=provider,scientific_cell_result=False,formal512_throughput_measured=False,memory_peak_bytes_recorded=False))
summary=dict(created_utc=datetime.now(timezone.utc).isoformat(),original3_engineering_models_completed=True,original3_collections_completed=True,full_oracles_completed=2,fullparam_local_audit_pending_reason='pre-entry unpublished HEAD; no audit directory or state read',all_original_models_and_collections_must_not_repeat=True,total_retained_engineering_reserve_usd='5.95',reserve_not_actual_expense=True,formal_model_calls=0,formal_numerical_admission=False,measurement_exceptions_for_formal=0,arms=items)
dump(OUT/'MEASURED_SUMMARY.json',summary)
dump(OUT/'SOURCE_AND_REVIEW_BINDING.json',dict(engineering_SPEC='reports/p011_20261020/long_preflight_failed_ledger_runtime_v1/SPEC.json',engineering_SPEC_sha256='eb88670f66ca6ebdfa080d9e5b39dc9654e00604be2cf398df31cb4f7d21d7a6',engineering_acceptance_report_sha256='395b60e24d8d836464b88e9adc690791338d9ff23bb77efbd576bf5b1f02c284',source_execution_commit='6ae79c06f65bcbd5d9f1e609c96d6c27ee64b3ef',formal44_source_acceptance_report_sha256='83d5d8c9a4ad6e63afb9b15a51be2261843c242978ae88b0f9e112782b6830e5',engineering_not_scientific_smoke=True))
put(OUT/'COPY_PUBLICATION_CODE.py',Path(__file__).read_bytes())
put(OUT/'README.md',b'''# Three-arm actual engineering evidence, dated before fullparameter local oracle

All three original engineering calls completed: two original longest accepted
answers, two updates/65082 supervised tokens,32 representative endpoint requests.
All original collections confirmed tar bytes and actualSTOPPED0. LoRA1.5B/LoRA3B
full local state/raw oracles passed. Fullparameter local audit was stopped by the
unpublished-HEAD guard before an audit directory or state read; its exact narrow
disposition is in ../long_F15_local_audit_preentry_failure_v1. It is not passed
or retried here. A later immutable local-proof addendum is needed if authorized.

This new copy publisher emits original metadata/raw bytes and nonprivate named
records with explicit private projections. It neither loads state/weights nor
repeats training, generation, decode, scoring, oracle or the original collector.
Public checkpoint hashes do not mean the external reviewer read private binary
state. Both the original successful LoRA proofs and absent F15 proof are explicit.

Observed full training/update and full endpoint cycles retain storage/remote
acknowledgments. The original32 requests are not formal512 throughput. Formal
training updates contain a different number/token total of complete sequences;
no unscaled update timing is a complete numerical basis. These observations
are not timing upper bounds. Peak device-memory bytes were not instrumented;
H10080GB and completed longest-sequence engineering are factual, but do not
establish all future512-request memory behavior. No scientific score, selected
student, formal cell result or official smoke decision is reported.

The existing shared formal request still needs concrete source44 SPEC, explicit
extrapolation/allowances, original total result windows, fresh actual budget,
and numerical acceptance. Original three-smoke/two-baseline science and later
Claude selection rule remain. No new scientific or timing exception is granted.
''')
dump(OUT/'PUBLIC_MANIFEST.json',{p.relative_to(OUT).as_posix():dict(bytes=p.stat().st_size,sha256=h(p.read_bytes())) for p in sorted(OUT.rglob('*')) if p.is_file()})
dump(R/'LONG_MEASURED_EVIDENCE_PUBLICATION_DONE.json',dict(utc=summary['created_utc'],packet=str(OUT),public_members=len(rd(OUT/'PUBLIC_MANIFEST.json')),new_model_calls=0,new_state_loads=0,new_oracle_calls=0,fullparam_oracle_pending=True))
print(json.dumps({'packet':str(OUT),'members':len(rd(OUT/'PUBLIC_MANIFEST.json')),'full_oracles_done':2,'F15_oracle_pending':True}))
