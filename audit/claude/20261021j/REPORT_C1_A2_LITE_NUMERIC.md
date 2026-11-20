# C1 数值 A2-lite（最终交付）

- **审计方**：Claude，2026-10-21 05:35 UTC 前后
- **共享请求**：`p011-C1-complete-path-CR-A1-A2-lite-r1`
- **scope**：`p011-C1-complete-path-CR-A1-A2-lite`

## 结论：PASS-WITH-NOTES

| 字段 | 值 |
|---|---|
| decision | `PASS-WITH-NOTES` |
| scope | `p011-C1-complete-path-CR-A1-A2-lite` |
| target_commit | `270db4a6fed92d310dd7a263269702bd13ed4ffe` |
| original_plan_commit | `e0dee182972f9910b707fac68800dcb5a3aff2d3` |
| spec_sha256 | `416f80bba5cb97162ec170b3f8410082a3f3175b098ad5840e5d6cd6e99395eb` |
| source_files | 13 个，与 `c1_self_calibration_preflight_v1/SOURCE_BINDING.json` 完全相同。这一组源码已在 20261021i 中给出 PASS |
| input_files | 18 个，与 `c1_inputs_actual_v1/INPUT_FILES.json` 完全相同。实际输入 A1 已在 20261021f 中给出 PASS-WITH-NOTES |
| original_group_binding_sha256 | `54e73b1cb1e69d300ee40423236e2d5d2f91e96e42ad03a81f10191256546006` |
| task_inventory_sha256（digest） | `b34417e9e0d7b37b647f3706cec9ecae6f8cc5b59a2e88425966dc58ea0c19f0`。SPEC 中的 task_inventory 与 TASK_INVENTORY.json 逐对象相同 |
| timing_sha256（digest） | `bab88889b9f2d535760fb63dda710cbd0af53de5a5c81ab94574c03f1c45110e` |
| measurement_exceptions | 1 |
| owner_decision_sha256 | `a08ba1abec5108b7ed583175151116f6a074626093c51148e783a5c1020506f0` |
| bounded_in_run_self_calibration_accepted | **true** |
| complete_input_A1_accepted | **true** |
| complete_source_closure_accepted | **true** |
| exact_timing_scope_accepted | **true**（按本次运行实测的完整轮次计时，不使用历史代理） |
| original_tokens_masks_and_EOS_unchanged | **true** |
| untouched_base_forward_only | **true** |
| full_result_window_and_budget_accepted | **true**（附带下面的条件 1 和 2） |

## 核对

- **SPEC 校验**：本地运行 `c1_execution.validate_spec(SPEC)`，通过。具体内容：
  - worker 2400、platform 2460、startup 600、load 900、allowance 300、closeout 7200；
  - full window 10260 = 600 + 2460 + 7200；
  - forward 配置与冻结值一致；
  - `complete_chunk_seconds = []`，`measurement_basis_accepted = false`，owner 文件已列入 source 且 sha 一致。
- **模型**：remote_path 和 9 个文件的 bytes/sha 与 P010 seed29 SPEC 完全相同（Qwen2.5-1.5B，revision `8faed761…`）。
- **费率**：
  - H100 3.95 + 4 个 CPU × 0.0473 + 32 GiB × 0.008 = **4.3952 USD/h**；
  - 0.0012208889 USD/s 向上取整是正确的；
  - reserve = ⌈0.001220888888889 × 3060⌉ = **$3.74**，≤ $4，也 ≤ C 类剩余的 80%（$9.60）。
- **时间窗**：最晚派发时间 10/22 02:09 UTC，可以保证 10260 s 全部落在 05 UTC 之前。之后每次派发时都会由代码重新检查。
- **预算口径**（D1）：
  - 负责人在 Codex 对话中直接报告了当前余额，记录绑定为 `9359a21c…`。这个数与负责人此前对我说的"还有 228 刀"一致。
  - 在此基础上，又**全额保留**了 P010 的有效 ledger 158.17（G 35.16 + T 108.33 + I 14.68，我已与 P010 STATUS.json 核对）和 0.15 的下修。
  - 扣除后约剩 69.68，覆盖受保护的 48 加上 3.74 仍有余量。
  - P011 已有的预留为 0，加上本次后为 3.74，≤ 180。
  - **我接受这个口径用于 C1**：它比实际情况更保守，P010 的费用很可能已经反映在余额里。

## 条件与注意

1. **新鲜度**：实际派发时，入口代码仍要求预算观测 ≤ 1 小时，`usd_per_second` 必须与 SPEC 相等，并且共享账本、并发槽、STOPPED 状态都要重新检查。本 A2-lite 不放宽其中任何一项。如果派发时的新观测与这里不一致，就阻止派发。
2. **证据限制**：余额来自负责人的直接陈述，不是平台 API 或浏览器的独立核验。这一点必须写入记录。
3. **这个口径不能直接用于 A/D（重要）**：
   - 如果后续的长训练继续"从 228 中再扣 158.17"，可用额度就只有约 69.68 − 48 = 21.7。这远低于负责人批准的 A 类 115 + D 类 25，A 网格会因此无法准入。
   - 负责人批准 P011 总额 180、受保护 48 时，前提是 228 为当时的可用余额（228 − 180 = 48），也就是 P010 的费用已经结算。
   - **A/D 的预算口径需要另行确定。** 我会把这一点报告给负责人，本 A2-lite 不预设结论。
4. **最坏损失**：$3.74。实际预计约 20–30 分钟，费用约 $2。实测速度一旦超出窗口或 reserve，会在当前 chunk 结束后立即中止，不重试。
5. **授权范围**：本报告完成后，满足条件 1 即可按已审路径执行一次 upload 和一次 `modal_c1::main`。**只授权 C1**，不授权 A、B、C2 或 D 的任何付费调用。
