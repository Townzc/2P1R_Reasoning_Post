"""Optional publication-readable plots from an immutable offline analysis only."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from experiments.thursday_probe.common import dump, verify_manifest
from src.sft_data import sha256_file


STATES = ('C-S', 'C-P', 'B-S', 'B-P')
MEASURES = (('discovery_sampled', 'pass_at_1', 'Sampled pass@1 · n = 4'),
            ('discovery_sampled', 'pass_at_4', 'Sampled pass@4 · n = 4'),
            ('discovery_greedy', 'pass_at_1', 'Greedy accuracy · n = 1'))
GROUP_LABELS = {'full': 'All discovery questions',
                'target_nondegenerate': 'Target-nondegenerate questions'}
COLORS = ('#3778AB', '#3778AB', '#D77835', '#D77835')
DEFAULT_ANALYSIS = Path('reports/thursday_resume_analysis_r1')


def measured_panels(core, *, full_only=False):
    """Reject missing cells/intervals; a missing measurement never becomes zero."""
    index = {}
    for row in core['results']:
        key = row['subgroup'], row['view'], row['metric']
        if key in index:
            raise ValueError('Duplicate discovery result panel')
        index[key] = row
    groups = ['full']
    if not full_only and any(key[0] == 'target_nondegenerate' for key in index):
        groups.append('target_nondegenerate')
    panels = []
    for group in groups:
        group_panels = []
        for view, metric, title in MEASURES:
            row = index.get((group, view, metric))
            if not row or row['status'] != 'complete' or row.get('contrasts') is None:
                raise ValueError('Not measured: complete four-cell '+group+'/'+view+'/'+metric+' required')
            if set(row['cells']) != set(STATES) or not row['questions'] > 0:
                raise ValueError('Incomplete state/question identity in plotting input')
            cells = []
            for state in STATES:
                cell = row['cells'][state]; mean = cell.get('mean'); interval = cell.get('question_ci')
                if (cell.get('status') != 'measured' or not isinstance(mean, (int, float)) or
                        not math.isfinite(mean) or not 0 <= mean <= 1 or
                        not isinstance(interval, list) or len(interval) != 2 or
                        any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in interval) or
                        not 0 <= interval[0] <= interval[1] <= 1 or
                        cell.get('questions') != row['questions']):
                    raise ValueError('Missing/invalid measured rate or question-bootstrap interval')
                cells.append(dict(state=state, mean=mean, low=interval[0], high=interval[1]))
            group_panels.append(dict(subgroup=group, questions=row['questions'], title=title,
                                     view=view, metric=metric, cells=cells))
        if len({p['questions'] for p in group_panels}) != 1:
            raise ValueError('Question population differs between plotted measures')
        panels.append(group_panels)
    return panels


def make_figure(panels):
    """Render already-validated panels; no results are calculated here."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.ticker import PercentFormatter

    style = {'font.family': 'DejaVu Sans', 'font.size': 10,
             'axes.spines.top': False, 'axes.spines.right': False,
             'axes.spines.left': False, 'axes.spines.bottom': False,
             'svg.fonttype': 'none', 'svg.hashsalt': 'thursday-resume-figure-v1'}
    with plt.rc_context(style):
        fig, axes = plt.subplots(len(panels), 3, figsize=(11.4, 3.95 if len(panels) == 1 else 6.65),
                                 sharex=True, sharey=True, squeeze=False)
        fig.subplots_adjust(left=.105, right=.985, top=.75 if len(panels) == 1 else .84,
                            bottom=.20 if len(panels) == 1 else .14, wspace=.18, hspace=.42)
        fig.suptitle('Discovery construction performance', x=.075, y=.98, ha='left',
                     fontsize=17, fontweight='bold')
        fig.text(.075, .91 if len(panels) == 1 else .935,
                 'Frozen four-cell comparison · exact target and number-resource scoring', fontsize=10.5)
        fig.legend(handles=[Patch(facecolor=COLORS[0], label='Control prep (C)'),
                            Patch(facecolor=COLORS[2], label='Bridge prep (B)')],
                   loc='upper right', bbox_to_anchor=(.995, .988), frameon=False, ncol=2,
                   fontsize=9, handlelength=1.2, columnspacing=1.2)
        for row_index, row in enumerate(panels):
            for column, panel in enumerate(row):
                ax = axes[row_index, column]
                ax.set_axisbelow(True); ax.yaxis.grid(True, color='#E5E7EB', linewidth=.7)
                ax.tick_params(axis='both', length=0, pad=6)
                ax.set_ylim(0, 1); ax.set_yticks([0, .2, .4, .6, .8, 1])
                ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
                ax.set_xlim(-.55, 3.55); ax.set_xticks(range(4), STATES)
                ax.tick_params(axis='x', labelbottom=True)
                ax.set_title(panel['title'], loc='left', fontsize=11, pad=11)
                for x, cell in enumerate(panel['cells']):
                    ax.bar(x, cell['mean'], width=.60, color=COLORS[x],
                           edgecolor='white', linewidth=.8, hatch='//' if x % 2 else None, zorder=2)
                    # Draw CI endpoints directly; they need not be symmetric.
                    ax.vlines(x, cell['low'], cell['high'], color='#182230', linewidth=1.1, zorder=3)
                    ax.hlines([cell['low'], cell['high']], x-.075, x+.075,
                              color='#182230', linewidth=1.1, zorder=3)
                    inside = cell['mean'] >= .9
                    y = cell['mean']-.065 if inside else min(.965, cell['high']+.035)
                    ax.text(x, y, f"{100*cell['mean']:.1f}", ha='center', va='center',
                            fontsize=9, color='white' if inside else '#182230',
                            fontweight='bold' if inside else 'normal')
                if column == 0:
                    ax.set_ylabel(GROUP_LABELS[panel['subgroup']]+'\n'+f"{panel['questions']} questions",
                                  fontsize=10, labelpad=10)
        fig.text(.075, .060 if len(panels) == 1 else .050,
                 'Error bars: 95% paired-question bootstrap intervals; training-seed uncertainty is not covered.',
                 fontsize=9, color='#374151')
        fig.text(.075, .015 if len(panels) == 1 else .019,
                 'S = Surface; P = Paths (hatched). Invalid or incomplete answers remain in the denominator. '
                 'All panels use the same 0–100% scale.', fontsize=8.7, color='#374151')
        return fig


