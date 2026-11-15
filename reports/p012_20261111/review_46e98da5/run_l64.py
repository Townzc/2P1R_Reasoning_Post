"""Execute only the original admitted 4B L64 through unchanged reviewed helpers."""
from pathlib import Path
import datetime, json, os, subprocess, sys, time, traceback
sys.path.insert(0, '.local/p012_20261111/amendment7_v1')
from a7_ops import ROOT, PUBLIC, PY, TINKER_PY, ENV, read, sha, publish

NAME = 'a6_3_tinker_lora_4b_math_l64_s17_20261113_v1'
TRAIN = ROOT / 'a6_runs_v1' / NAME
STATE = ROOT / 'l64_after46e98da5_v1/QUEUE.json'
assert not STATE.exists()
state = {'controller_pid': os.getpid(), 'status': 'running', 'events': [], 'automatic_retry': False}
source_hashes = {str(p): sha(p) for p in [Path('experiments/p012/tinker_lora.py'),
    Path('experiments/p012/scoring.py'), Path('experiments/p012/termination_summary.py'),
    ROOT / 'amendment6_v1/prepare_t_post_any.py', ROOT / 'amendment6_v1/score_a6.py',
    ROOT / 'amendment6_v1/publish_a6_cell.py']}


def event(stage, **kwargs):
    item = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'stage': stage, **kwargs}
    state['events'].append(item)
    STATE.write_text(json.dumps(state, indent=2) + '\n'); print(json.dumps(item), flush=True)


def command(helper, *args):
    for f, h in source_hashes.items():
        assert sha(f) == h
    subprocess.run([PY, str(ROOT / 'amendment6_v1' / helper), *args], env=ENV, check=True)


def start(d, request_path):
    assert not (d / 'run.log').exists() and not (d / 'result').exists()
    r = read(d / 'request.json')
    assert r['source_sha256'] == sha('experiments/p012/tinker_lora.py')
    assert r['forecast']['admitted'] and sha(r['forecast']['admission_file']) == r['forecast']['admission_sha256']
    assert (d / 'request.json').read_bytes() == subprocess.check_output(['git', 'show', 'HEAD:' + str(request_path)])
    with (d / 'run.log').open('x') as f:
        proc = subprocess.Popen([TINKER_PY, str(ROOT / 'amendment4_v1/launch_tinker_private.py'), str(d)],
            env=ENV, stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
    event('launched', run_id=d.name, pid=proc.pid)
    return proc


def wait_for(d, proc):
    deadline = time.monotonic() + 8 * 3600
    while not (d / 'result/COMPLETE.json').exists():
        assert proc.poll() in (None, 0), 'Failed call; no automatic replay'
        assert not (d / 'result/PARTIAL_USAGE.json').exists()
        assert time.monotonic() < deadline
        time.sleep(10)
    assert read(d / 'result/COMPLETE.json')['success']


try:
    storage = read(PUBLIC / 'review_46e98da5/STORAGE_API_CHECK.json')
    assert storage['rate_usd_per_gigabyte_month'] > 0
    assert (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(storage['utc'])).total_seconds() < 600
    r = read(TRAIN / 'request.json')
    assert (r['cell'], r['seed'], r['dose']['expected_updates']) == ('L64', 17, 16)
    proc = start(TRAIN, PUBLIC / 'l64_after46e98da5_admission_v1/requests' / (NAME + '.json'))
    wait_for(TRAIN, proc)
    command('prepare_t_post_any.py', 'a6_runs_v1/' + NAME)
    ev = TRAIN.with_name(NAME.replace('_s17_', '_s17_greedy_'))
    req = PUBLIC / 'tinker_lora_post_requests_v2' / (ev.name + '.json')
    commit = publish([req], 'P012: publish original 4B L64 full MATH evaluation request')
    event('evaluation_request_published', commit=commit)
    proc = start(ev, req); wait_for(ev, proc)
    command('score_a6.py', ev.name)
    command('publish_a6_cell.py', NAME)
    out = PUBLIC / NAME.replace('_20261113', '')
    commit = publish([out], 'P012: publish original 4B L64 result under approved cap38')
    state['status'] = 'complete'
    event('result_published', commit=commit, accuracy=read(out / 'RESULTS.json')['MATH5000']['accuracy'])
except BaseException as exc:
    state['status'] = 'stopped_for_inspection'; event('stopped', error=str(exc))
    traceback.print_exc(); raise
