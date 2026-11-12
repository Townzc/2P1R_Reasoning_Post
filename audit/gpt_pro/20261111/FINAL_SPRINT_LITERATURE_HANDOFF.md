# GPT Pro期末文献交接 — 2026-11-11

**性质：AI生成的内部科研证据，不是课程报告、PPT、演讲或Slack稿件。** 课程写作由owner独立完成。本文件不修改实验、分数、准入状态或预算，不授权GPU/API调用，不恢复自动化，不代替Claude的新方案与独立审查。

## 1. 本轮范围

用户提供教师中期评语：优先建立可信实验设置，核对Qwen2.5/MATH50027.2及SFT严重退化，借鉴正式发表工作；避免仅用Qwen/MATH与OLMo/GSM8K两个同时改变模型和任务的条件作广泛解释。用户已请Claude回顾并拟新方案。

本轮读取项目快照`ff30fafee7b3df3d230a1170eeb930188e8d8a2a`的COLLABORATION、WORKBOARD及P011扩量交接。COLLABORATION操作状态较旧；WORKBOARD最新可见为2026-10-23。没有读取到新的期末方案，因此不声称共同定案，也不重开已关闭旧审查。

分工沿用：owner科学决定/开支/课程表达/外部发送；GPT Pro原始文献证据；Codex配置与实现、受限执行及产物；Claude设计讨论、独立方法与结果审核。新增研究笔记不是执行许可。

## 2. 本批不可变阅读入口

阅读库：`Townzc/Obsidian-Vault`，提交 **`6a041ca8398a1650fe77a68cc6b46d2ac8c937ef`**。只新增55–61，原01–54未改动。

