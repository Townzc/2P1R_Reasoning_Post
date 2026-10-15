"""Score one fully verified original S1 endpoint once, preserving all failures.

The 500 original rows, exact full runtime/numeric review and local6000-second
scenario precede scoring. No old P1 cache is rescored or silently reused here.
The resulting verdicts still require independent outcome/adjudication A4.
"""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import time

from experiments.sft_allocation_midpoint.common import read, dump, sha, digest
from experiments.learning_regime_p009.stage1_s1_funded_binding import validate
from experiments.learning_regime_p009.stage1_s1_scoring import checked_endpoint_rows
from experiments.learning_regime_p009.stage1_s1_score_process import supervise_endpoint_once
from experiments.learning_regime_p009.stage1_s1_score_proof import verify_score_payload


def execute(args):
    spec = read(args.admission); generated = Path(args.generation_oracle)
    original = Path(args.evidence); sent = read(original/'intent.json'); env = read(args.receipt)
    cap = validate(spec,sent['plan'],args.run,sent['release'])
    proof = read(generated/'COMPLETED.json'); rows = read(generated/'SCORING_ROWS.json')
    if ((generated/'FAILED.json').exists() or proof.get('passed') is not True
        or proof.get('run_id') != args.run or proof.get('outputs_decoded') != 500
        or proof.get('technical_unknown') != 0 or proof.get('updates_verified') != 1024
        or proof.get('targets_verified') != 2097148 or proof.get('spec_sha256') != digest(spec)
        or proof.get('source_files') != spec['source_files']
        or proof.get('artifact_digest') != digest(env['artifact_manifest'])
        or proof.get('state_sha256') != env['artifact_manifest']['checkpoint_1024/state.pt']['sha256']
        or proof.get('original_intent_file_sha256') != sha(original/'intent.json')
        or proof.get('original_receipt_file_sha256') != sha(args.receipt)
        or proof.get('scoring_rows_file_sha256') != sha(generated/'SCORING_ROWS.json')
        or proof.get('decoded_file_sha256') != sha(generated/'DECODED_ROWS.json')
        or proof.get('full_runtime_lineage_admission_checked') is not True
        or proof.get('symbolic_scoring_performed') is not False or env['receipt']['status'] != 'completed'):
        raise ValueError('Complete original state/raw/lineage proof must precede any symbolic pair')
    checked_endpoint_rows(rows)
    if len({r['problem_id'] for r in rows}) != 500:
        raise ValueError('Exactly the original500 distinct problems are required')
    for name,h in spec['source_files'].items():
        if sha(name) != h: raise ValueError('Exact source bytes changed')
    review = sent['release']['runtime_review']
    if sha(review['local_report_path']) != review['report_sha256']:
        raise ValueError('Original complete runtime/numeric report must be present')
    versions = {name:importlib.metadata.version(name) for name in spec['local_scoring_versions']}
    if versions != spec['local_scoring_versions']:
        raise ValueError('Original local symbolic environment differs')
    out = Path(args.out); out.mkdir(parents=True,exist_ok=False); started = time.monotonic()
    binding = dict(run_id=args.run,spec_sha256=digest(spec),source_files=spec['source_files'],
        original_generation_proof_file_sha256=sha(generated/'COMPLETED.json'),
        original_scoring_rows_file_sha256=sha(generated/'SCORING_ROWS.json'),
        original_receipt_file_sha256=sha(args.receipt),original_state_sha256=proof['state_sha256'],
        actual_runtime_report_sha256=review['report_sha256'],local_scoring_versions=versions,
        local_scenario_seconds=5160.0,uncalibrated_overhead_seconds=300,
        original_labels_not_revised=True,independent_outcome_review_required=True)
    dump(out/'INTENT.json',dict(utc=datetime.now(timezone.utc).isoformat(),binding=binding,
        local_wall_seconds=6000,cleanup_allowance_seconds=5,automatic_retry=False))
    try:
        seconds = int(6000-(time.monotonic()-started))
        if seconds <= 0: raise TimeoutError('Original local total window exhausted')
        control = supervise_endpoint_once(out/'job',rows,binding,seconds)
        checked = verify_score_payload(out/'job/payload',rows,binding,seconds)
        if control['child_exit_code'] != 0 or not checked['passed'] or time.monotonic()-started >= 6000:
            raise TimeoutError('Complete scoring, process exit and proof must fit the local window')
        samples = read(out/'job/payload/AUDIT_SAMPLES.json')
        value = dict(passed=True,run_id=args.run,updates_verified=1024,targets_verified=2097148,
            state_sha256=proof['state_sha256'],artifact_digest=proof['artifact_digest'],
            correct=checked['correct'],total=500,question_correct=checked['question_correct'],
            logical_stops=proof['logical_stops'],technical_unknown=0,
            full_generation_oracle_file_sha256=sha(generated/'COMPLETED.json'),
            scoring_control_completed_file_sha256=sha(out/'job/COMPLETED.json'),
            scoring_payload_completed_file_sha256=sha(out/'job/payload/COMPLETED.json'),
            audit_samples_file_sha256=sha(out/'job/payload/AUDIT_SAMPLES.json'),
            original_binding=binding,local_total_observed_seconds=time.monotonic()-started,
            unique_symbolic_pairs=checked['unique_symbolic_pairs'],
            outer_timeout_over_half_percent=samples['outer_timeout_over_half_percent'],
            fallback_over_two_percent=samples['fallback_over_two_percent'],
            independent_adjudication_complete=False,external_A4_pending=True,
            scientific_G1_admitted=False,new_training_updates=0,new_generations=0,
            repeated_binary_state_loads=0,repeated_raw_decoding=0,utc=datetime.now(timezone.utc).isoformat())
        dump(out/'LOCAL_ORACLE_AUDIT.json',value)
        dump(out/'COMPLETED.json',dict(passed=True,oracle_file_sha256=sha(out/'LOCAL_ORACLE_AUDIT.json'),
            control_file_sha256=sha(out/'job/COMPLETED.json'),scientific_G1_admitted=False))
        return value
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),
            automatic_retry=False,partial_evidence_preserved=True,complete_endpoint=False))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('admission','run','generation-oracle','evidence','receipt','out'):
        parser.add_argument('--'+name,required=True)
    value = execute(parser.parse_args())
    print(json.dumps({k:v for k,v in value.items() if k not in ('question_correct','original_binding')}))
