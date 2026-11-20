"""Weighted estimates from Claude's Z1 labels. Usage: python3 -I z1_stats.py Z1_DIR"""
import json, sys, math, collections, random
D = sys.argv[1]
it = {x['item']: x for x in json.load(open(f'{D}/Z1_ITEMS.json'))}
lab = {json.loads(l)['item']: json.loads(l) for l in open(f'{D}/Z1_LABELS.jsonl')}
S = json.load(open(f'{D}/Z1_SUMMARY.json'))
def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z*z/n; c = (p + z*z/(2*n)) / d; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return c - h, c + h
out = {}
for task in ('gsm8k', 'math'):
    s = S[task]; popA = s['stratum_population']['A_base0_stud1']
    xs = [k for k, v in it.items() if v['task'] == task and v['stratum'] == 'A_base0_stud1']
    c = collections.Counter(lab[k]['label'] for k in xs); n = len(xs); k = c['PM']
    lo, hi = wilson(k, n); gap = s['strict']['gap']
    auto_pm = sum(it[x]['secondary'] for x in xs)
    agree_auto = sum((lab[x]['label'] == 'PM') == it[x]['secondary'] for x in xs)
    out[task] = dict(n_eval=s['n'], strict=s['strict'], secondary=s['secondary'],
        gap_shrink_auto=gap - s['secondary']['gap'], gap_shrink_auto_share=round((gap - s['secondary']['gap']) / gap, 3),
        stratumA_population=popA, stratumA_sample=n, stratumA_label_counts=dict(c),
        est_base_parser_miss_in_A=round(popA * k / n, 1), est_ci95=(round(popA*lo, 1), round(popA*hi, 1)),
        est_gap_share=round(popA * k / n / gap, 3), est_gap_share_ci95=(round(popA*lo/gap, 3), round(popA*hi/gap, 3)),
        auto_vs_human_agreement_in_A=f'{agree_auto}/{n}',
        other_strata={st+'|'+m: dict(collections.Counter(lab[x]['label'] for x, v in it.items() if v['task']==task and v['stratum']==st and v['model']==m))
                      for st, m in (('B_base1_stud0','student'),('C_both0','base'),('C_both0','student'))})
json.dump(out, open(f'{D}/Z1_ESTIMATES.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
# owner spot-check: 6 Claude-PM + 6 non-PM, fixed seed, blind order, no labels shown
rng = random.Random(20261020)
pm = sorted(k for k in it if lab[k]['label'] == 'PM'); non = sorted(k for k in it if lab[k]['label'] != 'PM')
pick = rng.sample(pm, 6) + rng.sample(non, 6); rng.shuffle(pick)
json.dump(pick, open(f'{D}/Z1_OWNER_SPOTCHECK_IDS.json', 'w'))
lines = ['# Z1 抽查表（盲表，12 条）', '',
 '每条给出：题目、标准答案（gold）、模型输出。模型身份和 Claude 的标签都已隐藏。请只看**最终答案**，每条选一个类别填在「你的标签」后面：', '',
 '- **PM**（解析器漏读）：输出里明确给出了正确的最终答案，只是格式不标准（没有 \\boxed{}、没有 "Answer:"，或答案后面跟了无关文字）',
 '- **WR**（真的答错）：最终答案是错的',
 '- **MID**（中间值）：正确的数出现在过程中，但最终给出的答案是错的',
 '- **NC**（无结论）：没有给出最终答案，或被截断',
 '- **LAB**（标签问题）：标准答案本身有问题', '']
for i, k in enumerate(pick, 1):
    v = it[k]; t = v['text']
    if len(t) > 2500: t = t[:900] + '\n[...中间省略...]\n' + t[-1400:]
    lines += [f'## {i}. {k}（{"GSM8K" if v["task"]=="gsm8k" else "MATH-500"}）', '', f'**题目：** {v["question"]}', '', f'**标准答案：** `{v["gold"]}`', '', '**模型输出：**', '', '```text', t, '```', '', '**你的标签：** ____', '']
open(f'{D}/Z1_OWNER_SPOTCHECK.md', 'w').write('\n'.join(lines))
print('spotcheck', pick)
