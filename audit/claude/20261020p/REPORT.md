# C6 未尝试 T72-n400 格补跑：完整 A1/A2

- **审计方**：Claude，2026-10-20 12:15 UTC 前后。
- **请求**：`p010-C6-unattempted-T72-remaining-A2-r1`，scope `p010-C6-unattempted-T72-remaining-input-runtime-and-numeric-A2`。
- **目标提交**：`5de23496b851023f8a1777ba4aa34247097d5ecd`。到 `be353fe7` 为止，数据包、源代码和脚本都没有改动。
- **负责人例外**：已单独批准，见 `audit/claude/20261020o/OWNER_DECISION_D5.md`（D5）。
- **结论：PASS-WITH-NOTES**

## 绑定字段

| 字段 | 值 |
|---|---|
| decision | `PASS-WITH-NOTES` |
| scope | `p010-C6-unattempted-T72-remaining-input-runtime-and-numeric-A2` |
| target_commit | `5de23496b851023f8a1777ba4aa34247097d5ecd` |
| spec_sha256 | `70122980ab2623384dd86cd81b0c0b8bc33d9f88bd1d39b18fdd14122d961b9b` |
| source_files / verification_source_files | 与 SPEC.json 完全相同（20 / 42 个） |
| owner_decision_evidence_sha256 | `f8b290dbe87eb6ac0f4bf9b4e9009f78390ecf99f8763a294b481b8093a4336e`（`20261020o/OWNER_DECISION_D5.md`） |
| failed_parent_manifest_sha256 | `875a27099352a40ffd04a5cfe1899c5f3092ba1857572638307832888e0fac13` |
| original_input_archive_sha256 / basis | `6006dc48…6ceb` / `eb3bf5b9…db9b` |
| same_I_D1_coverage_scope_accepted | true |
| reuse18871_generate2500_only | true |
| first_paid_measurement_exceptions | 0 |

## A1：输入

- **输入文件**：`input_files` 的 6 个文件与原 C6 基准 SPEC（`6167c36b…`，即我在 20261020m 审过并 PASS 的那份）**完全相同**。不重新上传，不重新生成。
- **cue 与选择**：cue 仍为 [1249]，`selection_sha256` 和 `existing_tables_sha256`（复用的无 cue Boolean 表）都与原 SPEC 一致。
- **模型绑定**：与原绑定逐键比较，**只有 `remote_path` 不同**，从 `student/` 改为 `students/`。
  - 产出方 `modal_students_k1_e1d.py`（SHA cc35bc81…）第 36 行的写入路径就是 `/evidence/p010-20261019/students/<run>`，所以新路径正确。
  - `model.safetensors` 的 SHA `d425dbab…` 与我 A3 审过的 `student_results_v1/t72_s17_n400_k1` 原始记录一致。
  - worker 会用 `model_reuse` 逐个核对全部文件的 SHA。
- **失败经过**：保存的 traceback 显示，原 store 里的 terminal 检查已经通过，失败发生在之后 `verify(remote_path)` 的 `FileNotFoundError`。所以这个错误只出在路径上，而且发生在生成之前。T72 格的 batch 和 batch_done 键全部为空；`PRESERVATION_COMPLETED` 记录三格保存的行数为 4500 / 11871 / 2500，ack 数为 18 / 47 / 10，合计 75。

## A2：运行时（逐行阅读）

**`cue_remaining.generate`**
- 运行前检查：1 张 H100（≥ 75 GiB）、一次性 claim、`check_parent`（原失败组的 claim、terminal、cell 都不变，T72 前缀没有任何尝试）、输入 verify。
- roster 检查：2500 行、cue [1249]、新路径。
- 分批：每批 256 条，共 10 批，最后一批 196 条。每批先写 forecast 和 intent，并设一次性围栏；生成后检查原始结果的身份和 prompt；写 ack。
- 结束检查：总时长不超过 deadline − 15 s。
- 生成主体（engine_kwargs、returned_records、prompt_token_ids=input_ids）与原 `generate_cell` 相同。

