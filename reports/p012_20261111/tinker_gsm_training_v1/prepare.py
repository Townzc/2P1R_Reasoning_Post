"""Admit the original 27 GSM cells using frozen inputs and measured pretraining tokens."""
from pathlib import Path
import copy, datetime, json, subprocess, sys

sys.path.insert(0, '.local/p012_20261111/amendment7_v1')
from a7_ops import ROOT, PUBLIC, lock, read, sha, accounting
from experiments.p012.tinker_lora import load_renderer, generation_messages

OUT = PUBLIC / 'tinker_gsm_training_v1'
assert not (OUT / 'ADMISSION.json').exists()
source = sha('experiments/p012/tinker_lora.py')
assert source == '050a9f43d81c7a610dfc9ca30c901103e145fff28384d2efd1f13247fc60f5ee'
counts = read(PUBLIC / 'tinker_gsm_preparation_v1/TRAINING_COUNTS.json')
eval_path = PUBLIC / 'tinker_gsm_preparation_v1/inputs/gsm8k1319.jsonl'
rows = [json.loads(x) for x in eval_path.open()]
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
requests = []
forecasts = []
for key in ['4b', '9b', '9b_base']:
    old = ROOT / 'tinker_formal_v1' / f'tinker_lora_qwen3_5_{key}_math_l_s17_20261113_v1'
    template = read(old / 'request.json')
    tokenizer, renderer = load_renderer(template)
    lengths = []
    for row in rows:
        messages = generation_messages(row)
        ids = renderer.build_generation_prompt(messages).to_ints()
        assert ids == tokenizer.apply_chat_template(messages, add_generation_prompt=True,
                                                    enable_thinking=False, return_dict=False)
        assert len(ids) + 4096 <= 8192
        lengths.append(len(ids))
    ref_name = f'tinker_lora_qwen3_5_{key}_gsm8k_pre_' + ('baseline4' if key == '9b_base' else 'baseline0') + '_20261114_v1'
    ref = ROOT / 'tinker_formal_v1' / ref_name
    assert read(ref / 'result/COMPLETE.json')['success']
    usage = read(ref / 'result/USAGE.json')['sampling']
    prices = template['prices_per_million']
    estimate = (sum(lengths) * prices['prefill'] + usage['completion_tokens'] * prices['sample']) / 1e6
    forecast = {'key': key, 'reference_run': ref_name,
        'reference_usage_sha256': sha(ref / 'result/USAGE.json'), 'measured_completion_tokens': usage['completion_tokens'],
        'exact_posttraining_prefill_tokens': sum(lengths), 'question_count': 1319,
        'buffered_greedy_usd': estimate * 1.5,
        'basis': 'Same-model measured GSM completion tokens plus exact posttraining prompts; entire token cost times 1.5.',
        'base_reference_format_note': 'Base uses its authorized 4-shot pretraining completion lengths; posttraining prompt is the fixed OMI-2 prompt.' if key == '9b_base' else None}
    forecasts.append(forecast)
    for seed in [17, 29]:
        for cell in (['L', 'P', 'R', 'K8', 'K4'] if seed == 17 else ['L', 'P', 'R', 'K8']):
            row = next(x for x in counts if x['key'] == key and x['cell'] == cell)
            assert sha(row['dataset']['path']) == row['dataset']['sha256']
            r = copy.deepcopy(template)
            r.update(run_id=f'tinker_lora_qwen3_5_{key}_gsm8k_{cell.lower()}_s{seed}_20261114_v1',
                seed=seed, cell=cell, dataset=row['dataset'], dose=row['dose'], source_sha256=source,
                code_commit=head, accepted_review_commit='a56115d6ceee49d0bb5495f9be3579e0cace8daa',
                original_track_review_commit='8bbf06a7ef19f56ace1b23dde4607b02bc10b389',
                authority='Original owner-approved A4 T-GSM; unchanged training/evaluation paths after A7.',
                track='tinker_lora', task='gsm8k', exploratory=True, excluded_from_H0_H3=True,
                cpu_counts={k: row[k] for k in ['full_training_input_tokens', 'maximum_sequence_tokens', 'all_rows_renderer_and_mask_verified']})
            r['forecast'] = {'admitted': True, 'training_buffered_usd': row['buffered_training_and_storage_usd'],
                'reserved_greedy_usd': forecast['buffered_greedy_usd'], 'sampling_reference': forecast,
                'T_GSM_cap_usd': 105, 'original_T_cap_usd': 340, 'combined_cap_usd': 485}
            requests.append(r)
