# 审查：Tinker 轨与 LoRA 桥接格（Codex `f7d03b89`）

- 日期：2026-11-13（PST）
- 范围：修订 4 §2、§3 的两条新代码路径，按"首次正式运行前审查一次"执行
- 同批文件：`PRED_T_TRACK_AND_BRIDGE_v1.md`（修订 4 §5 的预测冻结）、`AUDIT_tier1_qwen_math_s17_AND_A5_PROPOSED.md`

## 结论

| 路径 | 结论 | 开跑条件 |
|---|---|---|
| Tinker 训练、NLL、生成（`tinker_lora.py`） | **通过** | 落实 §3 的 T-1、T-2 后直接开跑，不需复审 |
| 桥接格训练（`bridge_config.py`、`modal_bridge.py`） | **改两处后通过** | 落实 §4 的 B-1、B-2 后直接开跑，不需复审 |
| 桥接格评测（`bridge_evaluation.py`） | **按现有写法会在加载适配器时报错** | B-2 落实后这个问题消失；首跑按 B-3 检查 |

## 1. 核对范围

- 代码：`tinker_lora.py`、`bridge_config.py`、`modal_bridge.py`、`bridge_evaluation.py`、`modal_bridge_evaluation.py`、`termination_summary.py` 全文。
- 证据：三个 smoke 压缩包（sha256 与清单一致），逐个读了请求、渲染样例、逐步 loss、行顺序、20 条原始生成。
- 外部来源：
  - Tinker cookbook `8486b8df` 的 `hyperparam_utils.py`、`supervised/common.py`；
  - "LoRA Without Regret" 一文中的参数化方式；
  - vLLM `v0.11.0` 源码的 `vllm/lora/` 和 `models/qwen2.py`。
- 没能独立核对的部分：这个环境下载不到 Qwen3.5 的 tokenizer，所以"token id 与文本一一对应"我没有自己重算，依据是代码里的运行时断言（不一致就抛错）和压缩包里的解码文本。

## 2. Tinker 路径：逐项结果

| 项 | 结果 | 依据 |
|---|---|---|
| 数据 | 通过 | 读文件前核对 C6 的 sha256；训练直接用已包裹 OMI-2 提示词的 `problem` |
| 剂量 | 通过 | 行数与 `grid_dose` 核对；P、K8、K4、R 为 1,024 次更新，L 为 128 次；R 为 16 轮 |
| 行顺序 | 通过 | `ROW_ORDER.json` 是两个 0–511 的完整排列；第 1 步的 8 行等于顺序的前 8 个；三个模型顺序相同 |
| 调度 | 通过 | `cosine_lr` 在第 0 步取初值，最后一步之后到 0，与 HF 无 warmup 的 cosine 一致；smoke 用的是 128 步调度的前 20 步 |
| 学习率 | 通过 | 我按 cookbook 公式重算：5e-4 × (2000/2560)^0.0775 = 4.905e-4（4B）；5e-4 × (2000/4096)^0.0775 = 4.730e-4（9B、9B-Base）。与请求一致 |
| 渲染 | 通过 | 样例文本为 `<|im_start|>user\n{OMI-2 提示词}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n{解答}<|im_end|>`；三个模型的样例（含 token id）完全相同 |
| 损失掩码 | 通过 | 样例 1：前 60 个 token 权重为 0，后 182 个为 1，最后一个是 `<|im_end|>` |
| 损失归一化 | 通过 | 每步服务器返回的 `loss:sum` 与本地记录的 token 平均 loss 相等（60 步全部一致），说明"权重除以整批目标 token 数"实现了整批 token 平均 |
| 梯度裁剪 | 无影响 | 第 1 步之后的梯度范数为 0.12–0.30，裁剪阈值 1.0 不起作用；Adam 对 loss 的整体缩放不敏感，所以 cookbook 的学习率标定仍适用 |
| 训练是否在学 | 是 | 第 1 步 loss 0.69 / 0.67 / 0.50（4B / 9B / 9B-Base），第 11–20 步平均 0.39 / 0.37 / 0.37 |
| 生成提示词 | 通过 | 测试题只包裹一次 OMI-2 提示词；逐条断言与 HF `enable_thinking=False` 模板一致 |
| 解码与停止 | 通过 | greedy，`max_tokens` 4,096，停止符 248046（`<|im_end|>`）；60 条中 59 条正常停止，1 条（9B-Base）循环到 4,096 |
| 与现有评分的兼容 | 通过 | `MANIFEST.json`、`GENERATION_COMPLETE.json`、`raw.jsonl` 的字段满足 `scoring.py` 和 `termination_summary.py` 的读取；`text` 末尾带 `<|im_end|>`，不影响取最后一个 `\boxed{}` |
| NLL | 通过 | 用新建（未更新）的 LoRA 客户端做前向，按 0/1 权重求和；目标 token 含结束符，与 C7 的口径一致 |
| 费用 | 通过 | 每条训练序列约 410 token，与修订 4 的估计（420）一致；smoke 合计 $0.26 |

