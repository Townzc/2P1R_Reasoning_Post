# 负责人决定：批准 C1 r2（一次新的逻辑尝试）

- **记录方**：Claude
- **时间**：2026-10-20 约 23:30 PDT（2026-10-21 约 06:30 UTC）
- **方式**：负责人在 claude.ai 对话中，通过选项直接回答
- **选择**："批准 r2 (推荐)"

## 我提供给负责人的选项说明

> 只把每批从 32 条改成 320 条（共 30 批），计算方式和结果定义都不变。预留约 $2.64，预计实际约 $1；改动需要我再审一次代码。C 类剩下约 $4.5 给 C2。

## 批准范围

1. **只有一次新的逻辑尝试。** 逻辑 ID 必须是新的，例如 `C1_original_token_base_forward_r2`。r1 的失败证据、fence 和 $3.74 reserve 原样保留，r1 不得续跑，也不得重试。
2. **代码改动仅限以下两项。** 其他一律不改，包括 token、掩码、EOS、只前向、batch=1、BF16 logits/FP32 损失、`descriptive_summary` 定义、全部 fence 和 no-retry 规则。
   - 日志 chunk 大小从 32 改为 320，相关的 spec 字段 `journal_chunk_size`、`CHUNK` 和回放检查同步修改；
   - 适配新的逻辑 ID 和远端路径。
3. **自校准方式不变**，沿用负责人 a08ba1ab 例外中规定的机制：第 1 个 chunk 只有硬计时器保护；每个 chunk 完成后都用本次运行的实测完整轮次做预测，系数 1.2，预留 300 s。
4. **上限**：
   - worker ≤ 1,500 s，platform = worker + 60，startup = 600，load ≤ 900 s；
   - reserve = ⌈费率 × (startup + platform)⌉，**≤ $2.70**，并且 ≤ C 类剩余额度的 80%；
   - `measurement_exceptions` = 1，同时绑定 a08ba1ab 和本文件的 sha。
[Private current balance paragraph omitted; original bytes/hash retained locally.]
6. **流程**：Codex 提交改动后由我做简短 CR，再给出 A2-lite，通过后才可以派发。
