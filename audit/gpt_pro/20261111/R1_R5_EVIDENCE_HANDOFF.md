# GPT Pro R1–R5 文献证据交接 — 2026-11-11

> AI生成的内部科研资料，不是课程报告、PPT、演讲或Slack成稿。本文件不修改代码、结果、评分、准入或预算，不授权模型调用或恢复自动化。全文和逐项来源保存在下列不可变阅读提交。

## 1. 阅读产物

阅读库提交：**e3b57036e358ddd91a1d6c3fc96d9ee53e77aea5**，新增62–68，原01–61未改动。

| 任务 | 不可变笔记入口 | 状态 |
|---|---|---|
| 总览 | [62 — R1–R5索引](https://github.com/Townzc/Obsidian-Vault/blob/e3b57036e358ddd91a1d6c3fc96d9ee53e77aea5/交换课程/cs294-288/Papers/62%20-%20R1-R5%20Literature%20Audit%20Index.md) | 证据、缺口与版本范围 |
| R1 Li | [63 — Li配置/图5/UWNSL](https://github.com/Townzc/Obsidian-Vault/blob/e3b57036e358ddd91a1d6c3fc96d9ee53e77aea5/交换课程/cs294-288/Papers/63%20-%20R1%20Li%20Learnability%20Configuration%20and%20Assets%20Audit.md) | 已核查；原文与代码冲突保留 |
| R1 OpenThoughts | [64 — D/E与1.5B配置](https://github.com/Townzc/Obsidian-Vault/blob/e3b57036e358ddd91a1d6c3fc96d9ee53e77aea5/交换课程/cs294-288/Papers/64%20-%20R1%20OpenThoughts%20Appendix%20D%20E%20Audit.md) | 已定向核查；若干发布默认值未绑定 |
| R2 | [65 — 官方基线/零样例协议](https://github.com/Townzc/Obsidian-Vault/blob/e3b57036e358ddd91a1d6c3fc96d9ee53e77aea5/交换课程/cs294-288/Papers/65%20-%20R2%20Official%20Baselines%20and%20Zero%20Shot%20Protocols.md) | 已建表；缺项明确NR |
| R3 | [66 — 六篇分配证据矩阵](https://github.com/Townzc/Obsidian-Vault/blob/e3b57036e358ddd91a1d6c3fc96d9ee53e77aea5/交换课程/cs294-288/Papers/66%20-%20R3%20Allocation%20Evidence%20Matrix.md) | 文献矩阵完成；新H1–H3编号映射待原句 |
| R4 | [67 — 激发/学习与边际收益](https://github.com/Townzc/Obsidian-Vault/blob/e3b57036e358ddd91a1d6c3fc96d9ee53e77aea5/交换课程/cs294-288/Papers/67%20-%20R4%20Elicitation%20Learning%20and%20Marginal%20Returns.md) | 支持与限制分开，不作普遍定律 |
| R5 | [68 — 条件式评审清单](https://github.com/Townzc/Obsidian-Vault/blob/e3b57036e358ddd91a1d6c3fc96d9ee53e77aea5/交换课程/cs294-288/Papers/68%20-%20R5%20Conditional%20Reviewer%20Audit.md) | 新版§5未取得，不是逐条审阅/PASS |

## 2. 应先处理的五个发现

**A. Li论文身份必须固定。** UWNSL、§3.4、Tables5/6对应Yuetai Li等《Small Models Struggle to Learn from Strong Reasoners》（Findings ACL2025），不是此前结构/内容讨论中的Dacheng Li论文。[L]

**B. Li的论文规格与公开YAML并不一致。** AppendixA训练长度为16384；固定代码1863f15a的Qwen3B-Instruct long/short YAML为8192、per-device2、gradient_accumulation1。只有采用4个DP rank时才推得global batch8；不把它套到所有Base/LoRA运行。Full warmup、LoRA rank/alpha/accum等没有完整历史绑定。该代码SFT默认packing=False、train_on_prompt=False，是代码行为，不等于已证明历史运行全部如此。[L][C]

**C. Figure5不是未训练Base的准确率。** 它是Long−Short或Large-teacher−Small-teacher两种SFT配方的差值；Base标记指学生初始化。笔记63给图读范围并明确非精确绝对分数。公开collection列6份数据、24个模型条目，本轮未在其中找到对应§3.4 Base检查点。不得从gap倒推原始Base分数。[L][U]

**D. 基线表需按协议而非模型简称比较。** Qwen官方通用1.5B Base MATH35.0/GSM68.5均为4-shot，前者不是零样例MATH500；Meta官方Base表没有这两项数学分数。OLMo2 v3 Table22给1B Base GSM43.8，Table23的68.3/20.7是Instruct。RISE正式会议论文给通用Qwen1.5B Base零样例ChatML MATH500为2.0（其随机采样协议），不是推荐目标分数，也不为项目27.2背书。[Q][M][O][R]

**E. 等资源与机制主张必须收紧。** OT/OMI2主要匹配最终样本量；DART匹配近似正确库存；Yuan的RFT主组匹配epochs而非updates；Bansal明确匹配近似生成算力/历史输出价格；AceReason的七点P/K系数来自扩量回归而非等成本随机化设计。既不能说前人不考虑成本，也不能把“弱学生提升更大”与“弱学生学不会复杂监督”视为矛盾：剩余空间与监督可学习性是两种条件，现有证据不证明训练前分数单独决定边际收益。[见66–67]

## 3. 尚未关闭，不能包装成全部任务完成

1. **新版H1–H3和§5全文。** 本轮查了可见分支、近期issues和文件，研究HEAD可见28cc0717、Claude审查HEAD636e2b1f仍为10月旧记录。用户转来的任务没有包含原假说/设计正文。因此R3先做主题映射，R5为条件式专家清单；没有沿用旧P008/P011编号，也没有给未知设计PASS/FAIL。
2. **Li历史运行缺项。** Base专属模板/命令、完整LoRA参数、full warmup、16384与8192的运行对应关系仍缺；Figure5仅能近似读差值。公开演示代码不能无条件当作所有会议结果的确切配置。
3. **OpenThinker3-1.5B复现缺项。** 已核保存的Instruct/full/16K/7epoch/batch256/LR1.6e-4配置，但未显式写出的packing/optimizer等须绑定实际fork默认值；内部数据别名与发布数据revision、原生评估命令需补齐。
4. **官方基线缺项。** Llama3.2 Base数学仍NR；OLMo1B Base MATH仍NR；若干Instruct的完整提示/长度/解码不能由官方表推断。不以第三方成绩填进官方栏。
5. **图像核查范围。** 关键Li/Yuan/DART/Bansal/OMI2/Ace/LIMA图表成功目视核对；OT部分D/E和OLMo2附录截图缓存失败，相关条目依原文解析文本/HTML核查，笔记已明确。没有声称完整逐页复现或取得全量数据/权重。

## 4. 给Claude的绑定方式

取得新版方案后，逐条填写：H原句→主估计量→受控对比→文献支持/反例→剩余混淆→反证条件。§5检查重点为模型/任务交叉、三种预算、共同支持筛选、真实响应多样性、库存与曝光、模型/采购/题目三层随机性、测试集选择泄漏与可推广范围。

笔记68给出配对discordance下的功效示例：在固定两模型、iid测试题、80%功效/双侧5%的近似下，500题且discordance20%时MDE约5.6pp。它是显式假设推算，不是本项目保证；训练seed与采购draw变异尚需另计。一个设置显著另一个不显著，不等于交互显著。

以上只为文献与方案讨论资料。没有新训练、评分、开支、自动化或外部消息。

## 原始入口

[L] [Li ACL2025全文](https://aclanthology.org/2025.findings-acl.1301.pdf)，AppendixA Tables5/6、§3.4 Figure5。
[C] [Li固定代码](https://github.com/Small-Model-Gap/Small-Model-Learnability-Gap/tree/1863f15a7c58b8a69fb1d18235ea85bca26d0484)。
[U] [UWNSL模型collection](https://huggingface.co/collections/UWNSL/small-model-learnability-gap-models)；[数据collection](https://huggingface.co/collections/UWNSL/small-model-learnability-gap-dataset)。
[Q] [Qwen官方表](https://qwenlm.github.io/blog/qwen2.5-llm/)。
[M] [Meta官方卡](https://huggingface.co/meta-llama/Llama-3.2-1B)。
[O] [OLMo2 v3](https://arxiv.org/pdf/2501.00656v3)，Tables20–23。
[R] [RISE NeurIPS2025](https://proceedings.neurips.cc/paper_files/paper/2025/file/bd3d106d8e9789ce4fd40e1edafe71d5-Paper-Conference.pdf)，Table1/Figure10。
