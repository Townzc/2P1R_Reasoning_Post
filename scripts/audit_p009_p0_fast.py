#!/usr/bin/env python3
"""Independent CPU-only P0 raw replay; never re-score the closed HF reference."""
import argparse
from collections import Counter
import datetime
import json
from pathlib import Path
from analyses.completion_contract import first_stop, completion_score
from experiments.sft_allocation_midpoint.common import dump, read, sha, digest, verify
from experiments.learning_regime_p009.gates import parity
from experiments.learning_regime_p009.p0_fast_contract import (
    ROLES, RUN, CAMPAIGN, PARENT_CAMPAIGN, PARENT_RUN, BATCH_SIZE,
    prompts_checked, raw_checked, validate_release, remaining_forecast,
)
from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs, validate_observed_engine


def audit(args):
    from transformers import AutoTokenizer
    from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
    spec=read(args.admission); root=Path(args.root); inputs=Path(args.inputs)
    envelope=read(args.receipt); ledger=read(args.ledger); provider=read(args.provider)
    intent=read(root/'intent.json'); plan=intent['plan']; run=RUN
    prefix='midpoint/'+plan['campaign_id']+'/'
    validate_release(spec, plan, intent['release'])
    if plan['campaign_id'] != CAMPAIGN:
        raise ValueError('Fresh campaign required')
    for name, expected in spec['source_files'].items():
        if sha(name) != expected:
            raise ValueError('Reviewed source drift')
    if spec != intent['spec'] or digest(plan) != spec['plan_sha256']:
        raise ValueError('Exact plan/spec changed')
    terminal=ledger[prefix+'terminal/'+run]; claim=ledger[prefix+'claim/'+run]
    if (terminal != envelope['receipt'] or terminal['status'] != 'completed'
            or terminal['claim_sha256'] != digest(claim)
            or terminal['evidence_sha256'] != digest(envelope['artifact_manifest'])):
        raise ValueError('Original completed claim/receipt missing')
    if (provider['app_ids'] != [spec['parent_app_id'], args.app_id] or provider['state'] != 'stopped'
            or provider['owned_container_ids'] != []):
        raise ValueError('Real matching app STOPPED0 required')
    validate_stopped_apps(provider['app_ids'],provider['original_app_info'],provider['owned_containers'])
    oldpre='midpoint/'+PARENT_CAMPAIGN+'/'
    if (ledger[oldpre+'claim/'+PARENT_RUN] != spec['parent_claim']
            or ledger[oldpre+'terminal/'+PARENT_RUN] != spec['parent_terminal']):
        raise ValueError('Historical failed parent changed')
    marker=read(root/'FRESH_CONFIGURATION_MARKER.json')
    expected_marker=dict(kind='owner_plan_A_fresh_configuration',campaign=CAMPAIGN,run_id=RUN,
        claim_sha256=digest(claim),owner_plan_A_sha256=digest(spec['owner_plan_A']),
        fresh_outputs=2638,inherited_outputs=0,parent_stays_failed=True)
    if marker != expected_marker or ledger[oldpre+'continuation/'+PARENT_RUN] != marker:
        raise ValueError('Once-only configuration marker differs')
    result=read(root/'result.json')
    if (result != envelope['result'] or result['outputs'] != 2638
            or result['inherited_outputs'] != 0 or result['new_training_updates'] != 0
            or result['batches'] != 12 or result['old_eager_timings_used'] is not False
            or len(result['full_batch_intervals_seconds']) != 12 or len(result['forecasts']) != 11):
        raise ValueError('Fresh complete endpoint/result provenance differs')
    names={f'{role}_{offset:04d}' for role in ROLES for offset in range(0,1319,BATCH_SIZE)}
    for kind in ('unit','done'):
        if {k.removeprefix(prefix+RUN+'/'+kind+'/') for k in ledger
                if k.startswith(prefix+RUN+'/'+kind+'/')} != names:
            raise ValueError('Missing, extra or unacknowledged scientific attempt')
    if {p.stem for p in (root/'intents').glob('*.json')} != names:
        raise ValueError('Unexpected local attempt journal')
    for i, forecast in enumerate(result['forecasts'], start=1):
        if forecast != read(root/'forecasts'/f'{i:03d}.json') or not forecast['admitted']:
            raise ValueError('Actual per-batch forecast missing or failed')
        elapsed=forecast['elapsed_worker_seconds']
        replay=remaining_forecast(elapsed,result['full_batch_intervals_seconds'][:i],12-i)
        for k,v in replay.items():
            if isinstance(v,float):
                if abs(v-forecast[k]) > 1e-6:
                    raise ValueError('Actual forecast arithmetic differs')
            elif v != forecast[k]:
                raise ValueError('Actual forecast binding differs')
    verify(root,envelope['artifact_manifest']); verify(inputs,spec['inputs'])
    prompts=prompts_checked(read(inputs/'qwen_gsm_zero_parity.json'))
    gold=[json.loads(line) for line in (inputs/'gsm8k_test1319.jsonl').read_text().split('\n') if line]
    if [x['problem_id'] for x in prompts] != [x['problem_id'] for x in gold]:
        raise ValueError('Gold/prompt identities differ')
    reference=read(inputs/'HF_REFERENCE_OUTCOMES.json')
    tok=AutoTokenizer.from_pretrained(args.tokenizer,local_files_only=True)
    vocab=set(tok.get_vocab().values())  # Exactly once, on CPU, never per token.
    special=tuple(tok.all_special_ids)
    for name, record in spec['tokenizer_files'].items():
        if sha(Path(args.tokenizer)/name) != record['sha256']:
            raise ValueError('CPU reference tokenizer bytes changed')
    scores={}; summaries={}
    for role in ROLES:
        env=read(root/role/'environment.json')
        if env['requested_engine'] != engine_kwargs():
            raise ValueError('Requested high-throughput engine drift')
        validate_observed_engine(env['actual_engine'])
        actual={}; stops=Counter(); backend=Counter(); rows_out=[]
        files=sorted((root/role/'raw').glob('*.json'))
        if [p.name for p in files] != [f'{x:04d}.json' for x in range(0,1319,BATCH_SIZE)]:
            raise ValueError('Missing/extra raw batch')
        for offset,path in zip(range(0,1319,BATCH_SIZE),files):
            raw=raw_checked(prompts[offset:offset+BATCH_SIZE],read(path)); name=f'{role}_{offset:04d}'
            unit=ledger[prefix+run+'/unit/'+name]; done=ledger[prefix+run+'/done/'+name]
            if (unit != read(root/'intents'/f'{name}.json')
                    or done != read(root/'completed'/f'{name}.json')
                    or done['raw_sha256'] != sha(path)
                    or unit['problem_ids'] != [r['problem_id'] for r in prompts[offset:offset+BATCH_SIZE]]
                    or unit['prompt_sha256'] != digest(prompts[offset:offset+BATCH_SIZE])
                    or done['count'] != len(raw)):
                raise ValueError('Raw/journal lineage changed')
            for row,item in zip(gold[offset:offset+BATCH_SIZE],raw):
                if any(x not in vocab for x in item['token_ids']):
                    raise ValueError('Unknown token is technical unknown, never scored zero')
                event=first_stop(item['token_ids'],lambda ids:tok.decode(ids,
                    skip_special_tokens=False,clean_up_tokenization_spaces=False),
                    tok.eos_token_id,512,special)
                score=completion_score(row,event)
                actual[row['problem_id']]=score['task_answer_correct']
                stops[event['stop_reason']]+=1; backend[item['finish_reason']]+=1
                rows_out.append(dict(problem_id=row['problem_id'],stop=event,score=score))
        if len(actual)!=1319:
            raise ValueError('Incomplete endpoint')
        summaries[role]=dict(correct=sum(actual.values()),total=1319,
            logical_stops=dict(stops),backend_stops=dict(backend),technical_unknown=0,
            parity=parity(reference['outcomes'][role],actual))
        scores[role]=rows_out
    merge=read(root/'MERGE_PROOF.json')
    if (merge['reference_state_sha256'] != spec['reference_state_sha256']
            or merge['adapter_exact_copy'] is not True or merge['new_training_updates'] != 0
            or merge['merge_dtype'] != 'float32' or merge['saved_dtype'] != 'bfloat16'):
        raise ValueError('Correct reference checkpoint or frozen merge differs')
    result=dict(schema='p009_p0_fast_raw_oracle_v1',passed=True,summary=summaries,scored=scores,
        new_model_calls=0,old_reference_rescored=False,new_training_updates=0,
        fresh_outputs=2638,inherited_outputs=0,parent_status='failed',old_parent_raw_scored=False,
        artifact_digest=digest(envelope['artifact_manifest']),spec_sha256=digest(spec),
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    dump(args.out,result)
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('root','inputs','receipt','ledger','provider','app-id','admission','tokenizer','out'):
        parser.add_argument('--'+name,required=True)
    audit(parser.parse_args())
