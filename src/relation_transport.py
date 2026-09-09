"""Constructive S5 evidence-route task. No model, rejection sampling or data I/O."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import itertools
import json
import random

STATES = tuple(range(5))
PERMS = tuple(itertools.permutations(STATES))
PERM_INDEX = {p: i for i, p in enumerate(PERMS)}
HEADER = (
    "States: 0 1 2 3 4.\n"
    "Each edge row lists the images of states 0 1 2 3 4 in that order.\n"
    "Tables are bijections. Reverse traversal uses the inverse table.\n"
    "Find a simple path from the query source to its target using listed edges.\n"
    "Write each step as E id : N from = state > N to = state.\n"
    "Finish with Answer : state.\nEdges:\n"
)


def derive_seed(*parts):
    raw = json.dumps(parts, separators=(",", ":")).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:16], "big")


def compose(a, b):
    return tuple(a[b[x]] for x in STATES)


def inverse(p):
    out = [0] * 5
    for x, y in enumerate(p):
        out[y] = x
    return tuple(out)


def render_prompt(question):
    rows = [f"E {e['id']} : N {e['u']} > N {e['v']} : " + " ".join(map(str, e['table']))
            for e in question['edges']]
    return HEADER + "\n".join(rows) + (
        f"\nQuery : N {question['source']} = {question['state']} > N {question['target']}\n")


def render_certificate(question, edge_ids):
    edges = {e['id']: e for e in question['edges']}
    node, state = question['source'], question['state']
    rows = []
    for edge_id in edge_ids:
        edge = edges[edge_id]
        if node == edge['u']:
            nxt, value = edge['v'], edge['table'][state]
        elif node == edge['v']:
            nxt, value = edge['u'], inverse(edge['table'])[state]
        else:
            raise ValueError('Certificate edge is not incident on current node')
        rows.append(f"E {edge_id} : N {node} = {state} > N {nxt} = {value}")
        node, state = nxt, value
    if node != question['target']:
        raise ValueError('Certificate misses target')
    return "\n".join(rows) + f"\nAnswer : {state}"


def make_world(seed, index, *, split):
    """Separate RNG streams prevent label-dependent rendering/deletion choices."""
    semantic = random.Random(derive_seed('semantic', seed, index))
    surface = random.Random(derive_seed('surface', seed, index))
    intervention = random.Random(derive_seed('intervention', seed, index))
    # 14 task nodes plus 20 distractor nodes; eight four-edge chains.
    routes = [[0, 2 + 3*r, 3 + 3*r, 4 + 3*r, 1] for r in range(4)]
    distractors = [list(range(14 + 5*r, 19 + 5*r)) for r in range(4)]
    potentials = [semantic.choice(PERMS) for _ in range(34)]
    x = semantic.randrange(5)
    endpoint = compose(potentials[1], inverse(potentials[0]))
    nodes = list(range(100, 134)); surface.shuffle(nodes)
    labels = list(range(200, 232)); surface.shuffle(labels)
    edges, task_paths, distractor_paths = [], [], []
    for chain_i, chain in enumerate(routes + distractors):
        ids = []
        for j, (u, v) in enumerate(zip(chain, chain[1:])):
            edge_id = labels[4*chain_i + j]
            ids.append(edge_id)
            edges.append({'id': edge_id, 'u': nodes[u], 'v': nodes[v],
                          'table': list(compose(potentials[v], inverse(potentials[u])))})
        (task_paths if chain_i < 4 else distractor_paths).append(ids)
    surface.shuffle(edges)
    question = {'source': nodes[0], 'target': nodes[1], 'state': x, 'edges': edges}
    keep = intervention.randrange(4)
    removed_routes = [r for r in range(4) if r != keep]
    positions = [intervention.choice((1, 2)) for _ in removed_routes]
    decoy_slots = list(range(4)); intervention.shuffle(decoy_slots)
    useful_ids = [task_paths[r][p] for r, p in zip(removed_routes, positions)]
    irrelevant_ids = [distractor_paths[r][p] for r, p in zip(decoy_slots[:3], positions)]
    return {
        'world_id': f'c014_s{seed:05d}_i{index:03d}', 'seed': seed, 'index': index, 'split': split,
        'question': question, 'prompt': render_prompt(question),
        'answer': endpoint[x], 'gold_endpoint_map': list(endpoint),
        'task_paths': task_paths, 'distractor_paths': distractor_paths,
        'responses': [render_certificate(question, p) for p in task_paths],
        'intervention': {'keep_route': keep, 'useful_delete': useful_ids,
                         'irrelevant_delete': irrelevant_ids, 'internal_positions': positions},
    }


def views(world):
    """All views stay in their parent's split. Labels are never part of the prompt."""
    base = world['question']
    output = {'clean': (deepcopy(base), world['answer'])}
    for name, field in [('useful_delete', 'useful_delete'), ('irrelevant_delete', 'irrelevant_delete')]:
        q = deepcopy(base)
        removed = set(world['intervention'][field])
        q['edges'] = [e for e in q['edges'] if e['id'] not in removed]
        output[name] = q, world['answer']
    q = deepcopy(base); q['state'] = (q['state'] + 1) % 5
    output['source_change'] = q, world['gold_endpoint_map'][q['state']]
    q = deepcopy(base)
    for e in q['edges']:
        if e['v'] == q['target']:
            e['table'] = [(v + 1) % 5 for v in e['table']]
        elif e['u'] == q['target']:
            e['table'] = [e['table'][(v - 1) % 5] for v in STATES]
    output['target_change'] = q, (world['answer'] + 1) % 5
    return output


def allocation_schedule(world_ids, seed, cycles=1):
    if not world_ids or len(world_ids) % 4 or cycles < 1:
        raise ValueError('Complete four-question blocks and positive cycles required')
    rng = random.Random(seed)
    ids = list(world_ids); rng.shuffle(ids)
    blocks = [ids[k:k+4] for k in range(0, len(ids), 4)]
    assignment = {}
    for block in blocks:
        slots = list(range(4)); rng.shuffle(slots)
        assignment.update(zip(block, slots))
    updates = []
    for cycle in range(cycles):
        order = list(range(len(blocks))); rng.shuffle(order)
        for block_id in order:
            for rnd in range(4):
                block = blocks[block_id]
                updates.append({'cycle': cycle, 'round': rnd, 'world_ids': block,
                                'multi': [(assignment[w] + rnd) % 4 for w in block],
                                'repeat': [assignment[w] for w in block]})
    return {'assignment': assignment, 'updates': updates}
