# P010 最终冻结版本：A5

- **审计方**：Claude。以本报告的 git 提交时间为准
- **请求 / scope**：`p010-final-frozen-technical-evidence-A5-20261021-r1` / `p010-final-frozen-technical-evidence-A5-20261021`
- **target_commit**：`db514956281b7492954a3dbecb429117178491cd`
- **packet**：`reports/p010_20261019/midpoint_freeze_20261021_1200PDT_v1`
- MANIFEST `fbfa3a5d8e09c7895251d842e2cf06b0d5790fe9487d2109510c3a7ecc2f3038`；COPY_SOURCE_BINDING `7ea2e7c900b501e98be23b993af46575959b5baf7fe6bd8e85546f92a4d1f8d7`；FREEZE_STATUS `4e472f29e722a6b35b7e78747452413c881846adfd69d9ac872ff79ff1eca7a5`（均已重算）

## 结论：PASS

| flag | 值 |
|---|---|
| actual_post_cutoff_freeze_and_distinct_write_times_accepted | **true**（计划截止 19:00:00 UTC；实际写入 19:00:10.76–19:00:11.32 UTC，分开记录） |
| all_copied_original_tables_figures_and_source_bindings_accepted | **true** |
| dated_footnotes_all_contrasts_and_failure_histories_retained | **true** |
| prior_review_access_limits_and_non_Z1_scope_retained | **true** |
| final_frozen_version_A5_accepted | **true** |

## 检查

- MANIFEST 中 58 个文件的 sha 全部一致。
- COPY_SOURCE_BINDING 中 54 个复制文件，我逐个用 `git show <source_commit>:<source_file>` 取出原字节比对：sha 和字节数**全部一致，0 处不符**。来源提交为 9178029d（T1–T4、F1–F2、number trace）和 f8c17cf8（带日期的脚注、E3/C6 A3、早期 A5、技术交接）。
- 排除项只有未使用的历史构建脚本和 Claude 的 Z1 占位文件，原 manifest 条目保留；Z1 内容不在本冻结中。
- 抽查数字溯源：T4 seed 17 的 9 个主对比（greedy）和 9 个次对比（采样）的点估计，用 T4_E1_E1D_SEED17 的计数重算，**全部一致**。
- 失败、取消（T7/T72 的 K4/K8）、GSM 解析器敏感性、T1 字段定义等脚注都保留。

## 局限（沿用）

早期 A5 中有 4 个只在本地的溯源来源无法独立访问，本次同样没有独立核验。区间来自 bootstrap，未重跑；点估计已重算。费用观测是延迟计量的部分归属，不是账单。
