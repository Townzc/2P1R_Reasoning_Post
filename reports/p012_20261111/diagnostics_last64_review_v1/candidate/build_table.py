"""Mechanical diagnostics from existing public evidence; no model or scorer calls.

All accuracies use frozen labels. No bootstrap, hypothesis test, or label change.
Final loss means the loss logged at the last optimizer update, not train_loss.
"""
from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path
import statistics
import zipfile

ROOT = Path('reports/p012_20261111')
HERE = Path(__file__).resolve().parent.relative_to(Path.cwd())
read = lambda p: json.loads(Path(p).read_text())
digest = lambda b: hashlib.sha256(b).hexdigest()
HASHES = {}


def file_hash(p):
    p = str(p)
    if p not in HASHES:
        with open(p, 'rb') as f:
            HASHES[p] = hashlib.file_digest(f, 'sha256').hexdigest()
    return HASHES[p]


def member_ref(archive, member, expected=None):
    with zipfile.ZipFile(archive) as z:
        with z.open(member) as f:
            h = hashlib.file_digest(f, 'sha256').hexdigest()
    if expected is not None:
        assert h == expected, (archive, member, 'changed evidence')
    return {'archive':str(archive), 'archive_sha256':file_hash(archive),
            'member':member, 'sha256':h}


def file_ref(path, expected=None):
    h = file_hash(path)
    assert expected is None or h == expected
    return {'path':str(path), 'sha256':h}


def content(ref):
    if 'archive' in ref:
        assert file_hash(ref['archive']) == ref['archive_sha256']
        with zipfile.ZipFile(ref['archive']) as z:
            b = z.read(ref['member'])
    else:
        b = Path(ref['path']).read_bytes()
    assert digest(b) == ref['sha256'], 'Changed bound evidence'
    return b


def catalogue():
    main_dir = ROOT/'registered_analysis_169754c4_v1'
    main = read(main_dir/'INPUT_MANIFEST.json')
    locations = {x['restore_path']:x for x in read(main_dir/'SOURCE_LOCATIONS.json')}
    rows = []

    def public_source(spec):
        loc = locations[spec['path']]
        assert loc['sha256'] == spec['sha256']
        src = loc['public_source']
        if 'archive' in src:
            assert file_hash(src['archive']) == src['archive_sha256']
            return member_ref(src['archive'], src['member'], spec['sha256'])
        return file_ref(src['path'], spec['sha256'])

    for setting, group in sorted(main['settings'].items()):
        for seed, cells in sorted(group['by_seed'].items()):
            for cell, endpoint in cells.items():
                refs = {k:public_source(endpoint[k]) for k in
                        ['raw','labels','generation_manifest','training_manifest','termination']}
                train_ref = refs['training_manifest']
                refs['training_loss'] = member_ref(train_ref['archive'],
                    train_ref['member'].removesuffix('MANIFEST.json')+'checkpoint/trainer_state.json')
                train = json.loads(content(train_ref))
                rows.append({'scope':'main', 'endpoint_id':f'{setting}.{cell}.s{seed}',
                    'setting':setting, 'cell':cell, 'seed':int(seed), 'task':setting.rsplit('_',1)[1],
                    'run_id':train['run_id'], 'model':train['model']['repo'],
                    'platform':'Modal/full', 'dose':train['dose'], 'sources':refs})
    assert len(rows) == 72
    for group in 'ABCT':
        packet = ROOT/f'amendment8_{group}_results_review_v1/ENDPOINTS.json'
        data = read(packet)
        for endpoint in data['endpoints']:
            result_ref = file_ref(endpoint['result']['path'], endpoint['result']['sha256'])
            result = json.loads(content(result_ref)); pe = endpoint['public_evidence']
            archive = pe['raw']['archive']
            refs = {k:member_ref(v['archive'],v['member'],v['sha256']) for k,v in pe.items()
                    if k in ['raw','labels','training_manifest','training_request','training_loss','trainer_state']}
            refs['training_loss'] = refs.pop('trainer_state') if group != 'T' else refs['training_loss']
            refs['generation_manifest'] = member_ref(archive, 'evaluation/generation/MANIFEST.json')
            refs['termination'] = member_ref(archive, 'TERMINATION.json')
            refs['result'] = result_ref
            rows.append({'scope':'A8', 'endpoint_id':result['run_id'].split('_')[1].upper(),
                'setting':result['model']+' / '+result['task'], 'cell':result['cell'],
                'seed':result['seed'], 'task':result['task'], 'run_id':result['run_id'],
                'model':result['model'], 'platform':'Tinker/LoRA' if group=='T' else 'Modal/full',
                'dose':result['dose'], 'sources':refs})
    assert len(rows) == 98
    for path in sorted(ROOT.glob('a9_*_results/RESULTS.json')):
        result = read(path)
        if not result.get('A9_id'):
            continue
        archive = path.parent/'evidence.zip'
        tinker = result['A9_id'] == 'R04'
        members = {'raw':'evaluation/generation/raw.jsonl', 'labels':'scores/labels.jsonl',
            'generation_manifest':'evaluation/generation/MANIFEST.json', 'termination':'TERMINATION.json',
            'training_request' if tinker else 'training_manifest':
                'training/REQUEST.json' if tinker else 'training/MANIFEST.json',
            'training_loss':'training/train_loss.jsonl' if tinker else 'training/checkpoint/trainer_state.json'}
        refs = {k:member_ref(archive,v,result.get(k+'_sha256')) for k,v in members.items()}
        refs['result'] = file_ref(path)
        rows.append({'scope':'A9', 'endpoint_id':result['A9_id'],
            'setting':result['model']+' / '+result['task'], 'cell':result['cell'],
            'seed':result['seed'], 'task':result['task'], 'run_id':result['run_id'],
            'model':result['model'], 'platform':'Tinker/LoRA' if tinker else 'Modal/full',
            'dose':result['dose'], 'sources':refs})
    assert len(rows) == 113
    assert len({x['run_id'] for x in rows}) == 113
    assert Counter(x['scope'] for x in rows) == {'main':72,'A8':26,'A9':15}
    return rows


