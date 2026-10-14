"""PREPARED ONLY. Real scoped reviews required; never creates a PASS."""
from pathlib import Path
import copy,sys,subprocess
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
from experiments.sft_allocation_p008.student_t8_cap_binding import validate_student_binding,expected_mapping,ORIGINAL,FAILED
r=Path(__file__).resolve().parent;s=r/'student_completion_r1';cap=r/'t8_cap_9600_r1';run=sys.argv[1]
packet=Path('reports/p008_20261013/student_t8_cap_9600_v1');verify(packet,read(packet/'MANIFEST.json'))
spec=read(packet/'ADMISSION.json');cfg=read(r/'student_preparation_r1'/(run+'.json'))
assert run in spec['runs'] and cfg==spec['configs'][run] and cfg['training_multiple']==8
source=read(packet/'SOURCE_BUNDLE.json');review=read(cap/'RUNTIME_ACCEPTED.json');numeric=read(cap/'NUMERIC_ACCEPTED.json')
for rev,scope in [(review,'t8-cap-9600-runtime'),(numeric,'t8-cap-9600-numeric')]:
 assert rev['scope']==scope and rev['source_files']==source and rev['spec_sha256']==digest(spec)
 assert sha(r/rev['local_report_path'])==rev['review_report_sha256']
 for n,h in source.items():
  assert sha(n)==h and subprocess.check_output(['git','show',rev['target_commit']+':'+n])==Path(n).read_bytes()
proposal=read(r/'T8_TIMING_PROPOSAL_REPLACEMENTS.json')
assert proposal==spec['original_failed_timing_proposal'] and numeric['proposal_file_sha256']==sha(r/'T8_TIMING_PROPOSAL_REPLACEMENTS.json')
assert numeric['original_N2_passed'] is False and numeric['post_hoc_engineering_deviation'] is True
old=spec['original_g1_releases'][str(cfg['draw'])]
gates=copy.deepcopy(old['gates'])
gates.update(runtime_review=review,cap_owner=read(cap/'OWNER_T8_CAP_9600.json'),t8_timing_proposal=proposal,t8_numeric_review=numeric)
records=[]
for logical,item in expected_mapping(spec['original_spec']).items():
 root=s if item['campaign']==ORIGINAL else r/'student_lr_replacements_r1';physical=item['run_id'];close=root/'closeouts'/physical;export=root/'exports'/physical/'evidence'
 envelope=read(root/'runs'/physical/'result.json');terminal=envelope['receipt']
 assert terminal==proposal['provenance'][logical]['terminal']
 assert sha(export/'LOCAL_ORACLE_AUDIT.json')==proposal['provenance'][logical]['oracle_sha256']
 assert read(export/'LOCAL_ORACLE_AUDIT.json')['passed'] is True
 provider=read(close/'provider.json');assert not provider['owned_containers'] and all(x['state']=='stopped' for x in provider['apps'])
 records.append(dict(campaign=item['campaign'],run_id=physical,terminal=terminal))
failed=read(s/'lr_preflight_failures_r1/RECONCILED.json');assert failed['runs']==proposal['failed_attempts_retained']
records += [dict(campaign=ORIGINAL,run_id=n,terminal=failed['runs'][n]['terminal']) for n in FAILED]
gates['t1_terminal_records']=records
assert gates['upload']==read(r/'student_preparation_r1/UPLOAD_VERIFIED.json')
assert sha(r/'student_preparation_r1/inputs/manifest.json')==cfg['input_sha256']
release=dict(source_files=source,spec_sha256=digest(spec),gates=gates)
validate_student_binding(read(s/'plan.json'),cfg,release,spec)
assert not (s/'runs'/run).exists(), 'Never overwrite an existing local attempt'
dump(s/'gates_t8_cap'/(run+'.json'),gates)
print('Prepared genuinely reviewed amended T8 gate only; no image/upload/remote writes.')
