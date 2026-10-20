"""UNATTEMPTED E4 endpoint-only exception; direct owner and exact A2 required."""
from pathlib import Path
import modal
from experiments.p010.common import read

ROOT = Path(__file__).resolve().parents[2]
SPEC = 'reports/p010_20261019/e4_endpoint_repair_preflight_v1/SPEC.json'
# This prospective module cannot be imported until its exact packet exists.
spec = read(ROOT/SPEC)
app = modal.App('p010-e4-endpoint-only')
volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
image = (modal.Image.debian_slim(python_version='3.12')
    .pip_install_from_requirements(ROOT/'experiments/learning_regime_p009/requirements_p0.txt')
    .env({'PYTHONPATH': '/workspace', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
          'TOKENIZERS_PARALLELISM': 'false', 'VLLM_WORKER_MULTIPROC_METHOD': 'spawn',
          'VLLM_USE_V1': '1', 'CUBLAS_WORKSPACE_CONFIG': ':4096:8'}))
for name in list(spec['source_files'])+[SPEC]:
    image = image.add_local_file(ROOT/name, '/workspace/'+name, copy=True)


@app.function(image=image, gpu='H100!', cpu=(4, 4), memory=(32768, 32768),
    timeout=1260, startup_timeout=600, retries=0, max_containers=2,
    min_containers=0, buffer_containers=0, scaledown_window=2,
    single_use_containers=True, serialized=True, include_source=False,
    volumes={'/evidence': volume})
