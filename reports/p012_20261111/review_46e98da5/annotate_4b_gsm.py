"""Attach the accepted baseline note after publication; never alter numeric results."""
from pathlib import Path
import datetime, json, os, subprocess, sys, time, traceback
sys.path.insert(0, '.local/p012_20261111/amendment7_v1')
from a7_ops import ROOT, PUBLIC, lock, read, sha

POLICY = PUBLIC / 'review_46e98da5/T_GSM_INTERPRETATION.json'
STATE = ROOT / 'review_46e98da5/ANNOTATION_QUEUE.json'
assert not STATE.exists()
state = {'status': 'running', 'controller_pid': os.getpid(), 'events': []}
names = [n for n in read(PUBLIC / 'tinker_gsm_training_v1/ADMISSION.json')['runs']
         if read(ROOT / 'tinker_gsm_runs_v1' / n / 'request.json')['model'] == 'Qwen/Qwen3.5-4B']
assert len(names) == 9
done = set()


def event(stage, **kwargs):
    row = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'stage': stage, **kwargs}
    state['events'].append(row); STATE.write_text(json.dumps(state, indent=2) + '\n')
    print(json.dumps(row), flush=True)


def annotate(name):
    folder = PUBLIC / name.replace('_20261114', '')
    result = folder / 'RESULTS.json'
    if not result.exists():
        return False
    with lock('GIT_PUBLICATION.lock'):
        committed = subprocess.run(['git', 'show', 'HEAD:' + str(result)], capture_output=True)
        if committed.returncode or committed.stdout != result.read_bytes():
            return False
        before = sha(result)
        side = folder / 'INTERPRETATION.json'
        if side.exists():
            assert read(side)['policy_sha256'] == sha(POLICY)
            return True
        assert not subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True).strip()
        value = {'accepted_review_commit': '46e98da59753315694ebc4a0699f0b7c6c37a9c5',
            'policy': str(POLICY), 'policy_sha256': sha(POLICY), 'result_sha256': before,
            'primary_pretraining_reference': '4-shot', 'reference_correct': 1216, 'reference_questions': 1319,
            'baseline0_answer_only_questions': 543, 'baseline0_questions': 1319,
            'baseline0_eligible_for_pretraining_capability': False,
            'holdout_pass1_pass8_eligible_for_pretraining_capability': False}
        side.write_text(json.dumps(value, indent=2) + '\n')
        text = folder / 'README.md'
        with text.open('a') as f:
            f.write('\n4B GSM8K baseline note (46e98da5): use4-shot1216/1319=92.19%as the pretraining reference. '
                'The0-shotbaseline has543/1319answer-only outputs; its65.81%is not used as pretraining capability. '
                'The0-shotholdoutpass@1/pass@8 has40.5%answer-only outputs and is also excluded from capability inputs. '
                'See INTERPRETATION.json. Numeric results and labels are unchanged.\n')
        assert sha(result) == before
        subprocess.run(['git', 'add', str(side), str(text)], check=True)
        staged = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True).splitlines()
        assert set(staged) == {str(side), str(text)}
        subprocess.run(['git', 'diff', '--cached', '--check'], check=True)
        subprocess.run(['git', 'commit', '-m', 'P012: attach accepted4B GSM baseline interpretation ' + name], check=True)
        subprocess.run(['git', 'push', 'origin', 'codex/icml-acl-2027'], check=True)
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    event('annotated', run_id=name, commit=commit)
    return True


try:
    deadline = time.monotonic() + 72 * 3600
    event('started', scope='Nine original4BGSMcells; metadata and README only, no model calls')
    while len(done) < len(names):
        for name in names:
            if name not in done and annotate(name):
                done.add(name)
        if len(done) == len(names):
            break
        upstream = read(ROOT / 't_gsm_v1/TRAINING_QUEUE.json')['status']
        assert upstream == 'running', 'Upstream stopped; preserve unfinished annotation scope'
        assert time.monotonic() < deadline
        time.sleep(15)
    state['status'] = 'complete'; event('all_nine_annotated')
except BaseException as exc:
    state['status'] = 'stopped_for_inspection'; event('stopped', error=str(exc))
    traceback.print_exc(); raise
