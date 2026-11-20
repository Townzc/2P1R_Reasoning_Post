# P012 —— 期末前实验：执行计划 v1（负责人已确认）

- **起草**：Claude（审计方）。
- **执行**：Codex，分支 `codex/icml-acl-2027`；交付位置 `reports/p012_20261111/`。
- **文献**：GPT Pro（§8.2 的 R1–R5）。
- **审计结果**：Claude 写在 `audit/claude/202611*/`（`claude/audit` 分支）。
- **取代**：草稿 v0（claude.ai 项目文档 `claude/P012_plan_draft_20261111.md`）。草稿里的背景回顾仍然有效，本文件是执行版本。
- **性质**：探索性计划。以下内容在看到任何 P012 结果之前随本 commit 冻结：§5 的对比定义与"明显"标准、§5.3 的预测 H0–H3、§9 的预算。
- **课程**：报告和展示里的解释、总结、分析文字，全部由负责人本人撰写。本文件和所有审计文档里的句子不进入任何课程交付物。

## 负责人决定（2026-11-11 16:15 PST，claude.ai 对话）

1. **算力**：Modal 余额约 **$89**；Tinker 额度 **$750**（课程老师提供）。
2. **第二个模型族用 Llama-3.2。** 负责人当晚在 Hugging Face 上接受 Llama 3.2 许可。
3. **base 与 Instruct 都进主网格。**
4. **基础设施故障允许自动重试 1 次。** 包括平台抢占、容器启动失败、网络中断这类非科学原因，重试要记录。科学性失败不重试。
5. **长链只做 R3 诊断**（草案默认，负责人未提异议）。

## 相对草案的改动（Claude 按预算作出，负责人知悉）

1. **主网格的教师解改用 OpenMathInstruct-2（OMI-2，ICLR 2025）里原始 MATH / GSM8K 训练题的现成解**，教师是 Llama-3.1-405B-Instruct。不再自己用 Qwen2.5-32B-Instruct 生成。
   - **原因**：
     - 自己生成要花约 $20–35 的 Modal 费用，超过余额的三分之一。
     - OMI-2 对每道 MATH 原题采样 512 次、每道 GSM8K 原题采样 64 次，并且只保留正确解（通常是答案正确的解），足够构造 K ≤ 8 的网格。
     - 它是口碑好的公开 SFT 数据集。
     - 论文本身报告了"独立题目数从 1K 增加到 6.5K，MATH 验证集提升 10.5%"（学生为 Llama-3.1-8B），可以作为 Δ_PK 的文献锚点。
   - **代价**：
     - 教师属于 Llama 家族，可能对 Llama 学生更"好学"。用 §5.4 的 NLL 量化这一点，并在报告里讨论。
     - 主网格的提示词和答案格式（`\boxed{}`）与 G0 所用的 Li et al.（"Final Answer:"）不同。G0 验证的是训练配方和评测流水线；主网格内部格式统一。
   - **后备**：如果 OMI-2 原题里"至少有 8 条不同解"的题少于 4,596 道，改在 Tinker 上用 Qwen3-8B（非思考模式）生成，费用从 Tinker 额度出，并在报告中披露。
2. **预算按 Modal $89 重排（§9）。** 每个"学生 × 任务 × 种子"放进一个容器，依次训练 5 个格并就地评测，摊薄启动开销；选能放下模型的最便宜 GPU。
3. **Tinker 的用途。** Tinker 当前的模型里很可能没有 ≤3B 的模型，所以主网格全部在 Modal 上跑。Tinker 额度用于：
   - 确认它当前支持哪些模型；
   - OMI-2 不够用时作为后备教师生成；
   - 可选的高能力外推点（E4，LoRA，单独标注）。

---

## 1. 背景与动机（简）

期中评审有两条要求：

- 基线数字和实验设定必须可信，最好照搬口碑好的参考论文；
- 用受控的交叉设计说明分配**何时**重要、**如何**重要，并且结论要能超出个别设定。

旧结果里两个现象需要先解释清楚：