def worker(run, execution, proof, approvals, prior):
    import time
    import traceback
    from experiments.p010.common import dump, sha, digest, verify, utc
    from experiments.p010.runtime_support import source_check, hard_timer, compact
    from experiments.p010.e4_endpoint_contract import endpoint_rows, sampling, forecast, validate_parent
    start = time.time(); timer = hard_timer(1200)
    old = Path('/evidence/p010-20261019/e4')/run
    out = Path('/evidence/p010-20261019/e4_endpoint_only')/run
    store = modal.Dict.from_name('p010-once-20261019', create_if_missing=False)
    key = 'e4_endpoint_only/'+run; original = 'e4/'+run
    claimed = False
    try:
        s = read('/workspace/'+SPEC); source_check(s); volume.reload()
        claim = store.get(original+'/claim'); terminal = store.get(original+'/terminal')
        def endpoint_records():
            return [store.get(original+'/'+kind+f'/{offset:04d}')
                    for offset in range(0, 1319, 256) for kind in ('eval', 'eval_done')]
        validate_parent(proof, run, claim, terminal, endpoint_records(), list((old/'raw').glob('*.json')))
        if (digest(proof) != s['parents'][run]['proof_canonical_sha256']
                or sha(old/'checkpoint_1024/state.pt') != proof['state_sha256']
                or read(old/'INTENT.json')['identity'] != proof['original_identity']
                or read(old/'MERGE_PROOF.json')['merged_files'] != proof['merged_files']
                or read(old/'TRAINING_EXIT.json')['joined_before_vllm'] is not True):
            raise ValueError('Original immutable final state/merge/exit differs')
        verify(old/'merged', proof['merged_files'])
        endpoint = Path('/evidence/p010-20261019/inputs/olmo_gsm_zero.json')
        if sha(endpoint) != s['endpoint_file_sha256']:
            raise ValueError('Original frozen endpoint bytes differ')
        rows = endpoint_rows(read(endpoint))
        params = [sampling() for _ in rows]
        marker = dict(run=run, execution=execution, epoch=start,
            original_failed_claim=claim, original_state_sha256=proof['state_sha256'])
        if not store.put(original+'/endpoint_only_successor', marker, skip_if_exists=True):
            raise RuntimeError('Independent endpoint exception already attempted')
        if not store.put(key+'/claim', marker, skip_if_exists=True):
            raise RuntimeError('Endpoint-only claim already exists; no replay')
        claimed = True; out.mkdir(parents=True, exist_ok=False)
        dump(out/'INTENT.json', dict(run=run, claim=marker, original_failed_terminal=terminal,
            execution=execution, worker_start_epoch=start, hard_deadline_epoch=start+1200,
            source_files=s['source_files'], approvals=approvals, prior_T_reserved_usd=prior))
        dump(out/'ORIGINAL_TRAINING_PROOF.json', proof); volume.commit()
        from vllm import LLM, SamplingParams
        from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs, actual_engine
        from experiments.learning_regime_p009.stage0_generation_engine_v2 import returned_records
        # Constructor checks use the real Linux package before the LLM lifetime.
        actual_params = [SamplingParams(**p) for p in params]
        dump(out/'BEFORE_MODEL_FORECAST.json', forecast(time.time()-start, 0, [], prior)); volume.commit()
        llm = LLM(model=str(old/'merged'), tokenizer=str(old/'merged'), **engine_kwargs())
        dump(out/'ENGINE.json', actual_engine(llm.llm_engine.vllm_config)); volume.commit()
        times = []
        for offset in range(0, len(rows), 256):
            unit = f'{offset:04d}'; part = rows[offset:offset+256]; part_params = params[offset:offset+256]
            f = forecast(time.time()-start, len(times), times, prior)
            if store.get(key+'/claim') != marker or store.get(original+'/terminal') != terminal:
                raise RuntimeError('Original failed terminal or child claim changed')
            dump(out/'eval_forecasts'/(unit+'.json'), f)
            intent = dict(rows=part, sampling=part_params, epoch=time.time())
            if not store.put(key+'/eval/'+unit, intent, skip_if_exists=True):
                raise RuntimeError('Endpoint batch already reserved; no repeat')
            dump(out/'eval_intents'/(unit+'.json'), intent); volume.commit(); tick = time.monotonic()
            outputs = llm.generate([{'prompt_token_ids': x['input_ids']} for x in part],
                actual_params[offset:offset+256], use_tqdm=False)
            raw = returned_records(part, part_params, outputs)
            dump(out/'raw'/(unit+'.json'), raw); volume.commit()
            if (len(raw) != len(part) or any(x['output_count'] != 1
                    or x['problem_id'] != row['problem_id'] or x['prompt_token_ids'] != row['input_ids']
                    for row, x in zip(part, raw))):
                raise ValueError('Original endpoint identity or raw shape differs')
            ack = dict(count=len(part), seconds=time.monotonic()-tick, raw_sha256=digest(raw))
            times.append(ack['seconds']); dump(out/'eval_acks'/(unit+'.json'), ack)
            if not store.put(key+'/eval_done/'+unit, ack, skip_if_exists=True):
                raise RuntimeError('Endpoint acknowledgment already exists')
            volume.commit()
        validate_parent(proof, run, store.get(original+'/claim'), store.get(original+'/terminal'),
            endpoint_records(), list((old/'raw').glob('*.json')))
        result = dict(run=run, original_training_proof_sha256=digest(proof), raw_endpoint_count=1319,
            new_training_updates=0, original_training_updates=1024, original_targets=2097148,
            original_failed_parent_remains_failed=True, eval_batch_seconds=times,
            seconds=time.time()-start, score='Frozen marked_answer_v1 and independent A3 still required')
        dump(out/'RESULT.json', result); volume.commit(); packed = compact(out); volume.commit()
        terminal_result = dict(status='completed', finished_utc=utc(), result=result,
            artifact=packed, seconds_including_pack=time.time()-start)
        dump(out/'TERMINAL.json', terminal_result); volume.commit()
        if not store.put(key+'/terminal', terminal_result, skip_if_exists=True):
            raise RuntimeError('Terminal already exists')
        return terminal_result
    except BaseException as exc:
        if claimed and out.exists():
            dump(out/'FAILURE.json', dict(type=type(exc).__name__, error=str(exc),
                traceback=traceback.format_exc(), utc=utc(), retry=False)); volume.commit()
            store.put(key+'/terminal', dict(status='failed', error=str(exc)), skip_if_exists=True)
        raise
    finally:
        timer.cancel()