assert len(requests) == 27
pre = []
for row in read(PUBLIC / 'tinker_gsm_pre_admission_v1/ADMISSION.json')['endpoints']:
    d = ROOT / 'tinker_formal_v1' / row['run_id']
    complete = (d / 'result/COMPLETE.json').exists()
    value = read(d / 'result/USAGE.json')['upper_token_cost_usd'] if complete else row['forecast_usd']
    pre.append({'run_id': row['run_id'], 'complete': complete, 'usd': value,
                'usage_sha256': sha(d / 'result/USAGE.json') if complete else None})
amount = sum(r['forecast']['training_buffered_usd'] + r['forecast']['reserved_greedy_usd'] for r in requests)
pre_total = sum(x['usd'] for x in pre)
storage_ledger = read(PUBLIC / 'review_2edeee51/paid_storage_ledger.json')
original_math = read(PUBLIC / 'tinker_gsm_pre_admission_v1/ADMISSION.json')['combined_reserved_usd'] - sum(
    x['forecast_usd'] for x in read(PUBLIC / 'tinker_gsm_pre_admission_v1/ADMISSION.json')['endpoints'])
base = original_math + storage_ledger['paid_storage_reserved_usd']
with lock('BUDGET_ADMISSION.lock'):
    snapshot = accounting()
    all_after = snapshot['combined_reserved_usd'] - snapshot['original_T_accounted_and_reserved_usd'] + base + pre_total + amount
    assert pre_total + amount <= 105
    assert base + pre_total + amount <= 340 and all_after <= 485
    record = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'admitted': True,
        'original_math_accounted_and_reserved_usd': original_math, 'paid_storage_reserve_usd': 30,
        'original_T_excluding_GSM_usd': base, 'GSM_pre_endpoints': pre,
        'GSM_pre_accounted_and_reserved_usd': pre_total, 'new_training_and_greedy_reserved_usd': amount,
        'GSM_total_accounted_and_reserved_usd': pre_total + amount,
        'combined_reserved_usd': base + pre_total + amount, 'value_field_scope': 'original T only',
        'combined_all_tracks_after_usd': all_after, 'snapshot_before': snapshot,
        'greedy_forecasts': forecasts, 'runs': [r['run_id'] for r in requests],
        'caps_usd': {'GSM': 105, 'original_T': 340, 'combined': 485},
        'failed_NLL_zero_token_cost_usd': 0,
        'sampling_hold': '4B GSM pass@8 remains unscored after diversity guard. T4 review section3 explicitly allows training independently.'}
    (OUT / 'ADMISSION.json').write_text(json.dumps(record, indent=2) + '\n')
    (OUT / 'requests').mkdir()
    for r in requests:
        r['forecast'].update(admission_file=str(OUT / 'ADMISSION.json'), admission_sha256=sha(OUT / 'ADMISSION.json'))
        d = ROOT / 'tinker_gsm_runs_v1' / r['run_id']; d.mkdir(parents=True, exist_ok=False)
        text = json.dumps(r, indent=2) + '\n'; assert '/Users/' not in text
        (d / 'request.json').write_text(text)
        (OUT / 'requests' / (r['run_id'] + '.json')).write_text(text)
    pointer = {'path': str(OUT / 'ADMISSION.json'), 'sha256': sha(OUT / 'ADMISSION.json'), 'value_field': 'combined_reserved_usd'}
    (ROOT / 'amendment6_v1/ORIGINAL_T_LEDGER_CURRENT.json').write_text(json.dumps(pointer, indent=2) + '\n')
print(json.dumps({k: record[k] for k in ['GSM_total_accounted_and_reserved_usd', 'combined_reserved_usd', 'combined_all_tracks_after_usd']}))