- **(a) Qwen2.5-1.5B base 在 MATH-500 上 0-shot 只有 27.2%。**
  - 原因是自定义提示词，加上 1024 token 上限（500 题里 68 题被截断判错），加上严格的解析器。
  - OLMo 的 base 分数（GSM8K 12.6%，546 题截断；MATH 0.2%）是同一类格式失败。
  - 这些都不再作为基线报告。
- **(b) P011 的长链 SFT 让 Qwen2.5-1.5B-Instruct 从 50.4% 降到 10–34%。**
  - 主因是终止失败（termination failure）：原生 EOS 比例从 98.5% 降到 22.6–59.5%；强制作答后正确率回到 41–47%。
  - 训练配方也与 OpenThoughts 差别很大，详见草案 §2.3。
  - 基线评测本身没问题：我们测得 50.35%，OpenThoughts 报告 50.2%。

旧数据里，"模型族 × 任务"四个格其实都有：

| ΔP（n400 → n3200，固定训练量） | GSM8K | MATH |
|---|---|---|
| Qwen2.5-1.5B base | +1.0 | +0.6 / +4.4 / +4.4（三个教师） |
| OLMo-2-1B base | +11.0 | +5.4 |

表面上看，模型族的影响大于任务。但四个格用的教师不同、OLMo 的评测有问题、而且只有单个种子，所以这只能当作待检验的假设。

## 2. 参考设定（照搬对象）

### 2.1 主锚点：Li et al. 2025, *Small Models Struggle to Learn from Strong Reasoners*（Findings of ACL 2025）

- **训练数据**：MATH 训练集 7,500 题；短链来自 Qwen2.5-32B-Instruct，长链来自 QwQ-32B-Preview；拒绝采样。
- **训练**：LLaMA-Factory；14B 以下全参微调；LR 1e-5，cosine，2 epochs，AdamW；最大长度 16,384；每卡 batch 2 × 4 卡（梯度累积待核）。
- **评测**：0-shot，greedy，最多生成 16K token。提示词："Solve the following math problem and present the final answer in the format: Final Answer: {your answer}\nProblem: {problem}\nAnswer:"。先精确匹配，不匹配再由 Qwen-32B-Instruct 判。
- **公开数据**：Hugging Face 组织 UWNSL，例如 `UWNSL/MATH_training_split_long_cot`。短链数据集和 SFT 模型的确切名字由 R1 和 C1 查清。

可对照的数字（MATH / GSM8K）：

| 学生 | 长链 | 短链 |
|---|---|---|
| Qwen2.5-1.5B-Instruct | 41.6 / 63.8 | 52.3 / 71.7 |
| Llama-3.2-1B-Instruct | 28.6 / 42.3 | 33.4 / 49.2 |

### 2.2 主网格数据：OpenMathInstruct-2（Toshniwal et al., ICLR 2025）

- 只取 `problem_source ∈ {math, gsm8k}` 的行，也就是原始训练题的解，不用 augmented 题。
- 提示词和答案格式沿用 OMI-2 / OpenMath2 模型卡（C1 核对原文）。

### 2.3 基线锚点

| 模型 | 数字 | 出处 / 协议 | 状态 |
|---|---|---|---|
| Llama-3.2-1B-Instruct | MATH 30.6（0-shot CoT），GSM8K 44.4（8-shot CoT） | Meta 模型卡 | 已核 |
| Qwen2.5-1.5B-Instruct | MATH500 50.2 | OpenThinker3-1.5B 模型卡，Evalchemy，T=0.7 | 已核 |
| Qwen2.5-1.5B-Instruct | MATH 55.2，GSM8K 73.2 | Qwen2.5 技术报告 | 待 R2 核对 |
| Qwen2.5-1.5B base | MATH 35.0（4-shot），GSM8K 62.0（4-shot） | Qwen2.5 技术报告 | 待 R2 核对 |
| Llama-3.2-1B base | 待查 | — | R2 |

## 3. G0 复现门槛（11/12–11/13）

**G0-E：只评测，不训练**

