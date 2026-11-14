"""Observe the already launched E8 evaluation, publish it, then gate original L64."""
from pathlib import Path
import datetime, json, os, subprocess, sys, time, traceback
sys.path.insert(0, '.local/p012_20261111/amendment7_v1')
from a7_ops import ROOT, PUBLIC, PY, TINKER_PY, ENV, read, sha, lock, publish, accounting

STATE = ROOT / 'e8_export_recovery_v1/CONTINUATION.json'
assert not STATE.exists()
state = {'controller_pid': os.getpid(), 'status': 'running', 'events': [], 'automatic_retry': False}
frozen = {str(p): sha(p) for p in [Path('experiments/p012/tinker_lora.py'), Path('experiments/p012/scoring.py'),
    Path('experiments/p012/termination_summary.py'), ROOT / 'amendment6_v1/score_a6.py',
    ROOT / 'amendment6_v1/publish_a6_cell.py', ROOT / 'amendment6_v1/prepare_t_post_any.py']}


def event(stage, **kwargs):
    row = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'stage': stage, **kwargs}
    state['events'].append(row)
    STATE.write_text(json.dumps(state, indent=2) + '\n'); print(json.dumps(row), flush=True)


def command(script, *args):
    for p, digest in frozen.items():
        assert sha(p) == digest
    subprocess.run([PY, str(ROOT / 'amendment6_v1' / script), *args], env=ENV, check=True)


def wait_complete(d, pid):
    deadline = time.monotonic() + 8 * 3600
    while not (d / 'result/COMPLETE.json').exists():
        assert not (d / 'result/PARTIAL_USAGE.json').exists(), 'Failed call; no retry'
        os.kill(pid, 0)
        assert time.monotonic() < deadline
        time.sleep(10)
    assert read(d / 'result/COMPLETE.json')['success']


def publish_result(name, recovery=False):
    ev = ROOT / 'a6_runs_v1' / name.replace('_s17_', '_s17_greedy_')
    assert not (ev / 'score.log').exists()
    command('score_a6.py', ev.name)
    command('publish_a6_cell.py', name)
    out = PUBLIC / name.replace('_20261113', '')
    if recovery:
        result = read(out / 'RESULTS.json')
        result['infrastructure_recovery'] = read(ROOT / 'a6_runs_v1' / name / 'result/EXPORT_RECOVERY_BINDING.json')
        (out / 'RESULTS.json').write_text(json.dumps(result, indent=2) + '\n')
        with (out / 'README.md').open('a') as f:
            f.write('\nThis endpoint had one training retry after an interruption and one owner-approved export-only recovery after the free checkpoint limit. All1,024 updates preceded the saved final state. Recovery added zero updates. The new sampler is linked to that state by the approved receipt and remote model/rank/target identity; weight bytes cannot be independently hashed. Original failed evidence is preserved and each attempt is charged once.\n')
    commit = publish([out], 'P012: publish recovered A6-3 result ' + name)
    event('published', run_id=name, commit=commit, accuracy=read(out / 'RESULTS.json')['MATH5000']['accuracy'])


def launch(d):
    assert not (d / 'run.log').exists() and not (d / 'result').exists()
    with (d / 'run.log').open('x') as log:
        proc = subprocess.Popen([TINKER_PY, str(ROOT / 'amendment4_v1/launch_tinker_private.py'), str(d)],
            env=ENV, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    event('launched', run_id=d.name, pid=proc.pid)
    return proc


try:
    launch_receipt = read(ROOT / 'e8_export_recovery_v1/EVALUATION_LAUNCH.json')
    e8_name = 'a6_3_tinker_lora_4b_math_e8_s17_20261113_v1'
    event('observing_existing_E8_evaluation', pid=launch_receipt['pid'])
    wait_complete(ROOT / 'a6_runs_v1' / launch_receipt['run_id'], launch_receipt['pid'])
    publish_result(e8_name, recovery=True)
    name = 'a6_3_tinker_lora_4b_math_l64_s17_20261113_v1'
    tr = ROOT / 'a6_runs_v1' / name
    req = read(tr / 'request_pending.json')
    with lock('BUDGET_ADMISSION.lock'):
        snapshot = accounting()
        amount = req['cpu_counts']['full_training_input_tokens'] * req['prices_per_million']['train'] / 1e6 * 1.25 + .1 + req['forecast']['reserved_greedy_usd']
        gate = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'A6_3_current_usd': snapshot['A6_3_accounted_and_reserved_usd'],
            'L64_buffered_next_usd': amount, 'A6_3_after_usd': snapshot['A6_3_accounted_and_reserved_usd'] + amount,
            'A6_3_cap_usd': 35, 'combined_after_usd': snapshot['combined_reserved_usd'] + amount,
            'combined_cap_usd': 485, 'snapshot': snapshot}
        gate['admitted'] = gate['A6_3_after_usd'] <= 35 and gate['combined_after_usd'] <= 485
        target = PUBLIC / 'review_2edeee51/L64_BUDGET_GATE.json'
        with target.open('x') as f:json.dump(gate, f, indent=2); f.write('\n')
        if gate['admitted']:
            command('admit_a6_prepared.py', 'a6_3_4b_l64_after_export_admission_v1', name)
    paths = [target]
    if gate['admitted']:
        paths.append(PUBLIC / 'a6_3_4b_l64_after_export_admission_v1')
    commit = publish(paths, 'P012: record L64 budget gate after measured E8 settlement')
    if not gate['admitted']:
        state['status'] = 'E8_complete_L64_budget_hold'
        event('L64_budget_hold', A6_3_after_usd=gate['A6_3_after_usd'], cap_usd=35, commit=commit)
    else:
        proc = launch(tr); wait_complete(tr, proc.pid)
        command('prepare_t_post_any.py', 'a6_runs_v1/' + name)
        ev = tr.with_name(name.replace('_s17_', '_s17_greedy_'))
        publish([PUBLIC / 'tinker_lora_post_requests_v2' / (ev.name + '.json')], 'P012: publish reserved 4B L64 evaluation request')
        proc = launch(ev); wait_complete(ev, proc.pid); publish_result(name)
        state['status'] = 'complete'; event('E8_and_L64_complete')
except BaseException as exc:
    state['status'] = 'stopped_for_inspection'; event('stopped', error=str(exc))
    traceback.print_exc(); raise
