"""Read-only failed-parent reconstruction. Never admits or dispatches a child.

Every physical intent must have its original raw return, scored file and done.
This deliberately implements the narrower zero-ambiguity recovery condition;
missing evidence is preserved and blocks this reconstruction, never regenerated.
"""
import argparse
from collections import defaultdict
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, verify
from experiments.sft_allocation_p008.main_binding import validate_binding
from experiments.sft_allocation_p008.contract import stable_seed
from experiments.sft_allocation_p008.procurement import Wallet
from experiments.sft_allocation_acquisition.contract import messages, completion, assess
from src.sft_data import read_jsonl


def reconcile(preservation, inputs, tokenizer, output):
    from transformers import AutoTokenizer
    src = Path(preservation); root = src/'evidence'; out = Path(output)
    if out.exists():
        raise ValueError('Existing reconciliation must be retained, not overwritten')
    saved = read(src/'PRESERVED.json')
    assert saved['preserved'] and not saved['repair_admitted']
    read_intent = read(src/'READ_INTENT.json')
    assert read_intent['run'] == 'pool_d2'
    assert not read_intent['owned_containers']
    assert all(x['state'] == 'stopped' for x in read_intent['provider'])
    db = read(src/'ledger.json'); camp = read_intent['campaign']; run = read_intent['run']
    prefix = 'midpoint/'+camp+'/'
    terminal = db[prefix+'terminal/'+run]
    assert terminal['status'] == 'failed' and terminal == saved['terminal']
    failure_manifest = read(root/'failure_manifest.json')
    assert digest(failure_manifest) == terminal['evidence_sha256']
    verify(root, failure_manifest)
    assert read(src/'REMOTE_LISTING_BEFORE.json') == read(src/'REMOTE_LISTING_AFTER.json')
    local_manifest = read(src/'LOCAL_MANIFEST.json'); verify(root, local_manifest)
    assert digest(local_manifest) == saved['manifest_sha256']
    sent = read(root/'intent.json'); config = sent['config']; spec = read(root/'admission.json')
    validate_binding(sent['plan'], config, sent['release'], spec)
    assert sent['plan']['campaign_id'] == camp and config['run_id'] == run and config['draw'] == 2
    claim = db[prefix+'claim/'+run]; bound = db[prefix+'intent/'+run]
    assert claim['intent_sha256'] == digest(bound) and claim['plan_sha256'] == digest(sent['plan'])
    assert terminal['claim_sha256'] == digest(claim)
    assert bound['source_sha256'] == digest(sent['release']['source_files'])
    assert bound['config_sha256'] == digest(config) and bound['data_sha256'] == config['input_sha256']
    assert sha(Path(inputs)/'manifest.json') == config['input_sha256']
    verify(inputs, read(Path(inputs)/'manifest.json')['files'])
    hardware = read(root/'environment.json')
    assert 'H100' in hardware['gpu'] and hardware['cuda'] == '12.8'
    assert hardware['versions'] == {'torch':'2.8.0','vllm':'0.11.0','transformers':'4.56.2','tokenizers':'0.22.1','numpy':'2.2.6'}
    failure = read(root/'failure.json')
    assert failure['error_type'] == 'TimeoutError' and failure['error'] == 'Finite P008 deadline'
    units = {}; dones = {}
    for kind, folder, dest in [('unit','intents',units),('done','completed',dones)]:
        remote = {k.split('/'+kind+'/',1)[1]:v for k,v in db.items() if k.startswith(prefix+run+'/'+kind+'/')}
        local = {p.stem:read(p) for p in (root/folder).glob('*.json')}
        assert local == remote, 'Local/remote journal disagreement; preserve, do not repair implicitly'
        dest.update(local)
    assert set(dones) <= set(units)
    parents = sorted(read_jsonl(Path(inputs)/'eligible_parents.jsonl'),key=lambda p:stable_seed('question_order',2,p['id']))
    assert len(parents) == 6973
    lookup = {p['id']:p for p in parents}; tok = AutoTokenizer.from_pretrained(tokenizer,local_files_only=True)
    prompts = {p['id']:tok.apply_chat_template(messages(p),tokenize=True,add_generation_prompt=True) for p in parents}
    lengths = {k:len(v) for k,v in prompts.items()}; frozen = read(root/'frozen_wallets.json')
    assert frozen['parent_order'] == list(lookup) and frozen['prompt_lengths'] == lengths
    physical = sorted(k for k in units if k.startswith('physical_batch_'))
    assert physical == [f'physical_batch_{i:05d}' for i in range(len(physical))]
    cache = {}; seen = defaultdict(dict); accepted = defaultdict(dict); attempts = defaultdict(int)
    returned = 0; seconds = 0
    for name in physical:
        assert name in dones, 'Unfinished physical intent: no ambiguous regeneration permitted'
        intent = units[name]; done = dones[name]
        assert intent['maximum_new_tokens'] == 1024
        raw_path = root/(name+'_raw.json'); scored_path = root/(name+'_scored.json')
        assert raw_path.exists() and scored_path.exists(), 'Original return/score absent'
        assert sha(raw_path) == done['raw_sha256'] and sha(scored_path) == done['scored_sha256']
        raw = read(raw_path); scored = read(scored_path); items = intent['items']
        assert len(items) == len(raw['outputs']) == len(scored) == done['count'] and 0 < len(items) <= 32
        assert raw['seconds'] == done['seconds'] and raw['seconds'] >= 0
        seconds += raw['seconds']
        for item,y,s in zip(items,raw['outputs'],scored):
            pid = item['problem_id']; cid = f"d2::{pid}::{item['attempt']}"
            assert item['draw'] == 2 and item['candidate_id'] == y['candidate_id'] == cid and cid not in cache
            assert item['attempt'] == attempts[pid]+1
            assert item['seed'] == stable_seed('teacher',2,pid,item['attempt'])
            assert y['prompt_token_ids'] == prompts[pid]
            stop = completion(y['token_ids']); text = tok.decode(stop['text_token_ids'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
            assert y['finish_reason'] == ('stop' if stop['eos'] else 'length')
            v = assess(lookup[pid],text,stop,seen[pid],accepted[pid])
            row = dict(**item,text=text,prompt_tokens=lengths[pid],completion_tokens=stop['token_count'],stop=stop,**v)
            assert row == s
            cache[cid] = row; attempts[pid] += 1; returned += stop['token_count']
            seen[pid].setdefault(v['normalized_text_sha256'],cid)
            if v['usable']:accepted[pid].setdefault(v['normalized_text_sha256'],cid)
    assert {p.name[:-9] for p in root.glob('physical_batch_*_raw.json')} == set(physical)
    assert {p.name[:-12] for p in root.glob('physical_batch_*_scored.json')} == set(physical)
    assert len(cache) <= config['max_physical_attempts'] == 16384 and returned <= 16384*1024
    states = {}; events = {}; requested = set(); expected_units = set(physical)
    for b in (1,8):
        for price in (0,4):
            for policy in ('breadth','depth'):
                w = Wallet(list(lookup),lengths,2,b,price,policy); names = sorted(k for k in units if k.startswith(w.name+'_batch_'))
                assert names == [w.name+f'_batch_{i:04d}' for i in range(len(names))]
                events[w.name] = []
                for i,name in enumerate(names):
                    intent = units[name]; assert w.propose() == intent; w.begin(intent)
                    ids = [f"d2::{x['problem_id']}::{x['attempt']}" for x in intent['action']['items']]
                    requested.update(ids); expected_units.add(name)
                    if name not in dones:
                        assert i == len(names)-1, 'Pending wallet followed by another intent'
                        events[w.name].append(dict(intent=intent,done=None))
                        break
                    assert all(cid in cache for cid in ids)
                    done = w.settle([cache[cid] for cid in ids]); assert done == dones[name]
                    events[w.name].append(dict(intent=intent,done=done))
                next_proposal = w.pending if w.pending is not None else w.propose()
                states[w.name] = dict(summary=w.summary(),published_pending=w.pending,next_proposal=next_proposal)
    assert expected_units == set(units), 'Unexplained unit in original journal'
    assert set(cache) <= requested, 'A physical output was not requested by a wallet'
    unresolved = sorted(requested-set(cache))
    # Unpublished physical requests may be a pending policy action. They were not
    # attempted; the child must retain the original action if any is admitted.
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'candidate_cache_reconstructed.json',cache)
    dump(out/'wallet_events_reconstructed.json',events)
    dump(out/'wallet_states_reconstructed.json',states)
    result = dict(passed=True,scope='failed_parent_preservation_and_prefix_replay_not_completion',
        parent_terminal=terminal,parent_claim=claim,parent_source_commit=sent['release']['commit'],
        parent_manifest_digest=digest(failure_manifest),preservation_manifest_sha256=sha(src/'LOCAL_MANIFEST.json'),
        physical_attempts=len(cache),physical_batches=len(physical),physical_raw_unknown=0,
        returned_tokens=returned,generation_seconds=seconds,all_raw_independently_redecoded=True,
        all_wallet_prefixes_replayed=True,unattempted_pending_candidate_ids=unresolved,
        pending_wallets=[k for k,v in states.items() if v['published_pending'] is not None],
        unfinished_wallets=[k for k,v in states.items() if v['next_proposal'] is not None],
        reconstructed_cache_sha256=sha(out/'candidate_cache_reconstructed.json'),
        reconstructed_events_sha256=sha(out/'wallet_events_reconstructed.json'),
        reconstructed_states_sha256=sha(out/'wallet_states_reconstructed.json'),
        new_model_calls=0,repair_admitted=False,student_admitted=False)
    dump(out/'RECONCILIATION.json',result)
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    for name in ('preservation','inputs','tokenizer','out'):p.add_argument('--'+name,required=True)
    a=p.parse_args();result=reconcile(a.preservation,a.inputs,a.tokenizer,a.out)
    print({k:v for k,v in result.items() if k not in ('parent_terminal','parent_claim','unattempted_pending_candidate_ids')})
