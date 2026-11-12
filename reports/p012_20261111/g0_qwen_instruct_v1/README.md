# Qwen2.5-1.5B-Instruct：G0-E 首批全量结果

模型与协议均使用冻结配置，执行代码 `5f7935f1`。首轮 20 题已通过 S1–S4。

| 数据集 | 结果 | 结束符 / 长度上限 / 停止串 | 未分类停止 |
|---|---|---|---|
| MATH-500 | Li 规范化精确匹配 232/500 = 46.4%；204 条待集中模型判分 | 478 / 21 / 1 | 0 |
| GSM8K test | Li flexible-extract 903/1319 = 68.46% | 1313 / 6 / 0 | 0 |

MATH 最终 Li 指标等待合并的 Qwen-32B 判分；准确率字段 `accuracy_with_judge` 当前为 null。GSM8K 无模型判分步骤。

两个压缩包包含配置、完整输入、原始 token / 文本 / 停止信息、运行日志、逐题标签和 manifest。按计划，结果审查由 Claude 独立抽取至少 10% 原始输出复核；该项尚未完成。官方数字只在 benchmark 与协议相同时设置数值门槛。

费用与结余见 [BUDGET_SNAPSHOT.json](BUDGET_SNAPSHOT.json)。后续继续评测两个固定 UWNSL 公开检查点。
