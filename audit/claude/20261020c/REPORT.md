# P010 审计 20261020c：C4/C5 学生运行时 A2（T1.5 K4/K8）——PASS

- **审计方**：Claude
- **时间**：2026-10-20 04:40 UTC
- **审计对象**：`codex/icml-acl-2027` @ `d51b4f74`
- **主要文件哈希**：
  - `student_runtime_v1/SPEC.json`：SHA-256 `753cbafbe895b1f1…`
  - `experiments/p010/student_training.py`：`d8f8ef8ce0817ef8…`

## 检查项与结果

| 检查项 | 结果 |
|---|---|
| A2 输入与已通过 A1 的输入是否一致 | 一致。`actual_inputs.tar.gz` 中 K4/K8 的 encoded、plan、rows 三个文件，与 A1 审计过的 `selected_inputs.tar.gz` **逐字节相同**（SHA 完全一致） |
| 训练函数是否与 P009 一致 | 一致。`student_training.train_and_merge` 与 P009 `stage1_training_core.train_and_merge` 的 **AST 相同**。多答案支持只出现在模块级的配方检查，并且使用了 A1 中审过的 `multi_answer_plan.validate_plan` |
| 配方 | seed 17；1,024 次更新 / 2,097,148 个监督 token；LR SHA `14ac59d2…`；学生模型 Qwen2.5-1.5B @ `8faed761`；EOS 151643 |
| 评测提示词（prompts） | 500 条 MATH-500 提示词的 token ID，与冻结的 base 0-shot 端点（`qwen_math_zero`，即 S1 用的端点）**500/500 完全一致** |
| 评测参数 | greedy：T = 0，top-p = 1，seed 17，最多 1,024 个新 token，与 S1 一致<br>4 次采样：T = 0.6，top-p = 0.95，seed 0–3，最多 1,024 个新 token，符合计划 §2.5 |
| 运行顺序与保护措施 | 训练进程必须先成功退出，才会启动 vLLM 评测；评测原始输出先存档、再评分；拒绝重放；不自动重试；硬超时 4,500 秒 |
| 预算 | T 子上限：已预留 $19.65，加上本格后剩余 $130.35；预测本格 $6.09，低于 $6.55 的预留 |

**结论**：T1.5 的 n400 K4 和 K8 两格可以启动训练。

## 未在本次范围内

- **T7 的 K4/K8**：存在选解规则冲突，已于 04:25 UTC 提交负责人决定，并附上我的建议（见消息记录）。在负责人决定前不做 A1。
- **T7 的 K1 格**：A1 尚未做，下一轮处理。
- **A3**：从原始 token 独立重新评分，等结果出来后进行。
