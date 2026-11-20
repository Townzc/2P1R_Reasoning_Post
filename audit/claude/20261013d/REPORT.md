# Claude 审计第十一轮：depth_p4_s23 预审 + 作图脚本 @ `0c08a331`

- 范围：`467602ef..0c08a331`（`c36c19bb`、`0c08a331`），包括 `scripts/plot_token_policy_results.py`（已准备，尚未运行）、`P007B_FINAL_DEPTH_EXPORT_RECOVERY_20261013.json`、`P007B_TOKEN_FINAL_DEPTH_CLOSED.json`、`LITERATURE_CORE_RECHECK_20261013.json`（只读过，不做裁定）。
- depth_p4_s23 还没有出正式的结果包。下面是我直接用用户电脑上的原始导出做的**预审**，正式结果包发布后只需对照哈希。

## 结论

| 对象 | 结论 |
| --- | --- |
| depth_p4_s23 结果（949/1319） | **PASS（预审）** |
| 第二次导出恢复（28 个文件 + 13 个块被复用，补齐 14 个块） | **PASS**。恢复后的 state 整个文件 SHA 与 oracle 一致（见下）。wrapper 因为不能覆盖已有的 EXECUTION intent 而报错，这是 `'xb'` 写入模式按设计不覆盖造成的；Codex 保留了报错记录，另写了一份 COMPLETION 记录，处理得当。 |
| `plot_token_policy_results.py` | **PASS-WITH-NOTES**（P11-1、P11-2）。没有运行，需要 8 个 oracle 和最终 CPU 审计都完成。 |

## 实际重算的内容

- 在用户电脑上独立计算 `depth_p4_s23/checkpoint_0256/state.pt` 的 SHA：`bda34bce…a1a6a`，与 RUN_LOG 和 `LOCAL_ORACLE_AUDIT.json` 一致（256 步、524,287 个 target）。
- 从原始 token 独立解码并重新评分（512 截断按答错）：**949** 题答对，截断 **60** 条，与 Codex 一致。与冻结评分器在每题上的判定逐一对照，**0 处不一致**（这个模型里没有 E2）。
- 同一次运行中顺带复核了 seed17 的两个 p4 模型：depth_p4_s17 得 952，0 处不一致；breadth_p4_s17 得 928，唯一的差异是已知的 E2（00803），与第七轮一致。
- 描述性数字（不是结论）：depth_p4 两个 seed 为 952 → 949，截断都是 60 条。breadth_p4_s23 还在评测，所以 seed23 的高题价对比和交互项还不能计算。

## 发现

| ID | 严重度 | 事实 | 建议 |
| --- | --- | --- | --- |
| P11-1 | 低（作图） | 图 1 的 y 轴范围是"最小值 − 2.5 到最大值 + 2.5"，以现在的数据大约是 67%–76%，所以 1–3pp 的差距在图上会显得很大。点上标注了"x/1319"，脚注写明了限制，这一点做得好。 | 汇报时口头说明 y 轴不从 0 开始；或者把图 2（差值与区间）作为主图，图 1 作为辅助。 |
| P11-2 | 低（作图） | 图 2 的"Mean of two observed seeds"使用 `summary['contrasts'][name]['conditional_question_interval_pp']`。这个区间还要等最终的 summary 才能看到计算方式。脚注已经写明它不是 seed CI，这是对的。 | 最终 summary 发布后，我会核对这个区间是不是对"两个 seed 平均后的逐题差值"做 bootstrap（我第九轮在 p0 得到 −0.49 [−2.24, 1.25]）。如果是这样，它仍然只以训练好的模型为条件。 |
| 信息 | — | 门控条件很严格：8 个 oracle、10,552 条输出、4,194,296 个 target、2,048 步、0 个容器，全部满足才会作图；作图也不会重新计算 bootstrap。 | 无需修改。 |

## 未检查

breadth_p4_s23（评测中）、最终 summary、作图脚本的实际输出、最终 CPU 审计。
