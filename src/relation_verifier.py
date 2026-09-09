"""Independent exposed-text solver and proof checker; no generator imports."""
from __future__ import annotations

from collections import defaultdict, deque
import hashlib
import itertools
import re

EDGE = re.compile(r'E (\d{3}) : N (\d{3}) > N (\d{3}) : ([0-4](?: [0-4]){4})')
QUERY = re.compile(r'Query : N (\d{3}) = ([0-4]) > N (\d{3})')
STEP = re.compile(r'E (\d{3}) : N (\d{3}) = ([0-4]) > N (\d{3}) = ([0-4])')
FINAL = re.compile(r'Answer : ([0-4])')


def parse_prompt(text):
    if text.count('\nEdges:\n') != 1:
        raise ValueError('Missing or duplicated Edges section')
    body = text.split('\nEdges:\n')[1].splitlines()
    if len(body) < 2:
        raise ValueError('Missing facts/query')
    query = QUERY.fullmatch(body[-1])
    if query is None:
        raise ValueError('Malformed query')
    s, x, t = map(int, query.groups())
    edges = []
    for row in body[:-1]:
        m = EDGE.fullmatch(row)
        if m is None:
            raise ValueError('Malformed edge row')
        edge_id, u, v = map(int, m.groups()[:3])
        table = tuple(map(int, m.group(4).split()))
        if sorted(table) != list(range(5)) or u == v:
            raise ValueError('Nonbijective table or self edge')
        edges.append({'id': edge_id, 'u': u, 'v': v, 'table': table})
    if len({e['id'] for e in edges}) != len(edges):
        raise ValueError('Duplicate edge ID')
    if len({frozenset((e['u'], e['v'])) for e in edges}) != len(edges):
        raise ValueError('Parallel edges outside this grammar')
    nodes = {e[k] for e in edges for k in ('u', 'v')}
    if s == t or s not in nodes or t not in nodes:
        raise ValueError('Invalid query endpoints')
    return {'source': s, 'target': t, 'state': x, 'edges': edges}


def adjacency(q):
    adj = defaultdict(list)
    for e in q['edges']:
        adj[e['u']].append((e['v'], e))
        adj[e['v']].append((e['u'], e))
    return adj


def solve(q):
    """Lift all five table rows into an undirected (node,state) graph."""
    graph = defaultdict(list)
    for e in q['edges']:
        for before, after in enumerate(e['table']):
            a, b = (e['u'], before), (e['v'], after)
            graph[a].append(b); graph[b].append(a)
    start = (q['source'], q['state'])
    seen, queue = {start}, deque([start])
    while queue:
        for node in graph[queue.popleft()]:
            if node not in seen:
                seen.add(node); queue.append(node)
    return sorted(state for node, state in seen if node == q['target'])


def simple_paths(q, max_paths=1000):
    adj = adjacency(q)
    result = []
    def walk(node, visited, steps):
        if node == q['target']:
            result.append(steps)
            if len(result) > max_paths:
                raise ValueError('Path enumeration bound exceeded')
            return
        for nxt, edge in adj[node]:
            if nxt not in visited:
                walk(nxt, visited | {nxt}, steps + [(node, nxt, edge)])
    walk(q['source'], {q['source']}, [])
    return result


def check_certificate(prompt, response):
    try:
        q = parse_prompt(prompt)
    except ValueError:
        return {'valid': False, 'reason': 'invalid_prompt'}
    lines = response.splitlines()
    if len(lines) < 2 or FINAL.fullmatch(lines[-1]) is None:
        return {'valid': False, 'reason': 'missing_final'}
    declared = int(FINAL.fullmatch(lines[-1]).group(1))
    state, node = q['state'], q['source']
    edges = {e['id']: e for e in q['edges']}
    visited = {node}
    for line in lines[:-1]:
        m = STEP.fullmatch(line)
        if m is None:
            return {'valid': False, 'reason': 'malformed_step'}
        edge_id, u, before, v, after = map(int, m.groups())
        if u != node or before != state:
            return {'valid': False, 'reason': 'disconnected_trace'}
        e = edges.get(edge_id)
        if e is None:
            return {'valid': False, 'reason': 'absent_edge'}
        if (u, v) == (e['u'], e['v']):
            correct = e['table'][before] == after
        elif (u, v) == (e['v'], e['u']):
            correct = e['table'][after] == before
        else:
            return {'valid': False, 'reason': 'wrong_endpoints'}
        if not correct:
            return {'valid': False, 'reason': 'wrong_state'}
        if v in visited:
            return {'valid': False, 'reason': 'repeated_node'}
        visited.add(v); node, state = v, after
    if node != q['target'] or declared != state:
        return {'valid': False, 'reason': 'wrong_final'}
    answers = solve(q)
    if answers != [state]:
        return {'valid': False, 'reason': 'inconsistent_or_undetermined'}
    return {'valid': True, 'reason': 'ok', 'answer': state, 'steps': len(lines)-1}


