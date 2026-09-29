"""Audit unchanged v1 inputs; freeze v2 labels and selections before model calls."""
import argparse
from collections import Counter
from fractions import Fraction
import itertools
import json
from pathlib import Path
import re

from experiments.thursday_probe.common import (
    ALIASES, SEEDS, digest, dump, epoch_schedule, jsonl, motifs, operations,
    path_record, response, stamp, verify_manifest)
from experiments.thursday_probe_v2.config import (
    DATA, ROOT, RELEASE, TRAINING, POLICY, LIMITS, evaluation_queue, learning_rates)
from scripts.audit_family_matching import verified_tokenizer
from src.countdown_smoke import safe_parse, value, canonical, verify_expression, render_trace
from src.pilot_data import SURFACE_FRAMES, verify_row
from src.sft_data import encode_row, budget_report, read_jsonl, sha256_file
from src.trace_audit import audit_trace


def identity_labels(tree):
    """All adjacent target edges must be nondegenerate; no-edge is not nondegenerate."""
    edges = []
    def visit(node, address='root'):
        if node[0] == 'n':
            return
        for side in (1, 2):
            child, sibling = node[side], node[3-side]
            if node[0] == '*' and child[0] == '-':
                diff, other, subtrahend = value(child), value(sibling), value(child[2])
                reasons = [name for name, flag in (
                    ('difference_zero', diff == 0), ('difference_one', diff == 1),
                    ('other_factor_zero', other == 0), ('other_factor_one', other == 1),
                    ('subtrahend_zero', subtrahend == 0)) if flag]
                edges.append(dict(address=address+'/'+str(side), difference=str(diff),
                                  other_factor=str(other), subtrahend=str(subtrahend),
                                  degenerate=bool(reasons), reasons=reasons))
            visit(child, address+'/'+str(side))
    visit(tree)
    anywhere = bool(path_record(tree)['identity_operations'])
    degenerate = any(e['degenerate'] for e in edges)
    return dict(identity_anywhere=anywhere, identity_at_target=degenerate,
                target_present=bool(edges), target_nondegenerate=bool(edges) and not degenerate,
                mixed_target_edges=degenerate and any(not e['degenerate'] for e in edges),
                target_edges=edges, identity_policy_version=POLICY)


def stable_order(rows, purpose):
    return sorted(rows, key=lambda r: digest([purpose, SEEDS['assignment'], r['problem_id']]))


def render_compute(row, variant):
    lines = row['response'].splitlines()
    rendered = []
    for i, line in enumerate(lines[:-1], 1):
        match = re.fullmatch(r'Step (\d+): (.+)\.', line)
        if not match or int(match[1]) != i:
            raise ValueError('Noncanonical existing compute reference')
        rendered.append(SURFACE_FRAMES[variant].format(i=i, eq=match[2]))
    return '\n'.join(rendered+[lines[-1]])


