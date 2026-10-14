"""Independently rescore exported main/base/remaining-work artifacts, locally only.

Never connects to Modal, generates text, changes raw evidence, or loads a base
model. Writes one new audit report after all checks pass. A resumed trajectory
must also name its already-verified failed parent export.
"""
import argparse
import datetime
import json
from pathlib import Path

from analyses.e017_audit import audit_predictions
from experiments.sft_allocation_midpoint import checkpoint as ck
from experiments.sft_allocation_midpoint.common import digest, sha
from experiments.sft_allocation_midpoint.completion import inspect_parent
from src.sft_data import read_jsonl

INPUT_SHA = 'a51b59f793136ea9fa86f4f5f254a445f71f2743b6283525979e14828083cd6c'
EVAL = dict(max_new_tokens=512, max_length=2048, eval_batch_size=8)


def read(path):
    return json.loads(Path(path).read_text())


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def verify_selected(root, records, steps):
    for name, record in records.items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'Unsafe artifact path')
        if name.endswith('.pt') and name.split('/')[0] not in {f'checkpoint_{s:04d}' for s in steps}:
            continue
        file = root / name
        require(file.stat().st_size == record['bytes'] and sha(file) == record['sha256'], 'Changed artifact: ' + name)


def audit(args):
    from transformers import AutoTokenizer
    root, inputs = Path(args.export_dir), Path(args.inputs)
    envelope, ledger = read(args.receipt), read(args.ledger)
    receipt, result = envelope['receipt'], envelope['result']
    prefix = f'midpoint/{args.campaign}/'
    require(receipt == ledger[prefix + 'terminal/' + args.run], 'Terminal differs from archived ledger')
    require(receipt['status'] == result['status'] == 'completed', 'Incomplete run')
    files, transport = read(root / 'artifact_manifest.json'), read(root / 'LOCAL_VERIFICATION.json')
    require(files == envelope['artifact_manifest'] and digest(files) == receipt['evidence_sha256'], 'Manifest binding differs')
    require(transport['campaign'] == args.campaign and transport['run'] == args.run, 'Foreign export')
    verify_selected(root, files, transport['full_checkpoint_steps'])
    require(read(root / 'result.json') == result, 'Returned result differs from saved result')
    require(sha(inputs / 'manifest.json') == INPUT_SHA, 'Input release changed')
    for name, record in read(inputs / 'manifest.json')['files'].items():
        require(sha(inputs / name) == record['sha256'], 'Changed input: ' + name)
    tok = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True)
    execution = read(root / 'intent.json')
    kind = execution['config']['kind']
    require(kind in ('main', 'continue_main', 'base'), 'Unsupported run kind')
    require(execution['config']['input_sha256'] == INPUT_SHA, 'Execution input differs')
    intents = {p.stem: read(p) for p in (root / 'intents').glob('*.json')}
    done = {p.stem: read(p) for p in (root / 'completed').glob('*.json')}
    require(set(intents) == set(done), 'Unresolved or unexpected attempted work')
    for unit in intents:
        require(ledger[prefix + args.run + '/unit/' + unit] == intents[unit], 'Intent differs from ledger: ' + unit)
        require(ledger[prefix + args.run + '/done/' + unit] == done[unit], 'Completion differs from ledger: ' + unit)

    parent_targets = parent_processed = start = 0
    parent = None
    if kind == 'continue_main':
        require(args.parent_export is not None, 'Resumed run requires its failed parent export')
        parent = Path(args.parent_export)
        recovery = execution['config']['recovery']
        verify_selected(parent, read(parent / 'failure_manifest.json'), [128])
        _, parent_done = inspect_parent(parent, recovery['failure_manifest_digest'], recovery['checkpoint_manifest'], verify_files=False)
        parent_audit = read(parent / 'LOCAL_PARENT_AUDIT.json')
        require(parent_audit['saved_outputs_verified'] == 128 and parent_audit['unknown_attempted_outputs'] == 8,
                'Prior independent parent audit differs')
        require(parent_audit['failure_manifest_digest'] == recovery['failure_manifest_digest'], 'Foreign parent audit')
        require(read(parent / 'recipe.json') == read(root / 'recipe.json'), 'Resumed scientific recipe changed')
        restored = read(root / 'restore_verification.json')
        require(restored['full_state_equal'] and restored['parent_state_sha256'] == sha(parent / 'checkpoint_0128/state.pt'),
                'Restoration proof differs')
        require(restored['new_optimizer_updates_for_verification'] == 0, 'Unaccounted diagnostic updates')
        parent_state = ck.load(parent / 'checkpoint_0128', read(parent / 'recipe.json')['identity'])
        start, parent_targets, parent_processed = 128, parent_state['supervised_tokens'], parent_state['processed_tokens']
        require(parent_targets == 262077, 'Parent dose differs')

    state_hash = None
    update_units = {u for u in done if u.startswith('update_')}
    if kind != 'base':
        recipe = read(root / 'recipe.json')
        state = ck.load(root / 'checkpoint_0256', recipe['identity'])
        require(transport['full_checkpoint_steps'] == [256], 'Full terminal state not independently exported')
        require(state['step'] == result['committed_updates'] == 256, 'Update total differs')
        require(state['supervised_tokens'] == result['supervised_tokens'] == 524288, 'Target total differs')
        require(recipe['eval'] == EVAL and state['lrs'] == recipe['lrs'], 'Numerical recipe differs')
        schedule = read(inputs / f"{recipe['arm']}_seed{recipe['seed']}.json")['updates']
        require(state['schedule'] == schedule, 'Training schedule differs')
        require(update_units == {f'update_{i:04d}' for i in range(start + 1, 257)}, 'New update set differs')
        targets, processed = parent_targets, parent_processed
        for step in range(start + 1, 257):
            unit = f'update_{step:04d}'
            intent, returned = intents[unit], done[unit]
            require(all(returned.get(k) == v for k, v in intent.items()), 'Update differs from intent')
            require(intent['indices'] == schedule[step - 1] and intent['lr'] == state['lrs'][step - 1], 'Frozen update changed')
            targets += returned['supervised_tokens']
            processed += returned['processed_tokens']
            require((targets, processed) == (returned['cumulative_targets'], returned['cumulative_processed']), 'Cumulative dose gap')
        require((targets, processed) == (state['supervised_tokens'], state['processed_tokens']), 'Final state dose differs')
        state_hash = sha(root / 'checkpoint_0256/state.pt')
    else:
        require(not update_units and result['committed_updates'] == 0, 'Base run contains training')

    observed, endpoint = read_jsonl(inputs / 'observed80.jsonl'), read_jsonl(inputs / 'endpoint431.jsonl')
    jobs = [('endpoint431', endpoint, result['endpoint'])]
    if kind == 'main':
        jobs = [(f'observed80_step{s}', observed, result['curve'][str(s)]) for s in (64, 128, 256)] + jobs
    elif kind == 'continue_main':
        jobs = [('observed80_step128_remaining', observed[56:], None),
                ('observed80_step256', observed, result['curve']['256'])] + jobs
    evaluations, all_expected, new_output_count = {}, set(update_units), 0
    for ev, rows, expected in jobs:
        saved = []
        for pos in range(0, len(rows), EVAL['eval_batch_size']):
            unit = f'{ev}_batch_{pos:04d}'
            all_expected.add(unit)
            scored, rawfile = root / ev / f'batch_{pos:04d}_scored.jsonl', root / ev / f'batch_{pos:04d}_raw.json'
            part = rows[pos:pos + EVAL['eval_batch_size']]
            require(intents[unit] == dict(problem_ids=[r['problem_id'] for r in part], count=len(part), config=EVAL), 'Generation intent changed')
            require(sha(scored) == done[unit]['scored_sha256'] and sha(rawfile) == done[unit]['raw_sha256'], 'Raw/scored receipt hash differs')
            raw, rescored = read(rawfile), audit_predictions(scored, part, tok, EVAL)
            require(raw['problem_ids'] == [r['problem_id'] for r in part], 'Generated roster differs')
            require(raw['batch_output_ids'] == [r['batch_output_ids'] for r in rescored], 'Raw token returns differ')
            require(raw['events'] == [r['stop'] for r in rescored], 'Raw stopping events differ')
            require(done[unit]['count'] == len(rescored), 'Output dose differs')
            saved.extend(rescored)
        summary = read(root / ev / 'summary.json')
        qc = {r['problem_id']: r['task_score']['task_answer_correct'] for r in saved}
        require(len(qc) == len(rows) and all(type(v) is bool for v in qc.values()), 'Missing/duplicate/unknown endpoint outcome')
        require(qc == summary['question_correct'] and sum(qc.values()) == summary['correct'], 'Summary score differs')
        require(expected is None or expected == summary, 'Result envelope summary differs')
        evaluations[ev] = dict(n=len(saved), correct=sum(qc.values()))
        new_output_count += len(saved)
    require(set(done) == all_expected, 'Extra unit outside frozen remaining work')
    require(new_output_count == result['physical_generated_outputs'], 'Physical generation total differs')

    parent_evidence = None
    if kind == 'continue_main':
        qc = {}
        for pos in range(0, 48, 8):
            for row in read_jsonl(parent / 'observed80_step128' / f'batch_{pos:04d}_scored.jsonl'):
                qc[row['problem_id']] = row['task_score']['task_answer_correct']
        qc.update(read(root / 'observed80_step128_remaining/summary.json')['question_correct'])
        qc.update({row['problem_id']: None for row in observed[48:56]})
        partial = read(root / 'observed80_step128_reconciled.json')
        require(partial['question_correct'] == qc and partial == result['curve']['128'], 'Partial diagnostic mapping differs')
        require(partial['known_n'] == 72 and partial['unknown_n'] == 8 and partial['known_correct'] == sum(v is True for v in qc.values()), 'Unknown diagnostic outcomes changed')
        require(result['curve']['64'] == read(parent / 'observed80_step64/summary.json'), 'Parent diagnostic changed')
        require(result['new_committed_updates'] == 128 and result['new_supervised_tokens'] == 262211, 'Resumed dose claim differs')
        require(new_output_count == 535 and result['parent_saved_outputs'] == 128 and result['unknown_attempted_outputs'] == 8,
                'Parent/child output accounting differs')
        require(result['total_saved_outputs'] == 663, 'Combined saved-output count differs')
        parent_evidence = dict(manifest_digest=recovery['failure_manifest_digest'],
                               prior_independent_audit_sha256=sha(parent / 'LOCAL_PARENT_AUDIT.json'),
                               saved_outputs_previously_verified=128, unknown_attempted_outputs=8)
    return dict(schema='independent_local_midpoint_audit_v2', checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                campaign=args.campaign, run=args.run, kind=kind, terminal_receipt=receipt,
                artifact_manifest_digest=digest(files), export=transport, state_sha256=state_hash,
                new_updates_verified=len(update_units), new_outputs_rescored=new_output_count,
                evaluations=evaluations, parent=parent_evidence, new_model_calls=0, raw_evidence_changed=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('campaign', 'run', 'export-dir', 'receipt', 'ledger', 'inputs', 'tokenizer', 'out'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--parent-export')
    args = p.parse_args()
    require(not Path(args.out).exists(), 'Refuse to overwrite prior audit')
    report = audit(args)
    with Path(args.out).open('x') as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report))
