"""One original E3 TP4 lifetime after D4, covered D1 and exact full A1/A2."""
from pathlib import Path
import modal
from experiments.p010.common import read

ROOT = Path(__file__).resolve().parents[2]
SPEC = 'reports/p010_20261019/e3_runtime_v1/SPEC.json'
spec = read(ROOT / SPEC)
app = modal.App('p010-e3-temperature-supply')
volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
image = (modal.Image.debian_slim(python_version='3.12')
    .pip_install_from_requirements(ROOT / 'experiments/learning_regime_p009/requirements_p0.txt')
    .env({'PYTHONPATH': '/workspace', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
          'TOKENIZERS_PARALLELISM': 'false', 'VLLM_WORKER_MULTIPROC_METHOD': 'spawn',
          'VLLM_USE_V1': '1'}))
for name in list(spec['source_files']) + [SPEC]:
    image = image.add_local_file(ROOT / name, '/workspace/' + name, copy=True)


@app.function(image=image, gpu='H100!:4', cpu=(8, 8), memory=(65536, 65536),
    timeout=1860, startup_timeout=600, retries=0, max_containers=1,
    min_containers=0, buffer_containers=0, scaledown_window=2,
    single_use_containers=True, serialized=True, include_source=False,
    volumes={'/evidence': volume})
def worker(execution, reviews, budget):
    import time
    import traceback
    from experiments.p010.common import dump, verify, utc
    from experiments.p010.runtime_support import source_check, hard_timer, compact
    from experiments.p010.e3_contract import KEY, HARD_SECONDS
    from experiments.p010.e3_runtime import generate
    start = time.time()
    timer = hard_timer(HARD_SECONDS)
    out = Path('/evidence/p010-20261019/e3/temperature_supply_r1')
    inputs = Path('/evidence/p010-20261019/e3_inputs')
    store = modal.Dict.from_name('p010-once-20261019', create_if_missing=False)
    claimed = False
    try:
        s = read('/workspace/' + SPEC)
        source_check(s)
        claim = dict(execution=execution, epoch=start, scientific_scope='original_E3')
        if not store.put(KEY + '/claim', claim, skip_if_exists=True):
            raise RuntimeError('Original E3 already attempted; no retry')
        claimed = True
        volume.reload()
        out.mkdir(parents=True, exist_ok=False)
        verify(inputs, s['input_files'])
        dump(out / 'INTENT.json', dict(execution=execution, source_files=s['source_files'],
            input_files=s['input_files'], model=s['model'], reviews=reviews, budget=budget,
            claim=claim, worker_start_epoch=start, hard_deadline_epoch=start + HARD_SECONDS))
        volume.commit()
        result = generate(inputs, out, s['model'], claim, start, start + HARD_SECONDS,
                          s['timing'], budget['D1_charged_G_usd'], store, volume)
        artifact = compact(out)
        volume.commit()
        if time.time() >= start + HARD_SECONDS:
            raise TimeoutError('Original E3 packing exceeded entry window')
        terminal = dict(status='completed', finished_utc=utc(), result=result,
                        artifact=artifact, seconds_including_pack=time.time()-start)
        dump(out / 'TERMINAL.json', terminal)
        volume.commit()
        if not store.put(KEY + '/terminal', terminal, skip_if_exists=True):
            raise RuntimeError('Original terminal already exists')
        return terminal
    except BaseException as exc:
        if claimed and out.exists():
            failure = dict(type=type(exc).__name__, error=str(exc),
                           traceback=traceback.format_exc(), utc=utc(), automatic_retry=False)
            dump(out / 'FAILURE.json', failure)
            volume.commit()
            store.put(KEY + '/terminal', dict(status='failed', failure=failure), skip_if_exists=True)
        raise
    finally:
        timer.cancel()


