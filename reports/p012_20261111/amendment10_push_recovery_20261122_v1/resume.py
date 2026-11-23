"""Resume an unpublished S1 admission; unchanged paid/selection functions.

Owner authorized recovery on 2026-11-22. Never repeat a completed paid batch.
No training, baseline, account change, or automatic experiment retry.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, '.')
HERE = Path(__file__).resolve().parent.relative_to(Path.cwd())
CONTROLLER = Path('reports/p012_20261111/amendment10_s1_addenda_v1/continue_s1.py')
spec = importlib.util.spec_from_file_location('accepted_s1_continuation', CONTROLLER)
cont = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cont)
s1 = cont.s1
read, sha = cont.read, cont.sha


def record(value):
    value['utc'] = cont.utc()
    s1.write(HERE/'STATUS.json', value, exclusive=False)


def main():
    with s1.lock('A10_S1_OWNER_RECOVERY.lock'):
        assert not (HERE/'STATUS.json').exists(), 'This one-time recovery was already invoked'
        cont.check_sources()
        assert Path(__file__).read_bytes() == subprocess.check_output(['git','show','HEAD:'+str(HERE/'resume.py')])
        for filename, expected in read('reports/p012_20261111/amendment10_completion_preparation_v1/SOURCES.json').items():
            assert sha(filename) == expected, filename
        state = read(cont.LOCAL/'RECOVERY_QUEUE.json')
        assert state == read(HERE/'STOPPED_QUEUE.json')
        assert state['qualified_rows'] == 3981 and len(state['completed_batches']) == 8
        assert state['status'] == 'stopped_for_inspection'
        assert state['active_batch']['run_id'] == 'a10_s1_batch09_v1'
        manifest = read(cont.BASE/'MANIFEST.json')
        assert sha(cont.LOCAL/'ALL_INPUTS_PRIVATE.json') == manifest['private_input_sha256']
        rows = read(cont.LOCAL/'ALL_INPUTS_PRIVATE.json')
        os.environ['TINKER_API_KEY'] = (s1.ROOT/'credentials/tinker_api_key').read_text().strip()
        state.pop('error')
        state.update(status='running', recovery_authority='owner instruction 2026-11-22',
                     recovery_source_sha256=sha(__file__))
        try:
            for start in range(4800, len(rows), 600):
                if state['qualified_rows'] >= 4300:
                    break
                cont.check_sources()
                batch = rows[start:start+600]
                name = f'a10_s1_batch{start//600+1:02d}_v1'
                directory = cont.LOCAL/'batches'/name
                public = cont.BASE/'batches'/name
                used = state['successful_attempts_token_cost_usd'] + state['failed_attempt_reserve_usd']
                forecast = max(x['token_cost_usd']/x['rows'] for x in state['completed_batches'])*len(batch)*1.5
                with s1.lock('BUDGET_ADMISSION.lock'):
                    assert state['no_other_A10_jobs'] is True
                    assert used+forecast <= 100 and used+forecast <= 200
                    if start == 4800:
                        request = read(public/'REQUEST.json')
                        assert (directory/'REQUEST.json').read_bytes() == (public/'REQUEST.json').read_bytes()
                        assert (public/'REQUEST.json').read_bytes() == subprocess.check_output(['git','show','HEAD:'+str(public/'REQUEST.json')])
                        assert request['global_start'] == start and request['rows'] == len(batch)
                        assert request['forecast_usd'] == forecast
                        assert not (directory/'result').exists(), 'Paid-call evidence appeared; inspect before acting'
                    else:
                        assert not directory.exists() and not public.exists()
                        directory.mkdir(parents=True); public.mkdir(parents=True)
                        s1.write(public/'INPUT_IDENTITIES.json', [s1.safe(r) for r in batch])
                        request = dict(read(cont.BASE/'batches/a10_s1_batch09_v1/REQUEST.json'))
                        request.update(utc=cont.utc(), run_id=name, global_start=start, rows=len(batch),
                            safe_inputs_sha256=sha(public/'INPUT_IDENTITIES.json'), forecast_usd=forecast,
                            prior_accounted_and_failed_reserve_usd=used,
                            recovery_source_sha256=sha(__file__))
                        s1.write(public/'REQUEST.json', request)
                        s1.write(directory/'REQUEST.json', request, True)
                    assert [s1.safe(r) for r in batch] == read(public/'INPUT_IDENTITIES.json')
                    assert sha(public/'INPUT_IDENTITIES.json') == request['safe_inputs_sha256']
                    state['active_batch'] = {'run_id':name, 'forecast_usd':forecast}
                    cont.record(state)
                    record({'status':'running', 'run_id':name, 'budget_with_next_usd':used+forecast,
                        'no_duplicate_generation':True, 'training_started':False})
                    s1.publish([HERE, public, cont.PUBLIC/'CURRENT_STATUS.json'],
                        'P012 A10: resume owner-authorized frozen admission '+name)
                s1.generate(batch, request, directory/'result')
                cont.complete_batch(batch, directory, public, manifest, state)
            assert state['qualified_rows'] >= 4300 or sum(x['rows'] for x in state['completed_batches']) == len(rows)
            assert state['qualified_rows'] >= 4096
            state['status'] = 'generation_complete_data_and_training_review_required'
            cont.record(state)
            record({'status':'generation_complete', 'qualified_rows':state['qualified_rows'], 'training_started':False})
            s1.publish([HERE, cont.PUBLIC/'CURRENT_STATUS.json'], 'P012 A10: S1 completed after push recovery')
        except BaseException as exc:
            state.update(status='stopped_for_inspection', error=str(exc))
            cont.record(state)
            record({'status':'stopped_for_inspection', 'reason':str(exc), 'training_started':False})
            s1.publish([HERE, cont.PUBLIC/'CURRENT_STATUS.json'], 'P012 A10: preserve recovery stop without retry')
            raise
        try:
            for script in ['freeze_data.py','prepare_requests.py','package_review.py']:
                for filename, expected in read('reports/p012_20261111/amendment10_completion_preparation_v1/SOURCES.json').items():
                    assert sha(filename) == expected, filename
                subprocess.run(['.local/p012_20261111/venv/bin/python',
                    str(Path('reports/p012_20261111/amendment10_training_review_v1')/script)], check=True)
            record({'status':'combined_review_ready', 'training_started':False,
                'review_packet':'reports/p012_20261111/amendment10_combined_training_review_v1/README.md',
                'prepared_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()})
            s1.publish([HERE], 'P012 A10: completed recovery and combined pretraining review packet')
        except BaseException as exc:
            record({'status':'CPU_preparation_stopped', 'reason':str(exc), 'training_started':False})
            s1.publish([HERE], 'P012 A10: preserve CPU preparation stop; completed generation retained')
            raise


if __name__ == '__main__':
    main()
