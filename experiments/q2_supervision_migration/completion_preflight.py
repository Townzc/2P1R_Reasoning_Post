"""Finite saved-output comparability gate; Linux CPU only, no new model output."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import platform
import sys
import time

from .contracts import read_records, identity_hash
from .gpu_profile import ProfileError, durable_json, launch_guarded, sha256
from .screen_scoring import load_problems, load_references, score_pair
from .scoring_preflight import saved_inputs
from .screen_runtime import extract_code


def saved_sample(phase, batch_index, index):
    matches=[]
    for d in (Path(phase)/'batches').iterdir():
        intent,=read_records(d/'intent.jsonl')
        if intent['batch_index']==batch_index: matches.append((d,intent))
    if len(matches)!=1: raise ProfileError('exact immutable batch missing or duplicated')
    d,intent=matches[0];rows=read_records(d/'batch.jsonl')
    if rows[0]!=intent: raise ProfileError('batch intent mismatch')
    sample=rows[index+1]
    backend=json.loads((d/'generation_return.json').read_text())
    inputs=json.loads((d/'scoring_inputs.json').read_text());code=inputs['codes'][index]
    if (sample['sample_index']!=index or sample['intent_sha256']!=intent['record_sha256']
        or sample['task_id']!=intent['tasks'][index]
        or sample['completion_text']!=backend['decoded_text'][index]
        or sample['completion_token_ids']!=backend['completion_ids'][index]
        or code!=extract_code(sample['completion_text'])
        or identity_hash({'code':code})!=inputs['code_sha256'][index]):
        raise ProfileError('saved candidate evidence changed')
    return sample,code


_AUTHORED = [
    ('valid', 'def fixture(x):\n    return x', 'pass'),
    ('wrong', 'def fixture(x):\n    return x+1', 'fail'),
    ('syntax', 'this is invalid syntax !', 'fail'),
    ('init', 'raise ValueError("authored initialization failure")', 'fail'),
    ('test_timeout', 'def fixture(x):\n    while True: pass', 'fail'),
]
_FAILURES = [('R599', 'continuation_root', 'R_future', 25, 8, 'Mbpp/599', 'extra', 34),
             ('C260', 'v2_root', 'C_prefix', 100, 2, 'Mbpp/260', 'base', 0)]
_SENTINELS = [('W_prefix', 'v2_root', 'Mbpp/599', 10, range(8, 16)),
              ('W_prefix', 'v2_root', 'Mbpp/260', 100, range(8)),
              ('W_future', 'continuation_root', 'Mbpp/599', 25, range(8, 16)),
              ('W_future', 'continuation_root', 'Mbpp/260', 52, range(8))]


def expected_items():
    return ([f'authored_{name}' for name, _, _ in _AUTHORED] + ['original96_inventory'] +
            [f'original96_{b:03d}_{i:02d}' for b in range(6) for i in range(16)] +
            [f'sentinel_{phase}_{batch:03d}_{i:02d}'
             for phase, _, _, batch, indices in _SENTINELS for i in indices] +
            [f'{label}_{repeat}' for repeat in range(3) for label, *_ in _FAILURES])


class DiagnosticCollector:
    """One finite attempt per item. A bad verdict cannot hide later diagnostics."""
    def __init__(self, out, deadline_epoch):
        self.out = Path(out)
        self.deadline_epoch = deadline_epoch
        self.checks = self.out / 'checks'
        self.checks.mkdir(exist_ok=False)

    def remaining(self):
        return max(0.0, self.deadline_epoch - time.time())

    def run(self, name, operation):
        # Reserve before execution; the parent can distinguish unfinished work
        # after its hard process-group deadline. Never overwrite or retry an item.
        started = time.time()
        durable_json(self.checks / f'{name}.intent.json', {
            'item': name, 'started_epoch': started,
            'deadline_epoch': self.deadline_epoch, 'attempt': 1})
        record = {'item': name, 'attempted': False, 'completed': False,
                  'blockers': [], 'warnings': [], 'payload': None}
        if self.remaining() <= 0:
            record['blockers'].append('shared_diagnostic_deadline')
        else:
            record['attempted'] = True
            try:
                payload, blockers, warnings = operation()
                record.update(payload=payload, blockers=list(blockers), warnings=list(warnings))
            except Exception as exc:
                record['blockers'].append('item_error')
                record['error'] = repr(exc)
            record['completed'] = True
        record['elapsed_seconds'] = max(0.0, time.time() - started)
        durable_json(self.checks / f'{name}.result.json', record)
        return record


def run_diagnostics(a, problems, refs, diagnose_timeout, checker, collector):
    """All bounded checks, without early exit on UNKNOWN or mismatched rewards.

    Known regressions precede the longer timeout fixtures; the two failure
    fixtures then alternate across three fixed repeats. No passing replay is
    selected and no model work is performed here.
    """
    for name, code, wanted in _AUTHORED:
        def authored(code=code, wanted=wanted):
            result = diagnose_timeout({'base_input': [[1]], 'entry_point': 'fixture', 'atol': 0},
                code, [1], [.01], suite='base', original_details=[],
                outer_cap_seconds=min(180.0, collector.remaining()))
            blockers = [] if result.get('verified_suite_verdict') == wanted else ['authored_control_failed']
            return result, blockers, []
        collector.run(f'authored_{name}', authored)

    # Inventory failure is reported, but individually verified other samples are
    # still useful diagnostic evidence and remain bounded to the original 96.
    inventory = {}
    def inventory_check():
        rows = saved_inputs(a.initial_root)
        if [(b, i) for b, i, _, _ in rows] != [(b, i) for b in range(6) for i in range(16)]:
            raise ProfileError('original96 inventory differs from frozen six batches')
        inventory.update({(b, i): (old, code) for b, i, old, code in rows})
        return {'samples': len(rows)}, [], []
    collector.run('original96_inventory', inventory_check)

    def compare(old, code, task=None):
        if task is not None and old['task_id'] != task:
            raise ProfileError('wrong sentinel task')
        task = old['task_id']
        pair = score_pair(problems[task], refs[task], code, checker,
                          fast_check=True, guarded_scoring_v2=True)
        known = all(old[k]['status'] in ('pass', 'fail') for k in ('base', 'extra'))
        resolved = all(pair[k]['status'] in ('pass', 'fail') for k in ('base', 'extra'))
        equal = all(old[k]['status'] == pair[k]['status'] for k in ('base', 'extra'))
        payload = {'sample_id': old['sample_id'], 'old': {k: old[k] for k in ('base', 'extra')},
                   'new': pair, 'known': known, 'resolved': resolved, 'equal': equal}
        blockers = ([] if resolved else ['unresolved_score']) + ([] if not known or not resolved or equal else ['known_reward_changed'])
        return payload, blockers, []

    for batch in range(6):
        for index in range(16):
            def original(batch=batch, index=index):
                pair = inventory.get((batch, index))
                if pair is None:
                    pair = saved_sample(Path(a.initial_root) / 'W_prefix', batch, index)
                return compare(*pair)
            collector.run(f'original96_{batch:03d}_{index:02d}', original)

    for phase, root, task, batch, indices in _SENTINELS:
        for index in indices:
            def sentinel(phase=phase, root=root, task=task, batch=batch, index=index):
                old, code = saved_sample(Path(getattr(a, root)) / phase, batch, index)
                payload, blockers, warnings = compare(old, code, task)
                if not payload['known']:
                    blockers.append('sentinel_original_not_known')
                return payload, blockers, warnings
            collector.run(f'sentinel_{phase}_{batch:03d}_{index:02d}', sentinel)

    for repeat in range(3):
        for label, root, phase, batch, index, task, suite, nold in _FAILURES:
            def failure(root=root, phase=phase, batch=batch, index=index, task=task, suite=suite, nold=nold):
                old, code = saved_sample(Path(getattr(a, root)) / phase, batch, index)
                if old['task_id'] != task or old[suite]['status'] != 'timeout':
                    raise ProfileError('wrong failure fixture')
                detail = json.loads(old[suite]['detail'])
                if detail['tests_observed'] != nold or detail['test_passes_observed'] != nold:
                    raise ProfileError('original timeout prefix is not verified')
                key = 'plus' if suite == 'extra' else 'base'
                result = diagnose_timeout(problems[task], code, refs[task][key], refs[task][key + '_time'],
                    suite=suite, original_details=[True] * nold,
                    outer_cap_seconds=min(180.0, collector.remaining()))
                payload = {'sample_id': old['sample_id'], 'code_sha256': identity_hash({'code': code}),
                           'old': old[suite], 'diagnosis': result, 'diagnostic_only': True,
                           'historical_result_changed': False}
                blockers = [] if result.get('verified_suite_verdict') in ('pass', 'fail') else ['failure_recovery_unresolved']
                warnings = ['historical_prefix_conflict'] if result.get('prefix_consistent') is False else []
                return payload, blockers, warnings
            collector.run(f'{label}_{repeat}', failure)


def summarize_diagnostics(a, *, execution_completed):
    """Parent-side summary survives a killed worker and never manufactures scores."""
    out = Path(a.out)
    records = {}
    blockers, warnings, unfinished = [], [], []
    for name in expected_items():
        path = out / 'checks' / f'{name}.result.json'
        if not path.exists():
            unfinished.append(name)
            blockers.append({'item': name, 'reason': 'unfinished' if (out / 'checks' / f'{name}.intent.json').exists() else 'not_started'})
            continue
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            unfinished.append(name)
            blockers.append({'item': name, 'reason': 'unreadable_result', 'error': repr(exc)})
            continue
        valid_record = (isinstance(record, dict) and record.get('item') == name and
                        type(record.get('completed')) is bool and
                        type(record.get('attempted')) is bool and
                        all(isinstance(record.get(key), list) and
                            all(isinstance(value, str) for value in record[key])
                            for key in ('blockers', 'warnings')) and
                        'payload' in record and
                        (record['payload'] is None or isinstance(record['payload'], dict)))
        if not valid_record:
            unfinished.append(name)
            blockers.append({'item': name, 'reason': 'invalid_record'})
            continue
        records[name] = record
        if not record.get('completed'):
            unfinished.append(name)
        blockers.extend({'item': name, 'reason': x} for x in record['blockers'])
        warnings.extend({'item': name, 'reason': x} for x in record['warnings'])
    if not execution_completed:
        blockers.append({'item': 'worker', 'reason': 'execution_incomplete'})
    if (out / 'preflight_failure.json').exists():
        blockers.append({'item': 'worker', 'reason': 'worker_failure_recorded'})
    def payload(name):
        return records.get(name, {}).get('payload') or {}
    originals = [payload(f'original96_{b:03d}_{i:02d}') for b in range(6) for i in range(16)]
    counts = {'original_saved_outputs': sum(bool(x) for x in originals),
              'previous_known_pairs': sum(x.get('known') is True for x in originals),
              'matched_pairs': sum(x.get('known') is True and x.get('equal') is True for x in originals),
              'resolved_pairs': sum(x.get('resolved') is True for x in originals),
              'known_W_sentinels_matched': sum(payload(name).get('known') is True and payload(name).get('equal') is True
                                             for name in expected_items() if name.startswith('sentinel_'))}
    if list(counts.values()) != [96, 90, 90, 96, 32]:
        blockers.append({'item': 'coverage', 'reason': 'exact_regression_coverage_not_met'})
    controls = [name for name, _, _ in _AUTHORED
                if records.get(f'authored_{name}', {}).get('completed') and
                not records[f'authored_{name}']['blockers']]
    diagnoses = []
    for label, *_ in _FAILURES:
        verdicts = [payload(f'{label}_{repeat}').get('diagnosis', {}).get('verified_suite_verdict') for repeat in range(3)]
        diagnoses.append({'fixture': label, 'verdicts': verdicts})
        if any(v not in ('pass', 'fail') for v in verdicts) or len(set(verdicts)) != 1:
            blockers.append({'item': label, 'reason': 'repeat_verdicts_unresolved_or_disagree'})
        if label == 'C260' and verdicts != ['fail'] * 3:
            blockers.append({'item': label, 'reason': 'initialization_failure_not_reproduced'})
    identity_path = out / 'reference_identity.json'
    try:
        refhash = json.loads(identity_path.read_text()).get('reference_manifest_sha256') if identity_path.exists() else None
    except (OSError, ValueError, AttributeError):
        refhash = None
    if not isinstance(refhash, str) or len(refhash) != 64 or any(c not in '0123456789abcdef' for c in refhash):
        blockers.append({'item': 'references', 'reason': 'verified_reference_identity_missing'})
    completed = not unfinished and execution_completed
    admitted = completed and not blockers
    return {'schema': 2, 'diagnostics_completed': completed, 'model_admitted': admitted,
            'passed': admitted, 'source_commit': a.source_commit,
            'plan_sha256': '351b33126af0b2457377a24ebb6618923e627f362cc8e06cfb69f390ae93806f',
            'blockers': blockers, 'warnings': warnings, 'unfinished_items': unfinished,
            'planned_items': len(expected_items()), 'recorded_items': len(records),
            'diagnoses': diagnoses, 'authored_controls_passed': controls, **counts,
            'reward_semantics_unchanged': admitted, 'reward_semantics_changed': False,
            'historical_records_relabelled': False, 'new_generations': 0, 'optimizer_updates': 0,
            'reference_manifest_sha256': refhash,
            'scope': 'finite saved-output diagnostics; completion is separate from model admission; no universal timing-equivalence claim'}


def worker(a):
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    from .scoring_cpu import pin_scoring_cpu
    out = Path(a.out)
    durable_json(out / 'scoring_cpu_placement.json', pin_scoring_cpu())
    from .scoring_guard_v2 import diagnose_timeout
    from evalplus.eval import untrusted_check
    intent = json.loads((out / 'preflight_intent.json').read_text())
    collector = DiagnosticCollector(out, intent['deadline_epoch'] - 10.0)
    problems = load_problems(a.data_json, a.data_sha256)
    refs, manifest = load_references(a.references)
    if manifest['data_sha256'] != a.data_sha256:
        raise ProfileError('reference identity mismatch')
    durable_json(out / 'reference_identity.json', {'reference_manifest_sha256': sha256(Path(a.references) / 'manifest.json')})
    run_diagnostics(a, problems, refs, diagnose_timeout, untrusted_check, collector)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['initial-root','v2-root','continuation-root','references','data-json','data-sha256','out','source-commit']:
        p.add_argument('--'+name,required=True)
    p.add_argument('--provider-deadline-epoch',type=float,required=True)
    p.add_argument('--execute-saved-output-preflight',action='store_true')
    p.add_argument('--_worker',action='store_true')
    a=p.parse_args()
    if platform.system()!='Linux' or not a.execute_saved_output_preflight: raise ProfileError('explicit Linux-only saved-code gate')
    if a._worker:
        if os.environ.get('Q2_PROFILE_PARENT_PID')!=str(os.getppid()): raise ProfileError('owned parent required')
        try: worker(a)
        except BaseException as exc:
            durable_json(Path(a.out)/'preflight_failure.json',{'error':repr(exc),'model_admitted':False})
            os._exit(1)
        os._exit(0)
    cap=min(1200.0,a.provider_deadline_epoch-600-time.time())
    if cap<=0: raise ProfileError('no diagnostic window remains')
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    durable_json(out/'preflight_intent.json',{'source_commit':a.source_commit,'cap_seconds':cap,
        'failure_fixtures_repeats':{'R599':3,'C260':3},'saved_original_outputs':96,'known_W_sentinels':32,
        'new_generations':0,'optimizer_updates':0,'started_epoch':time.time(),
        'deadline_epoch':time.time()+cap,'planned_items':expected_items(),
        'order':'authored, original96, W32, alternating failure repeats',
        'on_item_error':'record and continue within shared deadline; never retry'})
    result = 1
    try:
        result = launch_guarded([sys.executable,'-m','experiments.q2_supervision_migration.completion_preflight',
            *sys.argv[1:],'--_worker'],out,cap,phase='cpu')
    finally:
        summary = summarize_diagnostics(a, execution_completed=result == 0)
        durable_json(out/'diagnostic_summary.json', summary)
        if summary['model_admitted']:
            durable_json(out/'preflight_complete.json', summary)
    return result

if __name__=='__main__': raise SystemExit(main())
