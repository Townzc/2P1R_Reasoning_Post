"""Fixed lightweight CPU probes. Feature functions receive exposed text only."""
from __future__ import annotations

import itertools
import numpy as np
from scipy.stats import binomtest
from src.relation_verifier import parse_prompt, adjacency

PERMS = tuple(itertools.permutations(range(5)))
PERM_ID = {p: i for i, p in enumerate(PERMS)}
NAMES = ('prior', 'query_state', 'topology_ridge', 'endpoint_ridge',
         'table_bag_ridge', 'ordered_tables_ridge', 'template_1nn', 'three_step_prefix')
VIEW_NAMES = ('clean', 'useful_delete', 'irrelevant_delete', 'source_change', 'target_change')


def features(prompt):
    q = parse_prompt(prompt)
    source = np.eye(5, dtype=float)[q['state']]
    adj = adjacency(q)
    topology = np.zeros(2*34 + 32*4 + 5)
    topology[q['source']-100] = 1; topology[34+q['target']-100] = 1
    topology[-5:] = source
    for j, e in enumerate(q['edges']):
        topology[68+4*j:72+4*j] = ((e['u']-100)/33, (e['v']-100)/33,
                                      len(adj[e['u']])/4, len(adj[e['v']])/4)
    bag, endpoint, ordered = np.zeros(125), np.zeros(245), np.zeros(805)
    for j, e in enumerate(q['edges']):
        table_id = PERM_ID[tuple(e['table'])]
        bag[table_id] += 1
        if q['source'] in (e['u'], e['v']):
            endpoint[table_id] += 1
        if q['target'] in (e['u'], e['v']):
            endpoint[120+table_id] += 1
        for a, b in enumerate(e['table']):
            ordered[25*j + 5*a+b] = 1
    bag[-5:] = source; endpoint[-5:] = source; ordered[-5:] = source
    # Predeclared three-step branch: smallest neighbor ID, then degree-two
    # continuation. Never reads a fourth table or selects a branch by its label.
    node, previous, state = q['source'], None, q['state']
    completed = 0
    for _ in range(3):
        options = sorted((v, e['id'], e) for v, e in adj[node] if v != previous)
        if not options:
            break
        nxt, _, e = options[0]
        if node == e['u']:
            state = e['table'][state]
        else:
            state = next(a for a, b in enumerate(e['table']) if b == state)
        previous, node = node, nxt; completed += 1
    prefix = q['state']*6 + (state if completed == 3 else 5)
    return {'query_state': q['state'], 'three_step_prefix': prefix,
            'topology_ridge': topology, 'endpoint_ridge': endpoint,
            'table_bag_ridge': bag, 'ordered_tables_ridge': ordered,
            'template_1nn': bag.copy()}


def fit_probes(rows, labels, ridge_alpha=100.0):
    labels = np.asarray(labels, dtype=int)
    target = np.eye(5)[labels]
    models = {'prior': int(np.bincount(labels, minlength=5).argmax())}
    for name, width in [('query_state', 5), ('three_step_prefix', 30)]:
        counts = np.ones((width, 5))
        for row, label in zip(rows, labels):
            counts[row[name], label] += 1
        models[name] = counts.argmax(axis=1)
    for name in [n for n in NAMES if n.endswith('_ridge')]:
        x = np.asarray([r[name] for r in rows])
        mean, std = x.mean(axis=0), x.std(axis=0)
        std[std < 1e-12] = 1
        x = (x - mean)/std
        ymean = target.mean(axis=0)
        weights = np.linalg.solve(x.T@x + ridge_alpha*np.eye(x.shape[1]), x.T@(target-ymean))
        models[name] = {'mean': mean, 'std': std, 'weights': weights, 'ymean': ymean}
    x = np.asarray([r['template_1nn'] for r in rows])
    mean, std = x.mean(axis=0), x.std(axis=0); std[std < 1e-12] = 1
    models['template_1nn'] = {'mean': mean, 'std': std, 'x': (x-mean)/std, 'labels': labels}
    return models


def predict(models, rows):
    out = np.zeros((len(rows), len(NAMES)), dtype=int)
    for k, name in enumerate(NAMES):
        if name == 'prior':
            out[:, k] = models[name]
        elif name in ('query_state', 'three_step_prefix'):
            out[:, k] = models[name][[r[name] for r in rows]]
        elif name.endswith('_ridge'):
            m = models[name]; x = np.asarray([r[name] for r in rows])
            out[:, k] = (((x-m['mean'])/m['std'])@m['weights']+m['ymean']).argmax(axis=1)
        else:
            m = models[name]; x = (np.asarray([r[name] for r in rows])-m['mean'])/m['std']
            train_sq = np.square(m['x']).sum(axis=1)
            for start in range(0, len(x), 64):
                batch = x[start:start+64]
                dist = np.square(batch).sum(axis=1)[:, None] + train_sq[None, :] - 2*batch@m['x'].T
                out[start:start+64, k] = m['labels'][dist.argmin(axis=1)]
    return out


def probe_statistics(predictions, labels, family_tests=40, alpha=0.01):
    labels = np.asarray(labels)
    records = {}
    for k, name in enumerate(NAMES):
        correct = int((predictions[:, k] == labels).sum())
        p = float(binomtest(correct, len(labels), .2, alternative='greater').pvalue)
        records[name] = {'n': len(labels), 'correct': correct, 'accuracy': correct/len(labels),
                         'one_sided_p_vs_0_2': p, 'bonferroni_p': min(1., p*family_tests),
                         'flagged': p*family_tests <= alpha}
    return records
