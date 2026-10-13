"""Prepared numeric student packet creation after both local G1 oracles/plans.
This publishes a review target, never an accepted review or model dispatch.
"""
from pathlib import Path
import json,ast,datetime,shutil
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify,manifest
r=Path(__file__).resolve().parent;prep=r/'student_preparation_r1';s=read(prep/'PREPARATION.json');old=read('reports/p008_20261013/main_admission_v1/ADMISSION.json')
assert s['status']=='prepared_not_dispatched_requires_exact_G1' and s['branch']==old['branch'] and s['plan_sha256']==old['plan_sha256']
assert s['new_model_calls']==0 and len(s['configs'])==19
from experiments.sft_allocation_p008.pool_lineage import validate_pool_lineages
validate_pool_lineages(s['pool_lineages'],s['draw_local_oracle_sha256'])
paths={1:r/'exports/pool_d1/evidence',2:r/'d2_continuation_r1/export_r1/evidence'}
for d,root in paths.items():
 a=root/'LOCAL_ORACLE_AUDIT.json';assert read(a)['passed'] and sha(a)==s['draw_local_oracle_sha256'][str(d)]
provider=[read(r/'closeouts/pool_d1/provider.json'),read(r/'d2_continuation_r1/closeout_r1/provider.json')]
assert all(not x['owned_containers'] and all(y['state']=='stopped' for y in x['apps']) for x in provider)
verify(prep/'inputs',read(prep/'inputs/manifest.json')['files'])
out=Path('reports/p008_20261013/student_admission_v1');out.mkdir(exist_ok=False)
spec={**old,'schema':'p008_student_numeric_admission_v1','status':'exact_student_specs_frozen_external_G1_pending','pool_review_pending':True,'students_require_future_exact_input_spec_G1':True,'config_sha256':s['config_sha256'],'configs':s['configs'],'common_targets':s['common_targets'],'draw_local_oracle_sha256':s['draw_local_oracle_sha256'],'common_plan_gate_sha256':s['common_plan_gate_sha256'],'pool_admission_sha256':s['pool_admission_sha256'],'student_inputs_sha256':s['input_sha256']}
from experiments.sft_allocation_p008.block_journal import POLICY
spec['training_journal_policy']=POLICY
spec['pool_lineages']=s['pool_lineages']
spec['hard_reservation_including_phase0_and_child_usd']=249.68
dump(out/'ADMISSION.json',spec);dump(out/'PREPARATION.json',s)
module=ast.parse(Path('experiments/sft_allocation_p008/modal_students_lineage.py').read_text());names=next(ast.literal_eval(x.value) for x in module.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCES' for t in x.targets));dump(out/'SOURCE_BUNDLE.json',{n:sha(n) for n in names})
shutil.copytree(prep/'inputs',out/'inputs')
shutil.copyfile(r/'prepare_student_inputs_continued.py',out/'PREPARATION_SOURCE.py')
for name in s['configs']:shutil.copyfile(prep/(name+'.json'),out/(name+'.json'))
(out/'REVIEW_REQUEST.md').write_text('''# P008 exact student/input G1 gate\n\nD1 and the independently redecoded original-failed-D2 plus completed-child pool, and all-draw common whole-answer plans passed local oracles, with no student scores or student calls. This immutable packet binds all18 plans,19 configs including base, complete acquired usable inventories, common targets and input manifest to the preserved original campaign/18-74branch.\n\nPlease audit D1 pool raw/replay and this exact student source/input/spec first; D1/main+base may run only after a real fixed-scope acceptance. D2 raw review can follow while D1 students run, but D2 requires its own accepted review. Check q/q+1 including zero, all-draw common targets within registered0.1percent, horizon-normalized LR, no dev/test outcome gating, and the student-only successor's exactG1/terminal/readback/deadline checks, including the real failed parent and separately completed child. No parent status is fabricated. Two retained bridges do not identify fullB×T interaction. No acceptance is fabricated by this publisher.\n''')
dump(out/'MANIFEST.json',manifest(out));print(json.dumps(dict(packet=str(out),spec_sha256=digest(spec),external_review='pending',new_model_calls=0)))
