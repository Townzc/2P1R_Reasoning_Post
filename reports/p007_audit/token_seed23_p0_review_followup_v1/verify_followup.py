"""Saved-evidence checks for Claude round9; no new model calls or rescoring rule."""
from pathlib import Path
import datetime,json,hashlib
import numpy as np
from transformers import AutoTokenizer
from analyses.completion_contract import first_stop,completion_score

root=Path(__file__).resolve().parent
private=root.parent
packet=Path('reports/p007_audit/token_p0_two_seeds_v1')
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=read(packet/'paired_question_scores.json')
assert len(rows)==1319 and [x['problem_id'] for x in rows]==sorted({x['problem_id'] for x in rows})
columns=['breadth_p0_s17','depth_p0_s17','breadth_p0_s23','depth_p0_s23']
a=np.array([[int(x[k]) for k in columns] for x in rows]);assert a.sum(axis=0).tolist()==[963,950,958,958]
flip=dict(breadth_between_seeds=int((a[:,0]!=a[:,2]).sum()),depth_between_seeds=int((a[:,1]!=a[:,3]).sum()),within_seed17_between_policies=int((a[:,0]!=a[:,1]).sum()),within_seed23_between_policies=int((a[:,2]!=a[:,3]).sum()))
assert flip==dict(breadth_between_seeds=183,depth_between_seeds=156,within_seed17_between_policies=219,within_seed23_between_policies=208)
d=np.stack([a[:,1]-a[:,0],a[:,3]-a[:,2]],axis=1);rng=np.random.default_rng(20261013);boots=np.empty((10000,2))
for i in range(10000):boots[i]=d[rng.integers(0,1319,1319)].mean(axis=0)*100
summary=read(packet/'summary.json');contrasts={}
for col,seed in enumerate((17,23)):
 estimate=float(d[:,col].mean()*100);ci=np.quantile(boots[:,col],[.025,.975]).tolist()
 assert np.allclose(estimate,summary['contrasts'][str(seed)]['depth_minus_breadth_pp'],atol=1e-12)
 assert np.allclose(ci,summary['contrasts'][str(seed)]['conditional_question_bootstrap_95_pp'],atol=1e-12)
 contrasts[str(seed)]=dict(depth_minus_breadth_pp=estimate,conditional_question_bootstrap_95_pp=ci)
tok=AutoTokenizer.from_pretrained('.local/midpoint_20261011/data_pipeline/reconstruction_r1/tokenizer',local_files_only=True)
decode=lambda ids:tok.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
cases=[]
for run,num,gold in [('breadth_p0_s23',498,'40'),('depth_p0_s23',1169,'2')]:
 pid=f'gsm8k/test/{num:05d}';start=(num//16)*16;out=private/'student_exports'/run
 scoredfile=out/'endpoint1319'/f'batch_{start:04d}_scored.jsonl';rawfile=out/'endpoint1319'/f'batch_{start:04d}_raw.json'
 records=[json.loads(x) for x in scoredfile.read_text().splitlines()];idx=next(i for i,x in enumerate(records) if x['problem_id']==pid);record=records[idx];raw=read(rawfile);done=read(out/'completed'/f'endpoint1319_batch_{start:04d}.json')
 assert sha(rawfile)==done['raw_sha256'] and sha(scoredfile)==done['scored_sha256']
 assert raw['problem_ids'][idx]==pid and raw['batch_output_ids'][idx]==record['batch_output_ids']
 ids=raw['batch_output_ids'][idx];event=first_stop(ids,decode,tok.eos_token_id,512,set(tok.all_special_ids)|{i for i in ids if i>=len(tok)})
 assert event==record['stop'] and event['stop_reason']=='native_eos'
 text=tok.decode(ids[:event['retained_tokens']-1],skip_special_tokens=False,clean_up_tokenization_spaces=False)
 assert text==record['raw_text']
 score=completion_score(record,event);assert score==record['task_score'] and score['task_answer_correct'] is False
 claims=score['marked']['claims'];assert record['answer']==gold and any(x['kind']=='answer_statement' and x['payload']=='' for x in claims) and any(x['kind']=='box' and x['value']==gold for x in claims)
 cases.append(dict(run=run,problem_id=pid,gold=gold,claims=claims,stop_reason=event['stop_reason'],raw_batch_sha256=sha(rawfile),scored_batch_sha256=sha(scoredfile),raw_ids_independently_decoded=True,primary_correct=False,primary_unchanged=True))
proof=dict(schema='p007_token_round9_followup_v1',checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),review=read(root/'READ.json'),packet_manifest_sha256=sha(packet/'manifest.json'),paired_file_sha256=sha(packet/'paired_question_scores.json'),primary_counts={k:int(a[:,i].sum()) for i,k in enumerate(columns)},contrasts=contrasts,bootstrap=dict(seed=20261013,replicates=10000,unit='shared paired questions, conditional on the four trained price0 models'),prediction_flip_counts=flip,new_e2_cases=cases,disposition=['S9-1 accepted: report both realized training seeds; question intervals do not cover seed/procurement uncertainty; two repeats cannot estimate robust population seed variance.','At price0 the observed differences are -0.9856pp and0.0000pp, both conditional intervals cross zero; neither a stable winner nor equivalence is established.','Cross-seed flips are descriptive, not an isolated variance component: schedules/order and per-answer exposure can vary by seed.','E2-b both new cases independently decoded; frozen primary scores unchanged. Uniform sensitivity is deferred until all eight complete, not computed for selected models now.','C9-1 acknowledged: bounded sparse-block transport has full-file SHA gate; no transport/source change is needed, original failure retained.','Claude scope now includes independent two seed23 price0 final-state hashes and saved raw-score checks, but not per-step weight trajectories or final high-price outcomes.'],new_model_calls=0,live_protocol_unchanged=True)
with (root/'INDEPENDENT_FOLLOWUP.json').open('x') as f:json.dump(proof,f,indent=2,ensure_ascii=False);f.write('\n')
print(json.dumps(dict(contrasts=contrasts,flip_counts=flip,new_e2_cases=[x['problem_id'] for x in cases],primary_unchanged=True)))
