"""Frozen P010 student cells, one call each; A1 data and exact A2 precede dispatch."""
from pathlib import Path
import modal
from experiments.p010.common import read

ROOT = Path(__file__).resolve().parents[2]
SPEC = 'reports/p010_20261019/seed29_runtime_v1/SPEC.json'
spec = read(ROOT/SPEC)
app = modal.App('p010-original-seed29-students')
volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
image = (modal.Image.debian_slim(python_version='3.12')
    .pip_install_from_requirements(ROOT/'experiments/learning_regime_p009/requirements_p0.txt')
    .env({'PYTHONPATH': '/workspace', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
          'TOKENIZERS_PARALLELISM': 'false', 'VLLM_WORKER_MULTIPROC_METHOD': 'spawn',
          'VLLM_USE_V1': '1', 'CUBLAS_WORKSPACE_CONFIG': ':4096:8'}))
for name in list(spec['source_files'])+[SPEC]:
    image = image.add_local_file(ROOT/name, '/workspace/'+name, copy=True)


@app.function(image=image, gpu='H100!', cpu=(4, 4), memory=(32768, 32768),
    timeout=4560, startup_timeout=600, retries=0, max_containers=4,
    min_containers=0, buffer_containers=0, scaledown_window=2,
    single_use_containers=True, serialized=True, include_source=False,
    volumes={'/evidence': volume})
