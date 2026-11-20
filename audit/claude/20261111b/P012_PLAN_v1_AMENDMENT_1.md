# P012 v1 修订 1（2026-11-11 21:40 PST，早于任何 P012 结果）

- **依据**：
  - GPT Pro 的 R1–R5 交接：`codex/icml-acl-2027` @ `80919cfc`，`audit/gpt_pro/20261111/R1_R5_EVIDENCE_HANDOFF.md`，以及 Obsidian 笔记 62–68。
  - 负责人 21:23 的问题：Llama 授权要等多久；能否先用 Tinker 额度做 3B 实验。
- **适用范围**：本修订覆盖 `audit/claude/20261111a/P012_PLAN_v1.md` 中与下文冲突的条目；其余不变。
- **冻结时点**：写这份修订时还没有任何 P012 结果。

## M1 Llama 访问：不等待

- Meta 对 Llama 3.2 的访问申请是人工审批，可能几分钟就批，也可能要几天，偶尔会被拒。
- 先跑不依赖 Llama 的部分：G0 中 Qwen 的那几项，以及 Qwen 的 4 个设定。
- 如果到 **11/12 09:00 PST** 还没批下来，改用无门槛的镜像：
  - Instruct：`positron-ai/Llama-3.2-1B-Instruct`。该仓库声明与官方提交 `e9f8effb…` 逐字节一致，并列出了各文件的 SHA256；
  - base：`unsloth/Llama-3.2-1B`。
- Codex 要做的事：
  - 记录镜像的 repo、revision 和每个文件的 sha256，与镜像声明的上游 SHA256 逐一对照；
  - 拿到官方权限后再核对一次。sha256 一致就不重跑；不一致则停下汇报。
- 负责人已在 Hugging Face 上接受 Llama 3.2 社区许可。镜像属于按该许可的再分发，使用时照常标注 "Built with Llama"。

## M2 Tinker 上能不能跑 3B：今晚查清

- 运行 `ServiceClient().get_server_capabilities()`，列出 Tinker 当前支持的模型，结果写进 C1 的清单。
- **如果列表里有 Llama-3.2-3B 或 Llama-3.2-3B-Instruct**，用 Tinker 额度另开一条 LoRA 轨道（上限 $40，从 Tinker 的 E4 额度中划出）：
  - 用 Li et al. 的短链数据复现 Llama-3.2-3B-Instruct 那一格（论文值 50.9 / 77.5）。LoRA rank 64，LR 1e-4（即 Li et al. 的 LoRA 学习率），其余配置同 Li et al.；
  - 跑 E1 里 Llama-3.2-3B 的四格（P、K8、R、L），只做 MATH。base 和 Instruct 中，Tinker 上有哪个就做哪个。
  - 这条轨道的全部结果都单独标注为 **LoRA / Tinker**，不与 Modal 上的全参网格合并做统计，只作为外部参照点。E1 中对应的 Modal 部分取消。
- **如果列表里没有**：E1 仍按 v1 执行（在 Modal 上，用结余来跑）。
- Tinker 上没有 Qwen2.5 系列模型。主网格里的 Qwen 设定只能在 Modal 上跑。

## M3 Li et al. 配置细节（R1）

- **有效 batch = 8**。公开 YAML 是每卡 2、梯度累积 1；按 4 卡推得全局 batch 8。我们在单卡上用梯度累积复现全局 batch 8。主网格也用 8：P、K8、K4、R 各 1,024 步，L 为 128 步。
- **packing 关闭，train_on_prompt 关闭**（公开 YAML 的默认值）。
- **最大长度**：论文写 16,384，公开 YAML 是 8,192。
  - 短链在两种设置下没有区别；
  - R3（长链）按论文用 16,384，并报告超过 8,192 token 的样本占多少。
- 其他论文里没写明的项（如 warmup）按公开 YAML（`Small-Model-Gap/Small-Model-Learnability-Gap` @ `1863f15a`）取值；YAML 也没写的，用所固定 LLaMA-Factory 版本的默认值。全部写进 manifest。

## M4 基线锚点更正（R2）

| 项目 | 更正内容 |
|---|---|
| Qwen2.5-1.5B base 官方值 | MATH 35.0、GSM8K **68.5**，都是 4-shot。草案和 v1 把 GSM8K 写成 62.0，是错的 |
| Llama-3.2 base | Meta 官方表里没有 MATH 和 GSM8K。G0-E 对 Llama base 只报告标准协议下测到的数字，不设"与官方差 ≤ 3pp"的门槛 |
| Li et al. 图 5 | 画的是两种 SFT 配方之间的差值，不是 base 模型的绝对分数，不能当锚点 |
| UWNSL 公开资源 | 6 个数据集、24 个模型条目。G0-E 第 3 项（直接评测公开的 SFT 模型）照做 |

## M5 统计功效（R5）

- **问题**：MATH-500 上做配对比较，若 discordance 为 20%、要求 80% 功效，最小可检测差（MDE）约 5.6pp。v1 定的 3pp"明显"标准基本测不出来。
- **改动**：
  1. MATH 的主指标改为**完整 MATH test（5,000 题）的 greedy 准确率**。MATH-500 是其中的子集，照常报告，便于和文献对照。按同样的近似估算，MDE 约 1.8pp。
  2. §4 的去污染改为对照完整的 MATH test 5,000 题（不再只对照 MATH-500）。OMI-2 题池只保留 MATH train 里的题。
  3. 4 次采样取平均的次要指标只在 MATH-500 和完整的 GSM8K test 上做。
  4. GSM8K test 只有 1,319 题，MDE 约 4pp。判读时要写明这一点。
- **费用**：MATH 每格多生成约 175 万 token，每个 MATH 设定多花约 $0.5。从 Tier 1 和 Tier 2 的上限里出，总上限 $85 不变。

## M6 结论边界（R3、R5）

- 主网格是在**固定训练算力**下，改变**现成数据库存**的组成，不是在比较"采购数据的成本"。
- 报告中不能写成"同样多的钱，买题比买解更划算"一类的结论。采购成本的问题留给后续工作。

## M7 不变的部分

时间线、预算总额、对比定义、H0–H3，以及"明显"的判定标准（3pp，且 CI 不含 0，且两个种子方向一致）都不变。
