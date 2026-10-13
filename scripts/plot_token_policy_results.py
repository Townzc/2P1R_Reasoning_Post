"""Deterministic research figures, gated on eight local oracles and final audit.

Reads existing results only. No model calls, resampling, slide generation, or
selection of a checkpoint. The conditional intervals come from the frozen
summary script and do not cover training-seed or procurement uncertainty.
"""
import argparse
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def figures(summary_path, closeout_path, out):
    summary, closeout = read(summary_path), read(closeout_path)
    expected = {f'{policy}_p{price}_s{seed}'
                for policy in ('breadth', 'depth')
                for price in (0, 4) for seed in (17, 23)}
    if (set(closeout['full_student_oracles']) != expected
            or closeout['main_endpoint_outputs'] != 10552
            or closeout['main_supervised_targets'] != 4194296
            or closeout['main_scientific_updates'] != 2048
            or closeout['main_endpoint_unknown'] != 0
            or closeout['cpu_audit_labels'] != 14
            or closeout['containers']):
        raise ValueError('Complete independent closeout is required')
    if (summary['updates'], summary['supervised_targets'],
            summary['endpoint_outputs']) != (2048, 4194296, 10552):
        raise ValueError('Summary dose differs from admitted eight students')
    cells = {row['cell']: row for row in summary['table']}
    if set(cells) != {'breadth_p0', 'depth_p0', 'breadth_p4', 'depth_p4'}:
        raise ValueError('All four cells are required')
    for cell, row in cells.items():
        if set(row['seeds']) != {'17', '23'}:
            raise ValueError('Both realized training seeds are required')
        for seed, result in row['seeds'].items():
            oracle = closeout['full_student_oracles'][f'{cell}_s{seed}']
            if (result['n'] != 1319 or result['correct'] != oracle['correct']
                    or result['stop_reasons'] != oracle['stop_diagnostics']['stop_reasons']
                    or abs(result['accuracy'] - result['correct'] / 1319) > 1e-12):
                raise ValueError('Plot data differ from independently checked endpoint')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.fonttype': 'none'})
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    outputs = []

    def save(fig, name):
        for extension in ('png', 'svg'):
            path = out / f'{name}.{extension}'
            fig.savefig(path, dpi=180, facecolor='white')
            outputs.append(path)
        plt.close(fig)

    colors = {'breadth': '#176B9B', 'depth': '#C65C21'}
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.8), sharey=True)
    all_values = [100 * r['accuracy'] for c in cells.values() for r in c['seeds'].values()]
    low, high = min(all_values) - 2.5, max(all_values) + 2.5
    for ax, seed in zip(axes, (17, 23)):
        for policy, title in (('breadth', 'More problems'), ('depth', 'More solutions')):
            records = [cells[f'{policy}_p{price}']['seeds'][str(seed)] for price in (0, 4)]
            values = [100 * r['accuracy'] for r in records]
            ax.plot([0, 1], values, marker='o', linewidth=2,
                    color=colors[policy], label=title)
            for x, value, result in zip((0, 1), values, records):
                offset = 10 if policy == 'breadth' else -22
                ax.annotate(f"{value:.2f}%\n{result['correct']}/1319", (x, value),
                            xytext=(0, offset), textcoords='offset points',
                            ha='center', fontsize=9, color=colors[policy])
        ax.set_title(f'Training seed {seed}')
        ax.set_xticks([0, 1], ['Problem price 0', 'Problem price 4m'])
        ax.set_xlim(-.18, 1.18)
        ax.set_ylim(low, high)
        ax.grid(axis='y', alpha=.2)
    axes[0].set_ylabel('Greedy exact-answer accuracy (%)')
    axes[1].legend(loc='upper right', frameon=False)
    fig.suptitle('Common acquisition cap and fixed student training budget', fontsize=13)
    fig.text(.05, .065, 'Two training seeds; one teacher trace per cell. Hypothetical token tariff, not API dollars.', fontsize=9)
    fig.text(.05, .025, 'All 1,319 questions retained; 512-token capped outputs count as incorrect. Lines connect two observed scenarios.', fontsize=9)
    fig.subplots_adjust(left=.09, right=.97, bottom=.23, top=.84, wspace=.16)
    save(fig, 'accuracy_by_price_and_seed')

    names = ('depth_minus_breadth_p0', 'depth_minus_breadth_p4', 'price_interaction')
    titles = ('Price 0: more solutions − more problems',
              'Price 4m: more solutions − more problems',
              'Price interaction: high-price gap − zero-price gap')
    fig, axes = plt.subplots(3, 1, figsize=(10.5, 7.3), sharex=True)
    max_abs = max(abs(v) for name in names
                  for rec in [summary['contrasts'][name], *summary['contrasts'][name]['per_seed'].values()]
                  for v in rec['conditional_question_interval_pp'])
    for ax, name, title in zip(axes, names, titles):
        contrast = summary['contrasts'][name]
        records = [(f'Seed {seed}', contrast['per_seed'][str(seed)]['difference_pp'],
                    contrast['per_seed'][str(seed)]['conditional_question_interval_pp'])
                   for seed in (17, 23)]
        records.append(('Mean of two observed seeds', contrast['mean_difference_pp'],
                        contrast['conditional_question_interval_pp']))
        for y, (label, point, interval) in enumerate(records):
            lo, hi = interval
            color = '#515151' if y < 2 else '#176B9B'
            ax.errorbar(point, y, xerr=[[point - lo], [hi - point]], fmt='o',
                        capsize=4, color=color, markersize=5)
            ax.annotate(f'{point:+.2f} [{lo:+.2f}, {hi:+.2f}]', (max_abs + .3, y),
                        fontsize=9, va='center')
        ax.axvline(0, color='#888888', linewidth=1, linestyle='--')
        ax.set_yticks(range(3), [x[0] for x in records])
        ax.set_ylim(2.65, -.75)
        ax.set_title(title, loc='left', fontsize=11)
        ax.grid(axis='x', alpha=.15)
    axes[-1].set_xlabel('Difference in accuracy (percentage points)')
    axes[-1].set_xlim(-max_abs - .6, max_abs + 4.4)
    fig.text(.03, .055, '95% conditional paired-question intervals: 10,000 shared resamples, fixed seed 20261013.', fontsize=9)
    fig.text(.03, .025, 'These intervals exclude training-seed and acquisition-trace uncertainty; the observed-seed mean is not a seed CI.', fontsize=9)
    fig.subplots_adjust(left=.25, right=.97, bottom=.17, top=.95, hspace=.55)
    save(fig, 'policy_gaps_and_price_interaction')

    provenance = dict(schema='p007b_verified_deterministic_figures_v1',
        summary_sha256=sha(summary_path), closeout_sha256=sha(closeout_path),
        generator_sha256=sha(__file__), figures={p.name: sha(p) for p in outputs},
        new_model_calls=0, new_bootstrap_computations=0,
        slides_generated=False, primary_scoring_unchanged=True)
    (out / 'PROVENANCE.json').write_text(json.dumps(provenance, indent=2) + '\n')
    return provenance


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for key in ('summary', 'closeout', 'out'):
        parser.add_argument('--' + key, required=True)
    args = parser.parse_args()
    print(json.dumps(figures(args.summary, args.closeout, args.out)))
