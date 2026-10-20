"""Verify one newly preserved E4 final checkpoint once; no evaluation replay."""
import argparse
import json
from pathlib import Path

from experiments.p010.common import read, dump, sha, digest, verify, utc
from experiments.p010.e4_evidence import verify_training
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps


def endpoint_wrapper_failure(failure):
    import re
    # Python 3.12 made slice hashable: the same original dict slice raises
    # KeyError there, whereas the local older interpreter raises TypeError.
    known = {('TypeError', "unhashable type: 'slice'"),
             ('KeyError', 'slice(0, 256, None)')}
    source = Path(__file__).resolve().parents[1]/'experiments/p010/modal_e4.py'
    # Modal's serialized worker traceback retains the source location but can
    # omit the line text. Bind that exact location to the frozen source bytes.
    if sha(source) != '81271eee05a8342d6e74b110ec1a7435f1cc5da52426ea418999d76f651d9d00':
        return False
    trace = failure.get('traceback', '')
    location = re.search(r'File "[^"\n]*/experiments/p010/modal_e4\.py", line (\d+), in worker\n', trace)
    if location is None:
        return False
    number = int(location.group(1))
    lines = source.read_text().splitlines()
    return ((failure.get('type'), failure.get('error')) in known
            and 0 < number <= len(lines)
            and 'part=rows[startrow:startrow+256]' in lines[number-1])


def audit(args):
    from transformers import AutoTokenizer
    receipt, preservation, inputs = Path(args.receipt), Path(args.preservation), Path(args.inputs)
    root = preservation/'evidence'; spec = read(args.spec); sent = read(receipt/'SUBMITTED.json')
    local = read(receipt/'INTENT.json'); done = read(preservation/'COMPLETED.json')
    ledger = read(preservation/'LEDGER.json'); provider = read(preservation/'PROVIDER_PRIVATE.json')
    n = sent['n']; run = 'e4_s17_n'+str(n); prefix = 'e4/'+run+'/'
    if (n not in (400, 3200) or local['n'] != n or done['run'] != run
            or done['app_id'] != sent['app_id'] or done['call_id'] != sent['call_id']
            or done['provider_stopped'] is not True or done['raw_files'] != 0
            or done['any_endpoint_intent_or_ack'] is not False
            or done['complete_checkpoint_file_present'] is not True
            or (preservation/'FAILED.json').exists() or (receipt/'RESULT.json').exists()
            or done['manifest_sha256'] != sha(preservation/'MANIFEST.json')):
        raise ValueError('Exact original failure, full checkpoint and zero endpoint work required')
    validate_stopped_apps([sent['app_id']], provider['original_info'], provider['owned'])
    review = read(args.review)
    if (review['decision'] not in ('PASS', 'PASS-WITH-NOTES')
            or review['scope'] != 'p010-C8-A1-A2' or review['spec_sha256'] != sha(args.spec)
            or sha(review['local_report_file']) != review['report_sha256'] or review != local['review']):
        raise ValueError('Actual original combined input/runtime review required')
    for name, expected in spec['source_files'].items():
        if sha(name) != expected:
            raise ValueError('Original frozen source differs: '+name)
    original = read(root/'INTENT.json'); failure = read(root/'FAILURE.json')
    config = read(inputs/f'e4_n{n}_config.json')
    identity = dict(run_id=run, config=config, input_files=spec['input_files'],
        base_files=spec['model']['files'], execution=local['execution'], source_files=spec['source_files'],
        A1_A2_review={k: v for k, v in review.items() if k != 'local_report_file'})
    if (original['identity'] != identity or original['claim'] != ledger[prefix+'claim']
            or original['claim']['execution'] != local['execution'] or original['claim']['run'] != run
            or ledger[prefix+'terminal'] != done['original_failed_terminal']
            or ledger[prefix+'terminal']['status'] != 'failed'
            or not endpoint_wrapper_failure(failure)
            or abs(original['hard_deadline_epoch']-original['worker_start_epoch']-4500) > .001):
        raise ValueError('Exact original execution and endpoint wrapper failure differ')
    verify(root, read(preservation/'MANIFEST.json'))
    verify(inputs, spec['input_files'])
    out = Path(args.out); out.mkdir(parents=True, exist_ok=False)
    dump(out/'INTENT.json', dict(run=run, utc=utc(), original_preservation_sha256=sha(preservation/'COMPLETED.json'),
        original_failed_call_retained=True, new_generations=0, full_state_load_once=True, automatic_retry=False))
    try:
        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True)
        for name in ('tokenizer.json', 'tokenizer_config.json', 'config.json'):
            if sha(Path(args.tokenizer)/name) != spec['model']['files'][name]['sha256']:
                raise ValueError('Original pinned OLMo tokenizer/model configuration differs')
        trained = verify_training(root, inputs, spec, run, identity, ledger, tokenizer)
        merge = read(root/'MERGE_PROOF.json')
        proof = dict(passed=True, run=run, original_app_id=sent['app_id'], original_call_id=sent['call_id'],
            updates_verified=1024, targets_verified=trained['targets'], processed_tokens_verified=trained['processed'],
            state_sha256=trained['state_sha256'], original_identity=identity,
            original_preservation_sha256=sha(preservation/'COMPLETED.json'),
            original_manifest_sha256=sha(preservation/'MANIFEST.json'),
            original_error_sha256=sha(receipt/'ERROR.json'), original_claim=ledger[prefix+'claim'],
            original_failed_terminal=ledger[prefix+'terminal'], full_state_loaded_once=True,
            no_endpoint_intent_or_raw=True, original_run_stays_failed=True,
            merged_files=merge['merged_files'], merged_remote_bytes_reverification_required=True,
            training_block_seconds=trained['train_seconds'], original_spec_sha256=sha(args.spec),
            original_source_files=spec['source_files'], no_retry_authorization_granted=True,
            independent_review_pending=True, new_training=0, new_generations=0, utc=utc())
        dump(out/'COMPLETED.json', proof); return proof
    except BaseException as exc:
        dump(out/'FAILED.json', dict(type=type(exc).__name__, error=str(exc),
            partial_evidence_preserved=True, automatic_retry=False))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('receipt', 'preservation', 'inputs', 'spec', 'review', 'tokenizer', 'out'):
        parser.add_argument('--'+name, required=True)
    value = audit(parser.parse_args())
    print(json.dumps({k: v for k, v in value.items() if k not in ('original_identity', 'merged_files', 'original_source_files')}))
