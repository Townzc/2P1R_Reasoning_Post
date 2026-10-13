"""PREPARED ONLY. Requires both real pool local oracles before one CPU freeze.

No model calls. Does not admit students; exact inputs/plans must go to G1 first.
"""
from pathlib import Path
import json,datetime,shutil
from transformers import AutoTokenizer
from experiments.sft_allocation_midpoint.common import read,dump,sha,manifest,digest
from experiments.sft_allocation_acquisition.student_contract import training_rows
from experiments.sft_allocation_p008.student_plans import common_plans
from experiments.sft_allocation_p008.student_runtime import validate_plan
from experiments.sft_allocation_p008.contract import run_roster
from src.sft_data import encode_row
r=Path(__file__).resolve().parent;spec=read('reports/p008_20261013/main_admission_v1/ADMISSION.json');branch=tuple(spec['branch'])
with (r/'pool_inputs/eligible_parents.jsonl').open() as parent_file:
 parents=[json.loads(x) for x in parent_file if x.strip()]
tok=AutoTokenizer.from_pretrained('.local/midpoint_20261011/data_pipeline/reconstruction_r1/tokenizer',local_files_only=True)
corpora={};plain={};audits={};lineages={}
from experiments.sft_allocation_p008.pool_lineage import validate_pool_lineages
for d in range(1,branch[2]+1):
 if d==1:
  root=r/'exports/pool_d1/evidence';receipt=read(r/'runs/pool_d1/result.json');ledger=read(r/'closeouts/pool_d1/ledger.json')
  claim=ledger['midpoint/p008-main-20261013-r1/claim/pool_d1']
  provider=read(r/'closeouts/pool_d1/provider.json')
 else:
  cr=r/'d2_continuation_r1';root=cr/'export_r1/evidence';receipt=read(cr/'runs/pool_d2_remaining/result.json');ledger=read(cr/'closeout_r1/ledger.json')
  claim=ledger['midpoint/p008-d2-continuation-20261013-r1/claim/pool_d2_remaining']
  provider=read(cr/'closeout_r1/provider.json')
 oracle=read(root/'LOCAL_ORACLE_AUDIT.json')
 assert oracle['passed'] and oracle['draw']==d and oracle['manifest_digest']==receipt['receipt']['evidence_sha256'] and receipt['receipt']['status']=='completed'
 assert not provider['owned_containers'] and all(x['state']=='stopped' for x in provider['apps'])
 cache=read(root/'candidate_cache.json');audits[str(d)]=dict(oracle_sha256=sha(root/'LOCAL_ORACLE_AUDIT.json'),terminal=receipt['receipt'],physical_outputs=oracle['physical_outputs'])
 if d==1:
  lineages['1']=dict(kind='completed_original',local_oracle_sha256=sha(root/'LOCAL_ORACLE_AUDIT.json'),original=dict(campaign='p008-main-20261013-r1',run_id='pool_d1',terminal=receipt['receipt'],claim=claim))
 else:
  original=read(r/'interrupted_pools/pool_d2/reconciliation_r1/RECONCILIATION.json')
  assert original['parent_terminal']==ledger['midpoint/p008-main-20261013-r1/terminal/pool_d2']
  assert all(x['state']=='stopped' for x in provider['original_apps'])
  lineages['2']=dict(kind='failed_parent_completed_child',merged_oracle_sha256=sha(root/'LOCAL_ORACLE_AUDIT.json'),
   parent=dict(campaign='p008-main-20261013-r1',run_id='pool_d2',claim=original['parent_claim'],terminal=original['parent_terminal']),
   child=dict(campaign='p008-d2-continuation-20261013-r1',run_id='pool_d2_remaining',claim=claim,terminal=receipt['receipt']),
   merged_proof=oracle,parent_reconciliation_sha256=sha(r/'interrupted_pools/pool_d2/reconciliation_r1/RECONCILIATION.json'))
 for b in (1,branch[0]):
  for price in (0,4):
   for policy in ('breadth','depth'):
    name=f'd{d}_b{b}_p{price}_{policy}';summary=oracle['wallets'][name];records=[cache[k] for k in summary['consumed_candidate_ids']]
    acquired_ids=read(root/'frozen_wallets.json')['parent_order'][:summary['acquired_problems']]
    rows=training_rows(parents,acquired_ids,records);assert len(rows)==summary['usable_answers']
    encoded=[encode_row(x,tok,2048) for x in rows]
    for row,enc in zip(rows,encoded):row['source'].update({k:enc[k] for k in ('n_prompt','n_supervised','n_processed')})
    key=(d,b,price,policy);plain[key]=rows;corpora[key]=[dict(path_id=x['path_id'],problem_id=x['problem_id'],**{k:e[k] for k in ('n_supervised','n_processed','n_prompt')}) for x,e in zip(rows,encoded)]
