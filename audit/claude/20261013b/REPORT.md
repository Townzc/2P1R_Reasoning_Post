# Claude 审计第九轮：seed23 零题价两格结果 + 导出恢复代码 @ `5a9326ff`

- 范围：`3709b452..5a9326ff`，共三个 commit：`reports/p007_audit/token_p0_two_seeds_v1/`（external_review: pending）、`scripts/resume_midpoint_export.py` 及其测试、`P007B_EXPORT_RECOVERY_{20261013,CLOSED_20261013}.json`、`P007B_TOKEN_FINAL_PAIR_STARTED.json`。
- 不在范围内：高题价 seed23 两格（刚启动）、模型权重的逐步核对。

## 结论

| 对象 | 结论 |
| --- | --- |
| `token_p0_two_seeds_v1` | **PASS-WITH-NOTES**（E2 新增 2 例；S9-1 解读） |
| `resume_midpoint_export.py` | **PASS**。只读、不覆盖；4 个单元测试通过。 |
| 最后一对（p4 seed23）的启动 | **PASS（只覆盖记录）**。config 哈希与 admission 一致；源码从 `90ba8859` 变为 `5c69d32d`，但 `experiments/ src/ configs/` 没有变化，只新增了导出脚本。 |

## 实际重算的内容

- manifest 中 13 个文件的字节数和 SHA 全部匹配。用户电脑上那份 `paired_question_scores.json` 的哈希（`77d110e0…`）与 packet 一致。seed17 两列与之前的 packet 逐题相同。
- 准确率：breadth_p0_s23 **958**、depth_p0_s23 **958**（各 1,319 题）。截断各 49 条，与 packet 一致。
- 两个 seed23 的 `checkpoint_0256/state.pt` 在用户电脑上独立计算 SHA：`45f95707…`（222,114,421 字节）和 `496c16db…`（222,114,741 字节），与 oracle 记录一致。depth_p0_s23 就是经过导出恢复的那个文件，所以恢复后的状态是完整的。
- 从原始 token 独立解码并重新评分（512 截断按答错）。我与 packet 的差异只有以下三处，都是 E2（"The answer is:" 单独成行，后面是正确的框内答案；冻结规则判为未解析）：

| 模型 | 题号 | 金标准 / 框内 | 状态 |
| --- | --- | --- | --- |
| breadth_p0_s17 | gsm8k/test/00465 | 30 / 30 | 已知（第六轮） |
| breadth_p0_s23 | gsm8k/test/00498 | 40 / 40 | **新** |
| depth_p0_s23 | gsm8k/test/01169 | 2 / 2 | **新**，也是 depth 中第一次出现 E2 |

  其余 1,319 × 4 中的输出逐题一致。

- 配对 bootstrap（seed 20261013，10,000 次，四个模型共用同一组重抽样）：

| 对比 | 差值 | 95% 区间 |
| --- | ---: | --- |
| seed17：depth − breadth | −0.99pp | [−3.18, 1.21] |
| seed23：depth − breadth | **0.00pp** | [−2.12, 2.20] |
| 两个 seed 平均（补充，我算的） | −0.49pp | [−2.24, 1.25] |
| 同一格不同 seed：breadth s23 − s17（补充） | −0.38pp | [−2.35, 1.59] |
| 同一格不同 seed：depth s23 − s17（补充） | +0.61pp | [−1.29, 2.43] |

- E2 敏感度（统一规则：每个 E2 都算对）：p0 两个 seed 分别为 −1.06pp 和 0.00pp，结论不变。

## 发现

| ID | 严重度 | 事实 | 建议 |
| --- | --- | --- | --- |
| S9-1 | **中（解读）** | 同一格只换训练 seed，就有 **183 题**（breadth）和 **156 题**（depth）的对错发生变化。同一 seed 内 depth 与 breadth 的不一致题数是 219（s17）和 208（s23），两者是同一个量级。因此"题目层面的 bootstrap 区间"（以训练好的模型为条件）低估了真实的不确定性，因为它不包含训练方差。从 seed17 的 −0.99pp 到 seed23 的 0.00pp，这个变化本身就在训练噪声的范围内。 | 中期汇报中，p0 的结论写成"两个 training seed 下，depth 与 breadth 都无法区分（−0.99、0.00pp）"。不要单独引用 seed17 的数字。p4 seed23 出来后，交互项要同时报告每个 seed 的值；如果两个 seed 的方向不一致，那就是主要结论。这也说明，题目 bootstrap 需要配合 seed 层面的方差（clustered / hierarchical bootstrap，或者更多 seed）。中期后再考虑，不影响冻结方案。 |
| E2-b | 低 | 新增 2 例 E2，其中 1 例在 depth。到目前为止，6 个模型中共 4 例（breadth 3、depth 1）。 | 维持主结果；8 个模型都完成后，再统一做一次敏感度分析。 |
| C9-1 | 信息（代码） | `repair_state` 用 `body.ljust(length, b'\0')` 为短响应补零。单独看，这可能掩盖截断的响应；但 `assemble` 在发布前会检查整个文件的 SHA，所以不会静默出错。`fetch` 用 `'xb'` 打开文件，中途失败时会留下部分文件，下一次 `inventory` 会因为"内容不同"而拒绝，偏保守。 | 无需修改。如果想让失败原因更清楚，可以在补零前记录 `len(body)`。 |

## 未检查

两个 p4 seed23 学生（运行中），以及模型权重的逐步训练核对（仍依赖 Codex 的本地审计）。
