"""Unattempted P010 C6 search: exact A2, published source and fresh I budget."""
from pathlib import Path
import modal
from experiments.p010.common import read

ROOT = Path(__file__).resolve().parents[2]
SPEC = 'reports/p010_20261019/c6_search_runtime_v1/SPEC.json'
spec = read(ROOT/SPEC)
app = modal.App('p010-cue-search')
volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
image = (modal.Image.debian_slim(python_version='3.12')
    .pip_install_from_requirements(ROOT/'experiments/learning_regime_p009/requirements_p0.txt')
    .env({'PYTHONPATH': '/workspace', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
          'TOKENIZERS_PARALLELISM': 'false',
          'VLLM_WORKER_MULTIPROC_METHOD': 'spawn', 'VLLM_USE_V1': '1',
          'CUBLAS_WORKSPACE_CONFIG': ':4096:8'}))
for name in list(spec['source_files'])+[SPEC]:
    image = image.add_local_file(ROOT/name, '/workspace/'+name, copy=True)


@app.function(image=image, gpu='H100!', cpu=(4, 4), memory=(32768, 32768),
    timeout=1860, startup_timeout=600, retries=0, max_containers=1,
    min_containers=0, buffer_containers=0, scaledown_window=2,
    single_use_containers=True, serialized=True, include_source=False,
    volumes={'/evidence': volume})
