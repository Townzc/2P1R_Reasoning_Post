# C1 r2：完整路径源码 CR + 输入复用 + 数值 A2-lite

- **审计方**：Claude，2026-10-21 07:40 UTC 前后（负责人夜间全权审核期间）
- **请求**：`C1_R2_COMPLETE_PATH_CR_A1_A2_REQUEST`
- **target_commit**：`d18581c10d2a7647ff9ecb1f028eca911b7837cf`
- **packet**：`c1_r2_runtime_v1`，MANIFEST `d198c7ce…`，SOURCE_BINDING `3d868a68…`

## 结论

| scope | decision |
|---|---|
| `p011-C1-r2-chunk320-complete-path-CR` | **PASS** |
| `p011-C1-r2-chunk320-complete-path-CR-A1-A2-lite` | **PASS-WITH-NOTES** |

## 绑定字段

| 字段 | 值 |
|---|---|
| spec_sha256 | `c51ace0d0768740b49f803c8a219eddce2c30b0c0b23f48fa6afdd45c8f0496f`（本地 `validate_spec` 通过） |
| source_files | SPEC 中的 22 个文件，在 HEAD `c2258fd2` 上重算全部一致 |
| input_files | 原 18 个文件，与 20261021f 已 A1 的输入完全相同 |
| original_group_binding_sha256 | `54e73b1c…` |
| task_inventory_sha256 | `409481a7…`（journal_chunks=30，其余与原清单相同） |
| timing_sha256 | `b6bf1603…` |
| owner_decision_sha256 | `a08ba1ab…` |
| r2_owner_decision_sha256 | `e381630c…` |
| budget_owner_decision_sha256 | `364aaf6c…` |
| measurement_exceptions | 1 |
| 9 个必须为 true 的 flag | `bounded_in_run_self_calibration_accepted`、`r1_failed_call_and_reservation_retained`、`original_input_upload_reuse_accepted`、`complete_input_A1_accepted`、`complete_source_closure_accepted`、`exact_timing_scope_accepted`、`original_tokens_masks_and_EOS_unchanged`、`untouched_base_forward_only`、`full_result_window_and_budget_accepted`：**均为 true** |

## 核对要点

- **改动范围**：我逐行看了 `ORIGINAL_TO_NEW_PATH.diff`，所有改动都在负责人 e381630c 授权的范围内：
  - CHUNK 从 32 改为 320，`journal_chunk_size`、`target_scope` 以及各处 chunk 数计算同步修改；
  - 新逻辑 ID 与远端目录改为 `_r2`；
  - worker ≤ 1500，reserve ≤ $2.70；
  - 预算口径改为 protected 0、availability 按当前余额，并绑定 364aaf6c。

  token、掩码、EOS、只前向、batch 1、BF16/FP32 NLL、`descriptive_summary` 都没有改动。
- **剩余 chunk 数**：`run_body` 和 `check_body` 在最后一个不满的 chunk（314 条）上算出的剩余 chunk 数一致，都是 0 ✓
- **evidence 和收集**：都改为按 320 一组；`complete_record_keys` 用的是 SPEC 中的 `journal_chunks`=30，`inputs.load_pack` 校验时会还原成原清单的 300，与原清单保持一致 ✓
- **父尝试**：`parent.preserved` 核对了 r1 的 FAILURE、SUBMITTED、INTENT、STOPPED0，保留的 3.74，我的失败复核（`ecca9526…`），以及 3 个永久 fence；ledger 中保留了 r1 ✓
- **输入复用**：通过原 SPEC 和完整的回读收据复用原上传，不重新复制或上传；worker 读取原 `c1_inputs_r1` 路径 ✓
- **测试**：本地 10 + 4 项测试全部通过。
- **数值**：
  - 按历史认证费率，reserve = ⌈0.0012208889 × (600 + 1560)⌉ = $2.64 ≤ $2.70；
  - C 类剩余 8.26 × 80% = 6.61，$2.64 在范围内；
  - 结果窗口为 9,360 s，最晚 2026-10-22 02:24 UTC 派发 ✓

## 可行性推算（用 r1 已保存的逐条证据，只用于判断风险，不作为计时依据）

r1 第 1 个 chunk 的实测数据：
- 每条序列前向平均 0.040 s，其他开销仅约 0.003 s/条；
- 32 条序列共占 1.35 s；
- 完整轮次的其余部分主要是 3 次 commit，每次约 1.4–1.9 s。

推算 320 条一个 chunk：
- 前向约 13.5 s，3 次 commit 约 6–9 s，完整轮次约 **20–23 s**；
- 第 1 个 chunk 之后的预测约为 1.2 × (67 + 29 × 23 + 300) ≈ 1,240 s，上限是 1,470 s；
- 要触发止损，单轮需要超过约 **29.6 s**。

320 条一组时，各 chunk 的 token 数差异很小（最大 180,885，平均约 173,800）。我估计成功概率较高，但 commit 时间会随文件数增加，这一点有不确定性。即使失败，也会在第一个 chunk 后止损，损失不到 $0.5。

## 条件

1. **入口新鲜度**：实际派发时，入口代码仍要求预算观测 ≤ 1 h、费率与 SPEC 相等、账本与并发槽检查通过。Codex 需要在派发前取得新鲜的计量和费率证据；如果新费率高于历史费率，导致 reserve 超过 $2.70，必须停止派发并报告负责人。
2. **余额依据**：余额以负责人陈述的 $228 为基准，减去全部 P011 预留和之后的计量增长，不再扣 P010 的费用。这个口径**我接受**，但证据仅来自负责人的陈述，这一点需要披露。
3. **授权范围**：本报告完成后，可以执行 FUTURE_COMMANDS 中的唯一一次派发，以及之后的 collect 和 audit。C1 结果出来后，我会独立重算 `descriptive_summary` 并做成本对账（A3）。
