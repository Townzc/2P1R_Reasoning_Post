# D1/D2（F15）预算口径修正：CR

- **审计方**：Claude。以本报告的 git 提交时间为准
- **scope**：`p011-D-F15-pair-complete-path-CR-A1-A2-lite`
- **target_commit**：`687011075c425de058f35133a44284153a4c6159`

## 结论：PASS

| 字段 | 值 |
|---|---|
| decision | `PASS` |
| spec_sha256 | `438a120f242b10f99bddc76a06a80f9412dce766dc014fcf603e23e0e71d9321` |
| jobs_sha256 | `12b093de9c73a1a41e00e92ff125e947b7298e849bbc9e8bff231712e04e821d`（与 cbc2e3f0 时相同） |
| source_files | 62 个，sha 全部一致；与 87d2eba3 审查时相比只有 `long_d_pair_path.py` 不同；SOURCE_BINDING `3f800aa2…` |
| delegated_D_decision / original_numeric_SPEC | `bba65b44…` / `f0e92744…` |
| failed_attempt_bindings | `c1b58439…` |
| 其余绑定 | budget_owner `364aaf6c…`；输入目录 `long_inputs_numeric_gold_r1` / `cee34dc0…`；prior_failed_C1 `cef4180d…`；measurement_exceptions 0 |
| 17 个 flag | **全部 true**（包括 `predicted_cost_80percent_with_full_pair_reservations_accepted`） |

## 改动

- 只改了两行：SPEC 的路径，以及 `pair_budget` 中 `reserve > 0.8 × (25 − total)` 改为 `reserve > 25 − total`。
- 预测成本 ≤ 80% 仍由未改动的 forecast 执行。这与我在 87d2eba3 中按计划 §7.1 作出的处置一致 ✓ 新增测试在本机 OK。
- **数值**：D1 预测 10.33 ≤ 20，预留 11.40 ≤ 25；D2 预测 10.27 ≤ 10.88，预留 11.40 ≤ 13.60；合计 22.80 ≤ 25 ✓
- 最晚派发 22:40:35 UTC；派发前仍要做新鲜的费率、D1、槽位、fence 和窗口检查。两格都做或都不做。