def worker(run, execution, reviews, prior):
    import multiprocessing
    import time
    import traceback
    from experiments.p010.common import dump, read, verify, digest, utc
    from experiments.p010.runtime_support import source_check, hard_timer, compact
    from experiments.p010.student_contract import CELLS, evaluation_jobs, sampling, forecast
    from experiments.p010.student_process import child
    start = time.time()
    stop = start+4500
    timer = hard_timer(4500)
    out = Path('/evidence/p010-20261019/students')/run
    inputs = Path('/evidence/p010-20261019/student_inputs')
    store = modal.Dict.from_name('p010-once-20261019', create_if_missing=False)
    key = 'student/'+run
    claimed = False
    try:
        s = read('/workspace/'+SPEC)
        source_check(s)
        if run not in CELLS or run not in s['configs']:
            raise ValueError('No exact A1-reviewed input for this frozen cell')
        claim = dict(run=run, execution=execution, epoch=start)
        if not store.put(key+'/claim', claim, skip_if_exists=True):
            raise RuntimeError('Already attempted student; no automatic retry')
        claimed = True
        volume.reload()
        out.mkdir(parents=True, exist_ok=False)
        verify(inputs, {n:v for n,v in s['input_files'].items() if n.startswith(run+'/') or n=='MATH_ENDPOINT.json'})
        config = read(inputs/run/'config.json')
        if config != s['configs'][run]:
            raise ValueError('Exact input recipe differs')
        identity = dict(run_id=run, config=config, execution=execution,
            source_files=s['source_files'], input_files=s['input_files'],
            base_files=s['model']['files'], reviews=reviews)
        dump(out/'INTENT.json', dict(identity=identity, claim=claim,
            worker_start_epoch=start, hard_deadline_epoch=stop, prior_T_reserved_usd=prior))
        volume.commit()
        ctx = multiprocessing.get_context('spawn')
        parent, remote = ctx.Pipe()
        proc = ctx.Process(target=child, args=(remote, str(inputs/run), str(out),
            s['model'], identity, claim, start, stop, s['timing'], prior))
        proc.start()
        remote.close()
        if not parent.poll(max(1, stop-time.time()-30)):
            raise TimeoutError('Training child original deadline')
        kind, value, times = parent.recv()
        proc.join(timeout=max(1, min(30, stop-time.time()-15)))
        if kind != 'complete' or proc.is_alive() or proc.exitcode != 0:
            raise RuntimeError('Training child failed or did not exit: '+str(value))
        volume.reload()
        dump(out/'TRAINING_EXIT.json', dict(pid=proc.pid, exitcode=proc.exitcode,
            joined_before_vllm=True))
        volume.commit()
        from vllm import LLM, SamplingParams
        from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs, actual_engine
        from experiments.learning_regime_p009.stage0_generation_engine_v2 import returned_records
        llm = LLM(model=str(out/'merged'), tokenizer=str(out/'merged'), **engine_kwargs())
        dump(out/'ENGINE.json', actual_engine(llm.llm_engine.vllm_config))
        rows = read(inputs/'MATH_ENDPOINT.json')
        if len(rows) != 500 or len({r['candidate_id'] for r in rows}) != 500:
            raise ValueError('Original full MATH500 endpoint required')
        completed = 0
        endpoint_times = []
        for job in evaluation_jobs():
            for first in range(0, len(rows), 256):
                f = forecast(time.time()-start, 0, 10-completed,
                    s['timing']['training_seconds']+times,
                    s['timing']['endpoint_seconds']+endpoint_times, prior)
                unit = job[0]+f'/{first:04d}'
                dump(out/'eval_forecasts'/(unit+'.json'), f)
                if store.get(key+'/claim') != claim:
                    raise RuntimeError('Original claim changed')
                part = rows[first:first+256]
                params = [sampling(job) for _ in part]
                intent = dict(rows=part, sampling=params, epoch=time.time(), evaluation=job[0])
                if not store.put(key+'/eval/'+unit, intent, skip_if_exists=True):
                    raise RuntimeError('Endpoint batch was already attempted')
                dump(out/'eval_intents'/(unit+'.json'), intent)
                volume.commit()
                tick = time.monotonic()
                output = llm.generate([{'prompt_token_ids': r['input_ids']} for r in part],
                    [SamplingParams(**x) for x in params], use_tqdm=False)
                raw = returned_records(part, params, output)
                dump(out/'raw'/(unit+'.json'), raw)
                volume.commit()
                if (len(raw) != len(part) or any(x['output_count'] != 1
                        or x['candidate_id'] != r['candidate_id']
                        or x['prompt_token_ids'] != r['input_ids'] for r, x in zip(part, raw))):
                    raise ValueError('Original complete raw endpoint identity differs')
                ack = dict(count=len(part), seconds=time.monotonic()-tick,
                    raw_sha256=digest(raw), evaluation=job[0])
                endpoint_times.append(ack['seconds'])
                dump(out/'eval_acks'/(unit+'.json'), ack)
                store.put(key+'/eval_done/'+unit, ack, skip_if_exists=True)
                volume.commit()
                completed += 1
        result = dict(run=run, training=value, raw_endpoint_count=2500,
            unique_questions=500, evaluations=[x[0] for x in evaluation_jobs()],
            eval_batch_seconds=endpoint_times, seconds=time.time()-start,
            score='Not scored on GPU; original frozen CPU scorer and A3 required')
        dump(out/'RESULT.json', result)
        volume.commit()
        packed = compact(out)
        volume.commit()
        terminal = dict(status='completed', finished_utc=utc(), result=result,
            artifact=packed, seconds_including_pack=time.time()-start)
        dump(out/'TERMINAL.json', terminal)
        volume.commit()
        store.put(key+'/terminal', terminal, skip_if_exists=True)
        return terminal
    except BaseException as e:
        if claimed and out.exists():
            dump(out/'FAILURE.json', dict(type=type(e).__name__, error=str(e),
                traceback=traceback.format_exc(), utc=utc(), retry=False))
            volume.commit()
            store.put(key+'/terminal', dict(status='failed', error=str(e)), skip_if_exists=True)
        raise
    finally:
        if 'proc' in locals() and proc.is_alive():
            proc.kill()
            proc.join(timeout=5)
        timer.cancel()


