# B 生成：数值 A2-lite（仅生成阶段）

- **审计方**：Claude，2026-10-21 08:20 UTC（负责人夜间全权审核期间）
- **请求 / scope**：`p011-B-generation-student-complete-path-CR-A1-A2-lite-r1` / `p011-B-generation-student-complete-path-CR-A1-A2-lite`
- **target_commit**：`85bc4260036c607aae6db10bd3179eab14c91a66`

## 结论：PASS-WITH-NOTES（仅授权生成 job `B_generation_t10_400x16_r1`）

| 字段 | 值 |
|---|---|
| spec_sha256 | `9fe8109ff13cfcf7f86900ec66d635a9506697e947c06c77d6fd950b85ee1a79`。本地 `b_current_path.validate` 通过 |
| jobs_sha256 | `34293f2e7fd98dc68061c0f98230415cd1c0c3c23a2f86129208aa81ba716ac2` |
| source_files | SPEC 中的 75 个文件在 HEAD `91387a62` 上重算全部一致。AST 扫描显示本仓库内的 import 没有遗漏 |
| owner_B16_sha256 / budget_owner_decision_sha256 | `2e0c8af1…` / `364aaf6c…` |
| measurement_exceptions | 0 |
| packet | MANIFEST `7a13b700…`，SOURCE_BINDING `65f0823c…` |
| 9 个 true flags | `complete_source_closure_accepted`、`complete_actual_input_A1_accepted`、`original_P010_tokens_seeds_dose_and_endpoint_rules_unchanged`、`all_original_complete_timing_sources_accepted`、`full_state_raw_scoring_window_and_budget_accepted`、`remote_paths_traced_to_producers`、`owner_B16_selection_and_actual_Pcov_accepted`、`current_owner_accounting_and_saved_failed_parent_accepted`、`original_complete_cycle_interval_proxy_accepted`，**全部为 true** |
| 不授权 | B1、B2、B3 学生和 B4。学生的实际输入 A1 和数值附录要另行提交 |

## 核对

- **`b_current_path` 对比已审的 `b_path`**：逐行 diff 后，改动只有以下几处：
  - 预算口径改为 364aaf6c 的定义（protected 0，按负责人陈述的当前余额计算可用额度）；
  - 按资源计算完整费率，H100 + 4 CPU + 32 GiB = 4.3952 USD/h，reserve 等于 ⌈费率 × (600 + 1860)/3600⌉ = **$3.01**；
  - ledger 加入 r1 失败父尝试的保存记录，并检查 3 个 fence；
  - 新增 2 个 flag。

  `modal_b_current` 只改了 import ✓
- **计时代理**：P010 原 T1.5 生成的 23 个完整批次区间（每批 256 条，从一批 intent 到下一批 intent），最大值为 22.10 s。这些区间里还包括了当时的符号评分和存储操作，用来估计不含评分的新流程是偏保守的。我**接受**这个代理，条件有两点：
  - T=1.0 会让更多输出跑到 1024 的上限。但每批耗时本来就取决于其中最长的那条，而 P010 的批次里已经有很多跑满上限的输出，所以影响有限；
  - 运行中的 forecast 会用实测的批次时长持续更新。
- **数值**：
  - 初始预测为 1.2 × (25 × 22.10 + 600) = 1,383 s，worker 上限 1,800 − 30 = 1,770 s，可以放下；预测费用 $2.43，reserve $3.01；
  - B 类上限 $20 的 80% 是 $16，没有超；
  - 当前 B 类之前没有预留。
- **时间窗**：
  - 结果窗口 71,665 s = 600 + 1,860 + 69,205；69,205 = 3,600 collect + 3,600 audit + 62,000 评分 + 5；
  - **最晚派发时间是 2026-10-21 09:05:35 UTC**，现在剩约 45 分钟。
  - 评分上限 62,000 s 是按 1.2 × (6,400 × 8 s + 300) 的最坏情况设定的，实际评分时间会短得多。

## 注意

1. **时间非常紧**：如果 09:05:35 UTC 前无法完成上传、取得新鲜的费率和预算证据并派发，生成 job 的窗口检查就会失败。这种情况下**不得**缩短评分上限来强行准入；应当报告负责人，等待负责人决定。
2. **入口条件**：派发时，入口代码仍要求：费率与 SPEC 相等、预算观测在 1 小时内、账本和 4 个并发槽满足要求、r1 的 fence 检查通过。新费率如果更高，reserve 会随之变化，SPEC 必须重新审。
3. **学生阶段**：学生 job 必须在 05 UTC 前放得下自己的结果窗口（评分上限 25,200 s 加上训练和评测的时间），也就是大约在 2026-10-21 18:00–19:00 UTC 之前派发。这要求生成结果的本地评分在此之前完成。
