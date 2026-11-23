# 113 个训练格的损失与输出诊断

[完整表格及七格首个 boxed 附表](TABLE.md) · [逐格完整精度数值](RESULTS.json) · [与 Claude 参考值逐行对照](REFERENCE_COMPARISON.json) · [证据与文件哈希](REVIEW_RECEIPT.json)

本轮在原表中加入最后 64 个优化器更新步的损失均值。每步等权，区间为第 T−63 至 T 步。Modal 使用 Trainer 记录到小数点后四位的逐步损失，Tinker 使用原始逐步日志。末步损失仍单列。

113 个新值与 02713c98 提供的独立参考逐行相同，最大绝对差为 0。每行原来的 29 个字段和表格行序均一致。七格首个 boxed 附表与前次接受的文件逐字节相同。输入覆盖主网格 72 格、A8 26 格、A9 R/M 15 格，共 299,968 条已归档输出。

Claude 已在 dabb2a22 完成运行后复核，接受这张表作为诊断数据。运行前接受的候选源码为 06b7f176，先前 113 行的审查提交为 39cd2394。逐行对照包含训练运行标识、两份全精度数值和绝对差。

[冻结的输入及归档成员](INPUT_MANIFEST.json) · [Claude 独立参考](../../../audit/claude/20261122c/CLAUDE_LAST64_REFERENCE.json) · [事前审查](../../../audit/claude/20261122c/REVIEW_498955ab_diagnostics_last64_diff.md)

[运行后独立审查](../../../audit/claude/20261122d/AUDIT_c56a5c70_diagnostics_v2.md) · [接受回执](ACCEPTANCE.json)