def calculate(entry):
    refs = entry['sources']
    labels = [json.loads(line) for line in content(refs['labels']).splitlines()]
    by_key = {(r['id'],r['draw']):r for r in labels}
    assert len(by_key) == len(labels)
    raw = content(refs['raw'])
    lengths=[]; seen=set(); capped=0; uncapped_correct=0; correct=0; nonnormal_uncapped=0
    for line in raw.splitlines():
        r = json.loads(line); key = (r['id'],r['draw'])
        assert key not in seen and key in by_key and r['draw'] == 0
        seen.add(key)
        assert isinstance(r['length_capped'],bool)
        y = by_key[key]['correct']; assert isinstance(y,bool)
        lengths.append(len(r['token_ids'])); capped += r['length_capped']; correct += y
        if not r['length_capped']:
            uncapped_correct += y
            normal = r['finish_reason']=='stop' and (r['stopped_on_terminator'] or r['string_stop'])
            nonnormal_uncapped += not normal
    assert seen == set(by_key)
    n = len(lengths); expected_n = 5000 if entry['task']=='math' else 1319
    assert n == expected_n
    summary = json.loads(content(refs['termination']))['all']
    assert (summary['responses'],summary['correct'],summary['length_cap_count']) == (n,correct,capped)
    if not nonnormal_uncapped:
        assert summary['normally_terminated_count'] == n-capped
        assert summary['normally_terminated_correct'] == uncapped_correct
    generation = json.loads(content(refs['generation_manifest']))
    config = generation['config']
    assert config['n'] == 1 and config['temperature'] == 0 and config['task']==entry['task']
    assert max(lengths) <= config['max_tokens']
    expected_step = entry['dose']['expected_updates']
    if entry['platform'] == 'Modal/full':
        training = json.loads(content(refs['training_manifest']))
        assert training['run_id'] == entry['run_id'] and training['cell'] == entry['cell']
        assert training['model']['repo'] == entry['model'] and training['config']['seed'] == entry['seed']
        assert generation['checkpoint_verification']['training_manifest_sha256'] == refs['training_manifest']['sha256']
        assert config['training_run_id'] == entry['run_id']
        state = json.loads(content(refs['training_loss']))
        history = [x for x in state['log_history'] if 'loss' in x]
        assert state['global_step'] == expected_step
        whole_run = [x['train_loss'] for x in state['log_history'] if 'train_loss' in x]
        whole_run_mean = whole_run[-1] if whole_run else None
        loss_definition = 'last logged optimizer-step loss (logging_steps=1), rounded by Trainer'
        assert training['config']['logging_steps'] == 1
    else:
        training = json.loads(content(refs['training_request']))
        assert training['run_id'] == entry['run_id'] and training['cell'] == entry['cell']
        assert training['model'] == entry['model'] and training['seed'] == entry['seed']
        history = [json.loads(x) for x in content(refs['training_loss']).splitlines()]
        whole_run_mean = None
        loss_definition = 'last optimizer-step masked target-token cross entropy from train_loss.jsonl'
    assert len(history) == expected_step and [x['step'] for x in history] == list(range(1,expected_step+1))
    last = history[-1]; assert last['step'] == expected_step
    assert expected_step >= 64
    last64_mean = statistics.mean(step['loss'] for step in history[-64:])
    uncapped = n-capped
    return {**{k:v for k,v in entry.items() if k!='sources'},
        'responses':n,'correct':correct,'accuracy':correct/n,
        'max_tokens':config['max_tokens'],'length_cap_count':capped,'length_cap_rate':capped/n,
        'output_tokens_total':sum(lengths),'output_tokens_mean':statistics.mean(lengths),
        'output_tokens_median':statistics.median(lengths),'output_tokens_max':max(lengths),
        'uncapped_count':uncapped,'uncapped_correct':uncapped_correct,
        'uncapped_accuracy':uncapped_correct/uncapped if uncapped else None,
        'uncapped_but_not_normal_count':nonnormal_uncapped,
        'final_training_loss':last['loss'],'final_loss_step':last['step'],
        'last64_training_loss_mean':last64_mean,
        'final_loss_definition':loss_definition,'whole_run_train_loss_reference_only':whole_run_mean,
        'existing_termination_summary_matches':True}


