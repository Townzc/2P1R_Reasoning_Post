"""Frozen paired-goal SFT recipes, shared historical F replay, and new instances.

Only public released records/allocation identities are read. Construction,
assignment and diagnostics are frozen without inspecting model outcomes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
from fractions import Fraction
import itertools
import json
from pathlib import Path
import random

from experiments.post_e036_goal_probe import data as old
from experiments.thursday_probe.common import response, path_record, depth, verify_manifest
from experiments.thursday_probe_v2.config import learning_rates
from src.countdown_smoke import expression, safe_parse, value, verify_expression
from src.pilot_data import verify_row
from src.sft_data import read_jsonl, sha256_file, encode_row, budget_report, prefix
from src.trace_audit import audit_trace

ROOT = Path('experiments/post_e037_goal_training')
RELEASE = ROOT/'release_v1'
SEEDS = dict(data=2026091705, assignment=2026091706, training=17,
             evaluation=2026091707, bootstrap=2026091708)
OPS = old.OPS
PAIRS = tuple(itertools.combinations(OPS, 2))
TRAIN_QUOTAS = {p:44 if p in (('+','-'),('*','/')) else 42 for p in PAIRS}
EVAL_QUOTAS = {p:8 for p in PAIRS}
SURFACE = old.OLD_DATA/'surface.jsonl'
PREP = old.OLD_DATA/'prep_control.jsonl'
PARENT_MANIFEST = Path('runs/thursday_arithmetic_resume_r1/thu_v2_e031_r1/run_manifest_final.json')
ODD_EXTRA = {('+','*'):'+', ('-','*'):'*', ('-','/'):'-', ('+','/'):'/'}
digest = old.digest
dump = old.dump
write_rows = old.write_rows


def _rng(seed, label):
    return random.Random(int(digest(dict(seed=seed, substream=label)), 16))


def protected_identities():
    excluded, audit = old.protected_identities()
    prior_manifest = verify_manifest(old.RELEASE)
    prior = read_jsonl(old.RELEASE/'groups.jsonl')
    prior_numbers = {tuple(sorted(g['numbers'])) for g in prior}
    if len(prior_numbers) != 24:
        raise ValueError('Prior E037 identities are incomplete')
    excluded.update(prior_numbers)
    audit = copy.deepcopy(audit)
    audit.update(E037_number_groups_excluded=24,
                 E037_release_manifest_sha256=sha256_file(old.RELEASE/'manifest.json'),
                 E037_groups_sha256=prior_manifest['files_sha256']['groups.jsonl'],
                 excluded_number_multisets=len(excluded),
                 calibration_excluded_for_design_exposure_not_ancestry=True,
                 scope='Arithmetic number-multiset identities; published allocation protects sealed groups without opening their question bodies.')
    return excluded, audit


def make_groups(excluded=(), *, quotas=TRAIN_QUOTAS, pool='train', seed=SEEDS['data'], attempts_per_slot=100000):
    if set(quotas) != set(PAIRS) or any(type(n) is not int or n <= 0 or n % 2 for n in quotas.values()):
        raise ValueError('Positive even quotas for all six operator pairs required')
    rng = _rng(seed, 'construct/'+pool)
    forbidden = {tuple(sorted(g)) for g in excluded}
    groups, rejected, attempts = [], Counter(), 0
    for pair in PAIRS:
        for position in ('root','internal'):
            for slot in range(quotas[pair]//2):
                for _ in range(attempts_per_slot):
                    attempts += 1
                    numbers = rng.sample(range(1,41),4); key = tuple(sorted(numbers))
                    if key in forbidden:
                        rejected['protected_or_repeated_multiset'] += 1; continue
                    def build(shape):
                        return ('n',numbers[shape]) if isinstance(shape,int) else (rng.choice(OPS),build(shape[0]),build(shape[1]))
                    tree = build(rng.choice(old.SHAPES))
                    hole = () if position == 'root' else rng.choice(old.node_paths(tree)[1:])
                    skeleton = old.replace_op(tree,hole,'?')
                    trees = {op:old.replace_op(skeleton,hole,op) for op in OPS}
                    try:
                        values = {op:value(t) for op,t in trees.items()}
                        node = old.at(tree,hole); left,right = value(node[1]),value(node[2])
                    except ZeroDivisionError:
                        rejected['undefined_candidate'] += 1; continue
                    if any(old.degeneracy(op,left,right) for op in OPS):
                        rejected['hole_identity_or_absorbing'] += 1; continue
                    selected = [values[op] for op in pair]
                    if any(t.denominator != 1 or not 10 <= t <= 100 for t in selected):
                        rejected['target_domain'] += 1; continue
                    if selected[0] == selected[1] or any(sum(v==t for v in values.values()) != 1 for t in selected):
                        rejected['nonunique_target'] += 1; continue
                    group_id = f'goal_train_v1_{pool}_g{len(groups):03d}'
                    targets = [dict(target_index=i,target=int(values[op]),expected_operator=op,
                                    correct_operator=op,expression=expression(trees[op]),
                                    path_labels=old.path_labels(trees[op],hole)) for i,op in enumerate(pair)]
                    groups.append(dict(group_id=group_id,split='training' if pool=='train' else 'exploratory_development',
                        numbers=numbers,number_group_hash=digest(list(key)),template=expression(skeleton),
                        skeleton=expression(skeleton),skeleton_ast=skeleton,hole_path=list(hole),
                        hole_depth=len(hole),hole_position=position,skeleton_family=old.family(skeleton),
                        skeleton_family_id=digest(old.family(skeleton)),operator_pair=list(pair),targets=targets,
                        candidate_values={op:str(v) for op,v in values.items()}))
                    forbidden.add(key);break
                else:
                    raise RuntimeError(f'Finite construction exhausted: {pool}/{pair}/{position}/{slot}')
    validate_groups(groups,quotas)
    return groups,dict(seed=seed,substream='construct/'+pool,total_attempts=attempts,
        attempts_per_slot=attempts_per_slot,rejections=dict(rejected),group_count=len(groups),
        operator_pair_counts=dict(Counter(''.join(g['operator_pair']) for g in groups)),
        hole_position_counts=dict(Counter(g['hole_position'] for g in groups)),
        skeleton_families=len({g['skeleton_family_id'] for g in groups}),
        candidate_rule='All four candidates are finite; every local candidate excludes identity/absorbing operands. Selected two results are distinct unique integers10..100.',
        selection_uses_model_outputs=False,structural_ood_claim=False)


def validate_groups(groups, quotas=None):
    if quotas is not None and Counter(tuple(g['operator_pair']) for g in groups) != Counter(quotas):
        raise ValueError('Pair quota mismatch')
    if len({tuple(sorted(g['numbers'])) for g in groups}) != len(groups):
        raise ValueError('Repeated number multiset')
    for group in groups:
        if (len(group['numbers']) != 4 or len(set(group['numbers'])) != 4 or
                any(type(n) is not int or not 1 <= n <= 40 for n in group['numbers']) or
                group['template'].count('?') != 1 or len(group['targets']) != 2):
            raise ValueError('Invalid group/domain')
        if group['hole_position'] != ('internal' if group['hole_path'] else 'root'):
            raise ValueError('Incorrect hole position')
        values = {op:value(safe_parse(group['template'].replace('?',op))) for op in OPS}
        if group['candidate_values'] != {op:str(v) for op,v in values.items()}:
            raise ValueError('Candidate exact value mismatch')
        if {t['expected_operator'] for t in group['targets']} != set(group['operator_pair']):
            raise ValueError('Wrong operator pair')
        for target in group['targets']:
            op=target['expected_operator']; tree=safe_parse(target['expression']);node=old.at(tree,group['hole_path'])
            if (not verify_expression(target['expression'],group['numbers'],target['target']) or
                    tree != safe_parse(group['template'].replace('?',op)) or
                    not 10 <= target['target'] <= 100 or
                    [o for o in OPS if values[o]==target['target']] != [op]):
                raise ValueError('Reference/ordered AST/unique target mismatch')
            if any(old.degeneracy(o,value(node[1]),value(node[2])) for o in OPS):
                raise ValueError('Degenerate candidate hole')
        if len({t['target'] for t in group['targets']}) != 2:
            raise ValueError('Targets do not switch')
    if quotas is not None:
        for pair,count in quotas.items():
            for position in ('root','internal'):
                if sum(tuple(g['operator_pair'])==pair and g['hole_position']==position for g in groups) != count//2:
                    raise ValueError('Pair/position imbalance')


def assign(groups, *, seed=SEEDS['assignment'], pool='train'):
    """Independent balanced orientations for anchors, style0, and target_index0."""
    groups=copy.deepcopy(groups)
    for pair in PAIRS:
        for position in ('root','internal'):
            selected=[g for g in groups if tuple(g['operator_pair'])==pair and g['hole_position']==position]
            n=len(selected); first_count=n//2 + int(n%2 and ODD_EXTRA.get(pair)==pair[0])
            for label in ('anchor_operator','style0_operator','index0_operator'):
                order=list(selected);_rng(seed,f'{pool}/{label}/{pair}/{position}').shuffle(order)
                for index,group in enumerate(order):group[label]=pair[0] if index<first_count else pair[1]
    for group in groups:
        group['targets'].sort(key=lambda t:t['expected_operator'] != group['index0_operator'])
        for index,target in enumerate(group['targets']):target['target_index']=index
        group['anchor_target_index']=next(t['target_index'] for t in group['targets'] if t['expected_operator']==group['anchor_operator'])
    return groups


def interface_rows(groups, interface):
    rows=old.interface_rows(groups,interface)
    for row in rows:
        row['is_anchor']=row['target_index']==row['anchor_target_index']
        row['single_target_supervised']=row['is_anchor'] if row['split']=='training' else False
        row['paired_target_supervised']=row['split']=='training'
    return rows


def training_rows(groups, arm):
    if arm not in ('single','paired'):raise ValueError('Unknown training arm')
    rows=[]
    for group in groups:
        targets={t['expected_operator']:t for t in interface_rows([group],'H')}
        for style in (0,1):
            operator=(group['anchor_operator'] if arm=='single' else
                      group['style0_operator'] if style==0 else next(o for o in group['operator_pair'] if o!=group['style0_operator']))
            row=copy.deepcopy(targets[operator]);tree=safe_parse(row['expression'])
            row.update(path_record(tree),response=response(tree,style),rendering_id=style,slot=style,
                       recipe=arm,dataset_row_id=f"{group['group_id']}_{arm}_style{style}")
            verify_row(row)
            if audit_trace(row['response'],row['numbers'],row['target'])['complete_trace_status'] != 'verified':
                raise ValueError('Unverified exact supervised calculation')
            if '?' in row['response'] or row['response'].splitlines()[-1] != 'Answer: '+row['expression']:
                raise ValueError('Training answer must fill the entire ordered program')
            rows.append(row)
    return rows


def shared_surface():
    manifest=verify_manifest(old.OLD_DATA)
    raw=SURFACE.read_bytes();rows=read_jsonl(SURFACE)
    if len(rows)!=512 or sha256_file(SURFACE)!=manifest['files_sha256']['surface.jsonl']:
        raise ValueError('Exact historical512 Surface source is required')
    if len({tuple(sorted(r['numbers'])) for r in rows})!=256:
        raise ValueError('Historical Surface group support differs')
    for row in rows:verify_row(row)
    return raw,rows


def make_schedule(seed=SEEDS['training']):
    rng=random.Random(seed);schedule=[]
    for epoch in range(4):
        h=list(range(512));f=list(range(512,1024));rng.shuffle(h);rng.shuffle(f)
        for start in range(0,512,8):
            schedule.append([i for pair in zip(h[start:start+8],f[start:start+8]) for i in pair])
    validate_schedule(schedule)
    return schedule


def validate_schedule(schedule):
    if len(schedule)!=256:raise ValueError('Exactly256 updates required')
    for update in schedule:
        if len(update)!=16 or sum(0<=i<512 for i in update)!=8 or sum(512<=i<1024 for i in update)!=8:
            raise ValueError('Each update requires8H+8F')
    for epoch in range(4):
        if Counter(i for update in schedule[epoch*64:(epoch+1)*64] for i in update)!=Counter(range(1024)):
            raise ValueError('Every epoch must use every row slot exactly once')


def diagnostic_groups(training, evaluation):
    selected=[]
    for op in OPS:
        for position in ('root','internal'):
            candidates=[g for g in training if g['anchor_operator']==op and g['hole_position']==position]
            _rng(SEEDS['assignment'],f'train16/{op}/{position}').shuffle(candidates)
            selected.extend(candidates[:2])
    midpoint=[]
    for pair in PAIRS:
        for position in ('root','internal'):
            candidates=[g for g in evaluation if tuple(g['operator_pair'])==pair and g['hole_position']==position]
            _rng(SEEDS['assignment'],f'midpoint12/{pair}/{position}').shuffle(candidates)
            midpoint.append(candidates[0])
    if len({g['group_id'] for g in selected})!=16 or len({g['group_id'] for g in midpoint})!=12:
        raise ValueError('Stratified diagnostic selection failed')
    return selected,midpoint


def assignment_audit(groups):
    def counts(label):
        return {f'{op}/{position}':sum(g[label]==op and g['hole_position']==position for g in groups)
                for op in OPS for position in ('root','internal')}
    joint=Counter((g['anchor_operator'],g['hole_position'],g['style0_operator'],g['index0_operator']) for g in groups)
    return dict(seed=SEEDS['assignment'],anchor_operator_by_position=counts('anchor_operator'),
        style0_operator_by_position=counts('style0_operator'),index0_operator_by_position=counts('index0_operator'),
        anchor_is_smaller_target=sum(g['targets'][g['anchor_target_index']]['target']==min(t['target'] for t in g['targets']) for g in groups),
        numeric_target_order=dict(Counter('ascending' if g['targets'][0]['target']<g['targets'][1]['target'] else 'descending' for g in groups)),
        joint_anchor_position_style0_index0=[dict(anchor_operator=a,hole_position=p,style0_operator=s,index0_operator=i,groups=n) for (a,p,s,i),n in sorted(joint.items())],
        method='Separate hashed seed substreams shuffle each pair/position stratum. Odd counts use balanced cycle + to * to - to / to +. No target magnitude or model outcome enters assignment.',
        all_joint_cells_exactly_balanced=False)


def joint_distribution(rows,encoded):
    counts=Counter()
    for row,tokens in zip(rows,encoded):
        tree=safe_parse(row['expression']);vals=[value(old.at(tree,p)) for p in old.node_paths(tree)]
        fields=dict(operator=row.get('expected_operator','F_reference'),hole_position=row.get('hole_position','none'),
            style=row['rendering_id'],target=int(row['target']),target_digits=len(str(abs(int(row['target'])))),
            target_sign='positive' if row['target']>0 else 'zero' if row['target']==0 else 'negative',
            negative_intermediate=any(v<0 for v in vals),fractional_intermediate=any(v.denominator!=1 for v in vals),
            depth=depth(tree),hole_depth=row.get('hole_depth'),supervised_tokens=tokens['n_supervised'],
            processed_tokens=tokens['n_processed'],response_characters=len(row['response']))
        counts[json.dumps(fields,sort_keys=True)]+=1
    return [dict(**json.loads(key),rows=n) for key,n in sorted(counts.items())]


def source_support(h_rows,shared):
    prep=read_jsonl(PREP);parent=json.loads(PARENT_MANIFEST.read_text())
    if len(prep)!=256 or parent['identity']['data_sha256']!=sha256_file(PREP):
        raise ValueError('E031 ancestor source is not exact prep_control256')
    if (parent.get('parent')!='C0' or parent.get('experiment_id')!='E031' or
            parent.get('data')!='prep_control' or parent.get('status')!='completed' or parent.get('updates')!=32):
        raise ValueError('E031 parent lineage differs')
    scopes={'E031_actual_ancestor_prep_control':old.training_support(prep),
            'shared_future_F':old.training_support(shared)}
    for arm,rows in h_rows.items():
        scopes[arm+'_new_H']=old.training_support(rows)
        scopes[arm+'_actual_ancestor_plus_new_source_union']=old.training_support(prep+shared+rows)
    return dict(status='CPU_EXACT_SOURCE_SUPPORT_BEFORE_NEW_TRAINING',scopes=scopes,
        actual_ancestor_experiment='E031',actual_ancestor_source_rows=256,
        actual_ancestor_manifest_sha256=sha256_file(PARENT_MANIFEST),
        actual_ancestor_data_sha256=sha256_file(PREP),shared_future_F_sha256=sha256_file(SURFACE),
        E030_is_ancestor=False,E032_or_E033_to_E036_are_ancestors=False,
        union_definition='One source copy of actual E031 prep_control256 plus this arm H512 and identical future F512. Original C0 is untrained; E030 calibration is excluded from ancestry but retained in identity exclusions.',
        pretraining_support_claimed=False,no_reserved_contents_read=True)


def load_rows(interface, release=RELEASE, pool='eval'):
    if interface not in ('F','H','C') or pool not in ('eval','train16','midpoint12'):raise ValueError('Unknown row pool/interface')
    if pool=='train16' and interface=='C' or pool=='midpoint12' and interface!='H':raise ValueError('Unregistered diagnostic view')
    name=interface if pool=='eval' else 'train_'+interface if pool=='train16' else 'midpoint_H'
    return read_jsonl(Path(release)/(name+'.jsonl'))


def load_operator_rows(release=RELEASE):
    return read_jsonl(Path(release)/'operator_contexts.jsonl')


def load_inputs(release=RELEASE):
    release=Path(release);manifest=verify_manifest(release)
    result={key:read_jsonl(release/(key+'.jsonl')) for key in ('single','paired','F','H','C','midpoint_H','train_F','train_H')}
    result.update({key:json.loads((release/(key+'.json')).read_text()) for key in ('schedules','learning_rates','dose')})
    result['manifest']=manifest
    for schedule in result['schedules'].values():validate_schedule(schedule)
    if result['schedules']['single']!=result['schedules']['paired'] or result['single'][512:]!=result['paired'][512:]:
        raise ValueError('Shared macro slots or replay rows changed')
    return result


def prepare(tokenizer_dir, output=RELEASE):
    output=Path(output)
    if output.exists():raise FileExistsError('Never overwrite a frozen data release')
    from scripts.audit_family_matching import verified_tokenizer
    tokenizer,token_identity=verified_tokenizer(Path(tokenizer_dir))
    excluded,leakage=protected_identities();surface_bytes,shared=shared_surface()
    train,train_selection=make_groups(excluded)
    train=assign(train);train_numbers={tuple(sorted(g['numbers'])) for g in train}
    evaluation,eval_selection=make_groups(excluded|train_numbers,quotas=EVAL_QUOTAS,pool='eval')
    evaluation=assign(evaluation,pool='eval');eval_numbers={tuple(sorted(g['numbers'])) for g in evaluation}
    surface_numbers={tuple(sorted(r['numbers'])) for r in shared}
    if train_numbers&eval_numbers or (train_numbers|eval_numbers)&excluded or (train_numbers|eval_numbers)&surface_numbers:
        raise ValueError('New training/evaluation/protected replay identities overlap')
    diagnostic,midpoint=diagnostic_groups(train,evaluation)
    h_rows={arm:training_rows(train,arm) for arm in ('single','paired')}
    # Only the added interface annotation differs; every historical source field
    # remains exact, and shared_F.jsonl itself is a byte-for-byte source copy.
    shared_annotated=[dict(row,interface='F') for row in shared]
    arms={arm:hr+shared_annotated for arm,hr in h_rows.items()}
    schedule=make_schedule();schedules={arm:schedule for arm in arms};encoded={};dose={}
    for arm,data in arms.items():
        encoded[arm]=[encode_row(row,tokenizer,1024) for row in data]
        total=budget_report(encoded[arm],schedule,1)
        parts={}
        for pool,start in (('H',0),('F',512)):
            subset=encoded[arm][start:start+512]
            sub_schedule=[[i-start for i in update if start<=i<start+512] for update in schedule]
            parts[pool]=budget_report(subset,sub_schedule,1)
        dose[arm]=dict(**total,pools=parts,encoded_sha256=digest(encoded[arm]),
            encoded_row_sha256=[digest(row) for row in encoded[arm]],
            joint_distributions={pool:joint_distribution(data[start:start+512],encoded[arm][start:start+512]) for pool,start in (('H',0),('F',512))})
    if encoded['single'][512:]!=encoded['paired'][512:]:raise ValueError('F tokenization differs across arms')
    residual=lambda pool:abs(dose['paired']['pools'][pool]['supervised_response_tokens']/dose['single']['pools'][pool]['supervised_response_tokens']-1)
    dose['comparison']=dict(H_supervised_token_relative_difference=residual('H'),
        total_supervised_token_relative_difference=abs(dose['paired']['supervised_response_tokens']/dose['single']['supervised_response_tokens']-1),
        token_residual_denominator='G-single',H_within_two_percent=residual('H')<=.02,
        matching='Fixed source rows/presentations/256 updates. Exact F bytes and slots. Natural token residual retained; no answer truncation, padding filler or epoch adjustment.',
        rendering_adjustment='None: two preexisting deterministic styles0/1, independent balanced allocation frozen before token audit.',
        exact_equal_tokens_or_flops_claimed=False,shared_F_rows_equal=True,shared_F_slots_equal=True)
    eval_rows={interface:interface_rows(evaluation,interface) for interface in 'FHC'}
    operators=[old.operator_context(row,tokenizer) for row in eval_rows['H']]
    for a,b in zip(operators[::2],operators[1::2]):
        if a['answer_prefix']!=b['answer_prefix']:raise ValueError('Target pair forced prefixes differ')
    for row in eval_rows['H']:
        if len(tokenizer.encode(prefix(row['prompt']),add_special_tokens=False))+512>1024:raise ValueError('Evaluation context too long')
    support=source_support(h_rows,shared)
    def masked_families(records):
        return {digest(old.family(old.replace_op(safe_parse(r['expression']),p,'?')))
                for r in records for p in old.node_paths(safe_parse(r['expression']))}
    families={'new_H':{g['skeleton_family_id'] for g in train},
              'shared_future_F':masked_families(shared),'E031_prep':masked_families(read_jsonl(PREP))}
    similarity={pool:dict(unique_hole_skeleton_families=len(ids),
                         evaluation_groups_with_seen_hole_family=sum(g['skeleton_family_id'] in ids for g in evaluation))
                for pool,ids in families.items()}
    leakage.update(new_H_groups=256,new_evaluation_groups=48,new_training_overlap=0,new_evaluation_overlap=0,
        new_H_number_group_hashes=[g['number_group_hash'] for g in train],
        new_evaluation_number_group_hashes=[g['number_group_hash'] for g in evaluation],
        shared_F_source_sha256=sha256_file(SURFACE),shared_F_new_H_overlap=0,shared_F_new_eval_overlap=0)
    assignment=dict(training=assignment_audit(train),evaluation=assignment_audit(evaluation),
        train16_group_ids=[g['group_id'] for g in diagnostic],midpoint12_group_ids=[g['group_id'] for g in midpoint],
        train16_rule='Two groups per anchor operator by root/internal stratum; both targets retained with single/paired seen labels.',
        midpoint12_rule='One group per unordered operator pair by root/internal stratum; fixed before any model outputs.')
    output.mkdir(parents=True)
    with (output/'shared_F.jsonl').open('xb') as stream:stream.write(surface_bytes)
    write_rows(output/'train_groups.jsonl',train);write_rows(output/'eval_groups.jsonl',evaluation)
    for arm,records in arms.items():write_rows(output/(arm+'.jsonl'),records)
    for interface,records in eval_rows.items():write_rows(output/(interface+'.jsonl'),records)
    for interface in 'FH':write_rows(output/('train_'+interface+'.jsonl'),interface_rows(diagnostic,interface))
    write_rows(output/'midpoint_H.jsonl',interface_rows(midpoint,'H'))
    write_rows(output/'operator_contexts.jsonl',operators)
    for name,record in (('schedules',schedules),('learning_rates',learning_rates(256)),('dose',dose),
                        ('DATA_AUDIT',dict(training=train_selection,evaluation=eval_selection,assignment=assignment,
                                          skeleton_similarity=similarity,structural_ood_claim=False)),
                        ('LEAKAGE_AUDIT',leakage),('TRAIN_TARGET_SUPPORT_AUDIT',support)):
        dump(output/(name+'.json'),record)
    manifest=dict(status='FROZEN_BEFORE_NEW_MODEL_OUTPUTS_CPU_ONLY',seeds=SEEDS,
        training_groups=256,evaluation_groups=48,training_rows={'single':1024,'paired':1024},
        H_rows_per_arm=512,shared_F_rows_per_arm=512,epochs=4,updates_per_arm=256,
        effective_batch_size=16,H_per_update=8,F_per_update=8,microbatch_size=1,
        evaluation_rows={k:len(v) for k,v in eval_rows.items()},train_diagnostic_groups=16,midpoint_groups=12,
        planned_generations=3344,generation_cap=3600,operator_contexts_per_model=96,
        planned_operator_contexts=288,planned_candidate_scores=1152,
        operator_contexts_available_per_model=sum(r['available'] for r in operators),
        tokenizer=token_identity,shared_F_source=str(SURFACE),shared_F_source_sha256=sha256_file(SURFACE),
        parent='E031',parent_manifest_sha256=sha256_file(PARENT_MANIFEST),E030_is_ancestor=False,
        source_files_sha256={str(p):sha256_file(p) for p in (Path(__file__).relative_to(Path.cwd()),
            Path(old.__file__).relative_to(Path.cwd()),Path('experiments/thursday_probe/common.py'),
            Path('experiments/thursday_probe_v2/config.py'),Path('src/pilot_data.py'),Path('src/countdown_smoke.py'),Path('src/sft_data.py'))},
        files_sha256={p.name:sha256_file(p) for p in sorted(output.iterdir()) if p.is_file()},
        dose_comparison=dose['comparison'],prior_artifacts_modified=False,new_model_calls=0,
        new_training_performed=False,no_reserved_contents_read=True,
        interpretation='New numerical instances, exploratory single-training-seed recipe contrast; no structural OOD, exact-token matching, pure mechanism or pretraining-support claim.')
    dump(output/'manifest.json',manifest)
    load_inputs(output)
    return manifest


prepare_release=prepare

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=RELEASE)
    args=parser.parse_args();result=prepare(args.tokenizer_dir,args.output)
    print(json.dumps({k:result[k] for k in ('status','training_rows','evaluation_rows','dose_comparison')}))
