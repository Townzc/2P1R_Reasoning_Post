"""Prepared one-slot gate assembly after actual scoped G1, never dispatches."""
from pathlib import Path
import sys
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
from experiments.sft_allocation_p008.completion_student_binding import validate_student_binding
r=Path(__file__).resolve().parent;phase=r.parent;run=sys.argv[1]
spec=read('reports/p008_20261013/student_admission_v1/ADMISSION.json');cfg=read(r/'student_preparation_r1'/(run+'.json'));assert cfg==spec['configs'][run]
review=read(r/'STUDENT_RUNTIME_ACCEPTED.json');upload=read(r/'student_preparation_r1/UPLOAD_VERIFIED.json');source=read('reports/p008_20261013/student_admission_v1/SOURCE_BUNDLE.json')
for n,h in source.items():assert sha(n)==h
if cfg.get('training_multiple')==8:
 timing=read(r/'T8_TIMING_ACCEPTED.json')
 assert timing['passed'] is True and timing['N2_closed'] is True
 assert timing['source_files']==source and timing['spec_sha256']==digest(spec)
 assert run in timing['accepted_runs'] and timing['worker_caps'][run]==cfg['max_seconds']
 assert sha(r/timing['local_report_path'])==timing['report_sha256']
 # This evidence can exist only after real numerical review; code PASS is insufficient.
oracle=read(phase/'LOCAL_ORACLE_AUDIT.json');provider=read(phase/'closeout_r1/provider.json')
assert oracle['passed'] and oracle['four_gpu_verified'] and not provider['containers'] and all(x['state']=='stopped' for x in provider['apps'])
phase_terms=[];pool_terms=[]
for role in ('teacher_calibration','student_smoke','io_probe_a','io_probe_b'):
 receipt=read(phase/'phase0_run_r1'/(role+'_result.json'))['receipt'];assert receipt['status']=='completed'
 phase_terms.append(dict(campaign='p008-phase0-20261013-r1',run_id=role,terminal=receipt))
from experiments.sft_allocation_p008.pool_lineage import validate_pool_lineages
pool_terms=validate_pool_lineages(spec['pool_lineages'],spec['draw_local_oracle_sha256'])
paths={1:(r/'exports/pool_d1/evidence/LOCAL_ORACLE_AUDIT.json',r/'closeouts/pool_d1/provider.json'),
       2:(r/'d2_continuation_r1/export_r1/evidence/LOCAL_ORACLE_AUDIT.json',r/'d2_continuation_r1/closeout_r1/provider.json')}
for draw,(a,p) in paths.items():
 assert read(a)['passed'] and sha(a)==spec['draw_local_oracle_sha256'][str(draw)]
 provider=read(p);assert not provider['owned_containers'] and all(x['state']=='stopped' for x in provider['apps'])
 if draw==2:assert all(x['state']=='stopped' for x in provider['original_apps'])
j=r/'student_preparation_r1/inputs/COMMON_PLAN_GATE.json';assert read(j)['passed'] and sha(j)==spec['common_plan_gate_sha256']
gates=dict(runtime_review=review,phase0=dict(oracle_passed=True,four_gpu_verified=True,provider_released=True,oracle_sha256=sha(phase/'LOCAL_ORACLE_AUDIT.json')),upload=upload,required_terminals=phase_terms+pool_terms,pool_terminals=pool_terms,pool_lineage_sha256=digest(spec['pool_lineages']),joint_plan_gate=dict(passed=True,sha256=sha(j)),pool_admission_sha256=sha('reports/p008_20261013/main_admission_v1/ADMISSION.json'))
if cfg['role']!='base':gates['draw_review']=read(r/f"G1_D{cfg['draw']}_ACCEPTED.json")
gates['student_concurrency_owner']=read(r/'OWNER_STUDENT_8GPU.json')
gates['student_quota']=read(r/'STUDENT_H100_QUOTA_VERIFIED.json')
from experiments.sft_allocation_p008.completion_queue import transfer_record
plan=read(r/'student_completion_r1/plan.json')
gates['student_completion_owner']=read(r/'OWNER_STUDENT_COMPLETION.json')
gates['student_slot_transfer']=transfer_record(plan,read(r/'plan.json'),gates['student_completion_owner'])
release=dict(source_files=source,spec_sha256=digest(spec),gates=gates);validate_student_binding(plan,cfg,release,spec)
dump(r/'student_completion_r1/gates'/(run+'.json'),gates);print('Prepared exact already-accepted gate for '+run)
