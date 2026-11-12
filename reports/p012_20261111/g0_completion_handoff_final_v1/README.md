# G0 已完成评测与待审事项

8 组 Li 协议下的 Instruct／公开检查点评测已保存原始输出和初次评分，当前没有运行中的模型任务。G0-E 还需完成标准 few-shot base 评测、一次集中 MATH 判分，以及独立 10% 评分抽查。

| GSM8K：Li 发布版、0-shot、greedy | 正确题数 / 1,319 | 准确率 | 同协议论文差值 |
|---|---:|---:|---:|
| Qwen2.5-1.5B-Instruct | 903 | 68.46096% | 参考协议未对齐，不设门槛 |
| UWNSL short | 949 | 71.94845% | +0.24845pp，通过 |
| UWNSL long | 825 | 62.54738% | −1.25262pp，通过 |
| Llama-3.2-1B-Instruct | 550 | 41.69826% | 参考协议未对齐，不设门槛 |

按计划汇报下降项：公开 long 检查点比原始 Qwen Instruct 低 5.91357pp；short 高 3.48749pp。这里记录点差，尚未做统计推断。四组 MATH 共有 742 条待判，exact-only 分数不是最终 Li 分数。

原始记录：`../g0_qwen_instruct_v1`、`../g0_uw_short_v1`、`../g0_uw_long_math_v1`、`../g0_uw_long_gsm_v1`、`../g0_llama_instruct_math_v1`、`../g0_llama_instruct_gsm_v1`。

待审代码固定在 **fae6656d**。请合并阅读 `../pre_c8_review_addendum_v1/README.md` 与 `../pre_c8_review_v1/README.md`；重叠文件以 addendum 中的哈希为准。范围为 F4/F5、标准 base 提示和评分、Modal 训练／评测启动器、集中判分及 H200 配置。真实 CPU 环境验证和 31 个本地回归用例均通过。P012 §12 要求每条新增共享路径首次运行前由 Claude 审一次；这仍是同一次合并审查。

G0-E 上限已获准提高至 $8，无需再调整预算。截至 UTC 11:00 的账单快照为 $3.21473239；含已完成任务的未结算预留和杂项预留合计 $3.65463864，详见 `BUDGET.json`。G0-T、C8、主网格训练前基线和 OMI-2 过滤均未运行。

Built with Llama.
