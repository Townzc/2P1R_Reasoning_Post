from pathlib import Path
import datetime, hashlib, json, math, shutil, zipfile

ROOT = Path('.local/p012_20261111'); PUBLIC = Path('reports/p012_20261111')
OUT = PUBLIC / 'results_aftere9f0ebdd_v1'
read = lambda p: json.loads(Path(p).read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
bytes_sha = lambda data: hashlib.sha256(data).hexdigest()
names = ['a6_3_tinker_lora_4b_math_e4_s17_v1', 'a6_3_tinker_lora_4b_math_e8_s17_v1']
for key in ['4b', '9b', '9b_base']:
    for ep in ['baseline4'] + ([] if key == '9b_base' else ['baseline0']) + ([] if key == '4b' else ['holdout8']) + ['nll']:
        names.append(f'tinker_lora_qwen3_5_{key}_gsm8k_pre_{ep}_v1')
assert len(names) == 12
assert all((PUBLIC / name / 'RESULTS.json').exists() for name in names), 'Wait for E8 and all NLL publications'
assert not OUT.exists(); OUT.mkdir(); (OUT / 'inputs').mkdir()


def bind_input(spec):
    source = Path(spec['path'])
    assert sha(source) == spec['sha256']
    if str(source).startswith('reports/'):
        return dict(spec)
    target = OUT / 'inputs' / (spec['sha256'][:16] + '_' + source.name)
    if not target.exists():
        shutil.copyfile(source, target)
    assert sha(target) == spec['sha256']
    return {'path': str(target), 'sha256': sha(target)}


endpoints = []; total_raw = 0; total_nll = 0; table = []; nll_table = []
for name in names:
    folder = PUBLIC / name
    result = read(folder / 'RESULTS.json')
    entry = {'name': name, 'model': result['model'], 'result': {'path': str(folder / 'RESULTS.json'), 'sha256': sha(folder / 'RESULTS.json')},
             'archive': {'path': str(folder / 'evidence.zip'), 'sha256': sha(folder / 'evidence.zip')}, 'independent_audit': 'pending'}
    with zipfile.ZipFile(folder / 'evidence.zip') as archive:
        assert archive.testzip() is None
        if 'nll' in result:
            request = json.loads(archive.read('REQUEST.json'))
            records_bytes = archive.read('NLL_RECORDS.json'); records = json.loads(records_bytes)
            assert len(records) == 1000 and len({x['parent_id'] for x in records}) == 500
            summary = result['nll']
            targets = sum(x['target_tokens'] for x in records)
            chars = sum(x['solution_chars'] for x in records)
            nll = sum(x['nll_sum'] for x in records)
            assert targets == summary['target_tokens'] and chars == summary['solution_chars']
            assert math.isclose(nll / targets, summary['mean_per_token_nll'], abs_tol=1e-12)
            assert math.isclose(nll / chars, summary['nll_per_char'], abs_tol=1e-12)
            assert request['model'] == result['model']
            entry.update(kind='NLL', rows=1000, parents=500, input=bind_input(request['dataset']),
                request_sha256=bytes_sha(archive.read('REQUEST.json')), records_sha256=bytes_sha(records_bytes),
                nll_per_token=summary['mean_per_token_nll'], nll_per_char=summary['nll_per_char'])
            total_nll += 1000
            nll_table.append(f'| {result["model"]} | {summary["mean_per_token_nll"]:.6f} | {summary["nll_per_char"]:.6f} |')
        else:
            raw_name = next(x for x in archive.namelist() if x.endswith('/generation/raw.jsonl'))
            labels_name = next(x for x in archive.namelist() if x.endswith('/labels.jsonl'))
            request_name = raw_name.split('/generation/')[0] + '/REQUEST.json'
            request = json.loads(archive.read(request_name))
            raw_bytes = archive.read(raw_name); label_bytes = archive.read(labels_name)
            assert bytes_sha(raw_bytes) == result['raw_sha256']
            assert bytes_sha(label_bytes) == result['labels_sha256']
            raw = [json.loads(x) for x in raw_bytes.splitlines()]
            labels = [json.loads(x) for x in label_bytes.splitlines()]
            assert len(raw) == len(labels)
            raw_keys = {(x['id'], x['draw']) for x in raw}
            assert len(raw_keys) == len(raw) and raw_keys == {(x['id'], x['draw']) for x in labels}
            inp = bind_input(request['evaluation'])
            inputs = [json.loads(x) for x in Path(inp['path']).open()]
            assert {x['id'] for x in raw} == {x['id'] for x in inputs}
            assert len(raw) == len(inputs) * request['n']
            term = result.get('MATH5000', result.get('termination'))
            correct = sum(x['correct'] for x in labels)
            assert correct == term['correct'] and math.isclose(correct / len(labels), term['accuracy'])
            assert request['model'] == result['model']
            entry.update(kind='generation', task=request['evaluation']['task'], raw_rows=len(raw), input=inp,
                request_sha256=bytes_sha(archive.read(request_name)), raw_member=raw_name, labels_member=labels_name,
                raw_sha256=result['raw_sha256'], labels_sha256=result['labels_sha256'], correct=correct,
                accuracy=term['accuracy'], termination=term)
            if 'training/REQUEST.json' in archive.namelist():
                tr = json.loads(archive.read('training/REQUEST.json'))
                losses = [json.loads(x) for x in archive.read('training/train_loss.jsonl').splitlines()]
                assert tr['model'] == result['model'] and tr['seed'] == result['seed'] and tr['cell'] == result['cell']
                assert len(losses) == result['dose']['expected_updates'] == tr['dose']['expected_updates']
                assert [x['step'] for x in losses] == list(range(1, len(losses) + 1))
                entry['training_binding'] = {'run_id': tr['run_id'], 'cell': tr['cell'], 'seed': tr['seed'],
                    'updates': len(losses), 'request_sha256': bytes_sha(archive.read('training/REQUEST.json')),
                    'dataset': bind_input(tr['dataset']), 'train_loss_sha256': bytes_sha(archive.read('training/train_loss.jsonl'))}
            if request['n'] == 8:
                grouped = {}
                for row in labels:grouped.setdefault(row['id'], []).append(row['correct'])
                passed = sum(any(x) for x in grouped.values()) / len(grouped)
                assert math.isclose(passed, result['pass_metrics']['pass_at_8'])
                entry['pass_at_8'] = passed
            total_raw += len(raw)
            short_name = name.replace('tinker_lora_qwen3_5_', '').replace('_gsm8k_pre_', ' / GSM ').replace('a6_3_tinker_lora_', '').replace('_math_', ' / MATH ').replace('_s17_v1', '').replace('_v1', '')
            metric = f'{100 * term["accuracy"]:.2f}%'
            if request['n'] == 8:metric += f' / pass@8 {100 * entry["pass_at_8"]:.2f}%'
            table.append(f'| {short_name} | {correct}/{len(raw)} | {metric} | {100 * term["length_cap_rate"]:.2f}% | {term["loop_count"]} | {term["normally_terminated_correct"]}/{term["normally_terminated_count"]} |')
    endpoints.append(entry)

manifest = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'endpoints': endpoints,
    'endpoint_count': len(endpoints), 'scored_generation_endpoints': 9, 'scored_raw_outputs': total_raw,
    'NLL_endpoints': 3, 'NLL_solution_records': total_nll,
    'held_unscored_endpoint': {'path': str(PUBLIC / 'tinker_gsm_4b_diversity_hold_v1/HOLD.json'), 'sha256': sha(PUBLIC / 'tinker_gsm_4b_diversity_hold_v1/HOLD.json')},
    'accepted_prior_audit_excluded': 'e9f0ebdd167aa012f1d2fe9e308002949e3ee48a',
    'scientific_runner_sha256': sha('experiments/p012/tinker_lora.py'), 'scorer_sha256': sha('experiments/p012/scoring.py'),
    'bootstrap_core_sha256': sha('analysis/p012_registered.py')}