@app.local_entrypoint()
def main(receipt_dir: str, runtime_review_json: str, owner_d4_json: str,
         a4_report_json: str, actual_results_review_json: str, budget_json: str):
    import datetime
    import fcntl
    import json
    import subprocess
    import time
    from decimal import Decimal
    from concurrent.futures import ThreadPoolExecutor
    from experiments.p010.common import dump, sha, require_published
    from experiments.p010.runtime_support import source_check
    from experiments.p010.tier3_dispatch import attempted_records, totals_and_slots, fixed_review, validate_a4
    from experiments.p010.e3_contract import KEY, CAPS, RESERVE, validate_d4, forecast
    from experiments.p010.e3_settlement_binding import validate_settlement
    cutoff = datetime.datetime(2026, 10, 21, 10, tzinfo=datetime.timezone.utc).timestamp()
    final = datetime.datetime(2026, 10, 21, 19, tzinfo=datetime.timezone.utc).timestamp()
    # Cloud, bounded collection/records, complete raw oracle, local symbolic
    # scoring, metrics and metadata publication must all fit the result window.
    if time.time() >= cutoff or time.time() + 51105 > final:
        raise ValueError('Complete original E3 window does not fit the cutoff')
    execution = require_published(ROOT)
    source_check(spec, ROOT)
    for name, expected in spec['verification_source_files'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('Exact verification source differs: '+name)
    root = ROOT / '.local/p010_20261019/r1'
    out = Path(receipt_dir)
    if out.resolve() != (root / 'e3_runs/temperature_supply_r1').resolve():
        raise ValueError('Canonical original E3 directory required')
    audit = read(runtime_review_json)
    clean = fixed_review(audit)
    owner = read(owner_d4_json);validate_d4(owner)
    if (sha(owner['local_evidence_file']) != owner['evidence_sha256']
            or sha(owner_d4_json)!=spec['owner_D4_file_sha256']
            or owner['owner_delegation_sha256'] != spec['owner_delegation_sha256']
            or audit.get('scope') != 'p010-E3-complete-input-runtime-and-numeric-A2'
            or audit.get('spec_sha256') != sha(ROOT / SPEC)
            or audit.get('source_files') != spec['source_files']
            or audit.get('owner_D4_evidence_sha256') != owner['evidence_sha256']
            or audit.get('settlement_proposal_sha256') != spec['settlement_proposal_sha256']
            or audit.get('input_A1_accepted') is not True
            or audit.get('D1_hourly_coverage_scope_accepted') is not True
            or audit.get('all_old_T08_outputs_reused_without_rescoring') is not True
            or audit.get('first_paid_measurement_exceptions') != 0):
        raise ValueError('True independent full A1/A2, D1 coverage and original D4 required')
    a3 = read(actual_results_review_json)
    clean3 = fixed_review(a3)
    a4 = read(a4_report_json)
    validate_a4(a4, a3)
    uploaded = read(root / 'e3_input_upload_r1/COMPLETED.json')
    if {n: {k: v[k] for k in ('bytes', 'sha256')} for n, v in uploaded['files'].items()} != spec['input_files']:
        raise ValueError('Every exact input must have original readback')
    b = read(budget_json)
    if (not 0 <= time.time() - b['observed_epoch'] <= 3600
            or b.get('caps_usd') != {'G': 50, 'T': 150, 'I': 15, 'C': 25}
            or b.get('overall_cap_usd') != '240' or b.get('protected_usd') != '43'
            or b.get('D1_proposal_sha256') != spec['settlement_proposal_sha256']
            or sha(b['local_billing_report'])!=b['billing_report_sha256']):
        raise ValueError('Fresh original-cap D1 budget required')
    settlement=validate_settlement(spec,read(b['local_billing_report']))
    charged=settlement['proposed_charged_G_usd']
    initial = forecast(0, 0, [], spec['timing']['original_full_batch_seconds'],
                       spec['timing']['observed_pre_first_batch_seconds'], model_loaded=False,charged_G=charged)
    with (root / 'student_dispatch.lock').open('a+') as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        # D4: finish original predecessor dispatches and wait for zero slots.
        for relative in spec['required_prior_receipt_directories']:
            prior = root / relative
            if not (prior / 'INTENT.json').exists() or not (prior / 'SUBMITTED.json').exists():
                raise ValueError('Unattempted predecessor; E3 cannot delay original calls')
        records = attempted_records(root)
        cli = str(ROOT / '.local/midpoint_20261011/venv/bin/modal')
        containers = json.loads(subprocess.check_output([cli, 'container', 'list', '--json'], text=True, timeout=45))
        apps = [read(p.parent / 'SUBMITTED.json')['app_id'] for p in records
                if (p.parent / 'SUBMITTED.json').exists()]
        def state(app_id):
            try:
                value = json.loads(subprocess.check_output([cli, 'app', 'info', app_id, '--json'],
                    text=True, timeout=45, stderr=subprocess.PIPE))
                if value['app_id'] != app_id:
                    raise ValueError('Provider identity differs')
                return app_id, value['lifecycle']['state']
            except Exception:
                return app_id, 'unknown'
        with ThreadPoolExecutor(max_workers=2) as readers:
            states = dict(readers.map(state, apps))
        totals, slots = totals_and_slots(records, containers, states)
        if slots != 0 or totals['G'] != Decimal('44'):
            raise ValueError('All predecessors must be STOPPED0 and prior G exactly44')
        effective=dict(totals);effective['G']=Decimal(charged)
        if ({k: str(v) for k, v in totals.items()} != b['all_attempted_reservations_usd']
                or any(effective[k] + (RESERVE if k == 'G' else 0) > CAPS[k] for k in CAPS)
                or sum(effective.values()) + RESERVE > Decimal('240')):
            raise ValueError('Complete original reservation ledger differs')
        store = modal.Dict.from_name('p010-once-20261019', create_if_missing=False)
        if any(store.get(KEY + '/' + k) is not None for k in ('dispatch', 'claim', 'terminal')):
            raise ValueError('Original E3 dispatch/claim already consumed or unknown')
        reviews = dict(A2=clean, owner_D4={k: v for k, v in owner.items() if k != 'local_evidence_file'},
                       actual_results_A3=clean3, A4=dict(report=a4, file_sha256=sha(a4_report_json)))
        budget = dict(category='G', original_prior_reserved_usd='44', D1_charged_G_usd=charged,
                      new_reserved_usd=str(RESERVE),forecast_usd=initial['projected_usd'],cap_usd='50',
                      settlement_proposal_sha256=spec['settlement_proposal_sha256'],
                      original_failed_claims_retained=True,all_categories_unchanged=True)
        out.mkdir(parents=True, exist_ok=False)
        intent = dict(execution=execution, budget=budget, reviews=reviews, epoch=time.time(),
                      budget_source_sha256=sha(budget_json), admission_provider_states=states,
                      admission_container_slots=slots, all_attempted_reservations_usd={k: str(v) for k, v in totals.items()})
        dump(out / 'INTENT.json', intent)
        dump(out / 'D1_SETTLEMENT_APPLIED.json',dict(utc=__import__('experiments.p010.common',fromlist=['utc']).utc(),
            candidate=settlement,actual_release_applied=True,original_claims_modified=False,
            exact_A2_report_sha256=audit['report_sha256'],proposal_sha256=spec['settlement_proposal_sha256'],
            fresh_budget_sha256=sha(budget_json),runtime_spec_sha256=sha(ROOT/SPEC)))
        if not store.put(KEY + '/dispatch', intent, skip_if_exists=True):
            raise RuntimeError('Original E3 dispatch fence already exists')
        call = worker.spawn(execution, reviews, budget)
        dump(out / 'SUBMITTED.json', dict(app_id=app.app_id, call_id=call.object_id, run='temperature_supply_r1'))
    try:
        dump(out / 'RESULT.json', call.get())
    except BaseException as exc:
        dump(out / 'ERROR.json', dict(type=type(exc).__name__, error=str(exc), automatic_retry=False))
        raise