1. Qwen2.5-1.5B-Instruct 和 Llama-3.2-1B-Instruct 用 Li et al. 的协议，测 MATH-500 和 GSM8K。
2. Qwen2.5-1.5B base 和 Llama-3.2-1B base 用标准 few-shot 协议（lm-evaluation-harness，或与 R2 查到的官方协议一致），对照官方 base 数字。
3. 如果 UWNSL 公开了 SFT 后的模型，直接评测，对照 Li et al. 表 8。这一步能把"评测是否正确"和"训练是否正确"分开。

| 对象 | 允许差距 |
|---|---|
| Instruct 与官方数字 | ≤ 3pp；协议不同时 ≤ 4pp，并写明原因 |
| base few-shot 与官方数字 | ≤ 3pp |
| UWNSL 的 SFT 模型与表 8 | ≤ 2pp |

**G0-T：训练复现**（数据、超参、评测与 Li et al. 逐项一致）

| 编号 | 学生 | 数据 | 目标（MATH500 / GSM8K） | 允许差距 |
|---|---|---|---|---|
| R1 | Qwen2.5-1.5B-Instruct | UWNSL 短链 | 52.3 / 71.7 | ≤ 3pp |
| R2 | Llama-3.2-1B-Instruct | UWNSL 短链 | 33.4 / 49.2 | ≤ 3pp |
| R3 | Qwen2.5-1.5B-Instruct | UWNSL 长链 | 41.6 / 63.8，另报 EOS 与截断比例 | ≤ 4pp |

- **短链数据没有公开时**：R1、R2 取消，G0-T 只做 R3。G0-E 的第 3 项（评测 UWNSL 公开的 SFT 模型）因此变为必做。
- **不通过时**：先查模板、有效 batch、EOS 和评分器，主网格暂缓。11/13 晚仍不通过就汇报，由负责人决定是否带着已知差距继续，并在报告里写明。

## 4. 主网格数据（OMI-2）

1. **过滤**：保留 OMI-2 中 `problem_source` 为 `math` 和 `gsm8k` 的行，按题目文本（NFKC 规范化，去掉首尾空白）归组。
2. **去污染**：
   - MATH 题与 MATH-500 做精确匹配和 13-gram 检查；
   - GSM8K 题与 GSM8K test 做同样检查；
   - 命中的题剔除，并报告数量。
   - 如果 OMI-2 的 MATH 原题里包含 MATH test 中 MATH-500 以外的题，可以保留，但要报告。
3. **可用解**：
   - 能取出 `\boxed{}`，且与 `expected_answer` 判等价（math-verify 或数值比较）；
   - 题内规范化后精确去重；
   - 学生分词后总长不超过 4,096 token。
4. **题池**：每个任务只收"至少有 8 条不同可用解"的题，每个池至少需要 4,596 题（4,096 + 500）。少于此数就触发后备（见"相对草案的改动"第 1 条）。
5. **嵌套抽样**（每个任务各做一次）：
   - 题池按 `Random(20261111)` 打乱（输入先按题目键排序）；
   - 前 500 题作为留出题，只用于 §5.4；
   - 之后依次取前 512、1,024、4,096 题；
   - 每题的不同解按 `sha256(题目键 + 'p012')` 生成的 seed 打乱，取前 K 条。
6. **选择偏差**：题池去掉了教师解太少的题，所有格受同样影响。报告去掉的比例，以及池内外的难度分布（MATH 用 level；GSM8K 用解的长度作代理）。

## 5. 主实验（Tier 1 与 Tier 2）

### 5.1 因素：8 个设定，完全交叉

| 因素 | 水平 |
|---|---|
| 模型族 | Qwen2.5-1.5B、Llama-3.2-1B |
| 阶段 | base、Instruct |
| 任务 | MATH（评测 MATH-500）、GSM8K（评测 GSM8K test 1,319 题） |

### 5.2 每个设定的 5 个格

训练算力单位是"样本呈现次数"；C = 8,192，即 4,096 条 × 2 轮。

