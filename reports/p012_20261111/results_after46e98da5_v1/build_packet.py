"""Freeze only new completed outputs after the accepted46e98da5 batch."""
from pathlib import Path
import datetime, hashlib, json, math, shutil, sys, zipfile
sys.path.insert(0, 'reports/p012_20261111/review_46e98da5')
from current_budget import accounting
from a7_ops import lock

PUBLIC = Path('reports/p012_20261111'); ROOT = Path('.local/p012_20261111')
OUT = PUBLIC / 'results_after46e98da5_v1'
read = lambda p: json.loads(Path(p).read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
bh = lambda b: hashlib.sha256(b).hexdigest()
l64 = PUBLIC / 'a6_3_tinker_lora_4b_math_l64_s17_v1'
assert (l64 / 'RESULTS.json').exists(), 'Wait for L64 publication'
assert read(ROOT / 'l64_after46e98da5_v1/QUEUE.json')['status'] == 'complete'
targets = [l64, PUBLIC / 'tinker_lora_qwen3_5_4b_gsm8k_pre_holdout8_v1']
published = {e['run_id'] for e in read(ROOT / 't_gsm_v1/TRAINING_QUEUE.json')['events'] if e['stage'] == 'published'}
for name in read(PUBLIC / 'tinker_gsm_training_v1/ADMISSION.json')['runs']:
    d = PUBLIC / name.replace('_20261114', '')
    if name in published:
        assert (d / 'RESULTS.json').exists()
        assert not (d / 'AUDIT_STATUS.json').exists(), 'Accepted endpoint must not be re-reviewed'
        targets.append(d)
assert len(targets) >= 7
assert not OUT.exists(); OUT.mkdir(); (OUT / 'inputs').mkdir()


def bind_input(spec):
    source = Path(spec['path']); assert sha(source) == spec['sha256']
    if str(source).startswith('reports/'):
        return dict(spec)
    prior = PUBLIC / 'results_aftere9f0ebdd_v1/inputs' / (spec['sha256'][:16] + '_' + source.name)
    if prior.exists():
        assert sha(prior) == spec['sha256']
        return {'path': str(prior), 'sha256': sha(prior)}
    target = OUT / 'inputs' / (spec['sha256'][:16] + '_' + source.name)
    if not target.exists():shutil.copyfile(source, target)
    assert sha(target) == spec['sha256']
    return {'path': str(target), 'sha256': sha(target)}


entries = []; table = []; outputs = 0
policy = PUBLIC / 'review_46e98da5/T_GSM_INTERPRETATION.json'
for folder in targets:
    result = read(folder / 'RESULTS.json')
    term = result.get('MATH5000', result.get('GSM8K', result.get('termination')))
    entry = {'name': folder.name, 'model': result['model'], 'seed': result['seed'],
        'result': {'path': str(folder / 'RESULTS.json'), 'sha256': sha(folder / 'RESULTS.json')},
        'archive': {'path': str(folder / 'evidence.zip'), 'sha256': sha(folder / 'evidence.zip')},
        'independent_result_audit': 'pending', 'exploratory': True, 'excluded_from_H0_H3': True}
    with zipfile.ZipFile(folder / 'evidence.zip') as archive:
        assert archive.testzip() is None
        raw_name = next(n for n in archive.namelist() if n.endswith('/generation/raw.jsonl'))
        label_name = next(n for n in archive.namelist() if n.endswith('/labels.jsonl'))
        request_name = raw_name.split('/generation/')[0] + '/REQUEST.json'
        request = json.loads(archive.read(request_name))
        assert request['source_sha256'] == sha('experiments/p012/tinker_lora.py')
        raw_bytes = archive.read(raw_name); label_bytes = archive.read(label_name)
        assert bh(raw_bytes) == result['raw_sha256'] and bh(label_bytes) == result['labels_sha256']
        raw = [json.loads(x) for x in raw_bytes.splitlines()]
        labels = [json.loads(x) for x in label_bytes.splitlines()]
        assert len(raw) == len(labels)
        pairs = {(x['id'], x['draw']) for x in raw}
        assert len(pairs) == len(raw) and pairs == {(x['id'], x['draw']) for x in labels}
        inp = bind_input(request['evaluation'])
        inputs = [json.loads(x) for x in Path(inp['path']).open()]
        assert len(raw) == len(inputs) * request['n']
        assert {x['id'] for x in raw} == {x['id'] for x in inputs}
        correct = sum(x['correct'] for x in labels)
        assert correct == term['correct'] and math.isclose(correct / len(raw), term['accuracy'])
        assert request['model'] == result['model'] and request['seed'] == result['seed']
        pred = json.loads(archive.read('PREDICTION_BEFORE_SCORE.json'))
        assert pred['utc'] and pred['raw_sha256'] == result['raw_sha256']
        entry.update(task=request['evaluation']['task'], raw_rows=len(raw), input=inp,
            request_sha256=bh(archive.read(request_name)), raw_member=raw_name, labels_member=label_name,
            raw_sha256=result['raw_sha256'], labels_sha256=result['labels_sha256'],
            accuracy=term['accuracy'], correct=correct, termination=term, prediction_before_score=pred)
        if 'training/REQUEST.json' in archive.namelist():
            training = json.loads(archive.read('training/REQUEST.json'))
            losses = [json.loads(x) for x in archive.read('training/train_loss.jsonl').splitlines()]
            order = json.loads(archive.read('training/ROW_ORDER.json'))
            assert training['model'] == result['model'] and training['seed'] == result['seed']
            assert training['cell'] == result['cell']
            assert training['source_sha256'] == request['source_sha256']
            assert training['dataset']['sha256'] == result['dataset_sha256']
            assert [x['step'] for x in losses] == list(range(1, training['dose']['expected_updates'] + 1))
            assert [i for row in losses for i in row['row_indices']] == order
            assert json.loads(archive.read('training/USAGE.json'))['training_input_tokens'] == training['cpu_counts']['full_training_input_tokens']
            if 'full_supervised_target_tokens' in training['cpu_counts']:
                assert sum(x['target_tokens'] for x in losses) == training['cpu_counts']['full_supervised_target_tokens']
            entry['training_binding'] = {'run_id': training['run_id'], 'cell': training['cell'],
                'seed': training['seed'], 'model': training['model'], 'updates': len(losses),
                'dataset': bind_input(training['dataset']), 'request_sha256': bh(archive.read('training/REQUEST.json')),
                'train_loss_sha256': bh(archive.read('training/train_loss.jsonl')),
                'row_order_sha256': bh(archive.read('training/ROW_ORDER.json')),
                'state_manifest_sha256': bh(archive.read('training/STATE.json')),
                'sampler_manifest_sha256': bh(archive.read('training/SAMPLER.json')),
                'server_model_info_sha256': bh(archive.read('training/SERVER_MODEL_INFO.json'))}
            assert request['sampler_path'] == json.loads(archive.read('training/SAMPLER.json'))['path']
            assert pred['prediction_commit'] == training['prediction_commit']
        else:
            assert request['n'] == 8 and len(raw) == 4000
            assert len({x['sampling_seed'] for x in raw}) == len({x['sequence_id'] for x in raw}) == 4000
            groups = {}
            for row in labels:groups.setdefault(row['id'], []).append(row['correct'])
            pass8 = sum(any(v) for v in groups.values()) / len(groups)
            assert math.isclose(result['pass_metrics']['pass_at_1'], correct / len(raw))
            assert math.isclose(result['pass_metrics']['pass_at_8'], pass8)
            assert result['eligible_for_pretraining_capability'] is False
            entry.update(pass_at_1=correct / len(raw), pass_at_8=pass8,
                eligible_for_pretraining_capability=False, answer_only_output_fraction_audited=.405,
                sampling_disposition_review_commit='46e98da59753315694ebc4a0699f0b7c6c37a9c5')
            entry['independent_sampling_check'] = result['independent_sampling_check']
            assert result['raw_sha256'] == read(PUBLIC / 'tinker_gsm_4b_diversity_hold_v1/HOLD.json')['first_run_check']['raw_sha256']
        if entry['task'] == 'gsm8k' and result['model'] == 'Qwen/Qwen3.5-4B':
            entry['interpretation_policy'] = {'path': str(policy), 'sha256': sha(policy)}
            entry['primary_pretraining_reference'] = '4-shot1216/1319=92.19%'
            entry['baseline0_answer_only_count'] = 543
        outputs += len(raw)
        label = folder.name.replace('tinker_lora_qwen3_5_', '').replace('a6_3_tinker_lora_', '').replace('_s17_v1', '').replace('_v1', '')
        metric = f'{100 * term["accuracy"]:.3f}%'
        if 'pass_at_8' in entry:metric += f' / pass@8 {100 * entry["pass_at_8"]:.2f}%（不作能力指标）'
        table.append(f'| {label} | {correct}/{len(raw)} | {metric} | {100 * term["length_cap_rate"]:.2f}% | {term["loop_count"]} | {term["normally_terminated_correct"]}/{term["normally_terminated_count"]} |')
    entries.append(entry)

manifest = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'endpoint_count': len(entries),
    'raw_outputs': outputs, 'endpoints': entries, 'previous_accepted_review_excluded': '46e98da59753315694ebc4a0699f0b7c6c37a9c5',
    'scientific_runner_sha256': sha('experiments/p012/tinker_lora.py'), 'scorer_sha256': sha('experiments/p012/scoring.py'),
    'bootstrap_core_sha256': sha('analysis/p012_registered.py'), 'new_bootstrap_runs': 0}
