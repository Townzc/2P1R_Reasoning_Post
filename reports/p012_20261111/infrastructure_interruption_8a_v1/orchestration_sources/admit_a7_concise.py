"""Admit fixed A7 concise arms; no model or scoring changes."""
import copy
import datetime
import json
import subprocess
from a7_ops import *

DATA = PUBLIC / 'a7_1_concise_data_v1'
REPORT_COMMIT = '465bf2c13bc979ca9fbda5e3922e806574e3104f'


def names_for(seed):
    assert seed in (17, 29)
    models = ['9b', '4b', '9b_base'] if seed == 17 else ['9b', '4b']
    return [f'a7_1_tinker_lora_{m}_math_concise_s{seed}_20261113_v1' for m in models]


def prepare(seed):
    sent = read(META / 'CONCISE_REPORT_SENT.json')
    report = read(DATA / 'DATA_REPORT.json')
    assert sent['authority_commit'] == report['authority_commit'] == AUTHORITY
    assert sent['report_commit'] == REPORT_COMMIT
    assert sent['data_report_sha256'] == sha(DATA / 'DATA_REPORT.json')
    assert (DATA / 'DATA_REPORT.json').read_bytes() == subprocess.check_output(
        ['git', 'show', REPORT_COMMIT + ':' + str(DATA / 'DATA_REPORT.json')])
    assert all(d['fallback_rows'] <= 26 for d in report['datasets'])
    out = []
    for name in names_for(seed):
        d = ROOT / 'a7_runs_v1' / name
        p = DATA / 'prepared_requests' / (name + '.json')
        assert (d / 'request_prepared.json').read_bytes() == p.read_bytes()
        assert p.read_bytes() == subprocess.check_output(['git', 'show', REPORT_COMMIT + ':' + str(p)])
        assert not (d / 'request.json').exists(), 'Already admitted: ' + name
        assert not (d / 'run.log').exists() and not (d / 'result').exists()
        r = copy.deepcopy(read(p))
        assert r['authority_commit'] == r['prediction_commit'] == AUTHORITY
        assert r['seed'] == seed and r['mode'] == 'train' and r['A7_arm'] == 'concise'
        assert r['dose']['parents'] == r['dose']['distinct_rows'] == 512
        assert r['dose']['epochs'] == 2 and r['dose']['expected_updates'] == 128
        assert r['dose']['effective_batch'] == 8 and r['rank'] == 32
        assert r['dataset']['sha256'] == sha(r['dataset']['path'])
        assert r['dataset']['sha256'] in sent['concise_sha256'].values()
        assert r['source_sha256'] == sha('experiments/p012/tinker_lora.py')
        assert r['cpu_counts']['cpu_row_checks_sha256'] == sha(DATA / 'CPU_ROW_CHECKS.jsonl')
        assert all(sha(Path(r['asset']['path']) / f['path']) == f['sha256'] for f in r['asset']['files'])
        r['pretraining_data_report'] = dict(sent)
        r['prepared_request_sha256'] = sha(p)
        if seed == 29:
            for prior in names_for(17):
                result = PUBLIC / prior.replace('_20261113', '') / 'RESULTS.json'
                assert result.exists(), 'Seed17 batch must finish first'
            ev = ROOT / 'a7_runs_v1' / name.replace('_s29_', '_s17_greedy_')
            assert read(ev / 'result/COMPLETE.json')['success']
            er = read(ev / 'request.json')
            assert er['model'] == r['model'] and er['prediction_commit'] == AUTHORITY
            usage = read(ev / 'result/USAGE.json')
            r['forecast']['original_prepared_forecast'] = copy.deepcopy(r['forecast'])
            r['forecast']['reserved_greedy_usd'] = usage['upper_token_cost_usd'] * 1.5
            r['forecast']['sampling_reference'] = str(ev / 'result/USAGE.json')
            r['forecast']['sampling_reference_sha256'] = sha(ev / 'result/USAGE.json')
            r['forecast']['sampling_rule'] = 'Completed same-concise seed17 full5000 token cost x1.5'
            r['forecast']['forecast_usd'] = r['forecast']['training_buffered_usd'] + r['forecast']['reserved_greedy_usd']
        out.append(r)
    return out


def admit(seed):
    requests = prepare(seed)
    amount = sum(r['forecast']['forecast_usd'] for r in requests)
    pub = PUBLIC / f'a7_1_concise_seed{seed}_admission_v1'
    assert not pub.exists()
    with lock('BUDGET_ADMISSION.lock'):
        snap = accounting()
        ensure_budget(snap, amount)
        pub.mkdir()
        (pub / 'requests').mkdir()
        record = dict(snap, utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            authority_commit=AUTHORITY, new_runs=[r['run_id'] for r in requests],
            batch_buffered_usd=amount, A7_next_usd=snap['A7_accounted_and_reserved_usd']+amount,
            combined_next_usd=snap['combined_reserved_usd']+amount, admitted=True,
            data_report_commit=REPORT_COMMIT, report_delivery=read(META / 'CONCISE_REPORT_SENT.json'))
        (pub / 'ADMISSION.json').write_text(json.dumps(record, indent=2) + '\n')
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        for r in requests:
            r['code_commit'] = head
            r['forecast'].update(admitted=True, admission_file=str(pub/'ADMISSION.json'), admission_sha256=sha(pub/'ADMISSION.json'))
            text = json.dumps(r, indent=2) + '\n'
            assert '/Users/' not in text
            with (ROOT/'a7_runs_v1'/r['run_id']/'request.json').open('x') as f:
                f.write(text)
            (pub/'requests'/(r['run_id']+'.json')).write_text(text)
        (pub/'README.md').write_text(
            '# A7-1 concise training admission\n\n'
            f'Seed {seed}; fixed512 rows,2 epochs,128 updates,batch8,rank32. '
            'The data report was delivered before admission; full frozen data and token counts are at465bf2c1. '
            'All model, rendering, training, generation and scoring implementations remain unchanged. '
            'Each new endpoint records UTC and amendment22890560 before scoring. '
            'These arms are exploratory and excluded from H0-H3.\n')
        commit = publish([pub], f'P012: admit A7 concise seed{seed} after pretraining data report')
        return {'commit': commit, 'batch_usd': amount, 'A7_next_usd': record['A7_next_usd'],
                'combined_next_usd': record['combined_next_usd'], 'runs': record['new_runs']}


if __name__ == '__main__':
    import sys
    print(json.dumps(admit(int(sys.argv[1]))), flush=True)
