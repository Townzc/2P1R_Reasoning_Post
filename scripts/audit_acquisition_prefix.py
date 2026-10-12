"""Independent audit of the fixed P007B interrupted breadth prefix; no dispatch.

The last known batch has raw, scored and done records but no settlement. An
explicit provider-stop upper charge is a conservative reconstruction, never
claimed to be a measured settlement or a completed original run.
"""
import argparse, datetime, json, math
from collections import defaultdict
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read,sha,digest,verify,dump
from experiments.sft_allocation_acquisition.contract import SAMPLING,REVISION,messages,completion,assess
from scripts.audit_acquisition_policy import charge


def audit_prefix(args):
    from transformers import AutoTokenizer
    recovery=Path(args.recovery_dir);root=recovery/'files';inputs=Path(args.inputs)
    observed=read(recovery/'OBSERVED_MANIFEST.json');verify(root,observed['files'])
    ledger=read(recovery/'ledger.json');intent=read(root/'intent.json');cfg=intent['config']
    run_id=cfg['run_id'];assert run_id=='breadth_p4'
    spec=read('reports/sft_allocation_midpoint_20261011/P007B_ADMISSION.json')
    assert digest(cfg)==spec['acquisition_config_sha256'][run_id]
    assert digest(intent['plan'])==spec['plan_sha256']
    prefix='midpoint/'+intent['plan']['campaign_id']+'/'
    bound=ledger[prefix+'intent/'+run_id];claim=ledger[prefix+'claim/'+run_id]
    assert claim['intent_sha256']==digest(bound) and bound['config_sha256']==digest(cfg)
    assert bound['source_sha256']==digest(intent['release']['source_files'])
    assert ledger.get(prefix+'terminal/'+run_id) is None
    assert sha(inputs/'manifest.json')==cfg['input_sha256'];verify(inputs,read(inputs/'manifest.json')['files'])
    parents=[json.loads(x) for x in (inputs/'fresh_parents.jsonl').read_text().splitlines()]
    ids=[x['id'] for x in parents];lookup={x['id']:x for x in parents};assert len(ids)==len(lookup)==1024
    tok=AutoTokenizer.from_pretrained(args.tokenizer,local_files_only=True,padding_side='left');tok.pad_token_id=151643
    batches=sorted((root/'intents').glob('*.json'));names=[f'batch_{i:04d}' for i in range(len(batches))]
    assert len(names)==12 and [p.stem for p in batches]==names
    for kind,folder in [('unit','intents'),('done','completed')]:
        key=prefix+run_id+'/'+kind+'/'
        assert {k[len(key):] for k in ledger if k.startswith(key)}==set(names)
        assert {p.stem for p in (root/folder).glob('*.json')}==set(names)
    for folder in ('raw','scored'):
        assert {p.stem for p in (root/folder).glob('*.json')}==set(names)
    assert {p.stem for p in (root/'settlements').glob('*.json')}==set(names[:-1])
    start=read(batches[0])['active_start_ns'];cap=cfg['cap_nanodollars'];rate=cfg['hourly_nanodollars'];price=cfg['problem_nanodollars']
    seen=defaultdict(dict);eligible_seen=defaultdict(dict);history={};records=[];cursor=0;active=[]
    last_clock=start;generation_ns=checker_ns=0;maximum_action_ns=0
    for i,name in enumerate(names):
        sent=read(root/'intents'/f'{name}.json');done=read(root/'completed'/f'{name}.json')
        settlement_path=root/'settlements'/f'{name}.json'
        settle=read(settlement_path) if settlement_path.exists() else None
        assert (settle is None)==(i==len(names)-1)
        reserve=sent['reservation']
        assert sent==ledger[prefix+run_id+'/unit/'+name]
        assert done==ledger[prefix+run_id+'/done/'+name]
        assert sent['sampling']==SAMPLING and sent['seed']==cfg['sampling_seed']+i
        assert sent['active_start_ns']==start and reserve['batch_id']==name
        now=reserve['start_ns'];assert now>=last_clock
        previously=cursor*price+charge(now-start,rate)
        bound_ns=cfg['max_action_seconds']*10**9
        maximum=charge(bound_ns,rate)
        room=min(16-len(active),len(ids)-cursor)
        affordable=[n for n in range(room+1) if len(active)+n>0 and previously+n*price+maximum<=cap]
        assert affordable
        n=max(affordable);new_ids=ids[cursor:cursor+n]
        proposal=dict(cursor=cursor,new_problem_ids=new_ids,
                      items=[dict(problem_id=p,attempt=len(history.get(p,[]))+1) for p in active+new_ids])
        assert sent['proposal']==proposal and reserve['new_problem_ids']==new_ids
        assert reserve['previously_spent_nanodollars']==previously
        assert reserve['purchase_nanodollars']==n*price and reserve['maximum_action_nanodollars']==maximum
        assert reserve['deadline_ns']==now+bound_ns
        expected_items=[dict(**r,candidate_id=f"{r['problem_id']}::attempt{r['attempt']:02d}") for r in proposal['items']]
        assert sent['items']==expected_items and len(expected_items)<=16
        for p in new_ids:history[p]=[]
        cursor+=n;active+=new_ids
        rawfile=root/'raw'/f'{name}.json';scoredfile=root/'scored'/f'{name}.json'
        assert sha(rawfile)==done['raw_sha256'] and sha(scoredfile)==done['scored_sha256']
        raw=read(rawfile);scored=read(scoredfile)
        assert raw['items']==expected_items and raw['batch_id']==name
        assert len(scored)==len(expected_items)==len(raw['batch_output_ids'])==done['count']
        prompts=[tok.apply_chat_template(messages(lookup[r['problem_id']]),tokenize=False,add_generation_prompt=True) for r in expected_items]
        packed=tok(prompts,padding=True,truncation=False,add_special_tokens=False)
        assert packed['input_ids']==sent['prompt_token_ids'] and packed['attention_mask']==sent['attention_mask']
        width=raw['prompt_width'];assert width==len(packed['input_ids'][0])
        for item,tokens,saved,prompt,mask in zip(expected_items,raw['batch_output_ids'],scored,packed['input_ids'],packed['attention_mask']):
            assert tokens[:width]==prompt
            pid=item['problem_id'];stop=completion(tokens[width:])
            text=tok.decode(stop['text_token_ids'],skip_special_tokens=False)
            verdict=assess(lookup[pid],text,stop,seen[pid],eligible_seen[pid])
            expected=dict(**item,text=text,stop=stop,**verdict,prompt_tokens=sum(mask),batch_id=name,batch_size=len(expected_items))
            assert saved==expected
            seen[pid].setdefault(verdict['normalized_text_sha256'],item['candidate_id'])
            if verdict['usable']:eligible_seen[pid].setdefault(verdict['normalized_text_sha256'],item['candidate_id'])
            history[pid].append(saved);records.append(saved)
        active=[p for p in active if len(history[p])<8 and sum(r['usable'] for r in history[p])<cfg['target_usable']]
        assert done['candidate_ids']==[r['candidate_id'] for r in scored]
        assert done['generation_ns']==raw['generation_ns']
        assert done['usable']==sum(r['usable'] for r in scored)
        generation_ns+=done['generation_ns'];checker_ns+=done['checker_ns']
        if settle is None:
            last_clock=reserve['deadline_ns']
            continue
        assert all(settle[k]==v for k,v in reserve.items())
        end=settle['finished_ns'];assert now<=end<=reserve['deadline_ns']
        actual=cursor*price+charge(end-start,rate)
        assert settle['cumulative_spent_nanodollars']==actual<=cap
        assert settle['remaining_nanodollars']==cap-actual
        maximum_action_ns=max(maximum_action_ns,end-now);last_clock=end
    provider=read(args.provider)
    app=[x for x in provider['apps'] if x['app_id']=='ap-2mXKLaNtqwckB0Cqu6gTz0']
    assert len(app)==1 and app[0]['state']=='stopped' and not provider['containers']
    # Provider time has whole-second precision. Charge to the end of that second,
    # plus another second of clock margin. It includes the guarded zero-work restart.
    stopped=datetime.datetime.fromisoformat(app[0]['stopped_at']).timestamp()
    last=read(batches[-1]);upper_seconds=math.ceil(stopped+2-last['started_epoch'])
    assert upper_seconds>=cfg['max_action_seconds']
    charged_end_ns=last['reservation']['start_ns']+upper_seconds*10**9
    spent=cursor*price+charge(charged_end_ns-start,rate)
    assert spent<cap and len(records)==192 and all(type(x['usable']) is bool for x in records)
    return dict(schema='p007b_interrupted_prefix_verified_v1',status='interrupted_prefix_verified_not_completed',
        parent_campaign=intent['plan']['campaign_id'],run_id=run_id,config=cfg,original_intent=intent,
        observed_manifest_sha256=sha(recovery/'OBSERVED_MANIFEST.json'),observed_manifest=observed['files'],
        ledger_sha256=sha(recovery/'ledger.json'),provider_snapshot_sha256=sha(args.provider),provider_app=app[0],
        raw_outputs_verified=len(records),known_usable=sum(x['usable'] for x in records),unknown=0,
        acquired_ids=ids[:cursor],parent_outcomes=history,active_parents=active,next_batch_index=12,
        original_active_start_ns=start,charged_end_ns=charged_end_ns,charged_spent_nanodollars=spent,
        charge_method='Provider STOPPED end-of-second plus one-second clock margin; conservative reconstructed upper charge, not measured original settlement.',
        unresolved_original_settlement='batch_0011',charged_last_action_seconds=upper_seconds,
        reserved_last_action_seconds=cfg['max_action_seconds'],
        failed_action_bound_preserved=True,exact_original_active_duration_unknown=True,
        generation_ns=generation_ns,checker_ns=checker_ns,new_model_calls=0,external_claude_review='pending')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('recovery-dir','inputs','tokenizer','provider','out'):p.add_argument('--'+name,required=True)
    a=p.parse_args();result=audit_prefix(a);dump(a.out,result)
    print(json.dumps({k:result[k] for k in ('status','raw_outputs_verified','known_usable','unknown','next_batch_index','charged_spent_nanodollars','charged_last_action_seconds')}))