assert total_raw == 24595 and total_nll == 3000
(OUT / 'ENDPOINTS.json').write_text(json.dumps(manifest, indent=2) + '\n')
(OUT / 'CHECKS.json').write_text(json.dumps({'archive_integrity': 'passed', 'all_raw_label_hashes_and_pairings': 'passed',
    'all_exact_input_ids_and_output_counts': 'passed', 'training_model_cell_seed_dose_and_dataset_bindings': 'passed',
    'reported_correct_counts_from_existing_labels': 'passed', 'NLL_aggregation_from_all_records': 'passed',
    'new_model_calls_for_verification': 0, 'new_scores_or_bootstraps_for_verification': 0}, indent=2) + '\n')
for name in ['PAID_STORAGE_VERIFIED.json', 'L64_BUDGET_GATE.json']:
    if (PUBLIC / 'review_2edeee51' / name).exists():shutil.copyfile(PUBLIC / 'review_2edeee51' / name, OUT / name)
(OUT / 'README.md').write_text('# E8 恢复结果与新增 GSM8K 测量：下一轮独立审查\n\n'
    '本包包含 12 个新端点：E4/E8 两个 MATH 端点、GSM8K 五个 greedy 基线、两个 pass@8 和三个 NLL。共 24,595 条已评分输出、3,000 条教师解 NLL 记录。另附 4B GSM8K pass@8 的 4,000 条未评分输出及多样性门槛记录。全部是 Tinker / LoRA；不并入 H0–H3。e9f0ebdd 及更早已通过的端点不重复审查。\n\n'
    '| 端点 | 正确数/输出数 | 准确率或采样指标 | 截断率 | 循环数 | 正常终止正确数/分母 |\n|---|---:|---:|---:|---:|---:|\n' + '\n'.join(table) + '\n\n'
    '| NLL 模型 | 每 token | 每字符 |\n|---|---:|---:|\n' + '\n'.join(nll_table) + '\n\n'
    '## 请复核\n\n'
    '1. 按 P012 §12 对新生成端点独立评分；ENDPOINTS.json 绑定全部原始输出、标签、请求、输入、训练模型/格/种子/步数和哈希。NLL 请核对 1,000 条解答/500 题及两个归一化指标。CHECKS.json 是本地一致性检查，独立审查仍待本轮完成。\n'
    '2. 按 2edeee51 核对 E8 的恢复回执：原状态 046b588f、导出后采样权重 0a26c1d5、远端模型/rank/目标层一致，评测使用新采样路径，恢复新增 0 步。E8 经一次训练重试及一次仅导出恢复；原失败证据保持不变，训练 token 只记一次。完整回执位于 ../review_2edeee51/export_receipt/，原失败包位于 ../e8_storage_export_recovery_v1/。\n'
    '3. 请决定 4B GSM8K pass@8 的处置：4,000 个独立种子已核验，但仅 343/500 题有至少 7 条不同输出（68.6%，门槛80%）。原始证据位于 ../tinker_gsm_4b_diversity_hold_v1/。该端点尚未评分、没有重跑；请核对是否为可接受的自然重复，或指定下一步诊断。训练独立继续，依据 a56115d6 §3。\n\n'
    '存储控制台原先仍为 Free；按负责人既有授权切换并保存 Paid 后，API 费率为0.1。新建客户端被402拒绝的三个 NLL 尝试均为零 token，完整证据在 ../review_2edeee51/nll_zero_token_failures.zip；之后各执行一次基础设施重试。全部检查点保留，USD30存储预留计入原T340和合计485。原定27个GSM训练格由已发布的有限队列继续，配方和评分代码均未改变。\n')
print(json.dumps({'path': str(OUT), 'endpoints': len(endpoints), 'scored_outputs': total_raw, 'NLL_records': total_nll}))
