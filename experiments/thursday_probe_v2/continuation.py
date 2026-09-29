"""One bounded engineering continuation; immutable failed attempt stays evidence."""
import json
import math
from pathlib import Path
from experiments.thursday_probe_v2.config import LIMITS, RELEASE, DATA, TRAINING, evaluation_queue
from src.sft_data import read_jsonl,sha256_file


def continuation_cap(age,previous_charge):
    # Both prior process usage and elapsed powered-on time reduce availability.
    if not math.isfinite(age) or age<0 or type(previous_charge) is not int or previous_charge<0:
        raise ValueError('Invalid elapsed time or prior process charge')
    cap=math.floor(min(LIMITS['process_seconds']-previous_charge,
        LIMITS['whole_window_seconds']-age-LIMITS['export_shutdown_reserve_seconds']-LIMITS['kill_grace_seconds']))
    if cap<=0:raise ValueError('No bounded continuation time remains')
    return cap


def validate_previous(path):
    path=Path(path)
    if path!=Path('runs/thursday_arithmetic_v2_r1'):
        raise ValueError('Only the first preserved attempt can be continued')
    export=json.loads((path/'export_manifest_final.json').read_text())
    required={'resource_receipt.json','run_manifest_final.json','generation_ledger.json',
              'preflight.json','C0_calibration.jsonl','C0_calibration.generation.json','C0_probes.jsonl'}
    if not required<=set(export['files']):
        raise ValueError('Prior export does not bind all continuation evidence')
    for name,entry in export['files'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('Invalid prior export path')
        p=path/name
        if p.stat().st_size!=entry['bytes'] or sha256_file(p)!=entry['sha256']:
            raise ValueError('Prior attempt changed: '+name)
    receipt=json.loads((path/'resource_receipt.json').read_text())
    manifest=json.loads((path/'run_manifest_final.json').read_text())
    ledger=json.loads((path/'generation_ledger.json').read_text())
    preflight=json.loads((path/'preflight.json').read_text())
    if receipt['charged_seconds']!=478 or receipt['status']!='failed' or not receipt['historical_ledger_unchanged']:
        raise ValueError('Unexpected engineering-stop receipt')
    if (manifest['source_commit']!='a85d615fd7c2e7b4efe30fe248059ad195c16823'
        or len(manifest['runs'])!=len(TRAINING) or any(r['status']!='not_run' for r in manifest['runs'])):
        raise ValueError('Continuation is only valid before any training')
    if manifest['release_manifest_sha256']!=sha256_file(RELEASE/'manifest.json'):
        raise ValueError('Scientific release changed')
    if ([e['name'] for e in manifest['evaluations']]!=['C0_calibration'] or ledger['used']!=432
        or ledger['cap']!=LIMITS['generation_cap']
        or [(e['name'],e['reserved']) for e in ledger['events']]!=[('C0_calibration.jsonl',48),('C0_probes.jsonl',384)]):
        raise ValueError('Unexpected previous evaluation queue')
    expected=evaluation_queue()[0]
    if any(manifest['evaluations'][0].get(k)!=v for k,v in expected.items()):
        raise ValueError('Previous calibration recipe differs')
    calibration=read_jsonl(path/'C0_calibration.jsonl');partial=read_jsonl(path/'C0_probes.jsonl')
    if len(calibration)!=48 or len(partial)!=12:
        raise ValueError('Unexpected previous output lengths')
    calibration_ids=[(r['problem_id'],0) for r in read_jsonl(RELEASE/'calibration.jsonl')]
    probe_ids=[(r['problem_id'],s) for r in read_jsonl(DATA/'probes.jsonl') for s in range(4)]
    for records,expected_ids in ((calibration,calibration_ids),(partial,probe_ids[:12])):
        if ([(r['problem_id'],r['sample_index']) for r in records]!=expected_ids
            or any(r['batch_index']!=i//8 for i,r in enumerate(records))):
            raise ValueError('Prior prediction identities/batches differ')
    if sha256_file(path/'C0_calibration.jsonl')!=manifest['evaluations'][0]['predictions_sha256']:
        raise ValueError('Reuse hash mismatch')
    return dict(previous_attempt=str(path),charged_seconds=478,completed_reused_generations=48,
        power_on_at_utc=preflight['power_on_at_utc'],
        incomplete_saved_records=12,fault_generations=16,total_previous_attempted_generations=64,
        cancelled_uninvoked_reservation=368,
        reused_adapter=manifest['evaluations'][0]['adapter'],
        previous_export_manifest_sha256=sha256_file(path/'export_manifest_final.json'),
        reason='Operator SIGTERM for repeated tokenizer metadata lookup inside per-token audit; no training started. The old generic timeout traceback is preserved and is not evidence that the8400s cap elapsed.',
        generation_accounting='The synchronous generator returned batch2 before audit stopped at row12. Exactly16 probe outputs were attempted;48 completed calibration outputs are reused byte-for-byte. Remaining368 reserved probe outputs were never invoked. Replay the entire probe evaluation from its unchanged fixed seed; charge16 duplicates to the fault reserve.')