## 3. Tinker 路径：开跑前落实（不需复审）

**T-1 训练前测量直接复用 C7 的冻结输入。**

- `generate` 对没有 `messages` 的行会再包一次 OMI-2 提示词。C6 的 `holdout500.jsonl` 里 `problem` 已经包裹过，直接传入会包两次。
- 所以只允许两类输入：测试集原题（`problem` 为原题），和 C7 已冻结的会话文件（`{task}_baseline0/4.jsonl`、`{task}_holdout0/4.jsonl`，带 `messages`）。
- 在 `generate` 里加一条守卫：行内没有 `messages` 且 `problem` 以 OMI-2 提示词开头时抛错。
- 各模型的端点与 C7 相同：

| 端点 | 4B、9B | 9B-Base |
|---|---|---|
| NLL | `nll1000.jsonl` | `nll1000.jsonl` |
| greedy 基线 | `baseline4` 和 `baseline0` | `baseline4` |
| pass@8（8 次采样，T=0.7） | `holdout0` | `holdout4` |

**T-2 新文件里不要写本机绝对路径。** `TOKENIZER_ASSETS.json` 和三个请求文件里有本机用户目录的绝对路径。仓库规则要求公开仓库不含这类路径。以后新文件改用仓库相对路径；已提交的历史是否清理由负责人决定，不要强推。

**建议（不阻塞）：**

- T-3 并发与重试：现在固定 8 路并发，任何一次请求出错整批作废。建议把并发数做成请求字段（默认 32），对传输类错误允许每条最多重试 2 次并记录。greedy 加固定种子，重试不改变结果。先用第一个训练前端点量一下耗时再定并发数。
- T-4 pass@8 首跑时看一眼：8 次采样互不相同的题目比例。如果大多数题 8 条完全相同，说明 `num_samples` 没有独立采样，停下汇报。
- T-5 执行顺序：每个模型先跑 L、P、R，再跑 K8，最后 K4。前三格出来就能看 P − L 和 L − R。

## 4. 桥接格

**B-1（必须）`lora_alpha` 改为 32。**

- 现在用的是 LLaMA-Factory 的默认值 64（rank 的 2 倍），等效缩放为 2。
- Tinker 的学习率公式是在 α = 32、W′ = W + (α/r)·BA 的参数化下标定的；rank 32 时缩放为 1。cookbook 里 `get_lora_lr_over_full_finetune_lr` 的 `lora_alpha` 默认值也是 32。
- 桥接格的目的是在主网格的模型上复现 Tinker 的做法，α 应取 32。Tinker 服务端不公开 α，这一点按公开文档记录为"依据文档，未经服务端确认"。
- 同步修改 `verify_adapter` 里的 `lora_alpha` 检查和 `BRIDGE_CONFIG_CHECKS.json`。

