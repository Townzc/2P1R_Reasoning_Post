"""Independent local replay of P007B acquisition roster, scores and actual wallet.

No model calls. Does not call Policy, Wallet, choose_action, or a cloud function.
A successful audit is an engineering check, not an external Claude audit.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read,sha,digest,verify,dump
from experiments.sft_allocation_acquisition.contract import SAMPLING,REVISION,messages,completion,assess

HOUR_NS=3_600_000_000_000

def charge(ns,rate):
    assert type(ns) is int and ns>=0
    return (ns*rate+HOUR_NS-1)//HOUR_NS


def audit(args):
    from transformers import AutoTokenizer
    root=Path(args.export_dir);inputs=Path(args.inputs)
    envelope=read(args.receipt);ledger=read(args.ledger)
    intent=read(root/'intent.json');cfg=intent['config'];run_id=cfg['run_id']
    prefix='midpoint/'+args.campaign+'/'
    # The local synthetic fixture tests accounting, not cloud provenance.
    if args.campaign != 'fixture':
        spec=read('reports/sft_allocation_midpoint_20261011/P007B_ADMISSION.json')
        assert args.campaign==spec['campaign_id'] and digest(intent['plan'])==spec['plan_sha256']
        assert digest(cfg)==spec['acquisition_config_sha256'][run_id]
        claim=ledger[prefix+'claim/'+run_id]
        bound=ledger[prefix+'intent/'+run_id]
        assert bound['config_sha256']==digest(cfg) and bound['data_sha256']==cfg['input_sha256']
        assert bound['source_sha256']==digest(intent['release']['source_files'])
        assert claim['intent_sha256']==digest(bound) and claim['plan_sha256']==digest(intent['plan'])
        assert claim['run_id']==run_id
    assert envelope['receipt']==ledger[prefix+'terminal/'+run_id]
    assert envelope['receipt']['status']=='completed'
    if args.campaign != 'fixture':
        assert envelope['receipt']['claim_sha256']==digest(claim)
        assert envelope['receipt']['attempt_id']==claim['attempt_id']
        assert ledger[prefix+'attempt/'+run_id+'/'+claim['attempt_id']]==claim
    files=read(root/'artifact_manifest.json')
    assert files==envelope['artifact_manifest'] and digest(files)==envelope['receipt']['evidence_sha256']
    verify(root,files)
    assert read(root/'LOCAL_VERIFICATION.json')['files_verified']==len(files)
    result=read(root/'result.json');assert result==envelope['result']
    assert result['status']=='completed' and result['model_revision']==REVISION and result['student_updates']==0
    assert sha(inputs/'manifest.json')==cfg['input_sha256']
    verify(inputs,read(inputs/'manifest.json')['files'])
    parents=[json.loads(x) for x in (inputs/'fresh_parents.jsonl').read_text().splitlines()]
    ids=[x['id'] for x in parents];lookup={x['id']:x for x in parents}
    assert len(ids)==len(lookup)==1024
    tok=AutoTokenizer.from_pretrained(args.tokenizer,local_files_only=True,padding_side='left')
    tok.pad_token_id=151643
    batches=sorted((root/'intents').glob('*.json'))
    names=[f'batch_{i:04d}' for i in range(len(batches))]
    assert [p.stem for p in batches]==names and len(names)<=cfg['max_batches']
    for kind,folder in [('unit','intents'),('done','completed')]:
        key=prefix+run_id+'/'+kind+'/'
        assert {k[len(key):] for k in ledger if k.startswith(key)}==set(names)
        assert {p.stem for p in (root/folder).glob('*.json')}==set(names)
    for folder in ('settlements','raw','scored'):
        assert {p.stem for p in (root/folder).glob('*.json')}==set(names)
    start=result['active_start_ns'];cap=cfg['cap_nanodollars'];rate=cfg['hourly_nanodollars'];price=cfg['problem_nanodollars']
    if args.campaign != 'fixture':
        assert all(result[k]==cfg[k] for k in ('cap_nanodollars','hourly_nanodollars','problem_nanodollars','target_usable','sampling_seed','policy'))
    seen=defaultdict(dict);eligible_seen=defaultdict(dict);history={};records=[];cursor=0;active=[]
    last_clock=start;generation_ns=checker_ns=0;maximum_action_ns=0
    for i,name in enumerate(names):
        sent=read(root/'intents'/f'{name}.json');done=read(root/'completed'/f'{name}.json')
        settle=read(root/'settlements'/f'{name}.json');reserve=sent['reservation']
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
        assert all(settle[k]==v for k,v in reserve.items())
        end=settle['finished_ns'];assert now<=end<=reserve['deadline_ns']
        actual=cursor*price+charge(end-start,rate)
        assert settle['cumulative_spent_nanodollars']==actual<=cap
        assert settle['remaining_nanodollars']==cap-actual
        maximum_action_ns=max(maximum_action_ns,end-now);last_clock=end
    end=result['active_end_ns'];assert end>=last_clock
    spent=cursor*price+charge(end-start,rate)
    assert result['active_ns']==end-start and result['spent_nanodollars']==spent<=cap
    assert result['unspent_nanodollars']==cap-spent
    assert result['unspent_fraction']==(cap-spent)/cap
    assert result['parent_outcomes']==history and result['acquired_ids']==ids[:cursor]
    assert result['acquired_problems']==cursor and result['physical_outputs']==len(records)==result['attempted_candidates']
    assert result['usable']==sum(r['usable'] for r in records)
    assert result['unknown']==0 and result['unresolved_batch'] is False
    assert result['zero_usable_parents']==sum(not any(r['usable'] for r in rows) for rows in history.values())
    assert result['active_parents']==len(active) and result['pool_exhausted']==(cursor==len(ids))
    assert result['stop_reason'] in ('wallet_cannot_reserve_next_bounded_action','pool_exhausted','finite_batch_limit')
    if result['stop_reason']=='pool_exhausted':assert cursor==len(ids) and not active
    if result['stop_reason']=='finite_batch_limit':assert len(names)==cfg['max_batches']
    if result['stop_reason']=='wallet_cannot_reserve_next_bounded_action':
        room=min(16-len(active),len(ids)-cursor)
        assert not any(len(active)+n>0 and spent+n*price+charge(cfg['max_action_seconds']*10**9,rate)<=cap
                       for n in range(room+1))
    # Data quality screening is the fixed final-answer/stop contract, not proof of reasoning.
    return dict(schema='local_acquisition_policy_audit_v1',campaign=args.campaign,run_id=run_id,
        outputs_independently_rescored=len(records),manifest_digest=digest(files),new_model_calls=0,
        config_sha256=digest(cfg),input_sha256=sha(inputs/'manifest.json'),
        batches=len(names),acquired=cursor,usable=result['usable'],zero_usable_parents=result['zero_usable_parents'],
        generation_ns=generation_ns,checker_ns=checker_ns,maximum_action_ns=maximum_action_ns,
        active_ns=end-start,cap_nanodollars=cap,spent_nanodollars=spent,
        unspent_fraction=result['unspent_fraction'],stop_reason=result['stop_reason'],
        failures=sum(not r['score']['clean_correct'] for r in records),
        rejected_valid_duplicates=sum(r['score']['clean_correct'] and r['usable_duplicate_of'] is not None for r in records),
        all_attempts_cost_bearing=True,unknown=0,external_claude_review='pending',provider_invoice_usd=None)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('campaign','export-dir','inputs','tokenizer','receipt','ledger','out'):p.add_argument('--'+key,required=True)
    args=p.parse_args();result=audit(args);dump(args.out,result);print(json.dumps(result))