| 格 | (P 题数, K 每题解数) | 轮数 | 算力 | 含义 |
|---|---|---|---|---|
| P | (4096, 1) | 2 | C | 更多题（Problems） |
| K8 | (512, 8) | 2 | C | 更多解（Paths） |
| K4 | (1024, 4) | 2 | C | 中间点 |
| R | (512, 1) | 16 | C | 重复（Repeats） |
| L | (512, 1) | 2 | C/8 | 低预算对照 |

- **嵌套**：L、R 与 K8 用同一批 512 题；K8 中每题的第一条解就是 L、R 用的那条。
- **训练配方**：与 Li et al. 相同，只改数据组成和轮数。全参，bf16，LLaMA-Factory 固定版本；模板为 Qwen 族用 `qwen`、Llama 族用 `llama3`，base 与 Instruct 用同一个模板。
  - 有效 batch 和 warmup 与 Li et al. 一致（由 R1、C4 核对）；每个格按自己的总步数做 cosine 衰减。
  - Llama-3 base 的对话特殊 token 可能没有训练过；全参微调会更新 embedding，但 SFT 后必须检查 EOS 比例。
- **种子**：Tier 1 用 seed 17。Tier 2 用 seed 29，跑 P、K8、R、L 四格（K4 视预算）。

### 5.3 预先登记的对比和预测

| 记号 | 定义 | 问题 |
|---|---|---|
| Δ_SFT | P − 训练前 | SFT 在这个设定里有没有用 |
| Δ_data | P − L | 数据变多有没有用（前提检查） |
| Δ_PR | P − R | 同等算力下：更多题 vs 重复 |
| Δ_PK | P − K8 | 同等算力、同等条数下：更多题 vs 更多解 |
| Δ_KR | K8 − R | 同一批题、同等算力下：不同的解 vs 重复同一条解 |

- **"明显"**：|Δ| ≥ 3pp，题目层面配对 bootstrap 的 95% CI 不含 0，并且两个种子方向一致。Tier 1 只做单种子的描述；判定在 Tier 2 之后进行。
- **H0**：Instruct 学生的 Δ_SFT 小于同族 base 学生。
- **H1**：Δ_data 与训练前能力（§5.4）负相关，在 8 个设定上 Spearman ρ < 0。能力最低的设定可能因为"学不动"而增益也小，所以事先允许倒 U 形。
- **H2**：
  - 在 Δ_data 明显的设定里，Δ_PR > 0 且 Δ_PK ≥ 0；
  - 在 Δ_data 不明显的设定里，三种花法之间的差都 < 2pp。
- **H3**：Δ_KR > 0 只出现在 Δ_data 明显的设定里。
- 上述预测可能是错的。无论结果如何，全部对比都完整报告。

### 5.4 训练前能力（不训练，每个"学生 × 任务"测一次）

1. **训练分布上的 pass@1 和 pass@8**：
   - 用 500 道留出题，T=0.7，OMI-2 的提示词；
   - Instruct 用 0-shot；base 用 4-shot，4 个示例从题池外另取并固定。
2. **学生对教师解的平均每 token NLL**：用留出题里 1,000 条 OMI-2 解。
3. **测试集上的标准基线**：即 G0-E 的结果。

## 6. 扩展（按预算取舍）

- **E1 先预测、后验证**（Modal；11/15 按实测费用决定是否做）：
  - 先用 Tier 1 拟合一个简单规则，在运行前写下对新设定的预测并提交；
  - 然后跑 Qwen2.5-0.5B（base 与 Instruct）、Llama-3.2-3B base、Qwen2.5-3B base 中预算允许的部分，每个跑 2 个任务 × P、K8、R、L 四格。
- **E2 教师强度**（Modal，约 $3）：
  - 用 Qwen2.5-Math-1.5B-Instruct（即期中的 T1.5）为主网格 P 格的 4,096 道 MATH 题各生成 1 条可用解，最多尝试 4 次。4 次内都没有可用解的题，用第 1 次的输出并报告数量（沿用 P010 规则）；
  - 在 Qwen-1.5B base × MATH、Llama-1B base × MATH 两个设定上训练 P 格；
  - 与 OMI-2（405B 教师）的 P 格对比，检验"强教师更差"是否只出现在 learning 区；
  - 对照 Li et al. 表 7。
