# 负责人决定：C1 采用有界的自校准付费实测例外

- **记录方**：Claude
- **负责人答复时间**：2026-10-20 21:02 PDT（2026-10-21 04:02 UTC）
- **答复方式**：在 claude.ai 对话中通过选项直接作答

我提出的问题是：C1 按现行规则无法准入，应走哪条路线。三个选项为：自校准例外（推荐）、chunk=64 硬上（约 $8.6）、放弃或推迟 C1。

**负责人的选择："自校准例外 (推荐)"**

我向负责人说明的选项内容是：负责人批准一次付费实测例外；预留约 $3.7，最多运行 40 分钟；先跑 1–2 个 chunk，如果实测预测超限就自动中止，不重试；最坏损失为 $3.7，C 类约剩 $8 留给 C2；需要做一次小的代码修改并重新审查，约 1 小时。

## 例外范围（代码与 spec 必须严格满足；超出部分不在批准范围内）

1. **只适用于 C1**：逻辑 ID 为 `C1_original_token_base_forward_r1`，只允许一次尝试，不重试，partial 一律保留。
2. **窗口**：
   - `worker_seconds` ≤ 2,400；
   - `platform_seconds` = worker + 60；
   - `startup_seconds` = 600；
   - 整个结果窗口在 2026-10-22 05:00 UTC 之前结束。
3. **Reserve**：
   - reserve = ⌈当前新鲜费率 × (startup + platform)⌉，并且 **≤ $4.00**；
   - 同时不超过 C 类剩余额度的 80%；
   - C12、P011 总额 180、受保护 48 都保持不变，不做范围转移，不动 emergency 预算，不释放 reserve。
4. **准入阶段**：不使用任何代理计时。准入只检查以下几项：
   - 窗口和 reserve 满足上面两条；
   - 共享账本和并发槽满足要求；
   - 预算是新鲜的。

   spec 中写 `basis_kind = "owner_approved_in_run_self_calibration"`、`measurement_exceptions = 1`，并绑定本文件的 sha。
5. **运行中**：
   - 模型加载必须在 worker 开始后 900 s 内完成，否则中止；
   - 从第 1 个完整轮次结束起，forecast **只使用本次运行实测的完整轮次时长**（含 3 次 commit 和远端 chunk_done，即 0c37b5a0 的计时范围），保留 1.2 倍系数和 300 s 的 future allowance；
   - 任何一次预测超过 `worker_seconds − 30`，或者预测费用超过 reserve，就立即中止，写 FAILED，不重试；
   - 第 1 个 chunk 开始之前，没有基于预测的检查。第 1 个 chunk 期间的唯一保护是硬计时器，其最坏损失已经包含在 reserve 中。
6. **其余全部不变**：原 token/掩码/EOS、只前向、完整结果证明、`descriptive_summary` 的定义、全部 fence 与 no-retry 规则。

## 后续流程

- Codex 做有界的代码修改（`c1_execution.forecast`/`validate_spec`/`run_body`/`check_body`，以及 `c1_admission.fresh_budget` 中与初始预测相关的部分），并提交简短 CR。
- CR 通过后，再在同一共享请求下给出 A2-lite 结论。
- 本文件**本身不授权**上传或派发。
