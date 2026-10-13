"""Build an evidence handoff from completed audits, never a slide or model run."""
import argparse
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(summary_path, closeout_path, supply_path, figures_path, out):
    s, c, supply = read(summary_path), read(closeout_path), read(supply_path)
    expected = {f'{policy}_p{price}_s{seed}' for policy in ('breadth', 'depth')
                for price in (0, 4) for seed in (17, 23)}
    assert set(c['full_student_oracles']) == set(s['sources']) == expected
    assert c['main_endpoint_outputs'] == s['endpoint_outputs'] == 10552
    assert c['main_supervised_targets'] == s['supervised_targets'] == 4194296
    assert c['main_scientific_updates'] == s['updates'] == 2048
    assert c['main_endpoint_unknown'] == 0 and c['cpu_audit_labels'] == 14
    assert not c['containers'] and c['provider']['state'] == 'stopped'
    figures_path = Path(figures_path)
    fig = read(figures_path / 'PROVENANCE.json')
    assert fig['summary_sha256'] == sha(summary_path)
    assert fig['closeout_sha256'] == sha(closeout_path)
    assert all(sha(figures_path / name) == h for name, h in fig['figures'].items())
    cells = {x['cell']: x for x in s['table']}
    for cell, row in cells.items():
        for seed, v in row['seeds'].items():
            assert v['correct'] == c['full_student_oracles'][f'{cell}_s{seed}']['correct']
            assert v['n'] == 1319
        a = row['tariff_procurement']; d = supply['cells'][cell]
        assert a['attempts'] == d['attempts'] and a['usable'] == d['usable']
        assert d['attempts'] == d['usable'] + d['invalid_under_frozen_checker'] + d['valid_duplicates_rejected']
    workers = [v for row in cells.values() for v in row['seeds'].values()]
    billing = s['billing']
    meter = float(billing['summary']['metered_cost'])
    lines = [
        '# P007 中期：已核验实验事实与局限',
        '',
        '供研究者自行组织汇报和接受审计。全部数值来自冻结终点和完成的独立核验；不新增模型调用、不选择最好检查点。',
        '',
        '## 当前结论',
        '',
        '统一 token 计价的八项学生已完成：2 个训练种子 × 2 档题价 × 多题/多解。10,552 条终点评测、2,048 次更新、4,194,296 个监督 targets 与 8 个完整终点状态全部核验；独立 CPU 审计证据链通过，GPU/CPU 容器均退出；原审计及有限续核的失败/继承范围在最终收尾清单中分别保留。',
        '',
        '第一个种子在零题价略偏多题、高题价略偏多解；第二个种子在两档题价下均持平。因此，现有实验没有复现稳定的策略优劣反转。共同预算上限下的采购—训练—评测流程已跑通，但尚不足以给出普遍的最优分配建议。',
        '',
        '## 八项冻结结果',
        '',
        '| 题价 | 策略 | seed17 正确/1319 | seed23 正确/1319 | 两个已观察种子平均 | 长度截断数17/23 |',
        '|---|---|---:|---:|---:|---:|',
    ]
    for price in (0, 4):
        for policy, title in (('breadth', '多题'), ('depth', '多解')):
            row = cells[f'{policy}_p{price}']; a, b = row['seeds']['17'], row['seeds']['23']
            lines.append(f"| {'0' if price == 0 else '4m'} | {title} | {a['correct']} ({a['accuracy']*100:.2f}%) | {b['correct']} ({b['accuracy']*100:.2f}%) | {row['mean_accuracy']*100:.2f}% | {a['truncated_outputs']}/{b['truncated_outputs']} |")
    lines += ['', '每项均为固定第256步一次性 greedy 评测，完整1,319题；512-token长度截断按原规则计错，未从分母剔除。',
              '', '## 主要差值与条件区间', '',
              '正差值表示多解较好。交互 = 高题价差值 − 零题价差值，单位为百分点。', '',
              '| 比较 | seed17 | seed23 | 两个已观察种子的平均 |',
              '|---|---:|---:|---:|']
    for key, title in [('depth_minus_breadth_p0', '零题价：多解−多题'),
                       ('depth_minus_breadth_p4', '高题价：多解−多题'),
                       ('price_interaction', '题价交互')]:
        x = s['contrasts'][key]
        def fmt(v, point):
            lo, hi = v['conditional_question_interval_pp']
            return f'{v[point]:+.2f} [{lo:+.2f}, {hi:+.2f}]'
        lines.append('| '+title+' | '+fmt(x['per_seed']['17'], 'difference_pp')+' | '+fmt(x['per_seed']['23'], 'difference_pp')+' | '+fmt(x, 'mean_difference_pp')+' |')
    lines += ['', '区间由预先固定的10,000次共享配对题目 bootstrap 计算（seed20261013），未做多重比较校正。平均的计算先按题目平均两个已观察种子的差值，再对题目重采样；不把2,638个回答当独立题目，也不估计训练种子或采购总体的不确定性。区间跨零不等于策略等效；正交互也不单独证明高价时多解胜出。',
              '', '## 预算实际买到了什么', '',
              '共同获取上限211,257假设计价单位；prompt/output含EOS均1单位/token。m=373.341796875为先导每次尝试的平均token费用，非每个有效解成本；新题价为0或4m。失败和重复收费。', '',
              '| 题价/策略 | 购题P | 有可用解的题数 | 可用解N | 尝试 | 检查器未通过 | 有效重复拒绝 | 剩余上限 | 每解平均曝光17/23 |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for cell in ('breadth_p0', 'depth_p0', 'breadth_p4', 'depth_p4'):
        row = cells[cell]; a = row['tariff_procurement']; d = supply['cells'][cell]
        exposure = [row['seeds'][str(seed)]['training_exposure']['mean_per_answer'] for seed in (17, 23)]
        title = ('0' if cell.endswith('p0') else '4m') + '/' + ('多题' if cell.startswith('breadth') else '多解')
        lines.append(f"| {title} | {a['acquired']} | {a['covered']} | {a['usable']} | {a['attempts']} | {d['invalid_under_frozen_checker']} | {d['valid_duplicates_rejected']} | {100*a['unused']/a['cap']:.2f}% | {exposure[0]:.2f}/{exposure[1]:.2f} |")
    lines += ['', '检查器未通过包含错误、未解析及终止规则不合格，并非逐步推理的人工标签。四格共有1,408次入选前缀尝试、1,203条可用解、203条检查器未通过和2条有效重复，技术性无返回为0；全部原采购2,064输出、先导1,024输出及未入选后缀仍计入真实平台成本。',
              '', '## 与前一阶段的关系', '',
              '原公开答案库四组在431题开发评测上：Repeat309/307、Solutions354/355、Breadth350/352、Mixed348/351，base256。Solutions−Repeat平均+10.79pp；Breadth−Solutions平均−0.81pp，未识别稳定的多题优势。前者支持该多答案训练策略相对锚点重复的收益，未单独识别推理路径多样性或重复损伤。',
              '',
              '该答案库历史获取费用未知；不能套用当前teacher成本。原时间计价先导953/969 of1319保留为工程先导，未与新八项混合。431题开发集与1,319题官方测试、教师来源和数据库存不同，不能把两阶段准确率差当成某个方法的因果退化。',
              '', '## 中期必须同时呈现的局限', '',
              '- 两训练种子共享每格同一教师答案库存；每格只有一条随机teacher轨迹。训练重复不是采购重复，题价交互仍条件于这些库存。',
              '- 这是共同预算上限：四格仍有6.14%–12.26%未使用，均超过原5%严格等支出阈值。它不是等实际花费，也不是实际API美元最优。',
              '- 固定监督targets和更新数带来不同重复曝光，高价多题约20.75次、多解约8次。这是整体策略效果的一部分，不能孤立证明多样性或重复损伤的机制。',
              '- 原冻结解析器存在正确框内答案与空答案陈述并存时的漏判；主分保持原规则。任何后续敏感性须统一覆盖八项、单列为事后补充。',
              '- 512-token推理上限及截断计错属于评测契约。正确最终答案和不同文本不证明推理过程正确或结构多样。',
              '- 官方测试题在9月已被研究者观察过；不声称全新或无预训练污染。',
              '- 原训练抢占、工程失败、8条旧中间诊断unknown、旧时间计价故障及只读传输失败均保留；新八项正式终点无缺失。',
              '', '## 与最接近工作的边界', '',
              '- [When Does Generating More Help?](https://arxiv.org/html/2607.01727v1)比较匹配q×r样本预算，小预算下两方向可以接近，较大预算下扩展题目更强。当前小规模结果不构成对其结论的反证；本研究进一步明确题目价格、失败尝试与独立学生训练约束。',
              '- [OpenMathInstruct-2](https://arxiv.org/html/2410.01560v2)已在固定256K配对库存下改变题目数量并观察多题收益；P/R权衡本身已有直接前例。',
              '- [DART-Math](https://arxiv.org/html/2407.13690v2)已研究覆盖、有限尝试与达成答案配额的原始采样成本。因此计入失败或按难度配置生成并非独立新意。候选贡献应是经重复验证的成本条件与分配决策。',
              '', '## 中期后最值得补的设计（未准入、未执行）', '',
              '优先补独立采购重复，而不是继续给同一答案库存增加训练种子。冻结新的问题抽样与顺序，在每个独立采购重复中完成相同2策略×2题价，所有失败/重复/零供给题保留；用基于(problem, attempt)的预定随机流配对各价格场景，减少不同teacher轨迹对价格交互的干扰。至少多个独立采购重复才允许把采购变异纳入不确定性，具体剂量和费用另行设计。',
              '',
              '预先规定较小尾部动作、最坏token预留与停止规则，降低未花完预算；不能看已有答案后挑选便宜后缀填满。获取成本与学生训练预算分别控制，让P、N及有效R自然变化。若题目购买包含参考答案/验证器，成本定义必须明确，避免首解重复收费。',
              '',
              '确认集、最小有意义差异与统计单位在新结果前锁定，优先检验两档各自策略差值和价格交互的重复性。只有这些稳定后，再增加未用于开发推荐规则的价格/预算设置来验证决策；两策略、两价格不足以拟合普遍最优R或价格阈值。重复曝光/链质量可做后续机制问题，但不挤占本次中期的结果冻结与练习。',
              '', '## 费用与耗时', '',
              f"平台计量快照（{billing['utc']}）为${meter:.2f}，billed={billing['summary']['billed_cost']}；这是包含此前准备/失败/工程/采购的延迟workspace计量，不是最终发票或剩余余额。${s['reservation_usd']:.2f}为保守预留而非实际费用；$450支出上限与至少$50保护保持不变。", '',
              f"新八项训练阶段合计{sum(v['train_seconds'] for v in workers)/60:.1f} GPU分钟，有限worker合计{sum(v['wall_seconds'] for v in workers)/3600:.2f} GPU小时。其余worker时间包含终点评测、验证及读写开销；这些是已记录运行时长，不等于服务商最终账单。", '',
              '被动GPU采样及逐项耗时另见[运行诊断](P007B_TOKEN_RUNTIME_DIAGNOSTICS.json)：按约60秒采样混合各阶段，不能当FLOPS效率或硬件最优性证据。计算和收尾已完成，后续优先研究者组织材料、审计意见和练习；不为不显著结果自动扩组或调参。',
              '', '## 复现与图表', '',
              '主图：[差值与题价交互](figures_token_v1/policy_gaps_and_price_interaction.png)；辅助图：[各格准确率](figures_token_v1/accuracy_by_price_and_seed.png)（0–100%纵轴）。图表只读取冻结汇总，不新增bootstrap或模型调用。',
              '',
              '数据和完整核验：[最终审计包](../p007_audit/token_final_v1/REVIEW_REQUEST.md)。每轮Claude判定仅适用于对应固定提交；最终包的审计状态见WORKBOARD和处理记录。',
              '',
              f"来源SHA：summary `{sha(summary_path)}`；closeout `{sha(closeout_path)}`；supply `{sha(supply_path)}`。",
    ]
    out = Path(out)
    with out.open('x') as f:
        f.write('\n'.join(lines)+'\n')
    return dict(path=str(out), sha256=sha(out), new_model_calls=0)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('summary', 'closeout', 'supply', 'figures', 'out'):
        p.add_argument('--'+name, required=True)
    a = p.parse_args()
    print(json.dumps(build(a.summary, a.closeout, a.supply, a.figures, a.out)))
