# B1/B3 学生：长序列 r2 失败后的 100 源码账本适配，CR

- **审计方**：Claude。以本报告的 git 提交时间为准
- **请求**：`p011-B-generation-student-complete-path-CR-A1-A2-lite-r1`
- **scope**：`p011-B-retained-students-complete-path-CR-A1-A2-lite`
- **target_commit**：`3e2c1b8f3e4cfc2e076b5e42580d94ae570e74ce`（在 08b67af5 上核对）

## 结论：PASS

| 字段 | 值 |
|---|---|
| decision | `PASS` |
| spec_sha256 | `4270e923e59b230d0e8fbe1f9e95cd34dd5f50d3bdb424b108c028581f4328ab` |
| jobs_sha256 | `a4c5fc8f2fbf7e623e4292398c376786185366faae1f2f5d757cad6919838665`（与 acea0550 时的 job 完全相同） |
| source_files | 100 个，sha 全部一致；原 96 个不变，新增 4 个适配器 |
| failed_attempt_bindings_sha256 | `c1b5843976b6bd08028ab56cfb7e6403ab92d639ff756ede1419d08279c743ff`（B r1 3.01；L15 r1 26.08；F15 r1 15.63；F15 r2 15.63；基线 r2 12.17） |
| prior_B1_input_upload_sha256 | `fa18d43e10156699f52f770819011e6e19302730f701d3e98a488b10c21f5bcc` |
| prior_actual_B_input_numeric_report_sha256 | `acea0550…` |
| 其余绑定 | generation_actual_A3 `885fce37…`；student_input_CR `e1dbb377…`；input manifest `ccd0bf33…`；owner_B16 `2e0c8af1…`；budget_owner `364aaf6c…`；measurement_exceptions 0 |
| 16 个 flag | **全部 true** |

## 逐项

- **`b_students_post_long_failure_path.py`**（与 `b_students_path.py` 对比）：
  - `validate` 要求两个新的长序列 r2 失败父任务及其完整预留（15.63 / 12.17）都在账本中，B1 原上传收据的路径固定，并绑定 acea0550。
  - `prior_B1_upload` 核对收据的 sha、`job_sha256`、已全部回读、model_calls 为 0、资产收据，以及没有再次传输旧资产；在 submit 中先于任何远端操作调用 ✓
  - `reviewed` 新增 2 项绑定和 2 个 flag ✓
- **modal / IO / analyze**：只改了 import 和 app 名 ✓
- 科学部分、job、限额、窗口、80% 规则都不变。

## 数值（与 acea0550 相同；当前账本另外加入长序列失败，但它们属于 A 类，不影响 B）

B1 6.18 ≤ 0.8 × 13.98 ✓；B3 6.18 ≤ 0.8 × 7.80 ✓（余量 $0.06）。**最晚 18:35:35 UTC 派发**。派发前仍要做新鲜的费率、D1、≤ 4 槽位、fence 和窗口检查。B1 不得重复上传。
