# 正式 A：冻结 LR 的 r2 路径（F15 A7 冒烟 + 1.5B 基线），源码 CR + 数值审查

- **审计方**：Claude。以本报告的 git 提交时间为准
- **请求**：`p011-long-A-D-complete-path-CR-A1-A2-lite-r1`
- **scope**：`p011-long-A-D-complete-path-CR-A1-A2-lite`
- **source_appendix_scope**：`p011-long-frozen-LR-r2-complete-path-CR`
- **target_commit**：`f704855dd2c3a2909ab53ea0b94fdd40da749256`（在 8bfdaada 上核对）

## 结论：PASS

| 字段 | 值 |
|---|---|
| decision | `PASS` |
| spec_sha256 | `9f675f1c4e92f45f438e251ce926f096e9833868680bb2459e4cd14603e24f7b` |
| jobs_sha256 | `e81dc988a860fe4d752f2bd4d914f0383447b60cc086a101e9249f60cdb631d2`（已重算） |
| source_files | **55 个**：原 48 个不变，新增 7 个；HEAD 上逐个 sha 一致。SOURCE_BINDING `f531bd9f…` |
| failed_attempt_bindings_sha256 | `78051491dddd733cb2e59f169008e8ad7aa09a948bc6a8144c68f21f085a1282`（含 L15 r1 26.08、F15 r1 15.63、B r1 3.01） |
| prior_input_receipts_sha256 | `a443a76a0bc7f72189c01877cce20b917c29ed6f11726f06c454d8e10b72cadb` |
| prior_failed_C1_sha256 | `cef4180d…` |
| repair_decision_sha256 | `481620ca0df59ebcc0fd4aa314a7fe32445dd64c1d4e9609a57eeb1a8cd2911f`（副本与原文件 sha 一致） |
| LR_relative_peak_tolerance | `1e-12` |
| original_numeric_spec / report / decision | `f0e92744…` / `aac07df3…` / `PASS-WITH-CONDITIONS` |
| initial_allowed_jobs | `long_A7_S-F15_s17_r2`、`long_baseline_S-L15_s17_r2` |
| 其余绑定 | budget_owner `364aaf6c…`；输入目录 `long_inputs_numeric_gold_r1` / `cee34dc0…`；measurement_exceptions 0 |
| 21 个 flag | **全部 true** |

## 逐项

- **SPEC**：只有 2 个 job，每一个都与原 r1 job 在规范化 JSON 后完全相等（限额、计时、费率、输入、冻结 LR 文件的 sha 都不变；F15 的 `rates_S-F15.json` 为 `fbe6ae91…`）✓
- **`long_lr_r2_training.py`**：与 `long_training.py` 相比，只新增了 `compatible_frozen_rates`，并改了 `validate_plan` 中的一个条件。
  - 新条件要求：列表长度为 U，每项都是有限的 float，且每项与重算值的差 ≤ 1e-12 × peak。
  - 训练使用冻结的数值，**不替换任何一项**；其余校验逐字未变 ✓
- **`long_lr_r2_execution.py` / `long_lr_r2_evidence.py`**：只改了 import。这样训练入口、最终训练函数和本地完整状态 oracle 用的是同一个校验器 ✓ 其他地方都不再逐位比较 `learning_rates`（已 grep 确认）。
- **`long_lr_r2_path.py`**（与 conditional 版对比，108 行 diff）：
  - `logical` 只允许 F15 A7 和 1.5B 基线，后缀改为 `_r2`；key、BASE 下的输出目录和 fence 都是新的 ✓
  - `conditional_evidence` 新增修复决定的 sha 和容差字段；要求两个 job 都与原 r1 相等，`set(jobs)` 等于初始集合；两个失败父任务及其预留（26.08 / 15.63）必须存在；原上传收据的路径固定 ✓
  - `selection` 一律拒绝后续 job ✓
  - `initial_pair_budget` 对两个 r2 job 按顺序检查 80% 规则 ✓
  - submit 要求 r2 登记收据中的 `original_input_receipt_sha256` 等于 SPEC，且 `new_remote_input_or_weight_reads = 0` ✓
- **IO**：upload 只做 r2 登记：读取原输入收据，要求 sha 一致、`job_sha256` 等于当前 job（r1 和 r2 的 job 相同，所以成立）、已全部回读；不再传输任何东西。远端 worker 仍会完整校验输入和模型 ✓
- **modal / analyze**：只改了 import 和 app 名 ✓
- **我自己的复核（Linux）**：
  - 两个冻结 LR 文件用 `compatible_frozen_rates` 检查都是 True；最大绝对差分别为 1.7e-21（F15）和 1.4e-20（L15），远小于容差 1e-17 / 1e-16。
  - 把第 10 项乘以 1.0001 后检查为 False ✓
  - `tests/test_p011_long_lr_r2` 在本机 OK。

## 数值

- **预算**：A 现有预留 47.66。F15 15.63 ≤ 0.8 × 67.34 ✓；随后基线 12.17 ≤ 0.8 × 51.71 ✓；合计 75.46。
- **时间**：完整窗口不变，F15 最晚派发 21:48 UTC，基线最晚派发 22:13 UTC。
- 派发前仍要逐个做新鲜的费率、D1、≤ 4 槽位、未使用 fence 和完整窗口检查。
- §7.4 的 A6 预算缺口仍然存在，等负责人决定；本报告不释放预留、不加上限。
