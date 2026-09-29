"""Private, offline plot of verified Post-E039 analysis (no model calls).

Run only after actual core analysis exists. This program never invents missing
measurements, recomputes confidence intervals, or modifies the core manifest.
It writes one supplementary PNG and a provenance JSON, without overwriting.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys


STATES = ('E038', 'E039', 'S-U', 'S-D', 'P-U', 'P-D')
DISPLAY_STATES = ('E038', 'S-U', 'S-D', 'E039', 'P-U', 'P-D')
CONTRASTS = ('delta_S', 'delta_P', 'equal_recipe_mean')
COEFFICIENTS = {
    'delta_S': {'S-D': 1., 'S-U': -1.},
    'delta_P': {'P-D': 1., 'P-U': -1.},
    'equal_recipe_mean': {'S-D': .5, 'S-U': -.5, 'P-D': .5, 'P-U': -.5},
}
PANELS = (
    dict(role='primary_J_H', interface='H', decoding='greedy',
         metric='both_targets_correct', denominator=48,
         title='H greedy: both goals correct', nlabel='groups', primary=True),
    dict(role='secondary_F_sampled_pass_at_1', interface='F', decoding='sampled',
         metric='correct', denominator=384,
         title='F sampled: pass@1', nlabel='outputs', primary=False),
)
COLORS = {'parent': '#67717A', 'U': '#3B6F91', 'D': '#B85B36'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def estimate(value, *, difference=False):
    if not isinstance(value, dict) or not finite(value.get('mean')):
        raise ValueError('Measured estimate must contain a finite mean')
    low = -1 if difference else 0
    if not low <= value['mean'] <= 1:
        raise ValueError('Measured estimate is outside its probability/difference range')
    if value.get('groups') != 48 or not isinstance(value.get('families'), int) or not 1 <= value['families'] <= 48:
        raise ValueError('Expected 48 number groups and an actual family count')
    for key in ('group_ci', 'family_ci'):
        ci = value.get(key)
        if ci is None and key == 'family_ci':
            continue
        if not isinstance(ci, list) or len(ci) != 2 or not all(finite(x) for x in ci):
            raise ValueError('Measured interval is absent or nonfinite: ' + key)
        if not low <= ci[0] <= ci[1] <= 1:
            raise ValueError('Invalid interval bounds: ' + key)
    return value


def load_verified(reports, *, allow_partial=False):
    """Validate identities and outcome mappings before any figure is created."""
    reports = Path(reports)
    manifest = read(reports / 'manifest.json')
    inputs = {}
    for name in ('SUMMARY.json', 'BEHAVIOR_RESULTS.json'):
        digest = sha(reports / name)
        if manifest.get('files_sha256', {}).get(name) != digest:
            raise ValueError('Core manifest SHA mismatch: ' + name)
        inputs[name] = digest
    summary, behavior = read(reports / 'SUMMARY.json'), read(reports / 'BEHAVIOR_RESULTS.json')
    status = summary.get('status')
    if status not in ('all_registered_outputs_verified', 'partial_coverage_verified'):
        raise ValueError('Unrecognized core analysis status')
    if status != 'all_registered_outputs_verified' and not allow_partial:
        raise ValueError('Partial analysis requires --allow-partial; missing is never zero')
    if summary.get('analysis_model_calls') != 0:
        raise ValueError('Expected the registered offline analysis')
    index = {}
    for view in behavior['views']:
        if view['view'] != 'eval' or view['data_key'] != 'eval_' + view['interface']:
            raise ValueError('Training/midpoint view cannot enter the main evaluation plot')
        key = view['state'], view['interface'], view['decoding']
        if key in index or view['state'] not in STATES:
            raise ValueError('Duplicate or unregistered main view')
        index[key] = view
    roles = {}
    for item in behavior['contrasts']:
        if item['role'] in roles:
            raise ValueError('Duplicate contrast role')
        roles[item['role']] = item
    panels, families, measured = [], set(), 0
    for spec in PANELS:
        view_estimates, counts, missing = {}, {}, []
        for state in STATES:
            key = state, spec['interface'], spec['decoding']
            if key not in index:
                raise ValueError('Core analysis omitted a registered evaluation view: ' + str(key))
            view = index[key]
            metrics = view.get('metrics')
            if metrics is None:
                if view['status'] == 'measured':
                    raise ValueError('Measured view has no metrics')
                missing.append(state)
                view_estimates[state] = None
                counts[state] = None
                continue
            if view['status'] != 'measured':
                raise ValueError('Unmeasured view contains metrics')
            value = estimate(metrics[spec['metric']])
            n, d = value.get('numerator'), value.get('denominator')
            if type(n) is not int or type(d) is not int or d != spec['denominator'] or not 0 <= n <= d:
                raise ValueError('Wrong raw numerator/denominator for ' + spec['role'])
            if not math.isclose(n / d, value['mean'], rel_tol=0, abs_tol=1e-12):
                raise ValueError('Group estimate disagrees with balanced raw fraction')
            view_estimates[state], counts[state] = value, (n, d)
            families.add(value['families'])
            measured += 1
        item = roles.get(spec['role'])
        if not item or any(item.get(k) != spec[k] for k in ('interface', 'decoding', 'metric')):
            raise ValueError('Outcome role/interface/metric mapping differs')
        joint = item.get('result')
        if missing:
            if joint is not None or item['status'] == 'measured':
                raise ValueError('Incomplete grid cannot contain a complete planned contrast')
            if not allow_partial:
                raise ValueError('Incomplete six-state grid; use --allow-partial to show explicit NA')
            differences = {key: None for key in CONTRASTS}
        else:
            if not joint or item['status'] != 'measured' or item.get('missing_views'):
                raise ValueError('Complete grid must have its registered joint contrasts')
            if (joint.get('bootstrap_replicates') != 10000 or joint.get('bootstrap_seed') != 2026091714
                    or joint.get('joint_state_order') != list(STATES)):
                raise ValueError('Unregistered bootstrap definition')
            for state in STATES:
                joint_estimate = estimate(joint['states'][state])
                if not math.isclose(joint_estimate['mean'], view_estimates[state]['mean'], rel_tol=0, abs_tol=1e-12):
                    raise ValueError('Joint state mean differs from raw view')
                families.add(joint_estimate['families'])
                # Reuse exactly the same joint analysis estimates as the contrast panels.
                view_estimates[state] = joint_estimate
            differences = {}
            for key in CONTRASTS:
                value = estimate(joint['contrasts'][key], difference=True)
                if value.get('coefficients') != COEFFICIENTS[key]:
                    raise ValueError('D-minus-U contrast direction/weight differs')
                wanted = sum(view_estimates[s]['mean'] * c for s, c in COEFFICIENTS[key].items())
                if not math.isclose(value['mean'], wanted, rel_tol=0, abs_tol=1e-12):
                    raise ValueError('Contrast mean disagrees with registered coefficients')
                differences[key] = value
                families.add(value['families'])
        panels.append(dict(spec=spec, estimates=view_estimates, counts=counts,
                           contrasts=differences, missing_states=missing))
    if not measured:
        raise ValueError('No measured main outcomes; do not create an empty results figure')
    if len(families) != 1:
        raise ValueError('Main outcomes must share the frozen skeleton-family count')
    if status == 'all_registered_outputs_verified' and any(p['missing_states'] for p in panels):
        raise ValueError('Complete status conflicts with missing figure outcomes')
    return dict(summary=summary, panels=panels, families=families.pop(),
                inputs_sha256=inputs, core_manifest_sha256=sha(reports / 'manifest.json'))


def color(state):
    return COLORS['parent'] if state.startswith('E') else COLORS[state[-1]]


def draw_interval(ax, value, y, shade, *, family=True):
    if family and value['family_ci'] is not None:
        lo, hi = (100 * x for x in value['family_ci'])
        ax.plot([lo, hi], [y + .10, y + .10], color=shade, lw=1.1, alpha=.65, zorder=2)
        ax.plot([lo, lo], [y + .06, y + .14], color=shade, lw=1.1, alpha=.65)
        ax.plot([hi, hi], [y + .06, y + .14], color=shade, lw=1.1, alpha=.65)
    lo, hi = (100 * x for x in value['group_ci'])
    ax.plot([lo, hi], [y, y], color=shade, lw=2.8, solid_capstyle='round', zorder=3)
    ax.scatter([100 * value['mean']], [y], c=[shade], s=33, zorder=4,
               edgecolors='white', linewidths=.6)


def plot(bundle, output, *, deps=None):
    if deps:
        sys.path.insert(0, str(Path(deps).resolve()))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import MaxNLocator

    output = Path(output)
    provenance = output.with_suffix('.provenance.json')
    if output.suffix.lower() != '.png':
        raise ValueError('Only PNG output is authorized for this private plotting helper')
    if output.exists() or provenance.exists():
        raise FileExistsError('Never overwrite an existing figure or its provenance')
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.titlesize': 12, 'axes.labelsize': 10,
                         'savefig.facecolor': 'white'})
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 8.7),
                             gridspec_kw={'width_ratios': [1.5, 1]})
    fig.subplots_adjust(left=.115, right=.94, bottom=.18, top=.80, hspace=.43, wspace=.62)
    all_bounds = [abs(100 * v) for panel in bundle['panels'] for d in panel['contrasts'].values() if d
                  for key in ('group_ci', 'family_ci') for v in (d[key] or [])]
    # Common signed scale across both contrast panels; never clip measured intervals.
    bound = min(100, max(5, math.ceil((max(all_bounds, default=0) + 1) / 5) * 5))
    state_labels = {s: (s + '  parent' if s.startswith('E') else s) for s in STATES}
    difference_labels = ['S-D − S-U', 'P-D − P-U', 'Equal recipe mean']
    for row, panel in enumerate(bundle['panels']):
        spec = panel['spec']
        left, right = axes[row]
        left.set_title(('A  Primary: ' if row == 0 else 'C  Secondary: ') + spec['title'], loc='left', pad=14)
        right.set_title(('B' if row == 0 else 'D') + '  Decision-weighted − ordinary CE', loc='left', pad=14)
        left.set_xlim(0, 100)
        left.set_xticks([0, 25, 50, 75, 100])
        left.set_xlabel('Strict success (%)')
        left.set_yticks(range(6), [state_labels[s] for s in DISPLAY_STATES])
        left.set_ylim(5.55, -.60)
        left.axhline(2.5, color='#DDE1E4', lw=.8)
        for i, state in enumerate(DISPLAY_STATES):
            value = panel['estimates'][state]
            count = panel['counts'][state]
            if value is None:
                left.text(.02, i, 'NA — not measured', transform=left.get_yaxis_transform(),
                          va='center', color='#6F7378', fontsize=9)
                raw = 'NA'
            else:
                draw_interval(left, value, i, color(state))
                raw = f'{count[0]}/{count[1]}'
            left.text(1.025, i, raw, transform=left.get_yaxis_transform(), va='center', ha='left',
                      color='#252B30', fontsize=9.5, clip_on=False)
        left.text(1.025, 1.025, 'Raw n/d', transform=left.transAxes, fontsize=9.5, ha='left')
        right.set_xlim(-bound, bound)
        right.xaxis.set_major_locator(MaxNLocator(nbins=5))
        right.set_xlabel('Paired difference (percentage points)')
        right.set_yticks(range(3), difference_labels)
        right.set_ylim(2.55, -.6)
        right.axvline(0, color='#747C83', lw=1, linestyle='--', zorder=1)
        for i, key in enumerate(CONTRASTS):
            value = panel['contrasts'][key]
            if value is None:
                right.text(.04, i, 'NA — six-state grid incomplete', transform=right.get_yaxis_transform(),
                           va='center', color='#6F7378', fontsize=8.8)
            else:
                draw_interval(right, value, i, '#754B72' if key == 'equal_recipe_mean' else '#273F51')
        for ax in (left, right):
            ax.grid(axis='x', color='#E8ECEF', lw=.75, zorder=0)
            ax.set_axisbelow(True)
            ax.tick_params(axis='y', length=0)
            for spine in ('top', 'right', 'left'):
                ax.spines[spine].set_visible(False)
            ax.spines['bottom'].set_color('#BEC5CB')
    partial = bundle['summary']['status'] != 'all_registered_outputs_verified'
    fig.suptitle('Decision supervision at equal added dose' + (' — PARTIAL COVERAGE' if partial else ''),
                 x=.115, ha='left', y=.97, fontsize=18, fontweight='bold')
    fig.text(.115, .918, 'Parents: E038 / E039   •   U: ordinary CE   •   D: H first-decision weight λ = 5',
             ha='left', fontsize=10.5, color='#4C565F')
    handles = [Line2D([0], [0], color=COLORS[k], lw=0, marker='o', label=label)
               for k, label in (('parent', 'Parent endpoint'), ('U', 'U continuation'), ('D', 'D continuation'))]
    handles += [Line2D([0], [0], color='#344553', lw=2.8, marker='o', markersize=4, label='95% group interval'),
                Line2D([0], [0], color='#344553', lw=1.1, alpha=.65, label='95% family sensitivity (offset)')]
    fig.legend(handles=handles, loc='upper left', bbox_to_anchor=(.109, .89), frameon=False,
               ncol=3, fontsize=9.2, handlelength=2, columnspacing=1.7)
    note = (f"48 number groups; {bundle['families']} skeleton families; 10,000 paired bootstrap draws. "
            'One training seed; exploratory.\n'
            'Targets and samples stay nested within groups. Intervals exclude training-seed, parent-seed and assignment uncertainty.\n'
            'H: both targets correct / 48 groups. F: 2 targets × 4 samples × 48 groups = 384 outputs. All invalid outputs remain in n/d.\n'
            'F greedy and pass@4 remain in the accompanying table; a zero-containing interval does not establish equivalence.')
    fig.text(.115, .087, note, ha='left', va='center', fontsize=8.6, color='#515A63', linespacing=1.6)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220)
    plt.close(fig)
    provenance.write_text(json.dumps(dict(
        status='SUPPLEMENTARY_FIGURE_FROM_VERIFIED_CORE', analysis_status=bundle['summary']['status'],
        core_manifest_sha256=bundle['core_manifest_sha256'], input_files_sha256=bundle['inputs_sha256'],
        plot_script_sha256=sha(__file__), files_sha256={output.name: sha(output)},
        bootstrap_recomputed=False, model_calls=0, core_files_modified=False,
        missing_states_by_role={p['spec']['role']: p['missing_states'] for p in bundle['panels']},
        main_roles=[p['spec']['role'] for p in bundle['panels']],
        display_state_order=list(DISPLAY_STATES), uncertainty_scope=bundle['summary']['uncertainty_scope'],
    ), indent=2, sort_keys=True) + '\n')
    return dict(status='created',figure=output.name,provenance=provenance.name,sha256=sha(output))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports', default='reports/post_e039_decision_supervision')
    parser.add_argument('--output', default='reports/post_e039_decision_supervision/DECISION_SUPERVISION_RESULTS.png')
    parser.add_argument('--deps', default='.local/thu_plot_deps')
    parser.add_argument('--allow-partial', action='store_true')
    args = parser.parse_args()
    bundle = load_verified(args.reports, allow_partial=args.allow_partial)
    print(json.dumps(plot(bundle, args.output, deps=args.deps)))


if __name__ == '__main__':
    main()
