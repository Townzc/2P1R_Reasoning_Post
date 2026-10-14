#!/usr/bin/env python3
"""Independent full logical P0 replay from failed-parent prefix + new suffix."""
import argparse
from collections import Counter
import datetime
import json
from pathlib import Path
from analyses.completion_contract import first_stop, completion_score
from experiments.sft_allocation_midpoint.common import dump, read, sha, digest, verify
from experiments.learning_regime_p009.gates import parity
from experiments.learning_regime_p009.p0_contract import ROLES, prompts_checked, raw_checked
from experiments.learning_regime_p009.p0_suffix_contract import (
    CAMPAIGN, RUN, PARENT_CAMPAIGN, PARENT_RUN, OFFSETS, check_parent, validate_release,
)


def audit(args):
    from transformers import AutoTokenizer
    from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
    spec = read(args.admission); original = spec['parent_spec']
    root = Path(args.root); inputs = Path(args.inputs); preserved = Path(args.parent_preservation)
    envelope = read(args.receipt); ledger = read(args.ledger); provider = read(args.provider)
    intent = read(root/'intent.json'); plan = intent['plan']
    if spec != intent['spec']:
        raise ValueError('Actual child specification differs')
    validate_release(spec, plan, intent['release'])
    pre = 'midpoint/'+CAMPAIGN+'/'; oldpre = 'midpoint/'+PARENT_CAMPAIGN+'/'
    terminal = ledger[pre+'terminal/'+RUN]; claim = ledger[pre+'claim/'+RUN]
    if (terminal != envelope['receipt'] or terminal['status'] != 'completed' or
            terminal['claim_sha256'] != digest(claim) or
            terminal['evidence_sha256'] != digest(envelope['artifact_manifest'])):
        raise ValueError('Original completed child receipt missing')
    verify(root, envelope['artifact_manifest']); verify(inputs, original['inputs'])
    if sha(preserved/'PRESERVED.json') != spec['parent_preservation_sha256']:
        raise ValueError('Original parent preservation changed')
    oldroot = preserved/'evidence'
    oldledger = {k:ledger[k] for k in spec['parent_ledger_keys']}
    proof = check_parent(spec, oldroot, oldledger, inputs)
    if read(root/'PARENT_PREFIX_PROOF.json') != proof:
        raise ValueError('Wrong inherited prefix')
    marker = read(root/'PARENT_CONTINUATION_MARKER.json')
    if (marker != ledger[oldpre+'continuation/'+PARENT_RUN] or
            marker['child_claim_sha256'] != digest(claim) or marker['spec_sha256'] != digest(spec) or
            marker['child_campaign'] != CAMPAIGN or marker['child_run'] != RUN):
        raise ValueError('Permanent cross-campaign suffix marker differs')
    apps = [spec['parent_app_id'], args.app_id]
    if (provider['app_ids'] != apps or provider['state'] != 'stopped' or
            provider['owned_container_ids'] != []):
        raise ValueError('Exact parent and child STOPPED0 required')
    validate_stopped_apps(apps, provider['original_app_info'], provider['owned_containers'])
    prompts = prompts_checked(read(inputs/'qwen_gsm_zero_parity.json'))
    gold = [json.loads(s) for s in (inputs/'gsm8k_test1319.jsonl').read_text().split('\n') if s]
    if [x['problem_id'] for x in prompts] != [x['problem_id'] for x in gold]:
        raise ValueError('Gold/prompt order differs')
    reference = read(inputs/'HF_REFERENCE_OUTCOMES.json')
    tok = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True)
    vocab = set(tok.get_vocab().values()); special = tuple(tok.all_special_ids)
    for name, record in original['tokenizer_files'].items():
        if sha(Path(args.tokenizer)/name) != record['sha256']:
            raise ValueError('CPU tokenizer bytes changed')
    summaries = {}; scores = {}; new_raw_count = inherited_count = 0
    for role in ROLES:
        names = {p.name for p in (root/role/'raw').glob('*.json')}
        if names != {f'{i:04d}.json' for i in range(OFFSETS[role],1319,32)}:
            raise ValueError('Missing/extra child raw batches or prefix regenerated')
        actual = {}; stops = Counter(); backend = Counter(); rows_out = []
        for offset in range(0,1319,32):
            inherited = offset < OFFSETS[role]
            source = oldroot if inherited else root
            source_pre, source_run = (oldpre,PARENT_RUN) if inherited else (pre,RUN)
            path = source/role/'raw'/f'{offset:04d}.json'
            raw = raw_checked(prompts[offset:offset+32],read(path)); name = f'{role}_{offset:04d}'
            unit = ledger[source_pre+source_run+'/unit/'+name]
            done = ledger[source_pre+source_run+'/done/'+name]
            if (unit != read(source/'intents'/f'{name}.json') or
                    done != read(source/'completed'/f'{name}.json') or
                    done['raw_sha256'] != sha(path) or done['count'] != len(raw) or
                    unit['problem_ids'] != [x['problem_id'] for x in prompts[offset:offset+32]] or
                    unit['prompt_sha256'] != digest(prompts[offset:offset+32])):
                raise ValueError('Raw source/unit/done identity differs')
            inherited_count += len(raw) if inherited else 0
            new_raw_count += 0 if inherited else len(raw)
            for row,item in zip(gold[offset:offset+32],raw):
                if any(x not in vocab for x in item['token_ids']):
                    raise ValueError('Unknown token is not scored zero')
                event = first_stop(item['token_ids'], lambda ids:tok.decode(ids,
                    skip_special_tokens=False,clean_up_tokenization_spaces=False),
                    tok.eos_token_id,512,special)
                score = completion_score(row,event)
                actual[row['problem_id']] = score['task_answer_correct']
                stops[event['stop_reason']] += 1; backend[item['finish_reason']] += 1
                rows_out.append(dict(problem_id=row['problem_id'],source_campaign=(
                    PARENT_CAMPAIGN if inherited else CAMPAIGN),stop=event,score=score))
        if len(actual) != 1319:
            raise ValueError('Incomplete logical endpoint')
        summaries[role] = dict(correct=sum(actual.values()),total=1319,logical_stops=dict(stops),
            backend_stops=dict(backend),technical_unknown=0,parity=parity(reference['outcomes'][role],actual))
        scores[role] = rows_out
    if inherited_count != 128 or new_raw_count != 2510:
        raise ValueError('Physical versus inherited output count differs')
    if read(root/'MERGE_PROOF.json')['reference_state_sha256'] != original['reference_state_sha256']:
        raise ValueError('Wrong original correct-969 checkpoint')
    dump(args.out,dict(schema='p009_p0_full_parent_suffix_oracle_v1',passed=True,
        summary=summaries,scored=scores,parent_status='failed',new_raw_count=new_raw_count,
        inherited_raw_count=inherited_count,old_reference_rescored=False,new_model_calls=0,
        new_training_updates=0,original_timing_gate_failed=True,
        artifact_digest=digest(envelope['artifact_manifest']),spec_sha256=digest(spec),
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    print(json.dumps(summaries,indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('root','inputs','receipt','ledger','provider','app-id','admission',
                 'tokenizer','parent-preservation','out'):
        p.add_argument('--'+name,required=True)
    audit(p.parse_args())