**`modal_cue_remaining`**
- worker 资源：H100!，cpu 4，32 GiB，`timeout=1260`，`retries=0`，单容器，硬计时 1200 s。
- 失败时写 terminal=failed，不自动重试。
- 入口检查：
  - 完整结果窗口 61,425 s 必须在 10/21 19:00 UTC 前结束，所以**最晚 10/21 01:56 UTC（10/20 18:56 PDT）调度**；
  - 源代码和验证源代码逐个核对 SHA；
  - owner_review 和 A2 绑定；原 C6 A2、选择 A3、结果 A3/A4；
  - 保存包的 manifest 和 COMPLETED；输入上传后读回比对；预算文件在 1 小时内新鲜；
  - 所有作业 STOPPED、容器数为 0；
  - 新键和旧键都没有被占用。

**`forecast`**
- 费率：0.001097 + 4 × 0.0000131 + 32 × 0.00000222 = 0.00122044 $/s。
- 初始情景：1.2 × (20.412 × 10 + 600) = 964.95 s，预测 (964.95 + 700) × 0.00122044 = **$2.032**。
- `budget_check` 的计算：
  - 前置额度 prior = I 结算后的 12.16，剩余 = 15 − 12.16 = 2.84；
  - 预留 2.52 ≤ 2.84 ✓；
  - 预测 2.032 ≤ 0.8 × 2.84 = 2.272 ✓；
  - 预测 2.032 ≤ 预留 2.52 ✓。
- 观测批次共 233 个 = 原 158 个 + 保存的 75 个；最大 20.41 s。这些都是同为 1.5B 的学生或 base 模型，可比。

**`effective_totals` 与 E3 的兼容性**：两种状态都覆盖到了。
- G = 44（E3 没有跑）。
- G = 55.13（E3 已跑）。此时要求 E3 的 `D1_SETTLEMENT_APPLIED`、E3 A2，以及 settlement 能用新鲜账单复验；有效 G = 24.03 + 11.13 = 35.16。
- 两种状态下都要求 I 的原始账本恰为 14.43。
- 入口要求容器数为 0，所以**只能在 E3 STOPPED 之后调度**。这与 E3 的入口条件（I 的原始值不超过 15）一起，强制了 **E3 → C6 补跑** 的顺序，与 20261020o 备注 3 一致。

**I 类别的 D1**：0.82151854 是 4 个 hourly 资源行之和，我独立相加过，与历史读数相同。× 1.2 = 0.98582 → **$0.99**，释放 2.27；结算后 I = 14.68。如果新鲜计量更高，候选值就会改变，入口会直接拒绝（`validate_I_settlement`），不会默默修正。

**原始结果核对与评分**
- `audit_p010_cue_remaining`：失败父组和新调用分开核对身份链；18,871 + 2,500 = 21,371 行，用原有的 `replay` 第一次解码；检查 75 个原批次时间都进入了新的 forecast 序列。
- `score_p010_cue_remaining`：只加了 lineage 检查，评分仍调用原 `score()`。原 `score()` 依赖的 `existing_tables_sha256` 和 `cells[run]` 字段在新的 SPEC 和 proof 中都存在，所以兼容。

## 备注

1. **我在 20261020m 的漏审（承认）**：当时 A2 PASS 了 C6 基准，但没有把 T72 格的 `remote_path` 与产出方的实际写入路径（`students/`）对照，这才导致失败。这是第二次在"路径或输入格式"这类细节上漏审，第一次是 E4 的 endpoint。从这次起，A2 增加一条固定检查：**每个 remote_path 都要追到产出方代码的写入行**。本报告已经按这条做了。
2. **耦合风险**：现在的设计中，已完成三格的解码和评分要等补跑格完成后才能做。如果补跑失败，**建议 Codex 另外准备一个"只用保存的三格"的 oracle 和评分路径（不重新生成），提交审计后再用**，以免 base MATH / base GSM / S1-n400 的 cue 结果也因此丢失。这条不阻塞本次 PASS。
3. **合成测试**：Codex 记录的 11 项合成测试我没有重跑，也没有运行 vLLM 或 math-verify。
4. **披露**：第 4 格是在原组失败之后单独补跑的。四格不是同一次调用，但模型、cue、输入和采样都与原设定相同。报告里要写明（见 D5）。

**A3**：结果出来后由 Claude 独立做。