# All-draw feasibility precedes creating any student input or observing any student endpoint.
validate_pool_lineages(lineages,{k:v['oracle_sha256'] for k,v in audits.items()})
plans=common_plans(corpora,branch)
out=r/'student_preparation_r1';out.mkdir(exist_ok=False);inputs=out/'inputs';inputs.mkdir();rowfiles={}
for key,rows in plain.items():
 d,b,price,policy=key;name=f'd{d}_b{b}_p{price}_{policy}.jsonl';rowfiles[key]=name
 with (inputs/name).open('x') as f:
  for x in rows:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n')
for run,p in plans['plans'].items():dump(inputs/(run+'_plan.json'),p)
common={k:v['realized'] for k,v in plans['dose_choices'].items()}
dump(inputs/'COMMON_PLAN_GATE.json',dict(passed=True,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),common_targets=common,dose_choices=plans['dose_choices'],plans={k:sha(inputs/(k+'_plan.json')) for k in plans['plans']},draw_local_audits=audits,pool_lineages=lineages,main_scores_not_read=True))
endpoint=Path('.local/midpoint_20261011/teacher_policy_r1/inputs/gsm8k_test1319.jsonl')
assert len(endpoint.read_text().splitlines())==1319
shutil.copyfile(endpoint,inputs/'gsm8k_test1319.jsonl')
dump(inputs/'manifest.json',dict(files=manifest(inputs),all_usable_inventory_retained=True,balanced_exposure_including_zero=True,draw_local_audits=audits,official_endpoint_previously_seen_by_researcher=True))
configs={}
for item in run_roster(*branch):
 key=(item['draw'],item['budget_multiple'],item['price'],item['policy']);run=item['run_id'];cfg={**item,'targets':common[str(item['training_multiple'])],'max_seconds':spec['slot_max_seconds'][run], 'input_directory':'student_inputs','input_sha256':sha(inputs/'manifest.json'),'rows_file':rowfiles[key],'plan_file':run+'_plan.json'}
 validate_plan(plain[key],[encode_row(x,tok,2048) for x in plain[key]],plans['plans'][run],cfg)
 dump(out/(run+'.json'),cfg);configs[run]=cfg
base=dict(run_id='base',role='base',updates=0,targets=0,max_seconds=spec['slot_max_seconds']['base'],input_directory='student_inputs',input_sha256=sha(inputs/'manifest.json'))
dump(out/'base.json',base);configs['base']=base
summary=dict(status='prepared_not_dispatched_requires_exact_G1',branch=list(branch),configs=configs,config_sha256={k:digest(v) for k,v in configs.items()},common_targets=common,draw_local_oracle_sha256={k:v['oracle_sha256'] for k,v in audits.items()},input_sha256=sha(inputs/'manifest.json'),common_plan_gate_sha256=sha(inputs/'COMMON_PLAN_GATE.json'),endpoint_roster_sha256=sha(endpoint),pool_lineages=lineages,pool_admission_sha256=sha('reports/p008_20261013/main_admission_v1/ADMISSION.json'),plan_sha256=digest(read(r/'student_completion_r1/plan.json')),original_plan_sha256=spec['plan_sha256'],student_completion_owner_sha256=digest(read(r/'OWNER_STUDENT_COMPLETION.json')),new_model_calls=0)
dump(out/'PREPARATION.json',summary);print(json.dumps(dict(student_runs=len(configs)-1,common_targets=common,status=summary['status'])))