def worker(execution, approval, prior):
    import multiprocessing
    import time
    import traceback
    from experiments.p010.common import dump, sha, digest, utc
    from experiments.p010.runtime_support import source_check, hard_timer, compact
    from experiments.p010.cue_probability import validate_rows
    from experiments.p010.cue_proposal_process import child
    from experiments.p010.cue_search_contract import screen_rows, sampling, forecast, BATCHES
    start = time.time()
    stop = start+1800
    timer = hard_timer(1800)
    out = Path('/evidence/p010-20261019/cue/search_r1')
    input_file = Path('/evidence/p010-20261019/cue_inputs_r1/DEV_PROMPTS.json')
    store = modal.Dict.from_name('p010-once-20261019', create_if_missing=False)
    key = 'cue/search_r1'
    claimed = False
    try:
        s = read('/workspace/'+SPEC)
        source_check(s)
        volume.reload()
        if sha(input_file) != s['dev_input_sha256']:
            raise ValueError('Exact gold-free original thirty dev inputs required')
        dev = read(input_file)
        validate_rows(dev, 151936)
        initial = forecast(time.time()-start, 0, [], s['batch_observations_seconds'], prior,
                           proposal_complete=False)
        claim = dict(run='search_r1', execution=execution, epoch=start)
        if not store.put(key+'/claim', claim, skip_if_exists=True):
            raise RuntimeError('Original C6 search already attempted; no automatic retry')
        claimed = True
        out.mkdir(parents=True, exist_ok=False)
        dump(out/'INTENT.json', dict(claim=claim, execution=execution, approval=approval,
            worker_start_epoch=start, hard_deadline_epoch=stop, source_files=s['source_files'],
            dev_input_sha256=sha(input_file), prior_I_reserved_usd=prior,
            gold_used=False, correctness_used=False, training_updates=0))
        dump(out/'BEFORE_PROPOSAL_FORECAST.json', initial)
        dump(out/'DEV_PROMPTS.json', dev)
        volume.commit()
        ctx = multiprocessing.get_context('spawn')
        parent, remote = ctx.Pipe()
        proc = ctx.Process(target=child, args=(remote, str(input_file), str(out),
            s['model'], claim, stop))
        proc.start()
        remote.close()
        if not parent.poll(max(1, stop-time.time()-30)):
            raise TimeoutError('Original C6 proposal process deadline')
        kind, value = parent.recv()
        proc.join(timeout=max(1, min(30, stop-time.time()-15)))
        if kind != 'complete' or proc.is_alive() or proc.exitcode != 0:
            raise RuntimeError('Original proposal process failed or did not exit: '+str(value))
        volume.reload()
        dump(out/'PROPOSAL_EXIT.json', dict(pid=proc.pid, exitcode=proc.exitcode,
            joined_before_vllm=True))
        proposal = read(out/'PROPOSAL.json')
        rows = screen_rows(dev, proposal, read(out/'ALLOWED_CUE_TOKENS.json'))
        dump(out/'SCREEN_ROSTER.json', rows)
        volume.commit()
        from vllm import LLM, SamplingParams
        from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs, actual_engine
        from experiments.learning_regime_p009.stage0_generation_engine_v2 import returned_records
        params = [sampling(r['rollout']) for r in rows]
        actual_params = [SamplingParams(**p) for p in params]
        dump(out/'BEFORE_SCREEN_FORECAST.json', forecast(time.time()-start, 0, [],
            s['batch_observations_seconds'], prior, proposal_complete=True))
        volume.commit()
        llm = LLM(model=s['model']['remote_path'], tokenizer=s['model']['tokenizer_remote_path'],
                  **engine_kwargs())
        dump(out/'ENGINE.json', actual_engine(llm.llm_engine.vllm_config))
        volume.commit()
        times = []
        for offset in range(0, len(rows), 256):
            unit = f'{offset:05d}'
            part = rows[offset:offset+256]
            part_params = params[offset:offset+256]
            f = forecast(time.time()-start, len(times), times, s['batch_observations_seconds'],
                         prior, proposal_complete=True)
            if store.get(key+'/claim') != claim:
                raise RuntimeError('Original C6 claim changed')
            dump(out/'screen_forecasts'/(unit+'.json'), f)
            intent = dict(rows=part, sampling=part_params, epoch=time.time())
            if not store.put(key+'/screen/'+unit, intent, skip_if_exists=True):
                raise RuntimeError('Original development batch already attempted')
            dump(out/'screen_intents'/(unit+'.json'), intent)
            volume.commit()
            tick = time.monotonic()
            outputs = llm.generate([dict(prompt_token_ids=r['input_ids']) for r in part],
                actual_params[offset:offset+256], use_tqdm=False)
            raw = returned_records(part, part_params, outputs)
            dump(out/'raw'/(unit+'.json'), raw)
            volume.commit()
            if (len(raw) != len(part) or any(x['output_count'] != 1
                    or x['candidate_id'] != row['candidate_id']
                    or x['prompt_token_ids'] != row['input_ids'] for x, row in zip(raw, part))):
                raise ValueError('Original development raw identity differs')
            ack = dict(count=len(part), seconds=time.monotonic()-tick, raw_sha256=digest(raw))
            times.append(ack['seconds'])
            dump(out/'screen_acks'/(unit+'.json'), ack)
            if not store.put(key+'/screen_done/'+unit, ack, skip_if_exists=True):
                raise RuntimeError('Original development acknowledgment already exists')
            volume.commit()
        if len(times) != BATCHES:
            raise ValueError('Incomplete original development roster')
        result = dict(run='search_r1', raw_development_outputs=len(rows), candidates=21,
            dev_questions=30, rollouts=16, proposal_prefix_measurements=21,
            new_training_updates=0, gold_used=False, correctness_used=False, test_data_used=False,
            screen_batch_seconds=times, seconds=time.time()-start,
            selected_cue=None, selection='Pending complete local raw audit and gold-free entropy selection')
        dump(out/'RESULT.json', result)
        volume.commit()
        packed = compact(out)
        volume.commit()
        terminal = dict(status='completed', finished_utc=utc(), result=result,
            artifact=packed, seconds_including_pack=time.time()-start)
        dump(out/'TERMINAL.json', terminal)
        volume.commit()
        if not store.put(key+'/terminal', terminal, skip_if_exists=True):
            raise RuntimeError('Original C6 terminal already exists')
        return terminal
    except BaseException as exc:
        if claimed and out.exists():
            dump(out/'FAILURE.json', dict(type=type(exc).__name__, error=str(exc),
                traceback=traceback.format_exc(), utc=utc(), retry=False))
            volume.commit()
            store.put(key+'/terminal', dict(status='failed', error=str(exc)), skip_if_exists=True)
        raise
    finally:
        if 'proc' in locals() and proc.is_alive():
            proc.kill()
            proc.join(timeout=5)
        timer.cancel()


