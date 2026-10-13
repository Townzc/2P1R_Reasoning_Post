"""Prepared merged G1: original failed parent plus separately completed child; no fake parent terminal."""
import argparse
from collections import defaultdict
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
from experiments.sft_allocation_p008.contract import stable_seed
from experiments.sft_allocation_p008.continuation_binding import validate_continuation_binding, PROBE, probe_forecast
from experiments.sft_allocation_p008.pool_continuation_prefix import load_prefix
from experiments.sft_allocation_p008.procurement import Wallet
from experiments.sft_allocation_p008.procurement import replay
from experiments.sft_allocation_acquisition.contract import messages,completion,assess
from src.sft_data import read_jsonl


def audit(root,inputs,tokenizer,receipt,ledger,campaign,run_id,parent_preservation,prefix):
 from transformers import AutoTokenizer
 prefix=Path(prefix);root=Path(root);env=read(receipt);db=read(ledger);base='midpoint/'+campaign+'/'
 assert env['receipt']==db[base+'terminal/'+run_id] and env['receipt']['status']=='completed'
 assert digest(env['artifact_manifest'])==env['receipt']['evidence_sha256'];verify(root,env['artifact_manifest'])
 sent=read(root/'intent.json');config=sent['config'];spec=read(root/'admission.json')
 validate_continuation_binding(sent['plan'],config,sent['release'],spec)
 assert config['run_id']==run_id and config['role']=='pool_continuation' and sent['plan']['campaign_id']==campaign
 claim=db[base+'claim/'+run_id];bound=db[base+'intent/'+run_id]
 assert claim['intent_sha256']==digest(bound) and claim['plan_sha256']==digest(sent['plan'])
 assert bound['source_sha256']==digest(sent['release']['source_files']) and bound['config_sha256']==digest(config)
 assert bound['data_sha256']==config['prefix_manifest_sha256'] and env['receipt']['claim_sha256']==digest(claim)
 assert sha(Path(inputs)/'manifest.json')==config['input_sha256'];verify(inputs,read(Path(inputs)/'manifest.json')['files'])
 assert read(root/'artifact_manifest.json')==env['artifact_manifest']
 hardware=read(root/'environment.json')
 assert 'H100' in hardware['gpu'] and hardware['cuda']=='12.8'
 assert {**hardware['versions'],'torch':hardware['versions']['torch'].split('+')[0]}=={'torch':'2.8.0','vllm':'0.11.0','transformers':'4.56.2','tokenizers':'0.22.1','numpy':'2.2.6'}
 parent_preservation=Path(parent_preservation);parent=parent_preservation/'evidence'
 parentdb=read(parent_preservation/'ledger.json');parentbase='midpoint/p008-main-20261013-r1/'
 rec=spec['reconciliation'];verify(parent,read(parent_preservation/'LOCAL_MANIFEST.json'))
 assert sha(parent_preservation/'LOCAL_MANIFEST.json')==spec['parent_preservation_manifest_sha256']
 assert parentdb[parentbase+'terminal/pool_d2']==rec['parent_terminal'] and rec['parent_terminal']['status']=='failed'
 assert digest(read(parent/'failure_manifest.json'))==rec['parent_terminal']['evidence_sha256']
 for key,value in spec['parent_records'].items():assert parentdb[key]==value
 assert read(parent/'intent.json')['release']['commit']==rec['parent_source_commit']
 assert read(prefix/'RECONCILIATION.json')==rec
 assert sha(prefix/'RECONCILIATION.json')==spec['reconciliation_sha256']
 origins={'parent':(parent,parentdb,parentbase+'pool_d2/'),'child':(root,db,base+run_id+'/')}
 units_by_origin={'parent':set(),'child':set()}
 def unit_source(unit):
  candidates=[(label,r,d,k) for label,(r,d,k) in origins.items() if k+'unit/'+unit in d]
  assert len(candidates)==1,'Every original/child unit must have exactly one actual origin'
  label,r,d,k=candidates[0];units_by_origin[label].add(unit)
  intent=read(r/'intents'/(unit+'.json'));done=read(r/'completed'/(unit+'.json'))
  assert intent==d[k+'unit/'+unit] and done==d[k+'done/'+unit]
  return label,r,intent,done
 measure=read(root/'PRE_MODEL_TIMING.json')
 check=probe_forecast(measure['read_samples_seconds'],measure['remaining_seconds'])
 assert measure['passed'] is True and all(measure[k]==v for k,v in check.items())
 assert measure['pre_model'] is True and measure['charged_to_this_worker'] is True
 assert measure['complete_keys_per_check']==5+len(spec['parent_records'])
 assert read(root/'guard_read_metrics.json')['cache_across_checks'] is False
 draw=config['draw'];assert draw==2
 result=read(root/'result.json');assert result==env['result']
 parents=read_jsonl(Path(inputs)/'eligible_parents.jsonl');parents=sorted(parents,key=lambda r:stable_seed('question_order',draw,r['id']))
 assert len(parents)==6973
 lookup={p['id']:p for p in parents};tok=AutoTokenizer.from_pretrained(tokenizer,local_files_only=True)
 prompt_ids={p['id']:tok.apply_chat_template(messages(p),tokenize=True,add_generation_prompt=True) for p in parents}
 lengths={p:len(v) for p,v in prompt_ids.items()};frozen=read(root/'frozen_wallets.json')
 assert frozen['parent_order']==list(lookup) and frozen['prompt_lengths']==lengths
 wallets=[Wallet(list(lookup),lengths,2,b,p,s) for b in (1,8) for p in (0,4) for s in ('breadth','depth')]
 restored,lineage=load_prefix(prefix,config,wallets,list(lookup),lengths)
 assert read(root/'parent_lineage.json')==result['parent_lineage']==lineage
 assert result['original_parent_status']=='failed' and result['cumulative_parent_plus_child'] is True
 cache={};seen=defaultdict(dict);accepted=defaultdict(dict);attempt_numbers=defaultdict(list);units=set();returned_tokens=0;generation_seconds=0.0
 for index in range(result['physical_batches']):
  unit=f'physical_batch_{index:05d}';units.add(unit)
  label,physical_root,intent,done=unit_source(unit)
  assert label==('parent' if index<146 else 'child')
  assert intent['maximum_new_tokens']==1024
  raw=read(physical_root/(unit+'_raw.json'));saved=read(physical_root/(unit+'_scored.json'));part=intent['items']
  assert len(part)==len(raw['outputs'])==len(saved)==done['count'] and 0<len(part)<=32
  assert raw['seconds']==done['seconds'] and raw['seconds']>=0
  generation_seconds+=raw['seconds']
  assert sha(physical_root/(unit+'_raw.json'))==done['raw_sha256'] and sha(physical_root/(unit+'_scored.json'))==done['scored_sha256']
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
     label,event_root,intent,done=unit_source(unit)
     assert intent==e['intent'] and done==e['done']
 assert physical_consumed==set(cache), 'No unrequested teacher outputs permitted'
 for label,(origin,ledger_db,keyprefix) in origins.items():
  for kind in ('unit','done'):
   assert {k.split('/'+kind+'/',1)[1] for k in ledger_db if k.startswith(keyprefix+kind+'/')}==units_by_origin[label]
  assert {p.stem for p in (origin/'intents').glob('*.json')}==units_by_origin[label]
  assert {p.stem for p in (origin/'completed').glob('*.json')}==units_by_origin[label]
 assert result['child_physical_attempts']==result['child_physical_outputs']==len(cache)-3992
 assert result['child_returned_tokens']==returned_tokens-1190193
 assert result['child_physical_batches']==result['physical_batches']-146
 assert {k:v for k,v in cache.items() if k in restored['cache']}==restored['cache']
 assert 0<=result['wall_seconds']<=7200 and result['reserved_cost_usd']==12
 assert sent['hard_stop_epoch']==min(sent['started_epoch']+7200,sent['plan']['deadline_epoch'])
 assert env['receipt']['finished_epoch']<=sent['hard_stop_epoch']
 assert env['receipt']['actual_cost_cents']==1200
 for label,(origin,_,_) in origins.items():
  names={p.name for p in origin.glob('physical_batch_*_raw.json')}
  expected={u+'_raw.json' for u in units_by_origin[label] if u.startswith('physical_batch_')}
  assert names==expected
 return dict(passed=True,draw=draw,parent_status='failed',child_status='completed',parent_plus_child_redecoded=True,
   parent_physical_outputs=3992,child_physical_outputs=len(cache)-3992,parent_reconciliation_sha256=spec['reconciliation_sha256'],
   parent_terminal=rec['parent_terminal'],child_terminal=env['receipt'],physical_outputs=len(cache),all_raw_redecoded=True,all_wallets_replayed=True,
   wallets=summaries,returned_tokens=returned_tokens,generation_seconds=generation_seconds,
   source_commit=sent['release']['commit'],input_sha256=config['input_sha256'],spec_sha256=digest(spec),manifest_digest=digest(env['artifact_manifest']),new_model_calls=0,
   hardware_counterfactual_or_reasoning_validation=False)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for key in ('root','inputs','tokenizer','receipt','ledger','campaign','run-id','out','parent-preservation','prefix'):p.add_argument('--'+key,required=True)
 a=p.parse_args();r=audit(a.root,a.inputs,a.tokenizer,a.receipt,a.ledger,a.campaign,a.run_id,a.parent_preservation,a.prefix);dump(a.out,r);print('G1 local raw and wallet audit passed')
