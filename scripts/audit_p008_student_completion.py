"""Prepared P008 local full-state/dose/raw endpoint oracle, no model execution."""
import argparse,datetime,json,math
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
from experiments.sft_allocation_midpoint import checkpoint as ck
from experiments.sft_allocation_p008.student_runtime import validate_plan,EVAL
from experiments.sft_allocation_p008.completion_student_binding import validate_student_binding
from experiments.sft_allocation_p008.block_journal import POLICY,verify_training_blocks
from src.sft_data import read_jsonl,encode_row,prefix
from analyses.e017_audit import audit_predictions
from scripts.audit_token_student import endpoint_stop_diagnostics


def audit(args):
 from transformers import AutoTokenizer
 root=Path(args.export_dir);inputs=Path(args.inputs);env=read(args.receipt);db=read(args.ledger)
 sent=read(root/'intent.json');cfg=sent['config'];run=cfg['run_id'];base='midpoint/'+args.campaign+'/'
 spec=read(args.admission)
 assert read(root/'admission.json')==spec
 validate_student_binding(sent['plan'],cfg,sent['release'],spec)
 assert digest(cfg)==spec['config_sha256'][run] and digest(sent['plan'])==spec['plan_sha256']
 assert sha(inputs/'manifest.json')==cfg['input_sha256'];verify(inputs,read(inputs/'manifest.json')['files'])
 receipt=env['receipt'];assert receipt==db[base+'terminal/'+run] and receipt['status']=='completed'
 claim=db[base+'claim/'+run];bound=db[base+'intent/'+run]
 assert claim['intent_sha256']==digest(bound) and claim['plan_sha256']==digest(sent['plan'])
 assert bound['config_sha256']==digest(cfg) and bound['source_sha256']==digest(sent['release']['source_files'])
 assert bound['data_sha256']==cfg['input_sha256'] and receipt['claim_sha256']==digest(claim)
 files=read(root/'artifact_manifest.json');assert files==env['artifact_manifest'] and digest(files)==receipt['evidence_sha256'];verify(root,files)
 result=read(root/'result.json');assert result==env['result']
 tok=AutoTokenizer.from_pretrained(args.tokenizer,local_files_only=True)
 intents={p.stem:read(p) for p in (root/'intents').glob('*.json')};done={p.stem:read(p) for p in (root/'completed').glob('*.json')}
 assert set(intents)==set(done)
 blocks=verify_training_blocks(intents,done,db,base+run+'/',cfg['updates'])
 metrics=read(root/'block_journal_metrics.json')
 assert all(metrics[k]==v for k,v in dict(policy=POLICY,completed_blocks=len(blocks),completed_local_updates=cfg['updates'],configured_updates=cfg['updates'],block_boundary_calls=2*len(blocks)).items())
 assert all(type(metrics[k]) in (int,float) and math.isfinite(metrics[k]) and metrics[k]>=0 for k in ('block_boundary_seconds','local_step_write_seconds','maximum_block_boundary_seconds'))
 expected=set(blocks);targets=processed=0;state_hash=None;forensic={}
 if cfg['role']!='base':
  rows=read_jsonl(inputs/cfg['rows_file']);encoded=[encode_row(r,tok,2048) for r in rows]
  plan=read(inputs/cfg['plan_file']);budget=validate_plan(rows,encoded,plan,cfg)
  assert read(root/'training_journal_policy.json')==POLICY
  recipe=read(root/'recipe.json');assert json.loads(json.dumps(budget))==recipe['budget']
  assert recipe['identity']['config']==cfg and recipe['eval']==EVAL
  state_path=root/f"checkpoint_{cfg['updates']:04d}";state=ck.load(state_path,recipe['identity']);state_hash=sha(state_path/'state.pt')
  assert state['schedule']==plan['updates'] and state['lrs']==plan['lrs'] and state['cursor']==state['step']==cfg['updates']
  forensic={}
  for step,indices in enumerate(plan['updates'],1):
   name=f'update_{step:04d}';expected.add(name)
   item=dict(step=step,indices=indices,lr=plan['lrs'][step-1],supervised_tokens=sum(encoded[i]['n_supervised'] for i in indices),
      processed_tokens=sum(encoded[i]['n_processed'] for i in indices))
   assert intents[name]==item and all(done[name][k]==v for k,v in item.items())
   targets+=item['supervised_tokens'];processed+=item['processed_tokens']
   assert done[name]['cumulative_targets']==targets and done[name]['cumulative_processed']==processed
   if cfg['updates']==2048 and step==1024:
    mid=root/'checkpoint_1024';m=ck.load(mid,recipe['identity'])
    assert m['cursor']==m['step']==1024 and m['schedule']==plan['updates'] and m['lrs']==plan['lrs']
    assert m['supervised_tokens']==targets and m['processed_tokens']==processed
    forensic['1024']=dict(sha256=sha(mid/'state.pt'),targets=targets,processed=processed,used_for_selection=False)
  assert targets==cfg['targets']==state['supervised_tokens']==result['targets']
  assert processed==state['processed_tokens']==result['processed_tokens']
  assert result['updates']==cfg['updates']
 else:assert cfg['updates']==cfg['targets']==result['updates']==result['targets']==0
 rows=read_jsonl(inputs/'gsm8k_test1319.jsonl');assert len(rows)==1319;saved=[]
 for start in range(0,1319,16):
  part=rows[start:start+16];unit=f'endpoint1319_batch_{start:04d}';expected.add(unit)
  assert intents[unit]==dict(problem_ids=[r['problem_id'] for r in part],count=len(part),config=EVAL)
  rf=root/'endpoint1319'/f'batch_{start:04d}_raw.json';sf=root/'endpoint1319'/f'batch_{start:04d}_scored.jsonl'
  assert sha(rf)==done[unit]['raw_sha256'] and sha(sf)==done[unit]['scored_sha256']
  raw=read(rf);rescored=audit_predictions(sf,part,tok,EVAL)
  assert raw['problem_ids']==[r['problem_id'] for r in part]
  assert raw['input_ids']==[tok(prefix(r['prompt']),add_special_tokens=False)['input_ids'] for r in part]
  assert raw['batch_output_ids']==[r['batch_output_ids'] for r in rescored] and raw['events']==[r['stop'] for r in rescored]
  assert len(rescored)==done[unit]['count'];saved.extend(rescored)
 assert set(done)==expected
 qc={r['problem_id']:r['task_score']['task_answer_correct'] for r in saved}
 assert len(qc)==1319 and all(type(v)is bool for v in qc.values())
 summary=read(root/'endpoint1319/summary.json');assert summary==result['endpoint'] and summary['question_correct']==qc and summary['correct']==sum(qc.values())
 stops=endpoint_stop_diagnostics(saved,summary)
 return dict(passed=True,schema='p008_student_local_oracle_v1',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
   run_id=run,role=cfg['role'],updates_verified=cfg['updates'],targets_verified=targets,outputs_rescored=1319,
   training_journal_policy=POLICY,remote_training_blocks=len(blocks),
   correct=sum(qc.values()),state_sha256=state_hash,forensic_checkpoints=forensic,artifact_digest=digest(files),endpoint_stop_diagnostics=stops,
   new_model_calls=0,external_review='pending')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for k in ('campaign','export-dir','inputs','tokenizer','receipt','ledger','admission','out'):p.add_argument('--'+k,required=True)
 a=p.parse_args();r=audit(a);dump(a.out,r);print(json.dumps(r))