@app.local_entrypoint()
def main(run:str, receipt_dir:str, proof_json:str, owner_json:str, review_json:str, budget_json:str):
    import datetime
    import fcntl
    import json
    import subprocess
    import time
    from decimal import Decimal
    from experiments.p010.common import dump, sha, digest, require_published
    from experiments.p010.e4_endpoint_contract import forecast
    from experiments.sft_allocation_p008.provider_release import read_stopped_apps
    if run not in spec['parents'] or time.time()+1900 > datetime.datetime(2026,10,21,19,tzinfo=datetime.timezone.utc).timestamp():
        raise ValueError('Exact two cells and complete original deadline window required')
    execution = require_published(ROOT)
    proof, owner, review, b = map(read, [proof_json, owner_json, review_json, budget_json])
    if (sha(proof_json) != spec['parents'][run]['proof_file_sha256']
            or digest(proof) != spec['parents'][run]['proof_canonical_sha256']
            or owner.get('decision') != 'APPROVED'
            or owner.get('scope') != 'p010-E4-completed-state-endpoint-only-exception'
            or owner.get('spec_sha256') != sha(ROOT/SPEC)
            or owner.get('cells') != sorted(spec['parents'])
            or owner.get('maximum_new_reserved_usd') != '5.04'
            or not owner.get('direct_user_message')
            or review.get('decision') not in ('PASS', 'PASS-WITH-NOTES')
            or review.get('scope') != 'p010-C8-endpoint-only-repair-A2'
            or review.get('spec_sha256') != sha(ROOT/SPEC)
            or sha(review['local_report_file']) != review['report_sha256']):
        raise ValueError('Actual owner exception, exact proof and independent A2 required')
    if (b.get('category') != 'T' or b.get('cap_usd') != '150'
            or b.get('reserve_release_used') is not False or not 0 <= time.time()-b['observed_epoch'] <= 3600):
        raise ValueError('Fresh actual T reservation ledger required')
    prior = str(Decimal(b['prior_attempted_reserved_usd'])); initial = forecast(0,0,[],prior)
    cli = str(ROOT/'.local/midpoint_20261011/venv/bin/modal')
    containers = json.loads(subprocess.check_output([cli, 'container', 'list', '--json'], text=True, timeout=45))
    parent_apps = [spec['parents'][key]['original_app_id'] for key in sorted(spec['parents'])]
    provider = read_stopped_apps(cli,parent_apps,[x for x in containers if x.get('app_id') in parent_apps])
    lock = ROOT/'.local/p010_20261019/r1/student_dispatch.lock'
    with lock.open('a+') as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX); root = lock.parent
        originals = list(root.glob('e4_n*_r1/INTENT.json'))
        originals += list((root/'student_runs').glob('*/INTENT.json'))
        originals += list((root/'e4_endpoint_only_runs').glob('*/INTENT.json'))
        actual = sum((Decimal(read(p)['budget']['new_reserved_usd']) for p in originals), Decimal('0'))
        if actual != Decimal(prior):
            raise ValueError('Reservation ledger omits an attempted call')
        pending = sum(not (p.parent/'RESULT.json').exists() and not (p.parent/'ERROR.json').exists() for p in originals)
        if pending >= 4 or len(containers) >= 4:
            raise ValueError('No verified available slot within four-container scope')
        out = Path(receipt_dir)
        if out.resolve() != (root/'e4_endpoint_only_runs'/run).resolve():
            raise ValueError('Canonical child receipt directory required')
        out.mkdir(parents=True,exist_ok=False)
        approvals = dict(owner={k:v for k,v in owner.items() if not k.startswith('local_')},
            audit={k:v for k,v in review.items() if k!='local_report_file'})
        dump(out/'INTENT.json', dict(run=run, execution=execution, epoch=time.time(),
            budget=initial['budget'], budget_source_sha256=sha(budget_json),
            proof_file_sha256=sha(proof_json), approvals=approvals))
        dump(out/'PARENT_PROVIDER_PRIVATE.json',dict(infos=provider,owned=[],utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        call = worker.spawn(run, execution, proof, approvals, prior)
        dump(out/'SUBMITTED.json',dict(run=run,app_id=app.app_id,call_id=call.object_id))
    try:
        dump(out/'RESULT.json',call.get())
    except BaseException as exc:
        dump(out/'ERROR.json',dict(type=type(exc).__name__,error=str(exc)));raise
