"""Continue S1 from batch2 under accepted A10 addenda1/2.

The audited first batch remains immutable. Generation and selection are frozen;
only the accepted CPU length guard and budget limits differ. No model retries.
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

LENGTH_REVIEW = 'f0369f2590dfd4f70dab909c81a9d386bde672ae'
CAP_AUTHORITY = 'c9a534808e65ec648da1995ba26ee52929509de9'
LENGTH_SOURCE = Path('reports/p012_20261111/amendment10_overlength_review_v1/proposed_tinker_lora.py')
LENGTH_SOURCE_SHA = '3360ca269fe2962638d041ef678720ce6a8276dfd794f08ea9776e50197d96a4'
length_spec = importlib.util.spec_from_file_location('experiments.p012.a10_length_cpu', LENGTH_SOURCE)
length_module = importlib.util.module_from_spec(length_spec)
length_spec.loader.exec_module(length_module)

def render_logiqa_8192(row, tokenizer, renderer):
    return length_module.rendered_datum(row, tokenizer, renderer, max_length=8192)

# The frozen qualifier resolves only this CPU rendering dependency differently.
# No training or service client is invoked by this function.
s1.rendered_datum = render_logiqa_8192


def check_sources():
    assert sha(BASE/'s1.py') == SOURCE_SHA
    assert sha(LENGTH_SOURCE) == LENGTH_SOURCE_SHA
    assert read(PUBLIC/'AUTHORITY.json')['S1_cap_usd'] == 100
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
              'controller_sha256':sha(__file__),'length_review_commit':LENGTH_REVIEW,
              'cap_authority_commit':CAP_AUTHORITY,'training_max_length':8192,'raw_sha256':sha(directory/'result/raw.jsonl'),
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
    assert not result['overlength_training_samples'],'Selected training sample exceeds8192: stop and report'
    assert state['successful_attempts_token_cost_usd']+state['failed_attempt_reserve_usd'] <= 100


def main():
    check_sources()
    manifest = read(BASE/'MANIFEST.json')
    assert sha(LOCAL/'ALL_INPUTS_PRIVATE.json') == manifest['private_input_sha256']
    assert read(BASE/'OWNER_BUDGET_DECISION.json')['A10_independent_cap_usd'] == 200
    rows = read(LOCAL/'ALL_INPUTS_PRIVATE.json')
    previous = read(LOCAL/'RECOVERY_QUEUE.json')
    assert previous['status'] == 'stopped_for_inspection'
    assert previous['error'] == 'Selected training sample exceeds4096: stop and report'
    assert previous['active_batch'] is None
    assert len(previous['completed_batches']) == 1 and previous['qualified_rows'] == 501
    first = previous['completed_batches'][0]
    assert first['rows'] == 600
    assert sha(Path(first['private_directory'])/'result/raw.jsonl') == first['raw_sha256']
    assert read(PUBLIC/'AUDIT_STATUS.json')['accepted_review_commit'] == LENGTH_REVIEW
    assert previous['automatic_retries_remaining'] == 0
    assert previous['no_other_A10_jobs'] is True
    state = dict(previous)
    state.pop('error')
    state.update(status='ready_to_resume_batch2', controller_sha256=sha(__file__),
        length_review_commit=LENGTH_REVIEW, cap_authority_commit=CAP_AUTHORITY,
        training_max_length=8192, S1_cap_usd=100, A10_independent_cap_usd=200,
        generation_source_sha256=SOURCE_SHA, CPU_render_source_sha256=LENGTH_SOURCE_SHA)
    state['completed_batches'][0]['token_counts_addendum'] = str(PUBLIC/'FIRST_BATCH_COUNTS_ADDENDUM.json')
    record(state)
    os.environ['TINKER_API_KEY'] = (s1.ROOT/'credentials/tinker_api_key').read_text().strip()
    try:
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
                assert state['no_other_A10_jobs'] is True
                assert used+forecast <= 100 and used+forecast <= 200,'S1 budget admission failed: stop'
                directory.mkdir(parents=True);public.mkdir(parents=True)
                s1.write(public/'INPUT_IDENTITIES.json',[s1.safe(r) for r in batch])
                request = {'utc':utc(),'run_id':name,'authority_commit':s1.AUTHORITY,
                    'length_review_commit':LENGTH_REVIEW,'cap_authority_commit':CAP_AUTHORITY,
                    'training_max_length':8192,'CPU_render_source_sha256':LENGTH_SOURCE_SHA,
                    'source_sha256':SOURCE_SHA,'controller_sha256':sha(__file__),
                    'teacher':manifest['teacher'],'global_start':start,'rows':len(batch),'n':8,
                    'max_tokens':4096,'temperature':.7,'top_p':1,'seed_formula':manifest['seed_formula'],
                    'prices_per_million':manifest['teacher']['prices_per_million'],
                    'safe_inputs_sha256':sha(public/'INPUT_IDENTITIES.json'),
                    'forecast_usd':forecast,'forecast_basis':'Maximum completed-batch token cost per row times1.5',
                    'prior_accounted_and_failed_reserve_usd':used,'S1_cap_usd':100,'A10_independent_cap_usd':200,
                    'no_other_A10_jobs_started':True}
                s1.write(public/'REQUEST.json',request);s1.write(directory/'REQUEST.json',request,True)
                state.update(status='running',active_batch={'run_id':name,'forecast_usd':forecast})
                record(state)
                s1.publish([public,PUBLIC/'CURRENT_STATUS.json'],'P012 A10 S1: admit frozen batch under accepted addenda '+name)
            s1.generate(batch,request,directory/'result')
            complete_batch(batch,directory,public,manifest,state)
        assert state['qualified_rows'] >= 4096,'Exhausted rows below4096: stop'
        state['status'] = 'generation_complete_data_and_training_review_required'
        record(state)
        s1.publish([PUBLIC/'CURRENT_STATUS.json'],'P012 A10 S1: generation complete; combined training review required')
    except BaseException as exc:
        state.update(status='stopped_for_inspection',error=str(exc))
        record(state)
        s1.publish([PUBLIC/'CURRENT_STATUS.json'],'P012 A10 S1: stop and preserve evidence; no automatic retry')
        traceback.print_exc()
        raise

if __name__ == '__main__':
    main()