def build(analysis_dir=DEFAULT_ANALYSIS, output_stem=None, *, full_only=False):
    analysis_dir = Path(analysis_dir)
    verify_manifest(analysis_dir)
    summary = json.loads((analysis_dir/'summary.json').read_text())
    if summary['status'] not in ('all_registered_outputs_verified', 'partial_coverage_verified'):
        raise ValueError('An independently verified offline analysis is required')
    source = analysis_dir/'core_2x2.json'
    core = json.loads(source.read_text()); panels = measured_panels(core, full_only=full_only)
    stem = Path(output_stem) if output_stem is not None else analysis_dir/'DISCOVERY_FOUR_CELL'
    targets = [stem.with_suffix(ext) for ext in ('.png', '.svg', '.metadata.json')]
    if any(path.exists() for path in targets):
        raise FileExistsError('Do not overwrite a published plot or its provenance')
    stem.parent.mkdir(parents=True, exist_ok=True)
    import matplotlib
    import matplotlib.pyplot as plt
    fig = make_figure(panels)
    try:
        with matplotlib.rc_context({'svg.fonttype': 'none', 'svg.hashsalt': 'thursday-resume-figure-v1'}):
            fig.savefig(targets[0], dpi=300, facecolor='white')
            fig.savefig(targets[1], facecolor='white', metadata={'Date': None,
                'Description': 'Audited discovery point estimates and 95% paired-question bootstrap intervals; '
                               'not training-seed confidence intervals.'})
    finally:
        plt.close(fig)
    provenance = dict(analysis_manifest_sha256=sha256_file(analysis_dir/'manifest.json'),
                      core_results_sha256=sha256_file(source),
                      source_sha256=sha256_file(Path(__file__)), matplotlib_version=matplotlib.__version__,
                      state_order=list(STATES), question_bootstrap_seed=core['seed'],
                      bootstrap_replicates=core['bootstrap_replicates'],
                      uncertainty='Question resampling only; not training-seed uncertainty',
                      panels=panels,
                      files_sha256={path.name: sha256_file(path) for path in targets[:2]})
    dump(targets[2], provenance)
    return dict(png=str(targets[0]), svg=str(targets[1]), provenance=str(targets[2]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis-dir', type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument('--output-stem', type=Path)
    parser.add_argument('--full-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps(build(args.analysis_dir, args.output_stem, full_only=args.full_only), indent=2))