@app.local_entrypoint()
def main(run:str, receipt_dir:str, data_review_json:str, runtime_review_json:str,
         a4_report_json:str, actual_results_review_json:str, budget_json:str):
    import fcntl, time, datetime, json, subprocess
    from decimal import Decimal
    from concurrent.futures import ThreadPoolExecutor
    from experiments.p010.common import dump, sha, require_published, budget_check
    from experiments.p010.runtime_support import source_check
    from experiments.p010.student_contract import CELLS, forecast
    from experiments.p010.tier3_dispatch import (
        SEED29_RUNS, attempted_records, totals_and_slots, fixed_review,
        validate_seed29_data, validate_a4,
    )
    if run not in SEED29_RUNS or run not in spec['configs'] or CELLS[run]['tier'] != 3:
        raise ValueError('Only the four original Tier3 seed29 cells')
    cutoff = datetime.datetime(2026, 10, 21, 19, tzinfo=datetime.timezone.utc).timestamp()
    if time.time()+5200 > cutoff:
        raise ValueError('Full original window does not fit the result deadline')
    commit = require_published(ROOT); source_check(spec, ROOT)
    a1, a2, a3 = [read(p) for p in (data_review_json, runtime_review_json, actual_results_review_json)]
    clean1, clean2, clean3 = [fixed_review(v) for v in (a1, a2, a3)]
    validate_seed29_data(spec, run, a1)
    if (a2.get('scope') != 'p010-Tier3-seed29-complete-runtime-A2'
            or a2.get('spec_sha256') != sha(ROOT/SPEC)
            or a2.get('source_files') != spec['source_files']):
        raise ValueError('Exact complete seed29 runtime A2 required')
    a4 = read(a4_report_json); validate_a4(a4, a3)
    reviews = dict(A1=clean1, A2=clean2, actual_results_A3=clean3,
                   A4=dict(report=a4, file_sha256=sha(a4_report_json)))
    b = read(budget_json)
    if (b.get('category') != 'T' or b.get('cap_usd') != '150'
            or b.get('reserve_release_used') is not False
            or not 0 <= time.time()-b['observed_epoch'] <= 3600):
        raise ValueError('Fresh T-category budget with all failed reserves retained required')
    prior = str(Decimal(b['prior_attempted_reserved_usd']))
    initial = forecast(0, 64, 10, spec['timing']['training_seconds'],
                       spec['timing']['endpoint_seconds'], prior)
    budget = budget_check('T', prior, '6.55', initial['budget']['forecast_usd'])
    root = ROOT/'.local/p010_20261019/r1'; out = Path(receipt_dir)
    if out.resolve() != (root/'student_runs'/run).resolve():
        raise ValueError('Canonical original student receipt directory required')
    with (root/'student_dispatch.lock').open('a+') as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        records = attempted_records(root)
        cli = str(ROOT/'.local/midpoint_20261011/venv/bin/modal')
        containers = json.loads(subprocess.check_output([cli, 'container', 'list', '--json'], text=True, timeout=45))
        apps = [read(p.parent/'SUBMITTED.json')['app_id'] for p in records
                if (p.parent/'SUBMITTED.json').exists()]
        def state(app_id):
            try:
                value = json.loads(subprocess.check_output([cli, 'app', 'info', app_id, '--json'],
                    text=True, timeout=45, stderr=subprocess.PIPE))
                if value['app_id'] != app_id: raise ValueError('Provider identity differs')
                return app_id, value['lifecycle']['state']
            except Exception: return app_id, 'unknown'
        with ThreadPoolExecutor(max_workers=2) as readers:
            states = dict(readers.map(state, apps))
        totals, slots = totals_and_slots(records, containers, states)
        if totals['T'] != Decimal(prior) or slots >= 4:
            raise ValueError('All-category slot accounting or exact T reservations differ')
        if ({k:str(v) for k,v in totals.items()} != b['all_attempted_reservations_usd']
                or sum(totals.values())+Decimal('6.55') > Decimal('240')):
            raise ValueError('Fresh complete four-category ledger differs')
        out.mkdir(parents=True, exist_ok=False)
        dump(out/'INTENT.json', dict(run=run, execution=commit, budget=budget,
            budget_source_sha256=sha(budget_json), epoch=time.time(), reviews=reviews,
            admission_provider_states=states, admission_container_slots=slots,
            all_attempted_reservations_usd={k:str(v) for k,v in totals.items()},
            original_A4_is_report_not_extra_permission=True))
        call = worker.spawn(run, commit, reviews, prior)
        dump(out/'SUBMITTED.json', dict(app_id=app.app_id, call_id=call.object_id, run=run))
    try:
        dump(out/'RESULT.json', call.get())
    except BaseException as exc:
        dump(out/'ERROR.json', dict(type=type(exc).__name__, error=str(exc)))
        raise
