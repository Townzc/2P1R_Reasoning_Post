"""Bounded report from four already-verified price0 students; no model work."""
from pathlib import Path
import datetime,json,shutil
import numpy as np
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,manifest
from scripts.summarize_token_students import exposure_summary
from src.sft_data import read_jsonl

r=Path(__file__).resolve().parent
out=Path('reports/p007_audit/token_p0_two_seeds_v1')
assert not out.exists()
spec=read('reports/sft_allocation_midpoint_20261011/P007B_TOKEN_STUDENT_ADMISSION.json')
models={};pred={};receipts={};sources={}
for seed in (17,23):
 for cell in ('breadth_p0','depth_p0'):
  run=f'{cell}_s{seed}';ep=r/'students'/f'{run}_run_r1/result.json';ap=r/'student_exports'/run/'LOCAL_ORACLE_AUDIT.json';pp=r/'student_closeouts'/run/'provider.json'
  e,a,p=read(ep),read(ap),read(pp);z=e['result'];v=read(r/'student_exports'/run/'LOCAL_VERIFICATION.json')
  assert a['run_id']==run and a['campaign']==spec['campaign_id'] and a['seed']==seed
  assert a['updates_verified']==256 and a['supervised_tokens_verified']==524287 and a['outputs_independently_rescored']==1319
  assert a['correct']==z['endpoint']['correct'] and a['artifact_digest']==e['receipt']['evidence_sha256']==digest(e['artifact_manifest'])
  assert a['input_sha256']==spec['input_sha256'] and e['receipt']['status']=='completed'
  assert p['app']['state']=='stopped' and not p['containers'] and v['files_verified']==861 and v['full_checkpoint_steps']==[256]
  q=z['endpoint']['question_correct'];assert len(q)==1319 and all(type(x) is bool for x in q.values()) and sum(q.values())==a['correct']
  inputs=r/'student_preparation_r2/inputs'
  exposure=exposure_summary(read_jsonl(inputs/f'{cell}_train.jsonl'),read(inputs/f'{cell}_seed{seed}.json'))
  models[run]=dict(seed=seed,cell=cell,correct=a['correct'],n=1319,accuracy=a['correct']/1319,updates=256,supervised_targets=524287,state_sha256=a['state_sha256'],artifact_digest=a['artifact_digest'],stop_diagnostics=a['endpoint_stop_diagnostics'],training_exposure=exposure,procurement=spec['selection'][cell],wall_seconds=z['wall_seconds'],train_seconds=z['train_seconds'],runtime_rate_estimate_usd=z['runtime_rate_estimate_usd'],provider_stopped=True,containers=0)
  pred[run]=q;receipts[run]=e['receipt'];sources[run]=dict(source_commit=read(ep.parent/'intent.json')['release']['commit'],oracle_sha256=sha(ap),envelope_sha256=sha(ep),provider_sha256=sha(pp))
ids=sorted(next(iter(pred.values())));assert all(sorted(q)==ids for q in pred.values())
paired=[dict(problem_id=i,**{run:q[i] for run,q in pred.items()}) for i in ids]
idx=np.random.default_rng(20261013).integers(0,1319,(10000,1319));contrasts={}
for seed in (17,23):
 delta=np.array([int(pred[f'depth_p0_s{seed}'][i])-int(pred[f'breadth_p0_s{seed}'][i]) for i in ids])
 contrasts[str(seed)]=dict(depth_minus_breadth_pp=float(delta.mean()*100),conditional_question_bootstrap_95_pp=np.quantile(delta[idx].mean(axis=1)*100,[.025,.975]).tolist(),breadth_only=int((delta==-1).sum()),depth_only=int((delta==1).sum()))
billing=read(sorted((r/'billing').glob('*.json'))[-1]);billing.pop('report',None)
summary=dict(schema='p007b_token_price0_two_training_seeds_v1',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),campaign=spec['campaign_id'],models=models,sources=sources,contrasts=contrasts,bootstrap=dict(replicates=10000,seed=20261013,unit='paired questions shared across the four fixed price0 models'),training_seeds=[17,23],teacher_traces_per_cell=1,updates_verified=1024,supervised_targets_verified=2097148,raw_outputs_independently_rescored=5276,unknown_endpoint_outputs=0,full_states_verified=4,billing=billing,remaining_frozen_student_runs=2,final_cloud_audit='pending',external_review='New seed23 outcomes and this packet pending; earlier scoped seed17 review does not extend to new outcomes.',limits=['Same per-cell teacher corpus in both seeds: training repeats, not procurement replication.','Question intervals condition on trained models and data, not seed or procurement confidence.','The second-seed high-price outcomes are still pending; no completed two-seed price-interaction claim.','Common hypothetical token cap is not equal realized spending or real API dollars.','Fixed training targets include unequal repeated exposure; not isolated reasoning diversity or repetition damage.','All length caps remain incorrect; E2 primary scores unchanged.','Official test researcher-observed in September; not a fresh uncontaminated test.','Old time-priced pilots are not pooled; non-significance is not equivalence.'])
out.mkdir();dump(out/'summary.json',summary);dump(out/'paired_question_scores.json',paired);dump(out/'receipts.json',receipts)
for run in models:
 shutil.copyfile(r/'student_exports'/run/'LOCAL_ORACLE_AUDIT.json',out/f'{run}_local_audit.json')
 shutil.copyfile(r/'student_exports'/run/'artifact_manifest.json',out/f'{run}_artifact_manifest.json')
shutil.copyfile(__file__,out/'report_builder.py')
(out/'REVIEW_REQUEST.md').write_text('''# Price0: two training seeds, one teacher trace per cell

Pin this packet to its ordinary publication commit. The new seed23 pair has
complete1319-output independent raw-score oracles,256updates/524287targets and
full terminal states, and both GPU apps have stopped. Recompute each seed's
depth-minus-breadth contrast from paired_question_scores.json, using10000
shared paired-question resamples/seed20261013 for conditional intervals.
Large raw token arrays and states remain in the original local student_exports;
manifests list their hashes. The preserved report builder requires those local
envelopes/oracles. Compact scores alone cannot independently decode all tokens
or reconstruct weights. Earlier Claude verdicts on seed17 do not cover seed23.

This is price0 only. The final price4mseed23 pair and cloud audit remain pending;
do not report a complete two-seed price interaction yet. Two training seeds
share each cell's teacher-answer inventory; they do not replicate procurement.
Keep caps incorrect, full denominators and unchanged E2 primary scores. All
common-cap, unequal exposure, trace and benchmark-history limitations remain.
''')
dump(out/'manifest.json',dict(schema='audit_packet_manifest_v1',files=manifest(out),scope='Four price0 fixed students,5276 raw outputs/four state-dose local audits. New seed23 results, not final eight-run study.',external_review='pending'))
dump('reports/sft_allocation_midpoint_20261011/P007B_TOKEN_ZERO_PRICE_TWO_SEEDS.json',summary)
dump(r/'SEED23_P0_PAIR_CLOSED.json',dict(utc=summary['utc'],both_passed=True,both_provider_stopped=True,summary_sha256=sha(out/'summary.json'),oracles={run:sources[run]['oracle_sha256'] for run in models if run.endswith('_s23')},packet_manifest_sha256=sha(out/'manifest.json')))
print(json.dumps(dict(models={run:dict(correct=m['correct'],n=m['n'],caps=m['stop_diagnostics']['length_cap_outputs']) for run,m in models.items()},contrasts=contrasts,billing=billing)))
