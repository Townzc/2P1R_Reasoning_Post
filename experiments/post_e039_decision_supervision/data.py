"""Immutable continuation rows, first-decision masks, and outcome-blind subsets."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import json
from pathlib import Path

from experiments.post_e037_goal_training import data as previous
from experiments.post_e036_goal_probe import data as arithmetic
from experiments.thursday_probe.common import path_record, response, verify_manifest
from experiments.thursday_probe_v2.config import learning_rates
from src.countdown_smoke import safe_parse
from src.sft_data import read_jsonl, sha256_file, encode_row, budget_report, prefix
from .decision_spans import annotate, validate_mask

ROOT = Path('experiments/post_e039_decision_supervision')
RELEASE = ROOT / 'release_v1'
PRIOR = previous.RELEASE
PRIOR_MANIFEST_SHA = 'ca97959cac646eb709d428bede41e6aacc35ee7362b5fe01ddfa95e28d2e5536'
SEEDS = dict(data=2026091711, selection=2026091712, evaluation=2026091713,
             bootstrap=2026091714, training=17)
ROLES = ('S-U', 'S-D', 'P-U', 'P-D')
PARENT_RUNS = {'single':'goal_train_e038_r1', 'paired':'goal_train_e039_r1'}
PARENT_HASHES = {'single':'92da3a11e65e0de78012b6ab38d117554faa929f700dd95ed3f2df3c611fc5ae',
                 'paired':'a97f622c76c5817f8f283aa2f0034e19d438e8dd0bbb91026d443f3ba2f23bba'}
digest = arithmetic.digest
dump = arithmetic.dump
write_rows = arithmetic.write_rows


def _order(records, label, identity):
    return sorted(records, key=lambda r:(digest(dict(seed=SEEDS['selection'], label=label,
                                                  identity=identity(r))), identity(r)))


def protected_identities():
    excluded, audit = previous.protected_identities()
    manifest = verify_manifest(PRIOR)
    if sha256_file(PRIOR/'manifest.json') != PRIOR_MANIFEST_SHA:
        raise ValueError('Frozen E038/E039 release identity changed')
    sources = {}
    for name, count in [('train_groups',256), ('eval_groups',48)]:
        rows = read_jsonl(PRIOR/(name+'.jsonl'))
        identities = {tuple(sorted(r['numbers'])) for r in rows}
        if len(identities) != count:
            raise ValueError('Prior identity set is incomplete')
        excluded.update(identities)
        sources[name] = dict(groups=count, sha256=manifest['files_sha256'][name+'.jsonl'])
    audit = copy.deepcopy(audit)
    audit.update(E038_E039_original_groups=sources, prior_release_manifest_sha256=PRIOR_MANIFEST_SHA,
                 excluded_number_multisets=len(excluded), reserved_question_contents_read=False,
                 scope='All previously released training/development/calibration/diagnostic number identities plus published sealed allocation identities; no sealed question bodies.')
    return excluded, audit


def select_h_groups(groups):
    """32 groups over all24 pair/position/anchor strata; eight fixed extras.

    Base quota1 in every stratum. Four cross-pairs receive one extra for each
    position; a fixed four-cycle orientation balances each anchor/position at4.
    The other two pairs have4 groups; four cross-pairs have6 groups. H8 selects
    one hash-ranked member per anchor/position within the fixed H32.
    """
    quotas = {}; selected = []
    for pair in previous.PAIRS:
        for position in ('root','internal'):
            for anchor in pair:
                n = 1 + int(previous.ODD_EXTRA.get(pair) == anchor)
                key = '|'.join((*pair,position,anchor)); quotas[key] = n
                candidates = [g for g in groups if tuple(g['operator_pair']) == pair and
                              g['hole_position'] == position and g['anchor_operator'] == anchor]
                if len(candidates) < n: raise ValueError('Insufficient H diagnostic stratum')
                selected.extend(_order(candidates, 'H32/'+key, lambda g:g['group_id'])[:n])
    midpoint = []
    for operator in previous.OPS:
        for position in ('root','internal'):
            candidates = [g for g in selected if g['anchor_operator'] == operator and g['hole_position'] == position]
            midpoint.extend(_order(candidates, 'H8/'+operator+'/'+position, lambda g:g['group_id'])[:1])
    selected.sort(key=lambda g:g['group_id']); midpoint.sort(key=lambda g:g['group_id'])
    if len(selected) != 32 or len(midpoint) != 8 or len({g['group_id'] for g in selected}) != 32:
        raise ValueError('H subset count/identity mismatch')
    if Counter((g['anchor_operator'],g['hole_position']) for g in selected) != Counter({(o,p):4 for o in previous.OPS for p in ('root','internal')}):
        raise ValueError('H anchor/position diagnostic margin differs')
    return selected, midpoint, dict(H32_stratum_quotas=quotas,
        H32_pair_counts=dict(Counter(''.join(g['operator_pair']) for g in selected)),
        H32_position_counts=dict(Counter(g['hole_position'] for g in selected)),
        H32_group_ids=[g['group_id'] for g in selected], H8_group_ids=[g['group_id'] for g in midpoint],
        H8_rule='One pre-hashed H32 member per anchor operator and root/internal position',
        selection_uses_model_outputs=False)


def unique_f_prompts(rows, tokenizer):
    """Deduplicate the actual serialized prompt token sequence, never responses."""
    buckets = defaultdict(list)
    for index, row in enumerate(rows):
        ids = tuple(tokenizer(prefix(row['prompt']), add_special_tokens=False)['input_ids'])
        buckets[ids].append((index, row))
    result = []
    identities = []
    for ids, items in buckets.items():
        representative = items[0][1]
        if any((r['prompt'],r['numbers'],r['target'],r['problem_id']) !=
               (representative['prompt'],representative['numbers'],representative['target'],representative['problem_id'])
               for _,r in items):
            raise ValueError('Identical prompt tokens map to conflicting actual F identities')
        prompt_hash = digest(list(ids)); indices = [i for i,_ in items]
        row = copy.deepcopy(representative)
        row.update(interface='F', task='construct', group_id='decision_F_train_'+prompt_hash[:20],
            target_index=0, split='actual_F_replay_training_diagnostic',
            skeleton_family_id=digest(arithmetic.family(safe_parse(row['expression']))),
            prompt_token_sha256=prompt_hash, prompt_input_ids=list(ids),
            reference_responses=[r['response'] for _,r in items],
            source_training_row_indices={arm:[512+i for i in indices] for arm in ('single','paired')},
            source_F_row_indices=indices, source_training_row_sha256=[digest(r) for _,r in items],
            actual_F_replay_training_prompt=True, H_transfer_view=False)
        result.append(row)
        identities.append(dict(problem_id=row['problem_id'], prompt_token_sha256=prompt_hash,
            source_row_indices=indices, source_row_count=len(items),
            raw_prompt_sha256=digest(row['prompt']), unique_response_count=len(set(row['reference_responses']))))
    result.sort(key=lambda r:r['prompt_token_sha256'])
    end = _order(result,'F64',lambda r:r['prompt_token_sha256'])[:64]
    mid = _order(end,'F16',lambda r:r['prompt_token_sha256'])[:16]
    if len(end) != 64 or len(mid) != 16: raise ValueError('Actual F pool too small for prescribed diagnostics')
    return result, end, mid, dict(actual_F_source_rows=len(rows), unique_prompt_tokens=len(result),
        expected_unique_prompts=256, matches_expected_256=len(result)==256,
        source_rows_per_prompt=dict(Counter(str(len(v)) for v in buckets.values())),
        identities=sorted(identities,key=lambda r:r['prompt_token_sha256']),
        F64_problem_ids=[r['problem_id'] for r in end], F16_problem_ids=[r['problem_id'] for r in mid],
        grouping='Exact token IDs of Problem: + original prompt + Solution prefix; no BOS/chat template/EOS',
        original_prompt_strings_unchanged=True, actual_training_examples=True, outcome_blind=True)


def reference_rows(groups, interface, old_rows=None):
    result = previous.interface_rows(groups, interface)
    lookup = {arm:defaultdict(list) for arm in ('single','paired')}
    if old_rows:
        for arm in lookup:
            for index, row in enumerate(old_rows[arm][:512]):
                lookup[arm][row['problem_id']].append((index,row))
    for row in result:
        tree = safe_parse(row['expression'])
        row.update(path_record(tree), response=response(tree,0), rendering_id=0)
        refs = {arm:[dict(row_index=i,response=r['response'],row_sha256=digest(r),
                         rendering_id=r['rendering_id']) for i,r in lookup[arm].get(row['problem_id'],[])]
                for arm in lookup}
        row.update(training_references=refs,
            reference_responses=sorted({r['response'] for records in refs.values() for r in records}) or [row['response']],
            source_training_row_indices={arm:[r['row_index'] for r in records] for arm,records in refs.items()},
            reference_is_training_row=any(row['response']==r['response'] for records in refs.values() for r in records),
            diagnostic_reference_style=0)
    return result


def continuation_schedule():
    schedules = json.loads((PRIOR/'schedules.json').read_text())
    if schedules['single'] != schedules['paired']: raise ValueError('Prior schedules disagree')
    result = copy.deepcopy(schedules['single'][:128])
    validate_schedule(result)
    return result


def validate_schedule(schedule):
    if len(schedule) != 128: raise ValueError('Exactly128 continuation updates required')
    for batch in schedule:
        if len(batch) != 16 or len(set(batch)) != 16 or sum(0<=i<512 for i in batch) != 8 or sum(512<=i<1024 for i in batch) != 8:
            raise ValueError('Each continuation batch must be8 H and8 F')
    for start in (0,64):
        if sorted(i for b in schedule[start:start+64] for i in b) != list(range(1024)):
            raise ValueError('Each continuation epoch must present every source row once')


def _parents():
    records = {}
    for arm, run in PARENT_RUNS.items():
        folder = Path('runs/post_e037_goal_training_v1')/run
        final = json.loads((folder/'run_manifest_final.json').read_text())
        checkpoint = json.loads((folder/'checkpoint_256/checkpoint_identity.json').read_text())
        if final['status'] != 'completed' or final['completed_updates'] != 256 or final['final_adapter'] != checkpoint['parameter_digest'] or final['final_adapter']['sha256'] != PARENT_HASHES[arm]:
            raise ValueError('Registered continuation parent identity differs')
        records[arm] = dict(run_id=run, parent_experiment_id=final['experiment_id'],
            source_manifest=str(folder/'run_manifest_final.json'), source_manifest_sha256=sha256_file(folder/'run_manifest_final.json'),
            parent_checkpoint_step=256, parent_adapter=checkpoint['parameter_digest'],
            checkpoint_identity_sha256=sha256_file(folder/'checkpoint_256/checkpoint_identity.json'),
            original_checkpoint128_identity_sha256=sha256_file(folder/'checkpoint_128/checkpoint_identity.json'),
            original_training_identity_sha256=sha256_file(folder/'training_identity.json'))
    return records


def load_rows(interface, release=RELEASE, pool='eval'):
    names = {('F','eval'):'F', ('H','eval'):'H', ('F','train_all'):'F_train_all',
        ('F','endpoint64'):'F_train64', ('F','midpoint'):'F_train16',
        ('H','train32'):'H_train32', ('H','midpoint'):'H_train8'}
    if (interface,pool) not in names: raise ValueError('Unregistered interface/pool')
    return read_jsonl(Path(release)/(names[interface,pool]+'.jsonl'))


def load_inputs(release=RELEASE):
    release = Path(release); manifest = verify_manifest(release)
    result = {name:read_jsonl(release/(name+'.jsonl')) for name in
              ('single','paired','F','H','F_train_all','F_train64','F_train16','H_train32','H_train8')}
    h = read_jsonl(release/'DECISION_SPAN_AUDIT.jsonl'); f = read_jsonl(release/'F_SPAN_AUDIT.jsonl')
    result['spans'] = {arm:sorted([r for r in h if r['recipe']==arm],key=lambda r:r['row_index'])+f for arm in ('single','paired')}
    result['eval_H_spans'] = read_jsonl(release/'eval_H_spans.jsonl')
    result['train_H_spans'] = read_jsonl(release/'train_H_spans.jsonl')
    for name in ('schedules','learning_rates','dose'):
        result[name] = json.loads((release/(name+'.json')).read_text())
    result['manifest'] = manifest
    for schedule in result['schedules'].values(): validate_schedule(schedule)
    if result['schedules']['single'] != result['schedules']['paired'] or result['single'][512:] != result['paired'][512:]:
        raise ValueError('Frozen paired slots or common F replay differ')
    if any(len(result['spans'][arm]) != 1024 for arm in ('single','paired')):
        raise ValueError('Every unchanged source row needs a frozen span record')
    aliases = dict(eval_H='H',eval_F='F',train_H='H_train32',train_F='F_train_all',
                   train_F64='F_train64',midpoint_H='H_train8',midpoint_F='F_train16')
    result.update({alias:result[key] for alias,key in aliases.items()})
    result.update(spans_single=result['spans']['single'],spans_paired=result['spans']['paired'])
    return result


def load_span_rows(name, release=RELEASE):
    release=Path(release)
    if name in ('single','paired'):
        rows=read_jsonl(release/'DECISION_SPAN_AUDIT.jsonl')
        return sorted([r for r in rows if r['recipe']==name],key=lambda r:r['row_index'])+read_jsonl(release/'F_SPAN_AUDIT.jsonl')
    if name in ('eval_H','train_H'):
        return read_jsonl(release/('eval_H_spans.jsonl' if name=='eval_H' else 'train_H_spans.jsonl'))
    if name=='midpoint_H':
        ids={r['problem_id'] for r in load_rows('H',release,pool='midpoint')}
        return [r for r in load_span_rows('train_H',release) if r['problem_id'] in ids]
    if name=='train_F':
        all_f=read_jsonl(release/'F_SPAN_AUDIT.jsonl')
        return [all_f[r['source_F_row_indices'][0]] for r in load_rows('F',release,pool='train_all')]
    raise ValueError('Unknown frozen span pool')


def load_candidate_contexts(release=RELEASE, pool='eval'):
    names={'eval':'eval_H','train32':'train_H','midpoint':'midpoint_H'}
    if pool not in names: raise ValueError('Unknown decision context pool')
    rows=load_rows('H',release,pool=pool);spans={r['problem_id']:r for r in load_span_rows(names[pool],release)}
    fields=('problem_id','group_id','target_index','numbers','target','prompt','template',
            'hole_path','hole_position','skeleton_family_id','anchor_target_index','is_anchor',
            'single_target_supervised','paired_target_supervised')
    return [{**{key:row[key] for key in fields if key in row},**spans[row['problem_id']]} for row in rows]


def prepare(tokenizer_dir, output=RELEASE):
    output = Path(output)
    if output.exists(): raise FileExistsError('Never overwrite a frozen decision-supervision release')
    from scripts.audit_family_matching import verified_tokenizer
    tokenizer, tokenizer_identity = verified_tokenizer(Path(tokenizer_dir))
    old = previous.load_inputs(); parents = _parents()
    if sha256_file(PRIOR/'manifest.json') != PRIOR_MANIFEST_SHA: raise ValueError('Original data release changed')
    # Span feasibility is checked on ALL original H rows before building any new
    # intervention artifact. Failure leaves no published partial data release.
    spans = {}; encoded = {}; audit_h = []
    for arm in ('single','paired'):
        encoded[arm] = [encode_row(r,tokenizer,1024) for r in old[arm]]
        spans[arm] = [annotate(r,tokenizer) for r in old[arm][:512]]
        for index, record in enumerate(spans[arm]):
            validate_mask(encoded[arm][index],record)
            if record['status'] != 'valid_first_semantic_decision': raise ValueError('Intervention not implementable on every original H row')
            record.update(recipe=arm,row_index=index)
        audit_h.extend(spans[arm])
    f_spans = [annotate(r,tokenizer) for r in old['single'][512:]]
    for i,record in enumerate(f_spans):
        validate_mask(encoded['single'][512+i],record)
        if encoded['single'][512+i] != encoded['paired'][512+i]: raise ValueError('F encoded rows differ')
        record['source_F_row_index'] = i
    unique_f, f64, f16, f_audit = unique_f_prompts(old['single'][512:],tokenizer)
    groups = read_jsonl(PRIOR/'train_groups.jsonl')
    h32, h8, h_audit = select_h_groups(groups)
    excluded, leakage = protected_identities()
    new, selection = previous.make_groups(excluded,quotas=previous.EVAL_QUOTAS,
                                           pool='decision_eval',seed=SEEDS['data'])
    for i,g in enumerate(new): g['group_id'] = f'decision_v1_eval_g{i:03d}'
    new = previous.assign(new,seed=SEEDS['selection'],pool='decision_eval')
    previous.validate_groups(new,previous.EVAL_QUOTAS)
    new_ids = {tuple(sorted(g['numbers'])) for g in new}
    if len(new_ids) != 48 or new_ids & excluded: raise ValueError('New evaluation identities overlap prior exposure')
    eval_rows = {interface:reference_rows(new,interface) for interface in ('F','H')}
    h_train = reference_rows(h32,'H',old); h_mid = reference_rows(h8,'H',old)
    eval_spans = [annotate(row,tokenizer) for row in eval_rows['H']]
    train_spans = [annotate(row,tokenizer) for row in h_train]
    for row in eval_rows['F']+eval_rows['H']+unique_f+h_train:
        if len(tokenizer(prefix(row['prompt']),add_special_tokens=False)['input_ids'])+512>1024:
            raise ValueError('Frozen evaluation prompt plus512 token generation exceeds model context contract')
    schedule = continuation_schedule(); schedules = {arm:schedule for arm in ('single','paired')}
    lrs = learning_rates(128); dose = {}
    for arm in ('single','paired'):
        e = encoded[arm]; span = spans[arm]+f_spans
        tokens = budget_report(e,schedule,1)
        weighted = 0.; decisions = 0
        for batch in schedule:
            for index in batch:
                length=e[index]['n_supervised']; k=sum(span[index]['decision_mask'])
                if index < 512:
                    if k <= 0: raise ValueError('H decision mask missing')
                    a=length/(length+4*k); mass=k*5*a+(length-k)*a
                    if abs(mass-length)>1e-10: raise ValueError('H per-record weight mass changed')
                    weighted += mass; decisions += k
                else:
                    if k: raise ValueError('F tokens must not be decision upweighted')
                    weighted += length
        dose[arm] = dict(**tokens, encoded_sha256=digest(e), encoded_rows_sha256=digest([digest(r) for r in e]),
            encoded_row_sha256=[digest(r) for r in e], span_records_sha256=digest(span),
            mask_sha256=digest([r['decision_mask'] for r in span]),
            decision_tokens_presented=decisions, normalized_weight_mass=weighted,
            raw_supervised_denominator=tokens['supervised_response_tokens'], F_weights_unchanged=True,
            lambda_multiplier=5., objective_only_changes_H_supervision_distribution=True,
            gradient_norm_or_direction_equal_claimed=False)
    planned = 2*len(unique_f)+128+3456+512+128
    if planned > 5000: raise ValueError(f'Actual unique F pool requires{planned} generations, exceeding5000 by{planned-5000}; report before execution')
    leakage.update(new_eval_groups=48,new_eval_overlap=0,new_number_group_hashes=[g['number_group_hash'] for g in new],
                   previous_H_groups_excluded=256,previous_eval_groups_excluded=48,no_new_training_rows=True)
    span_summary = {arm:dict(rows=512, valid=512,
        span_types=dict(Counter(s['span_type'] for s in spans[arm])),
        token_lengths=dict(Counter(str(s['decision_token_count']) for s in spans[arm])),
        style_counts=dict(Counter(str(s['rendering_id']) for s in spans[arm])),
        operator_counts=dict(Counter(s['correct_operator'] for s in spans[arm])),
        root_internal_counts=dict(Counter('internal' if s['hole_path'] else 'root' for s in spans[arm])),
        earliest_response_character_min=min(s['response_char_span'][0] for s in spans[arm]),
        earliest_response_character_max=max(s['response_char_span'][0] for s in spans[arm]),
        earlier_leakage_rows=0,multi_token_rows=sum(s['multi_token'] for s in spans[arm])) for arm in ('single','paired')}
    audit = dict(status='all_original_H_rows_first_semantic_decision_valid',intervention_implementable=True,
        H_span_summary=span_summary, F_unique_prompt_audit=f_audit,H_selection=h_audit,new_eval_selection=selection,
        diagnostic_reference='New H and diagnostic H use the same existing style0 renderer; original per-recipe training references remain separately recorded.',
        mask_rule='First unknown-hole-dependent semantic atom in exact postorder renderer; four counterfactual operation prefixes must have identical preceding tokens.',
        no_response_editing=True, no_model_outputs_used=True, scientific_references_not_selected_by_loss=True)
    continuation = dict(phase='post_e039_decision_supervision_v1',parents=parents,
        roles=[dict(role=role,data='single' if role.startswith('S') else 'paired',
                    objective='ordinary_response_CE' if role.endswith('U') else 'first_decision_span_weighted_CE',
                    parent=parents['single' if role.startswith('S') else 'paired'],
                    updates=128,optimizer_reset=True,scheduler_reset=True) for role in ROLES],
        learning_rates_sha256=digest(lrs),schedules_sha256={k:digest(v) for k,v in schedules.items()},
        training_seed=17,epochs=2,H_per_update=8,F_per_update=8,effective_batch_size=16,microbatch=1,
        lambda_multiplier=5.,scientific_checkpoint_steps=[64,128],formal_endpoint=128,
        prior_training_data_sha256={a:sha256_file(PRIOR/(a+'.jsonl')) for a in ('single','paired')},
        optimizer_recipe='AdamW(.9,.999,1e-8,weight_decay0,foreachFalse), clip1; FP32 parameters/BF16 autocast/SDPA/TF32off',
        maximum_generations=5000,planned_generations=planned,maximum_forward_sequence_equivalents=16384,
        whole_powered_seconds_cap=14400,rental_cost_cny_cap=40,source_training_rows_unchanged=True)
    output.mkdir(parents=True)
    for name in ('single','paired','shared_F'):
        with (output/(name+'.jsonl')).open('xb') as stream: stream.write((PRIOR/(name+'.jsonl')).read_bytes())
    files = dict(F=eval_rows['F'],H=eval_rows['H'],F_train_all=unique_f,F_train64=f64,F_train16=f16,
                 H_train32=h_train,H_train8=h_mid,eval_groups=new,
                 DECISION_SPAN_AUDIT=audit_h,F_SPAN_AUDIT=f_spans,eval_H_spans=eval_spans,train_H_spans=train_spans)
    for name, rows in files.items(): write_rows(output/(name+'.jsonl'),rows)
    for name, record in [('schedules',schedules),('learning_rates',lrs),('dose',dose),('DATA_AUDIT',audit),
                         ('LEAKAGE_AUDIT',leakage),('CONTINUATION_MANIFEST',continuation)]:
        dump(output/(name+'.json'),record)
    manifest = dict(status='FROZEN_CPU_ONLY_BEFORE_NEW_MODEL_OUTPUTS',phase=continuation['phase'],seeds=SEEDS,
        prior_release_manifest_sha256=PRIOR_MANIFEST_SHA,parents=parents,training_rows={'single':1024,'paired':1024},
        original_H_rows_per_recipe=512,shared_F_rows=512,actual_unique_F_training_prompts=len(unique_f),
        evaluation_groups=48,evaluation_rows={'F':96,'H':96},H_training_diagnostic_groups=32,H_midpoint_groups=8,
        F_endpoint_questions=64,F_midpoint_questions=16,planned_generations=planned,generation_cap=5000,
        forward_sequence_equivalents_cap=16384,updates_per_arm=128,total_updates=512,intervention_implementable=True,
        tokenizer=tokenizer_identity,first_decision_span_rule=audit['mask_rule'],lambda_multiplier=5.,
        inherited_schedule='Exact first128 updates/two epochs of frozen prior shared seed17 schedule; not a continuation of its optimizer/LR state.',
        lr_recipe='Existing v2 learning_rates(128): peak5e-5, warmup8, cosine to1e-5.',
        source_files_sha256={str(p):sha256_file(p) for p in [Path(__file__).relative_to(Path.cwd()),
            ROOT/'decision_spans.py',Path(previous.__file__).relative_to(Path.cwd()),
            Path(arithmetic.__file__).relative_to(Path.cwd()),Path('src/sft_data.py'),Path('src/pilot_data.py'),
            Path('src/countdown_smoke.py'),Path('experiments/thursday_probe/common.py'),Path('experiments/thursday_probe_v2/config.py')]},
        files_sha256={p.name:sha256_file(p) for p in sorted(output.iterdir()) if p.is_file()},
        new_model_calls=0,new_training_performed=False,old_source_or_data_modified=False,no_reserved_contents_read=True,
        interpretation='Pre-frozen new numerical instances; exploratory, not structural OOD or training-seed confirmation. Loss weighting preserves scalar token mass, not gradients or effective learning rate.')
    dump(output/'manifest.json',manifest)
    return manifest


def main():
    p=argparse.ArgumentParser();p.add_argument('--tokenizer-dir',required=True);p.add_argument('--output',type=Path,default=RELEASE)
    args=p.parse_args();print(json.dumps(prepare(args.tokenizer_dir,args.output),indent=2))


if __name__=='__main__':main()
