"""Proposed once-only remaining local B oracle after a missing dependency.

Requires an explicit delegated exception and exact new review. Original model,
collection, extraction, failed audit, input checks and scientific sources remain
untouched. Only the original unexecuted oracle tail may run; it appends absent
proof files while retaining FAILED.json and a separate permanent continuation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time

from experiments.p011 import b_students_post_long_failure_path as path
from experiments.p011 import b_student_evidence, c1_admission as shared
from experiments.sft_allocation_midpoint.common import read, sha, digest
from scripts import p011_b_students_post_long_failure_io as original

ROOT = Path(__file__).resolve().parents[1]
PACKET = 'reports/p011_20261020/b_local_audit_remaining_preflight_v1'
JOBS = ('B_B1_s17_r1', 'B_B3_s17_r1')
SCOPE = 'p011-B-first-local-audit-remaining-tail-exception-CR'
OUTPUTS = ('DECODED.json', 'SCORING_ROWS.json', 'COMPLETE_PROOF.json')


def create(file, value):
    with Path(file).open('x') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)+'\n')


def failure_gate(auditdir):
    failure = read(auditdir/'FAILED.json')
    if (failure.get('type') != 'ModuleNotFoundError'
            or failure.get('message') != "No module named 'transformers'"
            or failure.get('partial_retained') is not True
            or failure.get('whole_helper_retry_allowed') is not False):
        raise ValueError('Only the exact unexecuted-oracle dependency failure is eligible')
    if any((auditdir/n).exists() for n in OUTPUTS):
        raise ValueError('Any partial/completed oracle output blocks continuation')
    return failure


def claim(base, job, value):
    if job not in JOBS:
        raise ValueError('Only original B1/B3 local tails are eligible')
    out = base/'b_audit_remaining_r1'/job
    out.mkdir(parents=True, exist_ok=False)
    create(out/'ATTEMPT.json', value)
    return out


def admission(root, specfile, spec, report):
    binding = read(root/PACKET/'SOURCE_BINDING.json')
    requirements = read(root/PACKET/'REVIEW_REQUIREMENTS.json')
    shared.fixed_report(report)
    if (any(report.get(k) != v for k,v in binding.items())
            or any(report.get(k) is not True for k in requirements['flags_required_true'])):
        raise ValueError('Explicit delegated exception and exact remaining-tail review required')
    if sha(Path(report['local_report_path'])) != report['report_sha256']:
        raise ValueError('Original complete report bytes differ')
    if (binding['scope'] != SCOPE or binding['original_model_spec_sha256'] != sha(specfile)
            or binding['original_model_source_files'] != spec['source_files']):
        raise ValueError('Original model/source scope changed')
    shared.exact_source({'source_files': binding['source_files']}, root)
    head = path.published(root,spec)
    for name in ('scripts/continue_p011_b_student_local_audit.py', PACKET+'/SOURCE_BINDING.json',
                 PACKET+'/REVIEW_REQUIREMENTS.json', PACKET+'/FAILURE_BINDING.json'):
        if subprocess.check_output(['git','show',head+':'+name],cwd=root) != (root/name).read_bytes():
            raise ValueError('Continuation bytes must be published before entry')
    failures = read(root/PACKET/'FAILURE_BINDING.json')
    if digest(failures) != binding['failure_binding_digest']:
        raise ValueError('Failure manifest differs')
    return binding,failures


def remaining_tail(root, spec, job, auditdir, saved, receipt, continuation):
    # This is the first execution of these original semantic checks. The source
    # functions and their strict state/token/stop/scoring contracts are unchanged.
    from transformers import AutoTokenizer
    payload = auditdir/'payload'
    records = read(saved/'RECORDS.json')
    identity = read(payload/'IDENTITY.json');timing = read(payload/'TIMING_POLICY.json')
    inputs = path.local_inputs(root,job);assets = root/job['model']['local_path']
    cfg = read(assets/'config.json')
    tokenizer = AutoTokenizer.from_pretrained(assets,local_files_only=True,trust_remote_code=False,use_fast=True)
    if sha(inputs/'GOLD.jsonl') != b_student_evidence.GOLD_SHA256:
        raise ValueError('Original frozen MATH gold differs')
    goldrows = [json.loads(s) for s in (inputs/'GOLD.jsonl').read_text().splitlines() if s]
    gold = {r['problem_id']:r for r in goldrows}
    if len(goldrows) != 500 or len(gold) != 500:
        raise ValueError('Exact original500 gold rows required')
    trained = b_student_evidence.verify_training(payload,inputs.parent,timing,job['run_id'],identity,records,tokenizer)
    endpoint = b_student_evidence.verify_endpoint(payload,read(inputs/'MATH_ENDPOINT.json'),timing,
        job['run_id'],records,trained,tokenizer,gold,cfg['vocab_size'])
    scoring = endpoint.pop('scoring_rows');decoded = endpoint.pop('decoded')
    create(auditdir/'DECODED.json',decoded)
    create(auditdir/'SCORING_ROWS.json',scoring)
    create(auditdir/'COMPLETE_PROOF.json',dict(passed=True,receipt_sha256=sha(saved/'ORIGINAL_RESULT.json'),
        job_sha256=digest(job),source_files=spec['source_files'],endpoint=endpoint,
        training_state_verified=True,training_proof=trained,scoring_rows_sha256=sha(auditdir/'SCORING_ROWS.json'),
        actual_A3_accepted=False,finished_epoch=time.time(),original_failed_audit_retained=True,
        explicit_remaining_tail_continuation=continuation))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job',choices=JOBS,required=True)
    parser.add_argument('--review',required=True)
    parser.add_argument('--original-review',required=True)
    args=parser.parse_args()
    specfile=ROOT/path.SPEC_FILES['student'];spec=path.validate(read(specfile))
    # Both independent decisions are necessary; a source pass is not an exception.
    original_review=read(args.original_review)
    path.reviewed(spec,specfile,original_review)
    report=read(args.review);binding,failures=admission(ROOT,specfile,spec,report)
    if sha(Path(args.original_review)) != binding['original_acceptance_file_sha256']:
        raise ValueError('Original reviewed admission changed')
    job=spec['jobs'][args.job];base=ROOT/path.LOCAL
    auditdir=base/'b_io_r1/audit'/args.job;saved=base/'b_io_r1/collect'/args.job
    # These new-boundary metadata reads do not re-extract or rehash old binaries.
    for name,meta in failures[args.job].items():
        file=ROOT/name
        if sha(file)!=meta['sha256'] or file.stat().st_size!=meta['bytes']:
            raise ValueError('Original failure/completion metadata changed')
    failure_gate(auditdir)
    receipt=read(saved/'ORIGINAL_RESULT.json')
    if (read(auditdir/'payload/EVIDENCE_MEMBERS.json')!=receipt['artifact']['members']
            or read(saved/'COMPLETED.json')['archive_sha256']!=receipt['artifact']['tar_sha256']):
        raise ValueError('Original completed extraction metadata differs')
    seconds,deadline=original.window('audit',job,time.time(),receipt)
    if read(auditdir/'ATTEMPT.json')['original_absolute_deadline']!=deadline:
        raise ValueError('The original worker absolute window must not reset')
    intent=dict(job_sha256=digest(job),binding=binding,report_sha256=report['report_sha256'],
        original_failed_file_sha256=sha(auditdir/'FAILED.json'),original_absolute_deadline=deadline,
        remaining_local_seconds=seconds,new_model_calls=0,new_collection_calls=0,new_extraction_calls=0,
        old_failed_audit_not_retried=True,only_previously_unexecuted_oracle_tail=True)
    out=claim(base,args.job,intent)
    timer=threading.Timer(seconds,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        remaining_tail(ROOT,spec,job,auditdir,saved,receipt,dict(attempt_sha256=sha(out/'ATTEMPT.json'),
            exception_report_sha256=report['report_sha256'],original_failure_sha256=intent['original_failed_file_sha256']))
        if time.time()>=deadline:raise TimeoutError('Original absolute closeout expired')
        create(out/'COMPLETED.json',dict(original_failure_retained=True,new_scores=0,
            outputs={n:sha(auditdir/n) for n in OUTPUTS},finished_epoch=time.time(),actual_A3_accepted=False))
    except BaseException as exc:
        create(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),automatic_retry=False,partial_retained=True))
        raise
    finally:timer.cancel()


if __name__=='__main__':main()