(OUT / 'ENDPOINTS.json').write_text(json.dumps(manifest, indent=2) + '\n')
(OUT / 'CHECKS.json').write_text(json.dumps({'archive_integrity': 'passed', 'raw_label_hashes_and_pairings': 'passed',
    'frozen_input_identity_and_counts': 'passed', 'training_model_cell_seed_dose_data_and_sampler_bindings': 'passed',
    'reported_correct_counts_from_existing_labels': 'passed', 'timestamped_prescore_prediction_bindings': 'passed',
    'released_sampling_raw_identity': 'passed', 'new_model_calls_or_rescoring_during_verification': 0}, indent=2) + '\n')
with lock('BUDGET_ADMISSION.lock'):
    (OUT / 'BUDGET_SNAPSHOT.json').write_text(json.dumps(accounting(), indent=2) + '\n')
(OUT / 'README.md').write_text('# 46e98da5 之后的新结果：下一轮独立审查\n\n'
    f'本包冻结 {len(entries)} 个新端点、{outputs:,} 条输出，包括原定4B L64、已解除暂停的4B GSM8K pass@8评分，以及新完成的GSM8K训练格。全部为Tinker/LoRA，探索性，不并入H0–H3。46e98da5接受的12个端点及更早已通过结果不重复审查。\n\n'
    '| 端点 | 正确数/输出数 | 准确率或采样指标 | 截断率 | 循环数 | 正常终止正确数/分母 |\n|---|---:|---:|---:|---:|---:|\n' + '\n'.join(table) + '\n\n'
    '**4B GSM8K参照：** 使用4-shot1216/1319=92.19%。0-shot有543/1319题只答不写；此次holdout输出40.5%只答不写，pass@1和pass@8只作描述记录，不作为训练前能力。ENDPOINTS.json逐项绑定这些用途限制。\n\n'
    '## 请复核\n\n'
    '1. 按P012§12独立评分新端点，核对正确数、截断、循环与正常终止分母；ENDPOINTS.json提供完整原始输出/标签/输入/训练/采样权重及预测绑定。CHECKS.json为本地一致性检查，独立审查待本轮完成。\n'
    '2. 4B GSM8K pass@8按46e98da5直接评分原有4000输出，raw哈希与暂停包完全一致，没有重新采样。种子与序列号各4000个不同；多数题八条全同的停止条件未触发。请核对新标签和pass指标，并保留不作能力指标的说明。\n'
    '3. L64是修订6的既定格：64题×2轮、16步、seed17、完整MATH5000。数据/配方/评分未改；负责人最新批准A6-3上限38，见l64_after46e98da5_admission_v1。训练前后token与预算只计一次。\n\n'
    '原27个GSM训练格继续。当前预算使用review_46e98da5/current_budget.py的最新上限：A6-2为48、A6-3为38、原T340、合计485、存储预留30。存储以API费率和用量为准；账户和计费设置只由负责人修改。没有新增统计分析或bootstrap。\n')
shutil.copyfile(__file__, OUT / 'build_packet.py')
print(json.dumps({'directory': str(OUT), 'endpoints': len(entries), 'outputs': outputs}))
