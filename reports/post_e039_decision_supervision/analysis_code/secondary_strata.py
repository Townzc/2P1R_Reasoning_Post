"""Offline, descriptive strata from a verified Post-E039 core analysis.

No new scoring, model calls, bootstrap, or primary endpoint. Complete-view
strict scores are preserved. Fresh-pool target roles are allocation labels,
never seen/unseen or supervised/unsupervised labels. Missing views remain NA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


STATES = ('E038', 'E039', 'S-U', 'S-D', 'P-U', 'P-D')
OPS = ('+', '-', '*', '/')
MEASURES = {
    'H_both_targets': ('H', 'greedy', 1, 'both_targets_correct', 'groups'),
    'H_strict_per_target': ('H', 'greedy', 1, 'correct', 'target outputs'),
    'F_sampled_pass1': ('F', 'sampled', 4, 'correct', 'sample outputs'),
}
DISCLAIMERS = [
    'Secondary descriptive strata only; no new primary endpoint or significance test.',
    'Small strata are exploratory. All registered levels are retained, not selected by outcome.',
    'One training seed. Targets and sampled outputs are nested within number groups; recipes are not independent seeds.',
    'Original strict scorer is unchanged. All invalid completed-view outputs remain in denominators; any legal correct F construction is accepted.',
    'Fresh-pool anchor/countergoal are frozen allocation roles only. No fresh evaluation target is relabeled as supervised, seen, or unseen using inherited training metadata.',
    'H both-target success is undefined within a single target role; those cells are not_applicable, not zero.',
    'D-minus-U counts use the same group/target/sample identities. Rescue/loss are descriptive discordances, not independent trials or McNemar/significance tests.',
    'D-minus-U requires both specified arm views; equal-recipe mean requires all four continuation views. In a partial run these descriptive subsets do not replace the registered all-six-state primary comparison.',
    'No new intervals are calculated; refer to the original complete-grid paired group/family intervals for planned inference.',
]


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_file(folder, name, mapping):
    digest = sha(folder / name)
    if mapping.get(name) != digest:
        raise ValueError('Manifest SHA mismatch: ' + name)
    return digest


def load_release(release):
    release = Path(release)
    manifest = read(release / 'manifest.json')
    bindings = {name: checked_file(release, name, manifest['files_sha256'])
                for name in ('eval_groups.jsonl', 'F.jsonl', 'H.jsonl')}
    groups = rows(release / 'eval_groups.jsonl')
    if len(groups) != 48 or len({g['group_id'] for g in groups}) != 48:
        raise ValueError('Expected all 48 distinct frozen evaluation groups')
    group_index = {g['group_id']: g for g in groups}
    role_available = all(type(g.get('anchor_target_index')) is int and g['anchor_target_index'] in (0, 1) for g in groups)
    for group in groups:
        pair = group['operator_pair']
        if len(pair) != 2 or len(set(pair)) != 2 or any(op not in OPS for op in pair):
            raise ValueError('Invalid frozen operator pair')
        if group['hole_position'] not in ('root', 'internal'):
            raise ValueError('Invalid frozen hole position')
        if (group['hole_position'] == 'root') != (group['hole_path'] == []):
            raise ValueError('Hole position/path disagree')
        if {t['target_index'] for t in group['targets']} != {0, 1} or len(group['targets']) != 2:
            raise ValueError('Each fresh group must have its two frozen targets')
        if set(t['correct_operator'] for t in group['targets']) != set(pair):
            raise ValueError('Operator pair disagrees with targets')
    row_index = {}
    for interface in ('F', 'H'):
        data = rows(release / (interface + '.jsonl'))
        if len(data) != 96 or len({r['problem_id'] for r in data}) != 96:
            raise ValueError('Expected 96 distinct rows per interface')
        seen = set()
        for row in data:
            group = group_index[row['group_id']]
            key = row['group_id'], row['target_index']
            if key in seen or row['interface'] != interface:
                raise ValueError('Duplicate or mismatched interface/target row')
            seen.add(key)
            target = next(t for t in group['targets'] if t['target_index'] == row['target_index'])
            if any(row.get(k) != group.get(k) for k in ('numbers', 'operator_pair', 'hole_position', 'skeleton_family_id')):
                raise ValueError('Row/group metadata disagree')
            if row['target'] != target['target'] or row['correct_operator'] != target['correct_operator']:
                raise ValueError('Row target/operator disagree')
            if role_available and (row['anchor_target_index'] != group['anchor_target_index'] or
                    row['is_anchor'] is not (row['target_index'] == group['anchor_target_index'])):
                raise ValueError('Frozen allocation role disagrees')
            row_index[interface, row['problem_id']] = row
        if seen != {(g, t) for g in group_index for t in (0, 1)}:
            raise ValueError('Missing registered target')
    return group_index, row_index, role_available, bindings


def load_core(reports, release):
    reports, release = Path(reports), Path(release)
    manifest = read(reports / 'manifest.json')
    inputs = {name: checked_file(reports, name, manifest['files_sha256'])
              for name in ('SUMMARY.json', 'BEHAVIOR_RESULTS.json', 'PER_PROBLEM.jsonl')}
    if manifest['release_manifest_sha256'] != sha(release / 'manifest.json'):
        raise ValueError('Core/release identity differs')
    groups, frozen_rows, role_available, release_inputs = load_release(release)
    summary = read(reports / 'SUMMARY.json')
    if summary['status'] not in ('all_registered_outputs_verified', 'partial_coverage_verified') or summary['analysis_model_calls'] != 0:
        raise ValueError('Expected registered offline core analysis')
    behavior = read(reports / 'BEHAVIOR_RESULTS.json')
    events = {}
    for view in behavior['views']:
        key = view['state'], view['interface'], view['decoding']
        if key in events or view['state'] not in STATES or view['view'] != 'eval':
            raise ValueError('Duplicate or invalid main view identity')
        events[key] = view
    per_problem = rows(reports / 'PER_PROBLEM.jsonl')
    if len(per_problem) != summary['completed_unique_generations']:
        raise ValueError('Per-problem coverage differs from core summary')
    collected = {key: [] for key in events}
    for record in per_problem:
        if record['view'] != 'eval':
            continue
        # Sample index zero is shared by greedy and sampled: evaluation name is authoritative.
        matching = [key for key, event in events.items() if event['name'] == record['evaluation']]
        if len(matching) != 1:
            raise ValueError('Unregistered per-problem evaluation name')
        key = matching[0]
        event = events[key]
        if record['state'] != event['state'] or record['interface'] != event['interface'] or record['data_key'] != event['data_key']:
            raise ValueError('Per-problem state/interface/data identity differs')
        frozen = frozen_rows[record['interface'], record['problem_id']]
        for field in ('group_id', 'target_index', 'numbers', 'target', 'template', 'is_anchor'):
            if record.get(field) != frozen.get(field):
                raise ValueError('Per-problem frozen identity differs: ' + field)
        if type(record['score']['correct']) is not bool:
            raise ValueError('Strict correctness must be boolean; unknown is not a successful output')
        collected[key].append(record)
    values = {}
    for state in STATES:
        for interface, decoding, samples, _, _ in MEASURES.values():
            key = state, interface, decoding
            if key in values:
                continue
            if key not in events:
                raise ValueError('Core omitted a required registered main view')
            event, records = events[key], collected[key]
            metrics = event.get('metrics')
            if metrics is None:
                if records or event['status'] == 'measured':
                    raise ValueError('Unmeasured complete view has published core metrics/records')
                values[key] = None
                continue
            if event['status'] != 'measured' or event['samples'] != samples:
                raise ValueError('Measured view status/sample count differs')
            indexed = {}
            for record in records:
                identity = record['group_id'], record['target_index'], record['sample_index']
                if type(record['sample_index']) is not int or identity in indexed:
                    raise ValueError('Duplicate or malformed registered sample identity')
                indexed[identity] = record['score']['correct']
            expected = {(g, t, s) for g in groups for t in (0, 1) for s in range(samples)}
            if set(indexed) != expected:
                raise ValueError('Measured view is not the complete registered target/sample set')
            count = sum(indexed.values())
            if metrics['correct']['numerator'] != count or metrics['correct']['denominator'] != len(expected):
                raise ValueError('Strict counts do not reproduce core result')
            if interface == 'H':
                both = sum(indexed[g, 0, 0] and indexed[g, 1, 0] for g in groups)
                if metrics['both_targets_correct']['numerator'] != both or metrics['both_targets_correct']['denominator'] != len(groups):
                    raise ValueError('Both-target counts do not reproduce core result')
            values[key] = indexed
    if summary['status'] == 'all_registered_outputs_verified' and any(v is None for v in values.values()):
        raise ValueError('Complete analysis contains missing main views')
    return dict(summary=summary, groups=groups, values=values, roles_available=role_available,
                source_binding=dict(core_manifest_sha256=sha(reports/'manifest.json'),
                    core_files_sha256=inputs, release_manifest_sha256=sha(release/'manifest.json'),
                    release_files_sha256=release_inputs))


def frozen_strata(groups, roles_available):
    result = []
    pairs = sorted({tuple(sorted(g['operator_pair'], key=OPS.index)) for g in groups.values()},
                   key=lambda p: tuple(OPS.index(op) for op in p))
    for pair in pairs:
        selected = {gid: [0, 1] for gid, g in groups.items() if set(g['operator_pair']) == set(pair)}
        result.append(dict(axis='operator_pair', level='(' + ', '.join(pair) + ')', scope='group', membership=selected))
    for position in ('root', 'internal'):
        result.append(dict(axis='hole_position', level=position, scope='group',
            membership={gid: [0, 1] for gid, g in groups.items() if g['hole_position'] == position}))
    for role in ('anchor', 'countergoal'):
        result.append(dict(axis='target_role', level=role, scope='target',
            membership=({gid: [g['anchor_target_index'] if role == 'anchor' else 1-g['anchor_target_index']]
                         for gid, g in groups.items()} if roles_available else None)))
    return result


def selected_values(indexed, membership, measure):
    if indexed is None:
        return None
    if measure == 'H_both_targets':
        return {(g,): indexed[g, 0, 0] and indexed[g, 1, 0] for g in membership}
    samples = MEASURES[measure][2]
    return {(g, t, s): indexed[g, t, s] for g, targets in membership.items() for t in targets for s in range(samples)}


def paired_counts(u, d):
    if u is None or d is None:
        return dict(status='not_measured_required_arm_views', difference_pp=None)
    if set(u) != set(d) or not u:
        raise ValueError('Paired stratum identities differ or are empty')
    if any(type(v) is not bool for v in list(u.values()) + list(d.values())):
        raise ValueError('Paired outcome is not strict boolean')
    denominator = len(u)
    un, dn = sum(u.values()), sum(d.values())
    rescue = sum(not u[k] and d[k] for k in u)
    loss = sum(u[k] and not d[k] for k in u)
    if dn-un != rescue-loss:
        raise AssertionError('Discordance/net arithmetic differs')
    return dict(status='measured_descriptive', U_numerator=un, D_numerator=dn,
                denominator=denominator, net_correct=dn-un, rescue=rescue, loss=loss,
                difference_pp=100*(dn-un)/denominator)


def summarize(bundle):
    result = []
    for stratum in frozen_strata(bundle['groups'], bundle['roles_available']):
        membership = stratum['membership']
        for measure, (interface, decoding, samples, _, unit) in MEASURES.items():
            row = dict(axis=stratum['axis'], level=stratum['level'], measure=measure, unit=unit,
                       group_ids=sorted(membership) if membership else [],
                       target_ids=sorted([[g, t] for g, ts in (membership or {}).items() for t in ts]),
                       groups=len(membership or {}), state_counts={}, contrasts={})
            reason = ('target_role_metadata_unavailable' if membership is None else
                      'both_goals_undefined_within_one_target_role' if stratum['scope'] == 'target' and measure == 'H_both_targets' else
                      'empty_frozen_stratum' if not membership else None)
            if reason:
                row.update(status='not_applicable', reason=reason)
                row['state_counts'] = {state: dict(status='not_applicable', numerator=None, denominator=None, fraction=None) for state in STATES}
                row['contrasts'] = {key: dict(status='not_applicable', difference_pp=None) for key in ('delta_S', 'delta_P', 'equal_recipe_mean')}
                result.append(row)
                continue
            selected = {state: selected_values(bundle['values'][state, interface, decoding], membership, measure) for state in STATES}
            expected_n = len(membership) if measure == 'H_both_targets' else sum(map(len, membership.values()))*samples
            for state, values in selected.items():
                row['state_counts'][state] = (dict(status='not_measured_complete_view', numerator=None,
                    denominator=expected_n, fraction=None) if values is None else
                    dict(status='measured_descriptive', numerator=sum(values.values()), denominator=len(values),
                         fraction=sum(values.values())/len(values)))
            row['contrasts']['delta_S'] = paired_counts(selected['S-U'], selected['S-D'])
            row['contrasts']['delta_P'] = paired_counts(selected['P-U'], selected['P-D'])
            ds, dp = (row['contrasts'][key]['difference_pp'] for key in ('delta_S', 'delta_P'))
            row['contrasts']['equal_recipe_mean'] = dict(
                status='measured_descriptive' if ds is not None and dp is not None else 'not_measured_required_arm_views',
                difference_pp=(ds+dp)/2 if ds is not None and dp is not None else None,
                interpretation='Equal recipe average; not two training-seed replicates and not a pooled independent-trial count.')
            row['status'] = 'all_six_measured_descriptive' if all(v is not None for v in selected.values()) else 'partial_descriptive'
            result.append(row)
    return result


def markdown(payload):
    lines = ['# Secondary strata: decision supervision', '',
             'These are descriptive supplements to the frozen main analysis. No primary endpoint or original score is changed.', '']
    lines += ['- ' + text for text in DISCLAIMERS]
    for measure in MEASURES:
        subset = [r for r in payload['strata'] if r['measure'] == measure]
        lines += ['', '## ' + measure, '', '| Frozen stratum | Groups | ' + ' | '.join(STATES) + ' |',
                  '|---|---:|' + '---:|'*len(STATES)]
        for row in subset:
            cells = [row['axis'] + ': `' + row['level'] + '`', str(row['groups'])]
            for state in STATES:
                cell = row['state_counts'][state]
                cells.append('NA' if cell['numerator'] is None else f"{cell['numerator']}/{cell['denominator']}")
            lines.append('| ' + ' | '.join(cells) + ' |')
        lines += ['', 'D−U cells give **net correct / denominator; difference in pp; rescue/loss**. '
                  'The equal mean is in pp only; detailed U and D counts are in JSON.', '',
                  '| Frozen stratum | delta_S | delta_P | Equal recipe mean |', '|---|---|---|---|']
        for row in subset:
            cells = [row['axis'] + ': `' + row['level'] + '`']
            for key in ('delta_S', 'delta_P', 'equal_recipe_mean'):
                item = row['contrasts'][key]
                value = item['difference_pp']
                if value is None:
                    cells.append('NA')
                elif key == 'equal_recipe_mean':
                    cells.append(f'{value:+.2f} pp')
                else:
                    cells.append(f"{item['net_correct']:+d}/{item['denominator']}; {value:+.2f} pp; {item['rescue']}/{item['loss']}")
            lines.append('| ' + ' | '.join(cells) + ' |')
    lines += ['', 'Missing views and structurally undefined target-role both-goal cells are distinguished in JSON. '
              'All membership identities are frozen-release derived. No model outputs or results were fabricated.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports', default='reports/post_e039_decision_supervision')
    parser.add_argument('--release', default='experiments/post_e039_decision_supervision/release_v1')
    parser.add_argument('--output', default=None, help='Output directory; defaults to reports. Never overwrites.')
    args = parser.parse_args()
    bundle = load_core(args.reports, args.release)
    payload = dict(status='EXPLORATORY_DESCRIPTIVE_SUPPLEMENT', analysis_status=bundle['summary']['status'],
                   target_roles_available=bundle['roles_available'], source_binding=bundle['source_binding'],
                   model_calls=0, new_bootstrap_draws=0, scoring_changed=False, main_endpoints_changed=False,
                   notes=DISCLAIMERS, strata=summarize(bundle))
    output = Path(args.output or args.reports)
    names = ('SECONDARY_STRATA.json', 'SECONDARY_STRATA.md', 'SECONDARY_STRATA.provenance.json')
    if any((output/name).exists() for name in names):
        raise FileExistsError('Never overwrite a supplementary strata report')
    output.mkdir(parents=True, exist_ok=True)
    (output/names[0]).write_text(json.dumps(payload, indent=2, sort_keys=True)+'\n')
    (output/names[1]).write_text(markdown(payload))
    provenance = dict(status='SUPPLEMENTARY_REPORTS_ONLY', script_sha256=sha(__file__),
                      source_binding=bundle['source_binding'],
                      files_sha256={name: sha(output/name) for name in names[:2]},
                      core_manifest_modified=False, model_calls=0)
    (output/names[2]).write_text(json.dumps(provenance, indent=2, sort_keys=True)+'\n')
    print(json.dumps(dict(status='created', files=list(names), model_calls=0)))


if __name__ == '__main__':
    main()
