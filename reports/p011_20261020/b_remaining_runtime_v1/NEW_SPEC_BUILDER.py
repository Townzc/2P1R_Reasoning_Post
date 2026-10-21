from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal,ROUND_CEILING
import ast,copy,hashlib,json,importlib.util
R=Path('.local/p011_20261020/r1');P=Path('reports/p011_20261020/b_remaining_runtime_v1')
assert not P.exists()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2,sort_keys=True);f.write('\n')
old=read('reports/p011_20261020/b_generation_runtime_v1/SPEC.json');job=copy.deepcopy(next(iter(old['jobs'].values())))
projection=read(R/'B_C2_NEW_NUMERIC_PROJECTION.json');rate=Decimal(projection['hourly_rate_usd'])
prospective=dict(hourly_rate_usd=str(rate),E3_recorded_upper_interval_seconds=projection['E3_scoring_window']['conservative_stage_to_next_dependent_stage_seconds'],
 generation_full_window_seconds=16865,generation_reserved_usd='3.01',retained_failed_B_usd='3.01',B_protected_floor_usd='48',
 cutoff_epoch=1792645200,original_failed_reservations_retained=True,students_approved_now=False,
 timing_source_files={k:v for k,v in projection['source_files'].items() if '/student_exports/' in k or 'e9_runtime_v1' in k},
 score_timing_source_files={k:v for k,v in projection['source_files'].items() if '/e3_' in k},
 latest_continuation_dispatch_epoch=min(1792591200,1792645200-16865-37465),students={})
for name in ('B1','B3'):
 prospective['students'][name]=dict(worker_seconds=4400,platform_seconds=4460,startup_seconds=600,
  collect_seconds=3600,audit_seconds=3600,score_seconds=25200,cleanup_seconds=5,full_window_seconds=37465,
  initial_worker_scenario_seconds=projection['B']['initial_complete_worker_scenario_seconds'],
  reserved_usd=str((rate*Decimal(5060)/3600).quantize(Decimal('.01'),rounding=ROUND_CEILING)))
from experiments.p011.b_remaining.numeric import verify_scenario
verify_scenario(prospective)
preserved=read(R/'b_generation_failed_preservation_r1/PRESERVATION_COMPLETED.json')
from experiments.p011.b_remaining.execution import prefix_names
prefix={x['relative_path'].removeprefix('generation/'):dict(bytes=x['bytes'],sha256=x['sha256']) for x in preserved['files'] if x['relative_path'].removeprefix('generation/') in prefix_names()}
assert set(prefix)==prefix_names()
job['prefix_files']=prefix;job['limits'].update(closeout_seconds=14405,full_result_window_seconds=16865,score_seconds=7200)
roots=['experiments/p011/b_remaining/modal_entry.py','scripts/p011_b_remaining_io.py','experiments/p011/b_remaining/student_input.py']
files=set();queue=list(roots)
def modules(name):
 stem=Path(*name.split('.'));return [str(x) for x in (stem.with_suffix('.py'),stem/'__init__.py') if x.is_file()]
while queue:
 n=queue.pop()
 if n in files:continue
 files.add(n);p=Path(n)
 for par in p.parents:
  init=par/'__init__.py'
  if str(par)!='.' and init.is_file() and str(init) not in files:queue.append(str(init))
 for node in ast.walk(ast.parse(p.read_text())):
  names=[]
  if isinstance(node,ast.Import):names=[x.name for x in node.names]
  elif isinstance(node,ast.ImportFrom):
   module=(importlib.util.resolve_name('.'*node.level+(node.module or ''),'.'.join(p.parent.parts))
           if node.level else node.module)
   if module:names=[module]+[module+'.'+x.name for x in node.names if x.name!='*']
  for name in names:
   for f in modules(name):
    if f not in files:queue.append(f)
files.update(old['source_files'])
source={n:sha(n) for n in sorted(files)}
ledger=read('reports/p011_20261020/long_preflight_failed_ledger_runtime_v1/SPEC.json')['failed_attempt_bindings']
from experiments.sft_allocation_midpoint.common import digest
spec=dict(old,source_files=source,jobs={'B_generation_t10_400x16_r2_continuation':job},
 delegated_failure_decision_sha256='8ca01d6f5d5f5e2dbe58b2e694aaa21685d3398d22d0e1c61d853a01fa92abf8',
 prefix_files=prefix,remaining_outputs=5120,reused_raw_outputs=1280,reused_transport_outputs=1024,
 original_failed_logical_id='B_generation_t10_400x16_r1',failed_attempt_bindings=ledger,
 original_upload_receipt_sha256=sha(R/'b_io_r1/upload/B_generation_t10_400x16_r1/COMPLETED.json'),
 original_generation_job_sha256=digest(next(iter(old['jobs'].values()))),prospective_students_and_score_window=prospective,
 original_failure_packet_target='14898f087718cdf0b1ba0e1b3f01df94f36aaa13',
 original_generation_inputs_A1_target=read(R/'B_GENERATION_PATH_A1_A2_ACCEPTED.json')['target_commit'],
 original_input_pack_file_sha256=sha(R/'b_generation_inputs_r1/PACK.json'),
 original_GPU_input_pack_file_sha256=sha(R/'b_generation_inputs_r1/GPU_PACK.json'))
from experiments.p011.b_remaining import path
path.validate(spec)
P.mkdir();write(P/'SPEC.json',spec)
write(P/'SOURCE_BINDING.json',dict(source_files=source,roots=roots,all_original75_sources_retained=True,
 delegated_failure_decision_sha256=spec['delegated_failure_decision_sha256'],original_plan_commit=spec['original_plan_commit'],
 original_failed_parent_packet=spec['original_failure_packet_target'],prefix_files=prefix,
 original_preservation_sha256=sha(R/'b_generation_failed_preservation_r1/PRESERVATION_COMPLETED.json')))
write(P/'PROSPECTIVE_NUMERIC.json',prospective)
write(R/'B_REMAINING_SPEC_PREPARED.json',dict(utc=datetime.now(timezone.utc).isoformat(),source_count=len(source),
 spec_sha256=sha(P/'SPEC.json'),new_model_calls=0,new_input_encodings=0,new_output_transport_calls=0,
 current_exact_A2_accepted=False,source_roots=roots))
print(json.dumps(dict(source_count=len(source),spec_sha256=sha(P/'SPEC.json'),student_reserve=prospective['students']['B1']['reserved_usd'],
 latest_continuation_dispatch_utc=datetime.fromtimestamp(prospective['latest_continuation_dispatch_epoch'],timezone.utc).isoformat())))