- [55 文献证据图与优先级](https://github.com/Townzc/Obsidian-Vault/blob/6a041ca8398a1650fe77a68cc6b46d2ac8c937ef/交换课程/cs294-288/Papers/55%20-%20Final%20Sprint%20Reference%20Evidence%20Map.md)
- [56 OpenThoughts小模型保存配置与评分审计](https://github.com/Townzc/Obsidian-Vault/blob/6a041ca8398a1650fe77a68cc6b46d2ac8c937ef/交换课程/cs294-288/Papers/56%20-%20OpenThoughts%20Small%20Model%20Recipe%20and%20Scorer%20Audit.md)
- [57 DeepSeek-R1蒸馏与评估校准](https://github.com/Townzc/Obsidian-Vault/blob/6a041ca8398a1650fe77a68cc6b46d2ac8c937ef/交换课程/cs294-288/Papers/57%20-%20DeepSeek%20R1%20Distillation%20and%20Evaluation%20Calibration.md)
- [58 SmolLM2小模型SFT及控制题源](https://github.com/Townzc/Obsidian-Vault/blob/6a041ca8398a1650fe77a68cc6b46d2ac8c937ef/交换课程/cs294-288/Papers/58%20-%20SmolLM2%20Small%20Model%20SFT%20and%20Controlled%20Data%20Sources.md)
- [59 Thinkless独立SFT warm-up参照](https://github.com/Townzc/Obsidian-Vault/blob/6a041ca8398a1650fe77a68cc6b46d2ac8c937ef/交换课程/cs294-288/Papers/59%20-%20Thinkless%20SFT%20Warmup%20as%20a%20Reproduction%20Control.md)
- [60 OpenMathInstruct-2匹配覆盖重读](https://github.com/Townzc/Obsidian-Vault/blob/6a041ca8398a1650fe77a68cc6b46d2ac8c937ef/交换课程/cs294-288/Papers/60%20-%20OpenMathInstruct-2%20Matching%20Coverage%20Revisit.md)
- [61 受控设计与阶段证据交接](https://github.com/Townzc/Obsidian-Vault/blob/6a041ca8398a1650fe77a68cc6b46d2ac8c937ef/交换课程/cs294-288/Papers/61%20-%20Final%20Sprint%20Controlled%20Design%20Handoff.md)

每篇区分原文证据、项目建议和待核实项；包含原始来源、具体版本、节表及读取范围。不声称逐页审完所有长附录。

## 3. 能实际改变复现决策的证据

| 原始证据 | 对执行的含义 | 不能自动推出 |
|---|---|---|
| OpenThinker3-1.5B官方configs.yaml：Qwen2.5-1.5B-Instruct/full/16K/7epochs/batch256/LR1.6e-4/cosine/warmup.1 | 有明确同规模配方；先锁默认值、dataset映射和评估命令 | 换成Base、LoRA、少量短链仍是精确复现 |
| OpenThoughts v2 H.1.3/Table17：同训练过滤条件报告55.0与82.2两种MATH500评分 | 先用公开检查点评估，再统一检查旧输出提取 | 我们27.2已被证明是parser错误 |
| R1-Distill-Qwen-1.5B从Qwen2.5-Math-1.5B起步；官方长上下文采样评估 | 适合评估正对照；必须区分模型身份与pass@1估计 | 可直接用83.9替换通用Base短协议分数 |
| Thinkless Table2单独报告warm-up：OT1M long83.60，原R1参照86.08 | 有独立SFT终点；下降未必全是bug；模板必须保留CoT | RL成绩是SFT收益；近零退化因此合理 |
| SmolLM2 §5/F/Table10固定学生比较数学来源 | 可构建同模型、跨题源的可解释比较 | 仅两个模型/任务组合即可识别家族因果作用 |
| OpenMathInstruct-2 matching coverage与§2.2.4 | 题目ID和每题响应数分别控制；库存实验与采购实验分层 | 等行数等于等采购费用或等训练FLOPs |

优先正式来源：OpenThoughts ICLR2026、OpenMathInstruct-2 ICLR2025、SmolLM2 COLM2025、Thinkless NeurIPS2025、DeepSeek-R1 Nature2025。OpenThoughts/SmolLM2本轮方法阅读采用明确arXiv版本；R1后续v2附录和官方小模型卡不冒充全部由原会议/期刊逐项审过。

## 4. 建议Claude/Codex接下来的决策材料

1. **复现锚点表：** 精确模型与tokenizer revision、数据文件/父题划分、序列化模板、完整推理/答案保留、mask/EOS、截断与packing、full/LoRA、优化器/LR/有效batch/训练剂量、评估协议。原配方与项目改动逐项对照。
2. **分开两种校准：** 发布检查点的原生评估复现不能证明训练代码正确；小规模训练成功也不能证明评分正确。先后或并行验证，但不要合为一个无范围PASS。
3. **最小交叉：** 同训练题池的两学生×两策略，各checkpoint评同两任务，是每seed四个学生；它检验模型条件与评测迁移，不识别训练题源效应。要识别后者，再做两学生×两训练题源×两策略，每seed八个。数量是设计建议，不是准入或成本承诺。
4. **保持三账：** B_proc为采购，T_train为学生训练，B_eval为测试时计算。公开库存没有失败历史时不伪造费用；P011同剂量扩量中的B是训练目标token，不是P008的教师采购预算。
5. **机制而非标签：** 关注新增可用监督率、真实策略多样性、学生学习斜率、题型覆盖及生成完成性；在保留设置检验解释。无差异不证明等价，单格大差异不证明可复用规律。

建议先交付可复核的健康锚点和差异清单，而不是必须在某日期出现正策略效应。用户的14/17/20/21–22/23/24里程碑由owner管理；这里没有创建提醒、会议或后台任务。

## 5. 与现有结果的边界

P011原扩量交接的3024题约三次呈现是精确曝光重复，不是三条不同解答。9072题单次呈现的自然greedy0/500及后续forced-answer改善需要检查完成性，但forced干预是额外生成，不能无声改写原主端点。[项目快照](https://github.com/Townzc/2P1R_Reasoning_Post/blob/ff30fafee7b3df3d230a1170eeb930188e8d8a2a/reports/p011_20261020/EXT3B_FINAL_MATERIAL_HANDOFF.md)

老师引用的27.2基线本轮未从原始运行重算；没有新模型结果、参数修改、重评分或全量数据下载。尚待补齐OpenThinker3-1.5B训练默认值/内部数据别名/确切Evalchemy命令，SmolLM2纯SFT终点与训练文件，以及各参考实现的完整输入绑定。对这些缺失项保持未核实，不以论文名替代证据。

## 原始入口

- [OpenThoughts v2](https://arxiv.org/pdf/2506.04178v2)，D/E/G.1/H.1.3；[1.5B配置](https://huggingface.co/open-thoughts/OpenThinker3-1.5B/blob/main/configs.yaml)。
- [DeepSeek-R1 Nature](https://www.nature.com/articles/s41586-025-09422-z)；[v2蒸馏附录](https://arxiv.org/pdf/2501.12948v2)，B.4.3/Table6/Table15。
- [SmolLM2 v1](https://arxiv.org/pdf/2502.02737v1)，§5/F；[官方评估固定提交](https://github.com/huggingface/smollm/blob/438be18dae658a638f3a6976fdf5190bb6d68619/text/evaluation/smollm2/README.md)。
- [Thinkless正式会议PDF](https://proceedings.neurips.cc/paper_files/paper/2025/file/de2ad3ed44ee4e675b3be42aa0b615d0-Paper-Conference.pdf)，§4.1/Table2/A.1/A.3；[SFT代码说明](https://github.com/VainF/Reasoning-SFT/blob/main/readme.md)。
- [OpenMathInstruct-2正式会议PDF](https://proceedings.iclr.cc/paper_files/paper/2025/file/302ce0673c00aee2cf84bb43d0117553-Paper-Conference.pdf)，§2及§2.2.4。
