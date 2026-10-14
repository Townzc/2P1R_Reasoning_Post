"""P008 v3.1: pure CPU contract; no dispatch or result-dependent branch choice."""
import hashlib
import json
import math
from fractions import Fraction

BASE_UPDATES = 256
BASE_TARGETS = 524287
BASE_CAP = 211257
M = Fraction(191151, 512)
STUDENT_SEED = 17
DEADLINE_EPOCH = 1791943200  # 2026-10-14 02:00:00 UTC
PHASE0_ROLES = ('teacher_calibration', 'student_smoke', 'io_probe_a', 'io_probe_b')
BRANCHES = ((8, True, 2), (8, False, 2), (4, False, 2), (4, False, 1))


def lrs(updates):
    if type(updates) is not int or updates < 16 or updates % 16:
        raise ValueError('Use positive multiples of 16; smoke takes a full vector prefix')
    warmup = updates // 16
    # Preserve the exact arithmetic ordering of the original 256-step vector.
    return [1e-4 * (i+1) / warmup if i < warmup else
            1e-5 + (1e-4-1e-5)*.5 * (1+math.cos(math.pi*(i-warmup+1)/(updates-warmup)))
            for i in range(updates)]


def stable_seed(domain, draw, problem_id='', attempt=0):
    if domain not in ('dev_split', 'question_order', 'teacher', 'calibration'):
        raise ValueError('Unknown random stream domain')
    if type(attempt) is not int or attempt < 0:
        raise ValueError('Invalid attempt')
    value = json.dumps(['p008-v3.1', domain, draw, problem_id, attempt],
                       ensure_ascii=False, separators=(',', ':'))
    # vLLM accepts a 64-bit seed; collision-check the finite request roster.
    return int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], 'big') & ((1<<63)-1)


def run_roster(high=8, full_bridge=True, draws=2):
    if (high, full_bridge, draws) not in BRANCHES:
        raise ValueError('Unregistered design branch')
    rows = []
    for draw in range(1, draws+1):
        for b in (1, high):
            for price in (0, 4):
                for policy in ('breadth', 'depth'):
                    rows.append(dict(run_id=f'd{draw}_b{b}_p{price}_{policy}_t{b}', draw=draw,
                        budget_multiple=b, price=price, policy=policy, training_multiple=b, seed=17, role='main'))
    for policy in ('breadth', 'depth'):
        corners = [(high, 1)] + ([(1, high)] if full_bridge else [])
        for b,t in corners:
            rows.append(dict(run_id=f'd1_b{b}_p0_{policy}_t{t}', draw=1, budget_multiple=b,
                price=0, policy=policy, training_multiple=t, seed=17, role='bridge'))
    for row in rows:
        row.update(updates=BASE_UPDATES*row['training_multiple'],
                   targets=BASE_TARGETS*row['training_multiple'], endpoint_outputs=1319)
    return rows


def select_branch(forecasts):
    """Forecasts made once from engineering evidence, before main student outcomes."""
    if len(forecasts) != len(BRANCHES):
        raise ValueError('Report forecasts for every predeclared branch')
    for branch, forecast in zip(BRANCHES, forecasts):
        if tuple(forecast['branch']) != branch:
            raise ValueError('Wrong branch order')
        if forecast['total_stage_usd_upper'] <= 200 and forecast['finish_hour_pdt_upper'] <= 18:
            return branch
    return None


def overlap_seconds(intervals):
    if set(intervals) != set(PHASE0_ROLES):
        raise ValueError('All four actual GPU intervals required')
    if any(a > b for a,b in intervals.values()):
        raise ValueError('Reversed interval')
    return max(0, min(b for a,b in intervals.values())-max(a for a,b in intervals.values()))