@app.local_entrypoint()
def main(receipt_dir:str, review_json:str, budget_json:str):
    import datetime
    import fcntl
    import json
    import subprocess
    import time
    from collections import Counter
    from concurrent.futures import ThreadPoolExecutor
    from decimal import Decimal
    from experiments.p010.common import dump, sha, require_published
    from experiments.p010.runtime_support import source_check
    from experiments.p010.student_dispatch_v2 import original_T_records
    from experiments.p010.cue_search_contract import forecast
    if time.time()+2500 > datetime.datetime(2026,10,21,19,tzinfo=datetime.timezone.utc).timestamp():
        raise ValueError('Full original C6 window must precede the result cutoff')
    execution = require_published(ROOT)
    source_check(spec, ROOT)
    review, b = read(review_json), read(budget_json)
    if (review.get('decision') not in ('PASS', 'PASS-WITH-NOTES')
            or review.get('scope') != 'p010-C6-search-input-runtime-and-selection-A2'
            or review.get('spec_sha256') != sha(ROOT/SPEC)
            or sha(review['local_report_file']) != review['report_sha256']):
        raise ValueError('Exact complete C6 A2 required before the original search')
    if (b.get('category') != 'I' or b.get('cap_usd') != '15'
            or b.get('reserve_release_used') is not False
            or not 0 <= time.time()-b['observed_epoch'] <= 3600):
        raise ValueError('Fresh original I-category reservation budget required')
    root = ROOT/'.local/p010_20261019/r1'
    uploaded = read(root/'cue_input_upload_r1/COMPLETED.json')
    if uploaded.get('dev_input_sha256') != spec['dev_input_sha256']:
        raise ValueError('Original input upload/readback required')
    prior = str(Decimal(b['prior_attempted_reserved_usd']))
    initial = forecast(0, 0, [], spec['batch_observations_seconds'], prior, proposal_complete=False)
    with (root/'student_dispatch.lock').open('a+') as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        out = Path(receipt_dir)
        if out.resolve() != (root/'cue_search_runs/search_r1').resolve():
            raise ValueError('Original canonical search receipt required')
        inference = list(root.glob('cue_*_runs/*/INTENT.json'))
        actual = sum((Decimal(read(p)['budget']['new_reserved_usd']) for p in inference), Decimal('0'))
        if actual != Decimal(prior):
            raise ValueError('All previous I reservations must remain included')
        records = original_T_records(root)+inference
        cli = str(ROOT/'.local/midpoint_20261011/venv/bin/modal')
        containers = json.loads(subprocess.check_output([cli,'container','list','--json'],
            text=True, timeout=45))
        apps = [read(p.parent/'SUBMITTED.json')['app_id'] for p in records
                if (p.parent/'SUBMITTED.json').exists()]
        if len(apps) != len(set(apps)):
            raise ValueError('Ambiguous original submitted app binding')

        def state(app_id):
            try:
                info = json.loads(subprocess.check_output([cli,'app','info',app_id,'--json'],
                    text=True, timeout=45, stderr=subprocess.PIPE))
                if info['app_id'] != app_id:
                    raise ValueError('Provider identity differs')
                return app_id, info['lifecycle']['state']
            except Exception:
                return app_id, 'unknown'

        with ThreadPoolExecutor(max_workers=2) as readers:
            states = dict(readers.map(state, apps))
        counts = Counter(x.get('app_id') for x in containers)
        slots = sum(not (p.parent/'SUBMITTED.json').exists() for p in records)
        for app_id in apps:
            count = counts.pop(app_id, 0)
            slots += count if str(states.get(app_id,'unknown')).lower() == 'stopped' else max(1,count)
        slots += sum(counts.values())
        if slots >= 4:
            raise ValueError('Shared four-container scope includes pending/unknown/unmatched work')
        out.mkdir(parents=True, exist_ok=False)
        approval = {k:v for k,v in review.items() if k != 'local_report_file'}
        dump(out/'INTENT.json', dict(run='search_r1', execution=execution, epoch=time.time(),
            budget=initial['budget'], budget_source_sha256=sha(budget_json), approval=approval,
            admission_provider_states=states, admission_slots=slots))
        call = worker.spawn(execution, approval, prior)
        dump(out/'SUBMITTED.json', dict(run='search_r1', app_id=app.app_id, call_id=call.object_id))
    try:
        dump(out/'RESULT.json', call.get())
    except BaseException as exc:
        dump(out/'ERROR.json', dict(type=type(exc).__name__, error=str(exc)))
        raise
