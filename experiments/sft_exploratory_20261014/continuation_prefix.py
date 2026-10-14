"""Read-only exact stopped-parent binding. Never generates, trains or acknowledges it."""
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read, sha, digest, verify
from src.sft_data import read_jsonl

PARENT = 'exploratory-20261014-r1'
COUNTS = {'base_4shot': 272, 'instruct_0shot': 144, 'wrong_teacher_t1': 80}


def inspect_prefix(root, inputs, ledger, logical, original_spec):
    root, inputs = Path(root), Path(inputs)
    base = 'midpoint/' + PARENT + '/'
    cfg = original_spec['configs'][logical]
    terminal, claim = ledger[base+'terminal/'+logical], ledger[base+'claim/'+logical]
    bound = ledger[base+'intent/'+logical]
    sent = read(root/'intent.json')
    failure = read(root/'failure_manifest.json')
    if (terminal['status'] != 'failed' or terminal['claim_sha256'] != digest(claim) or
            terminal['evidence_sha256'] != digest(failure) or claim['intent_sha256'] != digest(bound) or
            bound['config_sha256'] != digest(cfg) or bound['data_sha256'] != cfg['input_sha256'] or
            bound['source_sha256'] != digest(original_spec['source_files']) or
            sent['config'] != cfg or sent['plan'] != original_spec['plan'] or
            sent['release']['source_files'] != original_spec['source_files'] or
            read(root/'admission.json') != original_spec):
        raise ValueError('Original failed parent/source/claim binding differs')
    # Hash the preserved scientific prefix; state.pt has a separately verified
    # manifest and is checked by checkpoint.load in the paid child exactly once.
    files = {n: r for n, r in failure.items() if not n.endswith('.pt')}
    verify(root, files)
    rows = read_jsonl(inputs/'gsm8k_test1319.jsonl')
    if len(rows) != 1319 or len({r['problem_id'] for r in rows}) != 1319:
        raise ValueError('Endpoint identity roster differs')
    attempts = sorted(p.stem for p in (root/'intents').glob('endpoint1319_batch_*.json'))
    starts = [int(n.rsplit('_',1)[1]) for n in attempts]
    offset = COUNTS[logical]
    if starts != list(range(0, offset, 16)):
        raise ValueError('Unattempted/ambiguous prefix: never regenerate it')
    remote_units = {k.removeprefix(base+logical+'/unit/') for k in ledger
                    if k.startswith(base+logical+'/unit/endpoint1319_batch_')}
    if remote_units != set(attempts):
        raise ValueError('Remote attempted prefix differs')
    predictions, batches = [], []
    expected_files = set()
    for start, unit in zip(starts, attempts):
        rf = f'endpoint1319/batch_{start:04d}_raw.json'
        sf = f'endpoint1319/batch_{start:04d}_scored.jsonl'
        raw, scored = read(root/rf), read_jsonl(root/sf)
        ids = [r['problem_id'] for r in rows[start:start+16]]
        intent = read(root/'intents'/(unit+'.json'))
        if (intent != ledger[base+logical+'/unit/'+unit] or intent['problem_ids'] != ids or
                raw['problem_ids'] != ids or [r['problem_id'] for r in scored] != ids or
                len(scored) != 16 or len(raw['batch_output_ids']) != 16):
            raise ValueError('Saved batch identities/attempts differ')
        donepath = root/'completed'/(unit+'.json')
        ack = ledger.get(base+logical+'/done/'+unit)
        if donepath.exists() != (ack is not None):
            raise ValueError('Parent acknowledgement ambiguity')
        if ack is not None and (read(donepath) != ack or ack != dict(count=16,raw_sha256=sha(root/rf),scored_sha256=sha(root/sf))):
            raise ValueError('Parent original acknowledgement differs')
        expected_files.update((rf,sf)); predictions.extend(scored)
        batches.append(dict(start=start,count=16,raw_file=rf,scored_file=sf,
                            raw_sha256=sha(root/rf),scored_sha256=sha(root/sf),
                            original_ack_present=ack is not None))
    actual = {str(p.relative_to(root)) for p in (root/'endpoint1319').glob('*') if p.is_file()}
    if actual != expected_files or len(predictions) != offset:
        raise ValueError('Uninventoried saved output must be reconciled before any child')
    expected_done = {n for n in attempts[:-1]}
    if {n for n in attempts if (root/'completed'/(n+'.json')).exists()} != expected_done:
        raise ValueError('Exact stopped unacknowledged last batch differs')
    return dict(logical_run=logical,parent_campaign=PARENT,parent_status='failed',
                original_claim=claim,original_terminal=terminal,original_intent=bound,
                parent_failure_manifest_sha256=sha(root/'failure_manifest.json'),
                parent_failure_manifest_digest=digest(failure),
                parent_compact_files=files,offset=offset,remaining=1319-offset,
                saved_problem_ids=[r['problem_id'] for r in predictions],batches=batches,
                original_unacknowledged_rows=16,parent_ack_modified=False), predictions
