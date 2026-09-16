"""Immutable artifacts, exact arithmetic, and frozen experiment constants."""
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import random

from src.countdown_smoke import canonical, expression, safe_parse, value, render_trace
from src.pilot_data import surface_response
from src.sft_data import sha256_file

ROOT = Path('experiments/thursday_probe')
SEEDS = {'data': 20260916, 'prep': 2026091601, 'assignment': 2026091602,
         'training': 17, 'evaluation': 2026091603, 'bootstrap': 2026091604}
ALIASES = {'E018': 'gsm8k_lora_e018_r1', 'THU_PREP_C': 'thu_prep_control_e019_r1',
    'THU_PREP_B': 'thu_prep_bridge_e020_r1', 'THU_C_SURFACE': 'thu_c_surface_e021_r1',
    'THU_C_PATHS': 'thu_c_paths_e022_r1', 'THU_B_SURFACE': 'thu_b_surface_e023_r1',
    'THU_B_PATHS': 'thu_b_paths_e024_r1', 'THU_C_REPEAT': 'thu_c_repeat_e025_r1',
    'THU_B_REPEAT': 'thu_b_repeat_e026_r1', 'THU_F_REPEAT': 'thu_f_repeat_e027_r1',
    'THU_F_SURFACE': 'thu_f_surface_e028_r1', 'THU_F_PATHS': 'thu_f_paths_e029_r1'}

def stamp():
    return datetime.now(timezone.utc).isoformat()

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def dump(path, obj):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')

def jsonl(path, rows):
    with Path(path).open('x', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True, allow_nan=False)+'\n')

def motifs(tree):
    if tree[0] == 'n':
        return Counter()
    out = motifs(tree[1]) + motifs(tree[2])
    out.update(child[0]+'->'+tree[0] for child in tree[1:] if child[0] != 'n')
    return out

def leaves(tree):
    return [tree[1]] if tree[0] == 'n' else leaves(tree[1])+leaves(tree[2])

def operations(tree):
    if tree[0] == 'n':
        return []
    return operations(tree[1])+operations(tree[2])+[(tree[0], value(tree[1]), value(tree[2]), value(tree))]

def depth(tree):
    return 0 if tree[0] == 'n' else 1+max(depth(tree[1]), depth(tree[2]))

def path_record(tree):
    return {'expression': expression(tree), 'path_id': canonical(tree),
        'structure_id': canonical(tree, structure_only=True), 'interfaces': dict(motifs(tree)),
        'depth': depth(tree), 'operators': dict(Counter(x[0] for x in operations(tree))),
        'intermediates': [str(x[3]) for x in operations(tree)],
        'identity_operations': sum((op == '+' and (a == 0 or b == 0)) or
            (op == '-' and b == 0) or (op == '*' and (a == 1 or b == 1)) or
            (op == '/' and b == 1) for op, a, b, _ in operations(tree))}

def response(tree, variant=0):
    return surface_response(render_trace(tree), variant) if len(leaves(tree)) == 4 else render_trace(tree)

def learning_rates(steps):
    warm = max(1, round(steps/16))
    return [1e-4*s/warm if s <= warm else
            1e-5 + (1e-4-1e-5)/2*(1+math.cos(math.pi*(s-warm)/(steps-warm)))
            for s in range(1, steps+1)]

def epoch_schedule(n, epochs, batch_size, seed=17):
    schedule = []
    for e in range(epochs):
        order = list(range(n))
        random.Random(seed+e).shuffle(order)
        schedule.extend(order[i:i+batch_size] for i in range(0, n, batch_size))
    return schedule

def verify_manifest(folder):
    folder = Path(folder)
    m = json.loads((folder/'manifest.json').read_text())
    for name, h in m['files_sha256'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts or sha256_file(folder/name) != h:
            raise ValueError('Immutable artifact changed: '+name)
    return m
