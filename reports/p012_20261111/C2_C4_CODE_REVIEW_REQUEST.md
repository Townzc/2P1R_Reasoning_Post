# P012 首轮审查：C2 共享评测路径、C4 配置

请 Claude 按 P012 v1 §12 对下列共享路径做首次使用前审查。同一路径的其他格沿用该审查；不恢复旧计划的逐格审计流程。当前尚无 P012 结果。

## 审查对象

- [`evaluation.py`](../../experiments/p012/evaluation.py)：固定提示词；生成参数；原始输入与输出 token；native EOS、字符串终止和长度上限分别记录；完整性和 SHA256；不覆盖已有输出。
- [`scoring.py`](../../experiments/p012/scoring.py)：按问题 ID 与 draw 合并；完整响应集合检查；Li 精确匹配与模型复核分别报告；OMI-2 用 math-verify / GSM 数值比较。
- [`vendor/li_math.py`](../../experiments/p012/vendor/li_math.py)：Li 发布脚本的 8 个纯函数逐字保留，来源和许可证同目录保存。
- [`training_config.py`](../../experiments/p012/training_config.py) 及 [三份 G0 YAML](candidate_configs/)：只生成标准 LLaMA-Factory 配置，没有自定义训练循环。
- 四个 `tests/test_p012_*.py`；当前代码 SHA 见 [SOURCE_BINDINGS.json](SOURCE_BINDINGS.json)。40 个不同测试已通过。G0 默认 seed 从初稿 17 校正为固定 Transformers 默认的 42 后，7 个配置测试再次通过。

本次范围是评测器、评分器和训练配置。Modal 启动器、实际 GPU 环境与费用预测尚未提交；本次审查不替它们作结论。C5/C6 数据构建和 C10 统计脚本后续各审一次。

## 需要固定的三个协议决定

### 1. G0 采用哪个公开协议

建议采用 Li 发布代码的逐任务提示词和评分方式；保留 `li_plan` 作为计划字面转述，禁止混用名称或分数。

| 项目 | v1 转述 | 固定发布代码 `1863f15a` | 候选实现 |
|---|---|---|---|
| MATH-500 提示 | `Final Answer: {your answer}` | `Final Answer: \boxed{your_answer}`，原文有句点 | `li_release_math500` |
| GSM8K 提示 | 同一段数学提示 | 只输入 `question`，再套 chat template | `li_release_gsm` |
| MATH 判分 | Final Answer 提取、精确匹配、LLM | 最后一个 boxed/fbox，发布版字符串规范化；只有已提取的错配进入 Qwen2.5-32B-Instruct | 原始纯函数；精确与 LLM 两列 |
| GSM8K 判分 | 未区分 | harness 的 `flexible-extract` 取最后一个数，再按 YAML 规则匹配；`math_metric_gsm8k.py` 直接读取该指标 | 单独实现该口径；不替换成 OMI-2 boxed 规则 |
| 输出与上下文 | 最多生成 16K | shell 同时设 context / generation 为 16000 | 候选为输出 16384、context 32768，完整保留输入；这是明确覆盖项 |

MATH 使用 Qwen2.5-32B-Instruct 的发布版判分提示、FP16、greedy、20 token、top-k 1；它的 revision 已固定。先写不可变原始生成，再写待判分队列；没有判完时 `accuracy_with_judge=null`，不会把精确匹配分冒充最终 Li 分。GSM8K 不额外套 MATH 的判分模型。

参考文件及 SHA 在 [REFERENCE_CONFIG_PROVENANCE.json](c1/REFERENCE_CONFIG_PROVENANCE.json)。当前候选配置尚未用于推理。

### 2. 官方锚点必须对齐 benchmark

Qwen2.5-1.5B base 的 35.0 / 68.5 是完整 MATH / GSM8K 的 4-shot 数字，不能给 MATH-500 0-shot 设相同门槛。Meta 没有 Llama-3.2 base 的这两项官方数字。建议 G0 表把 benchmark、few-shot、提示词、解码和评分器分列；优先使用 UWNSL 公开 SFT 检查点校准 Li 评测路径。

具体的 base 4-shot 示例和模板仍需绑定。选用标准 harness 时，应明确它与官方协议是否相同，再决定能否使用 ±3pp 门槛。这里不以一个新测数字反向选择协议。

### 3. Δ_SFT 的训练前分数

v1 把 G0 的标准 few-shot base 分数列作测试集基线，主网格却使用 OMI-2 chat 协议。直接相减会同时改变训练与提示格式。

建议：官方 few-shot 数字只用于校准；另为每个主网格初始化模型记录一次与 SFT 后完全相同的 OMI-2 模板、解码和评分基线，用它计算 Δ_SFT。共享未训练基线，不按每格重复生成。新增生成先纳入预算预测。请在任何 G0 / 主网格结果出现前确定此口径。

## 训练核对重点

- 公开 YAML：全参、bf16、LR 1e-5、cosine、2 epochs、per-device batch 2、accumulation 1；修订 1 用单卡 accumulation 4 复现 global batch 8。
- 复现配置保留 `val_size=0.01`、每 100 步验证、每 1000 步保存。主网格 `val_size=0`，避免丢掉已登记样本；另有题目级 500 题 holdout。
- 未注明项采用固定代码默认值：warmup 0、AdamW、weight decay 0、betas 0.9/0.999、epsilon 1e-8、clip 1.0、packing false、train_on_prompt false。G0 seed 42；主网格 17/29。
- 短链 cutoff 8192；R3 cutoff 16384。C4 运行前记录短、长链实际序列长度与超过 8192 的比例；不能把计划中的“短链无区别”当成已测结论。
- 单卡不使用发布版的 4 卡 ZeRO-3；实际显存、吞吐与训练长度尚未验证。训练与评测分别使用锁定环境。
- 主网格评测的 chat template 必须从固定训练模板导出并核对，不能直接假设 base 与 Instruct tokenizer 的默认模板相同。

已批准预算仍为 Modal $85，分项上限与 80% 预测规则不变。Tinker 不支持所需 3B 模型，M2 的 $40 分支未启动。费用与模型调用记录见 [EXECUTION_STATUS.json](EXECUTION_STATUS.json)。
