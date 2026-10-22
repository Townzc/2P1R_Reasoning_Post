"""First per-endpoint metadata projection from already decoded original outputs.
No tokenizer, correctness scoring, bootstrap, model or binary-state access.
"""
from pathlib import Path
from collections import Counter
import json,hashlib,datetime
R=Path('.local/p011_20261020/r1')
OUT=R/'OWNER150_ENDPOINT_STOP_COUNTS.json'
assert not OUT.exists()
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
smoke=read(R/'owner150_smoke_posthoc_r1/RESULT.json')
names=['long_baseline_S-L15_s17_owner_r1','long_A1_S-F15_s17_owner_r2','long_A5_S-F15_s17_owner_r1','long_A6_S-F15_s17_owner_r1','long_A7_S-F15_s17_owner_r1']
expected={'math500_sample':2000,'math500_greedy':500,'aime24_sample':240,'aime25_sample':240,'amc23_sample':320}
saved={}
for name in names:
 base=R/'long_owner_closeout_r1';folder=base/'audit'/name;proof=read(folder/'COMPLETE_PROOF.json');score=read(base/'score'/name/'COMPLETED.json')['read_only_saved_score_proof'];assert proof['passed'] and score['passed'] and proof['endpoint']['technical_unknown']==0
 counters={k:Counter() for k in expected}
 reused=name in smoke['observations']
 if reused:
  s=smoke['observations'][name];assert s['sample_count']==2000
  counters['math500_sample'].update(native_eos=s['sample_native_eos'],length_cap=2000-s['sample_native_eos'])
 rows=read(folder/'SCORING_ROWS.json')
 for row in rows:
  benchmark=row['id'].split(':',1)[0];label=benchmark+('_sample' if ':sample:' in row['id'] else '_greedy')
  assert label in expected and row['stop_reason'] in ('native_eos','length_cap')
  if reused and label=='math500_sample':continue
  counters[label][row['stop_reason']]+=1
 for label,count in counters.items():assert sum(count.values())==expected[label]
 saved[name]={'endpoints':{k:{'total':expected[k],'native_eos':v['native_eos'],'length_cap':v['length_cap'],'technical_unknown':0,'native_eos_fraction':v['native_eos']/expected[k]} for k,v in counters.items()},'original_global_stop_counts':proof['endpoint']['logical_stops'],'math_sample_counter_reused_from_original_posthoc':reused,'score_proof_sha256':sha(base/'score'/name/'COMPLETED.json'),'scoring_rows_sha256':sha(folder/'SCORING_ROWS.json')}
with OUT.open('x') as f:json.dump({'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'jobs':saved,'D1_D2_counts_already_in_independent_report_not_recomputed':True,'no_decode_score_bootstrap_or_model_call':True,'posthoc_diagnostic_not_causal_mediation_estimate':True,'original_A7_baseline_smoke_file':str(R/'owner150_smoke_posthoc_r1/RESULT.json'),'producer_sha256':sha(__file__)},f,indent=2);f.write('\n')
print(json.dumps({'path':str(OUT),'jobs':len(saved),'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}))
