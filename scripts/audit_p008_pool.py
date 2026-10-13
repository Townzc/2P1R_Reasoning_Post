"""Prepared independent local raw-token scoring and legal-wallet replay for G1."""
import argparse
from collections import defaultdict
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
from experiments.sft_allocation_p008.contract import stable_seed
from experiments.sft_allocation_p008.main_binding import validate_binding
from experiments.sft_allocation_p008.procurement import replay
from experiments.sft_allocation_acquisition.contract import messages,completion,assess
from src.sft_data import read_jsonl


def audit(root,inputs,tokenizer,receipt,ledger,campaign,run_id):
 from transformers import AutoTokenizer
 root=Path(root);env=read(receipt);db=read(ledger);base='midpoint/'+campaign+'/'
 assert env['receipt']==db[base+'terminal/'+run_id] and env['receipt']['status']=='completed'
 assert digest(env['artifact_manifest'])==env['receipt']['evidence_sha256'];verify(root,env['artifact_manifest'])
 sent=read(root/'intent.json');config=sent['config'];spec=read(root/'admission.json')
 validate_binding(sent['plan'],config,sent['release'],spec)
 assert config['run_id']==run_id and config['role']=='pool' and sent['plan']['campaign_id']==campaign
 claim=db[base+'claim/'+run_id];bound=db[base+'intent/'+run_id]
 assert claim['intent_sha256']==digest(bound) and claim['plan_sha256']==digest(sent['plan'])
 assert bound['source_sha256']==digest(sent['release']['source_files']) and bound['config_sha256']==digest(config)
 assert bound['data_sha256']==config['input_sha256'] and env['receipt']['claim_sha256']==digest(claim)
 assert sha(Path(inputs)/'manifest.json')==config['input_sha256'];verify(inputs,read(Path(inputs)/'manifest.json')['files'])
 assert read(root/'artifact_manifest.json')==env['artifact_manifest']
 hardware=read(root/'environment.json')
 assert 'H100' in hardware['gpu'] and hardware['cuda']=='12.8'
 assert hardware['versions']=={'torch':'2.8.0','vllm':'0.11.0','transformers':'4.56.2','tokenizers':'0.22.1','numpy':'2.2.6'}
 draw=config['draw'];assert draw in (1,2)
 result=read(root/'result.json');assert result==env['result']
 parents=read_jsonl(Path(inputs)/'eligible_parents.jsonl');parents=sorted(parents,key=lambda r:stable_seed('question_order',draw,r['id']))
 assert len(parents)==6973
 lookup={p['id']:p for p in parents};tok=AutoTokenizer.from_pretrained(tokenizer,local_files_only=True)
 prompt_ids={p['id']:tok.apply_chat_template(messages(p),tokenize=True,add_generation_prompt=True) for p in parents}
 lengths={p:len(v) for p,v in prompt_ids.items()};frozen=read(root/'frozen_wallets.json')
 assert frozen['parent_order']==list(lookup) and frozen['prompt_lengths']==lengths
 cache={};seen=defaultdict(dict);accepted=defaultdict(dict);attempt_numbers=defaultdict(list);units=set();returned_tokens=0;generation_seconds=0.0
 for index in range(result['physical_batches']):
  unit=f'physical_batch_{index:05d}';units.add(unit)
  intent=read(root/'intents'/(unit+'.json'));done=read(root/'completed'/(unit+'.json'))
  assert intent==db[base+run_id+'/unit/'+unit] and done==db[base+run_id+'/done/'+unit]
  assert intent['maximum_new_tokens']==1024
  raw=read(root/(unit+'_raw.json'));saved=read(root/(unit+'_scored.json'));part=intent['items']
  assert len(part)==len(raw['outputs'])==len(saved)==done['count'] and 0<len(part)<=32
  assert raw['seconds']==done['seconds'] and raw['seconds']>=0
  generation_seconds+=raw['seconds']
  assert sha(root/(unit+'_raw.json'))==done['raw_sha256'] and sha(root/(unit+'_scored.json'))==done['scored_sha256']
  for item,y,s in zip(part,raw['outputs'],saved):
   pid=item['problem_id'];cid=f"d{draw}::{pid}::{item['attempt']}"
   assert item['candidate_id']==y['candidate_id']==cid and item['draw']==draw
   assert item['seed']==stable_seed('teacher',draw,pid,item['attempt'])
   assert cid not in cache and item['attempt']==len(attempt_numbers[pid])+1
   assert y['prompt_token_ids']==prompt_ids[pid]
   stop=completion(y['token_ids']);text=tok.decode(stop['text_token_ids'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
   assert y['finish_reason']==('stop' if stop['eos'] else 'length')
   v=assess(lookup[pid],text,stop,seen[pid],accepted[pid])
   expected=dict(**item,text=text,prompt_tokens=lengths[pid],completion_tokens=stop['token_count'],stop=stop,**v)
   assert expected==s
   returned_tokens+=stop['token_count']
   cache[cid]=expected;attempt_numbers[pid].append(item['attempt']);seen[pid].setdefault(v['normalized_text_sha256'],cid)
   if v['usable']:accepted[pid].setdefault(v['normalized_text_sha256'],cid)
 assert len(cache)==result['physical_attempts']==result['physical_outputs']<=config['max_physical_attempts']<=16384
 assert read(root/'candidate_cache.json')==cache and result['unknown']==0 and result['returned_tokens']==returned_tokens
 assert result['new_student_updates']==0
 summaries={};physical_consumed=set()
 for b in (1,config['high_multiple']):
  for price in (0,4):
   for policy in ('breadth','depth'):
    name=f'd{draw}_b{b}_p{price}_{policy}';events=read(root/(name+'_events.json'))
    summary=replay(list(lookup),lengths,draw,b,price,policy,events,cache)
    assert summary==read(root/(name+'_summary.json'))==result['wallets'][name]
    summaries[name]=summary;physical_consumed.update(summary['consumed_candidate_ids'])
    for e in events:
     unit=name+'_'+e['intent']['batch'];units.add(unit)
     assert read(root/'intents'/(unit+'.json'))==e['intent']==db[base+run_id+'/unit/'+unit]
     assert read(root/'completed'/(unit+'.json'))==e['done']==db[base+run_id+'/done/'+unit]
 assert physical_consumed==set(cache), 'No unrequested teacher outputs permitted'
 for kind in ('unit','done'):
  assert {k.split('/'+kind+'/',1)[1] for k in db if k.startswith(base+run_id+'/'+kind+'/')}==units
 return dict(passed=True,draw=draw,physical_outputs=len(cache),all_raw_redecoded=True,all_wallets_replayed=True,
   wallets=summaries,returned_tokens=returned_tokens,generation_seconds=generation_seconds,
   source_commit=sent['release']['commit'],input_sha256=config['input_sha256'],spec_sha256=digest(spec),manifest_digest=digest(env['artifact_manifest']),new_model_calls=0,
   hardware_counterfactual_or_reasoning_validation=False)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for key in ('root','inputs','tokenizer','receipt','ledger','campaign','run-id','out'):p.add_argument('--'+key,required=True)
 a=p.parse_args();r=audit(a.root,a.inputs,a.tokenizer,a.receipt,a.ledger,a.campaign,a.run_id);dump(a.out,r);print('G1 local raw and wallet audit passed')
