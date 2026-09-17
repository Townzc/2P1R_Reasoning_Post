"""Plot frozen, CPU-verified E038/E039 results; no model calls."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    root = Path('reports/post_e037_goal_training')
    data = json.loads((root/'GOAL_SWITCH_RESULTS.json').read_text())
    rows = {r['evaluation']: r['metrics'] for r in data['views']}
    comparisons = {r['role']: r['result'] for r in data['recipe_comparisons']}
    states = ['E031', 'G-single', 'G-paired']
    colors = ['#9aa3af', '#377eb8', '#c85e31']
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'savefig.dpi': 180})
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.4), layout='constrained')
    for ax, interface, mode, metric, title in [
        (axes[0, 0], 'H', 'greedy', 'both_targets_correct', 'A  H: both goals correct (primary)'),
        (axes[0, 1], 'F', 'sampled', 'correct', 'B  F: sampled pass@1 (primary)')]:
        stats = [rows[f'{s}_{interface}_{mode}'][metric] for s in states]
        heights = np.array([s['mean']*100 for s in stats])
        errors = np.array([[s['mean']-s['group_ci'][0] for s in stats],
                           [s['group_ci'][1]-s['mean'] for s in stats]])*100
        ax.bar(states, heights, color=colors, width=.6, yerr=errors,
               error_kw={'capsize': 4, 'lw': 1})
        for i, stat in enumerate(stats):
            ax.text(i, stat['group_ci'][1]*100+1.1 if interface=='H' else stat['group_ci'][1]*100+.15,
                    f"{stat['numerator']}/{stat['denominator']}", ha='center', fontsize=10)
        ax.set(title=title, ylabel='Strict success (%)', ylim=(0, 45 if interface=='H' else 8))
        ax.grid(axis='y', alpha=.18); ax.set_axisbelow(True)
    ax = axes[1, 0]
    categories = ['Strict correct', 'Scaffold kept, wrong operator', 'Other failure']
    bottoms = np.zeros(3)
    for category, color in zip(categories, ['#457d66', '#e0a955', '#dadde2']):
        values = []
        for state in states:
            m = rows[f'{state}_H_greedy']['interface_error_categories']
            correct = m.get('strict_correct', 0)
            wrong = m.get('template_followed_wrong_hole_operator', 0)
            values.append({'Strict correct': correct, 'Scaffold kept, wrong operator': wrong,
                           'Other failure': 96-correct-wrong}[category]/96*100)
        ax.bar(states, values, bottom=bottoms, color=color, width=.6, label=category)
        bottoms += values
    ax.set(title='C  H greedy: interface versus choice', ylabel='Share of 96 outputs (%)', ylim=(0, 102))
    ax.legend(loc='upper left', bbox_to_anchor=(0, -.12), frameon=False, fontsize=8)
    ax = axes[1, 1]
    for y, key, label in [(1, 'primary_direct_J_H', 'H both goals'),
                           (0, 'primary_transfer_pass_at_1', 'F sampled pass@1')]:
        stat = comparisons[key]; mean = stat['mean']*100
        lo, hi = [v*100 for v in stat['group_ci']]
        ax.errorbar(mean, y, xerr=[[mean-lo], [hi-mean]], fmt='o', color='#333333', capsize=5)
        ax.text(-19, y+.22, f'{mean:+.2f} pp [{lo:+.2f}, {hi:+.2f}]', fontsize=9)
    ax.axvline(0, color='#888888', ls='--', lw=1)
    ax.set(title='D  G-paired minus G-single', xlabel='Difference (percentage points)',
           yticks=[0, 1], yticklabels=['F sampled pass@1', 'H both goals'], ylim=(-.55, 1.7), xlim=(-20, 12))
    ax.grid(axis='x', alpha=.18)
    fig.suptitle('E038 / E039: interface improves; no observed paired-recipe gain on primary outcomes', fontsize=13)
    fig.supxlabel('95% paired number-group bootstrap intervals; 48 groups, 10,000 draws. One training seed; exploratory.', fontsize=9)
    for extension in ('png', 'pdf'):
        fig.savefig(root/f'PRIMARY_RESULTS.{extension}')
    plt.close(fig)


if __name__ == '__main__':
    main()
