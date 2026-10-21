# 勘误：recount.py 中的字段名错误（2026-10-21 04:35 UTC）

Codex 指出的问题属实：`recount.py` 第 50 行读的是 `flags.overlength`，去污染集合读的是 `decontamination`/`decontaminated`。原 disposition 中实际的字段名是 `flags.any_overlength` 和 `flags.decontamination_hit`。因此原 RECOUNT.json 中的 `rprime16_and_overlength=0` **无效**，并不能验证"847 个超长"。原报告与 RECOUNT.json 保持不变。

这次我按原字段名，用同样的原始数据（公开的 PARENT_DISPOSITIONS + PARENT_DIAGNOSTICS）重新统计，结果见 `RECOUNT_CORRECTION.json`：

- `any_overlength` 的分布：True 847 / False 4,038 / None 48,222（None 表示未检查，即不完整的父题）
- `decontamination_hit` 为 True 的有 3 个，**全部落在不完整的父题里**
- 原规则下 16 条全完整的父题共 4,885 个，可以完整拆分为 4,038 个合格 + 847 个超长，两者之间不重叠，也没有未归类的
- R′ 下 16 条全完整的 5,190 个父题：
  - 4,038 个合格 + 847 个超长 + 305 个新增；
  - 新增的 305 个全部没有长度判定（未知），也都没有去污染命中；
  - 可能合格的上界 = 4,038 + 305 = **4,343**
- PARENT_DIAGNOSTICS 中的 `original_any_overlength` 和 `original_decontamination_hit` 两列，与原 disposition 53,107/53,107 一致
- 所有合格父题都没有任何标记

**结论不变**：两条预先约定的阈值本来就不使用这两个字段，仍然都未触发；原报告叙述中的 847、4,038、305、4,343 现在都已有独立核实。
