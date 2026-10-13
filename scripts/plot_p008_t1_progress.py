"""Deterministic descriptive T1 figure from published, locally verified totals.

No endpoint rescoring, uncertainty inference, timing admission or model calls.
"""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main(out):
    out = Path(out)
    if out.exists():
        raise ValueError('Use a new output directory; preserve published figures')
    paths = [Path('reports/p008_20261013') / p / 'SUMMARY.json'
             for p in ('student_t1_eight_v1', 'student_t1_replacements_v1')]
    rows = {}
    for path in paths:
        for row in json.loads(path.read_text())['runs']:
            name = row.get('logical_run_id', row.get('run_id'))
            assert name not in rows and row['local_oracle_passed']
            assert row['updates'] == 256 and row['targets'] == 524287
            assert row['n'] == 1319 and row['technical_unknowns'] == 0
            rows[name] = row
    pairs = [('D1 / B1 / price 0', 'd1_b1_p0'),
             ('D1 / B1 / price 4m', 'd1_b1_p4'),
             ('D2 / B1 / price 0', 'd2_b1_p0'),
             ('D2 / B1 / price 4m', 'd2_b1_p4'),
             ('D1 / B8 / price 0  [T1 bridge]', 'd1_b8_p0')]
    table = []
    for label, stem in pairs:
        b, d = [rows[stem + '_' + policy + '_t1'] for policy in ('breadth', 'depth')]
        table.append(dict(label=label, breadth=b['correct'], depth=d['correct'],
                          n=1319, depth_minus_breadth_pp=100*(d['correct']-b['correct'])/1319,
                          caps=[b['length_caps'], d['length_caps']]))
    assert len(rows) == 10
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'svg.hashsalt': 'p008-t1-v1'})
    fig = plt.figure(figsize=(11, 5.6), facecolor='white')
    ax = fig.add_axes([.39, .22, .57, .56])
    ax.axvline(0, color='#89949d', linewidth=1)
    for i, row in enumerate(table):
        y = 4-i; gap = row['depth_minus_breadth_pp']
        color = '#246b9e' if i < 4 else '#8b5f28'
        ax.plot([0, gap], [y, y], color=color, alpha=.45, linewidth=3)
        ax.scatter([gap], [y], s=62, color=color, zorder=3)
        ax.text(gap+(.055 if gap>=0 else -.055), y, f'{gap:+.2f} pp',
                ha='left' if gap>=0 else 'right', va='center', color=color)
    ax.set_xlim(-1.1, 1.1); ax.set_ylim(-.65, 4.65)
    ax.set_yticks(range(5), ['']*5); ax.tick_params(axis='y', length=0)
    ax.set_xlabel('Depth minus breadth (percentage points)')
    ax.grid(axis='x', color='#e7ebef', linewidth=.8); ax.set_axisbelow(True)
    for side in ('top', 'right', 'left'): ax.spines[side].set_visible(False)
    fig.text(.03, .93, 'P008: all ten T1 endpoints verified locally', fontsize=18, weight='bold')
    fig.text(.03, .875, 'Fixed training: 256 updates / 524,287 targets. All eight T8 outcomes remain pending.', fontsize=11)
    fig.text(.03, .81, 'Condition', weight='bold')
    fig.text(.295, .81, 'Breadth / depth', weight='bold', ha='center')
    for i, row in enumerate(table):
        y = .22 + .56*((4-i+.65)/5.3)
        fig.text(.03, y, row['label'], va='center', fontsize=10)
        fig.text(.305, y, f"{row['breadth']} / {row['depth']}", va='center', ha='center', fontsize=11)
    fig.text(.03, .115, 'Counts are correct answers out of 1,319. Points only; uncertainty intervals are not shown.', fontsize=10)
    fig.text(.03, .075, 'Two procurement draws share initialization seed 17; data changes the training path. This is not a full B × T result.', fontsize=10)
    fig.text(.03, .035, 'Original eight endpoints: external PASS. Two replacements and this figure: external review pending. No winner inferred.', fontsize=10)
    out.mkdir()
    fig.savefig(out/'t1_policy_gaps.png', dpi=180)
    fig.savefig(out/'t1_policy_gaps.svg', metadata={'Date': None})
    plt.close(fig)
    evidence = dict(schema='p008_t1_descriptive_figure_v1', rows=table,
                    source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                    uncertainty_displayed=False, T8_included=False, external_review='pending')
    (out/'FIGURE_DATA.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    main(parser.parse_args().out)
