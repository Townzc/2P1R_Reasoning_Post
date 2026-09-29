"""One recipe, a finite queue, and explicit phase-local resource limits."""
import math
from pathlib import Path

from experiments.thursday_probe.common import SEEDS, epoch_schedule

ROOT = Path('experiments/thursday_probe_v2')
DATA = Path('experiments/thursday_probe/data_r1')
RELEASE = ROOT / 'release_r2'
OUT = Path('runs/thursday_arithmetic_v2_r1')
BRANCH = 'codex/iclr-2027-sprint'
REVISION = '8faed761d45a263340a0528343f099c05c9a4323'
OLD_LEDGER_HASH = '48541b40ec441c1c5d5870d7c198c00a5e567ef7bc3804e03ccc1d61a63fda8e'
POLICY = 'local_adjacent_subtraction_multiplication_v2.1'
STATES = ('C', 'B', 'C-S', 'C-P', 'B-S', 'B-P')
TRAINING = (
    ('calibration', 'C0', 'calibration_fit', 32),
    ('C', 'C0', 'prep_control', 32),
    ('B', 'C0', 'prep_bridge', 32),
    ('C-S', 'C', 'surface', 256),
    ('C-P', 'C', 'paths', 256),
    ('B-S', 'B', 'surface', 256),
    ('B-P', 'B', 'paths', 256),
)
LIMITS = {
    'generation_cap': 4864, 'core_generations': 4608,
    'optional_c0_discovery_greedy': 96, 'planned_generations': 4704,
    'optional_prefix_and_n8_enabled': False,
    'absolute_document_generation_cap': 7936,
    'process_seconds': 8400, 'kill_grace_seconds': 15,
    'training_run_seconds': 900, 'whole_window_seconds': 10800,
    'export_shutdown_reserve_seconds': 1500,
    'maximum_current_rate_cny_per_hour': 10.0,
    'whole_window_compute_cost_cap_cny': 30.0,
    'minimum_free_disk_gib': 4.5,
}


def learning_rates(steps):
    warm = max(1, round(steps / 16))
    return [5e-5 * s / warm if s <= warm else
            1e-5 + (5e-5 - 1e-5) / 2 * (1 + math.cos(math.pi * (s-warm) / (steps-warm)))
            for s in range(1, steps+1)]


def evaluation_queue():
    events = []
    def add(state, view, questions, samples, sampling):
        events.append(dict(name=state+'_'+view, state=state, view=view,
                           questions=questions, samples=samples, sampling=sampling,
                           generations=questions*samples))
    add('C0', 'calibration', 48, 1, False)
    add('C0', 'probes', 96, 4, True)
    add('C0', 'discovery_greedy', 96, 1, False)
    add('calibration', 'calibration', 48, 1, False)
    for s in ('C', 'B'):
        add(s, 'probes', 96, 4, True)
    for s in STATES[2:]:
        add(s, 'midpoint', 24, 1, False)
    for s in STATES:
        add(s, 'discovery_sampled', 96, 4, True)
        add(s, 'discovery_greedy', 96, 1, False)
    for s in STATES[2:]:
        add(s, 'sentinel', 48, 2, True)
    assert sum(e['generations'] for e in events) == LIMITS['planned_generations']
    return events


def continue_after_measurement(*, hard_errors, resource_available, **measurements):
    """Accuracy, NLL improvement, probe significance and sign never select cells."""
    return not hard_errors and resource_available
