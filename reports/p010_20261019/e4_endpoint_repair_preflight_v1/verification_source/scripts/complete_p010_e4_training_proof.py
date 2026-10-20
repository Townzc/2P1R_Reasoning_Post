"""Finish only the unattempted E4 state/dose tail after a bound local failure.

The original encoding prefix, failure and source snapshots remain immutable.
No tokenizer, model, generation, remote request or original output overwrite.
"""
import argparse
import json
from pathlib import Path

from experiments.p010.common import read, dump, sha, digest, verify, utc
from experiments.p010.e4_evidence import verify_training_after_encoding

PREFIXES = {
    400: 'b5a083e266ef80ba1a5ab1f2a8257e84ecacad1331b8308a457fbdaea0e04809',
    3200: '593667ca83670853a348b5071636dcf92b54621bf7ad85dbbd4c320f31c75e01',
}
OLD_SCRIPT = '6224b5fde91eb1d71c259dd77f51d25d034055c350bdf515dfd936bb146cf656'
OLD_EVIDENCE = '35ebeac49eb7fd4ff63568b778ba3f40c1ac7284b9367fa0902644b50dd42651'


def confirmed_prefix(root, n):
    prefix = root/'e4_training_oracles_r1'/f'n{n}'
    file = prefix/'CONFIRMED_PREFIX.json'; p = read(file)
    failure = read(prefix/'FAILED.json')
    version = root/'e4_oracle_prefix_version_r1'
    log = root/f'e4_full_training_oracle_n{n}_r2.log'
    if (sha(file) != PREFIXES[n] or p['run'] != f'e4_s17_n{n}'
            or p['exit_code'] != 1 or p['checkpoint_load_reached'] is not False
            or p['tokenizer_load_and_encoding_performed'] is not True
            or p['failed_file_sha256'] != sha(prefix/'FAILED.json')
            or p['intent_file_sha256'] != sha(prefix/'INTENT.json')
            or p['log_sha256'] != sha(log)
            or p['oracle_script_sha256'] != OLD_SCRIPT
            or p['evidence_module_sha256'] != OLD_EVIDENCE
            or sha(version/'audit_p010_e4_preserved_training.py') != OLD_SCRIPT
            or sha(version/'e4_evidence.py') != OLD_EVIDENCE
            or failure['error'] != 'Full original recipe, exposure or trajectory differs'
            or 'line 31, in verify_training' not in log.read_text()
            or (prefix/'COMPLETED.json').exists()):
        raise ValueError('Only the exact confirmed encoding prefixes may be reused')
    return p


def complete(root, n, out):
    root, out = Path(root), Path(out)
    prefix = confirmed_prefix(root, n)
    preservation = root/'e4_failure_preservation_r1'/f'n{n}'
    evidence = preservation/'evidence'; inputs = root/'inputs'
    receipt = root/f'e4_n{n}_r1'; sent = read(receipt/'SUBMITTED.json')
    spec_path = Path('reports/p010_20261019/e4_runtime_v1/SPEC.json')
    spec = read(spec_path); done = read(preservation/'COMPLETED.json')
    if (sha(preservation/'COMPLETED.json') != prefix['original_preservation_completed_sha256']
            or done['manifest_sha256'] != sha(preservation/'MANIFEST.json')
            or done['provider_stopped'] is not True or done['raw_files'] != 0
            or done['any_endpoint_intent_or_ack'] is not False):
        raise ValueError('Original confirmed preservation changed')
    verify(evidence, read(preservation/'MANIFEST.json')); verify(inputs, spec['input_files'])
    for name, expected in spec['source_files'].items():
        if sha(name) != expected:
            raise ValueError('Original runtime source changed: '+name)
    identity = read(evidence/'INTENT.json')['identity']
    ledger = read(preservation/'LEDGER.json'); run = f'e4_s17_n{n}'
    out.mkdir(parents=True, exist_ok=False)
    dump(out/'INTENT.json', dict(run=run, utc=utc(), confirmed_prefix_sha256=PREFIXES[n],
        new_training=0, new_generations=0, new_tokenizations=0,
        first_state_load=True, automatic_retry=False, original_failure_preserved=True))
    try:
        trained = verify_training_after_encoding(evidence, inputs, spec, run, identity, ledger)
        merge = read(evidence/'MERGE_PROOF.json')
        proof = dict(passed=True, run=run, original_app_id=sent['app_id'], original_call_id=sent['call_id'],
            updates_verified=1024, targets_verified=trained['targets'], processed_tokens_verified=trained['processed'],
            state_sha256=trained['state_sha256'], original_identity=identity,
            original_preservation_sha256=sha(preservation/'COMPLETED.json'),
            original_manifest_sha256=sha(preservation/'MANIFEST.json'),
            original_error_sha256=sha(receipt/'ERROR.json'), original_claim=ledger['e4/'+run+'/claim'],
            original_failed_terminal=ledger['e4/'+run+'/terminal'], full_state_loaded_once=True,
            confirmed_encoding_prefix_sha256=PREFIXES[n], new_tokenizations=0,
            no_endpoint_intent_or_raw=True, original_run_stays_failed=True,
            merged_files=merge['merged_files'], merged_remote_bytes_reverification_required=True,
            training_block_seconds=trained['train_seconds'], original_spec_sha256=sha(spec_path),
            original_source_files=spec['source_files'], no_retry_authorization_granted=True,
            independent_review_pending=True, new_training=0, new_generations=0, utc=utc())
        dump(out/'COMPLETED.json', proof)
        return {k:v for k,v in proof.items() if k not in ('original_identity','merged_files','original_source_files','training_block_seconds')}
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),partial_evidence_preserved=True,automatic_retry=False))
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('--root',required=True)
    p.add_argument('--n',type=int,choices=tuple(PREFIXES),required=True);p.add_argument('--out',required=True)
    args=p.parse_args();print(json.dumps(complete(args.root,args.n,args.out)))
