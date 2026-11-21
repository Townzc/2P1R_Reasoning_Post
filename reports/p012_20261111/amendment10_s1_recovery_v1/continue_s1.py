"""Continue the authorized S1 queue through unchanged generation/selection functions.

The separately launched, single infrastructure retry must finish first. This
controller never retries a model call, trains a model, or changes source data.
"""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

sys.path.insert(0, '.')
BASE = Path('reports/p012_20261111/amendment10_s1_v1')
PUBLIC = Path(__file__).resolve().parent.relative_to(Path.cwd())
LOCAL = Path('.local/p012_20261111/amendment10_v1')
SOURCE_SHA = '1b113ab6ab5af4b465f93dd207820a7a8cd9a921df75d39c4f611ae16199cb74'
read = lambda p: json.loads(Path(p).read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
spec = importlib.util.spec_from_file_location('frozen_s1', BASE/'s1.py')
s1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s1)


def check_sources():
    assert sha(BASE/'s1.py') == SOURCE_SHA
    for p,h in read(BASE/'DEPENDENCIES.json').items():
        assert sha(p) == h
    own = Path(__file__).resolve().relative_to(Path.cwd())
    assert own.read_bytes() == subprocess.check_output(['git','show','HEAD:'+str(own)])


def record(state):
    state['utc'] = utc()
    s1.write(LOCAL/'RECOVERY_QUEUE.json',state,True,False)
    s1.write(PUBLIC/'CURRENT_STATUS.json',state,exclusive=False)


def complete_batch(rows, directory, public, manifest, state, compare_failed=False):
    check_sources()
    assert read(directory/'result/COMPLETE.json')['success']
    freeze = {'utc':utc(),'authority_commit':s1.AUTHORITY,'generation_source_sha256':SOURCE_SHA,
              'controller_sha256':sha(__file__),'raw_sha256':sha(directory/'result/raw.jsonl'),
              'selection_rule':'at least4correct; first4whitespace-distinct correct by draw; fixed4300pool stopping'}
    prediction=public/'PREDICTION_BEFORE_SCORE.json'
    if prediction.exists():
        previous=read(prediction)
        assert previous['authority_commit']==s1.AUTHORITY and previous['generation_source_sha256']==SOURCE_SHA
        assert previous['raw_sha256']==freeze['raw_sha256']
    else:
        s1.write(prediction,freeze)
    s1.publish([public/'PREDICTION_BEFORE_SCORE.json'],'P012 A10 S1: bind frozen selection before scoring '+directory.name)
    if compare_failed:
        old = [json.loads(x) for x in (LOCAL/'batches/a10_s1_batch01_v1/result/raw.jsonl').read_text().splitlines()]
        new = [json.loads(x) for x in (directory/'result/raw.jsonl').read_text().splitlines()]
        matches = 0
        for a,b in zip(old,new[:len(old)],strict=True):
            assert (a['id'],a['draw'],a['sampling_seed']) == (b['id'],b['draw'],b['sampling_seed'])
            matches += (a['text'],a['token_ids']) == (b['text'],b['token_ids'])
        s1.write(public/'RETRY_COMPARISON.json',{'compared':len(old),'identical_text_and_tokens':matches,
            'policy':'Complete retry chosen before scoring, regardless of differences; failed attempt retained'})
    result,qualified = s1.qualify(rows,directory,manifest['student'])
    s1.archive_batch(directory,public)
    cost = read(directory/'result/USAGE.json')['upper_token_cost_usd']
    state['successful_attempts_token_cost_usd'] += cost
    state['qualified_rows'] += len(qualified)
    state['completed_batches'].append({'run_id':directory.name,'rows':len(rows),
        'qualified':len(qualified),'token_cost_usd':cost,'raw_sha256':result['raw_sha256'],
        'private_directory':str(directory),'public_directory':str(public)})
    state['active_batch'] = None
    record(state)
    s1.publish([public,PUBLIC/'CURRENT_STATUS.json'],'P012 A10 S1: preserve complete batch '+directory.name)
    assert result['eight_identical_questions'] <= len(rows)/2,'Majority eight-identical: stop'
    assert not result['overlength_training_samples'],'Selected training sample exceeds4096: stop and report'
    assert state['successful_attempts_token_cost_usd']+state['failed_attempt_reserve_usd'] <= 75