def main():
    entries = catalogue()
    rows=[]
    for i,entry in enumerate(entries,1):
        rows.append(calculate(entry))
        print(json.dumps({'completed':i,'total':len(entries),'endpoint':entry['endpoint_id']}),flush=True)
    assert sum(x['responses'] for x in rows) == 299968
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for name,value in [('INPUT_MANIFEST.json',{'utc':stamp,'script_sha256':file_hash(__file__),
            'source_policy':'Existing public raw tokens, frozen labels and complete training logs only',
            'endpoints':entries}),('RESULTS.json',{'utc':stamp,'rows':rows}),
            ('CHECKS.json',{'endpoints':113,'by_scope':dict(Counter(x['scope'] for x in rows)),
                'raw_outputs':sum(x['responses'] for x in rows),'unique_training_runs':113,
                'all_raw_label_joins_complete':True,'all_training_steps_complete':True,
                'all_existing_termination_counts_match':True,'new_model_calls':0,'new_training':0,
                'new_scoring':False,'bootstrap_or_hypothesis_tests':False,
                'uncapped_but_not_normal_total':sum(x['uncapped_but_not_normal_count'] for x in rows)})]:
        with (HERE/name).open('x') as f:
            json.dump(value,f,indent=2,ensure_ascii=False); f.write('\n')
    lines=['# 已有输出诊断表：主网格与 A8/A9', '',
        '113 个训练格：主网格 72、A8 26、A9 R/M 15；299,968 条既有 greedy 输出。逐格、逐种子列出，MATH 为完整 5,000 题，GSM8K 为 1,319 题。', '',
        '撞上限沿用原始输出的 length_capped 标记。token 长度是保存的 token_ids 数量，包含实际保存的终止 token；均值和中位数均包含撞上限输出。未撞上限准确率使用原标签并列出正确数/分母。最终损失取最后一个更新步的日志 loss，不使用全程平均 train_loss，也不是训练后重评损失；不同数据和模型的末批损失不能直接当作同一难度的评估分数。最后 64 步训练损失均值按每步等权计算，包含最后一次更新。', '',
        'A8/A9 为探索性，Tinker LoRA 与 Modal 全参保留单独标识。A9 LogiQA 试点评测/采样端点没有训练损失，不属于这 113 个训练格。此表不重判答案、不做新的统计检验。全部精度和每行证据哈希见 RESULTS.json / INPUT_MANIFEST.json。', '',
        '| 范围/端点 | 模型 | 任务 | 平台 | 格 (P,K,E) | seed | 撞上限 % | token 均值 | token 中位数 | 未撞上限正确/总数 (%) | 最后一步 loss | 最后 64 步训练损失均值 |',
        '|---|---|---|---|---|---:|---:|---:|---:|---|---:|---:|']
    for r in rows:
        dose=r['dose']; pk=(dose['parents'],dose['paths_per_parent'],dose['epochs'])
        label=r['cell'] if r['scope']=='main' else r['endpoint_id']
        accuracy='NA' if r['uncapped_accuracy'] is None else f"{100*r['uncapped_accuracy']:.2f}"
        lines.append(f"| {r['scope']}/{label} | {r['model'].split('/')[-1]} | {r['task']} | {r['platform']} | {pk} | {r['seed']} | {100*r['length_cap_rate']:.2f} | {r['output_tokens_mean']:.2f} | {r['output_tokens_median']:g} | {r['uncapped_correct']}/{r['uncapped_count']} ({accuracy}) | {r['final_training_loss']:.6f} | {r['last64_training_loss_mean']:.6f} |")
    (HERE/'TABLE.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'complete':True,'rows':len(rows),'outputs':sum(x['responses'] for x in rows)}))


if __name__ == '__main__':
    main()
