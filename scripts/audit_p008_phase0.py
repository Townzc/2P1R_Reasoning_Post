"""Independent local Phase0 reconstruction from exported raw files and ledger."""
import argparse
from collections import defaultdict
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
from experiments.sft_allocation_p008.contract import PHASE0_ROLES,overlap_seconds,lrs
from experiments.sft_allocation_acquisition.contract import completion,assess,messages
from src.sft_data import read_jsonl,encode_row


def audit(root,inputs,receipts,ledger_path,teacher_tokenizer,student_tokenizer):
 from transformers import AutoTokenizer
 from experiments.sft_allocation_midpoint import checkpoint as ck
 from analyses.e017_audit import audit_predictions
 root=Path(root);inputs=Path(inputs);receipts=Path(receipts);ledger=read(ledger_path)
 sent=read(receipts/'intent.json');plan=sent['plan'];prefix='midpoint/'+plan['campaign_id']+'/'
 tt=AutoTokenizer.from_pretrained(teacher_tokenizer,local_files_only=True)
 st=AutoTokenizer.from_pretrained(student_tokenizer,local_files_only=True)
 intervals={};manifests={};concurrency_status={}
 for role in PHASE0_ROLES:
  folder=root/role;envelope=read(receipts/(role+'_result.json'));files=envelope['artifact_manifest']
  assert envelope['receipt']==ledger[prefix+'terminal/'+role] and envelope['receipt']['status']=='completed'
  assert digest(files)==envelope['receipt']['evidence_sha256'];verify(folder,files)
  assert read(folder/'intent.json')['release']==sent['release']
  assert read(folder/'result.json')==envelope['result']
  c=read(folder/'concurrency.json');intervals[role]=c['interval'];manifests[role]=digest(files)
  assert c==envelope['result']['concurrency']
  assert c['status'] in ('four_gpu_verified','concurrency_not_achieved')
  concurrency_status[role]=c['status']
  assert set(c['ready'])==set(PHASE0_ROLES)
  assert set(c['acks']) in (set(),set(PHASE0_ROLES))
  for peer in PHASE0_ROLES:
   if c['ready'][peer] is not None:assert c['ready'][peer]==ledger[prefix+'ready/'+peer]
   if c['acks'].get(peer) is not None:assert c['acks'][peer]==ledger[prefix+'ack/'+peer]
   if peer in c['verified']:assert c['verified'][peer]==sha(root/peer/'io_probe.bin')
  if c['status']=='four_gpu_verified':
   assert c['reason'] is None and all(c['ready'].values()) and all(c['acks'].values())
   assert set(c['acks'])==set(c['verified'])==set(PHASE0_ROLES)
  elif c['reason']=='readiness_timeout':
   assert not all(c['ready'].values()) and c['acks']==c['verified']=={}
  else:
   assert c['reason']=='ack_timeout' and all(c['ready'].values()) and not all(c['acks'].values())
   assert set(c['acks'])==set(c['verified'])==set(PHASE0_ROLES)
 overlap=max(0.,overlap_seconds(intervals))
 distinct=len({read(root/r/'concurrency.json')['gpu'].strip().split(',')[-1].strip() for r in PHASE0_ROLES})
 four_gpu_verified=all(v=='four_gpu_verified' for v in concurrency_status.values()) and distinct==4 and overlap>0
 req=read_jsonl(inputs/'calibration_requests.jsonl');records=[];seen=defaultdict(dict);used=defaultdict(dict)
 folder=root/'teacher_calibration';expected_units=set()
 for start in range(0,1024,32):
  name=f'teacher_batch_{start:04d}';expected_units.add(name)
  intent=read(folder/'intents'/(name+'.json'));done=read(folder/'completed'/(name+'.json'))
  assert intent==ledger[prefix+'teacher_calibration/unit/'+name]
  assert done==ledger[prefix+'teacher_calibration/done/'+name]
  part=req[start:start+32];assert intent==dict(candidate_ids=[r['candidate_id'] for r in part],seeds=[r['seed'] for r in part])
  raw=read(folder/(name+'_raw.json'));scored=read(folder/(name+'_scored.json'))
  assert sha(folder/(name+'_raw.json'))==done['raw_sha256'] and sha(folder/(name+'_scored.json'))==done['scored_sha256']
  assert len(raw['outputs'])==len(scored)==done['count']==32 and done['seconds']==raw['seconds']
  for r,y,saved in zip(part,raw['outputs'],scored):
   assert y['candidate_id']==r['candidate_id']
   assert y['prompt_token_ids']==r['prompt_token_ids']==tt.apply_chat_template(messages(r['parent']),tokenize=True,add_generation_prompt=True)
   stop=completion(y['token_ids']);text=tt.decode(stop['text_token_ids'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
   pid=r['problem_id'];value=assess(r['parent'],text,stop,seen[pid],used[pid])
   expected=dict(candidate_id=r['candidate_id'],problem_id=pid,attempt=r['attempt'],seed=r['seed'],text=text,
      prompt_tokens=len(r['prompt_token_ids']),completion_tokens=stop['token_count'],stop=stop,**value)
   assert saved==expected
   assert y['finish_reason']==('stop' if stop['eos'] else 'length')
   seen[pid].setdefault(value['normalized_text_sha256'],r['candidate_id'])
   if value['usable']:used[pid].setdefault(value['normalized_text_sha256'],r['candidate_id'])
   records.append(expected)
 assert {k.split('/unit/',1)[1] for k in ledger if k.startswith(prefix+'teacher_calibration/unit/')}==expected_units
 assert {k.split('/done/',1)[1] for k in ledger if k.startswith(prefix+'teacher_calibration/done/')}==expected_units
 folder=root/'student_smoke';recipe=read(inputs/'smoke_recipe.json');train=read_jsonl(inputs/'smoke_train.jsonl')
 encoded=[encode_row(r,st,2048) for r in train];targets=0
 for step in range(1,9):
  name=f'update_{step:04d}';intent=read(folder/'intents'/(name+'.json'));done=read(folder/'completed'/(name+'.json'))
  assert intent==ledger[prefix+'student_smoke/unit/'+name] and done==ledger[prefix+'student_smoke/done/'+name]
  assert intent['indices']==[step-1] and intent['lr']==lrs(2048)[step-1]
  assert intent['supervised_tokens']==encoded[step-1]['n_supervised'];targets+=intent['supervised_tokens']
  assert done['cumulative_targets']==targets
 assert targets==recipe['supervised_targets']==921
 state=ck.load(folder/'checkpoint_0008')
 assert state['step']==8 and state['supervised_tokens']==targets and state['lrs']==lrs(2048)[:8]
 assert state['schedule']==recipe['schedule'] and state['identity']==read(folder/'recipe.json')['identity']
 erows=read_jsonl(inputs/'smoke_eval.jsonl');ef=folder/'engineering_eval16';raw=read(ef/'batch_0000_raw.json')
 saved=audit_predictions(ef/'batch_0000_scored.jsonl',erows,st,dict(max_new_tokens=512,max_length=2048,eval_batch_size=16))
 assert len(saved)==16 and raw['batch_output_ids']==[r['batch_output_ids'] for r in saved]
 edone=ledger[prefix+'student_smoke/done/engineering_eval16_batch_0000']
 assert edone['raw_sha256']==sha(ef/'batch_0000_raw.json') and edone['scored_sha256']==sha(ef/'batch_0000_scored.jsonl')
 smoke_units={f'update_{s:04d}' for s in range(1,9)}|{'engineering_eval16_batch_0000'}
 for kind in ('unit','done'):
  assert {k.split('/'+kind+'/',1)[1] for k in ledger if k.startswith(prefix+'student_smoke/'+kind+'/')}==smoke_units
 for role in ('io_probe_a','io_probe_b'):
  assert not any(k.startswith(prefix+role+'/unit/') for k in ledger)
 return dict(passed=True,teacher_outputs=1024,teacher_usable=sum(r['usable'] for r in records),
   teacher_tokens=sum(r['completion_tokens'] for r in records),smoke_updates=8,smoke_targets=targets,
   smoke_outputs=16,gpu_overlap_seconds=overlap,four_gpu_verified=four_gpu_verified,
   concurrency_status=concurrency_status,main_dispatch_requires_four_gpu_verified=True,
   manifests=manifests,new_model_calls=0,
   valid_scientific_accuracy_or_equivalence_claim=False,provider_release_must_be_checked_separately=True)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for k in ('root','inputs','receipts','ledger-path','teacher-tokenizer','student-tokenizer','out'):p.add_argument('--'+k,required=True)
 a=p.parse_args();r=audit(a.root,a.inputs,a.receipts,a.ledger_path,a.teacher_tokenizer,a.student_tokenizer);dump(a.out,r);print(r)
