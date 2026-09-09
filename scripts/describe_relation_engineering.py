"""Reproduce E011 post-hoc CPU descriptions; no scoring changes or model calls."""
import argparse
from collections import Counter
import math
from pathlib import Path

from scripts.audit_family_matching import verified_tokenizer
from scripts.verify_relation_cpu_audit import load_archive
from src.relation_engineering import dump
from src.relation_verifier import STEP, parse_prompt
from src.sft_data import prefix, read_jsonl, sha256_file


def describe_lines(rows):
    after = Counter(); grounded = correct = invalid_edges = parsed = 0
    emitted_steps = Counter()
    for row in rows:
        q = parse_prompt(row['prompt']); edges = {e['id']: e for e in q['edges']}; n = 0
        for line in row['text'].strip(' \t\r\n').splitlines():
            match = STEP.fullmatch(line)
            if not match:
                continue
            eid, u, a, v, b = map(int, match.groups())
            after[str(b)] += 1; parsed += 1; n += 1
            edge = edges.get(eid)
            if not edge or (u, v) not in ((edge['u'], edge['v']), (edge['v'], edge['u'])):
                invalid_edges += 1
                continue
            grounded += 1
            correct += edge['table'][a] == b if (u, v) == (edge['u'], edge['v']) else edge['table'][b] == a
        emitted_steps[str(n)] += 1
    return {'outputs': len(rows), 'syntactically_parseable_step_lines': parsed,
            'emitted_after_state_counts': dict(after), 'edge_and_endpoints_exist_lines': grounded,
            'locally_correct_table_lookup_lines': correct, 'invalid_edge_or_endpoints_lines': invalid_edges,
            'parseable_step_count_histogram': dict(emitted_steps),
            **{k: sum(r['score'][k] for r in rows) for k in ('complete_correct', 'answer_correct', 'truncated')}}


def describe(run, data, tokenizer, revision):
    train = read_jsonl(run/'final_train.jsonl'); dev = read_jsonl(run/'final_dev.jsonl')
    base = read_jsonl(run/'base_dev_clean.jsonl')
    by = {v: [r for r in dev if r['view'] == v] for v in ('clean', 'useful_delete', 'irrelevant_delete')}
    paired = {}
    comparisons = [('base_clean', 'final_clean', base, by['clean']),
                   ('clean', 'useful_delete', by['clean'], by['useful_delete']),
                   ('clean', 'irrelevant_delete', by['clean'], by['irrelevant_delete'])]
    for left, right, lrows, rrows in comparisons:
        if [r['problem_id'] for r in lrows] != [r['problem_id'] for r in rrows]:
            raise ValueError('Parent identities/order differ')
        for metric in ('answer_correct', 'complete_correct'):
            counts = Counter('both' if a['score'][metric] and b['score'][metric]
                             else 'left_only' if a['score'][metric]
                             else 'right_only' if b['score'][metric] else 'neither'
                             for a, b in zip(lrows, rrows))
            paired[left+'_vs_'+right+'_'+metric] = {k: counts[k] for k in ('both', 'left_only', 'right_only', 'neither')}
    worlds = load_archive(data/'worlds.json')[:32]
    if [w['world_id'] for w in worlds] != [r['problem_id'] for r in train]:
        raise ValueError('Training world identities differ')
    gold = Counter(str(int(STEP.fullmatch(line).groups()[-1])) for w in worlds
                   for text in w['responses'] for line in text.splitlines()[:-1])
    failure = {
        'scope': 'Post-hoc CPU description of existing frozen outputs; no new model calls, hypothesis tests, altered scores or causal allocation claim.',
        'methods': 'Count exact STEP-regex lines; a local lookup is assessed only when its cited edge and oriented endpoints exist. Local correctness does not establish source-to-target continuity, global answer correctness or EOS. Report all outputs and keep malformed/truncated cases.',
        'source_inputs_sha256': {p.name: sha256_file(p) for p in [run/'base_dev_clean.jsonl', run/'final_train.jsonl', run/'final_dev.jsonl']},
        'final_train': describe_lines(train), 'base_clean': describe_lines(base),
        'dev_by_view': {k: describe_lines(v) for k, v in by.items()},
        'gold_train_after_states_once_per_reference': dict(gold), 'paired_parent_counts': paired,
        'equal_route_reference_entropy_nll_lower_bound': math.log(4)/101,
        'entropy_bound_scope': 'Ideal teacher-forced mean NLL for four equally weighted distinct references with 101 supervised tokens each; not a measured model quantity.'}
    counts = []
    for world in worlds:
        for response in world['responses']:
            pre = prefix(world['prompt']); start = len(pre); count = 0
            offsets = tokenizer(pre+response, add_special_tokens=False, return_offsets_mapping=True)['offset_mapping']
            for line in response.splitlines()[:-1]:
                match = STEP.fullmatch(line); a, b = match.span(5); span = (start+a, start+b)
                if [(u,v) for u,v in offsets if u<span[1] and v>span[0]] != [span]:
                    raise ValueError('After-state value is not exactly one token')
                count += 1; start += len(line)+1
            if count != 4:
                raise ValueError('Reference does not have four state transitions')
            counts.append(count)
    inventory = {
        'scope': 'Post-hoc static reference-token inventory; no model calls or measured per-field loss.',
        'train_worlds': 32, 'references': len(counts), 'supervised_tokens_once_per_reference': len(counts)*101,
        'after_state_value_tokens_once_per_reference': sum(counts), 'fraction': sum(counts)/(len(counts)*101),
        'method': 'STEP group5 character spans mapped into the exact full prompt+response tokenizer offsets; each of four after-state values must occupy exactly one token. Supervised denominator includes EOS.',
        'data_manifest_sha256': sha256_file(data/'manifest.json'), 'tokenizer_revision': revision,
        'interpretation_limit': 'Remaining tokens include selected node/edge IDs as well as fixed syntax and EOS; they are not all trivial. This inventory alone does not identify the cause of the state collapse or measure field-specific model NLL.'}
    return failure, inventory


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', default='runs/relation_overfit_e011_r1')
    p.add_argument('--data-dir', default='runs/relation_engineering_c015_r1')
    p.add_argument('--tokenizer-dir', required=True)
    p.add_argument('--out-dir', required=True)
    a = p.parse_args(); output = Path(a.out_dir)
    if output.exists():
        raise FileExistsError('Immutable description output exists')
    tokenizer, metadata = verified_tokenizer(Path(a.tokenizer_dir))
    failure, inventory = describe(Path(a.run_dir), Path(a.data_dir), tokenizer, metadata['revision'])
    output.mkdir(parents=True, exist_ok=False)
    dump(output/'failure_analysis.json', failure)
    dump(output/'semantic_token_inventory.json', inventory)


if __name__ == '__main__':
    main()