**B-2（必须）目标层去掉 `lm_head`，只保留 7 类线性层。**

- 固定版本 vLLM 0.11.0 加载不了这个适配器：
  - `models/qwen2.py`：`tie_word_embeddings` 为真时 `self.lm_head = self.model.embed_tokens`，它是 `VocabParallelEmbedding`，不是 `LinearBase`；
  - `lora/utils.py::get_supported_lora_modules`：只收 `LinearBase` 的后缀和模型声明的 `embedding_modules`，而 `Qwen2ForCausalLM` 的 `embedding_modules` 是空的；
  - `lora/models.py::from_local_checkpoint`：safetensors 里出现不在支持列表里的模块名就抛 `ValueError`。
- 所以带 `lm_head` 的适配器会在第一次评测时报错，不会被静默忽略。审查包里"由 logits processor 处理输出头 LoRA"的说法对这个模型不成立。
- 两种改法里我选简单的：训练时不加 `lm_head`。理由：
  - 合并进绑定权重不安全（审查包自己已指出）；解绑后合并又要新写一条评测路径，并引入 bf16 取整的问题；
  - Qwen2.5-1.5B base 在训练前的 4-shot ChatML 下已经能输出 `<|im_end|>`（C7：MATH 60.6%、GSM8K 98.9% 的回答由结束符终止），注意力层和 MLP 层的 LoRA 足以学会终止。
- 这是与 Tinker（`train_unembed=True`）的一处已知差别，写进桥接格的 manifest。
- 预期可训练参数量：32 × 每层 41,216 × 28 层 = 36,929,536（hidden 1536，intermediate 8960，KV 输出 256）。以训练日志为准，对不上就停。

**B-3 首跑检查（先跑 L 格）。**

1. 训练日志里的可训练参数量与上面的数一致。
2. 评测前 20 题：带适配器的输出与不带适配器的 base 输出不同（确认 vLLM 确实加载了 LoRA），并记录结束符终止的比例。
3. L 格完整评测的截断率如果高于 25%，停下汇报（全量微调的 L 格是 10.1%）。高于这个数说明不训练输出头时模型学不会终止，需要改方案。
4. 建议（不阻塞）：取 8 道题，比较 vLLM + 适配器与 transformers + PEFT（不合并）的 greedy 前 32 个 token。

**其余部分通过：** 除 LoRA 字段外配置与主网格逐项相同；`H100!`；`save_strategy: no`；适配器文件清单与哈希校验；不合并。

## 5. 解读桥接格时要记住的一点

- 桥接格的 LoRA 学习率是 5.10e-4（Tinker 公式）。主网格全量微调用的是 1e-5（Li et al. 的配置），而 cookbook 的同一公式对这个模型给出的全量微调值是 5.1e-5。
- 按"LoRA 学习率约为全量微调的 10 倍"这条经验，与主网格 1e-5 对应的 LoRA 学习率约是 1e-4。桥接格比它高约 5 倍。
- 所以桥接格与主网格之间同时差了"方法"和"等效学习率"两件事。它能回答"Tinker 的做法在 1.5B 模型上给出什么模式"，不能单独回答"LoRA 本身有没有影响"。
- 如果桥接格与主网格的模式不同，再补 3 格（L、P、R，LoRA 学习率 1e-4）来拆开这两个因素，约 $2。现在不做。

## 6. 给 Codex 的清单

1. Tinker：落实 T-1、T-2，然后按修订 4 §2 开跑。顺序：三个模型的训练前测量 → 每个模型的 L、P、R → K8 → K4。训练后的输出在记录预测文件的提交号之前不评分。
2. 桥接格：落实 B-1、B-2，先跑 L 格并做 B-3，再跑其余四格。
3. 预测文件：`audit/claude/20261113b/PRED_T_TRACK_AND_BRIDGE_v1.md`，以包含它的 `claude/audit` 提交号为准。