def calibration_rows(rows):
    if len(rows) != 48:
        raise ValueError('Exactly 48 existing calibration questions required')
    output = []
    for category, nfit in (('construct', 8), ('target', 12), ('control', 12)):
        group = [r for r in rows if (r['task'] == 'construct' if category == 'construct'
                                    else r.get('category') == category)]
        if len(group) != 16:
            raise ValueError('Calibration strata changed')
        for i, r in enumerate(stable_order(group, 'calibration/'+category)):
            split = 'fit' if i < nfit else 'check'
            family = 'AB'[i % 2] if category == 'construct' else ('B' if category == 'target' else 'A')
            variant = (i // 2) % 2 if category == 'construct' else i % 2
            row = {k: v for k, v in r.items() if k != 'paths'}
            if category == 'construct':
                row.update(r['paths'][family])
                row['response'] = response(safe_parse(row['expression']), variant)
                row['template_family'] = row['structure_id']
            else:
                row['response'] = render_compute(r, variant)
            row.update(calibration_split=split, rendering_id=variant, coarse_path=family)
            output.append(row)
    for split, n in (('fit', 32), ('check', 16)):
        subset = [r for r in output if r['calibration_split'] == split]
        assert len(subset) == n
        assert Counter(r['rendering_id'] for r in subset) == {0:n//2, 1:n//2}
        assert Counter(r['coarse_path'] for r in subset) == {'A':n//2, 'B':n//2}
    return output


def validate_reference(row):
    tree = safe_parse(row['expression'])
    if canonical(tree) != row['path_id'] or canonical(tree, structure_only=True) != row['structure_id']:
        raise ValueError('Stored canonical program changed')
    if row['task'] == 'construct':
        verify_row(row)
        text, target = row['response'], Fraction(row['target'])
    else:
        if value(tree) != Fraction(row['answer']):
            raise ValueError('Compute target is wrong')
        text = row['response']
        if Fraction(text.splitlines()[-1].removeprefix('Answer: ')) != value(tree):
            raise ValueError('Compute reference final value is wrong')
        text = '\n'.join(text.splitlines()[:-1]+['Answer: '+row['expression']])
        target = value(tree)
    if audit_trace(text, row['numbers'], target)['complete_trace_status'] != 'verified':
        raise ValueError('Reference is not a fully executable connected trace')


def supports(problems, labels):
    by = {(r['problem_id'], r['family']):r for r in labels}
    sets = {}
    for f in 'AB':
        sets.update({f+'_'+k:{p['problem_id'] for p in problems if by[p['problem_id'],f][k]}
                     for k in ('identity_anywhere','identity_at_target','target_present','target_nondegenerate')})
    out = dict(questions=len(problems), counts={k:len(v) for k,v in sets.items()},
               intersections={a+'&'+b:len(sets[a]&sets[b]) for a,b in itertools.combinations(sets,2)},
               groups={'full':[p['problem_id'] for p in problems],
                       'target_nondegenerate':sorted(sets['B_target_nondegenerate']),
                       'target_degenerate':sorted(sets['B_identity_at_target'])})
    assert sets['A_target_present'] == set()
    assert sets['B_target_present'] == set(out['groups']['full'])
    assert len(out['groups']['target_nondegenerate'])+len(out['groups']['target_degenerate']) == len(problems)
    return out


def allocate_ids():
    """Respect IDs reserved by the old alias registry, even though not executed."""
    registry = json.loads(Path('reports/run_registry.json').read_text())
    # Parse identity fields only: hexadecimal file hashes are not experiment IDs.
    names = [r['run_id'] for r in registry['runs']+registry.get('planned_experiments',[])] + list(ALIASES.values())
    used = [int(x) for name in names for x in re.findall(r'(?i)(?:^|_)e(\d{3})(?:_|$)', name)]
    start = max(used)+1
    entries = [dict(experiment_id=f'E{start+i:03d}', state=s, parent=p, data=d,
                    updates=u, run_id=f'thu_v2_e{start+i:03d}_r1')
               for i,(s,p,d,u) in enumerate(TRAINING)]
    return dict(allocation='monotonic_after_executed_and_old_reserved_alias_ids',
                prior_registry_sha256=sha256_file('reports/run_registry.json'),
                old_planned_ids_preserved=list(ALIASES.values()), entries=entries)


def prepare(snapshot):
    old_manifest = verify_manifest(DATA)
    old_audit = json.loads((DATA/'DATA_AUDIT.json').read_text())
    tokenizer, tokenizer_record = verified_tokenizer(Path(snapshot))
    tokenizer.pad_token = tokenizer.eos_token
    primary = {n:read_jsonl(DATA/(n+'.jsonl')) for n in (
        'train_problems','discovery_problems','calibration','surface','paths',
        'prep_control','prep_bridge','probes')}
    if primary['prep_control'][:128] != primary['prep_bridge'][:128]:
        raise ValueError('The 128 shared atomic exercises differ')
    assert Counter(r['category'] for r in primary['probes']) == {'atomic':32,'target':32,'control':32}
    for n, category in (('prep_control','control'),('prep_bridge','target')):
        assert Counter(r['category'] for r in primary[n]) == {'atomic':128,category:128}
    split_sets = {n:{r['number_group_hash'] for r in primary[n]} for n in (
        'train_problems','discovery_problems','calibration','prep_control','prep_bridge','probes')}
    overlaps = {}
    shared = {r['number_group_hash'] for r in primary['prep_control'][:128]}
    for a,b in itertools.combinations(split_sets,2):
        intersection = split_sets[a]&split_sets[b]
        allowed = shared if {a,b} == {'prep_control','prep_bridge'} else set()
        if intersection != allowed:
            raise ValueError('Unexpected complete-instance/number-group leakage')
        overlaps[a+'&'+b] = len(intersection)
    cal = calibration_rows(primary['calibration'])
    labels, by_split = [], {}
    for split, rows in (('train',primary['train_problems']),('discovery',primary['discovery_problems'])):
        subset = []
        for p in rows:
            for family, path in p['paths'].items():
                tree = safe_parse(path['expression'])
                if (not verify_expression(path['expression'],p['numbers'],p['target'])
                    or canonical(tree) != path['path_id'] or dict(motifs(tree)) != path['interfaces']):
                    raise ValueError('Stored reference/program/interface mismatch')
                subset.append(dict(problem_id=p['problem_id'], split=split, family=family,
                                   expression=path['expression'], **identity_labels(tree)))
        labels.extend(subset); by_split[split] = supports(rows,subset)
    sentinel = [r for c in ('atomic','target','control') for r in
                stable_order([r for r in primary['probes'] if r['category']==c], 'sentinel/'+c)[:16]]
    midpoint = stable_order(primary['discovery_problems'], 'midpoint')[:24]
    rows_by = {k:primary[k] for k in ('surface','paths','prep_control','prep_bridge')}
    rows_by['calibration_fit'] = [r for r in cal if r['calibration_split']=='fit']
    for r in cal + [r for rows in rows_by.values() for r in rows] + primary['probes']:
        validate_reference(r)
    schedules = json.loads((DATA/'schedules.json').read_text())
    schedules['calibration'] = epoch_schedule(32,16,16,SEEDS['training'])
    doses = {}
    for name, rows in rows_by.items():
        encoded = [encode_row(r,tokenizer,1024) for r in rows]
        sched = schedules['calibration' if name=='calibration_fit' else 'main' if name in ('surface','paths') else 'prep']
        dose = budget_report(encoded,sched,1)
        dose['max_training_sequence'] = max(r['n_processed'] for r in encoded)
        dose['max_supervised_response'] = max(r['n_supervised'] for r in encoded)
        if dose['max_supervised_response'] >= 512:
            raise ValueError('Reference exceeds common decode capacity')
        if name in old_audit['dose']:
            for key in ('presentations','optimizer_updates','supervised_response_tokens','processed_nonpadding_tokens'):
                if dose[key] != old_audit['dose'][name][key]:
                    raise ValueError('Existing cumulative dose differs')
        doses[name] = dose
    structures = [Counter(r['structure_id'] for r in primary[n]) for n in ('surface','paths')]
    tv = sum(abs(structures[0][k]-structures[1][k]) for k in structures[0].keys()|structures[1].keys())/(2*512)
    encoded_cal = [encode_row(r,tokenizer,1024) for r in cal]
    audit = dict(status='CPU_AUDITED_NO_MODEL_RESULTS', created_at_utc=stamp(),
        immutable_input_manifest_sha256=sha256_file(DATA/'manifest.json'),
        immutable_files_sha256=old_manifest['files_sha256'], target_interface='-->*',
        control_definition='(c*a)-b for sorted a<b<c; bridge=(c-a)*b; disjoint full triples',
        identity_policy=dict(version=POLICY,
            identity_anywhere='Legacy local identity: + with zero, - right zero, * with one, / right one.',
            identity_at_target='Any adjacent subtraction-to-multiplication edge: subtraction result 0/1, sibling factor 0/1, or subtrahend 0.',
            multiple_target_edges='Nondegenerate iff target exists and ALL target edges avoid the local degeneracy rules.',
            limits='Local trajectory labels, not absence of all cancellations or a truth about cognitive complexity.'),
        reference_subgroups=by_split, number_group_intersections=overlaps,
        historical_reserved_group_overlap=old_audit['historical_reserved_group_overlap'],
        historical_reserved_question_contents_read=False,
        main_supervised_token_residual_fraction=old_audit['main_token_residual_fraction'],
        prep_supervised_token_residual_fraction=old_audit['prep_token_residual_fraction'],
        fine_structure_tv=tv, full_global_matching_claimed=False,
        dose_basis='Cumulative across already frozen epochs; never multiply these totals by epochs again.',
        dose_summary={k:{n:v for n,v in x.items() if n not in ('per_update','row_exposures','problem_exposures','path_exposures','text_exposures')} for k,x in doses.items()},
        calibration=dict(fit=32,check=16,fit_composition={'construct':8,'target':12,'control':12},
            check_composition={'construct':8,'target':4,'control':4},
            selection='SHA256 of purpose, frozen assignment seed, problem ID; fixed stratum prefixes.',
            coarse_definition='Construct A/B; compute control=A and target=B (target-edge presence).',
            style='Two existing frames generalized to one/two compute steps; fit16/16 and check8/8.',
            max_reference_response_tokens=max(r['n_supervised'] for r in encoded_cal)),
        sentinel_counts=dict(Counter(r['category'] for r in sentinel)), midpoint_questions=24,
        seeds=SEEDS, new_model_calls=0)
    if RELEASE.exists():
        raise FileExistsError('Immutable release already exists')
    RELEASE.mkdir(parents=True)
    jsonl(RELEASE/'calibration.jsonl', cal)
    jsonl(RELEASE/'calibration_fit.jsonl',rows_by['calibration_fit'])
    jsonl(RELEASE/'sentinel.jsonl',sentinel)
    jsonl(RELEASE/'midpoint.jsonl',midpoint)
    jsonl(RELEASE/'reference_identity_labels.jsonl',labels)
    dump(RELEASE/'schedules.json',schedules)
    dump(RELEASE/'learning_rates.json',{k:learning_rates(len(v)) for k,v in schedules.items()})
    dump(RELEASE/'doses.json',doses)
    dump(RELEASE/'registrations.json',allocate_ids())
    dump(RELEASE/'evaluation_queue.json',evaluation_queue())
    dump(RELEASE/'limits.json',LIMITS)
    dump(RELEASE/'DATA_AUDIT_v2.json',audit)
    dump(RELEASE/'manifest.json',dict(created_at_utc=stamp(),tokenizer=tokenizer_record,
        old_manifest_sha256=sha256_file(DATA/'manifest.json'),
        files_sha256={p.name:sha256_file(p) for p in sorted(RELEASE.iterdir()) if p.is_file()}))
    from experiments.thursday_probe_v2.training import atomic_json
    atomic_json(ROOT/'DATA_AUDIT_v2.json',audit)
    print(json.dumps(dict(fine_structure_tv=tv,reference_supports={k:v['counts'] for k,v in by_split.items()},
        doses=audit['dose_summary'],calibration=audit['calibration'],planned_generations=LIMITS['planned_generations']),indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--tokenizer-dir',required=True)
    prepare(p.parse_args().tokenizer_dir)
