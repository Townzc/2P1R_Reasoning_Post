# GPT Pro：P008文献复核与Codex交接

日期：2026-10-14。审阅源固定为 `b5dc82af24afbfce008802098c3be27778396a51` 的 [Claude说明](../../../claude/20261014ar/STATUS_AND_JUDGMENT.md)。本页是研究阅读与方法判断，不是重新评分后的独立审计PASS，不批准GPU任务或增加预算。原始结果和Claude报告均未修改。

## 完整笔记

以下三个链接固定到Obsidian仓库提交 `76f7e5361813aade0aad241a9b728044ecc3225c`，正文已与本地定稿的Git blob SHA核对一致：

1. [36 - P008 Saturation Evidence Review](https://github.com/Townzc/Obsidian-Vault/blob/76f7e5361813aade0aad241a9b728044ecc3225c/交换课程/cs294-288/Papers/36%20-%20P008%20Saturation%20Evidence%20Review.md)：报告逐项判断、标签抽查、平台与联合覆盖的边界。
2. [37 - P008 Six Theme Literature Map](https://github.com/Townzc/Obsidian-Vault/blob/76f7e5361813aade0aad241a9b728044ecc3225c/交换课程/cs294-288/Papers/37%20-%20P008%20Six%20Theme%20Literature%20Map.md)：第7节六主题的一手文献、核查范围、项目意义和不可外推之处。
3. [38 - P008 Diagnostic Handoff](https://github.com/Townzc/Obsidian-Vault/blob/76f7e5361813aade0aad241a9b728044ecc3225c/交换课程/cs294-288/Papers/38%20-%20P008%20Diagnostic%20Handoff.md)：已有输出审计、评测校准、错误示范配对及有限后续采购试验。

## 需要修订的主要判断

- 支持暂停原设定的大规模扩表。16格显示局部平台，但B与T主网格同时变化，不能断言数据和训练量分别均无作用。
- 4-shot接近SFT是激发性校准，不证明“只教格式”；官方Instruct是参考模型，不是相同base的能力上限。
- 跨18个模型的oracle联合覆盖不是单模型pass@18；八模型投票81.6%证明集合互补，不证明每个学生都有同样潜在覆盖。
- 全错67题的标签检查不是整个测试集噪声率。测试CSV只有13个具体ID与“其余54题”汇总行；应补逐题记录与独立理由。
- GSM8K-Platinum全测试版本移除110题、重标10题；不能把“约1%坏题”作为已确认总体比例，也不能把这120题都叫金标错误。官方数据卡及边界见第37篇。
- 696是失败尝试数；16.2%的token预算份额应通过实际输入/输出token账本核对。25和1/4不能脱离题目单位全局等价化。

## 优先工作顺序（建议，非执行授权）

先用已有输出核对：评分/截断、标签与Platinum映射、尾部token费用、实际训练曝光。再考虑owner批准的base4-shot和官方Instruct评测。原“自然错误池429条”实验与正确池混杂题目/难度/标签可靠性，不宜原样用于内容无关的因果结论；优先同一批可靠parent上的正确/错误配对，或明确仅研究终答标签的受控干预。

若仍存在平台，只改变一个模型或任务轴做有上限先导，确认供给与学习响应后再扫价格。稳定性先作诊断，保留“何时继续给旧题买新解、何时转向新题”的分配主线。不同时加入强教师升级、RL、课程优化等多个新变量。

## 最先查的原文

[Li：内容/结构消融](https://arxiv.org/html/2502.07374v2)；[Platinum官方清洗统计](https://huggingface.co/datasets/madrylab/gsm8k-platinum)；[DART §3.2](https://arxiv.org/html/2407.13690v2)；[SIKeD](https://aclanthology.org/2025.findings-acl.513/)；[ReASC，2026](https://aclanthology.org/2026.findings-acl.1085/)；[Spurious Rewards，ICML2026正式页](https://proceedings.mlr.press/v306/shao26d.html)。

本轮读取了说明和分类文件，转录计算16格描述统计，并独立核对原始GSM8K test/00454的明显参考答案错误；没有重新运行原始模型、完整采购账本或ALL_CELLS审计。saturation.png未取得可见图像，平台解释依据报告数值表。完整阅读范围在三份笔记中分别列明。
