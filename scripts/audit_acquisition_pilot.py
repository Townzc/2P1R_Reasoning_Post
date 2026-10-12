"""Independent local reconstruction of teacher attempts, scoring, duplicates and cost shares."""
import argparse,json
from pathlib import Path
from collections import defaultdict
from experiments.sft_allocation_midpoint.common import read,sha,digest,verify,dump
from experiments.sft_allocation_acquisition.contract import roster,completion,assess,summarize,SAMPLING,messages


def audit(args):
    from transformers import AutoTokenizer
    root=Path(args.export_dir);inputs=Path(args.inputs)
    envelope=read(args.receipt);ledger=read(args.ledger);prefix='midpoint/'+args.campaign+'/'
    assert envelope['receipt']==ledger[prefix+'terminal/pilot']
    assert envelope['receipt']['status']=='completed'
    files=read(root/'artifact_manifest.json');assert files==envelope['artifact_manifest']
    assert digest(files)==envelope['receipt']['evidence_sha256'];verify(root,files)
    assert read(root/'LOCAL_VERIFICATION.json')['files_verified']==len(files)
    result=read(root/'result.json');assert result==envelope['result']
    intent=read(root/'intent.json');assert sha(inputs/'manifest.json')==intent['config']['input_sha256']
    verify(inputs,read(inputs/'manifest.json')['files'])
    parents=[json.loads(x) for x in (inputs/'parents.jsonl').read_text().splitlines()]
    batches=roster(parents);assert batches==read(inputs/'batches.json')
    lookup={r['id']:r for r in parents}
    tok=AutoTokenizer.from_pretrained(args.tokenizer,local_files_only=True,padding_side='left');tok.pad_token_id=151643
    seen=defaultdict(dict);records=[];generation=checking=0
    all_units={b['batch_id'] for b in batches}
    assert {x.stem for x in (root/'intents').glob('*.json')}==all_units
    assert {x.stem for x in (root/'completed').glob('*.json')}==all_units
    for b in batches:
        name=b['batch_id'];sent=read(root/'intents'/f'{name}.json');done=read(root/'completed'/f'{name}.json')
        assert sent==ledger[prefix+'pilot/unit/'+name] and done==ledger[prefix+'pilot/done/'+name]
        assert sent['batch']==b and sent['sampling']==SAMPLING
        rawfile=root/'raw'/f'{name}.json';scoredfile=root/'scored'/f'{name}.json'
        assert sha(rawfile)==done['raw_sha256'] and sha(scoredfile)==done['scored_sha256']
        raw=read(rawfile);scored=read(scoredfile);items=b['items']
        prompts=[tok.apply_chat_template(messages(lookup[i['problem_id']]),tokenize=False,add_generation_prompt=True) for i in items]
        packed=tok(prompts,padding=True,truncation=False,add_special_tokens=False)
        assert packed['input_ids']==sent['prompt_token_ids'] and packed['attention_mask']==sent['attention_mask']
        assert raw['items']==items and len(scored)==len(items)==done['count']==len(raw['batch_output_ids'])
        width=raw['prompt_width'];assert width==len(packed['input_ids'][0])
        for item,tokens,saved,prompt_ids,mask in zip(items,raw['batch_output_ids'],scored,packed['input_ids'],packed['attention_mask']):
            assert tokens[:width]==prompt_ids
            stop=completion(tokens[width:]);text=tok.decode(stop['text_token_ids'],skip_special_tokens=False)
            value=assess(lookup[item['problem_id']],text,stop,seen[item['problem_id']])
            expected=dict(**item,text=text,stop=stop,**value,prompt_tokens=sum(mask),batch_id=name,batch_size=len(items),
                allocated_generation_seconds=raw['generation_seconds']/len(items),allocation_is_batch_share_not_independent_marginal_cost=True)
            assert saved==expected
            seen[item['problem_id']].setdefault(value['normalized_text_sha256'],item['candidate_id'])
            records.append(saved)
        assert done['candidate_ids']==[x['candidate_id'] for x in scored]
        assert done['generation_seconds']==raw['generation_seconds']
        assert done['output_tokens']==sum(x['stop']['token_count'] for x in scored)
        assert done['usable']==sum(x['usable'] for x in scored)
        assert done['duplicates']==sum(x['duplicate_of'] is not None for x in scored)
        generation+=done['generation_seconds'];checking+=done['checker_seconds']
    for k,v in summarize(parents,records).items():assert result[k]==v
    assert result['generation_seconds']==generation and result['checker_seconds']==checking
    assert result['recorded_outputs']==result['attempted']==1024 and result['student_updates']==0
    costs=[]
    for parent in parents:
        rows=sorted([r for r in records if r['problem_id']==parent['id']],key=lambda r:r['attempt'])
        for k in (1,2,4):
            prefix_rows=[];success=0
            for row in rows:
                prefix_rows.append(row);success+=row['usable']
                if success==k:break
            costs.append(dict(problem_id=parent['id'],k=k,reached=success>=k,
                attempts=len(prefix_rows),output_tokens=sum(r['stop']['token_count'] for r in prefix_rows),
                allocated_batch_seconds=sum(r['allocated_generation_seconds'] for r in prefix_rows),
                interpretation='Observed fixed-tape prefix accounting; not executed adaptive-policy latency.'))
    return dict(schema='local_teacher_cost_pilot_audit_v1',campaign=args.campaign,manifest_digest=digest(files),
        input_sha256=sha(inputs/'manifest.json'),outputs_independently_rescored=len(records),new_model_calls=0,
        all_failures_and_duplicates_preserved=True,result=result,cost_to_k=costs,
        overhead_seconds=result['wall_seconds']-generation-checking,
        provider_invoice_usd=None,invalid_inference='These teacher costs cannot price the historical bank or prove an optimal allocation.')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['campaign','export-dir','inputs','tokenizer','receipt','ledger','out']:p.add_argument('--'+key,required=True)
    a=p.parse_args();result=audit(a);dump(a.out,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ['result','cost_to_k']}))