- **E4 高能力外推点**（Tinker，LoRA，可选，11/17 OH 之后决定）：
  - 用 Tinker 当前支持的 base 模型（如 Qwen3.5-9B-Base，以 C1 查到的为准）跑 MATH × P、K8、R、L 四格；
  - 结果单独标注为 LoRA / Tinker，只作为外部有效性的参考点，不并入主网格统计。
- **长链分配小网格**：本轮不做。Tinker 跑不了 1.5B 模型，Modal 预算也不够。

## 7. 评测与统计

- **G0**：完全使用 Li et al. 的协议（16K 上限，greedy，"Final Answer:" 提取）；复现格另外跑一遍 LLM 判分，报告两种口径的差。
- **主网格**：
  - OMI-2 提示词，chat 模板与训练一致；
  - greedy，16K 上限；
  - 另做 4 次采样（T=0.7，top-p 1.0）取平均，作为次要指标；
  - 答案取最后一个 `\boxed{}`，用 math-verify 判等价；GSM8K 做数值比较。
- **每次运行自动记录**：训练 loss 曲线、EOS 比例、截断比例、平均长度、格式合规率、token 数、步数、费用。
- **统计**：
  - 题目层面配对 bootstrap，10,000 次，seed 20261111；
  - 两个种子分别报告，并给出均值；
  - 跨设定用 Spearman 相关和散点图。

## 8. 分工与任务

| 角色 | 本阶段职责 |
|---|---|
| 负责人 | 接受 Llama 许可；管理算力账户；亲自撰写 11/14 的 Slack 讨论和 11/17 的 OH 问题；完成全部课程写作 |
| Codex | §8.1 |
| GPT Pro | §8.2，笔记照旧写进 Obsidian `交换课程/cs294-288/Papers` |
| Claude | 每条新代码路径首次运行前做一次代码审查；判定 G0；每批抽 10% 原始输出独立重新评分；头条数字冻结前全量复核；E1 的预测在运行前写好；提供中文分析和由代码生成的图 |

### 8.1 Codex 任务

| 编号 | 任务 | 验收 |
|---|---|---|
| C1 | **环境与清单**：固定 LLaMA-Factory、vLLM、math-verify、lm-evaluation-harness 的版本；用负责人的 HF token 确认能访问 Llama-3.2-1B/1B-Instruct（以及 3B）；下载 Qwen2.5-1.5B/-Instruct 和 UWNSL 数据；列出 UWNSL 的数据集与模型清单；核对 OMI-2 的提示词原文；用 Tinker API 列出当前支持的模型 | manifest 写明版本与 sha；清单写入交付目录 |
| C2 | **评测器**：Li et al. 协议（"Final Answer:"）和 OMI-2 协议（`\boxed{}`）；greedy 与采样；EOS、截断统计；原始 token 落盘 | 20 条手工样例全部通过；Claude 代码审查通过 |
| C3 | G0-E | 输出与官方数字的对照表 |
| C4 | G0-T（R1–R3）：LLaMA-Factory 配置与 Li et al. 逐项对齐，配置文件入库 | 输出与表 8 的对照表 |
| C5 | OMI-2 题池（§4 第 1–4 条） | 两个任务各自的池大小、可用解数分布、去污染命中数、长度分布 |
| C6 | 主网格数据（§4 第 5–6 条） | 自动检查嵌套关系、每格条数、同等算力；token 数入 manifest |
| C7 | 训练前能力测量（§5.4） | — |
| C8 | 主网格：每个"学生 × 任务 × 种子"一个容器。第一个设定（Qwen-1.5B base × MATH）兼作费用探针，跑完后先报告实测费用和全网格预测，再放开其余设定；顺序为先 MATH 后 GSM8K | 每批运行前给出费用预测 |
| C9 | E2：小教师生成 + 2 次训练 | — |
| C10 | 分析脚本：结果总表、bootstrap、Δ 表、散点图。只出图和表，不写任何解读 | 脚本确定性、可重跑 |

