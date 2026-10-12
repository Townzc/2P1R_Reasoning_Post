"""Published original candidate calculation, parametrized to a new output file.
Requires preserved audited source exports; will not overwrite old evidence.
"""
from pathlib import Path
import argparse
from collections import defaultdict
import json,math
from experiments.sft_allocation_midpoint.common import read,dump
from experiments.sft_allocation_acquisition.contract import SAMPLING
p=argparse.ArgumentParser(description='CPU-only regeneration from preserved audited teacher exports; no GPU calls.')
p.add_argument('--policy-root',required=True);p.add_argument('--pilot-export',required=True);p.add_argument('--out',required=True);args=p.parse_args()
r=Path(args.policy_root);sources=read(r/'ACQUISITION_SOURCES.json');pilot=Path(args.pilot_export)
pr=[x for p in sorted((pilot/'scored').glob('*.json')) for x in read(p)]
assert len(pr)==1024
m=sum(x['prompt_tokens']+x['stop']['token_count'] for x in pr)/1024
Batches={};full={}
for cell,s in sources.items():
 root=Path(s['export']);b=[]
 for folder in ([root/'parent',root] if s.get('recovery') else [root]):
  for p in sorted((folder/'scored').glob('*.json')):
   b.append(dict(name=p.stem,rows=read(p),intent=read(folder/'intents'/p.name)))
 Batches[cell]=b;rows=[x for b in b for x in b['rows']];a=read(root/'LOCAL_ORACLE_AUDIT.json');g=a['generation_ns']/1e9;tt=sum(x['stop']['token_count'] for x in rows);pt=sum(x['prompt_tokens'] for x in rows)
 full[cell]=dict(prompt_tokens=pt,generated_tokens_including_eos=tt,generation_seconds=g,ms_per_generated_token=1000*g/tt,known_actual_outputs=len(rows),usable=sum(x['usable'] for x in rows),hypothetical_full_charge=pt+tt+(4*m*len({x['problem_id'] for x in rows}) if cell.endswith('p4') else 0))
# Diagnostic choice from data availability, before any student accuracy. Fixed ceiling, no result maximization.
cap=math.floor(min(x['hypothetical_full_charge'] for x in full.values()))
res={}
for cell,batches in Batches.items():
 price=4*m if cell.endswith('p4') else 0
 spent=0.;seen=set();used=[];stop='tape_exhausted';accepted_batches=0
 for b in batches:
  rows=b['rows'];assert len(rows)==16
  new={x['problem_id'] for x in rows}-seen
  # Ex ante worst-case completion reservation: full fixed16 slots or stop; no peek at generated lengths to choose a batch.
  reserve=price*len(new)+sum(x['prompt_tokens'] for x in rows)+16*SAMPLING['max_new_tokens']
  if spent+reserve>cap:stop='cannot_reserve_full16_action';break
  spent+=price*len(new)+sum(x['prompt_tokens']+x['stop']['token_count'] for x in rows)
  assert spent<=cap;seen|=new;used+=rows;accepted_batches+=1
 res[cell]=dict(acquired=len(seen),covered=len({x['problem_id'] for x in used if x['usable']}),usable=sum(x['usable'] for x in used),attempts=len(used),batches=accepted_batches,charge=spent,cap=cap,unused=(cap-spent)/cap,stop_reason=stop,accepted_candidates=[x['candidate_id'] for x in used])
result=dict(schema='cpu_only_candidate_token_budget_diagnostic_v1',admitted=False,student_outputs_used=False,new_model_calls=0,input_output_price_ratio=1,units='hypothetical billable prompt+completion tokens, one unit each; not measured dollars',pilot_mean_units_per_attempt=m,problem_prices=[0,4*m],cap=cap,full_trace=full,candidate=res,limitations=['Hypothetical tariff, not wall-clock money or measured API price.','A saved-trace prefix simulation; actual original collection spent extra beyond selected prefixes.','One trace per strategy; lacks procurement replication.','Ceiling selected by trace availability, not accuracy; must freeze a new version before student use.'])
dump(args.out,result)
print(json.dumps({k:v for k,v in result.items() if k!='candidate'},ensure_ascii=False))
print(json.dumps({k:{n:v for n,v in a.items() if n!='accepted_candidates'} for k,a in res.items()},ensure_ascii=False))
