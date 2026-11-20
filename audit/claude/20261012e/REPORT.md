# Claude 审计第五轮：教师原始输出逐条重评分（P007A 先导 + P007B 四格）

- 对照对象：本地保留的原始 token 导出（`.local/midpoint_20261011/teacher_pilot_r1/export_r1/raw`、`teacher_policy_r1/exports/*/raw`，breadth_p4 包含 parent 和恢复两部分），与 `codex/icml-acl-2027@849a3bd0` 中的 `reports/p007_audit/policy_all_v1/attempts.jsonl` 以及先导的 scored 记录。
- 方法：用纯 Python 的 byte-level BPE 从 token ID 独立解码，不使用 transformers，也不使用 `analyses/gsm8k_answer_audit.py`；在第一个 EOS（151645/151643）处截断；没有 EOS 且达到 1,024 token 视为截断。可用的判定：没有出现 "Problem:/Question:" 行首边界，所有 `\boxed{}` 与 `####` 的答案一致且等于 GSM8K train 金标准，以 EOS 结束且未截断，并且在同一题内与之前的可用答案不重复（NFC 加空白规范化）。边界和重复的规则与契约语义相同，但代码是我自己写的。

## 结论：PASS-WITH-NOTES

| 部分 | 重评分条数 | 可用（我 / packet） | 可用判定不一致 | token 数不一致 |
| --- | ---: | ---: | ---: | ---: |
| P007A 先导 | 1,024 | 959 / 959 | 0 | 0 |
| breadth_p0 | 544 | 437 / 437 | 0 | 0 |
| depth_p0 | 736 | 652 / 650 | **2** | 0 |
| breadth_p4（parent + 恢复） | 288 | 215 / 215 | 0 | 0 |
| depth_p4 | 496 | 449 / 449 | 0 | 0 |
| **合计** | **3,088** | | **2** | **0** |

## 发现

| ID | 严重度 | 事实 | 影响 | 建议 |
| --- | --- | --- | --- | --- |
| E1 | 低 | 两处不一致都出现在 `gsm8k/train/05907` 的第 2、5 次尝试：教师写的是 `\boxed{50\%}`，金标准为 50。`marked_answer_v1` 判为 `unresolved_marked_answer`，因此不可用；我的解析器去掉了 `\%`，判为正确。 | 只影响按时间计价的 depth_p0（以及据此训练的先导学生）：少了 2 个可用答案，该题在第 6 次尝试才达到 4 个。**token 计价的 depth_p0 前缀只包含该题的第 1 次尝试**，所以 8 个 token 学生的数据不受影响。 | 规则在所有格中一致使用，不需要修复已有数据；在局限中记录一句"带单位或百分号的框内答案按未解析处理"即可。3,088 条中，其他未解析或缺失的情况共 4 条，都不涉及百分号。 |

## 补充说明

- 这次补上了第一轮报告中写明"未检查"的范围（原始教师输出与检查器的逐条判定），WORKBOARD 中对应的说明可以更新。
- 本次没有检查：GPU 采样记录、服务商时间戳，以及 breadth_p4 故障批次 50 秒收费的重建。