### 8.2 GPT Pro 任务

- **R1 参考配置核对**：
  - Li et al.：附录 A 的表 5、表 6（有效 batch、梯度累积、warmup、chat 模板、是否打包）；评测脚本与判分模型；数据生成提示词；UWNSL 公开的数据集与模型；3.4 节 base 学生的数字。
  - OMI-2：原题解的数量与过滤规则；训练和评测所用的提示词。
- **R2 官方基线表**：
  - Qwen2.5-0.5B/1.5B/3B，以及 Llama-3.2-1B/3B 的 base 与 Instruct，在 MATH 和 GSM8K 上的分数，并写明协议；
  - 常用论文中 Qwen2.5-1.5B base 在 MATH-500 上的 0-shot 数字与所用模板。
- **R3 分配文献矩阵**：
  - 覆盖 OpenThoughts（1×/4×/16× 是否在固定条数下进行）、OMI-2（题目多样性消融）、AceReason-Nemotron 1.1（题数 vs 每题回答数）、Yuan et al. 2023（推理路径数）、DART-Math、Bansal et al.；
  - 每篇写清：学生规模、是否控制同等算力、结论，以及与 H0–H3 的关系。
- **R4 SFT 是"激发"还是"学习"**：LIMA 与表面对齐假说（superficial alignment），Li et al. 关于 base 与 Instruct 的结论；找支持或反驳"训练前能力决定数据边际收益"的证据。
- **R5 评审视角**：领域专家会对 §5 的设计提出哪些质疑（混淆、统计功效、可推广性）。

## 9. 预算

**Modal：本轮硬上限 $85，另外至少保留 $4 不动。**

| 子项 | 估计 | 上限 |
|---|---:|---:|
| G0-E 评测 | $2–4 | $4 |
| G0-T：R1–R3（R3 长链约占一半） | $5–9 | $10 |
| 训练前能力测量 | $2–3 | $4 |
| Tier 1（8 个设定 × 5 格，seed 17） | $15–30 | $30 |
| Tier 2（8 个设定 × 4–5 格，seed 29） | $12–25 | $22 |
| E2 | $2–3 | $3 |
| 应急（基础设施重试、调试） | — | $12 |
| **合计** | | **$85** |

- **E1** 只能用 Tier 1 和 Tier 2 的实际结余来做，11/15 按实测决定。
- **规则**：
  - 每批启动前按"实测单价 × 剩余数量"预测费用，预测超过所在子项上限剩余额度的 80% 就不启动，先汇报；
  - 各子项之间不得挪用；
  - 账单有延迟，计算时把未结算的预留额度一并算上。
- **Tinker（$750）**：
  - C1 查模型列表，$0；
  - OMI-2 后备生成，上限 $60，只在后备触发时使用；
  - E4，上限 $80，OH 之后决定；
  - 其余（不少于 $500）留给汇报后的工作和投稿扩展。
- **削减顺序**（先砍第 1 项）：
  1. E4；
  2. E1；
  3. Tier 2 的 K4；
  4. E2。
- **不可砍**：G0（R3 和 G0-E 核心）、Tier 1 全部 40 格、Tier 2 的 P、K8、R、L。

## 10. 时间线（PST）

