# Claude 审计第六轮：token 计价 p0 × seed17 学生 + R1/L1 修复 @ `e04212e3`

## 结论

| 对象 | 结论 |
| --- | --- |
| `c1f64cc2`：R1（去掉 pyarrow 依赖）、L1（截断计数） | **PASS**。在没有 pyarrow 的环境里，`reproduce_token_schedules.py` 现在可以直接运行（rc=0）；`tests.test_token_endpoint_reporting` 与 `tests.test_token_tariff` 通过；先导截断计数 38/33 与我上一轮的结果一致。 |
| `token_p0_seed17_v1`（第一对 token 学生） | **PASS-WITH-NOTES**（E2） |
| `e04212e3` 启动记录 | 只是记录启动，没有结果 |

## 实际重算的内容

- manifest 9 个文件的 SHA 全部匹配；1,319 题无重复。
- breadth_p0_s17 答对 963（73.01%），depth_p0_s17 答对 950（72.02%）。只有 depth 答对 103 题，只有 breadth 答对 116 题。depth − breadth = **−0.99pp**，配对 bootstrap 区间 **[−3.18, 1.21]**（seed 20261013，10,000 次）。
- 从你电脑上保留的原始 token 独立解码并重新评分（512 截断按答错）：截断条数 44 / 45，与 packet 一致；depth 2,638 条中 0 处不一致；breadth 只有 1 处不一致（E2）。
- 两个学生都是 256 步、524,287 个 target，输入 manifest `85efe502…` 与 admission 一致（依据 Codex 本地审计记录中的字段）。

## 发现

| ID | 严重度 | 事实 | 建议 |
| --- | --- | --- | --- |
| E2 | 低 | `gsm8k/test/00465`（breadth_p0_s17）：输出以 "The answer is:" 换行、再写 `\[\boxed{30}\]` 收尾，金标准为 30。`marked_answer_v1` 的 `ANSWER` 正则在 "The answer is:" 这一行匹配到一个**空的** answer statement，值为 None，导致整题记为 `unresolved_marked_answer`，按答错计入。这是解析器的系统性假阴性（false negative），触发条件是"答案陈述独占一行、框内答案在后面几行"。在 4 个已完成的 P007B 学生中，只有这 1 例的框内答案是正确的。 | 评测规则已冻结，所有臂一视同仁，运行中不要改。在局限中记录这一模式；最终结果表中可以附一个敏感度数字（把"空陈述 + 唯一正确框内答案"视为正确后的准确率），作为补充，不替换主终点。 |

## 未检查

模型权重与训练过程逐步核对（依赖 Codex 本地审计）；p4 两个学生和 seed23 尚未完成。