def normalized_chains(q):
    """Complete fixed-topology decomposition, using only exposed edges."""
    adj = adjacency(q)
    paths = simple_paths(q)
    if len(paths) != 4 or any(len(p) != 4 for p in paths):
        raise ValueError('Canonicalization requires the clean four-chain task')
    used = {e['id'] for p in paths for _, _, e in p}
    def table_from(u, e):
        if u == e['u']:
            return tuple(e['table'])
        return tuple(next(a for a, b in enumerate(e['table']) if b == x) for x in range(5))
    task = [[table_from(u, e) for u, _, e in p] for p in paths]
    remaining = {e['id'] for e in q['edges']} - used
    distractors = []
    while remaining:
        edge = next(e for e in q['edges'] if e['id'] in remaining)
        component, queue = {edge['u']}, [edge['u']]
        while queue:
            u = queue.pop()
            for v, e in adj[u]:
                if e['id'] in remaining and v not in component:
                    component.add(v); queue.append(v)
        endpoints = sorted(u for u in component if len(adj[u]) == 1)
        if len(component) != 5 or len(endpoints) != 2:
            raise ValueError('Distractor is not a disconnected four-edge chain')
        u, prev, tables = endpoints[0], None, []
        while True:
            nxt = [(v, e) for v, e in adj[u] if v != prev]
            if not nxt:
                break
            if len(nxt) != 1:
                raise ValueError('Branch in distractor')
            v, e = nxt[0]
            tables.append(table_from(u, e)); remaining.remove(e['id'])
            prev, u = u, v
        distractors.append(tables)
    if len(distractors) != 4:
        raise ValueError('Wrong distractor count')
    return task, distractors


_ORBIT_TABLES = None


def orbit_key(q):
    """Exact canonical word for fixed chains and declared conservative equivalence.

    Ignore source state and target-incident maps to group ALL queries/coherent
    endpoint changes. Quotient node/edge renaming, branch permutations, inverse
    edge notation, distractor reversal and global state conjugation. This is a
    coarsening of labeled-world identity, not topology-OOD or arbitrary local
    state relabeling. No hidden potential/seed is used.
    """
    global _ORBIT_TABLES
    import numpy as np
    perms = tuple(itertools.permutations(range(5)))
    lookup = {p: i for i, p in enumerate(perms)}
    if _ORBIT_TABLES is None:
        inv = [tuple(p.index(x) for x in range(5)) for p in perms]
        conjugations = [[lookup[tuple(g[p[gi[x]]] for x in range(5))]
                         for p in perms] for g, gi in zip(perms, inv)]
        _ORBIT_TABLES = np.asarray(conjugations, dtype=np.uint8), np.asarray([lookup[p] for p in inv])
    conj, inverse_ids = _ORBIT_TABLES
    task, decoys = normalized_chains(q)
    task_ids = [lookup[t] for chain in task for t in chain[:3]]
    decoy_ids = [lookup[t] for chain in decoys for t in chain]
    t_all = conj[:, task_ids].reshape(120, 4, 3)
    d_all = conj[:, decoy_ids].reshape(120, 4, 4)
    candidates = []
    for ts, ds in zip(t_all, d_all):
        t_words = sorted(row.tobytes() for row in ts)
        d_words = sorted(min(row.tobytes(), inverse_ids[row[::-1]].astype('uint8').tobytes()) for row in ds)
        candidates.append(b''.join(t_words + d_words))
    canonical = min(candidates)
    return {'key': hashlib.sha256(canonical).hexdigest(), 'canonical_hex': canonical.hex()}
