"""Finite orchestration of three previously admitted, unchanged C7 NLL calls."""
from pathlib import Path
import datetime, json, os, subprocess, sys, time, traceback, zipfile

sys.path.insert(0, '.local/p012_20261111/amendment7_v1')
from a7_ops import ROOT, PUBLIC, TINKER_PY, ENV, publish, read, sha

state_path = ROOT / 't_gsm_v1/NLL_QUEUE_after_storage.json'
assert not state_path.exists()
state = {'status': 'running', 'controller_pid': os.getpid(), 'events': []}
admission = PUBLIC / 'tinker_gsm_pre_admission_v1/ADMISSION.json'
names = [x['run_id'] for x in read(admission)['endpoints'] if x['endpoint'] == 'nll']
children = {}


def event(stage, **kwargs):
    row = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'stage': stage, **kwargs}
    state['events'].append(row)
    state_path.write_text(json.dumps(state, indent=2) + '\n')
    print(json.dumps(row), flush=True)


try:
    assert read(PUBLIC / 'review_2edeee51/PAID_STORAGE_VERIFIED.json')['effective_rate_usd_per_gigabyte_month'] > 0
    for name in names:
        d = ROOT / 'tinker_formal_v1' / name
        r = read(d / 'request.json')
        assert r['mode'] == 'nll' and r['forecast']['admitted']
        assert r['source_sha256'] == sha('experiments/p012/tinker_lora.py')
        assert r['forecast']['admission_sha256'] == sha(admission)
        assert (d / 'request.json').read_bytes() == subprocess.check_output([
            'git', 'show', 'HEAD:' + str(admission.parent / 'requests' / (name + '.json'))])
        assert not (d / 'result').exists() and not (d / 'run.log').exists()
        with (d / 'run.log').open('x') as log:
            proc = subprocess.Popen([TINKER_PY, str(ROOT / 'amendment4_v1/launch_tinker_private.py'), str(d)],
                env=ENV, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        children[name] = proc
        event('launched', run_id=name, pid=proc.pid)
    done = set()
    deadline = time.monotonic() + 8 * 3600
    while len(done) < len(names):
        assert time.monotonic() < deadline, 'Finite observation deadline reached'
        for name, proc in children.items():
            if name in done:
                continue
            assert proc.poll() in (None, 0), name + ': failed; no replay'
            d = ROOT / 'tinker_formal_v1' / name
            if not (d / 'result/COMPLETE.json').exists():
                continue
            assert read(d / 'result/COMPLETE.json')['success']
            records = read(d / 'result/NLL_RECORDS.json')
            assert len(records) == 1000 and len({x['parent_id'] for x in records}) == 500
            assert all(x['solution_chars'] > 0 for x in records)
            out = PUBLIC / name.replace('_20261114', '')
            out.mkdir(exist_ok=False)
            r = read(d / 'request.json')
            result = {'run_id': name, 'model': r['model'], 'task': 'gsm8k', 'pretraining': True,
                'records': 1000, 'parents': 500, 'nll': read(d / 'result/NLL_SUMMARY.json'),
                'usage': read(d / 'result/USAGE.json'), 'input': r['dataset'],
                'independent_numeric_audit': 'pending'}
            (out / 'RESULTS.json').write_text(json.dumps(result, indent=2) + '\n')
            with zipfile.ZipFile(out / 'evidence.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
                for f in (d / 'result').rglob('*'):
                    if f.is_file():
                        assert b'/Users/' not in f.read_bytes()
                        archive.write(f, str(f.relative_to(d / 'result')))
            (out / 'README.md').write_text('# GSM8K frozen C7 teacher NLL\n\n'
                'All 1,000 solution records over 500 parents, character-normalized summaries, '
                'frozen request and usage are retained. Independent result review is pending.\n')
            commit = publish([out], 'P012: publish authorized GSM NLL ' + name)
            event('published', run_id=name, commit=commit)
            done.add(name)
        if len(done) < len(names):
            time.sleep(10)
    state['status'] = 'complete'
    event('all_three_nll_complete')
except BaseException as exc:
    state['status'] = 'stopped_for_inspection'
    event('stopped', error=str(exc))
    traceback.print_exc()
    raise