| 日期 | Codex | Claude | 负责人 |
|---|---|---|---|
| 11/11 周三晚 | C1；开始写 C2 | 本计划 | 接受 Llama 许可 |
| 11/12 周四 | 上午 C3；下午 C4（R1–R3）；C5、C6 用 CPU 并行 | 审 C2 和训练配置的代码；判定 G0-E | — |
| 11/13 周五 | 上午先跑 C8 的费用探针，再跑 MATH 的其余 3 个设定；晚上跑 GSM8K 的 4 个设定；C7 | 判定 G0；审数据构建的代码；抽查评分 | — |
| 11/14 周六 | MATH 结果中午前出，GSM8K 晚上出 | 中文要点和图 | 亲自撰写 Slack 讨论 |
| 11/15–16 | Tier 2；E2 | 分析 v1；决定 E1 | 准备 OH |
| 11/17 周二 | — | 按 OH 意见出 v2 | **OH** |
| 11/18–20 | E1 或 E4（如果做） | 在运行前冻结 E1 的预测 | — |
| 11/20 周五 22:00 | **主结果冻结** | 头条数字全量复核 | — |
| 11/21–22 | 小型补充实验 | 只出图和表 | 做幻灯片 |
| 11/23–24 | — | — | 预讲；**汇报** |
| 11/25–12/6 | 剩余工作 | 数字复核 | — |
| 12/7–12/14 | — | 只核数字和图 | 写报告（COLM 模板，≤ 8 页） |

## 11. 立即汇报的触发条件

- G0 的任何一项不通过，或 UWNSL 的数据或模型拿不到；
- Llama-3.2 到 11/12 中午仍无访问权限（备选方案：OLMo-2-0425-1B）；
- OMI-2 题池少于 4,596 题，或去污染命中数异常；
- 任何设定的 Δ_SFT ≤ 0（SFT 没有用）；
- 短链训练后 EOS 比例低于 90%；
- 费用预测超过任何子项上限的 80%；
- 任何结果显示"更多数据或更多算力没有提升"（负责人的既定要求）。

## 12. 流程规则（相对 P009–P011 大幅精简）

- 只用固定版本的标准工具：LLaMA-Factory、vLLM、math-verify、lm-evaluation-harness。不写自定义训练循环。
- 每批运行对应一个 manifest，内容为配置、数据 sha 和代码 commit。不用 RunGuard、claim/receipt 或逐格的多轮审计。
- 每条新代码路径（评测器、训练配置与启动器、数据构建、分析脚本）在首次运行前由 Claude 审查一次。同一路径的其他格不再逐格审。
- 结果审计：每批抽 10% 原始输出独立重新评分；冻结前对头条数字全量重新评分，并重算 bootstrap。
- 基础设施故障自动重试 1 次并记录；科学性失败不重试。
- 不设会杀掉运行的硬计时器，只做费用预测和提醒。
- 公开仓库里不放私人通信、个人信息和凭据。Codex 不对外发送消息。
- 照旧维护 `AI_USE_LOG.md`。

## 13. 来源

- [Li et al. 2025, Small Models Struggle to Learn from Strong Reasoners（Findings of ACL 2025）](https://preview.aclanthology.org/eacl-dois/2025.findings-acl.1301)；[arXiv v3](https://arxiv.org/html/2502.12143v3)
- [Toshniwal et al. 2025, OpenMathInstruct-2（ICLR 2025）](https://proceedings.iclr.cc/paper_files/paper/2025/file/302ce0673c00aee2cf84bb43d0117553-Paper-Conference.pdf)；[数据集说明](https://www.huggingface.co/datasets/nvidia/OpenMathInstruct-2/blame/main/README.md)；[生成流程（NeMo-Skills）](https://nvidia.github.io/NeMo-Skills/openmathinstruct2/dataset)
- [Guha et al. 2025, OpenThoughts](https://arxiv.org/html/2506.04178v2)；[OpenThinker3-1.5B 模型卡](https://huggingface.co/open-thoughts/OpenThinker3-1.5B)
- [Llama 3.2 Instruct 基准（Meta 模型卡转载）](https://build.nvidia.com/meta/llama-3.2-3b-instruct/modelcard)
- [Qwen2.5 Technical Report](https://arxiv.org/pdf/2412.15115)
- [Tinker 定价页](https://thinkingmachines.ai/tinker/pricing/)；[Tinker 模型列表（文档页）](https://tinker-docs.thinkingmachines.ai/model-lineup)
- 仓库冻结结果：`reports/p010_20261019/midpoint_freeze_20261021_1200PDT_v1/`、`reports/p011_20261020/final_numeric_freeze_20261022_0500UTC_v1/`
