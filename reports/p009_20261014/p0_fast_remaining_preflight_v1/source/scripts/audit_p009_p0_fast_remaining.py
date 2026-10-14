"""First full2638 logical replay from immutable saved256 + new2382; no generation."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from analyses.completion_contract import first_stop, completion_score
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, verify
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
from experiments.learning_regime_p009.gates import parity
from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs, validate_observed_engine
from experiments.learning_regime_p009.p0_fast_remaining_contract import (
    CAMPAIGN, RUN, PARENT_CAMPAIGN, PARENT_RUN, ROLES, OFFSETS, BATCH_SIZE,
    validate_release, check_parent, prompts_checked, raw_checked, remaining_forecast,
)


def audit(args):
    from transformers import AutoTokenizer
    spec = read(args.admission); original = spec['parent_spec']
    root = Path(args.root); inputs = Path(args.inputs); preserved = Path(args.parent_preservation)
    envelope = read(args.receipt); ledger = read(args.ledger); provider = read(args.provider)
    intent = read(root/'intent.json'); pre = 'midpoint/'+CAMPAIGN+'/'
    oldpre = 'midpoint/'+PARENT_CAMPAIGN+'/'
    if intent['spec'] != spec:
        raise ValueError('Actual exact suffix spec differs')
    validate_release(spec, intent['plan'], intent['release'])
    for name, expected in spec['source_files'].items():
        if sha(name) != expected:
            raise ValueError('Reviewed source drift')
    claim = ledger[pre+'claim/'+RUN]; terminal = ledger[pre+'terminal/'+RUN]
    if (terminal != envelope['receipt'] or terminal['status'] != 'completed'
            or terminal['claim_sha256'] != digest(claim)
            or terminal['evidence_sha256'] != digest(envelope['artifact_manifest'])):
        raise ValueError('Original completed child claim/terminal missing')
    verify(root, envelope['artifact_manifest']); verify(inputs, original['inputs'])
    if sha(preserved/'PRESERVED.json') != spec['parent_preservation_sha256']:
        raise ValueError('Original failed-parent preservation differs')
    oldroot = preserved/'evidence'
    proof = check_parent(spec, oldroot, {k:ledger[k] for k in spec['parent_ledger_keys']}, inputs)
    if read(root/'PARENT_PREFIX_PROOF.json') != proof:
        raise ValueError('Original unacknowledged raw prefix differs')
    marker = dict(child_campaign=CAMPAIGN, child_run=RUN, child_claim_sha256=digest(claim),
        spec_sha256=digest(spec), parent_terminal=spec['parent_terminal'],
        inherited_outputs=256, suffix_outputs=2382, parent_stays_failed=True)
    if (read(root/'PARENT_CONTINUATION_MARKER.json') != marker
            or ledger[oldpre+'continuation/'+PARENT_RUN] != marker):
        raise ValueError('Original once-only suffix marker differs')
    apps = [original['parent_app_id'], spec['parent_app_id'], args.app_id]
    if (provider['app_ids'] != apps or provider['state'] != 'stopped'
            or provider['owned_container_ids']):
        raise ValueError('All three exact apps must be STOPPED0')
    validate_stopped_apps(apps, provider['original_app_info'], provider['owned_containers'])
    result = read(root/'result.json')
    if (result != envelope['result'] or result['suffix_outputs'] != 2382
            or result['inherited_outputs'] != 256 or result['total_logical_outputs'] != 2638
            or result['suffix_batches'] != 11 or result['new_training_updates'] != 0
            or result['parent_status'] != 'failed' or result['parent_proxy_is_completed_batch'] is not False
            or result['parent_raw_sha256'] != spec['parent_raw_sha256']
            or len(result['new_full_batch_seconds']) != 11 or len(result['forecasts']) != 11):
        raise ValueError('Actual complete suffix result/count/source differs')
    observations = [spec['parent_failed_batch_proxy_seconds']]+result['new_full_batch_seconds']
    for i, forecast in enumerate(result['forecasts']):
        replay = remaining_forecast(forecast['elapsed_worker_seconds'], observations[:i+1], 11-i)
        if (forecast != replay or forecast != read(root/'forecasts'/f'{i:03d}.json')
                or forecast['admitted'] is not True):
            raise ValueError('Every actual pre-batch forecast must replay with all observations')
    expected = {f'{role}_{offset:04d}' for role in ROLES
                for offset in range(OFFSETS[role],1319,BATCH_SIZE)}
    for kind in ('unit','done'):
        if {k.removeprefix(pre+RUN+'/'+kind+'/') for k in ledger
                if k.startswith(pre+RUN+'/'+kind+'/')} != expected:
            raise ValueError('Missing, duplicate, unknown or prefix-replayed attempt')
    if {p.stem for p in (root/'intents').glob('*.json')} != expected:
        raise ValueError('Original local journals differ')
    prompts = prompts_checked(read(inputs/'qwen_gsm_zero_parity.json'))
    gold = [json.loads(s) for s in (inputs/'gsm8k_test1319.jsonl').read_text().split('\n') if s]
    if [r['problem_id'] for r in prompts] != [r['problem_id'] for r in gold]:
        raise ValueError('Complete gold/prompt IDs differ')
    reference = read(inputs/'HF_REFERENCE_OUTCOMES.json')
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True)
    vocab = set(tokenizer.get_vocab().values()); special = tuple(tokenizer.all_special_ids)
    for name, record in original['tokenizer_files'].items():
        if sha(Path(args.tokenizer)/name) != record['sha256']:
            raise ValueError('Frozen tokenizer bytes changed')
    summaries = {}; scores = {}; inherited_count = new_count = 0
    for role in ROLES:
        env = read(root/role/'environment.json')
        if env['requested_engine'] != engine_kwargs():
            raise ValueError('New engine differs from inherited engine setting')
        validate_observed_engine(env['actual_engine'])
        if {p.name for p in (root/role/'raw').glob('*.json')} != {
                f'{i:04d}.json' for i in range(OFFSETS[role],1319,BATCH_SIZE)}:
            raise ValueError('Missing/extra raw or attempted prefix repeated')
        actual = {}; stops = Counter(); backend = Counter(); tie_count = 0; scored = []
        for offset in range(0,1319,BATCH_SIZE):
            inherited = offset < OFFSETS[role]
            source = oldroot if inherited else root
            source_pre, source_run = (oldpre,PARENT_RUN) if inherited else (pre,RUN)
            path = source/role/'raw'/f'{offset:04d}.json'
            part = prompts[offset:offset+BATCH_SIZE]; raw = raw_checked(part, read(path))
            name = f'{role}_{offset:04d}'; unit = ledger[source_pre+source_run+'/unit/'+name]
            if (unit != read(source/'intents'/f'{name}.json')
                    or unit['problem_ids'] != [r['problem_id'] for r in part]
                    or unit['prompt_sha256'] != digest(part)):
                raise ValueError('Exact original raw/attempt identity changed')
            if inherited:
                if source_pre+source_run+'/done/'+name in ledger or sha(path) != spec['parent_raw_sha256']:
                    raise ValueError('Never fabricate a missing parent acknowledgement')
                inherited_count += len(raw)
            else:
                done = ledger[source_pre+source_run+'/done/'+name]
                if (done != read(source/'completed'/f'{name}.json')
                        or done['raw_sha256'] != sha(path) or done['count'] != len(raw)
                        or done['problem_ids'] != unit['problem_ids']):
                    raise ValueError('Original child acknowledgement differs')
                new_count += len(raw)
            for row, item in zip(gold[offset:offset+BATCH_SIZE], raw):
                if any(x not in vocab for x in item['token_ids']):
                    raise ValueError('Unknown raw token cannot be scored zero')
                event = first_stop(item['token_ids'], lambda ids:tokenizer.decode(ids,
                    skip_special_tokens=False, clean_up_tokenization_spaces=False),
                    tokenizer.eos_token_id,512,special)
                score = completion_score(row,event)
                actual[row['problem_id']] = score['task_answer_correct']
                stops[event['stop_reason']] += 1; backend[item['finish_reason']] += 1
                tie_count += int(item['finish_reason']=='length' and item['token_ids'][-1]==151643)
                scored.append(dict(problem_id=row['problem_id'], source_campaign=(
                    PARENT_CAMPAIGN if inherited else CAMPAIGN), original_backend_finish=item['finish_reason'],
                    inherited_unacknowledged=inherited, stop=event, score=score))
        if len(actual) != 1319:
            raise ValueError('Incomplete logical endpoint')
        summaries[role] = dict(correct=sum(actual.values()),total=1319,logical_stops=dict(stops),
            backend_stops=dict(backend),native_eos_at_cap_metadata_ties=tie_count,
            technical_unknown=0,parity=parity(reference['outcomes'][role],actual))
        scores[role] = scored
    merge = read(root/'MERGE_PROOF.json')
    if (inherited_count != 256 or new_count != 2382
            or merge['reference_state_sha256'] != original['reference_state_sha256']
            or merge['adapter_exact_copy'] is not True or merge['new_training_updates'] != 0
            or merge['merge_dtype'] != 'float32' or merge['saved_dtype'] != 'bfloat16'):
        raise ValueError('Inherited/new dose or original checkpoint merge differs')
    dump(args.out,dict(schema='p009_p0_fast_remainder_full_oracle_v1',passed=True,
        summary=summaries,scored=scores,new_raw_count=new_count,inherited_raw_count=inherited_count,
        parent_status='failed',parent_acknowledgement_fabricated=False,old_eager_raw_scored=False,
        old_reference_rescored=False,new_model_calls=0,new_training_updates=0,
        artifact_digest=digest(envelope['artifact_manifest']),spec_sha256=digest(spec),
        utc=datetime.now(timezone.utc).isoformat()))
    print(json.dumps(summaries,indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('root','inputs','receipt','ledger','provider','app-id','admission',
                 'tokenizer','parent-preservation','out'):
        p.add_argument('--'+name, required=True)
    audit(p.parse_args())
