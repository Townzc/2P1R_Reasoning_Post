# Claude 审计第十三轮：第十二轮处理 + 运行时诊断 @ `bce2daca`

- 范围：`4f88d54c..bce2daca`（`25eaa661`、`7d46e1ef`、`bce2daca`），包括 `docs/audit/P007_TOKEN_REVIEW_DISPOSITION_20261012.md` 中第十二轮一节、`P007B_TOKEN_ROUND12_REVIEWED.json`、`scripts/summarize_token_runtime.py`、`P007B_TOKEN_RUNTIME_DIAGNOSTICS.json`，以及 `build_token_midpoint_evidence.py` 的两处一行修改。
- 最终 CPU 审计、最终 summary、图和事实页仍未生成，不在本轮范围内。

| 对象 | 结论 |
| --- | --- |
| 第十二轮处理（F12-1 撤回 S7-2、F12-2/3、P11-2） | **接受**。F12-1 的措辞正确："不以首个 seed 的单独下降作为发现，不作因果解释为重复损伤"；原记录保留，另加更正说明。 |
| 事实页生成器的两处修改 | **接受**。加了"未做多重比较校正"，并引用运行诊断及其局限；都是加限定，没有新增主张。 |
| `summarize_token_runtime.py` 与诊断 JSON | **PASS**。我重新求和：训练更新共 56.50 GPU 分钟，worker 共 9.778 GPU 小时，训练占 9.63%，`other = wall − train` 逐项成立；8 个 receipt SHA 与 closeout 一致；GPU 采样文件的大小和 SHA 由脚本对照 manifest 断言。局限写得充分（采样混合各阶段，不能当作 FLOPS 效率）。 |

## 建议（中期后，不是审计问题）

| ID | 内容 |
| --- | --- |
| R13-1 | 训练只占 worker 时间的 9.6%；每个学生平均约 66 分钟花在训练以外（准备、1,319 题 × 512 token 的 greedy 评测、checkpoint 和 I/O），采样的 GPU 利用率平均只有 16–30%。中期后有 $2,700 预算，**最大的效率杠杆是评测后端**，不是训练。建议先做一次小的等价性检查：同一个 checkpoint 分别用 HF generate 和 vLLM 做 greedy 评测，比较逐题输出与判定。如果有差异，就把 vLLM 评测定为一个新的冻结评测契约，只用于新的实验，**不与现有 8 个结果混合**。预计每个学生的成本可以明显下降，从而可以负担更多 seed 和独立采购重复（这是 S8-1、S9-1、F12-1 共同指向的需求）。 |

无新发现。等待 CPU 审计结果、最终 summary、图和事实页。
