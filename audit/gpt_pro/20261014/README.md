# GPT Pro：P008文献复核与Codex交接

日期：2026-10-14。原始审阅源为 `b5dc82af24afbfce008802098c3be27778396a51` 的 [Claude说明](https://github.com/Townzc/2P1R_Reasoning_Post/blob/b5dc82af24afbfce008802098c3be27778396a51/audit/claude/20261014ar/STATUS_AND_JUDGMENT.md)。本页是研究阅读与方法判断，不是重新评分后的独立审计PASS，不批准GPU任务或增加预算。原始结果和Claude报告均未修改。

**最新补充：** 写入期间出现了[20261014as代码与输入审计](https://github.com/Townzc/2P1R_Reasoning_Post/blob/517955ef6ae692846a5a8a3180938928418298c1/audit/claude/20261014as/REPORT.md)，审计执行源32c473d6的三个owner已授权探索slot，结论是代码/规格/输入绑定的PASS-WITH-NOTES，**不是运行结果**。先读第39篇更新，不要依据原始b5快照重复申请或提交已有slot；执行是否完成由实际结果包确认。

## 完整笔记

以下四份固定到Obsidian仓库提交 `a8d2a2baf0d23696a163bab4470b382dd7c47b16`。前三篇的原始审阅范围保留为b5，第39篇补充并行发生的新审计。远端文件与本地正文的Git blob SHA已逐份核对。

1. [39 - P008 Exploration Admission Addendum](https://github.com/Townzc/Obsidian-Vault/blob/a8d2a2baf0d23696a163bab4470b382dd7c47b16/交换课程/cs294-288/Papers/39%20-%20P008%20Exploration%20Admission%20Addendum.md)：**先读**；429条错误示范来自101题，AI金标/歧义标签的样本混合，以及授权/输入审计不等于结果。
2. [36 - P008 Saturation Evidence Review](https://github.com/Townzc/Obsidian-Vault/blob/a8d2a2baf0d23696a163bab4470b382dd7c47b16/交换课程/cs294-288/Papers/36%20-%20P008%20Saturation%20Evidence%20Review.md)：报告逐项判断、标签抽查、平台与联合覆盖的边界。
3. [37 - P008 Six Theme Literature Map](https://github.com/Townzc/Obsidian-Vault/blob/a8d2a2baf0d23696a163bab4470b382dd7c47b16/交换课程/cs294-288/Papers/37%20-%20P008%20Six%20Theme%20Literature%20Map.md)：第7节六主题的一手文献、核查范围、项目意义和不可外推之处。
4. [38 - P008 Diagnostic Handoff](https://github.com/Townzc/Obsidian-Vault/blob/a8d2a2baf0d23696a163bab4470b382dd7c47b16/交换课程/cs294-288/Papers/38%20-%20P008%20Diagnostic%20Handoff.md)：已有输出审计、评测校准、未来同题配对及有限后续采购试验。旧授权状态以第39篇为补充，不自动变更已绑定输入。

## 需要修订的主要判断

- 支持暂停原设定的大规模扩表。16格显示局部平台，但B与T主网格同时变化，不能断言数据和训练量分别均无作用。
- 4-shot接近SFT是激发性校准，不证明“只教格式”；官方Instruct是参考模型，不是相同base的能力上限。
- 跨18个模型的oracle联合覆盖不是单模型pass@18；八模型投票81.6%证明集合互补，不证明每个学生都有同样潜在覆盖。
- 全错67题的标签检查不是整个测试集噪声率。原测试CSV只有13个具体ID与“其余54题”汇总行；应补逐题记录与独立理由。
- GSM8K-Platinum全测试版本移除110题、重标10题；不能把“约1%坏题”作为已确认总体比例，也不能把这120题都叫金标错误。官方数据卡及边界见第37篇。
- 696是失败尝试数；16.2%的token预算份额应通过实际输入/输出token账本核对。25和1/4不能脱离题目单位全局等价化。
- 新审计确认错误池429条来自101个parent；45条所在题被Claude标为金标错误，127条被标为歧义/缺陷，仍需独立核验。正确depth参考965/1319、121个有答案题、469条答案比breadth更接近覆盖规模，但仍不是同parent对照。无论新结果升降，都不能单独识别真实性的因果作用。

## 优先工作顺序（建议，非执行授权）

先复用已有审计证据，核对评分/截断、标签与Platinum映射、尾部token费用、实际训练曝光。已授权探索按原有guard和绑定输入执行，不因本文重复提交、重采样或改训练数据。取得结果后按第39篇的边界解释；同题正确/错误配对或仅终答标签干预，属于后续候选，不自动加入本轮。

若仍存在平台，只改变一个模型或任务轴做有上限先导，确认供给与学习响应后再扫价格。稳定性先作诊断，保留“何时继续给旧题买新解、何时转向新题”的分配主线。不同时加入强教师升级、RL、课程优化等多个新变量。

## 最先查的原文

[Li：内容/结构消融](https://arxiv.org/html/2502.07374v2)；[Platinum官方清洗统计](https://huggingface.co/datasets/madrylab/gsm8k-platinum)；[DART §3.2](https://arxiv.org/html/2407.13690v2)；[SIKeD](https://aclanthology.org/2025.findings-acl.513/)；[ReASC，2026](https://aclanthology.org/2026.findings-acl.1085/)；[Spurious Rewards，ICML2026正式页](https://proceedings.mlr.press/v306/shao26d.html)。

本轮读取了说明、分类文件与新增输入审计，转录计算16格描述统计，并独立核对原始GSM8K test/00454的明显参考答案错误；没有重新运行原始模型、完整采购账本或ALL_CELLS审计。saturation.png未取得可见图像，平台解释依据报告数值表。完整阅读范围在四份笔记中分别列明。
