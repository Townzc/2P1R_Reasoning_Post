"""Export a compact, immutable public audit packet from verified local records.

No cloud calls or model execution. Does not grant an external review verdict.
Question text, correspondence, credentials and checkpoint binaries stay private.
"""
import argparse
import json
from pathlib import Path
from collections import Counter
from experiments.sft_allocation_midpoint.common import read, sha, digest, dump


def build(session, out):
    session, out = Path(session), Path(out)
    closeout = read(session/'main_closeout_r1/LOCAL_CLOSEOUT.json')
    if closeout['status'] != 'completed_verified_resources_released':
        raise ValueError('Main verification is incomplete')
    records, runs = [], {}
    for logical, verified in closeout['runs'].items():
        campaign, physical = verified['source']
        folder = 'grid_export_r2' if campaign == 'mp-grid-20261012-r2' else 'grid_completion_export'
        root = session/folder/physical
        result = read(root/'result.json')
        manifest = read(root/'artifact_manifest.json')
        local = read(root/'LOCAL_ORACLE_AUDIT.json')
        if sha(root/'LOCAL_ORACLE_AUDIT.json') != verified['local_audit_sha256']:
            raise ValueError('Previously verified local proof changed')
        rows = []
        for file in sorted((root/'endpoint431').glob('batch_*_scored.jsonl')):
            relative = str(file.relative_to(root))
            if sha(file) != manifest[relative]['sha256']:
                raise ValueError('Scored artifact changed')
            raw_name = relative.replace('_scored.jsonl', '_raw.json')
            for line in file.open():
                original = json.loads(line)
                correct = original['task_score']['task_answer_correct']
                if type(correct) is not bool:
                    raise ValueError('Unknown is not a Boolean score')
                rows.append(dict(run_id=logical, source_campaign=campaign,
                    source_run_id=physical, checkpoint_step=0 if logical == 'base' else 256,
                    question_id=original['problem_id'], correct=correct,
                    parse_status=original['task_score']['marked']['status'],
                    parsed_value=original['task_score']['marked'].get('value'),
                    stop_reason=original['stop']['stop_reason'],
                    generated_tokens=original['generated_tokens'],
                    raw_file=raw_name, raw_file_sha256=manifest[raw_name]['sha256'],
                    scored_record_sha256=digest(original)))
        if len(rows) != 431 or len({r['question_id'] for r in rows}) != 431:
            raise ValueError('Endpoint roster is incomplete')
        correct = {r['question_id']: r['correct'] for r in rows}
        if correct != result['endpoint']['question_correct']:
            raise ValueError('Question outcomes disagree with result')
        if sum(correct.values()) != verified['correct']:
            raise ValueError('Verified numerator differs')
        records.extend(rows)
        budget = result.get('budget')
        dose = None
        if budget:
            exposure = budget['row_exposures']
            values = list(exposure.values())
            dose = dict(optimizer_updates=budget['optimizer_updates'],
                supervised_targets=budget['supervised_response_tokens'],
                processed_tokens=budget['processed_nonpadding_tokens'],
                unique_pairs=len(exposure), trained_problems=len(budget['problem_exposures']),
                row_exposures=exposure, problem_exposures=budget['problem_exposures'],
                path_exposures=budget['path_exposures'],
                mean_pair_exposures=sum(values)/len(values),
                min_pair_exposures=min(values), max_pair_exposures=max(values))
        runs[logical] = dict(source=verified['source'], correct=sum(correct.values()), n=431,
            accuracy=sum(correct.values())/431,
            parsed=sum(r['parse_status'] == 'parsed' for r in rows),
            stop_counts=dict(Counter(r['stop_reason'] for r in rows)),
            generated_tokens=sum(r['generated_tokens'] for r in rows),
            dose=dose, initial_reference_nll=result.get('initial_reference_nll'),
            final_reference_nll=result.get('final_reference_nll'),
            observed_curves=result.get('curve'),
            original_manifest_digest=digest(manifest),
            checkpoint_state_sha256=verified['terminal_state_sha256'],
            local_proof_sha256=sha(root/'LOCAL_ORACLE_AUDIT.json'),
            terminal_receipt=verified['terminal'],
            # Rate-derived per-run estimates are explicitly NOT provider invoices.
            runtime_rate_estimate_usd=result.get('runtime_rate_estimate_usd'),
            provider_attributed_invoice_usd=None)
    if len(records) != 3879:
        raise ValueError('Nine complete endpoints required')
    out.mkdir(parents=True, exist_ok=False)
    with (out/'question_outcomes.jsonl').open('x') as stream:
        for row in sorted(records, key=lambda r: (r['run_id'], r['question_id'])):
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True)+'\n')
    dump(out/'runs.json', runs)
    dump(out/'cost_and_scope.json', dict(
        source_closeout_sha256=sha(session/'main_closeout_r1/LOCAL_CLOSEOUT.json'),
        provider_meter=closeout['provider_meter'], provider_checked_utc=closeout['provider_checked_utc'],
        attribution_scope='Workspace cumulative usage including engineering and failed work; not final invoice or balance.',
        provider_invoice_usd=None, protected_usd=50, total_authorized_usd=500,
        older_failure=closeout['older_failed_campaign'], engineering=closeout['engineering_separate'],
        unknown_intermediate_attempts=8, unknown_formal_endpoint_attempts=0,
        external_audit_status='pending', external_verdict=None,
        limitations=closeout['limitations']))
    dump(out/'manifest.json', dict(schema='p007_external_audit_packet_v1',
        snapshot_id='p007-main-20261012-v1', external_audit_status='pending',
        files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.iterdir()) if p.is_file()},
        rows=3879, runs=9, scientific_model_calls=0,
        scope='Metrics, exposure and reported cost audit. Token-level scoring reproduction also requires the retained raw artifacts and pinned tokenizer.'))
    return dict(out=str(out), rows=3879, runs=9, manifest_sha256=sha(out/'manifest.json'))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--session',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();print(json.dumps(build(a.session,a.out)))
