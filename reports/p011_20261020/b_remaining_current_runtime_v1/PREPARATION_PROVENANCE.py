from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
R=Path('.local/p011_20261020/r1');P=Path('reports/p011_20261020/b_remaining_current_runtime_v1')
D=R/'review_formal_long_due_20261021T105115Z'
ERR='fa73636a836a6fef05eb7620eb992cdb7a719003678d306f9c30f57e1e4466e2'
assert not P.exists() and not (R/'B_CURRENT_ACCOUNTING_PREPARED.json').exists()
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,s):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(s)
def dump(p,x):put(p,json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
assert h(D/'ERRATUM_20261021o.md')==ERR
pairs=[('experiments/p011/b_remaining/numeric.py','experiments/p011/b_remaining/current_numeric.py'),('experiments/p011/b_remaining/path.py','experiments/p011/b_remaining/current_path.py'),('experiments/p011/b_remaining/modal_entry.py','experiments/p011/b_remaining/current_modal_entry.py'),('scripts/p011_b_remaining_io.py','scripts/p011_b_remaining_current_io.py')]
assert all(not Path(b).exists() for a,b in pairs)
for a,b in pairs:
 s=Path(a).read_text()
 if b.endswith('current_numeric.py'):
  assert s.count("v['B_protected_floor_usd']!='48'")==1
  s=s.replace("v['B_protected_floor_usd']!='48'","v['B_protected_floor_usd']!='0'")
 elif b.endswith('current_path.py'):
  s=s.replace("SPEC_FILES={'generation':'reports/p011_20261020/b_remaining_runtime_v1/SPEC.json'}", "ERRATUM_SHA='"+ERR+"'\nSPEC_FILES={'generation':'reports/p011_20261020/b_remaining_current_runtime_v1/SPEC.json'}")
  s=s.replace("or spec.get('remaining_outputs')!=5120", "or spec.get('delegated_failure_erratum_sha256')!=ERRATUM_SHA\n            or spec.get('remaining_outputs')!=5120")
  s=s.replace('from experiments.p011.b_remaining.numeric import verify_scenario','from experiments.p011.b_remaining.current_numeric import verify_scenario')
  s=s.replace('delegated_failure_decision_sha256=DECISION_SHA,prefix_files=', 'delegated_failure_decision_sha256=DECISION_SHA,delegated_failure_erratum_sha256=ERRATUM_SHA,prefix_files=')
  s=s.replace("'E3_wall_time_and_two_student_sequential_budget_full_windows_accepted')", "'E3_wall_time_and_two_student_sequential_budget_full_windows_accepted',\n        'reported_B48_clause_void_current_protected0_accepted')")
  assert s.count("budget.get('protected_usd')!='48'")==1 and s.count('))-reserve<48')==1
  s=s.replace("budget.get('protected_usd')!='48'","budget.get('protected_usd')!='0'").replace('))-reserve<48','))-reserve<0').replace("protected_usd='48'","protected_usd='0'")
 elif b.endswith('current_modal_entry.py'):
  s=s.replace('from experiments.p011.b_remaining import path\n','from experiments.p011.b_remaining import current_path as path\n').replace('from experiments.p011.b_remaining import path as run','from experiments.p011.b_remaining import current_path as run')
 else:
  s=s.replace('from experiments.p011.b_remaining import path,transport as new_transport,selection as selected_rules', 'from experiments.p011.b_remaining import current_path as path,transport as new_transport,selection as selected_rules')
 put(b,s)
spec=json.loads(Path('reports/p011_20261020/b_remaining_runtime_v1/SPEC.json').read_text())
spec['source_files'].update({b:h(b) for a,b in pairs})
spec['delegated_failure_erratum_sha256']=ERR
spec['prospective_students_and_score_window']['B_protected_floor_usd']='0'
from experiments.p011.b_remaining import current_path
current_path.validate(spec)
P.mkdir();dump(P/'SPEC.json',spec)
binding=json.loads(Path('reports/p011_20261020/b_remaining_runtime_v1/SOURCE_BINDING.json').read_text())
binding.update(source_files=spec['source_files'],roots=[pairs[2][1],pairs[3][1],'experiments/p011/b_remaining/student_input.py'],
 delegated_failure_erratum_sha256=ERR,original87_candidate_target='7fec6ba31d9507edfd771a051110b21896072d16',
 original87_SPEC_sha256='d130c47743b2f81d3f188c6c36c1cb7b3882494cb0812b9f340ea7ab175086ab',
 all_original87_source_maps_retained_without_rechecking=True,new4_source_files={b:h(b) for a,b in pairs},
 scientific_transport_selection_timing_and_failed_reserve_rules_unchanged=True,protected_usd='0')
dump(P/'SOURCE_BINDING.json',binding)
dump(R/'B_CURRENT_ACCOUNTING_PREPARED.json',dict(utc=datetime.now(timezone.utc).isoformat(),source_count=len(spec['source_files']),new_source_files=binding['new4_source_files'],spec_sha256=h(P/'SPEC.json'),source_binding_sha256=h(P/'SOURCE_BINDING.json'),new_model_calls=0,new_decode_or_score_calls=0,new_reservations=0))
print(json.dumps({'source_count':len(spec['source_files']),'new4':list(binding['new4_source_files']),'protected_usd':'0'}))