def main():
    check_sources()
    manifest = read(BASE/'MANIFEST.json')
    assert sha(LOCAL/'ALL_INPUTS_PRIVATE.json') == manifest['private_input_sha256']
    assert read(BASE/'OWNER_BUDGET_DECISION.json')['A10_independent_cap_usd'] == 200
    rows = read(LOCAL/'ALL_INPUTS_PRIVATE.json')
    if (LOCAL/'RECOVERY_QUEUE.json').exists():
        previous=read(LOCAL/'RECOVERY_QUEUE.json')
        assert previous['status']=='stopped_for_inspection' and previous['completed_batches']==[]
        assert read(PUBLIC/'PUBLICATION_PATH_FIX.json')['no_scoring_or_extra_model_calls_before_fix']
        assert not (LOCAL/'a10_s1_batch01_infra_retry1_v1/labels.jsonl').exists()
    retry = LOCAL/'a10_s1_batch01_infra_retry1_v1'
    admission = read(PUBLIC/'ADMISSION.json')
    state = {'utc':utc(),'status':'awaiting_existing_first_batch_retry','authority_commit':s1.AUTHORITY,
        'generation_source_sha256':SOURCE_SHA,'controller_sha256':sha(__file__),
        'infrastructure_retry_used':1,'automatic_retries_remaining':0,
        'failed_attempt_reserve_usd':admission['original_attempt_reserved_usd'],
        'successful_attempts_token_cost_usd':0,'qualified_rows':0,'completed_batches':[],
        'active_batch':{'run_id':retry.name,'forecast_usd':admission['next_attempt_forecast_with_1_5_margin_usd']},
        'S1_cap_usd':75,'A10_independent_cap_usd':200,'no_other_A10_jobs':True}
    record(state)
    os.environ['TINKER_API_KEY']=(s1.ROOT/'credentials/tinker_api_key').read_text().strip()
    try:
        while not (retry/'result/COMPLETE.json').exists():
            assert not (retry/'result/PARTIAL_USAGE.json').exists(),'First retry failed: stop'
            assert 'Traceback' not in (retry/'run.log').read_text(),'First retry exception: stop'
            os.kill(read(retry/'LAUNCH.json')['pid'],0)
            time.sleep(30)
        complete_batch(rows[:600],retry,PUBLIC,manifest,state,True)
        for start in range(600,len(rows),600):
            if state['qualified_rows'] >= 4300:
                break
            check_sources()
            batch = rows[start:start+600]
            name = f'a10_s1_batch{start//600+1:02d}_v1'
            directory = LOCAL/'batches'/name
            public = BASE/'batches'/name
            assert not directory.exists() and not public.exists(),'Refuse duplicate batch'
            forecast = max(x['token_cost_usd']/x['rows'] for x in state['completed_batches'])*len(batch)*1.5
            used = state['successful_attempts_token_cost_usd']+state['failed_attempt_reserve_usd']
            with s1.lock('BUDGET_ADMISSION.lock'):
                assert used+forecast <= 75 and used+forecast <= 200,'S1 budget admission failed: stop'
                directory.mkdir(parents=True);public.mkdir(parents=True)
                s1.write(public/'INPUT_IDENTITIES.json',[s1.safe(r) for r in batch])
                request = {'utc':utc(),'run_id':name,'authority_commit':s1.AUTHORITY,
                    'source_sha256':SOURCE_SHA,'controller_sha256':sha(__file__),
                    'teacher':manifest['teacher'],'global_start':start,'rows':len(batch),'n':8,
                    'max_tokens':4096,'temperature':.7,'top_p':1,'seed_formula':manifest['seed_formula'],
                    'prices_per_million':manifest['teacher']['prices_per_million'],
                    'safe_inputs_sha256':sha(public/'INPUT_IDENTITIES.json'),
                    'forecast_usd':forecast,'forecast_basis':'Maximum completed-batch token cost per row times1.5',
                    'prior_accounted_and_failed_reserve_usd':used,'S1_cap_usd':75,'A10_independent_cap_usd':200,
                    'no_other_A10_jobs_started':True}
                s1.write(public/'REQUEST.json',request);s1.write(directory/'REQUEST.json',request,True)
                state.update(status='running',active_batch={'run_id':name,'forecast_usd':forecast})
                record(state)
                s1.publish([public,PUBLIC/'CURRENT_STATUS.json'],'P012 A10 S1: admit next original frozen batch '+name)
            s1.generate(batch,request,directory/'result')
            complete_batch(batch,directory,public,manifest,state)
        assert state['qualified_rows'] >= 4096,'Exhausted rows below4096: stop'
        state['status']='generation_complete_data_and_training_review_required'
        record(state)
        s1.publish([PUBLIC/'CURRENT_STATUS.json'],'P012 A10 S1: generation complete; data and training review remains')
    except BaseException as exc:
        state.update(status='stopped_for_inspection',error=str(exc))
        record(state)
        s1.publish([PUBLIC/'CURRENT_STATUS.json'],'P012 A10 S1: preserve stopped condition; no further retry')
        traceback.print_exc()
        raise


if __name__ == '__main__':
    main()
