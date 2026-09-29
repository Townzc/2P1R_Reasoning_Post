"""Plot verified F/H/C and conditional operator results without model calls.

Writes PNG and a provenance sidecar. By default all generation
views and operator artifacts must be present; --allow-partial explicitly marks
missing measurements NA and never substitutes zero. This module does not
change the frozen scorer, statistical analysis or original result artifacts.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from experiments.thursday_probe.common import dump, verify_manifest
from src.sft_data import sha256_file

STATES = ('C-S', 'C-P', 'B-S', 'B-P')
SERIES = (('F', 'greedy', 'F greedy', '#7856A6', 'o', True),
          ('H', 'greedy', 'H greedy', '#00868F', 'D', True),
          ('C', 'greedy', 'C greedy', '#64748B', 's', True),
          ('F', 'sampled', 'F sampled', '#7856A6', 'o', False),
          ('H', 'sampled', 'H sampled', '#00868F', 'D', False))
DEFAULT_ANALYSIS = Path('reports/post_e036_goal_probe')


def _interval(metric, *, rate=False):
    mean, ci = metric.get('mean'), metric.get('group_ci')
    if (type(mean) not in (int, float) or not math.isfinite(mean) or
            not isinstance(ci, list) or len(ci) != 2 or
            any(type(x) not in (int, float) or not math.isfinite(x) for x in ci) or ci[0] > ci[1] or
            type(metric.get('groups')) is not int or metric['groups'] <= 0):
        raise ValueError('Missing or invalid measured group-bootstrap estimate')
    if rate and (not 0 <= mean <= 1 or not 0 <= ci[0] <= ci[1] <= 1):
        raise ValueError('Invalid measured probability interval')
    return dict(mean=mean, low=ci[0], high=ci[1], groups=metric['groups'])


def _count(metric):
    n, d = metric['numerator'], metric['denominator']
    if type(n) is not int or type(d) is not int or not 0 <= n <= d or d <= 0:
        raise ValueError('Invalid raw success numerator/denominator')
    return f'{n}/{d}'


def prepare(generations, operators, *, allow_partial=False):
    """Validate structured analyses and preserve exact counts for plotting."""
    views = {}
    for view in generations['views']:
        key = view['state'], view['interface'], view['decoding']
        if key in views:
            raise ValueError('Duplicate state/interface/decoding result')
        views[key] = view
    ops = {r['state']: r for r in operators['results']}
    if len(ops) != len(operators['results']) or set(ops)-set(STATES):
        raise ValueError('Duplicate or unregistered operator state')
    left, right, missing = [], [], []
    for state in STATES:
        for interface, decoding, label, color, marker, filled in SERIES:
            view = views.get((state, interface, decoding))
            if view is None or view.get('status') != 'measured' or view.get('metrics') is None:
                left.append(dict(state=state, interface=interface, decoding=decoding,
                                 label=label, status='not_measured', count='NA'))
                missing.append(f'{state}/{interface}/{decoding}')
                continue
            metric = view['metrics']; estimate = _interval(metric['correct'], rate=True)
            expected_samples = 4 if decoding == 'sampled' else 1
            if (metric['groups'] != 24 or metric['samples_per_target'] != expected_samples or
                    metric['generations'] != metric['groups']*2*expected_samples or
                    metric['correct']['denominator'] != metric['generations'] or
                    not math.isclose(metric['correct']['numerator']/metric['generations'],
                                     estimate['mean'], rel_tol=1e-9, abs_tol=1e-12)):
                raise ValueError('Plot denominator differs from fixed group/target/sample design')
            left.append(dict(state=state, interface=interface, decoding=decoding, label=label,
                             status='measured', count=_count(metric['correct']), **estimate))
        artifact = ops.get(state)
        if artifact is None or artifact.get('status') == 'not_measured':
            right.append(dict(state=state, status='not_measured', argmax='NA', pair_switch='NA',
                              mass='NA', paired_groups='NA'))
            missing.append(state+'/operator')
            continue
        metrics = artifact['metrics']; d = metrics['D_goal']
        ranking = metrics['available_context_ranking_counts']
        pair = metrics['both_targets_correct_unique_argmax']
        total = metrics['registered_contexts']//2
        mean_mass = metrics['raw_candidate_probability_mass']['mean']
        item = dict(state=state, status='not_measurable' if d['mean'] is None else 'measured',
                    argmax=(f"{ranking['correct_unique_argmax']}/{ranking['denominator']}"
                            if ranking['denominator'] else 'NA'),
                    pair_switch=_count(pair) if pair['denominator'] else 'NA',
                    mass=(f'{mean_mass:.2e}' if 0 < mean_mass < .001 else f'{mean_mass:.3f}')
                         if mean_mass is not None else 'NA',
                    paired_groups=f"{d['denominator']}/{total}",
                    available_contexts=metrics['available_contexts'],
                    missing_contexts=metrics['missing_contexts'],
                    unavailable_contexts=len(metrics['unavailable_contexts']))
        if d['mean'] is not None:
            item.update(_interval(d))
        if metrics['missing_contexts']:
            missing.append(state+'/operator contexts')
        right.append(item)
    if missing and not allow_partial:
        raise ValueError('Not measured: '+', '.join(missing)+'. Use --allow-partial to label unavailable views NA.')
    return dict(generations=left, operators=right, missing=missing,
                group_bootstrap_seed=generations['bootstrap_seed'],
                bootstrap_replicates=generations['bootstrap_replicates'])


def _table(ax, rows, widths):
    ax.set_axis_off()
    table = ax.table(cellText=rows, colWidths=widths, cellLoc='center', bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False); table.set_fontsize(9)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor('#E2E8F0'); cell.set_linewidth(.5)
        cell.set_facecolor('#F1F5F9' if row == 0 else '#FFFFFF')
        if row == 0:
            cell.get_text().set_fontweight('bold')
        if col == 0:
            cell.get_text().set_ha('left'); cell.PAD = .045
    return table


def make_figure(data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import PercentFormatter, MaxNLocator

    style = {'font.family': 'DejaVu Sans', 'font.size': 10,
             'axes.spines.top': False, 'axes.spines.right': False,
             'axes.spines.left': False, 'axes.spines.bottom': False}
    with plt.rc_context(style):
        fig = plt.figure(figsize=(13.4, 7.35))
        left = fig.add_axes([.085, .405, .45, .405])
        right = fig.add_axes([.635, .405, .335, .405])
        fig.suptitle('E037: goal-conditioned construction and local operator choice', x=.045, y=.98,
                     ha='left', fontsize=17, fontweight='bold')
        fig.text(.045, .927, '24 number groups × two targets · four frozen endpoints · no additional training', fontsize=10.5)
        if data['missing']:
            fig.text(.97, .927, 'PARTIAL COVERAGE — missing measurements are NA', ha='right',
                     color='#B45309', fontsize=9.5, fontweight='bold')
        for ax in (left, right):
            ax.set_axisbelow(True); ax.yaxis.grid(True, color='#E2E8F0', linewidth=.7)
            ax.tick_params(axis='both', length=0, pad=6)
            ax.set_xlim(-.55, 3.55); ax.set_xticks(range(4), STATES)
        left.set_title('A  Free / hole / compute accuracy', loc='left', fontsize=12, pad=12)
        left.set_ylabel('Strict correct outputs', fontsize=10)
        left.set_ylim(0, 1.015); left.set_yticks([0, .2, .4, .6, .8, 1])
        left.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        lookup = {(r['state'], r['interface'], r['decoding']): r for r in data['generations']}
        offsets = (-.28, -.14, 0, .14, .28)
        handles = []
        for offset, (interface, decoding, label, color, marker, filled) in zip(offsets, SERIES):
            handles.append(Line2D([], [], linestyle='none', marker=marker, color=color,
                                 markerfacecolor=color if filled else 'white', markersize=6, label=label))
            for index, state in enumerate(STATES):
                cell = lookup[state, interface, decoding]
                if cell['status'] != 'measured':
                    continue
                x = index+offset
                left.vlines(x, cell['low'], cell['high'], color=color, alpha=.8, linewidth=1.0, zorder=2)
                left.hlines([cell['low'], cell['high']], x-.026, x+.026, color=color, linewidth=1)
                left.plot(x, cell['mean'], marker=marker, color=color,
                          markerfacecolor=color if filled else 'white', markersize=6, linestyle='none', zorder=3)
        fig.legend(handles=handles, loc='upper left', bbox_to_anchor=(.065, .89), ncol=5,
                   frameon=False, fontsize=9, handletextpad=.35, columnspacing=1.1)
        right.set_title('B  Goal effect given a valid prefix', loc='left', fontsize=12, pad=12)
        right.set_ylabel('$D_{goal}$ (natural-log odds)', fontsize=10, labelpad=6)
        measured = [r for r in data['operators'] if r['status'] == 'measured']
        bound = max([1.0]+[max(abs(r['low']), abs(r['high']), abs(r['mean']))*1.23 for r in measured])
        right.set_ylim(-bound, bound); right.yaxis.set_major_locator(MaxNLocator(nbins=5, symmetric=True))
        right.axhline(0, color='#94A3B8', linestyle='--', linewidth=1, zorder=1)
        for index, cell in enumerate(data['operators']):
            if cell['status'] != 'measured':
                right.text(index, 0, 'NA', ha='center', va='center', fontsize=10, color='#64748B',
                           bbox=dict(facecolor='white', edgecolor='none', pad=3))
                continue
            right.vlines(index, cell['low'], cell['high'], color='#334155', linewidth=1.2, zorder=2)
            right.hlines([cell['low'], cell['high']], index-.07, index+.07, color='#334155', linewidth=1.2)
            right.plot(index, cell['mean'], 'o', color='#1D4ED8', markersize=7, zorder=3)
            right.text(index, min(bound*.92, cell['high']+.08*bound), f"{cell['mean']:+.2f}",
                       ha='center', va='bottom', fontsize=9)
        counts = [['Correct / outputs']+list(STATES)]
        for interface, decoding, label, *_ in SERIES:
            counts.append([label]+[lookup[state, interface, decoding]['count'] for state in STATES])
        _table(fig.add_axes([.045, .135, .51, .225]), counts, [.30]+[.175]*4)
        table = [['Conditional diagnostic']+list(STATES)]
        for key, label in (('argmax', 'Correct unique argmax'), ('pair_switch', 'Both targets argmax'),
                           ('mass', 'Mean candidate mass'), ('paired_groups', 'D measured groups')):
            table.append([label]+[r[key] for r in data['operators']])
        _table(fig.add_axes([.605, .135, .37, .225]), table, [.39]+[.1525]*4)
        fig.text(.045, .083,
                 'F = free construction; H = ordered template; C = evaluation. Greedy: 48 outputs/interface/state. '
                 'F/H sampled pass@1: 192 outputs/interface/state.', fontsize=9, color='#334155')
        fig.text(.045, .051,
                 'Intervals: 95% bootstrap over 24 number groups, not training-seed uncertainty. '
                 'Two targets and all four draws remain nested in each group.', fontsize=9, color='#334155')
        fig.text(.045, .019,
                 'Operator argmax is within four candidates; candidate mass is their summed full-vocabulary probability. '
                 'Positive D or correct ranking is not free-generation success.', fontsize=9, color='#334155')
        return fig


def build(analysis_dir=DEFAULT_ANALYSIS, output_stem=None, *, allow_partial=False):
    analysis_dir = Path(analysis_dir)
    verify_manifest(analysis_dir)
    summary = json.loads((analysis_dir/'SUMMARY.json').read_text())
    if summary['status'] not in ('all_registered_outputs_verified', 'partial_coverage_verified'):
        raise ValueError('A verified offline analysis is required')
    paths = [analysis_dir/'FREE_HOLE_COMPUTE_RESULTS.json', analysis_dir/'OPERATOR_TARGET_SENSITIVITY.json']
    data = prepare(*(json.loads(p.read_text()) for p in paths), allow_partial=allow_partial)
    stem = Path(output_stem) if output_stem else analysis_dir/'GOAL_PROBE_DIAGNOSTIC'
    outputs = [stem.with_suffix(suffix) for suffix in ('.png', '.metadata.json')]
    if any(path.exists() for path in outputs):
        raise FileExistsError('Never overwrite an existing figure or provenance')
    stem.parent.mkdir(parents=True, exist_ok=True)
    import matplotlib
    import matplotlib.pyplot as plt
    figure = make_figure(data)
    try:
        figure.savefig(outputs[0], dpi=300, facecolor='white')
    finally:
        plt.close(figure)
    dump(outputs[1], dict(analysis_manifest_sha256=sha256_file(analysis_dir/'manifest.json'),
        inputs_sha256={p.name: sha256_file(p) for p in paths},
        source_sha256=sha256_file(Path(__file__)), matplotlib_version=matplotlib.__version__,
        state_order=list(STATES), data=data,
        interval='95% number-group bootstrap; excludes training-seed uncertainty',
        files_sha256={outputs[0].name: sha256_file(outputs[0])}))
    return dict(png=str(outputs[0]), metadata=str(outputs[1]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis-dir', type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument('--output-stem', type=Path)
    parser.add_argument('--allow-partial', action='store_true')
    args = parser.parse_args()
    print(json.dumps(build(args.analysis_dir, args.output_stem, allow_partial=args.allow_partial), indent=2))
